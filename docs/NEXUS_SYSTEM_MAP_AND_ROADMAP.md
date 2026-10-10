# NEXUS System Map and Implementation Roadmap

- Revision: 1.0
- Updated: 2026-10-10
- Status: controlling architecture map; implementation must follow dependency order below.
- Evidence policy: link each implementation item to official documentation, a code location, and a test. Unknown capability is not treated as verified.

## 1. Architecture principle

NEXUS is the control plane; OpenAI provides model and specialized capabilities. Do not treat NEXUS as a replacement for OpenAI models or recreate OpenAI services unnecessarily. Do not indiscriminately chain every API. Select capability adapters from the task's needs, then route all proposed actions through deterministic NEXUS policy and verification.

```text
User / ChatGPT mobile or NEXUS web client
                  |
                  v
        Task Intake + Identity/Trace
                  |
                  v
        OpenAI Capability Orchestrator
        |        |         |         |
        |        |         |         +-- Code/sandbox adapter (only if required)
        |        |         +------------ Retrieval / web research adapter
        |        +---------------------- Structured output + function calling
        +------------------------------- Responses/model reasoning
                  |
                  v
        NEXUS Deterministic Control Plane
        INTAKE -> RESEARCH -> PLAN -> POLICY -> EXECUTE -> VERIFY -> AUDIT -> COMPLETE
                         |          |                |
                         |          |                +-- stop/reconcile ambiguous effects
                         |          +-- allow/block; budget/permission/phase gates
                         +-- trusted evidence provenance; VERIFIED/RECOVERED/UNKNOWN/BLOCKED
                  |
                  v
        Capability adapters / MCP tools / approved external systems
                  |
                  v
        Result verifier + evidence-linked audit
                  |
                  v
        Append-only Record Store + Checkpoints + Search/Recovery
```

NEXUS policy/verification must remain deterministic and must not ask an LLM to decide whether policy passed. Model outputs are proposals, never authority to bypass gates. API keys stay server-side. Code execution requires a sandbox/runtime and explicit file/network/process limits; a model's code-generation capability is not itself permission to execute on a user's Android device.

## 2. OpenAI capability map (select by need; not all APIs are always called)

| Capability family | Purpose in NEXUS | Adapter contract / gate | Evidence |
|---|---|---|---|
| Responses API + selected model | Primary model interaction; text/code planning and multimodal input where supported | Input context is task-scoped; persist response ID/model/usage metadata, not secrets; output does not bypass policy | https://platform.openai.com/docs/api-reference/responses |
| Function/tool calling | Model proposes typed operations to NEXUS or approved tools | Strict allowlist, JSON schema validation, idempotency and policy gate before execution | https://platform.openai.com/docs/guides/function-calling |
| Structured Outputs | Machine-validated plan, route proposal, result envelope | Schema validation is a format check, not authorization or factual verification | https://platform.openai.com/docs/guides/structured-outputs |
| Built-in web search | Current public research when enabled for the selected model/API | Store URL, retrieved timestamp, quote/hash, source limitations; do not auto-promote unverified claims | https://platform.openai.com/docs/guides/tools-web-search |
| File search / retrieval | Search approved project documents and indexed knowledge | Project/tenant scope, source IDs and snippets recorded; stale files identified | https://platform.openai.com/docs/guides/tools-file-search |
| Code Interpreter | Sandboxed Python data/file/code analysis where appropriate | Isolated hosted environment; do not assume access to Android/local files or arbitrary system control | https://platform.openai.com/docs/guides/tools-code-interpreter |
| Remote MCP tools | Connect to approved external systems through a standard tool contract | Server allowlist, auth, tool schemas, per-tool permissions, trace and failure capture | https://platform.openai.com/docs/guides/tools-connectors-mcp |
| Agents SDK / agent workflows | Optional orchestration, handoffs, tracing, guardrails if complexity justifies it | Never duplicate NEXUS's deterministic gates; adopt only after lifecycle/security tests | https://platform.openai.com/docs/guides/agents-sdk |
| Image generation | Generate visual assets when task asks for images | Asset policy, prompt metadata and artifact reference recorded | https://platform.openai.com/docs/guides/image-generation |
| Audio / speech | Voice input/output only if required | Consent/privacy and transcript/audio retention controls | https://platform.openai.com/docs/guides/audio |
| Realtime | Low-latency live audio or multimodal session when needed | Separate session lifecycle and budget/rate limits | https://platform.openai.com/docs/guides/realtime |
| Embeddings | Semantic retrieval/ranking if keyword search is insufficient | Versioned model/dimensions; project-scoped index and deletion policy | https://platform.openai.com/docs/guides/embeddings |
| Moderation | Input/output risk signal where applicable | Treat as a safety signal, not as a substitute for NEXUS authorization | https://platform.openai.com/docs/guides/moderation |
| Batch API | Deferred bulk processing, not interactive critical control | Batch outputs must re-enter verification; no direct state mutation | https://platform.openai.com/docs/guides/batch |
| Fine-tuning | Consider only after evaluation proves a stable repeated behavior gap | Not an MVP dependency; dataset governance and evals required | https://platform.openai.com/docs/guides/fine-tuning |
| Evals | Regression/effectiveness measurement for model-dependent tasks | Version test sets; deterministic gate tests remain separate | https://platform.openai.com/docs/guides/evals |

The table is a capability inventory, not a promise that every item is available on every plan, model, endpoint, or region. Confirm exact current schemas, model support, limits, and costs before enabling each adapter. Prefer the smallest set that passes acceptance tests; scale toward more adapters only when evidence shows value.

## 3. Cross-module contracts

1. **Task contract:** task ID, project ID, session/trace ID, goal, constraints, requested outputs, risk class, budget ceiling, approval references.
2. **Plan contract:** schema-validated ordered steps; each step states inputs, expected output, tool/capability, side-effect class, evidence prerequisites, verification rule, rollback/reconciliation method.
3. **Policy contract:** deterministic ALLOW/BLOCK plus stable reason code, policy version, applicable rules, approval reference. No tool executes on a missing/invalid decision.
4. **Evidence contract:** trusted fetch provenance; URL, publisher, retrieval timestamp, source revision if available, exact quote/hash, verification method, limitations, linked requirement/test. Caller-supplied text alone cannot qualify as fetched VERIFIED evidence.
5. **Tool contract:** typed request/response, allowlisted capability, timeout/size limits, idempotency behavior, trace propagation, redacted summary, stable errors.
6. **Verification contract:** expected vs observed, method, verifier version, result, test run/reference. Static inspection, unit tests, integration tests, and live platform tests are distinct.
7. **Record contract:** every request/action/decision/failure/checkpoint/verification automatically appends a searchable event; records link by project/task/trace/operation IDs.
8. **Recovery contract:** classify failure before retry; policy denial is not retryable; ambiguous side effects must be reconciled before another execution.
9. **Client contract:** mobile client uses a supported integration or a responsive web client. Do not promise custom MCP write actions inside ChatGPT mobile until current official support and account-specific live test confirm it.

## 4. Evidence and current platform boundary

Official OpenAI documentation confirms Responses API, function calling, structured outputs, code interpreter, and remote MCP as distinct capability families. They have complementary roles, but their use depends on task and model support. OpenAI's current help page for developer mode/full MCP apps states availability is for Business/Enterprise/Edu on ChatGPT web and that MCP apps are not available on mobile. Therefore, an Android-first ChatGPT-app path cannot assume that a custom full-MCP write-enabled app will work inside the native mobile app. Treat that route as BLOCKED pending a current official change or successful account-specific test. A separate mobile-friendly NEXUS web client backed by OpenAI API is the fallback path; it must not be confused with an in-app ChatGPT integration.

Official sources retrieved 2026-10-10:
- Responses API: https://platform.openai.com/docs/api-reference/responses
- Function calling: https://platform.openai.com/docs/guides/function-calling
- Structured Outputs: https://platform.openai.com/docs/guides/structured-outputs
- Code Interpreter: https://platform.openai.com/docs/guides/tools-code-interpreter
- Remote MCP: https://platform.openai.com/docs/guides/tools-connectors-mcp
- Agents SDK: https://platform.openai.com/docs/guides/agents-sdk
- ChatGPT developer mode/MCP mobile availability: https://help.openai.com/en/articles/12584461-developer-mode-and-mcp-apps-in-chatgpt

## 5. Roadmap / gates (must be completed in order)

### R0 — Map and evidence
- Keep this map current before code changes.
- Build a source-to-requirement-to-module-to-test traceability table.
- Mark each fact VERIFIED / RECOVERED / UNKNOWN / BLOCKED.
- Gate: no code begins while a critical dependency or interface is unknown.

### R1 — Record/data foundation
- Review existing SQLite schema and migrations before adding new tables.
- Normalize operational usage, errors, evidence, decisions, checkpoints and verification records; append-only history.
- Add stable IDs, UTC timestamps, schema versions, trace/operation correlation, redaction, bounded pagination and indexed search.
- Gate: migration preserves existing state; searches return reproducible, scoped results.

### R2 — Core contracts and safety
- Centralize policy/error codes and versioning.
- Bind evidence fetch and provenance verification to trusted core boundaries; harden DNS/IP/TLS behavior.
- Add idempotency and concurrency/revision guards; never replay ambiguous side effects.
- Gate: negative/security tests pass and REST/MCP behavior matches.

### R3 — OpenAI capability adapters
- Start with Responses + structured outputs + function calling, with server-side secrets and explicit budgets.
- Add built-in web/file search or Code Interpreter only when task acceptance requires it.
- Add MCP/other capability adapters behind the same tool contract; avoid duplicate services.
- Gate: mocked contract tests, failure/timeout tests, cost-limit tests, no unauthorized side effect.

### R4 — Full lifecycle integration
- Test intake → research → plan → policy → execution → verification → audit → completion, including recovery/blocked paths.
- Check REST/MCP/API schemas, trace links, idempotency, concurrent requests and database migrations.
- Gate: end-to-end acceptance matrix passes on supported Python versions.

### R5 — Deployment and mobile
- Harden auth/tenant isolation/rate limits/TLS/secrets/backup/retention/monitoring.
- Deploy a test endpoint only after security review.
- Verify ChatGPT registration and mobile access against official product constraints; otherwise test the mobile web client path.
- Gate: live end-to-end mobile test is documented; no claim of ready-to-deploy until it passes.

## 6. Completion reporting rules

The final report must state commit IDs and links, tests actually executed and their results, unresolved blockers, and whether live mobile access was tested. Do not label planned work as complete. If a gate cannot be passed in the available environment, record the exact blocker and stop claiming overall completion.

## 7. Work rule

For every new work session or material change, update/read this map first, inspect all linked dependencies, change the map if interfaces or sequence change, implement, run tests, and update the record/evidence register. Report consolidated results after the work batch rather than sending progress chatter, except when a required user approval is genuinely unavoidable.
