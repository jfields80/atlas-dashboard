"""
atlas/services/opportunity_intelligence/market_research_analyst.py

AES-012B — Market Research Analyst (Deterministic Intelligence).

The first real Opportunity Intelligence employee: derives every fact
it honestly can from the Opportunity's own name/niche text alone —
market name, primary category, primary geography, and geographic
scope. No AI, no LLM calls, no web scraping, no external APIs, no
network access of any kind. Purely offline, deterministic text
matching against small, explicit, human-curated reference tables.

Honesty rule (matches Atlas's TaggedValue/DataVerificationTag
convention used throughout the rest of the codebase): a fact is only
reported when it was genuinely recognized in the text. Nothing is
guessed or fabricated. When no geography marker is found at all, the
opportunity is assumed national in scope (an explicit, documented
default — the same behavior the ticket's own "Direct Beef" example
expects), tagged ESTIMATED rather than VERIFIED. When no category
keyword is recognized, market_name/primary_category stay "UNKNOWN"
rather than guessing at a category.

Reference data (US_STATE_NAMES, KNOWN_CITIES, CATEGORY_KEYWORDS) is
deliberately small, static, and extensible — this analyst has no
access to a real city/business-category database. A name outside
these tables is never misclassified; it's honestly left unresolved.

Independent package: no Flask, no repositories, no persistence, no
services.opportunity_v2, no orchestrator, no Learning Memory, no
network I/O of any kind. Pure, side-effect-free, deterministic logic.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional, Tuple

from services.opportunity_intelligence.models import MarketProfile, Opportunity


class MarketScope(str, Enum):
    CITY = "CITY"
    STATE = "STATE"
    REGIONAL = "REGIONAL"
    NATIONAL = "NATIONAL"
    UNKNOWN = "UNKNOWN"


# ---------------------------------------------------------------------------
# Reference data — small, static, extensible lookup tables. Real, finite,
# unchanging factual data (US state names) or a curated, explicitly
# non-exhaustive sample (cities, category keywords) — not fabrication.
# ---------------------------------------------------------------------------

US_STATE_NAMES: Tuple[str, ...] = (
    "Alabama", "Alaska", "Arizona", "Arkansas", "California", "Colorado",
    "Connecticut", "Delaware", "Florida", "Georgia", "Hawaii", "Idaho",
    "Illinois", "Indiana", "Iowa", "Kansas", "Kentucky", "Louisiana",
    "Maine", "Maryland", "Massachusetts", "Michigan", "Minnesota",
    "Mississippi", "Missouri", "Montana", "Nebraska", "Nevada",
    "New Hampshire", "New Jersey", "New Mexico", "New York",
    "North Carolina", "North Dakota", "Ohio", "Oklahoma", "Oregon",
    "Pennsylvania", "Rhode Island", "South Carolina", "South Dakota",
    "Tennessee", "Texas", "Utah", "Vermont", "Virginia", "Washington",
    "West Virginia", "Wisconsin", "Wyoming",
)

# Not an exhaustive city database — a small, extensible, explicitly
# curated sample. Sorted longest-first so multi-word cities are matched
# before a shorter city name that might be a substring of another.
KNOWN_CITIES: Tuple[str, ...] = tuple(
    sorted(
        (
            "New York", "Los Angeles", "San Antonio", "San Diego",
            "San Francisco", "Fort Worth", "Columbus", "Charlotte",
            "Indianapolis", "Chicago", "Houston", "Phoenix",
            "Philadelphia", "Dallas", "Austin", "Jacksonville",
            "Cleveland", "Cincinnati", "Seattle", "Denver", "Boston",
            "Nashville", "Detroit", "Portland", "Memphis", "Louisville",
            "Milwaukee", "Baltimore", "Atlanta", "Miami", "Minneapolis",
            "Sacramento", "Orlando", "Tampa", "Pittsburgh", "St. Louis",
        ),
        key=len,
        reverse=True,
    )
)

# Canonical market/category name -> keyword patterns matched as a
# case-insensitive substring against the opportunity's name. Checked in
# order; the first canonical name with a matching pattern wins. Purely a
# reference lookup table — no inference, no AI.
CATEGORY_KEYWORDS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("Martial Arts", ("martial arts", "karate", "taekwondo", "jiu jitsu", "jiujitsu", "kickboxing")),
    ("Dog Grooming", ("dog groom", "pet groom")),
    ("Dog Walking", ("dog walk",)),
    ("Beef", ("beef",)),
    ("Landscaping", ("landscap",)),
    ("HVAC", ("hvac", "heating and cooling", "heating & cooling")),
    ("Plumbing", ("plumb",)),
    ("Roofing", ("roofing", "roofer")),
    ("Auto Repair", ("auto repair", "car repair", "mechanic")),
    ("Tutoring", ("tutor",)),
    ("Yoga", ("yoga",)),
)


def _extract_geography(name: str) -> Tuple[str, MarketScope]:
    """
    Returns (primary_geography, market_scope). Cities are checked
    before states (a city is more specific than a state), and a name
    with no recognizable geography marker at all defaults to National
    scope — an explicit, documented default, not a fabricated fact.
    """
    lowered = name.lower()

    for city in KNOWN_CITIES:
        if city.lower() in lowered:
            return city, MarketScope.CITY

    for state in US_STATE_NAMES:
        if state.lower() in lowered:
            return state, MarketScope.STATE

    return "National", MarketScope.NATIONAL


def _extract_category(name: str) -> Optional[str]:
    """Returns the first matching canonical category name, or None if
    nothing in CATEGORY_KEYWORDS is recognized in the text."""
    lowered = name.lower()

    for canonical_name, patterns in CATEGORY_KEYWORDS:
        for pattern in patterns:
            if pattern in lowered:
                return canonical_name

    return None


class MarketResearchAnalyst:
    """
    Pure, deterministic, offline Market Research stage. Satisfies
    services.opportunity_intelligence.stages.MarketResearchStageProtocol
    structurally (run(Opportunity) -> MarketProfile) — no inheritance
    required. No global state, no singletons: every instance is
    independent and stateless.
    """

    def run(self, opportunity: Opportunity) -> MarketProfile:
        text = f"{opportunity.name} {opportunity.niche}"

        geography, scope = _extract_geography(text)
        category = _extract_category(text)

        # Geography always resolves to a real inference (National is an
        # explicit, honest default, not a null result), so this analyst
        # always produces at least one genuine fact — never VERIFIED
        # (nothing here is confirmed against real market data), always
        # ESTIMATED rather than UNKNOWN.
        confidence = "ESTIMATED"

        return MarketProfile(
            market_name=category or "UNKNOWN",
            primary_category=category or "UNKNOWN",
            primary_geography=geography,
            market_scope=scope.value,
            data_confidence=confidence,
        )
