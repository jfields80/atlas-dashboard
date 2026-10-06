# PTF-KANSAS-CITY-MO-PRODUCTION-DEPLOYMENT-004 — FINAL

**Status:** KANSAS CITY IS LIVE. Netlify deploy **`6ac4dc8a39b0e7274828a32b`** published 2026-10-06T11:34:08.924Z.
Production is now **43 markets / 4,136 profiles / 4,552 release-index routes / 4,628 served routes**. Rollback was
not required.

**Branch:** `worker/ptf-kansas-city-mo-market-001`. **Live lineage commit:** `117afe11` (the deployment state; the
resolver now names it CURRENT_LIVE_SOURCE_COMMIT, built_from `c6609370`). Final commit: this report.

## 1. Predeploy parent (Phase 1)

Re-resolved immediately before the deploy (canonical resolver, Netlify `getSite`, hash of the served sitemap, 11:16Z):

| | |
|---|---|
| PREDEPLOY LIVE SOURCE COMMIT | `d57623030b95f153ec3fc82c7149c5960efc6625` (built_from `239c2836`) |
| PREDEPLOY LIVE DEPLOYMENT | **`6ac3bfda7b585d009f007620`** (Minneapolis; host `published_deploy` = this id, state ready) |
| PREDEPLOY LIVE BUNDLE | `3d7c53a1ba2adc6ca9141e88384a7ef1e1e84abf7bdf21a4417ae664ff33af24` |
| PREDEPLOY LIVE SITEMAP | `524d9d35c96668eaff45dfeb4f95edf7659ff815c7eb2d3f69a57658723ca7a1` (served sitemap hashed to it; byte-identical to the live artifact `C:/t/msp4a`; saved as the parent route set, 4,452 locs) |
| PREDEPLOY LIVE MARKETS / PROFILES | 42 / 3,975 |
| PREDEPLOY LIVE RELEASE-INDEX / SERVED ROUTES | 4,377 / 4,452 |
| HOST VERIFIED | YES |

## 2. Authorization and candidate integrity (Phases 2–8)

`kansas_city_mo_deployment_004.py predeploy` (`markets/reports/kansas_city_mo_predeploy_004.json`): **PASS**.

| | |
|---|---|
| DEPLOYMENT AUTHORIZATION | `ptf-auth-kansas-city-003-6a35c23829f9` |
| status before | **AUTHORIZED**, CONSUMED NO, deploy_id none; kansas-city-mo in the authorization |
| AUTHORIZED PACKAGE | `pkg-kansas-city-mo-140e35291a2195c3` (readiness packet and authorization source) |
| AUTHORIZED BUNDLE | `6a35c23829f9c0a0a1713acc721f3fcf317a94d7f57120379ffc951fdc60ed5f` |
| AUTHORIZED SITEMAP | `3d5d9425a4e0a90b6aca13f3d02866a815ebc934df8382e4fcf03c0ecc10967b` |
| AUTHORIZED SOURCE COMMIT | `c6609370ec22ac74bd1c8cd881d25ee147ce3d0c` (the founder-decision BUILD commit) |
| AUTHORIZED PARENT / rollback | `6ac3bfda7b585d009f007620`; 24,957 files; 43 / 4,136 / 4,628 |
| verify_authorization / deployability_problems / verify_target | `[]` / `[]` / `[]` (target pettripfinder-prod) |
| verify_bundle_directory | `[]` — every one of the 24,957 files in `C:\t\kc4a\site`, re-hashed from disk, equals the authorization (11:16:49 → 11:30:21Z) |
| candidate manifest | `GD.build_manifest` of the bundle on disk equals the committed candidate manifest |
| determinism evidence | BYTE_IDENTICAL, 24,957 files, 0 differing (the authorization order's accounting, re-read) |
| accounting re-read | 43 / 4,136 / 4,552 / 4,628; Kansas City 161 / 175 / 176; held content, two-state pages (96 MO / 65 KS, 0 wrong), other-market text 0, fixed identities, reader, fee and collision gates all PASS; prior files removed 0, prior-market files changed 0 |
| FAST receipt | `pkg-kansas-city-mo-140e35291a2195c3-b0245f8a1e4420b7`: currently eligible, J PASS, K PASS (BYTE_IDENTICAL), 0 defects |

**CANDIDATE INTEGRITY = PASS.** Nothing was rebuilt or resealed.

## 3. Live manifest and the deploy (Phases 9–10)

- **Live manifest** `deploy/netlify/global_deployment_manifest.json` written from the exact authorized bytes immediately
  before the deploy: `verify_manifest []`; byte-identical to the committed candidate manifest; bundle `6a35c238…`,
  sitemap `3d5d9425…`, 43 markets, 4,136 profiles, 4,628 served routes.
- **Command, run ONCE:** `netlify deploy --prod --no-build --dir C:\t\kc4a\site --site pettripfinder-prod`.

| | |
|---|---|
| DEPLOY START | 2026-10-06T11:30:47Z |
| DEPLOY COMPLETE | 2026-10-06T11:34:08Z (host `published_at` 11:34:08.924Z) |
| NETLIFY DEPLOYMENT ID | **`6ac4dc8a39b0e7274828a32b`** |
| EXIT STATUS | 0, "Deploy is live!". The CDN diff requested 957 files (the 955 new Kansas City files and the regenerated sitemap account for 956; the host's own diff picked one more, and the served bytes of every sampled page and the full served route set match the authorized candidate) |

No Netlify build ran.

## 4. Host verification (Phases 11–15)

`kansas_city_mo_deployment_004.py verify-live` (`markets/reports/kansas_city_mo_live_verification_004.json`):
**ALL LIVE CHECKS PASS (19 / 19), ROLLBACK_REQUIRED NO.**

| check | result |
|---|---|
| HOST SITEMAP MATCH | **PASS** — the served `sitemap.xml` hashes to `3d5d9425…`, and the served route SET equals the authorized candidate's |
| host deploys | publishes `6ac4dc8a…` (ready, production); previous deploy `6ac3bfda` = the authorized parent |
| LIVE accounting | **43 markets / 4,136 profiles / 4,552 release-index / 4,628 served** |
| KANSAS CITY ROUTES | expected 176 (derived from the authorized candidate's own sitemap) → **176 / 176 HTTP 200**, 0 missing; profiles live 161; 13 corridors live |
| PRIOR ROUTES | all **4,452 / 4,452** parent routes 200; 0 lost; only Kansas City routes added |
| byte identity | **30 / 30** sampled pages (global surfaces, the Kansas City hub, comparison page, corridors and profiles, and 15 other market hubs) byte-identical to the artifact |
| HELD ROWS | all **129** unpublished census rows (69 held + 60 verified-no-pets) probed at census slug and site route (163 URLs): every one **404** |
| FOUNDER-HELD ROWS | the 6 dual-brand rows (1875 Diamond Pkwy; 8710 Penrose Ln; 1535 Baltimore Ave), ESA Tiffany Springs, the Crossland identity and the 4 preopening hotels: **404** at every URL |
| REBRAND HOLDS | Hilton Garden Inn Overland Park and Sleep Inn Olathe (never admitted): **404** |
| TWO STATES | all **161** live profiles' own structured address states their state, ZIP and city: **96 Missouri, 65 Kansas**, KS→MO **0**, MO→KS **0**, wrong state / ZIP / city **0** |
| CROSS-STATE NAME TRAPS | Sonesta Select "South Overland Park" (64131 MO), ESA "Shawnee Mission" (66202 KS), Drury "Independence" (64015 MO) **200**; Hotel Lotus Merriam (66203 KS, held) **404** — exactly as committed |
| TIMESHARE / MILITARY | WorldMark Lake of the Ozarks, Holiday Inn Express at Hoge Hall, IHG Army Hotels Foster Lodge: **404**, named on no Kansas City page |
| representative markets | Minneapolis, Portland, Seattle, San Antonio, Austin, Phoenix, Denver, San Diego, Jacksonville FL, West Palm Beach, Fort Lauderdale, Augusta, Miami, Tampa, Orlando **200**; Kansas City hub **200**; Detroit **404** (still withheld) |
| bundle quality | broken links 0, collisions 0, global shadowing 0, canonical violations 0 |

**The parent-route sweep.** Run as one detached orchestrator of sequential 400-route batches (12 batches), each
persisted to `C:/t/kc_prior_batches/` by atomic rename, 11:34:30 → 11:45:56Z. Batch 10 overlapped a short window in
which this machine got no answers from the host (curl to pettripfinder.com timed out at 20 s while Google, Netlify and
the deploy's own unique URL answered in under 0.5 s; it cleared within minutes). That batch had 28 no-response (`000`)
answers on the first pass and 12 still `000` after the in-batch retry, which fell in the same window — one contiguous
block of Seattle routes. All 12 returned **200** on the normal refetch afterwards. No route was lost; the first-pass file
is kept (`C:/t/kc_prior_sweep.txt.first`). Final: **4,452 checked, 4,452 HTTP 200**.

**Held content, reader and fee safety live:**

| | |
|---|---|
| UNAPPROVED KANSAS CITY PROFILES LIVE | **0** |
| DUAL-BRAND HOLDS PUBLISHED | **0 / 6** |
| HGI OVERLAND PARK / SLEEP INN OLATHE REBRAND HOLDS | **0 / 0** |
| ESA TIFFANY SPRINGS / CROSSLAND IDENTITY | **0 / 0** |
| PREOPENING | **0 / 4** |
| TIMESHARE | **0** |
| all unresolved rows | **0 / 69** |
| verified-no-pets as hotel profiles | **0 / 60** |
| reader | PET-FRIENDLY WITH EXPLICIT REFUSAL 0, QUESTION-ONLY 0, SERVICE-ANIMAL-ONLY ACCEPTANCE 0 (the served bytes are the authorized bytes) |
| fees | MISLEADING SINGLE FEES 0; 25 single-basis fees publish; 37 tiered and 17 unsafe fees remain withheld |
| collisions | CROSS-MARKET 0, BARE-CHAIN 0, DUPLICATE EXCLUDED IDENTITIES 0 |

## 5. Bounded postdeploy checks (Phase 16)

No broad regression was run.

| | |
|---|---|
| pin and reader tests | `contracts/test_market_state_pins.py` + `test_question_negation_reader_001.py`: **322 / 322 passed** (7.5 s, one pytest process, run on the finalized state) |
| release contracts | `verify_all()` **44 / 44** clean |
| global authority | `build_global_authority --check`: all generated artifacts match the shards |
| FAST receipt | still currently eligible (the only receipt selected); RULE J NONEMPTY PASS (976 files / 960 HTML); RULE K NONVACUOUS PASS (BYTE_IDENTICAL) |
| quality | BROKEN LINKS 0, COLLISIONS 0, CANONICAL VIOLATIONS 0, GLOBAL SHADOWING 0, UNEXPECTED DELTA `[]` |

## 6. Deployment state finalized (Phase 17)

Written only after all 176 Kansas City routes, all 4,452 parent routes and the host verification passed:

| | |
|---|---|
| authorization | `ptf-auth-kansas-city-003-6a35c23829f9`: AUTHORIZED → **DEPLOYED**, CONSUMED YES (consumed_by PTF-KANSAS-CITY-MO-PRODUCTION-DEPLOYMENT-004, deployment `6ac4dc8a…`) |
| deployment record | `ptf-deploy-kansas-city-004-6ac4dc8a39b0e7274828a32b`: `work_order` = the authorizing 003, `deployer.work_order` = this 004 (with `authorizing_work_order`), `verify_record []` |
| supersessions | `ptf-auth-minneapolis-003-3d7c53a1ba2a` marked Historical (moved list `[]`, verified by re-hashing its release contracts); `ptf-auth-kansas-city-003-6a35c23829f9` appended as the CURRENT entry with an empty moved list; `reviewed_by` this order |
| pin | `tests/pettripfinder/pins/deployment_state.json` live = `6ac4dc8a…`, 43 markets, 4,136 profiles, 4,628 served, source commit `c6609370`, rollback target `6ac3bfda`; live and source agree |
| participation | kansas-city-mo stays FOUNDER_AUTHORIZED_FOR_LAUNCH (the live state); `decision_problems []` |
| lineage | the resolver now returns CURRENT_LIVE_SOURCE_COMMIT `117afe11` (built_from `c6609370`); `derive_registration_base` returns `117afe11` for the next market |

## 7. Rollback decision (Phase 18)

**ROLLBACK REQUIRED: NO.** No authorized-byte mismatch, sitemap mismatch, Kansas City route loss, parent route loss,
prior profile loss, held-profile publication, KS/MO corruption, reader contradiction, collision, canonical violation or
accounting mismatch was found. Rollback target `6ac3bfda7b585d009f007620` was not used.

## 8. Final accounting (Phase 19)

| | |
|---|---:|
| LIVE MARKETS | **43** |
| LIVE PROFILES | **4,136** |
| LIVE RELEASE-INDEX ROUTES | **4,552** |
| LIVE SERVED ROUTES | **4,628** |
| KANSAS CITY PROFILES LIVE | **161** (96 MO, 65 KS) |
| KANSAS CITY RELEASE-INDEX ROUTES | **175** |
| KANSAS CITY SERVED ROUTES | **176** |
| PRIOR MARKETS PRESERVED | **42 / 42** |
| PRIOR PROFILES LOST / PRIOR ROUTES LOST | **0 / 0** |

Processes: predeploy, the sweep orchestrator and verify-live all exited on their own; no process created by this order
remains (python 14180 predates it and was left alone). Live artifact for the next deploy's byte comparison:
`C:/t/kc4a` (twin `C:/t/kc4b`).
