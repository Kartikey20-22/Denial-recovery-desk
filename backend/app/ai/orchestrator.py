"""Bridges the LangGraph workflow to FastAPI routes and the SQL database.

Graph nodes themselves are DB-agnostic (they only read/return `DenialState`
dict fields, see app/ai/graph/nodes/*.py) -- this module is the one place
that knows how to turn a LangGraph run into `Denial`/`Appeal`/`Event` rows,
and vice versa. That keeps the graph/chain code independently testable
(mock the LLM, run the graph, assert on dict fields -- no DB needed) while
the API layer gets a normal-looking async function to call.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone

from langgraph.types import Command
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.checkpoint import get_graph
from app.ai.graph.graph import NODE_ORDER
from app.models import Appeal, Claim, Denial, Event, ReviewTask
from app.config import settings

NODE_STAGE = {
    "intake": "INTAKE",
    "extraction": "EXTRACTION",
    "classifier": "CLASSIFICATION",
    "policy_retrieval": "POLICY_RETRIEVAL",
    "evidence_retrieval": "EVIDENCE_RETRIEVAL",
    "appeal_generator": "APPEAL_GENERATION",
    "appeal_critic": "APPEAL_CRITIC",
    "human_review": "HUMAN_REVIEW",
    "submission": "SUBMISSION",
    "tracking": "TRACKING",
}


def _thread_config(denial: Denial) -> dict:
    return {"configurable": {"thread_id": denial.thread_id}}


async def _persist_events(session: AsyncSession, denial: Denial, node_output: dict) -> None:
    for evt in node_output.get("audit_events", []) or []:
        session.add(
            Event(
                denial_id=denial.id,
                stage=evt.get("stage", "UNKNOWN"),
                status=evt.get("status", "COMPLETED"),
                message=evt.get("message", ""),
            )
        )


def _apply_state_to_denial(denial: Denial, claim: Claim, state: dict) -> None:
    if state.get("denial_category"):
        denial.reason = state["denial_category"]
    if state.get("classification_confidence") is not None:
        denial.confidence = float(state["classification_confidence"])
    if state.get("denial_reason"):
        denial.explanation = state["denial_reason"]
    if state.get("policy_citations") is not None:
        denial.policy_citations = json.dumps(state["policy_citations"])
    if state.get("evidence_citations") is not None:
        denial.evidence_citations = json.dumps(state["evidence_citations"])
        # keep the legacy plain-text `evidence` column populated too, for the
        # existing frontend field that already renders it.
        denial.evidence = "\n\n".join(
            f"[{c.get('source')}] {c.get('content', '')}" for c in state["evidence_citations"]
        )
    if state.get("extracted_data") is not None:
        denial.extracted_data = json.dumps(state["extracted_data"])
    if state.get("critic_missing_evidence") is not None or state.get("appeal_missing_evidence") is not None:
        denial.missing_evidence = json.dumps(
            state.get("critic_missing_evidence") or state.get("appeal_missing_evidence") or []
        )
    if state.get("appeal_score") is not None:
        denial.appeal_score = float(state["appeal_score"])
    if state.get("appeal_issues") is not None:
        denial.appeal_issues = json.dumps(state["appeal_issues"])
    if state.get("recovery_probability") is not None:
        denial.recovery_probability = float(state["recovery_probability"])
    if state.get("submission_id"):
        denial.submission_id = state["submission_id"]
        denial.submitted_at = datetime.now(timezone.utc)

    submission_status = state.get("submission_status")
    human_decision = state.get("human_decision")
    if submission_status == "SUBMITTED":
        denial.status = "SUBMITTED"
        denial.outcome = "SUBMITTED"
    elif submission_status == "REJECTED" or human_decision == "REJECT":
        denial.status = "REJECTED"
        denial.outcome = "REJECTED"
    elif submission_status == "FOLLOW_UP_REQUIRED":
        denial.status = "FOLLOW_UP_REQUIRED"
    elif state.get("appeal_draft"):
        denial.status = "HUMAN_REVIEW"  # awaiting the review gate
    else:
        denial.status = "PROCESSING"


async def _sync_appeal_row(session: AsyncSession, denial: Denial, state: dict) -> None:
    from sqlalchemy import select

    draft = state.get("edited_appeal_draft") or state.get("appeal_draft")
    if not draft:
        return
    existing = (
        await session.scalars(select(Appeal).where(Appeal.denial_id == denial.id).order_by(Appeal.id.desc()))
    ).first()
    score = float(state.get("appeal_score") or 0)
    issues = json.dumps(state.get("appeal_issues") or [])
    recommendation = state.get("critic_recommendation", "")
    status = "SUBMITTED" if state.get("submission_status") == "SUBMITTED" else "READY_FOR_REVIEW"
    if existing and existing.draft != draft:
        existing.draft = draft
        existing.score = score
        existing.issues = issues
        existing.recommendation = recommendation
        existing.status = status
    elif not existing:
        session.add(
            Appeal(denial_id=denial.id, draft=draft, status=status, score=score, issues=issues, recommendation=recommendation)
        )
    else:
        existing.score = score
        existing.issues = issues
        existing.recommendation = recommendation
        existing.status = status


async def _sync_review_task(session: AsyncSession, denial: Denial, snapshot_state: dict, awaiting_human: bool) -> None:
    from sqlalchemy import select

    existing = (
        await session.scalars(
            select(ReviewTask).where(ReviewTask.denial_id == denial.id, ReviewTask.status == "PENDING")
        )
    ).first()
    if awaiting_human and not existing:
        session.add(
            ReviewTask(
                denial_id=denial.id,
                reason=snapshot_state.get("human_review_reason", "Human review required."),
            )
        )
    elif not awaiting_human and existing:
        existing.status = "COMPLETED"
        existing.notes = snapshot_state.get("reviewer_notes", "") or existing.notes


async def _drain_stream(session: AsyncSession, denial: Denial, claim: Claim, stream) -> dict:
    """Consume a graph.astream(...) iterator, persisting Event rows per
    node and returning the last node's output dict (or {} if interrupted
    immediately)."""
    last_output: dict = {}
    async for chunk in stream:
        if "__interrupt__" in chunk:
            # Graph paused at interrupt() inside human_review_node.
            break
        for node_name, node_output in chunk.items():
            await _persist_events(session, denial, node_output)
            _apply_state_to_denial(denial, claim, node_output)
            last_output = node_output
    return last_output


async def start_workflow(session: AsyncSession, denial: Denial, claim: Denial) -> dict:
    """Kick off (or restart) the LangGraph workflow for a denial and run it
    up to the first interrupt (human review) or completion."""
    graph = get_graph()
    if not denial.thread_id:
        denial.thread_id = f"denial-{denial.id}"

    config = _thread_config(denial)
    inputs = {
        "denial_id": denial.id,
        "claim_id": claim.id,
        "claim_no": claim.claim_no,
        "payer": claim.payer,
        "denied_amount": float(claim.amount or 0),
        "denial_text": denial.text,
        "document_path": None,
        "revision_count": 0,
        "errors": [],
        "audit_events": [],
    }
    denial.status = "PROCESSING"
    await session.flush()

    started = time.perf_counter()
    stream = graph.astream(inputs, config, stream_mode="updates")
    await _drain_stream(session, denial, claim, stream)

    snapshot = await graph.aget_state(config)
    elapsed = time.perf_counter() - started
    # RocketRide judging asks for predictable per-run cost. Local Ollama is $0
    # in API spend; for cloud providers we expose a conservative estimate from
    # input/output text size so the UI can report a number instead of guessing.
    raw_text = json.dumps(snapshot.values or {}, default=str)
    estimated_tokens = max(1, len(raw_text) // 4)
    estimated_cost = 0.0 if settings.llm_provider == "ollama" else (estimated_tokens / 1000.0) * settings.estimated_cloud_cost_per_1k_tokens_usd
    denial.processing_seconds = round(elapsed, 3)
    denial.estimated_tokens = estimated_tokens
    denial.estimated_cost_usd = round(estimated_cost, 6)
    session.add(Event(denial_id=denial.id, stage="RUN_METRICS", status="COMPLETED",
                      message=f"Run completed in {elapsed:.2f}s; estimated tokens={estimated_tokens}; estimated cost=${estimated_cost:.6f}."))
    awaiting_human = "human_review" in (snapshot.next or ())
    await _sync_appeal_row(session, denial, snapshot.values)
    await _sync_review_task(session, denial, snapshot.values, awaiting_human)
    if awaiting_human:
        denial.status = "HUMAN_REVIEW"
    else:
        # Finished without pausing (e.g. auto-approval path) -- reconcile
        # against the FULL accumulated state, not just the last node's delta.
        _apply_state_to_denial(denial, claim, snapshot.values)
    await session.commit()
    await session.refresh(denial)
    return snapshot.values


async def resume_workflow(
    session: AsyncSession, denial: Denial, claim: Denial, decision: str, notes: str = "", edited_draft: str | None = None
) -> dict:
    """Resume a paused workflow with a human reviewer's decision."""
    graph = get_graph()
    config = _thread_config(denial)

    resume_payload = {"decision": decision, "notes": notes, "edited_draft": edited_draft}
    stream = graph.astream(Command(resume=resume_payload), config, stream_mode="updates")
    await _drain_stream(session, denial, claim, stream)

    snapshot = await graph.aget_state(config)
    awaiting_human = "human_review" in (snapshot.next or ())
    await _sync_appeal_row(session, denial, snapshot.values)
    await _sync_review_task(session, denial, snapshot.values, awaiting_human)
    if not awaiting_human:
        _apply_state_to_denial(denial, claim, snapshot.values)
    await session.commit()
    await session.refresh(denial)
    return snapshot.values


async def get_workflow_snapshot(denial: Denial) -> dict:
    """Return per-node status for the frontend pipeline visualization."""
    graph = get_graph()
    if not denial.thread_id:
        return {"nodes": [{"node": n, "stage": NODE_STAGE[n], "status": "PENDING"} for n in NODE_ORDER], "awaiting_human": False}

    config = _thread_config(denial)
    snapshot = await graph.aget_state(config)
    values = snapshot.values or {}
    events = values.get("audit_events", []) or []
    stage_status: dict[str, str] = {}
    for evt in events:
        stage_status[evt.get("stage")] = evt.get("status")

    awaiting_human = "human_review" in (snapshot.next or ())
    nodes = []
    reached_current = False
    for node in NODE_ORDER:
        stage = NODE_STAGE[node]
        status = stage_status.get(stage)
        if status in ("COMPLETED",) or (status and status not in ("FAILED",) and stage != "HUMAN_REVIEW"):
            nodes.append({"node": node, "stage": stage, "status": "COMPLETED"})
        elif status == "FAILED":
            nodes.append({"node": node, "stage": stage, "status": "FAILED"})
        elif stage == "HUMAN_REVIEW" and awaiting_human:
            nodes.append({"node": node, "stage": stage, "status": "WAITING_FOR_HUMAN"})
            reached_current = True
        elif status:
            nodes.append({"node": node, "stage": stage, "status": status})
        else:
            nodes.append({"node": node, "stage": stage, "status": "PENDING"})

    return {"nodes": nodes, "awaiting_human": awaiting_human, "next": list(snapshot.next or ())}
