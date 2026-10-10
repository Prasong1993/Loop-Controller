# NEXUS OpenAI Capability Registry

This registry inventories 17 OpenAI-related capability categories and their dependencies/gates. It is an architectural inventory, **not** a claim that every capability is enabled, available to every account, included in one API request, or free. The router must select only the smallest applicable set for a task.

- Registry: `nexus/openai_capabilities.json`
- Main runtime adapter: `nexus/openai_adapter.py`
- Persistent operational records: `nexus/records.py`
- Design and official source register: `docs/OPENAI_PLATFORM_ARCHITECTURE.md`

## Operating rule

OpenAI is the model and specialized capability provider; NEXUS owns deterministic authorization, project/task state, evidence trust, approval, execution boundaries, verification, and records. API tools are not interchangeable. Use each capability only for its narrow supported role. In particular, hosted Code Interpreter is not the same as repository shell execution; MCP/Apps SDK availability is not equivalent to mobile availability.

Before a capability is enabled in a deployment, its provider documentation, model/account prerequisites, data handling, cost behavior, request limits, error semantics, and acceptance tests must be recorded in the evidence register. Any capability with unknown prerequisites remains disabled.
