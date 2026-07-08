"""Tests for the deterministic Website Intelligence Pipeline.

AES-005A Part 5.

Covers every handoff requirement: engine identity, pipeline construction,
successful execution, empty findings, findings/recommendations/work orders
preserved, scores/grade/launch readiness/report ID preserved, immutability,
determinism, repeatability, no duplicated work orders, recommendation ↔
work-order integrity, integration with the real ``AuditEngine``,
``RecommendationEngine``, and ``WorkOrderPlanner``, byte-identical repeated
runs, and full end-to-end execution.
"""

import pytest

from engines.website_intelligence.audit_engine import AuditEngine
from engines.website_intelligence.constants import (
    ENGINE_NAME,
    ENGINE_VERSION,
    SCORE_CATEGORIES,
    WORK_ORDER_STATUS_PENDING,
)
from engines.website_intelligence.models import (
    WebsiteAuditFinding,
    WebsiteAuditInput,
    WebsiteAuditRecommendation,
    WebsiteAuditReport,
    WebsiteWorkOrder,
)
from engines.website_intelligence.pipeline import WebsiteIntelligencePipeline
from engines.website_intelligence.recommendation_engine import (
    RecommendationEngine,
)
from engines.website_intelligence.work_order_planner import WorkOrderPlanner


# ---------------------------------------------------------------------------
# Input builders
# ---------------------------------------------------------------------------


def make_directory_input():
    """A realistic manufactured-directory payload with several audit issues.

    Mirrors the Part 4 integration fixture: two pages, two businesses, one
    with a missing description, one page with thin content and no meta
    description, no monetization sections. Produces a non-empty findings /
    recommendations / work orders set — the standard end-to-end test case.
    """
    long_content = "PetTripFinder helps travelers find pet friendly stops. " * 8
    return WebsiteAuditInput(
        project_assembly={
            "slug": "pettripfinder",
            "businesses": (
                {
                    "name": "Bark Park Cafe",
                    "category": "cafes",
                    "location": "Columbus",
                    "description": "A dog friendly cafe.",
                },
                {
                    "name": "Paws Motel",
                    "category": "lodging",
                    "location": "Dublin",
                    "description": "",
                },
            ),
            "categories": ("cafes", "lodging"),
            "locations": ("Columbus", "Dublin"),
        },
        static_site_package={
            "pages": (
                {
                    "path": "/",
                    "title": "PetTripFinder",
                    "meta_description": "Find pet friendly stops.",
                    "h1": "PetTripFinder",
                    "content": long_content,
                    "links": ("/cafes",),
                    "breadcrumbs": ("home",),
                },
                {
                    "path": "/cafes",
                    "title": "Cafes",
                    "meta_description": "",
                    "h1": "Cafes",
                    "content": "Short.",
                    "links": ("/",),
                    "breadcrumbs": ("home", "cafes"),
                },
            ),
            "sitemap_paths": ("/", "/cafes"),
            "robots": "User-agent: *",
            "cta_blocks": ("Join the newsletter",),
            "monetization_sections": (),
            "contact_info": "hello@pettripfinder.com",
        },
        preview_build={"pages": ()},
    )


def make_clean_input():
    """A clean manufactured-directory payload with zero audit issues.

    Two internally-linked pages, both fully populated. No businesses.
    Robots, CTA, monetization, and contact info all present. Produces a
    report with zero findings, zero recommendations, and zero work orders.
    """
    long_content = (
        "Our team welcomes every visitor with useful details about the "
        "services we offer. "
    ) * 4
    return WebsiteAuditInput(
        project_assembly={
            "slug": "cleansite",
            "businesses": (),
            "categories": (),
            "locations": (),
        },
        static_site_package={
            "pages": (
                {
                    "path": "/",
                    "title": "Home",
                    "meta_description": "Welcome to the home page.",
                    "h1": "Welcome",
                    "content": long_content,
                    "links": ("/about",),
                    "breadcrumbs": (),
                },
                {
                    "path": "/about",
                    "title": "About",
                    "meta_description": "Learn about our operation.",
                    "h1": "About Us",
                    "content": long_content.replace("Our team", "This page"),
                    "links": ("/",),
                    "breadcrumbs": ("home", "about"),
                },
            ),
            "sitemap_paths": ("/", "/about"),
            "robots": "User-agent: *",
            "cta_blocks": ("Sign up for our newsletter",),
            "monetization_sections": ("Featured partners",),
            "contact_info": "hello@example.com",
        },
        preview_build={"pages": ()},
    )


# ---------------------------------------------------------------------------
# Test doubles for dependency injection tests
# ---------------------------------------------------------------------------


class _RecordingAuditEngine:
    """Wraps a real AuditEngine and records every call for verification."""

    def __init__(self) -> None:
        self._delegate = AuditEngine()
        self.calls = []

    def audit(self, audit_input):
        self.calls.append(audit_input)
        return self._delegate.audit(audit_input)


class _RecordingWorkOrderPlanner:
    """Wraps a real WorkOrderPlanner and records every call for verification."""

    def __init__(self) -> None:
        self._delegate = WorkOrderPlanner()
        self.calls = []

    def plan_report(self, report):
        self.calls.append(report)
        return self._delegate.plan_report(report)


class _BadAuditEngine:
    """Returns a non-report value — used to verify contract enforcement."""

    def audit(self, audit_input):
        return {"not": "a report"}


class _BadWorkOrderPlanner:
    """Returns a non-report value — used to verify contract enforcement."""

    def plan_report(self, report):
        return "not a report"


# ===========================================================================
# Engine identity
# ===========================================================================


class TestEngineIdentity:
    def test_engine_name_matches_constants(self):
        assert WebsiteIntelligencePipeline.engine_name == ENGINE_NAME

    def test_engine_version_matches_constants(self):
        assert WebsiteIntelligencePipeline.engine_version == ENGINE_VERSION

    def test_engine_name_on_returned_report_matches(self):
        report = WebsiteIntelligencePipeline().run(make_directory_input())
        assert report.engine_name == ENGINE_NAME

    def test_engine_version_on_returned_report_matches(self):
        report = WebsiteIntelligencePipeline().run(make_directory_input())
        assert report.engine_version == ENGINE_VERSION


# ===========================================================================
# Pipeline construction
# ===========================================================================


class TestPipelineConstruction:
    def test_default_construction_succeeds(self):
        pipeline = WebsiteIntelligencePipeline()
        assert isinstance(pipeline, WebsiteIntelligencePipeline)

    def test_default_construction_uses_audit_engine(self):
        pipeline = WebsiteIntelligencePipeline()
        assert isinstance(pipeline._audit_engine, AuditEngine)

    def test_default_construction_uses_work_order_planner(self):
        pipeline = WebsiteIntelligencePipeline()
        assert isinstance(pipeline._work_order_planner, WorkOrderPlanner)

    def test_construction_accepts_injected_audit_engine(self):
        injected = AuditEngine()
        pipeline = WebsiteIntelligencePipeline(audit_engine=injected)
        assert pipeline._audit_engine is injected

    def test_construction_accepts_injected_work_order_planner(self):
        injected = WorkOrderPlanner()
        pipeline = WebsiteIntelligencePipeline(work_order_planner=injected)
        assert pipeline._work_order_planner is injected

    def test_run_is_the_only_public_method(self):
        public = [
            name
            for name in dir(WebsiteIntelligencePipeline)
            if not name.startswith("_")
        ]
        # engine_name and engine_version are identity attributes, not methods.
        callable_public = [
            name
            for name in public
            if callable(getattr(WebsiteIntelligencePipeline, name))
        ]
        assert callable_public == ["run"]


# ===========================================================================
# Successful execution
# ===========================================================================


class TestSuccessfulExecution:
    def test_run_returns_website_audit_report(self):
        report = WebsiteIntelligencePipeline().run(make_directory_input())
        assert isinstance(report, WebsiteAuditReport)

    def test_run_returns_a_single_report_not_a_tuple(self):
        result = WebsiteIntelligencePipeline().run(make_directory_input())
        assert not isinstance(result, tuple)

    def test_run_does_not_return_intermediate_objects(self):
        # The pipeline exposes only the final WebsiteAuditReport; nothing
        # from ScoringResult, findings tuples, or work-order tuples is
        # returned separately.
        result = WebsiteIntelligencePipeline().run(make_directory_input())
        assert isinstance(result, WebsiteAuditReport)


# ===========================================================================
# Input rejection
# ===========================================================================


class TestInputValidation:
    def test_run_rejects_none(self):
        with pytest.raises(ValueError):
            WebsiteIntelligencePipeline().run(None)

    def test_run_rejects_dict(self):
        with pytest.raises(ValueError):
            WebsiteIntelligencePipeline().run({"project_assembly": {}})

    def test_run_rejects_string(self):
        with pytest.raises(ValueError):
            WebsiteIntelligencePipeline().run("not an input")

    def test_run_rejects_report_object(self):
        # Passing a WebsiteAuditReport is a caller bug — the pipeline must
        # not silently repair it into a run.
        report = WebsiteIntelligencePipeline().run(make_directory_input())
        with pytest.raises(ValueError):
            WebsiteIntelligencePipeline().run(report)

    def test_run_rejects_bad_audit_engine_output(self):
        pipeline = WebsiteIntelligencePipeline(audit_engine=_BadAuditEngine())
        with pytest.raises(ValueError):
            pipeline.run(make_directory_input())

    def test_run_rejects_bad_work_order_planner_output(self):
        pipeline = WebsiteIntelligencePipeline(
            work_order_planner=_BadWorkOrderPlanner()
        )
        with pytest.raises(ValueError):
            pipeline.run(make_directory_input())


# ===========================================================================
# Empty findings
# ===========================================================================


class TestEmptyFindings:
    def test_clean_input_produces_zero_findings(self):
        report = WebsiteIntelligencePipeline().run(make_clean_input())
        assert report.findings == ()

    def test_clean_input_produces_zero_recommendations(self):
        report = WebsiteIntelligencePipeline().run(make_clean_input())
        assert report.recommendations == ()

    def test_clean_input_produces_zero_work_orders(self):
        report = WebsiteIntelligencePipeline().run(make_clean_input())
        assert report.work_orders == ()

    def test_clean_input_yields_perfect_scores(self):
        report = WebsiteIntelligencePipeline().run(make_clean_input())
        assert report.overall_score == 100.0
        for category in SCORE_CATEGORIES:
            assert getattr(report, f"{category}_score") == 100.0

    def test_clean_input_yields_top_grade_and_ready_launch(self):
        report = WebsiteIntelligencePipeline().run(make_clean_input())
        assert report.grade == "A"
        assert report.launch_readiness == "READY"


# ===========================================================================
# Findings preserved
# ===========================================================================


class TestFindingsPreserved:
    def test_findings_match_direct_audit_engine(self):
        audit_input = make_directory_input()
        pipeline_report = WebsiteIntelligencePipeline().run(audit_input)
        direct_report = AuditEngine().audit(audit_input)
        assert pipeline_report.findings == direct_report.findings

    def test_findings_present_after_pipeline_when_expected(self):
        report = WebsiteIntelligencePipeline().run(make_directory_input())
        assert len(report.findings) > 0
        assert all(isinstance(f, WebsiteAuditFinding) for f in report.findings)

    def test_findings_are_stored_as_tuple(self):
        report = WebsiteIntelligencePipeline().run(make_directory_input())
        assert isinstance(report.findings, tuple)


# ===========================================================================
# Recommendations preserved
# ===========================================================================


class TestRecommendationsPreserved:
    def test_recommendations_match_direct_audit_engine(self):
        audit_input = make_directory_input()
        pipeline_report = WebsiteIntelligencePipeline().run(audit_input)
        direct_report = AuditEngine().audit(audit_input)
        assert pipeline_report.recommendations == direct_report.recommendations

    def test_recommendations_present_after_pipeline_when_expected(self):
        report = WebsiteIntelligencePipeline().run(make_directory_input())
        assert len(report.recommendations) > 0
        assert all(
            isinstance(r, WebsiteAuditRecommendation)
            for r in report.recommendations
        )

    def test_recommendation_finding_ids_reference_report_findings(self):
        report = WebsiteIntelligencePipeline().run(make_directory_input())
        finding_ids = {finding.finding_id for finding in report.findings}
        for recommendation in report.recommendations:
            for finding_id in recommendation.finding_ids:
                assert finding_id in finding_ids

    def test_recommendations_match_direct_recommendation_engine(self):
        # Confirms the pipeline's recommendations are exactly what the
        # RecommendationEngine would produce from the pipeline's own findings.
        report = WebsiteIntelligencePipeline().run(make_directory_input())
        directly = RecommendationEngine().recommend(report.findings)
        assert report.recommendations == directly


# ===========================================================================
# Work orders preserved
# ===========================================================================


class TestWorkOrdersPreserved:
    def test_work_orders_populated_when_recommendations_exist(self):
        report = WebsiteIntelligencePipeline().run(make_directory_input())
        assert len(report.work_orders) == len(report.recommendations)
        assert all(isinstance(wo, WebsiteWorkOrder) for wo in report.work_orders)

    def test_work_orders_match_direct_planner(self):
        audit_input = make_directory_input()
        pipeline_report = WebsiteIntelligencePipeline().run(audit_input)
        direct_report = WorkOrderPlanner().plan_report(
            AuditEngine().audit(audit_input)
        )
        assert pipeline_report.work_orders == direct_report.work_orders

    def test_all_work_orders_status_pending(self):
        report = WebsiteIntelligencePipeline().run(make_directory_input())
        assert all(
            wo.status == WORK_ORDER_STATUS_PENDING for wo in report.work_orders
        )

    def test_work_order_ids_are_unique(self):
        report = WebsiteIntelligencePipeline().run(make_directory_input())
        ids = [wo.work_order_id for wo in report.work_orders]
        assert len(ids) == len(set(ids))

    def test_no_duplicated_work_orders(self):
        report = WebsiteIntelligencePipeline().run(make_directory_input())
        assert len(report.work_orders) == len(set(report.work_orders))


# ===========================================================================
# Scores preserved
# ===========================================================================


class TestScoresPreserved:
    def test_all_category_scores_preserved(self):
        audit_input = make_directory_input()
        pipeline_report = WebsiteIntelligencePipeline().run(audit_input)
        direct_report = AuditEngine().audit(audit_input)
        for category in SCORE_CATEGORIES:
            field = f"{category}_score"
            assert getattr(pipeline_report, field) == getattr(direct_report, field)

    def test_overall_score_preserved(self):
        audit_input = make_directory_input()
        pipeline_report = WebsiteIntelligencePipeline().run(audit_input)
        direct_report = AuditEngine().audit(audit_input)
        assert pipeline_report.overall_score == direct_report.overall_score

    def test_overall_score_within_bounds(self):
        report = WebsiteIntelligencePipeline().run(make_directory_input())
        assert 0.0 <= report.overall_score <= 100.0


# ===========================================================================
# Grade preserved
# ===========================================================================


class TestGradePreserved:
    def test_grade_matches_direct_audit_engine(self):
        audit_input = make_directory_input()
        pipeline_report = WebsiteIntelligencePipeline().run(audit_input)
        direct_report = AuditEngine().audit(audit_input)
        assert pipeline_report.grade == direct_report.grade

    def test_grade_is_one_of_known_grades(self):
        report = WebsiteIntelligencePipeline().run(make_directory_input())
        assert report.grade in ("A", "B", "C", "D", "F")


# ===========================================================================
# Launch readiness preserved
# ===========================================================================


class TestLaunchReadinessPreserved:
    def test_launch_readiness_matches_direct_audit_engine(self):
        audit_input = make_directory_input()
        pipeline_report = WebsiteIntelligencePipeline().run(audit_input)
        direct_report = AuditEngine().audit(audit_input)
        assert pipeline_report.launch_readiness == direct_report.launch_readiness

    def test_launch_readiness_is_a_known_tier(self):
        report = WebsiteIntelligencePipeline().run(make_directory_input())
        assert report.launch_readiness in (
            "READY", "REVIEW", "NEEDS_WORK", "NOT_READY",
        )


# ===========================================================================
# Report ID preserved
# ===========================================================================


class TestReportIdPreserved:
    def test_report_id_matches_audit_engine_report_id(self):
        # The WorkOrderPlanner preserves report_id verbatim, so the
        # pipeline's report_id must equal the AuditEngine's.
        audit_input = make_directory_input()
        pipeline_report = WebsiteIntelligencePipeline().run(audit_input)
        direct_report = AuditEngine().audit(audit_input)
        assert pipeline_report.report_id == direct_report.report_id

    def test_report_id_stable_across_runs(self):
        audit_input = make_directory_input()
        first = WebsiteIntelligencePipeline().run(audit_input).report_id
        second = WebsiteIntelligencePipeline().run(audit_input).report_id
        assert first == second

    def test_report_id_is_non_empty(self):
        report = WebsiteIntelligencePipeline().run(make_directory_input())
        assert report.report_id
        assert isinstance(report.report_id, str)


# ===========================================================================
# Immutability
# ===========================================================================


class TestImmutability:
    def test_returned_report_is_frozen(self):
        report = WebsiteIntelligencePipeline().run(make_directory_input())
        with pytest.raises(Exception):
            report.overall_score = 0.0

    def test_returned_report_work_orders_cannot_be_reassigned(self):
        report = WebsiteIntelligencePipeline().run(make_directory_input())
        with pytest.raises(Exception):
            report.work_orders = ()

    def test_returned_report_grade_cannot_be_reassigned(self):
        report = WebsiteIntelligencePipeline().run(make_directory_input())
        with pytest.raises(Exception):
            report.grade = "F"

    def test_findings_tuple_is_immutable(self):
        report = WebsiteIntelligencePipeline().run(make_directory_input())
        assert isinstance(report.findings, tuple)

    def test_recommendations_tuple_is_immutable(self):
        report = WebsiteIntelligencePipeline().run(make_directory_input())
        assert isinstance(report.recommendations, tuple)

    def test_work_orders_tuple_is_immutable(self):
        report = WebsiteIntelligencePipeline().run(make_directory_input())
        assert isinstance(report.work_orders, tuple)

    def test_pipeline_does_not_modify_input(self):
        audit_input = make_directory_input()
        original_assembly = audit_input.project_assembly
        original_package = audit_input.static_site_package
        original_preview = audit_input.preview_build
        WebsiteIntelligencePipeline().run(audit_input)
        # WebsiteAuditInput is itself frozen; verify identity of its parts.
        assert audit_input.project_assembly is original_assembly
        assert audit_input.static_site_package is original_package
        assert audit_input.preview_build is original_preview


# ===========================================================================
# Determinism + repeatability
# ===========================================================================


class TestDeterminism:
    def test_identical_input_identical_output(self):
        first = WebsiteIntelligencePipeline().run(make_directory_input())
        second = WebsiteIntelligencePipeline().run(make_directory_input())
        assert first == second

    def test_two_pipeline_instances_produce_equal_reports(self):
        audit_input = make_directory_input()
        first = WebsiteIntelligencePipeline().run(audit_input)
        second = WebsiteIntelligencePipeline().run(audit_input)
        assert first == second

    def test_repeated_runs_are_byte_identical(self):
        audit_input = make_directory_input()
        results = {
            repr(WebsiteIntelligencePipeline().run(audit_input))
            for _ in range(20)
        }
        assert len(results) == 1

    def test_pipeline_is_stateless_across_runs(self):
        pipeline = WebsiteIntelligencePipeline()
        audit_input = make_directory_input()
        first = pipeline.run(audit_input)
        _ = pipeline.run(make_clean_input())  # different input in between
        second = pipeline.run(audit_input)
        assert first == second


# ===========================================================================
# Recommendation ↔ Work Order Integrity
# ===========================================================================


class TestIntegrity:
    def test_every_work_order_fulfils_a_report_recommendation(self):
        report = WebsiteIntelligencePipeline().run(make_directory_input())
        recommendation_ids = {
            recommendation.recommendation_id
            for recommendation in report.recommendations
        }
        for work_order in report.work_orders:
            assert work_order.recommendation_id in recommendation_ids

    def test_work_order_priorities_mirror_recommendations(self):
        report = WebsiteIntelligencePipeline().run(make_directory_input())
        priority_by_recommendation = {
            recommendation.recommendation_id: recommendation.priority
            for recommendation in report.recommendations
        }
        for work_order in report.work_orders:
            assert (
                work_order.priority
                == priority_by_recommendation[work_order.recommendation_id]
            )

    def test_work_order_categories_mirror_recommendations(self):
        report = WebsiteIntelligencePipeline().run(make_directory_input())
        category_by_recommendation = {
            recommendation.recommendation_id: recommendation.category
            for recommendation in report.recommendations
        }
        for work_order in report.work_orders:
            assert (
                work_order.category
                == category_by_recommendation[work_order.recommendation_id]
            )

    def test_one_work_order_per_recommendation(self):
        report = WebsiteIntelligencePipeline().run(make_directory_input())
        assert len(report.work_orders) == len(report.recommendations)


# ===========================================================================
# Engine integration
# ===========================================================================


class TestAuditEngineIntegration:
    def test_pipeline_calls_injected_audit_engine_exactly_once(self):
        recorder = _RecordingAuditEngine()
        pipeline = WebsiteIntelligencePipeline(audit_engine=recorder)
        pipeline.run(make_directory_input())
        assert len(recorder.calls) == 1

    def test_pipeline_passes_input_through_to_audit_engine(self):
        recorder = _RecordingAuditEngine()
        pipeline = WebsiteIntelligencePipeline(audit_engine=recorder)
        audit_input = make_directory_input()
        pipeline.run(audit_input)
        assert recorder.calls[0] is audit_input

    def test_audit_engine_findings_survive_pipeline(self):
        audit_input = make_directory_input()
        direct_findings = AuditEngine().audit(audit_input).findings
        pipeline_findings = (
            WebsiteIntelligencePipeline().run(audit_input).findings
        )
        assert pipeline_findings == direct_findings


class TestRecommendationEngineIntegration:
    def test_pipeline_output_matches_recommendation_engine(self):
        # The pipeline delegates recommendation generation to the
        # RecommendationEngine (transitively through the AuditEngine). The
        # output's recommendations must equal what the RecommendationEngine
        # would produce from the report's own findings.
        report = WebsiteIntelligencePipeline().run(make_directory_input())
        assert report.recommendations == RecommendationEngine().recommend(
            report.findings
        )


class TestWorkOrderPlannerIntegration:
    def test_pipeline_calls_injected_planner_exactly_once(self):
        recorder = _RecordingWorkOrderPlanner()
        pipeline = WebsiteIntelligencePipeline(work_order_planner=recorder)
        pipeline.run(make_directory_input())
        assert len(recorder.calls) == 1

    def test_pipeline_hands_audited_report_to_planner(self):
        recorder = _RecordingWorkOrderPlanner()
        pipeline = WebsiteIntelligencePipeline(work_order_planner=recorder)
        pipeline.run(make_directory_input())
        received = recorder.calls[0]
        # Planner receives the AuditEngine's output — no work orders yet.
        assert isinstance(received, WebsiteAuditReport)
        assert received.work_orders == ()

    def test_planner_output_appears_verbatim_in_pipeline_output(self):
        audit_input = make_directory_input()
        direct_planned = WorkOrderPlanner().plan_report(
            AuditEngine().audit(audit_input)
        )
        pipeline_result = WebsiteIntelligencePipeline().run(audit_input)
        assert pipeline_result.work_orders == direct_planned.work_orders


# ===========================================================================
# Full end-to-end execution
# ===========================================================================


class TestEndToEnd:
    def test_pipeline_matches_manual_composition_byte_for_byte(self):
        audit_input = make_directory_input()
        pipeline_result = WebsiteIntelligencePipeline().run(audit_input)
        manual_result = WorkOrderPlanner().plan_report(
            AuditEngine().audit(audit_input)
        )
        assert pipeline_result == manual_result
        assert repr(pipeline_result) == repr(manual_result)

    def test_end_to_end_report_is_complete(self):
        report = WebsiteIntelligencePipeline().run(make_directory_input())
        # Every top-level report field is populated.
        assert report.report_id
        assert report.engine_name
        assert report.engine_version
        assert report.grade
        assert report.launch_readiness
        for category in SCORE_CATEGORIES:
            assert isinstance(getattr(report, f"{category}_score"), float)
        assert isinstance(report.overall_score, float)
        assert isinstance(report.findings, tuple)
        assert isinstance(report.recommendations, tuple)
        assert isinstance(report.work_orders, tuple)

    def test_full_end_to_end_execution_on_both_input_shapes(self):
        # Full pipeline runs cleanly on both a directory input with issues
        # and a clean input, without either interfering with the other.
        pipeline = WebsiteIntelligencePipeline()
        dirty = pipeline.run(make_directory_input())
        clean = pipeline.run(make_clean_input())
        assert dirty.report_id != clean.report_id
        assert len(dirty.findings) > 0
        assert len(clean.findings) == 0
        assert len(dirty.work_orders) == len(dirty.recommendations)
        assert len(clean.work_orders) == 0
