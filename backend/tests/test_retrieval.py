"""RAG retrieval tests -- dependency-free local embeddings, real synthetic
documents on disk under backend/data/{policies,evidence}."""
from app.ai.retrieval.policy_retriever import retrieve_policy
from app.ai.retrieval.evidence_retriever import retrieve_evidence


def test_policy_retrieval_returns_citations_with_source():
    hits = retrieve_policy("prior authorization retroactive")
    assert hits, "expected at least one policy hit"
    for h in hits:
        assert "source" in h and h["source"].endswith(".txt")
        assert "relevance_score" in h
        assert "content" in h


def test_policy_retrieval_never_invents_a_source():
    hits = retrieve_policy("prior authorization")
    sources = {h["source"] for h in hits}
    assert sources <= {
        "prior_authorization.txt", "medical_necessity.txt", "coding.txt",
        "timely_filing.txt", "eligibility.txt", "duplicate_claim.txt", "missing_documentation.txt",
    }


def test_evidence_retrieval_boosts_matching_claim():
    hits = retrieve_evidence("prior authorization request log", claim_no="CLM-1001")
    assert hits
    assert any(h["source"].startswith("CLM-1001_") for h in hits)
