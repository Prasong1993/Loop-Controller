import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from nexus.code_proposal import OpenAICodeProposalGenerator, CodeProposalError
from nexus.records import RecordStore

class FakeResponses:
    def __init__(self, response=None, error=None):
        self.response=response
        self.error=error
        self.kwargs=None
    def create(self, **kwargs):
        self.kwargs=kwargs
        if self.error:
            raise self.error
        return self.response

class CodeProposalTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.store=RecordStore(str(Path(self.tmp.name)/"records.db"))
        self.proposal={"goal":"add helper","files":[
            {"path":"nexus/helper.py","operation":"create","content":"def helper(): return True\n",
             "rationale":"small deterministic helper"}],
            "tests":["test_helper"],"risks":[],"blocked_questions":[]}
        self.fake=FakeResponses(SimpleNamespace(output_text=json.dumps(self.proposal),id="code-resp",
            usage=SimpleNamespace(input_tokens=30,output_tokens=50,total_tokens=80)))
        self.client=SimpleNamespace(responses=self.fake)

    def test_budget_gate_blocks_before_provider_call(self):
        gen=OpenAICodeProposalGenerator(self.store,client=self.client)
        with self.assertRaises(CodeProposalError) as ctx:
            gen.propose(project_id="p1",task="add helper",allowed_paths=["nexus/helper.py"])
        self.assertEqual(ctx.exception.code,"OPENAI_BUDGET_APPROVAL_REQUIRED")
        self.assertIsNone(self.fake.kwargs)
        self.assertEqual(self.store.search(project_id="p1",record_type="decision")["total"],1)

    def test_code_is_returned_as_proposal_and_not_written_to_records(self):
        gen=OpenAICodeProposalGenerator(self.store,client=self.client)
        result=gen.propose(project_id="p1",task="add helper",allowed_paths=["nexus/helper.py"],
                           task_id="t1",budget_approved=True)
        self.assertEqual(result["status"],"PROPOSAL_ONLY")
        self.assertEqual(result["policy_decision"],"NOT_EVALUATED")
        self.assertEqual(result["model"],"gpt-6-astra")
        self.assertEqual(result["usage"]["total_tokens"],80)
        self.assertEqual(self.fake.kwargs["text"]["format"]["type"],"json_schema")
        self.assertNotIn("tools",self.fake.kwargs)
        records=self.store.search(project_id="p1",record_type="usage")
        self.assertEqual(records["total"],1)
        self.assertNotIn("def helper",json.dumps(records))
        self.assertEqual(records["records"][0]["task_id"],"t1")

    def test_unapproved_proposed_path_is_blocked_and_recorded(self):
        bad={"goal":"escape","files":[{"path":"../../.env","operation":"update","content":"secret","rationale":"bad"}],
             "tests":[],"risks":[],"blocked_questions":[]}
        fake=FakeResponses(SimpleNamespace(output_text=json.dumps(bad),id="bad-resp"))
        gen=OpenAICodeProposalGenerator(self.store,client=SimpleNamespace(responses=fake))
        with self.assertRaises(CodeProposalError) as ctx:
            gen.propose(project_id="p1",task="change code",allowed_paths=["nexus/helper.py"],budget_approved=True)
        self.assertEqual(ctx.exception.code,"CODE_PATH_NOT_ALLOWED")
        self.assertEqual(self.store.search(project_id="p1",record_type="decision")["total"],1)

    def test_unsafe_allowlist_rejected_before_provider_call(self):
        gen=OpenAICodeProposalGenerator(self.store,client=self.client)
        with self.assertRaises(ValueError):
            gen.propose(project_id="p1",task="change code",allowed_paths=["../secrets/key"])
        self.assertIsNone(self.fake.kwargs)

    def test_unreviewed_code_model_rejected_before_provider_call(self):
        gen=OpenAICodeProposalGenerator(self.store,client=self.client,model="gpt-6-luna")
        with self.assertRaisesRegex(ValueError,"not verified for model"):
            gen.propose(project_id="p1",task="change code",allowed_paths=["nexus/helper.py"],budget_approved=True)
        self.assertIsNone(self.fake.kwargs)

if __name__=="__main__": unittest.main()
