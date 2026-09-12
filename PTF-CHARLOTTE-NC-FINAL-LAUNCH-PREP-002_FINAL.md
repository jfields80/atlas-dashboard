# PTF-CHARLOTTE-NC-FINAL-LAUNCH-PREP-002 — FINAL

**Charlotte, North Carolina is prepared for founder authorization and NOT deployed.**
The candidate adds Charlotte as the 15th market (106 profiles, 119 sitemap routes) on
top of the verified Raleigh-live release. It builds reproducibly from two
independent worktrees, and no live file changes except the global sitemap.

One order requirement was not met as written, and the operator ruled on it in
session (Phase 4 below).

## PHASE 1 — CURRENT VERIFIED LIVE (read from the host)

    HOST DEPLOYMENT ID     6aa593019a24fc17a07566a4  (Netlify published, state ready)
    LIVE RELEASE DIGEST    61ca6a2ef2f170c0ede36cdce03cbf36ee3ae498371d25b79e85e30cc20dc046
    SOURCE COMMIT          fa125e27706f2071d2b35387a0d537795f92f6fe
    SITEMAP DIGEST         55996aa7707e57888ce3545bfb0e55d3ec1c558204264bc4dfcbaf9573f0a72a
    MARKETS / PROFILES / ROUTES   14 / 965 / 1148
    PARTICIPANTS           cincinnati, cleveland-akron-canton, columbus, dayton, grand-rapids-holland,
                           indianapolis, lexington, louisville, milwaukee, nashville, pittsburgh,
                           raleigh, st-louis, toledo
    ROLLBACK PARENT        6aa212a8ba9f174305c0441a
    VERIFICATION STATUS    live sitemap fetched and hashed = 55996aa7…, 1148 <loc>;
                           Raleigh 70 / Nashville 87 / Lexington 25 / Toledo 21 routes live; Charlotte 0

The worktree is `C:\Atlas-Charlotte-Launch-V2` on branch
`worker/ptf-charlotte-final-launch-002`. It started at HEAD `c7330450` with a clean tree.

## PHASE 2–3 — SOURCE AND RECONCILIATION

The source is `C:\Atlas-Charlotte-Hardened-V1`, branch `worker/ptf-charlotte-new-market-001`, at `42cb937f`.
**That commit is an ancestor of HEAD.** Every Charlotte-owned file is already in the
base, together with the POLICY-001 re-registration package. The Charlotte import
delta is **0 paths**, and nothing was merged.

| | value (derived authority = contract = pin) |
| --- | --- |
| registered census | 268 (268 IDENTITY_CONFIRMED / LODGING_CONFIRMED) |
| pet-friendly | 106 |
| verified no-pets | 41 |
| resolved / unresolved | 147 / 121 |
| holds | 1 IDENTITY_HOLD, 2 SERVICE_ANIMAL_ONLY, 0 founder holds in package |
| corridors | 21 declared, 11 published corridor routes |

`contract_disagreements` = none. `verify_all` is clean for all 16 registered markets.
`market_eligibility` reports the market as assemblable; its partition resolves through
`LEGACY_TABLE` (the entry Charlotte already had), and the assembler was not edited.

## PHASE 4 — CLASSIFICATION (REQUIREMENT NOT MET AS WRITTEN; OPERATOR RULING)

Regression V2 ran in normal mode over `c7330450..WORKTREE`. It found 7 changed paths
(1 package, 1 receipt, 5 reports), and all 7 are accounted for:

    CHANGE CLASSES            MARKET_DATA_PACKAGE, GENERATED_REPORT_ONLY
    UNKNOWN PATHS             0      modules 0      narrowing blockers none
    FULL_REGRESSION_REQUIRED  NO     LOCAL BROAD REQUESTED 0 / RUN 0     REMOTE BROAD 0

**`COMPOSITE_FRESH_MARKET_DATA_ONLY` was NOT selected.** The registration proof refuses the set
with `change_set: exactly one previously absent market must be registered; the registry
gained nothing`. The other 14 proof checks were not evaluated. Charlotte was
already registered at the base, so a fresh-market class is structurally unreachable
without two things this order forbids: a fabricated de-registered base, or a
classifier change.

**Operator ruling, given in this session:** accept the actual class; ready = YES. The
ruling is recorded in the packet as the operator's. It is not a founder authorization.
The audited `registration_release_lane packet` gate would read NOT_AUTHORIZATION_READY
for this set, so it was not run.

## PHASE 5–6 — RE-SEAL / FAST

`registration_release_lane seal --market charlotte-nc` ran against the Raleigh-live
parent. `register` and `seal --work-order` were not run: Charlotte already has a
participation row and a pin block, and both steps refuse by design.

    SEAL + FAST          130.96 s   CLASSIFY 4.79 s   → REGISTRATION_TO_AUTH_READY 135.7 s
    PACKAGE              pkg-charlotte-nc-e09bf4526a010668, PACKAGE_REPRODUCIBLE YES
    FAST                 15 / 15 PASS, 0 UNKNOWN, 0 FAILED, determinism BYTE_IDENTICAL
    UNCHANGED MARKETS REBUILT 0      no acquisition rerun

## PHASE 7–9 — PARENT RECHECK, CANDIDATE, REPRODUCIBILITY

Immediately before composition, the host still served `6aa59301…` with sitemap
`55996aa7…` and 1148 routes, so the parent was not stale. Each of two fresh detached
worktrees at `c65e9f28` flipped exactly one participation row, `charlotte-nc`, for
the build only. `decision_problems` found none, and Detroit was not added.

    BUILD A / B          rc 0 / rc 0, 812 s / 759 s, 27/27 gates pass each
    FINAL_CANDIDATE_REPRODUCIBLE  YES (identical bundle + sitemap, re-hashed from disk)
    vs LIVE ARTIFACT     5907 → 6556 files; 5906 identical; 649 added, all under
                         pet-friendly-hotels/charlotte-nc/ (119) and go/charlotte-nc/ (530);
                         0 removed; changed = sitemap.xml only
    PRESERVED            raleigh 63, nashville 79, lexington 20, toledo 17 — every live market identical
    UNEXPECTED           market 0 / profile 0 / route 0 / file 0

    PARENT RELEASE DIGEST      61ca6a2ef2f170c0ede36cdce03cbf36ee3ae498371d25b79e85e30cc20dc046
    PARENT RELEASE INDEX       sha256:8a5ba9103d9ef0eda8edc75be3bbf09dc1e43a7e3dbca8fd2402e254101cc17c
    CHARLOTTE PACKAGE DIGEST   sha256:e09bf4526a010668a3499083542c6eee6e7eb86cbd19fa198acb82963ecdde2c
    BUILD INPUT KEY            sha256:fd7cb29b5ad2a4ee4373e7f7eb89ea6363f22f24bea1456adbd842e25f5c79c3
    INTENDED DELTA DIGEST      sha256:b2a566eb38e3bc6278da0b3ccc992b8abb85073edc436a85de9a7c679f131914
    FINAL CANDIDATE DIGEST     606d6088460a48c7787fac6deb1befcc12e39d6ee384342cc13d8ab43ad8a815
    DEPLOYMENT ARTIFACT DIGEST 606d6088460a48c7787fac6deb1befcc12e39d6ee384342cc13d8ab43ad8a815
    SITEMAP DIGEST             3c6713782208a486f96d7177663625d56606f2bc0bd6bdc353a9b7111af45e6d
    VALIDATION RECEIPT DIGEST  sha256:364aea0199da94b1c12049ecbb57ba0781096fccbebfb10afe90d034b617767e
    EXPECTED CANDIDATE INDEX   sha256:80e2aa2b285f704808ef68f38982e2e22a76aaf5e2676559999fe66c14aaa757

The staged artifacts are kept at `C:\t\clt002cand-a` and `C:\t\clt002cand-b`.

## PHASE 10–11 — FOUNDER PACKET, STOP

`launch_packages/pettripfinder/markets/reports/charlotte_nc_founder_authorization_packet_002.json`
has STATUS **AWAITING_FOUNDER_AUTHORIZATION**, with `authorized_by` and `authorized_at` both null.

- **Projected:** 15 markets / 1071 profiles / 1267 sitemap routes (release-index basis 15 / 1071 / 1219).
- **Charlotte adds:** +106 profiles and +119 routes.
- **Rollback:** `6aa593019a24fc17a07566a4`, release `61ca6a2ef2f170c0ede36cdce03cbf36ee3ae498371d25b79e85e30cc20dc046`. This is the Raleigh-live release, not its own rollback target, because that target would un-deploy Raleigh.

Nothing was authorized, activated or deployed.

## FINAL ANSWERS

     1. CURRENT LIVE MARKETS / PROFILES / ROUTES = 14 / 965 / 1148
     2. RALEIGH PRESENT AND LIVE = YES
     3. CHARLOTTE CENSUS / PF / NO-PETS = 268 / 106 / 41
     4. RESOLVED / UNRESOLVED = 147 / 121
     5. CHANGE CLASS = MARKET_DATA_PACKAGE + GENERATED_REPORT_ONLY (COMPOSITE_FRESH_MARKET_DATA_ONLY not selected: Charlotte already registered at base; accepted by operator ruling)
     6. CHANGED PATHS ACCOUNTED = 7 / 7
     7. UNKNOWN PATHS = 0
     8. LOCAL BROAD REQUESTED = 0
     9. LOCAL BROAD RUN = 0
    10. REMOTE BROAD REQUIRED = 0
    11. UNCHANGED LIVE MARKETS REBUILT = 0
    12. REGISTRATION_TO_AUTH_READY = 135.7 s (re-seal + FAST + classify)
    13. FAST = 15 / 15 PASS, 0 UNKNOWN, 0 FAILED
    14. PACKAGE REPRODUCIBLE = YES
    15. FINAL CANDIDATE REPRODUCIBLE = YES
    16. PROJECTED LIVE MARKETS / PROFILES / ROUTES = 15 / 1071 / 1267
    17. UNEXPECTED DELTAS = 0 / 0 / 0
    18. CHARLOTTE_FOUNDER_AUTHORIZATION_READY = YES (per operator ruling on Phase 4)
    19. FACTORY CODE CHANGED = NO
    20. origin == HEAD = YES
    21. tree clean = YES

CHARLOTTE AUTHORIZATION READY = YES
REGISTRATION BROAD RUNS = 0
FACTORY STATUS = RESUME_MARKET_PRODUCTION
CHARLOTTE DEPLOYED = NO
