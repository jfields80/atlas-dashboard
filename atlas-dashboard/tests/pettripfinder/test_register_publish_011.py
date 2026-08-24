"""PTF-ST-LOUIS-REGISTER-PUBLISH-011 -- the four defects registration exposed.

Registering a market is the first act that makes anything READ its authority
end to end. Four things that had never been read broke at once, and each one
would have shipped something wrong rather than nothing:

1. The package's ``key`` was the CENSUS identity, and the display join is on
   the PUBLISHED name. Four records disagreed and the join fails closed.
2. Two markets held one bare identity, ``holiday inn express and suites``.
   Cleveland's is LIVE. One identity is one listing.
3. ``withheld_fields`` was a map of bare reason-code STRINGS. The renderer
   reads decisions; a string crashes it. Twenty-two of the thirty entries were
   ``SOURCE_SILENT``, which the withholding contract rejects by name.
4. A founder ruling that two Chesterfield hotels are distinct lived in a
   ledger the exclusion guard does not read, so the pet-friendly half of a
   dual-brand pair was blocked by its neighbour's refusal.
"""

from __future__ import annotations

import csv
import json
import pathlib

import pytest

from scripts.pettripfinder import hotel_exclusions as HE
from scripts.pettripfinder import market_authority as MA
from scripts.pettripfinder import market_policy_package_cli as PP
from scripts.pettripfinder import market_registration_cli as MR
from scripts.pettripfinder import publication_guard as PG
from scripts.pettripfinder import release_contracts as RC
from scripts.pettripfinder.contracts import enums, withholding
from scripts.pettripfinder.site_data import normalize_name

PKG = pathlib.Path("launch_packages/pettripfinder")
MARKET = "st-louis-mo"


def _load(name):
    return json.loads((PKG / name).read_text(encoding="utf-8"))


def _package():
    return _load("hotel_policy_facts_st-louis-mo.json")


def _authority():
    return _load("st_louis_mo_proposed_authority_008b.json")


# --------------------------------------------------------------------------- #
# 1. The display join key
# --------------------------------------------------------------------------- #

class TestTheDisplayJoinKey:
    def test_every_record_joins_to_exactly_one_seed_row(self):
        """``verified_public_hotels`` matches ``normalize_name(seed name)`` to
        the package record's ``key`` and RAISES on a record with no row. This is
        the join, stated directly."""
        seeds = {normalize_name(r["name"])
                 for r in MA.load_market_seed_rows(MARKET)}
        keys = {h["key"] for h in _package()["hotels"]}
        assert keys == seeds
        assert len(keys) == 82

    def test_key_is_the_published_name_and_identity_key_is_the_census_one(self):
        """They are different questions and four records prove it. Collapsing
        them either publishes a bare chain word as a hotel name or breaks the
        join -- 010 emitted the census key for both and hit the second."""
        differing = [h for h in _package()["hotels"]
                     if h["key"] != h["identity_key"]]
        assert {h["identity_key"] for h in differing} == {
            "courtyard", "days inn", "hampton", "holiday inn express and suites"}
        for record in differing:
            assert record["key"] == normalize_name(record["name"])

    def test_the_identity_key_still_binds_to_the_founders_signature(self):
        """The correction may not move what the founder signed against."""
        signed = ({r["normalized_name"] for r in _authority()["pet_friendly"]})
        assert {h["identity_key"] for h in _package()["hotels"]} == signed

    def test_the_registration_builder_refuses_a_seed_row_that_cannot_join(self):
        record = {"normalized_name": "courtyard",
                  "canonical_name": "Courtyard by Marriott St. Louis Airport/Earth City",
                  "address": "1 Way", "city": "Earth City", "state": "MO",
                  "postal_code": "63045", "official_url": "https://example.invalid/",
                  "source_url": "https://example.invalid/", "observed_at": "2026-08-23",
                  "evidence_quote": "Pets allowed"}
        # The package publishes one name and joins on another: the shape 010
        # committed, where key was the census identity and name was the
        # corrected one.
        package = {"courtyard": {"key": "courtyard",
                                 "name": "Courtyard by Marriott "
                                         "St. Louis Airport/Earth City"}}
        with pytest.raises(MR.MarketRegistrationError) as exc:
            MR.seed_row(record, {"phone": "3145551234"}, MARKET, package)
        assert "the join fails closed" in str(exc.value)


# --------------------------------------------------------------------------- #
# 2. One identity is one listing
# --------------------------------------------------------------------------- #

class TestTheCrossMarketIdentityCollision:
    def test_no_two_seed_rows_anywhere_claim_one_identity(self):
        """``assemble_seed_rows`` refuses the global inventory otherwise, and it
        refused: Cleveland-Akron-Canton has published a LIVE hotel under the
        bare identity ``holiday inn express and suites`` (Westlake OH, IHG
        clelw) since before St. Louis existed."""
        rows = MA.assemble_seed_rows()
        seen = {}
        for row in rows:
            key = (row["category"], normalize_name(row["name"]))
            assert key not in seen, (key, seen.get(key), row["market_id"])
            seen[key] = row["market_id"]

    def test_the_wentzville_hotel_publishes_under_the_name_its_page_states(self):
        corrections = {r["identity_key"]: r for r in _load(
            "markets/name_corrections/st-louis-mo.json")["records"]}
        row = corrections["holiday inn express and suites"]
        assert row["corrected_canonical_name"] == (
            "Holiday Inn Express & Suites Wentzville St Louis West")
        # The rule the overlay states about itself: a replacement may only be a
        # name the property's own captured page states.
        assert row["evidence_field"] == "identity_check.name_on_page"
        store = _load("st_louis_mo_observation_store_007.json")
        observed = {r["identity_key"]: r for r in store["records"]}
        on_page = observed["holiday inn express and suites"][
            "observation"]["identity_check"]["name_on_page"]
        assert on_page.replace("&amp;", "&") == row["corrected_canonical_name"]

    def test_the_two_holiday_inn_express_rows_are_different_buildings(self):
        by_market = {}
        for market_id in ("cleveland-akron-canton-oh", MARKET):
            for row in MA.load_market_seed_rows(market_id):
                if "holiday inn express" in normalize_name(row["name"]):
                    by_market.setdefault(market_id, []).append(row)
        cleveland = [r for r in by_market["cleveland-akron-canton-oh"]
                     if normalize_name(r["name"]) == "holiday inn express and suites"]
        assert len(cleveland) == 1
        assert cleveland[0]["city"] == "Westlake"
        assert "clelw" in cleveland[0]["source_url"]
        wentzville = [r for r in by_market[MARKET] if "stlws" in r["source_url"]]
        assert len(wentzville) == 1
        assert wentzville[0]["city"] == "Wentzville"

    def test_the_overlay_is_idempotent_on_rows_already_corrected(self):
        """The observation store applied this overlay when it was built, so
        re-applying it at projection time must move nothing that already moved.
        Only a row corrected AFTER the authority was signed can change."""
        overlay = _load("markets/name_corrections/st-louis-mo.json")
        names = PP.corrected_names(overlay)
        authority = {r["normalized_name"]: r["canonical_name"]
                     for r in _authority()["pet_friendly"]}
        moved = [k for k, v in names.items()
                 if k in authority and authority[k] != v]
        assert moved == ["holiday inn express and suites"]


# --------------------------------------------------------------------------- #
# 3. Withholding is a decision, not a string
# --------------------------------------------------------------------------- #

class TestWithholdingProjection:
    def test_silence_is_absence_and_never_a_withholding_decision(self):
        """``withheld_fields`` means "we know something and are choosing not to
        publish it". ``contracts.withholding`` rejects SOURCE_SILENT by name:
        an entry claiming a decision was made about a non-event would tell a
        reader the hotel was overruled when it simply never spoke."""
        signed = sum(1 for r in _authority()["pet_friendly"]
                     for v in (r.get("withheld_fields") or {}).values()
                     if v == enums.SOURCE_SILENT)
        assert signed == 22
        for record in _package()["hotels"]:
            for field, entry in (record.get("withheld_fields") or {}).items():
                assert entry["reason_code"] != enums.SOURCE_SILENT

    def test_every_surviving_decision_is_reviewable(self):
        decisions = [(h["key"], f, e) for h in _package()["hotels"]
                     for f, e in (h.get("withheld_fields") or {}).items()]
        assert len(decisions) == 8
        for key, field, entry in decisions:
            assert entry["reason_code"] == enums.SCHEMA_CANNOT_REPRESENT
            assert entry["reason"].strip(), (key, field)
            assert entry["evidence_refs"], (key, field)

    def test_the_whole_package_satisfies_the_withholding_contract(self):
        for record in _package()["hotels"]:
            assert withholding.validate(record) == (), record["key"]

    def test_the_reason_is_the_readers_own_sentence_not_one_written_here(self):
        store = {r["identity_key"]: r for r
                 in _load("st_louis_mo_observation_store_007.json")["records"]}
        for record in _package()["hotels"]:
            for entry in (record.get("withheld_fields") or {}).values():
                observed = store[record["identity_key"]]["observation"]
                details = [f["detail"] for f in observed.get("flags") or ()]
                assert entry["reason"] in "; ".join(details)

    def test_a_bare_string_would_crash_the_profile_renderer(self):
        """The shape is not cosmetic: canonical_view.withheld_reason_code calls
        ``.get`` on the entry, so a string raises AttributeError mid-build."""
        from scripts.pettripfinder import canonical_view
        view = canonical_view.build(
            {"facts": {}, "withheld_fields": {"pet_fee": "SOURCE_SILENT"},
             "schema_version": "1.3"}, market_id=MARKET)
        with pytest.raises(AttributeError):
            view.withheld_reason_code("pet_fee")

    def test_evidence_references_come_from_the_store(self):
        refs = [e["evidence_ref"] for h in _package()["hotels"]
                for e in h["evidence"]]
        assert refs and all(r for r in refs), "every evidence item carries a ref"
        assert all(r.startswith("st-louis-mo-") for r in refs)


# --------------------------------------------------------------------------- #
# 4. The dual-brand pair
# --------------------------------------------------------------------------- #

class TestTheChesterfieldDualBrand:
    ADDRESS_KEY = "1065|chesterfield|63017"

    def _resolution(self):
        return [r for r in PG.load_resolutions()
                if r["resolution_id"] == "res-st-louis-chesterfield-dual-brand"][0]

    def test_the_founder_ruling_is_in_the_contract_the_guard_reads(self):
        """008B recorded 'CONFIRMED AS TWO DISTINCT HOTELS' in a withdrawal
        ledger, because an unregistered market had no resolutions row to put it
        in. The guard does not read that ledger. This is the same ruling in the
        authority the guard does read -- not a new decision."""
        resolution = self._resolution()
        assert resolution["address_key"] == self.ADDRESS_KEY
        assert resolution["market_id"] == MARKET
        confirmation = _load(
            "st_louis_mo_founder_withdrawals_008b.json")["identity_confirmations"][0]
        assert (resolution["decision_source"]["founder_ruling"]
                == confirmation["founder_ruling"])
        assert resolution["reviewer_id"] == "jfields80"

    def test_both_hotels_survive_and_neither_is_merged(self):
        published = {normalize_name(r["name"])
                     for r in MA.load_market_seed_rows(MARKET)}
        excluded = {r["normalized_name"] for r in MA.load_market_exclusions(MARKET)}
        assert "fairfield by marriott inn and suites st louis chesterfield" in published
        assert "springhill suites by marriott st louis chesterfield" in excluded

    def test_an_address_match_is_waived_only_with_a_resolution(self):
        candidate = {"name": "Fairfield by Marriott Inn & Suites St. Louis Chesterfield",
                     "address": "1065 Chesterfield Pkwy E", "postal_code": "63017",
                     "category": "pet-friendly-hotels"}
        exclusions = [r for r in MA.load_market_exclusions(MARKET)
                      if r["normalized_name"]
                      == "springhill suites by marriott st louis chesterfield"]
        assert exclusions
        # With the reviewed resolution: publishable.
        assert PG.exclusion_blocks([candidate], exclusions,
                                   resolutions=PG.load_resolutions()) == []
        # Without it: blocked. Absent means UNRESOLVED, never an automatic pass.
        blocked = PG.exclusion_blocks([candidate], exclusions, resolutions=[])
        assert len(blocked) == 1
        assert blocked[0]["match_basis"] == PG.MATCH_ADDRESS

    def test_a_name_match_is_never_waived_by_any_resolution(self):
        """A resolution is about an ADDRESS. No ruling about a shared building
        may publish a hotel that itself said no."""
        springhill = [r for r in MA.load_market_exclusions(MARKET)
                      if r["normalized_name"]
                      == "springhill suites by marriott st louis chesterfield"]
        candidate = {"name": "SpringHill Suites by Marriott St. Louis Chesterfield",
                     "address": "1065 Chesterfield Pkwy E", "postal_code": "63017",
                     "category": "pet-friendly-hotels"}
        blocked = PG.exclusion_blocks([candidate], springhill,
                                      resolutions=PG.load_resolutions())
        assert len(blocked) == 1
        assert blocked[0]["match_basis"] == PG.MATCH_NAME


# --------------------------------------------------------------------------- #
# The shard equals the current signed-minus-superseded set
# --------------------------------------------------------------------------- #

class TestTheAuthorityShard:
    def test_it_states_exactly_the_current_authority(self):
        assert MR.verify(MARKET, PKG / "st_louis_mo_proposed_authority_008b.json") == []

    def test_the_arithmetic_is_82_plus_37_equals_119(self):
        seeds = MA.load_market_seed_rows(MARKET)
        exclusions = MA.load_market_exclusions(MARKET)
        assert len(seeds) == 82
        assert len(exclusions) == 37
        assert len(seeds) + len(exclusions) == _authority()["authority_total"] == 119

    def test_every_exclusion_is_verified_no_pets_with_its_own_evidence(self):
        for row in MA.load_market_exclusions(MARKET):
            assert row["exclusion_state"] == HE.VERIFIED_NO_PETS
            assert row["evidence_quote"].strip()
            assert row["reviewer_id"] == "jfields80"
            # Derived by the contract's own functions, so a hand edit fails.
            assert row["record_hash"] == HE.record_hash(row)
            assert row["approval_hash"] == HE.approval_hash(row)

    def test_neither_superseded_identity_reached_a_publication_set(self):
        superseded = {r["identity_key"] for r in _authority()["superseded_rows"]}
        assert superseded == {"wingate at wyndham", "doubletree"}
        published = {normalize_name(r["name"])
                     for r in MA.load_market_seed_rows(MARKET)}
        excluded = {r["normalized_name"] for r in MA.load_market_exclusions(MARKET)}
        assert not (published | excluded) & superseded

    def test_the_held_identity_has_no_row_to_leak(self):
        held = "days inn and suites pontoon beach"
        assert held not in {normalize_name(r["name"])
                            for r in MA.load_market_seed_rows(MARKET)}
        assert held not in {r["normalized_name"]
                            for r in MA.load_market_exclusions(MARKET)}
        assert held not in {h["identity_key"] for h in _package()["hotels"]}

    def test_the_seed_rows_state_no_field_this_layer_invented(self):
        for row in MA.load_market_seed_rows(MARKET):
            for column in MR.SEED_REQUIRED:
                assert str(row[column]).strip(), (row["name"], column)
            assert row["source_type"] == "OFFICIAL_PROPERTY"
            assert row["market_id"] == MARKET

    def test_routing_and_affiliate_shards_are_explicitly_empty(self):
        """An empty shard is a statement; a missing one is a silence."""
        assert MA.load_market_routes(MARKET) == []
        affiliate = json.loads(
            MA.affiliate_shard_path(MARKET).read_text(encoding="utf-8"))
        assert affiliate["count"] == 0


# --------------------------------------------------------------------------- #
# The release contract
# --------------------------------------------------------------------------- #

class TestTheLiveReleaseContract:
    def test_it_verifies_against_its_own_authority(self):
        assert RC.verify_contract(MARKET) == []

    def test_it_pins_the_published_package(self):
        import hashlib
        block = RC.load_contract(MARKET)["policy_package"]
        raw = pathlib.Path(block["path"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == block["expected_sha256"]
        assert block["expected_record_count"] == 82
        assert block["expected_schema_version"] == "1.3"
        assert _package()["published"] is True

    def test_fifteen_corridors_publish_not_ten(self):
        """009 read the MARKET's minimum_published_hotels and reported ten. The
        threshold that decides a corridor route is the CORRIDOR's own
        minimum_hotel_count, which St. Louis sets per corridor."""
        assert RC.load_contract(MARKET)["routes"][
            "published_corridor_route_count"] == 15

    def test_it_no_longer_claims_to_be_unregistered(self):
        contract = RC.load_contract(MARKET)
        assert contract["status"] == "LIVE"
        assert "gates_not_evaluable_offline" not in contract
        assert "location_note" not in contract

    def test_every_market_contract_still_verifies(self):
        assert {k: v for k, v in RC.verify_all().items() if v} == {}
