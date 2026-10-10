import re

from .research import search

LABEL = "AI-generated, non-binding decision support — human judicial assessment required."


def analyze(db, payload, documents):
    material = []
    for kind, value in (("summary assertion", payload.summary), ("claimant allegation", payload.claimant),
                        ("opposing-party allegation", payload.opponent), ("unverified evidence description", payload.evidence)):
        for index, sentence in enumerate(re.split(r"(?<=[.!?])\s+|\n", value)):
            if sentence.strip():
                material.append({"id": f"input:{kind}:{index + 1}", "classification": kind,
                                 "text": sentence.strip(), "verified_fact": False, "source": "Reviewed user input; not independently verified"})
    for document in documents:
        for index, section in enumerate(document.get("sections", [])[:20]):
            material.append({"id": f"{document['id']}:section-{index + 1}", "classification": "documentary assertion",
                             "text": section["text"][:1500], "verified_fact": False,
                             "source": f"{document['id']} / {section['location']}"})
    sources = search(db, payload.provisions + " " + payload.questions)
    # Guidance pages are not substantive legal-element authorities.
    legal_sources = [p for p in sources if p["source_type"] == "statute"]
    issues = [q.strip() for q in re.split(r"[?\n]", payload.questions) if q.strip()]
    contradictions = []
    for m in material:
        if re.search(r"disput|denies|conflict|not |unsigned|unresolved", m["text"], re.I):
            contradictions.append({"reference": m["id"], "observation": m["text"], "status": "Potential dispute flagged by text pattern; human assessment required, not a credibility finding."})
    missing = ["Authenticity, admissibility and completeness of supplied material have not been established.",
               "No independently verified fact findings or applicable burden/standard-of-proof analysis is available.",
               "Current jurisdiction-specific legal provisions and elements require authoritative verification."]
    return {"label": LABEL, "mode": "experimental deterministic issue organizer; not a verdict model",
            "case_summary": payload.summary, "alleged_provisions": payload.provisions or "None supplied",
            "facts": material, "issues": issues, "legal_sources": sources,
            "legal_elements": [{"requirement": "Unable to verify applicable legal elements from the approved corpus.",
                                "verified_legal_source": None, "supporting_evidence": [], "contrary_evidence": [],
                                "unresolved": "Obtain current authoritative statutory text and verify applicability; supplied section labels are allegations, not verified law."}] if not legal_sources else
                               [{"requirement": "Retrieved statutory passage requires human element mapping; no automatic legal test inferred.", "verified_legal_source": p["passage_id"], "supporting_evidence": [], "contrary_evidence": [], "unresolved": "Verify jurisdiction, temporal applicability and legal interpretation."} for p in legal_sources],
            "both_sides": [{"issue": issue, "claimant_argument": payload.claimant, "opposing_argument": payload.opponent,
                            "evidence_references": [m["id"] for m in material if m["classification"] in ("documentary assertion", "unverified evidence description")],
                            "legal_reference": None, "uncertainty": "Party assertions may conflict. No automatic inference of credibility, guilt or evidential weight.",
                            "human_examination": "Identify which material actually bears on this issue and test alternative explanations."} for issue in issues],
            "potential_contradictions": contradictions, "unresolved_disputes": [m["id"] for m in material if "allegation" in m["classification"]],
            "missing_information": missing, "uncertainties": missing,
            "scenarios": [{"outcome": "A responsible outcome assessment cannot be formed from the available materials.",
                           "assumptions": "Applicable legal elements and evidence status remain unresolved.",
                           "reasoning": "This organizer cannot establish legal sufficiency, evidential reliability, burden or standard of proof. It therefore abstains instead of guessing a verdict.",
                           "source_support": [], "experimental": True}],
            "human_questions": issues + ["Which assertions are admitted, disputed or independently corroborated?", "What contrary or potentially exculpatory material is missing?", "Which current provisions, burden and standard of proof govern this matter?"],
            "input_document_ids": payload.document_ids, "model_version": "issue-organizer-v1", "provider": "local deterministic demo",
            "human_review_status": "pending", "limitations": "Not validated for judicial use. No verdict, judicial order, confidence percentage, authenticity assessment or legal advice. Allegations remain allegations."}