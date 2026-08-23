from __future__ import annotations

from app.ai.chains.critic_chain import critique_appeal
from app.ai.graph.state import DenialState


async def appeal_critic_node(state: DenialState) -> dict:
    try:
        evaluation = critique_appeal(
            denial_reason=state.get("denial_reason", ""),
            appeal_letter=state.get("appeal_draft", ""),
            policy_hits=state.get("policy_citations", []),
            evidence_hits=state.get("evidence_citations", []),
        )
        return {
            "appeal_score": evaluation.score,
            "appeal_confidence": evaluation.confidence,
            "appeal_issues": evaluation.issues,
            "critic_missing_evidence": evaluation.missing_evidence,
            "critic_recommendation": evaluation.recommendation.value,
            "audit_events": [
                {
                    "stage": "APPEAL_CRITIC",
                    "status": "COMPLETED",
                    "message": f"Critic score {evaluation.score}/100 -> {evaluation.recommendation.value}.",
                }
            ],
        }
    except Exception as exc:
        return {
            "appeal_score": 0,
            "critic_recommendation": "HUMAN_REVIEW",
            "errors": [f"Critic evaluation failed: {exc}"],
            "audit_events": [{"stage": "APPEAL_CRITIC", "status": "FAILED", "message": str(exc)}],
        }
