# Project Control API — Requirement Traceability

Updated: 2026-10-11
Scope: repository evidence and implementation tracking for this repository only.
Baseline: `main` at `eb5359505bf39e4ca1dcd3512f2b8ea3ac6e8baa`.
Work branch: `work/project-control-api-hardening-2026-10-11`.
This register distinguishes source inspection from executed tests and live integration. A source file existing does not prove its feature is complete. Latest work-branch verification: CI run #262 passed on Python 3.11, 3.12 and 3.13 for commit `17eddd28d6ca87b04dd4697b829ddf5787e2302c`; each matrix job passed 4 OpenAPI contract tests and 97 unit tests.

## Evidence states

- **VERIFIED-SOURCE** — source or documentation read from the stated Git ref.
- **PASS-CI** — GitHub Actions completed successfully for the exact commit.
- **FAIL-CI** — GitHub Actions reported failure for the exact commit.
- **NOT RUN** — no execution evidence is available.
- **BLOCKED** — a required environment, permission, or prerequisite is unavailable.
- **PARTIAL** — implementation exists but acceptance coverage is incomplete.

## Requirement → Source → Test → Verification

| Requirement | Source / module | Test case(s) | Current evidence / remaining work |
|---|---|---|---|
| Project and task identity/state | `nexus/core.py`, `nexus/api.py` | `tests/test_core.py`, `tests/test_api.py` | PASS-CI run #262; task dependency tests also passed |
| Legal state transitions and evidence gate | `nexus/core.py` | `tests/test_core.py` | PASS-CI on work branch: direct `RECOVER → EXECUTE` is rejected; recovery must return through planning/policy. Run #244 |
| Task dependencies and DAG safety | `nexus/core.py`, `nexus/api.py`, `nexus/mcp_server.py`, `openapi.yaml` | `tests/test_core.py`, `tests/test_api.py`, `tests/test_openapi_contract.py` | PASS-CI run #262: same-project dependencies, cycle/duplicate rejection, pre-policy editing restriction, and EXECUTE blocked until dependencies are COMPLETE |
| Evidence ingestion and source quote | `nexus/evidence.py`, `nexus/core.py` | `tests/test_evidence.py`, `tests/test_core.py` | PARTIAL: exact quote presence is not semantic claim support |
| Deterministic policy / permission gate | `nexus/core.py`, `nexus/capabilities.py`, `nexus/openai_adapter.py` | `tests/test_core.py`, `tests/test_capabilities.py`, `tests/test_openai_adapter.py` | VERIFIED-SOURCE; policy isolation/security review remains |
| Tool routing and Free-first | `nexus/router.py`, `nexus/runlog.py`, `nexus/core.py` | `tests/test_router.py`, `tests/test_core.py` | IMPLEMENTED ON WORK BRANCH; PASS-CI run #249: free-first, explicit budget approvals, quota preflight, safe fallback classification, verification stop, durable run events and checkpoints. No live provider adapter is configured |
| Budget approval | `nexus/core.py`, `nexus/openai_planner.py`, `nexus/code_proposal.py` | `tests/test_core.py`, `tests/test_openai_planner.py`, `tests/test_code_proposal.py` | PARTIAL; paid routing/real provider budgets require broader integration tests |
| Mandatory operational recording before tool dispatch | `nexus/openai_adapter.py` | `tests/test_openai_adapter.py::test_mandatory_record_failure_stops_before_tool_execution` | PASS-CI on work branch: record failure results in one provider request, zero handler calls, and immediate stop. Run #249 |
| Checkpoint/recovery | `nexus/core.py`, `nexus/api.py`, `nexus/mcp_server.py` | `tests/test_core.py`, `tests/test_api.py`, `tests/test_mcp_server.py` | PARTIAL; crash/partial side-effect recovery and concurrency remain |
| Audit / operational records | `nexus/core.py`, `nexus/records.py` | `tests/test_records.py`, `tests/test_api.py`, `tests/test_mcp_server.py` | PARTIAL; mandatory records and non-swallowed failures need explicit contract per operation |
| REST contract | `nexus/api.py`, `openapi.yaml` | `tests/test_api.py`, `tests/test_openapi_contract.py` | Source present; CI run #241 pending |
| MCP adapter | `nexus/mcp_server.py` | `tests/test_mcp_server.py` | Source present; live external client test NOT RUN |
| Retry/idempotency/duplicate side effects | `nexus/openai_adapter.py`, router candidate code | `tests/test_openai_adapter.py`, `tests/test_router.py` (PR #3) | PARTIAL; no general durable idempotency key/execution ledger proven |
| Authentication / permissions / rate limiting | `nexus/api.py`, `nexus/mcp_server.py` | `tests/test_api.py`, `tests/test_mcp_server.py` | PARTIAL: bearer gate is prototype; production identity, project-level authorization, and rate limiting remain open |
| Independent verification before completion | `nexus/core.py`, `nexus/api.py` | `tests/test_core.py`, `tests/test_api.py` | PARTIAL: workflow has VERIFY state; independent executor-result verification is not established for all actions |
| Plugin Creator live integration | `docs/CHATGPT_INTEGRATION_CONTRACT.md`, `openapi.yaml`, `nexus/mcp_server.py` | live round-trip acceptance suite not yet configured | NOT RUN / BLOCKED by secured HTTPS deployment and account-side integration setup |

## CI evidence

- Existing PR #3 run [#240](https://github.com/Prasong1993/Loop-Controller/actions/runs/38072692317) failed on commit `a706343877d9bb27202212054b958828c15040bf`; 92 tests ran and `test_mandatory_record_failure_stops_before_tool_execution` failed because a request-start record callback raised before the provider call, giving 0 calls rather than the test's expected 1. The tool handler was not executed.
- Work branch commit `11b33ba6f3cda9b9043d3758c4640a26f90ee570` adds a deferred fail-closed record gate and the regression test; run [#241](https://github.com/Prasong1993/Loop-Controller/actions/runs/38076402884) passed on Python 3.11–3.13.
- Work branch commit `39c1ebdd3d442d628631b4346ecd565d1268b947` removes the direct `RECOVER → EXECUTE` transition and adds a regression test; run [#244](https://github.com/Prasong1993/Loop-Controller/actions/runs/38076505103) passed on Python 3.11–3.13.
- Reviewed and ported the deterministic router from the unmerged feature branch into this work branch as isolated source files; it was not merged from or into PR #3. Controller-backed stage checkpoints and the append-only router run/event ledger were added. Run [#249](https://github.com/Prasong1993/Loop-Controller/actions/runs/38076731270) passed on Python 3.11–3.13; each job ran 4 OpenAPI tests and 94 unit tests, including checkpoint-persistence failure blocking provider execution.
- No production deployment, live OpenAI provider call, or Plugin Creator round-trip was run.

## Next verification gates

1. Read back the latest branch diff and preserve both regression fixes.
2. Expand tests for project-level permissions, durable idempotency and checkpoint restoration under partial execution.
3. Wire only explicitly registered server-side adapters to a runtime entry point; never accept executable adapter code from API input.
4. Keep PR #1–#3 unchanged; these changes are isolated on the work branch and do not change `main`.
5. Require secured HTTPS endpoint, actual account/plugin configuration, and real round-trip evidence before marking live integration PASS.


## 2026-10-11 — Authorization, idempotency and completion verification follow-up

Latest verified code baseline before this documentation update: `f55f07aabad2dd2b8769017517ec2d8b7c7d1445`. GitHub Actions run [#281](https://github.com/Prasong1993/Loop-Controller/actions/runs/38079224483) passed Compile, OpenAPI contract validation and unit tests on Python 3.11, 3.12 and 3.13.

| Requirement | Source / tests | Status | Evidence / remaining gap |
|---|---|---|---|
| Project membership and tenant isolation | `nexus/authorization.py`, `nexus/api.py`, `nexus/mcp_server.py`; `tests/test_api.py::test_project_level_authorization_denies_cross_tenant_reads_and_writes`, `tests/test_mcp_server.py::test_mcp_project_access_denies_cross_tenant_principal` | **VERIFIED-TESTED / PARTIAL** | REST and MCP support configured `NEXUS_API_TOKENS` principal mapping and persisted project membership. The legacy single `NEXUS_API_KEY` maps all holders to the same principal and is not a multi-tenant identity system. Membership provisioning is not yet an authenticated admin API. |
| Read-only project role | `nexus/authorization.py`, `nexus/api.py`, `nexus/mcp_server.py` | **PARTIAL** | OWNER/MEMBER may write; READ_ONLY may read. Dedicated negative tests for read-only write denial remain to be added. |
| Durable idempotency | `nexus/idempotency.py`, `nexus/api.py`, `tests/test_idempotency.py`, `tests/test_api.py` | **PARTIAL** | The REST transition to EXECUTE requires an Idempotency-Key. Completed responses are replayed from storage; mismatched keys conflict; IN_PROGRESS/UNCERTAIN records block automatic replay after timeout/crash. This is not a generalized idempotency contract for arbitrary external side effects, and there is no automated reconciliation workflow. |
| Independent verification before COMPLETE | `nexus/core.py`, `nexus/api.py`, `nexus/mcp_server.py`; `tests/test_core.py`, `tests/test_api.py` | **PARTIAL** | COMPLETE now requires a persisted passing verification joined back to VERIFIED project/task-scoped evidence. The verifier must be a distinct authenticated principal from the recorded EXECUTE actor. Semantic claim support, trusted verifier provisioning, and a required result digest still need stronger assurance. |
| Rate limiting | `nexus/api.py`, `nexus/mcp_server.py`; `tests/test_api.py::test_rate_limit_returns_429_after_configured_budget` | **VERIFIED-TESTED / PARTIAL** | Configurable per-process, per-client-IP limiter returns 429. It is not distributed across multiple workers/replicas and is not a production-grade abuse-control boundary. |
| Mandatory audit fail-closed | `nexus/api.py`, `nexus/mcp_server.py`; `tests/test_api.py::test_mandatory_start_audit_failure_stops_before_project_creation`, router checkpoint-failure test | **PARTIAL** | REST request-start and MCP tool-start records must persist before business/tool execution; failure stops the request. Some completion/error outcome records remain best-effort and swallowed, so mandatory end-to-end audit is not yet VERIFIED. |
| Timeout/crash/partial side-effect recovery | `nexus/idempotency.py`, `nexus/core.py`, `nexus/router.py`; `tests/test_idempotency.py`, `tests/test_router.py` | **PARTIAL** | A crash-like abandoned claim remains blocked from replay. Real provider/tool partial-side-effect fault injection and operator reconciliation are NOT RUN. |
| Live Plugin Creator integration | `docs/CHATGPT_INTEGRATION_CONTRACT.md`, `openapi.yaml`, `nexus/mcp_server.py` | **BLOCKED / NOT RUN** | No secured HTTPS endpoint, production identity, or real client round-trip has been approved or tested. No service was deployed. |

### Release gate

Do not mark this branch production-ready yet. Remaining gates include distributed rate limiting, non-swallowing completion audit semantics, a trusted identity/membership administration model, semantic/independent result verification, external-side-effect idempotency/reconciliation, provider fault-injection integration tests, and a secured HTTPS deployment plus actual Plugin Creator round-trip. Deployment and plugin registration remain unperformed pending explicit approval.
