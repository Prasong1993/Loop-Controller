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
