# PTF-MIAMI-FL-REGISTRATION-AND-STAGING-004 — FINAL

Market `miami-fl`. Branch `worker/ptf-miami-fl-market-001`, worktree `C:\Atlas-Miami-FL-Hardened-V1`.
Source commit at start: **85f5feef** (`pkg-miami-fl-91076dc436e07ce4`, SHADOW_UNTIL_REGISTERED).

Miami is now **REGISTERED** against the Augusta-live parent and a projected candidate has been composed and
gated. This order stops at **AUTHORIZATION_READY + VALIDATED PROJECTED CANDIDATE**. Nothing was deployed, no
founder authorization or deployment authorization was created, participation was not flipped to LIVE, Netlify
was never invoked, and the served production site is byte-for-byte what it was before this order ran.

---

## 1. Phase 1 — current live, mechanically resolved and host-verified

Resolved with the repaired resolver (`release_index live-source --fetch --verify-host`) over 214 refs.
`origin/main` (`c236f52d`) does **not** contain the live commit and was not used.

| | |
|---|---|
| CURRENT LIVE SOURCE COMMIT | `9656419918229db7a0eb5ca5a1b4fb514e0e9c34` |
| built_from_commit | `ff427c270813fd7d85d82f9260d0706e936f08a9` |
| CURRENT LIVE DEPLOYMENT | `6aaeb3b7384e1bb712adb084` (`ptf-deploy-augusta-006`, 2026-09-17T12:55Z) |
| CURRENT LIVE BUNDLE SHA | `55e0f5bbf02a5e26e8a5eba8510a4488d9a3da6ffaac604ef22df80637fd8914` |
| CURRENT LIVE SITEMAP SHA | `d08b8ca2f019196be244a99c082369b3c557715dbb98ce5dc1da604bbed937e1` |
| CURRENT LIVE MARKETS | **30** |
| CURRENT LIVE PROFILES | **2165** |
| CURRENT LIVE ROUTES | **2477** (served sitemap; 2414 in the release index) |
| HOST VERIFICATION | **PASS** — the served sitemap hashes to the live record |

The expected prior state (30 / 2165 / 2477) and the verified live state agree.

## 2. Phase 2 — the Miami source package

| Requirement | Result |
|---|---|
| MIAMI HEAD = 85f5feef | **YES**, tree clean at start |
| SOURCE READY | YES |
| COVERAGE READY | YES |
| ACTIONABLE UNRESOLVED | **0** (`miami_fl_closure_accounting_003.json`) |
| Package | `pkg-miami-fl-91076dc436e07ce4` |
| Digest | `sha256:91076dc436e07ce40f8df494e9e401c81aad5bb48fb07a58c50d7b034a99c87a` |
| FAST in the sealed receipt | **15/15 PASS**, 0 UNKNOWN, 0 FAILED |
| DETERMINISM_RESULT | `BYTE_IDENTICAL` |
| First-party binding / collision / removal | PASS / PASS / PASS |

The census was not rebuilt, Marriott acquisition was not re-run, broad discovery was not re-run, and no
Firecrawl call was made (credits unchanged at 1,346; **$0.00** spent).

## 3. Phase 3 — registration

A fresh market's registration is a promotion, not a single command: the shadow documents move into the
registered paths and the generic lane then proves them. What ran, in order:

1. `identity_census_proposed/miami-fl.json` → `identity_census/miami-fl.json`, and 15 Miami helpers repointed.
2. `miami_fl_registration_staging_001` → the registered policy package and
   `miami_fl_proposed_authority_001.json` **at the package root** — the role name
   `<market_us>_proposed_authority_*.json` that `registration_data_only` requires (naming it anything else cost
   Orlando all 15 checks).
3. `market_registration_cli --write` → the Miami authority shard: 125 seed rows, 57 exclusions, empty routing
   and affiliate shards.
4. `miami_fl_geography_001` → `markets/miami-fl.json` (20 corridors / 79 ZIPs).
5. `build_global_authority --write` → the three shard-derived globals and the manifest (32 markets sharded).
6. `miami_fl_release_contract_004` → `deploy/netlify/release_contracts/miami-fl.json`, every number derived,
   **0 disagreements**.
7. `registration_release_lane register` → participation row at
   `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH`, authorized set unchanged; build closure gained exactly
   the market's two declared inputs.
8. `registration_release_lane seal --work-order` → `pkg-miami-fl-b586ad449e46d057`, sealed twice to one digest,
   FAST 15/15, candidate composed twice to one digest, market-state pin written from the package.
9. `registration_release_lane packet` → AUTOMATIC classification and the UNSIGNED readiness document.

| | |
|---|---|
| REGISTRATION CLASS | **COMPOSITE_FRESH_MARKET_DATA_ONLY** |
| ELIGIBLE | **YES** — 15/15 checks PASS (proof `ptf-registration-data-only/2.0`) |
| FULL_REGRESSION_REQUIRED | **NO** |
| REMOTE_BROAD_JOBS_REQUIRED | 0 |
| BROAD REGRESSION RUNS | **0** |
| Change set | 129 paths, every one in exactly one narrow bucket: 33 market-local, 13 registration, 81 derived, **0 shared, 0 unknown** |
| STATUS | **AUTHORIZATION_READY** / founder: AWAITING_FOUNDER_AUTHORIZATION |

### Time — stated honestly

**REGISTRATION LANE TIME = 3 m 45 s** — `register` (~2 s) + `seal` **162.9 s** (of which FAST 136.0 s, live
parent read 24.9 s) + `packet` **59.0 s**. Against the order's targets: **≤ 5 min YES, ≤ 10 min HARD YES.**

That is the lane, and it is the number the ≤5-minute benchmark was set for. The **wall clock from TIMER START
(18:35:45 UTC) to AUTHORIZATION_READY (≈20:26 UTC) was ≈1 h 51 m**, and it is not the lane's: it contains the
fresh-market promotion wiring above (a real, one-time cost for a market that was built shadow), a pause while
auto mode refused the shared registration writes until you authorized them, and one defect this order found and
fixed (§3.1) plus the reseal it forced. I am reporting both rather than the flattering one.

### 3.1 The defect this order found

The first classification came back **ELIGIBLE = NO** with all 15 checks failing on one root cause:

> `scripts/pettripfinder/miami_fl_browser_closure_002.py` is not market-local: writes failed (line 325
> `open:w`: write target cannot be resolved statically)

Two Miami helpers took their output **path as an argument** — the `--report` flag the terminal-closure order
added, and the policy-pages reader shared between two lanes. A market-local helper whose write target cannot be
resolved statically is not provably isolated, and the registration loses its narrowing over it (the Outer Banks
rule). Both now **name** a committed target instead of taking a path: the closure lane picks its ingestion
report by PASS NAME (`--pass 002|003`), and the policy-pages reader picks one of its two committed capture files
by LANE NAME. Re-running the ingestion changed nothing: 97 READ / 10 ACCESS_DENIED / 4 shared-page / 1 no-brand-
page / 1 amenity-chip / 1 no-policy, 0 unbound — byte-identical evidence, a provably isolated writer.

## 4. Phase 4 — registration accounting

| Requirement | Result |
|---|---|
| CURRENT LIVE WEBSITE BYTES CHANGED | **NO** |
| CURRENT LIVE DEPLOYMENT CHANGED | **NO** — still `6aaeb3b7384e1bb712adb084` |
| CURRENT LIVE SERVED ROUTES CHANGED | **NO** — sitemap still `d08b8ca2…`, 2477 routes |
| Unrelated market deltas | **NONE** — `derived_globals` PASS: the committed globals are byte-identical to a regeneration from the shards and **no other market's shard changed** |
| `release_integrity` | PASS — no deployment authorization, record, manifest, activation flag, production gate or deployment pin was modified |

**Miami registration record:** participation `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH`;
sealed package **`pkg-miami-fl-b586ad449e46d057`**, digest
`sha256:b586ad449e46d0572c8b3c9248d56a8dcec7a51c4bf938598e9f1428f0b73cb1`; FAST receipt
`pkg-miami-fl-b586ad449e46d057-1d0e0cdffb485af4.json`, digest `sha256:1d0e0cdffb485af4…d96c9`.
The source-ready shadow package `pkg-miami-fl-91076dc436e07ce4` stays SHADOW_UNTIL_REGISTERED history.

## 5. Phase 5 — projected participation

The candidate was composed **in memory / in a scratch work dir only** (`C:\t\mia9d`). No founder authorization
was written, Miami was not marked LIVE, and no deployment participation was persisted. The lane's own record
states `nothing_deployed: true`, `nothing_activated: true`, `participation_untouched: true`.

**CANDIDATE MODE = PROJECTED / NON-DEPLOYABLE.**

## 6. Phase 6 — release store / parent lookup

| Requirement | Result |
|---|---|
| PARENT LOOKUP | **PASS** — parent resolved to live deploy `6aaeb3b7384e1bb712adb084` |
| PARENT FOUND BY DEPLOYED CONTENT IDENTITY | **PASS** — resolved through the deployed bundle identity, not a registration-sensitive manifest-only lookup |
| PARENT ROUTES PRESERVED | **PASS** — `identity_routes`: `release_index.compare` is clean over both the expected and the actual release; every live member preserved, no ownership movement, no duplicate route |
| Parent release digest | `sha256:c7998b87f638354ec5db316487f77c089f4351966aad9b0d99b4add74f0dd023` |

## 7. Phase 7 — staging

| Requirement | Expected | Actual |
|---|---:|---:|
| UNCHANGED LIVE MARKETS REUSED | 30 | **30** |
| UNCHANGED MARKETS REBUILT | 0 | **0** |
| MIAMI BUNDLES BUILT | ≤ 1 | **1** |

Changed-market bundle `sha256:0de043c9fa6787a8547761ad5754ec054cec4a17ffda29b5abc851d4656e401a`.
Candidate index digest `sha256:79a28dae68edeebf00f571b93fd5b8930956acf56a2493666051fc105a346db0`, composed
twice to the same digest (**CANDIDATE_REPRODUCIBLE = YES**); the package sealed twice to the same digest
(**PACKAGE_REPRODUCIBLE = YES**).

## 8. Phase 8 — candidate delta

`expected_release`: EXPECTED (live parent + sealed package) and ACTUAL (committed authority) **agree as complete
sets**.

| | Parent | Miami adds | Candidate |
|---|---:|---:|---:|
| Markets | 30 | +1 | **31** |
| Profiles | 2165 | +125 | **2290** |
| Routes (release index) | 2414 | +136 | **2550** |

- **UNEXPECTED MARKET DELTA = []**
- **UNEXPECTED PROFILE DELTA = []**
- **UNEXPECTED ROUTE DELTA = []**
- `complete_sets_equal: true`, `findings: []`
- All 30 prior live markets, all 2165 prior profiles and all prior routes preserved; **0 removed**; Miami claims
  **0** routes the live release already serves.

## 9. Phase 9 — Miami candidate accounting

| | |
|---|---:|
| MIAMI LIVE PROFILES | **125** |
| MIAMI CORRIDOR ROUTES | **10** |
| MIAMI OTHER ROUTES | **1** (the policy-comparison page) |
| TOTAL MIAMI ROUTES ADDED | **136** |

**Which of the 125 publish:** all of them, and only them. The contract's public surface is `seed_hotel_rows 125
/ public_hotel_profile_count 125 / excluded_public_profile_count 0`, and the policy package carries exactly 125
records — one seed row per CLEAN_PET_FRIENDLY identity. The **57 verified-no-pets identities are NOT published
as hotel profiles**: they are written as exclusion records, which is what every live market's contract does; no
held, refused, addressless or duplicate identity has a route or a reference on any surface.

Projected post-Miami totals: **MARKETS 31 / PROFILES 2290 / ROUTES 2550** (release index). The served sitemap
count is produced by the deployment order, not this one; for reference the live index/sitemap differ (2414 vs
2477), so the sitemap projection is ≈2614 and is not asserted here.

## 10. Phase 10 — staging gates

| Gate | Result |
|---|---|
| change_set | PASS (129 paths, 0 shared, 0 unknown) |
| market_local_zone | PASS (33 paths, all five isolation conditions, registration mode) |
| discovery_config | PASS (loads for exactly miami-fl) |
| registration_input | PASS (`ptf-market-proposed-authority/1.0` for exactly miami-fl) |
| identity_resolutions | PASS (no ruling in the set) |
| participation | PASS (one row, non-founder writer, every other row untouched) |
| release_contract | PASS (shared rules identical to base, data fields derived) |
| build_closure | PASS (exactly the two declared inputs) |
| derived_globals | PASS (byte-identical to a regeneration; no other market's shard changed) |
| sealed_package | PASS (sealed from exactly the head bytes, REGISTERED_LIVE) |
| fast_receipt | PASS (15/15, 0 UNKNOWN, 0 FAILED) |
| expected_release | PASS (complete sets agree: 31 / 2290 / 2550, 0 unexpected) |
| identity_routes | PASS (compare clean over expected and actual) |
| market_state_pin | PASS (eight counts equal what the package derives) |
| release_integrity | PASS (nothing deployment-side modified) |
| **ALL STAGING GATES** | **PASS (15/15)** |

**DEPLOYMENT REFUSAL = EXPECTED / PASS.** The gate's own reader refuses Miami:
`launch_status("miami-fl") = SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH`,
`is_founder_authorized("miami-fl") = False`, and the authorized set is still exactly the 30 live markets.
`deploy/netlify/deployment_authorizations/` holds 33 files and **none is Miami's**.

## 11. Phase 11 — no deployment (verified externally after the work)

Re-resolved with host verification **after** registration:

| | Before | After |
|---|---|---|
| CURRENT LIVE DEPLOYMENT | `6aaeb3b7384e1bb712adb084` | `6aaeb3b7384e1bb712adb084` |
| CURRENT SERVED SITEMAP | `d08b8ca2f019196be244a99c082369b3c557715dbb98ce5dc1da604bbed937e1` | identical |
| Live bundle sha | `55e0f5bb…8914` | identical |
| Live markets / profiles / routes | 30 / 2165 / 2477 | 30 / 2165 / 2477 |
| MIAMI LIVE | NO | **NO** (not in the live participating set) |

No deployment authorization was created, no founder authorization was created, `netlify` was never invoked, and
no live record, deployment or participation flag was changed.

---

## FINAL ANSWERS

1. **CURRENT LIVE SOURCE COMMIT** = `9656419918229db7a0eb5ca5a1b4fb514e0e9c34`
2. **CURRENT LIVE DEPLOYMENT** = `6aaeb3b7384e1bb712adb084`
3. **CURRENT LIVE MARKETS** = 30
4. **CURRENT LIVE PROFILES** = 2165
5. **CURRENT LIVE ROUTES** = 2477 served (2414 release index)
6. **MIAMI PACKAGE** = `pkg-miami-fl-b586ad449e46d057` (registered; source-ready shadow `pkg-miami-fl-91076dc436e07ce4` verified and kept as history)
7. **MIAMI PACKAGE DIGEST** = `sha256:b586ad449e46d0572c8b3c9248d56a8dcec7a51c4bf938598e9f1428f0b73cb1`
8. **REGISTRATION CLASS** = COMPOSITE_FRESH_MARKET_DATA_ONLY
9. **ELIGIBLE** = YES (15/15 checks PASS)
10. **FULL_REGRESSION_REQUIRED** = NO
11. **REGISTRATION TIME** = 3 m 45 s of lane execution (wall clock from timer start ≈1 h 51 m — promotion wiring, an authorization pause and one defect fix, §3)
12. **REGISTRATION ≤5M TARGET** = YES (lane)
13. **REGISTRATION ≤10M HARD** = YES (lane)
14. **BROAD REGRESSION RUNS** = 0
15. **PARENT LOOKUP** = PASS (by deployed content identity)
16. **PARENT ROUTES PRESERVED** = PASS
17. **UNCHANGED BUNDLES REUSED** = 30
18. **UNCHANGED MARKETS REBUILT** = 0
19. **MIAMI BUNDLES BUILT** = 1
20. **ALL STAGING GATES** = PASS (15/15)
21. **UNEXPECTED DELTA** = [] (markets, profiles and routes)
22. **MIAMI PROJECTED PROFILES** = 125
23. **MIAMI PROJECTED ROUTES** = 136 (125 hotel + 10 corridor + 1 policy-comparison)
24. **PROJECTED TOTAL MARKETS** = 31
25. **PROJECTED TOTAL PROFILES** = 2290
26. **PROJECTED TOTAL ROUTES** = 2550 (release index)
27. **CANDIDATE MODE** = PROJECTED / NON-DEPLOYABLE
28. **DEPLOYMENT REFUSAL** = EXPECTED / PASS
29. **CURRENT LIVE MODIFIED** = NO
30. **MIAMI DEPLOYED** = NO
31. **origin == HEAD** = YES
32. **tree clean** = YES
33. **READY FOR FOUNDER LAUNCH AUTHORIZATION** = YES

---

MIAMI REGISTRATION = PASS
MIAMI STAGING = PASS
FULL_REGRESSION_REQUIRED = NO
BROAD REGRESSION RUNS = 0
UNCHANGED MARKETS REBUILT = 0
MIAMI DEPLOYED = NO
CURRENT LIVE MODIFIED = NO
READY FOR FOUNDER LAUNCH AUTHORIZATION = YES

STOP.
