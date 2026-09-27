# PTF-DENVER-CO-REGISTRATION-AND-STAGING-002 — FINAL

`denver-co` (Denver / Boulder / Front Range, Colorado) is **REGISTERED** and **AUTHORIZATION_READY**, with a
validated **PROJECTED, NON-DEPLOYABLE** candidate.

- Branch: `worker/ptf-denver-co-market-001`
- Registration transaction: `83b9f6fb`, plus the classifier fix `8d9143ee`
- Source-ready commit: `84853470`

Boundaries kept:

- no founder launch authorization, no deployment authorization, no Netlify, nothing deployed
- current live untouched
- no broad regression, no spend, no Places
- `identity_resolutions.json` untouched and no ESA display name invented

**One finding for the founder before authorization** (§12a): one published row is a hotel whose own brand name says
it is *"Opening Early 2027"*.

---

## PHASE 1 — CURRENT LIVE

Resolved with host verification by `release_index live-source --verify-host` (2.9 s). The resolver reports `origin/main`
as stale, so it was not used.

| | |
|---|---|
| CURRENT LIVE SOURCE COMMIT | `f01587ba7d23a849e0c07b3cddd3250717e63b80` (built_from `34d523d9`) |
| CURRENT LIVE DEPLOYMENT | `6ab859787d349f8397e1450a` (san-diego-ca), rollback `6ab6c8798bd9daf5038ae3e5` |
| CURRENT LIVE BUNDLE | `553a858f2590094127ce68e63992c2c3dff969fcdc8f290decf112791f447eec` |
| CURRENT LIVE SITEMAP | `4f648fff6eaf50f7f7614eefda2639ac10c5cb678e77ef6fd15af60c89c0173e` |
| CURRENT LIVE MARKETS | **35** |
| CURRENT LIVE PROFILES | **2,666** |
| CURRENT LIVE RELEASE-INDEX ROUTES | **2,969** |
| CURRENT LIVE SERVED ROUTES | **3,037** |
| HOST VERIFIED | **true** |

The live sitemap was fetched: 3,037 `<loc>`, sha256 `4f648fff…`, byte-identical to the deployment record, with 0
Denver routes. The release-index figure is the deployment record's own live verification
(`live_release_index_routes 2969`).

## PHASE 2 — SEALED DENVER PACKAGE (nothing rebuilt)

Re-read from the committed shadow report and receipt. No census, acquisition, browser or competitor work was re-run.

| | |
|---|---|
| PACKAGE | `pkg-denver-co-8de3a042157dc335` ✅ |
| SOURCE READY | YES ✅ |
| FOUNDER COVERAGE DECISION | APPROVED (Phase 4) ✅ |
| ACTIONABLE UNRESOLVED | **0** ✅ |
| CENSUS / PF / NP / RESOLVED / UNRESOLVED | **441 / 289 / 46 / 335 / 106** ✅ |
| FAST | 15/15 PASS ✅ |
| RULE J | `file_count` **1,729**, `html_count` 1,713, non-empty **YES** ✅ |
| RULE K | **BYTE_IDENTICAL**, 4 cold builds, 0 reuse (non-vacuous) ✅ |
| PACKAGE REPRODUCIBLE | YES (independent detached-worktree reproduction, DIFFERING FILES 0) ✅ |

## PHASE 3 — THE 16 FOUNDER-DECISION ROWS, RECONCILED

**Source.** `markets/reports/denver_co_actionability_001.json` (committed at `84853470`), rows with `actionability =
REQUIRES_FOUNDER`, joined to the committed census and final partition.

**Result: TOTAL = 16, ENUMERATED = 16.**

**Where the "missing 7" are.** The order named 9 items: 7 buildings and 2 ESA rows. But every dual-brand building is
**two** rows. The 7 unnamed rows are the second halves of the 7 buildings, so 14 + 2 = 16. Nothing was invented and
the count did not change.

Every row below has hold class `IDENTITY_MISMATCH_HOLD` (final state `AWAITING_ROUTING_REPLACEMENT`, resolved = false).

| # | property id (slug) | canonical name | address | why founder decision |
|---:|---|---|---|---|
| 1 | fairfield-by-marriott-inn-and-suites-boulder-broomfield-interlocken | Fairfield by Marriott Inn & Suites Boulder Broomfield/Interlocken | 455 Zang St, 80021 | dual-brand building (denoo + denof): publishing needs a `same_campus_distinct_entity` row in the shared `identity_resolutions.json` |
| 2 | residence-inn-by-marriott-boulder-broomfield-interlocken | Residence Inn by Marriott Boulder Broomfield/Interlocken | 455 Zang St, 80021 | same building as #1 |
| 3 | comfort-suites-near-denver-downtown | Comfort Suites Near Denver Downtown | 620 Federal Blvd, 80204 | dual-brand (co317 + co318) |
| 4 | mainstay-suites-near-denver-downtown | MainStay Suites Near Denver Downtown | 620 Federal Blvd, 80204 | same building as #3 |
| 5 | mainstay-suites-denver-international-airport | MainStay Suites Denver International Airport | 5980 Tower Rd, 80249 | dual-brand (co337 + co338) |
| 6 | sleep-inn-and-suites-denver-international-airport | Sleep Inn & Suites Denver International Airport | 5980 N Tower Rd, 80249 | same building as #5 |
| 7 | hampton-inn-and-suites-denver-downtown-convention-center | Hampton Inn & Suites Denver Downtown-Convention Center | 550 15th St, 80202 | dual-brand (dencvhx + dendchw) |
| 8 | homewood-suites-by-hilton-denver-downtown-convention-center | Homewood Suites by Hilton Denver Downtown-Convention Center | 550 15th St, 80202 | same building as #7 |
| 9 | hampton-inn-aurora-medical-center-denver | Hampton Inn Aurora Medical Center Denver | 2556 N Oswego St, 80010 | dual-brand (denmahx + denskht) |
| 10 | home2-suites-by-hilton-aurora-medical-center-denver | Home2 Suites by Hilton Aurora Medical Center Denver | 2556 N Oswego St, 80010 | same building as #9 |
| 11 | homewood-suites-by-hilton-denver-airport-tower-road | Homewood Suites by Hilton Denver Airport Tower Road | 6951 Yampa St Suite A, 80249 | dual-brand (dendihw + dennyru) |
| 12 | tru-by-hilton-denver-airport-tower-road | Tru by Hilton Denver Airport Tower Road | 6951 Yampa St Suite B, 80249 | same building as #11 |
| 13 | candlewood-suites-greenwood-village-dtc | Candlewood Suites Greenwood Village – DTC | 9231 E Arapahoe Rd, 80112 | dual-brand (dengd + dengv) |
| 14 | holiday-inn-express-and-suites-greenwood-village-dtc | Holiday Inn Express & Suites Greenwood Village – DTC | 9231 E Arapahoe Rd, 80112 | same building as #13 |
| 15 | extended-stay-america-select-suites-denver-tech-center-south | Extended Stay America Select Suites Denver - Tech Center South | 9604 E. Easter Ave, 80112 | ESA title collision: shares its first 60 characters (the site's title limit) with #16; a display name is a founder naming decision |
| 16 | extended-stay-america-select-suites-denver-tech-center-south-greenwood-village | Extended Stay America Select Suites Denver - Tech Center South - Greenwood Village | 9253 E. Costilla Ave, 80112 | ESA title collision with #15 |

(The order wrote the second ESA name as "… Denver - Greenwood Village"; the brand's own name, used above, is "…
Tech Center South - Greenwood Village".)

**None is resolved here. ALL 16 REMAIN NONPUBLISHING = YES.** Each row's slug is absent from the built candidate
(Phase 14).

## PHASE 4 — FOUNDER COVERAGE DECISION, RECORDED

The decision is recorded in `markets/reports/denver_co_founder_coverage_decision_002.json`, using the same mechanism and
shape as San Diego's `…_founder_coverage_decision_002.json`.

- **Decision:** COVERAGE_READY = YES, basis FOUNDER DECISION.
- **Approved cohort:** 289 pet-friendly profiles, with 46 verified-no-pets exclusions.
- **Held:** 38 router-exhausted, 52 Places-gated / no-website and 16 founder-decision rows (106 in total), with
  the 16 enumerated.
- **What it does not do:** authorize Places spend, weaken any evidence rule, declare any held row resolved, publish
  any held row, write `identity_resolutions.json`, or invent an ESA display name.
- **Attribution:** it transcribes the work order's decision and **signs no reviewer name**.

## PHASE 5 — CANONICAL FRESH-MARKET REGISTRATION

In dependency order:

1. **Repoint, not copy.** 14 Denver modules were repointed from the shadow zone to the registered zone:
   - census → `identity_census/`
   - market document → `markets/denver-co.json`
   - policy package, proposed authority and final partition → the package root
2. **Promotion.**
   - The census and market document moved byte-for-byte (`git mv`, R100).
   - The policy package, proposed authority (`denver_co_proposed_authority_001.json`, the role name the classifier
     recognises) and final partition were regenerated by their own writers at the new targets.
   - **All five are byte-identical to the sealed originals.**
   - Re-running the geography writer at its new target produced no diff.
3. **Authority shard** (`market_registration_cli --write`).
   - Wrote 289 seed rows and 46 exclusions; the routing and affiliate shards are empty.
   - Its content is identical to the shard the shadow package sealed.
4. **Global regeneration** (`build_global_authority --write`, authorized by the operator in this session before it
   ran).

   | artifact | before | after | delta |
   |---|---:|---:|---|
   | `hotel_exclusions.json` | 1,281 | **1,327** | +46, all Denver, 0 removed |
   | `seed_businesses.csv` | 2,815 | **3,104** | +289, all Denver, 0 removed |
   | manifest | | | +1 market |

   - 37 markets sharded; build marker `sha256:06dd591b…`.
   - `--check`: *all generated artifacts match the shards*.
   - The cross-market duplicate-identity guard raised nothing.
5. **Release contract** `deploy/netlify/release_contracts/denver-co.json` (writer
   `denver_co_release_contract_002.py`).
   - Fully derived, **0 disagreements**.
   - The prose was rewritten from Denver's own geography, because the San Diego clone described San Diego County.
     Residual parent place names: **0**, except one factual "San Diego-live hardened lineage".
   - `release_contracts.verify_all()`: **all 37** contracts verify, **0** disagreements.
6. **`register`.** Participation was reissued, 36 → 37 rows (one added, 0 removed, **0 existing rows changed**,
   decision chain intact, `decision_problems` empty). The build closure gained exactly the two declared paths.
7. **`seal --work C:/t/den2a`.**
   - Registered package `pkg-denver-co-91b2e0a2da98b284`
     (`sha256:91b2e0a2da98b28425ee6b8058c2cd23fe2be9bf7738a9677e7c923b5269da2a`), FAST 15/15.
   - Market-state pin written; `reviewed_by` / `last_moved_by` = this work order.
8. **Commit** `83b9f6fb`, then **`packet --prepared-by PTF-DENVER-CO-REGISTRATION-AND-STAGING-002`**.
   - **The first `packet` refused, correctly.** The change-set check rejected
     `denver_co_clean_authority_001.py` as not market-local. It imported
     `engines.website_generation.constants.seo.TITLE_MAX_LENGTH`, which the source-ready order had added for the ESA
     title hold, and a market-local module may not import the website engine. Every other check was then reported
     "not evaluated".
   - Fix `8d9143ee`: the module states the limit (60) itself. Its output, `denver_co_clean_authority_001.json`, is
     **byte-identical**, and FAST rule J builds the real site, so a drift fails the seal.
   - The second `packet` returned **AUTHORIZATION_READY**.

**Classifier result.**

| | |
|---|---|
| CLASS | **`COMPOSITE_FRESH_MARKET_DATA_ONLY`** (classification_source AUTOMATIC) |
| ELIGIBLE | **YES**: 15/15 classifier checks PASS |
| FULL_REGRESSION_REQUIRED | **NO** |
| REMOTE BROAD JOBS | **0** |
| BROAD REGRESSION RUNS | **0** |
| assembly required | false |

**Same bundle as the shadow package.** The registered package builds the identical bundle
`03159c8d28c75750171707c38886e8a8d26b1a59fad546c9659891bfa1352df5` that the source-ready shadow package built.
Registration moved the market without changing it.

## PHASE 6 — TIMER

| | |
|---|---|
| **TOTAL PROMOTION / REGISTRATION WALL CLOCK** | **≈ 17 m 30 s**, from the order at 21:10:29Z to AUTHORIZATION_READY at ≈ 21:28:08Z; ≈ 18 m 24 s to the final live probe (21:28:53Z) |
| of which human permission wait | **63 s** (question 21:10:57Z → answer 21:12:00Z) |
| **GENERIC REGISTRATION-LANE TIME** | **≈ 7 m 16 s**: `register` ≈ 6 s + `seal` 361 s + `packet` 69 s. Counting the refused first `packet` (71 s) it is ≈ 8 m 27 s |
| ≤ 5 MINUTES TARGET | **FAIL** |
| ≤ 10 MINUTES HARD LIMIT | **PASS** (either way of counting) |

**Why the lane missed 5 minutes.** The seal's FAST lane took 316 s, because rules J and K build Denver's 1,729-file
bundle cold four times. San Diego's bundle was 881 files and its FAST lane took 166 s. Inside the seal, the live
parent read took 35.9 s and candidate composition ×2 took 0.33 s.

## PHASE 7 — REGISTRATION SAFETY

| | |
|---|---|
| SHARED FACTORY IMPLEMENTATION CHANGES | **0** (classifier: 0 shared paths; `SHARED_FACTORY_DELTA null`; no `.py` outside `denver_co_*` changed) |
| UNKNOWN PATHS | **0** (96 changed paths since base `1724e822`: 29 market-local, 13 registration data, 54 derived) |
| CROSS-MARKET SOURCE CHANGES | **0** |
| CURRENT PRODUCTION CHANGED | **NO** |
| DENVER LIVE | **NO** |

**Shared artifacts regenerated deterministically**, each diffed for foreign content:

- `hotel_exclusions.json`: +46, Denver only
- `seed_businesses.csv`: +289, Denver only
- `ptf_global_authority_manifest.json`: one market entry
- `launch_participation.json`: reissued, +1 row
- `bundle_cache_closure.json`: +2 paths
- `tests/pettripfinder/pins/market_state.json`: Denver's block

## PHASE 8 — HELD-COHORT SAFETY

| held class | rows | published |
|---|---:|---:|
| router-exhausted | 38 | **0** |
| Places-gated / no-website | 52 | **0** |
| founder-decision | 16 | **0** |
| **HELD ROWS PROMOTED TO PROFILE** | 106 | **0** |

This was checked against the candidate the seal actually built (`C:/t/den2a/oa/site`):

- No held row's slug is a profile directory or a sitemap route.
- No held row's name is among the 289 Denver rows of the global seed file.

`identity_resolutions.json` is **unchanged**, and no ESA name was altered.

## PHASE 9 — PROJECTED PARTICIPATION

The projection exists in memory only.

- The persisted row is `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH`.
- The lane reports `nothing_deployed: true` and `nothing_activated: true`.
- The receipt carries `PRODUCTION_ACTIVATION_ALLOWED = NO`.
- Readiness status is **AUTHORIZATION_READY**; founder status is **AWAITING_FOUNDER_AUTHORIZATION**.

The candidate is **PROJECTED / NON-DEPLOYABLE**.

## PHASE 10 — PARENT LOOKUP

| | |
|---|---|
| PARENT LOOKUP | **PASS**: live_deploy_id `6ab859787d349f8397e1450a`, rollback `6ab6c8798bd9daf5038ae3e5`, source `34d523d9`, live index `sha256:2c3f4ddd…`. The classifier's `sealed_package` check binds the package to the current live parent by deployed content |
| PARENT ROUTES PRESERVED | **PASS**: rule H (every unrelated live market preserved) and rule I (every removal intended; 0 removals); all 35 parent profile counts carried unchanged |

## PHASE 11 — STAGING, AND WHAT WAS REUSED

| | |
|---|---|
| **UNCHANGED BUNDLES REUSED** | **35** = the current live market count (`unchanged_markets` 35) |
| **UNCHANGED MARKETS REBUILT** | **0** |
| **DENVER BUNDLES BUILT** | **1** |

**Stated precisely.** The candidate **index** was composed twice (0.33 s) from the 35 unchanged markets' committed index
entries, and both compositions agree (`candidate_index_digest == recomposed_index_digest` `sha256:2635ea86…`,
CANDIDATE_REPRODUCIBLE YES).

**No whole-site assembly ran** (`assembly_required: false`), so no other market was physically re-rendered. The only
physical build was Denver's own bundle: 289 owned inventory rows, 4 cold builds inside FAST.

## PHASE 12 — PROJECTED ACCOUNTING (derived two ways)

**Release index.** Derived from the declared routes in the sealed package's intended delta, and from the lane's
candidate.

| | |
|---:|---:|
| DENVER PROJECTED PROFILES | **289** |
| DENVER HUB ROUTES | **1** |
| DENVER CORRIDOR ROUTES | **16** (of 20 corridors) |
| **DENVER RELEASE-INDEX ROUTES** | **306** = 289 + 16 + 1 |

**Served sitemap.** Counted from the sitemap the seal built (`C:/t/den2a/oa/site/sitemap.xml`): 312 `<loc>`.

- **307** are Denver-owned: 289 hotels, 16 corridors, 1 hub and 1 policy-comparison page.
- 5 are pre-existing global pages.

| | |
|---|---:|
| **DENVER SERVED ROUTES** | **307** |
| CANDIDATE MARKETS | **36** |
| CANDIDATE PROFILES | **2,955** (2,666 + 289) |
| CANDIDATE RELEASE-INDEX ROUTES | **3,275** (2,969 + 306) |
| CANDIDATE SERVED ROUTES | **3,344** (3,037 + 307) |

The lane independently reported 36 / 2,955 / 3,275. The classifier's `expected_release` check agrees on all three
(`complete_sets_equal`).

Its expected and actual index digests (`2635ea86…` vs `410e22e8…`) differ, because they are computed over differently
structured inputs. This is the same documented behaviour as San Diego, Jacksonville and West Palm Beach; the gate
compares complete sets.

### 12a — FINDING FOR THE FOUNDER: a not-yet-open hotel is inside the approved cohort

**The row.** `ECHO Suites Denver North - Thornton - Opening Early 2027` (13560 Grant St, 80241, route
wyndhamhotels.com, slug `echo-suites-denver-north-thornton-opening-early-2027`) is one of the 289 published profiles.

**Why it passed.** Its evidence is a genuine first-party brand page ("Dogs Allowed. / 2 dogs max. 75lbs or less per
pet."), so it passes every evidence gate. But the brand's own name says the hotel **is not open**. A pet traveller
could try to book a hotel that does not yet operate.

**What this order did.** The founder approved the cohort at exactly 289, and this order may not change it or weaken
or strengthen rules. So the row is **left as registered** and is not silently removed.

**Scope.** A scan of every published name and quote for opening / coming-soon / closed wording finds **only this
row**.

**Recommendation.** Rule on it **before** founder launch authorization. A FOUNDER-AUTHORIZED market cannot be
re-registered, so the correction would use the existing re-registration lane (a 288-profile candidate).

## PHASE 13 — PUBLICATION SAFETY

| | |
|---|---:|
| **APPROVED DENVER PROFILES IN CANDIDATE** | **289** (289/289 present as sitemap route and profile directory; 0 Denver profile routes outside the approved set) |
| **UNAPPROVED / HELD DENVER PROFILES IN CANDIDATE** | **0** |
| VERIFIED NO-PETS PUBLISHED AS PROFILES | **0** (46 exclusions) |
| UNRESOLVED ROWS PUBLISHED | **0** of 106 |

The release contract states *289 published / 0 held of 289 seed rows*. First-party gate: 335 / 335.

## PHASE 14 — DUAL-BRAND / ESA SAFETY

| | |
|---|---:|
| DUAL-BRAND FOUNDER-HOLD PROFILES PUBLISHED | **0** of 14 |
| ESA TITLE-COLLISION PROFILES PUBLISHED | **0** of 2 |

No display name was invented, and no same-campus rule was written.

## PHASE 15 — FEE SAFETY

| | |
|---|---:|
| TIERED FEES (withheld) | **80** |
| UNSAFE SINGLE FEES WITHHELD | **35** (basis not stated 26, stay-length condition 6, two bases 2, amount range 1) |
| SINGLE FEES PUBLISHED | **54**, each with the basis its own quote states |
| **MISLEADING SINGLE FEES PUBLISHED** | **0** (re-checked on the registered policy package: no published fee's quote states >1 amount or trips a withholding rule) |

## PHASE 16 — CANDIDATE DELTA

| | |
|---|---|
| UNEXPECTED MARKET DELTA | **`[]`** |
| UNEXPECTED PROFILE DELTA | **`[]`** |
| UNEXPECTED ROUTE DELTA | **`[]`** |

- `release_diff_passed: true`, finding count 0.
- The classifier's unexpected market / profile / route changes are 0 / 0 / 0.
- Measured delta: markets **+1**, profiles **+289**, index routes **+306**.
- All 35 live markets are preserved (rule H) and there are 0 removals (rule I).
- Collision checks against every other market's shard: seed↔seed 0, seed↔exclusion 0, exclusion↔seed 0,
  exclusion↔exclusion 0.
- Denver is the only projected new market.

## PHASE 17 — FAST RECEIPT

Read through the current reader (`fast_release_lane.eligible_receipts`), which rejects vacuous receipts.

| | |
|---|---|
| CURRENTLY ELIGIBLE receipts for `pkg-denver-co-91b2e0a2…` | **1**: `pkg-denver-co-91b2e0a2da98b284-100b89b55b6592ba.json` |
| `file_count > 0` | **1,729** ✅ |
| `html_count > 0` | **1,713** ✅ |
| `bundle != e3b0c442…` | `03159c8d28c75750171707c38886e8a8d26b1a59fad546c9659891bfa1352df5` ✅ |
| RULE J | **PASS**, output present, `output_defects: []` |
| RULE K | **PASS**, BYTE_IDENTICAL, 4 cold builds, 0 reuse hits |
| ELIGIBLE / PRODUCTION_ACTIVATION_ALLOWED | **YES / NO** |

## PHASE 18 — STAGING GATES

| Gate | Result |
|---|---|
| package identity | **PASS**: `pkg-denver-co-91b2e0a2da98b284`, reproducible YES |
| registration classification | **PASS**: COMPOSITE_FRESH_MARKET_DATA_ONLY, 15/15 checks, broad NO |
| FAST receipt eligibility | **PASS**: 1 currently eligible, non-vacuous receipt |
| FAST rules A–O | **PASS**: 15/15, 0 UNKNOWN, 0 FAILED |
| parent identity | **PASS**: bound to the current live parent by deployed content |
| parent routes preserved | **PASS**: rules H and I |
| market preservation | **PASS**: 35 of 35 |
| profile preservation | **PASS**: +289 and nothing else |
| route preservation | **PASS**: +306 index / +307 served and nothing else |
| candidate delta | **PASS**: 0 findings |
| participation projection | **PASS**: in memory; persisted row SOURCE_READY |
| founder-decision reconciliation | **PASS**: 16 / 16 enumerated |
| held-cohort safety | **PASS**: 0 of 106 held rows published |
| dual-brand / ESA safety | **PASS**: 0 / 0 |
| fee safety | **PASS**: 0 misleading single fees |
| collision safety | **PASS**: 0 in all four directions |
| first-party binding | **PASS**: 335 evaluated, 0 ineligible |
| release contracts | **PASS**: all 37 verify |
| global authority | **PASS**: `--check` clean |
| **deployment eligibility refusal** | **PASS (EXPECTED)** |

**Deployment refusal, proved.**

- 0 of 39 deployment authorizations name denver-co.
- 0 of 38 deployment records name denver-co.
- The participation row is `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH`.
- Denver is not among the 35 `FOUNDER_AUTHORIZED_FOR_LAUNCH` markets.

**20 of 20 gates PASS.**

## PHASE 19 — LIVE SAFETY (re-verified at 21:28:53Z)

The resolver at the end reports: deploy `6ab859787d349f8397e1450a`, 35 markets, 2,666 profiles, 3,037 routes, host
verified. The live sitemap was re-fetched and its sha256 is **`4f648fff…`**, byte-identical.

| Route | Expected | Actual |
|---|---|---|
| `/pet-friendly-hotels/denver-co/` | 404 | **404** ✅ |
| `/pet-friendly-hotels/san-diego-ca/` | 200 | **200** ✅ |
| `/pet-friendly-hotels/jacksonville-fl/` | 200 | **200** ✅ |
| `/pet-friendly-hotels/west-palm-beach-fl/` | 200 | **200** ✅ |
| `/pet-friendly-hotels/fort-lauderdale-fl/` | 200 | **200** ✅ |
| `/pet-friendly-hotels/augusta-ga/` | 200 | **200** ✅ |
| `/pet-friendly-hotels/detroit-ann-arbor-mi/` | 404 | **404** ✅ |

There was no Netlify invocation, no deployment record, no founder or deployment authorization and no LIVE flag.

---

## FINAL ANSWERS

```
 1. CURRENT LIVE DEPLOYMENT              = 6ab859787d349f8397e1450a (san-diego-ca), source f01587ba,
                                           bundle 553a858f..., sitemap 4f648fff..., rollback
                                           6ab6c8798bd9daf5038ae3e5, HOST VERIFIED true
 2. CURRENT LIVE MARKETS                 = 35
 3. CURRENT LIVE PROFILES                = 2,666
 4. CURRENT LIVE RELEASE-INDEX ROUTES    = 2,969
 5. CURRENT LIVE SERVED ROUTES           = 3,037
 6. DENVER PACKAGE                       = pkg-denver-co-91b2e0a2da98b284 (registered; source package
                                           pkg-denver-co-8de3a042157dc335 verified unchanged)
 7. PACKAGE DIGEST                       = sha256:91b2e0a2da98b28425ee6b8058c2cd23fe2be9bf7738a9677e7c923b5269da2a
                                           (bundle 03159c8d... -- identical to the source package's)
 8. FOUNDER COVERAGE DECISION            = APPROVED -- COVERAGE READY YES by founder decision, recorded in
                                           denver_co_founder_coverage_decision_002.json (not signed)
 9. FOUNDER-DECISION ROWS EXPECTED       = 16
10. FOUNDER-DECISION ROWS ENUMERATED     = 16 (7 dual-brand buildings x 2 rows + 2 ESA title rows)
11. REGISTRATION CLASS                   = COMPOSITE_FRESH_MARKET_DATA_ONLY
12. ELIGIBLE                             = YES
13. FULL_REGRESSION_REQUIRED             = NO
14. TOTAL REGISTRATION WALL CLOCK        = ~17m30s (21:10:29Z -> AUTHORIZATION_READY ~21:28:08Z),
                                           incl. 63 s human permission wait
15. GENERIC REGISTRATION-LANE TIME       = ~7m16s (register ~6s + seal 361s + packet 69s);
                                           ~8m27s counting the refused first packet (71s)
16. <=5M TARGET                          = FAIL (FAST J/K on a 1,729-file bundle took 316 s)
17. <=10M HARD                           = PASS
18. BROAD REGRESSION RUNS                = 0 (remote broad jobs 0)
19. SHARED FACTORY PATHS                 = 0
20. UNKNOWN PATHS                        = 0
21. PARENT LOOKUP                        = PASS
22. PARENT ROUTES PRESERVED              = PASS
23. UNCHANGED BUNDLES REUSED             = 35
24. UNCHANGED MARKETS REBUILT            = 0
25. DENVER BUNDLES BUILT                 = 1
26. DENVER PROJECTED PROFILES            = 289
27. DENVER RELEASE-INDEX ROUTES          = 306 (289 hotel + 16 corridor + 1 hub)
28. DENVER SERVED ROUTES                 = 307 (306 + the policy-comparison page)
29. CANDIDATE MARKETS                    = 36
30. CANDIDATE PROFILES                   = 2,955
31. CANDIDATE RELEASE-INDEX ROUTES       = 3,275
32. CANDIDATE SERVED ROUTES              = 3,344
33. APPROVED DENVER PROFILES             = 289
34. UNAPPROVED DENVER PROFILES           = 0
35. ROUTER-EXHAUSTED HOLDS PUBLISHED     = 0 (of 38)
36. PLACES-GATED HOLDS PUBLISHED         = 0 (of 52)
37. FOUNDER-DECISION HOLDS PUBLISHED     = 0 (of 16)
38. DUAL-BRAND HOLDS PUBLISHED           = 0 (of 14; identity_resolutions.json unchanged)
39. ESA TITLE-COLLISION HOLDS PUBLISHED  = 0 (of 2; no display name invented)
40. MISLEADING SINGLE FEES PUBLISHED     = 0 (80 tiered + 35 unsafe withheld; 54 basis-stated fees publish)
41. FAST RECEIPT CURRENTLY ELIGIBLE      = YES (exactly 1; file_count 1,729, html_count 1,713,
                                           bundle != e3b0c442...)
42. RULE J NONEMPTY                      = PASS
43. RULE K NONVACUOUS                    = PASS (BYTE_IDENTICAL, 4 cold builds, 0 reuse hits)
44. ALL STAGING GATES                    = PASS (20 of 20)
45. DEPLOYMENT REFUSAL                   = PASS (EXPECTED) -- 0 authorizations, 0 records,
                                           PRODUCTION_ACTIVATION_ALLOWED = NO
46. CURRENT LIVE MODIFIED                = NO (sitemap re-fetched at 21:28:53Z, 4f648fff..., 3,037 routes)
47. DEPLOYMENT PERFORMED                 = NO
48. DENVER LIVE                          = NO (hub 404)
49. origin == HEAD                       = YES (verified after the final push)
50. tree clean                           = YES (verified after the final push)
51. READY FOR FOUNDER LAUNCH AUTHORIZATION = YES -- with one finding to rule on first (12a: the
                                           "Opening Early 2027" ECHO Suites row)
```

## WHAT THE FOUNDER IS NOW BEING ASKED TO DECIDE

Denver is registered, classified, staged and refused for deployment exactly as it should be. The next order is a
founder launch authorization of the approved cohort. Open items:

1. **ECHO Suites Denver North – Thornton, "Opening Early 2027"** (§12a) is inside the 289. Decide before
   authorization whether to launch at 289, or to correct it to 288 through the re-registration lane first.
2. **Seven dual-brand buildings (14 rows).** Reviewed `same_campus_distinct_entity` rows in the shared
   `identity_resolutions.json` would release them. They need a founder signature, and this order would not self-sign
   one.
3. **Two ESA Tech Center South rows.** A founder naming decision for display names that fit the site's 60-character
   title.
4. **52 no-website rows.** They are routable only through Places website discovery; its free monthly allowance renews
   2026-10-01. No spend was made or assumed.

```
DENVER REGISTRATION = PASS
DENVER STAGING = PASS
FOUNDER COVERAGE DECISION = APPROVED
FOUNDER-DECISION ROWS = 16/16 RECONCILED
FULL_REGRESSION_REQUIRED = NO
BROAD REGRESSION RUNS = 0
UNCHANGED MARKETS REBUILT = 0
CURRENT LIVE MODIFIED = NO
DENVER DEPLOYED = NO
READY FOR FOUNDER LAUNCH AUTHORIZATION = YES
```
