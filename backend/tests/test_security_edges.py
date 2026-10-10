from datetime import datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app import config, main
from app.store import Store
from app.seed import seed


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "store", Store("sqlite", tmp_path / "security.sqlite3"))
    monkeypatch.setattr(config, "DATA", tmp_path)
    monkeypatch.setattr(config, "DEMO", True)
    main.login_attempts.clear()
    with TestClient(main.app, raise_server_exceptions=False) as client:
        client.headers["X-Nyaya-Request"] = "1"
        yield client


def test_missing_csrf_and_invalid_login(client):
    assert client.post("/api/auth/login", json={"account": "staff-1"}, headers={"X-Nyaya-Request": ""}).status_code == 403
    assert client.post("/api/auth/login", json={"account": "not-a-user"}).status_code == 422


def test_expired_session_and_logout_revocation(client):
    client.post("/api/auth/login", json={"account": "citizen-1"})
    session = main.store.all("sessions")[0]
    session["expires"] = 0
    main.store.put("sessions", session)
    assert client.get("/api/auth/me").status_code == 401
    client.post("/api/auth/login", json={"account": "staff-1"})
    cookie = client.cookies.get("nyaya_session")
    client.post("/api/auth/logout")
    client.cookies.set("nyaya_session", cookie)
    assert client.get("/api/auth/me").status_code == 401


def test_storage_write_error_is_not_success(client):
    client.post("/api/auth/login", json={"account": "staff-1"})
    with patch.object(main.store, "put", side_effect=OSError("private internal storage trace")):
        response = client.post("/api/cases", json={"title": "Fictional storage failure"})
    assert response.status_code == 503
    assert "private internal" not in response.text


def test_seed_calendar_and_ownership(tmp_path):
    db = Store("sqlite", tmp_path / "calendar.sqlite3")
    db.connect()
    seed(db)
    hearings = [datetime.fromisoformat(c["next_hearing"]) for c in db.all("cases") if c["next_hearing"]]
    assert all(h.weekday() < 5 and 10 <= h.hour < 17 for h in hearings)
    assert len(hearings) == len(set(hearings))
    for case in db.all("cases"):
        assert db.get("users", case["owner_id"])["role"] == "citizen"
        assert db.get("users", case["assigned_staff"])["role"] == "staff"
        assert case["filing_date"] <= case["updated_at"]


def test_seeded_document_packages_are_repeatable(client):
    from app.demo_samples import create_samples
    create_samples(main.store)
    create_samples(main.store)
    assert len(main.store.all("documents")) == 3
    assert len(main.store.all("filings")) == 2
    valid = main.store.get("filings", "sample-filing-case-001")
    invalid = main.store.get("filings", "sample-filing-case-002")
    assert valid["summary"]["fail"] == 0
    assert invalid["summary"]["fail"] >= 2
    assert len(main.store.get("cases", "case-001")["document_ids"]) == 2