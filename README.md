# NEXUS — AI Workflow Control Layer

**สถานะ:** Initial design / evidence review pending  
**เอกสารหลัก:** [NEXUS System Design Reference Document (SDRD)](docs/NEXUS_SDRD_v1.0_TH.md)

NEXUS เป็นชั้นควบคุม workflow สำหรับงานที่ AI ช่วยวิเคราะห์ วางแผน และใช้เครื่องมือ โดยตรวจ policy ก่อน execute ตรวจผลก่อนส่งมอบ และเก็บหลักฐานที่ตรวจสอบย้อนหลังได้

> **หลักการ:** AI เสนอแผนและทำงานภายในขอบเขตที่อนุญาต; policy และ verification ใช้กฎที่ชัดเจน ตรวจซ้ำได้

## สถานะหลักฐาน
- `VERIFIED`: มีแหล่งที่ตรวจสอบได้หรือผลทดสอบบันทึกไว้
- `RECOVERED`: กู้คืนจากบริบท/ข้อมูลเดิม แต่ยังต้องตรวจแหล่งที่มาและความเป็นปัจจุบัน
- `UNKNOWN`: หลักฐานยังไม่พอ ห้ามใช้อ้างเป็นข้อเท็จจริงยืนยัน
- `BLOCKED`: ดำเนินต่อไม่ได้จนกว่าจะคลี่คลายข้อจำกัด

## เอกสารโครงการ
- [System Design Reference Document](docs/NEXUS_SDRD_v1.0_TH.md)
- [Requirements](docs/REQUIREMENTS.md)
- [Verification and Test Plan](docs/VERIFICATION_PLAN.md)
- [Risks and Open Issues](docs/RISKS_AND_OPEN_ISSUES.md)
- [Evidence Register](evidence/EVIDENCE_REGISTER.md)
- [Changelog](CHANGELOG.md)

## ข้อจำกัดสำคัญ
เอกสารนี้ยังไม่ใช่หลักฐานว่ามี controller/runtime ที่ใช้งานจริงแล้ว ความสามารถในการควบคุม ChatGPT Android, connectors, background execution และการสลับผู้ให้บริการต้องตรวจจากเอกสารทางการและทดสอบจริงก่อนยืนยัน

## การเปลี่ยนแปลง
บันทึกเหตุผล แหล่งหลักฐาน ผลกระทบ และการทดสอบสำหรับการเปลี่ยนแปลงที่สำคัญ ห้ามนำข้อมูลจากโครงการอื่นมาเป็นข้อเท็จจริงของ NEXUS โดยอัตโนมัติ

## NEXUS controller implementation status
Cross-platform scope includes Android, iOS, iPadOS, web and server-side orchestration. The initial deterministic Python/SQLite controller and optional FastAPI API are under `nexus/`; tests are under `tests/`; CI is configured in `.github/workflows/ci.yml`.

- [System Design Reference Document](docs/NEXUS_SDRD_v1.0_TH.md)
- [Platform compatibility matrix](docs/PLATFORM_COMPATIBILITY.md)
- [Implementation guide](docs/IMPLEMENTATION.md)
- [Requirements](docs/REQUIREMENTS.md)
- [Verification plan](docs/VERIFICATION_PLAN.md)
- [Error report](docs/ERROR_REPORT.md)
- [Evidence register](evidence/EVIDENCE_REGISTER.md)

**Not production-ready:** CI/device test outcomes, authentication, production deployment, native mobile clients, evidence ingestion validation, and checkpoint restore are still open. Never expose the initial API publicly without security hardening.
