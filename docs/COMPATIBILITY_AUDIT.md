# NEXUS — Whole-System Compatibility Audit

- Audit date: 2026-10-10
- Branch reviewed: `main`
- Review method: read-back of current default-branch source, tests, dependency manifest, CI workflow, OpenAPI contract, and integration/verification documents via GitHub connector.
- Review type: **STATIC CROSS-MODULE REVIEW**. No claim is made that this connector session executed the repository's test suite locally.
- Release decision: **NOT READY** until critical findings are addressed and the full CI + integration acceptance matrix is rerun.

## Executive summary

The repository contains a coherent prototype shape (SQLite core, FastAPI API, source-fetch verifier, MCP adapter, unit tests, OpenAPI contract, CI), but the green CI history proves only that the current workflow's compile and unit-test commands passed for the recorded commit. It does not establish production security, cross-process behavior, OpenAPI conformance, safe source verification, or successful registration/use in the ChatGPT mobile app.

The audit found several concrete cross-module gaps. Fixes should be grouped by shared trust boundaries rather than applied as isolated patches.

## Compatibility matrix

| Area | Interfaces/dependencies reviewed | Static result | Required next action |
|---|---|---|---|
| Core state machine ↔ task DB | `nexus/core.py`, core tests | PARTIAL — transition guards exist; no full lifecycle E2E test is present in the reviewed test inventory | Add one end-to-end lifecycle and negative-transition suite |
| Core evidence ↔ API/MCP verifier | `add_verified_evidence`, `verify_source_quote`, API and MCP endpoints | **FAIL — trust boundary is weaker in core than in the adapters**; see NX-A01 | Make evidence verification provenance non-forgeable within the supported call path, or move VERIFIED creation behind one trusted service boundary |
| URL verifier ↔ network | `nexus/evidence.py` | **RISK — DNS is checked before a separate HTTP client resolution; rebinding/TOCTOU is not prevented**; see NX-A02 | Use a transport that connects to the validated IP while preserving TLS hostname verification, or isolate fetching behind a reviewed egress proxy |
| FastAPI auth ↔ MCP auth | `nexus/api.py`, `nexus/mcp_server.py` | PARTIAL — both use a shared bearer token, but status codes and error bodies differ; prototype token is not production identity | Define one auth contract and test it against both adapters; production identity/tenant scoping remains blocked |
| FastAPI ↔ MCP public contract | `api.py`, `mcp_server.py`, OpenAPI | PARTIAL — different version strings; OpenAPI describes REST only and does not describe MCP tool schemas | Align version source and document/test the REST and MCP surfaces separately |
| API error mapping ↔ core exceptions | `invoke()`, endpoint handlers | PARTIAL — most core calls are mapped; policy routing bypasses `invoke`, and source fetch errors have endpoint-specific mapping | Define a consistent error envelope/status mapping and test all endpoint families |
| DB model ↔ restore semantics | `checkpoints`, `restore_checkpoint`, restore tests | PARTIAL — execution-state checkpoint is not auto-restored; no idempotency key or recovery rehearsal is evidenced | Add stale-checkpoint, repeated-restore, and concurrent-transition tests |
| CI ↔ test coverage | `.github/workflows/ci.yml`, tests | PASS for compile + unittest on the recorded CI runs; **coverage incomplete** | Add contract, lifecycle, failure/recovery, and security regression tests |
| ChatGPT integration ↔ account/platform | integration docs and official evidence register | **BLOCKED / NOT TESTED** — no deployed endpoint or configured ChatGPT app in evidence reviewed | Do not claim live integration; deployment and account-specific acceptance are separate gates |
| Production operations | secrets, tenant isolation, rate limiting, migrations, backups, TLS | **NOT IMPLEMENTED / NOT VERIFIED** | Keep production release blocked |

## Findings register

### NX-A01 — VERIFIED evidence can be created by a caller that supplies fabricated source text
- Severity: **HIGH (trust-boundary design defect)**
- Status: CONFIRMED by static inspection.
- Evidence: `NEXUS.add_verified_evidence(..., source_text, ...)` accepts source text as an ordinary argument, checks only that a normalized quote appears in that argument, and checks that the URL begins with `https://`. The method itself does not fetch the URL or receive a cryptographically/structurally bound fetch result. The API/MCP adapters fetch first, but the core method remains callable directly and trusts caller-provided text.
- Impact: any internal caller or future adapter can mark an unsupported claim VERIFIED by passing fabricated text and an arbitrary HTTPS URL. This violates the stated “VERIFIED requires source verification” invariant at the core boundary.
- Fix direction: centralize fetch + verification + record in a single trusted service method; do not expose a general core method that accepts untrusted `source_text` as proof. If separation is necessary, use a narrowly scoped verified-fetch result type that cannot be constructed from ordinary request fields, plus tests for every public adapter.
- Required regression tests: direct attempt to forge VERIFIED evidence must fail; API and MCP valid-quote flows pass; quote mismatch and invalid URL remain blocked.

### NX-A02 — DNS validation and HTTP connection are not bound to the same resolved address
- Severity: **HIGH (SSRF defense gap)**
- Status: CONFIRMED as a design limitation; exploitability depends on runtime/network conditions.
- Evidence: `_validate_public_https_url()` calls `socket.getaddrinfo()` to check public addresses, then `urllib.request` opens the hostname separately. The later connection may resolve the hostname again.
- Impact: DNS answers can change between validation and connection; this is a TOCTOU/DNS-rebinding risk. Blocking redirects and rejecting non-public results from the first lookup do not by themselves close this gap.
- Fix direction: use a transport that connects to the already-validated IP while preserving correct TLS SNI/hostname verification, or use a dedicated egress proxy with enforceable destination policy. Add controlled DNS/redirect/IP tests and an independent security review before public exposure.

### NX-A03 — Adapter version identifiers disagree
- Severity: LOW (operational/contract inconsistency)
- Status: CONFIRMED.
- Evidence: FastAPI advertises version `0.2.0` in app metadata and `/health`; MCP `nexus_health` advertises `0.3.0`.
- Impact: monitoring and clients cannot infer one unambiguous controller release version.
- Fix direction: define a single package/build version and import it in both adapters; assert REST and MCP report the same version.

### NX-A04 — Current tests do not establish whole-system lifecycle or contract compatibility
- Severity: HIGH (release confidence gap)
- Status: CONFIRMED from reviewed test inventory/workflow.
- Evidence: CI runs `compileall` and `unittest discover` across Python 3.11–3.13. Reviewed tests cover selected core/API/evidence/MCP cases, but no test was found that drives a task through the complete lifecycle across adapters, checks OpenAPI operations against FastAPI routes, or exercises concurrency/idempotency/recovery after ambiguous execution.
- Impact: green CI can coexist with integration and policy gaps.
- Fix direction: add a cross-module contract test suite, lifecycle E2E, transition matrix coverage, concurrency/retry tests, and OpenAPI drift check. Record exact run URL/commit after changes.

### NX-A05 — Error semantics differ across REST and MCP boundaries
- Severity: MEDIUM.
- Status: CONFIRMED by static inspection.
- Evidence: REST `invoke()` maps `PolicyDenied` to 403 and selected `ValueError` messages to 404/409; `/policy/route` bypasses `invoke()`; MCP tool functions directly propagate core exceptions; source-fetch failures are converted to 422 in REST but can surface through MCP's tool error mechanism.
- Impact: callers must interpret different response shapes for similar policy/validation failures; retry classification is not centrally specified.
- Fix direction: define canonical error codes (e.g. POLICY_DENIED, INVALID_TRANSITION, NOT_FOUND, SOURCE_FETCH_FAILED, INTERNAL_ERROR) and test the mapping at both adapters. Never retry policy denials or ambiguous side effects blindly.

### NX-A06 — Evidence is project-scoped, not task-scoped
- Severity: MEDIUM (requirements decision needed)
- Status: CONFIRMED.
- Evidence: evidence rows reference `project_id`, and the PLAN gate counts any VERIFIED evidence for that project.
- Impact: a task may satisfy its evidence gate using a verified item that was recorded for a different task or unrelated claim in the same project.
- Fix direction: decide whether project-wide evidence is intentional. If task-specific evidence is required, add an optional/required task reference and require a claim-to-requirement mapping before PLAN.

### NX-A07 — API schemas permit weakly constrained fields and may return inconsistent validation errors
- Severity: MEDIUM.
- Status: CONFIRMED by static inspection.
- Evidence: fields such as actor/reason/notes and candidate dictionaries have few length/type constraints; whitespace-only names pass Pydantic's min_length but fail in core and are mapped as a conflict rather than a request-validation error.
- Impact: inconsistent client errors and unbounded user-controlled text can reach logs/storage.
- Fix direction: apply consistent max lengths, non-whitespace validators, typed route candidate schemas, and size limits; test boundary values and ensure secret-bearing text is not copied into audit records.

### NX-A08 — Checkpoint restore is guarded but not proven idempotent or safe under concurrent state changes
- Severity: MEDIUM.
- Status: CONFIRMED as a test/assurance gap; race behavior not runtime-tested in this review.
- Evidence: restore reads current state and checkpoint then updates task without a compare-and-swap condition or idempotency token; tests cover selected state guards but not simultaneous transition/restore or repeated restore.
- Impact: concurrent requests may race and overwrite newer workflow metadata.
- Fix direction: use a transactionally enforced expected-state/version guard (e.g. revision counter), make restore idempotency semantics explicit, and test concurrent transition/restore.

### NX-A09 — Bearer-token gate is prototype authentication, not production identity/authorization
- Severity: HIGH if publicly deployed.
- Status: CONFIRMED limitation; no production deployment reviewed.
- Evidence: a single shared `NEXUS_API_KEY` gates all users and projects; no user identity, role, tenant boundary, key rotation policy, rate limiting, or per-project authorization is visible in the reviewed code.
- Impact: any holder of the shared token can act across all projects in that database; compromise has broad blast radius.
- Fix direction: do not expose publicly as production. Require reviewed identity/OAuth, project/tenant authorization, TLS, secret management/rotation, rate limiting, and redacted logs.

### NX-A10 — ChatGPT app integration is not an implemented/tested runtime path yet
- Severity: RELEASE BLOCKER for the target product.
- Status: BLOCKED / NOT TESTED.
- Evidence: repository documents describe an MCP adapter and integration contract, but there is no verified deployed public endpoint, app registration, or successful account-specific tool invocation in the evidence reviewed. Official product access is plan/workspace/interface-dependent.
- Impact: repository code cannot currently be described as usable from the user's ChatGPT mobile app.
- Fix direction: first confirm a supported integration path for the user's account, then deploy securely, configure the app, and execute the acceptance tests in `docs/VERIFICATION_PLAN.md`. If the account cannot register custom MCP apps, report that blocker rather than implying the app is connected.

## Required coordinated repair order

1. **Trust boundary:** NX-A01 and NX-A02 (evidence provenance and SSRF controls).
2. **Contract consistency:** NX-A03 and NX-A05 (version and error semantics across REST/MCP).
3. **Workflow correctness:** NX-A04, NX-A06 and NX-A08 (lifecycle, evidence scope, concurrency/recovery).
4. **Input/security hardening:** NX-A07 and NX-A09.
5. **Real integration gate:** NX-A10 (deployment, account-specific app registration, live acceptance tests).

Each repair group must include callers, schemas, tests, OpenAPI/docs, and compatibility checks in the same review—not isolated source edits.

## Current verification status

- Static source read-back: **DONE for the files listed in the compatibility matrix**.
- Confirmed latest previously observed CI run: run #60, commit `b20b94453e41f38ffe7234365be15e5156085785`, conclusion `success`: https://github.com/Prasong1993/Loop-Controller/actions/runs/38012621871
- That CI run proves the configured compile/unit-test workflow passed at that commit; it does **not** prove the findings above are resolved.
- Local test execution in this audit session: **NOT RUN**.
- Security penetration testing: **NOT RUN**.
- Public deployment/TLS/production identity: **NOT VERIFIED**.
- ChatGPT app registration and live mobile acceptance: **NOT RUN / BLOCKED**.
- Overall release status: **NOT READY**.


## Follow-up implementation pass — 2026-10-10
This update records source changes made after the initial static audit. It does **not** itself certify the release.

| Finding | Current code disposition | Verification status |
|---|---|---|
| NX-A01 — forged VERIFIED evidence via caller-supplied source text | Core legacy method now denies caller-supplied source text; `verify_and_add_evidence` fetches and matches a quote inside the trusted core boundary; project existence is checked before outbound fetch. | FIX IMPLEMENTED; unit/CI status must be checked on the latest commit. |
| NX-A02 — DNS validation/connection TOCTOU | HTTPS fetch uses a pinned validated public IP and TLS hostname verification; redirects remain blocked; body and timeout bounds remain. | FIX IMPLEMENTED; current unit tests cover handler type and private DNS denial; no live adversarial network test. |
| NX-A03 — version mismatch | REST and MCP health read `nexus/version.py` (0.4.0). | STATIC READ-BACK REQUIRED; CI check pending. |
| NX-A04 — no end-to-end lifecycle/API contract verification | Added REST lifecycle through verified COMPLETE and audit readback, task-scope/migration, budget-gate, OpenAI tool-scope, source-transport and usage-accounting tests. | PARTIAL — CI run #150 passed 67 tests on Python 3.11/3.12/3.13; no remote E2E, live provider call or ChatGPT mobile invocation. |
| NX-A05 — inconsistent error mapping | `EvidenceFetchError` maps to HTTP 422 before generic `ValueError`; common error mapping remains incomplete for all REST/MCP paths. | PARTIAL. |
| NX-A06 — evidence not tied to task/claim requirements | Added optional task_id to evidence; task-specific VERIFIED evidence satisfies only the linked task's PLAN gate; project-wide evidence remains explicit via null task_id. Cross-project task links are denied and old SQLite schemas migrate. | PARTIAL — requirement/claim ID linkage and freshness gate remain OPEN. |
| NX-A07 — validation/record query hardening | Some request length limits and pagination checks exist; whitespace-only validation, filter/date validation, request body limits and audit payload policy need further review. | OPEN. |
| NX-A08 — checkpoint concurrency/idempotency | Existing unsafe execute-state restore guard remains; compare-and-swap/revision and concurrent restore proof are still missing. | OPEN. |
| NX-A09 — shared bearer token / tenant isolation | Prototype auth remains shared-key based. | RELEASE BLOCKER. |
| NX-A10 — deployed ChatGPT/mobile integration | No public endpoint or account registration/live invocation verified. Official Help page checked 2026-10-10 states full MCP write support is rolling out to Business/Enterprise/Edu; current user plan/account access is not established. | BLOCKED / NOT TESTED. |

OpenAI wiring now separates structured proposal generation from a read-only tool orchestration endpoint. Both require a request-level approval and a server-side budget flag. The default model was updated to `gpt-6-luna` based on the official model catalog inspected 2026-10-10; actual account access and current billing remain unverified. Code Interpreter is intentionally not enabled.


## Task-scoped evidence correction — 2026-10-10
- Evidence storage now supports task scope through `evidence.task_id`; existing databases are migrated without dropping rows.
- `PLAN` gate counts VERIFIED evidence for the current task plus explicitly project-wide VERIFIED evidence only; a different task's evidence cannot satisfy the gate.
- REST and MCP evidence tools accept optional `task_id`; OpenAPI reflects this.
- Regression coverage includes cross-task denial, cross-project link denial, and legacy schema migration. Final disposition depends on latest CI result.


## Verified regression run
GitHub Actions run #121 (commit `a3b898e0437490887046e7629465995f5c959e84`) completed successfully: compile + 58 unit/regression tests on each of Python 3.11, 3.12 and 3.13. Details: https://github.com/Prasong1993/Loop-Controller/actions/runs/38014779739. This is workspace CI evidence, not production or ChatGPT integration evidence.


## Code proposal integration — 2026-10-10
- Added `nexus/code_proposal.py` and `POST /ai/code-proposal`, backed by the Responses API and strict structured outputs, with a code-model allowlist drawn from `nexus/capabilities.py`.
- Every request requires an explicit `allowed_paths` list, task/project scope validation, and both request/server budget approval. Proposed paths are checked again after generation. Only hashes and metadata are recorded; code contents are returned to the caller but not persisted in operational logs.
- No file write or code execution occurs. Shell, Apply Patch, Code Interpreter and Computer Use remain disabled. CI run #150 passed 67 tests across Python 3.11–3.13: https://github.com/Prasong1993/Loop-Controller/actions/runs/38015297401.


## Latest verification read-back
Run #159 passed compile and 67 tests on Python 3.11, 3.12 and 3.13 at commit `6e5dcfcd46d2781a315bfefdfa6dbcfd34b53bea`: https://github.com/Prasong1993/Loop-Controller/actions/runs/38015447654. It includes task/project-scoped operational record assertions and the code-proposal API. No live provider, public deployment or ChatGPT mobile test was performed.
