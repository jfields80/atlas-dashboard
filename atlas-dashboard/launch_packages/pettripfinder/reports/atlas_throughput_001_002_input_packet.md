# ATLAS-THROUGHPUT-001 → 002 input packet

Status: PROPOSED. Nothing here is implemented. Every recommendation names the
measurement that justifies it; a recommendation with no measurement is marked
as such and is not a 002 deliverable.

Evidence files (all under `launch_packages/pettripfinder/reports/`):
`atlas_throughput_001_broad_run_profiles.json` (11 broad runs profiled from
their junit files), `atlas_throughput_001_instrumented_baseline.json` (the one
instrumented run), `atlas_throughput_001_sampler_cha_full.json` and
`atlas_throughput_001_sampler_baseline.json` (process-tree memory),
`atlas_throughput_001_classifier_audit.json` (Regression V2 over five real
branches), `atlas_throughput_001_failure_baseline_audit.json`,
`atlas_throughput_001_assembly_duplication.md`,
`atlas_throughput_001_safety_invariants.md`,
`atlas_throughput_001_release_model.md`.

## What 002 should implement, in order

### 1. Stop paying for `tests/website_generation/integration/test_pettripfinder_demo_media.py` in the market release lane  (VERIFIED BY MEASUREMENT)

- Measured: 3,489–4,440 s per broad run in every one of the 10 lane-runner
  broad runs kept on disk (58–67 % of the run); 12 identical real-chain
  builds of the SAME committed launch package, one per test, ~300 s each; the
  process working set rises from ~470 MB to 6.4–7.6 GB for the last ~65
  minutes of every broad run and drove system free memory to 46 MB during the
  Chattanooga run.
- It is not a PetTripFinder market test. The committed baselines (c854469,
  f75aa95) DESELECT it; the lane runner's `full_regression` lane does not, so
  every market order has been paying ~65 minutes the baseline never measured.
- 002 deliverable: give the website-generation demo-media suite its own lane
  (or a module-scoped real-chain fixture, which is a website-generation
  change and needs that team's order), and make the `full_regression` lane
  the committed baseline's definition. This alone brings a broad run from
  ~100 min to ~40 min (canon002-full measured 47.5 min with it deselected).
- Risk of narrowing: none for market data. The suite reads
  `launch_packages/pettripfinder/seed_businesses.csv`, `categories.json` and
  `demo_media.json`, which a market order does change (seed CSV). Keep it in
  a lane that runs when those shared files change; the classifier already
  names `*seed_businesses*.csv` as AUTHORITY_CHANGE.

### 2. Build the whole-site bundle ONCE per broad run and reuse it  (VERIFIED BY MEASUREMENT)

- Measured: `test_global_deployment_architecture_045.py::production`,
  `045::test_production_is_indexable_and_preview_is_not` (a second, preview
  build whose ten fragments are byte-identical) and
  `test_launch_participation_046.py::production` each assemble all ten
  participating markets from identical inputs: 3 × ~300–430 s = 900–1,360 s
  per broad run. Both `production` fixtures assert the same pin
  (`SOURCE_PINS.bundle_sha256`).
- The per-market `market_bundles` fixture assembles all 11 contract markets
  (330–436 s), and Columbus alone is generated 15 times per run across
  prod004/prod005/two_market/homepage/generate_columbus/release_contracts.
- 002 deliverable: a session-scoped, input-hashed bundle cache keyed on the
  plugin's `dependency_input_hash` (whole-site) / `market_input_hash`
  (one market) + the generator source hash, materialised under `data/` and
  reused by every fixture that asks for the same key. The plugin's
  `assembly` rows give the cache-hit accounting for free.
- Risk of narrowing: a cache must be keyed on content, never on a commit, and
  the two determinism tests (prod004 `test_build_is_deterministic`, prod005
  `test_deterministic_and_atomic_replace`) must keep building twice.

### 3. Ownership manifest and market-local execution zone  (VERIFIED BY MEASUREMENT of the classifier; the saving is the broad runs it would not demand)

- Measured: Regression V2 classified all five real market branches
  FULL_REGRESSION_REQUIRED = YES. Nashville 001: 45 changed paths, 21 driver
  paths, 18 of them `scripts/pettripfinder/nashville_tn_*.py` helpers; Toledo
  001: 37 / 18 / 15; Lexington: 36 / 17 / 15; Chattanooga: 28 / 12 / 8. The
  rule that fires is `prefix:scripts/pettripfinder/` → GENERIC_RUNTIME_CHANGE,
  plus `glob:scripts/pettripfinder/*routing*.py` / `*corridor*.py` /
  `*polic*.py` / `*identity*.py` on market-named helpers, and
  `prefix:scripts/pettripfinder/discovery/` on `discovery/config/<market>.json`.
- The helpers import only `scripts.pettripfinder.markets.contract`,
  `site_data.normalize_name`, `hotel_exclusions.address_key`; they write only
  `launch_packages/pettripfinder/markets/proposed/<market>.json`,
  `identity_census_proposed/<market>.json` and `markets/reports/<market>_*.json`.
  No production module imports them; the assembler reads none of their outputs.
- 002 deliverable: an ownership manifest that declares, per market namespace,
  the allowed import set, allowed read roots, allowed write roots, and the
  production-package exclusion list; a classifier rule that admits a path to
  the MARKET_LOCAL class only when the manifest proves (by import scan and
  write-root scan of the actual file) that it is isolated. Unproven → today's
  GENERIC_RUNTIME_CHANGE. Rename/deletion of a market-local file stays
  market-local when both sides are in the namespace; a market-local file that
  gains a shared import loses the class at that commit.
- Risk of narrowing: `assemble_production_site._partition_path` and
  `regression_lanes.MARKET_PREFIXES` are shared tables a promotion edits; they
  stay GENERIC_RUNTIME_CHANGE. `discovery/config/osm_extracts.json` is shared
  (Lexington and Chattanooga both added rows) and stays shared.

### 4. Dynamic-dependency escape, test-infrastructure and classifier self-change  (STRONGLY INDICATED)

- The reverse-dependent scan in `regression_delta.reverse_dependents` is a
  stem-mention scan (over-inclusive, safe). A market-local zone must keep it,
  and add: any `importlib` / `__import__` / `subprocess` use in a market-local
  file voids the class; `conftest.py`, `pytest.ini`, `epochs.py`,
  `market_state.py`, `pins/`, `regression_delta.py`, `regression_lanes.py`,
  `throughput_profile.py` remain mandatory-full (this order's own change was
  classified full for exactly that reason, and the one instrumented baseline
  is its broad validation).

### 5. A critical lane that proves the 13 launch-safety hazards without all-market rendering  (VERIFIED BY CODE READING, cost measured)

- `atlas_throughput_001_safety_invariants.md` §D: only five facts need the
  composed site (byte-level route collision, rendered-surface content gates,
  `global.live_routes_preserved` as written, bundle determinism / pinned sha
  reproduction, and a render of every record). Everything else is JSON-only
  and runs in seconds (the contracts chunk: 716 tests in 34 s).
- 002 deliverable: name the lane (node ids in §C) and measure it with the
  plugin; it becomes the gate a data-only change owes instead of the broad
  suite. Gaps to close before it can carry the launch: H2 has no gate at all,
  H9 determinism is skipped by default, H7 route inventory covers Columbus
  only, H12 has no rollback-target market-set check.

### 6. Release-coordinator inputs from the release-model audit  (VERIFIED BY CODE READING)

- The same published count is stored in ≥12 places; `bundle_sha256` in 8;
  three divergent partition-filename tables; two definitions of `resolved`;
  no repo script writes the global manifest, an authorization or a record
  (all in-session per runbook §12). A coordinator that reuses unchanged
  validated market bundles needs ONE per-market input manifest (the plugin's
  fingerprint is a start) and ONE writer for the release records.

## What 002 should NOT do

- Do not weaken any row of `VALIDATION_MATRIX`; add a class, do not relax one.
- Do not skip `TestEveryMarketAssembles` — it is the only per-record render
  proof for 8 of 11 markets (H3). Cache its inputs instead.
- Do not run xdist: no session fixtures, fixed absolute output paths in
  045/046/global_assembler, and process-global generator state
  (`atlas_throughput_001_assembly_duplication.md` §D).
- Do not touch the 160-node baseline: it is 150 ENVIRONMENT + 10
  HISTORICAL_COUNT/PIN failures over gitignored corpora, 0 critical.

## Open measurements 002 should take first

- Cold vs warm assembly with the cache in place (the plugin's `cold_vs_repeat`).
- Founder active time (no instrument exists today).
- Concurrency: two workers plus one release lane with the sampler running.
