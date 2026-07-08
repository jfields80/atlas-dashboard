"""
demand_providers.py — Demand Intelligence Provider Architecture.

Defines the provider protocol for Demand Intelligence, one of the four
Intelligence Engines that Scout orchestrates in the Atlas Investment OS:

    Scout
      ├── Business Intelligence
      ├── Demand Intelligence        ← this provider layer feeds it
      ├── Competition Intelligence
      └── Monetization Intelligence

Design: identical pattern to scout_providers.py. Providers are stateless,
speak TaggedValue (VERIFIED / ESTIMATED / UNKNOWN), and merge per-field
with higher-quality sources winning. Adding a real provider later
(Google Keyword Planner, Search Console, Google Trends, DataForSEO,
SEMrush, Ahrefs) upgrades tagged values from ESTIMATED to VERIFIED
without changing Demand Intelligence, Market Capacity, or anything
downstream.

Current providers:
    EstimatedDemandProvider — deterministic inference from DNA + niche
                              text. All outputs tagged ESTIMATED, except
                              trend_direction which is honestly UNKNOWN
                              (trend cannot be inferred without time-series
                              data; inventing one would violate the honesty
                              layer).

Future providers (documented, not implemented):
    GoogleKeywordPlannerProvider — search volume, CPC          → VERIFIED
    SearchConsoleProvider        — impressions, queries        → VERIFIED
    GoogleTrendsProvider         — trend_direction, seasonality → VERIFIED
    DataForSeoProvider           — volume, difficulty, SERP     → VERIFIED
    SemrushProvider              — volume, difficulty, CPC      → VERIFIED
    AhrefsProvider               — difficulty, SERP, backlinks  → VERIFIED

Single-source-of-truth rule:
    Demand Intelligence is the authoritative engine for search volume,
    CPC, keyword difficulty, and all other user-demand measurements in
    the Investment OS architecture. Older estimation paths elsewhere in
    Atlas remain untouched for backward compatibility, but new pipeline
    code should read demand data from DemandResult, never recompute it.

Architecture rules:
    - Pure service. No Flask, no SQL, no HTTP in this file.
    - Deterministic: same inputs always produce same outputs.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable

from .dna.schema import OpportunityDNA, Intensity
from .scout_providers import DataSource, TaggedValue, _estimated, _unknown


# ─────────────────────────────────────────────────────────────────────────────
# Provider output — what a demand provider CAN populate
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class DemandProviderOutput:
    """
    All fields optional — providers populate only what their data source
    covers. Demand Intelligence merges outputs (VERIFIED > ESTIMATED >
    UNKNOWN per field).
    """
    provider_name: str

    # Core demand metrics
    search_volume:         Optional[TaggedValue] = None   # monthly searches (cluster total)
    head_term_volume:      Optional[TaggedValue] = None   # monthly searches (head term only)
    commercial_intent:     Optional[TaggedValue] = None   # 0-100
    keyword_difficulty:    Optional[TaggedValue] = None   # 0-100, higher = harder
    cpc:                   Optional[TaggedValue] = None   # USD per click

    # Demand shape
    seasonality:           Optional[TaggedValue] = None   # 0-100, higher = more seasonal swing
    trend_direction:       Optional[TaggedValue] = None   # 0-100: 50=flat, >50 growing, <50 declining
    long_tail_depth:       Optional[TaggedValue] = None   # 0-100, breadth of variant demand
    question_demand:       Optional[TaggedValue] = None   # 0-100, informational question volume
    local_search_strength: Optional[TaggedValue] = None   # 0-100, "near me"-style demand
    serp_competition:      Optional[TaggedValue] = None   # 0-100, higher = more contested SERP


@runtime_checkable
class DemandProvider(Protocol):
    """Interface every demand provider implements. Stateless."""

    @property
    def name(self) -> str:
        ...

    def research(self, niche_name: str, dna: OpportunityDNA,
                  ctx: dict) -> DemandProviderOutput:
        """
        Return what this provider knows about demand for the niche.
        Fields the provider cannot populate remain None.
        Must not raise — return an empty output on internal error.
        """
        ...


# ─────────────────────────────────────────────────────────────────────────────
# Merging — VERIFIED > ESTIMATED > UNKNOWN, per field
# ─────────────────────────────────────────────────────────────────────────────

_SOURCE_PRIORITY = {
    DataSource.VERIFIED:  3,
    DataSource.ESTIMATED: 2,
    DataSource.UNKNOWN:   1,
}


def _best(a: Optional[TaggedValue],
          b: Optional[TaggedValue]) -> Optional[TaggedValue]:
    if a is None:
        return b
    if b is None:
        return a
    return a if _SOURCE_PRIORITY[a.source] >= _SOURCE_PRIORITY[b.source] else b


def merge_demand_outputs(outputs: list[DemandProviderOutput]) -> DemandProviderOutput:
    """Merge multiple provider outputs field-by-field, best source wins."""
    merged = DemandProviderOutput(provider_name="merged")
    for out in outputs:
        merged.search_volume         = _best(merged.search_volume,         out.search_volume)
        merged.head_term_volume      = _best(merged.head_term_volume,      out.head_term_volume)
        merged.commercial_intent     = _best(merged.commercial_intent,     out.commercial_intent)
        merged.keyword_difficulty    = _best(merged.keyword_difficulty,    out.keyword_difficulty)
        merged.cpc                   = _best(merged.cpc,                   out.cpc)
        merged.seasonality           = _best(merged.seasonality,           out.seasonality)
        merged.trend_direction       = _best(merged.trend_direction,       out.trend_direction)
        merged.long_tail_depth       = _best(merged.long_tail_depth,       out.long_tail_depth)
        merged.question_demand       = _best(merged.question_demand,       out.question_demand)
        merged.local_search_strength = _best(merged.local_search_strength, out.local_search_strength)
        merged.serp_competition      = _best(merged.serp_competition,      out.serp_competition)
    return merged


# ─────────────────────────────────────────────────────────────────────────────
# Estimated provider — deterministic inference, ships today
# ─────────────────────────────────────────────────────────────────────────────

_INTENSITY_NUM = {
    Intensity.EXTREME:   98, Intensity.VERY_HIGH: 85,
    Intensity.HIGH:      68, Intensity.MEDIUM:    50,
    Intensity.LOW:       30, Intensity.VERY_LOW:  12,
}


def _int(i: Optional[Intensity], default: float = 50.0) -> float:
    return float(_INTENSITY_NUM.get(i, default)) if i is not None else default


# CPC by DNA lead_value — the authoritative CPC estimation table for the
# Investment OS. (scout_providers.py carries a legacy copy for backward
# compatibility; per the single-source-of-truth rule, new consumers read
# CPC from DemandResult.)
_CPC_BY_LEAD_VALUE = {
    Intensity.EXTREME:   18.0,
    Intensity.VERY_HIGH: 12.0,
    Intensity.HIGH:       6.0,
    Intensity.MEDIUM:     2.5,
    Intensity.LOW:        0.80,
    Intensity.VERY_LOW:   0.25,
}

# Head-term monthly volume model: DNA intent quality × breadth ceiling.
# A 1-word niche can reach ~100k/mo; each extra word multiplies by 0.45.
_VOLUME_CEILING_BASE   = 100_000
_VOLUME_WORD_DECAY     = 0.45

# Seasonality signal keywords → estimated seasonal swing contribution.
# Deterministic text matching; a travel niche genuinely swings more than
# a therapy niche, and these words are the observable proxy for that.
_SEASONAL_SIGNALS = {
    "vacation": 25.0, "travel": 20.0, "holiday": 25.0, "summer": 30.0,
    "winter": 30.0, "christmas": 35.0, "beach": 25.0, "ski": 35.0,
    "wedding": 20.0, "camp": 20.0, "festival": 25.0, "tourist": 20.0,
}
_SEASONALITY_BASE = 15.0   # every market has some seasonal variation
_SEASONALITY_MAX  = 85.0

# SERP competition proxy (demand-side view: how contested is the results
# page a searcher actually sees). Breadth base minus specificity relief,
# plus aggregator-domination penalty.
_SERP_BREADTH_BASE     = 78.0
_SERP_WORD_RELIEF      = 8.0
_SERP_FLOOR            = 12.0
_SERP_AGGREGATOR_BOOST = 14.0
_AGGREGATOR_SIGNALS = [
    "restaurant", "hotel", "dentist", "doctor", "lawyer",
    "attorney", "contractor", "gym", "plumber", "realtor",
]

# Keyword difficulty tracks SERP competition but slightly softer for
# niche long-tail terms (directories rank for long-tail faster than
# head terms; difficulty reflects the blended cluster, not just the head).
_DIFFICULTY_FROM_SERP = 0.88


class EstimatedDemandProvider:
    """
    Deterministic demand inference from niche text + DNA.
    All outputs ESTIMATED except trend_direction, which is UNKNOWN:
    trend requires time-series evidence (Google Trends, Search Console),
    and a deterministic text model has no honest basis for inventing one.
    """

    _NAME = "EstimatedDemandProvider"

    @property
    def name(self) -> str:
        return self._NAME

    def research(self, niche_name: str, dna: OpportunityDNA,
                  ctx: dict) -> DemandProviderOutput:
        out = DemandProviderOutput(provider_name=self._NAME)
        n  = niche_name.lower()
        wc = len(niche_name.split())

        # ── Head-term volume ───────────────────────────────────────────────
        ci = _int(dna.intent.commercial_intent if dna.intent else None)
        li = _int(dna.intent.local_intent       if dna.intent else None)
        quality = (ci * 0.5 + li * 0.5) / 100.0
        ceiling = _VOLUME_CEILING_BASE * math.pow(_VOLUME_WORD_DECAY, max(0, wc - 1))
        head_volume = max(40, int(ceiling * quality))
        out.head_term_volume = _estimated(
            float(head_volume), self._NAME,
            f"DNA commercial={ci:.0f}, local={li:.0f} → quality {quality:.2f} "
            f"× breadth ceiling {ceiling:,.0f} ≈ {head_volume:,}/mo (head term)")

        # Cluster volume is synthesised by the engine from the intent
        # cluster (head volume / head share); the provider supplies the
        # head measurement only, mirroring what real keyword APIs return.

        # ── Commercial intent ──────────────────────────────────────────────
        transactional = ["best", "top", "buy", "hire", "book", "reserve",
                          "near me", "cost", "price", "affordable", "cheap"]
        hits  = sum(1 for s in transactional if s in n)
        boost = min(hits * 5.0, 20.0)
        ci_score = min(100.0, ci + boost)
        out.commercial_intent = _estimated(
            ci_score, self._NAME,
            f"DNA commercial_intent {ci:.0f} + {hits} transactional signal(s) "
            f"(+{boost:.0f}, cap 20) = {ci_score:.0f}")

        # ── SERP competition ───────────────────────────────────────────────
        agg_hit = any(s in n for s in _AGGREGATOR_SIGNALS)
        serp = max(_SERP_FLOOR,
                    _SERP_BREADTH_BASE - (wc - 1) * _SERP_WORD_RELIEF)
        if agg_hit:
            serp = min(96.0, serp + _SERP_AGGREGATOR_BOOST)
        serp = round(serp, 1)
        out.serp_competition = _estimated(
            serp, self._NAME,
            f"breadth {_SERP_BREADTH_BASE:.0f} − {wc-1}×{_SERP_WORD_RELIEF:.0f}"
            f"{' + aggregator ' + format(_SERP_AGGREGATOR_BOOST, '.0f') if agg_hit else ''}"
            f" = {serp}")

        # ── Keyword difficulty ─────────────────────────────────────────────
        kd = round(serp * _DIFFICULTY_FROM_SERP, 1)
        out.keyword_difficulty = _estimated(
            kd, self._NAME,
            f"SERP competition {serp} × {_DIFFICULTY_FROM_SERP} "
            f"(long-tail blend softener) = {kd}")

        # ── CPC ────────────────────────────────────────────────────────────
        cpc = _CPC_BY_LEAD_VALUE.get(
            dna.commercial.lead_value if dna.commercial else None, 2.5)
        out.cpc = _estimated(
            cpc, self._NAME,
            f"DNA lead_value="
            f"{dna.commercial.lead_value.value if dna.commercial else 'n/a'} "
            f"→ ${cpc:.2f}/click")

        # ── Seasonality ────────────────────────────────────────────────────
        season_hits = [(kw, pts) for kw, pts in _SEASONAL_SIGNALS.items() if kw in n]
        # Also inspect DNA display name — market-level seasonality signal
        dna_name = dna.display_name.lower() if dna.display_name else ""
        season_hits += [(f"dna:{kw}", pts * 0.8) for kw, pts in _SEASONAL_SIGNALS.items()
                         if kw in dna_name and not any(h[0] == kw for h in season_hits)]
        season = min(_SEASONALITY_MAX,
                      _SEASONALITY_BASE + sum(p for _, p in season_hits))
        detail = ", ".join(k for k, _ in season_hits) if season_hits else "none"
        out.seasonality = _estimated(
            round(season, 1), self._NAME,
            f"base {_SEASONALITY_BASE:.0f} + signals [{detail}] "
            f"= {season:.0f}/100 seasonal swing")

        # ── Trend direction — honestly UNKNOWN ─────────────────────────────
        out.trend_direction = _unknown("trend_direction")
        # A deterministic text model cannot know whether demand is growing
        # or declining. Connect GoogleTrendsProvider or SearchConsoleProvider
        # to populate this with VERIFIED time-series evidence.

        # ── Long-tail depth ────────────────────────────────────────────────
        # More DNA search dimensions and examples = more real query variants.
        dims = dna.search_dimensions
        dim_count = len(dims)
        example_count = sum(len(d.examples) for d in dims)
        lt = min(100.0, dim_count * 8.0 + example_count * 2.5)
        out.long_tail_depth = _estimated(
            round(lt, 1), self._NAME,
            f"{dim_count} DNA dimensions × 8 + {example_count} examples × 2.5 "
            f"= {lt:.0f}/100 (cap 100)")

        # ── Question demand ────────────────────────────────────────────────
        ca = _int(dna.intent.content_appetite if dna.intent else None)
        q = round(min(100.0, ca * 0.85 + (10.0 if wc <= 3 else 0.0)), 1)
        out.question_demand = _estimated(
            q, self._NAME,
            f"DNA content_appetite {ca:.0f} × 0.85"
            f"{' + 10 broad-niche question bonus' if wc <= 3 else ''} = {q}")

        # ── Local search strength ──────────────────────────────────────────
        local_signals = ["near me", "near ", " in ", "local", "nearby"]
        local_hits = sum(1 for s in local_signals if s in n)
        local = round(min(100.0, li * 0.80 + min(local_hits * 8.0, 20.0)), 1)
        out.local_search_strength = _estimated(
            local, self._NAME,
            f"DNA local_intent {li:.0f} × 0.80 + {local_hits} local signal(s) "
            f"(+{min(local_hits*8.0, 20.0):.0f}, cap 20) = {local}")

        return out
