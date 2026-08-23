"""PTF-ST-LOUIS-MARKET-001 -- the live five-market production set is untouched.

Section 15 of the work order: St. Louis work must not change the live bundle,
the deployment authorization, the deployment record, the launch status of any
existing market, the measurement state or the affiliate state.

The interesting one is the FIRST test. Registering a market is not a free act:
``markets/*.json`` IS the registry, ``launch_participation`` fails closed on any
registered market with no row, and the participation file's sha256 is pinned by
the global deployment manifest AND copied into the founder's signed
authorization. So creating ``markets/st-louis-mo.json`` in this work order would
have invalidated a production deployment record -- which is why the St. Louis
market contract is a valid, parseable, DELIBERATELY UNREGISTERED document in
``markets/pending/``.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.pettripfinder import global_deployment as GD
from scripts.pettripfinder import launch_participation as LP
from scripts.pettripfinder import market_authority as MA
from scripts.pettripfinder.markets.contract import load_markets, parse_market

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE = REPO_ROOT / "launch_packages" / "pettripfinder"
MARKETS_DIR = PACKAGE / "markets"
PENDING = MARKETS_DIR / "pending" / "st-louis-mo.json"
DEPLOY = REPO_ROOT / "deploy" / "netlify"

#: The five markets live at PTF-047, and the two registered-but-withheld ones.
LIVE_FIVE = ("cleveland-akron-canton-oh", "columbus-oh", "dayton-oh",
             "milwaukee-wi", "pittsburgh-pa")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TestStLouisIsNotRegistered:
    def test_the_contract_is_valid_and_deliberately_not_in_the_registry(self):
        document = json.loads(PENDING.read_text(encoding="utf-8"))
        config = parse_market(document, source="pending/st-louis-mo.json")
        assert config.market_id == "st-louis-mo"
        assert config.corridors, "a market contract with no corridor has no geography"
        assert not (MARKETS_DIR / "st-louis-mo.json").exists()

    def test_the_registry_still_holds_exactly_the_markets_it_held(self):
        assert "st-louis-mo" not in MA.registered_market_ids()
        assert len(load_markets()) == 8

    def test_an_unregistered_market_is_never_launch_authorized(self):
        assert LP.launch_status("st-louis-mo") == LP.UNLISTED
        assert not LP.is_founder_authorized("st-louis-mo")

    def test_no_authority_shard_directory_exists_for_st_louis(self):
        """``sharded_market_ids`` fails closed on a shard directory the market
        contract does not know about, so creating one would break every other
        market's authority build."""
        assert "st-louis-mo" not in MA.sharded_market_ids()


class TestLiveParticipationUnchanged:
    def test_the_founder_authorized_set_is_still_the_live_five(self):
        assert tuple(LP.authorized_market_ids()) == LIVE_FIVE

    def test_indianapolis_is_still_source_ready_and_withheld(self):
        assert (LP.launch_status("indianapolis-in")
                == LP.SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH)

    def test_the_participation_record_still_hashes_to_what_the_manifest_pins(self):
        manifest = json.loads(
            (DEPLOY / "global_deployment_manifest.json").read_text(encoding="utf-8"))
        pinned = manifest["launch_participation"]["sha256"]
        assert _sha(DEPLOY / "launch_participation.json") == pinned


class TestDeploymentArtifactsStillVerify:
    def test_the_global_deployment_manifest_verifies(self):
        manifest = json.loads(
            (DEPLOY / "global_deployment_manifest.json").read_text(encoding="utf-8"))
        assert GD.verify_manifest(manifest) == []

    def test_the_deployment_record_and_authorization_are_untouched(self):
        records = sorted((DEPLOY / "deployment_records").glob("*.json"))
        auths = sorted((DEPLOY / "deployment_authorizations").glob("*.json"))
        assert [p.name for p in records] == [
            "ptf-deploy-047-6a8a2dada6e73cb0d819c9d0.json"]
        assert [p.name for p in auths] == [
            "ptf-auth-047-a324b1bf5023.json"]
        record = json.loads(records[0].read_text(encoding="utf-8"))
        assert record["bundle_sha256"] == (
            "a324b1bf5023fc4e8f618d192de5eb994d093ed890db4219678223079e06852d")
        assert record["total_profiles"] == 333
        assert record["participating_markets"] == list(LIVE_FIVE)


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


class TestNoStLouisRouteCanEnterProduction:
    def test_the_live_route_list_names_no_st_louis_route(self):
        routes = (DEPLOY / "live_production_routes.txt").read_text(encoding="utf-8")
        assert "st-louis" not in routes.lower()

    def test_st_louis_has_no_release_contract(self):
        contracts = sorted(p.name for p in
                           (DEPLOY / "release_contracts").glob("*.json"))
        assert "st-louis-mo.json" not in contracts
