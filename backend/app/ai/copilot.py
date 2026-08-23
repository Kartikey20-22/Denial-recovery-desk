from __future__ import annotations

import re
from typing import Any

from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.ai.llm import LLMUnavailableError, get_chat_model
from app.ai.retrieval.evidence_retriever import retrieve_evidence
from app.ai.retrieval.policy_retriever import retrieve_policy
from app.db import Session
from app.models import Claim, Denial

CLAIM_RE = re.compile(r"\bCLM-\d{4,}\b", re.IGNORECASE)

COPILOT_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are Denial Recovery Desk AI Copilot running on a local Llama model.
You are a retrieval-augmented assistant for a synthetic healthcare-claims demo.

STRICT GROUNDING RULES:
1. Use ONLY the CASE CONTEXT and RETRIEVED SOURCES supplied below.
2. Never invent patient facts, payer rules, codes, dates, authorization numbers, payments, or evidence.
3. If the supplied context does not answer the question, explicitly say that the information was not found.
4. Distinguish clearly between FACTS FROM DATA, POLICY/EVIDENCE, and RECOMMENDATION.
5. Do not claim an appeal was submitted or a payment was verified unless the case context explicitly says so.
6. Keep answers concise but useful. Cite source filenames in square brackets, e.g. [prior_authorization.txt].
7. This is synthetic demo data; do not present it as real patient information.

Return a natural-language answer, not JSON.""",
        ),
        (
            "human",
            """USER QUESTION:
{question}

CASE CONTEXT:
{case_context}

RETRIEVED POLICY SOURCES:
{policy_context}

RETRIEVED EVIDENCE SOURCES:
{evidence_context}

Answer the user's question using only the material above.""",
        ),
    ]
)


class CopilotRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    claim_no: str | None = None
    history: list[dict[str, str]] = Field(default_factory=list, max_length=12)


class CopilotResponse(BaseModel):
    answer: str
    claim_no: str | None = None
    model: str
    provider: str
    sources: list[dict[str, Any]] = Field(default_factory=list)
    grounded: bool = True


def _claim_from_question(question: str, explicit: str | None) -> str | None:
    if explicit:
        return explicit.upper()
    match = CLAIM_RE.search(question or "")
    return match.group(0).upper() if match else None


async def _case_context(claim_no: str | None) -> str:
    if not claim_no:
        return "No specific claim was identified."

    async with Session() as session:
        claim = await session.scalar(select(Claim).where(Claim.claim_no == claim_no))
        if not claim:
            return f"No claim record was found for {claim_no}."

        denials = (
            await session.scalars(
                select(Denial)
                .where(Denial.claim_id == claim.id)
                .order_by(Denial.id.desc())
            )
        ).all()

        lines = [
            f"Claim: {claim.claim_no}",
            f"Payer: {claim.payer}",
            f"Amount: {float(claim.amount or 0):.2f}",
            f"Patient reference: {claim.patient_ref}",
        ]

        for d in denials[:3]:
            lines.extend(
                [
                    f"Denial ID: {d.id}",
                    f"Denial reason: {d.reason or 'unknown'}",
                    f"Denial text: {d.text}",
                    f"AI confidence: {float(d.confidence or 0):.2f}",
                    f"Status: {d.status}",
                    f"Outcome: {d.outcome or 'not recorded'}",
                    f"Recovered amount: {float(d.recovered_amount or 0):.2f}",
                    f"AI explanation: {d.explanation or 'not recorded'}",
                    f"Stored evidence: {d.evidence or 'not recorded'}",
                ]
            )

        return "\n".join(lines)


def _format_hits(hits: list[dict]) -> str:
    if not hits:
        return "No sources retrieved."

    blocks = []
    for h in hits:
        blocks.append(
            f"[{h.get('source', 'unknown')}]\n"
            f"{h.get('content', '')}"
        )
    return "\n\n".join(blocks)


def _fallback_answer(question: str, claim_no: str | None, policy_hits: list[dict], evidence_hits: list[dict], case_context: str) -> str:
    source_names = [h.get("source") for h in policy_hits + evidence_hits if h.get("source")]
    unique_sources = list(dict.fromkeys(source_names))

    parts = [
        "Llama is currently unavailable, so I used the local RAG fallback.",
        "",
        f"Question: {question}",
    ]

    if claim_no:
        parts.extend(["", f"Case: {claim_no}", case_context])

    if policy_hits:
        parts.extend(
            [
                "",
                "Relevant policy:",
                policy_hits[0]["content"],
                f"Source: [{policy_hits[0]['source']}]",
            ]
        )

    if evidence_hits:
        parts.extend(
            [
                "",
                "Relevant evidence:",
                evidence_hits[0]["content"],
                f"Source: [{evidence_hits[0]['source']}]",
            ]
        )

    if not policy_hits and not evidence_hits:
        parts.extend(
            [
                "",
                "I could not find a supporting policy or evidence source in the local RAG corpus.",
            ]
        )

    parts.extend(
        [
            "",
            "Sources used: " + (", ".join(f"[{x}]" for x in unique_sources) if unique_sources else "none"),
        ]
    )
    return "\n".join(parts)


async def chat(request: CopilotRequest) -> CopilotResponse:
    question = request.question.strip()
    claim_no = _claim_from_question(question, request.claim_no)

    case_context = await _case_context(claim_no)

    retrieval_query = question
    if claim_no:
        retrieval_query = f"{claim_no} {question}"

    policy_hits = retrieve_policy(retrieval_query, k=4)
    evidence_hits = retrieve_evidence(
        retrieval_query,
        claim_no=claim_no,
        k=4,
    )

    # A compact, citation-friendly source list for the UI.
    sources = []
    seen = set()
    for kind, hits in (("policy", policy_hits), ("evidence", evidence_hits)):
        for hit in hits:
            key = (kind, hit.get("source"))
            if key in seen:
                continue
            seen.add(key)
            sources.append(
                {
                    "type": kind,
                    "source": hit.get("source", "unknown"),
                    "score": hit.get("relevance_score", 0),
                }
            )

    try:
        llm = get_chat_model(temperature=0.1)
        chain = COPILOT_PROMPT | llm
        response = await chain.ainvoke(
            {
                "question": question,
                "case_context": case_context,
                "policy_context": _format_hits(policy_hits),
                "evidence_context": _format_hits(evidence_hits),
            }
        )
        answer = getattr(response, "content", str(response)).strip()
        return CopilotResponse(
            answer=answer,
            claim_no=claim_no,
            model=getattr(llm, "model", None) or "llama3.1:8b",
            provider="ollama",
            sources=sources,
            grounded=True,
        )
    except Exception:
        return CopilotResponse(
            answer=_fallback_answer(
                question,
                claim_no,
                policy_hits,
                evidence_hits,
                case_context,
            ),
            claim_no=claim_no,
            model="local-rag-fallback",
            provider="fallback",
            sources=sources,
            grounded=True,
        )
