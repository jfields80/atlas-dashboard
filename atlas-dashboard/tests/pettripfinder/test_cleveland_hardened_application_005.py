"""PTF-CLEVELAND-AKRON-CANTON-HARDENED-APPLICATION-005 -- pins.

* the pinned census is the promoted shadow, whole, with its lineage (the three
  retirements, the Studio 6 -> Suburban Studios supersession, every admission
  block) and a promotion record that names this order;
* the applied authority is exactly the pending inventory: 120 records that
  pass the schema gate, 51 sorted-appended exclusions that re-derive their
  hashes, 120 seed rows -- and no held founder identity is among them;
* the Oakwood explicit assignment is on the corridor without widening 44146;
* the ESA fee ladder and the Red Roof per-additional-pet schedule are WITHHELD
  with their wording, never published as a price;
* partition 005 covers the 220-identity census and the release contract agrees
  with the derived authority on every field;
* the deployment packet announces every non-zero market delta (exactly one:
  this market) and authorizes nothing.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from pettripfinder import epochs
from pettripfinder.market_state import current

_DASH = Path(__file__).resolve().parents[2]
PKG = _DASH / "launch_packages" / "pettripfinder"
MARKET_ID = "cleveland-akron-canton-oh"
M = MARKET_ID.replace("-", "_")
WO = "PTF-CLEVELAND-AKRON-CANTON-HARDENED-APPLICATION-005"

#: What this order left true; its own artifacts (promotion report, partition
#: 005, deployment packet) state these forever. LIVE files are held to the
#: current pin, which agrees exactly while nothing later has moved Cleveland.
EPOCH = epochs.HistoricalEpoch(
    WO, MARKET_ID,
    facts={"census": 220, "pet_friendly": 120, "verified_no_pets": 51,
           "resolved": 171, "unresolved": 49, "census_before": 188,
           "records_applied": 21, "exclusions_applied": 11})
NOW = current(MARKET_ID)


def test_the_live_market_still_stands_at_this_orders_epoch():
    """Exact while nothing later has moved Cleveland; superseded BY NAME after."""
    epochs.whole_market_counts_or_superseded(EPOCH, NOW, {
        "census": "census", "pet_friendly": "pet_friendly",
        "verified_no_pets": "verified_no_pets", "resolved": "resolved",
        "unresolved": "unresolved"})


def _read(p: Path):
    return json.loads(p.read_text(encoding="utf-8-sig"))


def _exists(p: Path):
    if not p.exists():
        pytest.skip("%s not written in this checkout" % p.name)
    return _read(p)


def test_census_is_the_promoted_shadow_with_lineage():
    census = _exists(PKG / "identity_census" / f"{MARKET_ID}.json")
    shadow = _read(PKG / "identity_census_admission" / f"{MARKET_ID}.json")
    assert census["count"] == len(census["hotels"]) == NOW.census
    promo = census["promotion"]
    assert promo["plan_work_order"] == WO and promo["decided_by"] == "founder"
    assert promo["from_count"] == EPOCH.fact("census_before")
    assert promo["to_count"] == EPOCH.fact("census")
    assert promo["retired"] == ["cleveland house hotels", "inn the doghouse", "the rowley inn"]
    assert promo["key_map"] == {"studio 6 extended stay hotel mentor": "suburban studios mentor cleveland northeast"}
    assert shadow["promoted_into_pinned"]["work_order"] == WO
    keys = [h["identity_key"] for h in census["hotels"]]
    assert len(keys) == len(set(keys))
    by = {h["identity_key"]: h for h in census["hotels"]}
    # lineage travelled whole
    assert len(census["retired_non_lodging_002"]) == 3
    assert census["supersessions_002"][0]["to"] == "suburban studios mentor cleveland northeast"
    assert by["suburban studios mentor cleveland northeast"]["superseded_from"]["identity_key"] == "studio 6 extended stay hotel mentor"
    # the held founder identities stay unresolved under their current keys
    for held in ("cambria hotel and suites avon", "woodspring suites cleveland", "harbor inn", "hopp inn",
                 "villa croatia at the american croatian lodge"):
        assert held in by
    assert "holiday inn express and suites cleveland richfield" not in by
    assert "wyndham avon" not in by and "extended stay america select suites cleveland airport" not in by


def test_authority_is_exactly_the_pending_inventory_and_no_held_row_leaked():
    package = _read(PKG / f"hotel_policy_facts_{MARKET_ID}.json")
    report = _exists(PKG / f"{M}_promotion_report_005.json")
    assert len(package["hotels"]) == NOW.pet_friendly
    keys = {h["identity_key"] for h in package["hotels"]}
    assert set(report["summary"]["records_applied"]) <= keys
    assert len(report["summary"]["records_applied"]) == EPOCH.fact("records_applied")
    shard = _read(PKG / "markets" / "authority" / MARKET_ID / "hotel_exclusions.json")
    assert shard["count"] == len(shard["exclusions"]) == NOW.verified_no_pets
    assert len(report["summary"]["exclusions_applied"]) == EPOCH.fact("exclusions_applied")
    excl = {e["normalized_name"] for e in shard["exclusions"]}
    assert not keys & excl, "a hotel is both published and excluded"
    for held in ("best western airport inn and suites cleveland", "candlewood suites cleveland south independence",
                 "candlewood suites beachwood cleveland", "cambria hotel and suites avon",
                 "woodspring suites cleveland", "extended stay america select suites cleveland airport",
                 "holiday inn express and suites cleveland richfield"):
        assert held not in keys and held not in excl, held
    from scripts.pettripfinder.contracts import policy_schema as PS
    assert list(PS.validate_package(package)) == []
    from scripts.pettripfinder import hotel_exclusions as EX
    assert len(EX.validate(shard)) == NOW.verified_no_pets
    # the new exclusions re-derive their hashes and carry a first-party refusal
    new = [e for e in shard["exclusions"] if e["normalized_name"] in set(report["summary"]["exclusions_applied"])]
    assert len(new) == EPOCH.fact("exclusions_applied")
    for e in new:
        assert EX.record_hash(e) == e["record_hash"] and EX.approval_hash(e) == e["approval_hash"]
        assert e["exclusion_state"] == "VERIFIED_NO_PETS" and e["source_hash"].startswith("sha256:")


def test_the_founder_rules_withhold_rather_than_publish_wrong():
    package = _read(PKG / f"hotel_policy_facts_{MARKET_ID}.json")
    by = {h["identity_key"]: h for h in package["hotels"]}
    for key, h in by.items():
        if "extended stay america" in key and h["verification_date"] == "2026-09-01":
            wf = h.get("withheld_fields") or {}
            assert "pet_fee" in wf and wf["pet_fee"]["reason_code"] == "SOURCE_AMBIGUOUS", key
            assert "pet_fee" not in h["facts"], key
            assert h["facts"].get("pet_count_limit") == 2, key
    rr = by["red roof inn akron"]
    assert "pet_fee" not in rr["facts"]
    assert rr["withheld_fields"]["pet_fee"]["reason_code"] == "SCHEMA_CANNOT_REPRESENT"
    assert rr["facts"]["pet_count_limit"] == 3 and rr["facts"]["weight_limit"]["value"] == 80.0
    lq = by["la quinta inn and suites by wyndham cleveland macedonia"]
    assert lq["facts"]["pet_fee"]["amount_cents"] == 2500 and lq["facts"]["pet_fee"]["basis"] == "per_night"
    assert lq["facts"]["fee_cap"]["amount_cents"] == 7500 and lq["facts"]["fee_cap"]["qualifier_stated"] is True
    ss = by["suburban studios mentor cleveland northeast"]
    assert ss["facts"]["pet_fee"]["amount_cents"] == 1000 and ss["facts"]["weight_limit"]["value"] == 30.0


def test_oakwood_explicit_assignment_without_widening():
    market = _read(PKG / "markets" / f"{MARKET_ID}.json")
    east = next(c for c in market["corridors"] if c["corridor_id"].endswith("cleveland-east-beachwood"))
    for key in ("hampton inn and suites oakwood village cleveland",
                "quality inn and suites oakwood village cleveland south"):
        assert key in east["explicit_hotel_ids"]
    assert "44146" not in east["included_postal_codes"]
    assert WO in market["_boundary_note"]


def test_partition_005_and_contract_agree_with_the_authority():
    # The 005 partition is this order's own committed artifact: held to the
    # epoch. The unresolved manifest is a live derived view: held to the pin.
    part = _exists(PKG / "cleveland_final_partition_005.json")
    assert part["count"] == EPOCH.fact("census")
    counts = part["final_state_counts"]
    assert counts["PUBLISHED_PET_FRIENDLY"] == EPOCH.fact("pet_friendly")
    assert counts["VERIFIED_NO_PETS"] == EPOCH.fact("verified_no_pets")
    unresolved = sum(n for s, n in counts.items() if s not in ("PUBLISHED_PET_FRIENDLY", "VERIFIED_NO_PETS", "OUT_OF_CURRENT_CATEGORY"))
    assert unresolved == EPOCH.fact("unresolved")
    um = _read(PKG / "cleveland_unresolved_manifest.json")
    assert (um["confirmed_identities"], um["published_pet_friendly"], um["verified_no_pets"], um["unresolved"]) == (
        NOW.census, NOW.pet_friendly, NOW.verified_no_pets, NOW.unresolved)
    assert len(um["items"]) == NOW.unresolved
    from scripts.pettripfinder.release_contracts import verify_contract
    assert verify_contract(MARKET_ID) == []


def test_routing_authority_has_no_orphan_and_the_successor_route_is_rebound():
    doc = _read(PKG / "markets" / "authority" / MARKET_ID / "identity_routing.json")
    census_keys = {h["identity_key"] for h in _read(PKG / "identity_census" / f"{MARKET_ID}.json")["hotels"]}
    from scripts.pettripfinder.contracts import partition
    assert partition.routing_subset_violations(doc["routes"], census_keys, market_id=MARKET_ID) == ()
    # The successor's route left the shard when the successor was published:
    # a published profile's route authority is the policy package + seed
    # inventory, and a routing row beside a seed row is a double source
    # (the Cincinnati precedent). The row is preserved verbatim in the
    # retirement ledger with its full supersession lineage.
    assert not any(r["hotel_ref"]["identity_key"] == "suburban studios mentor cleveland northeast" for r in doc["routes"])
    ledger = _read(PKG / "cleveland_route_retirement_005_ledger.json")
    assert ledger["count"] == 1
    row = ledger["routes"][0]
    assert row["hotel_ref"]["identity_key"] == "suburban studios mentor cleveland northeast"
    assert "SAME_IDENTITY_REBRAND_SUCCESSOR" in row["notes"]
    retired = [r for r in doc["routes"] if r["status"] == "ROUTING_RETIRED"]
    assert {r["hotel_ref"]["identity_key"] for r in retired} >= {"cleveland house hotels", "inn the doghouse", "the rowley inn"}
    for r in retired:
        assert r.get("retired_at") and r.get("retired_reason")


def test_deployment_packet_announces_every_delta_and_authorizes_nothing():
    packet = _exists(PKG / f"{M}_deployment_packet_005.json")
    assert packet["deployment_authorized"] is False
    assert packet["deployment_performed"] is False
    assert packet["authorization_consumed"] is False
    assert packet["markets_with_nonzero_delta"] == [MARKET_ID]
    assert packet["per_market_delta"][MARKET_ID] == {"live": 99, "candidate": 120, "delta": 21}
    for mid, d in packet["per_market_delta"].items():
        if mid != MARKET_ID:
            assert d["delta"] == 0, (mid, d)
    assert packet["promoted_census_count"] == 220 and packet["pet_friendly_profiles"] == 120
    assert packet["verified_no_pets"] == 51 and packet["unresolved"] == 49
    g = packet["gates"]
    assert (g["broken_links"], g["collisions"], g["global_shadowing"], g["canonical_violations"]) == (0, 0, 0, 0)
    assert packet["production_baseline_deploy_id"] == packet["rollback_deploy_id_for_the_next_deployment"]
    assert re.fullmatch(r"[0-9a-f]{64}", packet["candidate_bundle_sha256"])
    assert re.fullmatch(r"[0-9a-f]{64}", packet["policy_package_sha256"])


def test_participation_status_did_not_move():
    part = _read(_DASH / "deploy" / "netlify" / "launch_participation.json")
    row = next(m for m in part["markets"] if m["market_id"] == MARKET_ID)
    assert row["launch_status"] == "FOUNDER_AUTHORIZED_FOR_LAUNCH"
    assert "220" in row.get("note", "") and WO in row.get("note", "")


def test_promotion_report_spent_nothing_and_deployed_nothing():
    report = _exists(PKG / f"{M}_promotion_report_005.json")
    assert report["paid_provider_calls"] == 0 and report["usd_spent"] == 0.0
    assert report["deployment_performed"] is False
    text = json.dumps(report)
    assert "C:\\\\Atlas" not in text and "C:/Atlas" not in text and "AppData" not in text
