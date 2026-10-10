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


## Research update — 2026-10-10
The following official pages were opened and inspected during this update. These findings support only the claims listed; they do not certify NEXUS itself.

| ID | Source | URL | Claim supported | Status | Limitation |
|---|---|---|---|---|---|
| NXS-008 | Android Developers — Foreground services overview | https://developer.android.com/develop/background-work/services/fgs | Foreground services have defined use/permission requirements; not a blanket invisible automation capability | VERIFIED | Specific behavior depends on OS/API target and service type |
| NXS-009 | Apple Developer — Choosing Background Strategies | https://developer.apple.com/documentation/backgroundtasks/choosing-background-strategies-for-your-app | Apple provides specific system-managed background strategies and limited runtime | VERIFIED | Must verify details for exact OS versions and use case |
| NXS-010 | OpenAI API — Function calling | https://developers.openai.com/api/docs/guides/function-calling | Model can request application-defined tool calls; app handles tool execution | VERIFIED | Does not mean ChatGPT mobile app exposes arbitrary native tool execution |
| NXS-011 | OpenAI Help — Connected apps in ChatGPT | https://help.openai.com/en/articles/11487775-connected-apps-in-chatgpt | Connected app availability varies by app, plan, region, workspace, role, model and interface | VERIFIED | User-specific availability remains UNKNOWN |
| NXS-012 | NASA — System Design Processes | https://www.nasa.gov/reference/4-0-system-design-processes/ | Official NASA system design process reference exists and can inform process design | VERIFIED | Does not certify NEXUS or imply NASA endorsement |

Inspection method: opened official pages using live scrape on 2026-10-10. Exact account-specific integrations, device tests, deployment behavior, and provider quotas remain UNKNOWN until independently checked.


| NXS-013 | OpenAI Help — Developer mode and MCP apps in ChatGPT | https://help.openai.com/en/articles/12584461-developer-mode-and-mcp-apps-in-chatgpt | Official product documentation | Full MCP support/write actions are rolling out in beta to Business, Enterprise and Edu; app setup uses web/workspace developer mode | VERIFIED | User-account access must still be confirmed; current reported plan is Free |
| NXS-014 | OpenAI Help — Build with the Apps SDK | https://help.openai.com/en/articles/12515353-build-with-the-apps-sdk | Official product documentation | Apps SDK uses MCP and supports building/testing apps inside ChatGPT; availability depends on developer-mode access | VERIFIED | Does not prove NEXUS is deployed or registered |


## Fresh official-source verification — 2026-10-10 (UTC)
| ID | Source | URL | Verified claim | Status | Limitation / linked code |
|---|---|---|---|---|---|
| NXS-015 | OpenAI API — Models catalog | https://developers.openai.com/api/docs/models | Current catalog lists GPT-6 Luna as a cost-sensitive high-volume model; page lists model ID `gpt-6-luna`, Responses API/SDK availability, and tool capabilities including functions and web search. | VERIFIED (source statement) | Account entitlement, exact quota and price at activation remain UNKNOWN/NEEDS_REVALIDATION. Default in `nexus/openai_planner.py` and `nexus/api.py`; no live API request made. |
| NXS-016 | OpenAI API — Function calling | https://developers.openai.com/api/docs/guides/function-calling | Responses API function calling lets a model request application-defined functions; the application executes the function and returns output. Tool schemas can be strict, but schema shape does not grant authorization. | VERIFIED (source statement) | NEXUS deterministic policy must separately authorize each handler. Linked to `nexus/openai_adapter.py` and `tests/test_openai_adapter.py`. |
| NXS-017 | OpenAI API — Structured Outputs | https://developers.openai.com/api/docs/guides/structured-outputs | Structured Outputs is designed to constrain generated output to the supplied JSON Schema; it does not prove factual correctness or authorize execution. | VERIFIED (source statement) | Planner output remains `PROPOSAL_ONLY`; linked to `nexus/openai_planner.py` and `tests/test_openai_planner.py`. |
| NXS-018 | OpenAI Help — Developer mode and MCP apps in ChatGPT | https://help.openai.com/en/articles/12584461-developer-mode-and-mcp-apps-in-chatgpt | Page updated “yesterday” when fetched 2026-10-10; it says full MCP support including modify/write actions is rolling out in beta to Business, Enterprise and Edu, with workspace-admin and web availability conditions. | VERIFIED (source statement) | This user's current Free plan and Android-only path do not establish eligibility; direct ChatGPT app registration/live mobile use remains BLOCKED/NOT TESTED. |
| NXS-019 | User-authorized Anchor reference materials | https://anchor.cc/file/a1a12224-ba77-7e5f-9626-a11af08911ee and https://anchor.cc/file/a1a12224-658e-76ad-adb8-9f1410713784 | User explicitly permits use as reference while forbidding wholesale copying of the source project's workflow/system. NEXUS records the boundary in `docs/ANCHOR_REFERENCE_BOUNDARIES.md`. | USER_STATED / RECOVERED | These are design references, not external proof that NEXUS implementation works. |
