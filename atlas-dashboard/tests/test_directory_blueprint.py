"""Tests for the Directory Intelligence & Blueprint Engine (Atlas Phase 3).

Run from the repo root:
    python -m pytest tests\\test_directory_blueprint.py -v
"""

from __future__ import annotations

import os
import sqlite3
import sys

import pytest

# Ensure repo root is importable when pytest is invoked from anywhere.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from engines.directory_blueprint.blueprint_generator import (  # noqa: E402
    BLUEPRINT_ENGINE_VERSION,
    BlueprintGenerator,
    compute_input_hash,
    generate_blueprint,
    is_blueprint_eligible,
)
from engines.directory_blueprint.blueprint_models import (  # noqa: E402
    BlueprintRequest,
    CommitteeInput,
    CommitteeRecommendation,
    CompetitionLevel,
    DataVerificationTag,
    DirectoryBlueprint,
    DirectoryType,
    ExpansionClass,
    ExpansionClassificationInput,
    GeographicScope,
    MarketCapacityInput,
    MonetizationModel,
    OpportunityInput,
    PortfolioContextInput,
)
from engines.directory_blueprint.category_planner import (  # noqa: E402
    infer_directory_type,
    plan_directory_architecture,
    slugify,
)
from engines.directory_blueprint.monetization_planner import plan_monetization  # noqa: E402
from engines.directory_blueprint.pydantic_compat import (  # noqa: E402
    model_from_json,
    model_to_dict,
    model_to_json,
)
from engines.directory_blueprint.risk_analyzer import analyze_risks, score_to_level  # noqa: E402
from engines.directory_blueprint.roadmap_planner import plan_roadmap  # noqa: E402
from repositories import directory_blueprint_repository as repo  # noqa: E402
from services import directory_blueprint_service as service  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def make_request(
    recommendation: CommitteeRecommendation = CommitteeRecommendation.BUILD,
    scope: GeographicScope = GeographicScope.STATE,
    competition: CompetitionLevel = CompetitionLevel.MEDIUM,
    liquidity: float = 55.0,
    data_tag: DataVerificationTag = DataVerificationTag.ESTIMATED,
    classification: ExpansionClass = ExpansionClass.NEW_MARKET,
    name: str = "Ohio Dog Groomer Finder",
    niche: str = "dog grooming services",
) -> BlueprintRequest:
    return BlueprintRequest(
        opportunity=OpportunityInput(
            name=name,
            niche=niche,
            description="Directory of dog groomers",
            score=72.0,
            confidence=0.45,
            geographic_scope=scope,
            primary_market="Ohio",
            target_customer="Dog owners searching for local groomers",
            competition_level=competition,
            monetization_signals=["featured listings", "leads"],
        ),
        market_capacity=MarketCapacityInput(
            total_addressable_listings=1200,
            liquidity_score=liquidity,
            saturation_level=competition,
            data_tag=data_tag,
        ),
        portfolio_context=PortfolioContextInput(existing_assets=[], synergy_score=40.0),
        expansion=ExpansionClassificationInput(classification=classification),
        committee=CommitteeInput(
            recommendation=recommendation, confidence=0.45, rationale="test"
        ),
    )


@pytest.fixture()
def conn():
    connection = sqlite3.connect(":memory:")
    yield connection
    connection.close()


# ---------------------------------------------------------------------------
# Eligibility gate
# ---------------------------------------------------------------------------


class TestEligibilityGate:
    def test_build_is_eligible(self):
        assert is_blueprint_eligible(make_request(CommitteeRecommendation.BUILD))

    def test_test_is_eligible(self):
        assert is_blueprint_eligible(make_request(CommitteeRecommendation.TEST))

    def test_watch_is_not_eligible(self):
        assert not is_blueprint_eligible(make_request(CommitteeRecommendation.WATCH))

    def test_pass_is_not_eligible(self):
        assert not is_blueprint_eligible(make_request(CommitteeRecommendation.PASS))

    def test_engine_raises_for_ineligible(self):
        with pytest.raises(ValueError):
            generate_blueprint(make_request(CommitteeRecommendation.PASS))

    def test_service_returns_not_eligible_without_raising(self, conn):
        result = service.generate_and_store_blueprint(
            conn, make_request(CommitteeRecommendation.WATCH)
        )
        assert result.status == service.RESULT_NOT_ELIGIBLE
        assert result.blueprint is None
        assert "WATCH" in result.reason


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_identical_inputs_identical_hash(self):
        assert compute_input_hash(make_request()) == compute_input_hash(make_request())

    def test_different_inputs_different_hash(self):
        a = compute_input_hash(make_request())
        b = compute_input_hash(make_request(liquidity=10.0))
        assert a != b

    def test_identical_inputs_identical_blueprint_json(self):
        json_a = model_to_json(generate_blueprint(make_request()))
        json_b = model_to_json(generate_blueprint(make_request()))
        assert json_a == json_b

    def test_slugify_is_deterministic_and_clean(self):
        assert slugify("Ohio Dog Groomer Finder!") == "ohio-dog-groomer-finder"
        assert slugify("  --Weird__ Input  ") == "weird-input"


# ---------------------------------------------------------------------------
# Blueprint completeness (all 12 sections)
# ---------------------------------------------------------------------------


class TestBlueprintCompleteness:
    def test_all_sections_present_and_populated(self):
        bp = generate_blueprint(make_request())
        assert bp.engine_version == BLUEPRINT_ENGINE_VERSION
        assert len(bp.input_hash) == 64  # sha256 hex
        assert bp.project_profile.project_slug == "ohio-dog-groomer-finder"
        assert bp.project_profile.suggested_domains
        assert bp.directory_architecture.category_tree
        assert bp.directory_architecture.navigation_tree
        assert bp.directory_architecture.url_hierarchy
        assert bp.directory_architecture.canonical_strategy
        assert len(bp.database_blueprint.tables) >= 14
        assert bp.database_blueprint.repository_interfaces
        assert len(bp.business_profile_schema.fields) >= 20
        assert bp.search_experience.filters
        assert bp.search_experience.sort_options
        assert len(bp.monetization_plan.ranked_options) == 13
        assert bp.seo_blueprint.keyword_clusters
        assert bp.seo_blueprint.programmatic_seo_opportunities
        assert bp.content_strategy.items
        assert len(bp.ai_content_tasks.tasks) == 10
        assert len(bp.implementation_roadmap.phases) == 8
        assert len(bp.risk_analysis.assessments) == 7
        assert 1 <= bp.project_scorecard.overall_build_readiness <= 10

    def test_roadmap_phase_order_and_names(self):
        bp = generate_blueprint(make_request())
        names = [p.name for p in bp.implementation_roadmap.phases]
        assert names == [
            "Foundation", "Data", "Search", "Content",
            "SEO", "Monetization", "Launch", "Growth",
        ]
        assert [p.phase_number for p in bp.implementation_roadmap.phases] == list(range(1, 9))

    def test_database_blueprint_covers_required_tables(self):
        bp = generate_blueprint(make_request())
        table_names = {t.name for t in bp.database_blueprint.tables}
        for required in (
            "businesses", "categories", "locations", "reviews", "images",
            "owners", "subscriptions", "premium_listings", "claims",
            "events", "coupons", "jobs", "articles", "faqs",
        ):
            assert required in table_names

    def test_generation_notes_flag_unverified_data(self):
        bp = generate_blueprint(make_request(data_tag=DataVerificationTag.ESTIMATED))
        assert any("ESTIMATED" in note for note in bp.generation_notes)

    def test_test_recommendation_adds_mvp_note(self):
        bp = generate_blueprint(make_request(CommitteeRecommendation.TEST))
        assert any("TEST recommendation" in note for note in bp.generation_notes)


# ---------------------------------------------------------------------------
# Category planner
# ---------------------------------------------------------------------------


class TestCategoryPlanner:
    def test_directory_type_inference_travel(self):
        req = make_request(name="PetTripFinder", niche="pet friendly travel")
        assert infer_directory_type(req.opportunity) == DirectoryType.TRAVEL

    def test_directory_type_inference_education(self):
        req = make_request(name="Trade Schools", niche="skilled trades training")
        assert infer_directory_type(req.opportunity) == DirectoryType.EDUCATION

    def test_directory_type_default(self):
        opportunity = OpportunityInput(name="Widget Hub", niche="widgets", description="")
        assert infer_directory_type(opportunity) == DirectoryType.NICHE_INTEREST

    def test_location_levels_track_scope(self):
        national = plan_directory_architecture(
            make_request(scope=GeographicScope.NATIONAL).opportunity
        )
        city = plan_directory_architecture(
            make_request(scope=GeographicScope.CITY).opportunity
        )
        assert national.location_hierarchy.levels[0] == "Country"
        assert city.location_hierarchy.levels == ["City", "Neighborhood"]

    def test_navigation_includes_categories(self):
        arch = plan_directory_architecture(make_request().opportunity)
        browse = next(n for n in arch.navigation_tree if n.label == "Browse")
        assert len(browse.children) == len(arch.category_tree)


# ---------------------------------------------------------------------------
# Monetization planner
# ---------------------------------------------------------------------------


class TestMonetizationPlanner:
    def test_all_thirteen_models_ranked_uniquely(self):
        req = make_request()
        plan = plan_monetization(
            req.opportunity, req.market_capacity, DirectoryType.LOCAL_SERVICES
        )
        assert sorted(o.rank for o in plan.ranked_options) == list(range(1, 14))
        assert len({o.model for o in plan.ranked_options}) == 13

    def test_primary_model_is_rank_one(self):
        req = make_request()
        plan = plan_monetization(
            req.opportunity, req.market_capacity, DirectoryType.LOCAL_SERVICES
        )
        assert plan.primary_model == plan.ranked_options[0].model

    def test_low_liquidity_penalizes_advertising(self):
        req_high = make_request(liquidity=80.0)
        req_low = make_request(liquidity=10.0)
        high = plan_monetization(
            req_high.opportunity, req_high.market_capacity, DirectoryType.NICHE_INTEREST
        )
        low = plan_monetization(
            req_low.opportunity, req_low.market_capacity, DirectoryType.NICHE_INTEREST
        )

        def value(plan, model):
            return next(
                o.estimated_value_score for o in plan.ranked_options if o.model == model
            )

        assert value(low, MonetizationModel.ADVERTISING) < value(
            high, MonetizationModel.ADVERTISING
        )

    def test_travel_type_boosts_affiliate(self):
        req = make_request()
        travel = plan_monetization(req.opportunity, req.market_capacity, DirectoryType.TRAVEL)
        b2b = plan_monetization(req.opportunity, req.market_capacity, DirectoryType.B2B)

        def value(plan, model):
            return next(
                o.estimated_value_score for o in plan.ranked_options if o.model == model
            )

        assert value(travel, MonetizationModel.AFFILIATE) > value(b2b, MonetizationModel.AFFILIATE)

    def test_every_option_has_explainable_rationale(self):
        req = make_request()
        plan = plan_monetization(req.opportunity, req.market_capacity, DirectoryType.TRAVEL)
        assert all("base value" in o.rationale for o in plan.ranked_options)


# ---------------------------------------------------------------------------
# Roadmap planner
# ---------------------------------------------------------------------------


class TestRoadmapPlanner:
    def test_national_scope_costs_more_than_city(self):
        national = plan_roadmap(
            make_request(scope=GeographicScope.NATIONAL).opportunity,
            make_request().market_capacity,
        )
        city = plan_roadmap(
            make_request(scope=GeographicScope.CITY).opportunity,
            make_request().market_capacity,
        )
        assert national.total_estimated_effort_weeks > city.total_estimated_effort_weeks

    def test_dependencies_reference_earlier_phases_only(self):
        roadmap = plan_roadmap(make_request().opportunity, make_request().market_capacity)
        seen = set()
        for phase in roadmap.phases:
            for dep in phase.dependencies:
                assert dep in seen, "%s depends on %s before it exists" % (phase.name, dep)
            seen.add(phase.name)

    def test_total_equals_sum_of_phases(self):
        roadmap = plan_roadmap(make_request().opportunity, make_request().market_capacity)
        assert roadmap.total_estimated_effort_weeks == pytest.approx(
            round(sum(p.estimated_effort_weeks for p in roadmap.phases), 1)
        )


# ---------------------------------------------------------------------------
# Risk analyzer
# ---------------------------------------------------------------------------


class TestRiskAnalyzer:
    def test_seven_categories(self):
        req = make_request()
        analysis = analyze_risks(req.opportunity, req.market_capacity)
        categories = {a.category for a in analysis.assessments}
        assert categories == {
            "SEO risk", "Competition risk", "Operational risk",
            "Data acquisition risk", "Monetization risk",
            "Scaling risk", "AI content risk",
        }

    def test_high_competition_raises_seo_risk(self):
        low = make_request(competition=CompetitionLevel.LOW)
        high = make_request(competition=CompetitionLevel.HIGH)

        def seo_score(request):
            analysis = analyze_risks(request.opportunity, request.market_capacity)
            return next(a.score for a in analysis.assessments if a.category == "SEO risk")

        assert seo_score(high) > seo_score(low)

    def test_unverified_data_raises_monetization_risk(self):
        verified = make_request(data_tag=DataVerificationTag.VERIFIED)
        unknown = make_request(data_tag=DataVerificationTag.UNKNOWN)

        def monetization_score(request):
            analysis = analyze_risks(request.opportunity, request.market_capacity)
            return next(
                a.score for a in analysis.assessments if a.category == "Monetization risk"
            )

        assert monetization_score(unknown) > monetization_score(verified)

    def test_score_to_level_bands(self):
        assert score_to_level(1).value == "LOW"
        assert score_to_level(3).value == "LOW"
        assert score_to_level(4).value == "MODERATE"
        assert score_to_level(6).value == "ELEVATED"
        assert score_to_level(10).value == "HIGH"


# ---------------------------------------------------------------------------
# Scorecard
# ---------------------------------------------------------------------------


class TestScorecard:
    def test_all_scores_within_bounds(self):
        card = generate_blueprint(make_request()).project_scorecard
        for field in (
            card.complexity, card.build_time, card.operational_burden,
            card.content_burden, card.maintenance_burden, card.expansion_potential,
            card.scalability, card.automation_potential, card.ai_readiness,
            card.overall_build_readiness,
        ):
            assert 1 <= field <= 10

    def test_clone_reduces_complexity(self):
        clone = generate_blueprint(
            make_request(classification=ExpansionClass.CLONE)
        ).project_scorecard
        new_market = generate_blueprint(
            make_request(classification=ExpansionClass.NEW_MARKET)
        ).project_scorecard
        assert clone.complexity < new_market.complexity
        assert clone.expansion_potential > new_market.expansion_potential

    def test_verified_data_improves_readiness(self):
        verified = generate_blueprint(
            make_request(data_tag=DataVerificationTag.VERIFIED)
        ).project_scorecard
        estimated = generate_blueprint(
            make_request(data_tag=DataVerificationTag.ESTIMATED)
        ).project_scorecard
        assert verified.overall_build_readiness > estimated.overall_build_readiness

    def test_scorecard_explanations_present(self):
        card = generate_blueprint(make_request()).project_scorecard
        assert "overall_build_readiness" in card.explanations
        assert "complexity" in card.explanations


# ---------------------------------------------------------------------------
# Repository (raw SQL) round-trips
# ---------------------------------------------------------------------------


class TestRepository:
    def test_schema_creates_table(self, conn):
        repo.ensure_schema(conn)
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='directory_blueprints'"
        ).fetchone()
        assert row is not None

    def test_insert_and_fetch_round_trip(self, conn):
        repo.ensure_schema(conn)
        blueprint = generate_blueprint(make_request())
        row_id = repo.insert_blueprint(
            conn,
            project_slug=blueprint.project_profile.project_slug,
            engine_version=blueprint.engine_version,
            input_hash=blueprint.input_hash,
            committee_recommendation="BUILD",
            data_confidence_tag=blueprint.data_confidence_tag.value,
            blueprint_json=model_to_json(blueprint),
        )
        assert row_id is not None
        fetched = repo.get_blueprint_by_id(conn, row_id)
        assert fetched["project_slug"] == "ohio-dog-groomer-finder"
        restored = model_from_json(DirectoryBlueprint, fetched["blueprint_json"])
        assert model_to_dict(restored) == model_to_dict(blueprint)

    def test_duplicate_insert_is_idempotent(self, conn):
        repo.ensure_schema(conn)
        blueprint = generate_blueprint(make_request())
        kwargs = dict(
            project_slug=blueprint.project_profile.project_slug,
            engine_version=blueprint.engine_version,
            input_hash=blueprint.input_hash,
            committee_recommendation="BUILD",
            data_confidence_tag=blueprint.data_confidence_tag.value,
            blueprint_json=model_to_json(blueprint),
        )
        first = repo.insert_blueprint(conn, **kwargs)
        second = repo.insert_blueprint(conn, **kwargs)
        assert first is not None
        assert second is None
        assert len(repo.list_blueprints(conn)) == 1

    def test_latest_for_slug(self, conn):
        repo.ensure_schema(conn)
        blueprint = generate_blueprint(make_request())
        repo.insert_blueprint(
            conn,
            project_slug=blueprint.project_profile.project_slug,
            engine_version=blueprint.engine_version,
            input_hash=blueprint.input_hash,
            committee_recommendation="BUILD",
            data_confidence_tag=blueprint.data_confidence_tag.value,
            blueprint_json=model_to_json(blueprint),
        )
        latest = repo.get_latest_blueprint_for_slug(conn, "ohio-dog-groomer-finder")
        assert latest is not None
        assert repo.get_latest_blueprint_for_slug(conn, "nonexistent") is None


# ---------------------------------------------------------------------------
# Service orchestration
# ---------------------------------------------------------------------------


class TestService:
    def test_generate_and_store_happy_path(self, conn):
        result = service.generate_and_store_blueprint(conn, make_request())
        assert result.generated
        assert result.blueprint_id is not None
        assert result.blueprint.project_profile.project_slug == "ohio-dog-groomer-finder"

    def test_replay_returns_duplicate_with_stored_blueprint(self, conn):
        first = service.generate_and_store_blueprint(conn, make_request())
        second = service.generate_and_store_blueprint(conn, make_request())
        assert first.generated
        assert second.status == service.RESULT_DUPLICATE
        assert second.blueprint_id == first.blueprint_id
        assert model_to_dict(second.blueprint) == model_to_dict(first.blueprint)

    def test_load_latest_round_trip(self, conn):
        service.generate_and_store_blueprint(conn, make_request())
        loaded = service.load_latest_blueprint(conn, "ohio-dog-groomer-finder")
        assert loaded is not None
        assert len(loaded.implementation_roadmap.phases) == 8

    def test_from_payload_validates_raw_dicts(self, conn):
        payload = model_to_dict(make_request())
        result = service.generate_and_store_from_payload(conn, payload)
        assert result.generated

    def test_from_payload_rejects_invalid_recommendation(self, conn):
        payload = model_to_dict(make_request())
        payload["committee"]["recommendation"] = "MAYBE"
        with pytest.raises(Exception):
            service.generate_and_store_from_payload(conn, payload)


# ---------------------------------------------------------------------------
# Pydantic compatibility layer
# ---------------------------------------------------------------------------


class TestPydanticCompat:
    def test_dict_json_round_trip(self):
        blueprint = generate_blueprint(make_request())
        raw = model_to_json(blueprint)
        restored = model_from_json(DirectoryBlueprint, raw)
        assert model_to_dict(restored) == model_to_dict(blueprint)

    def test_enums_serialize_as_strings(self):
        blueprint = generate_blueprint(make_request())
        raw = model_to_json(blueprint)
        assert '"BUILD"' in raw or '"ESTIMATED"' in raw

    def test_shim_class_matches_functional_api(self):
        shim = BlueprintGenerator()
        request = make_request()
        assert shim.is_eligible(request) == is_blueprint_eligible(request)
        assert model_to_dict(shim.generate(request)) == model_to_dict(
            generate_blueprint(request)
        )
