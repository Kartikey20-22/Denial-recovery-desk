# Denial Recovery Desk — 10/10 Upgrade Notes

This package upgrades the existing project rather than replacing its AI foundation.

## Preserved

- React + Vite
- FastAPI
- PostgreSQL/SQLAlchemy
- LangChain
- LangGraph
- RAG + embeddings
- Local Ollama LLM
- Structured output chains
- AI critic
- Human-in-the-loop interrupt/resume
- SQLite LangGraph checkpointing
- Audit events
- Deterministic fallback chains

## Added/extended

- Screenshot-inspired enterprise healthcare SaaS dashboard
- KPI cards connected to backend aggregations
- Denial process visualization tied to workflow state
- Recent denials and notifications
- Appeals, documents, payer rules, users, reports, settings pages
- Case detail page with AI analysis + RAG citations + critic + audit timeline
- Deterministic payer/payment outcome tracking
- Payer simulator for demo environments
- Payment verification and partial-payment state
- Completion engine: submitted + payer approved + verified payment => COMPLETED
- Recovery dashboard counts only verified payments
- Demo seed data with realistic workflow/outcome states
- More robust CORS parsing for the existing `.env` format

## Important demo distinction

The payer and payment endpoints are a local simulator. They do not claim to be a real insurance-company integration. For a production deployment, replace the simulator calls with an authorized payer API/webhook/EDI integration while keeping the same outcome/completion interfaces.

## Run

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Set DATABASE_URL to your PostgreSQL instance.
python seed_demo.py
python -m uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

Demo account:

- Email: `demo@denialdesk.local`
- Password: `Demo@12345`

## End-to-end demo

1. Open Dashboard.
2. Open a denial.
3. Inspect the LangGraph pipeline.
4. For a NEW case, run Analyze Denial.
5. Approve at Human Review.
6. Use Simulate Payer Approval.
7. Use Verify Payment.
8. Confirm the case becomes COMPLETED and the verified amount appears in Money Recovered.
