"""
google_places_business_data_source.py — GooglePlacesBusinessDataSource.

The first REAL BusinessDataSource implementation, satisfying the adapter
interface defined in business_provider_verified.py without any changes
to that file, VerifiedBusinessProvider, Business Intelligence, Scout,
Market Capacity, or anything downstream.

Usage — replacing NullBusinessDataSource with this at the call site:

    from services.opportunity_v2.business_provider_verified import VerifiedBusinessProvider
    from services.opportunity_v2.google_places_business_data_source import GooglePlacesBusinessDataSource

    provider = VerifiedBusinessProvider(
        data_source=GooglePlacesBusinessDataSource(api_key=os.environ.get("GOOGLE_PLACES_API_KEY")))

    engine = BusinessIntelligence(providers=[
        EstimatedBusinessIntelligenceProvider(), provider])

That's it — nothing else in Atlas needs to know this data source exists.

API used: Places API (New) Text Search — POST https://places.googleapis.com/v1/places:searchText
    https://developers.google.com/maps/documentation/places/web-service/text-search

What this data source collects, and what it honestly cannot:
    Business Count         — number of Places results matched (bounded,
                              see _MAX_RESULT_PAGES below). Labeled in the
                              rationale as a matched-result count, not a
                              claim of exhaustive market census.
    Average Rating          — mean of the `rating` field across results
                              that have one.
    Average Review Count    — mean of `userRatingCount` across results
                              that have one.
    Geographic Coverage     — derived from the number of distinct
                              localities found in returned addresses.
                              A deterministic, documented proxy — not a
                              claim of precise geographic modeling.
    Directory Presence      — Places API has NO signal for whether these
                              businesses are listed on third-party
                              directories (Yelp, industry directories,
                              etc). This field is intentionally left None
                              on every fetch, which VerifiedBusinessProvider
                              correctly converts to UNKNOWN. Fabricating a
                              number here to fill the field would violate
                              the one hard rule this data source exists to
                              respect: never invent VERIFIED evidence.

Safety and cost discipline:
    - No API key is ever hardcoded. The constructor requires the caller
      to supply one (e.g. from an environment variable); if none is
      supplied, fetch() returns immediately with everything None and
      never attempts a network call.
    - The field mask sent to Google is minimal and explicit
      (_FIELD_MASK below) because Places API (New) bills per requested
      field group — requesting only what this data source actually uses
      controls cost.
    - Result pages are capped (_MAX_RESULT_PAGES) to bound both latency
      and API spend per fetch call. This is a deliberate, documented
      constant, not an oversight.
    - Every failure mode (missing key, network error, timeout, non-200
      response, malformed JSON, unexpected schema) degrades to "no data
      found" rather than raising. VerifiedBusinessProvider already
      guards against a data source raising, but this class defends
      itself first so a partial/degraded response never gets
      misinterpreted as a hard failure of the whole fetch.
"""

from __future__ import annotations

import logging
from typing import Callable, Optional, Union

from .dna.schema import OpportunityDNA
from .business_provider_verified import BusinessDataSource, BusinessDataSourceRecord
from .scout_query_builder import ScoutQuerySet

try:
    import requests
    _REQUESTS_AVAILABLE = True
except ImportError:                      # pragma: no cover - environment-dependent
    requests = None                      # type: ignore[assignment]
    _REQUESTS_AVAILABLE = False

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Named constants — every choice here has a documented, deliberate reason
# ─────────────────────────────────────────────────────────────────────────────

_SEARCH_TEXT_URL = "https://places.googleapis.com/v1/places:searchText"

# Minimal field mask: only what this data source actually reads. Places
# API (New) bills by requested field group (Essentials/Pro/Enterprise
# tiers) — requesting narrowly keeps this call in the cheapest tier that
# still covers rating, review count, and address/locality data.
_FIELD_MASK = (
    "places.id,"
    "places.rating,"
    "places.userRatingCount,"
    "places.formattedAddress,"
    "places.addressComponents"
)

# Bound API spend and latency per fetch. Text Search (New) returns up to
# 20 places per page. Two pages (40 results) is enough to compute a
# meaningful average rating / review count and locality spread without
# turning one opportunity's evidence-gathering into an unbounded, costly
# crawl. Override via the constructor if a caller deliberately wants more.
_DEFAULT_MAX_RESULT_PAGES = 2
_RESULTS_PER_PAGE = 20

_DEFAULT_TIMEOUT_SECONDS = 8.0

# Geographic coverage scale: each distinct locality found among matched
# results contributes this many points, capped at 100. A niche whose
# results span 5+ distinct cities/towns reads as broadly geographically
# covered; a niche confined to one locality reads as narrow. This is a
# deterministic proxy, documented here and in the returned rationale —
# not a precise geographic model.
_COVERAGE_POINTS_PER_LOCALITY = 20.0
_COVERAGE_MAX = 100.0

# Bounds how many alternate queries (from a configured query_builder) this
# data source will retry if the primary query returns zero results. Kept
# small and explicit for the same reason _MAX_RESULT_PAGES is bounded:
# every additional query is additional real API spend. Default of 1 means
# "try the primary, and if that finds nothing, try exactly one alternate
# before giving up" — a modest, cost-conscious improvement over trying
# only the raw niche_name, not an unbounded retry loop.
_DEFAULT_MAX_ALTERNATE_ATTEMPTS = 1


class GooglePlacesBusinessDataSource(BusinessDataSource):
    """
    Real BusinessDataSource backed by the Google Places API (New) Text
    Search endpoint. Satisfies the BusinessDataSource interface exactly;
    no changes needed anywhere it plugs in.

    Optional query improvement (this task):
        By default (query_builder=None, query_set=None), this data
        source searches the raw niche_name exactly as it always has —
        zero behavior change for any existing caller.

        Pass query_builder=build_scout_queries (or any callable with the
        signature (niche_name, dna, ctx) -> ScoutQuerySet) to have this
        data source clean up the search text before calling Google:
        it searches primary_query first, and — bounded by
        max_alternate_attempts — falls back to alternate_queries only if
        the primary query returns zero results. This is purely an
        internal improvement to what text gets sent to Google; the
        public fetch(niche_name, dna, ctx) -> BusinessDataSourceRecord
        contract is completely unchanged.

        Alternatively pass a precomputed query_set=ScoutQuerySet(...) if
        the caller already built one and wants every fetch() call on
        this instance to use it verbatim, regardless of the niche_name
        argument. query_set takes precedence over query_builder if both
        are supplied. Use this only when a single data source instance
        is dedicated to one fixed niche's queries — for the normal case
        of one instance reused across many niches, use query_builder.
    """

    def __init__(self, api_key: Optional[str] = None,
                  max_result_pages: int = _DEFAULT_MAX_RESULT_PAGES,
                  timeout_seconds: float = _DEFAULT_TIMEOUT_SECONDS,
                  session: Optional["requests.Session"] = None,
                  query_builder: Optional[Callable[[str, OpportunityDNA, dict], ScoutQuerySet]] = None,
                  query_set: Optional[ScoutQuerySet] = None,
                  max_alternate_attempts: int = _DEFAULT_MAX_ALTERNATE_ATTEMPTS):
        """
        api_key: caller-supplied Google Places API key (e.g. read from
            an environment variable by the caller — never hardcoded in
            this codebase). None is valid and means "not configured":
            fetch() will always return an empty record without making
            any network call.
        max_result_pages: caps how many pages of results (20 each) this
            data source will request per fetch. Bounds both API cost and
            latency. Defaults to a conservative 2 pages.
        timeout_seconds: per-request timeout passed to the HTTP client.
        session: optional pre-configured requests.Session (e.g. for
            connection pooling or test injection). Defaults to a plain
            requests.Session() created lazily on first use.
        query_builder: optional callable (niche_name, dna, ctx) ->
            ScoutQuerySet, e.g. scout_query_builder.build_scout_queries.
            When supplied, fetch() uses the returned primary_query (and,
            on zero results, up to max_alternate_attempts of
            alternate_queries) instead of the raw niche_name. None
            (default) preserves the original raw-niche_name behavior
            exactly.
        query_set: optional precomputed ScoutQuerySet used for every
            fetch() call regardless of the niche_name argument. Takes
            precedence over query_builder when both are given.
        max_alternate_attempts: bounds how many alternate queries are
            tried if the primary query returns zero results. Default 1.
        """
        self._api_key = api_key
        self._max_result_pages = max(1, int(max_result_pages))
        self._timeout_seconds = timeout_seconds
        self._session = session
        self._query_builder = query_builder
        self._query_set = query_set
        self._max_alternate_attempts = max(0, int(max_alternate_attempts))

    @property
    def name(self) -> str:
        return "GooglePlacesBusinessDataSource"

    # ── BusinessDataSource contract ──────────────────────────────────────────

    def fetch(self, niche_name: str, dna: OpportunityDNA,
               ctx: dict) -> BusinessDataSourceRecord:
        """
        Fetch business evidence for this niche from Google Places API
        (New) Text Search. Never raises: every failure mode returns a
        BusinessDataSourceRecord with the affected fields left None.

        Signature and return type are unchanged regardless of whether a
        query_builder or query_set is configured — only the search text
        actually sent to Google differs internally.
        """
        empty = BusinessDataSourceRecord(source_name=self.name)

        if not self._api_key:
            logger.info(
                "GooglePlacesBusinessDataSource: no API key configured — "
                "skipping network call, returning no data.")
            return empty

        if not _REQUESTS_AVAILABLE:
            logger.warning(
                "GooglePlacesBusinessDataSource: 'requests' library not "
                "available — returning no data.")
            return empty

        search_text, fallback_texts = self._resolve_search_texts(niche_name, dna, ctx)

        places: list[dict] = []
        tried: list[str] = []
        for text in [search_text] + fallback_texts[:self._max_alternate_attempts]:
            tried.append(text)
            try:
                places = self._search_places(text, ctx)
            except Exception as e:
                # Any network error, timeout, non-200, or malformed
                # response lands here. Log and degrade to "no data"
                # rather than raise — VerifiedBusinessProvider treats
                # this identically to a data source that legitimately
                # found nothing.
                logger.warning(
                    "GooglePlacesBusinessDataSource: fetch failed for "
                    "'%s': %s", text, e)
                return empty
            if places:
                break

        if not places:
            return BusinessDataSourceRecord(
                source_name=self.name,
                rationale_business_count=(
                    f"Google Places Text Search returned 0 results for "
                    f"{', '.join(repr(t) for t in tried)}."))

        return self._to_record(search_text, places)

    def _resolve_search_texts(self, niche_name: str, dna: OpportunityDNA,
                                ctx: dict) -> tuple[str, list[str]]:
        """
        Determine the primary search text and any bounded fallback texts.

        query_set (precomputed) takes precedence over query_builder.
        Neither configured -> (niche_name, []), i.e. the original,
        unmodified behavior. A query_builder that raises is treated the
        same as "not configured" — a broken query builder must never
        prevent this data source from at least trying the raw niche_name.
        """
        if self._query_set is not None:
            return self._query_set.primary_query, list(self._query_set.alternate_queries)

        if self._query_builder is not None:
            try:
                qs = self._query_builder(niche_name, dna, ctx)
                return qs.primary_query, list(qs.alternate_queries)
            except Exception as e:
                logger.warning(
                    "GooglePlacesBusinessDataSource: query_builder failed "
                    "for '%s' (%s) — falling back to raw niche_name.",
                    niche_name, e)

        return niche_name, []

    # ── Internal: network call ───────────────────────────────────────────────

    def _session_or_new(self) -> "requests.Session":
        if self._session is None:
            self._session = requests.Session()
        return self._session

    def _search_places(self, niche_name: str, ctx: dict) -> list[dict]:
        """
        Call Places API (New) Text Search, following pagination up to
        _max_result_pages. Raises on network/HTTP errors so fetch()'s
        try/except can convert them into an empty record uniformly —
        this method itself does not swallow errors, keeping the failure
        handling in one place.
        """
        session = self._session_or_new()
        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self._api_key,
            "X-Goog-FieldMask": _FIELD_MASK,
        }

        all_places: list[dict] = []
        body: dict = {"textQuery": niche_name, "pageSize": _RESULTS_PER_PAGE}

        # Optional location bias, only if the caller's ctx supplies one —
        # this data source never guesses coordinates on its own.
        loc_bias = ctx.get("location_bias") if ctx else None
        if isinstance(loc_bias, dict) and {"lat", "lng"} <= loc_bias.keys():
            body["locationBias"] = {
                "circle": {
                    "center": {"latitude": loc_bias["lat"], "longitude": loc_bias["lng"]},
                    "radius": float(loc_bias.get("radius_meters", 25000)),
                }
            }

        page_token = None
        for _ in range(self._max_result_pages):
            if page_token:
                body["pageToken"] = page_token

            response = session.post(
                _SEARCH_TEXT_URL, headers=headers, json=body,
                timeout=self._timeout_seconds)

            if response.status_code != 200:
                # Non-200 (bad key -> 403/400, rate limit -> 429, server
                # error -> 5xx) is a real failure. Raise so fetch()'s
                # except-block records it and returns an empty record —
                # never fabricate results from a failed call.
                raise RuntimeError(
                    f"Places API returned HTTP {response.status_code}: "
                    f"{response.text[:200]}")

            data = response.json()
            page_places = data.get("places", [])
            all_places.extend(page_places)

            page_token = data.get("nextPageToken")
            if not page_token or not page_places:
                break

        return all_places

    # ── Internal: translate Places API results into a raw record ────────────

    def _to_record(self, niche_name: str, places: list[dict]) -> BusinessDataSourceRecord:
        """
        Convert raw Places API results into a BusinessDataSourceRecord.
        Every field is computed only from data actually present in the
        response; a field with no usable underlying data is left None.
        """
        matched_count = len(places)

        ratings = [p["rating"] for p in places if isinstance(p.get("rating"), (int, float))]
        review_counts = [p["userRatingCount"] for p in places
                          if isinstance(p.get("userRatingCount"), (int, float))]

        rating_average = (sum(ratings) / len(ratings)) if ratings else None
        review_count_average = (sum(review_counts) / len(review_counts)) if review_counts else None

        localities = self._extract_localities(places)
        geographic_coverage = (
            min(_COVERAGE_MAX, len(localities) * _COVERAGE_POINTS_PER_LOCALITY)
            if localities else None)

        return BusinessDataSourceRecord(
            source_name=self.name,

            business_count=float(matched_count) if matched_count else None,
            rationale_business_count=(
                f"Google Places Text Search matched {matched_count} result(s) "
                f"for '{niche_name}' (up to {self._max_result_pages} page(s) "
                f"of {_RESULTS_PER_PAGE} requested) — a matched-result count, "
                f"not an exhaustive market census."),

            rating_average=rating_average,
            rationale_rating_average=(
                f"Mean of {len(ratings)} rated result(s) out of {matched_count} "
                f"matched." if ratings else None),

            review_count=review_count_average,
            rationale_review_count=(
                f"Mean user rating count across {len(review_counts)} result(s) "
                f"that reported one." if review_counts else None),

            geographic_coverage=geographic_coverage,
            rationale_geographic_coverage=(
                f"{len(localities)} distinct locality(ies) found among matched "
                f"results ({_COVERAGE_POINTS_PER_LOCALITY:.0f} pts each, capped "
                f"at {_COVERAGE_MAX:.0f}): {', '.join(sorted(localities)[:8])}"
                if localities else None),

            # directory_presence intentionally omitted (stays None): Places
            # API has no signal for third-party directory listing presence.
        )

    def _extract_localities(self, places: list[dict]) -> set[str]:
        """
        Pull distinct locality names from addressComponents when present.
        Returns an empty set (not a guess) if no place in the response
        includes a locality-type address component.
        """
        localities: set[str] = set()
        for place in places:
            for component in place.get("addressComponents", []) or []:
                types = component.get("types", [])
                if "locality" in types:
                    name = component.get("longText") or component.get("shortText")
                    if name:
                        localities.add(name)
                    break
        return localities
