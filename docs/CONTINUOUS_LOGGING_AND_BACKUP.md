# Continuous Operational Logging and Backup

Updated: 2026-10-10
Status: target design; distinguish implemented behavior from requirements not yet wired or tested

## Goal

Every workflow stage must leave an inspectable record, whether it succeeds, fails, is blocked, is skipped, or is not run. Logs are operational evidence, not model memory. The controller must not claim an unrun check passed.

## Event lifecycle

For each run, create a run_id and propagate project_id, task_id (when available), session_id (when available), trace_id, operation_id, sequence number, timestamp, actor/component, stage, event, outcome, reason/error code, evidence references, checkpoint reference, and verification result.

Minimum lifecycle events:
- RUN_STARTED / REQUEST_ACCEPTED
- STAGE_STARTED before each stage
- EVIDENCE_RETRIEVED or EVIDENCE_NOT_AVAILABLE
- POLICY_ALLOWED / POLICY_BLOCKED
- PROVIDER_REQUEST_STARTED before the external request
- PROVIDER_RESPONSE_RECEIVED or PROVIDER_REQUEST_FAILED
- TOOL_STARTED / TOOL_COMPLETED / TOOL_FAILED
- CHECKPOINT_CREATED
- VERIFICATION_STARTED / VERIFICATION_PASSED / VERIFICATION_FAILED / VERIFICATION_NOT_RUN
- BACKUP_STARTED / BACKUP_COMPLETED / BACKUP_FAILED
- RUN_COMPLETED / RUN_FAILED / RUN_BLOCKED / RUN_INTERRUPTED

A terminal event must not replace stage events. A run left without a terminal event must be reported as INTERRUPTED/INCOMPLETE during recovery, not assumed successful.

## Storage responsibilities

1. **Primary event ledger:** SQLite operational_records and router run ledger, append-only through application interfaces, indexed by project/task/trace/operation/time.
2. **Durability boundary:** commit each event in a short transaction. For critical pre-action events, persist before crossing an external/provider/tool boundary. If the primary database is unavailable, use a durable local append-only spool/outbox with fsync and a replay procedure; do not silently discard the event. If neither primary storage nor the durable spool accepts a mandatory event, stop before the side effect.
3. **Redaction:** store IDs, safe summaries, status, hashes, usage and references. Do not store API keys, authorization headers, raw prompts, full model outputs, private files, or raw tool arguments in operational logs. Sensitive work artifacts belong in access-controlled project storage, not the log ledger.
4. **Truthful statuses:** VERIFIED, RECOVERED, UNKNOWN, BLOCKED, NOT_RUN, FAILED and COMPLETED have distinct meanings. NOT_RUN is not FAILED; neither is success.

## Checkpoints and periodic backups

- Create logical checkpoints at run start, after evidence collection, before irreversible writes, after a successful mutation, after verification, and at terminal state.
- Use SQLite's consistent backup mechanism (for example, the SQLite backup API or VACUUM INTO) rather than copying a live database file blindly.
- Create a manifest per backup: backup_id, UTC time, source database/schema version, highest included event sequence or watermark, file size, SHA-256, record count, and verification result.
- Upload completed snapshots in bounded chunks/periods to a configured remote destination. Upload only after the local snapshot is complete; then read back metadata/hash where the destination supports it. Record upload outcome, destination reference, and any retry.
- Keep local working database, local recovery spool, and remote backup as separate failure domains. Remote backup must never be the only copy of the current live ledger.
- Retain daily and weekly snapshots according to an explicit retention policy; test restore periodically into a separate location and compare schema, row counts, event watermarks, and checksums.
- Do not upload raw prompts, secrets, or full private artifacts as part of telemetry. Back up the database according to its access-control and encryption requirements.

## Backup scheduler and recovery

A scheduled worker may run backups periodically, but scheduling is not the logging mechanism. Every backup attempt itself emits BACKUP_STARTED and BACKUP_COMPLETED/BACKUP_FAILED records. On startup, recovery should:
1. find runs without terminal events;
2. report them as interrupted;
3. replay valid spool entries idempotently using a unique event_id;
4. detect sequence gaps and duplicate events;
5. verify the latest backup manifest and database integrity;
6. resume only from an approved checkpoint, never automatically repeat a possibly completed non-idempotent action.

## ChatGPT/OpenAI boundary

The ChatGPT app's internal reasoning, hidden context, and private runtime telemetry are not exposed as a complete event stream to repository code. NEXUS can log the explicit actions, tool/API calls, decisions, evidence references, and outcomes that pass through its own adapters. This does not make a ChatGPT app session directly callable by the repository's OpenAI API client. Record the boundary accurately and continue all available offline checks when live access is NOT_RUN or BLOCKED.

## Current known implementation gap

Static source inspection of `nexus/api.py` shows the general REST middleware catches and suppresses exceptions from operational record writes. That behavior can lose ordinary request logs without surfacing the loss. The `/ai/run` callback was separately changed to propagate mandatory record failures, but the general middleware still needs a durable spool/outbox or a clearly visible health/degraded-state signal before continuous logging can be claimed as guaranteed.

## Acceptance criteria

- Every accepted run has a durable start event and a terminal or recoverably interrupted state.
- Every stage has start and outcome events, including normal success and explicit NOT_RUN/BLOCKED states.
- Every external side effect has a pre-action intent/checkpoint and a post-action result/verification record.
- Failure to write an event is visible; no blanket `except: pass` around mandatory logging.
- Backup manifests include hashes and watermarks; at least one restore test proves the backup can be read and reconciled.
- Unit tests cover normal path, failure path, spool fallback/replay, duplicate replay, interrupted run recovery, backup checksum mismatch, and restore verification.
- CI status and live service status are reported separately.
