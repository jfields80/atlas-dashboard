# PTF-RELEASE-FACTORY-BOUNDED-MIGRATION-DECISION-004 — FINAL (PAUSED)

Branch `worker/ptf-release-factory-efficiency-audit-001`, worktree `C:\Atlas-PTF-Release-Audit`.
Repair `cf73a06d`, parent / current live source `96564199` (deploy `6aaeb3b7384e1bb712adb084`,
bundle `55e0f5bb…`, 30 markets / 2165 profiles / 2477 sitemap routes).

**Outcome: the bounded migration decision is recorded. The Columbia controlled no-deploy
replay registered Columbia in 3 m 03 s with no broad regression. It FAILED two hard
reuse-staging criteria: PARENT RELEASE LOOKUP and the `release.parent_routes_preserved` gate.
As the order requires, the order is PAUSED and no fix was attempted.**

Nothing was deployed. Current live, `C:\Atlas` and `origin/main` were not touched. No founder
authorization was written. The replay ran in the throwaway worktree `C:\t\col4`, and its commits
were not pushed. No broad, demo-media, shard or real-build test was run.

Evidence: `PTF-RELEASE-FACTORY-BOUNDED-MIGRATION-DECISION-004_artifacts/`.

## Phase 1 — preserved repair

| Requirement | Result |
|---|---|
| repair commit | `cf73a06d` is an ancestor of HEAD `a063e68b`; only reports/artifacts were added since |
| focused repair tests | **57 / 57 PASS** (re-run at HEAD, 76.2 s, `focused_tests.txt`) |
| repair-caused differential failures | **0** (002 closeout + 003 determinism differential) |
| current live modified | NO |
| deployment performed | NO |
| branch tree | clean |

## Phase 2 — bounded migration decision (recorded)

1. The required legacy full-suite audit could not finish within its bounded operational
   requirement: about 44.5 h spent and shard 4 interrupted (002 PAUSED closeout).
2. The parent baseline shows the same pathological scaling:
   - demo_media: 15 608 s / 45.4 GB at the parent vs 16 533 s / 45.4 GB at the repair.
   - determinism: identical 60-minute TIMEOUT, identical stack and matching memory at both
     commits (003).
3. The focused changed-surface tests pass: 57 / 57.
4. Differential parent-vs-repair testing found **0** repair-caused failures:
   - 225 pre-existing functional failures.
   - 3 environmental failures.
   - 2 determinism tests PRE_EXISTING.
5. The repair may therefore proceed to the controlled NO-DEPLOY replay.
6. This does **not** waive the pre-existing demo-media scaling defect. The demo-media
   determinism assertions were **not reached at either commit** and are not claimed to pass.
7. This does **not** redefine ordinary future registration to require broad testing.

```
REPAIR-CAUSED DIFFERENTIAL FAILURES      = 0
PRE-EXISTING DEMO-MEDIA SCALING DEFECT   = YES
DEMO-MEDIA DETERMINISM ASSERTIONS        = NOT REACHED AT EITHER COMMIT
```

## Phase 3 — Columbia controlled no-deploy replay

Live resolved with the repaired resolver (`release_index live-source`, 2.2 s, 210 refs):
`CURRENT_LIVE_SOURCE_COMMIT = 9656419918229db7a0eb5ca5a1b4fb514e0e9c34`, deploy `6aaeb3b7…`,
30 participating markets. `origin/main` is stale and was not used.

Replay worktree `C:\t\col4`:

| Step | Commit | Content |
|---|---|---|
| created detached at live | `96564199` | current live source |
| fast-forward to repair | `cf73a06d` | only the 7 repair files differ from live, as in the 002 design |
| (one-time migration seed, Phase 4) | — | run here, before Columbia, tree clean |
| merge Columbia source-ready work | `2cc7b674` | `b58e8f10` (2 commits, `fe2d1b6a` + `b58e8f10`): **56 files, all added, all Columbia-named, 0 modified, 0 non-Columbia paths** |
| registration commit (step 7) | `5c976f51` | 14 added + 6 modified (the registration's own derived and shared outputs) |

In total 76 paths differ from the repair, the same shape as the 002 rehearsal.

Registration timer: from step 1 (promote) to step 8 (AUTOMATIC packet), with every command a
generic factory command (`mig4_register.py` is the 002 rehearsal driver, only the work dir
differs):

| Step | Seconds |
|---|---|
| 1 promote staged documents | 0.1 |
| 2 market_registration_cli --write | 0.3 |
| 3a / 3b build_global_authority write / check | 1.6 / 1.7 |
| 4 release contract (derived) | 1.2 |
| 5 lane register | 4.6 |
| 6 lane seal + FAST | 101.7 |
| 7 commit registration | 15.2 |
| 8 lane packet (AUTOMATIC classification) | 56.3 |
| **total** | **182.56** |

```
REGISTRATION TIME          = 182.56 s (3 m 03 s)   → AUTHORIZATION_READY
TARGET <= 5 MINUTES        = MET
HARD LIMIT <= 10 MINUTES   = MET
```

| Requirement | Result |
|---|---|
| live base resolved automatically | YES — 96564199 / 6aaeb3b7; base derived `cf73a06d` (factory commits since live: c465fc4f, cf73a06d) |
| classifier invoked automatically | YES — `classification_source AUTOMATIC`, 55.75 s |
| class | `COMPOSITE_FRESH_MARKET_DATA_ONLY` (NEW_MARKET_REGISTRATION_DATA_ONLY proof v2.0) |
| ELIGIBLE | **YES** — 15 / 15 proof checks PASS |
| FULL_REGRESSION_REQUIRED | **NO** (remote broad jobs 0) |
| FAST | 15 / 15 rules PASS; package and candidate reproducible |
| exactly +1 market | 30 → **31** |
| Columbia-only profiles / routes | +64 profiles (2165 → 2229), release-index routes 2477 → 2486; unexpected market / profile / route changes **0 / 0 / 0** |
| 30 live markets preserved | YES (0 unexpected changes, UNCHANGED_MARKETS_REBUILT 0) |
| broad regression runs | **0** |
| participation | Columbia row written by `register` as `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH` (the normal registration output); 30 FOUNDER_AUTHORIZED rows unchanged; no authorization file |

Sealed package `pkg-columbia-sc-5b31e211cb02fce5`, FAST receipt `…74845520d11b8f79`.

## Phase 4 — reuse-staging proof (PROJECTED / NON-DEPLOYABLE)

**One-time migration seed.** No release store holding the current 30-market live release
existed; 002 never ran its seed. The seed is the repair's designed migration step:

- It ran once, before Columbia was merged, on the live + repair tree.
- One whole-site assembly took 2829.7 s.
- Its bundle `55e0f5bb…` is the **live bundle byte for byte**.
- It was stored at the live release digest `sha256:13e12416…` with 30 fragments, and the round
  trip was verified (`seed.json`).
- It is a one-time store migration, not part of the Columbia stage or the registration timer.

**Stage.** `stage(ADD columbia-sc)` ran with participation projected in memory only,
`run_fast_lane=False` (the seal receipt was bound) and `cache=None`: 787.6 s in total, with
fragments 369.5 s, compose 71.9 s and gates 334.3 s.

| Requirement | Result |
|---|---|
| **PARENT RELEASE LOOKUP** | **FAIL** — see the root cause below |
| UNCHANGED BUNDLES REUSED | **30** (`RELEASE_STORE_FRAGMENT`, via the stage's bundle-sha fallback) |
| UNCHANGED MARKETS REBUILT | **0** |
| COLUMBIA BUNDLES BUILT | **1** (builder invocations 1, `PACKAGE_BUNDLE`, 64 profiles, 72 routes) |
| **ALL STAGING GATES** | **FAIL — 20 / 21 pass; `release.parent_routes_preserved` fails ("no stored parent bundle for 347888064a6b8197")** |
| UNEXPECTED DELTA | **[]** (release diff: added `columbia-sc`, removed [], updated []) |
| CANDIDATE | **PROJECTED / NON-DEPLOYABLE** — `deployment_bundle_manifest` refuses with `NOT_DEPLOYABLE_UNDER_COMMITTED_PARTICIPATION` |
| candidate market set | exactly live 30 + `columbia-sc` |
| live profile counts | all 30 preserved; totals 2165 → 2229, sitemap routes 2477 → 2550 |
| bytes vs seeded live site | 13 188 → 13 576 files: **0 removed, 388 added (all Columbia paths), 1 changed (`sitemap.xml`)** |
| `release.live_routes_preserved_or_declared` | PASS |
| `launch_participation.json` during staging | sha256 unchanged; Columbia still SOURCE_READY |
| founder authorization | none written (authorization directory unchanged) |

### Root cause of the two failures (read-only diagnosis, no fix attempted)

- The seed stored the parent at `LiveTruth.digest()` = `13e12416…`, computed on the live +
  repair tree.
- At stage time, after the registration commit, `LiveTruth.digest()` = `347888…`.
- Comparing the two parent manifests field by field:
  - `derived_from` and `markets` are identical apart from key order.
  - The only material difference is `global_index_digest`: `008f2791…` → `0bf1800d…`.
- `LiveTruth.index` is derived from committed authority and covers **every registered market**:
  32, including the non-participating `columbia-sc` and `detroit-ann-arbor-mi`.
- Registering Columbia therefore moves the live release digest, although the live release
  (deploy, bundle, 30 markets, counts) did not change.
- Keyed on that moving digest:
  - The store lookup misses.
  - The stage still reuses fragments through its bundle-sha fallback.
  - `release.parent_routes_preserved` cannot find the parent bundle and fails closed. Because
    it failed early, `release.additions_are_declared` did not report.

Classification:
- The defect is in how the repaired release store keys the parent release across a
  registration.
- It is not a regression against the parent. At `96564199` the parent-route gate could never
  find a seed (002 finding), and the 002 gate simulation keyed its parent on a single tree
  state, which is why it passed there.
- It is still a hard failure of this order's acceptance.

## Phase 5 — acceptance

| # | Criterion | Result |
|---|---|---|
| 1 | registration <= 10 minutes | PASS (182.56 s) |
| 2 | <= 5-minute target (reported separately) | MET |
| 3 | FULL_REGRESSION_REQUIRED = NO | PASS |
| 4 | broad replay runs = 0 | PASS |
| 5 | unchanged markets rebuilt = 0 | PASS |
| 6 | unchanged bundles reused = 30 | PASS (through the fallback; the keyed parent lookup failed) |
| 7 | Columbia build <= 1 | PASS (1) |
| 8 | candidate delta = Columbia only | PASS (bytes and release diff) |
| 9 | all gates pass | **FAIL** (`release.parent_routes_preserved`) |
| 10 | current live modified = NO | PASS |
| 11 | deployment performed = NO | PASS |
| (Phase 4) | PARENT RELEASE LOOKUP = PASS | **FAIL** |

A hard criterion failed, so the order is **PAUSED**. No other architecture fix was implemented
or proposed. The replay worktree `C:\t\col4`, store `C:\t\rs4`, seed `C:\t\seed4` and candidate
`C:\t\cc4\68e12b6afa4485e1` are left in place for review.

## Final answers

1. REPAIR-CAUSED DIFFERENTIAL FAILURES = 0
2. PRE-EXISTING DEMO-MEDIA SCALING DEFECT = YES
3. DEMO-MEDIA DETERMINISM ASSERTIONS PROVEN = NO (not reached at either commit)
4. BOUNDED MIGRATION DECISION = RECORDED — repair may proceed to the NO-DEPLOY replay; no waiver of the demo-media defect
5. COLUMBIA REPLAY COMPLETED = YES (ran to the end) — acceptance FAILED
6. REGISTRATION TIME = 182.56 s (3 m 03 s)
7. REGISTRATION <=5M TARGET = MET
8. REGISTRATION <=10M HARD = MET
9. FULL_REGRESSION_REQUIRED = NO
10. BROAD RUNS DURING REPLAY = 0
11. UNCHANGED BUNDLES REUSED = 30
12. UNCHANGED MARKETS REBUILT = 0
13. COLUMBIA BUNDLES BUILT = 1
14. PARENT ROUTES PRESERVED = on bytes YES (0 removed; `release.live_routes_preserved_or_declared` PASS); gate `release.parent_routes_preserved` FAIL (parent release not found)
15. UNEXPECTED DELTA = []
16. CURRENT LIVE MODIFIED = NO
17. DEPLOYMENT PERFORMED = NO
18. READY FOR PRODUCTION MERGE = NO

```
PTF BOUNDED MIGRATION DECISION = PASS
COLUMBIA CONTROLLED REPLAY = FAIL
UNCHANGED MARKETS REBUILT = 0
REGISTRATION TIME = 182.56 s (3 m 03 s)
BROAD REPLAY RUNS = 0
CURRENT LIVE MODIFIED = NO
DEPLOYMENT PERFORMED = NO
READY FOR PRODUCTION MERGE = NO
```
