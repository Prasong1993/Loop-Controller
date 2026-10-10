"""Structured code-change proposals via OpenAI Responses API.

This module generates reviewable file proposals only. It never writes to a
repository, executes code, or authorizes side effects.
"""
from __future__ import annotations
import hashlib
import json
import os
import time
import uuid
from pathlib import PurePosixPath
from typing import Any
from nexus.records import RecordStore

SUPPORTED_CODE_MODELS = {"gpt-6-astra", "gpt-6.1-sol"}

CODE_SCHEMA = {
    "type": "object",
    "properties": {
        "goal": {"type": "string"},
        "files": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "operation": {"type": "string", "enum": ["create", "update"]},
                "content": {"type": "string"},
                "rationale": {"type": "string"}
            },
            "required": ["path", "operation", "content", "rationale"],
            "additionalProperties": False
        }},
        "tests": {"type": "array", "items": {"type": "string"}},
        "risks": {"type": "array", "items": {"type": "string"}},
        "blocked_questions": {"type": "array", "items": {"type": "string"}}
    },
    "required": ["goal", "files", "tests", "risks", "blocked_questions"],
    "additionalProperties": False
}

class CodeProposalError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code

def _safe_relative_path(value: str) -> bool:
    if not value or not value.strip() or "\\" in value or value.startswith("/"):
        return False
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        return False
    forbidden = {".git", ".ssh", "secrets", "credentials", "node_modules"}
    if any(part.casefold() in forbidden or part.casefold() == ".env" or part.casefold().startswith(".env.") for part in path.parts):
        return False
    return True

class OpenAICodeProposalGenerator:
    def __init__(self, record_store: RecordStore, *, client: Any = None,
                 model: str | None = None, api_key: str | None = None):
        self.record_store = record_store
        self.client = client
        self.model = model or os.getenv("NEXUS_CODE_MODEL", "gpt-6-astra")
        self.api_key = api_key if api_key is not None else os.getenv("OPENAI_API_KEY", "")

    def _client(self):
        if self.client is not None:
            return self.client
        if not self.api_key.strip():
            raise CodeProposalError("OPENAI_API_KEY_MISSING", "OpenAI API is not configured; no provider request was sent.")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise CodeProposalError("OPENAI_SDK_MISSING", "OpenAI SDK is not installed.") from exc
        self.client = OpenAI(api_key=self.api_key)
        return self.client

    def propose(self, *, project_id: str, task: str, allowed_paths: list[str],
                task_id: str | None = None, constraints: list[str] | None = None,
                budget_approved: bool = False, trace_id: str | None = None) -> dict[str, Any]:
        if not project_id.strip() or not task.strip():
            raise ValueError("project_id and task are required")
        if len(task) > 20000:
            raise ValueError("task must be at most 20000 characters")
        if self.model not in SUPPORTED_CODE_MODELS:
            raise ValueError(f"code generation is not verified for model {self.model}")
        if not allowed_paths or len(allowed_paths) > 20:
            raise ValueError("allowed_paths must contain 1..20 paths")
        if len(set(allowed_paths)) != len(allowed_paths) or any(not _safe_relative_path(path) for path in allowed_paths):
            raise ValueError("allowed_paths contains unsafe or duplicate paths")
        constraints = constraints or []
        trace_id = trace_id or str(uuid.uuid4())
        operation_id = str(uuid.uuid4())
        if not budget_approved:
            self._record(project_id, task_id, trace_id, operation_id, "decision", "BLOCK",
                         "OPENAI_BUDGET_APPROVAL_REQUIRED", {"model": self.model})
            raise CodeProposalError("OPENAI_BUDGET_APPROVAL_REQUIRED",
                                    "Code proposal is blocked until paid API budget is explicitly approved.")
        started = time.monotonic()
        try:
            response = self._client().responses.create(
                model=self.model,
                reasoning={"effort": "high"},
                instructions=(
                    "Generate a proposed code change only. Do not claim that files were written or tests were run. "
                    "Only return files whose paths exactly match the caller-provided allowed_paths list. "
                    "Never include secrets, credentials, private keys, or environment files. "
                    "Prefer the smallest coherent change, include relevant tests, and state risks or blocked questions. "
                    "The proposal is not authorization to write or execute code."
                ),
                input=json.dumps({"task": task, "constraints": constraints,
                                  "allowed_paths": allowed_paths,
                                  "contract": "proposal_only; no writes or execution"},
                                 ensure_ascii=False),
                text={"format": {"type": "json_schema", "name": "nexus_code_proposal",
                                 "strict": True, "schema": CODE_SCHEMA}},
            )
            proposal = json.loads(getattr(response, "output_text", ""))
            files = proposal.get("files") if isinstance(proposal, dict) else None
            if not isinstance(files, list) or not files:
                raise ValueError("structured code proposal must contain at least one file")
            seen = set()
            for item in files:
                path = item.get("path", "")
                if path not in allowed_paths or not _safe_relative_path(path):
                    self._record(project_id, task_id, trace_id, operation_id, "decision", "BLOCK",
                                 "CODE_PATH_NOT_ALLOWED", {"proposed_path_sha256": hashlib.sha256(str(path).encode("utf-8")).hexdigest()})
                    raise CodeProposalError("CODE_PATH_NOT_ALLOWED", "Provider proposed a path outside the explicit allowlist.")
                if path in seen:
                    self._record(project_id, task_id, trace_id, operation_id, "decision", "BLOCK",
                                 "DUPLICATE_CODE_PATH", {"proposed_path_sha256": hashlib.sha256(str(path).encode("utf-8")).hexdigest()})
                    raise CodeProposalError("DUPLICATE_CODE_PATH", "Provider proposed the same path more than once.")
                seen.add(path)
            usage = {}
            raw_usage = getattr(response, "usage", None)
            if raw_usage:
                for key in ("input_tokens", "output_tokens", "total_tokens"):
                    value = getattr(raw_usage, key, None)
                    if isinstance(value, int) and value >= 0:
                        usage[key] = value
            file_summary = [{"path": item["path"], "operation": item["operation"],
                             "content_sha256": hashlib.sha256(item["content"].encode("utf-8")).hexdigest(),
                             "content_chars": len(item["content"])} for item in files]
            result = {"status": "PROPOSAL_ONLY", "project_id": project_id, "task_id": task_id,
                      "trace_id": trace_id, "operation_id": operation_id, "model": self.model,
                      "response_id": getattr(response, "id", None), "proposal": proposal,
                      "usage": usage, "policy_decision": "NOT_EVALUATED",
                      "next_gate": "REVIEW_DIFF_AND_TESTS_BEFORE_ANY_WORKSPACE_WRITE"}
            self._record(project_id, task_id, trace_id, operation_id, "usage", "SUCCESS", None,
                         {"operation": "responses.create.code_proposal",
                          "duration_ms": max(0, int((time.monotonic()-started)*1000)),
                          "model": self.model, "response_id": result["response_id"],
                          "usage": usage, "file_summary": file_summary, "test_count": len(proposal.get("tests", []))})
            return result
        except CodeProposalError:
            raise
        except Exception as exc:
            self._record(project_id, task_id, trace_id, operation_id, "error", "FAILED",
                         "OPENAI_CODE_PROPOSAL_FAILED",
                         {"exception_class": type(exc).__name__, "retryable": False, "model": self.model})
            raise CodeProposalError("OPENAI_CODE_PROPOSAL_FAILED",
                                    "Code proposal generation failed; inspect redacted operational records.") from exc

    def _record(self, project_id: str, task_id: str | None, trace_id: str, operation_id: str,
                record_type: str, status: str, error_code: str | None,
                payload: dict[str, Any]) -> None:
        try:
            self.record_store.append(project_id=project_id, task_id=task_id, trace_id=trace_id,
                operation_id=operation_id, record_type=record_type, actor_type="system",
                component="openai_code_proposal", status=status, error_code=error_code,
                severity="medium" if error_code else None,
                summary="OpenAI code proposal" if record_type != "decision" else "OpenAI code budget gate",
                payload=payload)
        except Exception:
            # A record-store failure never authorizes a write; this module never writes files.
            pass
