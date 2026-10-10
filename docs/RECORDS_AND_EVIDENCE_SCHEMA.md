# NEXUS Record and Evidence Schema

Version: 1.0  
Status: IMPLEMENTATION CONTRACT — not a claim that every producer/query endpoint is wired yet.

## Design goals

Records must be machine-readable, append-only by default, searchable without rereading raw research dumps, sufficient to resume interrupted work, and useful for investigating failures. Every record belongs to a project; task, trace, and operation links are optional only when the event occurs before those identifiers exist. The system records actions and failures automatically at integration boundaries; the user is not expected to manually write logs.

## Canonical record envelope

All operational records use the following logical envelope (JSON-compatible):

```json
{
  "schema_version": "1.0",
  "record_id": "uuid",
  "record_type": "usage | error | evidence | decision | checkpoint | verification",
  "project_id": "uuid",
  "task_id": "uuid-or-null",
  "session_id": "opaque-id-or-null",
  "trace_id": "uuid",
  "operation_id": "uuid-or-null",
  "occurred_at": "UTC RFC3339 timestamp",
  "actor_type": "user | model | system | tool",
  "actor_id": "non-secret identifier-or-null",
  "source_status": "VERIFIED | RECOVERED | UNKNOWN | BLOCKED",
  "payload": {},
  "links": []
}
```

The envelope is a logical contract, not permission to mark ordinary usage records as evidence. `source_status` is mandatory for evidence records; other record types may use `UNKNOWN` to mean no external claim is being asserted. Never store API keys, authorization headers, raw secrets, or unrestricted request/response bodies.

## Record types

### usage
Required payload fields: `operation`, `component`, `input_summary`, `outcome`, `duration_ms`, `http_status` (nullable for non-HTTP tools), `attempt`, `idempotency_key` (nullable), `started_at`, `finished_at`. Store summaries and hashes/IDs, not full sensitive payloads. Record denied operations as usage with outcome `BLOCKED`.

### error
Required payload fields: `error_code`, `severity`, `category`, `message_redacted`, `component`, `operation`, `retryable`, `retry_reason`, `first_seen_at`, `last_seen_at`, `occurrence_count`, `resolution_status`, `related_record_ids`. Keep a safe diagnostic message and exception class; stack traces go only to access-controlled server logs after redaction. Policy denials, validation failures, transient transport failures, timeouts, and ambiguous side effects must be distinct categories. A denial is not automatically retryable.

### evidence
Required payload fields: `claim`, `source_url`, `publisher`, `page_title`, `retrieved_at`, `source_revision` (nullable), `quote`, `quote_sha256`, `verification_method`, `limitations`, `reviewer`, `linked_requirement_ids`, `linked_test_ids`, `status`. URL presence alone never means VERIFIED. VERIFIED requires content fetched by the trusted verifier and a persisted provenance record. Exact quote match proves the quote was present, not that the source semantically entails every interpretation of the claim.

### decision
Required payload fields: `decision_id`, `gate`, `rule_id`, `input_record_ids`, `decision`, `reason_code`, `reason`, `policy_version`, `approval_ref` (nullable). Record ALLOW/BLOCK and paid-cost approval distinctly. Policy decisions must be deterministic and must not invoke an LLM.

### checkpoint
Required payload fields: `checkpoint_id`, `state`, `schema_version`, `snapshot_hash`, `created_at`, `restore_count`, `restore_status`. Checkpoints capture resumable workflow metadata, not credentials or replayable side effects. Restore must be guarded against stale state and must never automatically replay an ambiguous EXECUTE operation.

### verification
Required payload fields: `verification_id`, `target_record_id`, `method`, `expected`, `observed`, `result`, `verifier_version`, `checked_at`, `test_run_url` (nullable). Distinguish static review, unit tests, integration tests, and live platform acceptance.

## Storage and indexing

Use normalized, append-only tables for `usage_events`, `error_events`, `evidence_records`, `decisions`, `checkpoints`, and `verification_results`, with the common envelope columns indexed. Required indexes: (project_id, occurred_at), (task_id, occurred_at), trace_id, operation_id, record_type, status/error_code, and evidence claim/source hash. Payloads should be JSON with schema_version and validated fields. Migrations must be versioned and safe for existing SQLite databases; never silently drop existing audit history.

## Search and read contract

Queries must support:
- exact `record_id`, `trace_id`, `operation_id`, `task_id`, `error_code`, evidence ID/hash;
- filters by project, record type, status, severity, component, time range, and source;
- full-text search over redacted summaries, claims, reasons and error messages;
- chronological trace view that joins usage → policy decision → execution → verification → audit;
- error recurrence view grouping by normalized error code/category and showing the last known resolution;
- source re-research by URL, retrieval timestamp, quote/hash, revision and linked requirements/tests.

Every result should return stable record IDs, timestamps, schema version, pagination cursor, and provenance links. Never present a partial search as a complete history.

## Automatic capture rules

1. Every REST/MCP operation records start/end, component/tool name, outcome, duration, actor/session/trace where available, and safe request summary.
2. Every exception or denied operation records a stable error code/category and links to its usage event; preserve the original exception class for diagnostics.
3. Every research fetch records URL, retrieval time, quote/hash, content type/size, verifier method/version, and a failure record if fetch or verification fails.
4. Every policy decision records the rule/version and the reason, including BLOCK decisions.
5. Checkpoint creation, restore, failed restore, and interrupted/ambiguous execution are all events.
6. Correlation IDs propagate across API → controller → tools → provider adapters. Retries reuse an idempotency key when safe; ambiguous side effects are marked UNKNOWN and reconciled before retry.
7. Logs are redacted, bounded, access-controlled, and never treated as evidence merely because they exist.

## Release tests required

- Migrations preserve pre-existing projects/tasks/evidence/audit rows.
- Each REST and MCP call creates one usage record, including failed calls.
- Each failure produces a linked error record without leaking secrets.
- Search filters and pagination return deterministic results.
- Evidence provenance cannot be forged by passing caller-provided source text.
- Policy denial is logged and never automatically retried.
- Trace joins cover the complete lifecycle and identify the first failed gate.
- Concurrent requests do not duplicate or overwrite operation records.
- Retention/export and backup/restore are tested before production.

## Current implementation boundary

The existing `audit_log` stores selected workflow events. It is not yet equivalent to the full usage/error/evidence record system specified here. Until producers, migrations, search endpoints, and regression tests are wired and pass, automatic full capture is **OPEN**, not complete. ChatGPT-account registration and live mobile integration remain separate release gates.
