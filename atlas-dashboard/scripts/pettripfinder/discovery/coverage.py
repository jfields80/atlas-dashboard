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
from scripts.pettripfinder.discovery.deduplicate import deduplicate
from scripts.pettripfinder.discovery.market_config import MarketConfig
from scripts.pettripfinder.discovery.models import (
    CoverageSummary,
    DiscoveryCandidate,
    DiscoverySourceQuery,
    QueryYieldRow,
)
from scripts.pettripfinder.discovery.normalize import normalize_records
from scripts.pettripfinder.discovery.provider_result import ProviderQueryResult


def _tally(items) -> Tuple[Tuple[str, int], ...]:
    counts: Dict[str, int] = {}
    for k in items:
        counts[k] = counts.get(k, 0) + 1
    return tuple(sorted(counts.items()))


# --------------------------------------------------------------------------- #
# Query-yield/saturation table (AES-DATA-004B Phase 3). Reuses the real
# normalize/deduplicate pipeline for cumulative-candidate growth -- not a
# separate approximate reporting-only merge heuristic.
# --------------------------------------------------------------------------- #

def compute_query_yield_table(
    planned_queries: Sequence[DiscoverySourceQuery],
    query_results: Sequence[ProviderQueryResult],
    *,
    market_id: str = "",
) -> Tuple[QueryYieldRow, ...]:
    query_by_id = {q.query_id: q for q in planned_queries}
    seen_provider_ids = set()
    cumulative_records = []
    cumulative_count = 0
    rows = []

    for result in query_results:
        q = query_by_id.get(result.query_id)
        category = q.canonical_category if q else ""
        cell_id = q.cell_id if q else ""
        raw = len(result.records)

        new_records = []
        already_found = 0
        for rec in result.records:
            key = (rec.provider, rec.provider_record_id)
            if key in seen_provider_ids:
                already_found += 1
            else:
                seen_provider_ids.add(key)
                new_records.append(rec)
        new_unique = len(new_records)

        candidates_added = 0
        candidates_merged = 0
        if new_records:
            cumulative_records.extend(result.records)
            candidates_now = deduplicate(
                normalize_records(tuple(cumulative_records)), market_id=market_id)
            candidates_added = len(candidates_now) - cumulative_count
            candidates_merged = max(0, new_unique - candidates_added)
            cumulative_count = len(candidates_now)

        if result.provider == C.PROVIDER_GOOGLE_PLACES and raw >= C.GOOGLE_PAGE_SIZE:
            saturation = C.YIELD_SATURATION_POTENTIAL
        elif "overpass_element_cap_truncated" in result.warnings:
            saturation = C.YIELD_SATURATION_TRUNCATED
        else:
            saturation = C.YIELD_SATURATION_NOT_SATURATED

        if result.cache_hits > 0:
            cache_or_live = C.YIELD_CACHE_HIT
        elif result.requests_made > 0:
            cache_or_live = C.YIELD_LIVE_CALL
        elif result.state == C.QUERY_STATE_DISABLED:
            cache_or_live = C.YIELD_DISABLED
        else:
            cache_or_live = C.YIELD_SKIPPED

        rows.append(QueryYieldRow(
            query_id=result.query_id, provider=result.provider, category=category,
            cell_id=cell_id, state=result.state, raw_records_returned=raw,
            new_unique_provider_records=new_unique,
            already_found_by_earlier_query=already_found,
            candidates_added=candidates_added,
            candidates_merged_into_existing=candidates_merged,
            cumulative_unique_candidates=cumulative_count,
            zero_result=(raw == 0), saturation_status=saturation,
            cache_or_live=cache_or_live,
        ))
    return tuple(rows)


def saturated_query_ids(yield_table: Sequence[QueryYieldRow]) -> Tuple[str, ...]:
    """Queries that returned the provider's per-page maximum, or were
    truncated by the element cap -- candidates for a follow-up second-page
    pass in a LATER phase. Never proof the query exhausted the real market
    (mission Phase 3: potentially saturated, not proven complete)."""
    return tuple(r.query_id for r in yield_table
                if r.saturation_status != C.YIELD_SATURATION_NOT_SATURATED)


def zero_result_query_ids(yield_table: Sequence[QueryYieldRow]) -> Tuple[str, ...]:
    """Queries that were actually attempted (served from cache or fetched
    live -- state COMPLETED) and genuinely returned nothing. Excludes
    SKIPPED_CAP_REACHED/DISABLED/FAILED/etc, which also have raw=0 but were
    never really queried -- conflating "we tried and found nothing" with
    "we never got to try" would make this report noisy and misleading
    (bug found and fixed live during AES-DATA-004B Wave 1: the unfiltered
    version buried the few genuinely-empty queries under dozens of
    budget-skipped ones)."""
    return tuple(r.query_id for r in yield_table
                if r.zero_result and r.state == C.QUERY_STATE_COMPLETED)


def low_yield_query_ids(yield_table: Sequence[QueryYieldRow], threshold: int = 1) -> Tuple[str, ...]:
    """Queries that returned records but contributed at most ``threshold``
    NEW unique provider records (mostly re-finding what an earlier query
    in this run already found)."""
    return tuple(r.query_id for r in yield_table
                if not r.zero_result and r.new_unique_provider_records <= threshold)


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
    known_inventory_recall: Tuple[Tuple[str, int], ...] = (),
    import_plan_next_action_counts: Tuple[Tuple[str, int], ...] = (),
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

    yield_table = compute_query_yield_table(planned_queries, query_results, market_id=market.market_id)

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
        query_yield_table=yield_table,
        saturated_query_ids=saturated_query_ids(yield_table),
        low_yield_query_ids=low_yield_query_ids(yield_table),
        zero_result_query_ids=zero_result_query_ids(yield_table),
        known_inventory_recall=known_inventory_recall,
        import_plan_next_action_counts=import_plan_next_action_counts,
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
        "query_yield_table": [
            {
                "query_id": r.query_id, "provider": r.provider, "category": r.category,
                "cell_id": r.cell_id, "state": r.state,
                "raw_records_returned": r.raw_records_returned,
                "new_unique_provider_records": r.new_unique_provider_records,
                "already_found_by_earlier_query": r.already_found_by_earlier_query,
                "candidates_added": r.candidates_added,
                "candidates_merged_into_existing": r.candidates_merged_into_existing,
                "cumulative_unique_candidates": r.cumulative_unique_candidates,
                "zero_result": r.zero_result, "saturation_status": r.saturation_status,
                "cache_or_live": r.cache_or_live,
            }
            for r in summary.query_yield_table
        ],
        "saturated_query_ids": list(summary.saturated_query_ids),
        "low_yield_query_ids": list(summary.low_yield_query_ids),
        "zero_result_query_ids": list(summary.zero_result_query_ids),
        "known_inventory_recall": dict(summary.known_inventory_recall),
        "import_plan_next_action_counts": dict(summary.import_plan_next_action_counts),
        "disclosure": (
            "Counts describe the query plan actually executed and the "
            "candidates it produced -- not the true size of the real-world "
            "market. No completeness percentage is claimed."
        ),
        "pet_friendliness_warning": (
            "Discovery records are candidates only. Google/OSM identifying a "
            "hotel or motel never proves pets are accepted, pet fees, pet "
            "deposits, weight limits, species restrictions, room "
            "restrictions, pet amenities, or current booking availability. "
            "Official hotel/brand location pages remain the sole authority "
            "for pet policy -- nothing here is a verified listing."
        ),
        "market_completeness_warning": (
            "No completeness percentage is established or implied. Query "
            "saturation and cross-provider overlap describe the executed "
            "plan, not the true size of the real-world lodging market."
        ),
    }
    return json.dumps(data, sort_keys=True, indent=2)


def render_coverage_html(summary: CoverageSummary) -> str:
    e = html.escape
    total_planned = len(summary.query_completion)
    completed = sum(1 for _qid, state in summary.query_completion
                    if state == C.QUERY_STATE_COMPLETED)
    saturation = "%d/%d" % (completed, total_planned) if total_planned else "0/0"

    def rows(pairs):
        if not pairs:
            return "<tr><td colspan=\"2\" class=\"muted\">(none)</td></tr>"
        return "".join(
            "<tr><td>%s</td><td>%s</td></tr>" % (e(str(k)), e(str(v)))
            for k, v in pairs
        )

    def id_list(ids):
        if not ids:
            return "<span class=\"muted\">(none)</span>"
        return ", ".join(e(str(i)) for i in ids)

    request_accounting_rows = "".join(
        "<tr><td>%s</td><td>%s</td><td>%s</td></tr>" % (e(metric), e(p), e(str(n)))
        for metric, table in (
            ("requests", summary.request_counts), ("pages", summary.page_counts),
            ("cache_hits", summary.cache_hits))
        for p, n in table
    ) or "<tr><td colspan=\"3\" class=\"muted\">(none)</td></tr>"

    yield_rows = "".join(
        "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%d</td>"
        "<td>%d</td><td>%d</td><td>%d</td><td>%d</td><td>%d</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
            e(r.query_id), e(r.provider), e(r.category), e(r.cell_id), e(r.state),
            r.raw_records_returned, r.new_unique_provider_records,
            r.already_found_by_earlier_query, r.candidates_added,
            r.candidates_merged_into_existing, r.cumulative_unique_candidates,
            e(str(r.zero_result)), e(r.saturation_status), e(r.cache_or_live),
        )
        for r in summary.query_yield_table
    ) or "<tr><td colspan=\"14\" class=\"muted\">(none)</td></tr>"

    sections = []
    sections.append("""<!doctype html><html><head><meta charset="utf-8">
<title>Discovery coverage -- %s</title>
<style>body{font-family:sans-serif;margin:2em;}table{border-collapse:collapse;margin-bottom:1.5em;}
td,th{border:1px solid #ccc;padding:4px 10px;text-align:left;font-size:0.9em;}.muted{color:#888;}
.warning{background:#fff3cd;border:1px solid #ffe69c;padding:0.75em 1em;border-radius:4px;margin-bottom:1em;}</style>
</head><body>
<h1>Discovery coverage report</h1>
<p>market: <b>%s</b> &nbsp; observed_at: <b>%s</b></p>
<div class="warning"><b>Pet-friendliness is not established here.</b> %s</div>
<div class="warning"><b>Market completeness is not established here.</b> %s</div>""" % (
        e(summary.market_id), e(summary.market_id), e(summary.observed_at),
        e("Discovery records are candidates only. A provider identifying a hotel or motel "
          "never proves pets are accepted, pet fees, pet deposits, weight limits, species "
          "restrictions, room restrictions, pet amenities, or current booking availability. "
          "Official hotel/brand location pages remain the sole authority for pet policy."),
        e("Query saturation and cross-provider overlap describe the executed plan, not the "
          "true size of the real-world lodging market. No completeness percentage is claimed."),
    ))

    sections.append("""
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
<table>%s</table>""" % (
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
        request_accounting_rows,
        summary.estimated_billable_google_calls,
        rows(summary.provider_errors),
    ))

    sections.append("""
<h2>Query yield / saturation table</h2>
<table><tr><th>query_id</th><th>provider</th><th>category</th><th>cell_id</th><th>state</th>
<th>raw</th><th>new_unique</th><th>already_found</th><th>cand_added</th><th>cand_merged</th>
<th>cumulative</th><th>zero_result</th><th>saturation</th><th>cache_or_live</th></tr>%s</table>

<h2>Saturated queries (candidates for a possible second page later)</h2>
<p>%s</p>

<h2>Low-yield queries</h2>
<p>%s</p>

<h2>Zero-result queries</h2>
<p>%s</p>

<h2>Known-inventory recall spot-check</h2>
<table>%s</table>

<h2>Import-plan next-action counts</h2>
<table>%s</table>
</body></html>""" % (
        yield_rows,
        id_list(summary.saturated_query_ids),
        id_list(summary.low_yield_query_ids),
        id_list(summary.zero_result_query_ids),
        rows(summary.known_inventory_recall),
        rows(summary.import_plan_next_action_counts),
    ))

    return "".join(sections)
