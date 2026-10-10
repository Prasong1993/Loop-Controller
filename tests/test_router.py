import unittest

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
    def test_free_candidate_precedes_paid_candidate(self):
        free, paid = FakeAdapter(), FakeAdapter(result="paid")
        result = ToolRouter().route(
            {"task_id": "t1"}, [
                candidate("paid", paid, cost_tier="paid"),
                candidate("free", free),
            ],
            allow_paid=True, budget_approved=True,
        )
        self.assertEqual(result.selected, "free")
        self.assertTrue(result.verified)
        self.assertEqual(paid.calls, 0)

    def test_quota_exhaustion_falls_back_to_next_free_candidate(self):
        exhausted = FakeAdapter(quota=False)
        fallback = FakeAdapter(result="fallback-result")
        result = ToolRouter().route(
            {"task_id": "t2"},
            [candidate("primary", exhausted), candidate("fallback", fallback)],
        )
        self.assertEqual(result.selected, "fallback")
        self.assertEqual(exhausted.calls, 0)
        self.assertEqual(fallback.calls, 1)

    def test_paid_route_blocked_without_both_approvals(self):
        paid = FakeAdapter()
        result = ToolRouter().route(
            {"task_id": "t3"}, [candidate("paid", paid, cost_tier="paid")],
            allow_paid=True, budget_approved=False,
        )
        self.assertEqual(result.decision, "BLOCKED")
        self.assertEqual(paid.calls, 0)

    def test_paid_route_allowed_only_with_explicit_approvals(self):
        paid = FakeAdapter()
        result = ToolRouter().route(
            {"task_id": "t4"}, [candidate("paid", paid, cost_tier="paid")],
            allow_paid=True, budget_approved=True,
        )
        self.assertEqual(result.selected, "paid")
        self.assertTrue(result.verified)

    def test_permission_failure_excludes_candidate(self):
        denied = FakeAdapter()
        allowed = FakeAdapter()
        result = ToolRouter().route(
            {"task_id": "t5"},
            [candidate("denied", denied, permission_ok=False), candidate("allowed", allowed)],
        )
        self.assertEqual(result.selected, "allowed")
        self.assertEqual(denied.calls, 0)

    def test_explicit_safe_transient_error_uses_fallback(self):
        primary = FakeAdapter(execute_error=ProviderError("RATE_LIMIT", "rate limited", fallback_safe=True))
        fallback = FakeAdapter()
        result = ToolRouter().route(
            {"task_id": "t6"}, [candidate("primary", primary), candidate("fallback", fallback)]
        )
        self.assertEqual(result.selected, "fallback")
        self.assertEqual(primary.calls, 1)
        self.assertEqual(fallback.calls, 1)

    def test_unclassified_exception_stops_fallback(self):
        primary = FakeAdapter(execute_error=RuntimeError("unexpected"))
        fallback = FakeAdapter()
        result = ToolRouter().route(
            {"task_id": "t7"}, [candidate("primary", primary), candidate("fallback", fallback)]
        )
        self.assertEqual(result.decision, "BLOCKED")
        self.assertEqual(fallback.calls, 0)

    def test_warning_blocks_candidate_and_uses_safe_next_candidate(self):
        primary = FakeAdapter(warning=True)
        fallback = FakeAdapter()
        result = ToolRouter().route(
            {"task_id": "t8"}, [candidate("primary", primary), candidate("fallback", fallback)]
        )
        self.assertEqual(result.selected, "fallback")
        self.assertEqual(primary.calls, 0)

    def test_verification_failure_stops_fallback_to_avoid_duplicate_side_effect(self):
        primary = FakeAdapter(verified=False)
        fallback = FakeAdapter()
        result = ToolRouter().route(
            {"task_id": "t9"}, [candidate("primary", primary), candidate("fallback", fallback)]
        )
        self.assertEqual(result.decision, "BLOCKED")
        self.assertFalse(result.verified)
        self.assertEqual(fallback.calls, 0)

    def test_audit_and_checkpoint_sinks_receive_events(self):
        audit, checkpoints = [], []
        result = ToolRouter(
            audit_sink=audit.append, checkpoint_sink=checkpoints.append
        ).route({"task_id": "t10"}, [candidate("free", FakeAdapter())])
        self.assertTrue(any(e["event_type"] == "ROUTE_COMPLETED" for e in audit))
        self.assertTrue(any(c["stage"] == "BEFORE_EXECUTE" for c in checkpoints))
        self.assertEqual(len(audit), len(result.events))
        self.assertEqual(len(checkpoints), len(result.checkpoints))


if __name__ == "__main__":
    unittest.main()
