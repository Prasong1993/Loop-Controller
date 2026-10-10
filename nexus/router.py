"""Deterministic free-first tool router with explicit safe-fallback rules.

This module does not ship provider credentials or claim live provider connectivity.
Integrations supply adapters implementing preflight(), execute(), and verify().
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Protocol


class Adapter(Protocol):
    def preflight(self) -> Mapping[str, Any]:
        """Return availability/quota facts; unknown facts must not be treated as true."""
        ...

    def execute(self, task: Mapping[str, Any]) -> Any:
        ...

    def verify(self, task: Mapping[str, Any], result: Any) -> bool | Mapping[str, Any]:
        ...


class ProviderError(Exception):
    """Provider failure with explicit retry/fallback safety classification."""

    def __init__(self, code: str, message: str, *, fallback_safe: bool = False):
        super().__init__(message)
        self.code = code
        self.fallback_safe = fallback_safe


@dataclass(frozen=True)
class Candidate:
    id: str
    adapter: Adapter
    cost_tier: str = "free"
    enabled: bool = True
    permission_ok: bool = False
    capability_ok: bool = False
    warning: bool = False


@dataclass
class RouteResult:
    decision: str
    selected: str | None
    result: Any = None
    reason: str = ""
    verified: bool = False
    events: list[dict[str, Any]] = field(default_factory=list)
    checkpoints: list[dict[str, Any]] = field(default_factory=list)


class ToolRouter:
    """Route to eligible free candidates first; never silently authorize paid usage."""

    def __init__(
        self,
        *,
        audit_sink: Callable[[Mapping[str, Any]], None] | None = None,
        checkpoint_sink: Callable[[Mapping[str, Any]], None] | None = None,
    ) -> None:
        self._audit_sink = audit_sink
        self._checkpoint_sink = checkpoint_sink

    def route(
        self,
        task: Mapping[str, Any],
        candidates: list[Candidate],
        *,
        allow_paid: bool = False,
        budget_approved: bool = False,
    ) -> RouteResult:
        events: list[dict[str, Any]] = []
        checkpoints: list[dict[str, Any]] = []

        def record(event_type: str, **details: Any) -> None:
            event = {"event_type": event_type, **details}
            events.append(event)
            if self._audit_sink:
                self._audit_sink(event)

        def checkpoint(stage: str, **details: Any) -> None:
            item = {"stage": stage, "task_id": task.get("task_id"), **details}
            checkpoints.append(item)
            if self._checkpoint_sink:
                self._checkpoint_sink(item)

        eligible = [
            c for c in candidates
            if c.enabled and c.permission_ok and c.capability_ok and not c.warning
        ]
        free = [c for c in eligible if c.cost_tier == "free"]
        paid = [c for c in eligible if c.cost_tier == "paid"]
        unsupported_tiers = [c.id for c in eligible if c.cost_tier not in {"free", "paid"}]
        ordered = free + (paid if allow_paid and budget_approved else [])

        record("ROUTE_STARTED", task_id=task.get("task_id"), candidate_count=len(candidates))
        checkpoint("ROUTE_STARTED", candidate_ids=[c.id for c in ordered])

        if not ordered:
            reason = (
                "paid candidates require explicit allow_paid and budget_approved"
                if paid else "no candidate passed enabled/permission/capability/warning gates"
            )
            record("ROUTE_BLOCKED", reason=reason, unsupported_tiers=unsupported_tiers)
            checkpoint("ROUTE_BLOCKED", reason=reason)
            return RouteResult("BLOCKED", None, reason=reason, events=events, checkpoints=checkpoints)

        for candidate in ordered:
            checkpoint("BEFORE_PREFLIGHT", candidate_id=candidate.id)
            try:
                status = candidate.adapter.preflight()
            except ProviderError as exc:
                record("PREFLIGHT_ERROR", candidate_id=candidate.id, code=exc.code)
                if not exc.fallback_safe:
                    return self._blocked(candidate.id, f"unsafe preflight failure: {exc.code}", events, checkpoints, record, checkpoint)
                continue
            except Exception:
                record("PREFLIGHT_ERROR", candidate_id=candidate.id, code="UNCLASSIFIED")
                return self._blocked(candidate.id, "unclassified preflight failure; stopped to avoid unsafe retry", events, checkpoints, record, checkpoint)

            if status.get("warning") or status.get("available") is not True or status.get("quota_available") is not True:
                reason = str(status.get("reason") or "unavailable, warning present, or quota not confirmed")
                record("CANDIDATE_SKIPPED", candidate_id=candidate.id, reason=reason)
                checkpoint("CANDIDATE_SKIPPED", candidate_id=candidate.id, reason=reason)
                continue

            checkpoint("BEFORE_EXECUTE", candidate_id=candidate.id)
            try:
                value = candidate.adapter.execute(task)
            except ProviderError as exc:
                record("EXECUTION_ERROR", candidate_id=candidate.id, code=exc.code, fallback_safe=exc.fallback_safe)
                checkpoint("EXECUTION_ERROR", candidate_id=candidate.id, code=exc.code)
                if exc.fallback_safe:
                    continue
                return self._blocked(candidate.id, f"unsafe execution failure: {exc.code}", events, checkpoints, record, checkpoint)
            except Exception:
                record("EXECUTION_ERROR", candidate_id=candidate.id, code="UNCLASSIFIED", fallback_safe=False)
                return self._blocked(candidate.id, "unclassified execution failure; stopped to avoid unsafe retry", events, checkpoints, record, checkpoint)

            checkpoint("BEFORE_VERIFY", candidate_id=candidate.id)
            try:
                verification = candidate.adapter.verify(task, value)
            except Exception:
                record("VERIFICATION_FAILED", candidate_id=candidate.id, reason="verifier raised an exception")
                return self._blocked(candidate.id, "verification raised an exception; result not accepted", events, checkpoints, record, checkpoint)

            if verification is True:
                verified, verification_details = True, {}
            elif isinstance(verification, Mapping):
                verified = verification.get("passed") is True
                verification_details = dict(verification)
            else:
                verified, verification_details = False, {}

            if not verified:
                record("VERIFICATION_FAILED", candidate_id=candidate.id, details=verification_details)
                checkpoint("VERIFICATION_FAILED", candidate_id=candidate.id)
                # Do not rerun a task on another provider after an unverified side effect.
                return self._blocked(candidate.id, "result failed verification; fallback stopped to prevent duplicate side effects", events, checkpoints, record, checkpoint)

            record("ROUTE_COMPLETED", candidate_id=candidate.id, verified=True, cost_tier=candidate.cost_tier)
            checkpoint("ROUTE_COMPLETED", candidate_id=candidate.id, verified=True)
            return RouteResult("ALLOW", candidate.id, value, "execution result verified", True, events, checkpoints)

        reason = "all eligible candidates were unavailable, quota-limited, warned, or failed with explicitly safe fallback errors"
        record("ROUTE_BLOCKED", reason=reason)
        checkpoint("ROUTE_BLOCKED", reason=reason)
        return RouteResult("BLOCKED", None, reason=reason, events=events, checkpoints=checkpoints)

    @staticmethod
    def _blocked(candidate_id, reason, events, checkpoints, record, checkpoint):
        record("ROUTE_BLOCKED", candidate_id=candidate_id, reason=reason)
        checkpoint("ROUTE_BLOCKED", candidate_id=candidate_id, reason=reason)
        return RouteResult("BLOCKED", None, reason=reason, events=events, checkpoints=checkpoints)
