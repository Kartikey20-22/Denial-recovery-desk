"""Builds the primary LangGraph workflow.

    START -> intake -> extraction -> classifier -> policy_retrieval
          -> evidence_retrieval -> appeal_generator -> appeal_critic
          -> human_review --(REJECT)--------------------> tracking -> END
                          --(REQUEST_MORE_EVIDENCE)-----> evidence_retrieval (loop, capped)
                          --(APPROVE / EDIT / auto)------> submission -> tracking -> END

LangGraph owns workflow state, node execution, routing/branches, retries,
the human-in-the-loop interrupt, and checkpoint persistence (so a paused
workflow survives across separate HTTP requests). LangChain (see
app/ai/chains/*.py) owns the actual LLM calls, structured-output parsing,
RAG retrieval, and prompt templates used *inside* each node.
"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from app.ai.graph.nodes.appeal_critic import appeal_critic_node
from app.ai.graph.nodes.appeal_generator import appeal_generator_node
from app.ai.graph.nodes.classifier import classifier_node
from app.ai.graph.nodes.evidence_retrieval import evidence_retrieval_node
from app.ai.graph.nodes.extraction import extraction_node
from app.ai.graph.nodes.human_review import human_review_node
from app.ai.graph.nodes.intake import intake_node
from app.ai.graph.nodes.policy_retrieval import policy_retrieval_node
from app.ai.graph.nodes.submission import submission_node
from app.ai.graph.nodes.tracking import tracking_node
from app.ai.graph.routing import route_after_human_review
from app.ai.graph.state import DenialState


def build_graph(checkpointer=None):
    builder = StateGraph(DenialState)

    builder.add_node("intake", intake_node)
    builder.add_node("extraction", extraction_node)
    builder.add_node("classifier", classifier_node)
    builder.add_node("policy_retrieval", policy_retrieval_node)
    builder.add_node("evidence_retrieval", evidence_retrieval_node)
    builder.add_node("appeal_generator", appeal_generator_node)
    builder.add_node("appeal_critic", appeal_critic_node)
    builder.add_node("human_review", human_review_node)
    builder.add_node("submission", submission_node)
    builder.add_node("tracking", tracking_node)

    builder.add_edge(START, "intake")
    builder.add_edge("intake", "extraction")
    builder.add_edge("extraction", "classifier")
    builder.add_edge("classifier", "policy_retrieval")
    builder.add_edge("policy_retrieval", "evidence_retrieval")
    builder.add_edge("evidence_retrieval", "appeal_generator")
    builder.add_edge("appeal_generator", "appeal_critic")
    builder.add_edge("appeal_critic", "human_review")

    builder.add_conditional_edges(
        "human_review",
        route_after_human_review,
        {
            "submission": "submission",
            "evidence_retrieval": "evidence_retrieval",
            "tracking": "tracking",
        },
    )
    builder.add_edge("submission", "tracking")
    builder.add_edge("tracking", END)

    return builder.compile(checkpointer=checkpointer)


# Ordered list used by the frontend pipeline visualization / GET .../workflow
NODE_ORDER = [
    "intake",
    "extraction",
    "classifier",
    "policy_retrieval",
    "evidence_retrieval",
    "appeal_generator",
    "appeal_critic",
    "human_review",
    "submission",
    "tracking",
]
