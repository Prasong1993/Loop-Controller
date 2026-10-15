# NASA-style Review Gates for NEXUS

**Status:** Implemented readiness checklist; formal approvals and operational evidence are not yet integrated into a durable gate ledger.

This is an adaptation of systems-engineering review practices described by NASA, not a NASA-mandated software lifecycle, endorsement, or certification. Tailor review depth to project risk.

## Review sequence

| Gate | Purpose | Readiness evidence examples |
|---|---|---|
| SRR — System Requirements Review | Baseline scope, requirements, acceptance, initial risks | Requirement IDs, exclusions, acceptance tests, risk register |
| SFR — System Functional Review | Confirm workflows and functional coverage | Workflow map, policy boundary, evidence flow, recovery cases |
| PDR — Preliminary Design Review | Review architecture and interfaces | Architecture, API/MCP schemas, identity and data-scope design, capability registry |
| CDR — Critical Design Review | Confirm implementation and traceability | Code, policy tests, requirement-to-test matrix, secrets review |
| TRR — Test Readiness Review | Confirm test environment and procedures | CI run, integration fixtures, failure scenarios, evidence capture |
| ORR — Operational Readiness Review | Confirm production safeguards | Auth/TLS, durable storage, backup/restore, monitoring, rollback |
| AR — Acceptance Review | Confirm the delivered user outcome | Live round trip, denial test, audit readback, acceptance result |

The sequence is a project-level adaptation. A project may tailor or omit reviews only through a documented decision and risk rationale. The current implementation requires the immediately preceding gate to be marked APPROVED before a later gate can be marked READY_FOR_REVIEW.

## Deterministic readiness tools

The MCP tools nexus_list_review_gates and nexus_review_gate_readiness expose the gate catalogue and checklist evaluator.

For each criterion, submit its exact criterion_id, status=VERIFIED only when checked, a stable evidence_ref, and a verification_method. Supply predecessor statuses as objects such as {"gate_id":"SRR","status":"APPROVED"}. Missing predecessor approval, unknown/missing evidence, or missing verification method blocks readiness.

**Safety boundary:** the evaluator returns READY_FOR_REVIEW, never APPROVED. It checks submitted metadata but does not fetch/authenticate the cited artifact, validate that a CI URL passed, or record a durable reviewer signature. An authorized reviewer must independently inspect the evidence and record approval in the controlled review record. Model/user-supplied labels are not proof by themselves.

## OpenAI's role

OpenAI Responses API is the reasoning/planning layer. Structured plans and model-generated statements are proposals, not evidence and not approvals. NEXUS policy, verification tests, and audit remain authoritative. Enable additional OpenAI API capabilities only after official compatibility, account entitlement, cost, permissions, and tests are checked.

## Official references

- NASA Systems Engineering Handbook (NASA/SP-2016-6105 Rev 2): https://www.nasa.gov/wp-content/uploads/2018/09/nasa_systems_engineering_handbook_0.pdf
- NASA Systems Engineering Handbook appendix: https://www.nasa.gov/reference/system-engineering-handbook-appendix/
- OpenAI Responses API remote MCP tools: https://developers.openai.com/api/docs/guides/tools-connectors-mcp
- OpenAI function calling: https://developers.openai.com/api/docs/guides/function-calling

## Acceptance status

Unit tests cover ordering, missing/unknown evidence, predecessor blocking, duplicate inputs, and no-auto-approval. They do not prove deployed integration. Production identity/tenant isolation, durable gate approval ledger, live OpenAI requests, and end-to-end client acceptance remain separate gates.
