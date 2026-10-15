# OpenAI Responses API Tool Extensions

## Purpose

OpenAI Responses API is the model/orchestration interface. NEXUS remains the deterministic controller. Trusted extension modules may add project-scoped, read-only function tools to the OpenAI tool list used by the existing /ai/run route.

## Register an extension

1. Add a reviewed Python module to the server package.
2. Export register_openai_tools(registry).
3. Register a strict function tool with a project_id string property and no undeclared properties.
4. Pass a read-only handler that returns data only for the active project.
5. Configure NEXUS_OPENAI_EXTENSION_MODULES as a comma-separated list of trusted module paths.
6. Run tests, review the module's data access, and restart the server.

Example shape (pseudocode):

~~~python
def register_openai_tools(registry):
    registry.register(
        {
            "type": "function",
            "name": "read_project_documents",
            "description": "Read indexed documents for the active project",
            "parameters": {
                "type": "object",
                "properties": {"project_id": {"type": "string"}},
                "required": ["project_id"],
                "additionalProperties": False,
            },
            "strict": True,
        },
        handler=read_project_documents,
        risk="read",
    )
~~~

The handler must enforce its own record-level/project-level access restrictions as well. The API wrapper rejects arguments whose project_id differs from the active project and applies the same deterministic policy callback before invoking the handler.

## Safety and scope

- Only server-admin configured Python modules are imported. Never accept module names from model output, HTTP requests, task text, or users.
- Only risk="read" is enabled on /ai/run. Write/execute/external-side-effect tools are rejected by the registry until a separately reviewed approval and idempotency contract exists.
- A schema-valid function call is not proof of permission or truth. NEXUS policy still runs before each handler.
- Extension code is trusted executable code, not a sandbox. Review dependencies, network access, data scope and audit behavior before enabling it.
- Module count has no arbitrary product-defined cap, but API rate limits, tokens, hosting resources, latency and cost still apply.
- This registry is separate from MCP extensions; an extension must explicitly register for each protocol it supports.

## OpenAI platform references

- Responses API tools and remote MCP: https://developers.openai.com/api/docs/guides/tools-connectors-mcp
- Function calling: https://developers.openai.com/api/docs/guides/function-calling
