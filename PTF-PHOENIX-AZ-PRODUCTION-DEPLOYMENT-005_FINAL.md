# PTF-PHOENIX-AZ-PRODUCTION-DEPLOYMENT-005 — FINAL

**PHOENIX / SCOTTSDALE / VALLEY OF THE SUN, ARIZONA IS LIVE.** It is deploy **`6abc8387e81507b25eb94a0a`**: the exact
founder-authorized candidate `C:\t\phx4a`, deployed once with no rebuild. It is the first Arizona market.

- **Production now:** **37 markets / 3,210 profiles / 3,549 release-index routes / 3,619 served routes**.
- **Rollback:** not required.
- **Commit:** the deployment state is committed in `e2d45272`, which the resolver now reports as
  `CURRENT_LIVE_SOURCE_COMMIT`, built from `63e410ff`.
- **Branch:** `worker/ptf-phoenix-az-market-001`.

**Not done in this order:** no rebuild, no reseal, and no re-run of census, acquisition, registration or
authorization. No whole-site assembly and no broad regression; the only test run was the 4-test supersession-chain
contract class. No spend, no Places, no `identity_resolutions.json` write.

**Permission pause.** The first attempt at §9 (writing the live manifest) was blocked by the session's permission
classifier before anything was written or deployed. The order was re-issued, the parent was re-verified (§1, second
row), and only then did §9 and §10 run.

---

## 1 — PREDEPLOY PARENT (at the start, and again immediately before the manifest and the deploy)

| | |
|---|---|
| PREDEPLOY LIVE SOURCE COMMIT | `edf11b7a413903183cc59f4204de6066e93b52cf` (built_from `5bc62502`) |
| PREDEPLOY LIVE DEPLOYMENT | `6aba7587ddcc33a192bdf694` (denver-co) |
| PREDEPLOY LIVE BUNDLE | `7d3471c79e2d20d01c69e6dbd134bd3a5caec35e35967958f797decd06ee338a` |
| PREDEPLOY LIVE SITEMAP | `5d3d07a4c96563c0147cdca2ad0061ea437fee9748bc5cd3169eefe083712a2c` (3,343 `<loc>`, 0 Phoenix) |
| PREDEPLOY LIVE MARKETS / PROFILES | **36 / 2,954** |
| PREDEPLOY LIVE RELEASE-INDEX / SERVED ROUTES | **3,274 / 3,343** |
| HOST VERIFIED | **true** (02:30:23Z and again 03:34:25Z, immediately before §9) |

- **Baseline sweep:** all 3,343 live routes were fetched before the deploy: `total=3343 ok=3343`.
- **Host state:** Netlify `getSite` published deploy `6aba7587…`; `verify_target` returned `[]`.
- **Live artifact:** the live bundle and sitemap equal Denver's authorized artifact `C:\t\den4a`, and its fragments
  count 36 / 2,954 / 3,274.

## 2 — DEPLOYMENT AUTHORIZATION

| | |
|---|---|
| AUTHORIZATION | `ptf-auth-phoenix-004-19234b7affec` |
| STATUS BEFORE / CONSUMED / DEPLOY_ID | **AUTHORIZED / NO / NONE** (history PREPARED → AUTHORIZED) |
| MARKET | `phoenix-az`, in the bound set of 37 markets; 37 release contracts bound |
| AUTHORIZED PACKAGE | **`pkg-phoenix-az-07f7e75699af6a8c`**, named in `authorization_source` with its digest `sha256:07f7e756…0fccf` |
| AUTHORIZED BUNDLE / SITEMAP | `19234b7affec…1f78` / `647596dca769…2ecb` |
| AUTHORIZED SOURCE COMMIT | `63e410ff9cde676bd0621e2e1a7029bf54ff81bd` |
| AUTHORIZED PARENT / ROLLBACK TARGET | `6aba7587ddcc33a192bdf694` / `6aba7587ddcc33a192bdf694` |
| `verify_authorization` / `deployability_problems` | **`[]` / `[]`**, against the candidate manifest before §9 and against the live manifest after it |
| PRIOR PHOENIX PACKAGES | `pkg-phoenix-az-85ad9b66` and `pkg-phoenix-az-865822f4`: **no authorization binds either**. `ptf-auth-phoenix-004-19234b7affec` is the only authorization naming phoenix-az |
| existing Phoenix deployment records | **0** |

## 3 — CANDIDATE IDENTITY AND DETERMINISM (re-hashed from disk in this order)

| | Authorization | `C:\t\phx4a` | `C:\t\phx4b` |
|---|---|---|---|
| bundle (re-derived from every file) | `19234b7a…1f78` | **equal** | **equal** |
| sitemap | `647596dc…2ecb` | **equal** | **equal** |
| files on disk | 19,436 | 19,436 | 19,436 |
| `file_hash_manifest.json` mismatches / unlisted | — | 0 / 0 | 0 / 0 |
| `verify_bundle_directory` | — | **`[]`** | **`[]`** |
| markets / profiles / index / served | 37 / 3,210 / 3,549 / 3,619 | same | same |
| broken links · collisions · shadowing · canonical | — | **0 · 0 · 0 · 0**, `all_gates_pass true` | same |

- **Determinism:** the two trees differ in **0** of 19,436 files. The 004 evidence (BYTE_IDENTICAL) still holds.
- **Which tree shipped:** `phx4a`. `phx4b` was verification evidence only.

## 4 — DELTA / PRESERVATION (re-verified against current live `C:\t\den4a` before the deploy)

| | |
|---|---|
| FILES ADDED / REMOVED / CHANGED | **1,532 / 0 / 1**. All additions are Phoenix's; the one change is `sitemap.xml` |
| PRIOR-MARKET FILES CHANGED | **0** |
| PRIOR MARKETS / PROFILES / RELEASE-INDEX / SERVED ROUTES LOST | **0 / 0 / 0 / 0** |
| PHOENIX PROFILES / RELEASE-INDEX / SERVED ADDED | **256 / 275 / 276**, every served route under `/pet-friendly-hotels/phoenix-az/` |
| UNEXPECTED MARKET / PROFILE / ROUTE DELTA | **`[]` / `[]` / `[]`** (`release_diff_passed`, 0 findings) |
| REUSE | 36 bundles reused, 0 markets rebuilt, 1 Phoenix bundle |

The candidate accounting module reported `ALL_ACCOUNTING_GATES PASS` on this re-run (read-only, no `--write`).

## 5 — VACATION-OWNERSHIP SAFETY

| property | hotel profile | no-pets record | index route | served route | `/go/` | named on any Phoenix listing page |
|---|---|---|---|---|---|---|
| Club Wyndham Legacy Golf Resort | absent (404) | absent | absent | absent | 404 | no |
| Club Wyndham Orange Tree Resort | absent (404) | absent | absent | absent | 404 | no |
| WorldMark Phoenix - South Mountain Preserve | absent (404) | absent | absent | absent | 404 | no |
| WorldMark Scottsdale | absent (404) | absent | absent | absent | 404 | no |

- **Artifact:** 0 of 19,421 text files in the candidate name any of them.
- **Census:** each is a `NON_LODGING / TIMESHARE` row, outside the qualifying census and the exclusion registry.
- **Host:** checked on the hub, the policy-comparison page and all 18 corridor pages.
- **Result:** VACATION-OWNERSHIP HOTEL PROFILES LIVE **0**; VACATION-OWNERSHIP VERIFIED NO-PETS **0**.

## 6 — HELD / PREOPENING SAFETY

APPROVED PHOENIX PROFILES **256**. HELD / UNAPPROVED PHOENIX PROFILES IN CANDIDATE **0**.

The three not-yet-open hotels were checked on the host:

- ECHO Suites Phoenix-Chandler
- Home2 Suites by Hilton Peoria North Phoenix
- Vai Resort

Each profile returns 404, each `/go/` route returns 404, none has a served route, and none is named on the hub, the
comparison page or any corridor page.

## 7 — FEE SAFETY

49 supported single-basis fees publish. 77 tiered fees and 35 unsafe / missing-basis fees stay withheld. 113 published
records quote more than one amount; none of them publishes a single fee. **MISLEADING SINGLE FEES = 0.**

## 8 — CROSS-MARKET SAFETY

- **Collisions:** CROSS-MARKET **0**, BARE-CHAIN **0**, DUPLICATE EXCLUDED IDENTITIES **0** (1,386-row registry).
- **Existing markets:** no prior profile or route was displaced. Every prior market's files are byte-identical, and
  all 3,343 prior routes still return 200 (§12).

## 9 — LIVE MANIFEST

`global_deployment.write_manifest()` ran on `C:\t\phx4a\global_bundle_manifest.json` (the authorized bytes, not a
recomposition) immediately before the deploy.

- **What it describes:** bundle `19234b7a…`, sitemap `647596dc…`, **37 markets / 3,210 profiles / 3,619 routes**.
- **Checks:** `verify_manifest` returns `[]`, and the manifest is **identical** to the committed candidate manifest
  `global_deployment_manifest_candidate_phoenix_004.json`.

## 10 — THE DEPLOYMENT

```
netlify deploy --prod --no-build --dir C:\t\phx4a\site --site pettripfinder-prod

DEPLOY START          = 2026-09-30T03:35:06.70Z
DEPLOY COMPLETE       = 2026-09-30T03:36:16.90Z        EXIT STATUS = 0
NETLIFY DEPLOYMENT ID = 6abc8387e81507b25eb94a0a
DEPLOY URL            = https://pettripfinder.com
unique URL            = https://6abc8387e81507b25eb94a0a--pettripfinder-prod.netlify.app

CDN requesting 1534 files -> Finished uploading 1534 assets -> Deploy is live!
```

- **Build:** `--no-build`, so Netlify built nothing and no content was regenerated.
- **Runs:** one deploy command, run once, with no retry.
- **Lineage from Netlify's API:**
  - published deploy **`6abc8387e81507b25eb94a0a`**, `state: ready`, `context: production`, published at
    `2026-09-30T03:36:16.946Z`
  - the **previous** deploy is `6aba7587ddcc33a192bdf694`, the authorized parent

## 11 — HOST VERIFICATION (`phoenix_az_live_verification_005.json`, **15/15 PASS**)

| | |
|---|---|
| HOST SITEMAP SHA | `647596dca769c1b82c94e1c512ab04d87bbe729c07c1d06a49c2e11e5c652ecb` |
| HOST SITEMAP MATCH | **PASS** |
| SERVED ROUTE SET | **identical** to the authorized candidate's set |
| LIVE MARKETS | **37** (counted by each fragment's own hub route) |
| LIVE PROFILES | **3,210** |
| LIVE RELEASE-INDEX ROUTES | **3,549** |
| LIVE SERVED ROUTES | **3,619** |
| SAMPLED PAGES BYTE-IDENTICAL TO THE ARTIFACT | **25 / 25**: Phoenix hub, comparison page, 3 corridors, 6 hotels; 10 prior market hubs; apex, category root, robots.txt, llms.txt |

## 12 — ALL PHOENIX ROUTES, HELD ROWS AND PRIOR PRODUCTION

**All Phoenix routes.** The expected set came from the authorized candidate's own sitemap: every `<loc>` under
`/pet-friendly-hotels/phoenix-az/`, not arithmetic. Each was fetched once:

```
PHOENIX total=276 ok=276
```

| class (matched against the fragment's own route lists) | routes | in live sitemap | HTTP 200 |
|---|---:|---:|---:|
| hotel profiles | 256 | 256 | 256 |
| corridor pages | 18 | 18 | 18 |
| market hub | 1 | 1 | 1 |
| policy-comparison | 1 | 1 | 1 |
| **total** | **276** | **276** | **276** |

- **Missing:** PHOENIX ROUTES MISSING = **0**.
- **Refused places:** no live Phoenix route names Sedona, Flagstaff, the Grand Canyon, Prescott or Tucson.

**Held Phoenix identities in production.** Every unpublished census row was probed, exhaustively rather than sampled,
at both its census slug and the site's slug form: 265 URLs for 228 rows.

| group | rows | URLs probed | returning 200 |
|---|---:|---:|---:|
| Places-gated | 48 | 52 | **0** |
| dual-brand / shared-campus halves | 28 | 32 | **0** |
| redirect-domain founder-decision | 2 | 2 | **0** |
| router-exhausted / evidence / source-silent | 88 | 98 | **0** |
| preopening | 3 | 3 | **0** |
| other held | 0 | 0 | **0** |
| verified-no-pets (as profiles) | 59 | 78 | **0** |
| **total** | **228** | **265** | **0**, all 404 |

APPROVED PHOENIX PROFILES LIVE = **256**. HELD / UNAPPROVED PHOENIX PROFILES ERRONEOUSLY LIVE = **0**.

**Prior production.** All 3,343 prior served routes were re-fetched after the deploy.

- **First sweep:** `ok=3207`. The other 136 got **no HTTP response at all** (curl code `000`, not a 4xx or 5xx). They
  were one contiguous alphabetical run, the end of `st-louis-mo` through `tampa-fl`, which is the signature of a
  client-side connection gap.
- **Those 136 refetched:** **136 / 136 HTTP 200**.
- **Second full sweep** (all 3,343, with a per-request timeout), which is the sweep of record:

```
PRIOR total=3343 ok=3343
```

The host never served an error, so no rollback condition occurred. PRIOR MARKETS LOST **0** (36 / 36 preserved).
PRIOR PROFILES LOST **0**. PRIOR SERVED ROUTES LOST **0**.

| representative market | status |
|---|---|
| Denver | **200** |
| San Diego | **200** |
| Jacksonville FL | **200** |
| West Palm Beach | **200** |
| Fort Lauderdale | **200** |
| Augusta | **200** |
| Miami | **200** |
| Tampa | **200** |
| Orlando | **200** |
| Cleveland–Akron–Canton | **200** |
| Jacksonville NC | **200** (route set unchanged) |
| Phoenix hub | **200** |
| Detroit | **404**, still withheld |

## 13 — FAST / RECEIPT SAFETY

- **Phoenix's receipt:** `pkg-phoenix-az-07f7e75699af6a8c-b3679c3f11e56c1c.json` is **currently eligible**.
  - RULE J **PASS**: 1,553 files, 1,537 HTML, bundle `ea2a8d31…`, 0 defects.
  - RULE K **PASS**: BYTE_IDENTICAL.
- **Augusta's historical empty receipt:** unmodified and still **ineligible** (`EMPTY_BUNDLE`, `NO_HTML_OUTPUT`). No
  vacuous receipt qualifies.

## 14 — POSTDEPLOY QUALITY (bounded; no broad regression)

| | |
|---|---:|
| BROKEN LINKS | **0** |
| COLLISIONS | **0** |
| CANONICAL VIOLATIONS | **0** |
| GLOBAL SHADOWING | **0** |
| UNEXPECTED DELTA | **`[]`** |

Two route-accounting systems, kept separate:

| | release index | served sitemap |
|---|---:|---:|
| parent | 3,274 | 3,343 |
| Phoenix | +275 (256 hotel + 18 corridor + 1 hub) | +276 (+ the policy-comparison page) |
| **live now** | **3,549** | **3,619** |

The only test run was `tests/pettripfinder/contracts/test_market_state_pins.py::TestTheSupersessionChainReachesProduction`:
**4 passed**.

## 15 — DEPLOYMENT STATE FINALIZED (only after host verification passed)

| | |
|---|---|
| **AUTHORIZATION** | `ptf-auth-phoenix-004-19234b7affec`: **AUTHORIZED → DEPLOYED**, consumed; `status_history[-1].deployment_id = 6abc8387e81507b25eb94a0a`. No deployable Phoenix authorization remains |
| **deployment record** | `ptf-deploy-phoenix-005-6abc8387e81507b25eb94a0a`: `verify_record []`, final_status **DEPLOYED**, `rollback_used false`, `exit_status 0`. `work_order` is the authorizing order (…-FOUNDER-LAUNCH-AUTHORIZATION-004); `deployer.work_order` is this order |
| **live manifest** | `global_deployment_manifest.json` is the authorized bytes (§9) |
| **deployment pin** | moved to `6abc8387e81507b25eb94a0a`; live and source agree, `ahead_of_production false`, rollback `6aba7587ddcc33a192bdf694` |
| **supersessions chain** | **32 → 33**, `reviewed_by` this order. Denver's entry is now historical (36 bound contracts re-hashed: **0 drift**). Phoenix is appended as CURRENT (37 bound contracts: **0 drift**) |
| **resolver** | `CURRENT_LIVE_SOURCE_COMMIT e2d45272`, built_from `63e410ff`, `live_deploy_id 6abc8387e81507b25eb94a0a`, 37 markets, 3,210 profiles, 3,619 routes, host verified |
| **PHOENIX PARTICIPATION** | `FOUNDER_AUTHORIZED_FOR_LAUNCH` (the canonical live state), unchanged by this order. No other participation row was touched |

## 16 — ROLLBACK

**ROLLBACK REQUIRED = NO.** There was no critical failure:

- no bundle or served-sitemap mismatch
- no Phoenix route loss, prior-route loss or prior-profile loss
- no held-property, vacation-ownership or preopening publication
- no collision, canonical violation, unexpected delta or accounting mismatch

The rollback target `6aba7587ddcc33a192bdf694` stands unused and is recorded in the pin and the record.

## 17 — FINAL PRODUCTION ACCOUNTING

| | |
|---|---:|
| LIVE MARKETS | **37** |
| LIVE PROFILES | **3,210** |
| LIVE RELEASE-INDEX ROUTES | **3,549** |
| LIVE SERVED ROUTES | **3,619** |
| PHOENIX PROFILES LIVE | **256** |
| PHOENIX RELEASE-INDEX ROUTES | **275** |
| PHOENIX SERVED ROUTES | **276** |
| PRIOR MARKETS PRESERVED | **36 / 36** |
| PRIOR PROFILES / ROUTES LOST | **0 / 0** |

**Processes.** The byte walk, the accounting re-run, the Netlify CLI and the route sweeps all exited on their own;
nothing this order started remains. The pre-existing `C:\t\sink.py` process was left untouched.

---

## FINAL ANSWERS

```
 1. PREDEPLOY LIVE DEPLOYMENT              = 6aba7587ddcc33a192bdf694 (denver-co)
 2. PREDEPLOY LIVE BUNDLE                  = 7d3471c79e2d20d01c69e6dbd134bd3a5caec35e35967958f797decd06ee338a
 3. DEPLOYMENT AUTHORIZATION               = ptf-auth-phoenix-004-19234b7affec
 4. AUTHORIZATION STATUS BEFORE            = AUTHORIZED (unconsumed, no deploy_id)
 5. AUTHORIZED PACKAGE                     = pkg-phoenix-az-07f7e75699af6a8c
 6. AUTHORIZED CANDIDATE BUNDLE            = 19234b7affec61c16d6ac40e864e83a4c497262b2451eba2d03821482e9a1f78
 7. AUTHORIZED CANDIDATE SITEMAP           = 647596dca769c1b82c94e1c512ab04d87bbe729c07c1d06a49c2e11e5c652ecb
 8. CANDIDATE INTEGRITY                    = PASS (both trees re-hash to the authorized bundle; 19,436 files,
                                             0 differing; 0 manifest mismatches; 0 broken links / collisions /
                                             shadowing / canonical violations)
 9. NETLIFY DEPLOYMENT ID                  = 6abc8387e81507b25eb94a0a
10. NETLIFY RESULT                         = SUCCESS (exit 0, 1,534 assets, --no-build, ready / production)
11. HOST SITEMAP MATCH                     = PASS
12. LIVE MARKETS                           = 37
13. LIVE PROFILES                          = 3,210
14. LIVE RELEASE-INDEX ROUTES              = 3,549
15. LIVE SERVED ROUTES                     = 3,619
16. PHOENIX PROFILES LIVE                  = 256
17. PHOENIX RELEASE-INDEX ROUTES           = 275
18. PHOENIX SERVED ROUTES                  = 276
19. PHOENIX ROUTES HTTP 200                = 276 / 276
20. VACATION-OWNERSHIP HOTEL PROFILES LIVE = 0
21. VACATION-OWNERSHIP VERIFIED NO-PETS    = 0
22. PLACES-GATED HOLDS PUBLISHED           = 0 (of 48)
23. DUAL-BRAND HOLDS PUBLISHED             = 0 (of 28)
24. REDIRECT-DOMAIN HOLDS PUBLISHED        = 0 (of 2)
25. PREOPENING PROFILES PUBLISHED          = 0 (of 3)
26. OTHER HELD PHOENIX PROFILES ERRONEOUSLY LIVE = 0 (all 228 unpublished rows 404 at both slug forms)
27. MISLEADING SINGLE FEES                 = 0
28. PRIOR MARKETS LOST                     = 0
29. PRIOR PROFILES LOST                    = 0
30. PRIOR ROUTES LOST                      = 0 (3,343 / 3,343 HTTP 200)
31. DETROIT STILL WITHHELD                 = YES (404)
32. RULE J NONEMPTY                        = PASS
33. RULE K NONVACUOUS                      = PASS
34. BROKEN LINKS                           = 0
35. COLLISIONS                             = 0
36. CANONICAL VIOLATIONS                   = 0
37. GLOBAL SHADOWING                       = 0
38. UNEXPECTED DELTA                       = []
39. DEPLOYMENT AUTHORIZATION CONSUMED      = YES (AUTHORIZED -> DEPLOYED)
40. PHOENIX PARTICIPATION                  = FOUNDER_AUTHORIZED_FOR_LAUNCH (live)
41. ROLLBACK REQUIRED                      = NO
42. CURRENT LIVE DEPLOYMENT                = 6abc8387e81507b25eb94a0a
43. CURRENT LIVE BUNDLE                    = 19234b7affec61c16d6ac40e864e83a4c497262b2451eba2d03821482e9a1f78
44. origin == HEAD                         = YES (verified after the final push)
45. tree clean                             = YES (verified after the final push)
46. PHOENIX LIVE                           = YES
```

```
PHOENIX PRODUCTION DEPLOYMENT = PASS
LIVE MARKETS = 37
LIVE PROFILES = 3210
LIVE SERVED ROUTES = 3619
PHOENIX PROFILES LIVE = 256
PHOENIX ROUTES LIVE = 276
VACATION-OWNERSHIP HOTEL PROFILES LIVE = 0
VACATION-OWNERSHIP VERIFIED NO-PETS = 0
PLACES-GATED HOLDS PUBLISHED = 0
DUAL-BRAND HOLDS PUBLISHED = 0
PREOPENING PROFILES PUBLISHED = 0
HELD PHOENIX PROFILES ERRONEOUSLY LIVE = 0
MISLEADING SINGLE FEES = 0
PRIOR MARKETS LOST = 0
PRIOR ROUTES LOST = 0
ROLLBACK REQUIRED = NO
PHOENIX LIVE = YES
```
