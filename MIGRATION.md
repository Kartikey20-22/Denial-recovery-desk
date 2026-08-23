# Migration: Denial Recovery Desk → LangGraph / LangChain

## A. Architecture assessment (before)

The uploaded project was a working, well-scoped hackathon demo:

- **Frontend**: React + Vite + Tailwind-ish hand-rolled CSS. `App.jsx` holds
  top-level state (auth, tab, denial list, review queue) and passes callbacks
  down to `Dashboard`, `Queue`, `CaseDetail`, `ReviewQueue`, `UploadModal`.
  Clean, small, and worth keeping as-is.
- **Backend**: FastAPI + SQLAlchemy (async) + Postgres/SQLite. Routes were
  thin (`routes/denials.py`, `reviews.py`, `dashboard.py`, `auth.py`) and
  called a single `process()` function that ran the *entire* pipeline
  synchronously inside the `upload` endpoint: OCR → keyword-match "RAG" over
  `data/policies/*.txt` → one Ollama call (with a deterministic fallback
  classifier if Ollama was unreachable) → a hard-coded confidence threshold
  → either `AUTO_READY` or a `ReviewTask` row.
- **Models**: `User`, `Claim`, `Denial`, `Appeal`, `ReviewTask`, `Event`. This
  schema anticipated most of what a LangGraph state needs — it just didn't
  yet have columns for citations, critic scores, or a checkpoint thread id.
- **RocketRide**: `.rocketride/` and `rocketrider/` contained *documentation
  and a JSON schema* for an optional external pipeline-builder integration.
  It was never imported or executed by the FastAPI backend — there was no
  competing orchestration engine to reconcile.
- **What was already working well and worth preserving**: the OCR fallback
  chain (PDF text layer → pytesseract), the deterministic classifier
  fallback (so the demo never hard-fails without Ollama), JWT auth, and the
  whole frontend.
- **Gap vs. the target**: everything after "call Ollama once" was a single
  function, not a graph — no structured output validation, no real
  retrieval-with-citations, no critic step, no persisted pause/resume, and
  the confidence gate could only ever be a binary auto/human split.

## B. Migration plan (what changed, and why)

1. **New `app/ai/` package** — LangChain (`chains/`, `prompts/`,
   `retrieval/`, `tools/`, `llm.py`, `embeddings.py`) and LangGraph
   (`graph/state.py`, `graph/nodes/*`, `graph/routing.py`, `graph/graph.py`,
   `checkpoint.py`, `orchestrator.py`). Nothing in `app/ai/graph/nodes/*`
   touches the database directly — nodes are pure functions over
   `DenialState`, which makes them trivially unit-testable and keeps
   LangGraph's job (state/routing/retries/HIL/checkpoints) cleanly separated
   from LangChain's job (LLM calls/structured output/RAG/prompts), per the
   brief.
2. **`app/models.py`** — extended (not replaced) `Denial`/`Appeal` with the
   columns the graph state needs (`thread_id`, `policy_citations`,
   `evidence_citations`, `missing_evidence`, `appeal_score`,
   `appeal_issues`, `recovery_probability`, submission/tracking fields).
   Existing columns (`reason`, `confidence`, `status`, `evidence`, ...) are
   still populated for backward compatibility with anything reading them.
3. **`app/ai/orchestrator.py`** — the one place that knows how to turn a
   LangGraph run into DB rows: streams `graph.astream(..., stream_mode="updates")`,
   persists an `Event` row per node's audit event, and stops cleanly when it
   sees `"__interrupt__"` in the stream (the human-review pause). Resuming
   later (`resume_workflow`) uses `Command(resume=...)` against the same
   `thread_id` — this is what makes the pause survive a separate HTTP
   request or a server restart, backed by `AsyncSqliteSaver` (see
   `app/ai/checkpoint.py`, opened once in `app/main.py`'s lifespan).
4. **Routes** (`routes/denials.py`, `routes/reviews.py`) — `upload` and the
   new `analyze` endpoint now call `orchestrator.start_workflow` instead of
   the old synchronous `process()`. `POST /{id}/review`, `/approve`,
   `/reject` all resume the paused graph. The existing `/api/reviews/{task_id}`
   endpoint (used by the original `ReviewQueue` component) now also resolves
   the denial and calls the same `resume_workflow`, so both entry points
   share one code path.
5. **RAG** — real LangChain document loading + `RecursiveCharacterTextSplitter`
   + embeddings + retrieval, over both `data/policies/` (existing, expanded
   to cover all 8 denial categories) and a new `data/evidence/` corpus of
   synthetic supporting documents. The default embedding
   (`app/ai/embeddings.py::LocalHashingEmbeddings`) is dependency-free and
   deterministic — no model download, no GPU, no network — which matters
   for hackathon-demo reliability; `EMBEDDING_PROVIDER=ollama` is a one-line
   swap to a real embedding model if a bigger corpus is added later.
6. **Structured output + hallucination control** — `extraction_chain.py`,
   `classifier_chain.py`, `appeal_chain.py`, `critic_chain.py` all use
   `llm.with_structured_output(PydanticModel)`, and every chain has a
   deterministic fallback (keyword rules / templated letter) so the graph
   still completes if the LLM is unreachable — this generalizes the
   original project's existing Ollama-fallback pattern to every AI step
   instead of just classification.
7. **Human-in-the-loop** — `graph/nodes/human_review.py` uses LangGraph's
   `interrupt()`. Even a maximally confident, low-issue appeal still pauses
   here by default (`REQUIRE_HUMAN_APPROVAL=true`); disabling that flag only
   skips the interactive pause for low-value, high-confidence, high-critic-score
   cases, and even then the decision is written to the audit trail as an
   explicit auto-approval, never silently skipped. Reviewer buttons map to
   `APPROVE` / `EDIT` / `REQUEST_MORE_EVIDENCE` / `REJECT`; the last loops
   back to `evidence_retrieval` (capped at `MAX_REVISIONS = 2`) rather than
   dead-ending.
8. **RocketRide** — left untouched. It never executed anything in-process,
   so there was nothing to merge or remove; it remains available as an
   optional external integration point.
9. **Frontend** — kept as-is structurally. `CaseDetail.jsx` gained a
   pipeline-status strip (reads the new `GET /{id}/workflow` endpoint), an
   "Analyze Denial" button for `NEW` cases, a "Request more evidence"
   button, and a small panel showing the critic score/issues/missing
   evidence. `api.js` gained the corresponding calls. No component was
   rewritten from scratch.
10. **Tests** (`backend/tests/`) — the LLM is mocked in `conftest.py`
    (`app.ai.llm.get_chat_model` monkeypatched to always raise), so every
    test exercises the real deterministic fallback path with no network, no
    Ollama process, and no paid API key. Covers: classifier/extraction
    fallback correctness for every denial category, RAG citation shape,
    full graph run to the interrupt and back out via approve/reject/loop,
    orchestrator-DB integration, and a full HTTP-level lifecycle test via
    FastAPI's `TestClient` (register → upload → analyze → workflow status →
    approve → submitted).

## What I could not verify in this sandbox

This sandbox has no network access, so `pip install -r requirements.txt`
could not be run here and the test suite could not actually be executed —
only syntax-checked (`python -m py_compile`, which passed for every file).
Please run `pip install -r requirements.txt && pytest` locally before
relying on this; if the installed LangGraph/LangChain versions have drifted
from what's pinned, the most likely friction points are the exact
`interrupt()`/`Command(resume=...)` signature and `AsyncSqliteSaver`'s
constructor, both in active development upstream.
