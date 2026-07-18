"""AES-DATA-004C Task 12 -- deterministic lodging-resolution reports (JSON +
HTML). Never claims market completeness, never extracts or reports pet
policy, never claims production population.
"""

from __future__ import annotations

import html
import json
from typing import Dict, Sequence, Tuple

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery.resolution_runner import ResolvedCandidate


def _tally(items) -> Tuple[Tuple[str, int], ...]:
    counts: Dict[str, int] = {}
    for k in items:
        counts[k] = counts.get(k, 0) + 1
    return tuple(sorted(counts.items()))


def build_report_data(resolved: Sequence[ResolvedCandidate], *, market_id: str, observed_at: str,
                      batch_counts: Tuple[Tuple[str, int], ...] = ()) -> dict:
    total = len(resolved)
    scope_counts = _tally(r.scope for r in resolved)
    category_counts = _tally(r.category for r in resolved)
    outcome_counts = _tally(r.resolution_outcome for r in resolved)
    identity_outcome_counts = _tally(r.identity_outcome for r in resolved if r.identity_outcome)

    all_states = [ws.resolution_state for r in resolved for ws in r.website_resolutions]
    website_state_counts = _tally(all_states)

    confirmed = sum(1 for r in resolved
                    for ws in r.website_resolutions
                    if ws.resolution_state == C.WEBSITE_RES_PROPERTY_URL_CONFIRMED)
    probable = sum(1 for r in resolved
                   for ws in r.website_resolutions
                   if ws.resolution_state == C.WEBSITE_RES_PROPERTY_URL_PROBABLE)
    chain_homepage_only = sum(1 for r in resolved
                              for ws in r.website_resolutions
                              if ws.resolution_state == C.WEBSITE_RES_CHAIN_HOMEPAGE_ONLY)
    third_party_only = sum(1 for r in resolved
                           for ws in r.website_resolutions
                           if ws.resolution_state == C.WEBSITE_RES_THIRD_PARTY_BOOKING_URL)
    missing = sum(1 for r in resolved
                  for ws in r.website_resolutions
                  if ws.resolution_state == C.WEBSITE_RES_MISSING)
    blocked = sum(1 for r in resolved
                  for ws in r.website_resolutions
                  if ws.resolution_state == C.WEBSITE_RES_FETCH_BLOCKED)
    conflicting = outcome_counts_dict = dict(outcome_counts)
    conflicting_count = conflicting.get(C.RESOLUTION_REVIEW_WEBSITE, 0)

    import_eligible = sum(1 for r in resolved if r.resolution_outcome in C.RESOLUTION_ELIGIBLE_FOR_BATCH)
    unresolved = sum(1 for r in resolved if r.resolution_outcome in
                     (C.RESOLUTION_REVIEW_IDENTITY, C.RESOLUTION_REVIEW_WEBSITE,
                      C.RESOLUTION_MISSING_OFFICIAL_WEBSITE, C.RESOLUTION_DEFER))
    excluded = sum(1 for r in resolved if r.resolution_outcome in
                   (C.RESOLUTION_EXCLUDE_OUT_OF_SCOPE, C.RESOLUTION_EXCLUDE_CLOSED))

    review_table = [
        {
            "candidate_id": r.candidate_id, "name": r.name, "category": r.category,
            "scope": r.scope, "identity_outcome": r.identity_outcome,
            "resolution_outcome": r.resolution_outcome,
            "missing_website_action": r.missing_website_action,
        }
        for r in resolved
        if r.resolution_outcome not in C.RESOLUTION_ELIGIBLE_FOR_BATCH
    ]

    return {
        "market_id": market_id, "observed_at": observed_at,
        "total_lodging_candidates": total,
        "scope_counts": dict(scope_counts),
        "category_counts": dict(category_counts),
        "resolution_outcome_counts": dict(outcome_counts),
        "identity_outcome_counts": dict(identity_outcome_counts),
        "website_state_counts": dict(website_state_counts),
        "property_urls_confirmed": confirmed,
        "property_urls_probable": probable,
        "chain_homepage_only_count": chain_homepage_only,
        "third_party_only_count": third_party_only,
        "missing_website_count": missing,
        "conflicting_website_count": conflicting_count,
        "blocked_fetch_count": blocked,
        "import_eligible_count": import_eligible,
        "unresolved_count": unresolved,
        "excluded_count": excluded,
        "batch_counts": dict(batch_counts),
        "review_table": review_table,
        "no_pet_policy_extraction_warning": (
            "This report never extracts or evaluates pet-policy claims. "
            "Website resolution establishes identity only."
        ),
        "no_market_completeness_warning": (
            "No completeness percentage is established or implied for the "
            "real-world Columbus lodging market."
        ),
        "no_production_population_warning": (
            "No production inventory was populated or modified by this phase."
        ),
    }


def render_report_json(data: dict) -> str:
    return json.dumps(data, sort_keys=True, indent=2)


def render_report_html(data: dict) -> str:
    e = html.escape

    def rows(d):
        if not d:
            return "<tr><td colspan=\"2\" class=\"muted\">(none)</td></tr>"
        return "".join("<tr><td>%s</td><td>%s</td></tr>" % (e(str(k)), e(str(v)))
                       for k, v in sorted(d.items()))

    review_rows = "".join(
        "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % (
            e(row["candidate_id"]), e(row["name"]), e(row["category"]), e(row["scope"]),
            e(row["identity_outcome"]), e(row["resolution_outcome"]),
        )
        for row in data["review_table"]
    ) or "<tr><td colspan=\"6\" class=\"muted\">(none)</td></tr>"

    return """<!doctype html><html><head><meta charset="utf-8">
<title>Lodging resolution report -- %s</title>
<style>body{font-family:sans-serif;margin:2em;}table{border-collapse:collapse;margin-bottom:1.5em;}
td,th{border:1px solid #ccc;padding:4px 10px;text-align:left;font-size:0.9em;}.muted{color:#888;}
.warning{background:#fff3cd;border:1px solid #ffe69c;padding:0.75em 1em;border-radius:4px;margin-bottom:1em;}</style>
</head><body>
<h1>Lodging resolution report</h1>
<p>market: <b>%s</b> &nbsp; observed_at: <b>%s</b> &nbsp; total candidates: <b>%d</b></p>
<div class="warning">%s</div>
<div class="warning">%s</div>
<div class="warning">%s</div>

<h2>Scope counts</h2><table>%s</table>
<h2>Category counts</h2><table>%s</table>
<h2>Resolution outcomes</h2><table>%s</table>
<h2>Identity-conflict outcomes</h2><table>%s</table>
<h2>Website-state counts</h2><table>%s</table>

<h2>Summary</h2>
<table>
<tr><td>Confirmed property URLs</td><td>%d</td></tr>
<tr><td>Probable property URLs</td><td>%d</td></tr>
<tr><td>Chain-homepage-only</td><td>%d</td></tr>
<tr><td>Third-party-only</td><td>%d</td></tr>
<tr><td>Missing websites</td><td>%d</td></tr>
<tr><td>Conflicting websites</td><td>%d</td></tr>
<tr><td>Blocked fetches</td><td>%d</td></tr>
<tr><td>Import-eligible</td><td>%d</td></tr>
<tr><td>Unresolved</td><td>%d</td></tr>
<tr><td>Excluded</td><td>%d</td></tr>
</table>

<h2>Batch counts</h2><table>%s</table>

<h2>Review table (every unresolved/excluded candidate)</h2>
<table><tr><th>candidate_id</th><th>name</th><th>category</th><th>scope</th>
<th>identity_outcome</th><th>resolution_outcome</th></tr>%s</table>
</body></html>""" % (
        e(data["market_id"]), e(data["market_id"]), e(data["observed_at"]),
        data["total_lodging_candidates"],
        e(data["no_pet_policy_extraction_warning"]),
        e(data["no_market_completeness_warning"]),
        e(data["no_production_population_warning"]),
        rows(data["scope_counts"]), rows(data["category_counts"]),
        rows(data["resolution_outcome_counts"]), rows(data["identity_outcome_counts"]),
        rows(data["website_state_counts"]),
        data["property_urls_confirmed"], data["property_urls_probable"],
        data["chain_homepage_only_count"], data["third_party_only_count"],
        data["missing_website_count"], data["conflicting_website_count"],
        data["blocked_fetch_count"], data["import_eligible_count"],
        data["unresolved_count"], data["excluded_count"],
        rows(data["batch_counts"]), review_rows,
    )
