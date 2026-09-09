# ATLAS-THROUGHPUT-007 — FINAL REPORT

Bounded historical semantics and legacy regression debt cleanup. Worktree `C:\Atlas-Throughput-V1`, branch
`worker/atlas-throughput-001`, continued from the pushed 006 head `e9d6baf`. Test engineering only: no market
authority changed, no participation changed, nothing promoted, nothing deployed, no paid provider call.

## PRECHECK

- Worktree `C:\Atlas-Throughput-V1`, branch `worker/atlas-throughput-001`, HEAD at start
  `e9d6bafe1a54206162d48545da6b03abcf12d703` == `origin/worker/atlas-throughput-001`, tree clean.
- Every prior order ends at TRUE_NEW = 0: 001, 002 and 003 through committed V2 node-id closures, 004 through
  its 51-node closure, 005 and 006 with no true-new failure at all (their audits classified 160 PRE_EXISTING
  and 0 TRUE_NEW).
- Read before editing: the demo-media module and its fixtures, the real engine chain it drives, the session
  and persistent caches, Regression V2 and the lane runner, `epochs.py` and `market_state.py`, the pins, the
  f75aa95 baseline, the 006 signature normalizer, the shard manifest and the completeness reporter.

## 006 INPUT

Four items: split or shrink the demo-media module, retire the count pins that break on every application
order, give the baseline failures signatures rather than bare node ids, and quarantine with a stated reason
rather than silence. All four were addressed; the fourth needed nothing, for the reason below.

## DEMO-MEDIA SAFETY CLAIMS

Ten claims, each mapped to its owner, input, expensive setup, assertion and the defect it would catch
(`atlas_throughput_007_demo_media_claims.*`). **Zero were removed.** Two were added, both guarding the
redesign itself: that the determinism pair really is two independent executions, and that a zero-image site is
complete rather than truncated.

## DEMO-MEDIA PROFILE

Measured from the 006 audit's profiler output, not inferred from a pytest percentage.

| test | seconds | what it was |
|---|---|---|
| `TestDeterminism` | 530.8 | two cold builds |
| fixture setup | 280.9 | one cold build |
| `test_no_filesystem_path_in_dataset` | 262.1 | **a second identical build** |
| `TestZeroImageFallback` | 257.2 | one no-media build |
| everything else (14 tests) | 18.7 | assertions and one materialization |

**Five full real-chain builds at about 265 s each.** 001 found nine, 002 cut it to five, and 006 measured what
remained: 1,349.7 s, 38% of the broad suite.

## DEMO-MEDIA REDESIGN

One redundant build removed, and it was the only one that was redundant. The test asserting that the dataset
carries no filesystem path was building a second identical chain to inspect an artifact the module had already
built. It now reads the shared chain and checks strictly **more** — the fixture's own temp root is a filesystem
path that must not have leaked in either, which the private build could never have caught, because it was
inspecting a tree it had just created for itself.

The claims needing their own execution moved into their own modules and kept their builds: determinism keeps
two independent cold chains, and the zero-image fallback keeps its own because its input genuinely differs.
One shared chain helper means three modules assert against one implementation rather than three copies.

Splitting only helps when the modules do not each rebuild the same fixture. These three build different
things, so the split lowered the floor without duplicating work.

## OLD VS NEW DEMO-MEDIA TIME

| measure | before | after |
|---|---|---|
| modules | 1 | 3 |
| tests | 18 | 20 |
| full real-chain builds | 5 | 4 |
| aggregate seconds | 1,349.7 | **1,133.4** (−16%) |
| slowest module (the shard floor) | 1,349.7 | **558.2** (−59%) |
| safety claims | 8 | 10 (2 added, 0 removed) |

The preferred 600 s target is met at 558.2 s. The strong 450 s target is **not met and cannot be** at module
granularity: the determinism claim needs two real executions at about 265 s each, and comparing a build
against itself proves nothing. That is an indivisible floor, reported rather than engineered around.

## HISTORICAL INVARIANT MODEL

The four classes, with their existing owners — no competing terminology was created.

| class | means | owner |
|---|---|---|
| CURRENT_STATE_INVARIANT | what the market publishes today | `market_state.current()` / `live()` over the reviewed pins |
| HISTORICAL_COHORT_INVARIANT | these NAMED identities existed at epoch X | `epochs.cohort`, `by_identity_keys`, `assert_cohort_size` |
| HISTORICAL_ARTIFACT_INVARIANT | release R contained these exact bytes | the committed digests in deployment records and authorizations |
| DEPLOYMENT_EPOCH_INVARIANT | deployment R had these market counts | `deployment_state.json` via `market_state.live()` |

## COUNT PIN MIGRATION

**The main finding is that the high-value migration was already done.** The deployment-architecture module
derives every release count from the reviewed pins, and the Louisville suite already reads `market_state` and
`epochs` cohorts. Tests now record both facts so a later order does not "fix" them.

Two genuinely naive current-state pins were migrated, both in `test_identity_routing.py`:

| was | now | why |
|---|---|---|
| `len(pkg["hotels"]) == 88` | `== market_state.current("columbus-oh").profiles` | the claim is that ROUTING does not change the published count, not that Columbus publishes 88 |
| `len(hotels) == 89` | the seed CSV's Columbus hotel rows must equal its authority shard's, by count AND by name | the claim is that routing contributes nothing to seed inventory; the name check is strictly stronger |

Deliberately **not** migrated: the per-market route counts in the same module (Columbus 20, Cleveland 37,
Dayton 9, Cincinnati 51). Each carries a documented ledger of every order that moved it. That history is worth
more than the noise it costs, and rewriting it would be exactly the "replace an old hardcoded count with
today's hardcoded count" error the order forbids.

Cohort safety is proved directly: adding valid hotels leaves a named cohort unchanged; deleting a member
fails; substituting a wrong identity fails; and so does a compensating swap that keeps the total identical and
that a bare count therefore cannot see.

## FAILURE SIGNATURE BASELINE

All 160 baselined nodes now carry a normalized signature plus category, domain, environment, reason, recording
provenance and a review date. Normalization removes addresses, absolute paths, temp directories, timestamps
and run ids and preserves the semantic identity, so a signature survives a different machine but not a
different defect.

| case | verdict |
|---|---|
| same node, same signature | PRE_EXISTING |
| same node, different signature | **TRUE_NEW** |
| different node | TRUE_NEW unless separately baselined |
| baselined node not failing | BASELINE_NOW_PASSING — reported, never erased |
| no messages supplied | node-id classification, exactly as before 007 |

Both `regression_delta` and `regression_lanes` honour them and both stay backward compatible, so every
earlier run's verdict still means what it meant.

Provenance stated plainly: the signatures were captured from the 006 audit, not from the f75aa95 commit. That
run failed on exactly these 160 node ids, so they record how each fails today, which is what a future run must
match.

## LEGACY FAILURE TRIAGE

All 160 are in the baseline, none is outside it, and none has started passing.

| group | count |
|---|---|
| LEGACY_EXPECTATION | 74 |
| ENVIRONMENT | 39 |
| HISTORICAL_COUNT_PIN | 29 |
| TEST_INFRA | 11 |
| UNKNOWN | 7 |

**Was a critical defect hiding here?** No. Every node whose id mentions identity, policy, artifact, release,
authorization, deployment or bundle is a HISTORICAL suite asserting what its own closed order left true. The
modern critical lane — 003's FAST rules A–O, 004's bundle validation receipts, 005's release coordinator and
006's artifact handoff — appears nowhere in the baseline.

**Fixed in 007: zero.** Deliberately. The order forbids eliminating the 160, and each is already suppressed
correctly by node id. What changed is that they can no longer drift.

## QUARANTINE POLICY

**Quarantined in 007: zero**, because none needed it. A baselined node with a signature is a stronger record
than a quarantine: it still runs, still reports, and a change in how it fails is caught. The policy exists for
the case that does arise — required fields, never a silent skip, never reclassifying UNKNOWN as
environment-only to reduce a count, and an expired quarantine fails the run rather than lapsing quietly. The
mechanism is the completeness contract's explicit exclusions, which count a quarantined node against the
planned set so it is accounted for rather than missing.

## SHARD REBALANCE

| measure | before 007 | after 007 |
|---|---|---|
| projected remote wall (slowest shard) | 1,349.7 s | **847.2 s** |
| aggregate runner time | 3,621.7 s | 3,388.9 s |
| the module that sets the floor | demo-media, 1,375.7 s | 045, 770.9 s |
| shard spread | 1,375.7 / 750.0 / 748.0 / 748.0 | 847.2 / 847.2 / 847.2 / 847.2 |

Regenerated from the 007 audit's own full-suite profiler run, not a projection.

The plan is now **work-bound rather than bottleneck-bound**: the slowest module sits below the balanced share,
so the four shards are within a tenth of a second of each other. The bottleneck moved rather than vanished —
the next 007-style question is whether the deployment-architecture module's claims separate the same way.

## DATA-ONLY POLICY CHECK

Unchanged and re-verified: an ordinary proven data-only release requests **0** remote broad jobs, dispatch
NONE, recorded as NOT_REQUIRED_BY_POLICY. Shared runtime, schema, assembler, deployment and unknown changes
still select all four shards, and a mixed change still falls broad. 007 did not narrow its own validation
scope: the test-infrastructure surface it changed remains conservatively broad.

## MIGRATION AUDIT

Run: `data/regression/atlas-throughput-007-audit` on the committed 007 change set, clean tree, after the heavy-lane check; every test under `tests/` with the 002 profiler and the session cache ON, classified by NODE ID against `regression_baselines/f75aa95.json` (`atlas_throughput_007_migration_audit.json`). Exactly one broad run.

| measure | 006 audit | 007 audit |
|---|---|---|
| wall | 3,674.5 s | **3,439.2 s** (−235.3 s) |
| collected / passed / failed / skipped | 17,699 / 17,308 / 160 / 231 | 17,721 / 17,330 / 160 / 231 |
| against f75aa95 | PRE_EXISTING 160, TRUE_NEW 0 | PRE_EXISTING 160, EXPECTED_EPOCH 0, FLAKE 0, **TRUE_NEW 0** |
| baseline failures now passing | 0 | 0 |
| session cache | 27 reuse hits, 1,043.2 s avoided | 27 reuse hits, 1,071.5 s avoided |
| demo-media, all modules | 1,349.7 s (one module) | **1,083.8 s** (three: 534.0 + 290.7 + 259.1) |
| peak working set | 8,802 MB | 8,636 MB |

The suite grew by 22 collected tests and the failure set did not move: the same 160 node ids, and now each is
matched on its signature as well.

No TRUE_NEW failure: every failing node id is in the f75aa95 baseline set. No closure needed, no second run.

**Migration audit TRUE_NEW_FAILURE after closure = 0.**

## PERFORMANCE

| stage | measured |
|---|---|
| market-local validation (002) | ~318 s |
| FAST release safety (003) | 60.9 s standalone, 5.5 s in a 005 candidate |
| warm bundle reuse (004) | 3.7 s Dayton, 8.4 s Cleveland, 0 builder invocations |
| whole-site compose (005) | 547.4 s |
| data-only candidate staging (005) | 178.0 s |
| candidate handoff round trip (006) | byte-identical, deterministic archive |
| **demo-media, before / after (007)** | **1,349.7 s → 1,083.8 s aggregate in the audit; floor 534.0 s** |
| **projected remote broad wall (007)** | **1,349.7 s → 847.2 s** |
| ordinary data-only release, remote broad jobs | 0 |

## 008 REMAINING BLOCKERS

All five that 006 listed remain open, and 007 solved none of them, because none was in its scope: three
sealed markets, a tree whose live records include Toledo, an opened production gate, remote execution actually
proven, and the four live measurements. What 007 changed is the cost of working through them — a required
broad audit is now about 14 minutes of projected remote wall instead of 23, and an audit can no longer hide a
changed defect behind an old node id.

## 008 MARKET RECOMMENDATION

Using existing ready-market state only; nothing was promoted or sealed to satisfy this.

| slot | recommended | preparation still required |
|---|---|---|
| SMALL/MEDIUM | Lexington, KY (28 / 14) | register on the branch, seal a package, run the FAST lane |
| MEDIUM | Chattanooga, TN (48 / 8) | register, seal, FAST lane |
| LARGE | Nashville, TN (80 / 19) | register, seal, FAST lane |

Held in reserve: Dayton already has a committed sealed package and is already live, so a withdrawal-shaped
delta there rehearses the whole lane with no new market at all.

## GIT

Branch `worker/atlas-throughput-001` in worktree `C:\Atlas-Throughput-V1` (no new worktree), continued from
the pushed 006 head `e9d6baf`. Test engineering only: no market authority, no participation, no promotion, no
deployment, no paid call.

| commit | subject |
|---|---|
| `a3663ac` | ATLAS-THROUGHPUT-007 reduce legacy regression debt and historical test noise (the demo-media split and shared chain helper, the two migrated count pins, 160 failure signatures, signature-aware classification in both classifiers, the regenerated shard manifest, 18 new tests and the reports) |

Untracked measurement directories (`data/regression/atlas-throughput-007-audit/`) and the scratch roots under
`C:\ptf007` are gitignored artifacts, never inputs. The FINAL report is committed on top and the branch
pushed; origin == HEAD and a clean tree are verified after the push and stated in the delivery message.


---

1. WHAT WAS DEMO-MEDIA WALL TIME BEFORE 007? **1,349.7 s** in one module (1,375.7 s as measured in the 005
   audit that set the shard plan).
2. WHAT IS DEMO-MEDIA WALL TIME AFTER 007? **1,133.4 s aggregate across three modules, with the slowest at
   558.2 s** — and the slowest module is what a sharded run actually waits for.
3. WERE ANY ORIGINAL DEMO-MEDIA SAFETY CLAIMS REMOVED? **NO** — all ten are mapped to an owner, and two were
   added.
4. WHAT IS THE NEW PROJECTED FOUR-SHARD REMOTE BROAD WALL TIME? **847.2 s** (14.1 minutes), down from
   1,349.7 s, with all four shards landing on the same second.
5. CAN ADDING VALID HOTELS STILL BREAK THE MIGRATED HISTORICAL COHORT TESTS SOLELY BECAUSE CURRENT COUNTS
   GREW? **NO**.
6. DOES SAME NODE ID WITH A DIFFERENT FAILURE SIGNATURE BECOME TRUE_NEW? **YES**.
7. HOW MANY OF THE ~160 LEGACY FAILURES WERE ACTUALLY FIXED? **0** — deliberately; the order forbids
   eliminating them and each is already correctly suppressed.
8. HOW MANY WERE INTENTIONALLY LEFT AS DOCUMENTED LEGACY DEBT? **160**, now each with a signature, category,
   reason and review date.
9. DOES ORDINARY DATA_ONLY STILL REQUEST 0 BROAD JOBS? **YES**.
10. MIGRATION AUDIT TRUE_NEW_FAILURE = **0 (PRE_EXISTING 160 = the f75aa95 set exactly)**
11. WAS ANY MARKET AUTHORITY OR LIVE DEPLOYMENT CHANGED? **NO**.
12. IS ATLAS-THROUGHPUT-008 READY TO BEGIN PREPARATION FOR THE LIVE THREE-MARKET FACTORY PROOF? **YES** — the
    packet is complete and measured, and the five blockers are named with the order they must be worked in.
    008 itself is not started.

STOP. 008 not started. Nothing promoted. Nothing deployed.
