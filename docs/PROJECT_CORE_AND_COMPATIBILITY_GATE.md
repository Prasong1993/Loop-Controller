# Project Core and Compatibility Gate

Updated: 2026-10-10
Status: required architecture and release gate

## Primary core

OpenAI is the project's primary AI core. The OpenAI Responses API is the repository's model boundary for planning, structured proposals, and function/tool-call requests. NEXUS is the deterministic control plane around that core; it is not a competing AI model orchestrator.

The ChatGPT app conversation and the OpenAI API are different execution surfaces. The existence of this ChatGPT session does not itself give repository code a callable API to this session. API calls require a supported OpenAI API integration, configured credentials, budget approval, and end-to-end tests. Mark ChatGPT/MCP integration live only after a real invocation is verified.

Every work item should be traceable through project_id, task_id, trace_id, and operation_id where available. For OpenAI operations, retain capability, model identifier, provider response/request identifier, and usage metadata when actually returned and safe to store. Missing metadata must be UNKNOWN/NOT_AVAILABLE, never guessed. Never store API keys, raw prompts, private user content, or full model outputs in operational logs.

## Component boundaries

- OpenAI Responses API worker/planner: primary model and function-call boundary.
- Capability registry: deterministic allowlist of approved OpenAI capabilities and project enablement state.
- NEXUS core: deterministic state transitions, permissions, evidence acceptance, checkpoints, and audit.
- Tool Router: routes approved tool operations; it must not silently replace OpenAI with an unrelated AI provider. Any alternate AI provider requires a separately approved architecture change and compatibility review.
- REST and MCP adapters: transports into the same core and operational record store, not separate policy engines.
- Operational Record Store: searchable, redacted run, usage, error, decision, evidence, checkpoint, and verification records.
- Tests and CI: prove declared contracts; they do not prove live API access or Android ChatGPT registration unless those flows are actually exercised.

## Project-wide compatibility gate

Before a change is considered complete, inspect and test the integration edges affected by it:

1. Imports, public interfaces, data models, and dependency/version constraints.
2. OpenAI capability registry, supported model IDs, Responses API request/response handling, function-call schema, and budget/permission gates.
3. REST and MCP contracts, authentication, request IDs, and trace propagation.
4. NEXUS task state machine, checkpoint/restore behavior, audit log, and SQLite schema.
5. Operational Record Store schema, redaction rules, search/readback, and linkage from route events to project/task/trace.
6. OpenAPI schema and any public API contract tests.
7. Unit, integration, regression, and CI tests across the supported Python versions.
8. Explicitly classify live provider, deployment, and ChatGPT mobile integration as VERIFIED, UNKNOWN, or BLOCKED based on actual evidence.

A local unit-test pass is not a project-wide compatibility pass. Do not merge while a known contract mismatch remains. Fix and re-run affected tests until they pass, or report the exact blocked gate and evidence.

## Evidence rule

Use VERIFIED only for facts supported by current source inspection or completed tests. Use UNKNOWN when no proof is available, RECOVERED for facts restored from prior records, and BLOCKED when a required dependency or approval prevents validation. Link important decisions and test results to the code/tests they govern.
