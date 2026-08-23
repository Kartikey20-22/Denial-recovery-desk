from __future__ import annotations

from app.ai.chains.classifier_chain import classify_denial
from app.ai.graph.state import DenialState


async def classifier_node(state: DenialState) -> dict:
    try:
        result = classify_denial(state.get("denial_text", ""))
        pct = round(result.confidence * 100)
        return {
            "denial_category": result.category.value,
            "denial_reason": result.explanation,
            "classification_confidence": result.confidence,
            "classification_supporting_text": result.supporting_text,
            "audit_events": [
                {
                    "stage": "CLASSIFICATION",
                    "status": "COMPLETED",
                    "message": f"Classified as {result.category.value} ({pct}% confidence).",
                }
            ],
        }
    except Exception as exc:
        return {
            "denial_category": "OTHER",
            "classification_confidence": 0.0,
            "errors": [f"Classification failed: {exc}"],
            "audit_events": [{"stage": "CLASSIFICATION", "status": "FAILED", "message": str(exc)}],
        }
