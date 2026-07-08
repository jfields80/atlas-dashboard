"""
analyzers.py — the pluggable brains behind the drill engine, plus
Phase 5 final scoring and the investment-brief output format.

Two analyzers, one interface:

HeuristicAnalyzer
    Day-one, $0, instant. Same logic family as MVP v1 but restructured
    around the drill engine's needs. Every analysis is stamped
    data_quality="heuristic" so downstream confidence stays honest.

RealDataAnalyzer
    The full pipeline: for each node it runs competitor discovery
    (Phase 2) through the search provider, audits independent
    competitors (Phase 3), and derives competition / directory-weakness
    scores from what it actually FOUND, not from word counts.
    Business counts come from an injected `business_counter` callable —
    wire your existing Google Places connector in (it returns an int
    for "how many places match this niche"). Falls back to heuristic
    for any signal it couldn't verify, and stamps data_quality
    accordingly (verified / partial).

Cost control: RealDataAnalyzer caches per-niche results and only audits
the top `max_audits_per_node` independent competitors.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

from .drill_engine import Node, NodeAnalysis
from .competitor_discovery import discover_competitors, CompetitorReport
from .quality_audit import audit_url, AuditResult
from .revenue_signals import estimate_from_signals, RevenueEstimate
from .search_provider import SearchProvider


# ---------------------------------------------------------------------------
# Heuristic analyzer (day one)
# ---------------------------------------------------------------------------

HIGH_VALUE_HINTS = ["attorney", "lawyer", "dentist", "contractor", "roofing",
                      "hvac", "plumb", "insurance", "clinic", "wedding", "hotel"]
MED_VALUE_HINTS = ["restaurant", "bakery", "gym", "salon", "barber", "coffee",
                     "farm", "shop", "martial arts"]


class HeuristicAnalyzer:
    def analyze(self, node: Node) -> NodeAnalysis:
        depth, words = node.depth, len(node.niche_name.split())
        n_dims = len(node.dimensions_used)

        # Ecosystem-sibling seeds ARE well-scoped niches already (they're
        # nodes the DNA declared as directory-worthy). Treat their
        # word-count as inherent specificity rather than shallow-depth.
        origin = getattr(node, "origin", "drill_child")
        effective_depth = depth + (1 if origin == "ecosystem_sibling" else 0)
        effective_dims = n_dims + (1 if origin == "ecosystem_sibling" else 0)

        competition = max(8.0, 95.0 - effective_depth * 18 - effective_dims * 6
                            - max(0, words - 2) * 4)
        business_count = max(4, int(400 / (1 + effective_depth * 1.6 + effective_dims)))
        search_demand = max(15.0, 90.0 - depth * 12 - max(0, words - 3) * 4)

        lowered = node.niche_name.lower()
        monetization = (85.0 if any(h in lowered for h in HIGH_VALUE_HINTS)
                         else 62.0 if any(h in lowered for h in MED_VALUE_HINTS)
                         else 48.0)

        return NodeAnalysis(
            competition=competition, business_count=business_count,
            search_demand=search_demand,
            directory_weakness=60.0,   # neutral prior until verified
            monetization=monetization,
            automation_fit=max(70.0, 95.0 - depth * 3),
            evidence=[{"source": "heuristic", "note":
                        f"depth={depth}, dims={n_dims}, words={words} — all values are structural guesses"}],
            data_quality="heuristic",
        )


# ---------------------------------------------------------------------------
# Real-data analyzer (Phases 2+3 wired into the loop)
# ---------------------------------------------------------------------------

class RealDataAnalyzer:
    def __init__(self, provider: SearchProvider,
                  business_counter: Optional[Callable[[str], int]] = None,
                  max_audits_per_node: int = 3,
                  audit_fn: Callable[[str], AuditResult] = audit_url):
        self.provider = provider
        self.business_counter = business_counter
        self.max_audits = max_audits_per_node
        self.audit_fn = audit_fn
        self.heuristic = HeuristicAnalyzer()
        self._cache: dict[str, NodeAnalysis] = {}
        self.reports: dict[str, CompetitorReport] = {}   # kept for persistence/UI

    def analyze(self, node: Node) -> NodeAnalysis:
        key = node.niche_name.lower()
        if key in self._cache:
            return self._cache[key]

        base = self.heuristic.analyze(node)  # fallback values
        evidence: list[dict] = []
        verified_bits = 0

        # --- Phase 2: competitor discovery ---------------------------------
        report = discover_competitors(node.niche_name, self.provider)
        self.reports[key] = report
        summary = report.summary()
        got_serp_data = bool(report.competitors)

        if got_serp_data:
            verified_bits += 1
            evidence.append({"source": "serp", "note":
                              f"Competitor landscape: {summary}"})

            # Competition from what's ACTUALLY on the SERP:
            n_platform = summary.get("platform_giant", 0)
            n_indep = summary.get("independent", 0)
            n_listicle = summary.get("listicle", 0)
            competition = min(96.0, 15.0 + n_platform * 7 + n_indep * 12 + n_listicle * 4)
            base.competition = competition

        # --- Phase 3: audit independent competitors ------------------------
        audits: list[AuditResult] = []
        for comp in report.independents[: self.max_audits]:
            audit = self.audit_fn(comp.url)
            comp.quality_audit = audit.__dict__
            if audit.fetched:
                audits.append(audit)
                evidence.append({"source": "audit", "url": comp.url,
                                  "note": f"Quality {audit.quality_score}/100 ({audit.grade}): "
                                           + "; ".join(audit.notes[:3])})

        if audits:
            verified_bits += 1
            avg_quality = sum(a.quality_score for a in audits) / len(audits)
            base.directory_weakness = round(100 - avg_quality, 1)
        elif got_serp_data and not report.independents:
            # SERP verified, zero independent directories = wide open
            base.directory_weakness = 88.0
            evidence.append({"source": "serp", "note":
                              "No independent directories found serving this niche — undefended."})

        # Observed monetization (feeds Phase 4)
        observed_monetization: list[str] = []
        for a in audits:
            observed_monetization.extend(a.monetization_detected)
        base.evidence = evidence + base.evidence
        base.observed_monetization = observed_monetization  # attached for orchestrator

        # --- Business count via injected Places connector ------------------
        if self.business_counter:
            try:
                count = self.business_counter(node.niche_name)
                if count is not None:
                    base.business_count = count
                    verified_bits += 1
                    evidence.append({"source": "places", "note":
                                      f"Business count verified: {count}"})
            except Exception as e:
                evidence.append({"source": "places", "note": f"Count failed: {e}"})

        base.data_quality = ("verified" if verified_bits >= 2
                              else "partial" if verified_bits == 1
                              else "heuristic")
        self._cache[key] = base
        return base


# ---------------------------------------------------------------------------
# Phase 5: final opportunity score + investment brief
# ---------------------------------------------------------------------------

WEIGHTS = {"search_demand": 0.20, "competition_inv": 0.25,
            "directory_weakness": 0.20, "business_count": 0.15,
            "monetization": 0.15, "automation_fit": 0.05}


def _business_count_to_score(count: int) -> float:
    if count >= 150: return 95.0
    if count >= 75: return 85.0
    if count >= 40: return 70.0
    if count >= 25: return 55.0
    if count >= 10: return 35.0
    return 15.0


@dataclass
class InvestmentBrief:
    niche_name: str
    lineage: str
    opportunity_score: float
    subscores: dict
    revenue: RevenueEstimate
    business_count: int
    competition_label: str
    weak_competitors: int
    independent_competitors: int
    data_quality: str
    recommendation: str
    reasons: list


def build_brief(node: Node, report: Optional[CompetitorReport] = None,
                 dna=None) -> InvestmentBrief:
    a = node.analysis
    subscores = {
        "search_demand": a.search_demand,
        "competition": a.competition,
        "directory_weakness": a.directory_weakness,
        "business_count": _business_count_to_score(a.business_count),
        "monetization": a.monetization,
        "automation_fit": a.automation_fit,
    }

    # DNA-shaded weights when a profile is loaded; falls back to defaults
    if dna is not None:
        w = dna.scoring_weights.normalized()
        weights = {
            "search_demand": w.search_demand,
            "competition_inv": w.competition,
            "directory_weakness": w.directory_weakness,
            "business_count": w.business_count,
            "monetization": w.monetization,
            "automation_fit": w.automation_fit,
        }
    else:
        weights = WEIGHTS

    score = (subscores["search_demand"] * weights["search_demand"]
              + (100 - subscores["competition"]) * weights["competition_inv"]
              + subscores["directory_weakness"] * weights["directory_weakness"]
              + subscores["business_count"] * weights["business_count"]
              + subscores["monetization"] * weights["monetization"]
              + subscores["automation_fit"] * weights["automation_fit"])
    score = round(score, 1)

    revenue = estimate_from_signals(
        getattr(a, "observed_monetization", []),
        a.business_count, a.monetization, a.data_quality)

    weak = 0
    indep = 0
    if report:
        indep = len(report.independents)
        weak = sum(1 for c in report.independents
                    if c.quality_audit and c.quality_audit.get("grade") == "weak")

    if score >= 75 and a.data_quality == "verified":
        rec = "BUILD"
    elif score >= 75:
        rec = "TEST (verify data first — score is strong but unverified)"
    elif score >= 55:
        rec = "TEST"
    elif score >= 35:
        rec = "WATCH"
    else:
        rec = "REJECT"

    comp_label = ("Low" if a.competition <= 35 else
                   "Moderate" if a.competition <= 65 else "High")

    return InvestmentBrief(
        niche_name=node.niche_name, lineage=node.lineage,
        opportunity_score=score, subscores=subscores, revenue=revenue,
        business_count=a.business_count, competition_label=comp_label,
        weak_competitors=weak, independent_competitors=indep,
        data_quality=a.data_quality, recommendation=rec,
        reasons=node.verdict_reasons,
    )
