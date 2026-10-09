# PTF-FORT-MYERS-FL-FOUNDER-LAUNCH-AUTHORIZATION-003 — FINAL

**Status:** Fort Myers / Cape Coral / Sanibel is **FOUNDER_AUTHORIZED_FOR_LAUNCH** on `pkg-fort-myers-fl-919f61116936bf5e`,
bound to commit **`6a425592`** (not the first registration commit `19c47422`).

**Candidate:** the exact authorized whole-site candidate is built and byte-identical across two sequential assemblies.
Deployment authorization `ptf-auth-fort-myers-003-aad66024bf06` is **AUTHORIZED** and **not consumed**.

**Not done:** nothing was deployed, Netlify was not invoked, and live is unchanged.

**Branch:** `worker/ptf-fort-myers-fl-market-001` (worktree `C:\Atlas-Fort-Myers-FL-Hardened-V1`).

**Commits:**
- `ab616e2e` — the founder decision (participation). This is the **BUILD commit** the candidate was assembled from and
  the authorization's `source_commit`.
- the final commit — the candidate manifest, the deployment authorization, the accounting, the live probe, the two
  market-local candidate modules and this report.

## 1. Current live (Phase 1)

Resolved mechanically (`release_index live-source --fetch --verify-host`) on 2026-10-08, before the founder decision
was written. It was unchanged again immediately before the deployment authorization was written (2026-10-09, about
05:24Z) and after it (05:25:57Z).

| | |
|---|---|
| CURRENT LIVE SOURCE COMMIT | `3d812f28de52555b15adaa5f9a19049cd064ed32` (built_from `6959e985`) |
| CURRENT LIVE DEPLOYMENT | **`6ac6f3d213d002249f9c3e67`** (record `ptf-deploy-salt-lake-city-004-6ac6f3d2…`) |
| CURRENT LIVE BUNDLE | `2738162fe62b5a5395c266c54d701e8d23b45da28ea02c6b1c47eebb3760df12` (the on-disk live artifact `C:/t/slc4a` carries the same digest) |
| CURRENT LIVE SITEMAP | `3806de5e5093cd63f570ab60f83a76f29712b9a9158cb6bfe2dce8f51eb89dc9` (the served `sitemap.xml` hashes to it) |
| CURRENT LIVE MARKETS | **45** (Detroit withheld) |
| CURRENT LIVE PROFILES | **4,373** |
| CURRENT LIVE RELEASE-INDEX ROUTES | **4,807** (counted from the live index) |
| CURRENT LIVE SERVED ROUTES | **4,885** |
| HOST VERIFIED | YES |

Production had not advanced, so the decision is bound to the current Salt Lake City parent.

## 2. The exact registered package (Phases 2–4)

The package id is **read mechanically, never typed**:
- It is the one package file under `markets/packages/fort-myers-fl` at `6a425592`.
- It is the file `19c47422` added.
- It equals the readiness packet's `sealed_package_id`.

| | |
|---|---|
| REGISTERED PACKAGE | **`pkg-fort-myers-fl-919f61116936bf5e`** |
| PACKAGE DIGEST | **`sha256:919f61116936bf5e23fe42f0aa745c87c6020a7896f7149b64ec603359ace47e`** |
| REGISTERED RECEIPT | `pkg-fort-myers-fl-919f61116936bf5e-71b99a5343da6d8f` (`sha256:71b99a53…`), market bundle `cc784255…` |
| REGISTRATION COMMIT | `19c47422` — added the package file; an ancestor of `6a425592` |
| FOUNDER-BINDING COMMIT | **`6a425592`** (`6a4255924335…`) — the BUILD commit the readiness packet was computed on |
| package bytes | blob `41d966e5…` is identical at `19c47422`, at `6a425592` and in the tree |
| after `6a425592` | only the registration order's 3 reports and its final report changed (`only_registration_reports_changed_since_binding: true`); the packet was prepared (14:50:31Z) after `6a425592` was committed (14:48:39Z) |
| content | field-for-field the source-ready package `pkg-fort-myers-fl-68b3cfa8bc4758c5` (census, PF / NP records, seed rows, partition, official routes, evidence references, unresolved rows, founder holds); same bundle |
| refused | the source-ready shadow id `pkg-fort-myers-fl-68b3cfa8bc4758c5`, and the source-ready order's failed first seal (FAST J FAIL; outputs discarded, never committed; no package file and no receipt exist). Only `919f6111` is on disk. |
| registration evidence | REGISTRATION PASS, STAGING PASS (35/35 gates), CRASH RECOVERY PASS; AUTOMATIC base `21dacb1c`; AUTOMATIC classification COMPOSITE_FRESH_MARKET_DATA_ONLY; classifier checks 15/15; 106 paths = 32 market-local / 13 registration / 61 derived / 0 shared / 0 unknown; GLOBAL AUTHORITY WRITE / CHECK PASS; FULL_REGRESSION_REQUIRED NO; broad runs 0 |
| projected (staging) | Fort Myers +57 profiles / +62 release-index routes / +63 served routes; candidate 46 / 4,430 / 4,869 / 4,948 |
| state | census 142, PF 57, NP 34, unresolved 51, ACTIONABLE UNRESOLVED 0, SOURCE READY YES, COVERAGE READY YES |

## 3. Documented nonblocking notes (Phase 4)

**A. Display label.**
- The sealed policy package's `market` field reads "Fort Myers / Cape Coral / Southwest Florida, Florida".
- The market document, release contract and hub page read "Fort Myers, Cape Coral & Sanibel, Florida".
- The sealed package was not altered.
- Routes come from the market id and each hotel's name, and identities come from the census, so the label affects neither. All 63 candidate routes equal the staged set exactly, and all 57 pages state their own municipality.
- **MARKET DISPLAY LABEL CAUSES ROUTE OR IDENTITY ERROR = NO.**

**B. Deliberate prior-market references.**
- `fort_myers_fl_release_contract_002.py` names Lexington (the project-wide contract template `lexington-ky.json`).
- It also names Salt Lake City (the "on the Salt Lake City-live hardened lineage" sentence: the live parent).
- These are implementation references and were not modified.
- The clone-residue detectors were re-run read-only over every `fort_myers_fl_*` module, including this order's three new ones. The code scan finds exactly those 2 lines; the registered data finds 0 text, 0 coordinate and 0 boundary hits. The 57 built pages carry 0 other-market text.
- **ACTIVE FORT MYERS DATA CLONE RESIDUE = 0.**

## 4. Founder authorization and participation (Phases 11–12)

`fort_myers_fl_launch_participation_003.py` records the decision. It extends the chain through
`launch_participation.extend_decision`; the lineage now has 60 records.

**Founder's words** (transcribed; no name signed; `decided_by: founder`): *"The founder explicitly authorizes launch of:
fort-myers-fl using ONLY the exact registered Fort Myers package mechanically resolved from the completed staging
order. Bind this decision to: 6a425592. The founder approves the existing safe publication cohort: 57 pet-friendly
profiles. No publication expansion is authorized. Keep ALL held / unresolved rows unpublished."*

| | |
|---|---|
| FOUNDER AUTHORIZATION | the participation decision of `PTF-FORT-MYERS-FL-FOUNDER-LAUNCH-AUTHORIZATION-003`, committed `ab616e2e` |
| AUTHORIZED PACKAGE / DIGEST | `pkg-fort-myers-fl-919f61116936bf5e` / `sha256:919f6111…` |
| FOUNDER-BINDING COMMIT | `6a425592` (not `19c47422`) |
| AUTHORIZED PARENT | `6ac6f3d213d002249f9c3e67`, release-index digest `sha256:6f594776…` |
| DECISION BASIS | the readiness packet, classification and staging-checks documents of the registration order (each pinned by sha256); every count and digest is read from committed state; each founder decision is a guard |
| participation | fort-myers-fl SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH → **FOUNDER_AUTHORIZED_FOR_LAUNCH** (not live) |
| authorized set | **45 → 46**: gained `fort-myers-fl` only, lost none, other rows changed 0; `decision_problems = []` |
| contracts | `verify_all()` 47/47 clean after the change |

All prior Fort Myers packages stay unauthorized. No `founder_authorization_superseded` entry exists or was written,
because this is a first authorization.

## 5. The exact authorized candidate (Phases 13–15)

`assemble_production_site` was run from BUILD commit `ab616e2e` twice, **sequentially**, with short absolute paths:

- **Build A** (`C:/t/fm4a`, PID 16820):
  - Started 23:46:57Z (2026-10-08) and wrote its manifests at 02:31:45Z.
  - It then showed the known post-manifest hang. Output was stable across four snapshots (02:32:06 → 02:34:36Z: 26,726 files on disk, manifest mtimes unchanged), and CPU was idle (+2 s per 50 s).
  - Terminated at 02:34:46Z.
- **Build B** (`C:/t/fm4b`, PID 12452):
  - Started 02:34:46Z, after A was stopped, and wrote its manifests at 05:19:26Z.
  - Same hang. Output was stable across four snapshots (05:19:50 → 05:22:19Z), and CPU was idle.
  - Terminated at 05:22:31Z.

The two whole-site builds never ran concurrently.

**Memory:** during build B, Claude Code reaped the read-only accounting run that had been started beside it, because the
system was low on memory. It was not restarted until build B had fully stopped (about 2.8 GB free). It then ran
**once**, in the foreground, as the founder approved.

| | |
|---|---|
| AUTHORIZED CANDIDATE BUNDLE | **`aad66024bf065e8b0858ef1b9b45faf57b3143bedfc644d17370b568da6c9795`** |
| AUTHORIZED CANDIDATE SITEMAP | **`f3f87e096d24aebbda6eed88406bf92284b52aafe1e71ed3a9ccc177813af86c`** |
| CANDIDATE FILE COUNT | **26,724** (hashed site files; plus the 2 manifests on disk) |
| DETERMINISM | **BYTE_IDENTICAL** — bundle A = B, sitemap A = B, file count A = B, 26,724 files compared, **0 differing** |
| assembler gates | all pass (`all_gates_pass: true`); manifest `generated_from_commit` = `ab616e2e` |
| PARENT LOOKUP / ROUTES PRESERVED | PASS / PASS |
| UNCHANGED BUNDLES REUSED / REBUILT | **45 / 0** |
| FORT MYERS BUNDLES BUILT | **1** |
| PHYSICAL FRAGMENTS RERENDERED | **46** — no release store is populated in this worktree, so the composer physically renders every fragment. This is reported separately and is not reuse. (Build A's terminated log flushed 39 market scopes; the manifest's 46 fragments is the count.) |

## 6. Candidate accounting and delta (Phases 16–17)

The accounting is in `markets/reports/fort_myers_fl_launch_authorization_003.json` (`ALL_ACCOUNTING_GATES: PASS`,
`problems: []`); each figure is derived from its own source.

| | candidate | projected |
|---|---:|---:|
| CANDIDATE MARKETS | **46** | 46 |
| CANDIDATE PROFILES | **4,430** (from the bundle's own fragments) | 4,430 |
| CANDIDATE RELEASE-INDEX ROUTES | **4,869** | 4,869 |
| CANDIDATE SERVED ROUTES | **4,948** (from the bundle's own sitemap) | 4,948 |
| FORT MYERS PROFILES | **57** | 57 |
| FORT MYERS RELEASE-INDEX ROUTES | **62** (57 hotels + 4 corridors + hub) | 62 |
| FORT MYERS SERVED ROUTES | **63** (+ its policy-comparison page) | 63 |

**Route sets:**
- The candidate's 63 Fort Myers served routes equal the 63 staged routes exactly (0 only-in-candidate, 0 only-in-staging).
- Publishing corridors (4): bonita-springs, colonial-cleveland, daniels-six-mile, rsw-airport-gateway.
- The other 10 corridors stay below their publication minimum; none is forced.

**Byte preservation against the live artifact (`C:/t/slc4a`, 26,378 files):**
- +346 files, all of them Fort Myers'.
- 0 removed.
- 1 changed (`sitemap.xml`).
- **0 prior-market files changed** and 0 unclassified.

**Delta against current live:**
- PRIOR MARKETS / PROFILES / RELEASE-INDEX ROUTES / SERVED ROUTES LOST: 0 / 0 / 0 / 0.
- UNEXPECTED MARKET / PROFILE / ROUTE / SERVED-ROUTE DELTA: `[]`.
- Fort Myers is the only new market, and `release_index.compare` passed.

## 7. Held cohort, operating status, boundaries, non-hotel, reader, fees, routes, collisions (Phases 5–10, 18)

Checked on the BUILT artifact, by the route the site forms (and, for the founder premises, by address on every page):

| | published |
|---|---:|
| UNAPPROVED FORT MYERS PROFILES | **0** (63 market pages = 57 profiles + hub + 4 corridors + comparison) |
| ALL 51 UNRESOLVED ROWS | **0 / 51** |
| COMFORT SUITES / MAINSTAY, 9455 OLD LUCKETT | **0 / 2**; 0 built pages at 9455 Luckett |
| QUALITY INN, 4760 S CLEVELAND (old Travelodge at that building) | **0 / 1**; 0 built pages at 4760 Cleveland; 0 Travelodge evidence migrated |
| LATITUDE 26 rows (incl. Waterfront Inn & Suites, 4701 Bonita Beach Rd) | **0 / 5**; 0 built pages at 4701 Bonita Beach |
| PINK SHELL / EDISON BEACH HOUSE | **0 / 2** |
| router-exhausted | 0 / 49 |
| by disposition: EVIDENCE_HOLD / IDENTITY_MISMATCH_HOLD / ROUTING_HOLD / SOURCE_SILENT | 0/8, 0/2, 0/25, 0/16 |
| verified-no-pets as profiles | 0 / 34 |
| TIMESHARE / VACATION-OWNERSHIP | **0 / 5** |
| VACATION RENTAL / PRIVATE CONDO / RESIDENCE | **0 / 121** |
| OTHER NON-HOTEL | 0 / 44 |

For each class above I checked for a profile page, sitemap route, release-index route, `/go/` file, PF record,
registry row and qualifying census row.

**Quality Inn / Travelodge:**
- The census keeps 4760 S Cleveland as one `SAME_IDENTITY_REBRAND_SUCCESSOR` row (Quality Inn, held).
- There are 0 seed, PF or NP rows at 4760, and the Quality Inn was not promoted.
- The one published Travelodge, "Travelodge by Wyndham Fort Myers/Cape Coral", stands at **13353 North Cleveland Avenue, 33903**, a different building.

**Latitude 26 Waterfront Inn & Suites:** keeps its registered treatment (`NOT_ADMITTED:OUTSIDE_MARKET`); no new Lee /
Collier ruling. `identity_resolutions.json` was not written; the shared reader and shared factory were not touched.

**Operating status:**
- All 57 published profiles are `CURRENTLY_OPEN`.
- **NONOPERATING / TEMPORARILY CLOSED / PERMANENTLY CLOSED / PREOPENING PROFILES = 0 / 0 / 0 / 0**, and status-unknown = 0.
- The 27 held rows with a closed or unknown status (3 permanently closed, 2 temporarily closed, 22 unknown) have no page.
- The 9 unbound nonoperating signals, including the closed Sanibel inns and the retired Motel 6 route, publish nothing.

**Municipality and boundary:**
- All 57 pages were checked. Each page's own structured address states FL, the census municipality and that row's ZIP, all in Lee County: **0 wrong**.
- By municipality: Fort Myers 34, Bonita Springs 6, Cape Coral 4, Estero 4, Fort Myers Beach 4, Captiva 3, North Fort Myers 2.
- **WRONG-CITY FORT MYERS IDENTITIES = 0, NAPLES PROFILES ADMITTED = 0.** No page names a Naples / Marco Island / Punta Gorda / Port Charlotte / Collier locality, and 0 pages carry another market's text.

**Reader:** explicit-refusal PF 0, question-only 0, service-animal-only 0, NP quote without refusal 0, shared reader
disagrees 0 (the source-ready audit's own logic over the registered documents).

**Fees:**
- 5 safe single-basis fees publish, and 22 tiered plus 5 unsafe fees stay withheld: **MISLEADING SINGLE FEES = 0**.
- On the page, each of the 5 fee pages renders exactly its one amount.
- None of the 27 withheld-fee records and none of the 52 fee-less pages renders a fee sentence.
- 30 published records quote more than one amount; 0 of them publishes a single fee.

**Route schemes:**
- All 283 Fort Myers `/go/` pages were checked: 171 go to an absolute http(s) URL with a host, 55 to `tel:` and 57 to internal paths.
- **INVALID ROUTE SCHEMES = 0, HTTP-LESS FIRST-PARTY ROUTES = 0.**
- The registered receipt's Rule J passed over the same pages. The shared validator was not modified.

**Collisions:**
- **CROSS-MARKET COLLISIONS 0**, bare-chain names 0, **BARE-CHAIN COLLISIONS 0**, **DUPLICATE EXCLUDED IDENTITIES 0** (registry 1,920 rows, 34 of them Fort Myers').
- No live profile moves or is displaced.

## 8. FAST receipt, gates and deployment authorization (Phases 19–21)

**FAST receipt:** `…-71b99a5343da6d8f` is **currently eligible** and is the only receipt selected or on disk for this
market. It records FAST 15/15.
- **RULE J NONEMPTY PASS:** 367 files / 351 HTML, bundle `cc784255…`, not `e3b0c442`.
- **RULE K NONVACUOUS PASS:** BYTE_IDENTICAL over 4 cold builds; defects `[]`.

**Ineligible receipts:**
- The source-ready shadow digest selects nothing.
- The failed first seal has no receipt: **FAILED FIRST-SEAL RECEIPT ELIGIBLE = NO**.
- The factory's empty receipts are located by reading every receipt directory, never by name. There is one (`pkg-augusta-ga-14806eca…`), and it stays ineligible.

**ALL RELEASE GATES PASS:**
- the bounded candidate accounting;
- the assembler gates;
- `verify_all` 47/47;
- `decision_problems []`;
- clone residue in active data 0/0/0;
- the authorization's own `verify_manifest`, `verify_authorization` and `deployability_problems`, all `[]`.

The candidate is **DEPLOYABLE** and **NOT DEPLOYED**. No broad regression was run.

| | |
|---|---|
| DEPLOYMENT AUTHORIZATION ID | **`ptf-auth-fort-myers-003-aad66024bf06`** |
| STATUS | **AUTHORIZED**; **CONSUMED = NO**; **DEPLOY_ID = NONE** (no deployment record) |
| AUTHORIZED BUNDLE / SITEMAP | `aad66024…` / `f3f87e09…`; 46 markets / 4,430 profiles / 4,948 served |
| bound to | market fort-myers-fl, package `pkg-fort-myers-fl-919f61116936bf5e`, founder decision `ab616e2e`, founder-binding commit `6a425592` |
| source_commit | `ab616e2e53f8f82c6a36e3dd6c73f2736946ca54`, the BUILD commit (not the final HEAD) |
| AUTHORIZED PARENT / ROLLBACK TARGET | `6ac6f3d213d002249f9c3e67` / `6ac6f3d213d002249f9c3e67` |
| authorized_by | `founder`, with the founder's words quoted in `authorization_source` |
| deployable authorizations now | exactly one: this one |
| candidate manifest | `deploy/netlify/global_deployment_manifest_candidate_fort_myers_003.json`; the LIVE manifest was not written |

The authorization did not exist when the accounting ran, so the report's `deployment_eligibility` reads
`checked: false`. Eligibility was verified directly after the write: `deployability_problems []`,
`verify_authorization []`, bound to bundle and sitemap, status AUTHORIZED, `deploy_id` None.

## 9. Live safety (Phase 22)

At 05:25:57Z (2026-10-09), after both builds and the authorization (`markets/reports/fort_myers_fl_launch_authorization_live_probe_003.json`):
- CURRENT LIVE DEPLOYMENT unchanged: 6ac6f3d2, 45 / 4,373 / 4,807 / 4,885, host verified.
- SERVED SITEMAP unchanged (`3806de5e…`, 4,885 routes).
- Fort Myers hub **404**, and all **63** projected routes **404**.
- **200:** Salt Lake City, New Orleans, Kansas City, Minneapolis, Portland, Seattle, San Antonio, Austin, Phoenix, Denver, San Diego, Jacksonville FL, West Palm Beach, Fort Lauderdale and Augusta.
- **404:** Detroit.

Both build processes (PIDs 16820 and 12452) were stopped only after their output was stable and their CPU idle. No
process created by this order remains. The pre-existing python process (PID 14180, started 2026-09-14) was left
untouched.

## FINAL ANSWERS

1. CURRENT LIVE DEPLOYMENT = 6ac6f3d213d002249f9c3e67
2. CURRENT LIVE SOURCE COMMIT = 3d812f28de52555b15adaa5f9a19049cd064ed32
3. CURRENT LIVE MARKETS = 45
4. CURRENT LIVE PROFILES = 4,373
5. REGISTERED FORT MYERS PACKAGE = pkg-fort-myers-fl-919f61116936bf5e
6. PACKAGE DIGEST = sha256:919f61116936bf5e23fe42f0aa745c87c6020a7896f7149b64ec603359ace47e
7. REGISTRATION COMMIT = 19c47422 (added the package; not the binding)
8. FOUNDER-BINDING COMMIT = 6a425592
9. AUTOMATIC BASE DERIVES = YES (21dacb1c)
10. REGISTRATION CLASS = COMPOSITE_FRESH_MARKET_DATA_ONLY
11. AUTOMATIC CLASSIFICATION = YES
12. CLASSIFIER CHECKS = 15/15 PASS
13. GLOBAL AUTHORITY WRITE = PASS
14. GLOBAL AUTHORITY CHECK = PASS
15. FULL_REGRESSION_REQUIRED = NO
16. FOUNDER AUTHORIZATION CREATED = YES
17. FOUNDER AUTHORIZATION ID = the participation decision of PTF-FORT-MYERS-FL-FOUNDER-LAUNCH-AUTHORIZATION-003 (decided_by founder, lineage record 60)
18. FOUNDER DECISION COMMIT = ab616e2e
19. PARTICIPATION STATE = FOUNDER_AUTHORIZED_FOR_LAUNCH
20. AUTHORIZED SET BEFORE / AFTER = 45 / 46 (gained fort-myers-fl, lost none)
21. PARENT LOOKUP = PASS
22. PARENT ROUTES PRESERVED = PASS
23. UNCHANGED BUNDLES REUSED = 45
24. UNCHANGED MARKETS REBUILT = 0
25. PHYSICAL FRAGMENTS RERENDERED = 46 (no release store in this worktree; not reuse)
26. FORT MYERS BUNDLES BUILT = 1
27. AUTHORIZED CANDIDATE BUNDLE = aad66024bf065e8b0858ef1b9b45faf57b3143bedfc644d17370b568da6c9795
28. AUTHORIZED CANDIDATE SITEMAP = f3f87e096d24aebbda6eed88406bf92284b52aafe1e71ed3a9ccc177813af86c
29. CANDIDATE FILE COUNT = 26,724
30. CANDIDATE DETERMINISM = BYTE_IDENTICAL (26,724 files, 0 differing)
31. CANDIDATE MARKETS = 46
32. CANDIDATE PROFILES = 4,430
33. CANDIDATE RELEASE-INDEX ROUTES = 4,869
34. CANDIDATE SERVED ROUTES = 4,948
35. FORT MYERS PROFILES = 57
36. FORT MYERS RELEASE-INDEX ROUTES = 62
37. FORT MYERS SERVED ROUTES = 63
38. UNAPPROVED FORT MYERS PROFILES = 0
39. ALL 51 UNRESOLVED ROWS PUBLISHED = 0
40. COMFORT SUITES OLD LUCKETT PUBLISHED = 0
41. MAINSTAY OLD LUCKETT PUBLISHED = 0
42. OLD TRAVELODGE S CLEVELAND PUBLISHED = 0
43. QUALITY INN S CLEVELAND PUBLISHED = 0
44. LATITUDE 26 WATERFRONT PUBLISHED = 0
45. PINK SHELL PUBLISHED = 0
46. EDISON BEACH HOUSE PUBLISHED = 0
47. WRONG-CITY FORT MYERS IDENTITIES = 0
48. NAPLES PROFILES ADMITTED = 0
49. NONOPERATING PROFILES PUBLISHED = 0
50. TIMESHARE / VACATION-OWNERSHIP PROFILES PUBLISHED = 0
51. PET-FRIENDLY WITH EXPLICIT REFUSAL = 0
52. QUESTION-ONLY PET-FRIENDLY = 0
53. SERVICE-ANIMAL-ONLY ACCEPTANCE = 0
54. MISLEADING SINGLE FEES = 0
55. INVALID ROUTE SCHEMES = 0
56. ACTIVE DATA CLONE RESIDUE = 0
57. CROSS-MARKET COLLISIONS = 0
58. FAST RECEIPT ELIGIBLE = YES
59. FAILED FIRST-SEAL RECEIPT ELIGIBLE = NO
60. RULE J NONEMPTY = PASS (367 files / 351 HTML)
61. RULE K NONVACUOUS = PASS (BYTE_IDENTICAL, 4 cold builds)
62. ALL RELEASE GATES = PASS
63. UNEXPECTED DELTA = []
64. CANDIDATE DEPLOYABLE = YES
65. DEPLOYMENT AUTHORIZATION CREATED = YES
66. DEPLOYMENT AUTHORIZATION ID = ptf-auth-fort-myers-003-aad66024bf06
67. CURRENT LIVE MODIFIED = NO
68. DEPLOYMENT PERFORMED = NO
69. FORT MYERS LIVE = NO
70. origin == HEAD = YES (verified after push)
71. tree clean = YES (verified after push)
72. READY FOR FORT MYERS PRODUCTION DEPLOYMENT = YES

FORT MYERS FOUNDER AUTHORIZATION = PASS
FORT MYERS AUTHORIZED CANDIDATE = PASS
FOUNDER-BINDING COMMIT = 6a425592
FULL_REGRESSION_REQUIRED = NO
WRONG-CITY FORT MYERS IDENTITIES = 0
NAPLES PROFILES ADMITTED = 0
NONOPERATING PROFILES PUBLISHED = 0
PET-FRIENDLY RECORDS WITH EXPLICIT REFUSAL = 0
QUESTION-ONLY PET-FRIENDLY RECORDS = 0
SERVICE-ANIMAL-ONLY ACCEPTANCE = 0
UNAPPROVED FORT MYERS PROFILES = 0
MISLEADING SINGLE FEES = 0
INVALID ROUTE SCHEMES = 0
CURRENT LIVE MODIFIED = NO
FORT MYERS DEPLOYED = NO
READY FOR FORT MYERS PRODUCTION DEPLOYMENT = YES

STOP.

## For the deployment order

- **Deploy** `C:\t\fm4a\site`. Its twin is `C:\t\fm4b`; both are kept on disk.
- **Consume** `ptf-auth-fort-myers-003-aad66024bf06`.
- **Re-resolve live first.** If it is no longer `6ac6f3d2`, the parent has moved and this candidate is stale.
- **Expected after deploy:** 46 / 4,430 / 4,869 / 4,948, with Fort Myers' 63 routes returning 200.
- **Probe held rows** at both the census slug and the site route; all must stay 404:
  - Comfort Suites and MainStay Suites (9455 Old Luckett);
  - Quality Inn (4760 S Cleveland);
  - the Latitude 26 rows;
  - Pink Shell;
  - Edison Beach House.
- **Check addresses:** every page must still state its own municipality, and the published Travelodge must stay at 13353 N Cleveland.
- **Extend `tests/pettripfinder/pins/supersessions.json`** with the new live authorization at launch.
