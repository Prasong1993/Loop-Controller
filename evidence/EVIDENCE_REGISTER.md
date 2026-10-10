# NEXUS — Evidence Register

สถานะ: Starter register; URL ด้านล่างเป็นแหล่งตั้งต้นที่ต้องเปิดตรวจและผูกกับ claim ก่อนนำไปยืนยันข้อเท็จจริง

## สถานะหลักฐาน
- VERIFIED — แหล่งทางการ/การทดสอบจริงรองรับ claim ที่ระบุ
- RECOVERED — ข้อมูลที่กู้คืนจากบริบทเดิม ยังต้องตรวจซ้ำ
- UNKNOWN — ยังไม่ได้ตรวจหรือไม่มีหลักฐานเพียงพอ
- BLOCKED — ตรวจไม่ได้เพราะข้อจำกัดการเข้าถึงหรือข้อมูล

## Source register
| ID | แหล่งข้อมูล | URL | ประเภท | Claim ที่ต้องตรวจ | สถานะ |
|---|---|---|---|---|---|
| NXS-001 | NASA — System Design Processes | https://www.nasa.gov/reference/4-0-system-design-processes/ | Official reference | แนวทาง design process และ design products ที่เกี่ยวข้อง | UNKNOWN — ต้องตรวจเนื้อหา/วันที่เข้าถึง |
| NXS-002 | NASA — Systems Engineering Handbook Appendix | https://www.nasa.gov/reference/system-engineering-handbook-appendix/ | Official reference | คำศัพท์/แนวทาง systems engineering ที่เกี่ยวข้อง | UNKNOWN — ต้องตรวจเนื้อหา/วันที่เข้าถึง |
| NXS-003 | NASA Systems Engineering Handbook PDF | https://www.nasa.gov/wp-content/uploads/2018/09/nasa_systems_engineering_handbook_0.pdf | Official handbook | แนวทาง lifecycle, verification/validation, traceability | UNKNOWN — ต้องตรวจฉบับและหน้าอ้างอิง |
| NXS-004 | OpenAI — Function calling | https://developers.openai.com/api/docs/guides/function-calling | Official developer docs | รูปแบบการเชื่อมต่อ tools/function calling และข้อจำกัด | UNKNOWN — ต้องตรวจเนื้อหาปัจจุบัน |
| NXS-005 | OpenAI — Tools | https://developers.openai.com/api/docs/guides/tools | Official developer docs | tool capabilities และ integration pattern | UNKNOWN — ต้องตรวจเนื้อหาปัจจุบัน |
| NXS-006 | OpenAI Help — Connected apps in ChatGPT | https://help.openai.com/en/articles/11487775-connected-apps-in-chatgpt | Official Help Center | วิธีเชื่อมต่อแอป สิทธิ์ และข้อจำกัดใน ChatGPT | UNKNOWN — ต้องตรวจเนื้อหาปัจจุบัน |
| NXS-007 | OpenAI Help — ChatGPT Android FAQ | https://help.openai.com/en/articles/8142208-chatgpt-android-app-faq | Official Help Center | ข้อเท็จจริงเกี่ยวกับ Android app; ไม่ควรอนุมานเกินเนื้อหา | UNKNOWN — ต้องตรวจเนื้อหาปัจจุบัน |

## วิธีบันทึกเมื่อทำ research
สำหรับแต่ละ source ให้เพิ่ม:
- วันที่/เวลาที่เข้าถึง (UTC หรือระบุ timezone)
- ชื่อหน้าและ publisher
- version/revision/last updated ถ้ามี
- ข้อความหรือส่วนที่รองรับ claim พร้อม section/page
- claim ที่รองรับและ claim ที่ไม่รองรับ
- limitation และ confidence
- requirement/component/test ที่เชื่อมโยง
- ผู้ตรวจหรือวิธีตรวจ

**ข้อควรระวัง:** การมี URL ในรายการนี้ไม่ได้ทำให้ claim เป็น VERIFIED โดยอัตโนมัติ อย่าใช้ UNKNOWN เป็นหลักฐานยืนยัน
