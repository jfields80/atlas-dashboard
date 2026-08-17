"""Reconcile Grand Rapids–Holland Pass 1 capture evidence without promotion.

The Pass 1 raw files are deliberately retained, but they contain an
operator's selected text rather than durable page bytes or an operator
screenshot of the property page.  This report preserves that distinction and
derives the smallest possible recapture queue.  It does not mutate policy,
routing, exclusions, seeds, or founder decisions.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LP = ROOT / "launch_packages" / "pettripfinder"
CAPTURE = LP / "grand_rapids_holland_capture_pass1_001.json"
REPORT = LP / "grand_rapids_holland_capture_pass1_evidence_grade_reconciliation_001.json"
RECAPTURE = LP / "grand_rapids_holland_capture_pass1_recapture_queue_001.json"


def dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    capture = json.loads(CAPTURE.read_text(encoding="utf-8"))
    rows = capture["terminal_rows"]
    reconciliation = []
    recapture = []
    for row in rows:
        if row["terminal_outcome"] == "POLICY_NOT_FOUND":
            classification = "POLICY_NOT_FOUND"
            reason = ("The attended first-party page exposed only the generic "
                      "'Pet-friendly' amenity; no property-specific policy "
                      "terms were located in Pass 1.")
        else:
            classification = "ARTIFACT_INSUFFICIENT"
            reason = ("The hash binds a selected-text transcription, not "
                      "captured first-party page bytes, a PDF, or an operator "
                      "screenshot. TRANSCRIPTION_ONLY cannot publish under "
                      "the shared evidence contract.")
            recapture.append({
                "queue_position": row["queue_position"],
                "identity_key": row["identity_key"],
                "canonical_name": row["canonical_name"],
                "official_url": row["final_url"],
                "brand": row["brand"],
                "corridor": row["corridor"],
                "prior_capture_outcome": row["terminal_outcome"],
                "prior_artifact_sha256": row["artifact_sha256"],
                "recapture_requirement": (
                    "Capture durable page evidence: full rendered first-party "
                    "page bytes or an operator screenshot that visibly binds "
                    "the property identity and exact policy quote. Record the "
                    "new artifact SHA-256 and contract enum metadata."),
                "review_status": "NOT_STARTED",
            })
        reconciliation.append({
            "queue_position": row["queue_position"],
            "identity_key": row["identity_key"],
            "canonical_name": row["canonical_name"],
            "terminal_outcome": row["terminal_outcome"],
            "evidence_grade_classification": classification,
            "reason": reason,
            "source_url": row["source_url"],
            "final_url": row["final_url"],
            "prior_artifact_sha256": row["artifact_sha256"],
            "prior_artifact_class": row["artifact_class"],
            "prior_source_grade": row["source_grade"],
            "prior_artifact_kind": row["artifact_kind"],
        })

    counts = Counter(item["evidence_grade_classification"] for item in reconciliation)
    report = {
        "schema": "ptf-market-capture-evidence-grade-reconciliation/1.0",
        "work_order": "PTF-GRAND-RAPIDS-HOLLAND-CAPTURE-PASS1-EVIDENCE-GRADE-RECONCILIATION-001",
        "market_id": "grand-rapids-holland-mi",
        "capture_total": len(rows),
        "actionable_candidates": sum(row["terminal_outcome"] != "POLICY_NOT_FOUND" for row in rows),
        "publication_grade_before": 0,
        "publication_grade_after": 0,
        "classification_counts": dict(sorted(counts.items())),
        "root_cause": (
            "All Pass 1 artifacts are selected-text operator transcriptions. "
            "Their hashes prove the transcription bytes, not what a first-party "
            "page said. The capture rows also use non-enum labels "
            "FIRST_PARTY_PROPERTY_PAGE and RENDERED_PAGE; replacing those labels "
            "would not supply a valid rendered_html, operator_screenshot, or PDF "
            "artifact and therefore is not a publication-grade repair."),
        "mechanical_defect_fixed": False,
        "authority_changed": False,
        "rows": reconciliation,
    }
    queue = {
        "schema": "ptf-market-evidence-recapture-queue/1.0",
        "work_order": "PTF-GRAND-RAPIDS-HOLLAND-CAPTURE-PASS1-EVIDENCE-GRADE-RECONCILIATION-001",
        "market_id": "grand-rapids-holland-mi",
        "count": len(recapture),
        "reason": "Only actionable Pass 1 rows lacking a publication-grade page artifact are queued.",
        "items": recapture,
    }
    assert len(reconciliation) == 25
    assert counts == Counter({"ARTIFACT_INSUFFICIENT": 24, "POLICY_NOT_FOUND": 1})
    assert len(recapture) == 24
    dump(REPORT, report)
    dump(RECAPTURE, queue)


if __name__ == "__main__":
    main()
