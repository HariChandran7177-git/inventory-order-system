from fastapi.testclient import TestClient


def test_create_product_rejects_negative_price(inventory_client: TestClient):
    response = inventory_client.post(
        "/inventory/product",
        json={"name": "Invalid price", "price": -1, "quantity": 1},
    )

    assert response.status_code == 422


def test_create_product_rejects_negative_quantity(inventory_client: TestClient):
    response = inventory_client.post(
        "/inventory/product",
        json={"name": "Invalid stock", "price": 1, "quantity": -1},
    )

    assert response.status_code == 422


def test_create_product_rejects_blank_name(inventory_client: TestClient):
    response = inventory_client.post(
        "/inventory/product",
        json={"name": "", "price": 1, "quantity": 1},
    )

    assert response.status_code == 422


def test_update_product_rejects_negative_values(inventory_client: TestClient):
    response = inventory_client.put(
        "/inventory/product/missing",
        json={"price": 1, "quantity": -1},
    )

    assert response.status_code == 422
