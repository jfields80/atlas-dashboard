# PTF-NEW-ORLEANS-LA-PRODUCTION-DEPLOYMENT-004 — FINAL

**Status:** NEW ORLEANS IS LIVE. Netlify deploy **`6ac5ba3bcda3a604f7e467e0`** published 2026-10-07T03:19:56.230Z.
Production is now **44 markets / 4,240 profiles / 4,663 release-index routes / 4,740 served routes**. Rollback was not
required.

- **Branch:** `worker/ptf-new-orleans-la-market-001`.
- **Live lineage commit:** `90624cd8`. This is the deployment-state commit; the resolver names it
  CURRENT_LIVE_SOURCE_COMMIT, built_from `4c7e7b90`.
- **Final commit:** this report.

## 1. Predeploy parent (Phase 1)

Re-resolved immediately before the deploy at 02:59Z (canonical resolver, Netlify `getSite`, hash of the served
sitemap). Re-checked again at 03:18Z, straight after the live manifest was written: still `6ac4dc8a`, ready, sitemap
`3d5d9425…`.

| | |
|---|---|
| PREDEPLOY LIVE SOURCE COMMIT | `117afe1105f920a8fcebd5bc1f4c4e2be9bb3ed3` (built_from `c6609370`) |
| PREDEPLOY LIVE DEPLOYMENT | **`6ac4dc8a39b0e7274828a32b`** (Kansas City; host `published_deploy` = this id, state ready) |
| PREDEPLOY LIVE BUNDLE | `6a35c23829f9c0a0a1713acc721f3fcf317a94d7f57120379ffc951fdc60ed5f` |
| PREDEPLOY LIVE SITEMAP | `3d5d9425a4e0a90b6aca13f3d02866a815ebc934df8382e4fcf03c0ecc10967b`. The served sitemap hashed to it and is byte-identical to the live artifact `C:/t/kc4a`. Saved as the parent route set: 4,628 locs |
| PREDEPLOY LIVE MARKETS / PROFILES | 43 / 4,136 |
| PREDEPLOY LIVE RELEASE-INDEX / SERVED ROUTES | 4,552 / 4,628 |
| HOST VERIFIED | YES |

## 2. Authorization and candidate integrity (Phases 2–9)

`new_orleans_la_deployment_004.py predeploy` (`markets/reports/new_orleans_la_predeploy_004.json`): **PASS**
(02:59:42 → 03:18:27Z).

The module is market-local, derived from Kansas City's 004 module with every structural check unchanged. It adds New
Orleans' own municipality, name-twin, held-row and rental checks.

| | |
|---|---|
| DEPLOYMENT AUTHORIZATION | `ptf-auth-new-orleans-003-af70e0aa8a64` |
| status before | **AUTHORIZED**; CONSUMED NO; deploy_id none; new-orleans-la is in the authorization |
| AUTHORIZED PACKAGE | `pkg-new-orleans-la-0e5fef6af3af8339` (from the readiness packet and the authorization source) |
| AUTHORIZED BUNDLE | `af70e0aa8a64496e53c67750668c33029cbda3cf318d9d3ecb1198af346a0a41` (read from the authorization) |
| AUTHORIZED SITEMAP | `beb98d7a9f4687c337dfcbd5eaa1d301ac7d74eecddba5dcebf7d7b05c2a8508` (read from the authorization) |
| AUTHORIZED SOURCE COMMIT | `4c7e7b90b95042576f12f885e94684e7a7f54a08` (the founder-decision BUILD commit) |
| AUTHORIZED PARENT / rollback | `6ac4dc8a39b0e7274828a32b`; 25,580 files; 44 markets / 4,240 profiles / 4,740 served |
| verify_authorization / deployability_problems / verify_target | `[]` / `[]` / `[]` (target pettripfinder-prod) |
| verify_bundle_directory | `[]`. All 25,580 files in `C:\t\nola4a\site`, re-hashed from disk, equal the authorization. **AUTHORIZED BUNDLE MATCH PASS, AUTHORIZED SITEMAP MATCH PASS** |
| candidate manifest | `GD.build_manifest` of the bundle on disk equals the committed candidate manifest |
| determinism evidence | BYTE_IDENTICAL, 25,580 files compared, 0 differing (the authorization order's accounting, re-read) |
| candidate accounting | 44 / 4,240 / 4,663 / 4,740; New Orleans 104 / 111 / 112 |
| delta | prior markets / profiles / release-index routes / served routes lost 0. Unexpected market, profile, route and served-route deltas `[]`. Prior files removed 0, prior-market files changed 0, changed global artifacts only `sitemap.xml` |
| held content | unapproved profiles 0. Every held group published 0, including the 1600 Canal pair, The Garden District Hotel, Maison DuBois / Maison Dupuy, the preopening Fairmont and the closed Claiborne Mansion. 179 unresolved rows and 64 verified-no-pets rows: 0 profiles. Timeshare, rentals and military: 0 |
| municipality | 104 pages: Orleans 79, Jefferson 24, Plaquemines 1. Wrong state / city / ZIP 0; other-market text 0; fixed identities correct |
| Wyndham twin | Kenner bound to code 46094; built page states the Kenner building; Metairie map row published 0; held row shape exact; cross-building collision 0 |
| reader / fee / collision | all reader counters 0; misleading single fees 0; cross-market PASS; bare-chain collisions 0; duplicate excluded identities 0 |
| FAST receipt | `pkg-new-orleans-la-0e5fef6af3af8339-ea4d8ec3d090dfc1`: currently eligible, J PASS, K PASS (BYTE_IDENTICAL), 0 defects |

**CANDIDATE INTEGRITY = PASS.** Nothing was rebuilt, resealed or reassembled.

## 3. Live manifest and the deploy (Phases 10–11)

**Live manifest.** `deploy/netlify/global_deployment_manifest.json` was written from the exact authorized bytes
immediately before the deploy:
- `verify_manifest []`;
- byte-identical (`cmp`) to the committed candidate manifest;
- bundle `af70e0aa…`, sitemap `beb98d7a…`, 44 markets, 4,240 profiles, 4,740 served routes.

**Command, run ONCE:** `netlify deploy --prod --no-build --dir C:\t\nola4a\site --site pettripfinder-prod`.

| | |
|---|---|
| DEPLOY START | 2026-10-07T03:18:55Z |
| DEPLOY COMPLETE | 2026-10-07T03:19:56Z (host `published_at` 03:19:56.230Z) |
| NETLIFY DEPLOYMENT ID | **`6ac5ba3bcda3a604f7e467e0`** |
| EXIT STATUS | 0, "Deploy is live!" |

The CDN diff requested 625 files. The 623 new New Orleans files and the regenerated sitemap account for 624; the host's
diff picked one more, as it did for Kansas City (957 vs 956). Every served check still matches the authorized
candidate.

No Netlify build ran.

## 4. Host verification (Phases 12–15)

`new_orleans_la_deployment_004.py verify-live` (`markets/reports/new_orleans_la_live_verification_004.json`):
**ALL LIVE CHECKS PASS (19 / 19), ROLLBACK_REQUIRED NO.**

| check | result |
|---|---|
| HOST SITEMAP MATCH | **PASS**. The served `sitemap.xml` hashes to `beb98d7a…`, and the served route SET equals the authorized candidate's |
| host deploys | publishes `6ac5ba3b…` (ready, production); previous deploy `6ac4dc8a` = the authorized parent |
| LIVE accounting | **44 markets / 4,240 profiles / 4,663 release-index / 4,740 served** |
| NEW ORLEANS ROUTES | 112 expected, derived from the authorized candidate's own sitemap (not from arithmetic). **112 / 112 HTTP 200**, 0 missing. Profiles live 104; 6 corridors live (CBD-Canal Street, French Quarter-Marigny-Bywater, Harvey-West Bank, Metairie, MSY Airport-Kenner, Warehouse District-Convention Center) |
| PRIOR ROUTES | all **4,628 / 4,628** parent routes 200; 0 lost; only New Orleans routes added |
| byte identity | **31 / 31** sampled pages byte-identical to the artifact: global surfaces; the New Orleans hub, comparison page, corridors and profiles; 16 other market hubs |
| HELD ROWS | all **243** unpublished census rows (179 held + 64 verified-no-pets), probed at census slug and site route (270 URLs): every one **404** |
| FOUNDER-HELD ROWS | SpringHill Suites + TownePlace Suites (1600 Canal St), The Garden District Hotel, Maison DuBois, Maison Dupuy, Fairmont (preopening), Claiborne Mansion (closed): **404** |
| TIMESHARE / RENTALS / MILITARY | the 7 timeshare identities (Bluegreen La Pension ×2, Club Wyndham Avenue Plaza, Club Wyndham La Belle Maison, Holiday Inn Club Vacations ×2, WorldMark Hotel): **404**, named on no New Orleans page. The Syd, Castle Day and Compass Point Events: **404**, named on no page. 0 military identities |
| MUNICIPALITIES | all **104** live profiles' structured address states LA, the census municipality and the row's own ZIP. By parish: Orleans 79, Jefferson 24, Plaquemines 1. By municipality: New Orleans 79, Metairie 6, Harvey 6, Kenner 5, Gretna 3, Harahan 2, Avondale 1, Belle Chasse 1, Elmwood 1. **Wrong-city 0** (no Kenner, Metairie, Gretna, Harvey or other Jefferson Parish property written as New Orleans); wrong state / municipality / ZIP 0 |
| MUNICIPALITY TRAPS | Residence Inn Elmwood → Elmwood, Holiday Inn West Bank Tower → Gretna, Red Roof Westbank → Harvey, Wyndham Garden → Kenner: **200**, each page stating that municipality. Clarion Airport (Metairie), Hilton New Orleans Airport (verified no-pets) and Brent House (held): **404** |
| WYNDHAM NAME TWIN | Kenner hotel (4535 Williams Blvd, 70065, Wyndham property code **46094**, PROPERTY_PAGE lane): **200**, and its live page states the Kenner building. Held map-only row (6401 Veterans Memorial Boulevard, Metairie 70003, OSM only, IDENTITY_REVIEW_REQUIRED): its street appears on **0 of the 112** served New Orleans pages. **METAIRIE MAP-TWIN PUBLISHED 0, CURRENT CROSS-BUILDING COLLISION 0** |
| representative markets | Kansas City, Minneapolis, Portland, Seattle, San Antonio, Austin, Phoenix, Denver, San Diego, Jacksonville FL, West Palm Beach, Fort Lauderdale, Augusta, Miami, Tampa, Orlando **200**; New Orleans hub **200**; Detroit **404** (still withheld) |
| bundle quality | broken links 0, collisions 0, global shadowing 0, canonical violations 0 |

### The parent-route sweep

It ran as one detached orchestrator of sequential 400-route batches (12 batches), each written to `C:/t/nolad/prior_batches/` by atomic rename, 03:20:26 → ~03:32Z.

- **Batches 8 and 9** overlapped a short window in which pettripfinder.com did not answer this machine. Batch 9 had 81 first-pass no-responses, all 200 on its in-batch retry. Batch 8 had 5 routes still `000` after its retry: 5 Piedmont Triad profiles.
- **All 5 returned 200 on the normal refetch afterwards.** No route was lost; the first-pass file is kept (`C:/t/nolad/prior_sweep.txt.first`).
- **Final:** 4,628 checked, 4,628 HTTP 200.

### Held content, reader and fee safety live

| | |
|---|---|
| UNAPPROVED NEW ORLEANS PROFILES LIVE | **0** |
| DUAL-BRAND HOLDS (1600 Canal) | **0 / 2** |
| GARDEN DISTRICT HOTEL / MAISON DUBOIS / MAISON DUPUY | **0 / 0 / 0** |
| PREOPENING / CLOSED | **0 / 0** |
| TIMESHARE / PRIVATE-VENUE RENTALS | **0 / 0** |
| all unresolved rows | **0 / 179** |
| verified-no-pets as hotel profiles | **0 / 64** |
| reader | PET-FRIENDLY WITH EXPLICIT REFUSAL 0, QUESTION-ONLY 0, SERVICE-ANIMAL-ONLY ACCEPTANCE 0. The served bytes are the authorized bytes: sitemap, route set and 31 sampled pages |
| fees | MISLEADING SINGLE FEES 0; 29 single-basis fees publish; 22 tiered and 10 unsafe fees stay withheld |
| Crowne Plaza Astor | live page byte-identical to the artifact (`8892d730…`). It publishes **no fee of its own**: its "35 USD nightly, maximum 70 USD" quote is not flattened. The only amount on the page is a related-hotel card for AC Hotel New Orleans French Quarter |
| collisions | CROSS-MARKET 0, BARE-CHAIN 0, DUPLICATE EXCLUDED IDENTITIES 0 |

## 5. Bounded postdeploy checks (Phase 16)

No broad regression was run.

| | |
|---|---|
| pin and reader tests | `contracts/test_market_state_pins.py` + `test_question_negation_reader_001.py`: **327 / 327 passed** (8.5 s; one pytest process; run on the finalized state) |
| release contracts | `verify_all()` **45 / 45** clean |
| global authority | `build_global_authority --check`: all generated artifacts match the shards |
| FAST receipt | still currently eligible (the only receipt selected). **RULE J NONEMPTY PASS** (644 files / 628 HTML, bundle `047825df…`); **RULE K NONVACUOUS PASS** (BYTE_IDENTICAL); 0 defects |
| quality | BROKEN LINKS 0, COLLISIONS 0, CANONICAL VIOLATIONS 0, GLOBAL SHADOWING 0, UNEXPECTED DELTA `[]` |

## 6. Deployment state finalized (Phase 17)

Written only after all 112 New Orleans routes, all 4,628 parent routes and the host verification passed:

| | |
|---|---|
| authorization | `ptf-auth-new-orleans-003-af70e0aa8a64`: AUTHORIZED → **DEPLOYED**, CONSUMED YES (consumed_by PTF-NEW-ORLEANS-LA-PRODUCTION-DEPLOYMENT-004, deployment `6ac5ba3b…`) |
| deployment record | `ptf-deploy-new-orleans-004-6ac5ba3bcda3a604f7e467e0`. `work_order` = the authorizing 003; `deployer.work_order` = this 004 (with `authorizing_work_order`); `verify_record []` |
| supersessions | `ptf-auth-kansas-city-003-6a35c23829f9` marked Historical (moved list `[]`, verified by re-hashing its release contracts). `ptf-auth-new-orleans-003-af70e0aa8a64` appended as the CURRENT entry with an empty moved list. `reviewed_by` = this order |
| pin | `tests/pettripfinder/pins/deployment_state.json`: live = `6ac5ba3b…`, 44 markets, 4,240 profiles, 4,740 served, source commit `4c7e7b90`, rollback target `6ac4dc8a`; live and source agree |
| participation | new-orleans-la stays FOUNDER_AUTHORIZED_FOR_LAUNCH (the live state); 44 authorized; `decision_problems []` |
| lineage | the resolver returns CURRENT_LIVE_SOURCE_COMMIT `90624cd8` (built_from `4c7e7b90`, deploy `6ac5ba3b`, 4,240 / 4,740, host verified). `derive_registration_base` returns `90624cd8` for the next market |

## 7. Rollback decision (Phase 18)

**ROLLBACK REQUIRED: NO.** None of the following was found:
- authorized-byte mismatch or sitemap mismatch
- New Orleans route loss, parent route loss after retry, or prior profile loss
- held-profile publication or wrong-city publication
- reader contradiction, collision or canonical violation
- accounting mismatch

Rollback target `6ac4dc8a39b0e7274828a32b` was not used.

## 8. Final accounting (Phase 19)

| | |
|---|---:|
| LIVE MARKETS | **44** |
| LIVE PROFILES | **4,240** |
| LIVE RELEASE-INDEX ROUTES | **4,663** |
| LIVE SERVED ROUTES | **4,740** |
| NEW ORLEANS PROFILES LIVE | **104** |
| NEW ORLEANS RELEASE-INDEX ROUTES | **111** |
| NEW ORLEANS SERVED ROUTES | **112** |
| PRIOR MARKETS PRESERVED | **43 / 43** |
| PRIOR PROFILES LOST | **0** |
| PRIOR ROUTES LOST | **0** |

All processes created by this order ended: predeploy, the two sweeps and verify-live. No unrelated process was touched.

## FINAL ANSWERS

1. PREDEPLOY LIVE DEPLOYMENT = 6ac4dc8a39b0e7274828a32b
2. DEPLOYMENT AUTHORIZATION = ptf-auth-new-orleans-003-af70e0aa8a64
3. AUTHORIZATION STATUS BEFORE = AUTHORIZED (consumed NO, deploy_id none)
4. AUTHORIZED PACKAGE = pkg-new-orleans-la-0e5fef6af3af8339
5. AUTHORIZED CANDIDATE BUNDLE = af70e0aa8a64496e53c67750668c33029cbda3cf318d9d3ecb1198af346a0a41
6. AUTHORIZED CANDIDATE SITEMAP = beb98d7a9f4687c337dfcbd5eaa1d301ac7d74eecddba5dcebf7d7b05c2a8508
7. CANDIDATE INTEGRITY = PASS (25,580 files re-hashed equal to the authorization; BYTE_IDENTICAL, 0 differing)
8. NETLIFY DEPLOYMENT ID = 6ac5ba3bcda3a604f7e467e0
9. NETLIFY RESULT = exit 0, "Deploy is live!" (published 2026-10-07T03:19:56Z)
10. HOST SITEMAP MATCH = PASS
11. LIVE MARKETS = 44
12. LIVE PROFILES = 4,240
13. LIVE RELEASE-INDEX ROUTES = 4,663
14. LIVE SERVED ROUTES = 4,740
15. NEW ORLEANS PROFILES LIVE = 104
16. NEW ORLEANS RELEASE-INDEX ROUTES = 111
17. NEW ORLEANS SERVED ROUTES = 112
18. NEW ORLEANS ROUTES HTTP 200 = 112 / 112
19. NEW ORLEANS WRONG-CITY IDENTITIES LIVE = 0
20. METAIRIE MAP-TWIN PUBLISHED = 0
21. KENNER WYNDHAM FIRST-PARTY CODE = 46094 (published, live 200, page states 4535 Williams Blvd, Kenner 70065)
22. DUAL-BRAND HOLDS PUBLISHED = 0
23. GARDEN DISTRICT HOTEL PUBLISHED = 0
24. MAISON DUBOIS PUBLISHED = 0
25. MAISON DUPUY PUBLISHED = 0
26. PREOPENING PROFILES PUBLISHED = 0
27. TIMESHARE PROFILES PUBLISHED = 0
28. PRIVATE / VENUE RENTALS PUBLISHED = 0
29. UNAPPROVED NEW ORLEANS PROFILES LIVE = 0
30. PET-FRIENDLY WITH EXPLICIT REFUSAL = 0
31. QUESTION-ONLY PET-FRIENDLY = 0
32. SERVICE-ANIMAL-ONLY ACCEPTANCE = 0
33. MISLEADING SINGLE FEES = 0
34. PARENT ROUTES CHECKED = 4,628 (4,628 HTTP 200)
35. PRIOR MARKETS LOST = 0
36. PRIOR PROFILES LOST = 0
37. PRIOR ROUTES LOST = 0
38. DETROIT STILL WITHHELD = YES (404)
39. RULE J NONEMPTY = PASS
40. RULE K NONVACUOUS = PASS
41. BROKEN LINKS = 0
42. COLLISIONS = 0
43. CANONICAL VIOLATIONS = 0
44. GLOBAL SHADOWING = 0
45. UNEXPECTED DELTA = []
46. DEPLOYMENT AUTHORIZATION CONSUMED = YES (AUTHORIZED → DEPLOYED)
47. NEW ORLEANS PARTICIPATION = FOUNDER_AUTHORIZED_FOR_LAUNCH (live; decision_problems [])
48. ROLLBACK REQUIRED = NO
49. CURRENT LIVE DEPLOYMENT = 6ac5ba3bcda3a604f7e467e0
50. origin == HEAD = YES (verified after push)
51. tree clean = YES (verified after push)
52. NEW ORLEANS LIVE = YES

NEW ORLEANS PRODUCTION DEPLOYMENT = PASS
LIVE MARKETS = 44
LIVE PROFILES = 4240
LIVE SERVED ROUTES = 4740
NEW ORLEANS PROFILES LIVE = 104
NEW ORLEANS ROUTES LIVE = 112
NEW ORLEANS WRONG-CITY IDENTITIES LIVE = 0
PET-FRIENDLY RECORDS WITH EXPLICIT REFUSAL = 0
QUESTION-ONLY PET-FRIENDLY RECORDS = 0
SERVICE-ANIMAL-ONLY ACCEPTANCE = 0
UNAPPROVED NEW ORLEANS PROFILES LIVE = 0
MISLEADING SINGLE FEES = 0
PRIOR MARKETS LOST = 0
PRIOR ROUTES LOST = 0
ROLLBACK REQUIRED = NO
NEW ORLEANS LIVE = YES

STOP.
