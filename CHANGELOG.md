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
