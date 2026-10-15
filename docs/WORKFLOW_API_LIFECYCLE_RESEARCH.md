# Workflow API Lifecycle Research — Command to Verified Delivery

**Research date:** 2026-10-11  
**Repository:** `Prasong1993/Loop-Controller`  
**Branch:** `feature/tr-req-001-tool-router`  
**Status:** OFFICIAL DOCS REVIEWED; ACCOUNT ACCESS / LIVE PROVIDER TESTS NOT RUN  
**Purpose:** Map the minimum API and controller components needed from receiving a user command through verified delivery, while minimizing unnecessary model calls and cost.

## 1. Executive recommendation

Keep the existing NEXUS application controller and use the **OpenAI Responses API** as the primary model boundary. Continue using **Structured Outputs** for machine-readable plans and **Function Calling** to request allowlisted application tools. Do not replace deterministic policy, routing, persistence, or independent verification with an LLM or a managed agent runtime.

The official Agents documentation describes Agents API as a managed Codex harness for long-running tasks, Agents SDK as an application-controlled agent loop, and Responses API as the direct model/integration interface. Since this project already has a Responses adapter, a structured planner, deterministic router, audit/runlog components, and explicit policy gates, migrating to Agents API is not justified before a measured comparison. Reconsider Agents SDK only if reusable orchestration materially reduces code without weakening our gates.

“Manage the AI thinking process” means managing observable inputs/outputs, task plans, declared assumptions, tool requests, policy decisions, usage, checkpoints, and independently observed results. It does not mean accessing hidden chain-of-thought or private ChatGPT Android runtime state.

## 2. End-to-end lifecycle and required components

| Stage | What happens | API / component | Required gate or evidence |
|---|---|---|---|
| 0. Receive command | Accept task text, project identity, constraints and any explicit approvals | A supported client/REST/MCP ingress; existing NEXUS API where available | Authentication, canonical project ID, request/trace/task IDs. The current ChatGPT Android session is NOT proven connected to this repository runtime. |
| 1. Validate intake | Check required fields, size, scope, duplicates and project status | Local deterministic validation; no model call for simple checks | Reject invalid/ambiguous project identity; never guess project aliases. |
| 2. Restore context | Load project checkpoint, decisions, relevant evidence IDs, status and next permitted step | Existing SQLite/controller/record store and GitHub connector as configured | Project isolation; use latest verified project state; distinguish VERIFIED / RECOVERED / UNKNOWN / BLOCKED / NOT RUN. |
| 3. Analyze and plan | Turn command into goal, constraints, subtasks, required evidence, risks, expected outputs and acceptance checks | Responses API + Structured Outputs, using a cost-sensitive model only after its account access and suitability are confirmed | Output is a proposal only; schema validity is not truth or authorization. Keep stable instructions/schema prefixes where possible. |
| 4. Gather evidence | Reuse validated project evidence first; research official sources only for gaps, stale claims or conflicts | Existing evidence store; Responses web_search tool or an approved external research adapter when needed | Record source URL, retrieval time, quoted/supporting detail, evidence status and claim linkage. Search output is candidate evidence until screened. |
| 5. Decompose and route | Convert plan into executable work units; select eligible tool/provider based on capability, permissions, warnings, quota and cost | Deterministic controller + existing free-first Tool Router | No model can override routing. Paid use requires both `allow_paid=True` and `budget_approved=True`; unknown availability/quota is not treated as true. |
| 6. Authorize action | Check each proposed function/tool call against allowlist, project scope, policy and approval requirements | Function Calling is the request format; deterministic policy is the authority | Strict JSON Schema where supported; reject malformed, unregistered, out-of-scope or unauthorized calls. Persist a pre-action event/checkpoint before side effects. |
| 7. Execute | Run approved read/write/API/test operation | Application-owned tool handler/adapter; external API selected by capability | Idempotency where supported; capture sanitized arguments, operation ID, result reference and side-effect identifier. No blind retries for non-idempotent operations. |
| 8. Record usage/state | Save response IDs, token usage, timing, tool rounds, decisions, errors and checkpoint transitions | Responses usage metadata + existing audit/runlog/SQLite | Never log credentials or unrestricted sensitive payloads. Mandatory audit persistence failure must stop side effects. |
| 9. Verify independently | Check resulting files/state/API records, run tests, compare acceptance criteria and verify evidence references | Deterministic verifier, test runner, read-back through destination API; optional Evals API for offline/regression model-quality tests | The model that performed the action cannot be the sole judge. A response saying “done” is not proof. Verification failure blocks completion. |
| 10. Repair or recover | Diagnose failed criterion, update plan, resume from safe checkpoint and repeat affected checks | Controller state machine + a model call only when new analysis is necessary | Retry only explicitly classified safe errors. If verification failed after a side effect, stop fallback and inspect actual state before any repeat. |
| 11. Deliver and close | Return artifacts/links, verified results, test evidence, cost/usage when available, remaining blockers and status | Controller-generated final report using verified records; optional model formatting | Use COMPLETED only for terminal workflow state; separately state which acceptance criteria are VERIFIED. Save final checkpoint and read it back. |

## 3. API choice by job

| Candidate | Use in this workflow? | Why / boundary |
|---|---|---|
| **Responses API** | YES — primary | Already used in `nexus/openai_adapter.py` and `nexus/openai_planner.py`; direct request/response and tool-call handling keeps the app controller in charge. |
| **Structured Outputs** | YES | Makes plans/records conform to a JSON Schema; does not verify facts or grant permissions. |
| **Function Calling** | YES | Lets the model request registered functions; application code executes only after deterministic authorization. |
| **Built-in web search** | CONDITIONAL | Use for current public facts when needed. Record source provenance and independently screen evidence. Do not send every task through web search. |
| **Agents API** | NOT THE FIRST CHOICE | Managed Codex harness, useful for long-running tasks where managed agent infrastructure is desired. It is not a replacement for our project-specific audit/policy requirements without a gap analysis. |
| **Agents SDK** | DEFER | Can manage an application-side agent loop and handoffs. Consider only if it reduces orchestration complexity while preserving NEXUS's deterministic gates and persistent state. |
| **Evals API** | YES, for test/evaluation lanes | Useful for repeatable model/prompt quality tests over datasets. It is not a runtime permission system and cannot replace deterministic acceptance checks. |
| **Prompt caching** | YES, optimize after measurement | Repeated exact prefixes can reduce input-token cost and latency. Keep instructions/tools/schema stable and measure cached-token usage; cache hits are not guaranteed. |
| **Batch API** | CONDITIONAL / OFFLINE BULK | Official docs describe a 50% discount for asynchronous requests with a turnaround window up to 24 hours. Use for bulk evals/classification/research preparation, not interactive user-facing steps. |
| **File Search / Vector Stores** | DISABLED for now | Current project matrix says no approved vector-store lifecycle/data-scope controls; SQLite remains controller source of truth. Add only if retrieval needs and access controls are demonstrated. |
| **Embeddings / fine-tuning / moderation / computer use / hosted shell** | NOT REQUIRED FOR FIRST RELEASE | No accepted requirement currently justifies the added cost, scope, or execution risk. Reassess against evidence rather than adding components for their own sake. |

## 4. Cost evidence from the official pricing page

Source: https://developers.openai.com/api/docs/pricing  
The page reports standard prices per 1 million tokens. The following are **public listed prices retrieved on 2026-10-11**, not confirmation that the account can call these model IDs.

| Model | Input / 1M tokens (short context) | Cached input / 1M | Output / 1M | Intended role in a candidate test |
|---|---:|---:|---:|---|
| `gpt-6-luna` | $0.10 | $0.01 | $0.50 | Low-cost routine planning/classification candidate |
| `gpt-6.1-sol` | $2.00 | $0.10 | $10.00 | Higher-complexity planning/code-review comparison |
| `gpt-6-astra` | $10.00 | $1.00 | $50.00 | High-capability complex task/code proposal comparison |

These public prices may vary by context length, model/version and processing mode; confirm the live pricing page before implementation. Model entitlement, account billing status, limits and available budget remain UNKNOWN until checked in the user's authorized project.

### Illustrative token-only cost (not a measured run)

For a hypothetical request using 10,000 uncached input tokens and 2,000 output tokens:

- `gpt-6-luna`: (10,000 × $0.10 + 2,000 × $0.50) / 1,000,000 = **$0.002**
- `gpt-6.1-sol`: (10,000 × $2.00 + 2,000 × $10.00) / 1,000,000 = **$0.04**
- `gpt-6-astra`: (10,000 × $10.00 + 2,000 × $50.00) / 1,000,000 = **$0.20**

This example excludes any separately priced hosted tools, external services, retries, extra planning/tool rounds, and infrastructure. A workflow can cost more than one request because every model round may consume tokens. Never report actual savings without recording a comparable measured baseline.

Official docs state prompt caching is enabled by default for supported models and cached input may be discounted substantially, depending on model. The Batch API docs state 50% lower costs for eligible asynchronous requests. These are optimization opportunities, not proof of savings for our specific workload.

## 5. Low-cost controls to implement or verify

1. **Do deterministic work without an LLM:** required-field checks, state transitions, permission checks, budget caps, hash comparisons, schema checks, test exit codes and read-back comparisons.
2. **Use a model only where language understanding is needed:** plan proposals, ambiguous request interpretation, evidence synthesis, or diagnosis after a concrete failure.
3. **Use a role-based model allowlist:** cheap candidate for routine planning; stronger candidate only for tasks whose acceptance tests justify it. Never silently substitute an unapproved provider.
4. **Use Structured Outputs and strict function schemas:** avoid malformed handoffs and unnecessary retry calls.
5. **Minimize tool rounds and context:** pass the prior stage's curated evidence package, not every raw research result. Re-research only for gaps, stale evidence or conflicts.
6. **Keep stable prefixes:** consistent developer instructions, tool schemas and output schemas can help prompt-cache reuse. Track `usage.input_tokens_details.cached_tokens` and available cache-write fields.
7. **Use Batch only for non-interactive bulk work:** take the documented discount where the 24-hour completion window is acceptable.
8. **Set hard budget/usage limits in the controller:** preflight provider access/quota, estimate request cost, cap rounds/output/context, record actual usage, and block paid calls without explicit approval.
9. **Fallback conservatively:** free-first selection is permitted only when the candidate is actually configured and passes permission/capability/warning/quota checks. A ChatGPT subscription must not be assumed to provide API credits. Account-specific API billing/entitlement has NOT been tested here.
10. **Measure total cost per VERIFIED task:** include planner calls, tool-loop rounds, web/tool fees, failed attempts and verification calls—not just the first model response.

## 6. Existing source inspection

Repository files read from `feature/tr-req-001-tool-router`:

- `docs/OPENAI_CAPABILITY_MATRIX.md` — current capability activation matrix. Its stated statuses are project documentation/source claims, not live-provider proof.
- `docs/OPENAI_ADAPTER_CONTRACT.md` — policy, evidence and independent-verification boundaries.
- `nexus/openai_adapter.py` — Responses API worker, deterministic policy callback before tool execution, bounded tool rounds and usage metadata.
- `nexus/openai_planner.py` — structured plan proposal; paid API call requires budget approval; proposal is not execution authorization.
- `nexus/router.py` — free-first candidate ordering; paid candidates require both permission and budget approval; unknown preflight facts do not pass; unsafe/unclassified failures stop; verification failure stops fallback to avoid duplicate side effects.
- `docs/PROJECT_WORKING_MEMORY.md` — evidence-first, staged handoff, durable audit, checkpoint and status requirements.

Important source-level risk to investigate before implementation: `nexus/openai_planner.py` catches exceptions in `_record()` and silently passes. This conflicts with the Working Memory requirement that mandatory audit-write failures must be surfaced and fail closed. Do not claim this issue is fixed until a patch and tests demonstrate it.

## 7. Verification status and unresolved items

| Item | Status | Evidence / next check |
|---|---|---|
| Official API capability and pricing docs reviewed | VERIFIED — DOC REVIEW | Links listed below; review date 2026-10-11. |
| Existing adapter/planner/router source exists | VERIFIED — SOURCE | Exact branch files were fetched from GitHub. |
| Current account can access listed models | UNKNOWN / NOT RUN | Requires authorized account-level entitlement check. |
| Current account quota and billing limits | UNKNOWN / NOT RUN | Requires authorized account/project settings or a specifically approved live check. |
| Live Responses API request | NOT RUN | No paid/live API call made. |
| Real cost per task and realized savings | NOT RUN | Need approved test dataset, explicit budget, usage records and baseline. |
| ChatGPT Android app/session connected to this repo runtime | NOT VERIFIED | Need a supported client/connector and an end-to-end test; repository code alone does not establish connection. |
| Offline/mock tests for full lifecycle | NOT RUN in this research task | Define test cases and run through existing test suite before any live test. |
| Paid provider calls / service activation / deployment | NOT AUTHORIZED here | Do not run without explicit user approval. |

## 8. Official sources

- Agents runtime comparison: https://developers.openai.com/api/docs/guides/agents
- Responses API reference: https://developers.openai.com/api/docs/api-reference/responses
- Function Calling: https://developers.openai.com/api/docs/guides/function-calling
- Structured Outputs: https://developers.openai.com/api/docs/guides/structured-outputs
- Using tools: https://developers.openai.com/api/docs/guides/tools
- Prompt caching: https://developers.openai.com/api/docs/guides/prompt-caching
- API pricing: https://developers.openai.com/api/docs/pricing
- Evals guide: https://developers.openai.com/api/docs/guides/evals
- Batch API: https://developers.openai.com/api/docs/guides/batch
- Rate limits: https://developers.openai.com/api/docs/guides/rate-limits

## 9. Next permitted work unit

1. Build a requirement-to-stage acceptance checklist and map each check to existing source/test files.
2. Inspect the full failed CI unit-test logs recorded in Working Memory; establish the actual failure cause before unrelated implementation.
3. Add/adjust offline mocks to test: intake validation, evidence handoff, strict schema, free-first route, budget block, policy deny, pre-action durable checkpoint, tool error, unsafe fallback stop, independent verification failure, recovery and final status.
4. Fix the silent mandatory audit-write failure only after a failing test demonstrates the path; verify record read-back.
5. Only after explicit approval and confirmed budget, run a bounded live API test and record actual model, token usage, latency, quota and cost.
