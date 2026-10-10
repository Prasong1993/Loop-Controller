# NEXUS — Error, Defect, and Limitation Report

Report ID: NEXUS-ERR-001  
Date: 2026-10-10  
Scope: repository baseline, controller increment, and ChatGPT-app-first integration feasibility. This is not a claim that ChatGPT integration or production tests passed.

## Summary
- Core implemented: deterministic Python/SQLite state machine, evidence and execution gates, route selection, audit events and checkpoint creation.
- API and tests are included in source. Test results are not claimed until execution/CI is observed.
- Separate native mobile clients are intentionally out of scope. Physical Android/iOS/iPadOS tests are not a gate for the current ChatGPT-app-first scope; real ChatGPT integration is not configured and is NOT RUN.
- Production authentication, TLS, deployment and credentials are not configured.
- Official platform guidance confirms that mobile background execution is constrained.

## Findings
| ID | Severity | Finding | Status | Action |
|---|---|---|---|---|
| NXR-E001 | Low | Native Android/iOS/iPadOS client apps not implemented | OUT OF SCOPE | Do not implement unless native/OS-specific functionality is approved |
| NXR-E002 | Low | Physical-device tests not performed | NOT REQUIRED FOR CURRENT SCOPE | Only test devices when native/OS-specific behavior is added or a device-specific issue appears |
| NXR-E003 | High | Production authentication/TLS/secrets not configured | OPEN | Add auth, secrets manager and security review before public exposure |
| NXR-E004 | High | ChatGPT integration availability and live round-trip not confirmed | NOT RUN / UNKNOWN | Configure a supported connector/API integration and execute acceptance tests in the actual ChatGPT app/account |
| NXR-E005 | Medium | Repository is named Loop-Controller, not NEXUS | OPEN | Rename through repo settings/admin UI or supported API |
| NXR-E006 | Low | CI result not confirmed | SUPERSEDED BY CI EVIDENCE | See latest successful GitHub Actions run below |
| NXR-E007 | High | Production-grade identity, authorization and tenant isolation incomplete | OPEN | Add auth principal and adversarial isolation tests |
| NXR-E008 | Medium | Checkpoint creation exists; restore/resume not implemented | OPEN | Implement restore semantics and recovery tests |
| NXR-E009 | Medium | VERIFIED evidence currently requires a URL but does not fetch/verify its content | OPEN | Add source/quote/section/freshness/reviewer validation |
| NXR-E010 | Medium | Router is a selector, not a provider-adapter execution system | OPEN | Define adapters, health checks, idempotency and error contracts |

## Error-handling contract
- Illegal state transition: reject with InvalidTransition.
- Policy gate failure: reject with PolicyDenied.
- Unknown task/project: reject with ValueError (initial HTTP wrapper maps this to HTTP 409; refine to 404).
- Warning, missing capability/permission, or unapproved paid cost: block route; no blind retry.
- Unexpected runtime failure: production redacted logging and persistent error codes still need hardening.

## Verification status
- Source files: will be verified by GitHub read-back.
- Python unit tests: INCLUDED; execution status not yet claimed.
- GitHub Actions: CONFIGURED; result not yet claimed.
- Security review: NOT RUN.
- Native device tests: NOT RUN.
- Production readiness: NOT READY.


## CI update — 2026-10-10 (supersedes NXR-E006's earlier NOT RUN status)
GitHub Actions run #9 completed successfully for commit 4b61e19daa6301ebbe70595b8b44e1581074df88. All three matrix jobs passed: Python 3.11, 3.12, and 3.13. Each job completed dependency installation, compileall, and unittest discovery successfully.
Run: https://github.com/Prasong1993/Loop-Controller/actions/runs/38011520599

Updated statuses:
- Source read-back: VERIFIED.
- CI compile + unit test workflow: PASS on Python 3.11/3.12/3.13.
- Security review, production deployment, auth/TLS, checkpoint restoration and ChatGPT-app integration: NOT RUN / OPEN.
- Physical Android/iOS/iPadOS device testing: not required for current scope; becomes applicable only if native or OS-dependent functionality is introduced.
- Overall production readiness: NOT READY.

## Scope correction — ChatGPT-app-first (2026-10-10)
The earlier wording treated native mobile clients and physical device tests as required gaps. That was not aligned with the intended product. NEXUS is intended to be used through the ChatGPT application across Android, iOS and iPadOS, not through separate native NEXUS apps. Therefore native clients and device-matrix tests are OUT OF SCOPE for the current increment.

**New release acceptance blocker:** the NEXUS controller is currently repository code/local FastAPI, not a deployed and connected ChatGPT integration. The following remain NOT RUN until the integration is actually configured: connector discoverability for the user's account, authorized task create/read round-trip, policy-denial behavior, audit retrieval, and warning/error handling. A green CI workflow does not prove ChatGPT integration works.


## Scope and acceptance correction — 2026-10-10

Native Android/iOS/iPadOS NEXUS clients and physical-device matrix testing are **OUT OF SCOPE / NOT REQUIRED** for the current ChatGPT-app-first target. These become applicable only if approved native or OS-dependent features are added.

The real release blocker is that the controller/API has not been deployed securely or connected to the target ChatGPT account. Live integration checks (tool availability, authorized task round-trip, policy denial, audit readback and warning/timeout behavior) remain **NOT CONFIGURED / NOT RUN**. CI success does not close this blocker.

The following remain open before production: authentication/authorization, TLS, secrets management, tenant isolation, source-content evidence verification, checkpoint restoration, idempotency/recovery, and supported ChatGPT integration adapter.


## Implementation update — guarded restore and API access gate

- Implemented guarded checkpoint restore in `nexus/core.py`. Restore requires the task to be BLOCKED/RECOVER, only restores safe workflow metadata states, refuses EXECUTE-state checkpoints, and writes a CHECKPOINT_RESTORED audit event.
- Added `POST /tasks/{task_id}/restore` and API bearer-token gate in `nexus/api.py`. Remote requests fail closed if `NEXUS_API_KEY` is absent; health remains public. Unknown identifiers now map to 404, policy denials to 403, and invalid transitions to 409.
- Added API authentication/error mapping tests and core restore tests. These are **implemented but CI status for the newest commit is pending verification**.
- Remaining gaps: account-specific ChatGPT connector selection/configuration, secure deployment, production identity/tenant isolation, evidence content verification, provider execution adapters and restore idempotency/production review.


## Implementation update — source verification and MCP adapter

- Added `nexus/evidence.py`: HTTPS-only source fetching, rejects localhost/private-address resolution, blocks redirects, caps response size at 1 MB, allows text/HTML, and verifies an exact normalized quote match.
- Direct `POST /evidence` can no longer mark evidence VERIFIED. Use `POST /evidence/verify`, which fetches source content before recording the quote/hash and audit event.
- Added `nexus/mcp_server.py` with bounded MCP tools and a fail-closed bearer-token middleware; added OpenAPI contract and MCP authentication tests.
- **Important limitation:** exact quote existence does not prove that the quote semantically supports the full claim. A human/reviewer policy gate remains necessary for high-impact claims. The URL fetcher is prototype-grade; production SSRF/DNS rebinding and content parsing require independent security review.
- Latest confirmed passing CI before MCP auth test correction: run #43, commit `460ef9d500f54e3158e3b024f149d3e6ccfdbb98`, success: https://github.com/Prasong1993/Loop-Controller/actions/runs/38012369558. Run after MCP adapter auth test correction is pending.


## Consolidated implementation update — 2026-10-10
- Added OpenAI Responses API structured plan proposals and a separate read-only function-tool worker; neither model output nor strict schema is treated as authorization.
- Added double budget gate: per-request `budget_approved=true` plus server-side `NEXUS_OPENAI_BUDGET_APPROVED=true`. Default is blocked; no live provider request was made during this implementation.
- Added searchable operational records, trace correlation, redacted provider/tool errors and token-usage aggregation when available.
- Moved VERIFIED evidence creation to the core fetch-and-quote verification boundary and added DNS-pinned HTTPS transport code.
- Added architecture map and Anchor reference-only boundary documents; Anchor source workflow and schema were not copied.
- Added/expanded regression tests. **Do not mark tests PASS until the latest GitHub Actions run is complete and its jobs are inspected.**
- Still RELEASE BLOCKED: shared bearer token/tenant authorization, deployment/TLS/secrets, concurrency/idempotency, task-level evidence traceability, and account-specific ChatGPT MCP/mobile integration are unresolved.


## Verified regression result — 2026-10-10
GitHub Actions run #121: https://github.com/Prasong1993/Loop-Controller/actions/runs/38014779739
- Python 3.11: compile PASS; 58 tests PASS.
- Python 3.12: compile PASS; 58 tests PASS.
- Python 3.13: compile PASS; 58 tests PASS.
- Added coverage includes task-specific evidence isolation and migration, pinned HTTPS transport, REST lifecycle completion/audit, paid budget gates, read-only OpenAI tool scope, usage records and MCP bearer-gate tests.
- This does not prove live provider account access, remote deployment, production auth/tenant isolation, adversarial network resilience, or ChatGPT mobile integration.


## Capability registry update — 2026-10-10
- Added `nexus/capabilities.py` as the deterministic allowlist for OpenAI components and built-in tools, with explicit ENABLED / DISABLED / BLOCKED / OUT_OF_SCOPE states and model compatibility checks.
- Current enabled flow: Responses API + Structured Outputs + Function Calling + optional Web Search, behind the double budget gate.
- Code Interpreter, Computer Use, Shell, Apply Patch, File Search, embeddings and unrelated media APIs are not enabled merely to increase the tool count. Each requires a concrete requirement and verified compatibility/security contract.
- See `docs/OPENAI_CAPABILITY_MATRIX.md`. Capability registry code has been updated; latest CI run must be checked before marking the new registry increment verified.


## Code proposal path and latest verified regression — 2026-10-10
- Added `POST /ai/code-proposal` to produce structured file-content proposals with `gpt-6-astra` by default (or reviewed `gpt-6.1-sol`), an explicit file-path allowlist, task/project checks and the double budget gate.
- The endpoint does not write files, apply patches, run tests or execute code. It logs file hashes and metadata rather than raw code.
- GitHub Actions run #150 passed compile + 67 tests on Python 3.11, 3.12 and 3.13: https://github.com/Prasong1993/Loop-Controller/actions/runs/38015297401.
- Remaining release blockers: no live provider call/API entitlement check, no code-write/execution adapter, no secure deployment or production identity/tenant isolation, and no registered ChatGPT mobile integration.


## Latest code verification read-back
GitHub Actions run #159: https://github.com/Prasong1993/Loop-Controller/actions/runs/38015447654 — compile and 67 tests passed on Python 3.11, 3.12 and 3.13. This run includes the REST operational-record scope fix. The remaining blockers are external integration/deployment and unimplemented code writing/execution, not a failing CI suite.


## Latest CI including OpenAPI and record redaction
Run #174: https://github.com/Prasong1993/Loop-Controller/actions/runs/38015687274 — on Python 3.11, 3.12 and 3.13, the dedicated OpenAPI contract checks passed (4 checks) and the full unit/regression suite passed (73 tests). Record persistence now rejects common credential and raw-content keys recursively. Production identity, tenant isolation, retention/encryption, code execution, remote deployment and ChatGPT mobile integration remain unresolved.


## Final repository snapshot result
GitHub Actions run #179 passed for commit `83340b5b74fafa54df72554d2b8c3b0b44a0c8dd`: Python 3.11/3.12/3.13 each passed compile, 4 OpenAPI contract checks and 73 tests. Link: https://github.com/Prasong1993/Loop-Controller/actions/runs/38015769056. No live OpenAI provider call, secure deployment, production auth/tenant isolation, code execution or ChatGPT mobile round trip was performed.
