# PTF-RELEASE-FACTORY-DETERMINISM-DIFFERENTIAL-CLOSURE-003 — FINAL

Branch `worker/ptf-release-factory-efficiency-audit-001`, worktree `C:\Atlas-PTF-Release-Audit`.
This order closes the one unclassified differential left by
PTF-RELEASE-FACTORY-EFFICIENCY-BOUNDED-REPAIR-002 (the two `demo_media_determinism` tests).
The broad migration audit stayed closed. Nothing else was run: no shard, no demo_media or
fallback module, no Columbia replay, no registration and no deployment. No production code
changed.

Artifacts (runner, probe plugin, logs, memory samples, result JSON, status stream):
`PTF-RELEASE-FACTORY-DETERMINISM-DIFFERENTIAL-CLOSURE-003_artifacts/`.

## Phase 1 — the exact two tests

Recovered from `C:\t\rfa2\s4\plan_d_ids\det.txt`. They match the 2 UNCLASSIFIED rows of
the 002 closeout. **TEST COUNT = 2.**

```
T1 tests/website_generation/integration/test_pettripfinder_demo_media_determinism.py::TestDeterminism::test_repeated_real_build_identical
T2 tests/website_generation/integration/test_pettripfinder_demo_media_determinism.py::TestDeterminism::test_the_two_builds_were_genuinely_independent
```

Both tests read ONE module-scoped fixture, `independent_pair`, which calls `real_chain()`
twice (two cold builds). Running each test alone would build that pair twice and give no
extra information, so each commit ran both IDs in ONE process with identical ordering.

## Phase 2 — isolated worktrees

| | Repair (A) | Parent (B) |
|---|---|---|
| Path | `C:\t\rfd3a` (detached) | `C:\t\rfd3b` (detached) |
| HEAD | `cf73a06d1b6f3fe83dcdb8363da047735d14d82f` | `9656419918229db7a0eb5ca5a1b4fb514e0e9c34` |
| Tree clean (before and after) | YES / YES | YES / YES |
| Python / pytest | 3.13.5 / 9.1.1, same interpreter | same |
| Collect-only of the 2 IDs | 2 collected | 2 collected |

Environment inputs:
- `git diff 96564199 cf73a06d` touches exactly 7 files: the 6 release-factory modules under
  `scripts/pettripfinder/` plus the repair's own test module.
- The test file and `pettripfinder_demo_chain.py` have the same blob at both commits
  (`f80125c2…` and `ce06d04a…`).
- The demo chain's import closure contains none of the 6 changed modules.
  - This was checked statically at A.
  - The runtime probe's session-end record was lost because both processes were killed at
    the cap.

## Phase 3 — resource baselines

| | A (repair) | B (parent) |
|---|---|---|
| Start | 2026-09-19T07:43:38 | 2026-09-19T08:44:31 |
| Free RAM | 7.692 GB of 15.886 | 11.105 GB of 15.886 |
| Commit limit / free commit | 63.884 / 49.705 GB | 63.884 / 50.341 GB |
| CPU / load | i7-6700, 8 logical, 18 % | i7-6700, 8 logical, 38 % |
| Python | 3.13.5 | 3.13.5 |

Only one test process ran at a time. B started only after A's process tree was killed and
reaped, and no other pytest was running before either run.

## Phases 4–5 — bounded runs (identical argv, env, order, cap)

```
python -u -m pytest <T1> <T2> -vv -rA -p no:cacheprovider -p det_probe
       -o faulthandler_timeout=3300 -o junit_family=xunit2 --junitxml=<run>.xml --durations=0
hard cap 3600 s (process tree killed), commit guard 3 GB, memory sampled every 15 s, no retry
```

| | A (repair) | B (parent) |
|---|---|---|
| Outcome | **TIMEOUT** (killed at 3600.3 s) | **TIMEOUT** (killed at 3600.3 s) |
| Wall seconds incl. kill + reap | 3648.4 | 3602.4 |
| Exit code | 1 | 1 |
| Phase reached | T1 fixture setup, first build (`real_chain(root / "a")`) | same |
| T1 assertion reached | NO | NO |
| T2 started | NO | NO |
| junit written | NO | NO |
| Faulthandler dump at 55:00 | `layout_engine.py:271 <genexpr>` ← `:270 compose` ← `pettripfinder_demo_chain.py:139 real_chain` ← `test_…_determinism.py:47 independent_pair` | **identical** 45-frame stack after path normalization (`diff` empty) |
| Peak working set | 12.698 GB | 12.761 GB |
| Peak commit | 21.989 GB | 23.576 GB |
| Min system free commit | 28.16 GB | 27.145 GB |
| Log sha256 | `34f66427…c5a6af` | `909d86cd…1eab4f` |

Memory curve (process private GB, 5-minute marks):

| s | 300 | 600 | 900 | 1200 | 1500 | 1800 | 2100 | 2400 | 2700 | 3000 | 3300 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 8.8 | 14.1 | 14.7 | 17.9 | 18.1 | 19.2 | 19.2 | 19.2 | 19.2 | 22.0 | 22.0 |
| B | 16.6 | 17.9 | 19.0 | 19.2 | 19.2 | 19.2 | 22.0 | 22.0 | 22.0 | 22.0 | 23.3 |

Both runs climb the same staircase to the same plateaus (19.2 → 22.0 GB). The parent gets
there earlier and ends higher. The repair is not worse on any measure.

Inherited context (002): in the aggregate shard-2 run at A, both tests errored in fixture
setup with `MemoryError` (`json/encoder.py:261`) after 32 457 s. That run had 46.86 GB private
and under 1 GB free RAM. Bounded at 60 minutes, both commits show the same precondition: the
same code path with the same unbounded memory growth, inside a single build.

## Phase 6 — differential classification

| TEST NODE | REPAIR RESULT | PARENT RESULT | REPAIR RUNTIME | PARENT RUNTIME | REPAIR MEMORY (peak WS / commit) | PARENT MEMORY (peak WS / commit) | CLASSIFICATION |
|---|---|---|---|---|---|---|---|
| T1 `…::test_repeated_real_build_identical` | TIMEOUT in fixture setup (first build) | TIMEOUT in fixture setup (first build) | ≥ 3600 s (capped) | ≥ 3600 s (capped) | 12.698 / 21.989 GB | 12.761 / 23.576 GB | **PRE_EXISTING** |
| T2 `…::test_the_two_builds_were_genuinely_independent` | not started (blocked behind the shared fixture) | not started (same) | 0 s (never started) | 0 s (never started) | shared process | shared process | **PRE_EXISTING** |

Why these are PRE_EXISTING:
- Every compared dimension matches materially: result class (TIMEOUT), exit code (1), error
  point (identical faulthandler stack), runtime (cap at both), and memory behavior (same
  staircase, parent slightly worse).
- The parent does not pass or behave better, so the REPAIR_CAUSED condition is not met.
- The evidence does distinguish the two cases and shows they are indistinguishable, so this
  is not UNRESOLVED.
- The code under test is byte-identical at both commits and reaches none of the changed
  modules.

What this does NOT claim:
- Neither commit reached the determinism assertions. No timeout or kill is counted as a PASS.
- Whether the real build is deterministic remains unverified at BOTH commits.
- The classification covers only the repair-vs-parent differential. The underlying defect is
  a pre-existing real-build resource defect: over 1 hour and more than 22 GB for one build,
  which reaches `MemoryError` at 30 markets.

## Phase 7 — acceptance

```
REPAIR_CAUSED = 0
UNRESOLVED    = 0
PRE_EXISTING  = 2
DIFFERENTIAL CLOSURE = PASS
```

## Inherited evidence

```
FOCUSED TESTS                     = 57/57 PASS
PREVIOUS REPAIR-CAUSED FAILURES   = 0
PREVIOUS BROAD AUDIT              = INCOMPLETE
CURRENT LIVE MODIFIED             = NO
DEPLOYMENT PERFORMED              = NO
COLUMBIA REPLAY STARTED           = NO
PRODUCTION CODE CHANGED           = NO
```

```
PTF DETERMINISM DIFFERENTIAL CLOSURE = PASS
REPAIR-CAUSED FAILURES = 0
UNRESOLVED = 0
CURRENT LIVE MODIFIED = NO
DEPLOYMENT PERFORMED = NO
READY FOR BOUNDED MIGRATION DECISION = YES
```
