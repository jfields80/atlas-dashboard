# PTF-PHOENIX-AZ-REGISTRATION-AND-STAGING-002 — FINAL

`phoenix-az` (Phoenix / Scottsdale / Valley of the Sun, Arizona) is **REGISTERED** and **AUTHORIZATION_READY**, with a
validated **PROJECTED, NON-DEPLOYABLE** candidate.

- Branch: `worker/ptf-phoenix-az-market-001`
- Registration transaction: `7fbfb43d`; classification and unsigned readiness packet: `0336460f`
- Source-ready commit: `2c26ee7c`

Boundaries kept:

- no founder launch authorization, no deployment authorization, no Netlify, nothing deployed
- current live untouched
- no broad regression, no spend, no Places
- `identity_resolutions.json` untouched; no replacement identity, route or domain invented; no preopening hotel
  published

**One finding for the founder before authorization** (§12a): four Wyndham vacation-ownership resorts are inside the
63 verified-no-pets exclusions. None of them is a published profile.

---

## PHASE 1 — CURRENT LIVE

Resolved with host verification by `release_index live-source --verify-host` (3.7 s). The resolver reports `origin/main`
as stale, so it was not used.

| | |
|---|---|
| CURRENT LIVE SOURCE COMMIT | `edf11b7a413903183cc59f4204de6066e93b52cf` (built_from `5bc62502`) |
| CURRENT LIVE DEPLOYMENT | `6aba7587ddcc33a192bdf694` (denver-co), rollback `6ab859787d349f8397e1450a` |
| CURRENT LIVE BUNDLE | `7d3471c79e2d20d01c69e6dbd134bd3a5caec35e35967958f797decd06ee338a` |
| CURRENT LIVE SITEMAP | `5d3d07a4c96563c0147cdca2ad0061ea437fee9748bc5cd3169eefe083712a2c` |
| CURRENT LIVE MARKETS | **36** |
| CURRENT LIVE PROFILES | **2,954** |
| CURRENT LIVE RELEASE-INDEX ROUTES | **3,274** (the deployment record's own live verification) |
| CURRENT LIVE SERVED ROUTES | **3,343** |
| HOST VERIFIED | **true** |

## PHASE 2 — SEALED PHOENIX PACKAGE (nothing rebuilt)

Re-read from the committed shadow report, receipt and reproduction record. No census, acquisition, browser or
competitor work was re-run.

| | |
|---|---|
| PACKAGE | `pkg-phoenix-az-865822f4d2fe2640` ✅ |
| PACKAGE DIGEST | `sha256:865822f4d2fe2640fc517f489effaa2ec2d900a0814ce492127c232b41bbe167` ✅ |
| SOURCE READY | YES ✅ |
| FOUNDER COVERAGE DECISION | APPROVED (Phase 3) ✅ |
| ACTIONABLE UNRESOLVED | **0** ✅ |
| CENSUS / PF / NP / RESOLVED / UNRESOLVED | **488 / 256 / 63 / 319 / 169** ✅ |
| FAST | 15/15 PASS ✅ |
| RULE J | `file_count` **1,553**, `html_count` 1,537, output present, non-empty **YES** ✅ |
| RULE K | **BYTE_IDENTICAL**, 4 cold builds, 0 reuse (non-vacuous) ✅ |
| PACKAGE REPRODUCIBLE | YES (independent detached-worktree reproduction, DIFFERING FILES 0) ✅ |

## PHASE 3 — FOUNDER COVERAGE DECISION, RECORDED

Recorded in `markets/reports/phoenix_az_founder_coverage_decision_002.json`, with the same mechanism and shape as
Denver's and San Diego's `…_founder_coverage_decision_002.json`.

- **Decision:** COVERAGE_READY = YES, basis FOUNDER DECISION.
- **Approved cohort:** 256 pet-friendly profiles, with 63 verified-no-pets exclusions.
- **Held (169):** 48 Places-gated / no-route, 30 founder-decision, 3 preopening and 88 router-exhausted / evidence /
  source-silent rows.
- **The 30 founder-decision rows are enumerated from the committed actionability report**, not typed:
  - 14 dual-brand buildings × 2 rows = 28: 1100 S Price Rd (phxcf/phxff), 132 S Central Ave (phxxt/phxtw), 13430 N
    163rd Dr (phxzf/phxzt), 1550 N Verrado Way (phxyf/phxyt), 18513 N Scottsdale Rd (Hyatt phxxn/phxzs), 1929 E Rio
    Salado Pkwy (phxfe/phxpe), 25100 N 22nd Ln (phxhc/phxhe), 2735 W Sweetwater Ave (Choice az394 / Wyndham 33872),
    3150 N Central Ave (phxmmht/phxmtru), 5057 S Power Rd (phxhbhw/phxghpo), 6000 E Camelback Rd (phxpc/phxlc), 7290
    S Price Rd (phxptgi/phxrpht), 8401 N Pima Center Pkwy (phxdaht/phxscru), 9425 N Black Canyon Hwy (phxss/phxts).
  - 2 route-domain rows. **Tempe Mission Palms** is exactly the order's "redirect-domain" case: its recorded website
    missionpalms.com now redirects to its Destination by Hyatt page. **Best Western Plus Scottsdale Thunderbird
    Suites** is the same class of routing ruling without a redirect: the census binds bestwestern.com while a read was
    also taken on the hotel's own domain, and bestwestern.com's statement ("Pets may be accepted") is conditional
    anyway. Both stay held; no replacement route or domain is written.
- **What it does not do:** authorize Places spend, weaken any evidence rule, declare any held row resolved, publish
  any held row, write `identity_resolutions.json`, invent a route or domain, or publish a preopening hotel.
- **Attribution:** it transcribes the work order's decision and **signs no reviewer name**.

## PHASE 4 — CANONICAL FRESH-MARKET REGISTRATION

In dependency order:

1. **Repoint, not copy.** 14 Phoenix modules were repointed from the shadow zone to the registered zone (path
   constants only; the same change Denver made):
   - census → `identity_census/`
   - market document → `markets/phoenix-az.json`
   - policy package, proposed authority and final partition → the package root
2. **Promotion.**
   - The census and market document moved byte-for-byte (`git mv`, R100).
   - The policy package, proposed authority (`phoenix_az_proposed_authority_001.json`, the role name the classifier
     recognises) and final partition were regenerated by their own writers at the new targets.
   - **All five are byte-identical to the sealed originals.** Re-running the geography writer produced no diff to
     the market document (its report records the new path, nothing else).
   - Before registering, every `phoenix_az_*.py` was checked for imports outside the registration allow-list (the
     trap that refused Denver's first packet): none. The clean authority states the 60-character title limit
     itself.
3. **Authority shard** (`market_registration_cli --write`): 256 seed rows and 63 exclusions; routing and affiliate
   shards empty. **All four shard files are byte-identical to the shard the shadow package sealed.**
4. **Global regeneration** (`build_global_authority --write`, an ordinary deterministic registration write this order
   authorizes):

   | artifact | before | after | delta |
   |---|---:|---:|---|
   | `hotel_exclusions.json` | 1,327 | **1,390** | +63, all phoenix-az, 0 removed |
   | `seed_businesses.csv` | 3,103 | **3,359** | +256, all phoenix-az, 0 removed |
   | `ptf_global_authority_manifest.json` | | | +1 market entry, counts and build marker |

   - 38 markets sharded; build marker `sha256:2347ecef…`.
   - `--check`: *all generated artifacts match the shards*.
5. **Release contract** `deploy/netlify/release_contracts/phoenix-az.json` (writer
   `phoenix_az_release_contract_002.py`).
   - Fully derived, **0 disagreements**.
   - The prose was rewritten from Phoenix's own geography; the Denver clone described the Front Range. Residual
     parent place names: **0**, except one factual "Denver-live hardened lineage".
   - `release_contracts.verify_all()`: **all 38** contracts verify, **0** disagreements.
6. **`register`** (5.9 s). Participation reissued, 37 → 38 rows: one added, 0 removed, **0 existing rows changed**,
   founder-authorized set unchanged. The prior decision (Denver's founder authorization) is kept as `supersedes` with
   its sha256 and in `lineage`. The build closure gained exactly the two declared paths.
7. **`seal --work C:/t/phx2a --work-order …`** (363.5 s).
   - Registered package `pkg-phoenix-az-85ad9b6604d20b11`
     (`sha256:85ad9b6604d20b11eea56f06903210adef6eea14554296e6df03f207da8b1cc4`), FAST 15/15.
   - Market-state pin written: census 488 / pet-friendly 256 / verified-no-pets 63 / corridor routes 18;
     `reviewed_by` / `last_moved_by` = this work order.
8. **Commit** `7fbfb43d`, then **`packet --prepared-by PTF-PHOENIX-AZ-REGISTRATION-AND-STAGING-002`** (98.7 s),
   AUTOMATIC classification: **AUTHORIZATION_READY on the first packet.** Committed as `0336460f`.

**Classifier result.**

| | |
|---|---|
| CLASS | **`COMPOSITE_FRESH_MARKET_DATA_ONLY`** (classification_source AUTOMATIC) |
| ELIGIBLE | **YES**: 15/15 checks PASS (change_set, market_local_zone, discovery_config, registration_input, identity_resolutions, participation, release_contract, build_closure, derived_globals, sealed_package, fast_receipt, expected_release, identity_routes, market_state_pin, release_integrity) |
| FULL_REGRESSION_REQUIRED | **NO** |
| REMOTE BROAD JOBS | **0** |
| BROAD REGRESSION RUNS | **0** |

**Same bundle as the shadow package.** The registered package builds the identical bundle
`ea2a8d31aadf5dcb5a20aa4872e5f761596fc5fe348f409c23c72952fcfa8d69` that the source-ready shadow package built.
Registration moved the market without changing it.

## PHASE 5 — TIMER

| | |
|---|---|
| **TOTAL PROMOTION / REGISTRATION WALL CLOCK** | **≈ 14 m 00 s**, from the first action at 13:03:32Z to AUTHORIZATION_READY at ≈ 13:17:32Z; ≈ 16 m 30 s to the final live probe (≈ 13:20Z) |
| of which human / tool permission wait | **0 s** |
| **GENERIC REGISTRATION-LANE TIME** | **≈ 7 m 48 s**: `register` 5.9 s + `seal` 363.5 s + `packet` 98.7 s |
| ≤ 5 MINUTES TARGET | **FAIL** |
| ≤ 10 MINUTES HARD LIMIT | **PASS** |

**Why the lane missed 5 minutes.** Inside the seal, the FAST lane took 303.8 s: rules J and K build Phoenix's
1,553-file bundle cold four times (K alone 151 s). The live parent read took 57.0 s, and the packet spent 97.5 s
resolving live and classifying. Candidate composition ×2 took 0.36 s.

## PHASE 6 — REGISTRATION SAFETY

| | |
|---|---|
| SHARED FACTORY IMPLEMENTATION CHANGES | **0** (classifier: 0 shared-behavior paths; no `.py` outside `phoenix_az_*` changed) |
| UNKNOWN PATHS | **0** (93 changed paths since base `630d1198`: 29 market-local, 13 registration data, 51 derived; sum equals total) |
| CROSS-MARKET SOURCE CHANGES | **0** |
| CURRENT PRODUCTION CHANGED | **NO** |
| PHOENIX LIVE | **NO** |

**Shared artifacts regenerated deterministically**, each diffed for foreign content:

- `hotel_exclusions.json`: +63, phoenix-az only
- `seed_businesses.csv`: +256, phoenix-az only
- `ptf_global_authority_manifest.json`: one market entry
- `launch_participation.json`: reissued, +1 row
- `bundle_cache_closure.json`: +2 paths
- `tests/pettripfinder/pins/market_state.json`: Phoenix's block

## PHASE 7 — HELD-COHORT SAFETY

Checked against the candidate the seal actually built (`C:/t/phx2a/oa/site`). No held row's name is among the 256
seed rows, and no held row's slug (with or without "and") is a profile directory or a sitemap route.

| held class | rows | published |
|---|---:|---:|
| Places-gated / no route | 48 | **0** |
| dual-brand / shared-campus | 28 | **0** |
| redirect / route-domain founder rows | 2 | **0** |
| preopening | 3 | **0** |
| router-exhausted / evidence / source-silent | 88 | **0** |
| **HELD ROWS PROMOTED TO PROFILE** | 169 | **0** |

The 63 verified-no-pets rows are exclusions, and none is a profile. `identity_resolutions.json` is **unchanged**.

## PHASE 8 — PREOPENING SAFETY

| hotel | slug | profile / route / seed row |
|---|---|---|
| Home2 Suites by Hilton Peoria North Phoenix | `home2-suites-by-hilton-peoria-north-phoenix` | none |
| ECHO Suites Phoenix-Chandler - Opening Late 2026 | `echo-suites-phoenix-chandler-opening-late-2026` | none |
| Vai Resort (coming soon) | `vai-resort-coming-soon` | none |

**PREOPENING PROFILES PUBLISHED = 0.** A scan of all 256 published names and routes for opening / coming-soon / closed
wording finds nothing.

## PHASE 9 — PROJECTED PARTICIPATION

The projection exists in memory only.

- The persisted row is `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH`.
- The lane reports `nothing_deployed: true`, `nothing_activated: true` and `participation_untouched: true`.
- The receipt carries `PRODUCTION_ACTIVATION_ALLOWED = NO`.
- Readiness status is **AUTHORIZATION_READY**; founder status is **AWAITING_FOUNDER_AUTHORIZATION**.

The candidate is **PROJECTED / NON-DEPLOYABLE**.

## PHASE 10 — PARENT LOOKUP

| | |
|---|---|
| PARENT LOOKUP | **PASS**: live_deploy_id `6aba7587ddcc33a192bdf694`, rollback `6ab859787d349f8397e1450a`, source `5bc62502`, live index `sha256:280d8993…`. FAST rule N and the classifier's `sealed_package` check bind the package to the current live parent by deployed content |
| PARENT ROUTES PRESERVED | **PASS**: rule H (every unrelated live market preserved) and rule I (every removal intended; 0 removals); all 36 parent profile counts carried unchanged |

## PHASE 11 — STAGING, AND WHAT WAS REUSED

| | |
|---|---|
| **UNCHANGED BUNDLES REUSED** | **36** = the current live market count (`unchanged_markets` 36) |
| **UNCHANGED MARKETS REBUILT** | **0** |
| **PHOENIX BUNDLES BUILT** | **1** |

**Stated precisely.** The candidate **index** was composed twice (0.36 s) from the 36 unchanged markets' committed index
entries, and both compositions agree (`candidate_index_digest == recomposed_index_digest` `sha256:a6067d25…`,
CANDIDATE_REPRODUCIBLE YES). No whole-site assembly ran, so no other market was physically re-rendered. The only
physical build was Phoenix's own bundle (256 owned inventory rows, 4 cold builds inside FAST).

## PHASE 12 — PROJECTED ACCOUNTING

**Release index**, from the declared routes in the sealed package's intended delta and from the lane's candidate:

| | |
|---:|---:|
| PHOENIX PROJECTED PROFILES | **256** |
| PHOENIX HUB ROUTES | **1** |
| PHOENIX CORRIDOR ROUTES | **18** (of 26 corridors) |
| **PHOENIX RELEASE-INDEX ROUTES** | **275** = 256 + 18 + 1 |

**Served sitemap**, counted from the sitemap the seal built (`C:/t/phx2a/oa/site/sitemap.xml`): 281 `<loc>`.

- **276** are Phoenix-owned: 256 hotels, 18 corridors, 1 hub and 1 policy-comparison page.
- 5 are pre-existing global pages (`/`, `/about/`, `/contact/`, `/methodology/`, `/pet-friendly-hotels/`).
- The declared routes equal the sitemap's Phoenix routes minus the comparison page.

| | |
|---|---:|
| **PHOENIX SERVED ROUTES** | **276** |
| CANDIDATE MARKETS | **37** |
| CANDIDATE PROFILES | **3,210** (2,954 + 256) |
| CANDIDATE RELEASE-INDEX ROUTES | **3,549** (3,274 + 275) |
| CANDIDATE SERVED ROUTES | **3,619** (3,343 + 276) |

The lane independently reported 37 / 3,210 / 3,549. The classifier's `expected_release` check agrees on all three
(`complete_sets_equal`, 0 unexpected market, profile or route changes). Its expected and actual index digests
(`a6067d25…` vs `da2b2fd3…`) differ because they are computed over differently structured inputs; this is the same
documented behaviour as every earlier registration, and the gate compares complete sets.

### 12a — FINDING FOR THE FOUNDER: four vacation-ownership resorts are inside the 63 verified-no-pets exclusions

**The rows.** Club Wyndham Legacy Golf Resort (6808 S 32nd St), Club Wyndham Orange Tree Resort (10601 N 56th St),
WorldMark Phoenix – South Mountain Preserve (4647 E Francisco Dr) and WorldMark Scottsdale (8235 E Indian Bend Rd).
Each is routed to `wyndhamhotels.com/wyndham-vacations/…`, and each page states "Sorry, (no) other pets are not
allowed", so each is a VERIFIED_NO_PETS exclusion.

**Why it matters.** The source-ready order's own rule is that timeshare and vacation ownership are never admitted.
Its excluded-by-code list covered Marriott, Hilton, IHG and Choice vacation clubs but not the Wyndham Vacations family
(Club Wyndham / WorldMark), so these four were admitted. **None of them is a published profile**. They sit in the
exclusion set, which records that the property refuses pets, and they count in the census (488) and the no-pets
total (63).

**What this order did.** The founder approved the cohort at exactly 256 PF / 63 NP, and this order may not change it.
The rows are **left as registered** and are not silently removed.

**Recommendation.** Rule on it **before** founder launch authorization. Either accept the four as correct no-pets
exclusions (their pages do refuse pets), or correct them to excluded-as-timeshare through the existing
re-registration lane (a 484 / 256 / 59 candidate). A founder-authorized market cannot be re-registered.

## PHASE 13 — PUBLICATION SAFETY

| | |
|---|---:|
| **APPROVED PHOENIX PROFILES IN CANDIDATE** | **256** (256/256 present as sitemap route and profile directory; the seed rows equal the approved rows) |
| **UNAPPROVED / HELD PHOENIX PROFILES IN CANDIDATE** | **0** |
| VERIFIED NO-PETS PUBLISHED AS PROFILES | **0** (63 exclusions) |
| UNRESOLVED ROWS PUBLISHED | **0** of 169 |

First-party gate: 319 / 319.

## PHASE 14 — FEE SAFETY

Re-checked on the registered policy package at the package root:

| | |
|---|---:|
| SINGLE-BASIS FEES PUBLISHED | **49**, each one amount with the basis its own quote states |
| TIERED FEES WITHHELD | **77** |
| UNSAFE / MISSING-BASIS SINGLE FEES WITHHELD | **35** (basis not stated 30, stay-length condition 5) |
| **MISLEADING SINGLE FEES PUBLISHED** | **0** |

## PHASE 15 — CROSS-MARKET SAFETY

| | |
|---|---:|
| CROSS-MARKET IDENTITY COLLISIONS | **0**: Phoenix's shard against every other market's shard by normalized name: seed↔seed 0, seed↔exclusion 0, exclusion↔seed 0, exclusion↔exclusion 0 |
| BARE-CHAIN COLLISIONS | **0**: the 8 bare-chain / live-name collision rows the census found stay non-admitted, and no published name is a bare chain name |
| DUPLICATE EXCLUDED IDENTITIES | **0** (0 duplicate exclusion ids in the global file) |

Phoenix's routes are market-scoped (`/pet-friendly-hotels/phoenix-az/<slug>/`), so no live route can be displaced;
rule H preserves every live market.

## PHASE 16 — CANDIDATE DELTA

| | |
|---|---|
| UNEXPECTED MARKET DELTA | **`[]`** |
| UNEXPECTED PROFILE DELTA | **`[]`** |
| UNEXPECTED ROUTE DELTA | **`[]`** |

- `release_diff_passed: true`, 0 findings.
- Measured delta: markets **+1**, profiles **+256**, index routes **+275**.
- All 36 live markets are preserved (rule H) and there are 0 removals (rule I).
- Phoenix is the only projected new market.

## PHASE 17 — FAST RECEIPT

Read through the current reader (`fast_release_lane.eligible_receipts`), which rejects vacuous receipts.

| | |
|---|---|
| CURRENTLY ELIGIBLE receipts for `pkg-phoenix-az-85ad9b66…` | **1**: `pkg-phoenix-az-85ad9b6604d20b11-7e72516a1d6824f6.json` |
| `file_count > 0` | **1,553** ✅ |
| `html_count > 0` | **1,537** ✅ |
| `bundle != e3b0c442…` | `ea2a8d31aadf5dcb5a20aa4872e5f761596fc5fe348f409c23c72952fcfa8d69` ✅ |
| RULE J | **PASS**, output present, `output_defects: []` |
| RULE K | **PASS**, BYTE_IDENTICAL, 4 cold builds, 0 reuse hits |
| ELIGIBLE / PRODUCTION_ACTIVATION_ALLOWED | **YES / NO** |

## PHASE 18 — STAGING GATES

| Gate | Result |
|---|---|
| package identity | **PASS**: `pkg-phoenix-az-85ad9b6604d20b11`, reproducible YES, same bundle as the shadow package |
| registration classification | **PASS**: COMPOSITE_FRESH_MARKET_DATA_ONLY, 15/15 checks, broad NO |
| FAST receipt eligibility | **PASS**: 1 currently eligible, non-vacuous receipt |
| FAST rules A–O | **PASS**: 15/15, 0 UNKNOWN, 0 FAILED |
| parent identity | **PASS**: bound to the current live parent by deployed content |
| parent routes preserved | **PASS**: rules H and I |
| market preservation | **PASS**: 36 of 36 |
| profile preservation | **PASS**: +256 and nothing else |
| route preservation | **PASS**: +275 index / +276 served and nothing else |
| candidate delta | **PASS**: 0 findings |
| participation projection | **PASS**: in memory; persisted row SOURCE_READY |
| founder-decision reconciliation | **PASS**: 30 / 30 enumerated |
| held-cohort safety | **PASS**: 0 of 169 held rows published |
| preopening safety | **PASS**: 0 of 3 |
| fee safety | **PASS**: 0 misleading single fees |
| collision safety | **PASS**: 0 in all four directions |
| first-party binding | **PASS**: 319 evaluated, 0 ineligible |
| release contracts | **PASS**: all 38 verify |
| global authority | **PASS**: `--check` clean |
| **deployment eligibility refusal** | **PASS (EXPECTED)** |

**Deployment refusal, proved.**

- 0 of 40 deployment authorizations name phoenix-az.
- 0 of 39 deployment records name phoenix-az.
- The participation row is `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH`.
- Phoenix is not among the 36 `FOUNDER_AUTHORIZED_FOR_LAUNCH` markets.

**20 of 20 gates PASS.**

## PHASE 19 — LIVE SAFETY (re-verified at ≈ 13:20Z)

The resolver at the end reports: deploy `6aba7587ddcc33a192bdf694`, 36 markets, 2,954 profiles, 3,343 routes, host
verified. The live sitemap was re-fetched: sha256 **`5d3d07a4…`** (byte-identical), 3,343 `<loc>`, 0 Phoenix routes.

| Route | Expected | Actual |
|---|---|---|
| `/pet-friendly-hotels/phoenix-az/` | 404 | **404** ✅ |
| `/pet-friendly-hotels/denver-co/` | 200 | **200** ✅ |
| `/pet-friendly-hotels/san-diego-ca/` | 200 | **200** ✅ |
| `/pet-friendly-hotels/jacksonville-fl/` | 200 | **200** ✅ |
| `/pet-friendly-hotels/west-palm-beach-fl/` | 200 | **200** ✅ |
| `/pet-friendly-hotels/fort-lauderdale-fl/` | 200 | **200** ✅ |
| `/pet-friendly-hotels/augusta-ga/` | 200 | **200** ✅ |
| `/pet-friendly-hotels/detroit-ann-arbor-mi/` | 404 | **404** ✅ |

There was no Netlify invocation, no deployment record, no founder or deployment authorization and no LIVE flag. The
seal's scratch work dir `C:/t/phx2a` was removed after the verification.

---

## FINAL ANSWERS

```
 1. CURRENT LIVE DEPLOYMENT              = 6aba7587ddcc33a192bdf694 (denver-co), source edf11b7a,
                                           bundle 7d3471c7..., sitemap 5d3d07a4..., rollback
                                           6ab859787d349f8397e1450a, HOST VERIFIED true
 2. CURRENT LIVE MARKETS                 = 36
 3. CURRENT LIVE PROFILES                = 2,954
 4. CURRENT LIVE RELEASE-INDEX ROUTES    = 3,274
 5. CURRENT LIVE SERVED ROUTES           = 3,343
 6. PHOENIX PACKAGE                      = pkg-phoenix-az-85ad9b6604d20b11 (registered; source package
                                           pkg-phoenix-az-865822f4d2fe2640 verified unchanged)
 7. PACKAGE DIGEST                       = sha256:85ad9b6604d20b11eea56f06903210adef6eea14554296e6df03f207da8b1cc4
                                           (bundle ea2a8d31... -- identical to the source package's; source
                                           package digest sha256:865822f4...)
 8. FOUNDER COVERAGE DECISION            = APPROVED -- COVERAGE READY YES by founder decision, recorded in
                                           phoenix_az_founder_coverage_decision_002.json (not signed)
 9. REGISTRATION CLASS                   = COMPOSITE_FRESH_MARKET_DATA_ONLY
10. ELIGIBLE                             = YES (15/15 checks)
11. FULL_REGRESSION_REQUIRED             = NO
12. TOTAL REGISTRATION WALL CLOCK        = ~14m00s (13:03:32Z -> AUTHORIZATION_READY ~13:17:32Z);
                                           0 s human / tool permission wait
13. GENERIC REGISTRATION-LANE TIME       = ~7m48s (register 5.9s + seal 363.5s + packet 98.7s)
14. <=5M TARGET                          = FAIL (FAST J/K on a 1,553-file bundle took 303.8 s)
15. <=10M HARD                           = PASS
16. BROAD REGRESSION RUNS                = 0 (remote broad jobs 0)
17. SHARED FACTORY PATHS                 = 0
18. UNKNOWN PATHS                        = 0
19. PARENT LOOKUP                        = PASS
20. PARENT ROUTES PRESERVED              = PASS
21. UNCHANGED BUNDLES REUSED             = 36
22. UNCHANGED MARKETS REBUILT            = 0
23. PHOENIX BUNDLES BUILT                = 1
24. PHOENIX PROJECTED PROFILES           = 256
25. PHOENIX RELEASE-INDEX ROUTES         = 275 (256 hotel + 18 corridor + 1 hub)
26. PHOENIX SERVED ROUTES                = 276 (275 + the policy-comparison page)
27. CANDIDATE MARKETS                    = 37
28. CANDIDATE PROFILES                   = 3,210
29. CANDIDATE RELEASE-INDEX ROUTES       = 3,549
30. CANDIDATE SERVED ROUTES              = 3,619
31. APPROVED PHOENIX PROFILES            = 256
32. UNAPPROVED PHOENIX PROFILES          = 0
33. PLACES-GATED HOLDS PUBLISHED         = 0 (of 48)
34. DUAL-BRAND HOLDS PUBLISHED           = 0 (of 28 rows / 14 buildings; identity_resolutions.json unchanged)
35. REDIRECT-DOMAIN HOLDS PUBLISHED      = 0 (of 2; no route or domain invented)
36. PREOPENING PROFILES PUBLISHED        = 0 (of 3)
37. MISLEADING SINGLE FEES PUBLISHED     = 0 (77 tiered + 35 unsafe withheld; 49 basis-stated fees publish)
38. FAST RECEIPT CURRENTLY ELIGIBLE      = YES (exactly 1; file_count 1,553, html_count 1,537,
                                           bundle != e3b0c442...)
39. RULE J NONEMPTY                      = PASS
40. RULE K NONVACUOUS                    = PASS (BYTE_IDENTICAL, 4 cold builds, 0 reuse hits)
41. ALL STAGING GATES                    = PASS (20 of 20)
42. DEPLOYMENT REFUSAL                   = PASS (EXPECTED) -- 0 authorizations, 0 records,
                                           PRODUCTION_ACTIVATION_ALLOWED = NO
43. CURRENT LIVE MODIFIED                = NO (sitemap re-fetched, 5d3d07a4..., 3,343 routes)
44. DEPLOYMENT PERFORMED                 = NO
45. PHOENIX LIVE                         = NO (hub 404)
46. origin == HEAD                       = YES (verified after the final push)
47. tree clean                           = YES (verified after the final push)
48. READY FOR FOUNDER LAUNCH AUTHORIZATION = YES -- with one finding to rule on first (12a: four Wyndham
                                           vacation-ownership resorts among the 63 no-pets exclusions)
```

## WHAT THE FOUNDER IS NOW BEING ASKED TO DECIDE

Phoenix is registered, classified, staged and refused for deployment exactly as it should be. The next order is a
founder launch authorization of the approved cohort. Open items:

1. **Four Wyndham vacation-ownership resorts** (§12a) are among the 63 no-pets exclusions, though no profile publishes
   for them. Decide before authorization whether to launch as registered (256 / 63), or to correct them to
   excluded-as-timeshare through the re-registration lane first (256 / 59).
2. **Fourteen dual-brand buildings (28 rows).** Reviewed `same_campus_distinct_entity` rows in the shared
   `identity_resolutions.json` would release them. They need a founder signature, and this order would not self-sign
   one.
3. **Two route-domain rows** (Tempe Mission Palms, Best Western Plus Scottsdale Thunderbird Suites): a routing ruling.
4. **48 no-route rows.** They are routable only through Places website discovery; its free monthly allowance renews
   2026-10-01. No spend was made or assumed.
5. **Carried from the source-ready order:** Charlotte and Tampa publish nightly fees as per-stay in live production
   (source-ready FINAL §12). This needs its own correction order.

```
PHOENIX REGISTRATION = PASS
PHOENIX STAGING = PASS
FOUNDER COVERAGE DECISION = APPROVED
FULL_REGRESSION_REQUIRED = NO
BROAD REGRESSION RUNS = 0
UNCHANGED MARKETS REBUILT = 0
CURRENT LIVE MODIFIED = NO
PHOENIX DEPLOYED = NO
READY FOR FOUNDER LAUNCH AUTHORIZATION = YES
```
