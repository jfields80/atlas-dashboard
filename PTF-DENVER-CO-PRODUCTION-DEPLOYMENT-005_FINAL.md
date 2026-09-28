# PTF-DENVER-CO-PRODUCTION-DEPLOYMENT-005 — FINAL

**DENVER / BOULDER / FRONT RANGE, COLORADO IS LIVE.** It is deploy **`6aba7587ddcc33a192bdf694`**: the exact
founder-authorized candidate, deployed once with no rebuild. It is the first Colorado market.

- **Production now:** **36 markets / 2,954 profiles / 3,274 release-index routes / 3,343 served routes**.
- **Rollback:** not required.
- **Commit:** the deployment state is committed in `edf11b7a`, which the resolver now reports as
  `CURRENT_LIVE_SOURCE_COMMIT`, built from `5bc62502`.
- **Branch:** `worker/ptf-denver-co-market-001`.

**Not done in this order:** no rebuild, no reseal, and no re-run of registration, authorization or acquisition. No
whole-site assembly and no broad regression; the only test run was a 4-test chain contract class. No spend, no
Places, no `identity_resolutions.json` write and no ESA display name.

---

## 1 — PREDEPLOY PARENT (at the start and again immediately before the call)

| | |
|---|---|
| PREDEPLOY LIVE SOURCE COMMIT | `f01587ba7d23a849e0c07b3cddd3250717e63b80` (built_from `34d523d9`) |
| PREDEPLOY LIVE DEPLOYMENT | `6ab859787d349f8397e1450a` (san-diego-ca) |
| PREDEPLOY LIVE BUNDLE | `553a858f2590094127ce68e63992c2c3dff969fcdc8f290decf112791f447eec` |
| PREDEPLOY LIVE SITEMAP | `4f648fff6eaf50f7f7614eefda2639ac10c5cb678e77ef6fd15af60c89c0173e` |
| PREDEPLOY LIVE MARKETS / PROFILES | **35 / 2,666** |
| PREDEPLOY LIVE RELEASE-INDEX / SERVED ROUTES | **2,969 / 3,037** |
| HOST VERIFIED | **true** |

- **Baseline sweep:** all 3,037 live routes were fetched before the deploy, `total=3037 ok=3037 bad=0 lines=3037`.
- **Live artifact:** the live sitemap equals the sitemap of San Diego's authorized artifact `C:\t\sd3a`.
- **Parent had not advanced:** re-checked immediately before the deploy.

## 2 — DEPLOYMENT AUTHORIZATION

| | |
|---|---|
| AUTHORIZATION | `ptf-auth-denver-004-7d3471c79e2d` |
| STATUS BEFORE / CONSUMED / DEPLOY_ID | **AUTHORIZED / NO / NONE** (history PREPARED → AUTHORIZED) |
| MARKET | `denver-co`, in the bound set of 36 markets; 36 release contracts bound |
| AUTHORIZED PACKAGE | **`pkg-denver-co-07f10db29ab56d98`** (`sha256:07f10db2…6707`) — bound through `launch_participation_sha256` `25ea6f31…`, whose founder decision basis names exactly this package |
| OLD 289-PROFILE PACKAGE `pkg-denver-co-91b2e0a2` | **NOT authorized** — no authorization binds its digest; it appears only as the founder's "DO NOT AUTHORIZE" text |
| AUTHORIZED BUNDLE | `7d3471c79e2d20d01c69e6dbd134bd3a5caec35e35967958f797decd06ee338a` |
| AUTHORIZED SITEMAP | `5d3d07a4c96563c0147cdca2ad0061ea437fee9748bc5cd3169eefe083712a2c` |
| AUTHORIZED SOURCE COMMIT | `5bc62502a74407af6c9eadc7b5325c1ea521cccb` |
| AUTHORIZED PARENT / ROLLBACK TARGET | `6ab859787d349f8397e1450a` / `6ab859787d349f8397e1450a` |
| existing Denver deployment records | **0** |

**`verify_authorization` before the manifest step.** It was first checked against the committed live manifest, which
still described San Diego production. That returned 14 problems, which is the documented ordering.

Checked against the candidate's own manifest, it returned **`[]`**, and `deployability_problems` returned **`[]`**.
After §9 wrote the live manifest from the authorized bytes, both returned **`[]`**.

## 3 — CANDIDATE IDENTITY AND DETERMINISM

| | Authorization | `C:\t\den4a` | `C:\t\den4b` |
|---|---|---|---|
| bundle | `7d3471c7…338a` | **equal** | **equal** |
| sitemap | `5d3d07a4…2a2c` | **equal** (re-hashed from `site/sitemap.xml`) | **equal** |
| files / HTML pages | 17,904 / 17,886 | 17,904 on disk | 17,904 on disk |
| markets / profiles / index routes / served routes | 36 / 2,954 / 3,274 / 3,343 | same | same |
| Denver | — | 288 hotel / 16 corridor / hub / policy-comparison (305 index, 306 served) | same |
| broken links · collisions · shadowing · canonical violations | — | **0 · 0 · 0 · 0**, `all_gates_pass true` | same |

- **Byte walk:** a full byte walk re-ran in this order. Each tree has 17,904 files on disk, and each matches its own
  `file_hash_manifest.json` (0 mismatches, 0 unlisted files). The two trees differ in **0** files, so the
  authorization order's determinism evidence still holds.
- **Control files:** `_headers`, `_redirects`, `robots.txt` and `llms.txt` are present and byte-identical to the live
  artifact's.
- **Which tree shipped:** `den4a` was deployed; `den4b` was verification evidence only.

## 4 — DELTA / PRESERVATION (re-verified mechanically before the deploy)

| | |
|---|---|
| FILES ADDED / REMOVED / CHANGED | **1,702 / 0 / 1**. All 1,702 additions are under `pet-friendly-hotels/denver-co/` and `go/denver-co/`; the one change is `sitemap.xml` (global, regenerated every release) |
| PRIOR-MARKET FILES CHANGED / UNCLASSIFIED PATHS | **0 / 0** |
| PRIOR MARKETS / PROFILES / RELEASE-INDEX / SERVED ROUTES LOST | **0 / 0 / 0 / 0** |
| DENVER SERVED ROUTES ADDED | **306**, every one under `/pet-friendly-hotels/denver-co/` |
| UNEXPECTED MARKET / PROFILE / ROUTE DELTA | **`[]` / `[]` / `[]`** (`release_diff_passed`, 0 findings) |

`index.html` and `pet-friendly-hotels/index.html` are byte-identical to live, because a new market ships hidden from
global navigation.

## 5 — ECHO SUITES PREOPENING SAFETY

`ECHO Suites Denver North - Thornton - Opening Early 2027` (13560 Grant St) was checked on the candidate and on the
production host:

- **Profile:** `/pet-friendly-hotels/denver-co/echo-suites-denver-north-thornton-opening-early-2027/` returns **404**
  and is absent from the artifact.
- **Served route:** **absent**.
- **Release-index route:** **absent**.
- **`/go/` route:** `/go/denver-co/echo-suites-denver-north-thornton-opening-early-2027/` returns **404**.
- **Page text:** **absent**. No hit on the Denver hub, the policy-comparison page or the Thornton corridor page. In the
  candidate, 0 of 17,904 files mention it.

It stays held with its evidence untouched, for revalidation once it opens.

## 6 — HELD PROFILE SAFETY

| | |
|---:|---:|
| APPROVED DENVER PROFILES | **288** |
| HELD / UNAPPROVED DENVER PROFILES IN CANDIDATE | **0** |

Checked on the artifact first (no page, sitemap route, index route or `/go/` file) and then on the production host
(§11). `identity_resolutions.json` was not written and no ESA display name was invented.

## 7 — FEE SAFETY

54 single-basis fees publish. 80 tiered fees and 35 unsafe single fees stay withheld. 103 published records quote more
than one amount, and **0** of them publish a single fee. **MISLEADING SINGLE FEES = 0.**

## 8 — CROSS-MARKET SAFETY

- **Collisions:** CROSS-MARKET COLLISIONS **0**, BARE-CHAIN **0**, DUPLICATE EXCLUDED IDENTITIES **0** (1,327-row
  registry).
- **Existing markets:** no live market or profile moved. Every prior market's files are byte-identical, and all 3,037
  prior routes still return 200 (§12).

## 9 — LIVE MANIFEST

`global_deployment.write_manifest()` ran on `C:\t\den4a\global_bundle_manifest.json`, the authorized bytes rather than
a recomposition, immediately before the deploy.

- **What it describes:** bundle `7d3471c7…`, sitemap `5d3d07a4…`, **36 markets / 2,954 profiles / 3,343 routes**,
  source `5bc62502`.
- **Checks:** `verify_manifest` returns `[]`, and the manifest is **identical** to the committed candidate manifest
  `global_deployment_manifest_candidate_denver_004.json`.

## 10 — THE DEPLOYMENT

```
netlify deploy --prod --no-build --dir C:\t\den4a\site --site pettripfinder-prod

DEPLOY START          = 2026-09-28T14:10:29.23Z
DEPLOY COMPLETE       = 2026-09-28T14:17:02.06Z        EXIT STATUS = 0
NETLIFY DEPLOYMENT ID = 6aba7587ddcc33a192bdf694
DEPLOY URL            = https://pettripfinder.com
unique URL            = https://6aba7587ddcc33a192bdf694--pettripfinder-prod.netlify.app

CDN requesting 1704 files -> Finished uploading 1704 assets -> Deploy is live!
```

- **Build:** `--no-build`, so Netlify built nothing and no content was regenerated.
- **Runs:** one deploy command, run once, with no retry.
- **Upload count:** Netlify uploaded 1,704 files. That is its diff against its own stored deploy state, not the
  artifact delta (1,702 + 1); what is served is verified below.
- **Lineage from Netlify's API:**
  - published deploy **`6aba7587ddcc33a192bdf694`**, `state: ready`, `context: production`, published at
    `2026-09-28T14:12:02.160Z`
  - the **previous** deploy is `6ab859787d349f8397e1450a`, the authorized parent

## 11 — HOST VERIFICATION (`denver_co_live_verification_005.json`, **14/14 PASS**)

| | |
|---|---|
| HOST SITEMAP SHA | `5d3d07a4c96563c0147cdca2ad0061ea437fee9748bc5cd3169eefe083712a2c` |
| HOST SITEMAP MATCH | **PASS** (equals the authorized sitemap sha) |
| SERVED ROUTE SET | **identical** to the authorized candidate's set |
| LIVE MARKETS | **36** (counted by each fragment's own hub route) |
| LIVE PROFILES | **2,954** |
| LIVE RELEASE-INDEX ROUTES | **3,274** |
| LIVE SERVED ROUTES | **3,343** |
| SAMPLED PAGES BYTE-IDENTICAL TO THE ARTIFACT | **24 / 24**: Denver hub, comparison page, 3 corridors, 6 hotels; 9 prior market hubs; apex, category root, robots.txt, llms.txt |

**Held Denver identities in production.** Every unpublished census row was probed, exhaustively rather than sampled.
Each was probed at **both** its census slug and the site's slug form, because the site drops "and" — 180 URLs for 153
rows.

| group | rows | URLs probed | returning 200 |
|---|---:|---:|---:|
| Places-gated / no-website | 52 | 54 | **0** |
| founder-decision (14 dual-brand halves + 2 ESA title collisions) | 16 | 20 | **0** |
| router-exhausted | 38 | 43 | **0** |
| ECHO preopening | 1 | 1 | **0** |
| verified-no-pets (as profiles) | 46 | 62 | **0** |
| **total** | **153** | **180** | **0**, all 404 |

APPROVED DENVER PROFILES LIVE = **288**. HELD / UNAPPROVED DENVER PROFILES ERRONEOUSLY LIVE = **0**.

## 12 — ALL DENVER ROUTES, AND PRIOR PRODUCTION

**All Denver routes.** The expected Denver set came from the authorized candidate's own sitemap: every `<loc>` under
`/pet-friendly-hotels/denver-co/`, not arithmetic. Each was fetched once.

```
DENVER total=306 ok=306 bad=0 lines=306
```

| class (matched against the fragment's own route lists) | routes | HTTP 200 |
|---|---:|---:|
| hotel profiles | 288 | 288 |
| corridor pages | 16 | 16 |
| market hub | 1 | 1 |
| policy-comparison | 1 | 1 |
| **total** | **306** | **306** |

- **Publishing corridors:** aurora, boulder, central-park-lowry-i70, cherry-creek-glendale, den-airport,
  denver-tech-center, downtown-lodo-union-station, golden-red-rocks, highlands-rino-north-denver,
  lakewood-wheat-ridge, littleton-englewood, longmont-erie, louisville-superior-lafayette, parker-southeast,
  thornton-northglenn-north-i25, westminster-broomfield.
- **Missing:** DENVER ROUTES MISSING = **0**.
- **Refused places:** no live Denver route names a refused place (Colorado Springs, Fort Collins / Loveland, Estes
  Park, the ski resorts, Castle Rock, Greeley, Pueblo, Cheyenne, Firestone).

**Prior production.** All 3,037 prior served routes were re-fetched after the deploy, in one sweep that recorded every
status:

```
PRIOR total=3037 ok=3037 bad=0 lines=3037
```

PRIOR MARKETS LOST **0** (35 / 35 preserved). PRIOR PROFILES LOST **0**. PRIOR SERVED ROUTES LOST **0**.

| representative market | status |
|---|---|
| San Diego | **200** |
| Jacksonville FL | **200** |
| West Palm Beach | **200** |
| Fort Lauderdale | **200** |
| Augusta | **200** |
| Miami | **200** |
| Tampa | **200** |
| Orlando | **200** |
| Cleveland–Akron–Canton | **200** |
| Jacksonville NC | **200** (route set 19 → 19, unchanged) |
| Denver hub | **200** |
| Detroit | **404**, still withheld |

## 13 — FAST / RECEIPT SAFETY

- **Denver's receipt:** `pkg-denver-co-07f10db29ab56d98-d3f8fea6996a6fcb.json` is **currently eligible** under
  today's reader.
  - RULE J **PASS**: 1,723 files, 1,707 HTML, bundle `475633a2…`, 0 output defects.
  - RULE K **PASS**: BYTE_IDENTICAL.
- **Augusta's historical empty receipt:** unmodified and still **ineligible** (`EMPTY_BUNDLE`, `NO_HTML_OUTPUT`).

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
| parent | 2,969 | 3,037 |
| Denver | +305 (288 hotel + 16 corridor + 1 hub) | +306 (+ the policy-comparison page) |
| **live now** | **3,274** | **3,343** |

The only test run was the supersession-chain contract class
`tests/pettripfinder/contracts/test_market_state_pins.py::TestTheSupersessionChainReachesProduction`: **4 passed**.

## 15 — DEPLOYMENT STATE FINALIZED (only after host verification passed)

| | |
|---|---|
| **AUTHORIZATION** | `ptf-auth-denver-004-7d3471c79e2d`: **AUTHORIZED → DEPLOYED**, consumed. `status_history[-1].deployment_id = 6aba7587ddcc33a192bdf694`, consumed by this order. No deployable authorization remains |
| **deployment record** | `ptf-deploy-denver-005-6aba7587ddcc33a192bdf694`: `verify_record []`, final_status **DEPLOYED**, `rollback_used false`, `exit_status 0`. `work_order` is the authorizing order (…-FOUNDER-LAUNCH-AUTHORIZATION-004); `deployer.work_order` is this order |
| **live manifest** | `global_deployment_manifest.json` is the authorized bytes (§9) |
| **deployment pin** | moved to `6aba7587ddcc33a192bdf694`; live and source agree, `ahead_of_production false`, rollback `6ab859787d349f8397e1450a` |
| **supersessions chain** | **31 → 32**, `reviewed_by` this order. San Diego's entry is now historical (its 35 bound contracts re-hashed: **0 drift**). Denver is appended as CURRENT (36 bound contracts: **0 drift**) |
| **resolver** | `CURRENT_LIVE_SOURCE_COMMIT edf11b7a`, built_from `5bc62502`, `live_deploy_id 6aba7587ddcc33a192bdf694`, 36 markets, 2,954 profiles, 3,343 routes, host verified |
| **DENVER PARTICIPATION** | `FOUNDER_AUTHORIZED_FOR_LAUNCH` (the canonical live state), unchanged by this order. No other participation row was touched |

The Denver copies of the record and authorization writers read market ids out of the `participating_markets` records.
The San Diego modules they were cloned from tested a bare id against those records, so their "other deployable
authorization" refusal could never fire.

## 16 — ROLLBACK

**ROLLBACK REQUIRED = NO.** There was no critical failure:

- no candidate hash or served-sitemap mismatch
- no Denver route loss, prior-route loss or prior-profile loss
- no held-property or ECHO publication
- no collision, canonical violation, unexpected delta or accounting mismatch

The rollback target `6ab859787d349f8397e1450a` stands unused and is recorded in the pin and the record.

## 17 — FINAL PRODUCTION ACCOUNTING

| | |
|---|---:|
| LIVE MARKETS | **36** |
| LIVE PROFILES | **2,954** |
| LIVE RELEASE-INDEX ROUTES | **3,274** |
| LIVE SERVED ROUTES | **3,343** |
| DENVER PROFILES LIVE | **288** |
| DENVER RELEASE-INDEX ROUTES | **305** |
| DENVER SERVED ROUTES | **306** |
| PRIOR MARKETS PRESERVED | **35 / 35** |
| PRIOR PROFILES / ROUTES LOST | **0 / 0** |

**Processes.** The Netlify CLI, the byte walk and the route sweeps exited on their own, and nothing this order started
remains. The pre-existing `C:\t\sink.py` process (started 2026-09-14) was left untouched.

---

## FINAL ANSWERS

```
 1. PREDEPLOY LIVE DEPLOYMENT              = 6ab859787d349f8397e1450a (san-diego-ca)
 2. PREDEPLOY LIVE BUNDLE                  = 553a858f2590094127ce68e63992c2c3dff969fcdc8f290decf112791f447eec
 3. DEPLOYMENT AUTHORIZATION               = ptf-auth-denver-004-7d3471c79e2d
 4. AUTHORIZATION STATUS BEFORE            = AUTHORIZED (unconsumed, no deploy_id)
 5. AUTHORIZED PACKAGE                     = pkg-denver-co-07f10db29ab56d98
 6. OLD 289-PROFILE PACKAGE AUTHORIZED     = NO
 7. AUTHORIZED CANDIDATE BUNDLE            = 7d3471c79e2d20d01c69e6dbd134bd3a5caec35e35967958f797decd06ee338a
 8. AUTHORIZED CANDIDATE SITEMAP           = 5d3d07a4c96563c0147cdca2ad0061ea437fee9748bc5cd3169eefe083712a2c
 9. CANDIDATE INTEGRITY                    = PASS (exact authorization match; den4a == den4b over 17,904 files;
                                             0 manifest mismatches; 0 broken links / collisions / shadowing /
                                             canonical violations)
10. NETLIFY DEPLOYMENT ID                  = 6aba7587ddcc33a192bdf694
11. NETLIFY RESULT                         = SUCCESS (exit 0, 1,704 assets, --no-build, ready / production)
12. HOST SITEMAP MATCH                     = PASS
13. LIVE MARKETS                           = 36
14. LIVE PROFILES                          = 2,954
15. LIVE RELEASE-INDEX ROUTES              = 3,274
16. LIVE SERVED ROUTES                     = 3,343
17. DENVER PROFILES LIVE                   = 288
18. DENVER RELEASE-INDEX ROUTES            = 305
19. DENVER SERVED ROUTES                   = 306
20. DENVER ROUTES HTTP 200                 = 306 / 306
21. ECHO PREOPENING PROFILE LIVE           = NO (404; no route, /go/ route or page text)
22. DUAL-BRAND HOLDS PUBLISHED             = 0 (of 14)
23. ESA HOLDS PUBLISHED                    = 0 (of 2)
24. OTHER HELD DENVER PROFILES ERRONEOUSLY LIVE = 0 (all 153 unpublished rows 404 at both slug forms)
25. MISLEADING SINGLE FEES                 = 0
26. PRIOR MARKETS LOST                     = 0
27. PRIOR PROFILES LOST                    = 0
28. PRIOR ROUTES LOST                      = 0 (3,037 / 3,037 HTTP 200)
29. DETROIT STILL WITHHELD                 = YES (404)
30. RULE J NONEMPTY                        = PASS
31. RULE K NONVACUOUS                      = PASS
32. BROKEN LINKS                           = 0
33. COLLISIONS                             = 0
34. CANONICAL VIOLATIONS                   = 0
35. GLOBAL SHADOWING                       = 0
36. UNEXPECTED DELTA                       = []
37. DEPLOYMENT AUTHORIZATION CONSUMED      = YES (AUTHORIZED -> DEPLOYED)
38. DENVER PARTICIPATION                   = FOUNDER_AUTHORIZED_FOR_LAUNCH (live)
39. ROLLBACK REQUIRED                      = NO
40. CURRENT LIVE DEPLOYMENT                = 6aba7587ddcc33a192bdf694
41. CURRENT LIVE BUNDLE                    = 7d3471c79e2d20d01c69e6dbd134bd3a5caec35e35967958f797decd06ee338a
42. origin == HEAD                         = YES (verified after the final push)
43. tree clean                             = YES (verified after the final push)
44. DENVER LIVE                            = YES
```

```
DENVER PRODUCTION DEPLOYMENT = PASS
LIVE MARKETS = 36
LIVE PROFILES = 2954
LIVE SERVED ROUTES = 3343
DENVER PROFILES LIVE = 288
DENVER ROUTES LIVE = 306
OLD 289-PROFILE PACKAGE AUTHORIZED = NO
ECHO SUITES PREOPENING PROFILE LIVE = NO
DUAL-BRAND HOLDS PUBLISHED = 0
ESA HOLDS PUBLISHED = 0
HELD DENVER PROFILES ERRONEOUSLY LIVE = 0
MISLEADING SINGLE FEES = 0
PRIOR MARKETS LOST = 0
PRIOR ROUTES LOST = 0
ROLLBACK REQUIRED = NO
DENVER LIVE = YES
```
