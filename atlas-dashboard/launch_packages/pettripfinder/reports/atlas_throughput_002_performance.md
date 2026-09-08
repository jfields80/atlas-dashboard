# ATLAS-THROUGHPUT-002 -- performance report

Data: `atlas_throughput_002_performance.json` (the representative market-local run, profiled), `atlas_throughput_002_cold_reuse_parity.json`, `atlas_throughput_002_migration_audit.json`.

## OLD BROAD PATH versus NEW MARKET_LOCAL PATH

The change measured is Nashville 001's own change surface (42 files replayed as untracked additions into this worktree at 74152bd, minus the root-level `nashville_tn_osm_extracts_001.json` the proof rejects, the regenerated shared inventory and the FINAL.md). OLD = what Regression V2 charged it before 002: the whole suite, measured by the 001 instrumented baseline. NEW = what it owes now.

| | OLD BROAD PATH | NEW MARKET_LOCAL PATH |
|---|---|---|
| classification | (prefix rule, no proof) | 11.3 s; classes ['TEST_EXPECTATION_CHANGE', 'GENERATED_REPORT_ONLY', 'MARKET_LOCAL_TOOLING']; FULL_REGRESSION_REQUIRED = NO; assembly required = False |
| selected suites | every test under `tests/` | 19 modules: the zone's own suite (`test_nashville_tn_new_market_001.py`), the 16 per-market contract modules, reverse dependents |
| wall | 7955.454 s | 317.72 s (320.7 s incl. start-up) |
| collection | 50.18 s | 3.726 s |
| selected tests | 17408 | 1237 |
| outcome | {'passed': 17015, 'skipped': 231, 'failed': 162} | {'passed': 1229, 'failed': 3, 'skipped': 5} |
| assembly executions | 56 outer calls | 2 (fail-closed contract probes, ~1.5 s each; no site generated) |
| unique input keys | 19 | 2 |
| reuse hits | 0 | 0 (nothing to reuse) |
| peak working set | 7538.1 MB (tree 7416.7 MB) | 127.2 MB |
| demo-media / website-generation selected | yes | False / False |

Ratio: wall 25.0x, tests 14.1x. These are different scopes by design -- the market-local path runs the market's own gates and the contract rows, the broad path is the proof for shared changes -- and are compared only as the cost a proven-isolated change pays.

Failures in the market-local run not in the f75aa95 baseline: 3 -- `test_factory_throughput_001::test_the_committed_inventory_reproduces_from_the_suite` and `test_nashville_tn_new_market_001::test_production_truth_is_unchanged_by_this_order` are replay artifacts (the Nashville suite pins its own branch's inventory and production truth: 11 markets / 803 profiles on its branch, 10 / 786 in this tree); `test_atlas_throughput_002::TestClassifierMatrixSynthetic::test_a_deleted_local_helper_with_a_consumer_stays_broad` was a real defect in the proof's git reads (module-load-time cwd) fixed at cause in 74152bd before the audit.

## Cold / reuse benchmark (quiet tree)

| path | cold s | reuse s | forced cold s | files | byte-identical |
|---|---|---|---|---|---|
| generator_site (Columbus) | 25.7 | 7.2 | 25.5 | 668 | True |
| market_bundle (Columbus, production) | 26.4 | 2.2 | 39.2 | 670 | True |
| production_site (10 markets, production) | 409.8 | 8.8 | - | 4835 | True |

Preview compose with fragment reuse: 340.9 s (composition rebuilt; fragments copied).

## Inside the migration audit

See `atlas_throughput_002_migration_audit.json` / `atlas_throughput_002_assembly_reuse.md`: 3,815 s wall (was 7,955 s), 27 reuse hits, 746 s avoided, demo-media 1,494 s (was 5,630 s), PRE_EXISTING 160, TRUE_NEW 1 -> 0 after node-id closure.
