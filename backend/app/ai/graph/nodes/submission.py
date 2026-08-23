from __future__ import annotations

import secrets
from datetime import datetime, timezone

from app.ai.graph.state import DenialState


async def submission_node(state: DenialState) -> dict:
    """Simulated payer submission for the demo -- never contacts a real payer."""
    try:
        final_draft = state.get("edited_appeal_draft") or state.get("appeal_draft", "")
        submission_id = f"SIM-{secrets.token_hex(4).upper()}"
        now = datetime.now(timezone.utc).isoformat()
        return {
            "appeal_draft": final_draft,
            "submission_status": "SUBMITTED",
            "submission_id": submission_id,
            "audit_events": [
                {
                    "stage": "SUBMISSION",
                    "status": "COMPLETED",
                    "message": f"Simulated submission created: {submission_id} at {now}.",
                }
            ],
        }
    except Exception as exc:
        return {
            "submission_status": "SUBMISSION_FAILED",
            "errors": [f"Submission failed: {exc}"],
            "audit_events": [{"stage": "SUBMISSION", "status": "FAILED", "message": str(exc)}],
        }
