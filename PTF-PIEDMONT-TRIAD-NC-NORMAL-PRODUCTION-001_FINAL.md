# PTF-PIEDMONT-TRIAD-NC-NORMAL-PRODUCTION-001 — final report

Branch `worker/ptf-piedmont-triad-new-market-001`, worktree `C:\Atlas-Triad-Hardened-V1`.
Registration commit `9158e1b0`. Nothing was deployed. No factory code changed.

**Status: AWAITING_FOUNDER_AUTHORIZATION.** The founder packet is
`launch_packages/pettripfinder/markets/reports/piedmont_triad_nc_founder_authorization_packet_001.json`.

## Timeline

| | Time |
|---|---|
| Start (TRIAD_START_TIMESTAMP) | 2026-09-12T20:41:31Z |
| Authorization ready | 2026-09-12T22:01:18Z |
| **ZERO → AUTHORIZATION READY** | **1 h 19 m 47 s (EXCELLENT)** |

## Current verified live (Phase 1, re-read at Phase 17)

Host deploy `6aa5ad211250a04bc0bc6f7f` was published 2026-09-12T19:51:14Z, and it was unchanged at the recheck.

- Release digest: `606d6088460a48c7787fac6deb1befcc12e39d6ee384342cc13d8ab43ad8a815`
- Sitemap: `3c6713782208a486f96d7177663625d56606f2bc0bd6bdc353a9b7111af45e6d`. The host's sitemap sha matches it.
- Source commit: `c65e9f28b16fe77c55a0a8d2497ed18c519efeed`.
- Production: 15 markets / 1071 profiles / 1267 routes.
- Rollback parent: `6aa593019a24fc17a07566a4`.
- `release_index.live_index()` reports 0 problems.

## Geography

The Triad is treated as a multi-core metro. Membership is decided by the postal partition: 14 corridors over 34 ZIPs.

| Class | Corridors | What they cover |
|---|---|---|
| CORE | 9 | Downtown Greensboro/UNCG; Coliseum/Wendover; Friendly/NW Greensboro; PTI airport (27409 and Colfax); High Point/Jamestown; Downtown Winston-Salem; Hanes Mall; University Parkway north; Kernersville |
| CORRIDOR | 3 | South/East Greensboro on I-85, McLeansville and Whitsett; Clemmons/Lewisville; Archdale/Trinity |
| FRINGE | 2 | Oak Ridge/Summerfield; northern Forsyth on US-52 |

OUTSIDE, refused by name with their ZIPs: Lexington, Thomasville, Burlington, Graham, Mebane, Elon, Asheboro, Randleman, Mocksville, Bermuda Run/Advance, Reidsville, Eden, King and Yadkinville.

## Lanes

**Rung 0 — owned evidence**
- 33 Marriott GSO/INT routes from the committed national harvest.
- There was no owned Triad policy evidence.

**Free lanes (95 HTTP requests)**
- 20 Hilton North Carolina city pages.
- Wyndham en-us property shards.
- Drury and WoodSpring sitemaps.

**OSM**
- The Geofabrik NC extract, read by a two-pass market-local reader in 403 s: 225 lodging elements.

**Attended browser (free)**
- Hilton: 33 pages.
- Marriott: 27 pages.
- Wyndham: 40 navigations. 21 of the routes are retired and redirect to the brand's city search page.
- IHG: 15 pages.

**Static read**
- Drury: 1 page.

**Refused lanes, not fought**
- Choice: sitemap timeout, and a blank attended page.
- Hyatt: 403 / interstitial.
- ESA and Red Roof: 403.
- Motel 6: timeout.
- Best Western: structured boolean only.

**Firecrawl, Bright Data, paid discovery:** not used, $0.

**Competitor directory:** no competitor lane was run, so there is no competitor-gap evidence in this order.

## Market

| Measure | Count |
|---|---|
| Total discovered candidates | 247 |
| Registered census | 122 |
| Not admitted | 125 (59 outside market, 36 name-only, 24 identity review, 6 non-lodging) |
| Pet-friendly | 54 |
| Verified no-pets | 26 |
| Resolved / unresolved | 80 / 42 |

**Holds**
- Routing (awaiting official URL): 19
- Access blocked: 21
- Evidence (service-animal-only / WoodSpring): 2
- Identity: 0
- Geography: 0
- Paid: 0
- Founder: 0

**Corridors:** 11 of 14 have a published hotel. 4 corridor pages publish: PTI airport, Coliseum, Hanes Mall and Downtown Winston-Salem. All three cores publish.

**Coverage verdict:** REVIEW. 54 is below the helper's 60-hotel major-metro threshold, and the threshold was not tuned to pass.

## Registration

**Change class:** COMPOSITE_FRESH_MARKET_DATA_ONLY.
- 40 changed paths, all accounted for: 11 market-local, 13 registration, 16 derived, 0 shared, 0 unknown.
- All 15 proofs PASS.
- Local broad regressions requested / run: 0 / 0.
- Remote broad jobs: 0.
- Unchanged markets rebuilt: 0.

**Timing**
- REGISTRATION_TO_AUTH_READY on the release lane: 4 min 17 s.
- From the first registration write: 7 min 17 s.

**Two helper-level corrections, no factory edits**
1. FAST rule C refused the Sheraton quote "Pets are not allowed. Only certified service dogs are allowed." as SERVICE_ANIMAL_ONLY. The clean-authority helper now applies `first_party_binding.classify_quote`, and the row is held.
2. The first classification refused two helpers:
   - the geography helper, because it wrote through a dynamic path;
   - a co-location helper that opened `identity_resolutions.json` while proving 0 pairs.

   Both were fixed at the helper. No broad regression was run.

**Package and FAST**
- Package `pkg-piedmont-triad-nc-27c754bed2d60852`, reproducible YES.
- FAST 15/15 PASS, 0 unknown, 0 failed.

## Final candidate

The candidate is current live plus the Triad package. The partition was resolved through the contract. There is no assembler table edit.

| | Build A | Build B |
|---|---|---|
| Bundle sha256 | `5d6ced6ed2630d899595cef7d6c2e82dd43cfc15b56e2b48f22f0960afd4f225` | identical |
| Build time | 1009 s | 996 s |

**FINAL_CANDIDATE_REPRODUCIBLE: YES.**

**Release diff**

| | Markets | Profiles | Routes |
|---|---|---|---|
| Parent (live) | 15 | 1071 | 1267 |
| Candidate | 16 | 1125 | 1327 |
| Triad added | +1 | +54 | +60 |

- Removed: 0 markets, 0 profiles, 0 routes.
- Files: 6556 → 6885. Among existing files only `sitemap.xml` changed; nothing was added outside the Triad namespace and `/go/`.
- Unexpected market, profile and route changes: 0 / 0 / 0.
- Charlotte, Raleigh, Nashville, Lexington and Toledo keep identical profile counts.

**Digests (full)**

| Digest | Value |
|---|---|
| Parent release | `606d6088460a48c7787fac6deb1befcc12e39d6ee384342cc13d8ab43ad8a815` |
| Package | `sha256:27c754bed2d608521cd47cea8611c46efc18e2a430d5a5f290b4d8cef135e432` |
| Build input key | `sha256:dbdf939eb74d491c7e2f21c023a6ed4a3ee5da4829c37908e4d3b99b654ffd4b` |
| Intended delta | `sha256:bc6a2c87de686841a4dbfb1731b2e31a3439b231f902187dc65bf3bb075be6ca` |
| Candidate / deployment artifact | `5d6ced6ed2630d899595cef7d6c2e82dd43cfc15b56e2b48f22f0960afd4f225` |
| Sitemap | `aa857f2a275cd58ba1cbc6d9b124165abf4ca52876d20c78ae1e1fae0d83b0c0` |
| Validation receipt | `sha256:a868fb4bf4834cf4668442484bb2baa855856c250704d1fb3ff093a4498694d5` |

**Rollback:** deployment `6aa5ad211250a04bc0bc6f7f`, release `606d6088460a48c7787fac6deb1befcc12e39d6ee384342cc13d8ab43ad8a815`.

**Staged artifacts:** `C:\t\tri1a` and `C:\t\tri1b`. Staged participation sha: `b7c6311da2e9761e7b6e64b5aaf08be2fd48bdee57491d73bda18062d6ae71ae`.

## Performance

| Stage | Time |
|---|---|
| Geography | 3 min |
| Census (OSM 7 min, brand 11 min, overlapping) | ~13 min |
| Attended browser | ~24 min |
| Identity and policy adjudication | ~6 min |
| Registration → auth-ready | 4–7 min |
| FAST | 51 s |
| Whole-site candidate ×2, in parallel | 16.5 min |

**Bottleneck:** the whole-site candidate assembly, about 1000 s per build, followed by the attended browser pass.

- Provider cost: $0.
- Founder active time: 0.
- Peak memory: not instrumented. The assembler processes were about 163 MB working set each at the 21:54 sample.
