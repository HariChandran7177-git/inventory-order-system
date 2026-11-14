import pytest
from fastapi.testclient import TestClient


def test_standard_fee_1_5_percent(integrated_client: TestClient, inventory_client: TestClient):
    """
    Tier 1: Verify exact 1.5% platform fee calculation: unit_price=$50.00 -> fee=$0.75, total=$50.75.
    """
    prod = inventory_client.post("/inventory/product", json={"name": "Book", "price": 50.0, "quantity": 10}).json()
    res = integrated_client.post("/orders/", json={"product_id": prod["pk"], "order_quantity": 1})
    assert res.status_code == 200
    data = res.json()
    assert data["price"] == 50.0
    assert data["fee_per_unit"] == 0.75
    assert data["total"] == 50.75


def test_fractional_fee_rounding(integrated_client: TestClient, inventory_client: TestClient):
    """
    Tier 1: Verify fractional rounding: $19.99 * 0.015 = 0.29985 -> rounded to 0.30.
    Total = (19.99 + 0.30) * 1 = 20.29.
    """
    prod = inventory_client.post("/inventory/product", json={"name": "Coffee", "price": 19.99, "quantity": 10}).json()
    res = integrated_client.post("/orders/", json={"product_id": prod["pk"], "order_quantity": 1})
    assert res.status_code == 200
    data = res.json()
    assert data["price"] == 19.99
    assert data["fee_per_unit"] == 0.30
    assert data["total"] == 20.29


def test_multi_unit_fee_accumulation(integrated_client: TestClient, inventory_client: TestClient):
    """
    Tier 1: Verify multi-unit scaling: price=$12.50, fee=$0.19, unit_total=$12.69, qty=4 -> total=$50.76.
    """
    prod = inventory_client.post("/inventory/product", json={"name": "Pens", "price": 12.50, "quantity": 20}).json()
    res = integrated_client.post("/orders/", json={"product_id": prod["pk"], "order_quantity": 4})
    assert res.status_code == 200
    data = res.json()
    assert data["order_quantity"] == 4
    assert data["price"] == 12.50
    assert data["fee_per_unit"] == 0.19
    assert data["total"] == 50.76


def test_low_price_fee_rounding(integrated_client: TestClient, inventory_client: TestClient):
    """
    Tier 1: Verify low price calculation: price=$0.50 -> fee=$0.01 -> total=$0.51.
    """
    prod = inventory_client.post("/inventory/product", json={"name": "Sticker", "price": 0.50, "quantity": 100}).json()
    res = integrated_client.post("/orders/", json={"product_id": prod["pk"], "order_quantity": 1})
    assert res.status_code == 200
    data = res.json()
    assert data["price"] == 0.50
    assert data["fee_per_unit"] == 0.01
    assert data["total"] == 0.51


def test_exact_two_decimal_precision(integrated_client: TestClient, inventory_client: TestClient):
    """
    Tier 1: Verify currency precision: price=$9.95, fee=$0.15, total=(9.95+0.15)*3 = $30.30.
    """
    prod = inventory_client.post("/inventory/product", json={"name": "Notebook", "price": 9.95, "quantity": 50}).json()
    res = integrated_client.post("/orders/", json={"product_id": prod["pk"], "order_quantity": 3})
    assert res.status_code == 200
    data = res.json()
    assert data["price"] == 9.95
    assert data["fee_per_unit"] == 0.15
    assert data["total"] == 30.30
