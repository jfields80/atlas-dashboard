# PTF-NEW-ORLEANS-LA-FOUNDER-LAUNCH-AUTHORIZATION-003 — FINAL

**Status:** New Orleans is **FOUNDER_AUTHORIZED_FOR_LAUNCH** on `pkg-new-orleans-la-0e5fef6af3af8339`, bound to
registration commit `85e7c13e`.

**Candidate:** the exact authorized whole-site candidate is built and byte-identical across two sequential assemblies.
Deployment authorization `ptf-auth-new-orleans-003-af70e0aa8a64` is **AUTHORIZED** and **not consumed**.

**Not done:** nothing was deployed and Netlify was not invoked; live is unchanged.

**Branch:** `worker/ptf-new-orleans-la-market-001` (worktree `C:\Atlas-New-Orleans-LA-Hardened-V1`).

**Commits:**
- `4c7e7b90` — the founder decision (participation). This is the **BUILD commit** the candidate was assembled from.
- the final commit — the candidate manifest, the deployment authorization, the accounting, the live probe, the two
  market-local candidate modules and this report.

## 1. Current live (Phase 1)

Verified at 21:27:46Z (2026-10-06) and again after both builds and the authorization at 02:15:59Z (2026-10-07) —
unchanged both times:

| | |
|---|---|
| CURRENT LIVE SOURCE COMMIT | `117afe1105f920a8fcebd5bc1f4c4e2be9bb3ed3` (built_from `c6609370`) |
| CURRENT LIVE DEPLOYMENT | **`6ac4dc8a39b0e7274828a32b`** (record `ptf-deploy-kansas-city-004-…`) |
| CURRENT LIVE BUNDLE | `6a35c23829f9c0a0a1713acc721f3fcf317a94d7f57120379ffc951fdc60ed5f` (the on-disk live artifact `C:/t/kc4a` carries the same digest) |
| CURRENT LIVE SITEMAP | `3d5d9425a4e0a90b6aca13f3d02866a815ebc934df8382e4fcf03c0ecc10967b` (the served `sitemap.xml` hashes to it) |
| CURRENT LIVE MARKETS | **43** (Detroit withheld) |
| CURRENT LIVE PROFILES | **4,136** |
| CURRENT LIVE RELEASE-INDEX ROUTES | **4,552** (counted from the live index) |
| CURRENT LIVE SERVED ROUTES | **4,628** |
| HOST VERIFIED | YES |

## 2. Registered package and registration evidence (Phases 2–3)

| | |
|---|---|
| PACKAGE | `pkg-new-orleans-la-0e5fef6af3af8339`, `sha256:0e5fef6af3af83397a0fae3a1bc00e75cf30575100d9100ce4d7e19c2905ff0f` |
| REGISTRATION COMMIT | `85e7c13e3909730d40cd630071a89340ce16d38b` — an ancestor of HEAD; the package blob there (`a825195b…`) equals the tree's |
| state | SOURCE READY YES, COVERAGE READY YES, ACTIONABLE UNRESOLVED 0; census 347, PF 104, NP 64, resolved 168, unresolved 179 |
| FAST | 15/15; Rule J PASS (644 files / 628 HTML, bundle `047825df…`); Rule K PASS (BYTE_IDENTICAL) |
| receipt | `pkg-new-orleans-la-0e5fef6af3af8339-ea4d8ec3d090dfc1`, CURRENTLY ELIGIBLE (the only one selected), 0 defects |
| registration evidence | AUTOMATIC base `e42ae364`; AUTOMATIC classification COMPOSITE_FRESH_MARKET_DATA_ONLY; classifier checks 15/15; shared paths 0; unknown paths 0; FULL_REGRESSION_REQUIRED NO; broad runs 0 |
| municipalities | Orleans Parish 282, Jefferson Parish 62; wrong-city identities 0 |
| reader / fee safety | explicit-refusal PF 0, question-only PF 0, service-animal-only 0, misleading single fees 0 |

## 3. Founder authorization and participation (Phases 4–5)

`new_orleans_la_launch_participation_003.py` records the decision, extending the chain through
`launch_participation.extend_decision` (lineage now 56 records).

**Founder's words** (transcribed; no name signed; `decided_by: founder`): *"The founder explicitly authorizes launch
of: new-orleans-la ONLY for: pkg-new-orleans-la-0e5fef6af3af8339. Bind this decision to: 85e7c13e. Do NOT authorize:
pkg-new-orleans-la-939f3cda64d39402 or the earlier 8585917a shadow package. The founder accepts the current safe
publication cohort: 104 pet-friendly profiles."*

| | |
|---|---|
| FOUNDER AUTHORIZATION | the participation decision of `PTF-NEW-ORLEANS-LA-FOUNDER-LAUNCH-AUTHORIZATION-003`, committed `4c7e7b90` |
| AUTHORIZED PACKAGE / DIGEST | `pkg-new-orleans-la-0e5fef6af3af8339` / `sha256:0e5fef6a…` |
| AUTHORIZED SOURCE COMMIT | `4c7e7b90` (the BUILD commit; the candidate manifest's own `source_commit`) |
| AUTHORIZED REGISTRATION COMMIT | `85e7c13e` |
| AUTHORIZED PARENT | `6ac4dc8a39b0e7274828a32b`, release-index digest `sha256:3e8bcf48…` |
| DECISION BASIS | the readiness packet, classification and staging-checks documents of PTF-NEW-ORLEANS-LA-REGISTRATION-AND-STAGING-002 (each pinned by sha256); every count and digest read from committed state; each founder decision is a guard |
| refused packages | `pkg-new-orleans-la-939f3cda64d39402` (source-ready shadow id) and `pkg-new-orleans-la-8585917af96bd963` (the earlier shadow seal). Neither is authorized |
| participation | new-orleans-la SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH → **FOUNDER_AUTHORIZED_FOR_LAUNCH** |
| authorized set | 43 → 44: **gained new-orleans-la only, lost none, other rows changed 0**, `decision_problems = []` |

Guards verified before writing: 179 unresolved rows, 0 published; SpringHill + TownePlace at 1600 Canal St (one
building, 2 rows), The Garden District Hotel, Maison DuBois, Maison Dupuy, the preopening Fairmont and the closed
Claiborne Mansion all held and 0 published; The Syd, Castle Day and Compass Point Events outside the census
(NON_LODGING), 0 published; 175 router-exhausted held; fees 29 / 22 / 10 / 0 (of 27 published records quoting more than
one amount, 0 publish a single fee); 7 timeshare identities outside hotel inventory; the municipality and market-text
registration gates PASS. `identity_resolutions.json` was not written; the shared reader was not touched; the declined
navigations were not reopened.

**One correction:** the guard on military-restricted identities found 0, while the source-ready accounting had reported
2. Those two rows (Fanny Ranch Lodge, Woodland Plantation — Plaquemines Parish, OUTSIDE) only *name* the NAS JRB Navy
Lodge rule in their reasons. The accounting now counts the exclusion class by the reason's head; New Orleans has **0**
military-restricted identities (accounting regenerated).

## 4. The exact authorized candidate (Phases 6–8)

`assemble_production_site` from BUILD commit `4c7e7b90`, twice, **sequentially**, short absolute paths:

- **Build A** (`C:/t/nola4a`): started 21:32:14Z; manifests 23:58:41Z; then the known post-manifest hang — output stable
  across four snapshots (23:58:51 → 00:00:53Z), CPU +1.4 s per 40 s at the end — terminated 00:01:02Z.
- **Build B** (`C:/t/nola4b`): started 00:01:14Z, after A was gone; manifests 02:09:47Z; same hang — stable across five
  snapshots (02:09:55 → 02:12:38Z), CPU +1.6–1.8 s per 40 s — terminated 02:12:46Z.

Free memory stayed about 2.5–3.2 GB on this 16 GB machine. No failure.

| | |
|---|---|
| AUTHORIZED CANDIDATE BUNDLE | **`af70e0aa8a64496e53c67750668c33029cbda3cf318d9d3ecb1198af346a0a41`** |
| AUTHORIZED CANDIDATE SITEMAP | **`beb98d7a9f4687c337dfcbd5eaa1d301ac7d74eecddba5dcebf7d7b05c2a8508`** |
| DETERMINISM | **BYTE_IDENTICAL** — bundle A = B, sitemap A = B, 25,580 files compared, **0 differing** |
| assembler gates | all pass (`all_gates_pass: true`) |
| PARENT LOOKUP / ROUTES PRESERVED | PASS / PASS |
| UNCHANGED BUNDLES REUSED / REBUILT | **43 / 0** |
| NEW ORLEANS BUNDLES BUILT | **1** |
| PHYSICAL FRAGMENTS RERENDERED | **44** — no release store is populated in this worktree, so the composer physically renders every fragment. Reported separately; not reuse |

Accounting (`markets/reports/new_orleans_la_launch_authorization_003.json`), each system from its own source:

| | |
|---|---:|
| CANDIDATE MARKETS | **44** |
| CANDIDATE PROFILES | **4,240** (from the bundle's own fragments) |
| CANDIDATE RELEASE-INDEX ROUTES | **4,663** |
| CANDIDATE SERVED ROUTES | **4,740** (from the bundle's own sitemap) |
| NEW ORLEANS PROFILES | **104** |
| NEW ORLEANS RELEASE-INDEX ROUTES | **111** (104 hotels + 6 corridors + hub) |
| NEW ORLEANS SERVED ROUTES | **112** (+ its policy-comparison page) |

Byte preservation vs the live artifact (`C:/t/kc4a`): +623 files, all New Orleans'; 0 removed; 1 changed
(`sitemap.xml`); **0 prior-market files changed**; 0 unclassified.

## 5. Held content, municipality, name-twin, reader, fee and collision safety (Phases 9–13)

Checked on the BUILT artifact by the route the site forms:

| | published |
|---|---:|
| UNAPPROVED NEW ORLEANS PROFILES | **0** |
| SPRINGHILL / TOWNEPLACE 1600 CANAL | **0 / 2** |
| THE GARDEN DISTRICT HOTEL | **0** |
| MAISON DUBOIS / MAISON DUPUY | **0 / 0** |
| PREOPENING (Fairmont) / CLOSED (Claiborne Mansion) | **0 / 0** |
| TIMESHARE / VACATION-OWNERSHIP (7) | **0** |
| THE SYD / CASTLE DAY / COMPASS POINT (4 census rows) | **0** |
| router-exhausted | 0 / 175 |
| all unresolved | 0 / 179 |
| verified-no-pets as profiles | 0 / 64 |

- **Municipalities:** all 104 profile pages checked — 79 Orleans, 24 Jefferson, 1 Plaquemines. Every page's own
  structured address states LA, the municipality the census carries and that row's ZIP (New Orleans 79, Metairie 6,
  Harvey 6, Kenner 5, Gretna 3, Harahan 2, Avondale 1, Belle Chasse 1, Elmwood 1); **0 wrong**, 0 non-Orleans pages say
  New Orleans. The municipality traps build as committed (Residence Inn Elmwood → Elmwood, Holiday Inn West Bank Tower →
  Gretna, Red Roof Westbank → Harvey, Wyndham Garden → Kenner published; Clarion Airport, Hilton New Orleans Airport
  (verified no-pets) and Brent House (held) have no page).
- **Wyndham Garden name twin** (exactly the proven shape): the held map-only row is still one OSM row at 6401 Veterans
  Memorial Blvd, Metairie 70003 (IDENTITY_REVIEW_REQUIRED); the published hotel is bound to Wyndham property code
  **46094** at 4535 Williams Blvd, Kenner 70065, by the brand's own first-party page, and its built page states that
  building (`addressLocality: Kenner`). METAIRIE MAP-TWIN PUBLISHED **0** (no New Orleans file names 6401 Veterans
  Memorial); KENNER WYNDHAM FIRST-PARTY BOUND **YES**; CURRENT CROSS-BUILDING COLLISION **0**. The gate was not widened.
- **Market text:** 0 New Orleans pages carry Kansas City / Missouri, Minneapolis or Portland text.
- **Reader:** explicit-refusal PF 0, question-only 0, service-animal-only 0, NP quote without refusal 0. Shared reader
  unchanged.
- **Fees:** MISLEADING SINGLE FEES 0; 29 single-basis publish; 22 tiered and 10 unsafe stay withheld. **Crowne Plaza
  Astor** publishes no fee (its quote states "nightly fee of 35 USD with a maximum fee of 70 USD"; facts carry only
  pets allowed and the 2-pet limit).
- **Collisions:** cross-market 0, bare-chain names 0, bare-chain collisions 0, duplicate excluded identities 0.
- **Delta:** unexpected market / profile / route / served-route delta `[]`; prior markets, profiles, index routes and
  served routes lost 0; `release_index.compare` passed.

**FAST receipt (Phase 14):** `…-ea4d8ec3d090dfc1` remains currently eligible (644 files / 628 HTML, bundle `047825df…`,
not `e3b0c442`). Augusta's historical empty receipt stays ineligible.

## 6. Gates and deployment authorization (Phases 15–16)

ALL ACCOUNTING GATES **PASS**. The candidate is **AUTHORIZED** and **DEPLOYABLE**, and **NOT DEPLOYED**.

| | |
|---|---|
| DEPLOYMENT AUTHORIZATION ID | **`ptf-auth-new-orleans-003-af70e0aa8a64`** |
| STATUS | **AUTHORIZED**; **CONSUMED = NO** (no deploy id, no deployment record) |
| AUTHORIZED BUNDLE / SITEMAP | `af70e0aa…` / `beb98d7a…`; 44 markets / 4,240 profiles / 4,740 served |
| source_commit | `4c7e7b90`, the BUILD commit (not HEAD) |
| AUTHORIZED PARENT / rollback target | `6ac4dc8a39b0e7274828a32b` |
| authorized_by | `founder`, with the founder's words quoted in `authorization_source` |
| checks | `verify_manifest []`, `verify_authorization []`, `deployability_problems []`, bound to the candidate bytes |
| candidate manifest | `deploy/netlify/global_deployment_manifest_candidate_new_orleans_003.json`; the LIVE manifest was not written |

`verify_all()` 45/45 clean after the participation change.

## 7. Live safety (Phase 17)

At 02:15:59Z, after both builds and the authorization (`markets/reports/new_orleans_la_launch_authorization_live_probe_003.json`):
CURRENT LIVE DEPLOYMENT unchanged (6ac4dc8a, 43 / 4,136 / 4,628, host verified); SERVED SITEMAP unchanged
(`3d5d9425…`); New Orleans hub and all **112** projected routes **404**; Kansas City, Minneapolis, Portland, Seattle,
San Antonio, Austin, Phoenix, Denver, San Diego, Jacksonville FL, West Palm Beach, Fort Lauderdale and Augusta **200**;
Detroit **404**.

Both build processes (PIDs 21644, 11676) were stopped only after their output was stable and CPU idle. No process
created by this order remains.

## FINAL ANSWERS

1. CURRENT LIVE DEPLOYMENT = 6ac4dc8a39b0e7274828a32b
2. CURRENT LIVE MARKETS = 43
3. NEW ORLEANS PACKAGE = pkg-new-orleans-la-0e5fef6af3af8339
4. REGISTRATION COMMIT = 85e7c13e
5. AUTOMATIC BASE DERIVES = YES (e42ae364)
6. AUTOMATIC CLASSIFICATION = YES
7. REGISTRATION CLASS = COMPOSITE_FRESH_MARKET_DATA_ONLY
8. CLASSIFIER CHECKS = 15/15 PASS
9. SHARED PATHS = 0
10. UNKNOWN PATHS = 0
11. FULL_REGRESSION_REQUIRED = NO
12. FOUNDER AUTHORIZATION CREATED = YES
13. FOUNDER AUTHORIZATION ID = the participation decision of PTF-NEW-ORLEANS-LA-FOUNDER-LAUNCH-AUTHORIZATION-003 (commit 4c7e7b90)
14. PARTICIPATION STATE = FOUNDER_AUTHORIZED_FOR_LAUNCH
15. PARENT LOOKUP = PASS
16. PARENT ROUTES PRESERVED = PASS
17. UNCHANGED BUNDLES REUSED = 43
18. UNCHANGED MARKETS REBUILT = 0
19. PHYSICAL FRAGMENTS RERENDERED = 44 (no release store in this worktree; not reuse)
20. NEW ORLEANS BUNDLES BUILT = 1
21. AUTHORIZED CANDIDATE BUNDLE = af70e0aa8a64496e53c67750668c33029cbda3cf318d9d3ecb1198af346a0a41
22. AUTHORIZED CANDIDATE SITEMAP = beb98d7a9f4687c337dfcbd5eaa1d301ac7d74eecddba5dcebf7d7b05c2a8508
23. CANDIDATE MARKETS = 44
24. CANDIDATE PROFILES = 4,240
25. CANDIDATE RELEASE-INDEX ROUTES = 4,663
26. CANDIDATE SERVED ROUTES = 4,740
27. NEW ORLEANS PROFILES = 104
28. NEW ORLEANS RELEASE-INDEX ROUTES = 111
29. NEW ORLEANS SERVED ROUTES = 112
30. UNAPPROVED NEW ORLEANS PROFILES = 0
31. DUAL-BRAND HOLDS PUBLISHED = 0
32. GARDEN DISTRICT HOTEL PUBLISHED = 0
33. MAISON DUBOIS PUBLISHED = 0
34. MAISON DUPUY PUBLISHED = 0
35. PREOPENING PROFILES PUBLISHED = 0
36. TIMESHARE PROFILES PUBLISHED = 0
37. PRIVATE / VENUE RENTALS PUBLISHED = 0
38. NEW ORLEANS WRONG-CITY IDENTITIES = 0
39. METAIRIE MAP-TWIN PUBLISHED = 0
40. KENNER WYNDHAM FIRST-PARTY BOUND = YES (code 46094, 4535 Williams Blvd 70065)
41. PET-FRIENDLY WITH EXPLICIT REFUSAL = 0
42. QUESTION-ONLY PET-FRIENDLY = 0
43. SERVICE-ANIMAL-ONLY ACCEPTANCE = 0
44. MISLEADING SINGLE FEES = 0
45. CROSS-MARKET COLLISIONS = 0
46. FAST RECEIPT ELIGIBLE = YES
47. CANDIDATE DETERMINISM = BYTE_IDENTICAL (25,580 files, 0 differing)
48. ALL RELEASE GATES = PASS
49. UNEXPECTED DELTA = []
50. CANDIDATE DEPLOYABLE = YES
51. DEPLOYMENT AUTHORIZATION CREATED = YES
52. DEPLOYMENT AUTHORIZATION ID = ptf-auth-new-orleans-003-af70e0aa8a64
53. CURRENT LIVE MODIFIED = NO
54. DEPLOYMENT PERFORMED = NO
55. NEW ORLEANS LIVE = NO
56. origin == HEAD = YES (verified after push)
57. tree clean = YES (verified after push)
58. READY FOR NEW ORLEANS PRODUCTION DEPLOYMENT = YES

NEW ORLEANS FOUNDER AUTHORIZATION = PASS
NEW ORLEANS AUTHORIZED CANDIDATE = PASS
FULL_REGRESSION_REQUIRED = NO
NEW ORLEANS WRONG-CITY IDENTITIES = 0
PET-FRIENDLY RECORDS WITH EXPLICIT REFUSAL = 0
QUESTION-ONLY PET-FRIENDLY RECORDS = 0
SERVICE-ANIMAL-ONLY ACCEPTANCE = 0
UNAPPROVED NEW ORLEANS PROFILES = 0
MISLEADING SINGLE FEES = 0
CURRENT LIVE MODIFIED = NO
NEW ORLEANS DEPLOYED = NO
READY FOR NEW ORLEANS PRODUCTION DEPLOYMENT = YES

STOP.

## For the deployment order

- **Deploy** `C:\t\nola4a\site` (twin `C:\t\nola4b`; both kept on disk).
- **Consume** `ptf-auth-new-orleans-003-af70e0aa8a64`.
- **Re-resolve live first.** If it is no longer `6ac4dc8a`, the parent has moved and this candidate is stale.
- **Expected after deploy:** 44 / 4,240 / 4,663 / 4,740, with New Orleans' 112 routes returning 200.
- **Probe held rows** (1600 Canal pair, The Garden District Hotel, Maison DuBois, Maison Dupuy, Fairmont, Claiborne
  Mansion, The Syd, Castle Day, Compass Point) at both the census slug and the site route; all must stay 404.
- Extend `tests/pettripfinder/pins/supersessions.json` with the new live authorization at launch.
