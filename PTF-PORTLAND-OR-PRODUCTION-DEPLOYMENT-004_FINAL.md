# PTF-PORTLAND-OR-PRODUCTION-DEPLOYMENT-004 — FINAL

**Status:** PORTLAND IS LIVE. Netlify deploy **`6ac264b79e70ce6a7db4baaf`** published 2026-10-04T14:38:20Z. Production is
now **41 markets / 3,819 profiles / 4,206 release-index routes / 4,280 served routes**.

The exact authorized candidate (`C:\t\pdx4a\site`) was deployed **once**, with no rebuild. Rollback was **not
required**.

**Branch:** `worker/ptf-portland-or-market-001`.

**Commits:**
- **Live lineage commit `aeb57df1`**: the deployment record, the consumed authorization, the live manifest, the pins
  and the verification reports.
- The final commit: this report.

## 1. Predeploy parent (Phase 1)

Re-resolved immediately before the deploy. Canonical resolver at 14:23Z, Netlify `getSite` and a sitemap hash just
before the call:

| | |
|---|---|
| PREDEPLOY LIVE SOURCE COMMIT | `f0003e78b10d249774d376cc6bc2457d57cf63ce` (built_from `438348c7`) |
| PREDEPLOY LIVE DEPLOYMENT | **`6ac169ef7c75c383eb79f824`** (Seattle; host `published_deploy` = this id, state ready) |
| PREDEPLOY LIVE BUNDLE | `cfaad64a7bcb1b2b1734fe777ea577d5884aafe953054c2d80a7db1b01e0e5c3` |
| PREDEPLOY LIVE SITEMAP | `63e052812b36668271aebb3f8bc933a44ac0d6150b7b8c19279d5f1e45a2b151` (the served sitemap hashed to it; saved as the parent route set, 4,117 locs) |
| PREDEPLOY LIVE MARKETS / PROFILES | 40 / 3,669 |
| PREDEPLOY LIVE RELEASE-INDEX / SERVED ROUTES | 4,044 / 4,117 |
| HOST VERIFIED | YES |

## 2. Authorization and candidate integrity (Phases 2–8)

`portland_or_deployment_004.py predeploy` (`markets/reports/portland_or_predeploy_004.json`) returned **PASS**.

| | |
|---|---|
| DEPLOYMENT AUTHORIZATION | `ptf-auth-portland-003-d674d2898af1` |
| status before | **AUTHORIZED**, CONSUMED NO, deploy_id none; market portland-or in the authorization |
| bindings | package `pkg-portland-or-5b6016fb253bc7a7` (the readiness packet and the authorization source); bundle `d674d289…`; sitemap `a50f1e34…`; source commit `22ff1c94`; parent / rollback `6ac169ef`; 23,070 files; 41 / 3,819 / 4,280 |
| verify_authorization / deployability_problems / verify_target | `[]` / `[]` / `[]` (target pettripfinder-prod, site id `ecf6b5ee-45cb-…`) |
| verify_bundle_directory | `[]`: every one of the 23,070 files in `C:\t\pdx4a\site` re-hashed from disk equals the authorization |
| candidate manifest | `GD.build_manifest` of the bundle on disk equals the committed candidate manifest |
| determinism evidence | BYTE_IDENTICAL, 23,070 files, 0 differing (the authorization order's accounting, re-read) |
| accounting re-read | 41 / 3,819 / 4,206 / 4,280; Portland 150 / 162 / 163; delta, held-content, Vancouver (0 wrong-state), reader, fee and collision gates all PASS; prior files removed 0, prior-market files changed 0 |
| FAST receipt | `pkg-portland-or-5b6016fb253bc7a7-df634e23cb809eb7.json`: currently eligible, J PASS, K PASS (BYTE_IDENTICAL), 0 defects |

## 3. Live manifest and the deploy (Phases 9–10)

- **Live manifest** `deploy/netlify/global_deployment_manifest.json`:
  - written from the exact authorized bytes immediately before the deploy;
  - `verify_manifest` `[]`;
  - identical to the committed candidate manifest;
  - bundle `d674d289…`, sitemap `a50f1e34…`, 41 markets, 3,819 profiles, 4,280 served routes.
- **Command, run ONCE:** `netlify deploy --prod --no-build --dir C:\t\pdx4a\site --site pettripfinder-prod`.

| | |
|---|---|
| DEPLOY START | 2026-10-04T14:35:17Z |
| DEPLOY COMPLETE | 2026-10-04T14:38:20Z (host `published_at` 14:38:20.664Z) |
| NETLIFY DEPLOYMENT ID | **`6ac264b79e70ce6a7db4baaf`** |
| EXIT STATUS | 0. The CDN diff requested 889 files (the 887 new Portland files plus regenerated global files) |

No Netlify build ran.

## 4. Host verification (Phases 11–15)

`portland_or_deployment_004.py verify-live` (`markets/reports/portland_or_live_verification_004.json`):
**ALL LIVE CHECKS PASS (17 / 17), ROLLBACK_REQUIRED NO.**

| check | result |
|---|---|
| HOST SITEMAP MATCH | **PASS**: the served `sitemap.xml` hashes to `a50f1e34…`, and the served route SET equals the authorized candidate's |
| host deploys | publishes `6ac264b7…` (ready, production); previous deploy `6ac169ef` = the authorized parent |
| LIVE accounting | **41 markets / 3,819 profiles / 4,206 release-index / 4,280 served** |
| PORTLAND ROUTES | expected 163 (derived from the candidate's own sitemap) → **163 / 163 HTTP 200**, 0 missing; profiles live 150; corridors live 11 |
| PRIOR ROUTES | all **4,117 / 4,117** parent routes 200; 0 lost; only Portland routes added |
| byte identity | **28 / 28** sampled pages (global surfaces, Portland hub, comparison, corridors, profiles, and 12 other market hubs) byte-identical to the artifact |
| HELD ROWS | all **122** unpublished census rows (75 held + 47 verified-no-pets) probed at census slug and site route (140 URLs): every one **404** |
| SHARED CAMPUS | Hyatt House Portland Airport, The Mindaro and the bureau's name-only Mindaro row: **404** (outside the partition, probed explicitly) |
| TIMESHARE | WorldMark Portland – Waterfront Park, WorldMark Gleneden, WorldMark Seaside: 404, named on no Portland page |
| VANCOUVER WA | corridor `/pet-friendly-hotels/portland-or/vancouver-wa/` live. All **21** live Vancouver profiles state "WA" and their own 98xxx ZIP; none says "Vancouver, OR". **0 wrong-state** |
| representative markets | Seattle, San Antonio, Austin, Phoenix, Denver, San Diego, Jacksonville FL, West Palm Beach, Fort Lauderdale, Augusta, Miami, Tampa and Orlando: **200**. Detroit: **404** (still withheld) |
| bundle quality | broken links 0, collisions 0, global shadowing 0, canonical violations 0 |

**Sweep notes.** On the first pass of the parent-route sweep, 127 requests returned the client-side `000` (no
response). The same pattern was seen in Seattle and San Antonio. All 127 returned 200 on refetch. The first-pass
file is kept beside the merged result (`C:/t/pdx_prior_sweep.txt.first`); no judgement was made on a gap.

**Held content, reader and fee safety live** (published counts):

| | |
|---|---|
| UNAPPROVED PORTLAND PROFILES LIVE | **0** |
| WORLDMARK PORTLAND | **0** |
| HYATT HOUSE PORTLAND AIRPORT / THE MINDARO | **0 / 0** |
| PREOPENING | **0** (none exist) |
| TIMESHARE | **0** |
| AFFILIATE-TEMPLATE ROWS (Cameo, Portland INN, Bridgeway) | **0**: they 404 with the held rows |
| SELF-CONTRADICTORY ROWS (Dunes Motel, Hampton Inn Portland East) | **0** |
| verified-no-pets as hotel profiles | 0 / 47 |
| reader | PET-FRIENDLY WITH EXPLICIT REFUSAL 0, QUESTION-ONLY 0, SERVICE-ANIMAL-ONLY ACCEPTANCE 0 |
| fees | MISLEADING SINGLE FEES 0; 33 tiered and 20 unsafe / multi-amount fees remain withheld (the bytes are the authorized bytes) |
| collisions | CROSS-MARKET 0, BARE-CHAIN 0, DUPLICATE EXCLUDED IDENTITIES 0 |

## 5. Bounded postdeploy checks (Phase 16)

No broad regression was run.

| | |
|---|---|
| pin and reader tests | `contracts/test_market_state_pins.py` + `test_question_negation_reader_001.py`: **312 / 312 passed** (8.2 s) |
| release contracts | `verify_all()` **42 / 42** clean |
| global authority | `build_global_authority --check`: all generated artifacts match the shards |
| FAST receipt | still currently eligible; RULE J NONEMPTY PASS (908 files / 892 HTML); RULE K NONVACUOUS PASS |
| quality | BROKEN LINKS 0, COLLISIONS 0, CANONICAL VIOLATIONS 0, GLOBAL SHADOWING 0, UNEXPECTED DELTA `[]` |

## 6. Deployment state finalized (Phase 17)

These steps were run only after host verification passed:

| | |
|---|---|
| deployment record | `deploy/netlify/deployment_records/ptf-deploy-portland-004-6ac264b79e70ce6a7db4baaf.json`; `verify_record` `[]`. `work_order` = the authorizing order 003; `deployer.work_order` = this order 004 |
| authorization | `ptf-auth-portland-003-d674d2898af1`: **AUTHORIZED → DEPLOYED** (consumed by this order, deployment id `6ac264b7…`). **CONSUMED = YES** |
| supersessions | chain extended 37 → **38**. `ptf-auth-portland-003-d674d2898af1` is the CURRENT entry with an empty moved list. Seattle's `ptf-auth-seattle-003-cfaad64a7bcb` is now historical, with drift `[]` |
| pin | `tests/pettripfinder/pins/deployment_state.json` live = `6ac264b7…`, 41 markets, 3,819 profiles, 4,280 served, source commit `22ff1c94`, rollback target `6ac169ef`; live and source agree |
| participation | portland-or **FOUNDER_AUTHORIZED_FOR_LAUNCH** (live) |
| canonical resolver after push | CURRENT_LIVE_SOURCE_COMMIT **`aeb57df1`**, built_from `22ff1c94`, deploy `6ac264b7`, 41 / 3,819 / 4,280, host verified |
| next market | `derive_registration_base` resolves to `aeb57df1` |

## 7. Rollback decision (Phase 18)

**ROLLBACK REQUIRED = NO.** Every critical check passed:
- authorized bytes;
- sitemap;
- Portland routes;
- prior routes and profiles;
- held rows;
- Vancouver state;
- policy;
- collisions;
- canonical;
- accounting.

The rollback target `6ac169ef7c75c383eb79f824` is recorded in the deployment record and the pin. It was not used.
There was one deploy and no retry.

## 8. Final accounting (Phase 19)

| | |
|---|---:|
| LIVE MARKETS | **41** |
| LIVE PROFILES | **3,819** |
| LIVE RELEASE-INDEX ROUTES | **4,206** |
| LIVE SERVED ROUTES | **4,280** |
| PORTLAND PROFILES LIVE | **150** |
| PORTLAND RELEASE-INDEX ROUTES | **162** |
| PORTLAND SERVED ROUTES | **163** |
| PRIOR MARKETS PRESERVED | **40 / 40** |
| PRIOR PROFILES / ROUTES LOST | **0 / 0** |

Artifacts on disk:
- the live artifact is `C:\t\pdx4a` (its twin is `C:\t\pdx4b`), the byte-compare base for the next market;
- the Seattle artifact `C:\t\sea4a` is the rollback artifact.

No process created by this order remains.

## FINAL ANSWERS

1. PREDEPLOY LIVE DEPLOYMENT = 6ac169ef7c75c383eb79f824 (Seattle; source f0003e78, sitemap 63e05281…)
2. DEPLOYMENT AUTHORIZATION = ptf-auth-portland-003-d674d2898af1
3. AUTHORIZATION STATUS BEFORE = AUTHORIZED (unconsumed, no deploy id)
4. AUTHORIZED PACKAGE = pkg-portland-or-5b6016fb253bc7a7
5. AUTHORIZED CANDIDATE BUNDLE = d674d2898af11565559318500650bbee1c8e59fbf0fc3ea4040dacd3a7cfecea
6. AUTHORIZED CANDIDATE SITEMAP = a50f1e343949ff65122e903b39a8bc9aed6318aef0a25b265aba6da772adf360
7. CANDIDATE INTEGRITY = PASS (verify_bundle_directory [], 23,070 files re-hashed; manifest = committed candidate manifest)
8. NETLIFY DEPLOYMENT ID = 6ac264b79e70ce6a7db4baaf
9. NETLIFY RESULT = SUCCESS (exit 0, "Deploy is live!", 14:35:17Z → 14:38:20Z, one call, no build)
10. HOST SITEMAP MATCH = PASS (a50f1e34…; served route set = authorized)
11. LIVE MARKETS = 41
12. LIVE PROFILES = 3819
13. LIVE RELEASE-INDEX ROUTES = 4206
14. LIVE SERVED ROUTES = 4280
15. PORTLAND PROFILES LIVE = 150
16. PORTLAND RELEASE-INDEX ROUTES = 162
17. PORTLAND SERVED ROUTES = 163
18. PORTLAND ROUTES HTTP 200 = 163 / 163
19. WORLDMARK PORTLAND PUBLISHED = 0
20. HYATT HOUSE PORTLAND AIRPORT PUBLISHED = 0
21. THE MINDARO PUBLISHED = 0
22. PREOPENING PROFILES PUBLISHED = 0
23. TIMESHARE / VACATION-OWNERSHIP PROFILES PUBLISHED = 0
24. UNAPPROVED PORTLAND PROFILES LIVE = 0
25. VANCOUVER WA CORRIDOR PRESENT = YES
26. VANCOUVER WA WRONG-STATE PROFILES LIVE = 0 (21 / 21 Vancouver profiles state WA and their own ZIP)
27. PET-FRIENDLY WITH EXPLICIT REFUSAL = 0
28. QUESTION-ONLY PET-FRIENDLY = 0
29. MISLEADING SINGLE FEES = 0
30. PRIOR MARKETS LOST = 0
31. PRIOR PROFILES LOST = 0
32. PRIOR ROUTES LOST = 0 (4,117 / 4,117 parent routes 200)
33. DETROIT STILL WITHHELD = YES (404)
34. RULE J NONEMPTY = PASS
35. RULE K NONVACUOUS = PASS
36. BROKEN LINKS = 0
37. COLLISIONS = 0
38. CANONICAL VIOLATIONS = 0
39. GLOBAL SHADOWING = 0
40. UNEXPECTED DELTA = []
41. DEPLOYMENT AUTHORIZATION CONSUMED = YES (AUTHORIZED → DEPLOYED, deployment 6ac264b7…)
42. PORTLAND PARTICIPATION = FOUNDER_AUTHORIZED_FOR_LAUNCH (live)
43. ROLLBACK REQUIRED = NO
44. CURRENT LIVE DEPLOYMENT = 6ac264b79e70ce6a7db4baaf (lineage aeb57df1, built_from 22ff1c94)
45. origin == HEAD = YES (verified after push)
46. tree clean = YES (verified after push)
47. PORTLAND LIVE = YES

```
PORTLAND PRODUCTION DEPLOYMENT = PASS
LIVE MARKETS = 41
LIVE PROFILES = 3819
LIVE SERVED ROUTES = 4280
PORTLAND PROFILES LIVE = 150
PORTLAND ROUTES LIVE = 163
VANCOUVER WA WRONG-STATE PROFILES LIVE = 0
PET-FRIENDLY RECORDS WITH EXPLICIT REFUSAL = 0
QUESTION-ONLY PET-FRIENDLY RECORDS = 0
UNAPPROVED PORTLAND PROFILES LIVE = 0
MISLEADING SINGLE FEES = 0
PRIOR MARKETS LOST = 0
PRIOR ROUTES LOST = 0
ROLLBACK REQUIRED = NO
PORTLAND LIVE = YES
```
