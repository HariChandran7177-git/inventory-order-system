import pytest
from fastapi.testclient import TestClient
from inventory.app.models.models import Product


def test_create_product_success(inventory_client: TestClient):
    """
    Tier 1: Verify successful product creation via POST /inventory/product.
    Expects HTTP 200/201 and returned product with assigned pk.
    """
    payload = {
        "name": "Wireless Mechanical Keyboard",
        "price": 129.99,
        "quantity": 25,
    }
    response = inventory_client.post("/inventory/product", json=payload)
    assert response.status_code in [200, 201]
    data = response.json()
    assert data["name"] == payload["name"]
    assert data["price"] == payload["price"]
    assert data["quantity"] == payload["quantity"]
    assert "pk" in data
    assert data["pk"] is not None


def test_get_product_by_pk_success(inventory_client: TestClient):
    """
    Tier 1: Verify retrieval of an existing product by primary key.
    """
    create_res = inventory_client.post(
        "/inventory/product",
        json={"name": "Gaming Mouse", "price": 59.95, "quantity": 40},
    )
    product_pk = create_res.json()["pk"]

    response = inventory_client.get(f"/inventory/product/{product_pk}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == product_pk
    assert data["name"] == "Gaming Mouse"
    assert data["price"] == 59.95
    assert data["quantity"] == 40


def test_list_all_products_success(inventory_client: TestClient):
    """
    Tier 1: Verify listing all products from the catalog.
    """
    p1 = inventory_client.post("/inventory/product", json={"name": "Monitor", "price": 299.99, "quantity": 10}).json()
    p2 = inventory_client.post("/inventory/product", json={"name": "Desk Mat", "price": 24.50, "quantity": 50}).json()

    response = inventory_client.get("/inventory/products")
    assert response.status_code == 200
    items = response.json()
    assert isinstance(items, list)
    pks = [item["id"] for item in items]
    assert p1["pk"] in pks
    assert p2["pk"] in pks


def test_update_product_partial(inventory_client: TestClient):
    """
    Tier 1: Verify partial product update via PUT /inventory/product/{pk}.
    """
    created = inventory_client.post(
        "/inventory/product",
        json={"name": "USB-C Hub", "price": 45.00, "quantity": 30},
    ).json()
    pk = created["pk"]

    # Update only price and quantity, keeping name untouched
    update_res = inventory_client.put(
        f"/inventory/product/{pk}",
        json={"price": 39.99, "quantity": 20},
    )
    assert update_res.status_code == 200
    updated_data = update_res.json()
    assert updated_data["price"] == 39.99
    assert updated_data["quantity"] == 20
    assert updated_data["name"] == "USB-C Hub"


def test_delete_product_success(inventory_client: TestClient):
    """
    Tier 1: Verify product deletion removes it from subsequent queries.
    """
    created = inventory_client.post(
        "/inventory/product",
        json={"name": "Discontinued Cable", "price": 9.99, "quantity": 5},
    ).json()
    pk = created["pk"]

    delete_res = inventory_client.delete(f"/inventory/product/{pk}")
    assert delete_res.status_code == 200
    assert delete_res.json()["name"] == "Discontinued Cable"

    # Querying the deleted product must return 404
    get_res = inventory_client.get(f"/inventory/product/{pk}")
    assert get_res.status_code == 404


def test_update_product_name_only(inventory_client: TestClient):
    """
    Tier 1: Verify updating only the product name.
    """
    created = inventory_client.post(
        "/inventory/product",
        json={"name": "Old Brand Headset", "price": 89.99, "quantity": 15},
    ).json()
    pk = created["pk"]

    update_res = inventory_client.put(
        f"/inventory/product/{pk}",
        json={"name": "New Brand Elite Headset"},
    )
    assert update_res.status_code == 200
    data = update_res.json()
    assert data["name"] == "New Brand Elite Headset"
    assert data["price"] == 89.99
    assert data["quantity"] == 15
