import io
from datetime import date, timedelta
from unittest.mock import patch

import fitz
import pytest
from docx import Document
from fastapi.testclient import TestClient

from app import config, main, research
from app.documents import ExtractionError, extract
from app.seed import seed
from app.store import Store, StorageUnavailable

HEADERS = {"X-Nyaya-Request": "1", "Origin": "http://localhost:3000"}


@pytest.fixture
def client(tmp_path, monkeypatch):
    db = Store("sqlite", tmp_path / "test.sqlite3")
    monkeypatch.setattr(main, "store", db)
    monkeypatch.setattr(config, "DATA", tmp_path)
    monkeypatch.setattr(config, "DEMO", True)
    monkeypatch.setenv("LLM_PROVIDER", "demo")
    main.login_attempts.clear()
    with TestClient(main.app) as c:
        c.headers.update(HEADERS)
        yield c


def login(client, account="citizen-1"):
    response = client.post("/api/auth/login", json={"account": account})
    assert response.status_code == 200, response.text
    return response


def pdf_bytes(text):
    pdf = fitz.open()
    page = pdf.new_page()
    page.insert_text((50, 60), text, fontsize=10)
    data = pdf.tobytes()
    pdf.close()
    return data


def upload(client, text, filename="statement.pdf", case="case-001"):
    return client.post("/api/filing/upload", data={"case_id": case}, files={"file": (filename, pdf_bytes(text), "application/pdf")})


def test_health_auth_and_csrf(client):
    assert client.get("/api/health").json()["storage"] == "sqlite"
    assert client.get("/api/cases").status_code == 401
    response = login(client)
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "SameSite=strict" in response.headers["set-cookie"]
    assert client.get("/api/auth/me").json()["id"] == "citizen-1"
    assert client.post("/api/auth/logout", headers={"Origin": "https://evil.invalid"}).status_code == 403
    assert client.post("/api/auth/logout").status_code == 200
    assert client.get("/api/auth/me").status_code == 401


def test_permissions_and_filtering(client):
    login(client)
    records = client.get("/api/cases?page_size=100").json()
    assert records["total"] == 12
    assert all(c["owner_id"] == "citizen-1" for c in records["items"])
    assert client.get("/api/cases/case-002").status_code == 404
    assert client.post("/api/cases", json={"title": "Unauthorized sample case"}).status_code == 403
    assert client.get("/api/analytics/model-metrics").status_code == 403
    assert client.get("/api/staff/alerts").status_code == 403
    assert client.get("/api/cases?q=nonexistentword").json()["items"] == []
    assert client.get("/api/cases?page=0").status_code == 422


def test_case_tasks_and_timeline(client):
    login(client, "staff-1")
    created = client.post("/api/cases", json={"title": "Fictional test dispute", "category": "Civil"})
    assert created.status_code == 201
    case_id = created.json()["id"]
    updated = client.patch(f"/api/cases/{case_id}", json={"stage": "Evidence", "note": "Synthetic review completed."})
    assert updated.json()["stage"] == "Evidence"
    assert len(client.get(f"/api/cases/{case_id}/timeline").json()) == 1
    task = client.post(f"/api/cases/{case_id}/tasks", json={"title": "Review fictional invoice", "deadline": str(date.today()), "assigned_staff": "staff-2"})
    assert task.status_code == 201
    assert client.patch(f"/api/tasks/{task.json()['id']}", json={"status": "complete"}).json()["status"] == "complete"
    assert client.post(f"/api/cases/{case_id}/tasks", json={"title": "Bad assignee", "deadline": str(date.today()), "assigned_staff": "citizen-1"}).status_code == 422
    assert client.patch(f"/api/cases/{case_id}", json={"owner_id": "citizen-3"}).status_code == 422


def test_upload_and_filing_traceability(client):
    login(client)
    incident = str(date.today() - timedelta(days=20))
    text = f"Applicant: Demo Citizen 1\nRespondent: Demo Supplier\nIncident date: {incident}\nThe buyer alleges damage to a desk; the seller disputes the date.\nThe invoice and delivery photograph need verification."
    doc = upload(client, text).json()
    support = upload(client, "Fictional invoice DEMO-42. A desk was described; payment is disputed.", "invoice.pdf").json()
    assert doc["processing_status"] == "ready"
    assert doc["sections"][0]["location"] == "page 1"
    assert "path" not in doc
    payload = {"case_id": "case-001", "document_ids": [doc["id"], support["id"]], "document_types": {doc["id"]: "statement", support["id"]: "supporting record"}, "applicant_name": "Demo Citizen 1", "respondent_name": "Demo Supplier", "incident_date": incident}
    result = client.post("/api/filing/check", json=payload)
    assert result.status_code == 201, result.text
    report = result.json()
    assert report["summary"]["fail"] == 0
    assert report["summary"]["unable to verify"] == 1
    assert any(c["evidence_location"] == "page 1" for c in report["checks"])
    assert client.get(f"/api/filing/{report['id']}/report").status_code == 200
    assert client.post("/api/research/summarize", json={"document_id": doc["id"]}).status_code == 200
    login(client, "citizen-2")
    assert client.get(f"/api/documents/{doc['id']}").status_code == 404
    assert client.get(f"/api/documents/{doc['id']}/download").status_code == 404
    assert client.get(f"/api/filing/{report['id']}").status_code == 404


def test_invalid_documents_and_package(client):
    login(client)
    assert client.post("/api/filing/upload", data={"case_id": "case-001"}, files={"file": ("bad.exe", b"unsafe", "application/octet-stream")}).status_code == 415
    response = client.post("/api/filing/upload", data={"case_id": "case-001"}, files={"file": ("../../bad.pdf", b"not a PDF", "application/pdf")})
    assert response.status_code == 201
    assert response.json()["processing_status"] == "failed"
    assert response.json()["filename"] == "bad.pdf"
    assert upload(client, "A fictional statement", case="case-002").status_code == 404
    doc = upload(client, "Applicant: Wrong Name\nIncident date: 2026-02-31\nA fictional short claim.").json()
    result = client.post("/api/filing/check", json={"case_id": "case-001", "document_ids": [doc["id"]], "document_types": {doc["id"]: "statement"}, "applicant_name": "Demo Citizen 1", "respondent_name": "Demo Supplier", "incident_date": "2026-01-01"})
    assert result.json()["summary"]["fail"] >= 2
    assert result.json()["summary"]["warning"] >= 1


def test_docx_and_ocr_errors():
    doc = Document()
    doc.add_paragraph("Synthetic claimant alleges a damaged desk; authenticity is unresolved.")
    stream = io.BytesIO()
    doc.save(stream)
    assert "Synthetic claimant" in extract(stream.getvalue(), ".docx")["extracted_text"]
    with pytest.raises(ExtractionError):
        extract(b"not a docx", ".docx")
    from PIL import Image
    image = io.BytesIO()
    Image.new("RGB", (20, 20), "white").save(image, format="PNG")
    with patch("app.documents.ocr", side_effect=ExtractionError("OCR unavailable. Install Tesseract.")):
        with pytest.raises(ExtractionError, match="Tesseract"):
            extract(image.getvalue(), ".png")


def test_research_assistant_and_citations(client):
    login(client)
    result = client.post("/api/research/search", json={"question": "How do I find case status without CNR?"}).json()
    assert result["passages"]
    assert set(result["citations"]) <= {p["passage_id"] for p in result["passages"]}
    for passage in result["passages"]:
        source = client.get(f"/api/research/sources/{passage['source_id']}").json()
        assert passage["passage_id"] in [p["passage_id"] for p in source["passages"]]
    assert client.post("/api/research/search", json={"question": "quantum pineapple zeppelin"}).json()["passages"] == []
    assert client.post("/api/research/search", json={"question": "legal aid", "source_type": "judgment"}).json()["passages"] == []
    assert client.post("/api/assistant/chat", json={"question": "Where can I find legal aid?"}).json()["citations"]
    assert len(client.get("/api/assistant/history").json()) == 1
    assert client.post("/api/assistant/checklist", json={"question": "Prepare legal aid documents"}).json()["items"]
    assert client.post("/api/research/brief", json={"question": "legal aid"}).headers["content-disposition"]


def test_provider_citation_rejection(client, monkeypatch):
    login(client)
    monkeypatch.setenv("LLM_PROVIDER", "openai-compatible")
    monkeypatch.setenv("LLM_API_KEY", "synthetic-test-key")
    class FakeResponse:
        def raise_for_status(self):
            pass
        def json(self):
            return {"choices": [{"message": {"content": '{"answer":"Unsupported statement", "citations":["invented:p99"]}'}}]}
    monkeypatch.setattr(research.httpx, "post", lambda *args, **kwargs: FakeResponse())
    result = client.post("/api/research/search", json={"question": "legal aid"}).json()
    assert "fallback" in result["mode"]
    assert "invented:p99" not in result["citations"]


def test_scheduling_conflict_detection(client):
    login(client, "staff-1")
    start = str(date.today() + timedelta(days=10))
    suggestion = client.post("/api/staff/schedule/suggest", json={"case_id": "case-001", "start_date": start}).json()
    assert suggestion["options"]
    option = suggestion["options"][0]
    slot = {"case_id": "case-001", "start": option["start"], "duration_minutes": option["duration_minutes"]}
    assert client.post("/api/staff/schedule/approve", json=slot).status_code == 200
    slot["case_id"] = "case-002"
    assert client.post("/api/staff/schedule/approve", json=slot).status_code == 409
    slot["start"] = "2020-01-01T10:00:00+05:30"
    assert client.post("/api/staff/schedule/approve", json=slot).status_code == 422


def test_predictions_and_dashboard_agree(client):
    login(client, "staff-1")
    overview = client.get("/api/analytics/overview").json()
    assert overview["total"] == 36
    assert sum(c["count"] for c in overview["categories"]) == 36
    assert sum(r["count"] for r in overview["risk_bands"]) == overview["pending"]
    prediction = client.post("/api/analytics/delay-risk", json={"case_id": "case-001"}).json()
    assert 0 <= prediction["probability"] <= 1
    assert prediction["model_version"]
    metrics = client.get("/api/analytics/model-metrics").json()
    assert "baseline_prior" in metrics["metrics"]
    assert metrics["metrics"]["logistic_regression"]["brier_score"] < metrics["metrics"]["baseline_prior"]["brier_score"]
    assert client.post("/api/analytics/delay-risk", json={"case_id": "case-009"}).status_code == 422
    assert client.post("/api/analytics/delay-risk", json={"case_id": "missing"}).status_code == 404


def test_decision_structure_and_abstention(client):
    login(client, "staff-1")
    scenario = client.get("/api/cases/case-001").json()["scenario"]
    payload = {"case_id": "case-001", **scenario, "reviewed": False}
    assert client.post("/api/decision-support/analyze", json=payload).status_code == 422
    payload["reviewed"] = True
    response = client.post("/api/decision-support/analyze", json=payload)
    assert response.status_code == 201, response.text
    report = response.json()
    assert "non-binding" in report["label"]
    assert report["both_sides"] and report["legal_elements"] and report["missing_information"]
    assert all(f["verified_fact"] is False for f in report["facts"])
    assert "cannot be formed" in report["scenarios"][0]["outcome"]
    assert client.get(f"/api/decision-support/reports/{report['id']}").status_code == 200
    login(client)
    assert client.get(f"/api/decision-support/reports/{report['id']}").status_code == 403


def test_storage_failure_and_reset(client, tmp_path):
    main.app.state.storage_error = "MongoDB unavailable. Start MongoDB or explicitly select sqlite."
    assert client.get("/api/health").status_code == 503
    assert client.get("/api/cases").status_code == 503
    main.app.state.storage_error = None
    db = Store("sqlite", tmp_path / "persist.sqlite3")
    db.connect()
    seed(db)
    db.put("cases", {"id": "extra"})
    seed(db, reset=True)
    assert len(db.all("cases")) == 36
    another = Store("sqlite", tmp_path / "persist.sqlite3")
    another.connect()
    assert another.get("cases", "case-001")["reference"] == "DEMO/2026/0001"
    with patch("pymongo.MongoClient", side_effect=ConnectionError("offline")):
        with pytest.raises(StorageUnavailable, match="MongoDB unavailable"):
            Store("mongodb").connect()


def test_local_ingestion_is_not_published(client):
    login(client, "staff-1")
    doc = upload(client, "Confidential fictional zebra record. Not official legal guidance.").json()
    response = client.post("/api/research/ingest", json={"document_id": doc["id"], "title": "Fictional local source"})
    assert response.status_code == 201
    assert response.json()["status"] == "quarantined"
    login(client, "citizen-2")
    assert client.get(f"/api/research/sources/{response.json()['id']}").status_code == 404
    assert client.post("/api/research/search", json={"question": "confidential zebra"}).json()["passages"] == []