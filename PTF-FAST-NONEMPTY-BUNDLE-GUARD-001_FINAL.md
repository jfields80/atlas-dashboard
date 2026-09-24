# PTF-FAST-NONEMPTY-BUNDLE-GUARD-001 — FINAL

| | |
|---|---|
| Branch | `worker/ptf-fast-nonempty-bundle-guard-001` |
| Base | `origin/worker/ptf-reregistration-lane-repair-001` @ `4cbe6e4c` |
| Scope | FAST rule J fails closed on an empty / HTML-less / missing build output; rule K is NOT ELIGIBLE after it |
| Production files changed | 2 — `scripts/pettripfinder/fast_release_lane.py`, `scripts/pettripfinder/package_staging.py` (one field) |
| Test files changed | 1 new — `tests/pettripfinder/test_ptf_fast_nonempty_bundle_guard_001.py` (27 tests) |
| Market / participation / authorization / deployment data | untouched |
| Deployment | none |

## Phase 1 — The defect, reproduced (untouched base, synthetic)

`scratchpad/repro_empty_bundle.py` ran the REAL lane over the sealed Dayton withdrawal
package (the ATLAS-THROUGHPUT-003 fixture) with no production assembly.

| Case | J | file / html | bundle | K | ELIGIBLE |
|---|---|---|---|---|---|
| synthetic builder that collects nothing | **PASS** | 0 / 0 | `e3b0c44298fc1c14…` | **PASS BYTE_IDENTICAL** (a = b = `e3b0c442…`) | **YES** |
| real `build_changed_market`, relative `--work data/fast_work/w` | **PASS** | 0 / 0 | `e3b0c44298fc1c14…` | **PASS BYTE_IDENTICAL** | **YES** |
| real `build_changed_market`, absolute `--work` | PASS | 2 / 1 | `3b0b4ddf…` | PASS BYTE_IDENTICAL | YES |

Why it happens:

* `package_staging.overlay` points `assemble_netlify_bundle.REPO_ROOT` at the stage
  directory. With a relative work dir the stage is relative too, so
  `validate_output_path("…/oa")` joins it under the stage — the site was written to
  `…\data\fast_work\w\sa\data\fast_work\w\oa\site` (the West Palm Beach doubled path).
* The collector reads `<work>/oa/site`, which does not exist; `Path.rglob` on a missing
  directory yields nothing, so `file_hashes` = `{}` and `bundle_digest({})` = sha256 of the
  empty string.
* Rule J only checked assembler gates and that the build ran cold — nothing about output
  size. Rule K compared two empty bundles, and they are always byte-identical.

**Side finding (not changed — it is a committed market receipt):**
`launch_packages/pettripfinder/markets/receipts/augusta-ga/pkg-augusta-ga-14806eca154760a0-5f8116aa….json`
records J PASS with `file_count 0`, `html_count 0`, bundle `e3b0c442…`, K PASS and
`FAST_DATA_ONLY_RELEASE_ELIGIBLE = YES`. That is the same vacuous pattern. The other 22
committed receipts all have non-zero counts. Augusta's live site comes from the whole-site
assembler, not from this bundle, so it is not affected, but its FAST receipt proves nothing
about the build. Re-sealing that receipt needs its own order.

## Phase 2 — The contract

The code and docs agree on what rule J is for: *"J changed market builds — the real
per-market assembler, staged"* (module docstring), and *"changed-market artifact builds
successfully"* (`RULES`). The J detail already reports `file_count`, `html_count` and
`bundle_sha256`, taken from the real `site/` collector. No existing contract sets a
minimum size, so none was added. The rule proves the output is **non-empty**, not that the
market has a particular size:

* the collected `site/` output root exists (`MISSING_BUILD_OUTPUT`)
* `file_count` is a positive integer and the bundle is not the empty-content identity (`EMPTY_BUNDLE`)
* `html_count` is a positive integer (`NO_HTML_OUTPUT`) — not required of a cached
  bundle, because its record has no HTML count

A count that is missing or not a positive integer (`None`, `"3"`, `3.0`, `True`, `-1`) is
treated as a defect (fail closed).

## Phase 3 — Rule J fix

`fast_release_lane.bundle_output_defects(build, require_html=True)` returns
`"CODE: detail"` problems in a fixed order (MISSING_BUILD_OUTPUT, EMPTY_BUNDLE,
NO_HTML_OUTPUT). The codes are module constants, alongside
`EMPTY_BUNDLE_SHA256 = sha256(b"")`. Both J paths add its problems:

* cold path: `problems += bundle_output_defects(build_a)`. J detail gains
  `output_present` and `output_defects`.
* cache path: `bundle_output_defects(cached, require_html="html_count" in cached)`. J detail
  gains `output_defects`.

`package_staging.build_changed_market` adds one field: `output_present = site_dir.is_dir()`.
No path is resolved differently or substituted. The relative-path join itself is unchanged;
it is now refused instead of passed.

## Phase 4 — Rule K dependency

This follows the lane's existing convention for a failed prerequisite: rule A failing makes
the other rules UNKNOWN, "not evaluated". If J reports output defects, K is **UNKNOWN**
with `blocked_by: "J"` and the problem *"rule J did not prove a non-empty build output
(…); determinism not evaluated"*. The second cold build is **not run**. This applies to
the cache path too: a cached empty bundle cannot inherit a BYTE_IDENTICAL receipt. As
defence in depth, an empty second build also adds `second build: <CODE>` problems. K's own
digest comparison is unchanged. UNKNOWN already makes the package NOT ELIGIBLE.

After the fix, the same reproduction gives:

| Case | J | J problems | K | ELIGIBLE |
|---|---|---|---|---|
| synthetic empty | **FAIL** | EMPTY_BUNDLE, NO_HTML_OUTPUT | **UNKNOWN** (blocked by J) | **NO** |
| relative `--work` | **FAIL** | MISSING_BUILD_OUTPUT, EMPTY_BUNDLE, NO_HTML_OUTPUT | **UNKNOWN** | **NO** |
| absolute `--work` | PASS | — | PASS BYTE_IDENTICAL | YES |

## Phases 5–6 — Focused tests (`test_ptf_fast_nonempty_bundle_guard_001.py`, 27)

| # | Required case | Test(s) |
|---|---|---|
| 1 | zero-file bundle rejected | `test_1_a_zero_file_bundle_fails_rule_j`, `test_zero_files_is_an_empty_bundle` |
| 2 | zero-HTML bundle rejected | `test_2_a_bundle_with_no_html_fails_rule_j`, `test_files_without_html_is_no_html_output` |
| 3 | missing output directory rejected | `test_3_a_build_that_writes_no_output_root_fails_rule_j` (real staged build), `test_an_absent_output_root_is_missing_build_output` |
| 4 | relative work path → empty collection rejected | `test_4_a_relative_work_path_that_collects_nothing_is_refused` — asserts the doubled write path `…/w/sa/data/fast_work/w/oa/site`, then J FAIL, K UNKNOWN, NOT ELIGIBLE |
| 5 | two empty builds cannot satisfy determinism | `test_5_two_empty_builds_never_satisfy_determinism`, `test_a_cached_empty_bundle_cannot_pass_j_or_inherit_determinism` |
| 6 | valid non-empty bundle passes | `test_6_a_valid_non_empty_bundle_passes_rule_j`, `test_an_absolute_work_path_builds_and_proves_determinism` |
| 7 | two identical non-empty builds deterministic | `test_7_two_identical_non_empty_builds_are_deterministic` |
| 8 | differing builds fail | `test_8_two_differing_builds_fail_determinism`, `test_an_empty_second_build_fails_determinism_with_its_own_diagnostic` |
| 9 | diagnostics deterministic | `test_9_the_empty_bundle_diagnostics_are_deterministic`, `test_the_diagnostics_are_deterministic` |
| — | fail-closed counts, empty digest, cache shape, no market special case, staging field | 5 parametrised + 4 more |

At the untouched base the module gives **24 failed / 3 passed**. The 3 that pass are
cases 7, 8 and 9: their behaviour is meant to stay the same. 6 of the base failures are
behavioural (`'PASS' == 'FAIL'`: J passed an empty, relative-path or cached-empty output).
The rest fail because the new names or field do not exist at the base.

## Phase 7 — Targeted existing tests (one pytest process)

`tests/pettripfinder/test_atlas_throughput_003.py` (the lane and its J/K tests, including
the `slow` real cold-build determinism case 15), `test_atlas_throughput_004.py` (the
bundle-cache J/K path and the builder, including the real cold→warm builds), and the new
module.

| | |
|---|---|
| COLLECTED | 138 |
| PASSED | 137 |
| FAILED | 1 |
| SKIPPED | 0 |
| RUNTIME | 590.2 s |
| PEAK MEMORY | 137.6 MB working set (`throughput_profile.peak_working_set_mb`) |

Not run (as ordered): broad regression, `test_factory_throughput_001.py`, demo-media,
whole-site assembly, and unrelated market tests.

## Phase 8 — Differential

| Node | At base `4cbe6e4c` | Class |
|---|---|---|
| `test_atlas_throughput_004.py::TestBoundaries::test_the_fast_lane_reports_market_build_required_no_on_a_trusted_bundle` | same failure, `AssertionError: N` | **PRE_EXISTING** |

The failing assertion is rule **N**: the Dayton fixture's parent live state is older than the
current live release. J and K pass in that test with the new guard (J PASS, cache HIT; K
PASS inherited).

REPAIR_CAUSED = 0 · UNRESOLVED = 0 · CURRENT_REAL_DEFECT = 0 in scope. The Augusta
receipt above is reported, not repaired.

## Phase 9 — Zero production delta

`git status` shows only the two FAST modules, the new test module and this report. The
reproduction and verification scripts wrote only to temp dirs and the session scratchpad.

MARKET DATA CHANGED = NO · PARTICIPATION CHANGED = NO · AUTHORIZATION DATA CHANGED = NO ·
DEPLOYMENT RECORDS CHANGED = NO · CURRENT LIVE MODIFIED = NO · DEPLOYMENT PERFORMED = NO

`bundle_cache` hashes `package_staging.py` and `fast_release_lane.py` from the declared
closure **at runtime**; there is no committed digest pin. Existing persistent cache keys
built with the old bytes will miss and rebuild. That is the correct behaviour.

## Phase 10 — Current live (read-only)

| | |
|---|---|
| `resolve_current_live_source` | RESOLVED YES, 0 problems, lineage `e82120cc`, built from `0cc2817b`, head contains live |
| Deployment | `6ab1a035c7ef3b14a23a4ec6` (rollback `6ab071a5b7561c33aff6c17b`) — unchanged |
| Markets / profiles | 32 / 2375 |
| Release-index routes | 2646 |
| Served routes | 2711 (`<loc>` count on the host) |
| Bundle / sitemap | `0ec5c655…` / `e81961ae…` |
| Host verification | PASS — served sitemap sha256 = record's `e81961ae…` |
| Fort Lauderdale | participating; hub HTTP 200; 97 sitemap URLs |
| Detroit | withheld; hub HTTP 404; 0 sitemap URLs |
| West Palm Beach | not live; hub 404; 0 sitemap URLs |

## Final answers

1. EMPTY BUNDLE DEFECT REPRODUCED = YES (synthetic and real relative-path overlay join; both ELIGIBLE YES at base)
2. OLD RULE J EMPTY RESULT = PASS
3. NEW RULE J EMPTY RESULT = FAIL (EMPTY_BUNDLE / NO_HTML_OUTPUT / MISSING_BUILD_OUTPUT)
4. ZERO FILES REJECTED = YES
5. ZERO HTML REJECTED = YES
6. MISSING OUTPUT REJECTED = YES
7. RELATIVE PATH EMPTY COLLECTION REJECTED = YES
8. RULE K CAN PASS AFTER J EMPTY FAILURE = NO (UNKNOWN, blocked_by J; second build not run)
9. VALID NONEMPTY BUILD PASSES = YES
10. VALID BYTE-IDENTICAL BUILDS PASS = YES (synthetic, and the real cold-build case 15)
11. DIFFERING BUILDS FAIL = YES
12. NEGATIVE CASES = 9 required cases covered by 27 focused tests
13. FOCUSED TESTS COLLECTED = 138
14. FOCUSED TESTS PASSED = 137
15. FOCUSED TESTS FAILED = 1 (PRE_EXISTING, rule N stale parent)
16. REPAIR_CAUSED FAILURES = 0
17. UNRESOLVED = 0
18. PRODUCTION FILES CHANGED = 2 (`fast_release_lane.py`, `package_staging.py`)
19. TEST FILES CHANGED = 1 (new)
20. MARKET DATA CHANGED = NO
21. PARTICIPATION DATA CHANGED = NO
22. AUTHORIZATION DATA CHANGED = NO
23. DEPLOYMENT RECORDS CHANGED = NO
24. CURRENT LIVE MODIFIED = NO
25. DEPLOYMENT PERFORMED = NO
26. READY FOR WEST PALM BEACH INTEGRATION = YES — the guard is ready to merge under West Palm Beach's re-registration. Its own blockers (correction 004 and the re-registration lane) are separate.

PTF FAST NONEMPTY BUNDLE GUARD = PASS
EMPTY BUNDLE CAN PASS FAST = NO
VACUOUS DETERMINISM CAN PASS = NO
REPAIR-CAUSED FAILURES = 0
CURRENT LIVE MODIFIED = NO
DEPLOYMENT PERFORMED = NO
READY FOR WEST PALM BEACH INTEGRATION = YES
