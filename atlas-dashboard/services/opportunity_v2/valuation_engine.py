"""
valuation_engine.py — Opportunity Valuation Engine with Explainable Calculations.

Pure service module. No Flask, no SQL, no routes.
Takes OpportunityDNA + context dict, returns ValuationResult.

Every calculation now produces a ValuationExplanation alongside the
numbers. The explanation object records every intermediate value, every
named factor, and every adjustment so any output can be audited without
reading source code.

Design principle: prefer an explainable estimate over an impressive one.
If confidence is low, the explanation says so and says why.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional

from .dna.schema import OpportunityDNA, Intensity


# ─────────────────────────────────────────────────────────────────────────────
# Named constants — every number documented with its rationale
# ─────────────────────────────────────────────────────────────────────────────

# Strength -> fraction of DNA declared range achieved at maturity.
# EXTREME: market so dominated by this stream type that ceiling is reachable.
# VERY_HIGH: strong dominant stream, expect 85% of DNA ceiling.
# HIGH: meaningful stream, competitive market needed to hit ceiling, use 65%.
# MEDIUM: present but not primary, realistic capture 45%.
# LOW: incidental stream, expect ~20%.
# VERY_LOW: speculative, excluded from heuristic estimates.
_STRENGTH_CAPTURE = {
    Intensity.EXTREME:   1.00,
    Intensity.VERY_HIGH: 0.85,
    Intensity.HIGH:      0.65,
    Intensity.MEDIUM:    0.45,
    Intensity.LOW:       0.20,
    Intensity.VERY_LOW:  0.08,
}

# 12-24 month maturity capture: what fraction of the theoretical ceiling
# a site actually reaches at the 18-month mark.
# affiliate_booking:  SEO + booking-intent compounds by month 18 → 60%.
# affiliate_products: product content ranks faster than local → 65%.
# affiliate_platforms: similar compounding to products → 60%.
# premium_listings:   can pre-sell; 18mo close rate 20-35% of supply → 55%.
# lead_gen:           trust + traffic build; quality leads arrive with SEO → 50%.
# ads:                traffic-linear; sandbox lifts ~month 9 → 50%.
# sponsorships:       relationship-driven, slowest to build → 40%.
_MATURITY_CAPTURE = {
    "affiliate_booking":   0.60,
    "affiliate_products":  0.65,
    "affiliate_platforms": 0.60,
    "premium_listings":    0.55,
    "lead_gen":            0.50,
    "ads":                 0.50,
    "sponsorships":        0.40,
}
_MATURITY_CAPTURE_DEFAULT = 0.45

# Execution scenario multipliers applied to the maturity estimate.
# Conservative: pessimistic execution and tougher-than-expected conditions.
# Likely:       realistic for a competent operator using Atlas automation.
# Aggressive:   strong execution, favorable market timing, above-avg conversion.
_SCENARIO_CONSERVATIVE = 0.50
_SCENARIO_LIKELY       = 0.80
_SCENARIO_AGGRESSIVE   = 1.15

# Competition drag on the upside scenario.
# Formula: multiplier = max(FLOOR, 1.0 - (competition/100) × MAX_DRAG)
# At competition=0:   multiplier = 1.00 (no drag)
# At competition=50:  multiplier = 0.70
# At competition=100: multiplier = 0.40 (severe drag, floor)
_COMPETITION_MAX_DRAG = 0.60
_COMPETITION_FLOOR    = 0.40

# Demand lift across 0-100 demand score range.
# Formula: multiplier = BASE + (demand/100) × RANGE
# At demand=0:   multiplier = 0.50 (half capture)
# At demand=50:  multiplier = 0.80
# At demand=100: multiplier = 1.10 (slight upside from strong demand)
_DEMAND_LIFT_BASE  = 0.50
_DEMAND_LIFT_RANGE = 0.60

# Heuristic uncertainty discounts: no live data = more conservative projections.
# Conservative scenario is already pessimistic; no additional discount applied.
# Likely: -15% haircut for unknown unknowns.
# Aggressive: -30% haircut; optimism without data is dangerous.
_HEURISTIC_LIKELY_DISCOUNT     = 0.85
_HEURISTIC_AGGRESSIVE_DISCOUNT = 0.70

# Premium listing supply model at 18-month maturity.
# Research basis: established niche directories close 2-5% of reachable
# businesses at $35-$75/mo. Blended with DNA-declared range to prevent
# supply-model from overriding market research when DNA is well-calibrated.
_PL_MATURITY_CONV_LOW  = 0.020   # 2% conversion of business_count
_PL_MATURITY_CONV_HIGH = 0.050   # 5% conversion of business_count
_PL_PRICE_LOW          = 35      # $/mo per premium listing (low)
_PL_PRICE_HIGH         = 75      # $/mo per premium listing (high)

# Risk component weights. Must sum to 1.0.
# Competition is weighted highest: it's the most reliable signal we have
# for whether organic traffic will arrive. Concentration risk second
# because single-stream dependence is a common failure mode.
_RISK_COMPETITION_WEIGHT   = 0.35
_RISK_CONCENTRATION_WEIGHT = 0.25
_RISK_SUPPLY_WEIGHT        = 0.20
_RISK_DATA_QUALITY_WEIGHT  = 0.20
_RISK_SUPPLY_THIN_THRESHOLD = 30  # fewer businesses than this = high supply risk

# Five-year revenue growth ramp (fraction of year-2 likely monthly revenue).
# Year 1: 40% of likely/mo — SEO sandbox, early listings, ramp period.
# Year 2: 100% — model calibration point (this is what "likely" means).
# Year 3-5: 15%/year compounding growth assumption for an established directory.
_FIVE_YEAR_RAMP = [0.40, 1.00, 1.15, 1.32, 1.52]

# Exit multiple range: directory businesses sell at 30-42× monthly revenue.
# (2.5-3.5× annual, consistent with Motion Invest and Flippa 2023-2025 data.)
# Multiple is keyed to build_score as a proxy for asset quality.
_EXIT_MULTIPLE_PREMIUM  = 42   # build_score >= 75: proven, automated, diversified
_EXIT_MULTIPLE_STANDARD = 36   # build_score 55-74: solid asset, some risk
_EXIT_MULTIPLE_BASIC    = 30   # build_score <  55: speculative, unproven

# Investment grade thresholds.
# grade_score = (build_score × 0.6) + ((100 - risk_score) × 0.4)
# Weights: build_score is a more actionable signal than risk alone.
_GRADE_WEIGHT_BUILD = 0.6
_GRADE_WEIGHT_RISK  = 0.4
_GRADE_A_FLOOR = 72
_GRADE_B_FLOOR = 55
_GRADE_C_FLOOR = 38

# Monetization diversity: each of up to 6 streams contributes proportionally.
_DIVERSITY_STREAM_CAP = 6

# Confidence base scores by data quality.
# Heuristic: we don't know what we don't know. Hard cap at 45.
# Mixed: partial Scout data, meaningful uplift allowed.
# Verified: full Scout data, allow up to 92 (not 100 — model uncertainty remains).
_CONFIDENCE_BASE = {"verified": 78.0, "mixed": 58.0, "heuristic": 38.0}
_CONFIDENCE_HEURISTIC_CAP = 45.0
_CONFIDENCE_MAX = 92.0


# ─────────────────────────────────────────────────────────────────────────────
# Explanation dataclasses — one per major calculation
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class StreamCalculation:
    """Full calculation trail for one revenue stream."""
    stream: str

    # DNA inputs
    dna_range_low: int
    dna_range_high: int
    strength: str

    # Adjustment factors (all named, all traceable to a constant)
    strength_capture_pct: float        # from _STRENGTH_CAPTURE
    maturity_capture_pct: float        # from _MATURITY_CAPTURE
    demand_multiplier: float           # from _DEMAND_LIFT_BASE + demand × _DEMAND_LIFT_RANGE
    competition_multiplier: float      # from _COMPETITION_FLOOR / _COMPETITION_MAX_DRAG

    # Premium listing detail (only populated for premium_listings stream)
    pl_supply_low: Optional[int] = None    # business_count × conv_low × price_low
    pl_supply_high: Optional[int] = None   # business_count × conv_high × price_high
    pl_dna_low: Optional[int] = None
    pl_dna_high: Optional[int] = None
    pl_blended_low: Optional[int] = None   # average of supply and DNA
    pl_blended_high: Optional[int] = None

    # Maturity estimates before scenario splits
    maturity_estimate_low: int = 0
    maturity_estimate_high: int = 0

    # Scenario splits
    scenario_conservative: int = 0
    scenario_likely_pre_discount: int = 0
    scenario_aggressive_pre_discount: int = 0

    # Heuristic discounts (None if not applied)
    heuristic_likely_discount_applied: Optional[float] = None
    heuristic_aggressive_discount_applied: Optional[float] = None

    # Final outputs
    final_conservative: int = 0
    final_likely: int = 0
    final_aggressive: int = 0

    active: bool = True
    excluded_reason: str = ""


@dataclass
class RevenueExplanation:
    """Complete revenue calculation trail across all streams."""
    # Inputs
    business_count: int
    competition_score: float
    demand_score: float
    data_quality: str

    # Derived multipliers
    competition_multiplier: float
    competition_multiplier_formula: str  # human-readable formula

    demand_multiplier: float
    demand_multiplier_formula: str

    # Per-stream calculations
    stream_calculations: list[StreamCalculation]

    # Aggregation
    streams_included: int
    streams_excluded: int

    gross_conservative: int
    gross_likely: int
    gross_aggressive: int

    # Any adjustments applied at the aggregate level
    # (Currently none — adjustments are per-stream. Field reserved for future use.)
    aggregate_adjustments: list[str]

    final_conservative: int
    final_likely: int
    final_aggressive: int


@dataclass
class ConfidenceComponent:
    label: str
    condition: str         # the test that was applied
    applied: bool          # whether the adjustment fired
    adjustment: float      # points added (or subtracted)


@dataclass
class ConfidenceExplanation:
    data_quality: str
    base_score: float
    base_score_rationale: str
    components: list[ConfidenceComponent]
    raw_total: float
    cap_applied: Optional[float]    # None if no cap; value of cap if applied
    cap_reason: Optional[str]
    final_confidence: float


@dataclass
class RiskComponent:
    label: str
    raw_value: float
    weight: float
    weighted_contribution: float
    rationale: str


@dataclass
class RiskExplanation:
    components: list[RiskComponent]
    total_risk: float


@dataclass
class BuildScoreComponent:
    label: str
    raw_value: float
    weight: float
    weighted_contribution: float
    calculation: str    # human-readable derivation


@dataclass
class BuildScoreExplanation:
    components: list[BuildScoreComponent]
    raw_total: float
    final_build_score: float


@dataclass
class InvestmentGradeExplanation:
    build_score: float
    risk_score: float
    grade_score_formula: str
    grade_score: float
    threshold_applied: str     # e.g. "≥ 72 → A"
    grade: str


@dataclass
class EconomicsExplanation:
    base_startup: float
    startup_additions: list[str]     # each line: "Regulated market: +$400"
    total_startup: float

    base_maintenance: float
    maintenance_additions: list[str]
    total_maintenance: float

    automation_pct: float
    automation_source: str

    ttfr_base: int
    ttfr_adjustments: list[str]
    ttfr_final: int


@dataclass
class VentureExplanation:
    likely_monthly: int
    five_year_ramp: list[str]       # year-by-year: "Year 1: $X × 0.40 × 12 = $Y"
    five_year_total: int
    exit_multiple: int
    exit_multiple_rationale: str
    exit_value: int


@dataclass
class ValuationExplanation:
    """
    Complete audit trail for one valuation run.

    Every number in ValuationResult is derivable from this object
    without reading source code. Designed to be serialized to JSON
    and displayed in the UI as a Bloomberg-style calculation panel.
    """
    revenue: RevenueExplanation
    confidence: ConfidenceExplanation
    risk: RiskExplanation
    build_score: BuildScoreExplanation
    investment_grade: InvestmentGradeExplanation
    economics: EconomicsExplanation
    venture: VentureExplanation

    # Top-level summary sentence Atlas can display verbatim
    summary: str


# ─────────────────────────────────────────────────────────────────────────────
# Stream and result dataclasses (unchanged interface)
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class StreamValuation:
    stream: str
    monthly_low: int
    monthly_likely: int
    monthly_high: int
    strength: str
    basis: str
    active: bool = True


@dataclass
class ValuationResult:
    # Revenue scenarios
    conservative_monthly_revenue: int
    likely_monthly_revenue: int
    aggressive_monthly_revenue: int
    revenue_low: int        # alias: conservative
    revenue_likely: int     # alias: likely
    revenue_high: int       # alias: aggressive
    revenue_midpoint: int   # alias: likely (backward compat)

    # Venture projections
    five_year_revenue_potential: int
    estimated_exit_value: int

    # Scoring
    revenue_confidence: float
    risk_score: float
    build_score: float
    investment_grade: str
    monetization_diversity_score: float

    # Economics
    startup_cost: float
    maintenance_cost: float
    time_to_first_revenue_days: int
    automation_percentage: float
    roi_months: float

    # Detail
    streams: list[StreamValuation] = field(default_factory=list)
    valuation_notes: list[str] = field(default_factory=list)

    # Explanation (new — full audit trail)
    explanation: Optional[ValuationExplanation] = None


# ─────────────────────────────────────────────────────────────────────────────
# Engine
# ─────────────────────────────────────────────────────────────────────────────

class ValuationEngine:
    """Stateless. Instantiate once or per-call."""

    def value(self, dna: OpportunityDNA, ctx: dict) -> ValuationResult:
        """
        ctx keys (all optional):
            data_quality             "heuristic" | "verified" | "mixed"
            business_count           int
            competition_score        0-100 (higher = more competitive)
            search_demand_score      0-100
            directory_weakness_score 0-100
            automation_fit_score     0-100
            asset_type               str
        """
        data_quality   = ctx.get("data_quality", "heuristic")
        business_count = max(0, int(ctx.get("business_count", 0)))
        competition    = float(ctx.get("competition_score", 50))
        demand         = float(ctx.get("search_demand_score", 50))
        weakness       = float(ctx.get("directory_weakness_score", 50))
        automation_fit = float(ctx.get("automation_fit_score", 70))
        asset_type     = ctx.get("asset_type", "directory")

        # Compute market multipliers once — used in streams and explanation
        competition_mult = max(
            _COMPETITION_FLOOR,
            1.0 - (competition / 100.0) * _COMPETITION_MAX_DRAG)
        demand_mult = _DEMAND_LIFT_BASE + (demand / 100.0) * _DEMAND_LIFT_RANGE

        # Revenue
        streams, stream_calcs = self._value_streams(
            dna, business_count, competition_mult, demand_mult, data_quality)
        active = [s for s in streams if s.active]
        active_calcs = [c for c in stream_calcs if c.active]

        conservative = max(sum(s.monthly_low    for s in active), 0)
        likely       = max(sum(s.monthly_likely for s in active), conservative)
        aggressive   = max(sum(s.monthly_high   for s in active), likely)

        # ── Market Capacity ceiling (optional, additive) ────────────────────
        # When ctx carries a revenue ceiling from market_capacity.py, revenue
        # must never exceed realistic market capacity. This does NOT change
        # any existing calculation — it only clips the three scenarios
        # (and only if a ceiling is present) and records the fact in
        # valuation_notes for full auditability. Absent ctx key = no change
        # to prior behavior.
        revenue_ceiling = ctx.get("estimated_revenue_ceiling")
        capacity_clip_note: Optional[str] = None
        if revenue_ceiling is not None and revenue_ceiling > 0:
            ceiling = float(revenue_ceiling)
            if aggressive > ceiling:
                capacity_clip_note = (
                    f"Market Capacity ceiling applied: aggressive scenario "
                    f"${aggressive:,} exceeded realistic ceiling ${ceiling:,.0f} "
                    f"— clipped to ceiling.")
                aggressive = int(ceiling)
            if likely > aggressive:
                likely = aggressive
            if conservative > likely:
                conservative = likely

        # Economics
        startup, maintenance, ttfr, auto_pct, econ_expl = self._economics(
            dna, automation_fit, business_count, asset_type)

        monthly_profit = likely - maintenance
        roi = (round(startup / monthly_profit, 1)
               if monthly_profit > 0 and startup > 0 else 999.0)

        # Scoring
        confidence, conf_expl = self._confidence(
            data_quality, competition, demand, weakness, len(active))
        risk, risk_expl = self._risk_score(
            competition, len(active), business_count, data_quality)
        build, build_expl = self._build_score(
            confidence, likely, startup, maintenance, auto_pct)
        grade, grade_expl = self._investment_grade(build, risk)
        diversity = self._monetization_diversity(active)

        # Venture projections
        five_year, exit_val, venture_expl = self._venture(likely, build)

        # Revenue explanation
        rev_expl = self._revenue_explanation(
            business_count, competition, demand, data_quality,
            competition_mult, demand_mult, stream_calcs,
            conservative, likely, aggressive)

        # Notes
        notes = self._notes(
            dna, data_quality, business_count, competition, demand,
            active, roi, likely, five_year, exit_val)
        if capacity_clip_note:
            notes.insert(0, capacity_clip_note)

        # Summary sentence
        grade_label = {"A": "strong opportunity", "B": "viable opportunity",
                        "C": "marginal opportunity", "D": "avoid or defer"}.get(grade, "")
        summary = (
            f"Grade {grade} {grade_label}. "
            f"Likely ${likely:,}/mo at 18-month maturity "
            f"(conservative ${conservative:,}, aggressive ${aggressive:,}). "
            f"5-year gross ${five_year:,}. Exit estimate ${exit_val:,}. "
            f"Build score {build:.0f}/100, risk {risk:.0f}/100, confidence {confidence:.0f}%.")

        explanation = ValuationExplanation(
            revenue=rev_expl,
            confidence=conf_expl,
            risk=risk_expl,
            build_score=build_expl,
            investment_grade=grade_expl,
            economics=econ_expl,
            venture=venture_expl,
            summary=summary,
        )

        return ValuationResult(
            conservative_monthly_revenue=conservative,
            likely_monthly_revenue=likely,
            aggressive_monthly_revenue=aggressive,
            revenue_low=conservative,
            revenue_likely=likely,
            revenue_high=aggressive,
            revenue_midpoint=likely,
            five_year_revenue_potential=five_year,
            estimated_exit_value=exit_val,
            revenue_confidence=confidence,
            risk_score=risk,
            build_score=build,
            investment_grade=grade,
            monetization_diversity_score=diversity,
            startup_cost=startup,
            maintenance_cost=maintenance,
            time_to_first_revenue_days=ttfr,
            automation_percentage=auto_pct,
            roi_months=roi,
            streams=streams,
            valuation_notes=notes,
            explanation=explanation,
        )

    # ── Stream valuation ──────────────────────────────────────────────────────

    def _value_streams(
            self, dna: OpportunityDNA, business_count: int,
            competition_mult: float, demand_mult: float,
            data_quality: str) -> tuple[list[StreamValuation], list[StreamCalculation]]:

        if not dna.commercial or not dna.commercial.streams:
            base = int(80 * demand_mult * competition_mult)
            sv = StreamValuation(
                stream="ads",
                monthly_low=int(base * _SCENARIO_CONSERVATIVE),
                monthly_likely=base,
                monthly_high=int(base * _SCENARIO_AGGRESSIVE),
                strength="unknown",
                basis="No commercial DNA declared — minimal ad floor.",
                active=True)
            sc = StreamCalculation(
                stream="ads", dna_range_low=80, dna_range_high=80, strength="unknown",
                strength_capture_pct=1.0, maturity_capture_pct=_MATURITY_CAPTURE_DEFAULT,
                demand_multiplier=demand_mult, competition_multiplier=competition_mult,
                maturity_estimate_low=int(80 * demand_mult),
                maturity_estimate_high=base,
                scenario_conservative=int(base * _SCENARIO_CONSERVATIVE),
                scenario_likely_pre_discount=base,
                scenario_aggressive_pre_discount=int(base * _SCENARIO_AGGRESSIVE),
                final_conservative=int(base * _SCENARIO_CONSERVATIVE),
                final_likely=base,
                final_aggressive=int(base * _SCENARIO_AGGRESSIVE),
                active=True)
            return [sv], [sc]

        valuations: list[StreamValuation] = []
        calculations: list[StreamCalculation] = []

        for s in dna.commercial.streams:
            strength_cap = _STRENGTH_CAPTURE.get(s.strength, 0.35)
            maturity_cap = _MATURITY_CAPTURE.get(s.stream, _MATURITY_CAPTURE_DEFAULT)

            # Premium listing: blend supply model with DNA range
            pl_supply_low = pl_supply_high = None
            pl_dna_low = pl_dna_high = None
            pl_blended_low = pl_blended_high = None

            if s.stream == "premium_listings" and business_count > 0:
                pl_supply_low  = int(business_count * _PL_MATURITY_CONV_LOW  * _PL_PRICE_LOW)
                pl_supply_high = int(business_count * _PL_MATURITY_CONV_HIGH * _PL_PRICE_HIGH)
                pl_dna_low     = s.typical_monthly_range_low
                pl_dna_high    = s.typical_monthly_range_high
                raw_low  = int((pl_supply_low  + pl_dna_low)  / 2)
                raw_high = int((pl_supply_high + pl_dna_high) / 2)
                pl_blended_low  = raw_low
                pl_blended_high = raw_high
                basis = (
                    f"Supply blend: {business_count} businesses × "
                    f"{int(_PL_MATURITY_CONV_LOW*100)}–{int(_PL_MATURITY_CONV_HIGH*100)}% "
                    f"conv × ${_PL_PRICE_LOW}–${_PL_PRICE_HIGH}/mo "
                    f"blended with DNA ${pl_dna_low}–${pl_dna_high}")
            else:
                raw_low  = s.typical_monthly_range_low
                raw_high = s.typical_monthly_range_high
                basis = (
                    f"DNA ${raw_low}–${raw_high} "
                    f"× {int(strength_cap*100)}% strength "
                    f"× {int(maturity_cap*100)}% maturity capture "
                    f"({s.strength.value})")

            # Maturity estimates (before scenario splits)
            mat_high = int(raw_high * strength_cap * maturity_cap * demand_mult * competition_mult)
            mat_low  = int(raw_low  * strength_cap * maturity_cap * demand_mult)
            mat_low  = min(mat_low, mat_high)

            # Scenario splits
            conserv_pre    = int(mat_low  * _SCENARIO_CONSERVATIVE)
            likely_pre     = int(mat_high * _SCENARIO_LIKELY)
            aggressive_pre = int(mat_high * _SCENARIO_AGGRESSIVE)

            # Heuristic discounts
            h_likely_disc = h_agg_disc = None
            conserv    = conserv_pre
            likely_f   = likely_pre
            aggressive_f = aggressive_pre
            if data_quality == "heuristic":
                h_likely_disc = _HEURISTIC_LIKELY_DISCOUNT
                h_agg_disc    = _HEURISTIC_AGGRESSIVE_DISCOUNT
                likely_f     = int(likely_pre     * _HEURISTIC_LIKELY_DISCOUNT)
                aggressive_f = int(aggressive_pre * _HEURISTIC_AGGRESSIVE_DISCOUNT)

            conserv      = max(conserv, 0)
            likely_f     = max(likely_f,     conserv)
            aggressive_f = max(aggressive_f, likely_f)

            active = not (data_quality == "heuristic" and s.strength == Intensity.VERY_LOW)
            excluded_reason = (
                "Excluded from heuristic estimate: very_low strength is too speculative."
                if not active else "")

            valuations.append(StreamValuation(
                stream=s.stream,
                monthly_low=conserv,
                monthly_likely=likely_f,
                monthly_high=aggressive_f,
                strength=s.strength.value,
                basis=basis,
                active=active))

            calculations.append(StreamCalculation(
                stream=s.stream,
                dna_range_low=s.typical_monthly_range_low,
                dna_range_high=s.typical_monthly_range_high,
                strength=s.strength.value,
                strength_capture_pct=round(strength_cap * 100, 1),
                maturity_capture_pct=round(maturity_cap * 100, 1),
                demand_multiplier=round(demand_mult, 3),
                competition_multiplier=round(competition_mult, 3),
                pl_supply_low=pl_supply_low,
                pl_supply_high=pl_supply_high,
                pl_dna_low=pl_dna_low,
                pl_dna_high=pl_dna_high,
                pl_blended_low=pl_blended_low,
                pl_blended_high=pl_blended_high,
                maturity_estimate_low=mat_low,
                maturity_estimate_high=mat_high,
                scenario_conservative=conserv_pre,
                scenario_likely_pre_discount=likely_pre,
                scenario_aggressive_pre_discount=aggressive_pre,
                heuristic_likely_discount_applied=h_likely_disc,
                heuristic_aggressive_discount_applied=h_agg_disc,
                final_conservative=conserv,
                final_likely=likely_f,
                final_aggressive=aggressive_f,
                active=active,
                excluded_reason=excluded_reason))

        return valuations, calculations

    # ── Revenue explanation ───────────────────────────────────────────────────

    def _revenue_explanation(
            self, business_count: int, competition: float, demand: float,
            data_quality: str, competition_mult: float, demand_mult: float,
            stream_calcs: list[StreamCalculation],
            conservative: int, likely: int, aggressive: int) -> RevenueExplanation:

        included = [c for c in stream_calcs if c.active]
        excluded = [c for c in stream_calcs if not c.active]

        adj: list[str] = []
        if data_quality == "heuristic":
            adj.append(
                f"Heuristic mode: likely scenario discounted "
                f"{int((1 - _HEURISTIC_LIKELY_DISCOUNT)*100)}%, "
                f"aggressive discounted {int((1 - _HEURISTIC_AGGRESSIVE_DISCOUNT)*100)}%.")
        if excluded:
            adj.append(
                f"{len(excluded)} stream(s) excluded: "
                + "; ".join(c.stream for c in excluded)
                + f" ({excluded[0].excluded_reason if excluded else ''})")

        return RevenueExplanation(
            business_count=business_count,
            competition_score=competition,
            demand_score=demand,
            data_quality=data_quality,
            competition_multiplier=round(competition_mult, 3),
            competition_multiplier_formula=(
                f"max({_COMPETITION_FLOOR}, "
                f"1.0 - ({competition:.0f}/100) × {_COMPETITION_MAX_DRAG}) "
                f"= {competition_mult:.3f}"),
            demand_multiplier=round(demand_mult, 3),
            demand_multiplier_formula=(
                f"{_DEMAND_LIFT_BASE} + ({demand:.0f}/100) × {_DEMAND_LIFT_RANGE} "
                f"= {demand_mult:.3f}"),
            stream_calculations=stream_calcs,
            streams_included=len(included),
            streams_excluded=len(excluded),
            gross_conservative=sum(c.final_conservative for c in included),
            gross_likely=sum(c.final_likely       for c in included),
            gross_aggressive=sum(c.final_aggressive for c in included),
            aggregate_adjustments=adj,
            final_conservative=conservative,
            final_likely=likely,
            final_aggressive=aggressive,
        )

    # ── Economics ─────────────────────────────────────────────────────────────

    def _economics(self, dna: OpportunityDNA, automation_fit: float,
                    business_count: int,
                    asset_type: str) -> tuple[float, float, int, float, EconomicsExplanation]:

        regulated     = bool(dna.commercial and dna.commercial.regulated)
        content_heavy = bool(
            dna.intent and dna.intent.content_appetite
            in (Intensity.HIGH, Intensity.VERY_HIGH, Intensity.EXTREME))
        high_lead_val = bool(
            dna.commercial and dna.commercial.lead_value
            in (Intensity.HIGH, Intensity.VERY_HIGH, Intensity.EXTREME))

        _BASE_STARTUP      = 150.0
        _REGULATED_STARTUP = 400.0
        _COMPLEX_STARTUP   = 250.0
        _LARGE_DATA_STARTUP = 100.0
        _BASE_MAINTENANCE       = 20.0
        _CONTENT_MAINTENANCE    = 40.0
        _REGULATED_MAINTENANCE  = 30.0
        _LEAD_VAL_MAINTENANCE   = 20.0
        _BASE_TTFR = 21

        startup = _BASE_STARTUP
        startup_adds: list[str] = [f"Base directory setup: ${_BASE_STARTUP:.0f}"]

        if regulated:
            startup += _REGULATED_STARTUP
            startup_adds.append(
                f"Regulated market (licensing, compliance, legal review): +${_REGULATED_STARTUP:.0f}")
        if asset_type in ("marketplace", "lead_gen"):
            startup += _COMPLEX_STARTUP
            startup_adds.append(
                f"Complex asset type ({asset_type}) — additional build work: +${_COMPLEX_STARTUP:.0f}")
        if business_count > 200:
            startup += _LARGE_DATA_STARTUP
            startup_adds.append(
                f"Large data import ({business_count} businesses to enrich): +${_LARGE_DATA_STARTUP:.0f}")

        maintenance = _BASE_MAINTENANCE
        maint_adds: list[str] = [f"Base hosting + tools: ${_BASE_MAINTENANCE:.0f}/mo"]

        if content_heavy:
            maintenance += _CONTENT_MAINTENANCE
            maint_adds.append(
                f"Content-heavy market (high content_appetite in DNA) "
                f"— ongoing writing / updating: +${_CONTENT_MAINTENANCE:.0f}/mo")
        if regulated:
            maintenance += _REGULATED_MAINTENANCE
            maint_adds.append(
                f"Regulated market — ongoing compliance monitoring: +${_REGULATED_MAINTENANCE:.0f}/mo")
        if high_lead_val:
            maintenance += _LEAD_VAL_MAINTENANCE
            maint_adds.append(
                f"High lead-value market — lead qualification overhead: +${_LEAD_VAL_MAINTENANCE:.0f}/mo")

        auto_pct = float(max(50.0, min(98.0, automation_fit)))
        auto_source = (
            f"Clamped automation_fit_score {automation_fit:.0f} "
            f"to [{50}, {98}] range → {auto_pct:.0f}%")

        ttfr = _BASE_TTFR
        ttfr_adds: list[str] = [f"Base (pre-sell 3-5 listings): {_BASE_TTFR} days"]
        if regulated:
            ttfr += 30
            ttfr_adds.append("Regulated market (licensing delay): +30 days")
        if content_heavy:
            ttfr += 14
            ttfr_adds.append("Content-heavy market (SEO ramp): +14 days")
        if high_lead_val:
            ttfr = max(14, ttfr - 7)
            ttfr_adds.append("High lead-value market (can monetize leads early): -7 days (floor 14)")

        expl = EconomicsExplanation(
            base_startup=_BASE_STARTUP,
            startup_additions=startup_adds,
            total_startup=startup,
            base_maintenance=_BASE_MAINTENANCE,
            maintenance_additions=maint_adds,
            total_maintenance=maintenance,
            automation_pct=auto_pct,
            automation_source=auto_source,
            ttfr_base=_BASE_TTFR,
            ttfr_adjustments=ttfr_adds,
            ttfr_final=ttfr,
        )
        return startup, maintenance, ttfr, auto_pct, expl

    # ── Confidence ────────────────────────────────────────────────────────────

    def _confidence(self, data_quality: str, competition: float,
                     demand: float, weakness: float,
                     active_stream_count: int) -> tuple[float, ConfidenceExplanation]:

        base = _CONFIDENCE_BASE.get(data_quality, 38.0)
        base_rationale = (
            f"Data quality '{data_quality}' → base {base:.0f} "
            f"(verified=78, mixed=58, heuristic=38)")

        components: list[ConfidenceComponent] = [
            ConfidenceComponent(
                label="Strong search demand",
                condition=f"demand_score {demand:.0f} ≥ 60",
                applied=demand >= 60,
                adjustment=5.0),
            ConfidenceComponent(
                label="Low competition",
                condition=f"competition_score {competition:.0f} ≤ 40",
                applied=competition <= 40,
                adjustment=5.0),
            ConfidenceComponent(
                label="Weak incumbent directories",
                condition=f"directory_weakness_score {weakness:.0f} ≥ 60",
                applied=weakness >= 60,
                adjustment=4.0),
            ConfidenceComponent(
                label="Diversified revenue (≥3 streams)",
                condition=f"active streams {active_stream_count} ≥ 3",
                applied=active_stream_count >= 3,
                adjustment=3.0),
            ConfidenceComponent(
                label="Single-stream concentration penalty",
                condition=f"active streams {active_stream_count} = 1",
                applied=active_stream_count == 1,
                adjustment=-5.0),
        ]

        raw_total = base + sum(c.adjustment for c in components if c.applied)

        cap = None
        cap_reason = None
        if data_quality == "heuristic":
            cap = _CONFIDENCE_HEURISTIC_CAP
            cap_reason = (
                f"Heuristic mode hard cap: {_CONFIDENCE_HEURISTIC_CAP}. "
                "No live market data has been verified. "
                "Run Scout to lift the cap.")
        final = min(round(raw_total, 1),
                     cap if cap is not None else _CONFIDENCE_MAX)

        expl = ConfidenceExplanation(
            data_quality=data_quality,
            base_score=base,
            base_score_rationale=base_rationale,
            components=components,
            raw_total=round(raw_total, 1),
            cap_applied=cap,
            cap_reason=cap_reason,
            final_confidence=final,
        )
        return final, expl

    # ── Risk score ────────────────────────────────────────────────────────────

    def _risk_score(self, competition: float, active_stream_count: int,
                     business_count: int,
                     data_quality: str) -> tuple[float, RiskExplanation]:

        competition_risk = competition

        if active_stream_count == 0:
            concentration_risk = 100.0
            conc_rationale = "No active revenue streams — total concentration risk."
        elif active_stream_count == 1:
            concentration_risk = 70.0
            conc_rationale = "1 stream — single-stream dependence, high fragility."
        elif active_stream_count == 2:
            concentration_risk = 45.0
            conc_rationale = "2 streams — moderate; one failure is meaningful."
        elif active_stream_count == 3:
            concentration_risk = 25.0
            conc_rationale = "3 streams — reasonably diversified."
        else:
            concentration_risk = 10.0
            conc_rationale = f"{active_stream_count} streams — well-diversified."

        if business_count == 0:
            supply_risk = 90.0
            supply_rationale = "No businesses found — directory has no listing supply."
        elif business_count < _RISK_SUPPLY_THIN_THRESHOLD:
            supply_risk = max(30.0,
                90.0 - (business_count / _RISK_SUPPLY_THIN_THRESHOLD) * 60.0)
            supply_rationale = (
                f"{business_count} businesses < threshold {_RISK_SUPPLY_THIN_THRESHOLD} "
                f"— thin supply, premium listing revenue limited.")
        elif business_count < 100:
            supply_risk = 20.0
            supply_rationale = f"{business_count} businesses — adequate supply."
        else:
            supply_risk = 8.0
            supply_rationale = f"{business_count} businesses — strong supply."

        dq_risk = {"heuristic": 70.0, "mixed": 40.0, "verified": 10.0}.get(
            data_quality, 70.0)
        dq_rationale = (
            f"Data quality '{data_quality}': "
            f"heuristic=70, mixed=40, verified=10 → {dq_risk:.0f}")

        components = [
            RiskComponent(
                label="Competition risk",
                raw_value=competition_risk,
                weight=_RISK_COMPETITION_WEIGHT,
                weighted_contribution=round(competition_risk * _RISK_COMPETITION_WEIGHT, 2),
                rationale=f"competition_score {competition:.0f}/100 directly as risk input"),
            RiskComponent(
                label="Revenue concentration risk",
                raw_value=concentration_risk,
                weight=_RISK_CONCENTRATION_WEIGHT,
                weighted_contribution=round(concentration_risk * _RISK_CONCENTRATION_WEIGHT, 2),
                rationale=conc_rationale),
            RiskComponent(
                label="Supply risk",
                raw_value=supply_risk,
                weight=_RISK_SUPPLY_WEIGHT,
                weighted_contribution=round(supply_risk * _RISK_SUPPLY_WEIGHT, 2),
                rationale=supply_rationale),
            RiskComponent(
                label="Data quality risk",
                raw_value=dq_risk,
                weight=_RISK_DATA_QUALITY_WEIGHT,
                weighted_contribution=round(dq_risk * _RISK_DATA_QUALITY_WEIGHT, 2),
                rationale=dq_rationale),
        ]

        total = sum(c.weighted_contribution for c in components)
        total = round(min(total, 100.0), 1)

        return total, RiskExplanation(components=components, total_risk=total)

    # ── Build score ───────────────────────────────────────────────────────────

    def _build_score(self, confidence: float, likely_monthly: int,
                      startup: float, maintenance: float,
                      automation_pct: float) -> tuple[float, BuildScoreExplanation]:

        _WEIGHT_REVENUE    = 0.40
        _WEIGHT_CONFIDENCE = 0.30
        _WEIGHT_AUTOMATION = 0.20
        _WEIGHT_COST       = 0.10
        _REVENUE_TARGET    = 1000   # $1,000/mo likely = 100 pts on log scale

        rev_score = min(100.0, max(0.0,
            math.log10(max(likely_monthly, 1) + 1)
            / math.log10(_REVENUE_TARGET + 1) * 100))
        cost_score = max(0.0, min(100.0, (1000 - startup) / 8))

        raw = (rev_score     * _WEIGHT_REVENUE
                + confidence   * _WEIGHT_CONFIDENCE
                + automation_pct * _WEIGHT_AUTOMATION
                + cost_score   * _WEIGHT_COST)
        final = round(min(raw, 100.0), 1)

        components = [
            BuildScoreComponent(
                label="Revenue potential",
                raw_value=round(rev_score, 2),
                weight=_WEIGHT_REVENUE,
                weighted_contribution=round(rev_score * _WEIGHT_REVENUE, 2),
                calculation=(
                    f"log10({likely_monthly}+1) / log10({_REVENUE_TARGET}+1) × 100 "
                    f"= {rev_score:.1f} pts "
                    f"(${_REVENUE_TARGET}/mo = 100 pts reference)")),
            BuildScoreComponent(
                label="Confidence score",
                raw_value=confidence,
                weight=_WEIGHT_CONFIDENCE,
                weighted_contribution=round(confidence * _WEIGHT_CONFIDENCE, 2),
                calculation=f"confidence {confidence:.1f} × {_WEIGHT_CONFIDENCE}"),
            BuildScoreComponent(
                label="Automation fit",
                raw_value=automation_pct,
                weight=_WEIGHT_AUTOMATION,
                weighted_contribution=round(automation_pct * _WEIGHT_AUTOMATION, 2),
                calculation=f"automation_pct {automation_pct:.0f}% × {_WEIGHT_AUTOMATION}"),
            BuildScoreComponent(
                label="Cost efficiency",
                raw_value=round(cost_score, 2),
                weight=_WEIGHT_COST,
                weighted_contribution=round(cost_score * _WEIGHT_COST, 2),
                calculation=(
                    f"(1000 - ${startup:.0f}) / 8 = {cost_score:.1f} pts "
                    f"(startup <$200 = 100 pts, >$1000 = 0 pts)")),
        ]

        return final, BuildScoreExplanation(
            components=components, raw_total=round(raw, 2), final_build_score=final)

    # ── Investment grade ──────────────────────────────────────────────────────

    def _investment_grade(self, build_score: float,
                           risk_score: float) -> tuple[str, InvestmentGradeExplanation]:

        grade_score = round(
            (build_score * _GRADE_WEIGHT_BUILD)
            + ((100.0 - risk_score) * _GRADE_WEIGHT_RISK), 2)

        if grade_score >= _GRADE_A_FLOOR:
            grade = "A"
            threshold = f"≥ {_GRADE_A_FLOOR} → A"
        elif grade_score >= _GRADE_B_FLOOR:
            grade = "B"
            threshold = f"≥ {_GRADE_B_FLOOR} → B"
        elif grade_score >= _GRADE_C_FLOOR:
            grade = "C"
            threshold = f"≥ {_GRADE_C_FLOOR} → C"
        else:
            grade = "D"
            threshold = f"< {_GRADE_C_FLOOR} → D"

        expl = InvestmentGradeExplanation(
            build_score=build_score,
            risk_score=risk_score,
            grade_score_formula=(
                f"({build_score:.1f} × {_GRADE_WEIGHT_BUILD}) "
                f"+ ((100 - {risk_score:.1f}) × {_GRADE_WEIGHT_RISK}) "
                f"= {grade_score:.2f}"),
            grade_score=grade_score,
            threshold_applied=threshold,
            grade=grade,
        )
        return grade, expl

    # ── Monetization diversity ────────────────────────────────────────────────

    def _monetization_diversity(self, active_streams: list[StreamValuation]) -> float:
        if not active_streams:
            return 0.0
        str_to_num = {
            "extreme": 1.00, "very_high": 0.85, "high": 0.65,
            "medium": 0.45, "low": 0.20, "very_low": 0.08, "unknown": 0.35,
        }
        pts_per_stream = 100.0 / _DIVERSITY_STREAM_CAP
        total = sum(
            str_to_num.get(s.strength, 0.35) * pts_per_stream
            for s in active_streams)
        return round(min(total, 100.0), 1)

    # ── Venture projections ───────────────────────────────────────────────────

    def _venture(self, likely_monthly: int,
                  build_score: float) -> tuple[int, int, VentureExplanation]:

        yearly_lines: list[str] = []
        five_year_total = 0
        for i, fraction in enumerate(_FIVE_YEAR_RAMP, start=1):
            annual = int(likely_monthly * fraction) * 12
            five_year_total += annual
            yearly_lines.append(
                f"Year {i}: ${likely_monthly} × {fraction:.2f} × 12 months = ${annual:,}")

        if build_score >= 75:
            exit_multiple = _EXIT_MULTIPLE_PREMIUM
            exit_rationale = (
                f"build_score {build_score:.0f} ≥ 75 → premium multiple "
                f"{_EXIT_MULTIPLE_PREMIUM}× "
                f"(proven, automated, diversified asset)")
        elif build_score >= 55:
            exit_multiple = _EXIT_MULTIPLE_STANDARD
            exit_rationale = (
                f"build_score {build_score:.0f} in 55–74 → standard multiple "
                f"{_EXIT_MULTIPLE_STANDARD}× "
                f"(solid asset, some risk)")
        else:
            exit_multiple = _EXIT_MULTIPLE_BASIC
            exit_rationale = (
                f"build_score {build_score:.0f} < 55 → basic multiple "
                f"{_EXIT_MULTIPLE_BASIC}× "
                f"(speculative or low-quality asset)")

        exit_val = int(likely_monthly * exit_multiple)

        expl = VentureExplanation(
            likely_monthly=likely_monthly,
            five_year_ramp=yearly_lines,
            five_year_total=five_year_total,
            exit_multiple=exit_multiple,
            exit_multiple_rationale=exit_rationale,
            exit_value=exit_val,
        )
        return five_year_total, exit_val, expl

    # ── Notes ─────────────────────────────────────────────────────────────────

    def _notes(self, dna: OpportunityDNA, data_quality: str,
                business_count: int, competition: float, demand: float,
                active_streams: list, roi_months: float,
                likely_monthly: int, five_year: int, exit_val: int) -> list[str]:
        notes: list[str] = []
        conserv    = sum(s.monthly_low   for s in active_streams)
        aggressive = sum(s.monthly_high  for s in active_streams)
        notes.append(
            f"12–24 month potential: conservative ${conserv}/mo · "
            f"likely ${likely_monthly}/mo · aggressive ${aggressive}/mo. "
            f"5-year gross: ${five_year:,}. Exit estimate: ${exit_val:,}.")
        if data_quality == "heuristic":
            notes.append(
                "Heuristic mode: likely discounted 15%, aggressive 30%. "
                "Run Scout to unlock verified projections.")
        if business_count < _RISK_SUPPLY_THIN_THRESHOLD:
            notes.append(
                f"Thin supply ({business_count} businesses) limits premium listing "
                "revenue. Verify before committing build capital.")
        elif business_count >= 100:
            notes.append(
                f"Strong supply ({business_count} businesses) supports premium "
                "listing conversion at scale.")
        if competition >= 70:
            notes.append(
                f"High competition ({competition:.0f}/100) — "
                "competition multiplier reduces projections.")
        elif competition <= 30:
            notes.append(
                f"Low competition ({competition:.0f}/100) — favorable capture rate applied.")
        if demand >= 70:
            notes.append(
                f"Strong demand ({demand:.0f}/100) — demand lift applied across all streams.")
        if roi_months <= 6:
            notes.append(
                f"Fast ROI: ~{roi_months} months to recoup startup at likely run rate.")
        elif roi_months >= 24:
            notes.append(
                f"Long ROI (~{roi_months:.0f} months). "
                "Pre-selling listings before launch accelerates payback.")
        n = len(active_streams)
        if n >= 4:
            names = ", ".join(s.stream for s in active_streams[:3])
            notes.append(
                f"{n} active revenue streams ({names} + more) — diversified.")
        elif n == 1:
            notes.append(
                f"Single active stream ({active_streams[0].stream}). "
                "A second stream significantly reduces risk.")
        if dna.commercial and dna.commercial.regulated:
            notes.append(
                "Regulated market — compliance overhead included in cost estimates.")
        return notes
