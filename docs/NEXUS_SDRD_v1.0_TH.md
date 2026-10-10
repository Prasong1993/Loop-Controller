# NEXUS — System Design Reference Document (SDRD)

| รายการ | ค่า |
|---|---|
| Document ID | NEXUS-SDRD-001 |
| Version | 1.0 |
| ภาษา | ไทย |
| สถานะ | Initial baseline — ต้องผ่าน evidence review |
| วันที่จัดทำ | 2026-10-10 |
| Repository | Loop-Controller (พื้นที่เริ่มต้น; ยังไม่ได้เปลี่ยนชื่อ) |

## 1. บทสรุปผู้บริหาร
NEXUS คือชั้นควบคุม workflow สำหรับงานที่ AI ช่วยวิเคราะห์ วางแผน ใช้เครื่องมือ และส่งมอบผลลัพธ์ โดยมุ่งควบคุมขอบเขต ตรวจข้อกำหนดก่อนลงมือ ยืนยันผลหลังทำ บันทึกหลักฐาน และกู้คืนจากข้อผิดพลาดอย่างมีระเบียบ

NEXUS ไม่ตั้งสมมติฐานว่า ChatGPT Android เปิดให้ควบคุมเครื่องมือทุกชนิดหรือสลับผู้ให้บริการอัตโนมัติได้ ต้องยืนยันความสามารถจริงจากเอกสารและการทดสอบก่อน

## 2. วัตถุประสงค์
1. แปลงคำขอเป็นงานย่อยและเกณฑ์ตรวจรับที่ชัดเจน
2. รวบรวมหลักฐานก่อนออกแบบหรือพัฒนา
3. บังคับใช้ policy ที่กำหนดแน่นอนและตรวจซ้ำได้
4. เลือกเครื่องมือจาก capability, permission, availability, cost และ risk
5. ตรวจผลลัพธ์ก่อนส่งมอบ
6. เก็บ checkpoint, audit trail, version และหลักฐานสำหรับ recovery
7. แยกข้อมูลและความทรงจำของแต่ละโครงการ

## 3. ขอบเขต
### อยู่ในขอบเขต
- Workflow/state controller
- Evidence register และ project-local memory
- Policy gates และ capability-based routing
- Checkpoints, recovery และ audit events
- Verification plan, test results และ traceability
- Adapters สำหรับ integration ที่มีจริงและได้รับอนุญาต

### ยังไม่ยืนยันว่าอยู่ในขอบเขต
- การควบคุม UI หรือเครื่องมือทั้งหมดใน ChatGPT Android
- การทำงานต่อเนื่องเบื้องหลังเมื่อแอปปิด
- การสลับไปใช้บริการเสียเงินโดยอัตโนมัติ
- การที่ connector ทุกตัวจะมีสิทธิ์เขียนในทุกบัญชี
- การ deploy/run code โดยไม่มี runtime ที่เชื่อมต่อและได้รับอนุญาต

## 4. หลักการออกแบบ
1. **Evidence first:** ตรวจสอบแหล่งข้อมูลก่อนยืนยันข้อเท็จจริงหรือเริ่มพัฒนา
2. **Explicit status:** ใช้ VERIFIED / RECOVERED / UNKNOWN / BLOCKED
3. **Deterministic gates:** policy และ verification เป็นกฎที่ชัดเจน แยกจากการสร้างข้อความของ LLM
4. **Least privilege:** ใช้สิทธิ์เท่าที่จำเป็น
5. **No blind retry:** ห้ามลองซ้ำหลัง warning/error โดยไม่ตรวจสาเหตุและเงื่อนไข retry
6. **Cost-aware routing:** ใช้ทางเลือกฟรีที่อนุญาตก่อน; ทางเลือกเสียเงินต้องผ่าน policy/budget gate
7. **Project isolation:** ทุก task, evidence, config และ artifact ต้องผูกกับ project ID
8. **Auditability:** บันทึกเหตุผลและหลักฐานของการตัดสินใจสำคัญ
9. **Recoverability:** checkpoint ต้องบอกได้ว่าสำเร็จถึงไหนและควรกลับไปขั้นใด
10. **Human approval:** การเผยแพร่ ลบข้อมูล เปลี่ยนสิทธิ์ หรือก่อค่าใช้จ่ายต้องได้รับอนุมัติตาม policy

## 5. สถาปัตยกรรมระดับระบบ
### 5.1 ส่วนประกอบเชิงตรรกะ
- **Intake:** รับคำขอ สร้าง project/task ID และระบุเป้าหมาย/ข้อจำกัด
- **Research & Evidence:** รวบรวมเอกสารทางการ เวอร์ชัน ข้อจำกัด ตัวอย่าง และผลทดสอบ
- **Planner:** เสนอแผน งานย่อย dependency และ acceptance criteria
- **Policy Engine:** ตรวจสิทธิ์ ขอบเขต ความเสี่ยง ต้นทุน และ approval
- **Tool Router:** เลือก adapter จาก capability registry
- **Executor/Adapter:** เรียก integration ที่มีอยู่จริง
- **Verifier:** ตรวจผลลัพธ์กับเกณฑ์ที่กำหนด
- **Audit & Evidence Store:** บันทึก source, decision, checkpoint และผลตรวจ
- **Recovery Manager:** จัดประเภทข้อผิดพลาดและเลือกจุดกลับไปทำต่อ
- **Delivery:** ส่งมอบผลพร้อมสถานะและหลักฐาน

### 5.2 เส้นทางข้อมูล
คำขอ → task model → evidence → plan → policy decision → tool execution → verification → audit record → delivery

ทุก event สำคัญควรมี project_id, task_id, stage, timestamp, status, input/output reference และ reason code หลีกเลี่ยงการบันทึก secrets หรือข้อมูลส่วนบุคคลเกินจำเป็น

## 6. วงจรชีวิตและ state machine
เส้นทางหลัก:
`INTAKE → RESEARCH → PLAN → POLICY → EXECUTE → VERIFY → AUDIT → COMPLETE`

สถานะเสริม:
- `WAITING_APPROVAL`: รอการอนุมัติ
- `RECOVER`: วิเคราะห์ข้อผิดพลาดและเลือกขั้นกลับไป
- `BLOCKED`: ขาดสิทธิ์ หลักฐาน หรือ capability
- `CANCELLED`: ยกเลิกตามคำสั่งหรือ policy

### เงื่อนไขเปลี่ยนสถานะ
- INTAKE → RESEARCH: เป้าหมาย ขอบเขต และข้อจำกัดถูกบันทึก
- RESEARCH → PLAN: หลักฐานพอสำหรับวางแผน; ช่องว่างถูกทำเครื่องหมาย UNKNOWN
- PLAN → POLICY: มีงานย่อย dependency และ acceptance criteria
- POLICY → EXECUTE: policy อนุญาต และ approval/budget ผ่าน
- EXECUTE → VERIFY: มีผลการดำเนินงานให้ตรวจ
- VERIFY → AUDIT: ผ่านเกณฑ์ หรือมี failure record ที่ครบถ้วน
- AUDIT → COMPLETE: หลักฐานและผลส่งมอบถูกบันทึกครบ
- ข้อผิดพลาด → RECOVER: ระบุสาเหตุ ผลกระทบ และ retry safety ก่อนเลือกจุดกลับ

การเปลี่ยนสถานะที่ไม่ตรงกฎต้องถูกปฏิเสธและบันทึก audit event

## 7. Tool routing และ fallback
ลำดับนโยบาย:
1. `FREE_PRIMARY` — เครื่องมือฟรีที่มี capability และ permission ตรงงาน
2. `FREE_FALLBACK` — เครื่องมือฟรีสำรองที่ผ่านการตรวจ
3. `APPROVED_PAID_ALTERNATIVE` — ใช้ได้เมื่อ policy อนุมัติและ budget เหลือเพียงพอ
4. `BLOCKED` — ไม่มีทางเลือกที่ปลอดภัยหรือได้รับอนุญาต

ก่อนเรียกเครื่องมือให้ตรวจ capability, permission, availability, rate/usage limits, cost, data sensitivity และ retry policy ห้ามอนุมานว่าการเชื่อมต่อที่มองเห็นได้แปลว่ามีสิทธิ์เขียนหรือเผยแพร่

## 8. Policy gates
Policy Engine ควรตรวจอย่างน้อย:
- project/task อยู่ในสถานะที่อนุญาต
- action อยู่ใน scope ที่อนุมัติ
- tool capability และ permission ถูกต้อง
- prerequisite/evidence ที่จำเป็นครบ
- ไม่มี conflict ที่ยังไม่คลี่คลาย
- ไม่ทำซ้ำ action ที่สำเร็จแล้วโดยไม่มีเหตุผล re-run
- budget/usage limit ผ่าน
- approval มีอยู่เมื่อจำเป็น
- การกระทำไม่ละเมิด security/privacy requirements

ผลการตัดสินใจ: `ALLOW`, `DENY`, `REQUIRE_APPROVAL`, `BLOCKED` พร้อม reason code ที่ตรวจสอบได้

## 9. Evidence register และ project memory
บันทึกหลักฐานเป็นระเบียน ไม่เก็บ research dump ทั้งหมดโดยไม่มีการคัดกรอง ฟิลด์แนะนำ:
- evidence_id, project_id, claim
- source_title, source_url, publisher
- source_type, version/revision, retrieved_at
- status, confidence/limitations
- affected_requirement, affected_component
- validation_method, test_reference
- supersedes / superseded_by

สถานะ:
- VERIFIED: ตรวจจากแหล่งทางการหรือผลทดสอบที่ทำซ้ำได้
- RECOVERED: กู้คืนจากบริบทเดิม ยังต้องยืนยันความเป็นปัจจุบัน
- UNKNOWN: ไม่มีหลักฐานเพียงพอ ห้ามใช้ยืนยัน
- BLOCKED: การตรวจสอบถูกขัดขวาง

เก็บเฉพาะข้อมูลล่าสุดที่สำคัญ พร้อมความสัมพันธ์ไปยังข้อกำหนด การตัดสินใจ โค้ด และการทดสอบ

## 10. Configuration และ change control
- แยก config ตาม environment และ project
- กำหนด schema, version และ validation rule
- ห้ามเก็บ token/password/API key ใน repository
- การเปลี่ยน policy ต้องมีเหตุผล ผู้อนุมัติ วันที่ และ regression tests
- ต้องมี rollback path ไปยัง configuration version ที่รู้ว่าใช้งานได้
- เปลี่ยน requirement ต้องประเมินผลกระทบต่อ architecture, tests และ evidence

## 11. Verification และ validation
Verification ตอบว่า “สร้างถูกตามข้อกำหนดหรือไม่”; validation ตอบว่า “ตอบโจทย์การใช้งานจริงหรือไม่”

ระดับการตรวจ:
1. Schema/static validation
2. Unit tests สำหรับ state transitions และ policy rules
3. Integration tests สำหรับ adapters
4. End-to-end tests จาก intake ถึง delivery
5. Failure/recovery tests รวม timeout, rate limit, permission denial และ malformed outputs
6. Security/privacy checks
7. Acceptance review โดยผู้ใช้

ห้ามประกาศ COMPLETE หาก acceptance criteria ที่บังคับยังไม่ผ่าน หรือหลักฐานการทดสอบขาดหาย

## 12. Audit และ recovery
Audit event ควรเก็บ event_id, project_id, task_id, stage, action, actor/tool, decision, reason, timestamps, evidence references และ outcome โดยไม่บันทึก secrets

เมื่อผิดพลาด:
1. หยุดการเรียกซ้ำอัตโนมัติที่ยังไม่ผ่านการตรวจ retry safety
2. จัดประเภท error และระบุผลกระทบ
3. ตรวจว่า action ก่อนหน้าสำเร็จบางส่วนหรือไม่
4. ใช้ checkpoint ล่าสุดที่ผ่าน verification
5. ทำซ้ำเฉพาะงานที่ idempotent หรือมีการป้องกัน duplicate
6. บันทึกผล recovery และรัน verification ใหม่

## 13. Security และ privacy
- ใช้ least privilege และขอบเขตสิทธิ์แยกตาม project
- เก็บ secrets ใน secret manager/secure settings เท่านั้น
- ปกปิดข้อมูลอ่อนไหวใน logs
- กำหนด retention และการลบข้อมูล
- ตรวจสิทธิ์ก่อนอ่าน/เขียน/เผยแพร่
- ป้องกัน prompt injection ในข้อมูลภายนอกโดยถือว่าเป็น input ที่ไม่น่าเชื่อถือจนกว่าจะตรวจ
- ระบุผู้มีอำนาจอนุมัติการกระทำที่มีผลภายนอก
- บันทึก security incidents และการแก้ไข

## 14. ข้อกำหนดระดับระบบ
ดูรายการเต็มใน [REQUIREMENTS.md](REQUIREMENTS.md) ข้อกำหนดทุกข้อควรมี acceptance criteria และวิธีทดสอบก่อนเป็น baseline ที่อนุมัติแล้ว

## 15. แผนทดสอบ
ดู [VERIFICATION_PLAN.md](VERIFICATION_PLAN.md) การทดสอบจริงต้องแยกผล static inspection, unit, integration และ end-to-end อย่างชัดเจน ห้ามใช้การตรวจอ่านโค้ดแทนผล runtime test

## 16. ความเสี่ยงและประเด็นเปิด
ดู [RISKS_AND_OPEN_ISSUES.md](RISKS_AND_OPEN_ISSUES.md) โดยเฉพาะความสามารถที่มีอยู่จริงใน ChatGPT Android, permission model, background execution, tool availability และค่าใช้จ่าย

## 17. Roadmap และ phase gates
- **P0 — Evidence & feasibility:** ตรวจ official docs, available connectors, permissions, API limitations และ mobile constraints
- **P1 — Requirements baseline:** ยืนยัน scope, use cases, threat model และ acceptance criteria
- **P2 — Architecture & interface contracts:** กำหนด state model, schemas, tool registry และ error taxonomy
- **P3 — Minimal controller prototype:** สร้าง deterministic policy/state engine ใน runtime ที่เลือก
- **P4 — Adapter integration:** เชื่อมเฉพาะเครื่องมือที่พิสูจน์แล้วว่ารองรับ
- **P5 — Verification & recovery:** ทดสอบ normal/error/retry/rollback paths
- **P6 — Pilot & acceptance:** ทดสอบกับงานจริงในขอบเขตจำกัด พร้อมผู้ใช้อนุมัติ
- **P7 — Release review:** ตรวจ security, docs, rollback และ release evidence

แต่ละ phase ห้ามผ่าน gate จนกว่าจะมีหลักฐานและผลทดสอบที่จำเป็นครบ

## 18. Traceability
เชื่อมโยงอย่างน้อย:
`Requirement → Evidence → Design component → Policy rule → Test case → Result → Release`

การเปลี่ยนข้อกำหนดต้องบอกได้ว่าส่วนใดและการทดสอบใดได้รับผลกระทบ

## 19. แนวคิด data model
เอนทิตีที่คาดว่าจำเป็น:
- Project
- Task
- StageTransition
- Evidence
- Requirement
- PolicyDecision
- ToolCapability
- ExecutionAttempt
- Checkpoint
- VerificationResult
- AuditEvent
- ConfigurationVersion
- Approval
- BudgetRecord

เป็น conceptual model เท่านั้น; schema, database engine, migration strategy และ retention ยังต้องตัดสินหลัง evidence/requirements review

## 20. แหล่งข้อมูลตั้งต้น
รายการแหล่งอ้างอิงและสถานะการตรวจสอบอยู่ใน [EVIDENCE_REGISTER.md](../evidence/EVIDENCE_REGISTER.md) การใส่ URL ในทะเบียนไม่ได้หมายความว่าเนื้อหาทุกข้อได้รับการตรวจยืนยันแล้ว ต้องบันทึกวันที่เข้าถึง เวอร์ชัน และ claim ที่รองรับหลังตรวจจริง

## 21. เกณฑ์ความพร้อม
เอกสารนี้ยังเป็น **draft baseline** จนกว่า:
- ข้อกำหนดสำคัญทุกข้อมีวิธีตรวจ
- ความสามารถและข้อจำกัดของ platform ได้รับการยืนยัน
- architecture decisions มีหลักฐานและเหตุผล
- threat model และ permission model ผ่าน review
- test plan มี expected result และ exit criteria
- ผู้ใช้ยอมรับ scope และ release gate

## 22. ประวัติการแก้ไข
| Version | วันที่ | การเปลี่ยนแปลง |
|---|---|---|
| 1.0 | 2026-10-10 | สร้างเอกสารอ้างอิงตั้งต้น; ประเด็น platform feasibility ยังเปิดอยู่ |


## 19. ขอบเขตแพลตฟอร์มข้ามระบบ (revision 1.1)
NEXUS ต้องออกแบบให้รองรับ Android, iOS, iPadOS, เว็บ และ runtime ฝั่งเซิร์ฟเวอร์ ไม่ถือว่าแอป ChatGPT หรือระบบปฏิบัติการแต่ละตัวมีความสามารถเท่ากัน

- แกน state machine, policy, audit และ source-of-truth ควรอยู่ใน runtime ที่ควบคุมได้ ไม่ฝากสถานะสำคัญไว้บนมือถือเครื่องเดียว
- งานเบื้องหลังบนมือถือเป็น best-effort ตามข้อจำกัดของ OS; งานสำคัญ/ยาวนานให้พิจารณา server-side orchestration ที่มีสิทธิ์และการตรวจสอบ
- API keys ต้องไม่ฝังใน client app; ใช้ secret management ฝั่งเซิร์ฟเวอร์
- การเชื่อมต่อ ChatGPT apps/tools ขึ้นกับบัญชี แผน ภูมิภาค workspace รุ่นโมเดล และ interface ต้องตรวจเป็นรายกรณี
- การอ้างว่าใช้งานได้จริงต้องมี official source และผลทดสอบตามความเหมาะสม

ดูรายละเอียดใน [Platform Compatibility Matrix](PLATFORM_COMPATIBILITY.md), [Implementation Guide](IMPLEMENTATION.md) และ [Error Report](ERROR_REPORT.md).

## 20. สถานะ implementation
มี initial Python/SQLite controller, FastAPI wrapper, unit-test source และ GitHub Actions CI workflow เพิ่มใน repository แล้ว อย่างไรก็ตาม source commit/read-back ไม่เท่ากับ test pass; จนกว่าจะเห็นผล workflow ให้ถือ CI เป็น NOT RUN/UNKNOWN. ยังไม่มี native Android/iOS/iPadOS apps และยังไม่พร้อม production.
