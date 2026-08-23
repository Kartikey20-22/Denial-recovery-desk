from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import db
from app.models import ReviewTask,Denial,Claim
from app.schemas import Review
from app.security import current_user
from app.ai import orchestrator

r=APIRouter()

_LEGACY_MAP={"APPROVE":"APPROVE","REJECT":"REJECT"}
_VALID={"APPROVE","EDIT","REQUEST_MORE_EVIDENCE","REJECT"}

@r.get("")
async def tasks(s:AsyncSession=Depends(db),u=Depends(current_user)):
    xs=(await s.scalars(select(ReviewTask).where(ReviewTask.status=="PENDING"))).all()
    return [{"id":x.id,"denial_id":x.denial_id,"reason":x.reason} for x in xs]

@r.post("/{id}")
async def decide(id:int,x:Review,s:AsyncSession=Depends(db),u=Depends(current_user)):
    t=await s.get(ReviewTask,id)
    if not t: raise HTTPException(404,"Review task not found")
    decision=_LEGACY_MAP.get(x.decision,x.decision)
    if decision not in _VALID: raise HTTPException(400,f"decision must be one of {sorted(_VALID)}")
    d=await s.get(Denial,t.denial_id)
    if not d: raise HTTPException(404,"Denial not found")
    c=await s.get(Claim,d.claim_id)
    await orchestrator.resume_workflow(s,d,c,decision,notes=x.notes,edited_draft=x.edited_draft)
    return {"status":d.status}
