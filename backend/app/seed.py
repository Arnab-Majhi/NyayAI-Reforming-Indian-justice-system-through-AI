"""Repeatable synthetic records. No real litigants or case references."""
from datetime import date, datetime, timedelta, timezone


def now():
    return datetime.now(timezone.utc).isoformat()


SOURCES = [
    {
        "id": "nalsa-services", "title": "NALSA — legal aid and dispute-resolution services",
        "url": "https://nalsa.gov.in/", "source_type": "official guidance", "jurisdiction": "India",
        "text": "The National Legal Services Authority (NALSA) has been constituted under the Legal Services Authorities Act, 1987 to provide free Legal Services to the weaker sections of the society and to organize Lok Adalats for amicable settlement of disputes. In every State, State Legal Services Authority has been constituted to give effect to the policies and directions of the NALSA and to give free legal services to the people and conduct Lok Adalats in the State.",
        "publication_date": None, "effective_date": None, "verified_on": "2026-10-10",
        "verification_status": "Official homepage retrieved; excerpt. Eligibility and current local procedure need verification.",
    },
    {
        "id": "ecourts-status", "title": "eCourts Services — finding case status",
        "url": "https://services.ecourts.gov.in/ecourtindia_v6/", "source_type": "official guidance", "jurisdiction": "India",
        "text": "Enter the 16 digit alphanumeric CNR Number without any hyphen or space. Click Search button to view current status and history of the case. If you don't know the CNR number of the case, click on the Case Status icon on the left menu to search the case with other options like case registration number, party name, advocate name etc.",
        "publication_date": None, "effective_date": None, "verified_on": "2026-10-10",
        "verification_status": "Official portal instructions retrieved. NyayaAI does not query this portal or book hearings.",
    },
]

SCENARIOS = [
    {"summary": "Fictional defective desk delivery dispute", "claimant": "The buyer alleges the delivered desk was damaged. A dated delivery photograph is described but authenticity is not established.", "opponent": "The seller alleges the damage occurred after delivery and disputes the photograph date.", "evidence": "Documentary assertion: invoice for a desk. Witness statement: courier says packaging appeared intact. Unresolved claim: date of damage.", "questions": "What additional material is needed to resolve the delivery-date dispute?"},
    {"summary": "Fictional rental deposit disagreement", "claimant": "The tenant alleges the deposit was not returned after handover.", "opponent": "The landlord alleges repairs were needed and says deductions were communicated.", "evidence": "Documentary assertion: unsigned handover inventory. Documentary assertion: repair estimate, not proof of payment. Unresolved claim: prior condition.", "questions": "Which deductions and records need human examination?"},
    {"summary": "Fictional disputed service invoice", "claimant": "The supplier alleges agreed services were completed and payment remains due.", "opponent": "The customer alleges only part of the agreed work was delivered.", "evidence": "Documentary assertion: email listing requested work. Witness statement: project assistant recalls a demonstration. Unresolved claim: acceptance of deliverables.", "questions": "What records would clarify scope and acceptance?"},
]


def seed(db, reset=False):
    if reset:
        db.clear()
    if db.get("users", "citizen-1"):
        return
    for i in range(1, 4):
        db.put("users", {"id": f"citizen-{i}", "name": f"Demo Citizen {i}", "role": "citizen", "status": "active", "created_at": now()})
    for i in range(1, 5):
        db.put("users", {"id": f"staff-{i}", "name": f"Registry Officer {i} (fictional)", "role": "staff", "status": "active", "created_at": now()})
    db.put("users", {"id": "admin-1", "name": "Demo Administrator", "role": "admin", "status": "active", "created_at": now()})
    for source in SOURCES:
        db.put("sources", {**source, "ingested_at": now(), "ingestion_status": "indexed", "approved": True})
    today = date.today()
    for i in range(1, 37):
        identifier = f"case-{i:03}"
        filing = today - timedelta(days=30 + i * 7)
        updated = today - timedelta(days=i * 2)
        owner = f"citizen-{(i - 1) % 3 + 1}"
        scenario = SCENARIOS[(i - 1) % 3]
        record = {
            "id": identifier, "reference": f"DEMO/2026/{i:04}", "title": f"{scenario['summary']} · {i:02}",
            "owner_id": owner, "category": ["Consumer", "Civil", "Commercial"][(i - 1) % 3],
            "court": "Nyaya Demo District Forum", "filing_date": str(filing),
            "stage": ["Document review", "Notice", "Evidence", "Arguments"][i % 4],
            "status": "Closed" if i % 9 == 0 else "Pending",
            "assigned_staff": f"staff-{(i - 1) % 4 + 1}", "next_hearing": None,
            "adjournments": i % 4, "missing_documents": i % 3, "document_ids": [],
            "created_at": filing.isoformat(), "updated_at": updated.isoformat(), "scenario": scenario,
            "events": [{"id": f"event-{i}-1", "at": str(filing), "type": "Filing", "note": "Synthetic case created; no actual filing."}, {"id": f"event-{i}-2", "at": str(updated), "type": "Review", "note": "Simulated registry review recorded."}],
        }
        if record["status"] != "Closed":
            day = today + timedelta(days=1 + i // 6)
            while day.weekday() >= 5:
                day += timedelta(days=1)
            # Find a unique weekday slot rather than rolling a weekend batch
            # onto occupied Monday times.
            hour = 10 + i % 6
            occupied = {c.get("next_hearing") for c in db.all("cases")}
            while f"{day}T{hour:02}:00:00+05:30" in occupied:
                hour += 1
                if hour >= 17:
                    hour = 10
                    day += timedelta(days=1)
                    while day.weekday() >= 5:
                        day += timedelta(days=1)
            record["next_hearing"] = f"{day}T{hour:02}:00:00+05:30"
        db.put("cases", record)
        db.put("tasks", {"id": f"task-{i:03}", "case_id": identifier, "owner_id": owner, "title": "Review supporting document inventory", "assigned_staff": record["assigned_staff"], "deadline": str(today + timedelta(days=i % 10 - 4)), "status": "complete" if i % 5 == 0 else "pending"})


if __name__ == "__main__":
    import argparse
    from .store import store
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Delete demo records including sessions, then reseed")
    args = parser.parse_args()
    store.connect()
    seed(store, args.reset)
    print(f"Seeded {len(store.all('cases'))} fictional cases using {store.mode} storage.")