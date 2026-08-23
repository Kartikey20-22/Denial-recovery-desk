# Denial Recovery Desk — Enterprise UI Upgrade

The React application now follows the supplied Denial Recovery Desk dashboard reference while preserving the existing FastAPI + PostgreSQL + LangGraph/LangChain foundation.

## Important behavior

- KPI cards use backend aggregations.
- Recovery money counts **verified payments only**.
- Payer approval is separate from payment receipt.
- Case completion is deterministic: submitted + payer approved + verified payment.
- Human review remains the safety gate when configured.
- The payer/payment buttons in the case view use the included **Payer Simulator** for local demos; this is intentionally not presented as a real insurance integration.
- LangGraph workflow and checkpointing are preserved.
- Existing RAG, embeddings, structured output, critic and fallback chains are preserved.

## Demo login

`demo@denialdesk.local` / `Demo@12345`

## Demo flow

1. Open Dashboard.
2. Open a denial.
3. Run/inspect the LangGraph pipeline.
4. Approve the appeal at Human Review.
5. Use **Simulate Payer Approval**.
6. Use **Verify Payment**.
7. The case becomes **COMPLETED** and the recovered amount appears in the dashboard.
