# Denial Recovery Desk — RocketRide architecture

```text
                    ┌──────────────────────────────┐
                    │ React Recovery Desk           │
                    │ Dashboard / Review Queue      │
                    └──────────────┬───────────────┘
                                   │
                         batch / review / upload
                                   │
                    ┌──────────────▼───────────────┐
                    │ FastAPI Application           │
                    │ auth + DB + sandbox actions   │
                    └──────────────┬───────────────┘
                                   │
                   ┌───────────────▼────────────────┐
                   │ LangGraph audited workflow      │
                   │                                 │
                   │ Intake → Extraction             │
                   │ → Classification                │
                   │ → Policy RAG                     │
                   │ → Evidence RAG                   │
                   │ → Appeal Generation              │
                   │ → Critic                          │
                   │ → HUMAN GATE                     │
                   │ → Sandbox Submission             │
                   │ → Outcome Tracking                │
                   └───────────────▲────────────────┘
                                   │ tool call
                 ┌─────────────────┴─────────────────┐
                 │ RocketRide load-bearing pipeline   │
                 │                                     │
                 │ Webhook → RocketRide Agent          │
                 │             ↕ Ollama                 │
                 │             ↕ HTTP Recovery API      │
                 │             ↕ Outcome Memory         │
                 │             → Trace Response         │
                 └─────────────────────────────────────┘
```

RocketRide is not decorative: it receives the external denial payload, reasons
about whether the payload is complete, invokes the recovery API as a tool,
keeps in-pipeline memory, and returns the trace. The FastAPI/LangGraph layer
remains responsible for deterministic healthcare state transitions and the
mandatory human gate.
