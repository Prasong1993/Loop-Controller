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

## 12. Tool-first intake and work orchestration

Tool selection and work decomposition must begin at task intake, not after a long, purely sequential analysis. As soon as a user message arrives, determine the task intent, applicable project, risk/approval boundaries, and the kinds of evidence or outputs needed; then select the appropriate connected tools and skills to structure the work.

- Start with a lightweight intake record: task/run ID when available, objective, deliverables, constraints, acceptance criteria, required evidence, and any approval gates.
- Retrieve the current project Working Memory and relevant source-of-truth artifacts early when the request belongs to an existing project. Do not mix unrelated or stale project context into the active task.
- Inspect the available tool/skill inventory when capability choice matters. Select tools by their actual capabilities and access, not by habit; include tools for retrieval, code/repository work, testing, storage, and independent verification where relevant.
- Build a dependency-aware work graph before executing substantial work. Mark each unit as parallelizable, dependent, approval-gated, or blocked; assign expected inputs/outputs and verification criteria.
- Launch independent initial discovery concurrently where supported—for example, official-documentation research, repository/status inspection, test discovery, and backup/storage checks. Merge their results into one evidence register before making decisions that depend on them.
- Use tools as external work-management and evidence mechanisms: task decomposition, retrieval, durable notes, task IDs, checkpoints, test execution, audit records, and result reconciliation. Do not claim that tools expose or control hidden internal model reasoning; preserve only the instructions, outputs, actions, and events actually available to the application.
- Keep the intake/orchestration process proportional: use a lightweight path for simple questions, and a structured multi-tool plan for project work, multi-step tasks, risky changes, or requests involving several systems.
- Do not wait until analysis is entirely finished to discover that a necessary tool, source, or verification path was available. Identify tool needs early, while still allowing the plan to change when evidence reveals new dependencies.
- Before final delivery, reconcile the work graph against actual tool results and mark each work unit VERIFIED, COMPLETED, FAILED, BLOCKED, NOT_RUN, UNKNOWN, or RECOVERED as supported by evidence.

### Tool-first intake acceptance criteria

- [ ] Tool/skill selection starts at intake for project and multi-step work.
- [ ] Current project memory and source-of-truth files are retrieved before changes.
- [ ] The tool inventory is checked when relevant rather than defaulting to a familiar tool.
- [ ] Independent discovery tasks are launched concurrently when supported.
- [ ] A dependency-aware work graph identifies parallel tasks, serial dependencies, approval gates, and verification steps.
- [ ] Final status is reconciled with actual tool evidence; no planned or unlaunched work is reported as executed.

## 13. Skill-family orchestration and parallel work lanes

Treat available skills and capabilities as reusable work patterns that can be applied to multiple independent work units. Do not assume that one skill family can only be used once per task, or that selecting one skill prevents using related tools and other skills. Equally, do not assume the platform supports unlimited duplicate skill instances or unlimited concurrency: inspect actual tool/skill contracts and respect their execution limits.

- At intake, classify work into capability families (for example: research/evidence, repository/code, testing/QA, data analysis, storage/backup, deployment/operations, and independent review) based on the actual available inventory.
- Split a large task into independent lanes. Multiple lanes may use the same skill family concurrently when each lane has a distinct scope, inputs, output, and acceptance criteria and the tool runtime supports those calls.
- For each lane, select the appropriate subordinate tools/connectors. A skill guides the method; tools perform the concrete retrieval, edit, execution, or verification. Do not confuse loading a skill's instructions with executing the work.
- Build a capability map: skill/capability family → eligible tools → supported operations → permissions/credentials → concurrency/rate limits → verification method.
- Choose the number of concurrent lanes dynamically from task size, independence, tool limits, API quotas, and risk. A number such as five concurrent lanes is a possible target only if the actual environment supports it; never report a concurrency level as available or achieved without evidence.
- Avoid redundant lanes that repeat the same search or mutate the same resource. Use separate scopes for parallel investigation, then merge results at a defined coordination point. Serialize conflicting writes and approval-gated actions.
- If a skill or tool is unavailable, not installed, disconnected, or lacks permission, mark that lane BLOCKED/NOT_RUN and continue other independent lanes where possible. Do not let one unavailable tool stop all unrelated work.
- Record which skill instructions were consulted, which tools actually ran, each lane's inputs/results/status, and the evidence supporting the final synthesis. Do not claim that a skill itself performed an operation unless a corresponding tool/action result confirms it.

### Skill-family orchestration acceptance criteria

- [ ] Relevant installed skills and available tools are inventoried at intake for substantial project work.
- [ ] Capability families can be reused across multiple independent lanes where supported.
- [ ] Each lane is mapped to concrete subordinate tools, permissions, dependencies, and verification.
- [ ] Concurrency is bounded by observed platform/tool limits rather than an arbitrary hard-coded number.
- [ ] Tool/skill failures are isolated so unrelated work can continue.
- [ ] The final report distinguishes skill guidance consulted, tool actions executed, and outcomes independently verified.

## 14. Continuous code review, final compatibility review, and pre-delivery testing

Keep code review and testing as separate activities. The correct order is: review code continuously while it is being developed → perform a final whole-code compatibility review after integration → run the integrated test/CI/CD gate before delivery.

### A. During development — continuous code inspection (not continuous testing)

- Inspect code changes continuously as each component/work lane is developed. Review correctness, readability, control flow, interface contracts, imports/exports, types/schemas, error handling, security-sensitive paths, policy gates, idempotency, and consistency with the current requirements.
- This step means reviewing and checking the code itself as it evolves; it does **not** mean repeatedly running tests throughout development as a mandatory continuous activity.
- Run a focused check or a targeted test during development only when useful to investigate a suspected defect or validate a specific change. Do not label such targeted checks as a requirement for continuous testing.
- Record meaningful findings, affected files/revisions, fixes, and unresolved concerns. Component-level review does not prove that the integrated system is compatible.

### B. After integration — final whole-code compatibility review

- Review the full integrated codebase as a whole before the final test gate. Check architecture and cross-component consistency: module boundaries, imports/exports, function signatures, schemas, event/status vocabulary, shared state, error handling, idempotency, policy gates, configuration, dependency constraints, and tool routing.
- Resolve review findings before proceeding to the pre-delivery testing gate, where practical. If changes are made after a later test run, the relevant checks must be rerun.
- This is a static compatibility/consistency review; it is not a substitute for automated tests.

### C. Before delivery — integrated testing and CI/CD gate

- After the final compatibility review and its fixes, run the appropriate integrated automated test suite and configured CI/CD checks before delivery: unit/component tests, integration tests, contract/schema tests, end-to-end tests where feasible, security/dependency checks, build/package checks, and deployment/smoke checks when in scope.
- Investigate failures, fix them, and rerun affected checks. A change made after a successful test invalidates the relevant evidence until the affected checks are rerun.
- Report each check as passed, failed, blocked, or not run, with links/logs/revision references where available. Never imply CI/CD or live tests ran if they did not.
- If testing exposes a defect and code/configuration changes are made, return to the relevant code-review step, review the changed code, and rerun affected tests. Repeat this correction/review/test cycle until required checks pass or a real blocker is documented.
- Freeze the delivered revision and tie the final report to its commit/revision and test evidence for that exact revision. If the revision changes afterward, re-evaluate the evidence.

### Acceptance criteria

- [ ] Code is inspected continuously during development; this does not require tests to run continuously.
- [ ] A final whole-code compatibility review is performed after integration and before the final test/CI gate.
- [ ] Integrated automated tests and configured CI/CD checks are completed before delivery where configured and in scope.
- [ ] Review findings or test failures that lead to code changes trigger review and reruns of affected checks.
- [ ] The final report separates code-review findings, compatibility-review findings, and actual test results, and identifies unrun checks.
- [ ] Test evidence refers to the exact delivered revision, or any later changes have triggered the necessary reruns.

