# NEXUS — Verification and Test Plan

สถานะ: Initial plan; ยังไม่มีผลทดสอบ runtime ที่อ้างว่า PASS

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
ยังไม่มีผล runtime test ถูกบันทึกในเอกสารนี้ สถานะปัจจุบันคือ **NOT RUN** สำหรับ test cases ทั้งหมด จนกว่าจะมี implementation และหลักฐานผลทดสอบจริง


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
