# PTF-PORTLAND-OR-REGISTRATION-AND-STAGING-002 — FINAL

**Status:** Portland is **REGISTERED and STAGED**. The readiness packet is **AUTHORIZATION_READY**; the founder status
is AWAITING_FOUNDER_AUTHORIZATION.

**Not done:** nothing was deployed; there is no founder launch authorization and no deployment authorization; current
live is unchanged.

**Branch:** `worker/ptf-portland-or-market-001` (worktree `C:\Atlas-Portland-OR-Hardened-V1`).

**Commits:**
- `09850aa3`: the registration transaction. This is the **BUILD commit** a founder authorization must bind.
- The final commit: the automatic classification, the readiness packet, the live probe and this report.

## 1. Current live (Phase 1)

Resolved with the canonical resolver (`release_index live-source --fetch --verify-host`) at 02:59:59Z, and again after
staging at 03:16Z. Both times it was unchanged:

| | |
|---|---|
| CURRENT LIVE SOURCE COMMIT | `f0003e78b10d249774d376cc6bc2457d57cf63ce` (built_from `438348c7`) |
| CURRENT LIVE DEPLOYMENT | **`6ac169ef7c75c383eb79f824`**, record `ptf-deploy-seattle-004-6ac169ef7c75c383eb79f824.json` |
| CURRENT LIVE BUNDLE | `cfaad64a7bcb1b2b1734fe777ea577d5884aafe953054c2d80a7db1b01e0e5c3` |
| CURRENT LIVE SITEMAP | `63e052812b36668271aebb3f8bc933a44ac0d6150b7b8c19279d5f1e45a2b151` |
| CURRENT LIVE MARKETS | **40** (Detroit withheld) |
| CURRENT LIVE PROFILES | **3,669** |
| CURRENT LIVE RELEASE-INDEX ROUTES | **4,044** |
| CURRENT LIVE SERVED ROUTES | **4,117** |
| HOST VERIFIED | YES |

Live had not advanced, so registration ran against current production.

## 2. Automatic base (Phase 2)

`registration_release_lane.derive_registration_base('portland-or', f0003e78…)` returned
**`0e2e8bb89809c0a7929765089680f29453005a75`** (the Seattle deploy-final commit) with no manual input. The `packet`
step re-derived the same base on its own. No base or classification was supplied.

- AUTOMATIC BASE DERIVES = **YES**
- DERIVED BASE = `0e2e8bb8`
- CURRENT LIVE LINEAGE COMMIT = `f0003e78`

## 3. Source package and what was registered (Phases 3–5)

**Source package** `pkg-portland-or-b6f95c2ae170f44b`, `sha256:b6f95c2ae170f44b64f120f054cf07ef8ee48734d7ec2c6ee541882790eace5c`:

| | |
|---|---|
| status | SOURCE READY YES, COVERAGE READY YES, ACTIONABLE UNRESOLVED 0 |
| census | 272: PF 150, NP 47, resolved 197, unresolved 75 |
| FAST | 15/15; Rule J 908 files / 892 HTML; Rule K BYTE_IDENTICAL |
| reproducible | YES (in-process and independent) |
| receipt | `…-84acb4fb89e4e3df.json`, still eligible in its own shadow-receipt directory |
| safety | explicit-refusal PF 0, question-only PF 0, preopening 0, timeshare 0, misleading single fees 0 |

**Registered package** `pkg-portland-or-5b6016fb253bc7a7`, `sha256:5b6016fb253bc7a79ee20baf9099908db316cd95fff4ee3a97227684af905dfb`,
zone REGISTERED_LIVE:
- Field-for-field identical to `b6f95c2a`: census, PF and NP records, seed rows, partition, official routes, evidence
  references, unresolved rows and founder holds (the staging gate `package_identity` checks every field).
- It builds the **same bundle**, `f8a0a46d9ef67610…`.
- The id differs only because the zone, the source sha and the sealed_at differ.

**Held cohort (Phase 4):** all 75 unresolved rows are preserved as committed. No acquisition ran, no held row was
resolved, and `identity_resolutions.json` was **not** written. Checked on the built site, by the route the site forms:

| held item | profile | release-index route | served route |
|---|---|---|---|
| WorldMark Portland – Waterfront Park (vacation ownership, NON_LODGING) | absent | absent | absent |
| Hyatt House Portland Airport (SAME_CAMPUS) | absent | absent | absent |
| The Mindaro (SAME_CAMPUS) | absent | absent | absent |
| The Mindaro Part of JdV by Hyatt (bureau name-only sighting) | absent | absent | absent |

The other held rows publish nothing either: the two contradictory pages (The Dunes Motel, Hampton Inn Portland East),
the three affiliate-template rows (Cameo Motel, Portland INN, Bridgeway Inn) and all 75 unresolved rows are **0
published**. **UNAPPROVED PORTLAND PROFILES = 0.**

**Vancouver WA (Phase 5):** the `vancouver-wa` corridor is present and its corridor page builds. There are 34
Vancouver census rows, and 26 of them publish (21 pet-friendly, 5 no-pets). Every one keeps state WA and a 98xxx
postal code. No Oregon row carries any state but OR. **VANCOUVER WA WRONG-STATE IDENTITIES = 0.**

## 4. Canonical registration (Phase 6)

This is the ordinary composite fresh-market path, in Seattle's order.

1. **Repoint.** 15 market-local modules moved from the shadow zone to the registered zone. Only path constants
   changed: `identity_census_proposed/` → `identity_census/`, `markets/proposed/` → `markets/`, and staging
   `launch_package/` → the package root. The publication safety audit was split into a pure `audit()` function; its
   report is byte-identical.
2. **Promotion.** The census and market document were moved with `git mv` (R100).
   - The policy package, proposed authority and final partition were regenerated at the package root by their own
     writers.
   - **All five are byte-identical to the sealed copies** (policy `905f4bc7…` = the package's dependency digest).
3. **Authority shard.** `market_registration_cli --write` produced 150 seed rows and 47 exclusions, plus empty
   routing and affiliate shards. **All four are byte-identical to the sealed shard.**
4. **Globals.** `build_global_authority --write`, then `--check` clean:
   - exclusions 1,620 → **1,667** (+47, all portland-or);
   - seed rows 3,818 → **3,968** (+150, all portland-or);
   - **0 removed or modified.**
5. **Release contract.** `deploy/netlify/release_contracts/portland-or.json`, written by
   `portland_or_release_contract_002.py`:
   - fully derived through `release_contracts.derive_authority`, 0 disagreements;
   - `verify_all()`: **42 / 42** clean.
6. **`register`** (5.2 s):
   - participation 41 → 42 rows: portland-or added once at `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH`;
   - 0 rows removed, **0 existing rows changed**; the founder-authorized set is unchanged at 40;
   - the build closure gained exactly the release contract and the market document.
7. **`seal --work C:/t/pdx3a --work-order`** (217.7 s; detached):
   - package `5b6016fb`, reproducible YES;
   - FAST 15/15 in 149.0 s;
   - candidate 41 / 3,819 / 4,206, reproducible YES;
   - pin block: census 272 / PF 150 / NP 47 / corridor routes 11.
8. **Commit** `09850aa3`, then **`packet`** with no `--classification`.

**`packet` (automatic):** live source `f0003e78`, deploy `6ac169ef`, base `0e2e8bb8` (105.1 s; classification proof 100.4 s).

| | |
|---|---|
| classification_source | **AUTOMATIC** |
| CLASS | **COMPOSITE_FRESH_MARKET_DATA_ONLY** |
| ELIGIBLE | **YES**: 15/15 classifier checks PASS (change_set, market_local_zone, discovery_config, registration_input, identity_resolutions, participation, release_contract, build_closure, derived_globals, sealed_package, fast_receipt, expected_release, identity_routes, market_state_pin, release_integrity) |
| FULL_REGRESSION_REQUIRED | **NO** |
| REMOTE BROAD JOBS / BROAD REGRESSION RUNS | **0 / 0** |
| Change set | 108 paths: 34 market-local, 13 registration data, 61 derived; **0 shared, 0 unknown** |
| packet status | **AUTHORIZATION_READY**, founder AWAITING_FOUNDER_AUTHORIZATION |

The packet is `markets/reports/portland_or_registration_authorization_readiness.json`, and the classification is
beside it.

**expected_release.** The expected candidate digest (`6c5f8086…`, built from the live parent plus the sealed package)
and the actual digest (`b06600f1…`, built from the committed authority) differ by construction, as Seattle's did.
The check compares **complete sets**, and they agree: 41 / 3,819 / 4,206, with 0 unexpected changes.

## 5. Timer (Phase 7)

| | |
|---|---|
| REGISTER COMMAND TIME | 5.2 s |
| SEAL TIME | 217.7 s, of which FAST cold builds take 149.0 s and the live-parent read 66.8 s |
| PACKET TIME | 105.1 s (automatic classification proof 100.4 s) |
| GENERIC REGISTRATION-LANE TIME | **328.0 s ≈ 5 m 28 s** |
| TOTAL WALL CLOCK | **15 m 21 s** (02:59:59Z live check → 03:15:20Z packet) |

**≤ 5 minutes: MISSED by 28 s.** FAST's two cold builds alone take 2 m 29 s; without them the lane runs in 2 m 59 s.

**≤ 10 minutes:** the lane passes (5 m 28 s). The total wall clock (15 m 21 s) does not; the extra time went to the
repoint and to writing the two market-local modules (release contract, staging checks). There was no refusal, no
supplied classification, no factory repair, and no correction to the checks module after its first run.

## 6. Reader and fee safety (Phase 12)

Recorded in `markets/reports/portland_or_registration_checks_002.json` (`portland_or_registration_checks_002.py`).
Every check runs on the site the seal's own FAST build produced (`C:/t/pdx3a/oa/site`), over the registered root
documents, which are byte-identical to the sealed ones.

**Reader safety:**
- PET-FRIENDLY WITH EXPLICIT REFUSAL **0**; QUESTION-ONLY PET-FRIENDLY **0**; SERVICE-ANIMAL-ONLY ACCEPTANCE **0**;
- no-pets quote without a refusal 0;
- Rule C (shared first-party binding): **197 / 197** eligible.
- The shared reader was not modified.

**Fee safety:**
- **20** single-basis fees publish;
- **33** tiered fees are withheld;
- **20** unsafe single fees are withheld: basis not stated 13, stay-length condition 5, two bases 2;
- every one of the 53 withheld fee quotes was matched to its record (143 matches), and **0 publish a single fee**;
- **MISLEADING SINGLE FEES 0**.

## 7. Staging, accounting, delta, collisions (Phases 8–11, 13–16)

**Participation (Phase 8):** portland-or is `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH`, added once, by
reissue. All 40 live rows (plus withheld Detroit) are preserved, and 0 are changed.

**Parent (Phase 9):**
- PARENT LOOKUP PASS: the package parent is `6ac169ef`, current Seattle-live.
- PARENT ROUTES PRESERVED PASS: all 4,044 parent release-index routes are carried.

**Staging (Phase 10):**

| | |
|---|---|
| UNCHANGED BUNDLES REUSED | **40** (every live market's committed index entry is carried by identity) |
| UNCHANGED MARKETS REBUILT | **0** |
| PORTLAND BUNDLES BUILT | **1** (FAST's own two cold builds of the one bundle) |
| PHYSICAL FRAGMENTS RERENDERED | **0** (no whole-site assembly ran; the candidate was composed twice by the seal and agrees) |

**Projected accounting (Phase 11),** derived from candidate sets, not assumed:

| | |
|---|---:|
| PORTLAND PROJECTED PROFILES | **150** |
| PORTLAND RELEASE-INDEX ROUTES | **162** (150 hotels + 11 corridors + 1 hub) |
| PORTLAND SERVED ROUTES | **163** (the 162 plus its policy-comparison page, counted from the built sitemap) |
| CANDIDATE MARKETS | **41** |
| CANDIDATE PROFILES | **3,819** (3,669 + 150) |
| CANDIDATE RELEASE-INDEX ROUTES | **4,206** (4,044 + 162) |
| CANDIDATE SERVED ROUTES | **4,280** (4,117 + 163) |

**Delta safety (Phase 13):**
- UNEXPECTED MARKET, PROFILE and ROUTE DELTA: `[]`.
- Prior markets, profiles, release-index routes and served routes lost: 0.
- Portland is the only new market. `release_index.compare`: 0 findings.

**Cross-market safety (Phase 14):** CROSS-MARKET COLLISIONS 0, BARE-CHAIN COLLISIONS 0, DUPLICATE EXCLUDED
IDENTITIES 0, and 0 live properties moved or displaced.

**FAST receipt (Phase 15):**
- `pkg-portland-or-5b6016fb253bc7a7-df634e23cb809eb7.json` is **CURRENTLY ELIGIBLE**, the only receipt canonical
  selection returns.
- J PASS, NONEMPTY: 908 files / 892 HTML, bundle `f8a0a46d…` (not `e3b0c442`).
- K PASS: BYTE_IDENTICAL, 0 defects.

**Staging gates (Phase 16): 27 / 27 PASS.**

| gates | |
|---|---|
| package and lane | package identity, registration lane eligible, FAST receipt eligibility, FAST A–O |
| parent and preservation | parent lookup, parent routes, markets, profiles, routes, candidate delta |
| decision and safety | participation, founder-row reconciliation (0 dual-brand / 1 shared-reader / 0 preopening), held cohort, shared-campus hold, WorldMark absent, contradictory pages held, affiliate-template rows held, Vancouver WA safety, preopening, timeshare, military, reader, fee, collision |
| contracts and binding | first-party binding, release contracts |
| **deployment refusal** | **EXPECTED / PASS**: 0 deployment authorizations and 0 records name portland-or; not founder-authorized |

## 8. Live safety (Phase 17)

Re-verified after staging, at 03:16Z (`markets/reports/portland_or_registration_live_probe_002.json`):
- Live is still `6ac169ef`: 40 / 3,669 / 4,117, host verified.
- **Portland hub 404, and all 163 projected Portland routes 404.**
- Seattle, San Antonio, Austin, Phoenix, Denver, San Diego, Jacksonville FL, West Palm Beach, Fort Lauderdale and
  Augusta return **200**; Detroit **404**.

CURRENT LIVE MODIFIED = NO. No deploy, no deployment authorization, no founder authorization.

## 9. What the founder is now being asked to decide

Founder launch authorization of **`pkg-portland-or-5b6016fb253bc7a7`** only, bound to BUILD commit **`09850aa3`**.

**Expected effect:** +1 market / +150 profiles / +162 release-index routes / +163 served routes, giving
**41 / 3,819 / 4,206 / 4,280**.

**Held and not part of the decision:**
- the 75 unresolved rows: The Dunes Motel and Hampton Inn Portland East (contradictory pages), the three
  affiliate-template rows and the router-exhausted rest;
- the shared campus at 11707 NE Airport Way (Hyatt House Portland Airport, The Mindaro), which needs a
  `same_campus_distinct_entity` ruling this order did not write;
- WorldMark Portland – Waterfront Park and every other non-admitted census row.

The seal's scratch directory `C:/t/pdx3a` was removed after the checks report and the live probe were written. No
temporary process remains.

## FINAL ANSWERS

1. CURRENT LIVE DEPLOYMENT = 6ac169ef7c75c383eb79f824 (Seattle; lineage f0003e78, built_from 438348c7)
2. CURRENT LIVE MARKETS = 40
3. CURRENT LIVE PROFILES = 3669
4. CURRENT LIVE RELEASE-INDEX ROUTES = 4044
5. CURRENT LIVE SERVED ROUTES = 4117
6. PORTLAND SOURCE PACKAGE = pkg-portland-or-b6f95c2ae170f44b (sha256:b6f95c2ae170f44b64f120f054cf07ef8ee48734d7ec2c6ee541882790eace5c)
7. REGISTERED PORTLAND PACKAGE = pkg-portland-or-5b6016fb253bc7a7 (content identical to b6f95c2a; same bundle f8a0a46d…)
8. PACKAGE DIGEST = sha256:5b6016fb253bc7a79ee20baf9099908db316cd95fff4ee3a97227684af905dfb
9. AUTOMATIC BASE DERIVES = YES
10. DERIVED BASE = 0e2e8bb89809c0a7929765089680f29453005a75
11. REGISTRATION CLASS = COMPOSITE_FRESH_MARKET_DATA_ONLY
12. AUTOMATIC CLASSIFICATION = YES (classification_source AUTOMATIC)
13. CLASSIFIER CHECKS = 15/15 PASS
14. ELIGIBLE = YES
15. FULL_REGRESSION_REQUIRED = NO
16. REGISTER COMMAND TIME = 5.2 s
17. SEAL TIME = 217.7 s (FAST cold builds 149.0 s; live-parent read 66.8 s)
18. PACKET TIME = 105.1 s (automatic classification proof 100.4 s)
19. GENERIC REGISTRATION-LANE TIME = 328.0 s (5 m 28 s)
20. <=5M TARGET = MISSED by 28 s (without FAST cold builds 2 m 59 s)
21. <=10M HARD LIMIT = lane PASS (5 m 28 s); total wall clock 15 m 21 s exceeds it (repoint + module writing, no refusal)
22. BROAD REGRESSION RUNS = 0
23. SHARED PATHS = 0
24. UNKNOWN PATHS = 0
25. PARENT LOOKUP = PASS
26. PARENT ROUTES PRESERVED = PASS
27. UNCHANGED BUNDLES REUSED = 40
28. UNCHANGED MARKETS REBUILT = 0
29. PHYSICAL FRAGMENTS RERENDERED = 0
30. PORTLAND BUNDLES BUILT = 1
31. PORTLAND PROJECTED PROFILES = 150
32. PORTLAND RELEASE-INDEX ROUTES = 162
33. PORTLAND SERVED ROUTES = 163
34. CANDIDATE MARKETS = 41
35. CANDIDATE PROFILES = 3819
36. CANDIDATE RELEASE-INDEX ROUTES = 4206
37. CANDIDATE SERVED ROUTES = 4280
38. APPROVED PORTLAND PROFILES = 150
39. UNAPPROVED PORTLAND PROFILES = 0
40. WORLDMARK PORTLAND PUBLISHED = 0 (profile, release-index route and served route absent)
41. SHARED-CAMPUS HOLDS PUBLISHED = 0 (Hyatt House Portland Airport and The Mindaro absent)
42. VANCOUVER WA CORRIDOR PRESENT = YES
43. VANCOUVER WA WRONG-STATE IDENTITIES = 0
44. PET-FRIENDLY WITH EXPLICIT REFUSAL = 0
45. QUESTION-ONLY PET-FRIENDLY = 0
46. MISLEADING SINGLE FEES = 0
47. CROSS-MARKET COLLISIONS = 0 (bare-chain 0, duplicate excluded identities 0)
48. FAST RECEIPT CURRENTLY ELIGIBLE = YES (pkg-portland-or-5b6016fb253bc7a7-df634e23cb809eb7.json)
49. RULE J NONEMPTY = PASS (908 files / 892 HTML, bundle f8a0a46d…)
50. RULE K NONVACUOUS = PASS (BYTE_IDENTICAL)
51. ALL STAGING GATES = PASS (27/27)
52. DEPLOYMENT REFUSAL = EXPECTED / PASS
53. CURRENT LIVE MODIFIED = NO
54. DEPLOYMENT PERFORMED = NO
55. PORTLAND LIVE = NO (hub + 163 routes 404)
56. origin == HEAD = YES (verified after push)
57. tree clean = YES (verified after push)
58. READY FOR FOUNDER LAUNCH AUTHORIZATION = YES (packet AUTHORIZATION_READY; authorize pkg-portland-or-5b6016fb253bc7a7 only, bound to 09850aa3)

```
PORTLAND REGISTRATION = PASS
PORTLAND STAGING = PASS
AUTOMATIC BASE DERIVES = YES
FULL_REGRESSION_REQUIRED = NO
BROAD REGRESSION RUNS = 0
PET-FRIENDLY RECORDS WITH EXPLICIT REFUSAL = 0
QUESTION-ONLY PET-FRIENDLY RECORDS = 0
UNAPPROVED PORTLAND PROFILES = 0
MISLEADING SINGLE FEES = 0
UNCHANGED MARKETS REBUILT = 0
CURRENT LIVE MODIFIED = NO
PORTLAND DEPLOYED = NO
READY FOR FOUNDER LAUNCH AUTHORIZATION = YES
```
