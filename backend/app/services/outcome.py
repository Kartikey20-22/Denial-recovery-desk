from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Claim, Denial, PayerResponse, Payment, Event, Notification

async def latest_payer_response(session: AsyncSession, denial_id: int):
    return (await session.scalars(select(PayerResponse).where(PayerResponse.denial_id == denial_id).order_by(PayerResponse.id.desc()))).first()

async def latest_payment(session: AsyncSession, denial_id: int):
    return (await session.scalars(select(Payment).where(Payment.denial_id == denial_id).order_by(Payment.id.desc()))).first()

async def outcome_snapshot(session: AsyncSession, denial: Denial, claim: Claim):
    payer = await latest_payer_response(session, denial.id)
    payment = await latest_payment(session, denial.id)
    payer_status = payer.status if payer else ("SUBMITTED" if denial.submission_id else "NOT_SUBMITTED")
    payment_status = payment.status if payment else "NOT_FOUND"
    verified = bool(payment and payment.verified and payment.status == "PAID")
    paid = float(payment.amount or 0) if payment else 0.0
    approved = float(payer.approved_amount or 0) if payer else 0.0
    expected = float(claim.amount or 0)
    if payer_status == "DENIED":
        case_status = "REAPPEAL_REQUIRED"
    elif verified and paid > 0 and paid < max(approved or expected, 0.01):
        case_status = "PARTIAL_PAYMENT"
    elif verified:
        case_status = "COMPLETED"
    elif payer_status == "APPROVED":
        case_status = "PAYMENT_PENDING"
    elif payer_status == "PENDING":
        case_status = "PAYER_PENDING"
    elif denial.status == "SUBMITTED":
        case_status = "PAYER_PENDING"
    else:
        case_status = denial.status
    return {
        "case_status": case_status,
        "payer_status": payer_status,
        "payment_status": payment_status,
        "payment_verified": verified,
        "approved_amount": approved,
        "paid_amount": paid,
        "expected_amount": expected,
        "outstanding_amount": max(expected - paid, 0),
        "submission_id": denial.submission_id,
        "response_reference": payer.response_reference if payer else None,
        "payment_reference": payment.payment_reference if payment else None,
        "payment_date": payment.payment_date if payment else None,
    }

async def refresh_completion(session: AsyncSession, denial: Denial, claim: Claim):
    snap = await outcome_snapshot(session, denial, claim)
    if snap["case_status"] == "COMPLETED":
        denial.outcome = "COMPLETED"
        denial.recovered_amount = snap["paid_amount"]
    elif snap["case_status"] == "PARTIAL_PAYMENT":
        denial.outcome = "PARTIAL_PAYMENT"
        denial.recovered_amount = snap["paid_amount"]
    elif snap["case_status"] == "PAYMENT_PENDING":
        denial.outcome = "PAYMENT_PENDING"
    elif snap["case_status"] == "REAPPEAL_REQUIRED":
        denial.outcome = "REAPPEAL_REQUIRED"
    await session.flush()
    return snap

async def record_event(session, denial_id: int, stage: str, status: str, message: str):
    session.add(Event(denial_id=denial_id, stage=stage, status=status, message=message))

async def notify(session, denial_id: int | None, title: str, message: str, kind: str = "info"):
    session.add(Notification(denial_id=denial_id, title=title, message=message, kind=kind))
