"""HTTP API for the NEXUS deterministic core.

Security: set NEXUS_API_KEY for remote access. Without it, non-loopback
requests fail closed. /health is intentionally unauthenticated and reveals
only liveness/version metadata.
"""
import hmac
import os
import json
import time
import uuid
from nexus.records import RecordStore
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field
from nexus.core import NEXUS, PolicyDenied
from nexus.evidence import EvidenceFetchError, verify_source_quote

app=FastAPI(title="NEXUS Controller API",version="0.2.0",
 description="Evidence-first deterministic workflow controller")
controller=NEXUS(os.getenv("NEXUS_DB","data/nexus.db"))
record_store=RecordStore(os.getenv("NEXUS_RECORDS_DB",os.getenv("NEXUS_DB","data/nexus.db")))

@app.middleware("http")
async def operational_record_middleware(request: Request, call_next):
    """Capture every REST request outcome without storing raw bodies or secrets."""
    started=time.monotonic()
    trace_id=request.headers.get("x-request-id","").strip()
    if not trace_id or len(trace_id)>128:
        trace_id=str(uuid.uuid4())
    try:
        response=await call_next(request)
        status_code=response.status_code
        return response
    except Exception as exc:
        status_code=500
        try:
            record_store.append(project_id="system",record_type="error",
                trace_id=trace_id,actor_type="system",component="rest_api",
                status="FAILED",error_code="HTTP_UNHANDLED_EXCEPTION",severity="high",
                summary="Unhandled REST request exception",
                payload={"category":"internal","exception_class":type(exc).__name__,
                         "method":request.method,"path":request.url.path,
                         "retryable":False,"http_status":500})
        except Exception:
            pass
        raise
    finally:
        elapsed=max(0,int((time.monotonic()-started)*1000))
        project_id="system"
        task_id=None
        segments=[part for part in request.url.path.split("/") if part]
        if len(segments)>=2 and segments[0]=="projects":
            project_id=segments[1]
        elif len(segments)>=2 and segments[0]=="tasks":
            task_id=segments[1]
        try:
            record_store.append(project_id=project_id,task_id=task_id,
                record_type="usage",trace_id=trace_id,actor_type="system",
                component="rest_api",status="SUCCESS" if status_code<400 else "FAILED",
                summary=f"{request.method} {request.url.path}",
                payload={"operation":request.method,"path":request.url.path,
                         "http_status":status_code,"duration_ms":elapsed,
                         "outcome":"success" if status_code<400 else "failure"})
            if status_code>=400:
                record_store.append(project_id=project_id,task_id=task_id,
                    record_type="error",trace_id=trace_id,actor_type="system",
                    component="rest_api",status="FAILED",error_code=f"HTTP_STATUS_{status_code}",
                    severity="medium" if status_code<500 else "high",
                    summary=f"REST request returned HTTP {status_code}",
                    payload={"category":"http","method":request.method,
                             "path":request.url.path,"http_status":status_code,
                             "retryable":False})
        except Exception:
            # Observability must not turn a successful business operation into a failed request.
            pass

class ProjectIn(BaseModel):
    name:str=Field(min_length=1,max_length=200)
class TaskIn(BaseModel):
    project_id:str
    title:str=Field(min_length=1,max_length=500)
    expected_outcome:str=""
    verification_method:str=""
class EvidenceIn(BaseModel):
    project_id:str
    claim:str=Field(min_length=1,max_length=2000)
    status:str
    source_url:str|None=None
    notes:str=""
class VerifyEvidenceIn(BaseModel):
    project_id:str
    claim:str=Field(min_length=1,max_length=2000)
    source_url:str=Field(min_length=1,max_length=2000)
    quoted_text:str=Field(min_length=1,max_length=5000)
    notes:str=""
class TransitionIn(BaseModel):
    to_state:str
    actor:str="api"
    reason:str=""
    result:str|None=None
    error_code:str|None=None
class RouteIn(BaseModel):
    candidates:list[dict]
    allow_paid:bool=False
    budget_approved:bool=False
class RestoreIn(BaseModel):
    checkpoint_id:str=Field(min_length=1)
    actor:str="api"
    reason:str="Approved recovery"

def require_api_key(request:Request, authorization:str|None=Header(default=None)):
    expected=os.getenv("NEXUS_API_KEY","").strip()
    if not expected:
        host=request.client.host if request.client else ""
        if host in {"127.0.0.1","::1","localhost","testclient"}:
            return "local-development"
        raise HTTPException(status_code=503,detail="Remote API disabled: configure NEXUS_API_KEY")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401,detail="Bearer token required")
    supplied=authorization[7:].strip()
    if not hmac.compare_digest(supplied,expected):
        raise HTTPException(status_code=403,detail="Invalid API token")
    return "authenticated"

def invoke(fn,*args,**kwargs):
    try: return fn(*args,**kwargs)
    except PolicyDenied as exc: raise HTTPException(status_code=403,detail=str(exc)) from exc
    except ValueError as exc:
        message=str(exc)
        status=404 if message.startswith("unknown ") else 409
        raise HTTPException(status_code=status,detail=message) from exc

@app.get("/health")
def health(): return {"status":"ok","service":"nexus-controller","version":"0.2.0"}

@app.post("/projects",status_code=201,dependencies=[Depends(require_api_key)])
def create_project(body:ProjectIn): return invoke(controller.create_project,body.name)
@app.get("/projects/{project_id}/status",dependencies=[Depends(require_api_key)])
def project_status(project_id:str): return invoke(controller.status,project_id)
@app.post("/tasks",status_code=201,dependencies=[Depends(require_api_key)])
def create_task(body:TaskIn):
    return invoke(controller.create_task,body.project_id,body.title,body.expected_outcome,body.verification_method)
@app.get("/tasks/{task_id}",dependencies=[Depends(require_api_key)])
def get_task(task_id:str): return invoke(controller.get_task,task_id)
@app.post("/tasks/{task_id}/transition",dependencies=[Depends(require_api_key)])
def transition(task_id:str,body:TransitionIn):
    return invoke(controller.transition,task_id,body.to_state,body.actor,body.reason,body.result,body.error_code)
@app.post("/tasks/{task_id}/checkpoint",dependencies=[Depends(require_api_key)])
def checkpoint(task_id:str): return invoke(controller.checkpoint,task_id)
@app.post("/tasks/{task_id}/restore",dependencies=[Depends(require_api_key)])
def restore_checkpoint(task_id:str,body:RestoreIn):
    return invoke(controller.restore_checkpoint,task_id,body.checkpoint_id,body.actor,body.reason)
@app.post("/evidence",dependencies=[Depends(require_api_key)])
def add_evidence(body:EvidenceIn):
    return invoke(controller.add_evidence,body.project_id,body.claim,body.status,body.source_url,body.notes)

@app.post("/evidence/verify",dependencies=[Depends(require_api_key)])
def verify_evidence(body:VerifyEvidenceIn):
    try:
        proof=verify_source_quote(body.source_url,body.quoted_text)
    except EvidenceFetchError as exc:
        raise HTTPException(status_code=422,detail=str(exc)) from exc
    return invoke(controller.add_verified_evidence,body.project_id,body.claim,body.source_url,
                  proof["quoted_text"],proof["source_text"],body.notes,"api-source-verifier")
@app.get("/projects/{project_id}/audit",dependencies=[Depends(require_api_key)])
def audit(project_id:str,task_id:str|None=None): return invoke(controller.audit,project_id,task_id)
@app.post("/policy/route",dependencies=[Depends(require_api_key)])
def route(body:RouteIn): return controller.policy_route(body.candidates,body.allow_paid,body.budget_approved)
