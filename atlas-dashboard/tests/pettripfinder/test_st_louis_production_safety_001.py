"""PTF-ST-LOUIS-REGISTER-PUBLISH-011 -- registering St. Louis changed St. Louis.

This file used to assert the opposite of what it asserts now, and the reason is
worth keeping. PTF-ST-LOUIS-MARKET-001 section 15 required that St. Louis work
not change the live bundle, the deployment authorization, the deployment record,
the launch status of any existing market, the measurement state or the affiliate
state -- and registration is not a free act: ``markets/*.json`` IS the registry,
``launch_participation`` fails closed on any registered market with no row, and
the participation file's sha256 is pinned by the global deployment manifest AND
copied into the founder's signed authorization. So creating
``markets/st-louis-mo.json`` would have invalidated a production deployment
record, which is why the market contract sat in ``markets/pending/`` as a valid,
parseable, DELIBERATELY UNREGISTERED document.

011 is the work order that takes that step, so the registration assertions
invert. What does NOT invert is everything else: the five markets that were live
before must stay live, unchanged, and the deployment record and authorization
that describe the CURRENT production deploy must remain exactly what they were,
because a new bundle needs a NEW authorization and may not inherit one.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.pettripfinder import global_deployment as GD
from scripts.pettripfinder import launch_participation as LP
from scripts.pettripfinder import market_authority as MA
from scripts.pettripfinder import release_contracts as RC
from scripts.pettripfinder.markets.contract import load_markets, parse_market

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE = REPO_ROOT / "launch_packages" / "pettripfinder"
MARKETS_DIR = PACKAGE / "markets"
REGISTERED = MARKETS_DIR / "st-louis-mo.json"
DEPLOY = REPO_ROOT / "deploy" / "netlify"

#: The five markets live at PTF-047/012, before St. Louis joined.
LIVE_FIVE = ("cleveland-akron-canton-oh", "columbus-oh", "dayton-oh",
             "milwaukee-wi", "pittsburgh-pa")
#: The six the founder authorized at 011.
LIVE_SIX = tuple(sorted(LIVE_FIVE + ("st-louis-mo",)))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TestStLouisIsNowRegistered:
    def test_the_contract_moved_out_of_pending_into_the_registry(self):
        document = json.loads(REGISTERED.read_text(encoding="utf-8"))
        config = parse_market(document, source="st-louis-mo.json")
        assert config.market_id == "st-louis-mo"
        assert config.corridors, "a market contract with no corridor has no geography"
        assert not (MARKETS_DIR / "pending" / "st-louis-mo.json").exists()

    def test_the_pre_registration_markers_did_not_survive_registration(self):
        """``_registration_status: PENDING_REGISTRATION`` was true of the
        pending document and is false of this one. A registered contract that
        still claimed to be unregistered would be a false statement in the
        registry itself."""
        document = json.loads(REGISTERED.read_text(encoding="utf-8"))
        assert "_registration_status" not in document
        assert "_registration_note" not in document
        # The boundary note is not a registration marker -- every other market
        # carries one and it describes geography, which did not change.
        assert document["_boundary_note"]

    def test_the_registry_grew_by_exactly_one(self):
        """One market, one registration. The registry stood at 9 when St. Louis
        joined and at 10 since PTF-LOUISVILLE-PUBLICATION-008 -- each step is a
        market that arrived with its own contract, shard and participation
        row."""
        assert "st-louis-mo" in MA.registered_market_ids()
        assert len(load_markets()) == 10

    def test_the_authority_shard_exists_and_is_discoverable(self):
        assert "st-louis-mo" in MA.sharded_market_ids()
        assert len(MA.load_market_seed_rows("st-louis-mo")) == 82
        assert len(MA.load_market_exclusions("st-louis-mo")) == 37

    def test_the_generated_globals_are_regenerated_from_the_shards(self):
        """The three legacy global artifacts are GENERATED. A shard that is not
        reflected in them means a build reads one authority and a gate reads
        another."""
        assert MA.check_generated_artifacts() == []

    def test_it_is_founder_authorized_for_launch(self):
        assert LP.launch_status("st-louis-mo") == LP.FOUNDER_AUTHORIZED_FOR_LAUNCH
        assert LP.is_founder_authorized("st-louis-mo")


class TestParticipationIsTheSixMarketSet:
    def test_the_founder_authorized_set_still_holds_the_live_six(self):
        """The six St. Louis joined are all still authorized. The set has since
        grown by Louisville (PTF-LOUISVILLE-PUBLICATION-008) and Indianapolis
        (PTF-INDIANAPOLIS-LAUNCH-PARTICIPATION-019), and by nothing else -- the
        half of this assertion that protects St. Louis is that its six are
        still all there."""
        authorized = tuple(LP.authorized_market_ids())
        assert set(LIVE_SIX) <= set(authorized)
        assert set(authorized) - set(LIVE_SIX) == {"louisville-ky",
                                                   "indianapolis-in"}

    def test_no_other_registered_market_was_swept_in(self):
        """Registration is not participation. The two registered markets that
        are NOT source-ready must stay out, and no founder decision can admit
        them. Indianapolis left this list by decision, not by drift."""
        assert (LP.launch_status("indianapolis-in")
                == LP.FOUNDER_AUTHORIZED_FOR_LAUNCH)
        for market_id in ("cincinnati-oh", "detroit-ann-arbor-mi"):
            assert LP.launch_status(market_id) == LP.NOT_SOURCE_READY

    def test_every_registered_market_carries_a_row(self):
        """The gate ``global.launch_participation_explicit`` refuses a bundle
        built while any registered market is unlisted, so an omission is loud
        rather than a silent exclusion."""
        listed = {row["market_id"] for row
                  in json.loads((DEPLOY / "launch_participation.json")
                                .read_text(encoding="utf-8"))["markets"]}
        assert listed == set(MA.registered_market_ids())

    def test_the_record_names_what_it_supersedes(self):
        decision = json.loads((DEPLOY / "launch_participation.json")
                              .read_text(encoding="utf-8"))["decision"]
        assert decision["work_order"] == "PTF-INDIANAPOLIS-LAUNCH-PARTICIPATION-019"
        superseded = decision["supersedes"]
        assert superseded["work_order"] == "PTF-ST-LOUIS-REGISTER-PUBLISH-011"
        # The five St. Louis inherited are still readable, one hop further back
        # now that 019 has been issued. The lineage is what keeps them reachable.
        lineage = decision["lineage"]["records"]
        first = lineage[0]
        assert first["founder_authorized"] == list(LIVE_FIVE)
        assert first["sha256"] == (
            "e766944e49a6610b25eb9ab36deca363fdcf72bafce4bd82d933eb0b78f64eab")


class TestTheDeployedArtifactIsNotDisturbed:
    """A new bundle needs a NEW authorization. The deployed one is CONSUMED."""

    def test_the_012_record_still_describes_what_it_deployed(self):
        """PTF-ST-LOUIS-PRODUCTION-DEPLOY-012 superseded this deploy in
        production. It did not edit the record of it: a deployment record says
        what a deployment DID, and that never changes afterwards."""
        live = json.loads(
            (DEPLOY / "deployment_records"
             / "ptf-deploy-012-6a8c6de6fa99ff1f7bd5c7f5.json")
            .read_text(encoding="utf-8"))
        assert live["bundle_sha256"] == (
            "70747f09fdfe18ccc18e13a3155cc6287404e3ddfe5bb5784d0f03cc30348967")
        assert live["total_profiles"] == 333
        assert live["participating_markets"] == list(LIVE_FIVE)
        assert "st-louis-mo" not in live["participating_markets"]

    def test_the_earlier_authorizations_were_not_reused_for_st_louis(self):
        """Each was consumed by its own deploy. St. Louis needed a new one, and
        neither of these was reopened to supply it."""
        for name in ("ptf-auth-047-a324b1bf5023.json",
                     "ptf-auth-012-70747f09fdfe.json"):
            auth = json.loads((DEPLOY / "deployment_authorizations" / name)
                              .read_text(encoding="utf-8"))
            assert auth["authorization_status"] == "DEPLOYED"
            assert "st-louis-mo" not in auth["participating_markets"]


class TestMeasurementAndAffiliateUnchanged:
    def test_measurement_is_still_disabled(self):
        measurement = json.loads(
            (DEPLOY / "measurement.json").read_text(encoding="utf-8"))
        assert measurement.get("enabled") is False

    def test_the_measurement_config_still_hashes_to_the_pinned_value(self):
        manifest = json.loads(
            (DEPLOY / "global_deployment_manifest.json").read_text(encoding="utf-8"))
        assert (_sha(DEPLOY / "measurement.json")
                == manifest["measurement"]["config_sha256"])

    def test_no_affiliate_provider_is_enrolled(self):
        providers = json.loads(
            (DEPLOY / "affiliate_providers.json").read_text(encoding="utf-8"))
        enrolled = [p for p in (providers.get("providers") or [])
                    if p.get("enrolled") or p.get("active")]
        assert enrolled == []

    def test_st_louis_enrolls_no_affiliate_destination(self):
        shard = json.loads(MA.affiliate_shard_path("st-louis-mo")
                           .read_text(encoding="utf-8"))
        assert shard["count"] == 0
        assert shard["destinations"] == []


class TestEveryContractStillVerifies:
    def test_all_seven_release_contracts_agree_with_their_own_authority(self):
        results = RC.verify_all()
        assert "st-louis-mo" in results
        assert {k: v for k, v in results.items() if v} == {}

    def test_the_global_manifest_verifies(self):
        manifest = json.loads(
            (DEPLOY / "global_deployment_manifest.json").read_text(encoding="utf-8"))
        assert GD.verify_manifest(manifest) == []

    def test_the_manifest_pins_the_participation_file_as_it_stands(self):
        manifest = json.loads(
            (DEPLOY / "global_deployment_manifest.json").read_text(encoding="utf-8"))
        assert _sha(DEPLOY / "launch_participation.json") == (
            manifest["launch_participation"]["sha256"])
