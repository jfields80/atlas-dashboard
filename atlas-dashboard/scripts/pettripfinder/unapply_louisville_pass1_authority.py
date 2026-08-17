"""Revert applied Pass 1 authority. Keep D001-D006 recorded.

Required baseline for PTF-LOUISVILLE-ATTENDED-CAPTURE-PASS2-001:

    published = 0
    verified no-pets = 0
    unresolved = 129

    python -m scripts.pettripfinder.unapply_louisville_pass1_authority
"""
from __future__ import annotations

import json
from collections import OrderedDict
from pathlib import Path

from scripts.pettripfinder.census_partition_builder import write_json
from scripts.pettripfinder.contracts import census, enums, partition
from scripts.pettripfinder.contracts.partition import STATE_MEANINGS
from scripts.pettripfinder.hotel_exclusions import EXCLUSIONS_PATH

REPO = Path(__file__).resolve().parents[2]
PKG = REPO / "launch_packages" / "pettripfinder"
CENSUS_PATH = PKG / "identity_census" / "louisville-ky.json"
PARTITION_PATH = PKG / "louisville_final_partition_001.json"
DECISIONS_PATH = PKG / "markets" / "reports" / "louisville_pass1_founder_decisions.json"
PACKET_PATH = PKG / "markets" / "reports" / "louisville_pass1_founder_review_packet.json"
APPROVED_PATH = PKG / "markets" / "reports" / "louisville_pass1_approved_policy_records.json"

RESTORE = (
    "21c museum hotel louisville",
    "bellwether hotel",
    "econo lodge downtown",
)


def _restore_item(item: dict) -> None:
    item["final_state"] = enums.AWAITING_POLICY_OBSERVATION
    item["resolved"] = False
    item["next_action"] = (
        "Capture the property's pet-policy surface on its own official page."
    )
    item["next_action_source"] = "identity_census/louisville-ky.json"
    item["determined_by"] = "PTF-LOUISVILLE-MARKET-BUILD-001"
    item["updated_at"] = "2026-08-15"
    item["state_override_reason"] = ""


def main() -> None:
    census_doc = json.loads(CENSUS_PATH.read_text(encoding="utf-8-sig"))
    part_doc = json.loads(PARTITION_PATH.read_text(encoding="utf-8-sig"))
    items = {i["identity_key"]: i for i in part_doc["items"]}
    hotels = {h["identity_key"]: h for h in census_doc["hotels"]}

    for key in RESTORE:
        _restore_item(items[key])
        hotels[key]["policy_state"] = enums.POLICY_NOT_VERIFIED

    census_doc["note"] = (
        "Louisville visitor-market lodging census. POLICY_NOT_VERIFIED on "
        "every row. Official sources: GoToLouisville, SoIN Tourism, "
        "FlyLouisville courtesy-van roster, Louisville Downtown Partnership."
    )
    part_doc["note"] = (
        "Every Louisville identity is unresolved except confirmed non-lodging "
        "category exits. Pass 1 founder decisions D001-D006 are recorded and "
        "not applied. Silence is not a refusal."
    )
    part_doc["as_of"] = "2026-08-16"
    counts = OrderedDict()
    for state in enums.PARTITION_STATES:
        n = sum(1 for i in part_doc["items"] if i["final_state"] == state)
        if n:
            counts[state] = n
    present = {i["final_state"] for i in part_doc["items"]}
    part_doc["final_state_counts"] = counts
    part_doc["final_state_meanings"] = OrderedDict(
        (s, STATE_MEANINGS[s]) for s in enums.PARTITION_STATES if s in present)

    excl_doc = json.loads(EXCLUSIONS_PATH.read_text(encoding="utf-8-sig"))
    excl_doc["exclusions"] = [
        e for e in excl_doc["exclusions"] if e.get("market_id") != "louisville-ky"
    ]

    write_json(PARTITION_PATH, part_doc)
    write_json(CENSUS_PATH, census_doc)
    write_json(EXCLUSIONS_PATH, excl_doc)
    if APPROVED_PATH.exists():
        APPROVED_PATH.unlink()

    rec = partition.reconcile(
        census.identity_keys(census_doc), part_doc, market_id="louisville-ky")
    if not rec.agrees:
        raise SystemExit("census/partition disagree")
    if rec.published != 0 or rec.verified_no_pets != 0 or rec.unresolved != 129:
        raise SystemExit("expected 0/0/129, got %s/%s/%s"
                         % (rec.published, rec.verified_no_pets, rec.unresolved))
    issues = census.validate(census_doc, market_states=["KY", "IN"])
    if issues:
        raise SystemExit(issues)
    issues = partition.validate(part_doc)
    if issues:
        raise SystemExit(issues)

    decisions = json.loads(DECISIONS_PATH.read_text(encoding="utf-8-sig"))
    for row in decisions["decisions"]:
        row["applied"] = False
        row["publish"] = False
    decisions["note"] = (
        "D001-D006 recorded. Hotel Genevieve has no founder policy decision. "
        "Pass 1 authority is not applied. No publish, merge, or deploy."
    )
    decisions["authority_applied"] = False
    decisions["merged"] = False
    decisions["deployed"] = False
    decisions["published"] = 0
    decisions["verified_no_pets"] = 0
    decisions["unresolved"] = 129
    decisions["site_assembled"] = False
    decisions["release_contract_written"] = False
    decisions["d004_galt_house"] = "RECORDED_NOT_APPLIED"
    write_json(DECISIONS_PATH, decisions)

    packet = json.loads(PACKET_PATH.read_text(encoding="utf-8-sig"))
    packet["authority_applied"] = False
    packet["merged"] = False
    packet["deployed"] = False
    packet["authority_applied_for"] = []
    packet["authority_not_applied_for"] = [
        "D001", "D002", "D003", "D004", "D005", "D006"
    ]
    packet["founder_approvals_written"] = False
    packet["note"] = (
        "D001-D006 recorded verbatim. Hotel Genevieve has no founder policy "
        "decision. Pass 1 authority is not applied. No production policy "
        "file. No publish, merge, or deploy."
    )
    for row in packet.get("rows", ()):
        row["authority_applied"] = False
    for row in packet.get("founder_decisions", ()):
        row["authority_applied"] = False
        row["publish"] = False
    write_json(PACKET_PATH, packet)
    print("published", rec.published, "no_pets", rec.verified_no_pets,
          "unresolved", rec.unresolved)
    print("counts", dict(part_doc["final_state_counts"]))


if __name__ == "__main__":
    main()
