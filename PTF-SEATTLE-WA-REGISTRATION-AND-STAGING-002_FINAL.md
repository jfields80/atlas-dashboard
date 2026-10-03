# PTF-SEATTLE-WA-REGISTRATION-AND-STAGING-002 — FINAL

**Status:** Seattle is **REGISTERED and STAGED**. The readiness packet is **AUTHORIZATION_READY**, and the founder
status is AWAITING_FOUNDER_AUTHORIZATION.

**Not done:** nothing was deployed; no founder launch authorization and no deployment authorization exist; current
live is unchanged.

**Branch:** `worker/ptf-seattle-wa-market-001` (worktree `C:\Atlas-Seattle-WA-Hardened-V1`).

**Commits:**
- `89d6f249`: the registration transaction. This is the **BUILD commit** a founder authorization must bind.
- The final commit: the automatic classification, the readiness packet, the live probe and this report.

## 1. Current live (Phase 1)

Resolved with the canonical resolver (`release_index live-source --fetch --verify-host`) at 13:23Z, and again after
staging at 13:45:49Z. Both times it was unchanged:

| | |
|---|---|
| CURRENT LIVE SOURCE COMMIT | `606839025c4c13c25d4d03984c7d5c049d27c73f` (built_from `be83dab2`) |
| CURRENT LIVE DEPLOYMENT | **`6ac064cd6a4261e60054a2f3`**, record `ptf-deploy-san-antonio-005-6ac064cd6a4261e60054a2f3.json` |
| CURRENT LIVE BUNDLE | `50b1ce95d80386ed9c28f16ad1493bc4c8f2588f201bb1f95597a6d6984a6bf4` |
| CURRENT LIVE SITEMAP | `e2a6b1c94dff6f9178fe83913c0babaf74f1b02b9453be37e29ad2c82a86b484` |
| CURRENT LIVE MARKETS | **39** (Detroit withheld) |
| CURRENT LIVE PROFILES | **3,530** |
| CURRENT LIVE RELEASE-INDEX ROUTES | **3,894** |
| CURRENT LIVE SERVED ROUTES | **3,966** |
| HOST VERIFIED | YES |

Live had not advanced, so registration ran against current production.

## 2. Automatic base (Phase 2)

`registration_release_lane.derive_registration_base('seattle-wa', 60683902…)` returned **`5bd543044e6c90a5d00f6c3f1a998b6ebd39270a`**
(the San Antonio deploy-final commit) with no manual input. The `packet` step re-derived the same base on its own.
No base or classification was supplied.

- AUTOMATIC BASE DERIVES = **YES**
- DERIVED BASE = `5bd54304`
- CURRENT LIVE LINEAGE COMMIT = `60683902`

## 3. Source package and what was registered (Phases 3–4)

**Source package** `pkg-seattle-wa-d39a3919f10cf45b`, `sha256:d39a3919f10cf45bb1d5728fbb6255c0fefb6e17b819c0e4bc9b4376d749061f`:

| | |
|---|---|
| status | SOURCE READY YES, COVERAGE READY YES, ACTIONABLE UNRESOLVED 0 |
| census | 303: PF 139, NP 61, resolved 200, unresolved 103 |
| FAST | 15/15; Rule J 853 files / 837 HTML; Rule K BYTE_IDENTICAL |
| reproducible | YES (in-process and independent) |
| receipt | `…-d315b3cad2dba55d.json`, still eligible in its own shadow-receipt directory |
| safety | explicit-refusal PF 0, question-only PF 0, preopening 0, timeshare 0, misleading single fees 0 |

**Registered package** `pkg-seattle-wa-784f0147e1220f40`, `sha256:784f0147e1220f409eb7e5d7e9a4fd70af102c249a1bbf4468a3402d327d534e`,
zone REGISTERED_LIVE:
- Field-for-field identical to `d39a3919`: census, PF and NP records, seed rows, partition, official routes, evidence
  references, unresolved rows and founder holds (the staging gate `package_identity` checks every field).
- It builds the **same bundle**, `1872172c1e40f99a…`.
- The id differs only because the zone, the source sha and the sealed_at differ.

**Held cohort:** all 103 unresolved rows are preserved as committed. No acquisition ran, and no held row was
resolved. `identity_resolutions.json` was **not** written.

## 4. Canonical registration (Phase 5)

This is the ordinary composite fresh-market path, in San Antonio's order.

1. **Repoint.** 15 market-local modules moved from the shadow zone to the registered zone. Only path constants
   changed: `identity_census_proposed/` → `identity_census/`, `markets/proposed/` → `markets/`, and staging
   `launch_package/` → the package root. The publication safety audit was split into a pure `audit()` function; its
   report is byte-identical.
2. **Promotion.** The census and market document were moved with `git mv` (R100).
   - The policy package, proposed authority and final partition were regenerated at the package root by their own
     writers.
   - **All five are byte-identical to the sealed copies** (policy `8090a91c…` = the package's dependency digest).
3. **Authority shard.** `market_registration_cli --write` produced 139 seed rows and 61 exclusions, plus empty
   routing and affiliate shards. **All four are byte-identical to the sealed shard.**
4. **Globals.** `build_global_authority --write`, then `--check` clean:
   - exclusions 1,559 → **1,620** (+61, all seattle-wa);
   - seed rows 3,679 → **3,818** (+139, all seattle-wa);
   - **0 removed or modified.**
5. **Release contract.** `deploy/netlify/release_contracts/seattle-wa.json`, written by
   `seattle_wa_release_contract_002.py`:
   - fully derived through `release_contracts.derive_authority`, 0 disagreements;
   - `verify_all()`: **41 / 41** clean.
6. **`register`** (5.6 s):
   - participation 40 → 41 rows: seattle-wa added once at `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH`;
   - 0 rows removed, **0 existing rows changed**; the founder-authorized set is unchanged at 39;
   - the build closure gained exactly the release contract and the market document.
7. **`seal --work C:/t/sea3a --work-order`** (246.3 s):
   - package `784f0147`, reproducible YES;
   - FAST 15/15 in 175.9 s;
   - candidate 40 / 3,669 / 4,044, reproducible YES;
   - pin block: census 303 / PF 139 / NP 61 / corridor routes 10.
8. **Commit** `89d6f249`, then **`packet`** with no `--classification`.

**`packet` (automatic):** live source `60683902`, deploy `6ac064cd`, base `5bd54304` (95.9 s; classification proof 90.4 s).

| | |
|---|---|
| classification_source | **AUTOMATIC** |
| CLASS | **COMPOSITE_FRESH_MARKET_DATA_ONLY** |
| ELIGIBLE | **YES**: 15/15 classifier checks PASS (change_set, market_local_zone, discovery_config, registration_input, identity_resolutions, participation, release_contract, build_closure, derived_globals, sealed_package, fast_receipt, expected_release, identity_routes, market_state_pin, release_integrity) |
| FULL_REGRESSION_REQUIRED | **NO** |
| REMOTE BROAD JOBS / BROAD REGRESSION RUNS | **0 / 0** |
| Change set | 108 paths: 34 market-local, 13 registration data, 61 derived; **0 shared, 0 unknown** |
| packet status | **AUTHORIZATION_READY**, founder AWAITING_FOUNDER_AUTHORIZATION |

The packet is `markets/reports/seattle_wa_registration_authorization_readiness.json`, and the classification is
beside it.

**expected_release.** The expected candidate digest (`374b71d5…`, built from the live parent plus the sealed
package) and the actual digest (`3e72dcb6…`, built from the committed authority) differ by construction, as Austin's
and San Antonio's did. The check compares **complete sets**, and they agree: 40 / 3,669 / 4,044, with 0 unexpected
changes.

## 5. Timer (Phase 6)

| | |
|---|---|
| REGISTER COMMAND TIME | 5.6 s |
| SEAL TIME | 246.3 s, of which FAST cold builds take 175.9 s (J 112.6 s + K 61.6 s) and the live-parent read 68.4 s |
| PACKET TIME | 95.9 s (automatic classification proof 90.4 s) |
| GENERIC REGISTRATION-LANE TIME | **347.8 s ≈ 5 m 48 s** |
| TOTAL WALL CLOCK | **21 m 26 s** (13:23:29Z live check → 13:44:55Z packet) |

**≤ 5 minutes: MISSED by 48 s.** FAST's two cold builds alone take 2 m 56 s; without them the lane runs in 2 m 52 s.

**≤ 10 minutes:** the lane passes (5 m 48 s). Total wall clock does not. The extra time went to:
- reading San Antonio's recipe;
- writing the two market-local modules (release contract, staging checks);
- the repoint;
- one correction to my own staging-checks module (§7).

There was no refusal, no supplied classification, and no factory repair.

## 6. Held-row, reader and fee safety (Phases 4, 11–13)

Recorded in `markets/reports/seattle_wa_registration_checks_002.json` (`seattle_wa_registration_checks_002.py`).
- Every check runs on the site the seal's own FAST build produced (`C:/t/sea3a/oa/site`).
- Profiles are compared by the route the site forms (`release_index.hotel_route`), never by census slug.

**Held-row safety**, published / rows:

| held class | published |
|---|---:|
| dual-brand founder rows (Aloft / Element Redmond, HIX / Staybridge Federal Way) | **0 / 4** |
| preopening (Hotel Interurban Seattle Tukwila) | **0 / 1** |
| Courtyard Seattle Northgate (contradictory "Service Animals with credentials only") | **0 / 1** |
| FairBridge Inn Express Tukwila rebrand (Days Inn row IDENTITY_REVIEW + new-name observation) | **0 / 2**, SAFE |
| Motel 6 Suites Kent rebrand (ESA Seattle Kent row unresolved + new-name observation) | **0 / 2**, SAFE |
| router-exhausted | 0 / 98 |
| by disposition: routing 37, source-silent 33, evidence 19, identity 8, access 6 | 0 each |
| **all unresolved** | **0 / 103** |

- **Hotel Interurban:** profile **absent**, release-index route **absent**, served route **absent**.
- **Profiles built:** 139 Seattle profiles, all approved. **UNAPPROVED SEATTLE PROFILES = 0.**
- **Census rows not admitted** (outside 380, name-only 247, non-lodging 261, identity-review 99, duplicate 4,
  same-campus 1): 0 publish as a distinct entity.
- **Same-name second sightings:** 4 non-admitted rows share a published hotel's name. Each is listed in the checks
  report and none is resolved here.
  - Two are a competitor or name-only lead with no address (Country Inn Bothell, Hilton Motif Seattle).
  - **Places' "19333 North Creek Parkway South, 98011"** (SAME_CAMPUS) is Country Inn Bothell itself, published at
    19333 North Creek Parkway, 98011: same house number, same ZIP.
  - **W Seattle's City of Seattle business licence** (OUTSIDE_MARKET) carries only the licensee's office (W Operating
    Company LLC, Scottsdale AZ 85254). It is not a hotel elsewhere.

**Reader safety.** The registered root documents are byte-identical to the sealed ones.
- PET-FRIENDLY WITH EXPLICIT REFUSAL **0**; QUESTION-ONLY PET-FRIENDLY **0**; SERVICE-ANIMAL-ONLY ACCEPTANCE **0**;
- no-pets quote without a refusal 0;
- Rule C (shared first-party binding): **200 / 200** eligible.
- The shared reader was not modified.

**Fee safety:**
- **25** single-basis fees publish;
- **39** tiered fees are withheld;
- **15** unsafe single fees are withheld: basis not stated 8, two bases 2, waived 2, additional pet only 1 (Red Roof
  SeaTac), amount range 1, stay-length condition 1;
- every one of the 54 withheld fee quotes was matched to its record (148 matches), and **0 publish a single fee**;
- **MISLEADING SINGLE FEES 0**.

## 7. Staging, accounting, delta, collisions (Phases 7–10, 14–17)

**Participation (Phase 7):** seattle-wa is `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH`, added once, by
reissue. All 39 live rows (plus withheld Detroit) are preserved, and 0 are changed.

**Parent (Phase 8):**
- PARENT LOOKUP PASS: the package parent is `6ac064cd`, current San Antonio-live.
- PARENT ROUTES PRESERVED PASS: all 3,894 parent release-index routes are carried.

**Staging (Phase 9):**

| | |
|---|---|
| UNCHANGED BUNDLES REUSED | **39** (every live market's committed index entry is carried by identity) |
| UNCHANGED MARKETS REBUILT | **0** |
| SEATTLE BUNDLES BUILT | **1** (FAST's own two cold builds of the one bundle) |
| PHYSICAL FRAGMENTS RERENDERED | **0** (no whole-site assembly ran; the candidate was composed twice by the seal and agrees) |

**Projected accounting (Phase 10),** derived from candidate sets, not assumed:

| | |
|---|---:|
| SEATTLE PROJECTED PROFILES | **139** |
| SEATTLE RELEASE-INDEX ROUTES | **150** (139 hotels + 10 corridors + 1 hub) |
| SEATTLE SERVED ROUTES | **151** (the 150 plus its policy-comparison page, counted from the built sitemap) |
| CANDIDATE MARKETS | **40** |
| CANDIDATE PROFILES | **3,669** (3,530 + 139) |
| CANDIDATE RELEASE-INDEX ROUTES | **4,044** (3,894 + 150) |
| CANDIDATE SERVED ROUTES | **4,117** (3,966 + 151) |

**Delta safety (Phase 14):**
- UNEXPECTED MARKET, PROFILE and ROUTE DELTA: `[]`.
- Prior markets, profiles, release-index routes and served routes lost: 0.
- Seattle is the only new market. `release_index.compare`: 0 findings.

**Cross-market safety (Phase 15):** CROSS-MARKET COLLISIONS 0, BARE-CHAIN COLLISIONS 0 (no bare-chain-shaped name at
all), DUPLICATE EXCLUDED IDENTITIES 0, and 0 live properties moved or displaced.

**FAST receipt (Phase 16):**
- `pkg-seattle-wa-784f0147e1220f40-60013188aa5aff14.json` is **CURRENTLY ELIGIBLE**, the only receipt canonical
  selection returns.
- J PASS, NONEMPTY: 853 files / 837 HTML, bundle `1872172c…` (not `e3b0c442`).
- K PASS: BYTE_IDENTICAL, 0 defects.

**Staging gates (Phase 17): 24 / 24 PASS.**

| gates | |
|---|---|
| package and lane | package identity, registration lane eligible, FAST receipt eligibility, FAST A–O |
| parent and preservation | parent lookup, parent routes, markets, profiles, routes, candidate delta |
| decision and safety | participation, founder-row reconciliation (4 / 0 / 1), held cohort, rebrands, contradictory quote held, preopening, timeshare, military, reader, fee, collision |
| contracts and binding | first-party binding, release contracts |
| **deployment refusal** | **EXPECTED / PASS**: 0 deployment authorizations and 0 records name seattle-wa; not founder-authorized |

**Correction to my own checks module before it passed.** No package, data or shared code changed.
- The inherited held-cohort gate failed any distinct-class non-admitted row sharing a published name. It flagged the
  W Seattle licence row and Places' Country Inn Bothell row.
- Both are provably the published building. The gate now exempts exactly two shapes:
  - same house number **and** ZIP;
  - a licence-only row whose own ZIP is outside Washington's 980–994 range and whose name equals the published name.
- Each exemption is labelled in the report, and every other distinct-class match still fails outright.

## 8. Live safety (Phase 18)

Re-verified after staging, at 13:45Z (`markets/reports/seattle_wa_registration_live_probe_002.json`):
- Live is still `6ac064cd`: 39 / 3,530 / 3,966, host verified.
- **Seattle hub 404, and all 151 projected Seattle routes 404.**
- San Antonio, Austin, Phoenix, Denver, San Diego, Jacksonville FL, West Palm Beach, Fort Lauderdale and Augusta
  return **200**; Detroit **404**.

CURRENT LIVE MODIFIED = NO. No deploy, no deployment authorization, no founder authorization.

## 9. What the founder is now being asked to decide

Founder launch authorization of **`pkg-seattle-wa-784f0147e1220f40`** only, bound to BUILD commit **`89d6f249`**.

**Expected effect:** +1 market / +139 profiles / +150 release-index routes / +151 served routes, giving
**40 / 3,669 / 4,044 / 4,117**.

**Held and not part of the decision:**
- the 103 unresolved rows: 4 dual-brand, Hotel Interurban (preopening), Courtyard Northgate and the router-exhausted
  rest, including the FairBridge Tukwila and Motel 6 Suites Kent rebrands;
- every non-admitted census row.

The seal's scratch directory `C:/t/sea3a` was removed after the checks report was written. No temporary process
remains.

## FINAL ANSWERS

1. CURRENT LIVE DEPLOYMENT = 6ac064cd6a4261e60054a2f3 (San Antonio; lineage 60683902, built_from be83dab2)
2. CURRENT LIVE MARKETS = 39
3. CURRENT LIVE PROFILES = 3530
4. CURRENT LIVE RELEASE-INDEX ROUTES = 3894
5. CURRENT LIVE SERVED ROUTES = 3966
6. SEATTLE SOURCE PACKAGE = pkg-seattle-wa-d39a3919f10cf45b (sha256:d39a3919f10cf45bb1d5728fbb6255c0fefb6e17b819c0e4bc9b4376d749061f)
7. REGISTERED SEATTLE PACKAGE = pkg-seattle-wa-784f0147e1220f40 (content identical to d39a3919; same bundle 1872172c…)
8. PACKAGE DIGEST = sha256:784f0147e1220f409eb7e5d7e9a4fd70af102c249a1bbf4468a3402d327d534e
9. AUTOMATIC BASE DERIVES = YES
10. DERIVED BASE = 5bd543044e6c90a5d00f6c3f1a998b6ebd39270a
11. REGISTRATION CLASS = COMPOSITE_FRESH_MARKET_DATA_ONLY
12. AUTOMATIC CLASSIFICATION = YES (classification_source AUTOMATIC)
13. CLASSIFIER CHECKS = 15/15 PASS
14. ELIGIBLE = YES
15. FULL_REGRESSION_REQUIRED = NO
16. REGISTER COMMAND TIME = 5.6 s
17. SEAL TIME = 246.3 s (FAST cold builds 175.9 s; live-parent read 68.4 s)
18. PACKET TIME = 95.9 s (automatic classification proof 90.4 s)
19. GENERIC REGISTRATION-LANE TIME = 347.8 s (5 m 48 s)
20. <=5M TARGET = MISSED by 48 s (without FAST cold builds 2 m 52 s)
21. <=10M HARD LIMIT = lane PASS (5 m 48 s); total wall clock 21 m 26 s exceeds it (module writing + one check correction, no refusal)
22. BROAD REGRESSION RUNS = 0
23. SHARED PATHS = 0
24. UNKNOWN PATHS = 0
25. PARENT LOOKUP = PASS
26. PARENT ROUTES PRESERVED = PASS
27. UNCHANGED BUNDLES REUSED = 39
28. UNCHANGED MARKETS REBUILT = 0
29. PHYSICAL FRAGMENTS RERENDERED = 0
30. SEATTLE BUNDLES BUILT = 1
31. SEATTLE PROJECTED PROFILES = 139
32. SEATTLE RELEASE-INDEX ROUTES = 150
33. SEATTLE SERVED ROUTES = 151
34. CANDIDATE MARKETS = 40
35. CANDIDATE PROFILES = 3669
36. CANDIDATE RELEASE-INDEX ROUTES = 4044
37. CANDIDATE SERVED ROUTES = 4117
38. APPROVED SEATTLE PROFILES = 139
39. UNAPPROVED SEATTLE PROFILES = 0
40. DUAL-BRAND HELDS PUBLISHED = 0 / 4
41. PREOPENING PROFILES PUBLISHED = 0 (Hotel Interurban profile, release-index route and served route absent)
42. FAIRBRIDGE TUKWILA SAFE = YES
43. MOTEL 6 SUITES KENT SAFE = YES
44. PET-FRIENDLY WITH EXPLICIT REFUSAL = 0
45. QUESTION-ONLY PET-FRIENDLY = 0
46. MISLEADING SINGLE FEES = 0
47. CROSS-MARKET COLLISIONS = 0 (bare-chain 0, duplicate excluded identities 0)
48. FAST RECEIPT CURRENTLY ELIGIBLE = YES (pkg-seattle-wa-784f0147e1220f40-60013188aa5aff14.json)
49. RULE J NONEMPTY = PASS (853 files / 837 HTML, bundle 1872172c…)
50. RULE K NONVACUOUS = PASS (BYTE_IDENTICAL)
51. ALL STAGING GATES = PASS (24/24)
52. DEPLOYMENT REFUSAL = EXPECTED / PASS
53. CURRENT LIVE MODIFIED = NO
54. DEPLOYMENT PERFORMED = NO
55. SEATTLE LIVE = NO (hub + 151 routes 404)
56. origin == HEAD = YES (verified after push)
57. tree clean = YES (verified after push)
58. READY FOR FOUNDER LAUNCH AUTHORIZATION = YES (packet AUTHORIZATION_READY; authorize pkg-seattle-wa-784f0147e1220f40 only, bound to 89d6f249)

```
SEATTLE REGISTRATION = PASS
SEATTLE STAGING = PASS
AUTOMATIC BASE DERIVES = YES
FULL_REGRESSION_REQUIRED = NO
BROAD REGRESSION RUNS = 0
PET-FRIENDLY RECORDS WITH EXPLICIT REFUSAL = 0
QUESTION-ONLY PET-FRIENDLY RECORDS = 0
UNAPPROVED SEATTLE PROFILES = 0
MISLEADING SINGLE FEES = 0
UNCHANGED MARKETS REBUILT = 0
CURRENT LIVE MODIFIED = NO
SEATTLE DEPLOYED = NO
READY FOR FOUNDER LAUNCH AUTHORIZATION = YES
```
