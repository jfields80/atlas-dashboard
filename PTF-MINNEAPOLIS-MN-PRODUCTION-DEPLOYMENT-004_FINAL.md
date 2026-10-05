# PTF-MINNEAPOLIS-MN-PRODUCTION-DEPLOYMENT-004 — FINAL

**Status:** MINNEAPOLIS IS LIVE. Netlify deploy **`6ac3bfda7b585d009f007620`** published 2026-10-05T15:19:28.897Z.
Production is now **42 markets / 3,975 profiles / 4,377 release-index routes / 4,452 served routes**.

The exact authorized candidate (`C:\t\msp4a\site`) was deployed **once**, with no rebuild. Rollback was **not
required**.

**Branch:** `worker/ptf-minneapolis-mn-market-001`.

**Commits:**
- **Live lineage commit `d5762303`**: the deployment record, the consumed authorization, the live manifest, the pins,
  the supersessions chain and the verification reports.
- The final commit: this report.

## 1. Predeploy parent (Phase 1)

Re-resolved immediately before the deploy (canonical resolver, Netlify `getSite` and a hash of the served sitemap, at
15:00Z):

| | |
|---|---|
| PREDEPLOY LIVE SOURCE COMMIT | `aeb57df15d916262cb700bf7ff8550c738e4ddc6` (built_from `22ff1c94`) |
| PREDEPLOY LIVE DEPLOYMENT | **`6ac264b79e70ce6a7db4baaf`** (Portland; host `published_deploy` = this id, state ready) |
| PREDEPLOY LIVE BUNDLE | `d674d2898af11565559318500650bbee1c8e59fbf0fc3ea4040dacd3a7cfecea` |
| PREDEPLOY LIVE SITEMAP | `a50f1e343949ff65122e903b39a8bc9aed6318aef0a25b265aba6da772adf360` (the served sitemap hashed to it; saved as the parent route set, 4,280 locs) |
| PREDEPLOY LIVE MARKETS / PROFILES | 41 / 3,819 |
| PREDEPLOY LIVE RELEASE-INDEX / SERVED ROUTES | 4,206 / 4,280 |
| HOST VERIFIED | YES |

## 2. Authorization and candidate integrity (Phases 2–8)

`minneapolis_mn_deployment_004.py predeploy` (`markets/reports/minneapolis_mn_predeploy_004.json`) returned **PASS**.
Every hash below was read in full from the authorization file, never from abbreviated text.

| | |
|---|---|
| DEPLOYMENT AUTHORIZATION | `ptf-auth-minneapolis-003-3d7c53a1ba2a` |
| status before | **AUTHORIZED**, CONSUMED NO, deploy_id none; market minneapolis-mn in the authorization |
| AUTHORIZED PACKAGE | `pkg-minneapolis-mn-dd62d3082411d1d5` (the readiness packet and the authorization source) |
| AUTHORIZED BUNDLE | `3d7c53a1ba2adc6ca9141e88384a7ef1e1e84abf7bdf21a4417ae664ff33af24` |
| AUTHORIZED SITEMAP | `524d9d35c96668eaff45dfeb4f95edf7659ff815c7eb2d3f69a57658723ca7a1` |
| AUTHORIZED SOURCE COMMIT | `239c28360c95adbdf4371eabcec99ede00e3270c` (the founder-decision BUILD commit) |
| AUTHORIZED PARENT / rollback | `6ac264b79e70ce6a7db4baaf`; 24,002 files; 42 / 3,975 / 4,452 |
| verify_authorization / deployability_problems / verify_target | `[]` / `[]` / `[]` (target pettripfinder-prod, site id `ecf6b5ee-45cb-…`) |
| verify_bundle_directory | `[]`: every one of the 24,002 files in `C:\t\msp4a\site`, re-hashed from disk, equals the authorization (15:00:56 → 15:13:48Z) |
| candidate manifest | `GD.build_manifest` of the bundle on disk equals the committed candidate manifest |
| determinism evidence | BYTE_IDENTICAL, 24,002 files, 0 differing (the authorization order's accounting, re-read) |
| accounting re-read | 42 / 3,975 / 4,377 / 4,452; Minneapolis 156 / 171 / 172; delta, held-content, Twin Cities pages (0 wrong), fixed identities, reader, fee and collision gates all PASS; prior files removed 0, prior-market files changed 0 |
| FAST receipt | `pkg-minneapolis-mn-dd62d3082411d1d5-eac0c8724c679c00.json`: currently eligible, J PASS, K PASS (BYTE_IDENTICAL), 0 defects |

**CANDIDATE INTEGRITY = PASS.**

## 3. Live manifest and the deploy (Phases 9–10)

- **Live manifest** `deploy/netlify/global_deployment_manifest.json`:
  - written from the exact authorized bytes immediately before the deploy;
  - `verify_manifest` `[]`;
  - byte-identical to the committed candidate manifest;
  - bundle `3d7c53a1…`, sitemap `524d9d35…`, 42 markets, 3,975 profiles, 4,452 served routes.
- **Command, run ONCE:** `netlify deploy --prod --no-build --dir C:\t\msp4a\site --site pettripfinder-prod`.

| | |
|---|---|
| DEPLOY START | 2026-10-05T15:14:10Z |
| DEPLOY COMPLETE | 2026-10-05T15:19:29Z (host `published_at` 15:19:28.897Z) |
| NETLIFY DEPLOYMENT ID | **`6ac3bfda7b585d009f007620`** |
| EXIT STATUS | 0, "Deploy is live!". The CDN diff requested 933 files (the 932 new Minneapolis files plus the regenerated sitemap) |

No Netlify build ran.

## 4. Host verification (Phases 11–14)

`minneapolis_mn_deployment_004.py verify-live` (`markets/reports/minneapolis_mn_live_verification_004.json`):
**ALL LIVE CHECKS PASS (18 / 18), ROLLBACK_REQUIRED NO.**

| check | result |
|---|---|
| HOST SITEMAP MATCH | **PASS**: the served `sitemap.xml` hashes to `524d9d35…` (the authorized sitemap), and the served route SET equals the authorized candidate's |
| host deploys | publishes `6ac3bfda…` (ready, production); previous deploy `6ac264b7` = the authorized parent |
| LIVE accounting | **42 markets / 3,975 profiles / 4,377 release-index / 4,452 served** |
| MINNEAPOLIS ROUTES | expected 172 (derived from the authorized candidate's own sitemap) → **172 / 172 HTTP 200**, 0 missing; profiles live 156; corridors live 14 |
| PRIOR ROUTES | all **4,280 / 4,280** parent routes 200; 0 lost; only Minneapolis routes added |
| byte identity | **29 / 29** sampled pages (global surfaces, the Minneapolis hub, comparison page, corridors and profiles, and 14 other market hubs) byte-identical to the artifact |
| HELD ROWS | all **102** unpublished census rows (36 held + 66 verified-no-pets) probed at census slug and site route (135 URLs): every one **404** |
| FOUNDER-HELD ROWS | the six dual-brand rows (317 2nd Ave S; 2415 E Old Shakopee Rd; 1321 E 78th St) and Microtel Inver Grove Heights: **404** at every URL |
| MINNESOTA IDENTITY | all **156** live profiles state "MN" and their own postal code; **0 wrong** |
| FIXED IDENTITIES | Ramada Plymouth **200** (published); Hotel Alma, Celeste of St. Paul, Northernaire Motel **404** (held / verified no-pets), exactly as committed |
| TIMESHARE / MILITARY | none exists in this census; none is visible |
| representative markets | Portland, Seattle, San Antonio, Austin, Phoenix, Denver, San Diego, Jacksonville FL, West Palm Beach, Fort Lauderdale, Augusta, Miami, Tampa and Orlando: **200**. Minneapolis hub: **200**. Detroit: **404** (still withheld) |
| bundle quality | broken links 0, collisions 0, global shadowing 0, canonical violations 0 |

**The parent-route sweep, and why it ran twice.** The first attempt ran as a background shell, and Claude Code stopped
it partway because the machine was critically low on memory (other applications held most of the 16 GB). It wrote no
result, and nothing was judged on it. On the operator's instruction the sweep was re-run as one detached orchestrator
executing **11 sequential batches** (400 routes each, the last 280), each persisted to disk on completion
(`C:/t/msp_prior_batches/`), between 18:55:52 and 19:09:34Z. Result: **4,280 checked, 4,280 HTTP 200, 0 lost**,
covering exactly the parent sitemap's route set. On the first pass, batch 8 had 64 client-side `000` answers (no
response), the same pattern seen in Portland, Seattle and San Antonio; all 64 returned 200 on the normal refetch. The
first-pass file is kept (`C:/t/msp_prior_sweep.txt.first`).

**Held content, reader and fee safety live** (published counts):

| | |
|---|---|
| UNAPPROVED MINNEAPOLIS PROFILES LIVE | **0** |
| DUAL-BRAND HOLDS PUBLISHED | **0 / 6** |
| MICROTEL INVER GROVE HEIGHTS PUBLISHED | **0** |
| PREOPENING | **0** (none exists) |
| TIMESHARE | **0** (none exists) |
| all unresolved rows | **0 / 36** |
| verified-no-pets as hotel profiles | **0 / 66** |
| reader | PET-FRIENDLY WITH EXPLICIT REFUSAL 0, QUESTION-ONLY 0, SERVICE-ANIMAL-ONLY ACCEPTANCE 0 (the bytes are the authorized bytes) |
| fees | MISLEADING SINGLE FEES 0. 35 single-basis fees publish; 47 tiered and 16 unsafe fees remain withheld, Hyatt Regency Bloomington's stay-length fee among them |
| clone / geography | PORTLAND COORDINATE RESIDUE 0, OREGON TEXT RESIDUE 0, PORTLAND COMMENT RESIDUE 0 (re-scanned over 35 modules by the authorization order) |
| collisions | CROSS-MARKET 0, BARE-CHAIN 0, DUPLICATE EXCLUDED IDENTITIES 0 |

## 5. Bounded postdeploy checks (Phase 15)

No broad regression was run.

| | |
|---|---|
| pin and reader tests | `contracts/test_market_state_pins.py` + `test_question_negation_reader_001.py`: **317 / 317 passed** (10.0 s, one pytest process) |
| release contracts | `verify_all()` **43 / 43** clean |
| global authority | `build_global_authority --check`: all generated artifacts match the shards |
| FAST receipt | still currently eligible; RULE J NONEMPTY PASS (953 files / 937 HTML); RULE K NONVACUOUS PASS (BYTE_IDENTICAL) |
| quality | BROKEN LINKS 0, COLLISIONS 0, CANONICAL VIOLATIONS 0, GLOBAL SHADOWING 0, UNEXPECTED DELTA `[]` |

## 6. Deployment state finalized (Phase 16)

These steps were run only after the full sweep and host verification passed:

| | |
|---|---|
| deployment record | `deploy/netlify/deployment_records/ptf-deploy-minneapolis-004-6ac3bfda7b585d009f007620.json`; `verify_record` `[]`. `work_order` = the authorizing order 003; `deployer.work_order` = this order 004 |
| authorization | `ptf-auth-minneapolis-003-3d7c53a1ba2a`: **AUTHORIZED → DEPLOYED** (status history: consumed by this order, deployment id `6ac3bfda…`, record id above). **CONSUMED = YES** |
| supersessions | chain extended 38 → **39**. `ptf-auth-minneapolis-003-3d7c53a1ba2a` is the CURRENT entry with an empty moved list. Portland's `ptf-auth-portland-003-d674d2898af1` is now historical, with drift `[]` |
| pin | `tests/pettripfinder/pins/deployment_state.json` live = `6ac3bfda…`, 42 markets, 3,975 profiles, 4,452 served, source commit `239c2836`, rollback target `6ac264b7`; live and source agree |
| participation | minneapolis-mn **FOUNDER_AUTHORIZED_FOR_LAUNCH** (live); `decision_problems` `[]` |
| canonical resolver after push | CURRENT_LIVE_SOURCE_COMMIT **`d5762303`**, built_from `239c2836`, deploy `6ac3bfda`, 42 / 3,975 / 4,377 / 4,452, host verified |
| next market | `derive_registration_base` resolves to `d5762303` |

## 7. Rollback decision (Phase 17)

**ROLLBACK REQUIRED = NO.** Every critical check passed:
- authorized bytes;
- sitemap;
- Minneapolis routes;
- prior routes and profiles;
- held rows;
- Minnesota identity;
- policy;
- collisions;
- canonical;
- accounting.

The rollback target `6ac264b79e70ce6a7db4baaf` is recorded in the deployment record and the pin. It was not used.
There was one deploy and no retry.

## 8. Final accounting (Phase 18)

| | |
|---|---:|
| LIVE MARKETS | **42** |
| LIVE PROFILES | **3,975** |
| LIVE RELEASE-INDEX ROUTES | **4,377** |
| LIVE SERVED ROUTES | **4,452** |
| MINNEAPOLIS PROFILES LIVE | **156** |
| MINNEAPOLIS RELEASE-INDEX ROUTES | **171** |
| MINNEAPOLIS SERVED ROUTES | **172** |
| PRIOR MARKETS PRESERVED | **41 / 41** |
| PRIOR PROFILES / ROUTES LOST | **0 / 0** |

No process created by this order remains: the predeploy, verify-live and sweep processes all exited on their own. The
live artifact `C:\t\msp4a` and its twin `C:\t\msp4b` are kept on disk as the rollback reference for the next market.

## FINAL ANSWERS

1. PREDEPLOY LIVE DEPLOYMENT = 6ac264b79e70ce6a7db4baaf (Portland; source aeb57df1, sitemap a50f1e34…)
2. DEPLOYMENT AUTHORIZATION = ptf-auth-minneapolis-003-3d7c53a1ba2a
3. AUTHORIZATION STATUS BEFORE = AUTHORIZED (unconsumed, no deploy id)
4. AUTHORIZED PACKAGE = pkg-minneapolis-mn-dd62d3082411d1d5
5. AUTHORIZED CANDIDATE BUNDLE = 3d7c53a1ba2adc6ca9141e88384a7ef1e1e84abf7bdf21a4417ae664ff33af24
6. AUTHORIZED CANDIDATE SITEMAP = 524d9d35c96668eaff45dfeb4f95edf7659ff815c7eb2d3f69a57658723ca7a1
7. CANDIDATE INTEGRITY = PASS (24,002 files re-hashed = authorization; BYTE_IDENTICAL twin, 0 differing)
8. NETLIFY DEPLOYMENT ID = 6ac3bfda7b585d009f007620
9. NETLIFY RESULT = SUCCESS (exit 0, "Deploy is live!", 15:14:10Z → 15:19:29Z, one call, no build)
10. HOST SITEMAP MATCH = PASS (served sitemap = 524d9d35…, route set identical)
11. LIVE MARKETS = 42
12. LIVE PROFILES = 3975
13. LIVE RELEASE-INDEX ROUTES = 4377
14. LIVE SERVED ROUTES = 4452
15. MINNEAPOLIS PROFILES LIVE = 156
16. MINNEAPOLIS RELEASE-INDEX ROUTES = 171
17. MINNEAPOLIS SERVED ROUTES = 172
18. MINNEAPOLIS ROUTES HTTP 200 = 172 / 172
19. DUAL-BRAND HOLDS PUBLISHED = 0 / 6
20. MICROTEL INVER GROVE HEIGHTS PUBLISHED = 0
21. PREOPENING PROFILES PUBLISHED = 0
22. TIMESHARE PROFILES PUBLISHED = 0
23. UNAPPROVED MINNEAPOLIS PROFILES LIVE = 0
24. PET-FRIENDLY WITH EXPLICIT REFUSAL = 0
25. QUESTION-ONLY PET-FRIENDLY = 0
26. SERVICE-ANIMAL-ONLY ACCEPTANCE = 0
27. MISLEADING SINGLE FEES = 0
28. PORTLAND COORDINATE RESIDUE = 0
29. OREGON TEXT RESIDUE = 0
30. PRIOR MARKETS LOST = 0
31. PRIOR PROFILES LOST = 0
32. PRIOR ROUTES LOST = 0 (4,280 / 4,280 parent routes 200)
33. DETROIT STILL WITHHELD = YES (404)
34. RULE J NONEMPTY = PASS (953 files / 937 HTML)
35. RULE K NONVACUOUS = PASS (BYTE_IDENTICAL)
36. BROKEN LINKS = 0
37. COLLISIONS = 0
38. CANONICAL VIOLATIONS = 0
39. GLOBAL SHADOWING = 0
40. UNEXPECTED DELTA = [] (market, profile, route, served route)
41. DEPLOYMENT AUTHORIZATION CONSUMED = YES (AUTHORIZED → DEPLOYED, record ptf-deploy-minneapolis-004-6ac3bfda7b585d009f007620)
42. MINNEAPOLIS PARTICIPATION = FOUNDER_AUTHORIZED_FOR_LAUNCH (live)
43. ROLLBACK REQUIRED = NO
44. CURRENT LIVE DEPLOYMENT = 6ac3bfda7b585d009f007620 (lineage d5762303, built_from 239c2836)
45. origin == HEAD = YES (verified after push)
46. tree clean = YES (verified after push)
47. MINNEAPOLIS LIVE = YES

```
MINNEAPOLIS PRODUCTION DEPLOYMENT = PASS
LIVE MARKETS = 42
LIVE PROFILES = 3975
LIVE SERVED ROUTES = 4452
MINNEAPOLIS PROFILES LIVE = 156
MINNEAPOLIS ROUTES LIVE = 172
PET-FRIENDLY RECORDS WITH EXPLICIT REFUSAL = 0
QUESTION-ONLY PET-FRIENDLY RECORDS = 0
SERVICE-ANIMAL-ONLY ACCEPTANCE = 0
UNAPPROVED MINNEAPOLIS PROFILES LIVE = 0
MISLEADING SINGLE FEES = 0
PRIOR MARKETS LOST = 0
PRIOR ROUTES LOST = 0
ROLLBACK REQUIRED = NO
MINNEAPOLIS LIVE = YES
```

STOP.
