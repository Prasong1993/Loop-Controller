# Changelog

การเปลี่ยนแปลงที่มีนัยสำคัญของ NEXUS

## [1.0] — 2026-10-10
- สร้าง SDRD ฉบับตั้งต้นภาษาไทย
- เพิ่มข้อกำหนดระดับระบบ 30 ข้อ
- เพิ่มแผน verification/test และความเสี่ยง/ประเด็นเปิด
- เพิ่มทะเบียนแหล่งอ้างอิงโดยตั้งสถานะเป็น UNKNOWN จนกว่าจะตรวจจริง
- ยืนยันว่า implementation และ runtime tests ยังไม่ได้สร้าง/รันจาก commit นี้
- ใช้ Loop-Controller เป็น repository เริ่มต้นที่ว่าง; ยังไม่ได้เปลี่ยนชื่อ repository เป็น NEXUS


## 2026-10-10 — Initial controller implementation
- Added deterministic SQLite workflow core, optional FastAPI API, unit-test source and Python CI workflow.
- Added cross-platform compatibility matrix for Android, iOS, iPadOS and server/web.
- Added implementation guide and initial error/limitation report.
- Expanded requirements to explicitly include cross-platform behavior.
- Inspected official Android, Apple, OpenAI and NASA documentation and updated evidence statuses for narrowly scoped claims.
- Test execution and production readiness remain unverified/open.


## 2026-10-10 — CI verification
- Observed GitHub Actions run #9 complete successfully on Python 3.11, 3.12 and 3.13; compile and unit test steps passed.
- Native-device, security and production deployment validation remain open.


## 2026-10-10 — ChatGPT-app-first scope correction
- Clarified that ChatGPT on Android, iOS and iPadOS is the intended interface through a supported integration; a separate native NEXUS mobile app is out of scope.
- Made physical-device testing conditional on native/OS-specific features instead of a universal release gate.
- Added explicit live integration acceptance tests; status remains NOT CONFIGURED / NOT RUN until a real integration round-trip is evidenced.
- Added a NASA-style recovery checkpoint and action register; this is a project adaptation, not NASA certification.


## 2026-10-10 — Controller hardening increment
- Added guarded checkpoint restore with policy restrictions against replaying EXECUTE-state checkpoints.
- Added remote fail-closed bearer-token gate and API error mapping tests.
- Added HTTPS source quote verification; direct API claims cannot be marked VERIFIED without fetching content and matching a quote.
- Added Streamable HTTP MCP adapter, OpenAPI contract, ChatGPT integration contract, and official account-plan availability evidence.
- CI run #53 passed for commit `4fa719ab1c678355cc0ff18894ec8c0519319c4d`; later commits require their own CI verification.
- Live ChatGPT integration remains blocked until eligible account/workspace, secure HTTPS deployment and account-side connector registration are available.


## 2026-10-10 — OpenAI capability and code proposal integration
- Added a deterministic capability registry with explicit enabled/disabled/blocked/out-of-scope decisions rather than adding tools solely to increase the API count.
- Added OpenAI Responses API structured plan proposals, project-scoped read-only function tools, and a code-proposal endpoint using the official code-generation model guidance. Code proposals are allowlisted and never written or executed by this service.
- Added a double paid-API budget gate, structured usage/error records, trace IDs, project/task correlation, and record search.
- Moved VERIFIED evidence creation behind trusted HTTPS fetch + quote match, pinned the connection to a validated public IP while preserving TLS hostname checks, and added task-scoped evidence with additive SQLite migration.
- Consulted Anchor files only as references; recorded a boundary that excludes wholesale copying of their workflow, schema, code or project artifacts.
- CI run #159 passed 67 tests on Python 3.11, 3.12 and 3.13. Live OpenAI provider access, code writing/execution, production deployment, production identity/tenant isolation and ChatGPT mobile integration remain NOT RUN/BLOCKED.


## 2026-10-10 — Record privacy and contract validation
- Strengthened the operational record storage boundary to reject common credential-bearing and raw prompt/argument/output/code/patch fields recursively; redacted token counts and code hashes remain allowed.
- Added an OpenAPI contract test for YAML parsing, shared service version, required REST routes, verified-evidence rules and code-proposal path scope; CI runs it separately and in the full suite.
- CI run #174 passed the 4 OpenAPI checks and 73 tests on Python 3.11, 3.12 and 3.13. Production security, live provider, deployment and ChatGPT mobile integration remain NOT RUN/BLOCKED.


## 2026-10-10 — Final repository snapshot verification
- GitHub Actions run #179 passed compile, 4 OpenAPI contract checks and 73 tests on Python 3.11, 3.12 and 3.13: https://github.com/Prasong1993/Loop-Controller/actions/runs/38015769056.
- Source changes and docs were read back from GitHub. Live provider/API entitlement, secure deployment, production identity/tenant isolation, code writing/execution and ChatGPT mobile integration remain NOT RUN/BLOCKED.


## 2026-10-11 — Project Control API hardening work branch
- Added `docs/PROJECT_CONTROL_API_TRACEABILITY.md` mapping requirements to source modules, tests, and verified evidence.
- Fixed mandatory operational-recording failure handling in the OpenAI worker: a failed request-start record stops before tool dispatch and no automatic retry occurs; added a regression test.
- Removed direct `RECOVER → EXECUTE` transition and added a regression test requiring recovery to pass through planning/policy.
- Ported the reviewed deterministic Free-first ToolRouter and append-only router run/event ledger into the isolated work branch, including persistent stage checkpoints and verification-gated fallback.
- Added a regression test proving checkpoint persistence failure stops before provider execution.
- CI run #249 passed on Python 3.11, 3.12 and 3.13 (4 OpenAPI contract tests and 94 unit tests per matrix job): https://github.com/Prasong1993/Loop-Controller/actions/runs/38076731270
- This is not a production-readiness claim: live provider adapters, durable idempotency for arbitrary side effects, production identity/tenant isolation, rate limiting, secured HTTPS deployment, and Plugin Creator round-trip remain open / NOT RUN.
- All changes remain on `work/project-control-api-hardening-2026-10-11`; no existing PR was merged or modified.
