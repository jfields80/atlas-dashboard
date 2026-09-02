# -*- coding: utf-8 -*-
"""PTF-INDIANAPOLIS-PROMOTION-AND-ASSEMBLY-014 -- the reviewed shadow became
the pinned census with its lineage, the pending inventory became authority
under the canonical reader, the contract re-derived to zero disagreements,
and nothing was deployed or authorised."""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.pettripfinder.contracts import enums                     # noqa: E402
from scripts.pettripfinder.contracts import policy_schema as PS       # noqa: E402
from scripts.pettripfinder.contracts.identity_key import ptf_identity_key  # noqa: E402
from scripts.pettripfinder.release_contracts import (                 # noqa: E402
    contract_disagreements, derive_authority, load_contract)

from pettripfinder import epochs                                      # noqa: E402
from pettripfinder.market_state import current                        # noqa: E402

PKG = REPO_ROOT / "launch_packages" / "pettripfinder"
WO = "PTF-INDIANAPOLIS-PROMOTION-AND-ASSEMBLY-014"
#: What this order left true; its own partition (014) states it forever, the
#: LIVE files are held to the current pin.
EPOCH = epochs.HistoricalEpoch(
    WO, "indianapolis-in",
    facts={"census": 263, "census_before": 257, "pet_friendly": 67,
           "verified_no_pets": 37, "unresolved": 159})
NOW = current("indianapolis-in")


def test_the_live_market_still_stands_at_this_orders_epoch():
    """Exact while nothing later has moved Indianapolis; superseded BY NAME after."""
    epochs.whole_market_counts_or_superseded(EPOCH, NOW, {
        "census": "census", "pet_friendly": "pet_friendly",
        "verified_no_pets": "verified_no_pets", "unresolved": "unresolved"})
ESA = ("extended stay america indianapolis airport w southern ave", "extended stay america indianapolis lawrence",
       "extended stay america indianapolis northwest", "extended stay america indianapolis west 86th st",
       "extended stay america select suites indianapolis greenwood", "extended stay america select suites indianapolis west")
WYNDHAM_PF = ("baymont by wyndham indianapolis", "baymont by wyndham indianapolis west", "days inn by wyndham indianapolis south",
              "super 8 by wyndham indianapolis emerson ave", "travelodge by wyndham indianapolis speedway")
NO_PETS = ("baymont by wyndham indianapolis northeast", "days inn and suites by wyndham northwest indianapolis",
           "days inn by wyndham indianapolis castleton")


def _load(rel):
    return json.loads((PKG / rel).read_text(encoding="utf-8-sig"))


def test_pinned_census_is_the_promoted_shadow_with_lineage():
    pinned = _load("identity_census/indianapolis-in.json")
    shadow = _load("identity_census_admission/indianapolis-in.json")
    assert pinned["count"] == NOW.census == len(pinned["hotels"])
    assert [h["identity_key"] for h in pinned["hotels"]] == [h["identity_key"] for h in shadow["hotels"]]
    assert pinned["promotion"]["plan_work_order"] == WO
    assert pinned["promotion"]["from_count"] == EPOCH.fact("census_before")
    assert pinned["promotion_history"][0]["plan_work_order"] == "PTF-INDIANAPOLIS-PROMOTION-AUTHORITY-PREP-003"
    assert len(pinned["retired_013"]) == 5 and pinned["founder_rulings_013"]["decided_by"] == "founder"
    assert shadow["promoted_into_pinned"]["work_order"] == WO
    for h in pinned["hotels"]:
        assert ptf_identity_key(h["canonical_name"]) == h["identity_key"], h["identity_key"]


def test_airport_south_is_explicit_and_zip_46221_is_not_widened():
    m = _load("markets/indianapolis-in.json")
    airport = next(c for c in m["corridors"] if c["corridor_id"] == "indianapolis-in__airport")
    assert "woodspring suites indianapolis airport south" in airport["explicit_hotel_ids"]
    assert airport["included_postal_codes"] == ["46241"]
    assert WO in m["_boundary_note"]
    row = next(h for h in _load("identity_census/indianapolis-in.json")["hotels"]
               if h["identity_key"] == "woodspring suites indianapolis airport south")
    assert row["postal_code"] == "46221" and row["corridor"] == "indianapolis-in__airport"


def test_authority_is_67_published_37_refused_and_the_contract_agrees():
    pkg = _load("hotel_policy_facts_indianapolis-in.json")
    assert pkg["count"] == NOW.pet_friendly == len(pkg["hotels"])
    assert list(PS.validate_package(pkg)) == []
    keys = [h["identity_key"] for h in pkg["hotels"]]
    assert len(set(keys)) == NOW.pet_friendly and set(ESA + WYNDHAM_PF) <= set(keys)
    shard = _load("markets/authority/indianapolis-in/hotel_exclusions.json")
    assert shard["count"] == NOW.verified_no_pets
    refused = {e["normalized_name"] for e in shard["exclusions"] if e["exclusion_state"] == enums.VERIFIED_NO_PETS}
    assert set(NO_PETS) <= refused and not (refused & set(keys))
    derived = derive_authority("indianapolis-in")
    assert dict(derived.reconciliation()) == {"confirmed_identities": 263, "published_pet_friendly": 67,
                                              "verified_no_pets": 37, "resolved": 104, "unresolved": 159}
    assert contract_disagreements(load_contract("indianapolis-in"), derived) == []
    assert load_contract("indianapolis-in")["deployment_authorization"]["grants_deployment"] is False


def test_wyndham_records_carry_reader_read_fees_and_conditional_charges_are_withheld():
    pkg = {h["identity_key"]: h for h in _load("hotel_policy_facts_indianapolis-in.json")["hotels"]}
    expected = {"baymont by wyndham indianapolis": 1500, "baymont by wyndham indianapolis west": 2000,
                "days inn by wyndham indianapolis south": 2500, "super 8 by wyndham indianapolis emerson ave": 2500,
                "travelodge by wyndham indianapolis speedway": 2500}
    for key, cents in expected.items():
        fee = pkg[key]["facts"]["pet_fee"]
        assert (fee["amount_cents"], fee["currency"], fee["basis"], fee["scope"]) == (cents, "USD", "per_night", "per_pet"), key
        assert pkg[key]["facts"]["pet_count_limit"] == 2
        assert pkg[key]["approval"]["decision"] == enums.APPROVED_AFTER_CURRENT_REVIEW
        assert all(e["artifact_kind"] == enums.ARTIFACT_TEXT_EXTRACT for e in pkg[key]["evidence"])
    for key in ("baymont by wyndham indianapolis", "days inn by wyndham indianapolis south", "super 8 by wyndham indianapolis emerson ave"):
        assert pkg[key]["withheld_fields"]["other_charges"]["reason_code"] == enums.SCHEMA_CANNOT_REPRESENT
        assert "other_charges" not in pkg[key]["facts"]
    assert pkg["baymont by wyndham indianapolis west"]["withheld_fields"]["other_charges"]["reason_code"] == enums.SOURCE_AMBIGUOUS
    assert pkg["baymont by wyndham indianapolis west"]["facts"]["weight_limit"]["value"] == 25.0
    assert pkg["days inn by wyndham indianapolis south"]["facts"]["weight_limit"]["value"] == 50.0
    assert pkg["travelodge by wyndham indianapolis speedway"]["facts"]["weight_limit"]["value"] == 40.0
    assert pkg["super 8 by wyndham indianapolis emerson ave"]["facts"]["species"] == {"cats": enums.SPECIES_PROHIBITED}
    assert pkg["travelodge by wyndham indianapolis speedway"]["facts"]["species"] == {"dogs": enums.SPECIES_ACCEPTED}


def test_esa_records_publish_the_permission_and_withhold_the_ceiling_ladder():
    pkg = {h["identity_key"]: h for h in _load("hotel_policy_facts_indianapolis-in.json")["hotels"]}
    for key in ESA:
        r = pkg[key]
        assert r["facts"]["pets_allowed"] is True and r["facts"]["pet_count_limit"] == 2
        assert "pet_fee" not in r["facts"]
        assert r["withheld_fields"]["pet_fee"]["reason_code"] == enums.SOURCE_AMBIGUOUS
        assert r["withheld_fields"]["dimension_constraints"]["reason_code"] == enums.SCHEMA_CANNOT_REPRESENT
        assert all(e["artifact_kind"] == enums.ARTIFACT_RENDERED_HTML for e in r["evidence"])
        assert r["service_animal_statement"]["stated"] is True


def test_seed_shard_matches_the_package_and_routes_are_unique():
    rows = list(csv.DictReader((PKG / "markets/authority/indianapolis-in/seed_businesses.csv").open(encoding="utf-8-sig")))
    assert len(rows) == NOW.profiles
    pkg = _load("hotel_policy_facts_indianapolis-in.json")
    names = Counter(r["name"] for r in rows)
    assert max(names.values()) == 1
    assert {r["name"] for r in rows} == {h["name"] for h in pkg["hotels"]}
    assert all(r["market_id"] == "indianapolis-in" and r["category"] == "pet-friendly-hotels" for r in rows)


def test_partition_014_carries_the_authority_as_terminal_states():
    # This order's own committed partition: held to the epoch, not the pin.
    p = _load("indianapolis_in_final_partition_014.json")
    assert p["count"] == EPOCH.fact("census")
    assert p["final_state_counts"][enums.PUBLISHED_PET_FRIENDLY] == EPOCH.fact("pet_friendly")
    assert p["final_state_counts"][enums.VERIFIED_NO_PETS] == EPOCH.fact("verified_no_pets")
    assert sum(n for s, n in p["final_state_counts"].items() if s not in enums.TERMINAL_STATES) == EPOCH.fact("unresolved")
    assert (PKG / "indianapolis_in_final_partition_004.json").is_file()   # the 004 record is kept


def test_participation_status_is_unchanged_and_no_authorization_was_created():
    lp = _load("../../deploy/netlify/launch_participation.json") if False else json.loads(
        (REPO_ROOT / "deploy" / "netlify" / "launch_participation.json").read_text(encoding="utf-8-sig"))
    row = next(r for r in lp["markets"] if r["market_id"] == "indianapolis-in")
    assert row["launch_status"] == "FOUNDER_AUTHORIZED_FOR_LAUNCH"
    assert "67 founder-signed" in row["note"] and "263-identity" in row["note"]
    # the 046 withholding history stays at row.replaces (046's own test reads it
    # there); the note this order replaced is kept under source_state_correction
    assert row["replaces"]["launch_status"] == "SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH"
    assert row["source_state_correction"]["previous_note"].startswith("56 founder-signed")
    assert row["source_state_correction"]["work_order"] == WO
    auths = sorted((REPO_ROOT / "deploy" / "netlify" / "deployment_authorizations").glob("*.json"))
    assert not any("014" in a.name for a in auths)
    report = _load("indianapolis_in_promotion_report_014.json")
    assert report["deployment_performed"] is False and report["paid_provider_calls"] == 0
