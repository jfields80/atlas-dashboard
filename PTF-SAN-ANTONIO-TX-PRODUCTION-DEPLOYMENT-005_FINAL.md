# PTF-SAN-ANTONIO-TX-PRODUCTION-DEPLOYMENT-005 — FINAL

**SAN ANTONIO IS LIVE.** Deploy **`6ac064cd6a4261e60054a2f3`** (published 2026-10-03T02:14:06Z) serves:
- **39 markets / 3,530 profiles / 3,894 release-index routes / 3,966 served routes**;
- San Antonio / Greater San Antonio as the thirty-ninth market and the second in Texas.

The rollback target is `6abf3e749cc359701298718d` (Austin). **Rollback was not required.**

The exact, already-built, founder-authorized candidate was deployed ONCE. There was:
- no rebuild, reseal or re-registration;
- no re-authorization or second whole-site assembly;
- no broad regression.

Branch `worker/ptf-san-antonio-tx-market-001`. Commits:
- `60683902`: SAN ANTONIO IS LIVE (record, consumed authorization, live manifest, supersessions, pins). This is now
  the live lineage commit.
- Then this report.

## 1. Parent, re-verified immediately before deploying

| | |
|---|---|
| PREDEPLOY LIVE DEPLOYMENT | `6abf3e749cc359701298718d` (source `f0ddbcde`, built from `ef28f7b4`) |
| accounting | 38 markets / 3,386 profiles / 3,737 release-index / 3,808 served; host verified |
| served sitemap | `d6461dbc…` (re-hashed at 02:12:50Z, seconds before the deploy) |
| Netlify `getSite` | `pettripfinder-prod`, published `6abf3e74`, **ready** |
| baseline sweep | 3,808 / 3,808 parent routes 200 (26 client-side `000` gaps, one contiguous block, all 200 on refetch) |

The parent had not advanced.

## 2. Authorization and exact bytes (Phases 2–6)

`san_antonio_tx_deployment_005.py predeploy` produced `markets/reports/san_antonio_tx_predeploy_005.json` with
**PREDEPLOY PASS**.

**Authorization `ptf-auth-san-antonio-004-50b1ce95d803`, before the deploy:**
- **AUTHORIZED**, deploy_id none, consumed NO.
- It names san-antonio-tx and `pkg-san-antonio-tx-aa8f4fe9ea26a6ff` (via the readiness packet and the authorization
  source).
- It binds bundle `50b1ce95…`, sitemap `e2a6b1c9…` and parent `6abf3e74`.
- `verify_authorization` `[]`, `deployability_problems` `[]`, `verify_target` `[]`.

**Exact prebuilt bytes:** `verify_bundle_directory(C:\t\sa4a\site)` `[]`.
- Re-hashed from disk, not rebuilt: bundle `50b1ce95d80386ed9c28f16ad1493bc4c8f2588f201bb1f95597a6d6984a6bf4`,
  sitemap `e2a6b1c94dff6f9178fe83913c0babaf74f1b02b9453be37e29ad2c82a86b484`, **21,351 files**, control files as
  authorized.
- **CANDIDATE INTEGRITY = PASS.**

**Re-read from the authorization order's accounting:**
- **Determinism and totals:** BYTE_IDENTICAL, 0 differing files; 39 / 3,530 / 3,894 / 3,966; San Antonio 144 / 157 /
  158.
- **Delta:** 0 prior files removed or changed; unexpected served-route delta `[]`; parent markets, routes and
  profiles preserved.
- **Held content and safety:**
  - unapproved profiles 0;
  - Hilton 0/10, dual-brand 0/8, Jackson House 0, preopening 0/4;
  - timeshare 0, military 0;
  - explicit refusal 0, question-only 0, misleading fees 0.
- **Collisions:** collision-safe PASS, bare-chain collisions 0. The Best Western Garden Inn name-based exclusion
  remains a recorded latent risk with 0 other buildings currently exposed; the mechanism was not changed.

**FAST receipt** `…-859baec5238b5b52.json`: currently eligible; J PASS (non-empty), K PASS (BYTE_IDENTICAL).

## 3. Live manifest (Phase 7)

`write-manifest` built the canonical live `deploy/netlify/global_deployment_manifest.json` from the exact
authorized bytes, immediately before the deploy:
- `verify_manifest` `[]`;
- **byte-identical** to the committed candidate manifest;
- bundle `50b1ce95…`, sitemap `e2a6b1c9…`, 39 markets, 3,530 profiles, 3,966 served routes.

No candidate byte was altered.

## 4. The deployment (Phase 8)

```
netlify deploy --prod --no-build --dir C:\t\sa4a\site --site pettripfinder-prod
DEPLOY START    2026-10-03T02:13:06Z
DEPLOY COMPLETE 2026-10-03T02:14:07Z   (61 s; CDN requested and uploaded 865 files)
EXIT STATUS     0
NETLIFY DEPLOYMENT ID = 6ac064cd6a4261e60054a2f3
```

It ran once, with no Netlify build and no retry.

## 5. Host verification (Phases 9–12)

`san_antonio_tx_deployment_005 verify-live` produced `san_antonio_tx_live_verification_005.json`:
**ALL_LIVE_CHECKS PASS (15 / 15), ROLLBACK_REQUIRED NO.**

| check | result |
|---|---|
| host publishes | `6ac064cd` **ready / production**, previous deploy `6abf3e74` (the authorized parent) |
| HOST SITEMAP MATCH | **PASS**: served sitemap `e2a6b1c9…` = authorized |
| served route SET | identical to the authorized candidate's (3,966) |
| LIVE ACCOUNTING | **39 markets / 3,530 profiles / 3,894 release-index / 3,966 served** |
| SAN ANTONIO | 144 profiles, 157 release-index routes, **158 served; 158 / 158 HTTP 200, 0 missing**; 12 corridors live |
| prior production | **3,808 / 3,808 parent routes HTTP 200**, 0 lost, only San Antonio routes added |
| byte identity | 27 / 27 sampled pages byte-identical to the artifact (San Antonio hub, comparison, 3 corridors, 6 hotels, 12 other market hubs, global surfaces) |
| unpublished rows | **all 270 unpublished census rows return 404**: 172 held + 98 verified-no-pets, probed at the census slug and at the route the site forms, 319 URLs |
| timeshare / military | the 8 timeshare and 9 military-restricted identities have no route (404) and are not named on San Antonio's hub, comparison or corridor pages |
| spot checks | Austin, Phoenix, Denver, San Diego, Jacksonville FL, West Palm Beach, Fort Lauderdale, Augusta, Miami, Tampa, Orlando, Jacksonville NC and San Antonio **200**; **Detroit 404** (still withheld) |

**Held rows on production:**
- the 10 Hilton blocked, 8 dual-brand, The Jackson House and 4 preopening rows are unpublished (404);
- the 98 verified-no-pets rows are not hotel profiles (404);
- UNAPPROVED SAN ANTONIO PROFILES LIVE = **0**.

**One slip of mine, caught before it counted.** My first San Antonio sweep matched 0 routes: Git Bash rewrote the
`/san-antonio-tx/` filter argument into a Windows path. It was re-run with `MSYS_NO_PATHCONV=1` and covered all 158
routes, and the host verification requires the sweep to cover exactly the served San Antonio set. Nothing was
judged on the empty sweep.

## 6. Postdeploy bounded quality (Phase 13)

| | |
|---|---|
| BROKEN LINKS / COLLISIONS / CANONICAL VIOLATIONS / GLOBAL SHADOWING | **0 / 0 / 0 / 0** |
| UNEXPECTED DELTA | `[]` |
| FAST receipt | still currently eligible; RULE J NONEMPTY PASS, RULE K NONVACUOUS PASS |
| pin and reader tests | `test_market_state_pins.py` + `test_question_negation_reader_001.py`: **302 / 302** (Austin's 297 + San Antonio's pin block) |
| release contracts | `verify_all()` 40 / 40 |
| global authority | `build_global_authority --check` clean |
| broad regression runs | **0** |

## 7. Deployment state finalized (Phase 14, only after host verification passed)

**Record:** `deploy/netlify/deployment_records/ptf-deploy-san-antonio-005-6ac064cd6a4261e60054a2f3.json`;
`verify_record` `[]`.
- `work_order` = the AUTHORIZING order (004); `deployer.work_order` = this order (005).
- `source_commit` = `be83dab2`, the build commit.

**Authorization:** `ptf-auth-san-antonio-004-50b1ce95d803` went **AUTHORIZED → DEPLOYED**. **CONSUMED = YES.**

**`supersessions.json`:** 35 → 36 entries.
- Austin's `ptf-auth-austin-004-75e569412dd2` is now historical, with 0 contract drift.
- San Antonio is the new CURRENT entry, with an empty moved list.

**`deployment_state.json`:** the live and source pins both point at `6ac064cd` (bundle `50b1ce95…`, 3,530 / 3,966).
- source_commit equals the manifest's `be83dab2`.
- Rollback target `6abf3e74` and rollback record `ptf-deploy-austin-004-6abf3e74…` are recorded.

**Participation:** san-antonio-tx stays at `FOUNDER_AUTHORIZED_FOR_LAUNCH`, the state of every live market.

**Resolver after the commit:**
- RESOLVED YES; CURRENT_LIVE_SOURCE_COMMIT **`60683902`** (built from `be83dab2`); deploy `6ac064cd`.
- 39 / 3,530 / 3,894 / 3,966, host verified.
- `derive_registration_base` already derives `60683902` automatically for the next market.

## 8. Rollback (Phase 15)

No critical failure occurred, so no rollback was performed. The target `6abf3e749cc359701298718d` stays available.

## 9. Cleanup

- Every process this order started has exited: predeploy, sweeps, verify-live.
- No watcher remains, and unrelated pre-existing processes were left alone.
- **`C:\t\sa4a` is now the live artifact**, the parent bytes for the next deploy; `C:\t\sa4b` is its byte-identical
  twin.

## FINAL ANSWERS

1. PREDEPLOY LIVE DEPLOYMENT = 6abf3e749cc359701298718d
2. DEPLOYMENT AUTHORIZATION = ptf-auth-san-antonio-004-50b1ce95d803
3. AUTHORIZATION STATUS BEFORE = AUTHORIZED (unconsumed, deploy_id none)
4. AUTHORIZED PACKAGE = pkg-san-antonio-tx-aa8f4fe9ea26a6ff
5. AUTHORIZED CANDIDATE BUNDLE = 50b1ce95d80386ed9c28f16ad1493bc4c8f2588f201bb1f95597a6d6984a6bf4
6. AUTHORIZED CANDIDATE SITEMAP = e2a6b1c94dff6f9178fe83913c0babaf74f1b02b9453be37e29ad2c82a86b484
7. CANDIDATE INTEGRITY = PASS (verify_bundle_directory [] over 21,351 re-hashed files; BYTE_IDENTICAL twin)
8. NETLIFY DEPLOYMENT ID = 6ac064cd6a4261e60054a2f3
9. NETLIFY RESULT = SUCCESS (exit 0, 02:13:06Z → 02:14:07Z, published ready / production)
10. HOST SITEMAP MATCH = PASS
11. LIVE MARKETS = 39
12. LIVE PROFILES = 3530
13. LIVE RELEASE-INDEX ROUTES = 3894
14. LIVE SERVED ROUTES = 3966
15. SAN ANTONIO PROFILES LIVE = 144
16. SAN ANTONIO RELEASE-INDEX ROUTES = 157
17. SAN ANTONIO SERVED ROUTES = 158
18. SAN ANTONIO ROUTES HTTP 200 = 158 / 158
19. HILTON BLOCKED ROWS PUBLISHED = 0 / 10
20. DUAL-BRAND ROWS PUBLISHED = 0 / 8
21. JACKSON HOUSE PUBLISHED = 0
22. PREOPENING PROFILES PUBLISHED = 0 / 4
23. TIMESHARE PROFILES PUBLISHED = 0
24. MILITARY-RESTRICTED PROFILES PUBLISHED = 0
25. UNAPPROVED SAN ANTONIO PROFILES LIVE = 0
26. PET-FRIENDLY WITH EXPLICIT REFUSAL = 0
27. QUESTION-ONLY PET-FRIENDLY = 0
28. MISLEADING SINGLE FEES = 0
29. PRIOR MARKETS LOST = 0
30. PRIOR PROFILES LOST = 0
31. PRIOR ROUTES LOST = 0 (3,808 / 3,808 parent routes 200)
32. DETROIT STILL WITHHELD = YES (404)
33. RULE J NONEMPTY = PASS
34. RULE K NONVACUOUS = PASS
35. BROKEN LINKS = 0
36. COLLISIONS = 0
37. CANONICAL VIOLATIONS = 0
38. UNEXPECTED DELTA = []
39. DEPLOYMENT AUTHORIZATION CONSUMED = YES (AUTHORIZED → DEPLOYED)
40. SAN ANTONIO PARTICIPATION = FOUNDER_AUTHORIZED_FOR_LAUNCH, participating in the live release
41. ROLLBACK REQUIRED = NO
42. CURRENT LIVE DEPLOYMENT = 6ac064cd6a4261e60054a2f3
43. origin == HEAD = YES
44. tree clean = YES
45. SAN ANTONIO LIVE = YES

```
SAN ANTONIO PRODUCTION DEPLOYMENT = PASS
LIVE MARKETS = 39
LIVE PROFILES = 3530
LIVE SERVED ROUTES = 3966
SAN ANTONIO PROFILES LIVE = 144
SAN ANTONIO ROUTES LIVE = 158
PET-FRIENDLY RECORDS WITH EXPLICIT REFUSAL = 0
QUESTION-ONLY PET-FRIENDLY RECORDS = 0
UNAPPROVED SAN ANTONIO PROFILES LIVE = 0
MISLEADING SINGLE FEES = 0
PRIOR MARKETS LOST = 0
PRIOR ROUTES LOST = 0
ROLLBACK REQUIRED = NO
SAN ANTONIO LIVE = YES
```
