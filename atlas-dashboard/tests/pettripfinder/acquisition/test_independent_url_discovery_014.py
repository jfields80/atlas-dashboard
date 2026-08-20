"""PTF-INDEPENDENT-POLICY-URL-DISCOVERY-014 -- a better URL is still a claim.

Discovery is the easiest place in this pipeline to fool yourself. A rule that
follows any link whose path contains "pet" will find something for almost every
hotel, and the number it produces will look like a discovery rate while being a
measure of how many hotels have the word "pet" somewhere on their site.

So the guarantees here are mostly about what a discovery is NOT allowed to be:

  * not another property. Two of these operators run several hotels on one
    domain. An earlier version of the identity check accepted "same domain" as
    property binding and selected an IOWA FAQ for a Wisconsin hotel.
  * not a brand page. A page that says its terms "may vary by location" has
    told you it does not state this property's terms, however many times the
    property's name appears in its location picker.
  * not an amenity chip. The same bar diagnostic-013 set: a pets-allowed label
    is not a policy.
  * not a guess. A candidate must come from a link the property's own page
    actually contains, or the rate measures URL conventions rather than this
    corpus.

The correction that fixed the first two nearly broke a third: treating every
unrecognised path segment as a "location" read /contact/ and /amenities/ as two
different places and disqualified a hotel for having more than one page. Both
directions are pinned below.
"""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from scripts.pettripfinder.acquisition import independent_url_discovery_014 as U
from scripts.pettripfinder.acquisition import providers as PROVIDERS
from scripts.pettripfinder.acquisition import registry as REGISTRY

REPO_ROOT = Path(__file__).resolve().parents[3]
REPORTS = REPO_ROOT / "launch_packages" / "pettripfinder" / "markets" / "reports"
DISCOVERY = REPORTS / "ptf_independent_url_discovery_014.json"
ROUTES_PATH = (REPO_ROOT / "scripts" / "pettripfinder" / "acquisition"
               / "routes.json")


def _doc():
    if not DISCOVERY.is_file():
        pytest.skip("discovery not run in this worktree")
    return json.loads(DISCOVERY.read_text(encoding="utf-8-sig"))


# --------------------------------------------------------------------------- #
# 1 & 10. Cohort and determinism
# --------------------------------------------------------------------------- #

class TestTheCohortIsTheMechanicalEleven:
    def test_it_is_exactly_eleven_and_asserted(self):
        assert U.EXPECTED_COHORT == 11
        assert len(U.cohort()) == 11
        assert "ABORT" in inspect.getsource(U.cohort)

    def test_it_includes_the_property_013_excluded_by_its_cap(self):
        keys = {r["identity_key"] for r in U.cohort()}
        assert "woodspring suites milwaukee menomonee falls" in keys

    def test_it_is_derived_from_the_registry_not_listed(self):
        source = inspect.getsource(U.cohort)
        assert "generic_universe" in source
        assert "knickerbocker" not in source.lower()

    def test_selection_is_deterministic(self):
        first = [r["identity_key"] for r in U.cohort()]
        second = [r["identity_key"] for r in U.cohort()]
        assert first == second

    def test_the_candidate_budget_is_fixed_and_equal_for_every_property(self):
        """A property given more attempts would report a better discovery rate
        for that reason alone."""
        assert U.MAX_CANDIDATES_PER_PROPERTY == 3
        for row in _doc()["properties"]:
            assert len(row["candidates_tried"]) <= U.MAX_CANDIDATES_PER_PROPERTY


# --------------------------------------------------------------------------- #
# 2. Candidates come from evidence, and stay first-party
# --------------------------------------------------------------------------- #

class TestCandidatesAreDiscoveredNotGuessed:
    def test_a_candidate_must_come_from_a_link_on_the_page(self):
        html = '<a href="/pets/">Pets</a><a href="/rooms/">Rooms</a>'
        found = {c["url"] for c in
                 U.discover_candidates(html, "https://example.test/")}
        assert "https://example.test/pets/" in found
        # Never invented, however conventional.
        assert "https://example.test/pet-policy" not in found

    def test_nothing_is_synthesised_from_a_path_convention(self):
        assert U.discover_candidates("<html>no links</html>",
                                     "https://example.test/") == []

    def test_the_ladder_prefers_what_the_site_itself_names_most_specifically(self):
        html = ('<a href="/amenities/">Amenities</a>'
                '<a href="/faq/">FAQ</a>'
                '<a href="/dogs/">Dogs</a>')
        ranked = U.discover_candidates(html, "https://example.test/")
        assert ranked[0]["url"].endswith("/dogs/")
        assert ranked[0]["score"] > ranked[-1]["score"]

    def test_privacy_and_booking_pages_are_never_candidates(self):
        html = ('<a href="/privacy-policy/">Privacy Policy</a>'
                '<a href="/terms-of-use/">Terms of Use</a>'
                '<a href="/book">Book Now</a>')
        assert U.discover_candidates(html, "https://example.test/") == []

    def test_an_off_domain_link_is_classified_not_silently_followed(self):
        assert U.domain_relationship("https://other.test/pets",
                                     "https://example.test/") == "THIRD_PARTY"
        assert U.domain_relationship("https://www.example.test/pets",
                                     "https://example.test/") == "SAME_DOMAIN"

    def test_third_party_candidates_are_excluded_from_the_attempt_budget(self):
        source = inspect.getsource(U.evaluate)
        assert 'relationship"] != "THIRD_PARTY"' in source


# --------------------------------------------------------------------------- #
# 3 & 5. Identity is required, and same-domain is not identity
# --------------------------------------------------------------------------- #

class TestIdentityBinding:
    ENTRY = {"canonical_name": "Wildwood Lodge",
             "official_url": "https://thewildwoodlodge.com/pewaukee/"}

    def test_a_different_location_on_the_same_domain_is_refused(self):
        """It selected an Iowa FAQ for a Wisconsin hotel before this existed."""
        identity = U.check_identity(
            self.ENTRY, "Wildwood Lodge Clive FAQ. Dogs $20 per night.",
            "https://thewildwoodlodge.com/clive/faqs/")
        assert identity["confirmed"] is False
        assert identity["location_conflict"] is True
        assert "different location" in identity["why"]

    def test_the_property_own_location_is_accepted(self):
        identity = U.check_identity(
            self.ENTRY, "Wildwood Lodge Pewaukee FAQ.",
            "https://thewildwoodlodge.com/pewaukee/faqs/")
        assert identity["confirmed"] is True
        assert identity["location_conflict"] is False

    def test_a_page_type_is_not_mistaken_for_a_location(self):
        """The correction for the Iowa bug nearly disqualified a hotel for
        having both a /contact/ page and an /amenities/ page."""
        entry = {"canonical_name": "The Plaza Hotel Milwaukee",
                 "official_url": "https://plazahotelmilwaukee.com/contact/"}
        identity = U.check_identity(entry, "The Plaza Hotel. $50 pet fee.",
                                    "https://plazahotelmilwaukee.com/amenities/")
        assert identity["location_conflict"] is False
        assert identity["confirmed"] is True

    def test_a_page_that_disclaims_specificity_can_never_bind(self):
        """"Restrictions apply and may vary by location" is the page telling
        you it does not state this property's terms."""
        entry = {"canonical_name": "WoodSpring Suites Milwaukee Menomonee Falls",
                 "official_url": "https://www.woodspring.com/locations/x/"}
        identity = U.check_identity(
            entry,
            "WoodSpring Menomonee Falls Milwaukee. Pet fees apply. "
            "Restrictions apply and may vary by location.",
            "https://www.woodspring.com/offers/pet-friendly-hotel")
        assert identity["confirmed"] is False
        assert identity["disclaims_property_specificity"] is True

    def test_a_disclaiming_page_is_graded_generic_even_if_it_names_the_property(self):
        quality = U.source_quality(
            {"canonical_name": "X"},
            {"relationship": "SAME_DOMAIN", "score": 100, "url": "https://x.test/pets/"},
            {"disclaims_property_specificity": True, "tokens_found": ["x"],
             "same_domain": True, "location_conflict": False})
        assert quality == "generic_brand_or_operator_page"


# --------------------------------------------------------------------------- #
# 4 & 6. Policy presence, judged as 013 judged it
# --------------------------------------------------------------------------- #

class TestPolicyPresence:
    def test_an_amenity_only_page_cannot_become_policy_url_found(self):
        doc = _doc()
        for row in doc["properties"]:
            if row["outcome"] == "POLICY_URL_FOUND":
                assert row["policy_presence"] in ("FULL_POLICY_PRESENT",
                                                  "PARTIAL_POLICY_PRESENT")

    def test_presence_is_classified_by_the_013_taxonomy_not_a_new_one(self):
        source = inspect.getsource(U.evaluate)
        assert "D13.classify_presence" in source

    def test_presence_is_judged_without_the_reader(self):
        """Layer B independence, inherited from 013: a reader failure must not
        look like an absent policy."""
        source = inspect.getsource(U.evaluate)
        presence_line = [ln for ln in source.splitlines()
                         if "classify_presence" in ln][0]
        assert "reader" not in presence_line

    def test_every_found_url_carries_its_supporting_snippet(self):
        for row in _doc()["properties"]:
            if row["outcome"] == "POLICY_URL_FOUND":
                assert row["policy_snippets"], row["identity_key"]
                assert row["discovery_evidence"]["anchor_text"] is not None
                assert row["identity_evidence"]["confirmed"] is True


class TestUrlAndReaderEffectsAreSeparated:
    def test_every_found_url_is_labelled_with_which_layer_still_loses(self):
        for row in _doc()["properties"]:
            if row["outcome"] == "POLICY_URL_FOUND":
                assert row["reader_effect"] in (
                    "URL_FIX_SUFFICIENT", "URL_FOUND_READER_STILL_MISSES",
                    "URL_FOUND_PROVIDER_LIMITED"), row["identity_key"]

    def test_the_reader_is_not_credited_for_a_url_improvement(self):
        """A URL fix that still loses information must say so, or the next work
        order will believe the reader is fine."""
        effects = _doc()["reader_effects"]
        assert "URL_FOUND_READER_STILL_MISSES" in effects or \
            effects.get("URL_FIX_SUFFICIENT", 0) == sum(effects.values())


# --------------------------------------------------------------------------- #
# 7, 8, 9. Boundaries
# --------------------------------------------------------------------------- #

class TestNothingWasChanged:
    def test_no_source_url_was_edited(self):
        source = inspect.getsource(U)
        assert "official_url\"] =" not in source
        assert "identity_census" not in source
        assert "_policy_acquisition_queue" not in source

    def test_no_route_mutation(self):
        registry = REGISTRY.load()
        assert registry["version"] == 4
        assert registry["default"]["provider"] == PROVIDERS.BRIGHTDATA_BROWSER
        assert registry["brands"]["MOTEL6"]["provider"] == \
            PROVIDERS.BRIGHTDATA_BROWSER
        assert registry["brands"]["RED_ROOF"]["provider"] == \
            PROVIDERS.BRIGHTDATA_BROWSER
        for brand in ("CHOICE", "WYNDHAM", "IHG"):
            assert registry["brands"][brand]["provider"] == PROVIDERS.FIRECRAWL
        assert set(registry["domains"]) == {"www.choicehotels.com"}

    def test_the_route_table_does_not_cite_this_work_order(self):
        assert "DISCOVERY-014" not in ROUTES_PATH.read_text(encoding="utf-8")

    def test_no_policy_authority_exists_for_this_market(self):
        shard = (REPO_ROOT / "launch_packages" / "pettripfinder"
                 / "hotel_policy_facts_milwaukee-wi.json")
        assert not shard.exists()

    def test_neither_bright_data_provider_is_reachable(self):
        source = inspect.getsource(U)
        for forbidden in ("browser_capture", "cross_brand_capture",
                          "brightdata_browser", "brightdata_web_unlocker"):
            assert forbidden not in source, forbidden
        assert "FC.fetch" in inspect.getsource(U.fetch)

    def test_the_reader_was_not_modified(self):
        source = inspect.getsource(U)
        assert "policy_reading" not in source
        assert "D13.read_generically" in source

    def test_the_artifact_records_every_boundary(self):
        boundaries = _doc()["boundaries_respected"]
        for key in ("routes_changed", "reader_changed", "source_urls_changed",
                    "authority_written", "policies_published"):
            assert boundaries[key] is False, key
        assert boundaries["bright_data_attempts"] == 0


class TestTheCommittedDiscovery:
    def test_the_cohort_size_is_eleven(self):
        assert _doc()["cohort_size"] == 11

    def test_outcomes_account_for_every_property(self):
        doc = _doc()
        assert sum(doc["outcomes"].values()) == doc["cohort_size"]

    def test_the_ladder_is_recorded_so_the_ordering_is_auditable(self):
        ladder = _doc()["discovery_ladder"]
        assert ladder
        assert ladder[0]["score"] > ladder[-1]["score"]

    def test_no_bright_data_was_spent(self):
        cost = _doc()["cost"]
        assert cost["bright_data_attempts"] == 0
        assert cost["bright_data_usd"] == 0.0

    def test_the_recommendation_follows_from_the_discovery_rate(self):
        doc = _doc()
        rate = doc["rates"]["policy_url_discovery_rate_pct"]
        rec = doc["architectural_recommendation"]
        if rec == "BUILD_URL_DISCOVERY_LAYER":
            assert rate >= 60
        elif rec == "MIXED":
            assert 30 <= rate < 60
        elif rec == "MANUAL_SOURCE_ROUTING":
            assert 0 < rate < 30
        else:
            assert rate == 0
