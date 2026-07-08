"""
business_architect.py — Venture Studio decision layer.

Consumes OpportunityDNA + ValuationEngine, returns DecisionResult.

Architecture:
- No Flask, no SQL, no routes.
- Pure service: takes data, returns data.
- Passes the ValuationExplanation through unchanged as a serialized dict.

Honest data-quality wall:
    heuristic  -> confidence capped at 45, BUILD downgraded to TEST
    verified   -> BUILD allowed, confidence uncapped
"""

from __future__ import annotations

import dataclasses
from typing import Any, Optional

from .dna.schema import OpportunityDNA, Intensity
from .models import DecisionResult
from .valuation_engine import ValuationEngine, ValuationResult


_INTENSITY_TO_NUM = {
    Intensity.VERY_LOW: 10, Intensity.LOW: 30, Intensity.MEDIUM: 50,
    Intensity.HIGH: 70, Intensity.VERY_HIGH: 88, Intensity.EXTREME: 98,
}
_INTENSITY_LABEL = {
    Intensity.VERY_LOW: "very_low", Intensity.LOW: "low",
    Intensity.MEDIUM: "medium", Intensity.HIGH: "high",
    Intensity.VERY_HIGH: "very_high", Intensity.EXTREME: "extreme",
}

_valuation_engine = ValuationEngine()


def _to_dict(obj: Any) -> Any:
    """Recursively convert dataclasses to plain dicts for JSON serialization."""
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {k: _to_dict(v) for k, v in dataclasses.asdict(obj).items()}
    if isinstance(obj, list):
        return [_to_dict(i) for i in obj]
    if isinstance(obj, dict):
        return {k: _to_dict(v) for k, v in obj.items()}
    return obj


class BusinessArchitect:
    def __init__(self, dna: OpportunityDNA):
        self.dna = dna

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _has_strong_stream(self, stream_name: str) -> bool:
        if not self.dna.commercial:
            return False
        return any(
            s.stream == stream_name
            and s.strength in (Intensity.HIGH, Intensity.VERY_HIGH, Intensity.EXTREME)
            for s in self.dna.commercial.streams)

    def _strongest_stream(self):
        if not self.dna.commercial or not self.dna.commercial.streams:
            return None
        return max(self.dna.commercial.streams,
                    key=lambda s: _INTENSITY_TO_NUM.get(s.strength, 50))

    def _business_model(self, ctx: dict, valuation: ValuationResult) -> str:
        asset = ctx.get("asset_type", "directory")
        if self.dna.business_model_options:
            top = max(self.dna.business_model_options,
                       key=lambda o: _INTENSITY_TO_NUM.get(o.fit, 50))
            primary = top.offering
            if top.typical_price_or_cut:
                primary += f" ({top.typical_price_or_cut})"
        else:
            strongest = self._strongest_stream()
            primary = strongest.stream.replace("_", " ") if strongest else "display ads"
        active = [s.stream.replace("_", " ") for s in valuation.streams if s.active][:3]
        secondary = ", ".join(active) if active else "ads"
        return f"Primary: {primary} on a {asset}. Supporting streams: {secondary}."

    def _moat(self, ctx: dict, gravity: str) -> str:
        parts = []
        if ctx.get("directory_weakness_score", 0) >= 65:
            parts.append("weak incumbents create a replacement opening")
        if ctx.get("automation_fit_score", 0) >= 80:
            parts.append("high automation enables faster, deeper content than manual competitors")
        if gravity == "core":
            parts.append("core market gravity anchors adjacent ecosystem opportunities")
        if self._has_strong_stream("premium_listings"):
            parts.append("first-mover listing relationships create switching costs")
        if not parts:
            parts.append("programmatic scale across many long-tail pages")
        return "Defensibility: " + "; ".join(parts) + "."

    def _portfolio_fit(self, ctx: dict) -> str:
        node_name = ctx.get("ecosystem_node_name")
        adj = []
        if node_name:
            for e in self.dna.ecosystem_edges:
                if e.from_node == node_name and e.strength in (
                        Intensity.HIGH, Intensity.VERY_HIGH):
                    adj.append(e.to_node)
        if adj:
            return (f"Fits a {self.dna.display_name} portfolio; "
                    f"natural expansion into {', '.join(adj[:3])}.")
        return (f"Standalone asset in the {self.dna.display_name} market; "
                f"shares audience with adjacent ecosystem nodes.")

    def _related(self, node_name: Optional[str], gravity: str) -> list[dict]:
        related: list[dict] = []
        seen: set[str] = set()
        if node_name:
            for e in self.dna.ecosystem_edges:
                other = (e.to_node if e.from_node == node_name
                          else e.from_node if e.to_node == node_name else None)
                if other and other not in seen:
                    seen.add(other)
                    related.append({"node": other, "relationship": e.edge_type.value})
        if not related:
            for n in self.dna.ecosystem_nodes:
                if n.name == node_name or n.name in seen:
                    continue
                if n.gravity == gravity:
                    seen.add(n.name)
                    related.append({"node": n.name, "relationship": "same_gravity_tier"})
        return related[:10]

    # ── Main entry point ──────────────────────────────────────────────────────

    def generate_decision(self, opportunity_name: str,
                           opportunity_context: dict) -> DecisionResult:
        ctx          = opportunity_context or {}
        data_quality = ctx.get("data_quality", "heuristic")
        asset_type   = ctx.get("asset_type", "directory")

        valuation = _valuation_engine.value(self.dna, ctx)

        node_name    = ctx.get("ecosystem_node_name")
        node         = next((n for n in self.dna.ecosystem_nodes
                              if n.name == node_name), None) if node_name else None
        gravity      = node.gravity if node else "secondary"
        intent_level = (_INTENSITY_LABEL.get(self.dna.intent.commercial_intent, "medium")
                         if self.dna.intent else "medium")

        auto_factor = valuation.automation_percentage / 100.0
        pref_weight = self.dna.asset_weight(asset_type) / 100.0
        affinity    = round(auto_factor * pref_weight, 4)

        likely = valuation.likely_monthly_revenue

        # Reasoning
        reasoning: list[str] = []
        if valuation.startup_cost <= 200:
            reasoning.append("Low startup cost — limited downside exposure.")
        else:
            reasoning.append(
                f"Startup cost ${valuation.startup_cost:,.0f} reflects "
                "market complexity (regulated or content-heavy).")
        if valuation.automation_percentage >= 85:
            reasoning.append("High automation fit — pipeline handles most of the build.")
        if gravity == "core":
            reasoning.append("Core market position — anchors surrounding ecosystem.")
        if ctx.get("directory_weakness_score", 0) >= 65:
            reasoning.append("Weak incumbent directories — genuine replacement opportunity.")
        if ctx.get("competition_score", 100) <= 40:
            reasoning.append("Low competition — above-average traffic capture expected.")
        if valuation.time_to_first_revenue_days <= 21:
            reasoning.append("Fast path to first revenue via pre-sellable listings.")
        if valuation.roi_months <= 6:
            reasoning.append(
                f"Strong ROI: {valuation.roi_months} months to recoup startup cost.")
        if valuation.investment_grade in ("A", "B"):
            reasoning.append(
                f"Investment grade {valuation.investment_grade} — "
                f"5-year potential ${valuation.five_year_revenue_potential:,}, "
                f"exit estimate ${valuation.estimated_exit_value:,}.")
        reasoning.extend(valuation.valuation_notes)

        # Warnings
        warnings: list[str] = []
        if valuation.startup_cost > 500:
            warnings.append("Elevated startup cost — regulated or complex build.")
        if valuation.automation_percentage < 70:
            warnings.append("Lower automation — ongoing manual maintenance required.")
        if valuation.risk_score >= 60:
            warnings.append(
                f"Elevated risk score ({valuation.risk_score:.0f}/100). "
                "Verify supply and competition before committing capital.")
        business_count = ctx.get("business_count")
        if business_count is not None and business_count < 25:
            warnings.append(
                f"Thin business supply ({business_count}) — verify before building.")
        if data_quality == "heuristic":
            warnings.append(
                "All scores are heuristic estimates. "
                "Confidence capped at 45% and BUILD disabled until Scout verifies the market.")

        # Verdict
        blocking = [w for w in warnings if not w.startswith("All scores")]
        strong_signals = (
            ctx.get("competition_score", 100) <= 45
            and ctx.get("search_demand_score", 0) >= 55
            and ctx.get("directory_weakness_score", 0) >= 55)

        if (affinity >= 0.65
                and intent_level in ("high", "very_high", "extreme")
                and strong_signals
                and not blocking):
            raw_rec = "BUILD"
            thesis  = (
                f"Strong automation leverage, verified demand, and beatable incumbents. "
                f"Likely ${likely:,}/mo at maturity. "
                f"5-year gross: ${valuation.five_year_revenue_potential:,}. "
                f"Exit estimate: ${valuation.estimated_exit_value:,}.")
        elif affinity >= 0.50:
            raw_rec = "TEST"
            thesis  = (
                f"Viable venture: ${valuation.conservative_monthly_revenue:,}–"
                f"${likely:,}/mo (conservative–likely). "
                f"Investment grade {valuation.investment_grade}. "
                "Verify supply and demand before committing build capital.")
        elif affinity >= 0.35:
            raw_rec = "DEFER"
            thesis  = ("Sound baseline but lower priority than current focus assets; "
                        "revisit when portfolio capacity opens up.")
        else:
            raw_rec = "REJECT"
            thesis  = ("Insufficient automation leverage, weak monetization, or excessive "
                        "operational friction for the projected return.")

        # Honest wall
        if raw_rec == "BUILD" and data_quality == "heuristic":
            raw_rec = "TEST"
            thesis  = (
                f"Strong indicators (grade {valuation.investment_grade}, "
                f"${likely:,}/mo likely, ${valuation.estimated_exit_value:,} exit est.). "
                "Run Scout to verify supply, competition, and directory quality "
                "before committing build capital.")
            reasoning.append(
                "Downgraded BUILD → TEST: Scout verification required "
                "before build commitment on heuristic data.")

        # Narrative
        customer = (self.dna.customer.buyer_description.strip().rstrip(".")
                     if self.dna.customer else self.dna.display_name)
        why_this_market = (
            f"Serves {customer}, at a {gravity}-gravity position "
            f"in the {self.dna.display_name} market.")
        signals = ", ".join(self.dna.intent.dominant_intents) if self.dna.intent else ""
        why_now = (
            f"Aligns with declared market intent signals: {signals}."
            if data_quality == "heuristic"
            else f"Matches observed high-yield search intent markers: {signals}.")

        what_to_build = []
        for dim in self.dna.search_dimensions:
            hint   = (dim.typically_produces_asset or "category").replace("_", " ")
            sample = ", ".join(dim.examples[:3])
            what_to_build.append(f"{hint} pages for '{dim.name}': {sample}")

        low_fit = sorted(self.dna.asset_preferences, key=lambda p: p.fit_weight)[:2]
        sweat   = round(max(4.0, 40.0 * (1 - valuation.automation_percentage / 100)), 1)
        what_to_ignore = [
            f"{p.asset_type} (DNA fit {p.fit_weight}/100 in this market)"
            for p in low_fit]
        what_to_ignore.append(f"Manual workflows exceeding {sweat} hrs/month.")

        # Serialize the explanation dataclass tree to a plain dict
        explanation_dict = _to_dict(valuation.explanation) if valuation.explanation else None

        return DecisionResult(
            recommendation=raw_rec,
            confidence_score=valuation.revenue_confidence,
            conviction_thesis=thesis,
            data_quality=data_quality,
            reasoning=reasoning,
            startup_cost=valuation.startup_cost,
            maintenance_cost=valuation.maintenance_cost,
            estimated_revenue_low=float(valuation.conservative_monthly_revenue),
            estimated_revenue_high=float(valuation.aggressive_monthly_revenue),
            automation_percentage=valuation.automation_percentage,
            time_to_first_revenue_days=valuation.time_to_first_revenue_days,
            conservative_monthly_revenue=float(valuation.conservative_monthly_revenue),
            likely_monthly_revenue=float(valuation.likely_monthly_revenue),
            aggressive_monthly_revenue=float(valuation.aggressive_monthly_revenue),
            revenue_midpoint=float(valuation.likely_monthly_revenue),
            revenue_likely=float(valuation.likely_monthly_revenue),
            five_year_revenue_potential=float(valuation.five_year_revenue_potential),
            estimated_exit_value=float(valuation.estimated_exit_value),
            roi_months=valuation.roi_months,
            build_score=valuation.build_score,
            risk_score=valuation.risk_score,
            investment_grade=valuation.investment_grade,
            monetization_diversity_score=valuation.monetization_diversity_score,
            business_model=self._business_model(ctx, valuation),
            moat=self._moat(ctx, gravity),
            portfolio_fit=self._portfolio_fit(ctx),
            why_this_market=why_this_market,
            why_now=why_now,
            what_to_build_first=what_to_build,
            what_to_ignore=what_to_ignore,
            next_steps=[
                "Run Scout to verify business count and competitor quality",
                "Audit top 3 ranking directories for data and UX gaps",
                "Confirm search volume with a real keyword tool",
                "Build core directory + top geo/category pages",
                "Pre-sell 3–5 premium listings before public launch",
            ],
            roadmap_30=(
                f"Launch the core {asset_type} with top geo/category pages. "
                f"Target setup under ${valuation.startup_cost:,.0f}. "
                "Outreach to 10 businesses for founding listing slots."),
            roadmap_90=(
                "Layer in SEO landing pages and content from DNA intent dimensions. "
                "Begin premium-listing sales. "
                f"Target ${valuation.conservative_monthly_revenue:,}/mo run rate."),
            roadmap_365=(
                f"Expand into adjacent ecosystem nodes in gravity order. "
                f"Hold maintenance under ${valuation.maintenance_cost:,.0f}/mo. "
                f"Target ${valuation.likely_monthly_revenue:,}/mo at portfolio maturity. "
                f"5-year gross potential: ${valuation.five_year_revenue_potential:,}."),
            internal_affinity_score=affinity,
            market_gravity_intensity=gravity,
            commercial_intent_level=intent_level,
            core_pages_to_launch_count=int(ctx.get("blueprint_total_pages", 0)),
            related_opportunities=self._related(node_name, gravity),
            warnings=warnings,
            revenue_streams=[
                {
                    "stream":  s.stream,
                    "low":     s.monthly_low,
                    "likely":  s.monthly_likely,
                    "high":    s.monthly_high,
                    "strength": s.strength,
                    "active":  s.active,
                    "basis":   s.basis,
                }
                for s in valuation.streams
            ],
            valuation_explanation=explanation_dict,
        )
