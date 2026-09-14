# PTF-CHARLESTON-SC-REGISTER-RESEAL-AND-AUTHORIZATION-PREP-002 — FINAL

**Charleston, South Carolina is registered against the current verified live release.** The fresh package passed FAST 15/15, and the candidate was built twice with identical output. **Status: AWAITING_FOUNDER_AUTHORIZATION.**

Nothing was deployed, and no authorization was created.

Founder packet: `atlas-dashboard/launch_packages/pettripfinder/markets/reports/charleston_sc_founder_authorization_packet_002.json`

## Phase 1 — CURRENT VERIFIED LIVE

The live state was read from the host, the canonical deployment record and the live-state reader at 19:17:27Z, and re-read at 19:27:12Z and 20:02:39Z. All three reads were identical.

| Field | Value |
|---|---|
| HOST DEPLOYMENT ID | `6aa83f1bdbe7b7ba24cd4f2e` (state ready) |
| LIVE RELEASE DIGEST | `a81020258571f09d93eea746d3d5d195a12d87aa0ce8d98106a997466a96443d` |
| SOURCE COMMIT | `76fce8acf6f0abeb5ce4bef1bd87037f75c10ee7` (launch commit `dc0fcd01`) |
| SITEMAP DIGEST | `b86f414c6233d84557568ee854754103d675f09b593e149d6107facbb7f95790` |
| MARKETS / PROFILES / ROUTES | 24 / 1593 / 1849 |
| PARTICIPATING | Richmond, Atlanta, Jacksonville, Boone–Blowing Rock, Greenville, Fayetteville, Asheville, Wilmington, Piedmont Triad, Charlotte, Raleigh, Nashville, Lexington, Toledo and 10 earlier markets |
| ROLLBACK TARGET | `6aa7f125a91c73ba2363139e` |
| VERIFICATION STATUS | VERIFIED |

## Phases 2–4, 7 and 8 — Preflight and lineage

- **Lineage (Phase 8).** `dc0fcd01` was merged with no conflicts, as merge commit `33debd03`. The merged tree differs from `dc0fcd01` only in Charleston paths.
- **Source inputs (Phase 2).** All counts match the source-ready state: 440 discovered / 186 census / 82 PF / 44 no-pets / 126 resolved / 60 unresolved. Holds match too, and every census identity is accounted exactly once. The source-ready change set touched 0 non-Charleston paths.
- **Geography (Phase 3).** Kiawah Island and Seabrook Island (29455) remain OUTSIDE, with 110 rows reserved for `kiawah-seabrook-sc`. Johns Island, Isle of Palms and Folly Beach are FRINGE, and all 36 ZIPs are unchanged. The 45 non-hotel exclusions (vacation rental, villa, condo) stand.
- **Hilton vacation-club properties (Phase 4).** All three **stay FOUNDER_HOLD**.
  - Their own hilton.com pages were read again. They show brand code GV and a `resEnabled: true` flag, but no public nightly rate or availability. Nothing on the pages proves the stay needs no ownership or membership.
  - Lodge Alley Inn: FOUNDER_HOLD.
  - King 583: FOUNDER_HOLD.
  - Liberty Place: FOUNDER_HOLD. It is Hilton Club, the members' tier.
  - All three state "Service animals only", so admitting them would publish nothing.
- **Shadow package safety (Phase 7).**
  - `pkg-charleston-sc-b2987ee1c2bccb01` is SHADOW_UNTIL_REGISTERED and bound to the Atlanta parent, so FAST rule N fails it now. It is absent from `markets/packages/`, has no eligible receipt and is named by no authorization. It is **not production-selectable**.
  - The superseded seals `a2ac698d` and `87312e0f` exist nowhere on disk.

## Phases 5–6 — Holds

| Hold | Result |
|---|---|
| 406 Sigma Dr: Hilton Garden Inn (chsgigi) + Homewood Suites Summerville (chssmhw) | **RESOLVED.** `co_located_distinct` = DISTINCT, so one `same_campus_distinct_entity` DATA row (`res-charleston-sc-hilton-garden-inn-summerville`) was added to `identity_resolutions.json`. Both PF records are released. |
| 560 King St: Hyatt House (chsxh) + The Lowline (chszh) | **KEPT HELD.** The shared proof returns INSUFFICIENT because it reads no Hyatt code. No checker change and no ruling. |
| 18 FAQ-page evidence holds | **KEPT HELD.** No existing contract binds a sibling page, so no exception was created. |

## Phases 9–12 — Registration, final authority, package, FAST

- **Chain.** The Charleston chain was repointed to its registered paths. The registered census, market document, partition and shards equal the source-ready copies, apart from status and note text.
- **Registration steps.**
  - `market_registration_cli --write`
  - `build_global_authority --write` and `--check` (all generated artifacts match the shards)
  - The release contract (0 disagreements; `verify_all` finds 26 markets with no problems)
  - `registration_release_lane register`, then `seal`
- **Change class: COMPOSITE_FRESH_MARKET_DATA_ONLY.**
  - Changed paths: 82 / 82 accounted.
  - Buckets: 23 acquisition, 14 registration, 45 derived, 0 shared behavior, **0 unknown**.
  - All 15 proofs PASS: change_set, market_local_zone, discovery_config, registration_input, identity_resolutions, participation, release_contract, build_closure, derived_globals, sealed_package, fast_receipt, expected_release, identity_routes, market_state_pin, release_integrity.
  - FULL_REGRESSION_REQUIRED: NO. Local broad requested 0, local broad run 0, remote broad required 0, unchanged markets rebuilt 0.
- **FINAL AUTHORITY.** Census 186, PF **84**, no-pets 44, resolved **128**, unresolved **58**.
  - Only one hold changed: the Summerville pair (PF +2, evidence holds 55 → 53).
  - Publishable corridors: 7 of 14. Summerville's PF count went from 6 to 8.
- **Package.** `pkg-charleston-sc-59d606c736e34ee5`
  - Digest `sha256:59d606c736e34ee589dfde7252e480ddc236b178c917c95ebce0c80f72914381`
  - Build input key `sha256:549988b6df1d38a8a74054bcbfb1a4a1178b2d4be6d14804b2f016436bd292e9`
  - Intended delta `sha256:d4aba851da6d39811b1df895a99fd1abacd4ba2e1b3c7d49c2511fafd9d222e9`
  - Receipt `sha256:d99f4af6d7c13aaa70101fe07501d32c689c6d59b4762c607eb84789e1f59cb0`
- **FAST.** 15/15 PASS, 0 unknown, 0 failed, 103.6 s.

## Phases 13–17 — Candidate

- **Parent recheck.** Before composition, the host deploy, release digest, profiles and routes were identical. **STALE_PARENT = NO.**
- **Composition.** Current live plus the Charleston package, using the generic registered-market partition resolution. There was no assembler edit.
- **Builds.** Two independent whole-site builds from `7f286115` took 1818 s each, running in parallel. Both are **byte-identical**.

| Field | Value |
|---|---|
| Parent / candidate | 24 / 1593 / 1849 → **25 / 1677 / 1942** |
| Charleston additions | **+84 profiles, +93 sitemap routes, +92 release-index routes** |
| Removed | 0 markets, 0 profiles, 0 routes |
| Unexpected market / profile / route / file changes | 0 / 0 / 0 / 0 |
| Live files | 9736 of 9737 unchanged; only `sitemap.xml` changed |
| Added files | 93 in the market namespace + 419 /go/ interstitials |
| Every live market | Profile counts identical, including the 14 named live markets |
| Queued markets | Outer Banks, Savannah, Hickory, Banner Elk, Pinehurst and Detroit all stay non-live |

The sitemap has one more route than the release index: `/pet-friendly-hotels/charleston-sc/policy-comparison/`. The assembler emits it into the sitemap, and the release index does not declare it.

| Digest | Value |
|---|---|
| FINAL CANDIDATE | `1c61aeda2a1b27878824c96b2189f0104886783a8dc575f51b8f1e1289c89914` |
| DEPLOYMENT ARTIFACT | `1c61aeda2a1b27878824c96b2189f0104886783a8dc575f51b8f1e1289c89914` (`C:\t\chs2a\site`) |
| SITEMAP | `3f1c10fd23c54f12e83f5709921ec74a7eea7217d6c0c11f73e1012ee94e676e` |
| Independent rebuild | `1c61aeda2a1b27878824c96b2189f0104886783a8dc575f51b8f1e1289c89914` |

**Determinism.** A clean worktree at `7f286115` rebuilt the chain with zero content difference.
- All 7 package inputs use LF line endings and equal their committed blobs.
- An exact reseal from the clean checkout gives `59d606c7…` twice.
- The CRLF discovery config is not a package input, so it does not change the release bytes.
- The old shadow package is not in the registered store.
- The Homewood identity fix is deterministic: both Summerville identities are admitted with distinct codes, and the one ruling reproduces.

## Timing

| Step | Time (UTC) |
|---|---|
| Order start | 19:15:24Z |
| First registration write | 19:21:12Z |
| AUTHORIZATION_READY | 19:26:05Z |
| **REGISTRATION_TO_AUTH_READY** | **4 min 53 s** |

- Seal + FAST: 119.9 s.
- Classification: 45 s.
- Candidate builds: 1818 s.

## Rollback

- Rollback deployment: `6aa83f1bdbe7b7ba24cd4f2e` (Richmond-live).
- Rollback release digest: `a81020258571f09d93eea746d3d5d195a12d87aa0ce8d98106a997466a96443d`.

## Not done

- No founder authorization.
- No production gate.
- No host deployment.
- No factory, classifier, assembler, schema or test change.
- No broad regression.
