import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from nexus.core import NEXUS
from nexus.router import Candidate, ProviderError, ToolRouter


class FakeAdapter:
    def __init__(self, *, available=True, quota=True, warning=False, result="ok",
                 execute_error=None, verified=True):
        self.available = available
        self.quota = quota
        self.warning = warning
        self.result = result
        self.execute_error = execute_error
        self.verified = verified
        self.calls = 0

    def preflight(self):
        return {
            "available": self.available,
            "quota_available": self.quota,
            "warning": self.warning,
            "reason": "test preflight",
        }

    def execute(self, task):
        self.calls += 1
        if self.execute_error:
            raise self.execute_error
        return self.result

    def verify(self, task, result):
        return {"passed": self.verified, "result_matches": result == self.result}


def candidate(name, adapter, **kwargs):
    return Candidate(
        id=name,
        adapter=adapter,
        enabled=kwargs.get("enabled", True),
        permission_ok=kwargs.get("permission_ok", True),
        capability_ok=kwargs.get("capability_ok", True),
        cost_tier=kwargs.get("cost_tier", "free"),
        warning=kwargs.get("warning", False),
    )


class ToolRouterTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = str(Path(self.temp_dir.name) / "router-test.db")
        self.controller = NEXUS(database=self.db_path)
        project = self.controller.create_project("Tool Router tests")
        task = self.controller.create_task(
            project["project_id"], "Exercise deterministic routing",
            expected_outcome="Use eligible tools and verify the result",
            verification_method="Router adapter verification plus SQLite audit/checkpoint inspection",
        )
        self.task_id = task["task_id"]
        self.router = ToolRouter(controller=self.controller)

    def tearDown(self):
        self.temp_dir.cleanup()

    def route(self, candidates, **kwargs):
        return self.router.route({"task_id": self.task_id}, candidates, **kwargs)

    def test_free_candidate_precedes_paid_candidate(self):
        free, paid = FakeAdapter(), FakeAdapter(result="paid")
        result = self.route([
            candidate("paid", paid, cost_tier="paid"),
            candidate("free", free),
        ], allow_paid=True, budget_approved=True)
        self.assertEqual(result.selected, "free")
        self.assertTrue(result.verified)
        self.assertEqual(paid.calls, 0)

    def test_quota_exhaustion_falls_back_to_next_free_candidate(self):
        exhausted = FakeAdapter(quota=False)
        fallback = FakeAdapter(result="fallback-result")
        result = self.route([candidate("primary", exhausted), candidate("fallback", fallback)])
        self.assertEqual(result.selected, "fallback")
        self.assertEqual(exhausted.calls, 0)
        self.assertEqual(fallback.calls, 1)

    def test_paid_route_blocked_without_both_approvals(self):
        paid = FakeAdapter()
        result = self.route([candidate("paid", paid, cost_tier="paid")],
                            allow_paid=True, budget_approved=False)
        self.assertEqual(result.decision, "BLOCKED")
        self.assertEqual(paid.calls, 0)

    def test_paid_route_allowed_only_with_explicit_approvals(self):
        paid = FakeAdapter()
        result = self.route([candidate("paid", paid, cost_tier="paid")],
                            allow_paid=True, budget_approved=True)
        self.assertEqual(result.selected, "paid")
        self.assertTrue(result.verified)

    def test_permission_failure_excludes_candidate(self):
        denied, allowed = FakeAdapter(), FakeAdapter()
        result = self.route([
            candidate("denied", denied, permission_ok=False),
            candidate("allowed", allowed),
        ])
        self.assertEqual(result.selected, "allowed")
        self.assertEqual(denied.calls, 0)

    def test_explicit_safe_transient_error_uses_fallback(self):
        primary = FakeAdapter(execute_error=ProviderError("RATE_LIMIT", "rate limited", fallback_safe=True))
        fallback = FakeAdapter()
        result = self.route([candidate("primary", primary), candidate("fallback", fallback)])
        self.assertEqual(result.selected, "fallback")
        self.assertEqual(primary.calls, 1)
        self.assertEqual(fallback.calls, 1)

    def test_unclassified_exception_stops_fallback(self):
        primary, fallback = FakeAdapter(execute_error=RuntimeError("unexpected")), FakeAdapter()
        result = self.route([candidate("primary", primary), candidate("fallback", fallback)])
        self.assertEqual(result.decision, "BLOCKED")
        self.assertEqual(fallback.calls, 0)

    def test_warning_blocks_candidate_and_uses_safe_next_candidate(self):
        primary, fallback = FakeAdapter(warning=True), FakeAdapter()
        result = self.route([candidate("primary", primary), candidate("fallback", fallback)])
        self.assertEqual(result.selected, "fallback")
        self.assertEqual(primary.calls, 0)

    def test_verification_failure_stops_fallback_to_avoid_duplicate_side_effect(self):
        primary, fallback = FakeAdapter(verified=False), FakeAdapter()
        result = self.route([candidate("primary", primary), candidate("fallback", fallback)])
        self.assertEqual(result.decision, "BLOCKED")
        self.assertFalse(result.verified)
        self.assertEqual(fallback.calls, 0)

    def test_every_stage_checkpoint_is_persisted_to_sqlite_with_audit_event(self):
        audit, observed_checkpoints = [], []
        router = ToolRouter(
            controller=self.controller,
            audit_sink=audit.append,
            checkpoint_sink=observed_checkpoints.append,
        )
        result = router.route({"task_id": self.task_id}, [candidate("free", FakeAdapter())])
        self.assertTrue(any(e["event_type"] == "ROUTE_COMPLETED" for e in audit))
        self.assertTrue(any(c["stage"] == "BEFORE_EXECUTE" for c in observed_checkpoints))
        self.assertEqual(len(observed_checkpoints), len(result.checkpoints))
        self.assertTrue(all(c.get("checkpoint_id") for c in result.checkpoints))

        with sqlite3.connect(self.db_path) as con:
            rows = con.execute(
                "SELECT checkpoint_id,state,snapshot_json FROM checkpoints WHERE task_id=?",
                (self.task_id,),
            ).fetchall()
            audit_rows = con.execute(
                "SELECT event_type,details_json FROM audit_log WHERE task_id=?",
                (self.task_id,),
            ).fetchall()
        self.assertEqual(len(rows), len(result.checkpoints))
        persisted_stages = [json.loads(row[2])["router_checkpoint"]["stage"] for row in rows]
        self.assertIn("BEFORE_EXECUTE", persisted_stages)
        self.assertIn("ROUTE_COMPLETED", persisted_stages)
        self.assertTrue(any(kind == "ROUTER_CHECKPOINT_CREATED" for kind, _ in audit_rows))

    def test_missing_task_id_stops_before_provider_execution(self):
        adapter = FakeAdapter()
        with self.assertRaisesRegex(ValueError, "task.task_id is required"):
            self.router.route({}, [candidate("free", adapter)])
        self.assertEqual(adapter.calls, 0)


if __name__ == "__main__":
    unittest.main()
