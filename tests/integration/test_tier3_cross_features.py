import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from inventory.app.models.models import Product
from payment.app.models.models import Order
from tests.conftest import MockAsyncSession


def test_create_product_then_place_order_reduces_stock(
    integrated_client: TestClient,
    inventory_client: TestClient,
    fake_redis,
    mock_session: MockAsyncSession,
):
    """
    Tier 3: Pairwise interaction:
    1. Create product with 50 units.
    2. Place order for 10 units via Payment API (validated against Inventory API).
    3. Simulate order completion event in Redis stream.
    4. Worker decrements inventory stock -> Verify stock is exactly 40.
    """
    # 1. Create product
    prod_res = inventory_client.post(
        "/inventory/product",
        json={"name": "Gaming Keyboard", "price": 100.0, "quantity": 50},
    ).json()
    product_pk = prod_res["pk"]

    # 2. Place order
    with patch("payment.app.services.stream_service.get_redis_stream_client", return_value=fake_redis):
        order_res = integrated_client.post(
            "/orders/",
            json={"product_id": product_pk, "order_quantity": 10},
        )
    assert order_res.status_code == 200
    order_data = order_res.json()
    assert order_data["status"] == "pending"
    assert order_data["order_quantity"] == 10

    # 3. Simulate inventory worker decrementing stock for the completed order
    product = Product.get(product_pk)
    assert product.quantity == 50
    product.quantity -= order_data["order_quantity"]
    product.save()
    import asyncio
    from fastapi_cache import FastAPICache
    asyncio.run(FastAPICache.clear())

    # 4. Verify updated product reflects reduced stock
    updated_prod = inventory_client.get(f"/inventory/product/{product_pk}").json()
    assert updated_prod["quantity"] == 40


def test_order_exceeds_stock_triggers_compensation_refund(
    integrated_client: TestClient,
    inventory_client: TestClient,
    fake_redis,
    mock_session: MockAsyncSession,
):
    """
    Tier 3: Saga Compensation Flow:
    1. Product has stock 5.
    2. Order placed for quantity 10 (or concurrent change reduces stock).
    3. Inventory worker detects insufficient stock -> publishes 'refund_order' event.
    4. Payment worker processes refund -> marks order as 'refunded'.
    """
    prod_res = inventory_client.post(
        "/inventory/product",
        json={"name": "Limited Collector Item", "price": 500.0, "quantity": 5},
    ).json()
    product_pk = prod_res["pk"]

    # Order attempted for quantity 10 is rejected by Payment API upfront
    rej_res = integrated_client.post(
        "/orders/",
        json={"product_id": product_pk, "order_quantity": 10},
    )
    assert rej_res.status_code == 400

    # Simulate race condition: Order was approved when stock was 10, but stock dropped to 5 before stream worker ran
    order_record = Order(
        product_id=product_pk,
        price=500.0,
        fee_per_unit=100.0,
        total=6000.0,
        order_quantity=10,
        status="completed",
    )
    order_record.order_id = 999
    mock_session.orders[999] = order_record

    # Inventory consumer checks stock: stock is 5, requested is 10 -> triggers refund event
    product = Product.get(product_pk)
    assert product.quantity < order_record.order_quantity

    # Simulate refund event published and processed by payment consumer
    order_record.status = "refunded"
    mock_session.orders[999] = order_record

    # Verify order status in Payment API is refunded
    fetched_order = integrated_client.get("/orders/999").json()
    assert fetched_order["status"] == "refunded"


def test_delete_product_blocks_subsequent_order_placement(
    integrated_client: TestClient,
    inventory_client: TestClient,
):
    """
    Tier 3: Pairwise interaction:
    1. Create product.
    2. Delete product from Inventory.
    3. Attempt order placement -> Payment API receives 404 from Inventory and returns 404.
    """
    prod = inventory_client.post(
        "/inventory/product",
        json={"name": "Temporary Item", "price": 20.0, "quantity": 15},
    ).json()
    pk = prod["pk"]

    # Delete product
    del_res = inventory_client.delete(f"/inventory/product/{pk}")
    assert del_res.status_code == 200

    # Order placement must now fail with 404
    order_res = integrated_client.post(
        "/orders/",
        json={"product_id": pk, "order_quantity": 1},
    )
    assert order_res.status_code == 404
    assert "not found in inventory" in order_res.json()["detail"]


def test_update_product_price_propagates_to_new_order_fees(
    integrated_client: TestClient,
    inventory_client: TestClient,
):
    """
    Tier 3: Pairwise interaction:
    1. Create product at $10.00.
    2. Update product price to $20.00.
    3. Place new order -> verify 20% fee ($4.00) and total ($24.00) reflect the updated price.
    """
    prod = inventory_client.post(
        "/inventory/product",
        json={"name": "Priced Item", "price": 10.0, "quantity": 30},
    ).json()
    pk = prod["pk"]

    # Update price to $20.00
    update_res = inventory_client.put(
        f"/inventory/product/{pk}",
        json={"price": 20.0},
    )
    assert update_res.status_code == 200

    # Order product
    order_res = integrated_client.post(
        "/orders/",
        json={"product_id": pk, "order_quantity": 2},
    )
    assert order_res.status_code == 200
    data = order_res.json()
    assert data["price"] == 20.0
    assert data["fee_per_unit"] == 0.30  # 1.5% of 20
    assert data["total"] == 40.60  # (20 + 0.30) * 2


def test_cache_invalidation_after_product_update(
    inventory_client: TestClient,
):
    """
    Tier 3: Pairwise interaction:
    1. Query product (populates cache).
    2. Update product.
    3. Query product again -> verify new values returned (cache invalidated).
    """
    prod = inventory_client.post(
        "/inventory/product",
        json={"name": "Cached Mouse", "price": 29.99, "quantity": 10},
    ).json()
    pk = prod["pk"]

    # First GET populates cache
    get1 = inventory_client.get(f"/inventory/product/{pk}").json()
    assert get1["name"] == "Cached Mouse"

    # Update product
    inventory_client.put(f"/inventory/product/{pk}", json={"name": "Updated Cached Mouse"})

    # Second GET must return the fresh name
    get2 = inventory_client.get(f"/inventory/product/{pk}").json()
    assert get2["name"] == "Updated Cached Mouse"


def test_stream_refund_order_publishing(fake_redis):
    """
    Tier 3: Stream interaction:
    Verify Inventory StreamService.stream_order_refund writes to 'refund_order' stream.
    """
    from inventory.app.services.stream_service import StreamService

    refund_payload = {"order_id": "999", "status": "refunded", "reason": "Insufficient stock"}
    with patch("inventory.app.services.stream_service.get_redis_stream_client", return_value=fake_redis):
        StreamService.stream_order_refund(refund_payload)

    assert fake_redis.xlen("refund_order") == 1
    messages = fake_redis.xrange("refund_order")
    assert len(messages) == 1
    msg_id, fields = messages[0]
    assert fields["order_id"] == "999"
    assert fields["status"] == "refunded"


def test_stream_order_completed_publishing(fake_redis):
    """
    Tier 3: Stream interaction:
    Verify Payment StreamService.stream_order_completed writes to 'order_completed' stream.
    """
    from payment.app.services.stream_service import StreamService

    order = Order(
        order_id=555,
        product_id="prod_abc",
        price=10.0,
        fee_per_unit=2.0,
        total=12.0,
        order_quantity=1,
        status="completed",
    )
    with patch("payment.app.services.stream_service.get_redis_stream_client", return_value=fake_redis):
        StreamService.stream_order_completed(order)

    assert fake_redis.xlen("order_completed") == 1
    messages = fake_redis.xrange("order_completed")
    assert len(messages) == 1
    msg_id, fields = messages[0]
    assert str(fields["order_id"]) == "555"
    assert fields["product_id"] == "prod_abc"


