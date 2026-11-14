import pytest
from fastapi.testclient import TestClient
from payment.app.models.models import Order
from tests.conftest import MockAsyncSession


def test_create_order_pending_lifecycle(integrated_client: TestClient, inventory_client: TestClient):
    """
    Tier 1: Verify order creation against valid inventory yields status 'pending'.
    """
    prod = inventory_client.post(
        "/inventory/product",
        json={"name": "Ergonomic Chair", "price": 250.0, "quantity": 10},
    ).json()

    order_payload = {
        "product_id": prod["pk"],
        "order_quantity": 2,
    }
    response = integrated_client.post("/orders/", json=order_payload)
    assert response.status_code == 200
    data = response.json()
    assert data["order_id"] is not None
    assert data["status"] == "pending"
    assert data["product_id"] == prod["pk"]
    assert data["order_quantity"] == 2
    assert data["price"] == 250.0
    assert data["fee_per_unit"] == 3.75  # 1.5% of 250
    assert data["total"] == 507.50  # (250 + 3.75) * 2


def test_get_order_by_id(payment_client: TestClient, mock_session: MockAsyncSession):
    """
    Tier 1: Verify retrieval of order by order_id.
    """
    test_order = Order(
        product_id="prod_test_101",
        price=45.0,
        fee_per_unit=9.0,
        total=54.0,
        order_quantity=1,
        status="pending",
    )
    mock_session.add(test_order)
    # Commit synchronously into mock storage
    test_order.order_id = 101
    mock_session.orders[101] = test_order

    response = payment_client.get("/orders/101")
    assert response.status_code == 200
    data = response.json()
    assert data["order_id"] == 101
    assert data["product_id"] == "prod_test_101"
    assert data["status"] == "pending"
    assert data["total"] == 54.0


def test_list_all_orders(payment_client: TestClient, mock_session: MockAsyncSession):
    """
    Tier 1: Verify querying all orders returns full order list.
    """
    o1 = Order(product_id="p1", price=10.0, fee_per_unit=2.0, total=12.0, order_quantity=1, status="pending")
    o2 = Order(product_id="p2", price=20.0, fee_per_unit=4.0, total=24.0, order_quantity=1, status="completed")
    o1.order_id = 201
    o2.order_id = 202
    mock_session.orders[201] = o1
    mock_session.orders[202] = o2

    response = payment_client.get("/orders/")
    assert response.status_code == 200
    items = response.json()
    assert len(items) >= 2
    order_ids = [item["order_id"] for item in items]
    assert 201 in order_ids
    assert 202 in order_ids


def test_update_order_status(payment_client: TestClient, mock_session: MockAsyncSession):
    """
    Tier 1: Verify updating an order's status to 'completed'.
    """
    o = Order(product_id="p3", price=15.0, fee_per_unit=3.0, total=18.0, order_quantity=1, status="pending")
    o.order_id = 301
    mock_session.orders[301] = o

    response = payment_client.put("/orders/301", json={"status": "completed"})
    assert response.status_code == 200
    data = response.json()
    assert data["order_id"] == 301


def test_update_order_total(payment_client: TestClient, mock_session: MockAsyncSession):
    """
    Tier 1: Verify updating an order's monetary total.
    """
    o = Order(product_id="p4", price=100.0, fee_per_unit=20.0, total=120.0, order_quantity=1, status="pending")
    o.order_id = 401
    mock_session.orders[401] = o

    response = payment_client.put("/orders/401", json={"total": 115.0})
    assert response.status_code == 200


def test_delete_order(payment_client: TestClient, mock_session: MockAsyncSession):
    """
    Tier 1: Verify deleting an order removes it and subsequent queries 404.
    """
    o = Order(product_id="p5", price=30.0, fee_per_unit=6.0, total=36.0, order_quantity=1, status="pending")
    o.order_id = 501
    mock_session.orders[501] = o

    del_res = payment_client.delete("/orders/501")
    assert del_res.status_code == 200

    get_res = payment_client.get("/orders/501")
    assert get_res.status_code == 404
