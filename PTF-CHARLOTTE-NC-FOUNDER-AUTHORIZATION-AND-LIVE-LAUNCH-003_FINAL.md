# PTF-CHARLOTTE-NC-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-003 — FINAL

**Charlotte, North Carolina is LIVE.** Production serves 15 markets, 1,071 profiles
and 1,267 sitemap routes on host deployment `6aa5ad211250a04bc0bc6f7f`. The live
sitemap hashes exactly to the authorized candidate's sitemap, and every one of the
1,267 live routes returned 200. No build, reassembly, re-seal or candidate regeneration
happened after authorization.

## PHASE 1 — FINAL PARENT RECHECK

These values were read from the host (Netlify published deploy and live sitemap) and compared field by field with
the parent in the COMMITTED `charlotte_nc_founder_authorization_packet_002.json`
(at `89bb0c55`):

    HOST DEPLOYMENT ID     6aa593019a24fc17a07566a4 (ready)
    PARENT RELEASE DIGEST  61ca6a2ef2f170c0ede36cdce03cbf36ee3ae498371d25b79e85e30cc20dc046
    PARENT SITEMAP DIGEST  55996aa7707e57888ce3545bfb0e55d3ec1c558204264bc4dfcbaf9573f0a72a
    MARKETS / PROFILES / ROUTES   14 / 965 / 1148
    LIVE ROUTES            raleigh 70, nashville 87, lexington 25, toledo 21, charlotte 0, detroit 0

    STALE_PARENT = NO

## PHASE 2–3 — EXACT INPUTS AND DELTA (full values, from the committed packet)

    PARENT DEPLOYMENT ID        6aa593019a24fc17a07566a4
    PARENT RELEASE DIGEST       61ca6a2ef2f170c0ede36cdce03cbf36ee3ae498371d25b79e85e30cc20dc046
    PARENT SITEMAP DIGEST       55996aa7707e57888ce3545bfb0e55d3ec1c558204264bc4dfcbaf9573f0a72a
    CHARLOTTE PACKAGE DIGEST    sha256:e09bf4526a010668a3499083542c6eee6e7eb86cbd19fa198acb82963ecdde2c
    BUILD INPUT KEY             sha256:fd7cb29b5ad2a4ee4373e7f7eb89ea6363f22f24bea1456adbd842e25f5c79c3
    VALIDATION RECEIPT DIGEST   sha256:364aea0199da94b1c12049ecbb57ba0781096fccbebfb10afe90d034b617767e
    INTENDED DELTA DIGEST       sha256:b2a566eb38e3bc6278da0b3ccc992b8abb85073edc436a85de9a7c679f131914
    FINAL CANDIDATE DIGEST      606d6088460a48c7787fac6deb1befcc12e39d6ee384342cc13d8ab43ad8a815
    DEPLOYMENT ARTIFACT DIGEST  606d6088460a48c7787fac6deb1befcc12e39d6ee384342cc13d8ab43ad8a815
    CANDIDATE SITEMAP DIGEST    3c6713782208a486f96d7177663625d56606f2bc0bd6bdc353a9b7111af45e6d

Every value was cross-checked against its own artifact: the package file, the FAST
receipt (whose parent is the Raleigh-live deploy) and the artifact's bundle manifest.
The package and candidate are both reproducible, and the two independent builds produced
the same bytes. The whole-site gates passed 27/27 in each build, and FAST rules A–O passed
15/15 with 0 UNKNOWN and 0 FAILED. The change classes remain `MARKET_DATA_PACKAGE` +
`GENERATED_REPORT_ONLY`, with FULL_REGRESSION_REQUIRED NO and 0 remote broad jobs.

Taken from the artifact manifest, the candidate is 15 markets / 1071 profiles / 1267 routes / 6556 files. Charlotte
adds 106 profiles and 119 routes. Removals are 0 markets, 0 profiles and 0 routes, and every one of
the 14 live markets keeps its profile count. Detroit does not participate. Unexpected market, profile
and route changes are 0 / 0 / 0.

## PHASE 4 — FOUNDER AUTHORIZATION

The authorization is `deploy/netlify/deployment_authorizations/ptf-auth-charlotte-003-606d6088460a.json`,
with `authorized_by: founder` and the founder's own words quoted. Its status moved
PREPARED -> AUTHORIZED -> DEPLOYED.

- **What it binds:** the bundle and sitemap through the manifest, plus a `founder_bound_digests` block. That block holds the parent release, package, build input key, receipt, intended delta, candidate and artifact digests. `authorized_markets_by_this_decision` is `["charlotte-nc"]`.
- **Checks:** `verify_authorization` is CLEAN, `deployability_problems` reports none, and `verify_bundle_directory` is CLEAN.
- **Participation:** only the `charlotte-nc` row was flipped. The document went from `2ceba3f2…` to `ae577130089ebd189e033ceda5f57640f7fc09a22d34622a2de5c21b57468910`, which is exactly the bytes the candidate was composed under. `decision_problems` found none, and the only market added to the authorized set is charlotte-nc.
- **Deployment manifest:** re-derived from the candidate's own bundle manifest (`write_manifest`, not a rebuild), and `verify_manifest` is CLEAN.
- **Artifact commit vs this tree:** between the artifact commit `c65e9f28` and the launch tree, only report files changed. So the authorized artifact IS this tree's artifact.

Charlotte's policy authority, holds and 121 unresolved rows were not touched.

## PHASE 5 AND 11 — THE NARROW GATE, OPENED AND CLOSED

    opened   2026-09-12T19:49:40Z  ENABLED YES, ALLOWED_MARKETS ["charlotte-nc"], entry bound to
             candidate/artifact 606d6088…, parent 61ca6a2e…, package, intended delta
             loader probes while open: charlotte-nc allowed; detroit-ann-arbor-mi, raleigh-nc and an
             unnamed market each refused MARKET_NOT_IN_PILOT_ALLOWLIST
    closed   ENABLED NO, ALLOWED_MARKETS [], entry moved to previously_consumed with the host
             deployment id, record id and outcome; the loader now reads PRODUCTION_GATE_CLOSED

No open-ended Charlotte allowlist remains.

## PHASE 6–7 — FINAL CHECK, THEN THE HOST

Immediately before the host call, the host still served `6aa593019a24fc17a07566a4`
with sitemap `55996aa7…` and 1148 routes, and `verify_target` was clean. The staged
artifact `C:\t\clt002cand-a\site` was re-hashed to `606d6088…`, which is the authorized digest.

    RELEASE OPERATION ID   ptf-auth-charlotte-003-606d6088460a
    HOST DEPLOYMENT ID     6aa5ad211250a04bc0bc6f7f
    CANDIDATE DIGEST       606d6088460a48c7787fac6deb1befcc12e39d6ee384342cc13d8ab43ad8a815
    ARTIFACT DIGEST        606d6088460a48c7787fac6deb1befcc12e39d6ee384342cc13d8ab43ad8a815
    DEPLOY START           2026-09-12T19:50:27Z
    DEPLOY COMPLETE        2026-09-12T19:51:14Z   (47.3 s, exit 0; host published 19:51:14.854Z, ready)

## PHASE 8 — TARGETED LIVE VERIFICATION (no broad regression)

| # | check | result |
| --- | --- | --- |
| 1 | exact authorized candidate live | live sitemap hashes to `3c6713782208a486…` |
| 2 | host deployment id | `6aa5ad211250a04bc0bc6f7f`, ready |
| 3 | Charlotte hub | 200 |
| 4 | Charlotte profiles | 5 sampled 200 (and all 106 in the full sweep) |
| 5 | Charlotte corridors | 11 declared, 11 live, all 200 |
| 6 | policy-comparison route | 200 |
| 7 | Charlotte in sitemap | 119 routes, every declared route present |
| 8 | counts match artifact | 1267 routes |
| 9 | Charlotte live profiles | 106 |
| 10–13 | Raleigh / Nashville / Lexington / Toledo | 70 / 87 / 25 / 21 routes, unchanged |
| 14 | unrelated markets | every other market's route count identical; home, category root, about, contact, methodology, robots, llms, 5 hubs all 200 |
| 15–17 | unexpected market / profile / route changes | 0 / 0 / 0 (119 added, all Charlotte; 0 removed) |
| 18 | critical broken links | 0 — all 1267 sitemap routes fetched, 0 non-200 |
| 19 | rollback target | `6aa593019a24fc17a07566a4`, the Raleigh-live release Charlotte replaced |

On `/go/` interstitials, the sampled one carries `noindex`. Charlotte is absent from homepage navigation,
as its market document declares (`show_in_navigation: false`).

## PHASE 9 — ROLLBACK

Rollback was not required and not performed. The target is `6aa593019a24fc17a07566a4` (release
`61ca6a2ef2f170c0ede36cdce03cbf36ee3ae498371d25b79e85e30cc20dc046`). It is deliberately not
Raleigh's own older target, `6aa212a8ba9f174305c0441a`, which would take Raleigh down.

## PHASE 10 — LIVE STATE

- `deploy/netlify/deployment_records/ptf-deploy-charlotte-003-6aa5ad211250a04bc0bc6f7f.json`
  is DEPLOYED, and `verify_record` is CLEAN.
- `tests/pettripfinder/pins/deployment_state.json` has both its live and source blocks moved to this release, with
  `ahead_of_production` false.
- `launch_packages/pettripfinder/charlotte_nc_live_verification_003.json` is the verification receipt.
- `release_index.live_index()` now derives `6aa5ad211250a04bc0bc6f7f`, 15 / 1071 / 1267, with no problems.
  That is the only live-truth source.

## PHASE 12 — PERFORMANCE

    FOUNDER AUTHORIZATION PROCESSING     50.3 s
    FINAL PARENT CHECK                   4.1 s  (+ 3.3 s byte re-hash)
    HOST DEPLOYMENT                      47.3 s
    LIVE VERIFICATION                    31.2 s  (all 1267 routes)
    AUTHORIZATION_TO_VERIFIED_LIVE       5 min 29 s

    LOCAL BROAD REGRESSIONS              0
    REMOTE BROAD JOBS                    0
    UNCHANGED LIVE MARKETS REBUILT       0

## FINAL ANSWERS

     1. PARENT LIVE DEPLOYMENT ID = 6aa593019a24fc17a07566a4
     2. PARENT MARKETS / PROFILES / ROUTES = 14 / 965 / 1148
     3. CHARLOTTE PACKAGE DIGEST = sha256:e09bf4526a010668a3499083542c6eee6e7eb86cbd19fa198acb82963ecdde2c
     4. FINAL AUTHORIZED CANDIDATE DIGEST = 606d6088460a48c7787fac6deb1befcc12e39d6ee384342cc13d8ab43ad8a815
     5. FINAL CANDIDATE MARKETS / PROFILES / ROUTES = 15 / 1071 / 1267
     6. CHARLOTTE LIVE PROFILES = 106
     7. CHARLOTTE ADDED ROUTES = 119
     8. EXACT AUTHORIZED CANDIDATE DEPLOYED = YES
     9. BUILD OR REASSEMBLY AFTER AUTHORIZATION = NO
    10. NEW HOST DEPLOYMENT ID = 6aa5ad211250a04bc0bc6f7f
    11. RALEIGH STILL LIVE = YES
    12. NASHVILLE STILL LIVE = YES
    13. LEXINGTON STILL LIVE = YES
    14. TOLEDO STILL LIVE = YES
    15. UNEXPECTED MARKET / PROFILE / ROUTE CHANGES = 0 / 0 / 0
    16. LOCAL BROAD REGRESSIONS = 0
    17. REMOTE BROAD JOBS = 0
    18. UNCHANGED LIVE MARKETS REBUILT = 0
    19. AUTHORIZATION_TO_VERIFIED_LIVE WALL TIME = 5 min 29 s
    20. ALL CRITICAL LIVE CHECKS PASS = YES
    21. ROLLBACK REQUIRED = NO
    22. ROLLBACK TARGET IS EXACT PRE-CHARLOTTE RALEIGH RELEASE = YES
    23. CHARLOTTE_LIVE = YES
    24. FACTORY CODE CHANGED = NO
    25. FACTORY STATUS = RESUME_MARKET_PRODUCTION
    26. origin == HEAD = YES
    27. tree clean = YES

CHARLOTTE LIVE = YES
BROAD REGRESSIONS = 0
FACTORY CODE CHANGED = NO
FACTORY STATUS = RESUME_MARKET_PRODUCTION
ENGINEERING PHASE = COMPLETE
