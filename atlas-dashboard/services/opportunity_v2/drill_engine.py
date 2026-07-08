"""
drill_engine.py — Phase 1: Recursive Drill-Down Engine.

The core of the Opportunity Engine. Recursively decomposes a seed niche
across multiple dimensions simultaneously (geography, specialty, intent,
customer type, service, product/event, attribute), analyzing every node
and drilling deeper until stopping conditions are met.

Key design decisions:

1. ANALYZER IS PLUGGABLE. The engine doesn't know how competition or
   business counts are measured. It calls `analyzer.analyze(node)` and
   gets back a NodeAnalysis. Ship day one with HeuristicAnalyzer;
   swap in RealDataAnalyzer (competitor discovery + quality audit +
   Places counts) without changing this file. This is the seam that
   prevents the refactor.

2. DRILLING IS THRESHOLD-DRIVEN, exactly per the spec:
       competition 98 -> too hot, drill deeper
       competition 61 -> still hot, drill deeper
       competition 27 -> below threshold... check other conditions
       -> Opportunity detected. Stop drilling this branch.
   A node stops being expanded when it's EITHER a detected opportunity
   (all viability conditions met) OR a dead end (business supply too
   thin to go deeper / max depth reached).

3. BEAM PRUNING prevents combinatorial explosion. Multi-dimensional
   expansion of "Mexican restaurants" could generate 10,000+ nodes.
   Per level, only the `beam_width` most promising non-terminal nodes
   get expanded further. Total node budget is also capped so a run
   with a real (paid) analyzer can't burn unlimited API calls.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Optional, Protocol

from .dimensions import all_modifier_banks, DEFAULT_GEOGRAPHY, Modifier, DIMENSION_TIERS
from .asset_classifier import classify_node, STRUCTURAL_TYPES


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class NodeAnalysis:
    """What the analyzer knows about a node. Scores 0-100.
    competition: HIGHER = MORE competitive (matches the spec's
    'competition 98 -> rejected, 14 -> opportunity' framing)."""
    competition: float
    business_count: int
    search_demand: float
    directory_weakness: float      # higher = weaker incumbents = better for us
    monetization: float
    automation_fit: float
    evidence: list = field(default_factory=list)   # dicts: source/title/url/note
    data_quality: str = "heuristic"                # heuristic | partial | verified


@dataclass
class Node:
    id: int
    niche_name: str
    parent: Optional["Node"]
    depth: int
    dimensions_used: dict          # {"geography": "Columbus", "specialty": "birria", ...}
    analysis: Optional[NodeAnalysis] = None
    verdict: str = "pending"       # pending | opportunity | drill_deeper | dead_end | budget_stopped | leaf_asset
    verdict_reasons: list = field(default_factory=list)
    children: list = field(default_factory=list)
    asset_type: str = "directory"  # directory | geo_category | category | filter | seo_page | article | ...
    asset_rationale: str = ""
    # DNA-driven expansion carries these; fallback path leaves them empty
    dimension_intents: dict = field(default_factory=dict)
    dimension_asset_hints: dict = field(default_factory=dict)
    origin: str = "drill_child"          # drill_child | ecosystem_sibling | seed
    origin_note: str = ""

    @property
    def lineage(self) -> str:
        parts = []
        n = self
        while n:
            parts.append(n.niche_name)
            n = n.parent
        return " → ".join(reversed(parts))

    def nearest_structural_ancestor(self) -> Optional["Node"]:
        n = self.parent
        while n:
            if n.asset_type in ("directory", "geo_category", "category"):
                return n
            n = n.parent
        return None


@dataclass
class DrillConfig:
    """Stopping conditions & budgets. All configurable per the spec."""
    max_competition: float = 40.0        # opportunity requires competition BELOW this
    min_business_count: int = 25         # need enough businesses for a useful directory
    min_search_demand: float = 30.0      # need some demand
    min_monetization: float = 45.0       # monetization must be viable
    min_directory_weakness: float = 50.0 # incumbents must be beatable
    max_depth: int = 5
    max_total_nodes: int = 400           # hard budget (protects paid API analyzers)
    beam_width: int = 6                  # top-K nodes expanded per level
    modifiers_per_dimension: int = 4     # branching cap: sample N per bank
    geo_children_cap: int = 6            # branching cap: max geo children per node
    filter_promotion_threshold: int = 40      # verified supply to promote filter -> category
    category_directory_threshold: int = 120   # verified supply to promote category -> directory
    min_businesses_to_drill: int = 8     # if supply is already this thin, don't go deeper
    geography: dict = field(default_factory=lambda: DEFAULT_GEOGRAPHY)
    dna: object = None                   # OpportunityDNA if set — engine runs in DNA-driven mode
    examples_per_dimension: int = 6      # cap on values per DNA search_dimension


class Analyzer(Protocol):
    def analyze(self, node: Node) -> NodeAnalysis: ...


# ---------------------------------------------------------------------------
# Verdict logic — the "stopping conditions" from the spec, made explicit
# ---------------------------------------------------------------------------

def evaluate_node(node: Node, cfg: DrillConfig) -> tuple[str, list[str]]:
    a = node.analysis
    reasons: list[str] = []

    # Dead ends first — no point drilling where there's nothing to find
    if a.business_count < cfg.min_businesses_to_drill:
        reasons.append(
            f"Business supply too thin ({a.business_count} found, need ≥{cfg.min_businesses_to_drill} to justify drilling further).")
        return "dead_end", reasons
    if a.search_demand < cfg.min_search_demand:
        reasons.append(
            f"Search demand too low ({a.search_demand:.0f} < {cfg.min_search_demand:.0f}).")
        return "dead_end", reasons

    # Opportunity check: ALL viability conditions must hold
    checks = {
        f"Competition {a.competition:.0f} below threshold {cfg.max_competition:.0f}":
            a.competition <= cfg.max_competition,
        f"Business count {a.business_count} ≥ minimum {cfg.min_business_count}":
            a.business_count >= cfg.min_business_count,
        f"Monetization {a.monetization:.0f} ≥ {cfg.min_monetization:.0f}":
            a.monetization >= cfg.min_monetization,
        f"Directory weakness {a.directory_weakness:.0f} ≥ {cfg.min_directory_weakness:.0f} (incumbents beatable)":
            a.directory_weakness >= cfg.min_directory_weakness,
    }

    if all(checks.values()):
        reasons.extend(f"✓ {label}" for label in checks)
        return "opportunity", reasons

    # Not an opportunity yet — explain what failed and drill deeper
    for label, passed in checks.items():
        reasons.append(("✓ " if passed else "✗ ") + label)

    if node.depth >= cfg.max_depth:
        reasons.append(f"Max depth {cfg.max_depth} reached — stopping this branch.")
        return "dead_end", reasons

    reasons.append("Searching deeper…")
    return "drill_deeper", reasons


# ---------------------------------------------------------------------------
# Node expansion — multi-dimensional decomposition
# ---------------------------------------------------------------------------

def _apply_modifier(name: str, mod: Modifier) -> str:
    if mod.position == "suffix":
        return f"{name} {mod.text}"
    return f"{mod.text} {name}"


def _geo_children(node: Node, cfg: DrillConfig) -> list[tuple[str, dict]]:
    """Next geographic level down from the node's current geo, if any."""
    current_geo = node.dimensions_used.get("geography")
    out = []
    for state, metros in cfg.geography.items():
        if current_geo is None:
            out.append((f"{node.niche_name} in {state}",
                         {**node.dimensions_used, "geography": state}))
        elif current_geo == state:
            for metro in metros:
                base = node.niche_name.replace(f" in {state}", "")
                out.append((f"{base} in {metro}",
                             {**node.dimensions_used, "geography": metro}))
        elif current_geo in metros:
            for suburb in metros[current_geo]:
                base = node.niche_name.replace(f" in {current_geo}", "")
                out.append((f"{base} in {suburb}",
                             {**node.dimensions_used, "geography": suburb}))
    return out


def expand_node(node: Node, seed_niche: str, cfg: DrillConfig,
                 next_id: itertools.count) -> list[Node]:
    """DNA-driven: use search_dimensions from the loaded DNA profile.
    Fallback path (hardcoded banks) is used ONLY if cfg.dna is None."""
    if cfg.dna is not None:
        return _expand_from_dna(node, cfg, next_id)
    return _expand_fallback(node, seed_niche, cfg, next_id)


def _expand_from_dna(node: Node, cfg: DrillConfig,
                       next_id: itertools.count) -> list[Node]:
    from .dna_expander import expand_from_dna as _dna_expand

    # Walk to the tree root to recover the ORIGINAL seed niche
    root = node
    while root.parent is not None:
        root = root.parent
    seed = root.niche_name

    used = set(node.dimensions_used.keys())
    candidates = _dna_expand(
        base_niche=node.niche_name, dna=cfg.dna, used_dimensions=used,
        seed_niche=seed, accumulated_dims=node.dimensions_used,
        examples_per_dimension=cfg.examples_per_dimension)

    children: list[Node] = []
    for cand in candidates:
        # Merge with parent's accumulated dimension_use so lineage carries forward
        merged_dims = {**node.dimensions_used, **cand.dimensions_used}
        merged_intents = {**getattr(node, "dimension_intents", {}), **cand.dimension_intents}
        merged_hints = {**getattr(node, "dimension_asset_hints", {}),
                         **cand.dimension_asset_hints}
        child = Node(next(next_id), cand.niche_name, node, node.depth + 1, merged_dims)
        child.dimension_intents = merged_intents
        child.dimension_asset_hints = merged_hints
        child.origin = cand.origin
        child.origin_note = cand.origin_note
        children.append(child)
    return children


def _expand_fallback(node: Node, seed_niche: str, cfg: DrillConfig,
                       next_id: itertools.count) -> list[Node]:
    """Original hardcoded-bank expansion. Preserved as a fallback when NO
    DNA is loaded — kept intact so backwards-compat tests still pass."""
    children: list[Node] = []
    used = set(node.dimensions_used.keys())

    for name, dims in _geo_children(node, cfg)[: cfg.geo_children_cap]:
        children.append(Node(next(next_id), name, node, node.depth + 1, dims))

    banks = all_modifier_banks(seed_niche)
    for dimension, modifiers in banks.items():
        if DIMENSION_TIERS.get(dimension, 2) != 1:
            continue
        if dimension in used:
            continue
        for mod in modifiers[: cfg.modifiers_per_dimension]:
            name = _apply_modifier(node.niche_name, mod)
            dims = {**node.dimensions_used, dimension: mod.text}
            children.append(Node(next(next_id), name, node, node.depth + 1, dims))

    return children


# ---------------------------------------------------------------------------
# The drill loop
# ---------------------------------------------------------------------------

def run_drill(seed_niche: str, analyzer: Analyzer,
               cfg: DrillConfig | None = None) -> dict:
    cfg = cfg or DrillConfig()
    next_id = itertools.count(1)

    root = Node(next(next_id), seed_niche, None, 0, {})
    root.origin = "seed"
    all_nodes: list[Node] = [root]
    frontier: list[Node] = [root]
    opportunities: list[Node] = []
    nodes_analyzed = 0

    # DNA-driven ecosystem seeding: the ecosystem graph gives us sibling
    # opportunities that no drill would ever reach (they're not "deeper"
    # variants of the seed, they're commercially adjacent markets).
    if cfg.dna is not None:
        from .dna_expander import expand_ecosystem_siblings
        for cand in expand_ecosystem_siblings(cfg.dna):
            # Ecosystem siblings are their own tree roots. Depth 0 = seed peer.
            sib = Node(next(next_id), cand.niche_name, None, 0, {})
            sib.origin = "ecosystem_sibling"
            sib.origin_note = cand.origin_note
            sib.dimension_asset_hints = cand.dimension_asset_hints
            all_nodes.append(sib)
            frontier.append(sib)

    while frontier and nodes_analyzed < cfg.max_total_nodes:
        # Spend budget on the most promising lineages first: children of
        # low-competition parents get analyzed before children of hot ones,
        # so the budget reaches the depths where opportunities actually live.
        frontier.sort(key=lambda n: (n.parent.analysis.competition
                                      if n.parent and n.parent.analysis else 50.0))
        # Analyze every node on the frontier
        for node in frontier:
            if nodes_analyzed >= cfg.max_total_nodes:
                node.verdict = "budget_stopped"
                node.verdict_reasons = ["Node budget exhausted before analysis."]
                continue
            node.analysis = analyzer.analyze(node)
            nodes_analyzed += 1

            # --- Asset classification: what should this node BECOME? --------
            if cfg.dna is not None:
                from .dna_classifier import classify_with_dna
                cls = classify_with_dna(
                    node.dimensions_used, node.dimension_asset_hints,
                    node.dimension_intents, node.depth, cfg.dna,
                    business_count=node.analysis.business_count,
                    data_quality=node.analysis.data_quality,
                    ecosystem_role_hint=(
                        "directory" if node.origin == "ecosystem_sibling" else None),
                    config=cfg)
            else:
                cls = classify_node(
                    node.dimensions_used, node.depth,
                    business_count=node.analysis.business_count,
                    data_quality=node.analysis.data_quality,
                    filter_promotion_threshold=cfg.filter_promotion_threshold,
                    category_directory_threshold=cfg.category_directory_threshold,
                    geo_hierarchy=cfg.geography)
            node.asset_type = cls.asset_type
            node.asset_rationale = cls.rationale

            if node.asset_type not in STRUCTURAL_TYPES:
                # Filters / SEO pages / articles are LEAVES: they attach to
                # their parent directory's blueprint and are never expanded
                # or scored as standalone opportunities.
                node.verdict = "leaf_asset"
                node.verdict_reasons = [cls.rationale]
                continue

            node.verdict, node.verdict_reasons = evaluate_node(node, cfg)
            node.verdict_reasons.insert(0, f"Asset type: {node.asset_type} — {cls.rationale}")
            if node.verdict == "opportunity":
                opportunities.append(node)

        # Beam pruning: expand only the most promising drill_deeper nodes.
        # "Promising" = lowest competition + highest business supply —
        # i.e. the branches most likely to hide an opportunity underneath.
        drillable = [n for n in frontier if n.verdict == "drill_deeper"]
        drillable.sort(key=lambda n: (n.analysis.competition,
                                       -n.analysis.business_count))
        to_expand = drillable[:cfg.beam_width]
        for n in drillable[cfg.beam_width:]:
            n.verdict = "budget_stopped"
            n.verdict_reasons.append(
                "Pruned by beam search — other branches on this level looked more promising.")

        new_frontier: list[Node] = []
        for node in to_expand:
            kids = expand_node(node, seed_niche, cfg, next_id)
            node.children = kids
            all_nodes.extend(kids)
            new_frontier.extend(kids)
        frontier = new_frontier

    # Anything still pending never got analyzed before budget ran out
    for node in all_nodes:
        if node.verdict == "pending":
            node.verdict = "budget_stopped"
            node.verdict_reasons = ["Node budget exhausted before analysis."]

    opportunities.sort(
        key=lambda n: (n.analysis.directory_weakness + (100 - n.analysis.competition)
                        + n.analysis.monetization),
        reverse=True)

    return {
        "root": root,
        "all_nodes": all_nodes,
        "opportunities": opportunities,
        "nodes_analyzed": nodes_analyzed,
        "config": cfg,
    }
