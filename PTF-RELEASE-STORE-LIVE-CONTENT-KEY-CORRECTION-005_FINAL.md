# PTF-RELEASE-STORE-LIVE-CONTENT-KEY-CORRECTION-005 — FINAL

Branch `worker/ptf-release-factory-efficiency-audit-001`, worktree `C:\Atlas-PTF-Release-Audit`.
Correction commit **`cd8cb3d7`** on top of the repair `cf73a06d`, the 003 differential and the
004 decision, all preserved. Current live stays `96564199` / deploy `6aaeb3b7384e1bb712adb084`
/ bundle `55e0f5bb…`.

**Result: PASS.**
- The stored deployed parent is now found by the bundle it deployed.
- `release.parent_routes_preserved` passes for NO_DELTA and for Columbia, on the tree where
  the Columbia registration had already moved the release digest.
- 30 bundles reused, 0 rebuilt, Columbia built once, unexpected delta [].

Not done: no broad regression, no demo-media or shard test, no founder or deployment
authorization, no participation write, no deploy. A read-only GET of
`https://pettripfinder.com/sitemap.xml` returns sha256 `d08b8ca2…`, the parent's sitemap, so
live is unchanged.

Evidence: `PTF-RELEASE-STORE-LIVE-CONTENT-KEY-CORRECTION-005_artifacts/`.

## Phase 1 — identity semantics, proven on the Columbia replay

The replay worktree `C:\t\col5` ran live `96564199`, then a fast-forward to `cd8cb3d7`, then the
Columbia merge `f854309e`, then the registration commit `13f40785`. The snapshots
(`identity_before.json` / `identity_after.json`) were taken on the tree before the merge and
after the registration commit:

| | Before registration | After registration | |
|---|---|---|---|
| live bundle sha256 | `55e0f5bbf02a5e26…` | `55e0f5bbf02a5e26…` | **unchanged** |
| live sitemap sha256 | `d08b8ca2f019196b…` | `d08b8ca2f019196b…` | unchanged |
| deploy / markets / profiles / sitemap routes | 6aaeb3b7 / 30 / 2165 / 2477 | 6aaeb3b7 / 30 / 2165 / 2477 | unchanged |
| **release-manifest digest** | `sha256:13e12416…` | `sha256:347888…` | **changed** |
| `global_index_digest` | `008f2791…` | `0bf1800d…` | changed |
| registered markets in the live index | 31 (not participating: detroit) | 32 (not participating: columbia-sc, detroit) | changed |
| manifest digest **without** `global_index_digest` | `d811fe65…` | `d811fe65…` | **identical** |
| live files / routes (NO_DELTA candidate vs seeded live site) | 13 188 / 13 170 | 13 188 / 13 170; 0 added, 0 removed, 0 changed | **byte-identical** |

Fields that contribute to each identity:
- **Release-manifest digest** (`LiveTruth.manifest()`): `schema`, `release_schema_version`,
  `coordinator_version`, `derived`, `derived_from{deployment_record, authorization_id, deploy_id}`,
  `parent_release_digest`, `source_commit`, `participating_markets`,
  `markets[]{market_id, profile_count, route_count, …}`, `total_profiles`,
  `sitemap_route_count`, `deployment_artifact_digest`, `sitemap_sha256`, **`global_index_digest`**
  (a digest over every REGISTERED market's release index, participating or not),
  `rollback_target`, `status`.
- **Deployed content identity**: `bundle_sha256` = `APS.bundle_digest(APS.file_hashes(site))`,
  a digest over every served file's path and bytes. No registration input enters it.

So registration moves the release digest through `global_index_digest` alone, while the deployed
bytes, and therefore `bundle_sha256`, stay the same.

## Phase 2 — minimum store lookup fix (`release_coordinator.py`)

- `ReleaseStore.get_release_by_bundle(bundle_sha256)` scans the existing content-addressed
  release records:
  - Every record is read through the existing verified `get_release`, so a corrupt record is
    `CANDIDATE_CORRUPT`, never a miss.
  - It returns the record whose attached `bundle_sha256` matches.
  - Two records may claim one bundle only if they carry the same stored `bundle_object` and the
    same market fragments; otherwise it raises the new code `AMBIGUOUS_PARENT_BUNDLE`.
- `ReleaseStore.resolve_deployed(release_digest=, bundle_sha256=)`:
  - It tries the release digest first and keeps it as metadata.
  - A record found there that did not deploy `bundle_sha256` is `BUNDLE_DIGEST_MISMATCH`.
  - On a miss it falls through to the bundle identity, and it reports how the record was found
    (`RELEASE_DIGEST` / `DEPLOYED_BUNDLE_SHA256`).
- `_fragments_of(doc)` is a small helper that `fragment_digests` now shares.

What is unchanged:
- No new bundle format, database, store layout, cache or deployment path.
- Release records stay stored at, and verified against, their release-manifest digest.

## Phase 3 — lookups corrected

| Lookup | Before | After |
|---|---|---|
| `_parent_route_gate` (`release.parent_routes_preserved`, `release.additions_are_declared`) | `get_release(parent_digest)` only | `resolve_deployed(parent_digest, parent_bundle_sha256)`; records `parent_found_by`, `parent_release_digest_stored`, `parent_bundle_sha256`; archive self-hash check and route arithmetic unchanged |
| `_run_candidate_gates` / `stage` gate call | passed the digest only | also passes the live `bundle_sha256` (only when the parent is live, i.e. no explicit `parent_release_digest`) |
| `stage` parent fragments | digest lookup, then an unverified scan for the live bundle that took the FIRST match | `resolve_deployed`, which is verified, mismatch-checked and ambiguity-checked |
| `rollback` | `to_release_digest` only | `to_release_digest` and/or `to_bundle_sha256` through `resolve_deployed`; the host-current check, bundle-object presence and the re-hash of the extracted bundle are unchanged; returns `restored_found_by`; CLI `rollback-simulated --to-bundle` |
| `plan()` | digest only | `resolve_deployed` |
| `regression_delta` staging-availability report | digest only | `resolve_deployed` |

No check was weakened. Route preservation still compares every parent route. Rollback still
refuses a stale current release, a missing record or object, a corrupt record and a
re-hash mismatch.

## Phase 4 — focused tests

`tests/pettripfinder/test_release_factory_bounded_repair_002.py` gains section 7,
`TestDeployedContentIsTheParentKey`, with 9 tests. It extends the existing module; no new test
module was added.

| # | Required | Test |
|---|---|---|
| 1, 2 | seed live, look up by exact bundle | `test_a_seeded_live_release_is_found_by_its_exact_bundle` |
| 3, 4, 5 | registration moves index metadata, bundle unchanged, parent lookup still succeeds | `test_registration_moves_the_release_digest_and_never_the_bundle` (diff keys == `["global_index_digest"]`) |
| 6 | parent_routes_preserved passes | `test_parent_routes_are_preserved_across_a_registration` (and the digest alone still fails); `test_a_lost_route_still_fails_after_a_bundle_lookup` |
| 7 | rollback resolves the exact deployed parent | `test_rollback_resolves_the_exact_deployed_parent` (by bundle, by moved digest + bundle, by digest; stale current refused) |
| 8 | wrong bundle fails | `test_a_wrong_bundle_finds_no_parent` (store, gate, rollback) |
| 9 | corrupt record fails | `test_a_corrupt_record_fails_closed_on_the_bundle_lookup` (store, gate, rollback) |
| 10 | bundle mismatch fails | `test_a_bundle_sha_mismatch_fails` (digest record with another bundle; tampered bundle object) |
| 11 | no ambiguous claims without content identity | `test_two_records_claim_one_bundle_only_as_the_same_content` (same content allowed; different fragments → `AMBIGUOUS_PARENT_BUNDLE` in store, gate and rollback) |

The fixtures are synthetic (`m-one` / `m-two`). There are no city exceptions and no market
totals.

```
FOCUSED TESTS = 66 / 66 PASS   (57 prior + 9 new, 70.6 s)
```

Exposed existing modules: the 12 test modules that import `release_coordinator` or
`regression_delta` ran once at the fix and once at `cf73a06d` (`C:\t\rfd3a`), one after the
other. Both runs: **590 tests, 24 failures, IDENTICAL failure sets**
(`exposed_modules_failure_set.txt`).

## Phase 5 — NO_DELTA store proof

The store `C:\t\rs4` was seeded ONCE (in 004): one assembly of current verified live whose bundle
is `55e0f5bb…` byte for byte, stored at the pre-registration digest `13e12416…`. It was not
re-seeded. `stage(NO_DELTA)` ran on the POST-registration tree, where the live digest is
`347888…`:

| Requirement | Result |
|---|---|
| LIVE BUNDLE SHA | `55e0f5bbf02a5e26e8a5eba8510a4488d9a3da6ffaac604ef22df80637fd8914` |
| digest lookup (`347888…`) | misses (by design) |
| PARENT LOOKUP | **PASS** — `DEPLOYED_BUNDLE_SHA256` → stored `13e12416…`, 30 fragments |
| PARENT ROUTES PRESERVED | **PASS** — 13 170 / 13 170 parent routes, 0 undeclared removals |
| UNCHANGED BUNDLES REUSED | **30** |
| UNCHANGED MARKETS REBUILT | **0** |
| ALL GATES | **22 / 22 PASS** |
| BUNDLE BYTES MATCH CURRENT LIVE | **YES** — candidate `55e0f5bb…`; 13 188 files, 0 added / removed / changed |
| unexpected delta | [] |
| participation | sha256 unchanged |

## Phase 6 — Columbia staging

Registration was replayed ONCE, because the factory code changed and the AUTOMATIC classification
must be taken on the new base. It ran in 196.19 s:

| | Result |
|---|---|
| status | AUTHORIZATION_READY (live 96564199 resolved automatically, base derived `cd8cb3d7`, AUTOMATIC classification) |
| class | COMPOSITE_FRESH_MARKET_DATA_ONLY |
| ELIGIBLE | **YES** (15 / 15 proof checks) |
| FULL_REGRESSION_REQUIRED | **NO** (remote broad jobs 0) |
| FAST | **15 / 15** (package and candidate reproducible) |
| projection | 31 / 2229 / 2486, unexpected 0 / 0 / 0 |
| package | `pkg-columbia-sc-149fd8e7f7aaf507` |

`stage(ADD columbia-sc)` ran with the in-memory participation projection, the seal receipt
bound, and 668 s staging:

| Requirement | Result |
|---|---|
| PARENT LOOKUP | **PASS** (`DEPLOYED_BUNDLE_SHA256` → `13e12416…`) |
| PARENT ROUTES PRESERVED | **PASS** — 13 170 parent routes all served (13 558 candidate), 0 undeclared removals |
| additions_are_declared | PASS — 316 implied, 0 undeclared |
| UNCHANGED BUNDLES REUSED | **30** (each is exactly the parent's stored fragment) |
| UNCHANGED MARKETS REBUILT | **0** |
| COLUMBIA BUNDLES BUILT | **1** (64 profiles, 72 routes) |
| ALL STAGING GATES | **22 / 22 PASS** |
| UNEXPECTED DELTA | **[]** — added `columbia-sc` only; profiles 2165 → 2229, sitemap routes 2477 → 2550 |
| bytes vs live | 0 removed, 388 added (all Columbia), 1 changed (`sitemap.xml`) |
| candidate | **PROJECTED / NON-DEPLOYABLE** (`NOT_DEPLOYABLE_UNDER_COMMITTED_PARTICIPATION`) |
| participation / authorizations | `launch_participation.json` unchanged during staging (Columbia SOURCE_READY, as written by `register`); no authorization file |

## Phase 7 — acceptance

| Criterion | Result |
|---|---|
| focused tests all pass | PASS (66 / 66) |
| stable parent bundle lookup works | PASS |
| NO_DELTA staging passes | PASS (22 / 22, bundle == live) |
| Columbia staging passes all gates | PASS (22 / 22) |
| 30 unchanged bundles reused | PASS |
| 0 unchanged markets rebuilt | PASS |
| Columbia built <= 1 | PASS (1) |
| unexpected delta = [] | PASS |
| current live modified = NO | PASS (live sitemap still `d08b8ca2…`) |
| deployment = NO | PASS |

## Changed files

Production (2):
- `atlas-dashboard/scripts/pettripfinder/release_coordinator.py`
- `atlas-dashboard/scripts/pettripfinder/regression_delta.py` (one call site)

Tests (1): `atlas-dashboard/tests/pettripfinder/test_release_factory_bounded_repair_002.py` (+9 tests).

Commit `cd8cb3d7`. The replay worktree `C:\t\col5` and candidates `C:\t\cc5n`, `C:\t\cc5` are
local only.

## Final answers

1. DEPLOYED CONTENT IDENTITY KEY = `bundle_sha256` (`55e0f5bbf02a5e26e8a5eba8510a4488d9a3da6ffaac604ef22df80637fd8914`)
2. RELEASE MANIFEST DIGEST REGISTRATION-SENSITIVE = YES (`13e12416…` → `347888…`, only through `global_index_digest`)
3. BUNDLE SHA REGISTRATION-STABLE = YES
4. STORE LOOKUP FIXED = YES
5. PARENT ROUTES LOOKUP FIXED = YES
6. ROLLBACK LOOKUP FIXED = YES
7. FOCUSED TESTS = 66 / 66 PASS
8. NO_DELTA PARENT LOOKUP = PASS
9. NO_DELTA PARENT ROUTES PRESERVED = PASS
10. NO_DELTA UNCHANGED BUNDLES REUSED = 30
11. NO_DELTA UNCHANGED MARKETS REBUILT = 0
12. COLUMBIA ELIGIBLE = YES
13. COLUMBIA FULL_REGRESSION_REQUIRED = NO
14. COLUMBIA FAST = 15 / 15 PASS
15. COLUMBIA PARENT LOOKUP = PASS
16. COLUMBIA PARENT ROUTES PRESERVED = PASS
17. COLUMBIA UNCHANGED BUNDLES REUSED = 30
18. COLUMBIA UNCHANGED MARKETS REBUILT = 0
19. COLUMBIA BUNDLES BUILT = 1
20. COLUMBIA UNEXPECTED DELTA = []
21. CURRENT LIVE MODIFIED = NO
22. DEPLOYMENT PERFORMED = NO
23. READY FOR PRODUCTION MERGE = NO — this order's acceptance passed, but the branch has had no production-merge review or authorization. The legacy broad audit stays INCOMPLETE under the 004 bounded decision, and the pre-existing demo-media scaling defect is not waived.

```
PTF RELEASE STORE CONTENT-KEY CORRECTION = PASS
PARENT ROUTES PRESERVED = PASS
UNCHANGED MARKETS REBUILT = 0
UNCHANGED BUNDLES REUSED = 30
COLUMBIA BUNDLES BUILT = 1
CURRENT LIVE MODIFIED = NO
DEPLOYMENT PERFORMED = NO
READY FOR PRODUCTION MERGE = NO
```
