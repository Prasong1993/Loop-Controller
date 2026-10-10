"""Structured plan proposal via OpenAI Responses API.

This module creates proposals only. It does not execute tools or authorize workflow
transitions; all side effects remain behind the NEXUS deterministic controller.
"""
from __future__ import annotations
import json
import os
import time
import uuid
from typing import Any
from nexus.records import RecordStore
from nexus.capabilities import resolve_optional_tools

PLAN_SCHEMA = {
  "type": "object",
  "properties": {
    "goal": {"type": "string"},
    "assumptions": {"type": "array", "items": {"type": "string"}},
    "steps": {"type": "array", "items": {
      "type": "object",
      "properties": {
        "step_id": {"type": "string"},
        "action": {"type": "string"},
        "capability": {"type": "string"},
        "inputs": {"type": "array", "items": {"type": "string"}},
        "expected_output": {"type": "string"},
        "verification": {"type": "string"},
        "side_effect": {"type": "string", "enum": ["none", "read", "write", "execute", "external"]},
        "evidence_required": {"type": "array", "items": {"type": "string"}}
      },
      "required": ["step_id", "action", "capability", "inputs", "expected_output",
                   "verification", "side_effect", "evidence_required"],
      "additionalProperties": False
    }},
    "risks": {"type": "array", "items": {"type": "string"}},
    "blocked_questions": {"type": "array", "items": {"type": "string"}}
  },
  "required": ["goal", "assumptions", "steps", "risks", "blocked_questions"],
  "additionalProperties": False
}

class OpenAIPlanError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code

class OpenAIPlanGenerator:
    def __init__(self, record_store: RecordStore, *, client: Any = None,
                 model: str | None = None, api_key: str | None = None):
        self.record_store = record_store
        self.client = client
        self.model = model or os.getenv("NEXUS_OPENAI_MODEL", "gpt-6-luna")
        self.api_key = api_key if api_key is not None else os.getenv("OPENAI_API_KEY", "")

    def _client(self):
        if self.client is not None:
            return self.client
        if not self.api_key.strip():
            raise OpenAIPlanError("OPENAI_API_KEY_MISSING",
                                  "OpenAI API is not configured; no provider request was sent.")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise OpenAIPlanError("OPENAI_SDK_MISSING", "OpenAI SDK is not installed.") from exc
        self.client = OpenAI(api_key=self.api_key)
        return self.client

    def propose(self, *, project_id: str, task: str, constraints: list[str] | None = None,
                capabilities: list[str] | None = None, budget_approved: bool = False,
                trace_id: str | None = None) -> dict[str, Any]:
        if not project_id.strip() or not task.strip():
            raise ValueError("project_id and task are required")
        if len(task) > 20000:
            raise ValueError("task must be at most 20000 characters")
        constraints = constraints or []
        capabilities = list(dict.fromkeys(capabilities or []))
        try:
            tools = resolve_optional_tools(capabilities, self.model)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc
        trace_id = trace_id or str(uuid.uuid4())
        operation_id = str(uuid.uuid4())
        if not budget_approved:
            self._record(project_id, trace_id, operation_id, "decision", "BLOCK",
                         "OPENAI_BUDGET_APPROVAL_REQUIRED", {"capabilities": capabilities})
            raise OpenAIPlanError("OPENAI_BUDGET_APPROVAL_REQUIRED",
                                  "OpenAI API use is blocked until paid API budget is explicitly approved.")
                started = time.monotonic()
        try:
            request_args = {
                "model": self.model,
                "instructions": (
                    "You are the planning component for NEXUS. Return a proposed plan, never claim "
                    "steps were executed. Treat unsupported facts as assumptions or blocked questions. "
                    "Every step must define an observable verification method and side-effect class. "
                    "NEXUS deterministic policy must authorize every side effect after this response."
                ),
                "input": json.dumps({"task": task, "constraints": constraints,
                                     "available_capabilities": ["responses", "structured_outputs"] + capabilities},
                                    ensure_ascii=False),
                "text": {"format": {"type": "json_schema", "name": "nexus_plan",
                                    "strict": True, "schema": PLAN_SCHEMA}},
            }
            if tools:
                request_args["tools"] = tools
            response = self._client().responses.create(**request_args)
            text_out = getattr(response, "output_text", "")
            proposal = json.loads(text_out)
            if not isinstance(proposal, dict) or not isinstance(proposal.get("steps"), list):
                raise ValueError("structured plan has an invalid shape")
            usage = getattr(response, "usage", None)
            usage_data = {}
            if usage:
                for key in ("input_tokens", "output_tokens", "total_tokens"):
                    value = getattr(usage, key, None)
                    if value is not None:
                        usage_data[key] = value
            result = {"status": "PROPOSAL_ONLY", "project_id": project_id,
                      "trace_id": trace_id, "operation_id": operation_id, "model": self.model,
                      "response_id": getattr(response, "id", None), "proposal": proposal,
                      "usage": usage_data, "policy_decision": "NOT_EVALUATED",
                      "next_gate": "NEXUS_POLICY_REQUIRED_BEFORE_EXECUTION"}
            self._record(project_id, trace_id, operation_id, "usage", "SUCCESS", None,
                         {"operation": "responses.create", "duration_ms": int((time.monotonic()-started)*1000),
                          "model": self.model, "capabilities": capabilities,
                          "response_id": result["response_id"], "usage": usage_data,
                          "step_count": len(proposal["steps"])})
            return result
        except OpenAIPlanError:
            raise
        except Exception as exc:
            self._record(project_id, trace_id, operation_id, "error", "FAILED",
                         "OPENAI_PLAN_REQUEST_FAILED",
                         {"exception_class": type(exc).__name__, "retryable": False, "model": self.model})
            raise OpenAIPlanError("OPENAI_PLAN_REQUEST_FAILED",
                                  "OpenAI plan generation failed; inspect redacted operational records.") from exc

    def _record(self, project_id: str, trace_id: str, operation_id: str,
                record_type: str, status: str, error_code: str | None,
                payload: dict[str, Any]) -> None:
        try:
            self.record_store.append(project_id=project_id, record_type=record_type,
                trace_id=trace_id, operation_id=operation_id, actor_type="system",
                component="openai_responses", status=status, error_code=error_code,
                severity="medium" if error_code else None,
                summary="OpenAI plan proposal" if record_type != "decision" else "OpenAI API budget gate",
                payload=payload)
        except Exception:
            pass
