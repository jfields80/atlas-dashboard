# ATLAS-THROUGHPUT-001 — throughput baseline report

Worktree `C:\Atlas-Throughput-V1`, branch `worker/atlas-throughput-001`, base
commit `2163c4ed23b7315954f896c99729ca95c08eabfc` (Cincinnati launch 004 epoch
pins; production = 10 markets / 786 profiles / 945 routes in this tree). This
order measured. It changed no market authority, no pin, no participation, no
validation scope and no safety guard; it acquired nothing and deployed nothing.

Companion artifacts (same directory): `atlas_throughput_001_broad_run_profiles.json`,
`atlas_throughput_001_instrumented_baseline.json`, `atlas_throughput_001_inventory_summary.json`,
`atlas_throughput_001_sampler_cha_full.json`, `atlas_throughput_001_sampler_baseline.json`,
`atlas_throughput_001_classifier_audit.json`, `atlas_throughput_001_failure_baseline_audit.json`,
`atlas_throughput_001_release_model.md`, `atlas_throughput_001_assembly_duplication.md`,
`atlas_throughput_001_safety_invariants.md`, `atlas_throughput_001_success_criteria.json`,
`atlas_throughput_001_three_market_experiment.json`, `atlas_throughput_001_002_input_packet.md`.

---

## 1. Precheck (Phase 1)

| item | value |
|---|---|
| worktree | `C:\Atlas-Throughput-V1` (git root; package at `atlas-dashboard/`) |
| branch | `worker/atlas-throughput-001` |
| HEAD at start | `2163c4ed23b7315954f896c99729ca95c08eabfc` |
| upstream at start | `origin/worker/ptf-hardened-lineage-consolidation-008` (inherited; corrected at push) |
| tree at start | clean |

Owning modules, read rather than inferred:

| concern | file |
|---|---|
| Regression V2 classifier, matrix, delta validation, closure proof | `scripts/pettripfinder/regression_delta.py` (1,397 lines): `PATH_RULES`, `VALIDATION_MATRIX`, `SHARED_TEST_STATE`, `REGISTRATION_CONTAINERS`, `refine_test_change`, `classify_change`, `plan_for`, `run_plan`, `prove_closure`; matrix export `launch_packages/pettripfinder/regression_validation_matrix.json` |
| lanes, full-regression runner, baseline manifest, node-id classifier | `scripts/pettripfinder/regression_lanes.py` (638): `LANE_MEMBERSHIP`, `MARKET_PREFIXES`, `PER_MARKET_CONTRACT_MODULES`, `DEFERRED_TO_FULL_REGRESSION`, `run_lanes`, `build_baseline`, `classify` |
| lane markers at collection | `conftest.py` (root; `pytest_collection_modifyitems`), `pytest.ini` markers |
| pin inventory | `scripts/pettripfinder/regression_inventory.py` → `reports/factory_throughput_001_test_inventory.json` |
| failure baselines | `launch_packages/pettripfinder/regression_baselines/{c854469,f75aa95}.json`; closures `launch_packages/pettripfinder/failure_closures/` |
| per-market assembler | `scripts/pettripfinder/assemble_netlify_bundle.py:313 assemble` |
| release (multi-market) assembler | `scripts/pettripfinder/assemble_production_site.py:776 assemble` |
| site generator | `scripts/generate_pettripfinder_columbus_site.py:303 run` |
| TestEveryMarketAssembles | `tests/pettripfinder/test_per_market_release_contracts.py:818` (fixture `market_bundles` :807) |
| release contracts | `scripts/pettripfinder/release_contracts.py`; `deploy/netlify/release_contracts/*.json` |
| participation | `scripts/pettripfinder/launch_participation.py`; `deploy/netlify/launch_participation.json` |
| current-state pins | `tests/pettripfinder/market_state.py`, `tests/pettripfinder/epochs.py`, `tests/pettripfinder/pins/{market_state,deployment_state,supersessions}.json`; held to source by `tests/pettripfinder/contracts/test_market_state_pins.py` |
| policy / fee / identity / geography contracts | `scripts/pettripfinder/contracts/{policy_schema,evidence,fee_computation,identity_key,census,partition,market_geography,...}.py` |
| deployment contract | `scripts/pettripfinder/deployment_authorization.py`, `scripts/pettripfinder/global_deployment.py`; `deploy/netlify/global_deployment_manifest.json`, `deployment_authorizations/`, `deployment_records/` |
| production truth | `deploy/netlify/deployment_records/ptf-deploy-cincinnati-004-6a9d33f5dc8c3d1cf9464376.json` + `tests/pettripfinder/pins/deployment_state.json` `live` block |

Toledo, Nashville, Lexington, Fort Wayne and Chattanooga artifacts are NOT in
this worktree; they were read from their branches with `git show` / `git diff`
(read-only) for the case studies.

## 2. Current release model (Phase 2)

Full table with file:line citations: `atlas_throughput_001_release_model.md`.
Summary of what matters for throughput:

- 29 representations of release truth. The release identity is
  `bundle_sha256 = bundle_digest(file_hashes(site/))` (assemble_production_site
  :633-650), bound into the global manifest → authorization → record →
  `deployment_state.live`. The per-market assembler's `bundle_hash` is a
  DIFFERENT formula and is not bound.
- Hashed into the release: policy package (normalised `content_sha256`), each
  release contract (raw sha), launch participation (raw sha), control files and
  measurement config. NOT hashed: the market registry, census, partition,
  shards, the three generated globals, pins, packets.
- Duplicated state: the published pet-friendly count is stored in ≥12 places
  (package, 4 contract fields, 2 pin fields, partition, manifest, authorization,
  record, deployment_state ×2, participation basis, packet); `bundle_sha256`
  in 8; `source_commit` in 8; three divergent partition-filename tables; two
  definitions of `resolved`.
- No repo script writes the global manifest, an authorization or a record —
  all three are written in-session per runbook §12.

## 3. Regression V2 audit (Phase 3)

Every classifier rule, from `regression_delta.PATH_RULES` (first match wins)
and `VALIDATION_MATRIX`:

| change class | path / condition (rule) | selected suites | full | why |
|---|---|---|---|---|
| BASELINE_MANIFEST_ONLY | prefix `launch_packages/pettripfinder/regression_baselines/` | reverse-dependents only | no | a manifest records a past run |
| GENERATED_REPORT_ONLY | prefix `…/failure_closures/`, `…/markets/reports/`, `…/reports/`; globs `*_report_*.json`, `*_packet_*.json`, `*_verification_*.json`, `*_queue*.json` | reverse-dependents + market_targeted for named markets | no | an output, never an input |
| GENERIC_RUNTIME_CHANGE | glob `…/regression_validation_matrix.json`; prefixes `scripts/pettripfinder/contracts/` (+SCHEMA), `acquisition/`, `brightdata/`, `discovery/` (+ROUTING); globs `*polic*.py`, `*reader*.py`, `*render*.py`, `approved_hotel_profile.py` (+SCHEMA), `*identity*.py`, `*routing*.py`, `census_*.py`, `*corridor*.py` (+ROUTING), `assemble_*.py`, `build_market_manifest.py`, `*deploy*.py`, `release_contracts.py` (+DEPLOYMENT); **prefix `scripts/pettripfinder/`; prefix `scripts/`** | policy_schema, identity_routing, release_contract, cross_market, assembly, deployment_architecture + owning + reverse-dependents | **YES** | "one edit changes what eleven markets derive" |
| DEPLOYMENT_CHANGE | prefix `deploy/`; globs `launch_participation.json`, `*deployment_packet*.json`, `*deployment_manifest*.json`, `ptf_market_manifest*.json`, `markets/manifest*.json` | deployment_architecture, release_contract, assembly | **YES** | what the record claims is served must be what a fresh assembly builds |
| AUTHORITY_CHANGE | prefixes `markets/authority/`, `name_corrections/`, `founder_overrides/`, `coverage/`, `discovered_policy_urls/`, `identity_census` (+ROUTING); globs `hotel_policy_facts*.json`, `hotel_exclusions*.json`, `identity_routing*.json` (+ROUTING), `*seed_businesses*.csv`, `ptf_global_authority_manifest.json`, `*_final_partition_*.json`, `*_census_*.json` (+ROUTING), `markets/*.json` | policy_schema, identity_routing, release_contract, cross_market + market_targeted | **YES** | authority is what the site publishes |
| SCHEMA_CHANGE | with the contracts / reader / renderer rules above | policy_schema, release_contract, assembly | **YES** | a shape the renderer cannot carry is fatal at assembly |
| ROUTING_SEMANTIC_CHANGE | with the identity / routing / census / corridor / discovery rules | identity_routing, cross_market, release_contract + market_targeted | **YES** | a route is an identity's public address |
| TEST_EXPECTATION_CHANGE | prefix `tests/` | owning modules + reverse-dependents + market_targeted | CONDITIONAL: yes when the path is SHARED_TEST_STATE (`tests/pettripfinder/pins/`, `fixtures/`, any `conftest.py`, `epochs.py`, `market_state.py`, `*_freeze.py`) | a shared pin moves suites that never name it |
| BOOKKEEPING_REGISTRATION_CHANGE | a `tests/` .py whose two versions' module-level ASTs differ ONLY in the elements of a container named in `REGISTRATION_CONTAINERS` (today: one — `OTHER_MARKET_RUNS` in `acquisition/test_store_integration_025.py`) | owning module + owning directory + reverse-dependents + market_targeted | no | declares what exists |
| DOCUMENTATION_ONLY | prefix `docs/`; glob `*.md`; `../*.md`; `../.gitignore` | reverse-dependents | no | prose |
| UNCLASSIFIED | no rule (everything else, incl. the bulk of `launch_packages/pettripfinder/`, `conftest.py` at the root, `pytest.ini`, `requirements*.txt`, `data/`, `markets/proposed/`, `identity_census_proposed/`) | every lane except full/market_targeted | **YES** | uncertainty is not a narrow class |

Fallbacks and edge behaviour (read from code, confirmed by classification):

- Whole-change decision = the STRICTEST row any file selects (`plan_for`).
- Unknown path → UNCLASSIFIED → full. Rename → git `R` status, classified by
  the NEW path only; a renamed test module cannot be narrowed (no prior shape).
  Deletion → classified by the deleted path's rule (a deleted authority file is
  AUTHORITY_CHANGE → full). New file → same rules as an edit.
- `conftest.py` under `tests/` → TEST_EXPECTATION + shared → full. Root
  `conftest.py`, `pytest.ini`, `requirements-dev.txt` → UNCLASSIFIED → full.
- Schema (`scripts/pettripfinder/contracts/`) → GENERIC+SCHEMA → full.
- Test infrastructure (`epochs.py`, `market_state.py`, `pins/`) → shared → full.
- Classifier self-change (`regression_delta.py`, `regression_lanes.py`) →
  GENERIC_RUNTIME_CHANGE → full. This order's own `throughput_profile.py` and
  `throughput_baseline.py` classify the same way, which is why its one
  instrumented baseline is also its broad validation.

Classification ONLY of representative real paths (from
`atlas_throughput_001_classifier_audit.json`):

| path | classes | rule | full on its own |
|---|---|---|---|
| `scripts/pettripfinder/nashville_tn_shadow_market_001.py` | GENERIC_RUNTIME_CHANGE | prefix `scripts/pettripfinder/` | YES |
| `scripts/pettripfinder/nashville_tn_routing_001.py` | GENERIC_RUNTIME + ROUTING_SEMANTIC | glob `*routing*.py` | YES |
| `scripts/pettripfinder/nashville_tn_geography_001.py` | GENERIC_RUNTIME_CHANGE | prefix `scripts/pettripfinder/` | YES |
| `scripts/pettripfinder/discovery/config/nashville_tn.json` | GENERIC_RUNTIME + ROUTING_SEMANTIC | prefix `scripts/pettripfinder/discovery/` | YES |
| `launch_packages/pettripfinder/markets/proposed/nashville-tn.json` | UNCLASSIFIED | no rule | YES |
| `launch_packages/pettripfinder/identity_census_proposed/nashville-tn.json` | AUTHORITY + ROUTING_SEMANTIC | prefix `…/identity_census` (matches the PROPOSED dir too) | YES |
| `launch_packages/pettripfinder/nashville_tn_osm_extracts_001.json` | UNCLASSIFIED | no rule | YES |
| `launch_packages/pettripfinder/markets/reports/nashville_tn_routing_001.json` | GENERATED_REPORT_ONLY | prefix `…/markets/reports/` | no |
| `tests/pettripfinder/test_nashville_tn_new_market_001.py` | TEST_EXPECTATION_CHANGE | prefix `tests/` | no (not shared) |
| `launch_packages/pettripfinder/toledo_oh_founder_rulings_001.json` | UNCLASSIFIED | no rule | YES |
| `launch_packages/pettripfinder/reports/factory_throughput_001_test_inventory.json` | GENERATED_REPORT_ONLY | prefix `…/reports/` | no |

Five real branches, classified end to end (`classify_change` over `git diff`):

| branch (base..head) | files | classes seen | FULL | driver paths | of which market-named helpers |
|---|---|---|---|---|---|
| Nashville 001 (d335c50..4f3dd7b) | 45 | GENERATED_REPORT 22, GENERIC_RUNTIME 18, ROUTING 4, AUTHORITY 1, UNCLASSIFIED 2, TEST 1, DOC 1 | YES | 21 | 18 |
| Toledo 001 (2163c4e..133b937) | 37 | GENERATED_REPORT 17, GENERIC_RUNTIME 14, ROUTING 3, UNCLASSIFIED 3, AUTHORITY 1, TEST 1, DOC 1 | YES | 18 | 15 |
| Toledo 002+003 (2163c4e..d335c50) | 82 | GENERIC_RUNTIME 23, GENERATED_REPORT 22, TEST 15, AUTHORITY 11, DEPLOYMENT 7, ROUTING 4, UNCLASSIFIED 4, DOC 2 | YES | 46 | 25 |
| Lexington 001+002 (2163c4e..f1e0435) | 36 | GENERATED_REPORT 19, GENERIC_RUNTIME 17, ROUTING 4, SCHEMA 1 | YES | 17 | 15 |
| Chattanooga 001 (d335c50..4e058a3) | 28 | GENERATED_REPORT 15, GENERIC_RUNTIME 10, ROUTING 4, AUTHORITY 1, UNCLASSIFIED 1, BOOKKEEPING 1 | YES | 12 | 8 |

Note the Chattanooga branch is the only one whose `test_store_integration_025`
edit was narrowed to BOOKKEEPING_REGISTRATION_CHANGE — the narrowing works; it
is simply outvoted by the helpers.

## 4. Test inventory (Phase 4)

Exact collected count at this tree, from the instrumented baseline's
`inventory.json`: see §8 (`atlas_throughput_001_inventory_summary.json`).
Analytical categories (ANALYSIS ONLY; nothing selects by them), by category
over the Chattanooga broad run at 4e058a3 (17,532 collected; the same test set
as the launched Toledo lineage) and the canonical run at 1eab5dd (17,292):

| category (rule) | tests (cha) | seconds (cha) | share | seconds (canon002, demo-media deselected) |
|---|---|---|---|---|
| OTHER_NON_PTF — everything outside `tests/pettripfinder` | 6,756 | 3,861 | 63.5 % | 196 |
| DEPLOYMENT — deployment_architecture lane (045, 046, 047, 012, …) | 327 | 1,130 | 18.6 % | 1,361 |
| ASSEMBLY — assembly lane + `test_per_market_release_contracts.py` | 963 | 648 | 10.6 % | 818 |
| HISTORY — closed-order suites (`*_NNN.py`, pass suites) in sub-packages | 2,247 | 193 | 3.2 % | 135 |
| CORE_SHARED — shared runtime suites, multi-lane modules | 4,088 | 185 | 3.0 % | 212 |
| MARKET_LOCAL — market-named modules | 2,195 | 42 | 0.7 % | 47 |
| OTHER — single-lane top-level modules | 256 | 21 | 0.3 % | 28 |
| FAST_CONTRACT — `contracts/` | 700 | 3.4 | 0.06 % | 3.4 |

By market (module name prefix): market-named modules together cost 42 s of a
6,148 s run. By fixture and by file: `atlas_throughput_001_inventory_summary.json`.

## 5. Assembly call graph (Phase 5)

Full table: `atlas_throughput_001_assembly_duplication.md`. The facts that
matter:

- `TestEveryMarketAssembles` proves, for each of the 11 contract markets
  (including non-participating Detroit), that the market assembles ALONE with
  every minimum gate passing (zero broken links, clean quality report), that
  its route count equals the pinned published count, that its manifest
  carries the reconciliation and the not-an-authorization caveat, that the 11
  bundles are pairwise distinct, and that no contract restates an identity
  allow-list. It is the only per-record RENDER proof for 8 of the 11 markets.
  Its module-scoped `market_bundles` fixture runs 11 full generator builds
  once per broad run (296–436 s measured, charged to `test_all_gates_pass[columbus-oh]`).
- The whole 10-market site is composed THREE times per broad run from
  byte-identical inputs: `045::production` (module fixture), `045::test_production_is_indexable_and_preview_is_not`
  (a preview build whose 10 fragments are identical), `046::production`
  (module fixture asserting the SAME pin). 900–1,360 s per run.
- Columbus alone is generated 15 times per broad run (7 one-market bundles,
  5 bare generator runs, 3 fragments); every other participating market 4
  times (1 bundle + 3 fragments); Detroit once. 52 full site generations per
  broad run, derivable from code.
- No session fixtures; no xdist; no test spawns a subprocess except `git`.
  Production code spawns `git rev-parse HEAD` per assembly and per
  `build_package` (once per contract derivation).
- Existing hashes that could key a cache: `bundle_sha256`, per-file
  `file_hash_manifest.json`, contract `expected_sha256`, participation sha,
  control-file shas. No function fingerprints the generator's INPUT set; the
  plugin added one (`market_input_hash`, `dependency_input_hash`).

## 6. Existing-log reconstruction (Phase 7) — eleven broad runs

Every full-regression junit file kept on this machine was profiled
(`throughput_baseline junit`). `overhead` = suite time − Σ testcase time =
collection + session setup/teardown.

| run (commit) | wall s | min | Σ case s | overhead s | collected | demo-media module s | 045 + 046 + release_contracts s |
|---|---|---|---|---|---|---|---|
| canon002-full (1eab5dd, demo-media DESELECTED, 7-chunk baseline method) | 2,849 | 47.5 | 2,801 | 48 | 17,292 | 0 | 1,830 |
| ti002 (1eab5dd, lane runner) | 6,438 | 107.3 | 6,405 | 34 | 17,310 | 4,073 | 1,390 |
| cinc_full (Cincinnati hardened) | 6,620 | 110.3 | 6,551 | 68 | 17,311 | 4,214 | 1,384 |
| pgh002_broad | 5,607 | 93.5 | 5,574 | 33 | 17,379 | 3,489 | 1,243 |
| pgh003_broad (139f19c) | 5,952 | 99.2 | 5,925 | 27 | 17,379 | 4,063 | 1,096 |
| fortwayne full (7cc6941) | 6,267 | 104.5 | 6,238 | 29 | 17,380 | 3,920 | 1,447 |
| toledo_full | 7,476 | 124.6 | 7,424 | 52 | 17,505 | 3,830 | 2,483 |
| toledo_full2 | 6,293 | 104.9 | 6,267 | 26 | 17,505 | 4,092 | 1,402 |
| toledo_full3 (ee1ce3d) | 6,744 | 112.4 | 6,713 | 30 | 17,512 | 4,440 | 1,435 |
| toledo_launch (548d2f1) | 5,714 | 95.2 | 5,688 | 26 | 17,532 | 3,504 | 1,397 |
| cha-full (4e058a3, ran during this order) | 6,148 | 102.5 | 6,084 | 65 | 17,532 | 3,686 | 1,494 |

Findings that do not depend on the instrumented run:

1. **`tests/website_generation/integration/test_pettripfinder_demo_media.py`
   is 57–66 % of every lane-runner broad run** (3,489–4,440 s of 5,607–7,476 s).
   It is a website-generation integration suite, not a market test; each of
   its 12 real-chain builds rebuilds the SAME committed launch package
   (`_real_chain` is a plain helper called per test, ~280–920 s each). The
   committed baselines c854469 and f75aa95 DESELECT it ("30+ minutes of CPU"),
   but `regression_lanes.run --lane full_regression` runs `tests` with no
   deselect, so every market order since has paid ~65 minutes the baseline
   never counted. The one run that deselected it (canon002-full) took 47.5 min.
2. Collection + session overhead is 26–68 s per run (0.4–1.1 %). Collection
   is not the cost.
3. The all-market assembly cluster (045 + 046 + release_contracts) is
   1,096–2,483 s per run (18–33 % of the run once demo-media is removed).
4. Per-node times are stable across runs within ±30 % except under
   contention (toledo_full: 045 preview 857 s vs a 245–356 s median).
5. The 160-node failure set reproduced by node id in 9 of 11 runs; the two
   exceptions (toledo_full 169, toledo_launch 163) were the orders' own
   TRUE_NEW failures, closed at cause.

## 7. Memory profile (Phase 6/9) — Chattanooga broad run, sampled every 15 s

`atlas_throughput_001_sampler_cha_full.json` (381 samples, pytest pid 36556,
15:19–16:56, run 15:14–16:56):

| interval | pytest working set |
|---|---|
| 15:14–15:49 (acquisition, brightdata, contracts, discovery, PTF top-level incl. the assembly cluster) | 383–472 MB |
| 15:50–16:56 (`tests/website_generation/…`, i.e. the demo-media suite and its neighbours) | 6,418–7,625 MB |
| peak process tree | **7,625 MB** at 16:33 |
| system free memory minimum | **46 MB** (16 GB box) |

The process tree is the single pytest process (no children hold memory).
The 6–7.6 GB plateau is the website-generation real-chain builds; the whole
PetTripFinder tree, including every assembly, runs under 0.5 GB. This is the
"memory contention" the order describes: two broad runs cannot coexist on this
machine, and any market worker running beside one is starved.

## 8. Instrumented solitary baseline (Phase 8/9)

BROAD_BASELINE_STATUS: WAITING_FOR_HEAVY_LANE from 15:14 to 17:14 (a
Chattanooga `full_regression` lane, pid 36556, was already running; its junit
and memory samples are reported above rather than wasted). One instrumented
run was started at 17:23:46 in this worktree at HEAD + the uncommitted
instrumentation (pid 28920, `data/regression/atlas-throughput-001/`), with
the plugin loaded by `-p`, the inventory written at collection, and the
sampler running. No second run was started.

Result (`data/regression/atlas-throughput-001/`: junit, `profile.jsonl` with
17,408 test rows, `inventory.json`; analysed into
`atlas_throughput_001_instrumented_baseline.json` and
`atlas_throughput_001_sampler_baseline.json`):

| measure | value |
|---|---|
| TOTAL WALL TIME | 7,955 s (2 h 12 min 37 s; pytest's own figure 7,957.5 s) |
| COLLECTION TIME | 50.2 s (session start → `pytest_collection_finish`) |
| EXECUTION TIME | 7,905 s |
| CPU (process) | user 5,097 s + system 706 s = 5,803 s (73 % of wall; single-threaded, the rest is I/O wait: 9.36 GB read, 0.82 GB written) |
| PEAK PROCESS MEMORY | 7,538 MB working set (plugin, in-process); 7,417 MB peak of the process tree from the 15 s sampler (505 samples); system free memory minimum 46 MB |
| TOTAL TESTS | 17,408 collected (13,802 test functions, 4,146 parametrized items, 600 files) |
| PASSED / FAILED / SKIPPED / XFAIL | 17,015 / 162 / 218 / 13 (the profile counts the 13 xfails as skipped: 231) |
| phases (Σ over tests) | setup 1,157 s, call 6,692 s, teardown 12 s; slow fixture setups recorded 1,138 s |
| assembly (outer calls ≥ 1 s) | 56 calls, 1,882 s (23.7 % of wall) |

TOP 25 TEST NODES BY ELAPSED TIME (setup + call + teardown):

| s | node |
|---|---|
| 1,280 | `tests/website_generation/integration/test_pettripfinder_demo_media.py::TestDeterminism::test_repeated_real_build_identical` (two real-chain builds) |
| 964 | `…demo_media.py::TestZeroImageFallback::test_no_media_mapping_yields_zero_img` |
| 425 | `…demo_media.py::TestBundle::test_two_content_addressed_assets_materialized` |
| 408 | `…demo_media.py::TestRealPilotIngestion::test_no_filesystem_path_in_dataset` |
| 404 | `…demo_media.py::TestRequestSafety::test_every_img_src_is_bundled_local` |
| 379 | `…demo_media.py::TestBundle::test_no_duplicated_bytes` |
| 367 | `…demo_media.py::TestGeneratedHtml::test_configured_card_and_profile_render_img` |
| 363 | `…demo_media.py::TestRealPilotIngestion::test_asset_hashes_match_committed_bytes` |
| 353 | `…demo_media.py::TestRealPilotIngestion::test_configured_listings_gain_hero_refs` |
| 346 | `…demo_media.py::TestGeneratedHtml::test_img_tags_sitewide_are_exactly_the_two_demo_illustrations` |
| 340 | `…demo_media.py::TestGeneratedHtml::test_imageless_listing_stays_text_only` |
| 324 | `tests/pettripfinder/test_global_deployment_architecture_045.py::test_the_context_is_recorded_in_the_manifest` (carries the module `production` fixture: one 10-market compose) |
| 305 | `…045.py::test_production_is_indexable_and_preview_is_not` (a second, preview compose) |
| 304 | `tests/pettripfinder/test_launch_participation_046.py::test_the_bundle_carries_exactly_the_live_set` (carries 046's `production` fixture: the same compose again) |
| 303 | `tests/pettripfinder/test_per_market_release_contracts.py::TestEveryMarketAssembles::test_all_gates_pass[columbus-oh]` (carries `market_bundles`: 11 one-market bundles) |
| 62 | `tests/pettripfinder/test_prod005_netlify_config.py::TestAssembler::test_both_contexts_succeed` (carries `assembled`: 2 Columbus bundles) |
| 61 | `…prod005.py::TestAssembler::test_deterministic_and_atomic_replace` (2 Columbus bundles) |
| 48 | `tests/pettripfinder/test_prod004_verified_only.py::test_build_is_deterministic` (2 Columbus generator runs) |
| 30 | `tests/pettripfinder/test_homepage_market_awareness.py::TestColumbusProductionBundle::test_the_frozen_bundle_hash_is_unchanged` |
| 29 | `tests/pettripfinder/test_two_market_compat.py::test_columbus_assembler_succeeds_with_two_markets` |
| 28 | `…prod004.py::test_exactly_the_committed_public_hotel_profiles` (carries `build`) |
| 27 | `tests/website_generation/integration/test_pettripfinder_pilot_chain.py::TestEndToEnd::test_repository_materializes` |
| 26 | `tests/pettripfinder/test_atlas_throughput_001.py::TestPluginEndToEnd::test_the_child_run_reports_its_own_outcomes_unchanged` (this order's child pytest) |
| 25 | `…test_atlas_throughput_001.py::TestPluginEndToEnd::test_without_an_output_path_the_plugin_is_inert` |
| 25 | `tests/pettripfinder/test_generate_columbus_site.py::test_build_succeeds_and_reports_launch_ready` (carries `built_site`) |

The demo-media suite alone: 5,630 s = 70.8 % of this run (its determinism
and zero-image tests ran 2–3× slower than in the eleven earlier runs; the
suite as a whole 27 % slower). The "test at roughly 91 %" the order asked
about was measured: the module's first real-chain test began at 18:00 and
its last ended at 19:34.

TOP 20 FIXTURES BY CUMULATIVE SETUP TIME (setups ≥ 0.05 s are recorded):

| s | setups | fixture | scope | what it builds |
|---|---|---|---|---|
| 628 | 2 | `production` | module (045 and 046) | the whole 10-market site, twice, from identical inputs |
| 303 | 1 | `market_bundles` | module | 11 one-market bundles |
| 62 | 1 | `assembled` | module (prod005) | Columbus preview + production bundles |
| 28 | 1 | `build` | module (prod004) | Columbus generator run |
| 26 | 10 | `tmp_path` | function | (only setups over the floor) |
| 26 | 1 | `child_run` | module | this order's child pytest |
| 25 | 1 | `built_site` | module | Columbus generator run |
| 20 | 1 | `routing_delta_from_shards` | module | |
| 6 | 1 | `simulation` | module | |
| 5 | 1 | `package` | module | `load_launch_package()` |
| 4 | 1 | `queues` | module | |
| 3 | 5 | `replay_repo` | function | scratch git repos (test_regression_delta_001) |
| 1.5 | 19 | `repo` | function | |
| < 1 | — | `dry_run`, `st_louis`, `columbus_home`, `rows`, `indianapolis`, `live`, `client` | | |

The demo-media suite has NO fixture: `_real_chain` is a plain helper called
from inside each test, which is why its cost lands in `call`, not `setup`.

TOP ASSEMBLY INPUT KEYS BY BUILD COUNT (outer calls ≥ 1 s; key = kind +
dependency input hash + market + context):

| builds | repeats | Σ s | repeated s | kind | market / context | output hashes |
|---|---|---|---|---|---|---|
| 18 | 17 | 148 | 143 | `pilot_load_launch_package` (the launch-package load the demo-media chain starts with) | – | – |
| 12 | 11 | 153 | 134 | `wge_assembly_engine` (the AssemblyEngine step of each demo-media real chain; the chain's other engines are not wrapped) | – | – |
| 5 | 4 | 117 | 93 | `columbus_site` (bare generator; one of the five under a patched registry) | Columbus | – |
| 5 | 4 | 150 | 120 | `market_bundle` (Columbus, default market) | production | `e853ec0a…` ×4 (+ prod005's preview) |
| 2 | 1 | 628 | 304 | `production_site` | production | `ca59f371…` both times — the LIVE bundle sha |
| 1 | 0 | 302 | 0 | `production_site` | preview | `fb38371b…` (10 fragments identical to the production compose) |
| 1 each | 0 | 16–43 | 0 | `market_bundle` ×11 (`market_bundles`) | each contract market | distinct |

TOP MARKETS BY ASSEMBLY INVOCATIONS: whole-site / no market 45 (3 composes +
Columbus-default bundles + generator runs + demo-media chain steps); every
contract market 1 one-market bundle via `market_bundles`; Columbus 1 + 5
default-market bundles + 5 bare generator runs + 3 fragments. Fragments
inside the three composes: 30 generator runs (10 markets × 3), 12–34 s each,
recorded as nested `columbus_site` calls.

| measure | value |
|---|---|
| TOTAL ASSEMBLY INVOCATIONS | 56 outer calls ≥ 1 s (542 wrapped calls including 82 nested and 404 sub-second synthetic-fixture calls) |
| UNIQUE ASSEMBLY INPUTS | 19 keys |
| REPEATED IDENTICAL ASSEMBLIES | 37 by key; the material ones: 1 whole-site production compose (304 s), the preview compose's 10 identical fragments (193 s of its 302 s), 4 Columbus bundle repeats (120 s), 3–4 Columbus generator repeats (93 s), 10 demo-media real-chain repeats of one with-media input |
| TIME SPENT ASSEMBLING IDENTICAL INPUTS | PetTripFinder assemblies: ≈ 710 s of 1,882 s (38 %). Adding the demo-media chain, whose 11 with-media builds all consume one committed input: ≈ 3,800 s more (its 12 builds cost 5,630 s; one cold with-media and one no-media build would cost ≈ 800 s). Total ≈ 4,500 s ≈ 75 min of a 133-min run. |
| COLD VS REPEATED BUILD TIME | whole-site compose cold 323 s → repeat 304 s; Columbus bundle cold 30 s → repeat 20–31 s; generator cold 25 s → repeat 23 s; demo-media chain 353 s first → 340–425 s repeats (1,280 s for the two-build determinism test). Repeats are NOT cheaper: nothing is cached, and a repeat costs the full build. |

Failure classification of this run against `regression_baselines/f75aa95.json`
(`regression_lanes classify`, by node id): PRE_EXISTING 160 (the whole
baseline set, none resolved), EXPECTED_EPOCH_CHANGE 0, TEST_HARNESS_FLAKE 0,
**TRUE_NEW_FAILURE 2**:

1. `tests/pettripfinder/test_prod005_netlify_config.py::TestAssembler::test_reuses_existing_generator`
   — asserts `asm.generate_site is generator_run`. The plugin wrapped the
   generator's `run` AFTER `assemble_netlify_bundle` had bound the original
   as `generate_site`, so the two names no longer pointed at one object. An
   instrumentation artifact, present only when the plugin is loaded (the node
   passed in every one of the eleven un-instrumented runs). Fixed at cause by
   wrapping the generator BEFORE the modules that bind it (`WRAP_TARGETS`
   order); the node passes with the plugin loaded and without it.
2. `tests/pettripfinder/acquisition/test_normalization_041.py::test_the_simulation_wrote_nothing_to_the_repository`
   — asserts `git status --porcelain` is identical before and after a
   simulation. The run executed in a worktree carrying this order's
   uncommitted files, and the report this order writes under
   `launch_packages/…/reports/` changed size during the run, so the two
   listings differed. A worktree artifact: the node passes on a committed tree.

Closure: §18 — both nodes are proved CLOSED by node id after the commit,
through `regression_delta validate`, without a second broad run.

## 9. Failure baseline audit (Phase 10)

`atlas_throughput_001_failure_baseline_audit.json`: the 160 node ids of
`regression_baselines/f75aa95.json`, grouped with the failure messages of the
toledo_full3 run (whose failing set is IDENTICAL to the baseline by node id)
and a source scan of every failing module for gitignored `data/` reads.

| group | count | representative node ids | why it matters | data-only new market could move it? | launch-blocking in principle? |
|---|---|---|---|---|---|
| ENVIRONMENT | 150 | `acquisition/test_observation_rederivation_018.py` (18, FileNotFoundError `data/acquisition/…`), `acquisition/test_marriott_template_021.py` (17, "no persisted capture"), `acquisition/test_identity_binding_027.py` (14, 11 FileNotFoundError), `acquisition/test_store_reader_sync_030.py` (12), `test_louisville_authority.py` (5, `data/operator_evidence/…`), `test_indianapolis_promotion_validation_003.py` (3, FileNotFoundError) | closed-order suites that re-derive a Milwaukee / Indianapolis / Louisville / Grand Rapids authority from a gitignored observation store or capture corpus that a fresh worktree never has; the assertion fails on an absent input, not on a wrong derivation | no — none reads another market's committed authority; adding a market cannot create or remove the corpus | no, as long as the corpus is absent; YES in a worktree that carries the corpus, where the same nodes are the identity/policy derivation proof for those markets |
| HISTORICAL_COUNT/PIN | 10 | `acquisition/test_founder_review_036.py` (5: e.g. "expected at least one approved-proposal row with no weight"), `test_indianapolis_authority_promotion_017.py` (5: `assert 54 == 82` — the 017 epoch count against the current 82) | closed-order expectations over a package that later orders grew; the 017 module was scoped by name in the 013/014 lineage but still restates a whole-market count | no — they name their own market; a new market adds no record to Indianapolis or Milwaukee | no; they are candidates for the epoch/cohort pin migration (`ptf-cincinnati-hardened-revalidation-002` recipe) |
| IDENTITY_CRITICAL / POLICY_CRITICAL / ARTIFACT_INTEGRITY_CRITICAL / RELEASE_CRITICAL | 0 | — | none of the 160 is a live-market identity, policy, artifact or release proof | — | — |
| LEGACY_EXPECTATION / FLAKE / UNKNOWN | 0 | — | — | — | — |

No failure was waived, re-pinned or edited. The two "DID NOT RAISE
ReleaseContractError" nodes (`test_normalization_041`, `test_publication_042`)
are staging-directory tests over the Milwaukee 037 prepared contract whose
module also derives from the absent store; they are ENVIRONMENT by the
module-level rule and should be re-checked in a worktree that carries
`data/acquisition/` before any launch that touches Milwaukee.

## 10. Market-local case study (Phase 11) — Nashville 001 and Toledo 001

FILES CHANGED (Nashville, d335c50..4f3dd7b): 45 — 18 `scripts/pettripfinder/nashville_tn_*.py`
helpers, `scripts/pettripfinder/discovery/config/nashville_tn.json`, 24 JSON
artifacts under `launch_packages/pettripfinder/` (`markets/proposed/nashville-tn.json`,
`identity_census_proposed/nashville-tn.json`, `nashville_tn_osm_extracts_001.json`,
21 `markets/reports/nashville_tn_*.json`), one test module, the regenerated test
inventory, one FINAL.md.

IMPORTS (read from the helpers on the branch): `scripts.pettripfinder.markets.contract`
(`MC`), `scripts.pettripfinder.site_data.normalize_name`,
`scripts.pettripfinder.hotel_exclusions.address_key`, stdlib. No helper imports
another helper's runtime, the assembler, a reader, a renderer or a contract
validator.

WRITES: only `markets/proposed/nashville-tn.json`, `identity_census_proposed/nashville-tn.json`,
`markets/reports/nashville_tn_*.json`, and gitignored `data/` runs.
READS: the committed Dayton brand harvest, OSM extracts, the CVB sitemap, the
market's own proposed artifacts.

PRODUCTION RUNTIME REACHABILITY: none — no module under `scripts/pettripfinder/`
outside the `nashville_tn_` namespace imports a `nashville_tn_*` module
(grep on the branch), and the generator / assemblers read `markets/*.json`,
`identity_census/`, not the `proposed/` directories.
ASSEMBLER REACHABILITY: none (Nashville is not registered; `select_markets`
never sees it). SHARED CONTRACT REACHABILITY: read-only use of three pure
functions. TEST INFRA REACHABILITY: the regenerated
`factory_throughput_001_test_inventory.json` (GENERATED_REPORT_ONLY) and one
new test module.

WHAT SPECIFIC FACT CAUSES REGRESSION V2 TO REQUEST BROAD VALIDATION?
The classifier decides by PATH PREFIX, and `prefix:scripts/pettripfinder/`
→ GENERIC_RUNTIME_CHANGE is a mandatory-full row. Eighteen helper files match
it (three of them also match the semantic globs `*routing*.py`,
`*corridor*.py`), the discovery config matches
`prefix:scripts/pettripfinder/discovery/`, the proposed census matches
`prefix:launch_packages/pettripfinder/identity_census` (which does not
distinguish `identity_census/` from `identity_census_proposed/`), and the
proposed market config and OSM extract match no rule (UNCLASSIFIED → full).
Any ONE of those 21 files is enough. The classifier has no notion of a
market-local namespace, of imports, or of write roots; a helper that imports
nothing but stdlib is indistinguishable from an edit to the assembler.

COULD THE FILE BE PROVEN ISOLATED? **YES** — minimum proof:
(1) the file's path is inside a declared market namespace
(`scripts/pettripfinder/<market_us>_*.py`, `launch_packages/pettripfinder/markets/proposed/<market>.json`,
`identity_census_proposed/<market>.json`, `markets/reports/<market_us>_*.json`,
`<market_us>_*.json` at the package root, `discovery/config/<market_us>.json`);
(2) an import scan of the actual file shows only stdlib and a committed
allow-list of pure shared functions (`markets.contract`, `site_data.normalize_name`,
`hotel_exclusions.address_key`, …), no `importlib`, `__import__` or `subprocess`;
(3) a write-root scan shows every literal output path inside the namespace
or under `data/`; (4) no module outside the namespace imports the file
(reverse-import scan, which `regression_delta.reverse_dependents` already
does over tests and would need to do over `scripts/`); (5) the market is not
in `launch_packages/pettripfinder/markets/*.json` (unregistered → unreachable
by the assembler). Toledo 001 (37 files, 18 drivers, 15 helpers) satisfies the
same five conditions; Toledo 002/003 does NOT (it edits
`assemble_production_site._partition_path`, `regression_lanes.MARKET_PREFIXES`,
eleven shared test modules, the shards and participation — a genuine
full-regression change).

Regression V2 was NOT modified.

## 11. Critical safety invariants (Phase 12)

Full map with file:line: `atlas_throughput_001_safety_invariants.md`. Of the
13 hazards, only five facts genuinely require composing the whole site:
byte-level route collision between fragments, the rendered-surface content
gates, `global.live_routes_preserved` as written, bundle determinism /
reproduction of the pinned sha, and a render of every record (one market at a
time suffices — `market_bundles` does this). Everything else is JSON-only and
runs in seconds. Hazards with NO build- or deploy-time fail-closed gate today:
H2 first-party binding, H3 beyond renderable shape, H7 route-level
preservation for the nine non-Columbus live markets, H9 determinism (skipped
unless `PTF_ASSEMBLER_FULL_BUILD=1`), H12 rollback target's market set, H13
at every paid call site (URL-level double-buy is an open xfail defect).

## 12. Performance baseline table (Phase 13)

Measured from the cha-full junit (17,532 collected, 6,148 s) unless marked;
memory from the sampler; assembly calls from the code-derived call graph;
"operator involvement" from the runbook flow.

| phase | wall time | CPU time | peak memory | assembly calls | unique inputs | duplicate builds | test count | operator involvement | notes |
|---|---|---|---|---|---|---|---|---|---|
| classification (`regression_delta classify`) | 7 s (V2 benchmark) / 4–9 s here | ≈ wall | < 100 MB | 0 | – | – | – | none | reads ~400 test sources once |
| collection | 26–68 s across 11 runs | ≈ wall | 82 MB (contracts subset) | 0 | – | – | 17,292–17,532 | none | `pytest_collection_finish` − session start |
| contracts (`tests/pettripfinder/contracts`) | 3.4 s | ≈ wall | < 100 MB | 0 | – | – | 700 | none | 716 tests in 34 s when run alone (with the Columbus generator suite) |
| market-local tests | 42 s | ≈ wall | < 500 MB | 0 | – | – | 2,195 | none | all 11 markets' own modules |
| shared / core | 185 s | ≈ wall | < 500 MB | 0 | – | – | 4,088 | none | |
| history (closed-order suites) | 193 s | ≈ wall | < 500 MB | 0 | – | – | 2,247 | none | 150 of the 160 baseline failures live here |
| assembly (assembly lane + release_contracts) | 648 s | ≈ wall | < 500 MB | 11 NB + 17 Columbus builds | 12 | 11 (Columbus) | 963 | none | `market_bundles` 330 s; prod005 4 builds 115 s; prod004 3; two_market 2; homepage 1 |
| deployment tests (045, 046, 047, …) | 1,130 s | ≈ wall | < 500 MB | 3 all-market composes = 30 fragments | 1 (all identical) | 2 composes = 20 fragments | 327 | none | 045 765 s (2 composes), 046 340 s |
| non-PTF suites incl. demo-media | 3,861 s | ≈ wall | 7,625 MB | 12 real-chain builds | 2 (with/without media) | 10 | 6,756 | none | demo-media alone 3,686 s |
| failure comparison / reporting (`regression_lanes classify`) | < 5 s | – | – | 0 | – | – | – | reads the JSON | |
| release assembly (`assemble_production_site` CLI, one compose) | 410 s (FT-001 benchmark) / 300–430 s per compose here | ≈ wall | < 500 MB | 1 | 1 | 0 | – | starts it | |
| subprocess work | UNKNOWN as a total; every assembly and every `build_package` spawns `git rev-parse HEAD` (≈ 60 per broad run, ~50 ms each) | – | – | – | – | – | – | – | |
| fixture setup / teardown | see §8 (instrumented) | | | | | | | | |

## 13. Bottleneck ranking (Phase 14)

A. VERIFIED BY MEASUREMENT

| # | constraint | current cost | frequency | candidate solution | expected maximum saving | risk of narrowing |
|---|---|---|---|---|---|---|
| A1 | `test_pettripfinder_demo_media.py` in the market release lane | 3,489–4,440 s per broad run (57–66 %); 6–7.6 GB RSS for 65 min; system free memory → 46 MB | every broad run the lane runner starts (10 of 11 kept) | own lane / module-scoped real-chain fixture; make `full_regression` = the committed baseline's definition | ~60 min and ~7 GB per broad run | none for market data; keep it on the seed-CSV / categories change path |
| A2 | three identical all-market composes (045 ×2, 046) | 900–1,360 s per broad run | every broad run | one input-hashed compose per session, reused | ~600–900 s per run | determinism tests must keep building twice; cache keyed on content |
| A3 | Columbus one-market builds ×15 (7 NB + 5 GEN + 3 fragments) | ~420 s per run beyond the first | every broad run | same cache | ~350 s | same |
| A4 | broad regressions demanded by path-prefix classification of market-local helpers | one 95–125 min run per shadow-market order if the classifier is obeyed (Nashville/Toledo/Lexington/Chattanooga all YES) | every new-market order | ownership manifest + MARKET_LOCAL class with import/write-root proof | 1 broad run per shadow order; 3 of Toledo's 4 broad runs were promotion/launch (genuinely shared) | over-inclusive reverse-import scan must stay; shared tables stay full |
| A5 | four broad runs inside one promotion+launch (Toledo 002/003: 7,476 + 6,293 + 6,744 + 5,714 s) | 437 min of regression per launch | every launch | (A1) + delta-scoped closure already exists (V2); post-deploy run is DEPLOYMENT_CHANGE by doctrine | with A1 alone: 437 → ~170 min | the post-deploy proof is doctrine, not waste |
| A6 | hardware contention | cha-full 102.5 min vs canon002 47.5 min with demo-media out; Chattanooga OSM index 70 min "while another market's full broad regression held the CPU" | whenever two lanes overlap | A1 removes the 7 GB plateau; serialise broad runs | UNKNOWN beyond A1 | – |

B. STRONGLY INDICATED BUT NOT YET MEASURED

| # | constraint | evidence | candidate | note |
|---|---|---|---|---|
| B1 | `git rev-parse HEAD` per assembly / per `build_package` (~60 spawns per run) | code reading; ~50 ms each | memoise per session | small |
| B2 | 29 representations / ≥12 copies of the published count | release-model audit | one per-market input manifest, one release-record writer | throughput of the promotion order, not of the suite |
| B3 | founder active time | no instrument exists | timestamped rulings | unknown magnitude |

C. SPECULATIVE

| # | constraint | note |
|---|---|---|
| C1 | xdist parallelism | blocked by fixed absolute output paths, process-global generator state, no session fixtures; not a quick win |
| C2 | collection time | measured 26–68 s; not worth work |

## 14. Frozen success criteria (Phase 15)

`atlas_throughput_001_success_criteria.json` — 14 targets, every one
`TARGET_NOT_CLAIMED`, each with the current measured evidence and the
instrument that would move it.

## 15. Three-market experiment (Phase 16)

`atlas_throughput_001_three_market_experiment.json` — DEFINED_NOT_EXECUTED:
size bands (SMALL/MEDIUM 40–90 census, MEDIUM 91–149, LARGE ≥150), the
independence proof (no branch, config, proposed census or report for the
market before the opening artifact), minimum thresholds per band (PF ≥ 12 /
25 / 50; resolved ≥ 30 % of census; every unresolved row carries a next lane;
founder queue disclosed before promotion), and the measurement method for
every interval the order names.

## 16. Design input for 002 (Phase 17)

`atlas_throughput_001_002_input_packet.md` — six deliverables in order, each
tied to the measurement above: (1) demo-media out of the market release lane,
(2) input-hashed whole-site / one-market bundle cache, (3) ownership manifest +
MARKET_LOCAL class with import and write-root proof, (4) dynamic-dependency /
test-infra / classifier self-change protection, (5) the critical lane from the
invariant map, (6) release-coordinator inputs from the release-model audit.

## 17. Instrumentation (Phase 6/19)

- `scripts/pettripfinder/throughput_profile.py` — opt-in pytest plugin
  (`-p`), inert without `--ptf-profile-out`; JSONL rows: session_start,
  collection, fixture_setup, test (setup/call/teardown, outcome, peak working
  set), assembly (invocation id, kind, market, context, elapsed, output hash,
  `market_input_hash`, `dependency_input_hash`, cache = NO_CACHE, exit
  status, error), session_finish (wall, collection, execution, exit status,
  counts, CPU, io bytes, peak working set, recorder errors);
  `--ptf-inventory-out` writes the Phase 4 inventory at collection. Every hook
  swallows its own exceptions; the assembly wrap calls the original and
  returns its result unchanged (proved by `test_atlas_throughput_001.py`).
- `scripts/pettripfinder/throughput_baseline.py` — read-only analysis CLI:
  `junit`, `run`, `sampler`, `classify`, `failures`.
- `tests/pettripfinder/test_atlas_throughput_001.py` — 28 targeted tests
  (recorder, fingerprints, wrap pass-through and error path, plugin end to
  end in a child pytest, inventory, junit/run/sampler/classifier/failure
  analysis, committed artifacts).
- Both modules classify GENERIC_RUNTIME_CHANGE (prefix `scripts/pettripfinder/`)
  → the one instrumented baseline is their broad validation (§8).

## 18. Closure of the two TRUE_NEW nodes (Phase 19)

CLOSURE_PENDING
