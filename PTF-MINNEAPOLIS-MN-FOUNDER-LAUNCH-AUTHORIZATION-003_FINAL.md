# PTF-MINNEAPOLIS-MN-FOUNDER-LAUNCH-AUTHORIZATION-003 — FINAL

**Status:** Minneapolis is **FOUNDER_AUTHORIZED_FOR_LAUNCH** on `pkg-minneapolis-mn-dd62d3082411d1d5`, bound to
registration commit `4c3abd44`.

**Candidate:** the exact authorized whole-site candidate is built and byte-identical across two sequential
assemblies. Deployment authorization `ptf-auth-minneapolis-003-3d7c53a1ba2a` is **AUTHORIZED** and **not consumed**.

**Not done:** nothing was deployed and Netlify was not invoked; live is unchanged.

**Branch:** `worker/ptf-minneapolis-mn-market-001` (worktree `C:\Atlas-Minneapolis-MN-Hardened-V1`).

**Commits:**
- `239c2836`: the founder decision (participation). This is the **BUILD commit** the candidate was assembled from.
- The final commit: the candidate manifest, the deployment authorization, the accounting, the live probe, the two
  market-local candidate modules and this report.

## 1. Current live (Phase 1)

Verified at 23:38Z, and again after both builds and the authorization at 04:03Z. Both times, unchanged:

| | |
|---|---|
| CURRENT LIVE SOURCE COMMIT | `aeb57df15d916262cb700bf7ff8550c738e4ddc6` (built_from `22ff1c94`) |
| CURRENT LIVE DEPLOYMENT | **`6ac264b79e70ce6a7db4baaf`**, record `ptf-deploy-portland-004-6ac264b79e70ce6a7db4baaf.json` |
| CURRENT LIVE BUNDLE | `d674d2898af11565559318500650bbee1c8e59fbf0fc3ea4040dacd3a7cfecea` (the on-disk live artifact `C:/t/pdx4a` carries the same digest) |
| CURRENT LIVE SITEMAP | `a50f1e343949ff65122e903b39a8bc9aed6318aef0a25b265aba6da772adf360` (the served `sitemap.xml` hashes to it) |
| CURRENT LIVE MARKETS | **41** (Detroit withheld) |
| CURRENT LIVE PROFILES | **3,819** |
| CURRENT LIVE RELEASE-INDEX ROUTES | **4,206** |
| CURRENT LIVE SERVED ROUTES | **4,280** |
| HOST VERIFIED | YES |

## 2. Registered package and registration evidence (Phases 2–3)

| | |
|---|---|
| PACKAGE | `pkg-minneapolis-mn-dd62d3082411d1d5`, `sha256:dd62d3082411d1d513b276453dd0b648f044f71c60bf0089e5a308176f0770e2` |
| REGISTRATION COMMIT | `4c3abd441aa88fa3f7c9500f208560296728a457`. It is an ancestor of HEAD, and the package blob there (`36bacc71…`) equals the tree's |
| state | SOURCE READY YES, COVERAGE READY YES, ACTIONABLE UNRESOLVED 0; census 258, PF 156, NP 66, resolved 222, unresolved 36 |
| FAST | 15/15; Rule J PASS (953 files / 937 HTML, bundle `cdd95614…`); Rule K PASS (BYTE_IDENTICAL) |
| receipt | `pkg-minneapolis-mn-dd62d3082411d1d5-eac0c8724c679c00.json`, CURRENTLY ELIGIBLE, 0 defects |
| registration evidence | AUTOMATIC base `e494698f`; AUTOMATIC classification COMPOSITE_FRESH_MARKET_DATA_ONLY; classifier checks 15/15; shared paths 0; unknown paths 0; FULL_REGRESSION_REQUIRED NO; broad runs 0 |
| reader safety | explicit-refusal PF 0, question-only PF 0, service-animal-only acceptance 0, misleading single fees 0 |

## 3. Founder authorization and participation (Phases 4–5)

`minneapolis_mn_launch_participation_003.py` records the decision. It extends the decision chain through
`launch_participation.extend_decision`, and lineage now has 52 records.

**Founder's words** (transcribed; no name signed; `decided_by: founder`): *"The founder explicitly authorizes launch of:
minneapolis-mn ONLY for: pkg-minneapolis-mn-dd62d3082411d1d5. Bind this decision to: 4c3abd44. The founder accepts the
current safe publication cohort: 156 pet-friendly profiles."*

| | |
|---|---|
| FOUNDER AUTHORIZATION | the participation decision of `PTF-MINNEAPOLIS-MN-FOUNDER-LAUNCH-AUTHORIZATION-003`, committed `239c2836` |
| AUTHORIZED PACKAGE / DIGEST | `pkg-minneapolis-mn-dd62d3082411d1d5` / `sha256:dd62d308…` |
| AUTHORIZED SOURCE COMMIT | `239c2836` (the BUILD commit, the candidate manifest's own `source_commit`) |
| AUTHORIZED REGISTRATION COMMIT | `4c3abd44` |
| AUTHORIZED PARENT | `6ac264b79e70ce6a7db4baaf`, release-index digest `sha256:fb129098…` |
| DECISION BASIS | the readiness packet, classification and staging-checks documents of PTF-MINNEAPOLIS-MN-REGISTRATION-AND-STAGING-002 (each pinned by sha256); every count and digest is read from committed state, and each founder decision is a guard |
| refused packages | `pkg-minneapolis-mn-5e356167a116c464` (source-ready shadow id) and `pkg-minneapolis-mn-0d325c39fe61fabc` (digest-only staging seal, never written). Neither is authorized |
| participation | minneapolis-mn SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH → **FOUNDER_AUTHORIZED_FOR_LAUNCH** |
| authorized set | 41 → 42: **gained minneapolis-mn only, lost none, other rows changed 0**, `decision_problems` `[]` |

**What the guards verified before writing:**

| decision | held rows | published |
|---|---|---|
| unresolved rows | 36 | 0 |
| named: Home2 Suites + Tru, 317 2nd Ave S | 2 held | 0 |
| named: Home2 Suites + Tru, 2415 E Old Shakopee Rd | 2 held | 0 |
| named: Comfort Inn + MainStay Suites MSP, 1321 E 78th St | 2 held | 0 |
| named: Microtel Inver Grove Heights | 1 held (EVIDENCE_HOLD) | 0 |
| founder-class rows (the 3 dual-brand buildings) | 6 | 0 |
| preopening rows | 0 | — |
| router-exhausted | 30 | 0 |
| timeshare / military | 0 / 0 | 0 |

Two further guard results:
- **Fees:** 35 / 47 / 16 / 0. Of the 58 published records whose quotes state more than one amount, 0 publish a
  single fee.
- **Twin Cities geography:** the registration gate passed; Portland coordinate residue 0, Oregon text residue 0,
  Portland findings labelled as Minneapolis 0; the four fixed identities are correct; every admitted row is in MN.

`identity_resolutions.json` was not written. The cosmetic "Building A / Building B" city field on the held Comfort Inn
/ MainStay rows was not touched, as instructed.

## 4. The exact authorized candidate (Phases 6–8)

`assemble_production_site` ran twice, **sequentially**, from BUILD commit `239c2836`, with short absolute paths.

**Build A** (`C:/t/msp4a`):
- started 23:44:27Z; manifests written 01:44:36Z;
- then the known post-manifest hang: output was stable across three snapshots (01:45:00 → 01:46:48Z) and CPU fell to
  about 1.5 s per 30 s, so it was terminated at 01:47:15Z.

**Build B** (`C:/t/msp4b`):
- started 01:47:20Z, after A was gone; manifests written 03:56:40Z;
- then the same hang: output was stable across four snapshots (03:56:46 → 03:59:25Z) and CPU was about 1.8 s per
  40 s, so it was terminated at 03:59:49Z.

Each build took about 2 h to its manifests, slower than Portland's ~107 min. Free memory on this 16 GB machine stayed
between 0.6 and 1.9 GB through both builds; the memory was held by applications this order did not start, and none
was touched. There was no failure.

| | |
|---|---|
| AUTHORIZED CANDIDATE BUNDLE | **`3d7c53a1ba2adc6ca9141e88384a7ef1e1e84abf7bdf21a4417ae664ff33af24`** |
| AUTHORIZED CANDIDATE SITEMAP | **`524d9d35c96668eaff45dfeb4f95edf7659ff815c7eb2d3f69a57658723ca7a1`** |
| DETERMINISM | **BYTE_IDENTICAL**: bundle A = bundle B, sitemap A = sitemap B, 24,002 files compared, **0 differing** |
| assembler gates | all pass (`all_gates_pass: true`) |
| PARENT LOOKUP / ROUTES PRESERVED | PASS / PASS (all 4,206 parent release-index routes carried; parent markets and profiles preserved) |
| UNCHANGED BUNDLES REUSED / REBUILT | **41 / 0** |
| MINNEAPOLIS BUNDLES BUILT | **1** |
| PHYSICAL FRAGMENTS RERENDERED | **42**: no release store is populated in this worktree, so the composer physically renders every fragment. Reported separately; it is not reuse |

**Accounting** (`markets/reports/minneapolis_mn_launch_authorization_003.json`). The two systems are counted from their
own sources:

| | |
|---|---:|
| CANDIDATE MARKETS | **42** |
| CANDIDATE PROFILES | **3,975** (from the bundle's own fragments) |
| CANDIDATE RELEASE-INDEX ROUTES | **4,377** |
| CANDIDATE SERVED ROUTES | **4,452** (from the bundle's own sitemap) |
| MINNEAPOLIS PROFILES | **156** |
| MINNEAPOLIS RELEASE-INDEX ROUTES | **171** (156 hotels + 14 corridors + hub) |
| MINNEAPOLIS SERVED ROUTES | **172** (+ its policy-comparison page) |

**Byte preservation vs the live artifact (`C:/t/pdx4a`):**
- 23,070 → 24,002 files: +932, all Minneapolis's; 0 removed;
- 1 changed, `sitemap.xml`;
- **0 prior-market files changed**, 0 unclassified.

## 5. Held content, geography, reader, fee and collision safety (Phases 9–13)

Checked on the BUILT artifact, by the route the site forms:

| | published |
|---|---:|
| UNAPPROVED MINNEAPOLIS PROFILES | **0** |
| DUAL-BRAND HOLDS (3 buildings) | **0 / 6** |
| MICROTEL INVER GROVE HEIGHTS | **0 / 1** |
| PREOPENING | **0** (none exists) |
| TIMESHARE / VACATION-OWNERSHIP, MILITARY | **0** (none exists) |
| router-exhausted | 0 / 30 |
| all unresolved | 0 / 36 |
| verified-no-pets as profiles | 0 / 66 |

**Twin Cities pages:**
- All 156 published profile pages state MN and their own postal code; 0 wrong.
- The fixed identities build exactly as committed: Ramada Plymouth (55441) has its profile page; Hotel Alma (55414),
  Celeste of St. Paul (55101, verified no-pets) and Northernaire Motel (55109) have none.
- PORTLAND COORDINATE RESIDUE **0**, OREGON TEXT RESIDUE **0**, PORTLAND COMMENT RESIDUE **0** (35 modules scanned);
  the Twin Cities envelope (44.73–45.14 N, 93.60–92.89 W) is the census's rule.

**Reader safety:** PET-FRIENDLY WITH EXPLICIT REFUSAL **0**, QUESTION-ONLY **0**, SERVICE-ANIMAL-ONLY ACCEPTANCE **0**,
no-pets quote without refusal 0. The shared reader was not changed.

**Fees:** MISLEADING SINGLE FEES **0**. 35 single-basis fees publish; 47 tiered and 16 unsafe fees stay withheld,
Hyatt Regency Bloomington's stay-length fee among them.

**Collisions:**
- CROSS-MARKET COLLISIONS **0**: duplicate excluded identities 0, names held by another market 0.
- BARE-CHAIN COLLISIONS **0**: Minneapolis carries no bare-chain-shaped name.

**Delta safety:**
- UNEXPECTED MARKET, PROFILE, ROUTE and SERVED-ROUTE DELTA `[]`.
- Prior markets, profiles, release-index routes and served routes lost: 0.
- `release_index.compare` passed.

**FAST receipt (Phase 14):** `…-eac0c8724c679c00.json` remains currently eligible (953 files / 937 HTML, bundle
`cdd95614…`, not `e3b0c442`). Augusta's historical empty receipt stays ineligible.

## 6. Gates and deployment authorization (Phases 15–16)

ALL ACCOUNTING GATES **PASS**. The candidate is **AUTHORIZED** and **DEPLOYABLE**, and **NOT DEPLOYED**.

`minneapolis_mn_deployment_authorization_003.py`:

| | |
|---|---|
| DEPLOYMENT AUTHORIZATION ID | **`ptf-auth-minneapolis-003-3d7c53a1ba2a`** |
| STATUS | **AUTHORIZED**; **CONSUMED = NO** (no deploy id, no deployment record) |
| AUTHORIZED BUNDLE / SITEMAP | `3d7c53a1…` / `524d9d35…`; 42 markets / 3,975 profiles / 4,452 served |
| source_commit | `239c2836`, the BUILD commit (not HEAD) |
| AUTHORIZED PARENT / rollback target | `6ac264b79e70ce6a7db4baaf` |
| authorized_by | `founder`, with the founder's words quoted in `authorization_source` |
| checks | `verify_manifest` `[]`, `verify_authorization` `[]`, `deployability_problems` `[]`, bound to the candidate bytes |
| candidate manifest | `deploy/netlify/global_deployment_manifest_candidate_minneapolis_003.json`; the LIVE manifest was not written |

Before writing, the writer refused if:
- any other authorization was still deployable (there were none);
- the readiness packet bound another package;
- participation did not read FOUNDER_AUTHORIZED_FOR_LAUNCH.

## 7. Live safety (Phase 17)

At 04:03Z, after both builds and the authorization (`markets/reports/minneapolis_mn_launch_authorization_live_probe_003.json`):
- **CURRENT LIVE DEPLOYMENT unchanged** (`6ac264b7`, 41 / 3,819 / 4,280, host verified).
- **SERVED SITEMAP unchanged** (`a50f1e34…`).
- **Minneapolis hub 404; all 172 projected Minneapolis routes 404.**
- Portland, Seattle, San Antonio, Austin, Phoenix, Denver, San Diego, Jacksonville FL, West Palm Beach, Fort
  Lauderdale and Augusta return **200**; Detroit **404**.

Both build processes were stopped (PIDs 9576 and 11668, each after its output was stable and its CPU idle). No process
created by this order remains.

## 8. For the deployment order

- **Deploy** `C:\t\msp4a\site`; its twin is `C:\t\msp4b`. Both artifacts were kept on disk.
- **Consume** `ptf-auth-minneapolis-003-3d7c53a1ba2a`.
- **Re-resolve live first.** If it is no longer `6ac264b7`, the parent has moved and this candidate is stale.
- **Expected after deploy:** 42 / 3,975 / 4,377 / 4,452, with Minneapolis's 172 routes returning 200.
- **Probe held rows** (the six dual-brand rows, Microtel Inver Grove Heights) at both the census slug and the site
  route; all must stay 404.

## FINAL ANSWERS

1. CURRENT LIVE DEPLOYMENT = 6ac264b79e70ce6a7db4baaf (Portland; source aeb57df1, sitemap a50f1e34…, unchanged)
2. CURRENT LIVE MARKETS = 41
3. MINNEAPOLIS PACKAGE = pkg-minneapolis-mn-dd62d3082411d1d5 (sha256:dd62d3082411d1d513b276453dd0b648f044f71c60bf0089e5a308176f0770e2)
4. REGISTRATION COMMIT = 4c3abd441aa88fa3f7c9500f208560296728a457
5. AUTOMATIC BASE DERIVES = YES (e494698f)
6. AUTOMATIC CLASSIFICATION = YES
7. REGISTRATION CLASS = COMPOSITE_FRESH_MARKET_DATA_ONLY
8. CLASSIFIER CHECKS = 15/15 PASS
9. SHARED PATHS = 0
10. UNKNOWN PATHS = 0
11. FULL_REGRESSION_REQUIRED = NO
12. FOUNDER AUTHORIZATION CREATED = YES
13. FOUNDER AUTHORIZATION ID = PTF-MINNEAPOLIS-MN-FOUNDER-LAUNCH-AUTHORIZATION-003 participation decision (decided_by founder), committed 239c2836
14. PARTICIPATION STATE = FOUNDER_AUTHORIZED_FOR_LAUNCH (authorized set 41 → 42, gained minneapolis-mn only)
15. PARENT LOOKUP = PASS
16. PARENT ROUTES PRESERVED = PASS
17. UNCHANGED BUNDLES REUSED = 41
18. UNCHANGED MARKETS REBUILT = 0
19. PHYSICAL FRAGMENTS RERENDERED = 42 (no release store populated; not reuse)
20. MINNEAPOLIS BUNDLES BUILT = 1
21. AUTHORIZED CANDIDATE BUNDLE = 3d7c53a1ba2adc6ca9141e88384a7ef1e1e84abf7bdf21a4417ae664ff33af24
22. AUTHORIZED CANDIDATE SITEMAP = 524d9d35c96668eaff45dfeb4f95edf7659ff815c7eb2d3f69a57658723ca7a1
23. CANDIDATE MARKETS = 42
24. CANDIDATE PROFILES = 3975
25. CANDIDATE RELEASE-INDEX ROUTES = 4377
26. CANDIDATE SERVED ROUTES = 4452
27. MINNEAPOLIS PROFILES = 156
28. MINNEAPOLIS RELEASE-INDEX ROUTES = 171
29. MINNEAPOLIS SERVED ROUTES = 172
30. UNAPPROVED MINNEAPOLIS PROFILES = 0
31. DUAL-BRAND HOLDS PUBLISHED = 0 / 6
32. MICROTEL INVER GROVE HEIGHTS PUBLISHED = 0
33. PREOPENING PROFILES PUBLISHED = 0
34. TIMESHARE PROFILES PUBLISHED = 0
35. PET-FRIENDLY WITH EXPLICIT REFUSAL = 0
36. QUESTION-ONLY PET-FRIENDLY = 0
37. SERVICE-ANIMAL-ONLY ACCEPTANCE = 0
38. MISLEADING SINGLE FEES = 0
39. PORTLAND COORDINATE RESIDUE = 0
40. OREGON TEXT RESIDUE = 0
41. CROSS-MARKET COLLISIONS = 0
42. FAST RECEIPT ELIGIBLE = YES (pkg-minneapolis-mn-dd62d3082411d1d5-eac0c8724c679c00.json)
43. CANDIDATE DETERMINISM = BYTE_IDENTICAL (24,002 files, 0 differing)
44. ALL RELEASE GATES = PASS
45. UNEXPECTED DELTA = [] (market, profile, route, served route)
46. CANDIDATE DEPLOYABLE = YES
47. DEPLOYMENT AUTHORIZATION CREATED = YES
48. DEPLOYMENT AUTHORIZATION ID = ptf-auth-minneapolis-003-3d7c53a1ba2a (AUTHORIZED, unconsumed)
49. CURRENT LIVE MODIFIED = NO
50. DEPLOYMENT PERFORMED = NO
51. MINNEAPOLIS LIVE = NO (hub + 172 routes 404)
52. origin == HEAD = YES (verified after push)
53. tree clean = YES (verified after push)
54. READY FOR MINNEAPOLIS PRODUCTION DEPLOYMENT = YES (deploy C:\t\msp4a\site, consume ptf-auth-minneapolis-003-3d7c53a1ba2a)

```
MINNEAPOLIS FOUNDER AUTHORIZATION = PASS
MINNEAPOLIS AUTHORIZED CANDIDATE = PASS
FULL_REGRESSION_REQUIRED = NO
PET-FRIENDLY RECORDS WITH EXPLICIT REFUSAL = 0
QUESTION-ONLY PET-FRIENDLY RECORDS = 0
SERVICE-ANIMAL-ONLY ACCEPTANCE = 0
UNAPPROVED MINNEAPOLIS PROFILES = 0
MISLEADING SINGLE FEES = 0
CURRENT LIVE MODIFIED = NO
MINNEAPOLIS DEPLOYED = NO
READY FOR MINNEAPOLIS PRODUCTION DEPLOYMENT = YES
```

STOP.
