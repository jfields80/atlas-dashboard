"""PTF-DISCOVERY-P0-001 -- source-family taxonomy tests."""

from __future__ import annotations

import pytest

from scripts.pettripfinder.discovery.source_families import (
    CONCRETE_SOURCE_FAMILY,
    FAMILY_CHAIN,
    FAMILY_CVB,
    FAMILY_DIRECTORY,
    FAMILY_GDS,
    FAMILY_OTA,
    FAMILY_REGISTRY,
    SOURCE_FAMILIES,
    SourceFamilyError,
    collapse_families,
    family_of,
    validate_non_independent_pairs,
)


class TestTaxonomy:
    def test_exactly_ten_families(self):
        assert len(SOURCE_FAMILIES) == 10

    def test_every_mapped_concrete_source_has_a_known_family(self):
        for source, family in CONCRETE_SOURCE_FAMILY.items():
            assert family in SOURCE_FAMILIES, source

    def test_cleveland_census_sources_are_all_cvb(self):
        for source in ("destination_cleveland", "akron_summit_cvb",
                       "stark_county_cvb", "destination_hudson"):
            assert family_of(source) == FAMILY_CVB

    def test_pittsburgh_factory_sources_are_mapped(self):
        assert family_of("visit_pittsburgh") == FAMILY_CVB
        assert family_of("cultural_trust") == FAMILY_CVB
        for source in ("paacc", "east_liberty_chamber", "gpha", "parks_conservancy"):
            assert family_of(source) == FAMILY_DIRECTORY
        assert family_of("city_parks") == FAMILY_REGISTRY
        assert family_of("avets") == FAMILY_CHAIN
        assert family_of("veg_pittsburgh") == FAMILY_CHAIN

    def test_dbpr_is_registry(self):
        assert family_of("fl_dbpr_lodging") == FAMILY_REGISTRY

    def test_unmapped_source_is_an_answer_not_an_error(self):
        assert family_of("some_future_source") == ""

    def test_override_extends_without_editing_code(self):
        assert family_of("expedia", {"expedia": FAMILY_OTA}) == FAMILY_OTA

    def test_override_to_unknown_family_fails_closed(self):
        with pytest.raises(SourceFamilyError):
            family_of("x", {"x": "SOCIAL_MEDIA"})


class TestIndependenceCollapse:
    def test_default_is_every_family_independent(self):
        assert collapse_families([FAMILY_CVB, FAMILY_OTA, FAMILY_GDS]) == {
            FAMILY_CVB, FAMILY_OTA, FAMILY_GDS}

    def test_declared_pair_counts_as_one_voice(self):
        voices = collapse_families([FAMILY_OTA, FAMILY_GDS],
                                   [(FAMILY_OTA, FAMILY_GDS)])
        assert len(voices) == 1

    def test_collapse_is_transitive(self):
        voices = collapse_families(
            [FAMILY_OTA, FAMILY_GDS, FAMILY_CVB],
            [(FAMILY_OTA, FAMILY_GDS), (FAMILY_GDS, FAMILY_CVB)])
        assert len(voices) == 1

    def test_pair_absent_from_input_changes_nothing(self):
        voices = collapse_families([FAMILY_CVB],
                                   [(FAMILY_OTA, FAMILY_GDS)])
        assert voices == {FAMILY_CVB}

    def test_empty_strings_are_not_voices(self):
        assert collapse_families(["", FAMILY_CVB, ""]) == {FAMILY_CVB}

    def test_malformed_pair_fails_closed(self):
        with pytest.raises(SourceFamilyError):
            validate_non_independent_pairs([(FAMILY_OTA,)])
        with pytest.raises(SourceFamilyError):
            validate_non_independent_pairs([(FAMILY_OTA, "NOT_A_FAMILY")])
        with pytest.raises(SourceFamilyError):
            validate_non_independent_pairs([(FAMILY_OTA, FAMILY_OTA)])
