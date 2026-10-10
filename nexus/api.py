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
from nexus.authorization import ProjectAuthorization
from nexus.idempotency import IdempotencyStore, IdempotencyConflict, IdempotencyInProgress
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from nexus.core import NEXUS, PolicyDenied
from nexus.evidence import EvidenceFetchError
from nexus.openai_adapter import OpenAIResponsesWorker, OpenAIWorkerError
from nexus.openai_planner import OpenAIPlanGenerator, OpenAIPlanError
from nexus.code_proposal import OpenAICodeProposalGenerator, CodeProposalError
from nexus.version import VERSION

app=FastAPI(title="NEXUS Controller API",version=VERSION,
 description="Evidence-first deterministic workflow controller")
controller=NEXUS(os.getenv("NEXUS_DB","data/nexus.db"))
record_store=RecordStore(os.getenv("NEXUS_RECORDS_DB",os.getenv("NEXUS_DB","data/nexus.db")))
idempotency_store=IdempotencyStore(os.getenv("NEXUS_IDEMPOTENCY_DB",os.getenv("NEXUS_DB","data/nexus.db")))
project_authorization=ProjectAuthorization(os.getenv("NEXUS_AUTHZ_DB",os.getenv("NEXUS_DB","data/nexus.db")))
plan_generator=OpenAIPlanGenerator(record_store)
code_proposal_generator=OpenAICodeProposalGenerator(record_store)

_rate_limit_state={}
@app.middleware("http")
async def operational_record_middleware(request: Request, call_next):
    """Rate-limit requests and persist a mandatory start record before business execution."""
    started=time.monotonic()
    trace_id=request.headers.get("x-request-id","").strip()
    if not trace_id or len(trace_id)>128:
        trace_id=str(uuid.uuid4())
    request.state.trace_id=trace_id
    host=request.client.host if request.client else "unknown"
    now=time.monotonic()
    try:
        limit=max(1,int(os.getenv("NEXUS_RATE_LIMIT_PER_MINUTE","120")))
    except ValueError:
        return JSONResponse(status_code=503,content={"code":"RATE_LIMIT_CONFIG_INVALID"})
    window,count=_rate_limit_state.get(host,(now,0))
    if now-window>=60:
        window,count=now,0
    if count>=limit:
        try:
            record_store.append(project_id="system",record_type="error",trace_id=trace_id,
                actor_type="system",component="rest_api",status="BLOCKED",error_code="RATE_LIMIT_EXCEEDED",
                severity="medium",summary="REST request rejected by rate limiter",
                payload={"method":request.method,"path":request.url.path,"retryable":True,"http_status":429})
        except Exception:
            return JSONResponse(status_code=503,content={"code":"MANDATORY_AUDIT_UNAVAILABLE"})
        return JSONResponse(status_code=429,content={"code":"RATE_LIMIT_EXCEEDED","retry_after_seconds":max(1,int(60-(now-window)))})
    _rate_limit_state[host]=(window,count+1)
    try:
        record_store.append(project_id="system",record_type="usage",trace_id=trace_id,
            actor_type="system",component="rest_api",status="STARTED",
            summary=f"{request.method} {request.url.path} request accepted for processing",
            payload={"operation":request.method,"path":request.url.path,"phase":"REQUEST_STARTED"})
    except Exception:
        return JSONResponse(status_code=503,content={"code":"MANDATORY_AUDIT_UNAVAILABLE",
            "message":"Request was not executed because mandatory start-audit persistence failed."})
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
        task_id=getattr(request.state,"task_id",None)
        segments=[part for part in request.url.path.split("/") if part]
        if getattr(request.state,"project_id",None):
            project_id=request.state.project_id
        elif len(segments)>=2 and segments[0]=="projects":
            project_id=segments[1]
        elif len(segments)>=2 and segments[0]=="tasks":
            task_id=segments[1]
            try:
                task_row=controller.get_task(task_id)
                project_id=task_row["project_id"]
            except Exception:
                pass
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
    @field_validator("name")
    @classmethod
    def nonblank_name(cls,value):
        if not value.strip(): raise ValueError("name must not be blank")
        return value.strip()
class TaskIn(BaseModel):
    project_id:str=Field(min_length=1,max_length=200)
    title:str=Field(min_length=1,max_length=500)
    expected_outcome:str=""
    verification_method:str=""
    @field_validator("project_id","title")
    @classmethod
    def nonblank_task_fields(cls,value):
        if not value.strip(): raise ValueError("field must not be blank")
        return value.strip()
class EvidenceIn(BaseModel):
    project_id:str=Field(min_length=1,max_length=200)
    claim:str=Field(min_length=1,max_length=2000)
    status:str
    source_url:str|None=None
    notes:str=""
    task_id:str|None=None
    @field_validator("project_id","claim")
    @classmethod
    def nonblank_evidence_fields(cls,value):
        if not value.strip(): raise ValueError("field must not be blank")
        return value.strip()
class VerifyEvidenceIn(BaseModel):
    project_id:str=Field(min_length=1,max_length=200)
    claim:str=Field(min_length=1,max_length=2000)
    source_url:str=Field(min_length=1,max_length=2000)
    quoted_text:str=Field(min_length=1,max_length=5000)
    notes:str=""
    task_id:str|None=None
    @field_validator("project_id","claim","source_url","quoted_text")
    @classmethod
    def nonblank_verification_fields(cls,value):
        if not value.strip(): raise ValueError("field must not be blank")
        return value.strip()
class TransitionIn(BaseModel):
    to_state:str
    actor:str="api"
    reason:str=""
    result:str|None=None
    error_code:str|None=None
class VerificationIn(BaseModel):
    evidence_id:str=Field(min_length=1,max_length=200)
    verifier:str=Field(min_length=1,max_length=200)
    result_sha256:str=""
    notes:str=""
    @field_validator("evidence_id","verifier")
    @classmethod
    def nonblank_verification_values(cls,value):
        if not value.strip(): raise ValueError("field must not be blank")
        return value.strip()
class RouteIn(BaseModel):
    candidates:list[dict]
    allow_paid:bool=False
    budget_approved:bool=False
class RestoreIn(BaseModel):
    checkpoint_id:str=Field(min_length=1)
    actor:str="api"
    reason:str="Approved recovery"
class DependencyIn(BaseModel):
    depends_on_task_id:str=Field(min_length=1,max_length=200)
    @field_validator("depends_on_task_id")
    @classmethod
    def nonblank_dependency_id(cls,value):
        if not value.strip(): raise ValueError("depends_on_task_id must not be blank")
        return value.strip()
class AIPlanIn(BaseModel):
    project_id:str=Field(min_length=1,max_length=200)
    task:str=Field(min_length=1,max_length=20000)
    constraints:list[str]=Field(default_factory=list,max_length=100)
    capabilities:list[str]=Field(default_factory=list,max_length=2)
    budget_approved:bool=False
    @field_validator("project_id","task")
    @classmethod
    def nonblank_plan_fields(cls,value):
        if not value.strip(): raise ValueError("field must not be blank")
        return value.strip()
class AIRunIn(BaseModel):
    project_id:str=Field(min_length=1,max_length=200)
    prompt:str=Field(min_length=1,max_length=20000)
    budget_approved:bool=False
    @field_validator("project_id","prompt")
    @classmethod
    def nonblank_run_fields(cls,value):
        if not value.strip(): raise ValueError("field must not be blank")
        return value.strip()
class AICodeProposalIn(BaseModel):
    project_id:str=Field(min_length=1,max_length=200)
    task_id:str|None=None
    task:str=Field(min_length=1,max_length=20000)
    allowed_paths:list[str]=Field(min_length=1,max_length=20)
    constraints:list[str]=Field(default_factory=list,max_length=100)
    budget_approved:bool=False
    @field_validator("project_id","task")
    @classmethod
    def nonblank_code_fields(cls,value):
        if not value.strip(): raise ValueError("field must not be blank")
        return value.strip()

def require_api_key(request:Request, authorization:str|None=Header(default=None)):
    """Authenticate either a configured per-principal token map or legacy single token."""
    expected=os.getenv("NEXUS_API_KEY","").strip()
    tokens_raw=os.getenv("NEXUS_API_TOKENS","").strip()
    if tokens_raw:
        try:
            tokens=json.loads(tokens_raw)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=503,detail="NEXUS_API_TOKENS must be valid JSON") from exc
        if not isinstance(tokens,dict):
            raise HTTPException(status_code=503,detail="NEXUS_API_TOKENS must be a JSON object")
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401,detail="Bearer token required")
        supplied=authorization[7:].strip()
        principal=tokens.get(supplied)
        if not isinstance(principal,str) or not principal.strip():
            raise HTTPException(status_code=403,detail="Invalid API token")
        return principal.strip()
    if not expected:
        host=request.client.host if request.client else ""
        if host in {"127.0.0.1","::1","localhost","testclient"}:
            request.state.principal="local-development"
            return "local-development"
        raise HTTPException(status_code=503,detail="Remote API disabled: configure NEXUS_API_KEY")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401,detail="Bearer token required")
    supplied=authorization[7:].strip()
    if not hmac.compare_digest(supplied,expected):
        raise HTTPException(status_code=403,detail="Invalid API token")
    return "legacy-shared"

async def require_project_access(request:Request, authorization:str|None=Header(default=None)):
    """Resolve project scope before the handler; fail closed for non-member principals."""
    principal=require_api_key(request,authorization)
    request.state.principal=principal
    project_id=None
    path_parts=[part for part in request.url.path.split("/") if part]
    if len(path_parts)>=2 and path_parts[0]=="projects":
        project_id=path_parts[1]
    elif len(path_parts)>=2 and path_parts[0]=="tasks":
        try:
            task=controller.get_task(path_parts[1])
            project_id=task["project_id"]
        except ValueError:
            # The endpoint will return its normal 404 for an unknown task.
            project_id=None
    if not project_id:
        project_id=request.query_params.get("project_id")
    body_data={}
    if request.method in {"POST","PUT","PATCH"} and request.headers.get("content-type","").split(";")[0].strip()=="application/json":
        try:
            body_data=json.loads(await request.body())
        except (json.JSONDecodeError,UnicodeDecodeError):
            body_data={}
    body_project=body_data.get("project_id") if isinstance(body_data,dict) else None
    body_task=body_data.get("task_id") if isinstance(body_data,dict) else None
    if body_project:
        if project_id and project_id!=body_project:
            raise HTTPException(status_code=403,detail={"code":"PROJECT_SCOPE_MISMATCH","message":"Request references more than one project."})
        project_id=body_project
    if body_task:
        try:
            task=controller.get_task(str(body_task))
        except ValueError:
            task=None
        if task:
            if project_id and project_id!=task["project_id"]:
                raise HTTPException(status_code=403,detail={"code":"PROJECT_SCOPE_MISMATCH","message":"task_id does not belong to project_id"})
            project_id=task["project_id"]
    # Project creation has no existing scope; its handler records the creator as owner.
    if request.method=="POST" and request.url.path=="/projects":
        return principal
    # Generic route-selection has no project parameter and only returns policy metadata.
    if request.url.path=="/policy/route":
        return principal
    if project_id:
        try:
            controller.status(project_id)
        except ValueError as exc:
            raise HTTPException(status_code=404,detail="unknown project_id") from exc
        if not project_authorization.has_access(project_id,principal):
            raise HTTPException(status_code=403,detail={"code":"PROJECT_ACCESS_DENIED","message":"Principal is not a member of this project."})
        if request.method in {"POST","PUT","PATCH","DELETE"} and not project_authorization.can_write(project_id,principal):
            raise HTTPException(status_code=403,detail={"code":"PROJECT_READ_ONLY","message":"Project membership is read-only."})
    return principal

def ensure_project_access(project_id:str,request:Request)->None:
    principal=getattr(request.state,"principal","")
    if project_authorization.has_access(project_id,principal):
        if request.method in {"POST","PUT","PATCH","DELETE"} and not project_authorization.can_write(project_id,principal):
            raise HTTPException(status_code=403,detail={"code":"PROJECT_READ_ONLY","message":"Project membership is read-only."})
        return
    try:
        controller.status(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=404,detail="unknown project_id") from exc
    raise HTTPException(status_code=403,detail={"code":"PROJECT_ACCESS_DENIED","message":"Principal is not a member of this project."})

def invoke(fn,*args,**kwargs):
    try: return fn(*args,**kwargs)
    except PolicyDenied as exc: raise HTTPException(status_code=403,detail=str(exc)) from exc
    except EvidenceFetchError as exc: raise HTTPException(status_code=422,detail=str(exc)) from exc
    except ValueError as exc:
        message=str(exc)
        status=404 if message.startswith("unknown ") else 409
        raise HTTPException(status_code=status,detail=message) from exc

@app.get("/health")
def health(): return {"status":"ok","service":"nexus-controller","version":VERSION}

@app.post("/projects",status_code=201,dependencies=[Depends(require_project_access)])
def create_project(body:ProjectIn,request:Request):
    result=invoke(controller.create_project,body.name)
    request.state.project_id=result["project_id"]
    project_authorization.grant_owner(result["project_id"],getattr(request.state,"principal","legacy-shared"))
    return result
@app.get("/projects/{project_id}/status",dependencies=[Depends(require_project_access)])
def project_status(project_id:str): return invoke(controller.status,project_id)
@app.post("/tasks",status_code=201,dependencies=[Depends(require_project_access)])
def create_task(body:TaskIn,request:Request):
    ensure_project_access(body.project_id,request)
    request.state.project_id=body.project_id
    result=invoke(controller.create_task,body.project_id,body.title,body.expected_outcome,body.verification_method)
    request.state.task_id=result["task_id"]
    return result
@app.get("/tasks/{task_id}",dependencies=[Depends(require_project_access)])
def get_task(task_id:str): return invoke(controller.get_task,task_id)
@app.post("/tasks/{task_id}/dependencies",status_code=201,dependencies=[Depends(require_project_access)])
def add_task_dependency(task_id:str,body:DependencyIn,request:Request):
    task=invoke(controller.get_task,task_id)
    request.state.project_id=task["project_id"]
    request.state.task_id=task_id
    return invoke(controller.add_task_dependency,task_id,body.depends_on_task_id,"api")

@app.get("/tasks/{task_id}/dependencies",dependencies=[Depends(require_project_access)])
def get_task_dependencies(task_id:str,request:Request):
    task=invoke(controller.get_task,task_id)
    request.state.project_id=task["project_id"]
    request.state.task_id=task_id
    return invoke(controller.get_task_dependencies,task_id)
@app.post("/tasks/{task_id}/transition",dependencies=[Depends(require_project_access)])
def transition(task_id:str,body:TransitionIn,request:Request,idempotency_key:str|None=Header(default=None,alias="Idempotency-Key")):
    task=invoke(controller.get_task,task_id)
    request.state.project_id=task["project_id"]
    request.state.task_id=task_id
    if body.to_state=="EXECUTE":
        if not idempotency_key or not idempotency_key.strip():
            raise HTTPException(status_code=428,detail={"code":"IDEMPOTENCY_KEY_REQUIRED",
                "message":"Idempotency-Key is required before entering EXECUTE."})
        fingerprint=json.dumps({"task_id":task_id,"to_state":body.to_state,"actor":body.actor,
            "reason":body.reason,"result":body.result,"error_code":body.error_code},sort_keys=True,separators=(",",":"))
        try:
            existing=idempotency_store.claim(idempotency_key.strip(),scope=f"task:{task_id}:transition",fingerprint=fingerprint)
            if existing["status"]=="COMPLETED":
                return existing["response"]
            response=invoke(controller.transition,task_id,body.to_state,body.actor,body.reason,body.result,body.error_code)
            idempotency_store.complete(idempotency_key.strip(),response)
            return response
        except IdempotencyConflict as exc:
            raise HTTPException(status_code=409,detail={"code":"IDEMPOTENCY_KEY_CONFLICT","message":str(exc)}) from exc
        except IdempotencyInProgress as exc:
            raise HTTPException(status_code=409,detail={"code":"IDEMPOTENCY_OUTCOME_UNKNOWN","message":str(exc)}) from exc
        except Exception as exc:
            try: idempotency_store.mark_uncertain(idempotency_key.strip(),type(exc).__name__)
            except Exception as ledger_exc:
                raise HTTPException(status_code=503,detail={"code":"IDEMPOTENCY_LEDGER_UNAVAILABLE","message":"Could not persist execution outcome; stop and reconcile before retry."}) from ledger_exc
            raise
    return invoke(controller.transition,task_id,body.to_state,body.actor,body.reason,body.result,body.error_code)

@app.post("/tasks/{task_id}/verification",dependencies=[Depends(require_project_access)])
def record_task_verification(task_id:str,body:VerificationIn,request:Request):
    task=invoke(controller.get_task,task_id)
    request.state.project_id=task["project_id"]
    request.state.task_id=task_id
    return invoke(controller.record_verification,task_id,body.verifier,body.evidence_id,body.result_sha256,body.notes)

@app.get("/tasks/{task_id}/verification",dependencies=[Depends(require_project_access)])
def get_task_verifications(task_id:str,request:Request):
    task=invoke(controller.get_task,task_id)
    request.state.project_id=task["project_id"]
    request.state.task_id=task_id
    return invoke(controller.get_verifications,task_id)
@app.post("/tasks/{task_id}/checkpoint",dependencies=[Depends(require_project_access)])
def checkpoint(task_id:str): return invoke(controller.checkpoint,task_id)
@app.post("/tasks/{task_id}/restore",dependencies=[Depends(require_project_access)])
def restore_checkpoint(task_id:str,body:RestoreIn):
    return invoke(controller.restore_checkpoint,task_id,body.checkpoint_id,body.actor,body.reason)
@app.post("/evidence",dependencies=[Depends(require_project_access)])
def add_evidence(body:EvidenceIn,request:Request):
    ensure_project_access(body.project_id,request)
    request.state.project_id=body.project_id
    request.state.task_id=body.task_id
    return invoke(controller.add_evidence,body.project_id,body.claim,body.status,body.source_url,body.notes,body.task_id)

@app.post("/evidence/verify",dependencies=[Depends(require_project_access)])
def verify_evidence(body:VerifyEvidenceIn,request:Request):
    ensure_project_access(body.project_id,request)
    request.state.project_id=body.project_id
    request.state.task_id=body.task_id
    try:
        return invoke(controller.verify_and_add_evidence,body.project_id,body.claim,body.source_url,
                     body.quoted_text,body.notes,"api-source-verifier",task_id=body.task_id)
    except EvidenceFetchError as exc:
        raise HTTPException(status_code=422,detail=str(exc)) from exc
@app.get("/projects/{project_id}/audit",dependencies=[Depends(require_project_access)])
def audit(project_id:str,task_id:str|None=None): return invoke(controller.audit,project_id,task_id)

@app.get("/records/search",dependencies=[Depends(require_project_access)])
def search_records(request:Request,project_id:str,record_type:str|None=None,task_id:str|None=None,
                   trace_id:str|None=None,operation_id:str|None=None,status:str|None=None,
                   error_code:str|None=None,component:str|None=None,query:str|None=None,
                   since:str|None=None,until:str|None=None,limit:int=100,offset:int=0):
    request.state.project_id=project_id
    try:
        return record_store.search(project_id=project_id,record_type=record_type,
            trace_id=trace_id,operation_id=operation_id,status=status,error_code=error_code,
            component=component,query=query,since=since,until=until,limit=limit,offset=offset)
    except ValueError as exc:
        raise HTTPException(status_code=422,detail=str(exc)) from exc

@app.post("/ai/plan",dependencies=[Depends(require_project_access)])
def propose_ai_plan(body:AIPlanIn,request:Request):
    ensure_project_access(body.project_id,request)
    request.state.project_id=body.project_id
    # A request-level checkbox alone cannot enable paid API usage: the deployment
    # operator must also set the server-side budget gate.
    budget_gate=os.getenv("NEXUS_OPENAI_BUDGET_APPROVED","").casefold()=="true"
    trace_id=getattr(request.state,"trace_id",None) or str(uuid.uuid4())
    try:
        return plan_generator.propose(project_id=body.project_id,task=body.task,
            constraints=body.constraints,capabilities=body.capabilities,
            budget_approved=body.budget_approved and budget_gate,trace_id=trace_id)
    except OpenAIPlanError as exc:
        code=403 if exc.code=="OPENAI_BUDGET_APPROVAL_REQUIRED" else 503 if exc.code in {"OPENAI_API_KEY_MISSING","OPENAI_SDK_MISSING"} else 502
        raise HTTPException(status_code=code,detail={"code":exc.code,"message":str(exc)}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422,detail=str(exc)) from exc


@app.post("/ai/code-proposal",dependencies=[Depends(require_project_access)])
def propose_code(body:AICodeProposalIn,request:Request):
    ensure_project_access(body.project_id,request)
    request.state.project_id=body.project_id
    request.state.task_id=body.task_id
    budget_gate=os.getenv("NEXUS_OPENAI_BUDGET_APPROVED","").casefold()=="true"
    trace_id=getattr(request.state,"trace_id",None) or str(uuid.uuid4())
    # Validate project/task scope before a paid provider call.
    invoke(controller.status,body.project_id)
    if body.task_id:
        task_row=invoke(controller.get_task,body.task_id)
        if task_row["project_id"] != body.project_id:
            raise HTTPException(status_code=403,detail={"code":"PROJECT_SCOPE_MISMATCH",
                "message":"task_id does not belong to project_id"})
    try:
        return code_proposal_generator.propose(project_id=body.project_id,task=body.task,
            allowed_paths=body.allowed_paths,task_id=body.task_id,constraints=body.constraints,
            budget_approved=body.budget_approved and budget_gate,trace_id=trace_id)
    except CodeProposalError as exc:
        code=403 if exc.code in {"OPENAI_BUDGET_APPROVAL_REQUIRED","CODE_PATH_NOT_ALLOWED","DUPLICATE_CODE_PATH"} else 503 if exc.code in {"OPENAI_API_KEY_MISSING","OPENAI_SDK_MISSING"} else 502
        raise HTTPException(status_code=code,detail={"code":exc.code,"message":str(exc)}) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422,detail=str(exc)) from exc

_AI_READ_TOOLS=[
 {"type":"function","name":"nexus_get_project_status","description":"Read NEXUS project status. Read-only and restricted to the active project.",
  "parameters":{"type":"object","properties":{"project_id":{"type":"string"}},"required":["project_id"],"additionalProperties":False},"strict":True},
 {"type":"function","name":"nexus_read_audit","description":"Read audit events for the active NEXUS project. Read-only.",
  "parameters":{"type":"object","properties":{"project_id":{"type":"string"},"task_id":{"type":["string","null"]}},"required":["project_id","task_id"],"additionalProperties":False},"strict":True},
 {"type":"function","name":"nexus_get_task","description":"Read one task in the active NEXUS project. Read-only.",
  "parameters":{"type":"object","properties":{"project_id":{"type":"string"},"task_id":{"type":"string"}},"required":["project_id","task_id"],"additionalProperties":False},"strict":True}
]

@app.post("/ai/run",dependencies=[Depends(require_project_access)])
def run_ai_with_read_tools(body:AIRunIn,request:Request):
    ensure_project_access(body.project_id,request)
    request.state.project_id=body.project_id
    budget_gate=os.getenv("NEXUS_OPENAI_BUDGET_APPROVED","").casefold()=="true"
    if not (body.budget_approved and budget_gate):
        try:
            record_store.append(project_id=body.project_id,record_type="decision",
                trace_id=getattr(request.state,"trace_id",None) or str(uuid.uuid4()),
                actor_type="system",component="openai_responses",status="BLOCK",
                error_code="OPENAI_BUDGET_APPROVAL_REQUIRED",summary="OpenAI tool run blocked by budget gate",
                payload={"decision":"BLOCK","reason_code":"OPENAI_BUDGET_APPROVAL_REQUIRED"})
        except Exception:
            pass
        raise HTTPException(status_code=403,detail={"code":"OPENAI_BUDGET_APPROVAL_REQUIRED",
            "message":"Both request approval and server-side budget approval are required."})
    def status_handler(args):
        if args["project_id"] != body.project_id: raise PolicyDenied("cross-project tool access blocked")
        return controller.status(body.project_id)
    def audit_handler(args):
        if args["project_id"] != body.project_id: raise PolicyDenied("cross-project tool access blocked")
        return controller.audit(body.project_id,args["task_id"])
    def task_handler(args):
        if args["project_id"] != body.project_id: raise PolicyDenied("cross-project tool access blocked")
        task=controller.get_task(args["task_id"])
        if task["project_id"] != body.project_id: raise PolicyDenied("cross-project task access blocked")
        return task
    handlers={"nexus_get_project_status":status_handler,"nexus_read_audit":audit_handler,
              "nexus_get_task":task_handler}
    def policy_check(name,args):
        if name not in handlers:
            return {"decision":"BLOCK","reason_code":"TOOL_NOT_ALLOWLISTED"}
        if args.get("project_id") != body.project_id:
            return {"decision":"BLOCK","reason_code":"PROJECT_SCOPE_MISMATCH"}
        return {"decision":"ALLOW","reason_code":"READ_ONLY_PROJECT_SCOPED"}
    trace_id=getattr(request.state,"trace_id",None) or str(uuid.uuid4())
    def record(**event):
        record_type=event.pop("record_type","usage")
        payload={k:v for k,v in event.items() if k not in {"prompt","arguments","output","api_key"}}
        try:
            record_store.append(project_id=body.project_id,record_type=record_type,
                trace_id=trace_id,operation_id=payload.get("call_id") or payload.get("response_id"),
                actor_type="system",component="openai_responses",
                status=str(payload.get("decision",payload.get("outcome","RECORDED"))),
                error_code=payload.get("error_code"),summary="OpenAI tool orchestration event",payload=payload)
        except Exception:
            pass
    try:
        worker=OpenAIResponsesWorker(model=os.getenv("NEXUS_OPENAI_MODEL","gpt-6-luna"))
        result=worker.run(prompt=body.prompt,tools=_AI_READ_TOOLS,tool_handlers=handlers,
                          policy_check=policy_check,record=record)
        result.update({"project_id":body.project_id,"trace_id":trace_id,
                       "policy_boundary":"NEXUS_DETERMINISTIC_READ_ONLY_TOOLS"})
        return result
    except OpenAIWorkerError as exc:
        raise HTTPException(status_code=502,detail={"code":"OPENAI_WORKER_FAILED","message":str(exc)}) from exc
    except PolicyDenied as exc:
        raise HTTPException(status_code=403,detail={"code":"POLICY_DENIED","message":str(exc)}) from exc
@app.post("/policy/route",dependencies=[Depends(require_project_access)])
def route(body:RouteIn): return controller.policy_route(body.candidates,body.allow_paid,body.budget_approved)
