from __future__ import annotations

from functools import lru_cache

from app.ai.embeddings import get_embeddings
from app.ai.retrieval.vectorstore import InMemoryVectorIndex
from app.config import settings


@lru_cache(maxsize=1)
def _index() -> InMemoryVectorIndex:
    return InMemoryVectorIndex.from_directory(settings.policy_data_dir, get_embeddings())


def retrieve_policy(query: str, k: int | None = None) -> list[dict]:
    """Return relevant payer-policy chunks with citation metadata.

    Each result preserves the document name, source path, and a relevance
    score, per the "every retrieved policy chunk must preserve..."
    requirement.
    """
    idx = _index()
    if idx.is_empty:
        return []
    top_k = k or settings.retrieval_top_k
    hits = idx.similarity_search_with_score(query, k=top_k)
    return [
        {
            "content": doc.page_content,
            "source": doc.metadata.get("source", "unknown"),
            "section": doc.metadata.get("chunk"),
            "relevance_score": round(float(score), 4),
        }
        for doc, score in hits
        if score > 0
    ]
