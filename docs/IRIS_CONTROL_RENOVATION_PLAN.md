# IRIS Control — Vendor-Neutral System Renovation & Review Plan

Date: 2026-10-11 (Asia/Bangkok)
Repository: `Prasong1993/Loop-Controller`
Target branch: `work/project-control-api-hardening-2026-10-11`
Related review: `docs/IRIS_CONTROL_INDEPENDENT_REVIEW.md`
PR: https://github.com/Prasong1993/Loop-Controller/pull/4

## 0. Purpose and decision

This document is the implementation-ready proposal for an independent reviewer/plugin to inspect the current system and identify or implement corrections in an isolated branch.

**Architecture decision proposed:** IRIS Control must not depend on OpenAI as its control-plane core. The deterministic controller, evidence store, policy engine, state machine, audit trail, checkpoint/recovery logic, authorization, budget gates, and verification contract must operate independently of any model vendor. OpenAI is one optional model/provider adapter, not the source of truth and not the authority that approves execution.

This is a proposal and review brief, not evidence that the renovation has already been implemented. Do not mark requirements complete until source, tests, and—where relevant—runtime records prove them.

## 1. Non-negotiable system principles

1. **Controller before execution:** a model may propose plans and tool calls; deterministic IRIS policy must authorize each consequential action before execution.
2. **Vendor-neutral core:** core state, policy, evidence, task graph, audit, idempotency, checkpoints, recovery and verification must not import or require OpenAI SDKs.
3. **Provider adapters are replaceable:** OpenAI, another hosted model, a local model, deterministic code, and human-provided input must fit a documented adapter contract. No provider gets implicit privileges.
4. **Evidence before claims:** all important facts and test conclusions cite source, retrieval/test time, version/commit, method and evidence status. Unknown is never proof.
5. **Fail closed on safety-critical uncertainty:** missing identity, policy, budget approval, required audit, dependency status or verification blocks the action.
6. **No false completion:** COMPLETE is only possible after the intended result is durably recorded, independently checked against acceptance criteria, and the audit trail reaches a valid terminal state.
7. **No silent duplicate side effects:** an uncertain operation is quarantined for reconciliation, not automatically retried.
8. **Reproducibility:** each test report states exact commit, environment, command/action, expected result, actual result and trace/task IDs.
9. **Minimal user intervention:** infer safe routine details, but stop for genuinely missing authorization, destructive actions, spending approval or unresolved conflicts.
10. **No unsafe release actions:** do not merge, deploy, expose a service, rotate/change secrets, or register/update a Plugin Creator plugin as part of this review unless separately authorized.

## 2. Target architecture

Keep the core small, deterministic, testable and vendor-independent.

```text
User / ChatGPT / Plugin / CLI / REST / MCP
                 |
          Identity Boundary
                 |
       API + Protocol Adapters
       (REST / MCP / future UI)
                 |
       Application / Use-Case Layer
                 |
  +--------------+-------------------+
  |              |                   |
Task & State   Policy Engine     Evidence Registry
Machine        (deterministic)   (source/status/hash)
  |              |                   |
  +--------- Execution Gate ----------+
                 |
        Approved Tool Dispatcher
                 |
     Tool / Provider Adapter Contract
       |          |          |
    OpenAI     Other LLM   Non-LLM tools
    adapter     adapter    / local tools
                 |
        Result Verification Gate
                 |
      Durable Audit + Run Ledger
                 |
       Checkpoint / Recovery Queue
                 |
     SQLite first; storage interface
     allows later PostgreSQL deployment
```

### Layer responsibilities

- **Domain/core:** Task, Project, Dependency, Evidence, PolicyDecision, ExecutionAttempt, VerificationRecord, AuditEvent and BudgetApproval. No vendor SDK imports.
- **Policy engine:** deterministic rules only; returns ALLOW/DENY/REQUIRE_APPROVAL with reason codes and policy version. It does not call a model.
- **Provider interface:** proposes text/structured plans or model tool calls. It cannot directly execute tools, change task state, create VERIFIED evidence, or mark a task COMPLETE.
- **Tool dispatcher:** accepts only registered tools with schemas, permission scopes, risk classification, timeout/retry rules and idempotency behavior.
- **Evidence registry:** preserves source URI/identifier, title, version/revision, retrieval time, content hash, verification method, status and project/task scope.
- **Audit/run ledger:** records request, authorization decision, execution intent, outcome, verification, errors and trace relationships. Required audit failure blocks new side effects; missing terminal events remain visibly incomplete.
- **Protocol adapters:** REST and MCP call the same use cases and policy enforcement. Neither adapter reimplements policy independently.
- **Storage abstraction:** core uses repository interfaces; SQLite is the development/default backend. Transaction guarantees and multi-process deployment requirements must be documented. Do not claim distributed consistency for SQLite without proof.

## 3. Proposed corrections, ordered by priority

These are proposed work items. First reproduce each issue against the exact branch; implement only confirmed gaps, but retain a regression test for every fix.

### P0 — Authorization and completion integrity

**P0-01: Real principal identity and tenant isolation**
- Inspect: `nexus/authorization.py`, `nexus/api.py`, `nexus/mcp_server.py`.
- Proposed fix: require explicit principal identity for remote access; map each credential to one principal and scoped roles; deprecate shared `NEXUS_API_KEY` for multi-tenant use or limit it to explicitly configured single-tenant/local mode. Never infer Owner from untrusted caller-supplied project data.
- Test: two isolated principals; attempt cross-project read/write through every REST and MCP tool. Expect deny and audit event without leaking record existence/content.
- Test READ_ONLY against every mutation, including dependencies, evidence, reset/recovery, verification, usage/budget and audit-related actions.

**P0-02: Mandatory durable audit outcomes**
- Inspect: `nexus/api.py`, `nexus/mcp_server.py`, `nexus/records.py`, `nexus/runlog.py`.
- Proposed fix: standardize lifecycle events: REQUEST_ACCEPTED → AUTHORIZED/DENIED → EXECUTION_INTENT → EFFECT_STARTED (if applicable) → RESULT_RECORDED → VERIFIED/FAILED → TERMINAL. Use a durable append interface and explicit audit-write errors. A terminal audit failure must not be silently converted to success.
- If an external side effect may have occurred but the result/audit write failed, mark the attempt UNCERTAIN and prohibit replay until reconciled.
- Test fault injection at each audit write boundary. Assert no unsafe work begins when required pre-execution audit fails, and no false success is returned after terminal audit failure.

**P0-03: Bind verification to the exact result**
- Inspect: `nexus/core.py`, verification/evidence APIs and tests.
- Proposed fix: store canonical result bytes or canonical JSON, SHA-256 digest, verifier principal, verification method/version, acceptance criteria IDs, evidence IDs, timestamp and verdict. Verification must refer to the exact result digest and exact task/project. The executor cannot verify its own work under the same trusted principal.
- Exact source quote matching proves quote presence only; it must not alone claim that a source semantically supports an arbitrary conclusion. Distinguish source-integrity checks from claim-support verification.
- Test wrong task/project evidence, modified result after verification, missing digest, same executor/verifier, untrusted verifier identity, and failed acceptance criteria. COMPLETE must be denied.

**P0-04: One authoritative transition and policy gate**
- Inspect: `nexus/core.py`, all REST/MCP state-changing handlers.
- Proposed fix: every state change passes through one core transition service. Reject direct jumps, invalid recovery routes, policy bypasses and transitions that do not satisfy dependencies. The model never sets state directly.
- Test every allowed and disallowed transition; include direct RECOVER→EXECUTE, policy bypass through MCP, cross-project dependencies, dependency cycles and incomplete dependencies.

### P1 — Idempotency, recovery, routing and consistency

**P1-01: Side-effect-aware idempotency**
- Inspect: `nexus/idempotency.py`, dispatcher and provider/tool adapters.
- Proposed fix: define idempotency at the execution-attempt/tool boundary, not just at the API transition. Persist key, tenant/project/task scope, tool name, canonical request fingerprint, status, provider idempotency token where supported, timestamps, and result reference. Use atomic claim/update transactions.
- Status model: NEW → IN_PROGRESS → COMPLETED; uncertain crash/timeout becomes UNCERTAIN. IN_PROGRESS/UNCERTAIN must never silently re-execute. Add a documented reconciliation operation requiring an authorized reviewer/operator.
- Test concurrency, same-key replay, changed payload, cross-tenant key collision, process restart, timeout before/after side effect, stale claim and provider response lost after success.

**P1-02: Durable checkpoints and recovery policy**
- Proposed fix: checkpoint before each risky side effect and after each confirmed stage. Store state version, plan/policy version, attempt ID, prior state, expected next state and artifact/result references. Recovery resumes from last safe checkpoint but re-runs policy validation before any new side effect.
- Test crash at every stage; prove no duplicate effect and no jump over evidence, policy or verification.

**P1-03: Provider-neutral free-first router**
- Inspect: `nexus/router.py`, `nexus/runlog.py`.
- Proposed fix: keep routing logic provider-independent. Adapters declare capabilities, availability/quota evidence, cost classification, required permission, timeout/retry semantics, side-effect/idempotency support and verification method. Unknown quota or capability is not treated as true.
- Paid route requires explicit user/project permission and budget approval. Fallback is allowed only when failure is classified as safe and the previous attempt is proven not to have caused an effect. A verification failure must not trigger a second provider/tool execution automatically.
- Test fake adapters deterministically for free-first, unknown preflight, paid denial, safe/unsafe fallback, timeout, verification failure and run-log failure.

**P1-04: Atomic storage boundaries**
- Inspect all SQLite use in core, authorization, evidence, records, idempotency and runlog.
- Proposed fix: define transaction ownership, foreign keys, busy/lock behavior and migration versioning. Prefer one transaction for state + required records when stored in one database. If stores can be split via environment variables, document that cross-database atomicity is not guaranteed and use explicit outbox/reconciliation semantics.
- Test concurrent transitions, simultaneous idempotency claims, DB locked/full/read-only errors, partial migrations and restart recovery.

**P1-05: Rate limiting and identity hardening**
- Proposed fix: keep process-local limiter clearly marked development/single-worker only. Production multi-worker rate limiting requires a shared backend and atomic counters; do not claim protection until it is implemented and tested.
- Add credential rotation/revocation, expiry where appropriate, least-privilege scopes, secret-safe errors, and HTTPS deployment requirements.

### P2 — Contract, operability and maintainability

- Keep REST and MCP thin adapters over the same use cases; generate/validate contracts from shared schemas where practical.
- Add API versioning and documented error codes; validate `openapi.yaml` against actual runtime schemas.
- Add structured logs with trace_id, request_id, project_id, task_id, attempt_id, policy version and terminal status; redact credentials and sensitive payloads.
- Add schema migration tests, backup/restore instructions, retention policy and operational health/readiness checks. Health must not disclose secrets or internal state.
- Pin and audit dependencies; make setup reproducible; test supported Python versions.
- Map every requirement to implementation, test and recorded evidence in `docs/PROJECT_CONTROL_API_TRACEABILITY.md`.

## 4. OpenAI must be an adapter, not the core

Current code includes `nexus/openai_adapter.py` and OpenAI-specific planner/proposal modules. Proposed refactor:

1. Define interfaces such as `ModelProvider`, `PlanProvider`, and `StructuredOutputProvider` in a vendor-neutral module (suggested `nexus/providers/contracts.py`).
2. Move OpenAI SDK imports and Responses API specifics into `nexus/providers/openai_provider.py`.
3. Add a deterministic fake provider used by unit/contract tests. It must work offline and require no API key.
4. Add a second adapter only if a real need and verified official documentation justify it; do not introduce another vendor solely to satisfy a checklist.
5. Core consumes typed proposals; validates schema, provenance and bounds; then asks the deterministic policy engine to authorize every tool call.
6. Provider failure, malformed output, quota unknown, missing credentials or unavailable network must leave task state recoverable and must not bypass policy.
7. Tests for state machine, authorization, evidence, idempotency, audit and recovery must run with no OpenAI package, key or network access.
8. Provider-specific evaluation/quality is separate from controller safety. A model's confidence or assertion is not a policy decision and not proof of task completion.

Acceptance criterion: run the core test suite in an environment with no `OPENAI_API_KEY`, no provider credentials and no network; all domain, policy, persistence, auth, audit, idempotency and recovery tests must pass. Provider adapter tests may use injected mock clients. Live provider tests are separate and must be labeled distinctly.

## 5. Test evidence model — distinguish actual use from CI

The reviewer must report evidence by layer, not collapse all evidence into a single pass/fail:

- **SOURCE REVIEW:** exact code inspected at exact commit.
- **UNIT/CONTRACT CI:** automated tests and their actual job URLs/results.
- **CONTROLLED RUNTIME:** a real request/tool invocation with request ID, task ID, trace ID, result and audit records.
- **CHATGPT/PLUGIN INTERACTION:** a real end-to-end call from the connected ChatGPT/plugin interface, with captured request/result/audit evidence.
- **EXTERNAL PROVIDER:** real provider call/quota behavior, only if configured and explicitly tested.
- **DEPLOYMENT:** HTTPS/authentication/operational behavior on the target environment, only if actually deployed and authorized.

Using ChatGPT as the operator is valid runtime evidence for the behaviors observable in that interaction. It is not by itself proof of an unobserved REST/MCP endpoint, durable database write or external side effect. Conversely, an unavailable external provider does not invalidate unrelated controller/runtime tests. Mark only the specific untested capability NOT RUN or BLOCKED.

Never fabricate trace IDs, logs or runtime records. If records do not exist or cannot be accessed, say exactly that.

## 6. Implementation sequence and gates

### Phase A — Baseline and reproduce
- Freeze the inspected commit and record branch/HEAD.
- Run current CI and tests; preserve outputs.
- Map each P0/P1 requirement to current code and test.
- Reproduce each alleged defect with a minimal failing test or mark it unconfirmed.

**Exit gate:** findings have evidence, no guesses are labeled confirmed.

### Phase B — P0 safety fixes
- Fix principal/tenant authorization.
- Make audit outcome failures explicit and safe.
- Bind verification to immutable result digests and independent identity.
- Centralize state transitions/policy gates.
- Add regression and fault-injection tests.

**Exit gate:** all P0 tests pass; negative cases fail closed; no COMPLETE state without required durable evidence.

### Phase C — P1 reliability fixes
- Extend idempotency to side-effect boundary.
- Implement UNCERTAIN reconciliation and safe recovery.
- Test checkpoint and DB failures.
- Harden router fallback, paid-budget and concurrency behavior.

**Exit gate:** no unsafe duplicate side effects in tested failure scenarios; uncertain outcomes remain visible and blocked pending reconciliation.

### Phase D — Vendor-neutral refactor
- Define provider contracts.
- Move OpenAI-specific behavior behind adapter boundary.
- Run core suite offline without API keys.
- Verify model tool proposals cannot bypass deterministic authorization.

**Exit gate:** core tests do not require OpenAI SDK/key/network; adapter-specific tests remain separately identified.

### Phase E — Contract and runtime validation
- Validate REST/MCP parity and OpenAPI contract.
- Run controlled runtime tests and capture real records.
- Run plugin round-trip only when endpoint is available and plugin changes are explicitly approved.
- Validate deployment security separately if deployment is authorized.

**Exit gate:** runtime evidence is reproducible and traceable; blockers are explicitly listed.

### Phase F — Release review
- Update traceability and changelog.
- Run CI against the exact final commit.
- Reviewer issues a report with pass/fail/partial/not-run per acceptance criterion.
- Keep PR Draft until P0/P1 gates pass and user approves any release action.

## 7. Required independent-review output

Return:
1. Exact repository, branch, head SHA, base SHA and review time.
2. Verdict: READY FOR REVIEW / NEEDS FIXES / BLOCKED (not production approval).
3. P0/P1/P2 findings with code locations, reproduction steps, expected/actual results, evidence and proposed patch.
4. Which proposed fixes were applied, commit SHA, changed files and regression tests.
5. Separate results for source review, CI, controlled runtime, ChatGPT/plugin interaction, provider and deployment.
6. Requirement traceability: requirement → source → test → observed evidence → status.
7. Remaining unknowns and precise evidence needed to close them.
8. Merge and deployment gates listed separately.

## 8. Scope and safety of remediation

The reviewer may propose code changes only within this repository and target work branch if authorized for implementation. Prefer small, reviewable commits with regression tests. Do not push to `main`, merge PR #4, deploy, expose services, modify secrets, register/update plugins or change external systems without separate explicit approval. Do not alter `iris-step1` or `iris-controller`.

## 9. Initial readiness verdict

**NEEDS INDEPENDENT REVIEW AND FIXES — NOT PRODUCTION READY.**

The existing CI result is useful evidence for the commit it tested, but it does not close the listed security, durability, recovery, provider-neutrality or live-runtime criteria. This document prepares the review and renovation path; it does not claim those changes have been implemented or tested yet.
