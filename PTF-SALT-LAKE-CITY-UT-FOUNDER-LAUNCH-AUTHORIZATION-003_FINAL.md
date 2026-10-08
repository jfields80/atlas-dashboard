# PTF-SALT-LAKE-CITY-UT-FOUNDER-LAUNCH-AUTHORIZATION-003 — FINAL

**Status:** Salt Lake City / Park City is **FOUNDER_AUTHORIZED_FOR_LAUNCH** on `pkg-salt-lake-city-ut-6d474d2906ae01e0`,
bound to registration commit `2822639c`.

**Candidate:** the exact authorized whole-site candidate is built and byte-identical across two sequential assemblies.
Deployment authorization `ptf-auth-salt-lake-city-003-2738162fe62b` is **AUTHORIZED** and **not consumed**.

**Not done:** nothing was deployed, Netlify was not invoked, and live is unchanged.

**Branch:** `worker/ptf-salt-lake-city-ut-market-001` (worktree `C:\Atlas-Salt-Lake-City-UT-Hardened-V1`).

**Commits:**
- `6959e985` — the founder decision (participation). This is the **BUILD commit** the candidate was assembled from,
  and the authorization's `source_commit`.
- the final commit — the candidate manifest, the deployment authorization, the accounting, the live probe, the two
  market-local candidate modules, the residue-scan declaration and this report.

## 1. Current live (Phase 1)

Resolved mechanically (`release_index live-source --fetch --verify-host`) at 19:21:14Z (2026-10-07). It was unchanged
again before the authorization was written (00:37:26Z, 2026-10-08) and after it (00:40:21Z).

| | |
|---|---|
| CURRENT LIVE SOURCE COMMIT | `90624cd8392d6283e38834ddafa314423eba0ea8` (built_from `4c7e7b90`) |
| CURRENT LIVE DEPLOYMENT | **`6ac5ba3bcda3a604f7e467e0`** (record `ptf-deploy-new-orleans-004-6ac5ba3b…`) |
| CURRENT LIVE BUNDLE | `af70e0aa8a64496e53c67750668c33029cbda3cf318d9d3ecb1198af346a0a41` (the on-disk live artifact `C:/t/nola4a` carries the same digest) |
| CURRENT LIVE SITEMAP | `beb98d7a9f4687c337dfcbd5eaa1d301ac7d74eecddba5dcebf7d7b05c2a8508` (the served `sitemap.xml` hashes to it) |
| CURRENT LIVE MARKETS | **44** (Detroit withheld) |
| CURRENT LIVE PROFILES | **4,240** |
| CURRENT LIVE RELEASE-INDEX ROUTES | **4,663** (counted from the live index) |
| CURRENT LIVE SERVED ROUTES | **4,740** |
| HOST VERIFIED | YES |

## 2. The exact registered package (Phases 2–4)

The founder's console recap truncated the package id, so it was **not used**. The id is read mechanically: it is the
one package file registration commit `2822639c` added, and it equals the readiness packet's `sealed_package_id`.

| | |
|---|---|
| REGISTERED PACKAGE | **`pkg-salt-lake-city-ut-6d474d2906ae01e0`** |
| PACKAGE DIGEST | **`sha256:6d474d2906ae01e062dc5ef6158b3e167e244e5c780e2ab8478eb8ec36e0100d`** |
| REGISTRATION / BUILD COMMIT | `2822639c2866fde8ad5932fc8a42852d0cd3e917` — an ancestor of HEAD; the package blob there (`4f550310…`) equals the tree's |
| REGISTERED RECEIPT | `pkg-salt-lake-city-ut-6d474d2906ae01e0-7f8811ce601d32c4` (`sha256:7f8811ce…`), market bundle `42035f18…` |
| content | field-for-field the source-ready package `pkg-salt-lake-city-ut-f084558e8d8acabe` (census, PF / NP records, seed rows, partition, official routes, evidence references, unresolved rows, founder holds); same bundle |
| registration evidence | SALT LAKE CITY REGISTRATION PASS, STAGING PASS (34/34 gates); AUTOMATIC base `a67c8e75`; AUTOMATIC classification COMPOSITE_FRESH_MARKET_DATA_ONLY; classifier checks 15/15; ELIGIBLE YES; shared paths 0; unknown paths 0; FULL_REGRESSION_REQUIRED NO; broad runs 0; parent lookup / routes preserved PASS; 44 reused / 0 rebuilt |
| projected (staging) | Salt Lake City +133 profiles / +144 release-index routes / +145 served routes; candidate 45 / 4,373 / 4,807 / 4,885 |
| state | census 209, PF 133, NP 29, unresolved 47, ACTIONABLE UNRESOLVED 0, SOURCE READY YES, COVERAGE READY YES |
| package safety | Park City labelled SLC 0; explicit-refusal PF 0; question-only PF 0; service-animal-only 0; preopening / timeshare / private condo-residence published 0; misleading single fees 0; clone text / coordinate / boundary residue 0 / 0 / 0; cross-market collisions 0 |

## 3. Founder authorization and participation (Phases 5–8)

`salt_lake_city_ut_launch_participation_003.py` records the decision. It extends the chain through
`launch_participation.extend_decision`; the lineage now has 58 records.

**Founder's words** (transcribed; no name signed; `decided_by: founder`): *"The founder explicitly authorizes launch
of: salt-lake-city-ut ONLY for the exact CURRENT registered Salt Lake City package created by
PTF-SALT-LAKE-CITY-UT-REGISTRATION-AND-STAGING-002 and bound to: 2822639c. The founder approves the current safe
publication cohort: 133 pet-friendly profiles. Keep ALL unresolved / held rows unpublished."*

| | |
|---|---|
| FOUNDER AUTHORIZATION | the participation decision of `PTF-SALT-LAKE-CITY-UT-FOUNDER-LAUNCH-AUTHORIZATION-003`, committed `6959e985` |
| AUTHORIZED PACKAGE / DIGEST | `pkg-salt-lake-city-ut-6d474d2906ae01e0` / `sha256:6d474d29…` |
| AUTHORIZED REGISTRATION COMMIT | `2822639c` |
| AUTHORIZED PARENT | `6ac5ba3bcda3a604f7e467e0`, release-index digest `sha256:b5f65101…` |
| DECISION BASIS | the readiness packet, classification and staging-checks documents of the registration order (each pinned by sha256); every count and digest is read from committed state; each founder decision is a guard |
| refused packages | `pkg-salt-lake-city-ut-f084558e8d8acabe` (source-ready shadow id) and the superseded `cb60864b` seal; neither is authorized |
| participation | salt-lake-city-ut SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH → **FOUNDER_AUTHORIZED_FOR_LAUNCH** (not live) |
| authorized set | **44 → 45**: gained `salt-lake-city-ut` only, lost none, other rows changed 0; `decision_problems = []` |

**Guards verified before the decision was written:**
- **Unresolved rows:** 47, of which 0 publish.
- **Hyatt Place Cottonwood:** the only founder-class row, held; it publishes nothing as pet-friendly or as no-pets.
- **Hyatt Place Lehi:** held; no ZIP was invented.
- **The three Vail Canyons Village rows:** held; the server-error pages were not retried.
- **The preopening Ascent:** held.
- **Router-exhausted rows:** 45, all held.
- **Outside hotel inventory:** 19 timeshare, 172 private condo / residence / rental and 4 military-restricted identities; 0 published.
- **Fees:** 21 published / 39 tiered withheld / 13 unsafe withheld / 0 misleading. Of 55 published records that quote more than one amount, 0 publish a single fee.
- **Registration gates:** the municipality, Park City, canyon-resort and market-text gates all PASS.
- **Not touched:** `identity_resolutions.json` was not written; the shared reader and the shared factory were not touched.
- **Contracts:** `verify_all()` is 46/46 clean after the change.

## 4. The exact authorized candidate (Phases 9–10)

`assemble_production_site` was run from BUILD commit `6959e985` twice, **sequentially**, with short absolute paths:

- **Build A** (`C:/t/slc4a`, PID 17636):
  - Started 19:27:12Z and wrote its manifests at 21:58:05Z.
  - It then showed the known post-manifest hang. Output was stable across four snapshots (21:58:27 → 22:02:05Z: 26,380 files on disk, manifests unchanged) and CPU was near idle.
  - I validated the manifests (45 fragments, 26,378 hashed files) and terminated the process at 22:02:20Z.
- **Build B** (`C:/t/slc4b`, PID 29252):
  - Started 22:02:20Z, after A was gone, and wrote its manifests at 00:31:28Z.
  - Same hang. Output was stable across five snapshots (00:31:39 → 00:34:25Z) and CPU was idle (+1.5 s per 40 s); terminated 00:34:34Z.

Free memory stayed at about 1.7–2.8 GB on this 16 GB machine, and nothing failed.

| | |
|---|---|
| AUTHORIZED CANDIDATE BUNDLE | **`2738162fe62b5a5395c266c54d701e8d23b45da28ea02c6b1c47eebb3760df12`** |
| AUTHORIZED CANDIDATE SITEMAP | **`3806de5e5093cd63f570ab60f83a76f29712b9a9158cb6bfe2dce8f51eb89dc9`** |
| CANDIDATE FILE COUNT | **26,378** |
| DETERMINISM | **BYTE_IDENTICAL** — bundle A = B, sitemap A = B, file count A = B, 26,378 files compared, **0 differing** |
| assembler gates | all pass (`all_gates_pass: true`) |
| PARENT LOOKUP / ROUTES PRESERVED | PASS / PASS |
| UNCHANGED BUNDLES REUSED / REBUILT | **44 / 0** |
| SALT LAKE CITY BUNDLES BUILT | **1** |
| PHYSICAL FRAGMENTS RERENDERED | **45** — no release store is populated in this worktree, so the composer physically renders every fragment. This is reported separately and is not reuse |

## 5. Candidate accounting and delta (Phases 11–12)

The accounting is in `markets/reports/salt_lake_city_ut_launch_authorization_003.json`; each figure is derived from
its own source.

| | candidate | staging packet |
|---|---:|---:|
| CANDIDATE MARKETS | **45** | 45 |
| CANDIDATE PROFILES | **4,373** (from the bundle's own fragments) | 4,373 |
| CANDIDATE RELEASE-INDEX ROUTES | **4,807** | 4,807 |
| CANDIDATE SERVED ROUTES | **4,885** (from the bundle's own sitemap) | 4,885 |
| SALT LAKE CITY PROFILES | **133** | 133 |
| SALT LAKE CITY RELEASE-INDEX ROUTES | **144** (133 hotels + 10 corridors + hub) | 144 |
| SALT LAKE CITY SERVED ROUTES | **145** (+ its policy-comparison page) | 145 |

**Publishing corridors (10):** canyons-kimball-junction, cottonwood-heights-holladay, downtown-salt-lake-city, lehi,
midvale, murray, park-city, sandy, slc-airport-west-side, west-valley-city. The other 9 corridors stay below their
publication minimum, and none is forced.

**Byte preservation against the live artifact (`C:/t/nola4a`, 25,580 files):**
- +798 files, all of them Salt Lake City's.
- 0 removed.
- 1 changed (`sitemap.xml`).
- **0 prior-market files changed** and 0 unclassified.

**Delta against current live:**
- PRIOR MARKETS / PROFILES / RELEASE-INDEX ROUTES / SERVED ROUTES LOST: 0 / 0 / 0 / 0.
- UNEXPECTED MARKET / PROFILE / ROUTE / SERVED-ROUTE DELTA: `[]`.
- Salt Lake City is the only new market, and `release_index.compare` passed.

## 6. Held cohort, Park City, reader, fee and collision safety (Phases 5–6, 13–15)

Checked on the BUILT artifact by the route the site forms:

| | published |
|---|---:|
| UNAPPROVED SALT LAKE CITY PROFILES | **0** |
| HYATT PLACE COTTONWOOD | **0** |
| HYATT PLACE LEHI | **0** |
| VAIL CANYONS VILLAGE (Grand Summit, Silverado, Sundial) | **0 / 3** |
| PREOPENING (The Ascent) | **0** |
| router-exhausted | 0 / 45 |
| by disposition: ACCESS_BLOCKED / EVIDENCE_HOLD / IDENTITY_MISMATCH_HOLD / ROUTING_HOLD / SOURCE_SILENT | 0/16, 0/14, 0/1, 0/9, 0/7 |
| all unresolved | 0 / 47 |
| verified-no-pets as profiles | 0 / 29 |
| TIMESHARE / VACATION-OWNERSHIP | **0 / 19** |
| PRIVATE CONDO / RESIDENCE / RENTAL | **0 / 172** |
| UNBOUND RESORT-CAMPUS (Vail rows; canyon-resort audit 0) | **0** |
| MILITARY-RESTRICTED | 0 / 4 |

For each class above I checked for a profile page, sitemap route, release-index route, `/go/` file, PF record and
registry row. A held row whose route coincides with a published record's route would be reported; none does.

**Municipalities and Park City:**
- All 133 profile pages were checked. Every page's own structured address states UT, the municipality the census carries and that row's ZIP; **0 wrong**, and 0 pages carry another market's text.
- By county: Salt Lake 106, Summit 16, Utah 8, Davis 3.
- By municipality: Salt Lake City 51, Park City 16, West Valley City 16, Lehi 8, Midvale 8, Sandy 7, Murray 6, Draper 4, South Jordan 4, Cottonwood Heights 3, West Jordan 3, Woods Cross 3, Holladay 2, Bluffdale 1, Herriman 1.
- **Park City:** all 16 pages at a Park City code (84060 / 84068 / 84098) state `addressLocality: Park City`. **PARK CITY PROFILES LABELED SALT LAKE CITY = 0.**
- **The municipality traps build as committed:**
  - Grand Hyatt Deer Valley and Canopy by Hilton Deer Valley (84060) are Park City.
  - Holiday Inn Express Park City and Hyatt Centric Park City (84098) are Park City.
  - Fairfield Cottonwood (84121) is Holladay, and MainStay Fort Union (84121) is Cottonwood Heights.
  - Fairfield SLC South (84123, Murray) does not publish and has no page.

**Reader:** explicit-refusal PF 0, question-only 0, service-animal-only 0, NP quote without refusal 0, shared reader
disagrees 0. The shared reader is unchanged.

**Fees, on the page:**
- MISLEADING SINGLE FEES = 0: 21 single-basis fees publish, and 39 tiered plus 13 unsafe fees stay withheld.
- Each of the 21 pages with a fee renders exactly that one amount.
- None of the 52 withheld records renders a fee sentence, and none of the 112 fee-less pages renders one.
- No tiered, capped, conditional or multi-amount fee is flattened. AC Hotel Downtown's two-basis fee ("for entire stay" beside a per-night field) publishes no fee.

**Collisions:** cross-market 0, bare-chain names 0, bare-chain collisions 0, duplicate excluded identities 0, names
held by another market 0. No live profile is displaced.

## 7. FAST receipt, gates and deployment authorization (Phases 16–18)

**FAST receipt:** `…-7f8811ce601d32c4` is currently eligible and is the only receipt selected.
- RULE J NONEMPTY PASS: 819 files / 803 HTML, bundle `42035f18…`, not `e3b0c442`.
- RULE K NONVACUOUS PASS (BYTE_IDENTICAL); defects `[]`.
- Augusta's historical empty receipt stays ineligible.

ALL RELEASE GATES **PASS**: the bounded candidate accounting, the assembler gates, `verify_all` 46/46,
`decision_problems []` and clone residue 0/0/0. The candidate is **DEPLOYABLE** and **NOT DEPLOYED**. No broad
regression was run.

| | |
|---|---|
| DEPLOYMENT AUTHORIZATION ID | **`ptf-auth-salt-lake-city-003-2738162fe62b`** |
| STATUS | **AUTHORIZED**; **CONSUMED = NO**; **DEPLOY_ID = NONE** (no deployment record) |
| AUTHORIZED BUNDLE / SITEMAP | `2738162f…` / `3806de5e…`; 45 markets / 4,373 profiles / 4,885 served |
| bound to | market salt-lake-city-ut, package `pkg-salt-lake-city-ut-6d474d2906ae01e0`, founder decision `6959e985`, registration commit `2822639c` |
| source_commit | `6959e985dae864e5f3e276d81337be3ea3410d37`, the BUILD commit (not the final HEAD) |
| AUTHORIZED PARENT / rollback target | `6ac5ba3bcda3a604f7e467e0` |
| authorized_by | `founder`, with the founder's words quoted in `authorization_source` |
| checks | `verify_manifest []`, `verify_authorization []`, `deployability_problems []`, bound to the candidate bytes |
| candidate manifest | `deploy/netlify/global_deployment_manifest_candidate_salt_lake_city_003.json`; the LIVE manifest was not written |

**One adjustment, no data change:** the clone-residue scan first counted 6 hits in the new accounting module. They
are its own residue-detector regex and the Augusta empty-receipt canary (FAST Rule J). Both are now named constants
and are declared as cross-market references, exactly as the registration order declared its detectors. The scan reads
0 / 0 / 0, and the accounting re-ran to a byte-identical report.

## 8. Live safety (Phase 19)

At 00:40:21Z, after both builds and the authorization (`markets/reports/salt_lake_city_ut_launch_authorization_live_probe_003.json`):
- CURRENT LIVE DEPLOYMENT unchanged: 6ac5ba3b, 44 / 4,240 / 4,663 / 4,740, host verified.
- SERVED SITEMAP unchanged (`beb98d7a…`).
- Salt Lake City hub **404**, and all **145** projected routes **404**.
- **200:** New Orleans, Kansas City, Minneapolis, Portland, Seattle, San Antonio, Austin, Phoenix, Denver, San Diego, Jacksonville FL, West Palm Beach, Fort Lauderdale and Augusta.
- **404:** Detroit.

Both build processes (PIDs 17636 and 29252) were stopped only after their output was stable and their CPU idle. No
process created by this order remains. The pre-existing python process (PID 14180, started 2026-09-14) was left
untouched.

## FINAL ANSWERS

1. CURRENT LIVE DEPLOYMENT = 6ac5ba3bcda3a604f7e467e0
2. CURRENT LIVE MARKETS = 44
3. CURRENT LIVE PROFILES = 4,240
4. REGISTERED SALT LAKE CITY PACKAGE = pkg-salt-lake-city-ut-6d474d2906ae01e0
5. PACKAGE DIGEST = sha256:6d474d2906ae01e062dc5ef6158b3e167e244e5c780e2ab8478eb8ec36e0100d
6. REGISTRATION / BUILD COMMIT = 2822639c
7. AUTOMATIC BASE DERIVES = YES (a67c8e75)
8. AUTOMATIC CLASSIFICATION = YES
9. REGISTRATION CLASS = COMPOSITE_FRESH_MARKET_DATA_ONLY
10. CLASSIFIER CHECKS = 15/15 PASS
11. SHARED PATHS = 0
12. UNKNOWN PATHS = 0
13. FULL_REGRESSION_REQUIRED = NO
14. FOUNDER AUTHORIZATION CREATED = YES
15. FOUNDER AUTHORIZATION ID = the participation decision of PTF-SALT-LAKE-CITY-UT-FOUNDER-LAUNCH-AUTHORIZATION-003 (decided_by founder, lineage record 58)
16. FOUNDER DECISION COMMIT = 6959e985
17. PARTICIPATION STATE = FOUNDER_AUTHORIZED_FOR_LAUNCH
18. AUTHORIZED SET BEFORE / AFTER = 44 / 45 (gained salt-lake-city-ut, lost none)
19. PARENT LOOKUP = PASS
20. PARENT ROUTES PRESERVED = PASS
21. UNCHANGED BUNDLES REUSED = 44
22. UNCHANGED MARKETS REBUILT = 0
23. PHYSICAL FRAGMENTS RERENDERED = 45 (no release store in this worktree; not reuse)
24. SALT LAKE CITY BUNDLES BUILT = 1
25. AUTHORIZED CANDIDATE BUNDLE = 2738162fe62b5a5395c266c54d701e8d23b45da28ea02c6b1c47eebb3760df12
26. AUTHORIZED CANDIDATE SITEMAP = 3806de5e5093cd63f570ab60f83a76f29712b9a9158cb6bfe2dce8f51eb89dc9
27. CANDIDATE FILE COUNT = 26,378
28. CANDIDATE MARKETS = 45
29. CANDIDATE PROFILES = 4,373
30. CANDIDATE RELEASE-INDEX ROUTES = 4,807
31. CANDIDATE SERVED ROUTES = 4,885
32. SALT LAKE CITY PROFILES = 133
33. SALT LAKE CITY RELEASE-INDEX ROUTES = 144
34. SALT LAKE CITY SERVED ROUTES = 145
35. UNAPPROVED SALT LAKE CITY PROFILES = 0
36. HYATT PLACE COTTONWOOD PUBLISHED = 0
37. HYATT PLACE LEHI PUBLISHED = 0
38. PARK CITY PROFILES LABELED SALT LAKE CITY = 0
39. PREOPENING PROFILES PUBLISHED = 0
40. TIMESHARE / VACATION-OWNERSHIP PROFILES PUBLISHED = 0
41. PRIVATE CONDO / RESIDENCE PROFILES PUBLISHED = 0
42. PET-FRIENDLY WITH EXPLICIT REFUSAL = 0
43. QUESTION-ONLY PET-FRIENDLY = 0
44. SERVICE-ANIMAL-ONLY ACCEPTANCE = 0
45. MISLEADING SINGLE FEES = 0
46. CROSS-MARKET COLLISIONS = 0
47. FAST RECEIPT ELIGIBLE = YES
48. RULE J NONEMPTY = PASS (819 files / 803 HTML)
49. RULE K NONVACUOUS = PASS (BYTE_IDENTICAL)
50. CANDIDATE DETERMINISM = BYTE_IDENTICAL (26,378 files, 0 differing)
51. ALL RELEASE GATES = PASS
52. UNEXPECTED DELTA = []
53. CANDIDATE DEPLOYABLE = YES
54. DEPLOYMENT AUTHORIZATION CREATED = YES
55. DEPLOYMENT AUTHORIZATION ID = ptf-auth-salt-lake-city-003-2738162fe62b
56. CURRENT LIVE MODIFIED = NO
57. DEPLOYMENT PERFORMED = NO
58. SALT LAKE CITY LIVE = NO
59. origin == HEAD = YES (verified after push)
60. tree clean = YES (verified after push)
61. READY FOR SALT LAKE CITY PRODUCTION DEPLOYMENT = YES

SALT LAKE CITY FOUNDER AUTHORIZATION = PASS
SALT LAKE CITY AUTHORIZED CANDIDATE = PASS
FULL_REGRESSION_REQUIRED = NO
PARK CITY PROFILES LABELED SALT LAKE CITY = 0
PET-FRIENDLY RECORDS WITH EXPLICIT REFUSAL = 0
QUESTION-ONLY PET-FRIENDLY RECORDS = 0
SERVICE-ANIMAL-ONLY ACCEPTANCE = 0
UNAPPROVED SALT LAKE CITY PROFILES = 0
MISLEADING SINGLE FEES = 0
CURRENT LIVE MODIFIED = NO
SALT LAKE CITY DEPLOYED = NO
READY FOR SALT LAKE CITY PRODUCTION DEPLOYMENT = YES

STOP.

## For the deployment order

- **Deploy** `C:\t\slc4a\site`. Its twin is `C:\t\slc4b`; both are kept on disk.
- **Consume** `ptf-auth-salt-lake-city-003-2738162fe62b`.
- **Re-resolve live first.** If it is no longer `6ac5ba3b`, the parent has moved and this candidate is stale.
- **Expected after deploy:** 45 / 4,373 / 4,807 / 4,885, with Salt Lake City's 145 routes returning 200.
- **Probe held rows** at both the census slug and the site route; all must stay 404:
  - Hyatt Place Cottonwood and Hyatt Place Lehi;
  - Grand Summit, Silverado and Sundial at Canyons Village;
  - The Ascent.
- **Check that every Park City page still states Park City.**
- **Extend `tests/pettripfinder/pins/supersessions.json`** with the new live authorization at launch.
