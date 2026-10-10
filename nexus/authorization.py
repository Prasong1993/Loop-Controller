"""Project-level authorization registry.

Tokens authenticate principals; project membership authorizes access. The legacy
single shared API key intentionally maps to one shared principal and therefore
must not be treated as multi-tenant identity.
"""
from pathlib import Path
import sqlite3

class ProjectAuthorization:
    def __init__(self,database:str="data/nexus.db"):
        self.database=database
        Path(database).parent.mkdir(parents=True,exist_ok=True)
        with self._connect() as con:
            con.execute("""CREATE TABLE IF NOT EXISTS project_members(
                project_id TEXT NOT NULL,
                principal TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('OWNER','MEMBER','READ_ONLY')),
                created_at TEXT NOT NULL,
                PRIMARY KEY(project_id,principal)
            )""")
            con.execute("CREATE INDEX IF NOT EXISTS idx_project_members_principal ON project_members(principal,project_id)")

    def _connect(self):
        con=sqlite3.connect(self.database,timeout=10)
        con.execute("PRAGMA busy_timeout=10000")
        return con

    def grant_owner(self,project_id:str,principal:str)->None:
        if not project_id.strip() or not principal.strip():
            raise ValueError("project_id and principal are required")
        from datetime import datetime,timezone
        with self._connect() as con:
            con.execute("""INSERT INTO project_members(project_id,principal,role,created_at)
                VALUES(?,?, 'OWNER', ?) ON CONFLICT(project_id,principal) DO UPDATE SET role='OWNER'""",
                (project_id,principal,datetime.now(timezone.utc).isoformat()))

    def has_access(self,project_id:str,principal:str)->bool:
        with self._connect() as con:
            row=con.execute("SELECT role FROM project_members WHERE project_id=? AND principal=?",
                (project_id,principal)).fetchone()
            return bool(row and row[0] in {"OWNER","MEMBER","READ_ONLY"})

    def can_write(self,project_id:str,principal:str)->bool:
        with self._connect() as con:
            row=con.execute("SELECT role FROM project_members WHERE project_id=? AND principal=?",
                (project_id,principal)).fetchone()
            return bool(row and row[0] in {"OWNER","MEMBER"})

