from __future__ import annotations

from app.ai.graph.state import DenialState

# Recovery-probability heuristic for the demo dashboard. A real system would
# base this on historical payer-specific recovery rates; here it's a simple,
# transparent function of classification confidence and critic score so the
# dashboard has a meaningful number to show without inventing payer data.


def _estimate_recovery_probability(state: DenialState) -> float:
    if state.get("human_decision") == "REJECT":
        return 0.0
    confidence = float(state.get("classification_confidence") or 0.0)
    score = float(state.get("appeal_score") or 0) / 100.0
    return round(min(0.98, max(0.05, 0.5 * confidence + 0.5 * score)), 2)


async def tracking_node(state: DenialState) -> dict:
    decision = state.get("human_decision")
    if decision == "REJECT":
        status = "REJECTED"
        message = "Denial rejected by reviewer; no submission made."
    elif state.get("submission_status") == "SUBMITTED":
        status = "SUBMITTED"
        message = f"Tracking initialized for submission {state.get('submission_id')}."
    else:
        status = "FOLLOW_UP_REQUIRED"
        message = "Additional evidence requested; not yet resubmitted."

    return {
        "submission_status": status,
        "recovery_probability": _estimate_recovery_probability(state),
        "audit_events": [{"stage": "TRACKING", "status": "COMPLETED", "message": message}],
    }
