from __future__ import annotations

from pathlib import Path

from app.ai.graph.state import DenialState
from app.services.ocr import extract as ocr_extract

MAX_INLINE_CHARS = 6000  # don't blast a huge raw document straight at the LLM


async def intake_node(state: DenialState) -> dict:
    """Normalize whatever came in (uploaded file, raw text, or an existing
    denial record's stored text) into `denial_text` on the state.

    Supports JPG/PNG/PDF via OCR, or plain text passed straight through.
    """
    text = state.get("denial_text") or ""
    doc_path = state.get("document_path")

    if doc_path:
        suffix = Path(doc_path).suffix.lower()
        if suffix in {".pdf", ".png", ".jpg", ".jpeg", ".webp", ".tiff"}:
            try:
                ocr_text = await ocr_extract(doc_path)
                if ocr_text:
                    text = ocr_text
            except Exception as exc:  # OCR failure must not crash the graph
                return {
                    "denial_text": text,
                    "errors": [f"OCR failed for {doc_path}: {exc}"],
                    "audit_events": [
                        {"stage": "INTAKE", "status": "COMPLETED", "message": "Denial received; OCR failed, using provided text."}
                    ],
                }

    if len(text) > MAX_INLINE_CHARS:
        text = text[:MAX_INLINE_CHARS] + "\n...[truncated for LLM input]..."

    return {
        "denial_text": text,
        "audit_events": [{"stage": "INTAKE", "status": "COMPLETED", "message": "Denial intake normalized."}],
    }
