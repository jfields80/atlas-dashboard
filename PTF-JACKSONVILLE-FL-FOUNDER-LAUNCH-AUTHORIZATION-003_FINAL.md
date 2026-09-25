# PTF-JACKSONVILLE-FL-FOUNDER-LAUNCH-AUTHORIZATION-003 — FINAL

`jacksonville-fl` is **FOUNDER_AUTHORIZED_FOR_LAUNCH** and the **exact authorized production candidate is built,
byte-reproducible and deployable**. Branch `worker/ptf-jacksonville-fl-market-001`.

**STOPPED BEFORE DEPLOYMENT.** Netlify was not invoked, no deployment record exists, the authorization is
written **AUTHORIZED and UNCONSUMED**, and current production is byte-identical to what it served before this
order began.

---

## PHASE 1 — CURRENT LIVE, REVERIFIED

Resolved by the repaired resolver with host verification. `origin/main` was not used and is reported stale.

| | |
|---|---|
| CURRENT LIVE SOURCE COMMIT | `e3efa2210f759886aaad830b07fa241231a8f734` (built_from `ff6b506d`) |
| CURRENT LIVE DEPLOYMENT | `6ab599163f833ab7f48b395d` (west-palm-beach-fl) |
| CURRENT LIVE BUNDLE | `23728b4bff71c66d0a9a063de3882d744f92465f5f568f72b3caf16ca8641d78` |
| CURRENT LIVE SITEMAP | `8ae34cea1c7e384f0f4c8499066c5ff2f9ca841d099c344a5860041b4b6c7546` |
| CURRENT LIVE MARKETS | **33** |
| CURRENT LIVE PROFILES | **2,424** |
| CURRENT LIVE RELEASE-INDEX ROUTES | **2,701** |
| CURRENT LIVE SERVED ROUTES | **2,767** |
| HOST VERIFIED | **true** |

**The parent has NOT advanced since registration** — same deployment, same source commit, same bundle, same
sitemap. This authorization is not written against a stale parent.

The comparison artifact used throughout is `C:\t\wpb6a`, and it was proved to BE current live rather than assumed
to be: its own manifest carries bundle `23728b4b…` and sitemap `8ae34cea…`, and its `sitemap.xml` hashes to the
same `8ae34cea…` the host serves.

## PHASE 2 — THE REGISTERED PACKAGE, VERIFIED MECHANICALLY

| | |
|---|---|
| PACKAGE | `pkg-jacksonville-fl-60ba2edccd4882b3` ✅ |
| PACKAGE DIGEST | `sha256:60ba2edccd4882b38785d69c016f39f550924675d54197004adaf994b55c0536` ✅ |
| execution zone / sealed at | `REGISTERED_LIVE` / 2026-09-25T16:26:45Z, from source `bbdf2259` |
| identity records / PF / NP / unresolved | **268 / 95 / 18 / 155** ✅ |
| evidence references | 113 |
| SOURCE READY / COVERAGE READY / ACTIONABLE UNRESOLVED | **YES / YES / 0** ✅ |
| FAST | **15/15 PASS**, 0 UNKNOWN, 0 FAILED ✅ |
| RULE J | `file_count` **603**, `html_count` **587**, `output_present` true, defects `[]` ✅ |
| RULE K | **BYTE_IDENTICAL**, `a == b`, 4 cold builds, 0 reuse hits ✅ |
| REGISTRATION ELIGIBLE / FULL_REGRESSION_REQUIRED | **YES / NO** ✅ |
| registration proof | **15 of 15 checks PASS** |

Nothing was rebuilt: no census, no acquisition, no Firecrawl, no browser lane.

**One thing worth stating rather than passing over.** The readiness packet records
`expected_candidate_index_digest d0d88ba7…` beside `actual_candidate_index_digest bc0c5e0d…`. That is not a
defect and it is not drift: at packet time Jacksonville was still `SOURCE_READY`, so the "actual" index was
composed from the authorized set *without* it while the "expected" index included it. The `expected_release`
gate compares complete **sets** rather than digests, which is why it passes; the registration lane's own
composition agreed with itself at `d0d88ba7` twice over. After the flip in Phase 4 the two describe the same
market set.

## PHASES 3–4 — THE FOUNDER AUTHORIZATION AND THE PARTICIPATION FLIP

| | |
|---|---|
| FOUNDER AUTHORIZATION ID | **`ptf-auth-jacksonville-003-f82f0714db2d`** |
| AUTHORIZED MARKET | `jacksonville-fl` — **and only** `jacksonville-fl` |
| AUTHORIZED PACKAGE | `pkg-jacksonville-fl-60ba2edccd4882b3` |
| AUTHORIZED PACKAGE DIGEST | `sha256:60ba2edccd4882b3…c0536` |
| AUTHORIZED SOURCE COMMIT | `e7e02d4394dde29e949c13cf06732f3f7d69dc5f` |
| AUTHORIZED PARENT | deploy `6ab599163f833ab7f48b395d`, release-index digest `sha256:fda6317b…` |
| PARTICIPATION STATE | `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH` → **`FOUNDER_AUTHORIZED_FOR_LAUNCH`** |

Written through `launch_participation.extend_decision` — the chain is extended, never rebuilt. **35 markets, 34
now authorized, exactly one gained, none lost, no other market's row moved, lineage 36 records,
`decision_problems []`.** Detroit remains withheld at `SOURCE_READY`.

### The decision does not merely record the founder's four decisions — it refuses to write unless they are true

Every number in `decision_basis` is derived at run time from the committed census, policy package, exclusion
shard, release contract, partition, readiness packet and FAST receipt. Nothing is typed. And each of the
founder's four decisions is a **guard**:

1. **Authorize the sealed 95-profile cohort** — the module aborts unless the cohort is exactly 95 / 18.
2. **Keep the 1201 Kings Avenue dual-brand pair held, and self-sign no `identity_resolutions.json` ruling** —
   the module aborts unless exactly **2** rows carry that hold and **0** of them publish. The two rows are found
   by the adjudicator's **own `address_key`** (`1201|kings|32207`) written inside its hold reason, which is the
   ruling itself; keying on the word "Kings" would have swept in *Kings Landing*, an unrelated property held for
   an unrelated reason. `identity_resolutions.json` is **unchanged**.
3. **Keep Amelia Island a corridor** — the module aborts unless `amelia-island-fernandina-beach` is present as a
   publishing corridor and **absent** as a market document.
4. **Accept coverage at 42.16 %** — the module aborts unless `ACTIONABLE UNRESOLVED` is 0, and records the
   bound: Marriott's Akamai per-window quota (19 rows terminally held, all 43 in-market codes attempted), ESA's
   DataDome wall (terminal for the family, 6 rows), and independents with no first-party route in any authorized
   lane.

Recorded explicitly as **not** authorized by this decision: weaker evidence rules, weaker identity standards,
anti-bot bypass, publication of held properties, the dual-brand pair, Amelia Island's promotion, any geography
change, and deployment.

**A first authorization, not a re-authorization.** Jacksonville has never been authorized and never deployed, so
no `founder_authorization_superseded` block is written — and the module refuses to run if one exists for this
market. West Palm Beach's 006 decision needed that block because a pre-deploy identity correction had replaced
its bytes; nothing here was ever corrected after an authorization, because nothing here was ever authorized.

## PHASE 5 — THE EXACT AUTHORIZED CANDIDATE

`assemble_production_site --output C:/t/jax3a`, then `--output C:/t/jax3b`, on the committed tree `e7e02d43`.

| | |
|---|---|
| AUTHORIZED CANDIDATE BUNDLE | **`f82f0714db2dd4d714b6b789c68492f60de8a1f3287a11b1e6f1afd680cf0c4e`** |
| AUTHORIZED SITEMAP | `d34b0e5d7d5ed045a3f727e49f18e2fe61de3df108e9ef0666c5413d1bb48e4f` |
| total HTML pages / files | 15,324 / **15,342** |
| broken links · route collisions · global shadowing · canonical violations | **0 · 0 · 0 · 0** |
| markets included / excluded | 34 / **Detroit** (`participates: false`, still `SOURCE_READY`) |
| PARENT LOOKUP | **PASS** |
| PARENT ROUTES PRESERVED | **PASS** |

### Reuse and physical rendering are two different numbers

| | |
|---|---:|
| **UNCHANGED BUNDLES REUSED** | **33** = current live market count |
| **UNCHANGED MARKETS REBUILT** | **0** |
| **JACKSONVILLE BUNDLES BUILT** | **1** |
| **PHYSICAL FRAGMENTS RERENDERED** | **34** |

**This is reported separately because it is not reuse.** The release index carried all 33 unchanged markets'
entries forward untouched. But this worktree has **no populated release store**, so the whole-site composer
physically re-rendered every participating fragment — all 34 — read from the build's own log (`Market scope:`
× 34). Calling that reuse would overstate what the factory did. What the reuse figure *does* mean is proved
independently in Phase 12: not one prior market's bytes moved.

## PHASE 6 — TWO ROUTE ACCOUNTINGS, VERIFIED AS SETS

Neither system was derived from the other, and the two were never reconciled by arithmetic — the **actual route
sets** were differenced.

**A. RELEASE-INDEX ROUTES** — what markets own:

| | |
|---|---:|
| live | **2,701** |
| Jacksonville | **+106** |
| **candidate** | **2,807** |

**B. SERVED SITEMAP ROUTES** — read as a set from each bundle's own `sitemap.xml`:

| | |
|---|---:|
| live | **2,767** |
| Jacksonville | **+107** |
| **candidate** | **2,874** |

Differencing the two sitemaps as sets:

```
PRIOR SERVED ROUTES LOST : 0
ROUTES ADDED             : 107
  of which jacksonville-fl : 107
  NOT jacksonville-fl      : 0
```

The **+1 served-vs-index difference is exactly the policy-comparison page**, confirmed by classifying
Jacksonville's 107 served routes against the built artifact rather than assuming the composition contract:

| Class | Routes |
|---|---:|
| hotel profiles | **95** |
| corridor pages | **10** |
| market hub | **1** |
| **release-index subtotal** | **106** |
| policy-comparison (served, not market-owned) | **1** |
| **served total** | **107** |

The non-market served surface is 66 routes live and 67 in the candidate — the same global set plus Jacksonville's
comparison page.

## PHASE 7 — CANDIDATE ACCOUNTING

| | |
|---|---:|
| CANDIDATE MARKETS | **34** |
| CANDIDATE PROFILES | **2,519** |
| CANDIDATE RELEASE-INDEX ROUTES | **2,807** |
| CANDIDATE SERVED ROUTES | **2,874** |
| JACKSONVILLE PROFILES | **95** |
| JACKSONVILLE RELEASE-INDEX ROUTES | **106** |
| JACKSONVILLE SERVED ROUTES | **107** |

**Corridors, stated as two distinct facts** rather than collapsed into one, because they are not the same thing:

| | |
|---|---:|
| corridors **registered** | **17** |
| corridors **containing a published hotel** | **16** |
| corridors that **publish their own page** | **10** |
| corridors **forced** | **0** |

The 10 publishing corridors: `jax-airport-northside`, `westside-i10-i295`, `southside-university-boulevard`,
`st-johns-town-center-gate-parkway`, `deerwood-baymeadows`, `mandarin-bartram-julington-creek`,
`jacksonville-beach`, `atlantic-neptune-beach-mayport`, `orange-park-fleming-island`,
`amelia-island-fernandina-beach`. The 7 suppressed ones — `arlington-intracoastal-west`,
`deerwood-park-mayo-unf`, `downtown-jacksonville`, `ponte-vedra-beach-sawgrass`, `riverside-avondale-brooklyn`,
`southbank-san-marco`, `yulee-nassau-i95` — sit below their own publication minimum of 5 and **were not forced**.
Their hotels still publish under the market hub; a suppressed corridor is a threshold, not a gap.

**Downtown Jacksonville is one of the suppressed seven**, which is the source-ready order's central geographic
finding arriving intact at the release: downtown carries 5 of this market's 258 hotel-rank licences, and it does
not reach a corridor page.

## PHASE 8 — HOLD SAFETY

| | |
|---|---:|
| **APPROVED JACKSONVILLE PROFILES IN CANDIDATE** | **95** |
| **UNAPPROVED / HELD JACKSONVILLE PROFILES IN CANDIDATE** | **0** |
| Jacksonville pages in the candidate | 107 = 95 profiles + 10 corridors + hub + comparison |
| **KINGS AVENUE DUAL-BRAND PROFILES IN CANDIDATE** | **0** |

Kept unpublished, and checked against the **built artifact** rather than the partition — a hold honoured upstream
that leaks a page downstream is not a hold:

| | |
|---|---:|
| dual-brand profiles in the candidate | **0** |
| dual-brand **files** in the candidate | **0** |
| dual-brand **sitemap routes** | **0** |
| dual-brand **release-index routes** | **0** |
| `identity_resolutions.json` ruling written | **NO** |

Also unpublished: all **155** held rows (ACCESS_BLOCKED 53 including the 19 Marriott Akamai and 6 ESA DataDome
holds, ROUTING 43, SOURCE_SILENT 25, EVIDENCE 22, IDENTITY 12), and the **18** verified-no-pets rows, which are
exclusions in the authority shard and never profiles.

## PHASE 9 — GEOGRAPHY SAFETY

| | |
|---|---|
| **AMELIA ISLAND TIER** | **CORRIDOR** — publishes `/pet-friendly-hotels/jacksonville-fl/amelia-island-fernandina-beach/`, and no `amelia-island-fl` market document exists |
| **ST AUGUSTINE ADMITTED** | **0** |
| geography changed by this order | **NO** — no corridor registry, postal partition or market document was edited |

Amelia Island is the market's second-largest publishing corridor (11 published hotels behind
`jax-airport-northside`'s 13). It publishes as part of Jacksonville and is **not** promoted, exactly as decided.

## PHASE 10 — COLLISION SAFETY

Rechecked across the whole shared registry (1,189 rows, 35 markets):

| | |
|---|---:|
| **JACKSONVILLE-NC COLLISIONS** | **0** |
| **BARE-CHAIN CROSS-MARKET COLLISIONS** | **0** |
| **ANY-MARKET DUPLICATE EXCLUDED IDENTITY COLLISIONS** | **0** |
| duplicate canonical names anywhere in the registry | **0** |

**This market's canary is a LIVE market that shares its name**, and it is checked at the byte level rather than
at the registry level alone. `jacksonville-nc` is production market #22, Onslow County, North Carolina, and the
shared exclusion registry matches a normalised canonical name *before* it looks at an address:

| | |
|---|---:|
| `jacksonville-nc` profiles in the candidate | **16** (unchanged) |
| `jacksonville-nc` served routes, live vs candidate | **19 / 19, identical set** |
| `jacksonville-nc` files, live vs candidate | **99 / 99** |
| `jacksonville-nc` **bytes changed** | **0** |

No current live profile is displaced.

## PHASE 11 — FAST RECEIPT SAFETY

| | |
|---|---|
| selected receipt | `pkg-jacksonville-fl-60ba2edccd4882b3-b961d823ca502d7b.json` |
| CURRENTLY ELIGIBLE | **YES** (exactly one) |
| RULE J FILE COUNT | **603** > 0 ✅ |
| RULE J HTML COUNT | **587** > 0 ✅ |
| RULE J | **PASS**, `output_defects []` |
| RULE K | **PASS**, BYTE_IDENTICAL |
| bundle | `a98efbea…` — **not** `e3b0c442…` (the empty tree) ✅ |

**No vacuous historical receipt can be selected, and that is proved rather than asserted:** Augusta's historical
empty receipt is still on disk, and under today's reader it is **not currently eligible**, with defects
`EMPTY_BUNDLE` and `NO_HTML_OUTPUT`.

## PHASE 12 — DELTA AND FILE PRESERVATION

| | |
|---|---|
| UNEXPECTED MARKET DELTA | **`[]`** |
| UNEXPECTED PROFILE DELTA | **`[]`** |
| UNEXPECTED ROUTE DELTA | **`[]`** |
| UNEXPECTED SERVED ROUTE DELTA | **`[]`** |
| PRIOR MARKETS LOST | **0** |
| PRIOR PROFILES LOST | **0** |
| PRIOR RELEASE-INDEX ROUTES LOST | **0** |
| PRIOR SERVED ROUTES LOST | **0** |
| `release_diff_passed` / findings | **true** / `{}` |

File-level, comparing each bundle's own `file_hash_manifest.json` by sha256:

| | |
|---|---:|
| files live / candidate | 14,760 / **15,342** |
| **FILES ADDED** | **582** — *all 582 Jacksonville* |
| **FILES REMOVED** | **0** |
| **FILES CHANGED** | **1** |
| unexplained removed files | **0** |
| unexplained prior-market file changes | **0** |
| **unclassified paths** | **0** |

Every changed global artifact classified — and there is exactly one:

| Path | Class | Why |
|---|---|---|
| `sitemap.xml` | `global_regenerated` | the one global surface that must change when a market's routes join the release |

**Not even the navigation indexes moved.** `index.html` and `pet-friendly-hotels/index.html` are byte-identical,
because Jacksonville is hidden from navigation and from the sitemap flags at this stage exactly as every recently
launched market is. Checked market by market across all 158 market-owned path prefixes: **no prior market has a
single changed file.**

## PHASE 13 — RELEASE GATES

| Gate | Result |
|---|---|
| FOUNDER AUTHORIZATION | **PASS** — written by `extend_decision`, `decision_problems []` |
| PACKAGE IDENTITY | **PASS** — digest verified against the sealed package |
| FAST RECEIPT ELIGIBILITY | **PASS** — 1 currently eligible, non-vacuous |
| PARENT IDENTITY | **PASS** — package parent = resolved deploy = deployed bundle = comparison artifact |
| PARENT ROUTES PRESERVED | **PASS** — 2,701/2,701 index and 2,767/2,767 served present in the candidate |
| PROFILE PRESERVATION | **PASS** — +95 and nothing else |
| ROUTE PRESERVATION | **PASS** — +106 index / +107 served and nothing else |
| MARKET DELTA | **PASS** — +1, Jacksonville alone |
| PARTICIPATION | **PASS** — one gained, none lost, no other row moved |
| CANDIDATE DETERMINISM | **PASS** — **15,342 files compared, 0 differing, BYTE_IDENTICAL** |
| DEPLOYMENT ELIGIBILITY | **PASS** — deployable true, `deployability_problems []` |
| ALL_ACCOUNTING_GATES | **PASS**, `problems []` |

Candidate state: **AUTHORIZED and DEPLOYABLE**. Not deployed.

### A process note that belongs in the record

Build A wrote its manifests at 14:02 and then **hung**, sitting at roughly 0.03 CPU-seconds per second with its
outputs already complete, while build B was starting. Three things were checked before trusting either build:
build A's bundle hash was read three times across several minutes and never moved; the full accounting gates
passed against its output; and both builds read the same **committed tree**, not each other's output, so the
determinism comparison is between two independent renders of identical inputs. Build A was then terminated and
its bytes re-confirmed unchanged. The two builds agree byte for byte across all 15,342 files.

## PHASE 14 — DEPLOYMENT AUTHORIZATION (CREATED, NOT CONSUMED)

| | |
|---|---|
| **DEPLOYMENT AUTHORIZATION CREATED** | **YES** |
| **DEPLOYMENT AUTHORIZATION ID** | **`ptf-auth-jacksonville-003-f82f0714db2d`** |
| **AUTHORIZED BUNDLE** | `f82f0714db2dd4d714b6b789c68492f60de8a1f3287a11b1e6f1afd680cf0c4e` |
| **AUTHORIZED SITEMAP** | `d34b0e5d7d5ed045a3f727e49f18e2fe61de3df108e9ef0666c5413d1bb48e4f` |
| **AUTHORIZED PARENT** | `6ab599163f833ab7f48b395d` |
| rollback target | `6ab599163f833ab7f48b395d` — what production serves today |
| status | **AUTHORIZED** |
| bound to candidate bytes | **true** |
| `verify_authorization` / `deployability` problems | `[]` / `[]` |
| **CONSUMED** | **NO** |
| deployment record exists | **NO** |

The candidate manifest was written to the **candidate** path
(`global_deployment_manifest_candidate_jacksonville_003.json`), **not** to `global_deployment_manifest.json`.
This order stops before deployment, so overwriting the live manifest would leave the repository's own cross-check
describing a bundle production does not serve. The deploying order writes the live manifest from these same
bytes.

The authorization's own prose was rewritten from the cloned parent: it binds **this** founder's words, **this**
parent and **this** package. A clone that kept West Palm Beach's sentences would have bound Jacksonville's bundle
to another market's founder statement, its superseded authorization and its identity correction — the same defect
class as the cloned release contract that carried the Palm Beaches' geography during registration.

## PHASE 15 — FINAL LIVE SAFETY

Re-verified externally **after** everything above:

| | |
|---|---|
| CURRENT LIVE DEPLOYMENT | `6ab599163f833ab7f48b395d` — **unchanged** |
| CURRENT LIVE SITEMAP | `8ae34cea…` — **unchanged, byte-identical** |
| live served routes | **2,767** — unchanged |
| live markets / profiles | 33 / 2,424 — unchanged |
| jacksonville-fl routes in the live sitemap | **0** |

| Route | Expected | Actual |
|---|---|---|
| `/pet-friendly-hotels/jacksonville-fl/` | 404 | **404** ✅ |
| `/pet-friendly-hotels/jacksonville-fl/jax-airport-northside/` | 404 | **404** ✅ |
| `/pet-friendly-hotels/jacksonville-fl/policy-comparison/` | 404 | **404** ✅ |
| `/pet-friendly-hotels/west-palm-beach-fl/` | 200 | **200** ✅ |
| `/pet-friendly-hotels/fort-lauderdale-fl/` | 200 | **200** ✅ |
| `/pet-friendly-hotels/augusta-ga/` | 200 | **200** ✅ |
| `/pet-friendly-hotels/detroit-ann-arbor-mi/` | 404 | **404** ✅ |

**No Jacksonville route is live.**

---

## FINAL ANSWERS

```
 1. CURRENT LIVE DEPLOYMENT              = 6ab599163f833ab7f48b395d (west-palm-beach-fl),
                                           source e3efa2210f759886aaad830b07fa241231a8f734,
                                           bundle 23728b4b..., sitemap 8ae34cea..., HOST VERIFIED true
 2. CURRENT LIVE MARKETS                 = 33
 3. CURRENT LIVE PROFILES                = 2,424
 4. CURRENT LIVE RELEASE-INDEX ROUTES    = 2,701
 5. CURRENT LIVE SERVED ROUTES           = 2,767
 6. REGISTERED PACKAGE                   = pkg-jacksonville-fl-60ba2edccd4882b3
 7. PACKAGE DIGEST                       = sha256:60ba2edccd4882b38785d69c016f39f550924675d54197004
                                           adaf994b55c0536
 8. FOUNDER AUTHORIZATION CREATED        = YES
 9. FOUNDER AUTHORIZATION ID             = ptf-auth-jacksonville-003-f82f0714db2d
10. PARTICIPATION STATE                  = FOUNDER_AUTHORIZED_FOR_LAUNCH
                                           (34 of 35 authorized; Detroit withheld)
11. PARENT LOOKUP                        = PASS
12. PARENT ROUTES PRESERVED              = PASS (2,701/2,701 index, 2,767/2,767 served)
13. UNCHANGED BUNDLES REUSED             = 33
14. UNCHANGED MARKETS REBUILT            = 0
15. PHYSICAL FRAGMENTS RERENDERED        = 34 -- no populated release store in this worktree,
                                           so the composer rendered every fragment. NOT reuse.
16. JACKSONVILLE BUNDLES BUILT           = 1
17. AUTHORIZED CANDIDATE BUNDLE          = f82f0714db2dd4d714b6b789c68492f60de8a1f3287a11b1e6f1afd6
                                           80cf0c4e (sitemap d34b0e5d...)
18. CANDIDATE MARKETS                    = 34
19. CANDIDATE PROFILES                   = 2,519
20. CANDIDATE RELEASE-INDEX ROUTES       = 2,807
21. CANDIDATE SERVED ROUTES              = 2,874
22. JACKSONVILLE PROFILES                = 95
23. JACKSONVILLE RELEASE-INDEX ROUTES    = 106 (95 hotel + 10 corridor + 1 hub)
24. JACKSONVILLE SERVED ROUTES           = 107 (106 + the policy-comparison page)
25. JACKSONVILLE CORRIDORS               = 17 registered / 16 containing a published hotel /
                                           10 publishing their own page / 0 forced
26. UNAPPROVED JACKSONVILLE PROFILES     = 0
27. KINGS AVENUE DUAL-BRAND PROFILES     = 0 (0 profiles, 0 files, 0 sitemap routes,
                                           0 release-index routes; no ruling written)
28. AMELIA ISLAND TIER                   = CORRIDOR (not promoted; no market document exists)
29. ST AUGUSTINE ADMITTED                = 0
30. JACKSONVILLE-NC COLLISIONS           = 0 (and 0 bytes of jacksonville-nc changed)
31. BARE-CHAIN COLLISIONS                = 0
32. FAST RECEIPT ELIGIBLE                = YES (1 currently eligible; Augusta's historical empty
                                           receipt remains INELIGIBLE: EMPTY_BUNDLE, NO_HTML_OUTPUT)
33. RULE J NONEMPTY                      = PASS (603 files / 587 html / 0 defects)
34. RULE K NONVACUOUS                    = PASS (BYTE_IDENTICAL, 4 cold builds, 0 reuse hits)
35. ALL RELEASE GATES                    = PASS (12 of 12; ALL_ACCOUNTING_GATES PASS, problems [])
36. UNEXPECTED DELTA                     = NONE -- market [], profile [], route [], served route []
37. CANDIDATE DEPLOYABLE                 = YES (determinism BYTE_IDENTICAL over 15,342 files,
                                           0 differing)
38. DEPLOYMENT AUTHORIZATION CREATED     = YES -- ptf-auth-jacksonville-003-f82f0714db2d,
                                           AUTHORIZED and UNCONSUMED
39. CURRENT LIVE MODIFIED                = NO (sitemap re-fetched after all work: 8ae34cea...,
                                           2,767 routes, byte-identical)
40. DEPLOYMENT PERFORMED                 = NO (Netlify not invoked; no deployment record)
41. JACKSONVILLE LIVE                    = NO (hub, a corridor and the comparison page all 404)
42. origin == HEAD                       = YES
43. tree clean                           = YES
44. READY FOR JACKSONVILLE PRODUCTION
    DEPLOYMENT                           = YES
```

### Answers 42 and 43 were measured after the push, not pre-written

```
$ git push                       # f9e91669..42f3996b
$ git fetch origin worker/ptf-jacksonville-fl-market-001
$ git rev-parse HEAD             -> 42f3996bde417ba50eac6852650ed997fef74708
$ git rev-parse origin/worker/ptf-jacksonville-fl-market-001
                                 -> 42f3996bde417ba50eac6852650ed997fef74708
origin == HEAD : YES
$ git status --porcelain         # no output
tree clean : YES
```

This document is committed and pushed on top, and both checks are re-run against that commit; both still hold.

| Commit | What it holds |
|---|---|
| `f9e91669` | the registered, authorization-ready market (order 002) |
| `e7e02d43` | the founder launch decision and the participation flip |
| `42f3996b` | the authorized candidate's accounting, the deployment authorization and this report |

---

## WHAT REMAINS FOR THE DEPLOYING ORDER

Everything is staged and nothing is spent. A production deployment order needs to:

1. **Consume `ptf-auth-jacksonville-003-f82f0714db2d`** — it is AUTHORIZED, bound to the exact candidate bytes,
   and unconsumed.
2. **Deploy bundle `f82f0714…`** with rollback target `6ab599163f833ab7f48b395d`, the deployment production
   serves today.
3. **Write the live manifest from these same bytes.** This order deliberately wrote the candidate manifest to
   `global_deployment_manifest_candidate_jacksonville_003.json` and left `global_deployment_manifest.json`
   describing what production actually serves.
4. Expect afterwards: **34 markets / 2,519 profiles / 2,807 release-index routes / 2,874 served routes**, with
   Jacksonville's 107 routes newly 200 and every one of the prior 2,767 unchanged.

Two things a deploying order should not be surprised by. The candidate was assembled with **34 physical fragment
renders**, not 33 reuses plus one build — this worktree has no populated release store, and the distinction is
recorded rather than smoothed over. And Jacksonville ships **hidden from global navigation and from the sitemap
flags**, exactly as every recently launched market does at this stage; making it navigable is a later, separate
decision.
