# NEXUS Quickstart — Local and Cloud-Ready Package

## Included

- Deterministic Python/SQLite controller and FastAPI API.
- OpenAI Responses API adapter for structured planning, proposal-only code generation, and allowlisted read-only tool orchestration.
- Remote MCP server with a server-admin extension registry.
- OpenAI Responses API read-only function-tool extensions configured through NEXUS_OPENAI_EXTENSION_MODULES.
- NASA-style gate-readiness checklist and tests.

This repository does not include an OpenAI API key, hosted service, registered ChatGPT app, or unlimited API usage. Configure your own credentials and deployment secrets.

## Run locally with Docker Compose

Prerequisites: Docker Engine and Docker Compose v2.

1. Copy .env.example to .env.
2. Set NEXUS_API_KEY to a long random secret. Keep .env out of version control.
3. Set OPENAI_API_KEY only if you intend to call the paid OpenAI API. Keep NEXUS_OPENAI_BUDGET_APPROVED=false until you deliberately authorize API spending.
4. Start the API and MCP service:

~~~sh
docker compose up --build -d
docker compose logs -f
~~~

Ports are bound to loopback only:
- REST API: http://127.0.0.1:8000
- MCP Streamable HTTP: http://127.0.0.1:8001/mcp
- Health: http://127.0.0.1:8000/health

Data persists in the named Docker volume nexus_data. The API and MCP processes share the same SQLite files. This is for single-instance evaluation/development, not high-availability or multi-tenant production.

## Verify before use

~~~sh
curl http://127.0.0.1:8000/health
curl -H "Authorization: Bearer $NEXUS_API_KEY" http://127.0.0.1:8000/openapi.json
~~~

Never paste tokens into chat, commit them, embed them in mobile-client code, or include them in logs/screenshots.

## OpenAI API activation

Trusted read-only tool modules can be added to the Responses API path through NEXUS_OPENAI_EXTENSION_MODULES; see docs/OPENAI_TOOL_EXTENSIONS.md. Modules are server-admin configuration, not user input. Write/execute tools remain disabled on /ai/run.


Paid OpenAI calls require both request-level budget_approved=true and server-level NEXUS_OPENAI_BUDGET_APPROVED=true. Both gates apply to /ai/plan, /ai/code-proposal, and /ai/run. Model availability and cost depend on your OpenAI Platform project; verify NEXUS_OPENAI_MODEL in your own account.

The /ai/run endpoint currently exposes project-scoped read-only tools. Code proposals are returned for review; they are not written to the repository or executed.

## Connect a remote MCP client

Deploy nexus.mcp_server:app behind HTTPS and set NEXUS_API_KEY in the server secret store. Configure a compatible client with the HTTPS MCP endpoint and bearer authentication only where supported. The Compose endpoint is local HTTP and must not be exposed directly to the public internet.

Availability of custom MCP apps inside ChatGPT depends on OpenAI's current plan, workspace, and client support. The Responses API remote MCP path is separate from registering a custom app inside ChatGPT. Confirm both through current official documentation and a live test.

## Production blockers

Before public production use:
1. Replace shared bearer-token prototype auth with reviewed OAuth/identity and tenant isolation.
2. Configure HTTPS termination, secret management, rate limits, and monitoring.
3. Verify persistence, backup/restore, concurrency, retention, and rollback.
4. Run security tests and a live integration round trip, including denial and audit readback.
5. Review gate evidence. A checklist result is not formal gate approval.

This package makes the repository runnable; it does not by itself make an unreviewed public deployment safe or claim NASA certification.
