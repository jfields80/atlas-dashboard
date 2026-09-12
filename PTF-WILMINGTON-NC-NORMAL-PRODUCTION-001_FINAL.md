# PTF-WILMINGTON-NC-NORMAL-PRODUCTION-001 — final report

Branch `worker/ptf-wilmington-nc-new-market-001`, worktree `C:\Atlas-Wilmington-Hardened-V1`.
Registration commit `7709953fac20326181abb04d5d4f2f33eee869c2`.

- Nothing was deployed.
- No factory or shared code changed.
- **Status: AWAITING_FOUNDER_AUTHORIZATION.** The founder packet is `launch_packages/pettripfinder/markets/reports/wilmington_nc_founder_authorization_packet_001.json`.

## Timeline

| | Time |
|---|---|
| WILMINGTON_START_TIMESTAMP | 2026-09-12T22:23:52Z |
| Registration first write | 22:55:25Z |
| Release lane AUTHORIZATION_READY | 23:01:04Z |
| Candidate reproduced, packet written | 23:23:07Z |
| **ZERO → AUTHORIZATION READY** | **59 m 15 s (EXCELLENT)** |
| REGISTRATION_TO_AUTH_READY | 5 m 39 s from the first registration write (4 m 15 s from `register`) |

## Current verified live

Read at 22:24:56Z and re-read at 23:01:42Z and 23:20:12Z. It was unchanged at every read.

| Field | Value |
|---|---|
| Host deployment | `6aa5ce23d51fa8544146ebac` (ready) |
| Live release digest | `5d6ced6ed2630d899595cef7d6c2e82dd43cfc15b56e2b48f22f0960afd4f225` |
| Source commit | `9158e1b0d23a037292f05e6d74d63219c81f584f` |
| Sitemap digest | `aa857f2a275cd58ba1cbc6d9b124165abf4ca52876d20c78ae1e1fae0d83b0c0` (the host sitemap sha matches) |
| Markets / profiles / routes | 16 / 1125 / 1327 |
| Rollback parent | `6aa5ad211250a04bc0bc6f7f` |
| Release index problems | 0 |
| Verification | VERIFIED |

## Geography

Membership is decided by the property's own postal code. The market has 9 corridors over 11 ZIPs.

| Class | Corridors |
|---|---|
| CORE | Downtown (28401); Midtown / UNCW (28403); ILM airport / Market St / Mayfaire (28405); Wrightsville Beach (28480); Carolina Beach / Kure Beach (28428, 28449) |
| CORRIDOR | Monkey Junction (28409, 28412); Ogden / Porters Neck (28411); Leland / Belville (28451) |
| FRINGE | Castle Hayne (28429) |

**Leland is admitted as CORRIDOR.** Its hotels brand themselves to Wilmington: "Tru by Hilton Leland Wilmington" and "Holiday Inn Express Leland - Wilmington Area".

**OUTSIDE, refused by name:**
- Hampstead
- Topsail Beach / Surf City / Holly Ridge
- Sneads Ferry
- Southport / Bald Head Island / Boiling Spring Lakes
- Oak Island
- Bolivia
- Winnabow
- Holden Beach
- Shallotte
- Ocean Isle Beach
- Sunset Beach
- Carolina Shores / Calabash
- Burgaw
- Rocky Point
- Wallace

## Lanes

**Rung 0 (owned):**
- 14 Marriott ILM routes from the committed national harvest.
- No owned Wilmington identities and no owned policy evidence.

**Free lanes:**
- Hilton city pages.
- The Wyndham sitemap.
- 87 brand requests.
- OSM (Geofabrik NC extract, market-local two-pass reader, 502 s): 112 lodging elements.

**Attended browser (free):**
- Hilton: 20 pages.
- Marriott: 14 pages.
- Wyndham: 4 live properties. The brand's own search lists only 4, and 6 sitemap routes are retired and redirect to the search page.
- IHG: 7 pages.
- Extended Stay America: 1 page.
- 2 independents that refused the plain client.

**Independent first-party static lane:** 26 sites, 49 requests.

**Refused lanes, not fought:**
- Choice: sitemap timeout and a blank attended page.
- Best Western: sitemap 403 and an attended error page.
- Red Roof, Radisson and Hyatt: sitemap 403.
- Motel 6: sitemap timeout.
- Several independents: 403 or an interstitial.

**Firecrawl, Bright Data, paid discovery:** not used. $0.

## Market

| Measure | Value |
|---|---|
| Total discovered candidates | 131 |
| Registered census | 73 |
| Not admitted | 58: 32 name-only, 16 outside market, 5 identity review, 5 non-lodging / vacation rental |
| Pet-friendly | 29 |
| Verified no-pets | 14 |
| Resolved / unresolved | 43 / 30 |

**Holds**

| Class | Count |
|---|---|
| Identity | 0 |
| Routing | 10 |
| Access-blocked | 12 |
| Evidence | 8 (5 service-animal-only Hilton, 2 first-party conflicts, 1 silent) |
| Geography | 0 |
| Paid | 0 |
| Founder | 0 |

**Corridor counts (census / PF / no-pets)**

| Corridor | Census | PF | No-pets |
|---|---|---|---|
| Downtown | 11 | 5 | 2 |
| Midtown / UNCW | 15 | 5 | 4 |
| ILM / Mayfaire | 18 | 9 | 2 |
| Wrightsville Beach | 6 | 0 | 4 |
| Carolina / Kure Beach | 14 | 4 | 1 |
| Monkey Junction | 3 | 2 | 0 |
| Ogden / Porters Neck | 2 | 1 | 1 |
| Leland | 4 | 3 | 0 |
| Castle Hayne | 0 | 0 | 0 |

Three corridor pages publish: Downtown, Midtown and ILM/Mayfaire.

**Sub-areas (census / PF / no-pets)**

| Sub-area | Census | PF | No-pets |
|---|---|---|---|
| Wilmington proper | 27 | 11 | 6 |
| ILM airport | 12 | 3 | 2 |
| Mayfaire / Wrightsville corridor | 10 | 8 | 1 |
| Wrightsville Beach | 6 | 0 | 4 |
| Carolina / Kure Beach | 14 | 4 | 1 |
| Leland | 4 | 3 | 0 |

Every Wrightsville Beach hotel read refuses pets:
- Trailborn Surf and Sound (the former Blockade Runner)
- Holiday Inn Resort Lumina
- Sandpeddler
- The Surf Suites

**Vacation-rental and non-lodging exclusions:**
- One South Lumina (condo rental)
- The Cottage
- Mill Creek Apartments
- Hell's Kitchen (bar)
- The Beach House

Shell Island Resort is admitted as a condo-hotel operated as a hotel.

**Competitor gap (BringFido leads, names only):**
- SeaBirds: REBRAND of the map's Moran Motel, now published.
- Carolina Beach Inn: EXACT match.
- Savannah Inn: ALIAS.
- Carolina Beach Motel: TRUE MISSING identity, left as a routing lead.

## Registration

**Change class:** COMPOSITE_FRESH_MARKET_DATA_ONLY, selected on the first classification.
- 42 changed paths, all accounted for: 12 market-local, 13 registration, 17 derived, 0 shared, 0 unknown.
- All 15 proofs PASS.
- Local broad requested / run: 0 / 0.
- Remote broad jobs: 0.
- Unchanged markets rebuilt: 0.

**Package and FAST**
- Package `pkg-wilmington-nc-0720bc825aab9057`, reproducible YES.
- FAST 15/15 PASS in 36.0 s, 0 unknown, 0 failed.

**Helper-level corrections (no factory edits)**
1. **Shared operator phone.** Carolina Beach Inn and SeaBirds share one phone number, which merged two buildings. A phone now overrides a street disagreement only when the names share chain vocabulary.
2. **Trademark sign.** `seal` refused KEY_NAME_MISMATCH because of the "™" in ARRIVE's name. Trademark signs are now stripped at the census door.

## Final candidate

The candidate is current live plus the Wilmington package. The partition was resolved through the contract, with no assembler edit.

**FINAL_CANDIDATE_REPRODUCIBLE: YES.** Build A and build B produced identical bytes. The two builds ran in parallel in 1058 s.

**Release diff**

| | Markets | Profiles | Routes |
|---|---|---|---|
| Parent | 16 | 1125 | 1327 |
| Candidate | 17 | 1154 | 1361 |
| Wilmington added | +1 | +29 | +34 (sitemap basis; 33 on the release-index basis) |

- Removed: 0 markets, 0 profiles, 0 routes.
- Files: 6885 → 7064. Only `sitemap.xml` changed among existing files.
- Unexpected market, profile and route changes: 0 / 0 / 0.
- Every live market keeps its profile count, including Piedmont Triad, Charlotte, Raleigh, Nashville, Lexington and Toledo.
- Detroit is not included.

**Digests (full)**

| Digest | Value |
|---|---|
| Parent release | `5d6ced6ed2630d899595cef7d6c2e82dd43cfc15b56e2b48f22f0960afd4f225` |
| Package | `sha256:0720bc825aab90573b816221f45d270a6423f2ed9cae1437a228bbdcc8f08aa2` |
| Build input key | `sha256:c9afb5b30697106f1950f87e1afd74076927d0ebf18284677988ad78b348035e` |
| Intended delta | `sha256:5b9eb66b5215d676e08368f1224131a5fa609d7803dd6c7761617057d6931ef5` |
| Candidate / deployment artifact | `a0f92c7fd5e052e0cf03ad8a9cfacfe9968547ad13dd546829f42ce4f39dcb05` |
| Sitemap | `9344e961269df8fa6143a7ba21cb2734b3369d25294928b38d70bab037a963c8` |
| Validation receipt | `sha256:28816890974ef052115c51be031b7bb97ba82721d753b3f16e36b52f3e88ffc1` |

**Rollback:** deployment `6aa5ce23d51fa8544146ebac`, release `5d6ced6ed2630d899595cef7d6c2e82dd43cfc15b56e2b48f22f0960afd4f225`.

**Staged artifacts:** `C:\t\wil1a` and `C:\t\wil1b`. Staged participation sha: `e08952fd6414f0f8e96e13245cd53992b7583c4d3cb447947d837662d29d941b`.

## Performance

| Stage | Time |
|---|---|
| Geography | ~3 min |
| Census (OSM 8.4 min, brand lane 11 min, overlapping) | ~11 min |
| Attended browser + independents | ~25 min |
| Identity and policy adjudication | ~9 min |
| Registration → auth-ready | 5.6 min |
| FAST | 36 s |
| Whole-site candidate ×2, in parallel | 17.6 min |

**Bottleneck:** the whole-site candidate assembly (~1050 s), then the attended pass.

- Provider cost: $0.
- Founder active time: 0.
- Peak memory: not instrumented. The assembler processes were about 167 MB working set each.
