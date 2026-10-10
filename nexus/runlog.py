"""Durable per-invocation router run ledger stored beside the NEXUS SQLite database."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
import json
import sqlite3
import uuid


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class RouterRunLog:
    """Append-only run/event ledger; a missing terminal event remains visibly incomplete."""

    def __init__(self, database: str):
        self.database = database
        Path(database).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as con:
            con.executescript("""
                CREATE TABLE IF NOT EXISTS router_runs (
                    run_id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    finished_at TEXT,
                    outcome_json TEXT NOT NULL DEFAULT '{}'
                );
                CREATE TABLE IF NOT EXISTS router_run_events (
                    event_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL REFERENCES router_runs(run_id),
                    sequence_no INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    details_json TEXT NOT NULL DEFAULT '{}',
                    UNIQUE(run_id, sequence_no)
                );
                CREATE INDEX IF NOT EXISTS idx_router_runs_task ON router_runs(task_id, started_at);
                CREATE INDEX IF NOT EXISTS idx_router_events_run ON router_run_events(run_id, sequence_no);
            """)

    def _connect(self):
        con = sqlite3.connect(self.database, timeout=10)
        con.row_factory = sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        return con

    def start(self, task_id: str, candidate_ids: list[str]) -> str:
        run_id = str(uuid.uuid4())
        now = _now()
        with self._connect() as con:
            con.execute(
                "INSERT INTO router_runs(run_id,task_id,status,started_at) VALUES(?,?,?,?)",
                (run_id, task_id, "RUNNING", now),
            )
            self._append(con, run_id, "RUN_STARTED", {"task_id": task_id, "candidate_ids": candidate_ids})
        return run_id

    def append(self, run_id: str, event_type: str, details: Mapping[str, Any] | None = None) -> None:
        with self._connect() as con:
            self._append(con, run_id, event_type, dict(details or {}))
    def finish(self, run_id: str, status: str, outcome: Mapping[str, Any]) -> None:
        if status not in {"COMPLETED", "BLOCKED", "FAILED"}:
            raise ValueError("invalid terminal run status")
        with self._connect() as con:
            changed = con.execute(
                "UPDATE router_runs SET status=?,finished_at=?,outcome_json=? WHERE run_id=? AND status='RUNNING'",
                (status, _now(), json.dumps(dict(outcome), ensure_ascii=False, sort_keys=True, default=str), run_id),
            ).rowcount
            if changed != 1:
                raise ValueError("run is missing or already finalized")
            self._append(con, run_id, "RUN_FINISHED", {"status": status, "outcome": dict(outcome)})

    def _append(self, con: sqlite3.Connection, run_id: str, event_type: str, details: Mapping[str, Any]) -> None:
        sequence = con.execute(
            "SELECT COALESCE(MAX(sequence_no),0)+1 FROM router_run_events WHERE run_id=?", (run_id,)
        ).fetchone()[0]
        con.execute(
            "INSERT INTO router_run_events(event_id,run_id,sequence_no,event_type,created_at,details_json) VALUES(?,?,?,?,?,?)",
            (str(uuid.uuid4()), run_id, sequence, event_type, _now(),
             json.dumps(dict(details), ensure_ascii=False, sort_keys=True, default=str)),
        )

    def get_run(self, run_id: str) -> dict[str, Any]:
        with self._connect() as con:
            run = con.execute("SELECT * FROM router_runs WHERE run_id=?", (run_id,)).fetchone()
            if not run:
                raise ValueError("unknown run_id")
            events = con.execute(
                "SELECT sequence_no,event_type,created_at,details_json FROM router_run_events WHERE run_id=? ORDER BY sequence_no",
                (run_id,),
            ).fetchall()
        result = dict(run)
        result["outcome_json"] = json.loads(result["outcome_json"])
        result["events"] = [
            {"sequence_no": row["sequence_no"], "event_type": row["event_type"],
             "created_at": row["created_at"], "details": json.loads(row["details_json"])}
            for row in events
        ]
        return result
