from __future__ import annotations

from langgraph.types import interrupt

from app.ai.graph.state import DenialState
from app.config import settings

MAX_REVISIONS = 2


async def human_review_node(state: DenialState) -> dict:
    """Pause the workflow for a human reviewer.

    Healthcare claim appeals must NOT be blindly auto-submitted. Even a
    high-confidence, high-critic-score appeal only skips the interactive
    interrupt when an operator has explicitly set
    REQUIRE_HUMAN_APPROVAL=false *and* the claim is low value and the AI
    pipeline was confident end to end -- and even then the decision is still
    fully recorded in the audit trail as an automatic approval, never
    silently skipped.
    """
    amount = float(state.get("denied_amount") or 0.0)
    confidence = float(state.get("classification_confidence") or 0.0)
    critic_rec = state.get("critic_recommendation", "HUMAN_REVIEW")
    high_value = amount >= settings.high_value_threshold
    high_confidence_path = (
        confidence >= settings.confidence_threshold and critic_rec == "APPROVE_REVIEW" and not high_value
    )

    if not settings.require_human_approval and high_confidence_path:
        return {
            "human_review_required": False,
            "human_review_reason": "High confidence and critic score; human gate disabled by configuration.",
            "human_decision": "APPROVE",
            "reviewer_notes": "Auto-approved by workflow configuration (REQUIRE_HUMAN_APPROVAL=false).",
            "audit_events": [
                {"stage": "HUMAN_REVIEW", "status": "COMPLETED", "message": "Auto-approved (human gate disabled by config)."}
            ],
        }

    if high_value:
        reason = "High-value claim requires human approval regardless of AI confidence."
    elif high_confidence_path:
        reason = "AI confidence and critic score meet the auto threshold; reviewing before submission per policy."
    else:
        reason = "Confidence below threshold or the critic flagged issues; human review required."

    payload = {
        "claim_no": state.get("claim_no"),
        "payer": state.get("payer"),
        "denied_amount": amount,
        "denial_category": state.get("denial_category"),
        "denial_reason": state.get("denial_reason"),
        "classification_confidence": confidence,
        "policy_citations": state.get("policy_citations", []),
        "evidence_citations": state.get("evidence_citations", []),
        "appeal_draft": state.get("appeal_draft", ""),
        "appeal_score": state.get("appeal_score", 0),
        "appeal_issues": state.get("appeal_issues", []),
        "missing_evidence": state.get("critic_missing_evidence", []) or state.get("appeal_missing_evidence", []),
        "recommendation": critic_rec,
        "reason": reason,
    }

    decision = interrupt(payload) or {}

    return {
        "human_review_required": True,
        "human_review_reason": reason,
        "human_decision": decision.get("decision"),
        "reviewer_notes": decision.get("notes", ""),
        "edited_appeal_draft": decision.get("edited_draft"),
        "revision_count": int(state.get("revision_count") or 0) + (1 if decision.get("decision") == "REQUEST_MORE_EVIDENCE" else 0),
        "audit_events": [
            {
                "stage": "HUMAN_REVIEW",
                "status": decision.get("decision") or "PENDING",
                "message": f"Reviewer decision: {decision.get('decision')}." if decision.get("decision") else "Waiting for reviewer.",
            }
        ],
    }
