"""Record Pass 2 founder decisions. Reconcile Pass 1+2. Prepare next batch.

Does not apply authority. Does not execute the next capture batch.

    python -m scripts.pettripfinder.record_louisville_pass2_founder_decisions
"""
from __future__ import annotations

import json
from collections import OrderedDict
from pathlib import Path

from scripts.pettripfinder.census_partition_builder import write_json
from scripts.pettripfinder.contracts import census, partition

REPO = Path(__file__).resolve().parents[2]
PKG = REPO / "launch_packages" / "pettripfinder"
P2_PACKET = PKG / "markets" / "reports" / "louisville_pass2_founder_review_packet.json"
P2_DECISIONS = PKG / "markets" / "reports" / "louisville_pass2_founder_decisions.json"
P1_DECISIONS = PKG / "markets" / "reports" / "louisville_pass1_founder_decisions.json"
RECONCILE = PKG / "markets" / "reports" / "louisville_pass1_plus_pass2_founder_decision_reconcile.json"
IDENTITY_ACTION = (
    PKG / "markets" / "reports"
    / "louisville_drury_east_identity_resolution_action.json"
)
NEXT_BATCH = PKG / "markets" / "reports" / "louisville_pass3_capture_batch_prepared.json"
READY = PKG / "markets" / "reports" / "louisville_capture_ready_queue_002.json"
REPAIR = PKG / "markets" / "reports" / "louisville_identity_routing_repair_001.json"
CENSUS = PKG / "identity_census" / "louisville-ky.json"
PARTITION = PKG / "louisville_final_partition_001.json"
WORK = "PTF-LOUISVILLE-PASS2-FOUNDER-DECISIONS-001"
AS_OF = "2026-08-16"

DONE_KEYS = {
    "21c museum hotel louisville",
    "bellwether hotel",
    "econo lodge downtown",
    "galt house hotel",
    "hotel genevieve",
    "hotel louisville downtown",
    "the brown hotel",
    "omni louisville hotel",
    "drury inn and suites louisville",
    "drury inn and suites louisville north",
    "best western greentree inn",
    "radisson hotel louisville north",
}
EXCLUDE_HOSTS = ("hilton.com", "hyatt.com")
NEXT_KEYS = [
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


def main() -> None:
    packet = json.loads(P2_PACKET.read_text(encoding="utf-8-sig"))
    by_row = {r["identity_key"]: r for r in packet["rows"]}
    omni = by_row["omni louisville hotel"]
    east = by_row["drury inn and suites louisville"]
    north = by_row["drury inn and suites louisville north"]

    decisions = [
        OrderedDict((
            ("decision_id", "P2-001"),
            ("packet_id", "LVL-P2-001"),
            ("identity_key", "omni louisville hotel"),
            ("hotel", "Omni Louisville Hotel"),
            ("decision", "APPROVE_AFFIRMATIVE_STRUCTURED"),
            ("class", "APPROVAL_POSITIVE"),
            ("authority_applied", False),
            ("publish", False),
            ("applied", False),
            ("approved_fact_keys", [
                "pets_allowed",
                "species",
                "pet_count_limit",
                "pet_count_scope",
                "weight_limit",
                "other_charges",
            ]),
            ("approved_other_charges", omni["proposed_schema_1_2_facts"]["other_charges"]),
            ("do_not", [
                "convert cleaning_fee into pet_fee",
                "treat credit card on reservation as pet declaration",
                "infer a second pet is accepted",
            ]),
            ("artifact_sha256", omni["artifact_sha256"]),
            ("verbatim",
             "DECISION:\n\nAPPROVE_AFFIRMATIVE_STRUCTURED\n\n"
             "Approve only the source-supported facts presented in the Pass 2 "
             "packet.\n\n"
             "Approve pets_allowed, species = dogs + cats, pet_count_limit = 1, "
             "pet_count_scope = room, weight_limit <=25 lb per_pet.\n\n"
             "Approve the explicitly stated $125 non-refundable cleaning fee as "
             "other_charges with the exact source-supported basis/scope already "
             "proposed.\n\n"
             "Do NOT convert the cleaning fee into a generic pet_fee.\n"
             "Do NOT treat credit card required on reservation as a pet "
             "reservation/declaration requirement.\n"
             "Do NOT infer that a second pet is automatically accepted."),
        )),
        OrderedDict((
            ("decision_id", "P2-002"),
            ("packet_id", "LVL-P2-002"),
            ("identity_key", "drury inn and suites louisville"),
            ("hotel", "Drury Inn and Suites Louisville"),
            ("decision", "HOLD_IDENTITY_CORRECTION"),
            ("class", "HOLD"),
            ("authority_applied", False),
            ("publish", False),
            ("applied", False),
            ("policy_approval", False),
            ("retain_as_provenance", True),
            ("artifact_sha256", east["artifact_sha256"]),
            ("verbatim",
             "DECISION:\n\nHOLD_IDENTITY_CORRECTION\n\n"
             "The captured policy may be retained as provenance/evidence.\n"
             "Do NOT publish it under the current census identity.\n"
             "The East property identity must be corrected/resolved first.\n"
             "The policy wording may be reused only after it is safely rebound "
             "to the corrected final identity.\n"
             "No policy approval yet."),
        )),
        OrderedDict((
            ("decision_id", "P2-003"),
            ("packet_id", "LVL-P2-003"),
            ("identity_key", "drury inn and suites louisville north"),
            ("hotel", "Drury Inn and Suites Louisville North"),
            ("decision", "APPROVE_AFFIRMATIVE_STRUCTURED"),
            ("class", "APPROVAL_POSITIVE"),
            ("authority_applied", False),
            ("publish", False),
            ("applied", False),
            ("approved_fact_keys", [
                "pets_allowed",
                "species",
                "pet_count_limit",
                "pet_count_scope",
                "combined_weight_limit",
                "pet_fee",
            ]),
            ("combined_weight_limit",
             north["proposed_schema_1_2_facts"]["combined_weight_limit"]),
            ("pet_fee", north["proposed_schema_1_2_facts"]["pet_fee"]),
            ("do_not", [
                "convert combined 80 lb to 40 lb per pet",
                "invent refundability or additional qualifiers",
            ]),
            ("artifact_sha256", north["artifact_sha256"]),
            ("verbatim",
             "DECISION:\n\nAPPROVE_AFFIRMATIVE_STRUCTURED\n\n"
             "Approve the source-supported facts exactly as presented.\n\n"
             "Approve pets_allowed, species = dogs + cats, pet_count_limit = 2, "
             "pet_count_scope = room, combined_weight_limit <=80 lb.\n\n"
             "The 80 lb value is a COMBINED room limit. Do NOT convert it to "
             "40 lb per pet.\n\n"
             "Approve the source-stated daily fee $50 per room plus tax using "
             "only the basis/scope the first-party wording explicitly supports. "
             "Preserve the tax relationship. Do not invent refundability."),
        )),
    ]
    no_decision = [
        OrderedDict((
            ("identity_key", "best western greentree inn"),
            ("hotel", "Best Western Greentree Inn"),
            ("packet_id", "LVL-P2-004"),
            ("founder_policy_decision", "NONE"),
            ("decision_id", None),
            ("class", "NO_DECISION_BLOCKED"),
            ("keep_unresolved", True),
            ("lane", "ATTENDED_MANUAL_DATADOME"),
            ("verbatim",
             "NO FOUNDER POLICY DECISION.\n\n"
             "The first-party surface was ACCESS_BLOCKED.\n"
             "JSON-LD or third-party wording was not used as substitute "
             "authority.\nKeep unresolved.\nPrepare a materially different "
             "attended/manual evidence path if one exists."),
        )),
        OrderedDict((
            ("identity_key", "radisson hotel louisville north"),
            ("hotel", "Radisson Hotel Louisville North"),
            ("packet_id", "LVL-P2-005"),
            ("founder_policy_decision", "NONE"),
            ("decision_id", None),
            ("class", "NO_DECISION_BLOCKED"),
            ("keep_unresolved", True),
            ("lane", "ATTENDED_MANUAL_CHOICE"),
            ("verbatim",
             "NO FOUNDER POLICY DECISION.\n\n"
             "The Choice/Radisson surface was ACCESS_BLOCKED.\n"
             "No third-party no-pets wording may be substituted.\n"
             "Keep unresolved.\nPrepare a fresh attended/manual route rather "
             "than repeated automated retries."),
        )),
    ]

    for row in packet["rows"]:
        if row["identity_key"] == "omni louisville hotel":
            row["founder_decision_id"] = "P2-001"
            row["founder_decision"] = "APPROVE_AFFIRMATIVE_STRUCTURED"
            row["founder_decision_recorded"] = True
            row["authority_applied"] = False
        elif row["identity_key"] == "drury inn and suites louisville":
            row["founder_decision_id"] = "P2-002"
            row["founder_decision"] = "HOLD_IDENTITY_CORRECTION"
            row["founder_decision_recorded"] = True
            row["authority_applied"] = False
        elif row["identity_key"] == "drury inn and suites louisville north":
            row["founder_decision_id"] = "P2-003"
            row["founder_decision"] = "APPROVE_AFFIRMATIVE_STRUCTURED"
            row["founder_decision_recorded"] = True
            row["authority_applied"] = False
        else:
            row["founder_decision_id"] = None
            row["founder_decision"] = "NO_FOUNDER_POLICY_DECISION"
            row["founder_decision_recorded"] = False
            row["authority_applied"] = False

    packet["founder_approvals_written"] = False
    packet["founder_decisions_recorded"] = True
    packet["authority_applied"] = False
    packet["merged"] = False
    packet["deployed"] = False
    packet["decision_count"] = 3
    packet["recorded_decision_count"] = 3
    packet["recorded_summary"] = OrderedDict((
        ("decisions_recorded", 3),
        ("approvals_positive", 2),
        ("identity_holds", 1),
        ("no_decision_blocked_rows", 2),
        ("decisions_applied", 0),
    ))
    packet["founder_decisions"] = decisions
    packet["no_founder_policy_decision"] = no_decision
    packet["publish"] = False
    packet["note"] = (
        "Pass 2 founder decisions recorded. Omni and Drury North approved "
        "structured. Drury East held for identity correction. Best Western "
        "and Radisson have no founder policy decision. Authority not applied."
    )
    write_json(P2_PACKET, packet)

    write_json(P2_DECISIONS, OrderedDict((
        ("schema", "ptf-louisville-pass2-founder-decisions/1.0"),
        ("work_order", WORK),
        ("market_id", "louisville-ky"),
        ("as_of", AS_OF),
        ("operator", "jfields80"),
        ("authority_applied", False),
        ("merged", False),
        ("deployed", False),
        ("recorded_decision_count", 3),
        ("recorded_summary", packet["recorded_summary"]),
        ("decisions", decisions),
        ("no_founder_policy_decision", no_decision),
        ("published", 0),
        ("verified_no_pets", 0),
        ("unresolved", 129),
        ("site_assembled", False),
        ("release_contract_written", False),
        ("note",
         "Three Pass 2 founder decisions recorded and not applied. Two "
         "ACCESS_BLOCKED rows have no founder policy decision."),
    )))

    corr = east["identity_correction"]
    write_json(IDENTITY_ACTION, OrderedDict((
        ("schema", "ptf-louisville-identity-resolution-action/1.0"),
        ("work_order", WORK),
        ("identity_key", "drury inn and suites louisville"),
        ("action", "RESOLVE_CENSUS_IDENTITY"),
        ("executed", False),
        ("current_census_canonical_name", corr["census_canonical_name"]),
        ("current_census_address", corr["census_address"]),
        ("observed_property_name", corr["observed_official_name"]),
        ("observed_property_address", corr["observed_address"]),
        ("phone", corr["phone"]),
        ("official_url", corr["url"]),
        ("drury_property_location_identifier", corr["property_code"]),
        ("exact_mismatch", corr["discrepancy"]),
        ("proposed_correction", corr["proposed_identity_correction"]),
        ("policy_reuse",
         "Captured East-page policy wording may be rebound only after the "
         "corrected identity is committed. No policy approval yet."),
        ("next_action",
         "Correct the census canonical name and identity key to the official "
         "Drury Inn and Suites Louisville East / 0105 identity. Do not "
         "silently rename. Do not publish under the current key."),
    )))

    p1 = json.loads(P1_DECISIONS.read_text(encoding="utf-8-sig"))
    p1_summary = p1["recorded_summary"]
    combined = OrderedDict((
        ("decisions_recorded",
         p1_summary["decisions_recorded"] + 3),
        ("approvals_positive",
         p1_summary["approvals_positive"] + 2),
        ("verified_no_pets", p1_summary["verified_no_pets"]),
        ("holds", p1_summary["holds"] + 1),
        ("no_decision_blocked_rows",
         p1_summary["no_decision_blocked_rows"] + 2),
        ("decisions_applied", 0),
    ))
    write_json(RECONCILE, OrderedDict((
        ("schema", "ptf-louisville-pass1-plus-pass2-founder-decision-reconcile/1.0"),
        ("work_order", WORK),
        ("market_id", "louisville-ky"),
        ("as_of", AS_OF),
        ("authority_applied", False),
        ("pass1", OrderedDict((
            ("decisions_recorded", p1_summary["decisions_recorded"]),
            ("approvals_positive", p1_summary["approvals_positive"]),
            ("verified_no_pets", p1_summary["verified_no_pets"]),
            ("holds", p1_summary["holds"]),
            ("no_decision_blocked_rows", p1_summary["no_decision_blocked_rows"]),
            ("positive", ["bellwether hotel", "galt house hotel"]),
            ("verified_no_pets_keys", [
                "econo lodge downtown",
                "hotel louisville downtown",
                "the brown hotel",
            ]),
            ("holds_keys", ["21c museum hotel louisville"]),
            ("no_decision_keys", ["hotel genevieve"]),
        ))),
        ("pass2", OrderedDict((
            ("decisions_recorded", 3),
            ("approvals_positive", 2),
            ("verified_no_pets", 0),
            ("holds", 1),
            ("no_decision_blocked_rows", 2),
            ("positive", [
                "omni louisville hotel",
                "drury inn and suites louisville north",
            ]),
            ("holds_keys", ["drury inn and suites louisville"]),
            ("no_decision_keys", [
                "best western greentree inn",
                "radisson hotel louisville north",
            ]),
        ))),
        ("combined", combined),
        ("note",
         "Mechanical sum of recorded, unapplied Pass 1 and Pass 2 founder "
         "decisions. Authority unchanged."),
    )))

    ready = json.loads(READY.read_text(encoding="utf-8-sig"))
    repair = {
        r["identity_key"]: r
        for r in json.loads(REPAIR.read_text(encoding="utf-8-sig"))["rows"]
    }
    hotels = {
        h["identity_key"]: h
        for h in json.loads(CENSUS.read_text(encoding="utf-8-sig"))["hotels"]
    }
    items = {
        i["identity_key"]: i
        for i in json.loads(PARTITION.read_text(encoding="utf-8-sig"))["items"]
    }
    ready_by = {r["identity_key"]: r for r in ready["items"]}
    batch_items = []
    for order, key in enumerate(NEXT_KEYS, start=1):
        row = ready_by[key]
        hotel = hotels[key]
        item = items[key]
        desk = repair.get(key, {})
        url = hotel["official_url"]
        host = url.split("/")[2]
        assert host not in {"www.hilton.com", "www.hyatt.com"}
        assert key not in DONE_KEYS
        assert desk.get("identity_class", "IDENTITY_CONFIRMED") != (
            "IDENTITY_CORRECTION_REQUIRED"
        )
        batch_items.append(OrderedDict((
            ("order", order),
            ("identity_key", key),
            ("canonical_name", hotel["canonical_name"]),
            ("official_url", url),
            ("url_grade", row.get("url_grade")),
            ("url_class", desk.get("url_class") or row.get("url_grade")),
            ("identity_state", hotel["identity_state"]),
            ("desk_identity_class", desk.get("identity_class", "")),
            ("identity_binding",
             "BOUND" if desk.get("url_class") == "EXACT_PROPERTY_URL_FOUND"
             else "URL_BOUND"),
            ("capture_ready", True),
            ("executed", False),
            ("partition_final_state", item["final_state"]),
        )))
    write_json(NEXT_BATCH, OrderedDict((
        ("schema", "ptf-louisville-pass3-capture-batch-prepared/1.0"),
        ("work_order", WORK),
        ("market_id", "louisville-ky"),
        ("as_of", AS_OF),
        ("executed", False),
        ("excluded", [
            "unresolved identity corrections",
            "best western greentree inn retry",
            "radisson hotel louisville north retry",
            "hilton",
            "hyatt",
        ]),
        ("selection",
         "Clean IDENTITY_CONFIRMED capture-ready rows. Prefer first-party and "
         "property-level non-Hilton/non-Hyatt URLs. Choice retries omitted "
         "after Pass 2 ACCESS_BLOCKED."),
        ("count", len(batch_items)),
        ("items", batch_items),
        ("note",
         "Next Louisville capture batch prepared only. Not executed. "
         "Authority unchanged."),
    )))

    rec = partition.reconcile(
        census.identity_keys(json.loads(CENSUS.read_text(encoding="utf-8-sig"))),
        json.loads(PARTITION.read_text(encoding="utf-8-sig")),
        market_id="louisville-ky",
    )
    if rec.published != 0 or rec.verified_no_pets != 0 or rec.unresolved != 129:
        raise SystemExit("authority freeze broken")
    print("pass2_recorded", 3, "positive", 2, "identity_hold", 1,
          "no_decision", 2)
    print("combined", dict(combined))
    print("next_batch", len(batch_items), "executed", False)


if __name__ == "__main__":
    main()
