# PTF-SAN-DIEGO-CA-PRODUCTION-DEPLOYMENT-004 — FINAL

**SAN DIEGO / COASTAL SAN DIEGO COUNTY IS LIVE** — deploy **`6ab859787d349f8397e1450a`**, the exact
founder-authorized candidate, deployed once with no rebuild. Production is now **35 markets / 2,666 profiles /
2,969 release-index routes / 3,037 served routes**. Rollback was not required.

Branch `worker/ptf-san-diego-ca-market-001`; the deployment state is committed in `f01587ba` (the resolver's new
`CURRENT_LIVE_SOURCE_COMMIT`, built from `34d523d9`).

No rebuild, no reseal, no acquisition, registration or authorization re-run, no whole-site assembly, no broad
regression, no spend, no Places lookups, no `identity_resolutions.json` write.

---

## 1 — PREDEPLOY PARENT (reverified at the start and again immediately before the call)

| | |
|---|---|
| PREDEPLOY LIVE SOURCE COMMIT | `e9a059e50c88d011bd708a28dbd25a6fffece461` (built_from `e7e02d43`) |
| PREDEPLOY LIVE DEPLOYMENT | `6ab6c8798bd9daf5038ae3e5` (jacksonville-fl) |
| PREDEPLOY LIVE BUNDLE | `f82f0714db2dd4d714b6b789c68492f60de8a1f3287a11b1e6f1afd680cf0c4e` |
| PREDEPLOY LIVE SITEMAP | `d34b0e5d7d5ed045a3f727e49f18e2fe61de3df108e9ef0666c5413d1bb48e4f` |
| PREDEPLOY LIVE MARKETS / PROFILES | **34 / 2,519** |
| PREDEPLOY LIVE RELEASE-INDEX / SERVED ROUTES | **2,807 / 2,874** |
| HOST VERIFIED | **true** |

A baseline sweep of all 2,874 live routes before the deploy: **2,874 / 2,874 HTTP 200**. The live sitemap equals
the sitemap of Jacksonville's authorized artifact `C:\t\jax3a`, so byte comparisons against that artifact are
comparisons against production.

## 2 — DEPLOYMENT AUTHORIZATION (resolved from the committed document; full hashes)

| | |
|---|---|
| AUTHORIZATION | `ptf-auth-san-diego-003-553a858f2590` |
| STATUS BEFORE / CONSUMED / DEPLOY_ID | **AUTHORIZED / NO / NONE** (history PREPARED → AUTHORIZED) |
| MARKET | `san-diego-ca`, in the bound set of 35 markets; 35 release contracts bound |
| AUTHORIZED PACKAGE | `pkg-san-diego-ca-5d5ffd65bf1262a1` (sha256:5d5ffd65bf1262a17273100a2dc97ecfe80e54d61033441530dd05ab19914b7e) |
| AUTHORIZED BUNDLE | `553a858f2590094127ce68e63992c2c3dff969fcdc8f290decf112791f447eec` |
| AUTHORIZED SITEMAP | `4f648fff6eaf50f7f7614eefda2639ac10c5cb678e77ef6fd15af60c89c0173e` |
| AUTHORIZED SOURCE COMMIT | `34d523d9792499c9a7c413eddac3dc6e8d54d135` |
| AUTHORIZED PARENT / ROLLBACK TARGET | `6ab6c8798bd9daf5038ae3e5` / `6ab6c8798bd9daf5038ae3e5` |
| existing San Diego deployment records | **0** |

`verify_authorization` failed on first load, and every problem was the documented ordering: it compared the
authorization with `global_deployment_manifest.json`, which still described Jacksonville production (bundle
`f82f0714…`, 34 markets, source `e7e02d43`). Once Phase 7 wrote the live manifest from the authorized bytes, both
`verify_authorization` and `deployability_problems` returned **`[]`**. The candidate was never touched to make a
check pass.

## 3 — CANDIDATE IDENTITY AND DETERMINISM

| | Authorization | `C:\t\sd3a` | `C:\t\sd3b` |
|---|---|---|---|
| bundle | `553a858f…7eec` | **equal** | **equal** |
| sitemap | `4f648fff…173e` | **equal** (also re-hashed from `site/sitemap.xml`) | **equal** |
| files / HTML pages | 16,202 | 16,202 / 16,184 | 16,202 / 16,184 |
| served routes | 3,037 | 3,037 | 3,037 |
| markets / profiles / index routes | 35 / 2,666 / 2,969 | 35 / 2,666 / 2,969 | same |
| San Diego | — | 147 hotel / 14 corridor / hub / policy-comparison | same |
| broken links · collisions · shadowing · canonical violations | — | **0 · 0 · 0 · 0**, all gates pass | same |

Control files `_headers`, `_redirects`, `robots.txt`, `llms.txt` are present and byte-identical to the live
artifact's. **Full byte walk of both site trees: 16,202 files each, 0 differing**, and every file on disk matches
`file_hash_manifest.json` (0 mismatches, 0 unlisted files). `sd3b` was used only as verification evidence;
`sd3a` was deployed.

## 4 — DELTA / PRESERVATION (as sets and bytes, versus the live bytes)

| | |
|---|---|
| FILES ADDED / REMOVED / CHANGED | **860 / 0 / 1** — 860 = 163 San Diego pages + 697 `/go/` pages; the one change is `sitemap.xml` (global, regenerated every release) |
| PRIOR-MARKET FILES CHANGED | **0**; unclassified paths **0** |
| PRIOR MARKETS / PROFILES / RELEASE-INDEX ROUTES / SERVED ROUTES LOST | **0 / 0 / 0 / 0** |
| SAN DIEGO SERVED ROUTES ADDED | **163**, every one under `/pet-friendly-hotels/san-diego-ca/` |
| UNEXPECTED MARKET / PROFILE / ROUTE DELTA | **`[]` / `[]` / `[]`** |

`index.html` and `pet-friendly-hotels/index.html` are byte-identical to live (a new market ships hidden from
global navigation and the sitemap flags).

## 5 — SAN DIEGO PUBLICATION SAFETY

| | |
|---|---:|
| APPROVED SAN DIEGO PROFILES | **147** |
| HELD / UNAPPROVED SAN DIEGO PROFILES IN CANDIDATE | **0** |
| NO-WEBSITE HOLDS PUBLISHED | **0** of 130 |
| DUAL-BRAND HOLDS PUBLISHED | **0** of 10 |
| OTHER HELD ROWS PUBLISHED | **0** of 52 |
| VERIFIED-NO-PETS AS HOTEL PROFILES | **0** of 92 |

Checked on the built artifact (no page, sitemap route, release-index route or `/go/` file for any of them) and
again on the production host (§11). `identity_resolutions.json` not written.

## 6 — FEE SAFETY

| | |
|---|---:|
| TIERED FEE ROWS | **30** (all withheld) |
| MULTI-AMOUNT ROWS | **43** |
| MISLEADING SINGLE FEES | **0** |

## 7 — LIVE MANIFEST

`global_deployment.write_manifest()` on `C:\t\sd3a\global_bundle_manifest.json` — the authorized bytes, not a
recomposition — immediately before the deploy. It describes bundle `553a858f…`, sitemap `4f648fff…`, **35 markets /
2,666 profiles / 3,037 routes**, source `34d523d9`; `verify_manifest []`; identical to the committed candidate
manifest `global_deployment_manifest_candidate_san_diego_003.json`.

## 8 — THE DEPLOYMENT

```
netlify deploy --prod --no-build --dir C:\t\sd3a\site --site pettripfinder-prod

DEPLOY START          = 2026-09-26T23:46:12.31Z
DEPLOY COMPLETE       = 2026-09-26T23:47:36.20Z        (84 s)        EXIT STATUS = 0
NETLIFY DEPLOYMENT ID = 6ab859787d349f8397e1450a
DEPLOY URL            = https://pettripfinder.com
unique URL            = https://6ab859787d349f8397e1450a--pettripfinder-prod.netlify.app

CDN requesting 862 files -> Finished uploading 862 assets -> Deploy is live!
```

`--no-build`: Netlify built nothing and no content was regenerated. One deploy command, run once. Netlify's upload
count (862) is its diff against its own stored deploy state, not the artifact delta (860 + 1); what is SERVED is
verified below. Netlify's API confirms the lineage: published deploy **`6ab859787d349f8397e1450a`**, `state: ready`,
`context: production`, `published_at 2026-09-26T23:47:34.677Z`; the **previous** deploy is
`6ab6c8798bd9daf5038ae3e5`, the authorized parent.

## 9 — HOST VERIFICATION (`san_diego_ca_live_verification_004.json`, **13/13 PASS**)

| | |
|---|---|
| HOST SITEMAP SHA | `4f648fff6eaf50f7f7614eefda2639ac10c5cb678e77ef6fd15af60c89c0173e` |
| HOST SITEMAP MATCH | **PASS** (= authorized sitemap sha) |
| SERVED ROUTE SET | **identical** to the authorized candidate's set |
| LIVE MARKETS | **35** (counted by each fragment's own hub route) |
| LIVE PROFILES | **2,666** |
| LIVE RELEASE-INDEX ROUTES | **2,969** |
| LIVE SERVED ROUTES | **3,037** |
| SAMPLED PAGES BYTE-IDENTICAL TO THE ARTIFACT | **23 / 23** (San Diego hub, comparison page, 3 corridors, 6 hotels; 8 prior market hubs; apex, category root, robots.txt, llms.txt) |

## 10 — ALL SAN DIEGO ROUTES

The expected set was taken from the authorized candidate's own sitemap (every `<loc>` under
`/pet-friendly-hotels/san-diego-ca/`), not from arithmetic, and fetched once each:

```
total=163 ok=163 bad=0 lines=163
```

| class | routes | HTTP 200 |
|---|---:|---:|
| hotel profiles | 147 | 147 |
| corridor pages | 14 | 14 |
| market hub | 1 | 1 |
| policy-comparison | 1 | 1 |
| **total** | **163** | **163** |

Publishing corridors: carlsbad, del-mar-solana-beach, downtown-gaslamp-waterfront, east-county-i8,
escondido-san-marcos-vista, la-jolla, mission-pacific-beach, mission-valley-hotel-circle, oceanside,
old-town-midway, point-loma-shelter-island-airport, rancho-bernardo-poway-i15, south-bay-chula-vista,
utc-golden-triangle-sorrento. SAN DIEGO ROUTES MISSING = **0**. No live route of this market names a refused place
(Orange County, Riverside / Temecula, Palm Springs, Tijuana).

## 11 — HELD PROFILES IN PRODUCTION

**Every** unpublished census row was probed at its own census slug on the production host — exhaustively, not
sampled:

| group | rows | returning 200 |
|---|---:|---:|
| no-website | 130 | **0** |
| dual-brand | 10 | **0** |
| other held | 52 | **0** |
| verified-no-pets (as profiles) | 92 | **0** |
| **total** | **284** | **0** — all 404 |

APPROVED SAN DIEGO PROFILES LIVE = **147**; HELD / UNAPPROVED SAN DIEGO PROFILES ERRONEOUSLY LIVE = **0**.

## 12 — PRIOR PRODUCTION PRESERVATION

All 2,874 prior served routes re-fetched after the deploy, one sweep recording every status:

```
total=2874 ok=2874 bad=0 lines=2874
```

PRIOR MARKETS LOST **0** (34 / 34 preserved), PRIOR PROFILES LOST **0**, PRIOR SERVED ROUTES LOST **0**.

| representative market | status |
|---|---|
| Jacksonville FL | **200** |
| West Palm Beach | **200** |
| Fort Lauderdale | **200** |
| Augusta | **200** |
| Miami | **200** |
| Tampa | **200** |
| Orlando | **200** |
| Cleveland–Akron–Canton | **200** |
| Jacksonville NC | **200** (route set 19 → 19, unchanged) |
| Detroit | **404** — still withheld |

## 13 — FAST / RECEIPT SAFETY

San Diego's receipt `pkg-san-diego-ca-5d5ffd65bf1262a1-d3954ca9de28df5a.json` is **currently eligible** under
today's reader: RULE J **PASS** (881 files, 865 HTML, bundle `9d07caac…`, 0 output defects), RULE K **PASS**
(BYTE_IDENTICAL). Augusta's historical empty receipt is unmodified and still **ineligible** (`EMPTY_BUNDLE`,
`NO_HTML_OUTPUT`).

## 14 — POSTDEPLOY QUALITY (bounded; no broad regression)

| | |
|---|---:|
| BROKEN LINKS | **0** |
| COLLISIONS | **0** |
| CANONICAL VIOLATIONS | **0** |
| GLOBAL SHADOWING | **0** |
| UNEXPECTED DELTA | **`[]`** |

Two route accounting systems, kept separate:

| | release index | served sitemap |
|---|---:|---:|
| parent | 2,807 | 2,874 |
| San Diego | +162 (147 hotel + 14 corridor + 1 hub) | +163 (+ the policy-comparison page) |
| **live now** | **2,969** | **3,037** |

The only test run was the supersession-chain contract class
`test_market_state_pins.py::TestTheSupersessionChainReachesProduction` — **4 passed**.

## 15 — DEPLOYMENT STATE FINALIZED (only after host verification passed)

| | |
|---|---|
| **AUTHORIZATION** | `ptf-auth-san-diego-003-553a858f2590`: **AUTHORIZED → DEPLOYED**, consumed; `status_history[-1].deployment_id = 6ab859787d349f8397e1450a`, consumed by this order |
| **deployment record** | `ptf-deploy-san-diego-004-6ab859787d349f8397e1450a` — `verify_record []`, final_status **DEPLOYED**, `rollback_used false`, `exit_status 0`; `work_order` = the authorizing order (…-FOUNDER-LAUNCH-AUTHORIZATION-003), `deployer.work_order` = this order |
| **live manifest** | `global_deployment_manifest.json` = the authorized bytes (Phase 7) |
| **deployment pin** | moved to `6ab859787d349f8397e1450a`; live and source agree, `ahead_of_production false` |
| **supersessions chain** | **30 → 31** — `reviewed_by` = this order; Jacksonville's entry is now historical (its 34 bound contracts re-hashed: **0 drift**); San Diego appended as CURRENT (35 bound contracts: **0 drift**) |
| **resolver** | `CURRENT_LIVE_SOURCE_COMMIT f01587ba`, built_from `34d523d9`, `live_deploy_id 6ab859787d349f8397e1450a`, 35 markets, 2,666 profiles, 3,037 routes, host verified |
| **SAN DIEGO PARTICIPATION** | `FOUNDER_AUTHORIZED_FOR_LAUNCH` (the canonical live state) — unchanged by this order; no other participation row touched |

## 16 — ROLLBACK

**ROLLBACK REQUIRED = NO.** No critical failure: no hash or sitemap mismatch, no San Diego route loss, no prior route
or profile loss, no held-property publication, no collision, no canonical violation, no unexpected delta, no
accounting mismatch. The rollback target `6ab6c8798bd9daf5038ae3e5` stands unused and is recorded in the pin and the
record.

## 17 — FINAL PRODUCTION ACCOUNTING

| | |
|---|---:|
| LIVE MARKETS | **35** |
| LIVE PROFILES | **2,666** |
| LIVE RELEASE-INDEX ROUTES | **2,969** |
| LIVE SERVED ROUTES | **3,037** |
| SAN DIEGO PROFILES LIVE | **147** |
| SAN DIEGO RELEASE-INDEX ROUTES | **162** |
| SAN DIEGO SERVED ROUTES | **163** |
| PRIOR MARKETS PRESERVED | **34 / 34** |
| PRIOR PROFILES / ROUTES LOST | **0 / 0** |

Processes: the Netlify CLI and the route sweeps exited on their own; nothing this order started remains. Pre-existing
node / python processes (started 2026-09-12 to 09-25) were left untouched.

---

## FINAL ANSWERS

```
 1. PREDEPLOY LIVE DEPLOYMENT              = 6ab6c8798bd9daf5038ae3e5 (jacksonville-fl)
 2. PREDEPLOY LIVE BUNDLE                  = f82f0714db2dd4d714b6b789c68492f60de8a1f3287a11b1e6f1afd680cf0c4e
 3. DEPLOYMENT AUTHORIZATION               = ptf-auth-san-diego-003-553a858f2590
 4. AUTHORIZATION STATUS BEFORE            = AUTHORIZED (unconsumed, no deploy_id)
 5. AUTHORIZED CANDIDATE BUNDLE            = 553a858f2590094127ce68e63992c2c3dff969fcdc8f290decf112791f447eec
 6. AUTHORIZED CANDIDATE SITEMAP           = 4f648fff6eaf50f7f7614eefda2639ac10c5cb678e77ef6fd15af60c89c0173e
 7. CANDIDATE INTEGRITY                    = PASS (exact authorization match; sd3a == sd3b over 16,202 files;
                                             0 broken links / collisions / shadowing / canonical violations)
 8. NETLIFY DEPLOYMENT ID                  = 6ab859787d349f8397e1450a
 9. NETLIFY RESULT                         = SUCCESS (exit 0, 84 s, 862 assets, --no-build, ready/production)
10. HOST SITEMAP MATCH                     = PASS
11. LIVE MARKETS                           = 35
12. LIVE PROFILES                          = 2,666
13. LIVE RELEASE-INDEX ROUTES              = 2,969
14. LIVE SERVED ROUTES                     = 3,037
15. SAN DIEGO PROFILES LIVE                = 147
16. SAN DIEGO RELEASE-INDEX ROUTES         = 162
17. SAN DIEGO SERVED ROUTES                = 163
18. SAN DIEGO ROUTES HTTP 200              = 163 / 163
19. NO-WEBSITE HOLDS PUBLISHED             = 0
20. DUAL-BRAND HOLDS PUBLISHED             = 0
21. OTHER HELD PROFILES ERRONEOUSLY LIVE   = 0
22. MISLEADING MULTI-AMOUNT FEES           = 0
23. PRIOR MARKETS LOST                     = 0
24. PRIOR PROFILES LOST                    = 0
25. PRIOR ROUTES LOST                      = 0 (2,874 / 2,874 HTTP 200)
26. DETROIT STILL WITHHELD                 = YES (404)
27. RULE J NONEMPTY                        = PASS
28. RULE K NONVACUOUS                      = PASS
29. BROKEN LINKS                           = 0
30. COLLISIONS                             = 0
31. CANONICAL VIOLATIONS                   = 0
32. GLOBAL SHADOWING                       = 0
33. UNEXPECTED DELTA                       = []
34. DEPLOYMENT AUTHORIZATION CONSUMED      = YES (AUTHORIZED -> DEPLOYED)
35. SAN DIEGO PARTICIPATION                = FOUNDER_AUTHORIZED_FOR_LAUNCH (live)
36. ROLLBACK REQUIRED                      = NO
37. CURRENT LIVE DEPLOYMENT                = 6ab859787d349f8397e1450a
38. CURRENT LIVE BUNDLE                    = 553a858f2590094127ce68e63992c2c3dff969fcdc8f290decf112791f447eec
39. origin == HEAD                         = YES (verified after the final push)
40. tree clean                             = YES (verified after the final push)
41. SAN DIEGO LIVE                         = YES
```

```
SAN DIEGO PRODUCTION DEPLOYMENT = PASS
LIVE MARKETS = 35
LIVE PROFILES = 2666
LIVE SERVED ROUTES = 3037
SAN DIEGO PROFILES LIVE = 147
SAN DIEGO ROUTES LIVE = 163
NO-WEBSITE HOLDS PUBLISHED = 0
DUAL-BRAND HOLDS PUBLISHED = 0
HELD SAN DIEGO PROFILES ERRONEOUSLY LIVE = 0
MISLEADING MULTI-AMOUNT FEES = 0
PRIOR MARKETS LOST = 0
PRIOR ROUTES LOST = 0
ROLLBACK REQUIRED = NO
SAN DIEGO LIVE = YES
```
