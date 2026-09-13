# PTF-ASHEVILLE-NC-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-002 — final report

**ASHEVILLE IS LIVE.** Production is 18 markets / 1195 profiles / 1408 routes on host deployment `6aa60a3e018fd6b1b9a40450`.

Branch `worker/ptf-asheville-nc-new-market-001`. Source commit `5c3264650962cf726700ccda4962422d96dadad1`.

## Timeline

| | Time |
|---|---|
| Founder authorization received | 2026-09-13T02:21:30Z |
| Authorization written, gate opened | 02:27:29Z (processing 158.5 s) |
| Final parent check / byte check | 4.5 s / 3.7 s |
| Host deploy | 02:27:45Z → 02:28:28Z (42.1 s) |
| Live verification | 33.0 s, 27/27 PASS |
| **AUTHORIZATION → VERIFIED LIVE** | **9 min 23 s** |
| ZERO → AUTHORIZATION READY | 1 h 04 m 51 s |
| **ZERO → VERIFIED LIVE (active)** | **1 h 14 m 14 s** |
| Wall clock including founder decision wait (35 m 43 s) | 1 h 49 m 57 s |

## Phase 1 — final seal only (8/8 PASS)

The superseded package `pkg-asheville-nc-08ac409eb44a3776` and its receipt, plus the superseded receipt `…af7b78b6abf82d8a-efe395717c23277c`, were checked against every place a stale seal could live:
- **Commits:** neither was ever committed in any commit.
- **References:** neither is named in the release contract, the founder packet or any file at HEAD.
- **Selectable copies:** neither is on disk or in the candidate worktree.

The market-state pin schema records counts, not a digest. Its Asheville block equals the final package's counts (96 / 41 / 15). The committed lane report names the final package `sha256:af7b78b6abf82d8a7624afc9bf2f475dbac64f134e005a590679ed3a681ca0c1` as the seal that wrote it, and exactly one commit touched the pin.

**SUPERSEDED PACKAGE SELECTABLE = NO.**

## Parent (re-read before authorization and immediately before deploy)

| Field | Value |
|---|---|
| Host deployment | `6aa5e2623de160fcdf416577` (ready) |
| Live release | `a0f92c7fd5e052e0cf03ad8a9cfacfe9968547ad13dd546829f42ce4f39dcb05` |
| Source commit | `7709953fac20326181abb04d5d4f2f33eee869c2` |
| Sitemap | `9344e961269df8fa6143a7ba21cb2734b3369d25294928b38d70bab037a963c8` |
| Markets / profiles / routes | 17 / 1154 / 1361 |
| Rollback target of the parent | `6aa5ce23d51fa8544146ebac` |
| STALE_PARENT | NO |

## Authorization inputs (read from the committed packet; all agree)

| Input | Value |
|---|---|
| Package | `sha256:af7b78b6abf82d8a7624afc9bf2f475dbac64f134e005a590679ed3a681ca0c1` |
| Build input key | `sha256:441b35b68fc4aee6e2cb3d6efa8543fe3636addf1a87010824d95829351118fa` |
| Intended delta | `sha256:ba28aa005a5def9528dd1e26373548e9e3690e37b13e1a83748f0dd31881b527` |
| Validation receipt | `sha256:c717db2ac1fadd61af07303fcce3e30540e928b66054a09e0fd8f4d15b862534` |
| Candidate = deployment artifact | `d98a24038ef25df4b481e71b8436377ff01abc2bc80a11de2fe7222df9dadb36` |
| Candidate sitemap | `6a33f1e53a094f934f1175bd21c58e77675820ab18b593288ab472c55152a699` |

- Package reproducible: YES.
- Final candidate reproducible: YES.
- FAST: 15/15, 0 unknown, 0 failed.

## Release delta

- **Added:** 1 market and 41 profiles.
- **Sitemap routes:** +47, from 1361 to 1408.
- **Release-index routes:** +46.
- **The one-route difference is mechanically `/pet-friendly-hotels/asheville-nc/policy-comparison/` and nothing else.** The release index does not model the comparison page.
- **Removed and unexpected:** 0 markets, 0 profiles and 0 routes removed. Unexpected market, profile and route changes are 0 / 0 / 0. Only `sitemap.xml` changed among the parent's files.
- **Preserved:** every live market's profile count, including Wilmington, Piedmont Triad, Charlotte, Raleigh, Nashville, Lexington and Toledo. Detroit does not participate.

## Authorization, gate, deploy

- **Authorization:** `ptf-auth-asheville-002-d98a24038ef2`, bound to the parent, the final package, the intended delta and the candidate/artifact digests. Its lifecycle ran AUTHORIZED → DEPLOYED.
- **Participation:** exactly one row flipped. The after-sha `0894c004b95c9fc070ecddb5c3ef1cf9ebc17853033da74460dc3b96443d12b3` equals the bytes the candidate was composed under.
- **Gate:** opened for `asheville-nc` only. The loader refused detroit-ann-arbor-mi, wilmington-nc, piedmont-triad-nc, charlotte-nc and unnamed-market while it was open.
- **Deploy:** the existing `C:\t\ash1a\site` was re-hashed against the authorization and deployed with `netlify deploy --prod --no-build`. No build, reassembly, re-seal or policy change happened after authorization.

## Live verification (27/27 PASS)

- **Candidate and host:** the live sitemap hashes to the authorized candidate, and the host deployment id matches.
- **Every live route:** all 1408 routes fetched, 0 non-200.
- **Asheville routes:** the hub, comparison page and sampled profiles all return 200 (the profile samples are below). The market's 47 sitemap entries match the artifact, and 41 profiles are live.
- **Other markets:** Wilmington, Triad, Charlotte, Raleigh, Nashville, Lexington and Toledo are still live. Every other market's fragment routes are identical between the parent artifact and live.
- **Rollback target:** the exact pre-Asheville Wilmington-live release, `6aa5e2623de160fcdf416577` / `a0f92c7fd5e052e0cf03ad8a9cfacfe9968547ad13dd546829f42ce4f39dcb05`.

Sampled profiles, all returning 200:
- Downtown
- Biltmore Village
- Tunnel Road / East Asheville
- West Asheville
- South Asheville (Biltmore Park)
- AVL airport / Fletcher
- Black Mountain

Rollback required: NO.

**Two checker corrections before authorization, neither a site defect:**
1. The Phase 4 checker converted from the Wilmington launch still expected 29 profiles. Every measured value matched Asheville's 41.
2. Seal check 6 first looked for a digest inside a count-only pin schema.

## Recorded live state

- Deployment record `ptf-deploy-asheville-002-6aa60a3e018fd6b1b9a40450`.
- `tests/pettripfinder/pins/deployment_state.json` live and source moved to the Asheville release, rollback `6aa5e2623de160fcdf416577`.
- Receipt `launch_packages/pettripfinder/markets/reports/asheville_nc_live_verification_002.json`.
- `release_index.live_index()` now reads `6aa60a3e018fd6b1b9a40450` / `d98a24038ef25df4b481e71b8436377ff01abc2bc80a11de2fe7222df9dadb36`, 18 / 1195 / 1408, 0 problems.

The gate is closed: ENABLED = NO, allowlist empty, and the entry was moved to `previously_consumed`.

**Totals for this order:**
- Local broad regressions: 0. Remote broad jobs: 0. Unchanged live markets rebuilt: 0.
- Factory code changed: NO. Factory status: RESUME_MARKET_PRODUCTION.
