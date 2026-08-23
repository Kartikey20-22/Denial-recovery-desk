from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from app.ai.llm import get_chat_model
from app.ai.prompts.classifier import CLASSIFIER_PROMPT


class DenialCategory(str, Enum):
    PRIOR_AUTHORIZATION = "PRIOR_AUTHORIZATION"
    MEDICAL_NECESSITY = "MEDICAL_NECESSITY"
    CODING_ERROR = "CODING_ERROR"
    MISSING_DOCUMENTATION = "MISSING_DOCUMENTATION"
    TIMELY_FILING = "TIMELY_FILING"
    ELIGIBILITY = "ELIGIBILITY"
    DUPLICATE_CLAIM = "DUPLICATE_CLAIM"
    OTHER = "OTHER"


class DenialClassification(BaseModel):
    category: DenialCategory
    explanation: str = Field(description="Why this category was chosen")
    confidence: float = Field(ge=0, le=1)
    supporting_text: str = Field(description="Verbatim phrase(s) from the denial text supporting the category")


_KEYWORDS: list[tuple[str, DenialCategory, float]] = [
    ("prior authorization", DenialCategory.PRIOR_AUTHORIZATION, 0.94),
    ("prior auth", DenialCategory.PRIOR_AUTHORIZATION, 0.92),
    ("duplicate", DenialCategory.DUPLICATE_CLAIM, 0.9),
    ("timely filing", DenialCategory.TIMELY_FILING, 0.9),
    ("filing limit", DenialCategory.TIMELY_FILING, 0.88),
    ("eligib", DenialCategory.ELIGIBILITY, 0.85),
    ("coverage terminated", DenialCategory.ELIGIBILITY, 0.85),
    ("cpt", DenialCategory.CODING_ERROR, 0.85),
    ("icd", DenialCategory.CODING_ERROR, 0.85),
    ("coding", DenialCategory.CODING_ERROR, 0.82),
    ("medical necessity", DenialCategory.MEDICAL_NECESSITY, 0.68),
    ("documentation", DenialCategory.MISSING_DOCUMENTATION, 0.8),
    ("records were not attached", DenialCategory.MISSING_DOCUMENTATION, 0.86),
]


def _heuristic_classify(denial_text: str) -> DenialClassification:
    text = (denial_text or "").lower()
    for kw, category, conf in _KEYWORDS:
        if kw in text:
            return DenialClassification(
                category=category,
                explanation=f"Local fallback classifier matched keyword '{kw}'.",
                confidence=conf,
                supporting_text=denial_text.strip()[:200],
            )
    return DenialClassification(
        category=DenialCategory.OTHER,
        explanation="Local fallback classifier found no strong keyword match.",
        confidence=0.5,
        supporting_text=denial_text.strip()[:200],
    )


def classify_denial(denial_text: str) -> DenialClassification:
    try:
        llm = get_chat_model()
        structured = llm.with_structured_output(DenialClassification)
        chain = CLASSIFIER_PROMPT | structured
        result = chain.invoke({"denial_text": denial_text})
        if isinstance(result, DenialClassification):
            return result
        return DenialClassification.model_validate(result)
    except Exception:
        return _heuristic_classify(denial_text)
