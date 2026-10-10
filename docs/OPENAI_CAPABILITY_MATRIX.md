# NEXUS OpenAI Capability Matrix
Updated: 2026-10-10
Status: source-backed selection and enablement map; not a claim that every capability is available to this account.

## Selection rule
NEXUS composes capabilities by demonstrated task need and compatible contracts—not by a target number of APIs. The Responses API is the provider request boundary; Structured Outputs constrains proposal shape; Function Calling carries tool requests; deterministic NEXUS policy is the only authority that can allow a registered handler. Add further APIs/tools only when their prerequisites, data access, model compatibility, budget, failure behavior and tests are verified.

## Current connection map
`Task → OpenAI Responses API → [Structured Outputs plan OR Function Call proposal] → NEXUS policy + scope check → registered adapter → result verification → audit/operational records`

| Capability | Current status | NEXUS use | Why this disposition |
|---|---|---|---|
| Responses API | ENABLED behind paid budget gate | Model request/response boundary | Current official API surface used by planner and worker. |
| Structured Outputs | ENABLED in planner | Return a typed plan proposal | Schema adherence reduces shape errors; does not verify facts or grant authority. |
| Function Calling | ENABLED in worker | Model requests one of three registered read tools | Application handles calls; NEXUS policy checks before handler execution. |
| Code generation | ENABLED as `/ai/code-proposal` only | Produce allowlisted file-content proposals with `gpt-6-astra` (or reviewed `gpt-6.1-sol`) | Official code-generation guide recommends `gpt-6-astra` for API-based code generation; this endpoint returns proposals only and does not write or execute them. |
| Web Search tool | ENABLED as optional planner capability | Fresh research proposals when explicitly requested | Current GPT-6 model catalog lists web search for GPT-6 Astra, GPT-6.1 Sol and GPT-6 Luna; code checks model compatibility. |
| File Search | DISABLED | Potential retrieval over approved files/vector stores | Requires data scope, vector-store lifecycle, tenant isolation and retrieval-evidence rules first. |
| Code Interpreter | BLOCKED | Potential sandboxed analysis/code execution | The selected model page did not list it among that model's tool capabilities; absence is not universal unavailability, but this project will not enable it without direct compatibility and sandbox verification. |
| Computer Use | DISABLED | Potential UI interaction | No authorized UI/device action adapter, explicit approval model or live mobile test. |
| Shell | DISABLED | Potential code/test execution in a controlled workspace | No sandboxed runner, filesystem/network limits or execution reconciliation are implemented. Never substitute arbitrary shell for a safe code adapter. |
| Apply Patch | DISABLED | Potential code changes to a workspace | Requires workspace binding, patch review, diff validation, idempotency and post-change tests. |
| Embeddings | DISABLED | Potential semantic retrieval | No accepted need; structured SQLite records remain authoritative. |
| Moderation | DISABLED | Potential screening of untrusted public input | Reassess if a concrete requirement appears; not enabled just to increase API count. |
| Image generation | OUT OF SCOPE | Asset creation | No current project requirement. |
| Audio/realtime speech | OUT OF SCOPE | Voice interaction | No current project requirement. |
| Batch | OUT OF SCOPE | Asynchronous bulk work | Current interactive workflow does not need it. |
| Fine-tuning | OUT OF SCOPE | Model customization | No evidence that training a model is necessary. |

## Budget and permission gates
- Every live OpenAI API call is potentially billable. Default behavior is blocked unless the request sets `budget_approved=true` and the deployment operator separately sets `NEXUS_OPENAI_BUDGET_APPROVED=true`.
- The current account's API key, entitlement, quotas and billing are not connected or verified. No live provider call was made during this implementation.
- `NEXUS_OPENAI_MODEL` may override the default, but built-in web search is rejected unless the model is in the explicit compatibility list in `nexus/capabilities.py`.
- Code Interpreter, Computer Use, Shell, and Apply Patch are not enabled for the current release. Code generation is separate from code execution: no workspace write or code runner is connected.
- OpenAI API function tools are read-only and project-scoped in `/ai/run`. MCP exposes a separate set of controller operations; the shared bearer token is not production-grade identity or tenant isolation.

## ChatGPT application path
The official Help Center page retrieved on 2026-10-10 says full MCP support including modify/write actions is rolling out in beta to Business, Enterprise and Edu, with workspace-admin and web availability conditions. The current user's Free plan and Android interface do not establish eligibility. Therefore:
- **ChatGPT mobile MCP integration: BLOCKED / NOT TESTED.**
- **Backend code and contract tests: available; deployment and account registration: NOT DONE.**
- Do not report NEXUS as connected to the ChatGPT app until a real authorized round trip is observed.

## Official source evidence
- Models catalog: https://developers.openai.com/api/docs/models
- Responses API function calling: https://developers.openai.com/api/docs/guides/function-calling
- Structured Outputs: https://developers.openai.com/api/docs/guides/structured-outputs
- Code generation: https://developers.openai.com/api/docs/guides/code-generation
- Tools overview: https://developers.openai.com/api/docs/guides/tools
- ChatGPT developer mode and MCP apps: https://help.openai.com/en/articles/12584461-developer-mode-and-mcp-apps-in-chatgpt
- Retrieval method: live official-page scrape/read on 2026-10-10; claims are limited to the page content. Account-specific API access, quotas and mobile integration remain UNKNOWN/BLOCKED.
