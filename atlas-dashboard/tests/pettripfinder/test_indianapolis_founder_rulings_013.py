# -*- coding: utf-8 -*-
"""PTF-INDIANAPOLIS-FOUNDER-RULINGS-013 -- the seven founder rulings landed on
the shadow census with lineage intact, and nothing production-bearing moved."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.pettripfinder.contracts import census as C  # noqa: E402

PKG = REPO_ROOT / "launch_packages" / "pettripfinder"
WO = "PTF-INDIANAPOLIS-FOUNDER-RULINGS-013"
RETIRED = {"quality inn and suites noblesville indianapolis", "quality inn brownsburg indianapolis west",
           "echo suites extended stay by wyndham", "americinn by wyndham fishers indianapolis",
           "ramada indianapolis airport"}


def _load(rel):
    return json.loads((PKG / rel).read_text(encoding="utf-8-sig"))


def shadow():
    return _load("identity_census_admission/indianapolis-in.json")


def rows():
    return {h["identity_key"]: h for h in shadow()["hotels"]}


def test_pinned_production_is_byte_for_byte_the_257_it_was():
    pinned = _load("identity_census/indianapolis-in.json")
    assert len(pinned["hotels"]) == 257
    pin = C.identity_keys(pinned)
    # every retired or renamed key still lives in the pinned census -- 013 is shadow only
    for key in RETIRED | {"la quinta inn"}:
        if key in pin:
            assert key in pin
    assert len(_load("hotel_policy_facts_indianapolis-in.json")["hotels"]) == 56


def test_shadow_reconciles_to_263_with_five_retirements_and_no_duplicate_key():
    doc = shadow()
    assert doc["count"] == 263 == len(doc["hotels"])
    keys = [h["identity_key"] for h in doc["hotels"]]
    assert len(set(keys)) == 263
    retired = {e["row"]["identity_key"] for e in doc["retired_013"]}
    assert retired == RETIRED
    assert not (retired & set(keys))
    assert doc["founder_rulings_013"]["shadow_before"] == 268
    assert doc["founder_rulings_013"]["decided_by"] == "founder"


def test_every_retirement_keeps_the_whole_row_and_names_its_ruling():
    for e in shadow()["retired_013"]:
        assert e["work_order"] == WO and e["routing"] == "ROUTING_RETIRED"
        assert e["lineage_preserved"] is True and e["second_identity_created"] is False
        assert e["row"]["address"] and e["row"]["provenance"]
        assert len(e["evidence"]) >= 2
        if e["review_id"] in ("IDR-012-001", "IDR-012-002", "IDR-012-003"):
            assert e["merged_into"] in rows()
        if e["review_id"] == "IDR-012-005":
            assert e["merged_into"] == ""      # no successor invented for the Ramada


def test_la_quinta_became_baymont_northwest_with_its_old_name_in_lineage():
    h = rows()["baymont by wyndham indianapolis northwest"]
    assert h["canonical_name"] == "Baymont by Wyndham Indianapolis Northwest"
    assert h["address"] == "3871 W 92nd St" and h["postal_code"] == "46268"
    assert h["phone"] == "3174260215"
    assert h["official_url"].endswith("/baymont-inn-and-suites-indianapolis-northwest/overview")
    assert "la quinta inn" in h["prior_census_identity_keys"]
    sup = h["supersession"]
    assert sup["verdict"] == "SAME_IDENTITY_REBRAND_SUCCESSOR" and sup["decided_by"] == "founder"
    assert sup["was"]["canonical_name"] == "La Quinta Inn" and sup["was"]["address"] == "3871 West 92nd Street"
    assert sup["second_identity_created"] is False and sup["policy_published"] is False


def test_the_merge_targets_are_bound_to_their_choice_property_codes():
    r = rows()
    assert r["quality inn noblesville indianapolis"]["official_url"].endswith("/in338")
    assert r["quality inn noblesville indianapolis"]["merged_in_013"] == ["quality inn and suites noblesville indianapolis"]
    b = r["quality inn and suites brownsburg indianapolis west"]
    assert b["official_url"].endswith("/in441") and b["property_code"] == "IN441"
    assert b["address"] == "31 Maplehurst Drive"
    assert b["merged_in_013"] == ["quality inn brownsburg indianapolis west"]
    e = r["echo suites extended stay by wyndham indianapolis ameriplex"]
    assert e["merged_in_013"] == ["echo suites extended stay by wyndham"]


def test_wyndham_airport_kept_its_key_and_its_old_name():
    h = rows()["wyndham indianapolis west"]
    assert h["canonical_name"] == "Wyndham Indianapolis Airport"
    assert h["name_correction_013"]["identity_key_unchanged"] is True
    assert h["name_correction_013"]["was"]["canonical_name"] == "Wyndham Indianapolis West"


def test_no_new_address_duplicate_and_no_cross_market_collision():
    doc = shadow()
    addr = Counter((h["address"].lower(), h.get("postal_code", "")) for h in doc["hotels"])
    assert addr[("3871 w 92nd st", "46268")] == 1
    new_keys = {"baymont by wyndham indianapolis northwest"}
    for m in ("cincinnati-oh", "cleveland-akron-canton-oh", "columbus-oh", "dayton-oh", "detroit-ann-arbor-mi",
              "grand-rapids-holland-mi", "louisville-ky", "milwaukee-wi", "pittsburgh-pa", "st-louis-mo"):
        assert not (new_keys & C.identity_keys(_load("identity_census/%s.json" % m))), m


def test_pending_policy_inventory_is_preserved_and_binds_to_live_keys():
    pend = _load("indianapolis_in_pending_application_inventory_009.json")
    assert len(pend["CLEAN_PET_FRIENDLY"]) == 11
    assert len(pend["CLEAN_VERIFIED_NO_PETS"]) == 3
    r = rows()
    for rec in pend["CLEAN_PET_FRIENDLY"] + pend["CLEAN_VERIFIED_NO_PETS"]:
        assert rec["identity_key"] in r, rec["identity_key"]


def test_the_register_shows_all_seven_rulings_applied_by_013():
    reg = _load("indianapolis_in_identity_review_register_002.json")
    ids = {x["review_id"]: x for x in reg["reviews"]}
    for rid in ("IDR-007-001", "IDR-012-001", "IDR-012-002", "IDR-012-003", "IDR-012-004", "IDR-012-005", "IDR-012-006"):
        assert ids[rid]["review_state"] == "RULED_AND_APPLIED" and ids[rid]["applied_by"] == WO
        assert ids[rid]["decided_by"] == "founder"
    # nothing else in the register was touched by 013
    others = [x for x in reg["reviews"] if x["review_id"].startswith("IDR-002") or x["review_id"].startswith("IDR-005")]
    assert all(x["applied_by"] != WO for x in others)


def test_the_cohort_after_013_has_nothing_under_review_and_prices_100_rows():
    c12 = _load("indianapolis_in_unrouted_cohort_012.json")
    c13 = _load("indianapolis_in_unrouted_cohort_013.json")
    assert c13["supersedes"] == "indianapolis_in_unrouted_cohort_012.json"
    assert c13["count"] == 100 == len(c13["identity_keys"])
    assert set(c12["identity_keys"]) - set(c13["identity_keys"]) == set(c13["removed_by_013"])
    assert set(c13["removed_by_013"]) == RETIRED | {"la quinta inn"}
    assert c13["segments"]["IDENTITY_REVIEW_FIRST"] == 0 and c13["segments"]["CLOSED_OR_CONVERTED"] == 0
    assert sum(c13["segments"].values()) == 100
    plan = _load("indianapolis_in_routing_cost_plan_003.json")
    assert plan["cohort_primary"]["rows"] == 100 and plan["spend_authorized_usd"] == 0.0
