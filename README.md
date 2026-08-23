# Denial Recovery Desk — LangGraph / LangChain Edition

Hackathon-ready full-stack demo using React + FastAPI + PostgreSQL, with the
AI orchestration layer rebuilt on **LangGraph** (workflow state, routing,
retries, human-in-the-loop, checkpointing) and **LangChain** (LLM calls,
structured output, prompts, RAG retrieval). Everything runs locally against
Ollama by default; Anthropic/Groq are drop-in alternatives via one env var.

> ⚠️ **Synthetic Data — No Real PHI.** Every claim, denial, policy, and
> evidence document in this repo is fabricated for demo purposes.

## What changed in this edition

The AI/pipeline layer was migrated from a single-pass Ollama call + keyword
RAG into a proper **LangGraph state machine**, while the FastAPI backend,
React frontend, and SQLAlchemy models were kept and *extended* rather than
rewritten. See `MIGRATION.md` for the full before/after assessment.

- **LangGraph** now owns the 10-node workflow graph, conditional routing,
  the mandatory human-approval interrupt, and checkpoint persistence (a
  paused review genuinely survives a server restart).
- **LangChain** now owns every LLM call: structured-output extraction and
  classification, a real RAG pipeline (document loaders → splitter →
  embeddings → in-memory vector index → retriever) over the synthetic
  policy/evidence corpus, and the appeal-generation / critic chains.
- Every chain has a **deterministic offline fallback** (no LLM required) so
  the demo keeps working if Ollama isn't running — this was already true of
  the original project's classifier, and now extends to every AI step.
- **RocketRide** (`.rocketride/`, `rocketrider/`) was inspected first: it was
  documentation/schema scaffolding for an *optional external* pipeline
  builder integration point and never executed anything inside this
  backend, so there was no competing orchestration engine to remove.
  LangGraph is the only in-process AI workflow engine; RocketRide is left
  untouched as an optional future outer-integration point (see
  `.rocketride/docs/ROCKETRIDE_README.md`).

## Target LangGraph workflow

```
START -> intake -> extraction -> classifier -> policy_retrieval
      -> evidence_retrieval -> appeal_generator -> appeal_critic
      -> human_review ──(REJECT)───────────────────► tracking -> END
                      ──(REQUEST_MORE_EVIDENCE)────► evidence_retrieval (loops, capped)
                      ──(APPROVE / EDIT / auto)────► submission -> tracking -> END
```

Healthcare claim appeals are **never blindly auto-submitted**. Even a
high-confidence, high-critic-score appeal pauses at `human_review` by
default (`REQUIRE_HUMAN_APPROVAL=true`); the gate is configurable for demo
purposes but every path — including an auto-approval — is fully audited.

## Architecture

```
React (Vite) -> FastAPI -> PostgreSQL (or SQLite for tests)
                   |
                   +-> app/ai/graph  (LangGraph: state, nodes, routing, checkpoints)
                          |
                          +-> app/ai/chains      (LangChain: LLM calls, structured output)
                          +-> app/ai/retrieval   (LangChain: RAG over policies/evidence)
                          +-> app/ai/tools       (LangChain: policy_search, evidence_search)
                          +-> app/ai/llm.py      (provider factory: ollama | anthropic | groq)
```

## Run (macOS)

```bash
# Optional: local LLM
ollama serve
ollama pull llama3.1:8b

# Optional: Postgres (SQLite works fine for the demo; see DATABASE_URL)
open -a Docker
docker compose up -d postgres

# Terminal 1 — backend
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python seed_demo.py
python -m uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 — login with `demo@denialdesk.local` /
`Demo@12345`, open a seeded case, click **Analyze Denial**, and follow the
pipeline through to the human review gate.

API docs: http://localhost:8000/docs

## Tests

```bash
cd backend
source .venv/bin/activate
pytest
```

Every test mocks the LLM (forces the deterministic fallback path in
`app/ai/chains/*.py`) and runs against an isolated SQLite database and an
in-memory LangGraph checkpointer — no Ollama process, API key, or network
access required.

## Configuration

See `.env.example` for the full list. The important switches:

| Variable | Purpose |
|---|---|
| `LLM_PROVIDER` | `ollama` (default) \| `anthropic` \| `groq` |
| `EMBEDDING_PROVIDER` | `local` (default, dependency-free) \| `ollama` |
| `REQUIRE_HUMAN_APPROVAL` | `true` (default, recommended) \| `false` |
| `CONFIDENCE_THRESHOLD` / `HIGH_VALUE_THRESHOLD` | routing/reason thresholds |
| `CHECKPOINT_DB_PATH` | where LangGraph persists paused workflows |

Use synthetic data only. Do not upload real PHI.

## RocketRide Buildathon mode

This project includes a load-bearing RocketRide pipeline at
`rocketrider/denial-recovery-load-bearing.pipe`. RocketRide handles webhook
intake, agent reasoning, local Ollama, HTTP tool invocation, memory and the
execution trace; the FastAPI/LangGraph layer performs the audited denial
recovery workflow and mandatory human approval.

### Buildathon demo

- Dashboard → **Run 25-case Batch** to demonstrate batch throughput, failures,
  human-review count, wall time and estimated cost.
- Review Queue → approve/edit/reject before sandbox submission.
- Case → workflow timeline for the complete execution trace.
- Dashboard → recovered revenue and outcome-learning signals.

See `docs/ROCKETRIDE_SUBMISSION.md` and `docs/ARCHITECTURE_ROCKETRIDE.md`.
# Denial-recovery-desk
# Denial-recovery-desk
