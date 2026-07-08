"""
opportunity_scorer.py — Deterministic Opportunity Scoring Service.

Produces seven named scores (0-100 each) for any opportunity niche,
then synthesises them into an overall Opportunity Score. All scores
are fed into the existing ctx dict consumed by ValuationEngine and
BusinessArchitect, so two opportunities within the same DNA profile
receive different valuations without touching any other file.

Architecture:
    Pure service module. No Flask, no SQL, no routes.
    Input:  niche_name (str), dna (OpportunityDNA), seed_ctx (dict)
    Output: enriched ctx dict + OpportunityScoreResult (attached as
            ctx["opportunity_score_result"] for templates if needed)

Seven component scores:

    1. search_demand_score        (0-100)
       How much monthly search interest the niche likely has.
       Driven by: niche specificity (word count, depth), DNA local/commercial
       intent intensity, and whether the niche contains demand signals.

    2. commercial_intent_score    (0-100)
       Probability that searchers want to spend money.
       Driven by: DNA commercial_intent + lead_value + recurring_revenue
       + presence of transactional intent signals in the niche name.

    3. competition_score          (0-100, HIGHER = MORE competitive)
       How hard it is to rank and capture the niche.
       Driven by: niche breadth (fewer words = broader = more contested),
       presence of national brand signals, depth in the drill tree.
       NOTE: this feeds valuation as competition_score (high = bad).

    4. business_supply_score      (0-100)
       How many real businesses exist to populate the directory.
       Driven by: DNA ecosystem supply_intensity for matching nodes,
       niche specificity (broader = more supply), business_count if
       already verified in ctx.

    5. seo_difficulty_score       (0-100, HIGHER = HARDER)
       How difficult organic ranking will be.
       Derived from: competition_score (primary) + whether the niche
       contains keywords dominated by aggregators/platforms + DNA
       review_importance (high review weight = Yelp-dominated SERP).
       NOTE: feeds directory_weakness_score inversely (high SEO
       difficulty = stronger incumbents = lower weakness score).

    6. monetization_potential_score  (0-100)
       How much revenue the niche can support across all streams.
       Driven by: DNA stream count + stream strength distribution +
       lead_value + recurring_revenue_potential + asset fit weight
       for the best-matching asset type.

    7. automation_fit_score       (0-100)
       How much of the build Atlas can automate.
       Driven by: number of DNA search_dimensions (more structured =
       more automatable) + asset_type (geo/directory = high automation)
       + DNA regulation flag (regulated = more manual review needed).

Overall Opportunity Score:
    Weighted sum of the above. Weights are named constants.
    competition and seo_difficulty contribute negatively (higher = worse).

Determinism guarantee:
    All inputs are the niche name string + DNA object + optional verified
    business_count. Same inputs always produce the same outputs.
    No random numbers. No external calls. No LLM.

Integration:
    In the route, after building the raw ctx and before calling
    arch.generate_decision(), call:

        from services.opportunity_v2.opportunity_scorer import score_opportunity
        ctx = score_opportunity(node.niche_name, dna, ctx)

    That replaces ctx["competition_score"], ctx["search_demand_score"],
    ctx["directory_weakness_score"], ctx["automation_fit_score"],
    and ctx["business_count"] with scored values, while preserving
    everything else (asset_type, data_quality, blueprint_total_pages,
    revenue_low/high from brief, ecosystem_node_name).
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Optional

from .dna.schema import OpportunityDNA, Intensity


# ─────────────────────────────────────────────────────────────────────────────
# Named constants
# ─────────────────────────────────────────────────────────────────────────────

# Overall Opportunity Score weights. Sum = 1.0.
# Positive contributors:
_W_SEARCH_DEMAND   = 0.20   # is there traffic to capture?
_W_COMMERCIAL      = 0.20   # will visitors spend money?
_W_BUSINESS_SUPPLY = 0.15   # is there enough content to build with?
_W_MONETIZATION    = 0.25   # can it make money? (highest weight)
_W_AUTOMATION      = 0.10   # can Atlas build it efficiently?
# Negative contributors (subtracted, scaled to their weight):
_W_COMPETITION     = 0.05   # competition penalty (mild — niche = less contested)
_W_SEO_DIFFICULTY  = 0.05   # SEO difficulty penalty

# ── Market-Capacity-aware weight set ────────────────────────────────────────
# Used ONLY when a MarketCapacityResult is supplied to score(). Rebalances
# the weights above to make room for a market_capacity component so the
# scorer also asks "is this market big enough?" alongside "can we build it?"
# When market_capacity is None, the ORIGINAL weights above apply unchanged —
# this block does not alter default scorer behavior.
_W_SEARCH_DEMAND_MC   = 0.16
_W_COMMERCIAL_MC      = 0.16
_W_BUSINESS_SUPPLY_MC = 0.12
_W_MONETIZATION_MC    = 0.20
_W_AUTOMATION_MC      = 0.08
_W_MARKET_CAPACITY_MC = 0.20   # new: is the market large enough to matter?
_W_COMPETITION_MC     = 0.04
_W_SEO_DIFFICULTY_MC  = 0.04

# Intensity -> numeric score (0-100), used to convert DNA enum values
_INTENSITY_SCORE = {
    Intensity.EXTREME:   98,
    Intensity.VERY_HIGH: 85,
    Intensity.HIGH:      68,
    Intensity.MEDIUM:    50,
    Intensity.LOW:       30,
    Intensity.VERY_LOW:  12,
}
_INTENSITY_SCORE_DEFAULT = 50


def _int_score(intensity: Optional[Intensity]) -> float:
    if intensity is None:
        return _INTENSITY_SCORE_DEFAULT
    return float(_INTENSITY_SCORE.get(intensity, _INTENSITY_SCORE_DEFAULT))


# ── Search demand scoring ─────────────────────────────────────────────────────

# Every extra word beyond the first two signals more specificity and therefore
# lower raw search volume. Penalty per additional word after word 2.
_DEMAND_WORD_PENALTY      = 7.0
_DEMAND_BASE              = 85.0
_DEMAND_WORD_PENALTY_FLOOR = 20.0  # never penalise below this floor

# Niche substrings that signal locally-bounded, high-intent searches.
# These lift demand because they target real transactional queries.
_DEMAND_BOOST_SIGNALS = [
    "near", "in ", " ohio", " columbus", "best ", "top ",
    "affordable", "local", "nearby", "open late", "open now",
]
_DEMAND_BOOST_PER_SIGNAL = 4.0
_DEMAND_BOOST_MAX        = 15.0

# DNA commercial_intent weight in demand calculation.
# High commercial intent → people searching to buy → real demand.
_DEMAND_COMMERCIAL_WEIGHT = 0.30   # 30% of score from DNA commercial intent
_DEMAND_NICHE_WEIGHT      = 0.70   # 70% from niche text analysis


# ── Commercial intent scoring ─────────────────────────────────────────────────

# Niche name keywords that signal transactional intent.
_COMMERCIAL_TRANSACTIONAL_SIGNALS = [
    "best", "top", "buy", "hire", "book", "reserve", "order",
    "find", "near me", "cost", "price", "affordable", "cheap",
    "services", "for hire", "professionals",
]
_COMMERCIAL_BOOST_PER_SIGNAL = 5.0
_COMMERCIAL_BOOST_MAX        = 20.0

# DNA weights in commercial intent
_COMMERCIAL_INTENT_DNA_WEIGHT    = 0.50
_COMMERCIAL_LEAD_VALUE_WEIGHT    = 0.30
_COMMERCIAL_RECURRING_WEIGHT     = 0.20


# ── Competition scoring ───────────────────────────────────────────────────────
# Competition: HIGHER = MORE competitive. 100 = very hard to penetrate.
# Broad niches (few words) are dominated by aggregators → high competition.

_COMPETITION_BREADTH_BASE     = 80.0   # starting point for a 1-word niche
_COMPETITION_PER_WORD_RELIEF  = 8.0    # each extra word → less competition
_COMPETITION_FLOOR            = 10.0
_COMPETITION_AGGREGATOR_BOOST = 15.0   # penalty when aggregator signals present

# Keywords that suggest Yelp/Google/TripAdvisor dominate the SERP
_AGGREGATOR_DOMINATED_SIGNALS = [
    "restaurant", "hotel", "plumber", "dentist", "doctor",
    "lawyer", "attorney", "realtor", "contractor", "gym",
]

# Depth relief: a node found deep in the drill tree is specific → less competition.
# drill depth 0 = no relief; depth 3 = 24 points of relief.
_COMPETITION_DEPTH_RELIEF_PER_LEVEL = 8.0
_COMPETITION_DEPTH_RELIEF_MAX       = 32.0


# ── Business supply scoring ───────────────────────────────────────────────────

# Verified business count takes full precedence when available.
_SUPPLY_COUNT_THRESHOLDS = [
    (500, 100), (200, 90), (100, 80), (50, 65),
    (25, 48),   (10, 30),  (1, 15),   (0, 0),
]
# When no verified count is available, infer from DNA supply_intensity
# of the best-matching ecosystem node. This produces different scores
# for "pet-friendly hotels" vs "dog beaches" because the DNA nodes differ.
_SUPPLY_DNA_WEIGHT = 1.0   # use DNA supply directly when no verified count


# ── SEO difficulty ────────────────────────────────────────────────────────────
# High SEO difficulty means incumbents are strong → directory_weakness is LOW.
# directory_weakness = 100 - seo_difficulty (inverted before feeding valuation).

_SEO_BASE_FROM_COMPETITION  = 0.70   # 70% weight from competition score
_SEO_REVIEW_WEIGHT          = 0.20   # high review importance → Yelp-heavy SERP
_SEO_PLATFORM_WEIGHT        = 0.10   # DNA commercial_intent at extreme → platform risk

_SEO_REVIEW_MULTIPLIER      = 0.25   # how much review_importance shifts SEO difficulty


# ── Monetization potential ────────────────────────────────────────────────────

_MON_STREAM_STRENGTH_WEIGHTS = {
    "extreme":   1.00,
    "very_high": 0.85,
    "high":      0.65,
    "medium":    0.45,
    "low":       0.20,
    "very_low":  0.08,
    "unknown":   0.35,
}
_MON_MAX_STREAM_POINTS = 20.0   # max per-stream contribution (5 streams × 20 = 100)
_MON_STREAM_CAP        = 5      # streams beyond 5 don't add more

# Asset fit bonus: best asset_preference weight in this DNA normalised to 0-20
_MON_ASSET_FIT_SCALE   = 20.0   # 100/100 asset fit = +20 pts


# ── Automation fit ────────────────────────────────────────────────────────────

_AUTO_BASE = 75.0
# Structured markets (many DNA search_dimensions) are more automatable
_AUTO_DIMENSION_BONUS_PER_DIM = 2.0
_AUTO_DIMENSION_BONUS_MAX     = 15.0
# Regulated markets need manual review
_AUTO_REGULATED_PENALTY       = 20.0
# Simple asset types (geo_category, directory) automate better
_AUTO_ASSET_BONUS = {
    "directory":    5.0,
    "geo_category": 8.0,
    "category":     3.0,
    "filter":       2.0,
    "seo_page":     0.0,
    "article":     -5.0,
    "lead_gen":    -8.0,
    "marketplace": -10.0,
}


# ─────────────────────────────────────────────────────────────────────────────
# Score result dataclass — full audit trail
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ScoreComponent:
    """One labelled input that contributed to a score."""
    label: str
    value: float
    weight: float
    contribution: float
    rationale: str


@dataclass
class ComponentScore:
    """A single scored dimension with its full calculation trail."""
    name: str
    score: float                                 # 0-100
    components: list[ScoreComponent] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class OpportunityScoreResult:
    """Complete scoring output. Attached to ctx so templates can render it."""

    niche_name: str
    dna_slug: str

    # Seven component scores
    search_demand:        ComponentScore
    commercial_intent:    ComponentScore
    competition:          ComponentScore   # higher = MORE competitive (bad)
    business_supply:      ComponentScore
    seo_difficulty:       ComponentScore   # higher = HARDER to rank (bad)
    monetization:         ComponentScore
    automation_fit:       ComponentScore

    # Overall weighted composite
    overall_score: float
    overall_formula: str
    overall_components: list[ScoreComponent] = field(default_factory=list)

    # What these scores mean for the valuation engine inputs
    ctx_mapping: dict = field(default_factory=dict)

    # Market Capacity integration (optional — None when no MarketCapacityResult
    # was supplied to score()/score_opportunity(); backward compatible).
    market_capacity_score: Optional[float] = None
    market_capacity_component: Optional["ScoreComponent"] = None


# ─────────────────────────────────────────────────────────────────────────────
# Scorer
# ─────────────────────────────────────────────────────────────────────────────

class OpportunityScorer:
    """Stateless. Safe to instantiate once and reuse."""

    def score(self, niche_name: str, dna: OpportunityDNA,
               ctx: dict, market_capacity=None) -> OpportunityScoreResult:
        """
        Score a niche opportunity. Returns OpportunityScoreResult.
        All inputs deterministic — same arguments always produce same output.

        market_capacity: optional MarketCapacityResult (from
            services/opportunity_v2/market_capacity.py). When provided,
            the overall score also weighs "is this market large enough?"
            via market_capacity.market_capacity_score, using the rebalanced
            _*_MC weight set. When None (default), scoring behaves EXACTLY
            as before this parameter was added — fully backward compatible.
        """
        niche_lower   = niche_name.lower()
        word_count    = len(niche_name.split())
        drill_depth   = int(ctx.get("drill_depth", 0))
        asset_type    = ctx.get("asset_type", "directory")
        verified_count = ctx.get("business_count")   # may be None or 0

        demand     = self._score_search_demand(niche_lower, word_count, dna)
        commercial = self._score_commercial_intent(niche_lower, dna)
        competition = self._score_competition(niche_lower, word_count, drill_depth, dna)
        supply     = self._score_business_supply(niche_lower, dna, verified_count)
        seo_diff   = self._score_seo_difficulty(niche_lower, competition.score, dna)
        monetize   = self._score_monetization(asset_type, dna)
        automation = self._score_automation_fit(asset_type, dna)

        if market_capacity is not None:
            mc_score = float(market_capacity.market_capacity_score)
            overall = (
                demand.score          * _W_SEARCH_DEMAND_MC
                + commercial.score    * _W_COMMERCIAL_MC
                + supply.score        * _W_BUSINESS_SUPPLY_MC
                + monetize.score      * _W_MONETIZATION_MC
                + automation.score    * _W_AUTOMATION_MC
                + mc_score            * _W_MARKET_CAPACITY_MC
                - competition.score   * _W_COMPETITION_MC
                - seo_diff.score      * _W_SEO_DIFFICULTY_MC
            )
            overall = round(max(0.0, min(100.0, overall)), 1)
            formula = (
                f"({demand.score:.1f}×{_W_SEARCH_DEMAND_MC}"
                f" + {commercial.score:.1f}×{_W_COMMERCIAL_MC}"
                f" + {supply.score:.1f}×{_W_BUSINESS_SUPPLY_MC}"
                f" + {monetize.score:.1f}×{_W_MONETIZATION_MC}"
                f" + {automation.score:.1f}×{_W_AUTOMATION_MC}"
                f" + {mc_score:.1f}×{_W_MARKET_CAPACITY_MC}"
                f" − {competition.score:.1f}×{_W_COMPETITION_MC}"
                f" − {seo_diff.score:.1f}×{_W_SEO_DIFFICULTY_MC})"
                f" = {overall}"
            )
            mc_component = ScoreComponent(
                "Market capacity", mc_score, _W_MARKET_CAPACITY_MC,
                round(mc_score * _W_MARKET_CAPACITY_MC, 2),
                f"MarketCapacityResult.market_capacity_score = {mc_score:.1f} "
                f"(category: {getattr(market_capacity, 'business_category', 'n/a')})")
            overall_comps = [
                ScoreComponent("Search demand",    demand.score,     _W_SEARCH_DEMAND_MC,
                                round(demand.score * _W_SEARCH_DEMAND_MC, 2),    "+"),
                ScoreComponent("Commercial intent",commercial.score, _W_COMMERCIAL_MC,
                                round(commercial.score * _W_COMMERCIAL_MC, 2),   "+"),
                ScoreComponent("Business supply",  supply.score,     _W_BUSINESS_SUPPLY_MC,
                                round(supply.score * _W_BUSINESS_SUPPLY_MC, 2),  "+"),
                ScoreComponent("Monetization",     monetize.score,   _W_MONETIZATION_MC,
                                round(monetize.score * _W_MONETIZATION_MC, 2),   "+"),
                ScoreComponent("Automation fit",   automation.score, _W_AUTOMATION_MC,
                                round(automation.score * _W_AUTOMATION_MC, 2),   "+"),
                mc_component,
                ScoreComponent("Competition (−)",  competition.score,_W_COMPETITION_MC,
                                round(-competition.score * _W_COMPETITION_MC, 2),"−"),
                ScoreComponent("SEO difficulty (−)",seo_diff.score,  _W_SEO_DIFFICULTY_MC,
                                round(-seo_diff.score * _W_SEO_DIFFICULTY_MC, 2),"−"),
            ]
        else:
            # Positive contributors
            overall = (
                demand.score          * _W_SEARCH_DEMAND
                + commercial.score    * _W_COMMERCIAL
                + supply.score        * _W_BUSINESS_SUPPLY
                + monetize.score      * _W_MONETIZATION
                + automation.score    * _W_AUTOMATION
                # Negative contributors
                - competition.score   * _W_COMPETITION
                - seo_diff.score      * _W_SEO_DIFFICULTY
            )
            overall = round(max(0.0, min(100.0, overall)), 1)

            formula = (
                f"({demand.score:.1f}×{_W_SEARCH_DEMAND}"
                f" + {commercial.score:.1f}×{_W_COMMERCIAL}"
                f" + {supply.score:.1f}×{_W_BUSINESS_SUPPLY}"
                f" + {monetize.score:.1f}×{_W_MONETIZATION}"
                f" + {automation.score:.1f}×{_W_AUTOMATION}"
                f" − {competition.score:.1f}×{_W_COMPETITION}"
                f" − {seo_diff.score:.1f}×{_W_SEO_DIFFICULTY})"
                f" = {overall}"
            )

            mc_component = None
            overall_comps = [
                ScoreComponent("Search demand",    demand.score,     _W_SEARCH_DEMAND,
                                round(demand.score * _W_SEARCH_DEMAND, 2),    "+"),
                ScoreComponent("Commercial intent",commercial.score, _W_COMMERCIAL,
                                round(commercial.score * _W_COMMERCIAL, 2),   "+"),
                ScoreComponent("Business supply",  supply.score,     _W_BUSINESS_SUPPLY,
                                round(supply.score * _W_BUSINESS_SUPPLY, 2),  "+"),
                ScoreComponent("Monetization",     monetize.score,   _W_MONETIZATION,
                                round(monetize.score * _W_MONETIZATION, 2),   "+"),
                ScoreComponent("Automation fit",   automation.score, _W_AUTOMATION,
                                round(automation.score * _W_AUTOMATION, 2),   "+"),
                ScoreComponent("Competition (−)",  competition.score,_W_COMPETITION,
                                round(-competition.score * _W_COMPETITION, 2),"−"),
                ScoreComponent("SEO difficulty (−)",seo_diff.score,  _W_SEO_DIFFICULTY,
                                round(-seo_diff.score * _W_SEO_DIFFICULTY, 2),"−"),
            ]

        # ctx_mapping shows exactly which valuation-engine keys each score populates
        directory_weakness = round(max(0.0, min(100.0, 100.0 - seo_diff.score)), 1)
        ctx_mapping = {
            "search_demand_score":      round(demand.score, 1),
            "competition_score":        round(competition.score, 1),
            "directory_weakness_score": directory_weakness,
            "automation_fit_score":     round(automation.score, 1),
            # business_count: only overwritten if no verified count was provided
        }

        return OpportunityScoreResult(
            niche_name=niche_name,
            dna_slug=dna.slug,
            search_demand=demand,
            commercial_intent=commercial,
            competition=competition,
            business_supply=supply,
            seo_difficulty=seo_diff,
            monetization=monetize,
            automation_fit=automation,
            overall_score=overall,
            overall_formula=formula,
            overall_components=overall_comps,
            ctx_mapping=ctx_mapping,
            market_capacity_score=(
                float(market_capacity.market_capacity_score)
                if market_capacity is not None else None),
            market_capacity_component=mc_component,
        )

    # ── Search demand ─────────────────────────────────────────────────────────

    def _score_search_demand(self, niche_lower: str, word_count: int,
                               dna: OpportunityDNA) -> ComponentScore:
        components: list[ScoreComponent] = []
        notes: list[str] = []

        # Niche-text component: more specific = lower raw volume
        extra_words = max(0, word_count - 2)
        penalty     = min(extra_words * _DEMAND_WORD_PENALTY,
                           _DEMAND_BASE - _DEMAND_WORD_PENALTY_FLOOR)
        niche_base  = _DEMAND_BASE - penalty

        # Boost for transactional demand signals in niche name
        signal_hits = sum(1 for s in _DEMAND_BOOST_SIGNALS if s in niche_lower)
        boost = min(signal_hits * _DEMAND_BOOST_PER_SIGNAL, _DEMAND_BOOST_MAX)
        niche_score = min(100.0, niche_base + boost)

        components.append(ScoreComponent(
            label="Niche specificity (word count)",
            value=niche_base,
            weight=_DEMAND_NICHE_WEIGHT,
            contribution=round(niche_base * _DEMAND_NICHE_WEIGHT, 2),
            rationale=(
                f"{word_count} words: base {_DEMAND_BASE:.0f} "
                f"− {extra_words}×{_DEMAND_WORD_PENALTY:.0f} penalty = {niche_base:.0f}; "
                f"+{boost:.0f} from {signal_hits} demand signal(s) → {niche_score:.0f}")))

        # DNA component: how commercially intense is this market?
        dna_demand = _int_score(dna.intent.commercial_intent if dna.intent else None)
        components.append(ScoreComponent(
            label="DNA commercial intent",
            value=dna_demand,
            weight=_DEMAND_COMMERCIAL_WEIGHT,
            contribution=round(dna_demand * _DEMAND_COMMERCIAL_WEIGHT, 2),
            rationale=(
                f"DNA intent.commercial_intent = "
                f"{dna.intent.commercial_intent.value if dna.intent else 'n/a'} "
                f"→ {dna_demand:.0f} pts")))

        score = round(
            niche_score  * _DEMAND_NICHE_WEIGHT
            + dna_demand * _DEMAND_COMMERCIAL_WEIGHT, 1)

        if boost > 0:
            notes.append(
                f"Demand boost +{boost:.0f} pts from {signal_hits} demand signal(s) "
                f"in niche name.")
        if extra_words > 2:
            notes.append(
                f"Long-tail niche ({word_count} words) — lower raw search volume "
                "but higher conversion when found.")

        return ComponentScore(name="search_demand", score=score,
                               components=components, notes=notes)

    # ── Commercial intent ─────────────────────────────────────────────────────

    def _score_commercial_intent(self, niche_lower: str,
                                   dna: OpportunityDNA) -> ComponentScore:
        components: list[ScoreComponent] = []
        notes: list[str] = []

        # Transactional signals in niche name
        hits  = sum(1 for s in _COMMERCIAL_TRANSACTIONAL_SIGNALS if s in niche_lower)
        boost = min(hits * _COMMERCIAL_BOOST_PER_SIGNAL, _COMMERCIAL_BOOST_MAX)

        # DNA: commercial_intent + lead_value + recurring_revenue
        ci  = _int_score(dna.intent.commercial_intent  if dna.intent    else None)
        lv  = _int_score(dna.commercial.lead_value      if dna.commercial else None)
        rec = _int_score(dna.commercial.recurring_revenue_potential if dna.commercial else None)

        dna_component = (
            ci  * _COMMERCIAL_INTENT_DNA_WEIGHT
            + lv  * _COMMERCIAL_LEAD_VALUE_WEIGHT
            + rec * _COMMERCIAL_RECURRING_WEIGHT)

        score = round(min(100.0, dna_component + boost), 1)

        components.append(ScoreComponent(
            label="DNA commercial intent",
            value=ci,
            weight=_COMMERCIAL_INTENT_DNA_WEIGHT,
            contribution=round(ci * _COMMERCIAL_INTENT_DNA_WEIGHT, 2),
            rationale=(
                f"intent.commercial_intent = "
                f"{dna.intent.commercial_intent.value if dna.intent else 'n/a'} "
                f"→ {ci:.0f}")))
        components.append(ScoreComponent(
            label="DNA lead value",
            value=lv,
            weight=_COMMERCIAL_LEAD_VALUE_WEIGHT,
            contribution=round(lv * _COMMERCIAL_LEAD_VALUE_WEIGHT, 2),
            rationale=(
                f"commercial.lead_value = "
                f"{dna.commercial.lead_value.value if dna.commercial else 'n/a'} "
                f"→ {lv:.0f}")))
        components.append(ScoreComponent(
            label="DNA recurring revenue",
            value=rec,
            weight=_COMMERCIAL_RECURRING_WEIGHT,
            contribution=round(rec * _COMMERCIAL_RECURRING_WEIGHT, 2),
            rationale=(
                f"commercial.recurring_revenue_potential = "
                f"{dna.commercial.recurring_revenue_potential.value if dna.commercial else 'n/a'} "
                f"→ {rec:.0f}")))
        if boost > 0:
            components.append(ScoreComponent(
                label=f"Transactional signals in niche name ({hits} found)",
                value=boost,
                weight=1.0,
                contribution=round(boost, 2),
                rationale=f"{hits} signal(s) × {_COMMERCIAL_BOOST_PER_SIGNAL} pts "
                           f"= +{boost:.0f} (cap {_COMMERCIAL_BOOST_MAX})"))
            notes.append(
                f"Niche name contains {hits} transactional signal(s) — "
                "buyer intent is explicit in the search phrase.")

        return ComponentScore(name="commercial_intent", score=score,
                               components=components, notes=notes)

    # ── Competition ───────────────────────────────────────────────────────────

    def _score_competition(self, niche_lower: str, word_count: int,
                             drill_depth: int, dna: OpportunityDNA) -> ComponentScore:
        components: list[ScoreComponent] = []
        notes: list[str] = []

        # Breadth: shorter niches are more contested
        breadth_competition = max(
            _COMPETITION_FLOOR,
            _COMPETITION_BREADTH_BASE - (word_count - 1) * _COMPETITION_PER_WORD_RELIEF)

        components.append(ScoreComponent(
            label="Niche breadth (word count)",
            value=breadth_competition,
            weight=1.0,
            contribution=breadth_competition,
            rationale=(
                f"{word_count} words: {_COMPETITION_BREADTH_BASE:.0f} "
                f"− {word_count-1}×{_COMPETITION_PER_WORD_RELIEF:.0f} "
                f"= {breadth_competition:.0f} (floor {_COMPETITION_FLOOR:.0f})")))

        # Aggregator signal: some categories are SERP-dominated by Yelp/Google
        agg_hits = sum(1 for s in _AGGREGATOR_DOMINATED_SIGNALS if s in niche_lower)
        agg_penalty = _COMPETITION_AGGREGATOR_BOOST if agg_hits else 0.0
        if agg_penalty:
            components.append(ScoreComponent(
                label=f"Aggregator-dominated category ({agg_hits} signal(s))",
                value=agg_penalty,
                weight=1.0,
                contribution=agg_penalty,
                rationale=(
                    f"Niche contains '{', '.join(s for s in _AGGREGATOR_DOMINATED_SIGNALS if s in niche_lower)}' "
                    f"— Yelp/Google Maps likely dominates SERP: +{agg_penalty:.0f}")))
            notes.append(
                "Aggregator-dominated category detected. Yelp, Google Maps, or "
                "TripAdvisor likely hold the top SERP positions.")

        # Depth relief: deeper drill = more specific = less competition
        depth_relief = min(drill_depth * _COMPETITION_DEPTH_RELIEF_PER_LEVEL,
                            _COMPETITION_DEPTH_RELIEF_MAX)
        if depth_relief > 0:
            components.append(ScoreComponent(
                label=f"Drill depth relief (depth {drill_depth})",
                value=-depth_relief,
                weight=1.0,
                contribution=-depth_relief,
                rationale=(
                    f"depth {drill_depth} × {_COMPETITION_DEPTH_RELIEF_PER_LEVEL:.0f} "
                    f"= −{depth_relief:.0f} pts (niche is specific)")))

        raw = min(100.0, max(_COMPETITION_FLOOR,
                              breadth_competition + agg_penalty - depth_relief))
        score = round(raw, 1)

        return ComponentScore(name="competition", score=score,
                               components=components, notes=notes)

    # ── Business supply ───────────────────────────────────────────────────────

    def _score_business_supply(self, niche_lower: str, dna: OpportunityDNA,
                                 verified_count: Optional[int]) -> ComponentScore:
        components: list[ScoreComponent] = []
        notes: list[str] = []

        if verified_count is not None and verified_count > 0:
            # Verified count takes full precedence
            for threshold, pts in _SUPPLY_COUNT_THRESHOLDS:
                if verified_count >= threshold:
                    score = float(pts)
                    break
            else:
                score = 0.0
            components.append(ScoreComponent(
                label=f"Verified business count: {verified_count}",
                value=verified_count,
                weight=1.0,
                contribution=score,
                rationale=(
                    f"{verified_count} verified businesses → "
                    f"{score:.0f} pts (threshold table)")))
            notes.append(
                f"Verified count used: {verified_count} businesses. "
                "Run Scout to refresh if market has changed.")
        else:
            # No verified count — infer from DNA ecosystem nodes
            # Find nodes whose name overlaps with the niche
            best_node = None
            best_match = 0
            for node in dna.ecosystem_nodes:
                words = set(node.name.lower().split())
                overlap = sum(1 for w in words if w in niche_lower and len(w) > 3)
                if overlap > best_match:
                    best_match, best_node = overlap, node

            if best_node:
                dna_supply = _int_score(best_node.supply_intensity)
                score = round(dna_supply * _SUPPLY_DNA_WEIGHT, 1)
                components.append(ScoreComponent(
                    label=(
                        f"DNA ecosystem node '{best_node.name}' "
                        f"supply_intensity={best_node.supply_intensity.value}"),
                    value=dna_supply,
                    weight=_SUPPLY_DNA_WEIGHT,
                    contribution=score,
                    rationale=(
                        f"Best-matching ecosystem node: '{best_node.name}' "
                        f"(role: {best_node.role}) → {dna_supply:.0f} pts")))
                notes.append(
                    f"No verified business count. Inferred from DNA node "
                    f"'{best_node.name}' (supply_intensity: "
                    f"{best_node.supply_intensity.value}). "
                    "Run Scout to verify actual count.")
            else:
                # No matching node — use DNA-level default
                score = 50.0
                components.append(ScoreComponent(
                    label="No matching ecosystem node — using neutral default",
                    value=50.0,
                    weight=1.0,
                    contribution=50.0,
                    rationale="No DNA ecosystem node matched niche keywords. Neutral 50 applied."))
                notes.append(
                    "Could not match niche to a DNA ecosystem node. "
                    "Business supply is uncertain — Scout verification strongly recommended.")

        return ComponentScore(name="business_supply",
                               score=round(min(100.0, max(0.0, score)), 1),
                               components=components, notes=notes)

    # ── SEO difficulty ────────────────────────────────────────────────────────

    def _score_seo_difficulty(self, niche_lower: str, competition_score: float,
                                dna: OpportunityDNA) -> ComponentScore:
        """
        SEO difficulty: how hard is it to rank organically?
        Directory weakness = 100 - seo_difficulty.
        High review_importance → Yelp dominates → hard to displace.
        """
        components: list[ScoreComponent] = []
        notes: list[str] = []

        # Primary: competition score already captures most of this
        comp_contribution = round(competition_score * _SEO_BASE_FROM_COMPETITION, 2)
        components.append(ScoreComponent(
            label="Competition score (primary SEO proxy)",
            value=competition_score,
            weight=_SEO_BASE_FROM_COMPETITION,
            contribution=comp_contribution,
            rationale=(
                f"{competition_score:.1f} × {_SEO_BASE_FROM_COMPETITION} "
                f"= {comp_contribution:.1f}")))

        # Review importance: high review weight = review platforms dominate
        rev = _int_score(dna.intent.review_importance if dna.intent else None)
        rev_contribution = round(rev * _SEO_REVIEW_WEIGHT * _SEO_REVIEW_MULTIPLIER, 2)
        components.append(ScoreComponent(
            label="Review platform dominance",
            value=rev,
            weight=_SEO_REVIEW_WEIGHT,
            contribution=rev_contribution,
            rationale=(
                f"DNA review_importance = "
                f"{dna.intent.review_importance.value if dna.intent else 'n/a'} "
                f"→ {rev:.0f} × {_SEO_REVIEW_WEIGHT} × {_SEO_REVIEW_MULTIPLIER} "
                f"= {rev_contribution:.1f}")))

        # Platform risk at extreme commercial intent (think Google Hotels)
        ci = _int_score(dna.intent.commercial_intent if dna.intent else None)
        plat_contribution = round(ci * _SEO_PLATFORM_WEIGHT * 0.15, 2)
        components.append(ScoreComponent(
            label="Platform encroachment risk",
            value=ci,
            weight=_SEO_PLATFORM_WEIGHT,
            contribution=plat_contribution,
            rationale=(
                f"DNA commercial_intent {ci:.0f} × {_SEO_PLATFORM_WEIGHT} × 0.15 "
                f"= {plat_contribution:.1f} "
                "(high commercial intent attracts Google's own products)")))

        score = round(min(100.0, max(0.0,
                           comp_contribution + rev_contribution + plat_contribution)), 1)

        if rev >= 70:
            notes.append(
                "High review_importance — review platforms (Yelp, TripAdvisor, "
                "Google Maps) likely hold several top SERP positions. "
                "Target informational and geo-specific queries to find gaps.")

        return ComponentScore(name="seo_difficulty", score=score,
                               components=components, notes=notes)

    # ── Monetization potential ────────────────────────────────────────────────

    def _score_monetization(self, asset_type: str,
                              dna: OpportunityDNA) -> ComponentScore:
        components: list[ScoreComponent] = []
        notes: list[str] = []

        if not dna.commercial or not dna.commercial.streams:
            return ComponentScore(
                name="monetization",
                score=20.0,
                components=[ScoreComponent(
                    "No DNA streams declared", 20.0, 1.0, 20.0,
                    "No commercial DNA streams — minimal monetization assumed.")],
                notes=["No commercial streams in DNA. Monetization is uncertain."])

        # Each stream contributes proportionally to its strength
        stream_pts = 0.0
        stream_comps: list[ScoreComponent] = []
        for s in dna.commercial.streams[:_MON_STREAM_CAP]:
            str_weight = _MON_STREAM_STRENGTH_WEIGHTS.get(s.strength.value, 0.35)
            pts = str_weight * _MON_MAX_STREAM_POINTS
            stream_pts += pts
            stream_comps.append(ScoreComponent(
                label=f"Stream: {s.stream}",
                value=pts,
                weight=str_weight,
                contribution=round(pts, 2),
                rationale=(
                    f"{s.stream} strength={s.strength.value} "
                    f"→ {str_weight:.2f} × {_MON_MAX_STREAM_POINTS:.0f} = {pts:.1f}")))

        stream_pts = min(stream_pts, 100.0)

        # Asset fit bonus: does the best-fit asset type align with this niche?
        best_fit = max(
            (p.fit_weight for p in dna.asset_preferences
              if p.asset_type == asset_type),
            default=50)
        asset_bonus = round((best_fit / 100.0) * _MON_ASSET_FIT_SCALE, 2)

        components.extend(stream_comps)
        components.append(ScoreComponent(
            label=f"Asset type fit ({asset_type})",
            value=best_fit,
            weight=_MON_ASSET_FIT_SCALE / 100.0,
            contribution=asset_bonus,
            rationale=(
                f"DNA asset_preference for '{asset_type}' = {best_fit}/100 "
                f"→ {asset_bonus:.1f} bonus pts")))

        score = round(min(100.0, stream_pts + asset_bonus), 1)

        n = len(dna.commercial.streams)
        if n >= 4:
            notes.append(
                f"{n} revenue streams in DNA — well-diversified monetization.")
        elif n == 1:
            notes.append(
                "Single revenue stream declared in DNA — concentration risk.")

        return ComponentScore(name="monetization", score=score,
                               components=components, notes=notes)

    # ── Automation fit ────────────────────────────────────────────────────────

    def _score_automation_fit(self, asset_type: str,
                                dna: OpportunityDNA) -> ComponentScore:
        components: list[ScoreComponent] = []
        notes: list[str] = []

        score = _AUTO_BASE
        components.append(ScoreComponent(
            label="Base automation score",
            value=_AUTO_BASE,
            weight=1.0,
            contribution=_AUTO_BASE,
            rationale="All directory builds start at a 75% automation baseline."))

        # DNA search_dimensions: more structured = more automatable
        dim_count = len(dna.search_dimensions)
        dim_bonus = min(dim_count * _AUTO_DIMENSION_BONUS_PER_DIM,
                         _AUTO_DIMENSION_BONUS_MAX)
        if dim_bonus > 0:
            score += dim_bonus
            components.append(ScoreComponent(
                label=f"Structured DNA dimensions ({dim_count})",
                value=dim_bonus,
                weight=1.0,
                contribution=dim_bonus,
                rationale=(
                    f"{dim_count} search_dimensions × {_AUTO_DIMENSION_BONUS_PER_DIM} "
                    f"= +{dim_bonus:.0f} pts (cap {_AUTO_DIMENSION_BONUS_MAX:.0f})")))

        # Regulated markets need manual compliance review
        if dna.commercial and dna.commercial.regulated:
            score -= _AUTO_REGULATED_PENALTY
            components.append(ScoreComponent(
                label="Regulated market penalty",
                value=-_AUTO_REGULATED_PENALTY,
                weight=1.0,
                contribution=-_AUTO_REGULATED_PENALTY,
                rationale=(
                    f"DNA commercial.regulated = True → "
                    f"−{_AUTO_REGULATED_PENALTY:.0f} pts "
                    "(manual compliance review required)")))
            notes.append(
                "Regulated market — compliance review cannot be fully automated.")

        # Asset type bonus/penalty
        asset_adj = _AUTO_ASSET_BONUS.get(asset_type, 0.0)
        if asset_adj != 0:
            score += asset_adj
            components.append(ScoreComponent(
                label=f"Asset type adjustment ({asset_type})",
                value=asset_adj,
                weight=1.0,
                contribution=asset_adj,
                rationale=(
                    f"asset_type '{asset_type}' "
                    f"→ {'+' if asset_adj > 0 else ''}{asset_adj:.0f} pts")))

        score = round(max(30.0, min(98.0, score)), 1)

        return ComponentScore(name="automation_fit", score=score,
                               components=components, notes=notes)


# ─────────────────────────────────────────────────────────────────────────────
# Public interface
# ─────────────────────────────────────────────────────────────────────────────

_scorer = OpportunityScorer()


def score_opportunity(niche_name: str, dna: OpportunityDNA,
                       ctx: dict, market_capacity=None) -> dict:
    """
    Score the opportunity and return an enriched copy of ctx.

    The returned ctx replaces the valuation-engine input fields with
    deterministic scored values. It also adds:
        ctx["opportunity_score_result"]  — full OpportunityScoreResult
        ctx["overall_opportunity_score"] — 0-100 composite

    market_capacity: optional MarketCapacityResult (from market_capacity.py).
        When provided, the scorer also weighs "is this market large enough?"
        and the ctx additionally receives:
            ctx["estimated_revenue_ceiling"] — from market_capacity
            ctx["market_capacity_score"]     — from market_capacity
            ctx["estimated_asset_size"]      — from market_capacity
        so ValuationEngine can apply a revenue ceiling. When market_capacity
        is None (default), behavior is IDENTICAL to before this parameter
        existed — fully backward compatible.

    Preserves all other ctx keys (asset_type, data_quality,
    blueprint_total_pages, revenue_low/high, ecosystem_node_name, etc.)

    Usage (in the route, before arch.generate_decision):
        ctx = score_opportunity(node.niche_name, dna, ctx)
        # or, with Market Capacity:
        ctx = score_opportunity(node.niche_name, dna, ctx, market_capacity=capacity_result)
    """
    result = _scorer.score(niche_name, dna, ctx, market_capacity=market_capacity)

    enriched = dict(ctx)

    # Overwrite the valuation-engine input fields
    enriched["search_demand_score"]      = result.ctx_mapping["search_demand_score"]
    enriched["competition_score"]        = result.ctx_mapping["competition_score"]
    enriched["directory_weakness_score"] = result.ctx_mapping["directory_weakness_score"]
    enriched["automation_fit_score"]     = result.ctx_mapping["automation_fit_score"]

    # Overwrite business_count only if no verified count already in ctx
    existing_count = ctx.get("business_count")
    if not existing_count:
        # Use supply score to back-infer an estimated count range midpoint
        # so the premium-listing supply model gets a reasonable input.
        # Supply score 100 → ~500 businesses; 50 → ~50; 30 → ~15.
        supply_s = result.business_supply.score
        estimated_count = int(math.pow(10, (supply_s / 100) * 2.7))
        enriched["business_count"] = max(1, estimated_count)
        enriched["business_count_is_estimate"] = True
    else:
        enriched["business_count_is_estimate"] = False

    # Attach the full result for templates and persistence
    enriched["opportunity_score_result"] = result
    enriched["overall_opportunity_score"] = result.overall_score

    # Market Capacity pass-through for the Valuation Engine
    if market_capacity is not None:
        enriched["market_capacity_result"]      = market_capacity
        enriched["market_capacity_score"]       = market_capacity.market_capacity_score
        enriched["estimated_revenue_ceiling"]   = market_capacity.estimated_revenue_ceiling
        enriched["estimated_asset_size"]        = market_capacity.estimated_asset_size

    return enriched
