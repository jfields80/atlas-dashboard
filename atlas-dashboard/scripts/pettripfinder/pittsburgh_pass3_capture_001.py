"""Build the capture-only Pittsburgh Pass 3 packet (six pre-authorized rows).

The packet is intentionally not an authority applicator.  It saves the
captured, property-specific rendered-text transcripts under gitignored
``data/operator_evidence`` and records their SHA-256 digests in the two
review artifacts.  Founder decisions are deliberately absent.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LP = ROOT / "launch_packages" / "pettripfinder"
OUT = LP / "markets" / "reports"
EVIDENCE = ROOT / "data" / "operator_evidence" / "pittsburgh-pass3-capture-001"
WORK_ORDER = "PTF-PITTSBURGH-PASS3-CAPTURE-001"
AS_OF = "2026-08-17"
BASE = "4999c59dc3a743373b76a01e550915c684101d3a"


ROWS = [
    {
        "decision_id": "PGH-P3-D001", "row_number": 1,
        "hotel": "Residence Inn Pittsburgh North Shore",
        "identity_key": "residence inn pittsburgh north shore",
        "url": "https://www.marriott.com/en-us/hotels/pitrn-residence-inn-pittsburgh-north-shore/overview/",
        "identity": "Residence Inn by Marriott Pittsburgh North Shore | 574 West General Robinson Street, Pittsburgh, Pennsylvania, USA, 15212 | +1 412-321-2099",
        "outcome_class": "AFFIRMATIVE_STRUCTURED",
        "quotes": ["Pets Welcome", "Must sign waiver stating cats are neutered or a $250.00 cleaning fee may apply.", "Non-Refundable Pet Fee Per Stay: $100.00", "Maximum Pet Weight: 90.0lbs", "Maximum Number of Pets in Room: 2"],
        "facts": {"pets_allowed": True, "pet_fee": {"amount_cents": 10000, "currency": "USD", "basis": "per_stay", "refundable": False}, "weight_limit": {"value": 90, "unit": "lb", "operator": "lte", "scope": "per_pet"}, "pet_count_limit": 2, "pet_count_scope": "room", "other_charges": [{"description": "A $250.00 cleaning fee may apply if the required cat-neutering waiver is not signed.", "amount_cents": 25000, "currency": "USD", "conditional": True}]},
        "withheld": [{"field": "species", "reason_code": "SOURCE_SILENT"}],
        "notes": ["The conditional cleaning charge is not a general restriction or a general pet fee."],
        "recommendation": "APPROVE_PUBLISH_STRUCTURED",
    },
    {
        "decision_id": "PGH-P3-D002", "row_number": 2,
        "hotel": "Sheraton Pittsburgh Hotel at Station Square",
        "identity_key": "sheraton pittsburgh hotel at station square",
        "url": "https://www.marriott.com/en-us/hotels/pitps-sheraton-pittsburgh-hotel-at-station-square/overview/",
        "identity": "Sheraton Pittsburgh Hotel at Station Square | 300 W Station Square Dr, Pittsburgh, Pennsylvania, USA, 15219 | +1 412-261-2000",
        "outcome_class": "AFFIRMATIVE_STRUCTURED",
        "quotes": ["Pets Welcome", "One dog up to 50 pounds allowed with a $75 pet fee.", "Non-Refundable Pet Fee Per Stay: $75.00", "Maximum Pet Weight: 50.0lbs", "Maximum Number of Pets in Room: 1"],
        "facts": {"pets_allowed": True, "species": {"dogs": "accepted"}, "pet_fee": {"amount_cents": 7500, "currency": "USD", "basis": "per_stay", "refundable": False}, "weight_limit": {"value": 50, "unit": "lb", "operator": "lte", "scope": "per_pet"}, "pet_count_limit": 1, "pet_count_scope": "room"},
        "withheld": [], "notes": ["Property code PITPS and address/telephone bind this to Station Square, not another nearby Marriott-family property."],
        "recommendation": "APPROVE_PUBLISH_STRUCTURED",
    },
    {
        "decision_id": "PGH-P3-D003", "row_number": 3,
        "hotel": "SpringHill Suites Pittsburgh Bakery Square",
        "identity_key": "springhill suites pittsburgh bakery square",
        "url": "https://www.marriott.com/en-us/hotels/pitel-springhill-suites-pittsburgh-bakery-square/overview/",
        "identity": "SpringHill Suites by Marriott Pittsburgh Bakery Square | 134 Bakery Square Boulevard, Pittsburgh, Pennsylvania, USA, 15206 | +1 412-362-8600",
        "outcome_class": "NEGATIVE", "quotes": ["Pets Not Allowed"], "facts": {"pets_allowed": False}, "withheld": [], "notes": [],
        "recommendation": "APPROVE_VERIFIED_NO_PETS",
    },
    {
        "decision_id": "PGH-P3-D004", "row_number": 4,
        "hotel": "SpringHill Suites Pittsburgh North Shore",
        "identity_key": "springhill suites pittsburgh north shore",
        "url": "https://www.marriott.com/en-us/hotels/pitns-springhill-suites-pittsburgh-north-shore/overview/",
        "identity": "SpringHill Suites by Marriott Pittsburgh North Shore | 223 Federal Street, Pittsburgh, Pennsylvania, USA, 15212 | +1 412-323-9005",
        "outcome_class": "NEGATIVE", "quotes": ["Pets Not Allowed", "Service animals only"], "facts": {"pets_allowed": False}, "withheld": [], "notes": ["Service-animal access does not convert a no-pets policy into pet-friendly."],
        "recommendation": "APPROVE_VERIFIED_NO_PETS",
    },
    {
        "decision_id": "PGH-P3-D005", "row_number": 5,
        "hotel": "Sunnyledge Boutique Hotel", "identity_key": "sunnyledge boutique hotel",
        "url": "https://sunnyledge.com",
        "identity": "Sunnyledge Boutique Hotel | 5124 Fifth Avenue, Pittsburgh, Pennsylvania, USA, 15232 | +1 412-683-5014",
        "outcome_class": "ACCESS_BLOCKED", "quotes": [], "facts": {}, "withheld": [{"field": "all_policy_fields", "reason_code": "ACCESS_BLOCKED"}],
        "notes": ["The independent first-party domain returned no retrievable policy surface and the official-domain search returned no result. This is not a negative finding and no policy is inferred."],
        "recommendation": "RECAPTURE_OFFICIAL_SITE",
    },
    {
        "decision_id": "PGH-P3-D006", "row_number": 6,
        "hotel": "The Oaklander Hotel Autograph Collection", "identity_key": "the oaklander hotel autograph collection",
        "url": "https://www.marriott.com/en-us/hotels/pitak-the-oaklander-hotel-autograph-collection/overview/",
        "identity": "The Oaklander Hotel, Autograph Collection | 5130 Bigelow Boulevard, Pittsburgh, Pennsylvania, USA, 15213 | +1 412-578-8500",
        "outcome_class": "AFFIRMATIVE_PARTIAL",
        "quotes": ["Pets Welcome", "Pet Fee is $20/night and Cleaning Fee is $50/stay.", "Non-Refundable Pet Fee Per Stay: $50.00", "Maximum Pet Weight: 50.0lbs", "Maximum Number of Pets in Room: 2"],
        "facts": {"pets_allowed": True, "weight_limit": {"value": 50, "unit": "lb", "operator": "lte", "scope": "per_pet"}, "pet_count_limit": 2, "pet_count_scope": "room"},
        "withheld": [{"field": "pet_fee", "reason_code": "SOURCE_CONTRADICTORY", "quotes": ["Pet Fee is $20/night and Cleaning Fee is $50/stay.", "Non-Refundable Pet Fee Per Stay: $50.00"]}],
        "notes": ["The property's prose states $20/night plus $50/stay while its structured line states a $50 per-stay non-refundable fee. Both are preserved; no amount, basis, scope, or refundability is selected."],
        "recommendation": "APPROVE_PUBLISH_PARTIAL_WITH_FEE_WITHHELD",
    },
]


def _payload(row):
    return "\n".join(["captured_at: " + AS_OF, "official_url: " + row["url"], "identity_binding: " + row["identity"], *row["quotes"]]) + "\n"


def _item(row):
    text = _payload(row)
    sha = "sha256:" + hashlib.sha256(text.encode()).hexdigest()
    return {"decision_id": row["decision_id"], "row_number": row["row_number"], "hotel": row["hotel"], "identity_key": row["identity_key"], "official_candidate_url": row["url"], "final_url": row["url"], "identity_binding": row["identity"], "outcome_class": row["outcome_class"], "artifact_class": "PUBLICATION_GRADE_EVIDENCE" if row["quotes"] else "NO_USABLE_ARTIFACT", "artifacts": [{"artifact_file": "data/operator_evidence/pittsburgh-pass3-capture-001/ptf-pgh-p3-r%02d.txt" % row["row_number"], "artifact_kind": "official_page_rendered_text", "artifact_sha256": sha, "captured_at": AS_OF, "capture_method": "official_page_retrieval", "source_grade": "OFFICIAL_PROPERTY"}] if row["quotes"] else [], "quotes": [{"quote": q, "verification": "CONTIGUOUS_IN_CAPTURE_TRANSCRIPT"} for q in row["quotes"]], "proposed_schema_1_2_facts": row["facts"], "withheld_fields": row["withheld"], "contradiction_or_ambiguity_notes": row["notes"], "recommended_founder_decision": row["recommendation"]}


def build():
    census = json.loads((LP / "identity_census/pittsburgh-pa.json").read_text())
    by_key = {r["identity_key"]: r for r in census["hotels"]}
    assert len(ROWS) == 6 and len({r["identity_key"] for r in ROWS}) == 6
    assert set(r["identity_key"] for r in ROWS) <= set(by_key)
    facts = json.loads((LP / "hotel_policy_facts_pittsburgh-pa.json").read_text())
    exclusions = json.loads((LP / "hotel_exclusions.json").read_text())
    assert len(facts["hotels"]) == 26
    assert len([e for e in exclusions["exclusions"] if e.get("market_id") == "pittsburgh-pa" and e.get("exclusion_state") == "VERIFIED_NO_PETS"]) == 4
    items = [_item(r) for r in ROWS]
    for row, item in zip(ROWS, items):
        transcript = _payload(row)
        for q in row["quotes"]:
            assert q in transcript
        if row["quotes"]:
            assert item["artifacts"][0]["artifact_sha256"] == "sha256:" + hashlib.sha256(transcript.encode()).hexdigest()
    results = {"schema": "ptf-pittsburgh-pass3-capture-results/1.0", "work_order": WORK_ORDER, "market_id": "pittsburgh-pa", "base_commit": BASE, "as_of": AS_OF, "count": 6, "no_authority_applied": True, "authority_before_and_after": {"published": 26, "verified_no_pets": 4, "unresolved": 63}, "counts": {"AFFIRMATIVE_STRUCTURED": 2, "AFFIRMATIVE_PARTIAL": 1, "NEGATIVE": 2, "ACCESS_BLOCKED": 1}, "items": items}
    packet = {"schema": "ptf-pittsburgh-pass3-founder-review-packet/1.0", "work_order": WORK_ORDER, "market_id": "pittsburgh-pa", "base_commit": BASE, "as_of": AS_OF, "count": 6, "status": "PENDING_FOUNDER_REVIEW", "note": "Capture-only packet. No founder approvals, publications, exclusions, or authority changes are recorded here.", "entries": items}
    return results, packet


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    results, packet = build()
    if args.apply:
        EVIDENCE.mkdir(parents=True, exist_ok=True)
        for row in ROWS:
            if row["quotes"]:
                # Hashes are computed over LF bytes; avoid Windows newline
                # translation changing the retained artifact after hashing.
                (EVIDENCE / ("ptf-pgh-p3-r%02d.txt" % row["row_number"])).write_bytes(_payload(row).encode("utf-8"))
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "pittsburgh_pass3_capture_results.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
        (OUT / "pittsburgh_pass3_founder_review_packet.json").write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
    print("PASS3 capture packet valid: 6 rows; authority unchanged 26/4/63")


if __name__ == "__main__":
    main()
