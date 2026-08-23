`ollama.py` and `rag.py` in this directory are the **pre-LangGraph**
implementations (direct Ollama HTTP calls + keyword-match RAG). They are no
longer imported by anything — `app/ai/llm.py`, `app/ai/chains/*`, and
`app/ai/retrieval/*` replace them (see MIGRATION.md). Left in place for
reference / diff purposes rather than deleted outright; safe to remove.
