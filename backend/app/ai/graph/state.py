"""LangGraph state for the denial-recovery workflow.

Adapted from the existing `Denial`/`Claim`/`Appeal` SQLAlchemy models (see
app/models.py) rather than introduced from scratch -- field names line up
with the DB columns the FastAPI layer already reads/writes so the
orchestrator can map graph state <-> DB rows in one place
(app/ai/orchestrator.py).
"""
from __future__ import annotations

import operator
from typing import Annotated, Any, TypedDict


def _keep_last(a, b):
    """Reducer: a node's returned value replaces the previous one."""
    return b if b is not None else a


class DenialState(TypedDict, total=False):
    # --- identity -------------------------------------------------------
    denial_id: int
    claim_id: int
    thread_id: str

    # --- intake -----------------------------------------------------------
    claim_no: str
    payer: str
    denied_amount: float
    denial_text: str
    document_path: str | None

    # --- extraction ---------------------------------------------------------
    extracted_data: dict[str, Any]

    # --- classification -------------------------------------------------------
    denial_category: str
    denial_reason: str
    classification_confidence: float
    classification_supporting_text: str

    # --- retrieval ------------------------------------------------------------
    policy_citations: list[dict]
    evidence_citations: list[dict]

    # --- appeal generation --------------------------------------------------
    appeal_draft: str
    appeal_evidence_used: list[str]
    appeal_policy_references: list[str]
    appeal_missing_evidence: list[str]
    appeal_generation_confidence: float

    # --- critic ---------------------------------------------------------------
    appeal_score: int
    appeal_confidence: float
    appeal_issues: list[str]
    critic_missing_evidence: list[str]
    critic_recommendation: str

    # --- human-in-the-loop ------------------------------------------------
    human_review_required: bool
    human_review_reason: str
    human_decision: str | None  # APPROVE | EDIT | REQUEST_MORE_EVIDENCE | REJECT
    reviewer_notes: str | None
    edited_appeal_draft: str | None
    revision_count: int

    # --- submission / tracking -------------------------------------------
    submission_status: str
    submission_id: str | None
    recovery_probability: float

    # --- bookkeeping --------------------------------------------------------
    # Annotated with operator.add so concurrent/repeated node runs accumulate
    # rather than clobber each other.
    errors: Annotated[list[str], operator.add]
    audit_events: Annotated[list[dict], operator.add]
    current_node: str
