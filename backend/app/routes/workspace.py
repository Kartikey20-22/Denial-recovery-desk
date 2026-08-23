import json
from pathlib import Path
from sqlalchemy import select
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import db
from app.models import Appeal, Claim, Denial, Document, Event, Notification, User
from app.security import current_user
from app.config import settings

r = APIRouter()

@r.get("/appeals")
async def appeals(s: AsyncSession = Depends(db), u=Depends(current_user)):
    rows = (await s.execute(select(Appeal, Denial, Claim).join(Denial, Appeal.denial_id == Denial.id).join(Claim, Denial.claim_id == Claim.id).order_by(Appeal.id.desc()))).all()
    return [{"id":a.id,"denial_id":d.id,"claim_no":c.claim_no,"payer":c.payer,"reason":d.reason,
             "score":a.score,"status":a.status,"recommendation":a.recommendation,"created_at":a.created_at} for a,d,c in rows]

@r.get("/documents")
async def documents(s: AsyncSession = Depends(db), u=Depends(current_user)):
    rows = (await s.scalars(select(Document).order_by(Document.id.desc()))).all()
    return [{"id":x.id,"denial_id":x.denial_id,"name":x.name,"document_type":x.document_type,
             "status":x.status,"created_at":x.created_at} for x in rows]

@r.get("/payer-rules")
async def payer_rules(u=Depends(current_user)):
    root = Path(settings.policy_data_dir)
    root.mkdir(parents=True, exist_ok=True)
    items=[]
    for p in sorted(root.glob("*.txt")):
        items.append({"name":p.stem.replace("_"," ").title(),"file":p.name,"size":p.stat().st_size})
    return items

@r.get("/notifications")
async def notifications(s: AsyncSession = Depends(db), u=Depends(current_user)):
    rows = (await s.scalars(select(Notification).order_by(Notification.id.desc()).limit(20))).all()
    return [{"id":n.id,"denial_id":n.denial_id,"title":n.title,"message":n.message,"kind":n.kind,"read":n.read,"created_at":n.created_at} for n in rows]

@r.post("/notifications/{id}/read")
async def read_notification(id: int, s: AsyncSession = Depends(db), u=Depends(current_user)):
    n = await s.get(Notification,id)
    if n:
        n.read = True
        await s.commit()
    return {"ok":True}

@r.get("/users")
async def users(s: AsyncSession = Depends(db), u=Depends(current_user)):
    rows = (await s.scalars(select(User).order_by(User.id.asc()))).all()
    return [{"id":x.id,"name":x.name,"email":x.email,"role":x.role} for x in rows]
