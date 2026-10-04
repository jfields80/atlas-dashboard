# PTF-PORTLAND-OR-FOUNDER-LAUNCH-AUTHORIZATION-003 — FINAL

**Status:** Portland is **FOUNDER_AUTHORIZED_FOR_LAUNCH** on `pkg-portland-or-5b6016fb253bc7a7`, bound to registration
commit `09850aa3`.

**Candidate:** the exact authorized whole-site candidate is built and byte-identical across two sequential
assemblies. Deployment authorization `ptf-auth-portland-003-d674d2898af1` is **AUTHORIZED** and **not consumed**.

**Not done:** nothing was deployed and Netlify was not invoked; live is unchanged.

**Branch:** `worker/ptf-portland-or-market-001` (worktree `C:\Atlas-Portland-OR-Hardened-V1`).

**Commits:**
- `22ff1c94`: the founder decision (participation). This is the **BUILD commit** the candidate was assembled from.
- The final commit: the candidate manifest, the deployment authorization, the accounting, the live probe, the three
  market-local modules and this report.

## 1. Current live (Phase 1)

Verified at 03:56Z, and again after both builds and the authorization at 07:40Z. Both times, unchanged:

| | |
|---|---|
| CURRENT LIVE SOURCE COMMIT | `f0003e78b10d249774d376cc6bc2457d57cf63ce` (built_from `438348c7`) |
| CURRENT LIVE DEPLOYMENT | **`6ac169ef7c75c383eb79f824`**, record `ptf-deploy-seattle-004-6ac169ef7c75c383eb79f824.json` |
| CURRENT LIVE BUNDLE | `cfaad64a7bcb1b2b1734fe777ea577d5884aafe953054c2d80a7db1b01e0e5c3` (the on-disk live artifact `C:/t/sea4a` carries the same digest) |
| CURRENT LIVE SITEMAP | `63e052812b36668271aebb3f8bc933a44ac0d6150b7b8c19279d5f1e45a2b151` (the served `sitemap.xml` hashes to it) |
| CURRENT LIVE MARKETS | **40** (Detroit withheld) |
| CURRENT LIVE PROFILES | **3,669** |
| CURRENT LIVE RELEASE-INDEX ROUTES | **4,044** |
| CURRENT LIVE SERVED ROUTES | **4,117** |
| HOST VERIFIED | YES |

## 2. Registered package and registration evidence (Phases 2–3)

| | |
|---|---|
| PACKAGE | `pkg-portland-or-5b6016fb253bc7a7`, `sha256:5b6016fb253bc7a79ee20baf9099908db316cd95fff4ee3a97227684af905dfb` |
| REGISTRATION COMMIT | `09850aa357651039ce1b9eb20a24caf33080b6c9`. It is an ancestor of HEAD, and the package blob there (`bbf2fc0b…`) equals the tree's |
| state | SOURCE READY YES, COVERAGE READY YES, ACTIONABLE UNRESOLVED 0, PET-FRIENDLY 150 (NP 47) |
| FAST | 15/15; Rule J PASS (908 files / 892 HTML); Rule K PASS (BYTE_IDENTICAL) |
| receipt | `pkg-portland-or-5b6016fb253bc7a7-df634e23cb809eb7.json`, CURRENTLY ELIGIBLE |
| registration evidence | AUTOMATIC base `0e2e8bb8`; AUTOMATIC classification COMPOSITE_FRESH_MARKET_DATA_ONLY; classifier checks 15/15; shared paths 0; unknown paths 0; FULL_REGRESSION_REQUIRED NO |
| reader safety | explicit-refusal PF 0, question-only PF 0, misleading single fees 0 |

## 3. Founder authorization and participation (Phases 4–5)

`portland_or_launch_participation_003.py` records the decision. It extends the decision chain through
`launch_participation.extend_decision`, and lineage now has 50 records.

**Founder's words** (transcribed; no name signed; `decided_by: founder`): *"The founder explicitly authorizes launch of:
portland-or ONLY for: pkg-portland-or-5b6016fb253bc7a7. Bind this decision to: 09850aa3. The founder accepts the
current safe publication cohort: 150 pet-friendly profiles."*

| | |
|---|---|
| FOUNDER AUTHORIZATION | the participation decision of `PTF-PORTLAND-OR-FOUNDER-LAUNCH-AUTHORIZATION-003`, committed `22ff1c94` |
| AUTHORIZED PACKAGE / DIGEST | `pkg-portland-or-5b6016fb253bc7a7` / `sha256:5b6016fb…` |
| AUTHORIZED SOURCE COMMIT | `22ff1c94` (the BUILD commit, the candidate manifest's own `source_commit`) |
| AUTHORIZED REGISTRATION COMMIT | `09850aa3` |
| AUTHORIZED PARENT | `6ac169ef7c75c383eb79f824`, release-index digest `sha256:123c8f93…` |
| DECISION BASIS | the readiness packet, classification and staging-checks documents of PTF-PORTLAND-OR-REGISTRATION-AND-STAGING-002 (each pinned by sha256); every count and digest is read from committed state, and each founder decision is a guard |
| refused packages | `pkg-portland-or-b6f95c2ae170f44b` (source-ready shadow id) and `pkg-portland-or-aad74479d8ce7a07` (digest-only staging seal, never written). Neither is authorized |
| participation | portland-or SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH → **FOUNDER_AUTHORIZED_FOR_LAUNCH** |
| authorized set | 40 → 41: **gained portland-or only, lost none, other rows changed 0**, `decision_problems` `[]` |

**What the guards verified before writing:**

| decision | held rows | published |
|---|---|---|
| unresolved rows | 75 | 0 |
| named: WorldMark Portland – Waterfront Park | NON_LODGING | 0 |
| named: Hyatt House Portland Airport, The Mindaro | SAME_CAMPUS (+ the bureau's name-only Mindaro sighting) | 0 |
| named: self-contradictory pages (The Dunes Motel, Hampton Inn Portland East) | held | 0 |
| named: affiliate-template rows (Cameo Motel, Portland INN, Bridgeway Inn) | held | 0 |
| founder-class rows (The Dunes Motel) | 1 | 0 |
| dual-brand / preopening rows | 0 / 0 | — |
| router-exhausted | 74 | 0 |
| timeshare / military | 3 / 0 (none in census, none a PF record, none an exclusion) | 0 |

Two further guard results:
- **Fees:** 20 / 33 / 20 / 0. Of the 37 published records whose quotes state more than one amount, 0 publish a
  single fee.
- **Vancouver WA:** the corridor is present. Its 34 rows (26 published) all carry state WA; 0 Oregon rows carry any
  state but OR.

`identity_resolutions.json` was not written.

## 4. The exact authorized candidate (Phases 6–8)

`assemble_production_site` ran twice, **sequentially**, from BUILD commit `22ff1c94`, with short absolute paths.

**Build A** (`C:/t/pdx4a`):
- started 03:58:10Z; manifests written ~05:45Z;
- then the known post-manifest hang: manifests were stable and CPU 1.1–1.4 s per 30 s, so it was terminated at
  05:48:30Z.

**Build B** (`C:/t/pdx4b`):
- started 05:48:53Z, after A was gone; manifests ~07:34Z;
- then the same hang: stable and CPU 1.3–1.5 s per 30 s, so it was terminated at 07:37:15Z.

| | |
|---|---|
| AUTHORIZED CANDIDATE BUNDLE | **`d674d2898af11565559318500650bbee1c8e59fbf0fc3ea4040dacd3a7cfecea`** |
| AUTHORIZED CANDIDATE SITEMAP | **`a50f1e343949ff65122e903b39a8bc9aed6318aef0a25b265aba6da772adf360`** |
| DETERMINISM | **BYTE_IDENTICAL**: bundle A = bundle B, sitemap A = sitemap B, 23,070 files compared, **0 differing** |
| assembler gates | all pass (`all_gates_pass: true`) |
| PARENT LOOKUP / ROUTES PRESERVED | PASS / PASS (all 4,044 parent release-index routes carried; parent markets and profiles preserved) |
| UNCHANGED BUNDLES REUSED / REBUILT | **40 / 0** |
| PORTLAND BUNDLES BUILT | **1** |
| PHYSICAL FRAGMENTS RERENDERED | **41**: no release store is populated in this worktree, so the composer physically renders every fragment. Reported separately; it is not reuse |

**Accounting** (`markets/reports/portland_or_launch_authorization_003.json`). The two systems are counted from their
own sources:

| | |
|---|---:|
| CANDIDATE MARKETS | **41** |
| CANDIDATE PROFILES | **3,819** (from the bundle's own fragments) |
| CANDIDATE RELEASE-INDEX ROUTES | **4,206** |
| CANDIDATE SERVED ROUTES | **4,280** (from the bundle's own sitemap) |
| PORTLAND PROFILES | **150** |
| PORTLAND RELEASE-INDEX ROUTES | **162** (150 hotels + 11 corridors + hub) |
| PORTLAND SERVED ROUTES | **163** (+ its policy-comparison page) |

**Byte preservation vs the live artifact (`C:/t/sea4a`):**
- 22,183 → 23,070 files: +887, all Portland's; 0 removed;
- 1 changed, `sitemap.xml`;
- **0 prior-market files changed**, 0 unclassified.

## 5. Held content, Vancouver, reader, fee and collision safety (Phases 9–12)

Checked on the BUILT artifact, by the route the site forms:

| | published |
|---|---:|
| UNAPPROVED PORTLAND PROFILES | **0** |
| WORLDMARK PORTLAND (and the 2 other WorldMark timeshare rows) | **0**: no profile, route, index entry, /go/ file, policy record or registry row, and no mention in Portland's pages or the global surface |
| HYATT HOUSE PORTLAND AIRPORT / THE MINDARO (+ name-only sighting) | **0 / 3** |
| PREOPENING | **0** (none exists) |
| SELF-CONTRADICTORY ROWS (The Dunes Motel, Hampton Inn Portland East) | **0 / 2** |
| AFFILIATE-TEMPLATE ROWS (Cameo Motel, Portland INN, Bridgeway Inn) | **0 / 3** |
| router-exhausted | 0 / 74 |
| all unresolved | 0 / 75 |
| verified-no-pets as profiles | 0 / 47 |

**Vancouver WA:**
- VANCOUVER WA CORRIDOR PRESENT **YES**; the `vancouver-wa` corridor page is built.
- All 21 Vancouver pet-friendly profile pages state "WA" and their own 98xxx postal code, and none says
  "Vancouver, OR".
- VANCOUVER WA WRONG-STATE IDENTITIES **0**.

**Reader safety:** PET-FRIENDLY WITH EXPLICIT REFUSAL **0**, QUESTION-ONLY **0**, SERVICE-ANIMAL-ONLY ACCEPTANCE **0**,
no-pets quote without refusal 0. The shared reader was not changed.

**Fees:** MISLEADING SINGLE FEES **0**. 20 single-basis fees publish; 33 tiered and 20 unsafe fees stay withheld.

**Collisions:**
- CROSS-MARKET COLLISIONS **0**: duplicate excluded identities 0, names held by another market 0.
- BARE-CHAIN COLLISIONS **0**: Portland carries no bare-chain-shaped name.

**Delta safety:**
- UNEXPECTED MARKET, PROFILE, ROUTE and SERVED-ROUTE DELTA `[]`.
- Prior markets, profiles, release-index routes and served routes lost: 0.
- `release_index.compare` passed.

## 6. Gates and deployment authorization (Phases 13–14)

ALL ACCOUNTING GATES **PASS**. The candidate is **AUTHORIZED** and **DEPLOYABLE**, and **NOT DEPLOYED**.

`portland_or_deployment_authorization_003.py`:

| | |
|---|---|
| DEPLOYMENT AUTHORIZATION ID | **`ptf-auth-portland-003-d674d2898af1`** |
| STATUS | **AUTHORIZED**; **CONSUMED = NO** (no deploy id, no deployment record) |
| AUTHORIZED BUNDLE / SITEMAP | `d674d289…` / `a50f1e34…`; 41 markets / 3,819 profiles / 4,280 served |
| source_commit | `22ff1c94`, the BUILD commit (not HEAD) |
| AUTHORIZED PARENT / rollback target | `6ac169ef7c75c383eb79f824` |
| authorized_by | `founder`, with the founder's words quoted in `authorization_source` |
| checks | `verify_manifest` `[]`, `verify_authorization` `[]`, `deployability_problems` `[]`, bound to the candidate bytes |
| candidate manifest | `deploy/netlify/global_deployment_manifest_candidate_portland_003.json`; the LIVE manifest was not written |

Before writing, the writer refused if:
- any other authorization was still deployable (there were none);
- the readiness packet bound another package;
- participation did not read FOUNDER_AUTHORIZED_FOR_LAUNCH.

## 7. Live safety (Phase 15)

At 07:40Z, after both builds and the authorization (`markets/reports/portland_or_launch_authorization_live_probe_003.json`):
- **CURRENT LIVE DEPLOYMENT unchanged** (`6ac169ef`, 40 / 3,669 / 4,117, host verified).
- **SERVED SITEMAP unchanged** (`63e05281…`).
- **Portland hub 404; all 163 projected Portland routes 404.**
- Seattle, San Antonio, Austin, Phoenix, Denver, San Diego, Jacksonville FL, West Palm Beach, Fort Lauderdale and
  Augusta return **200**; Detroit **404**.

Both build processes were stopped (PIDs 2836 and 26512, each after its manifests were stable and its CPU idle). No
process created by this order remains.

## 8. For the deployment order

- **Deploy** `C:\t\pdx4a\site`; its twin is `C:\t\pdx4b`. Both artifacts were kept on disk.
- **Consume** `ptf-auth-portland-003-d674d2898af1`.
- **Re-resolve live first.** If it is no longer `6ac169ef`, the parent has moved and this candidate is stale.
- **Expected after deploy:** 41 / 3,819 / 4,206 / 4,280, with Portland's 163 routes returning 200.
- **Probe held rows** (WorldMark, Hyatt House Portland Airport, The Mindaro) at both the census slug and the site
  route.

## FINAL ANSWERS

1. CURRENT LIVE DEPLOYMENT = 6ac169ef7c75c383eb79f824 (Seattle; source f0003e78, sitemap 63e05281…, unchanged)
2. CURRENT LIVE MARKETS = 40
3. PORTLAND PACKAGE = pkg-portland-or-5b6016fb253bc7a7
4. PACKAGE DIGEST = sha256:5b6016fb253bc7a79ee20baf9099908db316cd95fff4ee3a97227684af905dfb
5. REGISTRATION COMMIT = 09850aa357651039ce1b9eb20a24caf33080b6c9
6. AUTOMATIC BASE DERIVES = YES (0e2e8bb8)
7. AUTOMATIC CLASSIFICATION = YES
8. REGISTRATION CLASS = COMPOSITE_FRESH_MARKET_DATA_ONLY
9. CLASSIFIER CHECKS = 15/15 PASS
10. SHARED PATHS = 0
11. UNKNOWN PATHS = 0
12. FULL_REGRESSION_REQUIRED = NO
13. FOUNDER AUTHORIZATION CREATED = YES
14. FOUNDER AUTHORIZATION ID = PTF-PORTLAND-OR-FOUNDER-LAUNCH-AUTHORIZATION-003 participation decision (decided_by founder), committed 22ff1c94
15. PARTICIPATION STATE = FOUNDER_AUTHORIZED_FOR_LAUNCH (authorized set 40 → 41, gained portland-or only)
16. PARENT LOOKUP = PASS
17. PARENT ROUTES PRESERVED = PASS
18. UNCHANGED BUNDLES REUSED = 40
19. UNCHANGED MARKETS REBUILT = 0
20. PHYSICAL FRAGMENTS RERENDERED = 41 (no release store populated; not reuse)
21. PORTLAND BUNDLES BUILT = 1
22. AUTHORIZED CANDIDATE BUNDLE = d674d2898af11565559318500650bbee1c8e59fbf0fc3ea4040dacd3a7cfecea
23. AUTHORIZED CANDIDATE SITEMAP = a50f1e343949ff65122e903b39a8bc9aed6318aef0a25b265aba6da772adf360
24. CANDIDATE MARKETS = 41
25. CANDIDATE PROFILES = 3819
26. CANDIDATE RELEASE-INDEX ROUTES = 4206
27. CANDIDATE SERVED ROUTES = 4280
28. PORTLAND PROFILES = 150
29. PORTLAND RELEASE-INDEX ROUTES = 162
30. PORTLAND SERVED ROUTES = 163
31. UNAPPROVED PORTLAND PROFILES = 0
32. WORLDMARK PORTLAND PUBLISHED = 0
33. HYATT HOUSE PORTLAND AIRPORT PUBLISHED = 0
34. THE MINDARO PUBLISHED = 0
35. PREOPENING PROFILES PUBLISHED = 0
36. TIMESHARE / VACATION-OWNERSHIP PROFILES PUBLISHED = 0
37. VANCOUVER WA CORRIDOR PRESENT = YES
38. VANCOUVER WA WRONG-STATE IDENTITIES = 0
39. PET-FRIENDLY WITH EXPLICIT REFUSAL = 0
40. QUESTION-ONLY PET-FRIENDLY = 0
41. MISLEADING SINGLE FEES = 0
42. CROSS-MARKET COLLISIONS = 0
43. FAST RECEIPT ELIGIBLE = YES (pkg-portland-or-5b6016fb253bc7a7-df634e23cb809eb7.json)
44. CANDIDATE DETERMINISM = BYTE_IDENTICAL (23,070 files, 0 differing)
45. ALL RELEASE GATES = PASS
46. UNEXPECTED DELTA = [] (market, profile, route, served route)
47. CANDIDATE DEPLOYABLE = YES
48. DEPLOYMENT AUTHORIZATION CREATED = YES
49. DEPLOYMENT AUTHORIZATION ID = ptf-auth-portland-003-d674d2898af1 (AUTHORIZED, unconsumed)
50. CURRENT LIVE MODIFIED = NO
51. DEPLOYMENT PERFORMED = NO
52. PORTLAND LIVE = NO (hub + 163 routes 404)
53. origin == HEAD = YES (verified after push)
54. tree clean = YES (verified after push)
55. READY FOR PORTLAND PRODUCTION DEPLOYMENT = YES (deploy C:\t\pdx4a\site, consume ptf-auth-portland-003-d674d2898af1)

```
PORTLAND FOUNDER AUTHORIZATION = PASS
PORTLAND AUTHORIZED CANDIDATE = PASS
FULL_REGRESSION_REQUIRED = NO
PET-FRIENDLY RECORDS WITH EXPLICIT REFUSAL = 0
QUESTION-ONLY PET-FRIENDLY RECORDS = 0
UNAPPROVED PORTLAND PROFILES = 0
MISLEADING SINGLE FEES = 0
CURRENT LIVE MODIFIED = NO
PORTLAND DEPLOYED = NO
READY FOR PORTLAND PRODUCTION DEPLOYMENT = YES
```
