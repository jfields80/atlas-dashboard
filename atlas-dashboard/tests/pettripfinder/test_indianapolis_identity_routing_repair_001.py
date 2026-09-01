"""PTF-INDIANAPOLIS-IDENTITY-ROUTING-REPAIR-001 gates."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.pettripfinder.contracts import census, enums, partition
from scripts.pettripfinder.contracts.identity_key import ptf_identity_key

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "launch_packages" / "pettripfinder"
REPAIR = PACKAGE / "indianapolis_identity_routing_repair_001.json"
QUEUE = PACKAGE / "indianapolis_capture_ready_queue_002.json"
CENSUS = PACKAGE / "identity_census" / "indianapolis-in.json"
# 004 until PTF-INDIANAPOLIS-PROMOTION-AND-ASSEMBLY-014 rebuilt the partition over the promoted census.
PARTITION = PACKAGE / "indianapolis_in_final_partition_014.json"


def _json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_crowne_airport_exclusion_remains_applied():
    repair = _json(REPAIR)
    assert repair["crowne_plaza_airport"]["status"] == "APPLIED"
    assert repair["crowne_plaza_airport"]["decision"] == "APPROVE_VERIFIED_NO_PETS"
    rec = partition.reconcile(
        census.identity_keys(_json(CENSUS)), _json(PARTITION),
        market_id="indianapolis-in")
    assert rec.agrees
    # PTF-INDIANAPOLIS-FOUNDER-PROMOTION-004: the promoted census and its factory partition agree row for row;
    # the repair's subject (Crowne Plaza Airport) is still a signed exclusion.
    assert rec.census_count == rec.partition_count == 263     # 257 until 014
    exclusions = _json(PACKAGE / "hotel_exclusions.json")["exclusions"]
    assert "crowne plaza indianapolis airport" in {
        e["normalized_name"] for e in exclusions if e["market_id"] == "indianapolis-in"}


def test_eight_identity_rows_are_classified_without_policy_inference():
    rows = _json(REPAIR)["pass1_eight"]
    assert len(rows) == 8
    by_key = {r["identity_key"]: r for r in rows}
    assert by_key["comfort suites indianapolis airport"]["classification"] == (
        "IDENTITY_CORRECTION_REQUIRED")
    assert by_key["comfort suites indianapolis airport"]["proposed_correction"]["action"] == "REVIEW"
    confirmed = [r for r in rows if r["classification"] == "IDENTITY_CONFIRMED"]
    assert len(confirmed) == 7
    downtown = by_key["crowne plaza indianapolis downtown union station"]
    assert downtown["classification"] == "IDENTITY_CONFIRMED"
    assert "not inherited" in downtown["note"]
    for row in rows:
        assert row["identity_key"] == ptf_identity_key(row["canonical_property_name"])
        assert row["official_property_url"]
        assert "proposed_schema_1_2_facts" not in row


def test_embassy_stays_access_blocked():
    embassy = _json(REPAIR)["embassy_suites_downtown"]
    assert embassy["classification"] == "ACCESS_BLOCKED"
    ready = {h["hotel_id"] for h in _json(QUEUE)["hotels"]}
    assert "embassy suites by hilton indianapolis downtown" not in ready
    assert "hyatt place indianapolis airport" not in ready
    assert "comfort suites indianapolis airport" not in ready
    assert "crowne plaza indianapolis airport" not in ready


def test_broader_audit_covers_every_unresolved_identity():
    repair = _json(REPAIR)
    assert repair["identities_audited"] == 152
    assert repair["census_count"] == 153
    assert sum(repair["audit_class_counts"].values()) == 152
    assert repair["url_corrections"] == 0
    assert repair["renamed_or_converted"] == 0
    assert repair["closed"] == 0
    assert repair["identity_corrections_applied"] == 0
    assert repair["identity_corrections_proposed"] == 1


def test_capture_ready_queue_is_strict_and_loadable():
    queue = _json(QUEUE)
    assert queue["schema"] == "ptf-capture-queue/1.1"
    hotels = queue["hotels"]
    assert len(hotels) == 18
    assert repair_ready_count() == 18
    ids = [h["hotel_id"] for h in hotels]
    assert ids == sorted(ids)
    assert len(ids) == len(set(ids))
    for hotel in hotels:
        assert hotel["official_url"]
        assert hotel["expected_property_code"]
        assert hotel["hotel_id"] == hotel["listing_key"]
        assert hotel["market_id"] == "indianapolis-in"


def repair_ready_count():
    return _json(REPAIR)["capture_ready_count"]


def test_live_indianapolis_policy_package_excludes_identity_repair_rows():
    facts = _json(PACKAGE / "hotel_policy_facts_indianapolis-in.json")
    assert facts["published"] is True
    published = {h["identity_key"] for h in facts["hotels"]}
    assert "comfort suites indianapolis airport" not in published
    assert "home2 suites by hilton indianapolis airport" not in published
