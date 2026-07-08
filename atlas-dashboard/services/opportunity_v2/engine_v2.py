"""
engine_v2.py — Orchestrator. One entry point across all five phases.

    from services.opportunity_v2 import engine_v2
    result = engine_v2.discover(
        "Mexican restaurants",
        mode="heuristic",                    # or "real"
        # provider=GoogleCustomSearchProvider(),   # required for mode="real"
        # business_counter=my_places_count_fn,     # optional, wires Places
    )

Returns ranked InvestmentBrief objects for every detected opportunity,
plus the full drill tree for the UI.
"""

from __future__ import annotations

from typing import Callable, Optional

from .drill_engine import run_drill, DrillConfig
from .analyzers import HeuristicAnalyzer, RealDataAnalyzer, build_brief
from .search_provider import SearchProvider


def discover(seed_niche: str,
              mode: str = "heuristic",
              provider: Optional[SearchProvider] = None,
              business_counter: Optional[Callable[[str], int]] = None,
              config: Optional[DrillConfig] = None) -> dict:
    if mode == "real":
        if provider is None:
            raise ValueError(
                "mode='real' requires a SearchProvider (e.g. "
                "GoogleCustomSearchProvider). Use mode='heuristic' for $0 runs.")
        analyzer = RealDataAnalyzer(provider, business_counter)
    else:
        analyzer = HeuristicAnalyzer()

    drill = run_drill(seed_niche, analyzer, config)

    reports = getattr(analyzer, "reports", {})
    briefs = []
    for node in drill["opportunities"]:
        report = reports.get(node.niche_name.lower())
        briefs.append(build_brief(node, report))
    briefs.sort(key=lambda b: b.opportunity_score, reverse=True)

    return {
        "seed_niche": seed_niche,
        "mode": mode,
        "nodes_analyzed": drill["nodes_analyzed"],
        "opportunities_found": len(briefs),
        "briefs": briefs,
        "tree_root": drill["root"],
        "all_nodes": drill["all_nodes"],
    }


def format_brief(b) -> str:
    """Terminal/log-friendly rendering of an InvestmentBrief."""
    lines = [
        b.niche_name,
        f"  Lineage:            {b.lineage}",
        f"  Opportunity Score:  {b.opportunity_score}",
        f"  Estimated Revenue:  ${b.revenue.low}-${b.revenue.high}/mo "
        f"(confidence {b.revenue.confidence}%)",
        f"  Businesses Found:   {b.business_count}",
        f"  Competition:        {b.competition_label}",
        f"  Independent Comps:  {b.independent_competitors} "
        f"({b.weak_competitors} weak)",
        f"  Data Quality:       {b.data_quality}",
        f"  Recommendation:     {b.recommendation}",
    ]
    return "\n".join(lines)
