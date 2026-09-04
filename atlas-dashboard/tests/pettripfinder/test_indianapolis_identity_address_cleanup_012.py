# -*- coding: utf-8 -*-
"""PTF-INDIANAPOLIS-IDENTITY-ADDRESS-CLEANUP-012 -- the shadow cleanup left the
pinned production Indianapolis untouched, preserved every superseded address in
lineage, and queued every retire/merge/rename for the founder instead of
deciding it."""
from __future__ import annotations

import json

from pettripfinder.market_state import current as _pinned
import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

PKG = REPO_ROOT / "launch_packages" / "pettripfinder"
WORK_ORDER = "PTF-INDIANAPOLIS-IDENTITY-ADDRESS-CLEANUP-012"


def _load(rel):
    return json.loads((PKG / rel).read_text(encoding="utf-8-sig"))


def shadow():
    return _load("identity_census_admission/indianapolis-in.json")


def by_key():
    return {h["identity_key"]: h for h in shadow()["hotels"]}


SUPERSEDED = {
    "comfort inn east indianapolis": ("7015 Western Select Drive", "2295 N. Shadeland", "3173599999"),
    "comfort suites indianapolis airport": ("2181 West Southern Avenue", "2750 Fortune Circle West", "3177592371"),
    "wingate by wyndham indianapolis airport plainfield": ("6010 Gateway Drive", "6300 Gateway Drive", "3172042457"),
    "echo suites extended stay by wyndham indianapolis ameriplex": ("8805 Ameriplex Drive", "5831 Alta Lake Drive", "3172839434"),
    "quality inn noblesville indianapolis": ("17070 Dragonfly Drive", "17070 Dragonfly Lane", ""),
}


def test_pinned_production_census_and_live_authority_are_untouched():
    # Untouched BY 012 (257 / 56). PTF-INDIANAPOLIS-PROMOTION-AND-ASSEMBLY-014 then
    # promoted the shadow into the pinned census (263 / 67), carrying every 012
    # supersession with its old address in lineage.
    pinned = _load("identity_census/indianapolis-in.json")
    # 257 at 012, 263 at 014, moved again by PROMOTION-AND-APPLICATION-004.
    # Read from the pin; the supersessions this order applied are asserted
    # row by row below and those are what it actually established.
    assert len(pinned["hotels"]) == _pinned("indianapolis-in").census
    live = _load("hotel_policy_facts_indianapolis-in.json")
    assert len(live["hotels"]) == _pinned("indianapolis-in").pet_friendly
    pin = {h["identity_key"]: h for h in pinned["hotels"]}
    for key, (old, new, _phone) in SUPERSEDED.items():
        assert pin[key]["address"] == new, key
        assert pin[key]["supersession"]["was"]["address"] == old, key


def test_shadow_count_is_unchanged_and_no_identity_was_added_or_removed():
    # 268 at 012 (this order added and removed nothing). 263 since
    # PTF-INDIANAPOLIS-FOUNDER-RULINGS-013 applied the packet: five rows
    # retired into ``retired_013`` (three duplicates, two closures), none added.
    doc = shadow()
    assert doc["count"] == 263 and len(doc["hotels"]) == 263
    assert len({h["identity_key"] for h in doc["hotels"]}) == 263
    assert len(doc["retired_013"]) == 5


def test_every_supersession_keeps_the_old_address_in_lineage():
    rows = by_key()
    for key, (old, new, phone) in SUPERSEDED.items():
        h = rows[key]
        assert h["address"] == new, key
        sup = h["supersession"]
        assert sup["work_order"] == WORK_ORDER
        assert sup["was"]["address"] == old
        assert sup["lineage_preserved"] is True and sup["second_identity_created"] is False
        assert sup["policy_published"] is False
        assert len(sup["proof"]) >= 3
        if phone:
            assert h["phone"] == phone
        assert h["official_url"].startswith("https://")
        assert h["routing_history"][-1]["work_order"] == WORK_ORDER
        assert h["routing_history"][-1]["cost"].startswith("$0")


def test_the_choice_rows_bind_on_their_property_codes():
    rows = by_key()
    assert rows["comfort inn east indianapolis"]["official_url"].endswith("/in099")
    assert rows["comfort suites indianapolis airport"]["official_url"].endswith("/in293")
    assert rows["quality inn noblesville indianapolis"]["official_url"].endswith("/in338")


def test_wyndham_west_is_routed_on_an_exact_telephone_and_not_renamed():
    h = by_key()["wyndham indianapolis west"]
    assert h["official_url"].endswith("/wyndham-indianapolis-airport/overview")
    assert h["phone"] == "3172482481"
    # 012 left the name alone because the rename was the founder's; 013
    # (IDR-012-006) approved it. The key is unchanged and the old name is in
    # name_correction_013.was.
    # 014 carried the founder's name correction into the name_corrections overlay;
    # the census row keeps the key-derived name, as the census contract requires.
    assert h["canonical_name"] == "Wyndham Indianapolis West"
    assert h["name_correction_013"]["was"]["canonical_name"] == "Wyndham Indianapolis West"
    assert h["routing_history"][0]["page_telephone"] == "3172482481"
    assert h["closure_review_012"]["now"].startswith("STILL_ACTIVE")


def test_no_new_duplicate_address_was_introduced():
    def key(h):
        return (h["address"].lower().replace(".", ""), str(h.get("postal_code", "")))
    dup_now = {k for k, n in Counter(key(h) for h in shadow()["hotels"]).items() if n > 1}
    # every superseded target street is either unique or was already shared
    for _key, (_old, new, _phone) in SUPERSEDED.items():
        holders = [h["identity_key"] for h in shadow()["hotels"] if h["address"] == new]
        assert len(holders) == 1, (new, holders)
    assert ("6010 gateway drive", "46168") not in dup_now   # the Wingate left the Baymont's street


def test_held_candidates_resolved_as_aliases_are_recorded_not_added():
    resolved = {c["identity_key"]: c.get("resolution_012") for c in shadow()["identity_key_collisions"]}
    assert resolved["comfort suites indianapolis airport"]["classification"] == "ALREADY_REGISTERED_ALIAS"
    assert resolved["wingate by wyndham indianapolis airport plainfield"]["classification"] == "ALREADY_REGISTERED_ALIAS"


def test_every_retire_merge_or_rename_is_queued_for_the_founder():
    reg = _load("indianapolis_in_identity_review_register_002.json")
    ids = {r["review_id"]: r for r in reg["reviews"]}
    # 012 queued every one of these with acted_on False; 013 applied the
    # founder's rulings, so each is now RULED_AND_APPLIED by 013 and the
    # forbidden list it carried is still on record.
    for rid in ("IDR-012-001", "IDR-012-002", "IDR-012-003", "IDR-012-004", "IDR-012-005", "IDR-012-006", "IDR-007-001"):
        assert ids[rid]["applied_by"] == "PTF-INDIANAPOLIS-FOUNDER-RULINGS-013"
        assert ids[rid]["review_state"] == "RULED_AND_APPLIED"
    assert "retiring, merging or renaming the identity" in ids["IDR-012-001"]["forbidden_until_ruled"]
    # the rows 012 refused to retire left the shadow only through 013's
    # retired_013 block (lineage kept) or its rename (la quinta inn -> Baymont NW)
    rows = by_key()
    retired = {e["row"]["identity_key"] for e in shadow()["retired_013"]}
    for key in ("quality inn and suites noblesville indianapolis", "quality inn brownsburg indianapolis west",
                "echo suites extended stay by wyndham", "americinn by wyndham fishers indianapolis",
                "ramada indianapolis airport"):
        assert key not in rows and key in retired, key
    assert "la quinta inn" not in rows
    assert "la quinta inn" in rows["baymont by wyndham indianapolis northwest"]["prior_census_identity_keys"]
    packet = _load("indianapolis_in_founder_packet_012.json")
    assert {p["review_id"] for p in packet["decisions_requested"]} == {
        "IDR-007-001", "IDR-012-001", "IDR-012-002", "IDR-012-003", "IDR-012-004", "IDR-012-005", "IDR-012-006"}
    assert packet["cost"]["paid_provider_calls"] == 0 and packet["cost"]["usd_spent"] == 0.0


def test_the_address_queue_is_fully_classified():
    reg = _load("indianapolis_in_identity_review_register_002.json")
    q = reg["address_review_queue_006"]
    assert q["count"] == 6 and len(q["rows"]) == 6
    for row in q["rows"]:
        assert row["resolution_012"].split(" ")[0] in ("ADDRESS_SUPERSESSION", "ADDRESS_CONFIRMED_CURRENT", "IDENTITY_UNRESOLVED")


def test_the_rebuilt_cohort_drops_exactly_the_routed_rows():
    c7 = _load("indianapolis_in_unrouted_cohort_007.json")
    c12 = _load("indianapolis_in_unrouted_cohort_012.json")
    assert c12["supersedes"] == "indianapolis_in_unrouted_cohort_007.json"
    # Comfort Suites Airport already carried a URL and was never in 007's
    # cohort, so the drop is the routed set INTERSECTED with 007's keys.
    assert set(c7["identity_keys"]) - set(c12["identity_keys"]) == (
        set(c12["routed_by_012"]) & set(c7["identity_keys"]))
    assert "comfort suites indianapolis airport" in c12["routed_by_012"]
    assert c12["count"] == len(c12["identity_keys"]) == sum(c12["segments"].values())
    assert c12["segments"]["IDENTITY_REVIEW_FIRST"] == 4
    assert c12["segments"]["CLOSED_OR_CONVERTED"] == 2
    rows = by_key()
    for key in c12["routed_by_012"]:
        assert rows[key]["official_url"].startswith("https://"), key


def test_the_cost_plan_prices_the_012_cohort():
    plan = _load("indianapolis_in_routing_cost_plan_003.json")
    c12 = _load("indianapolis_in_unrouted_cohort_012.json")
    # The plan prices the NEWEST cohort: 012's until PTF-INDIANAPOLIS-FOUNDER-
    # RULINGS-013 superseded it with a 100-row cohort.
    newest = PKG / "indianapolis_in_unrouted_cohort_013.json"
    expected = _load(newest.name)["count"] if newest.is_file() else c12["count"]
    assert plan["cohort_primary"]["rows"] == expected
    assert plan["spend_authorized_usd"] == 0.0
    assert plan["cohort_primary"]["conservative_hard_cap_ceiling_usd"] > 0
