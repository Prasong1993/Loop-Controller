import os
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from nexus.mcp_server import app, BearerGateMiddleware
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route

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

    def test_mcp_bearer_gate_accepts_matching_token(self):
        async def ok_endpoint(request):
            return JSONResponse({"ok":True})
        gated=BearerGateMiddleware(Starlette(routes=[Route("/",ok_endpoint)]))
        client=TestClient(gated)
        with patch.dict(os.environ,{"NEXUS_API_KEY":"test-secret"}):
            response=client.get("/",headers={"Authorization":"Bearer test-secret"})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json(),{"ok":True})

if __name__ == "__main__":
    unittest.main()
