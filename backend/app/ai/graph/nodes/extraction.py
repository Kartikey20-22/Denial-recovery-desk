from __future__ import annotations

from app.ai.chains.extraction_chain import extract_denial_fields
from app.ai.graph.state import DenialState


async def extraction_node(state: DenialState) -> dict:
    try:
        extraction = extract_denial_fields(
            denial_text=state.get("denial_text", ""),
            claim_no=state.get("claim_no", ""),
            payer=state.get("payer", ""),
            amount=state.get("denied_amount", 0.0),
        )
        return {
            "extracted_data": extraction.model_dump(),
            "audit_events": [
                {"stage": "EXTRACTION", "status": "COMPLETED", "message": "Structured fields extracted from denial text."}
            ],
        }
    except Exception as exc:
        return {
            "extracted_data": {},
            "errors": [f"Extraction failed: {exc}"],
            "audit_events": [{"stage": "EXTRACTION", "status": "FAILED", "message": str(exc)}],
        }
