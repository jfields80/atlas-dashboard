# ATLAS-THROUGHPUT-004 — persistent content-addressed market-bundle cache

Branch `worker/atlas-throughput-001`, continued from the pushed 003 head `9a4fe55`. Engineering only:
no market authority changed, nothing promoted, nothing deployed, no paid provider call.

## What exists now

| piece | where | what it proves |
|---|---|---|
| The cache | `scripts/pettripfinder/bundle_cache.py` | `BundleCache.build_or_reuse(package, work_dir=…)`: stage → canonical build-input manifest → key → trusted lookup (extract, re-hash, receipt binding, policy, revocation, freshness) → HIT / HIT_AFTER_WAIT / REVALIDATE, else per-key lock → cold build (traced for undeclared reads) → determinism (second cold build) → atomic publication (archive, receipt, then the index row) |
| The declared closure | `launch_packages/pettripfinder/bundle_cache_closure.json` | the 43 shared data files + the market's affiliate shard + 177 repository modules a staged build reads/loads, MEASURED by tracing Dayton and Cleveland builds; a build that reads outside it is never trusted |
| Storage | `data/bundle_cache/` (gitignored; `PTF_BUNDLE_CACHE_ROOT` overrides) | `objects/<bundle sha>.zip` immutable, `index/<key>.json`, `receipts/<digest>.json`, `locks/`, `quarantine/`, `tmp/`, `telemetry.jsonl` |
| Fast-lane integration | `fast_release_lane.run_fast_lane(..., bundle_cache=…)` | rule J may be a trusted hit (`MARKET_BUILD_REQUIRED = NO`), rule K inherits the bundle receipt's determinism; rules A–I, L–O still decide the release |
| Regression V2 | `regression_delta.fast_data_only_release` | `MARKET_BUILD_REQUIRED` from a cheap probe; `FULL_REGRESSION_REQUIRED` unchanged (a bundle is not a release proof); `bundle_cache.py` + closure file are narrowing blockers |
| Telemetry | `throughput_profile` session rows `bundle_cache` / `bundle_cache_request` | RUN_ID, MARKET, BUILD_INPUT_KEY, CACHE_STATUS, seconds, bytes, digest |
| Pilot | `scripts/pettripfinder/atlas_throughput_004_pilot.py` | cold → warm in a SEPARATE PROCESS with builds forbidden, the invalidation matrix, concurrency, multi-market reuse, retention dry run, benchmark |
| Tests | `tests/pettripfinder/test_atlas_throughput_004.py` | the 25-case matrix (one `slow` cross-process case with real builds) |
| Policy | `fast_release_activation.json` | `PERSISTENT_CACHE_IMPLEMENTED = YES`, `PERSISTENT_CACHE_VALIDATED = YES`, `PRODUCTION_RELEASE_CONSUMPTION = DISABLED` |

Reports: `launch_packages/pettripfinder/reports/atlas_throughput_004_*`.

## How to use it

```
python -m scripts.pettripfinder.atlas_throughput_004_pilot --work-dir C:\ptf004\pw --cache-root C:\ptf004\pcache --out <report.json>
python -m pytest tests/pettripfinder/test_atlas_throughput_004.py -m "not slow"
```

A lane or coordinator holding a sealed package: `BundleCache().build_or_reuse(package, work_dir=<short path>)`;
`cold_required=True` when the caller's claim IS a cold build (a determinism proof). Keep work directories
short on Windows (260-character paths). A hit materialises `<work>/out/site/`, re-hashed to the deployer's
`bundle_digest` formula.

## Boundaries

A cache hit proves artifact identity: these bytes are what these declared inputs produce, validated under
this policy. It does not authorise a release (003's lane does), it does not compose the whole site (005),
and the production assembler and deployer do not read it.
