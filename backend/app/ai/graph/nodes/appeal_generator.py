from __future__ import annotations

from app.ai.chains.appeal_chain import generate_appeal
from app.ai.graph.state import DenialState


async def appeal_generator_node(state: DenialState) -> dict:
    try:
        draft = generate_appeal(
            claim_no=state.get("claim_no", ""),
            payer=state.get("payer", ""),
            denied_amount=state.get("denied_amount", 0.0),
            category=state.get("denial_category", "OTHER"),
            denial_reason=state.get("denial_reason", ""),
            policy_hits=state.get("policy_citations", []),
            evidence_hits=state.get("evidence_citations", []),
        )
        return {
            "appeal_draft": draft.letter,
            "appeal_evidence_used": draft.evidence_used,
            "appeal_policy_references": draft.policy_references,
            "appeal_missing_evidence": draft.missing_evidence,
            "appeal_generation_confidence": draft.confidence,
            "audit_events": [{"stage": "APPEAL_GENERATION", "status": "COMPLETED", "message": "Appeal letter drafted."}],
        }
    except Exception as exc:
        return {
            "appeal_draft": "",
            "errors": [f"Appeal generation failed: {exc}"],
            "audit_events": [{"stage": "APPEAL_GENERATION", "status": "FAILED", "message": str(exc)}],
        }
