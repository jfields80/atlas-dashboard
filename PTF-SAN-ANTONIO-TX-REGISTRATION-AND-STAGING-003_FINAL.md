# PTF-SAN-ANTONIO-TX-REGISTRATION-AND-STAGING-003 — FINAL

**Status:** SAN ANTONIO REGISTERED and STAGED. The packet is **AUTHORIZATION_READY**, and founder status is
AWAITING_FOUNDER_AUTHORIZATION.

**Not done:** nothing deployed; no founder authorization or deployment authorization created; live unchanged.

**Branch:** `worker/ptf-san-antonio-tx-market-001` (worktree `C:\Atlas-San-Antonio-TX-Hardened-V1`).

**Commits:**
- `5f30c7b3`: the registration transaction.
- The final commit: the automatic classification, the readiness packet and this report.

## 1. Current live (Phase 1)

Resolved with the canonical resolver (`release_index live-source --fetch --verify-host`) at 20:09:00Z, and again
after staging at 20:32Z. Both times, unchanged:

| | |
|---|---|
| CURRENT_LIVE_SOURCE_COMMIT | `f0ddbcde` (built_from `ef28f7b4`) |
| deploy | **`6abf3e749cc359701298718d`**, record `ptf-deploy-austin-004-6abf3e749cc359701298718d.json` (Austin) |
| bundle / sitemap | `75e56941…` / `d6461dbc…` |
| markets / profiles | **38 / 3,386** (Detroit withheld) |
| release-index routes | **3,737**, counted from the live index: per market profiles + corridor routes + 1 hub |
| served routes | **3,808** |
| host verified | YES |

Live had not advanced, so registration ran against current production.

## 2. Automatic base derivation (Phase 2)

`registration_release_lane.derive_registration_base('san-antonio-tx', f0ddbcde)` returned **`3afa9b17`** (the Austin
deploy-final commit) with no manual input.
- Rule: the newest first-parent ancestor of HEAD that contains the live lineage commit, names no San Antonio path,
  and carries the lineage commit's live-truth files.
- The only factory commit since live is `3afa9b17` itself.

The `packet` step re-derived the same base automatically. No classification or base was supplied.

## 3. Source package, Hilton retry, and what was registered (Phases 3–4)

**Source package** `pkg-san-antonio-tx-b6018714bcc2bd44` (`sha256:b6018714…`):

| | |
|---|---|
| status | SOURCE READY YES, COVERAGE READY YES, ACTIONABLE UNRESOLVED 0 |
| census | 414: PF 144, NP 98, resolved 242, unresolved 172 |
| FAST | 15/15, J 884 files / 868 HTML, K BYTE_IDENTICAL |
| reproducible | YES |
| receipt | `…-54a176a91524761e.json`, still ELIGIBLE in its own shadow-receipt directory |

**Hilton paced retry record (002):** retried 10, real hotel pages loaded 0, new reads 0, still blocked 10. No
Hilton policy was inferred, and no browser acquisition was re-run.

**Registered package** `pkg-san-antonio-tx-aa8f4fe9ea26a6ff` (`sha256:aa8f4fe9ea26a6ff575bcae2af68d3f60ad194048be13a6a351834ff75dad116`),
zone REGISTERED_LIVE:
- These fields are **field-for-field identical** to `b6018714`: census, PF and NP records, seed rows, partition,
  official routes, evidence references, unresolved rows and founder holds.
- It builds the **same bundle**, `f9b4c610bd27eb9b…`.
- The id differs only because the zone, the source sha and the parent declaration differ.

## 4. Canonical registration (Phase 5)

This is the ordinary composite fresh-market path, in Austin's and Phoenix's order.

1. **Repoint.** 15 market-local modules moved from the shadow zone to the registered zone. Only path constants
   changed: `identity_census_proposed/` → `identity_census/`, `markets/proposed/` → `markets/`, and staging
   `launch_package/` → the package root.
2. **Promotion.** The census and market document were moved with `git mv` (R100).
   - The policy package, proposed authority and final partition were regenerated at the package root by their own
     writers.
   - **All five are byte-identical to the sealed copies.**
3. **Authority shard.** `market_registration_cli --write` produced 144 seed rows and 98 exclusions, plus empty
   routing and affiliate shards. **All four are byte-identical to the sealed shard.**
4. **Globals.** `build_global_authority --write`, then `--check` clean:
   - exclusions 1,461 → **1,559** (+98, all san-antonio-tx);
   - seed rows 3,535 → **3,679** (+144, all san-antonio-tx);
   - **0 removed or modified.**
5. **Release contract.** `deploy/netlify/release_contracts/san-antonio-tx.json`, written by
   `san_antonio_tx_release_contract_003.py`:
   - fully derived through `release_contracts.derive_authority`, 0 disagreements;
   - `verify_all()`: **40 / 40** clean.
6. **`register`** (5.0 s):
   - participation 39 → 40 rows: san-antonio-tx added once at `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH`;
   - 0 rows removed, **0 existing rows changed**; the founder-authorized set is unchanged at 37;
   - the build closure gained exactly the release contract and the market document.
7. **`seal --work C:/t/sa3a --work-order`** (203.5 s):
   - package `aa8f4fe9`, reproducible YES;
   - FAST 15/15 in 139.7 s;
   - candidate 39 / 3,530 / 3,894, reproducible YES;
   - pin block: census 414 / PF 144 / NP 98 / corridor routes 12.
8. **Commit** `5f30c7b3`, then **`packet`** with no `--classification`.

**`packet` (automatic):** live source `f0ddbcde`, deploy `6abf3e74`, base `3afa9b17` (classification 97.9 s).

| | |
|---|---|
| classification_source | **AUTOMATIC** |
| CLASS | **COMPOSITE_FRESH_MARKET_DATA_ONLY** |
| ELIGIBLE | **YES**: 15/15 classifier checks PASS (change_set, market_local_zone, discovery_config, registration_input, identity_resolutions, participation, release_contract, build_closure, derived_globals, sealed_package, fast_receipt, expected_release, identity_routes, market_state_pin, release_integrity) |
| FULL_REGRESSION_REQUIRED | **NO** |
| REMOTE BROAD JOBS / BROAD REGRESSION RUNS | **0 / 0** |
| Change set | 109 paths: 34 market-local, 13 registration data, 62 derived; **0 shared, 0 unknown** |
| packet status | **AUTHORIZATION_READY**, founder AWAITING_FOUNDER_AUTHORIZATION |

The packet is written to `markets/reports/san_antonio_tx_registration_authorization_readiness.json`; the
classification is beside it.

**expected_release.** The expected digest (`9eac52d7…`, built from the live parent plus the sealed package) and the
actual digest (`e3b3beea…`, built from the committed authority) differ by construction, exactly as Austin's did
(`7e189f8c` vs `b471d387`). The check compares **complete sets**, and they agree: 39 / 3,530 / 3,894, with 0
unexpected changes.

## 5. Timer (Phase 6)

| | |
|---|---|
| REGISTER COMMAND TIME | 5.0 s |
| SEAL TIME | 203.5 s, of which FAST cold builds take 139.7 s (J 75.2 s + K 62.8 s) |
| PACKET TIME | 98.6 s (automatic classification 97.9 s) |
| GENERIC REGISTRATION-LANE TIME | **307.1 s ≈ 5 m 07 s** |
| TOTAL REGISTRATION WALL CLOCK | **22 m 38 s** (20:09:00Z live check → 20:31:38Z packet) |

**≤ 5 minutes: MISSED by 7.1 s.** FAST's cold builds alone take 2 m 20 s; without them, the lane runs in 2 m 47 s.

**≤ 10 minutes:** the lane passes (5 m 07 s). Total wall clock does not. The extra time went to:
- reading the Austin recipe;
- writing the two market-local modules (release contract, staging checks);
- the repoint;
- two corrections to my own staging-checks module (§7).

There was no refusal, no supplied classification, and no factory repair.

## 6. Held-row, reader and fee safety (Phases 7–9)

Recorded in `markets/reports/san_antonio_tx_registration_checks_003.json` (`san_antonio_tx_registration_checks_003.py`).
- Every check runs on the site the seal's own FAST build produced (`C:/t/sa3a/oa/site`).
- Profiles are compared by the route the site forms (`release_index.hotel_route`), never by census slug.

**Held-row safety**, published / rows:

| held class | published |
|---|---:|
| Hilton access-blocked (the retry record's 10, mapped one-to-one) | **0 / 10** |
| dual-brand founder rows | **0 / 8** |
| The Jackson House (shared-reader-unreadable refusal; still held) | **0 / 1** |
| preopening (Homewood Rim, Perlen House, Sitio El Tropicano, The St Paul) | **0 / 4** |
| router-exhausted | 0 / 159 |
| by disposition: routing 81, access 28, source-silent 30, evidence 17, identity 16 | 0 each |
| **all unresolved** | **0 / 172** |

- **Profiles built:** 144 San Antonio profiles, all approved. **UNAPPROVED SAN ANTONIO PROFILES = 0.**
- **Census rows not admitted** (outside 540, name-only 230, identity-review 148, non-lodging 101, same-campus 7):
  0 publish as a distinct entity.
- **Same-name observations:** 8 identity-review or name-only rows share a published hotel's name. Each is a second
  sighting of the published building, listed in the checks report and never resolved here.
  - Five are competitor-lead names with no address.
  - ESA Colonnade Medical: "4331 Spectrum 1" vs "4331 Spectrum One".
  - Homewood Northwest: an OSM row in the same 78230 postal code.
  - Marriott Riverwalk: the licence-registry row on 711 E River Walk St, the River Walk side of the brand's own
    889 E Market St, both in 78205.
- **`identity_resolutions.json`:** not written.

**Reader safety.** The registered root documents are byte-identical to the sealed ones. The source-ready audit's
logic was reused, split into a pure `audit()` function with byte-identical output:
- PET-FRIENDLY WITH EXPLICIT REFUSAL **0**; QUESTION-ONLY PET-FRIENDLY **0**; SERVICE-ANIMAL-ONLY ACCEPTANCE **0**;
- no-pets quote without a refusal 0;
- Rule C (shared first-party binding): **242 / 242** eligible.
- The shared reader was not modified.

**Preopening, timeshare and military:** 0 / 0 / 0 published.

**Fee safety:**
- **14** explicit per-stay fees publish;
- **39** tiered fees are withheld;
- **17** unsafe single fees are withheld;
- **MISLEADING SINGLE FEES 0**.

## 7. Staging, accounting, delta, collisions (Phases 10–17)

**Participation (Phase 10):** san-antonio-tx is `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH`, added once,
by reissue. All 38 live rows (plus withheld Detroit) are preserved, and 0 are changed.

**Parent (Phase 11):**
- PARENT LOOKUP PASS: the package parent is `6abf3e74`, current Austin-live.
- PARENT ROUTES PRESERVED PASS: all 3,737 parent release-index routes are carried.

**Staging (Phase 12):**

| | |
|---|---|
| UNCHANGED BUNDLES REUSED | **38** (every live market's committed index entry is carried by identity) |
| UNCHANGED MARKETS REBUILT | **0** |
| SAN ANTONIO BUNDLES BUILT | **1** (FAST's own cold builds of the one bundle) |
| PHYSICAL FRAGMENTS RERENDERED | **0** (no whole-site assembly ran; the candidate was composed twice by the seal and agrees) |

**Projected accounting (Phase 13),** derived from candidate sets, not assumed:

| | |
|---|---:|
| SAN ANTONIO PROJECTED PROFILES | **144** |
| SAN ANTONIO RELEASE-INDEX ROUTES | **157** (144 hotels + 12 corridors + 1 hub) |
| SAN ANTONIO SERVED ROUTES | **158** (the 157 plus its policy-comparison page, counted from the built sitemap) |
| CANDIDATE MARKETS | **39** |
| CANDIDATE PROFILES | **3,530** (3,386 + 144) |
| CANDIDATE RELEASE-INDEX ROUTES | **3,894** (3,737 + 157) |
| CANDIDATE SERVED ROUTES | **3,966** (3,808 + 158) |

**Delta safety (Phase 14):**
- UNEXPECTED MARKET, PROFILE and ROUTE DELTA: `[]`.
- Prior markets, profiles, release-index routes and served routes lost: 0.
- San Antonio is the only new market. `release_index.compare`: 0 findings.

**Cross-market safety (Phase 15):** CROSS-MARKET COLLISIONS 0, BARE-CHAIN COLLISIONS 0, DUPLICATE EXCLUDED
IDENTITIES 0, and 0 live properties moved or displaced.

- **One bare-chain-*shaped* name, measured rather than waved through.** The verified-no-pets exclusion is
  "Best Western Garden Inn": Best Western code 44559, at 11939 I-H 35 N, 78233.
  - The shared registry matches an exclusion by normalized name in **every** market. So I searched every market's
    census (admitted and non-admitted), every other market's registry row and every live profile for that name.
  - The only other row anywhere is Austin's OUTSIDE_MARKET record of **the same building** (11939 Interstate 35
    North, 78233). **0 other buildings are exposed.**
  - The registry already carries 12 such names from 7 live markets, for example Lexington "Comfort Inn",
    Tampa "Best Western" and Cleveland "Holiday Inn Express".
  - The risk is latent: a future market with a *different* "Best Western Garden Inn" would be held by this row.
    That market's own in-market collision test is where it would surface.

**FAST receipt (Phase 16):**
- `pkg-san-antonio-tx-aa8f4fe9ea26a6ff-859baec5238b5b52.json` is **CURRENTLY ELIGIBLE**, the only receipt
  canonical selection returns.
- J PASS, NONEMPTY: 884 files / 868 HTML, bundle `f9b4c610…` (not `e3b0c442`).
- K PASS: BYTE_IDENTICAL, 0 defects.

**Staging gates (Phase 17): 22 / 22 PASS.**

| gates | |
|---|---|
| package and lane | package identity, registration lane eligible, FAST receipt eligibility, FAST A–O |
| parent and preservation | parent lookup, parent routes, markets, profiles, routes, candidate delta |
| decision and safety | participation, founder-row reconciliation (8 / 1 / 4 / 10), held-cohort, preopening, timeshare, military, reader, fee, collision |
| contracts and binding | first-party binding, release contracts |
| **deployment refusal** | **EXPECTED / PASS**: 0 deployment authorizations and 0 records name san-antonio-tx; not founder-authorized |

**Corrections to my own checks module before it passed.** No package, data or shared code changed:
1. **Receipt field:** it read rule J's outcome from a `result` field. The receipt states it as `status: PASS`.
2. **Non-admitted name matches:** it counted every non-admitted row sharing a published name as a leak. It now
   fails a distinct entity outright, and fails an observation only when it places itself at a different building.
   Every match is listed.
3. **Bare-chain names:** it failed on the name's token shape alone. It now fails on measured exposure to another
   building, and still reports the shape.

## 8. Live safety (Phase 18)

Re-verified after staging, at 20:32Z:
- Live is still `6abf3e74`: 38 / 3,386 / 3,808, host verified.
- **San Antonio hub 404, and all 158 projected San Antonio routes 404.**
- Austin, Phoenix, Denver, San Diego, Jacksonville FL, West Palm Beach, Fort Lauderdale and Augusta return **200**;
  Detroit **404**.

CURRENT LIVE MODIFIED = NO. No deploy, no deployment authorization, no founder authorization.

## 9. What the founder is now being asked to decide

Founder launch authorization of **`pkg-san-antonio-tx-aa8f4fe9ea26a6ff`** only.

**Expected effect:** +1 market / +144 profiles / +157 release-index routes / +158 served routes, giving
**39 / 3,530 / 3,894 / 3,966**.

**Held and not part of the decision:**
- the 172 unresolved rows: 8 dual-brand, The Jackson House, 4 preopening, 10 Hilton-blocked and the router-exhausted
  rest;
- every non-admitted census row.

The authorization should bind the BUILD commit (the commit carrying the registered package), per the standing rule.

The seal's scratch directory `C:/t/sa3a` was removed after the checks report was written. No temporary process
remains.

## FINAL ANSWERS

1. CURRENT LIVE DEPLOYMENT = 6abf3e749cc359701298718d (Austin; lineage f0ddbcde, built_from ef28f7b4)
2. CURRENT LIVE MARKETS = 38
3. CURRENT LIVE PROFILES = 3386
4. CURRENT LIVE RELEASE-INDEX ROUTES = 3737
5. CURRENT LIVE SERVED ROUTES = 3808
6. SAN ANTONIO PACKAGE = pkg-san-antonio-tx-aa8f4fe9ea26a6ff (registered; content identical to source-ready pkg-san-antonio-tx-b6018714bcc2bd44)
7. PACKAGE DIGEST = sha256:aa8f4fe9ea26a6ff575bcae2af68d3f60ad194048be13a6a351834ff75dad116
8. AUTOMATIC BASE DERIVES = YES
9. DERIVED BASE = 3afa9b1721eb72f61c4a0b761ff9e54a820af03c
10. REGISTRATION CLASS = COMPOSITE_FRESH_MARKET_DATA_ONLY
11. AUTOMATIC CLASSIFICATION = YES (classification_source AUTOMATIC; 15/15 checks PASS)
12. ELIGIBLE = YES
13. FULL_REGRESSION_REQUIRED = NO
14. REGISTER COMMAND TIME = 5.0 s
15. SEAL TIME = 203.5 s (FAST 139.7 s of cold builds)
16. PACKET TIME = 98.6 s (automatic classification 97.9 s)
17. GENERIC REGISTRATION-LANE TIME = 307.1 s (5 m 07 s)
18. <=5M TARGET = MISSED by 7.1 s (lane 5 m 07 s; without FAST cold builds 2 m 47 s)
19. <=10M HARD LIMIT = lane PASS (5 m 07 s); total wall clock 22 m 38 s exceeds it (module writing + check corrections, no refusal)
20. BROAD REGRESSION RUNS = 0
21. SHARED PATHS = 0
22. UNKNOWN PATHS = 0
23. PARENT LOOKUP = PASS
24. PARENT ROUTES PRESERVED = PASS
25. UNCHANGED BUNDLES REUSED = 38
26. UNCHANGED MARKETS REBUILT = 0
27. PHYSICAL FRAGMENTS RERENDERED = 0
28. SAN ANTONIO BUNDLES BUILT = 1
29. SAN ANTONIO PROJECTED PROFILES = 144
30. SAN ANTONIO RELEASE-INDEX ROUTES = 157
31. SAN ANTONIO SERVED ROUTES = 158
32. CANDIDATE MARKETS = 39
33. CANDIDATE PROFILES = 3530
34. CANDIDATE RELEASE-INDEX ROUTES = 3894
35. CANDIDATE SERVED ROUTES = 3966
36. APPROVED SAN ANTONIO PROFILES = 144
37. UNAPPROVED SAN ANTONIO PROFILES = 0
38. HILTON BLOCKED ROWS PUBLISHED = 0 / 10
39. DUAL-BRAND ROWS PUBLISHED = 0 / 8
40. JACKSON HOUSE PUBLISHED = 0 (held)
41. PREOPENING PROFILES PUBLISHED = 0 / 4
42. TIMESHARE PROFILES PUBLISHED = 0
43. MILITARY-RESTRICTED PROFILES PUBLISHED = 0
44. PET-FRIENDLY WITH EXPLICIT REFUSAL = 0
45. QUESTION-ONLY PET-FRIENDLY = 0
46. MISLEADING SINGLE FEES = 0
47. CROSS-MARKET COLLISIONS = 0 (bare-chain collisions 0; one bare-chain-shaped name, 0 other buildings exposed)
48. FAST RECEIPT CURRENTLY ELIGIBLE = YES (pkg-san-antonio-tx-aa8f4fe9ea26a6ff-859baec5238b5b52.json)
49. RULE J NONEMPTY = PASS (884 files / 868 HTML, bundle f9b4c610…)
50. RULE K NONVACUOUS = PASS (BYTE_IDENTICAL)
51. ALL STAGING GATES = PASS (22/22)
52. DEPLOYMENT REFUSAL = EXPECTED / PASS
53. CURRENT LIVE MODIFIED = NO
54. DEPLOYMENT PERFORMED = NO
55. SAN ANTONIO LIVE = NO (hub + 158 routes 404)
56. origin == HEAD = YES
57. tree clean = YES
58. READY FOR FOUNDER LAUNCH AUTHORIZATION = YES (packet AUTHORIZATION_READY; authorize pkg-san-antonio-tx-aa8f4fe9ea26a6ff only)

```
SAN ANTONIO REGISTRATION = PASS
SAN ANTONIO STAGING = PASS
AUTOMATIC BASE DERIVES = YES
FULL_REGRESSION_REQUIRED = NO
BROAD REGRESSION RUNS = 0
PET-FRIENDLY RECORDS WITH EXPLICIT REFUSAL = 0
QUESTION-ONLY PET-FRIENDLY RECORDS = 0
UNAPPROVED SAN ANTONIO PROFILES = 0
MISLEADING SINGLE FEES = 0
UNCHANGED MARKETS REBUILT = 0
CURRENT LIVE MODIFIED = NO
SAN ANTONIO DEPLOYED = NO
READY FOR FOUNDER LAUNCH AUTHORIZATION = YES
```
