"""Deterministic NASA-style review-gate readiness checks for NEXUS.

This is a tailored software-project adaptation, not NASA certification. The
evaluator checks supplied review evidence references; it does not authenticate
external artifacts or grant formal gate approval.
"""
from __future__ import annotations
from typing import Any

GATE_SEQUENCE = ("SRR", "SFR", "PDR", "CDR", "TRR", "ORR", "AR")
GATES: dict[str, dict[str, Any]] = {
    "SRR": {"title": "System Requirements Review", "purpose": "Baseline intended use, scope, requirements, and acceptance criteria.", "criteria": [
        {"id": "scope_baselined", "description": "Intended use, exclusions, and system boundary are recorded."},
        {"id": "requirements_traced", "description": "Requirements have stable IDs and verification methods."},
        {"id": "acceptance_defined", "description": "User acceptance criteria are observable and testable."},
        {"id": "risks_recorded", "description": "Initial risks, assumptions, and unknowns are recorded."}]},
    "SFR": {"title": "System Functional Review", "purpose": "Confirm required behavior and workflow coverage.", "criteria": [
        {"id": "workflows_mapped", "description": "Primary and failure workflows map to requirements."},
        {"id": "policy_boundaries_defined", "description": "Policy decisions are deterministic and separate from model output."},
        {"id": "evidence_flow_defined", "description": "Evidence source, freshness, status, and traceability rules are defined."},
        {"id": "failure_recovery_defined", "description": "Failure classification, safe retry, and recovery behavior are specified."}]},
    "PDR": {"title": "Preliminary Design Review", "purpose": "Review architecture, interfaces, data boundaries, and provider integration.", "criteria": [
        {"id": "architecture_reviewed", "description": "Controller, OpenAI adapter, tools, store, and client boundaries are documented."},
        {"id": "interfaces_versioned", "description": "API/MCP schemas and compatibility assumptions are documented."},
        {"id": "identity_model_reviewed", "description": "Authentication, authorization, project scope, and tenant boundaries are designed."},
        {"id": "capability_registry_reviewed", "description": "Provider capabilities have evidence for support, policy, and tests."}]},
    "CDR": {"title": "Critical Design Review", "purpose": "Confirm implementation and traceable policy enforcement.", "criteria": [
        {"id": "implementation_complete", "description": "Required components are implemented or explicitly dispositioned."},
        {"id": "policy_tests_passed", "description": "Denied operations are shown not to execute side effects."},
        {"id": "traceability_complete", "description": "Requirements link to implementation and verification cases."},
        {"id": "secrets_reviewed", "description": "Secrets are not embedded in source, images, logs, or client bundles."}]},
    "TRR": {"title": "Test Readiness Review", "purpose": "Confirm test environment, procedures, and failure scenarios.", "criteria": [
        {"id": "test_plan_ready", "description": "Tests cover success, denial, malformed input, timeout, limits, and recovery."},
        {"id": "ci_passed", "description": "The required CI matrix passed on the candidate commit."},
        {"id": "integration_environment_ready", "description": "A secured integration environment and test credentials are configured."},
        {"id": "evidence_capture_ready", "description": "Test outputs, correlation IDs, and redacted logs can be inspected."}]},
    "ORR": {"title": "Operational Readiness Review", "purpose": "Confirm operational controls before production exposure.", "criteria": [
        {"id": "production_auth_verified", "description": "Production authentication and authorization were tested."},
        {"id": "durable_storage_verified", "description": "Persistence, backup, restore, and concurrency behavior are tested."},
        {"id": "monitoring_ready", "description": "Health, error, rate-limit, and usage monitoring are configured."},
        {"id": "rollback_tested", "description": "A tested rollback and recovery procedure exists."},
        {"id": "deployment_tls_verified", "description": "Public endpoints use HTTPS and deployment secret management."}]},
    "AR": {"title": "Acceptance Review", "purpose": "Verify that the deployed system meets the intended user outcome.", "criteria": [
        {"id": "live_round_trip_passed", "description": "A real authorized client-to-service round trip passed."},
        {"id": "denial_test_passed", "description": "Unauthorized and out-of-scope operations were denied before execution."},
        {"id": "audit_readback_passed", "description": "Decision, evidence, and outcome can be read from audit records."},
        {"id": "user_outcome_verified", "description": "The intended workflow passed documented acceptance criteria."}]},
}

def list_review_gates() -> list[dict[str, Any]]:
    result = []
    for index, gate_id in enumerate(GATE_SEQUENCE):
        gate = GATES[gate_id]
        result.append({"gate_id": gate_id, "sequence": index + 1, "title": gate["title"],
            "purpose": gate["purpose"], "predecessor": GATE_SEQUENCE[index - 1] if index else None,
            "criteria": [dict(item) for item in gate["criteria"]]})
    return result

def evaluate_gate_readiness(gate_id: str, prior_gate_statuses: list[dict[str, Any]],
                            criteria_evidence: list[dict[str, Any]]) -> dict[str, Any]:
    """Check readiness metadata only; never grants formal approval or authenticates artifacts."""
    normalized_gate = gate_id.strip().upper() if isinstance(gate_id, str) else ""
    if normalized_gate not in GATES:
        raise ValueError("UNKNOWN_REVIEW_GATE")
    prior: dict[str, str] = {}
    for row in prior_gate_statuses:
        if not isinstance(row, dict) or not isinstance(row.get("gate_id"), str):
            raise ValueError("INVALID_PRIOR_GATE_STATUS")
        key = row["gate_id"].strip().upper()
        if key in prior:
            raise ValueError("DUPLICATE_PRIOR_GATE_STATUS")
        prior[key] = str(row.get("status", "")).strip().upper()
    index = GATE_SEQUENCE.index(normalized_gate)
    predecessor = GATE_SEQUENCE[index - 1] if index else None
    blockers: list[str] = []
    if predecessor and prior.get(predecessor) != "APPROVED":
        blockers.append(f"PREDECESSOR_GATE_NOT_APPROVED:{predecessor}")
    supplied: dict[str, dict[str, Any]] = {}
    for row in criteria_evidence:
        if not isinstance(row, dict) or not isinstance(row.get("criterion_id"), str):
            raise ValueError("INVALID_CRITERION_EVIDENCE")
        key = row["criterion_id"].strip()
        if key in supplied:
            raise ValueError(f"DUPLICATE_CRITERION_EVIDENCE:{key}")
        supplied[key] = row
    required = GATES[normalized_gate]["criteria"]
    checks = []
    for criterion in required:
        cid = criterion["id"]
        row = supplied.get(cid, {})
        status = str(row.get("status", "UNKNOWN")).strip().upper()
        evidence_ref, method = row.get("evidence_ref"), row.get("verification_method")
        ready = (status == "VERIFIED" and isinstance(evidence_ref, str) and bool(evidence_ref.strip())
                 and isinstance(method, str) and bool(method.strip()))
        checks.append({"criterion_id": cid, "status": "READY" if ready else "BLOCKED",
            "submitted_status": status, "evidence_ref": evidence_ref.strip() if isinstance(evidence_ref, str) else None,
            "verification_method": method.strip() if isinstance(method, str) else None,
            "reason_code": "EVIDENCE_REFERENCE_AND_METHOD_PRESENT" if ready else "VERIFIED_EVIDENCE_REFERENCE_REQUIRED"})
        if not ready:
            blockers.append(f"CRITERION_NOT_READY:{cid}")
    unknown_ids = sorted(set(supplied) - {item["id"] for item in required})
    blockers.extend(f"UNKNOWN_CRITERION:{cid}" for cid in unknown_ids)
    return {"gate_id": normalized_gate, "title": GATES[normalized_gate]["title"],
        "status": "READY_FOR_REVIEW" if not blockers else "BLOCKED", "gate_approval": "NOT_GRANTED",
        "predecessor": predecessor, "checks": checks, "blockers": blockers,
        "reviewer_action_required": True,
        "limitations": ["Readiness is not formal gate approval.",
            "Evidence references and submitted statuses are not independently authenticated by this evaluator.",
            "An authorized reviewer must inspect the cited artifacts and record approval separately."]}
