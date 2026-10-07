# PTF-SALT-LAKE-CITY-UT-HARDENED-SOURCE-READY-001 — FINAL

Market `salt-lake-city-ut` — Salt Lake City / Park City / Wasatch Front, Utah.
Branch `worker/ptf-salt-lake-city-ut-market-001`, worktree `C:\Atlas-Salt-Lake-City-UT-Hardened-V1`.
Built from zero on the New Orleans-live lineage. **SHADOW_UNTIL_REGISTERED.** Nothing was registered, authorized or deployed.

## Outcome

| | |
|---|---|
| Shadow package | `pkg-salt-lake-city-ut-f084558e8d8acabe` |
| Package digest | `sha256:f084558e8d8acabeb116c094b6cc4863e226586fd0f05844061f40a0eb05e2e1` |
| Sealed from | `bb0ac0d4` (SEALED_AT 2026-10-07T17:06:00Z — after the last capture, seq 199 at 17:04:03Z; the real clock read 17:06:59Z when it was set) |
| FAST | 15/15 PASS, 0 unknown, 0 failed, `FAST_DATA_ONLY_RELEASE_ELIGIBLE = YES` |
| Rule J | non-empty: bundle `42035f18…`, 819 files / 803 HTML, output present |
| Rule K | non-vacuous: BYTE_IDENTICAL, 4 cold builds, 0 reuse hits |
| Receipt | `pkg-salt-lake-city-ut-f084558e8d8acabe-9c910e4766ec8d27`, currently eligible (`eligible_receipts`, receipts_dir = shadow_receipts) |
| First-party gate | 162/162 records eligible under the shared reader |
| Independent reproduction | detached worktree at `17f4f430`, separate process, fresh work dir `C:/t/slc2`: same package id and digest, same git blob (`d7d20c10`), same Rule J bundle, independent FAST 15/15; DATA / SITE differences 0 — `salt_lake_city_ut_reproduction_001.json` |
| Census | 209 qualifying identities (by postal-code county: Salt Lake 159, Summit 32 — all Park City, Utah 13 — Lehi, Davis 5) |
| Published | 133 pet-friendly, 29 verified no-pets (162 resolved, 77.5 %) |
| Held | 47, **actionable 0** |
| Readiness | TECHNICAL SOURCE READY = YES; COVERAGE READY = YES |

An earlier package (`cb60864b`, sealed from `a28bb9e8`, FAST 15/15) was superseded after the BringFido REVIEW-lead audit admitted Holiday Inn Express & Suites Park City; its files were removed from the staging tree (history keeps them).

## Lineage

- Current live: New Orleans deploy `6ac5ba3bcda3a604f7e467e0` (44 markets / 4,240 profiles / 4,663 release-index / 4,740 served), lineage `90624cd8`; the shadow package's parent_live_state names it.
- Automatic base derives **YES** → `a67c8e75` (`registration_release_lane.derive_registration_base`, the docs-only child of `90624cd8`; the walk saw only this market's paths above it).
- Start 2026-10-07T13:19:04Z. First FAST-clean package committed 17:00:34Z (**3 h 41 min**); final package committed 17:10:57Z — **3 h 52 min** zero-to-source-ready; coverage-ready verified on the sealed report at 17:17Z — **3 h 58 min**.

## Geography

19 corridors over 51 Utah ZIPs — 6 CORE (Downtown / Temple Square, University–Foothill, Sugar House, SLC Airport–West Side, Park City, Canyons Village–Kimball Junction), 9 STRONG CORRIDOR (South Salt Lake–Millcreek, Murray, Midvale, Sandy, South Jordan, West Jordan, Draper, West Valley City, Cottonwood Heights–Holladay), 4 FRINGE (Taylorsville–Kearns, Riverton–Herriman–Bluffdale, Lehi, North Salt Lake–Bountiful).
10 corridors publish (≥ 5 pet-friendly profiles): Downtown, SLC Airport–West Side, Park City, Canyons–Kimball Junction, Murray, Midvale, Sandy, West Valley City, Cottonwood Heights–Holladay, Lehi.

**Park City is its own identity.** 32 admitted rows (Park City 20, Canyons–Kimball Junction 12), all published as Park City; **PARK CITY PROFILES LABELED SALT LAKE CITY = 0** (census guard + accounting). 16 pet-friendly, 1 verified no-pets, 15 held. Deer Valley East Village: the Grand Hyatt Deer Valley and Canopy by Hilton Deer Valley lie in Wasatch County but their own pages state Park City, UT 84060, so the postal-code rule places them in Park City; the ZIP-derived county field reads Summit for them (no county is published). Municipalities are never flattened: Salt Lake City 80, Park City 32, West Valley City 17, Midvale 14, Lehi 13, Murray 10, Sandy 8, Draper 7, South Jordan 7, Cottonwood Heights 6, West Jordan 4, Woods Cross 3, Holladay 2, and one each Bluffdale, Bountiful, Herriman, Kearns, North Salt Lake, South Salt Lake; 8 rows relabelled from a "Salt Lake City" mailing label to their own municipality; wrong-city identities 0. Utah's grid addresses ("150 W 500 S" vs "150 S 500 W", "West Temple" vs "South Temple") are folded by coordinate pair, never by the shared key.

Boundary audit (graph nodes discovered / admitted): Provo–Orem–Utah County 36/0, Ogden–Davis beyond Bountiful 31/0, Heber Valley–Jordanelle 14/0, eastern Summit 6/0, Snowbird–Alta 9/0, Solitude–Brighton 5/0, Tooele 7/0, Logan–Cache–Bear Lake 3/0, Moab 0/0, St. George–Zion–Bryce 1/0, other 1/0. Canyon resorts sharing 84092 / 84121 with valley suburbs (19 nodes) are refused by name and street, never admitted by the shared code. Rows admitted from a refused ZIP: 0.

## Census and lanes

1,634 raw observations → 897 graph nodes → 209 identities.
Lanes: owned data first (0 owned identities in Utah, 58 owned routes), Utah OSM extract (402 elements in the box, statewide counts kept), Utah registry probe (no public lodging register exists in a readable form — 0 leads, measured), Visit Salt Lake + Visit Park City rosters (346 rows, 303 in admitted codes), brand inventories (125 leads), BringFido challenge (535 raw / 523 unique, identity only — never policy), Places route / gap / map-pin verification, first-party property pages.
Exclusions: OUTSIDE 153; vacation rental 162; timeshare 19 (Westgate ×9, Marriott's MountainSide / Summit Watch ×4, Marriott Vacation Club, Club Wyndham, HGV Sunrise Lodge, WorldMark ×2); non-hotel 80 (incl. AP1 Lofts and Maven apartments, The Other Side venue, the Crystal Ranch outfitter, the "Empire Pass" area listing); military-restricted 4; preopening 1 (The Ascent Park City, Tapestry — Hilton's own card: opening 2027-10-05); closed 0; name-only residue 214; identity-review residue 60 (incl. Park City condo lodges whose public hotel operation is unproven, and The Inn at the Alta Club, a private club). Deer Valley's Stag Lodge, Grand Lodge and Trail's End (residences only, by Deer Valley's own pages), The Lowell condominiums and Park City Vacations are refused as vacation rentals.
Same-premises holds 4 (Comfort Inn Draper = Quality Inn Draper UT121, Sleep Inn West Valley = UT051, and the two Draper buildings Marriott titles identically "Fairfield Inn Salt Lake City Draper"); dual-brand / shared-campus holds 0.

## Policy acquisition

- **Attended browser** (claude-in-chrome; no JS exfiltration, no relay, no bypass, no CAPTCHA solved): 197 recorded attempts, 168 reads. Marriott 42 attempts / 42 reads, **0 denials** (one hotel per batch; Akamai interstitials waited out). Hilton 39 / 38, IHG 17 / 17, Hyatt 10 / 9, Choice (incl. Radisson Americas) 24 / 24, Best Western 7 / 6, ESA 5 / 5, Sonesta, Motel 6, InTown ×2, LivAway ×2, independents 44 / 21.
- Brand directories read in the browser proved four brand departures (Hampton Inn Murray, Country Inn Bountiful, Baymont Murray, Super 8 Midvalley — no longer listed by their own brands) and found two buildings no lane carried (InTown Suites SLC South was already a census row; LivAway Suites Draper was verified by Places and admitted).
- **Quote integrity:** every quote is node text, page text or a zoomed screenshot; find summaries were never quoted. Two transcription corrections were made before commit and are noted on the records: the Crystal Inn reads cited the operator's shared FAQ URL (which merged two buildings) and were re-read from each property's own FAQ; the Anniversary Inn policy read carried a location-list label as an address (which minted a phantom row) and now carries none.
- **Firecrawl:** not used — the plan sits at its protected reserve (60 credits); 0 attempted.
- **Google Places:** 77 requests (27 Enterprise, 50 Pro) inside the free monthly allowance.
- Static plain client 122 requests; Wyndham property service 10 read / 13 retired; independents' policy pages 65 targets.
- New paid spend: **none**. Provider cost: **$0 USD**.

## Publication safety

All zero (`salt_lake_city_ut_publication_safety_audit_001.json`): pet-friendly with explicit refusal 0, question-only 0, service-animal-only 0, preopening / closed 0, timeshare 0, military 0, misleading single fees 0, Park City labelled Salt Lake City 0, canyon resorts published 0, vacation rental / condo published 0, and the shared reader run in advance on every staged record agrees with all 162.
Fees: 21 single-basis fees published (each with the basis and scope its own fee sentence states); 39 tiered fees withheld; 13 unsafe fees withheld (basis not stated 8, two bases 2 — incl. AC Hotel's "$75 pet fee for entire stay" beside a per-night field —, fee sentence cut by the capture 2, stay-length condition 1). Fee scope is read only from the fee's own sentence ("2 pets per room with $150 fee per stay" is never a per-room fee).

## Holds (47, actionable 0)

ACCESS_BLOCKED 16, EVIDENCE 14, ROUTING 9, SOURCE_SILENT 7, IDENTITY 1. Every row has one class and one reason (`salt_lake_city_ut_actionability_001.json`): 45 AUTHORIZED_ROUTER_EXHAUSTED (own site silent after FAQ / policy pages; brand departed by its own directory; Vail's Park City Mountain pages answer server errors; motels with no web presence; amenity-chip-only or conditional statements the shared reader will not publish; Deer Valley's "Rental guests are not allowed to have pets…" and Engen Hus's "unable to welcome any animals" refusals the shared reader cannot interpret; Hyatt Place Lehi's own page prints ZIP 84048 against every other lane's 84043), 1 HELD_UNTIL_OPENING (The Ascent), 1 founder-class row safely held (Hyatt Place Cottonwood: a pet-friendly page that also says "No pets are allowed in 4th-floor rooms"; the shared reader treats the mixed statement as non-operative).

## Isolation and boundaries

Clone residue (Phase 32, run before the first seal): MARKET TEXT 0, COORDINATE 0, BOUNDARY 0 (`salt_lake_city_ut_clone_residue_scan_001.json`; New Orleans' `BROWSER_REACHED` facts, a Portland title pattern and other inherited strings were found and replaced first).
Cross-market file changes 0; factory code changed NO (every edit is a `salt_lake_city_ut_*` module or this market's data); broad regression runs 0; identity_resolutions.json untouched; no final production candidate, no founder authorization, no deployment authorization.
Memory safety: each seal and the reproduction ran detached and alone, with short forward-slash work dirs.

Machine-readable accountings: source, provider, brand, corridor, Park City, competitor reconciliation, municipality, boundary, fee withholding, actionability, publication safety, clone residue, reproduction, performance (`markets/reports/salt_lake_city_ut_*_001.json`).

## FINAL ANSWERS

1. START TIMESTAMP = 2026-10-07T13:19:04Z
2. ZERO_TO_SOURCE_READY = 3 h 52 min (first FAST-clean package 3 h 41 min)
3. ZERO_TO_COVERAGE_READY = 3 h 58 min
4. CURRENT LIVE DEPLOYMENT = 6ac5ba3bcda3a604f7e467e0 (New Orleans, lineage 90624cd8)
5. CURRENT LIVE MARKETS = 44 (4,240 profiles / 4,663 release-index / 4,740 served)
6. AUTOMATIC BASE DERIVES = YES → a67c8e75
7. TOTAL DISCOVERED = 1,634 raw observations
8. NORMALIZED IDENTITIES = 897 graph nodes
9. QUALIFYING CENSUS = 209
10. PET-FRIENDLY = 133
11. VERIFIED NO-PETS = 29
12. RESOLVED = 162
13. UNRESOLVED = 47
14. RESOLUTION RATE = 77.5 %
15. ACTIONABLE UNRESOLVED = 0
16. HOLDS BY CLASS = ACCESS_BLOCKED 16, EVIDENCE 14, ROUTING 9, SOURCE_SILENT 7, IDENTITY 1 (by actionability: exhausted 45, held until opening 1, founder-class safely held 1)
17. EXCLUSIONS BY CLASS = outside 153, vacation rental 162, timeshare 19, non-hotel 80, military 4, preopening 1, closed 0, name-only residue 214, identity-review residue 60
18. PREOPENING IDENTITIES = 1 (The Ascent Park City, Tapestry Collection)
19. PREOPENING PUBLISHED = 0
20. TEMPORARY / SEASONAL IDENTITIES = 0
21. TIMESHARE / VACATION-OWNERSHIP IDENTITIES = 19 (all refused)
22. TIMESHARE / VACATION-OWNERSHIP PUBLISHED = 0
23. PARK CITY QUALIFYING HOTELS = 32
24. PARK CITY PET-FRIENDLY = 16
25. PARK CITY PROFILES LABELED SALT LAKE CITY = 0
26. PUBLISHING CORRIDORS = 10 (downtown-salt-lake-city, slc-airport-west-side, park-city, canyons-kimball-junction, murray, midvale, sandy, west-valley-city, cottonwood-heights-holladay, lehi)
27. COMPETITOR RAW / NORMALIZED / MATCHED / TRUE MISSING = 535 / 523 / 121 (113 identities) / 19 (Places: 10 verified missing → admitted or ruled, 6 already in census, 3 no lodging, 1 outside); REVIEW 65 audited (every hotel-branded lead is a census row; 5 name-only leads Places-verified: 1 apartment product, 4 no lodging)
28. MATERIAL IDENTITY GAP = NO
29. MATERIAL POLICY GAP = NO
30. FIRECRAWL ATTEMPTED / SUCCESS = 0 / 0 (reserve-protected)
31. GOOGLE PLACES REQUESTS = 77 (27 Enterprise, 50 Pro; free allowance)
32. MARRIOTT CENSUS = 40 admitted (42 in-market Marriott pages, incl. the two held Draper Fairfields)
33. MARRIOTT ATTEMPTED = 42
34. MARRIOTT READ SUCCESS = 42 (0 denials)
35. MARRIOTT ACTIONABLE REMAINING = 0
36. OTHER BROWSER ATTEMPTED / SUCCESS = 155 / 126
37. DUAL-BRAND / SHARED-CAMPUS HOLDS = 0 (same-premises holds 4)
38. SINGLE-BASIS FEES PUBLISHED = 21
39. TIERED FEES WITHHELD = 39
40. UNSAFE / MULTI-AMOUNT FEES WITHHELD = 13
41. MISLEADING SINGLE FEES = 0
42. PET-FRIENDLY WITH EXPLICIT REFUSAL = 0
43. QUESTION-ONLY PET-FRIENDLY = 0
44. SERVICE-ANIMAL-ONLY ACCEPTANCE = 0
45. EXISTING PROVIDER CREDITS USED = Google Places 77 requests (free allowance); Firecrawl 0
46. NEW PAID SPEND = NONE
47. PROVIDER COST = $0 USD
48. CLONE MARKET TEXT RESIDUE = 0
49. CLONE COORDINATE RESIDUE = 0
50. RULE J NONEMPTY = PASS (819 files / 803 HTML, output present)
51. RULE K NONVACUOUS = PASS (BYTE_IDENTICAL, 4 cold builds, 0 reuse)
52. FAST RECEIPT CURRENTLY ELIGIBLE = YES
53. SHADOW PACKAGE = pkg-salt-lake-city-ut-f084558e8d8acabe
54. PACKAGE REPRODUCIBLE = YES (independent, BYTE_IDENTICAL)
55. PACKAGE DIGEST = sha256:f084558e8d8acabeb116c094b6cc4863e226586fd0f05844061f40a0eb05e2e1
56. FAST = 15/15 PASS
57. TECHNICAL SOURCE READY = YES
58. COVERAGE READY = YES
59. CROSS-MARKET FILE CHANGES = 0
60. FACTORY CODE CHANGED = NO
61. BROAD REGRESSION RUNS = 0
62. FINAL PRODUCTION CANDIDATE CREATED = NO
63. FOUNDER AUTHORIZATION CREATED = NO
64. SALT LAKE CITY DEPLOYED = NO
65. origin == HEAD = YES (verified after push)
66. tree clean = YES (verified after push)

SALT LAKE CITY SOURCE READY = YES
SALT LAKE CITY COVERAGE READY = YES
ACTIONABLE UNRESOLVED = 0
PARK CITY PROFILES LABELED SALT LAKE CITY = 0
PET-FRIENDLY RECORDS WITH EXPLICIT REFUSAL = 0
QUESTION-ONLY PET-FRIENDLY RECORDS = 0
SERVICE-ANIMAL-ONLY ACCEPTANCE = 0
PREOPENING PROFILES PUBLISHED = 0
TIMESHARE / VACATION-OWNERSHIP PROFILES PUBLISHED = 0
MISLEADING SINGLE FEES = 0
CLONE MARKET TEXT RESIDUE = 0
CLONE COORDINATE RESIDUE = 0
RULE J NONEMPTY = PASS
RULE K NONVACUOUS = PASS
FAST = 15/15 PASS
FACTORY CODE CHANGED = NO
BROAD REGRESSION RUNS = 0
SALT LAKE CITY FINAL CANDIDATE = NO
SALT LAKE CITY DEPLOYED = NO
WAITING FOR RELEASE QUEUE = YES

STOP.

Do not register.
Do not authorize.
Do not deploy.
