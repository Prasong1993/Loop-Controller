# NEXUS — System Requirements (Initial Draft)

สถานะเอกสาร: Draft; ต้องตรวจ evidence และอนุมัติก่อนใช้เป็น baseline

| ID | Requirement | Acceptance criteria (initial) | Verification |
|---|---|---|---|
| NXR-001 | รับคำขอและสร้าง task identity | ทุกคำขอที่รับงานมี project_id/task_id และเป้าหมายที่บันทึกได้ | Unit/integration |
| NXR-002 | แยกข้อมูลตามโครงการ | query ข้าม project ไม่คืนข้อมูลที่ไม่ได้รับอนุญาต | Security test |
| NXR-003 | บันทึก evidence status | ระเบียนมี VERIFIED/RECOVERED/UNKNOWN/BLOCKED และ source reference | Schema/unit |
| NXR-004 | UNKNOWN ห้ามเป็นหลักฐานยืนยัน | policy ปฏิเสธการใช้ UNKNOWN เป็น verified prerequisite | Policy unit test |
| NXR-005 | แผนมี acceptance criteria | ก่อน EXECUTE มี expected outcome และ verification method | State/policy test |
| NXR-006 | ตรวจ policy ก่อน execute | action ที่ถูก deny ไม่เรียก executor | Integration test |
| NXR-007 | Tool routing ตาม capability | router เลือกเฉพาะ tool ที่ capability และ permission ตรง | Router unit test |
| NXR-008 | Free-first fallback | ลำดับเลือกเป็น free primary → free fallback → paid only if approved → blocked | Routing test |
| NXR-009 | ควบคุมค่าใช้จ่าย | paid action ถูก deny หรือรอ approval เมื่อ budget/policy ไม่ผ่าน | Policy test |
| NXR-010 | ไม่ retry แบบไม่ตรวจ | error/warning หยุด retry จนกว่าจะผ่าน retry-safety check | Failure test |
| NXR-011 | ป้องกัน duplicate action | completed non-idempotent action ไม่ถูก execute ซ้ำโดยไม่มี explicit re-run approval | Integration test |
| NXR-012 | State transition ถูกต้อง | transition ที่ไม่อนุญาตถูกปฏิเสธและ audit | State-machine test |
| NXR-013 | Verification ก่อน complete | task ไม่ COMPLETE หาก required checks ยังไม่ผ่าน | End-to-end test |
| NXR-014 | Audit trail | policy decisions และ transitions สำคัญมี actor, reason, timestamp, outcome | Audit test |
| NXR-015 | Checkpoint/recovery | recovery กลับไป checkpoint ที่ผ่าน verification ได้ | Recovery test |
| NXR-016 | Configuration versioning | config เปลี่ยนแล้วมี version และ rollback reference | Config test |
| NXR-017 | Secrets protection | repository และ logs ไม่มี secrets ที่รู้จักจาก test fixtures | Security scan/review |
| NXR-018 | Approval gates | consequential action ต้องมี approval ตาม policy | Policy/integration |
| NXR-019 | Platform feasibility | ข้ออ้างเกี่ยวกับ ChatGPT/Android/connectors มี official evidence หรือ test result | Evidence review |
| NXR-020 | Test traceability | ทุก requirement สำคัญเชื่อมกับ test case และผลล่าสุด | Traceability review |
| NXR-021 | Error taxonomy | error ถูกจัดประเภทและมี recovery action ที่กำหนด | Unit/failure test |
| NXR-022 | Data minimization | audit ไม่เก็บ secrets และลดข้อมูลส่วนบุคคลเท่าที่ทำได้ | Privacy review |
| NXR-023 | External input safety | เนื้อหาภายนอกไม่สามารถข้าม policy โดยตรง | Threat-model tests |
| NXR-024 | Clear delivery status | รายงานแยก completed, blocked, unknown และ not-tested | Acceptance review |
| NXR-025 | Rollback path | release/config มีวิธีกลับไปเวอร์ชันก่อนหน้าและทดสอบได้ | Release test |
| NXR-026 | No unsupported capability claims | ไม่มี feature ที่อ้างว่าทำงานจริงโดยไม่มีหลักฐาน | Documentation review |
| NXR-027 | Project-local memory | บันทึกเฉพาะข้อมูลสำคัญล่าสุด พร้อม source and decision links | Data review |
| NXR-028 | Rate/usage limits | router ตรวจ usage limits ก่อนเรียกและจัดการ rate-limit errors | Integration/failure test |
| NXR-029 | Safe cancellation | ยกเลิกงานแล้วหยุด action ที่ยังไม่เริ่ม และบันทึกสถานะ partial work | Cancellation test |
| NXR-030 | Final audit | ก่อน COMPLETE มีผลตรวจและหลักฐานส่งมอบที่อ้างอิงได้ | End-to-end test |

## ข้อกำหนดที่ยังต้องกำหนด
- SLO/latency targets และปริมาณงานที่รองรับ
- Retention periods และนโยบายลบข้อมูล
- รายละเอียด threat model และระดับความเสี่ยง
- Schema/versioning contract ของ adapters
- Budget ceilings และผู้อนุมัติ
- การจัดการ identity/authorization ใน runtime จริง
- Acceptance thresholds สำหรับแต่ละชนิดงาน


## Cross-platform requirement update
| ID | Requirement | Acceptance criteria | Verification |
|---|---|---|---|
| NXR-031 | Cross-platform coverage | Requirements and capability matrix explicitly cover Android, iOS, iPadOS, web/server; platform-specific claims require source evidence | Documentation/evidence review |
| NXR-032 | Server-authoritative state | Critical task state is not dependent solely on a mobile process or local device storage | Architecture review and recovery test |
| NXR-033 | Mobile background constraints | No promise of indefinite/unattended execution; OS-specific behavior is documented and tested on target versions | Platform review and device tests |
| NXR-034 | Client secret safety | Server API keys are not embedded in Android/iOS/iPadOS clients | Static scan and security review |
