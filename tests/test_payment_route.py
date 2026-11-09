import unittest
from typing import AsyncGenerator
from fastapi.testclient import TestClient

from payment.app.db.postgresql import get_db
from payment.app.main import app
from tests.conftest import MockAsyncSession


class TestPaymentRouter(unittest.TestCase):
    """
    Integration tests for Payment Service routes with isolated in-memory database mocks.
    Eliminates brittle unmocked failures and strictly removes tolerance of 500 errors.
    """

    client: TestClient
    mock_session: MockAsyncSession

    @classmethod
    def setUpClass(cls) -> None:
        cls.mock_session = MockAsyncSession()

        async def override_get_db() -> AsyncGenerator[MockAsyncSession, None]:
            yield cls.mock_session

        app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(app)

    @classmethod
    def tearDownClass(cls) -> None:
        app.dependency_overrides.clear()

    def test_create_order_invalid_payload(self) -> None:
        """
        Test that creating an order without required fields returns 422 Unprocessable Entity.
        """
        response = self.client.post("/orders/", json={})
        self.assertEqual(response.status_code, 422)

    def test_get_non_existent_order(self) -> None:
        """
        Test that querying a non-existent order strictly returns 404 Not Found (never 500).
        """
        response = self.client.get("/orders/9999999")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Order with id 9999999 not found")

    def test_update_non_existent_order(self) -> None:
        """
        Test that updating a non-existent order returns 404 Not Found without raising 500.
        """
        response = self.client.put("/orders/8888888", json={"status": "completed"})
        self.assertEqual(response.status_code, 404)

    def test_delete_non_existent_order(self) -> None:
        """
        Test that deleting a non-existent order returns 404 Not Found.
        """
        response = self.client.delete("/orders/7777777")
        self.assertEqual(response.status_code, 404)
