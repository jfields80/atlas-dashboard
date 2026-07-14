"""Recipe-completion tests (AES-WEB-002J.1; AES-WEB-002 §26.3-26.5, §26.7-
26.13, §6.1).

Covers the ten PageRole recipe tables AES-WEB-002J.1 adds to
``constants/components.py`` -- city, city-category, search-results,
comparison, best-of, lead-gen-landing, claim-listing, sponsor-page,
submission, correction -- completing the recipe-table gap tracked since
AES-WEB-002A and closing the Implementation Roadmap's "002J MVP
integration: All recipes end-to-end" entry. Structure mirrors
test_catalog_wave6.py's ``TestSecondaryRecipeTables`` /
``TestDoesNotModifyEarlierWaveRecipeTables`` classes and
test_selector_pipeline.py's ``TestRealRecipeResolution``: real-registry
resolution proof, not a hand-pinned manifest. No live recipe/selection
pipeline or Component Engine is exercised beyond the selector itself
(component_engine.py does not exist yet, matching every prior wave's own
disposition of this question).
"""

from __future__ import annotations

from engines.website_generation.contracts.enums import (
    CommercialPurpose,
    PageRole,
    RegionKind,
)
from engines.website_generation.contracts.errors import ComponentResolutionError
from engines.website_generation.components.registry import build_default_registry
from engines.website_generation.components.selection import (
    ComponentSelector,
    LifecycleBuildFlags,
    SlotSelectionRequest,
)
from engines.website_generation.constants import components as constants_components
from engines.website_generation.constants.components import (
    _UNBUILT_FAMILY_SENTINEL,
    BEST_OF_RECIPE_SLOTS,
    BUSINESS_PROFILE_RECIPE_SLOTS,
    CATEGORY_RECIPE_SLOTS,
    CITY_CATEGORY_RECIPE_SLOTS,
    CITY_RECIPE_SLOTS,
    CLAIM_LISTING_RECIPE_SLOTS,
    COLLECTION_RECIPE_SLOTS,
    COMPARISON_RECIPE_SLOTS,
    CORRECTION_RECIPE_SLOTS,
    EDITORIAL_GUIDE_RECIPE_SLOTS,
    HOME_RECIPE_SLOTS,
    LEAD_GEN_LANDING_RECIPE_SLOTS,
    REGIONAL_HUB_RECIPE_SLOTS,
    SEARCH_RESULTS_RECIPE_SLOTS,
    SERVICE_AREA_RECIPE_SLOTS,
    SPONSOR_PAGE_RECIPE_SLOTS,
    SUBMISSION_RECIPE_SLOTS,
    VERIFICATION_RECIPE_SLOTS,
)

_COMPAT_OK = {"renderer": "1.0.0", "token_schema": "1.0.0", "registry_schema": "1.0.0"}
_FLAGS_ALLOW_PROPOSED = LifecycleBuildFlags(allow_proposed=True)

_NEW_TABLES = {
    "CITY_RECIPE_SLOTS": CITY_RECIPE_SLOTS,
    "CITY_CATEGORY_RECIPE_SLOTS": CITY_CATEGORY_RECIPE_SLOTS,
    "SEARCH_RESULTS_RECIPE_SLOTS": SEARCH_RESULTS_RECIPE_SLOTS,
    "COMPARISON_RECIPE_SLOTS": COMPARISON_RECIPE_SLOTS,
    "BEST_OF_RECIPE_SLOTS": BEST_OF_RECIPE_SLOTS,
    "LEAD_GEN_LANDING_RECIPE_SLOTS": LEAD_GEN_LANDING_RECIPE_SLOTS,
    "CLAIM_LISTING_RECIPE_SLOTS": CLAIM_LISTING_RECIPE_SLOTS,
    "SPONSOR_PAGE_RECIPE_SLOTS": SPONSOR_PAGE_RECIPE_SLOTS,
    "SUBMISSION_RECIPE_SLOTS": SUBMISSION_RECIPE_SLOTS,
    "CORRECTION_RECIPE_SLOTS": CORRECTION_RECIPE_SLOTS,
}

_EXPECTED_SLOT_COUNTS = {
    "CITY_RECIPE_SLOTS": 6,
    "CITY_CATEGORY_RECIPE_SLOTS": 8,
    "SEARCH_RESULTS_RECIPE_SLOTS": 7,
    "COMPARISON_RECIPE_SLOTS": 6,
    "BEST_OF_RECIPE_SLOTS": 5,
    "LEAD_GEN_LANDING_RECIPE_SLOTS": 4,
    "CLAIM_LISTING_RECIPE_SLOTS": 6,
    "SPONSOR_PAGE_RECIPE_SLOTS": 7,
    "SUBMISSION_RECIPE_SLOTS": 4,
    "CORRECTION_RECIPE_SLOTS": 5,
}

_SLOT_SCHEMA_KEYS = frozenset(HOME_RECIPE_SLOTS[0].keys())


def _to_request(slot: dict) -> SlotSelectionRequest:
    return SlotSelectionRequest(
        slot_id=slot["slot_id"],
        page_role=PageRole(slot["page_role"]),
        purpose=CommercialPurpose(slot["purpose"]) if slot["purpose"] else None,
        required_region=(
            RegionKind(slot["required_region"]) if slot["required_region"] else None
        ),
        required_prop_names=slot["required_prop_names"],
        required_slot_names=slot["required_slot_names"],
        monetization_eligible=slot["monetization_eligible"],
        fallback_component_id=slot["fallback_component_id"],
        required=slot["required"],
    )


def _resolve(slots):
    registry = build_default_registry()
    requests = [_to_request(s) for s in slots]
    trace = ComponentSelector().select(
        registry,
        requests,
        compatibility_versions=_COMPAT_OK,
        lifecycle_flags=_FLAGS_ALLOW_PROPOSED,
    )
    return {s.slot_id: s.chosen_component_id for s in trace.slots}


class TestNewRecipeTablesExist:
    """Presence, slot counts, and schema shape for all ten new tables."""

    def test_all_ten_tables_exist_with_expected_slot_counts(self):
        for name, table in _NEW_TABLES.items():
            assert len(table) == _EXPECTED_SLOT_COUNTS[name], name

    def test_every_slot_uses_the_established_schema(self):
        for name, table in _NEW_TABLES.items():
            for slot in table:
                assert set(slot.keys()) == _SLOT_SCHEMA_KEYS, (name, slot.get("slot_id"))

    def test_every_slot_page_role_matches_its_table(self):
        expected_role = {
            "CITY_RECIPE_SLOTS": "city",
            "CITY_CATEGORY_RECIPE_SLOTS": "city-category",
            "SEARCH_RESULTS_RECIPE_SLOTS": "search-results",
            "COMPARISON_RECIPE_SLOTS": "comparison",
            "BEST_OF_RECIPE_SLOTS": "best-of",
            "LEAD_GEN_LANDING_RECIPE_SLOTS": "lead-gen-landing",
            "CLAIM_LISTING_RECIPE_SLOTS": "claim-listing",
            "SPONSOR_PAGE_RECIPE_SLOTS": "sponsor-page",
            "SUBMISSION_RECIPE_SLOTS": "submission",
            "CORRECTION_RECIPE_SLOTS": "correction",
        }
        for name, table in _NEW_TABLES.items():
            for slot in table:
                assert slot["page_role"] == expected_role[name], (name, slot["slot_id"])
                PageRole(slot["page_role"])  # every value is a valid enum member

    def test_slot_ids_unique_within_each_table(self):
        for name, table in _NEW_TABLES.items():
            slot_ids = [s["slot_id"] for s in table]
            assert len(slot_ids) == len(set(slot_ids)), name

    def test_sentinel_gated_slots_use_the_shared_sentinel_and_are_optional(self):
        for name, table in _NEW_TABLES.items():
            for slot in table:
                if slot["required_slot_names"] == _UNBUILT_FAMILY_SENTINEL:
                    assert slot["required_slot_names"] is _UNBUILT_FAMILY_SENTINEL, (
                        name, slot["slot_id"],
                    )
                    assert slot["required"] is False, (name, slot["slot_id"])
                    assert slot["fallback_component_id"] == "", (name, slot["slot_id"])

    def test_every_required_slot_declares_a_fallback(self):
        # Every required slot in this delivery carries a guaranteed-
        # satisfiable fallback (the belt-and-suspenders posture
        # SERVICE_AREA_RECIPE_SLOTS/REGIONAL_HUB_RECIPE_SLOTS use), except
        # the handful that mirror CATEGORY_RECIPE_SLOTS's own
        # "pagination"/"zero_results" slots exactly (same real candidate,
        # same no-fallback-needed precedent).
        no_fallback_ok = {
            ("CITY_RECIPE_SLOTS", "zero_results"),
            ("CITY_CATEGORY_RECIPE_SLOTS", "zero_results"),
            ("SEARCH_RESULTS_RECIPE_SLOTS", "pagination"),
            ("SEARCH_RESULTS_RECIPE_SLOTS", "zero_results"),
        }
        for name, table in _NEW_TABLES.items():
            for slot in table:
                if not slot["required"]:
                    continue
                if (name, slot["slot_id"]) in no_fallback_ok:
                    continue
                assert slot["fallback_component_id"] != "", (name, slot["slot_id"])


class TestNewRecipeTablesResolveAgainstRealRegistry:
    """Real-registry resolution proof via the production §14.2 selector --
    mirrors test_selector_pipeline.py's TestRealRecipeResolution discipline
    for HOME_RECIPE_SLOTS/CATEGORY_RECIPE_SLOTS."""

    def test_no_table_raises_component_resolution_error(self):
        for name, table in _NEW_TABLES.items():
            try:
                _resolve(table)
            except ComponentResolutionError as exc:  # pragma: no cover - diagnostic
                raise AssertionError(f"{name} raised: {exc}") from exc

    def test_every_required_slot_resolves_to_a_real_or_fallback_component(self):
        for name, table in _NEW_TABLES.items():
            chosen = _resolve(table)
            for slot in table:
                if slot["required"]:
                    assert chosen[slot["slot_id"]] != "", (name, slot["slot_id"])

    def test_sentinel_gated_optional_slots_drop_to_empty(self):
        for name, table in _NEW_TABLES.items():
            chosen = _resolve(table)
            for slot in table:
                if slot["required_slot_names"] == _UNBUILT_FAMILY_SENTINEL:
                    assert chosen[slot["slot_id"]] == "", (name, slot["slot_id"])

    def test_resolution_is_deterministic(self):
        for table in _NEW_TABLES.values():
            assert _resolve(table) == _resolve(table)

    def test_city_recipe_resolves_required_slots_to_real_components(self):
        chosen = _resolve(CITY_RECIPE_SLOTS)
        assert chosen["hero"] == "hero.local.standard"
        assert chosen["categories_in_city_navigator"] == "directory.categories.grid"
        assert chosen["listing_cards"] == "listing.card.standard"
        assert chosen["nearby_cities_parent_region"] == "seo.local-links.cities"
        assert chosen["zero_results"] == "status.results.zero"
        assert chosen["local_facts"] == ""

    def test_city_category_recipe_resolves_required_slots_to_real_components(self):
        chosen = _resolve(CITY_CATEGORY_RECIPE_SLOTS)
        assert chosen["hero"] == "hero.local.standard"
        assert chosen["filters"] == "directory.filters.panel"
        assert chosen["results_summary"] == "directory.results.summary"
        assert chosen["listing_cards"] == "listing.card.standard"
        assert chosen["nearby_city_links"] == "seo.local-links.cities"
        assert chosen["parent_category_links"] == "seo.local-links.categories"
        assert chosen["zero_results"] == "status.results.zero"

    def test_search_results_recipe_resolves_required_slots_to_real_components(self):
        chosen = _resolve(SEARCH_RESULTS_RECIPE_SLOTS)
        assert chosen["results_header"] == "directory.results.summary"
        assert chosen["filters"] == "directory.filters.panel"
        assert chosen["sort"] == "directory.sort.control"
        assert chosen["listing_rows_or_cards"] == "listing.card.standard"
        assert chosen["pagination"] == "nav.pagination.standard"
        assert chosen["zero_results"] == "status.results.zero"
        assert chosen["related_searches"] == ""

    def test_comparison_recipe_resolves_to_real_component_or_fallback(self):
        chosen = _resolve(COMPARISON_RECIPE_SLOTS)
        assert chosen["comparison_table"] == "content.table.comparison"
        assert chosen["hero"] == "layout.section.container"
        assert chosen["methodology"] == "layout.section.container"
        assert chosen["page_cta_band"] == "atom.button.action"
        assert chosen["empty_comparison"] == ""
        assert chosen["related_links"] == ""

    def test_best_of_recipe_resolves_to_fallback_for_every_known_gap(self):
        # Every required slot in best-of is a documented pre-existing gap
        # (no listing.*/seo.* component declares "best-of"); each still
        # resolves via its guaranteed Wave 1/2 fallback.
        chosen = _resolve(BEST_OF_RECIPE_SLOTS)
        assert chosen["hero"] == "layout.section.container"
        assert chosen["ranking_methodology"] == "layout.section.container"
        assert chosen["ranked_listing_cards"] == "layout.card.shell"
        assert chosen["related_best_of_links"] == "layout.stack.standard"
        assert chosen["featured_block"] == ""

    def test_sponsor_page_recipe_resolves_required_slots_to_real_components(self):
        chosen = _resolve(SPONSOR_PAGE_RECIPE_SLOTS)
        assert chosen["audience_statistics"] == "trust.statistics.strip"
        assert chosen["sponsor_inquiry_cta"] == "cta.sponsor.inquiry"
        assert chosen["sponsorship_pricing"] == "commerce.pricing.sponsorship"
        assert chosen["paid_placement_disclosure"] == "monetization.disclosure.advertising"
        assert chosen["states"] == ""

    def test_claim_listing_recipe_resolves_required_slots_to_real_components(self):
        chosen = _resolve(CLAIM_LISTING_RECIPE_SLOTS)
        assert chosen["claim_form"] == "form.claim.standard"
        assert chosen["upgrade_preview"] == "monetization.prompt.upgrade"
        assert chosen["claim_state"] == "status.listing.pending"
        assert chosen["listing_preview"] == ""

    def test_lead_gen_landing_recipe_resolves_required_slots_to_real_components(self):
        chosen = _resolve(LEAD_GEN_LANDING_RECIPE_SLOTS)
        assert chosen["trust_adjacent_to_form"] == "trust.statistics.strip"
        assert chosen["lead_quote_form"] == "form.lead.quote"
        assert chosen["social_proof_listings"] == ""

    def test_submission_recipe_resolves_required_slots_to_real_components(self):
        chosen = _resolve(SUBMISSION_RECIPE_SLOTS)
        assert chosen["submission_form"] == "form.submission.listing"
        assert chosen["paid_fast_track"] == "monetization.disclosure.advertising"
        assert chosen["states"] == ""

    def test_correction_recipe_resolves_required_slots_to_real_components(self):
        chosen = _resolve(CORRECTION_RECIPE_SLOTS)
        assert chosen["correction_form"] == "form.correction.standard"
        assert chosen["data_source_disclosure"] == "legal.statement.standard"
        assert chosen["states"] == ""
        # Regression guard for the purpose=ORIENT fix: this slot must NOT
        # collide with correction_form's own form.correction.standard.
        assert chosen["listing_being_corrected"] == "layout.card.shell"
        assert chosen["listing_being_corrected"] != chosen["correction_form"]


class TestNoAccidentalCrossSlotCollisions:
    """No two different slots within the same new recipe resolve to the
    same non-fallback real component -- would indicate an under-specified
    purpose/prop signature letting one slot's candidate leak into another's,
    the exact class of bug the correction recipe's listing_being_corrected
    slot required a purpose fix for."""

    def test_no_two_slots_share_a_non_fallback_real_component(self):
        for name, table in _NEW_TABLES.items():
            chosen = _resolve(table)
            seen = {}
            for slot in table:
                cid = chosen[slot["slot_id"]]
                if not cid or cid == slot["fallback_component_id"]:
                    continue
                assert cid not in seen, (name, seen.get(cid), slot["slot_id"], cid)
                seen[cid] = slot["slot_id"]


class TestDoesNotModifyEarlierRecipeTables:
    """AES-WEB-002J.1 is strictly additive -- continues the AMB-002F-02/
    AMB-002G-02/AMB-002H-02 precedent one final time."""

    def test_all_eight_earlier_tables_unchanged_by_slot_count(self):
        assert len(HOME_RECIPE_SLOTS) == 11  # AES-WEB-002K.1: +site_header/+site_footer
        assert len(CATEGORY_RECIPE_SLOTS) == 11  # AES-WEB-002K.1: +site_header/+site_footer
        assert len(BUSINESS_PROFILE_RECIPE_SLOTS) == 17  # AES-WEB-002K.1: +site_header/+site_footer
        assert len(EDITORIAL_GUIDE_RECIPE_SLOTS) == 5
        assert len(COLLECTION_RECIPE_SLOTS) == 3
        assert len(SERVICE_AREA_RECIPE_SLOTS) == 5
        assert len(VERIFICATION_RECIPE_SLOTS) == 5
        assert len(REGIONAL_HUB_RECIPE_SLOTS) == 6

    def test_known_sentinel_slots_on_earlier_tables_still_sentinel_gated(self):
        home = {s["slot_id"]: s for s in HOME_RECIPE_SLOTS}
        category = {s["slot_id"]: s for s in CATEGORY_RECIPE_SLOTS}
        profile = {s["slot_id"]: s for s in BUSINESS_PROFILE_RECIPE_SLOTS}
        verification = {s["slot_id"]: s for s in VERIFICATION_RECIPE_SLOTS}
        assert home["editorial_resources"]["required_slot_names"] == _UNBUILT_FAMILY_SENTINEL
        assert category["related_categories_cities"]["required_slot_names"] == _UNBUILT_FAMILY_SENTINEL
        assert profile["faqs"]["required_slot_names"] == _UNBUILT_FAMILY_SENTINEL
        assert profile["unavailable_state"]["required_slot_names"] == _UNBUILT_FAMILY_SENTINEL
        assert verification["pending_state"]["required_slot_names"] == _UNBUILT_FAMILY_SENTINEL


class TestAllEighteenPageRolesNowHaveARecipeTable:
    """The MVP-integration milestone signal: every PageRole enum member now
    resolves to exactly one recipe table in constants/components.py."""

    _TABLE_BY_ROLE = {
        "home": "HOME_RECIPE_SLOTS",
        "category": "CATEGORY_RECIPE_SLOTS",
        "city": "CITY_RECIPE_SLOTS",
        "city-category": "CITY_CATEGORY_RECIPE_SLOTS",
        "search-results": "SEARCH_RESULTS_RECIPE_SLOTS",
        "business-profile": "BUSINESS_PROFILE_RECIPE_SLOTS",
        "comparison": "COMPARISON_RECIPE_SLOTS",
        "best-of": "BEST_OF_RECIPE_SLOTS",
        "editorial-guide": "EDITORIAL_GUIDE_RECIPE_SLOTS",
        "collection": "COLLECTION_RECIPE_SLOTS",
        "service-area": "SERVICE_AREA_RECIPE_SLOTS",
        "lead-gen-landing": "LEAD_GEN_LANDING_RECIPE_SLOTS",
        "claim-listing": "CLAIM_LISTING_RECIPE_SLOTS",
        "sponsor-page": "SPONSOR_PAGE_RECIPE_SLOTS",
        "submission": "SUBMISSION_RECIPE_SLOTS",
        "correction": "CORRECTION_RECIPE_SLOTS",
        "verification": "VERIFICATION_RECIPE_SLOTS",
        "regional-hub": "REGIONAL_HUB_RECIPE_SLOTS",
    }

    def test_every_page_role_enum_member_is_covered(self):
        assert set(self._TABLE_BY_ROLE) == {role.value for role in PageRole}

    def test_every_mapped_table_exists_and_matches_its_role(self):
        for role_value, table_name in self._TABLE_BY_ROLE.items():
            table = getattr(constants_components, table_name)
            assert len(table) > 0, table_name
            assert all(s["page_role"] == role_value for s in table), table_name
