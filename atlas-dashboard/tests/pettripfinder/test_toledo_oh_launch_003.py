"""PTF-TOLEDO-OH-DEPLOYMENT-AND-LAUNCH-AUTHORIZATION-003 -- Toledo is live.

The promotion suite proved a market that was REGISTERED and deliberately
invisible. Two of its gates asserted the pre-launch production truth and are
retired there by name. This file is the other half: what must now be true
because Toledo reaches readers.

The gate that matters most here is the delta. A launch is the one change class
that can silently take something away, so "every previously live market moved by
exactly zero" and "no route the previous deploy served is gone" are asserted
against the committed record rather than assumed from a passing build.
"""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE = REPO_ROOT / "launch_packages" / "pettripfinder"
PINS = REPO_ROOT / "tests" / "pettripfinder" / "pins"
DEPLOY = REPO_ROOT / "deploy" / "netlify"

WORK_ORDER = "PTF-TOLEDO-OH-DEPLOYMENT-AND-LAUNCH-AUTHORIZATION-003"
PROMOTION = "PTF-TOLEDO-OH-PROMOTION-AND-APPLICATION-002"
MARKET = "toledo-oh"

AUTH_ID = "ptf-auth-toledo-003-895248738c79"
RECORD_ID = "ptf-deploy-toledo-003-6a9e047690ec8bdaf99bcad2"
DEPLOY_ID = "6a9e047690ec8bdaf99bcad2"
PREVIOUS_DEPLOY = "6a9d33f5dc8c3d1cf9464376"

BUNDLE = "895248738c79bc27f26da5bba1d2a490361ce6bd4959698adf3fb6f892aad8b0"
SITEMAP = "dfdac840be527d5431d0752e702b55fd41d3ee0d2f3635bed6796044d869d56a"
SOURCE_COMMIT = "85c66eea46a64df871af4d1dd51ddb1b8fdcffc7"

#: The bundle the PROMOTION packet pinned. Toledo contributes nothing to it.
PRE_FLIP_BUNDLE = "ca59f3710abde7504dc6c312992e0e2c9db70eccbff737cd12be6ec72708ff1f"

#: What production served before this launch, and what it serves now.
BEFORE = {"markets": 10, "profiles": 786, "routes": 945}
AFTER = {"markets": 11, "profiles": 803, "routes": 966}
TOLEDO = {"profiles": 17, "routes": 21, "corridors": 2, "census": 54,
          "verified_no_pets": 9}


def _load(path: Path) -> dict:
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def auth() -> dict:
    return _load(DEPLOY / "deployment_authorizations" / ("%s.json" % AUTH_ID))


def record() -> dict:
    return _load(DEPLOY / "deployment_records" / ("%s.json" % RECORD_ID))


def live_pin() -> dict:
    return _load(PINS / "deployment_state.json")["live"]


# --------------------------------------------------------------------------
# Toledo is live.
# --------------------------------------------------------------------------

def test_toledo_participates_in_the_composed_bundle():
    from scripts.pettripfinder import launch_participation as LP
    assert LP.launch_status(MARKET) == LP.FOUNDER_AUTHORIZED_FOR_LAUNCH
    decision = _load(DEPLOY / "launch_participation.json")["decision"]
    assert decision["work_order"] == WORK_ORDER
    assert decision["decided_by"] == "founder"


def test_exactly_one_market_joined_and_none_left():
    """A launch record that quietly carried a second market is the worst defect."""
    decision = _load(DEPLOY / "launch_participation.json")["decision"]
    before = set(decision["supersedes"]["founder_authorized"])
    after = set(live_pin()["participating_markets"])
    assert sorted(after - before) == [MARKET]
    assert sorted(before - after) == []
    assert len(before) == BEFORE["markets"] and len(after) == AFTER["markets"]


def test_detroit_fort_wayne_and_lexington_are_still_out():
    from scripts.pettripfinder import launch_participation as LP
    assert LP.launch_status("detroit-ann-arbor-mi") != LP.FOUNDER_AUTHORIZED_FOR_LAUNCH
    for unregistered in ("fort-wayne-in", "lexington-ky"):
        assert not (PACKAGE / "markets" / ("%s.json" % unregistered)).is_file()
        assert unregistered not in live_pin()["participating_markets"]


# --------------------------------------------------------------------------
# The delta: what a launch can silently take away.
# --------------------------------------------------------------------------

def test_every_previously_live_market_moved_by_exactly_zero():
    counts = record()["profile_counts"]
    was = _load(DEPLOY / "deployment_records"
                / ("ptf-deploy-cincinnati-004-%s.json" % PREVIOUS_DEPLOY))["profile_counts"]
    for market, before in sorted(was.items()):
        assert counts[market] == before, "%s moved %d -> %d" % (market, before,
                                                                counts[market])
    assert counts[MARKET] == TOLEDO["profiles"]


def test_production_grew_by_exactly_toledo():
    pin = live_pin()
    assert pin["total_profiles"] == AFTER["profiles"] == BEFORE["profiles"] + TOLEDO["profiles"]
    assert pin["sitemap_route_count"] == AFTER["routes"] == BEFORE["routes"] + TOLEDO["routes"]
    assert len(pin["participating_markets"]) == AFTER["markets"]


def test_no_route_the_previous_deploy_served_was_removed():
    live = record()["live_verification_results"]
    assert live["routes_removed_vs_previous_deploy"] == 0
    assert live["profiles_removed"] == 0
    assert live["routes_added_vs_previous_deploy"] == TOLEDO["routes"]
    assert live["previous_deploy_sitemap_read_from_its_own_address"] is True


# --------------------------------------------------------------------------
# The chain: packet, authorization, record, manifest, live.
# --------------------------------------------------------------------------

def test_the_authorization_was_consumed_in_order():
    a = auth()
    assert [h["status"] for h in a["status_history"]] == ["PREPARED", "AUTHORIZED", "DEPLOYED"]
    assert a["authorization_status"] == "DEPLOYED"
    assert a["authorized_by"] == "founder"
    assert a["work_order"] == WORK_ORDER


def test_one_digest_runs_from_authorization_to_live():
    a, r = auth(), record()
    manifest = _load(DEPLOY / "global_deployment_manifest.json")
    pin = live_pin()
    live = r["live_verification_results"]
    for doc in (a, r, manifest, pin):
        assert doc["bundle_sha256"] == BUNDLE
        assert doc["sitemap_sha256"] == SITEMAP
    assert live["live_sitemap_sha256"] == SITEMAP
    assert live["sitemap_exact_match_to_authorized"] is True


def test_the_promotion_packets_bundle_is_NOT_what_deployed():
    """The packet pins the PRE-FLIP bundle, in which Toledo contributes nothing.

    The order asked for PACKET == AUTHORIZED on bundle_sha256. That equality
    cannot hold for a launch: deploying the pre-flip bundle would change nothing,
    which is the opposite of launching. The packet value is UNTOUCHED -- it is
    still the correct digest of the artifact it describes -- and the founder was
    shown both before binding this authorization to the reassembled candidate.
    """
    packet = _load(PACKAGE / "markets" / "reports"
                   / "toledo_deployment_authorization_003_PROPOSED.json")
    assert packet["bundle_sha256"] == PRE_FLIP_BUNDLE
    assert packet["bundle_sha256"] != BUNDLE
    assert packet["toledo_is_registered_but_does_not_participate"][
        "bundle_identical_to_live"] is True, (
        "the packet described a candidate identical to the THEN-live bundle")
    assert auth()["bundle_sha256"] == BUNDLE


def test_rollback_target_is_what_production_actually_served():
    """Cincinnati's order named a rollback one deploy stale; it would have
    un-deployed Louisville."""
    a, r = auth(), record()
    assert a["rollback_target"] == PREVIOUS_DEPLOY
    assert r["rollback_target"] == PREVIOUS_DEPLOY
    assert r["previous_deployment_id"] == PREVIOUS_DEPLOY
    assert live_pin()["previous_deploy_id"] == PREVIOUS_DEPLOY


def test_the_record_is_final_and_names_its_authorization():
    r = record()
    assert r["final_status"] == "DEPLOYED"
    assert r["rollback_used"] is False
    assert r["authorization_id"] == AUTH_ID
    assert r["deployment_id"] == DEPLOY_ID
    assert r["source_commit"] == SOURCE_COMMIT


def test_source_is_back_in_sync_with_production():
    source = _load(PINS / "deployment_state.json")["source"]
    assert source["ahead_of_production"] is False
    assert source["moved_by"] is None
    assert source["bundle_sha256"] == BUNDLE


def test_the_new_authorization_is_registered_as_current_and_nothing_moved_under_it():
    reg = _load(PINS / "supersessions.json")["authorizations"]
    assert AUTH_ID in reg
    assert reg[AUTH_ID]["work_order"] == WORK_ORDER
    assert reg[AUTH_ID]["moved_by_later_work"] == {}


# --------------------------------------------------------------------------
# Live verification, and the founder's holds.
# --------------------------------------------------------------------------

def test_every_authorized_route_serves_the_authorized_bytes():
    live = record()["live_verification_results"]
    assert live["routes_fetched"] == AFTER["routes"]
    assert live["routes_http_200"] == AFTER["routes"]
    assert live["routes_byte_identical_to_authorized_bundle"] == AFTER["routes"]
    assert live["routes_non_200"] == []
    assert live["routes_mismatched"] == []
    assert live["route_sets_identical_to_authorized"] is True


def test_toledos_own_routes_are_live():
    live = record()["live_verification_results"]
    assert live["toledo_hub_200"] is True
    assert live["toledo_routes_authorized"] == TOLEDO["routes"]
    assert live["toledo_routes_live_and_identical"] == TOLEDO["routes"]
    corridors = live["toledo_corridor_routes"]
    assert len(corridors) == TOLEDO["corridors"]
    for slug, row in corridors.items():
        assert row["http"] == 200 and row["byte_identical"] is True, slug


def test_the_held_fremont_pike_pair_did_not_surface():
    """Founder ruling TOLEDO-R3 holds BOTH reads at 10667 / 10667B Fremont Pike.

    address_key collapses the building letter, so one canonical row would carry
    "no other pets" and "Dog-friendly" at once. A launch is exactly where such a
    hold leaks, so production itself is checked, not just the authority.
    """
    live = record()["live_verification_results"]
    assert live["held_pair_10667_surfaced_on"] == []
    holds = _load(PACKAGE / "toledo_oh_identity_holds_002.json")
    assert holds["holds"], "the hold record must survive the launch"
    policy = _load(PACKAGE / ("hotel_policy_facts_%s.json" % MARKET))
    assert len(policy["hotels"]) == TOLEDO["profiles"]


def test_fort_wayne_and_lexington_serve_nothing():
    live = record()["live_verification_results"]
    assert live["fort_wayne_or_lexington_routes_live"] == []


def test_the_composed_bundle_had_no_structural_defect():
    live = record()["live_verification_results"]
    for gate in ("broken_links", "collisions", "global_shadowing",
                 "canonical_violations"):
        assert live[gate] == 0, gate
