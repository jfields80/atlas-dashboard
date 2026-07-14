"""Wave 7 catalog tests (AES-WEB-002H; AES-WEB-002 §27.8, §15.2, §30.1).

Catalog completeness (exact IDs, versions, families, roles, variants,
count), definition validity, determinism (hash stability across order and
process restarts), compatibility metadata, registry lookups,
monetization/legal/status ethical-doctrine enforcement linkage, the new
disclosure-kind constants, the recipe-table non-modification guard
(AMB-002H-02), and the fixture-only "every §6.1 monetization cell
exercisable; every role's required-status components resolvable" proof
(§31 acceptance, AMB-002H-01/02/03 discipline) -- mirrors
test_catalog_wave5.py's and test_catalog_wave6.py's structure.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from engines.website_generation.contracts.artifacts import (
    canonical_json,
    model_to_dict,
)
from engines.website_generation.contracts.enums import (
    CommercialPurpose,
    ComponentFamily,
    LifecycleStatus,
    PageRole,
    PropType,
    RegionKind,
    SemanticElement,
    SlotCardinality,
)
from engines.website_generation.components.catalog.monetization_status import (
    WAVE7_COMPONENTS,
)
from engines.website_generation.components.registry import (
    REGISTERED_COMPONENTS,
    ComponentRegistry,
    build_default_registry,
    definition_fingerprint,
    validate_definition,
)
from engines.website_generation.constants import components as constants_components
from engines.website_generation.constants.components import (
    MONETIZATION_DISCLOSURE_KIND_ADVERTISING,
    MONETIZATION_DISCLOSURE_KIND_PREMIUM,
    MONETIZATION_DISCLOSURE_KIND_SPONSORED,
    MONETIZATION_DISCLOSURE_KIND_UPGRADE,
    MONETIZATION_DISCLOSURE_KINDS,
    _UNBUILT_FAMILY_SENTINEL,
)

APP_ROOT = Path(__file__).resolve().parents[3]

# The exact §27.8 Wave 7 inventory (lexicographic -- §15.2 ordering law).
EXPECTED_IDS = [
    "commerce.pricing.sponsorship",
    "legal.statement.standard",
    "monetization.disclosure.advertising",
    "monetization.prompt.upgrade",
    "monetization.ribbon.sponsor",
    "monetization.section.premium-profile",
    "status.listing.pending",
    "status.listing.unavailable",
]

EXPECTED_VARIANTS = {
    "commerce.pricing.sponsorship": ("cards", "table"),
    "legal.statement.standard": (),
    "monetization.disclosure.advertising": ("inline", "page-level"),
    "monetization.prompt.upgrade": (),
    "monetization.ribbon.sponsor": (),
    "monetization.section.premium-profile": (),
    "status.listing.pending": (),
    "status.listing.unavailable": (),
}

# §27.8 "Roles" column, resolved per the module docstring's documented
# interpretive resolutions.
EXPECTED_ROLE_COUNTS = {
    "commerce.pricing.sponsorship": 1,  # spon
    "legal.statement.standard": 18,  # ALL (§5.15 family-level statement)
    "monetization.disclosure.advertising": 16,  # ALL minus lead-gen-landing, verification
    "monetization.prompt.upgrade": 1,  # claim only (profile is P3)
    "monetization.ribbon.sponsor": 5,  # home, category, city, city-category, search-results
    "monetization.section.premium-profile": 1,  # prof
    "status.listing.pending": 2,  # prof, claim
    "status.listing.unavailable": 1,  # prof
}

EXPECTED_FAMILY = {
    "commerce.pricing.sponsorship": ComponentFamily.COMMERCE,
    "legal.statement.standard": ComponentFamily.LEGAL,
    "monetization.disclosure.advertising": ComponentFamily.MONETIZATION,
    "monetization.prompt.upgrade": ComponentFamily.MONETIZATION,
    "monetization.ribbon.sponsor": ComponentFamily.MONETIZATION,
    "monetization.section.premium-profile": ComponentFamily.MONETIZATION,
    "status.listing.pending": ComponentFamily.STATUS,
    "status.listing.unavailable": ComponentFamily.STATUS,
}

EXPECTED_CLASS_PREFIX = {
    "commerce.pricing.sponsorship": "ac-commerce",
    "legal.statement.standard": "ac-legal",
    "monetization.disclosure.advertising": "ac-monetization",
    "monetization.prompt.upgrade": "ac-monetization",
    "monetization.ribbon.sponsor": "ac-monetization",
    "monetization.section.premium-profile": "ac-monetization",
    "status.listing.pending": "ac-status",
    "status.listing.unavailable": "ac-status",
}

EXPECTED_GATES = {
    "commerce.pricing.sponsorship": ("CG-COM-006",),
    "legal.statement.standard": (),
    "monetization.disclosure.advertising": ("CG-COM-001",),
    "monetization.prompt.upgrade": ("CG-COM-004",),
    "monetization.ribbon.sponsor": ("CG-COM-001",),
    "monetization.section.premium-profile": ("CG-COM-012",),
    "status.listing.pending": ("CG-COM-004",),
    "status.listing.unavailable": ("CG-STR-006",),
}

# The four MONETIZATION-family components and the disclosure_kind each
# declares (§27.8 Wave 7 scope; see catalog module docstring).
EXPECTED_DISCLOSURE_KIND = {
    "monetization.disclosure.advertising": MONETIZATION_DISCLOSURE_KIND_ADVERTISING,
    "monetization.prompt.upgrade": MONETIZATION_DISCLOSURE_KIND_UPGRADE,
    "monetization.ribbon.sponsor": MONETIZATION_DISCLOSURE_KIND_SPONSORED,
    "monetization.section.premium-profile": MONETIZATION_DISCLOSURE_KIND_PREMIUM,
}


def _get(cid):
    return next(d for d in WAVE7_COMPONENTS if d.component_id == cid)


class TestCatalogCompleteness:
    def test_exact_component_ids(self):
        assert [d.component_id for d in WAVE7_COMPONENTS] == EXPECTED_IDS

    def test_exact_catalog_count(self):
        assert len(WAVE7_COMPONENTS) == 8  # §27.8 "Monetization, legal, and status (8)"
        # Wave 1 (15) + Wave 2 (8) + Wave 3 (9) + Wave 4 (12) + Wave 5 (13)
        # + Wave 6 (7) + Wave 7 (8) = 72 -- the full MVP catalog (§27.1).
        assert len(REGISTERED_COMPONENTS) == 72

    def test_exact_versions(self):
        assert all(d.component_version == "1.0.0" for d in WAVE7_COMPONENTS)

    def test_exact_family_assignments(self):
        for d in WAVE7_COMPONENTS:
            assert d.component_family is EXPECTED_FAMILY[d.component_id], (
                d.component_id
            )

    def test_family_counts(self):
        commerce = [d for d in WAVE7_COMPONENTS if d.component_family is ComponentFamily.COMMERCE]
        legal = [d for d in WAVE7_COMPONENTS if d.component_family is ComponentFamily.LEGAL]
        monetization = [d for d in WAVE7_COMPONENTS if d.component_family is ComponentFamily.MONETIZATION]
        status = [d for d in WAVE7_COMPONENTS if d.component_family is ComponentFamily.STATUS]
        assert len(commerce) == 1
        assert len(legal) == 1
        assert len(monetization) == 4
        assert len(status) == 2

    def test_exact_variant_names(self):
        for d in WAVE7_COMPONENTS:
            expected = EXPECTED_VARIANTS[d.component_id]
            assert tuple(sorted(d.supported_variants)) == expected, d.component_id

    def test_exact_role_counts_match_authority_table(self):
        for d in WAVE7_COMPONENTS:
            assert len(d.supported_page_roles) == EXPECTED_ROLE_COUNTS[
                d.component_id
            ], d.component_id

    def test_no_duplicate_ids_or_versions(self):
        keys = [(d.component_id, d.component_version) for d in WAVE7_COMPONENTS]
        assert len(keys) == len(set(keys))

    def test_no_duplicate_ids_or_versions_across_full_catalog(self):
        keys = [(d.component_id, d.component_version) for d in REGISTERED_COMPONENTS]
        assert len(keys) == len(set(keys))

    def test_lexicographic_tuple_order(self):
        ids = [d.component_id for d in REGISTERED_COMPONENTS]
        assert ids == sorted(ids)  # §15.2 ordering law

    def test_no_placeholder_values(self):
        text = canonical_json(
            [model_to_dict(d) for d in WAVE7_COMPONENTS]
        ).lower()
        for marker in ("todo", "tbd", "lorem", "dummy", "fixme", "xxx"):
            assert marker not in text, marker


class TestDefinitionValidity:
    def test_every_definition_passes_validate_definition(self):
        for d in WAVE7_COMPONENTS:
            validate_definition(d)

    def test_every_default_variant_exists(self):
        for d in WAVE7_COMPONENTS:
            if d.supported_variants:
                assert d.default_variant in d.supported_variants, d.component_id
            else:
                assert d.default_variant == "", d.component_id

    def test_lifecycle_is_proposed_until_emitters_exist(self):
        # Operator decision carried through 002B-002G and reaffirmed for
        # 002H (AES-WEB-002H architectural preflight, AMB-002H-01,
        # operator-approved): no renderer/gates package is built this wave;
        # no component is promoted to ACTIVE.
        for d in WAVE7_COMPONENTS:
            assert d.lifecycle_status is LifecycleStatus.PROPOSED

    def test_required_contract_fields_present(self):
        for d in WAVE7_COMPONENTS:
            assert d.analytics_contract.impression_id == d.component_id.replace(".", "-")
            assert d.rendering_contract.emitter_key == d.component_id + "@1"
            assert d.rendering_contract.class_prefix == EXPECTED_CLASS_PREFIX[d.component_id]
            assert d.description and d.display_name
            assert d.design_token_dependencies, d.component_id
            assert d.example_fixture_ids

    def test_fixture_ids_include_registration_minimum_set(self):
        minimum_suffixes = {
            "min", "full", "bad-prop", "bad-slot", "mobile", "long", "a11y",
        }
        for d in WAVE7_COMPONENTS:
            suffixes = {
                fid.replace("fx-%s-" % d.component_id, "")
                for fid in d.example_fixture_ids
            }
            assert minimum_suffixes <= suffixes, d.component_id

    def test_monetization_family_fixtures_include_sponsored_case(self):
        for d in WAVE7_COMPONENTS:
            if d.component_family is ComponentFamily.MONETIZATION:
                assert any(
                    fid.endswith("-sponsored") for fid in d.example_fixture_ids
                ), d.component_id

    def test_no_directory_contract_in_wave7(self):
        # §6.3's ListingKind semantics are Wave 4's domain; no Wave 7
        # component is listing-kind-bearing.
        for d in WAVE7_COMPONENTS:
            assert d.directory_contract is None, d.component_id

    def test_no_conversion_contract_in_wave7(self):
        # §27.8's RP column is blank for every row; see catalog module
        # docstring's documented interpretive resolution.
        for d in WAVE7_COMPONENTS:
            assert d.conversion_contract is None, d.component_id

    def test_monetization_contract_required_and_present_for_monetization_family_only(self):
        # §5.10/§15.2: only the MONETIZATION family requires a
        # monetization_contract; registry.validate_definition enforces this.
        for d in WAVE7_COMPONENTS:
            if d.component_family is ComponentFamily.MONETIZATION:
                assert d.monetization_contract is not None, d.component_id
                assert d.monetization_contract.requires_visible_disclosure is True
                assert d.monetization_contract.disclosure_kind == (
                    EXPECTED_DISCLOSURE_KIND[d.component_id]
                )
            else:
                assert d.monetization_contract is None, d.component_id

    def test_no_free_form_string_props(self):
        for d in WAVE7_COMPONENTS:
            for props in (d.required_props, d.optional_props):
                for name, spec in props.items():
                    assert isinstance(spec.prop_type, PropType), (d.component_id, name)

    def test_definitions_are_frozen_and_reject_extras(self):
        for d in WAVE7_COMPONENTS:
            with pytest.raises(Exception):
                d.component_id = "x.y.z"
            assert d.component_id != "x.y.z"

    def test_commerce_pricing_sponsorship_pricing_and_disclaimer_shape(self):
        d = _get("commerce.pricing.sponsorship")
        assert d.required_content_slots["pricing"].block_type == "PriceSpec"
        assert d.required_content_slots["pricing"].cardinality is SlotCardinality.ONE_TO_N
        assert d.required_content_slots["disclaimer"].block_type == "RichTextBlock"
        assert d.required_content_slots["disclaimer"].cardinality is SlotCardinality.EXACTLY_ONE
        assert d.quality_gate_requirements == ("CG-COM-006",)

    def test_status_listing_unavailable_reason_enum_and_recovery_links(self):
        d = _get("status.listing.unavailable")
        assert d.required_props["reason"].prop_type is PropType.STR_ENUM
        assert set(d.required_props["reason"].enum_values) == {
            "unavailable", "closed", "stale", "archived",
        }
        slot = d.required_content_slots["recovery_links"]
        assert slot.block_type == "LinkSpec"
        assert slot.cardinality is SlotCardinality.ONE_TO_N
        assert d.quality_gate_requirements == ("CG-STR-006",)

    def test_status_listing_pending_never_claims_verified(self):
        # E10: status.listing.pending is the honest interim state -- it
        # carries no verification-badge-shaped prop or slot of its own.
        d = _get("status.listing.pending")
        names = set(d.required_props) | set(d.optional_props)
        assert not any("verif" in n.lower() for n in names)
        assert d.accessibility_contract.live_region_role == "status"
        assert d.quality_gate_requirements == ("CG-COM-004",)

    def test_legal_statement_standard_kind_enum_and_heading_scope(self):
        d = _get("legal.statement.standard")
        assert d.required_props["kind"].prop_type is PropType.STR_ENUM
        assert set(d.required_props["kind"].enum_values) == {
            "privacy", "terms", "accessibility",
            "editorial-standards", "advertising", "data-source",
        }
        assert d.semantic_element is SemanticElement.ARTICLE
        assert d.seo_contract.heading_levels == (3, 4)
        assert d.supported_page_roles == tuple(PageRole)

    def test_monetization_ribbon_sponsor_roles_match_listing_card_union(self):
        # Documented interpretive resolution: exact union of
        # listing.card.featured's and listing.card.sponsored's own §27.5
        # roles (AES-WEB-002E).
        d = _get("monetization.ribbon.sponsor")
        assert set(d.supported_page_roles) == {
            PageRole.HOME, PageRole.CATEGORY, PageRole.CITY,
            PageRole.CITY_CATEGORY, PageRole.SEARCH_RESULTS,
        }

    def test_monetization_disclosure_advertising_excludes_forbidden_roles(self):
        # §6.1 Monetization column marks lead-gen-landing and verification
        # "F" (forbidden); the component must not claim eligibility there.
        d = _get("monetization.disclosure.advertising")
        assert PageRole.LEAD_GEN_LANDING not in d.supported_page_roles
        assert PageRole.VERIFICATION not in d.supported_page_roles
        assert len(d.supported_page_roles) == len(tuple(PageRole)) - 2

    def test_monetization_prompt_upgrade_excludes_p3_profile_usage(self):
        # §27.8: "claim, prof (owner contexts P3)" -- only the non-P3 claim
        # usage is in this wave's contract.
        d = _get("monetization.prompt.upgrade")
        assert d.supported_page_roles == (PageRole.CLAIM_LISTING,)
        assert PageRole.BUSINESS_PROFILE not in d.supported_page_roles


class TestDeterminism:
    def test_identical_catalog_identical_hash(self):
        assert (
            ComponentRegistry(WAVE7_COMPONENTS).registry_hash()
            == ComponentRegistry(WAVE7_COMPONENTS).registry_hash()
        )

    def test_registration_order_does_not_alter_hash(self):
        forward = ComponentRegistry(WAVE7_COMPONENTS).registry_hash()
        backward = ComponentRegistry(tuple(reversed(WAVE7_COMPONENTS))).registry_hash()
        assert forward == backward

    def test_full_catalog_hash_reproduces_across_process_restarts(self):
        code = (
            "from engines.website_generation.components import "
            "build_default_registry; print(build_default_registry().registry_hash())"
        )
        runs = {
            subprocess.run(
                [sys.executable, "-c", code],
                cwd=str(APP_ROOT), capture_output=True, text=True, check=True,
            ).stdout.strip()
            for _ in range(2)
        }
        assert len(runs) == 1
        assert runs == {build_default_registry().registry_hash()}

    def test_definition_fingerprints_stable_and_unique(self):
        prints = [definition_fingerprint(d) for d in WAVE7_COMPONENTS]
        assert prints == [definition_fingerprint(d) for d in WAVE7_COMPONENTS]
        assert len(set(prints)) == 8

    def test_earlier_waves_fingerprints_unchanged_by_wave7_addition(self):
        from engines.website_generation.components.catalog.layout_atoms import (
            WAVE1_COMPONENTS,
        )
        from engines.website_generation.components.catalog.navigation import (
            WAVE2_COMPONENTS,
        )
        from engines.website_generation.components.catalog.discovery import (
            WAVE3_COMPONENTS,
        )
        from engines.website_generation.components.catalog.listings_profiles import (
            WAVE4_COMPONENTS,
        )
        from engines.website_generation.components.catalog.trust_conversion import (
            WAVE5_COMPONENTS,
        )
        from engines.website_generation.components.catalog.seo_editorial import (
            WAVE6_COMPONENTS,
        )
        earlier = {
            d.component_id: definition_fingerprint(d)
            for d in WAVE1_COMPONENTS + WAVE2_COMPONENTS + WAVE3_COMPONENTS
            + WAVE4_COMPONENTS + WAVE5_COMPONENTS + WAVE6_COMPONENTS
        }
        r = build_default_registry()
        for component_id, expected_fp in earlier.items():
            got = r.get(component_id)
            assert definition_fingerprint(got) == expected_fp, component_id


class TestCompatibilityMetadata:
    def test_compatibility_axes_pinned(self):
        for d in WAVE7_COMPONENTS:
            assert set(d.compatibility_range) == {
                "renderer", "token_schema", "registry_schema",
            }, d.component_id

    def test_gate_requirements_match_authority_table(self):
        for d in WAVE7_COMPONENTS:
            assert d.quality_gate_requirements == EXPECTED_GATES[d.component_id], (
                d.component_id
            )

    def test_page_roles_and_region_kinds_typed(self):
        for d in WAVE7_COMPONENTS:
            assert all(isinstance(r, PageRole) for r in d.supported_page_roles)
            assert all(isinstance(r, RegionKind) for r in d.allowed_parent_regions)


class TestRegistryLookups:
    def test_every_wave7_component_resolvable(self):
        r = build_default_registry()
        for d in WAVE7_COMPONENTS:
            got = r.get(d.component_id, "1.0.0")
            assert got.component_id == d.component_id

    def test_by_family_returns_full_cross_wave_sets(self):
        r = build_default_registry()
        # status.banner.notification (Wave 2) + status.results.zero (Wave 3)
        # + status.listing.pending + status.listing.unavailable (Wave 7).
        assert len(r.by_family(ComponentFamily.STATUS)) == 4
        # legal.footer.directory (Wave 2) + legal.statement.standard (Wave 7).
        assert len(r.by_family(ComponentFamily.LEGAL)) == 2
        # First-ever MONETIZATION/COMMERCE registrations (Wave 7 only).
        assert len(r.by_family(ComponentFamily.MONETIZATION)) == 4
        assert len(r.by_family(ComponentFamily.COMMERCE)) == 1

    def test_candidates_for_business_profile_includes_wave7_profile_components(self):
        r = build_default_registry()
        prof_ids = {d.component_id for d in r.candidates_for(PageRole.BUSINESS_PROFILE)}
        for cid in (
            "monetization.section.premium-profile",
            "monetization.disclosure.advertising",
            "status.listing.pending",
            "status.listing.unavailable",
            "legal.statement.standard",
        ):
            assert cid in prof_ids, cid
        assert "monetization.prompt.upgrade" not in prof_ids  # P3-excluded (see docstring)
        assert "commerce.pricing.sponsorship" not in prof_ids

    def test_candidates_for_claim_listing_includes_upgrade_prompt_and_pending_state(self):
        r = build_default_registry()
        claim_ids = {d.component_id for d in r.candidates_for(PageRole.CLAIM_LISTING)}
        for cid in (
            "monetization.prompt.upgrade",
            "status.listing.pending",
            "legal.statement.standard",
            "monetization.disclosure.advertising",
        ):
            assert cid in claim_ids, cid
        assert "status.listing.unavailable" not in claim_ids

    def test_candidates_for_sponsor_page_includes_pricing_and_disclosure(self):
        r = build_default_registry()
        spon_ids = {d.component_id for d in r.candidates_for(PageRole.SPONSOR_PAGE)}
        assert "commerce.pricing.sponsorship" in spon_ids
        assert "monetization.disclosure.advertising" in spon_ids
        assert "legal.statement.standard" in spon_ids

    def test_candidates_for_verification_and_lead_gen_landing_exclude_disclosure(self):
        # §6.1 Monetization column: both roles are "F" (forbidden).
        r = build_default_registry()
        for role in (PageRole.VERIFICATION, PageRole.LEAD_GEN_LANDING):
            ids = {d.component_id for d in r.candidates_for(role)}
            assert "monetization.disclosure.advertising" not in ids, role
            assert "legal.statement.standard" in ids, role  # ALL roles still applies

    def test_candidates_for_home_includes_ribbon_and_disclosure_not_profile_only_components(self):
        r = build_default_registry()
        home_ids = {d.component_id for d in r.candidates_for(PageRole.HOME)}
        assert "monetization.ribbon.sponsor" in home_ids
        assert "monetization.disclosure.advertising" in home_ids
        assert "legal.statement.standard" in home_ids
        assert "monetization.section.premium-profile" not in home_ids
        assert "commerce.pricing.sponsorship" not in home_ids

    def test_variant_resolution(self):
        r = build_default_registry()
        assert r.resolve_variant(
            "commerce.pricing.sponsorship", "table"
        ).display_name == "Table"
        assert r.resolve_variant(
            "monetization.disclosure.advertising", "inline"
        ).display_name == "Inline"


class TestMonetizationDisclosureConstants:
    def test_disclosure_kinds_table_matches_authority_intent(self):
        # §17.1: "visible ... label from the constants-registered disclosure
        # text set." Four kinds, one per MONETIZATION-family Wave 7
        # component (see catalog module docstring).
        assert MONETIZATION_DISCLOSURE_KINDS == (
            MONETIZATION_DISCLOSURE_KIND_ADVERTISING,
            MONETIZATION_DISCLOSURE_KIND_PREMIUM,
            MONETIZATION_DISCLOSURE_KIND_SPONSORED,
            MONETIZATION_DISCLOSURE_KIND_UPGRADE,
        )
        assert len(MONETIZATION_DISCLOSURE_KINDS) == len(
            set(MONETIZATION_DISCLOSURE_KINDS)
        )

    def test_every_monetization_component_disclosure_kind_in_registered_set(self):
        for d in WAVE7_COMPONENTS:
            if d.monetization_contract is not None:
                assert (
                    d.monetization_contract.disclosure_kind
                    in MONETIZATION_DISCLOSURE_KINDS
                ), d.component_id

    def test_commerce_pricing_sponsorship_does_not_draw_from_disclosure_kinds(self):
        # COMMERCE is not a monetization_contract-required family (§15.2);
        # its own E4 disclaimer is a plain RichTextBlock slot, not a
        # MonetizationContract.disclosure_kind (see catalog module
        # docstring).
        d = _get("commerce.pricing.sponsorship")
        assert d.monetization_contract is None


class TestRecipeTablesUnchanged:
    """AMB-002H-02 (operator-approved via the AES-WEB-002H architectural
    preflight): this delivery is strictly additive to the catalog. It does
    not touch any *_RECIPE_SLOTS table in constants/components.py, even
    though status.listing.unavailable/pending now make
    BUSINESS_PROFILE_RECIPE_SLOTS's "unavailable_state" and
    VERIFICATION_RECIPE_SLOTS's "pending_state" slots satisfiable in
    principle -- that integration remains deferred to the later
    recipe-integration phase, per the unchanged AMB-002F-02/AMB-002G-02
    precedent this wave continues a third time.
    """

    def test_business_profile_unavailable_state_slot_still_sentinel_gated(self):
        profile = {
            s["slot_id"]: s
            for s in constants_components.BUSINESS_PROFILE_RECIPE_SLOTS
        }
        slot = profile["unavailable_state"]
        assert slot["required_slot_names"] == _UNBUILT_FAMILY_SENTINEL
        assert slot["required"] is False
        assert slot["fallback_component_id"] == ""

    def test_verification_pending_state_slot_still_sentinel_gated(self):
        verification = {
            s["slot_id"]: s for s in constants_components.VERIFICATION_RECIPE_SLOTS
        }
        slot = verification["pending_state"]
        assert slot["required_slot_names"] == _UNBUILT_FAMILY_SENTINEL
        assert slot["required"] is False

    def test_recipe_table_slot_counts_unchanged_from_002g(self):
        assert len(constants_components.HOME_RECIPE_SLOTS) == 11  # AES-WEB-002K.1: +site_header/+site_footer
        assert len(constants_components.CATEGORY_RECIPE_SLOTS) == 11  # AES-WEB-002K.1: +site_header/+site_footer
        assert len(constants_components.BUSINESS_PROFILE_RECIPE_SLOTS) == 17  # AES-WEB-002K.1: +site_header/+site_footer
        assert len(constants_components.EDITORIAL_GUIDE_RECIPE_SLOTS) == 5
        assert len(constants_components.COLLECTION_RECIPE_SLOTS) == 3
        assert len(constants_components.SERVICE_AREA_RECIPE_SLOTS) == 5
        assert len(constants_components.VERIFICATION_RECIPE_SLOTS) == 5
        assert len(constants_components.REGIONAL_HUB_RECIPE_SLOTS) == 6

    def test_no_new_recipe_table_created_by_wave7(self):
        # §31's 002H acceptance text was silent on recipes; as of AES-WEB-
        # 002H, no city, city-category, search-results, comparison, best-of,
        # sponsor-page, claim-listing, lead-gen-landing, submission, or
        # correction recipe table existed yet. AES-WEB-002J.1 "Recipe
        # Completion" is the later recipe-integration phase this module's
        # own docstring and §26's closing note anticipated, and authors all
        # ten tables -- confirmed present here rather than re-asserting the
        # now-superseded absence.
        for later_table in (
            "CITY_RECIPE_SLOTS", "CITY_CATEGORY_RECIPE_SLOTS",
            "SEARCH_RESULTS_RECIPE_SLOTS",
            "COMPARISON_RECIPE_SLOTS", "BEST_OF_RECIPE_SLOTS",
            "SPONSOR_PAGE_RECIPE_SLOTS", "CLAIM_LISTING_RECIPE_SLOTS",
            "LEAD_GEN_LANDING_RECIPE_SLOTS", "SUBMISSION_RECIPE_SLOTS",
            "CORRECTION_RECIPE_SLOTS",
        ):
            assert hasattr(constants_components, later_table), later_table


class TestMonetizationLegalStatusDoctrineEnforcement:
    """AES-WEB-002 §31 acceptance: "every §6.1 monetization cell
    exercisable; every role's required-status components resolvable" and
    the standing §2.6 E1-E11 doctrine requirement ("every E1-E11 rule has at
    least one failing fixture proving enforcement"). Unlike Wave 5/6, E4,
    E5, and E10 are this wave's *own* domain (§2.6's enforcement table names
    monetization.*/commerce.*/status.* directly) -- each is addressed
    substantively below; the remaining eight are correctly out of scope or
    structurally absent, addressed explicitly rather than silently skipped,
    matching the test_catalog_wave5.py/test_catalog_wave6.py discipline.
    """

    # E1 -- False urgency: structurally impossible -- no Wave 7 component
    # declares a conversion_contract (test_no_conversion_contract_in_wave7),
    # so no urgency_policy value exists to violate E1 in the first place.
    def test_e1_false_urgency_structurally_absent(self):
        for d in WAVE7_COMPONENTS:
            assert d.conversion_contract is None, d.component_id

    # E2 -- Fabricated reviews/testimonials: owned by trust.* (Wave 5); no
    # Wave 7 component is trust-family or review-bearing.
    def test_e2_fabricated_reviews_out_of_wave_scope(self):
        for d in WAVE7_COMPONENTS:
            for slots in (d.required_content_slots, d.optional_content_slots):
                for spec in slots.values():
                    assert spec.block_type not in ("ReviewBlock", "RatingSummary"), (
                        d.component_id
                    )

    # E3 -- Deceptive scarcity / fake inventory counts: structurally
    # satisfied by absence -- no Wave 7 component exposes a count prop.
    def test_e3_deceptive_scarcity_structurally_absent(self):
        for d in WAVE7_COMPONENTS:
            for name in list(d.required_props) + list(d.optional_props):
                assert "count" not in name.lower(), (d.component_id, name)

    # E4 -- Hidden fees: pricing components MUST render a disclaimer slot
    # for non-exact PriceSpec kinds; gate CG-COM-006. This wave's own
    # domain (§5.12).
    def test_e4_hidden_fees(self):
        d = _get("commerce.pricing.sponsorship")
        assert "CG-COM-006" in d.quality_gate_requirements
        assert d.required_content_slots["disclaimer"].block_type == "RichTextBlock"
        assert d.required_content_slots["disclaimer"].cardinality is (
            SlotCardinality.EXACTLY_ONE
        )
        assert "fx-commerce.pricing.sponsorship-bad-slot" in d.example_fixture_ids

    # E5 -- Disguised advertisements: every monetized component carries
    # mandatory visible + semantic disclosure; gate CG-COM-001. This wave's
    # own domain (§5.10) -- every MONETIZATION-family component carries a
    # non-null monetization_contract with requires_visible_disclosure=True
    # (registry-enforced, §15.2), and the two components whose entire
    # purpose is disclosure/marking declare CG-COM-001 explicitly.
    def test_e5_disguised_ads(self):
        for cid in ("monetization.disclosure.advertising", "monetization.ribbon.sponsor"):
            d = _get(cid)
            assert "CG-COM-001" in d.quality_gate_requirements, cid
            assert d.monetization_contract.requires_visible_disclosure is True
        for d in WAVE7_COMPONENTS:
            if d.component_family is ComponentFamily.MONETIZATION:
                assert d.monetization_contract is not None, d.component_id
        assert (
            "fx-monetization.disclosure.advertising-bad-slot"
            in _get("monetization.disclosure.advertising").example_fixture_ids
        )

    # E6 -- Misleading rankings: owned by listing/best-of ranked-list
    # contexts (Wave 4/6); no Wave 7 component binds a ranking_rationale
    # slot or renders a ranked list.
    def test_e6_misleading_rankings_out_of_wave_scope(self):
        for d in WAVE7_COMPONENTS:
            for slots in (d.required_content_slots, d.optional_content_slots):
                assert "ranking_rationale" not in slots, d.component_id

    # E7 -- Inaccessible interactions as friction: accessibility gates are
    # BLOCKING; there is no conversion exception. The two status.* live
    # regions and the disclosure-bearing components declare reasonable
    # accessibility contracts; none is a JS-driven interactive state
    # machine this wave (that remains Wave 1/2's drawer/accordion domain).
    def test_e7_status_components_declare_live_region(self):
        for cid in ("status.listing.pending", "status.listing.unavailable"):
            d = _get(cid)
            assert d.accessibility_contract.live_region_role == "status", cid

    # E8 -- Manipulative consent patterns: owned by form.* (Wave 5); no
    # Wave 7 component renders a consent control.
    def test_e8_manipulative_consent_out_of_wave_scope(self):
        for d in WAVE7_COMPONENTS:
            assert "atom.field.choice" not in d.allowed_child_components

    # E9 -- Bait-and-switch copy: CTA label must match conversion_goal;
    # structurally impossible -- no Wave 7 component has a
    # conversion_contract (see E1).
    def test_e9_bait_and_switch_out_of_wave_scope(self):
        for d in WAVE7_COMPONENTS:
            assert d.conversion_contract is None, d.component_id

    # E10 -- Fake verification badges: verification indicators render only
    # when verification_state is VERIFIED; gate CG-COM-004. This wave's own
    # domain (§27.8 notes: status.listing.pending "never fakes VERIFIED";
    # monetization.prompt.upgrade "never positioned as requirement",
    # E10 adjacency per §17.2).
    def test_e10_fake_verification(self):
        for cid in ("status.listing.pending", "monetization.prompt.upgrade"):
            d = _get(cid)
            assert "CG-COM-004" in d.quality_gate_requirements, cid
        pending = _get("status.listing.pending")
        assert not any(
            "verif" in n.lower()
            for n in list(pending.required_props) + list(pending.optional_props)
        )
        assert (
            "fx-status.listing.pending-bad-slot"
            in pending.example_fixture_ids
        )

    # E11 -- Fake popularity indicators: same rule as E3.
    def test_e11_fake_popularity_structurally_absent(self):
        for d in WAVE7_COMPONENTS:
            for name in list(d.required_props) + list(d.optional_props):
                assert "popular" not in name.lower(), (d.component_id, name)


class TestMonetizationCellAndStatusExercisability:
    """AES-WEB-002 §31's AES-WEB-002H acceptance criterion: "every §6.1
    monetization cell exercisable; every role's required-status components
    resolvable." Per the AMB-002G-01 precedent (operator-approved, reused
    here as AMB-002H's own disposition for the identical shape of
    question): satisfied via the fixture-only approach -- direct
    registry-candidacy proof against synthetic per-role bindings, not a
    live recipe/selection pipeline run (component_engine.py does not exist
    for any wave yet). This does NOT modify any *_RECIPE_SLOTS table (see
    TestRecipeTablesUnchanged).
    """

    # §6.1 Monetization column, non-P3 cells, mapped to the Wave 7 (or
    # earlier) component that can exercise them (see AES-WEB-002H
    # architectural preflight §11).
    # best-of is intentionally absent here: §6.1 names an "O clearly-
    # separated featured block" for best-of, but listing.card.featured
    # itself (§27.5, AES-WEB-002E) does not declare best-of among its
    # supported_page_roles -- a pre-existing Wave-4 gap. Per the catalog
    # module docstring's documented interpretive resolution,
    # monetization.ribbon.sponsor mirrors listing.card.featured/sponsored's
    # own role union exactly rather than silently claiming a broader
    # context than the cards it decorates actually support. See
    # test_best_of_featured_block_is_a_known_uncovered_gap below.
    MONETIZATION_CELL_COVERAGE = {
        PageRole.HOME: ("monetization.ribbon.sponsor", "monetization.disclosure.advertising"),
        PageRole.CATEGORY: ("monetization.ribbon.sponsor",),
        PageRole.CITY_CATEGORY: ("monetization.ribbon.sponsor",),
        PageRole.SEARCH_RESULTS: ("monetization.ribbon.sponsor",),
        PageRole.BUSINESS_PROFILE: ("monetization.section.premium-profile",),
        PageRole.CLAIM_LISTING: ("monetization.prompt.upgrade",),
        PageRole.SPONSOR_PAGE: ("commerce.pricing.sponsorship", "monetization.disclosure.advertising"),
        PageRole.SUBMISSION: ("monetization.disclosure.advertising",),
    }

    # §6.1 Status column cells this wave specifically closes (the general
    # zero-results case is already Wave 3's status.results.zero and is not
    # re-tested here).
    STATUS_CELL_COVERAGE = {
        PageRole.BUSINESS_PROFILE: (
            "status.listing.unavailable", "status.listing.pending",
        ),
        PageRole.CLAIM_LISTING: ("status.listing.pending",),
    }

    def test_every_monetization_cell_has_a_resolvable_candidate(self):
        r = build_default_registry()
        for role, expected_ids in self.MONETIZATION_CELL_COVERAGE.items():
            candidates = {d.component_id for d in r.candidates_for(role)}
            for cid in expected_ids:
                assert cid in candidates, (role, cid)

    def test_every_required_status_cell_has_a_resolvable_candidate(self):
        r = build_default_registry()
        for role, expected_ids in self.STATUS_CELL_COVERAGE.items():
            candidates = {d.component_id for d in r.candidates_for(role)}
            for cid in expected_ids:
                assert cid in candidates, (role, cid)

    def test_best_of_featured_block_is_a_known_uncovered_gap(self):
        # §6.1's best-of "O clearly-separated featured block" cell has no
        # resolvable candidate today -- neither listing.card.featured
        # (Wave 4) nor monetization.ribbon.sponsor (this wave) declares
        # best-of. Recorded explicitly as a known, carried limitation
        # (not silently papered over) rather than asserted as covered.
        r = build_default_registry()
        candidates = {d.component_id for d in r.candidates_for(PageRole.BEST_OF)}
        assert "monetization.ribbon.sponsor" not in candidates
        assert "listing.card.featured" not in candidates

    def test_comparison_affiliate_monetization_correctly_unexercisable(self):
        # §6.1: comparison's monetization cell is "O affiliate (P3,
        # disclosed)" -- P3 per §34.2, correctly absent from the 72-MVP
        # inventory and therefore not exercisable by design.
        r = build_default_registry()
        candidates = {d.component_id for d in r.candidates_for(PageRole.COMPARISON)}
        assert "monetization.ribbon.sponsor" not in candidates
        assert "commerce.pricing.sponsorship" not in candidates

    def test_wave7_exercisability_is_registry_candidacy_only(self):
        # Wave-7 (AES-WEB-002H) catalog exercisability is proven purely from
        # registry candidacy (candidates_for), never from a live selection
        # run -- the AMB-002G-01 precedent. The Component Engine arrived later
        # (AES-WEB-002J.6); its existence does not change these proofs, which
        # deliberately depend only on the registry index. (Historically this
        # guard asserted component_engine.py was absent; J.6 built it, so the
        # invariant is restated as "wave-7 proofs need no engine", which
        # remains true.)
        import importlib.util

        spec = importlib.util.find_spec(
            "engines.website_generation.components.component_engine"
        )
        assert spec is not None  # present as of AES-WEB-002J.6
