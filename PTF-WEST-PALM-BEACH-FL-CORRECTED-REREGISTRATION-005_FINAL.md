# PTF-WEST-PALM-BEACH-FL-CORRECTED-REREGISTRATION-005 — FINAL

**Branch** `worker/ptf-west-palm-beach-fl-market-001` (worktree `C:\Atlas-West-Palm-Beach-FL-Hardened-V1`)
**Result: STOPPED AT PHASE 7.** The canonical `reregister` → `packet` lane ran on the corrected package and
the classification came back **NOT** `AUTHORIZED_NONLIVE_MARKET_REREGISTRATION_DATA_ONLY`. As the order
requires, I stopped. No broad suite ran, staging did not run, and nothing was authorized or deployed.

**Cause: a lane ordering defect, not a data defect.** The re-registration base is West Palm Beach's own
authorizing commit, `d4da13d1`. The lane's own code (`4cbe6e4c`, `f182cc08`, `e59883f7`) was merged into
the branch *after* that commit, so `d4da13d1..HEAD` necessarily contains 17 shared factory paths, and the
`change_set` check correctly refuses them. A read-only measurement against a base that already contains
the factory repair gives **ELIGIBLE YES, 17/17 PASS, 0 shared, 0 unknown**. So the WPB change set itself is
narrow, and the factory merge ordering is the only blocker. The measurement is evidence only. It does
not replace the canonical classification.

---

## Ancestry (mechanical)

`git merge-base --is-ancestor <c> HEAD`: `4cbe6e4c` ANCESTOR · `f182cc08` ANCESTOR · `e59883f7` ANCESTOR
(through merge `df77f1aa`).

## PHASE 1 — CURRENT LIVE (`release_index live-source --verify-host`, 2026-09-24T14:21Z)

| | |
|---|---|
| CURRENT LIVE SOURCE COMMIT | `e82120cce7e48c62d3c1057a6c82785bed920485` (built from `0cc2817b`) |
| CURRENT LIVE DEPLOYMENT | `6ab1a035c7ef3b14a23a4ec6` (`ptf-deploy-fort-lauderdale-004-…`) |
| CURRENT LIVE BUNDLE | `0ec5c6557d79eaf77a4065b6700c0a5807e9bfe282408dd4779804b33af3a40f` |
| CURRENT LIVE SITEMAP | `e81961ae76454ce608fcb39624d5147c8779f52b269faab9449138397cb8fa3d` |
| CURRENT LIVE MARKETS | 32 |
| CURRENT LIVE PROFILES | 2375 |
| CURRENT LIVE RELEASE-INDEX ROUTES | 2646 (`live_index`, participating markets; index digest `97ec0244…`) |
| CURRENT LIVE SERVED ROUTES | 2711 |
| HOST VERIFIED | YES (resolver `host_verified true`, plus an external GET: sitemap sha `e81961ae…`, 2711 `<loc>`, 0 WPB URLs) |

West Palm Beach is not in `participating_markets`, and `/pet-friendly-hotels/west-palm-beach-fl/` returns 404. **Not live.**

## PHASE 2 — CORRECTED PACKAGE (read-only; `C:\t\wpb5\phase2_verify.json`)

| | |
|---|---|
| PACKAGE | `pkg-west-palm-beach-fl-94d6f4115daa9b88` |
| DIGEST | `sha256:94d6f4115daa9b88a8773d2b73b49593c5de4a4757125def52b7ba17c25ec086` (matches the order) |
| `verify_seal` | 0 issues |
| SOURCE READY | YES: census 190, PF 49, NP 25, unresolved 116, 0 founder holds |
| COVERAGE READY | YES: scorecard unchanged from 004 (public routes 62, evidence refs 74) |
| PACKAGE REPRODUCIBLE | YES: `find_covering_package(HEAD)` re-seals the head authority to exactly `94d6f411…`, the only covering package (the old `789c0187` is refused: its declared inputs are not the head bytes) |
| FAST (committed receipt `5aaf1cb2`) | 15/15 PASS, 0 UNKNOWN, 0 FAILED, J `file_count 320` / `html_count 304`, bundle `711760f0…` |
| FAST (corrected implementation, **shadow re-run**) | `run_fast_lane` on the committed package, work dir `C:/t/w5a`, receipt kept **out of the tree**: 15/15 PASS, ELIGIBLE YES, 95.2 s |
| Rule J | `file_count 320`, `html_count 304`, **`output_present true`**, `output_defects []`, bundle `711760f09faddc80…` |
| Rule K | `BYTE_IDENTICAL`, a = b = `711760f09faddc80…` (≠ `e3b0c442…`), 4 cold builds, 0 reuse hits. **Non-vacuous.** |

## PHASE 3 — WITHDRAW HELPER

| | |
|---|---|
| WITHDRAW HELPER FOUND | `atlas-dashboard/scripts/pettripfinder/west_palm_beach_fl_withdraw_authorization_004.py` (117 lines, added in `9cf163b1`, imports `deployment_authorization`) |
| Transition already durable | YES. `ptf-auth-west-palm-beach-003-217f87eeba72` reads SUPERSEDED at HEAD. Its committed blob equals disk, history is `…AUTHORIZED 2026-09-22T22:56:10Z → SUPERSEDED 2026-09-23T00:49:35Z`, `deploy_id null`, and SUPERSEDED has no outgoing transition |
| Sole-purpose artifacts | none: the helper wrote only into the authorization record, which stays |
| WITHDRAW HELPER REMOVED | YES, commit `e32b7a86` (`git rm` of that one file; `git show 9cf163b1:…` still returns all 117 lines) |
| HISTORICAL SUPERSESSION PRESERVED | YES: authorization record, old package `789c0187`, its receipt, and the 003/004 reports all untouched |

## PHASE 4 — OLD AUTHORIZATIONS (`C:\t\wpb5\phase4_auth.json`)

| | |
|---|---|
| Authorizations naming WPB | exactly 1: `ptf-auth-west-palm-beach-003-217f87eeba72` |
| OLD FOUNDER AUTHORIZATION | historically preserved: decision `PTF-WEST-PALM-BEACH-FL-FOUNDER-LAUNCH-AUTHORIZATION-003`, participation sha `19328995…`, `registered_package_digest sha256:789c0187…`. It is now named by the supersession entry and kept in the decision chain's `supersedes` |
| OLD DEPLOYMENT AUTHORIZATION | SUPERSEDED, terminal, `deploy_id null`, bundle `217f87ee…` kept |
| OLD AUTHORIZATION CAN DEPLOY CORRECTED PACKAGE | NO: `deployability_problems` against bundle `711760f0…` returns `bundle_sha256: authorization binds '217f87ee…'` and `authorization_status is SUPERSEDED; only ['AUTHORIZED'] may deploy` |
| DEPLOYABLE OLD AUTHORIZATIONS REMAINING | 0 (and 0 AUTHORIZED records anywhere in the repo) |

## PHASE 5 — RE-REGISTRATION BASE

| | |
|---|---|
| REREGISTRATION BASE COMMIT | `d4da13d142821a0d13483ad912c3414b67b221c0` (`derive_reregistration_base`, mode re-registration: the commit that wrote authorizing decision `19328995…`) |
| PRIOR REGISTERED PACKAGE | `pkg-west-palm-beach-fl-789c0187e366abe8` (`sha256:789c0187e366abe8c199…`) |
| CORRECTED PACKAGE | `pkg-west-palm-beach-fl-94d6f4115daa9b88` |

The base is the correct one. It is also the root of the refusal (Phase 7).

## PHASE 6 — PARTICIPATION REISSUE (commit `174d6b31`)

`registration_release_lane reregister --market west-palm-beach-fl --work-order PTF-WEST-PALM-BEACH-FL-CORRECTED-REREGISTRATION-005`:

* row `FOUNDER_AUTHORIZED_FOR_LAUNCH` → **`SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH`**, proof PASS
* authorized set 33 → 32: lost exactly `[west-palm-beach-fl]`, gained nothing. 34 rows, **0 other rows changed**,
  Detroit still SOURCE_READY, `decision_problems []`
* `founder_authorization_superseded`: authorizing decision `{PTF-WEST-PALM-BEACH-FL-FOUNDER-LAUNCH-AUTHORIZATION-003,
  19328995fd21…}`, superseded `sha256:789c0187e366abe8…`, corrected `sha256:94d6f4115daa9b88…`, deployment
  authorizations `[ptf-auth-west-palm-beach-003-217f87eeba72, bundle 217f87ee…, SUPERSEDED]`, `market_live false`,
  `reauthorization_required true`
* `decided_by` = the work order, not the founder. The market-state pin block was re-derived: 190 / 49 / 25 / 5 corridors,
  counts unchanged, only `last_moved_by` / `reviewed_by` moved
* No history was deleted, and participation monotonicity was not weakened: the drop is excused only by the package-bound entry.

## PHASE 7 — CANONICAL CLASSIFICATION: **REFUSED → STOP**

`registration_release_lane packet --market west-palm-beach-fl` (AUTOMATIC classification):

```
live source    : e82120cce7e4 | deploy 6ab1a035c7ef3b14a23a4ec6 | base d4da13d14282 | 5.7s
status         : NOT_AUTHORIZATION_READY | founder: AWAITING_FOUNDER_AUTHORIZATION
change class   : AUTHORITY_CHANGE/GENERIC_RUNTIME_CHANGE/ROUTING_SEMANTIC_CHANGE/DEPLOYMENT_CHANGE/
                 TEST_EXPECTATION_CHANGE/DOCUMENTATION_ONLY/GENERATED_REPORT_ONLY/MARKET_DATA_PACKAGE/UNCLASSIFIED
                 | broad: YES
change_set FAIL: the change set touches narrowing blocker(s) a registration does not own:
  ['launch_packages/pettripfinder/registration_data_only_contract.json',
   'launch_packages/pettripfinder/regression_validation_matrix.json',
   'scripts/pettripfinder/fast_release_lane.py']
(the other 16 checks: "not evaluated: the change set is not a registration")
```

The 41 changed paths since `d4da13d1` are the 24 WPB paths (correction 004 + this order) plus the **17 paths of
the merged factory repair**: 7 modules (`fast_release_lane`, `launch_participation`, `market_local_isolation`,
`package_staging`, `registration_data_only`, `registration_release_lane`, `regression_delta`), 2 regenerated
contract documents, the runbook, 4 test modules and 3 root reports. The refused packet outputs are committed as the
current truth: `west_palm_beach_fl_registration_{classification,authorization_readiness}.json`, both
`NOT_AUTHORIZATION_READY`, base `d4da13d1`.

### Root cause

`derive_reregistration_base` walks the first-parent chain to the oldest commit carrying the authorizing decision.
That is `d4da13d1`, reached *through* merge `df77f1aa`, whose first parent is the WPB line. Because the factory
repair (including the re-registration lane itself) lands after the authorizing commit, **every** market that needs
this lane has the lane's own code in its change set. The lane repair measured WPB applicability on `6fa2ae34`,
*before* the merge ("20/21 narrow + the helper"), so it could not see this. Any factory merge after an authorization
has the same effect. This is a bootstrap gap in the lane.

### Read-only measurement: is the factory merge the ONLY blocker?

I built one dangling commit object `36dd0d2b` with `git commit-tree` (no ref, never pushed). Its tree is `git merge-tree
--write-tree d4da13d1 e59883f7`, with parents `e59883f7` and `d4da13d1`: WPB's authorized state on the current factory.
`regression_delta.classify_document(36dd0d2b, WORKTREE)` on the committed head (tree clean, 36.6 s) gave:

| | |
|---|---|
| changed paths | 24 (1 market-local, 9 registration data, 14 derived; **0 shared, 0 unknown**) |
| class | **`AUTHORIZED_NONLIVE_MARKET_REREGISTRATION_DATA_ONLY`**, ELIGIBLE YES, FULL_REGRESSION_REQUIRED NO, REMOTE_BROAD_JOBS 0 |
| checks | **17/17 PASS**, including `participation`, `release_integrity`, `authorization_supersession`, `live_veto`, `fast_receipt`, `market_state_pin` |
| expected release | 33 markets / 2424 profiles / 2701 routes, 0 unexpected market / profile / route changes |

Output: `C:\t\wpb5\measure_classification.json` (sha256 `10a7b557…`). It is **not** committed and **not** canonical,
because the base was hand-constructed. It only locates the defect.

## PHASE 8 — TIMER

| | |
|---|---|
| `reregister` | 31.1 s (14:28:15.035Z → 14:28:46.096Z) |
| `packet` (auto-classify + refusal) | 6.2 s (14:29:10.215Z → 14:29:16.448Z) |
| lane wall clock to refusal (including the commit between) | **61.4 s** |
| human permission waits | 0 |

## PHASE 9 — SAFETY (at the stop)

WPB paths only. No other market's source changed. No factory code change in this order: its three commits touch only the
helper deletion, participation, the pin block and WPB reports. Production unchanged, live site unchanged, no authorization
inherited. **NEW FOUNDER AUTHORIZATION = NO · NEW DEPLOYMENT AUTHORIZATION = NO · CORRECTED PACKAGE DEPLOYABLE = NO.**

## PHASES 10–17 — NOT RUN (stopped at Phase 7)

The projected participation, parent lookup, staging, candidate accounting, delta safety and staging gates were
**not run**. Their prerequisite, a canonical ELIGIBLE classification, does not exist. The one number the classifier's own
`expected_release` check produced (33 / 2424 / 2701) comes from the non-canonical measurement and is not a staged candidate.

Partial read-only evidence that does not depend on staging:

* **Phase 14 (package level):** the corrected package's published record is `Hilton Garden Inn Boca Raton`
  (`identity_key hilton garden inn boca raton`), and route `/pet-friendly-hotels/west-palm-beach-fl/hilton-garden-inn-boca-raton/` is
  among the 55 declared routes. `Apple Ten Hospitality Management Inc` survives only as census alias and DBPR licensee
  evidence, never as a record name or route (the one route containing "apple" is `hyatt-place-delray-beach-pineapple-grove`).
  The browser lane's `bctbrgi` / `full_premises_match true` binding is unchanged from 004.
* **Phase 16:** `eligible_receipts(west-palm-beach-fl, 94d6f411…)` selects exactly `…-5aaf1cb212b2f493.json`
  (J 320 / 304, `receipt_output_defects []`). Augusta's `…-5f8116aaecd97d09.json` is historically preserved
  (sha256 `a2e22ce8…`, stored ELIGIBLE YES) and **currently ineligible** (`EMPTY_BUNDLE`, `NO_HTML_OUTPUT`). Augusta was not modified.

## PHASE 18 — LIVE SAFETY (2026-09-24T14:32Z)

Resolver RESOLVED YES: `e82120cc` / `6ab1a035c7ef3b14a23a4ec6` / 32 markets / 2375 / 2711, host verified. External sitemap
sha `e81961ae…` (unchanged), 2711 `<loc>`, 0 WPB. WPB hub 404 · FTL hub 200 · Augusta hub 200 · Detroit 404 · both WPB profile
routes (corrected and old) 404. No Netlify call.

## WHAT THE FOUNDER MUST DECIDE (not done here)

1. **Factory repair (recommended):** teach `derive_reregistration_base` / the classifier that factory commits merged
   *after* the authorizing commit belong to the base. For example, compose the base as the authorizing commit merged with
   each second-parent factory side, provided that side names no path of the market and contains live. This is shared code,
   so it needs its own order and focused tests. Without it, the next market that is corrected after a factory merge hits
   the same wall.
2. **Branch reshape:** rebuild WPB's post-authorization line on a first-parent merge of the factory into `d4da13d1`, so the
   canonical lane derives that merge as the base. This is the shape the measurement used. It rewrites or re-parents history
   on a pushed branch, so it is the founder's call and was not done.
3. **One broad regression run** on the current head.

After (1) or (2), re-run `packet` alone. Participation is already reissued and committed, so no second `reregister` is needed.

## Commits

`df77f1aa` repair integration (merge, now pushed) · `e32b7a86` helper removal · `174d6b31` canonical re-registration
(participation + pin + report) · the report commit (this file + the refused packet outputs).

---

## FINAL ANSWERS

1. CURRENT LIVE DEPLOYMENT = `6ab1a035c7ef3b14a23a4ec6` (Fort Lauderdale 004, source `e82120cc`)
2. CURRENT LIVE MARKETS = 32
3. CORRECTED PACKAGE = `pkg-west-palm-beach-fl-94d6f4115daa9b88`
4. CORRECTED PACKAGE DIGEST = `sha256:94d6f4115daa9b88a8773d2b73b49593c5de4a4757125def52b7ba17c25ec086`
5. RULE J NONEMPTY = YES (320 files / 304 HTML / output_present true, corrected implementation, shadow)
6. RULE K NONVACUOUS DETERMINISM = YES (a = b = `711760f0…`, not `e3b0c442…`)
7. WITHDRAW HELPER REMOVED = YES (`e32b7a86`; history keeps it at `9cf163b1`)
8. HISTORICAL OLD AUTH PRESERVED = YES
9. OLD DEPLOYMENT AUTH STATUS = SUPERSEDED (terminal, unconsumed, bundle `217f87ee…` kept)
10. DEPLOYABLE OLD AUTH REMAINING = 0
11. REREGISTRATION BASE = `d4da13d1` (canonical)
12. REREGISTRATION CLASS = **NOT GRANTED**: canonical classification is `AUTHORITY_CHANGE/GENERIC_RUNTIME_CHANGE/…` (change_set FAIL on the merged factory repair). A non-canonical measurement against a factory-inclusive base gives `AUTHORIZED_NONLIVE_MARKET_REREGISTRATION_DATA_ONLY`
13. ELIGIBLE = NO (canonical) · YES in the measurement only
14. FULL_REGRESSION_REQUIRED = YES (canonical) · NO in the measurement only
15. BROAD REGRESSION RUNS = 0
16. REREGISTRATION LANE TIME = 61.4 s to refusal (reregister 31.1 s + packet 6.2 s); 0 human waits
17. SHARED PATHS = 17 (canonical; all from the merged factory repair) · 0 in the measurement
18. UNKNOWN PATHS = 0 in the measurement (the canonical run stopped at change_set and did not produce a partition)
19. NEW FOUNDER AUTHORIZATION = NO
20. NEW DEPLOYMENT AUTHORIZATION = NO
21. PARENT LOOKUP = NOT RUN (stopped at Phase 7)
22. PARENT ROUTES PRESERVED = NOT RUN
23. UNCHANGED BUNDLES REUSED = NOT RUN
24. UNCHANGED MARKETS REBUILT = 0 (nothing was staged)
25. WEST PALM BEACH BUNDLES BUILT = 0 staged (the shadow FAST run built the market bundle twice for J/K, outside the tree)
26. CANDIDATE MARKETS = NOT STAGED (measurement's expected release: 33)
27. CANDIDATE PROFILES = NOT STAGED (measurement: 2424)
28. CANDIDATE RELEASE-INDEX ROUTES = NOT STAGED (measurement: 2701)
29. CANDIDATE SERVED ROUTES = NOT STAGED
30. WEST PALM BEACH PROFILES = 49 (package)
31. CORRECTED HILTON GARDEN INN PROFILE PRESENT = YES (package level; no candidate staged)
32. OLD APPLE TEN PROFILE PRESENT = NO (package level)
33. OLD APPLE TEN ROUTE PRESENT = NO (package level; 404 live)
34. UNEXPECTED DELTA = NOT STAGED (measurement: 0 / 0 / 0)
35. FAST RECEIPT CURRENTLY VALID = YES (`5aaf1cb2`, J 320 / 304, 0 defects; Augusta's vacuous receipt currently ineligible)
36. ALL STAGING GATES = NOT RUN
37. DEPLOYMENT REFUSAL = YES (0 AUTHORIZED records; the old authorization refuses the corrected bundle)
38. CURRENT LIVE MODIFIED = NO
39. DEPLOYMENT PERFORMED = NO
40. WEST PALM BEACH LIVE = NO
41. origin == HEAD = YES (after the push of the report commit)
42. tree clean = YES
43. READY FOR NEW FOUNDER AUTHORIZATION = NO

WEST PALM BEACH REREGISTRATION = FAIL
REREGISTRATION CLASS = AUTHORIZED_NONLIVE_MARKET_REREGISTRATION_DATA_ONLY — NOT GRANTED (canonical change_set FAIL on the merged factory repair; measured ELIGIBLE against a factory-inclusive base)
FULL_REGRESSION_REQUIRED = YES (canonical) — not run
BROAD REGRESSION RUNS = 0
OLD AUTHORIZATION TRANSFERS = NO
UNCHANGED MARKETS REBUILT = 0
CURRENT LIVE MODIFIED = NO
WEST PALM BEACH DEPLOYED = NO
READY FOR NEW FOUNDER AUTHORIZATION = NO
