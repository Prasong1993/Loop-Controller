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
