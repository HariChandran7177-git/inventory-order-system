import pytest
from fastapi.testclient import TestClient


# ============================================================================
# Tier 2: Inventory Boundary & Corner Cases
# ============================================================================

def test_inventory_boundary_quantity_zero(inventory_client: TestClient):
    """
    Tier 2: Product creation with quantity=0 is valid (out-of-stock initial state).
    """
    res = inventory_client.post("/inventory/product", json={"name": "Zero Stock Item", "price": 10.0, "quantity": 0})
    assert res.status_code in [200, 201]
    assert res.json()["quantity"] == 0


def test_inventory_boundary_empty_product_name(inventory_client: TestClient):
    """
    Tier 2: Product creation with an empty name is rejected by validation.
    """
    res = inventory_client.post("/inventory/product", json={"name": "", "price": 5.0, "quantity": 1})
    assert res.status_code == 422


def test_inventory_boundary_max_integer_quantity(inventory_client: TestClient):
    """
    Tier 2: Product creation with large 32-bit integer quantity limit.
    """
    max_qty = 2147483647
    res = inventory_client.post("/inventory/product", json={"name": "Bulk Commodity", "price": 1.0, "quantity": max_qty})
    assert res.status_code in [200, 201]
    assert res.json()["quantity"] == max_qty


def test_inventory_boundary_non_existent_pk_queries(inventory_client: TestClient):
    """
    Tier 2: Querying, updating, and deleting non-existent product PKs returns 404 without crashing.
    """
    fake_pk = "non_existent_pk_00000000"
    get_res = inventory_client.get(f"/inventory/product/{fake_pk}")
    assert get_res.status_code == 404

    put_res = inventory_client.put(f"/inventory/product/{fake_pk}", json={"name": "Ghost"})
    assert put_res.status_code == 404

    del_res = inventory_client.delete(f"/inventory/product/{fake_pk}")
    assert del_res.status_code == 404


def test_inventory_boundary_malformed_json_payload(inventory_client: TestClient):
    """
    Tier 2: Invalid JSON or wrong datatypes yield HTTP 422 Unprocessable Entity.
    """
    # String for quantity instead of int
    res1 = inventory_client.post("/inventory/product", json={"name": "Bad Types", "price": "not_a_price", "quantity": "invalid"})
    assert res1.status_code == 422

    # Missing mandatory name and price
    res2 = inventory_client.post("/inventory/product", json={"quantity": 10})
    assert res2.status_code == 422


# ============================================================================
# Tier 2: Payment & Order Boundary & Corner Cases
# ============================================================================

def test_order_boundary_quantity_zero(integrated_client: TestClient, inventory_client: TestClient):
    """
    Tier 2: Order request with quantity 0.
    """
    prod = inventory_client.post("/inventory/product", json={"name": "Item", "price": 10.0, "quantity": 5}).json()
    res = integrated_client.post("/orders/", json={"product_id": prod["pk"], "order_quantity": 0})
    # If accepted or rejected, status code is valid HTTP response (not 500)
    assert res.status_code in [200, 400, 422]


def test_order_boundary_negative_quantity(integrated_client: TestClient, inventory_client: TestClient):
    """
    Tier 2: Negative order quantity must not result in 500 server crash.
    """
    prod = inventory_client.post("/inventory/product", json={"name": "Item", "price": 10.0, "quantity": 5}).json()
    res = integrated_client.post("/orders/", json={"product_id": prod["pk"], "order_quantity": -5})
    # Should not produce internal server error
    assert res.status_code in [400, 422, 200]


def test_order_boundary_non_existent_ids(payment_client: TestClient):
    """
    Tier 2: Non-existent order IDs query returns 404 (never 500).
    """
    assert payment_client.get("/orders/99999999").status_code == 404
    assert payment_client.put("/orders/99999999", json={"status": "cancelled"}).status_code == 404
    assert payment_client.delete("/orders/99999999").status_code == 404


def test_order_boundary_malformed_json(payment_client: TestClient):
    """
    Tier 2: Posting malformed order JSON returns 422 Unprocessable Entity.
    """
    res = payment_client.post("/orders/", json={"product_id": 12345, "order_quantity": "invalid_int"})
    assert res.status_code in [400, 422]

    empty_res = payment_client.post("/orders/", json={})
    assert empty_res.status_code == 422


def test_order_boundary_extreme_order_quantity(integrated_client: TestClient, inventory_client: TestClient):
    """
    Tier 2: Ordering huge integer far exceeding stock triggers clean 400.
    """
    prod = inventory_client.post("/inventory/product", json={"name": "Rare Gem", "price": 1000.0, "quantity": 1}).json()
    res = integrated_client.post("/orders/", json={"product_id": prod["pk"], "order_quantity": 999999999})
    assert res.status_code == 400
    assert "exceeds available stock" in res.json()["detail"]
