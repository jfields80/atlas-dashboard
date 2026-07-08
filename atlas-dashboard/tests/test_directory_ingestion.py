"""
Directory Data Ingestion & Seeding Engine — Test Suite (Phase 3B)
=================================================================

No external APIs. No live scraping. All fixtures are in-file sample
datasets: clean records, duplicates, and incomplete records.

Run:  pytest tests/test_directory_ingestion.py -v
"""

from __future__ import annotations

import json
import sqlite3

import pytest

from engines.directory_ingestion import (
    AUTO_MERGE_THRESHOLD,
    BlueprintInput,
    CategoryNode,
    DuplicateDetector,
    EnrichmentTaskGenerator,
    EnrichmentTaskType,
    ImportPreparer,
    ListingNormalizer,
    LocationNode,
    MergeRecommendation,
    Provenance,
    QUALITY_THRESHOLD,
    QualityEngine,
    RawListing,
    SeedPackageBuilder,
    SourcePlanner,
    SourceType,
    TaskPriority,
)
from repositories.directory_ingestion_repository import DirectoryIngestionRepository
from services.directory_ingestion_service import DirectoryIngestionService


# ===========================================================================
# Fixtures — sample datasets
# ===========================================================================

def _raw(raw_id: str, source: SourceType, **fields: str) -> RawListing:
    return RawListing(
        raw_id=raw_id,
        source_type=source,
        source_name=source.value,
        source_url=fields.pop("_source_url", None),
        payload=tuple(fields.items()),
    )


@pytest.fixture
def blueprint() -> BlueprintInput:
    return BlueprintInput(
        directory_slug="oh-dog-groomers",
        directory_name="Ohio Dog Groomers Directory",
        category_hierarchy=(
            CategoryNode(slug="grooming", name="Grooming"),
            CategoryNode(slug="mobile-grooming", name="Mobile Grooming",
                         parent_slug="grooming"),
        ),
        location_hierarchy=(
            LocationNode(slug="oh", name="Ohio", level="state", state_code="OH"),
            LocationNode(slug="columbus-oh", name="Columbus", level="city",
                         parent_slug="oh", state_code="OH"),
            LocationNode(slug="dublin-oh", name="Dublin", level="city",
                         parent_slug="oh", state_code="OH"),
        ),
        profile_schema_fields=("business_name", "address", "phone", "website"),
        search_keywords=("dog groomer columbus", "pet grooming ohio"),
    )


@pytest.fixture
def regulated_blueprint(blueprint: BlueprintInput) -> BlueprintInput:
    return BlueprintInput(
        directory_slug="oh-daycare",
        directory_name="Ohio Licensed Daycare Directory",
        category_hierarchy=(
            CategoryNode(slug="childcare", name="Licensed Childcare",
                         keywords=("daycare", "licensed")),
        ),
        location_hierarchy=blueprint.location_hierarchy,
        profile_schema_fields=blueprint.profile_schema_fields,
        search_keywords=("licensed daycare ohio",),
    )


@pytest.fixture
def clean_raws() -> list[RawListing]:
    """Complete, well-formed records."""
    return [
        _raw(
            "raw_001", SourceType.GOOGLE_PLACES,
            _source_url="https://maps.example.com/pawsclub",
            name="Paws Club Grooming",
            address="123 Main St", city="Columbus", state="OH", zip="43004",
            phone="(614) 555-0101", website="pawsclub.com",
            email="hello@pawsclub.com",
            categories="Grooming, Mobile Grooming",
            hours="Mon-Fri 9-5",
            latitude="39.9612", longitude="-82.9988",
            description=(
                "Full-service dog grooming salon in Columbus offering baths, "
                "cuts, nail trims and de-shedding for all breeds since 2015."
            ),
            services="Bath; Nail Trim; De-shedding",
            pricing="From $45",
        ),
        _raw(
            "raw_002", SourceType.GOVERNMENT_OPEN_DATA,
            company="DUBLIN DOG SPA LLC",
            street_address="500 Bridge Park Ave", city="Dublin",
            state="Ohio", postal_code="43017",
            phone_number="614.555.0102",
            url="https://www.dublindogspa.com/",
        ),
    ]


@pytest.fixture
def duplicate_raws() -> list[RawListing]:
    """Same real-world business arriving from three sources."""
    return [
        _raw(
            "dup_a", SourceType.GOOGLE_PLACES,
            name="Bark Avenue Grooming",
            address="77 High St", city="Columbus", state="OH", zip="43215",
            phone="614-555-0200", website="https://barkavenue.com",
            latitude="39.9650", longitude="-83.0000",
        ),
        _raw(
            "dup_b", SourceType.PUBLIC_DIRECTORY,
            business_name="Bark Avenue Grooming LLC",
            address="77 High Street", city="Columbus", state="OH",
            phone="(614) 555-0200",
        ),
        _raw(
            "dup_c", SourceType.CSV_IMPORT,
            name="BARK AVENUE GROOMING",
            city="Columbus", state="OH",
            website="www.barkavenue.com",
            latitude="39.9651", longitude="-83.0001",
        ),
        # Not a duplicate — different business, same city.
        _raw(
            "uniq_d", SourceType.CSV_IMPORT,
            name="Shaggy Chic Salon",
            address="9 Elm St", city="Columbus", state="OH",
            phone="614-555-0999",
        ),
    ]


@pytest.fixture
def incomplete_raws() -> list[RawListing]:
    """Sparse and broken records."""
    return [
        _raw("inc_001", SourceType.CSV_IMPORT, name="Mystery Groomer"),
        _raw("inc_002", SourceType.CSV_IMPORT,
             name="Bad Contact Co", phone="123", website="not a url",
             email="nope", state="Narnia", zip="ABCDE"),
        _raw("inc_003", SourceType.CSV_IMPORT, address="1 Nameless Rd"),  # no name → reject
    ]


@pytest.fixture
def repo(tmp_path) -> DirectoryIngestionRepository:
    conn = sqlite3.connect(tmp_path / "atlas_test.db")
    repository = DirectoryIngestionRepository(conn)
    repository.ensure_schema()
    return repository


@pytest.fixture
def service(repo: DirectoryIngestionRepository) -> DirectoryIngestionService:
    return DirectoryIngestionService(repo)


# ===========================================================================
# 1. Source Planner
# ===========================================================================

class TestSourcePlanner:
    def test_plan_covers_all_source_types(self, blueprint):
        plan = SourcePlanner().plan(blueprint)
        assert {r.source_type for r in plan.recommendations} == set(SourceType)

    def test_ranks_are_sequential_and_sorted(self, blueprint):
        plan = SourcePlanner().plan(blueprint)
        ranks = [r.rank for r in plan.recommendations]
        assert ranks == list(range(1, len(ranks) + 1))
        overalls = [r.overall_score for r in plan.recommendations]
        assert overalls == sorted(overalls, reverse=True)

    def test_deterministic(self, blueprint):
        assert SourcePlanner().plan(blueprint) == SourcePlanner().plan(blueprint)

    def test_future_sources_flagged_unimplemented(self, blueprint):
        plan = SourcePlanner().plan(blueprint)
        future = {r.source_type: r for r in plan.recommendations}
        assert not future[SourceType.FUTURE_SCRAPER].implemented
        assert not future[SourceType.FUTURE_API].implemented
        assert future[SourceType.CSV_IMPORT].implemented

    def test_regulated_niche_boosts_government_coverage(self, blueprint, regulated_blueprint):
        base = SourcePlanner().plan(blueprint)
        boosted = SourcePlanner().plan(regulated_blueprint)

        def gov(plan):
            return next(r for r in plan.recommendations
                        if r.source_type == SourceType.GOVERNMENT_OPEN_DATA)

        assert gov(boosted).coverage_score > gov(base).coverage_score


# ===========================================================================
# 2. Listing Normalizer
# ===========================================================================

class TestListingNormalizer:
    def test_normalizes_clean_record(self, clean_raws):
        n = ListingNormalizer().normalize(clean_raws[0])
        assert n is not None
        assert n.business_name == "Paws Club Grooming"
        assert n.phone.value == "(614) 555-0101"
        assert n.website.value == "https://pawsclub.com"
        assert n.state.value == "OH"
        assert n.zip_code.value == "43004"
        assert n.latitude == pytest.approx(39.9612)
        assert n.categories == ("Grooming", "Mobile Grooming")

    def test_alternate_source_keys_and_state_name(self, clean_raws):
        n = ListingNormalizer().normalize(clean_raws[1])
        assert n is not None
        # company → business_name, ALL-CAPS title-cased
        assert n.business_name == "Dublin Dog Spa Llc"
        # "Ohio" → "OH"
        assert n.state.value == "OH"
        # dotted phone normalized
        assert n.phone.value == "(614) 555-0102"
        # trailing slash stripped
        assert n.website.value == "https://www.dublindogspa.com"

    def test_verified_source_tags_provenance(self, clean_raws):
        gov = ListingNormalizer().normalize(clean_raws[1])
        places = ListingNormalizer().normalize(clean_raws[0])
        assert gov.verified is True
        assert gov.address.provenance is Provenance.VERIFIED
        assert places.verified is False
        assert places.address.provenance is Provenance.ESTIMATED

    def test_invalid_values_become_unknown(self, incomplete_raws):
        n = ListingNormalizer().normalize(incomplete_raws[1])
        assert n.phone.value is None
        assert n.phone.provenance is Provenance.UNKNOWN
        assert n.website.value is None
        assert n.email.value is None
        assert n.state.value is None
        assert n.zip_code.value is None

    def test_nameless_record_rejected(self, incomplete_raws):
        normalized, rejected = ListingNormalizer().normalize_batch(incomplete_raws)
        assert rejected == ["inc_003"]
        assert len(normalized) == 2

    def test_confidence_scales_with_completeness(self, clean_raws, incomplete_raws):
        full = ListingNormalizer().normalize(clean_raws[0])
        sparse = ListingNormalizer().normalize(incomplete_raws[0])
        assert full.confidence > sparse.confidence
        assert 0.0 <= sparse.confidence <= 1.0

    def test_listing_id_deterministic(self, clean_raws):
        a = ListingNormalizer().normalize(clean_raws[0])
        b = ListingNormalizer().normalize(clean_raws[0])
        assert a.listing_id == b.listing_id


# ===========================================================================
# 3. Duplicate Detection
# ===========================================================================

class TestDuplicateDetector:
    def _normalized(self, raws):
        normalized, _ = ListingNormalizer().normalize_batch(raws)
        return normalized

    def test_detects_three_way_duplicate(self, duplicate_raws):
        listings = self._normalized(duplicate_raws)
        report = DuplicateDetector().detect(listings)
        assert len(report.clusters) == 1
        cluster = report.clusters[0]
        assert len(cluster.listing_ids) == 3
        assert report.total_listings == 4
        assert report.unique_listings == 2  # cluster + Shaggy Chic

    def test_unrelated_listing_not_clustered(self, duplicate_raws):
        listings = self._normalized(duplicate_raws)
        report = DuplicateDetector().detect(listings)
        shaggy = next(l for l in listings if l.business_name == "Shaggy Chic Salon")
        assert all(shaggy.listing_id not in c.listing_ids for c in report.clusters)

    def test_matched_signals_recorded(self, duplicate_raws):
        listings = self._normalized(duplicate_raws)
        report = DuplicateDetector().detect(listings)
        all_signals = {s for c in report.clusters for p in c.pairs for s in p.matched_signals}
        assert "name" in all_signals
        assert "phone" in all_signals or "website" in all_signals

    def test_canonical_prefers_most_complete(self, duplicate_raws):
        listings = self._normalized(duplicate_raws)
        report = DuplicateDetector().detect(listings)
        canonical_id = report.clusters[0].canonical_listing_id
        canonical = next(l for l in listings if l.listing_id == canonical_id)
        # dup_a has address+phone+website+geo → most complete
        assert canonical.raw_id == "dup_a"

    def test_canonical_listings_collapse(self, duplicate_raws):
        listings = self._normalized(duplicate_raws)
        detector = DuplicateDetector()
        report = detector.detect(listings)
        canonical = detector.canonical_listings(listings, report)
        assert len(canonical) == 2

    def test_merge_recommendation_bounds(self, duplicate_raws):
        listings = self._normalized(duplicate_raws)
        report = DuplicateDetector().detect(listings)
        for c in report.clusters:
            if c.confidence >= AUTO_MERGE_THRESHOLD:
                assert c.merge_recommendation is MergeRecommendation.AUTO_MERGE
            else:
                assert c.merge_recommendation is MergeRecommendation.REVIEW

    def test_no_duplicates_in_clean_set(self, clean_raws):
        listings = self._normalized(clean_raws)
        report = DuplicateDetector().detect(listings)
        assert report.clusters == ()
        assert report.unique_listings == len(listings)

    def test_deterministic(self, duplicate_raws):
        listings = self._normalized(duplicate_raws)
        assert DuplicateDetector().detect(listings) == DuplicateDetector().detect(listings)


# ===========================================================================
# 4. Data Quality Engine
# ===========================================================================

class TestQualityEngine:
    def _one(self, raw):
        return ListingNormalizer().normalize(raw)

    def test_complete_listing_scores_high(self, clean_raws):
        score = QualityEngine().score(self._one(clean_raws[0]))
        assert score.overall >= QUALITY_THRESHOLD
        assert score.completeness >= 90
        assert score.contact_quality == 100

    def test_sparse_listing_scores_low(self, incomplete_raws):
        score = QualityEngine().score(self._one(incomplete_raws[0]))
        assert score.overall < QUALITY_THRESHOLD
        assert score.contact_quality == 0

    def test_all_dimensions_bounded(self, clean_raws, incomplete_raws):
        engine = QualityEngine()
        for raw in clean_raws + incomplete_raws[:2]:
            s = engine.score(self._one(raw))
            for dim in (s.completeness, s.contact_quality, s.location_accuracy,
                        s.seo_readiness, s.monetization_readiness,
                        s.verification_quality, s.freshness, s.overall):
                assert 0 <= dim <= 100

    def test_verified_source_boosts_verification(self, clean_raws):
        gov = QualityEngine().score(self._one(clean_raws[1]))
        places = QualityEngine().score(self._one(clean_raws[0]))
        assert gov.verification_quality > places.verification_quality

    def test_explanations_present(self, clean_raws):
        score = QualityEngine().score(self._one(clean_raws[0]))
        assert len(score.explanations) >= 7

    def test_batch_report(self, clean_raws, incomplete_raws):
        listings = [self._one(r) for r in clean_raws + incomplete_raws[:1]]
        report = QualityEngine().score_batch(listings)
        assert len(report.scores) == 3
        assert report.threshold == QUALITY_THRESHOLD
        assert 0 <= report.average_overall <= 100
        assert report.listings_above_threshold >= 1


# ===========================================================================
# 5. Enrichment Task Generator
# ===========================================================================

class TestEnrichmentGenerator:
    def _tasks_for(self, raw):
        listing = ListingNormalizer().normalize(raw)
        score = QualityEngine().score(listing)
        return listing, EnrichmentTaskGenerator().generate(listing, score)

    def test_missing_fields_generate_tasks(self, incomplete_raws):
        _, tasks = self._tasks_for(incomplete_raws[0])
        types = {t.task_type for t in tasks}
        assert EnrichmentTaskType.FIND_WEBSITE in types
        assert EnrichmentTaskType.FIND_PHONE in types
        assert EnrichmentTaskType.FIND_EMAIL in types
        assert EnrichmentTaskType.WRITE_DESCRIPTION in types
        assert EnrichmentTaskType.CATEGORIZE_BUSINESS in types

    def test_complete_listing_skips_contact_tasks(self, clean_raws):
        _, tasks = self._tasks_for(clean_raws[0])
        types = {t.task_type for t in tasks}
        assert EnrichmentTaskType.FIND_WEBSITE not in types
        assert EnrichmentTaskType.FIND_PHONE not in types

    def test_premium_candidate_flagged_for_monetizable_listing(self, clean_raws):
        _, tasks = self._tasks_for(clean_raws[0])
        types = {t.task_type for t in tasks}
        assert EnrichmentTaskType.FIND_PREMIUM_CANDIDATE in types

    def test_task_ids_stable_across_replays(self, incomplete_raws):
        _, first = self._tasks_for(incomplete_raws[0])
        _, second = self._tasks_for(incomplete_raws[0])
        assert [t.task_id for t in first] == [t.task_id for t in second]

    def test_batch_ordered_by_priority(self, clean_raws, incomplete_raws):
        normalizer, engine, gen = ListingNormalizer(), QualityEngine(), EnrichmentTaskGenerator()
        listings = [normalizer.normalize(r) for r in clean_raws + incomplete_raws[:2]]
        scores = {l.listing_id: engine.score(l) for l in listings}
        tasks = gen.generate_batch(listings, scores)
        order = {TaskPriority.HIGH: 0, TaskPriority.MEDIUM: 1, TaskPriority.LOW: 2}
        priorities = [order[t.priority] for t in tasks]
        assert priorities == sorted(priorities)


# ===========================================================================
# 6 + 7. Seed Package Builder & Import Preparation (via service pipeline)
# ===========================================================================

class TestSeedPackageAndImport:
    def _package(self, blueprint, raws, service):
        return service.run_ingestion(blueprint, raws).package

    def test_package_contents(self, blueprint, duplicate_raws, service):
        pkg = self._package(blueprint, duplicate_raws, service)
        assert pkg.directory_slug == "oh-dog-groomers"
        assert pkg.statistics.total_raw == 4
        assert pkg.statistics.total_normalized == 4
        assert pkg.statistics.total_canonical == 2
        assert pkg.statistics.duplicate_clusters == 1
        assert len(pkg.categories) == 2
        assert len(pkg.locations) == 3
        assert pkg.package_id.startswith("seed_")

    def test_package_id_content_addressed(self, blueprint, duplicate_raws, repo):
        s1 = DirectoryIngestionService(repo)
        pkg_a = self._package(blueprint, duplicate_raws, s1)
        pkg_b = SeedPackageBuilder().build(
            blueprint, list(pkg_a.businesses), pkg_a.duplicate_report,
            pkg_a.quality_report, list(pkg_a.enrichment_queue),
            pkg_a.statistics.total_raw, pkg_a.statistics.total_normalized,
        )
        assert pkg_a.package_id == pkg_b.package_id

    def test_json_export_round_trips(self, blueprint, clean_raws, service):
        pkg = self._package(blueprint, clean_raws, service)
        artifact = ImportPreparer().to_json(pkg)
        payload = json.loads(artifact.artifact)
        assert payload["package_id"] == pkg.package_id
        assert len(payload["businesses"]) == 2
        assert artifact.validation.valid is True

    def test_csv_export_has_all_rows(self, blueprint, clean_raws, service):
        pkg = self._package(blueprint, clean_raws, service)
        artifact = ImportPreparer().to_csv(pkg)
        lines = artifact.artifact.strip().splitlines()
        assert len(lines) == 1 + 2  # header + rows
        assert lines[0].startswith("listing_id,business_name")

    def test_sqlite_staging_script_executes(self, blueprint, clean_raws, service):
        pkg = self._package(blueprint, clean_raws, service)
        artifact = ImportPreparer().to_sqlite_staging(pkg)
        conn = sqlite3.connect(":memory:")
        conn.executescript(artifact.artifact)
        count = conn.execute("SELECT COUNT(*) FROM staging_businesses").fetchone()[0]
        assert count == 2

    def test_validation_flags_unknown_category(self, blueprint, service):
        raws = [_raw("v1", SourceType.CSV_IMPORT, name="Odd Biz",
                     city="Columbus", state="OH", categories="Skydiving")]
        pkg = self._package(blueprint, raws, service)
        report = ImportPreparer().validate(pkg)
        assert report.valid is True  # warnings only
        assert any("Skydiving" in i.message for i in report.issues)

    def test_validation_warns_on_unlocatable_listing(self, blueprint, service):
        raws = [_raw("v2", SourceType.CSV_IMPORT, name="Nowhere Biz")]
        pkg = self._package(blueprint, raws, service)
        report = ImportPreparer().validate(pkg)
        assert any("No city/state" in i.message for i in report.issues)


# ===========================================================================
# 9. Storage — repository round trips
# ===========================================================================

class TestRepository:
    def test_raw_listing_round_trip(self, repo, clean_raws):
        repo.create_run("run_t1", "oh-dog-groomers", "directory_ingestion", "1.0.0")
        repo.save_raw_listings("run_t1", clean_raws)
        loaded = repo.get_raw_listings("run_t1")
        assert loaded == sorted(clean_raws, key=lambda r: r.raw_id)

    def test_normalized_listing_round_trip(self, repo, clean_raws):
        repo.create_run("run_t2", "oh-dog-groomers", "directory_ingestion", "1.0.0")
        repo.save_raw_listings("run_t2", clean_raws)
        normalized, _ = ListingNormalizer().normalize_batch(clean_raws)
        repo.save_normalized_listings("run_t2", normalized)
        loaded = repo.get_normalized_listings("run_t2")
        assert loaded == sorted(normalized, key=lambda l: l.listing_id)
        # provenance survives the round trip
        assert loaded[0].address.provenance in (Provenance.VERIFIED, Provenance.ESTIMATED)

    def test_canonical_flag(self, repo, duplicate_raws):
        repo.create_run("run_t3", "oh-dog-groomers", "directory_ingestion", "1.0.0")
        repo.save_raw_listings("run_t3", duplicate_raws)
        normalized, _ = ListingNormalizer().normalize_batch(duplicate_raws)
        repo.save_normalized_listings("run_t3", normalized)
        repo.mark_non_canonical([normalized[0].listing_id])
        canonical = repo.get_normalized_listings("run_t3", canonical_only=True)
        assert len(canonical) == len(normalized) - 1

    def test_task_status_update(self, repo, incomplete_raws):
        repo.create_run("run_t4", "oh-dog-groomers", "directory_ingestion", "1.0.0")
        repo.save_raw_listings("run_t4", incomplete_raws[:1])
        listing = ListingNormalizer().normalize(incomplete_raws[0])
        repo.save_normalized_listings("run_t4", [listing])
        score = QualityEngine().score(listing)
        tasks = EnrichmentTaskGenerator().generate(listing, score)
        repo.save_enrichment_tasks("run_t4", tasks)
        repo.update_task_status(tasks[0].task_id, "done")
        pending = repo.get_enrichment_tasks("run_t4", status="pending")
        done = repo.get_enrichment_tasks("run_t4", status="done")
        assert len(done) == 1
        assert len(pending) == len(tasks) - 1


# ===========================================================================
# 10. Service — full pipeline integration
# ===========================================================================

class TestServicePipeline:
    def test_full_pipeline_persists_all_stages(self, blueprint, duplicate_raws,
                                               service, repo):
        result = service.run_ingestion(blueprint, duplicate_raws)
        assert result.replayed is False
        run = repo.get_run(result.run_id)
        assert run["status"] == "complete"
        assert run["package_id"] == result.package.package_id
        assert len(repo.get_raw_listings(result.run_id)) == 4
        assert len(repo.get_normalized_listings(result.run_id)) == 4
        assert len(repo.get_normalized_listings(result.run_id, canonical_only=True)) == 2
        assert len(repo.get_duplicate_clusters(result.run_id)) == 1
        assert len(repo.get_quality_scores(result.run_id)) == 2
        assert len(repo.get_enrichment_tasks(result.run_id)) > 0
        assert repo.get_seed_package_json(result.package.package_id) is not None

    def test_replay_is_idempotent(self, blueprint, duplicate_raws, service):
        first = service.run_ingestion(blueprint, duplicate_raws)
        second = service.run_ingestion(blueprint, duplicate_raws)
        assert second.replayed is True
        assert second.run_id == first.run_id
        assert second.package.package_id == first.package.package_id

    def test_rejected_raw_ids_surfaced(self, blueprint, incomplete_raws, service):
        result = service.run_ingestion(blueprint, incomplete_raws)
        assert result.rejected_raw_ids == ("inc_003",)

    def test_source_plan_via_service(self, blueprint, service):
        plan = service.plan_sources(blueprint)
        assert plan.directory_slug == blueprint.directory_slug
        assert len(plan.recommendations) == len(SourceType)

    def test_prepare_import_formats(self, blueprint, clean_raws, service):
        pkg = service.run_ingestion(blueprint, clean_raws).package
        for fmt in ("json", "csv", "sqlite_staging"):
            artifact = service.prepare_import(pkg, fmt)
            assert artifact.format == fmt
            assert artifact.artifact
        with pytest.raises(ValueError):
            service.prepare_import(pkg, "xml")

    def test_load_persisted_package(self, blueprint, clean_raws, service):
        pkg = service.run_ingestion(blueprint, clean_raws).package
        payload = json.loads(service.load_seed_package_json(pkg.package_id))
        assert payload["directory_slug"] == "oh-dog-groomers"
        with pytest.raises(KeyError):
            service.load_seed_package_json("seed_missing")

    def test_pipeline_deterministic_package_id(self, blueprint, duplicate_raws, tmp_path):
        def fresh_service(name):
            conn = sqlite3.connect(tmp_path / name)
            r = DirectoryIngestionRepository(conn)
            r.ensure_schema()
            return DirectoryIngestionService(r)

        a = fresh_service("a.db").run_ingestion(blueprint, duplicate_raws)
        b = fresh_service("b.db").run_ingestion(blueprint, duplicate_raws)
        assert a.package.package_id == b.package.package_id
