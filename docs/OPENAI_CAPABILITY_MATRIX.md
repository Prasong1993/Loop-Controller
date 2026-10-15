# OpenAI Capability Matrix
Updated: 2026-10-10
Status: project-specific activation matrix; official provider support is distinct from NEXUS implementation readiness.

## Decision rule

NEXUS uses OpenAI's Responses API as the model/agent boundary. It does **not** enable every provider feature merely because the API offers it. A capability can be:

- **ENABLED** — the project has a narrow implementation and local tests for its declared contract.
- **DISABLED** — available in principle, but not enabled because required scope, policy, adapter, or tests are missing.
- **BLOCKED** — the capability is a candidate but a required safety/runtime condition is not yet met.
- **OUT_OF_SCOPE** — no accepted first-release requirement justifies enabling it.

The deterministic registry is `nexus/capabilities.py`. OpenAI is the primary AI core for this project; the architecture and required project-wide integration checks are defined in [Project Core and Compatibility Gate](PROJECT_CORE_AND_COMPATIBILITY_GATE.md). Model text, structured output, a tool call, or a provider's “success” response never replaces NEXUS policy and independent verification.

## Provider and project activation matrix

| OpenAI capability | Official/API role | NEXUS status | Current implementation / reason |
|---|---|---|---|
| Responses API | Primary request/response API; supports built-in tools and function calling | ENABLED | `nexus/openai_adapter.py`, `nexus/openai_planner.py`, `nexus/code_proposal.py`; outbound paid calls require server + request approval. |
| Structured Outputs | Constrains model response to a JSON schema | ENABLED | Used for plan and code proposals. Schema validity is not truth, permission or test evidence. |
| Function Calling | Model emits a request for an application-defined function | ENABLED | Three read-only NEXUS handlers are exposed through `/ai/run`; policy and project scope are checked before handler execution. |
| Code generation | Generates code text/file proposals | ENABLED — proposal only | `POST /ai/code-proposal`; explicit allowed paths, code-model allowlist, task/project checks, double budget gate. Does not write files, apply patches, or execute code. |
| Web search tool | Hosted retrieval/search inside Responses API | ENABLED as an optional planner tool | Enabled only for model IDs listed in the central registry. Search output is candidate evidence; NEXUS source verification remains separate. |
| File search tool | Hosted retrieval over configured vector stores | DISABLED | No approved vector-store lifecycle, access-control design, or data-scope tests. SQLite remains the controller's source of truth. |
| Code Interpreter | Hosted sandboxed Python execution tool | BLOCKED for NEXUS execution | OpenAI model catalog lists it as provider-supported for the current flagship models, but NEXUS has not verified the complete execution policy, sandbox isolation, input/output limits, artifact handling, and independent result-verification contract. |
| Computer use | Model-guided computer interaction tool | DISABLED | No authorized desktop/device adapter or human-approval boundary. This does not control the user's ChatGPT Android app or bypass its platform permissions. |
| Hosted shell | Provider-hosted shell tool | DISABLED | No accepted command allowlist, filesystem/network boundary, approval contract, or side-effect reconciliation tests. |
| Apply patch | Provider-supported patch proposal/application workflow | DISABLED | No workspace-bound patch adapter, diff review, idempotency, rollback and post-edit test contract. Code proposal generation is not patch application. |
| MCP tool connection | Connects the model/API to registered remote MCP servers | NOT YET LIVE | NEXUS has a Streamable HTTP MCP server and bearer-token prototype gate. No verified public deployment, OAuth setup, ChatGPT app registration, or successful Android/mobile invocation. |
| Embeddings | Vector representations for retrieval | DISABLED | No accepted vector-retrieval requirement; do not add a vector database just to increase component count. |
| Moderation | Safety classification API | DISABLED | No demonstrated requirement in the current private controller scope. Reassess if untrusted public user content enters scope; it does not replace deterministic policy. |
| Image generation/editing | Image/media generation | OUT_OF_SCOPE | No current controller requirement for generated image assets. |
| Audio/realtime | Speech, transcription, realtime sessions | OUT_OF_SCOPE | No current controller requirement for audio. |
| Batch | Asynchronous large-scale requests | OUT_OF_SCOPE | Current workflow is interactive; reassess only if queued bulk processing becomes a requirement. |
| Fine-tuning | Model customization | OUT_OF_SCOPE | No evidence that training is needed; first use model selection, structured contracts, evidence, tools and evaluation. |

## Model routing

The current defaults are selected for distinct roles, not because more model IDs automatically make the system better:

| Role | Model ID | Selection reason | Guard |
|---|---|---|---|
| General plan / tool orchestration | `gpt-6-luna` | Official catalog describes it as cost-sensitive/high-volume | Paid API gate; actual account entitlement still untested. |
| Code proposal | `gpt-6-astra` | Official catalog describes it as the flagship model for complex reasoning and coding | Explicit path allowlist, approved model registry, double budget gate; proposal only. |
| Reviewed code alternative | `gpt-6.1-sol` | Official catalog describes it as a lower-cost alternative for complex work | Only enabled in the code-proposal allowlist; proposal only. |

Do not hardcode price or quota as guaranteed account entitlement. Public catalog prices/limits can change, and account tier, project spend limits and actual model access must be checked before live provider use.

## Connection map

```text
ChatGPT / API client
        │ (a supported connector or client; not yet registered live)
        ▼
NEXUS REST API / Streamable HTTP MCP adapter
        │ authenticate + validate scope + trace
        ▼
Deterministic NEXUS core ───────► Evidence verifier
        │                          HTTPS allowlist + pinned IP + quote match
        ├────► OpenAI Responses planner ───► structured plan proposal
        ├────► OpenAI code generator ─────► allowlisted code proposal
        └────► OpenAI read-only function tools
                    │
                    ▼
          deterministic policy + budget gate
                    │
          only allowlisted handlers proceed
                    ▼
       observed result → verification → audit/records
                    │
          checkpoint / recovery / completion
```

## Official source evidence (checked 2026-10-10)

- Model catalog: https://developers.openai.com/api/docs/models
- GPT-6 Astra: https://developers.openai.com/api/docs/models/gpt-6-astra
- GPT-6.1 Sol: https://developers.openai.com/api/docs/models/gpt-6.1-sol
- GPT-6 Luna: https://developers.openai.com/api/docs/models/gpt-6-luna
- Responses API: https://developers.openai.com/api/docs/api-reference/responses
- Function calling: https://developers.openai.com/api/docs/guides/function-calling
- Structured Outputs: https://developers.openai.com/api/docs/guides/structured-outputs
- Code generation: https://developers.openai.com/api/docs/guides/code-generation
- Built-in tools: https://developers.openai.com/api/docs/guides/tools
- Code Interpreter: https://developers.openai.com/api/docs/guides/tools-code-interpreter
- MCP: https://developers.openai.com/api/docs/guides/tools-connectors-mcp

## Reference-use boundary

Anchor's archived project records were consulted for ideas such as requirements-to-test traceability, explicit status labels, recovery/idempotency, redacted operational logs, and read-back after writes. They are reference material only: NEXUS retains its own scope, state machine, code, schemas, and acceptance criteria; no wholesale copy of the Anchor workflow or architecture is authorized.

## Release blockers

- Live OpenAI provider request and account/model entitlement: NOT RUN.
- Secure deployment, production identity/tenant isolation, rate limits, key rotation, retention and tamper-evident audit: NOT COMPLETE.
- Workspace write/patch or code execution: NOT IMPLEMENTED.
- ChatGPT app registration and Android/mobile end-to-end invocation: NOT CONFIGURED / NOT TESTED.
- Current CI verifies code contracts and unit/regression tests only; it is not a remote production smoke test.
