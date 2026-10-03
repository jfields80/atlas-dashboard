# PTF-SEATTLE-WA-FOUNDER-LAUNCH-AUTHORIZATION-003 — FINAL

**SEATTLE IS FOUNDER-AUTHORIZED, AND ITS EXACT CANDIDATE IS BUILT, AUTHORIZED AND DEPLOYABLE.**
**It is NOT DEPLOYED.**

- Netlify was not invoked.
- The deployment authorization was created and **not consumed**.
- Live is unchanged.

**Founder's decision, transcribed** (no name signed; `decided_by: founder`):

> The founder explicitly authorizes launch of: seattle-wa ONLY for: pkg-seattle-wa-784f0147e1220f40. Bind
> authorization to: 89d6f249. The founder accepts the current safe publication cohort: 139 pet-friendly profiles.

Branch `worker/ptf-seattle-wa-market-001`. Commits:
- `438348c7`: the founder decision. It is the **BUILD commit**, committed before either whole-site build.
- The final commit: the candidate manifest, the deployment authorization, the accounting and this report.

## 1. Current live (Phase 1)

Verified at 15:35Z, and again after both builds and the authorization at 18:58Z. Both times, unchanged:

| | |
|---|---|
| CURRENT LIVE SOURCE COMMIT | `606839025c4c13c25d4d03984c7d5c049d27c73f` (built_from `be83dab2`) |
| CURRENT LIVE DEPLOYMENT | **`6ac064cd6a4261e60054a2f3`** (San Antonio) |
| CURRENT LIVE BUNDLE | `50b1ce95d80386ed9c28f16ad1493bc4c8f2588f201bb1f95597a6d6984a6bf4` |
| CURRENT LIVE SITEMAP | `e2a6b1c94dff6f9178fe83913c0babaf74f1b02b9453be37e29ad2c82a86b484` |
| MARKETS / PROFILES | 39 / 3,530 |
| RELEASE-INDEX / SERVED ROUTES | 3,894 / 3,966 |
| HOST VERIFIED | YES |

## 2. Registered package and registration evidence (Phases 2–3)

**Package and binding:**
- Package `pkg-seattle-wa-784f0147e1220f40` is `sha256:784f0147e1220f409eb7e5d7e9a4fd70af102c249a1bbf4468a3402d327d534e`,
  REGISTERED_LIVE, with parent `6ac064cd`.
- **Registration commit `89d6f249` carries the package's exact bytes:** blob `5756c373…` at `89d6f249` equals the
  working tree's, and `89d6f249` is an ancestor of HEAD.

**Source state:**
- SOURCE READY YES, COVERAGE READY YES, ACTIONABLE UNRESOLVED 0.
- PF 139 / NP 61; census 303; unresolved 103.

**FAST receipt:** `…-60013188aa5aff14.json`, 15/15, J PASS (853 files / 837 HTML, bundle `1872172c…`), K
BYTE_IDENTICAL. **Currently eligible.** Augusta's historical empty receipt stays ineligible.

**Safety counts:** explicit refusal 0, question-only 0, service-animal-only 0, preopening 0, timeshare 0, military 0,
misleading single fees 0.

**Registration evidence:**
- base derived AUTOMATICALLY (`5bd54304`);
- classification AUTOMATIC: COMPOSITE_FRESH_MARKET_DATA_ONLY, **15/15** checks;
- SHARED 0, UNKNOWN 0, FULL_REGRESSION_REQUIRED NO.

No broad regression was run in this order.

## 3. Founder authorization and participation (Phases 4–5)

Written by `seattle_wa_launch_participation_003.py` with `launch_participation.extend_decision`, so the chain is
extended, not rewritten. Every number in the decision basis is read from committed documents at run time, and each
founder decision is a guard.

| | |
|---|---|
| FOUNDER AUTHORIZATION ID | the participation decision of **`PTF-SEATTLE-WA-FOUNDER-LAUNCH-AUTHORIZATION-003`** (lineage record 48), committed `438348c7` |
| AUTHORIZED PACKAGE / DIGEST | `pkg-seattle-wa-784f0147e1220f40` / `sha256:784f0147e1220f409eb7e5d7e9a4fd70af102c249a1bbf4468a3402d327d534e` |
| AUTHORIZED REGISTRATION COMMIT | `89d6f2493f18174389837f64f9dedcb8758ee33f` (blob-verified) |
| AUTHORIZED SOURCE COMMIT | `438348c7` (the build commit the candidate was assembled from) |
| AUTHORIZED PARENT | `6ac064cd6a4261e60054a2f3` (release-index digest `079bde95…`) |
| DECISION BASIS | derived at run time from the readiness packet, classification, registration checks, census, policy package, shard, contract, partition, actionability, clean authority, fee report and safety audit; each item a GUARD |
| status | seattle-wa `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH` → **`FOUNDER_AUTHORIZED_FOR_LAUNCH`**; not live |
| authorized set | 39 → 40: **gained seattle-wa only, lost none, other rows changed 0**, `decision_problems` `[]` |
| earlier packages | the shadow id `pkg-seattle-wa-d39a3919f10cf45b` and the never-committed failed shadow `pkg-seattle-wa-5b2ee4fc…` are refused by the decision, the authorization writer and the accounting |

**Guards that held:**
- cohort 139 / 61, with 0 verified-no-pets as profiles;
- 103 unresolved, 0 published;
- founder rows 4: dual-brand on 2 buildings, 2 each (15220 NE Shen St 98052; 32124 25th Ave S 98003);
- named rows held and unpublished:
  - Hotel Interurban Tukwila;
  - Courtyard Northgate;
  - FairBridge Tukwila: the Days Inn row, IDENTITY_REVIEW, plus the new-name observation;
  - Motel 6 Suites Kent: the ESA Kent row, unresolved, plus the new-name observation;
- router-exhausted 98 and preopening 1, each 0 published;
- fees 25 / 39 / 15 / 0; 48 published records quote more than one amount, and 0 of them publish a single fee;
- 2 timeshare and 3 military-restricted identities: none in the census, none a PF record, none an exclusion;
- reader safety all 0;
- `identity_resolutions.json` not written.

## 4. The exact authorized candidate (Phases 6–8)

`assemble_production_site` ran twice, **sequentially**, from BUILD commit `438348c7`, with short absolute paths:

| | build | started | outcome |
|---|---|---|---|
| A | `C:/t/sea4a` | 15:37:00Z | manifests written 17:13:18Z, then the known post-manifest hang. Manifests were stable and CPU 1.14 s over 30 s, so it was terminated at 17:15:38Z |
| B | `C:/t/sea4b` | 17:15:51Z (after A was gone) | manifests 18:52:45Z, then the same hang; stable and CPU 1.22 s over 30 s, so it was terminated at 18:55:07Z |

| | |
|---|---|
| AUTHORIZED CANDIDATE BUNDLE | **`cfaad64a7bcb1b2b1734fe777ea577d5884aafe953054c2d80a7db1b01e0e5c3`** |
| AUTHORIZED CANDIDATE SITEMAP | **`63e052812b36668271aebb3f8bc933a44ac0d6150b7b8c19279d5f1e45a2b151`** |
| DETERMINISM | **BYTE_IDENTICAL**: bundle A = bundle B, sitemap A = sitemap B, 22,183 files compared, **0 differing** |
| assembler gates | 27 / 27 pass; broken links 0, collisions 0, canonical violations 0 |
| PARENT LOOKUP / ROUTES PRESERVED | PASS / PASS (all 3,894 parent release-index routes carried) |
| UNCHANGED BUNDLES REUSED / REBUILT | **39 / 0** |
| SEATTLE BUNDLES BUILT | **1** |
| PHYSICAL FRAGMENTS RERENDERED | **40**: no release store is populated in this worktree, so the composer physically renders every fragment. Reported separately; it is not reuse |

**Accounting** (`markets/reports/seattle_wa_launch_authorization_003.json`). The two systems are counted from their
own sources:

| | |
|---|---:|
| CANDIDATE MARKETS | **40** |
| CANDIDATE PROFILES | **3,669** (from the bundle's own fragments) |
| CANDIDATE RELEASE-INDEX ROUTES | **4,044** |
| CANDIDATE SERVED ROUTES | **4,117** (from the bundle's own sitemap) |
| SEATTLE PROFILES | **139** |
| SEATTLE RELEASE-INDEX ROUTES | **150** (139 hotels + 10 corridors + hub) |
| SEATTLE SERVED ROUTES | **151** (+ its policy-comparison page) |

**Byte preservation vs the live artifact (`C:/t/sa4a`):**
- 21,351 → 22,183 files: +832, all Seattle's; 0 removed;
- 1 changed, `sitemap.xml`;
- **0 prior-market files changed**, 0 unclassified.

## 5. Held content, reader, fee and collision safety (Phases 9–11)

Checked on the BUILT artifact, by the route the site forms:

| | published |
|---|---:|
| UNAPPROVED SEATTLE PROFILES | **0** |
| DUAL-BRAND ROWS | **0 / 4** |
| HOTEL INTERURBAN (preopening) | **0 / 1** |
| COURTYARD NORTHGATE | **0 / 1** |
| FAIRBRIDGE TUKWILA (2 rows) | **0** |
| MOTEL 6 SUITES KENT (2 rows) | **0** |
| router-exhausted | 0 / 98 |
| all unresolved | 0 / 103 |
| verified-no-pets as profiles | 0 / 61 |
| TIMESHARE (2) / MILITARY-RESTRICTED (3) | **0 / 0**: no profile, route, index entry, /go/ file, policy record or registry row, and no mention in Seattle's pages or the global surface |

**Reader safety:** PET-FRIENDLY WITH EXPLICIT REFUSAL **0**, QUESTION-ONLY **0**, SERVICE-ANIMAL-ONLY ACCEPTANCE **0**,
no-pets quote without refusal 0. The shared reader was not changed.

**Fees and collisions:**
- MISLEADING SINGLE FEES **0**. Every withheld fee stays withheld: waived, second-pet-only, tiered, multi-amount and
  basis-less.
- CROSS-MARKET COLLISIONS **0**: duplicate excluded identities 0, names held by another market 0.
- BARE-CHAIN COLLISIONS **0**: Seattle carries no bare-chain-shaped name.

## 6. Delta safety and gates (Phases 11–12)

**Delta safety:**
- UNEXPECTED MARKET, PROFILE and ROUTE DELTA `[]`; unexpected served-route delta `[]`.
- Prior markets, profiles, release-index routes and served routes lost: 0.
- `release_index.compare` passed.

**Gates:** ALL ACCOUNTING GATES **PASS**. The candidate is **AUTHORIZED** and **DEPLOYABLE**, and **NOT DEPLOYED**.

## 7. Deployment authorization (Phase 13)

`seattle_wa_deployment_authorization_003.py`:

| | |
|---|---|
| DEPLOYMENT AUTHORIZATION ID | **`ptf-auth-seattle-003-cfaad64a7bcb`** |
| STATUS | **AUTHORIZED**; **CONSUMED = NO** (no deploy id, no deployment record) |
| AUTHORIZED BUNDLE / SITEMAP | `cfaad64a…` / `63e05281…`; 40 markets / 3,669 profiles / 4,117 served |
| source_commit | `438348c7`, the BUILD commit (not HEAD) |
| AUTHORIZED PARENT / rollback target | `6ac064cd6a4261e60054a2f3` |
| authorized_by | `founder`, with the founder's words quoted in `authorization_source` |
| checks | `verify_manifest` `[]`, `verify_authorization` `[]`, `deployability_problems` `[]`, bound to the candidate bytes |
| candidate manifest | `deploy/netlify/global_deployment_manifest_candidate_seattle_003.json`; the LIVE manifest was not written |

Before writing, the writer refused if:
- any other authorization was still deployable (there were none);
- the readiness packet bound another package;
- participation did not read FOUNDER_AUTHORIZED_FOR_LAUNCH.

## 8. Live safety (Phase 14)

At 18:58Z, after both builds and the authorization (`markets/reports/seattle_wa_launch_authorization_live_probe_003.json`):
- **CURRENT LIVE DEPLOYMENT unchanged** (`6ac064cd`, 39 / 3,530 / 3,966, host verified).
- **SERVED SITEMAP unchanged** (`e2a6b1c9…`).
- **Seattle hub 404; all 151 projected Seattle routes 404.**
- San Antonio, Austin, Phoenix, Denver, San Diego, Jacksonville FL, West Palm Beach, Fort Lauderdale and Augusta return
  **200**; Detroit **404**.

## 9. For the deployment order

- **Deploy** `C:\t\sea4a\site`; its twin is `C:\t\sea4b`. Both artifacts were kept on disk.
- **Consume** `ptf-auth-seattle-003-cfaad64a7bcb`.
- **Re-resolve live first.** If it is no longer `6ac064cd`, the parent has moved and this candidate is stale.
- **Expected after deploy:** 40 / 3,669 / 4,044 / 4,117.
- **Probe held rows** at both the census slug and the site route.

Both build processes were stopped (PIDs 17964 and 3616, each after its manifests were stable and its CPU idle). No
other process from this order remains.

## FINAL ANSWERS

1. CURRENT LIVE DEPLOYMENT = 6ac064cd6a4261e60054a2f3 (San Antonio; source 60683902, sitemap e2a6b1c9…, unchanged)
2. CURRENT LIVE MARKETS = 39
3. SEATTLE PACKAGE = pkg-seattle-wa-784f0147e1220f40 (sha256:784f0147e1220f409eb7e5d7e9a4fd70af102c249a1bbf4468a3402d327d534e)
4. REGISTRATION COMMIT = 89d6f249 (carries the package's exact bytes; ancestor of HEAD)
5. AUTOMATIC BASE DERIVES = YES (5bd54304)
6. AUTOMATIC CLASSIFICATION = YES
7. REGISTRATION CLASS = COMPOSITE_FRESH_MARKET_DATA_ONLY
8. CLASSIFIER CHECKS = 15/15 PASS
9. SHARED PATHS = 0
10. UNKNOWN PATHS = 0
11. FULL_REGRESSION_REQUIRED = NO
12. FOUNDER AUTHORIZATION CREATED = YES
13. FOUNDER AUTHORIZATION ID = participation decision PTF-SEATTLE-WA-FOUNDER-LAUNCH-AUTHORIZATION-003 (lineage record 48, commit 438348c7)
14. PARTICIPATION STATE = FOUNDER_AUTHORIZED_FOR_LAUNCH (not live; authorized set 39 → 40, gained seattle-wa only)
15. PARENT LOOKUP = PASS
16. PARENT ROUTES PRESERVED = PASS
17. UNCHANGED BUNDLES REUSED = 39
18. UNCHANGED MARKETS REBUILT = 0
19. PHYSICAL FRAGMENTS RERENDERED = 40 (no release store populated; reported separately, not reuse)
20. SEATTLE BUNDLES BUILT = 1
21. AUTHORIZED CANDIDATE BUNDLE = cfaad64a7bcb1b2b1734fe777ea577d5884aafe953054c2d80a7db1b01e0e5c3
22. AUTHORIZED CANDIDATE SITEMAP = 63e052812b36668271aebb3f8bc933a44ac0d6150b7b8c19279d5f1e45a2b151
23. CANDIDATE MARKETS = 40
24. CANDIDATE PROFILES = 3669
25. CANDIDATE RELEASE-INDEX ROUTES = 4044
26. CANDIDATE SERVED ROUTES = 4117
27. SEATTLE PROFILES = 139
28. SEATTLE RELEASE-INDEX ROUTES = 150
29. SEATTLE SERVED ROUTES = 151
30. UNAPPROVED SEATTLE PROFILES = 0
31. DUAL-BRAND HELDS PUBLISHED = 0 / 4
32. HOTEL INTERURBAN PUBLISHED = 0
33. COURTYARD NORTHGATE PUBLISHED = 0
34. FAIRBRIDGE TUKWILA PUBLISHED = 0
35. MOTEL 6 SUITES KENT PUBLISHED = 0
36. PREOPENING PROFILES PUBLISHED = 0
37. TIMESHARE PROFILES PUBLISHED = 0
38. PET-FRIENDLY WITH EXPLICIT REFUSAL = 0
39. QUESTION-ONLY PET-FRIENDLY = 0
40. MISLEADING SINGLE FEES = 0
41. CROSS-MARKET COLLISIONS = 0
42. FAST RECEIPT ELIGIBLE = YES (pkg-seattle-wa-784f0147e1220f40-60013188aa5aff14.json)
43. CANDIDATE DETERMINISM = BYTE_IDENTICAL (22,183 files, 0 differing; bundle A = B, sitemap A = B)
44. ALL RELEASE GATES = PASS
45. UNEXPECTED DELTA = [] (market / profile / route / served)
46. CANDIDATE DEPLOYABLE = YES
47. DEPLOYMENT AUTHORIZATION CREATED = YES (AUTHORIZED, not consumed)
48. DEPLOYMENT AUTHORIZATION ID = ptf-auth-seattle-003-cfaad64a7bcb
49. CURRENT LIVE MODIFIED = NO
50. DEPLOYMENT PERFORMED = NO
51. SEATTLE LIVE = NO (hub + 151 routes 404)
52. origin == HEAD = YES (verified after push)
53. tree clean = YES (verified after push)
54. READY FOR SEATTLE PRODUCTION DEPLOYMENT = YES (deploy C:\t\sea4a\site, consume ptf-auth-seattle-003-cfaad64a7bcb, parent 6ac064cd)

```
SEATTLE FOUNDER AUTHORIZATION = PASS
SEATTLE AUTHORIZED CANDIDATE = PASS
FULL_REGRESSION_REQUIRED = NO
PET-FRIENDLY RECORDS WITH EXPLICIT REFUSAL = 0
QUESTION-ONLY PET-FRIENDLY RECORDS = 0
UNAPPROVED SEATTLE PROFILES = 0
MISLEADING SINGLE FEES = 0
CURRENT LIVE MODIFIED = NO
SEATTLE DEPLOYED = NO
READY FOR SEATTLE PRODUCTION DEPLOYMENT = YES
```
