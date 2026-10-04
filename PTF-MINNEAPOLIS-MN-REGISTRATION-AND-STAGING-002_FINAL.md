# PTF-MINNEAPOLIS-MN-REGISTRATION-AND-STAGING-002 — FINAL

**Status:** Minneapolis / St. Paul / Twin Cities is **REGISTERED and STAGED**. The readiness packet is
**AUTHORIZATION_READY**; the founder status is AWAITING_FOUNDER_AUTHORIZATION.

**Not done:** nothing was deployed; there is no founder launch authorization and no deployment authorization; current
live is unchanged.

**Branch:** `worker/ptf-minneapolis-mn-market-001` (worktree `C:\Atlas-Minneapolis-MN-Hardened-V1`).

**Commits:**
- `4c3abd44`: the registration transaction. This is the **BUILD commit** a founder authorization must bind.
- The final commit: the automatic classification, the readiness packet, the live probe and this report.

## 1. Current live (Phase 1)

Resolved with the canonical resolver (`release_index live-source --fetch --verify-host`) at 20:42Z, and again after
staging at 21:05Z. Both times it was unchanged:

| | |
|---|---|
| CURRENT LIVE SOURCE COMMIT | `aeb57df15d916262cb700bf7ff8550c738e4ddc6` (built_from `22ff1c94`) |
| CURRENT LIVE DEPLOYMENT | **`6ac264b79e70ce6a7db4baaf`**, record `ptf-deploy-portland-004-6ac264b79e70ce6a7db4baaf.json` |
| CURRENT LIVE BUNDLE | `d674d2898af11565559318500650bbee1c8e59fbf0fc3ea4040dacd3a7cfecea` |
| CURRENT LIVE SITEMAP | `a50f1e343949ff65122e903b39a8bc9aed6318aef0a25b265aba6da772adf360` |
| CURRENT LIVE MARKETS | **41** (Detroit withheld) |
| CURRENT LIVE PROFILES | **3,819** |
| CURRENT LIVE RELEASE-INDEX ROUTES | **4,206** (participating markets' index routes, counted from the live index) |
| CURRENT LIVE SERVED ROUTES | **4,280** |
| HOST VERIFIED | YES |

Live had not advanced, so registration ran against current production.

## 2. Automatic base (Phase 2)

`registration_release_lane.derive_registration_base('minneapolis-mn', aeb57df1…)` returned
**`e494698f7ee846f9a6e314111828b6c3ae9cfa80`** (the Portland deploy-final commit) with no manual input. The `packet`
step re-derived the same base on its own. No base or classification was supplied.

- AUTOMATIC BASE DERIVES = **YES**
- DERIVED BASE = `e494698f`
- CURRENT LIVE LINEAGE COMMIT = `aeb57df1`

## 3. Source state, resolved mechanically (Phases 3–4)

All four sources agree on one source-ready state:

| | |
|---|---|
| SOURCE-READY HEAD | `1a8a8e9ded28cc51ef70df8949408bf6fbbd261b` (origin == HEAD at the start) |
| SOURCE PACKAGE | `pkg-minneapolis-mn-5e356167a116c464`, the only shadow package on disk, sealed from `4b019137` |
| SOURCE PACKAGE DIGEST | `sha256:5e356167a116c464a4d9e78dbc5907a5b7299ed4f5a5e23dbf87301d7f5cef34`, equal to the digest the source-ready report states |
| SOURCE FAST RECEIPT | `pkg-minneapolis-mn-5e356167a116c464-88a5ed7276ec6ba9.json`. It is the only receipt `eligible_receipts` returns; its PACKAGE_DIGEST is the package's; stored ELIGIBLE YES; no output defects; FAST 15/15 |

Counts read from the package, not assumed:

| | |
|---|---|
| census | 258: PF 156, NP **66**, resolved **222**, unresolved **36**, resolution rate **86.05 %** |
| FAST | 15/15; Rule J 953 files / 937 HTML; Rule K BYTE_IDENTICAL |
| reproducible | YES (in-process and independent) |

**Safety recheck (Phase 4):** the publication audit is all zero. The six dual-brand rows and Microtel Inver Grove
Heights are none of PF, NP or seed rows (**0 / 6** and **0**).

## 4. Canonical registration (Phase 5)

This is the ordinary composite fresh-market path, Portland's `09850aa3` recipe replayed.

1. **Repoint.** 15 market-local modules moved from the shadow zone to the registered zone (24 edits). Only path
   constants changed: `identity_census_proposed/` → `identity_census/`, `markets/proposed/` → `markets/`, and staging
   `launch_package/` → the package root. The publication safety audit was split into a pure `audit()` function; its
   report is unchanged (all zero).
2. **Promotion.** The census and market document were moved with `git mv` (R100). The policy package, proposed
   authority and final partition were regenerated at the package root by their own writers. **All five are
   byte-identical to the sealed copies** (policy `77633dc4…` = the package's dependency digest).
3. **Authority shard.** `market_registration_cli --write` produced 156 seed rows and 66 exclusions, plus empty routing
   and affiliate shards. **All four are byte-identical to the sealed shard.**
4. **Globals.** `build_global_authority --write`, then `--check` clean:
   - exclusions 1,667 → **1,733** (+66, all minneapolis-mn);
   - seed rows 3,968 → **4,124** (+156, all minneapolis-mn);
   - **0 removed or modified.**
5. **Release contract.** `deploy/netlify/release_contracts/minneapolis-mn.json`, written by
   `minneapolis_mn_release_contract_002.py`:
   - fully derived through `release_contracts.derive_authority`, 0 disagreements;
   - `verify_all()`: **43 / 43** clean.
6. **`register`** (5.6 s):
   - participation 42 → 43 rows: minneapolis-mn added once at `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH`;
   - 0 rows removed, **0 existing rows changed**; the founder-authorized set is unchanged at 41;
   - `load_participation()` loads and `decision_problems` = [];
   - the build closure gained exactly the release contract and the market document.
7. **`seal --work C:/t/msp3a --work-order`** (400.1 s; detached):
   - package `dd62d308`, reproducible YES;
   - FAST 15/15 in 325.9 s;
   - candidate 42 / 3,975 / 4,377, reproducible YES;
   - pin block: census 258 / PF 156 / NP 66 / corridor routes 14.
8. **Commit** `4c3abd44`, then **`packet`** with no `--classification`.

**`packet` (automatic):** live source `aeb57df1`, deploy `6ac264b7`, base `e494698f` (112.5 s; classification proof 111.7 s).

| | |
|---|---|
| classification_source | **AUTOMATIC** |
| CLASS | **COMPOSITE_FRESH_MARKET_DATA_ONLY** |
| ELIGIBLE | **YES**: 15/15 classifier checks PASS (change_set, market_local_zone, discovery_config, registration_input, identity_resolutions, participation, release_contract, build_closure, derived_globals, sealed_package, fast_receipt, expected_release, identity_routes, market_state_pin, release_integrity) |
| FULL_REGRESSION_REQUIRED | **NO** |
| REMOTE BROAD JOBS / BROAD REGRESSION RUNS | **0 / 0** |
| Change set | 107 paths: 34 market-local, 13 registration data, 60 derived; **0 shared, 0 unknown** |
| packet status | **AUTHORIZATION_READY**, founder AWAITING_FOUNDER_AUTHORIZATION |

**Registered package** `pkg-minneapolis-mn-dd62d3082411d1d5`,
`sha256:dd62d3082411d1d513b276453dd0b648f044f71c60bf0089e5a308176f0770e2`, zone REGISTERED_LIVE:
- Field-for-field identical to `5e356167`: census, PF and NP records, seed rows, partition, official routes, evidence
  references, unresolved rows and founder holds (the staging gate `package_identity` checks every field).
- It builds the **same bundle**, `cdd956142e245072…`.
- The id differs only because the zone, the source sha and the sealed_at differ.

## 5. Timer (Phase 6)

| | |
|---|---|
| REGISTER COMMAND TIME | 5.6 s |
| SEAL TIME | 400.1 s, of which FAST cold builds take 325.9 s and the live-parent read 72.4 s |
| FAST COLD-BUILD TIME | 325.9 s |
| PACKET TIME | 112.5 s (automatic classification proof 111.7 s) |
| GENERIC REGISTRATION-LANE TIME | **518.2 s ≈ 8 m 38 s** |
| TOTAL WALL CLOCK | **22 m 55 s** (20:42:07Z live check → 21:05:02Z packet) |

**≤ 5 minutes: MISSED by 3 m 38 s.** The cause is FAST's cold builds: 325.9 s here against Portland's 149.0 s for a
bundle of similar size (953 vs 908 files). Free memory during this session was low (1.9–2.6 GB on a 16 GB machine),
which is the likeliest reason. Without the cold builds the lane runs in 192.3 s (3 m 12 s).

**≤ 10 minutes:** the lane passes (8 m 38 s). The total wall clock (22 m 55 s) does not; the extra time went to the
repoint, writing the two market-local modules (release contract, staging checks) and one residue correction (§9).
There was no refusal, no supplied classification, no factory repair, and no correction to the checks module's gates
after its first run.

## 6. Participation and parent (Phases 7–8)

**Participation:** minneapolis-mn is `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH`, added once, by reissue. All
41 live rows (plus withheld Detroit) are preserved, and 0 are changed.

**Parent:**
- PARENT LOOKUP PASS: the package parent is `6ac264b7`, current Portland-live.
- PARENT ROUTES PRESERVED PASS: all 4,206 parent release-index routes are carried.

## 7. Staging and projected accounting (Phases 9–10)

| | |
|---|---|
| UNCHANGED BUNDLES REUSED | **41** (every live market's committed index entry is carried by identity) |
| UNCHANGED MARKETS REBUILT | **0** |
| MINNEAPOLIS BUNDLES BUILT | **1** (FAST's own cold builds of the one bundle) |
| PHYSICAL FRAGMENTS RERENDERED | **0** (no whole-site assembly ran; the candidate was composed twice by the seal and agrees) |

**Projected accounting,** derived from candidate sets, not assumed:

| | |
|---|---:|
| MINNEAPOLIS PROJECTED PROFILES | **156** |
| MINNEAPOLIS RELEASE-INDEX ROUTES | **171** (156 hotels + 14 corridors + 1 hub) |
| MINNEAPOLIS SERVED ROUTES | **172** (the 171 plus its policy-comparison page, counted from the built sitemap) |
| CANDIDATE MARKETS | **42** |
| CANDIDATE PROFILES | **3,975** (3,819 + 156) |
| CANDIDATE RELEASE-INDEX ROUTES | **4,377** (4,206 + 171) |
| CANDIDATE SERVED ROUTES | **4,452** (4,280 + 172) |

## 8. Safety (Phases 11–17)

All of the following are recorded in `markets/reports/minneapolis_mn_registration_checks_002.json`
(`minneapolis_mn_registration_checks_002.py`). Every check runs on the site the seal's own FAST build produced
(`C:/t/msp3a/oa/site`), over the registered root documents, which are byte-identical to the sealed ones.

**Held rows (Phase 11), under the founder's ruling:**

| held item | profile | NP record | release-index route | served route |
|---|---|---|---|---|
| Home2 Suites by Hilton Minneapolis Downtown (317 2nd Ave S) | absent | absent | absent | absent |
| Tru by Hilton Minneapolis Downtown (317 2nd Ave S) | absent | absent | absent | absent |
| Home2 Suites by Hilton Minneapolis Mall of America (2415 E Old Shakopee Rd) | absent | absent | absent | absent |
| Tru by Hilton Minneapolis Mall of America (2415 E Old Shakopee Rd) | absent | absent | absent | absent |
| Comfort Inn MSP Airport – Mall of America (1321 E 78th St) | absent | absent | absent | absent |
| MainStay Suites MSP Airport – Mall of America (1321 E 78th St) | absent | absent | absent | absent |
| Microtel Inn & Suites by Wyndham Inver Grove Heights (EVIDENCE_HOLD) | absent | absent | absent | absent |

- All 36 unresolved rows publish nothing; no row of any hold class is published. **UNAPPROVED MINNEAPOLIS PROFILES =
  0**, and APPROVED = 156.
- `identity_resolutions.json` was **not** written. No acquisition ran, and no held row was resolved.
- Microtel stays EVIDENCE_HOLD: neither pet-friendly nor verified no-pets.

**Reader safety (Phase 12):**
- PET-FRIENDLY WITH EXPLICIT REFUSAL **0**; QUESTION-ONLY PET-FRIENDLY **0**; SERVICE-ANIMAL-ONLY ACCEPTANCE **0**;
- no-pets quote without a refusal 0;
- Rule C (shared first-party binding): **222 / 222** eligible.
- The shared reader was not modified.

**Fee safety (Phase 13):**
- **35** single-basis fees publish;
- **47** tiered fees are withheld;
- **16** unsafe single fees are withheld: basis not stated 12, stay-length condition 4;
- every one of the 63 withheld fee quotes was matched to its records (402 matches), and **0 publish a single fee**;
- **Hyatt Regency Bloomington:** its record publishes no pet_fee, and its quote is withheld as STAY_LENGTH_CONDITION;
- **MISLEADING SINGLE FEES 0**.

**Identity / geography (Phase 14),** measured over all 32 other Minneapolis modules:
- PORTLAND COORDINATE RESIDUE **0**. The Twin Cities envelope (44.73–45.14 N, 93.60–92.89 W) is the census's rule.
- OREGON TOWN-LIST RESIDUE IN CODE **0**.
- PORTLAND FINDINGS LABELLED AS MINNEAPOLIS **0**.
- Rows admitted outside Minnesota: 0.
- The fixed identities are correct:
  - Hotel Alma: 55414, SOURCE_SILENT, unpublished.
  - Celeste of St. Paul: 55101, published verified no-pets.
  - Northernaire Motel: 55109, SOURCE_SILENT, unpublished.
  - Ramada Plymouth: 55441, published pet-friendly.

**Cross-market (Phase 15):**
- CROSS-MARKET COLLISIONS 0, BARE-CHAIN COLLISIONS 0 (0 bare-chain names), DUPLICATE EXCLUDED IDENTITIES 0.
- 0 live properties moved or displaced.
- 3 non-admitted census rows share a published name and are second sightings of the published building (listed, not
  resolved).

**Delta (Phase 16):**
- UNEXPECTED MARKET, PROFILE and ROUTE DELTA: `[]`.
- Prior markets, profiles, release-index routes and served routes lost: 0.
- Minneapolis is the only new market. `release_index.compare`: 0 findings.

**FAST receipt (Phase 17):**
- `pkg-minneapolis-mn-dd62d3082411d1d5-eac0c8724c679c00.json` is **CURRENTLY ELIGIBLE**, the only receipt canonical
  selection returns.
- J PASS, NONEMPTY: 953 files / 937 HTML, bundle `cdd95614…` (not `e3b0c442`).
- K PASS: BYTE_IDENTICAL, 0 defects.

**Staging gates (Phase 18): 26 / 26 PASS** on the first run.

| gates | |
|---|---|
| package and lane | package identity, registration lane eligible, FAST receipt eligibility, FAST A–O |
| parent and preservation | parent lookup, parent routes, markets, profiles, routes, candidate delta |
| decision and safety | participation, founder-row reconciliation (6 dual-brand / 0 shared-reader / 0 preopening), held cohort, founder ruling: dual-brand held, founder ruling: Microtel held, Twin Cities identity / geography, Hyatt Regency Bloomington fee withheld, preopening, timeshare, military, reader, fee, collision |
| contracts and binding | first-party binding, release contracts |
| **deployment refusal** | **EXPECTED / PASS**: 0 deployment authorizations and 0 records name minneapolis-mn; not founder-authorized |

## 9. One residue correction, made in this order

The Phase 14 scan found **one** Portland sentence that the source-ready order's sweep had missed. It was report text,
not logic: the competitor lane's `method_note` said BringFido's radius widening "is expected to reach Camas, Newberg,
Sandy, Canby and the Gorge".
- The module (`minneapolis_mn_competitor_challenge_001.py`) and the same field of its committed report now name
  Stillwater, Hastings, Lakeville, Anoka and the St. Croix valley.
- The change is text only: no lead, count or classification moves.
- The lane was not re-run: that would spend Firecrawl credits.
- That report is not a sealed-package dependency (the package hashes census, exclusions, market, partition, policy,
  routing and seed only).

Two hits of the first scan draft were false positives and are excluded by the final pattern: a 50-state name table
naming the state of Oregon, and "Waldorf Astoria".

**Noted, not changed:** the two held Comfort Inn / MainStay rows carry city "Building A" / "Building B". The page
address "1321 E 78th St Bldg A, Bloomington" was split at the building designator. Both rows are held and publish
nothing; a later correction order can fix the parse.

## 10. Live safety (Phase 19)

Re-verified after staging, at 21:05Z (`markets/reports/minneapolis_mn_registration_live_probe_002.json`):
- Live is still `6ac264b7`: 41 / 3,819 / 4,280, host verified.
- **Minneapolis hub 404, and all 172 projected Minneapolis routes 404.**
- Portland, Seattle, San Antonio, Austin, Phoenix, Denver, San Diego, Jacksonville FL, West Palm Beach, Fort
  Lauderdale and Augusta return **200**; Detroit **404**.

CURRENT LIVE MODIFIED = NO. No deploy, no deployment authorization, no founder authorization.

## 11. What the founder is now being asked to decide

Founder launch authorization of **`pkg-minneapolis-mn-dd62d3082411d1d5`** only, bound to BUILD commit **`4c3abd44`**.

**Expected effect:** +1 market / +156 profiles / +171 release-index routes / +172 served routes, giving
**42 / 3,975 / 4,377 / 4,452**.

**Held and not part of the decision:**
- the six dual-brand rows at 317 2nd Ave S, 2415 E Old Shakopee Rd and 1321 E 78th St;
- Microtel Inver Grove Heights;
- the 29 other unresolved rows.

The seal's scratch directory `C:/t/msp3a` was removed after the checks report and the live probe were written. No
temporary process remains.

## FINAL ANSWERS

1. CURRENT LIVE DEPLOYMENT = 6ac264b79e70ce6a7db4baaf (Portland; lineage aeb57df1, built_from 22ff1c94)
2. CURRENT LIVE MARKETS = 41
3. CURRENT LIVE PROFILES = 3819
4. CURRENT LIVE RELEASE-INDEX ROUTES = 4206
5. CURRENT LIVE SERVED ROUTES = 4280
6. MINNEAPOLIS SOURCE PACKAGE = pkg-minneapolis-mn-5e356167a116c464 (sha256:5e356167a116c464a4d9e78dbc5907a5b7299ed4f5a5e23dbf87301d7f5cef34)
7. REGISTERED MINNEAPOLIS PACKAGE = pkg-minneapolis-mn-dd62d3082411d1d5 (content identical to 5e356167; same bundle cdd95614…)
8. PACKAGE DIGEST = sha256:dd62d3082411d1d513b276453dd0b648f044f71c60bf0089e5a308176f0770e2
9. SOURCE-READY COMMIT = 1a8a8e9d (source-ready HEAD; the source package was sealed from 4b019137)
10. AUTOMATIC BASE DERIVES = YES
11. DERIVED BASE = e494698f7ee846f9a6e314111828b6c3ae9cfa80
12. REGISTRATION CLASS = COMPOSITE_FRESH_MARKET_DATA_ONLY
13. AUTOMATIC CLASSIFICATION = YES (classification_source AUTOMATIC)
14. CLASSIFIER CHECKS = 15/15 PASS
15. ELIGIBLE = YES
16. FULL_REGRESSION_REQUIRED = NO
17. REGISTER COMMAND TIME = 5.6 s
18. SEAL TIME = 400.1 s (FAST cold builds 325.9 s; live-parent read 72.4 s)
19. FAST COLD-BUILD TIME = 325.9 s
20. PACKET TIME = 112.5 s (automatic classification proof 111.7 s)
21. GENERIC REGISTRATION-LANE TIME = 518.2 s (8 m 38 s)
22. <=5M TARGET = MISSED by 3 m 38 s (FAST cold builds 325.9 s; without them 3 m 12 s)
23. <=10M HARD LIMIT = lane PASS (8 m 38 s); total wall clock 22 m 55 s exceeds it (repoint + module writing + one text correction, no refusal)
24. BROAD REGRESSION RUNS = 0
25. SHARED PATHS = 0
26. UNKNOWN PATHS = 0
27. PARENT LOOKUP = PASS
28. PARENT ROUTES PRESERVED = PASS
29. UNCHANGED BUNDLES REUSED = 41
30. UNCHANGED MARKETS REBUILT = 0
31. PHYSICAL FRAGMENTS RERENDERED = 0
32. MINNEAPOLIS BUNDLES BUILT = 1
33. MINNEAPOLIS PROJECTED PROFILES = 156
34. MINNEAPOLIS RELEASE-INDEX ROUTES = 171
35. MINNEAPOLIS SERVED ROUTES = 172
36. CANDIDATE MARKETS = 42
37. CANDIDATE PROFILES = 3975
38. CANDIDATE RELEASE-INDEX ROUTES = 4377
39. CANDIDATE SERVED ROUTES = 4452
40. APPROVED MINNEAPOLIS PROFILES = 156
41. UNAPPROVED MINNEAPOLIS PROFILES = 0
42. DUAL-BRAND HOLDS PUBLISHED = 0 / 6
43. MICROTEL INVER GROVE HEIGHTS PUBLISHED = 0
44. PET-FRIENDLY WITH EXPLICIT REFUSAL = 0
45. QUESTION-ONLY PET-FRIENDLY = 0
46. SERVICE-ANIMAL-ONLY ACCEPTANCE = 0
47. MISLEADING SINGLE FEES = 0
48. PORTLAND COORDINATE RESIDUE = 0
49. OREGON TEXT RESIDUE = 0 (one report sentence corrected in this order, text only; see §9)
50. CROSS-MARKET COLLISIONS = 0 (bare-chain 0, duplicate excluded identities 0)
51. FAST RECEIPT CURRENTLY ELIGIBLE = YES (pkg-minneapolis-mn-dd62d3082411d1d5-eac0c8724c679c00.json)
52. RULE J NONEMPTY = PASS (953 files / 937 HTML, bundle cdd95614…)
53. RULE K NONVACUOUS = PASS (BYTE_IDENTICAL)
54. ALL STAGING GATES = PASS (26/26)
55. DEPLOYMENT REFUSAL = EXPECTED / PASS
56. CURRENT LIVE MODIFIED = NO
57. DEPLOYMENT PERFORMED = NO
58. MINNEAPOLIS LIVE = NO (hub + 172 routes 404)
59. origin == HEAD = YES (verified after push)
60. tree clean = YES (verified after push)
61. READY FOR FOUNDER LAUNCH AUTHORIZATION = YES (packet AUTHORIZATION_READY; authorize pkg-minneapolis-mn-dd62d3082411d1d5 only, bound to 4c3abd44)

```
MINNEAPOLIS REGISTRATION = PASS
MINNEAPOLIS STAGING = PASS
AUTOMATIC BASE DERIVES = YES
FULL_REGRESSION_REQUIRED = NO
BROAD REGRESSION RUNS = 0
PET-FRIENDLY RECORDS WITH EXPLICIT REFUSAL = 0
QUESTION-ONLY PET-FRIENDLY RECORDS = 0
SERVICE-ANIMAL-ONLY ACCEPTANCE = 0
UNAPPROVED MINNEAPOLIS PROFILES = 0
MISLEADING SINGLE FEES = 0
UNCHANGED MARKETS REBUILT = 0
CURRENT LIVE MODIFIED = NO
MINNEAPOLIS DEPLOYED = NO
READY FOR FOUNDER LAUNCH AUTHORIZATION = YES
```

STOP.
