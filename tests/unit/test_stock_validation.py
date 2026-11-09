import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient
import httpx


def test_stock_validation_order_less_than_stock(integrated_client: TestClient, inventory_client: TestClient):
    """
    Tier 1: Stock validation succeeds when order_quantity < product.quantity.
    """
    prod = inventory_client.post("/inventory/product", json={"name": "SSD", "price": 99.0, "quantity": 10}).json()
    res = integrated_client.post("/orders/", json={"product_id": prod["pk"], "order_quantity": 5})
    assert res.status_code == 200
    assert res.json()["status"] == "pending"


def test_stock_validation_order_equal_to_stock(integrated_client: TestClient, inventory_client: TestClient):
    """
    Tier 1: Stock validation succeeds when order_quantity == product.quantity.
    """
    prod = inventory_client.post("/inventory/product", json={"name": "RAM", "price": 45.0, "quantity": 7}).json()
    res = integrated_client.post("/orders/", json={"product_id": prod["pk"], "order_quantity": 7})
    assert res.status_code == 200
    assert res.json()["order_quantity"] == 7


def test_stock_validation_order_exceeds_stock_returns_400(integrated_client: TestClient, inventory_client: TestClient):
    """
    Tier 1: Order request exceeding available stock returns HTTP 400 Bad Request.
    """
    prod = inventory_client.post("/inventory/product", json={"name": "GPU", "price": 799.0, "quantity": 2}).json()
    res = integrated_client.post("/orders/", json={"product_id": prod["pk"], "order_quantity": 5})
    assert res.status_code == 400
    assert "exceeds available stock" in res.json()["detail"]


def test_stock_validation_zero_stock_returns_400(integrated_client: TestClient, inventory_client: TestClient):
    """
    Tier 1: Order request for product with 0 available stock returns HTTP 400 Bad Request.
    """
    prod = inventory_client.post("/inventory/product", json={"name": "Sold Out Item", "price": 20.0, "quantity": 0}).json()
    res = integrated_client.post("/orders/", json={"product_id": prod["pk"], "order_quantity": 1})
    assert res.status_code == 400
    assert "exceeds available stock" in res.json()["detail"]


def test_stock_validation_missing_product_returns_404(integrated_client: TestClient):
    """
    Tier 1: Order request for non-existent product ID returns HTTP 404 Not Found.
    """
    res = integrated_client.post("/orders/", json={"product_id": "non_existent_id_xyz", "order_quantity": 1})
    assert res.status_code == 404
    assert "not found in inventory" in res.json()["detail"]


def test_stock_validation_inventory_down_returns_502(payment_client: TestClient):
    """
    Tier 1: Payment API gracefully returns HTTP 502 when Inventory service is unreachable.
    """
    with patch.object(httpx.AsyncClient, "get", side_effect=httpx.RequestError("Connection refused")):
        res = payment_client.post("/orders/", json={"product_id": "any_id", "order_quantity": 1})
        assert res.status_code == 502
        assert "Unable to connect to inventory service" in res.json()["detail"]
