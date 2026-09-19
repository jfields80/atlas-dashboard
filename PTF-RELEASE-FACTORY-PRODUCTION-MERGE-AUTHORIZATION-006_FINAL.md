# PTF-RELEASE-FACTORY-PRODUCTION-MERGE-AUTHORIZATION-006 — FINAL

**Result: PASS.** The bounded release-factory repair is integrated as code only:
- Branch `worker/ptf-release-factory-integration-006` = **`0b6ad264`**.
- It is current live `96564199` plus exactly the 3 repair commits, and it is pushed.
- Every post-merge requirement passed on the clean integrated code.
- The PetTripFinder site, launch participation and all authorizations are untouched.
- No market was deployed or registered into production.
- The legacy broad suite was not run.

Evidence: `PTF-RELEASE-FACTORY-PRODUCTION-MERGE-AUTHORIZATION-006_artifacts/`.

## Founder decision (recorded)

```
LEGACY BROAD AUDIT                    = INCOMPLETE / NON-SCALABLE
BOUNDED DIFFERENTIAL MIGRATION PROOF  = ACCEPTED
```

The legacy full-suite audit did **not** pass and is not claimed to have passed. For THIS
release-factory repair only, it is superseded by:
- the focused changed-surface tests;
- the parent-vs-repair differential (0 repair-caused failures);
- the bounded determinism differential (both commits identical);
- the NO_DELTA proof;
- the Columbia registration replay;
- the Columbia zero-rebuild staging proof.

This is not a general waiver for future shared-code changes. The pre-existing demo-media
scaling defect is not waived.

## Phase 1 — exact production change set

Audit-branch history since live `96564199`:

| Commit | Kind | Files |
|---|---|---|
| `c465fc4f` | **A + B** repair | the 6 production modules below + the focused test module |
| `cf73a06d` | **A + B** repair (implied additions) | `release_coordinator.py`, the test module |
| `cc1cc8f9` | C report | `…EFFICIENCY-BOUNDED-REPAIR-002_PAUSED.md` |
| `a063e68b` | C report + artifacts | `…DETERMINISM-DIFFERENTIAL-CLOSURE-003_*` |
| `261b0d94` | C report + artifacts | `…BOUNDED-MIGRATION-DECISION-004_*` |
| `cd8cb3d7` | **A + B** content-key correction | `release_coordinator.py`, `regression_delta.py`, the test module |
| `28ef699a` | C report + artifacts | `…LIVE-CONTENT-KEY-CORRECTION-005_*` |

**A. Production repair code (6 files)**, all under `atlas-dashboard/scripts/pettripfinder/`:

| File | What it does in the repair |
|---|---|
| `release_index.py` | resolves the current live source commit (`live-source`) |
| `registration_release_lane.py` | live preflight, derived base, AUTOMATIC classification |
| `regression_delta.py` | `classify_document`; staging report through `resolve_deployed` |
| `registration_data_only.py` | lookup hygiene, paid-ledger content proof |
| `release_coordinator.py` | release-store round trip, deployed-bundle parent lookup, stage/reuse, implied additions, deployment manifest, rollback |
| `assemble_production_site.py` | pure extraction of gates + description |

**B. Required focused tests (1 file)**:
`atlas-dashboard/tests/pettripfinder/test_release_factory_bounded_repair_002.py`.

**C. Report / audit only**: the 4 `docs(ptf)` commits above. Not integrated.

No `C:\t` outputs, logs or replay artifacts are in A or B.

## Phase 2 — current live lineage

`release_index live-source --verify-host`, run at the integration head:

| | |
|---|---|
| RESOLVED | **YES** |
| CURRENT_LIVE_SOURCE_COMMIT | **`9656419918229db7a0eb5ca5a1b4fb514e0e9c34`** (tip of `origin/worker/ptf-augusta-ga-market-002`) |
| live deploy / record | `6aaeb3b7384e1bb712adb084` / `ptf-deploy-augusta-006-…json` |
| markets / profiles / routes | **30 / 2165 / 2477** |
| host_verified | **true** (served sitemap sha256 `d08b8ca2…` == live record) |
| origin/main | `c236f52d`, stale, does not contain live, **not used** |

**CURRENT LIVE VERIFIED = YES.**

One transient: the first `--fetch --verify-host` run got "Remote end closed connection without
response" and failed closed (RESOLVED NO). Two immediate re-reads, with both User-Agents,
returned the same sitemap `d08b8ca2…`, and the re-run resolved YES. The bootstrap contract
retries the host check once.

## Phase 3 — clean production-integration branch

- `worker/ptf-release-factory-integration-006` was created from **`96564199`**, not from
  `origin/main`, with no history rewritten.
- `git cherry-pick -x` of the 3 repair commits applied cleanly:
  - `8dfef9d5` ← `c465fc4f`
  - `5572496d` ← `cf73a06d`
  - `0b6ad264` ← `cd8cb3d7`
- `git diff cd8cb3d7 0b6ad264 -- atlas-dashboard` is **empty**: the integrated code tree is
  byte-identical to the proven one.
- It differs from live in exactly the 7 files above. No reports are included.

## Phase 4 — post-merge focused verification (integration worktree `C:\t\int6`)

| Run | Result |
|---|---|
| repair focused module (resolver, lane/classifier, release store incl. deployed-bundle lookup, paid ledger, narrow-lane negatives, deployment compatibility) | **66 / 66 PASS** (85.4 s) |
| 12 directly affected existing modules (`toledo_oh_promotion_002`, `regression_delta_001`, `registration_data_only_001`, `nashville_tn_launch_005`, `lexington_ky_launch_006`, `composite_fresh_market_001`, `atlas_throughput_002/003/004/005/006/007`) | 590 tests, 24 failed. **Failure set IDENTICAL** to the accepted evidence at `cd8cb3d7`, so **0 new failures** |

The 24 failures are pre-existing and listed in `post_merge_failure_set.txt`. The legacy broad
suite was not run.

## Phase 5 — NO_DELTA safety proof (integrated code, live tree, `C:\t\col6` before Columbia)

The store is the one seeded ONCE (in 004) from one assembly of current verified live, bundle
`55e0f5bb…`. It was reused, not re-seeded.

| Requirement | Result |
|---|---|
| CURRENT LIVE BUNDLE MATCHES EXACTLY | **YES** — candidate `55e0f5bb…`; 13 188 files, 0 added / removed / changed |
| UNCHANGED BUNDLES REUSED | **30** |
| UNCHANGED MARKETS REBUILT | **0** |
| PARENT LOOKUP | **PASS** (by release digest `13e12416…`, the pre-registration tree) |
| PARENT ROUTES PRESERVED | **PASS** — 13 170 / 13 170 |
| ALL GATES | **22 / 22 PASS** |
| UNEXPECTED DELTA | **[]** |

## Phase 6 — Columbia final controlled replay (integrated code, no deploy)

The Columbia source-ready work `b58e8f10` was merged unchanged into `C:\t\col6`: 56 files, all
added, all Columbia-named, 0 non-Columbia paths. No policy or census file was altered.

| Requirement | Result |
|---|---|
| REGISTRATION (promote → AUTOMATIC packet) | **198.48 s (3 m 18 s)** → AUTHORIZATION_READY |
| <= 10 minutes (hard) | **MET** |
| <= 5 minutes (target) | **MET** |
| live base / classification | live `96564199` resolved automatically; base derived `0b6ad264`; AUTOMATIC; COMPOSITE_FRESH_MARKET_DATA_ONLY |
| ELIGIBLE | **YES** (15 / 15 proof checks) |
| FULL_REGRESSION_REQUIRED | **NO** (remote broad jobs 0) |
| FAST | **15 / 15 PASS**; package and candidate reproducible |
| BROAD RUNS | **0** |
| projection | 31 / 2229 / 2486; unexpected 0 / 0 / 0; package `pkg-columbia-sc-5b35c84f0969f7eb` |
| PARENT LOOKUP | **PASS** — the registration moved the digest to `347888…`; the parent was found by `DEPLOYED_BUNDLE_SHA256` → `13e12416…` |
| UNCHANGED BUNDLES REUSED | **30** (each the parent's own stored fragment) |
| UNCHANGED MARKETS REBUILT | **0** |
| COLUMBIA BUNDLES BUILT | **1** (64 profiles, 72 routes) |
| PARENT ROUTES PRESERVED | **PASS** — 13 170 parent routes all served, 0 undeclared removals |
| additions | 316 implied, 0 undeclared |
| ALL STAGING GATES | **22 / 22 PASS** |
| UNEXPECTED DELTA | **[]** — +`columbia-sc` only; bytes: 0 removed, 388 added (all Columbia), 1 changed (`sitemap.xml`) |
| candidate | PROJECTED / NON-DEPLOYABLE (`NOT_DEPLOYABLE_UNDER_COMMITTED_PARTICIPATION`) |
| CURRENT LIVE MODIFIED | **NO** — served sitemap still `d08b8ca2…` after the replay |
| DEPLOYMENT | **NO** |

`launch_participation.json` is unchanged during staging; Columbia stays SOURCE_READY, as the
replay's own `register` step wrote it in the throwaway worktree. No founder or deployment
authorization exists. The replay commits in `C:\t\col6` were not pushed.

## Phase 7 — integration

Phases 4–6 passed, so the repair was integrated. Repository practice:
- `origin/main` is 581+ commits stale and never carries live.
- The live lineage is the latest launched market's branch tip.

The integration is therefore the pushed code-only factory ref:

```
origin/worker/ptf-release-factory-integration-006 = 0b6ad264e7f2c7e97aca3fd8935b8c33f69a3308
  = 96564199 (current live) + 8dfef9d5 + 5572496d + 0b6ad264 (the repair, cherry-picked -x)
```

Untouched:
- `origin/main` (`c236f52d`)
- `origin/worker/ptf-augusta-ga-market-002` (`96564199`, the live deploy lineage)
- every market branch
- current live, participation, authorizations

The next market branches from this ref (Phase 8). Its launch then puts the repair into the live
lineage through the normal launch path.

## Phase 8 — future market bootstrap contract

Script: `PTF-RELEASE-FACTORY-PRODUCTION-MERGE-AUTHORIZATION-006_artifacts/bootstrap_new_market.ps1`.
It was dry-run, and the dry run resolved live mechanically, host-verified, and chose base
`0b6ad264`.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File bootstrap_new_market.ps1 `
    -Market <market-id> -WorkOrder <PTF-...-001> [-DryRun]
```

It:
1. runs `git fetch --prune origin`;
2. checks out `origin/worker/ptf-release-factory-integration-006` in a throwaway worktree and runs
   **its** resolver: `release_index live-source --verify-host --json`. It requires
   `RESOLVED = YES` and `host_verified = true`, retrying once, and never reads `origin/main`;
3. picks the base:
   - the live commit, if live already contains the factory ref;
   - else the factory ref, if it contains live;
   - else it **STOPS** (the lineages diverged);
4. creates `worker/ptf-<market>-market-001` at that base in the short path `C:\Atlas-<market>`.

Canonical workflow for a new Top-50 market:

1. **Bootstrap**: the script above.
2. **Source-ready shadow build**:
   - Work only in the market's own shard, staged under
     `launch_packages/pettripfinder/markets/staging/<market>/`.
   - Never edit the 3 generated globals.
   - Seal the shadow package with FAST.
3. **Registration**: generic factory commands, in order:
   - promote the staged documents
   - `market_registration_cli --write`
   - `build_global_authority --write` / `--check`
   - derive the release contract
   - `registration_release_lane register`
   - `registration_release_lane seal --work C:/t/<short>`
   - commit
   - `registration_release_lane packet` with no `--classification`: the lane resolves live,
     derives the base and classifies AUTOMATICALLY.

   Expected: AUTHORIZATION_READY, NEW_MARKET_REGISTRATION_DATA_ONLY / COMPOSITE_FRESH_MARKET
   ELIGIBLE, FULL_REGRESSION_REQUIRED NO, broad runs 0, target ≤ 5 minutes.
4. **Founder authorization**: a separate founder decision. The factory never writes it.
5. **Staging**:
   - `release_coordinator.stage(ADD)` from the release store.
   - The parent is found by its deployed `bundle_sha256`.
   - Expect 0 unchanged markets rebuilt, the new market built ≤ 1 time, all gates passing and
     no unexpected delta.
   - The store is seeded ONCE per live release: one assembly that must equal the live bundle.
6. **Deployment**: the existing deployment order, current-parent guard and authorization,
   unchanged by this repair.

## Final answers

1. LEGACY BROAD AUDIT = INCOMPLETE / NON-SCALABLE
2. BOUNDED DIFFERENTIAL PROOF ACCEPTED = YES (for this repair only)
3. MINIMUM PRODUCTION COMMITS = `c465fc4f`, `cf73a06d`, `cd8cb3d7`, integrated as `8dfef9d5`, `5572496d`, `0b6ad264`
4. PRODUCTION FILES CHANGED = 6 — `release_index.py`, `registration_release_lane.py`, `regression_delta.py`, `registration_data_only.py`, `release_coordinator.py`, `assemble_production_site.py`
5. TEST FILES CHANGED = 1 — `tests/pettripfinder/test_release_factory_bounded_repair_002.py`
6. CURRENT LIVE SOURCE COMMIT = `9656419918229db7a0eb5ca5a1b4fb514e0e9c34` (deploy `6aaeb3b7…`, 30 / 2165 / 2477, host-verified)
7. POST-MERGE FOCUSED TESTS = 66 / 66 PASS; 12 affected modules have a failure set identical to the evidence (0 new)
8. NO_DELTA UNCHANGED BUNDLES REUSED = 30
9. NO_DELTA UNCHANGED MARKETS REBUILT = 0
10. COLUMBIA REGISTRATION TIME = 198.48 s (3 m 18 s)
11. COLUMBIA ELIGIBLE = YES
12. COLUMBIA FULL_REGRESSION_REQUIRED = NO
13. COLUMBIA FAST = 15 / 15 PASS
14. COLUMBIA UNCHANGED BUNDLES REUSED = 30
15. COLUMBIA UNCHANGED MARKETS REBUILT = 0
16. COLUMBIA BUNDLES BUILT = 1
17. PARENT ROUTES PRESERVED = PASS (NO_DELTA and Columbia)
18. UNEXPECTED DELTA = []
19. CURRENT LIVE MODIFIED = NO
20. DEPLOYMENT PERFORMED = NO
21. FACTORY REPAIR INTEGRATED = YES — `origin/worker/ptf-release-factory-integration-006` @ `0b6ad264`
22. READY TO RESUME TOP-50 EXPANSION = YES — through the bootstrap contract above

```
PTF RELEASE FACTORY PRODUCTION MERGE = PASS
REGISTRATION TARGET = <=5 MINUTES
UNCHANGED MARKETS REBUILT = 0
BROAD REGISTRATION RUNS = 0
CURRENT LIVE MODIFIED = NO
DEPLOYMENT PERFORMED = NO
READY TO RESUME TOP-50 EXPANSION = YES
```
