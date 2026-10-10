import hashlib
import json
import logging
import secrets
import time
import uuid
from collections import Counter, defaultdict, deque
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query as Param, Request, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from starlette.concurrency import run_in_threadpool

from . import analytics, config, decision, documents, filing, research, scheduling
from .schemas import (CaseCreate, CasePatch, DecisionInput, FilingInput, IngestInput, Login,
                      Query, RiskInput, ScheduleApprove, ScheduleInput, SummaryInput, TaskCreate, TaskPatch)
from .seed import now, seed
from .store import StorageUnavailable, store

logger = logging.getLogger("nyayaai")


@asynccontextmanager
async def lifespan(app):
    try:
        store.connect()
        seed(store)
        app.state.storage_error = None
        logger.info("NyayaAI storage mode: %s (demo records)", store.mode)
    except StorageUnavailable as exc:
        app.state.storage_error = str(exc)
        logger.error("%s", exc)
    yield


app = FastAPI(title="NyayaAI — Prototype API", version="0.1.0", lifespan=lifespan,
              description="Synthetic case workflows. Not a court system, legal filing service or automated judge.")
app.add_middleware(CORSMiddleware, allow_origins=[config.ORIGIN], allow_credentials=True,
                   allow_methods=["GET", "POST", "PATCH"], allow_headers=["Content-Type", "X-Nyaya-Request"])


@app.middleware("http")
async def guard(request: Request, call_next):
    if request.url.path.startswith("/api/") and request.url.path != "/api/health" and getattr(app.state, "storage_error", None):
        return JSONResponse({"detail": app.state.storage_error}, status_code=503)
    if request.method in ("POST", "PATCH", "DELETE", "PUT"):
        origin = request.headers.get("origin")
        if request.headers.get("x-nyaya-request") != "1" or (origin and origin != config.ORIGIN):
            return JSONResponse({"detail": "Request origin or CSRF header rejected."}, status_code=403)
        try:
            if int(request.headers.get("content-length", "0")) > 11 * 1024 * 1024:
                return JSONResponse({"detail": "Request exceeds 11 MB."}, status_code=413)
        except ValueError:
            return JSONResponse({"detail": "Invalid Content-Length."}, status_code=400)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Referrer-Policy"] = "same-origin"
    return response


@app.exception_handler(Exception)
async def unexpected_error(request, exc):
    # Do not log request bodies, document text, tokens or exception representations.
    logger.error("Unhandled API error of type %s", type(exc).__name__)
    return JSONResponse({"detail": "Operation failed. Check storage availability and server configuration; no success is implied."}, status_code=503)


def identifier(prefix):
    return f"{prefix}-{uuid.uuid4().hex[:16]}"


def audit(user, action, record_type, record_id):
    store.put("audit", {"id": identifier("audit"), "actor": user["id"], "action": action,
                        "record_type": record_type, "record_id": record_id, "at": now(),
                        "summary": "Demo record operation; document content and secrets omitted."})


def current_user(request: Request):
    token = request.cookies.get("nyaya_session", "")
    session = store.get("sessions", hashlib.sha256(token.encode()).hexdigest()) if token else None
    if not session or session["expires"] < time.time():
        raise HTTPException(401, "Sign in to a demo account.")
    user = store.get("users", session["user_id"])
    if not user or user["status"] != "active":
        raise HTTPException(401, "Account unavailable.")
    return user


def staff(user=Depends(current_user)):
    if user["role"] not in ("staff", "admin"):
        raise HTTPException(403, "Court staff permission required.")
    return user


def allowed(record, user):
    return user["role"] in ("staff", "admin") or record.get("owner_id") == user["id"]


def owned(collection, item_id, user):
    record = store.get(collection, item_id)
    if not record or not allowed(record, user):
        raise HTTPException(404, "Record not found or access not permitted.")
    return record


def visible(collection, user):
    return [r for r in store.all(collection) if allowed(r, user)]


def validate_staff(staff_id):
    member = store.get("users", staff_id)
    if not member or member["role"] not in ("staff", "admin"):
        raise HTTPException(422, "Assigned staff account does not exist.")


def linked_documents(ids, case_id, user):
    if len(ids) != len(set(ids)):
        raise HTTPException(422, "Duplicate document IDs are not permitted.")
    result = [owned("documents", d, user) for d in ids]
    if any(d["case_id"] != case_id for d in result):
        raise HTTPException(422, "All documents must belong to the selected case.")
    return result


def export_json(record, filename):
    return Response(json.dumps(record, indent=2, ensure_ascii=False), media_type="application/json",
                    headers={"Content-Disposition": f'attachment; filename="{filename}.json"'})


@app.get("/api/health", tags=["General"])
def health():
    error = getattr(app.state, "storage_error", None)
    if not error:
        try:
            store.ping()
        except Exception:
            error = "Database unavailable; writes cannot be confirmed. Check database configuration."
    return JSONResponse({"status": "unavailable" if error else "ok", "storage": store.mode,
                         "demo": config.DEMO, "ai": "demo by default; provider configured through environment",
                         "detail": error}, status_code=503 if error else 200)


login_attempts = defaultdict(deque)


@app.post("/api/auth/login", tags=["Authentication"])
def login(payload: Login, request: Request, response: Response):
    if not config.DEMO:
        raise HTTPException(403, "Demo login is disabled. No production identity provider is configured.")
    host = request.client.host if request.client else "local"
    attempts = login_attempts[host]
    while attempts and attempts[0] < time.time() - 60:
        attempts.popleft()
    if len(attempts) >= 30:
        raise HTTPException(429, "Too many sign-in attempts. Wait a minute.")
    attempts.append(time.time())
    user = store.get("users", payload.account)
    if not user or user["status"] != "active":
        raise HTTPException(401, "Demo account unavailable.")
    old = request.cookies.get("nyaya_session")
    if old:
        store.delete("sessions", hashlib.sha256(old.encode()).hexdigest())
    token = secrets.token_urlsafe(32)
    store.put("sessions", {"id": hashlib.sha256(token.encode()).hexdigest(), "user_id": user["id"], "expires": time.time() + 8 * 3600})
    response.set_cookie("nyaya_session", token, httponly=True, secure=config.SECURE, samesite="strict", max_age=8 * 3600, path="/")
    audit(user, "demo login", "users", user["id"])
    return user


@app.post("/api/auth/logout", tags=["Authentication"])
def logout(request: Request, response: Response, user=Depends(current_user)):
    store.delete("sessions", hashlib.sha256(request.cookies["nyaya_session"].encode()).hexdigest())
    response.delete_cookie("nyaya_session", path="/")
    return {"message": "Signed out"}


@app.get("/api/auth/me", tags=["Authentication"])
def me(user=Depends(current_user)):
    return user


@app.get("/api/users/staff", tags=["Cases"])
def staff_list(user=Depends(staff)):
    return [{"id": u["id"], "name": u["name"]} for u in store.all("users") if u["role"] in ("staff", "admin")]


@app.get("/api/cases", tags=["Cases"])
def cases(q: str = Param("", max_length=200), status: str = "", category: str = "", stage: str = "",
          assigned_staff: str = "", filed_after: date | None = None, hearing_before: date | None = None,
          pending_tasks: bool = False, page: int = Param(1, ge=1), page_size: int = Param(12, ge=1, le=100), user=Depends(current_user)):
    records = visible("cases", user)
    task_cases = {t["case_id"] for t in store.all("tasks") if t["status"] == "pending"}
    records = [c for c in records if (not q or q.casefold() in (c["reference"] + " " + c["title"]).casefold())
               and (not status or c["status"] == status) and (not category or c["category"] == category)
               and (not stage or c["stage"] == stage) and (not assigned_staff or c["assigned_staff"] == assigned_staff)
               and (not filed_after or c["filing_date"] >= str(filed_after))
               and (not hearing_before or (c.get("next_hearing") and c["next_hearing"][:10] <= str(hearing_before)))
               and (not pending_tasks or c["id"] in task_cases)]
    records.sort(key=lambda c: c["reference"])
    return {"items": records[(page - 1) * page_size:page * page_size], "total": len(records), "page": page, "page_size": page_size}


@app.post("/api/cases", status_code=201, tags=["Cases"])
def create_case(payload: CaseCreate, user=Depends(staff)):
    owner = store.get("users", payload.owner_id)
    if not owner or owner["role"] != "citizen":
        raise HTTPException(422, "Choose an existing citizen owner.")
    validate_staff(payload.assigned_staff)
    case_id = identifier("case")
    record = {**payload.model_dump(), "id": case_id, "reference": "DEMO/NEW/" + case_id[-8:].upper(),
              "filing_date": str(date.today()), "stage": "Document review", "status": "Pending", "next_hearing": None,
              "adjournments": 0, "missing_documents": 0, "document_ids": [], "events": [], "scenario": {},
              "created_at": now(), "updated_at": now()}
    store.put("cases", record)
    audit(user, "create synthetic case", "cases", case_id)
    return record


@app.get("/api/cases/{case_id}", tags=["Cases"])
def case_detail(case_id: str, user=Depends(current_user)):
    case = owned("cases", case_id, user)
    return {**case, "tasks": [t for t in store.all("tasks") if t["case_id"] == case_id],
            "documents": [{k: v for k, v in d.items() if k not in ("path", "extracted_text", "sections")} for d in visible("documents", user) if d["case_id"] == case_id],
            "reports": [{"id": r["id"], "created_at": r["created_at"], "label": r["label"]} for r in visible("reports", user) if r["case_id"] == case_id] if user["role"] != "citizen" else [],
            "filings": [r for r in visible("filings", user) if r["case_id"] == case_id],
            "risk": analytics.predict(case, store.all("tasks"))}


@app.patch("/api/cases/{case_id}", tags=["Cases"])
def update_case(case_id: str, payload: CasePatch, user=Depends(staff)):
    with store.lock:
        case = owned("cases", case_id, user)
        data = payload.model_dump(exclude_none=True)
        note = data.pop("note", None)
        case.update(data)
        if note:
            case["events"].append({"id": identifier("event"), "at": now(), "type": "Staff note", "note": note})
        case["updated_at"] = now()
        if case["status"] == "Closed":
            case["next_hearing"] = None
        store.put("cases", case)
    audit(user, "update case / simulated event", "cases", case_id)
    return case


@app.get("/api/cases/{case_id}/timeline", tags=["Cases"])
def timeline(case_id: str, user=Depends(current_user)):
    return sorted(owned("cases", case_id, user)["events"], key=lambda e: e["at"])


@app.post("/api/cases/{case_id}/tasks", status_code=201, tags=["Cases"])
def create_task(case_id: str, payload: TaskCreate, user=Depends(staff)):
    case = owned("cases", case_id, user)
    validate_staff(payload.assigned_staff)
    record = {**payload.model_dump(mode="json"), "id": identifier("task"), "case_id": case_id, "owner_id": case["owner_id"], "status": "pending"}
    store.put("tasks", record)
    audit(user, "create task", "tasks", record["id"])
    return record


@app.patch("/api/tasks/{task_id}", tags=["Cases"])
def update_task(task_id: str, payload: TaskPatch, user=Depends(staff)):
    task = owned("tasks", task_id, user)
    if payload.assigned_staff:
        validate_staff(payload.assigned_staff)
    task.update(payload.model_dump(mode="json", exclude_none=True))
    store.put("tasks", task)
    audit(user, "update task", "tasks", task_id)
    return task


@app.post("/api/filing/upload", status_code=201, tags=["Filing"])
async def upload(case_id: str = Form(...), file: UploadFile = File(...), user=Depends(current_user)):
    case = owned("cases", case_id, user)
    extension = Path(file.filename or "").suffix.lower()
    if extension not in documents.TYPES:
        raise HTTPException(415, "Supported formats: PDF, DOCX, PNG, JPG.")
    data = await file.read(documents.MAX_BYTES + 1)
    await file.close()
    if len(data) > documents.MAX_BYTES or not data:
        raise HTTPException(413, "File must be nonempty and at most 10 MB.")
    doc_id = identifier("doc")
    directory = config.DATA / "uploads"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / (doc_id + extension)
    path.write_bytes(data)
    record = {"id": doc_id, "case_id": case_id, "owner_id": case["owner_id"], "uploaded_by": user["id"],
              "filename": (file.filename or "document").replace("\\", "/").split("/")[-1][:180],
              "mime_type": documents.TYPES[extension], "path": str(path), "uploaded_at": now(), "processing_status": "processing"}
    store.put("documents", record)
    try:
        extracted = await run_in_threadpool(documents.extract, data, extension)
        record.update(extracted)
    except documents.ExtractionError as exc:
        record.update(processing_status="failed", warnings=[str(exc)], extracted_text="", sections=[])
    store.put("documents", record)
    with store.lock:
        case = owned("cases", case_id, user)
        case["document_ids"].append(doc_id)
        case["updated_at"] = now()
        store.put("cases", case)
    audit(user, "upload synthetic document", "documents", doc_id)
    return {k: v for k, v in record.items() if k != "path"}


@app.get("/api/documents/{document_id}", tags=["Documents"])
def document(document_id: str, user=Depends(current_user)):
    return {k: v for k, v in owned("documents", document_id, user).items() if k != "path"}


@app.get("/api/documents/{document_id}/download", tags=["Documents"])
def download_document(document_id: str, user=Depends(current_user)):
    record = owned("documents", document_id, user)
    path = Path(record["path"]).resolve()
    if not path.is_relative_to((config.DATA / "uploads").resolve()) or not path.is_file():
        raise HTTPException(404, "Stored file unavailable.")
    return FileResponse(path, media_type=record["mime_type"], filename=record["filename"])


@app.get("/api/demo/sample-document", tags=["Documents"])
def sample_document(kind: str = "valid", user=Depends(current_user)):
    if kind not in ("valid", "invalid"):
        raise HTTPException(422, "Choose valid or invalid.")
    import fitz
    pdf = fitz.open()
    page = pdf.new_page()
    incident = str(date.today() - timedelta(days=20))
    text = f"SYNTHETIC DEMO STATEMENT - NOT A COURT FILING\nApplicant: Demo Citizen 1\nRespondent: Demo Supplier\nIncident date: {incident}\nThe applicant alleges a desk arrived damaged. The supplier disputes when the damage occurred.\nThe applicant requests review of the invoice and delivery photographs. No fact is established here.\nSupporting record: fictional invoice DEMO-42 for a desk."
    if kind == "invalid":
        text = "SYNTHETIC INCOMPLETE STATEMENT\nApplicant: Different Name\nIncident date: 2026-02-31\nMissing respondent and supporting record."
    page.insert_text((50, 60), text, fontsize=10)
    content = pdf.tobytes()
    pdf.close()
    return Response(content, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{kind}-demo-statement.pdf"'})


@app.post("/api/filing/check", status_code=201, tags=["Filing"])
def check_filing(payload: FilingInput, user=Depends(current_user)):
    case = owned("cases", payload.case_id, user)
    docs = linked_documents(payload.document_ids, payload.case_id, user)
    if set(payload.document_types) != set(payload.document_ids):
        raise HTTPException(422, "Classify every selected document, and only selected documents.")
    record = {**filing.check_package(payload, docs), "id": identifier("filing"), "case_id": case["id"],
              "owner_id": case["owner_id"], "reviewed_metadata": payload.model_dump(mode="json"), "created_at": now()}
    store.put("filings", record)
    audit(user, "run demo filing checklist", "filings", record["id"])
    return record


@app.get("/api/filing/{filing_id}", tags=["Filing"])
def get_filing(filing_id: str, user=Depends(current_user)):
    return owned("filings", filing_id, user)


@app.get("/api/filing/{filing_id}/report", tags=["Filing"])
def export_filing(filing_id: str, user=Depends(current_user)):
    return export_json(owned("filings", filing_id, user), "nyayaai-filing-readiness")


@app.post("/api/research/search", tags=["Research"])
def search(payload: Query, user=Depends(current_user)):
    result = research.answer(store, payload)
    store.put("research", {"id": identifier("research"), "owner_id": user["id"], "question": payload.question,
                           "citations": result["citations"], "created_at": now()})
    return result


@app.post("/api/research/summarize", tags=["Research"])
def summarize(payload: SummaryInput, user=Depends(current_user)):
    doc = owned("documents", payload.document_id, user)
    if doc["processing_status"] != "ready":
        raise HTTPException(422, "Document has no readable text.")
    return research.summarize(doc)


@app.post("/api/research/brief", tags=["Research"])
def brief(payload: Query, user=Depends(current_user)):
    return export_json({**research.answer(store, payload), "created_at": now(),
                        "unresolved_questions": ["Which current law and local procedure apply?", "Are further authoritative sources needed?"]}, "nyayaai-research-brief")


@app.get("/api/research/sources/{source_id}", tags=["Research"])
def get_source(source_id: str, user=Depends(current_user)):
    source = store.get("sources", source_id)
    if not source or not source.get("approved"):
        raise HTTPException(404, "Approved source not found.")
    return {**source, "passages": research.passages(source)}


@app.post("/api/research/ingest", status_code=201, tags=["Research"])
def ingest(payload: IngestInput, user=Depends(staff)):
    doc = owned("documents", payload.document_id, user)
    if doc["processing_status"] != "ready":
        raise HTTPException(422, "Only readable documents can be ingested.")
    # Local case material is deliberately NOT published to the shared public research index.
    record = {**payload.model_dump(mode="json"), "id": identifier("source"), "text": doc["extracted_text"],
              "owner_id": doc["owner_id"], "url": None, "approved": False, "ingested_at": now(),
              "ingestion_status": "quarantined", "verification_status": "Locally supplied; provenance unverified. Excluded from shared research to prevent disclosure."}
    store.put("sources", record)
    audit(user, "quarantine local source for provenance review", "sources", record["id"])
    return {"id": record["id"], "status": record["ingestion_status"], "detail": record["verification_status"]}


@app.post("/api/assistant/chat", tags=["Citizen Assistant"])
def chat(payload: Query, user=Depends(current_user)):
    result = research.answer(store, payload)
    store.put("conversations", {"id": identifier("message"), "owner_id": user["id"], "question": payload.question,
                               "answer": result, "created_at": now()})
    return result


@app.get("/api/assistant/history", tags=["Citizen Assistant"])
def history(user=Depends(current_user)):
    return sorted([r for r in store.all("conversations") if r["owner_id"] == user["id"]], key=lambda r: r["created_at"])[-20:]


@app.post("/api/assistant/checklist", tags=["Citizen Assistant"])
def checklist(payload: Query, user=Depends(current_user)):
    return {"question": payload.question, "mode": "general preparation checklist, not a legal filing rule", "items": [
        "Identify the relevant court/forum and current procedural stage.", "Prepare a chronology using anonymized names.",
        "List each document and distinguish allegations from verified information.", "Confirm applicable forms, deadlines and fees with the official registry or qualified legal assistance."],
        "sources": research.search(store, payload.question)}


@app.get("/api/staff/schedule", tags=["Scheduling"])
def schedule(user=Depends(staff)):
    return [{"case_id": c["id"], "reference": c["reference"], "start": c["next_hearing"], "assigned_staff": c["assigned_staff"]}
            for c in store.all("cases") if c.get("next_hearing") and c["status"] != "Closed"]


@app.post("/api/staff/schedule/suggest", tags=["Scheduling"])
def suggest_schedule(payload: ScheduleInput, user=Depends(staff)):
    case = owned("cases", payload.case_id, user)
    if case["status"] == "Closed":
        raise HTTPException(422, "Reopen the sample case before scheduling.")
    if payload.deadline and payload.deadline < payload.start_date:
        raise HTTPException(422, "Deadline cannot precede start date.")
    return scheduling.suggest(store, case, payload)


@app.post("/api/staff/schedule/approve", tags=["Scheduling"])
def approve_schedule(payload: ScheduleApprove, user=Depends(staff)):
    if payload.start.tzinfo is None or not scheduling.valid_slot(payload.start, payload.duration_minutes):
        raise HTTPException(422, "Choose a future weekday slot within 10:00–17:00 IST, on the hour or half-hour, with timezone.")
    with store.lock:
        case = owned("cases", payload.case_id, user)
        if case["status"] == "Closed":
            raise HTTPException(422, "Cannot schedule a closed case.")
        conflicts = scheduling.conflicts(store, case, payload.start, payload.duration_minutes)
        if conflicts:
            raise HTTPException(409, {"message": "Slot conflicts with existing simulated schedule.", "conflicts": conflicts})
        case.update(next_hearing=payload.start.isoformat(), hearing_duration=payload.duration_minutes, updated_at=now())
        case["events"].append({"id": identifier("event"), "at": now(), "type": "Simulated scheduling", "note": f"Human-confirmed demo hearing: {payload.start.isoformat()}. No actual hearing booked."})
        store.put("cases", case)
    audit(user, "approve simulated hearing", "cases", case["id"])
    return {"message": "Simulated schedule updated; no actual hearing booked.", "case": case}


@app.get("/api/staff/alerts", tags=["Scheduling"])
def alerts(user=Depends(staff)):
    tasks = store.all("tasks")
    return [r for c in store.all("cases") if c["status"] == "Pending" and (r := analytics.predict(c, tasks))["reasons"]]


@app.get("/api/analytics/overview", tags=["Analytics"])
def overview(user=Depends(current_user)):
    cases = visible("cases", user)
    tasks = visible("tasks", user)
    predictions = [analytics.predict(c, tasks) for c in cases if c["status"] == "Pending"]
    categories, workload, stages = Counter(c["category"] for c in cases), Counter(c["assigned_staff"] for c in cases if c["status"] == "Pending"), Counter(c["stage"] for c in cases if c["status"] == "Pending")
    recent = sorted([r for r in store.all("research") if r["owner_id"] == user["id"]], key=lambda r: r["created_at"], reverse=True)[:5]
    return {"sample_data": True, "storage": store.mode, "total": len(cases), "pending": sum(c["status"] == "Pending" for c in cases),
            "upcoming": sum(bool(c.get("next_hearing")) and c["next_hearing"][:10] >= str(date.today()) for c in cases),
            "recently_updated": sum(c["updated_at"][:10] >= str(date.today() - timedelta(days=7)) for c in cases),
            "overdue": sum(t["status"] == "pending" and t["deadline"] < str(date.today()) for t in tasks),
            "filings": len(visible("filings", user)), "documents": len(visible("documents", user)),
            "categories": [{"name": k, "count": v} for k, v in categories.items()],
            "workload": [{"name": k, "count": v} for k, v in workload.items()],
            "stages": [{"name": k, "count": v} for k, v in stages.items()],
            "risk_bands": [{"name": b, "count": sum(p["band"] == b for p in predictions)} for b in ("Low", "Moderate", "High")],
            "risks": predictions, "recent_research": recent,
            "filing_trend": [{"name": month, "count": count} for month, count in sorted(Counter(c["filing_date"][:7] for c in cases).items())],
            "projection": {"expected_delayed_milestones": round(sum(p["probability"] for p in predictions), 1), "assumption": "Sum of synthetic probabilities across pending sample cases; assumes synthetic training conditions apply. Not a real forecast."}}


@app.post("/api/analytics/delay-risk", tags=["Analytics"])
def delay_risk(payload: RiskInput, user=Depends(staff)):
    case = owned("cases", payload.case_id, user)
    if case["status"] == "Closed":
        raise HTTPException(422, "Delay analysis applies to pending sample cases.")
    result = {**analytics.predict(case, store.all("tasks")), "id": identifier("prediction"), "owner_id": case["owner_id"], "created_at": now(), "prediction_type": "administrative delay"}
    store.put("predictions", result)
    return result


@app.get("/api/analytics/model-metrics", tags=["Analytics"])
def metrics(user=Depends(staff)):
    return analytics.train()[1]


@app.post("/api/decision-support/analyze", status_code=201, tags=["Decision Support"])
def analyze(payload: DecisionInput, user=Depends(staff)):
    if not payload.reviewed:
        raise HTTPException(422, "Review and confirm input assertions before generating a report.")
    case = owned("cases", payload.case_id, user)
    docs = linked_documents(payload.document_ids, case["id"], user)
    if any(d["processing_status"] != "ready" for d in docs):
        raise HTTPException(422, "Remove unreadable documents before analysis.")
    report = {**decision.analyze(store, payload, docs), "id": identifier("report"), "case_id": case["id"], "owner_id": case["owner_id"], "created_at": now()}
    store.put("reports", report)
    audit(user, "generate non-binding decision support", "reports", report["id"])
    return report


@app.get("/api/decision-support/reports/{report_id}", tags=["Decision Support"])
def get_report(report_id: str, download: bool = False, user=Depends(staff)):
    record = owned("reports", report_id, user)
    return export_json(record, "nyayaai-nonbinding-analysis") if download else record


@app.get("/api/notifications", tags=["General"])
def notifications(user=Depends(current_user)):
    tasks = [t for t in visible("tasks", user) if t["status"] == "pending"]
    return {"tasks": sorted(tasks, key=lambda t: t["deadline"]),
            "audit": sorted([a for a in store.all("audit") if user["role"] in ("staff", "admin") or a["actor"] == user["id"]], key=lambda a: a["at"], reverse=True)[:40]}