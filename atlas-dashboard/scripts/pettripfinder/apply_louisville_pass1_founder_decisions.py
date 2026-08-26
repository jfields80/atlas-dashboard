"""PTF-LOUISVILLE-PASS1-FOUNDER-DECISIONS-001.

Applies only founder decisions that have been explicitly authorized.

Authorized:

- D001 21c Museum Hotel Louisville — HOLD_PARTIAL_AFFIRMATIVE
- D002 Bellwether Hotel — APPROVE_AFFIRMATIVE_STRUCTURED
- D003 Econo Lodge Downtown — APPROVE_VERIFIED_NO_PETS

D004 Galt House Hotel has no authorized decision text and is not applied.

FROZEN HISTORICAL ONE-SHOT. This pre-sharding replay is deliberately disabled:
PTF-LOUISVILLE-FOUNDING-AUTHORITY-APPLICATION-001A superseded it with the
complete, market-sharded founder-approved authority application. Its retained
body is provenance only and must never be re-enabled to mutate current state.
"""
from __future__ import annotations

import json
from collections import OrderedDict
from pathlib import Path

from scripts.pettripfinder.census_partition_builder import write_json
from scripts.pettripfinder.contracts import census, enums, partition
from scripts.pettripfinder.contracts import evidence as evidence_contract
from scripts.pettripfinder.contracts import policy_schema
from scripts.pettripfinder.hotel_exclusions import (
    approval_hash, record_hash as exclusion_record_hash,
    validate as validate_exclusions,
)
from scripts.pettripfinder.policy_migration import (
    evidence_hash, evidence_ref_for, record_hash,
)

REPO = Path(__file__).resolve().parents[2]
PKG = REPO / "launch_packages" / "pettripfinder"
CENSUS_PATH = PKG / "identity_census" / "louisville-ky.json"
PARTITION_PATH = PKG / "louisville_final_partition_001.json"
RESULTS_PATH = PKG / "markets" / "reports" / "louisville_pass1_capture_results.json"
DECISIONS_PATH = PKG / "markets" / "reports" / "louisville_pass1_founder_decisions.json"
PACKET_PATH = PKG / "markets" / "reports" / "louisville_pass1_founder_review_packet.json"
APPROVED_PATH = PKG / "markets" / "reports" / "louisville_pass1_approved_policy_records.json"
WORK = "PTF-LOUISVILLE-PASS1-FOUNDER-DECISIONS-001"
AS_OF = "2026-08-16"
OPERATOR = "jfields80"
REVIEWED_AT = "2026-08-16T12:00:00-04:00"

BELL_SHA = "f22f9436153498c752fa5ec655e97deab0551835568d5ad917a3ccbc5af8667d"
ECONO_SHA = "5c854fa35d3420f346c9e1e73a6bb58d3faeb4ca6e92f2d6df9e9f147333a579"
BELL_URL = "https://www.thebellwetherhotel.com/faqs"
ECONO_URL = "http://www.econodowntown.com/louisville-ky-hotel-amenities.html"
Q_BELL = (
    "The Bellwether Hotel allows dogs only with the following restrictions: "
    "Dogs are only allowed in first floor rooms. We allow up to two dogs to "
    "stay as long as their combined weight is not over 50 pounds, or one dog "
    "not over 50 pounds. A $35 pet fee will be required at time of booking."
)
Q_BELL_UNATTENDED = (
    "Pets must not be left unattended in room, or anywhere else on hotel "
    "property unless crated."
)
Q_BELL_RESERVE = "Please notify us at time of booking if a dog will be staying."
Q_ECONO = "No Pets Allowed"


def _evidence(field, quote, url, sha, value=None):
    entry = OrderedDict((
        ("field", field),
        ("quote", quote),
        ("source_url", url),
        ("source_grade", enums.GRADE_PT1_FIRST_PARTY),
        ("artifact_class", enums.PUBLICATION_GRADE_EVIDENCE),
        ("artifact_sha256", "sha256:%s" % sha),
        ("artifact_kind", enums.ARTIFACT_RENDERED_HTML),
        ("captured_at", AS_OF),
        ("capture_method", "https_get_official_page"),
    ))
    if value is not None:
        entry["value"] = value
    entry["evidence_ref"] = evidence_ref_for(entry)
    return entry


def _set_terminal(item, state, reason):
    item["final_state"] = state
    item["resolved"] = True
    item["next_action"] = ""
    item["next_action_source"] = ""
    item["determined_by"] = ""
    item["updated_at"] = AS_OF
    item["state_override_reason"] = reason


def _historical_pre_sharding_main() -> None:
    census_doc = json.loads(CENSUS_PATH.read_text(encoding="utf-8-sig"))
    part_doc = json.loads(PARTITION_PATH.read_text(encoding="utf-8-sig"))
    results = json.loads(RESULTS_PATH.read_text(encoding="utf-8-sig"))
    hotels = {h["identity_key"]: h for h in census_doc["hotels"]}
    items = {i["identity_key"]: i for i in part_doc["items"]}
    by_result = {r["identity_key"]: r for r in results["rows"]}

    # D001 — hold 21c on the unresolved queue with the missing-field action.
    item21 = items["21c museum hotel louisville"]
    item21["final_state"] = enums.AWAITING_POLICY_OBSERVATION
    item21["resolved"] = False
    item21["next_action"] = (
        "Re-read the 21c Louisville FAQ and capture explicit pet-fee basis "
        "(per stay / per night) and fee scope (per pet / per room). Species "
        "remains withheld until the page names dogs or cats. Do not publish "
        "the partial record."
    )
    item21["next_action_source"] = (
        "markets/reports/louisville_pass1_founder_decisions.json"
    )
    item21["determined_by"] = WORK
    item21["updated_at"] = AS_OF
    item21["state_override_reason"] = (
        "D001 HOLD_PARTIAL_AFFIRMATIVE. Artifact, quotes, identity binding, "
        "and pets_allowed=true preserved. Missing fee basis and fee scope. "
        "Not published."
    )
    hotels["21c museum hotel louisville"]["policy_state"] = enums.POLICY_NOT_VERIFIED
    census_doc["note"] = (
        "Louisville visitor-market lodging census. D002 confirms Bellwether. "
        "D003 marks Econo Lodge Downtown VERIFIED_NO_PETS. Remaining rows "
        "stay POLICY_NOT_VERIFIED. No production policy package."
    )

    # D002 — Bellwether, source-supported facts only.
    bell_ev = [
        _evidence("pets_allowed", Q_BELL, BELL_URL, BELL_SHA, "true"),
        _evidence("species", Q_BELL, BELL_URL, BELL_SHA, "dogs"),
        _evidence("pet_count_limit", Q_BELL, BELL_URL, BELL_SHA, "2"),
        _evidence("combined_weight_limit", Q_BELL, BELL_URL, BELL_SHA, "50 pounds"),
        _evidence("pet_room_restriction", Q_BELL, BELL_URL, BELL_SHA),
        _evidence("unattended_policy", Q_BELL_UNATTENDED, BELL_URL, BELL_SHA),
        _evidence("reservation_requirement", Q_BELL_RESERVE, BELL_URL, BELL_SHA),
    ]
    facts = OrderedDict((
        ("pets_allowed", True),
        ("species", {"dogs": enums.SPECIES_ACCEPTED}),
        ("pet_count_limit", 2),
        ("combined_weight_limit",
         {"value": 50, "unit": "lb", "operator": enums.OP_LTE}),
        ("pet_room_restriction", "Dogs are only allowed in first floor rooms."),
        ("unattended_policy", Q_BELL_UNATTENDED),
        ("reservation_requirement", Q_BELL_RESERVE),
    ))
    issues = policy_schema.validate_facts(facts)
    if issues:
        raise SystemExit(issues)
    bell_record = OrderedDict((
        ("key", "bellwether hotel"),
        ("name", "Bellwether Hotel"),
        ("facts", facts),
        ("evidence", bell_ev),
        ("evidence_count", len(bell_ev)),
        ("evidence_quote", Q_BELL),
        ("source_url", BELL_URL),
        ("source_type", "EXACT_ENTITY_DOMAIN"),
        ("verification_state", "VERIFIED_PET_FRIENDLY"),
        ("verification_date", AS_OF),
        ("verified_at", AS_OF),
        ("schema_version", "1.2"),
        ("identity_key", "bellwether hotel"),
        ("market_id", "louisville-ky"),
        ("computation_class", enums.NOT_COMPUTABLE),
        ("founder_attested", True),
        ("founder_work_order", WORK),
        ("founder_decision_id", "D002"),
        ("withheld_fields", OrderedDict((
            ("pet_fee", OrderedDict((
                ("reason_code", "SOURCE_AMBIGUOUS"),
                ("reason",
                 "A $35 pet fee is required at booking. The page does not "
                 "state stay/night basis, per-pet/per-room scope, or "
                 "refundability. SOURCE SILENCE = ABSENCE."),
                ("evidence_refs", [bell_ev[0]["evidence_ref"]]),
            ))),
        ))),
    ))
    ev_issues = evidence_contract.validate(bell_record)
    if ev_issues:
        raise SystemExit(ev_issues)
    bell_record["approval"] = OrderedDict((
        ("decision", enums.APPROVED_AFTER_CURRENT_REVIEW),
        ("operator", OPERATOR),
        ("approval_date", AS_OF),
        ("record_hash", record_hash(bell_record)),
        ("evidence_hash", evidence_hash(bell_ev)),
        ("caveats", [
            "D002 APPROVE_AFFIRMATIVE_STRUCTURED. Only source-supported "
            "facts from the Pass 1 packet. $35 fee amount is withheld "
            "pending basis and scope."
        ]),
    ))
    write_json(APPROVED_PATH, OrderedDict((
        ("schema_version", "1.2"),
        ("market", "louisville-ky"),
        ("work_order", WORK),
        ("note",
         "Founder-approved Pass 1 records only. Not a production "
         "hotel_policy_facts_louisville-ky.json and not a release."),
        ("hotels", [bell_record]),
    )))
    _set_terminal(
        items["bellwether hotel"], enums.PUBLISHED_PET_FRIENDLY,
        "D002 APPROVE_AFFIRMATIVE_STRUCTURED. Source-supported facts only. "
        "Fee basis, fee scope, and refundability withheld.")
    hotels["bellwether hotel"]["policy_state"] = enums.POLICY_CONFIRMED

    # D003 — Econo Lodge verified no-pets.
    excl_doc = json.loads(EXCLUSIONS_PATH.read_text(encoding="utf-8-sig"))
    excl_doc["exclusions"] = [
        e for e in excl_doc["exclusions"] if e.get("market_id") != "louisville-ky"
    ]
    econo_hotel = hotels["econo lodge downtown"]
    excl = OrderedDict((
        ("canonical_name", econo_hotel["canonical_name"]),
        ("address", econo_hotel["address"]),
        ("city", econo_hotel["city"]),
        ("state", econo_hotel["state"]),
        ("postal_code", econo_hotel["postal_code"]),
        ("phone", econo_hotel["phone"]),
        ("official_url", econo_hotel["official_url"]),
        ("exclusion_state", enums.VERIFIED_NO_PETS),
        ("evidence_quote", Q_ECONO),
        ("source_url", ECONO_URL),
        ("observed_at", AS_OF),
        ("reviewer_id", OPERATOR),
        ("reviewed_at", REVIEWED_AT),
        ("notes",
         "D003 APPROVE_VERIFIED_NO_PETS. Bound to captured property-specific "
         "amenities artifact sha256:%s. Service-animal access is not "
         "pet-friendly." % ECONO_SHA),
        ("exclusion_id", "excl-econo-lodge-downtown"),
        ("normalized_name", "econo lodge downtown"),
        ("source_hash", "sha256:%s" % ECONO_SHA),
        ("market_id", "louisville-ky"),
    ))
    excl["record_hash"] = exclusion_record_hash(excl)
    excl["approval_hash"] = approval_hash(excl)
    excl_doc["exclusions"].append(excl)
    validate_exclusions(excl_doc)
    write_json(EXCLUSIONS_PATH, excl_doc)
    _set_terminal(
        items["econo lodge downtown"], enums.VERIFIED_NO_PETS,
        "D003 APPROVE_VERIFIED_NO_PETS. First-party wording: No Pets Allowed.")
    hotels["econo lodge downtown"]["policy_state"] = enums.VERIFIED_NO_PETS

    counts = OrderedDict()
    for state in enums.PARTITION_STATES:
        n = sum(1 for i in part_doc["items"] if i["final_state"] == state)
        if n:
            counts[state] = n
    from scripts.pettripfinder.contracts.partition import STATE_MEANINGS
    present = {i["final_state"] for i in part_doc["items"]}
    part_doc["final_state_counts"] = counts
    part_doc["final_state_meanings"] = OrderedDict(
        (s, STATE_MEANINGS[s]) for s in enums.PARTITION_STATES if s in present)
    part_doc["note"] = (
        "D001 holds 21c as a partial affirmative on the unresolved queue. "
        "D002 approves Bellwether source-supported facts. D003 verifies Econo "
        "Lodge Downtown as no-pets. D004 Galt House is not decided. Silence "
        "is not a refusal."
    )
    part_doc["as_of"] = AS_OF
    write_json(PARTITION_PATH, part_doc)
    write_json(CENSUS_PATH, census_doc)

    rec = partition.reconcile(
        census.identity_keys(census_doc), part_doc, market_id="louisville-ky")
    if not rec.agrees:
        raise SystemExit("census/partition disagree")
    issues = census.validate(census_doc, market_states=["KY", "IN"])
    if issues:
        raise SystemExit(issues)
    issues = partition.validate(part_doc)
    if issues:
        raise SystemExit(issues)

    row21 = by_result["21c museum hotel louisville"]
    row_bell = by_result["bellwether hotel"]
    row_econo = by_result["econo lodge downtown"]
    decisions = OrderedDict((
        ("schema", "ptf-louisville-pass1-founder-decisions/1.0"),
        ("work_order", WORK),
        ("market_id", "louisville-ky"),
        ("as_of", AS_OF),
        ("operator", OPERATOR),
        ("note",
         "Authorized decisions only: D001, D002, D003. D004 was received "
         "without a decision and was not applied."),
        ("decisions", [
            OrderedDict((
                ("decision_id", "D001"),
                ("packet_id", "LVL-P1-001"),
                ("identity_key", "21c museum hotel louisville"),
                ("hotel", "21c Museum Hotel Louisville"),
                ("decision", "HOLD_PARTIAL_AFFIRMATIVE"),
                ("publish", False),
                ("queue", True),
                ("preserved", OrderedDict((
                    ("artifact_sha256", row21["artifact_sha256"]),
                    ("artifact_relpath", row21["artifact_relpath"]),
                    ("final_url", row21["final_url"]),
                    ("identity_binding", row21["identity_binding"]),
                    ("identity_signals", row21["identity_signals"]),
                    ("exact_quotes", row21["quotes"]),
                    ("captured_partial_facts", row21["proposed_facts"]),
                    ("withheld_fields", row21["withheld_fields"]),
                    ("next_action", item21["next_action"]),
                ))),
                ("applied", True),
            )),
            OrderedDict((
                ("decision_id", "D002"),
                ("packet_id", "LVL-P1-002"),
                ("identity_key", "bellwether hotel"),
                ("hotel", "Bellwether Hotel"),
                ("decision", "APPROVE_AFFIRMATIVE_STRUCTURED"),
                ("publish", True),
                ("approved_fact_keys", list(facts.keys())),
                ("withheld", ["pet_fee.basis", "pet_fee.scope", "refundability"]),
                ("artifact_sha256", row_bell["artifact_sha256"]),
                ("applied", True),
            )),
            OrderedDict((
                ("decision_id", "D003"),
                ("packet_id", "LVL-P1-003"),
                ("identity_key", "econo lodge downtown"),
                ("hotel", "Econo Lodge Downtown"),
                ("decision", "APPROVE_VERIFIED_NO_PETS"),
                ("publish", False),
                ("artifact_sha256", row_econo["artifact_sha256"]),
                ("evidence_quote", Q_ECONO),
                ("applied", True),
            )),
        ]),
        ("published", rec.published),
        ("verified_no_pets", rec.verified_no_pets),
        ("unresolved", rec.unresolved),
        ("site_assembled", False),
        ("release_contract_written", False),
        ("d004_galt_house", "NOT_DECIDED"),
    ))
    write_json(DECISIONS_PATH, decisions)

    packet = json.loads(PACKET_PATH.read_text(encoding="utf-8-sig"))
    packet["founder_approvals_written"] = True
    packet["applied_work_order"] = WORK
    packet["note"] = (
        "Authorized: D001 hold, D002 Bellwether approve, D003 Econo Lodge "
        "no-pets. D004 Galt House not decided. No production policy file."
    )
    write_json(PACKET_PATH, packet)
    print("published", rec.published, "no_pets", rec.verified_no_pets,
          "unresolved", rec.unresolved)
    print("counts", dict(part_doc["final_state_counts"]))


def main() -> None:
    raise SystemExit(
        "FROZEN_HISTORICAL_ONE_SHOT: use "
        "apply_louisville_founding_authority_001a.py and market-local shards; "
        "this pre-sharding replay is retained only as provenance.")


if __name__ == "__main__":
    main()
