"""PTF-LOUISVILLE-ATTENDED-CAPTURE-PASS3-001 -- compile the 12-row batch.

Does not write policy authority or founder approvals.

    python -m scripts.pettripfinder.compile_louisville_pass3_capture
"""
from __future__ import annotations

import hashlib
import json
from collections import OrderedDict
from pathlib import Path

from scripts.pettripfinder.census_partition_builder import write_json
from scripts.pettripfinder.contracts import census, enums, partition

REPO = Path(__file__).resolve().parents[2]
PKG = REPO / "launch_packages" / "pettripfinder"
ART = REPO / "data" / "operator_evidence" / "louisville-pass3-capture-001"
RAW = ART / "raw"
RESULTS = PKG / "markets" / "reports" / "louisville_pass3_capture_results.json"
PACKET = PKG / "markets" / "reports" / "louisville_pass3_founder_review_packet.json"
PREP = PKG / "markets" / "reports" / "louisville_pass3_capture_batch_prepared.json"
CENSUS = PKG / "identity_census" / "louisville-ky.json"
PARTITION = PKG / "louisville_final_partition_001.json"
WORK = "PTF-LOUISVILLE-ATTENDED-CAPTURE-PASS3-001"
AS_OF = "2026-08-16"

BATCH = [
    "myriad hotel",
    "red roof inn louisville expo airport",
    "red roof inn louisville hurstbourne",
    "studio 6 louisville airport expo center",
    "baymont by wyndham louisville airport south",
    "hawthorn suites by wyndham louisville east",
    "travelodge by wyndham sellersburg louisville north",
    "super 8 by wyndham louisville airport",
    "la quinta inn and suites by wyndham louisville northeast old henry",
    "holiday inn express and suites jeffersonville",
    "staybridge suites louisville east",
    "candlewood suites louisville airport",
]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _assert_in(html: str, needle: str, label: str) -> None:
    if needle not in html:
        raise SystemExit("%s missing %r" % (label, needle))


def _blocked(decision_id, hotel, key, hotels, notes, recommended="HOLD_ACCESS_BLOCKED",
             outcome="ACCESS_BLOCKED"):
    return OrderedDict((
        ("decision_id", decision_id),
        ("hotel", hotel),
        ("identity_key", key),
        ("queued_url", hotels[key]["official_url"]),
        ("final_url", hotels[key]["official_url"]),
        ("identity_binding", "NOT_BOUND"),
        ("identity_signals", []),
        ("outcome", outcome),
        ("source_grade", ""),
        ("artifact_relpath", ""),
        ("artifact_sha256", ""),
        ("artifact_bytes", 0),
        ("quotes", []),
        ("proposed_facts", OrderedDict()),
        ("withheld_fields", OrderedDict()),
        ("notes", notes),
        ("recommended_founder_decision", recommended),
    ))


def _not_found(decision_id, hotel, key, hotels, path, final_url, signals, notes):
    html = _text(path)
    for sig in signals:
        _assert_in(html, sig, path.name)
    return OrderedDict((
        ("decision_id", decision_id),
        ("hotel", hotel),
        ("identity_key", key),
        ("queued_url", hotels[key]["official_url"]),
        ("final_url", final_url),
        ("identity_binding", "BOUND"),
        ("identity_signals", signals),
        ("outcome", "POLICY_NOT_FOUND"),
        ("source_grade", enums.GRADE_PT1_FIRST_PARTY),
        ("artifact_relpath", "raw/%s" % path.name),
        ("artifact_sha256", _sha(path)),
        ("artifact_bytes", path.stat().st_size),
        ("quotes", []),
        ("proposed_facts", OrderedDict()),
        ("withheld_fields", OrderedDict()),
        ("notes", notes),
        ("recommended_founder_decision", "HOLD_POLICY_NOT_FOUND"),
    ))


def main() -> None:
    census_doc = json.loads(CENSUS.read_text(encoding="utf-8-sig"))
    hotels = {h["identity_key"]: h for h in census_doc["hotels"]}
    for key in BATCH:
        if key not in hotels:
            raise SystemExit("missing census row %s" % key)

    a_myriad = RAW / "myriad-hotel__home.html"
    a_bay = RAW / "baymont-by-wyndham-louisville-airport-south__home.html"
    a_haw = RAW / "hawthorn-suites-by-wyndham-louisville-east__home.html"
    a_trav = RAW / "travelodge-by-wyndham-sellersburg-louisville-north__home.html"
    a_s8 = RAW / "super-8-by-wyndham-louisville-airport__home.html"
    a_lq = RAW / (
        "la-quinta-inn-and-suites-by-wyndham-louisville-northeast-old-henry"
        "__oldhenry.html"
    )
    for path in (a_myriad, a_bay, a_haw, a_trav, a_s8, a_lq):
        if not path.is_file() or path.stat().st_size < 10000:
            raise SystemExit("missing artifact %s" % path.name)

    rows = [
        _not_found(
            "LVL-P3-001", "Myriad Hotel", "myriad hotel", hotels, a_myriad,
            "https://myriadhotel.com/",
            ["The Myriad Hotel", "900 Baxter", "40204", "502-632-7931"],
            "First-party Myriad site bound. Home and rooms pages contain no "
            "pet-policy wording. FAQ/policies URLs 404. Silence is not a "
            "refusal. Hilton Tapestry was not used.",
        ),
        _blocked(
            "LVL-P3-002", "Red Roof Inn Louisville Expo Airport",
            "red roof inn louisville expo airport", hotels,
            "redroof.com/property/ky/louisville/rri118 returned HTTP 403. "
            "No publication-grade HTML retained. Property-specific first-pet-"
            "free wording was not captured and was not inherited from another "
            "Red Roof.",
        ),
        _blocked(
            "LVL-P3-003", "Red Roof Inn Louisville Hurstbourne",
            "red roof inn louisville hurstbourne", hotels,
            "redroof.com/property/ky/louisville/rri034 returned HTTP 403. "
            "No publication-grade HTML retained. No sibling Red Roof policy "
            "was substituted.",
        ),
        _blocked(
            "LVL-P3-004", "Studio 6 Louisville Airport Expo Center",
            "studio 6 louisville airport expo center", hotels,
            "studio6.com property page timed out with 0 bytes. Capture failed "
            "rather than returning a usable identity-bound page.",
            recommended="HOLD_CAPTURE_FAILED",
            outcome="CAPTURE_FAILED",
        ),
        _not_found(
            "LVL-P3-005", "Baymont by Wyndham Louisville Airport South",
            "baymont by wyndham louisville airport south", hotels, a_bay,
            hotels["baymont by wyndham louisville airport south"]["official_url"],
            ["Baymont by Wyndham Louisville Airport South", "6515 Signature",
             "40213", "502-968-4100"],
            "Property page bound. Pet-policy slot is empty in the captured "
            "HTML (JS-rendered). Brand Wyndham/La Quinta pet pages were not "
            "used. Silence on this artifact is not a fee or species fact.",
        ),
        _not_found(
            "LVL-P3-006", "Hawthorn Suites by Wyndham Louisville East",
            "hawthorn suites by wyndham louisville east", hotels, a_haw,
            hotels["hawthorn suites by wyndham louisville east"]["official_url"],
            ["Hawthorn Suites by Wyndham Louisville East", "751 Cypress",
             "40207", "502-785-0823"],
            "Property page bound. Pet-policy description empty in static HTML. "
            "No brand inheritance.",
        ),
        _not_found(
            "LVL-P3-007", "Travelodge by Wyndham Sellersburg Louisville North",
            "travelodge by wyndham sellersburg louisville north", hotels, a_trav,
            hotels["travelodge by wyndham sellersburg louisville north"]["official_url"],
            ["Travelodge by Wyndham Sellersburg", "7618 Old State Road 60",
             "47172", "812-246-4451"],
            "Property page bound. Pet-policy description empty in static HTML. "
            "No brand inheritance.",
        ),
        _not_found(
            "LVL-P3-008", "Super 8 by Wyndham Louisville Airport",
            "super 8 by wyndham louisville airport", hotels, a_s8,
            hotels["super 8 by wyndham louisville airport"]["official_url"],
            ["Super 8 by Wyndham Louisville Airport", "4800 Preston", "40213"],
            "Property page bound. Pet-policy description empty in static HTML. "
            "No brand inheritance.",
        ),
        _not_found(
            "LVL-P3-009",
            "La Quinta Inn and Suites by Wyndham Louisville Northeast Old Henry",
            "la quinta inn and suites by wyndham louisville northeast old henry",
            hotels, a_lq,
            "https://www.wyndhamhotels.com/laquinta/louisville-kentucky/"
            "la-quinta-inn-and-suites-louisville-ne-old-henry-rd/overview",
            ["13825 Terra View", "40245", "Old Henry"],
            "Prepared URL la-quinta-louisville-east is a different property "
            "(1501 Alliant Ave, 40299). Recovered the Old Henry page at "
            "13825 Terra View Trl, 40245, identifier 53765. Census phone "
            "502-919-7910 vs page +1-502-208-5205. Pet-policy slot empty in "
            "static HTML. Brand La Quinta pet page was not used.",
        ),
        _blocked(
            "LVL-P3-010", "Holiday Inn Express and Suites Jeffersonville",
            "holiday inn express and suites jeffersonville", hotels,
            "ihg.com INDJV hoteldetail returned HTTP 403. No FAQ/hotelinfo "
            "HTML retained. No sibling IHG policy inheritance.",
        ),
        _blocked(
            "LVL-P3-011", "Staybridge Suites Louisville East",
            "staybridge suites louisville east", hotels,
            "ihg.com SDFMT hoteldetail returned HTTP 403. Staybridge ladder "
            "could not be read. No sibling inheritance.",
        ),
        _blocked(
            "LVL-P3-012", "Candlewood Suites Louisville Airport",
            "candlewood suites louisville airport", hotels,
            "ihg.com SDFGL hoteldetail returned HTTP 403. No property FAQ "
            "HTML retained. No sibling Candlewood inheritance.",
        ),
    ]
    if [r["identity_key"] for r in rows] != BATCH:
        raise SystemExit("batch order mismatch")

    rec = partition.reconcile(
        census.identity_keys(census_doc),
        json.loads(PARTITION.read_text(encoding="utf-8-sig")),
        market_id="louisville-ky",
    )
    if rec.published != 0 or rec.verified_no_pets != 0:
        raise SystemExit("authority freeze broken")

    outcomes = [r["outcome"] for r in rows]
    write_json(RESULTS, OrderedDict((
        ("schema", "ptf-louisville-pass3-capture-results/1.0"),
        ("work_order", WORK),
        ("market_id", "louisville-ky"),
        ("as_of", AS_OF),
        ("note",
         "Twelve-row non-Hilton/non-Hyatt attended capture. Raw HTML is "
         "gitignored under data/operator_evidence/louisville-pass3-capture-001/"
         "raw. No policy authority and no founder approvals were written."),
        ("batch_total", 12),
        ("outcome_counts", OrderedDict((
            ("AFFIRMATIVE_STRUCTURED", outcomes.count("AFFIRMATIVE_STRUCTURED")),
            ("AFFIRMATIVE_PARTIAL", outcomes.count("AFFIRMATIVE_PARTIAL")),
            ("NEGATIVE", outcomes.count("NEGATIVE")),
            ("POLICY_NOT_FOUND", outcomes.count("POLICY_NOT_FOUND")),
            ("IDENTITY_UNCERTAIN", outcomes.count("IDENTITY_UNCERTAIN")),
            ("POLICY_CAPTURED_PENDING_IDENTITY_CORRECTION",
             outcomes.count("POLICY_CAPTURED_PENDING_IDENTITY_CORRECTION")),
            ("ROUTING_PROBLEM", outcomes.count("ROUTING_PROBLEM")),
            ("ACCESS_BLOCKED", outcomes.count("ACCESS_BLOCKED")),
            ("CAPTURE_FAILED", outcomes.count("CAPTURE_FAILED")),
        ))),
        ("publication_grade_artifacts",
         sum(1 for r in rows if r["artifact_sha256"])),
        ("positive_candidates", 0),
        ("negative_candidates", 0),
        ("identity_uncertain_candidates", 0),
        ("founder_decisions_required",
         sum(1 for r in rows if r["outcome"] == "POLICY_NOT_FOUND")),
        ("authority_changed", False),
        ("rows", rows),
    )))

    packet_rows = []
    for row in rows:
        packet_rows.append(OrderedDict((
            ("decision_id", row["decision_id"]),
            ("hotel", row["hotel"]),
            ("identity_key", row["identity_key"]),
            ("url", row["queued_url"]),
            ("final_url", row["final_url"]),
            ("identity_binding", row["identity_binding"]),
            ("exact_quotes", row["quotes"]),
            ("artifact_sha256", row["artifact_sha256"]),
            ("source_grade", row["source_grade"]),
            ("proposed_schema_1_2_facts", row["proposed_facts"]),
            ("withheld_fields", row["withheld_fields"]),
            ("ambiguity_or_contradiction", row.get("notes", "")),
            ("recommended_founder_decision", row["recommended_founder_decision"]),
            ("outcome", row["outcome"]),
        )))
    write_json(PACKET, OrderedDict((
        ("schema", "ptf-louisville-pass3-founder-review-packet/1.0"),
        ("work_order", WORK),
        ("market_id", "louisville-ky"),
        ("as_of", AS_OF),
        ("note",
         "Pass 3 founder review packet. No founder approvals written. Prior "
         "decisions remain recorded and unapplied. published=0, no-pets=0."),
        ("founder_approvals_written", False),
        ("decision_count",
         sum(1 for r in rows if r["outcome"] == "POLICY_NOT_FOUND")),
        ("rows", packet_rows),
    )))

    if PREP.is_file():
        prep = json.loads(PREP.read_text(encoding="utf-8-sig"))
        prep["executed"] = True
        prep["executed_work_order"] = WORK
        prep["note"] = (
            "Pass 3 twelve-row capture executed. Hilton and Hyatt excluded. "
            "Authority unchanged."
        )
        write_json(PREP, prep)
    print("batch", 12,
          "publication_grade", sum(1 for r in rows if r["artifact_sha256"]),
          "policy_not_found", outcomes.count("POLICY_NOT_FOUND"),
          "access_blocked", outcomes.count("ACCESS_BLOCKED"),
          "capture_failed", outcomes.count("CAPTURE_FAILED"))


if __name__ == "__main__":
    main()
