"""
Module 6 — Seed Package Builder
===============================

Assembles the final Normalized Directory Seed Package: canonical businesses,
blueprint categories and locations, duplicate + quality reports, the
enrichment queue, statistics and metadata.

Package ids are content-addressed hashes → replaying identical inputs yields
the identical package id (Prediction Ledger–style idempotency).
"""

from __future__ import annotations

import hashlib

from engines.directory_ingestion.ingestion_models import (
    BlueprintInput,
    DuplicateReport,
    EnrichmentTask,
    NormalizedListing,
    QualityReport,
    SeedPackage,
    SeedStatistics,
)


class SeedPackageBuilder:
    """Stateless builder for seed packages."""

    def build(
        self,
        blueprint: BlueprintInput,
        canonical_listings: list[NormalizedListing],
        duplicate_report: DuplicateReport,
        quality_report: QualityReport,
        enrichment_queue: list[EnrichmentTask],
        total_raw: int,
        total_normalized: int,
    ) -> SeedPackage:
        businesses = tuple(sorted(canonical_listings, key=lambda l: l.listing_id))
        statistics = SeedStatistics(
            total_raw=total_raw,
            total_normalized=total_normalized,
            total_canonical=len(businesses),
            duplicate_clusters=len(duplicate_report.clusters),
            enrichment_tasks=len(enrichment_queue),
            average_quality=quality_report.average_overall,
            verified_count=sum(1 for b in businesses if b.verified),
        )
        return SeedPackage(
            package_id=self._package_id(blueprint.directory_slug, businesses),
            directory_slug=blueprint.directory_slug,
            businesses=businesses,
            categories=blueprint.category_hierarchy,
            locations=blueprint.location_hierarchy,
            duplicate_report=duplicate_report,
            quality_report=quality_report,
            enrichment_queue=tuple(enrichment_queue),
            statistics=statistics,
        )

    @staticmethod
    def _package_id(directory_slug: str, businesses: tuple[NormalizedListing, ...]) -> str:
        fingerprint = directory_slug + "|" + "|".join(b.listing_id for b in businesses)
        digest = hashlib.sha256(fingerprint.encode()).hexdigest()
        return f"seed_{digest[:16]}"
