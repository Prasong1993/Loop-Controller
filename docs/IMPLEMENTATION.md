# NEXUS Controller — Implementation Guide

## Implemented in this increment
Deterministic state machine, SQLite project/task/evidence/audit/checkpoint storage, evidence and execution gates, cost-aware route selector, HTTP API, unit tests and CI configuration.

## Local run
Requires Python 3.11+.
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m unittest discover -s tests -v
uvicorn nexus.api:app --host 127.0.0.1 --port 8000
```
API docs: http://127.0.0.1:8000/docs. Do not expose this prototype to the public internet. A shared bearer token exists, but production identity, tenant isolation, rate limiting, TLS deployment, secret management and security review are still missing.

## Endpoints
- GET /health
- POST /projects
- GET /projects/{project_id}/status
- POST /tasks
- GET /tasks/{task_id}
- POST /tasks/{task_id}/transition
- POST /tasks/{task_id}/checkpoint
- POST /tasks/{task_id}/restore
- POST /evidence
- GET /projects/{project_id}/audit
- GET /records/search
- POST /ai/plan (OpenAI Responses API + Structured Outputs; proposal only)
- POST /ai/run (OpenAI Responses API + read-only NEXUS function tools)
- POST /policy/route
- POST /evidence/verify (trusted public HTTPS fetch and quote match)
- MCP Streamable HTTP adapter: `nexus.mcp_server:app`

## Required workflow
INTAKE -> RESEARCH -> PLAN -> POLICY -> EXECUTE -> VERIFY -> AUDIT -> COMPLETE.
Research needs at least one VERIFIED evidence item before PLAN. EXECUTE needs expected outcome and verification method. COMPLETE needs AUDIT state and a recorded result.

## Route candidate schema
```json
{"id":"tool-free-1","enabled":true,"permission_ok":true,"capability_ok":true,"cost_tier":"free","warning":false}
```
Paid candidates require allow_paid=true and budget_approved=true. Candidates with warnings are excluded. This selector does not itself call external tools.

## OpenAI provider wiring and budget gate
- Set `OPENAI_API_KEY` only in the server secret environment; never in a client or repository.
- Optional model override: `NEXUS_OPENAI_MODEL`; default currently follows the official catalog's cost-sensitive model `gpt-6-luna`.
- Provider requests are blocked unless the request has `budget_approved=true` **and** the server has `NEXUS_OPENAI_BUDGET_APPROVED=true`. The server-side gate defaults off. This does not establish account entitlement or guarantee a fixed price.
- `/ai/plan` returns `PROPOSAL_ONLY`; the plan is not approved for execution.
- `/ai/run` only exposes project status, task detail and audit read tools; every tool call is checked by deterministic NEXUS policy and scoped to the active project. It exposes no arbitrary shell or code execution.
- The planner currently enables only `web_search` as an optional built-in capability. Code Interpreter remains disabled until compatibility with the chosen model and deployment is verified.
- Operational records capture trace IDs, redacted errors, model/tool events and usage token counts when the provider returns them. Raw prompts, raw tool arguments, raw tool outputs and API keys must not be recorded.

## Production gaps
See ERROR_REPORT.md. Before production: replace the shared bearer token with reviewed identity/OAuth and per-project roles; enforce tenant isolation and rate limits; add migrations and durable backup/restore; finish idempotency/concurrency/recovery; review egress/network security and data retention; run end-to-end, adversarial and remote integration tests; deploy behind HTTPS; verify the actual ChatGPT account/plan integration. Static source changes and CI do not establish these properties.


## Intended ChatGPT-app integration

NEXUS is intended to be accessed through the ChatGPT application on Android, iOS and iPadOS using a connected app/tool/API integration supported by the target account and interface. A separate native NEXUS mobile app is not required.

**Current status: NOT CONFIGURED / NOT RUN.** The FastAPI API in this repository is source/local runtime only; it has not been securely deployed or connected to the user's ChatGPT account. Do not claim live integration until an actual end-to-end round-trip passes.

Acceptance must cover integration discoverability, least-privilege authorization, create/read task, policy denial, audit readback and warning/timeout handling. Physical-device tests are conditional and apply only when native or OS-specific features are introduced.

## API access control
Set `NEXUS_API_KEY` in the server environment and send `Authorization: Bearer <token>` for all non-health endpoints. When no token is configured, non-loopback requests fail closed with HTTP 503; loopback development requests are allowed. Keep the token in a secret manager and never commit it. This is a prototype bearer-token gate, not a complete production identity/OAuth solution.

Unknown project/task/checkpoint identifiers map to HTTP 404; policy denials map to HTTP 403; invalid workflow transitions map to HTTP 409. Safe checkpoint restore is allowed only from BLOCKED/RECOVER and refuses checkpoints at EXECUTE or other unsafe states.

The API contract is documented in [openapi.yaml](../openapi.yaml) and [ChatGPT Integration Contract](CHATGPT_INTEGRATION_CONTRACT.md).

## Remaining production/integration gaps
Tenant isolation tied to authenticated identities, migrations, actual source-content evidence verification, restore/idempotency stress tests, rate limiting, redacted logs, backup/restore, secure deployment and a supported ChatGPT connector/adapter remain open. Do not expose the API publicly until reviewed and deployed securely.


## Remote MCP adapter

The repository now includes `nexus/mcp_server.py`, an MCP Streamable HTTP adapter for the controller:
```bash
uvicorn nexus.mcp_server:app --host 127.0.0.1 --port 8000
```
Set `NEXUS_API_KEY` before remote use and terminate TLS at a trusted HTTPS gateway. Never expose the service publicly without security review. The adapter uses a shared bearer token as an interim gate, not production OAuth/identity.

**ChatGPT account gate:** OpenAI's current Help Center documents full MCP apps/write actions for Business, Enterprise and Edu in beta, with developer mode/app creation managed via web/workspace settings. The currently reported Free plan is not documented as supporting this custom MCP app workflow. Therefore the source adapter can be tested in CI, but ChatGPT registration and end-to-end use are blocked until a supported account/interface and authorized setup path are available.


## Source evidence verification

- `POST /evidence/verify` fetches a public HTTPS text/HTML source and records VERIFIED only when the supplied exact quote is found in the fetched content.
- Direct `POST /evidence` rejects status VERIFIED.
- Fetch controls: HTTPS only, no embedded credentials, standard HTTPS port, public DNS/IP check, redirects disabled, 8-second timeout, 1 MB response limit, and text/HTML content types.
- This is exact quote verification, not semantic entailment. High-impact claims still need reviewer confirmation. The fetcher requires production security review for DNS rebinding/SSRF and parser limitations.


## Anchor reference boundary
The Anchor project materials were consulted only as references for evidence provenance, requirement-to-test traceability, operational error records, checkpoints, and independent read-back. NEXUS does not copy the source project's full workflow/phases, database schema, code, names or gate rules. See [ANCHOR_REFERENCE_BOUNDARIES.md](ANCHOR_REFERENCE_BOUNDARIES.md) and [ARCHITECTURE_MAP.md](ARCHITECTURE_MAP.md).
