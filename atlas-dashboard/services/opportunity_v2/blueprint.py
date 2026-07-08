"""
blueprint.py — from opportunity to SITE ARCHITECTURE.

For every opportunity directory the drill detects, synthesize the full
asset blueprint:

    DIRECTORY: Dog Bakeries in Columbus
    ├── GEO CATEGORIES:  Dublin · Westerville · Hilliard · …
    ├── CATEGORIES:      Custom Cakes · Gourmet Treats · …
    ├── FILTERS:         Grain-Free · Organic · Family-Owned · With Delivery
    ├── SEO PAGES:       Best Dog Bakeries in Columbus · Cheap Dog Bakeries…
    └── ARTICLES:        Planning a Dog Wedding? · Dog Birthday Party Guide…

Leaves are synthesized deterministically from the modifier banks and
classified through the same classify_node() logic as the drill (so
promotion rules stay in ONE place). They cost zero drill budget and zero
API calls — a filter or article doesn't need competition analysis; it
inherits its parent directory's economics.

Structural children (geo categories / specialty categories) come from the
actual drilled tree when available, so verified analysis is preserved.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .dimensions import all_modifier_banks, DIMENSION_TIERS
from .asset_classifier import classify_node
from .drill_engine import Node, DrillConfig


@dataclass
class BlueprintAsset:
    name: str
    asset_type: str        # geo_category | category | filter | seo_page | article
    rationale: str
    source: str            # drilled (came from tree, has analysis) | synthesized
    dimension_value: str = ""
    analysis_note: str = ""


@dataclass
class SiteBlueprint:
    directory_name: str
    lineage: str
    geo_categories: list = field(default_factory=list)
    categories: list = field(default_factory=list)
    filters: list = field(default_factory=list)
    seo_pages: list = field(default_factory=list)
    articles: list = field(default_factory=list)

    def counts(self) -> dict:
        return {"geo_categories": len(self.geo_categories),
                 "categories": len(self.categories),
                 "filters": len(self.filters),
                 "seo_pages": len(self.seo_pages),
                 "articles": len(self.articles)}

    def total_pages(self) -> int:
        # filters aren't pages; everything else is
        c = self.counts()
        return c["geo_categories"] + c["categories"] + c["seo_pages"] + c["articles"] + 1


def _apply(name: str, mod) -> str:
    return f"{name} {mod.text}" if mod.position == "suffix" else f"{mod.text} {name}"


def build_blueprint(directory_node: Node, seed_niche: str,
                     cfg: DrillConfig | None = None,
                     seo_pages_cap: int = 8,
                     articles_cap: int = 6,
                     filters_cap: int = 10) -> SiteBlueprint:
    cfg = cfg or DrillConfig()
    if cfg.dna is not None:
        return _build_blueprint_from_dna(directory_node, cfg,
                                           seo_pages_cap, articles_cap, filters_cap)
    return _build_blueprint_fallback(directory_node, seed_niche, cfg,
                                       seo_pages_cap, articles_cap, filters_cap)


def _build_blueprint_from_dna(directory_node: Node, cfg: DrillConfig,
                                seo_pages_cap: int, articles_cap: int,
                                filters_cap: int) -> SiteBlueprint:
    """DNA-driven blueprint: synthesize categories/filters/seo/articles
    from the DNA's search_dimensions. Leaf names are composed from the
    seed + accumulated directory dims + the new leaf dim, using the
    same compose_niche_name that produced the directory itself — that
    keeps naming consistent instead of nesting the compound label.
    """
    from .dna_expander import compose_niche_name

    bp = SiteBlueprint(directory_name=directory_node.niche_name,
                        lineage=directory_node.lineage)
    dna = cfg.dna

    # Walk to root to recover the original seed
    root = directory_node
    while root.parent is not None:
        root = root.parent
    seed = root.niche_name
    dir_dims = dict(directory_node.dimensions_used)

    # Reuse drilled structural children
    for child in directory_node.children:
        if child.asset_type == "geo_category":
            bp.geo_categories.append(BlueprintAsset(
                child.niche_name, "geo_category", child.asset_rationale, "drilled"))
        elif child.asset_type == "category":
            bp.categories.append(BlueprintAsset(
                child.niche_name, "category", child.asset_rationale, "drilled"))

    for dim in dna.search_dimensions:
        if dim.name in dir_dims:
            continue  # already applied at directory level
        target_asset = (dim.typically_produces_asset or "category").lower()
        if dna.asset_weight(target_asset) < 40:
            continue

        for value in dim.examples:
            # Compose fresh from seed + dir dims + this new leaf dim
            leaf_dims = {**dir_dims, dim.name: value}
            name = compose_niche_name(seed, leaf_dims, dna)
            rationale = (f"DNA dimension '{dim.name}' -> {target_asset} "
                          f"(fit {dna.asset_weight(target_asset)}/100)")

            if target_asset == "geo_category" and len(bp.geo_categories) < 20:
                if name.lower() not in {a.name.lower() for a in bp.geo_categories}:
                    bp.geo_categories.append(BlueprintAsset(
                        name, "geo_category", rationale, "synthesized", value))
            elif target_asset == "category" and len(bp.categories) < 20:
                if name.lower() not in {a.name.lower() for a in bp.categories}:
                    bp.categories.append(BlueprintAsset(
                        name, "category", rationale, "synthesized", value))
            elif target_asset == "filter" and len(bp.filters) < filters_cap:
                bp.filters.append(BlueprintAsset(
                    name, "filter", rationale, "synthesized", value))
            elif target_asset == "seo_page" and len(bp.seo_pages) < seo_pages_cap:
                bp.seo_pages.append(BlueprintAsset(
                    name, "seo_page", rationale, "synthesized", value))
            elif target_asset == "article" and len(bp.articles) < articles_cap:
                bp.articles.append(BlueprintAsset(
                    name, "article", rationale, "synthesized", value))
            elif target_asset in ("buying_guide", "comparison", "tool") \
                    and len(bp.articles) < articles_cap:
                bp.articles.append(BlueprintAsset(
                    name, target_asset, rationale, "synthesized", value))
    return bp


def _build_blueprint_fallback(directory_node: Node, seed_niche: str,
                                cfg: DrillConfig,
                                seo_pages_cap: int, articles_cap: int,
                                filters_cap: int) -> SiteBlueprint:
    """Original hardcoded-bank blueprint. Kept for backward compat when no
    DNA is loaded."""
    bp = SiteBlueprint(directory_name=directory_node.niche_name,
                        lineage=directory_node.lineage)
    a = directory_node.analysis

    for child in directory_node.children:
        if child.asset_type == "geo_category":
            bp.geo_categories.append(BlueprintAsset(
                child.niche_name, "geo_category", child.asset_rationale, "drilled"))
        elif child.asset_type == "category":
            bp.categories.append(BlueprintAsset(
                child.niche_name, "category", child.asset_rationale, "drilled"))

    banks = all_modifier_banks(seed_niche)
    data_quality = a.data_quality if a else "heuristic"
    biz = a.business_count if a else None

    def leaves_for(dim: str):
        for mod in banks.get(dim, []):
            dims = {**directory_node.dimensions_used, dim: mod.text}
            cls = classify_node(dims, directory_node.depth + 1,
                                  business_count=biz, data_quality=data_quality,
                                  filter_promotion_threshold=cfg.filter_promotion_threshold,
                                  category_directory_threshold=cfg.category_directory_threshold,
                                  geo_hierarchy=cfg.geography)
            yield mod, cls

    drilled_names = {c.name.lower() for c in bp.categories}
    for mod, cls in leaves_for("specialty"):
        name = _apply(directory_node.niche_name, mod)
        if name.lower() not in drilled_names and cls.asset_type == "category":
            bp.categories.append(BlueprintAsset(
                name, "category", cls.rationale, "synthesized", mod.text))

    for dim in ("attribute", "service", "customer_type"):
        for mod, cls in leaves_for(dim):
            if len(bp.filters) >= filters_cap:
                break
            target = bp.categories if cls.asset_type == "category" else bp.filters
            target.append(BlueprintAsset(
                _apply(directory_node.niche_name, mod), cls.asset_type,
                cls.rationale, "synthesized", mod.text))

    for mod, cls in leaves_for("intent"):
        if len(bp.seo_pages) >= seo_pages_cap:
            break
        bp.seo_pages.append(BlueprintAsset(
            _apply(directory_node.niche_name, mod), "seo_page",
            cls.rationale, "synthesized", mod.text))

    for mod, cls in leaves_for("event"):
        if len(bp.articles) >= articles_cap:
            break
        topic = mod.text.replace("for ", "").title()
        seed_singularish = seed_niche.rstrip("s").title()
        bp.articles.append(BlueprintAsset(
            f"{seed_singularish} Guide: {topic}", "article",
            cls.rationale, "synthesized", mod.text))

    return bp


def format_blueprint(bp: SiteBlueprint) -> str:
    lines = [f"DIRECTORY: {bp.directory_name}",
              f"  ({bp.total_pages()} total pages: 1 home + "
              f"{bp.counts()['geo_categories']} geo + {bp.counts()['categories']} categories + "
              f"{bp.counts()['seo_pages']} SEO pages + {bp.counts()['articles']} articles; "
              f"{bp.counts()['filters']} filters)"]

    def section(label, assets, show_note=False):
        if not assets:
            return
        lines.append(f"  {label}:")
        for x in assets:
            note = f"  [{x.analysis_note}]" if (show_note and x.analysis_note) else ""
            src = "" if x.source == "synthesized" else " (drilled)"
            lines.append(f"    - {x.name}{src}{note}")

    section("GEO CATEGORIES", bp.geo_categories, show_note=True)
    section("CATEGORIES", bp.categories, show_note=True)
    section("FILTERS", bp.filters)
    section("SEO PAGES", bp.seo_pages)
    section("ARTICLES", bp.articles)
    return "\n".join(lines)
