# ATLAS-THROUGHPUT-002 — FINAL

Market-local ownership, regression scope, and in-run assembly reuse.
**No market authority, pin, participation, promotion state, deployment
record, ledger or production launch rule changed. Nothing was promoted or
deployed. Exactly one broad regression (the one-time migration audit) was
launched.**

Full artifacts: `atlas-dashboard/launch_packages/pettripfinder/reports/atlas_throughput_002_*`.

---

## PRECHECK

| item | value |
|---|---|
| worktree / branch | `C:\Atlas-Throughput-V1` / `worker/atlas-throughput-001` (no new worktree) |
| 001 HEAD at start | `0a623a0fb5797ec0f392b298b5552142f92e018e`; `origin == HEAD`; tree clean |
| 001 TRUE_NEW | 0 (`failure_closures/atlas-throughput-001-1.json`: PRE_EXISTING 24, TRUE_NEW 0, both nodes CLOSED) |
| 001 artifacts read | baseline report, broad-run profiles, instrumented baseline, classifier audit, assembly duplication, safety invariants, success criteria, 002 input packet, three-market experiment |

## 001 MEASURED INPUTS

Instrumented broad run 7,955 s; demo-media 5,630 s (71 %); 56 PetTripFinder
assembly calls / 1,882 s / 19 unique keys / 37 identical builds (~710 s);
three identical whole-site composes; Columbus ×15; every shadow-market helper
forced broad by `prefix:scripts/pettripfinder/` (+ `*routing*.py`); Regression
V2 blind to namespace, imports, writes, reverse imports, reachability and
registration; PROVABLY_TOO_BROAD = YES.

## OWNERSHIP MODEL

`launch_packages/pettripfinder/market_local_ownership.json`
(`ptf-market-local-ownership/1.0`), loaded and validated by
`scripts/pettripfinder/market_local_ownership.py`:

- per zone: MARKET, EXECUTION_ZONE (SHADOW / SHADOW_UNTIL_REGISTERED),
  OWNED_PATHS, ALLOWED_WRITE_ROOTS, ALLOWED_READ_ROOTS, OWNED_TESTS,
  PRODUCTION_RUNTIME_INCLUDED (all NO); a zone may only own patterns that
  carry its own id; malformed / duplicated / unsubstituted → `OwnershipError`
  (no zone trusted);
- repository-wide: `shared_import_allowlist` (contracts, acquisition capture
  lanes, brightdata readers, discovery utilities, `markets.contract`,
  `site_data`, `hotel_exclusions`, `regression_inventory`, …),
  `shared_write_allowlist` (`data/` and the two generated-report directories),
  `allowed_subprocess` (read-only git subcommands; `python -m pytest` /
  the lane runners), `reachability_scan_exclusions` (the classifier's own
  self-tests, test modules only), and the `never_local` fence (deploy/,
  authority, identity_census/, contracts/, acquisition/, brightdata/,
  discovery/*.py and its shared configs, pins, fixtures, the classifier, the
  lanes, the registry, the proof, the cache, the profiler, the assemblers,
  the generators, conftest, pytest.ini, every `markets/*.json`, package,
  partition, census and packet file);
- zones registered: nashville-tn, chattanooga-tn, lexington-ky,
  fort-wayne-in (SHADOW), toledo-oh (SHADOW_UNTIL_REGISTERED, kept so the
  transition is proved rather than assumed). No blanket claim over
  `scripts/pettripfinder/`.

## ISOLATION PROOF

`scripts/pettripfinder/market_local_isolation.py` — for every changed path
whose Regression V2 rule is in `MARKET_LOCAL_REFINABLE_RULES`:

1. NAMESPACE — exactly one zone owns the path; for a rename, the old path too.
2. IMPORTS — every import stdlib / allow-listed / the zone's own; no
   `importlib`, `__import__`, `exec`, `runpy`; `from x import y` accepted if
   either `x` or `x.y` is allowed.
3. WRITES — every `open(...,'w')`, `write_text/bytes`, `mkdir/makedirs`,
   `rename/replace/remove`, `shutil.*` target resolved by a static evaluator
   (constants, f-strings, `os.path.join`, `Path /`, `__file__` anchors,
   module constants, function-local assignments, loop variables over literal
   collections, argparse defaults, `a or b`, constants imported from a sibling
   helper of the same zone); an unresolvable target FAILS; the target must
   lie inside the zone's roots or the shared report/data roots.
4. REACHABILITY — `git grep` of the module stem (data files: their path) at
   the head revision over scripts/, engines/, repositories/, tests/,
   conftest, deploy/, pytest.ini, netlify.toml, core/, services/, routes/;
   any hit outside the zone (and outside the declared self-tests) fails; a
   data file's directory enumerated by shared code (`glob/iterdir/listdir/
   rglob/scandir` naming both the directory and its parent segment, or a
   module beside it) fails; a subprocess argv must resolve to `git
   <read-only subcommand>` (through a `*args` wrapper, by its call sites) or
   `python -m pytest|regression_lanes|regression_delta`; a deleted file is
   scanned at the base.
5. REGISTRATION — no `markets/<id>.json` and no launch-participation row at
   the head; `production_runtime_included = NO`.

Every failure names its condition and reason; UNKNOWN is a failure.
Ownership proof over the five real branches
(`atlas_throughput_002_ownership_proof.json`): 68 proofs, 63 passed;
failures: reachability 5 (root-level artifacts in the enumerated package
root; a Toledo data file named by a shared test), namespace 2, imports 2,
writes 2, registration 2 (all Toledo 002/003).

## REGRESSION V2 BEFORE / AFTER

`regression_delta.py`: new class `MARKET_LOCAL_TOOLING` (assembly not
required, full regression not required; owes the zone's own test modules,
the per-market contract rows, and every test module naming the changed
one); `MARKET_LOCAL_REFINABLE_RULES` (the `scripts/pettripfinder/` prefix,
the discovery prefix, the eight filename globs, `identity_census_proposed/`,
`markets/reports/`, `docs/`, "no rule" — never an authority, deployment or
contracts rule); `NARROWING_BLOCKERS` (classifier, lanes, inventory,
registry, proof, cache, profiler, matrix export, conftest, pytest.ini,
requirements, plus every shared test state path) — a change set carrying any
of them gets no narrowing; renames are captured (`git diff -M`) and both
paths evaluated; `identity_census_proposed/` re-ruled from AUTHORITY to
UNCLASSIFIED before the proof. `classify_path` (the pure path verdict) is
unchanged for every runtime and authority file; the six mandatory-full
matrix rows are byte-for-byte what V2-001 committed (proved against the
matrix read from git).

Real branches (`atlas_throughput_002_plan_matrix.json`, `atlas_throughput_002_classifier_before_after.md`):

| branch | paths | OLD drivers → NEW drivers | MARKET_LOCAL paths | NEW verdict and the one reason |
|---|---|---|---|---|
| Nashville 001 (d335c50..4f3dd7b) | 45 | 21 → 1 | 20 | FULL=YES only for `launch_packages/pettripfinder/nashville_tn_osm_extracts_001.json` — the package root is enumerated by `tests/pettripfinder/test_build_capture_queue.py` |
| Chattanooga 001 (d335c50..4e058a3) | 28 | 12 → 1 | 11 | FULL=YES only for the shared `discovery/config/osm_extracts.json` row |
| Lexington 001+002 (2163c4e..f1e0435) | 36 | 17 → 1 | 16 | same shared OSM registry row |
| Toledo 001 (2163c4e..133b937) | 37 | 18 → 2 | 16 | two root-level artifacts (`toledo_oh_osm_extracts_001.json`, `toledo_oh_founder_rulings_001.json`) |
| Toledo 002+003 (2163c4e..d335c50) | 82 | 46 → 46 | 0 | blockers (`regression_lanes.py`, the pins), registration, shared writes: still fully broad, as it must be |

The representative replay of Nashville 001 into this worktree with the one
rejected root artifact left out: `FULL_REGRESSION_REQUIRED = NO`, 19
modules, classes {MARKET_LOCAL_TOOLING, TEST_EXPECTATION_CHANGE,
GENERATED_REPORT_ONLY}.

## DEMO-MEDIA LANE

`website_generation_integration` lane (8 modules), marked at collection,
runnable alone, still inside every `full_regression`; role documented in
`atlas_throughput_002_demo_media_lane_role.md`. Not selected by any
MARKET_LOCAL_TOOLING plan (proved). Nine consumer tests share one module
fixture; the two cold-claim tests keep their own builds (12 → 4 chains).
Nothing deleted, skipped or weakened. A market-local run is reported as its
module list, never as a full regression.

## ASSEMBLY REUSE

`scripts/pettripfinder/assembly_session_cache.py` (see
`atlas_throughput_002_assembly_reuse.md`): generator / per-market bundle /
whole-site compose reuse a verified copy for the same key (build args +
content fingerprint of every input root + patched registry/census dirs +
`PTF_*` env + builder module state + interpreter); nothing stored on
failure; digest re-checked on every hit; one copy per consumer; per-key
locks; `cold()` around the three explicit cold-execution tests;
`PTF_ASSEMBLY_REUSE=0` disables. Profiler rows carry `cache =
BUILD_EXECUTED | REUSE_HIT`, `input_key`, `reused_seconds_avoided`; the
session summary gives INPUT_KEY / BUILD_COUNT / REUSE_COUNT / BUILD_SECONDS /
REUSED_SECONDS_AVOIDED per key.

## COLD / WARM PARITY (`atlas_throughput_002_cold_reuse_parity.json`, quiet tree)

| path | cold | reuse | forced cold | files | byte-identical |
|---|---|---|---|---|---|
| generator (Columbus) | 25.7 s | 7.2 s | 25.5 s | 668 | yes (manifests identical) |
| market bundle (Columbus, production) | 26.4 s | 2.2 s | 39.2 s | 670 | yes |
| whole site (10 markets, production) | 409.8 s | 8.8 s | — | 4,835 | yes |
| whole site preview (fragments reused) | — | 340.9 s | — | — | (different context, different bundle) |

Input mutation invalidates (a changed package byte → miss → the build's own
gate refuses it).

## MARKET PLAN MATRIX

See REGRESSION V2 BEFORE / AFTER above and `atlas_throughput_002_plan_matrix.json`
(per path: CHANGED PATH, OLD CLASS, NEW CLASS, WHY, PROOF RESULT; per
branch: SELECTED SUITES, FULL_REGRESSION_REQUIRED).

## PERFORMANCE (`atlas_throughput_002_performance.json`)

| | OLD BROAD PATH (001 baseline) | NEW MARKET_LOCAL PATH (Nashville replay) |
|---|---|---|
| what runs | every test under `tests/` | 19 modules: the zone's own suite, the 16 per-market contract modules, reverse dependents |
| classification | — | 11.3 s, FULL = NO, assembly not required |
| wall | 7,955 s | 317.7 s (320.7 s with pytest start-up) |
| collection | 50.2 s | 3.7 s |
| selected tests | 17,408 | 1,237 |
| assembly executions | 56 outer calls, 1,882 s | 2 (two fail-closed contract probes, 1.4–1.6 s, no site generated) |
| unique input keys | 19 | 2 |
| reuse hits | 0 | 0 (nothing to reuse) |
| peak working set | 7,538 MB | 127 MB |
| demo-media / website-generation selected | yes | no |
| failures not in the f75aa95 baseline | 2 (closed in 001) | 3 — two replay artifacts (the Nashville suite pins its own branch's production truth and inventory) and one real defect in this order's synthetic deletion case, fixed at cause before the audit |

Ratio: 25× less wall time, 14× fewer tests, 59× less memory — for a change
the classifier previously charged the full suite. Not a like-for-like
comparison of coverage: the market-local path deliberately runs the
market's own gates plus the contract rows; the broad suite remains the
proof for every shared change.

## MIGRATION AUDIT

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

## SAFETY FREEZE

- The six mandatory-full rows (AUTHORITY, GENERIC_RUNTIME, SCHEMA,
  ROUTING_SEMANTIC, DEPLOYMENT, UNCLASSIFIED) and the TEST_EXPECTATION /
  BOOKKEEPING rows are byte-identical to the V2-001 matrix at 0a623a0
  (`TestProductionSafetyFreeze`).
- `classify_path` is unchanged for every tracked runtime, deploy and
  authority file (`test_no_safe_classification_can_be_reached_from_a_runtime_or_authority_path`
  still passes); a promotion (registry, package, contract, participation,
  record) still costs assembly and the full suite; a mixed change is decided
  by its strictest file.
- Only SHADOW zones can narrow: condition 5 fails the moment a market is
  registered (Toledo 002/003 measured), and `production_runtime_included`
  must be NO. 002 claims NOTHING about data-only promotions; that is 003.

## 003 REQUIRED SAFETY INPUTS

Recorded unchanged in `atlas_throughput_002_003_input_packet.md`: H2 no
first-party binding gate; H9 determinism skipped by default; H7 route
preservation Columbus-only; H12 rollback market set unchecked; H13 paid
call sites bypass the ledgers; H3 `validate_record` not a build gate; H1
identity_key canonicality for 3–8 markets only. Plus two 002 findings:
root-level shadow artifacts fail reachability (put them under
`markets/reports/`), and the shared OSM registry row needs its own
structured narrowing.

## GIT

Commits on `worker/atlas-throughput-001` after the 001 head 0a623a0, all pushed:

1. `d7f733f` -- ATLAS-THROUGHPUT-002 scope market-local validation and reuse assemblies (registry, proof, classifier class + blockers + rename handling, lane, demo-media fixture, session cache + hooks, profiler accounting, 72 targeted tests, pre-audit reports).
2. `0e73517` -- the reachability scan ignores the classifier's own self-tests; parity re-measured in a quiet tree.
3. `0add645` -- the 001 self-test excluded too.
4. `74152bd` -- the proof's git reads use REPO_ROOT at call time (found by the replay run); performance report.
5. the closure commit (branch tip at push) -- migration audit report, assembly-reuse report, the closure artifact, this FINAL, docs.

Regression proof: targeted suites green (test_atlas_throughput_002 72, test_regression_delta_001, test_factory_throughput_001, test_atlas_throughput_001, contracts, sharding); ONE migration audit (17,480 collected, PRE_EXISTING 160 = f75aa95 exactly, 1 TRUE_NEW closed by node id through Regression V2's delta validation, no second audit); `origin == HEAD`; tree clean. Committed content: engineering, tests, reports, docs. No market authority, no shared production state, no deployment.

---

## THE NINE ANSWERS

1. **DOES A PROVEN NASHVILLE-STYLE MARKET-LOCAL BUILD STILL REQUIRE FULL BROAD REGRESSION?** NO — provided every artifact stays inside the zone (the replayed Nashville change set without its root-level OSM extract classified FULL = NO and ran in 318 s). The real Nashville branch as committed still says YES for that ONE root-level file, by evidence.
2. **DOES A PROVEN CHATTANOOGA-STYLE MARKET-LOCAL BUILD STILL REQUIRE FULL BROAD REGRESSION?** NO for every helper and proposed artifact (11 of 11 pass); the committed branch still says YES for its one edit to the shared `discovery/config/osm_extracts.json`, which is not market-local and stays ROUTING_SEMANTIC_CHANGE.
3. **HOW LONG DOES THE NEW REPRESENTATIVE MARKET-LOCAL VALIDATION TAKE?** 11 s to classify + 318 s to run (1,237 tests, 19 modules, 127 MB peak) versus 7,955 s for the broad path it replaces.
4. **HOW MANY IDENTICAL ASSEMBLY EXECUTIONS REMAIN?** Within the audit, only the executions that a test explicitly claims as cold: prod004 determinism (2 generator builds), prod005 atomic replace (2 bundle builds with their generators), and the two demo-media determinism chains. Every other identical request was a REUSE_HIT (27 hits over 33 builds: the second whole-site compose, 20 of 30 market fragments, 6 Columbus generator and 2 Columbus bundle requests). The preview compose remains a distinct key (a different bundle) whose fragments reuse but whose composition rebuilds.
5. **HOW MUCH ASSEMBLY WALL TIME WAS REMOVED?** 746 s of assembly avoided by the cache inside the audit (1,073 s attributed through the wrapped calls, fragments included); assembly seconds by kind fell from 1,882 s to 1,529 s, and the whole-site compose from two builds (628 s) to one build plus a 7 s copy. Together with the demo-media consumer-reuse fixture (5,630 s -> 1,494 s) the broad run fell from 7,955 s to 3,815 s (-52 %), while a proven market-local change no longer owes it at all (318 s).
6. **IS DEMO-MEDIA STILL FULLY AVAILABLE IN THE BROAD/AUDIT PATH?** YES — 18 tests, unchanged claims, inside every `full_regression` and in its own `website_generation_integration` lane; it ran in the migration audit.
7. **WAS PRODUCTION PROMOTION VALIDATION WEAKENED?** NO — the mandatory-full rows are byte-identical to V2-001, `classify_path` is unchanged for every runtime/authority/deployment file, and only unregistered SHADOW zones can narrow.
8. **MIGRATION AUDIT TRUE_NEW_FAILURE =** 0 after the one node-id closure (1 at first run: a source-inspection test that followed the generator split; TEST_EXPECTATION_CHANGE, closed in 25 s; PRE_EXISTING 160 = the f75aa95 set exactly).
9. **IS ATLAS-THROUGHPUT-003 READY TO BUILD THE CRITICAL FAST RELEASE LANE?** YES — the zone model, the proof, the lane, the cache and the profiler accounting are in place and measured; the seven safety gaps are recorded unchanged as 003's inputs.

STOP. 003 not started; no market authority changed; nothing promoted or deployed.
