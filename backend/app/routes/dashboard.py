from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import db
from app.models import Denial, Claim, Payment, PayerResponse, BatchRun
from app.security import current_user
from app.services.outcome import outcome_snapshot

r=APIRouter()

@r.get("/stats")
async def stats(s:AsyncSession=Depends(db),u=Depends(current_user)):
    total=await s.scalar(select(func.count(Denial.id))) or 0
    auto=await s.scalar(select(func.count(Denial.id)).where(Denial.confidence >= 0.90)) or 0
    human=await s.scalar(select(func.count(Denial.id)).where(Denial.status=="HUMAN_REVIEW")) or 0
    submitted=await s.scalar(select(func.count(Denial.id)).where(Denial.submission_id.is_not(None))) or 0
    completed=await s.scalar(select(func.count(Denial.id)).where(Denial.outcome=="COMPLETED")) or 0
    amount=await s.scalar(select(func.coalesce(func.sum(Claim.amount),0))) or 0
    recovered=await s.scalar(select(func.coalesce(func.sum(Payment.amount),0)).where(Payment.verified==True)) or 0
    return {"total":total,"auto":auto,"human":human,"submitted":submitted,"recovered_claims":completed,
            "approved":completed,"denied_amount":float(amount),"recovered_amount":float(recovered),
            "recovery_rate":round(completed/total*100,1) if total else 0}

@r.get("/breakdown")
async def breakdown(s:AsyncSession=Depends(db),u=Depends(current_user)):
    by_reason=(await s.execute(select(Denial.reason,func.count(Denial.id)).where(Denial.reason.is_not(None)).group_by(Denial.reason))).all()
    by_status=(await s.execute(select(Denial.status,func.count(Denial.id)).group_by(Denial.status))).all()
    by_day=(await s.execute(select(func.date(Denial.created_at),func.count(Denial.id)).group_by(func.date(Denial.created_at)).order_by(func.date(Denial.created_at)))).all()
    by_conf=[]
    buckets=[("90%+",0), ("70–89%",0),("50–69%",0),("Below 50%",0)]
    for row in (await s.scalars(select(Denial.confidence))).all():
        v=float(row or 0)
        if v>=.9: buckets[0]=(buckets[0][0],buckets[0][1]+1)
        elif v>=.7: buckets[1]=(buckets[1][0],buckets[1][1]+1)
        elif v>=.5: buckets[2]=(buckets[2][0],buckets[2][1]+1)
        else: buckets[3]=(buckets[3][0],buckets[3][1]+1)
    by_conf=[{"name":n,"value":v} for n,v in buckets]
    payments=(await s.execute(select(func.date(Payment.payment_date),func.coalesce(func.sum(Payment.amount),0)).where(Payment.verified==True).group_by(func.date(Payment.payment_date)).order_by(func.date(Payment.payment_date)))).all()
    return {"by_reason":[{"name":r or "unclassified","value":c} for r,c in by_reason],
            "by_status":[{"name":st,"value":c} for st,c in by_status],
            "by_day":[{"date":str(d),"count":c} for d,c in by_day],
            "confidence_distribution":by_conf,
            "recovery_trend":[{"date":str(d),"amount":float(a or 0)} for d,a in payments]}

@r.get("/report")
async def report(s:AsyncSession=Depends(db),u=Depends(current_user)):
    return {"generated_at":datetime.now(timezone.utc),"stats":await stats(s,u),"breakdown":await breakdown(s,u)}

@r.get("/learning")
async def learning(s:AsyncSession=Depends(db),u=Depends(current_user)):
    """Outcome feedback loop: surface payer/category combinations that have
    historically recovered money, so reviewers can reuse proven playbooks."""
    rows=(await s.execute(select(Claim.payer, Denial.reason, func.count(Denial.id), func.coalesce(func.sum(Denial.recovered_amount),0))
        .join(Denial, Denial.claim_id==Claim.id)
        .where(Denial.recovered_amount>0)
        .group_by(Claim.payer, Denial.reason)
        .order_by(func.sum(Denial.recovered_amount).desc()).limit(12))).all()
    return [{"payer":p or "Unknown","category":r or "OTHER","successful_cases":int(c),"recovered_amount":float(a or 0),
             "playbook":"Prioritize the evidence + policy arguments used in recovered cases."} for p,r,c,a in rows]

@r.get("/operations")
async def operations(s:AsyncSession=Depends(db),u=Depends(current_user)):
    latest=(await s.scalars(select(BatchRun).order_by(BatchRun.id.desc()).limit(1))).first()
    return {"latest_batch": None if not latest else {"run_id":latest.run_id,"requested":latest.requested,"completed":latest.completed,
        "failed":latest.failed,"human_review":latest.human_review,"duration_seconds":latest.duration_seconds,"estimated_cost_usd":latest.estimated_cost_usd},
        "pipeline":"denial-recovery-load-bearing.pipe","human_gate":"required","cost_note":"Local Ollama reports $0 API spend; cloud is estimated from configured rate."}
