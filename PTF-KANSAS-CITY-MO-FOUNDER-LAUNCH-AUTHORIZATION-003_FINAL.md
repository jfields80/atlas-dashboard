# PTF-KANSAS-CITY-MO-FOUNDER-LAUNCH-AUTHORIZATION-003 — FINAL

**Status:** Kansas City is **FOUNDER_AUTHORIZED_FOR_LAUNCH** on `pkg-kansas-city-mo-140e35291a2195c3`, bound to
registration commit `d054d6c0`.

**Candidate:** the exact authorized whole-site candidate is built and byte-identical across two sequential assemblies.
Deployment authorization `ptf-auth-kansas-city-003-6a35c23829f9` is **AUTHORIZED** and **not consumed**.

**Not done:** nothing was deployed and Netlify was not invoked; live is unchanged.

**Branch:** `worker/ptf-kansas-city-mo-market-001` (worktree `C:\Atlas-Kansas-City-MO-Hardened-V1`).

**Commits:**
- `c6609370` — the founder decision (participation). This is the **BUILD commit** the candidate was assembled from.
- the final commit — the candidate manifest, the deployment authorization, the accounting, the live probe, the two
  market-local candidate modules and this report.

## 1. Current live (Phase 1)

Verified at 03:32Z and again after both builds and the authorization at 08:21Z — unchanged both times:

| | |
|---|---|
| CURRENT LIVE SOURCE COMMIT | `d57623030b95f153ec3fc82c7149c5960efc6625` (built_from `239c2836`) |
| CURRENT LIVE DEPLOYMENT | **`6ac3bfda7b585d009f007620`** (record `ptf-deploy-minneapolis-004-…`) |
| CURRENT LIVE BUNDLE | `3d7c53a1ba2adc6ca9141e88384a7ef1e1e84abf7bdf21a4417ae664ff33af24` (the on-disk live artifact `C:/t/msp4a` carries the same digest) |
| CURRENT LIVE SITEMAP | `524d9d35c96668eaff45dfeb4f95edf7659ff815c7eb2d3f69a57658723ca7a1` (the served `sitemap.xml` hashes to it) |
| CURRENT LIVE MARKETS | **42** (Detroit withheld) |
| CURRENT LIVE PROFILES | **3,975** |
| CURRENT LIVE RELEASE-INDEX ROUTES | **4,377** |
| CURRENT LIVE SERVED ROUTES | **4,452** |
| HOST VERIFIED | YES |

## 2. Registered package and registration evidence (Phases 2–3)

| | |
|---|---|
| PACKAGE | `pkg-kansas-city-mo-140e35291a2195c3`, `sha256:140e35291a2195c359b0c4210741f2d8acff9250f4555cdadd3549e931145167` |
| REGISTRATION COMMIT | `d054d6c08525fc8f050bafb472928a24004533b4` — an ancestor of HEAD; the package blob there (`49067c64…`) equals the tree's |
| state | SOURCE READY YES, COVERAGE READY YES, ACTIONABLE UNRESOLVED 0; census 290, PF 161, NP 60, resolved 221, unresolved 69 |
| FAST | 15/15; Rule J PASS (976 files / 960 HTML, bundle `f454f0bd…`); Rule K PASS (BYTE_IDENTICAL) |
| receipt | `pkg-kansas-city-mo-140e35291a2195c3-b0245f8a1e4420b7`, CURRENTLY ELIGIBLE (the only one selected), 0 defects |
| registration evidence | AUTOMATIC base `e74dee3b`; AUTOMATIC classification COMPOSITE_FRESH_MARKET_DATA_ONLY; classifier checks 15/15; shared paths 0; unknown paths 0; FULL_REGRESSION_REQUIRED NO; broad runs 0 |
| two states | Missouri 189, Kansas 101; KS→MO mislabels 0, MO→KS 0 |
| reader / fee safety | explicit-refusal PF 0, question-only PF 0, service-animal-only 0, misleading single fees 0 |

## 3. Founder authorization and participation (Phases 4–5)

`kansas_city_mo_launch_participation_003.py` records the decision, extending the chain through
`launch_participation.extend_decision` (lineage now 54 records).

**Founder's words** (transcribed; no name signed; `decided_by: founder`): *"The founder explicitly authorizes launch
of: kansas-city-mo ONLY for: pkg-kansas-city-mo-140e35291a2195c3. Bind this decision to: d054d6c0. Do NOT authorize:
pkg-kansas-city-mo-24718ac004c967b8 or any earlier Kansas City package. The founder accepts the current safe
publication cohort: 161 pet-friendly profiles."*

| | |
|---|---|
| FOUNDER AUTHORIZATION | the participation decision of `PTF-KANSAS-CITY-MO-FOUNDER-LAUNCH-AUTHORIZATION-003`, committed `c6609370` |
| AUTHORIZED PACKAGE / DIGEST | `pkg-kansas-city-mo-140e35291a2195c3` / `sha256:140e3529…` |
| AUTHORIZED SOURCE COMMIT | `c6609370` (the BUILD commit; the candidate manifest's own `source_commit`) |
| AUTHORIZED REGISTRATION COMMIT | `d054d6c0` |
| AUTHORIZED PARENT | `6ac3bfda7b585d009f007620`, release-index digest `sha256:b7764d5a…` |
| DECISION BASIS | the readiness packet, classification and staging-checks documents of PTF-KANSAS-CITY-MO-REGISTRATION-AND-STAGING-002 (each pinned by sha256); every count and digest read from committed state; each founder decision is a guard |
| refused packages | `pkg-kansas-city-mo-24718ac004c967b8` (source-ready shadow id) and `pkg-kansas-city-mo-154f5c6b4f5d360c` (the source-ready order's first, superseded seal, never committed). Neither is authorized |
| participation | kansas-city-mo SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH → **FOUNDER_AUTHORIZED_FOR_LAUNCH** |
| authorized set | 42 → 43: **gained kansas-city-mo only, lost none, other rows changed 0**, `decision_problems = []` |

Guards verified before writing: 69 unresolved rows, 0 published; the three dual-brand buildings (6 rows), both
rebrand holds (outside the admitted census), ESA Tiffany Springs, the Crossland route identity and the 4 preopening
hotels all held and 0 published; 59 router-exhausted held; fees 25 / 37 / 17 / 0 (of 59 published records quoting
more than one amount, 0 publish a single fee); 1 timeshare and 2 military-restricted identities outside hotel
inventory; the two-state and market-text registration gates PASS. `identity_resolutions.json` was not written; no
rebrand hold was resolved; the Crossland page was not revisited; no CAPTCHA was touched.

## 4. The exact authorized candidate (Phases 6–8)

`assemble_production_site` from BUILD commit `c6609370`, twice, **sequentially**, short absolute paths:

- **Build A** (`C:/t/kc4a`): started 03:35:55Z; manifests 05:56:42Z; then the known post-manifest hang — output stable
  across four snapshots (05:57:06 → 05:59:46Z), CPU ~2 s per 40 s — terminated 05:59:54Z.
- **Build B** (`C:/t/kc4b`): started 06:00:02Z, after A was gone; manifests 08:13:20Z; same hang — stable across four
  snapshots (08:13:47 → 08:16:27Z), CPU ~2 s per 45 s — terminated 08:16:36Z.

Free memory stayed 1.0–1.9 GB on this 16 GB machine through both builds (held by applications this order did not
start, none touched). No failure.

| | |
|---|---|
| AUTHORIZED CANDIDATE BUNDLE | **`6a35c23829f9c0a0a1713acc721f3fcf317a94d7f57120379ffc951fdc60ed5f`** |
| AUTHORIZED CANDIDATE SITEMAP | **`3d5d9425a4e0a90b6aca13f3d02866a815ebc934df8382e4fcf03c0ecc10967b`** |
| DETERMINISM | **BYTE_IDENTICAL** — bundle A = B, sitemap A = B, 24,957 files compared, **0 differing** |
| assembler gates | all pass (`all_gates_pass: true`) |
| PARENT LOOKUP / ROUTES PRESERVED | PASS / PASS |
| UNCHANGED BUNDLES REUSED / REBUILT | **42 / 0** |
| KANSAS CITY BUNDLES BUILT | **1** |
| PHYSICAL FRAGMENTS RERENDERED | **43** — no release store is populated in this worktree, so the composer physically renders every fragment. Reported separately; not reuse |

Accounting (`markets/reports/kansas_city_mo_launch_authorization_003.json`), each system from its own source:

| | |
|---|---:|
| CANDIDATE MARKETS | **43** |
| CANDIDATE PROFILES | **4,136** (from the bundle's own fragments) |
| CANDIDATE RELEASE-INDEX ROUTES | **4,552** |
| CANDIDATE SERVED ROUTES | **4,628** (from the bundle's own sitemap) |
| KANSAS CITY PROFILES | **161** |
| KANSAS CITY RELEASE-INDEX ROUTES | **175** (161 hotels + 13 corridors + hub) |
| KANSAS CITY SERVED ROUTES | **176** (+ its policy-comparison page) |

Byte preservation vs the live artifact (`C:/t/msp4a`): +955 files, all Kansas City's; 0 removed; 1 changed
(`sitemap.xml`); **0 prior-market files changed**; 0 unclassified.

## 5. Held content, two-state, reader, fee, text and collision safety (Phases 9–13)

Checked on the BUILT artifact by the route the site forms:

| | published |
|---|---:|
| UNAPPROVED KANSAS CITY PROFILES | **0** |
| DUAL-BRAND HOLDS (3 buildings) | **0 / 6** |
| HGI OVERLAND PARK REBRAND HOLD | **0** |
| SLEEP INN OLATHE REBRAND HOLD | **0** |
| ESA TIFFANY SPRINGS | **0** |
| CROSSLAND ROUTE IDENTITY | **0** |
| PREOPENING | **0 / 4** |
| TIMESHARE / MILITARY-RESTRICTED | **0 / 0** |
| router-exhausted | 0 / 59 |
| all unresolved | 0 / 69 |
| verified-no-pets as profiles | 0 / 60 |

- **Two states:** all 161 profile pages checked — 96 Missouri, 65 Kansas — and every page's own structured address
  (`addressRegion` + `postalCode`) states the state its ZIP is in and that ZIP; 0 wrong. The cross-state name traps
  build exactly as committed (Sonesta Select "South Overland Park" 64131 MO, ESA "Shawnee Mission" 66202 KS, Drury
  "Independence" 64015 MO published; Hotel Lotus Merriam 66203 KS held).
- **Market text:** 0 Kansas City pages carry Minneapolis / St. Paul or Portland / Oregon text (520 Minnesota Avenue is
  a Kansas City, Kansas street); the registered documents' residue is 0 and the label is Kansas City's.
- **Reader:** explicit-refusal PF 0, question-only 0, service-animal-only 0, NP quote without refusal 0. Shared reader
  unchanged.
- **Fees:** MISLEADING SINGLE FEES 0; 25 single-basis publish; 37 tiered and 17 unsafe stay withheld.
- **Collisions:** cross-market 0, bare-chain names 0, bare-chain collisions 0, duplicate excluded identities 0.
- **Delta:** unexpected market / profile / route / served-route delta `[]`; prior markets, profiles, index routes and
  served routes lost 0; `release_index.compare` passed.

**FAST receipt (Phase 14):** `…-b0245f8a1e4420b7` remains currently eligible (976 files / 960 HTML, bundle `f454f0bd…`,
not `e3b0c442`). Augusta's historical empty receipt stays ineligible.

## 6. Gates and deployment authorization (Phases 15–16)

ALL ACCOUNTING GATES **PASS**. The candidate is **AUTHORIZED** and **DEPLOYABLE**, and **NOT DEPLOYED**.

| | |
|---|---|
| DEPLOYMENT AUTHORIZATION ID | **`ptf-auth-kansas-city-003-6a35c23829f9`** |
| STATUS | **AUTHORIZED**; **CONSUMED = NO** (no deploy id, no deployment record) |
| AUTHORIZED BUNDLE / SITEMAP | `6a35c238…` / `3d5d9425…`; 43 markets / 4,136 profiles / 4,628 served |
| source_commit | `c6609370`, the BUILD commit (not HEAD) |
| AUTHORIZED PARENT / rollback target | `6ac3bfda7b585d009f007620` |
| authorized_by | `founder`, with the founder's words quoted in `authorization_source` |
| checks | `verify_manifest []`, `verify_authorization []`, `deployability_problems []`, bound to the candidate bytes |
| candidate manifest | `deploy/netlify/global_deployment_manifest_candidate_kansas_city_003.json`; the LIVE manifest was not written |

`verify_all()` 44/44 clean after the participation change.

## 7. Live safety (Phase 17)

At 08:21Z, after both builds and the authorization (`markets/reports/kansas_city_mo_launch_authorization_live_probe_003.json`):
CURRENT LIVE DEPLOYMENT unchanged (6ac3bfda, 42 / 3,975 / 4,452, host verified); SERVED SITEMAP unchanged
(`524d9d35…`); Kansas City hub and all **176** projected routes **404**; Minneapolis, Portland, Seattle, San Antonio,
Austin, Phoenix, Denver, San Diego, Jacksonville FL, West Palm Beach, Fort Lauderdale and Augusta **200**; Detroit
**404**.

Both build processes (PIDs 26832, 10992) were stopped only after their output was stable and CPU idle. No process
created by this order remains (python 14180 predates it and was left alone).

## 8. For the deployment order

- **Deploy** `C:\t\kc4a\site` (twin `C:\t\kc4b`; both kept on disk).
- **Consume** `ptf-auth-kansas-city-003-6a35c23829f9`.
- **Re-resolve live first.** If it is no longer `6ac3bfda`, the parent has moved and this candidate is stale.
- **Expected after deploy:** 43 / 4,136 / 4,552 / 4,628, with Kansas City's 176 routes returning 200.
- **Probe held rows** (6 dual-brand, both rebrand holds, ESA Tiffany Springs, the Crossland identity, 4 preopening) at
  both the census slug and the site route; all must stay 404.
- Extend `tests/pettripfinder/pins/supersessions.json` with the new live authorization at launch.
