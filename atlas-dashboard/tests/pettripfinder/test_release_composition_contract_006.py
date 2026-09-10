"""PTF-NASHVILLE-POST-LAUNCH-TEST-HARNESS-CLEANUP-006 -- composition claims, without rendering the site.

WHY THIS MODULE EXISTS

Closing the Nashville launch cost about 61 minutes of pytest, and nearly all of
it was two modules that each RENDER THE ENTIRE THIRTEEN-MARKET SITE in a
module-scoped fixture. Most of what they then assert is not about rendered
bytes at all. "The participation set is derived rather than hand-listed" is a
statement about a derivation; "each market contributes the profile count its own
release contract states" is a statement about two committed files. Neither needs
5,506 HTML pages to have been written to disk first.

So the claims that do not need bytes are proved here, from the committed
artifacts and by EXECUTING the derivations they are about. The claims that do
need bytes stay where they were, in the full-assembly modules, and this module
does not repeat them.

WHAT THIS IS NOT

It is not a second source of truth. Every number here is read from the
participation record, the release contracts, the market registry, the committed
global manifest or the deployment records -- the same inputs the assembler
reads. Nothing is restated, and :data:`REVIEWED_MARKETS` is the one reviewed
list, imported by the heavy modules rather than copied into them, so a launch
edits it once.

WHAT STILL REQUIRES A FULL ASSEMBLY

Control files, security headers, canonical sitemap routes, route-collision and
global-shadowing gates, the live-route migration gate, and every byte-for-byte
bundle comparison. Those live in test_global_deployment_architecture_045 and
test_launch_participation_046, both of which are in the deployment_architecture
and full_regression lanes and NEITHER of which is in market_targeted -- so a
routine market launch does not select them, and an assembler or shared-schema
change still does.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.pettripfinder import global_deployment as GD
from scripts.pettripfinder import launch_participation as LP
from scripts.pettripfinder import release_index as RI
from scripts.pettripfinder.assemble_production_site import (
    market_eligibility, published_hotels, select_markets,
)
from scripts.pettripfinder.markets import load_markets, market_by_id

REPO = Path(__file__).resolve().parents[2]

#: The reviewed live market list. ONE place, imported by the heavy modules.
#: Explicit rather than derived: a test that derives both sides of its own
#: comparison asserts nothing, which is why
#: test_global_deployment_architecture_045 kept it explicit in the first place.
#: A founder launch decision moves this line and nothing else.
REVIEWED_MARKETS = (
    "cincinnati-oh", "cleveland-akron-canton-oh", "columbus-oh", "dayton-oh",
    "grand-rapids-holland-mi", "indianapolis-in", "lexington-ky", "louisville-ky",
    "milwaukee-wi", "nashville-tn", "pittsburgh-pa", "st-louis-mo", "toledo-oh",
)

#: Registered, source-ready, and deliberately not authorized.
REVIEWED_WITHHELD = ("detroit-ann-arbor-mi",)


@pytest.fixture(scope="module")
def manifest():
    return GD.load_manifest()


@pytest.fixture(scope="module")
def participation():
    return LP.load_participation()


class TestTheParticipationSetIsDerivedNotListed:
    """The claim 045 proves by rendering. It is a claim about a derivation."""

    def test_the_composed_set_is_what_the_derivation_returns(self, manifest):
        chosen, _eligibility = select_markets(None)
        assert [m.market_id for m in chosen] == \
            [row["market_id"] for row in manifest["participating_markets"]]

    def test_the_derivation_admits_exactly_the_founder_authorized_set(self):
        chosen, _ = select_markets(None)
        assert [m.market_id for m in chosen] == LP.authorized_market_ids()

    def test_a_withheld_market_is_source_ready_and_still_excluded(self):
        """Readiness is necessary and not sufficient, proved without a build."""
        for market_id in REVIEWED_WITHHELD:
            row = market_eligibility(market_by_id(load_markets(), market_id))
            assert row["assemblable"] is True, market_id
            assert row["participates"] is False, market_id
            assert LP.launch_status(market_id) == \
                LP.SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH
            assert market_id not in [m.market_id for m in select_markets(None)[0]]

    def test_every_registered_market_has_an_explicit_status(self):
        registered = [m.market_id for m in load_markets()]
        rows = {mid: market_eligibility(market_by_id(load_markets(), mid))["assemblable"]
                for mid in registered}
        assert LP.verify_participation(registered, rows) == \
            {"unlisted": [], "unregistered": [], "source_disagreement": []}


class TestTheReviewedListAgreesWithEveryDerivedOne:
    """The single edit point a launch touches, held to four independent sources."""

    def test_the_reviewed_list_is_the_authorized_set(self):
        assert sorted(REVIEWED_MARKETS) == LP.authorized_market_ids()

    def test_the_reviewed_list_is_what_the_manifest_composed(self, manifest):
        assert sorted(REVIEWED_MARKETS) == \
            sorted(row["market_id"] for row in manifest["participating_markets"])

    def test_the_reviewed_list_is_what_production_serves(self):
        live = RI.current_verified_live()
        assert sorted(REVIEWED_MARKETS) == sorted(live.participating_markets)
        assert not live.problems

    def test_the_withheld_list_is_exactly_the_registered_remainder(self, manifest):
        registered = {m.market_id for m in load_markets()}
        assert registered - set(REVIEWED_MARKETS) == set(REVIEWED_WITHHELD)
        assert sorted(row["market_id"] for row in manifest["excluded_markets"]) == \
            sorted(REVIEWED_WITHHELD)


class TestEachMarketContributesWhatItsContractStates:
    """045 proves this by counting rendered profile directories. The same claim
    is two committed files: the market's published authority and its release
    contract. A rendered count that disagreed with either would be an assembler
    defect, which is what the full-assembly module is still for."""

    @pytest.mark.parametrize("market_id", REVIEWED_MARKETS)
    def test_the_manifest_count_is_the_published_count(self, market_id, manifest):
        row = next(r for r in manifest["participating_markets"]
                   if r["market_id"] == market_id)
        market = market_by_id(load_markets(), market_id)
        assert row["published_profiles"] == len(published_hotels(market))

    @pytest.mark.parametrize("market_id", REVIEWED_MARKETS)
    def test_the_contract_agrees_with_the_source(self, market_id, manifest):
        row = next(r for r in manifest["participating_markets"]
                   if r["market_id"] == market_id)
        assert row["contract_disagreements"] == []
        contract = json.loads(
            (REPO / row["release_contract"]).read_text(encoding="utf-8-sig"))
        assert contract["market_id"] == market_id

    def test_the_totals_are_the_sum_and_nothing_else(self, manifest):
        rows = manifest["participating_markets"]
        assert manifest["total_published_profiles"] == \
            sum(r["published_profiles"] for r in rows)
        assert len(rows) == len(REVIEWED_MARKETS)


class TestTheManifestPinsTheRecordItWasComposedUnder:

    def test_it_names_the_participation_record_and_its_hash(self, manifest):
        pin = manifest["launch_participation"]
        assert pin["source"] == "deploy/netlify/launch_participation.json"
        assert pin["sha256"] == LP.participation_sha256()
        assert pin["founder_authorized"] == LP.authorized_market_ids()

    def test_a_changed_record_invalidates_it(self, manifest):
        """The pin is load-bearing, proved by breaking it in memory only."""
        doc = dict(manifest)
        doc["launch_participation"] = dict(doc["launch_participation"], sha256="0" * 64)
        assert any("launch_participation.json has changed" in p
                   for p in GD.verify_manifest(doc))

    def test_the_decision_chain_is_reachable_and_ends_before_the_current_record(self):
        chain = LP.decision_chain()
        shas = [r["sha256"] for r in chain["records"]]
        assert LP.participation_sha256() not in shas
        assert chain["supersedes"]["sha256"] == shas[-1]
        assert LP.decision_problems(LP.load_participation()) == []


class TestTheLiveReleaseIsInternallyConsistent:
    """The deployment membership, rollback parent and release digests, read from
    the committed records rather than rebuilt."""

    def test_the_live_index_reports_no_problem(self):
        assert list(RI.current_verified_live().problems) == []

    def test_the_counts_are_the_ones_production_serves(self):
        live = RI.current_verified_live()
        assert (len(live.participating_markets), live.total_profiles,
                live.sitemap_route_count) == (13, 902, 1078)

    def test_the_rollback_parent_is_a_deployed_record_of_its_own(self):
        live = RI.current_verified_live()
        parent = json.loads(
            (REPO / "deploy" / "netlify" / "deployment_records" / live.rollback_record)
            .read_text(encoding="utf-8-sig"))
        assert parent["deployment_id"] == live.rollback_target
        assert parent["final_status"] == "DEPLOYED"
        assert set(parent["participating_markets"]) < set(live.participating_markets)

    def test_the_manifest_and_the_live_record_name_one_bundle(self, manifest):
        live = RI.current_verified_live()
        assert manifest["bundle_sha256"] == live.bundle_sha256
        assert manifest["total_published_profiles"] == live.total_profiles
