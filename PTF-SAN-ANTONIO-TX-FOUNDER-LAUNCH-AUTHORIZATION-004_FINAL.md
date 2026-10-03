# PTF-SAN-ANTONIO-TX-FOUNDER-LAUNCH-AUTHORIZATION-004 — FINAL

**SAN ANTONIO IS FOUNDER-AUTHORIZED, AND ITS EXACT CANDIDATE IS BUILT, AUTHORIZED AND DEPLOYABLE.**
**It is NOT DEPLOYED.**

- Netlify was not invoked.
- The deployment authorization was created and **not consumed**.
- Live is unchanged.

**Founder's decision, transcribed** (no name signed; `decided_by: founder`):

> The founder explicitly authorizes launch of: san-antonio-tx ONLY for: pkg-san-antonio-tx-aa8f4fe9ea26a6ff.
> Bind this decision to registration commit: 5f30c7b3. The founder accepts the current safe publication cohort:
> 144 pet-friendly profiles.

Branch `worker/ptf-san-antonio-tx-market-001`. Commits:
- `be83dab2`: the founder decision. It is the **BUILD commit**, committed before either whole-site build.
- The final commit: the candidate manifest, the deployment authorization, the accounting and this report.

## 1. Current live (Phase 1)

Verified at 22:24:58Z, and again after both builds at 01:42:50Z. Both times, unchanged:

| | |
|---|---|
| CURRENT LIVE SOURCE COMMIT | `f0ddbcde` (built_from `ef28f7b4`) |
| CURRENT LIVE DEPLOYMENT | **`6abf3e749cc359701298718d`** (Austin) |
| BUNDLE / SITEMAP | `75e569412dd2…` / `d6461dbc2cd4…` |
| MARKETS / PROFILES | 38 / 3,386 |
| RELEASE-INDEX / SERVED ROUTES | 3,737 / 3,808 |
| HOST VERIFIED | YES |

## 2. Registered package and registration evidence (Phases 2–3)

**Package and binding:**
- Package `pkg-san-antonio-tx-aa8f4fe9ea26a6ff` is `sha256:aa8f4fe9…d116`, REGISTERED_LIVE, with parent `6abf3e74`.
- **Registration commit `5f30c7b3` carries the package's exact bytes:** blob `ac434491…` at `5f30c7b3` equals the
  working tree's, and `5f30c7b3` is an ancestor of HEAD.
- The package's own `created_from_source_sha` is `45e885be`, the commit before the registration commit. The seal
  reads working-tree bytes, and `5f30c7b3` committed exactly those bytes.

**Source state:**
- SOURCE READY YES, COVERAGE READY YES, ACTIONABLE UNRESOLVED 0.
- PF 144 / NP 98; census 414; unresolved 172.

**FAST receipt:** `…-859baec5238b5b52.json`, 15/15, J PASS (884 files / 868 HTML, bundle `f9b4c610…`), K
BYTE_IDENTICAL. **Currently eligible.**

**Safety counts:** explicit refusal 0, question-only 0, service-animal-only 0, preopening 0, timeshare 0, military 0,
misleading single fees 0.

**Registration evidence:**
- base derived AUTOMATICALLY (`3afa9b17`);
- classification AUTOMATIC: COMPOSITE_FRESH_MARKET_DATA_ONLY, **15/15** checks;
- SHARED 0, UNKNOWN 0, FULL_REGRESSION_REQUIRED NO, broad runs 0.

No broad regression was run in this order.

## 3. Founder authorization and participation (Phases 4–5)

Written by `san_antonio_tx_launch_participation_004.py` with `launch_participation.extend_decision`, so the chain is
extended, not rewritten.

| | |
|---|---|
| FOUNDER AUTHORIZATION ID | the participation decision of **`PTF-SAN-ANTONIO-TX-FOUNDER-LAUNCH-AUTHORIZATION-004`** (lineage record 46), committed `be83dab2` |
| AUTHORIZED PACKAGE / DIGEST | `pkg-san-antonio-tx-aa8f4fe9ea26a6ff` / `sha256:aa8f4fe9ea26a6ff575bcae2af68d3f60ad194048be13a6a351834ff75dad116` |
| AUTHORIZED REGISTRATION COMMIT | `5f30c7b3e65da1584402b6d8129f36890a584410` (blob-verified) |
| AUTHORIZED SOURCE COMMIT | `be83dab2` (the build commit the candidate was assembled from) |
| AUTHORIZED PARENT | `6abf3e749cc359701298718d` (release-index digest `37f5fe83…`) |
| DECISION BASIS | derived at run time from the readiness packet, classification, registration checks, census, policy package, shard, contract, partition, actionability, clean authority, Hilton retry record, fee report and safety audit; each item a GUARD |
| status | san-antonio-tx `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH` → **`FOUNDER_AUTHORIZED_FOR_LAUNCH`**; not live |
| authorized set | 38 → 39: **gained san-antonio-tx only, lost none, other rows changed 0**, `decision_problems` `[]` |
| earlier packages | the shadow id `pkg-san-antonio-tx-b6018714bcc2bd44` is refused by the decision, the authorization writer and the accounting (it is the only other San Antonio package) |

**Guards that held:**
- cohort 144 / 98, with 0 verified-no-pets as profiles;
- 172 unresolved, 0 published;
- Hilton 10 retried / 0 new reads / 10 still blocked, 0 published, no further retry;
- founder rows 9: 8 dual-brand on 4 buildings, 2 each (111 Soledad, 118 Soledad, 1025 S Frio, 6815 W US 90), plus
  The Jackson House;
- router-exhausted 159 and preopening 4, each 0 published;
- fees 14 / 39 / 17 / 0, with 0 multi-amount records publishing a single fee;
- 8 timeshare and 9 military-restricted identities: none in the census, none a PF record, none an exclusion;
- reader safety all 0;
- `identity_resolutions.json` not written.

## 4. The exact authorized candidate (Phases 6–8)

`assemble_production_site` ran twice, **sequentially**, from BUILD commit `be83dab2`, with short absolute paths:

| | build | started | outcome |
|---|---|---|---|
| A | `C:/t/sa4a` | 22:28:43Z | manifests written ~00:07Z, then the known post-manifest hang. Manifests were stable and CPU 1.27 s over 30 s, so it was terminated at 00:09:58Z |
| B | `C:/t/sa4b` | 00:10:05Z (after A was gone) | the same hang; manifests stable and CPU 1.13 s over 30 s, so it was terminated at 01:40:19Z |

| | |
|---|---|
| AUTHORIZED CANDIDATE BUNDLE | **`50b1ce95d80386ed9c28f16ad1493bc4c8f2588f201bb1f95597a6d6984a6bf4`** |
| AUTHORIZED CANDIDATE SITEMAP | **`e2a6b1c94dff6f9178fe83913c0babaf74f1b02b9453be37e29ad2c82a86b484`** |
| DETERMINISM | **BYTE_IDENTICAL**: bundle A = bundle B, sitemap A = sitemap B, 21,351 files compared, **0 differing** |
| assembler gates | 27 / 27 pass; broken links 0, collisions 0, canonical violations 0 |
| PARENT LOOKUP / ROUTES PRESERVED | PASS / PASS (all 3,737 parent release-index routes carried) |
| UNCHANGED BUNDLES REUSED / REBUILT | **38 / 0** |
| SAN ANTONIO BUNDLES BUILT | **1** |
| PHYSICAL FRAGMENTS RERENDERED | **39**: no release store is populated in this worktree, so the composer physically renders every fragment. Reported separately; it is not reuse |

**Accounting** (`markets/reports/san_antonio_tx_launch_authorization_004.json`). The two systems are counted from
their own sources:

| | |
|---|---:|
| CANDIDATE MARKETS | **39** |
| CANDIDATE PROFILES | **3,530** (from the bundle's own fragments) |
| CANDIDATE RELEASE-INDEX ROUTES | **3,894** |
| CANDIDATE SERVED ROUTES | **3,966** (from the bundle's own sitemap) |
| SAN ANTONIO PROFILES | **144** |
| SAN ANTONIO RELEASE-INDEX ROUTES | **157** (144 hotels + 12 corridors + hub) |
| SAN ANTONIO SERVED ROUTES | **158** (+ its policy-comparison page) |

**Byte preservation vs the live artifact (`C:/t/atx4a`):**
- +863 files, all San Antonio's; 0 removed;
- 1 changed, `sitemap.xml`;
- **0 prior-market files changed**, 0 unclassified.

## 5. Held content, reader, fee and collision safety (Phases 9–11)

Checked on the BUILT artifact, by the route the site forms:

| | published |
|---|---:|
| UNAPPROVED SAN ANTONIO PROFILES | **0** |
| HILTON BLOCKED ROWS | **0 / 10** |
| DUAL-BRAND ROWS | **0 / 8** |
| THE JACKSON HOUSE | **0 / 1** |
| PREOPENING | **0 / 4** |
| router-exhausted | 0 / 159 |
| all unresolved | 0 / 172 |
| verified-no-pets as profiles | 0 / 98 |
| TIMESHARE (8) / MILITARY-RESTRICTED (9) | **0 / 0**: no profile, route, index entry, /go/ file, policy record or registry row, and no mention in San Antonio's pages or the global surface |

**Reader safety:** PET-FRIENDLY WITH EXPLICIT REFUSAL **0**, QUESTION-ONLY **0**, SERVICE-ANIMAL-ONLY ACCEPTANCE **0**,
no-pets quote without refusal 0. The shared reader was not changed.

**Fees and collisions:**
- MISLEADING SINGLE FEES **0**.
- CROSS-MARKET COLLISIONS **0**, duplicate excluded identities 0, names held by another market 0.
- BARE-CHAIN COLLISIONS **0**.

**Known latent risk, recorded and not repaired, per the order:** "Best Western Garden Inn" is a name-matched
verified-no-pets exclusion.
- The shared registry matches an exclusion by normalized name in every market, so it could shadow a future,
  unrelated hotel of the same name.
- **CURRENTLY EXPOSED OTHER BUILDINGS WITH SAME NAME = 0.** The only other row is Austin's OUTSIDE_MARKET record of
  the same building at 78233.

## 6. Delta safety and gates (Phases 12–13)

**Delta safety:**
- UNEXPECTED MARKET, PROFILE and ROUTE DELTA `[]`; unexpected served-route delta `[]`.
- Prior markets, profiles, release-index routes and served routes lost: 0.
- `release_index.compare` passed.

**Gates:** ALL ACCOUNTING GATES **PASS**. The candidate is **AUTHORIZED** and **DEPLOYABLE**, and **NOT DEPLOYED**.

## 7. Deployment authorization (Phase 14)

`san_antonio_tx_deployment_authorization_004.py`:

| | |
|---|---|
| DEPLOYMENT AUTHORIZATION ID | **`ptf-auth-san-antonio-004-50b1ce95d803`** |
| STATUS | **AUTHORIZED**; **CONSUMED = NO** (no deploy id, no deployment record) |
| AUTHORIZED BUNDLE / SITEMAP | `50b1ce95…` / `e2a6b1c9…`; 39 markets / 3,530 profiles / 3,966 served |
| source_commit | `be83dab2`, the BUILD commit (not HEAD) |
| AUTHORIZED PARENT / rollback target | `6abf3e749cc359701298718d` |
| authorized_by | `founder`, with the founder's words quoted in `authorization_source` |
| checks | `verify_manifest` `[]`, `verify_authorization` `[]`, `deployability_problems` `[]`, bound to the candidate bytes |
| candidate manifest | `deploy/netlify/global_deployment_manifest_candidate_san_antonio_004.json`; the LIVE manifest was not written |

Before writing, the writer refused if:
- any other authorization was still deployable (there were none);
- the readiness packet bound another package;
- participation did not read FOUNDER_AUTHORIZED_FOR_LAUNCH.

## 8. Live safety (Phase 15)

At 01:42:50Z, after both builds and the authorization:
- **CURRENT LIVE DEPLOYMENT unchanged** (`6abf3e74`, 38 / 3,386 / 3,808, host verified).
- **SERVED SITEMAP unchanged** (`d6461dbc…`).
- **San Antonio hub 404; all 158 projected San Antonio routes 404.**
- Austin, Phoenix, Denver, San Diego, Jacksonville FL, West Palm Beach, Fort Lauderdale and Augusta return **200**;
  Detroit **404**.

## 9. For the deployment order

- **Deploy** `C:\t\sa4a\site`; its twin is `C:\t\sa4b`. Both artifacts were kept on disk.
- **Consume** `ptf-auth-san-antonio-004-50b1ce95d803`.
- **Re-resolve live first.** If it is no longer `6abf3e74`, the parent has moved and this candidate is stale.
- **Expected after deploy:** 39 / 3,530 / 3,894 / 3,966.
- **Probe held rows** at both the census slug and the site route.

Both build processes were stopped (PIDs 14392 and 26528, each after its manifests were stable and its CPU idle). No
other process from this order remains.

## FINAL ANSWERS

1. CURRENT LIVE DEPLOYMENT = 6abf3e749cc359701298718d (Austin; source f0ddbcde, sitemap d6461dbc…, unchanged)
2. CURRENT LIVE MARKETS = 38
3. SAN ANTONIO PACKAGE = pkg-san-antonio-tx-aa8f4fe9ea26a6ff
4. PACKAGE DIGEST = sha256:aa8f4fe9ea26a6ff575bcae2af68d3f60ad194048be13a6a351834ff75dad116
5. REGISTRATION COMMIT = 5f30c7b3 (carries the package's exact bytes; ancestor of HEAD)
6. AUTOMATIC BASE DERIVES = YES (3afa9b17)
7. AUTOMATIC CLASSIFICATION = YES
8. REGISTRATION CLASS = COMPOSITE_FRESH_MARKET_DATA_ONLY
9. CLASSIFIER CHECKS = 15/15 PASS
10. SHARED PATHS = 0
11. UNKNOWN PATHS = 0
12. FULL_REGRESSION_REQUIRED = NO
13. FOUNDER AUTHORIZATION CREATED = YES
14. FOUNDER AUTHORIZATION ID = participation decision PTF-SAN-ANTONIO-TX-FOUNDER-LAUNCH-AUTHORIZATION-004 (lineage record 46, commit be83dab2)
15. PARTICIPATION STATE = FOUNDER_AUTHORIZED_FOR_LAUNCH (not live; authorized set 38 → 39, gained san-antonio-tx only)
16. PARENT LOOKUP = PASS
17. PARENT ROUTES PRESERVED = PASS
18. UNCHANGED BUNDLES REUSED = 38
19. UNCHANGED MARKETS REBUILT = 0
20. PHYSICAL FRAGMENTS RERENDERED = 39 (no release store populated; reported separately, not reuse)
21. SAN ANTONIO BUNDLES BUILT = 1
22. AUTHORIZED CANDIDATE BUNDLE = 50b1ce95d80386ed9c28f16ad1493bc4c8f2588f201bb1f95597a6d6984a6bf4
23. AUTHORIZED CANDIDATE SITEMAP = e2a6b1c94dff6f9178fe83913c0babaf74f1b02b9453be37e29ad2c82a86b484
24. CANDIDATE MARKETS = 39
25. CANDIDATE PROFILES = 3530
26. CANDIDATE RELEASE-INDEX ROUTES = 3894
27. CANDIDATE SERVED ROUTES = 3966
28. SAN ANTONIO PROFILES = 144
29. SAN ANTONIO RELEASE-INDEX ROUTES = 157
30. SAN ANTONIO SERVED ROUTES = 158
31. UNAPPROVED SAN ANTONIO PROFILES = 0
32. HILTON BLOCKED ROWS PUBLISHED = 0 / 10
33. DUAL-BRAND ROWS PUBLISHED = 0 / 8
34. JACKSON HOUSE PUBLISHED = 0
35. PREOPENING PROFILES PUBLISHED = 0 / 4
36. TIMESHARE PROFILES PUBLISHED = 0
37. MILITARY-RESTRICTED PROFILES PUBLISHED = 0
38. PET-FRIENDLY WITH EXPLICIT REFUSAL = 0
39. QUESTION-ONLY PET-FRIENDLY = 0
40. MISLEADING SINGLE FEES = 0
41. CROSS-MARKET COLLISIONS = 0
42. BEST WESTERN GARDEN INN CURRENT OTHER-BUILDING COLLISIONS = 0 (latent risk recorded, not repaired)
43. FAST RECEIPT ELIGIBLE = YES
44. CANDIDATE DETERMINISM = BYTE_IDENTICAL (21,351 files, 0 differing; bundle A = B, sitemap A = B)
45. ALL RELEASE GATES = PASS
46. UNEXPECTED DELTA = [] (market / profile / route / served)
47. CANDIDATE DEPLOYABLE = YES
48. DEPLOYMENT AUTHORIZATION CREATED = YES (AUTHORIZED, not consumed)
49. DEPLOYMENT AUTHORIZATION ID = ptf-auth-san-antonio-004-50b1ce95d803
50. CURRENT LIVE MODIFIED = NO
51. DEPLOYMENT PERFORMED = NO
52. SAN ANTONIO LIVE = NO (hub + 158 routes 404)
53. origin == HEAD = YES
54. tree clean = YES
55. READY FOR SAN ANTONIO PRODUCTION DEPLOYMENT = YES (deploy C:\t\sa4a\site, consume ptf-auth-san-antonio-004-50b1ce95d803, parent 6abf3e74)

```
SAN ANTONIO FOUNDER AUTHORIZATION = PASS
SAN ANTONIO AUTHORIZED CANDIDATE = PASS
FULL_REGRESSION_REQUIRED = NO
PET-FRIENDLY RECORDS WITH EXPLICIT REFUSAL = 0
QUESTION-ONLY PET-FRIENDLY RECORDS = 0
UNAPPROVED SAN ANTONIO PROFILES = 0
MISLEADING SINGLE FEES = 0
CURRENT LIVE MODIFIED = NO
SAN ANTONIO DEPLOYED = NO
READY FOR SAN ANTONIO PRODUCTION DEPLOYMENT = YES
```
