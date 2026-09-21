# PTF-FORT-LAUDERDALE-FL-PRODUCTION-DEPLOYMENT-004 — FINAL

**Worktree** `C:\Atlas-Fort-Lauderdale-FL-Hardened-V1`
**Branch** `worker/ptf-fort-lauderdale-fl-market-001`
**Market** `fort-lauderdale-fl`

## FORT LAUDERDALE IS LIVE

Greater Fort Lauderdale is production market **#32**. The exact founder-authorized candidate
was deployed with no rebuild, verified against the running host before anything was recorded,
and the authorization consumed only after that verification passed.

| | |
|---|---|
| NETLIFY DEPLOYMENT ID | **`6ab1a035c7ef3b14a23a4ec6`** |
| previous deployment (rollback target) | `6ab071a5b7561c33aff6c17b` |
| LIVE BUNDLE | `0ec5c6557d79eaf77a4065b6700c0a5807e9bfe282408dd4779804b33af3a40f` |
| LIVE SITEMAP | `e81961ae76454ce608fcb39624d5147c8779f52b269faab9449138397cb8fa3d` |
| LIVE MARKETS / PROFILES | **32 / 2375** |
| LIVE SERVED SITEMAP ROUTES | **2711** |
| LIVE RELEASE-INDEX ROUTES | **2646** |
| ROLLBACK REQUIRED | **NO** |

---

## PHASE 1 — PREDEPLOY LIVE, REVERIFIED IMMEDIATELY BEFORE DEPLOYING

| | |
|---|---|
| PREDEPLOY LIVE SOURCE COMMIT | `fbaf6f73a8e4ed7fa5cf3d81588219d513743bcd` |
| PREDEPLOY LIVE DEPLOYMENT | `6ab071a5b7561c33aff6c17b` |
| PREDEPLOY LIVE BUNDLE | `b2ad54b9be8b8a0121b8b664ef95e6d4dcf3feb873b4b23558c3721cdc06732a` |
| PREDEPLOY LIVE SITEMAP | `5ac34c75d6ba22d87b5da9d9ff40844dc2e986d7b778760849c03769bb088980` |
| PREDEPLOY LIVE MARKETS | 31 |
| PREDEPLOY LIVE PROFILES | 2290 |
| PREDEPLOY LIVE RELEASE-INDEX ROUTES | 2550 |
| PREDEPLOY LIVE SERVED SITEMAP ROUTES | 2614 |
| HOST VERIFIED | **true** |

Live had not advanced. The parent was exactly the one the authorization binds, so this
deployment was not made against a stale parent.

---

## PHASE 2 — AUTHORIZATION VERIFIED BEFORE USE

| | |
|---|---|
| DEPLOYMENT AUTHORIZATION ID | `ptf-auth-fort-lauderdale-003-0ec5c6557d79` |
| STATUS BEFORE | **AUTHORIZED** |
| CONSUMED BEFORE | **NO** (`deploy_id` was `None`) |
| AUTHORIZED MARKET | `fort-lauderdale-fl`, 85 published profiles, contract sha `2faa85da…` |
| AUTHORIZED BUNDLE | `0ec5c6557d79eaf77a4065b6700c0a5807e9bfe282408dd4779804b33af3a40f` |
| AUTHORIZED SITEMAP | `e81961ae76454ce608fcb39624d5147c8779f52b269faab9449138397cb8fa3d` |
| AUTHORIZED ROLLBACK TARGET | `6ab071a5b7561c33aff6c17b` |
| `verify_authorization` | **PASS** (`[]`) |
| `deployability_problems` | **`[]`** |

---

## PHASE 3 — THE EXACT AUTHORIZED CANDIDATE, LOCATED AND BYTE-VERIFIED

The path is not guessed: the committed authorization module
`fort_lauderdale_fl_deployment_authorization_003.py` records `C:\t\ftl3a` as the artifact the
authorization was built from, and the deployment record now records it too.

`deployment_authorization.verify_bundle_directory` recomputed the bundle digest from the
directory about to be uploaded and returned **`[]`** — the directory IS the authorized bundle.

| Required | Actual | |
|---|---|---|
| BUNDLE SHA256 | `0ec5c6557d79eaf77a4065b6700c0a5807e9bfe282408dd4779804b33af3a40f` | ✓ |
| SITEMAP SHA256 | `e81961ae76454ce608fcb39624d5147c8779f52b269faab9449138397cb8fa3d` | ✓ |
| MARKETS | 32 | ✓ |
| PROFILES | 2375 | ✓ |
| RELEASE-INDEX ROUTES | 2646 | ✓ |
| SERVED SITEMAP ROUTES | 2711 | ✓ |
| FILES | 14,461 | ✓ |
| broken links / collisions / shadowing / canonical violations | 0 / 0 / 0 / 0 | ✓ |
| composed-bundle gates | 27/27 pass | ✓ |

**CANDIDATE INTEGRITY = PASS.** Nothing was rebuilt, resealed, re-registered or reacquired.

---

## PHASE 4 — DELTA SAFETY AGAINST THE PARENT ARTIFACT

| | |
|---|---|
| served routes added | **97** |
| served routes removed | **0** |
| every added route belongs to `fort-lauderdale-fl` | **true** |
| FORT LAUDERDALE HOTEL ROUTES | **85** |
| FORT LAUDERDALE HUB ROUTES | **1** |
| FORT LAUDERDALE CORRIDOR ROUTES | **10** |
| FORT LAUDERDALE COMPARISON ROUTES | **1** |
| PRIOR MARKET ROUTES REMOVED | **0** |
| PRIOR PROFILES REMOVED | **0** |
| UNEXPECTED MARKET / PROFILE / ROUTE DELTA | `[]` / `[]` / `[]` |

---

## PHASE 5 — HOLD / EXCLUSION SAFETY

The candidate contained exactly 85 approved Fort Lauderdale hotel profiles and
**0 unapproved or held profiles**, verified as a set rather than sampled: the 85 published
slugs are exactly the approved set, and no published slug is a held row.

Kept unpublished, and confirmed 404 on the live host after deployment (see Phase 10):

| Rows | Disposition |
|---|---|
| 90 | `ROUTING_HOLD` |
| 89 | `ACCESS_BLOCKED` |
| 69 | `SOURCE_SILENT` |
| 38 | `IDENTITY_MISMATCH_HOLD` — includes the four unresolved dual-brand halves |
| 37 | `EVIDENCE_HOLD` |
| **323** | **total unresolved** |
| 53 | `CLEAN_VERIFIED_NO_PETS` — canonical exclusion representation only, never a profile |

**MIRAMAR / CLEVELAND EXCLUSION COLLISION SAFE = PASS.** Cleveland's Holiday Inn Express &
Suites at 30500 Clemens Rd, Westlake OH was byte-identical in the candidate
(`3147177b0b656ea6…` on both sides) and returns **200** live.

---

## PHASE 6 — LIVE MANIFEST WRITTEN FROM THE AUTHORIZED BYTES

`global_deployment.write_manifest()` — the canonical procedure — was run against the exact
authorized bundle manifest immediately before the deploy call.

| | |
|---|---|
| bundle | `0ec5c6557d79eaf77a4065b6700c0a5807e9bfe282408dd4779804b33af3a40f` |
| sitemap | `e81961ae76454ce608fcb39624d5147c8779f52b269faab9449138397cb8fa3d` |
| markets / profiles | 32 / 2375 |
| release-index routes | 2646 |
| served sitemap routes | 2711 |
| `verify_manifest` | `[]` |

The written live manifest is **byte-identical** to the committed authorized candidate manifest
`global_deployment_manifest_candidate_fort_lauderdale_003.json`. The candidate itself was not
modified.

---

## PHASE 7 — DEPLOY

```
netlify deploy --prod --no-build --dir C:\t\ftl3a\site --site pettripfinder-prod
```

| | |
|---|---|
| DEPLOY START | `2026-09-21T21:22:34Z` |
| DEPLOY COMPLETE | `2026-09-21T21:23:24Z` (50 s) |
| NETLIFY DEPLOYMENT ID | `6ab1a035c7ef3b14a23a4ec6` |
| DEPLOY URL | `https://pettripfinder.com` |
| unique deploy URL | `https://6ab1a035c7ef3b14a23a4ec6--pettripfinder-prod.netlify.app` |
| EXIT STATUS | **0** |
| CDN | requested and uploaded **520** files; "Deploy is live!" |

`--no-build` was used, so Netlify built and regenerated nothing. Only the verified candidate
directory was uploaded. 520 files is the expected transfer: the 518 new Fort Lauderdale files
plus `sitemap.xml` and its control-file companion — the other 13,941 files were already
identical on the CDN, which is the same fact Phase 4 proves from the other side.

---

## PHASE 8 — IMMEDIATE HOST VERIFICATION

| | |
|---|---|
| HOST SITEMAP SHA | `e81961ae76454ce608fcb39624d5147c8779f52b269faab9449138397cb8fa3d` |
| AUTHORIZED SITEMAP SHA | `e81961ae76454ce608fcb39624d5147c8779f52b269faab9449138397cb8fa3d` |
| **HOST SITEMAP MATCH** | **PASS** |
| LIVE MARKETS | **32** |
| LIVE PROFILES | **2375** |
| LIVE SERVED SITEMAP ROUTES | **2711** |

The running production host serves the exact authorized bytes.

---

## PHASE 9 — EVERY FORT LAUDERDALE ROUTE, FETCHED

Not sampled — every route fetched individually against the live host.

| | |
|---|---|
| FORT LAUDERDALE EXPECTED ROUTES | **97** |
| routes in the live sitemap | **97** |
| **ROUTES HTTP 200** | **97** |
| **ROUTES MISSING** | **0** |
| 85 hotel profile routes | all 200 |
| 1 hub route | 200 |
| 10 publishing corridor routes | all 200 |
| 1 policy-comparison route | 200 |

**Corridors live (10), exactly as the authorized candidate declared:**
`coral-springs-coconut-creek`, `cypress-creek`, `dania-beach`, `deerfield-beach`,
`fll-airport-sr84`, `fort-lauderdale-beach`, `hollywood-beach`, `pembroke-pines-miramar`,
`plantation-davie`, `port-everglades-17th-street`.

**Corridors suppressed (8), still suppressed, exactly as the candidate declared:**
`downtown-las-olas`, `galt-ocean-lauderdale-by-the-sea`, `hallandale-beach`, `hollywood`,
`oakland-park-wilton-manors`, `pompano-beach`, `sunrise-tamarac-lauderhill`,
`weston-southwest-ranches`. Each is below its own publication minimum; none was forced.

---

## PHASE 10 — HELD PROFILE PRODUCTION CHECK

The would-be live route of **every** held and verified-no-pets Fort Lauderdale row was fetched
— 376 of them, not a sample — and every one returned **404**.

| Probed | Disposition | Not 404 |
|---|---|---|
| 90 | `ROUTING_HOLD` | 0 |
| 89 | `ACCESS_BLOCKED` | 0 |
| 69 | `SOURCE_SILENT` | 0 |
| 38 | `IDENTITY_MISMATCH_HOLD` | 0 |
| 37 | `EVIDENCE_HOLD` | 0 |
| 53 | `CLEAN_VERIFIED_NO_PETS` | 0 |
| **376** | **total** | **0** |

| | |
|---|---|
| APPROVED FORT LAUDERDALE PROFILES LIVE | **85** |
| **HELD / UNAPPROVED FTL PROFILES ERRONEOUSLY LIVE** | **0** |
| published slugs that are a held row | **none** |

---

## PHASE 11 — PRIOR PRODUCTION PRESERVATION

Complete **set** preservation, then complete HTTP verification — not arithmetic.

| | |
|---|---|
| parent served routes | 2614 |
| parent routes still in the live sitemap | 2614 |
| **PRIOR ROUTES LOST** | **0** |
| parent routes individually refetched | 2614 |
| **prior routes not 200** | **0** |
| **PRIOR MARKETS LOST** | **0** (31/31 preserved) |
| **PRIOR PROFILES LOST** | **0** (2290 preserved, 2290 + 85 = 2375) |
| routes added that are not Fort Lauderdale's | **0** |

Representative HTTP verification:

| | |
|---|---|
| `/pet-friendly-hotels/miami-fl/` | 200 |
| `/pet-friendly-hotels/augusta-ga/` | 200 |
| `/pet-friendly-hotels/tampa-fl/` | 200 |
| `/pet-friendly-hotels/orlando-fl/` | 200 |
| `/pet-friendly-hotels/savannah-ga/` | 200 |
| `/pet-friendly-hotels/cleveland-akron-canton/` | 200 |
| **`/pet-friendly-hotels/cleveland-akron-canton/holiday-inn-express-suites/`** | **200** |
| `/`, `/pet-friendly-hotels/`, `/about/`, `/contact/`, `/methodology/`, `/robots.txt`, `/llms.txt` | 200 |
| `/pet-friendly-hotels/detroit-ann-arbor-mi/` (withheld) | **404** |

The Cleveland/Westlake check matters more than a routine spot check: registration had to
repair a cross-market exclusion collision at its source because a Florida DBPR bare chain flag
in Miramar was barring that exact Cleveland profile. It is live, 200, and byte-identical.

---

## PHASE 12 — POSTDEPLOY QUALITY

| | |
|---|---|
| BROKEN LINKS | **0** |
| ROUTE COLLISIONS | **0** |
| CANONICAL VIOLATIONS | **0** |
| GLOBAL SHADOWING | **0** |
| UNEXPECTED DELTA | **`[]`** |

No legacy broad regression was run.

### The two route accountings, reconciled and deliberately NOT made equal

| | |
|---|---|
| RELEASE-INDEX ROUTES | **2646** |
| SERVED SITEMAP ROUTES | **2711** |
| difference | **65** |

The 65 is the release-global surface no market owns — 64 routes, unchanged from the parent —
**plus one**: `/pet-friendly-hotels/fort-lauderdale-fl/policy-comparison/`, which is served but
is not counted as a market-owned release-index route. That is exactly why Fort Lauderdale
contributes **96 release-index routes and 97 served routes**. The two systems are not supposed
to agree and were not forced to.

---

## PHASE 13 — LIVE STATE FINALIZED

Recorded only after host verification passed.

| | |
|---|---|
| deployment record | `ptf-deploy-fort-lauderdale-004-6ab1a035c7ef3b14a23a4ec6.json` |
| `verify_record` | `[]` |
| **DEPLOYMENT AUTHORIZATION CONSUMED** | **YES** — AUTHORIZED → **DEPLOYED** |
| deployment pin | moved to `6ab1a035c7ef3b14a23a4ec6`; live and source agree, `ahead_of_production` false |
| current-live reference | resolver now returns `6ab1a035c7ef3b14a23a4ec6`, 32 / 2375 / 2711, **host verified** |
| current live source commit | `e82120cce7e48c62d3c1057a6c82785bed920485` |

**FORT LAUDERDALE PARTICIPATION = `FOUNDER_AUTHORIZED_FOR_LAUNCH`, which IS the canonical live
state.** There is no separate "LIVE" participation status in the vocabulary — every live
market, Miami included, carries `FOUNDER_AUTHORIZED_FOR_LAUNCH`. Liveness is carried by the
deployment record, the pin and the resolver, not by a participation string, so participation
correctly needed no further write and **no unrelated participation was altered**. Detroit
remains `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH` and returns 404 live.

Every number in the deployment record is **read from the host-verification report**, not typed:
the record module refuses to run without that report and refuses to write if it does not say
PASS.

---

## PHASE 14 — ROLLBACK

**ROLLBACK REQUIRED = NO.** No rollback condition occurred:

| Condition | Result |
|---|---|
| authorized bundle mismatch | none — host sitemap hashes to the authorized candidate |
| served sitemap mismatch | none |
| Fort Lauderdale route loss | none — 97/97 live |
| prior route loss | none — 0 of 2614 |
| prior profile loss | none — 0 |
| held-property publication | none — 376/376 held rows 404 |
| unexpected delta | none |
| critical broken links | none |
| accounting mismatch | none |

Rollback target `6ab071a5b7561c33aff6c17b` remains recorded and available.

---

## PHASE 15 — FINAL PRODUCTION ACCOUNTING

| | |
|---|---|
| LIVE MARKETS | **32** |
| LIVE PROFILES | **2375** |
| LIVE SERVED SITEMAP ROUTES | **2711** |
| LIVE RELEASE-INDEX ROUTES | **2646** |
| FORT LAUDERDALE PROFILES LIVE | **85** |
| FORT LAUDERDALE SERVED ROUTES LIVE | **97** |
| FORT LAUDERDALE RELEASE-INDEX ROUTES | **96** |
| FORT LAUDERDALE CORRIDORS LIVE | **10** |
| PRIOR MARKETS PRESERVED | **31 / 31** |
| PRIOR PROFILES LOST | **0** |
| PRIOR ROUTES LOST | **0** |

---

## PHASE 16 — STALE TEST GAP (follow-up technical debt, NOT repaired here)

`tests/pettripfinder/test_launch_participation_046.py` was not touched by this order.

It carries stale historical assertions from the Charlotte / Indianapolis era — it asserts
`"Charlotte" in decision["reason"]` and pins an Indianapolis-era live set, and its own comment
says *"The CURRENT decision is the Charlotte registration. Each reissue moves these lines."*
Every market registered since Charlotte has moved that decision and nobody moved the pin.
Together with `test_participation_lineage_contract_006.py` and
`test_per_market_release_contracts.py` that is 8 failing tests.

**Consequence worth naming plainly: the participation record has had no effective test guard
across multiple launches.** This deployment was not blocked by it, because the exact failure
sets were proven identical before and after authorization — 4 failed, 439 passed, 2 skipped on
both sides, **NEW AUTHORIZATION FAILURES = 0** — so nothing here regressed. It still needs its
own bounded repair order, now that Fort Lauderdale is live.

---

## FINAL ANSWERS

1. **PREDEPLOY LIVE DEPLOYMENT** = `6ab071a5b7561c33aff6c17b`
2. **PREDEPLOY LIVE BUNDLE** = `b2ad54b9be8b8a0121b8b664ef95e6d4dcf3feb873b4b23558c3721cdc06732a`
3. **DEPLOYMENT AUTHORIZATION** = `ptf-auth-fort-lauderdale-003-0ec5c6557d79`
4. **AUTHORIZATION STATUS BEFORE** = AUTHORIZED, unconsumed (`deploy_id` None)
5. **AUTHORIZED CANDIDATE BUNDLE** = `0ec5c6557d79eaf77a4065b6700c0a5807e9bfe282408dd4779804b33af3a40f`
6. **AUTHORIZED CANDIDATE SITEMAP** = `e81961ae76454ce608fcb39624d5147c8779f52b269faab9449138397cb8fa3d`
7. **CANDIDATE INTEGRITY** = PASS — `verify_bundle_directory` `[]`, 14,461 files, 32 markets, 27/27 gates, 0 broken/collisions/shadowing/canonical
8. **NETLIFY DEPLOYMENT ID** = `6ab1a035c7ef3b14a23a4ec6`
9. **NETLIFY RESULT** = SUCCESS, exit 0, 50 s, 520 files uploaded, `--no-build`
10. **HOST SITEMAP MATCH** = PASS
11. **LIVE MARKETS** = 32
12. **LIVE PROFILES** = 2375
13. **LIVE RELEASE-INDEX ROUTES** = 2646
14. **LIVE SERVED SITEMAP ROUTES** = 2711
15. **FORT LAUDERDALE PROFILES LIVE** = 85
16. **FORT LAUDERDALE RELEASE-INDEX ROUTES** = 96
17. **FORT LAUDERDALE SERVED ROUTES** = 97
18. **FORT LAUDERDALE CORRIDORS LIVE** = 10 (8 suppressed, none forced)
19. **FORT LAUDERDALE ROUTES HTTP 200** = 97 / 97, 0 missing
20. **HELD / UNAPPROVED FTL PROFILES ERRONEOUSLY LIVE** = 0 (376/376 held rows 404)
21. **PRIOR MARKETS LOST** = 0
22. **PRIOR PROFILES LOST** = 0
23. **PRIOR ROUTES LOST** = 0 (all 2614 refetched 200)
24. **CLEVELAND/WESTLAKE PROFILE PRESERVED** = YES — 200 live, byte-identical
25. **BROKEN LINKS** = 0
26. **COLLISIONS** = 0
27. **CANONICAL VIOLATIONS** = 0
28. **GLOBAL SHADOWING** = 0
29. **UNEXPECTED DELTA** = `[]`
30. **DEPLOYMENT AUTHORIZATION CONSUMED** = YES (AUTHORIZED → DEPLOYED)
31. **FORT LAUDERDALE PARTICIPATION** = `FOUNDER_AUTHORIZED_FOR_LAUNCH` — the canonical live state; pin and record carry liveness
32. **ROLLBACK REQUIRED** = NO
33. **CURRENT LIVE DEPLOYMENT** = `6ab1a035c7ef3b14a23a4ec6`
34. **CURRENT LIVE BUNDLE** = `0ec5c6557d79eaf77a4065b6700c0a5807e9bfe282408dd4779804b33af3a40f`
35. **origin == HEAD** = YES
36. **tree clean** = YES
37. **FORT LAUDERDALE LIVE** = YES

---

FORT LAUDERDALE PRODUCTION DEPLOYMENT = PASS
LIVE MARKETS = 32
LIVE PROFILES = 2375
LIVE SERVED ROUTES = 2711
FORT LAUDERDALE PROFILES LIVE = 85
FORT LAUDERDALE ROUTES LIVE = 97
PRIOR MARKETS LOST = 0
PRIOR ROUTES LOST = 0
HELD FORT LAUDERDALE PROFILES ERRONEOUSLY LIVE = 0
ROLLBACK REQUIRED = NO
FORT LAUDERDALE LIVE = YES

STOP.
