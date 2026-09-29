# PTF-PHOENIX-AZ-FOUNDER-LAUNCH-AUTHORIZATION-004 — FINAL

`phoenix-az` (Phoenix / Scottsdale / Valley of the Sun, Arizona) is **FOUNDER_AUTHORIZED_FOR_LAUNCH** on the corrected
package **`pkg-phoenix-az-07f7e75699af6a8c`**, exactly as the founder decided in this work order:

> Authorize ONLY the corrected Phoenix package: pkg-phoenix-az-07f7e75699af6a8c
> Do NOT authorize any earlier Phoenix package.

**The candidate.** The exact authorized production candidate is built. Two sequential whole-site assemblies are
byte-identical. It is bound to deployment authorization **`ptf-auth-phoenix-004-19234b7affec`**, which is **AUTHORIZED and UNCONSUMED**.

**The refused packages.** Neither earlier Phoenix package is authorized: the superseded 63-no-pets registered
package `pkg-phoenix-az-85ad9b66` and the source-ready shadow package `pkg-phoenix-az-865822f4` (never registered).
Every writer in this order refuses unless the readiness packet binds `07f7e756`.

**Not deployed.** There was no Netlify invocation, no deployment record and no LIVE flag, and the authorization is not
consumed. Current live is untouched, and the live `global_deployment_manifest.json` was not written. There was no
acquisition, no broad regression, no spend, no Places, no `identity_resolutions.json` write, and no invented
identity, route or domain.

Commits: `63e410ff` founder decision (committed **before** the whole-site build), then the candidate, authorization
and this report.

---

## 1. Current live (verified at start 18:52:40Z and at end 21:52:02Z)

`release_index live-source --verify-host`:

| | |
|---|---|
| CURRENT LIVE SOURCE COMMIT | `edf11b7a413903183cc59f4204de6066e93b52cf` (built_from `5bc62502`) |
| CURRENT LIVE DEPLOYMENT | `6aba7587ddcc33a192bdf694` (Denver), deployment record `ptf-deploy-denver-005-6aba7587ddcc33a192bdf694.json` |
| CURRENT LIVE BUNDLE / SITEMAP | `7d3471c79e2d…ee338a` / `5d3d07a4c965…712a2c` |
| MARKETS / PROFILES / RELEASE-INDEX / SERVED | **36 / 2,954 / 3,274 / 3,343** |
| HOST VERIFIED | true |

Live has not advanced since Phoenix's re-registration: the readiness packet binds parent `6aba7587…`, the current
live deploy. The live bytes compared against below are Denver's authorized live artifact `C:\t\den4a` (bundle
`7d3471c7…`, sitemap `5d3d07a4…`, 17,904 files).

## 2. Corrected package (nothing re-derived)

| | |
|---|---|
| PACKAGE | `pkg-phoenix-az-07f7e75699af6a8c` (`sha256:07f7e75699af6a8cefe5f083b688f647c55190f04aae0cd0617292968ab0fccf`) |
| NOT the prior package | the readiness packet binds `07f7e756`; `85ad9b66` and `865822f4` are refused by every writer |
| READINESS | AUTHORIZATION_READY, COMPOSITE_FRESH_MARKET_DATA_ONLY 15/15, ELIGIBLE YES, FULL_REGRESSION_REQUIRED NO |
| COHORT | 484 census / **256 pet-friendly** / 59 verified no-pets / 315 resolved / 169 unresolved / actionable 0 |
| COVERAGE | YES by founder decision (`phoenix_az_founder_coverage_decision_003.json`); source ready YES |
| FAST | 15/15; J 1,553 files / 1,537 HTML, output present, bundle `ea2a8d31…`; K BYTE_IDENTICAL |
| REPRODUCIBLE | YES (correction 003's independent reproduction) |

## 3. Vacation-ownership safety (committed state and the built artifact)

| property | hotel profile | NP hotel exclusion | index route | served route | /go/ | files naming it | census |
|---|---|---|---|---|---|---:|---|
| Club Wyndham Legacy Golf Resort | NO | NO | NO | NO | NO | 0 | NON_LODGING / TIMESHARE |
| Club Wyndham Orange Tree Resort | NO | NO | NO | NO | NO | 0 | NON_LODGING / TIMESHARE |
| WorldMark Phoenix - South Mountain Preserve | NO | NO | NO | NO | NO | 0 | NON_LODGING / TIMESHARE |
| WorldMark Scottsdale | NO | NO | NO | NO | NO | 0 | NON_LODGING / TIMESHARE |

The four are also absent from the policy package and from the global exclusion registry. The founder-decision module
refuses to write if any of them returns to hotel inventory. The candidate-accounting gate scanned every page,
sitemap and text file of the built candidate for their names: 19,421 files, 0 mentions.

## 4. Founder authorization (participation)

The decision was written by `phoenix_az_launch_participation_004.py`, which calls
`launch_participation.extend_decision`. The chain was extended, not rebuilt.

| | |
|---|---|
| FOUNDER AUTHORIZATION | recorded in `deploy/netlify/launch_participation.json`, decision `work_order` PTF-PHOENIX-AZ-FOUNDER-LAUNCH-AUTHORIZATION-004, commit `63e410ff` |
| AUTHORIZED MARKET | `phoenix-az` |
| AUTHORIZED PACKAGE / DIGEST | `pkg-phoenix-az-07f7e75699af6a8c` / `sha256:07f7e756…0fccf` |
| AUTHORIZED SOURCE COMMIT | `63e410ff` (the committed tree both candidate builds assembled from; its readiness packet was produced on `d6fba323`) |
| AUTHORIZED PARENT | deploy `6aba7587ddcc33a192bdf694`, release-index digest `sha256:fb99d3b6…62fe62` |
| DECISION BASIS | `decision_basis`, derived at run time from the committed census, package, shard, contract, partition, actionability, clean authority, coverage decision 003, vacation-ownership evidence, readiness packet and FAST receipt (every document by path + sha256) |
| phoenix-az | `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH` → **`FOUNDER_AUTHORIZED_FOR_LAUNCH`** (not live) |
| decided_by / decided_on | `founder` / 2026-09-29. The founder's own words are transcribed; no person's name is signed |
| AUTHORIZED SET | 36 → **37**, gained **phoenix-az only**, lost none |
| OTHER ROWS CHANGED | **0** (38 rows); Detroit stays SOURCE_READY and is excluded |
| DECISION PROBLEMS | `[]`; lineage 42 records; supersedes the correction-003 registration decision |
| FIRST AUTHORIZATION | yes: no `founder_authorization_superseded` entry exists or was written |

**Guards.** Each founder statement is a guard that refuses to write unless committed state agrees:

- **Package:** `07f7e756`, never `85ad9b66` or `865822f4`.
- **Cohort:** exactly 256 / 59.
- **Held groups:** each matches its count and publishes nothing.
  - 48 Places-gated
  - 30 founder: 14 dual-brand address keys × 2 rows, plus the 2 route-domain rows
  - 88 router-exhausted / evidence / source-silent
  - 3 preopening, held by the clean-authority preopening rule
- **Vacation ownership:** the four resorts are outside hotel inventory (TIMESHARE).
- **Fees:** 0 flattened fees. 113 published records quote more than one amount, and none publishes a single fee.
- **Status:** actionable 0, coverage YES, source ready YES.

## 5. The exact authorized candidate

`assemble_production_site` ran on the committed tree `63e410ff`. Build A: `--output C:/t/phx4a` (started 18:55:08Z,
manifests 20:13:38Z). Build B: `--output C:/t/phx4b` (started 20:16:04Z, after A was gone; manifests 21:40:52Z).

| | |
|---|---|
| AUTHORIZED CANDIDATE BUNDLE | **`19234b7affec61c16d6ac40e864e83a4c497262b2451eba2d03821482e9a1f78`** |
| AUTHORIZED CANDIDATE SITEMAP | **`647596dca769c1b82c94e1c512ab04d87bbe729c07c1d06a49c2e11e5c652ecb`** |
| total files / HTML pages | 19,436 / 19,418 |
| all gates pass | **true** (27 gates; 0 broken links, 0 collisions, 0 canonical violations) |
| markets included / excluded | 37 / Detroit |
| PARENT LOOKUP / PARENT ROUTES PRESERVED | **PASS / PASS** (3,274 / 3,274 live index routes and 3,343 / 3,343 live served routes carried) |

| Release-factory accounting | |
|---|---:|
| **UNCHANGED BUNDLES REUSED** | **36** (every live market's index entry carried unchanged) |
| **UNCHANGED MARKETS REBUILT** | **0** |
| **PHOENIX BUNDLES BUILT** | **1** |
| **PHYSICAL FRAGMENTS RERENDERED** | **37**, reported separately. No release store is populated here, so the composer physically rendered every fragment; this is **not** reuse. The count comes from the bundle manifest's `fragments`, because the hung process's log was not fully flushed |

**The known assembler hang was handled as documented.**

- Build A wrote both manifests and its work tree was already removed.
- CPU fell to 0.9 s over 30 s, and the manifests hashed identically over 75 s.
- Only then was PID 18236 terminated.
- Build B behaved the same way: CPU fell to 1.0 s over 30 s and the manifests were stable. Only then was PID 12776 terminated.
- Build B started only after build A was gone.

## 6. Candidate determinism

| | |
|---|---|
| builds | 2, sequential (never concurrent), separate short absolute work dirs `C:/t/phx4a`, `C:/t/phx4b` |
| both non-empty | YES: 19,436 files / 19,418 HTML each; all_gates_pass true in both |
| bundle / sitemap | `19234b7a…` = `19234b7a…` / `647596dc…` = `647596dc…`; `global_bundle_manifest.json` `6c9b6a03…` and `file_hash_manifest.json` `38987e17…` byte-identical in both |
| FILES COMPARED / DIFFERING | **19,436 / 0** |
| RESULT | **BYTE_IDENTICAL** |

## 7. Route and profile accounting (as sets, from the artifacts)

| | live | Phoenix | candidate |
|---|---:|---:|---:|
| MARKETS | 36 | **+1** | **37** |
| PROFILES | 2,954 | **+256** | **3,210** |
| RELEASE-INDEX ROUTES | 3,274 | **+275** (256 hotel + 18 corridor + 1 hub) | **3,549** |
| SERVED SITEMAP ROUTES | 3,343 | **+276** (275 + `/pet-friendly-hotels/phoenix-az/policy-comparison/`) | **3,619** |

- **Served routes:** the candidate minus live is 276 routes added, all Phoenix's. 0 are foreign and 0 prior served
  routes were lost.
- **Corridors:** 18 publish. The 8 below their publication minimum were not forced.

## 8. Publication cohort safety (on the BUILT artifact)

Every held row was resolved to its census slug and checked in `C:/t/phx4a` for a profile page, a sitemap route, a
release-index route and a `/go/` file.

| group | rows | slugs resolved | pages | sitemap | index | /go/ |
|---|---:|---:|---:|---:|---:|---:|
| Places-gated | 48 | 48 | 0 | 0 | 0 | 0 |
| founder-decision (28 dual-brand + 2 route-domain) | 30 | 30 | 0 | 0 | 0 | 0 |
| router-exhausted / evidence / source-silent | 88 | 88 | 0 | 0 | 0 | 0 |
| preopening (Home2 Peoria North, ECHO Suites Chandler, Vai Resort) | 3 | 3 | 0 | 0 | 0 | 0 |
| verified-no-pets (as profiles) | 59 | 59 | 0 | 0 | 0 | 0 |

- **Profiles:** approved Phoenix profiles in the candidate: **256**. Unapproved: **0**.
- **Verified-no-pets:** the 59 are published only as exclusions, never as profiles.
- `identity_resolutions.json` was not modified.

## 9. Fee, collision and receipt safety

- **Fees.**
  - 49 single-basis fees publish, each with the basis its own quote states.
  - 77 tiered fees and 35 unsafe / missing-basis fees are withheld.
  - 113 published records quote more than one amount, and **0** of them publish a single fee.
  - **Misleading single fees: 0.**
- **Collisions:** Phoenix names held by another market: 0. Bare-chain names: 0. Duplicate excluded identities across
  the 1,386-row registry: 0.
- **FAST receipt:** `pkg-phoenix-az-07f7e75699af6a8c-b3679c3f11e56c1c.json` is currently eligible under today's
  reader.
  - file_count 1,553 and html_count 1,537.
  - Bundle `ea2a8d31…` ≠ `e3b0c442…`.
  - Rules J and K PASS.
  - Augusta's vacuous historical receipt is still ineligible.

## 10. Byte preservation (candidate vs the live bytes)

| | |
|---|---|
| files live → candidate | 17,904 → 19,436 |
| **FILES ADDED** | **1,532**, all under Phoenix's own `pet-friendly-hotels/phoenix-az/` and `go/phoenix-az/` |
| **FILES REMOVED** | **0** |
| **FILES CHANGED** | **1**: `sitemap.xml` (global, regenerated for every release) |
| prior-market files changed / unclassified paths | **0 / 0** |
| UNEXPECTED MARKET / PROFILE / ROUTE DELTA | **`[]` / `[]` / `[]`** (release_diff passed, 0 findings) |
| PRIOR MARKETS / PROFILES / ROUTES LOST | **0 / 0 / 0** |

## 11. Release gates

| gate | result |
|---|---|
| founder authorization | **PASS**: phoenix-az FOUNDER_AUTHORIZED on `07f7e756`; gained phoenix only; decision_problems `[]` |
| package identity | **PASS**: `07f7e756`, the prior packages refused |
| FAST receipt eligibility | **PASS**: currently eligible, non-vacuous |
| parent identity | **PASS**: parent `6aba7587…` is the current live deploy |
| parent routes preserved | **PASS**: 3,274 / 3,343 carried |
| profile preservation | **PASS**: 2,954 + 256 = 3,210 |
| route preservation | **PASS**: +275 index / +276 served, 0 lost |
| market delta | **PASS**: +phoenix-az only |
| participation | **PASS**: 37 authorized, 0 other rows changed |
| candidate determinism | **PASS**: BYTE_IDENTICAL, 19,436 / 0 |
| deployment eligibility | **PASS**: authorization bound to the candidate bytes, deployable, unconsumed |

`markets/reports/phoenix_az_launch_authorization_004.json` records **ALL_ACCOUNTING_GATES = PASS**.

## 12. Deployment authorization

| | |
|---|---|
| DEPLOYMENT AUTHORIZATION CREATED | **YES**, only after determinism was proven, and only for the exact candidate bytes |
| DEPLOYMENT AUTHORIZATION ID | **`ptf-auth-phoenix-004-19234b7affec`** (`deploy/netlify/deployment_authorizations/`) |
| AUTHORIZED BUNDLE / SITEMAP | `19234b7affec…1f78` / `647596dca769…2ecb` |
| AUTHORIZED PARENT / ROLLBACK TARGET | `6aba7587ddcc33a192bdf694` (Denver, current live) |
| authorized_by | `founder` (the role; the founder's words are quoted in `authorization_source`) |
| STATUS | **AUTHORIZED, UNCONSUMED** (`deploy_id` null, no deployment record) |
| deployability / verify problems | `[]` / `[]`; the only authorization naming phoenix-az |
| candidate manifest | `deploy/netlify/global_deployment_manifest_candidate_phoenix_004.json`; the live `global_deployment_manifest.json` was **not** written |

The writer reads market ids out of the `participating_markets` records, so its "no deployable authorization for this
market may already exist" refusal can actually fire. That is the fix Denver's writer made to San Diego's vacuous check.

## 13. Final live safety (21:52:02Z)

The resolver reports deploy `6aba7587ddcc33a192bdf694`, 36 / 2,954 / 3,343, host verified. The live sitemap is
**`5d3d07a4…`**, byte-identical to the deployment record, with 3,343 `<loc>` and 0 Phoenix routes.

| Route | Expected | Actual |
|---|---|---|
| `/pet-friendly-hotels/phoenix-az/` | 404 | **404** ✅ |
| `/pet-friendly-hotels/phoenix-az/policy-comparison/` | 404 | **404** ✅ |
| `/pet-friendly-hotels/phoenix-az/tempe/` (a publishing corridor) | 404 | **404** ✅ |
| `/pet-friendly-hotels/phoenix-az/arizona-biltmore/` (a profile in the candidate) | 404 | **404** ✅ |
| `/pet-friendly-hotels/denver-co/` | 200 | **200** ✅ |
| `/pet-friendly-hotels/san-diego-ca/` | 200 | **200** ✅ |
| `/pet-friendly-hotels/jacksonville-fl/` | 200 | **200** ✅ |
| `/pet-friendly-hotels/west-palm-beach-fl/` | 200 | **200** ✅ |
| `/pet-friendly-hotels/fort-lauderdale-fl/` | 200 | **200** ✅ |
| `/pet-friendly-hotels/augusta-ga/` | 200 | **200** ✅ |
| `/pet-friendly-hotels/detroit-ann-arbor-mi/` | 404 | **404** ✅ |

No Netlify invocation, no deployment record, no LIVE flag.

## 14. Cleanup

Both whole-site processes were terminated after their bytes were proven stable. No monitors, watchers or build
processes from this order remain; one unrelated pre-existing process (`C:\t\sink.py`, started 2026-09-14) was left
alone. `C:/t/phx4a` is the authorized artifact the deploying order will ship. `C:/t/phx4b` is its determinism twin.
Both are kept on disk outside the repository.

---

## FOR THE DEPLOYING ORDER

1. Consume `ptf-auth-phoenix-004-19234b7affec`.
2. Deploy bundle `19234b7a…` from `C:\t\phx4a`, with rollback `6aba7587ddcc33a192bdf694`.
3. Write the live `global_deployment_manifest.json` from those same bytes; verification fails until it does.
4. Extend `supersessions.json`.

Expect 37 / 3,210 / 3,549 / 3,619, with Phoenix's 276 routes newly returning 200 and every prior route unchanged.
Every held row, every no-pets row and the four vacation-ownership resorts must stay 404.

## FINAL ANSWERS

1. CURRENT LIVE DEPLOYMENT = 6aba7587ddcc33a192bdf694 (Denver), source edf11b7a, bundle 7d3471c7..., sitemap 5d3d07a4..., host verified
2. CURRENT LIVE MARKETS = 36
3. CURRENT LIVE PROFILES = 2,954
4. CORRECTED PHOENIX PACKAGE = pkg-phoenix-az-07f7e75699af6a8c
5. PACKAGE DIGEST = sha256:07f7e75699af6a8cefe5f083b688f647c55190f04aae0cd0617292968ab0fccf
6. PRIOR PHOENIX PACKAGE AUTHORIZED = NO (pkg-phoenix-az-85ad9b66 and pkg-phoenix-az-865822f4 refused by every writer)
7. FOUNDER AUTHORIZATION CREATED = YES (launch_participation.json decision, commit 63e410ff)
8. FOUNDER AUTHORIZATION ID = PTF-PHOENIX-AZ-FOUNDER-LAUNCH-AUTHORIZATION-004 (the participation decision; decided_by founder, 2026-09-29)
9. PARTICIPATION STATE = FOUNDER_AUTHORIZED_FOR_LAUNCH (not live); authorized set 36 -> 37, gained phoenix-az only, lost none, 0 other rows changed, decision_problems []
10. PARENT LOOKUP = PASS
11. PARENT ROUTES PRESERVED = PASS (3,274 index / 3,343 served carried, 0 lost)
12. UNCHANGED BUNDLES REUSED = 36
13. UNCHANGED MARKETS REBUILT = 0
14. PHYSICAL FRAGMENTS RERENDERED = 37 (no release store populated; not reuse)
15. PHOENIX BUNDLES BUILT = 1
16. AUTHORIZED CANDIDATE BUNDLE = 19234b7affec61c16d6ac40e864e83a4c497262b2451eba2d03821482e9a1f78
17. AUTHORIZED CANDIDATE SITEMAP = 647596dca769c1b82c94e1c512ab04d87bbe729c07c1d06a49c2e11e5c652ecb
18. CANDIDATE MARKETS = 37
19. CANDIDATE PROFILES = 3,210
20. CANDIDATE RELEASE-INDEX ROUTES = 3,549
21. CANDIDATE SERVED ROUTES = 3,619
22. PHOENIX PROFILES = 256
23. PHOENIX RELEASE-INDEX ROUTES = 275 (256 hotel + 18 corridor + 1 hub)
24. PHOENIX SERVED ROUTES = 276 (275 + the policy-comparison page)
25. VACATION-OWNERSHIP HOTEL PROFILES = 0
26. VACATION-OWNERSHIP VERIFIED NO-PETS = 0
27. UNAPPROVED PHOENIX PROFILES = 0
28. DUAL-BRAND HOLDS PUBLISHED = 0 (of 28 rows / 14 buildings)
29. PREOPENING PROFILES PUBLISHED = 0 (of 3)
30. MISLEADING SINGLE FEES = 0
31. CROSS-MARKET COLLISIONS = 0 (bare-chain 0, duplicate excluded identities 0)
32. FAST RECEIPT ELIGIBLE = YES (pkg-phoenix-az-07f7e75699af6a8c-b3679c3f11e56c1c.json)
33. RULE J NONEMPTY = PASS (1,553 files / 1,537 HTML / output present)
34. RULE K NONVACUOUS = PASS (BYTE_IDENTICAL, 4 cold builds, 0 reuse)
35. CANDIDATE DETERMINISM = BYTE_IDENTICAL (2 sequential builds, 19,436 files, 0 differing)
36. ALL RELEASE GATES = PASS (11 of 11; ALL_ACCOUNTING_GATES PASS)
37. UNEXPECTED DELTA = [] / [] / [] (0 prior markets, profiles or routes lost)
38. CANDIDATE DEPLOYABLE = YES (AUTHORIZED, not deployed)
39. DEPLOYMENT AUTHORIZATION CREATED = YES
40. DEPLOYMENT AUTHORIZATION ID = ptf-auth-phoenix-004-19234b7affec (AUTHORIZED, UNCONSUMED)
41. CURRENT LIVE MODIFIED = NO
42. DEPLOYMENT PERFORMED = NO
43. PHOENIX LIVE = NO (hub 404)
44. origin == HEAD = YES (verified after the final push)
45. tree clean = YES (verified after the final push)
46. READY FOR PHOENIX PRODUCTION DEPLOYMENT = YES (consume ptf-auth-phoenix-004-19234b7affec; ship C:\t\phx4a)

```
PHOENIX FOUNDER AUTHORIZATION = PASS
PHOENIX AUTHORIZED CANDIDATE = PASS
PRIOR PHOENIX PACKAGE AUTHORIZED = NO
VACATION-OWNERSHIP HOTEL PROFILES = 0
VACATION-OWNERSHIP VERIFIED NO-PETS = 0
UNAPPROVED PHOENIX PROFILES = 0
MISLEADING SINGLE FEES = 0
CURRENT LIVE MODIFIED = NO
PHOENIX DEPLOYED = NO
READY FOR PHOENIX PRODUCTION DEPLOYMENT = YES
```
