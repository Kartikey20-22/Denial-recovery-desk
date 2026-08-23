from __future__ import annotations

from pydantic import BaseModel, Field

from app.ai.llm import get_chat_model
from app.ai.prompts.appeal import APPEAL_PROMPT


class AppealDraft(BaseModel):
    letter: str = Field(description="The full appeal letter text")
    evidence_used: list[str] = Field(default_factory=list, description="Evidence source names actually cited")
    policy_references: list[str] = Field(default_factory=list, description="Policy source names actually cited")
    missing_evidence: list[str] = Field(default_factory=list, description="Evidence still needed, if any")
    confidence: float = Field(ge=0, le=1, description="Model's own confidence the letter is well supported")


def _format_context(items: list[dict]) -> str:
    if not items:
        return "None retrieved."
    return "\n\n".join(f"[{it.get('source', 'unknown')}] {it.get('content', '')}" for it in items)


def _heuristic_appeal(
    claim_no: str, payer: str, denied_amount: float, category: str, denial_reason: str,
    policy_hits: list[dict], evidence_hits: list[dict],
) -> AppealDraft:
    policy_names = sorted({h.get("source", "") for h in policy_hits if h.get("source")})
    evidence_names = sorted({h.get("source", "") for h in evidence_hits if h.get("source")})
    missing = [] if evidence_hits else ["No supporting evidence on file for this claim yet."]
    letter = (
        f"RE: Appeal of Denied Claim {claim_no or '[unknown]'}\n"
        f"Payer: {payer or '[unknown]'}\n"
        f"Denied amount: {denied_amount if denied_amount else '[unknown]'}\n\n"
        f"This letter appeals the denial categorized as {category or 'OTHER'}.\n\n"
        f"Denial reason on file: {denial_reason or 'not provided'}\n\n"
        + ("Relevant payer policy: " + ", ".join(policy_names) + ".\n\n" if policy_names else
           "No matching payer policy section was retrieved; policy citation should be added before submission.\n\n")
        + ("Supporting evidence on file: " + ", ".join(evidence_names) + ".\n\n" if evidence_names else
           "No supporting evidence documents were retrieved for this claim; please attach the relevant "
           "records before this appeal is submitted.\n\n")
        + "NOTE: This is a local offline fallback draft (LLM unavailable). A reviewer must verify every "
          "fact above against the source record before this appeal is submitted.\n"
    )
    return AppealDraft(
        letter=letter,
        evidence_used=evidence_names,
        policy_references=policy_names,
        missing_evidence=missing,
        confidence=0.4,
    )


def generate_appeal(
    claim_no: str, payer: str, denied_amount: float, category: str, denial_reason: str,
    policy_hits: list[dict], evidence_hits: list[dict],
) -> AppealDraft:
    try:
        llm = get_chat_model()
        structured = llm.with_structured_output(AppealDraft)
        chain = APPEAL_PROMPT | structured
        result = chain.invoke(
            {
                "claim_no": claim_no or "unknown",
                "payer": payer or "unknown",
                "denied_amount": denied_amount,
                "denial_category": category,
                "denial_reason": denial_reason,
                "policy_context": _format_context(policy_hits),
                "evidence_context": _format_context(evidence_hits),
            }
        )
        draft = result if isinstance(result, AppealDraft) else AppealDraft.model_validate(result)
        if not evidence_hits and not draft.missing_evidence:
            draft.missing_evidence.append("No supporting evidence documents were retrieved for this claim.")
        return draft
    except Exception:
        return _heuristic_appeal(claim_no, payer, denied_amount, category, denial_reason, policy_hits, evidence_hits)
