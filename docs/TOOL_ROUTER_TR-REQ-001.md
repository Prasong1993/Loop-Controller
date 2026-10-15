# TR-REQ-001 — Deterministic Tool Router

Status: **IMPLEMENTED ON `work/project-control-api-hardening-2026-10-11`; CI PASS on run #249; live provider integration NOT RUN**

## Scope

This change adds `nexus.router.ToolRouter`, an adapter-based execution boundary. The reviewed implementation is now copied into the dedicated work branch; PR #3 itself remains open and unchanged. It does not add provider credentials, discover account quotas by itself, or claim that any external model is connected. A real integration must implement the adapter contract and supply truthful preflight results.

## Routing rules

1. Reject candidates that are disabled, unauthorized, lack the required capability, or already carry a warning.
2. Try eligible free candidates in caller-supplied priority order.
3. A candidate is runnable only when preflight explicitly confirms `available=True` and `quota_available=True`, with no warning.
4. Paid candidates are considered only when both `allow_paid=True` and `budget_approved=True`.
5. Fall back after a provider error only when the adapter explicitly classifies it with `fallback_safe=True`. Unclassified exceptions stop routing.
6. Verify each returned result before accepting it. If verification fails, stop rather than risk repeating a side effect on another provider.
7. Persist every router-stage checkpoint directly through the required NEXUS controller into the existing SQLite `checkpoints` table. Each checkpoint is stored with the task snapshot and router-stage details, and a `ROUTER_CHECKPOINT_CREATED` event is written to `audit_log` in the same transaction. Optional sinks are supplemental observers, not the persistence mechanism.

## Adapter contract

Construct `ToolRouter(controller=nexus_controller)`; a controller implementing `record_router_checkpoint(task_id, snapshot)` is mandatory. If checkpoint persistence fails, routing stops before the next operation. An adapter implements:
- `preflight() -> Mapping`: must explicitly return availability and quota facts; unknown values are not treated as available.
- `execute(task) -> result`: perform one authorized provider/tool operation.
- `verify(task, result) -> bool | Mapping`: return `True` or a mapping with `passed=True` only after checking acceptance criteria.

Raise `ProviderError(code, message, fallback_safe=True)` only when the error is known to be safe for trying a different candidate. Do not classify authentication errors, policy denials, unknown errors, or potentially completed side effects as fallback-safe.

## Test coverage added

- Free-first ordering over paid options
- Quota-exhaustion fallback
- Explicit paid approval and budget gate
- Permission exclusion
- Explicitly safe transient failure fallback
- Unclassified error stops routing
- Warning/preflight handling
- Verification failure stops fallback
- Audit/checkpoint sink callbacks

## Remaining verification

- GitHub Actions run [#249](https://github.com/Prasong1993/Loop-Controller/actions/runs/38076731270) passed on Python 3.11, 3.12 and 3.13 for work-branch commit `188a604f498abb5986600a182e04354b1daadb8a` (4 OpenAPI contract tests + 94 unit tests per matrix job). This verifies mock-backed tests only.
- No real provider adapter or live quota endpoint is included in this change.
- No API key or provider account is called by the mock-backed unit tests.
- Durable router-stage checkpoints are wired to the existing SQLite controller and covered by a test that reads back checkpoint rows and audit events.
- Production behavior, rate limits, and live fallback remain **NOT RUN / UNKNOWN** until exercised against an authorized provider integration. The router is currently a Python module and is not wired to a configured live provider endpoint; do not claim live execution. This does not block source review, static contract checks, mock-backed tests, or unrelated implementation work. Each skipped live check must be logged with a reason, and all runnable checks should continue.


## Automatic per-round execution logging

Every invocation now creates one row in SQLite `router_runs` and an ordered, append-only event history in `router_run_events`. Route decisions, errors, and durable checkpoint writes are recorded automatically. A successful route is marked `COMPLETED`; a blocked route is marked `BLOCKED`. If execution is interrupted before a terminal event, the run remains `RUNNING` so it is visibly incomplete and can be investigated rather than being reported as successful.

The run ledger shares the NEXUS database configured by the controller. The test suite checks that a full routing round writes a start event, route events, checkpoint events, a terminal status, and a persisted outcome. This is runtime execution history; Git commits remain the version history for source-code changes, not a place to append private task payloads every round.
