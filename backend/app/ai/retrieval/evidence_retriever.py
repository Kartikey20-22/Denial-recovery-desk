from __future__ import annotations

from functools import lru_cache

from app.ai.embeddings import get_embeddings
from app.ai.retrieval.vectorstore import InMemoryVectorIndex
from app.config import settings


@lru_cache(maxsize=1)
def _index() -> InMemoryVectorIndex:
    return InMemoryVectorIndex.from_directory(settings.evidence_data_dir, get_embeddings())


def retrieve_evidence(query: str, claim_no: str | None = None, k: int | None = None) -> list[dict]:
    """Return relevant supporting-evidence chunks with citation metadata.

    If claim_no is supplied, results are boosted when the source filename
    references that claim (synthetic evidence files are named
    `<claim_no>_<topic>.txt`), so evidence for the specific claim under
    appeal is preferred over generic evidence from other cases.
    """
    idx = _index()
    if idx.is_empty:
        return []
    top_k = k or settings.retrieval_top_k
    hits = idx.similarity_search_with_score(query, k=top_k * 2 if claim_no else top_k)
    results = []
    for doc, score in hits:
        source = doc.metadata.get("source", "unknown")
        boosted = score
        related = claim_no is not None and source.startswith(f"{claim_no}_")
        if claim_no and related:
            boosted += 1.0  # simple boost so claim-specific evidence sorts first
        results.append(
            {
                "content": doc.page_content,
                "source": source,
                "relevance_score": round(float(score), 4),
                "relates_to_claim": related,
            }
        )
    results.sort(key=lambda r: (r["relates_to_claim"], r["relevance_score"]), reverse=True)
    return [r for r in results[:top_k] if r["relevance_score"] > 0 or r["relates_to_claim"]]
