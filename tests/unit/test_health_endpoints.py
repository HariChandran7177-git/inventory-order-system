import pytest
from fastapi.testclient import TestClient


def test_inventory_health_ok(inventory_client: TestClient):
    """
    Tier 1: Verify Inventory GET /health returns HTTP 200 and healthy status.
    """
    response = inventory_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "inventory"


def test_payment_health_ok(payment_client: TestClient):
    """
    Tier 1: Verify Payment GET /health returns HTTP 200 and healthy status.
    """
    response = payment_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "payment"


def test_inventory_health_method_not_allowed(inventory_client: TestClient):
    """
    Tier 1: Verify health endpoints reject non-GET requests with HTTP 405.
    """
    post_res = inventory_client.post("/health", json={"ping": "pong"})
    assert post_res.status_code == 405

    delete_res = inventory_client.delete("/health")
    assert delete_res.status_code == 405


def test_payment_health_method_not_allowed(payment_client: TestClient):
    """
    Tier 1: Verify Payment /health rejects non-GET methods with HTTP 405.
    """
    post_res = payment_client.post("/health", json={})
    assert post_res.status_code == 405

    put_res = payment_client.put("/health", json={})
    assert put_res.status_code == 405


def test_health_response_schema_and_headers(inventory_client: TestClient, payment_client: TestClient):
    """
    Tier 1: Verify health responses conform strictly to JSON schema and Content-Type.
    """
    for client, expected_service in [(inventory_client, "inventory"), (payment_client, "payment")]:
        res = client.get("/health")
        assert res.status_code == 200
        assert "application/json" in res.headers.get("content-type", "")
        payload = res.json()
        assert isinstance(payload, dict)
        assert payload.get("status") == "ok"
        assert payload.get("service") == expected_service
