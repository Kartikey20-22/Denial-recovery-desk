"""Full HTTP-level end-to-end test through FastAPI: register -> seed a
denial directly in the DB -> analyze -> review -> submitted.

Uses FastAPI's TestClient, which runs the app's lifespan (so the real
LangGraph checkpointer + graph get initialized) inside a `with` block.
"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client():
    from app.main import app

    with TestClient(app) as c:
        yield c


def _register_and_login(client):
    email = "e2e-tester@denialdesk.local"
    client.post("/api/auth/register", json={"email": email, "password": "TestPass123", "name": "E2E Tester"})
    resp = client.post("/api/auth/login", json={"email": email, "password": "TestPass123"})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def test_full_denial_lifecycle_via_api(client):
    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    # Seed a denial directly via the upload endpoint (multipart form + a
    # tiny fake PDF so we don't need a real OCR-able document -- denial_text
    # is supplied directly, matching one of intake's three supported input
    # modes).
    files = {"file": ("denial.pdf", b"%PDF-1.4 minimal", "application/pdf")}
    data = {
        "claim_no": "CLM-E2E-1",
        "payer": "Acme Health",
        "amount": "18000",
        "denial_text": "Prior authorization was not found for the billed service.",
    }
    resp = client.post("/api/denials/upload", files=files, data=data, headers=headers)
    assert resp.status_code == 200, resp.text
    denial = resp.json()
    denial_id = denial["id"]
    assert denial["status"] == "HUMAN_REVIEW"
    assert denial["reason"] == "PRIOR_AUTHORIZATION"
    assert denial["appeal"]

    # Pipeline visualization endpoint reflects the paused state.
    wf = client.get(f"/api/denials/{denial_id}/workflow", headers=headers).json()
    assert wf["awaiting_human"] is True
    statuses = {n["node"]: n["status"] for n in wf["nodes"]}
    assert statuses["human_review"] == "WAITING_FOR_HUMAN"
    assert statuses["intake"] == "COMPLETED"

    # Timeline / events endpoint has entries.
    events = client.get(f"/api/denials/{denial_id}/events", headers=headers).json()
    assert len(events) >= 5

    # Approve -> resumes the graph -> simulated submission.
    resp = client.post(f"/api/denials/{denial_id}/approve", headers=headers)
    assert resp.status_code == 200, resp.text
    final = resp.json()
    assert final["status"] == "SUBMITTED"
    assert final["submission_id"]

    # Review queue should no longer list this denial.
    queue = client.get("/api/reviews", headers=headers).json()
    assert all(t["denial_id"] != denial_id for t in queue)


def test_reject_flow_via_api(client):
    token = _register_and_login(client)
    headers = {"Authorization": f"Bearer {token}"}

    files = {"file": ("denial.pdf", b"%PDF-1.4 minimal", "application/pdf")}
    data = {
        "claim_no": "CLM-E2E-2",
        "payer": "NorthCare",
        "amount": "3000",
        "denial_text": "Claim identified as a duplicate of a previously processed claim.",
    }
    resp = client.post("/api/denials/upload", files=files, data=data, headers=headers)
    denial_id = resp.json()["id"]

    resp = client.post(f"/api/denials/{denial_id}/reject", json={"decision": "REJECT", "notes": "Confirmed duplicate."}, headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "REJECTED"
