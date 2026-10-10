import tempfile
import unittest
from pathlib import Path
from nexus.core import NEXUS, PolicyDenied, InvalidTransition

class NexusCoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.n=NEXUS(str(Path(self.tmp.name)/"test.db"))
        self.project=self.n.create_project("test-project")["project_id"]
    def test_task_starts_at_intake(self):
        self.assertEqual(self.n.create_task(self.project,"demo")["state"],"INTAKE")
    def test_unknown_evidence_cannot_satisfy_research_gate(self):
        t=self.n.create_task(self.project,"demo")
        self.n.transition(t["task_id"],"RESEARCH")
        self.n.add_evidence(self.project,"claim","UNKNOWN","https://example.com")
        with self.assertRaises(PolicyDenied): self.n.transition(t["task_id"],"PLAN")
    def test_verified_evidence_requires_source(self):
        with self.assertRaises(PolicyDenied): self.n.add_evidence(self.project,"claim","VERIFIED")
    def test_invalid_transition_denied(self):
        t=self.n.create_task(self.project,"demo")
        with self.assertRaises(InvalidTransition): self.n.transition(t["task_id"],"COMPLETE")
    def test_execute_requires_acceptance_and_verification(self):
        t=self.n.create_task(self.project,"demo")
        self.n.transition(t["task_id"],"RESEARCH")
        self.n.add_evidence(self.project,"official fact","VERIFIED","https://example.com")
        self.n.transition(t["task_id"],"PLAN"); self.n.transition(t["task_id"],"POLICY")
        with self.assertRaises(PolicyDenied): self.n.transition(t["task_id"],"EXECUTE")
    def test_complete_requires_audited_result(self):
        t=self.n.create_task(self.project,"demo","expected","manual check")
        self.n.transition(t["task_id"],"RESEARCH")
        self.n.add_evidence(self.project,"official fact","VERIFIED","https://example.com")
        self.n.transition(t["task_id"],"PLAN"); self.n.transition(t["task_id"],"POLICY")
        self.n.transition(t["task_id"],"EXECUTE"); self.n.transition(t["task_id"],"VERIFY")
        self.n.transition(t["task_id"],"AUDIT")
        with self.assertRaises(PolicyDenied): self.n.transition(t["task_id"],"COMPLETE")
        self.n.transition(t["task_id"],"COMPLETE",result="verified output")
        self.assertEqual(self.n.get_task(t["task_id"])["state"],"COMPLETE")
    def test_router_free_first_and_paid_approval(self):
        paid={"id":"paid","enabled":True,"permission_ok":True,"capability_ok":True,"cost_tier":"paid"}
        free={"id":"free","enabled":True,"permission_ok":True,"capability_ok":True,"cost_tier":"free"}
        self.assertEqual(self.n.policy_route([paid,free])["selected"],"free")
        self.assertEqual(self.n.policy_route([paid])["decision"],"BLOCK")
        self.assertEqual(self.n.policy_route([paid],True,True)["selected"],"paid")
    def test_warning_candidate_is_blocked(self):
        c={"id":"tool","enabled":True,"permission_ok":True,"capability_ok":True,"cost_tier":"free","warning":True}
        self.assertEqual(self.n.policy_route([c])["decision"],"BLOCK")
    def test_audit_created_for_transitions(self):
        t=self.n.create_task(self.project,"audit"); self.n.transition(t["task_id"],"RESEARCH")
        self.assertGreaterEqual(len(self.n.audit(self.project,t["task_id"])),2)
    def test_unknown_project_rejected(self):
        with self.assertRaises(ValueError): self.n.create_task("missing-project","fail")

if __name__=="__main__": unittest.main()
