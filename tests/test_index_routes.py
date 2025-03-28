import sys
import os
import unittest
from unittest.mock import patch
from app import create_app
from config import TestConfig

# Ensure the project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class TestIndexRoutes(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()

    def test_home_exception(self):
        # Patch render_template so that it raises an Exception.
        with patch(
            "routes.index_routes.render_template", side_effect=Exception("Test error")
        ):
            response = self.client.get("/")
            self.assertEqual(response.status_code, 500)
            self.assertIn(b"Test error", response.data)

    def test_dashboard_exception(self):
        # Patch render_template for the dashboard route.
        with patch(
            "routes.index_routes.render_template",
            side_effect=Exception("Dashboard error"),
        ):
            response = self.client.get("/dashboard")
            self.assertEqual(response.status_code, 500)
            self.assertIn(b"Dashboard error", response.data)

    def test_home_route(self):
        # Check that GET "/" returns a 200 status code
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_dashboard_route(self):
        # Check that GET "/dashboard" returns a 200 status code
        response = self.client.get("/dashboard")
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
