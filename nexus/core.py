"""Deterministic NEXUS workflow core. No LLM is used for policy decisions."""
from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any
import json
import sqlite3
import uuid

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

class State(str, Enum):
    INTAKE="INTAKE"; RESEARCH="RESEARCH"; PLAN="PLAN"; POLICY="POLICY"
    EXECUTE="EXECUTE"; VERIFY="VERIFY"; AUDIT="AUDIT"; COMPLETE="COMPLETE"
    RECOVER="RECOVER"; BLOCKED="BLOCKED"

class EvidenceStatus(str, Enum):
    VERIFIED="VERIFIED"; RECOVERED="RECOVERED"; UNKNOWN="UNKNOWN"; BLOCKED="BLOCKED"

ALLOWED_TRANSITIONS = {
    State.INTAKE:{State.RESEARCH,State.BLOCKED},
    State.RESEARCH:{State.PLAN,State.BLOCKED,State.RECOVER},
    State.PLAN:{State.POLICY,State.RECOVER,State.BLOCKED},
    State.POLICY:{State.EXECUTE,State.RECOVER,State.BLOCKED},
    State.EXECUTE:{State.VERIFY,State.RECOVER,State.BLOCKED},
    State.VERIFY:{State.AUDIT,State.RECOVER,State.BLOCKED},
    State.AUDIT:{State.COMPLETE,State.RECOVER,State.BLOCKED},
    State.RECOVER:{State.RESEARCH,State.PLAN,State.POLICY,State.VERIFY,State.BLOCKED},
    State.BLOCKED:{State.RECOVER}, State.COMPLETE:set()
}

class PolicyDenied(ValueError): pass
class InvalidTransition(ValueError): pass

class NEXUS:
    """SQLite-backed deterministic workflow controller with audit events."""
    def __init__(self, database: str = "data/nexus.db"):
        self.database=database
        Path(database).parent.mkdir(parents=True,exist_ok=True)
        self._init_db()

    def _connect(self):
        con=sqlite3.connect(self.database)
        con.row_factory=sqlite3.Row
        con.execute("PRAGMA foreign_keys=ON")
        return con

    def _init_db(self):
        with self._connect() as con:
            con.executescript("""
            CREATE TABLE IF NOT EXISTS projects(project_id TEXT PRIMARY KEY,name TEXT NOT NULL,created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS tasks(task_id TEXT PRIMARY KEY,project_id TEXT NOT NULL REFERENCES projects(project_id),
              title TEXT NOT NULL,state TEXT NOT NULL,expected_outcome TEXT NOT NULL DEFAULT '',
              verification_method TEXT NOT NULL DEFAULT '',result TEXT NOT NULL DEFAULT '',error_code TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS evidence(evidence_id TEXT PRIMARY KEY,project_id TEXT NOT NULL REFERENCES projects(project_id),
              claim TEXT NOT NULL,status TEXT NOT NULL,source_url TEXT,inspected_at TEXT,notes TEXT NOT NULL DEFAULT '');
            CREATE TABLE IF NOT EXISTS audit_log(event_id TEXT PRIMARY KEY,project_id TEXT NOT NULL,task_id TEXT,
              event_type TEXT NOT NULL,from_state TEXT,to_state TEXT,actor TEXT NOT NULL,reason TEXT NOT NULL,
              created_at TEXT NOT NULL,details_json TEXT NOT NULL DEFAULT '{}');
            CREATE TABLE IF NOT EXISTS checkpoints(checkpoint_id TEXT PRIMARY KEY,task_id TEXT NOT NULL REFERENCES tasks(task_id),
              state TEXT NOT NULL,snapshot_json TEXT NOT NULL,created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS task_dependencies(
              task_id TEXT NOT NULL REFERENCES tasks(task_id),
              depends_on_task_id TEXT NOT NULL REFERENCES tasks(task_id),
              created_at TEXT NOT NULL,
              PRIMARY KEY(task_id,depends_on_task_id),
              CHECK(task_id <> depends_on_task_id)
            );
            CREATE INDEX IF NOT EXISTS idx_tasks_project ON tasks(project_id);
            CREATE INDEX IF NOT EXISTS idx_task_dependencies_depends_on ON task_dependencies(depends_on_task_id);
            CREATE INDEX IF NOT EXISTS idx_evidence_project ON evidence(project_id);
            CREATE INDEX IF NOT EXISTS idx_audit_task ON audit_log(task_id);
            """)
            evidence_columns={row["name"] for row in con.execute("PRAGMA table_info(evidence)")}
            if "task_id" not in evidence_columns:
                con.execute("ALTER TABLE evidence ADD COLUMN task_id TEXT REFERENCES tasks(task_id)")
            con.execute("CREATE INDEX IF NOT EXISTS idx_evidence_task ON evidence(task_id)")

    def _audit(self,con,project_id,task_id,event_type,actor,reason,from_state=None,to_state=None,details=None):
        con.execute("INSERT INTO audit_log VALUES(?,?,?,?,?,?,?,?,?,?)",
          (str(uuid.uuid4()),project_id,task_id,event_type,from_state,to_state,actor,reason,utc_now(),
           json.dumps(details or {},ensure_ascii=False,sort_keys=True)))

    def create_project(self,name:str)->dict[str,Any]:
        if not name.strip(): raise ValueError("project name is required")
        pid=str(uuid.uuid4())
        with self._connect() as con:
            con.execute("INSERT INTO projects VALUES(?,?,?)",(pid,name.strip(),utc_now()))
            self._audit(con,pid,None,"PROJECT_CREATED","user","Project initialized")
        return {"project_id":pid,"name":name.strip()}

    def create_task(self,project_id:str,title:str,expected_outcome:str="",verification_method:str="")->dict[str,Any]:
        if not title.strip(): raise ValueError("task title is required")
        now=utc_now(); tid=str(uuid.uuid4())
        with self._connect() as con:
            if not con.execute("SELECT 1 FROM projects WHERE project_id=?",(project_id,)).fetchone():
                raise ValueError("unknown project_id")
            con.execute("INSERT INTO tasks(task_id,project_id,title,state,expected_outcome,verification_method,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
              (tid,project_id,title.strip(),State.INTAKE.value,expected_outcome,verification_method,now,now))
            self._audit(con,project_id,tid,"TASK_CREATED","user","Task initialized",None,State.INTAKE.value)
        return self.get_task(tid)

    def get_task(self,task_id:str)->dict[str,Any]:
        with self._connect() as con:
            row=con.execute("SELECT * FROM tasks WHERE task_id=?",(task_id,)).fetchone()
            if not row: raise ValueError("unknown task_id")
            return dict(row)

    def add_task_dependency(self,task_id:str,depends_on_task_id:str,actor:str="user")->dict[str,Any]:
        """Add a same-project dependency while the task is still being planned; reject cycles."""
        if task_id == depends_on_task_id:
            raise PolicyDenied("a task cannot depend on itself")
        with self._connect() as con:
            task=con.execute("SELECT * FROM tasks WHERE task_id=?",(task_id,)).fetchone()
            if not task:
                raise ValueError("unknown task_id")
            dependency=con.execute("SELECT * FROM tasks WHERE task_id=?",(depends_on_task_id,)).fetchone()
            if not dependency:
                raise ValueError("unknown dependency task_id")
            if task["project_id"] != dependency["project_id"]:
                raise PolicyDenied("task dependencies must remain within the same project")
            if State(task["state"]) not in {State.INTAKE,State.RESEARCH,State.PLAN}:
                raise PolicyDenied("dependencies can only change before the policy gate")
            cycle=con.execute("""
                WITH RECURSIVE reachable(task_id) AS (
                    SELECT depends_on_task_id FROM task_dependencies WHERE task_id=?
                    UNION
                    SELECT d.depends_on_task_id FROM task_dependencies d
                    JOIN reachable r ON d.task_id=r.task_id
                )
                SELECT 1 FROM reachable WHERE task_id=? LIMIT 1
            """,(depends_on_task_id,task_id)).fetchone()
            if cycle:
                raise PolicyDenied("dependency would create a cycle")
            try:
                con.execute("INSERT INTO task_dependencies(task_id,depends_on_task_id,created_at) VALUES(?,?,?)",
                            (task_id,depends_on_task_id,utc_now()))
            except sqlite3.IntegrityError as exc:
                if con.execute("SELECT 1 FROM task_dependencies WHERE task_id=? AND depends_on_task_id=?",
                                (task_id,depends_on_task_id)).fetchone():
                    raise PolicyDenied("dependency already exists") from exc
                raise
            self._audit(con,task["project_id"],task_id,"TASK_DEPENDENCY_ADDED",actor,
                        "Task dependency added",task["state"],task["state"],
                        {"depends_on_task_id":depends_on_task_id})
        return {"task_id":task_id,"depends_on_task_id":depends_on_task_id,"status":dependency["state"]}

    def get_task_dependencies(self,task_id:str)->list[dict[str,Any]]:
        with self._connect() as con:
            task=con.execute("SELECT project_id FROM tasks WHERE task_id=?",(task_id,)).fetchone()
            if not task:
                raise ValueError("unknown task_id")
            rows=con.execute("""
                SELECT d.task_id,d.depends_on_task_id,d.created_at,t.title,t.state
                FROM task_dependencies d JOIN tasks t ON t.task_id=d.depends_on_task_id
                WHERE d.task_id=? ORDER BY d.created_at,d.depends_on_task_id
            """,(task_id,)).fetchall()
            return [dict(row) for row in rows]

    def add_evidence(self,project_id:str,claim:str,status:str,source_url:str|None=None,notes:str="",task_id:str|None=None)->dict[str,Any]:
        try: status=EvidenceStatus(status).value
        except ValueError as exc: raise ValueError("invalid evidence status") from exc
        if not claim.strip(): raise ValueError("claim is required")
        if status=="VERIFIED":
            raise PolicyDenied("Direct VERIFIED status is disabled; use the source verification workflow")
        eid=str(uuid.uuid4()); inspected=None
        with self._connect() as con:
            if not con.execute("SELECT 1 FROM projects WHERE project_id=?",(project_id,)).fetchone():
                raise ValueError("unknown project_id")
            if task_id and not con.execute("SELECT 1 FROM tasks WHERE task_id=? AND project_id=?",(task_id,project_id)).fetchone():
                raise ValueError("unknown task_id for project")
            con.execute("INSERT INTO evidence(evidence_id,project_id,claim,status,source_url,inspected_at,notes,task_id) VALUES(?,?,?,?,?,?,?,?)",
                        (eid,project_id,claim.strip(),status,source_url,inspected,notes,task_id))
            self._audit(con,project_id,task_id,"EVIDENCE_ADDED","user","Evidence status recorded",
                        details={"evidence_id":eid,"status":status,"scope":"TASK" if task_id else "PROJECT"})
        return {"evidence_id":eid,"project_id":project_id,"task_id":task_id,"scope":"TASK" if task_id else "PROJECT",
                "claim":claim.strip(),"status":status,"source_url":source_url,"inspected_at":inspected,"notes":notes}

    def add_verified_evidence(self,project_id:str,claim:str,source_url:str,quoted_text:str,
                              source_text:str,notes:str="",verified_by:str="source-verifier")->dict[str,Any]:
        """Deprecated insecure entry point; caller-supplied text is not proof of retrieval."""
        raise PolicyDenied("Caller-supplied source_text cannot establish VERIFIED evidence; use verify_and_add_evidence")

    def verify_and_add_evidence(self,project_id:str,claim:str,source_url:str,quoted_text:str,
                                notes:str="",verified_by:str="source-verifier",task_id:str|None=None)->dict[str,Any]:
        """Fetch and verify source content inside the trusted core boundary."""
        from nexus.evidence import EvidenceFetchError, verify_source_quote
        import hashlib
        if not claim.strip() or not quoted_text.strip():
            raise PolicyDenied("claim and quoted_text are required for verification")
        # Reject unknown projects before any outbound source fetch; recheck inside
        # the insert transaction to handle concurrent project deletion/mutation.
        with self._connect() as con:
            if not con.execute("SELECT 1 FROM projects WHERE project_id=?",(project_id,)).fetchone():
                raise ValueError("unknown project_id")
            if task_id and not con.execute("SELECT 1 FROM tasks WHERE task_id=? AND project_id=?",(task_id,project_id)).fetchone():
                raise ValueError("unknown task_id for project")
        try:
            fetched=verify_source_quote(source_url,quoted_text)
        except EvidenceFetchError:
            raise
        proof={"quoted_text":fetched["quoted_text"],
               "quote_sha256":hashlib.sha256(fetched["quoted_text"].strip().encode("utf-8")).hexdigest(),
               "verification_method":fetched["method"],"verified_by":verified_by,
               "source_text_chars":fetched["source_chars"]}
        eid=str(uuid.uuid4()); inspected=utc_now()
        with self._connect() as con:
            if not con.execute("SELECT 1 FROM projects WHERE project_id=?",(project_id,)).fetchone():
                raise ValueError("unknown project_id")
            if task_id and not con.execute("SELECT 1 FROM tasks WHERE task_id=? AND project_id=?",(task_id,project_id)).fetchone():
                raise ValueError("unknown task_id for project")
            con.execute("INSERT INTO evidence(evidence_id,project_id,claim,status,source_url,inspected_at,notes,task_id) VALUES(?,?,?,?,?,?,?,?)",
                        (eid,project_id,claim.strip(),EvidenceStatus.VERIFIED.value,source_url,inspected,
                         json.dumps({"operator_notes":notes,"verification":proof},ensure_ascii=False,sort_keys=True),task_id))
            self._audit(con,project_id,task_id,"EVIDENCE_VERIFIED","source-verifier","Exact quote matched trusted fetched source",
                        details={"evidence_id":eid,"quote_sha256":proof["quote_sha256"],"source_url":source_url,
                                 "scope":"TASK" if task_id else "PROJECT"})
        return {"evidence_id":eid,"project_id":project_id,"task_id":task_id,"scope":"TASK" if task_id else "PROJECT",
                "claim":claim.strip(),"status":"VERIFIED","source_url":source_url,"inspected_at":inspected,"verification":proof}

    def transition(self,task_id:str,to_state:str,actor:str="system",reason:str="",result:str|None=None,error_code:str|None=None)->dict[str,Any]:
        try: target=State(to_state)
        except ValueError as exc: raise InvalidTransition("unknown target state") from exc
        with self._connect() as con:
            row=con.execute("SELECT * FROM tasks WHERE task_id=?",(task_id,)).fetchone()
            if not row: raise ValueError("unknown task_id")
            current=State(row["state"])
            if target not in ALLOWED_TRANSITIONS[current]:
                raise InvalidTransition(f"transition {current.value} -> {target.value} is not allowed")
            if target==State.PLAN:
                n=con.execute("SELECT COUNT(*) FROM evidence WHERE project_id=? AND status='VERIFIED' AND (task_id=? OR task_id IS NULL)",(row["project_id"],task_id)).fetchone()[0]
                if n<1: raise PolicyDenied("PLAN requires at least one VERIFIED evidence item")
            if target==State.EXECUTE:
                if not row["expected_outcome"].strip() or not row["verification_method"].strip():
                    raise PolicyDenied("EXECUTE requires expected_outcome and verification_method")
                pending=con.execute("""
                    SELECT d.depends_on_task_id,t.state FROM task_dependencies d
                    JOIN tasks t ON t.task_id=d.depends_on_task_id
                    WHERE d.task_id=? AND t.state <> ?
                """,(task_id,State.COMPLETE.value)).fetchall()
                if pending:
                    raise PolicyDenied("EXECUTE requires all task dependencies to be COMPLETE")
            if target==State.COMPLETE and (current!=State.AUDIT or not (result or row["result"]).strip()):
                raise PolicyDenied("COMPLETE requires AUDIT state and a recorded result")
            now=utc_now()
            con.execute("UPDATE tasks SET state=?,updated_at=?,result=COALESCE(?,result),error_code=COALESCE(?,error_code) WHERE task_id=?",
              (target.value,now,result,error_code,task_id))
            self._audit(con,row["project_id"],task_id,"STATE_TRANSITION",actor,reason or "No reason supplied",
                        current.value,target.value,{"error_code":error_code} if error_code else {})
            return dict(con.execute("SELECT * FROM tasks WHERE task_id=?",(task_id,)).fetchone())

    def checkpoint(self,task_id:str)->dict[str,Any]:
        task=self.get_task(task_id); cid=str(uuid.uuid4())
        with self._connect() as con:
            con.execute("INSERT INTO checkpoints VALUES(?,?,?,?,?)",(cid,task_id,task["state"],json.dumps(task,sort_keys=True),utc_now()))
            self._audit(con,task["project_id"],task_id,"CHECKPOINT_CREATED","system","Explicit checkpoint",
                        task["state"],task["state"],{"checkpoint_id":cid})
        return {"checkpoint_id":cid,"task_id":task_id,"state":task["state"]}

    def record_router_checkpoint(self,task_id:str,snapshot:dict[str,Any],actor:str="tool-router")->dict[str,Any]:
        """Persist a router stage checkpoint and audit event in one SQLite transaction."""
        cid=str(uuid.uuid4())
        with self._connect() as con:
            task=con.execute("SELECT * FROM tasks WHERE task_id=?",(task_id,)).fetchone()
            if not task:
                raise ValueError("unknown task_id")
            task_data=dict(task)
            payload={"task":task_data,"router_checkpoint":snapshot}
            state=task_data["state"]
            created=utc_now()
            con.execute("INSERT INTO checkpoints VALUES(?,?,?,?,?)",
                        (cid,task_id,state,json.dumps(payload,ensure_ascii=False,sort_keys=True,default=str),created))
            self._audit(con,task_data["project_id"],task_id,"ROUTER_CHECKPOINT_CREATED",actor,
                        "Tool Router stage checkpoint persisted",state,state,
                        {"checkpoint_id":cid,"stage":snapshot.get("stage"),"candidate_id":snapshot.get("candidate_id")})
        return {"checkpoint_id":cid,"task_id":task_id,"state":state,"created_at":created}

    def restore_checkpoint(self,task_id:str,checkpoint_id:str,actor:str="system",reason:str="Approved recovery") -> dict[str,Any]:
        """Restore safe workflow metadata from a checkpoint; never auto-resume EXECUTE."""
        safe_states={State.RESEARCH,State.PLAN,State.POLICY,State.VERIFY,State.AUDIT}
        with self._connect() as con:
            task=con.execute("SELECT * FROM tasks WHERE task_id=?",(task_id,)).fetchone()
            if not task: raise ValueError("unknown task_id")
            checkpoint=con.execute("SELECT * FROM checkpoints WHERE checkpoint_id=? AND task_id=?",
                                   (checkpoint_id,task_id)).fetchone()
            if not checkpoint: raise ValueError("unknown checkpoint for task")
            current=State(task["state"]); target=State(checkpoint["state"])
            if current not in {State.BLOCKED,State.RECOVER}:
                raise PolicyDenied("restore requires task state BLOCKED or RECOVER")
            if target not in safe_states:
                raise PolicyDenied("checkpoint state is not safe for automatic restore")
            snapshot=json.loads(checkpoint["snapshot_json"])
            # Restore only workflow metadata. Never restore side-effecting execution as if it had not run.
            now=utc_now()
            con.execute("UPDATE tasks SET state=?,expected_outcome=?,verification_method=?,result=?,error_code=?,updated_at=? WHERE task_id=?",
                        (target.value,snapshot.get("expected_outcome",""),snapshot.get("verification_method",""),
                         snapshot.get("result",""),snapshot.get("error_code",""),now,task_id))
            self._audit(con,task["project_id"],task_id,"CHECKPOINT_RESTORED",actor,reason,
                        current.value,target.value,{"checkpoint_id":checkpoint_id,"safe_restore":True})
            return dict(con.execute("SELECT * FROM tasks WHERE task_id=?",(task_id,)).fetchone())

    def audit(self,project_id:str,task_id:str|None=None)->list[dict[str,Any]]:
        with self._connect() as con:
            if not con.execute("SELECT 1 FROM projects WHERE project_id=?",(project_id,)).fetchone():
                raise ValueError("unknown project_id")
            if task_id:
                rows=con.execute("SELECT * FROM audit_log WHERE project_id=? AND task_id=? ORDER BY created_at",(project_id,task_id))
            else: rows=con.execute("SELECT * FROM audit_log WHERE project_id=? ORDER BY created_at",(project_id,))
            return [dict(r) for r in rows]

    def policy_route(self,candidates:list[dict[str,Any]],allow_paid:bool=False,budget_approved:bool=False)->dict[str,Any]:
        usable=[c for c in candidates if c.get("enabled") and c.get("permission_ok") and c.get("capability_ok") and not c.get("warning")]
        free=[c for c in usable if c.get("cost_tier","free")=="free"]
        if free: return {"decision":"ALLOW","selected":free[0].get("id"),"reason":"first eligible free candidate"}
        paid=[c for c in usable if c.get("cost_tier")=="paid"]
        if paid and allow_paid and budget_approved:
            return {"decision":"ALLOW","selected":paid[0].get("id"),"reason":"paid tool explicitly approved"}
        return {"decision":"BLOCK","selected":None,"reason":"no eligible free candidate; paid tool missing explicit approval or unavailable"}

    def status(self,project_id:str)->dict[str,Any]:
        with self._connect() as con:
            p=con.execute("SELECT * FROM projects WHERE project_id=?",(project_id,)).fetchone()
            if not p: raise ValueError("unknown project_id")
            tasks=[dict(r) for r in con.execute("SELECT * FROM tasks WHERE project_id=? ORDER BY created_at",(project_id,))]
            evidence=[dict(r) for r in con.execute("SELECT * FROM evidence WHERE project_id=? ORDER BY inspected_at",(project_id,))]
            return {"project":dict(p),"task_counts":{s.value:sum(t["state"]==s.value for t in tasks) for s in State},
              "tasks":tasks,"evidence_count":len(evidence),
              "evidence_status_counts":{s.value:sum(e["status"]==s.value for e in evidence) for s in EvidenceStatus}}
