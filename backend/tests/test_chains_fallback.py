"""Unit tests for the deterministic offline fallback in each chain.

These exercise the classifier and extraction chains' heuristics directly --
no LangGraph, no DB, no network. Because `no_real_llm` (conftest.py) forces
LLMUnavailableError, every call here already exercises the real
production fallback path, not a special test-only code path.
"""
from app.ai.chains.classifier_chain import DenialCategory, classify_denial
from app.ai.chains.extraction_chain import extract_denial_fields


def test_classify_prior_authorization():
    r = classify_denial("Prior authorization was not found for the billed service.")
    assert r.category == DenialCategory.PRIOR_AUTHORIZATION
    assert 0 <= r.confidence <= 1


def test_classify_timely_filing():
    r = classify_denial("Claim exceeded timely filing limit.")
    assert r.category == DenialCategory.TIMELY_FILING


def test_classify_duplicate_claim():
    r = classify_denial("Claim identified as a duplicate of a previously processed claim.")
    assert r.category == DenialCategory.DUPLICATE_CLAIM


def test_classify_eligibility():
    r = classify_denial("Patient was not eligible for coverage on the date of service.")
    assert r.category == DenialCategory.ELIGIBILITY


def test_classify_coding_error():
    r = classify_denial("Claim denied due to CPT coding mismatch.")
    assert r.category == DenialCategory.CODING_ERROR


def test_classify_missing_documentation():
    r = classify_denial("Medical records were not attached to support the claim.")
    assert r.category == DenialCategory.MISSING_DOCUMENTATION


def test_classify_unknown_falls_back_to_other():
    r = classify_denial("Some entirely unrelated free-text note with no denial keywords.")
    assert r.category == DenialCategory.OTHER


def test_extraction_never_invents_a_claim_number():
    result = extract_denial_fields(denial_text="Denied for lack of medical necessity.", claim_no="", payer="", amount=0)
    assert result.claim_number is None


def test_extraction_preserves_supplied_claim_number():
    result = extract_denial_fields(denial_text="Denied.", claim_no="CLM-9999", payer="Acme", amount=500)
    assert result.claim_number == "CLM-9999"
    assert result.payer == "Acme"
    assert result.denied_amount == 500
