import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
from fastapi_cache import FastAPICache
from inventory.app.models.models import Product
from payment.app.models.models import Order
from tests.conftest import MockAsyncSession


def test_full_customer_shopping_journey(
    integrated_client: TestClient,
    inventory_client: TestClient,
    fake_redis,
    mock_session: MockAsyncSession,
):
    """
    Tier 4: Complete E2E customer shopping journey:
    1. Customer browses catalog via GET /inventory/products.
    2. Customer inspects item details via GET /inventory/product/{pk}.
    3. Customer initiates purchase via POST /orders/.
    4. Order persists in PostgreSQL with status 'pending' and calculated 20% fees.
    5. Order completion event is processed, stock is deducted in inventory.
    6. Customer inspects updated order status and product stock.
    """
    # Setup catalog product
    init_prod = inventory_client.post(
        "/inventory/product",
        json={"name": "Ultrawide Curved Monitor", "price": 499.99, "quantity": 8},
    ).json()
    product_pk = init_prod["pk"]

    # Step 1: Browse catalog
    catalog_res = inventory_client.get("/inventory/products")
    assert catalog_res.status_code == 200
    catalog = catalog_res.json()
    assert any(item["id"] == product_pk for item in catalog)

    # Step 2: Inspect item
    item_res = inventory_client.get(f"/inventory/product/{product_pk}")
    assert item_res.status_code == 200
    assert item_res.json()["name"] == "Ultrawide Curved Monitor"

    # Step 3: Place order for 2 units
    with patch("payment.app.services.stream_service.get_redis_stream_client", return_value=fake_redis):
        order_res = integrated_client.post(
            "/orders/",
            json={"product_id": product_pk, "order_quantity": 2},
        )
    assert order_res.status_code == 200
    order = order_res.json()
    assert order["status"] == "pending"
    assert order["order_quantity"] == 2
    assert order["price"] == 499.99
    assert order["fee_per_unit"] == 100.00  # 20% of 499.99 is 99.998 -> rounded to 100.00
    assert order["total"] == 1199.98  # (499.99 + 100.00) * 2

    order_id = order["order_id"]

    # Step 4: Simulate order processing completion
    saved_order = mock_session.orders[order_id]
    saved_order.status = "completed"

    # Step 5: Simulate inventory worker decrement and cache invalidation
    prod = Product.get(product_pk)
    prod.quantity -= 2
    prod.save()
    # Invalidate cached product
    import asyncio
    asyncio.run(FastAPICache.clear())

    # Step 6: Verify final states
    final_order = integrated_client.get(f"/orders/{order_id}").json()
    assert final_order["status"] == "completed"

    final_prod = inventory_client.get(f"/inventory/product/{product_pk}").json()
    assert final_prod["quantity"] == 6


def test_concurrent_orders_inventory_depletion(
    integrated_client: TestClient,
    inventory_client: TestClient,
):
    """
    Tier 4: Concurrency and overselling prevention:
    1. Flash sale product has strictly 2 units available.
    2. Two consecutive orders for quantity 1 succeed.
    3. Third order is rejected with 400 Bad Request due to stock exhaustion.
    """
    prod = inventory_client.post(
        "/inventory/product",
        json={"name": "Limited Edition Sneaker", "price": 180.0, "quantity": 2},
    ).json()
    pk = prod["pk"]

    # Order 1: Success
    res1 = integrated_client.post("/orders/", json={"product_id": pk, "order_quantity": 1})
    assert res1.status_code == 200

    # Decrement stock to simulate completed order 1
    p = Product.get(pk)
    p.quantity -= 1
    p.save()
    import asyncio
    asyncio.run(FastAPICache.clear())

    # Order 2: Success
    res2 = integrated_client.post("/orders/", json={"product_id": pk, "order_quantity": 1})
    assert res2.status_code == 200

    # Decrement stock to simulate completed order 2
    p = Product.get(pk)
    p.quantity -= 1
    p.save()
    asyncio.run(FastAPICache.clear())

    # Order 3: Should fail (stock is now 0)
    res3 = integrated_client.post("/orders/", json={"product_id": pk, "order_quantity": 1})
    assert res3.status_code == 400
    assert "exceeds available stock" in res3.json()["detail"]


def test_redis_stream_event_publishing_and_pel_acknowledgement(
    fake_redis,
):
    """
    Tier 4: Stream PEL (Pending Entries List) recovery and ACK verification:
    1. Create consumer group on stream 'order_completed'.
    2. Publish order completed event.
    3. Consumer reads event -> message enters PEL.
    4. Consumer processes and calls XACK.
    5. Query PEL (XPENDING) -> verify count is 0 (no lingering unacked entries).
    """
    stream_key = "order_completed"
    group = "inventory_group"
    consumer = "test_worker_1"

    # 1. Initialize consumer group
    fake_redis.xgroup_create(stream_key, group, id="0", mkstream=True)

    # 2. Add message to stream
    msg_id = fake_redis.xadd(
        stream_key,
        {"order_id": "888", "product_id": "prod_1", "order_quantity": "2", "status": "completed"},
    )
    assert msg_id is not None

    # 3. Read message via consumer group
    entries = fake_redis.xreadgroup(group, consumer, {stream_key: ">"}, count=1)
    assert len(entries) > 0
    read_stream, msg_list = entries[0]
    read_id, read_fields = msg_list[0]
    assert read_id == msg_id
    assert read_fields["order_id"] == "888"

    # Verify message is in PEL before ACK
    pending_info = fake_redis.xpending(stream_key, group)
    assert pending_info["pending"] == 1

    # 4. Acknowledge message
    fake_redis.xack(stream_key, group, read_id)

    # 5. Verify PEL is cleared
    pending_after = fake_redis.xpending(stream_key, group)
    assert pending_after["pending"] == 0


def test_multi_item_independent_orders_flow(
    integrated_client: TestClient,
    inventory_client: TestClient,
):
    """
    Tier 4: Multi-item storefront purchasing sequence:
    Customer places multiple orders for diverse products.
    Verifies isolation across distinct order IDs, independent 20% fees, and stock deductions.
    """
    prod_a = inventory_client.post("/inventory/product", json={"name": "Product Alpha", "price": 30.0, "quantity": 10}).json()
    prod_b = inventory_client.post("/inventory/product", json={"name": "Product Beta", "price": 60.0, "quantity": 20}).json()

    order_a_res = integrated_client.post("/orders/", json={"product_id": prod_a["pk"], "order_quantity": 2})
    order_b_res = integrated_client.post("/orders/", json={"product_id": prod_b["pk"], "order_quantity": 3})

    assert order_a_res.status_code == 200
    assert order_b_res.status_code == 200

    order_a = order_a_res.json()
    order_b = order_b_res.json()

    assert order_a["order_id"] != order_b["order_id"]
    assert order_a["total"] == 72.0  # (30 + 6) * 2
    assert order_b["total"] == 216.0  # (60 + 12) * 3


def test_order_resilience_to_malformed_inventory_response(
    payment_client: TestClient,
):
    """
    Tier 4: Resilience test: When Inventory API returns unexpected payload schema (missing price),
    Payment API returns clean HTTP 502 without unhandled crash.
    """
    import httpx

    # Simulate an inventory response missing 'price'
    mock_transport = httpx.MockTransport(
        lambda req: httpx.Response(200, json={"id": "bad_item", "quantity": 10})
    )

    with patch("httpx.AsyncClient", return_value=httpx.AsyncClient(transport=mock_transport)):
        res = payment_client.post("/orders/", json={"product_id": "bad_item", "order_quantity": 1})
        assert res.status_code == 502
        assert "Invalid response schema" in res.json()["detail"]
