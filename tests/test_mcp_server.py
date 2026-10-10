import os
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from nexus.mcp_server import app

class NexusMcpGateTests(unittest.TestCase):
    def test_remote_mcp_fails_closed_without_token(self):
        client=TestClient(app,client=("203.0.113.20",12345))
        with patch.dict(os.environ,{"NEXUS_API_KEY":""}):
            response=client.post("/mcp",json={})
        self.assertEqual(response.status_code,503)

    def test_mcp_requires_bearer_token_when_configured(self):
        client=TestClient(app)
        with patch.dict(os.environ,{"NEXUS_API_KEY":"test-secret"}):
            response=client.post("/mcp",json={})
        self.assertEqual(response.status_code,401)

    def test_mcp_accepts_matching_bearer_at_gate(self):
        client=TestClient(app)
        with patch.dict(os.environ,{"NEXUS_API_KEY":"test-secret"}):
            with TestClient(app) as live_client:
                response=live_client.post("/mcp",json={},headers={"Authorization":"Bearer test-secret"})
        # Authentication succeeds; the MCP protocol may reject an empty JSON-RPC payload.
        self.assertNotEqual(response.status_code,401)
        self.assertNotEqual(response.status_code,503)

if __name__ == "__main__":
    unittest.main()
