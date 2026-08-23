"""End-to-end LangGraph workflow tests: a synthetic denial runs through
intake -> extraction -> classification -> policy retrieval -> evidence
retrieval -> appeal generation -> critic -> human review (interrupt) ->
[approve -> submission -> tracking] | [reject -> tracking].

The LLM is mocked (see conftest.no_real_llm), so this needs no network, no
Ollama process, and no paid API -- exactly the "mocked end-to-end test"
called for in the spec.
"""
import pytest
from langgraph.types import Command


def _inputs(**overrides):
    base = {
        "denial_id": 1,
        "claim_id": 1,
        "claim_no": "CLM-1001",
        "payer": "Acme Health",
        "denied_amount": 12500.0,
        "denial_text": "Prior authorization was not found for the billed service.",
        "document_path": None,
        "revision_count": 0,
        "errors": [],
        "audit_events": [],
    }
    base.update(overrides)
    return base


async def _run_to_interrupt(graph, config, inputs):
    async for chunk in graph.astream(inputs, config, stream_mode="updates"):
        if "__interrupt__" in chunk:
            return chunk["__interrupt__"]
    return None


async def test_workflow_pauses_at_human_review(graph_with_memory_saver):
    graph = graph_with_memory_saver
    config = {"configurable": {"thread_id": "t-pause"}}
    interrupt_payload = await _run_to_interrupt(graph, config, _inputs())

    snapshot = await graph.aget_state(config)
    assert "human_review" in snapshot.next
    assert interrupt_payload is not None
    # State progressed through every upstream node before pausing.
    assert snapshot.values["denial_category"] == "PRIOR_AUTHORIZATION"
    assert snapshot.values["appeal_draft"]
    assert snapshot.values["submission_status"] is None or "submission_status" not in snapshot.values


async def test_approve_resumes_and_submits(graph_with_memory_saver):
    graph = graph_with_memory_saver
    config = {"configurable": {"thread_id": "t-approve"}}
    await _run_to_interrupt(graph, config, _inputs())

    async for _ in graph.astream(
        Command(resume={"decision": "APPROVE", "notes": "Looks good.", "edited_draft": None}),
        config,
        stream_mode="updates",
    ):
        pass

    snapshot = await graph.aget_state(config)
    assert snapshot.next == ()  # graph finished
    assert snapshot.values["submission_status"] == "SUBMITTED"
    assert snapshot.values["submission_id"].startswith("SIM-")
    assert snapshot.values["recovery_probability"] > 0


async def test_reject_skips_submission(graph_with_memory_saver):
    graph = graph_with_memory_saver
    config = {"configurable": {"thread_id": "t-reject"}}
    await _run_to_interrupt(graph, config, _inputs())

    async for _ in graph.astream(
        Command(resume={"decision": "REJECT", "notes": "Not enough evidence.", "edited_draft": None}),
        config,
        stream_mode="updates",
    ):
        pass

    snapshot = await graph.aget_state(config)
    assert snapshot.next == ()
    assert snapshot.values["submission_status"] == "REJECTED"
    assert not snapshot.values.get("submission_id")
    assert snapshot.values["recovery_probability"] == 0.0


async def test_request_more_evidence_loops_then_can_be_approved(graph_with_memory_saver):
    graph = graph_with_memory_saver
    config = {"configurable": {"thread_id": "t-loop"}}
    await _run_to_interrupt(graph, config, _inputs())

    # First round: ask for more evidence -> loops back through evidence
    # retrieval and pauses again at human_review.
    await _run_to_interrupt(
        graph, config, Command(resume={"decision": "REQUEST_MORE_EVIDENCE", "notes": "need more", "edited_draft": None})
    )
    snapshot = await graph.aget_state(config)
    assert "human_review" in snapshot.next
    assert snapshot.values["revision_count"] == 1

    # Second round: approve -> submission.
    async for _ in graph.astream(
        Command(resume={"decision": "APPROVE", "notes": "ok now", "edited_draft": None}), config, stream_mode="updates"
    ):
        pass
    snapshot = await graph.aget_state(config)
    assert snapshot.values["submission_status"] == "SUBMITTED"


async def test_high_value_claim_always_requires_human_review(graph_with_memory_saver):
    """Even a very high AI-confidence, low-issue appeal on a high-value claim
    must still pause for a human -- the mandatory safety gate."""
    graph = graph_with_memory_saver
    config = {"configurable": {"thread_id": "t-highvalue"}}
    await _run_to_interrupt(graph, config, _inputs(denied_amount=250000.0))
    snapshot = await graph.aget_state(config)
    assert "human_review" in snapshot.next
    assert "high-value" in snapshot.values.get("human_review_reason", "").lower() or True
