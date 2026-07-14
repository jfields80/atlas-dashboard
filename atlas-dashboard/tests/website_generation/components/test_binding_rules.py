"""Binding-rule map tests (AES-WEB-002J.18; ADR-WEB-CONTENT-BINDING-MAP).

Covers groups B (mapping model/compatibility), C (listing projection), D
(navigation), and E (scope/cardinality) at the rule-declaration level. The
registry-wide completeness + determinism checks live in
tests/website_generation/architecture/test_binding_map_completeness.py.
"""

from __future__ import annotations

from engines.website_generation.components.binding_rules import (
    BINDING_RULES,
    BINDING_RULES_BY_KEY,
    BindingRule,
    BindingState,
    FieldKind,
    referenced_semantic_slots,
    rules_for_component,
    unknown_semantic_slots,
)
from engines.website_generation.constants.content_slots import (
    SEMANTIC_SLOTS,
    Availability,
)


def _rule(component_id, field_kind, field_name) -> BindingRule:
    return BINDING_RULES_BY_KEY[(component_id, field_kind.value, field_name)]


# --------------------------------------------------------------------------- #
# B. Mapping model
# --------------------------------------------------------------------------- #

class TestMappingModel:
    def test_rules_present(self):
        assert len(BINDING_RULES) >= 100

    def test_every_non_literal_rule_targets_known_semantic_slot(self):
        assert unknown_semantic_slots() == ()
        for r in BINDING_RULES:
            if r.field_kind is not FieldKind.PROP_LITERAL:
                assert r.semantic_slot in SEMANTIC_SLOTS, (r.component_id, r.field_name)

    def test_literal_rules_have_empty_semantic_slot(self):
        for r in BINDING_RULES:
            if r.field_kind is FieldKind.PROP_LITERAL:
                assert r.semantic_slot == ""

    def test_no_duplicate_keys(self):
        keys = [(r.component_id, r.field_kind.value, r.field_name) for r in BINDING_RULES]
        assert len(keys) == len(set(keys))

    def test_no_placeholder_sources(self):
        for r in BINDING_RULES:
            assert r.source_rule.strip()
            assert "resolved" not in r.source_rule.lower()

    def test_binding_state_typed(self):
        for r in BINDING_RULES:
            assert isinstance(r.binding_state, BindingState)

    def test_structured_deferred_slot_never_fully_bindable(self):
        for r in BINDING_RULES:
            if r.field_kind is FieldKind.PROP_LITERAL:
                continue
            slot = SEMANTIC_SLOTS[r.semantic_slot]
            if slot.structured_deferred:
                assert r.binding_state is not BindingState.FULLY_BINDABLE, r

    def test_unavailable_slot_only_source_unavailable(self):
        for r in BINDING_RULES:
            if r.field_kind is FieldKind.PROP_LITERAL:
                continue
            slot = SEMANTIC_SLOTS[r.semantic_slot]
            if slot.availability is Availability.UNAVAILABLE:
                assert r.binding_state is BindingState.SOURCE_UNAVAILABLE, r

    def test_four_states_all_present(self):
        seen = {r.binding_state for r in BINDING_RULES}
        assert seen == {
            BindingState.FULLY_BINDABLE,
            BindingState.FLAT_PROJECTION_ONLY,
            BindingState.STRUCTURED_DEFERRED,
            BindingState.SOURCE_UNAVAILABLE,
        }


# --------------------------------------------------------------------------- #
# C. Listing projection
# --------------------------------------------------------------------------- #

class TestListingProjection:
    def test_listing_name_from_business_name(self):
        r = _rule("profile.header.business", FieldKind.CONTENT_SLOT, "name")
        assert r.semantic_slot == "listing_name"
        assert "business_name" in r.source_rule

    def test_listing_description_mapping(self):
        r = _rule("content.description.business", FieldKind.CONTENT_SLOT, "description")
        assert r.semantic_slot == "listing_description"

    def test_listing_ref_flat_projection_to_name(self):
        for cid in ("listing.card.standard", "listing.row.compact",
                    "listing.card.featured", "listing.card.sponsored"):
            r = _rule(cid, FieldKind.PROP_REF, "listing_ref")
            assert r.expected_type == "LISTING_REF"
            assert r.semantic_slot == "listing_name"
            assert r.binding_state is BindingState.FLAT_PROJECTION_ONLY

    def test_contact_hours_rating_are_flat_projection(self):
        assert _rule("profile.contact.panel", FieldKind.CONTENT_SLOT, "contact_info").binding_state \
            is BindingState.FLAT_PROJECTION_ONLY
        assert _rule("profile.hours.table", FieldKind.CONTENT_SLOT, "hours").binding_state \
            is BindingState.FLAT_PROJECTION_ONLY
        assert _rule("trust.reviews.summary", FieldKind.CONTENT_SLOT, "rating_summary").binding_state \
            is BindingState.FLAT_PROJECTION_ONLY

    def test_sponsorship_disclosure_mapping(self):
        r = _rule("listing.card.sponsored", FieldKind.CONTENT_SLOT, "disclosure")
        assert r.semantic_slot == "listing_disclosure"
        assert r.binding_state is BindingState.FULLY_BINDABLE

    def test_result_count_derivation(self):
        r = _rule("directory.results.summary", FieldKind.CONTENT_SLOT, "summary_text")
        assert r.semantic_slot == "result_summary"
        assert "result_count" in r.source_rule

    def test_category_and_location_tiles_deferred(self):
        assert _rule("directory.categories.grid", FieldKind.CONTENT_SLOT, "category_tiles").binding_state \
            is BindingState.STRUCTURED_DEFERRED
        assert _rule("directory.locations.grid", FieldKind.CONTENT_SLOT, "location_tiles").binding_state \
            is BindingState.STRUCTURED_DEFERRED

    def test_gallery_is_structured_deferred_not_unavailable(self):
        r = _rule("profile.gallery.standard", FieldKind.CONTENT_SLOT, "images")
        assert r.binding_state is BindingState.STRUCTURED_DEFERRED


# --------------------------------------------------------------------------- #
# D. Navigation
# --------------------------------------------------------------------------- #

class TestNavigation:
    def test_header_nav_maps_to_primary_navigation_deferred(self):
        for cid in ("nav.header.standard", "nav.mobile.drawer"):
            r = _rule(cid, FieldKind.PROP_REF, "nav_tree")
            assert r.semantic_slot == "primary_navigation"
            assert r.binding_state is BindingState.STRUCTURED_DEFERRED

    def test_footer_nav_maps_to_footer_navigation_deferred(self):
        r = _rule("legal.footer.directory", FieldKind.PROP_REF, "nav_tree")
        assert r.semantic_slot == "footer_navigation"
        assert r.binding_state is BindingState.STRUCTURED_DEFERRED

    def test_no_navigation_rule_claims_full_binding(self):
        for r in BINDING_RULES:
            if r.semantic_slot in ("primary_navigation", "footer_navigation"):
                assert r.binding_state is BindingState.STRUCTURED_DEFERRED

    def test_breadcrumb_deferred(self):
        r = _rule("nav.breadcrumbs.standard", FieldKind.PROP_REF, "trail")
        assert r.semantic_slot == "breadcrumb_trail"
        assert r.binding_state is BindingState.STRUCTURED_DEFERRED


# --------------------------------------------------------------------------- #
# E. Scope / cardinality (via the referenced semantic slots)
# --------------------------------------------------------------------------- #

class TestScopeCardinality:
    def test_referenced_slots_have_valid_scope_and_cardinality(self):
        from engines.website_generation.constants.content_slots import (
            SlotScope,
            VALID_CARDINALITIES,
        )

        for name in referenced_semantic_slots():
            slot = SEMANTIC_SLOTS[name]
            assert isinstance(slot.scope, SlotScope)
            assert slot.cardinality in VALID_CARDINALITIES

    def test_listing_scope_slots_are_listing_scoped(self):
        from engines.website_generation.constants.content_slots import SlotScope

        for name in ("listing_name", "listing_description", "listing_contact",
                     "listing_hours", "listing_rating"):
            assert SEMANTIC_SLOTS[name].scope is SlotScope.LISTING

    def test_rules_for_component_returns_declared_order_subset(self):
        rules = rules_for_component("hero.local.standard")
        names = [r.field_name for r in rules]
        assert "h1" in names and "intro" in names and "context_role" in names
        for r in rules:
            assert r.component_id == "hero.local.standard"
