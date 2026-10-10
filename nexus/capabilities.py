"""Deterministic allowlist of OpenAI capabilities evaluated for NEXUS.

Statuses are project enablement decisions, not claims that a provider feature is
universally unavailable. Re-enable a capability only after official model/API
compatibility, permissions, runtime, budget, and tests are verified.
"""
from __future__ import annotations

CAPABILITY_REGISTRY = {
    "responses_api": {
        "status": "ENABLED",
        "kind": "api",
        "risk": "provider_request",
        "notes": "Base request/response transport; paid API usage requires budget gate.",
    },
    "structured_outputs": {
        "status": "ENABLED",
        "kind": "response_format",
        "risk": "model_output",
        "notes": "Constrains output shape; does not establish truth or authorize execution.",
    },
    "code_generation": {
        "status": "ENABLED",
        "kind": "responses_structured_output",
        "supported_models": ["gpt-6-astra", "gpt-6.1-sol"],
        "risk": "code_proposal",
        "notes": "Generates allowlisted file-content proposals only; does not write files or execute code."
    },
    "function_calling": {
        "status": "ENABLED",
        "kind": "tool_protocol",
        "risk": "tool_request",
        "notes": "Every requested handler must pass deterministic NEXUS policy.",
    },
    "web_search": {
        "status": "ENABLED",
        "kind": "built_in_tool",
        "tool_type": "web_search",
        "supported_models": ["gpt-6-astra", "gpt-6.1-sol", "gpt-6-luna"],
        "risk": "external_read",
        "notes": "Optional planner research tool; output still requires evidence review.",
    },
    "file_search": {
        "status": "DISABLED",
        "kind": "built_in_tool",
        "risk": "data_access",
        "notes": "Requires verified vector-store/data-scope design and explicit permission tests.",
    },
    "code_interpreter": {
        "status": "BLOCKED",
        "kind": "built_in_tool",
        "risk": "code_execution",
        "notes": "Provider model support is documented; NEXUS execution remains blocked pending sandbox isolation, input/output limits, artifact handling, policy and independent verification tests.",
    },
    "computer_use": {
        "status": "DISABLED",
        "kind": "built_in_tool",
        "risk": "high",
        "notes": "Provider support does not grant control of ChatGPT/mobile devices; no authorized desktop/device adapter or human approval boundary is implemented.",
    },
    "shell": {
        "status": "DISABLED",
        "kind": "execution_tool",
        "risk": "critical",
        "notes": "Requires a separate sandboxed runner, scoped filesystem/network access, and approval gates.",
    },
    "apply_patch": {
        "status": "DISABLED",
        "kind": "code_edit_tool",
        "risk": "write",
        "notes": "Provider support is separate from local activation; requires a workspace-bound patch adapter, diff review, idempotency, rollback and post-edit tests.",
    },
    "image_generation": {
        "status": "OUT_OF_SCOPE",
        "kind": "media_api",
        "risk": "low",
        "notes": "No current NEXUS requirement for generated image assets.",
    },
    "audio": {
        "status": "OUT_OF_SCOPE",
        "kind": "media_api",
        "risk": "low",
        "notes": "No current speech/audio workflow requirement.",
    },
    "embeddings": {
        "status": "DISABLED",
        "kind": "retrieval_api",
        "risk": "data_processing",
        "notes": "No vector-retrieval requirement has been accepted; SQLite records remain authoritative.",
    },
    "moderation": {
        "status": "DISABLED",
        "kind": "safety_api",
        "risk": "data_processing",
        "notes": "Reassess if untrusted public user-generated content becomes in scope.",
    },
    "batch": {
        "status": "OUT_OF_SCOPE",
        "kind": "api",
        "risk": "asynchronous",
        "notes": "Current interactive controller flow does not require batch processing.",
    },
    "fine_tuning": {
        "status": "OUT_OF_SCOPE",
        "kind": "model_customization",
        "risk": "cost_and_data",
        "notes": "No evidence that custom model training is necessary for the controller.",
    },
}

def resolve_optional_tools(capabilities: list[str], model: str) -> list[dict]:
    """Resolve only explicitly enabled capabilities with verified model support."""
    tools = []
    for capability in capabilities:
        spec = CAPABILITY_REGISTRY.get(capability)
        if not spec or spec.get("status") != "ENABLED" or "tool_type" not in spec:
            raise ValueError(f"capability is not enabled: {capability}")
        supported_models = spec.get("supported_models", [])
        if model not in supported_models:
            raise ValueError(f"capability {capability} is not verified for model {model}")
        tools.append({"type": spec["tool_type"]})
    return tools
