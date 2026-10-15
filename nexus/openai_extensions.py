"""Trusted server-configured read-only tool extensions for OpenAI Responses API.

Only deployment administrators may configure modules. Extensions are trusted
Python code; the registry validates their schema and project-scope contract but
is not a sandbox. Side-effecting tools are deliberately rejected by this path.
"""
from __future__ import annotations
import importlib
import os
import re
from collections.abc import Iterable
from copy import deepcopy
from typing import Any, Callable

BUILTIN_TOOL_NAMES = {"nexus_get_project_status", "nexus_read_audit", "nexus_get_task"}
_TOOL_NAME = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

class OpenAIToolRegistry:
    def __init__(self, reserved_names: Iterable[str] = ()):
        self.tools: list[dict[str, Any]] = []
        self.handlers: dict[str, Callable[[dict[str, Any]], Any]] = {}
        self.reserved_names = set(BUILTIN_TOOL_NAMES) | set(reserved_names)
        self.module_names: list[str] = []

    def register(self, tool: dict[str, Any], handler: Callable[[dict[str, Any]], Any], *, risk: str = "read") -> None:
        if risk != "read":
            raise ValueError("OPENAI_EXTENSION_SIDE_EFFECTS_DISABLED")
        if not callable(handler):
            raise ValueError("OPENAI_EXTENSION_HANDLER_REQUIRED")
        if not isinstance(tool, dict) or tool.get("type") != "function":
            raise ValueError("OPENAI_EXTENSION_TOOL_MUST_BE_FUNCTION")
        name = tool.get("name")
        if not isinstance(name, str) or not _TOOL_NAME.fullmatch(name):
            raise ValueError("OPENAI_EXTENSION_INVALID_TOOL_NAME")
        if name in self.reserved_names or name in self.handlers:
            raise ValueError(f"OPENAI_EXTENSION_DUPLICATE_TOOL:{name}")
        parameters = tool.get("parameters")
        if not isinstance(parameters, dict) or parameters.get("type") != "object":
            raise ValueError("OPENAI_EXTENSION_PARAMETERS_MUST_BE_OBJECT")
        properties = parameters.get("properties")
        required = parameters.get("required")
        if not isinstance(properties, dict) or parameters.get("additionalProperties") is not False:
            raise ValueError("OPENAI_EXTENSION_SCHEMA_MUST_BE_CLOSED_OBJECT")
        if not isinstance(required, list) or set(required) != set(properties):
            raise ValueError("OPENAI_EXTENSION_STRICT_SCHEMA_REQUIRES_ALL_PROPERTIES")
        project_id = properties.get("project_id")
        if not isinstance(project_id, dict) or project_id.get("type") != "string" or "project_id" not in required:
            raise ValueError("OPENAI_EXTENSION_PROJECT_ID_REQUIRED")
        if tool.get("strict") is not True:
            raise ValueError("OPENAI_EXTENSION_STRICT_MODE_REQUIRED")
        for key in ("description",):
            if not isinstance(tool.get(key), str) or not tool[key].strip():
                raise ValueError(f"OPENAI_EXTENSION_{key.upper()}_REQUIRED")
        self.tools.append(deepcopy(tool))
        self.handlers[name] = handler

def load_openai_extensions(
    modules: str | Iterable[str] | None = None,
    *,
    reserved_names: Iterable[str] = (),
) -> OpenAIToolRegistry:
    """Load trusted modules exporting register_openai_tools(registry), failing closed."""
    configured = os.getenv("NEXUS_OPENAI_EXTENSION_MODULES", "") if modules is None else modules
    values = configured.split(",") if isinstance(configured, str) else list(configured)
    names = [str(value).strip() for value in values if str(value).strip()]
    if len(names) != len(set(names)):
        raise RuntimeError("Duplicate module in NEXUS_OPENAI_EXTENSION_MODULES")
    registry = OpenAIToolRegistry(reserved_names)
    for name in names:
        try:
            module = importlib.import_module(name)
        except Exception as exc:
            raise RuntimeError(f"Unable to import OpenAI extension {name!r} ({type(exc).__name__})") from exc
        register = getattr(module, "register_openai_tools", None)
        if not callable(register):
            raise RuntimeError(f"OpenAI extension {name!r} must define register_openai_tools(registry)")
        try:
            register(registry)
        except Exception as exc:
            raise RuntimeError(f"Unable to register OpenAI extension {name!r} ({type(exc).__name__})") from exc
        registry.module_names.append(name)
    return registry
