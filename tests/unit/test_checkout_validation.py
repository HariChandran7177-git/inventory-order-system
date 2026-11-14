import pytest
from fastapi.testclient import TestClient


def test_validate_checkout_success(integrated_client: TestClient, inventory_client: TestClient):
    """
    Verify validation succeeds when stock is sufficient and prices match.
    """
    prod = inventory_client.post(
        "/inventory/product",
        json={"name": "Gaming Chair", "price": 200.0, "quantity": 10},
    ).json()

    payload = {
        "items": [
            {
                "product_id": prod["pk"],
                "order_quantity": 2,
                "client_price": 200.0,
            }
        ]
    }

    res = integrated_client.post("/orders/validate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["is_valid"] is True
    assert data["has_stock_issues"] is False
    assert data["has_price_changes"] is False
    assert len(data["items"]) == 1
    item = data["items"][0]
    assert item["has_sufficient_stock"] is True
    assert item["price_change_type"] == "none"
    assert item["status"] == "ok"
    assert data["updated_subtotal"] == 400.0
    # 1.5% fee on 400 is 6.00
    assert data["updated_platform_fee"] == 6.0
    assert data["updated_total"] == 406.0


def test_validate_checkout_insufficient_stock(integrated_client: TestClient, inventory_client: TestClient):
    """
    Verify validation fails and flags insufficient stock when requested quantity > stock.
    """
    prod = inventory_client.post(
        "/inventory/product",
        json={"name": "Limited Desk", "price": 150.0, "quantity": 2},
    ).json()

    payload = {
        "items": [
            {
                "product_id": prod["pk"],
                "order_quantity": 5,  # Requested 5, but stock is 2
                "client_price": 150.0,
            }
        ]
    }

    res = integrated_client.post("/orders/validate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["is_valid"] is False
    assert data["has_stock_issues"] is True
    item = data["items"][0]
    assert item["has_sufficient_stock"] is False
    assert item["available_stock"] == 2
    assert item["status"] == "insufficient_stock"


def test_validate_checkout_price_hike(integrated_client: TestClient, inventory_client: TestClient):
    """
    Verify validation detects a price hike (live price > client price).
    """
    prod = inventory_client.post(
        "/inventory/product",
        json={"name": "SSD Drive", "price": 120.0, "quantity": 10},
    ).json()

    payload = {
        "items": [
            {
                "product_id": prod["pk"],
                "order_quantity": 1,
                "client_price": 100.0,  # Cart had $100, but live catalog is $120 (hike!)
            }
        ]
    }

    res = integrated_client.post("/orders/validate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["is_valid"] is False
    assert data["has_price_changes"] is True
    item = data["items"][0]
    assert item["price_change_type"] == "hike"
    assert item["price_difference"] == 20.0
    assert item["current_price"] == 120.0
    assert item["status"] == "price_changed"
    assert data["updated_subtotal"] == 120.0


def test_validate_checkout_price_drop(integrated_client: TestClient, inventory_client: TestClient):
    """
    Verify validation detects a price drop (live price < client price).
    """
    prod = inventory_client.post(
        "/inventory/product",
        json={"name": "Monitor Arm", "price": 40.0, "quantity": 10},
    ).json()

    payload = {
        "items": [
            {
                "product_id": prod["pk"],
                "order_quantity": 2,
                "client_price": 50.0,  # Cart had $50, but live catalog dropped to $40 (drop!)
            }
        ]
    }

    res = integrated_client.post("/orders/validate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["is_valid"] is False
    assert data["has_price_changes"] is True
    item = data["items"][0]
    assert item["price_change_type"] == "drop"
    assert item["price_difference"] == -10.0
    assert item["current_price"] == 40.0
    assert item["status"] == "price_changed"
    assert data["updated_subtotal"] == 80.0
