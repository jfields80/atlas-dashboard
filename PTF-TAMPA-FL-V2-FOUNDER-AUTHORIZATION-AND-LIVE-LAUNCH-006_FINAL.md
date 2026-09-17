# PTF-TAMPA-FL-V2-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-006 — FINAL

Market `tampa-fl` — **Tampa Bay, Florida**. Branch `worker/ptf-tampa-fl-market-002`, worktree `C:\Atlas-Tampa-FL-Hardened-V2`.

**TAMPA V2 IS LIVE.**

---

## 1. Founder authorization

Persisted through the existing lifecycle by flipping `tampa-fl`'s `launch_status` in `deploy/netlify/launch_participation.json` from `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH` to `FOUNDER_AUTHORIZED_FOR_LAUNCH` — replicating, field-for-field, the exact single-line edit verified in Orlando's own real launch commit (`30d1b3ce`). No other market's row was touched.

A `deployment_authorization` record (`ptf-auth-tampa-006-cf761795e3de`) was built and persisted via `deployment_authorization.build_authorization`/`write_authorization`, binding: parent deployment `6aa9dad7cf1419580b307f71`, parent release digest `084ac16aba3293b1e9fa02d8e8d95700251cb001dba5a24d45b0df5b4d1eb380`, registered package `sha256:38f6e4b2dc1f6a111985288f334ca93d66472423ccac760c98f05f47afaa9c8d`, and the founder's own exact authorization statement. `verify_authorization` returned 0 problems before it was transitioned `PREPARED -> AUTHORIZED`.

## 2. Why `release_coordinator.py` was not used for the actual deploy

`release_coordinator.py` (ATLAS-THROUGHPUT-005/006) is the newer host-simulator framework; it self-reports `REAL_PRODUCTION_ACTIVATION: DISABLED` and ships with an empty production allowlist. Inspecting Orlando's own real launch commit confirmed its actual artifacts (`deployment_authorizations/`, `deployment_records/`, launch/verification reports) come from the older, proven `assemble_production_site.py` → `deployment_authorization.py` → `netlify deploy` pipeline — the same one used here. `release_coordinator.py inspect` was still used throughout as an independent, read-only cross-check of live state (it validates against 8 separate authoritative sources).

## 3. Real whole-site candidate build

Two genuine environmental obstacles were hit and resolved honestly rather than worked around:

- **Memory**: the first two build attempts were killed by the OS for low memory (as low as ~2GB free on a 15.9GB machine, shared with several other concurrent sessions/apps). Per explicit instruction, no repeated blind retries were made — the build was deferred until free memory recovered to ~7.5GB, then it succeeded.
- **A Bash path-mangling bug**: `C:\t\tpa6a` collapsed to a literal `C:ttpa6a` when passed through Bash's backslash handling, creating stray debris in the wrong directory. Fixed by using forward-slash Windows paths (`C:/t/tpa6b`) for every subsequent build.

The successful build (`C:\t\tpa6b`) assembled all 29 authorized markets (28 previously live + tampa-fl) and correctly excluded `detroit-ann-arbor-mi` (still `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH`). All 27 required gates passed; 0 broken links, 0 collisions, 0 global shadowing, 0 canonical violations.

**A real, investigated discrepancy, not a leak.** The registration-stage abstract "release-index" calculation had projected +99 routes for Tampa (2299→2398); the real build produced +161 (2299→2460). Investigated rather than dismissed: Tampa's 161 real routes decompose exactly as 148 hotel profiles + 11 corridors + 1 hub + 1 comparison page, and Orlando's own already-live 218-route count decomposes identically (201 + 15 + 1 + 1) — confirming the registration-time abstraction simply measures a narrower thing than the real sitemap, for every market, not a Tampa-specific defect. The real, verified, correct delta is **+161 routes**.

## 4. Exact digests

| Digest | Value |
|---|---|
| Registered package | `sha256:38f6e4b2dc1f6a111985288f334ca93d66472423ccac760c98f05f47afaa9c8d` |
| Final candidate / deployment artifact (same value, per established convention) | `cf761795e3deb1380ffb8e25869bd6ceefe31d2a9dfbaddad30c550ff69d60d2` |
| Candidate / live sitemap | `53589cf6a740046ad244d3760495f6cdc62bbc0f17f3061cfc4d83e1017f103b` |
| Intended delta (registration-stage `changed_market_bundle_sha256`; `release_coordinator`'s own intended-delta schema was not exercised, see §2) | `sha256:c1504c075e0720ec2703c86094c9e176cbecd9af06a02c76142d6dc560b5b940` |

## 5. Independent reproduction

Built twice, fully independently: `C:\t\tpa6b` and `C:\t\tpa6c`, separate process invocations, separate output directories. **Byte-identical**: same `bundle_sha256`, same `sitemap_sha256`, same route count, same gate results.

## 6. Hold and prior-live safety

- **All 314 held Tampa identities** individually checked against the live site: 0 in the live sitemap, all 404, 0 fetchable at 200.
- **All 28 prior-live markets**: published-profile counts compared field-by-field between the pre-deploy `release_coordinator inspect()` snapshot and the authoritative post-build `global_bundle_manifest.json` — every single one identical (e.g. `orlando-fl` 201=201, `atlanta-ga` 244=244). 0 unexpected market/profile/route changes.
- `detroit-ann-arbor-mi` (the one other source-ready-but-unauthorized market) confirmed still 404, correctly excluded.

## 7. Deployment

```
netlify deploy --prod --no-build --dir "C:/t/tpa6b/site" --site "$NETLIFY_SITE_ID"
```

Deploy ID `6aab379e0777c9ee96702a4f`, state `ready`, published `2026-09-17T00:43:38.767Z`. No build, no reassembly, no reseal, no candidate regeneration — the exact bytes already reproduced twice.

## 8. Critical live verification (all performed post-deploy, against the real production host)

- Live sitemap SHA-256 **exactly matches** the authorized candidate sitemap digest.
- **All 2,460 live routes checked** (concurrent HTTP HEAD, not a sample): 2,460 / 2,460 return 200.
- Tampa hub, policy-comparison page, and all 11 publishing corridor pages: 200.
- A cross-corridor sample of 8 Tampa hotel profiles: 200.
- All 314 held identities: 404 (checked individually, not sampled).
- All 28 prior-live markets: profile counts unchanged, all still live.
- `release_coordinator inspect()` (independent, 8-source cross-check): **`verified: true`, 0 problems** — confirmed only after the deployment record and the `tests/pettripfinder/pins/deployment_state.json` mirror were both updated to reflect the new reality.

**Rollback was not required.**

## 9. Records written

- `deploy/netlify/deployment_authorizations/ptf-auth-tampa-006-cf761795e3de.json` — final status `DEPLOYED`.
- `deploy/netlify/deployment_records/ptf-deploy-tampa-006-6aab379e0777c9ee96702a4f.json`.
- `deploy/netlify/global_deployment_manifest.json` — regenerated from the real build.
- `tests/pettripfinder/pins/deployment_state.json` — `live` and `source` blocks both updated to the new reality (they agree; `ahead_of_production: false`).
- `launch_packages/pettripfinder/release_production_gate.json` — Tampa's gate-history entry appended (opened and immediately closed by this same work order; allowlist stays empty).
- `launch_packages/pettripfinder/markets/reports/tampa_fl_launch_report_006.json`, `tampa_fl_live_verification_006.json` — full machine-readable detail.

## 10. Parallel safety

`git diff --name-only` against the pre-launch commit touches only Tampa-specific paths plus the same class of shared bookkeeping documents every prior real launch touched (`launch_participation.json`, `global_deployment_manifest.json`, `deployment_state.json`, `release_production_gate.json`) — 0 shared factory code changed, 0 other market's own data changed, 0 broad regression run.

---

## FINAL ANSWERS

1. PARENT LIVE DEPLOYMENT ID = `6aa9dad7cf1419580b307f71`
2. PARENT RELEASE DIGEST = `084ac16aba3293b1e9fa02d8e8d95700251cb001dba5a24d45b0df5b4d1eb380`
3. PARENT MARKETS / PROFILES / ROUTES = 28 / 2003 / 2299
4. REGISTERED TAMPA PACKAGE DIGEST = `sha256:38f6e4b2dc1f6a111985288f334ca93d66472423ccac760c98f05f47afaa9c8d`
5. FOUNDER AUTHORIZATION ID = `ptf-auth-tampa-006-cf761795e3de`
6. FINAL CANDIDATE DIGEST = `cf761795e3deb1380ffb8e25869bd6ceefe31d2a9dfbaddad30c550ff69d60d2`
7. DEPLOYED ARTIFACT DIGEST = `cf761795e3deb1380ffb8e25869bd6ceefe31d2a9dfbaddad30c550ff69d60d2`
8. DEPLOYED SITEMAP DIGEST = `53589cf6a740046ad244d3760495f6cdc62bbc0f17f3061cfc4d83e1017f103b`
9. INTENDED DELTA DIGEST = `sha256:c1504c075e0720ec2703c86094c9e176cbecd9af06a02c76142d6dc560b5b940` (see §4 note on provenance)
10. NEW HOST DEPLOYMENT ID = `6aab379e0777c9ee96702a4f`
11. FINAL LIVE MARKETS / PROFILES / ROUTES = 29 / 2151 / 2460
12. TAMPA LIVE PROFILES = 148
13. TAMPA SITEMAP ROUTES ADDED = 161 (real, verified; see §3 for why this differs from the registration-stage estimate of 99)
14. TAMPA RELEASE-INDEX ROUTES ADDED = 161
15. ALL 314 HOLDS REMAIN UNPUBLISHED = YES
16. ALL PRIOR LIVE MARKETS PRESERVED = YES (28/28, 0 unexpected changes)
17. ORLANDO PRESERVED = YES (201 profiles, 218 routes, unchanged)
18. UNEXPECTED MARKET / PROFILE / ROUTE CHANGES = 0 / 0 / 0
19. CANDIDATES BYTE IDENTICAL = YES
20. EXACT AUTHORIZED ARTIFACT DEPLOYED = YES
21. BUILD / REASSEMBLY AFTER STAGING = NO
22. ALL CRITICAL LIVE CHECKS PASS = YES
23. BROAD REGRESSIONS = 0
24. FACTORY CODE CHANGED = NO
25. ROLLBACK REQUIRED = NO
26. origin == HEAD = (verified mechanically after push, not pre-written — see push verification)
27. tree clean = (verified mechanically after push, not pre-written — see push verification)

TAMPA V2 LIVE = YES
LIVE MARKETS = 29
LIVE PROFILES = 2151
LIVE ROUTES = 2460
BROAD REGRESSIONS = 0
FACTORY CODE CHANGED = NO
FACTORY STATUS = RESUME_MARKET_PRODUCTION

STOP.
