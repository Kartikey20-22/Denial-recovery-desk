from __future__ import annotations

from app.ai.graph.nodes.human_review import MAX_REVISIONS
from app.ai.graph.state import DenialState


def route_after_human_review(state: DenialState) -> str:
    """Decide where to go once the human-review node returns.

    APPROVE / EDIT / an auto-approval -> submission.
    REJECT                            -> tracking (no submission).
    REQUEST_MORE_EVIDENCE             -> back to evidence retrieval for
                                          another pass, capped at
                                          MAX_REVISIONS to avoid infinite
                                          loops in the demo.
    """
    decision = state.get("human_decision")
    if decision == "REJECT":
        return "tracking"
    if decision == "REQUEST_MORE_EVIDENCE" and int(state.get("revision_count") or 0) < MAX_REVISIONS:
        return "evidence_retrieval"
    # APPROVE, EDIT, an exhausted revision budget, or an auto-approval all
    # proceed to submission.
    return "submission"
