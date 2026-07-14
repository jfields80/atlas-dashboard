"""Semantic content-slot vocabulary tests (AES-WEB-002J.18;
ADR-WEB-CONTENT-BINDING-MAP).

Covers group A (vocabulary) and F (IA/content constant expansion): every
semantic slot is well-formed, uniquely named, honestly classified, and the
additive IA/content constants preserve existing behavior while resolving the
editorial aliases against the vocabulary.
"""

from __future__ import annotations

from engines.website_generation.constants.content_slots import (
    SEMANTIC_SLOTS,
    Availability,
    SourceOwner,
    SlotScope,
    VALID_CARDINALITIES,
    is_flat_bindable,
    semantic_slot,
)
from engines.website_generation.constants import content as content_constants
from engines.website_generation.constants import ia as ia_constants


# --------------------------------------------------------------------------- #
# A. Vocabulary
# --------------------------------------------------------------------------- #

class TestVocabulary:
    def test_nonempty(self):
        assert len(SEMANTIC_SLOTS) >= 30

    def test_every_slot_name_unique_and_matches_key(self):
        for name, slot in SEMANTIC_SLOTS.items():
            assert slot.name == name
        assert len(SEMANTIC_SLOTS) == len({s.name for s in SEMANTIC_SLOTS.values()})

    def test_every_slot_has_owner_source_blocktype(self):
        for slot in SEMANTIC_SLOTS.values():
            assert isinstance(slot.source_owner, SourceOwner)
            assert slot.source_key, slot.name
            assert slot.block_type, slot.name

    def test_every_slot_scope_and_cardinality_valid(self):
        for slot in SEMANTIC_SLOTS.values():
            assert isinstance(slot.scope, SlotScope)
            assert slot.cardinality in VALID_CARDINALITIES, slot.name

    def test_flags_are_bools_and_availability_typed(self):
        for slot in SEMANTIC_SLOTS.values():
            assert isinstance(slot.flat_ok, bool)
            assert isinstance(slot.structured_deferred, bool)
            assert isinstance(slot.availability, Availability)

    def test_no_placeholder_source_keys(self):
        for slot in SEMANTIC_SLOTS.values():
            assert "resolved" not in slot.source_key.lower(), slot.name

    def test_structured_deferred_is_not_flat_ok(self):
        # A slot flat text cannot honestly carry must not also claim flat_ok.
        for slot in SEMANTIC_SLOTS.values():
            if slot.structured_deferred:
                assert not slot.flat_ok, slot.name

    def test_unavailable_source_owner_matches_availability(self):
        for slot in SEMANTIC_SLOTS.values():
            if slot.source_owner is SourceOwner.UNAVAILABLE:
                assert slot.availability is Availability.UNAVAILABLE, slot.name

    def test_is_flat_bindable_only_for_available_flat_slots(self):
        for slot in SEMANTIC_SLOTS.values():
            if is_flat_bindable(slot):
                assert slot.flat_ok and not slot.structured_deferred
                assert slot.availability in (Availability.AVAILABLE, Availability.DERIVABLE)

    def test_navigation_slots_are_structured_deferred(self):
        # No raw-route-label workaround: nav/tiles are never fully bindable.
        for name in ("primary_navigation", "footer_navigation", "category_tiles",
                     "location_tiles"):
            slot = semantic_slot(name)
            assert slot.structured_deferred is True
            assert slot.availability is Availability.DEFERRED

    def test_flat_editorial_slots_available(self):
        for name in ("page_h1", "page_intro", "listing_name", "listing_description"):
            slot = semantic_slot(name)
            assert slot.flat_ok and not slot.structured_deferred
            assert slot.availability is Availability.AVAILABLE

    def test_result_summary_is_derivable(self):
        assert semantic_slot("result_summary").availability is Availability.DERIVABLE

    def test_structured_listing_slots_deferred(self):
        for name in ("listing_contact", "listing_hours", "listing_rating"):
            assert semantic_slot(name).structured_deferred is True


# --------------------------------------------------------------------------- #
# F. IA / content constant expansion (behavior preservation)
# --------------------------------------------------------------------------- #

class TestIaConstants:
    def test_existing_content_slots_by_role_unchanged(self):
        assert ia_constants.CONTENT_SLOTS_BY_ROLE == {
            "home": ("hero_h1", "intro"),
            "category": ("hero_h1", "intro"),
        }

    def test_semantic_requirements_only_for_current_roles(self):
        assert set(ia_constants.SEMANTIC_REQUIREMENTS_BY_ROLE) == {"home", "category"}

    def test_semantic_requirement_slots_resolve_to_vocabulary(self):
        for role, groups in ia_constants.SEMANTIC_REQUIREMENTS_BY_ROLE.items():
            for kind in ("required", "deferred"):
                for name in groups[kind]:
                    assert name in SEMANTIC_SLOTS, (role, kind, name)

    def test_required_semantic_slots_are_flat_bindable(self):
        for role, groups in ia_constants.SEMANTIC_REQUIREMENTS_BY_ROLE.items():
            for name in groups["required"]:
                assert is_flat_bindable(SEMANTIC_SLOTS[name]), (role, name)

    def test_deferred_semantic_slots_are_not_flat_bindable(self):
        for role, groups in ia_constants.SEMANTIC_REQUIREMENTS_BY_ROLE.items():
            for name in groups["deferred"]:
                assert not is_flat_bindable(SEMANTIC_SLOTS[name]), (role, name)

    def test_ia_alias_bridge_resolves(self):
        assert ia_constants.IA_SLOT_TO_SEMANTIC == {
            "hero_h1": "page_h1",
            "intro": "page_intro",
        }
        for semantic in ia_constants.IA_SLOT_TO_SEMANTIC.values():
            assert semantic in SEMANTIC_SLOTS


class TestContentConstants:
    def test_supported_slot_ids_unchanged(self):
        # Content Engine behavior preserved: the active accepted vocabulary is
        # still exactly hero_h1/intro (the additive editorial vocabulary is
        # separate groundwork, not wired into SUPPORTED_SLOT_IDS).
        assert set(content_constants.SUPPORTED_SLOT_IDS) == {"hero_h1", "intro"}
        assert set(content_constants.SLOT_MIN_LENGTHS) == set(content_constants.SUPPORTED_SLOT_IDS)
        assert set(content_constants.SLOT_MAX_LENGTHS) == set(content_constants.SUPPORTED_SLOT_IDS)

    def test_editorial_vocabulary_resolves_to_semantic_slots(self):
        for name in content_constants.EDITORIAL_SEMANTIC_SLOTS:
            assert name in SEMANTIC_SLOTS, name

    def test_editorial_slots_are_flat_editorial_only(self):
        # No structured slot is falsely added as plain text.
        for name in content_constants.EDITORIAL_SEMANTIC_SLOTS:
            slot = SEMANTIC_SLOTS[name]
            assert slot.flat_ok and not slot.structured_deferred, name

    def test_editorial_length_bounds_well_formed(self):
        for name, (lo, hi) in content_constants.EDITORIAL_SEMANTIC_SLOT_LENGTHS.items():
            assert name in content_constants.EDITORIAL_SEMANTIC_SLOTS
            assert 0 <= lo < hi

    def test_editorial_length_table_covers_vocabulary(self):
        assert set(content_constants.EDITORIAL_SEMANTIC_SLOT_LENGTHS) == set(
            content_constants.EDITORIAL_SEMANTIC_SLOTS
        )
