"""Tests for the deterministic Website Intelligence work order planner.

AES-005A Part 4.

Covers: recommendation validation, work order validation, deterministic
IDs, instruction and acceptance criteria derivation, one-to-one planning,
duplicate collapsing, stable ordering, order-independence, report
attachment, the planner facade, full-pipeline integration with the audit
engine, and byte-for-byte determinism.
"""

import pytest

from engines.website_intelligence.constants import (
    CATEGORY_CONTENT,
    CATEGORY_DIRECTORY,
    CATEGORY_NAVIGATION,
    CATEGORY_SEO,
    ENGINE_NAME,
    ENGINE_VERSION,
    PRIORITIES,
    PRIORITY_HIGH,
    PRIORITY_LOW,
    PRIORITY_MEDIUM,
    SCORE_CATEGORIES,
    WORK_ORDER_STATUS_PENDING,
)
from engines.website_intelligence.audit_engine import AuditEngine
from engines.website_intelligence.models import (
    WebsiteAuditInput,
    WebsiteAuditRecommendation,
    WebsiteAuditReport,
    WebsiteWorkOrder,
)
from engines.website_intelligence.work_order_planner import (
    WorkOrderPlanner,
    acceptance_criteria_for,
    attach_work_orders,
    plan_work_orders,
    validate_recommendations,
    validate_work_orders,
    work_order_for,
    work_order_id_for,
    work_order_instructions_for,
)

# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


def make_recommendation(**overrides):
    data = {
        "recommendation_id": "rec-abc123",
        "category": CATEGORY_SEO,
        "priority": PRIORITY_MEDIUM,
        "title": "Address warning: Missing meta description",
        "description": (
            "Resolve 2 occurrence(s) of 'Missing meta description' in the "
            "'seo' category (severity: WARNING)."
        ),
        "finding_ids": ("find-222", "find-111"),
    }
    data.update(overrides)
    return WebsiteAuditRecommendation(**data)


def make_report(**overrides):
    recommendation = make_recommendation()
    data = {
        "report_id": "rpt-000111",
        "engine_name": ENGINE_NAME,
        "engine_version": ENGINE_VERSION,
        "seo_score": 84.0,
        "navigation_score": 90.0,
        "content_score": 80.0,
        "directory_score": 88.0,
        "commercial_score": 75.0,
        "monetization_score": 60.0,
        "ux_score": 92.0,
        "overall_score": 82.05,
        "grade": "B",
        "launch_readiness": "REVIEW",
        "findings": (),
        "recommendations": (recommendation,),
        "work_orders": (),
    }
    data.update(overrides)
    return WebsiteAuditReport(**data)


def make_audit_input():
    """A small but realistic manufactured-website payload."""
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


# ---------------------------------------------------------------------------
# Recommendation validation
# ---------------------------------------------------------------------------


class TestRecommendationValidation:
    def test_valid_recommendations_pass(self):
        validate_recommendations((make_recommendation(),))  # must not raise

    def test_empty_input_passes(self):
        validate_recommendations(())  # must not raise

    def test_non_recommendation_rejected(self):
        with pytest.raises(ValueError):
            validate_recommendations(({"recommendation_id": "rec-1"},))

    def test_unknown_priority_rejected(self):
        with pytest.raises(ValueError):
            validate_recommendations((make_recommendation(priority="URGENT"),))

    def test_unknown_category_rejected(self):
        with pytest.raises(ValueError):
            validate_recommendations((make_recommendation(category="performance"),))

    def test_exact_duplicates_allowed(self):
        validate_recommendations(
            (make_recommendation(), make_recommendation())
        )  # must not raise

    def test_conflicting_duplicate_ids_rejected(self):
        first = make_recommendation()
        second = make_recommendation(title="Different title")
        with pytest.raises(ValueError):
            validate_recommendations((first, second))


# ---------------------------------------------------------------------------
# Work order validation
# ---------------------------------------------------------------------------


class TestWorkOrderValidation:
    def test_valid_work_orders_pass(self):
        validate_work_orders((work_order_for(make_recommendation()),))

    def test_empty_input_passes(self):
        validate_work_orders(())  # must not raise

    def test_non_work_order_rejected(self):
        with pytest.raises(ValueError):
            validate_work_orders((make_recommendation(),))

    def test_unknown_priority_rejected(self):
        work_order = WebsiteWorkOrder(
            work_order_id="wo-1",
            recommendation_id="rec-1",
            category=CATEGORY_SEO,
            priority="URGENT",
            title="t",
        )
        with pytest.raises(ValueError):
            validate_work_orders((work_order,))

    def test_unknown_category_rejected(self):
        work_order = WebsiteWorkOrder(
            work_order_id="wo-1",
            recommendation_id="rec-1",
            category="performance",
            priority=PRIORITY_HIGH,
            title="t",
        )
        with pytest.raises(ValueError):
            validate_work_orders((work_order,))

    def test_exact_duplicates_allowed(self):
        work_order = work_order_for(make_recommendation())
        validate_work_orders((work_order, work_order))  # must not raise

    def test_conflicting_duplicate_ids_rejected(self):
        first = work_order_for(make_recommendation())
        second = WebsiteWorkOrder(
            work_order_id=first.work_order_id,
            recommendation_id=first.recommendation_id,
            category=first.category,
            priority=first.priority,
            title="Different title",
        )
        with pytest.raises(ValueError):
            validate_work_orders((first, second))


# ---------------------------------------------------------------------------
# Deterministic derivations
# ---------------------------------------------------------------------------


class TestWorkOrderId:
    def test_identical_input_identical_id(self):
        assert work_order_id_for("rec-abc123") == work_order_id_for("rec-abc123")

    def test_different_input_different_id(self):
        assert work_order_id_for("rec-a") != work_order_id_for("rec-b")

    def test_prefix_included(self):
        assert work_order_id_for("rec-abc123").startswith("wo-")

    def test_empty_recommendation_id_rejected(self):
        with pytest.raises(ValueError):
            work_order_id_for("")


class TestInstructions:
    def test_instructions_carry_recommendation_fields_verbatim(self):
        recommendation = make_recommendation()
        instructions = work_order_instructions_for(recommendation)
        assert recommendation.recommendation_id in instructions
        assert recommendation.category in instructions
        assert recommendation.priority in instructions
        assert recommendation.title in instructions
        assert recommendation.description in instructions

    def test_instructions_mandate_operator_approval(self):
        instructions = work_order_instructions_for(make_recommendation())
        assert "operator approval" in instructions

    def test_instructions_are_deterministic(self):
        first = work_order_instructions_for(make_recommendation())
        second = work_order_instructions_for(make_recommendation())
        assert first == second

    def test_non_recommendation_rejected(self):
        with pytest.raises(ValueError):
            work_order_instructions_for("not a recommendation")


class TestAcceptanceCriteria:
    def test_three_criteria_with_finding_ids(self):
        criteria = acceptance_criteria_for(make_recommendation())
        assert len(criteria) == 3
        assert isinstance(criteria, tuple)

    def test_two_criteria_without_finding_ids(self):
        criteria = acceptance_criteria_for(make_recommendation(finding_ids=()))
        assert len(criteria) == 2

    def test_first_criterion_names_title_and_category(self):
        recommendation = make_recommendation()
        criteria = acceptance_criteria_for(recommendation)
        assert recommendation.title in criteria[0]
        assert recommendation.category in criteria[0]

    def test_finding_criterion_lists_sorted_ids_and_count(self):
        criteria = acceptance_criteria_for(make_recommendation())
        assert "2 linked finding(s)" in criteria[1]
        assert criteria[1].index("find-111") < criteria[1].index("find-222")

    def test_finding_id_order_does_not_affect_criteria(self):
        forward = acceptance_criteria_for(
            make_recommendation(finding_ids=("find-111", "find-222"))
        )
        reverse = acceptance_criteria_for(
            make_recommendation(finding_ids=("find-222", "find-111"))
        )
        assert forward == reverse

    def test_last_criterion_forbids_regressions(self):
        criteria = acceptance_criteria_for(make_recommendation())
        assert "no new CRITICAL or WARNING findings" in criteria[-1]

    def test_non_recommendation_rejected(self):
        with pytest.raises(ValueError):
            acceptance_criteria_for(None)


class TestWorkOrderFor:
    def test_fields_carry_over_verbatim(self):
        recommendation = make_recommendation()
        work_order = work_order_for(recommendation)
        assert work_order.recommendation_id == recommendation.recommendation_id
        assert work_order.category == recommendation.category
        assert work_order.priority == recommendation.priority
        assert work_order.title == recommendation.title

    def test_work_order_id_derived_from_recommendation_id(self):
        recommendation = make_recommendation()
        work_order = work_order_for(recommendation)
        assert work_order.work_order_id == work_order_id_for(
            recommendation.recommendation_id
        )

    def test_status_is_always_pending(self):
        assert work_order_for(make_recommendation()).status == (
            WORK_ORDER_STATUS_PENDING
        )

    def test_work_order_is_immutable(self):
        work_order = work_order_for(make_recommendation())
        with pytest.raises(Exception):
            work_order.status = "APPROVED"

    def test_non_recommendation_rejected(self):
        with pytest.raises(ValueError):
            work_order_for(42)


# ---------------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------------


class TestPlanWorkOrders:
    def test_empty_input_gives_empty_tuple(self):
        assert plan_work_orders(()) == ()

    def test_one_work_order_per_recommendation(self):
        recommendations = (
            make_recommendation(),
            make_recommendation(
                recommendation_id="rec-def456",
                category=CATEGORY_CONTENT,
                priority=PRIORITY_HIGH,
                title="Fix critical issue: Empty page",
            ),
        )
        work_orders = plan_work_orders(recommendations)
        assert len(work_orders) == 2
        assert {wo.recommendation_id for wo in work_orders} == {
            "rec-abc123",
            "rec-def456",
        }

    def test_exact_duplicates_collapse_to_one_work_order(self):
        work_orders = plan_work_orders((make_recommendation(), make_recommendation()))
        assert len(work_orders) == 1

    def test_conflicting_duplicates_rejected(self):
        with pytest.raises(ValueError):
            plan_work_orders(
                (make_recommendation(), make_recommendation(title="Other"))
            )

    def test_ordered_by_priority_then_category(self):
        recommendations = (
            make_recommendation(
                recommendation_id="rec-low",
                category=CATEGORY_SEO,
                priority=PRIORITY_LOW,
                title="c",
            ),
            make_recommendation(
                recommendation_id="rec-high-nav",
                category=CATEGORY_NAVIGATION,
                priority=PRIORITY_HIGH,
                title="b",
            ),
            make_recommendation(
                recommendation_id="rec-high-seo",
                category=CATEGORY_SEO,
                priority=PRIORITY_HIGH,
                title="a",
            ),
            make_recommendation(
                recommendation_id="rec-med",
                category=CATEGORY_DIRECTORY,
                priority=PRIORITY_MEDIUM,
                title="d",
            ),
        )
        work_orders = plan_work_orders(recommendations)
        assert [wo.recommendation_id for wo in work_orders] == [
            "rec-high-seo",
            "rec-high-nav",
            "rec-med",
            "rec-low",
        ]

    def test_ties_break_on_title_then_id(self):
        recommendations = (
            make_recommendation(recommendation_id="rec-z", title="zebra"),
            make_recommendation(recommendation_id="rec-a", title="apple"),
        )
        work_orders = plan_work_orders(recommendations)
        assert [wo.title for wo in work_orders] == ["apple", "zebra"]

    def test_output_independent_of_input_order(self):
        recommendations = tuple(
            make_recommendation(
                recommendation_id=f"rec-{index}",
                priority=priority,
                title=f"title-{index}",
            )
            for index, priority in enumerate(PRIORITIES * 3)
        )
        forward = plan_work_orders(recommendations)
        reverse = plan_work_orders(tuple(reversed(recommendations)))
        assert forward == reverse

    def test_all_statuses_pending(self):
        recommendations = (
            make_recommendation(),
            make_recommendation(recommendation_id="rec-2", title="t2"),
        )
        assert all(
            wo.status == WORK_ORDER_STATUS_PENDING
            for wo in plan_work_orders(recommendations)
        )

    def test_identical_input_identical_output(self):
        recommendations = (make_recommendation(),)
        assert plan_work_orders(recommendations) == plan_work_orders(recommendations)

    def test_repeated_runs_are_byte_identical(self):
        recommendations = (
            make_recommendation(),
            make_recommendation(
                recommendation_id="rec-2",
                category=CATEGORY_DIRECTORY,
                priority=PRIORITY_HIGH,
                title="t2",
            ),
        )
        results = {repr(plan_work_orders(recommendations)) for _ in range(50)}
        assert len(results) == 1

    def test_returns_tuple(self):
        assert isinstance(plan_work_orders((make_recommendation(),)), tuple)


# ---------------------------------------------------------------------------
# Report attachment
# ---------------------------------------------------------------------------


class TestAttachWorkOrders:
    def test_attaches_work_orders_to_new_report(self):
        report = make_report()
        work_orders = plan_work_orders(report.recommendations)
        attached = attach_work_orders(report, work_orders)
        assert attached.work_orders == work_orders
        assert isinstance(attached.work_orders, tuple)

    def test_input_report_is_never_modified(self):
        report = make_report()
        work_orders = plan_work_orders(report.recommendations)
        attached = attach_work_orders(report, work_orders)
        assert report.work_orders == ()
        assert attached is not report

    def test_every_other_field_carries_over_verbatim(self):
        report = make_report()
        attached = attach_work_orders(
            report, plan_work_orders(report.recommendations)
        )
        assert attached.report_id == report.report_id
        assert attached.engine_name == report.engine_name
        assert attached.engine_version == report.engine_version
        assert attached.seo_score == report.seo_score
        assert attached.navigation_score == report.navigation_score
        assert attached.content_score == report.content_score
        assert attached.directory_score == report.directory_score
        assert attached.commercial_score == report.commercial_score
        assert attached.monetization_score == report.monetization_score
        assert attached.ux_score == report.ux_score
        assert attached.overall_score == report.overall_score
        assert attached.grade == report.grade
        assert attached.launch_readiness == report.launch_readiness
        assert attached.findings == report.findings
        assert attached.recommendations == report.recommendations

    def test_attaching_empty_work_orders_is_allowed(self):
        report = make_report(recommendations=())
        attached = attach_work_orders(report, ())
        assert attached.work_orders == ()

    def test_unknown_recommendation_rejected(self):
        report = make_report()
        stray = work_order_for(
            make_recommendation(recommendation_id="rec-unknown", title="stray")
        )
        with pytest.raises(ValueError):
            attach_work_orders(report, (stray,))

    def test_report_with_existing_work_orders_rejected(self):
        work_orders = plan_work_orders((make_recommendation(),))
        report = make_report(work_orders=work_orders)
        with pytest.raises(ValueError):
            attach_work_orders(report, work_orders)

    def test_non_report_rejected(self):
        with pytest.raises(ValueError):
            attach_work_orders("not a report", ())

    def test_invalid_work_order_rejected(self):
        report = make_report()
        with pytest.raises(ValueError):
            attach_work_orders(report, ("not a work order",))

    def test_attached_report_is_immutable(self):
        report = make_report()
        attached = attach_work_orders(
            report, plan_work_orders(report.recommendations)
        )
        with pytest.raises(Exception):
            attached.work_orders = ()


# ---------------------------------------------------------------------------
# Planner facade
# ---------------------------------------------------------------------------


class TestWorkOrderPlanner:
    def test_engine_identity(self):
        planner = WorkOrderPlanner()
        assert planner.engine_name == ENGINE_NAME
        assert planner.engine_version == ENGINE_VERSION

    def test_plan_matches_pure_function(self):
        recommendations = (make_recommendation(),)
        assert WorkOrderPlanner().plan(recommendations) == plan_work_orders(
            recommendations
        )

    def test_plan_report_plans_one_work_order_per_recommendation(self):
        report = make_report()
        planned = WorkOrderPlanner().plan_report(report)
        assert len(planned.work_orders) == len(report.recommendations)
        assert planned.work_orders[0].recommendation_id == (
            report.recommendations[0].recommendation_id
        )

    def test_plan_report_preserves_report_identity(self):
        report = make_report()
        planned = WorkOrderPlanner().plan_report(report)
        assert planned.report_id == report.report_id

    def test_plan_report_leaves_input_untouched(self):
        report = make_report()
        WorkOrderPlanner().plan_report(report)
        assert report.work_orders == ()

    def test_plan_report_with_no_recommendations(self):
        report = make_report(recommendations=())
        planned = WorkOrderPlanner().plan_report(report)
        assert planned.work_orders == ()

    def test_plan_report_rejects_non_report(self):
        with pytest.raises(ValueError):
            WorkOrderPlanner().plan_report({"report_id": "rpt-1"})

    def test_plan_report_is_deterministic(self):
        report = make_report()
        first = WorkOrderPlanner().plan_report(report)
        second = WorkOrderPlanner().plan_report(report)
        assert first == second


# ---------------------------------------------------------------------------
# Full pipeline integration (Audit Engine -> Work Order Planner)
# ---------------------------------------------------------------------------


class TestPipelineIntegration:
    def test_planner_consumes_real_audit_report(self):
        report = AuditEngine().audit(make_audit_input())
        assert report.recommendations  # the fixture site has issues
        assert report.work_orders == ()
        planned = WorkOrderPlanner().plan_report(report)
        assert len(planned.work_orders) == len(report.recommendations)

    def test_every_work_order_fulfils_a_report_recommendation(self):
        report = AuditEngine().audit(make_audit_input())
        planned = WorkOrderPlanner().plan_report(report)
        recommendation_ids = {
            recommendation.recommendation_id
            for recommendation in report.recommendations
        }
        assert all(
            wo.recommendation_id in recommendation_ids
            for wo in planned.work_orders
        )

    def test_work_orders_mirror_recommendation_priorities(self):
        report = AuditEngine().audit(make_audit_input())
        planned = WorkOrderPlanner().plan_report(report)
        priority_by_recommendation = {
            recommendation.recommendation_id: recommendation.priority
            for recommendation in report.recommendations
        }
        assert all(
            wo.priority == priority_by_recommendation[wo.recommendation_id]
            for wo in planned.work_orders
        )

    def test_pipeline_scores_and_readiness_unchanged_by_planning(self):
        report = AuditEngine().audit(make_audit_input())
        planned = WorkOrderPlanner().plan_report(report)
        assert planned.overall_score == report.overall_score
        assert planned.grade == report.grade
        assert planned.launch_readiness == report.launch_readiness

    def test_full_pipeline_is_byte_identical_across_runs(self):
        results = {
            repr(WorkOrderPlanner().plan_report(AuditEngine().audit(make_audit_input())))
            for _ in range(10)
        }
        assert len(results) == 1

    def test_all_pipeline_work_orders_are_pending(self):
        planned = WorkOrderPlanner().plan_report(
            AuditEngine().audit(make_audit_input())
        )
        assert all(
            wo.status == WORK_ORDER_STATUS_PENDING for wo in planned.work_orders
        )
