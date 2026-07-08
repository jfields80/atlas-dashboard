"""
Module 8 — Future Extension Points
==================================

Abstract provider interfaces for future data sources. NOTHING here is
implemented — Phase 3B ships interfaces only, per spec. When a provider
lands, it plugs into the existing pipeline by returning RawListing records;
everything downstream (normalize → dedupe → quality → enrich → seed) is
already built and unchanged.

Mirrors the Scout Intelligence provider architecture.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from engines.directory_ingestion.ingestion_models import (
    BlueprintInput,
    RawListing,
    SourceType,
)


@dataclass(frozen=True)
class ProviderCapabilities:
    """Static declaration of what a provider can do — used by the
    SourcePlanner in future phases to replace editorial base scores with
    provider-declared capabilities."""
    provider_name: str
    source_type: SourceType
    supports_geo_search: bool
    supports_category_search: bool
    supports_pagination: bool
    rate_limited: bool
    cost_per_thousand_usd: float


class ListingProvider(ABC):
    """
    Contract every future acquisition provider must satisfy.

    Implementations MUST:
        * be deterministic given identical remote responses (record raw
          payloads verbatim; no in-provider cleaning — that is the
          ListingNormalizer's job),
        * never write to the database (PipelineRunner remains the sole
          database writer),
        * surface provenance via RawListing.source_type / source_url.
    """

    @abstractmethod
    def capabilities(self) -> ProviderCapabilities:
        """Declare static capabilities."""

    @abstractmethod
    def fetch(self, blueprint: BlueprintInput, limit: int) -> list[RawListing]:
        """Fetch raw listings for the blueprint's categories and locations."""


class GooglePlacesProvider(ListingProvider, ABC):
    """Future: Google Places API. Interface reserved — do not implement in 3B."""


class OpenStreetMapProvider(ListingProvider, ABC):
    """Future: OSM/Overpass. Interface reserved — do not implement in 3B."""


class YelpProvider(ListingProvider, ABC):
    """Future: Yelp Fusion API. Interface reserved — do not implement in 3B."""


class AppleMapsProvider(ListingProvider, ABC):
    """Future: Apple Maps Server API. Interface reserved."""


class FacebookProvider(ListingProvider, ABC):
    """Future: Facebook Pages. Interface reserved."""


class LinkedInProvider(ListingProvider, ABC):
    """Future: LinkedIn company data. Interface reserved."""


class ScraperProvider(ListingProvider, ABC):
    """Future: site-specific scrapers. Interface reserved."""


class LLMEnrichmentProvider(ABC):
    """
    Future: LLM-backed enrichment workers ("AI Employees").

    Consumes EnrichmentTask records from the queue and returns proposed
    field updates tagged ESTIMATED — never VERIFIED. Verification remains a
    human/authoritative-source responsibility (honest wall preserved).
    """

    @abstractmethod
    def execute_task(self, task_id: str) -> dict[str, str]:
        """Return proposed field updates for the task's listing."""
