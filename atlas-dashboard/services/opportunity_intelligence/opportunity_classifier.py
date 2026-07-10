"""
atlas/services/opportunity_intelligence/opportunity_classifier.py

AES-012C — Opportunity Classification Engine.

Enriches an Opportunity + its MarketProfile (AES-012B) into a
structured OpportunityClassification — industry, audience, business
type, commercial intent, market vertical, business model — for
downstream analysts to consume. No AI, no LLM calls, no web access,
no external APIs, no persistence, no global state.

Deterministic classification via small, explicit, configurable lookup
tables — no hardcoded if/elif chains. Reuses MarketProfile.
primary_category (already derived by MarketResearchAnalyst) rather
than re-deriving category from raw text a second time.

Honesty rule (same convention as market_research_analyst.py): a field
is only set to something other than "UNKNOWN" when a real keyword/
lookup match was found. commercial_intent and business_type are
derived FROM the recognized industry/category — if nothing was
recognized upstream, this stage has nothing to classify and every
field honestly stays "UNKNOWN". business_model is intentionally left
"UNKNOWN" in this version: no monetization signal is available yet to
derive it from (a future analyst may add that signal).

Independent package: no Flask, no repositories, no persistence, no
services.opportunity_v2, no orchestrator, no Learning Memory, no
network I/O of any kind.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional, Tuple

from services.opportunity_intelligence.models import (
    MarketProfile,
    Opportunity,
    OpportunityClassification,
)


class CommercialIntent(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


# ---------------------------------------------------------------------------
# Reference data — small, static, explicitly configurable lookup tables.
# Adjust/extend these tables to change classification behavior; no logic
# branches need to change.
# ---------------------------------------------------------------------------

# Canonical MarketProfile.primary_category (from market_research_analyst.py's
# CATEGORY_KEYWORDS) -> broader industry bucket.
CATEGORY_TO_INDUSTRY: dict = {
    "Martial Arts": "Sports & Recreation",
    "Yoga": "Health & Wellness",
    "Dog Grooming": "Pet Services",
    "Dog Walking": "Pet Services",
    "Beef": "Food & Agriculture",
    "Landscaping": "Home Services",
    "HVAC": "Home Services",
    "Plumbing": "Home Services",
    "Roofing": "Home Services",
    "Auto Repair": "Automotive",
    "Tutoring": "Education",
}

# Industry -> default commercial intent. A documented business
# heuristic (not AI-derived): recurring/urgent local services default
# higher, commodity/wholesale goods default lower. Easily adjustable.
INDUSTRY_COMMERCIAL_INTENT: dict = {
    "Sports & Recreation": CommercialIntent.HIGH,
    "Home Services": CommercialIntent.HIGH,
    "Pet Services": CommercialIntent.MEDIUM,
    "Automotive": CommercialIntent.MEDIUM,
    "Education": CommercialIntent.MEDIUM,
    "Health & Wellness": CommercialIntent.MEDIUM,
    "Food & Agriculture": CommercialIntent.LOW,
}

# Canonical audience name -> keyword patterns matched as a
# case-insensitive substring against the opportunity's text.
AUDIENCE_KEYWORDS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("Children", ("for kids", "kids", "children", "youth")),
    ("Seniors", ("senior", "elderly", "retirement")),
    ("Adults", ("adult",)),
    ("Pet Owners", ("dog", "pet", "cat")),
)

# Atlas's own core business thesis is directory-style businesses
# (see ATLAS.md) — any opportunity with a recognized category is, by
# default, evaluated as a Directory business_type candidate. An
# opportunity with no recognized category has nothing to classify.
DEFAULT_RECOGNIZED_BUSINESS_TYPE = "Directory"


def _classify_industry(primary_category: str) -> str:
    return CATEGORY_TO_INDUSTRY.get(primary_category, "UNKNOWN")


def _classify_commercial_intent(industry: str) -> CommercialIntent:
    return INDUSTRY_COMMERCIAL_INTENT.get(industry, CommercialIntent.UNKNOWN)


def _classify_audience(text: str) -> str:
    lowered = text.lower()
    for canonical_name, patterns in AUDIENCE_KEYWORDS:
        for pattern in patterns:
            if pattern in lowered:
                return canonical_name
    return "UNKNOWN"


def _classify_business_type(primary_category: str) -> str:
    if primary_category == "UNKNOWN":
        return "UNKNOWN"
    return DEFAULT_RECOGNIZED_BUSINESS_TYPE


class OpportunityClassifier:
    """
    Pure, deterministic, offline Opportunity Classification stage.
    Satisfies OpportunityClassificationStageProtocol structurally
    (run(Opportunity, MarketProfile) -> OpportunityClassification) —
    no inheritance required. No global state, no singletons: every
    instance is independent and stateless.
    """

    def run(self, opportunity: Opportunity, market_profile: MarketProfile) -> OpportunityClassification:
        text = f"{opportunity.name} {opportunity.niche}"

        industry = _classify_industry(market_profile.primary_category)
        audience = _classify_audience(text)
        business_type = _classify_business_type(market_profile.primary_category)
        commercial_intent = _classify_commercial_intent(industry)
        market_vertical = market_profile.primary_category
        business_model = "UNKNOWN"

        confidence = "ESTIMATED" if (industry != "UNKNOWN" or audience != "UNKNOWN") else "UNKNOWN"

        return OpportunityClassification(
            industry=industry,
            audience=audience,
            business_type=business_type,
            commercial_intent=commercial_intent.value,
            market_vertical=market_vertical,
            business_model=business_model,
            confidence=confidence,
        )
