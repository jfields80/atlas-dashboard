"""PTF-DISCOVERY-AUTHORITY-001 -- the wall between identity and policy.

The change these tests defend is a loosening in one direction only. A hotel may
now be confirmed to EXIST from a tourism board, a business listing plus an
independent OTA, or any two independent sources that agree on name and street
identity -- because a blocked chain page was producing census holes, not
accuracy. Nothing about PET POLICY moved: it still comes from the property's own
official source, and the tests below try to smuggle a policy in through every
door the new contract opens.
"""

from __future__ import annotations

import pytest

from scripts.pettripfinder.identity_evidence import (
    IDENTITY_CONFIRMED,
    IDENTITY_CONFLICT,
    IDENTITY_PROVISIONAL,
    POLICY_ELIGIBLE_TIERS,
    POLICY_FIELD_NAMES,
    POSSIBLE_CLOSURE,
    POSSIBLE_REBRAND,
    TIER_1_OFFICIAL_PROPERTY,
    TIER_2_OFFICIAL_DESTINATION,
    TIER_3_BUSINESS_LISTING,
    TIER_4_OTA_DIRECTORY,
    IdentityEvidenceError,
    adjudicate,
    assert_no_policy_from_identity_evidence,
    identity_record,
    validate_evidence,
)


def ev(tier, family, name="Test Hotel Independence", address="6001 Rockside Rd",
       postal="44131", **kw):
    rec = {"tier": tier, "source_family": family, "source_url": "https://%s.example/x" % family,
           "observed_at": "2026-08-07", "name": name, "address": address,
           "city": "Independence", "state": "OH", "postal_code": postal}
    rec.update(kw)
    return rec


# --------------------------------------------------------------------------- #
# The wall.
# --------------------------------------------------------------------------- #

class TestPolicyStandardUnchanged:

    def test_only_tier_one_may_establish_a_policy(self):
        assert POLICY_ELIGIBLE_TIERS == (TIER_1_OFFICIAL_PROPERTY,)

    @pytest.mark.parametrize("tier", [TIER_2_OFFICIAL_DESTINATION, TIER_3_BUSINESS_LISTING,
                                      TIER_4_OTA_DIRECTORY])
    def test_non_official_evidence_cannot_carry_a_policy_fact(self, tier):
        with pytest.raises(IdentityEvidenceError, match="[Oo]nly an official property source"):
            assert_no_policy_from_identity_evidence(
                [ev(tier, "cvb")], {"pets_allowed": "true", "pet_fee": "$50.00"})

    def test_a_tier_one_source_may(self):
        assert_no_policy_from_identity_evidence(
            [ev(TIER_1_OFFICIAL_PROPERTY, "property")], {"pets_allowed": "true"})

    def test_evidence_carrying_a_policy_field_is_refused_outright(self):
        with pytest.raises(IdentityEvidenceError, match="may not carry pet-policy field"):
            validate_evidence(ev(TIER_2_OFFICIAL_DESTINATION, "cvb", pets_allowed="true"))

    @pytest.mark.parametrize("field", ["pets_allowed", "pet_fee", "fee_basis", "fee_tiers",
                                       "pet_count_limit", "weight_limit", "breed_restrictions",
                                       "pet_deposit", "species_allowed", "refundability",
                                       "pet_count_scope", "weight_limit_stated_none"])
    def test_every_policy_field_is_barred_from_an_identity_record(self, field):
        with pytest.raises(IdentityEvidenceError, match="pet-policy field"):
            identity_record("Test Hotel", [ev(TIER_2_OFFICIAL_DESTINATION, "cvb")],
                            **{field: "anything"})

    def test_the_barred_vocabulary_matches_production(self):
        from scripts.pettripfinder.site_data import _POLICY_FIELDS
        assert set(_POLICY_FIELDS) <= POLICY_FIELD_NAMES

    def test_an_identity_record_is_policy_unverified_by_construction(self):
        rec = identity_record("Test Hotel", [ev(TIER_2_OFFICIAL_DESTINATION, "cvb")])
        assert rec["policy_state"] == "POLICY_NOT_VERIFIED"
        assert not (POLICY_FIELD_NAMES & set(rec))


# --------------------------------------------------------------------------- #
# The loosening.
# --------------------------------------------------------------------------- #

class TestIdentityConfirmation:

    def test_a_blocked_chain_page_no_longer_costs_an_identity(self):
        """The whole point: a CVB listing alone confirms the hotel exists."""
        assert adjudicate([ev(TIER_2_OFFICIAL_DESTINATION, "akron_summit_cvb")])["outcome"] \
            == IDENTITY_CONFIRMED

    def test_official_property_evidence_confirms(self):
        assert adjudicate([ev(TIER_1_OFFICIAL_PROPERTY, "property")])["outcome"] \
            == IDENTITY_CONFIRMED

    def test_business_listing_plus_independent_ota_confirms(self):
        v = adjudicate([ev(TIER_3_BUSINESS_LISTING, "maps"), ev(TIER_4_OTA_DIRECTORY, "ota")])
        assert v["outcome"] == IDENTITY_CONFIRMED
        assert "independent" in v["reason"]

    def test_two_pages_of_one_source_do_not_confirm(self):
        """A single publisher cannot corroborate itself."""
        v = adjudicate([ev(TIER_4_OTA_DIRECTORY, "ota"), ev(TIER_4_OTA_DIRECTORY, "ota")])
        assert v["outcome"] == IDENTITY_PROVISIONAL

    def test_a_lone_low_tier_source_stays_provisional(self):
        assert adjudicate([ev(TIER_4_OTA_DIRECTORY, "ota")])["outcome"] == IDENTITY_PROVISIONAL

    def test_evidence_without_an_address_stays_provisional(self):
        v = adjudicate([ev(TIER_3_BUSINESS_LISTING, "maps", address="", postal="")])
        assert v["outcome"] == IDENTITY_PROVISIONAL
        assert "street address" in v["reason"]

    def test_sources_agreeing_on_the_name_but_not_the_street_conflict(self):
        v = adjudicate([ev(TIER_3_BUSINESS_LISTING, "maps", address="6001 Rockside Rd"),
                        ev(TIER_4_OTA_DIRECTORY, "ota", address="5300 Rockside Rd")])
        assert v["outcome"] == IDENTITY_CONFLICT

    def test_a_reported_closure_is_never_confirmed(self):
        v = adjudicate([ev(TIER_2_OFFICIAL_DESTINATION, "cvb"),
                        ev(TIER_4_OTA_DIRECTORY, "ota", status_note="Permanently closed")])
        assert v["outcome"] == POSSIBLE_CLOSURE

    def test_a_reported_rename_is_held_not_confirmed(self):
        v = adjudicate([ev(TIER_2_OFFICIAL_DESTINATION, "cvb",
                           status_note="Formerly the Holiday Inn Rockside")])
        assert v["outcome"] == POSSIBLE_REBRAND

    def test_two_names_at_one_address_are_never_merged(self):
        """Gervasi Casa and Villas, and BrewDog DogHouse and DogTap, are the live
        cases this protects."""
        v = adjudicate([ev(TIER_2_OFFICIAL_DESTINATION, "cvb", name="The Casa at Gervasi"),
                        ev(TIER_2_OFFICIAL_DESTINATION, "other_cvb", name="The Villas at Gervasi")])
        assert v["outcome"] == POSSIBLE_REBRAND
        assert "not merged" in v["reason"]

    def test_provenance_is_preserved_on_every_record(self):
        rec = identity_record("Test Hotel", [ev(TIER_3_BUSINESS_LISTING, "maps"),
                                             ev(TIER_4_OTA_DIRECTORY, "ota")])
        assert rec["identity_sources"] == ["maps", "ota"]
        assert rec["identity_tiers"] == [3, 4]
        assert len(rec["evidence"]) == 2


# --------------------------------------------------------------------------- #
# Columbus must not move.
# --------------------------------------------------------------------------- #

class TestColumbusUnchanged:

    def test_the_published_authority_still_holds_83_records(self):
        import json
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        pkg = json.loads((root / "launch_packages/pettripfinder/hotel_policy_facts.json")
                         .read_text(encoding="utf-8"))
        assert len(pkg["hotels"]) == 83

    def test_no_published_record_carries_identity_evidence_provenance(self):
        """The new contract is additive. It has not touched a published record."""
        import json
        import pathlib
        root = pathlib.Path(__file__).resolve().parents[2]
        pkg = json.loads((root / "launch_packages/pettripfinder/hotel_policy_facts.json")
                         .read_text(encoding="utf-8"))
        for h in pkg["hotels"]:
            assert "identity_outcome" not in h
            assert h["source_type"] in ("EXACT_ENTITY_DOMAIN", "BRAND_DOMAIN")

    def test_exclusions_and_resolutions_are_untouched(self):
        from scripts.pettripfinder.hotel_exclusions import load_exclusions
        from scripts.pettripfinder.publication_guard import load_resolutions
        # 3 -> 9 -> 14: PTF-COLUMBUS-AUTHORITY-APPLY-002 added six
        # VERIFIED_NO_PETS records and PTF-NEGATIVE-EVIDENCE-P0-001 added five
        # more once their denials could be cited. They are exclusions, not
        # publications -- which is exactly what this test is here to keep true
        # of them.
        assert len(load_exclusions()) == 16
        assert [r["resolution_id"] for r in load_resolutions()] == ["res-brewdog-gender-rd"]

    def test_a_blocked_columbus_hold_can_be_identity_confirmed_without_a_policy(self):
        """SpringHill Gahanna: Marriott refuses us, so its policy is unknown and
        stays unknown -- but its identity is not in doubt, and the new contract
        can say so without implying anything about pets."""
        rec = identity_record(
            "SpringHill Suites Columbus Airport Gahanna",
            [ev(TIER_2_OFFICIAL_DESTINATION, "experience_columbus",
                name="SpringHill Suites Columbus Airport Gahanna",
                address="665 Taylor Rd", postal="43230"),
             ev(TIER_4_OTA_DIRECTORY, "ota",
                name="SpringHill Suites Columbus Airport Gahanna",
                address="665 Taylor Rd", postal="43230")])
        assert rec["identity_outcome"] == IDENTITY_CONFIRMED
        assert rec["policy_state"] == "POLICY_NOT_VERIFIED"
        with pytest.raises(IdentityEvidenceError):
            assert_no_policy_from_identity_evidence(rec["evidence"], {"pets_allowed": "true"})

    def test_identity_confirmation_creates_no_publication_path(self):
        """An identity record cannot reach the seed or the package: it carries no
        policy, and the publication guard governs those authorities separately."""
        import csv
        import json
        import pathlib
        from scripts.pettripfinder.site_data import normalize_name
        root = pathlib.Path(__file__).resolve().parents[2]
        seed = {normalize_name(r["name"]) for r in csv.DictReader(
            (root / "launch_packages/pettripfinder/seed_businesses.csv").open(encoding="utf-8"))}
        pkg = {h["key"] for h in json.loads(
            (root / "launch_packages/pettripfinder/hotel_policy_facts.json")
            .read_text(encoding="utf-8"))["hotels"]}
        # Aloft Columbus Westerville used to stand here. It was published by
        # PTF-COLUMBUS-AUTHORITY-APPLY-002 -- not by identity confirmation, but
        # by quote-backed policy evidence that passed the publication guard,
        # which is exactly the path this test says identity alone cannot take.
        # Residence Inn Columbus Polaris replaces it: identity CONFIRMED, and
        # held out of both authorities on an unresolved policy contradiction.
        for held in ("SpringHill Suites Columbus Airport Gahanna",
                     "Residence Inn by Marriott Columbus Polaris",
                     "Le Meridien Columbus, The Joseph", "South Wind Motel"):
            assert normalize_name(held) not in seed
            assert normalize_name(held) not in pkg
