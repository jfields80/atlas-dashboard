"""PTF-LOUISVILLE-PUBLICATION-008 -- what registering and publishing a market
has to be able to say about itself.

A market arrives in production through four artifacts that can disagree in
silence: the policy package the site reads, the authority shard the seeds come
from, the release contract that gates the build, and the participation row that
admits it to the bundle. Each of the ways they can disagree is a different kind
of wrong, and this file is one assertion per way.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.pettripfinder import deployment_authorization as DA
from scripts.pettripfinder import global_deployment as GD
from scripts.pettripfinder import launch_participation as LP
from scripts.pettripfinder import market_authority as MA
from scripts.pettripfinder import release_contracts as RC
from scripts.pettripfinder.census_partition_builder import slugify
from scripts.pettripfinder.contracts import policy_schema as PS
from scripts.pettripfinder.markets import load_markets, market_by_id

REPO = Path(__file__).resolve().parents[2]
PKG = REPO / "launch_packages" / "pettripfinder"
MARKET = "louisville-ky"
PACKAGE_PATH = PKG / "hotel_policy_facts_louisville-ky.json"
PROFILES = 46
EXCLUSIONS = 17


@pytest.fixture(scope="module")
def package():
    return json.loads(PACKAGE_PATH.read_text(encoding="utf-8-sig"))


@pytest.fixture(scope="module")
def contract():
    return RC.load_contract(MARKET)


class TestThePackageIsTheOneTheFounderSigned:
    def test_it_holds_the_signed_population_and_says_it_is_published(self, package):
        assert package["count"] == PROFILES == len(package["hotels"])
        assert package["schema_version"] == "1.3"
        assert package["published"] is True

    def test_every_record_validates_under_the_schema_it_claims(self, package):
        for record in package["hotels"]:
            assert PS.validate_facts(record["facts"]) == (), record["identity_key"]
            assert PS.validate_record(record) == (), record["identity_key"]
        assert PS.validate_package(package) == ()

    def test_the_two_founder_normalisations_are_visible_in_the_facts(self, package):
        """23 weights and one cap publish under a named founder decision, and
        they publish the SOURCE's value with the founder's qualifier -- never a
        value the source did not state."""
        weights = [r for r in package["hotels"] if r["facts"].get("weight_limit")]
        assert len(weights) == 23
        for record in weights:
            weight = record["facts"]["weight_limit"]
            assert weight["operator"] == "lte"
            assert weight["scope"] == "per_pet"
            assert weight["value"] > 0
        caps = [r for r in package["hotels"] if r["facts"].get("fee_cap")]
        assert len(caps) == 1
        assert caps[0]["facts"]["fee_cap"]["qualifier_stated"] is False


class TestTheRoutesNameBuildings:
    def test_every_profile_has_its_own_route(self, package):
        slugs = [slugify(r["name"]) for r in package["hotels"]]
        assert len(slugs) == PROFILES
        assert len(set(slugs)) == PROFILES
        assert all(slugs)

    @pytest.mark.parametrize("name, slug", [
        ("Tru By Hilton Louisville East", "tru-by-hilton-louisville-east"),
        ("Hampton Inn New Albany Louisville West",
         "hampton-inn-new-albany-louisville-west"),
        ("Holiday Inn Louisville Downtown", "holiday-inn-louisville-downtown"),
        ("The Seelbach Hilton Louisville", "the-seelbach-hilton-louisville"),
    ])
    def test_a_corrected_name_carries_into_the_route(self, package, name, slug):
        """The route is slugify(NAME), so a corrected canonical name is what
        decides the URL. None of the eight corrected rows publishes at the bare
        chain word its census row still carries."""
        assert any(r["name"] == name for r in package["hotels"]), name
        assert slugify(name) == slug

    def test_no_profile_publishes_under_a_bare_chain_word(self, package):
        bare = {"tru", "hampton", "holiday-inn", "residence-inn",
                "candlewood-suites", "towneplace-suites", "days-inn",
                "quality-suites"}
        assert not bare & {slugify(r["name"]) for r in package["hotels"]}


class TestTheShardAndThePackageAgree:
    def test_one_seed_row_per_published_record(self, package):
        seeds = MA.load_market_seed_rows(MARKET)
        assert len(seeds) == PROFILES
        assert {r["name"] for r in seeds} == {r["name"] for r in package["hotels"]}

    def test_one_exclusion_per_verified_no_pets_row(self):
        exclusions = MA.load_market_exclusions(MARKET)
        assert len(exclusions) == EXCLUSIONS
        assert {e["exclusion_state"] for e in exclusions} == {"VERIFIED_NO_PETS"}

    def test_an_exclusion_key_derives_from_the_name_it_carries(self):
        """The exclusion contract's own rule, and the way the publication guard
        matches: it normalises the name on the row it is about to publish. A key
        copied from the census identity would miss a corrected name."""
        from scripts.pettripfinder.site_data import normalize_name

        for record in MA.load_market_exclusions(MARKET):
            assert record["normalized_name"] == normalize_name(record["canonical_name"])

    def test_no_published_identity_is_also_excluded(self, package):
        excluded = {e["normalized_name"] for e in MA.load_market_exclusions(MARKET)}
        from scripts.pettripfinder.site_data import normalize_name
        published = {normalize_name(r["name"]) for r in package["hotels"]}
        assert not (published & excluded)

    def test_the_generated_globals_are_in_sync_with_the_shards(self):
        assert MA.check_generated_artifacts() == []


class TestTheContract:
    def test_it_is_in_the_live_set_and_verifies(self, contract):
        assert MARKET in RC.available_market_ids()
        assert RC.verify_contract(MARKET) == []
        assert contract["contract_id"] == "pettripfinder-louisville-ky-release/1.0"

    def test_it_pins_the_package_it_is_about(self, contract):
        spec = contract["policy_package"]
        assert spec["expected_record_count"] == PROFILES
        assert spec["expected_schema_version"] == "1.3"
        assert spec["expected_sha256"] == \
            hashlib.sha256(PACKAGE_PATH.read_bytes()).hexdigest()

    def test_it_states_the_launch_posture_the_market_contract_carries(self, contract):
        market = market_by_id(load_markets(), MARKET)
        assert market.show_in_navigation is False
        assert market.show_in_sitemap is False
        assert contract["routes"]["route_mode"] == market.route_mode == "market_prefixed"
        assert contract["routes"]["hotel_route_count"] == PROFILES

    def test_it_records_the_dual_brand_confirmation_so_no_gate_reasks_it(self, contract):
        group = contract["identity_confirmations"]["dual_brand_same_address"][0]
        assert group["verdict"] == "TWO DISTINCT HOTELS"
        assert set(group["identities"]) == {
            "hampton inn louisville east hurstbourne",
            "home2 suites by hilton louisville east hurstbourne"}
        assert "founder" in group["confirmed_by"]

    def test_no_other_market_stopped_verifying(self):
        assert all(not problems for problems in RC.verify_all().values())


class TestRegistrationIsAtomicWithParticipation:
    def test_the_market_is_registered(self):
        assert MARKET in MA.registered_market_ids()
        assert MARKET in MA.sharded_market_ids()
        assert not (PKG / "markets" / "pending" / "louisville-ky.json").exists()

    def test_it_has_a_participation_row_and_the_check_is_clean(self):
        assert LP.launch_status(MARKET) == LP.FOUNDER_AUTHORIZED_FOR_LAUNCH
        registered = MA.registered_market_ids()
        ready = {mid: True for mid in registered}
        problems = LP.verify_participation(registered, ready)
        assert problems["unlisted"] == []
        assert problems["unregistered"] == []

    def test_a_registered_market_with_no_row_would_be_refused(self):
        """The state this ordering exists to prevent, asserted directly: the
        contract left markets/pending/ and the row was written in one step, and
        had it not been, the check fails closed on the silence."""
        doc = LP.load_participation()
        without = dict(doc, markets=[m for m in doc["markets"]
                                     if m["market_id"] != MARKET])
        registered = MA.registered_market_ids()
        ready = {mid: True for mid in registered}
        problems = LP.verify_participation(registered, ready, without)
        assert problems["unlisted"] == [MARKET]


class TestTheCandidateIsAuthorizedAndNotDeployed:
    def test_the_manifest_carries_the_seven_market_candidate(self):
        manifest = GD.load_manifest()
        assert GD.verify_manifest() == []
        assert [r["market_id"] for r in manifest["participating_markets"]] == [
            "cleveland-akron-canton-oh", "columbus-oh", "dayton-oh",
            "louisville-ky", "milwaukee-wi", "pittsburgh-pa", "st-louis-mo"]
        assert manifest["total_published_profiles"] == 461
        assert manifest["launch_participation"]["sha256"] == LP.participation_sha256()

    def test_the_authorization_is_the_only_one_that_may_deploy(self):
        """PTF-LOUISVILLE-DEPLOYMENT-AUTHORIZATION-009 moved this record
        PREPARED -> AUTHORIZED after re-verifying all eleven bindings the
        founder named. Exactly one record may deploy, and it is this one."""
        auth = DA.load_authorization("ptf-auth-008-38c811dfc22c")
        assert auth["authorization_status"] == DA.AUTHORIZED
        assert DA.verify_authorization(auth) == []
        assert DA.deployability_problems(auth) == []
        deployable = [a["authorization_id"] for a in DA.list_authorizations()
                      if not DA.deployability_problems(a)]
        assert deployable == ["ptf-auth-008-38c811dfc22c"]

    def test_the_prepared_step_is_still_in_the_history(self):
        """A status history that loses its first step cannot show that a human
        moved it."""
        auth = DA.load_authorization("ptf-auth-008-38c811dfc22c")
        assert [e["status"] for e in auth["status_history"]] == [
            DA.PREPARED, DA.AUTHORIZED]
        assert auth["status_history"][-1]["authorized_by"] == "jfields80"

    def test_it_binds_the_bundle_the_named_commit_produces(self):
        manifest = GD.load_manifest()
        auth = next(a for a in DA.list_authorizations()
                    if a["work_order"] == "PTF-LOUISVILLE-PUBLICATION-008")
        assert auth["bundle_sha256"] == manifest["bundle_sha256"]
        assert auth["source_commit"] == manifest["source_commit"]
        assert auth["launch_participation_sha256"] == LP.participation_sha256()
        assert auth["total_profiles"] == 461
        assert auth["global_gate_count"] == 27

    def test_the_market_is_not_deployed_by_any_of_this(self):
        """Authorization is not deployment. The flag mirrors a record that says
        AUTHORIZED, and no deployment record exists for this bundle: what is
        live is still the six-market bundle 011 deployed."""
        manifest = GD.load_manifest()
        assert manifest["deployment_authorized"] is True
        assert manifest["deployment_authorization"]["authorization_id"] == \
            "ptf-auth-008-38c811dfc22c"
        assert GD.verify_manifest() == []
        records = DA.list_records()
        assert not any(r["bundle_sha256"] == manifest["bundle_sha256"]
                       for r in records)
        assert not any("008" in r["deployment_record_id"] for r in records)
