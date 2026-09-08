# ATLAS-THROUGHPUT-004 — FINAL REPORT

Persistent content-addressed market-bundle cache. Worktree `C:\Atlas-Throughput-V1`, branch
`worker/atlas-throughput-001`, continued from the pushed 003 head `9a4fe55`. Engineering only: production
authority changed = 0, nothing promoted, nothing deployed, no paid provider call, no browser research.

## PRECHECK

- Worktree `C:\Atlas-Throughput-V1`, branch `worker/atlas-throughput-001`, HEAD at start
  `9a4fe558331fe0ee9e24ebd0b5598127a8ef312d` == `origin/worker/atlas-throughput-001`, tree clean.
- 001 TRUE_NEW = 0 (`failure_closures/atlas-throughput-001-1.json`), 002 TRUE_NEW = 0 (`-002-1.json`), 003 TRUE_NEW = 0
  (`-003-1.json`: three nodes CLOSED, PRE_EXISTING 160 = the f75aa95 set).
- Read: the 001 safety map and release model, the 002 and 003 reports, the 003 → 004 input packet, and the owning
  implementations: `sealed_market_package.py` (package + digest), `market_package_writer.py`, `fast_release_lane.py`
  (receipt, rules A–O), `package_staging.py` (the staged market builder), `assemble_netlify_bundle.py` (the per-market
  assembler and its bundle manifest: `deployment_manifest.json`, `file_hash_manifest.json`, `route_inventory.json`,
  `validation_report.json`, `site/`), `assemble_production_site.py` (the whole-site composer: `build_global_home`,
  `build_global_hotel_index`, `build_global_sitemap`, robots, control files, `file_hashes`/`bundle_digest`),
  `assembly_session_cache.py` (002: `session_key`, `input_fingerprint`, `tree_fingerprint`, `INPUT_ROOTS`,
  `reuse_or_build`, `cold()`), `generate_pettripfinder_columbus_site.py` + `generate_pettripfinder_pilot.py`
  (`load_launch_package`, `LAUNCH_PACKAGE_DIR`, `date.today()` → `compute_inventory_readiness`), `release_contracts.py`,
  `deployment_authorization.py`, `requirements.txt` / `requirements-dev.txt` (the only lockfiles; Python 3.13.5,
  no Node toolchain), `site_pages.py` (the literal copyright year), `evidence_revocations.json` and the 365-day
  freshness rule in the lane. No parallel build system was invented: the cache wraps `package_staging.build_changed_market`.

## 003 INPUT PACKET

`atlas_throughput_003_004_input_packet.md`: build on the package digest, the dependency digest, the receipts, the
staged input digest, the byte-deterministic changed-market bundle and the session cache's verify-on-hit; take the
measurements first (cross-process cold vs hit, the declared closure's size and churn, staged digest → bundle digest).

## SEVEN CROSS-RUN OBSTACLES (verbatim from the 003 packet, and what 004 did with each)

1. **The bundle digest depends on more than the package.** The staged tree carries every registered market's
   registry entry, the shared control files, `identity_resolutions.json`, the four shared contract sections; 002's
   session key fingerprints 2,000+ files. → 004 MEASURED the closure by tracing two real builds (43 shared data
   files + the market's affiliate shard + 177 repository modules; `bundle_cache_closure.json`) and keys on exactly
   those plus the staged tree; a build that reads outside it is never trusted.
2. **The generator reads module state, not only files.** → the key hashes the SOURCE of every module the build
   loads (the shared-runtime digest) plus the builder/assembler sources; `module_state_signature` stays 002's.
3. **`release_name` and `generated_from_commit` carry the build's commit.** → both live in `deployment_manifest.json`
   outside `site/`; the artifact identity is `bundle_digest(file_hashes(site/))`, which the pilot proved
   commit-independent (Dayton `6340911b…` reproduced byte-for-byte today from the same package).
4. **The whole-site compose is not keyed per market.** → out of 004's scope by design; the composed identity
   `f(sorted bundle digests, control files, participation sha, assembler digest)` is item 1 of the 005 packet.
5. **Nothing survives the process.** → `data/bundle_cache/` with immutable objects, index rows, receipts, locks,
   quarantine; proven across processes with builds forbidden.
6. **Receipts expire on live movement.** → the bundle receipt carries no live state (artifact identity only); the
   package receipt (003) keeps its live-deploy expiry; 005 joins them. Evidence revocation and expiry are checked
   on every lookup.
7. **Only Dayton currently seals.** → 004 corrected two over-readings in the writer (retired routing rows outside
   the census are history, not dangling references; dash-spelled artifact hashes are the same digests), so
   Cleveland seals too; the third pilot market is a labelled fixture clone.

## CACHEABLE UNIT

ONE VALIDATED MARKET BUNDLE: sealed package (by digest) + declared build dependencies (the measured closure) +
builder version + shared runtime/template/asset inputs + toolchain identity + build options = BUILD_INPUT_KEY →
bundle bytes (`site/`) + OUTPUT_BUNDLE_DIGEST (the deployer's formula) + bundle validation receipt. The output
digest is not an input; the validation policy version is outside the byte key (`atlas_throughput_004_cache_contract.*`).

## INPUT MANIFEST

`bundle_cache.build_input_manifest` (`atlas_throughput_004_input_manifest.*`): PACKAGE_DIGEST, MARKET_ID,
AUTHORITY / ROUTE / POLICY / EVIDENCE MANIFEST / GEOGRAPHY-IDENTITY / MARKET CONFIG / partition digests, RENDER
INPUT DIGEST (the staged tree), BUILDER and ASSEMBLER DIGESTS, SHARED RUNTIME DEPENDENCY DIGEST (177 modules),
TEMPLATE / ASSET / SHARED DATA DIGESTS (43 files + the affiliate shard), declared-closure digest, TOOLCHAIN (Python
3.13.5, platform, both requirement files, installed versions of every declared package; Node not applicable),
BUILD ARGUMENTS, LOCALE, PTF_* ENV, VALIDATION POLICY VERSION, fast-lane version, contract versions, builder
version. Canonical: sorted keys, no whitespace, POSIX repo-relative paths, sorted collections, explicit null,
no timestamps, no absolute paths. Coverage rule: undeclared read ⇒ UNTRUSTED (fail closed), never a widened key.

## CACHE STORAGE

`data/bundle_cache/` (gitignored; `PTF_BUNDLE_CACHE_ROOT`): `objects/<bundle sha>.zip` (deterministic archive,
never overwritten under its digest), `index/<key>.json` (one row per key: key, market, package digest, output
digest, object path, archive sha/bytes, byte size, file count, receipt digest, policy version, dependency digests,
created at/by, trust state, last verified, revocation state, expiry, the manifest), `receipts/<digest>.json`,
`locks/`, `quarantine/`, `tmp/`, `telemetry.jsonl`. No database, no network service.

## TRUST MODEL

TRUSTED only through the publisher after: build succeeded, assembler gates passed, bundle built cold, archive
round-trips to the built digest, no undeclared repository read, determinism proven by a second cold build, no
evidence revoked or expired, receipt written and bound. Anything less is an UNTRUSTED row (recorded, never
served). A planted archive or a hand-written index row is a miss and is quarantined.

## LOOKUP RULE

Requested key == stored key; TRUSTED; archive present, non-empty, recorded size and archive sha; extracted bytes
re-hash to OUTPUT_BUNDLE_DIGEST; receipt present, digest re-derives, binds key + digest + policy + builder /
assembler / runtime / closure / render digests + Python version; policy compatible (older compatible ⇒ REVALIDATE);
no revoked artifact, expiry in the future, entry not revoked. Otherwise a miss; questionable entries are quarantined,
never repaired into a hit.

## INVALIDATION MATRIX

Measured on the pilot cache, every probe in a SEPARATE process with builds forbidden (18/18 match; `atlas_throughput_004_invalidation_matrix.*`):

| case | expected | actual | match |
|---|---|---|---|
| baseline_unchanged | HIT | HIT | True |
| policy_mutation | MISS | MISS | True |
| route_mutation | MISS | MISS | True |
| geography_mutation | MISS | MISS | True |
| shadow_repo_unchanged | HIT | HIT | True |
| template_mutation | MISS | MISS | True |
| builder_mutation | MISS | MISS | True |
| shared_runtime_mutation | MISS | MISS | True |
| market_tooling_only_mutation | HIT | HIT | True |
| lockfile_mutation | MISS | MISS | True |
| validation_policy_version_change_compatible | REVALIDATE | REVALIDATE | True |
| corrupt_artifact | MISS | MISS | True |
| missing_artifact | MISS | MISS | True |
| zero_byte_artifact | MISS | MISS | True |
| missing_receipt | MISS | MISS | True |
| wrong_receipt | MISS | MISS | True |
| malformed_metadata | MISS | MISS | True |
| revoked_entry | MISS | MISS | True |

Policy: market authority / routes / policy / geography / evidence-reference change ⇒ MISS (package and section digests); shared template, shared runtime, builder, lockfile ⇒ MISS for every dependent (the closure is in the key; multi-market: all three miss after one css change); market-tooling-only ⇒ HIT; test-only ⇒ HIT (tests are outside the closure); validation policy change ⇒ REVALIDATE (bytes reused, new receipt, no build) when compatible, INVALID_POLICY_VERSION ⇒ rebuild when not; participation ⇒ HIT (the bundle does not read it; the release manifest changes in 005); revoked entry / revoked or expired evidence ⇒ INVALID_REVOKED ⇒ rebuild, UNTRUSTED while the evidence stays revoked; schema/contract change ⇒ MISS (contract versions and the closure digest are in the key; no compatibility table yet).

## ATOMIC PUBLICATION

Archive to `tmp/`, round-trip check, receipt to `tmp/`, index row to `tmp/`; then rename the archive (only if
absent; a damaged object under the same digest is moved to quarantine), the receipt, and LAST the index row. An
interrupted publication (tested with a crashing `os.replace`) leaves no object, receipt or row; the next request
rebuilds and publishes cleanly. `tmp/` is empty after every publication.

## CONCURRENCY

Two simultaneous same-key requests: statuses ['HIT_AFTER_WAIT', 'MISS'], BUILD_EXECUTED = 1, REUSE_AFTER_WAIT = 1, digests equal True. Two different keys: BUILD_EXECUTED = 2, builds overlapped = True (wall 1.794 s for two 1 s builds). Per-key thread lock + `O_EXCL` lock file (holder pid/run/time), waiter re-verifies the published artifact, stale locks broken; no global lock, no distributed locking (`atlas_throughput_004_concurrency_proof.*`).

## COLD/WARM PROOF

RUN 1 in the pilot process; RUN 2 in a NEW Python process with `PTF_BUNDLE_CACHE_FORBID_BUILD=1` (a miss raises). Receipt re-read and re-bound on every hit; no builder invoked (`atlas_throughput_004_cold_warm_proof.*`).

| market | RUN 1 (cold) | RUN 2 (warm, separate process) |
|---|---|---|
| A_dayton | MISS / BUILD_EXECUTED 2 / TRUSTED_CACHE_PUBLISHED 1 / 20.026 s / BYTE_IDENTICAL | HIT / BUILD_EXECUTED 0 / PERSISTENT_CACHE_HIT 1 / bytes identical True / sha identical True / **3.732 s** (process wall 4.212 s) |
| B_cleveland | MISS / BUILD_EXECUTED 2 / TRUSTED_CACHE_PUBLISHED 1 / 45.892 s / BYTE_IDENTICAL | HIT / BUILD_EXECUTED 0 / PERSISTENT_CACHE_HIT 1 / bytes identical True / sha identical True / **8.355 s** (process wall 8.839 s) |
| C_fixture | MISS / BUILD_EXECUTED 2 / TRUSTED_CACHE_PUBLISHED 1 / 22.982 s / BYTE_IDENTICAL | HIT / BUILD_EXECUTED 0 / PERSISTENT_CACHE_HIT 1 / bytes identical True / sha identical True / **3.882 s** (process wall 4.32 s) |

## MULTI-MARKET REUSE

A = cleveland-akron-canton-oh changed (one fee mutation), B = dayton-oh unchanged, C = fixture-dayton-oh unchanged, after a warm cache: A MISS (2 builder invocations, 95.605 s), B HIT (0, 3.521 s), C HIT (0, 4.688 s); unchanged markets rebuilt: 0; total 103.936 s. Then one shared template changed (approved_hotel_profile.css in the shadow closure): {"A": "MISS", "B": "MISS", "C": "MISS"} — every dependent bundle invalidates, proven with builds forbidden (`atlas_throughput_004_multi_market_reuse.*`).

## GLOBAL DEPENDENCIES

A market bundle embeds no global state: the Dayton bundle (334 files) contains no other market's name, no
totals, no release id, no commit (grep of every HTML file). The registry entries the build reads are consumed
only for ownership validation; they are in the key via the staged tree. The global artifacts belong to the
composer and are classified in the 005 packet: home `index.html`, the global hotel index and `sitemap.xml` are
GLOBAL MUST REGENERATE (membership, counts, routes); `robots.txt`, `_headers`, `_redirects` are GLOBAL
INCREMENTAL; the anchor's shell pages are PER-MARKET CACHEABLE via the anchor bundle; no search index exists.
No product-render refactor was made.

## TIME DEPENDENCIES

The copyright year is a literal in `site_pages.py`. The one wall-clock input, `date.today()`, feeds
`compute_inventory_readiness` (a launch-readiness gate), never the bytes; it is recorded on the bundle receipt as
`reference_date`. Two cold builds minutes apart and the 003 pilot's build hours earlier hash identically.

## PERFORMANCE

`atlas_throughput_004_performance.*`. COLD BUILD TIME dayton 20.026 s / cleveland 45.892 s (+ determinism second build 17.964 / 42.076 s); CACHE PUBLICATION 3.061 / 8.047 s; WARM CACHE LOOKUP (index read + extract + re-hash + receipt) 2.834 / 7.372 s, of which ARTIFACT HASH VERIFICATION 2.818 / 7.357 s; manifest (stage + closure hashing) 0.897 / 0.982 s; WARM TOTAL in-process **3.732 s / 8.355 s** (process wall incl. interpreter start 4.212 / 8.839 s); REVALIDATION-ONLY 3.271 s; BYTES REUSED 1405426 / 2900407; DISK SPACE 4179146 bytes for the pilot cache; PEAK MEMORY 224.9 MB (pilot process); BUILD EXECUTIONS AVOIDED 3. Multi-market simulated release: MARKETS 3, COLD BUILDS 1, CACHE HITS 2, REVALIDATIONS 0, GLOBAL REBUILDS not in scope (005): the whole-site compose, TOTAL 103.936 s. Target < 10 s warm: met (checksum and receipt validation never disabled). Pilot total 371.934 s.

## OBSERVABILITY

Every request appends `{run_id, market_id, build_input_key, cache_status, lookup_seconds / build_seconds /
validation_seconds / verify_seconds, bytes, output_digest, trust_state}` to `bundle_cache.EVENTS` and
`data/bundle_cache/telemetry.jsonl`; statuses MISS, HIT, HIT_AFTER_WAIT, REVALIDATE, INVALID_CORRUPT,
INVALID_REVOKED, INVALID_POLICY_VERSION, BYPASS_COLD_REQUIRED (+ BUILD_FORBIDDEN, UNTRUSTED). The 002 profiler
writes a `bundle_cache` summary row and one `bundle_cache_request` row per event at session end.

## MIGRATION AUDIT

Run: `data/regression/atlas-throughput-004-audit` on the committed 004 change set, clean tree, after the heavy-lane check; every test under `tests/` with the 002 profiler and the session cache ON, classified by NODE ID against `regression_baselines/f75aa95.json` (`atlas_throughput_004_migration_audit.json`). Exactly one broad run.

| measure | 003 audit | 004 audit |
|---|---|---|
| wall | 3,610 s | **3384.807 s** |
| collected / passed / failed / skipped | 17,549 / 17,155 / 163 / 218 | 17589 / 17147 / 211 / 231 |
| against f75aa95 | PRE_EXISTING 160, TRUE_NEW 3 -> closed | PRE_EXISTING 160, EXPECTED_EPOCH 0, FLAKE 0, **TRUE_NEW 51** |
| baseline failures now passing | 0 | 0 |
| session cache | 27 reuse hits, 800 s avoided | 21 reuse hits, 852.0 s avoided |
| demo-media module | 1,390 s | 1397.4 s |
| peak working set | 8,877 MB | 8995.4 MB |

**Root cause.** All 51 read ONE production assembly of 782 profiles instead of 786 (sitemap 939, not 945; html pages 4,789, not 4,815): `bundle_cache._build_and_publish` had frozen the 002 session cache's whole input fingerprint BEFORE the staging overlay was entered, so the dynamic inputs (overlay census dir, PTF_* env, module state) described the committed repository and the staged Dayton WITHDRAWAL render (four pet-friendly records and two corridor routes fewer) was remembered under the committed Dayton key, then served to the production assembly later in the same pytest session. **Fix** (4b84608): `_frozen_tree_fingerprint` freezes only the read-heavy tree walk and reads the dynamic inputs live under the overlay; `TestSessionCacheIsolation` pins it (fails on the previous bytes with the staged generator_site entry carrying the committed census dir). **Closure** by node id through Regression V2 (`failure_closures/atlas-throughput-004-1.json`, fix commit f19d6e0): targeted run 4707 collected / 24 failed (all PRE_EXISTING against f75aa95, TRUE_NEW 0); node ids CLOSED=51; sources: 5 by the lanes, 46 by the ordered replay (`data/regression/atlas-throughput-004-replay/replay.xml` at 4b84608: 355 cases, 355 passed, 0 failed). Every lane defers TestEveryMarketAssembles to the full regression, so V2 gained `--exercised-junit` (017071c): a run the caller made at the fix commit proves ONLY node ids the lanes left NOT_EXERCISED and never overrides a lane result. FULL_REGRESSION_REQUIRED (V2's verdict for the fix) = YES -- recorded, not executed; the order permits one broad run. Ordered one-process replay at the fix commit (`data/regression/atlas-throughput-004-replay`: the 004 module FIRST, then test_global_deployment_architecture_045, test_launch_participation_046, test_per_market_release_contracts -- the audit's order): 355 tests, 0 failed/errored, 1395 s; the production assembly reproduced the pinned candidate.

The 004 change set (the cache, the pilot, the staging changes, the writer corrections, the classifier and lane integration) classifies CLASSIFIER_TEST_INFRA_CHANGE + SHARED_RUNTIME_CHANGE + UNKNOWN_MIXED under Regression V2 and owed exactly this broad run. **Migration audit TRUE_NEW_FAILURE after closure = 0.**

## PRODUCTION ACTIVATION STATUS

PERSISTENT_CACHE_IMPLEMENTED = YES. PERSISTENT_CACHE_VALIDATED = YES. PRODUCTION_RELEASE_CONSUMPTION = **DISABLED**
(`fast_release_activation.json`); the production assembler, generator and deployer do not import the cache
(tested); FAST_PATH_PRODUCTION_ACTIVATION stays DISABLED. A cache hit sets nothing about a release: no entry or
bundle receipt carries an eligibility, authorization or live field; Regression V2 reports
`MARKET_BUILD_REQUIRED = NO` from a trusted bundle while `FULL_REGRESSION_REQUIRED` stays what the FAST-lane
receipt and activation decide.

## 005 INPUT PACKET

`atlas_throughput_004_005_input_packet.md`: the nine inputs 005 consumes (package, bundle, key, both receipts,
current verified live, intended delta, global index, unchanged-bundle reuse, parent digest), the global-artifact
map, and the seven things that still prevent CURRENT LIVE MANIFEST + ONE AUTHORIZED PACKAGE DELTA = ONE FINAL
STAGED CANDIDATE (no per-market compose identity; only two live markets seal; participation is a release input;
two receipt kinds to join; no durable release store for live/rollback bundles; writer-version compatibility for
package receipts; Windows path length).

## GIT

Branch `worker/atlas-throughput-001` in worktree `C:\Atlas-Throughput-V1` (no new worktree), continued from the pushed 003 head `9a4fe55`. Throughput engineering only: no market authority changed, nothing promoted, nothing deployed, no paid call.

| commit | subject |
|---|---|
| `019e3f1` | ATLAS-THROUGHPUT-004 persist validated market bundle cache (the cache, the measured closure, the pilot, the staging/writer/normaliser corrections, the lane and V2 integration, activation flags, 39 tests, the reports, the regenerated test inventory) |
| `e855dc9` | re-export the committed validation matrix with the bundle-cache narrowing blockers |
| `4b84608` | freeze only the session cache's tree walk during a traced bundle build; record the migration audit (the 51 TRUE_NEW root cause + `TestSessionCacheIsolation`) |
| `1fbfd3b` | runbook: the session-cache isolation lesson |
| `017071c` | Regression V2: `validate --exercised-junit` — an exercised run at the fix commit proves the node ids the lanes defer |
| `f19d6e0` | docs: the exercised-run closure option and the migration audit record |
| `d0d3787` | closure: the audit's 51 TRUE_NEW node ids CLOSED (5 by the lanes, 46 by the ordered replay), TRUE_NEW 0 |

This FINAL report is committed on top of `d0d3787` and the branch pushed to `origin/worker/atlas-throughput-001`; origin == HEAD and a clean tree are verified after the push and stated in the delivery message. Untracked run directories under `data/regression/` (`atlas-throughput-004-audit`, `-replay`, `-closure`) and the pilot cache under `C:\ptf004` are measurement artifacts, gitignored, never inputs.


---

1. CAN AN UNCHANGED VALIDATED MARKET BUNDLE NOW BE REUSED ACROSS SEPARATE RUNS? **YES** — cold in one process,
   HIT in a new process with builds forbidden, bytes and digest identical, receipt verified (Dayton, Cleveland,
   the fixture).
2. ON A WARM CACHE HIT, HOW MANY TIMES WAS THE MARKET BUILDER INVOKED? **0** (`builder_invocations = 0`;
   `PTF_BUNDLE_CACHE_FORBID_BUILD=1` would have raised).
3. HOW LONG DID WARM BUNDLE REUSE TAKE INCLUDING INTEGRITY/RECEIPT CHECKS? **3.732 s (Dayton, 334 files) / 8.355 s (Cleveland, 120 profiles) in-process, including extraction, re-hash of every file, receipt digest re-derivation and binding, revocation and freshness; 4.212 / 8.839 s process wall including interpreter start.**
4. DID POLICY/ROUTE/TEMPLATE/BUILDER CHANGES INVALIDATE CORRECTLY? **YES** — every mutation missed (proven
   with builds forbidden); shared runtime and lockfile mutations too.
5. DID A MARKET-TOOLING-ONLY CHANGE PRESERVE THE VALID BUNDLE? **YES** — HIT after mutating an offline helper
   outside the closure.
6. DID CORRUPTED OR INCOMPLETE CACHE DATA FAIL CLOSED? **YES** — flipped, zero-byte and missing artifacts,
   missing / wrong receipts, malformed and mismatched index rows, revoked entries: quarantined, rebuilt, never served.
7. DID TWO CONCURRENT SAME-KEY REQUESTS BUILD ONLY ONCE? **YES** — BUILD_EXECUTED 1, REUSE_AFTER_WAIT 1; different
   keys built concurrently.
8. IN THE MULTI-MARKET TEST, HOW MANY UNCHANGED MARKETS WERE REBUILT? **0** (A rebuilt, B and C hit; after a shared
   template change all three miss).
9. IS CACHE HIT KEPT SEPARATE FROM RELEASE AUTHORIZATION? **YES**.
10. WAS THE CACHE USED FOR LIVE DEPLOYMENT? **NO**.
11. MIGRATION AUDIT TRUE_NEW_FAILURE = **0 (51 found, closed by node id)**
12. IS ATLAS-THROUGHPUT-005 READY? **YES** — the input packet is complete and measured; 005 is not started.

STOP. 005 not started. No market promoted. Nothing deployed.
