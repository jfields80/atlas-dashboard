# PTF-KANSAS-CITY-MO-REGISTRATION-AND-STAGING-002 — FINAL

**Status:** Kansas City / Greater Kansas City (Missouri & Kansas) is **REGISTERED and STAGED**. The readiness packet is
**AUTHORIZATION_READY**; founder status AWAITING_FOUNDER_AUTHORIZATION.

**Not done:** nothing was deployed; there is no founder launch authorization and no deployment authorization; current
live is unchanged.

**Branch:** `worker/ptf-kansas-city-mo-market-001` (worktree `C:\Atlas-Kansas-City-MO-Hardened-V1`).

**Commits:**
- `d054d6c0` — the registration transaction. This is the **BUILD commit** a founder authorization must bind.
- the final commit — the automatic classification, the readiness packet, the live probe and this report.

## 1. Current live (Phase 1)

`release_index live-source --fetch --verify-host` at 01:02Z and again after staging at 01:32Z — unchanged both times:

| | |
|---|---|
| CURRENT LIVE SOURCE COMMIT | `d57623030b95f153ec3fc82c7149c5960efc6625` (built_from `239c2836`) |
| CURRENT LIVE DEPLOYMENT | **`6ac3bfda7b585d009f007620`** (record `ptf-deploy-minneapolis-004-…`) |
| CURRENT LIVE BUNDLE | `3d7c53a1ba2adc6ca9141e88384a7ef1e1e84abf7bdf21a4417ae664ff33af24` |
| CURRENT LIVE SITEMAP | `524d9d35c96668eaff45dfeb4f95edf7659ff815c7eb2d3f69a57658723ca7a1` |
| CURRENT LIVE MARKETS | **42** (Detroit withheld) |
| CURRENT LIVE PROFILES | **3,975** |
| CURRENT LIVE RELEASE-INDEX ROUTES | **4,377** (counted from the live index) |
| CURRENT LIVE SERVED ROUTES | **4,452** |
| HOST VERIFIED | YES |

## 2. Automatic base (Phase 2)

`derive_registration_base('kansas-city-mo', d5762303…)` → **`e74dee3b8d6375998271e49cd0e77fa569679227`** with no
manual input (newest first-parent ancestor naming no Kansas City path and carrying the live-truth files). `packet`
re-derived the same base on its own. No base or classification was supplied.

## 3. Source package (Phases 3–5)

| | |
|---|---|
| SOURCE PACKAGE | `pkg-kansas-city-mo-24718ac004c967b8`, `sha256:24718ac0…0402`, sealed from `39b3ec70` |
| SOURCE RECEIPT | `…-bcbd3d220f61eaa8`, currently eligible; FAST 15/15; J 976 files / 960 HTML; K BYTE_IDENTICAL |
| census | 290 — PF 161, NP 60, resolved 221, unresolved 69 (76.2 %), actionable 0 |
| states | Missouri **189**, Kansas **101**; KS→MO mislabels **0**, MO→KS **0**; seed rows with a rewritten state **0** |

Held cohort (founder ruling) — every row checked by name on the built site: no profile, no NP record, no release-index
route, no served route:

| held | census state | published |
|---|---|---|
| Aloft + Element North Kansas City (1875 Diamond Pkwy) | ADMITTED, IDENTITY_MISMATCH_HOLD | 0 / 2 |
| AC Hotel + Residence Inn Lenexa City Center (8710 Penrose Ln) | ADMITTED, IDENTITY_MISMATCH_HOLD | 0 / 2 |
| Courtyard + Residence Inn KC Downtown / Convention Center (1535 Baltimore) | ADMITTED, IDENTITY_MISMATCH_HOLD | 0 / 2 |
| Hilton Garden Inn Overland Park (rebrand) | NOT ADMITTED, SAME_IDENTITY_REBRAND_SUCCESSOR | 0 |
| Sleep Inn Olathe (rebrand) | NOT ADMITTED, SAME_IDENTITY_REBRAND_SUCCESSOR | 0 |
| ESA Kansas City – Airport – Tiffany Springs (DataDome) | ADMITTED, ACCESS_BLOCKED | 0 |
| Extended Stay Kansas City (the Crossland route; never revisited, never evidence) | ADMITTED, ROUTING_HOLD | 0 |
| 4 preopening (Park Hotel on the Plaza, Home2 Speedway, Spark KC Airport, DoubleTree KCI) | ADMITTED, EVIDENCE_HOLD | 0 / 4 |
| WorldMark Lake of the Ozarks (timeshare) | NOT ADMITTED, NON_LODGING | 0 |

All 69 unresolved rows publish nothing. `identity_resolutions.json` was **not** written; no rebrand ruling was made; no
acquisition ran.

## 4. Canonical registration (Phase 6)

Minneapolis's `4c3abd44` recipe, replayed:

1. **Repoint** — 15 market-local modules, 24 edits, path constants only (`identity_census_proposed/` → `identity_census/`,
   `markets/proposed/` → `markets/`, staging `launch_package/` → the package root); the publication-safety audit split
   into a pure `audit()` (report unchanged, all zero).
2. **Promotion** — census and market document moved with `git mv`; policy package, proposed authority and final
   partition regenerated at the package root by their own writers. **All five byte-identical to the sealed copies.**
3. **Shard** — `market_registration_cli --write`: 161 seed rows, 60 exclusions, empty routing and affiliate shards.
   **All four byte-identical to the sealed shard.**
4. **Globals** — `build_global_authority --write`, then `--check` clean: exclusions 1,733 → **1,793** (+60, all
   kansas-city-mo); seed rows 4,124 → **4,285** (+161); **0 removed or modified**.
5. **Release contract** — `kansas_city_mo_release_contract_002.py`, fully derived through
   `release_contracts.derive_authority`, 0 disagreements; `verify_all()` **44 / 44** clean.
6. **`register`** (13.4 s) — participation 43 → 44 rows, kansas-city-mo added once at
   `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH`; 0 rows removed, **0 changed**; founder-authorized set
   unchanged at 42; `load_participation()` loads, `decision_problems = []`; build closure gained exactly the release
   contract and the market document.
7. **`seal --work C:/t/kc3a --work-order`** (416.0 s, detached) — package `pkg-kansas-city-mo-140e35291a2195c3`,
   reproducible YES; FAST 15/15 in 343.6 s; candidate 43 / 4,136 / 4,552, reproducible YES; pin block census 290 /
   PF 161 / NP 60 / corridor routes 13.
8. **Commit** `d054d6c0`, then **`packet`** with no `--classification` (118.0 s).

| | |
|---|---|
| classification_source | **AUTOMATIC** |
| CLASS | **COMPOSITE_FRESH_MARKET_DATA_ONLY** |
| ELIGIBLE | **YES** — 15/15 checks PASS (change_set, market_local_zone, discovery_config, registration_input, identity_resolutions, participation, release_contract, build_closure, derived_globals, sealed_package, fast_receipt, expected_release, identity_routes, market_state_pin, release_integrity) |
| FULL_REGRESSION_REQUIRED | **NO** |
| REMOTE BROAD JOBS / BROAD REGRESSION RUNS | **0 / 0** |
| Change set | 106 paths: 34 market-local, 13 registration data, 59 derived; **0 shared, 0 unknown** |

**Registered package** `pkg-kansas-city-mo-140e35291a2195c3`
(`sha256:140e35291a2195c359b0c4210741f2d8acff9250f4555cdadd3549e931145167`), zone REGISTERED_LIVE: field-for-field
identical to `24718ac0` (census, PF/NP records, seed rows, partition, official routes, evidence, unresolved rows,
founder holds — checked by the `package_identity` gate) and it builds the **same bundle** `f454f0bd…`. The id differs
only by zone, source sha and sealed_at.

## 5. Timer (Phase 7)

| | |
|---|---|
| REGISTER COMMAND TIME | 13.4 s |
| SEAL TIME | 416.0 s (live-parent read 69.9 s, FAST 343.6 s) |
| FAST COLD-BUILD TIME | 343.6 s |
| PACKET TIME | 118.0 s (classification proof 113.0 s) |
| GENERIC REGISTRATION-LANE TIME | **547.4 s ≈ 9 m 07 s** |
| TOTAL WALL CLOCK | **29 m 32 s** (01:02:02Z live check → 01:31:34Z packet) |

**≤ 5 minutes: MISSED** by 4 m 07 s — the cause is FAST's cold builds (343.6 s; free memory ~2.6 GB on the 16 GB
machine). Without them the lane runs in 203.8 s (3 m 24 s). **≤ 10 minutes: PASS** (9 m 07 s). The rest of the wall
clock went to the repoint, the two market-local modules (release contract, staging gates) and one gate-module
correction (§9).

## 6. Participation and parent (Phases 8–9)

- kansas-city-mo `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH`, added once by reissue; all 42 live rows (and
  withheld Detroit) preserved, 0 changed.
- PARENT LOOKUP **PASS** (package parent 6ac3bfda, current Minneapolis-live); PARENT ROUTES PRESERVED **PASS** (all
  4,377 parent index routes carried).

## 7. Staging and projected accounting (Phases 10–11)

| | |
|---|---|
| UNCHANGED BUNDLES REUSED | **42** |
| UNCHANGED MARKETS REBUILT | **0** |
| KANSAS CITY BUNDLES BUILT | **1** (FAST's own cold builds of the one bundle) |
| PHYSICAL FRAGMENTS RERENDERED | **0** (no whole-site assembly; the candidate was composed twice by the seal and agrees) |

| | |
|---|---:|
| KANSAS CITY PROJECTED PROFILES | **161** |
| KANSAS CITY RELEASE-INDEX ROUTES | **175** (161 hotels + 13 corridors + 1 hub) |
| KANSAS CITY SERVED ROUTES | **176** (the 175 plus its policy-comparison page, from the built sitemap) |
| CANDIDATE MARKETS | **43** |
| CANDIDATE PROFILES | **4,136** (3,975 + 161) |
| CANDIDATE RELEASE-INDEX ROUTES | **4,552** (4,377 + 175) |
| CANDIDATE SERVED ROUTES | **4,628** (4,452 + 176) |

## 8. Safety (Phases 12–18)

`markets/reports/kansas_city_mo_registration_checks_002.json` (`kansas_city_mo_registration_checks_002.py`), run on the
site the seal's FAST build produced (`C:/t/kc3a/oa/site`) over the registered root documents.

- **Reader:** PF with explicit refusal 0; question-only PF 0; service-animal-only 0; NP quote without refusal 0;
  Rule C (shared first-party binding) 221 / 221 eligible. Shared reader not modified.
- **Fees:** 25 single-basis publish; 37 tiered withheld; 17 unsafe withheld (16 basis not stated, 1 stay-length); 0
  withheld fees flattened (186 record matches); the three Drury "daily fee" rows publish no fee; MISLEADING SINGLE
  FEES 0.
- **Market text:** MINNEAPOLIS / ST PAUL residue **0**, OREGON / PORTLAND residue **0** across the 11 registered
  documents (`520 Minnesota Avenue` in Kansas City, KS and the Oregon Trail Apartments row are Kansas City facts);
  market label "Kansas City / Greater Kansas City, Missouri & Kansas" correct; boundary audit names Lawrence, Topeka,
  St. Joseph, Columbia, Manhattan and Lake of the Ozarks (0 admitted from each).
- **Cross-state:** the name traps stay where their codes put them — Sonesta Select "South Overland Park" 64131 MO,
  ESA "Shawnee Mission" 66202 KS, Drury "Independence" 64015 MO, Hotel Lotus Merriam 66203 KS; pin envelope is
  Kansas City's (38.77–39.35 N, 94.94–94.15 W).
- **Cross-market:** collisions 0; bare-chain names 0; duplicate excluded identities 0; live properties moved 0.
- **Delta:** unexpected market / profile / route delta `[]`; prior markets, profiles, index routes and served routes
  lost 0; Kansas City the only new market; `release_index.compare` 0 findings.
- **FAST receipt:** `pkg-kansas-city-mo-140e35291a2195c3-b0245f8a1e4420b7` CURRENTLY ELIGIBLE (the only receipt
  selected); J PASS, 976 files / 960 HTML, bundle `f454f0bd…` (not `e3b0c442`); K BYTE_IDENTICAL; 0 defects.
- **Staging gates: 29 / 29 PASS.** Deployment refusal **EXPECTED / PASS**: 0 authorizations and 0 deployment records
  name kansas-city-mo; not founder-authorized.

## 9. One correction made in this order

The first run of the gate module flagged two "residue" hits in the census and package — `"520|minnesota|66101"` (the
folded street identity of 520 Minnesota Avenue, Kansas City, KS) and `oregon-trail-apartments`. The allowlist knew
only the spelled-out forms; it now accepts these two folded forms. No data changed. A sweep of all KC report text
found only the Places allowance ledger naming other orders' usage — factual, not Kansas City text.

## 10. Live safety (Phase 19)

After staging: live deploy unchanged (6ac3bfda, 42 / 3,975 / 4,452, host verified). Kansas City hub and all **176**
projected routes **404**. Minneapolis, Portland, Seattle, San Antonio, Austin, Phoenix, Denver, San Diego,
Jacksonville FL, West Palm Beach, Fort Lauderdale, Augusta **200**; Detroit **404**.

## 11. Isolation

No shared reader or factory implementation changed; no broad regression; no acquisition, spend, founder
authorization, deployment authorization or deployment. Shared documents touched are exactly the registration-owned
six: `launch_participation.json` (reissued), `bundle_cache_closure.json` (+2), the three generated globals and the
market-state pin. The seal's work directory `C:/t/kc3a` is kept (it holds the built candidate site the gates read).

## Next

Founder launch authorization of `pkg-kansas-city-mo-140e35291a2195c3`, binding BUILD commit `d054d6c0`. If authorized:
+1 market / +161 profiles / +175 index / +176 served → 43 / 4,136 / 4,552 / 4,628.
