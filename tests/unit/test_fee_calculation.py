import pytest
from fastapi.testclient import TestClient


def test_standard_fee_20_percent(integrated_client: TestClient, inventory_client: TestClient):
    """
    Tier 1: Verify exact 20% calculation: unit_price=$50.00 -> fee=$10.00, total=$60.00.
    """
    prod = inventory_client.post("/inventory/product", json={"name": "Book", "price": 50.0, "quantity": 10}).json()
    res = integrated_client.post("/orders/", json={"product_id": prod["pk"], "order_quantity": 1})
    assert res.status_code == 200
    data = res.json()
    assert data["price"] == 50.0
    assert data["fee_per_unit"] == 10.0
    assert data["total"] == 60.0


def test_fractional_fee_rounding(integrated_client: TestClient, inventory_client: TestClient):
    """
    Tier 1: Verify fractional rounding: $19.99 * 0.2 = 3.998 -> rounded to 4.00.
    Total = (19.99 + 4.00) * 1 = 23.99.
    """
    prod = inventory_client.post("/inventory/product", json={"name": "Coffee", "price": 19.99, "quantity": 10}).json()
    res = integrated_client.post("/orders/", json={"product_id": prod["pk"], "order_quantity": 1})
    assert res.status_code == 200
    data = res.json()
    assert data["price"] == 19.99
    assert data["fee_per_unit"] == 4.00
    assert data["total"] == 23.99


def test_multi_unit_fee_accumulation(integrated_client: TestClient, inventory_client: TestClient):
    """
    Tier 1: Verify multi-unit scaling: price=$12.50, fee=$2.50, unit_total=$15.00, qty=4 -> total=$60.00.
    """
    prod = inventory_client.post("/inventory/product", json={"name": "Pens", "price": 12.50, "quantity": 20}).json()
    res = integrated_client.post("/orders/", json={"product_id": prod["pk"], "order_quantity": 4})
    assert res.status_code == 200
    data = res.json()
    assert data["order_quantity"] == 4
    assert data["price"] == 12.50
    assert data["fee_per_unit"] == 2.50
    assert data["total"] == 60.00


def test_low_price_fee_rounding(integrated_client: TestClient, inventory_client: TestClient):
    """
    Tier 1: Verify low price calculation: price=$0.50 -> fee=$0.10 -> total=$0.60.
    """
    prod = inventory_client.post("/inventory/product", json={"name": "Sticker", "price": 0.50, "quantity": 100}).json()
    res = integrated_client.post("/orders/", json={"product_id": prod["pk"], "order_quantity": 1})
    assert res.status_code == 200
    data = res.json()
    assert data["price"] == 0.50
    assert data["fee_per_unit"] == 0.10
    assert data["total"] == 0.60


def test_exact_two_decimal_precision(integrated_client: TestClient, inventory_client: TestClient):
    """
    Tier 1: Verify currency precision: price=$9.95, fee=$1.99, total=(9.95+1.99)*3 = $35.82.
    """
    prod = inventory_client.post("/inventory/product", json={"name": "Notebook", "price": 9.95, "quantity": 50}).json()
    res = integrated_client.post("/orders/", json={"product_id": prod["pk"], "order_quantity": 3})
    assert res.status_code == 200
    data = res.json()
    assert data["price"] == 9.95
    assert data["fee_per_unit"] == 1.99
    assert data["total"] == 35.82
