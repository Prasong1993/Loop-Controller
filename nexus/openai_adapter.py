"""OpenAI Responses API worker with deterministic NEXUS tool gating.

The model may propose tool calls. This module never executes a proposed tool unless
the deterministic policy callback explicitly allows it. API keys are read by the
official SDK from OPENAI_API_KEY and must never be written to operational records.
"""
from __future__ import annotations
import json
import os
from typing import Any, Callable

class OpenAIWorkerError(RuntimeError):
    pass

class OpenAIResponsesWorker:
    def __init__(self, *, model: str, client: Any | None = None,
                 max_tool_rounds: int = 6):
        if not model or not model.strip():
            raise ValueError("model is required")
        if max_tool_rounds < 1 or max_tool_rounds > 20:
            raise ValueError("max_tool_rounds must be between 1 and 20")
        if client is None:
            try:
                from openai import OpenAI
            except ImportError as exc:
                raise OpenAIWorkerError(
                    "OpenAI SDK is not installed; install the project's openai dependency"
                ) from exc
            if not os.environ.get("OPENAI_API_KEY"):
                raise OpenAIWorkerError("OPENAI_API_KEY is not configured")
            client = OpenAI()
        self.client = client
        self.model = model
        self.max_tool_rounds = max_tool_rounds

    def run(self, *, prompt: str, tools: list[dict[str, Any]],
            tool_handlers: dict[str, Callable[[dict[str, Any]], Any]],
            policy_check: Callable[[str, dict[str, Any]], dict[str, Any]],
            record: Callable[..., Any] | None = None) -> dict[str, Any]:
        """Run a Responses API turn. Tools are executed only after policy ALLOW.

        policy_check(tool_name, parsed_arguments) must be a deterministic NEXUS
        policy function. A missing handler, malformed arguments, policy denial,
        or tool exception never causes an automatic retry of that tool.
        """
        if not prompt.strip():
            raise ValueError("prompt is required")
        declared_names = set()
        for tool in tools:
            if tool.get("type") == "function":
                name = (tool.get("name") or tool.get("function", {}).get("name"))
                if name:
                    declared_names.add(name)
        conversation: list[Any] = [{"role": "user", "content": prompt}]
        executed: list[dict[str, Any]] = []
        decisions: list[dict[str, Any]] = []

        def log(record_type: str, **fields: Any) -> None:
            if record:
                # Never pass prompts, raw tool arguments, credentials, or raw outputs.
                record(record_type=record_type, model=self.model, **fields)

        for round_index in range(self.max_tool_rounds + 1):
            try:
                response = self.client.responses.create(
                    model=self.model, input=conversation, tools=tools,
                    tool_choice="auto", parallel_tool_calls=False,
                )
            except Exception as exc:
                log("error", error_class=type(exc).__name__, error_code="OPENAI_RESPONSE_FAILED",
                    retryable=False, round=round_index)
                raise OpenAIWorkerError("OpenAI Responses API request failed") from exc

            output = list(getattr(response, "output", []) or [])
            conversation.extend(output)
            calls = [item for item in output if getattr(item, "type", None) == "function_call"]
            if not calls:
                log("usage", outcome="completed", round=round_index,
                    response_id=getattr(response, "id", None))
                return {"response_id": getattr(response, "id", None),
                        "output_text": getattr(response, "output_text", ""),
                        "tool_calls": executed, "policy_decisions": decisions,
                        "rounds": round_index + 1}

            if round_index >= self.max_tool_rounds:
                log("error", error_class="ToolRoundLimit", error_code="TOOL_ROUND_LIMIT",
                    retryable=False, round=round_index)
                raise OpenAIWorkerError("maximum tool-call rounds reached")

            for call in calls:
                name = getattr(call, "name", "")
                call_id = getattr(call, "call_id", "")
                raw_arguments = getattr(call, "arguments", "{}")
                try:
                    arguments = json.loads(raw_arguments or "{}")
                    if not isinstance(arguments, dict):
                        raise ValueError("tool arguments must be a JSON object")
                except (TypeError, json.JSONDecodeError, ValueError):
                    decision = {"decision": "BLOCK", "reason_code": "INVALID_TOOL_ARGUMENTS"}
                    result: Any = {"error": "INVALID_TOOL_ARGUMENTS", "retryable": False}
                else:
                    if name not in declared_names or name not in tool_handlers:
                        decision = {"decision": "BLOCK", "reason_code": "TOOL_NOT_REGISTERED"}
                        result = {"error": "TOOL_NOT_REGISTERED", "retryable": False}
                    else:
                        try:
                            decision = policy_check(name, arguments)
                        except Exception as exc:
                            decision = {"decision": "BLOCK", "reason_code": "POLICY_CHECK_FAILED",
                                        "policy_error_class": type(exc).__name__}
                        if decision.get("decision") != "ALLOW":
                            result = {"error": "POLICY_DENIED",
                                      "reason_code": decision.get("reason_code", "POLICY_DENIED"),
                                      "retryable": False}
                        else:
                            try:
                                result = tool_handlers[name](arguments)
                                executed.append({"tool": name, "call_id": call_id, "outcome": "executed"})
                            except Exception as exc:
                                result = {"error": "TOOL_EXECUTION_FAILED",
                                          "error_class": type(exc).__name__, "retryable": False}
                                log("error", error_class=type(exc).__name__,
                                    error_code="TOOL_EXECUTION_FAILED", tool=name,
                                    retryable=False, call_id=call_id)
                decisions.append({"tool": name, "call_id": call_id, **decision})
                log("decision", tool=name, call_id=call_id,
                    decision=decision.get("decision", "BLOCK"),
                    reason_code=decision.get("reason_code", "UNSPECIFIED"))
                try:
                    serialized = json.dumps(result, ensure_ascii=False, default=str)
                except Exception:
                    serialized = json.dumps({"error": "TOOL_RESULT_SERIALIZATION_FAILED"})
                conversation.append({"type": "function_call_output",
                                     "call_id": call_id, "output": serialized})

        raise OpenAIWorkerError("unreachable tool loop termination")
