"""Optional HTTP API for the NEXUS deterministic core."""
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from nexus.core import NEXUS

app=FastAPI(title="NEXUS Controller API",version="0.1.0",
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

def invoke(fn,*args,**kwargs):
    try: return fn(*args,**kwargs)
    except ValueError as exc: raise HTTPException(status_code=409,detail=str(exc)) from exc

@app.get("/health")
def health(): return {"status":"ok","service":"nexus-controller","version":"0.1.0"}
@app.post("/projects",status_code=201)
def create_project(body:ProjectIn): return invoke(controller.create_project,body.name)
@app.get("/projects/{project_id}/status")
def project_status(project_id:str): return invoke(controller.status,project_id)
@app.post("/tasks",status_code=201)
def create_task(body:TaskIn):
    return invoke(controller.create_task,body.project_id,body.title,body.expected_outcome,body.verification_method)
@app.get("/tasks/{task_id}")
def get_task(task_id:str): return invoke(controller.get_task,task_id)
@app.post("/tasks/{task_id}/transition")
def transition(task_id:str,body:TransitionIn):
    return invoke(controller.transition,task_id,body.to_state,body.actor,body.reason,body.result,body.error_code)
@app.post("/tasks/{task_id}/checkpoint")
def checkpoint(task_id:str): return invoke(controller.checkpoint,task_id)
@app.post("/evidence")
def add_evidence(body:EvidenceIn):
    return invoke(controller.add_evidence,body.project_id,body.claim,body.status,body.source_url,body.notes)
@app.get("/projects/{project_id}/audit")
def audit(project_id:str,task_id:str|None=None): return invoke(controller.audit,project_id,task_id)
@app.post("/policy/route")
def route(body:RouteIn): return controller.policy_route(body.candidates,body.allow_paid,body.budget_approved)
