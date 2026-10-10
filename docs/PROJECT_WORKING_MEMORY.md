# Project Working Memory — AI Compliance, Audit & Recovery

> Purpose: preserve durable project decisions and operating requirements so future work can retrieve and apply them without relying on chat history. This is a requirements/decision record, not proof that the features are implemented.

## 1. Core objective

The controller must establish whether an AI system actually followed the requirements it was given. A final answer saying “done” is not sufficient evidence. For each task, connect:

**requirement → context/evidence supplied → AI plan and declared rationale → policy decision → actual API/tool actions → observed result → independent verification → final status.**

## 2. What to record

Record every meaningful lifecycle event, including ordinary successful steps—not only errors:

- Task and requirement snapshot: requirement IDs, version/hash, acceptance criteria, constraints and approvals.
- Context manifest: source IDs/URIs, versions or revisions, retrieval time, evidence status, and which evidence was passed to the model.
- Model boundary: model/provider identifier, request metadata, relevant input/output content where permitted, response status, tool-call requests, token/usage metadata when available, and correlation IDs.
- Plan and declared rationale: the plan and explanations actually returned by the model, declared assumptions, selected approach, and requirement-to-step mapping.
- Policy gates: policy/rule version, inputs/evidence used, allow/deny/needs-approval result, and reason code.
- Tool/API execution: requested action, sanitized arguments, authorization result, start/end timestamps, actual response/result reference, side-effect identifier, retries, and idempotency key when supported.
- Checkpoints and state transitions: what state was saved, what was completed, and what remains.
- Verification evidence: independently observed state, test commands/results, requirement-level pass/fail, evidence references and verifier version.
- Terminal outcome: COMPLETED, FAILED, BLOCKED, NOT_RUN, UNKNOWN, or RECOVERED with reason and supporting evidence.
- Logging/backup health: sequence gaps, write failures, spool/replay events, backup manifest, checksum and restore-test outcome.

Never store API keys, access tokens, credentials, or unrestricted sensitive payloads in logs. Apply redaction, data minimization, access control, and retention limits. Use secure content references or encrypted storage for sensitive request/response bodies.

## 3. Do not confuse model reasoning with audit evidence

Store the full relevant material that the application/API actually exposes and is authorized to retain: user instructions, model requests and returned outputs, plans, explanations, tool-call arguments/results, policy decisions, and external observations.

Do not claim to capture hidden internal chain-of-thought or private model runtime state. If an API does not expose a field or event, record it as unavailable/not exposed rather than fabricating it. A model's own explanation is useful context, but it is not proof that the action occurred.

## 4. Independent compliance verification

- Turn each requirement into an explicit, testable acceptance criterion.
- Map each criterion to one or more events and observable evidence.
- Verify actual state independently where possible (e.g. inspect the resulting file, run a test, query the destination, or compare before/after state).
- Enforce ordering constraints at the controller boundary. For example, if tests must precede a write, reject the write when no successful test event exists.
- Treat missing, contradictory, stale, or unverifiable evidence as UNKNOWN or BLOCKED—not VERIFIED.
- Do not permit the AI that performed an action to be the sole judge of whether it complied.
- On verification failure, stop unsafe follow-on actions and avoid blindly repeating non-idempotent side effects.

## 5. Event ledger and durability requirements

Use a project-local append-oriented event ledger (SQLite is the intended primary store) with fields such as:

- event_id, run_id, task_id, trace_id, monotonic sequence
- event_type, timestamp_utc, status, actor, component
- requirement_ids, policy_version, evidence_refs
- sanitized payload/summary, payload hash where appropriate
- checkpoint_id, parent_event_id, error/reason code

Every successful, failed, blocked, skipped and not-run stage should be represented. Critical pre-action events must be durable before an external side effect begins. Use a durable local spool/outbox with idempotent replay if the primary store is temporarily unavailable. If neither the primary ledger nor the spool can durably record a critical pre-action event, fail closed and do not perform that side effect. Do not silently swallow mandatory logging failures.

## 6. Checkpoints, backups and recovery

Create checkpoints at run start, after evidence gathering, before irreversible writes, after mutations, after verification, and at terminal completion.

Back up SQLite using a consistent snapshot mechanism (SQLite backup API or equivalent), not a raw copy of a live database. Each backup should have a manifest containing backup ID, UTC timestamp, schema version, event-sequence watermark, size, SHA-256, record count where practical, and verification/restore-test status. Upload backups in batches to a separate storage failure domain when configured. Verify remote readback/hash when supported.

On recovery: detect runs without terminal events, replay the durable spool idempotently, identify sequence gaps and duplicates, validate backup integrity, and resume only from an approved checkpoint. Never repeat a non-idempotent action merely because its completion event is missing; inspect the external state first.

## 7. Status vocabulary

Use distinct, evidence-based statuses:

- VERIFIED: acceptance criteria passed with recorded evidence.
- COMPLETED: workflow reached its terminal state; this alone does not imply all requirements were verified.
- FAILED: an executed operation or verification failed.
- BLOCKED: cannot proceed due to a known gate, missing authorization, or unavailable prerequisite.
- NOT_RUN: the check/action has not been executed.
- UNKNOWN: evidence is insufficient or contradictory.
- RECOVERED: state/run was recovered; record what was restored and what still needs verification.

Never label an unexecuted live API check as passed. Missing live credentials may block that specific live check but must not stop unrelated offline tests or source review.

## 8. Scope and trust boundaries

- OpenAI is the primary model provider for this project; do not silently substitute another AI provider.
- The ChatGPT mobile/app session and an OpenAI API runtime are different execution surfaces. Repository code cannot assume it can inspect or control this exact ChatGPT session. Only actions routed through instrumented adapters can be reliably logged by the application.
- Log observable actions, outputs, policy decisions and evidence—not private hidden reasoning.
- Do not merge the active pull request without the user's explicit approval.
- Keep original project/source artifacts unchanged unless the user explicitly authorizes editing them.

## 9. Implementation tracking — not assumed complete

The following are acceptance requirements, not claims of existing implementation:

- [ ] Every normal-success, failure, blocked, skipped and NOT_RUN stage is recorded.
- [ ] Requirement-to-evidence mapping is available for each run.
- [ ] Mandatory audit-write failures are surfaced; no silent exception suppression around required logging.
- [ ] Durable spool/outbox and idempotent replay are implemented and tested.
- [ ] Critical pre-action records are durable before side effects.
- [ ] Interrupted-run detection and safe recovery are tested.
- [ ] Backup manifest, checksum/readback and restore test are implemented.
- [ ] Tests verify that the controller detects requirement violations and refuses unsupported VERIFIED claims.
- [ ] CI results and live-provider tests are reported separately and truthfully.

## 10. Operating rule for future work

Before coding, retrieve this file and the current repository evidence. Update this file only when there is a meaningful new decision, verified implementation status, test result, risk, or unresolved blocker. Keep it concise and current; do not turn it into a raw research dump. Record code changes and test results with links/commit references where available.

## 11. Parallel execution and multi-tool orchestration

Parallel execution is the default when tasks are independent and the connected tools support concurrent calls. Do not serialize work merely because a sequential workflow is familiar or easier to describe.

- Decompose each request into small work units; identify dependencies, shared-file conflicts, ordering constraints, permissions, and irreversible side effects before dispatch.
- Run independent research, repository inspection, test preparation, status checks, and storage checks concurrently where appropriate. Select tools by capability and evidence quality, not habit; use all relevant connected tools when they add value.
- Keep dependent operations ordered. For example, do not publish or back up a new artifact before its content/version is finalized when the backup is expected to represent that exact revision.
- Avoid concurrent writes to the same file, branch, database row, or mutable resource unless the operation is explicitly safe and conflict-controlled. Use separate work units/branches or serialize only the conflicting writes.
- Give each work unit a clear input, expected output, owner/tool, dependency list, and completion criterion. Collect results at a coordination point and reconcile conflicting evidence before taking dependent actions.
- For cross-service work (such as GitHub plus Dropbox), treat each service as a separate result: confirm each write/readback independently, compare revision identifiers or content hashes when feasible, and report partial success honestly. One service succeeding does not imply the other succeeded.
- Record parallel task/run IDs, start/end times, dependencies, tool calls, outputs, retries, failures, and final reconciliation in the audit trail. Mark unlaunched or unsupported work NOT_RUN/BLOCKED rather than implying it ran.
- Use bounded concurrency and respect rate limits, quotas, API budgets, and provider/tool restrictions. Do not duplicate a call after a warning unless the warning and retry policy permit it.
- Parallelize independent work; sequence only where a real dependency, safety gate, shared-resource conflict, or approval requirement demands it. The objective is lower elapsed time without reducing traceability, correctness, or user control.
- Do not claim permanent background execution or automatic cross-service synchronization unless that automation has actually been configured and tested.

### Parallel-work acceptance criteria

- [ ] The plan explicitly identifies parallelizable tasks and dependencies before execution.
- [ ] Independent tool calls are dispatched concurrently when supported and beneficial.
- [ ] Shared-resource writes and irreversible actions have explicit conflict/order controls.
- [ ] Results from every dispatched work unit are collected and independently checked.
- [ ] Partial failures and NOT_RUN/BLOCKED work are visible in the final report.
- [ ] A benchmark or execution log can compare elapsed time and correctness against an unnecessarily sequential baseline when useful.

