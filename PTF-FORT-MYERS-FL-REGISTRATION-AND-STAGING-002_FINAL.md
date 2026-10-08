# PTF-FORT-MYERS-FL-REGISTRATION-AND-STAGING-002 — FINAL (with crash recovery)

**Status:** Fort Myers, Cape Coral & Sanibel, Florida is **REGISTERED and STAGED**. The readiness packet is
**AUTHORIZATION_READY**; founder status is AWAITING_FOUNDER_AUTHORIZATION.

**Not done:** nothing was deployed. There is no founder launch authorization and no deployment authorization, and
current live is unchanged.

**Branch:** `worker/ptf-fort-myers-fl-market-001` (worktree `C:\Atlas-Fort-Myers-FL-Hardened-V1`). At the start, HEAD =
origin = `6f4d67ef` (the last clean source-ready commit).

**Commits:**
- `19c47422`: the registration transaction (first BUILD commit; its packet refused one gate import, see §5).
- `6a425592`: the gate-module import fix. **This is the BUILD commit a founder authorization must bind.** The packet
  classified it AUTHORIZATION_READY.
- The final commit holds the automatic classification, the readiness packet, the live probe and this report.

## 1. Interruptions and recovery (recorded as required)

| event | what happened |
|---|---|
| **Initial permission block** | The first attempt completed the repoint, promotion, policy / authority / partition regeneration and the shard, then stopped at `build_global_authority --write`. Auto mode refused it as *Modify Shared Resources*. |
| **Terminal crash** | The VS Code terminal crashed after that block, leaving the registration work uncommitted on disk. |
| **Recovery start** | This order opened by inspecting disk state. No write was made before the inspection finished. |
| **Second permission block** | The resumed write was refused again. The approval sat inside a *pasted* work order, which the classifier does not treat as the operator's own words. The operator was asked, not routed around. |
| **Founder approval** | The operator then typed an approval of `build_global_authority --write` and of the canonical registration-owned writes that follow (launch_participation.json, bundle_cache_closure.json, the generated globals, the market-state pin written by `seal --work-order`). That approval excludes shared factory or reader changes, broad regression, founder authorization, deployment authorization and Netlify. |

### Disk state found (mechanical)

| check | result |
|---|---|
| branch / HEAD / origin | `worker/ptf-fort-myers-fl-market-001` / `6f4d67ef` / `6f4d67ef` |
| 15 `fort_myers_fl_*` modules | **26 path repoints intact** (`identity_census_proposed/` → `identity_census/`, `markets/proposed/` → `markets/`, staging `launch_package/` → package root); publication-safety audit split into a pure `audit()` |
| census, market document | git-renamed into the registry, **0 content change** |
| policy package, proposed authority, final partition | at the package root, **byte-identical** to the sealed source-ready copies |
| shard (4 files) | written 08:02:38 local; **byte-identical** to the sealed shard; 57 seed rows, 34 exclusions |
| three generated globals | **== HEAD blobs** byte-for-byte; mtimes = worktree checkout (2026-10-07 22:18); `--check` reported all three STALE |

**Did the global-authority write complete before the crash? NO.** It never ran (recovery case A).
**Exact step resumed:** `build_global_authority --write`, followed by `--check`.
**No destructive reset was performed**; no uncommitted change was discarded; no completed source-ready or
preprocessing step was rerun (acquisition, the source package, the repoint, the promotion, the regenerations and the
shard were all verified on disk and kept).

## 2. Current live (before and after)

`release_index live-source --fetch --verify-host` at 14:30:45Z and again at 14:52:17Z, unchanged both times:

| | |
|---|---|
| CURRENT LIVE DEPLOYMENT | **`6ac6f3d213d002249f9c3e67`** (record `ptf-deploy-salt-lake-city-004-…`) |
| CURRENT LIVE SOURCE COMMIT | `3d812f28` (built_from `6959e985`) |
| MARKETS / PROFILES / RELEASE-INDEX / SERVED | **45 / 4,373 / 4,807 / 4,885** |
| HOST VERIFIED | YES |

## 3. Global authority

`build_global_authority --write` → `--check` = **all generated artifacts match the shards**.

| | before | after | delta |
|---|---:|---:|---:|
| global seed rows | 4,522 | 4,579 | **+57**, all fort-myers-fl; added rows == the shard's rows; prior rows and their order preserved |
| global exclusions | 1,886 | 1,920 | **+34**, all fort-myers-fl; added == the shard; **0 removed or modified** |
| manifest markets | 46 | 47 | fort-myers-fl added; **0 other market entries changed**; `identity_routing.json` unchanged |

**UNEXPECTED GLOBAL AUTHORITY DELTA = []**. No generated file was hand-edited, and `build_market_authorities --write`
was not run.

## 4. Registration steps (resumed)

1. **Release contract:** new module `fort_myers_fl_release_contract_002.py`, fully derived through
   `release_contracts.derive_authority` with **0 disagreements**. Census 142, PF 57, NP 34, resolved 91, unresolved 51,
   4 of 14 corridors publish. `verify_all()`: **47 / 47 clean**.
2. **`register`** (≈6 s, 14:30:03Z→14:30:09Z): participation goes from 46 to 47 rows. fort-myers-fl is added once at
   `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH`. 0 rows removed, **0 changed**, authorized set unchanged,
   Detroit still withheld. `load_participation()` loads with `decision_problems = []`. The build closure gained exactly
   the release contract and the market document.
3. **`seal --work C:/t/fm3 --work-order`** (205.4 s, detached, alone; live-parent read 75.7 s, FAST 128.2 s):
   - package **`pkg-fort-myers-fl-919f61116936bf5e`**
     (`sha256:919f61116936bf5e23fe42f0aa745c87c6020a7896f7149b64ec603359ace47e`), reproducible YES;
   - FAST 15/15, receipt `…-71b99a5343da6d8f` eligible, J 367 files / 351 HTML, bundle `cc784255…`
     (= the source-ready bundle), K BYTE_IDENTICAL;
   - candidate 46 / 4,430 / 4,869, reproducible YES;
   - pin block census 142 / PF 57 / NP 34 / corridor routes 4 (the pin diff is exactly that block plus `reviewed_by`).
4. **Staging gates** (`fort_myers_fl_registration_checks_002.py`, run on the seal's FAST site `C:/t/fm3/oa/site`):
   **35 / 35 PASS**, problems `[]`.
5. **BUILD commit** `19c47422`, then **`packet`** (§5), then the fix commit `6a425592` and a second `packet`.

**Registered package = source-ready content:** census, PF/NP records, seed rows, partition, official routes, evidence,
unresolved rows and founder holds are field-for-field identical to `pkg-fort-myers-fl-68b3cfa8bc4758c5`
(`sha256:68b3cfa8…2415`, sealed at `f0096324`), and the package builds the **same bundle**. The id differs only by
zone, source sha and sealed_at.

## 5. One correction made in this order

The first `packet` (53.3 s) returned **NOT_AUTHORIZATION_READY / broad YES**. The cause was a single path: the new gate
module imported `scripts.pettripfinder.commercial_actions`, which is not on the market-local import allow-list. That
made the module SHARED, and the other 14 checks were reported as "not evaluated". The gate's route-scheme check now
states the same external-destination rule itself (absolute http/https with a real host). FAST rule J still checks every
built `/go/` page. The gates were rerun at 35/35 with the report **byte-identical**, committed as `6a425592`, and the
second `packet` passed. No data changed, and no shared module was touched. The failed first packet outputs were not
committed; the second packet regenerated them.

## 6. Automatic classification and readiness

| | |
|---|---|
| AUTOMATIC BASE DERIVES | **YES**, `21dacb1c2d4ba7d98804b55a9f81ac615b5b7272` from live lineage `3d812f28`, no manual input |
| classification_source | **AUTOMATIC** (no `--classification` given) |
| REGISTRATION CLASS | **COMPOSITE_FRESH_MARKET_DATA_ONLY** |
| CLASSIFIER CHECKS | **15 / 15 PASS** (change_set, market_local_zone, discovery_config, registration_input, identity_resolutions, participation, release_contract, build_closure, derived_globals, sealed_package, fast_receipt, expected_release, identity_routes, market_state_pin, release_integrity) |
| ELIGIBLE | YES |
| FULL_REGRESSION_REQUIRED | **NO** |
| REMOTE BROAD JOBS / BROAD REGRESSION RUNS | **0 / 0** |
| change set | 106 paths: 32 market-local, 13 registration data, 61 derived; **0 shared, 0 unknown** |
| packet | **AUTHORIZATION_READY**, founder AWAITING_FOUNDER_AUTHORIZATION (106.0 s; classification 100.4 s) |

## 7. Projected candidate (derived, not guessed)

| | |
|---|---:|
| FORT MYERS PROFILES | **57** |
| FORT MYERS RELEASE-INDEX ROUTES | **62** (57 hotels + 4 corridors + 1 hub) |
| FORT MYERS SERVED ROUTES | **63** (the 62 plus the policy-comparison page, from the built sitemap) |
| CANDIDATE MARKETS | **46** |
| CANDIDATE PROFILES | **4,430** (4,373 + 57) |
| CANDIDATE RELEASE-INDEX ROUTES | **4,869** (4,807 + 62) |
| CANDIDATE SERVED ROUTES | **4,948** (4,885 + 63) |
| UNCHANGED BUNDLES REUSED | **45** |
| UNCHANGED MARKETS REBUILT | **0** |
| FORT MYERS BUNDLES BUILT | 1 (FAST's own cold builds of the one bundle) |
| PHYSICAL FRAGMENTS RERENDERED | 0 (no whole-site assembly; the seal composed the candidate twice and both agree) |

Unexpected market / profile / route delta `[]`. Prior markets, profiles, index routes and served routes lost: 0.
`release_index.compare` reports 0 findings.

## 8. Safety (from `fort_myers_fl_registration_checks_002.json`)

- **Founder rulings, all held, checked by name and by address:**
  - **Comfort Suites / MainStay Suites, 9455 Old Luckett:** both non-admitted SAME_CAMPUS_DISTINCT_ENTITY. 0 seed, PF
    or NP rows at 9455; no profile, index route or served route.
  - **4760 S Cleveland:** Quality Inn is the census SAME_IDENTITY_REBRAND_SUCCESSOR, held in the sealed package, so
    there is no registration-time promotion (0 seed / PF / NP rows at 4760). Travelodge is retired, and
    TRAVELODGE_EVIDENCE_MIGRATED_TO_4760 = 0. The one published Travelodge is the separate 13353 N Cleveland Ave
    building, 33903, bound by its own Wyndham page.
  - **Latitude 26 Waterfront Inn & Suites:** OUTSIDE_MARKET (34134, Collier licence). All five Latitude 26 keys are
    unpublished.
  - **Pink Shell Beach Resort & Marina and Edison Beach House:** REQUIRES_FOUNDER / EVIDENCE_HOLD, never PF or NP.
  - **All 51 unresolved rows:** 0 published.
  - **`identity_resolutions.json`:** not written. The shared reader was not modified.
- **Reader:** PF with explicit refusal 0; question-only PF 0; service-animal-only 0; NP quote without refusal 0; shared
  reader disagreements 0. First-party binding: 91 / 91 eligible.
- **Fees:** 5 single-basis fees publish. Each is a Marriott-family "Non-Refundable Pet Fee Per Stay" field, and no
  quote states a daily or nightly basis. 22 tiered and 5 unsafe fees are withheld (3 basis not stated, 1 amount floor,
  1 sentence cut); 0 withheld fees flattened. **MISLEADING SINGLE FEES 0.**
- **Geography:**
  - All 142 rows are in Lee County, Florida; the pin envelope is Fort Myers' own (26.28–26.78 N, 82.26–81.56 W).
  - WRONG-CITY 0; own municipality flattened to Fort Myers 0; Naples / Collier admitted 0; Naples seed rows 0;
    non-Florida 0; seed rows rewritten 0.
  - Published by municipality: Fort Myers 34, Bonita Springs 6, Cape Coral 4, Estero 4, Fort Myers Beach 4,
    Captiva 3, North Fort Myers 2.
  - The boundary audit refuses Naples, Marco Island, Everglades City, Immokalee, Punta Gorda, Port Charlotte,
    Englewood / Boca Grande, Pine Island, LaBelle and Sarasota–Venice, with 0 admitted from any.
- **Operating status / lodging class:** nonoperating 0, preopening / closed 0, timeshare / vacation ownership 0
  (5 refused rows checked by name), condo / residence / rental 0 (121 refused rows checked by name), military 0, boundary
  islands 0.
- **Routes:** 182 outbound destinations checked; **INVALID ROUTE SCHEMES 0**. FAST rule J passed on the build.
- **Cross-market:** collisions 0; bare-chain names 0; duplicate excluded identities 0; live properties moved 0.
- **Market text:**
  - Clone residue in the registered data documents is 0 text, 0 coordinate and 0 boundary (109 other-market tokens,
    11 documents).
  - The release contract states its lineage by name ("on the Salt Lake City-live hardened lineage"), and that is
    allowed.
  - Its module also names the `lexington-ky.json` template from which the project-wide release rules are read. As in
    the previous registration, both are deliberate cross-market references, never market identity.
  - The market label "Fort Myers, Cape Coral & Sanibel, Florida" is correct in the market document, the contract and
    the hub page. The sealed policy package's internal `market` field reads "Fort Myers / Cape Coral / Southwest
    Florida, Florida". It is recorded as found and was not edited, because the package is sealed.
- **Deployment refusal: EXPECTED / PASS.** 0 authorizations and 0 deployment records name fort-myers-fl, and the market
  is not founder-authorized.

## 9. Live safety (after staging)

`fort_myers_fl_registration_live_probe_002.json`, 14:51:02Z:
- Live deploy is unchanged: 6ac6f3d2, 45 / 4,373 / 4,807 / 4,885, Fort Myers not participating.
- **Fort Myers hub 404; all 63 projected Fort Myers routes 404.** **Detroit 404.**
- Salt Lake City, New Orleans, Kansas City, Minneapolis, Portland, Seattle, San Antonio, Tampa, Miami, Orlando,
  Jacksonville FL, West Palm Beach, Fort Lauderdale and Augusta are **200**.

## 10. Timing

| | |
|---|---|
| REGISTER | ≈6 s |
| SEAL | 205.4 s (FAST 128.2 s) |
| PACKET | 106.0 s (first, refused packet: 53.3 s) |
| GENERIC LANE (register + seal + passing packet) | ≈317 s ≈ 5 m 17 s; the ≤ 5 min target is missed by ≈17 s, all of it FAST cold builds; ≤ 10 min PASS |
| resumed work | 14:29Z (approved write) → 14:52:17Z (post-staging live check) ≈ 23 m |

## 11. Isolation

- No shared factory or reader implementation changed. No broad regression, acquisition, spend, founder
  authorization, deployment authorization, deployment or Netlify call.
- Shared documents touched are exactly the registration-owned six: `launch_participation.json` (reissued by
  `register`), `bundle_cache_closure.json` (+2), the three generated globals and the market-state pin (written by
  `seal --work-order`).
- The seal's work directory `C:/t/fm3` is kept, because it holds the built candidate site the gates read.
- Only processes this order started were run, and each has exited. The pre-existing `C:\t\sink.py` process was left
  untouched.

## FINAL ANSWERS

FORT MYERS REGISTRATION = PASS
FORT MYERS STAGING = PASS
CRASH RECOVERY = PASS
AUTOMATIC BASE DERIVES = YES
GLOBAL AUTHORITY WRITE = PASS
GLOBAL AUTHORITY CHECK = PASS
FULL_REGRESSION_REQUIRED = NO
BROAD REGRESSION RUNS = 0
WRONG-CITY FORT MYERS IDENTITIES = 0
NAPLES PROFILES ADMITTED = 0
NONOPERATING PROFILES PUBLISHED = 0
PET-FRIENDLY RECORDS WITH EXPLICIT REFUSAL = 0
QUESTION-ONLY PET-FRIENDLY RECORDS = 0
SERVICE-ANIMAL-ONLY ACCEPTANCE = 0
UNAPPROVED FORT MYERS PROFILES = 0
MISLEADING SINGLE FEES = 0
INVALID ROUTE SCHEMES = 0
UNCHANGED MARKETS REBUILT = 0
CURRENT LIVE MODIFIED = NO
FORT MYERS DEPLOYED = NO
READY FOR FOUNDER LAUNCH AUTHORIZATION = YES (bind BUILD commit 6a425592, package pkg-fort-myers-fl-919f61116936bf5e)

STOP.
