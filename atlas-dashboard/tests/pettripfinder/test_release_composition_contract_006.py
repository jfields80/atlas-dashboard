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
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts.pettripfinder import global_deployment as GD
from scripts.pettripfinder import launch_participation as LP
from scripts.pettripfinder import release_index as RI
from scripts.pettripfinder.assemble_production_site import (
    market_eligibility, published_hotels, select_markets,
)
from scripts.pettripfinder.markets import load_markets, market_by_id
from pettripfinder.market_state import live as _live_pin

REPO = Path(__file__).resolve().parents[2]

#: The reviewed live market list. ONE place, imported by the heavy modules.
#:
#: PTF-PARTICIPATION-GUARD-REPAIR-001 made this a READ of the deployment pin.
#: It was a hand-written tuple of thirteen markets, introduced at 2d48e15b and
#: last touched by the Charlotte registration (7a41d27e) -- which added
#: charlotte-nc to REVIEWED_WITHHELD below and did not move this line. Charlotte
#: then went live, and so did eighteen markets after it, and nobody moved it for
#: any of them. A list that names thirteen markets while thirty-two are live
#: does not protect the participation contract: it just fails, and a guard that
#: always fails is read as noise. That is exactly what happened -- the Fort
#: Lauderdale deployment recorded these failures as PRE-EXISTING and shipped
#: past them, so the participation record went nineteen launches with no
#: effective test guard.
#:
#: The old comment argued explicit-over-derived, because a test that derives
#: BOTH sides of its own comparison asserts nothing. That argument is kept and
#: satisfied: ``pins/deployment_state.json`` is ONE document, written by the
#: work order that deploys and never computed from the files it describes, and
#: the class below holds it to FOUR independent others -- the participation
#: record, the composed manifest, the deployed record behind
#: ``RI.current_verified_live``, and the market registry. A market that reached
#: the pin without a founder authorization still fails, which is the contract
#: this module exists to protect. This is the doctrine
#: ``pettripfinder.market_state`` already states for every other current
#: number: a number dozens of files restate is not a pin, it is a tax on every
#: future market.
REVIEWED_MARKETS = _live_pin().participating_markets

#: Registered, source-ready, and deliberately NOT authorized.
#:
#: Still EXPLICIT, on purpose. This is the founder judgement rather than an
#: observation, and it is the one line a launch must move by hand: a market
#: registers INTO this tuple and leaves it when the founder authorizes it. That
#: keeps a human review point exactly where the decision is, while the live list
#: above -- which is an observation, not a judgement -- stops being a tax.
#: charlotte-nc left here when it went live (deploy 393cbffe); Detroit has
#: carried the withheld role alone since.
REVIEWED_WITHHELD = ("detroit-ann-arbor-mi",)

#: The thirteen-market tuple this order replaced, kept named so nobody restores
#: it and so ``test_the_stale_pin_this_order_replaced_is_dead`` can prove it is
#: no longer a description of anything.
SUPERSEDED_THIRTEEN = (
    "cincinnati-oh", "cleveland-akron-canton-oh", "columbus-oh", "dayton-oh",
    "grand-rapids-holland-mi", "indianapolis-in", "lexington-ky", "louisville-ky",
    "milwaukee-wi", "nashville-tn", "pittsburgh-pa", "st-louis-mo", "toledo-oh",
)


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
        # The manifest is a HISTORICAL artifact, composed by the last deploy. It
        # can only name markets that existed then, so a market registered since
        # is absent from BOTH its lists. That absence is a fact about deploy
        # order and not a review decision, which is why the comparison is scoped
        # to what the manifest knew rather than relaxed.
        known = {row["market_id"] for row in manifest["participating_markets"]} | \
                {row["market_id"] for row in manifest["excluded_markets"]}
        assert sorted(row["market_id"] for row in manifest["excluded_markets"]) == \
            sorted(set(REVIEWED_WITHHELD) & known)
        # And a withheld market the manifest never knew must still be withheld
        # and must serve nothing, or its absence would be hiding a live market.
        for market_id in sorted(set(REVIEWED_WITHHELD) - known):
            assert LP.launch_status(market_id) == \
                LP.SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH, market_id
            assert market_id not in RI.current_verified_live().participating_markets


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
        # The manifest pins the record it was COMPOSED under. Registering a
        # market REISSUES that record -- the lapsed-pin doctrine conftest
        # states at length -- so the pin equals the current record until a
        # registration lands and is an ANCESTOR of it afterwards. Either is
        # legal; a sha that is neither would mean the manifest was composed
        # under a record no longer in this document's own lineage.
        ancestors = [r["sha256"] for r in LP.decision_chain()["records"]]
        assert pin["sha256"] in [LP.participation_sha256()] + ancestors
        # The authorized set, though, may NOT drift: a registration adds a
        # withheld market and moves no lever.
        assert pin["founder_authorized"] == LP.authorized_market_ids()

    def test_a_changed_record_invalidates_it(self, manifest):
        """The pin is load-bearing, proved by breaking it in memory only."""
        doc = dict(manifest)
        doc["launch_participation"] = dict(doc["launch_participation"], sha256="0" * 64)
        assert any("launch_participation.json has changed" in p
                   for p in GD.verify_manifest(doc))


class TestTheGuardActuallyFailsOnBadState:
    """PTF-PARTICIPATION-GUARD-REPAIR-001 -- the guard is load-bearing.

    The repair above replaced assertions that had stopped describing anything.
    A replacement is only worth having if it still REFUSES, so each case here
    builds the bad state and asserts the refusal by name.

    Every case works on an in-memory copy or a tmp_path copy. No committed
    record is written, and ``test_no_case_here_touched_a_committed_record``
    proves that at the end rather than promising it.
    """

    #: The committed records these cases copy, and their hashes going in.
    TOUCHED = ("deploy/netlify/launch_participation.json",
               "deploy/netlify/global_deployment_manifest.json",
               "tests/pettripfinder/pins/deployment_state.json")

    @staticmethod
    def _write_participation(tmp_path, doc):
        path = tmp_path / "launch_participation.json"
        path.write_text(json.dumps(doc, indent=1) + "\n",
                        encoding="utf-8", newline="\n")
        return path

    def test_the_committed_manifest_is_clean_to_begin_with(self):
        """So a complaint in any case below is the injection and not the tree."""
        assert GD.verify_manifest() == []
        assert RI.current_verified_live().problems == ()

    # 1 --------------------------------------------------------------------- #
    def test_an_unauthorized_market_injected_into_the_live_set_is_refused(
            self, manifest):
        """The case the whole record exists for: a market in the bundle that no
        founder admitted."""
        doc = dict(manifest)
        donor = doc["participating_markets"][0]
        doc["participating_markets"] = list(doc["participating_markets"]) + [
            dict(donor, market_id=REVIEWED_WITHHELD[0])]
        problems = GD.verify_manifest(doc)
        assert any("founder authorizes" in p for p in problems), problems
        assert any(REVIEWED_WITHHELD[0] in p for p in problems), problems

    # 2 --------------------------------------------------------------------- #
    def test_dropping_a_currently_live_market_is_refused(self, tmp_path, manifest):
        """A launch set only ever grows. Losing a live market must be refused
        by the decision chain AND by the manifest, not noticed later."""
        victim = REVIEWED_MARKETS[0]
        doc = LP.load_participation()
        demoted = dict(doc, markets=[
            dict(r, launch_status=LP.SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH)
            if r["market_id"] == victim else r for r in doc["markets"]])
        problems = LP.decision_problems(
            demoted, path=self._write_participation(tmp_path, demoted))
        assert any("drops market(s)" in p and victim in p for p in problems), problems

        dropped = dict(manifest)
        dropped["participating_markets"] = [
            r for r in dropped["participating_markets"] if r["market_id"] != victim]
        assert any("founder authorizes" in p for p in GD.verify_manifest(dropped))

    # 3 --------------------------------------------------------------------- #
    def test_a_deployed_market_with_no_participation_row_is_reported(self):
        """Silence is the failure mode: an unlisted market is not authorized,
        and the gate refuses the silence rather than defaulting."""
        served = list(RI.current_verified_live().participating_markets)
        assert set(served) <= {m.market_id for m in load_markets()}
        ghost = served + ["ghost-market-xx"]
        checks = LP.verify_participation(ghost, {m: True for m in ghost})
        assert checks["unlisted"] == ["ghost-market-xx"], checks

    # 4 --------------------------------------------------------------------- #
    def test_promoting_a_withheld_market_breaks_the_reviewed_remainder(self):
        """Detroit is withheld by DECISION, not by readiness. Flipping the
        decision must move the reviewed remainder, or the remainder assertion
        above is not doing any work."""
        doc = LP.load_participation()
        promoted = dict(doc, markets=[
            dict(r, launch_status=LP.FOUNDER_AUTHORIZED_FOR_LAUNCH)
            if r["market_id"] in REVIEWED_WITHHELD else r for r in doc["markets"]])
        registered = {m.market_id for m in load_markets()}
        for market_id in REVIEWED_WITHHELD:
            assert LP.is_founder_authorized(market_id, promoted) is True
            assert LP.is_founder_authorized(market_id) is False
        assert registered - set(LP.authorized_market_ids(promoted)) != \
            set(REVIEWED_WITHHELD)

    # 5 --------------------------------------------------------------------- #
    def test_a_decision_that_does_not_describe_current_live_is_refused(
            self, tmp_path):
        """The exact failure this order repaired, as a test: a decision whose
        inherited set names a market the record no longer authorizes."""
        doc = json.loads(json.dumps(LP.load_participation()))
        doc["decision"]["supersedes"]["founder_authorized"] = sorted(
            set(doc["decision"]["supersedes"]["founder_authorized"])
            | {"ghost-market-xx"})
        problems = LP.decision_problems(
            doc, path=self._write_participation(tmp_path, doc))
        assert any("drops market(s)" in p and "ghost-market-xx" in p
                   for p in problems), problems

    def test_the_stale_pin_this_order_replaced_is_dead(self):
        """SUPERSEDED_THIRTEEN is kept so it can be proved wrong here rather
        than quietly restored by someone reading the git history."""
        assert sorted(SUPERSEDED_THIRTEEN) != LP.authorized_market_ids()
        assert set(SUPERSEDED_THIRTEEN) < set(REVIEWED_MARKETS)
        assert sorted(SUPERSEDED_THIRTEEN) != \
            sorted(RI.current_verified_live().participating_markets)

    # 6 --------------------------------------------------------------------- #
    def test_a_live_market_whose_release_contract_is_missing_is_refused(
            self, manifest):
        doc = dict(manifest)
        victim = REVIEWED_MARKETS[0]
        doc["participating_markets"] = [
            dict(r, release_contract="deploy/netlify/release_contracts/nope.json")
            if r["market_id"] == victim else r
            for r in doc["participating_markets"]]
        problems = GD.verify_manifest(doc)
        assert any("contract missing" in p and victim in p for p in problems), problems

    # 7 --------------------------------------------------------------------- #
    def test_a_pin_that_disagrees_with_the_deployed_record_is_reported(
            self, tmp_path):
        """The resolver is fail-closed across THREE records. Corrupt the pin in
        a copy and the live state must come back carrying the problem -- a
        resolver that returned a clean state here would let a deploy be planned
        against a bundle nobody deployed."""
        shutil.copy(RI.PINS_DIR / "deployment_state.json",
                    tmp_path / "deployment_state.json")
        doc = json.loads(
            (tmp_path / "deployment_state.json").read_text(encoding="utf-8"))
        doc["live"]["bundle_sha256"] = "0" * 64
        (tmp_path / "deployment_state.json").write_text(
            json.dumps(doc, indent=1), encoding="utf-8")
        state = RI.current_verified_live(pins_dir=tmp_path)
        assert any("deployment_state pin bundle_sha256" in p
                   for p in state.problems), state.problems

    def test_no_case_here_touched_a_committed_record(self):
        """Asserted, not promised: the three records these cases copy are
        byte-identical to what git has."""
        for rel in self.TOUCHED:
            path = REPO / rel
            committed = subprocess.run(
                ["git", "show", "HEAD:atlas-dashboard/%s" % rel],
                cwd=str(REPO.parent), capture_output=True)
            assert committed.returncode == 0, rel
            assert path.read_bytes().replace(b"\r\n", b"\n") == \
                committed.stdout.replace(b"\r\n", b"\n"), rel

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
        """PTF-PARTICIPATION-GUARD-REPAIR-001: held to the pin, not to a literal.

        This read ``== (13, 902, 1078)`` -- the Nashville-era counts -- and went
        stale on the same day and for the same reason REVIEWED_MARKETS did.
        It is now the resolver against the reviewed deployment pin, which are
        two independent documents: ``current_verified_live`` reads the deployed
        RECORD, the pin is what the deploying order wrote down. A deploy that
        moved one and not the other is exactly what this should catch.
        """
        live = RI.current_verified_live()
        pin = _live_pin()
        assert (len(live.participating_markets), live.total_profiles,
                live.sitemap_route_count) == \
            (len(pin.participating_markets), pin.total_profiles,
             pin.sitemap_route_count)
        # and the counts are self-consistent: the per-market profile counts sum
        # to the total production serves.
        assert sum(live.profile_counts.values()) == live.total_profiles
        assert sorted(live.profile_counts) == sorted(live.participating_markets)

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
