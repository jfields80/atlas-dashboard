"""AES-DATA-004A discovery -- deterministic coverage report (Task 11).

Every count here has an established, disclosed denominator (the query plan
actually built, the candidates actually produced). Never renders a market-
completeness percentage -- there is no way to know the true size of the
real-world Columbus business universe, so none is claimed (doctrine: use
"discovered coverage" / "query saturation" / "unresolved candidate count",
never "78% complete").
"""

from __future__ import annotations

import html
import json
from itertools import combinations
from typing import Dict, Sequence, Tuple

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery.market_config import MarketConfig
from scripts.pettripfinder.discovery.models import CoverageSummary, DiscoveryCandidate
from scripts.pettripfinder.discovery.models import DiscoverySourceQuery
from scripts.pettripfinder.discovery.provider_result import ProviderQueryResult


def _tally(items) -> Tuple[Tuple[str, int], ...]:
    counts: Dict[str, int] = {}
    for k in items:
        counts[k] = counts.get(k, 0) + 1
    return tuple(sorted(counts.items()))


def _cell_municipality_map(market: MarketConfig) -> Dict[str, str]:
    return {cell.cell_id: cell.municipality for cell in market.cells}


def build_coverage_summary(
    *,
    market: MarketConfig,
    observed_at: str,
    providers_enabled: Sequence[str],
    google_key_present: bool,
    foursquare_key_present: bool,
    planned_queries: Sequence[DiscoverySourceQuery],
    query_results: Sequence[ProviderQueryResult],
    candidates: Sequence[DiscoveryCandidate],
) -> CoverageSummary:
    results_by_query_id = {r.query_id: r for r in query_results}
    query_completion = tuple(sorted(
        (q.query_id, results_by_query_id[q.query_id].state if q.query_id in results_by_query_id
         else (C.QUERY_STATE_DISABLED if not q.enabled else C.QUERY_STATE_PLANNED))
        for q in planned_queries
    ))
    provider_errors = tuple(sorted(
        (r.query_id, r.error) for r in query_results if r.error
    ))

    records_by_provider = _tally(
        r.provider for res in query_results for r in res.records
    )
    request_counts = _tally(
        p for res in query_results for p in ([res.provider] * res.requests_made)
    )
    page_counts = _tally(
        p for res in query_results for p in ([res.provider] * res.pages_fetched)
    )
    cache_hits = _tally(
        p for res in query_results for p in ([res.provider] * res.cache_hits)
    )
    estimated_billable_google = sum(
        r.requests_made for r in query_results if r.provider == C.PROVIDER_GOOGLE_PLACES
    )

    total_raw_records = sum(len(res.records) for res in query_results)
    unique_candidates = len(candidates)
    duplicates_merged = max(0, total_raw_records - unique_candidates)

    provider_only: Dict[str, int] = {}
    overlap_pairs: Dict[str, int] = {}
    for cand in candidates:
        providers_here = sorted({p for p, _pid in cand.provider_ids})
        if len(providers_here) == 1:
            provider_only[providers_here[0]] = provider_only.get(providers_here[0], 0) + 1
        for a, b in combinations(providers_here, 2):
            key = "%s+%s" % (a, b)
            overlap_pairs[key] = overlap_pairs.get(key, 0) + 1

    candidates_with_website = sum(
        1 for c in candidates if c.website_state == C.WEBSITE_STATE_OFFICIAL_PRESENT)
    candidates_without_website = unique_candidates - candidates_with_website
    conflicts_requiring_review = sum(
        1 for c in candidates if c.review_state == C.REVIEW_STATE_NEEDS_REVIEW)

    cell_to_municipality = _cell_municipality_map(market)
    municipality_counts: Dict[str, int] = {}
    category_counts: Dict[str, int] = {}
    for cand in candidates:
        cell_id = ""
        if cand.source_records:
            cell_id = cand.source_records[0].provenance_dict().get("cell_id", "")
        municipality = cell_to_municipality.get(cell_id, "unknown")
        municipality_counts[municipality] = municipality_counts.get(municipality, 0) + 1
        for category in cand.category_candidates:
            category_counts[category] = category_counts.get(category, 0) + 1

    return CoverageSummary(
        market_id=market.market_id, observed_at=observed_at,
        providers_enabled=tuple(providers_enabled),
        credentials_available=(
            (C.PROVIDER_GOOGLE_PLACES, google_key_present),
            (C.PROVIDER_OPENSTREETMAP, True),
            (C.PROVIDER_FOURSQUARE, foursquare_key_present),
        ),
        records_by_provider=records_by_provider,
        unique_candidates=unique_candidates,
        overlap_by_provider_pair=tuple(sorted(overlap_pairs.items())),
        provider_only_candidates=tuple(sorted(provider_only.items())),
        candidates_with_website=candidates_with_website,
        candidates_without_website=candidates_without_website,
        duplicates_merged=duplicates_merged,
        conflicts_requiring_review=conflicts_requiring_review,
        counts_by_category=tuple(sorted(category_counts.items())),
        counts_by_municipality=tuple(sorted(municipality_counts.items())),
        query_completion=query_completion,
        provider_errors=provider_errors,
        request_counts=request_counts,
        page_counts=page_counts,
        cache_hits=cache_hits,
        estimated_billable_google_calls=estimated_billable_google,
    )


def render_coverage_json(summary: CoverageSummary) -> str:
    data = {
        "market_id": summary.market_id,
        "observed_at": summary.observed_at,
        "providers_enabled": list(summary.providers_enabled),
        "credentials_available": dict(summary.credentials_available),
        "records_by_provider": dict(summary.records_by_provider),
        "unique_candidates": summary.unique_candidates,
        "overlap_by_provider_pair": dict(summary.overlap_by_provider_pair),
        "provider_only_candidates": dict(summary.provider_only_candidates),
        "candidates_with_website": summary.candidates_with_website,
        "candidates_without_website": summary.candidates_without_website,
        "duplicates_merged": summary.duplicates_merged,
        "conflicts_requiring_review": summary.conflicts_requiring_review,
        "counts_by_category": dict(summary.counts_by_category),
        "counts_by_municipality": dict(summary.counts_by_municipality),
        "query_completion": dict(summary.query_completion),
        "provider_errors": dict(summary.provider_errors),
        "request_counts": dict(summary.request_counts),
        "page_counts": dict(summary.page_counts),
        "cache_hits": dict(summary.cache_hits),
        "estimated_billable_google_calls": summary.estimated_billable_google_calls,
        "disclosure": (
            "Counts describe the query plan actually executed and the "
            "candidates it produced -- not the true size of the real-world "
            "market. No completeness percentage is claimed."
        ),
    }
    return json.dumps(data, sort_keys=True, indent=2)


def render_coverage_html(summary: CoverageSummary) -> str:
    e = html.escape
    total_planned = len(summary.query_completion)
    completed = sum(1 for _qid, state in summary.query_completion
                    if state == C.QUERY_STATE_COMPLETED)
    saturation = "%d/%d" % (completed, total_planned) if total_planned else "0/0"

    def rows(pairs, cols=("key", "value")):
        if not pairs:
            return "<tr><td colspan=\"2\" class=\"muted\">(none)</td></tr>"
        return "".join(
            "<tr><td>%s</td><td>%s</td></tr>" % (e(str(k)), e(str(v)))
            for k, v in pairs
        )

    return """<!doctype html><html><head><meta charset="utf-8">
<title>Discovery coverage -- %s</title>
<style>body{font-family:sans-serif;margin:2em;}table{border-collapse:collapse;margin-bottom:1.5em;}
td,th{border:1px solid #ccc;padding:4px 10px;text-align:left;}.muted{color:#888;}</style>
</head><body>
<h1>Discovery coverage report</h1>
<p>market: <b>%s</b> &nbsp; observed_at: <b>%s</b></p>
<p class="muted">%s</p>

<h2>Credentials available</h2>
<table>%s</table>

<h2>Query saturation</h2>
<p><b>%s</b> planned queries completed (a count of the query plan actually built for this run -- not a market-completeness estimate).</p>

<h2>Records by provider (raw, pre-dedup)</h2>
<table>%s</table>

<h2>Unique candidates</h2>
<p><b>%d</b> unique candidates from <b>%d</b> raw records (<b>%d</b> duplicates merged).</p>

<h2>Cross-provider overlap</h2>
<table>%s</table>

<h2>Provider-only candidates</h2>
<table>%s</table>

<h2>Website readiness</h2>
<p>with website: <b>%d</b> &nbsp; without: <b>%d</b></p>

<h2>Unresolved candidate count</h2>
<p><b>%d</b> candidates flagged NEEDS_REVIEW.</p>

<h2>Counts by category</h2>
<table>%s</table>

<h2>Counts by municipality</h2>
<table>%s</table>

<h2>Request / page / cache accounting</h2>
<table><tr><th>metric</th><th>provider</th><th>count</th></tr>%s</table>

<h2>Estimated billable Google calls (actual, this run)</h2>
<p><b>%d</b></p>

<h2>Provider errors</h2>
<table>%s</table>
</body></html>""" % (
        e(summary.market_id), e(summary.market_id), e(summary.observed_at),
        e("Counts describe the query plan actually executed and the candidates it produced -- "
          "not the true size of the real-world market. No completeness percentage is claimed."),
        rows(summary.credentials_available),
        saturation,
        rows(summary.records_by_provider),
        summary.unique_candidates, summary.unique_candidates + summary.duplicates_merged,
        summary.duplicates_merged,
        rows(summary.overlap_by_provider_pair),
        rows(summary.provider_only_candidates),
        summary.candidates_with_website, summary.candidates_without_website,
        summary.conflicts_requiring_review,
        rows(summary.counts_by_category),
        rows(summary.counts_by_municipality),
        "".join(
            "<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (e(metric), e(p), e(str(n)))
            for metric, table in (
                ("requests", summary.request_counts), ("pages", summary.page_counts),
                ("cache_hits", summary.cache_hits))
            for p, n in table
        ) or "<tr><td colspan=\"3\" class=\"muted\">(none)</td></tr>",
        summary.estimated_billable_google_calls,
        rows(summary.provider_errors),
    )
