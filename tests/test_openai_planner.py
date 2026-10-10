import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from nexus.openai_planner import OpenAIPlanGenerator, OpenAIPlanError
from nexus.records import RecordStore

class FakeResponses:
    def __init__(self, response=None, error=None):
        self.response, self.error, self.kwargs = response, error, None
    def create(self, **kwargs):
        self.kwargs = kwargs
        if self.error:
            raise self.error
        return self.response

class OpenAIPlanTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.store=RecordStore(str(Path(self.tmp.name)/"records.db"))
        self.proposal={"goal":"test","assumptions":[],"steps":[
            {"step_id":"S1","action":"inspect","capability":"responses","inputs":[],
             "expected_output":"report","verification":"check report","side_effect":"none",
             "evidence_required":[]}],"risks":[],"blocked_questions":[]}
        self.fake=FakeResponses(SimpleNamespace(output_text=json.dumps(self.proposal),id="resp-1",
            usage=SimpleNamespace(input_tokens=4,output_tokens=8,total_tokens=12)))
        self.client=SimpleNamespace(responses=self.fake)

    def test_budget_gate_blocks_without_provider_call(self):
        planner=OpenAIPlanGenerator(self.store,client=self.client,api_key="fake")
        with self.assertRaises(OpenAIPlanError) as ctx:
            planner.propose(project_id="p1",task="test")
        self.assertEqual(ctx.exception.code,"OPENAI_BUDGET_APPROVAL_REQUIRED")
        self.assertIsNone(self.fake.kwargs)
        self.assertEqual(self.store.search(project_id="p1",record_type="decision")["total"],1)

    def test_structured_proposal_is_not_authorized(self):
        planner=OpenAIPlanGenerator(self.store,client=self.client,api_key="fake")
        result=planner.propose(project_id="p1",task="test",budget_approved=True,
                               capabilities=["web_search"])
        self.assertEqual(result["status"],"PROPOSAL_ONLY")
        self.assertEqual(result["policy_decision"],"NOT_EVALUATED")
        self.assertEqual(self.fake.kwargs["text"]["format"]["type"],"json_schema")
        self.assertEqual(self.fake.kwargs["tools"],[{"type":"web_search"}])
        self.assertEqual(self.store.search(project_id="p1",record_type="usage")["total"],1)

    def test_default_model_uses_current_cost_sensitive_catalog_entry(self):
        planner=OpenAIPlanGenerator(self.store,client=self.client,api_key="fake")
        self.assertEqual(planner.model,"gpt-6-luna")
    def test_web_search_rejected_for_unreviewed_model_override(self):
        planner=OpenAIPlanGenerator(self.store,client=self.client,model="unreviewed-model",api_key="fake")
        with self.assertRaisesRegex(ValueError,"not verified for model"):
            planner.propose(project_id="p1",task="research",budget_approved=True,capabilities=["web_search"])
        self.assertIsNone(self.fake.kwargs)
    def test_code_interpreter_not_enabled_without_verified_model_support(self):
        planner=OpenAIPlanGenerator(self.store,client=self.client,api_key="fake")
        with self.assertRaises(ValueError):
            planner.propose(project_id="p1",task="run code",budget_approved=True,capabilities=["code_interpreter"])
        self.assertIsNone(self.fake.kwargs)
    def test_no_optional_tool_omits_tools_parameter(self):
        planner=OpenAIPlanGenerator(self.store,client=self.client,api_key="fake")
        planner.propose(project_id="p1",task="test",budget_approved=True)
        self.assertNotIn("tools",self.fake.kwargs)
    def test_unknown_capability_rejected(self):
        planner=OpenAIPlanGenerator(self.store,client=self.client,api_key="fake")
        with self.assertRaises(ValueError):
            planner.propose(project_id="p1",task="test",budget_approved=True,capabilities=["fine_tuning"])
        self.assertIsNone(self.fake.kwargs)

    def test_provider_error_is_redacted_and_recorded(self):
        planner=OpenAIPlanGenerator(self.store,client=SimpleNamespace(responses=FakeResponses(error=RuntimeError("secret provider body"))),api_key="fake")
        with self.assertRaises(OpenAIPlanError):
            planner.propose(project_id="p1",task="test",budget_approved=True)
        results=self.store.search(project_id="p1",record_type="error")
        self.assertEqual(results["total"],1)
        self.assertNotIn("secret provider body",json.dumps(results))

if __name__=="__main__": unittest.main()
