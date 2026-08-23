# RocketRide Buildathon submission hardening

This release is structured around the judging bar in the supplied RocketRide
Buildathon brief: a specific buyer, automatic work, real-world action, human
oversight, batch processing, predictable cost, graceful failure, and a
load-bearing RocketRide pipeline.

## P0 coverage

| Requirement | Implementation |
|---|---|
| Actual `.pipe` | `rocketrider/denial-recovery-load-bearing.pipe` |
| RocketRide orchestration | Native RocketRide agent + Ollama + HTTP tool + memory |
| Batch processing | `POST /api/denials/batch-analyze` + Dashboard batch monitor |
| Human approval | LangGraph interrupt + Review Queue; enabled by default |
| Sandbox action | Submission + payer-response + payment simulator |
| Malformed input | Upload validation + batch isolation + RocketRide process validation |
| Execution trace | Event timeline + per-stage workflow endpoint + RocketRide response trace |
| Cost/run | Per-denial elapsed time, token estimate, estimated cost, batch rollup |

## P1 coverage

- Outcome feedback is exposed through `/api/dashboard/learning` and is grouped by payer + denial category.
- Payer-specific recovery history is derived from recovered cases and shown as reusable playbook signals.
- Dashboard now exposes recovered money and the latest RocketRide batch metrics.
- `.env.example` contains all new operational settings.
- README and architecture documentation explain local/cloud deployment.

## Demo sequence

1. Open Dashboard and show the RocketRide Run Monitor.
2. Run a 25-case batch. Show requested/completed/failed/human-review counts,
   wall-clock time and estimated spend.
3. Open one case and show the stage trace.
4. Show the generated appeal and citations.
5. Stop at the human gate; approve/edit/reject from Review Queue.
6. Show the sandbox submission ID.
7. Record a simulated payer approval and payment to demonstrate recovery.
8. Re-open the Dashboard and show recovered revenue and outcome feedback.

## Cost statement

With the default local Ollama provider, the application reports **$0 API
spend**. For a cloud provider, the application reports a conservative
estimated spend using the configured `ESTIMATED_CLOUD_COST_PER_1K_TOKENS_USD`.
This is an estimate, not a provider invoice.
