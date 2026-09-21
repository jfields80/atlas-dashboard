# PTF-MIAMI-FL-PRODUCTION-DEPLOYMENT-006 — FINAL

**MIAMI IS LIVE.** Greater Miami joined production as the **thirty-first market** at 125 published pet-friendly
profiles over 10 publishing corridors.

Market `miami-fl`. Branch `worker/ptf-miami-fl-market-001`, worktree `C:\Atlas-Miami-FL-Hardened-V1`.
Head at start **18968073**; deployment recorded at **fbaf6f73**.

The exact already-built, already-gated, already-authorized candidate was deployed. Nothing was rebuilt, nothing
was resealed, no bytes were substituted, and no other market was touched.

---

## 1. Phase 1 — predeploy live, reverified immediately before the call

| | |
|---|---|
| PREDEPLOY LIVE SOURCE COMMIT | `9656419918229db7a0eb5ca5a1b4fb514e0e9c34` |
| PREDEPLOY LIVE DEPLOYMENT | `6aaeb3b7384e1bb712adb084` |
| PREDEPLOY LIVE BUNDLE | `55e0f5bbf02a5e26e8a5eba8510a4488d9a3da6ffaac604ef22df80637fd8914` |
| PREDEPLOY LIVE SITEMAP | `d08b8ca2f019196be244a99c082369b3c557715dbb98ce5dc1da604bbed937e1` |
| PREDEPLOY LIVE MARKETS | **30** |
| PREDEPLOY LIVE PROFILES | **2165** |
| PREDEPLOY LIVE ROUTES | **2477** |
| HOST VERIFIED | **YES** |
| PARENT MATCHES AUTHORIZED | **YES** — identical on every field |

The parent had not advanced. Deployment proceeded against the exact parent the authorization binds.

## 2. Phase 2 — the founder authorization

| | |
|---|---|
| FOUNDER AUTHORIZATION ID | `ptf-auth-miami-005-b2ad54b9be8b` |
| authorized_by / authorized_at | `founder` / 2026-09-20T22:17:44Z |
| AUTHORIZED (before deploy) | **YES** — `authorization_status: AUTHORIZED` |
| CONSUMED (before deploy) | **NO** |
| AUTHORIZED MARKET | `miami-fl`, and only `miami-fl` |
| AUTHORIZED PACKAGE | `pkg-miami-fl-b586ad449e46d057` |
| AUTHORIZED PARENT | `6aaeb3b7384e1bb712adb084` (= the verified live above) |
| AUTHORIZED CANDIDATE BUNDLE | `b2ad54b9be8b8a0121b8b664ef95e6d4dcf3feb873b4b23558c3721cdc06732a` |
| AUTHORIZED SITEMAP | `5ac34c75d6ba22d87b5da9d9ff40844dc2e986d7b778760849c03769bb088980` |
| binding identity | `bundle_sha256` |

**A verification that failed first, and why that was correct.** Run before Phase 5, `verify_authorization`
reported disagreements on every Miami field — the authorization binds the candidate while the committed live
manifest still described Augusta. That is precisely the state the previous order left on purpose. After Phase 5
wrote the live manifest from the authorized bytes, the same command returned **`disagreements: []`** and
`--deployable` returned **`blockers: []`**. No gate was relaxed to get there.

## 3. Phase 3 — the exact candidate bytes

Recomputed from `C:\t\mia5a\site` with the deployer's own formula (`assemble_production_site.file_hashes` →
`bundle_digest`), not read from a log:

| | Required | Recomputed | |
|---|---|---|---|
| BUNDLE SHA256 | `b2ad54b9…6732a` | `b2ad54b9be8b8a0121b8b664ef95e6d4dcf3feb873b4b23558c3721cdc06732a` | **MATCH** |
| SITEMAP SHA256 | `5ac34c75…88980` | `5ac34c75d6ba22d87b5da9d9ff40844dc2e986d7b778760849c03769bb088980` | **MATCH** |
| FILES | 13943 | **13943** | **MATCH** |
| MARKETS | 31 | **31** | **MATCH** |
| PROFILES | 2290 | **2290** | **MATCH** |
| SITEMAP ROUTES | 2614 | **2614** | **MATCH** |

Assembly quality counters: **broken links 0, collisions 0, global shadowing 0, canonical violations 0.**

Against the pre-deploy live sitemap: **PRIOR ROUTES REMOVED = 0**, 137 routes added and every one Miami,
**UNEXPECTED MARKET DELTA = []**, no market lost.

## 4. Phase 4 — deployment authorization

The canonical authorization for these exact bytes already existed from order 005 and was **verified and reused**,
not recreated — creating a second authorization for the same bytes is exactly what the mechanism forbids.

| | |
|---|---|
| DEPLOYMENT AUTHORIZATION ID | `ptf-auth-miami-005-b2ad54b9be8b` |
| AUTHORIZED BUNDLE | `b2ad54b9be8b8a0121b8b664ef95e6d4dcf3feb873b4b23558c3721cdc06732a` |
| AUTHORIZED SITEMAP | `5ac34c75d6ba22d87b5da9d9ff40844dc2e986d7b778760849c03769bb088980` |
| AUTHORIZED PARENT | `6aaeb3b7384e1bb712adb084` |
| STATUS at deploy time | **AUTHORIZED**, unconsumed, `disagreements: []`, `blockers: []` |

## 5. Phase 5 — the live manifest, written from the authorized bytes

`global_deployment_manifest.json` was rebuilt from `C:\t\mia5a\global_bundle_manifest.json` — the candidate's own
bytes. The rebuilt document is **byte-equal to the candidate manifest order 005 wrote**, so nothing about the
artifact changed between authorization and deployment.

Manifest now states: bundle `b2ad54b9…`, sitemap `5ac34c75…`, **31 markets / 2290 profiles / 2614 routes**,
`verify_manifest` **0 problems**, `deployment_authorized: false` (that flag is set by the deployer contract, not
by this write).

## 6. Phase 6 — production deployment

```
netlify deploy --prod --no-build --dir C:\t\mia5a\site --site pettripfinder-prod
```

| | |
|---|---|
| NETLIFY DEPLOYMENT ID | **`6ab071a5b7561c33aff6c17b`** |
| DEPLOYED URL / HOST | https://pettripfinder.com (unique: `https://6ab071a5b7561c33aff6c17b--pettripfinder-prod.netlify.app`) |
| DEPLOY START | 2026-09-20T23:51:37Z |
| DEPLOY COMPLETE | 2026-09-20T23:52:32Z (**55 s**) |
| EXIT STATUS | **0** |
| Files uploaded | **757** — only what changed; no Netlify build ran |

## 7. Phase 7 — immediate host verification

| | Required | Measured |
|---|---|---|
| HOST SITEMAP = AUTHORIZED CANDIDATE SITEMAP | yes | **`5ac34c75d6ba22d87b5da9d9ff40844dc2e986d7b778760849c03769bb088980`** — exact match |
| LIVE MARKETS | 31 | **31** |
| LIVE PROFILES | 2290 | **2290** |
| LIVE SITEMAP ROUTES | 2614 | **2614** |
| EXPECTED MIAMI ROUTES | 137 | **137** |
| MIAMI ROUTES 200 | 137 | **137** |
| MIAMI ROUTES MISSING | 0 | **0** |

Miami's 137 = **1 market hub + 10 corridor routes + 125 hotel profiles + 1 policy-comparison route**, matching
the release contract's declared 125 hotel routes and 10 published corridors exactly.

## 8. Phase 8 — hold and exclusion safety

| | Expected | Measured |
|---|---:|---:|
| MIAMI APPROVED PROFILES LIVE | 125 | **125** |
| MIAMI HELD/EXCLUDED PROFILES ERRONEOUSLY LIVE | 0 | **0** |

- All **125** CLEAN_PET_FRIENDLY slugs from the committed partition are live; the live Miami profile set contains
  **nothing else**.
- **0** of the 57 VERIFIED_NO_PETS rows appear as profiles — they remain exclusion records, as every live
  market's contract does it.
- **0** of the 455 held rows appear as profiles.
- 18 held/no-pets rows sampled across **every** non-publishing disposition — ACCESS_BLOCKED, EVIDENCE_HOLD,
  IDENTITY_MISMATCH_HOLD, ROUTING_HOLD, SOURCE_SILENT, VERIFIED_NO_PETS — **all 18 return 404**.

## 9. Phase 9 — prior production preservation

| | |
|---|---:|
| PRIOR MARKETS LOST | **0** |
| PRIOR PROFILES LOST | **0** |
| PRIOR ROUTES LOST | **0** |

Full membership, not spot checks: every one of the **2477** pre-deploy routes is present in the served sitemap,
and the served route set is **exactly** the authorized candidate's set. Per-market profile counts are unchanged
for all 30 prior markets.

Representative HTTP checks, all **200**: `augusta-ga`, `tampa-fl`, `orlando-fl`, `savannah-ga`, `asheville-nc`,
`raleigh-nc`, `richmond-va`, plus `/`, `/pet-friendly-hotels/`, `/about/`, `/methodology/` — 11 of 11.

## 10. Phase 10 — post-deploy quality gates

**Every one of the 2614 served routes was fetched individually — 2614 × HTTP 200, 0 non-200.** Not sampled.

| | |
|---|---:|
| BROKEN LINKS | **0** |
| COLLISIONS | **0** |
| CANONICAL VIOLATIONS | **0** |
| GLOBAL SHADOWING | **0** |
| UNEXPECTED DELTA | **[]** (markets, profiles, routes) |

Production accounting reconciles exactly: 2165 + 125 = **2290** profiles; 2477 + 137 = **2614** routes;
30 + 1 = **31** markets. No legacy broad regression was run.

## 11. Phase 11 — deployment state finalized

Only after host verification passed:

- Deployment record **`ptf-deploy-miami-006-6ab071a5b7561c33aff6c17b`** written; `verify_record` **0 problems**.
- Authorization transitioned **AUTHORIZED → DEPLOYED** and **consumed**.
- Deployment pins moved to the Miami deployment, both blocks derived from committed evidence; `live` and
  `source` agree, so `ahead_of_production` is false.
- Miami participation is `FOUNDER_AUTHORIZED_FOR_LAUNCH` and Miami is now in the live participating set. **No
  other market's participation was altered.**

The repaired resolver, re-run after the records were committed, now reports Miami as canonical live with
**`host_verified: true`, `problems: []`** — live deploy `6ab071a5b7561c33aff6c17b`, bundle `b2ad54b9…`,
31 / 2290 / 2614.

## 12. Phase 12 — rollback

**ROLLBACK REQUIRED = NO.** No rollback condition occurred: bundle matched, served sitemap matched, no Miami
route missing, no prior route or profile lost, no unexpected delta, no broken links, no held property published,
and accounting reconciled. The rollback target `6aaeb3b7384e1bb712adb084` (augusta-ga LIVE) is recorded in the
deployment record and pins, unused.

## 13. Phase 13 — final accounting

| | Before | **After** |
|---|---:|---:|
| LIVE MARKETS | 30 | **31** |
| LIVE PROFILES | 2165 | **2290** |
| LIVE ROUTES | 2477 | **2614** |

| Miami | |
|---|---:|
| MIAMI PROFILES LIVE | **125** |
| MIAMI ROUTES LIVE | **137** |
| MIAMI CORRIDORS LIVE | **10** |

| Preservation | |
|---|---:|
| PRIOR MARKETS PRESERVED | **30 / 30** |
| PRIOR PROFILES PRESERVED | **2165 / 2165** |
| PRIOR ROUTES PRESERVED | **2477 / 2477** |

---

## FINAL ANSWERS

1. **PREDEPLOY LIVE DEPLOYMENT** = `6aaeb3b7384e1bb712adb084`
2. **PREDEPLOY LIVE BUNDLE** = `55e0f5bbf02a5e26e8a5eba8510a4488d9a3da6ffaac604ef22df80637fd8914`
3. **FOUNDER AUTHORIZATION** = `ptf-auth-miami-005-b2ad54b9be8b` (founder, 2026-09-20)
4. **DEPLOYMENT AUTHORIZATION** = `ptf-auth-miami-005-b2ad54b9be8b` — verified and reused, not recreated
5. **AUTHORIZED CANDIDATE BUNDLE** = `b2ad54b9be8b8a0121b8b664ef95e6d4dcf3feb873b4b23558c3721cdc06732a`
6. **CANDIDATE INTEGRITY** = VERIFIED — 13943 files rehashed on disk to the authorized bundle; sitemap matched
7. **NETLIFY DEPLOYMENT ID** = `6ab071a5b7561c33aff6c17b`
8. **NETLIFY DEPLOYMENT RESULT** = SUCCESS (exit 0, 757 files, `--no-build`, 55 s)
9. **HOST SITEMAP MATCH** = YES — served sitemap hashes to the authorized candidate
10. **LIVE MARKETS** = 31
11. **LIVE PROFILES** = 2290
12. **LIVE ROUTES** = 2614
13. **MIAMI PROFILES LIVE** = 125
14. **MIAMI ROUTES LIVE** = 137
15. **MIAMI CORRIDORS LIVE** = 10
16. **MIAMI EXPECTED ROUTES 200** = 137 / 137
17. **HELD/EXCLUDED MIAMI PROFILES ERRONEOUSLY LIVE** = 0
18. **PRIOR MARKETS LOST** = 0
19. **PRIOR PROFILES LOST** = 0
20. **PRIOR ROUTES LOST** = 0
21. **BROKEN LINKS** = 0
22. **COLLISIONS** = 0
23. **CANONICAL VIOLATIONS** = 0
24. **UNEXPECTED DELTA** = []
25. **AUTHORIZATION CONSUMED** = YES (AUTHORIZED → DEPLOYED)
26. **MIAMI PARTICIPATION** = `FOUNDER_AUTHORIZED_FOR_LAUNCH`, live and serving
27. **ROLLBACK REQUIRED** = NO
28. **CURRENT LIVE DEPLOYMENT** = `6ab071a5b7561c33aff6c17b`
29. **CURRENT LIVE BUNDLE** = `b2ad54b9be8b8a0121b8b664ef95e6d4dcf3feb873b4b23558c3721cdc06732a`
30. **origin == HEAD** = YES
31. **tree clean** = YES
32. **MIAMI LIVE** = YES

---

MIAMI PRODUCTION DEPLOYMENT = PASS
LIVE MARKETS = 31
LIVE PROFILES = 2290
LIVE ROUTES = 2614
MIAMI PROFILES LIVE = 125
MIAMI ROUTES LIVE = 137
PRIOR MARKETS LOST = 0
PRIOR ROUTES LOST = 0
HELD MIAMI PROFILES ERRONEOUSLY LIVE = 0
ROLLBACK REQUIRED = NO
MIAMI LIVE = YES

STOP.
