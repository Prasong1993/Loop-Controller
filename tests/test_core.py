import tempfile
import sqlite3
import unittest
from pathlib import Path
from unittest.mock import patch
from nexus.core import NEXUS, PolicyDenied, InvalidTransition

class NexusCoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.n=NEXUS(str(Path(self.tmp.name)/"test.db"))
        self.project=self.n.create_project("test-project")["project_id"]
    def add_verified(self, claim):
        with patch("nexus.evidence.verify_source_quote", return_value={
            "source_text":claim,"quoted_text":claim,"source_chars":len(claim),
            "method":"exact normalized quote match","source_url":"https://example.com"}):
            return self.n.verify_and_add_evidence(self.project,claim,"https://example.com",claim)
    def test_legacy_evidence_table_migrates_task_scope_column(self):
        legacy_path=str(Path(self.tmp.name)/"legacy.db")
        with sqlite3.connect(legacy_path) as con:
            con.execute("CREATE TABLE projects(project_id TEXT PRIMARY KEY,name TEXT NOT NULL,created_at TEXT NOT NULL)")
            con.execute("CREATE TABLE tasks(task_id TEXT PRIMARY KEY,project_id TEXT NOT NULL REFERENCES projects(project_id),title TEXT NOT NULL,state TEXT NOT NULL,expected_outcome TEXT NOT NULL DEFAULT '',verification_method TEXT NOT NULL DEFAULT '',result TEXT NOT NULL DEFAULT '',error_code TEXT NOT NULL DEFAULT '',created_at TEXT NOT NULL,updated_at TEXT NOT NULL)")
            con.execute("CREATE TABLE evidence(evidence_id TEXT PRIMARY KEY,project_id TEXT NOT NULL REFERENCES projects(project_id),claim TEXT NOT NULL,status TEXT NOT NULL,source_url TEXT,inspected_at TEXT,notes TEXT NOT NULL DEFAULT '')")
        migrated=NEXUS(legacy_path)
        with sqlite3.connect(legacy_path) as con:
            columns={row[1] for row in con.execute("PRAGMA table_info(evidence)")}
        self.assertIn("task_id",columns)
        self.assertIsNotNone(migrated)
    def test_task_starts_at_intake(self):
        self.assertEqual(self.n.create_task(self.project,"demo")["state"],"INTAKE")
    def test_unknown_evidence_cannot_satisfy_research_gate(self):
        t=self.n.create_task(self.project,"demo")
        self.n.transition(t["task_id"],"RESEARCH")
        self.n.add_evidence(self.project,"claim","UNKNOWN","https://example.com")
        with self.assertRaises(PolicyDenied): self.n.transition(t["task_id"],"PLAN")
    def test_verified_evidence_requires_source(self):
        with self.assertRaises(PolicyDenied): self.n.add_evidence(self.project,"claim","VERIFIED")
    def test_caller_supplied_source_text_cannot_create_verified_evidence(self):
        with self.assertRaises(PolicyDenied):
            self.n.add_verified_evidence(self.project,"claim","https://example.com","claim","fabricated claim")
    def test_task_specific_evidence_does_not_unlock_other_task(self):
        task_a=self.n.create_task(self.project,"task A","result","verify")
        task_b=self.n.create_task(self.project,"task B","result","verify")
        self.n.transition(task_b["task_id"],"RESEARCH")
        with patch("nexus.evidence.verify_source_quote",return_value={
            "source_text":"source","quoted_text":"source","source_chars":6,
            "method":"exact normalized quote match","source_url":"https://example.com"}):
            self.n.verify_and_add_evidence(self.project,"A-specific claim","https://example.com","source",task_id=task_a["task_id"])
        with self.assertRaises(PolicyDenied):
            self.n.transition(task_b["task_id"],"PLAN")
    def test_task_specific_evidence_rejects_cross_project_task(self):
        other=self.n.create_project("other-project")["project_id"]
        other_task=self.n.create_task(other,"other task")
        with patch("nexus.evidence.verify_source_quote",return_value={
            "source_text":"source","quoted_text":"source","source_chars":6,
            "method":"exact normalized quote match","source_url":"https://example.com"}):
            with self.assertRaises(ValueError):
                self.n.verify_and_add_evidence(self.project,"claim","https://example.com","source",task_id=other_task["task_id"])
    def test_invalid_transition_denied(self):
        t=self.n.create_task(self.project,"demo")
        with self.assertRaises(InvalidTransition): self.n.transition(t["task_id"],"COMPLETE")
    def test_recovery_cannot_skip_directly_to_execute(self):
        t=self.n.create_task(self.project,"recovery gate","expected result","manual verification")
        self.n.transition(t["task_id"],"BLOCKED",reason="simulate interruption")
        self.n.transition(t["task_id"],"RECOVER",reason="begin recovery")
        with self.assertRaises(InvalidTransition):
            self.n.transition(t["task_id"],"EXECUTE",reason="must replan and pass policy first")

    def test_execute_requires_acceptance_and_verification(self):
        t=self.n.create_task(self.project,"demo")
        self.n.transition(t["task_id"],"RESEARCH")
        self.add_verified("official fact")
        self.n.transition(t["task_id"],"PLAN"); self.n.transition(t["task_id"],"POLICY")
        with self.assertRaises(PolicyDenied): self.n.transition(t["task_id"],"EXECUTE")
    def test_complete_requires_persisted_verification_and_audited_result(self):
        t=self.n.create_task(self.project,"demo","expected","manual check")
        self.n.transition(t["task_id"],"RESEARCH")
        evidence=self.add_verified("official result evidence")
        self.n.transition(t["task_id"],"PLAN"); self.n.transition(t["task_id"],"POLICY")
        self.n.transition(t["task_id"],"EXECUTE"); self.n.transition(t["task_id"],"VERIFY")
        self.n.transition(t["task_id"],"AUDIT")
        with self.assertRaisesRegex(PolicyDenied,"persisted passing verification"):
            self.n.transition(t["task_id"],"COMPLETE",result="verified output")
        self.assertEqual(self.n.get_verifications(t["task_id"]),[])
        self.n.transition(t["task_id"],"RECOVER",reason="verification required")
        self.n.transition(t["task_id"],"VERIFY",reason="redo independent verification")
        record=self.n.record_verification(t["task_id"],"independent-reviewer",evidence["evidence_id"],
                                          notes="Acceptance criteria checked")
        self.assertEqual(record["evidence_status"],"VERIFIED")
        self.assertEqual(self.n.get_verifications(t["task_id"])[0]["verification_id"],record["verification_id"])
        self.n.transition(t["task_id"],"AUDIT")
        self.n.transition(t["task_id"],"COMPLETE",result="verified output")
        self.assertEqual(self.n.get_task(t["task_id"])["state"],"COMPLETE")

    def test_task_dependency_blocks_execute_until_dependency_is_complete(self):
        dependency=self.n.create_task(self.project,"dependency","dependency result","manual verification")
        task=self.n.create_task(self.project,"dependent task","task result","manual verification")
        self.n.add_task_dependency(task["task_id"],dependency["task_id"])
        self.add_verified("dependency evidence")
        self.n.transition(task["task_id"],"RESEARCH")
        self.n.transition(task["task_id"],"PLAN")
        self.n.transition(task["task_id"],"POLICY")
        with self.assertRaisesRegex(PolicyDenied,"dependencies to be COMPLETE"):
            self.n.transition(task["task_id"],"EXECUTE")
        self.n.transition(dependency["task_id"],"RESEARCH")
        self.n.transition(dependency["task_id"],"PLAN")
        self.n.transition(dependency["task_id"],"POLICY")
        self.n.transition(dependency["task_id"],"EXECUTE")
        self.n.transition(dependency["task_id"],"VERIFY")
        self.n.transition(dependency["task_id"],"AUDIT")
        self.n.transition(dependency["task_id"],"COMPLETE",result="dependency verified")
        self.assertEqual(self.n.transition(task["task_id"],"EXECUTE")["state"],"EXECUTE")

    def test_task_dependency_rejects_cycles_and_cross_project_links(self):
        first=self.n.create_task(self.project,"first")
        second=self.n.create_task(self.project,"second")
        self.n.add_task_dependency(first["task_id"],second["task_id"])
        with self.assertRaisesRegex(PolicyDenied,"already exists"):
            self.n.add_task_dependency(first["task_id"],second["task_id"])
        with self.assertRaisesRegex(PolicyDenied,"cycle"):
            self.n.add_task_dependency(second["task_id"],first["task_id"])
        late=self.n.create_task(self.project,"late dependency","done","manual verification")
        self.add_verified("late dependency evidence")
        self.n.transition(late["task_id"],"RESEARCH")
        self.n.transition(late["task_id"],"PLAN")
        self.n.transition(late["task_id"],"POLICY")
        with self.assertRaisesRegex(PolicyDenied,"before the policy gate"):
            self.n.add_task_dependency(late["task_id"],first["task_id"])
        other=self.n.create_project("other-project")["project_id"]
        foreign=self.n.create_task(other,"foreign")
        with self.assertRaisesRegex(PolicyDenied,"same project"):
            self.n.add_task_dependency(first["task_id"],foreign["task_id"])

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

    def test_checkpoint_restore_from_blocked_state(self):
        t=self.n.create_task(self.project,"recover")
        self.n.transition(t["task_id"],"RESEARCH")
        cp=self.n.checkpoint(t["task_id"])["checkpoint_id"]
        self.n.transition(t["task_id"],"BLOCKED",reason="test interruption")
        restored=self.n.restore_checkpoint(t["task_id"],cp,reason="test recovery")
        self.assertEqual(restored["state"],"RESEARCH")
        self.assertIn("CHECKPOINT_RESTORED", [e["event_type"] for e in self.n.audit(self.project,t["task_id"])])

    def test_checkpoint_restore_rejected_from_non_recovery_state(self):
        t=self.n.create_task(self.project,"restore gate")
        self.n.transition(t["task_id"],"RESEARCH")
        cp=self.n.checkpoint(t["task_id"])["checkpoint_id"]
        with self.assertRaises(PolicyDenied):
            self.n.restore_checkpoint(t["task_id"],cp)

    def test_checkpoint_restore_never_replays_execute_state(self):
        t=self.n.create_task(self.project,"unsafe restore","result","verify")
        self.n.transition(t["task_id"],"RESEARCH")
        self.add_verified("official fact")
        self.n.transition(t["task_id"],"PLAN")
        self.n.transition(t["task_id"],"POLICY")
        self.n.transition(t["task_id"],"EXECUTE")
        cp=self.n.checkpoint(t["task_id"])["checkpoint_id"]
        self.n.transition(t["task_id"],"RECOVER")
        with self.assertRaises(PolicyDenied):
            self.n.restore_checkpoint(t["task_id"],cp)

    def test_unknown_project_rejected(self):
        with self.assertRaises(ValueError): self.n.create_task("missing-project","fail")

if __name__=="__main__": unittest.main()
