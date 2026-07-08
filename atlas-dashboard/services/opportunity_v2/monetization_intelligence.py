"""
monetization_intelligence.py — Monetization Intelligence Engine.

One of the independent providers Scout orchestrates:

    Scout
      ├── Business Intelligence
      ├── Demand Intelligence        (not implemented yet — reserved)
      ├── Competition Intelligence
      └── Monetization Intelligence  ← this module

Single responsibility:
    Monetization Intelligence answers exactly one question:
        "What monetization infrastructure already exists in this market?"
    It measures affiliate_programs, lead_value, advertiser_presence,
    premium_listing_value, and sponsorship_potential — as observed or
    modeled evidence of monetization capacity. It NEVER computes a
    Monetization Score, Investment Grade, or revenue ceiling; those
    belong to Market Capacity and Valuation Engine downstream.

Architecture: identical pattern to business_intelligence.py and
    competition_intelligence.py. Provider Protocol, ProviderOutput,
    merge function (VERIFIED > ESTIMATED > UNKNOWN),
    EstimatedMonetizationIntelligenceProvider (deterministic today).

Future providers (documented, not implemented):
    CommonCrawlProvider    — affiliate program discovery via footprint scan
    BrightLocalProvider    — observed premium listing prices
    SEMrushProvider        — advertiser density, CPC-derived lead value
    Direct outreach/manual — sponsorship deal discovery

This module NEVER computes a Build Score, Investment Grade, or any
composite decision-oriented number. It returns evidence only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol, runtime_checkable

from .dna.schema import OpportunityDNA, Intensity
from .scout_providers import DataSource, TaggedValue, _estimated, _unknown


# ─────────────────────────────────────────────────────────────────────────────
# Provider output
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class MonetizationIntelligenceOutput:
    provider_name: str

    affiliate_programs:     Optional[TaggedValue] = None   # count of programs found
    lead_value:             Optional[TaggedValue] = None   # USD per lead
    advertiser_presence:    Optional[TaggedValue] = None   # 0-100, active advertiser evidence
    premium_listing_value:  Optional[TaggedValue] = None   # USD/mo observed or modeled price
    sponsorship_potential:  Optional[TaggedValue] = None   # 0-100


@runtime_checkable
class MonetizationIntelligenceProvider(Protocol):
    @property
    def name(self) -> str:
        ...

    def research(self, niche_name: str, dna: OpportunityDNA,
                  ctx: dict) -> MonetizationIntelligenceOutput:
        ...


# ─────────────────────────────────────────────────────────────────────────────
# Merging
# ─────────────────────────────────────────────────────────────────────────────

_SOURCE_PRIORITY = {DataSource.VERIFIED: 3, DataSource.ESTIMATED: 2, DataSource.UNKNOWN: 1}


def _best(a: Optional[TaggedValue], b: Optional[TaggedValue]) -> Optional[TaggedValue]:
    if a is None:
        return b
    if b is None:
        return a
    return a if _SOURCE_PRIORITY[a.source] >= _SOURCE_PRIORITY[b.source] else b


def merge_monetization_outputs(
        outputs: list[MonetizationIntelligenceOutput]) -> MonetizationIntelligenceOutput:
    merged = MonetizationIntelligenceOutput(provider_name="merged")
    for out in outputs:
        merged.affiliate_programs    = _best(merged.affiliate_programs,    out.affiliate_programs)
        merged.lead_value            = _best(merged.lead_value,            out.lead_value)
        merged.advertiser_presence   = _best(merged.advertiser_presence,   out.advertiser_presence)
        merged.premium_listing_value = _best(merged.premium_listing_value, out.premium_listing_value)
        merged.sponsorship_potential = _best(merged.sponsorship_potential, out.sponsorship_potential)
    return merged


# ─────────────────────────────────────────────────────────────────────────────
# Estimated provider
# ─────────────────────────────────────────────────────────────────────────────

_INTENSITY_NUM = {
    Intensity.EXTREME:   98, Intensity.VERY_HIGH: 85,
    Intensity.HIGH:      68, Intensity.MEDIUM:    50,
    Intensity.LOW:       30, Intensity.VERY_LOW:  12,
}


def _int(i: Optional[Intensity], default: float = 50.0) -> float:
    return float(_INTENSITY_NUM.get(i, default)) if i is not None else default


# Lead value by DNA lead_value intensity (USD per lead), the same
# documented tier table used elsewhere in Atlas for consistency.
_LEAD_VALUE_USD_BY_INTENSITY = {
    Intensity.EXTREME:   150.0,
    Intensity.VERY_HIGH:  85.0,
    Intensity.HIGH:       45.0,
    Intensity.MEDIUM:     18.0,
    Intensity.LOW:         6.0,
    Intensity.VERY_LOW:   2.0,
}

# Premium listing price proxy by DNA lead_value intensity.
_LISTING_PRICE_BY_INTENSITY = {
    Intensity.EXTREME:   95.0, Intensity.VERY_HIGH: 72.0,
    Intensity.HIGH:      48.0, Intensity.MEDIUM:    32.0,
    Intensity.LOW:       18.0, Intensity.VERY_LOW:  10.0,
}


class EstimatedMonetizationIntelligenceProvider:
    """Deterministic inference from DNA. All outputs ESTIMATED."""

    _NAME = "EstimatedMonetizationIntelligenceProvider"

    @property
    def name(self) -> str:
        return self._NAME

    def research(self, niche_name: str, dna: OpportunityDNA,
                  ctx: dict) -> MonetizationIntelligenceOutput:
        out = MonetizationIntelligenceOutput(provider_name=self._NAME)

        # ── Affiliate programs (count of DNA-declared affiliate-type streams
        #    as a proxy for "programs known to exist in this vertical") ────
        aff_streams = sum(
            1 for s in (dna.commercial.streams if dna.commercial else [])
            if "affiliate" in s.stream)
        out.affiliate_programs = _estimated(
            float(aff_streams), self._NAME,
            f"{aff_streams} affiliate-type stream(s) declared in DNA "
            f"(proxy for known program availability — not a live scan)",
            confidence=30.0)   # explicitly low: this is a DNA proxy, not
                                 # a real footprint scan for live programs

        # ── Lead value ──────────────────────────────────────────────────────
        lv_intensity = dna.commercial.lead_value if dna.commercial else Intensity.MEDIUM
        lead_val = _LEAD_VALUE_USD_BY_INTENSITY.get(lv_intensity, 18.0)
        out.lead_value = _estimated(
            lead_val, self._NAME,
            f"DNA lead_value={lv_intensity.value} → ${lead_val:.2f}/lead")

        # ── Advertiser presence ─────────────────────────────────────────────
        ci = _int(dna.intent.commercial_intent if dna.intent else None)
        out.advertiser_presence = _estimated(
            ci, self._NAME,
            f"DNA commercial_intent {ci:.0f}/100 used as advertiser "
            f"presence proxy (no live ad-auction observation available)")

        # ── Premium listing value ───────────────────────────────────────────
        price = _LISTING_PRICE_BY_INTENSITY.get(lv_intensity, 32.0)
        out.premium_listing_value = _estimated(
            price, self._NAME,
            f"DNA lead_value={lv_intensity.value} → ${price:.0f}/mo "
            f"modeled premium listing price")

        # ── Sponsorship potential ───────────────────────────────────────────
        rec = _int(dna.commercial.recurring_revenue_potential if dna.commercial else None)
        sponsorship = round(min(100.0, rec * 0.75 + ci * 0.25), 1)
        out.sponsorship_potential = _estimated(
            sponsorship, self._NAME,
            f"recurring_revenue_potential {rec:.0f}×0.75 + "
            f"commercial_intent {ci:.0f}×0.25 = {sponsorship:.1f}/100")

        return out


# ─────────────────────────────────────────────────────────────────────────────
# Result — evidence only, no scoring
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class MonetizationIntelligenceResult:
    """Pure evidence about monetization infrastructure. No scores,
    grades, or recommendations — those belong to Market Capacity /
    Valuation Engine / Business Architect."""
    affiliate_programs:    TaggedValue
    lead_value:            TaggedValue
    advertiser_presence:   TaggedValue
    premium_listing_value: TaggedValue
    sponsorship_potential: TaggedValue

    providers_used:   list[str]
    verified_fields:  list[str]
    estimated_fields: list[str]
    unknown_fields:   list[str]


class MonetizationIntelligence:
    """Stateless orchestrator over registered Monetization Intelligence providers."""

    def __init__(self, providers: Optional[list] = None):
        self._providers = providers if providers is not None else [
            EstimatedMonetizationIntelligenceProvider()]

    def research(self, niche_name: str, dna: OpportunityDNA,
                  ctx: dict) -> MonetizationIntelligenceResult:
        outputs, used = [], []
        for provider in self._providers:
            try:
                outputs.append(provider.research(niche_name, dna, ctx))
                used.append(provider.name)
            except Exception as e:
                used.append(f"{provider.name}[FAILED:{type(e).__name__}]")

        merged = merge_monetization_outputs(outputs)
        fields = {
            "affiliate_programs":    merged.affiliate_programs    or _unknown("affiliate_programs"),
            "lead_value":            merged.lead_value            or _unknown("lead_value"),
            "advertiser_presence":   merged.advertiser_presence   or _unknown("advertiser_presence"),
            "premium_listing_value": merged.premium_listing_value or _unknown("premium_listing_value"),
            "sponsorship_potential": merged.sponsorship_potential or _unknown("sponsorship_potential"),
        }
        verified_f  = [k for k, v in fields.items() if v.is_verified]
        estimated_f = [k for k, v in fields.items() if v.is_estimated]
        unknown_f   = [k for k, v in fields.items() if v.is_unknown]

        return MonetizationIntelligenceResult(
            affiliate_programs=fields["affiliate_programs"],
            lead_value=fields["lead_value"],
            advertiser_presence=fields["advertiser_presence"],
            premium_listing_value=fields["premium_listing_value"],
            sponsorship_potential=fields["sponsorship_potential"],
            providers_used=used,
            verified_fields=verified_f,
            estimated_fields=estimated_f,
            unknown_fields=unknown_f,
        )


_default_engine = MonetizationIntelligence()


def run_monetization_intelligence(niche_name: str, dna: OpportunityDNA, ctx: dict,
                                    providers: Optional[list] = None) -> MonetizationIntelligenceResult:
    """Run Monetization Intelligence for one niche. providers=None uses
    the default EstimatedMonetizationIntelligenceProvider."""
    engine = MonetizationIntelligence(providers) if providers is not None else _default_engine
    return engine.research(niche_name, dna, ctx)


def monetization_intelligence_to_dict(result: MonetizationIntelligenceResult) -> dict:
    def tv(t: TaggedValue) -> dict:
        return {"value": t.value, "source": t.source.value, "provider": t.provider,
                 "rationale": t.rationale, "confidence": t.confidence}
    return {
        "affiliate_programs": tv(result.affiliate_programs),
        "lead_value": tv(result.lead_value),
        "advertiser_presence": tv(result.advertiser_presence),
        "premium_listing_value": tv(result.premium_listing_value),
        "sponsorship_potential": tv(result.sponsorship_potential),
        "providers_used": result.providers_used,
        "verified_fields": result.verified_fields,
        "estimated_fields": result.estimated_fields,
        "unknown_fields": result.unknown_fields,
    }
