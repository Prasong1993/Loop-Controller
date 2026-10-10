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
API docs: http://127.0.0.1:8000/docs. Do not expose this initial API to the public internet; authentication/TLS/production hardening are not implemented.

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
- POST /policy/route

## Required workflow
INTAKE -> RESEARCH -> PLAN -> POLICY -> EXECUTE -> VERIFY -> AUDIT -> COMPLETE.
Research needs at least one VERIFIED evidence item before PLAN. EXECUTE needs expected outcome and verification method. COMPLETE needs AUDIT state and a recorded result.

## Route candidate schema
```json
{"id":"tool-free-1","enabled":true,"permission_ok":true,"capability_ok":true,"cost_tier":"free","warning":false}
```
Paid candidates require allow_paid=true and budget_approved=true. Candidates with warnings are excluded. This selector does not itself call external tools.

## Production gaps
See ERROR_REPORT.md. Before production: authentication/authorization, tenant isolation, migrations, verified evidence ingestion, checkpoint restoration, rate limiting, secret management, structured redacted logging, idempotency keys, backup/restore, deployment configuration and platform-specific clients/adapters.


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
