"""Remote MCP adapter for the NEXUS controller.

Run with: uvicorn nexus.mcp_server:app --host 0.0.0.0 --port 8000
Set NEXUS_API_KEY before any remote exposure. This adapter is designed for
ChatGPT MCP app configuration but is not registered/deployed automatically.
"""
from __future__ import annotations
import hmac
import os
import time
import uuid
import json
from contextvars import ContextVar
import functools
import inspect
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Scope, Receive, Send
from mcp.server.fastmcp import FastMCP
from nexus.core import NEXUS, PolicyDenied
from nexus.records import RecordStore
from nexus.authorization import ProjectAuthorization
from nexus.evidence import EvidenceFetchError
from nexus.version import VERSION

controller=NEXUS(os.getenv("NEXUS_DB","data/nexus.db"))
record_store=RecordStore(os.getenv("NEXUS_RECORDS_DB",os.getenv("NEXUS_DB","data/nexus.db")))
project_authorization=ProjectAuthorization(os.getenv("NEXUS_AUTHZ_DB",os.getenv("NEXUS_DB","data/nexus.db")))
current_principal=ContextVar("nexus_mcp_principal",default=None)

def track_tool(fn):
    """Automatically record MCP tool usage and failures without persisting arguments."""
    signature=inspect.signature(fn)
    @functools.wraps(fn)
    def wrapped(*args,**kwargs):
        started=time.monotonic()
        trace_id=str(uuid.uuid4())
        bound=signature.bind_partial(*args,**kwargs)
        values=bound.arguments
        project_id=str(values.get("project_id") or "system")
        task_id=values.get("task_id")
        if not values.get("project_id") and task_id:
            try:
                task_row=controller.get_task(str(task_id))
                project_id=str(task_row.get("project_id") or "system")
            except Exception:
                pass
        outcome="SUCCESS"
        error_code=None
        principal=current_principal.get()
        try:
            # Mandatory start record must be durable before any tool can mutate state.
            record_store.append(project_id=project_id,task_id=task_id,record_type="usage",
                trace_id=trace_id,actor_type="tool",actor_id=principal,component="mcp_server",
                status="STARTED",summary=f"MCP tool {fn.__name__} started",
                payload={"operation":fn.__name__,"phase":"TOOL_STARTED"})
            if principal and fn.__name__!="nexus_health":
                scoped_project=str(values.get("project_id") or "")
                if task_id:
                    task_row=controller.get_task(str(task_id))
                    if scoped_project and scoped_project!=task_row["project_id"]:
                        raise PolicyDenied("task_id does not belong to project_id")
                    scoped_project=task_row["project_id"]
                if scoped_project and not project_authorization.has_access(scoped_project,principal):
                    raise PolicyDenied("principal is not a member of this project")
            result=fn(*args,**kwargs)
            if fn.__name__=="nexus_create_project":
                project_authorization.grant_owner(result["project_id"],principal or "legacy-shared")
            return result
        except Exception as exc:
            outcome="FAILED"
            error_code=type(exc).__name__.upper()[:80]
            try:
                record_store.append(project_id=project_id,task_id=task_id,
                    record_type="error",trace_id=trace_id,actor_type="tool",
                    component="mcp_server",status="FAILED",error_code=error_code,
                    severity="medium",summary=f"MCP tool {fn.__name__} failed",
                    payload={"category":"tool","tool":fn.__name__,
                             "exception_class":type(exc).__name__,"retryable":False})
            except Exception:
                pass
            raise
        finally:
            try:
                record_store.append(project_id=project_id,task_id=task_id,
                    record_type="usage",trace_id=trace_id,actor_type="tool",
                    component="mcp_server",status=outcome,
                    summary=f"MCP tool {fn.__name__}",
                    payload={"operation":fn.__name__,"duration_ms":max(0,int((time.monotonic()-started)*1000)),
                             "outcome":outcome,"error_code":error_code})
            except Exception:
                pass
    return wrapped
mcp=FastMCP("NEXUS Controller",stateless_http=True,json_response=True)

@mcp.tool()
@track_tool
def nexus_health()->dict:
    """Return controller liveness and integration version."""
    return {"status":"ok","service":"nexus-controller","version":VERSION}

@mcp.tool()
@track_tool
def nexus_create_project(name:str)->dict:
    """Create a project and return its project_id."""
    return controller.create_project(name)

@mcp.tool()
@track_tool
def nexus_create_task(project_id:str,title:str,expected_outcome:str,verification_method:str)->dict:
    """Create a workflow task with explicit outcome and verification criteria."""
    return controller.create_task(project_id,title,expected_outcome,verification_method)

@mcp.tool()
@track_tool
def nexus_get_task(task_id:str)->dict:
    """Read a task's current state and recorded result."""
    return controller.get_task(task_id)

@mcp.tool()
@track_tool
def nexus_add_task_dependency(task_id:str,depends_on_task_id:str)->dict:
    """Add a same-project dependency before the policy gate; cycles and cross-project links are denied."""
    return controller.add_task_dependency(task_id,depends_on_task_id,"chatgpt")

@mcp.tool()
@track_tool
def nexus_get_task_dependencies(task_id:str)->list[dict]:
    """Read a task's dependency list and current dependency states."""
    return controller.get_task_dependencies(task_id)

@mcp.tool()
@track_tool
def nexus_get_project_status(project_id:str)->dict:
    """Read project status, task counts and evidence counts."""
    return controller.status(project_id)

@mcp.tool()
@track_tool
def nexus_transition_task(task_id:str,to_state:str,actor:str="chatgpt",reason:str="",result:str|None=None,error_code:str|None=None)->dict:
    """Request a policy-gated state transition. Policy denials must not be retried blindly."""
    return controller.transition(task_id,to_state,actor,reason,result,error_code)

@mcp.tool()
@track_tool
def nexus_create_checkpoint(task_id:str)->dict:
    """Create an auditable checkpoint for a task."""
    return controller.checkpoint(task_id)

@mcp.tool()
@track_tool
def nexus_restore_checkpoint(task_id:str,checkpoint_id:str,reason:str="Approved recovery")->dict:
    """Restore safe workflow metadata only from BLOCKED/RECOVER; EXECUTE checkpoints are never replayed."""
    return controller.restore_checkpoint(task_id,checkpoint_id,"chatgpt",reason)

@mcp.tool()
@track_tool
def nexus_add_unverified_evidence(project_id:str,claim:str,status:str,source_url:str|None=None,notes:str="",task_id:str|None=None)->dict:
    """Record RECOVERED, UNKNOWN or BLOCKED evidence. VERIFIED is prohibited here; use source quote verification."""
    if status=="VERIFIED":
        raise PolicyDenied("Use nexus_verify_source_evidence to record VERIFIED evidence")
    return controller.add_evidence(project_id,claim,status,source_url,notes,task_id)

@mcp.tool()
@track_tool
def nexus_verify_source_evidence(project_id:str,claim:str,source_url:str,quoted_text:str,notes:str="",task_id:str|None=None)->dict:
    """Fetch and verify source content inside the trusted core boundary."""
    return controller.verify_and_add_evidence(project_id,claim,source_url,quoted_text,notes,"chatgpt-source-verifier",task_id)

@mcp.tool()
@track_tool
def nexus_read_audit(project_id:str,task_id:str|None=None)->list[dict]:
    """Read audit events for a project, optionally filtered by task_id."""
    return controller.audit(project_id,task_id)


@mcp.tool()
@track_tool
def nexus_search_records(project_id:str,record_type:str|None=None,task_id:str|None=None,
                         trace_id:str|None=None,operation_id:str|None=None,status:str|None=None,
                         error_code:str|None=None,component:str|None=None,query:str|None=None,
                         limit:int=100,offset:int=0)->dict:
    """Search structured usage/error/evidence/decision/checkpoint/verification records."""
    return record_store.search(project_id=project_id,record_type=record_type,task_id=task_id,
        trace_id=trace_id,operation_id=operation_id,status=status,error_code=error_code,
        component=component,query=query,limit=limit,offset=offset)

@mcp.tool()
@track_tool
def nexus_select_route(candidates:list[dict],allow_paid:bool=False,budget_approved:bool=False)->dict:
    """Select an eligible route; does not execute a provider. Paid routes need both approvals."""
    return controller.policy_route(candidates,allow_paid,budget_approved)

_mcp_rate_limit_state={}
class BearerGateMiddleware:
    """Authenticate a principal, apply a process-local request limit, and scope tool calls."""
    def __init__(self,app:ASGIApp):
        self.app=app
    async def __call__(self,scope:Scope,receive:Receive,send:Send):
        if scope["type"] != "http":
            await self.app(scope,receive,send); return
        headers={k.lower():v.decode("latin1") for k,v in scope.get("headers",[])}
        auth=headers.get(b"authorization".lower(),"")
        expected=os.getenv("NEXUS_API_KEY","").strip()
        token_map_raw=os.getenv("NEXUS_API_TOKENS","").strip()
        client=scope.get("client")
        host=client[0] if client else "unknown"
        principal=None
        if token_map_raw:
            try:
                token_map=json.loads(token_map_raw)
            except json.JSONDecodeError:
                response=JSONResponse({"error":"NEXUS_API_TOKENS must be valid JSON"},status_code=503)
                await response(scope,receive,send); return
            token=auth[7:].strip() if auth.startswith("Bearer ") else ""
            principal=token_map.get(token) if isinstance(token_map,dict) else None
            if not isinstance(principal,str) or not principal.strip():
                response=JSONResponse({"error":"Bearer token required or invalid"},status_code=401)
                await response(scope,receive,send); return
        elif not expected:
            if host not in {"127.0.0.1","::1","localhost","testclient"}:
                response=JSONResponse({"error":"Remote MCP disabled: configure NEXUS_API_KEY"},status_code=503)
                await response(scope,receive,send); return
            principal="local-development"
        elif not auth.startswith("Bearer ") or not hmac.compare_digest(auth[7:].strip(),expected):
            response=JSONResponse({"error":"Bearer token required or invalid"},status_code=401)
            await response(scope,receive,send); return
        else:
            principal="legacy-shared"
        try:
            limit=max(1,int(os.getenv("NEXUS_RATE_LIMIT_PER_MINUTE","120")))
        except ValueError:
            response=JSONResponse({"error":"RATE_LIMIT_CONFIG_INVALID"},status_code=503)
            await response(scope,receive,send); return
        now=time.monotonic()
        window,count=_mcp_rate_limit_state.get(host,(now,0))
        if now-window>=60:
            window,count=now,0
        if count>=limit:
            response=JSONResponse({"error":"RATE_LIMIT_EXCEEDED","retry_after_seconds":max(1,int(60-(now-window)))},status_code=429)
            await response(scope,receive,send); return
        _mcp_rate_limit_state[host]=(window,count+1)
        token=current_principal.set(principal)
        try:
            await self.app(scope,receive,send)
        finally:
            current_principal.reset(token)

app=mcp.streamable_http_app()
app.add_middleware(BearerGateMiddleware)
