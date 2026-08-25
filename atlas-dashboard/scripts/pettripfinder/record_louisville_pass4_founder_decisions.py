"""Record the Pass 4 Louisville founder decisions and stage one application.

This records decisions only.  It intentionally does not create policy
authority, exclusions, or a production package.

    python -m scripts.pettripfinder.record_louisville_pass4_founder_decisions
"""
from __future__ import annotations

import json
from collections import OrderedDict
from pathlib import Path

from scripts.pettripfinder.census_partition_builder import write_json
from scripts.pettripfinder.contracts import census, partition

REPO = Path(__file__).resolve().parents[2]
PKG = REPO / "launch_packages" / "pettripfinder"
REPORTS = PKG / "markets" / "reports"
CAPTURE = REPORTS / "louisville_attended_capture_pass4_001.json"
PACKET = REPORTS / "louisville_attended_capture_pass4_founder_review_packet.json"
P1 = REPORTS / "louisville_pass1_founder_decisions.json"
P2 = REPORTS / "louisville_pass2_founder_decisions.json"
DECISIONS = REPORTS / "louisville_pass4_founder_decisions.json"
RECONCILE = REPORTS / "louisville_pass1_plus_pass2_plus_pass4_founder_decision_reconcile.json"
APPLICATION = REPORTS / "louisville_pass4_decision_application_prepared.json"
CENSUS = PKG / "identity_census" / "louisville-ky.json"
PARTITION = PKG / "louisville_final_partition_001.json"
WORK = "PTF-LOUISVILLE-PASS4-FOUNDER-REVIEW-001"
APPLICATION_WORK = "PTF-LOUISVILLE-PASS4-DECISION-APPLICATION-001"
AS_OF = "2026-08-17"


def _decision(row, decision, approved, withheld=(), do_not=(), notes=""):
    return OrderedDict((
        ("decision_id", "P4-%03d" % int(row["decision_id"].rsplit("-", 1)[1])),
        ("packet_id", row["decision_id"]),
        ("identity_key", row["identity_key"]),
        ("hotel", row["hotel"]),
        ("decision", decision),
        ("class", "APPROVAL_NO_PETS" if decision == "APPROVE_VERIFIED_NO_PETS"
         else "APPROVAL_POSITIVE"),
        ("authority_applied", False),
        ("publish", False),
        ("applied", False),
        ("official_url", row["final_url"]),
        ("identity_binding", row["identity_binding"]),
        ("artifacts", row["artifacts"]),
        ("exact_quotes", row["quotes"]),
        ("approved_facts", approved),
        ("withheld_fields", list(withheld)),
        ("do_not", list(do_not)),
        ("notes", notes),
    ))


def _positive_keys(decisions):
    return [d["identity_key"] for d in decisions
            if d["class"] == "APPROVAL_POSITIVE"]


def main() -> None:
    capture = json.loads(CAPTURE.read_text(encoding="utf-8-sig"))
    if capture["batch_total"] != 11 or len(capture["rows"]) != 11:
        raise SystemExit("Pass 4 must contain exactly eleven rows")
    rows = {r["identity_key"]: r for r in capture["rows"]}
    if len(rows) != 11 or any(r["identity_binding"] != "BOUND"
                               for r in rows.values()):
        raise SystemExit("Pass 4 identity gate failed")

    d = []
    d.append(_decision(rows["red roof inn louisville expo airport"],
        "APPROVE_PUBLISH_STRUCTURED", OrderedDict((
            ("pets_allowed", True), ("species", ["cat", "dog"]),
            ("max_pets_per_room", 2), ("first_pet_fee", {"amount_cents": 0}),
            ("second_pet_fee", {"amount_cents": 1500, "basis": "per_night",
                                  "scope": "per_pet", "cap_cents": 10500,
                                  "cap_basis": "per_stay"}),
            ("weight_limit", {"value": 80, "unit": "lb", "operator": "lte",
                              "scope": "per_pet"}),
            ("service_animal_note", "separate_from_normal_pet_policy"),
        )), withheld=("property_wide_guest_deposit",), do_not=(
            "apply the second-pet $105 cap to the first pet",
            "generalize this schedule to another Red Roof property",
        )))
    d.append(_decision(rows["red roof inn louisville hurstbourne"],
        "APPROVE_PUBLISH_STRUCTURED", OrderedDict((
            ("pets_allowed", True), ("species", ["cat", "dog"]),
            ("max_pets_per_room", 2), ("first_pet_fee", {"amount_cents": 0}),
            ("second_pet_fee", {"amount_cents": 1500, "basis": "per_night",
                                  "scope": "per_pet", "cap_cents": 10500,
                                  "cap_basis": "per_stay"}),
            ("weight_limit", {"value": 80, "unit": "lb", "operator": "lte",
                              "scope": "per_pet"}),
        )), withheld=("property_wide_guest_deposit",), do_not=(
            "model the $50 refundable all-guests deposit as a pet deposit",
            "apply the second-pet $105 cap to the first pet",
        ), notes="On-page Louisville East - Hurstbourne identity is bound by rri034."))
    d.append(_decision(rows["studio 6 louisville airport expo center"],
        "APPROVE_PARTIAL_PUBLICATION", OrderedDict((("pets_allowed", True),)),
        withheld=("species", "fee", "weight_limit", "pet_count", "deposit",
                   "fee_basis", "fee_scope"),
        do_not=("infer any source-silent fact", "use generic Studio 6 wording")))
    d.append(_decision(rows["baymont by wyndham louisville airport south"],
        "APPROVE_PUBLISH_STRUCTURED", rows["baymont by wyndham louisville airport south"]["proposed_facts"],
        do_not=("infer facts beyond the captured text",),
        notes="Service animals remain separately stated from the normal dog policy."))
    d.append(_decision(rows["hawthorn suites by wyndham louisville east"],
        "APPROVE_PUBLISH_STRUCTURED", rows["hawthorn suites by wyndham louisville east"]["proposed_facts"],
        withheld=("fee_refundable",), do_not=(
            "normalize or reinterpret the $25 additional-pet charge",
            "alter the 1-4 / 5+ night tier boundaries",
        )))
    travelodge = rows["travelodge by wyndham sellersburg louisville north"]
    d.append(_decision(travelodge, "APPROVE_PUBLISH_STRUCTURED", OrderedDict((
        ("pets_allowed", True), ("species", ["dog", "bird"]),
        ("species_excluded", ["cat"]), ("max_pets_per_room", 1),
        ("pet_fee", {"amount_cents": 2000, "basis": "per_night",
                      "refundability": "non_refundable"}),
        ("other_charges", [{"kind": "sanitation_fee", "amount_cents": 15000,
                            "currency": "USD", "conditional": True,
                            "trigger": "if applicable"}]),
        ("service_animal_note", "separate_from_normal_pet_policy"),
    )), withheld=("weight_limit",), do_not=(
        "put conditional sanitation fee in general_restrictions",
        "merge conditional sanitation fee into base pet fee",
    )))
    super8 = rows["super 8 by wyndham louisville airport"]
    d.append(_decision(super8, "APPROVE_WITH_CHANGE", OrderedDict((
        ("pets_allowed", True), ("max_pets_per_room", 2),
        ("weight_limit", {"value": 50, "unit": "lb", "source_scope": "per room",
                          "scope_interpretation": "SOURCE_TEXT_ONLY"}),
        ("pet_fee", {"amount_cents": 2500, "basis": "per_night",
                      "scope": "per_pet", "refundability": "non_refundable"}),
        ("other_charges", [{"kind": "sanitation_fee", "amount_cents": 15000,
                            "currency": "USD", "conditional": True,
                            "trigger": "if applicable"}]),
    )), withheld=("species", "weight_limit_scope_interpretation"), do_not=(
        "invent species", "convert the source phrase 'per room' to per-pet",
        "merge conditional sanitation fee into base pet fee",
    )))
    d.append(_decision(rows["la quinta inn and suites by wyndham louisville northeast old henry"],
        "APPROVE_PUBLISH_STRUCTURED",
        rows["la quinta inn and suites by wyndham louisville northeast old henry"]["proposed_facts"],
        do_not=("use the prior Alliant Ave routing",),
        notes="Apply only to corrected Old Henry Rd property identity and URL."))
    d.append(_decision(rows["holiday inn express and suites jeffersonville"],
        "APPROVE_VERIFIED_NO_PETS", OrderedDict((("pets_allowed", False),)),
        do_not=("treat separately stated service-animal access as pet-friendly authority",)))
    d.append(_decision(rows["staybridge suites louisville east"],
        "APPROVE_WITH_CHANGE", rows["staybridge suites louisville east"]["proposed_facts"],
        withheld=("refundability", "fee_vs_deposit_characterization"), do_not=(
            "choose between deposit and non-refundable-fee wording",
            "synthesize the contradictory monetary relationship",
        ), notes="Affected monetary relationship is SOURCE_CONTRADICTORY."))
    d.append(_decision(rows["candlewood suites louisville airport"],
        "APPROVE_WITH_CHANGE", rows["candlewood suites louisville airport"]["proposed_facts"],
        withheld=("pet_damage_deposit_vs_fee_relationship",), do_not=(
            "merge $30 nightly fee and separately observed $30 damage deposit",
            "assume the two charges are duplicates",
        ), notes="Deposit/fee relationship remains SOURCE_AMBIGUOUS unless independently representable."))

    if len(d) != 11 or len({x["identity_key"] for x in d}) != 11:
        raise SystemExit("Pass 4 decision membership failure")
    if sum(x["class"] == "APPROVAL_POSITIVE" for x in d) != 10:
        raise SystemExit("expected ten Pass 4 positive approvals")
    if sum(x["class"] == "APPROVAL_NO_PETS" for x in d) != 1:
        raise SystemExit("expected one Pass 4 no-pets approval")
    if sum(x["decision"] == "APPROVE_WITH_CHANGE" for x in d) != 3:
        raise SystemExit("expected three change approvals")

    packet = json.loads(PACKET.read_text(encoding="utf-8-sig"))
    by_decision = {x["identity_key"]: x for x in d}
    for row in packet["rows"]:
        decision = by_decision[row["identity_key"]]
        row["founder_decision_id"] = decision["decision_id"]
        row["founder_decision"] = decision["decision"]
        row["founder_decision_recorded"] = True
        row["authority_applied"] = False
    packet.update(OrderedDict((
        ("founder_approvals_written", False),
        ("founder_decisions_recorded", True),
        ("authority_applied", False), ("merged", False), ("deployed", False),
        ("recorded_decision_count", 11),
        ("recorded_summary", OrderedDict((
            ("approvals_positive", 10), ("verified_no_pets", 1),
            ("approve_with_change", 3), ("decisions_applied", 0),
        ))),
        ("founder_decisions", d),
    )))
    write_json(PACKET, packet)

    decision_doc = OrderedDict((
        ("schema", "ptf-louisville-pass4-founder-decisions/1.0"),
        ("work_order", WORK), ("market_id", "louisville-ky"), ("as_of", AS_OF),
        ("authority_applied", False), ("merged", False), ("deployed", False),
        ("recorded_decision_count", 11),
        ("recorded_summary", packet["recorded_summary"]), ("decisions", d),
        ("published", 0), ("verified_no_pets", 0), ("unresolved", 129),
        ("note", "Founder decisions recorded from Pass 4 instruction; no authority applied."),
    ))
    write_json(DECISIONS, decision_doc)

    p1, p2 = (json.loads(p.read_text(encoding="utf-8-sig")) for p in (P1, P2))
    s1, s2 = p1["recorded_summary"], p2["recorded_summary"]
    p4_positive, p4_negative = _positive_keys(d), [x["identity_key"] for x in d if x["class"] == "APPROVAL_NO_PETS"]
    p1_positive = ["bellwether hotel", "galt house hotel"]
    p1_negative = ["econo lodge downtown", "hotel louisville downtown", "the brown hotel"]
    p2_positive = ["omni louisville hotel", "drury inn and suites louisville north"]
    holds = ["21c museum hotel louisville", "drury inn and suites louisville"]
    blocked = ["hotel genevieve", "best western greentree inn", "radisson hotel louisville north"]
    reconcile = OrderedDict((
        ("schema", "ptf-louisville-pass1-plus-pass2-plus-pass4-founder-decision-reconcile/1.0"),
        ("work_order", WORK), ("market_id", "louisville-ky"), ("as_of", AS_OF),
        ("authority_applied", False),
        ("pass1", OrderedDict((("approvals_positive", s1["approvals_positive"]),
            ("verified_no_pets", s1["verified_no_pets"]), ("positive", p1_positive),
            ("verified_no_pets_keys", p1_negative)))),
        ("pass2", OrderedDict((("approvals_positive", s2["approvals_positive"]),
            ("verified_no_pets", 0), ("positive", p2_positive)))),
        ("pass4", OrderedDict((("approvals_positive", 10), ("verified_no_pets", 1),
            ("approve_with_change", 3), ("positive", p4_positive),
            ("verified_no_pets_keys", p4_negative)))),
        ("holds", OrderedDict((("count", 2), ("keys", holds),
            ("identity_correction_keys", ["drury inn and suites louisville"]),
            ("partial_evidence_hold_keys", ["21c museum hotel louisville"])))),
        ("no_decision_blocked_rows", OrderedDict((("count", 3), ("keys", blocked)))),
        ("combined", OrderedDict((("decisions_recorded", 20),
            ("approvals_positive", 14), ("verified_no_pets", 4), ("holds", 2),
            ("no_decision_blocked_rows", 3), ("decisions_applied", 0)))),
        ("note", "Mechanical all-pass reconciliation. Authority unchanged."),
    ))
    write_json(RECONCILE, reconcile)

    application = OrderedDict((
        ("schema", "ptf-louisville-decision-application-prepared/1.0"),
        ("work_order", APPLICATION_WORK), ("market_id", "louisville-ky"),
        ("as_of", AS_OF), ("executed", False), ("authority_applied", False),
        ("merged", False), ("deployed", False),
        ("input_decision_reports", [P1.name, P2.name, DECISIONS.name]),
        ("atomic_application", True),
        ("approved_positive_keys", p1_positive + p2_positive + p4_positive),
        ("approved_verified_no_pets_keys", p1_negative + p4_negative),
        ("excluded_from_application", OrderedDict((("holds", holds), ("no_decision", blocked)))),
        ("preconditions", [
            "All 18 approved decisions remain recorded and unapplied.",
            "All source artifacts still pass hash and identity validation.",
            "No unresolved hold or no-decision row is materialized.",
            "Stage all 14 positive records and 4 verified-no-pets exclusions before any authority write.",
        ]),
        ("deterministic_steps", [
            "Read the three decision reports and require their exact key sets.",
            "Build one staged Schema 1.2 positive package for the 14 approved positive identities.",
            "Build one staged verified-no-pets exclusion set for the 4 approved explicit refusals.",
            "Validate evidence pointers, identity bindings, policy schema, exclusions, census and partition as one candidate state.",
            "Only after every validation passes, atomically replace Louisville authority surfaces and reconcile market counts.",
        ]),
        ("expected_post_application", OrderedDict((("published", 14),
            ("verified_no_pets", 4), ("unresolved", 111)))),
        ("note", "Prepared only. This is one all-pass atomic application proposal, not execution authority."),
    ))
    write_json(APPLICATION, application)

    rec = partition.reconcile(
        census.identity_keys(json.loads(CENSUS.read_text(encoding="utf-8-sig"))),
        json.loads(PARTITION.read_text(encoding="utf-8-sig")), market_id="louisville-ky")
    if (rec.published, rec.verified_no_pets, rec.unresolved) != (0, 0, 129):
        raise SystemExit("authority freeze broken")
    print("pass4_recorded", 11, "positive", 10, "no_pets", 1)
    print("combined", dict(reconcile["combined"]))
    print("application_prepared", True, "executed", False)


if __name__ == "__main__":
    main()
