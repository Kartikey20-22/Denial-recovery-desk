"""Integration test: orchestrator <-> real (sqlite) DB rows, with the graph
wired to an in-memory checkpointer so no external services are needed."""
import json

import pytest
from langgraph.checkpoint.memory import MemorySaver
from sqlalchemy import select

from app.ai import orchestrator
from app.ai.graph.graph import build_graph
from app.models import Claim, Denial, Event, ReviewTask


@pytest.fixture()
def patched_graph(monkeypatch):
    graph = build_graph(checkpointer=MemorySaver())
    monkeypatch.setattr(orchestrator, "get_graph", lambda: graph)
    return graph


async def test_start_workflow_pauses_and_creates_review_task(db_sessionmaker, patched_graph):
    async with db_sessionmaker() as session:
        claim = Claim(claim_no="CLM-2001", payer="NorthCare", amount=15000)
        session.add(claim)
        await session.flush()
        denial = Denial(claim_id=claim.id, text="Medical necessity documentation was insufficient.", status="NEW")
        session.add(denial)
        await session.flush()

        await orchestrator.start_workflow(session, denial, claim)

        assert denial.status == "HUMAN_REVIEW"
        assert denial.thread_id == f"denial-{denial.id}"
        assert json.loads(denial.policy_citations or "[]") or json.loads(denial.evidence_citations or "[]") is not None

        events = (await session.scalars(select(Event).where(Event.denial_id == denial.id))).all()
        assert len(events) >= 5  # intake through critic at minimum

        tasks = (await session.scalars(select(ReviewTask).where(ReviewTask.denial_id == denial.id))).all()
        assert len(tasks) == 1


async def test_resume_workflow_approve_submits_and_closes_review_task(db_sessionmaker, patched_graph):
    async with db_sessionmaker() as session:
        claim = Claim(claim_no="CLM-2002", payer="Prime Payer", amount=9000)
        session.add(claim)
        await session.flush()
        denial = Denial(claim_id=claim.id, text="Claim exceeded timely filing limit.", status="NEW")
        session.add(denial)
        await session.flush()

        await orchestrator.start_workflow(session, denial, claim)
        assert denial.status == "HUMAN_REVIEW"

        await orchestrator.resume_workflow(session, denial, claim, "APPROVE", notes="Approved by test reviewer.")

        assert denial.status == "SUBMITTED"
        assert denial.submission_id

        tasks = (await session.scalars(select(ReviewTask).where(ReviewTask.denial_id == denial.id))).all()
        pending = [t for t in tasks if t.status == "PENDING"]
        assert not pending


async def test_resume_workflow_reject_does_not_submit(db_sessionmaker, patched_graph):
    async with db_sessionmaker() as session:
        claim = Claim(claim_no="CLM-2003", payer="Acme Health", amount=4000)
        session.add(claim)
        await session.flush()
        denial = Denial(claim_id=claim.id, text="Claim identified as a duplicate of a previously processed claim.", status="NEW")
        session.add(denial)
        await session.flush()

        await orchestrator.start_workflow(session, denial, claim)
        await orchestrator.resume_workflow(session, denial, claim, "REJECT", notes="Confirmed duplicate.")

        assert denial.status == "REJECTED"
        assert not denial.submission_id
