"""
business_provider_verified.py — VerifiedBusinessProvider and the
Business Data Source adapter layer.

Implementation task only. Business Intelligence's public API
(business_intelligence.py) is NOT modified — this file adds a second
provider that satisfies the existing BusinessIntelligenceProvider
Protocol structurally, exactly like EstimatedBusinessIntelligenceProvider
already does. Business Intelligence's merge logic (VERIFIED > ESTIMATED
> UNKNOWN) already handles multiple providers with no changes needed;
this file simply gives it a second one to merge.

Architecture — two layers, separated on purpose:

    BusinessDataSource (adapter interface)
        The seam where a real data provider (Google Business Profile,
        Google Maps, Data Axle, Yelp Fusion) will eventually plug in.
        Its job is ONLY to fetch raw external data and report what it
        actually found. It knows nothing about TaggedValue, VERIFIED/
        ESTIMATED/UNKNOWN, or the BusinessIntelligenceProvider Protocol.

    VerifiedBusinessProvider (BusinessIntelligenceProvider)
        Wraps a BusinessDataSource. Its job is ONLY to translate whatever
        the data source found into TaggedValue-wrapped
        BusinessIntelligenceOutput, tagging every field VERIFIED when the
        data source actually returned it and UNKNOWN when it did not.
        Never fabricates a VERIFIED value. Satisfies the existing
        BusinessIntelligenceProvider Protocol unchanged, so it plugs
        directly into BusinessIntelligence(providers=[...]) alongside
        EstimatedBusinessIntelligenceProvider.

This separation means adding Google Business Profile later requires
writing ONE new BusinessDataSource subclass (the API call + auth) and
zero changes to VerifiedBusinessProvider, BusinessIntelligence, Scout,
Market Capacity, or anything downstream.

No API keys are hardcoded. No authentication is implemented. The only
data source shipped in this file, NullBusinessDataSource, performs no
network calls and always reports "nothing found" — which is the honest,
correct behavior until a real data source is wired in. With
NullBusinessDataSource, VerifiedBusinessProvider deterministically
returns UNKNOWN for every field, so Business Intelligence's merge
falls back to EstimatedBusinessIntelligenceProvider's ESTIMATED values,
exactly as VERIFIED > ESTIMATED > UNKNOWN dictates.

Future integration sketch (not implemented here):

    class GoogleBusinessProfileDataSource(BusinessDataSource):
        def __init__(self, api_key: str):
            self._api_key = api_key   # supplied by the caller, e.g. from
                                       # an environment variable — never
                                       # hardcoded in this codebase

        def fetch(self, niche_name, dna, ctx) -> BusinessDataSourceRecord:
            # real HTTP call to the Google Business Profile API here
            ...

    provider = VerifiedBusinessProvider(
        data_source=GoogleBusinessProfileDataSource(api_key=os.environ["GBP_API_KEY"]))
    engine = BusinessIntelligence(providers=[
        EstimatedBusinessIntelligenceProvider(), provider])
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from .dna.schema import OpportunityDNA
from .scout_providers import TaggedValue, _verified, _unknown
from .business_intelligence import BusinessIntelligenceOutput


# ─────────────────────────────────────────────────────────────────────────────
# Raw data source record — external data, not yet TaggedValue-wrapped
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class BusinessDataSourceRecord:
    """
    Raw fields a BusinessDataSource can report, before any VERIFIED/
    ESTIMATED/UNKNOWN tagging is applied. All fields optional — a data
    source populates only what it actually retrieved; None means "this
    source has no answer for this field," not zero.

    confidence_* fields are optional per-field confidence figures a real
    API might report (e.g. a places-search match-quality score). When a
    data source doesn't have one, leave it None and VerifiedBusinessProvider
    applies its own default VERIFIED confidence.
    """
    source_name: str            # e.g. "GoogleBusinessProfile", "DataAxle"

    business_count:      Optional[float] = None
    review_count:         Optional[float] = None
    rating_average:       Optional[float] = None
    geographic_coverage:  Optional[float] = None
    directory_presence:   Optional[float] = None

    confidence_business_count:      Optional[float] = None
    confidence_review_count:        Optional[float] = None
    confidence_rating_average:      Optional[float] = None
    confidence_geographic_coverage: Optional[float] = None
    confidence_directory_presence:  Optional[float] = None

    # Free-text rationale a data source can attach per field, surfaced in
    # the TaggedValue.rationale so evidence stays auditable. Optional.
    rationale_business_count:      Optional[str] = None
    rationale_review_count:        Optional[str] = None
    rationale_rating_average:      Optional[str] = None
    rationale_geographic_coverage: Optional[str] = None
    rationale_directory_presence:  Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# BusinessDataSource — the adapter interface real providers implement
# ─────────────────────────────────────────────────────────────────────────────

class BusinessDataSource(ABC):
    """
    Adapter interface for a real external business-data provider (Google
    Business Profile, Google Maps, Data Axle, Yelp Fusion, etc).

    Implementations own:
        - Authentication (API keys, OAuth) — none of that lives here or
          in VerifiedBusinessProvider. A real subclass takes whatever
          credentials it needs in its own __init__ and is responsible
          for using them safely.
        - The actual network call(s).
        - Translating the provider's native response into a
          BusinessDataSourceRecord.

    Implementations do NOT know about TaggedValue, VERIFIED/ESTIMATED/
    UNKNOWN, or BusinessIntelligenceOutput — that translation is
    VerifiedBusinessProvider's job, kept in one place regardless of how
    many data sources exist later.

    Must not raise for "no data found" — return a BusinessDataSourceRecord
    with the relevant fields left None. Raising is reserved for genuine
    failures (network error, auth failure); VerifiedBusinessProvider
    catches those and treats the whole fetch as unavailable (UNKNOWN
    everywhere) rather than crashing Business Intelligence.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name for this data source, used in
        TaggedValue.provider and audit trails."""
        ...

    @abstractmethod
    def fetch(self, niche_name: str, dna: OpportunityDNA,
               ctx: dict) -> BusinessDataSourceRecord:
        """
        Fetch whatever this data source can find for the niche. Fields
        it cannot answer must be left None in the returned record — never
        invent a plausible-looking number.
        """
        ...


class NullBusinessDataSource(BusinessDataSource):
    """
    Default data source. Performs no network calls, requires no
    credentials, and always reports that nothing was found. This is the
    honest behavior for "no real provider connected yet" — every field
    comes back None, which VerifiedBusinessProvider correctly turns into
    UNKNOWN TaggedValues, letting Business Intelligence's merge fall back
    to EstimatedBusinessIntelligenceProvider.

    Ships as the default so `VerifiedBusinessProvider()` is usable with
    zero configuration today, and swapping in a real data source later
    is a one-line constructor change.
    """

    @property
    def name(self) -> str:
        return "NullBusinessDataSource"

    def fetch(self, niche_name: str, dna: OpportunityDNA,
               ctx: dict) -> BusinessDataSourceRecord:
        return BusinessDataSourceRecord(source_name=self.name)


# ─────────────────────────────────────────────────────────────────────────────
# VerifiedBusinessProvider — satisfies BusinessIntelligenceProvider
# ─────────────────────────────────────────────────────────────────────────────

class VerifiedBusinessProvider:
    """
    Business Intelligence provider backed by a real (or, today, null)
    external data source. Structurally satisfies the existing
    BusinessIntelligenceProvider Protocol from business_intelligence.py
    — that file is not modified; this class simply implements the same
    `.name` property and `.research(niche_name, dna, ctx)` method shape,
    which is how BusinessIntelligenceProvider is already defined (a
    @runtime_checkable Protocol, satisfied structurally).

    Per field, per fetch:
        data source returned a value  -> VERIFIED TaggedValue
        data source returned None     -> UNKNOWN TaggedValue
        data source raised            -> UNKNOWN for every field (the
                                          whole fetch is treated as
                                          unavailable; the failure is
                                          never surfaced as fabricated
                                          VERIFIED data)

    Never fabricates VERIFIED data. If the data source doesn't know,
    this provider doesn't pretend to.
    """

    def __init__(self, data_source: Optional[BusinessDataSource] = None,
                  provider_name: Optional[str] = None):
        """
        data_source: any BusinessDataSource implementation. Defaults to
            NullBusinessDataSource() — safe, no credentials required,
            always reports "nothing found."
        provider_name: optional override for the name reported to
            Business Intelligence's provider_summaries. Defaults to
            "VerifiedBusinessProvider:<data_source.name>" so the audit
            trail shows exactly which real data source (if any) backed
            this provider's evidence.
        """
        self._data_source = data_source or NullBusinessDataSource()
        self._name = provider_name or f"VerifiedBusinessProvider:{self._data_source.name}"

    @property
    def name(self) -> str:
        return self._name

    def research(self, niche_name: str, dna: OpportunityDNA,
                  ctx: dict) -> BusinessIntelligenceOutput:
        """
        Fetch from the configured data source and translate its findings
        into a TaggedValue-wrapped BusinessIntelligenceOutput. Must not
        raise — BusinessIntelligence.research() already tolerates a
        provider raising by catching the exception and recording a
        failure marker, but this method additionally guards the fetch
        itself so a data-source outage degrades to "all UNKNOWN" rather
        than removing this provider's contribution outright.
        """
        try:
            record = self._data_source.fetch(niche_name, dna, ctx)
        except Exception:
            record = BusinessDataSourceRecord(source_name=self._data_source.name)

        out = BusinessIntelligenceOutput(provider_name=self._name)

        out.business_count = self._tag(
            record.business_count, "business_count",
            record.confidence_business_count, record.rationale_business_count,
            record.source_name)
        out.review_count = self._tag(
            record.review_count, "review_count",
            record.confidence_review_count, record.rationale_review_count,
            record.source_name)
        out.rating_average = self._tag(
            record.rating_average, "rating_average",
            record.confidence_rating_average, record.rationale_rating_average,
            record.source_name)
        out.geographic_coverage = self._tag(
            record.geographic_coverage, "geographic_coverage",
            record.confidence_geographic_coverage, record.rationale_geographic_coverage,
            record.source_name)
        out.directory_presence = self._tag(
            record.directory_presence, "directory_presence",
            record.confidence_directory_presence, record.rationale_directory_presence,
            record.source_name)

        return out

    # ── Internal ──────────────────────────────────────────────────────────

    def _tag(self, value: Optional[float], field_name: str,
              confidence: Optional[float], rationale: Optional[str],
              source_name: str) -> TaggedValue:
        """
        VERIFIED when the data source actually returned a value, UNKNOWN
        otherwise. This is the one place fabrication is prevented: there
        is no path from "data source returned None" to a VERIFIED tag.
        """
        if value is None:
            return _unknown(field_name)
        return _verified(
            float(value),
            provider=source_name,
            rationale=(rationale or
                        f"{field_name} verified via {source_name}."),
            confidence=confidence)
