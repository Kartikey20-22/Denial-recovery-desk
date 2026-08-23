from __future__ import annotations

import re

from pydantic import BaseModel, Field

from app.ai.llm import get_chat_model
from app.ai.prompts.extraction import EXTRACTION_PROMPT


class DenialExtraction(BaseModel):
    """Structured fields pulled from a denial letter. Every field is optional
    -- the extractor must never invent a value that isn't in the source
    text (see EXTRACTION_SYSTEM prompt)."""

    claim_number: str | None = Field(None, description="Claim number as it appears in the text")
    payer: str | None = None
    member_id: str | None = Field(None, description="Patient/member identifier")
    provider: str | None = None
    date_of_service: str | None = None
    billed_amount: float | None = None
    denied_amount: float | None = None
    denial_code: str | None = Field(None, description="Payer denial/remark code, e.g. CO-197")
    denial_reason_text: str | None = Field(None, description="Verbatim denial reason sentence")
    appeal_deadline: str | None = None


_AMOUNT_RE = re.compile(r"\$?\s*([0-9][0-9,]*\.?[0-9]{0,2})")
_CODE_RE = re.compile(r"\b(CO|CARC|PR)[- ]?\w{1,6}\b", re.IGNORECASE)


def _heuristic_extract(denial_text: str, claim_no: str, payer: str, amount: float) -> DenialExtraction:
    """Deterministic, dependency-free fallback used when the LLM is
    unavailable, so the graph keeps making progress in an offline demo."""
    code_match = _CODE_RE.search(denial_text or "")
    return DenialExtraction(
        claim_number=claim_no or None,
        payer=payer or None,
        denied_amount=amount or None,
        denial_code=code_match.group(0) if code_match else None,
        denial_reason_text=(denial_text or "").strip()[:300] or None,
    )


def extract_denial_fields(denial_text: str, claim_no: str = "", payer: str = "", amount: float = 0.0) -> DenialExtraction:
    try:
        llm = get_chat_model()
        structured = llm.with_structured_output(DenialExtraction)
        chain = EXTRACTION_PROMPT | structured
        result = chain.invoke(
            {"denial_text": denial_text, "claim_no": claim_no, "payer": payer, "amount": amount}
        )
        if isinstance(result, DenialExtraction):
            return result
        return DenialExtraction.model_validate(result)
    except Exception:
        return _heuristic_extract(denial_text, claim_no, payer, amount)
