# PetTripFinder discovery — Overpass resilience

**Authority:** PTF-DISCOVERY-OVERPASS-RESILIENCE-001 (2026-08-25).
**Modules:** `scripts/pettripfinder/discovery/{overpass_endpoints,pacing,discovery_state,paid_discovery_fallback,osm_extract}.py`, `discovery/config/overpass_endpoints.json`, and the resilient path in `discovery/overpass.py`.

Pittsburgh's discovery had 30 Overpass queries (15 cells × hotel/motel), 8 safely
cached, 22 remaining, and one public endpoint timing out at the TCP layer. Nothing
else was wrong and nothing was lost — and the market waited for hours, because the
only endpoint the client knew was the dead one and it was asked again for every
remaining cell. This document records what the discovery factory now does instead.

## Approved endpoints

`discovery/config/overpass_endpoints.json` (`ptf-overpass-endpoints/1.0`) lists the
public Overpass instances discovery may query, in preference order, each with
`endpoint_id`, `base_url`, `enabled`, health-check path, timeouts, minimum request
spacing, cooldown, failure threshold and notes/provenance. Defaults are deliberately
gentle: 2 s spacing, 15 min cooldown, 3 failures to trip, concurrency 1 (a registry
declaring more than 1 is refused). Rotation survives an outage; it is not a way
around a rate limit — a 429 opens the circuit immediately for the full cooldown.

## Endpoint selection

`EndpointSelector.select()`:

1. Walk enabled endpoints in registry order, current endpoint first (selection is
   sticky, not round-robin).
2. Skip any whose circuit is OPEN and still cooling down — without a probe.
3. Probe the rest (`GET <base>/api/status`) and classify: `HEALTHY`, `TIMEOUT`,
   `CONNECTION_REFUSED`, `HTTP_RATE_LIMITED`, `HTTP_SERVER_ERROR`, `OTHER_FAILURE`.
4. Return the first `HEALTHY`. Each failed probe counts toward that endpoint's
   circuit; the threshold opens it and records `cooldown_until`.
5. No healthy endpoint → `NoHealthyEndpoint` carrying every endpoint's state and
   the earliest cooldown expiry. The client re-sweeps with backoff, bounded by the
   failure threshold, so a real outage opens every circuit and leaves the cooldown
   on disk (`<output_root>/overpass_endpoint_health.json`) for the next run.

Live query failures count toward the same circuit; when it opens mid-run the
client selects again and the remaining cells go straight to the next endpoint.

## The cache key names the question, not the server

The old fingerprint was `{endpoint, ql}`; the new one is `{ql, query_version}`.
Market, category and cell geometry are in the QL and the query id; the endpoint
that answered lives in the entry's `status_metadata` (`endpoint_id`, `endpoint_url`,
`requested_at`, `http_status`, `query_id`, `cell_id`, `query_hash`, `query_version`).
Entries written under the legacy key are still found by a fallback lookup over every
approved endpoint URL, so Pittsburgh's 8 cached cells are hits, not re-fetches, and
`ptf-discovery-state` reports which endpoint produced which cell.

## Pacing defaults

concurrency 1 · spacing 2.0 s + up to 0.5 s jitter · backoff 2 s × 2^(n−1) + jitter,
capped 60 s · at most 2 attempts per endpoint per query · every wait recorded.
`overpass_run_stats.json` records requests, successes, timeouts, rate limits, server
errors, endpoint switches, cache hits, waited and elapsed seconds, per-endpoint counts.

## Free-discovery exhaustion

`discovery_cli.py state --market <id> --output-root <root>` (and
`discovery_state.build`) derives, offline: `OVERPASS_ENDPOINTS_AVAILABLE`,
`OVERPASS_CELLS_TOTAL / CACHED / REMAINING`, `OVERPASS_FREE_DISCOVERY_EXHAUSTED`, and
one state — `OVERPASS_FREE_DISCOVERY_EXHAUSTED`, `FREE_DISCOVERY_RUNNABLE`, or
`WAITING_FOR_FREE_DISCOVERY` (with cached/remaining cells, endpoint health states and
the earliest cooldown expiry). The market factory's `census` phase refuses to build a
census unless the state is EXHAUSTED; the coverage-completion artifact carries the
same fields under `boolean_basis.free_discovery`.

## Paid fallback

The state reports `PAID_DISCOVERY_FALLBACK_AVAILABLE` when a Google key is present
and cells remain. Using it needs a `ptf-paid-discovery-authorization/1.0` document
naming the market, an author, a reason, a Google request cap and a cost plan. No code
path runs Google because Overpass is unavailable.

## Local OSM extract

`osm_extract.py` implements `ptf-osm-extract-index/1.0` — a reduced, queryable index
of a regional `.osm.pbf` — and `LocalOsmExtractSource`, which answers the same cell
queries locally in Overpass's own response shape, under the same cache key, with
`endpoint_id = local_extract:<extract_id>`. `discovery_cli.py run --osm-extract-index
<path>` uses it in place of any public server. `build_index_from_pbf` reduces a PBF
with `pyosmium` when installed and refuses with instructions when not. Extract
download/refresh is designed as a data registry and not yet built.
