# ATLAS-THROUGHPUT-002 → 003 input packet

Status: PROPOSED. 003 builds the cheap CRITICAL FAST launch lane around the
actual hazards. Nothing here is implemented in 002.

## What 002 delivered that 003 builds on

- A market-local zone model (`launch_packages/pettripfinder/market_local_ownership.json`)
  and a five-condition isolation proof (`scripts/pettripfinder/market_local_isolation.py`)
  that Regression V2 consults for every refinable path; MARKET_LOCAL_TOOLING
  owes the zone's tests + the per-market contract rows, never assembly, never
  the broad suite. Measured: every Python helper of Nashville (20), Chattanooga
  (11), Lexington (16) and Toledo 001 (16) proves isolated; the 001 finding
  was reproduced by evidence, not by name.
- The `website_generation_integration` broad-audit lane and its documented
  role (`atlas_throughput_002_demo_media_lane_role.md`).
- Session-local, input-keyed reuse for the generator, the per-market bundle
  and the whole-site compose (`scripts/pettripfinder/assembly_session_cache.py`),
  with BUILD_EXECUTED / REUSE_HIT accounting in the profiler.

## REQUIRED INPUTS FOR 003 — the 001 safety gaps, recorded unchanged

`atlas_throughput_001_safety_invariants.md` §E. None was solved in 002; the
old broad suite's existence is NOT evidence that any of them is covered.

| # | gap (001) | where it stands after 002 | what 003 must build |
|---|---|---|---|
| H2 | no build- or deploy-time gate for FIRST-PARTY POLICY BINDING; `policy_schema` has no `source_url` rule; `source_grade` is self-declared | unchanged | a fail-closed record gate: every publication-grade evidence entry's `source_url` domain is the property's official domain (from the routing shard / seed row), run inside the applier and in the fast lane |
| H9 | bundle DETERMINISM proof is skipped by default (`PTF_ASSEMBLER_FULL_BUILD`) | unchanged; 002 added an explicit `cold()` around the existing cold-claim tests and proved cold-vs-reuse byte parity for the three reuse paths (`atlas_throughput_002_cold_reuse_parity.json`) | a determinism proof the fast lane can afford: two cold generator runs of ONE market (~30 s) per changed market, plus the compose digest re-derived by `verify_bundle_directory` |
| H7 | ROUTE PRESERVATION is gated for the 132 Columbus routes of 2026-08-09 only; the nine other live markets rely on count gates and hand-recorded `live_verification_results` | unchanged | a committed all-market live route inventory regenerated from the previous deploy's sitemap at every deploy, and a `routes_removed == 0` gate against it in the assembler |
| H12 | the ROLLBACK TARGET's market set is not checked; `verify_target` is manual and network-only | unchanged | a JSON-only check that the rollback target's own deployment record carries every currently live market minus the launching one; a CLI wrapper for `verify_target` / `verify_bundle_directory` |
| H13 | every PAID CALL SITE bypasses the paid-attempt and discovery ledgers; URL-level double-buy is an open `xfail(strict=True)` defect (PTF-DEFECT-URL-LEVEL-DOUBLE-BUY-001) | unchanged | consult the ledgers inside `firecrawl_capture.fetch`, the Bright Data capture modules and `google_places` before spending; key the cost plan on the page, not the identity |
| H3 | `policy_schema.validate_record` is write-time + TEST only; a bare-string `service_animal_statement` would not fail the build | unchanged (Toledo 002 already validates inside its applier; not generic) | make `validate_record` a gate in `assemble_netlify_bundle` Phase 1 |
| H1 | build-time identity check is a `normalize_name` join; `identity_key` canonicality tested for 3–8 markets, not 11 | unchanged | the H1 minimum node set over all 11 packages in the fast lane |

## What 003 should decide about registered markets

002 narrows SHADOW zones only (condition 5 fails the moment a market is
registered, and `production_runtime_included` must be NO). A registered
market's revalidation helpers (Cincinnati 002, Pittsburgh 001 style) still
classify GENERIC_RUNTIME_CHANGE by prefix. 003 can extend the zone model to a
REGISTERED execution zone only once the critical fast lane proves the
production facts a promotion changes.

## Two findings 003 should take as inputs, not solve blindly

1. Root-level artifacts (`launch_packages/pettripfinder/<market>_osm_extracts_*.json`,
   `<market>_founder_rulings_*.json`) fail condition 4 because
   `tests/pettripfinder/test_build_capture_queue.py` enumerates the package
   root. Market orders should write such artifacts under
   `markets/reports/<market>_…` (owned, not enumerated by shared code), or 003
   should give the package root a declared layout.
2. `scripts/pettripfinder/discovery/config/osm_extracts.json` is a SHARED
   registry every new region appends a row to (Lexington, Chattanooga). It
   stays ROUTING_SEMANTIC_CHANGE; a structured registration narrowing (added
   rows only, each naming the market, like REGISTRATION_CONTAINERS for tests)
   would need its own proof and belongs to 003, not to a prefix rule.

## Measurements 003 should take first

- The migration audit's cache accounting (`atlas_throughput_002_migration_audit.json`):
  which repeats remain (the three composes should be 1 build + 2 reuses).
- Founder active time — still no instrument.
- Two concurrent market workers beside one release lane, with the sampler.
