"""A small, dependency-light in-memory vector index.

We deliberately avoid requiring a running vector database (Chroma server,
Qdrant, etc.) or a compiled dependency (faiss-cpu) for the hackathon demo --
the corpus is a handful of short synthetic policy/evidence text files, so an
in-memory cosine-similarity index rebuilt at process startup is more than
enough, and it means `pip install -r requirements.txt` never has to fight a
native build on someone's laptop.

If you want a "real" vector database for a larger corpus, swap this module
for `langchain_community.vectorstores.Chroma` or `.FAISS` -- every retriever
in this package only depends on the `similarity_search` method below, so the
rest of the RAG/graph code does not need to change.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


@dataclass
class InMemoryVectorIndex:
    """Minimal vector store: holds (Document, embedding) pairs in memory."""

    embeddings: Embeddings
    _docs: list[Document] = field(default_factory=list)
    _vectors: list[list[float]] = field(default_factory=list)

    @classmethod
    def from_directory(cls, directory: str | Path, embeddings: Embeddings) -> "InMemoryVectorIndex":
        idx = cls(embeddings=embeddings)
        directory = Path(directory)
        if not directory.exists():
            return idx

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap
        )
        raw_docs: list[Document] = []
        for path in sorted(directory.rglob("*.txt")):
            try:
                text = path.read_text(errors="ignore")
            except OSError:
                continue
            if not text.strip():
                continue
            for i, chunk in enumerate(splitter.split_text(text)):
                raw_docs.append(
                    Document(
                        page_content=chunk,
                        metadata={"source": path.name, "chunk": i, "path": str(path)},
                    )
                )
        if raw_docs:
            idx.add_documents(raw_docs)
        return idx

    def add_documents(self, docs: list[Document]) -> None:
        vectors = self.embeddings.embed_documents([d.page_content for d in docs])
        self._docs.extend(docs)
        self._vectors.extend(vectors)

    def similarity_search_with_score(self, query: str, k: int = 4) -> list[tuple[Document, float]]:
        if not self._docs:
            return []
        q = self.embeddings.embed_query(query)
        scored = [(_cosine(q, v), doc) for v, doc in zip(self._vectors, self._docs)]
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [(doc, score) for score, doc in scored[:k]]

    def similarity_search(self, query: str, k: int = 4) -> list[Document]:
        return [doc for doc, _ in self.similarity_search_with_score(query, k)]

    @property
    def is_empty(self) -> bool:
        return not self._docs
