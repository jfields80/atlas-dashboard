"""
asset_classifier.py — "What should this become?"

The engine's job is no longer just scoring niches; it's assigning every
generated node the correct ASSET TYPE within a site architecture:

    directory            — standalone site. Seed niche, or seed + broad geo.
    geo_category         — city/suburb page inside a parent directory.
    category             — specialty section inside a directory
                            (promotable from deeper specialties).
    filter               — Tier-2 attribute (family-owned, grain-free,
                            with patio…). A UI filter, not a page — UNLESS
                            real business supply exceeds the promotion
                            threshold, in which case it's promoted to a
                            category ("Food Trucks" started life as a filter
                            in many verticals).
    seo_page             — Tier-3 intent page ("Best X in Y", "cheap X").
                            Auto-generated landing page targeting the query.
    article              — Tier-4 occasion content ("Planning a dog
                            wedding?"). Content hub material.

Classification rules (checked in order):
1. The most PAGE-LIKE dimension in the node's lineage wins. If the lineage
   contains ANY Tier-4 modifier -> article. Else any Tier-3 -> seo_page.
   Else any Tier-2 -> filter (with promotion check). A "best grain-free X"
   node is an SEO page, not a filter, because intent is what the URL targets.
2. Pure Tier-1 lineage: geography depth decides directory vs geo_category
   (state/metro-level = directory candidate; suburb = geo_category), and
   specialty presence with sufficient supply = category (or its own
   directory if supply is very high).
3. Promotion: a filter with verified business supply above
   `filter_promotion_threshold` becomes a category. In heuristic mode
   supply is a guess, so promotion is disabled unless data_quality is
   partial/verified — another place the honest wall holds.
"""

from __future__ import annotations

from dataclasses import dataclass

from .dimensions import DIMENSION_TIERS


ASSET_TYPES = ["directory", "geo_category", "category", "filter",
                "seo_page", "article"]

# Only these asset types compete for standalone-opportunity verdicts and
# continue to be drilled/expanded. lead_gen and marketplace are added because
# under DNA-driven mode they're real full-site opportunities (a therapist
# lead-gen site is a legitimate asset, not a leaf inside a directory).
STRUCTURAL_TYPES = {"directory", "geo_category", "category", "lead_gen",
                     "marketplace", "affiliate_hub"}


@dataclass
class AssetClassification:
    asset_type: str
    rationale: str
    promoted: bool = False


def _max_tier_in(dimensions_used: dict) -> int:
    tiers = [DIMENSION_TIERS.get(d, 2) for d in dimensions_used]
    return max(tiers) if tiers else 1


def classify_node(dimensions_used: dict,
                   depth: int,
                   business_count: int | None = None,
                   data_quality: str = "heuristic",
                   filter_promotion_threshold: int = 40,
                   category_directory_threshold: int = 120,
                   geo_hierarchy: dict | None = None) -> AssetClassification:
    max_tier = _max_tier_in(dimensions_used)

    # --- Tier 4 anywhere in lineage: occasion content -----------------------
    if max_tier == 4:
        occasion = dimensions_used.get("event", "occasion")
        return AssetClassification(
            "article",
            f"Occasion modifier ('{occasion}') — real demand is content-shaped: "
            f"great article/content-hub for the parent directory, terrible standalone directory.")

    # --- Tier 3: search intent = SEO landing page ----------------------------
    if max_tier == 3:
        intent = dimensions_used.get("intent", "intent")
        return AssetClassification(
            "seo_page",
            f"Search-intent modifier ('{intent}') — this is a query to target with an "
            f"auto-generated landing page inside the parent directory, not a separate site.")

    # --- Tier 2: attribute/service/customer-type = filter (maybe promoted) ---
    if max_tier == 2:
        attr = (dimensions_used.get("attribute")
                 or dimensions_used.get("service")
                 or dimensions_used.get("customer_type") or "attribute")
        if (business_count is not None
                and data_quality in ("partial", "verified")
                and business_count >= filter_promotion_threshold):
            return AssetClassification(
                "category",
                f"Attribute ('{attr}') PROMOTED to category — verified supply of "
                f"{business_count} businesses exceeds threshold {filter_promotion_threshold}; "
                f"enough real inventory to deserve its own section.",
                promoted=True)
        note = ("supply unverified (heuristic mode) — promotion to category "
                 "requires verified counts" if data_quality == "heuristic"
                 else f"supply {business_count} below promotion threshold {filter_promotion_threshold}")
        return AssetClassification(
            "filter",
            f"Business attribute ('{attr}') — a UI filter inside the parent directory; {note}.")

    # --- Pure Tier 1 lineage: the structural skeleton -------------------------
    geo = dimensions_used.get("geography")
    has_specialty = "specialty" in dimensions_used

    if geo and geo_hierarchy:
        # suburb-level geo = geo_category page inside the metro directory
        for state, metros in geo_hierarchy.items():
            for metro, suburbs in metros.items():
                if geo in suburbs:
                    return AssetClassification(
                        "geo_category",
                        f"Suburb-level geography ('{geo}') — a city page within the "
                        f"{metro} directory, not a standalone site.")

    if has_specialty:
        specialty = dimensions_used["specialty"]
        if (business_count is not None
                and data_quality in ("partial", "verified")
                and business_count >= category_directory_threshold):
            return AssetClassification(
                "directory",
                f"Specialty ('{specialty}') with verified supply of {business_count} — "
                f"deep enough to stand alone as its own directory.",
                promoted=True)
        return AssetClassification(
            "category",
            f"Specialty ('{specialty}') — a category section within the parent "
            f"geographic directory. Could be promoted to its own directory if "
            f"verified supply ≥ {category_directory_threshold}.")

    return AssetClassification(
        "directory",
        "Structural node (seed or seed + state/metro geography) — directory candidate.")
