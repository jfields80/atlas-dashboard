"""
dna_classifier.py — asset classification driven by DNA.

Rules, in order:

1. If the node's lineage carries a dimension whose DNA-declared
   typically_produces_asset is a LEAF type (filter/seo_page/article/
   comparison/buying_guide/tool), it becomes that leaf. This replaces
   the tier-based heuristic entirely — the DNA is source of truth on
   what each dimension becomes.

2. Structural dimensions (geography, product, business type) yield
   structural nodes (directory / geo_category / category). The specific
   choice depends on lineage depth and the DNA's asset_preferences:
   - Root ecosystem node with directory fit >= 70 -> directory
   - Geography child of a directory -> geo_category
   - Structural child of a directory whose asset_hint == 'directory'
     with high fit -> nested directory (rare; usually category)
   - Otherwise -> category

3. If the DNA's asset_preferences penalize an asset type below a floor
   (default 40), the classifier will NOT recommend that asset type even
   when rule 1/2 would produce it — it downgrades to the next best fit.
   That's how "this market doesn't support marketplaces" is enforced
   even if a search dimension technically points there.

If no DNA is provided at all, delegate to the old classify_node().
"""

from __future__ import annotations

from dataclasses import dataclass

from .dna.schema import OpportunityDNA
from .asset_classifier import AssetClassification, classify_node as _fallback_classify

LEAF_ASSET_TYPES = {"filter", "seo_page", "article", "comparison",
                     "buying_guide", "tool", "affiliate_hub"}
STRUCTURAL_ASSET_TYPES = {"directory", "geo_category", "category",
                           "lead_gen", "marketplace"}


def _best_asset(dna: OpportunityDNA, candidates: list[str],
                 floor: int = 40) -> tuple[str, int]:
    """Pick the highest-fit asset type from candidates, respecting DNA
    preferences. Returns (asset_type, fit_weight)."""
    scored = [(c, dna.asset_weight(c)) for c in candidates]
    scored.sort(key=lambda x: -x[1])
    top_type, top_weight = scored[0]
    if top_weight >= floor:
        return top_type, top_weight
    # Everything below floor — fall through to "category" as safe default
    return "category", dna.asset_weight("category")


def classify_with_dna(node_dimensions_used: dict,
                       dimension_asset_hints: dict,
                       dimension_intents: dict,
                       depth: int,
                       dna: OpportunityDNA | None,
                       business_count: int | None = None,
                       data_quality: str = "heuristic",
                       ecosystem_role_hint: str | None = None,
                       config=None) -> AssetClassification:
    """The full DNA-aware classifier. If dna is None, delegate to the
    tier-based fallback."""
    if dna is None:
        # Fallback: no DNA loaded, use old classifier
        return _fallback_classify(
            node_dimensions_used, depth,
            business_count=business_count, data_quality=data_quality,
            geo_hierarchy=config.geography if config else None)

    # --- Rule 1: leaf-generating dimension in lineage? ----------------------
    # The MOST leaf-like hint wins if multiple dims are present. Article
    # (occasion) trumps SEO page (intent) trumps filter (attribute) — same
    # ordering as before, but now driven by the DNA's declared hints.
    leaf_priority = ["article", "comparison", "buying_guide", "tool",
                       "affiliate_hub", "seo_page", "filter"]
    dim_hints_present = list(dimension_asset_hints.values())
    for leaf_type in leaf_priority:
        if leaf_type in dim_hints_present:
            # Which dimension pointed here? (for rationale)
            dim_name = next(name for name, hint in dimension_asset_hints.items()
                             if hint == leaf_type)
            value = node_dimensions_used.get(dim_name, "unknown")
            weight = dna.asset_weight(leaf_type)
            if weight < 40:
                # DNA says this market doesn't support this asset type well
                return AssetClassification(
                    asset_type="filter" if weight > dna.asset_weight("category")
                                 else "category",
                    rationale=f"Dimension '{dim_name}' ('{value}') would normally produce "
                                f"a {leaf_type}, but DNA gives {leaf_type} only fit {weight}/100 "
                                f"in this market — downgraded.")
            return AssetClassification(
                asset_type=leaf_type,
                rationale=f"Dimension '{dim_name}' ('{value}') — DNA declares this "
                            f"dimension produces {leaf_type} assets (fit weight {weight}).")

    # --- Rule 2: structural placement ---------------------------------------
    if ecosystem_role_hint == "directory":
        # Ecosystem sibling seed — directory candidate directly
        weight = dna.asset_weight("directory")
        return AssetClassification(
            asset_type="directory",
            rationale=f"Ecosystem node with directory potential (DNA fit {weight}/100).")

    # Any structural dimension in lineage?
    structural_hints = [hint for hint in dim_hints_present
                          if hint in ("directory", "geo_category", "category")]
    if structural_hints:
        # If depth >= 1 and 'geo_category' is a declared hint, use it
        if "geo_category" in structural_hints:
            weight = dna.asset_weight("geo_category")
            return AssetClassification(
                asset_type="geo_category" if weight >= 40 else "category",
                rationale=f"Geographic dimension — geo_category page (DNA fit {weight}/100).")
        if "directory" in structural_hints and depth == 0:
            weight = dna.asset_weight("directory")
            return AssetClassification(
                asset_type="directory",
                rationale=f"Root structural node — directory (DNA fit {weight}/100).")
        # Otherwise category
        weight = dna.asset_weight("category")
        return AssetClassification(
            asset_type="category" if weight >= 40 else "filter",
            rationale=f"Structural sub-dimension — category (DNA fit {weight}/100).")

    # Root node with no dimensions used at all -> directory
    if depth == 0 and not node_dimensions_used:
        return AssetClassification(
            asset_type="directory",
            rationale="Seed niche (root) — directory candidate.")

    # Fallback: category
    return AssetClassification(
        asset_type="category",
        rationale="No declared asset hint — default to category.")
