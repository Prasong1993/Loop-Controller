# NEXUS Project Checkpoint — NASA-style Gate / Decision / Action Record

| Field | Value |
|---|---|
| Checkpoint ID | NEXUS-CP-2026-10-10-01 |
| Project | NEXUS |
| Repository | https://github.com/Prasong1993/Loop-Controller |
| Recorded | 2026-10-10 |
| Record type | Project status / recovery checkpoint |
| Framework | NASA-style lifecycle, review gates, decision and action tracking; this is an adaptation, not a NASA approval or certification |
| Overall status | **IN PROGRESS — ChatGPT integration not configured** |
| Last confirmed CI | GitHub Actions run #12, commit `6e89df9bb2f10dd088acecfdc99e46932a60649e`, success: https://github.com/Prasong1993/Loop-Controller/actions/runs/38011572637 |

## 1. Purpose and resume rule

This checkpoint records the actual stopping point, unresolved gaps, approved scope, evidence status and exact next actions so work can resume without reconstructing the entire conversation. It applies to NEXUS only. Do not import IRIS files or treat old-project information as NEXUS evidence.

On resume, read this checkpoint first, then inspect the current repository and latest CI status before changing files. Do not assume any action listed as OPEN or NOT RUN has been completed. Re-check the default branch and current file contents before writing.

## 2. Scope decision (approved direction)

**Decision NEXUS-DEC-001 — ChatGPT-app-first**

- Intended user interface: ChatGPT application on Android, iOS and iPadOS, using a connected app/tool/API integration actually supported by the user's account and interface.
- Separate native NEXUS Android/iOS/iPadOS applications: **OUT OF SCOPE** unless explicitly added as a future requirement.
- Physical-device testing on every mobile OS/device: **NOT A universal release gate**. Require it only for native code or OS-dependent features such as local device access, push notifications or background execution.
- Required acceptance: prove the real integration works through the target ChatGPT account/interface. CI success alone is not integration evidence.
- No claim that NEXUS is callable from ChatGPT until the connector/API is deployed, configured, authorized and passes end-to-end acceptance.

## 3. Confirmed baseline

| Item | Status | Evidence / limitation |
|---|---|---|
| Python/SQLite workflow controller source | VERIFIED (source read-back) | `nexus/core.py` |
| FastAPI wrapper source | VERIFIED (source read-back) | `nexus/api.py`; local/source code, not deployed |
| Unit tests and CI workflow | VERIFIED (repository source) | `tests/test_core.py`, `.github/workflows/ci.yml` |
| CI matrix Python 3.11, 3.12, 3.13 | PASS | Run #12 above |
| Deterministic state/policy prototype | IMPLEMENTED — prototype scope | Not a production security boundary yet |
| ChatGPT app connector/API integration | NOT CONFIGURED / NOT RUN | No live round-trip evidence |
| Production deployment, auth/TLS, secrets, tenant isolation | OPEN / NOT RUN | Do not expose API publicly |
| Evidence URL/content verification | OPEN | URL presence does not prove the source content supports a claim |
| Checkpoint creation | IMPLEMENTED | Creation exists; restore/resume semantics are not implemented |
| External tool/provider adapters | OPEN | Current route selector selects candidates; it does not execute providers |
| Native mobile clients | OUT OF SCOPE | Not a missing deliverable under the current scope |
| Physical device matrix tests | NOT REQUIRED FOR CURRENT SCOPE | Reassess only if OS-specific features enter scope |
| Repository rename from Loop-Controller to NEXUS | OPEN / OPTIONAL ADMIN ACTION | Repository rename is not a prerequisite for functional acceptance |

## 4. NASA-style review gates

The following is a practical adaptation of lifecycle reviews, not a claim of NASA endorsement.

| Gate | Review intent | Exit criteria | Current status |
|---|---|---|---|
| SRR — System Requirements Review | Confirm intended use and scope | ChatGPT-app-first scope and acceptance requirements recorded | **BASELINE RECORDED; formal review pending** |
| SFR — System Functional Review | Confirm functional flow | Intake, research/evidence, policy, execute, verify, audit and delivery behavior mapped to tests | **PARTIAL** |
| PDR — Preliminary Design Review | Confirm architecture and interfaces | Controller/runtime boundary, connector contract, identity, permissions and error contract documented | **PARTIAL; integration contract still needed** |
| CDR — Critical Design Review | Confirm implementation is ready to integrate | Adapter and secure runtime implemented; restore/recovery design reviewed | **NOT READY** |
| TRR — Test Readiness Review | Confirm test setup and procedures | Unit/CI tests pass; real integration test environment, test account and safe fixtures ready | **CI PASS; integration TRR BLOCKED until configured** |
| ORR — Operational Readiness Review | Confirm safe operational deployment | Authentication, authorization, TLS, secrets, logging, backup/restore, monitoring and rollback verified | **NOT READY** |
| AR — Acceptance Review | Confirm user outcome | Real ChatGPT round-trip, denial, audit readback and error/retry tests pass | **NOT RUN** |

No gate should be treated as passed solely because documentation exists. Record review decision, evidence links, unresolved actions and approver/date when each gate is reviewed.

## 5. Open actions — prioritized

| Action ID | Priority | Action | Completion evidence | Status |
|---|---|---|---|---|
| NEXUS-A001 | P0 | Revise platform, requirements, verification, implementation, SDRD, README and error report to adopt ChatGPT-app-first scope | Git commit plus read-back of all changed files | **OPEN — prior bulk update was blocked; no successful write was confirmed** |
| NEXUS-A002 | P0 | Identify the supported ChatGPT integration path for the user's account/interface and document its official requirements | Official documentation, availability constraints and integration decision | **OPEN** |
| NEXUS-A003 | P0 | Define an integration contract: tool names, schemas, auth model, permission boundaries, timeout/error format and audit correlation IDs | Versioned interface document and schema tests | **OPEN** |
| NEXUS-A004 | P0 | Deploy controller only to a secured test runtime after auth/TLS/secrets controls are in place | Deployment evidence and security checklist | **BLOCKED by security/deployment gaps** |
| NEXUS-A005 | P0 | Configure the supported connector/tool integration to point to the secured runtime | Integration configuration evidence without exposing secrets | **NOT CONFIGURED** |
| NEXUS-A006 | P0 | Run real ChatGPT-app acceptance tests: discover tool, create/read task, policy denial, audit readback, warning/timeout without blind retry | Timestamped results, request/task IDs, redacted audit evidence | **NOT RUN** |
| NEXUS-A007 | P1 | Implement real evidence ingestion/verification (fetch source, identify supporting passage/version/date, record limits) | Positive/negative tests proving unsupported claims cannot be VERIFIED | **OPEN** |
| NEXUS-A008 | P1 | Implement checkpoint restore/resume and crash/partial-execution recovery | Restore tests and duplicate-action protection evidence | **OPEN** |
| NEXUS-A009 | P1 | Implement actual provider/tool adapters; keep routing separate from execution | Adapter contracts, mock and integration tests, idempotency behavior | **OPEN** |
| NEXUS-A010 | P1 | Add production identity, authorization, project/tenant isolation, rate limits and redacted structured logs | Security tests/review | **OPEN** |
| NEXUS-A011 | P1 | Add backup/restore, retention/deletion, migration and rollback procedures | Rehearsal records | **OPEN** |
| NEXUS-A012 | P2 | Decide whether repository rename is worthwhile and supported | Rename only if administratively available; verify links afterward | **OPTIONAL / OPEN** |

## 6. ChatGPT integration acceptance checklist

All checks below remain **NOT RUN** until a real supported integration is configured.

- [ ] I-01: The integration/tool is visible and callable in the target ChatGPT account/interface.
- [ ] I-02: Least-privilege authentication and authorization are enforced.
- [ ] I-03: Create a harmless test task through ChatGPT; receive task ID.
- [ ] I-04: Read the same task status back through ChatGPT and compare with controller state.
- [ ] I-05: Request a disallowed action; controller rejects it before execution and records reason.
- [ ] I-06: Read the related audit events; verify actor/action/outcome/time without secret leakage.
- [ ] I-07: Simulate a warning, timeout or ambiguous response; no blind retry or duplicate side effect occurs.
- [ ] I-08: Verify unavailable connector, missing permission and runtime-down errors produce a clear BLOCKED result.
- [ ] I-09: Confirm the flow works in the user's intended ChatGPT mobile interface, if that interface exposes the configured integration. This is an app-level acceptance check, not a requirement to build a native NEXUS app.
- [ ] I-10: Record test environment, date, result, evidence references and unresolved defects.

## 7. Known risks and controls

1. **ChatGPT capability/account variability:** connector availability differs by account, plan, region, workspace and interface. Control: verify on the actual target account; keep UNKNOWN until then.
2. **Local API is not remotely available:** source code is not a deployment. Control: secure deployment and integration configuration are explicit gates.
3. **Prototype security gaps:** do not expose the current API publicly until authentication, authorization, TLS, secrets and isolation are reviewed.
4. **Evidence trust gap:** storing a URL alone is insufficient. Control: verify source content and link claims to exact evidence.
5. **Recovery gap:** checkpoint creation does not imply restore works. Control: test restore, partial execution and duplicate prevention.
6. **Tool routing is not execution:** a selected candidate does not prove an external tool ran. Control: adapters must return structured results and trace IDs.
7. **No native app requirement:** do not spend effort on separate mobile clients or device-matrix testing unless scope changes.

## 8. Resume procedure

1. Read this checkpoint and inspect the repository's latest default-branch state.
2. Check the latest GitHub Actions run and current commit; do not reuse stale SHAs.
3. Complete **NEXUS-A001** in small, sequential file updates (one file per write) to avoid unsafe bulk mutation; read each file back after writing.
4. Continue P0 actions in order: integration path → interface contract → secure runtime → connector configuration → real acceptance tests.
5. Keep each action's status explicit: VERIFIED / RECOVERED / UNKNOWN / BLOCKED / NOT RUN / PASS / FAIL as appropriate. Do not use PASS for unexecuted tests.
6. At handoff, report completed actions, still-open actions, evidence links, CI result and blockers. Do not report a plan as completed implementation.

## 9. Change log

| Date | Change |
|---|---|
| 2026-10-10 | Created recovery checkpoint to capture current NEXUS implementation state, approved ChatGPT-app-first scope, NASA-style review gates, unresolved gaps and prioritized resume actions. |


## 10. Checkpoint update — 2026-10-10

### A001 progress
The ChatGPT-app-first scope has now been recorded in the following repository files:
- `docs/REQUIREMENTS.md`
- `docs/VERIFICATION_PLAN.md`
- `docs/IMPLEMENTATION.md`
- `README.md`
- `docs/NEXUS_SDRD_v1.0_TH.md`

The platform compatibility matrix already states that native clients/device matrix testing are not required for the current scope. The error report still needs a matching explicit scope correction at the time of this checkpoint update.

**A001 status: PARTIALLY COMPLETE — read back all updated files and update the error report/changelog before marking complete.** This action must not be closed until those files and this checkpoint are read back successfully.


## 11. Documentation scope correction closeout — 2026-10-10

Read-back verification completed for the following files after successful GitHub writes:
- `docs/REQUIREMENTS.md` — ChatGPT-app-first requirements and conditional device tests recorded.
- `docs/VERIFICATION_PLAN.md` — integration acceptance cases NXT-017 through NXT-022 recorded as NOT RUN.
- `docs/IMPLEMENTATION.md` — deployment/integration boundary and production gaps recorded.
- `README.md` — intended interface and NOT CONFIGURED status recorded.
- `docs/NEXUS_SDRD_v1.0_TH.md` — scope and acceptance gate recorded.
- `docs/ERROR_REPORT.md` — native clients/device tests correctly scoped out; real integration remains a blocker.
- `docs/PLATFORM_COMPATIBILITY.md` — ChatGPT-app-first target and conditional device test policy already recorded.
- `CHANGELOG.md` — scope correction recorded.

**NEXUS-A001: COMPLETE (documentation change only).** This does not mean live ChatGPT integration is complete. NEXUS-A002 through A006 remain open/not configured as described above. The latest CI run recorded in this checkpoint remains run #12; confirm newer runs before relying on it for a release decision.


## 12. Execution checkpoint update — 2026-10-10

### Confirmed implementation since the previous checkpoint
- **Safe checkpoint restore implemented** in `nexus/core.py` and exposed by the REST API. Restore is allowed only from BLOCKED/RECOVER; checkpoints captured at EXECUTE are denied to prevent accidental replay. Audit event `CHECKPOINT_RESTORED` is recorded.
- **Remote API bearer gate implemented**: non-health endpoints require `NEXUS_API_KEY` when configured; remote requests fail closed if it is missing. Unknown IDs return 404, policy denials 403, invalid transitions 409. This is prototype authentication, not production OAuth/identity.
- **Source quote verification implemented** in `nexus/evidence.py` and `POST /evidence/verify`; direct VERIFIED status through `POST /evidence` is denied. HTTPS-only fetch, no redirects, public-address check, 8-second timeout and 1 MB cap. Exact quote match proves quote presence only, not semantic support; high-impact claims need review.
- **MCP adapter implemented** in `nexus/mcp_server.py` using the Python MCP SDK, with bounded project/task/checkpoint/evidence/audit/route tools and fail-closed bearer middleware.
- **OpenAPI and integration contract added**: `openapi.yaml`, `docs/CHATGPT_INTEGRATION_CONTRACT.md`.
- Added unit/API/evidence/MCP tests.

### Latest confirmed CI
- Run #53: **SUCCESS**, commit `4fa719ab1c678355cc0ff18894ec8c0519319c4d`: https://github.com/Prasong1993/Loop-Controller/actions/runs/38012564851
- This run verifies the source at that commit. Later documentation commits may have newer runs; check latest status before release.

### Open actions — revised status
| Action | Revised status | Reason / next closure condition |
|---|---|---|
| NEXUS-A001 scope/documentation correction | COMPLETE | Files were written and read back |
| NEXUS-A002 choose supported ChatGPT integration | **PARTIALLY VERIFIED / ACCOUNT BLOCKED** | Official OpenAI docs inspected: full MCP/write actions are rolling out in beta to Business/Enterprise/Edu and developer-mode setup is web/workspace controlled. Current reported user plan is Free; a supported workspace/account or a different available path is needed. Mobile-interface availability remains UNKNOWN until actual test. |
| NEXUS-A003 integration contract | COMPLETE — draft contract | `openapi.yaml` and `docs/CHATGPT_INTEGRATION_CONTRACT.md` exist; auth mechanism needs final decision during deployment |
| NEXUS-A004 secure deployment | BLOCKED | No selected/authorized runtime deployment; production identity, tenant isolation, SSRF review and secrets controls remain |
| NEXUS-A005 register/configure ChatGPT app | BLOCKED | Requires supported plan/workspace, deployed HTTPS endpoint, and account-side setup |
| NEXUS-A006 ChatGPT end-to-end acceptance | BLOCKED / NOT RUN | Cannot test a connector that is not configured |
| NEXUS-A007 evidence verification | PARTIAL IMPLEMENTATION | Exact source quote is checked; semantic claim support and hardened SSRF/DNS rebinding review remain |
| NEXUS-A008 checkpoint restore | IMPLEMENTED; CI PASS at run #53 | Restore gate and audit test passed; production crash/side-effect/idempotency stress tests remain |
| NEXUS-A009 external provider execution adapters | OPEN | Router is still a selector; no external provider is executed |
| NEXUS-A010 security/identity/tenant isolation | PARTIAL | Bearer gate implemented; production OAuth/identity, tenant/project authorization, rate limits and redacted logs remain |
| NEXUS-A011 backup/migration/rollback | OPEN | No tested backup/restore, schema migration or operational rollback rehearsal |
| NEXUS-A012 repository rename | OPTIONAL | Does not block product implementation |

### Important platform finding
OpenAI's official documentation checked on 2026-10-10 says full MCP support including write/modify actions is rolling out in beta to Business, Enterprise and Edu, and developer-mode setup is managed through web/workspace settings. It does not establish that the current Free account can register a custom MCP app or that the app is available in the mobile interface. Do not claim otherwise.

### Resume instruction
The code-side increments above are implemented and CI-tested at the commit listed. Do not loop back to the completed documentation task. Continue with hardening and adapter tests; live ChatGPT registration remains blocked by account/workspace and deployment prerequisites, not by a missing checklist.
