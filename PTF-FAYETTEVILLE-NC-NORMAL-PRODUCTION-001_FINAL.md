# PTF-FAYETTEVILLE-NC-NORMAL-PRODUCTION-001 — final report

Branch `worker/ptf-fayetteville-nc-new-market-001`, worktree `C:\Atlas-Fayetteville-Hardened-V1`.
Registration commit `c4db424ba6b4351158708889c803643be9edc2a3`; classification + readiness commit `db5fce66`.

- Nothing was deployed.
- No factory or shared code changed.
- **Status: AWAITING_FOUNDER_AUTHORIZATION.** The founder packet is `launch_packages/pettripfinder/markets/reports/fayetteville_nc_founder_authorization_packet_001.json`.

## Timeline (UTC)

| | Time |
|---|---|
| FAYETTEVILLE_START_TIMESTAMP | 2026-09-13T03:27:50Z |
| Registration first write | 03:57:12Z |
| Release lane AUTHORIZATION_READY | 03:59:27Z (31 m 37 s from start) |
| Candidate reproduced, packet written | 04:21:33Z |
| **ZERO → AUTHORIZATION READY** | **53 m 43 s (EXCELLENT)** |
| REGISTRATION_TO_AUTH_READY | 2 m 15 s from the first registration write (1 m 45 s from `register`) |

## Current verified live (parent)

Read at 03:28:47Z, re-read at 04:00:20Z and 04:18:04Z; unchanged at every read.

| Field | Value |
|---|---|
| Host deployment | `6aa60a3e018fd6b1b9a40450` (ready) |
| Live release digest | `d98a24038ef25df4b481e71b8436377ff01abc2bc80a11de2fe7222df9dadb36` |
| Source commit | `5c3264650962cf726700ccda4962422d96dadad1` |
| Sitemap digest | `6a33f1e53a094f934f1175bd21c58e77675820ab18b593288ab472c55152a699` (host sitemap sha matches) |
| Markets / profiles / routes | 18 / 1195 / 1408 |
| Participants | asheville, charlotte, cincinnati, cleveland-akron-canton, columbus, dayton, grand-rapids-holland, indianapolis, lexington, louisville, milwaukee, nashville, piedmont-triad, pittsburgh, raleigh, st-louis, toledo, wilmington |
| Rollback parent | `6aa5e2623de160fcdf416577` |
| Release index problems | 0 |
| Verification | VERIFIED |

## Geography

Membership is the property's own postal code joined to a 9-corridor, 12-ZIP partition.

| Class | Corridors |
|---|---|
| CORE | Downtown / Haymount (28301, 28305); Cross Creek Mall / Skibo / Raeford Rd / Bragg Blvd (28303, 28304, 28314); FAY Airport / Gillespie / I-95 south (28306); North Fayetteville (28311); I-95 Central / Eastover / Vander (28312); Spring Lake / Fort Liberty (28390); Hope Mills (28348) |
| CORRIDOR | Wade / I-95 North (28395) |
| FRINGE | Raeford (28376) |

**OUTSIDE, refused by name:** Fort Liberty on-post 28307 / 28310 and Pope AAF 28308 (MILITARY_GOVERNMENT_NONPUBLIC); Southern Pines / Pinehurst / Aberdeen (golf-resort market, never absorbed); Sanford; Lumberton / St. Pauls; Dunn / Erwin / Godwin (I-95 alone admits nothing); Stedman (no inventory); Clinton; Lillington; Elizabethtown.

**Military rule:** IHG Army Hotels (Forrestal Hall / Delmont House), Airborne Inn and Landmark Inn are on-post Army lodging behind the gate and are refused as MILITARY_GOVERNMENT_NONPUBLIC. Off-post commercial hotels serving Fort Liberty are admitted normally.

## Lanes

- **Rung 0 (owned):** 17 Marriott FAY routes from the committed national harvest. Owned Fayetteville identities: 0. Owned policy evidence: 0. Cross-market collisions: 0 (Raleigh's hits are "Fayetteville Street/Road" addresses).
- **OSM** (Geofabrik NC extract, 460 s): 162 lodging elements in the observation box.
- **Brand lane (plain client, 88 requests):** Hilton 15 city pages (36 codes), Wyndham sitemap (31 NC routes), Sonesta / Drury / WoodSpring / ESA / Hilton sitemaps answered with no route; Choice and Motel 6 timed out; IHG, Best Western, Red Roof, Hyatt, Radisson, Omni 403.
- **Attended browser (free):** Hilton 46 pages (same-origin), Marriott 9 navigations (StudioRes route in a redirect loop), Wyndham 16 routes (7 live, 7 retired to brand search, 2 search pages), IHG 5 destination pages → 7 codes, Red Roof same-origin sitemap → 2 property pages, G6 same-origin sitemap → Motel 6 + Studio 6 (amenity chip only), Choice blank page.
- **Static first-party:** ESA city page + 5 property pages; WoodSpring POI page (no Fayetteville property); Fayetteville CVB (listing client-rendered).
- **Web search:** 4 queries for routes and competitor names only.
- **Firecrawl, Bright Data, paid discovery:** not used. **$0.**

## Market

| Measure | Value |
|---|---|
| Total discovered candidates | 194 |
| Registered census | 56 |
| Not admitted | 138: 75 outside market (incl. 3 military nonpublic, 1 geography hold), 51 name-only, 11 identity review, 1 non-lodging |
| Pet-friendly | 26 |
| Verified no-pets | 10 |
| Resolved / unresolved | 36 / 20 |

**Holds (over the census)**

| Class | Count | Rows |
|---|---|---|
| Identity | 0 | (3 addressed in-market review rows are outside the census: Econo Lodge 1952 Cedar Creek, Quality Inn Raeford, Super 8 Spring Lake retired route) |
| Routing | 12 | 11 independents / weekly motels with no first-party site + Everhome Suites |
| Access-blocked | 5 | Comfort Inn I-95, Sleep Inn, Comfort Inn Near Ft. Bragg, Sleep Inn & Suites Spring Lake, Red Lion (now Choice Quality Inn) |
| Evidence | 3 | DoubleTree (service animals only), Super 8 (fee only), Studio 6 (amenity chip only) |
| Geography | 1 | Days Inn & Suites 1720 Skibo Rd — own page and map state 28308; not in census |
| Paid | 0 | |
| Founder | 0 | |

**Corridors (census / PF / no-pets)**

| Corridor | Census | PF | No-pets |
|---|---|---|---|
| Downtown / Haymount | 3 | 1 | 0 |
| Cross Creek / Skibo / Bragg | 26 | 14 | 5 |
| FAY Airport / south | 3 | 1 | 0 |
| North Fayetteville | 2 | 1 | 1 |
| I-95 Central / Eastover | 16 | 7 | 2 |
| Spring Lake / Fort Liberty | 4 | 2 | 1 |
| Hope Mills | 1 | 0 | 1 |
| Wade / I-95 North | 1 | 0 | 0 |
| Raeford | 0 | 0 | 0 |

Two corridor pages publish: Cross Creek / Skibo and I-95 Central / Eastover.

**Required coverage slices (census / PF / no-pets)**

| Sub-area | Census | PF | No-pets |
|---|---|---|---|
| Downtown | 3 | 1 | 0 |
| Cross Creek / Skibo | 21 | 13 | 5 |
| Fort Liberty corridor (Bragg Blvd) | 5 | 1 | 0 |
| Spring Lake | 4 | 2 | 1 |
| Hope Mills | 1 | 0 | 1 |
| FAY Airport | 3 | 1 | 0 |
| I-95 North (exits 55–61) | 3 | 0 | 0 |
| I-95 Central (exits 49–52) | 14 | 7 | 2 |
| I-95 South (exits 44–46) | 0 | 0 | 0 |
| North Fayetteville | 2 | 1 | 1 |

**Competitor gap:** Embassy Suites, Hampton Inn & Suites, Tru I-95, Red Roof Fort Bragg, Travelodge, Studio 6 EXACT; Home2 "Fort Liberty" ALIAS; Motel 6 REVIEW (co-located with Studio 6 at 3719 Bragg Blvd); Red Lion, 3 WoodSprings (now ESA), Quality Inn Sigman (now Hawthorn), Wingate (now HIE), Country Inn Spring Lake (now Spark) REBRAND; 3 on-post lodgings MILITARY/GOVERNMENT NONPUBLIC; Barrington House NON_HOTEL. **True missing qualifying hotels: 0.**

**Helper-level corrections (market-local, no factory edits):** Travelodge's "2 pets for no charge; additional pets $20/night" no longer publishes $20 as the fee; the on-post military names are refused before the house-name rule; the Wyndham retired-flag rule reaches only map-only rows.

## Registration

- **Change class:** COMPOSITE_FRESH_MARKET_DATA_ONLY on the first classification.
- 40 changed paths accounted: 11 market-local, 13 registration, 16 derived, 0 shared, **0 unknown**.
- All 15 proofs PASS (change set, market-local zone, discovery config, registration input, identity resolutions, participation, release contract, build closure, derived globals, sealed package, FAST receipt, expected release, identity routes, market-state pin, release integrity).
- Local broad requested / run: 0 / 0. Remote broad required: 0. Unchanged markets rebuilt: 0.
- Package `pkg-fayetteville-nc-37769ac1dcf90058`, reproducible YES.
- FAST 15/15 PASS in 29.1 s, 0 unknown, 0 failed.

## Final candidate

Current live + the Fayetteville package, partition resolved from the contract (no assembler edit). **FINAL_CANDIDATE_REPRODUCIBLE: YES** — builds A and B identical (1036 s, parallel).

| | Markets | Profiles | Routes |
|---|---|---|---|
| Parent | 18 | 1195 | 1408 |
| Candidate | 19 | 1221 | 1438 |
| Fayetteville added | +1 | +26 | +30 sitemap basis; +29 release-index basis |

The sitemap delta is 26 profiles + 2 corridor pages + the market hub + `policy-comparison/`; the release index does not model the comparison page, so it is one less.

- Removed: 0 markets, 0 profiles, 0 routes. Files 7315 → 7475; only `sitemap.xml` changed among existing files.
- Unexpected market / profile / route / file changes: 0 / 0 / 0 / 0.
- Every live market keeps its profile count (Asheville 41, Wilmington 29, Triad 54, Charlotte 106, Raleigh 63, Nashville 79, Lexington 20, Toledo 17, …). Detroit not included.

**Digests (full)**

| Digest | Value |
|---|---|
| Parent release | `d98a24038ef25df4b481e71b8436377ff01abc2bc80a11de2fe7222df9dadb36` |
| Package | `sha256:37769ac1dcf9005829e5d268cd24935a61b6aef439441a75feb516144f47548b` |
| Build input key | `sha256:3962c46be301cf86f44e8101e80081c22ce24855b9254226ac99d1400f2b1720` |
| Intended delta | `sha256:35ad3b350d55a8506f3bff5ac8f93bbdca782d03a5d0173c7b1253e7896e5dfd` |
| Candidate / deployment artifact | `e6c669cf14980efc44eaee4799e060e28888cac510498310595fcd125939f965` |
| Sitemap | `3cb2fc6d20d6fda185345d8d25b30e5489099959b48c516dfa6ae79668b9a99f` |
| Validation receipt | `sha256:e593f00e79eaa6af7ec639c9a8cd556cc4cd713b47cbf9255176a4e7eccffbf6` |

**Rollback:** deployment `6aa60a3e018fd6b1b9a40450`, release `d98a24038ef25df4b481e71b8436377ff01abc2bc80a11de2fe7222df9dadb36`.

**Staged artifacts:** `C:\t\fay1a`, `C:\t\fay1b`. Staged participation sha `71bf502ca9651a7433118cb13d25c2a90caaae5f0802f9660bbc2871dd2a2fd8`.

## Performance

| Stage | Time |
|---|---|
| Geography | ~4 min |
| Census (OSM 7.7 min, brand lane ~7 min, overlapping) | ~8 min |
| Attended browser + static reads | ~14 min |
| Identity and policy adjudication | ~7 min |
| Registration → auth-ready | 2.3 min |
| FAST | 29.1 s |
| Whole-site candidate ×2 in parallel | 17.3 min |

**Bottleneck:** the whole-site candidate assembly (~1036 s). Provider cost $0. Founder active time 0. Peak memory not instrumented.
