# NEXUS ↔ ChatGPT Integration Contract

**Status:** Interface contract draft; live integration NOT CONFIGURED / NOT RUN.

## Intended deployment shape

ChatGPT application (Android/iOS/iPadOS)
→ supported connected app / custom MCP or API action supported by the target account
→ secured HTTPS integration endpoint
→ NEXUS API
→ authoritative SQLite/PostgreSQL state + audit.

This document does not imply the user's account has permission to add custom connectors. Verify capability in the actual ChatGPT account and interface before selecting the integration path. Do not send private credentials in chat.

## Integration selection gate

1. Inspect official current OpenAI guidance for connected apps, custom connectors/MCP, and Actions/API integration.
2. Confirm feature availability for the target account/plan/workspace and mobile interface.
3. Select one supported integration mechanism and document its auth requirements. Do not implement multiple competing connectors by default.
4. Deploy only behind HTTPS and authentication; the API refuses remote access without `NEXUS_API_KEY`.
5. Configure the integration using a secret-management flow. Never commit the token or embed it in client code.
6. Run the acceptance matrix in `docs/VERIFICATION_PLAN.md`; preserve redacted evidence and audit IDs.

## API contract

The draft REST/OpenAPI contract is in `openapi.yaml`. It describes controller operations and bearer authentication. It is not itself a registered ChatGPT app/connector. A custom MCP adapter may be required if the selected ChatGPT integration requires MCP rather than OpenAPI Actions.

## Minimum permission model

- Read: health, task status, project status, audit (project-scoped).
- Write: create project/task, add evidence, transition task, create/restore checkpoint.
- Every write requires authentication and must be policy-gated.
- A denied action must not call an external executor.
- Paid tools require explicit per-operation approval and budget approval.
- Do not expose generic arbitrary URL fetch, arbitrary shell, or arbitrary SQL as ChatGPT tools.
- Redact tokens, credentials and private evidence from logs.

## Error contract

| HTTP | Meaning | Client behavior |
|---|---|---|
| 401 | Missing bearer token | Stop; configure auth; do not retry blindly |
| 403 | Invalid token or policy denial | Stop and report denied action |
| 404 | Project/task/checkpoint not found | Re-check identifier; no blind retry |
| 409 | Invalid state transition or workflow conflict | Read current task/audit, then decide recovery |
| 422 | Request schema invalid | Correct request before retry |
| 429 | Rate limited (if enforced by gateway) | Respect Retry-After; bounded retry only if operation is idempotent |
| 503 | Remote API disabled or runtime unavailable | Report BLOCKED; inspect configuration/runtime |

## Acceptance evidence record

For each run, record:
- test ID and UTC timestamp
- integration method and ChatGPT account/interface capability result (never record credentials)
- task ID, project ID and trace/audit event IDs
- expected versus actual result
- status PASS/FAIL/BLOCKED/NOT RUN
- redacted logs or GitHub Actions URL
- operator and unresolved defects

## Current blockers

- The account-specific supported connector path has not been verified.
- The API is not deployed to a secured public HTTPS runtime.
- No ChatGPT tool/connector is registered against this API.
- End-to-end ChatGPT acceptance has not run.
- Bearer-token auth is a prototype gate, not a substitute for a reviewed production identity/OAuth model.


## Implemented adapter

A remote MCP adapter now exists at `nexus/mcp_server.py` using the Python MCP SDK and Streamable HTTP transport. It exposes bounded controller tools for project/task management, guarded transitions, checkpoint recovery, evidence quote verification, audit readback and route selection. It does not expose arbitrary shell, SQL or arbitrary URL fetch.

Run locally with:
```bash
uvicorn nexus.mcp_server:app --host 127.0.0.1 --port 8000
```
For a remote integration, use a secured HTTPS deployment and set `NEXUS_API_KEY`. Remote calls fail closed when the token is not configured. The shared bearer-token gate is prototype security only; use a reviewed OAuth/identity setup for production.

## OpenAI account capability gate (official documentation checked 2026-10-10)

OpenAI's current Help Center article says full MCP support including write/modify actions is rolling out in beta to ChatGPT Business, Enterprise and Edu, with developer mode/custom MCP apps managed through the web/workspace settings. Availability is account/workspace/interface-dependent. The user's currently reported plan is Free, so **custom MCP app availability on that account is BLOCKED/NOT AVAILABLE based on current documented plan requirements** unless the account/plan changes or another officially supported integration path is confirmed. Do not promise this connector can be added from the current Free plan.

Official references:
- Developer mode and MCP apps: https://help.openai.com/en/articles/12584461-developer-mode-and-mcp-apps-in-chatgpt
- Build with Apps SDK: https://help.openai.com/en/articles/12515353-build-with-the-apps-sdk
- Connected apps availability: https://help.openai.com/en/articles/11487775-connected-apps-in-chatgpt
