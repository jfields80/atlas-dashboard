# PTF-JACKSONVILLE-FL-REGISTRATION-AND-STAGING-002 — FINAL

`jacksonville-fl` (Jacksonville / Northeast Florida) is **REGISTERED** and **AUTHORIZATION_READY**, with a
**validated PROJECTED, NON-DEPLOYABLE candidate**. Branch `worker/ptf-jacksonville-fl-market-001`, source commit
in `bbdf2259`.

No founder launch authorization. No deployment authorization. Nothing deployed. Current live untouched.
No broad regression.

---

## PHASE 1 — CURRENT LIVE

Resolved by the repaired resolver with host verification (`release_index live-source --verify-host`, 3.4 s).
`origin/main` was **not** used and the resolver reports it stale.

| | |
|---|---|
| CURRENT LIVE SOURCE COMMIT | `e3efa2210f759886aaad830b07fa241231a8f734` (built_from `ff6b506d`) |
| CURRENT LIVE DEPLOYMENT | `6ab599163f833ab7f48b395d` (west-palm-beach-fl), rollback `6ab1a035c7ef3b14a23a4ec6` |
| CURRENT LIVE BUNDLE | `23728b4bff71c66d0a9a063de3882d744f92465f5f568f72b3caf16ca8641d78` |
| CURRENT LIVE SITEMAP | `8ae34cea1c7e384f0f4c8499066c5ff2f9ca841d099c344a5860041b4b6c7546` |
| CURRENT LIVE MARKETS | **33** |
| CURRENT LIVE PROFILES | **2,424** |
| CURRENT LIVE RELEASE-INDEX ROUTES | **2,701** |
| CURRENT LIVE SERVED ROUTES | **2,767** |
| HOST VERIFIED | **true** |

The release-index count was **derived, not assumed**: summing each participating market's committed release
contract gives hotels 2,424 + corridors 244 + hubs 33 = **2,701**, and the served count was confirmed by fetching
`https://pettripfinder.com/sitemap.xml` — 2,767 `<loc>` entries, sha256 `8ae34cea…`, byte-identical to the
deployment record. Detroit is absent from the participating set; `jacksonville-nc` is present and live with 19
served routes.

## PHASE 2 — JACKSONVILLE PACKAGE (nothing rebuilt)

HEAD contains `bbdf2259`. Every requirement re-read from the committed receipt, and **no** census, discovery,
Firecrawl, browser, Marriott-closure or competitor work was re-run.

| | |
|---|---|
| PACKAGE | `pkg-jacksonville-fl-e9cbc9abbb727694` ✅ |
| SOURCE READY / COVERAGE READY | YES / YES ✅ |
| ACTIONABLE UNRESOLVED | **0** ✅ |
| PET-FRIENDLY / VERIFIED NO-PETS | **95 / 18** ✅ |
| FAST | 15/15 PASS, 0 UNKNOWN, 0 FAILED ✅ |
| RULE J | `file_count` **603**, `html_count` **587**, non-empty **YES** ✅ |
| RULE K | **BYTE_IDENTICAL**, 4 cold builds, 0 reuse hits ✅ |
| PACKAGE REPRODUCIBLE | YES ✅ |

## PHASE 3 — CANONICAL FRESH-MARKET REGISTRATION

Performed in full, in dependency order.

**Promotion out of `SHADOW_UNTIL_REGISTERED` was a REPOINT of the writers, not a copy of their output.** Sixteen
market-local modules were repointed from the shadow zone to the registered zone, so each registered artifact is
the module's own product and stays reproducible:

- census → `launch_packages/pettripfinder/identity_census/jacksonville-fl.json`
- market document → `launch_packages/pettripfinder/markets/jacksonville-fl.json`
- policy package → `hotel_policy_facts_jacksonville-fl.json` at the **package root**
- proposed authority → `jacksonville_fl_proposed_authority_001.json` at the **package root** — the **role name**
  the classifier recognises; the staged name already matched, so this was a move and not a rename
- final partition → `jacksonville_fl_final_partition_001.json` at the **package root**

**All four promoted documents are byte-identical to the sealed originals** (`sha256sum` on each pair), so the
promotion moved bytes rather than rebuilding them. The market document was additionally re-derived by re-running
the geography module at its new target: `git diff` is empty.

Then:

- **authority shard** `markets/authority/jacksonville-fl/` — 95 seed rows, 18 exclusions, routing and affiliate
  shards written **empty** (an empty shard is a statement; a missing one is a silence)
- **deterministic global regeneration** from the shards — `hotel_exclusions.json` 1,171 → **1,189**,
  `seed_businesses.csv` 2,573 → **2,668**, `ptf_global_authority_manifest.json`; 35 markets sharded, build marker
  `sha256:7895e9e9…`; then `--check` → *all generated artifacts match the shards*
- **release contract** `deploy/netlify/release_contracts/jacksonville-fl.json`, fully derived, **0
  disagreements**; `release_contracts` verifies **all 35** contracts with **0** disagreements anywhere
- **`registration_release_lane register`** — participation reissued, build-closure extended by exactly the two
  paths a registered market adds (its market document and its release contract)
- **`registration_release_lane seal --work-order`** — registered package, FAST receipt, market-state pin
- **`registration_release_lane packet`** — automatic classification, AUTHORIZATION_READY

**Not written, deliberately:** `identity_resolutions.json` (unchanged — Phase 7).

### The one write that needed founder approval

`build_global_authority --write` was refused by auto mode as *Modify Shared Resources*. The order's Phase 3
authorizes it explicitly and forbids routing around permission controls, so the run **stopped and asked**. The
block was real and total: with the global seed file missing Jacksonville's 95 rows, `verified_public_hotels`
fails closed and the release contract, register, seal and packet are all unreachable. Approval was given and the
regeneration ran. It is deterministic — same shards, same bytes, no clock, no network — and `--check` confirms it.

### What the regeneration proved about this market's defining hazard

`build_global_authority` refuses a **duplicate excluded identity across every market**. West Palm Beach's own
registration was refused twice by that guard (`Best Western`, `Comfort Inn & Suites`). **Jacksonville raised
nothing.** The bare-chain repair made in the source-ready order — after FAST caught `home2 suites by hilton`
about to take miami-fl's identity — holds at the shared registry, and so does the jacksonville-nc name defence.

### The one defect found during promotion

The cloned release-contract writer still described **the Palm Beaches** — 15 corridors over 60 Palm Beach County
postal codes, Broward and Miami-Dade, the Port of Palm Beach, Tequesta, equestrian-season rentals. A contract's
prose is part of the contract, and this one is a shared deploy-time document, so a clone that keeps the parent's
geography states things that are false about this market in shared space. It is the same class of defect West
Palm Beach found in its policy package (`"market": "Fort Lauderdale, Florida"`). Rewritten from this market's own
geography: 17 corridors over 47 postal codes, four counties with three split, St. Augustine refused, JAX airport
earning a corridor, Mayport and NAS Jax carrying zero lodging licences, and the fact that the name *Jacksonville*
decides nothing because `jacksonville-nc` is live. Residual references to the parent market: **0**.

## PHASE 4 — TIMER

| | |
|---|---|
| **TOTAL PROMOTION / REGISTRATION WALL CLOCK** | **17 m 24 s** (16:14:56Z → 16:32:20Z) |
| **GENERIC REGISTRATION-LANE TIME** | **4 m 15 s** — `register` 5 s + `seal` 175 s + `packet` 72 s + the correctly-refused first `packet` 3 s |
| GENERIC LANE ≤ 5 min target | **PASS** |
| HARD LIMIT ≤ 10 min | **PASS** |

Inside the seal's 170.2 s: live parent read 30.1 s, package inputs 0.14 s, seal ×2 0.66 s, first-party gate
0.27 s, **FAST lane 138.4 s**, candidate compose ×2 0.24 s, market-state pin 0.07 s.

**Human / tool permission wait — reported separately as the order requires.** The auto-mode refusal, the approval
request and the answer all fall inside the ~13 minutes between the order start and the lane start, together with
the repoint, the promotion, the shard install and the contract derivation. That wait was **not separately
instrumented**, so it is bounded by that window rather than measured; the lane time above contains none of it.

## PHASE 5 — AUTOMATIC CLASSIFICATION

Classifier ran automatically (`classification_source: AUTOMATIC`), resolving current live itself.

| | |
|---|---|
| CHANGE CLASS | **`COMPOSITE_FRESH_MARKET_DATA_ONLY`** |
| ELIGIBLE | **YES** |
| **FULL_REGRESSION_REQUIRED** | **NO** |
| REMOTE BROAD JOBS REQUIRED | **0** |
| BROAD REGRESSION RUNS | **0** |
| FAST | **ALL PASS** |
| inherited factory paths | **0** |
| plan modules | 119 |
| assembly required | false |

Reason, in the classifier's own words: *every changed file classifies into a narrow class
(COMPOSITE_FRESH_MARKET_DATA_ONLY, DOCUMENTATION_ONLY, GENERATED_REPORT_ONLY, MARKET_DATA_PACKAGE); no row of the
matrix makes a broad regression mandatory.*

**The first `packet` was REFUSED, and the refusal was correct:** `DIRTY_WORKTREE: commit the registration first;
the classifier proves committed bytes`. The registration was committed (`50c164b0`) and the packet then passed.
A classifier that read an uncommitted tree would be proving nothing.

## PHASE 6 — REGISTRATION SAFETY

| | |
|---|---|
| SHARED FACTORY IMPLEMENTATION CHANGES | **0** — no `.py` outside `jacksonville_fl_*` changed; classifier agrees (`inherited_factory_paths: 0`, `SHARED_FACTORY_DELTA: null`) |
| UNKNOWN CHANGE PATHS | **0** |
| CROSS-MARKET SOURCE CHANGES | **0** |
| CURRENT LIVE DEPLOYMENT CHANGED | **NO** — `6ab599163f833ab7f48b395d`, re-resolved at report time |
| CURRENT SERVED SITEMAP CHANGED | **NO** — re-fetched at report time, sha256 `8ae34cea…`, 2,767 routes, byte-identical |
| JACKSONVILLE LIVE | **NO** |

Every changed path is either Jacksonville-owned or a **deterministically regenerated shared artifact**, and each
of the latter was diffed for foreign content:

| Shared artifact | Change |
|---|---|
| `hotel_exclusions.json` | +540 lines, −0 — Jacksonville's 18 exclusions only |
| `seed_businesses.csv` | +95, −0 — Jacksonville's 95 seed rows only |
| `ptf_global_authority_manifest.json` | one market entry added |
| `launch_participation.json` | **REISSUED**, never edited |
| `bundle_cache_closure.json` | +2 declared paths (this market's document and contract) |
| `tests/pettripfinder/pins/market_state.json` | Jacksonville's pin block |

**The participation reissue was verified row by row: 34 → 35 markets, exactly one added (`jacksonville-fl`),
zero removed, and zero existing rows changed.** A hand-added row would break the decision chain and make every
market read UNLISTED; reissue is the only correct mechanism, and the diff proves it behaved as one.

No deployment record and no deployment authorization was added.

## PHASE 7 — DUAL-BRAND HOLD SAFETY

| | |
|---|---|
| **DUAL-BRAND HELD ROWS** | **2** |
| **DUAL-BRAND PROFILES IN PROJECTED CANDIDATE** | **0** |
| `identity_resolutions.json` | **UNCHANGED** |

Both rows sit at **1201 Kings Avenue, 32207** and are held `IDENTITY_MISMATCH_HOLD` with the same reason —
*SAME PREMISES, TWO IDENTITIES (address_key `1201|kings|32207`)*:

- `hilton garden inn jacksonville downtown southbank`
- `homewood suites by hilton jacksonville downtown southbank`

Neither appears in the 95 published seed rows. No shared identity ruling was invented, and no founder identity
edit was required for this registration.

## PHASE 8 — PROJECTED PARTICIPATION

Constructed **in memory only** by the lane. Jacksonville's persisted participation row is
`SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH`. The lane reports `nothing_deployed: true`,
`nothing_activated: true`, `participation_untouched: true`. Candidate mode is **PROJECTED / NON-DEPLOYABLE**:
the receipt carries `PRODUCTION_ACTIVATION_ALLOWED = NO`.

## PHASE 9 — PARENT LOOKUP

| | |
|---|---|
| PARENT LOOKUP | **PASS** |
| PARENT FOUND BY DEPLOYED BUNDLE | **PASS** |
| PARENT ROUTES PRESERVED | **PASS** |

The receipt's `PARENT_RELEASE` resolves `live_deploy_id 6ab599163f833ab7f48b395d`, `rollback_target
6ab1a035c7ef3b14a23a4ec6`, `source_commit ff6b506d…` and `live_index_digest sha256:fda6317b…` — the repaired
deployed-content identity semantics, which resolve the deployed parent by **bundle**, not by a store key that
moves on registration. Rule **H** (*every unrelated live market/member is preserved*) and rule **I** (*every
removal is explicitly intended*) both PASS.

## PHASE 10 — STAGING, AND WHAT WAS ACTUALLY REUSED

| | |
|---|---|
| **UNCHANGED BUNDLES REUSED** | **33** = CURRENT LIVE MARKET COUNT |
| **UNCHANGED MARKETS REBUILT** | **0** |
| **JACKSONVILLE BUNDLES BUILT** | **1** |

**Stated precisely, because the order asks not to mislabel re-rendering as reuse:** this staging composed the
**release index**, not a physical whole-site artifact. The candidate index was composed twice in **0.24 s total**
from the 33 unchanged markets' committed index entries, and the two compositions agree
(`candidate_index_digest == recomposed_index_digest`, `CANDIDATE_REPRODUCIBLE = YES`). The only physical build
was Jacksonville's own market bundle, scoped by the builder to `jacksonville-fl — 95 owned inventory rows`, and
FAST executed 4 cold builds of it in 138.4 s.

**No physical fragment re-rendering of other markets occurred, because no whole-site assembly was run at all**
(`assembly_required: false`). That is a stronger statement than reuse from a populated release store, and it is
not the same statement — there is nothing here to mislabel.

## PHASE 11 — PROJECTED ACCOUNTING, DERIVED TWO WAYS

The two route accounting systems were derived **independently** and then compared.

**System A — the release index** (contracts and package):

| | |
|---|---:|
| JACKSONVILLE PROJECTED PROFILES | **95** |
| JACKSONVILLE HUB ROUTES | **1** |
| JACKSONVILLE CORRIDOR ROUTES | **10** (of 17 corridors) |
| JACKSONVILLE OTHER MARKET-OWNED ROUTES | **1** (policy-comparison) |
| **JACKSONVILLE RELEASE-INDEX ROUTES** | **106** = 95 + 10 + 1 hub |
| CANDIDATE RELEASE-INDEX ROUTES | 2,701 + 106 = **2,807** |

**System B — the served sitemap**, counted from the sitemap the seal actually built (`oa/site/sitemap.xml`):
112 `<loc>` entries, of which **107 are Jacksonville-owned** (95 hotels + 10 corridors + 1 hub + 1
policy-comparison) and 5 are pre-existing global pages.

| | |
|---|---:|
| **JACKSONVILLE SERVED SITEMAP ROUTES** | **107** |
| CANDIDATE SERVED ROUTES | 2,767 + 107 = **2,874** |

**The two systems agree**: the lane's independently reported candidate is **34 markets / 2,519 profiles / 2,807
routes**, and System A derived 2,807 without reading it. The release-index count excludes the policy-comparison
page and the served count includes it — that one-route difference per market is the whole of the gap, and it is
why the two systems are kept separate rather than reconciled by arithmetic.

| | |
|---|---:|
| CANDIDATE MARKETS | **34** |
| CANDIDATE PROFILES | **2,519** |
| CANDIDATE RELEASE-INDEX ROUTES | **2,807** |
| CANDIDATE SERVED ROUTES | **2,874** |

## PHASE 12 — PUBLISHABLE COHORT SAFETY

| | |
|---|---:|
| **APPROVED JACKSONVILLE PROFILES IN CANDIDATE** | **95** |
| **UNAPPROVED / HELD JACKSONVILLE PROFILES IN CANDIDATE** | **0** |

The release contract states it directly: *95 published / 0 held of 95 seed rows*. The first-party gate evaluated
**113 records, 113 eligible, 0 ineligible**. Everything else remains non-profile state: 18 verified-no-pets
(exclusions, not profiles), 155 held rows — ACCESS_BLOCKED 53 (including the 19 Marriott Akamai holds and the 6
ESA DataDome holds), ROUTING 43, SOURCE_SILENT 25, EVIDENCE 22, IDENTITY 12 (including the 2 dual-brand rows).

## PHASE 13 — CROSS-MARKET COLLISION SAFETY

Both classes reverified explicitly against **every** market's authority shard, in all four directions.

**A. jacksonville-nc collisions — `0`**

| Direction | Collisions |
|---|---:|
| FL seed vs NC seed | **0** |
| FL seed vs NC exclusion | **0** |
| FL exclusion vs NC seed | **0** |
| FL exclusion vs NC exclusion | **0** |

**B. bare-chain cross-market collisions — `0`**

| | |
|---|---:|
| Jacksonville FL seed names also seeded in ANY other market | **0** |
| Jacksonville FL exclusions also excluded in ANY other market | **0** |
| Bare-chain names in the published seed | **0** |
| Bare-chain names in the exclusions | **0** |

`build_global_authority` — which refuses a duplicate excluded identity across all 35 markets — raised nothing.
No existing live market or profile is displaced: rule **G** (no forbidden collision) PASS, rule **H** (every
unrelated live market preserved) PASS.

## PHASE 14 — CANDIDATE DELTA

| | |
|---|---|
| UNEXPECTED MARKET DELTA | **`[]`** |
| UNEXPECTED PROFILE DELTA | **`[]`** |
| UNEXPECTED ROUTE DELTA | **`[]`** |

`release_diff_passed: true`, `finding_counts: {}`, and the packet's own projection reports
`unexpected_market_changes: 0`, `unexpected_profile_changes: 0`, `unexpected_route_changes: 0`.

Measured delta: **markets +1, profiles +95, routes +106**. The set of unchanged markets in the candidate is
**exactly equal** to the set of live participating markets (33 of 33, proved by set equality, not by count).
Jacksonville is the only added market.

## PHASE 15 — FAST RECEIPT ELIGIBILITY

Read through the current receipt-reader semantics (`fast_release_lane.eligible_receipts`), which judge **current**
eligibility and reject a vacuous receipt on today's rule.

| | |
|---|---|
| CURRENTLY ELIGIBLE receipts for this package | **1** |
| receipt | `pkg-jacksonville-fl-60ba2edccd4882b3-b961d823ca502d7b.json` |
| `file_count > 0` | **603** ✅ |
| `html_count > 0` | **587** ✅ |
| `bundle != e3b0c442…` (empty tree) | `a98efbea86c38a268bfa489354add4a700a0d4bc0ab13df740a5ae35ee842636` ✅ |
| RULE J | **PASS**, `output_present: true`, `output_defects: []` |
| RULE K | **PASS**, `BYTE_IDENTICAL` |
| ELIGIBLE / PRODUCTION_ACTIVATION_ALLOWED | **YES / NO** |

No historical vacuous receipt qualifies — exactly one receipt is currently eligible, and it is this
registration's. **The registered package builds the identical bundle `a98efbea…` that the source-ready shadow
package built**, which is the strongest available statement that registration moved the market without changing
it.

## PHASE 16 — STAGING GATES

| Gate | Result |
|---|---|
| package identity | **PASS** — `pkg-jacksonville-fl-60ba2edccd4882b3`, `PACKAGE_REPRODUCIBLE YES` |
| registration classification | **PASS** — `COMPOSITE_FRESH_MARKET_DATA_ONLY`, broad NO |
| FAST receipt eligibility | **PASS** — 1 currently-eligible, non-vacuous receipt |
| FAST rules A–O | **PASS** — 15/15, 0 UNKNOWN, 0 FAILED |
| parent identity | **PASS** — parent found by deployed bundle |
| parent routes preserved | **PASS** — rules H and I |
| market preservation | **PASS** — 33 of 33 live markets preserved (set equality) |
| profile preservation | **PASS** — +95 and nothing else |
| route preservation | **PASS** — +106 index / +107 served and nothing else |
| candidate delta | **PASS** — `release_diff_passed`, 0 findings |
| participation projection | **PASS** — in memory; persisted row is SOURCE_READY, not LIVE |
| collision safety | **PASS** — 0 jacksonville-nc, 0 bare-chain, 0 any-market duplicates |
| first-party binding | **PASS** — 113 evaluated, 0 ineligible |
| release contracts | **PASS** — all 35 verify, 0 disagreements |
| global authority | **PASS** — `--check`: all generated artifacts match the shards |
| **deployment eligibility refusal** | **PASS (EXPECTED)** |

**Deployment refusal, proved rather than asserted:** 0 deployment authorizations naming jacksonville-fl (of 37 on
disk), 0 deployment records, participation `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH`, and of the 33
markets that are `FOUNDER_AUTHORIZED_FOR_LAUNCH`, Jacksonville is **not** one.

## PHASE 17 — NO DEPLOYMENT, AND LIVE RE-VERIFIED

Nothing created a founder authorization, a deployment authorization, a Netlify invocation, a deployment record or
a LIVE flag.

Re-verified against the host **at report time**:

| Route | Expected | Actual |
|---|---|---|
| `/pet-friendly-hotels/jacksonville-fl/` | 404 | **404** ✅ |
| `/pet-friendly-hotels/west-palm-beach-fl/` | 200 | **200** ✅ |
| `/pet-friendly-hotels/fort-lauderdale-fl/` | 200 | **200** ✅ |
| `/pet-friendly-hotels/augusta-ga/` | 200 | **200** ✅ |
| `/pet-friendly-hotels/detroit-ann-arbor-mi/` | 404 | **404** ✅ |
| `/pet-friendly-hotels/jacksonville-nc/` | — | **200** (the live NC market, untouched) |

Live sitemap re-fetched: **2,767 routes, sha256 `8ae34cea…`** — identical to the deployment record and to the
pre-registration fetch. `jacksonville-fl` routes in the live sitemap: **0**.

---

## FINAL ANSWERS

```
 1. CURRENT LIVE DEPLOYMENT              = 6ab599163f833ab7f48b395d (west-palm-beach-fl),
                                           source e3efa2210f759886aaad830b07fa241231a8f734,
                                           bundle 23728b4b..., sitemap 8ae34cea...,
                                           rollback 6ab1a035c7ef3b14a23a4ec6, HOST VERIFIED true
 2. CURRENT LIVE MARKETS                 = 33
 3. CURRENT LIVE PROFILES                = 2,424
 4. CURRENT LIVE RELEASE-INDEX ROUTES    = 2,701
 5. CURRENT LIVE SERVED ROUTES           = 2,767
 6. JACKSONVILLE PACKAGE                 = pkg-jacksonville-fl-60ba2edccd4882b3
                                           (registered; source package
                                           pkg-jacksonville-fl-e9cbc9abbb727694 verified unchanged)
 7. PACKAGE DIGEST                       = sha256:60ba2edccd4882b38785d69c016f39f550924675d54197004
                                           adaf994b55c0536
                                           (bundle a98efbea86c38a268bfa489354add4a700a0d4bc0ab13df
                                           740a5ae35ee842636 -- identical to the source package's)
 8. REGISTRATION CLASS                   = COMPOSITE_FRESH_MARKET_DATA_ONLY
 9. ELIGIBLE                             = YES
10. FULL_REGRESSION_REQUIRED             = NO
11. TOTAL PROMOTION / REGISTRATION
    WALL CLOCK                           = 17m24s (16:14:56Z -> 16:32:20Z)
12. GENERIC REGISTRATION-LANE TIME       = 4m15s (register 5s + seal 175s + packet 72s
                                           + the correctly-refused first packet 3s);
                                           the permission wait is outside this and was not
                                           separately instrumented
13. REGISTRATION <=5M TARGET             = PASS
14. REGISTRATION <=10M HARD              = PASS
15. BROAD REGRESSION RUNS                = 0 (remote broad jobs 0)
16. SHARED FACTORY PATHS                 = 0
17. UNKNOWN PATHS                        = 0
18. PARENT LOOKUP                        = PASS (parent found by deployed bundle)
19. PARENT ROUTES PRESERVED              = PASS
20. UNCHANGED BUNDLES REUSED             = 33
21. UNCHANGED MARKETS REBUILT            = 0
22. JACKSONVILLE BUNDLES BUILT           = 1
23. JACKSONVILLE PROJECTED PROFILES      = 95
24. JACKSONVILLE RELEASE-INDEX ROUTES    = 106 (95 hotel + 10 corridor + 1 hub)
25. JACKSONVILLE SERVED ROUTES           = 107 (106 + the policy-comparison page)
26. CANDIDATE MARKETS                    = 34
27. CANDIDATE PROFILES                   = 2,519
28. CANDIDATE RELEASE-INDEX ROUTES       = 2,807
29. CANDIDATE SERVED ROUTES              = 2,874
30. APPROVED JACKSONVILLE PROFILES       = 95
31. UNAPPROVED JACKSONVILLE PROFILES     = 0
32. DUAL-BRAND HELD ROWS                 = 2 (0 in the candidate;
                                           identity_resolutions.json unchanged)
33. JACKSONVILLE-NC COLLISIONS           = 0
34. BARE-CHAIN CROSS-MARKET COLLISIONS   = 0
35. FAST RECEIPT CURRENTLY ELIGIBLE      = YES (exactly 1; file_count 603, html_count 587,
                                           bundle != e3b0c442..., 0 output defects)
36. RULE J NONEMPTY                      = PASS
37. RULE K NONVACUOUS                    = PASS (BYTE_IDENTICAL, 4 cold builds, 0 reuse hits)
38. ALL STAGING GATES                    = PASS (16 of 16)
39. DEPLOYMENT REFUSAL                   = PASS (EXPECTED) -- 0 authorizations, 0 records,
                                           PRODUCTION_ACTIVATION_ALLOWED = NO
40. CURRENT LIVE MODIFIED                = NO (sitemap re-fetched at report time, sha256
                                           8ae34cea..., 2,767 routes, byte-identical)
41. DEPLOYMENT PERFORMED                 = NO
42. JACKSONVILLE LIVE                    = NO (hub 404)
43. origin == HEAD                       = (verified after push -- see below)
44. tree clean                           = (verified after push -- see below)
45. READY FOR FOUNDER LAUNCH
    AUTHORIZATION                        = YES
```
