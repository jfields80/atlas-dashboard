"""Tests for Website Intelligence contract models (AES-005A Part 1).

Covers: construction, immutability, score range constraints, defaults,
tuple coercion, nested contracts, and Pydantic v1/v2 compatibility.
"""

import pytest
from pydantic import ValidationError

from engines.website_intelligence.constants import (
    CATEGORY_SEO,
    ENGINE_NAME,
    ENGINE_VERSION,
    PRIORITY_HIGH,
    SEVERITY_WARNING,
    WORK_ORDER_STATUS_PENDING,
)
from engines.website_intelligence.models import (
    PYDANTIC_V2,
    WebsiteAuditFinding,
    WebsiteAuditInput,
    WebsiteAuditRecommendation,
    WebsiteAuditReport,
    WebsiteWorkOrder,
)

# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def make_input(**overrides):
    data = {
        "project_assembly": {"slug": "pettripfinder"},
        "static_site_package": {"files": 12},
        "preview_build": {"pages": 40},
    }
    data.update(overrides)
    return WebsiteAuditInput(**data)


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


def make_recommendation(**overrides):
    data = {
        "recommendation_id": "rec-def456",
        "category": CATEGORY_SEO,
        "priority": PRIORITY_HIGH,
        "title": "Add meta descriptions",
        "description": "Write meta descriptions for the 3 affected pages.",
        "finding_ids": ("find-abc123",),
    }
    data.update(overrides)
    return WebsiteAuditRecommendation(**data)


def make_work_order(**overrides):
    data = {
        "work_order_id": "wo-789xyz",
        "recommendation_id": "rec-def456",
        "category": CATEGORY_SEO,
        "priority": PRIORITY_HIGH,
        "title": "Add meta descriptions",
        "instructions": "Add a unique meta description to each affected page.",
        "acceptance_criteria": ("Every page has a non-empty meta description.",),
    }
    data.update(overrides)
    return WebsiteWorkOrder(**data)


def make_report(**overrides):
    data = {
        "report_id": "rpt-000111",
        "engine_name": ENGINE_NAME,
        "engine_version": ENGINE_VERSION,
        "seo_score": 85.0,
        "navigation_score": 90.0,
        "content_score": 80.0,
        "directory_score": 88.0,
        "commercial_score": 75.0,
        "monetization_score": 60.0,
        "ux_score": 92.0,
        "overall_score": 82.05,
        "grade": "B",
        "launch_readiness": "REVIEW",
        "findings": (make_finding(),),
        "recommendations": (make_recommendation(),),
        "work_orders": (make_work_order(),),
    }
    data.update(overrides)
    return WebsiteAuditReport(**data)


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestConstruction:
    def test_audit_input_constructs(self):
        audit_input = make_input()
        assert audit_input.project_assembly == {"slug": "pettripfinder"}
        assert audit_input.static_site_package == {"files": 12}
        assert audit_input.preview_build == {"pages": 40}

    def test_audit_input_wraps_arbitrary_objects(self):
        class FakeAssembly:
            slug = "directbeef"

        audit_input = make_input(project_assembly=FakeAssembly())
        assert audit_input.project_assembly.slug == "directbeef"

    def test_audit_input_requires_all_three_artifacts(self):
        with pytest.raises(ValidationError):
            WebsiteAuditInput(project_assembly={"slug": "x"})

    def test_finding_constructs(self):
        finding = make_finding()
        assert finding.finding_id == "find-abc123"
        assert finding.category == CATEGORY_SEO
        assert finding.severity == SEVERITY_WARNING

    def test_finding_optional_fields_default_empty(self):
        finding = WebsiteAuditFinding(
            finding_id="f1",
            category=CATEGORY_SEO,
            severity=SEVERITY_WARNING,
            title="t",
        )
        assert finding.description == ""
        assert finding.evidence == ""

    def test_recommendation_constructs(self):
        rec = make_recommendation()
        assert rec.recommendation_id == "rec-def456"
        assert rec.finding_ids == ("find-abc123",)

    def test_recommendation_finding_ids_default_empty_tuple(self):
        rec = make_recommendation(finding_ids=())
        assert rec.finding_ids == ()

    def test_work_order_constructs(self):
        wo = make_work_order()
        assert wo.work_order_id == "wo-789xyz"
        assert wo.recommendation_id == "rec-def456"

    def test_work_order_status_defaults_to_pending(self):
        wo = make_work_order()
        assert wo.status == WORK_ORDER_STATUS_PENDING

    def test_report_constructs_with_nested_contracts(self):
        report = make_report()
        assert report.engine_name == ENGINE_NAME
        assert report.engine_version == ENGINE_VERSION
        assert len(report.findings) == 1
        assert len(report.recommendations) == 1
        assert len(report.work_orders) == 1
        assert isinstance(report.findings[0], WebsiteAuditFinding)

    def test_report_collections_default_empty(self):
        report = make_report(findings=(), recommendations=(), work_orders=())
        assert report.findings == ()
        assert report.recommendations == ()
        assert report.work_orders == ()

    def test_report_list_input_coerced_to_tuple(self):
        report = make_report(findings=[make_finding()])
        assert isinstance(report.findings, tuple)

    def test_required_id_must_be_non_empty(self):
        with pytest.raises(ValidationError):
            make_finding(finding_id="")


# ---------------------------------------------------------------------------
# Immutability
# ---------------------------------------------------------------------------


class TestImmutability:
    def test_audit_input_is_immutable(self):
        audit_input = make_input()
        with pytest.raises(Exception):
            audit_input.project_assembly = {"slug": "other"}

    def test_finding_is_immutable(self):
        finding = make_finding()
        with pytest.raises(Exception):
            finding.title = "changed"

    def test_recommendation_is_immutable(self):
        rec = make_recommendation()
        with pytest.raises(Exception):
            rec.priority = "LOW"

    def test_work_order_is_immutable(self):
        wo = make_work_order()
        with pytest.raises(Exception):
            wo.status = "APPROVED"

    def test_report_is_immutable(self):
        report = make_report()
        with pytest.raises(Exception):
            report.overall_score = 99.0

    def test_report_collections_are_tuples(self):
        report = make_report()
        assert isinstance(report.findings, tuple)
        assert isinstance(report.recommendations, tuple)
        assert isinstance(report.work_orders, tuple)

    def test_nested_contract_is_immutable(self):
        report = make_report()
        with pytest.raises(Exception):
            report.findings[0].title = "changed"


# ---------------------------------------------------------------------------
# Score range constraints
# ---------------------------------------------------------------------------


class TestScoreRanges:
    @pytest.mark.parametrize(
        "field",
        [
            "seo_score",
            "navigation_score",
            "content_score",
            "directory_score",
            "commercial_score",
            "monetization_score",
            "ux_score",
            "overall_score",
        ],
    )
    def test_score_below_zero_rejected(self, field):
        with pytest.raises(ValidationError):
            make_report(**{field: -0.01})

    @pytest.mark.parametrize(
        "field",
        [
            "seo_score",
            "navigation_score",
            "content_score",
            "directory_score",
            "commercial_score",
            "monetization_score",
            "ux_score",
            "overall_score",
        ],
    )
    def test_score_above_hundred_rejected(self, field):
        with pytest.raises(ValidationError):
            make_report(**{field: 100.01})

    def test_score_boundaries_accepted(self):
        report = make_report(seo_score=0.0, ux_score=100.0)
        assert report.seo_score == 0.0
        assert report.ux_score == 100.0


# ---------------------------------------------------------------------------
# Pydantic compatibility
# ---------------------------------------------------------------------------


class TestPydanticCompatibility:
    def test_capability_detection_matches_runtime(self):
        import pydantic

        is_v2 = pydantic.VERSION.startswith("2")
        assert PYDANTIC_V2 == is_v2

    def test_only_one_immutability_mechanism_defined(self):
        # Never both model_config (v2) and a custom Config (v1) on our base.
        has_v2_config = "model_config" in WebsiteAuditFinding.__mro__[1].__dict__
        has_v1_config = "Config" in WebsiteAuditFinding.__mro__[1].__dict__
        assert has_v2_config != has_v1_config

    def test_serialization_round_trip(self):
        report = make_report()
        if PYDANTIC_V2:
            data = report.model_dump()
            rebuilt = WebsiteAuditReport(**data)
        else:  # pragma: no cover - Pydantic v1 runtime
            data = report.dict()
            rebuilt = WebsiteAuditReport(**data)
        assert rebuilt == report

    def test_equality_is_value_based(self):
        assert make_finding() == make_finding()
        assert make_finding() != make_finding(finding_id="find-other")