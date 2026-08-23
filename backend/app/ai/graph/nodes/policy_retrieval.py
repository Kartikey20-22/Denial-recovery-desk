from __future__ import annotations

from app.ai.graph.state import DenialState
from app.ai.retrieval.policy_retriever import retrieve_policy


async def policy_retrieval_node(state: DenialState) -> dict:
    try:
        query = f"{state.get('denial_category', '')} {state.get('denial_text', '')}"[:1000]
        hits = retrieve_policy(query)
        message = (
            f"Retrieved {len(hits)} relevant policy section(s)." if hits else "No matching policy section found."
        )
        return {
            "policy_citations": hits,
            "audit_events": [{"stage": "POLICY_RETRIEVAL", "status": "COMPLETED", "message": message}],
        }
    except Exception as exc:
        return {
            "policy_citations": [],
            "errors": [f"Policy retrieval failed: {exc}"],
            "audit_events": [{"stage": "POLICY_RETRIEVAL", "status": "FAILED", "message": str(exc)}],
        }
