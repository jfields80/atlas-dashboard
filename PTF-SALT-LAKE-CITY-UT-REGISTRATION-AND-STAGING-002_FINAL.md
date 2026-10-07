# PTF-SALT-LAKE-CITY-UT-REGISTRATION-AND-STAGING-002 — FINAL

**Status:** Salt Lake City / Park City / Wasatch Front, Utah is **REGISTERED and STAGED**. The readiness packet is
**AUTHORIZATION_READY**; founder status AWAITING_FOUNDER_AUTHORIZATION.

**Not done:** nothing was deployed; there is no founder launch authorization and no deployment authorization; current
live is unchanged.

**Branch:** `worker/ptf-salt-lake-city-ut-market-001` (worktree `C:\Atlas-Salt-Lake-City-UT-Hardened-V1`).
At the start: CURRENT HEAD = origin/worker/ptf-salt-lake-city-ut-market-001 = `efe88e22ab8bdae3d5e98d46d26fe11864325434`, tree clean.

**Commits:**
- `2822639c` — the registration transaction. This is the **BUILD commit** a founder authorization must bind.
- the final commit — the automatic classification, the readiness packet, the live probe and this report.

## 1. Current live (Phase 1)

`release_index live-source --fetch --verify-host` at 17:38Z and again after staging at 18:08:20Z — unchanged both times:

| | |
|---|---|
| CURRENT LIVE SOURCE COMMIT | `90624cd8392d6283e38834ddafa314423eba0ea8` (built_from `4c7e7b90`) |
| CURRENT LIVE DEPLOYMENT | **`6ac5ba3bcda3a604f7e467e0`** (record `ptf-deploy-new-orleans-004-…`) |
| CURRENT LIVE BUNDLE | `af70e0aa8a64496e53c67750668c33029cbda3cf318d9d3ecb1198af346a0a41` |
| CURRENT LIVE SITEMAP | `beb98d7a9f4687c337dfcbd5eaa1d301ac7d74eecddba5dcebf7d7b05c2a8508` |
| CURRENT LIVE MARKETS | **44** (Detroit withheld) |
| CURRENT LIVE PROFILES | **4,240** |
| CURRENT LIVE RELEASE-INDEX ROUTES | **4,663** (counted from the live index) |
| CURRENT LIVE SERVED ROUTES | **4,740** |
| HOST VERIFIED | YES |

## 2. Automatic base (Phase 2)

`derive_registration_base('salt-lake-city-ut', 90624cd8…)` → **`a67c8e75f47b81942436e0d12956e3ec52510446`** with no manual
input (newest first-parent ancestor naming no Salt Lake City path and carrying the live-truth files). `packet` re-derived
the same base on its own. No base or classification was supplied. (A first exploratory call passed the live record's
`built_from` commit instead of the lineage commit and was refused; the lineage commit the resolver names derives
cleanly.)

## 3. Source package (Phases 3–5)

| | |
|---|---|
| SOURCE PACKAGE | `pkg-salt-lake-city-ut-f084558e8d8acabe`, `sha256:f084558e8d8acabeb116c094b6cc4863e226586fd0f05844061f40a0eb05e2e1`, sealed from `bb0ac0d4` |
| SOURCE RECEIPT | `…-9c910e4766ec8d27`, currently eligible; FAST 15/15; J 819 files / 803 HTML; K BYTE_IDENTICAL; reproduced byte-identical |
| census | 209 — PF 133, NP 29, resolved 162, unresolved 47, actionable 0 |
| counties | Salt Lake **159**, Summit **32** (all Park City), Utah **13** (Lehi), Davis **5** |
| superseded seal | `pkg-salt-lake-city-ut-cb60864b9dedafe1`: **SUPERSEDED PACKAGE SELECTED = NO** (gate `superseded_package_not_selected` PASS) |

Held cohort (founder ruling) — every row checked by name on the built site: no profile, no NP record, no release-index
route, no served route:

| held | census state | published |
|---|---|---|
| Hyatt Place Salt Lake City/Cottonwood ("No pets are allowed in 4th-floor rooms" beside a welcome) | ADMITTED, EVIDENCE_HOLD | 0 (neither PF nor NP) |
| Hyatt Place Salt Lake City/Lehi (own page ZIP 84048 vs 84043) | ADMITTED, ACCESS_BLOCKED (read, unbound) | 0 |
| Grand Summit / Silverado / Sundial at Canyons Village (Vail server errors) | ADMITTED, ACCESS_BLOCKED | 0 / 0 / 0 |
| The Ascent Park City, Tapestry (preopening) | ADMITTED, EVIDENCE_HOLD | 0 |
| all 47 unresolved rows | ADMITTED, held | 0 |
| 19 vacation-ownership identities (Westgate, Marriott's MountainSide / Summit Watch, Club Wyndham, HGV Sunrise Lodge, WorldMark) | NOT ADMITTED, NON_LODGING | 0 |
| 172 condo / residence / rental / unproven-lodging rows (Deer Valley's Stag / Grand / Trail's End residences, The Lowell, Park City Vacations, Park City condo lodges, apartments) | NOT ADMITTED | 0 |

`identity_resolutions.json` was **not** written; the shared reader was not touched; the Vail pages were not retried; no
acquisition ran.

## 4. Canonical registration (Phase 6)

New Orleans' `85e7c13e` recipe, replayed:

1. **Repoint** — 15 market-local modules, 25 edits, path constants only (`identity_census_proposed/` → `identity_census/`,
   `markets/proposed/` → `markets/`, staging `launch_package/` → the package root); the publication-safety audit split
   into a pure `audit()` (report unchanged byte-for-byte, all zero).
2. **Promotion** — census and market document moved with `git mv`; policy package, proposed authority and final
   partition regenerated at the package root by their own writers. **All five byte-identical to the sealed copies.**
3. **Shard** — `market_registration_cli --write`: 133 seed rows, 29 exclusions, empty routing and affiliate shards.
   **All four byte-identical to the sealed shard.**
4. **Globals** — `build_global_authority --write`, then `--check` clean: seed rows +133, exclusions 1,857 → **1,886**
   (+29, all salt-lake-city-ut); **0 removed or modified**. (`build_market_authorities --write` was not run.)
5. **Release contract** — `salt_lake_city_ut_release_contract_002.py`, fully derived through
   `release_contracts.derive_authority`, 0 disagreements; `verify_all()` **46 / 46** clean.
6. **`register`** (≈5 s) — participation 45 → 46 rows, salt-lake-city-ut added once at
   `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH`; 0 rows removed, **0 changed**; founder-authorized set unchanged at
   44 (all live rows preserved; Detroit still withheld); `load_participation()` loads, `decision_problems = []`; build
   closure gained exactly the release contract and the market document.
7. **`seal --work C:/t/slc3 --work-order`** (216.0 s, detached, alone) — package `pkg-salt-lake-city-ut-6d474d2906ae01e0`,
   reproducible YES; FAST 15/15 in 134.6 s; candidate 45 / 4,373 / 4,807, reproducible YES; pin block census 209 /
   PF 133 / NP 29 / corridor routes 10.
8. **Commit** `2822639c`, then **`packet`** with no `--classification` (154.9 s).

| | |
|---|---|
| classification_source | **AUTOMATIC** |
| CLASS | **COMPOSITE_FRESH_MARKET_DATA_ONLY** |
| ELIGIBLE | **YES** — 15/15 checks PASS (change_set, market_local_zone, discovery_config, registration_input, identity_resolutions, participation, release_contract, build_closure, derived_globals, sealed_package, fast_receipt, expected_release, identity_routes, market_state_pin, release_integrity) |
| FULL_REGRESSION_REQUIRED | **NO** |
| REMOTE BROAD JOBS / BROAD REGRESSION RUNS | **0 / 0** |
| Change set | 107 paths: 32 market-local, 13 registration data, 62 derived; **0 shared, 0 unknown** |

**Registered package** `pkg-salt-lake-city-ut-6d474d2906ae01e0`
(`sha256:6d474d2906ae01e062dc5ef6158b3e167e244e5c780e2ab8478eb8ec36e0100d`), zone REGISTERED_LIVE: field-for-field
identical to `f084558e` (census, PF/NP records, seed rows, partition, official routes, evidence, unresolved rows,
founder holds — the `package_identity` gate) and it builds the **same bundle** `42035f18…`. The id differs only by zone,
source sha and sealed_at.

## 5. Timer (Phase 7)

| | |
|---|---|
| REGISTER COMMAND TIME | ≈5 s (17:47:37Z start → report stamped 17:47:42Z) |
| SEAL TIME | 216.0 s (live-parent read 79.6 s, FAST 134.6 s) |
| FAST COLD-BUILD TIME | 134.6 s |
| PACKET TIME | 154.9 s (classification proof 149.5 s) |
| GENERIC REGISTRATION-LANE TIME | **≈375.9 s ≈ 6 m 16 s** |
| TOTAL WALL CLOCK | **≈ 30 m 18 s** (17:38:02Z live check → 18:08:20Z post-staging live probe) |

**≤ 5 minutes: MISSED** by ≈76 s — the excess is FAST's cold builds (134.6 s); without them the lane runs in ≈241 s
(4 m 1 s). **≤ 10 minutes: PASS**. The rest of the wall clock went to the repoint, the two market-local modules (release
contract, staging gates) and one gate correction (§9).

## 6. Participation and parent (Phases 8–9)

- salt-lake-city-ut `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH`, added once by reissue; all 44 live rows (and
  withheld Detroit) preserved, 0 changed.
- PARENT LOOKUP **PASS** (package parent 6ac5ba3b, current New Orleans-live); PARENT ROUTES PRESERVED **PASS** (all
  4,663 parent index routes carried).

## 7. Staging and projected accounting (Phases 10–11)

| | |
|---|---|
| UNCHANGED BUNDLES REUSED | **44** |
| UNCHANGED MARKETS REBUILT | **0** |
| SALT LAKE CITY BUNDLES BUILT | **1** (FAST's own cold builds of the one bundle) |
| PHYSICAL FRAGMENTS RERENDERED | **0** (no whole-site assembly; the candidate was composed twice by the seal and agrees) |

| | |
|---|---:|
| SALT LAKE CITY PROJECTED PROFILES | **133** |
| SALT LAKE CITY RELEASE-INDEX ROUTES | **144** (133 hotels + 10 corridors + 1 hub) |
| SALT LAKE CITY SERVED ROUTES | **145** (the 144 plus its policy-comparison page, from the built sitemap) |
| CANDIDATE MARKETS | **45** |
| CANDIDATE PROFILES | **4,373** (4,240 + 133) |
| CANDIDATE RELEASE-INDEX ROUTES | **4,807** (4,663 + 144) |
| CANDIDATE SERVED ROUTES | **4,885** (4,740 + 145) |

## 8. Safety (Phases 12–19)

`markets/reports/salt_lake_city_ut_registration_checks_002.json` (`salt_lake_city_ut_registration_checks_002.py`), run on
the site the seal's FAST build produced (`C:/t/slc3/oa/site`) over the registered root documents.

- **Reader:** PF with explicit refusal 0; question-only PF 0; service-animal-only 0; NP quote without refusal 0; the shared
  reader run on every record agrees (0); Rule C (shared first-party binding) 162 / 162 eligible. Shared reader not modified.
- **Fees:** 21 single-basis publish; 39 tiered withheld; 13 unsafe withheld (8 basis not stated, 2 two bases, 2 sentence
  cut, 1 stay-length); 0 withheld fees flattened (199 record matches); **AC Hotel Salt Lake City Downtown** ("$75 pet fee for
  entire stay" beside a per-night field) publishes no fee; MISLEADING SINGLE FEES 0.
- **Park City:** 32 rows, every one published as Park City, UT with its own postal code (16 Park City seed rows, all
  Park City, UT); **PARK CITY PROFILES LABELED SALT LAKE CITY = 0**; fixed traps correct (Grand Hyatt Deer Valley and Canopy
  by Hilton Deer Valley 84060 Park City; Holiday Inn Express & Suites Park City and Hyatt Centric Park City 84098 Park City;
  Fairfield Cottonwood 84121 Holladay; MainStay Fort Union 84121 Cottonwood Heights; Fairfield SLC South 84123 Murray).
- **Municipalities:** wrong-city 0; every row's city is a municipality its own postal code carries; 0 non-Utah rows; 0
  seed rows with a rewritten city, ZIP or state; pin envelope is Salt Lake City's (40.35–40.94 N, 112.08–111.43 W).
- **Resort / timeshare:** timeshare published 0; private condo / residence / rental published 0 (172 refused or
  unproven rows checked by name, plus the 19 timeshares); canyon resorts published 0; no residence enters by sharing a
  resort campus.
- **Market text:** New Orleans / Louisiana 0, Kansas City / Missouri 0, Minneapolis 0, Portland 0, Seattle 0 across the
  11 registered documents (the "New Orleans-live lineage" statement is the lineage, allowed by name); market label "Salt Lake
  City / Park City / Wasatch Front, Utah" correct; boundary audit names Provo–Orem, Ogden–Davis, Heber–Jordanelle,
  Snowbird–Alta and Solitude–Brighton (0 admitted from each). Clone residue scan: text 0, coordinates 0, boundary 0.
- **Cross-market:** collisions 0; bare-chain names 0; duplicate excluded identities 0; live properties moved 0.
- **Delta:** unexpected market / profile / route delta `[]`; prior markets, profiles, index routes and served routes
  lost 0; Salt Lake City the only new market; `release_index.compare` 0 findings.
- **FAST receipt:** `pkg-salt-lake-city-ut-6d474d2906ae01e0-7f8811ce601d32c4` CURRENTLY ELIGIBLE (the only receipt
  selected); J PASS, 819 files / 803 HTML, bundle `42035f18…` (not `e3b0c442`); K BYTE_IDENTICAL; 0 defects.
- **Staging gates: 34 / 34 PASS.** Deployment refusal **EXPECTED / PASS**: 0 authorizations and 0 deployment records
  name salt-lake-city-ut; not founder-authorized.

## 9. One correction made in this order

The first run of the gate module failed `private_condo_residence_rental_safety` on "silver baron lodge": that identity key
names both the ADMITTED, held row (2250 Deer Valley Dr South, ACCESS_BLOCKED, publishing nothing) and two non-admitted
map / page rows at 2800 / 2880 Deer Valley Drive. The gate derived its rental cohort from non-admitted rows without
excluding keys an admitted row also carries; it now checks such a key through the admitted row's own hold (the
all-unresolved gate). No data changed. (A one-parenthesis syntax slip in that edit briefly left a stale report on disk;
it was caught before anything was committed.)

## 10. Live safety (Phase 20)

After staging: live deploy unchanged (6ac5ba3b, 44 / 4,240 / 4,740, host verified). Salt Lake City hub and all **145**
projected routes **404**. New Orleans, Kansas City, Minneapolis, Portland, Seattle, San Antonio, Austin, Phoenix, Denver,
San Diego, Jacksonville FL, West Palm Beach, Fort Lauderdale, Augusta **200**; Detroit **404**
(`salt_lake_city_ut_registration_live_probe_002.json`).

## 11. Isolation

No shared reader or factory implementation changed; no broad regression; no acquisition, spend, founder
authorization, deployment authorization or deployment. Shared documents touched are exactly the registration-owned
six: `launch_participation.json` (reissued), `bundle_cache_closure.json` (+2), the three generated globals and the
market-state pin. The seal's work directory `C:/t/slc3` is kept (it holds the built candidate site the gates read). Only
processes this order started were run, and each has exited.

## FINAL ANSWERS

1. CURRENT LIVE DEPLOYMENT = 6ac5ba3bcda3a604f7e467e0
2. CURRENT LIVE MARKETS = 44
3. CURRENT LIVE PROFILES = 4,240
4. CURRENT LIVE RELEASE-INDEX ROUTES = 4,663
5. CURRENT LIVE SERVED ROUTES = 4,740
6. SALT LAKE CITY SOURCE PACKAGE = pkg-salt-lake-city-ut-f084558e8d8acabe
7. REGISTERED SALT LAKE CITY PACKAGE = pkg-salt-lake-city-ut-6d474d2906ae01e0
8. PACKAGE DIGEST = sha256:6d474d2906ae01e062dc5ef6158b3e167e244e5c780e2ab8478eb8ec36e0100d (source: sha256:f084558e8d8acabeb116c094b6cc4863e226586fd0f05844061f40a0eb05e2e1)
9. SOURCE-READY COMMIT = bb0ac0d4
10. SUPERSEDED PACKAGE SELECTED = NO
11. AUTOMATIC BASE DERIVES = YES
12. DERIVED BASE = a67c8e75f47b81942436e0d12956e3ec52510446
13. REGISTRATION CLASS = COMPOSITE_FRESH_MARKET_DATA_ONLY
14. AUTOMATIC CLASSIFICATION = YES
15. CLASSIFIER CHECKS = 15/15 PASS
16. ELIGIBLE = YES
17. FULL_REGRESSION_REQUIRED = NO
18. REGISTER COMMAND TIME = ≈5 s
19. SEAL TIME = 216.0 s
20. FAST COLD-BUILD TIME = 134.6 s
21. PACKET TIME = 154.9 s
22. GENERIC REGISTRATION-LANE TIME = ≈375.9 s (6 m 16 s)
23. <=5M TARGET = MISSED by ≈76 s (FAST cold builds 134.6 s; ≈241 s without them)
24. <=10M HARD LIMIT = PASS
25. BROAD REGRESSION RUNS = 0
26. SHARED PATHS = 0
27. UNKNOWN PATHS = 0
28. PARENT LOOKUP = PASS
29. PARENT ROUTES PRESERVED = PASS
30. UNCHANGED BUNDLES REUSED = 44
31. UNCHANGED MARKETS REBUILT = 0
32. PHYSICAL FRAGMENTS RERENDERED = 0
33. SALT LAKE CITY BUNDLES BUILT = 1
34. SALT LAKE CITY PROJECTED PROFILES = 133
35. SALT LAKE CITY RELEASE-INDEX ROUTES = 144
36. SALT LAKE CITY SERVED ROUTES = 145
37. CANDIDATE MARKETS = 45
38. CANDIDATE PROFILES = 4,373
39. CANDIDATE RELEASE-INDEX ROUTES = 4,807
40. CANDIDATE SERVED ROUTES = 4,885
41. APPROVED SALT LAKE CITY PROFILES = 133
42. UNAPPROVED SALT LAKE CITY PROFILES = 0
43. HYATT PLACE COTTONWOOD PUBLISHED = 0
44. HYATT PLACE LEHI PUBLISHED = 0
45. PARK CITY PROFILES LABELED SALT LAKE CITY = 0
46. PREOPENING PROFILES PUBLISHED = 0
47. TIMESHARE / VACATION-OWNERSHIP PROFILES PUBLISHED = 0
48. PRIVATE CONDO / RESIDENCE PROFILES PUBLISHED = 0
49. PET-FRIENDLY WITH EXPLICIT REFUSAL = 0
50. QUESTION-ONLY PET-FRIENDLY = 0
51. SERVICE-ANIMAL-ONLY ACCEPTANCE = 0
52. MISLEADING SINGLE FEES = 0
53. CLONE MARKET TEXT RESIDUE = 0
54. CLONE COORDINATE RESIDUE = 0
55. CROSS-MARKET COLLISIONS = 0
56. FAST RECEIPT CURRENTLY ELIGIBLE = YES
57. RULE J NONEMPTY = PASS (819 files / 803 HTML)
58. RULE K NONVACUOUS = PASS (BYTE_IDENTICAL)
59. ALL STAGING GATES = PASS (34/34)
60. DEPLOYMENT REFUSAL = EXPECTED / PASS
61. CURRENT LIVE MODIFIED = NO
62. DEPLOYMENT PERFORMED = NO
63. SALT LAKE CITY LIVE = NO
64. origin == HEAD = YES (verified after push)
65. tree clean = YES (verified after push)
66. READY FOR FOUNDER LAUNCH AUTHORIZATION = YES (bind BUILD commit 2822639c, package 6d474d29)

SALT LAKE CITY REGISTRATION = PASS
SALT LAKE CITY STAGING = PASS
AUTOMATIC BASE DERIVES = YES
FULL_REGRESSION_REQUIRED = NO
BROAD REGRESSION RUNS = 0
PARK CITY PROFILES LABELED SALT LAKE CITY = 0
PET-FRIENDLY RECORDS WITH EXPLICIT REFUSAL = 0
QUESTION-ONLY PET-FRIENDLY RECORDS = 0
SERVICE-ANIMAL-ONLY ACCEPTANCE = 0
UNAPPROVED SALT LAKE CITY PROFILES = 0
MISLEADING SINGLE FEES = 0
UNCHANGED MARKETS REBUILT = 0
CURRENT LIVE MODIFIED = NO
SALT LAKE CITY DEPLOYED = NO
READY FOR FOUNDER LAUNCH AUTHORIZATION = YES

STOP.
