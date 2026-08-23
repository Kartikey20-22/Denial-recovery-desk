"""Manages the LangGraph checkpointer lifecycle.

The workflow must be resumable after human approval -- a human review
genuinely pauses graph execution (via `interrupt()` in
app/ai/graph/nodes/human_review.py) and needs to resume later, potentially
in a completely separate HTTP request/process restart. LangGraph's
AsyncSqliteSaver persists the paused state to a local SQLite file so that
works without any extra infrastructure (no Redis/Postgres required just for
checkpoints).

The saver's context manager must stay open for the lifetime of the app, so
it's opened once in FastAPI's lifespan (see app/main.py) and the compiled
graph is built once and reused across requests.
"""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from app.ai.graph.graph import build_graph
from app.config import settings

_graph = None


def get_graph():
    if _graph is None:
        raise RuntimeError("Graph not initialized yet -- app lifespan must run first.")
    return _graph


@asynccontextmanager
async def graph_lifespan():
    """Async context manager that opens the checkpointer, compiles the
    graph once, and makes it available via get_graph() for the app's
    lifetime."""
    global _graph
    path = Path(settings.checkpoint_db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    async with AsyncSqliteSaver.from_conn_string(str(path)) as saver:
        _graph = build_graph(checkpointer=saver)
        try:
            yield _graph
        finally:
            _graph = None
