"""
scout_providers.py — Scout Intelligence Provider Architecture.

Defines the Provider protocol that all Scout data sources implement.
New providers plug in here without changing scout_intelligence.py
or anything else in Atlas.

Current providers:
    EstimatedProvider — deterministic inference from DNA + niche text.
                        Ships today. Produces ESTIMATED tags, never VERIFIED.

Future providers (not implemented, documented for reference):
    GoogleBusinessProvider  — Google Business Profile API
    GoogleMapsProvider      — Places API / Nearby Search
    BrightLocalProvider     — BrightLocal Ratings API
    SemrushProvider         — SEMrush Domain/Keyword API
    AhrefsProvider          — Ahrefs API
    YelpFusionProvider      — Yelp Fusion API
    DataAxleProvider        — Data Axle business database
    CommonCrawlProvider     — Common Crawl directory index

Provider contract:
    Each provider is responsible for ONE domain of data (business counts,
    search volume, competitor quality, etc.). Scout Intelligence calls all
    registered providers, merges their outputs, and prefers higher-quality
    tags (VERIFIED > ESTIMATED > UNKNOWN) per field.

Data source tags — the honesty layer:
    VERIFIED  — came from a live external provider call.
                A real API returned this specific value.
    ESTIMATED — deterministic model, no external call.
                Reproducible: same inputs always produce same output.
                Honest about what it is.
    UNKNOWN   — we have no basis for this value.
                Better than inventing something.

Architecture rules:
    - Pure service. No Flask, no SQL.
    - No external HTTP calls in this file (that is each provider's job).
    - Provider instances are stateless; safe to reuse.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Protocol, runtime_checkable

from .dna.schema import OpportunityDNA, Intensity


# ─────────────────────────────────────────────────────────────────────────────
# Data source tags
# ─────────────────────────────────────────────────────────────────────────────

class DataSource(str, Enum):
    VERIFIED  = "verified"    # from a live external API
    ESTIMATED = "estimated"   # deterministic model, no external call
    UNKNOWN   = "unknown"     # no basis; do not use for decisions


@dataclass
class TaggedValue:
    """A scalar value with its provenance tag and human-readable source name.

    confidence: optional 0-100 confidence in THIS specific value (distinct
    from the categorical `source` status). None when no meaningful
    confidence figure exists yet (e.g. legacy call sites that predate this
    field). Populated with sensible tier defaults by the _estimated/
    _verified/_unknown helpers below unless a caller overrides it with a
    more specific figure (e.g. a provider's own reported match confidence).
    This field is additive: every existing TaggedValue(...) construction
    using keyword arguments continues to work unchanged.
    """
    value: float
    source: DataSource
    provider: str          # e.g. "EstimatedProvider", "GoogleBusinessProvider"
    rationale: str         # one-line explanation of how this value was derived
    confidence: Optional[float] = None

    @property
    def is_verified(self) -> bool:
        return self.source == DataSource.VERIFIED

    @property
    def is_estimated(self) -> bool:
        return self.source == DataSource.ESTIMATED

    @property
    def is_unknown(self) -> bool:
        return self.source == DataSource.UNKNOWN

    def __repr__(self) -> str:
        return f"{self.value:.1f} [{self.source.value}:{self.provider}]"


# Default confidence tiers by status, used by the helpers below unless a
# caller supplies a more specific figure. VERIFIED evidence defaults to a
# high-but-not-perfect confidence (a real API call can still be stale or
# mismatched); ESTIMATED reflects a deterministic-model baseline; UNKNOWN
# carries no confidence at all — there's nothing to be confident about.
_DEFAULT_CONFIDENCE_VERIFIED  = 90.0
_DEFAULT_CONFIDENCE_ESTIMATED = 40.0


def _unknown(field_name: str) -> TaggedValue:
    return TaggedValue(
        value=0.0,
        source=DataSource.UNKNOWN,
        provider="none",
        rationale=f"{field_name}: no data source available yet.",
        confidence=None)


def _estimated(value: float, provider: str, rationale: str,
                confidence: Optional[float] = None) -> TaggedValue:
    return TaggedValue(
        value=round(value, 1),
        source=DataSource.ESTIMATED,
        provider=provider,
        rationale=rationale,
        confidence=(confidence if confidence is not None
                     else _DEFAULT_CONFIDENCE_ESTIMATED))


def _verified(value: float, provider: str, rationale: str,
               confidence: Optional[float] = None) -> TaggedValue:
    return TaggedValue(
        value=round(value, 1),
        source=DataSource.VERIFIED,
        provider=provider,
        rationale=rationale,
        confidence=(confidence if confidence is not None
                     else _DEFAULT_CONFIDENCE_VERIFIED))


# ─────────────────────────────────────────────────────────────────────────────
# Raw provider output — what each provider returns
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ProviderOutput:
    """
    The fields a provider CAN populate. All optional — providers only
    return what their data source actually covers.
    Scout Intelligence merges outputs from all registered providers,
    preferring higher-quality tags.
    """
    provider_name: str

    # Market size
    verified_business_count:  Optional[TaggedValue] = None
    estimated_search_volume:  Optional[TaggedValue] = None   # monthly searches
    google_maps_density:      Optional[TaggedValue] = None   # businesses per sq km

    # Competition
    directory_competitor_count: Optional[TaggedValue] = None
    competitor_authority_avg:   Optional[TaggedValue] = None   # 0-100 DA proxy
    seo_difficulty:             Optional[TaggedValue] = None   # 0-100
    backlink_difficulty:        Optional[TaggedValue] = None   # 0-100

    # Content & quality
    directory_quality_avg:      Optional[TaggedValue] = None   # 0-100
    competitor_content_depth:   Optional[TaggedValue] = None   # 0-100
    mobile_quality_avg:         Optional[TaggedValue] = None   # 0-100

    # Demand signals
    commercial_intent_score:    Optional[TaggedValue] = None   # 0-100
    avg_cpc_usd:                Optional[TaggedValue] = None   # $ per click
    advertiser_demand:          Optional[TaggedValue] = None   # 0-100

    # Business quality signals
    review_avg_rating:          Optional[TaggedValue] = None   # 0-5
    review_volume_avg:          Optional[TaggedValue] = None   # reviews per biz
    online_booking_pct:         Optional[TaggedValue] = None   # 0-100
    claimed_gbp_pct:            Optional[TaggedValue] = None   # 0-100 (Google Business %)
    nap_consistency_pct:        Optional[TaggedValue] = None   # 0-100

    # Monetization signals
    affiliate_programs_found:   Optional[TaggedValue] = None   # count
    avg_listing_price_usd:      Optional[TaggedValue] = None   # premium listing $/mo

    # Gap signals (higher = more gaps = more opportunity)
    ux_gap_score:               Optional[TaggedValue] = None   # 0-100
    feature_gap_score:          Optional[TaggedValue] = None   # 0-100
    geo_coverage_gap_score:     Optional[TaggedValue] = None   # 0-100


# ─────────────────────────────────────────────────────────────────────────────
# Provider protocol
# ─────────────────────────────────────────────────────────────────────────────

@runtime_checkable
class ScoutProvider(Protocol):
    """
    Interface every Scout provider must implement.
    Providers are stateless and produce ProviderOutput.
    """

    @property
    def name(self) -> str:
        """Unique name used in TaggedValue.provider and logging."""
        ...

    def research(self, niche_name: str, dna: OpportunityDNA,
                  ctx: dict) -> ProviderOutput:
        """
        Run research for this niche and return what this provider knows.
        Fields the provider cannot populate remain None.
        Must not raise — return empty ProviderOutput on any error.
        """
        ...


# ─────────────────────────────────────────────────────────────────────────────
# Merging — prefer verified > estimated > unknown
# ─────────────────────────────────────────────────────────────────────────────

_SOURCE_PRIORITY = {
    DataSource.VERIFIED:  3,
    DataSource.ESTIMATED: 2,
    DataSource.UNKNOWN:   1,
}


def _best(a: Optional[TaggedValue],
          b: Optional[TaggedValue]) -> Optional[TaggedValue]:
    """Return whichever TaggedValue has the higher-quality data source."""
    if a is None:
        return b
    if b is None:
        return a
    return a if _SOURCE_PRIORITY[a.source] >= _SOURCE_PRIORITY[b.source] else b


def merge_outputs(outputs: list[ProviderOutput]) -> ProviderOutput:
    """
    Merge multiple ProviderOutputs into one, field by field.
    For each field, the value with the highest DataSource priority wins.
    """
    merged = ProviderOutput(provider_name="merged")
    for out in outputs:
        merged.verified_business_count  = _best(merged.verified_business_count,  out.verified_business_count)
        merged.estimated_search_volume  = _best(merged.estimated_search_volume,  out.estimated_search_volume)
        merged.google_maps_density      = _best(merged.google_maps_density,      out.google_maps_density)
        merged.directory_competitor_count = _best(merged.directory_competitor_count, out.directory_competitor_count)
        merged.competitor_authority_avg = _best(merged.competitor_authority_avg, out.competitor_authority_avg)
        merged.seo_difficulty           = _best(merged.seo_difficulty,           out.seo_difficulty)
        merged.backlink_difficulty      = _best(merged.backlink_difficulty,       out.backlink_difficulty)
        merged.directory_quality_avg    = _best(merged.directory_quality_avg,    out.directory_quality_avg)
        merged.competitor_content_depth = _best(merged.competitor_content_depth, out.competitor_content_depth)
        merged.mobile_quality_avg       = _best(merged.mobile_quality_avg,       out.mobile_quality_avg)
        merged.commercial_intent_score  = _best(merged.commercial_intent_score,  out.commercial_intent_score)
        merged.avg_cpc_usd              = _best(merged.avg_cpc_usd,              out.avg_cpc_usd)
        merged.advertiser_demand        = _best(merged.advertiser_demand,        out.advertiser_demand)
        merged.review_avg_rating        = _best(merged.review_avg_rating,        out.review_avg_rating)
        merged.review_volume_avg        = _best(merged.review_volume_avg,        out.review_volume_avg)
        merged.online_booking_pct       = _best(merged.online_booking_pct,       out.online_booking_pct)
        merged.claimed_gbp_pct          = _best(merged.claimed_gbp_pct,          out.claimed_gbp_pct)
        merged.nap_consistency_pct      = _best(merged.nap_consistency_pct,      out.nap_consistency_pct)
        merged.affiliate_programs_found = _best(merged.affiliate_programs_found, out.affiliate_programs_found)
        merged.avg_listing_price_usd    = _best(merged.avg_listing_price_usd,    out.avg_listing_price_usd)
        merged.ux_gap_score             = _best(merged.ux_gap_score,             out.ux_gap_score)
        merged.feature_gap_score        = _best(merged.feature_gap_score,        out.feature_gap_score)
        merged.geo_coverage_gap_score   = _best(merged.geo_coverage_gap_score,   out.geo_coverage_gap_score)
    return merged


# ─────────────────────────────────────────────────────────────────────────────
# Estimated provider — deterministic inference, ships today
# ─────────────────────────────────────────────────────────────────────────────

_INTENSITY_NUM = {
    Intensity.EXTREME:   98, Intensity.VERY_HIGH: 85,
    Intensity.HIGH:      68, Intensity.MEDIUM:     50,
    Intensity.LOW:       30, Intensity.VERY_LOW:   12,
}


def _int(i: Optional[Intensity], default: float = 50.0) -> float:
    if i is None:
        return default
    return float(_INTENSITY_NUM.get(i, default))


# CPC estimation by DNA lead_value (USD/click proxy).
# These are typical CPC ranges for directory-adjacent keywords by market value.
_CPC_BY_LEAD_VALUE = {
    Intensity.EXTREME:   18.0,
    Intensity.VERY_HIGH: 12.0,
    Intensity.HIGH:       6.0,
    Intensity.MEDIUM:     2.5,
    Intensity.LOW:        0.80,
    Intensity.VERY_LOW:   0.25,
}

# Review volume proxy by DNA review_importance.
# How many reviews the average business in this category has.
_REVIEWS_BY_IMPORTANCE = {
    Intensity.EXTREME:   180, Intensity.VERY_HIGH: 95,
    Intensity.HIGH:       45, Intensity.MEDIUM:    18,
    Intensity.LOW:         8, Intensity.VERY_LOW:   3,
}

# Word count → business count proxy (used when no ecosystem node matched)
# Broader niche = more businesses. Each extra word halves the pool.
_SUPPLY_BASE_COUNT = 800   # 1-word niche baseline


class EstimatedProvider:
    """
    Deterministic inference provider. Ships as the baseline provider.
    Uses only the niche name text and OpportunityDNA.
    All outputs are tagged ESTIMATED — never VERIFIED.
    """

    _NAME = "EstimatedProvider"

    @property
    def name(self) -> str:
        return self._NAME

    def research(self, niche_name: str, dna: OpportunityDNA,
                  ctx: dict) -> ProviderOutput:
        out = ProviderOutput(provider_name=self._NAME)
        n   = niche_name.lower()
        wc  = len(niche_name.split())
        depth = int(ctx.get("drill_depth", 0))

        # ── Business count ────────────────────────────────────────────────
        # First: try matching a DNA ecosystem node by keyword overlap
        best_node, best_overlap = None, 0
        for node in dna.ecosystem_nodes:
            words = {w for w in node.name.lower().split() if len(w) > 3}
            overlap = sum(1 for w in words if w in n)
            if overlap > best_overlap:
                best_overlap, best_node = overlap, node

        if best_node:
            supply_score = _int(best_node.supply_intensity)
            # supply_score 0-100 → approximate business count via exponential
            estimated_count = int(math.pow(10, (supply_score / 100.0) * 2.7))
            # Attenuate for specificity: each word beyond 2 halves the count
            specificity_factor = math.pow(0.60, max(0, wc - 2))
            estimated_count = max(5, int(estimated_count * specificity_factor))
            out.verified_business_count = _estimated(
                float(estimated_count), self._NAME,
                f"DNA node '{best_node.name}' supply_intensity="
                f"{best_node.supply_intensity.value} "
                f"→ {estimated_count} (specificity factor {specificity_factor:.2f})")
        else:
            # Fallback: pure word-count model
            estimated_count = max(5, int(_SUPPLY_BASE_COUNT * math.pow(0.55, max(0, wc - 1))))
            out.verified_business_count = _estimated(
                float(estimated_count), self._NAME,
                f"No DNA node matched — word-count model: "
                f"{_SUPPLY_BASE_COUNT} × 0.55^{max(0, wc-1)} ≈ {estimated_count}")

        # ── Search volume ─────────────────────────────────────────────────
        # Base from DNA commercial + local intent; attenuated by word count.
        ci   = _int(dna.intent.commercial_intent if dna.intent else None)
        li   = _int(dna.intent.local_intent       if dna.intent else None)
        vol_base = (ci * 0.5 + li * 0.5) / 100.0   # 0-1 quality index
        # Convert to approximate monthly search volume range
        # High-intent local niche: 500-10,000/mo; broad niche: up to 100k
        vol_ceiling = 100_000 * math.pow(0.45, max(0, wc - 1))
        estimated_vol = max(50, int(vol_ceiling * vol_base))
        out.estimated_search_volume = _estimated(
            float(estimated_vol), self._NAME,
            f"DNA commercial_intent={ci:.0f}, local_intent={li:.0f} "
            f"→ quality {vol_base:.2f} × ceiling {vol_ceiling:.0f} "
            f"≈ {estimated_vol}/mo")

        # ── CPC ───────────────────────────────────────────────────────────
        if dna.commercial:
            cpc = _CPC_BY_LEAD_VALUE.get(dna.commercial.lead_value, 2.5)
        else:
            cpc = 2.5
        out.avg_cpc_usd = _estimated(
            cpc, self._NAME,
            f"DNA lead_value="
            f"{dna.commercial.lead_value.value if dna.commercial else 'n/a'} "
            f"→ ${cpc:.2f}/click")

        # ── Advertiser demand ─────────────────────────────────────────────
        adv = _int(dna.intent.commercial_intent if dna.intent else None)
        out.advertiser_demand = _estimated(
            adv, self._NAME,
            f"DNA commercial_intent {adv:.0f}/100 as advertiser demand proxy")

        # ── SEO difficulty ─────────────────────────────────────────────────
        # Broader + aggregator-dominated = harder. Depth helps.
        agg_signals = ["restaurant", "hotel", "dentist", "doctor", "lawyer",
                         "attorney", "contractor", "gym", "plumber", "realtor"]
        agg_hit = any(s in n for s in agg_signals)
        seo_base = max(15.0, 80.0 - (wc - 1) * 8.0)
        if agg_hit:
            seo_base = min(95.0, seo_base + 12.0)
        depth_relief = min(depth * 7.0, 28.0)
        seo_est = round(max(10.0, seo_base - depth_relief), 1)
        out.seo_difficulty = _estimated(
            seo_est, self._NAME,
            f"breadth base {seo_base:.0f}"
            f"{' +12 aggregator' if agg_hit else ''}"
            f" −{depth_relief:.0f} depth relief = {seo_est}")

        # ── Backlink difficulty ───────────────────────────────────────────
        # Slightly softer than SEO difficulty for niche directories.
        bld = max(10.0, seo_est * 0.82)
        out.backlink_difficulty = _estimated(
            bld, self._NAME,
            f"SEO difficulty {seo_est:.0f} × 0.82 = {bld:.1f}")

        # ── Competitor count ──────────────────────────────────────────────
        # Fewer competitors exist for specific niches.
        comp_count = max(1.0, 12.0 * math.pow(0.70, max(0, wc - 2)))
        out.directory_competitor_count = _estimated(
            comp_count, self._NAME,
            f"12 base × 0.70^{max(0, wc-2)} word-specificity = {comp_count:.1f}")

        # ── Competitor authority (DA proxy) ───────────────────────────────
        # Narrow niches tend to have lower-DA incumbent directories.
        auth = max(15.0, 55.0 - (wc - 1) * 7.0)
        out.competitor_authority_avg = _estimated(
            auth, self._NAME,
            f"55 − {wc-1}×7 word-penalty = {auth:.0f} (DA proxy)")

        # ── Directory quality ─────────────────────────────────────────────
        # Most niche directories are thin; broader = more established tools.
        dq = max(20.0, 50.0 - (wc - 1) * 6.0)
        out.directory_quality_avg = _estimated(
            dq, self._NAME,
            f"50 − {wc-1}×6 = {dq:.0f} / 100 quality estimate")

        out.competitor_content_depth = _estimated(
            dq * 0.9, self._NAME,
            f"content depth ≈ quality × 0.9 = {dq*0.9:.0f}")

        out.mobile_quality_avg = _estimated(
            max(30.0, dq * 0.85), self._NAME,
            f"mobile quality ≈ quality × 0.85 = {dq*0.85:.0f}")

        # ── Commercial intent score ───────────────────────────────────────
        out.commercial_intent_score = _estimated(
            _int(dna.intent.commercial_intent if dna.intent else None),
            self._NAME,
            f"DNA commercial_intent → score")

        # ── Review signals ────────────────────────────────────────────────
        ri   = dna.intent.review_importance if dna.intent else None
        r_vol = float(_REVIEWS_BY_IMPORTANCE.get(ri, 18)) if ri else 18.0
        r_avg = 4.1 if r_vol >= 45 else 3.9    # high-review markets are competitive = higher avg
        out.review_avg_rating   = _estimated(r_avg, self._NAME,
            f"review_importance={ri.value if ri else 'n/a'} → avg {r_avg}")
        out.review_volume_avg   = _estimated(r_vol, self._NAME,
            f"review_importance={ri.value if ri else 'n/a'} → {r_vol:.0f} reviews/biz")

        # ── Online adoption ───────────────────────────────────────────────
        # High commercial intent → businesses have invested in digital presence.
        ci_norm = _int(dna.intent.commercial_intent if dna.intent else None) / 100.0
        out.online_booking_pct = _estimated(
            round(20.0 + ci_norm * 50.0, 1), self._NAME,
            f"commercial_intent {ci_norm:.2f} → {20 + ci_norm*50:.0f}% adopt booking")
        out.claimed_gbp_pct    = _estimated(
            round(30.0 + ci_norm * 45.0, 1), self._NAME,
            f"commercial_intent {ci_norm:.2f} → {30 + ci_norm*45:.0f}% claimed GBP")
        out.nap_consistency_pct = _estimated(
            round(40.0 + ci_norm * 35.0, 1), self._NAME,
            f"commercial_intent {ci_norm:.2f} → {40 + ci_norm*35:.0f}% NAP consistent")

        # ── Listing price ─────────────────────────────────────────────────
        lv_price = {
            Intensity.EXTREME:   95.0, Intensity.VERY_HIGH: 72.0,
            Intensity.HIGH:      48.0, Intensity.MEDIUM:    32.0,
            Intensity.LOW:       18.0, Intensity.VERY_LOW:  10.0,
        }
        price = lv_price.get(
            dna.commercial.lead_value if dna.commercial else None, 32.0)
        out.avg_listing_price_usd = _estimated(
            price, self._NAME,
            f"lead_value={dna.commercial.lead_value.value if dna.commercial else 'n/a'} "
            f"→ ${price:.0f}/mo listing price")

        # ── Affiliate programs ────────────────────────────────────────────
        aff_streams = sum(1 for s in (dna.commercial.streams if dna.commercial else [])
                          if "affiliate" in s.stream)
        out.affiliate_programs_found = _estimated(
            float(aff_streams), self._NAME,
            f"{aff_streams} affiliate-type stream(s) declared in DNA")

        # ── Gap scores ────────────────────────────────────────────────────
        # Lower directory quality → more UX and feature gaps → more opportunity.
        ux_gap      = round(max(10.0, 85.0 - dq), 1)
        feature_gap = round(max(10.0, 78.0 - dq * 0.85), 1)
        geo_gap     = round(max(10.0, 90.0 - dq - depth * 5.0), 1)
        out.ux_gap_score          = _estimated(ux_gap, self._NAME,
            f"85 − quality {dq:.0f} = {ux_gap:.0f}")
        out.feature_gap_score     = _estimated(feature_gap, self._NAME,
            f"78 − quality×0.85 = {feature_gap:.0f}")
        out.geo_coverage_gap_score = _estimated(geo_gap, self._NAME,
            f"90 − quality {dq:.0f} − depth {depth}×5 = {geo_gap:.0f}")

        return out
