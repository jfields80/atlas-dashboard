# ATLAS-THROUGHPUT-002 — session-local assembly reuse report

Companion data: `atlas_throughput_002_cold_reuse_parity.json` (cold / reuse /
forced-cold for each supported path, quiet tree), `atlas_throughput_002_migration_audit.json`
(the broad audit with the cache on), `atlas_throughput_002_performance.json`
(the market-local run), and 001's `atlas_throughput_001_instrumented_baseline.json`.

## What was measured in 001

56 PetTripFinder assembly calls in one broad run, 19 unique input keys, 37
repeated builds: the 10-market production site composed three times from
identical inputs (2 × production, 1 × preview whose ten fragments were
identical), Columbus built 15 times (5 default-market bundles, 5 bare
generator runs, 3 fragments + the `market_bundles` bundle), ~710 s of
repeated PetTripFinder work; and inside the demo-media suite 12 real-chain
builds of one launch package (~3,800 s repeated). Repeats were not cheaper:
nothing was cached.

## The mechanism (`scripts/pettripfinder/assembly_session_cache.py`)

| element | decision |
|---|---|
| scope | one Python process; a per-process temp store removed at exit; the production CLI runs one assembly per process and never sees a hit |
| hooked builders | `generate_pettripfinder_columbus_site.run` (kind `generator_site`; the market scoping + module build state is applied on every call, the generation is cached), `assemble_netlify_bundle.assemble` (`market_bundle`), `assemble_production_site.assemble` (`production_site`) |
| key | sha256 over: kind; every build argument (context, base_url, market id AND `dataclasses.asdict(market)`, the contract document when passed in memory, keep_fragments, package-only flag); the content fingerprint of every file under `launch_packages/pettripfinder`, `deploy/netlify`, `scripts`, `engines`, `repositories`, `templates`, `static`, `models`, `core` (2,000+ files, sha256 memoised by path+size+mtime); the markets-registry directory and census directory the loaders are currently pointed at (with their content when patched); every `PTF_*` environment variable; interpreter and platform; and `module_state_signature` — every public immutable value and every callable's identity across the 26 builder/state modules, so a monkeypatched constant or function changes the key |
| what is NOT in the key | the output sha (never), mutable caches and the build-state globals the build itself sets (`site_pages.PUBLISHED_CATEGORIES` …), private module attributes |
| on a hit | the stored copy is re-hashed and refused if its digest moved; the consumer's output directory receives a fresh `copytree` (no shared bytes between consumers); the stored result document is returned as a deep copy |
| on failure | the exception propagates; nothing is stored |
| concurrency | one lock per key; a same-key request waits for the first build and reuses it (tested with four threads: one build, three hits) |
| explicit cold | `assembly_session_cache.cold()` around the three tests whose claim IS two cold executions (prod005 atomic replace, prod004 determinism, global_assembler run-twice); `PTF_ASSEMBLY_REUSE=0` disables reuse process-wide |
| instrumentation | every decision appended to `EVENTS` as BUILD_EXECUTED / REUSE_HIT with seconds and, for a hit, the seconds the original build cost; the profiler stamps each wrapped assembly row with `cache`, `input_key`, `reused_seconds_avoided`; `summary()` gives INPUT_KEY / BUILD_COUNT / REUSE_COUNT / BUILD_SECONDS / REUSED_SECONDS_AVOIDED per key and is written as an `assembly_session_cache` row at session end |

## Cold vs reuse parity (quiet tree, one process, `atlas_throughput_002_cold_reuse_parity.json`)

| path | cold s | reuse s | forced cold s | files | reused copy byte-identical | manifest identical | cold-vs-cold identical |
|---|---|---|---|---|---|---|---|
| generator_site (Columbus) | 25.7 | 7.2 (≈6 s is the market scoping + fingerprint; the copy is ~1 s) | 25.5 | 668 | yes | yes | yes |
| market_bundle (Columbus, production) | 26.4 | 2.2 | 39.2 | 670 | yes | yes | yes |
| production_site (10 markets, production) | 409.8 | 8.8 | — | 4,835 | yes | yes | — |
| production_site preview (fragments reused, composition rebuilt) | — | 340.9 (vs 302–329 s cold in 001) | — | | | | |

The preview compose gains little: its ten fragment generations hit (≈ 10 × 1 s
copies instead of 10 × 12–24 s builds), but the composition, gates, link
check and per-market `derive_authority` (each with a `git rev-parse`)
dominate that path. That is the remaining cost the whole-site key does not
cover between contexts.

Input mutation invalidates: appending a byte to `hotel_policy_facts.json`
between two identical bundle requests produced a miss (the build then refused
the changed package at its own gate). A parity benchmark run while another
process wrote a report under `launch_packages/pettripfinder/reports/` missed
on every key — which is the fingerprint doing its job, and the reason the
committed benchmark was taken in a quiet tree.

## Inside the migration audit (broad suite, cache on)

Run: `data/regression/atlas-throughput-002-audit` on commit 74152bd, clean tree, 22:41:38-23:45:15 (no other heavy Atlas lane was running; checked before launch). Every test under `tests/` -- demo-media included -- with the profiler and the session cache ON. Classified by NODE ID against `regression_baselines/f75aa95.json` (`atlas_throughput_002_migration_audit.json`).

| measure | 001 instrumented baseline | 002 migration audit |
|---|---|---|
| wall | 7,955 s (2 h 12 min) | **3,815 s (1 h 03 min)** |
| collected / passed / failed / skipped / xfail | 17,408 / 17,015 / 162 / 218 / 13 | 17,480 / 17,088 / 161 / 218 / 13 |
| against f75aa95 | PRE_EXISTING 160, TRUE_NEW 2 (closed) | PRE_EXISTING 160, EXPECTED_EPOCH 0, FLAKE 0, **TRUE_NEW 1 -> closed by node id (below)** |
| demo-media module | 5,630 s (12 chains) | 1,494 s (4 chains: 1 fixture + 2 cold determinism + 1 no-media) |
| assembly outer calls >= 1 s | 56 | 45 |
| unique assembly input keys | 19 | 18 |
| assembly seconds by kind | production_site 930, market_bundle 484, columbus_site 117, pilot load 148, wge engine 154 = 1,882 | production_site 855 (2 builds: production 361 s + preview 396 s; 1 reuse 7 s), market_bundle 467, columbus_site 110, pilot load 56, wge engine 40 = 1,529 |
| session cache | none | 27 keys, 33 builds, **27 REUSE_HITs**, 746 s avoided (cache accounting; 1,073 s attributed through wrapped calls incl. nested fragments) |
| whole-site production compose | built 2x (045 fixture + 046 fixture) | built 1x, reused 1x (046: 354 s avoided) |
| per-market fragments | 30 generator runs | 10 builds + 20 reuses (every non-Columbus market: 1 build, 2 hits) |
| Columbus generator | 15 | 6 builds (1 first + prod004 determinism 2 cold + prod005 atomic-replace 2 cold via the bundle + 1 under the patched two-market registry) + 6 hits |
| Columbus bundle | 7 | 3 builds (prod005 assembled + 2 cold) + 2 hits + 1 preview |
| peak working set | 7,538 MB | 8,486 MB in-process (8,220 MB tree; system free minimum 300 MB) -- the shared `with_media_chain` fixture keeps one chain alive across its nine consumers while a second chain (determinism) builds |

The one TRUE_NEW: `tests/pettripfinder/test_prod002_integration.py::test_non_hotel_path_unchanged` inspects the SOURCE of `generate_pettripfinder_columbus_site.run` for the two rendering calls; the split moved that body into `_generate`. The test now inspects `_generate` and additionally asserts that `run` still routes through it. Regression V2 classified the fix TEST_EXPECTATION_CHANGE confined to its module (FULL_REGRESSION_REQUIRED = NO), the delta run executed the node (13 collected, 0 failing, 25 s), verdict CLOSED, artifact `failure_closures/atlas-throughput-002-1.json`. No second audit was launched. **Migration audit TRUE_NEW_FAILURE after closure = 0.**

## Demo-media real-chain repeats

Not cached: the chain is not one builder and its tests' claims split cleanly.
Nine result-consumer tests now share one module fixture (`with_media_chain`);
`TestDeterminism` still builds twice cold; `TestZeroImageFallback` builds the
no-media variant. 12 builds → 4 per broad run.

## What remains, and why

- Columbus `market_bundles` bundle vs the five default-market bundles: same
  market, but `resolve_market(None)` and `resolve_market(market_id=…)` give
  the same MarketConfig → same key → the five default bundles reuse the
  first; `test_two_market_compat` runs under a patched registry → its own key
  (a legitimate cold build).
- Preview compose: fragments reuse, composition does not (different context).
- `derive_authority` / `build_package` and their `git rev-parse` spawn per
  call are not cached (JSON-only, seconds).
- Nothing survives the process; a persistent, content-addressed artifact
  cache is a later order's design.
