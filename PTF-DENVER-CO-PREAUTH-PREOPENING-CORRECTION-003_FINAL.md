# PTF-DENVER-CO-PREAUTH-PREOPENING-CORRECTION-003 — FINAL

The not-yet-open **ECHO Suites Denver North – Thornton** is removed from Denver's publication cohort.

- **Held, not deleted:** its first-party evidence is kept for revalidation, and it is never recorded as verified no-pets.
- **New package:** pkg-denver-co-07f10db29ab56d98, sealed, independently reproduced and re-registered.
- **Candidate:** a new projected, non-deployable candidate with **288** Denver profiles.
- **Status:** AUTHORIZATION_READY. The superseded 289-profile package `pkg-denver-co-91b2e0a2` must not be authorized
  (recorded in `denver_co_founder_coverage_decision_003.json`), and it is kept as history.

Nothing was deployed. No founder or deployment authorization, no Netlify, no broad regression, no spend, no other
market touched, no shared factory code changed.

Branch `worker/ptf-denver-co-market-001`. Commits: `f0a65e78` correction + re-registration, `9db7ac6d` readiness,
then this report.

---

## PHASE 1 — CURRENT LIVE

`release_index live-source --verify-host`, checked at start (00:04Z) and end (00:27Z):

| | |
|---|---|
| CURRENT LIVE | San Diego, deploy `6ab859787d349f8397e1450a`, source `f01587ba` |
| MARKETS / PROFILES / RELEASE-INDEX / SERVED | **35 / 2,666 / 2,969 / 3,037** |
| LIVE SITEMAP | `4f648fff…`, 3,037 `<loc>`, 0 Denver routes |
| HOST VERIFIED | true |
| DENVER LIVE | **NO** (hub 404) |

## PHASE 2 — THE PREOPENING PROPERTY

| | |
|---|---|
| PROPERTY ID | `echo suites denver north thornton opening early 2027` (slug `echo-suites-denver-north-thornton-opening-early-2027`) |
| CANONICAL NAME | ECHO Suites Denver North - Thornton - Opening Early 2027 |
| ADDRESS | 13560 Grant Street, Thornton, CO 80241 (corridor thornton-northglenn-north-i25) |
| BRAND | WYNDHAM (ECHO Suites Extended Stay by Wyndham) |
| PROPERTY CODE | 58277 |
| FIRST-PARTY URL | https://www.wyndhamhotels.com/echo-suites/thornton-colorado/echo-suites-extended-stay-denver-north-thornton/overview |
| CURRENT DISPOSITION (before) | CLEAN_PET_FRIENDLY |
| CURRENT PUBLISHABLE STATE (before) | PUBLISHED_PET_FRIENDLY: one of the 289 profiles in `pkg-denver-co-91b2e0a2` |

**First-party opening status, verified.** The wording comes from Wyndham's **own** property service
(`BWSServices … property/search?propertyId=58277`), whose property-name field reads *"ECHO Suites Denver North -
Thornton - Opening Early 2027"*. That response (sha256 `a730edf1c2080d8f…`) is committed in
`markets/staging/denver-co/raw_captures/wyndham_rows.json`, and it is the same response the census and the pet-policy
quote came from. No third-party source was used.

## PHASE 3 — CORRECTED DISPOSITION

- **New disposition:** `EVIDENCE_HOLD`, an existing Denver class, with hold reason `PREOPENING_NOT_YET_OPEN`.
- **Partition state:** `AWAITING_POLICY_OBSERVATION`, an existing contract enum, because the policy must be re-observed
  once the hotel opens.
- **No shared schema value was invented.**

The rule lives in `denver_co_clean_authority_001.py`. It fires when a property's own first-party name states it has
not opened ("Opening Early 2027", "Coming Soon"). It is market-local and matches **exactly one** Denver row.

**What the row keeps:**

- its first-party quote and the document sha
- `disposition_before_preopening_hold: CLEAN_PET_FRIENDLY`
- `policy_facts_for_revalidation` (dogs, 75 lb)

It is **not** verified no-pets, and it is **not** deleted. CURRENTLY PUBLISHABLE = **NO**.

**Exactly one clean-authority row changed.** The report was compared row by row against the committed report.

## PHASE 4 — RECOMPUTED DENVER ACCOUNTING

| | before | after |
|---|---:|---:|
| QUALIFYING CENSUS | 441 | **441** |
| PET-FRIENDLY | 289 | **288** |
| VERIFIED NO-PETS | 46 | **46** |
| RESOLVED | 335 | **334** |
| UNRESOLVED | 106 | **107** |
| ACTIONABLE UNRESOLVED | 0 | **0** |

The actionability breakdown is router-exhausted 38, new spend 52, founder 16, and **HELD_UNTIL_OPENING 1**. That last
class is new and Denver-local. The preopening row gets its own class so that the 38 / 52 / 16 cohorts are not altered.

Fees are unchanged: 54 published, 80 tiered and 35 unsafe withheld. The ECHO quote never carried a published fee.

## PHASE 5 — COVERAGE DECISION REMAINS IN FORCE

`markets/reports/denver_co_founder_coverage_decision_003.json` is a new record; the 002 record is kept unchanged.

- **COVERAGE READY:** YES BY FOUNDER DECISION, cohort **288** pet-friendly / 46 no-pets.
- **Why it still holds:** the correction makes the publication set safer and opens no acquisition gap. No lane, spend
  or ruling can move a hotel that has not opened.
- **Held:** 38 / 52 / 16, all untouched, plus the 1 preopening row.
- **The superseded package:** the record states that the 289-profile package must not be authorized.
- **Attribution:** transcribed, not signed.

## PHASE 6 — RE-SEALED CORRECTED PACKAGE

- **Package:** `pkg-denver-co-07f10db29ab56d98` (`sha256:07f10db29ab56d982490df7341831d731c8015e198d9805572730113056c6707`),
  sealed via `registration_release_lane seal --work C:/t/den3a` (short forward-slash path).
- **FAST:** **15/15 PASS, 0 UNKNOWN, 0 FAILED**.
- **RULE J NONEMPTY:** PASS, 1,723 files / 1,707 HTML, output present, 0 defects, bundle `475633a2…`. It is 6
  files fewer than the 289-profile bundle: the ECHO profile and its pages.
- **RULE K NONVACUOUS:** PASS, BYTE_IDENTICAL, 4 cold builds, 0 reuse.
- **History:** `pkg-denver-co-91b2e0a2` and its receipt were **not overwritten**; both are still in
  `markets/packages|receipts/denver-co/`.

## PHASE 7 — INDEPENDENT REPRODUCTION

Detached worktree `C:/t/den3b-wt` at `9db7ac6d`, separate processes, work dir `C:/t/den3b`. The process record was
written before start. The worktree was removed afterwards.

1. **Data chain re-derived in the worktree.** The re-derived documents were clean authority, actionability, final
   partition, policy package, proposed authority and shard; `build_global_authority --check` also ran.
   `git status` afterwards was **clean: 0 differing files.**
2. **Seal in a separate OS process.** The package **content is identical**: 127,814 fields compared, and only 4 differ.
   - The differing fields are `created_from_source_sha`, `sealed_at` (not digested) and the digest and id derived from
     them.
   - The registered seal ran on `1b30054f`'s tree plus the uncommitted correction, because the canonical sequence
     seals and then commits. The reproduction sealed the committed `9db7ac6d`.
   - Recomputed under the registered provenance, **the reproduction's digest is exactly `sha256:07f10db2…` and the two
     documents are equal.**
   - The **built site is 1,723 / 1,723 files identical**, with the same bundle `475633a2…`.
   - Both runs pass FAST 15/15, ELIGIBLE YES.

**BYTE IDENTICAL = YES** (under identical provenance). **DIFFERING FILES = 0.**

## PHASE 8 — RE-REGISTRATION OF THE CORRECTED PACKAGE

**Why the plain registration path applies.** Denver is REGISTERED, NOT FOUNDER-AUTHORIZED and NOT LIVE. The repository's
`reregister` lane only accepts a FOUNDER_AUTHORIZED market (it reissues from the authorizing decision). It was not
used and not forced. For an unauthorized market, the classifier's `derive_registration_base` still resolves
**`1724e822`**, the newest ancestor naming no Denver path. So the correction remains one first registration and goes
through the canonical fresh-market path.

**The one step no lane command covers.** `seal --work-order` refuses an already-pinned market, and `register` refuses
an existing row. So `launch_participation.json`, `bundle_cache_closure.json` and
`tests/pettripfinder/pins/market_state.json` were restored to their committed base bytes (`1724e822`); the base
participation loaded with `decision_problems` empty. The **unchanged** writers then re-derived them. This was
authorized by the operator in this session. Nothing was hand-edited.

The sequence ran in this order:

1. clean authority → actionability → final partition → `registration_staging --write` (the policy package, proposed
   authority and partition at the root)
2. `market_registration_cli --write`: 288 seed rows / 46 exclusions
3. `build_global_authority --write`: seed rows 3,104 → **3,103**, exclusions 1,327 unchanged; `--check` clean
4. release contract: 0 disagreements; all 37 contracts verify
5. `register`: participation +1 row against base, **0 other rows changed**; note "288 published pet-friendly";
   closure +2
6. `seal --work-order PTF-DENVER-CO-PREAUTH-PREOPENING-CORRECTION-003`: pin block 441 / 288 / 46 / 16
7. commit `f0a65e78`
8. `packet`

**Classifier result.**

| | |
|---|---|
| REGISTRATION CORRECTION CLASS | **COMPOSITE_FRESH_MARKET_DATA_ONLY** (automatic) |
| ELIGIBLE | **YES**: 15/15 checks PASS (102 changed paths vs `1724e822`: 29 market-local, 13 registration, 60 derived; 0 shared, 0 unknown) |
| FULL_REGRESSION_REQUIRED | **NO** |
| REMOTE BROAD JOBS / BROAD REGRESSION RUNS | **0 / 0** |
| readiness | **AUTHORIZATION_READY**, founder AWAITING_FOUNDER_AUTHORIZATION |

**Lane time:** `register` 6 s + `seal` 404 s (FAST 354.5 s) + `packet` 80 s ≈ **8 m 10 s**, inside the 10-minute hard
limit. The wall clock was ≈ 24 min, from 00:04Z to 00:28Z. The permission question was answered before the timer
started.

## PHASE 9 — PROJECTED CANDIDATE

| | |
|---|---:|
| UNCHANGED LIVE MARKETS REUSED / REBUILT | **35 / 0** (index composed ×2, digests agree; `assembly_required: false`, no other market physically re-rendered) |
| DENVER BUNDLES BUILT | 1 |
| DENVER PROJECTED PROFILES | **288** |
| DENVER RELEASE-INDEX ROUTES | **305** = 288 hotels + 16 corridors + 1 hub (declared `add_routes` 305) |
| DENVER SERVED ROUTES | **306** = 305 + policy-comparison (counted in the built `sitemap.xml`: 311 `<loc>`, 306 Denver + 5 global) |
| CANDIDATE MARKETS | **36** |
| CANDIDATE PROFILES | **2,954** (2,666 + 288) |
| CANDIDATE RELEASE-INDEX ROUTES | **3,274** (2,969 + 305) |
| CANDIDATE SERVED ROUTES | **3,343** (3,037 + 306) |

The Thornton corridor still publishes with 6 profiles, so there are still 16 corridors.

## PHASE 10 — PREOPENING SAFETY

These checks ran against the site the seal built (`C:/t/den3a/oa/site`) and the sealed package.

| | |
|---|---|
| PREOPENING PROFILE PRESENT | **NO** |
| PREOPENING SERVED ROUTE PRESENT | **NO** |
| PREOPENING `/go/` ROUTE PRESENT | **NO** (0 `/go/` pages mention it) |
| PREOPENING RELEASE-INDEX ROUTE PRESENT | **NO** (not in `add_routes`, not a pet-friendly record) |
| HTML pages anywhere mentioning it | **0** |
| Global seed row for it | **0** (global seed has 288 Denver rows) |

The identity and its evidence remain only in nonpublishing market data: the census, clean authority and final
partition.

## PHASE 11 — ALL OTHER SAFETY PRESERVED

| held cohort | rows | published |
|---|---:|---:|
| founder-decision | 16 | **0** |
| — dual-brand halves | 14 | **0** |
| — ESA title collisions | 2 | **0** |
| Places-gated | 52 | **0** |
| router-exhausted | 38 | **0** |
| preopening | 1 | **0** |

- **Approved profiles:** 288 / 288 present. **Unapproved Denver profiles: 0.** No-pets rows as profiles: 0.
- **MISLEADING SINGLE FEES = 0.**
- **Collisions:** seed↔seed / seed↔excl / excl↔seed / excl↔excl = 0 / 0 / 0 / 0.
- **UNEXPECTED MARKET / PROFILE / ROUTE DELTA = `[]` / `[]` / `[]`** (classifier: 0 / 0 / 0, `complete_sets_equal`).
  Against live, Denver is the only new market. Against the superseded 289-profile candidate, the only change is the
  intentional removal of the ECHO profile, which takes the counts from 289 to 288, 306 to 305 and 307 to 306.
- `identity_resolutions.json` untouched; no ESA name altered.

## PHASE 12 — DEPLOYMENT REFUSAL

| | |
|---|---|
| CANDIDATE | **PROJECTED / NON-DEPLOYABLE** |
| DEPLOYMENT REFUSAL | **PASS (EXPECTED)** |

- 0 of 39 authorizations and 0 of 38 records name denver-co.
- The participation row is `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH`.
- The receipt carries `PRODUCTION_ACTIVATION_ALLOWED = NO`.
- No Netlify.

**Staging gates, 21 of 21 PASS:**

package identity · classification · FAST eligibility (1 current receipt for `07f10db2`) · FAST A–O · parent identity ·
parent routes (H / I) · market preservation (35 / 35) · profile preservation · route preservation · candidate delta ·
participation projection · founder-decision reconciliation (16 / 16) · preopening safety · held cohort · dual-brand /
ESA · fee safety · collision safety · first-party binding (334 / 334) · release contracts (37) · global authority
`--check` · deployment refusal.

## PHASE 13 — LIVE SAFETY (00:27:49Z)

| Route | Expected | Actual |
|---|---|---|
| `/pet-friendly-hotels/denver-co/` | 404 | **404** ✅ |
| `/pet-friendly-hotels/san-diego-ca/` | 200 | **200** ✅ |
| `/pet-friendly-hotels/jacksonville-fl/` | 200 | **200** ✅ |
| `/pet-friendly-hotels/west-palm-beach-fl/` | 200 | **200** ✅ |
| `/pet-friendly-hotels/fort-lauderdale-fl/` | 200 | **200** ✅ |
| `/pet-friendly-hotels/augusta-ga/` | 200 | **200** ✅ |
| `/pet-friendly-hotels/detroit-ann-arbor-mi/` | 404 | **404** ✅ |

The live sitemap is `4f648fff…`, byte-identical to the start of this order. **CURRENT LIVE MODIFIED = NO.**

---

## FINAL ANSWERS

```
 1. PREOPENING PROPERTY                  = ECHO Suites Denver North - Thornton - Opening Early 2027,
                                           13560 Grant St, Thornton CO 80241 (Wyndham 58277)
 2. FIRST-PARTY OPENING STATUS           = "Opening Early 2027" -- Wyndham's own property service
                                           (propertyId 58277, sha256 a730edf1...), committed capture
 3. OLD DISPOSITION                      = CLEAN_PET_FRIENDLY (PUBLISHED_PET_FRIENDLY)
 4. NEW DISPOSITION                      = EVIDENCE_HOLD / PREOPENING_NOT_YET_OPEN
                                           (AWAITING_POLICY_OBSERVATION; HELD_UNTIL_OPENING); evidence kept
 5. OLD PUBLISHABLE PROFILE COUNT        = 289
 6. NEW PUBLISHABLE PROFILE COUNT        = 288
 7. ACTIONABLE UNRESOLVED                = 0
 8. COVERAGE READY                       = YES BY FOUNDER DECISION (decision_003; 002 kept)
 9. CORRECTED PACKAGE                    = pkg-denver-co-07f10db29ab56d98 (supersedes pkg-denver-co-91b2e0a2,
                                           kept as history, not to be authorized)
10. PACKAGE DIGEST                       = sha256:07f10db29ab56d982490df7341831d731c8015e198d9805572730113056c6707
11. FAST                                 = 15/15 PASS, 0 UNKNOWN, 0 FAILED
12. RULE J NONEMPTY                      = PASS (1,723 files, bundle 475633a2...)
13. RULE K NONVACUOUS                    = PASS (BYTE_IDENTICAL, 4 cold builds, 0 reuse)
14. PACKAGE REPRODUCIBLE                 = YES -- separate worktree/process; digest identical under the same
                                           provenance, built site 1,723/1,723 identical, DIFFERING FILES 0
15. REGISTRATION CORRECTION CLASS        = COMPOSITE_FRESH_MARKET_DATA_ONLY (registered-not-authorized: base
                                           stays 1724e822; the authorized-only reregister lane not used)
16. ELIGIBLE                             = YES (15/15)
17. FULL_REGRESSION_REQUIRED             = NO
18. BROAD REGRESSION RUNS                = 0
19. UNCHANGED MARKETS REBUILT            = 0
20. DENVER PROJECTED PROFILES            = 288
21. CANDIDATE MARKETS                    = 36
22. CANDIDATE PROFILES                   = 2,954
23. CANDIDATE RELEASE-INDEX ROUTES       = 3,274
24. CANDIDATE SERVED ROUTES              = 3,343
25. PREOPENING PROFILE PRESENT           = NO
26. PREOPENING SERVED ROUTE PRESENT      = NO
27. PREOPENING RELEASE-INDEX ROUTE PRESENT = NO
28. UNAPPROVED DENVER PROFILES           = 0
29. ALL STAGING GATES                    = PASS (21 of 21)
30. DEPLOYMENT REFUSAL                   = PASS (EXPECTED)
31. CURRENT LIVE MODIFIED                = NO
32. DEPLOYMENT PERFORMED                 = NO
33. DENVER LIVE                          = NO (hub 404)
34. origin == HEAD                       = YES (verified after the final push)
35. tree clean                           = YES (verified after the final push)
36. READY FOR FOUNDER LAUNCH AUTHORIZATION = YES -- for pkg-denver-co-07f10db29ab56d98 (288) only
```

```
DENVER PREOPENING CORRECTION = PASS
ECHO SUITES PREOPENING PROFILE PUBLISHED = NO
DENVER PROJECTED PROFILES = 288
FULL_REGRESSION_REQUIRED = NO
BROAD REGRESSION RUNS = 0
UNCHANGED MARKETS REBUILT = 0
CURRENT LIVE MODIFIED = NO
DENVER DEPLOYED = NO
READY FOR FOUNDER LAUNCH AUTHORIZATION = YES
```
