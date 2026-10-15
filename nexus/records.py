"""Append-only operational record store for NEXUS.

This module defines a structured, searchable persistence boundary. It intentionally
stores redacted summaries rather than raw request/response bodies or credentials.
"""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json
import sqlite3
import uuid
from nexus.database import connect_database

SCHEMA_VERSION = "1.0"
RECORD_TYPES = {"usage", "error", "evidence", "decision", "checkpoint", "verification"}

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

class RecordStore:
    def __init__(self, database: str = "data/nexus.db"):
        self.database = database
        Path(database).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as con:
            con.executescript("""
            CREATE TABLE IF NOT EXISTS operational_records (
              record_id TEXT PRIMARY KEY,
              schema_version TEXT NOT NULL,
              record_type TEXT NOT NULL,
              project_id TEXT NOT NULL,
              task_id TEXT,
              session_id TEXT,
              trace_id TEXT NOT NULL,
              operation_id TEXT,
              occurred_at TEXT NOT NULL,
              actor_type TEXT NOT NULL,
              actor_id TEXT,
              status TEXT NOT NULL,
              component TEXT NOT NULL,
              error_code TEXT,
              severity TEXT,
              summary TEXT NOT NULL,
              payload_json TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_records_project_time ON operational_records(project_id, occurred_at);
            CREATE INDEX IF NOT EXISTS idx_records_task_time ON operational_records(task_id, occurred_at);
            CREATE INDEX IF NOT EXISTS idx_records_trace ON operational_records(trace_id);
            CREATE INDEX IF NOT EXISTS idx_records_operation ON operational_records(operation_id);
            CREATE INDEX IF NOT EXISTS idx_records_type_status ON operational_records(record_type, status);
            CREATE INDEX IF NOT EXISTS idx_records_error ON operational_records(error_code, occurred_at);
            CREATE INDEX IF NOT EXISTS idx_records_component ON operational_records(component, occurred_at);
            """)

    def _connect(self):
        return connect_database(self.database)

    def append(self, *, project_id: str, record_type: str, payload: dict[str, Any],
               task_id: str | None = None, session_id: str | None = None,
               trace_id: str | None = None, operation_id: str | None = None,
               actor_type: str = "system", actor_id: str | None = None,
               status: str = "RECORDED", component: str = "nexus",
               error_code: str | None = None, severity: str | None = None,
               summary: str = "") -> dict[str, Any]:
        if record_type not in RECORD_TYPES:
            raise ValueError("unsupported record_type")
        if not project_id.strip() or not component.strip() or not actor_type.strip():
            raise ValueError("project_id, component and actor_type are required")
        record_id = str(uuid.uuid4())
        trace_id = trace_id or str(uuid.uuid4())
        occurred_at = utc_now()
        safe_payload = dict(payload)
        # Reject credentials and raw user/provider/code content at the storage boundary.
        # Normalize key spelling so OPENAI_API_KEY, client-secret, etc. cannot bypass the guard.
        forbidden_markers = (
            "authorization", "apikey", "password", "secret", "accesstoken",
            "refreshtoken", "privatekey", "bearertoken", "cookie",
            "prompt", "messages", "arguments", "toolarguments", "outputtext",
            "responsetext", "sourcetext", "pagecontent", "filecontent",
            "requestbody", "responsebody", "patch", "diff", "sourcecode",
            "generatedcode", "rawcode", "codesnippet", "codeblock", "codecontent",
            "modelinput", "modeloutput", "inputdata", "outputdata", "transcript",
        )
        forbidden_exact = {"input", "output", "content", "code", "body"}
        def inspect(value):
            if isinstance(value, dict):
                for key, nested in value.items():
                    normalized = "".join(ch for ch in str(key).casefold() if ch.isalnum())
                    if normalized in forbidden_exact or any(marker in normalized for marker in forbidden_markers):
                        raise ValueError("secret-bearing or raw-content payload keys must not be recorded")
                    inspect(nested)
            elif isinstance(value, list):
                for nested in value:
                    inspect(nested)
        inspect(safe_payload)
        with self._connect() as con:
            con.execute("""INSERT INTO operational_records
              (record_id,schema_version,record_type,project_id,task_id,session_id,trace_id,operation_id,
               occurred_at,actor_type,actor_id,status,component,error_code,severity,summary,payload_json)
              VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
              (record_id, SCHEMA_VERSION, record_type, project_id, task_id, session_id, trace_id,
               operation_id, occurred_at, actor_type, actor_id, status, component, error_code,
               severity, summary[:1000], json.dumps(safe_payload, ensure_ascii=False, sort_keys=True)))
        return {"record_id": record_id, "schema_version": SCHEMA_VERSION, "record_type": record_type,
                "project_id": project_id, "task_id": task_id, "trace_id": trace_id,
                "operation_id": operation_id, "occurred_at": occurred_at, "status": status,
                "error_code": error_code}

    def search(self, *, project_id: str, record_type: str | None = None,
               task_id: str | None = None, trace_id: str | None = None,
               operation_id: str | None = None, status: str | None = None,
               error_code: str | None = None, component: str | None = None,
               query: str | None = None, since: str | None = None, until: str | None = None,
               limit: int = 100, offset: int = 0) -> dict[str, Any]:
        if not project_id.strip():
            raise ValueError("project_id is required")
        if limit < 1 or limit > 500 or offset < 0:
            raise ValueError("limit must be 1..500 and offset must be non-negative")
        clauses = ["project_id=?"]
        params: list[Any] = [project_id]
        for column, value in (("record_type", record_type), ("task_id", task_id),
                              ("trace_id", trace_id), ("operation_id", operation_id),
                              ("status", status), ("error_code", error_code), ("component", component)):
            if value is not None:
                clauses.append(f"{column}=?"); params.append(value)
        if since is not None:
            clauses.append("occurred_at>=?"); params.append(since)
        if until is not None:
            clauses.append("occurred_at<=?"); params.append(until)
        if query is not None and query.strip():
            clauses.append("(summary LIKE ? OR payload_json LIKE ?)")
            pattern = "%" + query.strip().replace("%", "\\%").replace("_", "\\_") + "%"
            clauses.extend([]); params.extend([pattern, pattern])
        where = " AND ".join(clauses)
        with self._connect() as con:
            total = con.execute(f"SELECT COUNT(*) FROM operational_records WHERE {where}", params).fetchone()[0]
            rows = con.execute(f"""SELECT * FROM operational_records WHERE {where}
                ORDER BY occurred_at DESC, record_id DESC LIMIT ? OFFSET ?""",
                [*params, limit, offset]).fetchall()
        records = []
        for row in rows:
            item = dict(row)
            item["payload"] = json.loads(item.pop("payload_json"))
            records.append(item)
        return {"project_id": project_id, "count": len(records), "total": total,
                "limit": limit, "offset": offset, "next_offset": offset + len(records) if offset + len(records) < total else None,
                "records": records}
