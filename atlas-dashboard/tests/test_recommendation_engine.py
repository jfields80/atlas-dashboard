"""Tests for the deterministic Website Intelligence recommendation engine.

AES-005A Part 2.

Covers: recommendation generation, merging, ordering, priority assignment,
duplicate prevention, determinism, empty input, mixed severity, category
grouping, stable IDs, and regression safety against Part 1.
"""

import pytest

from engines.website_intelligence.constants import (
    CATEGORY_COMMERCIAL,
    CATEGORY_CONTENT,
    CATEGORY_DIRECTORY,
    CATEGORY_MONETIZATION,
    CATEGORY_NAVIGATION,
    CATEGORY_SEO,
    CATEGORY_UX,
    ENGINE_NAME,
    ENGINE_VERSION,
    PRIORITIES,
    PRIORITY_HIGH,
    PRIORITY_LOW,
    PRIORITY_MEDIUM,
    SCORE_CATEGORIES,
    SEVERITIES,
    SEVERITY_CRITICAL,
    SEVERITY_INFO,
    SEVERITY_WARNING,
)
from engines.website_intelligence.models import (
    WebsiteAuditFinding,
    WebsiteAuditRecommendation,
)
from engines.website_intelligence.recommendation_engine import (
    SEVERITY_PRIORITY_MAP,
    RecommendationEngine,
    generate_recommendations,
    priority_for_severity,
    recommendation_description_for,
    recommendation_id_for,
    recommendation_title_for,
    validate_findings,
)
from engines.website_intelligence.scoring_engine import ScoringEngine, stable_id

# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def make_finding(**overrides):
    data = {
        "finding_id": "find-abc123",
        "category": CATEGORY_SEO,
        "severity": SEVERITY_WARNING,
        "title": "Missing meta descriptions",
        "description": "3 of 40 pages lack meta descriptions.",
        "evidence": "pages: /about, /contact, /faq",
    }
    data.update(overrides)
    return WebsiteAuditFinding(**data)


def make_meta_findings(count=5):
    """Build N findings that differ only by ID and evidence (mergeable)."""
    return tuple(
        make_finding(
            finding_id=f"find-meta-{index:03d}",
            evidence=f"page: /page-{index:03d}",
        )
        for index in range(count)
    )


# ---------------------------------------------------------------------------
# Severity -> priority mapping
# ---------------------------------------------------------------------------


class TestPriorityMapping:
    def test_map_covers_every_severity(self):
        assert set(SEVERITY_PRIORITY_MAP.keys()) == set(SEVERITIES)

    def test_map_values_are_valid_priorities(self):
        assert set(SEVERITY_PRIORITY_MAP.values()) <= set(PRIORITIES)

    def test_critical_maps_to_high(self):
        assert priority_for_severity(SEVERITY_CRITICAL) == PRIORITY_HIGH

    def test_warning_maps_to_medium(self):
        assert priority_for_severity(SEVERITY_WARNING) == PRIORITY_MEDIUM

    def test_info_maps_to_low(self):
        assert priority_for_severity(SEVERITY_INFO) == PRIORITY_LOW

    def test_unknown_severity_rejected(self):
        with pytest.raises(ValueError):
            priority_for_severity("BLOCKER")


# ---------------------------------------------------------------------------
# Finding validation
# ---------------------------------------------------------------------------


class TestFindingValidation:
    def test_valid_findings_pass(self):
        validate_findings(make_meta_findings())  # must not raise

    def test_non_finding_rejected(self):
        with pytest.raises(ValueError):
            validate_findings(({"finding_id": "f1"},))

    def test_unknown_severity_rejected(self):
        with pytest.raises(ValueError):
            validate_findings((make_finding(severity="BLOCKER"),))

    def test_unknown_category_rejected(self):
        with pytest.raises(ValueError):
            validate_findings((make_finding(category="performance"),))

    def test_conflicting_duplicate_ids_rejected(self):
        first = make_finding(finding_id="find-x", title="Missing meta descriptions")
        second = make_finding(finding_id="find-x", title="Broken internal link")
        with pytest.raises(ValueError):
            validate_findings((first, second))

    def test_exact_duplicate_findings_allowed(self):
        finding = make_finding()
        validate_findings((finding, finding))  # must not raise


# ---------------------------------------------------------------------------
# Recommendation generation
# ---------------------------------------------------------------------------


class TestGeneration:
    def test_empty_input_returns_empty_tuple(self):
        assert generate_recommendations(()) == ()

    def test_output_is_tuple_of_recommendations(self):
        result = generate_recommendations((make_finding(),))
        assert isinstance(result, tuple)
        assert all(isinstance(rec, WebsiteAuditRecommendation) for rec in result)

    def test_single_finding_single_recommendation(self):
        result = generate_recommendations((make_finding(),))
        assert len(result) == 1

    def test_recommendation_category_matches_finding(self):
        (rec,) = generate_recommendations((make_finding(category=CATEGORY_UX),))
        assert rec.category == CATEGORY_UX

    def test_recommendation_carries_finding_id(self):
        (rec,) = generate_recommendations((make_finding(finding_id="find-777"),))
        assert rec.finding_ids == ("find-777",)

    def test_critical_finding_yields_high_priority(self):
        (rec,) = generate_recommendations((make_finding(severity=SEVERITY_CRITICAL),))
        assert rec.priority == PRIORITY_HIGH

    def test_warning_finding_yields_medium_priority(self):
        (rec,) = generate_recommendations((make_finding(severity=SEVERITY_WARNING),))
        assert rec.priority == PRIORITY_MEDIUM

    def test_info_finding_yields_low_priority(self):
        (rec,) = generate_recommendations((make_finding(severity=SEVERITY_INFO),))
        assert rec.priority == PRIORITY_LOW

    def test_output_recommendations_are_immutable(self):
        (rec,) = generate_recommendations((make_finding(),))
        with pytest.raises(Exception):
            rec.priority = PRIORITY_LOW

    def test_invalid_finding_propagates_error(self):
        with pytest.raises(ValueError):
            generate_recommendations((make_finding(severity="BLOCKER"),))


# ---------------------------------------------------------------------------
# Deterministic wording
# ---------------------------------------------------------------------------


class TestWording:
    def test_critical_title_template(self):
        (rec,) = generate_recommendations(
            (make_finding(severity=SEVERITY_CRITICAL, title="Broken homepage"),)
        )
        assert rec.title == "Fix critical issue: Broken homepage"

    def test_warning_title_template(self):
        (rec,) = generate_recommendations(
            (make_finding(severity=SEVERITY_WARNING, title="Missing meta descriptions"),)
        )
        assert rec.title == "Address warning: Missing meta descriptions"

    def test_info_title_template(self):
        (rec,) = generate_recommendations(
            (make_finding(severity=SEVERITY_INFO, title="Short page titles"),)
        )
        assert rec.title == "Consider improvement: Short page titles"

    def test_description_includes_count_category_severity(self):
        recs = generate_recommendations(make_meta_findings(5))
        (rec,) = recs
        assert rec.description == (
            "Resolve 5 occurrence(s) of 'Missing meta descriptions' in the "
            "'seo' category (severity: WARNING)."
        )

    def test_title_helper_rejects_unknown_severity(self):
        with pytest.raises(ValueError):
            recommendation_title_for("BLOCKER", "x")

    def test_description_helper_rejects_zero_count(self):
        with pytest.raises(ValueError):
            recommendation_description_for(0, "t", CATEGORY_SEO, SEVERITY_INFO)

    def test_wording_never_references_ai(self):
        recs = generate_recommendations(
            tuple(
                make_finding(finding_id=f"find-{severity}", severity=severity)
                for severity in SEVERITIES
            )
        )
        for rec in recs:
            combined = (rec.title + " " + rec.description).lower()
            for banned in ("ai", "chatgpt", "claude", "gpt", "llm"):
                assert banned not in combined.split()


# ---------------------------------------------------------------------------
# Merging
# ---------------------------------------------------------------------------


class TestMerging:
    def test_five_equivalent_findings_merge_to_one(self):
        recs = generate_recommendations(make_meta_findings(5))
        assert len(recs) == 1

    def test_merged_recommendation_carries_all_finding_ids(self):
        recs = generate_recommendations(make_meta_findings(5))
        (rec,) = recs
        assert rec.finding_ids == tuple(f"find-meta-{i:03d}" for i in range(5))

    def test_finding_ids_are_sorted(self):
        findings = tuple(reversed(make_meta_findings(5)))
        (rec,) = generate_recommendations(findings)
        assert rec.finding_ids == tuple(sorted(rec.finding_ids))

    def test_different_titles_do_not_merge(self):
        first = make_finding(finding_id="f1", title="Missing meta descriptions")
        second = make_finding(finding_id="f2", title="Broken internal link")
        assert len(generate_recommendations((first, second))) == 2

    def test_different_categories_do_not_merge(self):
        first = make_finding(finding_id="f1", category=CATEGORY_SEO)
        second = make_finding(finding_id="f2", category=CATEGORY_CONTENT)
        assert len(generate_recommendations((first, second))) == 2

    def test_different_severities_do_not_merge(self):
        first = make_finding(finding_id="f1", severity=SEVERITY_WARNING)
        second = make_finding(finding_id="f2", severity=SEVERITY_CRITICAL)
        assert len(generate_recommendations((first, second))) == 2

    def test_merge_ignores_description_and_evidence_differences(self):
        first = make_finding(finding_id="f1", description="a", evidence="x")
        second = make_finding(finding_id="f2", description="b", evidence="y")
        assert len(generate_recommendations((first, second))) == 1


# ---------------------------------------------------------------------------
# Duplicate prevention
# ---------------------------------------------------------------------------


class TestDuplicatePrevention:
    def test_exact_duplicate_findings_collapse(self):
        finding = make_finding()
        (rec,) = generate_recommendations((finding, finding, finding))
        assert rec.finding_ids == (finding.finding_id,)

    def test_no_duplicate_recommendation_ids_in_output(self):
        findings = make_meta_findings(4) + tuple(
            make_finding(
                finding_id=f"find-{category}",
                category=category,
                severity=SEVERITY_INFO,
                title="Thin content",
            )
            for category in SCORE_CATEGORIES
        )
        recs = generate_recommendations(findings)
        ids = [rec.recommendation_id for rec in recs]
        assert len(ids) == len(set(ids))

    def test_conflicting_duplicate_ids_rejected(self):
        first = make_finding(finding_id="find-x", severity=SEVERITY_WARNING)
        second = make_finding(finding_id="find-x", severity=SEVERITY_CRITICAL)
        with pytest.raises(ValueError):
            generate_recommendations((first, second))


# ---------------------------------------------------------------------------
# Ordering
# ---------------------------------------------------------------------------


class TestOrdering:
    def test_priority_order_high_medium_low(self):
        findings = (
            make_finding(finding_id="f-info", severity=SEVERITY_INFO, title="C"),
            make_finding(finding_id="f-crit", severity=SEVERITY_CRITICAL, title="A"),
            make_finding(finding_id="f-warn", severity=SEVERITY_WARNING, title="B"),
        )
        recs = generate_recommendations(findings)
        assert [rec.priority for rec in recs] == [
            PRIORITY_HIGH,
            PRIORITY_MEDIUM,
            PRIORITY_LOW,
        ]

    def test_category_order_within_priority(self):
        findings = tuple(
            make_finding(
                finding_id=f"find-{category}",
                category=category,
                severity=SEVERITY_WARNING,
                title="Thin content",
            )
            for category in reversed(SCORE_CATEGORIES)
        )
        recs = generate_recommendations(findings)
        assert tuple(rec.category for rec in recs) == SCORE_CATEGORIES

    def test_title_order_within_category(self):
        findings = (
            make_finding(finding_id="f1", title="Zulu issue"),
            make_finding(finding_id="f2", title="Alpha issue"),
            make_finding(finding_id="f3", title="Mike issue"),
        )
        recs = generate_recommendations(findings)
        titles = [rec.title for rec in recs]
        assert titles == sorted(titles)

    def test_input_order_does_not_affect_output(self):
        findings = (
            make_finding(finding_id="f1", severity=SEVERITY_INFO, category=CATEGORY_UX),
            make_finding(finding_id="f2", severity=SEVERITY_CRITICAL, category=CATEGORY_SEO),
            make_finding(finding_id="f3", severity=SEVERITY_WARNING, category=CATEGORY_DIRECTORY),
            make_finding(finding_id="f4", severity=SEVERITY_WARNING, category=CATEGORY_DIRECTORY, title="Other"),
        )
        assert generate_recommendations(findings) == generate_recommendations(
            tuple(reversed(findings))
        )

    def test_ordering_is_total(self):
        findings = make_meta_findings(3) + tuple(
            make_finding(
                finding_id=f"find-x-{category}-{severity}",
                category=category,
                severity=severity,
                title=f"Issue {category}",
            )
            for category in (CATEGORY_NAVIGATION, CATEGORY_COMMERCIAL, CATEGORY_MONETIZATION)
            for severity in SEVERITIES
        )
        recs = generate_recommendations(findings)
        keys = [
            (PRIORITIES.index(r.priority), SCORE_CATEGORIES.index(r.category), r.title, r.recommendation_id)
            for r in recs
        ]
        assert keys == sorted(keys)


# ---------------------------------------------------------------------------
# Stable IDs
# ---------------------------------------------------------------------------


class TestStableIds:
    def test_id_uses_rec_prefix(self):
        (rec,) = generate_recommendations((make_finding(),))
        assert rec.recommendation_id.startswith("rec-")

    def test_id_matches_stable_id_convention(self):
        finding = make_finding()
        (rec,) = generate_recommendations((finding,))
        assert rec.recommendation_id == stable_id(
            "rec", finding.category, finding.severity, finding.title
        )

    def test_identical_merge_key_identical_id(self):
        assert recommendation_id_for(
            CATEGORY_SEO, SEVERITY_WARNING, "Missing meta descriptions"
        ) == recommendation_id_for(
            CATEGORY_SEO, SEVERITY_WARNING, "Missing meta descriptions"
        )

    def test_different_titles_different_ids(self):
        first = recommendation_id_for(CATEGORY_SEO, SEVERITY_WARNING, "A")
        second = recommendation_id_for(CATEGORY_SEO, SEVERITY_WARNING, "B")
        assert first != second

    def test_id_independent_of_evidence_and_finding_ids(self):
        one = generate_recommendations((make_finding(finding_id="f1", evidence="x"),))
        many = generate_recommendations(make_meta_findings(5))
        assert one[0].recommendation_id == many[0].recommendation_id


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def _mixed_findings(self):
        return make_meta_findings(3) + (
            make_finding(
                finding_id="find-crit-1",
                category=CATEGORY_DIRECTORY,
                severity=SEVERITY_CRITICAL,
                title="No listings rendered",
            ),
            make_finding(
                finding_id="find-info-1",
                category=CATEGORY_UX,
                severity=SEVERITY_INFO,
                title="Small tap targets",
            ),
        )

    def test_identical_input_identical_output(self):
        findings = self._mixed_findings()
        assert generate_recommendations(findings) == generate_recommendations(findings)

    def test_repeated_runs_are_byte_identical(self):
        findings = self._mixed_findings()
        results = {repr(generate_recommendations(findings)) for _ in range(50)}
        assert len(results) == 1

    def test_mixed_severity_counts(self):
        recs = generate_recommendations(self._mixed_findings())
        priorities = [rec.priority for rec in recs]
        assert priorities.count(PRIORITY_HIGH) == 1
        assert priorities.count(PRIORITY_MEDIUM) == 1
        assert priorities.count(PRIORITY_LOW) == 1


# ---------------------------------------------------------------------------
# Engine facade + regression safety
# ---------------------------------------------------------------------------


class TestEngineFacade:
    def test_engine_identity(self):
        engine = RecommendationEngine()
        assert engine.engine_name == ENGINE_NAME
        assert engine.engine_version == ENGINE_VERSION

    def test_facade_matches_module_function(self):
        findings = make_meta_findings(4)
        assert RecommendationEngine().recommend(findings) == generate_recommendations(
            findings
        )

    def test_facade_empty_input(self):
        assert RecommendationEngine().recommend(()) == ()


class TestRegressionSafety:
    def test_part1_scoring_engine_unaffected(self):
        scores = {category: 80.0 for category in SCORE_CATEGORIES}
        result = ScoringEngine().score(scores)
        assert result.overall_score == 80.0
        assert result.grade == "B"

    def test_part1_stable_id_unaffected(self):
        assert stable_id("find", "seo", "missing-meta") == stable_id(
            "find", "seo", "missing-meta"
        )

    def test_recommendations_satisfy_part1_contract(self):
        recs = generate_recommendations(make_meta_findings(2))
        (rec,) = recs
        # Round-trip through the Part 1 contract to prove full compliance.
        rebuilt = WebsiteAuditRecommendation(
            recommendation_id=rec.recommendation_id,
            category=rec.category,
            priority=rec.priority,
            title=rec.title,
            description=rec.description,
            finding_ids=rec.finding_ids,
        )
        assert rebuilt == rec
