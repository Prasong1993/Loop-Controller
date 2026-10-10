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
plan_generator=OpenAIPlanGenerator(record_store)
code_proposal_generator=OpenAICodeProposalGenerator(record_store)

@app.middleware("http")
async def operational_record_middleware(request: Request, call_next):
    """Capture every REST request outcome without storing raw bodies or secrets."""
    started=time.monotonic()
    trace_id=request.headers.get("x-request-id","").strip()
    if not trace_id or len(trace_id)>128:
        trace_id=str(uuid.uuid4())
    request.state.trace_id=trace_id
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
class RouteIn(BaseModel):
    candidates:list[dict]
    allow_paid:bool=False
    budget_approved:bool=False
class RestoreIn(BaseModel):
    checkpoint_id:str=Field(min_length=1)
    actor:str="api"
    reason:str="Approved recovery"
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
    except EvidenceFetchError as exc: raise HTTPException(status_code=422,detail=str(exc)) from exc
    except ValueError as exc:
        message=str(exc)
        status=404 if message.startswith("unknown ") else 409
        raise HTTPException(status_code=status,detail=message) from exc

@app.get("/health")
def health(): return {"status":"ok","service":"nexus-controller","version":VERSION}

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
    return invoke(controller.add_evidence,body.project_id,body.claim,body.status,body.source_url,body.notes,body.task_id)

@app.post("/evidence/verify",dependencies=[Depends(require_api_key)])
def verify_evidence(body:VerifyEvidenceIn):
    try:
        return invoke(controller.verify_and_add_evidence,body.project_id,body.claim,body.source_url,
                     body.quoted_text,body.notes,"api-source-verifier",task_id=body.task_id)
    except EvidenceFetchError as exc:
        raise HTTPException(status_code=422,detail=str(exc)) from exc
@app.get("/projects/{project_id}/audit",dependencies=[Depends(require_api_key)])
def audit(project_id:str,task_id:str|None=None): return invoke(controller.audit,project_id,task_id)

@app.get("/records/search",dependencies=[Depends(require_api_key)])
def search_records(project_id:str,record_type:str|None=None,task_id:str|None=None,
                   trace_id:str|None=None,operation_id:str|None=None,status:str|None=None,
                   error_code:str|None=None,component:str|None=None,query:str|None=None,
                   since:str|None=None,until:str|None=None,limit:int=100,offset:int=0):
    try:
        return record_store.search(project_id=project_id,record_type=record_type,task_id=task_id,
            trace_id=trace_id,operation_id=operation_id,status=status,error_code=error_code,
            component=component,query=query,since=since,until=until,limit=limit,offset=offset)
    except ValueError as exc:
        raise HTTPException(status_code=422,detail=str(exc)) from exc

@app.post("/ai/plan",dependencies=[Depends(require_api_key)])
def propose_ai_plan(body:AIPlanIn,request:Request):
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


@app.post("/ai/code-proposal",dependencies=[Depends(require_api_key)])
def propose_code(body:AICodeProposalIn,request:Request):
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

@app.post("/ai/run",dependencies=[Depends(require_api_key)])
def run_ai_with_read_tools(body:AIRunIn,request:Request):
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
@app.post("/policy/route",dependencies=[Depends(require_api_key)])
def route(body:RouteIn): return controller.policy_route(body.candidates,body.allow_paid,body.budget_approved)
