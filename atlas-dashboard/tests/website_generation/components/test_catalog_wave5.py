"""Wave 5 catalog tests (AES-WEB-002F; AES-WEB-002 §27.6, §15.2, §30.1).

Catalog completeness (exact IDs, versions, families, roles, variants,
count), definition validity, determinism (hash stability across order and
process restarts), compatibility metadata, registry lookups, ethical-
conversion doctrine (E1-E11) enforcement linkage, and architecture
boundaries -- mirrors test_catalog_wave4.py's structure.
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
    ComponentFamily,
    LifecycleStatus,
    PageRole,
    PropType,
    RegionKind,
    SlotCardinality,
)
from engines.website_generation.components.catalog.trust_conversion import (
    WAVE5_COMPONENTS,
)
from engines.website_generation.components.registry import (
    REGISTERED_COMPONENTS,
    ComponentRegistry,
    build_default_registry,
    definition_fingerprint,
    validate_definition,
)
from engines.website_generation.constants.components import (
    CTA_GOAL_ACTION_TARGET_TYPES,
    CTA_GOAL_ANALYTICS_EVENT,
    CTA_GOAL_LABEL_CLASSES,
    CTA_PRIMARY_GOAL_MAX_REPETITIONS_PER_PAGE,
    FORM_FRICTION_BUDGET_CLAIM_STEP_ONE_MAX_FIELDS,
    FORM_FRICTION_BUDGET_CORRECTION_MAX_FIELDS,
    FORM_FRICTION_BUDGET_MAX_REQUIRED_FIELDS,
    FORM_FRICTION_BUDGET_NEWSLETTER_MAX_FIELDS,
    FORM_FRICTION_BUDGET_QUOTE_LEAD_MAX_FIELDS,
    FORM_FRICTION_BUDGET_SPONSOR_INQUIRY_MAX_FIELDS,
)

APP_ROOT = Path(__file__).resolve().parents[3]

# The exact §27.6 Wave 5 inventory (lexicographic -- §15.2 ordering law).
EXPECTED_IDS = [
    "content.faq.standard",
    "cta.claim.listing",
    "cta.sponsor.inquiry",
    "cta.sticky.mobile",
    "cta.submit.listing",
    "form.capture.newsletter",
    "form.claim.standard",
    "form.correction.standard",
    "form.lead.quote",
    "form.submission.listing",
    "trust.reviews.list",
    "trust.reviews.summary",
    "trust.statistics.strip",
]

EXPECTED_VARIANTS = {
    "content.faq.standard": ("accordion", "open-list"),
    "cta.claim.listing": ("band", "inline"),
    "cta.sponsor.inquiry": (),
    "cta.sticky.mobile": (),
    "cta.submit.listing": (),
    "form.capture.newsletter": ("band", "inline"),
    "form.claim.standard": (),
    "form.correction.standard": (),
    "form.lead.quote": (),
    "form.submission.listing": (),
    "trust.reviews.list": (),
    "trust.reviews.summary": ("block", "inline"),
    "trust.statistics.strip": ("grid", "strip"),
}

# §27.6 "Roles" column, mapped to PageRole membership counts.
EXPECTED_ROLE_COUNTS = {
    "content.faq.standard": 4,  # prof, cat, city, guides
    "cta.claim.listing": 3,  # prof, home, cat
    "cta.sponsor.inquiry": 1,  # spon
    "cta.sticky.mobile": 3,  # prof, lg, cc
    "cta.submit.listing": 3,  # home, cat, sub
    "form.capture.newsletter": 2,  # home, guides
    "form.claim.standard": 1,  # claim
    "form.correction.standard": 1,  # corr
    "form.lead.quote": 3,  # lg, prof, cc
    "form.submission.listing": 1,  # sub
    "trust.reviews.list": 1,  # prof
    "trust.reviews.summary": 7,  # prof + "listing contexts" (see docstring)
    "trust.statistics.strip": 3,  # home, spon, lg
}

EXPECTED_FAMILY = {
    "content.faq.standard": ComponentFamily.CONTENT,
    "cta.claim.listing": ComponentFamily.CTA,
    "cta.sponsor.inquiry": ComponentFamily.CTA,
    "cta.sticky.mobile": ComponentFamily.CTA,
    "cta.submit.listing": ComponentFamily.CTA,
    "form.capture.newsletter": ComponentFamily.FORM,
    "form.claim.standard": ComponentFamily.FORM,
    "form.correction.standard": ComponentFamily.FORM,
    "form.lead.quote": ComponentFamily.FORM,
    "form.submission.listing": ComponentFamily.FORM,
    "trust.reviews.list": ComponentFamily.TRUST,
    "trust.reviews.summary": ComponentFamily.TRUST,
    "trust.statistics.strip": ComponentFamily.TRUST,
}

EXPECTED_CLASS_PREFIX = {
    "content.faq.standard": "ac-content",
    "cta.claim.listing": "ac-cta",
    "cta.sponsor.inquiry": "ac-cta",
    "cta.sticky.mobile": "ac-cta",
    "cta.submit.listing": "ac-cta",
    "form.capture.newsletter": "ac-form",
    "form.claim.standard": "ac-form",
    "form.correction.standard": "ac-form",
    "form.lead.quote": "ac-form",
    "form.submission.listing": "ac-form",
    "trust.reviews.list": "ac-trust",
    "trust.reviews.summary": "ac-trust",
    "trust.statistics.strip": "ac-trust",
}

EXPECTED_GATES = {
    "content.faq.standard": ("CG-A11Y-002", "CG-SEO-006"),
    "cta.claim.listing": ("CG-COM-008",),
    "cta.sponsor.inquiry": ("CG-COM-008",),
    "cta.sticky.mobile": ("CG-CMP-009", "CG-RSP-006"),
    "cta.submit.listing": ("CG-COM-008",),
    "form.capture.newsletter": ("CG-COM-007", "CG-COM-010"),
    "form.claim.standard": ("CG-COM-004", "CG-COM-010"),
    "form.correction.standard": ("CG-A11Y-012",),
    "form.lead.quote": ("CG-COM-005", "CG-COM-010", "CG-A11Y-012"),
    "form.submission.listing": ("CG-COM-007",),
    "trust.reviews.list": ("CG-COM-003",),
    "trust.reviews.summary": ("CG-COM-003", "CG-SEO-005"),
    "trust.statistics.strip": ("CG-COM-003",),
}

# form.* components that compose the Wave-1 field primitives (§27.2) as
# children rather than declaring a content slot -- see the module docstring
# in trust_conversion.py for the rationale.
FORM_COMPONENTS_WITH_FIELD_CHILDREN = (
    "form.claim.standard",
    "form.correction.standard",
    "form.lead.quote",
    "form.submission.listing",
)


def _get(cid):
    return next(d for d in WAVE5_COMPONENTS if d.component_id == cid)


class TestCatalogCompleteness:
    def test_exact_component_ids(self):
        assert [d.component_id for d in WAVE5_COMPONENTS] == EXPECTED_IDS

    def test_exact_catalog_count(self):
        assert len(WAVE5_COMPONENTS) == 13  # §27.6 "Trust, conversion, and forms (13)"
        # Wave 1 (15) + Wave 2 (8) + Wave 3 (9) + Wave 4 (12) + Wave 5 (13)
        # + Wave 6 (7) + Wave 7 (8) = 72.
        assert len(REGISTERED_COMPONENTS) == 72

    def test_exact_versions(self):
        assert all(d.component_version == "1.0.0" for d in WAVE5_COMPONENTS)

    def test_exact_family_assignments(self):
        for d in WAVE5_COMPONENTS:
            assert d.component_family is EXPECTED_FAMILY[d.component_id], (
                d.component_id
            )

    def test_family_counts(self):
        trust = [d for d in WAVE5_COMPONENTS if d.component_family is ComponentFamily.TRUST]
        content = [d for d in WAVE5_COMPONENTS if d.component_family is ComponentFamily.CONTENT]
        form = [d for d in WAVE5_COMPONENTS if d.component_family is ComponentFamily.FORM]
        cta = [d for d in WAVE5_COMPONENTS if d.component_family is ComponentFamily.CTA]
        assert len(trust) == 3 and len(content) == 1 and len(form) == 5 and len(cta) == 4

    def test_exact_variant_names(self):
        for d in WAVE5_COMPONENTS:
            expected = EXPECTED_VARIANTS[d.component_id]
            assert tuple(sorted(d.supported_variants)) == expected, d.component_id

    def test_exact_role_counts_match_authority_table(self):
        for d in WAVE5_COMPONENTS:
            assert len(d.supported_page_roles) == EXPECTED_ROLE_COUNTS[
                d.component_id
            ], d.component_id

    def test_exact_roles_per_form_component(self):
        # §27.6's per-row "Roles" column, verbatim -- layout_atoms._FORM_ROLES
        # (Wave 1's "forms" abbreviation, §5.13) is not a universal bound on
        # every Wave 5 form.* component: form.lead.quote's "cc" (city-category)
        # and form.capture.newsletter's "home, guides" both fall outside it.
        assert set(_get("form.lead.quote").supported_page_roles) == {
            PageRole.LEAD_GEN_LANDING, PageRole.BUSINESS_PROFILE, PageRole.CITY_CATEGORY,
        }
        assert set(_get("form.claim.standard").supported_page_roles) == {
            PageRole.CLAIM_LISTING,
        }
        assert set(_get("form.submission.listing").supported_page_roles) == {
            PageRole.SUBMISSION,
        }
        assert set(_get("form.correction.standard").supported_page_roles) == {
            PageRole.CORRECTION,
        }
        assert set(_get("form.capture.newsletter").supported_page_roles) == {
            PageRole.HOME, PageRole.EDITORIAL_GUIDE,
        }

    def test_no_duplicate_ids_or_versions(self):
        keys = [(d.component_id, d.component_version) for d in WAVE5_COMPONENTS]
        assert len(keys) == len(set(keys))

    def test_no_duplicate_ids_or_versions_across_full_catalog(self):
        keys = [(d.component_id, d.component_version) for d in REGISTERED_COMPONENTS]
        assert len(keys) == len(set(keys))

    def test_lexicographic_tuple_order(self):
        ids = [d.component_id for d in REGISTERED_COMPONENTS]
        assert ids == sorted(ids)  # §15.2 ordering law

    def test_no_placeholder_values(self):
        text = canonical_json(
            [model_to_dict(d) for d in WAVE5_COMPONENTS]
        ).lower()
        for marker in ("todo", "tbd", "lorem", "dummy", "fixme", "xxx"):
            assert marker not in text, marker


class TestDefinitionValidity:
    def test_every_definition_passes_validate_definition(self):
        for d in WAVE5_COMPONENTS:
            validate_definition(d)

    def test_every_default_variant_exists(self):
        for d in WAVE5_COMPONENTS:
            if d.supported_variants:
                assert d.default_variant in d.supported_variants, d.component_id
            else:
                assert d.default_variant == "", d.component_id

    def test_lifecycle_is_proposed_until_emitters_exist(self):
        # Operator decision carried through 002B-002E and reaffirmed for
        # 002F (preflight Accepted-Warning Disposition): no renderer/gates
        # package is built this wave; no component is promoted to ACTIVE.
        for d in WAVE5_COMPONENTS:
            assert d.lifecycle_status is LifecycleStatus.PROPOSED

    def test_required_contract_fields_present(self):
        for d in WAVE5_COMPONENTS:
            assert d.analytics_contract.impression_id == d.component_id.replace(".", "-")
            assert d.rendering_contract.emitter_key == d.component_id + "@1"
            assert d.rendering_contract.class_prefix == EXPECTED_CLASS_PREFIX[d.component_id]
            assert d.description and d.display_name
            assert d.design_token_dependencies, d.component_id
            assert d.example_fixture_ids

    def test_fixture_ids_follow_grammar(self):
        expected_suffixes = {
            "min", "full", "bad-prop", "bad-slot", "mobile", "long", "a11y",
        }
        for d in WAVE5_COMPONENTS:
            suffixes = {
                fid.replace("fx-%s-" % d.component_id, "")
                for fid in d.example_fixture_ids
            }
            assert suffixes == expected_suffixes, d.component_id

    def test_no_directory_contract_in_wave5(self):
        # §6.3's ListingKind semantics are Wave 4's domain; no Wave 5
        # component is listing-kind-bearing.
        for d in WAVE5_COMPONENTS:
            assert d.directory_contract is None, d.component_id

    def test_no_monetization_contract_in_wave5(self):
        # §5.10: only the MONETIZATION family requires monetization_contract.
        # cta.sponsor.inquiry is monetization-adjacent but is a cta-family
        # inquiry entry point, not a monetized surface itself.
        for d in WAVE5_COMPONENTS:
            assert d.monetization_contract is None, d.component_id

    def test_no_free_form_string_props(self):
        for d in WAVE5_COMPONENTS:
            for props in (d.required_props, d.optional_props):
                for name, spec in props.items():
                    assert isinstance(spec.prop_type, PropType), (d.component_id, name)

    def test_definitions_are_frozen_and_reject_extras(self):
        for d in WAVE5_COMPONENTS:
            with pytest.raises(Exception):
                d.component_id = "x.y.z"
            assert d.component_id != "x.y.z"

    def test_content_faq_standard_placement_and_shape(self):
        # AMB-002F-01 (operator-approved): content.faq.standard is a
        # content-family component registered in this wave's own file.
        d = _get("content.faq.standard")
        assert d.component_family is ComponentFamily.CONTENT
        assert d.seo_contract.schema_fragments == ("FAQPage",)
        assert d.accessibility_contract.state_machine == "accordion"
        qa = d.required_content_slots["qa_pairs"]
        assert qa.cardinality is SlotCardinality.ONE_TO_N
        assert qa.max_count == 12

    def test_trust_reviews_list_density_prop_not_variant(self):
        # §7.1: density is a shared axis, not a per-component variant --
        # matches listing.card.standard's own Wave-4 precedent.
        d = _get("trust.reviews.list")
        assert "density" in d.required_props
        assert d.required_props["density"].prop_type is PropType.STR_ENUM
        assert set(d.required_props["density"].enum_values) == {"comfortable", "compact"}
        assert "comfortable" not in d.supported_variants
        assert "compact" not in d.supported_variants

    def test_trust_reviews_list_evidence_bearing_slot(self):
        d = _get("trust.reviews.list")
        assert d.required_content_slots["reviews"].block_type == "ReviewBlock"
        assert d.required_content_slots["reviews"].cardinality is SlotCardinality.ONE_TO_N

    def test_form_components_compose_field_primitives_not_slots(self):
        for cid in FORM_COMPONENTS_WITH_FIELD_CHILDREN:
            d = _get(cid)
            assert d.allowed_child_components == (
                "atom.field.choice", "atom.field.select", "atom.field.text",
            ), cid
            assert "fields" not in d.required_content_slots
            assert "fields" not in d.optional_content_slots

    def test_newsletter_consent_via_choice_primitive_only(self):
        d = _get("form.capture.newsletter")
        assert d.allowed_child_components == ("atom.field.choice",)
        assert "consent" not in d.required_content_slots

    def test_form_states_via_conversion_contract_not_slots(self):
        for cid in FORM_COMPONENTS_WITH_FIELD_CHILDREN + ("form.capture.newsletter",):
            d = _get(cid)
            assert d.conversion_contract is not None, cid
            assert d.conversion_contract.success_state == "form_success", cid
            assert d.conversion_contract.failure_state == "form_error", cid
            assert "states" not in d.required_content_slots

    def test_form_lead_quote_has_disclosure_slot(self):
        d = _get("form.lead.quote")
        assert d.required_content_slots["disclosure"].block_type == "DisclosureBlock"

    def test_form_submission_listing_has_standards_link_slot(self):
        d = _get("form.submission.listing")
        assert d.required_content_slots["standards_link"].block_type == "LinkSpec"

    def test_form_semantic_element_is_form(self):
        from engines.website_generation.contracts.enums import SemanticElement
        for d in WAVE5_COMPONENTS:
            if d.component_family is ComponentFamily.FORM:
                assert d.semantic_element is SemanticElement.FORM, d.component_id

    def test_cta_labels_are_content_slots(self):
        for cid in ("cta.claim.listing", "cta.sponsor.inquiry", "cta.submit.listing"):
            d = _get(cid)
            assert d.required_content_slots["label"].block_type == "RichTextBlock"

    def test_cta_sticky_mobile_goal_prop_spans_full_conversion_goal_enum(self):
        from engines.website_generation.contracts.enums import ConversionGoal
        d = _get("cta.sticky.mobile")
        assert d.required_props["goal"].prop_type is PropType.STR_ENUM
        assert set(d.required_props["goal"].enum_values) == {
            g.value for g in ConversionGoal
        }
        assert d.required_props["target_route"].prop_type is PropType.ROUTE_REF
        assert RegionKind.STICKY_MOBILE in d.allowed_parent_regions

    def test_cta_sticky_mobile_single_instance_repetition_limit(self):
        d = _get("cta.sticky.mobile")
        assert d.conversion_contract.repetition_limit_per_page == 1

    def test_cta_sponsor_inquiry_footer_as_region_not_extra_role(self):
        # "footer contexts" (§27.6) is a RegionKind concern, not an
        # additional PageRole -- see trust_conversion.py's module docstring.
        d = _get("cta.sponsor.inquiry")
        assert set(d.supported_page_roles) == {PageRole.SPONSOR_PAGE}
        assert RegionKind.FOOTER in d.allowed_parent_regions
        assert RegionKind.BODY in d.allowed_parent_regions

    def test_cta_primary_goal_repetition_limits_within_constant(self):
        for cid in ("cta.claim.listing", "cta.sponsor.inquiry", "cta.submit.listing"):
            d = _get(cid)
            assert (
                d.conversion_contract.repetition_limit_per_page
                == CTA_PRIMARY_GOAL_MAX_REPETITIONS_PER_PAGE
            ), cid


class TestDeterminism:
    def test_identical_catalog_identical_hash(self):
        assert (
            ComponentRegistry(WAVE5_COMPONENTS).registry_hash()
            == ComponentRegistry(WAVE5_COMPONENTS).registry_hash()
        )

    def test_registration_order_does_not_alter_hash(self):
        forward = ComponentRegistry(WAVE5_COMPONENTS).registry_hash()
        backward = ComponentRegistry(tuple(reversed(WAVE5_COMPONENTS))).registry_hash()
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
        prints = [definition_fingerprint(d) for d in WAVE5_COMPONENTS]
        assert prints == [definition_fingerprint(d) for d in WAVE5_COMPONENTS]
        assert len(set(prints)) == 13

    def test_earlier_waves_fingerprints_unchanged_by_wave5_addition(self):
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
        earlier = {
            d.component_id: definition_fingerprint(d)
            for d in WAVE1_COMPONENTS + WAVE2_COMPONENTS + WAVE3_COMPONENTS + WAVE4_COMPONENTS
        }
        r = build_default_registry()
        for component_id, expected_fp in earlier.items():
            got = r.get(component_id)
            assert definition_fingerprint(got) == expected_fp, component_id


class TestCompatibilityMetadata:
    def test_compatibility_axes_pinned(self):
        for d in WAVE5_COMPONENTS:
            assert set(d.compatibility_range) == {
                "renderer", "token_schema", "registry_schema",
            }, d.component_id

    def test_gate_requirements_match_authority_table(self):
        for d in WAVE5_COMPONENTS:
            assert d.quality_gate_requirements == EXPECTED_GATES[d.component_id], (
                d.component_id
            )

    def test_page_roles_and_region_kinds_typed(self):
        for d in WAVE5_COMPONENTS:
            assert all(isinstance(r, PageRole) for r in d.supported_page_roles)
            assert all(isinstance(r, RegionKind) for r in d.allowed_parent_regions)


class TestRegistryLookups:
    def test_every_wave5_component_resolvable(self):
        r = build_default_registry()
        for d in WAVE5_COMPONENTS:
            got = r.get(d.component_id, "1.0.0")
            assert got.component_id == d.component_id

    def test_by_family_returns_wave5_sets(self):
        r = build_default_registry()
        assert len(r.by_family(ComponentFamily.TRUST)) == 3
        assert len(r.by_family(ComponentFamily.CTA)) == 4
        assert len(r.by_family(ComponentFamily.FORM)) == 5
        # content family = 1 Wave 4 (content.description.business) + 1
        # Wave 5 (content.faq.standard) + 5 Wave 6 (§27.7) = 7.
        assert len(r.by_family(ComponentFamily.CONTENT)) == 7

    def test_candidates_for_business_profile_includes_wave5_components(self):
        r = build_default_registry()
        profile_ids = {d.component_id for d in r.candidates_for(PageRole.BUSINESS_PROFILE)}
        for cid in (
            "trust.reviews.summary", "trust.reviews.list", "content.faq.standard",
            "form.lead.quote", "cta.claim.listing", "cta.sticky.mobile",
        ):
            assert cid in profile_ids, cid
        assert "form.claim.standard" not in profile_ids
        assert "cta.sponsor.inquiry" not in profile_ids

    def test_candidates_for_claim_listing_includes_form_claim_standard_only_wave5(self):
        # Wave 1/2 universal-role primitives (layout.*, atom.*, nav.*) also
        # match every PageRole, including claim-listing; form.claim.standard
        # is the only *Wave 5* component scoped to this role.
        r = build_default_registry()
        claim_ids = {d.component_id for d in r.candidates_for(PageRole.CLAIM_LISTING)}
        assert "form.claim.standard" in claim_ids
        wave5_claim_ids = claim_ids & {d.component_id for d in WAVE5_COMPONENTS}
        assert wave5_claim_ids == {"form.claim.standard"}

    def test_candidates_for_sponsor_page_includes_sponsor_only_components(self):
        r = build_default_registry()
        spon_ids = {d.component_id for d in r.candidates_for(PageRole.SPONSOR_PAGE)}
        assert "cta.sponsor.inquiry" in spon_ids
        assert "trust.statistics.strip" in spon_ids
        assert "form.claim.standard" not in spon_ids

    def test_variant_resolution(self):
        r = build_default_registry()
        assert r.resolve_variant(
            "trust.reviews.summary", "block"
        ).display_name == "Block"


class TestEthicalConversionDoctrineEnforcement:
    """AES-WEB-002 §31 acceptance: "every E1-E11 doctrine rule has at least
    one failing fixture proving enforcement." No gates/ package exists yet
    (AES-WEB-002I), so "enforcement" at this wave's declarative-only stage
    means: the specific gate ID that will enforce each rule is declared on
    the component(s) it governs, a bad-case fixture ID is registered
    demonstrating the violation, and (where checkable without executing a
    gate) the contract shape structurally prevents the violation by
    construction. Each of E1-E11 is addressed explicitly below, including
    the three rules correctly out of this wave's scope (owned by a
    different family/wave per §2.6's own table) and the two rules Wave 5
    satisfies by the *absence* of any component exposing the prohibited
    prop shape.
    """

    # E1 -- False urgency: urgency claims must reference a spec-backed
    # offer with an expiry, or gate CG-COM-005 blocks. Every Wave 5
    # conversion_contract declares urgency_policy="none" (the only legal
    # value here -- none of these components has an "offer" concept), and
    # form.lead.quote (the most plausible home for urgency copy, e.g. a
    # lead-gen offer) declares CG-COM-005 explicitly.
    def test_e1_false_urgency(self):
        for d in WAVE5_COMPONENTS:
            if d.conversion_contract is not None:
                assert d.conversion_contract.urgency_policy == "none", d.component_id
        d = _get("form.lead.quote")
        assert "CG-COM-005" in d.quality_gate_requirements
        assert "fx-form.lead.quote-bad-prop" in d.example_fixture_ids

    # E2 -- Fabricated reviews/testimonials: review components accept only
    # ContentPackage review blocks carrying evidence_ref provenance; gate
    # CG-COM-003 blocks unreferenced review content.
    def test_e2_fabricated_reviews(self):
        for cid in ("trust.reviews.list", "trust.reviews.summary", "trust.statistics.strip"):
            d = _get(cid)
            assert "CG-COM-003" in d.quality_gate_requirements, cid
        d = _get("trust.reviews.list")
        assert "fx-trust.reviews.list-bad-slot" in d.example_fixture_ids

    # E3 -- Deceptive scarcity / fake inventory counts: no component
    # exposes a count prop without a data_source reference. Structurally
    # satisfied by absence -- no Wave 5 component declares any prop or
    # slot resembling a live count.
    def test_e3_deceptive_scarcity_structurally_absent(self):
        for d in WAVE5_COMPONENTS:
            for name in list(d.required_props) + list(d.optional_props):
                assert "count" not in name.lower(), (d.component_id, name)

    # E4 -- Hidden fees: pricing components must render a disclaimer slot
    # for estimated PriceSpec kinds. Owned by commerce.* (Wave 7, §5.12);
    # no Wave 5 component carries a PriceSpec slot.
    def test_e4_hidden_fees_out_of_wave_scope(self):
        for d in WAVE5_COMPONENTS:
            for slots in (d.required_content_slots, d.optional_content_slots):
                for spec in slots.values():
                    assert spec.block_type != "PriceSpec", d.component_id

    # E5 -- Disguised advertisements: every monetized component carries
    # mandatory disclosure; gate CG-COM-001 blocks. Owned by monetization.*
    # (Wave 7, §5.10) -- no Wave 5 component is monetization-family or
    # carries a monetization_contract (see TestDefinitionValidity).
    def test_e5_disguised_ads_out_of_wave_scope(self):
        for d in WAVE5_COMPONENTS:
            assert d.component_family is not ComponentFamily.MONETIZATION

    # E6 -- Misleading rankings: ranked lists must bind ranking_rationale
    # or a methodology link. Owned by listing/best-of contexts (Wave 4/6);
    # no Wave 5 component renders a ranked list.
    def test_e6_misleading_rankings_out_of_wave_scope(self):
        for d in WAVE5_COMPONENTS:
            for slots in (d.required_content_slots, d.optional_content_slots):
                assert "ranking_rationale" not in slots, d.component_id

    # E7 -- Inaccessible interactions as friction: accessibility gates are
    # BLOCKING; there is no conversion exception. Every interactive Wave 5
    # component (forms, ctas, the FAQ accordion) declares
    # keyboard_operable=True.
    def test_e7_accessibility_no_conversion_exception(self):
        interactive_families = (ComponentFamily.FORM, ComponentFamily.CTA)
        for d in WAVE5_COMPONENTS:
            if d.component_family in interactive_families or d.component_id == "content.faq.standard":
                assert d.accessibility_contract.keyboard_operable is True, d.component_id

    # E8 -- Manipulative consent patterns: consent controls must present
    # equal-weight accept/decline actions; pre-checked marketing consent is
    # prohibited; gate CG-COM-007 blocks. form.capture.newsletter composes
    # atom.field.choice (Wave 1's own "equal-weight consent" primitive) for
    # its consent control rather than a pre-set BOOL prop.
    def test_e8_manipulative_consent(self):
        d = _get("form.capture.newsletter")
        assert "CG-COM-007" in d.quality_gate_requirements
        assert d.allowed_child_components == ("atom.field.choice",)
        assert not any(
            spec.prop_type.value == "BOOL" and "consent" in name.lower()
            for name, spec in {**d.required_props, **d.optional_props}.items()
        )
        assert "fx-form.capture.newsletter-bad-prop" in d.example_fixture_ids

    # E9 -- Bait-and-switch copy: CTA label must match conversion_goal
    # action class; gate CG-COM-008. The §16.2 CTA_GOAL_LABEL_CLASSES
    # table constrains every cta.* component this wave declares.
    def test_e9_bait_and_switch_cta_labels(self):
        for cid in ("cta.claim.listing", "cta.sponsor.inquiry", "cta.submit.listing"):
            d = _get(cid)
            assert "CG-COM-008" in d.quality_gate_requirements, cid
            goal = d.conversion_contract.conversion_goal.value
            assert goal in CTA_GOAL_LABEL_CLASSES, cid
            assert goal in CTA_GOAL_ACTION_TARGET_TYPES, cid
            assert goal in CTA_GOAL_ANALYTICS_EVENT, cid
        assert "fx-cta.claim.listing-bad-prop" in _get("cta.claim.listing").example_fixture_ids

    # E10 -- Fake verification badges: verification indicators render only
    # when verification_state is VERIFIED; gate CG-COM-004.
    # form.claim.standard never renders a verification badge itself (that
    # stays owned by profile.header.business, Wave 4) but declares
    # CG-COM-004 since claiming is verification-adjacent.
    def test_e10_fake_verification(self):
        d = _get("form.claim.standard")
        assert "CG-COM-004" in d.quality_gate_requirements
        assert "fx-form.claim.standard-bad-slot" in d.example_fixture_ids

    # E11 -- Fake popularity indicators: same rule as E3, no unreferenced
    # counters. Structurally satisfied by the same absence check.
    def test_e11_fake_popularity_structurally_absent(self):
        for d in WAVE5_COMPONENTS:
            for name in list(d.required_props) + list(d.optional_props):
                assert "popular" not in name.lower(), (d.component_id, name)


class TestFrictionBudgetConstants:
    def test_friction_budget_values_match_authority(self):
        # §16.5: "Quote/lead <= 6 fields; newsletter <= 2; claim step one
        # <= 5; correction <= 5; sponsor inquiry <= 6. Required-field
        # count <= 4 on any MVP form."
        assert FORM_FRICTION_BUDGET_QUOTE_LEAD_MAX_FIELDS == 6
        assert FORM_FRICTION_BUDGET_NEWSLETTER_MAX_FIELDS == 2
        assert FORM_FRICTION_BUDGET_CLAIM_STEP_ONE_MAX_FIELDS == 5
        assert FORM_FRICTION_BUDGET_CORRECTION_MAX_FIELDS == 5
        assert FORM_FRICTION_BUDGET_SPONSOR_INQUIRY_MAX_FIELDS == 6
        assert FORM_FRICTION_BUDGET_MAX_REQUIRED_FIELDS == 4

    def test_cta_goal_tables_internally_consistent(self):
        assert (
            set(CTA_GOAL_LABEL_CLASSES)
            == set(CTA_GOAL_ACTION_TARGET_TYPES)
            == set(CTA_GOAL_ANALYTICS_EVENT)
        )
        for goal, targets in CTA_GOAL_ACTION_TARGET_TYPES.items():
            assert targets == ("route",), goal
