# PTF-NEW-ORLEANS-LA-REGISTRATION-AND-STAGING-002 — FINAL

**Status:** New Orleans / Greater New Orleans, Louisiana is **REGISTERED and STAGED**. The readiness packet is
**AUTHORIZATION_READY**; founder status AWAITING_FOUNDER_AUTHORIZATION.

**Not done:** nothing was deployed; there is no founder launch authorization and no deployment authorization; current
live is unchanged.

**Branch:** `worker/ptf-new-orleans-la-market-001` (worktree `C:\Atlas-New-Orleans-LA-Hardened-V1`).

**Commits:**
- `85e7c13e` — the registration transaction. This is the **BUILD commit** a founder authorization must bind.
- the final commit — the automatic classification, the readiness packet, the live probe and this report.

## 1. Current live (Phase 1)

`release_index live-source --fetch --verify-host` at 20:47:45Z and again after staging at 21:17:23Z — unchanged both times:

| | |
|---|---|
| CURRENT LIVE SOURCE COMMIT | `117afe1105f920a8fcebd5bc1f4c4e2be9bb3ed3` (built_from `c6609370`) |
| CURRENT LIVE DEPLOYMENT | **`6ac4dc8a39b0e7274828a32b`** (record `ptf-deploy-kansas-city-004-…`) |
| CURRENT LIVE BUNDLE | `6a35c23829f9c0a0a1713acc721f3fcf317a94d7f57120379ffc951fdc60ed5f` |
| CURRENT LIVE SITEMAP | `3d5d9425a4e0a90b6aca13f3d02866a815ebc934df8382e4fcf03c0ecc10967b` |
| CURRENT LIVE MARKETS | **43** (Detroit withheld) |
| CURRENT LIVE PROFILES | **4,136** |
| CURRENT LIVE RELEASE-INDEX ROUTES | **4,552** (counted from the live index) |
| CURRENT LIVE SERVED ROUTES | **4,628** |
| HOST VERIFIED | YES |

## 2. Automatic base (Phase 2)

`derive_registration_base('new-orleans-la', 117afe11…)` → **`e42ae36452c59030db86636f31958fc4f44d2d9b`** with no manual
input (the newest first-parent ancestor naming no New Orleans path and carrying the live-truth files; current live
lineage commit `117afe11`). `packet` re-derived the same base on its own. No base or classification was supplied.

## 3. Source package (Phases 3–5)

| | |
|---|---|
| SOURCE PACKAGE | `pkg-new-orleans-la-939f3cda64d39402`, `sha256:939f3cda64d394023919387400281d378b49e68ca747ccb7a0bbe4af5abd0126`, sealed from `b31cd583` |
| SOURCE RECEIPT | `…-236fd45013205813`, currently eligible; FAST 15/15; J 644 files / 628 HTML; K BYTE_IDENTICAL; reproduced byte-identical |
| census | 347 — PF 104, NP 64, resolved 168, unresolved 179, actionable 0 |
| parishes | Orleans **282**, Jefferson **62**, St. Bernard 2, Plaquemines 1; wrong-city identities **0** |
| earlier seal | `pkg-new-orleans-la-8585917af96bd963` was superseded by the final browser-policy pass: **EARLIER PACKAGE SELECTED = NO** (the gate `superseded_package_not_selected` PASS); its history is kept in git |

Held cohort (founder ruling) — every row checked by name on the built site: no profile, no NP record, no release-index
route, no served route:

| held | census state | published |
|---|---|---|
| SpringHill Suites + TownePlace Suites New Orleans Downtown / Canal Street (1600 Canal St) | ADMITTED, IDENTITY_MISMATCH_HOLD | 0 / 2 |
| The Garden District Hotel (refusal the shared reader does not interpret) | ADMITTED, EVIDENCE_HOLD | 0 (neither PF nor NP) |
| Maison DuBois Bed and Breakfast (browser permission declined) | ADMITTED, IDENTITY_MISMATCH_HOLD | 0 |
| Maison Dupuy Hotel (browser permission declined) | ADMITTED, IDENTITY_MISMATCH_HOLD | 0 |
| Fairmont New Orleans (preopening) / Claiborne Mansion (closed) | ADMITTED, EVIDENCE_HOLD | 0 / 0 |
| 7 vacation-ownership identities (Bluegreen ×2, Club Wyndham ×2, Holiday Inn Club Vacations ×2, WorldMark) | NOT ADMITTED, NON_LODGING | 0 |
| The Syd, Castle Day, Compass Point Events (group-villa / venue rentals) | NOT ADMITTED, NON_LODGING | 0 |

All 179 unresolved rows publish nothing. `identity_resolutions.json` was **not** written; the shared reader was not
touched; Maison DuBois and Maison Dupuy were not retried; no acquisition ran.

## 4. Canonical registration (Phase 7)

Kansas City's `d054d6c0` recipe, replayed:

1. **Repoint** — 15 market-local modules, 23 edits, path constants only (`identity_census_proposed/` → `identity_census/`,
   `markets/proposed/` → `markets/`, staging `launch_package/` → the package root); the publication-safety audit split
   into a pure `audit()` (report unchanged, all zero).
2. **Promotion** — census and market document moved with `git mv`; policy package, proposed authority and final
   partition regenerated at the package root by their own writers. **All five byte-identical to the sealed copies.**
3. **Shard** — `market_registration_cli --write`: 104 seed rows, 64 exclusions, empty routing and affiliate shards.
   **All four byte-identical to the sealed shard.**
4. **Globals** — `build_global_authority --write`, then `--check` clean: seed rows +104, exclusions 1,793 → **1,857**
   (+64, all new-orleans-la); **0 removed or modified**. (`build_market_authorities --write` was not run.)
5. **Release contract** — `new_orleans_la_release_contract_002.py`, fully derived through
   `release_contracts.derive_authority`, 0 disagreements; `verify_all()` **45 / 45** clean.
6. **`register`** (5.4 s) — participation 44 → 45 rows, new-orleans-la added once at
   `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH`; 0 rows removed, **0 changed**; founder-authorized set unchanged at
   43 (all live rows preserved; Detroit still withheld); `load_participation()` loads, `decision_problems = []`; build
   closure gained exactly the release contract and the market document.
7. **`seal --work C:/t/nola3 --work-order`** (200.8 s, detached) — package `pkg-new-orleans-la-0e5fef6af3af8339`,
   reproducible YES; FAST 15/15 in 112.9 s; candidate 44 / 4,240 / 4,663, reproducible YES; pin block census 347 /
   PF 104 / NP 64 / corridor routes 6.
8. **Commit** `85e7c13e`, then **`packet`** with no `--classification` (125.6 s).

| | |
|---|---|
| classification_source | **AUTOMATIC** |
| CLASS | **COMPOSITE_FRESH_MARKET_DATA_ONLY** |
| ELIGIBLE | **YES** — 15/15 checks PASS (change_set, market_local_zone, discovery_config, registration_input, identity_resolutions, participation, release_contract, build_closure, derived_globals, sealed_package, fast_receipt, expected_release, identity_routes, market_state_pin, release_integrity) |
| FULL_REGRESSION_REQUIRED | **NO** |
| REMOTE BROAD JOBS / BROAD REGRESSION RUNS | **0 / 0** |
| Change set | 108 paths: 34 market-local, 13 registration data, 61 derived; **0 shared, 0 unknown** |

**Registered package** `pkg-new-orleans-la-0e5fef6af3af8339`
(`sha256:0e5fef6af3af83397a0fae3a1bc00e75cf30575100d9100ce4d7e19c2905ff0f`), zone REGISTERED_LIVE: field-for-field
identical to `939f3cda` (census, PF/NP records, seed rows, partition, official routes, evidence, unresolved rows,
founder holds — the `package_identity` gate) and it builds the **same bundle** `047825df…`. The id differs only by zone,
source sha and sealed_at.

## 5. Timer (Phase 8)

| | |
|---|---|
| REGISTER COMMAND TIME | 5.4 s |
| SEAL TIME | 200.8 s (live-parent read 85.5 s, FAST 112.9 s) |
| FAST COLD-BUILD TIME | 112.9 s |
| PACKET TIME | 125.6 s (classification proof 124.9 s) |
| GENERIC REGISTRATION-LANE TIME | **331.8 s ≈ 5 m 32 s** |
| TOTAL WALL CLOCK | **≈ 27 m 35 s** (20:47:45Z live check → ≈ 21:15:20Z packet); 29 m 38 s to the post-staging live re-check |

**≤ 5 minutes: MISSED** by 32 s — the excess is FAST's cold builds (112.9 s); without them the lane runs in 218.9 s
(3 m 39 s). **≤ 10 minutes: PASS**. The rest of the wall clock went to the repoint, the two market-local modules (release
contract, staging gates) and one gate correction (§9).

## 6. Participation and parent (Phases 9–10)

- new-orleans-la `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH`, added once by reissue; all 43 live rows (and
  withheld Detroit) preserved, 0 changed.
- PARENT LOOKUP **PASS** (package parent 6ac4dc8a, current Kansas City-live); PARENT ROUTES PRESERVED **PASS** (all
  4,552 parent index routes carried).

## 7. Staging and projected accounting (Phases 11–12)

| | |
|---|---|
| UNCHANGED BUNDLES REUSED | **43** |
| UNCHANGED MARKETS REBUILT | **0** |
| NEW ORLEANS BUNDLES BUILT | **1** (FAST's own cold builds of the one bundle) |
| PHYSICAL FRAGMENTS RERENDERED | **0** (no whole-site assembly; the candidate was composed twice by the seal and agrees) |

| | |
|---|---:|
| NEW ORLEANS PROJECTED PROFILES | **104** |
| NEW ORLEANS RELEASE-INDEX ROUTES | **111** (104 hotels + 6 corridors + 1 hub) |
| NEW ORLEANS SERVED ROUTES | **112** (the 111 plus its policy-comparison page, from the built sitemap) |
| CANDIDATE MARKETS | **44** |
| CANDIDATE PROFILES | **4,240** (4,136 + 104) |
| CANDIDATE RELEASE-INDEX ROUTES | **4,663** (4,552 + 111) |
| CANDIDATE SERVED ROUTES | **4,740** (4,628 + 112) |

## 8. Safety (Phases 13–20)

`markets/reports/new_orleans_la_registration_checks_002.json` (`new_orleans_la_registration_checks_002.py`), run on the
site the seal's FAST build produced (`C:/t/nola3/oa/site`) over the registered root documents.

- **Reader:** PF with explicit refusal 0; question-only PF 0; service-animal-only 0; NP quote without refusal 0;
  Rule C (shared first-party binding) 168 / 168 eligible. Shared reader not modified.
- **Fees:** 29 single-basis publish; 22 tiered withheld; 10 unsafe withheld (8 basis not stated, 2 stay-length); 0
  withheld fees flattened (89 record matches); **Crowne Plaza Astor** publishes no fee, and its record carries the
  corrected quote "…nightly fee of 35 USD with a maximum fee of 70 USD"; MISLEADING SINGLE FEES 0.
- **Municipalities:** Orleans 282 / Jefferson 62 / St. Bernard 2 / Plaquemines 1; wrong-city 0; every row's city is a
  municipality its own postal code carries; 0 non-Louisiana rows; 0 seed rows with a rewritten city, ZIP or state;
  fixed traps correct (Residence Inn Elmwood 70123 Elmwood, Brent House 70121 Jefferson, Clarion Airport 70001
  Metairie, Hilton New Orleans Airport 70062 Kenner, Holiday Inn West Bank Tower 70053 Gretna, Red Roof Westbank 70058
  Harvey); pin envelope is New Orleans' (29.80–30.10 N, 90.32–89.70 W).
- **Market text:** Kansas City / Missouri residue **0**, Minneapolis residue **0**, Portland residue **0** across the 11
  registered documents (the "Kansas City-live lineage" statement is the lineage, allowed by name); market label "New
  Orleans / Greater New Orleans, Louisiana" correct; boundary audit names Baton Rouge, the Northshore, Houma–Thibodaux,
  the river parishes and the Mississippi Gulf Coast (0 admitted from each).
- **Non-hotel:** The Syd, Castle Day and Compass Point Events stay NON_LODGING; private / venue rental rows published 0.
- **Cross-market:** collisions 0; bare-chain names 0; duplicate excluded identities 0; live properties moved 0.
- **Delta:** unexpected market / profile / route delta `[]`; prior markets, profiles, index routes and served routes
  lost 0; New Orleans the only new market; `release_index.compare` 0 findings.
- **FAST receipt:** `pkg-new-orleans-la-0e5fef6af3af8339-ea4d8ec3d090dfc1` CURRENTLY ELIGIBLE (the only receipt
  selected); J PASS, 644 files / 628 HTML, bundle `047825df…` (not `e3b0c442`); K BYTE_IDENTICAL; 0 defects.
- **Staging gates: 32 / 32 PASS.** Deployment refusal **EXPECTED / PASS**: 0 authorizations and 0 deployment records
  name new-orleans-la; not founder-authorized.

## 9. One correction made in this order

The first run of the gate module flagged one "held row publishing": the map-only row "Wyndham Garden New Orleans
Airport" at 6401 Veterans Memorial Blvd, Metairie 70003 (OSM way 712428067: no brand tag, no website), held for review.
The published profile of that name is a different building — Wyndham's own property service binds code 46094 to
4535 Williams Blvd, Kenner 70065 — so the held map row publishes nothing. The gate now records a map-only name twin of
a building bound by the brand's own property code and its own first-party page under
`map_label_name_twins_of_brand_bound_buildings`; any other name twin still fails. No data changed. (The same edit
pass fixed a mis-named report key, `KANSAS_CITY_TEXT_RESIDUE`.)

## 10. Live safety (Phase 21)

After staging: live deploy unchanged (6ac4dc8a, 43 / 4,136 / 4,628, host verified). New Orleans hub and all **112**
projected routes **404**. Kansas City, Minneapolis, Portland, Seattle, San Antonio, Austin, Phoenix, Denver, San Diego,
Jacksonville FL, West Palm Beach, Fort Lauderdale, Augusta **200**; Detroit **404**
(`new_orleans_la_registration_live_probe_002.json`).

## 11. Isolation

No shared reader or factory implementation changed; no broad regression; no acquisition, spend, founder
authorization, deployment authorization or deployment. Shared documents touched are exactly the registration-owned
six: `launch_participation.json` (reissued), `bundle_cache_closure.json` (+2), the three generated globals and the
market-state pin. The seal's work directory `C:/t/nola3` is kept (it holds the built candidate site the gates read).

## FINAL ANSWERS

1. CURRENT LIVE DEPLOYMENT = 6ac4dc8a39b0e7274828a32b
2. CURRENT LIVE MARKETS = 43
3. CURRENT LIVE PROFILES = 4,136
4. CURRENT LIVE RELEASE-INDEX ROUTES = 4,552
5. CURRENT LIVE SERVED ROUTES = 4,628
6. NEW ORLEANS SOURCE PACKAGE = pkg-new-orleans-la-939f3cda64d39402
7. REGISTERED NEW ORLEANS PACKAGE = pkg-new-orleans-la-0e5fef6af3af8339
8. PACKAGE DIGEST = sha256:0e5fef6af3af83397a0fae3a1bc00e75cf30575100d9100ce4d7e19c2905ff0f (source: sha256:939f3cda64d394023919387400281d378b49e68ca747ccb7a0bbe4af5abd0126)
9. SOURCE-READY COMMIT = b31cd583
10. AUTOMATIC BASE DERIVES = YES
11. DERIVED BASE = e42ae36452c59030db86636f31958fc4f44d2d9b
12. REGISTRATION CLASS = COMPOSITE_FRESH_MARKET_DATA_ONLY
13. AUTOMATIC CLASSIFICATION = YES
14. CLASSIFIER CHECKS = 15/15 PASS
15. ELIGIBLE = YES
16. FULL_REGRESSION_REQUIRED = NO
17. REGISTER COMMAND TIME = 5.4 s
18. SEAL TIME = 200.8 s
19. FAST COLD-BUILD TIME = 112.9 s
20. PACKET TIME = 125.6 s
21. GENERIC REGISTRATION-LANE TIME = 331.8 s (5 m 32 s)
22. <=5M TARGET = MISSED by 32 s (FAST cold builds 112.9 s; 218.9 s without them)
23. <=10M HARD LIMIT = PASS
24. BROAD REGRESSION RUNS = 0
25. SHARED PATHS = 0
26. UNKNOWN PATHS = 0
27. PARENT LOOKUP = PASS
28. PARENT ROUTES PRESERVED = PASS
29. UNCHANGED BUNDLES REUSED = 43
30. UNCHANGED MARKETS REBUILT = 0
31. PHYSICAL FRAGMENTS RERENDERED = 0
32. NEW ORLEANS BUNDLES BUILT = 1
33. NEW ORLEANS PROJECTED PROFILES = 104
34. NEW ORLEANS RELEASE-INDEX ROUTES = 111
35. NEW ORLEANS SERVED ROUTES = 112
36. CANDIDATE MARKETS = 44
37. CANDIDATE PROFILES = 4,240
38. CANDIDATE RELEASE-INDEX ROUTES = 4,663
39. CANDIDATE SERVED ROUTES = 4,740
40. APPROVED NEW ORLEANS PROFILES = 104
41. UNAPPROVED NEW ORLEANS PROFILES = 0
42. DUAL-BRAND HOLDS PUBLISHED = 0
43. GARDEN DISTRICT HOTEL PUBLISHED = 0
44. MAISON DU BOIS PUBLISHED = 0
45. MAISON DUPUY PUBLISHED = 0
46. PRIVATE / VENUE RENTAL ROWS PUBLISHED = 0
47. NEW ORLEANS WRONG-CITY IDENTITIES = 0
48. PET-FRIENDLY WITH EXPLICIT REFUSAL = 0
49. QUESTION-ONLY PET-FRIENDLY = 0
50. SERVICE-ANIMAL-ONLY ACCEPTANCE = 0
51. MISLEADING SINGLE FEES = 0
52. CLONE TEXT RESIDUE = 0 (Kansas City 0, Minneapolis 0, Portland 0)
53. CROSS-MARKET COLLISIONS = 0
54. FAST RECEIPT CURRENTLY ELIGIBLE = YES
55. RULE J NONEMPTY = PASS (644 files / 628 HTML)
56. RULE K NONVACUOUS = PASS (BYTE_IDENTICAL)
57. ALL STAGING GATES = PASS (32/32)
58. DEPLOYMENT REFUSAL = EXPECTED / PASS
59. CURRENT LIVE MODIFIED = NO
60. DEPLOYMENT PERFORMED = NO
61. NEW ORLEANS LIVE = NO
62. origin == HEAD = YES (verified after push)
63. tree clean = YES (verified after push)
64. READY FOR FOUNDER LAUNCH AUTHORIZATION = YES

NEW ORLEANS REGISTRATION = PASS
NEW ORLEANS STAGING = PASS
AUTOMATIC BASE DERIVES = YES
FULL_REGRESSION_REQUIRED = NO
BROAD REGRESSION RUNS = 0
NEW ORLEANS WRONG-CITY IDENTITIES = 0
PET-FRIENDLY RECORDS WITH EXPLICIT REFUSAL = 0
QUESTION-ONLY PET-FRIENDLY RECORDS = 0
SERVICE-ANIMAL-ONLY ACCEPTANCE = 0
UNAPPROVED NEW ORLEANS PROFILES = 0
MISLEADING SINGLE FEES = 0
UNCHANGED MARKETS REBUILT = 0
CURRENT LIVE MODIFIED = NO
NEW ORLEANS DEPLOYED = NO
READY FOR FOUNDER LAUNCH AUTHORIZATION = YES

STOP.

## Next

Founder launch authorization of `pkg-new-orleans-la-0e5fef6af3af8339`, binding BUILD commit `85e7c13e`. If authorized:
+1 market / +104 profiles / +111 index / +112 served → 44 / 4,240 / 4,663 / 4,740.
