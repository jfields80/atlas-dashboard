# PTF-ASHEVILLE-NC-NORMAL-PRODUCTION-001 — final report

Branch `worker/ptf-asheville-nc-new-market-001`, worktree `C:\Atlas-Asheville-Hardened-V1`.
Registration commit `5c3264650962cf726700ccda4962422d96dadad1`.

- Nothing was deployed.
- No factory or shared code changed.
- **Status: AWAITING_FOUNDER_AUTHORIZATION.** The founder packet is `launch_packages/pettripfinder/markets/reports/asheville_nc_founder_authorization_packet_001.json`.

## Timeline

| | Time |
|---|---|
| ASHEVILLE_START_TIMESTAMP | 2026-09-13T00:40:56Z |
| Registration first write | ~01:16:00Z |
| Release lane AUTHORIZATION_READY | 01:22:20Z (41 m 24 s from start) |
| Candidate reproduced, packet written | 01:45:47Z |
| **ZERO → AUTHORIZATION READY** | **1 h 04 m 51 s (EXCELLENT)** |
| REGISTRATION_TO_AUTH_READY | ~6 m 20 s from the first registration write (5 m 41 s from `register`) |

## Current verified live

Read at 00:41:55Z and re-read at 01:23:05Z and 01:42:45Z. It was unchanged at every read.

| Field | Value |
|---|---|
| Host deployment | `6aa5e2623de160fcdf416577` (ready) |
| Live release digest | `a0f92c7fd5e052e0cf03ad8a9cfacfe9968547ad13dd546829f42ce4f39dcb05` |
| Source commit | `7709953fac20326181abb04d5d4f2f33eee869c2` |
| Sitemap digest | `9344e961269df8fa6143a7ba21cb2734b3369d25294928b38d70bab037a963c8` (the host sitemap sha matches) |
| Markets / profiles / routes | 17 / 1154 / 1361 |
| Rollback parent | `6aa5ce23d51fa8544146ebac` |
| Release index problems | 0 |
| Verification | VERIFIED |

## Geography

Membership is decided by the property's own postal code. The market has 10 corridors over 11 ZIPs.

| Class | Corridors |
|---|---|
| CORE | Downtown (28801); Biltmore Village / Biltmore Estate / South Asheville (28803); Tunnel Road / East Asheville (28805); West Asheville (28806); North Asheville / Grove Park / Woodfin (28804); Arden / Fletcher / AVL (28704, 28732) |
| CORRIDOR | Candler (28715); Weaverville (28787); Swannanoa (28778) |
| FRINGE | Black Mountain (28711) |

**OUTSIDE, refused by name:**
- Hendersonville / Laurel Park, Flat Rock / East Flat Rock and Mills River: a separate Henderson County lodging market, reserved for a future market.
- Fairview and Leicester: cabin and vacation-rental country.
- Mars Hill / Marshall / Hot Springs.
- Waynesville / Lake Junaluska, Maggie Valley and Canton / Clyde.
- Chimney Rock / Lake Lure / Bat Cave.
- Montreat / Ridgecrest and Old Fort.
- Brevard / Pisgah Forest.

## Lanes

**Rung 0 (owned):** 24 Marriott AVL routes from the committed national harvest. There were no owned Asheville identities and no owned policy evidence.

**Free lanes:**
- Hilton's 15 city pages, which yielded 36 codes.
- The Wyndham sitemap, which yielded 26 routes.
- The WoodSpring sitemap.
- 90 brand requests in total.
- OSM (Geofabrik NC extract, market-local two-pass reader, 424 s): 191 lodging elements.
- IHG destination pages: 12 codes.

**Attended browser (free):**
- Hilton: 36 pages. Marriott: 21. IHG: 12. Omni Grove Park Inn: 1.
- Wyndham: 8 live properties. The brand's own search lists the same set; 11 sitemap routes are retired and redirect to that search page.
- BringFido's Asheville page, read for names only.

**Independent first-party static lane:** 30 seeds, 68 requests.

**Refused lanes, not fought:**
- Choice: a sitemap timeout and a blank attended property page.
- Best Western, Red Roof, Hyatt and Omni: sitemap 403.
- Radisson: sitemap 403, and the domain is not navigable in the operator's session.
- Motel 6: sitemap timeout.
- Independents: 8 sites with no DNS answer, 3 returning 403 and 1 returning 500.
- exploreasheville.com: 403.

**Firecrawl, Bright Data, paid discovery:** not used. $0.

## Market

| Measure | Value |
|---|---|
| Total discovered candidates | 217 |
| Registered census | 96 |
| Not admitted | 121: 68 outside market, 21 name-only, 17 identity review, 15 non-lodging / vacation rental / B&B |
| Pet-friendly | 41 |
| Verified no-pets | 15 |
| Resolved / unresolved | 56 / 40 |

**Holds**

| Class | Count |
|---|---|
| Identity | 0 |
| Routing | 10 |
| Access-blocked | 23 |
| Evidence | 7 (2 service-animal-only, 3 non-operative quotes, 2 policy silence) |
| Geography | 0 |
| Paid | 0 |
| Founder | 0 |

**Corridor counts (census / PF / no-pets)**

| Corridor | Census | PF | No-pets |
|---|---|---|---|
| Downtown | 23 | 17 | 1 |
| Biltmore / South Asheville | 14 | 6 | 3 |
| Tunnel Road / East Asheville | 20 | 7 | 5 |
| West Asheville | 18 | 5 | 1 |
| North Asheville / Woodfin | 5 | 3 | 0 |
| Arden / Fletcher / AVL | 8 | 2 | 4 |
| Candler | 2 | 0 | 0 |
| Weaverville | 1 | 0 | 1 |
| Swannanoa | 0 | 0 | 0 |
| Black Mountain | 5 | 1 | 0 |

Four corridor pages publish: Downtown, Biltmore / South Asheville, Tunnel Road and West Asheville.

**Sub-areas (census / PF / no-pets)**

| Sub-area | Census | PF | No-pets |
|---|---|---|---|
| Downtown | 23 | 17 | 1 |
| Biltmore Village / Biltmore | 13 | 5 | 3 |
| South Asheville (Biltmore Park) | 1 | 1 | 0 |
| Tunnel Road / East Asheville | 20 | 7 | 5 |
| West Asheville | 18 | 5 | 1 |
| AVL Airport / Fletcher / Arden | 8 | 2 | 4 |
| North Asheville / Woodfin | 5 | 3 | 0 |
| Black Mountain | 5 | 1 | 0 |
| Weaverville | 1 | 0 | 1 |
| Candler | 2 | 0 | 0 |

**Vacation-rental and non-lodging exclusions (examples):**
- Sensibilities Day Spa: a spa at Hilton Biltmore Park's address.
- Wrong Way River Lodge and Cabins: a campground.
- Carolina Bed & Breakfast and Grafton Lodge B&B.
- Buffalo Creek Vacations listings, River View Cabins, Minnehaha Falls Guest House and a single rental house.

**Admitted despite a vacation-rental look:**
- Lantern Lodge Asheville (the map's Residences at Biltmore): a condo-hotel operated as one hotel.
- AutoCamp Asheville: a Hilton-operated resort.

**Competitor gap (BringFido leads, names only):**
- EXACT match: Kimpton Hotel Arras, Aloft Asheville Downtown, The Restoration.
- ALIAS: Comfort Suites Outlet Center.
- REVIEW: Country Inn & Suites River Arts District, ESA Premier Suites and Americas Best Value Inn.
- NON_HOTEL: 1900 Inn on Montford and Black Walnut Inn.
- VACATION_RENTAL: The Pines Cottages.
- True missing qualifying hotels: 0.

## Registration

**Change class:** COMPOSITE_FRESH_MARKET_DATA_ONLY, selected on the first classification.
- 42 changed paths, all accounted for: 12 market-local, 13 registration, 17 derived, 0 shared, 0 unknown.
- All 15 proofs PASS.
- Local broad requested / run: 0 / 0.
- Remote broad jobs: 0.
- Unchanged markets rebuilt: 0.

**Package and FAST**
- Package `pkg-asheville-nc-af7b78b6abf82d8a`, reproducible YES.
- FAST 15/15 PASS in 38.7 s, 0 unknown, 0 failed.

**Helper-level corrections (no factory edits)**
1. **A map phone is not a merge key.** The OSM Wingate row carries Fairfield's phone number, which folded the two hotels together.
2. **Page and map spellings of one building now fold.** "One/Two Buckstone Place" and "1/2", and "Knoll" and "Knolls", no longer split.
3. **A false Wyndham sitemap lead is filtered.** "wyndham-garden" matched the "arden" token.
4. **"2 pets max per room with a fee" is no longer read as a per-room fee.**
5. **The pin blocks a second seal.** The Omni binding-method label was corrected after the first seal, so the pin file was restored and the market resealed once. The superseded untracked package was removed.

## Final candidate

The candidate is current live plus the Asheville package. The partition was resolved through the contract, with no assembler edit.

**FINAL_CANDIDATE_REPRODUCIBLE: YES.** Build A and build B produced identical bytes. The two builds ran in parallel in 1115 s.

**Release diff**

| | Markets | Profiles | Routes |
|---|---|---|---|
| Parent | 17 | 1154 | 1361 |
| Candidate | 18 | 1195 | 1408 |
| Asheville added | +1 | +41 | +47 (sitemap basis; 46 on the release-index basis) |

The two route numbers differ by exactly one route. The sitemap delta is the 41 profiles, 4 corridors, the hub and `policy-comparison/`. The release index does not model the comparison page, so it is always one less.

- Removed: 0 markets, 0 profiles, 0 routes.
- Files: 7064 → 7315. Only `sitemap.xml` changed among existing files.
- Unexpected market, profile and route changes: 0 / 0 / 0.
- Every live market keeps its profile count, including Wilmington, Piedmont Triad, Charlotte, Raleigh, Nashville, Lexington and Toledo.
- Detroit is not included.

**Digests (full)**

| Digest | Value |
|---|---|
| Parent release | `a0f92c7fd5e052e0cf03ad8a9cfacfe9968547ad13dd546829f42ce4f39dcb05` |
| Package | `sha256:af7b78b6abf82d8a7624afc9bf2f475dbac64f134e005a590679ed3a681ca0c1` |
| Build input key | `sha256:441b35b68fc4aee6e2cb3d6efa8543fe3636addf1a87010824d95829351118fa` |
| Intended delta | `sha256:ba28aa005a5def9528dd1e26373548e9e3690e37b13e1a83748f0dd31881b527` |
| Candidate / deployment artifact | `d98a24038ef25df4b481e71b8436377ff01abc2bc80a11de2fe7222df9dadb36` |
| Sitemap | `6a33f1e53a094f934f1175bd21c58e77675820ab18b593288ab472c55152a699` |
| Validation receipt | `sha256:c717db2ac1fadd61af07303fcce3e30540e928b66054a09e0fd8f4d15b862534` |

**Rollback:** deployment `6aa5e2623de160fcdf416577`, release `a0f92c7fd5e052e0cf03ad8a9cfacfe9968547ad13dd546829f42ce4f39dcb05`.

**Staged artifacts:** `C:\t\ash1a` and `C:\t\ash1b`. Staged participation sha: `0894c004b95c9fc070ecddb5c3ef1cf9ebc17853033da74460dc3b96443d12b3`.

## Performance

| Stage | Time |
|---|---|
| Geography | ~4 min |
| Census (OSM 7.1 min, brand lane ~7 min, overlapping) | ~8 min |
| Attended browser + independents | ~20 min |
| Identity and policy adjudication | ~12 min |
| Registration → auth-ready | ~6.3 min |
| FAST | 38.7 s |
| Whole-site candidate ×2, in parallel | 18.6 min |

**Bottleneck:** the whole-site candidate assembly (~1110 s), then the attended pass.

- Provider cost: $0.
- Founder active time: 0.
- Peak memory: not instrumented.
