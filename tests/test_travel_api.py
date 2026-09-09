"""API contract checks without database access or paid travel service calls."""
import importlib.util
from pathlib import Path
import sys
from types import ModuleType
import unittest
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient


class TravelApiTests(unittest.TestCase):
    def setUp(self):
        backend = ModuleType("backend")
        self.agent = backend.run_travel_agent = Mock()
        spec = importlib.util.spec_from_file_location(
            "travel_app_test", Path(__file__).resolve().parents[1] / "app.py"
        )
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"backend": backend}):
            spec.loader.exec_module(module)
        self.client = TestClient(module.app)
        self.addCleanup(self.client.close)

    def test_live_server_cors(self):
        for origin in ["http://127.0.0.1:5500", "http://localhost:5500"]:
            response = self.client.options("/api/travel", headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            })
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["access-control-allow-origin"], origin)
            response = self.client.post("/api/travel", json={"message": ""}, headers={"Origin": origin})
            self.assertEqual(response.headers["access-control-allow-origin"], origin)

    def test_unrelated_origin_is_not_allowed(self):
        response = self.client.options("/api/travel", headers={
            "Origin": "https://unrelated.example", "Access-Control-Request-Method": "POST",
        })
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("access-control-allow-origin", response.headers)

    def test_success(self):
        self.agent.return_value = {
            "thread_id": "trip-1", "answer": "Travel plan", "flight_results": "",
            "hotel_results": "", "itinerary": "", "llm_calls": 4,
        }
        response = self.client.post("/api/travel", json={"message": " Japan "})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["success"])
        self.assertEqual(response.json()["answer"], "Travel plan")
        self.agent.assert_called_once_with(user_input="Japan", thread_id=None)

    def test_empty_message(self):
        response = self.client.post("/api/travel", json={"message": " "})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json()["success"])
        self.agent.assert_not_called()

    def test_agent_error_returns_json(self):
        self.agent.side_effect = RuntimeError("Travel service unavailable")
        with patch("builtins.print"), patch("traceback.print_exc"):
            response = self.client.post("/api/travel", json={"message": "Japan"})
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json()["error"], "Travel service unavailable")

    def test_missing_message(self):
        response = self.client.post("/api/travel", json={})
        self.assertEqual(response.status_code, 422)
        self.assertIn("detail", response.json())
        self.agent.assert_not_called()


if __name__ == "__main__":
    unittest.main()
