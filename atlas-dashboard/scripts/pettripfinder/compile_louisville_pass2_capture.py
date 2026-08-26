"""PTF-LOUISVILLE-ATTENDED-CAPTURE-PASS2-001 -- compile the 5-row batch.

Reads gitignored captured HTML, verifies quote contiguity and identity
signals, and writes the two committed reports. Does not write policy
authority or founder approvals.

    python -m scripts.pettripfinder.compile_louisville_pass2_capture
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
ART = REPO / "data" / "operator_evidence" / "louisville-pass2-capture-001"
RAW = ART / "raw"
RESULTS = PKG / "markets" / "reports" / "louisville_pass2_capture_results.json"
PACKET = PKG / "markets" / "reports" / "louisville_pass2_founder_review_packet.json"
PREP = PKG / "markets" / "reports" / "louisville_pass2_capture_batch_prepared.json"
CENSUS = PKG / "identity_census" / "louisville-ky.json"
PARTITION = PKG / "louisville_final_partition_001.json"
WORK = "PTF-LOUISVILLE-ATTENDED-CAPTURE-PASS2-001"
AS_OF = "2026-08-16"

BATCH = [
    "omni louisville hotel",
    "drury inn and suites louisville",
    "drury inn and suites louisville north",
    "best western greentree inn",
    "radisson hotel louisville north",
]

Q_OMNI = (
    "Omni Louisville Hotel is a pet-friendly hotel. Guests must have a valid "
    "credit card on their reservation. The weight of the pet is not to exceed "
    "25 lbs. A non-refundable cleaning fee of $125 will be charged per stay "
    "per room (not per pet). One pet is allowed per guest room. If guest "
    "plans to have two or more animals in the room, he or she must contact "
    "the hotel directly to discuss. Only dogs and cats are allowed. Extreme "
    "or wild animals (snakes, birds, etc.) are not authorized. In the event a "
    "dog begins to bark or is the cause of guest complaints, the guest will "
    "be asked to remove the pet. The pet must be placed in a carrier when "
    "Hotel Associates enter the room. The guest will be required to sign a "
    "document accepting complete financial responsibility for any damage "
    "caused by the pet. Registered service animals are exempt from the pet "
    "policy - there is no weight limit or pet fee."
)
Q_DRURY = (
    "Dogs and cats accepted. Rooms with pets will be charged a daily fee of "
    "$50 per room plus tax. Service animals are free of charge. Limit of two "
    "pets per room with a combined weight of 80 pounds."
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _assert_contiguous(html: str, quote: str) -> None:
    if quote not in html:
        raise SystemExit("quote not contiguous in artifact: %r" % quote[:80])


def main() -> None:
    census_doc = json.loads(CENSUS.read_text(encoding="utf-8-sig"))
    hotels = {h["identity_key"]: h for h in census_doc["hotels"]}
    for key in BATCH:
        if key not in hotels:
            raise SystemExit("missing census row %s" % key)

    a_omni = RAW / "omni-louisville-hotel__policies.html"
    a_east = RAW / "drury-inn-and-suites-louisville__home.html"
    a_north = RAW / "drury-inn-and-suites-louisville-north__home.html"
    for path in (a_omni, a_east, a_north):
        if not path.is_file() or path.stat().st_size < 1000:
            raise SystemExit("missing artifact %s" % path.name)

    _assert_contiguous(_text(a_omni), Q_OMNI)
    _assert_contiguous(_text(a_omni), "Omni Louisville Hotel")
    _assert_contiguous(_text(a_omni), "400 S 2nd Street")
    _assert_contiguous(_text(a_omni), "40202")
    _assert_contiguous(_text(a_omni), "(502) 313-6664")
    _assert_contiguous(_text(a_east), Q_DRURY)
    _assert_contiguous(_text(a_east), "Drury Inn & Suites Louisville East")
    _assert_contiguous(_text(a_east), "9501 Blairwood Road")
    _assert_contiguous(_text(a_east), "502-326-4170")
    _assert_contiguous(_text(a_north), Q_DRURY)
    _assert_contiguous(_text(a_north), "Drury Inn & Suites Louisville North")
    _assert_contiguous(_text(a_north), "9597 Brownsboro Road")
    _assert_contiguous(_text(a_north), "502-425-5500")

    sha_omni = _sha(a_omni)
    sha_east = _sha(a_east)
    sha_north = _sha(a_north)
    facts_drury = OrderedDict((
        ("pets_allowed", True),
        ("species", ["dog", "cat"]),
        ("pet_count_limit", 2),
        ("pet_count_scope", "per_room"),
        ("combined_weight_limit",
         OrderedDict((("value", 80), ("unit", "lb"), ("operator", enums.OP_LTE)))),
        ("pet_fee", OrderedDict((
            ("amount_cents", 5000),
            ("currency", "USD"),
            ("basis", "per_day"),
            ("scope", "per_room"),
            ("tax_relationship", enums.TAX_PLUS),
        ))),
    ))
    facts_omni = OrderedDict((
        ("pets_allowed", True),
        ("species", ["dog", "cat"]),
        ("pet_count_limit", 1),
        ("pet_count_scope", "per_room"),
        ("weight_limit", OrderedDict((
            ("value", 25),
            ("unit", "lb"),
            ("scope", "per_pet"),
            ("operator", enums.OP_LTE),
        ))),
        ("other_charges", [OrderedDict((
            ("kind", enums.CHARGE_CLEANING_FEE),
            ("amount_cents", 12500),
            ("currency", "USD"),
            ("basis", "per_stay"),
            ("scope", "per_room"),
            ("refundable", False),
        ))]),
        ("reservation_requirement",
         "The guest will be required to sign a document accepting complete "
         "financial responsibility for any damage caused by the pet."),
    ))

    rows = [
        OrderedDict((
            ("decision_id", "LVL-P2-001"),
            ("hotel", "Omni Louisville Hotel"),
            ("identity_key", "omni louisville hotel"),
            ("queued_url", hotels["omni louisville hotel"]["official_url"]),
            ("final_url",
             "https://www.omnihotels.com/hotels/louisville/property-details/policies"),
            ("identity_binding", "BOUND"),
            ("identity_signals", [
                "Omni Louisville Hotel",
                "400 S 2nd Street",
                "40202",
                "(502) 313-6664",
            ]),
            ("outcome", "AFFIRMATIVE_STRUCTURED"),
            ("source_grade", enums.GRADE_PT1_FIRST_PARTY),
            ("artifact_relpath", "raw/omni-louisville-hotel__policies.html"),
            ("artifact_sha256", sha_omni),
            ("artifact_bytes", a_omni.stat().st_size),
            ("quotes", [Q_OMNI]),
            ("proposed_facts", facts_omni),
            ("withheld_fields", OrderedDict((
                ("reservation_requirement.credit_card",
                 "SOURCE_AMBIGUOUS: valid credit card on reservation is payment, "
                 "not a pet-declaration requirement"),
                ("pet_count_limit.exception",
                 "SOURCE_AMBIGUOUS: two or more animals requires contacting the "
                 "hotel; not modeled as a second accepted count"),
            ))),
            ("notes",
             "Property-specific Omni Louisville policies page only. Home page "
             "returned 403. Cleaning fee modeled as other_charges, not a "
             "general restriction. Service-animal exemption is not pet-friendly "
             "expansion."),
            ("recommended_founder_decision", "APPROVE_AFFIRMATIVE_STRUCTURED"),
        )),
        OrderedDict((
            ("decision_id", "LVL-P2-002"),
            ("hotel", "Drury Inn and Suites Louisville"),
            ("identity_key", "drury inn and suites louisville"),
            ("queued_url", hotels["drury inn and suites louisville"]["official_url"]),
            ("final_url",
             "https://www.druryhotels.com/locations/louisville-ky/"
             "drury-inn-and-suites-louisville-east"),
            ("identity_binding", "URL_BOUND_IDENTITY_CORRECTION_OPEN"),
            ("identity_signals", [
                "Drury Inn & Suites Louisville East",
                "9501 Blairwood Road",
                "40222",
                "502-326-4170",
                "0105",
            ]),
            ("outcome", "POLICY_CAPTURED_PENDING_IDENTITY_CORRECTION"),
            ("source_grade", enums.GRADE_PT1_FIRST_PARTY),
            ("artifact_relpath", "raw/drury-inn-and-suites-louisville__home.html"),
            ("artifact_sha256", sha_east),
            ("artifact_bytes", a_east.stat().st_size),
            ("quotes", [Q_DRURY]),
            ("proposed_facts", facts_drury),
            ("withheld_fields", OrderedDict((
                ("publication",
                 "IDENTITY_CORRECTION_OPEN: do not publish under the current "
                 "census identity"),
            ))),
            ("identity_correction", OrderedDict((
                ("census_canonical_name", "Drury Inn and Suites Louisville"),
                ("observed_official_name", "Drury Inn & Suites Louisville East"),
                ("census_address", "9501 Blairwood Road"),
                ("observed_address", "9501 Blairwood Road"),
                ("census_city_state_zip", "Louisville, KY 40222"),
                ("observed_city_state_zip", "Louisville, KY 40222"),
                ("phone", "502-326-4170"),
                ("url",
                 "https://www.druryhotels.com/locations/louisville-ky/"
                 "drury-inn-and-suites-louisville-east"),
                ("property_code", "0105"),
                ("discrepancy",
                 "Official property name is Drury Inn & Suites Louisville East. "
                 "Census canonical name omits East. Street, ZIP, and phone match. "
                 "Earlier desk-pass notes mentioned census 9502; the current "
                 "census row already carries 9501 Blairwood Road."),
                ("proposed_identity_correction",
                 "Rename the census canonical name to Drury Inn and Suites "
                 "Louisville East and re-key to "
                 "'drury inn and suites louisville east'. Do not silently rename."),
            ))),
            ("notes",
             "Policy captured on the official East property page. Not a "
             "publication candidate under the current census identity."),
            ("recommended_founder_decision", "HOLD_IDENTITY_CORRECTION"),
        )),
        OrderedDict((
            ("decision_id", "LVL-P2-003"),
            ("hotel", "Drury Inn and Suites Louisville North"),
            ("identity_key", "drury inn and suites louisville north"),
            ("queued_url",
             hotels["drury inn and suites louisville north"]["official_url"]),
            ("final_url",
             "https://www.druryhotels.com/locations/louisville-ky/"
             "drury-inn-and-suites-louisville-north"),
            ("identity_binding", "BOUND"),
            ("identity_signals", [
                "Drury Inn & Suites Louisville North",
                "9597 Brownsboro Road",
                "40241",
                "502-425-5500",
                "0149",
            ]),
            ("outcome", "AFFIRMATIVE_STRUCTURED"),
            ("source_grade", enums.GRADE_PT1_FIRST_PARTY),
            ("artifact_relpath",
             "raw/drury-inn-and-suites-louisville-north__home.html"),
            ("artifact_sha256", sha_north),
            ("artifact_bytes", a_north.stat().st_size),
            ("quotes", [Q_DRURY]),
            ("proposed_facts", facts_drury),
            ("withheld_fields", OrderedDict()),
            ("notes",
             "Combined 80-pound limit kept as combined_weight_limit with "
             "operator lte. Not converted to per-pet. Brand FAQ was not used "
             "as the property authority."),
            ("recommended_founder_decision", "APPROVE_AFFIRMATIVE_STRUCTURED"),
        )),
        OrderedDict((
            ("decision_id", "LVL-P2-004"),
            ("hotel", "Best Western Greentree Inn"),
            ("identity_key", "best western greentree inn"),
            ("queued_url", hotels["best western greentree inn"]["official_url"]),
            ("final_url", hotels["best western greentree inn"]["official_url"]),
            ("identity_binding", "NOT_BOUND"),
            ("identity_signals", []),
            ("outcome", "ACCESS_BLOCKED"),
            ("source_grade", ""),
            ("artifact_relpath", ""),
            ("artifact_sha256", ""),
            ("artifact_bytes", 0),
            ("quotes", []),
            ("proposed_facts", OrderedDict()),
            ("withheld_fields", OrderedDict()),
            ("notes",
             "bestwestern.com returned HTTP 403 / DataDome challenge. No "
             "publication-grade HTML retained. JSON-LD was not used. Third-party "
             "summaries were not used."),
            ("recommended_founder_decision", "HOLD_ACCESS_BLOCKED"),
        )),
        OrderedDict((
            ("decision_id", "LVL-P2-005"),
            ("hotel", "Radisson Hotel Louisville North"),
            ("identity_key", "radisson hotel louisville north"),
            ("queued_url",
             hotels["radisson hotel louisville north"]["official_url"]),
            ("final_url",
             hotels["radisson hotel louisville north"]["official_url"]),
            ("identity_binding", "NOT_BOUND"),
            ("identity_signals", []),
            ("outcome", "ACCESS_BLOCKED"),
            ("source_grade", ""),
            ("artifact_relpath", ""),
            ("artifact_sha256", ""),
            ("artifact_bytes", 0),
            ("quotes", []),
            ("proposed_facts", OrderedDict()),
            ("withheld_fields", OrderedDict()),
            ("notes",
             "choicehotels.com in043 reset the connection. radissonhotels.com "
             "returned Access Restricted. Identity could not be verified on the "
             "current Choice-family surface. Third-party no-pets summaries were "
             "not used."),
            ("recommended_founder_decision", "HOLD_ACCESS_BLOCKED"),
        )),
    ]

    rec = partition.reconcile(
        census.identity_keys(census_doc),
        json.loads(PARTITION.read_text(encoding="utf-8-sig")),
        market_id="louisville-ky",
    )
    if rec.published != 0 or rec.verified_no_pets != 0:
        raise SystemExit("authority freeze broken: published=%s no_pets=%s"
                         % (rec.published, rec.verified_no_pets))

    results = OrderedDict((
        ("schema", "ptf-louisville-pass2-capture-results/1.0"),
        ("work_order", WORK),
        ("market_id", "louisville-ky"),
        ("as_of", AS_OF),
        ("note",
         "Five-row PT1 independent attended capture. Raw HTML is gitignored "
         "under data/operator_evidence/louisville-pass2-capture-001/raw. No "
         "policy authority and no founder approvals were written. Pass 1 "
         "decisions remain recorded and unapplied."),
        ("batch_total", 5),
        ("outcome_counts", OrderedDict((
            ("AFFIRMATIVE_STRUCTURED", 2),
            ("AFFIRMATIVE_PARTIAL", 0),
            ("NEGATIVE", 0),
            ("POLICY_NOT_FOUND", 0),
            ("POLICY_CAPTURED_PENDING_IDENTITY_CORRECTION", 1),
            ("IDENTITY_UNCERTAIN", 0),
            ("ROUTING_PROBLEM", 0),
            ("ACCESS_BLOCKED", 2),
            ("CAPTURE_FAILED", 0),
        ))),
        ("publication_grade_artifacts", 3),
        ("positive_candidates", 2),
        ("negative_candidates", 0),
        ("identity_correction_candidates", 1),
        ("founder_decisions_required", 3),
        ("authority_changed", False),
        ("rows", rows),
    ))
    write_json(RESULTS, results)

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
            ("identity_correction", row.get("identity_correction", {})),
            ("recommended_founder_decision", row["recommended_founder_decision"]),
            ("outcome", row["outcome"]),
        )))
    write_json(PACKET, OrderedDict((
        ("schema", "ptf-louisville-pass2-founder-review-packet/1.0"),
        ("work_order", WORK),
        ("market_id", "louisville-ky"),
        ("as_of", AS_OF),
        ("note",
         "Pass 2 founder review packet. No founder approvals written. Pass 1 "
         "authority remains unapplied. published=0, verified no-pets=0."),
        ("founder_approvals_written", False),
        ("decision_count", 3),
        ("rows", packet_rows),
    )))

    if PREP.is_file():
        prep = json.loads(PREP.read_text(encoding="utf-8-sig"))
        prep["executed"] = True
        prep["executed_work_order"] = WORK
        prep["note"] = (
            "Pass 2 five-property capture executed. Hilton, Hyatt, and Marriott "
            "were excluded. Authority unchanged."
        )
        write_json(PREP, prep)
    print("batch", 5, "publication_grade", 3, "positive", 2,
          "identity_correction", 1, "access_blocked", 2)


if __name__ == "__main__":
    main()
