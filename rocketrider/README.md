# RocketRide load-bearing integration

`denial-recovery-load-bearing.pipe` is the RocketRide entry pipeline for the
Denial Recovery Desk. It uses a webhook source, a native RocketRide agent,
local Ollama, RocketRide HTTP tooling, persistent in-pipeline memory, and a
response sink.

The agent calls the local FastAPI recovery endpoint, which runs the audited
LangGraph business workflow and returns the per-stage trace. This keeps the
healthcare business rules deterministic while RocketRide remains the AI
execution/orchestration layer.

## Run locally

1. Start Ollama and make sure `llama3.1:8b` is available.
2. Start the FastAPI backend on `http://localhost:8000`.
3. Open this `.pipe` in the RocketRide VS Code/Cursor extension.
4. Connect RocketRide in Local mode and run the pipeline from the webhook.
5. Send a JSON payload like:

```json
{
  "claim_no": "CLM-RR-001",
  "payer": "Demo Payer",
  "amount": 12500,
  "denial_text": "Prior authorization was not found for the submitted service."
}
```

The backend intentionally pauses at the human gate before submission. After
approval, the submission is a sandbox/mock payer action, never a real insurer.

## Why this is load-bearing

- RocketRide owns intake, agent reasoning, tool invocation, memory, and output.
- FastAPI/LangGraph owns deterministic healthcare workflow state and the human gate.
- The UI exposes batch throughput, wall time, estimated spend, and audit trace.
