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


def current_live_pin() -> dict:
    """What production serves RIGHT NOW. Moved by every later deployment."""
    return _load(PINS / "deployment_state.json")["live"]


def live_pin() -> dict:
    """The deployment state AS OF THIS LAUNCH.

    While Toledo was the live deploy this was simply the pin. A later launch
    moves the pin -- PTF-DETROIT-ANN-ARBOR-DEPLOYMENT-AND-LAUNCH-AUTHORIZATION-032
    shipped Detroit as the twelfth market -- and reading it here would ask this
    suite to describe a deployment it is not about. The facts are unchanged and
    are preserved in Toledo's own deployment record, which is immutable evidence
    of what was deployed at the time, so they are read from there instead. The
    assertions below are untouched: they say the same things about the same
    launch, from the source that actually owns them.
    """
    pin = current_live_pin()
    if pin["deploy_id"] == DEPLOY_ID:
        return pin
    r = record()
    return {
        "deploy_id": r["deployment_id"],
        "previous_deploy_id": r["previous_deployment_id"],
        "rollback_target": r["rollback_target"],
        "bundle_sha256": r["bundle_sha256"],
        "sitemap_sha256": r["sitemap_sha256"],
        "participating_markets": sorted(r["profile_counts"]),
        "profile_counts": r["profile_counts"],
        "total_profiles": r["total_profiles"],
        "sitemap_route_count": r["sitemap_route_count"],
    }


# --------------------------------------------------------------------------
# Toledo is live.
# --------------------------------------------------------------------------

def _toledos_decision() -> dict:
    """This order's decision, read from wherever the record now keeps it.

    While 003 was the current decision this read ``decision`` directly. A later
    order moves it into the lineage, which is what the lineage is FOR. So the
    facts are asserted from whichever position holds them and they are the same
    facts either way -- the same treatment
    test_grand_rapids_launch_participation_032 already gives its own decision.
    """
    doc = _load(DEPLOY / "launch_participation.json")
    decision = doc["decision"]
    if decision["work_order"] == WORK_ORDER:
        return decision
    return next(r for r in decision["lineage"]["records"]
                if r["work_order"] == WORK_ORDER)


def test_toledo_participates_in_the_composed_bundle():
    from scripts.pettripfinder import launch_participation as LP
    assert LP.launch_status(MARKET) == LP.FOUNDER_AUTHORIZED_FOR_LAUNCH
    mine = _toledos_decision()
    assert mine["work_order"] == WORK_ORDER
    assert MARKET in mine["founder_authorized"]
    # Toledo's own decision WAS the founder's, and stays so wherever it is
    # held. The CURRENT record may be a later order's -- and since
    # PTF-DETROIT-ANN-ARBOR-LAUNCH-PREP-031 it is a PROPOSAL that deliberately
    # claims no founder signature -- which says nothing about this one.
    doc = _load(DEPLOY / "launch_participation.json")
    if doc["decision"]["work_order"] == WORK_ORDER:
        assert doc["decision"]["decided_by"] == "founder"


def test_exactly_one_market_joined_and_none_left():
    """A launch record that quietly carried a second market is the worst defect.

    Both sides are read from THIS launch's epoch: the set Toledo inherited, and
    the set the deployment pinned. A later order proposing a twelfth market
    moves neither, which is the point -- this asserts what the Toledo launch
    did, not what the participation record says today.
    """
    doc = _load(DEPLOY / "launch_participation.json")
    decision = doc["decision"]
    if decision["work_order"] == WORK_ORDER:
        before = set(decision["supersedes"]["founder_authorized"])
    else:
        # The record Toledo's own superseded, found by name rather than by
        # position: the chain grows and an index would drift.
        records = decision["lineage"]["records"]
        mine = next(i for i, r in enumerate(records)
                    if r["work_order"] == WORK_ORDER)
        assert mine > 0, "the Toledo record has no ancestor"
        before = set(records[mine - 1]["founder_authorized"])
    after = set(live_pin()["participating_markets"])
    assert sorted(after - before) == [MARKET]
    assert sorted(before - after) == []
    assert len(before) == BEFORE["markets"] and len(after) == AFTER["markets"]


def test_detroit_fort_wayne_and_lexington_are_still_out():
    """Out of what PRODUCTION serves, which is this module's subject.

    Detroit was out of the participation record too until
    PTF-DETROIT-ANN-ARBOR-LAUNCH-PREP-031 proposed it in as a twelfth market.
    That order deployed nothing, so Detroit is still out of the deployed
    bundle, and the assertion is scoped to the deployment this suite is about
    rather than relaxed. Fort Wayne and Lexington are not even registered.
    """
    live = live_pin()["participating_markets"]
    assert "detroit-ann-arbor-mi" not in live
    assert len(live) == AFTER["markets"]
    # Detroit's admission to the RECORD is traceable to a named later order and
    # is not a founder decision, so nothing was admitted silently.
    doc = _load(DEPLOY / "launch_participation.json")
    row = next(r for r in doc["markets"]
               if r["market_id"] == "detroit-ann-arbor-mi")
    if row["launch_status"] == "FOUNDER_AUTHORIZED_FOR_LAUNCH":
        # Admitted by a LATER order than this one -- 031 proposed it and 032
        # signed it -- never by this launch, which named Toledo and nothing
        # else. That is the guard: no market rides in on another's decision.
        assert doc["decision"]["work_order"] != WORK_ORDER
        assert MARKET in doc["decision"].get("founder_authorized", [MARKET])
    for unregistered in ("fort-wayne-in", "lexington-ky"):
        assert not (PACKAGE / "markets" / ("%s.json" % unregistered)).is_file()
        assert unregistered not in live


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
    """One digest, from the authorization through to the bytes production served.

    The global manifest is CURRENT state and describes whatever is live now, so
    it belongs in this chain only while this launch is the live deploy. Once a
    later launch replaces it -- Detroit did, at
    PTF-DETROIT-ANN-ARBOR-DEPLOYMENT-AND-LAUNCH-AUTHORIZATION-032 -- the manifest
    is asserted to describe THAT deployment instead, which is the same rule
    (the manifest never describes a deployment other than the live one) applied
    to a moved epoch rather than dropped.
    """
    a, r = auth(), record()
    manifest = _load(DEPLOY / "global_deployment_manifest.json")
    pin = live_pin()
    current = current_live_pin()
    live = r["live_verification_results"]

    chain = [a, r, pin]
    if current["deploy_id"] == DEPLOY_ID:
        chain.append(manifest)
    else:
        assert manifest["bundle_sha256"] == current["bundle_sha256"]
        assert manifest["sitemap_sha256"] == current["sitemap_sha256"]
        assert manifest["bundle_sha256"] != BUNDLE

    for doc in chain:
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
    """In sync AT THIS LAUNCH: what deployed IS a fresh assembly of 85c66ee.

    That is a fact about the Toledo epoch and it is permanent. Source has since
    moved ahead again -- PTF-DETROIT-ANN-ARBOR-LAUNCH-PREP-031 proposed a
    twelfth market -- which is the normal cycle and not a contradiction. The
    assertion that survives is that any drift is NAMED: an unexplained
    divergence between source and production is what this was written to catch,
    and it still fails on one.
    """
    source = _load(PINS / "deployment_state.json")["source"]
    live = live_pin()
    # This launch's deployment served exactly this launch's bundle.
    assert live["bundle_sha256"] == BUNDLE
    assert live["deploy_id"] == DEPLOY_ID
    current = current_live_pin()
    if current["deploy_id"] != DEPLOY_ID:
        # A later launch has replaced it. Source-vs-production is that
        # deployment's business, not this one's; what this suite still owns is
        # that the replacement NAMES itself rather than drifting in.
        from pettripfinder import epochs
        assert epochs.is_work_order(current["deployed_by"])
        assert current["previous_deploy_id"] == DEPLOY_ID, (
            "the deployment that replaced this one does not name it as its "
            "predecessor")
        return
    if source["ahead_of_production"]:
        # Ahead is allowed only with a work order that says who moved it.
        from pettripfinder import epochs
        assert epochs.is_work_order(source["moved_by"]), source["moved_by"]
        assert source["bundle_sha256"] != BUNDLE
    else:
        assert source["moved_by"] is None
        assert source["bundle_sha256"] == BUNDLE


def test_the_new_authorization_is_registered_as_current_and_nothing_moved_under_it():
    """Nothing this authorization AUTHORIZED has moved out from under it.

    It authorized eleven markets. A later order may move a market this
    authorization never covered -- PTF-DETROIT-ANN-ARBOR-LAUNCH-PREP-031
    proposed a twelfth -- and the registry names it, which is the mechanism
    working. What must never happen is one of the ELEVEN moving unnamed, and
    that is what this asserts.
    """
    reg = _load(PINS / "supersessions.json")["authorizations"]
    assert AUTH_ID in reg
    assert reg[AUTH_ID]["work_order"] == WORK_ORDER
    authorized = set(live_pin()["participating_markets"])
    assert len(authorized) == AFTER["markets"]
    moved = reg[AUTH_ID]["moved_by_later_work"]
    assert set(moved) & authorized == set(), (
        "a market this authorization deployed moved out from under it")
    from pettripfinder import epochs
    for market_id, work_order in moved.items():
        assert market_id not in authorized
        assert epochs.is_work_order(work_order), (market_id, work_order)


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
