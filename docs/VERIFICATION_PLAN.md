# NEXUS — Verification and Test Plan

สถานะ: PARTIAL VERIFIED — CI unit/regression suite and in-process REST lifecycle E2E passed on Python 3.11–3.13; live OpenAI, remote deployment, security penetration and ChatGPT mobile acceptance remain NOT RUN/BLOCKED.

## 1. หลักการรายงานผล
แยกผลเป็น:
- **STATIC_REVIEW:** ตรวจเอกสาร/schema/source โดยไม่รันระบบ
- **UNIT:** ทดสอบ component เดี่ยว
- **INTEGRATION:** ทดสอบ adapter และ boundary
- **END_TO_END:** ทดสอบตั้งแต่ intake ถึง delivery
- **SECURITY/PRIVACY:** ตรวจ permission, secrets, isolation และ input trust
- **ACCEPTANCE:** ผู้ใช้ตรวจผลเทียบเป้าหมาย

ห้ามสรุปว่า test ผ่านหากไม่มี test command, environment, result และหลักฐานที่เพียงพอ

## 2. Test matrix เริ่มต้น
| Test ID | สถานการณ์ | Expected result | ระดับ |
|---|---|---|---|
| NXT-001 | คำขอครบถ้วน | สร้าง task และเข้าสู่ RESEARCH | Unit |
| NXT-002 | ขาดข้อมูลจำเป็น | ระบุ UNKNOWN หรือขอข้อมูลที่จำเป็น ไม่แต่งข้อมูล | Unit |
| NXT-003 | ใช้ UNKNOWN เป็นหลักฐานยืนยัน | Policy ปฏิเสธ | Unit |
| NXT-004 | Transition ผิดลำดับ | ปฏิเสธและเขียน audit event | Unit |
| NXT-005 | Tool ไม่มี permission | ไม่เรียก executor; สถานะ BLOCKED | Integration |
| NXT-006 | Free primary unavailable | ทดลอง free fallback ที่อนุญาตเท่านั้น | Router |
| NXT-007 | มีแต่ paid option แต่ไม่มี approval | ไม่เรียก paid option; รอ approval หรือ BLOCKED | Policy |
| NXT-008 | Rate limit/warning | หยุด blind retry และจัดประเภท error | Failure |
| NXT-009 | Executor ทำงานสำเร็จแต่ response ขาด | ตรวจสถานะก่อน retry เพื่อป้องกัน duplicate | Recovery |
| NXT-010 | Verification ไม่ผ่าน | ห้าม COMPLETE; ส่งกลับแก้ไข/RECOVER | End-to-end |
| NXT-011 | Task ถูกยกเลิก | หยุด action ที่ยังไม่เริ่มและบันทึก partial state | Integration |
| NXT-012 | อ่านข้อมูลอีก project | ปฏิเสธหรือไม่คืนข้อมูลที่ไม่ได้รับอนุญาต | Security |
| NXT-013 | Log มี secret fixture | Security scan ต้องตรวจพบ; ห้าม release | Security |
| NXT-014 | Config เปลี่ยน | version เพิ่มและ rollback target ระบุชัด | Config |
| NXT-015 | ทุก acceptance checks ผ่าน | Audit ครบแล้วจึง COMPLETE | End-to-end |
| NXT-016 | ChatGPT Android capability claim | มี official evidence หรือผลทดสอบจริงก่อน mark VERIFIED | Evidence review |

## 3. Exit criteria สำหรับ prototype
- ทุก required state transition มี positive/negative tests
- policy rules มี unit tests
- failure/recovery cases ครอบคลุม timeout, rate limit, permission denial และ partial execution
- ทุก requirement ระดับสูงเชื่อมกับ test case
- ไม่มี critical/high security issue ที่ยังไม่คลี่คลาย
- ไม่มี secrets ใน repository/logs
- เอกสารระบุชัดเจนว่าฟีเจอร์ใด tested, not tested, blocked หรือ unknown
- มี rollback procedure ที่ทดสอบได้

## 4. ผลทดสอบ
ผลที่มีหลักฐานล่าสุดอยู่ในหัวข้อ “Latest verified CI execution” ด้านล่าง แถว test ที่ไม่มีการรันจริงยังคง NOT RUN; ห้ามใช้ผล CI แทนการทดสอบ remote deployment, real provider calls หรือ ChatGPT mobile integration.


## Execution evidence — 2026-10-10
GitHub Actions run #9: https://github.com/Prasong1993/Loop-Controller/actions/runs/38011520599
- Python 3.11: compile and unit test steps PASS.
- Python 3.12: compile and unit test steps PASS.
- Python 3.13: compile and unit test steps PASS.
- Workflow conclusion: success.
- Device-specific Android/iOS/iPadOS tests: NOT RUN.
- Security and deployment tests: NOT RUN.


## 5. ChatGPT application integration acceptance (required; currently NOT RUN)

The target is use through the ChatGPT application on Android, iOS and iPadOS. Native NEXUS apps are out of scope. Physical device tests are not a universal gate; require them only for native/OS-specific features.

| Test ID | Scenario | Expected result | Status |
|---|---|---|---|
| NXT-017 | Integration is available in the target ChatGPT account/interface | Configured tool/action is visible and authorized | NOT RUN — not configured |
| NXT-018 | Create then read a harmless test task through ChatGPT | Task ID/status match controller state | NOT RUN — not configured |
| NXT-019 | Attempt an unauthorized action | Denied before execution and audit reason recorded | NOT RUN — not configured |
| NXT-020 | Read audit for the test task | Events show action/outcome/time without leaking secrets | NOT RUN — not configured |
| NXT-021 | Warning, timeout or ambiguous response | No blind retry; check state before recovery | NOT RUN — not configured |
| NXT-022 | Use integration from the intended ChatGPT mobile interface | Works within the account's actual supported capabilities | NOT RUN — requires configured integration |

Do not confuse opening the ChatGPT app with proof that NEXUS is connected. CI success is not live integration evidence. Record test date, environment, task/trace IDs, results and redacted evidence when executed.


## 6. New code-level acceptance cases

| Test ID | Scenario | Expected result | Evidence |
|---|---|---|---|
| NXT-023 | Restore checkpoint while task is BLOCKED | Restore only an allowed state; add CHECKPOINT_RESTORED audit event | `tests/test_core.py` |
| NXT-024 | Restore attempted outside BLOCKED/RECOVER | Policy denial | `tests/test_core.py` |
| NXT-025 | Restore checkpoint captured in EXECUTE | Policy denial; never automatically replay side-effecting execution | `tests/test_core.py` |
| NXT-026 | Remote API request with no server token configured | Fail closed with HTTP 503 | `tests/test_api.py` |
| NXT-027 | Configured API token missing/valid | Missing token gets 401; valid token is accepted | `tests/test_api.py` |
| NXT-028 | Unknown task identifier | HTTP 404 | `tests/test_api.py` |

These are test definitions in source. Mark PASS only after the latest GitHub Actions run reports success.


| NXT-029 | Remote MCP request without configured token | Fail closed with 503 | `tests/test_mcp_server.py` |
| NXT-030 | MCP request with missing/invalid token | Deny before dispatch | `tests/test_mcp_server.py` |
| NXT-031 | Source quote absent from fetched text | Do not record VERIFIED | `tests/test_evidence.py` |
| NXT-032 | HTTP/local URL supplied as source | Reject before fetch | `tests/test_evidence.py` |
| NXT-033 | Direct evidence API attempts status VERIFIED | Deny; require verification endpoint | `tests/test_api.py` |


## Latest verified CI execution — 2026-10-10
**GitHub Actions run #121:** https://github.com/Prasong1993/Loop-Controller/actions/runs/38014779739  
Commit: `a3b898e0437490887046e7629465995f5c959e84`  
Workflow: compile + `python -m unittest discover -s tests -v`.

| Runtime | Compile | Unit/regression suite | Result |
|---|---|---|---|
| Python 3.11 | PASS | 58 tests, 0 failures | PASS |
| Python 3.12 | PASS | 58 tests, 0 failures | PASS |
| Python 3.13 | PASS | 58 tests, 0 failures | PASS |

Coverage in this run includes deterministic workflow gates, task-scoped evidence and legacy schema migration, HTTPS pinning/private-DNS rejection, REST lifecycle from project/task creation through verified COMPLETE and audit readback, budget gating, OpenAI tool policy behavior with fake clients, operational record search/redaction, and MCP bearer-gate behavior.

**Not proven by this run:** real OpenAI API call/account entitlement, live public HTTPS fetching against adversarial DNS, production database concurrency, OAuth/tenant isolation, deployed remote endpoint, ChatGPT app registration, or use from the user's Android ChatGPT account. These remain NOT RUN/BLOCKED.

## Added test-case mapping
| Test ID | Added coverage | Source | Latest disposition |
|---|---|---|---|
| NXT-034 | Task-A evidence cannot unlock Task-B; cross-project task link denied | `tests/test_core.py` | PASS in CI #121 |
| NXT-035 | Legacy evidence schema migrates additively to task_id | `tests/test_core.py` | PASS in CI #121 |
| NXT-036 | HTTPS connection pins validated IP while preserving TLS hostname; private DNS denied | `tests/test_evidence.py` | PASS in CI #121 |
| NXT-037 | Request + server-side paid budget gates prevent provider calls | `tests/test_api.py`, `tests/test_openai_planner.py` | PASS in CI #121 |
| NXT-038 | Structured plan remains PROPOSAL_ONLY; unsupported capability rejected; no-tools request omits tools field | `tests/test_openai_planner.py` | PASS in CI #121 |
| NXT-039 | OpenAI read tool cross-project request is blocked before handler | `tests/test_api.py`, `tests/test_openai_adapter.py` | PASS in CI #121 |
| NXT-040 | REST lifecycle completes only after evidence, audit and result; audit readback works | `tests/test_api.py` | PASS in CI #121 |
