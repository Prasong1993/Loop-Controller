# Project Control API — Requirement Traceability

Updated: 2026-10-11
Scope: repository evidence and implementation tracking for this repository only.
Baseline: `main` at `eb5359505bf39e4ca1dcd3512f2b8ea3ac6e8baa`.
Work branch: `work/project-control-api-hardening-2026-10-11`.
This register distinguishes source inspection from executed tests and live integration. A source file existing does not prove its feature is complete. Latest work-branch verification: CI run #244 passed on Python 3.11, 3.12 and 3.13 for commit `39c1ebdd3d442d628631b4346ecd565d1268b947`.

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
| Project and task identity/state | `nexus/core.py`, `nexus/api.py` | `tests/test_core.py`, `tests/test_api.py` | VERIFIED-SOURCE; latest branch CI pending |
| Legal state transitions and evidence gate | `nexus/core.py` | `tests/test_core.py` | PASS-CI on work branch: direct `RECOVER → EXECUTE` is rejected; recovery must return through planning/policy. Run #244 |
| Evidence ingestion and source quote | `nexus/evidence.py`, `nexus/core.py` | `tests/test_evidence.py`, `tests/test_core.py` | PARTIAL: exact quote presence is not semantic claim support |
| Deterministic policy / permission gate | `nexus/core.py`, `nexus/capabilities.py`, `nexus/openai_adapter.py` | `tests/test_core.py`, `tests/test_capabilities.py`, `tests/test_openai_adapter.py` | VERIFIED-SOURCE; policy isolation/security review remains |
| Tool routing and Free-first | `nexus/core.py`; proposed router in PR #3 | `tests/test_core.py`; `tests/test_router.py` on PR #3 only | main has basic candidate selection; PR #3 is not part of main and its latest CI failed |
| Budget approval | `nexus/core.py`, `nexus/openai_planner.py`, `nexus/code_proposal.py` | `tests/test_core.py`, `tests/test_openai_planner.py`, `tests/test_code_proposal.py` | PARTIAL; paid routing/real provider budgets require broader integration tests |
| Mandatory operational recording before tool dispatch | `nexus/openai_adapter.py` | `tests/test_openai_adapter.py::test_mandatory_record_failure_stops_before_tool_execution` | PASS-CI on work branch: record failure results in one provider request, zero handler calls, and immediate stop. Run #244 |
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
- Work branch commit `39c1ebdd3d442d628631b4346ecd565d1268b947` also removes the direct `RECOVER → EXECUTE` transition and adds a regression test; run [#244](https://github.com/Prasong1993/Loop-Controller/actions/runs/38076505103) passed on Python 3.11–3.13. Each matrix job ran the OpenAPI contract checks (4 tests) and full unit suite (81 tests).
- No production deployment, live OpenAI provider call, or Plugin Creator round-trip was run.

## Next verification gates

1. Read back the latest branch diff and preserve both regression fixes.
2. Expand tests for project-level permissions, idempotency and checkpoint restoration under partial execution.
3. Keep PR #1–#3 changes isolated until reviewed; do not infer main includes them.
4. Require secured HTTPS endpoint, actual account/plugin configuration, and real round-trip evidence before marking live integration PASS.
