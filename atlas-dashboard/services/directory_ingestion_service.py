"""
Directory Ingestion Service
===========================

Orchestrates the ingestion pipeline:

    RawListings
        → ListingNormalizer
        → DuplicateDetector
        → QualityEngine
        → EnrichmentTaskGenerator
        → SeedPackageBuilder
        → ImportPreparer
        → Repository (persistence)

Atlas contract:
    * Business logic lives here and in engines — never in repositories.
    * No SQL in this module; all persistence via DirectoryIngestionRepository.
    * Framework agnostic: no Flask objects, no HTML, no request context.
    * Idempotent: replaying identical inputs reuses the completed run.

Integration note: when this subsystem is wired into PipelineRunner (the
sole orchestrator/database writer in Atlas), PipelineRunner will call
``run_ingestion`` and own the connection lifecycle. Until then, this
service is directly callable with an injected repository.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from engines.directory_ingestion.ingestion_models import (
    ENGINE_NAME,
    ENGINE_VERSION,
    BlueprintInput,
    ImportPackage,
    RawListing,
    SeedPackage,
    SourcePlan,
)
from engines.directory_ingestion.source_planner import SourcePlanner
from engines.directory_ingestion.listing_normalizer import ListingNormalizer
from engines.directory_ingestion.duplicate_detector import DuplicateDetector
from engines.directory_ingestion.quality_engine import QualityEngine
from engines.directory_ingestion.enrichment_generator import EnrichmentTaskGenerator
from engines.directory_ingestion.seed_package_builder import SeedPackageBuilder
from engines.directory_ingestion.import_preparer import ImportPreparer
from repositories.directory_ingestion_repository import DirectoryIngestionRepository


@dataclass(frozen=True)
class IngestionResult:
    """Immutable result snapshot returned to callers (PipelineRunner-ready)."""
    run_id: str
    package: SeedPackage
    rejected_raw_ids: tuple[str, ...]
    replayed: bool          # True when idempotency short-circuited the run


class DirectoryIngestionService:
    """Orchestrator for the Directory Data Ingestion & Seeding Engine."""

    def __init__(self, repository: DirectoryIngestionRepository) -> None:
        self._repo = repository
        self._planner = SourcePlanner()
        self._normalizer = ListingNormalizer()
        self._detector = DuplicateDetector()
        self._quality = QualityEngine()
        self._enricher = EnrichmentTaskGenerator()
        self._builder = SeedPackageBuilder()
        self._importer = ImportPreparer()

    # -- public API -------------------------------------------------------------

    def plan_sources(self, blueprint: BlueprintInput) -> SourcePlan:
        """Module 1: rank acquisition strategies for a blueprint."""
        return self._planner.plan(blueprint)

    def run_ingestion(
        self, blueprint: BlueprintInput, raw_listings: list[RawListing]
    ) -> IngestionResult:
        """
        Execute the full ingestion pipeline and persist every stage.

        Deterministic and idempotent: the run id is a content hash of the
        blueprint slug + raw ids; if a completed run with the resulting
        package already exists, it is replayed rather than recomputed.
        """
        run_id = self._run_id(blueprint, raw_listings)

        # 1. Normalize
        normalized, rejected = self._normalizer.normalize_batch(raw_listings)

        # 2. Deduplicate
        duplicate_report = self._detector.detect(normalized)
        canonical = self._detector.canonical_listings(normalized, duplicate_report)

        # 3. Quality — canonical listings only (merged-away records are noise)
        quality_report = self._quality.score_batch(canonical)
        scores_by_listing = {s.listing_id: s for s in quality_report.scores}

        # 4. Enrichment queue
        enrichment_queue = self._enricher.generate_batch(canonical, scores_by_listing)

        # 5. Seed package
        package = self._builder.build(
            blueprint=blueprint,
            canonical_listings=canonical,
            duplicate_report=duplicate_report,
            quality_report=quality_report,
            enrichment_queue=enrichment_queue,
            total_raw=len(raw_listings),
            total_normalized=len(normalized),
        )

        # Idempotency: identical package already persisted → replay.
        existing = self._repo.find_run_by_package(package.package_id)
        if existing is not None:
            return IngestionResult(
                run_id=existing["run_id"],
                package=package,
                rejected_raw_ids=tuple(sorted(rejected)),
                replayed=True,
            )

        # 6. Persist every stage
        self._repo.create_run(run_id, blueprint.directory_slug, ENGINE_NAME, ENGINE_VERSION)
        try:
            self._repo.save_raw_listings(run_id, raw_listings)
            self._repo.save_normalized_listings(run_id, normalized)

            merged_away = [
                lid
                for cluster in duplicate_report.clusters
                for lid in cluster.listing_ids
                if lid != cluster.canonical_listing_id
            ]
            if merged_away:
                self._repo.mark_non_canonical(merged_away)

            self._repo.save_duplicate_clusters(run_id, list(duplicate_report.clusters))
            self._repo.save_quality_scores(run_id, list(quality_report.scores))
            self._repo.save_enrichment_tasks(run_id, enrichment_queue)

            package_json = self._importer.to_json(package).artifact
            self._repo.save_seed_package(run_id, package, package_json)
            self._repo.complete_run(run_id, package.package_id)
        except Exception:
            self._repo.fail_run(run_id)
            raise

        return IngestionResult(
            run_id=run_id,
            package=package,
            rejected_raw_ids=tuple(sorted(rejected)),
            replayed=False,
        )

    def prepare_import(self, package: SeedPackage, fmt: str) -> ImportPackage:
        """Module 7: generate an import-ready artifact. fmt ∈ json|csv|sqlite_staging."""
        if fmt == "json":
            return self._importer.to_json(package)
        if fmt == "csv":
            return self._importer.to_csv(package)
        if fmt == "sqlite_staging":
            return self._importer.to_sqlite_staging(package)
        raise ValueError(f"Unsupported import format: {fmt!r}")

    def load_seed_package_json(self, package_id: str) -> str:
        """Retrieve a persisted seed package (JSON) by id."""
        payload = self._repo.get_seed_package_json(package_id)
        if payload is None:
            raise KeyError(f"Seed package not found: {package_id}")
        return payload

    # -- helpers ------------------------------------------------------------------

    @staticmethod
    def _run_id(blueprint: BlueprintInput, raws: list[RawListing]) -> str:
        fingerprint = blueprint.directory_slug + "|" + "|".join(
            sorted(r.raw_id for r in raws)
        )
        digest = hashlib.sha256(fingerprint.encode()).hexdigest()
        return f"run_{digest[:16]}"
