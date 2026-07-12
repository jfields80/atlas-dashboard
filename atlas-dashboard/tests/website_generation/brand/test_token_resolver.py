"""Token resolver internals: contrast math and family classification
(AES-WEB-001 §5.2).
"""

from __future__ import annotations

from engines.website_generation.contracts.artifacts import ArtifactKind, BusinessSpec
from engines.website_generation.constants.brand import (
    FAMILY_CIVIC_SLATE,
    FAMILY_FIELD_GUIDE,
    FAMILY_HARBOR_INK,
    FAMILY_MARKET_CLAY,
    FAMILY_ORDER,
    SANCTIONED_CONTRAST_PAIRS,
)
from engines.website_generation.brand.token_resolver import (
    break_family_tie,
    build_contrast_evidence,
    contrast_ratio_hundredths,
    resolve_family,
)


def _spec(**overrides) -> BusinessSpec:
    fields = dict(
        schema_version="1.0.0",
        artifact_kind=ArtifactKind.BUSINESS_SPEC,
        source_hashes={},
        business_name="Test Co",
        niche="",
        audience="",
        value_proposition="",
        directory_taxonomy=(),
    )
    fields.update(overrides)
    return BusinessSpec(**fields)


class TestContrastMath:
    def test_black_white_contrast_is_2100(self):
        assert contrast_ratio_hundredths("#000000", "#ffffff") == 2100

    def test_same_color_contrast_is_100(self):
        assert contrast_ratio_hundredths("#123456", "#123456") == 100

    def test_known_reference_gray_mid_pair(self):
        # #767676 on white is the commonly-cited "just clears 4.5:1" WCAG
        # reference gray (~4.54:1) — an independent, hand-verifiable value.
        assert contrast_ratio_hundredths("#767676", "#ffffff") == 454

    def test_contrast_ratio_is_symmetric(self):
        assert contrast_ratio_hundredths(
            "#2e5544", "#faf7f0"
        ) == contrast_ratio_hundredths("#faf7f0", "#2e5544")


class TestContrastEvidence:
    def test_every_family_clears_every_pair_by_at_least_10_hundredths(self):
        for family in FAMILY_ORDER:
            for record in build_contrast_evidence(family):
                margin = record.contrast_ratio_hundredths - record.required_hundredths
                assert margin >= 10, (
                    "%s %s x %s margin too small: %d"
                    % (family, record.foreground_token, record.background_token, margin)
                )

    def test_evidence_covers_every_sanctioned_pair(self):
        for family in FAMILY_ORDER:
            evidence = build_contrast_evidence(family)
            assert len(evidence) == len(SANCTIONED_CONTRAST_PAIRS)
            for record in evidence:
                assert record.passed is True

    def test_evidence_is_stably_sorted(self):
        for family in FAMILY_ORDER:
            evidence = build_contrast_evidence(family)
            keys = [(e.foreground_token, e.background_token) for e in evidence]
            assert keys == sorted(keys)

    def test_evidence_is_stable_across_repeated_calls(self):
        for family in FAMILY_ORDER:
            first = build_contrast_evidence(family)
            second = build_contrast_evidence(family)
            assert first == second

    def test_evidence_contains_no_floats(self):
        for family in FAMILY_ORDER:
            for record in build_contrast_evidence(family):
                assert isinstance(record.contrast_ratio_hundredths, int)
                assert not isinstance(record.contrast_ratio_hundredths, bool)
                assert isinstance(record.required_hundredths, int)
                assert not isinstance(record.required_hundredths, bool)
                assert isinstance(record.foreground_token, str)
                assert isinstance(record.background_token, str)
                assert isinstance(record.passed, bool)


class TestFamilyClassification:
    def test_field_guide_keywords_resolve_to_field_guide(self):
        spec = _spec(
            niche="pet-friendly travel",
            audience="traveling pet owners",
            value_proposition="Find verified pet-friendly stays fast",
            directory_taxonomy=("hotels", "parks", "restaurants"),
        )
        assert resolve_family(spec) == FAMILY_FIELD_GUIDE

    def test_civic_slate_keywords_resolve_to_civic_slate(self):
        spec = _spec(
            niche="professional legal services",
            audience="B2B clients",
            value_proposition="Reliable professional services",
        )
        assert resolve_family(spec) == FAMILY_CIVIC_SLATE

    def test_market_clay_keywords_resolve_to_market_clay(self):
        spec = _spec(
            niche="local commerce",
            audience="neighborhood shoppers",
            value_proposition="Fresh craft goods at the market",
        )
        assert resolve_family(spec) == FAMILY_MARKET_CLAY

    def test_harbor_ink_keywords_resolve_to_harbor_ink(self):
        spec = _spec(
            niche="data analytics",
            audience="finance teams",
            value_proposition="Technology-driven analytics platform",
        )
        assert resolve_family(spec) == FAMILY_HARBOR_INK

    def test_business_name_is_not_used_for_classification(self):
        # "Hotel"/"Legal"/"Market"/"Data" all appear in business_name only;
        # niche/audience/value_proposition/taxonomy contain no keyword, so
        # classification must fall through to the harbor_ink fallback.
        spec = _spec(
            business_name="Hotel Legal Market Data Co",
            niche="zzz",
            audience="zzz",
            value_proposition="zzz",
        )
        assert resolve_family(spec) == FAMILY_HARBOR_INK

    def test_fallback_works_when_nothing_matches(self):
        spec = _spec(niche="zzz", audience="zzz", value_proposition="zzz")
        assert resolve_family(spec) == FAMILY_HARBOR_INK

    def test_classification_is_deterministic(self):
        spec = _spec(
            niche="pet-friendly travel",
            audience="traveling pet owners",
            value_proposition="Find verified pet-friendly stays fast",
        )
        assert resolve_family(spec) == resolve_family(spec)


class TestTieBreaking:
    def test_single_candidate_returns_unchanged(self):
        spec = _spec(niche="n", audience="a", value_proposition="v")
        assert break_family_tie((FAMILY_FIELD_GUIDE,), spec) == FAMILY_FIELD_GUIDE

    def test_tie_break_is_independent_of_candidate_order(self):
        spec = _spec(niche="n", audience="a", value_proposition="v")
        forward = break_family_tie((FAMILY_CIVIC_SLATE, FAMILY_MARKET_CLAY), spec)
        backward = break_family_tie((FAMILY_MARKET_CLAY, FAMILY_CIVIC_SLATE), spec)
        assert forward == backward

    def test_tie_break_is_stable_across_repeated_calls(self):
        spec = _spec(niche="n", audience="a", value_proposition="v")
        candidates = (FAMILY_CIVIC_SLATE, FAMILY_MARKET_CLAY, FAMILY_HARBOR_INK)
        first = break_family_tie(candidates, spec)
        second = break_family_tie(candidates, spec)
        assert first == second
        assert first in candidates

    def test_tie_break_depends_on_spec_content(self):
        candidates = (FAMILY_CIVIC_SLATE, FAMILY_MARKET_CLAY, FAMILY_HARBOR_INK)
        spec_a = _spec(niche="alpha", audience="a", value_proposition="v")
        spec_b = _spec(niche="beta", audience="a", value_proposition="v")
        # Not asserted to differ (a hash collision on the bucket index is
        # possible), but each must independently be stable and valid.
        result_a = break_family_tie(candidates, spec_a)
        result_b = break_family_tie(candidates, spec_b)
        assert result_a in candidates
        assert result_b in candidates
        assert result_a == break_family_tie(candidates, spec_a)
        assert result_b == break_family_tie(candidates, spec_b)

    def test_tie_break_never_uses_python_hash(self):
        import ast
        from pathlib import Path

        path = (
            Path(__file__).resolve().parents[3]
            / "engines" / "website_generation" / "brand" / "token_resolver.py"
        )
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id != "hash"
