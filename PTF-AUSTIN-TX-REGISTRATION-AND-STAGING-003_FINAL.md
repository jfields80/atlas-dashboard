# PTF-AUSTIN-TX-REGISTRATION-AND-STAGING-003 — FINAL

**Austin / Central Texas (`austin-tx`) is REGISTERED, STAGED and AUTHORIZATION_READY.** It is not authorized and
not deployed. Registered package: `pkg-austin-tx-ee3f5c9147638f51`, built from the refreshed package's content.

| | |
|---|---|
| Class | COMPOSITE_FRESH_MARKET_DATA_ONLY: 15/15 checks, broad NO, 0 remote broad jobs |
| FAST | 15/15 |
| Candidate | 38 markets / 3,386 profiles / 3,737 release-index routes / 3,808 served routes |
| Staging gates | 21/21 PASS |
| Production | unchanged |

Worktree `C:\Atlas-Austin-TX-Hardened-V1`, branch `worker/ptf-austin-tx-market-001`.

**Read first:** the lane's AUTOMATIC classification refused (BASE_NOT_DERIVABLE). The cause is a correction I made
in the previous production order, not anything in Austin. The classification was therefore SUPPLIED against an
explicit, documented base (§5, §12).

## 1. Current live (Phase 1)

The canonical resolver (`release_index live-source --fetch --verify-host`) gave:

| | |
|---|---|
| CURRENT LIVE SOURCE COMMIT | `46e49a02fa6297c80c1052bfab815b490cdc1997` (built from `18f4f979`) |
| CURRENT LIVE DEPLOYMENT | `6abdbcb87e046e3e673760ac` |
| CURRENT LIVE BUNDLE | `63ae17cf40542101c731ce315a210da5fae6ebce4ba51fc76477c80e2364edd7` |
| CURRENT LIVE SITEMAP | `4ee064226b37e36e96e1ecaf91a5e1301985445547a0225fdce526dd7b06999d` |
| CURRENT LIVE MARKETS / PROFILES | 37 / 3,196 |
| CURRENT LIVE RELEASE-INDEX / SERVED ROUTES | 3,534 / 3,604 |
| HOST VERIFIED | YES; HEAD contains live |

**Live had not advanced.** It was re-verified after staging (§9).

## 2. The Austin package (Phases 2–3)

**Refreshed package.** Registration started from the refreshed package `pkg-austin-tx-024e6fb46a9e6934`
(`sha256:024e6fb4…65b4`):

- SOURCE READY YES, actionable 0.
- Census 407; 190 pet-friendly / 63 verified-no-pets / 253 resolved / 154 unresolved (62.16 %).
- FAST 15/15, J and K PASS, receipt eligible, independently reproduced.
- Reader-safety: refusal 0, question-only 0, misleading fees 0.

**Registered package.** The lane sealed it as `pkg-austin-tx-ee3f5c9147638f51`
(`sha256:ee3f5c9147638f5128621ef113ce7b496ff00c4afa78bbff242a5bd50f5e5ea8`), zone REGISTERED_LIVE.

- Its census, records, seed rows, partition, routes, evidence, unresolved rows and holds are **field-for-field
  identical** to `pkg-austin-tx-024e6fb4`.
- It builds the **same bundle** `6cc8b825…`.
- The id differs only because the zone and source sha differ.

**Stale package.** `pkg-austin-tx-3030caf7` was not registered or authorized, and no canonical receipt selects it.
Its historical files are kept.

## 3. Founder coverage decision (Phase 4)

Recorded in `markets/reports/austin_tx_founder_coverage_decision_003.json`, written by
`austin_tx_founder_coverage_decision_003.py`. It uses the same shape as Phoenix's, Denver's and San Diego's records,
transcribes the order's decision, and signs no reviewer name.

**Decision:** APPROVED FOR LAUNCH WITH CURRENT SAFE COHORT; COVERAGE READY = YES BY FOUNDER DECISION.

**Approved:** 190 pet-friendly profiles, with 63 verified-no-pets exclusions.

**Held (154), enumerated from the committed actionability report** (the writer refuses on any mismatch):

| held class | rows |
|---|---:|
| need new spend | 80 |
| founder-decision: 18 dual-brand + 5 operator-domain / Bunkhouse + 2 refusal-language (Mountain Star, Strickland Arms) | 25 |
| router-exhausted / evidence / source-silent | 49 |
| preopening | 0 |

**Held outside the census, unchanged:**
- 11 same-campus rows;
- Sentral East Austin (IDENTITY_REVIEW_REQUIRED);
- timeshare: Club Wyndham Austin, WorldMark Austin, Raintree.

**The decision does not:**
- authorize spend;
- resolve, publish or convert any held row;
- write `identity_resolutions.json`;
- resolve any dual-brand or operator-domain question;
- weaken any evidence rule.

## 4. Canonical registration (Phase 5)

Steps, in dependency order. This is Phoenix's recipe, unchanged.

1. **Repoint.** 14 Austin modules were repointed from the shadow zone to the registered zone (path constants only).
2. **Promotion.** The census and market document moved byte-for-byte (`git mv`, R100).
   - The policy package, proposed authority and final partition were regenerated at the package root by their own
     writers.
   - **All five are byte-identical to the sealed copies.**
   - `austin_tx_*.py` imports were checked through the isolation proof's own `_import_allowed` in registration
     mode. After one fix (my new checks module read deployment documents through the deployer modules; it now reads
     them as data): 0 refused.
3. **Authority shard.** `market_registration_cli --write` wrote 190 seed rows and 63 exclusions, plus empty routing
   and affiliate shards. **All four are byte-identical to the shard the refreshed package sealed.**
4. **Globals.** `build_global_authority --write`, then `--check` clean:
   - exclusions 1,398 → **1,461** (+63, all austin-tx);
   - seed rows 3,345 → **3,535** (+190, all austin-tx);
   - 0 removed or modified.
5. **Release contract.** `deploy/netlify/release_contracts/austin-tx.json` (writer `austin_tx_release_contract_003.py`):
   - fully derived, 0 disagreements;
   - `release_contracts.verify_all()`: **39 / 39** verify.
6. **`register`** (6.3 s). Participation went 38 → 39 rows: austin-tx added once at
   `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH`, 0 removed, **0 existing rows changed**. The founder-authorized
   set is unchanged at 37. The build closure gained exactly the release contract and the market document.
7. **`seal --work C:/t/atx3a --work-order`** (378.5 s).
   - Package `pkg-austin-tx-ee3f5c9147638f51`, FAST 15/15, K BYTE_IDENTICAL.
   - Market-state pin: census 407 / PF 190 / NP 63 / corridor routes 12.
8. **Commit** `cfcd2a0e`, then **packet**.

## 5. Classification (Phase 5, continued)

**`packet` (automatic classification) REFUSED: BASE_NOT_DERIVABLE.**

`derive_registration_base` requires the base to carry **exactly the live lineage commit's live-truth files**: the
deployment records and authorizations, the global manifest, and the deployment-state pin.

- The live lineage commit `46e49a02` added deployment record `ptf-deploy-question-negation-001-6abdbcb8`.
- The next commit on that lineage, `8da2c313`, was mine (PTF-FIRST-PARTY-QUESTION-NEGATION-AND-LIVE-CORRECTION-001).
  After the deploy, it corrected one field (`source_commit` `56b68e13` → `18f4f979`) in that record, its
  authorization and the deployment-state pin.
- The resolver treats records as immutable and anchors the lineage to the commit that added them. So no commit after
  `46e49a02` carries its exact live-truth bytes, and **no registration on this lineage can derive a base
  automatically**.
- This is not specific to Austin. It lasts until the next deployment creates a new lineage commit.

**Supplied classification.** The lane's supported alternative is
`packet --classification <supplied classification>`. It was used with the classifier itself
(`regression_delta classify`, head = the clean working tree = committed `0221907b`) against base
**`1109a239`**.

- `1109a239` is the tip of the live production lineage this branch merged.
- It contains the live lineage commit and names no austin-tx path.
- It differs from `46e49a02` only by the correction above and that order's report.
- The classification document records `classification_source = SUPPLIED`, the live resolution, and this explanation
  (`markets/reports/austin_tx_registration_classification_003.json`).

**The supplied run went through three classifications:**

1. **First run:** FULL_REGRESSION_REQUIRED = YES, from one cause. My refresh module (`austin_tx_reader_refresh_002.py`,
   from the previous order) read committed blobs with `git -C <dir> show`, which the isolation proof cannot resolve
   as read-only. The other checks were therefore not evaluated.
   - This is a market-local code defect, not a structural one. It was fixed (`git show` with `cwd`) and committed
     as `0221907b`.
   - No broad regression was run.
2. **Second run, `--head HEAD`:** ELIGIBLE NO. The sealed-package checks read "from the working tree only", so a
   head other than the working tree cannot prove them.
3. **Third run, clean working tree** (the mode the lane itself uses):

| | |
|---|---|
| CLASS | **COMPOSITE_FRESH_MARKET_DATA_ONLY** |
| ELIGIBLE | **YES**: 15/15 checks PASS (change_set, market_local_zone, discovery_config, registration_input, identity_resolutions, participation, release_contract, build_closure, derived_globals, sealed_package, fast_receipt, expected_release, identity_routes, market_state_pin, release_integrity) |
| FULL_REGRESSION_REQUIRED | **NO** |
| REMOTE BROAD JOBS | **0** |
| BROAD REGRESSION RUNS | **0** |
| Change set | 116 paths: 34 market-local, 13 registration data, 69 derived (companion reports / docs), **0 shared, 0 unknown** |

**`packet --classification …`:** **AUTHORIZATION_READY**, founder status AWAITING_FOUNDER_AUTHORIZATION, written to
`markets/reports/austin_tx_registration_authorization_readiness.json`.

## 6. Timer (Phase 6)

| | |
|---|---|
| REGISTER COMMAND TIME | 6.3 s |
| SEAL TIME | 378.5 s (FAST 324.5 s: rules J and K build Austin's 1,157-file bundle cold four times; live parent read 43.9 s) |
| PACKET TIME | 83.7 s (classification 83.2 s + packet 0.5 s) |
| GENERIC REGISTRATION-LANE TIME | **≈ 7 m 49 s** (468.6 s) |
| TOTAL REGISTRATION WALL CLOCK | **21 m 02 s** (13:29:37Z → 13:50:38Z) |

- **≤ 5 minutes: MISSED.** The FAST cold builds alone take 5 m 25 s.
- **≤ 10 minutes:** the lane steps pass (7 m 49 s). **Total wall clock does not (21 m 02 s).** The extra time was
  the automatic packet's refusal, its diagnosis, the module fix, and two extra classifications (42 s and 66 s).

## 7. Isolation, held rows, reader and fee safety (Phases 7–10)

`markets/reports/austin_tx_registration_checks_003.json`. Every check runs on the site the seal's own FAST build
produced (`C:/t/atx3a/oa/site`). Profiles are compared by the route the site itself forms
(`release_index.hotel_route`), never by census slug. Census slugs keep "and"; the site drops it. The first run of
my check compared slugs and wrongly flagged 5 approved hotels.

**Isolation (Phase 7):** SHARED FACTORY IMPLEMENTATION CHANGES 0, UNKNOWN PATHS 0, UNRELATED MARKET SOURCE CHANGES 0.

**Held-row safety (Phase 8)**, rows published / rows:

| class | published |
|---|---:|
| need new spend | 0 / 80 |
| dual-brand | 0 / 18 |
| operator-domain | 0 / 5 |
| Mountain Star | 0 / 1 |
| Strickland Arms | 0 / 1 |
| router-exhausted / other | 0 / 49 |
| **all unresolved** | **0 / 154** |

- **Profiles built:** 190 Austin profiles, all approved. UNAPPROVED AUSTIN PROFILES = 0.
- **Held outside the census** (same-campus, Sentral, timeshare): 0 published.
- **Preopening and timeshare profiles:** 0.

**Reader safety (Phase 9):**
- PET-FRIENDLY WITH EXPLICIT REFUSAL 0; QUESTION-ONLY PET-FRIENDLY 0.
- Kalahari, AT&T Hotel, Heywood and Sage Hill are each **not pet-friendly** and are verified no-pets.
- Rule C: 253 / 253 eligible.

**Fee safety (Phase 10):** MISLEADING SINGLE FEES 0. Nightly ≠ per-stay and daily ≠ per-stay are preserved, tiered
fees are withheld rather than flattened, and multi-amount fees are not collapsed.

## 8. Staging, accounting and delta (Phases 11–18)

**Participation (Phase 11):** austin-tx is `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH`, added once; all 38
existing rows are preserved and 0 changed.

**Parent (Phase 12):**
- PARENT LOOKUP PASS: the package parent is `6abdbcb8`, the current 37-market repaired release.
- PARENT ROUTES PRESERVED PASS: all 3,534 parent release-index routes are carried.

**Staging (Phase 13):**

| | |
|---|---|
| UNCHANGED BUNDLES REUSED | **37**: every live market's committed index entry is carried unchanged |
| UNCHANGED MARKETS REBUILT | **0** |
| AUSTIN BUNDLES BUILT | **1** (FAST's own cold builds) |
| PHYSICAL FRAGMENTS RERENDERED | **0** (no whole-site assembly ran; the candidate index was composed twice and agrees, `7e189f8c…`) |

**Projected accounting (Phase 14),** from candidate sets:

| | |
|---|---:|
| AUSTIN PROJECTED PROFILES | 190 |
| AUSTIN RELEASE-INDEX ROUTES | **203** (190 hotels + 12 corridors + 1 hub) |
| AUSTIN SERVED ROUTES | **204** (the 203 plus its policy-comparison page, counted from the built sitemap) |
| CANDIDATE MARKETS | **38** |
| CANDIDATE PROFILES | **3,386** (3,196 + 190) |
| CANDIDATE RELEASE-INDEX ROUTES | **3,737** (3,534 + 203) |
| CANDIDATE SERVED ROUTES | **3,808** (3,604 + 204) |

**Delta safety (Phase 15):**
- Unexpected market, profile and route deltas: `[]`.
- Prior markets, profiles, release-index routes and served routes lost: 0.
- Austin is the only new market. `release_index.compare`: 0 findings.

**Cross-market safety (Phase 16):** CROSS-MARKET COLLISIONS 0, BARE-CHAIN 0, DUPLICATE EXCLUDED IDENTITIES 0; 0 live
properties moved or displaced.

**FAST receipt (Phase 17):**
- `pkg-austin-tx-ee3f5c9147638f51-2a0d99ea89736090.json` is CURRENTLY ELIGIBLE.
- J: 1,157 files / 1,141 HTML, bundle `6cc8b825…` (not `e3b0c442`). K: BYTE_IDENTICAL, 0 defects.
- No stale Austin receipt is selectable.

**Staging gates (Phase 18): 21/21 PASS.**

| gates | |
|---|---|
| package and lane | package identity, registration lane eligible, FAST receipt eligibility, FAST A–O |
| parent and preservation | parent lookup, parent routes, markets, profiles, routes, candidate delta |
| decision and safety | participation, founder-decision reconciliation, held-cohort, preopening, timeshare, reader, fee, collision |
| contracts and binding | first-party binding, release contracts |
| **deployment refusal** | **EXPECTED / PASS**: 0 deployment authorizations and 0 records name austin-tx; not founder-authorized |

## 9. Live safety (Phase 19)

Re-verified after staging:

- Live is still `6abdbcb8` (ready); served sitemap `4ee06422…`.
- **Austin hub 404, and all 204 projected Austin routes 404.**
- Phoenix, Denver, San Diego, Jacksonville FL, West Palm Beach, Fort Lauderdale and Augusta return 200; Detroit 404.

CURRENT LIVE MODIFIED = NO. No deploy, no deployment authorization, no founder authorization.

## 10. Commits

- `cfcd2a0e`: the registration transaction.
- `0221907b`: the module fix.
- The final commit: the classification, the readiness packet and this report.

The seal's scratch dir `C:/t/atx3a` and every temporary process were removed.

## 11. What the founder is now being asked to decide

Founder launch authorization of `pkg-austin-tx-ee3f5c9147638f51`, the registered package with the refreshed
content. Expected effect: **+1 market / +190 profiles / +203 release-index routes / +204 served routes**, giving
38 / 3,386 / 3,737 / 3,808.

The stale `pkg-austin-tx-3030caf7` must not be authorized.

## 12. FINDING: automatic registration base derivation is blocked on the current live lineage

- My post-deploy correction of `source_commit` in the live deployment record (`8da2c313`) made the record
  "change" after the commit that added it.
- `derive_registration_base` therefore refuses every registration on this lineage. A supplied classification
  (§5) is required until the next deployment adds a new record, and so a new lineage commit.
- Austin's own deployment will clear it.
- A durable fix needs a factory ruling, which this order may not make. Options: let the resolver accept an
  explicitly superseding record, or make corrections a new record file rather than an edit.

## FINAL ANSWERS

1. CURRENT LIVE DEPLOYMENT = 6abdbcb87e046e3e673760ac
2. CURRENT LIVE MARKETS = 37
3. CURRENT LIVE PROFILES = 3196
4. CURRENT LIVE RELEASE-INDEX ROUTES = 3534
5. CURRENT LIVE SERVED ROUTES = 3604
6. AUSTIN PACKAGE = pkg-austin-tx-ee3f5c9147638f51 (registered; content field-identical to the refreshed pkg-austin-tx-024e6fb46a9e6934, same bundle 6cc8b825)
7. PACKAGE DIGEST = sha256:ee3f5c9147638f5128621ef113ce7b496ff00c4afa78bbff242a5bd50f5e5ea8 (refreshed source package sha256:024e6fb46a9e6934e4884ddb2ac2f4c42756a6154f6f0cd74d6674baf9e665b4)
8. STALE PACKAGE REGISTERED = NO
9. FOUNDER COVERAGE DECISION = APPROVED FOR LAUNCH WITH CURRENT SAFE COHORT (190 PF / 63 NP; 154 held)
10. REGISTRATION CLASS = COMPOSITE_FRESH_MARKET_DATA_ONLY. The classification was SUPPLIED against base 1109a239, because the automatic base derivation refused (§5, §12).
11. ELIGIBLE = YES (15/15)
12. FULL_REGRESSION_REQUIRED = NO. An intermediate supplied run said YES because of one market-local `git -C` call; it was fixed in 0221907b, and no broad run was made.
13. REGISTER COMMAND TIME = 6.3 s
14. SEAL TIME = 378.5 s (FAST cold builds 324.5 s)
15. PACKET TIME = 83.7 s (classification 83.2 s + packet 0.5 s)
16. GENERIC REGISTRATION-LANE TIME = 7 m 49 s
17. <=5M TARGET = MISSED (the FAST cold builds alone take 5 m 25 s)
18. <=10M HARD LIMIT = lane steps PASS (7 m 49 s); total wall clock 21 m 02 s exceeds it, because of the automatic-packet refusal and its fix
19. BROAD REGRESSION RUNS = 0
20. SHARED FACTORY PATHS = 0
21. UNKNOWN PATHS = 0
22. PARENT LOOKUP = PASS
23. PARENT ROUTES PRESERVED = PASS
24. UNCHANGED BUNDLES REUSED = 37
25. UNCHANGED MARKETS REBUILT = 0
26. PHYSICAL FRAGMENTS RERENDERED = 0 (no whole-site assembly ran)
27. AUSTIN BUNDLES BUILT = 1
28. AUSTIN PROJECTED PROFILES = 190
29. AUSTIN RELEASE-INDEX ROUTES = 203
30. AUSTIN SERVED ROUTES = 204
31. CANDIDATE MARKETS = 38
32. CANDIDATE PROFILES = 3386
33. CANDIDATE RELEASE-INDEX ROUTES = 3737
34. CANDIDATE SERVED ROUTES = 3808
35. APPROVED AUSTIN PROFILES = 190
36. UNAPPROVED AUSTIN PROFILES = 0
37. NEW-SPEND HOLDS PUBLISHED = 0 of 80
38. DUAL-BRAND HOLDS PUBLISHED = 0 of 18
39. OPERATOR-DOMAIN HOLDS PUBLISHED = 0 of 5
40. REMAINING REFUSAL HOLDS PUBLISHED = 0 of 2 (Mountain Star, Strickland Arms)
41. PREOPENING PROFILES PUBLISHED = 0
42. TIMESHARE PROFILES PUBLISHED = 0
43. PET-FRIENDLY WITH EXPLICIT REFUSAL = 0
44. QUESTION-ONLY PET-FRIENDLY = 0
45. MISLEADING SINGLE FEES = 0
46. CROSS-MARKET COLLISIONS = 0
47. FAST RECEIPT CURRENTLY ELIGIBLE = YES
48. RULE J NONEMPTY = PASS (1,157 files / 1,141 HTML)
49. RULE K NONVACUOUS = PASS (BYTE_IDENTICAL)
50. ALL STAGING GATES = PASS (21/21)
51. DEPLOYMENT REFUSAL = EXPECTED / PASS
52. CURRENT LIVE MODIFIED = NO
53. DEPLOYMENT PERFORMED = NO
54. AUSTIN LIVE = NO (hub and all 204 routes 404)
55. origin == HEAD = YES (verified after the final push)
56. tree clean = YES (verified after the final push)
57. READY FOR FOUNDER LAUNCH AUTHORIZATION = YES (packet AUTHORIZATION_READY; authorize pkg-austin-tx-ee3f5c9147638f51 only)

```
AUSTIN REGISTRATION = PASS
AUSTIN STAGING = PASS
FOUNDER COVERAGE DECISION = APPROVED
FULL_REGRESSION_REQUIRED = NO
BROAD REGRESSION RUNS = 0
PET-FRIENDLY RECORDS WITH EXPLICIT REFUSAL = 0
QUESTION-ONLY PET-FRIENDLY RECORDS = 0
UNAPPROVED AUSTIN PROFILES = 0
MISLEADING SINGLE FEES = 0
UNCHANGED MARKETS REBUILT = 0
CURRENT LIVE MODIFIED = NO
AUSTIN DEPLOYED = NO
READY FOR FOUNDER LAUNCH AUTHORIZATION = YES
```
