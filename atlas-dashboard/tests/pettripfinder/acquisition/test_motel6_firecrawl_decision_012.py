"""PTF-MOTEL6-FIRECRAWL-DECISION-012 -- the first brand decision to say no.

Three brands moved onto Firecrawl on their own measurements. Motel 6 did not,
and a rejected decision needs its guarantees held just as firmly as an approved
one -- arguably more, because the pressure on a fourth test is to find the
answer the first three found.

What these tests hold:

  * the route did NOT move. A REJECT that leaves an experimental route behind
    is worse than no test at all.
  * the bar was applied as written, not as the previous brands' ladder. This
    work order said REJECT below 3/4 OR on a systemic defect, and both fired.
  * the reason is the evidence, not the pass rate. Two captures reached
    publication-grade over a block reading "Pets Allowed Coin Laundry" -- an
    amenity checkbox next to the laundry checkbox. Counting those as successes
    would have made 2/4 look like a near miss instead of what it is.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.pettripfinder.acquisition import motel6_firecrawl_decision_012 as M6
from scripts.pettripfinder.acquisition import providers as PROVIDERS
from scripts.pettripfinder.acquisition import registry as REGISTRY
from scripts.pettripfinder.acquisition import wyndham_firecrawl_decision_008 as WY

REPO_ROOT = Path(__file__).resolve().parents[3]
REPORTS = REPO_ROOT / "launch_packages" / "pettripfinder" / "markets" / "reports"
DECISION = REPORTS / "ptf_motel6_firecrawl_decision_012.json"
ROUTES_PATH = (REPO_ROOT / "scripts" / "pettripfinder" / "acquisition"
               / "routes.json")


def _doc():
    if not DECISION.is_file():
        pytest.skip("decision test not run in this worktree")
    return json.loads(DECISION.read_text(encoding="utf-8-sig"))


# --------------------------------------------------------------------------- #
# The route did not move
# --------------------------------------------------------------------------- #

class TestMotel6StayedWhereItWas:
    def test_the_primary_is_still_the_browser_api(self):
        route = REGISTRY.resolve(
            brand="MOTEL6",
            url="https://www.motel6.com/property/motel-glendale-wisconsin-us-294362/")
        assert route.provider == PROVIDERS.BRIGHTDATA_BROWSER
        assert route.reader == "generic"

    def test_firecrawl_reaches_only_the_three_brands_that_passed(self):
        registry = REGISTRY.load()
        leads = sorted(b for b, row in registry["brands"].items()
                       if row["provider"] == PROVIDERS.FIRECRAWL)
        assert leads == ["CHOICE", "IHG", "WYNDHAM"]
        assert "MOTEL6" not in leads

    def test_the_registry_version_did_not_advance(self):
        """A rejected decision changes nothing, so nothing needs versioning."""
        assert REGISTRY.load()["version"] == 4

    def test_no_experimental_route_was_left_behind(self):
        """The MOTEL6 row must be byte-identical to what it was, and nothing
        anywhere in the table may cite this work order.

        Scoped to the MOTEL6 row and to this work order's own name: an earlier
        version of this test searched the whole file for the phrase "decision
        test" and matched a legitimate rationale sentence in the Wyndham and
        IHG rows, which describe how their attempt budgets were measured."""
        text = ROUTES_PATH.read_text(encoding="utf-8")
        row = json.loads(text)["brands"]["MOTEL6"]
        assert row["provider"] == "brightdata_browser"
        assert row["fallback_providers"] == ["brightdata_web_unlocker"]
        assert row["reader"] == "generic"
        assert row["measured_by"] == "PTF-BRIGHTDATA-CROSS-BRAND-PILOT-002"
        assert "forbidden_providers" not in row
        assert "MOTEL6-FIRECRAWL-DECISION-012" not in text
        assert "DECISION-012" not in text

    def test_the_decision_artifact_says_it_changed_nothing(self):
        doc = _doc()
        assert doc["routes_changed"] is False
        assert doc["authority_written"] is False
        assert doc["policies_published"] is False


# --------------------------------------------------------------------------- #
# The bar
# --------------------------------------------------------------------------- #

class TestTheBarWasAppliedAsWritten:
    def test_the_threshold_was_fixed_before_the_run(self):
        t = _doc()["thresholds_fixed_before_the_run"]
        assert t["cohort"] == 4
        assert t["approve_min_publication_grade_rate"] == 0.75
        assert t["approve_min_records"] == 3

    def test_a_systemic_defect_alone_forces_reject(self):
        """This work order's bar is stricter than the ladder the previous
        brands used: a subset carved out of boilerplate is not a subset, so a
        systemic defect rules out APPROVE_WITH_LIMITATION too."""
        doc = _doc()
        if doc["systemic_defects"]:
            assert doc["decision"] == "REJECT"

    def test_the_decision_follows_from_the_numbers(self):
        doc = _doc()
        rate = doc["totals"]["publication_grade_rate"]
        systemic = doc["systemic_defects"]
        if doc["decision"] == "APPROVE":
            assert rate >= 0.75 and not systemic
        elif doc["decision"] == "REJECT":
            assert rate < 0.75 or systemic
        assert doc["decision_reasons"]

    def test_the_cohort_was_asserted_before_any_request(self):
        import inspect
        source = inspect.getsource(M6.main_async)
        assert "ABORT" in source
        assert M6.EXPECTED_COHORT == 4


# --------------------------------------------------------------------------- #
# Why it failed
# --------------------------------------------------------------------------- #

class TestTheAmenityChipFinding:
    def test_an_amenity_label_is_not_a_policy(self):
        out = M6.amenity_chip_audit([{
            "identity_key": "x",
            "policy_surface_result": {"excerpt": "Pets Allowed Coin Laundry"},
            "extraction": {"pets_allowed": True}}])
        assert out["verdict"] == "AMENITY_CHIP_NOT_POLICY"
        assert out["amenity_chips_read_as_policy"][0]["block_chars"] < 60

    def test_a_terse_refusal_is_not_flagged(self):
        """"Sorry, no pets allowed." is short and featureless and is a real
        policy. Flagging it would push toward publishing nothing."""
        out = M6.amenity_chip_audit([{
            "identity_key": "x",
            "policy_surface_result": {"excerpt": "Sorry, no pets allowed."},
            "extraction": {"pets_allowed": False}}])
        assert out["verdict"] == "POLICY_BLOCKS_ARE_SUBSTANTIVE"

    def test_a_substantive_policy_is_not_flagged(self):
        out = M6.amenity_chip_audit([{
            "identity_key": "x",
            "policy_surface_result": {"excerpt":
                "Pets Allowed. 30 USD per pet per night. 2 pets max, 50 lbs."},
            "extraction": {"pets_allowed": True, "pet_fee": 3000,
                           "pet_count_limit": 2}}])
        assert out["verdict"] == "POLICY_BLOCKS_ARE_SUBSTANTIVE"

    def test_the_live_cohort_tripped_it(self):
        audit = _doc()["amenity_chip_audit"]
        assert audit["verdict"] == "AMENITY_CHIP_NOT_POLICY"
        assert audit["amenity_chips_read_as_policy"]
        for row in audit["amenity_chips_read_as_policy"]:
            assert row["fields"] == ["pets_allowed"]


class TestTheDuplicateTextFinding:
    def test_identical_text_across_the_whole_cohort_is_reported(self):
        dup = _doc()["duplicate_text_audit"]
        assert dup["verdict"] == "BOILERPLATE_SUSPECTED"
        assert dup["distinct_policy_texts"] == 1
        assert dup["distinct_extractions"] == 1

    def test_variation_anywhere_would_have_cleared_it(self):
        """The rule that let Wyndham's three identical La Quintas pass: shared
        text is only boilerplate when the corpus never varies."""
        out = M6.duplicate_text_audit([
            {"identity_key": "a", "policy_surface_result": {"excerpt": "same"},
             "extraction": {"pets_allowed": True}},
            {"identity_key": "b", "policy_surface_result": {"excerpt": "same"},
             "extraction": {"pets_allowed": True}},
            {"identity_key": "c", "policy_surface_result": {"excerpt": "other"},
             "extraction": {"pets_allowed": False}}])
        assert out["verdict"] == "BRAND_STANDARD_OR_VARIED"


class TestTheOffPropertyRedirect:
    def test_a_capture_that_left_the_brand_domain_is_recorded(self):
        doc = _doc()
        off = [a for a in doc["defect_audit"]["per_property"]
               if a["landed_off_the_property_page"]]
        assert off, "the studio6.com redirect must be recorded"

    def test_the_page_health_gate_refused_it_rather_than_reading_it(self):
        doc = _doc()
        redirected = [p for p in doc["properties"]
                      if any("studio6.com" in (a.get("final_url") or "")
                             for a in p["http_access_result"])]
        assert redirected
        for prop in redirected:
            assert not prop["acquired"]
            assert prop["publication_grade_result"]["confirmed"] is False


class TestTheFreeStayAudit:
    def test_a_zero_fee_must_be_stated_not_inferred(self):
        """For a brand whose proposition is that pets stay free, a reader that
        found nothing and a property that charges nothing look identical."""
        inferred = M6.free_stay_audit([{
            "identity_key": "x",
            "policy_surface_result": {"excerpt": "Pets Allowed Coin Laundry"},
            "extraction": {"pets_allowed": True, "pet_fee": 0}}])
        assert inferred["verdict"] == "ZERO_FEE_INFERRED"

    def test_absence_of_a_fee_is_not_a_zero_fee(self):
        out = M6.free_stay_audit([{
            "identity_key": "x",
            "policy_surface_result": {"excerpt": "Pets Allowed Coin Laundry"},
            "extraction": {"pets_allowed": True}}])
        assert out["verdict"] == "NO_INFERRED_ZERO_FEE"
        assert out["no_fee_and_source_silent"]

    def test_the_live_cohort_inferred_nothing(self):
        assert _doc()["free_stay_audit"]["verdict"] == "NO_INFERRED_ZERO_FEE"


# --------------------------------------------------------------------------- #
# Method, and nothing else moved
# --------------------------------------------------------------------------- #

class TestTheTestMeasuredFirecrawlAlone:
    def test_it_reuses_the_earlier_construction_and_audits(self):
        assert M6.WY.test_registry is WY.test_registry
        assert M6.WY._observe is WY._observe
        assert M6.IHG.aggregate_audit is not None

    def test_the_override_forbids_both_bright_data_lanes(self):
        row = WY.test_registry("MOTEL6", "generic")["brands"]["MOTEL6"]
        assert row["provider"] == PROVIDERS.FIRECRAWL
        assert row["fallback_providers"] == []
        assert PROVIDERS.BRIGHTDATA_BROWSER in row["forbidden_providers"]
        assert PROVIDERS.BRIGHTDATA_WEB_UNLOCKER in row["forbidden_providers"]

    def test_it_used_the_existing_generic_reader(self):
        """There is no dedicated Motel 6 reader, and inventing one to make the
        test pass would have measured the reader, not the provider."""
        assert M6.READER == "generic"
        assert WY.test_registry("MOTEL6", "generic")["brands"]["MOTEL6"]["reader"] \
            == "generic"

    def test_no_bright_data_attempt_was_made(self):
        doc = _doc()
        assert doc["cost"]["bright_data_attempts"] == 0
        assert doc["cost"]["bright_data_usd"] == 0.0
        for prop in doc["properties"]:
            for provider in prop["providers_tried"]:
                assert not provider.startswith("brightdata"), prop["identity_key"]

    def test_it_records_that_provider_and_reader_are_entangled_here(self):
        """A failure on this lane could belong to either, and the report says
        so rather than resolving the ambiguity in the provider's favour."""
        note = _doc()["what_makes_this_brand_different"]
        assert "no_dedicated_reader" in note
        assert "could belong to either" in note["no_dedicated_reader"]


class TestNothingElseMoved:
    @pytest.mark.parametrize("brand,provider", [
        ("CHOICE", PROVIDERS.FIRECRAWL),
        ("WYNDHAM", PROVIDERS.FIRECRAWL),
        ("IHG", PROVIDERS.FIRECRAWL),
        ("MARRIOTT", PROVIDERS.BRIGHTDATA_BROWSER),
        ("HILTON", PROVIDERS.BRIGHTDATA_BROWSER),
        ("RED_ROOF", PROVIDERS.BRIGHTDATA_BROWSER),
        ("MOTEL6", PROVIDERS.BRIGHTDATA_BROWSER),
    ])
    def test_every_brand_route_is_where_it_was(self, brand, provider):
        assert REGISTRY.load()["brands"][brand]["provider"] == provider

    def test_the_default_and_domains_are_untouched(self):
        registry = REGISTRY.load()
        assert registry["default"]["provider"] == PROVIDERS.BRIGHTDATA_BROWSER
        assert set(registry["domains"]) == {"www.choicehotels.com"}

    def test_the_failure_taxonomy_is_untouched(self):
        from scripts.pettripfinder.acquisition import failures as F
        assert F.ESCALATING | F.TERMINAL == set(F.FAILURES)
        assert not F.may_escalate(F.POLICY_NOT_FOUND)
        assert F.may_escalate(F.UNEXPECTED_PAGE)

    def test_milwaukee_still_has_no_policy_authority_shard(self):
        shard = (REPO_ROOT / "launch_packages" / "pettripfinder"
                 / "hotel_policy_facts_milwaukee-wi.json")
        assert not shard.exists()
