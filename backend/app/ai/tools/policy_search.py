from langchain_core.tools import tool

from app.ai.retrieval.policy_retriever import retrieve_policy


@tool("policy_search")
def policy_search(query: str) -> str:
    """Search synthetic payer policy documents for text relevant to a denial
    reason (e.g. 'prior authorization', 'timely filing'). Returns the most
    relevant policy excerpts with their source document name."""
    hits = retrieve_policy(query)
    if not hits:
        return "No relevant policy sections found."
    return "\n\n".join(f"[{h['source']}] {h['content']}" for h in hits)
