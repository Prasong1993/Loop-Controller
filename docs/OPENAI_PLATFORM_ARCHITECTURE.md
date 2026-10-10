# OpenAI Platform Integration Architecture

**Status:** Implementation contract; the OpenAI API adapter and unit tests exist, but live API execution and ChatGPT account integration are not claimed until explicitly verified.

## Architectural decision

OpenAI is the intelligence and model-execution platform. NEXUS is the deterministic control plane, evidence ledger, project/task memory, approval gate, verification and audit layer. Do not recreate OpenAI model capabilities inside NEXUS, and do not let the model bypass NEXUS policy.

```text
Client (ChatGPT app / web client / approved connector)
             |
             v
OpenAI platform
  Responses API — model response and orchestration
  Function calling — typed requests for external actions
  Structured Outputs — constrained JSON contracts where appropriate
  Web search / File search — research and retrieval tools when suitable
  Code Interpreter — hosted Python analysis in its supported sandbox
  Agents SDK — optional higher-level orchestration, tracing and handoffs
  MCP / Apps SDK — connector surface where the account/platform supports it
             |
             v
NEXUS deterministic controller
  task/project context -> evidence gate -> policy decision -> approval
  -> bounded tool execution -> verification -> audit/checkpoint
             |
             v
Tool adapters and isolated runtime (repository, files, APIs, test runner)
             |
             v
Structured usage/error/evidence/decision/checkpoint/verification records
```

## API capability registry (select by need, not by count)

| OpenAI capability | Best-fit role | NEXUS boundary |
|---|---|---|
| Responses API | Primary model interaction and tool orchestration | Provider adapter; never grants permission by itself |
| Function calling | Ask for a specific registered action with arguments | Validate tool name/schema and run deterministic policy before handler |
| Structured Outputs | Enforce response data shape | Schema validation; valid JSON is not proof that a claim is true |
| Web search tool | Fresh public web research | Store source URL, retrieval time, quote and verifier result; re-fetch before VERIFIED |
| File search | Retrieval over explicitly indexed files | Project scope and access controls must be enforced separately |
| Code Interpreter | Sandboxed Python/data analysis where supported | Not a general shell, unrestricted repository executor, or Android device controller |
| Agents SDK | Optional multi-step orchestration, handoffs, guardrails and tracing | Adopt only if it removes duplication; NEXUS policy remains deterministic |
| MCP / Apps SDK | Connect tools to ChatGPT or compatible clients | Availability depends on account, plan, workspace and interface; test the actual target |
| Audio, image, realtime, embeddings, moderation | Specialized capabilities when a real requirement exists | Add as modular providers only when justified by task evidence |

Do not add 10 or 20 APIs just to increase the count. Use a capability registry with explicit purpose, prerequisites, cost tier, data class, permission, failure policy, version, and tests. Route to the smallest suitable set, prefer eligible free options where available, and require explicit approval for paid-cost actions.

## Tool-call execution invariant

1. Model returns text or a proposed function call.
2. Validate that the tool is declared, registered, schema-valid, and within task scope.
3. Run deterministic NEXUS policy. If it errors, block.
4. Execute only after ALLOW and any required approval.
5. Record usage, decision and outcome without storing secrets/raw sensitive payloads.
6. Verify the result independently and record evidence/checkpoint/audit.
7. On denial, validation error, or ambiguous side effect, do not blindly retry. Reconcile state first.

The initial `nexus/openai_adapter.py` follows this invariant: the model can propose registered function calls, but a deterministic `policy_check` must return ALLOW before the handler runs. The callback that records events is an integration hook; it must be wired to `RecordStore` by the application composition layer for persistent records.

## Code execution distinction

Generating code, analyzing code, and executing code are separate capabilities. The Responses API/Function Calling path can request tools, but actual repository changes and tests require a specifically configured execution adapter/runtime. Code Interpreter is a hosted Python environment for supported analysis tasks; it is not equivalent to an unrestricted shell or control of the Android device. Never execute model-generated code on the host without a sandbox, resource/time limits, filesystem/network policy, and an audit trail.

## ChatGPT mobile compatibility

OpenAI's official help article currently says full MCP apps/developer mode are available on ChatGPT web for Business and Enterprise/Edu, and says MCP apps are not available on mobile. Therefore do not promise custom MCP tools directly inside the Android ChatGPT app without a later official compatibility change and live account-level test. The same NEXUS core can support an API-backed mobile web client and a separately supported ChatGPT integration; these are distinct channels.

## Official sources checked 2026-10-10

- Responses API reference: https://developers.openai.com/api/reference/resources/responses
- Function calling: https://developers.openai.com/api/docs/guides/function-calling
- Structured outputs: https://developers.openai.com/api/docs/guides/structured-outputs
- Code Interpreter: https://developers.openai.com/api/docs/guides/tools-code-interpreter
- MCP tools: https://developers.openai.com/api/docs/guides/tools-connectors-mcp
- Agents: https://developers.openai.com/api/docs/guides/agents
- ChatGPT developer mode and MCP apps: https://help.openai.com/en/articles/12584461-developer-mode-and-mcp-apps-in-chatgpt
- Apps SDK: https://help.openai.com/en/articles/12515353-build-with-the-apps-sdk

## Evidence and limitations

Official documentation establishes the existence and intended roles of these platform capabilities, but does not establish that a particular user's ChatGPT account can register a custom app or that a deployed NEXUS endpoint is live. API use requires a separately configured API key and may incur API charges. Account-specific availability, deployment, production security, and live mobile acceptance remain separate verification gates.
