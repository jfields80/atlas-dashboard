# PTF-RELEASE-FACTORY-EFFICIENCY-BOUNDED-REPAIR-002 — PAUSED / CLOSEOUT

Branch `worker/ptf-release-factory-efficiency-audit-001`, worktree `C:\Atlas-PTF-Release-Audit`.
Parent (current verified live when the order started): `96564199`, deploy `6aaeb3b7384e1bb712adb084`.
Preserved audit evidence: `C:\t\rfa2\` (broad shards: `broad\`, `watch\preserved\`; failure
classification and A/B runs: `s4\`). This closeout ran no tests and changed no production code.

## Mechanical state

```
IMPLEMENTATION COMPLETE = YES
FOCUSED TESTS PASS      = YES
CURRENT HEAD            = cf73a06d1b6f3fe83dcdb8363da047735d14d82f (before this report's commit)
TREE CLEAN              = YES
```

## Implementation

```
IMPLEMENTATION COMMITS =
  c465fc4f  bounded release-factory repair: live-source resolver, automatic registration
            classification, release-store round trip, reuse-staging deploy manifest
  cf73a06d  a joining market's action and comparison pages are implied additions

CHANGED PRODUCTION MODULES = (6)
  atlas-dashboard/scripts/pettripfinder/assemble_production_site.py   (pure extraction)
  atlas-dashboard/scripts/pettripfinder/registration_data_only.py
  atlas-dashboard/scripts/pettripfinder/registration_release_lane.py
  atlas-dashboard/scripts/pettripfinder/regression_delta.py           (pure refactor)
  atlas-dashboard/scripts/pettripfinder/release_coordinator.py
  atlas-dashboard/scripts/pettripfinder/release_index.py

CHANGED TEST FILES = (1, new)
  atlas-dashboard/tests/pettripfinder/test_release_factory_bounded_repair_002.py
```

Focused test evidence (preserved):

| Run | Commit | Result | File |
|---|---|---|---|
| `test_release_factory_bounded_repair_002` + `test_atlas_throughput_005` | `cf73a06d` | 110 passed (57 + 53), 0 failed | `C:\t\rfa2\t002b.txt` |
| `test_release_factory_bounded_repair_002` inside broad shard 1 | `cf73a06d` | 57 / 57 passed | `C:\t\rfa2\broad\shard-1.xml` |
| Exposed existing modules (throughput_005, registration_data_only_001, composite_fresh_market_001, regression_delta_001, factory_throughput_001, throughput_006, lexington/nashville launch) | `cf73a06d` vs `96564199` | failure sets IDENTICAL to the parent | `C:\t\rfa2\t*.txt`, `t*_base.txt` |

## Broad migration audit

```
BROAD MIGRATION AUDIT = INCOMPLETE / FAILED BOUNDED-TIME REQUIREMENT
```

```
TOTAL WALL CLOCK SPENT = ~44 h 28 m of audit
                         (first broad start 2026-09-17 ~11:05 → last preserved run end
                          2026-09-19 07:33:05; the order itself began 2026-09-17 ~09:44,
                          ~45 h 49 m total)
```

Run history (all at `cf73a06d` unless stated):

| Attempt | Outcome |
|---|---|
| Single-process broad at `c465fc4f` (11:05) | aborted, superseded by `cf73a06d` |
| Single-process broad at `cf73a06d` (11:22 → 13:47) | aborted at ~91 % (resource growth) |
| Sharded broad, first start (17:08) | sharding driver bug, discarded |
| Sharded broad, shard 1 (20:23 → 21:49) | complete: 4322 tests, 56 failed, 68 skipped, 5172.9 s |
| Resumed shard 2 (22:53 → 09-18 09:07) | complete: 4444 tests, 72 failed, 2 errors, 81 skipped, **36 831.6 s** |
| Shard 3 (→ 09:53) | complete: 5159 tests, 47 failed, 45 skipped, 2692.0 s |
| Shard 4 (09:53 → 13:34) | **INTERRUPTED** — 4329 / 4696 done, stalled at 4329 for 3 h 20 m in the demo-media real-build module while private memory grew 14 → 39 GB; stopped by founder decision (PID 5832 only) |
| Plan C: 356 of shard 4's 367 not-run tests, 5 sequential batches | complete: 356 run, 8 failed |
| Plan D: the 11 remaining real-build tests + 2 determinism tests, A/B | partial (see below) |
| Plan P: every failure re-run isolated at `cf73a06d` (A) and `96564199` (B) | complete: 228 / 228 runnable IDs |
| Plan E: the 3 aggregate-only failures, isolated A/B | complete: passed at both commits |

```
COMPLETED AUDIT EVIDENCE =
  shards 1-3 junit, sha256-pinned (watch/preserved/*.xml.sha256):
    shard-1.xml 01B126CD28D14A3C118FDF7BA0712F5C44C4AF224840962A4F986280F022F89C
    shard-2.xml F5C2345FF35E04D0772BEBEC93FA374944889EC42CC089A52D8C235104E9EF92
    shard-3.xml 0E576AE1BF868F42CA3CA444CB46107E0DF7973E0E8EE8530AF9E47F831BA70B
  shards 1-3 folded run.json: 13 925 collected / 13 554 passed / 194 skipped / 177 failed
  shard 4 completed portion: 4329 tests (4229 passed, 45 failed, 4 xfailed, 51 skipped)
  plan C: 356 of 367 not-run shard-4 tests (8 failed)
  plan D: demo_media (9) A PASS + B PASS; demo_media_fallback (2) A PASS
  plan P: 228 failure IDs isolated at both commits → s4/classification.json
  plan E: 3 environmental failures isolated at both commits → PASS/PASS

INCOMPLETE AUDIT EVIDENCE =
  demo_media_fallback at the parent (d_fallback_B): terminated at 8363.0 s, no junit
  demo_media_determinism (2 tests): errored in the aggregate shard-2 run at A
    (test_repeated_real_build_identical alone ran 32 457 s); the isolated A/B runs
    (d_det_A 25.3 s, d_det_B 10.0 s) exited 1 with an EMPTY log and NO junit —
    not valid evidence at either commit
  no single uninterrupted full-inventory run exists; the audit PASS was never reached
```

## Failure classification

230 distinct failing node IDs across shards 1-3, the completed part of shard 4 and plan C
(`s4/classification.json`, `s4/classify_p.txt`, plan E):

```
PRE-EXISTING SCALING DEFECTS PROVEN =
  1. website_generation/integration/test_pettripfinder_demo_media*.py real builds:
     4.3-5.1 h and ~45.4 GB peak process commit per module, at BOTH the repair and
     the parent (symmetric table below)
  2. tests/pettripfinder/test_launch_participation_046.py::test_the_bundle_carries_exactly_the_live_set:
     ~2540 s in the aggregate; the isolated batch containing it ran 2605.3 s (A) vs
     2565.3 s (B) at 0.66 GB — same cost at both commits
  3. whole-process growth in the aggregate suite: shard 2 reached 46.86 GB private with
     0.34-0.63 GB free RAM and 2.5-2.8 GB free commit; shard 4 grew to 39.27 GB while
     making no test progress
  plus 225 PRE_EXISTING functional failures (fail at both commits with the same message)
  and 3 ENVIRONMENTAL failures (test_site_enrichment x3: fail only in the aggregate run,
  pass isolated at both commits — plan E re-proved it)

REPAIR-CAUSED FAILURES PROVEN = 0

UNCLASSIFIED FAILURES REMAINING = 2
  tests/website_generation/integration/test_pettripfinder_demo_media_determinism.py::TestDeterminism::test_repeated_real_build_identical
  tests/website_generation/integration/test_pettripfinder_demo_media_determinism.py::TestDeterminism::test_the_two_builds_were_genuinely_independent
  (all 367 shard-4 not-run IDs were later run at A: 356 in plan C + 9 media + 2 fallback;
   demo_media_fallback passed at A but has no parent result)
```

## Symmetric real-build evidence (repair A = `cf73a06d`, parent B = `96564199`)

Each run a separate sequential pytest process, node IDs identical, never two at once
(`C:\t\rfa2\s4\plan_d\status.jsonl`):

| Module (node IDs) | A runtime | B runtime | A peak WS / commit | B peak WS / commit | A | B |
|---|---|---|---|---|---|---|
| `test_pettripfinder_demo_media.py` (9) | 16 533.6 s (4 h 36 m) | 15 608.5 s (4 h 20 m) | 12.561 / 45.398 GB | 13.689 / 45.386 GB | PASS | PASS |
| `test_pettripfinder_demo_media_fallback.py` (2) | 18 337.1 s (5 h 06 m) | ≥ 8 363.0 s, terminated | 12.889 / 45.394 GB | 13.862 / ≥ 31.297 GB | PASS | INCOMPLETE |
| `test_pettripfinder_demo_media_determinism.py` (2) | 32 457 s in shard 2 (errored) | not measured | — | — | ERROR | — |
| plan P batch p3 (61 IDs, incl. launch_participation_046) | 2 605.3 s | 2 565.3 s | 0.658 / 0.679 GB | 0.656 / 0.677 GB | same failures | same failures |

```
PATHOLOGICAL TEST / MODULE = tests/website_generation/integration/test_pettripfinder_demo_media.py
                             (and its siblings _fallback and _determinism: real full-site builds)
REPAIR RUNTIME      = 16 533.6 s
PARENT RUNTIME      = 15 608.5 s
REPAIR PEAK MEMORY  = 12.561 GB working set / 45.398 GB process commit
PARENT PEAK MEMORY  = 13.689 GB working set / 45.386 GB process commit
```

The repair is 5.9 % slower on this module and uses the same memory (commit within 12 MB).
The parent already needs ~4.3 h and ~45 GB for these 9 tests at the current 30-market size,
so the pathological integration cost was PRE-EXISTING, not introduced by this repair. The
fallback module shows the same growth curve at the parent (14.7 → 31.3 GB private in 2 h 19 m,
matching A's curve over the same interval) before it was terminated.

## Safety

```
CURRENT LIVE MODIFIED  = NO
DEPLOYMENT PERFORMED   = NO
COLUMBIA REPLAY STARTED = NO   (only a pre-audit rehearsal ran, on 2026-09-17 in a throwaway
                                worktree; it was not the timed replay and committed nothing)
```

## Closeout statement

1. The bounded factory repair implementation is preserved: `c465fc4f` and `cf73a06d` are
   unchanged on this branch.
2. The focused tests passed: 57 / 57 in the new module (alone and inside the broad shard), and
   every exposed existing module's failure set is identical to the parent's.
3. The required legacy broad migration audit did not complete within the bounded operational
   window: ~44.5 h spent, shard 4 was interrupted, and the determinism and fallback-at-parent
   evidence is missing.
4. The legacy broad suite showed severe scaling and resource problems at the current 30-market
   size: single real-build modules take 4-9 h and ~45 GB, and the aggregate process ran the
   machine down to under 1 GB of free RAM. The parent shows the same costs.
5. This order therefore cannot claim the required migration-audit PASS.
6. The Columbia replay was correctly withheld, because it depends on that PASS.
7. The implementation is NOT approved for production merge from this order.
8. This closeout proposes no further architecture layer.

```
PTF RELEASE FACTORY BOUNDED REPAIR = PAUSED
IMPLEMENTATION PRESERVED = YES
FOCUSED TESTS PASS = YES
BROAD MIGRATION AUDIT PASS = NO
CURRENT LIVE MODIFIED = NO
DEPLOYMENT PERFORMED = NO
COLUMBIA REPLAY STARTED = NO
READY FOR PRODUCTION MERGE = NO
```
