"""
atlas/engines/market_liquidity.py

Market Liquidity Engine — evidence-only, TaggedValue throughout.

Per the architecture separation rule:
  "Scout and its intelligence engines collect evidence ONLY —
   they never score, grade, or recommend."

This engine sits alongside the Scout intelligence engines in the
separation-of-evidence-from-judgment model.  It gathers and tags
liquidity-relevant evidence; the Investment Committee makes all
judgments about what that evidence means.

What this engine produces:
  - Revenue multiple ranges (comparable exit multiples for the category)
  - Buyer demand signal (estimated appetite for this asset type)
  - Estimated time-to-exit range
  - Multiple compression risk (factors that could depress exit multiples)
  - Market depth estimate (how many realistic buyers exist)

All values are ESTIMATED from heuristic tables in this initial
implementation.  When a marketplace-data provider (Flippa, Empire
Flippers, Motion Invest, etc.) is integrated, their responses can
be tagged VERIFIED.

Note on the "continuous revenue multiplier" from the Investment OS
design session: it lives here as a tagged evidence range (lo/hi).
The judgment — whether to use lo, hi, or midpoint in a valuation —
belongs to the Investment Committee, not this engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# ---------------------------------------------------------------------------
# DataSource — mirrors the v2 TaggedValue contract
# ---------------------------------------------------------------------------

class DataSource:
    VERIFIED  = "VERIFIED"
    ESTIMATED = "ESTIMATED"
    UNKNOWN   = "UNKNOWN"


@dataclass(frozen=True)
class TaggedValue:
    """Honesty primitive. Mirrors the v2 TaggedValue exactly."""
    value: Any
    source: str         # VERIFIED | ESTIMATED | UNKNOWN
    provider: str | None = None
    rationale: str | None = None
    confidence: float = 0.0

    def __post_init__(self) -> None:
        if self.source not in (DataSource.VERIFIED, DataSource.ESTIMATED, DataSource.UNKNOWN):
            raise ValueError(f"Invalid source: {self.source!r}")


# ---------------------------------------------------------------------------
# Output types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RevenueMultipleRange:
    """Exit multiple expressed as a range: value is (lo, hi) tuple."""
    lo: float
    hi: float
    typical: float          # midpoint / most likely
    source: str
    confidence: float
    rationale: str


@dataclass(frozen=True)
class LiquidityEvidence:
    """
    Complete evidence bundle produced by this engine.

    Every field is a TaggedValue or typed evidence struct that wraps
    TaggedValues.  Nothing is a bare scalar — provenance must always
    be present so the Investment Committee can apply the honest wall.
    """
    # Monthly revenue multiple range for exit valuation
    revenue_multiple_range: RevenueMultipleRange

    # Buyer demand signal: 0.0 (illiquid) → 1.0 (highly liquid)
    buyer_demand_signal: TaggedValue             # value: float

    # Estimated months to exit from the point of listing
    time_to_exit_months: TaggedValue             # value: (lo_months, hi_months) tuple

    # Factors that could compress the multiple below typical
    # value: list of plain-English compression risk strings
    compression_risks: TaggedValue

    # Estimated number of realistic strategic buyers in this category
    # (not just marketplace buyers — strategic acquirers)
    buyer_depth_estimate: TaggedValue            # value: int (order-of-magnitude)

    # Category slug used to look up these heuristics
    category: str

    # Geographic scope considered
    geographic_scope: str


# ---------------------------------------------------------------------------
# Heuristic tables
# The honest wall: these are ESTIMATED.  Adjust as real exit data arrives.
# Key: (primary_category, geographic_scope) → dict
# If no exact match, we fall back to (primary_category, 'national'),
# then to ('_default', 'national').
#
# Multiple ranges are monthly revenue multiples (annual = 12× monthly,
# so a 30× monthly multiple ≈ 2.5× annual).  Industry norm for content
# sites is 30–42× monthly per v2 strategy docs.
# ---------------------------------------------------------------------------

_MULTIPLE_TABLE: dict[tuple[str, str], dict[str, Any]] = {
    # Pet / animal niches — strong buyer demand, proven category
    ("pet", "national"): {
        "multiple_lo": 30, "multiple_hi": 45, "multiple_typical": 36,
        "buyer_demand": 0.75,
        "time_to_exit_lo": 3, "time_to_exit_hi": 9,
        "buyer_depth": 50,
        "compression_risks": [
            "Google algorithm sensitivity for pet content",
            "Seasonality may depress trailing-12 revenue at listing",
        ],
        "rationale": "Pet niche has active buyer pool on Flippa/Empire Flippers; "
                     "strong CPMs and affiliate revenue make assets attractive.",
        "confidence": 0.55,
    },
    ("pet", "local"): {
        "multiple_lo": 18, "multiple_hi": 30, "multiple_typical": 24,
        "buyer_demand": 0.40,
        "time_to_exit_lo": 6, "time_to_exit_hi": 18,
        "buyer_depth": 8,
        "compression_risks": [
            "Local geographic constraint limits acquirer pool",
            "Harder to demonstrate scalability to strategic buyers",
        ],
        "rationale": "Local pet directories trade at lower multiples; buyer pool "
                     "is regional operators rather than strategic acquirers.",
        "confidence": 0.45,
    },
    # Trades / vocational niches
    ("trades", "national"): {
        "multiple_lo": 28, "multiple_hi": 42, "multiple_typical": 34,
        "buyer_demand": 0.60,
        "time_to_exit_lo": 4, "time_to_exit_hi": 10,
        "buyer_depth": 30,
        "compression_risks": [
            "Lead-gen revenue can appear lumpy to buyers",
            "Dependency on contractor supply in macro downturns",
        ],
        "rationale": "Vocational/trades directories benefit from strong B2B lead-gen "
                     "revenue, which is attractive to strategic acquirers.",
        "confidence": 0.50,
    },
    # Food / agriculture
    ("food", "national"): {
        "multiple_lo": 25, "multiple_hi": 38, "multiple_typical": 30,
        "buyer_demand": 0.55,
        "time_to_exit_lo": 4, "time_to_exit_hi": 12,
        "buyer_depth": 25,
        "compression_risks": [
            "DTC food market consolidation may depress multiples",
            "Regulatory changes in food safety advertising",
        ],
        "rationale": "Food directories trade in line with broader niche content; "
                     "DTC angle can attract strategic food-brand acquirers.",
        "confidence": 0.45,
    },
    # Travel / experiences
    ("travel", "national"): {
        "multiple_lo": 28, "multiple_hi": 44, "multiple_typical": 35,
        "buyer_demand": 0.65,
        "time_to_exit_lo": 3, "time_to_exit_hi": 9,
        "buyer_depth": 40,
        "compression_risks": [
            "Travel revenue highly seasonal; trailing-12 timing matters",
            "OTA competition could commoditise listing revenue",
        ],
        "rationale": "Travel niche commands healthy multiples; strong affiliate "
                     "and sponsorship revenue mix is well-understood by buyers.",
        "confidence": 0.55,
    },
    # Health / wellness
    ("health", "national"): {
        "multiple_lo": 32, "multiple_hi": 48, "multiple_typical": 38,
        "buyer_demand": 0.70,
        "time_to_exit_lo": 3, "time_to_exit_hi": 8,
        "buyer_depth": 60,
        "compression_risks": [
            "YMYL Google sensitivity — ranking volatility risk",
            "FTC disclosure requirements can complicate affiliate revenue",
        ],
        "rationale": "Health/wellness is one of the highest-demand niche content "
                     "categories; strategic and financial buyers both active.",
        "confidence": 0.55,
    },
    # Default fallback
    ("_default", "national"): {
        "multiple_lo": 24, "multiple_hi": 38, "multiple_typical": 30,
        "buyer_demand": 0.45,
        "time_to_exit_lo": 4, "time_to_exit_hi": 14,
        "buyer_depth": 15,
        "compression_risks": [
            "Niche-specific buyer pool size unknown",
            "Undiversified revenue streams reduce acquirer confidence",
        ],
        "rationale": "Default heuristic — no category-specific exit data available. "
                     "Based on niche content site median on Flippa/Empire Flippers.",
        "confidence": 0.30,
    },
}


def _lookup_heuristics(category: str, scope: str) -> dict[str, Any]:
    """
    Hierarchical lookup:
        1. (category, scope) exact match
        2. (category, 'national') fallback
        3. ('_default', 'national') final fallback
    """
    # Normalise category — strip common suffixes/prefixes
    cat = category.lower().strip().split("-")[0].split("_")[0]
    scope_norm = scope.lower().strip()

    return (
        _MULTIPLE_TABLE.get((cat, scope_norm))
        or _MULTIPLE_TABLE.get((cat, "national"))
        or _MULTIPLE_TABLE[("_default", "national")]
    )


# ---------------------------------------------------------------------------
# Engine entry point
# ---------------------------------------------------------------------------

def gather(
    category: str,
    geographic_scope: str = "national",
    # Future: provider_results: dict[str, Any] | None = None
) -> LiquidityEvidence:
    """
    Gather liquidity evidence for a given business category and scope.

    All outputs are ESTIMATED (heuristic tables).  When real provider
    data is integrated, verified responses from e.g. Empire Flippers
    should be passed through `provider_results` and tagged VERIFIED
    before being folded in — that transformation belongs in a future
    provider adapter layer, not here.

    Args:
        category:          Primary business category slug (e.g. "pet", "travel").
        geographic_scope:  One of: local | regional | national | global.

    Returns:
        LiquidityEvidence — fully tagged, no bare scalars.
    """
    h = _lookup_heuristics(category, geographic_scope)
    source = DataSource.ESTIMATED
    conf = h["confidence"]

    multiple_range = RevenueMultipleRange(
        lo=h["multiple_lo"],
        hi=h["multiple_hi"],
        typical=h["multiple_typical"],
        source=source,
        confidence=conf,
        rationale=h["rationale"],
    )

    buyer_demand = TaggedValue(
        value=h["buyer_demand"],
        source=source,
        provider="heuristic_table_v1",
        rationale=f"Buyer demand signal for {category}/{geographic_scope}. "
                  f"0.0=illiquid, 1.0=highly liquid.",
        confidence=conf,
    )

    time_to_exit = TaggedValue(
        value=(h["time_to_exit_lo"], h["time_to_exit_hi"]),
        source=source,
        provider="heuristic_table_v1",
        rationale=f"Estimated months from listing to close: "
                  f"{h['time_to_exit_lo']}–{h['time_to_exit_hi']} months.",
        confidence=conf,
    )

    compression_risks = TaggedValue(
        value=h["compression_risks"],
        source=source,
        provider="heuristic_table_v1",
        rationale="Factors that could compress exit multiples below the typical range.",
        confidence=conf,
    )

    buyer_depth = TaggedValue(
        value=h["buyer_depth"],
        source=source,
        provider="heuristic_table_v1",
        rationale=f"Order-of-magnitude estimate: ~{h['buyer_depth']} realistic buyers "
                  f"(including strategic acquirers) active in this category.",
        confidence=conf,
    )

    return LiquidityEvidence(
        revenue_multiple_range=multiple_range,
        buyer_demand_signal=buyer_demand,
        time_to_exit_months=time_to_exit,
        compression_risks=compression_risks,
        buyer_depth_estimate=buyer_depth,
        category=category,
        geographic_scope=geographic_scope,
    )


# ---------------------------------------------------------------------------
# Convenience: estimate exit value range (not a score — an evidence helper)
# ---------------------------------------------------------------------------

def estimate_exit_value(
    liquidity: LiquidityEvidence,
    monthly_revenue: float,
    revenue_source: str = DataSource.ESTIMATED,
) -> TaggedValue:
    """
    Compute lo/typical/hi exit valuations by multiplying revenue × multiple range.

    This is arithmetic evidence — not a recommendation.  The Committee
    decides whether to use the conservative, typical, or aggressive figure.

    The output TaggedValue source is the *weaker* of the two inputs:
    if revenue is ESTIMATED and multiples are ESTIMATED, output is ESTIMATED.
    If either is UNKNOWN, output is UNKNOWN.
    """
    source_rank = {DataSource.VERIFIED: 2, DataSource.ESTIMATED: 1, DataSource.UNKNOWN: 0}
    multiple_source = liquidity.revenue_multiple_range.source
    combined_source = min(
        [revenue_source, multiple_source],
        key=lambda s: source_rank.get(s, 0)
    )

    if monthly_revenue <= 0 or combined_source == DataSource.UNKNOWN:
        return TaggedValue(
            value={"lo": 0.0, "typical": 0.0, "hi": 0.0},
            source=DataSource.UNKNOWN,
            rationale="Cannot estimate exit value: revenue is zero or unknown.",
            confidence=0.0,
        )

    r = liquidity.revenue_multiple_range
    result = {
        "lo":      round(monthly_revenue * r.lo, 2),
        "typical": round(monthly_revenue * r.typical, 2),
        "hi":      round(monthly_revenue * r.hi, 2),
    }

    confidence = min(
        liquidity.revenue_multiple_range.confidence,
        0.9 if revenue_source == DataSource.VERIFIED else 0.5,
    )

    return TaggedValue(
        value=result,
        source=combined_source,
        provider="market_liquidity_engine_v1",
        rationale=(
            f"Exit value = ${monthly_revenue:,.0f}/mo × "
            f"{r.lo}–{r.hi}× multiple range "
            f"(category: {liquidity.category}, scope: {liquidity.geographic_scope}). "
            f"Revenue source: {revenue_source}."
        ),
        confidence=round(confidence, 3),
    )


# ---------------------------------------------------------------------------
# Compatibility wrapper
#
# Thin class shim for older call sites / tests that expect a
# MarketLiquidityEngine class instance rather than the module-level
# gather() / estimate_exit_value() functions. Contains zero business
# logic — every method delegates directly to the function of the
# same name above. The functional API remains canonical; the
# evidence-only contract (no scoring, everything ESTIMATED from
# heuristic tables) is enforced only in gather() above, unchanged.
# ---------------------------------------------------------------------------

class MarketLiquidityEngine:
    """
    Compatibility wrapper around the module-level gather() and
    estimate_exit_value() functions.

    Usage:
        engine = MarketLiquidityEngine()
        evidence = engine.gather(category="pet", geographic_scope="national")
        exit_val = engine.estimate_exit_value(evidence, monthly_revenue=500.0)

    This class holds no state and performs no logic of its own —
    it exists solely so that code written against a class-based
    interface continues to work unchanged.
    """

    def gather(
        self,
        category: str,
        geographic_scope: str = "national",
    ) -> LiquidityEvidence:
        return gather(category, geographic_scope)

    def estimate_exit_value(
        self,
        liquidity: LiquidityEvidence,
        monthly_revenue: float,
        revenue_source: str = DataSource.ESTIMATED,
    ) -> TaggedValue:
        return estimate_exit_value(liquidity, monthly_revenue, revenue_source)
