# PTF-SAN-DIEGO-CA-FOUNDER-LAUNCH-AUTHORIZATION-003 — FINAL

`san-diego-ca` (San Diego / Coastal San Diego County) is **FOUNDER_AUTHORIZED_FOR_LAUNCH**, and the exact
authorized production candidate is built, proven byte-identical twice, and bound to a deployment authorization that
is **AUTHORIZED and UNCONSUMED**. Branch `worker/ptf-san-diego-ca-market-001`: founder decision `34d523d9`,
candidate + authorization in the commit that carries this report.

**Not deployed.** No Netlify invocation, no deployment record, no LIVE flag, no consumption of the authorization.
Current live untouched. No acquisition re-run, no broad regression, no spend, no Places lookups, no
`identity_resolutions.json` write.

---

## PHASE 1 — CURRENT LIVE (reverified; not advanced since registration)

`release_index live-source --verify-host` at 17:59Z and again at 19:57Z:

| | |
|---|---|
| CURRENT LIVE SOURCE COMMIT | `e9a059e50c88d011bd708a28dbd25a6fffece461` (built_from `e7e02d43`) |
| CURRENT LIVE DEPLOYMENT | `6ab6c8798bd9daf5038ae3e5` (jacksonville-fl), rollback `6ab599163f833ab7f48b395d` |
| CURRENT LIVE BUNDLE | `f82f0714db2dd4d714b6b789c68492f60de8a1f3287a11b1e6f1afd680cf0c4e` |
| CURRENT LIVE SITEMAP | `d34b0e5d7d5ed045a3f727e49f18e2fe61de3df108e9ef0666c5413d1bb48e4f` |
| CURRENT LIVE MARKETS | **34** |
| CURRENT LIVE PROFILES | **2,519** |
| CURRENT LIVE RELEASE-INDEX ROUTES | **2,807** |
| CURRENT LIVE SERVED ROUTES | **2,874** |
| HOST VERIFIED | **true** |

Identical to the parent the registration bound (deploy `6ab6c879…`, release-index digest `sha256:3bd26696…`). The
live sitemap was fetched both times: 2,874 routes, sha256 `d34b0e5d…`, 0 San Diego routes. The live bytes compared
against below are Jacksonville's authorized artifact `C:\t\jax3a`, whose manifest names the live bundle
`f82f0714…` and sitemap `d34b0e5d…`.

## PHASE 2 — REGISTERED PACKAGE

| | |
|---|---|
| PACKAGE | `pkg-san-diego-ca-5d5ffd65bf1262a1` |
| PACKAGE DIGEST | `sha256:5d5ffd65bf1262a17273100a2dc97ecfe80e54d61033441530dd05ab19914b7e` |
| SOURCE READY / COVERAGE READY | YES / YES (founder decision, `san_diego_ca_founder_coverage_decision_002.json`) |
| ACTIONABLE UNRESOLVED | **0** |
| PET-FRIENDLY / VERIFIED NO-PETS / UNRESOLVED | **147 / 92 / 192** |
| FAST | 15/15 PASS |
| RULE J | 881 files, 865 HTML, bundle `9d07caac…`, NONEMPTY PASS |
| RULE K | BYTE_IDENTICAL, 4 cold builds, 0 reuse — NONVACUOUS PASS |
| PACKAGE REPRODUCIBLE / ELIGIBLE / FULL_REGRESSION_REQUIRED | YES / YES / NO |

Nothing re-derived; census and acquisition not reopened.

## PHASE 3 — FOUNDER AUTHORIZATION

| | |
|---|---|
| FOUNDER AUTHORIZATION ID | **`ptf-auth-san-diego-003-553a858f2590`** (the deployment authorization binding the founder's decision to the exact candidate bytes); the participation decision record is work order `PTF-SAN-DIEGO-CA-FOUNDER-LAUNCH-AUTHORIZATION-003`, `decided_by: founder`, `decided_on: 2026-09-26` |
| AUTHORIZED MARKET | `san-diego-ca` — **and only** `san-diego-ca` |
| AUTHORIZED PACKAGE | `pkg-san-diego-ca-5d5ffd65bf1262a1` |
| AUTHORIZED PACKAGE DIGEST | `sha256:5d5ffd65bf1262a1…14b7e` |
| AUTHORIZED SOURCE COMMIT | `34d523d9` (the committed founder decision the candidate was built from) |
| AUTHORIZED PARENT | deploy `6ab6c8798bd9daf5038ae3e5`, release-index digest `sha256:3bd26696…e44b` |
| DECISION BASIS | derived at run time from committed state by `san_diego_ca_launch_participation_003.py` (census, policy package, exclusion shard, release contract, final partition, actionability, coverage decision, readiness packet, FAST receipt — each path with its sha256) |

`decided_by` is the role `founder`, transcribing the founder's explicit decision in this order; no person's name is
signed. Each founder decision is a **guard that refuses to write** unless committed state agrees: cohort exactly
147 / 92; 130 no-website rows held and 0 published; 10 dual-brand rows held on five address keys (2 rows each) and 0
published; 52 other held rows and 0 published; 0 verified-no-pets published as profiles; 0 multi-amount records
carrying a single fee; ACTIONABLE 0; coverage READY by the recorded decision; source ready. A **first**
authorization: no `founder_authorization_superseded` entry exists or was written.

## PHASE 4 — PARTICIPATION

`launch_participation.extend_decision` — the chain is extended, never rebuilt.

| | |
|---|---|
| san-diego-ca | `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH` → **`FOUNDER_AUTHORIZED_FOR_LAUNCH`** |
| AUTHORIZED SET GAINED | **`san-diego-ca` only** (34 → 35) |
| AUTHORIZED SET LOST | **none** |
| OTHER PARTICIPATION ROWS CHANGED | **0** (36 rows) |
| DECISION PROBLEMS | **`[]`** |
| previous record sha256 | `eca4c907…1381`; lineage 38 records; new participation sha256 `e902abe8…6077` |

Not marked live. Detroit remains `SOURCE_READY` and is excluded from the candidate (`participates: false`).
**The decision was committed (`34d523d9`) BEFORE the whole-site build**, so the candidate's source commit contains
the authorized participation.

## PHASE 5 — THE EXACT AUTHORIZED CANDIDATE

`assemble_production_site --output C:/t/sd3a` (18:02Z → manifests 18:58Z), then `--output C:/t/sd3b` (19:00Z →
19:54Z), on committed tree `34d523d9`.

| | |
|---|---|
| AUTHORIZED CANDIDATE BUNDLE | **`553a858f2590094127ce68e63992c2c3dff969fcdc8f290decf112791f447eec`** |
| AUTHORIZED CANDIDATE SITEMAP | **`4f648fff6eaf50f7f7614eefda2639ac10c5cb678e77ef6fd15af60c89c0173e`** |
| total files | 16,202 |
| all gates pass (0 broken links, 0 collisions, 0 shadowing, 0 canonical violations) | **true** |
| markets included / excluded | 35 / Detroit |
| PARENT LOOKUP | **PASS** |
| PARENT ROUTES PRESERVED | **PASS** (2,807/2,807 index, 2,874/2,874 served) |

| Release-factory accounting | |
|---|---:|
| **UNCHANGED BUNDLES REUSED** | **34** (live index entries carried unchanged) |
| **UNCHANGED MARKETS REBUILT** | **0** |
| **SAN DIEGO BUNDLES BUILT** | **1** |
| **PHYSICAL FRAGMENTS RERENDERED** | **35** |

**Physical re-rendering is reported separately because it is not reuse.** This worktree has no populated release
store, so the whole-site composer physically rendered every participating fragment. The count is read from the
bundle's own manifest (35 fragments, each with its own `files_contributed`). The build log shows only 32
`Market scope:` lines because terminating the hung process discarded its unflushed stdout (the log stops inside
the 32nd market); the manifest, not the truncated log, is the count.

## PHASE 6 — CANDIDATE DETERMINISM

| | |
|---|---|
| builds | 2, **sequential** (never concurrent), separate short absolute work dirs `C:/t/sd3a`, `C:/t/sd3b` |
| both complete / non-empty | YES / YES (16,202 files each) |
| bundle hashes | `553a858f…` = `553a858f…` |
| sitemap hashes | `4f648fff…` = `4f648fff…` |
| file-hash manifest digest | `e2a1c0156e0d3911…` = `e2a1c0156e0d3911…` |
| FILES COMPARED / DIFFERING | **16,202 / 0** |
| RESULT | **BYTE_IDENTICAL** |

**The known assembler hang, handled as ordered.** Each build wrote `global_bundle_manifest.json` and
`file_hash_manifest.json` and then sat idle (build A ~0.16, build B ~0.03 CPU-seconds per second; resident memory
flat). For each, the manifests were read twice over more than a minute and were stable; only then was that
completed process terminated (A: PID 15004; B: PID 27732), and build B started only after A was gone.

## PHASE 7 — ROUTE ACCOUNTING (as sets, from the actual artifacts)

**A. RELEASE-INDEX ROUTES**

| | |
|---|---:|
| live | **2,807** |
| San Diego | **+162** (147 hotel + 14 corridor + 1 hub) |
| **candidate** | **2,969** |

**B. SERVED SITEMAP ROUTES** — read as sets from each bundle's own `sitemap.xml`:

| | |
|---|---:|
| live | **2,874** |
| San Diego | **+163** |
| **candidate** | **3,037** |

Set difference candidate − live: **163 routes added, all San Diego's; 0 not San Diego's; 0 prior served routes
lost.** The +1 served-vs-index difference is San Diego's policy-comparison page
(`/pet-friendly-hotels/san-diego-ca/policy-comparison/`), read from the fragment's own `comparison_route`, not
assumed.

## PHASE 8 — PUBLICATION COHORT SAFETY (on the BUILT artifact)

| | |
|---|---:|
| **APPROVED SAN DIEGO PROFILES IN CANDIDATE** | **147** |
| **UNAPPROVED / HELD SAN DIEGO PROFILES IN CANDIDATE** | **0** |

Every held row resolved to its census slug and checked for a profile page, a sitemap route, a release-index route
and a `/go/` file in `C:/t/sd3a`:

| group | rows | slugs resolved | pages | sitemap | index | /go/ |
|---|---:|---:|---:|---:|---:|---:|
| no-website | 130 | 130 | 0 | 0 | 0 | 0 |
| dual-brand | 10 | 10 | 0 | 0 | 0 | 0 |
| other held | 52 | 52 | 0 | 0 | 0 | 0 |
| verified-no-pets (as profiles) | 92 | 92 | 0 | 0 | 0 | 0 |

`identity_resolutions.json` not modified.

## PHASE 9 — TIERED / MULTI-AMOUNT FEE SAFETY

| | |
|---|---:|
| TIERED FEE ROWS | **30** (all withheld) |
| MULTI-AMOUNT ROWS (published records whose own quote states >1 amount) | **43** |
| **MISLEADING SINGLE FEES PUBLISHED** | **0** |

## PHASE 10 — CROSS-MARKET / IDENTITY SAFETY

| | |
|---|---:|
| CROSS-MARKET COLLISIONS (San Diego names held by any other market) | **0** |
| BARE-CHAIN COLLISIONS | **0** |
| DUPLICATE EXCLUDED IDENTITIES (shared registry, 1,281 rows) | **0** |

No existing live profile moved or disappeared (profiles 2,519 + 147 = 2,666; every prior market's files
byte-identical, Phase 11).

## PHASE 11 — DELTA / BYTE PRESERVATION (candidate vs the live bytes)

| | |
|---|---|
| UNEXPECTED MARKET / PROFILE / ROUTE DELTA | **`[]` / `[]` / `[]`** (release_diff passed, 0 findings) |
| PRIOR MARKETS / PROFILES / RELEASE-INDEX ROUTES / SERVED ROUTES LOST | **0 / 0 / 0 / 0** |
| files live → candidate | 15,342 → 16,202 |
| **FILES ADDED** | **860** — all San Diego: 163 pages (147 hotels, 14 corridors, hub, policy-comparison) + 697 `/go/` pages |
| **FILES REMOVED** | **0** |
| **FILES CHANGED** | **1** — `sitemap.xml` (global, regenerated for every release) |
| unexplained removed / prior-market changed / unclassified paths | **0 / 0 / 0** |

`index.html` and `pet-friendly-hotels/index.html` are byte-identical to live: San Diego ships hidden from global
navigation and the sitemap flags, exactly as every newly launched market does at this stage.

## PHASE 12 — FAST RECEIPT SAFETY

| | |
|---|---|
| selected receipt | `pkg-san-diego-ca-5d5ffd65bf1262a1-d3954ca9de28df5a.json` — **currently eligible** under today's reader |
| file_count / html_count | **881 / 865** |
| bundle | `9d07caac…` ≠ `e3b0c442…` |
| RULE J / RULE K | **PASS / PASS** (BYTE_IDENTICAL) |
| vacuous historical receipt | Augusta's `pkg-augusta-ga-14806eca…` preserved on disk and **still ineligible** (`EMPTY_BUNDLE`, `NO_HTML_OUTPUT`) |

## PHASE 13 — RELEASE GATES

| Gate | Result |
|---|---|
| FOUNDER AUTHORIZATION | **PASS** — participation FOUNDER_AUTHORIZED, decision_problems `[]`, basis guards all hold |
| PACKAGE IDENTITY | **PASS** — `pkg-san-diego-ca-5d5ffd65bf1262a1` |
| FAST RECEIPT ELIGIBILITY | **PASS** |
| PARENT IDENTITY | **PASS** — live deploy `6ab6c879…`, bundle `f82f0714…` |
| PARENT ROUTES PRESERVED | **PASS** |
| PROFILE PRESERVATION | **PASS** — +147 and nothing else |
| ROUTE PRESERVATION | **PASS** — +162 index / +163 served and nothing else |
| MARKET DELTA | **PASS** — +1 (san-diego-ca) |
| PARTICIPATION | **PASS** — 34 → 35, only San Diego gained |
| CANDIDATE DETERMINISM | **PASS** — BYTE_IDENTICAL, 16,202 / 0 |
| DEPLOYMENT ELIGIBILITY | **PASS** — authorization bound to the candidate bytes, `deployability_problems []`, `verify_authorization_problems []`, deployable, NOT consumed |
| HOLD / FEE / COLLISION SAFETY | **PASS** |

**Candidate: AUTHORIZED, DEPLOYABLE — not deployed.** `ALL_ACCOUNTING_GATES = PASS` in
`markets/reports/san_diego_ca_launch_authorization_003.json`.

## PHASE 14 — DEPLOYMENT AUTHORIZATION

| | |
|---|---|
| DEPLOYMENT AUTHORIZATION CREATED | **YES** |
| DEPLOYMENT AUTHORIZATION ID | **`ptf-auth-san-diego-003-553a858f2590`** |
| AUTHORIZED BUNDLE | `553a858f2590094127ce68e63992c2c3dff969fcdc8f290decf112791f447eec` |
| AUTHORIZED SITEMAP | `4f648fff6eaf50f7f7614eefda2639ac10c5cb678e77ef6fd15af60c89c0173e` |
| AUTHORIZED PARENT | `6ab6c8798bd9daf5038ae3e5` (also the rollback target) |
| STATUS | **AUTHORIZED, UNCONSUMED** (`deploy_id` null, no deployment record) |
| candidate manifest | `deploy/netlify/global_deployment_manifest_candidate_san_diego_003.json` — the live `global_deployment_manifest.json` was **not** written |

The authorization's source text quotes the founder's words from this order and binds the parent, the package
digest, the market bundle and the expected delta. It was created only after determinism was proven, and only for
the exact candidate bytes.

## PHASE 15 — FINAL LIVE SAFETY (19:57Z)

Resolver: deploy `6ab6c8798bd9daf5038ae3e5`, source `e9a059e5`, 34 / 2,519 / 2,874, host verified. Sitemap
re-fetched: **2,874 routes, `d34b0e5d…`, byte-identical; 0 San Diego routes.**

| Route | Expected | Actual |
|---|---|---|
| `/pet-friendly-hotels/san-diego-ca/` | 404 | **404** ✅ |
| `/pet-friendly-hotels/san-diego-ca/policy-comparison/` | 404 | **404** ✅ |
| `/pet-friendly-hotels/san-diego-ca/la-jolla/` | 404 | **404** ✅ |
| `/pet-friendly-hotels/jacksonville-fl/` | 200 | **200** ✅ |
| `/pet-friendly-hotels/west-palm-beach-fl/` | 200 | **200** ✅ |
| `/pet-friendly-hotels/fort-lauderdale-fl/` | 200 | **200** ✅ |
| `/pet-friendly-hotels/augusta-ga/` | 200 | **200** ✅ |
| `/pet-friendly-hotels/detroit-ann-arbor-mi/` | 404 | **404** ✅ |

## PHASE 16 — CLEANUP

Both whole-site build processes (15004, 27732) terminated after their bytes were proven stable; no monitors,
watchers or build processes created by this order remain. `C:/t/sd3a` (the authorized artifact the deploying order
will ship) and `C:/t/sd3b` (its determinism twin) are kept on disk, outside the repository.

---

## FINAL ANSWERS

```
 1. CURRENT LIVE DEPLOYMENT              = 6ab6c8798bd9daf5038ae3e5 (jacksonville-fl), source e9a059e5,
                                           bundle f82f0714..., sitemap d34b0e5d..., HOST VERIFIED true
 2. CURRENT LIVE MARKETS                 = 34
 3. CURRENT LIVE PROFILES                = 2,519
 4. CURRENT LIVE RELEASE-INDEX ROUTES    = 2,807
 5. CURRENT LIVE SERVED ROUTES           = 2,874
 6. REGISTERED PACKAGE                   = pkg-san-diego-ca-5d5ffd65bf1262a1
 7. PACKAGE DIGEST                       = sha256:5d5ffd65bf1262a17273100a2dc97ecfe80e54d61033441530dd05ab19914b7e
 8. FOUNDER AUTHORIZATION CREATED        = YES
 9. FOUNDER AUTHORIZATION ID             = ptf-auth-san-diego-003-553a858f2590
10. PARTICIPATION STATE                  = FOUNDER_AUTHORIZED_FOR_LAUNCH (35 of 36 authorized; Detroit withheld)
11. PARENT LOOKUP                        = PASS
12. PARENT ROUTES PRESERVED              = PASS (2,807/2,807 index, 2,874/2,874 served)
13. UNCHANGED BUNDLES REUSED             = 34
14. UNCHANGED MARKETS REBUILT            = 0
15. PHYSICAL FRAGMENTS RERENDERED        = 35 (no populated release store; counted from the bundle manifest --
                                           reported separately, NOT reuse)
16. SAN DIEGO BUNDLES BUILT              = 1
17. AUTHORIZED CANDIDATE BUNDLE          = 553a858f2590094127ce68e63992c2c3dff969fcdc8f290decf112791f447eec
18. AUTHORIZED CANDIDATE SITEMAP         = 4f648fff6eaf50f7f7614eefda2639ac10c5cb678e77ef6fd15af60c89c0173e
19. CANDIDATE MARKETS                    = 35
20. CANDIDATE PROFILES                   = 2,666
21. CANDIDATE RELEASE-INDEX ROUTES       = 2,969
22. CANDIDATE SERVED ROUTES              = 3,037
23. SAN DIEGO PROFILES                   = 147
24. SAN DIEGO RELEASE-INDEX ROUTES       = 162 (147 hotel + 14 corridor + 1 hub)
25. SAN DIEGO SERVED ROUTES              = 163 (162 + the policy-comparison page)
26. UNAPPROVED SAN DIEGO PROFILES        = 0
27. NO-WEBSITE HOLDS PUBLISHED           = 0 (of 130)
28. DUAL-BRAND HOLDS PUBLISHED           = 0 (of 10; identity_resolutions.json unchanged)
29. MULTI-AMOUNT MISLEADING FEES         = 0 (43 multi-amount rows, 30 tiered, all withheld)
30. CROSS-MARKET COLLISIONS              = 0 (bare-chain 0, duplicate excluded identities 0)
31. FAST RECEIPT ELIGIBLE                = YES (file_count 881, html_count 865, bundle 9d07caac...)
32. RULE J NONEMPTY                      = PASS
33. RULE K NONVACUOUS                    = PASS
34. CANDIDATE DETERMINISM                = BYTE_IDENTICAL (16,202 files, 0 differing)
35. ALL RELEASE GATES                    = PASS
36. UNEXPECTED DELTA                     = [] (860 added, all San Diego; 0 removed; 1 changed: sitemap.xml)
37. CANDIDATE DEPLOYABLE                 = YES (AUTHORIZED, DEPLOYABLE, not deployed)
38. DEPLOYMENT AUTHORIZATION CREATED     = YES
39. DEPLOYMENT AUTHORIZATION ID          = ptf-auth-san-diego-003-553a858f2590 (AUTHORIZED, UNCONSUMED)
40. CURRENT LIVE MODIFIED                = NO
41. DEPLOYMENT PERFORMED                 = NO
42. SAN DIEGO LIVE                       = NO (hub 404)
43. origin == HEAD                       = YES (verified after the final push)
44. tree clean                           = YES (verified after the final push)
45. READY FOR SAN DIEGO PRODUCTION
    DEPLOYMENT                           = YES
```

## FOR THE DEPLOYING ORDER

Consume `ptf-auth-san-diego-003-553a858f2590`; deploy bundle `553a858f…` from `C:\t\sd3a` with rollback
`6ab6c8798bd9daf5038ae3e5`; write the live `global_deployment_manifest.json` from those same bytes (verification
fails until it does) and extend `supersessions.json`. Expect 35 / 2,666 / 2,969 / 3,037 with San Diego's 163 routes
newly 200 and every prior route unchanged.

```
SAN DIEGO FOUNDER AUTHORIZATION = PASS
SAN DIEGO AUTHORIZED CANDIDATE = PASS
UNAPPROVED SAN DIEGO PROFILES = 0
NO-WEBSITE HOLDS PUBLISHED = 0
DUAL-BRAND HOLDS PUBLISHED = 0
MISLEADING MULTI-AMOUNT FEES = 0
CURRENT LIVE MODIFIED = NO
SAN DIEGO DEPLOYED = NO
READY FOR SAN DIEGO PRODUCTION DEPLOYMENT = YES
```
