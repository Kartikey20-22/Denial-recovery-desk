from datetime import datetime, timezone
from sqlalchemy import String, Text, Float, DateTime, ForeignKey, Numeric, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base

def now(): return datetime.now(timezone.utc)

class User(Base):
    __tablename__="users"
    id: Mapped[int]=mapped_column(primary_key=True)
    email: Mapped[str]=mapped_column(String(255),unique=True,index=True)
    password_hash: Mapped[str]=mapped_column(String(500))
    name: Mapped[str]=mapped_column(String(120))
    role: Mapped[str]=mapped_column(String(40),default="reviewer")

class Claim(Base):
    __tablename__="claims"
    id: Mapped[int]=mapped_column(primary_key=True)
    claim_no: Mapped[str]=mapped_column(String(80),unique=True,index=True)
    payer: Mapped[str]=mapped_column(String(120))
    amount: Mapped[float]=mapped_column(Numeric(12,2),default=0)
    patient_ref: Mapped[str]=mapped_column(String(80),default="SYNTHETIC")

class Denial(Base):
    __tablename__="denials"
    id: Mapped[int]=mapped_column(primary_key=True)
    claim_id: Mapped[int]=mapped_column(ForeignKey("claims.id"))
    reason: Mapped[str|None]=mapped_column(String(80))
    code: Mapped[str|None]=mapped_column(String(40))
    text: Mapped[str]=mapped_column(Text,default="")
    confidence: Mapped[float]=mapped_column(Float,default=0)
    status: Mapped[str]=mapped_column(String(40),default="NEW",index=True)
    explanation: Mapped[str]=mapped_column(Text,default="")
    evidence: Mapped[str]=mapped_column(Text,default="")
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
    thread_id: Mapped[str|None]=mapped_column(String(80),index=True)
    extracted_data: Mapped[str]=mapped_column(Text,default="{}")
    policy_citations: Mapped[str]=mapped_column(Text,default="[]")
    evidence_citations: Mapped[str]=mapped_column(Text,default="[]")
    missing_evidence: Mapped[str]=mapped_column(Text,default="[]")
    appeal_score: Mapped[float]=mapped_column(Float,default=0)
    appeal_issues: Mapped[str]=mapped_column(Text,default="[]")
    recovery_probability: Mapped[float]=mapped_column(Float,default=0)
    submission_id: Mapped[str|None]=mapped_column(String(80))
    submitted_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    follow_up_date: Mapped[datetime|None]=mapped_column(DateTime(timezone=True))
    outcome: Mapped[str|None]=mapped_column(String(40))
    recovered_amount: Mapped[float]=mapped_column(Float,default=0)
    processing_seconds: Mapped[float]=mapped_column(Float,default=0)
    estimated_cost_usd: Mapped[float]=mapped_column(Float,default=0)
    estimated_tokens: Mapped[int]=mapped_column(default=0)

class Appeal(Base):
    __tablename__="appeals"
    id: Mapped[int]=mapped_column(primary_key=True)
    denial_id: Mapped[int]=mapped_column(ForeignKey("denials.id"))
    draft: Mapped[str]=mapped_column(Text)
    status: Mapped[str]=mapped_column(String(40),default="DRAFT")
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
    score: Mapped[float]=mapped_column(Float,default=0)
    issues: Mapped[str]=mapped_column(Text,default="[]")
    recommendation: Mapped[str]=mapped_column(String(30),default="")

class ReviewTask(Base):
    __tablename__="review_tasks"
    id: Mapped[int]=mapped_column(primary_key=True)
    denial_id: Mapped[int]=mapped_column(ForeignKey("denials.id"))
    reason: Mapped[str]=mapped_column(String(300))
    status: Mapped[str]=mapped_column(String(30),default="PENDING")
    notes: Mapped[str]=mapped_column(Text,default="")

class Event(Base):
    __tablename__="events"
    id: Mapped[int]=mapped_column(primary_key=True)
    denial_id: Mapped[int]=mapped_column(ForeignKey("denials.id"))
    stage: Mapped[str]=mapped_column(String(60))
    status: Mapped[str]=mapped_column(String(30))
    message: Mapped[str]=mapped_column(Text,default="")
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)

class Document(Base):
    __tablename__="documents"
    id: Mapped[int]=mapped_column(primary_key=True)
    denial_id: Mapped[int|None]=mapped_column(ForeignKey("denials.id"), nullable=True)
    name: Mapped[str]=mapped_column(String(255))
    document_type: Mapped[str]=mapped_column(String(60),default="DENIAL_LETTER")
    path: Mapped[str|None]=mapped_column(String(500),nullable=True)
    status: Mapped[str]=mapped_column(String(30),default="UPLOADED")
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)

class PayerResponse(Base):
    __tablename__="payer_responses"
    id: Mapped[int]=mapped_column(primary_key=True)
    denial_id: Mapped[int]=mapped_column(ForeignKey("denials.id"),index=True)
    submission_id: Mapped[str|None]=mapped_column(String(80),nullable=True)
    status: Mapped[str]=mapped_column(String(30),default="PENDING")
    approved_amount: Mapped[float]=mapped_column(Float,default=0)
    response_reference: Mapped[str|None]=mapped_column(String(100),nullable=True)
    response_date: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
    message: Mapped[str]=mapped_column(Text,default="")

class Payment(Base):
    __tablename__="payments"
    id: Mapped[int]=mapped_column(primary_key=True)
    denial_id: Mapped[int]=mapped_column(ForeignKey("denials.id"),index=True)
    claim_id: Mapped[int]=mapped_column(ForeignKey("claims.id"),index=True)
    payment_reference: Mapped[str]=mapped_column(String(100),unique=True,index=True)
    amount: Mapped[float]=mapped_column(Float,default=0)
    status: Mapped[str]=mapped_column(String(30),default="PENDING")
    payment_date: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
    verified: Mapped[bool]=mapped_column(Boolean,default=False)
    source: Mapped[str]=mapped_column(String(40),default="PAYER_SIMULATOR")
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)

class Notification(Base):
    __tablename__="notifications"
    id: Mapped[int]=mapped_column(primary_key=True)
    denial_id: Mapped[int|None]=mapped_column(ForeignKey("denials.id"),nullable=True)
    title: Mapped[str]=mapped_column(String(180))
    message: Mapped[str]=mapped_column(Text,default="")
    kind: Mapped[str]=mapped_column(String(30),default="info")
    read: Mapped[bool]=mapped_column(Boolean,default=False)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)


class BatchRun(Base):
    __tablename__="batch_runs"
    id: Mapped[int]=mapped_column(primary_key=True)
    run_id: Mapped[str]=mapped_column(String(80),unique=True,index=True)
    requested: Mapped[int]=mapped_column(default=0)
    completed: Mapped[int]=mapped_column(default=0)
    failed: Mapped[int]=mapped_column(default=0)
    human_review: Mapped[int]=mapped_column(default=0)
    started_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
    finished_at: Mapped[datetime|None]=mapped_column(DateTime(timezone=True),nullable=True)
    duration_seconds: Mapped[float]=mapped_column(Float,default=0)
    estimated_cost_usd: Mapped[float]=mapped_column(Float,default=0)
    notes: Mapped[str]=mapped_column(Text,default="")
