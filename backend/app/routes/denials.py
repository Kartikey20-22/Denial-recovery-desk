import json
from pathlib import Path
from uuid import uuid4
import time
from typing import Optional
from fastapi import APIRouter,Depends,File,Form,HTTPException,UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select,or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.db import db
from app.models import Claim,Denial,Appeal,ReviewTask,Event,Document,BatchRun
from app.schemas import WorkflowDecision
from app.security import current_user
from app.ai import orchestrator
from app.services.outcome import outcome_snapshot
from app.config import settings

r=APIRouter()

class BatchRequest(BaseModel):
    ids: list[int] | None = None
    limit: int = Field(default=25, ge=1, le=100)


async def _get_denial_and_claim(s:AsyncSession,id:int):
    d=await s.get(Denial,id)
    if not d: raise HTTPException(404,"Not found")
    c=await s.get(Claim,d.claim_id)
    return d,c

@r.post("/upload")
async def upload(file:UploadFile=File(...),claim_no:str=Form(...),payer:str=Form("Demo Payer"),
                 amount:float=Form(0),denial_text:str=Form(""),s:AsyncSession=Depends(db),
                 user=Depends(current_user)):
    ext=Path(file.filename or "").suffix.lower()
    if ext not in {".pdf",".png",".jpg",".jpeg",".webp",".tiff"}: raise HTTPException(400,"PDF/images only")
    data=await file.read()
    if len(data)>15*1024*1024: raise HTTPException(413,"File too large")
    d=Path(settings.upload_dir); d.mkdir(parents=True,exist_ok=True)
    path=d/(uuid4().hex+ext); path.write_bytes(data)
    claim=await s.scalar(select(Claim).where(Claim.claim_no==claim_no))
    if not claim:
        claim=Claim(claim_no=claim_no,payer=payer,amount=amount); s.add(claim); await s.flush()
    denial=Denial(claim_id=claim.id,text=denial_text,status="PROCESSING"); s.add(denial); await s.flush()
    s.add(Document(denial_id=denial.id, name=file.filename or path.name, document_type="DENIAL_LETTER", path=str(path), status="UPLOADED"))
    try:
        await orchestrator.start_workflow(s,denial,claim)
    except Exception as exc:
        s.add(Event(denial_id=denial.id,stage="INTAKE",status="FAILED",message=f"Workflow failed to start: {exc}"))
        denial.status="FAILED"
        await s.commit(); await s.refresh(denial)
    return await one(denial.id,s,user)

@r.post("/{id}/analyze")
async def analyze(id:int,s:AsyncSession=Depends(db),user=Depends(current_user)):
    """Run the LangGraph pipeline against an existing denial record (e.g. one
    that was seeded as demo data, or is being re-analyzed)."""
    d,c=await _get_denial_and_claim(s,id)
    try:
        await orchestrator.start_workflow(s,d,c)
    except Exception as exc:
        s.add(Event(denial_id=d.id,stage="INTAKE",status="FAILED",message=f"Workflow failed to start: {exc}"))
        d.status="FAILED"
        await s.commit()
    return await one(id,s,user)

@r.post("/{id}/generate-appeal")
async def generate_appeal_endpoint(id:int,s:AsyncSession=Depends(db),user=Depends(current_user)):
    """Re-run the pipeline to regenerate the appeal (e.g. after more evidence
    has been added to the demo evidence corpus)."""
    d,c=await _get_denial_and_claim(s,id)
    await orchestrator.start_workflow(s,d,c)
    return await one(id,s,user)

@r.post("/batch-analyze")
async def batch_analyze(body: BatchRequest, s:AsyncSession=Depends(db), user=Depends(current_user)):
    """Run a bounded batch through the same production workflow used by the UI.
    The response intentionally exposes throughput, failures, human-review count
    and estimated spend for a hackathon-grade batch demonstration."""
    limit = body.limit
    stmt = select(Denial).order_by(Denial.id.asc()).limit(limit)
    if body.ids:
        clean = list(dict.fromkeys(int(x) for x in body.ids))[:100]
        stmt = select(Denial).where(Denial.id.in_(clean)).order_by(Denial.id.asc())
    denials = list((await s.scalars(stmt)).all())
    run_id = f"BATCH-{uuid4().hex[:8].upper()}"
    batch = BatchRun(run_id=run_id, requested=len(denials))
    s.add(batch); await s.flush()
    started = time.perf_counter()
    results=[]
    for d in denials:
        try:
            c = await s.get(Claim, d.claim_id)
            if not c or not (d.text or "").strip():
                raise ValueError("Malformed denial: missing claim or denial text")
            await orchestrator.start_workflow(s, d, c)
            results.append({"id":d.id,"status":d.status,"ok":True,"seconds":d.processing_seconds,"cost_usd":d.estimated_cost_usd})
            batch.completed += 1
            if d.status == "HUMAN_REVIEW": batch.human_review += 1
        except Exception as exc:
            batch.failed += 1
            d.status = "FAILED"
            s.add(Event(denial_id=d.id, stage="BATCH_VALIDATION", status="FAILED", message=str(exc)))
            results.append({"id":d.id,"status":"FAILED","ok":False,"error":str(exc)})
            await s.commit()
    batch.duration_seconds = round(time.perf_counter() - started, 3)
    batch.finished_at = __import__('datetime').datetime.now(__import__('datetime').timezone.utc)
    batch.estimated_cost_usd = round(sum(float(x.get("cost_usd") or 0) for x in results), 6)
    batch.notes = "Malformed records are isolated and do not crash the remaining batch."
    await s.commit()
    return {"run_id":run_id,"requested":batch.requested,"completed":batch.completed,"failed":batch.failed,
            "human_review":batch.human_review,"duration_seconds":batch.duration_seconds,
            "estimated_cost_usd":batch.estimated_cost_usd,"cost_model":"Ollama local = $0 API spend; cloud uses configured estimate per 1K tokens.",
            "results":results}

@r.get("/batch-runs")
async def batch_runs(limit:int=10,s:AsyncSession=Depends(db),user=Depends(current_user)):
    rows=(await s.scalars(select(BatchRun).order_by(BatchRun.id.desc()).limit(min(max(limit,1),50)))).all()
    return [{"run_id":x.run_id,"requested":x.requested,"completed":x.completed,"failed":x.failed,
             "human_review":x.human_review,"duration_seconds":x.duration_seconds,"estimated_cost_usd":x.estimated_cost_usd,
             "started_at":x.started_at,"finished_at":x.finished_at,"notes":x.notes} for x in rows]

@r.post("/rocketride/process")
async def rocketrider_process(payload: dict, s:AsyncSession=Depends(db)):
    """Internal RocketRide action endpoint. A RocketRide agent can call this
    sandbox endpoint after validating a denial payload. It creates the case,
    runs the same audited workflow, and returns a compact trace for the pipe."""
    required = ["claim_no", "payer", "amount", "denial_text"]
    missing = [k for k in required if k not in payload or payload.get(k) in (None, "")]
    if missing:
        raise HTTPException(422, {"error":"malformed_input","missing":missing})
    if len(str(payload.get("denial_text"))) < 10:
        raise HTTPException(422, {"error":"malformed_input","message":"denial_text is too short"})
    claim_no=str(payload["claim_no"])[:80]
    claim=await s.scalar(select(Claim).where(Claim.claim_no==claim_no))
    if not claim:
        claim=Claim(claim_no=claim_no,payer=str(payload["payer"])[:120],amount=float(payload["amount"])); s.add(claim); await s.flush()
    denial=Denial(claim_id=claim.id,text=str(payload["denial_text"]),status="PROCESSING")
    s.add(denial); await s.flush()
    await orchestrator.start_workflow(s,denial,claim)
    events=(await s.scalars(select(Event).where(Event.denial_id==denial.id).order_by(Event.id.asc()))).all()
    return {"denial_id":denial.id,"claim_no":claim.claim_no,"status":denial.status,
            "submission_id":denial.submission_id,"confidence":denial.confidence,
            "processing_seconds":denial.processing_seconds,"estimated_cost_usd":denial.estimated_cost_usd,
            "trace":[{"stage":e.stage,"status":e.status,"message":e.message} for e in events]}

@r.get("/rocketride/status")
async def rocketrider_status(s:AsyncSession=Depends(db),user=Depends(current_user)):
    return {"enabled":settings.rocketrider_enabled,"pipeline":settings.rocketrider_pipeline_name,
            "mode":"load-bearing orchestration manifest","backend_workflow":"LangGraph + FastAPI",
            "human_gate":settings.require_human_approval,"llm_provider":settings.llm_provider}

@r.get("")
async def list_denials(status:Optional[str]=None,reason:Optional[str]=None,q:Optional[str]=None,
                        s:AsyncSession=Depends(db),user=Depends(current_user)):
    stmt=select(Denial,Claim).join(Claim,Claim.id==Denial.claim_id).order_by(Denial.id.desc())
    if status: stmt=stmt.where(Denial.status==status)
    if reason: stmt=stmt.where(Denial.reason==reason)
    if q:
        like=f"%{q}%"
        stmt=stmt.where(or_(Claim.claim_no.ilike(like),Claim.payer.ilike(like),Denial.text.ilike(like)))
    rows=(await s.execute(stmt)).all()
    return [{"id":d.id,"claim_id":d.claim_id,"claim_no":c.claim_no,"payer":c.payer,
             "amount":float(c.amount or 0),"reason":d.reason,"confidence":d.confidence,
             "status":d.status,"explanation":d.explanation,"created_at":d.created_at} for d,c in rows]

@r.get("/{id}")
async def one(id:int,s:AsyncSession=Depends(db),user=Depends(current_user)):
    d,c=await _get_denial_and_claim(s,id)
    a=(await s.scalars(select(Appeal).where(Appeal.denial_id==id).order_by(Appeal.id.desc()))).first()
    outcome = await outcome_snapshot(s, d, c)
    return {"id":d.id,"claim_no":c.claim_no,"payer":c.payer,"amount":float(c.amount or 0),
            "reason":d.reason,"code":d.code,"confidence":d.confidence,"status":d.status,
            "explanation":d.explanation,"evidence":d.evidence,
            "policy_citations":json.loads(d.policy_citations or "[]"),
            "evidence_citations":json.loads(d.evidence_citations or "[]"),
            "missing_evidence":json.loads(d.missing_evidence or "[]"),
            "extracted_data":json.loads(d.extracted_data or "{}"),
            "appeal_score":d.appeal_score,"appeal_issues":json.loads(d.appeal_issues or "[]"),
            "recovery_probability":d.recovery_probability,
            "submission_id":d.submission_id,"submitted_at":d.submitted_at,
            "appeal":(a.draft if a else ""),
            "appeal_recommendation":(a.recommendation if a else ""),
            "created_at":d.created_at,
            "outcome": outcome}

@r.get("/{id}/events")
async def events(id:int,s:AsyncSession=Depends(db),user=Depends(current_user)):
    d=await s.get(Denial,id)
    if not d: raise HTTPException(404,"Not found")
    xs=(await s.scalars(select(Event).where(Event.denial_id==id).order_by(Event.id.asc()))).all()
    return [{"id":e.id,"stage":e.stage,"status":e.status,"message":e.message,
             "created_at":e.created_at} for e in xs]

@r.get("/{id}/timeline")
async def timeline(id:int,s:AsyncSession=Depends(db),user=Depends(current_user)):
    return await events(id,s,user)

@r.get("/{id}/workflow")
async def workflow(id:int,s:AsyncSession=Depends(db),user=Depends(current_user)):
    d=await s.get(Denial,id)
    if not d: raise HTTPException(404,"Not found")
    return await orchestrator.get_workflow_snapshot(d)

@r.get("/{id}/evidence")
async def evidence(id:int,s:AsyncSession=Depends(db),user=Depends(current_user)):
    d=await s.get(Denial,id)
    if not d: raise HTTPException(404,"Not found")
    return {"evidence_citations":json.loads(d.evidence_citations or "[]"),
            "policy_citations":json.loads(d.policy_citations or "[]"),
            "missing_evidence":json.loads(d.missing_evidence or "[]")}

@r.get("/{id}/appeal")
async def appeal(id:int,s:AsyncSession=Depends(db),user=Depends(current_user)):
    a=(await s.scalars(select(Appeal).where(Appeal.denial_id==id).order_by(Appeal.id.desc()))).first()
    if not a: raise HTTPException(404,"No appeal draft yet")
    return {"draft":a.draft,"status":a.status,"score":a.score,
            "issues":json.loads(a.issues or "[]"),"recommendation":a.recommendation}

@r.post("/{id}/review")
async def review(id:int,body:WorkflowDecision,s:AsyncSession=Depends(db),user=Depends(current_user)):
    """Resume a paused workflow with a reviewer decision, addressed by
    denial id directly (see also /api/reviews/{task_id} which is addressed
    by review-task id and is what the current frontend calls)."""
    d,c=await _get_denial_and_claim(s,id)
    if body.decision not in {"APPROVE","EDIT","REQUEST_MORE_EVIDENCE","REJECT"}:
        raise HTTPException(400,"invalid decision")
    await orchestrator.resume_workflow(s,d,c,body.decision,notes=body.notes,edited_draft=body.edited_draft)
    return await one(id,s,user)

@r.post("/{id}/approve")
async def approve(id:int,body:WorkflowDecision|None=None,s:AsyncSession=Depends(db),user=Depends(current_user)):
    d,c=await _get_denial_and_claim(s,id)
    notes=body.notes if body else ""
    edited=body.edited_draft if body else None
    decision="EDIT" if edited else "APPROVE"
    await orchestrator.resume_workflow(s,d,c,decision,notes=notes,edited_draft=edited)
    return await one(id,s,user)

@r.post("/{id}/reject")
async def reject(id:int,body:WorkflowDecision|None=None,s:AsyncSession=Depends(db),user=Depends(current_user)):
    d,c=await _get_denial_and_claim(s,id)
    notes=body.notes if body else ""
    await orchestrator.resume_workflow(s,d,c,"REJECT",notes=notes)
    return await one(id,s,user)
