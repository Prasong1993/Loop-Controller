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

## 14. Work-lane compatibility, whole-system review, and one final CI submission

The purpose of staged review is to catch compatibility defects by inspecting code before spending CI, test-run, API, or other tool resources. Do not repeatedly trigger expensive external checks while independent work lanes are still being developed. The normal flow is: **review each lane's code continuously → validate compatibility inside each lane → integrate all lanes → review/fix the entire codebase → submit the integrated revision to CI once for the final gate**.

### A. During development — continuous code inspection inside each work lane

- Each independent work lane is responsible for reviewing the code it produces as it evolves. Inspect correctness, control flow, requirements alignment, imports/exports, function signatures, types/schemas, error handling, security-sensitive paths, policy gates, idempotency, and configuration.
- Before marking a lane complete, inspect the whole code group produced by that lane together—not just individual files—to verify that its modules, interfaces, dependencies, data contracts, and internal assumptions are mutually compatible and have no known code-level defects.
- Fix issues found inside the lane before handing its output to integration. Record the lane's revision, reviewed files/contracts, findings, fixes, unresolved issues, and review status.
- This step is code inspection and compatibility review, **not mandatory continuous test execution**. Do not repeatedly run CI or broad test suites for every small edit. A targeted local check is allowed when it materially helps diagnose a specific issue, but it is not the default activity.
- A lane cannot be marked ready for integration while known compatibility errors remain unresolved. If an external dependency or another lane prevents a conclusion, mark that specific point BLOCKED/UNKNOWN rather than guessing.

### B. After all lanes are ready — integrate and review the whole codebase

- Bring all completed work lanes together on the intended integration revision. Resolve duplicate implementations, conflicting edits, inconsistent naming/status vocabulary, incompatible schemas/signatures, missing exports/imports, dependency/configuration conflicts, shared-state assumptions, error-handling differences, policy-gate gaps, and incorrect tool routing.
- Review the integrated codebase as a whole, including the boundaries between every work lane and the overall architecture. Check that all parts fit together and that there are no known code-level errors or unresolved compatibility defects.
- Fix review findings before submitting the revision to CI. After fixes, inspect the changed code and the affected cross-component interfaces again. Continue this review/fix cycle until no known code errors or compatibility issues remain, or document a genuine blocker.
- Keep a clear record of the exact integrated revision and the review evidence. Do not submit partial lane revisions to the final CI gate merely to check each lane separately.

### C. Once the integrated review is clean — one final CI/test gate

- Submit/push the integrated, reviewed revision to the configured CI system once for the normal final validation run, rather than triggering repeated CI runs during development or for each lane. This is the resource-efficient default, provided the repository's CI configuration and branch protections support it.
- The final CI gate runs the checks configured for the project and appropriate to scope, such as unit/component, integration, contract/schema, end-to-end, security/dependency, build/package, and deployment/smoke checks. Do not claim a check ran if it is not configured or was not executed.
- If the CI run passes, tie the result to the exact commit/revision being delivered. If CI fails, inspect the failure, fix the cause, re-review the changed code and affected interfaces, then rerun the necessary checks. A failed CI run must not be hidden merely to save tool usage; correctness and safety take priority over minimizing calls.
- If any code changes after a passing CI run, rerun the checks affected by those changes before delivery. Avoid rerunning unrelated checks when reliable dependency/impact information shows they are unaffected; obey mandatory CI and repository protections.
- Do not bypass required CI, branch protection, approvals, or safety checks in order to force a single run. “One final CI submission” is the intended efficient workflow, not a guarantee that failures or repository rules can never require another run.

### Acceptance criteria

- [ ] Each lane continuously reviews its own code while developing.
- [ ] Each lane reviews its complete code group for internal compatibility and resolves known defects before handoff.
- [ ] All lanes are integrated before the final whole-system compatibility review.
- [ ] The full codebase and cross-lane interfaces are reviewed and known issues fixed before the final CI submission.
- [ ] Broad tests/CI are not repeatedly triggered during routine code edits; targeted checks are used only when useful.
- [ ] The integrated revision is submitted to the configured final CI gate once by default, with additional runs only when failures, later changes, or required repository rules make them necessary.
- [ ] The final report distinguishes code review from executed tests and cites the exact delivered revision and actual CI results.
- [ ] No required test, approval, or safety gate is bypassed merely to reduce tool calls.

## 15. Evidence-first staged workflow and project evidence repository

The user's required workflow is a staged, evidence-first pipeline, inspired by the user's requested NASA-style reference model. Treat the workflow below as a project requirement; do not claim that every detail is an official NASA process unless it is separately verified against authoritative NASA sources. The purpose is to collect and screen evidence once near the beginning, preserve its provenance in a project-scoped central evidence repository, and let later stages reuse progressively refined evidence instead of repeatedly starting research from scratch.

### A. Stage 1 — intake, research, screening, and evidence curation

- Interpret the task, decompose it into the information and decisions needed across the full workflow, and identify acceptance criteria, constraints, and evidence needs.
- Collect relevant source material broadly enough to cover the task, prioritizing official, primary, current, and independently verifiable sources. Record source URI/ID, title, publisher/owner, revision/version, retrieval date, relevant passage or data location, and verification method.
- Screen and classify evidence for authority, freshness, relevance, applicability, completeness, contradiction, and limitations. Preserve the distinction between VERIFIED, RECOVERED, UNKNOWN, and BLOCKED; an unverified item must not be promoted to confirmed evidence.
- Store the screened evidence and its provenance in the central evidence repository for this project. Keep candidate/background evidence separate from the curated evidence set approved for a particular task or stage. The repository is reusable, but evidence is not automatically applicable to every task merely because it is stored there.
- Produce a curated evidence package with stable evidence IDs, concise findings, source links, scope/applicability, confidence or verification status, known contradictions, and gaps. Stage 1 is the main gate that reduces noise and prevents every later stage from repeating the initial research.

### B. Stage 2 — work from Stage 1's curated evidence

- Begin with the Stage 1 curated package and its recorded conclusions. Do not restart broad research or query original sources again by default when the needed evidence is already available and still current.
- Use the curated evidence to perform Stage 2's assigned analysis/work, and record which evidence IDs support each important decision or output.
- If evidence is missing, stale, contradictory, or insufficient for a specific decision, first request/retrieve the relevant supplemental material already screened or indexed by Stage 1. If that cannot resolve the gap, explicitly reopen the appropriate original source/research path, verify the additional material, and add it to the project evidence repository with provenance before relying on it.
- Keep Stage 2 outputs, derived findings, decisions, and unresolved questions as a traceable work package for the next stage. Clearly distinguish source facts from analysis or derived conclusions.

### C. Stage 3 and every subsequent stage — reuse the nearest validated work first

- Start with the immediately preceding stage's outputs and evidence package because it contains the most task-specific analysis. Do not jump back to raw source research when the prior stage already supplies sufficient, current, verified support.
- If the previous stage's package is insufficient, consult the relevant curated evidence and references retained by Stage 1. Return to original sources or conduct new research only if those two levels still cannot close the identified gap, or if freshness/contradiction checks require it.
- When new evidence is acquired, register and verify it, link it to the affected decisions and artifacts, and pass the updated evidence package forward. Never silently replace prior evidence or lose the provenance of a changed conclusion.
- Repeat this handoff pattern for each later stage until the final delivery/acceptance stage. The next stage receives the prior stage's outputs, relevant evidence IDs, decisions, verification status, unresolved gaps, and required acceptance criteria—not merely an unstructured dump of all collected material.

### D. Evidence retrieval order and re-research rule

Use this default retrieval order for each stage:
1. The immediately preceding stage's validated outputs and evidence package.
2. Stage 1's curated project evidence repository and screened supporting references.
3. Original authoritative sources or new research, only for a specific unresolved gap, stale item, contradiction, or verification need.

This is a reuse-first policy, not a prohibition on fresh research. Evidence must be refreshed when its version/date matters, its applicability is doubtful, a contradiction appears, or the stage's acceptance criteria cannot be met. Record why the evidence was reopened and what changed.

### E. Required stage handoff record

Every stage must produce a structured handoff containing:
- Stage ID, task/run ID, input revision, output/artifact references, and completion status.
- Evidence IDs consumed and produced; source provenance; and links from key claims/decisions to supporting evidence.
- Work performed and decisions made, distinguishing directly sourced facts from derived analysis.
- Checks actually performed and their results; do not confuse code/reasoning review with an executed test.
- Missing, conflicting, stale, UNKNOWN, or BLOCKED evidence; assumptions that remain unverified; and any reason the next stage may need to return to an earlier evidence tier.
- Explicit acceptance criteria and whether the stage is ready for handoff.

### Acceptance criteria

- [ ] Stage 1 gathers, screens, classifies, and stores relevant evidence before downstream work depends on it.
- [ ] The project evidence repository preserves provenance and distinguishes the general screened pool from task/stage-specific curated evidence.
- [ ] Stage 2 starts from Stage 1's curated package and does not repeat broad source gathering without a recorded reason.
- [ ] Stage 3 and later stages prioritize the previous stage's validated package, then Stage 1's curated repository, and only then reopen original sources as needed.
- [ ] New or refreshed evidence is verified, registered, and linked to affected decisions before being used as confirmed support.
- [ ] Every stage hands off artifacts, evidence references, status, checks, and unresolved gaps in a structured form.
- [ ] The final output can trace key conclusions and actions through the stages to source evidence.
- [ ] NASA-specific claims about the reference model remain unverified until supported by authoritative NASA documentation.

