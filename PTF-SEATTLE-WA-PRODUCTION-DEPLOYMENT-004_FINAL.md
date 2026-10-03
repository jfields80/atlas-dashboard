# PTF-SEATTLE-WA-PRODUCTION-DEPLOYMENT-004 — FINAL

**SEATTLE IS LIVE.** Deploy **`6ac169ef7c75c383eb79f824`** (published 2026-10-03T20:48:15Z) serves:
- **40 markets / 3,669 profiles / 4,044 release-index routes / 4,117 served routes**;
- Seattle / Bellevue / Puget Sound as the fortieth market and the first in Washington.

The rollback target is `6ac064cd6a4261e60054a2f3` (San Antonio). **Rollback was not required.**

The exact, already-built, founder-authorized candidate was deployed ONCE. There was:
- no rebuild, reseal or re-registration;
- no re-authorization or second whole-site assembly;
- no broad regression.

Branch `worker/ptf-seattle-wa-market-001`. Commits:
- `f0003e78`: SEATTLE IS LIVE (record, consumed authorization, live manifest, supersessions, pins). This is now the
  live lineage commit.
- Then this report.

## 1. Parent, re-verified immediately before deploying (Phase 1)

| | |
|---|---|
| PREDEPLOY LIVE SOURCE COMMIT | `606839025c4c13c25d4d03984c7d5c049d27c73f` (built from `be83dab2`) |
| PREDEPLOY LIVE DEPLOYMENT | `6ac064cd6a4261e60054a2f3` (San Antonio) |
| PREDEPLOY LIVE BUNDLE / SITEMAP | `50b1ce95d80386ed…` / `e2a6b1c94dff6f91…` (served sitemap re-hashed, equal) |
| accounting | 39 markets / 3,530 profiles / 3,894 release-index / 3,966 served; host verified |
| Netlify `getSite` | `pettripfinder-prod`, published `6ac064cd`, **ready** |
| baseline sweep | 3,966 / 3,966 parent routes 200 (24 client-side `000` gaps in one contiguous block, all 200 on refetch) |

The parent had not advanced.

## 2. Authorization and exact bytes (Phases 2–7)

`seattle_wa_deployment_004.py predeploy` produced `markets/reports/seattle_wa_predeploy_004.json` with
**PREDEPLOY PASS**.

**Authorization `ptf-auth-seattle-003-cfaad64a7bcb`, before the deploy:**
- **AUTHORIZED**, deploy_id none, consumed NO.
- It names seattle-wa and `pkg-seattle-wa-784f0147e1220f40` (via the readiness packet and the authorization
  source).
- It binds bundle `cfaad64a…`, sitemap `63e05281…`, parent `6ac064cd` and source commit `438348c7`.
- `verify_authorization` `[]`, `deployability_problems` `[]`, `verify_target` `[]`.

**Exact prebuilt bytes:** `verify_bundle_directory(C:\t\sea4a\site)` `[]`.
- Re-hashed from disk, not rebuilt: bundle `cfaad64a7bcb1b2b1734fe777ea577d5884aafe953054c2d80a7db1b01e0e5c3`,
  sitemap `63e052812b36668271aebb3f8bc933a44ac0d6150b7b8c19279d5f1e45a2b151`, **22,183 files**.
- The authorization order's twin build `C:\t\sea4b` is byte-identical: 22,183 files, 0 differing.
- **CANDIDATE INTEGRITY = PASS.**

**Re-read from the authorization order's accounting:**
- **Totals:** 40 / 3,669 / 4,044 / 4,117; Seattle 139 / 150 / 151.
- **Delta:** 0 prior files removed or changed, and only `sitemap.xml` changed globally. Unexpected served-route delta
  `[]`. Parent markets, routes and profiles preserved.
- **Held content:**
  - unapproved profiles 0;
  - dual-brand 0/4, Hotel Interurban 0, Courtyard Northgate 0, FairBridge Tukwila 0, Motel 6 Suites Kent 0;
  - preopening 0, timeshare 0, military 0;
  - verified-no-pets as profiles 0/61.
- **Reader and fees:** explicit refusal 0, question-only 0, service-animal-only 0, misleading fees 0.
- **Collisions:** collision-safe PASS, bare-chain collisions 0, duplicate excluded identities 0.

**FAST receipt** `…-60013188aa5aff14.json`: currently eligible; J PASS (non-empty), K PASS (BYTE_IDENTICAL).

## 3. Live manifest (Phase 8)

`write-manifest` built the canonical live `deploy/netlify/global_deployment_manifest.json` from the exact
authorized bytes, immediately before the deploy:
- `verify_manifest` `[]`;
- **identical** to the committed candidate manifest;
- bundle `cfaad64a…`, sitemap `63e05281…`, 40 markets, 3,669 profiles, 4,117 served routes.

No candidate byte was altered.

## 4. The deployment (Phase 9)

```
netlify deploy --prod --no-build --dir C:\t\sea4a\site --site pettripfinder-prod
DEPLOY START    2026-10-03T20:47:14Z
DEPLOY COMPLETE 2026-10-03T20:48:16Z   (62 s; CDN requested and uploaded 834 files)
EXIT STATUS     0
NETLIFY DEPLOYMENT ID = 6ac169ef7c75c383eb79f824
```

It ran once, with no Netlify build and no retry.

## 5. Host verification (Phases 10–13)

`seattle_wa_deployment_004 verify-live` produced `seattle_wa_live_verification_004.json`:
**ALL_LIVE_CHECKS PASS (15 / 15), ROLLBACK_REQUIRED NO.**

| check | result |
|---|---|
| host publishes | `6ac169ef` **ready / production**, previous deploy `6ac064cd` (the authorized parent) |
| HOST SITEMAP MATCH | **PASS**: served sitemap `63e05281…` = authorized |
| served route SET | identical to the authorized candidate's (4,117) |
| LIVE ACCOUNTING | **40 markets / 3,669 profiles / 4,044 release-index / 4,117 served** |
| SEATTLE | 139 profiles, 150 release-index routes, **151 served; 151 / 151 HTTP 200, 0 missing**; 10 corridors live |
| prior production | **3,966 / 3,966 parent routes HTTP 200**, 0 lost, only Seattle routes added |
| byte identity | 27 / 27 sampled pages byte-identical to the artifact (Seattle hub, comparison, 3 corridors, 6 hotels, 12 other market hubs, global surfaces) |
| unpublished rows | **all 164 unpublished census rows return 404**: 103 held + 61 verified-no-pets, probed at the census slug and at the route the site forms, 178 URLs |
| timeshare / military | the 2 timeshare and 3 military-restricted identities have no route (404) and are not named on Seattle's hub, comparison or corridor pages |
| spot checks | San Antonio, Austin, Phoenix, Denver, San Diego, Jacksonville FL, West Palm Beach, Fort Lauderdale, Augusta, Miami, Tampa, Orlando and Seattle **200**; **Detroit 404** (still withheld) |

The prior sweep's first pass had 48 client-side `000` gaps (no server answered anything but 200). All 48 returned
200 on refetch. The first-pass file is kept beside the merged one, and nothing was judged on a gap.

**Named held rows on production** (`markets/reports/seattle_wa_named_held_rows_live_004.json`). Each was probed at its
census slug and site route; the rebrands were also probed at their new names:

| row | result |
|---|---|
| 4 dual-brand rows | 404 |
| Hotel Interurban Tukwila | 404 |
| Courtyard Northgate | 404 |
| FairBridge Inn Express Tukwila (Days Inn row + new name) | 404 |
| Motel 6 Suites Kent (ESA Kent row + new name) | 404 |

UNAPPROVED SEATTLE PROFILES LIVE = **0**; the 61 verified-no-pets hotels are not profiles.

## 6. Postdeploy bounded quality (Phase 14)

| | |
|---|---|
| BROKEN LINKS / COLLISIONS / CANONICAL VIOLATIONS / GLOBAL SHADOWING | **0 / 0 / 0 / 0** |
| UNEXPECTED DELTA | `[]` |
| FAST receipt | still currently eligible; RULE J NONEMPTY PASS, RULE K NONVACUOUS PASS |
| pin and reader tests | `test_market_state_pins.py` + `test_question_negation_reader_001.py`: **307 / 307** |
| release contracts | `verify_all()` 41 / 41 |
| global authority | `build_global_authority --check` clean |
| broad regression runs | **0** |

## 7. Deployment state finalized (Phase 15, only after host verification passed)

**Record:** `deploy/netlify/deployment_records/ptf-deploy-seattle-004-6ac169ef7c75c383eb79f824.json`; `verify_record`
`[]`.
- `work_order` = the AUTHORIZING order (003); `deployer.work_order` = this order (004).
- `source_commit` = `438348c7`, the build commit.

**Authorization:** `ptf-auth-seattle-003-cfaad64a7bcb` went **AUTHORIZED → DEPLOYED** (consumed by deploy
`6ac169ef`). **CONSUMED = YES.**

**`supersessions.json`:** 36 → 37 entries.
- San Antonio's `ptf-auth-san-antonio-004-50b1ce95d803` is now historical, with 0 contract drift.
- Seattle is the new CURRENT entry, with an empty moved list.

**`deployment_state.json`:** the live and source pins both point at `6ac169ef` (bundle `cfaad64a…`, 3,669 / 4,117).
- source_commit equals the manifest's `438348c7`.
- Rollback target `6ac064cd` and rollback record `ptf-deploy-san-antonio-005-6ac064cd…` are recorded.

**Participation:** seattle-wa stays at `FOUNDER_AUTHORIZED_FOR_LAUNCH`, the state of every live market.

**Resolver after the commit:**
- RESOLVED YES; CURRENT_LIVE_SOURCE_COMMIT **`f0003e78`** (built from `438348c7`); deploy `6ac169ef`.
- 3,669 / 4,117, host verified.
- `derive_registration_base` already derives `f0003e78` automatically for the next market.

## 8. Rollback (Phase 16)

No critical failure occurred, so no rollback was performed. The target `6ac064cd6a4261e60054a2f3` stays available.

## 9. Cleanup

- Every process this order started has exited: predeploy, sweeps, verify-live, tests.
- No watcher remains, and the unrelated pre-existing python process (pid 14180) was left alone.
- **`C:\t\sea4a` is now the live artifact**, the parent bytes for the next deploy; `C:\t\sea4b` is its byte-identical
  twin.

## FINAL ANSWERS

1. PREDEPLOY LIVE DEPLOYMENT = 6ac064cd6a4261e60054a2f3
2. DEPLOYMENT AUTHORIZATION = ptf-auth-seattle-003-cfaad64a7bcb
3. AUTHORIZATION STATUS BEFORE = AUTHORIZED (unconsumed, deploy_id none)
4. AUTHORIZED PACKAGE = pkg-seattle-wa-784f0147e1220f40
5. AUTHORIZED CANDIDATE BUNDLE = cfaad64a7bcb1b2b1734fe777ea577d5884aafe953054c2d80a7db1b01e0e5c3
6. AUTHORIZED CANDIDATE SITEMAP = 63e052812b36668271aebb3f8bc933a44ac0d6150b7b8c19279d5f1e45a2b151
7. CANDIDATE INTEGRITY = PASS (verify_bundle_directory [] over 22,183 re-hashed files; BYTE_IDENTICAL twin)
8. NETLIFY DEPLOYMENT ID = 6ac169ef7c75c383eb79f824
9. NETLIFY RESULT = SUCCESS (exit 0, 20:47:14Z → 20:48:16Z, published ready / production)
10. HOST SITEMAP MATCH = PASS
11. LIVE MARKETS = 40
12. LIVE PROFILES = 3669
13. LIVE RELEASE-INDEX ROUTES = 4044
14. LIVE SERVED ROUTES = 4117
15. SEATTLE PROFILES LIVE = 139
16. SEATTLE RELEASE-INDEX ROUTES = 150
17. SEATTLE SERVED ROUTES = 151
18. SEATTLE ROUTES HTTP 200 = 151 / 151
19. DUAL-BRAND HELDS PUBLISHED = 0 / 4
20. HOTEL INTERURBAN PUBLISHED = 0
21. COURTYARD NORTHGATE PUBLISHED = 0
22. FAIRBRIDGE TUKWILA PUBLISHED = 0
23. MOTEL 6 SUITES KENT PUBLISHED = 0
24. PREOPENING PROFILES PUBLISHED = 0
25. TIMESHARE PROFILES PUBLISHED = 0
26. MILITARY-RESTRICTED PROFILES PUBLISHED = 0
27. UNAPPROVED SEATTLE PROFILES LIVE = 0
28. PET-FRIENDLY WITH EXPLICIT REFUSAL = 0
29. QUESTION-ONLY PET-FRIENDLY = 0
30. MISLEADING SINGLE FEES = 0
31. PRIOR MARKETS LOST = 0
32. PRIOR PROFILES LOST = 0
33. PRIOR ROUTES LOST = 0 (3,966 / 3,966 parent routes 200)
34. DETROIT STILL WITHHELD = YES (404)
35. RULE J NONEMPTY = PASS
36. RULE K NONVACUOUS = PASS
37. BROKEN LINKS = 0
38. COLLISIONS = 0
39. CANONICAL VIOLATIONS = 0
40. GLOBAL SHADOWING = 0
41. UNEXPECTED DELTA = []
42. DEPLOYMENT AUTHORIZATION CONSUMED = YES (AUTHORIZED → DEPLOYED)
43. SEATTLE PARTICIPATION = FOUNDER_AUTHORIZED_FOR_LAUNCH, participating in the live release
44. ROLLBACK REQUIRED = NO
45. CURRENT LIVE DEPLOYMENT = 6ac169ef7c75c383eb79f824
46. origin == HEAD = YES (verified after push)
47. tree clean = YES (verified after push)
48. SEATTLE LIVE = YES

```
SEATTLE PRODUCTION DEPLOYMENT = PASS
LIVE MARKETS = 40
LIVE PROFILES = 3669
LIVE SERVED ROUTES = 4117
SEATTLE PROFILES LIVE = 139
SEATTLE ROUTES LIVE = 151
PET-FRIENDLY RECORDS WITH EXPLICIT REFUSAL = 0
QUESTION-ONLY PET-FRIENDLY RECORDS = 0
UNAPPROVED SEATTLE PROFILES LIVE = 0
MISLEADING SINGLE FEES = 0
PRIOR MARKETS LOST = 0
PRIOR ROUTES LOST = 0
ROLLBACK REQUIRED = NO
SEATTLE LIVE = YES
```
