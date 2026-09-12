# PTF-RALEIGH-NC-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-003 — FINAL

**Raleigh, North Carolina is LIVE.** Production serves 14 markets, 965 profiles
and 1,148 sitemap routes on host deployment `6aa593019a24fc17a07566a4`. The live
sitemap hashes to exactly the authorized candidate's sitemap. Raleigh is the
first market admitted by the contract-driven partition resolver: no assembler
edit, no static table entry.

Nothing was rebuilt after authorization. The bytes deployed are the bytes that
were assembled twice, audited and authorized.

## PHASE 1 — CURRENT LIVE PARENT

Read from the committed record chain and then from the host itself:

    HOST DEPLOYMENT ID     6aa212a8ba9f174305c0441a
    PARENT RELEASE DIGEST  c12b410ec8331dbf7a50581027ad60291cac95f626de5a6a846b0d77524e0e11
    SOURCE COMMIT          aee8a21e6c13881543601a4fcd54350b6a64bb19
    SITEMAP DIGEST         13f5335fc1a055ce06de5ce66c7921da55308110e94c0b0f18806853c1662bc4
    MARKETS / PROFILES / ROUTES     13 / 902 / 1078
    ROLLBACK PARENT        6aa172121d37bb4013eb44a4 (the parent's own, not used here)
    VERIFICATION STATUS    the live host's sitemap hashed to 13f5335f… with 1078 <loc>
                           entries and zero Raleigh routes -- an independent read, not
                           a restatement of the record

    STALE_PARENT = NO

One value needed reconciling and did: the packet's
`parent_release_index_digest` is `sha256:b7be3484…` while the launch branch
computes `sha256:b078d97e…`. The release index enumerates REGISTERED markets,
and the packet's value was computed in a tree where Raleigh is registered.
Recomputing it in that same tree reproduces `b7be3484…` exactly. Live itself is
identical either way: same deploy id, same bundle digest, same sitemap digest,
same counts.

## PHASE 2 — AUTHORIZATION INPUTS, FULL DIGESTS

Read mechanically from the committed packet and receipt, never from terminal
output:

    RALEIGH SEALED PACKAGE DIGEST   sha256:0acacc0707bd2b47da30e16b443a8a2a1d6aa20f9a48ef66a811ec463d017465
    SEALED PACKAGE ID               pkg-raleigh-nc-0acacc0707bd2b47
    BUILD INPUT KEY (dependency)    sha256:16efec294d79e95871d4e6851987ad1dc29cff1f6e65971e8b0361447d7ae571
    INTENDED DELTA DIGEST           sha256:e93147c2a7b8dfd482bca74941a7148302b48b1ccd6b342e65f7fdc591d917d5
    VALIDATION RECEIPT DIGEST       sha256:3044b0bd76788da5aad0a57bdf7a6c169599dbfac344902227e807edd0412410
    CHANGED MARKET BUNDLE           25802a6fac7d51e16994d273f30ddef65f8f3ef09196ea6fe3dbdd7fadb3c8c2
    EXPECTED CANDIDATE INDEX        sha256:90513eea910411a1f0352fd403b2c353152107f46c2b469245dc4f7ca4695a0c
    FINAL CANDIDATE DIGEST          61ca6a2ef2f170c0ede36cdce03cbf36ee3ae498371d25b79e85e30cc20dc046
    DEPLOYMENT ARTIFACT DIGEST      61ca6a2ef2f170c0ede36cdce03cbf36ee3ae498371d25b79e85e30cc20dc046
    CANDIDATE SITEMAP DIGEST        55996aa7707e57888ce3545bfb0e55d3ec1c558204264bc4dfcbaf9573f0a72a

The staged artifact was re-hashed from disk over all 5,907 files and reproduced
`61ca6a2e…` and `55996aa7…` exactly. FAST 15/15 PASS, 0 UNKNOWN, 0 FAILED.
Package reproducible YES, candidate reproducible YES. Nothing was rebuilt.

The launch branch merged Raleigh's registration, and every input the assembler
reads — `scripts/`, `launch_packages/` outside `reports/`, and `deploy/` — is
byte-identical between the commit the artifact was built from and the launch
tree. The authorized artifact IS this tree's artifact.

## PHASE 3 — FOUNDER AUTHORIZATION

`deploy/netlify/deployment_authorizations/ptf-auth-raleigh-003-61ca6a2ef2f1.json`,
`authorized_by: founder`, status PREPARED -> AUTHORIZED -> DEPLOYED. It binds
the parent release digest, the Raleigh package digest, the intended delta, the
final candidate and the deployment artifact. `verify_authorization` CLEAN,
`deployability_problems` NO BLOCKERS, `verify_bundle_directory` CLEAN against
the staged tree. Only `raleigh-nc` was authorized; Charlotte and Detroit remain
source-ready and unauthorized, and Raleigh's 4 unresolved identities were not
touched.

Participation was flipped for `raleigh-nc` alone, and the resulting document
hashes to `2ceba3f24362e682f7fd84ecb6be6dc95682f8ad08e939fba1b3e95b2d2753a0` —
the exact bytes the authorized candidate was composed under. Membership is an
input to the candidate's digest, so writing any other participation document
after authorization would have invalidated the artifact the founder authorized.
`decision_problems` reports NONE.

## PHASE 4 AND 10 — THE NARROW GATE, OPENED AND CLOSED

    opened   ENABLED YES, ALLOWED_MARKETS ["raleigh-nc"], bound to candidate 61ca6a2e…
             charlotte-nc, detroit-ann-arbor-mi and an unnamed market were each
             refused by the loader: MARKET_NOT_IN_PILOT_ALLOWLIST
    closed   ENABLED NO, ALLOWED_MARKETS [], the entry moved to previously_consumed
             with its host deployment id and outcome

No open-ended Raleigh allowlist remains, and the audited factory was not
disabled globally.

## PHASE 5 AND 6 — FINAL CHECK, THEN THE HOST

Immediately before activation the host was read again: the live sitemap still
hashed to `13f5335f…` with 1078 routes and zero Raleigh. The staged artifact
still hashed to `61ca6a2e…`.

    RELEASE OPERATION ID   ptf-auth-raleigh-003-61ca6a2ef2f1
    HOST DEPLOYMENT ID     6aa593019a24fc17a07566a4
    DEPLOY START           2026-09-12T17:58:54Z
    DEPLOY COMPLETE        2026-09-12T17:59:47Z   (53 s, exit 0)
    HOST PUBLISHED AT      2026-09-12T17:59:44.109Z, state ready

The host requested 385 of the candidate's 5,907 files. The other 5,522 it
already held, which is the same fact as the pre-deploy comparison stated
differently: every previously live market's bytes were untouched.

## PHASE 7 — TARGETED LIVE VERIFICATION

No broad regression was run after deployment.

| # | check | result |
| --- | --- | --- |
| 1 | exact authorized candidate live | live sitemap hashes to `55996aa7…` |
| 2 | host deployment id matches | `6aa593019a24fc17a07566a4`, state ready |
| 3 | Raleigh hub reachable | 200 |
| 4 | Raleigh hotel profiles | 5 sampled, all 200 |
| 5 | Raleigh corridors | 5 declared, 5 in sitemap, 2 sampled 200 |
| 6 | policy-comparison route | 200 |
| 7 | Raleigh in sitemap | 70 routes |
| 8 | production counts | 14 / 965 / 1148 |
| 9 | Raleigh live profiles | 63 declared, 63 in the live sitemap |
| 10 | Nashville still live | 87 routes, unchanged |
| 11 | Lexington still live | 25 routes, unchanged |
| 12 | Toledo still live | 21 routes, unchanged |
| 13 | unrelated markets preserved | Cincinnati hub, category root, about, contact, methodology, robots, llms all 200 |
| 14–16 | unexpected market / profile / route changes | 0 / 0 / 0 |
| 17 | critical broken links | 0 |
| 18 | rollback target | `6aa212a8ba9f174305c0441a`, the exact release Raleigh replaced |

Raleigh is correctly absent from the homepage navigation and the category
directory, because its own market document sets `show_in_navigation` and
`show_in_sitemap` to false; its profile pages, corridors and `/go/`
interstitials are live, and the interstitial carries `noindex`.

## PHASE 8 — ROLLBACK

Not required. No rollback was performed. The recorded rollback target is
`6aa212a8ba9f174305c0441a` — the deployment Raleigh replaced — and deliberately
not that deployment's own older target, which would un-deploy Nashville.

## PHASE 11 — PERFORMANCE

    FOUNDER AUTHORIZATION PROCESSING     34 s
    FINAL PARENT CHECK                   0.5 s
    DEPLOYMENT                           53 s
    LIVE VERIFICATION                    41 s
    AUTHORIZATION_TO_VERIFIED_LIVE       5 min 36 s

    LOCAL BROAD REGRESSIONS              0
    REMOTE BROAD JOBS                    0
    UNCHANGED LIVE MARKETS REBUILT       0

## FINAL ANSWERS

     1. PARENT LIVE DEPLOYMENT ID = 6aa212a8ba9f174305c0441a
     2. PARENT RELEASE DIGEST = c12b410ec8331dbf7a50581027ad60291cac95f626de5a6a846b0d77524e0e11
     3. RALEIGH PACKAGE DIGEST = sha256:0acacc0707bd2b47da30e16b443a8a2a1d6aa20f9a48ef66a811ec463d017465
     4. FINAL AUTHORIZED CANDIDATE DIGEST = 61ca6a2ef2f170c0ede36cdce03cbf36ee3ae498371d25b79e85e30cc20dc046
     5. EXACT AUTHORIZED CANDIDATE DEPLOYED = YES
     6. BUILD OR REASSEMBLY AFTER AUTHORIZATION = NO
     7. NEW HOST DEPLOYMENT ID = 6aa593019a24fc17a07566a4
     8. LIVE MARKETS / PROFILES / ROUTES = 14 / 965 / 1148 sitemap routes (1101 on the release-index basis)
     9. RALEIGH LIVE PROFILES = 63
    10. NASHVILLE STILL LIVE = YES
    11. LEXINGTON STILL LIVE = YES
    12. TOLEDO STILL LIVE = YES
    13. UNEXPECTED MARKET / PROFILE / ROUTE CHANGES = 0 / 0 / 0
    14. LOCAL BROAD REGRESSIONS = 0
    15. REMOTE BROAD JOBS = 0
    16. UNCHANGED LIVE MARKETS REBUILT = 0
    17. AUTHORIZATION_TO_VERIFIED_LIVE WALL TIME = 5 min 36 s
    18. ALL CRITICAL LIVE CHECKS PASS = YES
    19. ROLLBACK REQUIRED = NO
    20. ROLLBACK TARGET IS EXACT PRE-RALEIGH VERIFIED RELEASE = YES
    21. RALEIGH_LIVE = YES
    22. FACTORY STATUS = RESUME_MARKET_PRODUCTION
    23. origin == HEAD = YES
    24. tree clean = YES

RALEIGH LIVE = YES
FACTORY STATUS = RESUME_MARKET_PRODUCTION
ENGINEERING PHASE COMPLETE = YES
