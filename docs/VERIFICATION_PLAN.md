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
