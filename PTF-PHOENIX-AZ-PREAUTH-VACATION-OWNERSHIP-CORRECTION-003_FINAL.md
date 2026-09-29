# PTF-PHOENIX-AZ-PREAUTH-VACATION-OWNERSHIP-CORRECTION-003 — FINAL

The four Wyndham vacation-ownership resorts are removed from Phoenix's qualifying hotel census and moved to the
market's existing **TIMESHARE** exclusion class.

- **Not hotels, not no-pets:** they are no longer pet-friendly, verified-no-pets, profile candidates or hotel
  exclusions. Their evidence is kept.
- **New package:** `pkg-phoenix-az-07f7e75699af6a8c`, sealed, independently reproduced and re-registered.
- **Candidate:** a new projected, non-deployable candidate, still **256** Phoenix profiles.
- **Status:** AUTHORIZATION_READY. The superseded 63-no-pets package `pkg-phoenix-az-85ad9b66` must **not** be
  authorized (recorded in `phoenix_az_founder_coverage_decision_003.json`), and it is kept as history.

Nothing was deployed. No founder or deployment authorization, no Netlify, no broad regression, no spend, no other
market touched, no shared factory code changed.

Branch `worker/ptf-phoenix-az-market-001`. Commits: `66860b5a` correction + re-registration, `d6fba323` readiness,
then this report.

---

## PHASE 1 — CURRENT LIVE

`release_index live-source --verify-host`. The first check ran at 16:23:03Z, after the correction data was derived but
before anything was committed or pushed (this order changes nothing that live reads). It was repeated at the end, at
16:36:42Z.

| | |
|---|---|
| CURRENT LIVE | Denver, deploy `6aba7587ddcc33a192bdf694`, source `edf11b7a` |
| MARKETS / PROFILES / RELEASE-INDEX / SERVED | **36 / 2,954 / 3,274 / 3,343** |
| LIVE SITEMAP | `5d3d07a4…`, 3,343 `<loc>`, 0 Phoenix routes |
| HOST VERIFIED | true |
| PHOENIX LIVE | **NO** (hub 404) |

## PHASE 2 — THE FOUR PROPERTIES

| canonical name | address | brand / code | disposition before | qualifying before |
|---|---|---|---|---|
| Club Wyndham Legacy Golf Resort | 6808 South 32nd St, Phoenix, AZ 85042 | WYNDHAM 51351 | CLEAN_VERIFIED_NO_PETS | YES |
| Club Wyndham Orange Tree Resort | 10601 North 56th St, Scottsdale, AZ 85254 | WYNDHAM 51349 | CLEAN_VERIFIED_NO_PETS | YES |
| WorldMark Phoenix - South Mountain Preserve | 4647 E Francisco Drive, Phoenix, AZ 85044 | WYNDHAM 52342 | CLEAN_VERIFIED_NO_PETS | YES |
| WorldMark Scottsdale | 8235 E Indian Bend Rd, Scottsdale, AZ 85250 | WYNDHAM 52344 | CLEAN_VERIFIED_NO_PETS | YES |

**Vacation-ownership evidence** (first-party, not brand-name intuition), recorded in
`markets/reports/phoenix_az_vacation_ownership_evidence_003.json` with every document's sha256:

1. **Wyndham's own property records.** For each code, Wyndham's property service (`BWSServices … propertyId=<code>`)
   and overview page place the property under the brand route **`wyndham-vacations/…`**. Each overview page carries
   Wyndham's own notice *"WYNDHAM VACATION RESORTS REQUIRE A NIGHT MINIMUM STAY"*, and South Mountain's page shows an
   owners'-lounge image. These documents were persisted by the source-ready Wyndham lane.
2. **Wyndham's own segment page** `wyndhamhotels.com/wyndham-vacations` is titled *"Wyndham Vacation Clubs"*.
3. **The clubs' own first-party sites** (free static GETs, this order):
   - `clubwyndham.wyndhamdestinations.com` is titled *"Club Wyndham Timeshare"*. It states *"As a Club Wyndham owner
     you can expect more vacations, space, and flexibility"* and links "Learn more about ownership" and "My Ownership".
   - `worldmark.wyndhamdestinations.com` is *"WorldMark The Club"*. It states *"WorldMark owners have a new digital tool
     to take their ownership to the next level"* and links "Dues & loans".

## PHASE 3 — CORRECTED CLASSIFICATION

- **Mechanism:** the four brand codes were added to `phoenix_az_nonhotel_rulings_001.TIMESHARE_CODES`. This is the
  market's **existing** vacation-ownership mechanism, and it already excludes the Marriott, IHG, Choice and Hilton
  vacation clubs by code. The census's `classify` refuses each one as **`NON_LODGING` with reason
  `TIMESHARE -- …`** (exclusion class `TIMESHARE`) before any policy applies.
- **No shared schema value was invented.** No row is classified verified-no-pets.
- **Evidence is not deleted.** Each property stays in the census graph's `non_admitted` set with its reason. Its
  first-party pet sentence and document hashes remain in the committed Wyndham raw capture and in the new evidence
  report.
- **Why the name rule did not catch them:** the rulings module's name pattern already names `worldmark` and
  `club wyndham`, but it yields to a brand-inventory or property-page read by design. The brand-code rule is the one
  that governs brand rows.

| each of the four | |
|---|---|
| QUALIFYING HOTEL | **NO** |
| PET-FRIENDLY | **NO** |
| VERIFIED NO-PETS | **NO** |
| PROFILE PUBLISHABLE | **NO** |

**Exactly four rows moved.** The committed and corrected documents were compared key by key:

- census `hotels`: −4 (the four), 0 added, 0 changed; `non_admitted` +4 (the four, as TIMESHARE), 0 removed
- clean authority and final partition: −4, 0 changed
- proposed authority: no-pets −4, pet-friendly 0 changed
- actionability: 0 rows changed
- **policy package (the 256 profiles): byte-identical**

## PHASE 4 — RECOMPUTED PHOENIX ACCOUNTING (derived)

| | before | after |
|---|---:|---:|
| QUALIFYING CENSUS | 488 | **484** |
| PET-FRIENDLY | 256 | **256** |
| VERIFIED NO-PETS | 63 | **59** |
| RESOLVED | 319 | **315** |
| UNRESOLVED | 169 | **169** |
| ACTIONABLE UNRESOLVED | 0 | **0** |

Resolution rate 65.08 %. Timeshare exclusions in the census graph went 11 → 15. Fees are unchanged: 49 published, 77
tiered and 35 unsafe withheld, 0 misleading. None of the four had a fee.

## PHASE 5 — ALL OTHER PHOENIX DECISIONS PRESERVED

The unresolved classes are unchanged: 48 Places-gated, 30 founder-decision (28 dual-brand rows in 14 buildings plus 2
redirect / route-domain rows, each enumerated exactly as in 002), 3 preopening and 88 router-exhausted / evidence /
source-silent.

`markets/reports/phoenix_az_founder_coverage_decision_003.json` is a new record; the 002 record is kept unchanged.

- **COVERAGE READY:** YES BY FOUNDER DECISION, cohort **256** pet-friendly / 59 no-pets.
- **Why it still holds:** the correction removes four non-hotels from the hotel accounting. It changes no published
  profile, opens no acquisition gap and moves no held row.
- **The superseded package:** the record states that `pkg-phoenix-az-85ad9b66` (63 no-pets) must not be authorized.
- **Attribution:** transcribed, not signed.

## PHASE 6 — RE-SEALED CORRECTED PACKAGE

- **Package:** `pkg-phoenix-az-07f7e75699af6a8c`
  (`sha256:07f7e75699af6a8cefe5f083b688f647c55190f04aae0cd0617292968ab0fccf`), sealed via
  `registration_release_lane seal --work C:/t/phx3a --work-order …` (short forward-slash path).
- **FAST:** **15/15 PASS, 0 UNKNOWN, 0 FAILED**; receipt `sha256:b3679c3f…`, ELIGIBLE YES, PRODUCTION_ACTIVATION_ALLOWED
  NO.
- **RULE J NONEMPTY:** PASS: 1,553 files / 1,537 HTML, output present, 0 defects, bundle
  `ea2a8d31aadf5dcb5a20aa4872e5f761596fc5fe348f409c23c72952fcfa8d69`. This is the same bundle as before: exclusions
  render no page, so removing four exclusions changes no page.
- **RULE K NONVACUOUS:** PASS, BYTE_IDENTICAL, 4 cold builds, 0 reuse.
- **History:** `pkg-phoenix-az-85ad9b66…` and its receipt were **not overwritten**; both remain in
  `markets/packages|receipts/phoenix-az/`.

## PHASE 7 — INDEPENDENT REPRODUCTION

Detached worktree `C:/t/phx3b-wt` at `d6fba323`, separate processes, work dir `C:/t/phx3b`. The process record
(`reproduction/independent_reproduction_process_003.txt`) was written before either process started. The worktree
and work dirs were removed afterwards.

1. **The whole data chain was re-derived in the worktree:** census reconciliation, routing, browser lane, clean
   authority, actionability, final partition, `registration_staging --write`, competitor reconciliation, accounting,
   `market_registration_cli --write`, `build_global_authority --check` and the release contract. Afterwards `git
   status` was **clean: 0 differing files.**
2. **Seal in a separate OS process** (no `--work-order`, no pin written). This gave reproduction package
   `pkg-phoenix-az-8ccb9a8e921b5e34`.
   - Of 152,104 package fields, 4 differ: `created_from_source_sha`, `sealed_at` (not digested), and the digest and
     id derived from them. The registering seal ran on `1c89cd4f`'s tree plus the uncommitted correction, because the
     canonical sequence seals and then commits. The reproduction sealed the committed `d6fba323`.
   - Recomputed under the registered provenance, **the reproduction's digest is exactly `sha256:07f7e756…` and the two
     documents are equal.**
   - The **built site is 1,553 / 1,553 files identical**, with the same bundle `ea2a8d31…`.
   - Both runs pass FAST 15/15, ELIGIBLE YES, K BYTE_IDENTICAL.

**BYTE IDENTICAL = YES** (under identical provenance). **DIFFERING FILES = 0.**

## PHASE 8 — RE-REGISTRATION OF THE CORRECTED PACKAGE

**Why the plain registration path applies.** Phoenix is REGISTERED, NOT FOUNDER-AUTHORIZED and NOT LIVE. The
repository's `reregister` lane only accepts a FOUNDER_AUTHORIZED market (it reissues from the authorizing decision), so
it was not used. For an unauthorized market, `derive_registration_base` still resolves **`630d1198`**, the newest
ancestor naming no Phoenix path. So the correction remains one first registration and goes through the canonical
fresh-market path. This is the same path Denver's preauth correction 003 took.

**The one step no lane command covers.** `seal --work-order` refuses an already-pinned market, and `register`
refuses an existing row. So `launch_participation.json`, `bundle_cache_closure.json` and
`tests/pettripfinder/pins/market_state.json` were restored to their base bytes (`630d1198`). Only Phoenix's own
registration commit `7fbfb43d` had touched them since. The **unchanged** writers then re-derived them. Nothing was
hand-edited.

The sequence:

1. census → routing → browser lane → clean authority → actionability → final partition → `registration_staging
   --write` → competitor reconciliation → accounting
2. `market_registration_cli --write`: 256 seed rows / 59 exclusions
3. `build_global_authority --write`: exclusions 1,390 → **1,386** (−4, all phoenix-az), seed 3,359 unchanged;
   `--check` clean
4. release contract: 0 disagreements; all 38 contracts verify
5. `register`: participation 38 rows, **only Phoenix's row changed** (note "484 … 59"); founder-authorized set
   unchanged; closure +2 against base
6. `seal --work-order PTF-PHOENIX-AZ-PREAUTH-VACATION-OWNERSHIP-CORRECTION-003`: pin block 484 / 256 / 59 / 18
7. commit `66860b5a`
8. `packet`

**Classifier result.**

| | |
|---|---|
| REGISTRATION CORRECTION CLASS | **COMPOSITE_FRESH_MARKET_DATA_ONLY** (automatic) |
| ELIGIBLE | **YES**: 15/15 checks PASS (100 changed paths vs `630d1198`: 29 market-local, 13 registration, 58 derived; 0 shared, 0 unknown) |
| FULL_REGRESSION_REQUIRED | **NO** |
| REMOTE BROAD JOBS / BROAD REGRESSION RUNS | **0 / 0** |
| readiness | **AUTHORIZATION_READY**, founder AWAITING_FOUNDER_AUTHORIZATION |

**Lane time:** `register` ≈ 6 s + `seal` 484 s (FAST 426.6 s) + `packet` 85 s ≈ **9 m 35 s**. That is inside the
10-minute hard limit and misses the 5-minute target. The wall clock ran ≈ 22 min from the first evidence fetch
(15:59:43Z) to AUTHORIZATION_READY (16:21:26Z), with 0 s permission wait.

## PHASE 9 — PROJECTED CANDIDATE

| | |
|---:|---:|
| UNCHANGED LIVE MARKETS REUSED / REBUILT | **36 / 0** (index composed ×2, digests agree; no whole-site assembly; no other market physically re-rendered) |
| PHOENIX BUNDLES BUILT | 1 |
| PHOENIX PROJECTED PROFILES | **256** |
| PHOENIX VERIFIED NO-PETS | **59** (exclusions, not profiles) |
| PHOENIX RELEASE-INDEX ROUTES | **275** = 256 hotels + 18 corridors + 1 hub (declared `add_routes` 275) |
| PHOENIX SERVED ROUTES | **276** = 275 + policy-comparison (built `sitemap.xml`: 281 `<loc>`, 276 Phoenix + 5 global) |
| CANDIDATE MARKETS | **37** |
| CANDIDATE PROFILES | **3,210** (2,954 + 256) |
| CANDIDATE RELEASE-INDEX ROUTES | **3,549** (3,274 + 275) |
| CANDIDATE SERVED ROUTES | **3,619** (3,343 + 276) |

## PHASE 10 — VACATION-OWNERSHIP SAFETY (per property)

Checked against the site the seal built (`C:/t/phx3a/oa/site`), the sealed package and every authority file:

| property | profile | served route | index route | PF record | NP record | seed row | exclusion (shard / global) | partition | site files naming it | representation |
|---|---|---|---|---|---|---|---|---|---:|---|
| Club Wyndham Legacy Golf Resort | NO | NO | NO | NO | NO | NO | NO / NO | NO | 0 | census `non_admitted`, NON_LODGING / TIMESHARE |
| Club Wyndham Orange Tree Resort | NO | NO | NO | NO | NO | NO | NO / NO | NO | 0 | census `non_admitted`, NON_LODGING / TIMESHARE |
| WorldMark Phoenix - South Mountain Preserve | NO | NO | NO | NO | NO | NO | NO / NO | NO | 0 | census `non_admitted`, NON_LODGING / TIMESHARE |
| WorldMark Scottsdale | NO | NO | NO | NO | NO | NO | NO / NO | NO | 0 | census `non_admitted`, NON_LODGING / TIMESHARE |

**VACATION-OWNERSHIP ROWS STILL VERIFIED NO-PETS = 0. VACATION-OWNERSHIP HOTEL PROFILES = 0.**

## PHASE 11 — ALL OTHER SAFETY PRESERVED

| held cohort | rows | published |
|---|---:|---:|
| Places-gated | 48 | **0** |
| dual-brand / shared-campus | 28 | **0** |
| redirect / route-domain | 2 | **0** |
| preopening | 3 | **0** |
| router-exhausted / evidence / source-silent | 88 | **0** |

- **Approved profiles:** 256 / 256 present as sitemap route and profile directory. **Unapproved Phoenix profiles: 0.**
  No-pets rows as profiles: 0.
- **MISLEADING SINGLE FEES PUBLISHED = 0.**
- **Collisions:** seed↔seed / seed↔excl / excl↔seed / excl↔excl = 0 / 0 / 0 / 0. There are 0 duplicate exclusion ids.
- **UNEXPECTED MARKET / PROFILE / ROUTE DELTA = `[]` / `[]` / `[]`** (classifier: 0 / 0 / 0,
  `complete_sets_equal`). Against live, Phoenix is the only new market. Against the superseded 63-no-pets candidate,
  the only change is the intentional removal of four no-pets exclusions. Profiles and routes are identical: 256 /
  275 / 276, and the same bundle.
- `identity_resolutions.json` untouched; no route, domain or identity invented.

## PHASE 12 — DEPLOYMENT REFUSAL

| | |
|---|---|
| CANDIDATE | **PROJECTED / NON-DEPLOYABLE** |
| DEPLOYMENT REFUSAL | **PASS (EXPECTED)** |

- 0 of 40 deployment authorizations and 0 of 39 deployment records name phoenix-az.
- The participation row is `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH`.
- The receipt carries `PRODUCTION_ACTIVATION_ALLOWED = NO`.
- No Netlify.

**Staging gates: 20 of 20 PASS.** They are: package identity, classification, receipt eligibility, FAST A–O, parent
identity, parent routes (H/I), market / profile / route preservation, candidate delta, participation projection,
founder-decision reconciliation (30/30), held-cohort, preopening, vacation-ownership, fee and collision safety,
first-party binding (315/315), release contracts (38 verify) and global authority `--check`. Deployment refusal
PASSES as expected.

## PHASE 13 — LIVE SAFETY (re-verified at 16:36:42Z)

The resolver reports: deploy `6aba7587ddcc33a192bdf694`, 36 markets, 2,954 profiles, 3,343 routes, host verified. The
live sitemap was re-fetched: sha256 **`5d3d07a4…`** (byte-identical), 3,343 `<loc>`, 0 Phoenix.

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

---

## FINAL ANSWERS

```
 1. VACATION-OWNERSHIP PROPERTIES FOUND  = 4 (Club Wyndham Legacy Golf 51351, Club Wyndham Orange Tree 51349,
                                           WorldMark South Mountain 52342, WorldMark Scottsdale 52344)
 2. OLD QUALIFYING CENSUS                = 488
 3. NEW QUALIFYING CENSUS                = 484
 4. OLD PET-FRIENDLY                     = 256
 5. NEW PET-FRIENDLY                     = 256
 6. OLD VERIFIED NO-PETS                 = 63
 7. NEW VERIFIED NO-PETS                 = 59
 8. ACTIONABLE UNRESOLVED                = 0
 9. COVERAGE READY                       = YES BY FOUNDER DECISION (256 / 59; record 003)
10. CORRECTED PACKAGE                    = pkg-phoenix-az-07f7e75699af6a8c
11. PACKAGE DIGEST                       = sha256:07f7e75699af6a8cefe5f083b688f647c55190f04aae0cd0617292968ab0fccf
12. FAST                                 = 15/15 PASS, 0 UNKNOWN, 0 FAILED
13. RULE J NONEMPTY                      = PASS (1,553 files / 1,537 HTML / output present)
14. RULE K NONVACUOUS                    = PASS (BYTE_IDENTICAL, 4 cold builds, 0 reuse)
15. PACKAGE REPRODUCIBLE                 = YES (independent worktree + separate processes: data chain 0 differing
                                           files; digest equal under the registered provenance; site 1,553/1,553)
16. REGISTRATION CORRECTION CLASS        = COMPOSITE_FRESH_MARKET_DATA_ONLY
17. ELIGIBLE                             = YES (15/15)
18. FULL_REGRESSION_REQUIRED             = NO
19. BROAD REGRESSION RUNS                = 0
20. UNCHANGED MARKETS REBUILT            = 0
21. PHOENIX PROJECTED PROFILES           = 256
22. CANDIDATE MARKETS                    = 37
23. CANDIDATE PROFILES                   = 3,210
24. CANDIDATE RELEASE-INDEX ROUTES       = 3,549
25. CANDIDATE SERVED ROUTES              = 3,619
26. CLUB WYNDHAM LEGACY GOLF HOTEL PROFILE = NO
27. CLUB WYNDHAM ORANGE TREE HOTEL PROFILE = NO
28. WORLDMARK SOUTH MOUNTAIN HOTEL PROFILE = NO
29. WORLDMARK SCOTTSDALE HOTEL PROFILE   = NO
30. VACATION-OWNERSHIP ROWS STILL VERIFIED NO-PETS = 0
31. ALL STAGING GATES                    = PASS (20 of 20)
32. DEPLOYMENT REFUSAL                   = PASS (EXPECTED)
33. CURRENT LIVE MODIFIED                = NO
34. DEPLOYMENT PERFORMED                 = NO
35. PHOENIX LIVE                         = NO (hub 404)
36. origin == HEAD                       = YES (verified after the final push)
37. tree clean                           = YES (verified after the final push)
38. READY FOR FOUNDER LAUNCH AUTHORIZATION = YES -- authorize pkg-phoenix-az-07f7e75699af6a8c;
                                           NOT pkg-phoenix-az-85ad9b66
```

```
PHOENIX VACATION-OWNERSHIP CORRECTION = PASS
VACATION-OWNERSHIP HOTEL PROFILES PUBLISHED = 0
VACATION-OWNERSHIP ROWS VERIFIED NO-PETS = 0
PHOENIX PROJECTED PROFILES = 256
FULL_REGRESSION_REQUIRED = NO
BROAD REGRESSION RUNS = 0
UNCHANGED MARKETS REBUILT = 0
CURRENT LIVE MODIFIED = NO
PHOENIX DEPLOYED = NO
READY FOR FOUNDER LAUNCH AUTHORIZATION = YES
```
