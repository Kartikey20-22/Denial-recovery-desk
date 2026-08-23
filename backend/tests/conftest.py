"""Shared test fixtures.

Everything here runs fully offline: the LLM factory is monkeypatched to
always fail, which forces every chain in app/ai/chains/* onto its
deterministic fallback path -- so these tests never need Ollama, a paid API
key, or network access, per the "mock the LLM" testing requirement.
"""
import os
import sys
from pathlib import Path

TEST_DIR = Path(__file__).resolve().parent
BACKEND_DIR = TEST_DIR.parent

# Point the app at an isolated sqlite DB + checkpoint file for the test run,
# and use the dependency-free local embedding provider. Must happen BEFORE
# `app.config` (and anything importing it) is imported for the first time.
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{TEST_DIR}/test.db")
os.environ.setdefault("CHECKPOINT_DB_PATH", str(TEST_DIR / "test_checkpoints.sqlite"))
os.environ.setdefault("EMBEDDING_PROVIDER", "local")
os.environ.setdefault("LLM_PROVIDER", "ollama")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("REQUIRE_HUMAN_APPROVAL", "true")
os.environ.setdefault("HIGH_VALUE_THRESHOLD", "100000")
os.environ.setdefault("CONFIDENCE_THRESHOLD", "0.90")

sys.path.insert(0, str(BACKEND_DIR))

import pytest

from app.ai.llm import LLMUnavailableError


@pytest.fixture(autouse=True)
def no_real_llm(monkeypatch):
    """Force every chain onto its offline heuristic fallback."""

    def _boom(*args, **kwargs):
        raise LLMUnavailableError("LLM disabled in tests")

    monkeypatch.setattr("app.ai.llm.get_chat_model", _boom)
    yield


@pytest.fixture()
async def graph_with_memory_saver():
    """A compiled graph backed by an in-memory checkpointer -- fast, no
    disk I/O, isolated per test."""
    from langgraph.checkpoint.memory import MemorySaver

    from app.ai.graph.graph import build_graph

    saver = MemorySaver()
    return build_graph(checkpointer=saver)


@pytest.fixture()
async def db_engine(tmp_path):
    """A fresh sqlite database for a single test."""
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.db import Base

    db_path = tmp_path / "orchestrator_test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async with engine.begin() as conn:
        from app import models  # noqa: F401  (register models on Base metadata)

        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture()
def db_sessionmaker(db_engine):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    return async_sessionmaker(db_engine, expire_on_commit=False)
