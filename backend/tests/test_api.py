import io

import pytest
from fastapi.testclient import TestClient

from app import create_app

from .conftest import make_pdf

ADMIN = {"Authorization": "Bearer test-admin-token"}


@pytest.fixture
def client(settings, pipeline):
    with TestClient(create_app(settings, pipeline)) as c:
        yield c


def _pdf_file(data: bytes, name="policy.pdf", ctype="application/pdf"):
    return {"file": (name, io.BytesIO(data), ctype)}


# ------------------------------------------------------------------- health
def test_health_exposes_no_secrets(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["components"]["admin_configured"] is True
    assert "test-admin-token" not in client.get("/health").text


def test_health_degraded_when_llm_down(client, llm):
    llm.available = False
    assert client.get("/health").json()["status"] == "degraded"


# ---------------------------------------------------------------------- auth
def test_upload_requires_admin_token(client, policy_pdf):
    assert client.post("/documents/upload", files=_pdf_file(policy_pdf)).status_code == 401
    bad = {"Authorization": "Bearer wrong"}
    assert client.post("/documents/upload", files=_pdf_file(policy_pdf), headers=bad).status_code == 401
    assert client.get("/documents").json()["documents"] == []  # nothing was indexed


def test_delete_requires_admin_token(client, policy_pdf):
    client.post("/documents/upload", files=_pdf_file(policy_pdf), headers=ADMIN)
    assert client.delete("/documents/policy?confirm=policy").status_code == 401
    assert client.get("/documents").json()["indexed_documents"] == 1


def test_admin_disabled_when_token_not_configured(settings, pipeline, policy_pdf):
    from dataclasses import replace

    with TestClient(create_app(replace(settings, admin_token=""), pipeline)) as c:
        r = c.post("/documents/upload", files=_pdf_file(policy_pdf), headers=ADMIN)
        assert r.status_code == 503


# ------------------------------------------------------------ upload / delete
def test_upload_success_and_duplicate(client, policy_pdf):
    r = client.post("/documents/upload", files=_pdf_file(policy_pdf), headers=ADMIN)
    assert r.status_code == 200
    body = r.json()
    assert body["outcome"] == "indexed" and body["document"]["status"] == "ready"
    assert body["document"]["page_count"] == 3

    again = client.post("/documents/upload", files=_pdf_file(policy_pdf, "other.pdf"), headers=ADMIN)
    assert again.status_code == 200 and again.json()["outcome"] == "duplicate"


def test_upload_new_version_reports_replacement(client, policy_pdf):
    client.post("/documents/upload", files=_pdf_file(policy_pdf), headers=ADMIN)
    r = client.post("/documents/upload", files=_pdf_file(make_pdf(["Revised CGPA text 8.0."])), headers=ADMIN)
    assert r.json()["replaced_version"] == 1 and r.json()["document"]["version"] == 2


@pytest.mark.parametrize(
    "name, data, status",
    [
        ("notes.txt", b"hello", 400),
        ("fake.pdf", b"this is not a pdf", 422),
        ("empty.pdf", b"", 422),
        ("broken.pdf", b"%PDF-1.4 garbage", 422),
    ],
)
def test_upload_validation(client, name, data, status):
    r = client.post("/documents/upload", files=_pdf_file(data, name), headers=ADMIN)
    assert r.status_code == status


def test_upload_size_limit(client):
    big = b"%PDF-1.4\n" + b"0" * (1024 * 1024 + 10)
    r = client.post("/documents/upload", files=_pdf_file(big), headers=ADMIN)
    assert r.status_code == 413


def test_delete_needs_confirmation_and_works(client, policy_pdf):
    client.post("/documents/upload", files=_pdf_file(policy_pdf), headers=ADMIN)
    assert client.delete("/documents/policy", headers=ADMIN).status_code == 400
    assert client.delete("/documents/policy?confirm=nope", headers=ADMIN).status_code == 400
    assert client.delete("/documents/policy?confirm=policy", headers=ADMIN).status_code == 200
    assert client.delete("/documents/policy?confirm=policy", headers=ADMIN).status_code == 404


def test_documents_list_hides_internals_from_students(client, policy_pdf):
    client.post("/documents/upload", files=_pdf_file(policy_pdf), headers=ADMIN)
    public = client.get("/documents").json()
    assert public["detailed"] is False and public["indexed_documents"] == 1
    assert "content_hash" not in public["documents"][0]
    admin = client.get("/documents", headers=ADMIN).json()
    assert admin["detailed"] is True and "content_hash" in admin["documents"][0]


# ---------------------------------------------------------------------- chat
@pytest.mark.parametrize("payload", [{}, {"question": ""}, {"question": "   "}, {"question": "x" * 1001}])
def test_chat_validation(client, payload):
    assert client.post("/chat", json=payload).status_code == 422


def test_chat_response_contract_matches_frontend_types(client, policy_pdf):
    """Keys here mirror frontend/src/types/index.ts (ChatResponse / Citation)."""
    client.post("/documents/upload", files=_pdf_file(policy_pdf), headers=ADMIN)
    body = client.post("/chat", json={"question": "What minimum CGPA is required for eligibility?"}).json()
    assert set(body) == {"answer", "citations", "conversation_id", "grounded", "retrieval"}
    assert set(body["citations"][0]) == {
        "document_id", "filename", "document_version", "page_number", "chunk_id", "excerpt", "distance",
    }
    assert body["citations"][0]["page_number"] == 1


def test_chat_llm_outage_returns_503(client, policy_pdf, llm):
    from src.llm import LLMError

    client.post("/documents/upload", files=_pdf_file(policy_pdf), headers=ADMIN)

    def boom(system, prompt):
        raise LLMError("down")

    llm.generate = boom
    r = client.post("/chat", json={"question": "What minimum CGPA is required for eligibility?"})
    assert r.status_code == 503 and "down" not in r.text


# ---------------------------------------------------------------------- CORS
def test_cors_allows_only_configured_origin(client):
    ok = client.options(
        "/chat",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "POST"},
    )
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:3000"
    bad = client.options(
        "/chat",
        headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "POST"},
    )
    assert "access-control-allow-origin" not in bad.headers
