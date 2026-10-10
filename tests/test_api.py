import os
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
from nexus.api import app
from unittest.mock import patch

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


    def test_direct_verified_evidence_is_denied(self):
        with patch.dict(os.environ, {"NEXUS_API_KEY":"test-secret"}):
            project = self.client.post("/projects", json={"name":"evidence-deny"},
                                       headers={"Authorization":"Bearer test-secret"}).json()
            response = self.client.post("/evidence", json={"project_id":project["project_id"],
                "claim":"claim","status":"VERIFIED","source_url":"https://example.com"},
                headers={"Authorization":"Bearer test-secret"})
        self.assertEqual(response.status_code, 403)

    def test_verified_evidence_endpoint_requires_matching_quote(self):
        with patch.dict(os.environ, {"NEXUS_API_KEY":"test-secret"}):
            project = self.client.post("/projects", json={"name":"evidence-verify"},
                                       headers={"Authorization":"Bearer test-secret"}).json()
            with patch("nexus.evidence.verify_source_quote", return_value={
                "source_text":"Exact policy quote appears here.","quoted_text":"Exact policy quote",
                "source_chars":32,"method":"exact normalized quote match","source_url":"https://example.com"}):
                response = self.client.post("/evidence/verify", json={"project_id":project["project_id"],
                    "claim":"policy claim","source_url":"https://example.com","quoted_text":"Exact policy quote"},
                    headers={"Authorization":"Bearer test-secret"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "VERIFIED")

    def test_unknown_task_maps_to_404(self):
        with patch.dict(os.environ, {"NEXUS_API_KEY":"test-secret"}):
            response = self.client.get("/tasks/not-a-real-task",
                                       headers={"Authorization":"Bearer test-secret"})
        self.assertEqual(response.status_code, 404)


    def test_ai_plan_is_blocked_without_explicit_paid_budget_approval(self):
        with patch.dict(os.environ, {"NEXUS_API_KEY":"test-secret","NEXUS_OPENAI_BUDGET_APPROVED":"false"}):
            response=self.client.post("/ai/plan",json={"project_id":"p-test","task":"draft a plan","budget_approved":True},
                                      headers={"Authorization":"Bearer test-secret"})
        self.assertEqual(response.status_code,403)
        self.assertEqual(response.json()["detail"]["code"],"OPENAI_BUDGET_APPROVAL_REQUIRED")

    def test_ai_run_is_blocked_without_explicit_paid_budget_approval(self):
        with patch.dict(os.environ, {"NEXUS_API_KEY":"test-secret","NEXUS_OPENAI_BUDGET_APPROVED":"false"}):
            response=self.client.post("/ai/run",json={"project_id":"p-test","prompt":"read status","budget_approved":True},
                                      headers={"Authorization":"Bearer test-secret"})
        self.assertEqual(response.status_code,403)

    def test_record_search_endpoint_returns_scoped_page(self):
        from nexus.api import record_store
        record_store.append(project_id="search-test",record_type="usage",payload={"operation":"unit-test"},
                            summary="search endpoint test")
        with patch.dict(os.environ, {"NEXUS_API_KEY":"test-secret"}):
            response=self.client.get("/records/search?project_id=search-test&record_type=usage",
                                     headers={"Authorization":"Bearer test-secret"})
        self.assertEqual(response.status_code,200)
        self.assertGreaterEqual(response.json()["total"],1)
        self.assertEqual(response.json()["project_id"],"search-test")

if __name__ == "__main__":
    unittest.main()
