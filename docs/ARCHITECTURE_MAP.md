# NEXUS Architecture & Connection Map
Updated: 2026-10-10
Status: implementation map for this repository; static source review, not a deployment claim.

## 1. Goal and boundary
NEXUS is a controller layer, not a replacement for OpenAI models or the ChatGPT app. OpenAI capabilities are replaceable worker/tool adapters. Deterministic NEXUS code owns project/task state, evidence acceptance, policy gates, operational records and verification. Model output is a proposal or tool request, never authorization.

## 2. End-to-end flow
`Request → Scope/Project → Evidence → [Structured Plan | Code Proposal | Read-Only Tool Request] → Deterministic Policy → Allowlisted Adapter → Observed Result → Verification → Audit/Records → Checkpoint/Recovery → Completion`

Any missing permission, required evidence, budget approval, tool registration or verification result routes to `BLOCKED` or a targeted `RECOVER`; it must not be silently treated as success.

Capability enablement is centralized in `nexus/capabilities.py`; see [OpenAI Capability Matrix](OPENAI_CAPABILITY_MATRIX.md). The registry deliberately enables only model-verified tools and leaves code execution, computer use and patch application disabled until their runtime and policy contracts are proven.

## 3. Component connection map

| Component | Owns | Inputs | Outputs / next connection | Must not own |
|---|---|---|---|---|
| REST API (`nexus/api.py`) | HTTP validation, auth gate, status/error mapping, request trace | Client request | Core calls, OpenAI proposal/run, record search | Model judgment as policy |
| MCP adapter (`nexus/mcp_server.py`) | MCP transport and tool schemas; auth; tool operation trace | MCP client/tool request | Same core and record store as REST | Separate workflow rules/state |
| Workflow core (`nexus/core.py`) | Project/task states, allowed transitions, deterministic policy, evidence gate, audit | Typed command and current DB state | Allow/deny/state change; evidence result | LLM calls or caller-supplied evidence proof |
| Evidence fetcher (`nexus/evidence.py`) | Conservative HTTPS retrieval, SSRF/redirect/body controls, exact quote matching | Public HTTPS URL + requested quote | Retrieved-source verification result | Deciding project policy |
| OpenAI planner (`nexus/openai_planner.py`) | Structured plan proposal via Responses API; optional documented capabilities | Task, constraints, allowed capability list, server-side budget gate | Typed `PROPOSAL_ONLY`, usage/error record | Executing proposed steps or approving policy |
| Code proposal generator (`nexus/code_proposal.py`) | Structured code-file proposal through Responses API using coding model | Task, explicit allowlisted file paths, constraints, double budget gate | File contents + rationale + tests/risks as `PROPOSAL_ONLY`; records only hashes/metadata | Writing files, executing code, claiming tests ran, or approving its own changes |
| OpenAI worker (`nexus/openai_adapter.py`) | Responses API loop and function-call orchestration | Prompt + allowlisted tool schemas | Model text/tool proposals; calls policy callback before handler | Direct arbitrary shell/code/network side effects |
| Tool adapters/handlers | Narrow operations such as read status/task/audit | Validated tool args | Bounded result | Unlisted tools or cross-project access |
| Operational Record Store (`nexus/records.py`) | Searchable append-only usage/error/decision/evidence/checkpoint/verification events | Redacted structured event | Traceable record IDs and paginated search; schema documented in [OPERATIONAL_RECORD_SCHEMA.md](OPERATIONAL_RECORD_SCHEMA.md) | Raw prompts, secrets, unbounded payloads |
| SQLite persistence | Durable state and records | Core/record transactions | State, evidence, audit, operational records | Cross-database atomicity assumptions |
| Tests/CI | Reproducible contract and regression checks | Fixtures and fake provider clients | Test results for defined scope | Claiming live provider or mobile integration |

## 4. Critical interfaces and invariants
1. REST and MCP must call the same deterministic core; no duplicated business rules.
2. `VERIFIED` evidence can only be created by a trusted fetch-and-match boundary; caller-supplied text is never proof.
3. OpenAI plan generation requires both request approval and a server-side budget approval setting; absent approval means no provider call. The current default model is `gpt-6-luna` based on the official model catalog; actual account access and current price must be checked before enabling spend. Only model-verified optional tools are enabled through `nexus/capabilities.py`. The code proposal endpoint uses `gpt-6-astra` by default (or reviewed `gpt-6.1-sol`) and never writes files or executes code.
4. OpenAI function calls must be declared, registered, parsed, project-scoped and explicitly ALLOWed by deterministic policy before a handler runs.
5. The OpenAI `/ai/run` allowlist is read-only: project status, task detail, audit. MCP separately exposes workflow mutations (create task, request state transition, checkpoint/restore, evidence recording); each uses the same core gate, but tenant/user authorization is still only a shared bearer token and remains a production blocker. No arbitrary shell or code-execution tool is exposed by the OpenAI worker.
6. Every request/tool/provider action records a traceable redacted operational event where possible. Logging failure must never turn a denied action into an allowed action.
7. Project/task/evidence/audit state and operational records use SQLite in the current implementation; a transaction spanning separate databases is not assumed atomic. Prefer one configured database path unless isolation is intentionally configured.
8. Model/provider failures are not automatically retried if a tool may have side effects. Current exposed OpenAI tools are read-only; any future side-effecting tool requires idempotency and ambiguous-outcome reconciliation.
9. `COMPLETE` is a controller state reached only after required verification and audit gates; a model's statement that work is done is not evidence.
10. Health endpoints and static CI do not prove a remote service is deployed or usable from ChatGPT mobile.

## 5. State and record map
- Evidence records have optional `task_id`: task-scoped VERIFIED evidence unlocks only that task; evidence with no task_id is explicitly project-wide and may support any task in that project. Cross-project task links are rejected. Existing SQLite databases are migrated by adding the nullable column and index.
- Workflow states: `INTAKE → RESEARCH → PLAN → POLICY → EXECUTE → VERIFY → AUDIT → COMPLETE`; `RECOVER` and `BLOCKED` are controlled exception states.
- Operational record types: `usage`, `error`, `evidence`, `decision`, `checkpoint`, `verification`.
- Correlation keys: `project_id`, `task_id`, `session_id`, `trace_id`, `operation_id`; sensitive request/response bodies should not be persisted.
- Each operational record should preserve timestamp, actor, component, status, stable error code, severity, redacted summary/payload, and relation to the workflow/task where known.

## 6. Known integration gaps to close before release
- Validate every REST and MCP tool mapping against current schemas and tests.
- Prove core evidence verification cannot be bypassed through any endpoint, MCP tool or direct method.
- Expand source-fetch tests with adversarial live DNS/IPv4/IPv6 and TLS cases; unit tests currently prove the connection uses the pinned validated IP and original TLS hostname, but do not establish production network resilience.
- Align REST/MCP health version with `nexus/version.py`.
- Ensure tool instrumentation covers every exported MCP tool and does not leak arguments/secrets.
- Expand malformed tool-call, concurrency/idempotency and recovery tests; an in-process REST lifecycle and cross-project tool/evidence denial tests now pass in CI.
- Run CI on the exact final commit and inspect failed job logs; do not infer a pass from a previous commit.
- Public deployment, ChatGPT app registration and Android/mobile invocation remain unverified until tested live.

## 7. Verification vocabulary
`STATIC INSPECTION` is not `UNIT TEST`; `UNIT TEST` is not `INTEGRATION TEST`; `INTEGRATION TEST` is not `REMOTE E2E`; none of these is a `PRODUCTION SMOKE TEST`. Report each level separately.
