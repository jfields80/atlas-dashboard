"""
scout.py — Scout: the Atlas Intelligence Orchestrator.
"""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

# Decision engine imports
from services.opportunity_v2.scout_decision_engine import (
    compute_verification_level, 
    compute_market_strength
)

from .dna.schema import OpportunityDNA
from .scout_providers import TaggedValue
from .business_intelligence import (
    BusinessIntelligence, 
    BusinessIntelligenceResult, 
    business_intelligence_to_dict,
    EstimatedBusinessIntelligenceProvider,
)
from .competition_intelligence import (
    CompetitionIntelligence, 
    CompetitionIntelligenceResult, 
    competition_intelligence_to_dict,
)
from .monetization_intelligence import (
    MonetizationIntelligence, 
    MonetizationIntelligenceResult, 
    monetization_intelligence_to_dict,
)

logger = logging.getLogger(__name__)

_GOOGLE_PLACES_API_KEY_ENV_VAR = "GOOGLE_PLACES_API_KEY"

def _build_default_business_intelligence() -> BusinessIntelligence:
    api_key = os.environ.get(_GOOGLE_PLACES_API_KEY_ENV_VAR)
    if not api_key:
        return BusinessIntelligence(providers=[EstimatedBusinessIntelligenceProvider()])

    try:
        from .business_provider_verified import VerifiedBusinessProvider
        from .google_places_business_data_source import GooglePlacesBusinessDataSource
        from .scout_query_builder import build_scout_queries

        return BusinessIntelligence(providers=[
            VerifiedBusinessProvider(
                data_source=GooglePlacesBusinessDataSource(
                    api_key=api_key, query_builder=build_scout_queries)),
            EstimatedBusinessIntelligenceProvider(),
        ])
    except Exception as e:
        logger.warning("Google Places provider could not be constructed: %s", e)
        return BusinessIntelligence(providers=[EstimatedBusinessIntelligenceProvider()])

@dataclass
class ScoutMetadata:
    niche_name: str
    dna_slug: str
    demand_intelligence_available: bool = False

@dataclass
class ProviderSummary:
    engine: str
    providers_used: list[str]
    verified_fields: list[str]
    estimated_fields: list[str]
    unknown_fields: list[str]

@dataclass
class ScoutResult:
    metadata: ScoutMetadata
    business: BusinessIntelligenceResult
    competition: CompetitionIntelligenceResult
    monetization: MonetizationIntelligenceResult
    demand: Optional[Any] = None
    provider_summaries: list[ProviderSummary] = field(default_factory=list)
    
    # Decision output fields
    latest_data_quality: Optional[str] = None
    market_strength: Optional[float] = None

    def to_market_capacity_overlay(self) -> "_MarketCapacityOverlay":
        return _MarketCapacityOverlay(self)

    def to_dict(self) -> dict:
        return scout_result_to_dict(self)

class _MarketCapacityOverlay:
    def __init__(self, scout: ScoutResult):
        self.verified_business_count = scout.business.business_count
        self.competition_score = scout.competition.competition_score
        self.affiliate_programs_found = scout.monetization.affiliate_programs
        self.avg_listing_price_usd = scout.monetization.premium_listing_value
        self.advertiser_demand = scout.monetization.advertiser_presence

class Scout:
    def __init__(self, business_engine=None, competition_engine=None, monetization_engine=None, demand_engine=None):
        self._business_engine_override = business_engine
        self._competition = competition_engine or CompetitionIntelligence()
        self._monetization = monetization_engine or MonetizationIntelligence()
        self._demand = demand_engine

    def _resolve_business_engine(self) -> BusinessIntelligence:
        if self._business_engine_override is not None:
            return self._business_engine_override
        return _build_default_business_intelligence()

    def research(self, niche_name: str, dna: OpportunityDNA, ctx: dict) -> ScoutResult:
        business_engine = self._resolve_business_engine()
        business_result = business_engine.research(niche_name, dna, ctx)
        competition_result = self._competition.research(niche_name, dna, ctx)
        monetization_result = self._monetization.research(niche_name, dna, ctx)

        # 🧠 EXPLICIT DATA EXTRACTION (Safe wiring)
        google_result = {
            "business_count": getattr(business_result.business_count, "value", 0) if business_result.business_count else 0,
            "average_review_count": getattr(business_result.review_count, "value", 0) if business_result.review_count else 0,
            "average_rating": getattr(business_result.rating_average, "value", 0) if business_result.rating_average else 0
        }
        
        quality = compute_verification_level(google_result)
        market_strength = compute_market_strength(google_result)

        summaries = [
            ProviderSummary(
                engine="business",
                providers_used=business_result.providers_used,
                verified_fields=business_result.verified_fields,
                estimated_fields=business_result.estimated_fields,
                unknown_fields=business_result.unknown_fields
            ),
            # Additional engine summaries would be appended here
        ]

        metadata = ScoutMetadata(niche_name=niche_name, dna_slug=dna.slug)
        
        return ScoutResult(
            metadata=metadata,
            business=business_result,
            competition=competition_result,
            monetization=monetization_result,
            provider_summaries=summaries,
            latest_data_quality=quality,
            market_strength=market_strength
        )