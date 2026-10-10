# NEXUS Operational Record Schema
Updated: 2026-10-10
Schema version: `1.0`
Implementation: `nexus/records.py`

## Purpose
This is NEXUS's own operational log contract, designed for automatic recording, readback, filtering and error diagnosis. It is not copied wholesale from the Anchor project's schema. It complements, but does not replace, the workflow `audit_log` stored by the deterministic core.

## Record envelope

| Field | Required | Purpose |
|---|---|---|
| `record_id` | yes | Unique immutable identifier for this record. |
| `schema_version` | yes | Envelope version, currently `1.0`; future schema changes must be versioned. |
| `record_type` | yes | `usage`, `error`, `evidence`, `decision`, `checkpoint`, or `verification`. |
| `project_id` | yes | Project scope used for isolation and search. |
| `task_id` | no | Task scope when known; null for project-level or system events. |
| `session_id` | no | Session correlation when available. |
| `trace_id` | yes | Correlates one request across REST/MCP/provider/adapter events. |
| `operation_id` | no | Correlates a provider response, tool call, or logical operation. |
| `occurred_at` | yes | UTC ISO-8601 timestamp. |
| `actor_type` | yes | E.g. user, system, tool, worker. |
| `actor_id` | no | Authenticated actor identifier when available; do not invent one. |
| `status` | yes | Outcome such as SUCCESS, FAILED, BLOCK, DENIED, or RECORDED. |
| `component` | yes | Stable subsystem label, e.g. rest_api, mcp_server, openai_responses, openai_code_proposal. |
| `error_code` | no | Stable machine-readable reason; required for categorized failures/denials where known. |
| `severity` | no | Severity used for prioritization; do not infer high severity without evidence. |
| `summary` | yes | Short human-readable summary, capped at 1,000 characters. |
| `payload_json` | yes | Redacted structured metadata only; not a dump of the conversation or request body. |

## Record-type guidance

- **usage:** operation, component, duration, HTTP/provider outcome, model/tool identifiers, token counts when returned.
- **error:** stable error code, exception class/category, retryable decision, component, HTTP/provider outcome. Never persist credentials or full exception bodies that might contain user data.
- **evidence:** evidence ID, source URL, task/project scope, verification method, quote hash, retrieval timestamp/status. Core evidence truth remains in the evidence table and core audit log.
- **decision:** ALLOW/BLOCK decision, rule/reason code, selected route/capability, approval gate outcome.
- **checkpoint:** checkpoint ID, task ID, saved state, restore decision. Snapshot contents remain in the checkpoint table, not copied into operational payloads.
- **verification:** expected/observed result summary, test identifiers and result; do not claim a test ran without execution evidence.

## Search and correlation
`GET /records/search` and MCP `nexus_search_records` support project scope and filters for record type, task, trace, operation, status, error code, component, text query and time range, with pagination. Indexes support project/time, task/time, trace, operation, type/status, error and component queries.

Preferred investigation sequence:
1. Start with `project_id` and `task_id`.
2. Follow `trace_id` across request, provider, tool and verification events.
3. Use `operation_id` to group a provider response/tool call.
4. Filter `record_type=error` and `error_code` to diagnose failure.
5. Read core `audit_log` for authoritative state transitions and evidence/checkpoint events.
6. After any repair, record the corrective action and rerun the relevant test; do not overwrite or erase the original failure record.

## Privacy and failure policy
- Do not store raw prompts, full tool arguments, full model outputs, source page bodies, API keys, authorization headers, passwords, tokens, private keys or environment file contents.
- Code proposals store only path, operation, SHA-256 and content length in operational records; proposed source content is returned to the caller but is not persisted in the record payload.
- The record writer rejects common secret-bearing keys recursively. Callers must still redact values before invoking it.
- Logging failure must never authorize an otherwise denied action. When the log write fails, the operation should fail closed where auditability is a safety requirement, or return an explicit observability warning for non-critical read operations; current wrappers favor preserving the primary response and this remains a production policy decision.
- Record retention, encryption at rest, user/tenant access controls, backup/restore and deletion policy are not yet implemented. The shared bearer token is not sufficient for production multi-tenant isolation.

## Known limitations
The operational store and workflow core may be configured to separate SQLite paths; no transaction across those files is atomic. Prefer a single configured database path for the prototype. This schema is append-oriented but is not tamper-proof or cryptographically chained. Production deployment needs migrations, retention and audit-integrity controls.
