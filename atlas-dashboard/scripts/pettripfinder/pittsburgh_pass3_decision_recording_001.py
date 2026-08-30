"""Record founder decisions for Pittsburgh Pass 3 without applying authority.

This work order intentionally writes only the founder-review packet and a
non-executing application plan.  It never writes hotel policy facts,
exclusions, the census, or the final partition.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LP = ROOT / "launch_packages" / "pettripfinder"
REPORTS = LP / "markets" / "reports"
PACKET_PATH = REPORTS / "pittsburgh_pass3_founder_review_packet.json"
RESULTS_PATH = REPORTS / "pittsburgh_pass3_capture_results.json"
PLAN_PATH = REPORTS / "pittsburgh_pass3_decision_application_plan.json"
FACTS_PATH = LP / "hotel_policy_facts_pittsburgh-pa.json"
EXCLUSIONS_PATH = LP / "hotel_exclusions.json"
PARTITION_PATH = LP / "pittsburgh_final_partition_001.json"
WORK_ORDER = "PTF-PITTSBURGH-PASS3-DECISION-APPLICATION-001"
RECORDED_AT = "2026-08-17"
FOUNDER_SOURCE = "Founder instruction: PITTSBURGH PASS 3 — FOUNDER DECISIONS (2026-08-17)"


DECISIONS = {
    "PGH-P3-D001": {
        "founder_decision": "APPROVE_PUBLISH_STRUCTURED",
        "application_instruction": {
            "target": "published_pet_friendly",
            "approved_facts": ["pets_allowed", "pet_fee=$100 per_stay non_refundable", "weight_limit<=90 lb", "pet_count_limit=2", "pet_count_scope=room"],
            "other_charges": "Preserve the conditional $250 cleaning charge separately with its captured trigger wording.",
            "prohibitions": ["Do not merge the conditional cleaning charge into pet_fee.", "Do not put the conditional cleaning charge in general_restrictions."],
        },
    },
    "PGH-P3-D002": {
        "founder_decision": "APPROVE_PUBLISH_STRUCTURED",
        "application_instruction": {
            "target": "published_pet_friendly",
            "approved_facts": ["pets_allowed", "species=dogs only", "pet_count_limit=1", "weight_limit<=50 lb", "pet_fee=$75 per_stay non_refundable"],
            "prohibitions": ["Do not add cats or another unstated qualifier."],
        },
    },
    "PGH-P3-D003": {
        "founder_decision": "APPROVE_VERIFIED_NO_PETS",
        "application_instruction": {
            "target": "verified_no_pets_exclusion",
            "approved_facts": ["property-specific explicit first-party refusal"],
            "prohibitions": ["Do not treat service-animal access as pet-friendly authority."],
        },
    },
    "PGH-P3-D004": {
        "founder_decision": "APPROVE_VERIFIED_NO_PETS",
        "application_instruction": {
            "target": "verified_no_pets_exclusion",
            "approved_facts": ["property-specific explicit first-party refusal"],
            "prohibitions": ["Service-animal wording is a legal-access exception only; do not create pet-friendly authority."],
        },
    },
    "PGH-P3-D005": {
        "founder_decision": "NO_FOUNDER_POLICY_DECISION",
        "next_action": "RECAPTURE_REQUIRED",
        "application_instruction": {
            "target": "unresolved",
            "approved_facts": [],
            "prohibitions": ["Do not infer VERIFIED_NO_PETS from silence."],
            "required_follow_up": "Use a materially different first-party evidence path if one exists.",
        },
    },
    "PGH-P3-D006": {
        "founder_decision": "APPROVE_WITH_CHANGE",
        "application_instruction": {
            "target": "published_pet_friendly",
            "approved_facts": ["pets_allowed", "weight_limit<=50 lb", "pet_count_limit=2", "pet_count_scope=room"],
            "withhold": {"pet_fee": "SOURCE_CONTRADICTORY"},
            "prohibitions": ["Do not choose, combine, average, or normalize the conflicting monetary representations."],
            "preserve_conflicting_quotes": True,
        },
    },
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def current_authority() -> dict:
    facts = load(FACTS_PATH)
    exclusions = load(EXCLUSIONS_PATH)
    partition = load(PARTITION_PATH)
    published = len(facts["hotels"])
    verified_no_pets = sum(
        exclusion.get("market_id") == "pittsburgh-pa"
        and exclusion.get("exclusion_state") == "VERIFIED_NO_PETS"
        for exclusion in exclusions["exclusions"]
    )
    states = Counter(item["final_state"] for item in partition["items"])
    unresolved = sum(count for state, count in states.items() if state.startswith("AWAITING_"))
    assert (published, verified_no_pets, unresolved) == (26, 4, 63)
    return {
        "published": published,
        "verified_no_pets": verified_no_pets,
        "unresolved": unresolved,
        "authority_sha256": {
            "hotel_policy_facts_pittsburgh_pa": digest(FACTS_PATH),
            "hotel_exclusions": digest(EXCLUSIONS_PATH),
            "pittsburgh_final_partition": digest(PARTITION_PATH),
        },
    }


def record_packet(packet: dict) -> dict:
    entries = packet["entries"]
    assert [entry["decision_id"] for entry in entries] == list(DECISIONS)
    for entry in entries:
        decision = DECISIONS[entry["decision_id"]]
        entry["founder_decision"] = decision["founder_decision"]
        entry["founder_decision_recorded_at"] = RECORDED_AT
        entry["founder_decision_source"] = FOUNDER_SOURCE
        entry["authority_application_status"] = "NOT_APPLIED"
        entry["application_instruction"] = decision["application_instruction"]
        if "next_action" in decision:
            entry["next_action"] = decision["next_action"]
    packet["status"] = "FOUNDER_DECISIONS_RECORDED_NOT_APPLIED"
    packet["note"] = "Founder decisions are recorded in this review packet only. No live approvals, publications, exclusions, or authority changes have been written."
    packet["decision_summary"] = {
        "recorded_policy_decisions": 5,
        "positive_approvals": 3,
        "structured_positive_approvals": 2,
        "verified_no_pets_approvals": 2,
        "approve_with_change": 1,
        "recapture_no_decision": 1,
        "authority_changes_applied": 0,
    }
    packet["next_work_order"] = WORK_ORDER
    return packet


def tail(partition: dict) -> dict:
    items = partition["items"]

    def rows(predicate):
        return [
            {"identity_key": item["identity_key"], "hotel": item["canonical_name"], "current_state": item["final_state"]}
            for item in items if predicate(item)
        ]

    return {
        "identity_review": rows(lambda item: item["final_state"] == "AWAITING_IDENTITY_RESOLUTION"),
        "url_recovery": rows(lambda item: item["final_state"] in {"AWAITING_OFFICIAL_URL", "AWAITING_PROPERTY_LEVEL_URL"}),
        "hyatt_manual": rows(lambda item: "hyatt" in item["canonical_name"].lower()),
        "joinery_recapture": rows(lambda item: item["identity_key"] == "joinery hotel pittsburgh"),
        "census_review": rows(lambda item: item["final_state"] == "AWAITING_CENSUS_REVIEW"),
        "sunnyledge_recapture": rows(lambda item: item["identity_key"] == "sunnyledge boutique hotel"),
    }


def plan(authority: dict, partition: dict) -> dict:
    current_tail = tail(partition)
    assert len(current_tail["identity_review"]) == 38
    assert len(current_tail["url_recovery"]) == 10
    assert len(current_tail["hyatt_manual"]) == 6
    assert len(current_tail["joinery_recapture"]) == 1
    assert len(current_tail["census_review"]) == 3
    assert len(current_tail["sunnyledge_recapture"]) == 1
    return {
        "schema": "ptf-pittsburgh-pass3-decision-application-plan/1.0",
        "work_order": WORK_ORDER,
        "market_id": "pittsburgh-pa",
        "as_of": RECORDED_AT,
        "status": "PREPARED_NOT_EXECUTED",
        "application_performed": False,
        "preconditions": {
            "current_authority": authority,
            "required_founder_decision_ids": list(DECISIONS),
            "revalidate_authority_hashes_before_application": True,
        },
        "proposed_direction_only": {
            "published_delta": 3,
            "verified_no_pets_delta": 2,
            "sunnyledge_remains_unresolved": True,
            "final_unresolved_count": "DERIVE_FROM_REBUILT_PARTITION_AT_APPLICATION",
        },
        "application_order": [
            "Revalidate artifacts, hashes, identity bindings, and current authority immediately before application.",
            "Apply only the five explicit founder policy decisions using the recorded application instructions.",
            "Rebuild the Pittsburgh partition and derive all final state counts from that rebuild.",
            "Run Pittsburgh authority, exclusion, census/partition, routing, release-contract, and governance checks.",
        ],
        "remaining_tail_after_application_prep": current_tail,
        "non_actions": ["Do not apply this plan.", "Do not merge.", "Do not deploy."],
    }


def build() -> tuple[dict, dict]:
    packet = load(PACKET_PATH)
    results = load(RESULTS_PATH)
    assert packet["status"] in {"PENDING_FOUNDER_REVIEW", "FOUNDER_DECISIONS_RECORDED_NOT_APPLIED"}
    if packet["status"] == "FOUNDER_DECISIONS_RECORDED_NOT_APPLIED":
        assert packet["decision_summary"]["authority_changes_applied"] == 0
        for entry in packet["entries"]:
            assert entry["founder_decision"] == DECISIONS[entry["decision_id"]]["founder_decision"]
            assert entry["authority_application_status"] == "NOT_APPLIED"
    assert results["authority_before_and_after"] == {"published": 26, "verified_no_pets": 4, "unresolved": 63}
    authority = current_authority()
    partition = load(PARTITION_PATH)
    return record_packet(packet), plan(authority, partition)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Write only the decision packet and non-executing application plan.")
    args = parser.parse_args()
    packet, application_plan = build()
    if args.apply:
        PACKET_PATH.write_text(json.dumps(packet, indent=2) + "\n", encoding="utf-8")
        PLAN_PATH.write_text(json.dumps(application_plan, indent=2) + "\n", encoding="utf-8")
    print("PASS3 founder decisions recorded: 5 policy decisions, 1 recapture/no-decision; authority unchanged 26/4/63; application prepared but not executed")


if __name__ == "__main__":
    main()
