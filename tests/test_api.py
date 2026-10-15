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

    def test_record_search_applies_task_id_filter(self):
        from nexus.api import record_store
        record_store.append(project_id="task-filter-test",task_id="task-a",record_type="usage",
                            payload={"operation":"task-a"},summary="task A record")
        record_store.append(project_id="task-filter-test",task_id="task-b",record_type="usage",
                            payload={"operation":"task-b"},summary="task B record")
        with patch.dict(os.environ, {"NEXUS_API_KEY":"test-secret"}):
            response=self.client.get("/records/search?project_id=task-filter-test&task_id=task-a",
                                     headers={"Authorization":"Bearer test-secret"})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()["total"],1)
        self.assertEqual([row["task_id"] for row in response.json()["records"]],["task-a"])


    def test_record_search_task_id_filter_excludes_other_tasks(self):
        from nexus.api import record_store
        project_id = "task-filter-regression"
        record_store.append(project_id=project_id, task_id="task-a", record_type="usage",
                            payload={"operation":"task-a"}, summary="task a record")
        record_store.append(project_id=project_id, task_id="task-b", record_type="usage",
                            payload={"operation":"task-b"}, summary="task b record")
        with patch.dict(os.environ, {"NEXUS_API_KEY":"test-secret"}):
            response = self.client.get(
                "/records/search?project_id=task-filter-regression&task_id=task-a",
                headers={"Authorization":"Bearer test-secret"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["total"], 1)
        self.assertTrue(all(row["task_id"] == "task-a" for row in response.json()["records"]))

    def test_evidence_quote_mismatch_maps_to_422(self):
        from nexus.evidence import EvidenceFetchError
        with patch.dict(os.environ, {"NEXUS_API_KEY":"test-secret"}):
            project = self.client.post("/projects", json={"name":"evidence-mismatch"},
                                       headers={"Authorization":"Bearer test-secret"}).json()
            with patch("nexus.evidence.verify_source_quote", side_effect=EvidenceFetchError("quote mismatch")):
                response = self.client.post("/evidence/verify", json={"project_id":project["project_id"],
                    "claim":"claim","source_url":"https://example.com","quoted_text":"not in source"},
                    headers={"Authorization":"Bearer test-secret"})
        self.assertEqual(response.status_code,422)

    def test_ai_run_policy_blocks_cross_project_tool_request(self):
        seen = {}
        class FakeWorker:
            def __init__(self, *, model):
                seen["model"] = model
            def run(self, **kwargs):
                seen["tool_names"] = [tool["name"] for tool in kwargs["tools"]]
                seen["decision"] = kwargs["policy_check"](
                    "nexus_get_project_status", {"project_id":"different-project"})
                return {"response_id":"fake-response","output_text":"blocked","tool_calls":[],
                        "policy_decisions":[seen["decision"]],"rounds":1,"usage":{}}
        with patch.dict(os.environ, {"NEXUS_API_KEY":"test-secret","NEXUS_OPENAI_BUDGET_APPROVED":"true"}):
            with patch("nexus.api.OpenAIResponsesWorker", FakeWorker):
                response=self.client.post("/ai/run",json={"project_id":"active-project",
                    "prompt":"read status","budget_approved":True},
                    headers={"Authorization":"Bearer test-secret","x-request-id":"test-trace-01"})
        self.assertEqual(response.status_code,200)
        self.assertEqual(seen["decision"]["decision"],"BLOCK")
        self.assertEqual(seen["decision"]["reason_code"],"PROJECT_SCOPE_MISMATCH")
        self.assertEqual(set(seen["tool_names"]),{
            "nexus_get_project_status","nexus_read_audit","nexus_get_task"})
        self.assertEqual(response.json()["trace_id"],"test-trace-01")
        from nexus.api import record_store
        scoped=record_store.search(project_id="active-project",record_type="usage",component="rest_api")
        self.assertGreaterEqual(scoped["total"],1)
        self.assertTrue(any(row["trace_id"]=="test-trace-01" for row in scoped["records"]))


    def test_rest_lifecycle_runs_through_verified_completion(self):
        headers={"Authorization":"Bearer test-secret","x-request-id":"lifecycle-trace"}
        with patch.dict(os.environ, {"NEXUS_API_KEY":"test-secret"}):
            project_response=self.client.post("/projects",json={"name":"rest-e2e-project"},headers=headers)
            self.assertEqual(project_response.status_code,201)
            project_id=project_response.json()["project_id"]
            task_response=self.client.post("/tasks",json={"project_id":project_id,"title":"rest-e2e",
                "expected_outcome":"verified result","verification_method":"assert final state"},
                headers=headers)
            self.assertEqual(task_response.status_code,201)
            task_id=task_response.json()["task_id"]
            for state in ["RESEARCH"]:
                response=self.client.post(f"/tasks/{task_id}/transition",json={"to_state":state},headers=headers)
                self.assertEqual(response.status_code,200,response.text)
            with patch("nexus.evidence.verify_source_quote",return_value={
                "source_text":"official quote","quoted_text":"official quote","source_chars":14,
                "method":"exact normalized quote match","source_url":"https://example.com"}):
                evidence=self.client.post("/evidence/verify",json={"project_id":project_id,
                    "claim":"source-backed claim","source_url":"https://example.com",
                    "quoted_text":"official quote","task_id":task_id},headers=headers)
            self.assertEqual(evidence.status_code,200,evidence.text)
            self.assertEqual(evidence.json()["status"],"VERIFIED")
            for state in ["PLAN","POLICY","EXECUTE","VERIFY","AUDIT"]:
                response=self.client.post(f"/tasks/{task_id}/transition",json={"to_state":state},headers=headers)
                self.assertEqual(response.status_code,200,response.text)
            completed=self.client.post(f"/tasks/{task_id}/transition",json={
                "to_state":"COMPLETE","result":"verified result"},headers=headers)
            self.assertEqual(completed.status_code,200,completed.text)
            self.assertEqual(completed.json()["state"],"COMPLETE")
            audit=self.client.get(f"/projects/{project_id}/audit?task_id={task_id}",headers=headers)
            self.assertEqual(audit.status_code,200)
            self.assertIn("EVIDENCE_VERIFIED",[event["event_type"] for event in audit.json()])
            records=self.client.get(f"/records/search?project_id={project_id}&task_id={task_id}&component=rest_api",headers=headers)
            self.assertEqual(records.status_code,200)
            self.assertGreaterEqual(records.json()["total"],1)
            self.assertTrue(all(row["project_id"]==project_id for row in records.json()["records"]))


    def test_code_proposal_requires_server_and_request_budget_gate(self):
        with patch.dict(os.environ, {"NEXUS_API_KEY":"test-secret","NEXUS_OPENAI_BUDGET_APPROVED":"false"}):
            project=self.client.post("/projects",json={"name":"code-budget"},headers={"Authorization":"Bearer test-secret"}).json()
            with patch("nexus.api.code_proposal_generator._client",side_effect=AssertionError("provider must not be called")):
                response=self.client.post("/ai/code-proposal",json={"project_id":project["project_id"],
                    "task":"add a helper","allowed_paths":["nexus/helper.py"],"budget_approved":True},
                    headers={"Authorization":"Bearer test-secret"})
        self.assertEqual(response.status_code,403)
        self.assertEqual(response.json()["detail"]["code"],"OPENAI_BUDGET_APPROVAL_REQUIRED")

    def test_code_proposal_rejects_cross_project_task_before_provider_call(self):
        with patch.dict(os.environ, {"NEXUS_API_KEY":"test-secret","NEXUS_OPENAI_BUDGET_APPROVED":"true"}):
            project_a=self.client.post("/projects",json={"name":"code-scope-a"},headers={"Authorization":"Bearer test-secret"}).json()
            project_b=self.client.post("/projects",json={"name":"code-scope-b"},headers={"Authorization":"Bearer test-secret"}).json()
            task=self.client.post("/tasks",json={"project_id":project_b["project_id"],"title":"foreign",
                "expected_outcome":"x","verification_method":"y"},headers={"Authorization":"Bearer test-secret"}).json()
            with patch("nexus.api.code_proposal_generator.propose",side_effect=AssertionError("provider must not be called")):
                response=self.client.post("/ai/code-proposal",json={"project_id":project_a["project_id"],
                    "task_id":task["task_id"],"task":"change code","allowed_paths":["nexus/helper.py"],
                    "budget_approved":True},headers={"Authorization":"Bearer test-secret"})
        self.assertEqual(response.status_code,403)
        self.assertEqual(response.json()["detail"]["code"],"PROJECT_SCOPE_MISMATCH")


    def test_code_proposal_endpoint_returns_proposal_only(self):
        with patch.dict(os.environ, {"NEXUS_API_KEY":"test-secret","NEXUS_OPENAI_BUDGET_APPROVED":"true"}):
            project=self.client.post("/projects",json={"name":"code-proposal-api"},headers={"Authorization":"Bearer test-secret"}).json()
            with patch("nexus.api.code_proposal_generator.propose",return_value={
                "status":"PROPOSAL_ONLY","project_id":project["project_id"],"task_id":None,
                "trace_id":"code-trace","policy_decision":"NOT_EVALUATED","proposal":{"files":[]}}) as propose:
                response=self.client.post("/ai/code-proposal",json={"project_id":project["project_id"],
                    "task":"add a helper","allowed_paths":["nexus/helper.py"],"budget_approved":True},
                    headers={"Authorization":"Bearer test-secret","x-request-id":"code-trace"})
        self.assertEqual(response.status_code,200,response.text)
        self.assertEqual(response.json()["status"],"PROPOSAL_ONLY")
        self.assertEqual(response.json()["policy_decision"],"NOT_EVALUATED")
        self.assertEqual(propose.call_args.kwargs["allowed_paths"],["nexus/helper.py"])
        self.assertEqual(propose.call_args.kwargs["trace_id"],"code-trace")

if __name__ == "__main__":
    unittest.main()
