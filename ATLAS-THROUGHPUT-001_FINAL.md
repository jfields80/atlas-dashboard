# ATLAS-THROUGHPUT-001 — FINAL

Baseline, instrumentation and success-criteria freeze for the factory
throughput redesign. **This order measured. It changed no market authority,
no pin, no participation, no promotion state, no deployment record, no
provider ledger and no safety guard; it acquired no evidence, ran no browser,
deployed nothing, promoted nothing, spent $0 and 0 credits.**

Full report: `atlas-dashboard/launch_packages/pettripfinder/reports/atlas_throughput_001_baseline_report.md`.

---

## PRECHECK

| item | value |
|---|---|
| worktree | `C:\Atlas-Throughput-V1` |
| branch | `worker/atlas-throughput-001` |
| HEAD at start | `2163c4ed23b7315954f896c99729ca95c08eabfc` (clean) |
| upstream | was `origin/worker/ptf-hardened-lineage-consolidation-008` (inherited); set to `origin/worker/atlas-throughput-001` at push |
| owning modules | `scripts/pettripfinder/regression_delta.py` (Regression V2), `regression_lanes.py` (lanes, runner, baselines, classifier), `regression_inventory.py`, `assemble_netlify_bundle.py`, `assemble_production_site.py`, `generate_pettripfinder_columbus_site.py`, `release_contracts.py`, `launch_participation.py`, `deployment_authorization.py`, `global_deployment.py`, `tests/pettripfinder/{market_state,epochs}.py` + `pins/`, `tests/pettripfinder/test_per_market_release_contracts.py:818` (TestEveryMarketAssembles) |

## CURRENT RELEASE MODEL

29 representations of release truth (`atlas_throughput_001_release_model.md`).
The release identity is `bundle_sha256 = bundle_digest(file_hashes(site/))`,
bound manifest → authorization → record → `deployment_state.live`. The
published pet-friendly count is stored in ≥ 12 places, `bundle_sha256` in 8,
`source_commit` in 8; three divergent partition-filename tables; two
definitions of `resolved`; no repo script writes the global manifest, an
authorization or a record (all in-session).

## REGRESSION V2

Path-prefix rules, strictest row wins, UNCLASSIFIED = full. Six mandatory-full
classes, four narrow, one conditional. Every real market branch (Nashville,
Toledo 001, Toledo 002/003, Lexington, Chattanooga) classifies
FULL_REGRESSION_REQUIRED = YES; for the four shadow-market orders the drivers
are `prefix:scripts/pettripfinder/` on `<market>_*.py` helpers (18 / 15 / 15 / 8
of the drivers), `prefix:…/discovery/` on `discovery/config/<market>.json`,
`prefix:…/identity_census` matching `identity_census_proposed/`, and
`markets/proposed/*.json` + `*_osm_extracts_*.json` being UNCLASSIFIED.
Rename/deletion/new-file/conftest/schema/test-infra/unknown behaviour
documented in report §3; Regression V2 not modified.

## TEST INVENTORY

17,408 collected at this tree (13,802 functions, 4,146 parametrized items,
600 files), written by the plugin at collection
(`atlas_throughput_001_inventory_summary.json`). By analytical category:
OTHER_NON_PTF 6,756 · CORE_SHARED 4,085 · MARKET_LOCAL 2,195 · HISTORY 2,161 ·
ASSEMBLY 933 · FAST_CONTRACT 695 · DEPLOYMENT 327 · OTHER 256.

## ASSEMBLY CALL GRAPH

`atlas_throughput_001_assembly_duplication.md`. TestEveryMarketAssembles
builds all 11 contract markets once per run (module fixture) and is the only
per-record render proof for 8 of them. The 10-market site is composed three
times per broad run from identical inputs (045 fixture, 045 preview test, 046
fixture); Columbus is generated 15 times; 52 full generations per run. No
session fixtures, no xdist, no test subprocess except `git`.

## BASELINE PROFILE

Eleven kept broad runs profiled from junit (`atlas_throughput_001_broad_run_profiles.json`)
plus ONE solitary instrumented run (pid 28920, 17:23–19:37, after waiting
for the Chattanooga lane 15:14–17:14):

| | instrumented run | range of the 10 lane-runner runs |
|---|---|---|
| wall | 7,955 s (2 h 13 min) | 5,607–7,476 s |
| collection | 50 s | 26–68 s |
| demo-media suite | 5,630 s (71 %) | 3,489–4,440 s (57–66 %) |
| 045 + 046 + release_contracts | 1,307 s | 1,096–2,483 s |
| assembly outer calls | 56 calls, 1,882 s | — |
| passed / failed / skipped / xfail | 17,015 / 162 / 218 / 13 | — |

## MEMORY PROFILE

Pytest working set ~470 MB through the entire PetTripFinder tree (every
assembly included), then 6.4–7.6 GB for the website-generation demo-media
suite: peak 7,538 MB in-process (plugin), 7,417 MB process tree (sampler),
system free memory minimum 46 MB on a 16 GB machine, in both the Chattanooga
run and the instrumented run. CPU 5,803 s of 7,955 s wall; 9.4 GB read.

## FAILURE BASELINE

160 nodes (f75aa95), reproduced by node id: 150 ENVIRONMENT (closed-order
suites over gitignored `data/` corpora absent in a fresh worktree), 10
HISTORICAL_COUNT/PIN, **0 identity / policy / artifact / release critical**.
Nothing waived (`atlas_throughput_001_failure_baseline_audit.json`).

## MARKET-LOCAL CASE STUDY

Nashville 001: 45 files, 18 helpers importing only three pure shared
functions, writing only `markets/proposed/`, `identity_census_proposed/`,
`markets/reports/`; unreachable by the runtime, the assembler (unregistered
market) and shared contracts. Regression V2 demands a full run because the
path prefix `scripts/pettripfinder/` is GENERIC_RUNTIME_CHANGE. Isolation is
provable: namespace + import scan + write-root scan + reverse-import scan +
unregistered market (report §10).

## CRITICAL SAFETY INVARIANTS

`atlas_throughput_001_safety_invariants.md`: 13 hazards mapped to their
minimum current gate, cost and scope. Only five facts need all-market
rendering. No build/deploy gate exists for first-party policy binding (H2),
determinism is skipped by default (H9), route preservation is Columbus-only
(H7), the rollback target's market set is unchecked (H12), every paid call
site bypasses the ledgers (H13).

## BOTTLENECK RANKING

A (measured): A1 demo-media suite in the market lane (57–71 % of wall, the 7 GB
plateau, the contention); A2 three identical all-market composes (900–1,360 s);
A3 Columbus ×15 (~420 s); A4 path-prefix classification forcing a broad run
per shadow-market order; A5 four broad runs per launch (Toledo: 437 min);
A6 contention (102.5 min vs 47.5 min). B (indicated): git subprocess per
assembly, ≥12 copies of each count, founder active time unmeasured.
C (speculative): xdist, collection.

## FROZEN SUCCESS CRITERIA

`atlas_throughput_001_success_criteria.json` — 14 targets, all
TARGET_NOT_CLAIMED, with current evidence and instrument.

## THREE-MARKET EXPERIMENT

`atlas_throughput_001_three_market_experiment.json` — DEFINED_NOT_EXECUTED:
size bands, independence proof, per-band minimum PF / resolved thresholds,
unresolved behaviour, founder-queue disclosure, and the measurement of every
interval the order names.

## ARTIFACTS

Under `atlas-dashboard/launch_packages/pettripfinder/reports/`: baseline
report, broad-run profiles, instrumented baseline, inventory summary, two
sampler summaries, classifier audit, failure-baseline audit, release model,
assembly duplication, safety invariants, success criteria, three-market
experiment, 002 input packet. Tools: `scripts/pettripfinder/throughput_profile.py`,
`scripts/pettripfinder/throughput_baseline.py`; tests
`tests/pettripfinder/test_atlas_throughput_001.py` (28); runbook section
"Profiling a run"; order text `docs/work_items/ATLAS-THROUGHPUT-001.md`.

## GIT

Two commits on `worker/atlas-throughput-001` over base `2163c4e`:

1. `463438537c75cfee71f127a1b6600de68b88446e` — "ATLAS-THROUGHPUT-001 baseline
   and instrumentation": the plugin, the analysis CLI, 28 targeted tests, the
   regenerated test-pin inventory, the runbook section, the order text, the
   thirteen `atlas_throughput_001_*` reports and this FINAL.
2. the closure commit (branch tip at push) — the durable closure artifact
   `failure_closures/atlas-throughput-001-1.json`, report §18 and this section.

Regression proof: ONE instrumented broad run (17,408 collected, 160
PRE_EXISTING = the f75aa95 set exactly, 2 TRUE_NEW both instrumentation /
dirty-worktree artifacts fixed at cause), then Regression V2's delta-scoped
validation over the classifier's plan (4,552 collected, 24 PRE_EXISTING,
**0 TRUE_NEW**, both nodes **CLOSED** by node id). No second broad run.
Pushed to `origin/worker/atlas-throughput-001` with the upstream corrected
from the inherited `origin/worker/ptf-hardened-lineage-consolidation-008`;
origin == HEAD; tree clean. Committed content: instrumentation, analytical
tooling, baseline reports, proof criteria, 002 planning. No market
authority, no shared production semantic change.

---

## THE SEVEN ANSWERS

**1. WHAT IS THE SINGLE BIGGEST MEASURED SOURCE OF ATLAS RELEASE DELAY?**
`tests/website_generation/integration/test_pettripfinder_demo_media.py` —
a website-generation integration suite, not a market test — costs 3,489–5,630 s
of every lane-runner broad run (57–71 %), rebuilding one committed launch
package twelve times and holding 6.4–7.6 GB for over an hour. The committed
baselines deselect it; the `full_regression` lane does not. Second: the three
identical all-market composes (900–1,360 s).

**2. HOW MANY IDENTICAL/UNCHANGED ASSEMBLY BUILDS OCCURRED IN THE BASELINE?**
Among PetTripFinder assemblies: 1 repeated whole-site production compose, the
preview compose's 10 identical fragments, 4 repeated Columbus bundles and 3–4
repeated Columbus generator runs (37 repeats by input key over 19 unique
keys). Plus 10 repeated demo-media real-chain builds of one input.

**3. HOW MUCH WALL TIME DID THEY COST?**
≈ 710 s for the PetTripFinder repeats (38 % of 1,882 s of assembly) and
≈ 3,800 s for the demo-media repeats: ≈ 4,500 s ≈ 75 min of the 133-min run.
A repeat costs the full build; nothing is cached.

**4. WHY DID A MARKET-LOCAL HELPER REQUIRE BROAD REGRESSION?**
Because `regression_delta.PATH_RULES` classifies by path prefix and
`prefix:scripts/pettripfinder/` → GENERIC_RUNTIME_CHANGE is a mandatory-full
row; `nashville_tn_routing_001.py` additionally matches `*routing*.py`
(ROUTING_SEMANTIC_CHANGE). The classifier has no notion of a market
namespace, imports or write roots.

**5. IS THAT CLASSIFICATION PROVABLY TOO BROAD?  YES.**
The helpers import three pure shared functions and stdlib, write only into
the market's own proposed/report paths, are imported by nothing outside the
namespace, and describe an unregistered market the assembler cannot select.
The five-condition proof in report §10 is mechanical and would have admitted
Nashville 001, Toledo 001, Lexington and Chattanooga while still refusing
Toledo 002/003 (which edits shared tables).

**6. WHAT EXACT WORK SHOULD ATLAS-THROUGHPUT-002 IMPLEMENT FIRST?**
(1) Move the demo-media suite out of the market `full_regression` lane so the
lane equals the committed baseline's definition (saves ~60 min and ~7 GB per
broad run); (2) an input-hashed session cache for the whole-site compose and
the Columbus bundle, keyed on the plugin's `dependency_input_hash` /
`market_input_hash`; (3) the ownership manifest and a MARKET_LOCAL class
admitted only on the import / write-root / reverse-import proof. Details:
`atlas_throughput_001_002_input_packet.md`.

**7. IS THE 7-DAY THROUGHPUT REDESIGN STILL TECHNICALLY PLAUSIBLE?  YES.**
The measured delay is concentrated in three mechanical causes (one misplaced
suite, three identical composes, one over-broad path rule), each removable
without weakening a gate; acquisition itself already runs at 125–300 minutes
per market. What is NOT yet measured — founder active time and true
concurrency — is the residual risk to the 3-launches-per-day proof.

STOP. 002 was not begun; no production authority was modified; nothing was
deployed; exactly one broad regression was launched.
