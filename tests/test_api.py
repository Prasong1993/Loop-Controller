import os
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from nexus.api import app

class NexusApiTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.env = patch.dict(os.environ, {}, clear=False)
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_health_is_public_and_minimal(self):
        with patch.dict(os.environ, {"NEXUS_API_KEY":""}):
            response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_remote_request_fails_closed_without_key(self):
        with patch.dict(os.environ, {"NEXUS_API_KEY":""}):
            client = TestClient(app, client=("203.0.113.10", 12345))
            response = client.post("/projects", json={"name":"remote"})
        self.assertEqual(response.status_code, 503)

    def test_configured_key_required_and_accepted(self):
        with patch.dict(os.environ, {"NEXUS_API_KEY":"test-secret"}):
            denied = self.client.post("/projects", json={"name":"no-token"})
            accepted = self.client.post("/projects", json={"name":"with-token"},
                                        headers={"Authorization":"Bearer test-secret"})
        self.assertEqual(denied.status_code, 401)
        self.assertEqual(accepted.status_code, 201)

    def test_unknown_task_maps_to_404(self):
        with patch.dict(os.environ, {"NEXUS_API_KEY":"test-secret"}):
            response = self.client.get("/tasks/not-a-real-task",
                                       headers={"Authorization":"Bearer test-secret"})
        self.assertEqual(response.status_code, 404)

if __name__ == "__main__":
    unittest.main()
