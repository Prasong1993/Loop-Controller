# Project Control API — Requirement Traceability

Updated: 2026-10-11
Scope: repository evidence and implementation tracking for this repository only.
Baseline: `main` at `eb5359505bf39e4ca1dcd3512f2b8ea3ac6e8baa`.
Work branch: `work/project-control-api-hardening-2026-10-11`.
This register distinguishes source inspection from executed tests and live integration. A source file existing does not prove its feature is complete. Latest fully confirmed work-branch verification before task-dependency changes: CI run #252 passed on Python 3.11, 3.12 and 3.13. Task dependency implementation and tests are now on the branch; their final CI result is pending.

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
| Project and task identity/state | `nexus/core.py`, `nexus/api.py` | `tests/test_core.py`, `tests/test_api.py` | PASS-CI on prior branch increment; task-dependency extensions added afterward and await final CI |
| Legal state transitions and evidence gate | `nexus/core.py` | `tests/test_core.py` | PASS-CI on work branch: direct `RECOVER → EXECUTE` is rejected; recovery must return through planning/policy. Run #244 |
| Task dependencies and DAG safety | `nexus/core.py`, `nexus/api.py`, `nexus/mcp_server.py`, `openapi.yaml` | `tests/test_core.py`, `tests/test_api.py`, `tests/test_openapi_contract.py` | Implementation added: same-project dependencies, cycle/duplicate rejection, pre-policy editing restriction, and EXECUTE blocked until dependencies are COMPLETE; final CI pending |
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
