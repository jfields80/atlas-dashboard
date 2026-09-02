# -*- coding: utf-8 -*-
"""PTF-GRAND-RAPIDS-LAUNCH-PARTICIPATION-032 -- the ninth market joins the candidate.

THREE THINGS HAD TO BE TRUE BEFORE GRAND RAPIDS COULD ASSEMBLE, and two of them
were silently false until this order went looking.

THE PARTITION LOOKUP NEVER MATCHED. ``_partition_path`` builds a glob by
stripping the market id's last segment: "grand-rapids-holland-mi" becomes
"grand-rapids-holland_final_partition_*", and no file matches because the
filenames use underscores. It returned None, ``final_partition_present`` read
False, and the market was simply not assemblable -- not refused, not reported,
just absent from every bundle. The explicit table already existed for
louisville-ky and st-louis-mo for this exact reason; Grand Rapids now has an
entry, and a test proves the artifact is FOUND rather than trusting the glob.

THE PARTITION IT WOULD HAVE FOUND WAS STALE. The committed 163-row partition
predates every founder signature and still carried 42 rows as
AWAITING_FOUNDER_DECISION -- 40 of which have since been decided. Pinning it
would have assembled a market whose own partition says its published hotels are
waiting to be looked at. So the table names 002, rebuilt from the signed
authority, and the tests pin BOTH halves: the resolved rows are terminal, and
the rows nobody has ruled on keep the state they had.

AND ONLY THEN THE FOUNDER'S ROW. Grand Rapids was NOT_SOURCE_READY because the
assembler genuinely could not assemble it; with the first two fixed it is
source-ready, and the row records the launch decision.

THE CANDIDATE ADDS AND CHANGES NOTHING ELSE. 3263 files byte-identical, 254
added and every one Grand Rapids, four global surfaces changed, zero removed --
and both HTML changes are pure insertions with zero characters deleted.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder import launch_participation as LP
from scripts.pettripfinder import release_contracts as RC
from scripts.pettripfinder.assemble_production_site import (
    _partition_path, market_eligibility)
from scripts.pettripfinder.markets import load_markets, market_by_id

PKG = REPO / "launch_packages" / "pettripfinder"
DEPLOY = REPO / "deploy" / "netlify"
MARKET = "grand-rapids-holland-mi"
CANDIDATE = DEPLOY / "global_deployment_manifest_candidate_032.json"
PARTITION = PKG / "grand_rapids_holland_mi_final_partition_002.json"

CANDIDATE_BUNDLE = (
    "5fc4ae2c555d83a9986d3d071df1013cc1a9f2fcff5d509d26c49278c84defb6")
CANDIDATE_SITEMAP = (
    "b48aab5fd46232fd03cbdd2e764d6362214938697e56a3d32b2a499b58432a0b")
#: The eight-market bundle live BEFORE this candidate deployed -- the one
#: PTF-GRAND-RAPIDS-DEPLOY-AUTHORIZATION-034 named as its rollback target.
#: It was called LIVE_BUNDLE while it was live; the candidate has since
#: replaced it in production, and a constant that says "live" about a bundle
#: that no longer is would mislead the next reader of this file.
REPLACED_BUNDLE = (
    "e9998c51d13559333ef9bd63f287e8858b73eb0011401a9606a58871f6ba74cc")


def _load(path):
    assert path.is_file(), "%s is missing" % path.name
    return json.loads(path.read_text(encoding="utf-8-sig"))


@pytest.fixture(scope="module")
def partition():
    return _load(PARTITION)


@pytest.fixture(scope="module")
def candidate():
    return _load(CANDIDATE)


# --------------------------------------------------------------------------- #
# Step 1 -- the partition lookup
# --------------------------------------------------------------------------- #

def test_the_partition_artifact_is_found_at_all():
    """The regression Step 1 asks for. It returned None before this order."""
    found = _partition_path(MARKET)
    assert found is not None, (
        "the glob builds 'grand-rapids-holland_final_partition_*' from the "
        "market id and the files use underscores, so only the explicit table "
        "can reach this market")
    assert found.name == "grand_rapids_holland_mi_final_partition_002.json"
    assert found.is_file()


def test_the_lookup_names_the_signed_partition_not_the_stale_one():
    """Sorted-order would take 001 -- the partition from before any founder
    signed. St. Louis's entry exists for the same reason and says so."""
    assert _partition_path(MARKET).name.endswith("_002.json")
    stale = PKG / "grand_rapids_holland_mi_final_partition_001.json"
    assert stale.is_file(), "the superseded partition is kept, not deleted"
    assert _partition_path(MARKET) != stale


def test_every_other_markets_lookup_is_unchanged():
    for market_id, expected in (
            ("columbus-oh", "columbus_final_partition_001.json"),
            ("cleveland-akron-canton-oh", "cleveland_final_partition_002.json"),
            ("dayton-oh", "dayton_final_partition_001.json"),
            ("louisville-ky", "louisville_final_partition_001.json"),
            ("st-louis-mo", "st_louis_mo_final_partition_007.json")):
        found = _partition_path(market_id)
        assert found is not None and found.name == expected, market_id


def test_the_market_is_assemblable_and_says_why_on_every_condition():
    row = market_eligibility(market_by_id(load_markets(), MARKET))
    assert row["conditions"] == {
        "census_present": True, "final_partition_present": True,
        "policy_authority_present": True, "meets_minimum_published": True}
    assert row["assemblable"] is True
    assert row["published_count"] == 43


# --------------------------------------------------------------------------- #
# Step 2 -- the regenerated partition
# --------------------------------------------------------------------------- #

def test_the_partition_agrees_with_the_census_and_the_authority(partition):
    census = _load(PKG / "identity_census" / ("%s.json" % MARKET))
    assert partition["count"] == len(census["hotels"]) == 163
    counts = partition["final_state_counts"]
    assert counts["PUBLISHED_PET_FRIENDLY"] == 43
    assert counts["VERIFIED_NO_PETS"] == 20
    assert counts["PUBLISHED_PET_FRIENDLY"] + counts["VERIFIED_NO_PETS"] == 63
    derived = RC.derive_authority(MARKET)
    assert counts["PUBLISHED_PET_FRIENDLY"] == derived.published_hotel_profiles
    assert counts["VERIFIED_NO_PETS"] == derived.verified_no_pets
    assert sum(counts.values()) == 163


def test_no_resolved_row_is_left_awaiting_a_founder_decision(partition):
    """The defect that made the stale partition unusable: 40 rows the founder
    had decided still said they were waiting."""
    from scripts.pettripfinder import (
        grand_rapids_holland_final_partition_032 as P)
    ruled = P.effective_authority()
    assert len(ruled) == 63
    for item in partition["items"]:
        if item["identity_key"] in ruled:
            assert item["final_state"] == ruled[item["identity_key"]]
            assert item["final_state"] != "AWAITING_FOUNDER_DECISION"
            assert item["resolved"] is True


def test_the_two_rows_that_still_await_a_decision_genuinely_do(partition):
    awaiting = [i["identity_key"] for i in partition["items"]
                if i["final_state"] == "AWAITING_FOUNDER_DECISION"]
    assert sorted(awaiting) == ["avid hotel zeeland",
                                "comfort suites grandville grand rapids sw"]
    # The first was WITHDRAWN by the founder in 022 "for now", which is a
    # decision still owed; the second is one half of an identity pair 019
    # holds open.
    from scripts.pettripfinder import (
        grand_rapids_holland_final_partition_032 as P)
    assert not (set(awaiting) & set(P.effective_authority()))


def test_the_unresolved_rows_kept_the_state_they_had(partition):
    """This pass re-adjudicates nothing. A row nobody ruled on since 009 has a
    blocker that has not changed, and inventing a fresher state for it would be
    writing a finding no work order made."""
    from scripts.pettripfinder import (
        grand_rapids_holland_final_partition_032 as P)
    prior = {i["identity_key"]: i["final_state"] for i in
             _load(PKG / "grand_rapids_holland_mi_final_partition_001.json")["items"]}
    ruled = P.effective_authority()
    unresolved = [i for i in partition["items"]
                  if i["identity_key"] not in ruled]
    assert len(unresolved) == 100
    for item in unresolved:
        assert item["final_state"] == prior[item["identity_key"]]
        assert item["resolved"] is False


def test_the_partition_names_what_it_supersedes(partition):
    assert partition["supersedes"]["path"].endswith(
        "grand_rapids_holland_mi_final_partition_001.json")
    assert "predates every founder signature" in partition["supersedes"]["why"]


# --------------------------------------------------------------------------- #
# Step 3 -- participation
# --------------------------------------------------------------------------- #

def test_grand_rapids_is_authorized_and_nothing_else_moved():
    assert LP.launch_status(MARKET) == LP.FOUNDER_AUTHORIZED_FOR_LAUNCH
    assert LP.authorized_market_ids() == sorted([
        "cleveland-akron-canton-oh", "columbus-oh", "dayton-oh",
        "grand-rapids-holland-mi", "indianapolis-in", "louisville-ky",
        "milwaukee-wi", "pittsburgh-pa", "st-louis-mo"])
    # Neither is authorized. Cincinnati assembles cleanly since
    # PTF-CINCINNATI-HARDENED-SYNC-002, Detroit since
    # PTF-DETROIT-ANN-ARBOR-TROY-IDENTITY-AND-BUNDLE-030 (carried here by
    # PTF-LINEAGE-CONSOLIDATION-008), and both are withheld by the record --
    # which is the state SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH
    # exists to express. What this test guards is that neither is in the
    # authorized set, and neither is.
    assert LP.launch_status("detroit-ann-arbor-mi") == (
        LP.SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH)
    assert LP.launch_status("cincinnati-oh") == (
        LP.SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH)
    for mid in ("cincinnati-oh", "detroit-ann-arbor-mi"):
        assert mid not in LP.authorized_market_ids()


def test_every_registered_market_still_carries_an_explicit_row():
    registered = [m.market_id for m in load_markets()]
    checks = LP.verify_participation(
        registered,
        {mid: market_eligibility(market_by_id(load_markets(), mid))["assemblable"]
         for mid in registered})
    assert checks == {"unlisted": [], "unregistered": [],
                      "source_disagreement": []}


def test_the_decision_names_this_order_and_preserves_its_predecessor():
    doc = LP.load_participation()
    decision = doc["decision"]
    assert decision["work_order"] == "PTF-GRAND-RAPIDS-LAUNCH-PARTICIPATION-032"
    assert decision["decided_by"] == "founder"
    assert decision["supersedes"]["work_order"] == \
        "PTF-INDIANAPOLIS-LAUNCH-PARTICIPATION-019"
    # The set it inherited: the eight live before Grand Rapids.
    assert "grand-rapids-holland-mi" not in decision["supersedes"]["founder_authorized"]
    assert len(decision["supersedes"]["founder_authorized"]) == 8


# --------------------------------------------------------------------------- #
# Steps 4-6 -- the candidate
# --------------------------------------------------------------------------- #

def test_the_candidate_is_nine_markets_and_560_profiles(candidate):
    assert len(candidate["participating_markets"]) == 9
    assert candidate["total_published_profiles"] == 560
    assert candidate["sitemap_route_count"] == 688
    by_market = {r["market_id"]: r["published_profiles"]
                 for r in candidate["participating_markets"]}
    assert by_market["grand-rapids-holland-mi"] == 43
    assert by_market["indianapolis-in"] == 56
    assert sum(by_market.values()) == 560


def test_every_prior_live_market_is_still_present_at_its_own_count(candidate):
    by_market = {r["market_id"]: r["published_profiles"]
                 for r in candidate["participating_markets"]}
    for mid, count in (("cleveland-akron-canton-oh", 99), ("columbus-oh", 88),
                       ("dayton-oh", 47), ("indianapolis-in", 56),
                       ("louisville-ky", 46), ("milwaukee-wi", 73),
                       ("pittsburgh-pa", 26), ("st-louis-mo", 82)):
        assert by_market[mid] == count, mid


def test_the_candidate_changes_no_prior_market_byte(candidate):
    """The measured diff against the live 8-market bundle."""
    p = candidate["baseline_preservation"]
    assert p["files_byte_identical"] == 3263
    assert p["files_added"] == 254
    assert p["files_changed"] == 4
    assert p["files_removed"] == 0
    assert p["prior_sitemap_routes_lost"] == 0
    assert p["unexpected_prior_market_change"] is False
    assert "all 254 are Grand Rapids" in p["added_attribution"]
    assert "PURE INSERTIONS" in p["changed_attribution"]


def test_the_candidate_is_clean_on_every_content_measure(candidate):
    assert candidate["all_required_gates_pass"] is True
    for market in candidate["participating_markets"]:
        assert market["contract_disagreements"] == [], market["market_id"]


def test_the_candidate_pins_its_own_hashes_and_the_record_it_used(candidate):
    assert candidate["bundle_sha256"] == CANDIDATE_BUNDLE
    assert candidate["sitemap_sha256"] == CANDIDATE_SITEMAP
    assert candidate["bundle_sha256"] != REPLACED_BUNDLE
    # PTF-CINCINNATI-HARDENED-SYNC-002 lapsed the pin again by correcting Cincinnati's source-readiness row,
    # so the candidate pins the record AS IT WAS when 032 composed it. That is
    # what a pin is for: it must not follow the file. The rollback target and
    # both bundle hashes below are unaffected.
    assert candidate["launch_participation"]["sha256"] != LP.participation_sha256()
    assert candidate["launch_participation"]["source"] == (
        "deploy/netlify/launch_participation.json")
    assert candidate["source_commit"]


def test_the_rollback_target_is_the_deployment_this_candidate_replaced(candidate):
    """It WAS the live deploy when the candidate was composed, and it is what
    a rollback returns to now that the candidate has been deployed. Both
    readings are the same fact about the same deployment id, which is why
    this test does not need to move when production does."""
    rollback = candidate["rollback_target"]
    assert rollback["deployment_id"] == "6a9102c07ae3a341194c6f4c"
    assert rollback["bundle_sha256"] == REPLACED_BUNDLE
    assert rollback["markets"] == 8
    assert rollback["published_profiles"] == 517
    assert (REPO / rollback["record"]).is_file()


def test_the_candidate_authorizes_nothing(candidate):
    assert candidate["deployment_authorized"] is False
    assert "deployment_authorization" not in candidate
    note = candidate["deployment_authorization_note"]
    assert "none is created here" in note
    assert "ptf-auth-020" in note and "deliberately not reused" in note


def test_the_candidate_never_edited_the_committed_manifest():
    """The candidate was written as a NEW file: 032 did not rewrite the record
    of a deployment that had already happened to describe one that had not.

    The committed manifest has since been promoted to this same bundle, but by
    the DEPLOY order and not by 032 -- and the two documents stay
    distinguishable, because only the deployed one names the authorization
    that put it live. That is the fact worth asserting; "the committed
    manifest still describes the eight-market bundle" was only ever true
    between composing the candidate and deploying it.
    """
    live = _load(DEPLOY / "global_deployment_manifest.json")
    candidate = _load(CANDIDATE)
    assert live is not candidate
    assert "deployment_authorization" not in candidate
    assert live.get("deployment_authorization")
    assert live["deployment_authorized"] is True
    # The candidate is 032's own committed artifact and never moves. The
    # committed manifest has since described three LATER deploys (015's
    # eef57e2b, then PTF-CLEVELAND-AKRON-CANTON-DEPLOYMENT-AUTHORIZATION-006's
    # b0eedd71, then PTF-DAYTON-OH-DEPLOYMENT-AUTHORIZATION-003's de669c40,
    # live as 6a982a1f) -- a record of the CURRENT deploy, not of this order's.
    assert candidate["bundle_sha256"] == CANDIDATE_BUNDLE
    assert live["bundle_sha256"] == (
        "de669c40d8118a9293798ae1e5ad10ab8219c66798d002d6bf2a12cae504e374")
    assert CANDIDATE.name != "global_deployment_manifest.json"
