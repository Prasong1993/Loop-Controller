# Anchor Reference Use & Non-Copy Boundary
Updated: 2026-10-10
Status: design provenance note for NEXUS; Anchor materials are reference sources, not the NEXUS governing specification.

## User instruction
The user authorized using selected Anchor workspace records and archived project files as reference material and practical examples. The user explicitly did **not** authorize copying that project's entire architecture, workflow, phases, gates, data schema, or operating model into NEXUS.

## What is useful as reference
The following ideas are evaluated and adapted only when they solve a demonstrated NEXUS requirement:
- provenance/status discipline: VERIFIED, RECOVERED, UNKNOWN, BLOCKED, and explicit test execution levels;
- source-of-truth and version/supersession links;
- requirement → component/interface → evidence → acceptance test traceability;
- separating model proposals from deterministic authorization;
- scoped workstreams, dependency mapping, and an integration/challenge review;
- structured operational error/usage records with trace IDs, error codes, root cause, corrective action and retest;
- recovery/checkpoint, idempotency and ambiguous-outcome considerations;
- read-back of saved artifacts and consolidated reporting.

These are candidate engineering principles, not proof that the source project's implementation works. Claims must be checked against current source, official documentation or reproducible tests before they are treated as NEXUS facts.

## What is not copied wholesale
- The Anchor project's identity, names, tables, record IDs, schema, data, code, API implementation, environment variables, credentials, deployment details or legacy project artifacts.
- Its exact Phase 0/A/B/C/D/E/F sequence, review-gate IDs, approval states or release restrictions as NEXUS's own governing lifecycle.
- Its entire capability catalog or every listed API/tool. NEXUS selects only components that meet a traced requirement, current compatibility evidence, security needs and cost/budget policy.
- NASA-specific procedures or aerospace artifacts. At most, general lifecycle and review principles are tailored to software scale.
- Historical/unverified conclusions as current truth. Recovered information is a research lead until revalidated.

## Source pointers reviewed
- Global multi-tool working rule: https://anchor.cc/file/a1a12307-6f31-7d6a-8064-d3b2fa693879
- Agent Workflow Control Platform project home: https://anchor.cc/file/a1a12224-ba77-7e5f-9626-a11af08911ee
- Recovery snapshot: https://anchor.cc/file/a1a12235-c959-73cf-b96c-d6b881a8c04e
- Governing lifecycle / NASA-inspired review principles: https://anchor.cc/file/a1a12232-fb94-7a91-8b12-94b014d7694b
- Current Evidence & Rebuild Rules: https://anchor.cc/file/a1a12224-658e-76ad-adb8-9f1410713784
- Capability/Evidence Registry README: https://anchor.cc/file/a1a12224-5e92-7022-9279-06482e38a4c4

## Boundary decision
NEXUS remains governed by its own requirements, repository source, current official OpenAI/MCP documentation and its own tests. Anchor is an external reference set. Where a reference conflicts with NEXUS requirements or would introduce unnecessary complexity, do not transplant it; record the conflict and use the narrower requirement-driven design.
