"""HTTP API for the NEXUS deterministic core.

Security: set NEXUS_API_KEY for remote access. Without it, non-loopback
requests fail closed. /health is intentionally unauthenticated and reveals
only liveness/version metadata.
"""
import hmac
import os
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field
from nexus.core import NEXUS, PolicyDenied
from nexus.evidence import EvidenceFetchError, verify_source_quote

app=FastAPI(title="NEXUS Controller API",version="0.2.0",
 description="Evidence-first deterministic workflow controller")
controller=NEXUS(os.getenv("NEXUS_DB","data/nexus.db"))

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
