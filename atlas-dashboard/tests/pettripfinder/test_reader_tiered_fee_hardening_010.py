"""PTF-POLICY-READER-TIERED-FEE-HARDENING-010 -- a fee may not be flattened.

The defect: Staybridge Milwaukee Airport South prices pets at 50 USD for stays
of 1 to 6 nights and 150 USD for stays over 7, and the reader published 5000.
That record was publication-grade, internally consistent, and understated a
week-long stay by 100 USD -- the most dangerous shape a bad record can take,
because nothing about it looks wrong.

The fix routes tiered fees through the withholding machinery that already
existed for weight-conditioned fees. Nothing new was invented and no schema
changed: the vocabulary holds one amount, the surface stated several, so no
amount is asserted and the tiers survive in the evidence quote.

Two directions have to hold, and the second is the one that costs data if it
breaks: a tier must never be published, AND a cap, a simple fee and a
single-priced policy that merely mentions a night range must never be withheld.
Withholding a fact the schema can hold is also a defect -- a quieter one.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.pettripfinder.brightdata import policy_reading as PR
from scripts.pettripfinder.brightdata import tiered_fee_corpus_010 as CORPUS
from scripts.pettripfinder.contracts import enums

REPO_ROOT = Path(__file__).resolve().parents[2]
REPORTS = REPO_ROOT / "launch_packages" / "pettripfinder" / "markets" / "reports"
DIFFERENTIAL = REPORTS / "ptf_reader_differential_010.json"
ROUTES_PATH = (REPO_ROOT / "scripts" / "pettripfinder" / "acquisition"
               / "routes.json")


def _read(text: str):
    reading = PR.parse(text, strategy="test")
    return reading, PR.to_extraction(reading, location="")


def _fields(text: str):
    _reading, result = _read(text)
    return dict(result.extraction), dict(result.withheld), result


# --------------------------------------------------------------------------- #
# 1 & 2. Tiered fees cannot be flattened
# --------------------------------------------------------------------------- #

class TestTieredFeesAreNeverFlattened:
    def test_the_staybridge_duration_tier_is_withheld(self):
        """The live defect. 5000 was the FIRST TIER, published as the price."""
        case = CORPUS.get("staybridge_tiered_nights")
        extraction, withheld, _ = _fields(case["text"])
        assert "pet_fee" not in extraction
        assert extraction.get("fee_basis") is None
        assert withheld["pet_fee"] == enums.SCHEMA_CANNOT_REPRESENT
        assert withheld["fee_basis"] == enums.SCHEMA_CANNOT_REPRESENT

    def test_no_tiered_case_in_the_corpus_publishes_an_amount(self):
        for name in CORPUS.TIERED_CASES:
            case = CORPUS.get(name)
            extraction, withheld, _ = _fields(case["text"])
            assert "pet_fee" not in extraction, name
            assert withheld.get("pet_fee"), name

    def test_a_multi_pet_price_ladder_is_withheld(self):
        """15USD one dog / 25USD two dogs is two prices for the same stay."""
        case = CORPUS.get("travelodge_tiered_pets_and_weekly")
        extraction, withheld, _ = _fields(case["text"])
        assert "pet_fee" not in extraction
        assert withheld.get("pet_fee")

    def test_the_reason_is_recorded_as_a_flag_not_silently(self):
        _reading, result = _read(CORPUS.get("staybridge_tiered_nights")["text"])
        assert "FLAG_TIERED_FEE" in {f.get("code") for f in (result.flags or [])}

    def test_the_detector_needs_both_a_qualifier_and_two_prices(self):
        """Either alone is not a tier, and withholding on one alone would
        delete facts the schema holds correctly."""
        assert PR._fee_is_tiered(
            "50 USD for stays 1 to 6 nights, 150 USD for stays over 7 nights.")
        # qualifier, one price
        assert not PR._fee_is_tiered(
            "A 50 USD fee applies for stays 1 to 6 nights.")
        # two prices, no qualifier
        assert not PR._fee_is_tiered(
            "25 USD nightly. Max 75 USD per stay.")


# --------------------------------------------------------------------------- #
# 3, 4 & 5. What must NOT change
# --------------------------------------------------------------------------- #

class TestRepresentableFeesAreUntouched:
    @pytest.mark.parametrize("name", CORPUS.SIMPLE_CASES)
    def test_a_representable_fee_still_publishes(self, name):
        case = CORPUS.get(name)
        extraction, _withheld, _ = _fields(case["text"])
        assert extraction.get("pet_fee") is not None, name

    def test_a_capped_per_night_fee_survives_intact(self):
        """25 USD nightly with a 75 USD ceiling is ONE price with a cap, and
        the schema has a field for it. Reading it as a tier would delete a
        fact -- the quieter half of this defect class."""
        extraction, withheld, _ = _fields(
            CORPUS.get("laquinta_per_night_with_cap")["text"])
        assert extraction["pet_fee"] == 2500
        assert extraction["fee_basis"] == enums.BASIS_PER_NIGHT
        assert "pet_fee" not in withheld

    def test_a_per_stay_fee_survives_intact(self):
        extraction, _w, _ = _fields(CORPUS.get("brookfield_per_stay")["text"])
        assert extraction["pet_fee"] == 10000
        assert extraction["fee_basis"] == enums.BASIS_PER_STAY

    def test_the_weight_conditioned_withholding_still_works(self):
        """The mechanism this fix borrowed must not have been disturbed."""
        extraction, withheld, _ = _fields(
            CORPUS.get("weight_conditioned_fee")["text"])
        assert "pet_fee" not in extraction
        assert withheld["pet_fee"] == enums.SCHEMA_CANNOT_REPRESENT


# --------------------------------------------------------------------------- #
# 6. Evidence survives a withholding
# --------------------------------------------------------------------------- #

class TestEvidenceSurvivesWithholding:
    def test_the_raw_policy_text_is_still_attached(self):
        case = CORPUS.get("staybridge_tiered_nights")
        reading, result = _read(case["text"])
        assert reading.block_text == PR.collapse(case["text"])
        assert "150 USD for stays over 7 nights" in reading.block_text

    def test_the_other_facts_on_the_surface_are_still_published(self):
        """Withholding the fee must not throw away the weight, the count or
        the species the same sentence stated."""
        extraction, _w, _ = _fields(
            CORPUS.get("staybridge_tiered_nights")["text"])
        assert extraction["weight_limit"]["value"] == 80.0
        assert extraction["pet_count_limit"] == 2
        assert extraction["species_allowed"] == ["dog"]
        assert extraction["pets_allowed"] is True


# --------------------------------------------------------------------------- #
# 7-10. Weight
# --------------------------------------------------------------------------- #

class TestWeightRecognition:
    def test_the_ihg_40lb_form_is_recognised(self):
        extraction, _w, _ = _fields(CORPUS.get("weight_ihg_40lb")["text"])
        assert extraction["weight_limit"] == {"value": 40.0, "unit": enums.UNIT_LB}

    def test_the_ihg_50lb_form_is_recognised(self):
        extraction, _w, _ = _fields(CORPUS.get("weight_ihg_50lb")["text"])
        assert extraction["weight_limit"] == {"value": 50.0, "unit": enums.UNIT_LB}

    @pytest.mark.parametrize("name", [
        c["case"] for c in CORPUS.CASES
        if c["family"] == "WEIGHT" and "expect_weight" in c])
    def test_every_supported_weight_form_reads_the_stated_number(self, name):
        case = CORPUS.get(name)
        extraction, _w, _ = _fields(case["text"])
        assert extraction["weight_limit"]["value"] == case["expect_weight"], name

    def test_a_combined_room_limit_never_becomes_a_per_pet_limit(self):
        """100 lbs across all pets is not 100 lbs per pet."""
        extraction, _w, _ = _fields(CORPUS.get("weight_combined_room")["text"])
        assert "weight_limit" not in extraction

    def test_an_explicit_no_limit_does_not_become_a_limit(self):
        extraction, _w, _ = _fields(CORPUS.get("weight_explicit_none")["text"])
        assert "weight_limit" not in extraction

    def test_silence_stays_silence(self):
        extraction, _w, _ = _fields(CORPUS.get("weight_not_stated")["text"])
        assert "weight_limit" not in extraction

    def test_ambiguous_size_language_never_becomes_a_number(self):
        extraction, _w, _ = _fields(CORPUS.get("weight_ambiguous_small")["text"])
        assert "weight_limit" not in extraction

    def test_the_added_connector_cannot_break_what_already_matched(self):
        """The fix added one optional token to one pattern. Every form that
        parsed before must parse to the same number."""
        for text, want in (("Max weight 75 lbs", 75.0),
                           ("Maximum 50 pounds each.", 50.0),
                           ("Pets under 30 lbs are welcome.", 30.0),
                           ("Dogs up to 60 lbs allowed.", 60.0),
                           ("must weigh less than 80 lbs.", 80.0),
                           ("75lbs or less per pet.", 75.0)):
            reading = PR.parse(text, strategy="t")
            assert reading.weight_value == want, text


# --------------------------------------------------------------------------- #
# 11-14. No regression, no routing change, no authority change
# --------------------------------------------------------------------------- #

class TestTheChangeIsNarrow:
    def _doc(self):
        if not DIFFERENTIAL.is_file():
            pytest.skip("differential not run in this worktree")
        return json.loads(DIFFERENTIAL.read_text(encoding="utf-8-sig"))

    def test_every_focused_case_meets_its_recorded_expectation(self):
        d = self._doc()["focused_regression"]
        assert d["failing_expectation"] == []

    def test_only_the_intended_cases_changed(self):
        """Four changes: the tiered fee withheld, and three weight forms that
        were being missed. Anything else is collateral damage."""
        rows = self._doc()["focused_regression"]["rows"]
        changed = sorted(r["case"] for r in rows if r["changed"])
        assert changed == ["holiday_inn_express_tiered_nights",
                           "staybridge_tiered_nights",
                           "weight_ihg_40lb", "weight_ihg_50lb"]

    def test_the_corpus_wide_blast_radius_is_three_records(self):
        c = self._doc()["corpus_dry_run"]
        assert c["unique_policy_texts_scanned"] > 50
        assert c["fee_output_changed"] == 1
        assert c["weight_output_changed"] == 2
        assert set(c["changes_by_brand"]) == {"IHG"}

    def test_no_record_newly_publishes_a_fee_it_did_not_before(self):
        """The fix may only make the reader quieter about fees, never louder."""
        assert self._doc()["corpus_dry_run"]["newly_structured"] == 0

    def test_the_dry_run_wrote_no_authority(self):
        assert self._doc()["corpus_dry_run"]["authority_written"] is False

    def test_routing_is_untouched_by_a_reader_change(self):
        from scripts.pettripfinder.acquisition import registry as REGISTRY
        from scripts.pettripfinder.acquisition import providers as PROVIDERS
        registry = REGISTRY.load()
        assert registry["brands"]["CHOICE"]["provider"] == PROVIDERS.FIRECRAWL
        assert registry["brands"]["WYNDHAM"]["provider"] == PROVIDERS.FIRECRAWL
        assert registry["brands"]["IHG"]["provider"] == PROVIDERS.FIRECRAWL
        assert registry["brands"]["MARRIOTT"]["provider"] == \
            PROVIDERS.BRIGHTDATA_BROWSER
        assert registry["brands"]["HILTON"]["provider"] == \
            PROVIDERS.BRIGHTDATA_BROWSER
        assert registry["default"]["provider"] == PROVIDERS.BRIGHTDATA_BROWSER
        assert registry["version"] == 4

    def test_no_provider_configuration_changed(self):
        from scripts.pettripfinder.acquisition import providers as PROVIDERS
        from scripts.pettripfinder.acquisition import firecrawl_capture as FC
        assert set(PROVIDERS.implemented()) == {
            PROVIDERS.BRIGHTDATA_BROWSER, PROVIDERS.BRIGHTDATA_WEB_UNLOCKER,
            PROVIDERS.FIRECRAWL}
        assert PROVIDERS.get(PROVIDERS.FIRECRAWL).capture_kwargs["profile"] is \
            FC.ROUTED_PROFILE

    def test_running_the_reader_writes_nothing_anywhere(self):
        """A reader is a pure function of its text. If reading a policy could
        write, a test run would mutate authority."""
        import inspect
        source = inspect.getsource(PR)
        assert "write_text" not in source
        assert "write_bytes" not in source
        assert "open(" not in source.replace("# ", "")


# --------------------------------------------------------------------------- #
# The corpus itself
# --------------------------------------------------------------------------- #

class TestTheCorpusIsReal:
    def test_every_case_names_a_source_and_a_reason(self):
        for case in CORPUS.CASES:
            assert case["source"].strip(), case["case"]
            assert case["why"].strip(), case["case"]
            assert case["text"].strip(), case["case"]

    def test_it_covers_the_families_the_work_order_named(self):
        families = {c["family"] for c in CORPUS.CASES}
        for required in ("TIERED_DURATION", "TIERED_COUNT", "CONDITIONAL_WEIGHT",
                         "SIMPLE", "SIMPLE_PER_STAY", "CAPPED", "WEIGHT"):
            assert required in families, required

    def test_it_has_at_least_two_already_correct_tiered_cases(self):
        """Proving a fix on the broken case alone risks breaking the ones that
        were already right."""
        already = [c for c in CORPUS.CASES
                   if c["family"].startswith("TIERED")
                   and c["case"] != "staybridge_tiered_nights"]
        assert len(already) >= 2
