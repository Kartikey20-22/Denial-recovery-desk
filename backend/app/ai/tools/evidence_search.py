from langchain_core.tools import tool

from app.ai.retrieval.evidence_retriever import retrieve_evidence


@tool("evidence_search")
def evidence_search(query: str, claim_no: str = "") -> str:
    """Search synthetic supporting-evidence documents (clinical notes, prior
    auth logs, clearinghouse reports, etc.) relevant to a denial. Pass the
    claim number when known to prefer evidence tied to that specific claim."""
    hits = retrieve_evidence(query, claim_no=claim_no or None)
    if not hits:
        return "No supporting evidence found."
    return "\n\n".join(f"[{h['source']}] {h['content']}" for h in hits)
