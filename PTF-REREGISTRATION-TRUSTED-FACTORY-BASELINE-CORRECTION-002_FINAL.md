# PTF-REREGISTRATION-TRUSTED-FACTORY-BASELINE-CORRECTION-002 — FINAL

**Market branch** `worker/ptf-west-palm-beach-fl-market-001` (worktree `C:\Atlas-West-Palm-Beach-FL-Hardened-V1`)
**Repair branch** `worker/ptf-reregistration-trusted-factory-baseline-002` @ `a000b167` (worktree
`C:\Atlas-PTF-Trusted-Factory-Baseline`, based on `e59883f7`, pushed, merged into the market branch as `e6858e31`)

**Result: PASS.** Re-registration now compares the market's own paths against its authorizing commit, and any factory
lineage merged after that commit against the lineage's own proven tip, by git blob id. West Palm Beach re-registers as
`AUTHORIZED_NONLIVE_MARKET_REREGISTRATION_DATA_ONLY` (ELIGIBLE YES, 17/17 checks, FULL_REGRESSION_REQUIRED NO,
SHARED_FACTORY_DELTA 0). It is staged as a projected, non-deployable candidate and stops **before** a new founder
authorization. No broad regression ran. No WPB market data and no authorization record changed. Nothing was deployed.

---

## 1 — THE REFUSAL, REPRODUCED

On the pre-repair tree (`eb15f9cb`), the canonical packet (005) returned: base **`d4da13d1`** (WPB's authorizing commit),
`change_set FAIL`, 41 changed paths. The measured market-correction set against a factory-inclusive base had
**0 shared, 0 unknown**. Every one of the **17** shared paths maps to one of the three merged repairs
(`git log d4da13d1..HEAD -- <path>`):

| Commit | Paths |
|---|---|
| `4cbe6e4c` canonical re-registration lane | `PTF-CANONICAL-REREGISTRATION-LANE-REPAIR-001_FINAL.md`, `docs/PTF_HARDENED_FACTORY_RUNBOOK.md`, `registration_data_only_contract.json`, `regression_validation_matrix.json`, `launch_participation.py`, `market_local_isolation.py`, `registration_data_only.py`, `registration_release_lane.py`, `regression_delta.py`, `test_reregistration_lane_001.py` |
| `f182cc08` FAST rule J non-empty guard | `PTF-FAST-NONEMPTY-BUNDLE-GUARD-001_FINAL.md`, `fast_release_lane.py` (also e59883f7), `package_staging.py`, `test_ptf_fast_nonempty_bundle_guard_001.py` |
| `e59883f7` FAST receipt reader guard | `PTF-FAST-RECEIPT-READER-GUARD-001_FINAL.md`, `test_atlas_throughput_003.py`, `test_ptf_fast_receipt_reader_guard_001.py` |

**Unexplained shared paths = 0.** The synthetic battery reproduces the same refusal
(`test_the_merged_factory_reproduces_the_refusal_without_a_baseline`).

## 2 — THE TWO-LINEAGE MODEL

* **A. Market baseline:** `derive_reregistration_base`, unchanged: the commit that wrote the authorizing decision.
  All market-owned state is still classified against A. The classification document's `base` stays `d4da13d1`.
* **B. Trusted factory baseline:** derived (section 3). A path is compared against B **only** when all three hold,
  by git blob id (`regression_delta.factory_baseline_delta`):
  1. its bytes at HEAD **are** its bytes at B;
  2. its bytes at A are its bytes at `merge-base(A, B)`, meaning the market line never touched it, so the whole change is the factory's;
  3. the factory lineage itself changed it.
* No path is exempted by name, class or list. A factory path whose HEAD bytes differ from B is **re-edited**
  (`SHARED_FACTORY_DELTA`). It is put back into the change set **and named a narrowing blocker**, so the shared-path
  prohibition refuses it whatever its class (a re-edited *doc* would otherwise have read as narrow; the battery caught this).
  A path both lineages changed stays in the market diff and fails as before.

## 3 — THE BASELINE, DERIVED MECHANICALLY (no hard-coded commit or branch)

`registration_release_lane.derive_trusted_factory_baseline(market, A, live)`:

* Candidates are every non-first parent of every first-parent merge in `A..HEAD` that A does not already contain.
* **Every** candidate must pass `prove_factory_lineage`, and one unproven merge refuses the whole baseline
  (`FACTORY_BASELINE_NOT_DERIVABLE`). A proven lineage:
  - is an ancestor of HEAD and does not contain A;
  - names no path of the market;
  - contains the live lineage commit and carries its live-truth files byte-for-byte;
  - is **published by a ref of its own** (a branch or remote ref that contains it but not A);
  - changes, since leaving the market line, **only factory paths**: no `AUTHORITY_CHANGE`, `MARKET_DATA_PACKAGE`
    or `DEPLOYMENT_CHANGE`, and no path naming any market.
* The proven tips must be one line of descent. The newest, which contains all the others, is B. If they are not, the
  baseline is refused as not uniquely resolvable.
* If nothing was merged, it returns `None` and the classification is exactly the old one.
* It is wired **only** in `classify_automatically`'s re-registration branch. Fresh-market registration, the composite
  class and ordinary shared-code classification are untouched (`classify_change`'s new argument defaults to `None`, and
  the document gains a `trusted_factory_baseline` key only when the argument is used).

**For WPB (measured):**

| | |
|---|---|
| B (before this repair) | `e59883f7`, merge `df77f1aa`, merge base `efd22bc7`, refs `worker/ptf-fast-receipt-reader-guard-001` (local and origin), 17 factory paths |
| B (after merging this repair) | **`a000b167`**, merges `e6858e31` → `df77f1aa`, tips ordered (a000b167 ⊇ e59883f7), refs `worker/ptf-reregistration-trusted-factory-baseline-002` (local and origin) |
| Every shared path in HEAD byte-identical to B | YES: 17/17 inherited, 0 re-edited |
| WPB correction commits' shared implementation changes after B | 0 |

This rule has a consequence: a repair to the lane itself cannot be committed on a market branch. Its edited modules would
differ from B and fail closed. So this repair was built on its own branch from `e59883f7`, tested and pushed there, and
**then** merged. The runbook states this rule.

## 4 — THE CLASSIFIER CHANGE (minimum)

| File | Change |
|---|---|
| `scripts/pettripfinder/regression_delta.py` | `blob_id_at` (committed bytes; the worktree is hashed through git's clean filters, so CRLF checkouts compare equal), `factory_baseline_delta`, optional `factory_baseline` on `classify_change` / `classify_document`, re-edited factory paths added to the blockers |
| `scripts/pettripfinder/registration_release_lane.py` | `FACTORY_BASELINE_NOT_DERIVABLE`, `prove_factory_lineage`, `derive_trusted_factory_baseline`, wiring in `classify_automatically` (re-registration only), 3 packet fields (`trusted_factory_baseline`, `inherited_factory_paths`, `SHARED_FACTORY_DELTA`) |
| `docs/PTF_HARDENED_FACTORY_RUNBOOK.md` | the two-lineage paragraph under the re-registration class |
| `tests/pettripfinder/test_reregistration_lane_001.py` | a `_build(after_auth=…)` hook, the `repo` fixture body extracted to `_attach`, and the new `TestTheTrustedFactoryBaseline` battery (20 tests). It was added to the existing module on purpose: a new module would move the committed test inventory and lane-membership table |

Not changed: `registration_data_only.py`, `launch_participation.py`, the 17 checks, the partition, the shared-path
prohibition, the contract and matrix documents, and any market data.

## 5 — HARD NEGATIVES (all fail closed, synthetic, `TestTheTrustedFactoryBaseline`)

| # | Case | Result |
|---|---|---|
| 1 | a shared file differs from B (worktree edit of the factory module) | ELIGIBLE NO, re-edited, `change_set FAIL`, SHARED_FACTORY_DELTA 1 |
| 2 | the correction edits a factory file after the merge (committed) | ELIGIBLE NO, re-edited, **named a narrowing blocker** |
| 2b | the market line reverts or deletes a factory module | ELIGIBLE NO (put back into the change set) |
| 3 | the baseline is not an ancestor (an unmerged lineage) | `FACTORY_BASELINE_NOT_DERIVABLE: … is not an ancestor of HEAD` |
| 4 | two unrelated lineages merged | refused: *cannot be resolved uniquely* (and 4b: a lineage built on the first IS accepted, as the newest) |
| 5 | a merged lineage published by no ref of its own | refused: *published by no ref of its own* |
| 5b | a merged "factory" lineage carrying market data | refused: *non-factory path* |
| 5c | a merged lineage carrying a path naming the market | refused |
| 5d | an arbitrary shared commit straight onto the market line | ELIGIBLE NO (in the change set, SHARED) |
| 6 | unknown path | ELIGIBLE NO |
| 7 | another market changes | ELIGIBLE NO |
| 8 | live market | `live_veto FAIL` |
| 9 | old authorization still deployable | `authorization_supersession FAIL` (*still deployable*) |
| 10 | authorization inheritance (row kept FOUNDER_AUTHORIZED) | `participation FAIL` |

Positive cases: mechanical derivation; the narrow class against both lineages, with base still A; ordinary lifecycle →
baseline `None`; lane wiring `classify_automatically` → `packet` AUTHORIZATION_READY with the factory fields.

## 6 — WEST PALM BEACH READ-ONLY PROOF (merged tree `e6858e31`, nothing written)

`derive_reregistration_base` → `d4da13d1` · `derive_trusted_factory_baseline` → `a000b167` ·
`classify_document(d4da13d1, WORKTREE, factory_baseline)` in 43.5 s:

**AUTHORIZED_NONLIVE_MARKET_REREGISTRATION_DATA_ONLY · ELIGIBLE YES · FULL_REGRESSION_REQUIRED NO · 17/17 PASS ·
SHARED_FACTORY_DELTA 0 · inherited 17 · changed 25 (1 market-local, 9 registration, 15 derived) · SHARED 0 · UNKNOWN 0.**

## 7 — FOCUSED TESTS (one pytest process at a time; no broad run)

Modules: `test_reregistration_lane_001` (75 tests, 20 new), `test_registration_data_only_001`,
`test_composite_fresh_market_001`, `test_regression_delta_001`, `test_release_factory_bounded_repair_002`.

| | repair `a000b167` (pre-commit tree) | base `e59883f7` (detached worktree) |
|---|---|---|
| collected | 333 | 313 |
| passed | 319 | 299 |
| failed | 14 | 14 |
| runtime | 258.4 s | 238.7 s |

The failure sets are **identical by node id** (`diff` empty): the 12 `test_registration_data_only_001` real-tree nodes pinned to
the Charlotte base, `test_composite_fresh_market_001::…test_a_bare_re_registration_keeps_the_original_class`, and
`test_regression_delta_001::test_the_committed_closures_all_verify`. These are the same 14 PRE_EXISTING nodes that
PTF-CANONICAL-REREGISTRATION-LANE-REPAIR-001 documented. **REPAIR_CAUSED = 0 · UNRESOLVED = 0.** Not run: broad regression,
`test_factory_throughput_001.py`, demo-media, whole-site assembly, unrelated launch tests. The repository CLAUDE.md asks for
a full regression before commits; this order forbids it, and none ran.

## 8 — WEST PALM BEACH APPLIED

The participation reissue (`reregister`) was already committed in 005 (`174d6b31`: row SOURCE_READY, one package-bound
`founder_authorization_superseded` entry). Running it again would correctly refuse, because the row is no longer
FOUNDER_AUTHORIZED. The remaining canonical step, `registration_release_lane packet --market west-palm-beach-fl`, ran on the
merged tree (commit `348c9da6`):

| | |
|---|---|
| status | **AUTHORIZATION_READY** / `AWAITING_FOUNDER_AUTHORIZATION`, `authorized_by null` |
| class | `AUTHORIZED_NONLIVE_MARKET_REREGISTRATION_DATA_ONLY`, ELIGIBLE YES, 17/17 PASS |
| FULL_REGRESSION_REQUIRED | NO; REMOTE_BROAD_JOBS 0; plan modules 0; assembly not required |
| base / factory baseline | `d4da13d1` / `a000b167`, inherited 17, SHARED_FACTORY_DELTA 0 |
| binds | pkg `94d6f411…`, receipt `5aaf1cb2…`, bundle `711760f0…`, parent deploy `6ab1a035…`, parent release `97ec0244…` |
| reregistration | superseded decision 003 (`19328995`), 789c0187 → 94d6f411, auth `217f87ee` SUPERSEDED, `old_authorizations_authorize_the_corrected_package false`, `new_founder_authorization_required true` |
| **lane time** | **42.6 s** (14:58:57.230Z → 14:59:39.845Z); 0 human waits |

### Staging (in memory, `C:\t\wpb5\staging_002.json`, nothing persisted, participation bytes unchanged)

| | |
|---|---|
| PARENT LOOKUP | PASS: the package's parent `6ab1a035…` = resolved deploy = deployed bundle `0ec5c655…` |
| PROJECTED PARTICIPATION | PROJECTED / NON-DEPLOYABLE: in memory 32 → 33 (+ WPB only); the committed record stays at 32 |
| UNCHANGED BUNDLES REUSED | **32** (every live market index carried unchanged) |
| UNCHANGED MARKETS REBUILT | **0** |
| WEST PALM BEACH BUNDLES BUILT | **1** distinct bundle, `711760f0…` (320 files / 304 HTML). It was built by rule J; rule K's byte-identical twin is the determinism proof, not a second bundle. It comes from this session's shadow FAST run of the same package bytes |
| Physical re-render | none in this order (no whole-site assembly; the release store is not used by this staging) |
| CANDIDATE REPRODUCIBLE | YES: `91373ef9…` composed twice, and equal to the digest the 004 seal recorded |

### Candidate accounting (recomputed)

| | |
|---|---|
| CANDIDATE MARKETS | **33** |
| CANDIDATE PROFILES | **2424** |
| CANDIDATE RELEASE-INDEX ROUTES | **2701** |
| CANDIDATE SERVED SITEMAP ROUTES | **2767** (projection = live 2711 measured + WPB 56 measured from the WPB build's own sitemap) |
| WEST PALM BEACH PROFILES | 49 |
| WEST PALM BEACH RELEASE-INDEX ROUTES | 55 (= the declared set exactly) |
| WEST PALM BEACH SERVED ROUTES | 56 (55 + `/policy-comparison/`) |
| WEST PALM BEACH CORRIDORS | 5: boca-raton, delray-beach, downtown-west-palm-beach, palm-beach-gardens, palm-beach-international-airport |

### Corrected identity

`Hilton Garden Inn Boca Raton`, route `/pet-friendly-hotels/west-palm-beach-fl/hilton-garden-inn-boca-raton/`, property code
**`bctbrgi`**, premises `8201|congress|33487`, first-party binding `full_premises_match true` (Hilton `/hotel-info/`, READ).
The page is present in the WPB build. No profile is named Apple Ten, no `apple-ten` route exists in the candidate, and no
page was built for the old route.

### Delta safety and gates

UNEXPECTED MARKET / PROFILE / ROUTE DELTA = `[]` / `[]` / `[]`. `release_index.compare` passed with no findings. 2646/2646
parent routes and 2375/2375 parent profiles are preserved (the profiles by record digest). The added routes are exactly WPB's 55.

Staging gates **12/12 PASS**: package identity · parent identity · participation projection · parent route preservation ·
profile preservation · route preservation · candidate delta · reuse · corrected identity · FAST receipt eligibility
(`5aaf1cb2`, 320 / 304, 0 defects; Augusta `5f8116aa` preserved and currently ineligible: EMPTY_BUNDLE, NO_HTML_OUTPUT) ·
deployment refusal (0 AUTHORIZED records anywhere; the only WPB authorization is SUPERSEDED and binds bundle `217f87ee`) ·
live-market veto. Together with the packet's 17 (which include re-registration class, authorization supersession and
live veto): **29/29 PASS**. **DEPLOYMENT REFUSAL = EXPECTED / PASS.**

## 9 — FINAL STATE AND LIVE SAFETY (2026-09-24T15:00Z)

Resolver RESOLVED YES: `e82120cc` / `6ab1a035c7ef3b14a23a4ec6` / 32 / 2375 / 2711, host verified. External sitemap
`e81961ae…`, 2711 `<loc>`, 0 WPB. WPB hub 404, FTL 200, Augusta 200, Detroit 404; both WPB profile routes 404. No Netlify call.

## Commits

Repair branch: `a000b167` (pushed). Market branch: `e6858e31` merge of the repair · `348c9da6` packet (AUTHORIZATION_READY) ·
the report commit. Earlier and unchanged: `df77f1aa` (repairs 001), `e32b7a86` (helper removal), `174d6b31` (reissue).

---

## FINAL ANSWERS

1. REFUSAL REPRODUCED = YES (base `d4da13d1`, canonical shared 17, measured correction shared 0, unknown 0)
2. SHARED PATHS MAPPED = 17/17 to `4cbe6e4c` / `f182cc08` / `e59883f7`; unexplained 0
3. TRUSTED FACTORY BASELINE = derived `a000b167` (was `e59883f7` before this repair merged); ancestor of HEAD; independent refs present
4. SHARED PATHS BYTE-IDENTICAL TO BASELINE = 17/17
5. CORRECTION SHARED CHANGES AFTER BASELINE = 0
6. HARD NEGATIVES = 10 required (+5 variants), all fail closed
7. FOCUSED TESTS = 333 collected / 319 passed / 14 failed (identical failure set at `e59883f7`); REPAIR_CAUSED 0; UNRESOLVED 0
8. REREGISTRATION CLASS = AUTHORIZED_NONLIVE_MARKET_REREGISTRATION_DATA_ONLY
9. ELIGIBLE = YES
10. FULL_REGRESSION_REQUIRED = NO
11. SHARED FACTORY DELTA = 0
12. UNKNOWN = 0
13. BROAD REGRESSION RUNS = 0
14. LANE TIME = 42.6 s (packet)
15. PARENT LOOKUP = PASS
16. PARENT ROUTES PRESERVED = PASS
17. UNCHANGED BUNDLES REUSED = 32
18. UNCHANGED MARKETS REBUILT = 0
19. WEST PALM BEACH BUNDLES BUILT = 1
20. CANDIDATE = 33 markets / 2424 profiles / 2701 release-index / 2767 served (projected)
21. WEST PALM BEACH = 49 profiles / 55 release-index / 56 served / 5 corridors
22. CORRECTED HILTON GARDEN INN BOCA RATON PRESENT = YES
23. OLD APPLE TEN PROFILE = NO
24. OLD APPLE TEN ROUTE = NO
25. UNEXPECTED DELTA = [] / [] / []
26. ALL STAGING GATES = 29/29 PASS (17 registration + 12 staging)
27. DEPLOYMENT REFUSAL = EXPECTED / PASS
28. NEW FOUNDER AUTHORIZATION = NO
29. NEW DEPLOYMENT AUTHORIZATION = NO
30. WPB MARKET DATA MODIFIED = NO
31. AUTHORIZATION DATA MODIFIED = NO
32. CURRENT LIVE MODIFIED = NO
33. WEST PALM BEACH DEPLOYED = NO
34. origin == HEAD = YES (both branches, after push)
35. tree clean = YES

WPB REREGISTRATION BASELINE CORRECTION = PASS
REREGISTRATION CLASS = AUTHORIZED_NONLIVE_MARKET_REREGISTRATION_DATA_ONLY
SHARED FACTORY DELTA = 0
FULL_REGRESSION_REQUIRED = NO
BROAD REGRESSION RUNS = 0
UNCHANGED MARKETS REBUILT = 0
CURRENT LIVE MODIFIED = NO
WEST PALM BEACH DEPLOYED = NO
READY FOR NEW FOUNDER AUTHORIZATION = YES
