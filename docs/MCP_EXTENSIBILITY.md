# Scalable MCP Tool Extensions

## Purpose

NEXUS can expose additional controller-owned MCP tools through a startup-time
extension registry. The built-in tool set remains available; the registry adds
trusted extensions without an arbitrary product-defined maximum count.

## Add an extension

1. Add a Python module to the deployed application package.
2. Export `register_mcp_tools(mcp, track_tool)` from that module.
3. Register each tool with the supplied FastMCP instance and wrap handlers with
   the supplied `track_tool` decorator so tool use and failures remain auditable.
4. Configure `NEXUS_MCP_EXTENSION_MODULES` on the server with comma-separated
   Python module paths, for example `nexus.extensions.documents,nexus.extensions.search`.
5. Run the test suite, review the extension's permissions and side effects, then
   deploy/restart the server. MCP clients discover registered tools through the
   standard `tools/list` mechanism.

The configuration is trusted deployment configuration. Never accept module
names or Python imports from user requests, tool arguments, task text, or remote
client input. Extensions must call the same deterministic controller policy and
must not bypass authentication, evidence gates, audit, or approval requirements.
Do not add arbitrary shell, unrestricted SQL, or unrestricted network access.

## What this does and does not remove

- Removes an arbitrary fixed count ceiling from the extension loader.
- Enables adding integration tools as reviewed server-side modules without
  editing the central MCP server for every extension.
- Does not create tools automatically, grant permissions, or bypass policy.
- Does not remove provider/API quotas, rate limits, plan restrictions, hosting
  capacity, memory/CPU limits, network constraints, or third-party service limits.
- Extension code is loaded at startup. Updating a package/repository does not
  affect the live endpoint until the owning deployment is updated and restarted.
- A configured extension that fails to import or register prevents startup rather
  than silently presenting a partial tool catalog.

## Verification status

The extension loader has unit tests for empty configuration, multiple extensions,
duplicate configuration, missing entrypoints, and import failure. Repository CI
must pass before this change is considered validated. Live MCP discovery and
production deployment remain separate acceptance gates.
