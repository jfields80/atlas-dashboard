# -*- coding: utf-8 -*-
"""PTF-INDIANAPOLIS-IDENTITY-ADDRESS-CLEANUP-012 -- the shadow cleanup left the
pinned production Indianapolis untouched, preserved every superseded address in
lineage, and queued every retire/merge/rename for the founder instead of
deciding it."""
from __future__ import annotations

import json
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
    pinned = _load("identity_census/indianapolis-in.json")
    assert len(pinned["hotels"]) == 257
    live = _load("hotel_policy_facts_indianapolis-in.json")
    assert len(live["hotels"]) == 56
    # the pinned rows still carry the addresses the shadow superseded
    pin = {h["identity_key"]: h for h in pinned["hotels"]}
    for key, (old, _new, _phone) in SUPERSEDED.items():
        if key in pin:
            assert pin[key]["address"] == old, key


def test_shadow_count_is_unchanged_and_no_identity_was_added_or_removed():
    doc = shadow()
    assert doc["count"] == 268 and len(doc["hotels"]) == 268
    assert len({h["identity_key"] for h in doc["hotels"]}) == 268


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
    assert h["canonical_name"] == "Wyndham Indianapolis West"       # the rename is the founder's
    assert h["routing_history"][-1]["page_telephone"] == "3172482481"
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
    for rid in ("IDR-012-001", "IDR-012-002", "IDR-012-003", "IDR-012-004", "IDR-012-005", "IDR-012-006"):
        assert ids[rid]["acted_on"] is False
        assert "retiring, merging or renaming the identity" in ids[rid]["forbidden_until_ruled"]
    assert ids["IDR-007-001"]["review_state"] == "SUCCESSOR_IDENTITY_REVIEW"       # still held
    assert ids["IDR-007-001"]["acted_on"] is False
    # the duplicate rows still exist in the shadow -- nothing was retired here
    rows = by_key()
    for key in ("quality inn and suites noblesville indianapolis", "quality inn brownsburg indianapolis west",
                "echo suites extended stay by wyndham", "americinn by wyndham fishers indianapolis",
                "ramada indianapolis airport", "la quinta inn"):
        assert key in rows, key
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
    assert plan["cohort_primary"]["rows"] == c12["count"]
    assert plan["spend_authorized_usd"] == 0.0
    assert plan["cohort_primary"]["conservative_hard_cap_ceiling_usd"] > 0
