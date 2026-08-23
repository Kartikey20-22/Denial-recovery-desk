from __future__ import annotations

from app.ai.graph.state import DenialState
from app.ai.retrieval.evidence_retriever import retrieve_evidence


async def evidence_retrieval_node(state: DenialState) -> dict:
    try:
        query = f"{state.get('denial_category', '')} {state.get('denial_text', '')}"[:1000]
        hits = retrieve_evidence(query, claim_no=state.get("claim_no"))
        message = (
            f"Retrieved {len(hits)} supporting evidence item(s)." if hits else "No supporting evidence found."
        )
        return {
            "evidence_citations": hits,
            "audit_events": [{"stage": "EVIDENCE_RETRIEVAL", "status": "COMPLETED", "message": message}],
        }
    except Exception as exc:
        return {
            "evidence_citations": [],
            "errors": [f"Evidence retrieval failed: {exc}"],
            "audit_events": [{"stage": "EVIDENCE_RETRIEVAL", "status": "FAILED", "message": str(exc)}],
        }
