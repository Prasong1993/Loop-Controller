# IRIS Control / Project Control API — Review Handoff

Updated: 2026-10-11 (Asia/Bangkok)
Repository: `Prasong1993/Loop-Controller`
Review target: PR #4, `work/project-control-api-hardening-2026-10-11`
Last inspected head before this handoff document: `cb9d661a68ff521fd7b52ab4d0a03965306ed2ff`
Base: `main` at `eb5359505bf39e4ca1dcd3512f2b8ea3ac6e8baa`
PR: https://github.com/Prasong1993/Loop-Controller/pull/4
Latest recorded CI: https://github.com/Prasong1993/Loop-Controller/actions/runs/38079334552

## 1. Purpose and review boundaries

Prepare an independent, evidence-based review of the current Project Control API / controller implementation before any merge or deployment.

This repository currently uses the internal product/module name **NEXUS** in source code. Review it as the current IRIS Control / Project Control API workstream, but do not import assumptions or code from older IRIS repositories, `iris-step1`, or `iris-controller`.

- Review only the named repository and the specified PR branch unless the user explicitly broadens scope.
- Do not merge, deploy, publish, register/update a Plugin Creator plugin, change production, alter secrets, or modify `main`.
- Do not edit other plugins, especially `iris-step1` and `iris-controller`.
- Do not treat a source file existing or a CI pass as proof that a live integration works.
- Do not treat lack of an external provider call as proof that every real-use test failed. Assess each claim against the evidence actually available, including runtime records and controlled interaction tests.
- Never invent execution logs. If runtime logs or a live endpoint are unavailable, mark that specific evidence **NOT RUN** or **BLOCKED**.

## 2. Evidence vocabulary

Use these labels consistently:
- **VERIFIED-SOURCE** — inspected the exact source/docs at the stated branch and commit.
- **PASS-CI** / **FAIL-CI** — exact CI result tied to a commit.
- **PASS-RUNTIME** / **FAIL-RUNTIME** — observed execution with traceable request/task/result/audit evidence.
- **PARTIAL** — some controls exist but acceptance criteria are not fully satisfied.
- **NOT RUN** — no execution evidence was found.
- **BLOCKED** — a named prerequisite prevents the test.
- **UNKNOWN** — evidence is insufficient; do not use this as confirmation.

Every finding should include: severity, requirement/control, exact file and symbol or line, reproducible scenario, expected vs actual behavior, evidence link/log/test, security or reliability impact, and proposed fix.

## 3. Existing evidence confirmed before handoff

- PR #4 was observed as **OPEN, DRAFT, NOT MERGED**.
- The PR head at inspection was `cb9d661a68ff521fd7b52ab4d0a03965306ed2ff`.
- CI run #283 completed successfully for Python 3.11, 3.12 and 3.13; each job passed Compile, OpenAPI contract validation and unit tests.
- The CI result is evidence for that exact commit only. After this handoff document creates a new commit, re-check CI for the new head rather than inheriting the previous result.
- No live provider/quota integration, secured HTTPS deployment, or Plugin Creator round-trip is established by the above CI run.
- No merge or deployment is authorized by this review handoff.

## 4. Implementation areas to inspect

1. `nexus/core.py`: workflow state machine, policy gate, task dependencies, evidence scoping, verification records, COMPLETE transition, recovery, concurrency and transaction boundaries.
2. `nexus/authorization.py`: principal mapping, project membership, role enforcement, default-deny behavior, membership changes and tenant isolation.
3. `nexus/api.py`: REST authentication, authorization on every endpoint, request-start/final audit behavior, rate limiting, idempotency integration, validation and error responses.
4. `nexus/mcp_server.py`: MCP authentication, tool-level authorization, context/principal isolation, mandatory start/end audit, rate limiting and REST/MCP policy parity.
5. `nexus/idempotency.py`: concurrent claims, key scope, request fingerprinting, persisted replay, crash/timeout states, retention and safe reconciliation.
6. `nexus/records.py`, `nexus/runlog.py`: append-only behavior, failure propagation, audit completeness, secret/PII minimization, trace IDs, transaction integrity and recovery from missing terminal events.
7. `nexus/router.py`: free-first ordering, permissions/capabilities, paid-budget approval, unknown preflight handling, error classification, duplicate side-effect prevention, verification-gated fallback and checkpoint persistence.
8. `nexus/openai_adapter.py`: model-proposed tool call gating, unknown/invalid tool rejection, audit failure behavior, retries, maximum rounds, malformed responses and secret-safe records.
9. `openapi.yaml` and `tests/test_openapi_contract.py`: contract matches runtime schemas, authentication expectations, status/error codes, and REST/MCP behavior.
10. Tests and docs: `tests/test_core.py`, `tests/test_api.py`, `tests/test_mcp_server.py`, `tests/test_idempotency.py`, `tests/test_router.py`, `tests/test_openai_adapter.py`, `docs/REQUIREMENTS.md`, `docs/PROJECT_CONTROL_API_TRACEABILITY.md`.

## 5. Known gaps to validate independently (do not assume fixed)

### P0 — Safety / authorization / completion integrity
- **Audit completion semantics — PARTIAL:** start-of-request/tool audit is intended to fail closed, but some completion/error outcome writes are documented as best-effort. Verify every consequential operation has a durable terminal outcome or remains visibly incomplete/uncertain; a swallowed audit failure must not produce a success-looking result.
- **Identity and tenant isolation — PARTIAL:** `NEXUS_API_TOKENS` supports configured principal mapping, but the legacy single `NEXUS_API_KEY` maps all holders to one shared principal. Check every REST and MCP operation, including reads, writes, dependency endpoints, verification endpoints and audit access, for cross-project leakage. Check READ_ONLY cannot mutate.
- **Completion verification — PARTIAL:** COMPLETE requires a stored passing verification tied to scoped VERIFIED evidence and a verifier principal distinct from the recorded executor. Check whether executor/verifier identity is trustworthy, the result being verified is bound to the exact task output, result digest is required and checked, and evidence actually supports the claim rather than merely containing an exact quote.
- **Recovery — PARTIAL:** recovery must not jump directly to execution without re-running required planning/policy gates. Verify every transition and failure path, including MCP operations.

### P1 — Duplicate effects, failure recovery and runtime robustness
- **Idempotency — PARTIAL:** current durable key ledger protects REST transition into EXECUTE, not all external tool/provider side effects. Test concurrent duplicate requests, timeout after side effect but before response persistence, process restart, stale IN_PROGRESS, UNCERTAIN, key reuse across task/project, and operator reconciliation. Do not automatically replay an uncertain non-idempotent action.
- **Checkpoint/run log — PARTIAL:** inject database write failures at run start, each stage checkpoint, provider execution, verification, and terminal event. Confirm the controller stops before unsafe work where required and records uncertainty where an effect may already have occurred.
- **Tool routing — PARTIAL:** ensure unknown quota/preflight is not treated as available; paid route requires explicit paid permission and budget approval; fallback is allowed only for classified safe failures; verification failure never silently causes a second side effect.
- **Rate limiting — PARTIAL:** existing limiter is process-local/per-client-IP. Confirm behavior under concurrent calls and document that it is not distributed across workers/replicas; do not label production abuse protection complete.
- **SQLite/concurrency — REVIEW REQUIRED:** inspect connection/transaction behavior across core, authorization, records, idempotency and runlog stores; check races, locking, foreign keys, atomic updates and consistency if environment variables point stores to different databases.

### P2 — Contract and operational readiness
- Validate REST/MCP schema parity, error semantics, authentication responses, versioning and backward compatibility.
- Verify that logs and error responses never include bearer tokens, API keys, secret environment values or unnecessary personal data.
- Review startup defaults and deployment settings; no remote exposure without an approved authenticated HTTPS boundary.
- Confirm dependency versions, reproducible setup, migrations and backup/restore expectations.
- Add a test-to-requirement mapping for every P0/P1 control, including negative/fault-injection cases.

## 6. Required test matrix

For every relevant test, record test ID, branch/commit, setup, action, expected result, actual result, trace/task ID, audit evidence, and pass/fail.

- Unauthenticated and invalid-token REST/MCP calls are rejected before business logic.
- Principal A cannot read or mutate Principal B's project/task/evidence/verification/audit/dependency records.
- READ_ONLY cannot execute, mutate, reset, change dependencies or record privileged verification.
- Failure to persist required start audit prevents the operation from beginning.
- Failure to persist terminal audit never yields an unqualified success/COMPLETE state.
- UNKNOWN/RECOVERED/BLOCKED evidence cannot satisfy a VERIFIED prerequisite.
- A task cannot EXECUTE until all declared same-project dependencies are COMPLETE; cycles, self-dependencies and cross-project links are rejected.
- Invalid state transitions, including direct RECOVER-to-EXECUTE, are rejected.
- COMPLETE fails when verification is missing, fails, is not durably readable, references other task/project evidence, or is performed by the same principal as executor.
- Same idempotency key + same request returns the stored result without executing twice; same key + different request is rejected.
- Timeout/crash after a possible side effect blocks replay and surfaces an explicit uncertain state with a documented reconciliation path.
- Router denies unknown quota, unapproved paid use, unclassified errors and unsafe fallback; checkpoint failure blocks execution if no effect has started.
- Secrets are absent from repository fixtures, logs, responses and audit metadata.
- CI runs on Python 3.11–3.13 and validates compilation, OpenAPI contract and unit tests.
- Runtime/ChatGPT interaction tests must use actual captured request/result/audit records when available. If the target integration is not configured, record NOT RUN/BLOCKED instead of guessing.

## 7. Required reviewer output

Return a concise but complete report in this structure:

1. **Verdict:** READY FOR REVIEW / NEEDS FIXES / BLOCKED — not a production approval.
2. **Exact revision inspected:** repository, branch, head SHA, base SHA and CI run.
3. **Findings ordered by severity:** P0, P1, P2; each with code location, evidence, reproducible case and fix.
4. **Tests executed:** exact commands or CI URLs and actual results. Separate source inspection, CI, and runtime evidence.
5. **Requirements traceability:** requirement → implementation → test → evidence → remaining gap.
6. **Fix plan:** smallest safe changes first, each paired with a regression test.
7. **Unverified/blocked items:** exact reason and evidence needed to unblock.
8. **Final gate:** list criteria that must pass before merge; separately list criteria that must pass before any deployment/plugin registration.

Do not change code, branches, PR state, deployment, secrets, or plugin registrations during the independent review unless separately instructed. A review report is not permission to merge or deploy.

## 8. Current decision

**Suitable for independent review preparation; NOT production-ready.** The work branch has meaningful CI-verified controls, but the gaps above must be independently reproduced or disproven with source/tests/runtime records. Keep PR #4 Draft and unmerged while the review is in progress.
