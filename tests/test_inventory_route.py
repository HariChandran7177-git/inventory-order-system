import unittest
import pytest
from fastapi.testclient import TestClient

from inventory.app.main import app


class TestInventoryRouter(unittest.TestCase):
    """
    Integration tests for Inventory Service routes using isolated in-memory test environment.
    """

    client: TestClient

    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def test_non_existent_route(self) -> None:
        """
        Test that a non-existent endpoint returns 404 Not Found.
        """
        response = self.client.get("/group/")
        self.assertEqual(response.status_code, 404)
        self.assertDictEqual(response.json(), {"detail": "Not Found"})

    def test_get_product_not_found(self) -> None:
        """
        Test that fetching a non-existent product ID returns 404 cleanly.
        """
        response = self.client.get("/inventory/product/non_existent_pk_12345")
        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertIn("detail", data)
