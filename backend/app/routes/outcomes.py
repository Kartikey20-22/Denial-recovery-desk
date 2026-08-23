from datetime import datetime, timezone
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import db
from app.models import Claim, Denial, PayerResponse, Payment
from app.security import current_user
from app.services.outcome import outcome_snapshot, refresh_completion, record_event, notify

r = APIRouter()

class PayerDecision(BaseModel):
    status: str = Field(pattern="^(PENDING|APPROVED|DENIED)$")
    approved_amount: float = 0
    message: str = ""

class PaymentInput(BaseModel):
    amount: float = Field(ge=0)
    status: str = Field(default="PAID", pattern="^(PENDING|PAID)$")
    payment_reference: str | None = None

async def get_case(s, id):
    d = await s.get(Denial, id)
    if not d: raise HTTPException(404, "Denial not found")
    c = await s.get(Claim, d.claim_id)
    return d, c

@r.get("/{id}/outcome")
async def get_outcome(id: int, s: AsyncSession = Depends(db), u=Depends(current_user)):
    d, c = await get_case(s, id)
    return await outcome_snapshot(s, d, c)

@r.post("/{id}/payer-response")
async def payer_response(id: int, body: PayerDecision, s: AsyncSession = Depends(db), u=Depends(current_user)):
    d, c = await get_case(s, id)
    if not d.submission_id:
        raise HTTPException(400, "Submit the appeal before recording a payer response")
    ref = f"PAYER-{uuid4().hex[:8].upper()}"
    row = PayerResponse(denial_id=id, submission_id=d.submission_id, status=body.status,
                        approved_amount=body.approved_amount, response_reference=ref,
                        message=body.message or f"Payer simulator returned {body.status}.")
    s.add(row)
    await record_event(s, id, "PAYER_RESPONSE", body.status, row.message)
    await notify(s, id, "Payer decision received", f"{d.id}: payer status is {body.status}.", "good" if body.status == "APPROVED" else "warn")
    await s.flush()
    snap = await refresh_completion(s, d, c)
    await s.commit()
    return snap

@r.post("/{id}/payment")
async def record_payment(id: int, body: PaymentInput, s: AsyncSession = Depends(db), u=Depends(current_user)):
    d, c = await get_case(s, id)
    payer = (await s.scalars(select(PayerResponse).where(PayerResponse.denial_id == id).order_by(PayerResponse.id.desc()))).first()
    if not payer or payer.status != "APPROVED":
        raise HTTPException(400, "Payer must approve the claim before payment can be recorded")
    ref = body.payment_reference or f"PAY-{uuid4().hex[:8].upper()}"
    paid_now = body.status == "PAID"
    row = Payment(denial_id=id, claim_id=c.id, payment_reference=ref, amount=body.amount,
                  status=body.status, payment_date=datetime.now(timezone.utc) if paid_now else None,
                  verified=paid_now, source="PAYER_SIMULATOR")
    s.add(row)
    await record_event(s, id, "PAYMENT", "VERIFIED" if paid_now else "PENDING",
                       f"Payment {ref}: {body.amount:.2f} recorded; verified={paid_now}.")
    await notify(s, id, "Payment received" if paid_now else "Payment pending",
                 f"{d.id}: {body.amount:.2f} payment record updated.", "good" if paid_now else "info")
    await s.flush()
    snap = await refresh_completion(s, d, c)
    await s.commit()
    return snap

@r.post("/{id}/simulate")
async def simulate(id: int, s: AsyncSession = Depends(db), u=Depends(current_user)):
    d, c = await get_case(s, id)
    if not d.submission_id:
        raise HTTPException(400, "Submit the appeal before simulating payer outcome")
    payer = PayerResponse(denial_id=id, submission_id=d.submission_id, status="APPROVED",
                          approved_amount=float(c.amount or 0), response_reference=f"PAYER-{uuid4().hex[:8].upper()}",
                          message="Simulated payer approved the appeal.")
    s.add(payer)
    await record_event(s, id, "PAYER_RESPONSE", "APPROVED", "Simulated payer approved the appeal.")
    await notify(s, id, "Payer approved appeal", f"Claim {c.claim_no} was approved for {float(c.amount or 0):.2f}.", "good")
    await s.flush()
    snap = await refresh_completion(s, d, c)
    await s.commit()
    return snap
