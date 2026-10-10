"""Populate the selected demo database with traceable synthetic filing packages.

Optional explicit command: python -m app.demo_samples
Idempotent stable document/package identifiers; original files stay private.
"""
from datetime import date, timedelta

import fitz

from . import config
from .documents import extract
from .filing import check_package
from .schemas import FilingInput
from .seed import now, seed
from .store import store


def create_samples(db):
    directory = config.DATA / "uploads"
    directory.mkdir(parents=True, exist_ok=True)
    incident = str(date.today() - timedelta(days=20))
    samples = [
        ("sample-statement-valid", "case-001", "statement", f"SYNTHETIC SAMPLE - NOT A COURT FILING\nApplicant: Demo Citizen 1\nRespondent: Demo Supplier\nIncident date: {incident}\nThe applicant alleges a desk arrived damaged. The supplier disputes the date of damage.\nThe buyer asks for review of the delivery record and a fictional invoice. No fact is established."),
        ("sample-invoice", "case-001", "supporting record", f"SYNTHETIC SUPPORTING RECORD\nInvoice: DEMO-42\nApplicant: Demo Citizen 1\nRespondent: Demo Supplier\nDate: {incident}\nItem: demonstration desk\nDocumentary assertion only; authenticity, delivery and payment are unverified."),
        ("sample-statement-defective", "case-002", "statement", "SYNTHETIC DEFECTIVE STATEMENT\nApplicant: Wrong Name\nIncident date: 2026-02-31\nRespondent missing; supporting record missing.\nThis exercise intentionally contains date and identity inconsistencies."),
    ]
    for doc_id, case_id, kind, text in samples:
        if db.get("documents", doc_id):
            continue
        case = db.get("cases", case_id)
        pdf = fitz.open()
        page = pdf.new_page()
        page.insert_text((50, 60), text, fontsize=10)
        raw = pdf.tobytes()
        pdf.close()
        path = directory / f"{doc_id}.pdf"
        path.write_bytes(raw)
        db.put("documents", {"id": doc_id, "case_id": case_id, "owner_id": case["owner_id"], "uploaded_by": "demo-seed",
                             "filename": f"{doc_id}.pdf", "mime_type": "application/pdf", "document_type": kind,
                             "path": str(path), "uploaded_at": now(), **extract(raw, ".pdf")})
        if doc_id not in case["document_ids"]:
            case["document_ids"].append(doc_id)
            db.put("cases", case)
    for case_id, ids in (("case-001", ["sample-statement-valid", "sample-invoice"]), ("case-002", ["sample-statement-defective"])):
        filing_id = f"sample-filing-{case_id}"
        if db.get("filings", filing_id):
            continue
        case = db.get("cases", case_id)
        docs = [db.get("documents", d) for d in ids]
        payload = FilingInput(case_id=case_id, document_ids=ids,
                              document_types={d["id"]: d["document_type"] for d in docs},
                              applicant_name="Demo Citizen 1" if case_id == "case-001" else "Demo Citizen 2",
                              respondent_name="Demo Supplier", incident_date=incident)
        db.put("filings", {**check_package(payload, docs), "id": filing_id, "case_id": case_id,
                           "owner_id": case["owner_id"], "reviewed_metadata": payload.model_dump(mode="json"), "created_at": now()})


if __name__ == "__main__":
    store.connect()
    seed(store)
    create_samples(store)
    print("Created two fictional filing packages with readable PDFs and known checklist findings.")