"""
atlas/services/opportunity_intelligence/competition_analyst.py

AES-012D — Competition Analyst Foundation.

Derives a structured CompetitionProfile from the already-derived
MarketProfile (AES-012B) and OpportunityClassification (AES-012C)
structured outputs. No AI, no LLM calls, no web scraping, no external
APIs, no network access of any kind. Purely offline, deterministic
lookup against a small, explicit, configurable table.

Honesty rule (same convention as market_research_analyst.py and
opportunity_classifier.py): a fact is only reported when a genuine
deterministic signal was found. Does not re-parse raw opportunity
text or duplicate category/geography logic — consumes
MarketProfile.market_scope and OpportunityClassification.business_type
directly. Every field defaults to "UNKNOWN"; nothing here is
fabricated when this analyst has no real signal to work from.

SCOPE_COMPETITION_PROFILE intentionally covers only STATE and
NATIONAL market_scope values — the two scopes evidenced by the
ticket's worked examples. CITY and REGIONAL are not yet represented by
any worked example, so they honestly fall through to an
all-"UNKNOWN" CompetitionProfile rather than being extrapolated.

Independent package: no Flask, no repositories, no persistence, no
services.opportunity_v2, no orchestrator, no Learning Memory, no
network I/O of any kind.
"""

from __future__ import annotations

from services.opportunity_intelligence.models import (
    CompetitionProfile,
    MarketProfile,
    Opportunity,
    OpportunityClassification,
)

# Reference data — a small, static, explicitly configurable lookup
# table. Keyed by MarketProfile.market_scope. Adjust/extend this table
# to change competition-characterization behavior; no logic branches
# need to change.
SCOPE_COMPETITION_PROFILE: dict = {
    "STATE": {
        "competitor_archetype": "fragmented_local_providers",
        "market_fragmentation": "HIGH",
        "likely_competitor_type": "local_businesses_and_small_directories",
        "competitive_risk": "MODERATE",
    },
    "NATIONAL": {
        "competitor_archetype": "national_platforms",
        "market_fragmentation": "MODERATE",
        "likely_competitor_type": "large_directories_and_marketplaces",
        "competitive_risk": "HIGH",
    },
}


class CompetitionAnalyst:
    """
    Pure, deterministic, offline Competition Analysis stage. Satisfies
    services.opportunity_intelligence.stages.CompetitionAnalysisStageProtocol
    structurally (run(Opportunity, MarketProfile,
    OpportunityClassification) -> CompetitionProfile) — no inheritance
    required. No global state, no singletons: every instance is
    independent and stateless.
    """

    def run(
        self,
        opportunity: Opportunity,
        market_profile: MarketProfile,
        classification: OpportunityClassification,
    ) -> CompetitionProfile:
        scope_data = SCOPE_COMPETITION_PROFILE.get(market_profile.market_scope)

        if scope_data is None or classification.business_type == "UNKNOWN":
            return CompetitionProfile()

        return CompetitionProfile(
            competitor_archetype=scope_data["competitor_archetype"],
            market_fragmentation=scope_data["market_fragmentation"],
            likely_competitor_type=scope_data["likely_competitor_type"],
            competitive_risk=scope_data["competitive_risk"],
            competition_scope=market_profile.market_scope,
            data_confidence="ESTIMATED",
        )
