"""Trusted, server-configured MCP tool extension loader.

Only deployment administrators may configure extension module names. Never take
module names from tool arguments, task input, or other user-controlled content.
"""
from __future__ import annotations

import importlib
import os
from collections.abc import Iterable
from types import ModuleType
from typing import Any


def _configured_names(modules: str | Iterable[str] | None) -> list[str]:
    configured: str | Iterable[str]
    configured = os.getenv("NEXUS_MCP_EXTENSION_MODULES", "") if modules is None else modules
    values = configured.split(",") if isinstance(configured, str) else list(configured)
    names = [str(value).strip() for value in values if str(value).strip()]
    if len(names) != len(set(names)):
        raise RuntimeError("Duplicate module in NEXUS_MCP_EXTENSION_MODULES")
    return names


def load_mcp_extensions(
    mcp: Any,
    track_tool: Any,
    modules: str | Iterable[str] | None = None,
) -> list[str]:
    """Register all configured trusted extensions; there is no arbitrary count cap.

    Each extension module must export register_mcp_tools(mcp, track_tool). A
    broken configured extension fails startup rather than silently hiding tools.
    """
    names = _configured_names(modules)
    loaded: list[str] = []
    for name in names:
        try:
            module: ModuleType = importlib.import_module(name)
        except Exception as exc:
            raise RuntimeError(
                f"Unable to import configured MCP extension {name!r} ({type(exc).__name__})"
            ) from exc
        register = getattr(module, "register_mcp_tools", None)
        if not callable(register):
            raise RuntimeError(
                f"MCP extension {name!r} must define register_mcp_tools(mcp, track_tool)"
            )
        try:
            register(mcp, track_tool)
        except Exception as exc:
            raise RuntimeError(
                f"Unable to register configured MCP extension {name!r} ({type(exc).__name__})"
            ) from exc
        loaded.append(name)
    return loaded
