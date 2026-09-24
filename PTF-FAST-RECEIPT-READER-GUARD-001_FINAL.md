# PTF-FAST-RECEIPT-READER-GUARD-001 — FINAL

| | |
|---|---|
| Worktree | `C:\Atlas-PTF-FAST-Receipt-Reader-Guard` |
| Branch | `worker/ptf-fast-receipt-reader-guard-001` |
| Base | `origin/worker/ptf-fast-nonempty-bundle-guard-001` = `f182cc08` (verified, HEAD == base at start, tree clean) |
| Production files changed | 1 — `scripts/pettripfinder/fast_release_lane.py` (+24/−3) |
| Test files changed | 1 new (`test_ptf_fast_receipt_reader_guard_001.py`, 30 tests) + 1 fixture update (`test_atlas_throughput_003.py`, +4) |
| Data / authorization / deployment files changed | 0 |

## Phase 1 — Base and current live (read-only)

`release_index.resolve_current_live_source(verify_host=…)`: **RESOLVED YES, 0 problems, host verified**.

| | |
|---|---|
| Live lineage commit | `e82120cc` (built from `0cc2817b`); HEAD contains live |
| Deployment | `6ab1a035c7ef3b14a23a4ec6` (rollback `6ab071a5b7561c33aff6c17b`) |
| Markets / profiles | 32 / 2375 |
| Release-index routes | 2646 (participating markets' `MarketIndex.routes`) |
| Served routes | 2711 (`<loc>` count of the host sitemap) |
| Bundle / sitemap | `0ec5c655…` / `e81961ae…` (served sitemap hashes to the record's) |

CURRENT LIVE MODIFIED = NO.

## Phase 2 — The reader defect, reproduced at base

Real receipt, read only:
`launch_packages/pettripfinder/markets/receipts/augusta-ga/pkg-augusta-ga-14806eca154760a0-5f8116aaecd97d09.json`
(file sha256 `a2e22ce8ca4f74e1…`, `RECEIPT_DIGEST` `sha256:5f8116aaecd97d09…`).

```
OLD RECEIPT: J PASS  file_count 0  html_count 0  bundle e3b0c442…  K PASS  ELIGIBLE YES
eligible_receipts("augusta-ga", sha256:14806eca…)  ->  [pkg-augusta-ga-14806eca154760a0-5f8116aaecd97d09.json]
bundle_output_defects(J.detail)                     ->  [EMPTY_BUNDLE, NO_HTML_OUTPUT]
```

The same file copied into a synthetic receipts directory also came back ELIGIBLE.

**Why.** At base, `fast_release_lane.eligible_receipts` (line 798) filters only on `schema`,
`PACKAGE_DIGEST`, the stored `FAST_DATA_ONLY_RELEASE_ELIGIBLE == YES` and an empty
`UNKNOWN_RULES`. It never looks at `RESULTS.J.detail`. `bundle_output_defects` (line 130) runs
only on the write path, in `run_fast_lane`'s rule J (lines 479 and 523) and the second build in K
(line 562). So a verdict stored by the old lane was trusted as it stood.

Call path: `release_coordinator.bound_fast_receipt` / `registration_data_only.check_fast_receipt` /
`regression_delta.fast_data_only_release` → `FL.eligible_receipts(...)` → `paths[-1]`.

## Phase 3 — Call-site audit (before editing)

| Caller | Use | Class |
|---|---|---|
| `release_coordinator.bound_fast_receipt` (1177) | the receipt a staging pass re-uses instead of re-running A–O | CURRENT CANDIDATE ELIGIBILITY |
| `registration_data_only.check_fast_receipt` (1958) | the registration lane's `fast_receipt` check | CURRENT CANDIDATE ELIGIBILITY |
| `regression_delta.fast_data_only_release` (1515) | whether a FAST receipt can lift the broad regression | CURRENT CANDIDATE ELIGIBILITY |
| `lexington_ky_authorization_packet_005.main` (95) | one-shot packet generator (historical, 2026) | OTHER (historical one-shot script; Lexington's receipt is non-empty, so it is unaffected) |
| `lexington_ky_reauthorization_packet_004.main` (108) | one-shot packet generator (historical) | OTHER (same) |
| `test_atlas_throughput_003` (930), `test_lexington_ky_launch_halt_004` (195) | assertions over committed receipts | REPORTING (tests) |

Equivalent selection helpers: none. `sealed_market_package.list_packages` globs *packages*, not
receipts. The `shadow_receipts/` directories are only written (`FL.write_receipt(…, STAGING / "shadow_receipts")`)
and never read by any selector.

Historical verification: `deployment_authorization.verify_authorization`,
`global_deployment` and `release_index.current_verified_live` contain **no** reference to
receipts (`grep -c receipt` = 0 in each). The supersessions/deployment-record contract tests
(`contracts/test_market_state_pins.py`, `pins/supersessions.json`) also have 0 references.

```
CALLERS                         = 5 production (+2 test sites)
CURRENT-SELECTION CALLERS       = 3 (bound_fast_receipt, check_fast_receipt, fast_data_only_release)
HISTORICAL-VERIFICATION CALLERS = 0
```

So the reader can be tightened without making any historical authorization unverifiable. No
new historical/current split was needed in production code (Phase 5).

## Phase 4 — Semantics

- **CURRENT ELIGIBILITY** (`eligible_receipts`): the stored verdict must say ELIGIBLE, **and**
  `receipt_output_defects(receipt)` must be empty. That applies the writer's own
  `bundle_output_defects` to the stored rule J detail. It rejects `file_count` ≤ 0, missing,
  non-int or bool; a bundle equal to `e3b0c442…` (bare or `sha256:`-prefixed); `html_count`
  ≤ 0, missing or non-int; `output_present is False`; and a missing J, empty detail or
  non-mapping detail.
- `html_count` is required unless the detail is a cached-bundle detail (`cache_status`). That is
  exactly what the writer does: its cache path records no HTML count and does not require one.
- **HISTORICAL REFERENCE**: the bytes exist, they hash to their own `RECEIPT_DIGEST`, and the
  authorization packet binds that digest and that package. Today's eligibility rules do not apply.
- The receipt is never mutated, and its stored `J PASS / ELIGIBLE YES` is untouched. It is
  classified as **HISTORICAL RECEIPT PRESERVED, CURRENT ELIGIBILITY = NO**.

## Phase 5 — Historical authorization preservation

The chain, verified by `TestAugustaHistoricalReceipt`:

`ptf-auth-augusta-006-55e0f5bbf02a` (DEPLOYED, listed by `DA.list_authorizations`, present in
`pins/supersessions.json`) → its `authorization_source` names
`reports/augusta_ga_founder_authorization_packet_005.json` (present) →
`the_digests_this_authorization_binds.validation_receipt_digest` =
`sha256:5f8116aaecd97d09…` = the receipt's `RECEIPT_DIGEST` = its recomputed self-digest. The
packet's `sealed_package_id` and `sealed_package_digest` equal the receipt's. Deployment record
`ptf-deploy-augusta-006-6aaeb3b7…` is DEPLOYED, names the same authorization and has the same
bundle `55e0f5bb…`.

`verify_authorization` never reads a receipt, so it needed no change.
`contracts/test_market_state_pins.py` (supersession chain and deployment records) passes in full.

## Phase 6 — Implementation

`fast_release_lane.py`:

- new `receipt_output_defects(receipt)`: reads `RESULTS.J.detail` and calls
  `bundle_output_defects(detail, require_html="cache_status" not in detail)`. There is **no
  second copy** of the non-empty rules.
- `eligible_receipts` adds `and not receipt_output_defects(doc)` to its existing filter.
- `receipt_output_defects` is exported in `__all__`.

Unchanged: receipt storage, schema, file naming, the `sorted()` order, and every caller's
`paths[-1]`. Because the filter runs before callers pick `[-1]`, an ineligible file cannot be the
lexicographically last candidate. No CORRECTS/supersession mechanics were added.

## Phase 7 — Augusta proof

```
OLD RECEIPT BYTES CHANGED                        = NO  (sha256 a2e22ce8… before and after)
OLD RECEIPT DIGEST CHANGED                       = NO  (sha256:5f8116aaecd97d09…)
HISTORICAL AUTHORIZATION VERIFICATION            = PASS
CURRENT eligible_receipts INCLUDES VACUOUS RECEIPT = NO   ( -> [] )
REASON = EMPTY_BUNDLE: the bundle contains no files (file_count 0, bundle e3b0c44298fc1c14)
         NO_HTML_OUTPUT: the bundle contains no HTML (html_count 0)
```

`bound_fast_receipt(augusta package)` → `RECEIPT_NOT_BOUND`; `check_fast_receipt` → FAIL "no
committed receipt says FAST_DATA_ONLY_RELEASE_ELIGIBLE = YES". Of the 23 committed receipts, 22
stay current-eligible and **only** Augusta's is withdrawn.

For information: all 5 Augusta *shadow* receipts and 1 Fort Lauderdale shadow receipt under
`markets/staging/*/shadow_receipts/` are also vacuous. No selector reads them. They were not
touched.

## Phase 8 — Focused tests (`test_ptf_fast_receipt_reader_guard_001.py`, 30)

| # | Required case | Test(s) |
|---|---|---|
| 1 | PASS receipt, 0 files | `test_zero_files_is_not_current_eligible` |
| 2 | PASS receipt, 0 HTML | `test_zero_html_is_not_current_eligible` |
| 3 | missing / invalid count | `test_a_missing_or_invalid_count_is_not_current_eligible` ×11 (missing, string, bool, negative, null file_count; missing, float html_count; output absent; empty detail; non-mapping detail; no rule J) |
| 4 | e3b0c442 bundle | `test_the_empty_string_bundle_cannot_qualify_even_with_counts` |
| 5 | valid receipt stays eligible | `test_a_valid_non_empty_receipt_remains_eligible`, `test_a_cached_bundle_receipt_needs_no_html_count_like_the_writer`, `test_the_pre_existing_filters_still_apply` |
| 6 | invalid later receipt cannot displace valid | `test_an_invalid_lexicographically_later_receipt_cannot_displace_a_valid_one`, `test_only_invalid_receipts_selects_nothing` |
| 7 | multiple valid keep sorted order | `test_several_valid_receipts_keep_the_existing_sorted_order` |
| 8 | historical digest/reference still verifies | `test_the_committed_receipt_bytes_are_the_historical_bytes`, `test_the_historical_reference_still_verifies` |
| 9 | historical authorization verifiable | `test_the_historical_authorization_chain_remains_verifiable`, `test_historical_verification_never_consults_current_receipt_eligibility` |
| 10 | current selection does not use it | `test_the_vacuous_receipt_is_not_current_eligible`, `test_current_candidate_selection_does_not_use_it`, `test_every_other_committed_receipt_stays_current_eligible` |
| 11 | no mutation | `test_reading_never_mutates_a_receipt` |
| 12 | deterministic diagnostics | `test_the_same_receipt_always_gives_the_same_defects_in_the_same_order`, `test_the_reader_reuses_the_writers_rule_not_a_copy` |

At base `f182cc08` the module gives **25 failed / 5 passed**. The 5 that pass are the
history-preservation tests (8, 9), which must hold both before and after. The Augusta-selection,
displacement and candidate-selection failures are behavioural. The rest fail because
`receipt_output_defects` does not exist at base.

## Phase 9 — Targeted tests (one pytest process, detached)

Modules: the new module; `test_ptf_fast_nonempty_bundle_guard_001.py` (rule J writer);
`test_atlas_throughput_003.py` (the lane, J/K, the committed-pilot `eligible_receipts` caller);
`test_lexington_ky_launch_halt_004.py` (caller over a real committed receipt);
`contracts/test_market_state_pins.py` (historical authorization / supersession / deployment-record
chain); and `test_release_factory_bounded_repair_002.py::TestTheNarrowLaneRejects::test_a_stale_or_mismatched_receipt`
(`bound_fast_receipt` + `check_fast_receipt`).

| | |
|---|---|
| COLLECTED | 373 |
| PASSED | 368 |
| FAILED | 0 |
| SKIPPED | 5 (pre-existing `SUPERSEDED by PTF-LEXINGTON-KY-…-006` markers in the Lexington halt module) |
| RUNTIME | 286.8 s |
| PEAK MEMORY | 134.5 MB working set (`throughput_profile.peak_working_set_mb`) |

Not run, as ordered: broad regression, `test_factory_throughput_001.py`, demo-media, whole-site
assembly, the `registration_data_only` real-tree suite (its `TestBinding` receipt variants copy a
real non-empty receipt, so no J count changes), `test_atlas_throughput_004.py` (the bundle-cache
*writer* path, not changed here), and unrelated market tests. The repo `CLAUDE.md` asks for full
regression before a commit; this work order and the standing rule forbid a broad run, so the order
governs.

## Phase 10 — Differential

The first targeted run (367 passed / 1 failed / 5 skipped, 288.8 s, 136.1 MB) failed one node:

| Node | At base `f182cc08` | Class | Resolution |
|---|---|---|---|
| `test_atlas_throughput_003.py::TestRegressionV2Extension::test_the_fast_requirement_fails_closed_without_a_package_receipt_or_activation` | PASS (167.9 s) | **REPAIR_CAUSED** (fixture) | fixture updated |

Cause: the test forges an "ELIGIBLE" receipt by flipping the flag on a lane receipt run with
`build=False`. Its J is UNKNOWN with an **empty** detail, which is exactly the vacuous shape the
reader must now refuse. The node exists to prove that a DISABLED activation keeps the broad
regression required even with an eligible receipt. The fixture now carries a non-empty J detail
(`file_count 3`, `html_count 2`, a non-empty bundle), as any real eligible receipt must. The reader
was not loosened. After the change, the rerun above is 0 failed.

```
PRE_EXISTING = 0   REPAIR_CAUSED (open) = 0   CURRENT_REAL_DEFECT = 0   UNRESOLVED = 0
```

## Phase 11 — Zero production delta

`git diff --stat f182cc08`: `fast_release_lane.py`, `test_atlas_throughput_003.py`, plus the new
test module and this report. `git diff f182cc08 -- atlas-dashboard/launch_packages atlas-dashboard/deploy`
is empty.

AUGUSTA RECEIPT BYTES CHANGED = NO · AUGUSTA MARKET DATA CHANGED = NO · OTHER MARKET DATA CHANGED = NO ·
PARTICIPATION CHANGED = NO · AUTHORIZATION RECORDS CHANGED = NO · DEPLOYMENT RECORDS CHANGED = NO ·
CURRENT LIVE MODIFIED = NO · DEPLOYMENT PERFORMED = NO

The temporary base worktree (`C:\t\rrgb`) was removed. Scripts and outputs went only to the
session scratchpad.

## Phase 12 — Current live re-verified (read-only)

| | |
|---|---|
| Resolver | RESOLVED YES, 0 problems, host verified, lineage `e82120cc` |
| Deployment | `6ab1a035c7ef3b14a23a4ec6`, unchanged |
| Markets / profiles | 32 / 2375 |
| Release-index routes | 2646 |
| Served routes | 2711 |
| Host sitemap | HTTP 200, sha256 `e81961ae…`, unchanged |
| Augusta | participating; hub `/pet-friendly-hotels/augusta-ga/` 200; 17 sitemap URLs |
| Fort Lauderdale | participating; hub 200; 97 sitemap URLs |
| Detroit | withheld; hub 404; 0 sitemap URLs |
| West Palm Beach | not live; hub 404; 0 sitemap URLs |

## Final answers

1. READER DEFECT REPRODUCED = YES (real Augusta receipt and a synthetic copy, both ELIGIBLE at base)
2. AUGUSTA OLD RECEIPT PRESERVED = YES
3. AUGUSTA OLD RECEIPT DIGEST PRESERVED = YES (`sha256:5f8116aaecd97d09…`; file sha256 `a2e22ce8…`)
4. OLD VACUOUS RECEIPT CURRENTLY ELIGIBLE BEFORE = YES
5. OLD VACUOUS RECEIPT CURRENTLY ELIGIBLE AFTER = NO (EMPTY_BUNDLE, NO_HTML_OUTPUT)
6. READER USES NONEMPTY VALIDATION = YES (`receipt_output_defects` → the writer's `bundle_output_defects`; no copy)
7. HISTORICAL AUTH VERIFICATION SEMANTICS = bytes present + self-digest == packet-bound digest + package binding; independent of current eligibility (0 historical verifiers call the reader)
8. CURRENT ELIGIBILITY SEMANTICS = stored ELIGIBLE YES, no UNKNOWN rules, AND rule J detail passes today's non-empty-output rule
9. AUGUSTA HISTORICAL AUTH STILL VALID = YES
10. MULTIPLE RECEIPT SELECTION SAFE = YES (filter runs before `[-1]`; sorted order kept among eligible receipts)
11. INVALID LATER RECEIPT CAN DISPLACE VALID = NO
12. NEGATIVE CASES = 12 required cases covered by 30 focused tests
13. TARGETED TESTS COLLECTED = 373
14. TARGETED TESTS PASSED = 368 (5 pre-existing SUPERSEDED skips)
15. TARGETED TESTS FAILED = 0
16. REPAIR_CAUSED FAILURES = 0 (1 found in the first run: a vacuous synthetic fixture, fixed at the fixture)
17. UNRESOLVED = 0
18. PRODUCTION FILES CHANGED = 1 (`fast_release_lane.py`)
19. TEST FILES CHANGED = 2 (1 new, 1 fixture update)
20. AUGUSTA RECEIPT CHANGED = NO
21. MARKET DATA CHANGED = NO
22. PARTICIPATION DATA CHANGED = NO
23. AUTHORIZATION DATA CHANGED = NO
24. DEPLOYMENT RECORDS CHANGED = NO
25. CURRENT LIVE MODIFIED = NO
26. DEPLOYMENT PERFORMED = NO
27. READY TO RETURN TO WEST PALM BEACH = YES

PTF FAST RECEIPT READER GUARD = PASS
VACUOUS AUGUSTA RECEIPT CURRENTLY ELIGIBLE = NO
HISTORICAL AUGUSTA AUTHORIZATION PRESERVED = YES
AUGUSTA RECEIPT BYTES CHANGED = NO
REPAIR-CAUSED FAILURES = 0
CURRENT LIVE MODIFIED = NO
DEPLOYMENT PERFORMED = NO
READY TO RETURN TO WEST PALM BEACH = YES
