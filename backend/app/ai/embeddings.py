"""Embedding provider factory for the policy/evidence RAG retrievers.

Default is a dependency-free, deterministic local embedding (hashed bag of
words projected into a fixed-size vector). It needs no model download, no
GPU, and no network access, so the RAG pipeline works out of the box on a
laptop with nothing else running -- important for hackathon-demo
reliability. Set EMBEDDING_PROVIDER=ollama to use a real embedding model
(e.g. nomic-embed-text) served by a local Ollama instance instead.
"""
from __future__ import annotations

import hashlib
import math
import re
from functools import lru_cache

from langchain_core.embeddings import Embeddings

from app.config import settings

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_DIM = 384


class LocalHashingEmbeddings(Embeddings):
    """A tiny, deterministic, dependency-free embedding.

    Not as semantically rich as a trained embedding model, but stable,
    fast, free, and offline -- appropriate for a demo RAG index over a
    handful of short synthetic policy/evidence documents where keyword
    overlap is a reasonable proxy for relevance.
    """

    def __init__(self, dim: int = _DIM):
        self.dim = dim

    def _vector(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        tokens = _TOKEN_RE.findall((text or "").lower())
        for tok in tokens:
            if len(tok) < 3:
                continue
            h = int(hashlib.sha256(tok.encode()).hexdigest(), 16)
            idx = h % self.dim
            sign = 1.0 if (h // self.dim) % 2 == 0 else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)


@lru_cache(maxsize=2)
def get_embeddings() -> Embeddings:
    provider = (settings.embedding_provider or "local").lower()
    if provider == "ollama":
        try:
            from langchain_ollama import OllamaEmbeddings

            return OllamaEmbeddings(base_url=settings.ollama_base_url, model=settings.embedding_model)
        except Exception:
            # Ollama not reachable / embedding model not pulled -- fall back
            # to the local embedding so retrieval keeps working.
            return LocalHashingEmbeddings()
    return LocalHashingEmbeddings()
