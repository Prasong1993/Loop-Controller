# NEXUS — Risks and Open Issues

สถานะ: Initial register; ประเมินความเสี่ยงเชิงคุณภาพเบื้องต้น ยังไม่ใช่ผล threat-model workshop

| ID | ความเสี่ยง/คำถาม | สถานะ | ผลกระทบ | วิธีปิดประเด็น |
|---|---|---|---|---|
| NXRISK-001 | ChatGPT Android เปิดให้ controller ภายนอกสั่ง/ควบคุม workflow ได้แค่ไหน | UNKNOWN | สูง | ตรวจเอกสารทางการและทดสอบจากบัญชี/อุปกรณ์จริง |
| NXRISK-002 | Connector/API มีสิทธิ์อ่าน/เขียนอะไรบ้าง | UNKNOWN | สูง | ตรวจ permission scope ของแต่ละ integration |
| NXRISK-003 | สามารถทำงานต่อเมื่อแอปปิดหรือไม่ | UNKNOWN | สูง | ตรวจเอกสาร platform และทดสอบ |
| NXRISK-004 | Free/paid routing ทำได้จริงใน integration ที่เลือกหรือไม่ | UNKNOWN | สูง | ตรวจ capability, pricing, limits และ approval path |
| NXRISK-005 | Retry หลัง timeout อาจทำ action ซ้ำ | OPEN | สูง | idempotency keys, execution ledger, recovery tests |
| NXRISK-006 | Prompt injection จากแหล่งภายนอก | OPEN | สูง | threat model, trust boundaries, allowlists และ tests |
| NXRISK-007 | ข้อมูลโครงการรั่วข้าม project | OPEN | สูง | project-scoped authorization และ isolation tests |
| NXRISK-008 | Logs เก็บ secrets/PII มากเกินไป | OPEN | สูง | redaction, data minimization และ retention policy |
| NXRISK-009 | การเปลี่ยน policy ทำให้ workflow เดิมพัง | OPEN | กลาง-สูง | versioning, regression tests และ rollback |
| NXRISK-010 | ชื่อ repository ยังไม่ตรงกับ NEXUS | OPEN | ต่ำ | เปลี่ยนชื่อ repo เมื่อมี tool/API ที่รองรับ หรือใช้ repository ใหม่ |
| NXRISK-011 | เอกสารอ้างอิงอาจเปลี่ยนหรือ link ไม่ตรง | OPEN | กลาง | ตรวจ URL, revision, access date และ claim-to-source mapping |
| NXRISK-012 | ไม่มี implementation จึงยังยืนยันพฤติกรรมจริงไม่ได้ | VERIFIED (สถานะเอกสาร) | สูง | สร้าง prototype หลัง P0/P1 ผ่าน |

## Open decisions
1. Runtime เป้าหมาย: ChatGPT connector, hosted service, local/mobile component หรือ hybrid
2. Database และ storage model
3. Authentication/authorization model
4. Audit retention และ data deletion
5. Policy language/schema และ versioning
6. Budget caps และ approval roles
7. การตั้ง repository name เป็น NEXUS และ visibility ที่ต้องการ
8. Release strategy และ rollback owner

## กฎการปิดความเสี่ยง
ห้ามเปลี่ยน UNKNOWN เป็น VERIFIED ด้วยการคาดเดาหรือเพียงมี URL อยู่ในเอกสาร ต้องบันทึกแหล่งข้อมูลที่อ่านจริงหรือ test result ที่ทำซ้ำได้
