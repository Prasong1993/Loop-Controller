"""Durable at-most-once request ledger for operations with uncertain outcomes.

An IN_PROGRESS/UNCERTAIN key is never silently replayed. Operators must reconcile
whether the protected operation took effect before deciding how to recover.
"""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json
import sqlite3

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

class IdempotencyConflict(ValueError):
    pass

class IdempotencyInProgress(RuntimeError):
    pass

class IdempotencyStore:
    def __init__(self, database: str = "data/nexus.db"):
        self.database=database
        Path(database).parent.mkdir(parents=True,exist_ok=True)
        with self._connect() as con:
            con.execute("""CREATE TABLE IF NOT EXISTS idempotency_records(
                idempotency_key TEXT PRIMARY KEY,
                scope TEXT NOT NULL,
                fingerprint TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('IN_PROGRESS','COMPLETED','UNCERTAIN')),
                response_json TEXT,
                error_class TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )""")
            con.execute("CREATE INDEX IF NOT EXISTS idx_idempotency_scope ON idempotency_records(scope,created_at)")

    def _connect(self):
        con=sqlite3.connect(self.database,timeout=10)
        con.row_factory=sqlite3.Row
        con.execute("PRAGMA busy_timeout=10000")
        return con

    def claim(self,key:str,*,scope:str,fingerprint:str)->dict[str,Any]:
        if not key.strip() or len(key)>200:
            raise ValueError("Idempotency-Key must contain 1..200 characters")
        now=utc_now()
        with self._connect() as con:
            row=con.execute("SELECT * FROM idempotency_records WHERE idempotency_key=?",(key,)).fetchone()
            if row:
                if row["scope"]!=scope or row["fingerprint"]!=fingerprint:
                    raise IdempotencyConflict("Idempotency-Key was already used for a different operation")
                if row["status"]=="COMPLETED":
                    return {"status":"COMPLETED","response":json.loads(row["response_json"])}
                raise IdempotencyInProgress("An earlier attempt is IN_PROGRESS or UNCERTAIN; reconcile before retrying")
            con.execute("""INSERT INTO idempotency_records
                (idempotency_key,scope,fingerprint,status,response_json,error_class,created_at,updated_at)
                VALUES(?,?,?,'IN_PROGRESS',NULL,NULL,?,?)""",(key,scope,fingerprint,now,now))
        return {"status":"IN_PROGRESS","response":None}

    def complete(self,key:str,response:dict[str,Any])->None:
        now=utc_now()
        with self._connect() as con:
            cur=con.execute("""UPDATE idempotency_records SET status='COMPLETED',response_json=?,
                error_class=NULL,updated_at=? WHERE idempotency_key=? AND status='IN_PROGRESS'""",
                (json.dumps(response,ensure_ascii=False,sort_keys=True,default=str),now,key))
            if cur.rowcount!=1:
                raise IdempotencyInProgress("idempotency record is not in a completable state")

    def mark_uncertain(self,key:str,error_class:str)->None:
        with self._connect() as con:
            cur=con.execute("""UPDATE idempotency_records SET status='UNCERTAIN',error_class=?,updated_at=?
                WHERE idempotency_key=? AND status='IN_PROGRESS'""",(error_class[:100],utc_now(),key))
            if cur.rowcount!=1:
                raise IdempotencyInProgress("idempotency record is not in an uncertain transition state")
