import json
import re
from datetime import date
from pathlib import Path

RULES = json.loads(Path(__file__).with_name("filing_rules.json").read_text(encoding="utf-8"))


def check_package(payload, documents):
    findings = []

    def add(identifier, requirement, status, explanation, correction, doc=None, location=None):
        findings.append({"check_id": identifier, "requirement": requirement, "status": status,
                         "explanation": explanation, "correction": correction, "document_id": doc,
                         "evidence_location": location, "source_reference": RULES["source_reference"],
                         "uncertainty": "Configured demo check; not an official acceptance decision."})

    for kind in RULES["required_document_types"]:
        matching = [d for d in documents if payload.document_types.get(d["id"]) == kind]
        add(f"type-{kind}", f"Include a {kind}", "pass" if matching else "fail",
            f"{len(matching)} document(s) classified by the user as {kind}.", f"Upload and classify a {kind}." if not matching else "No correction suggested.")
    for d in documents:
        readable = d["processing_status"] == "ready" and bool(d.get("extracted_text", "").strip())
        add(f"read-{d['id']}", "Readable document", "pass" if readable else "fail",
            "Text extracted." if readable else "Document is not processed; it was not analyzed.", "Review extracted text." if readable else "Replace with readable PDF/DOCX or configure OCR.", d["id"])
        if not readable:
            continue
        text = d["extracted_text"]
        if payload.document_types.get(d["id"]) == "statement":
            for key in RULES["required_fields"]:
                value = str(getattr(payload, key))
                section = next((s for s in d.get("sections", []) if value.casefold() in s["text"].casefold()), None)
                add(f"{key}-{d['id']}", f"Reviewed {key.replace('_', ' ')} appears in statement", "pass" if section else "warning",
                    f"Found reviewed value: {value}." if section else f"Exact reviewed value '{value}' not found; this may be a formatting or extraction difference.",
                    "Confirm this text is correct." if section else "Compare the statement with reviewed metadata and correct mismatches.", d["id"], section["location"] if section else None)
            adequate = len(text.strip()) >= RULES["minimum_statement_characters"]
            add(f"length-{d['id']}", "Statement contains sufficient text for this demo checklist", "pass" if adequate else "warning", f"{len(text.strip())} extracted characters.", "Provide a clear chronology and requested remedy.", d["id"])
        dates = re.findall(r"\b\d{4}-\d{2}-\d{2}\b", text)
        invalid = []
        for value in dates:
            try:
                date.fromisoformat(value)
            except ValueError:
                invalid.append(value)
        if invalid:
            add(f"invalid-date-{d['id']}", "Calendar dates are valid", "fail", f"Invalid ISO dates: {', '.join(invalid)}", "Correct the calendar dates.", d["id"])
    future = payload.incident_date > date.today()
    add("incident-date", "Past incident chronology", "warning" if future else "pass", "Incident date is in the future." if future else "Incident date is not in the future.", "Confirm the date; future events may need a different intake description.")
    add("official-review", "Applicable official filing rules", "unable to verify", RULES["official_requirements"], "Verify the applicable forum's current official checklist with the registry or qualified counsel.")
    return {"rules": RULES, "checks": findings, "summary": {s: sum(f["status"] == s for f in findings) for s in ("pass", "warning", "fail", "unable to verify")},
            "limitations": "Readiness exercise only. No actual court filing, acceptance, rejection, legal deadline determination or authenticity check."}