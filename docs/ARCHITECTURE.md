# System Architecture

## Core flow
React Dashboard -> FastAPI -> PostgreSQL
FastAPI -> OCR -> Local RAG -> Ollama llama3.1:8b
LLM result -> deterministic confidence gate
AUTO_READY -> appeal workflow
HUMAN_REVIEW -> reviewer queue -> approval/rejection

## Why local LLM?
No external model API is required. Denial text remains on the local machine.
The LLM is advisory; deterministic business rules remain the final automation gate.

## RocketRide
RocketRide can be connected as an optional orchestration layer. Keep the FastAPI
pipeline as the source of truth so the application remains runnable if RocketRide
is unavailable.
