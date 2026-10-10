# OpenAI Adapter Contract: Data In, Model Work, Data Out

Updated: 2026-10-10
Status: required architecture contract; runtime claims remain evidence-based

## Purpose

OpenAI is the primary AI core. An OpenAI adapter is the controlled integration boundary between NEXUS/workspace capabilities and OpenAI APIs. It is not a second AI, a generic unrestricted file writer, or a claim that the ChatGPT mobile app session is directly callable from repository code.

## Adapter responsibilities

1. **Capability discovery and registration**: expose only project-approved OpenAI API capabilities and model/tool combinations. The capability registry describes project enablement; official provider support and live account access must be verified separately.
2. **Data in**: retrieve only the task context, evidence, records, and workspace data that the caller is authorized to access through a real registered connector. Record source component, source record/reference, timestamp/version when available, and access decision. Do not assume the OpenAI API can browse private ChatGPT app data or the user's workspace without a connected tool/API.
3. **Request mapping**: translate approved context into a supported OpenAI API request; validate schema, model/capability compatibility, project/task scope, permission, budget, and data minimization before sending.
4. **Model processing**: send the request to the selected OpenAI API. Capture only metadata actually returned and safe to persist: model, capability, response/request ID, token usage, round, and result status. Never store API keys, raw private prompts, raw tool arguments, or full outputs in the operational ledger.
5. **Tool requests**: treat function calls as proposals. Resolve the call to an allowlisted handler and run deterministic NEXUS policy before execution. Unknown, cross-project, unauthorized, malformed, or unverified requests fail closed.
6. **Data out / workspace writes**: write only through registered destination adapters with explicit operation schemas and permissions. Before a mutation, persist an intent/checkpoint; after it, read back the destination and verify the expected result. Record destination, operation, redacted result reference/hash where appropriate, and verification status. Do not retry a possibly completed non-idempotent write unless its safety is established.
7. **Provenance and trace**: link source read, OpenAI request/response, policy decision, tool operation, destination write, checkpoint, error, and verification with project_id, task_id, trace_id, and operation_id where available. Unknown fields remain UNKNOWN; never fabricate identifiers or evidence.
8. **Error handling**: persist API failures, policy blocks, tool failures, and verification failures. If mandatory audit/checkpoint persistence fails, stop before the next stage and return a visible failure; never silently continue as though the action were audited.
9. **Compatibility**: each adapter must implement the declared input/output contract and have unit plus integration tests. Changes to a provider capability require updates to the capability matrix, schemas, adapter tests, API/MCP contracts, and project-wide regression checks.

## Required end-to-end trace

`authorized source -> source evidence record -> OpenAI request metadata -> OpenAI response metadata -> policy decision -> registered tool/destination operation -> durable checkpoint -> destination read-back -> verification record`

For read-only operations, the destination is the returned authorized data and no workspace mutation is implied. For writes, a successful API response alone is insufficient: destination read-back and verification are required.

## Current repository boundary

- `nexus/openai_adapter.py`: Responses API worker and deterministic tool gating.
- `nexus/capabilities.py`: project capability allowlist.
- `nexus/records.py`: append-only redacted operational record store.
- `nexus/core.py`: deterministic state, audit, and checkpoints.
- `nexus/router.py` and `nexus/runlog.py`: route execution and durable per-round history.
- `nexus/api.py` and `nexus/mcp_server.py`: REST/MCP entry points and tool exposure.

The current `/ai/run` tool set is read-only (project status, audit, and task reads). A workspace-write adapter is not considered available merely because the architecture describes it; it must be implemented, allowlisted, and tested against an actual authorized destination before being marked VERIFIED.

## Status vocabulary

- VERIFIED: source or completed test demonstrates the behavior.
- RECOVERED: reconstructed from a prior recorded artifact, not re-proven in the current run.
- UNKNOWN: no sufficient evidence yet.
- BLOCKED: a required credential, integration, permission, approval, or test is missing.
