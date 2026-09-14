# PTF-HAMPTON-ROADS-VA-PARALLEL-SOURCE-READY-001 — FINAL

Market `hampton-roads-va` ("Hampton Roads, Virginia"), branch `worker/ptf-hampton-roads-va-market-001`. Built from zero on the
branch lineage `6825851b`, whose committed live index is **Atlanta-live** (deploy `6aa7f125a91c73ba2363139e`, 23 markets / 1500
profiles / 1744 routes, read mechanically by the seal). **Current verified production** has since moved on other branches to
**Charleston** (25 markets / 1677 profiles / 1942 routes, deploy `6aa8625938b7e0e0d66e6912`). The shadow package records the
Atlanta binding for integrity; FAST rule N will fail it by design once registration merges the then-current live parent.

**State: SOURCE READY — SHADOW_UNTIL_REGISTERED.** Hampton Roads waits for its turn in the serialized release lane.

Machine-readable accounting: `atlas-dashboard/launch_packages/pettripfinder/markets/reports/hampton_roads_va_source_ready_accounting_009.json`

## Timings (UTC, 2026-09-14)

| Phase | Observed |
|---|---|
| **HAMPTON_ROADS_START_TIMESTAMP** | **21:24:42Z** (first transmission of the order; the complete order arrived minutes later, clock not restarted) |
| Precheck, template read, chain clone | 21:24Z–22:10Z (Richmond VA chain @82c8ea46; Virginia extract re-used from the same-day download) |
| Geography | 22:13:34Z (ZIP 23463 added 22:48Z) |
| Census lanes | OSM 367.8 s; brand inventory ~30 min detached; Visit Chesapeake + Visit Newport News (plain client); Visit Virginia Beach CRM API (attended browser) |
| Routing | Wyndham property service 17.8 s; static lane 49.6 s; policy-page lane 35.6 s |
| Browser evidence | 22:15Z–23:00Z (IHG 25, Hyatt 7, Choice 31 + 1, Best Western 10, Marriott 50, Hilton 42, Red Roof 12, ESA 8, independents) |
| Identity | 22:45Z–23:06Z |
| Policy adjudication | 22:50Z–23:00Z |
| Reconciliation | 23:00Z–23:02Z |
| Shadow package + FAST | first 15/15 at 23:04:46Z (ceaf8efb, superseded); final 23:11:20Z at `d38797e6`, 15/15 |
| Independent reproduction | 23:11:34Z–23:11:59Z, byte-identical |
| **ZERO_TO_SOURCE_READY** | **1 h 46 min 38 s** (first FAST-passed seal 1 h 40 min 4 s) |

Peak memory: not measured. Paid provider cost: **$0**. Founder intervention: **none**.

## Geography (Phases 2–4)

Postal-code partition, 17 corridors, 64 admitted ZIPs. Every corridor sits in ONE city (`CITY_OF_CORRIDOR`); a property whose own page
states another city beside the ZIP is a GEOGRAPHY_HOLD (municipality safety, Phase 12).

| Class | Corridor | City | ZIPs |
|---|---|---|---|
| CORE | virginia-beach-oceanfront | Virginia Beach | 23451, 23450 |
| CORE | virginia-beach-town-center | Virginia Beach | 23462 |
| CORE | virginia-beach-central-bayside | Virginia Beach | 23452 23454 23455 23453 23456 23457 23459 23460 23461 23464 23463 |
| CORE | norfolk-downtown | Norfolk | 23510 23507 23517 23508 23501 23504 23523 |
| CORE | norfolk-airport-military-highway | Norfolk | 23502 23518 23513 23505 23509 |
| CORE | norfolk-ocean-view | Norfolk | 23503 |
| CORE | chesapeake-greenbrier | Chesapeake | 23320 23325 |
| CORE | chesapeake-great-bridge-south | Chesapeake | 23322 23323 23324 |
| CORE | chesapeake-western-branch | Chesapeake | 23321 |
| CORE | portsmouth | Portsmouth | 23701 23702 23703 23704 23705 23707 23708 |
| CORE | hampton-coliseum-central | Hampton | 23666 |
| CORE | hampton-mercury-downtown | Hampton | 23669 23661 23663 23664 23651 23670 23630 |
| CORE | newport-news-city-center | Newport News | 23606 23601 23605 23607 |
| CORE | newport-news-i-64-denbigh | Newport News | 23602 23608 23603 |
| CORRIDOR | suffolk | Suffolk | 23434 23435 23436 23433 |
| FRINGE | smithfield | Smithfield / Carrollton | 23430 23431 23314 |
| FRINGE | yorktown-route-17 | Yorktown (Tabb / Grafton) | 23692 23693 |

**Adjudications:** Williamsburg / Jamestown / Busch Gardens / Kingsmill / Lightfoot / Toano **and historic Yorktown (23690)** → OUTSIDE,
preserved for a future **`williamsburg-va`** market (139 rows carry the reason). Yorktown split: the US-17 / Tabb / Grafton corridor is
peninsula business lodging (FRINGE). Poquoson OUTSIDE (no hotel core). Western Suffolk (Holland, Whaleyville, Chuckatuck), Isle of Wight
rural / Windsor / Surry, Gloucester, the Eastern Shore and North Carolina OUTSIDE by name. Installation-only ZIPs (23511 23551 23521 23604
23665 23691 23709 23681) OUTSIDE as MILITARY_NONPUBLIC.

Overlays (reporting only; shared ZIPs): ORF Airport vs Military Circle (23502), Battlefield Blvd North vs Greenbrier (23320), Coliseum vs
Convention Center vs Hampton Roads Center (23666), City Center vs Oyster Point (23606), PHF vs Denbigh.

## Owned data (Phase 7)

- **OWNED IDENTITIES: 0.**
- **OWNED ROUTES: 53** (52 ORF/PHF Marriott + 1 Magnuson, `dayton_oh_brand_directory_harvest_001`); every in-market Marriott route re-read on Marriott's own page (2 are NC, outside).
- **OWNED VALID POLICY EVIDENCE: 0.**

## Accounting (Phase 18)

| Measure | Value |
|---|---|
| TOTAL DISCOVERED | **518** |
| PROPOSED CENSUS | **264** |
| VALID PET-FRIENDLY | **94** |
| VALID VERIFIED NO-PETS | **72** |
| RESOLVED / UNRESOLVED | **166 / 98** |

Every census identity has exactly one disposition; every identity key is unique.

| Hold class | Count | Contents |
|---|---|---|
| IDENTITY (non-census) | 36 | brand-flag map rows the brand's inventory does not list (Days Inn ×2, Econo Lodge 2113 Atlantic, Rodeway Inn, Super 8 ×2, Travelodge ×2); same-name pairs (19 Atlantic Hotel, Breeze Inn & Suites, Budget Lodge ×3); 9 Oceanfront vacation-ownership resorts whose only website is a timeshare agent; name-only rows |
| ROUTING | 40 | map-only / directory-only motels (Military Hwy, Warwick Blvd, Jefferson Ave, Pruden Blvd, Studios & Suites 4 Less ×4, Economy 7 ×2 …), parked domains (Alamar, Oceans 2700), booking-engine-only sites |
| ACCESS_BLOCKED | 11 | Choice behind the 403 wall (Clarion Inn & Suites, Comfort Suites Airport, Sleep Inn & Suites), Motel 6 ×2 (timeouts), Sea View Hotel and Ocean Cove Motel (403 / browser not permitted), The Belvedere, American Inn, Bowers Hill Inn (TLS failures), stayAPT Suites (403) |
| EVIDENCE | 47 | SERVICE_ANIMAL_ONLY ×7 (Hilton VB Oceanfront, DoubleTree Oceanfront South, Spark Oceanfront, Hilton Norfolk The Main, The Landing at Hampton Marina, Hilton Vacation Club ×2); AMENITY_CHIP_ONLY ×11 (ESA ×8, Inn at Old Beach, Economy Inn, YourSpace); FEE_ONLY ×3 (WoodSpring VB, Chesapeake Greenbrier, Chesapeake South); ADDRESS_NOT_ON_DOCUMENT ×4 (Beach Carousel, Cerca Del Mar, The Capes, InTown Greenbrier); QUOTE_NOT_OPERATIVE ×4 (Holiday Inn VB-Norfolk, Crowne Plaza Town Center, The Sitio, Magnuson); FIRST_PARTY_CONFLICT ×1 (Brentwood Inn & Suites Suffolk); POLICY_NOT_FOUND (Staybridge ×2, City Express NN, Hyatt Studios Chesapeake, Blue Marlin, Seashire, Cutty Sark, MacThrift, Schooner Inn, Sun and Sand, The Breakers, Historic Boxwood Inn, Lodge at Kiln Creek, Country Villa, Garner Hotel VB North, Sonesta Simply Suites Hampton …) |
| GEOGRAPHY | 2 | Red Roof Inn Virginia Beach – Norfolk Airport (page says Norfolk beside VB 23455); Red Roof Inn Newport News – Yorktown (page says Newport News beside York County 23692) |
| MILITARY / NONPUBLIC | 4 | Navy Gateway Inn and Suites, Navy Lodge Norfolk, Langley Inn and Bayview Towers (Langley 23665) |
| PAID | 0 | budget $0; no lane used or reserved |
| FOUNDER | 0 | — |
| CLOSED / RETIRED | 34 | Wyndham routes redirecting to the brand's city search |
| OUTSIDE | 161 | 139 Williamsburg future market; Cape Charles / Eastern Shore, Gloucester, Surry, NC, Richmond-region rows |
| NON-HOTEL | 54 | 28 bureau vacation-rental / condo / beach-house listings, 8 campgrounds / state parks, 6 map apartment / condo / chalet units, 3 apartment buildings, 3 private dwellings / B&B map rows, 2 rental operators / concierges, 2 offices (CVB, hotel association), 1 timeshare agency, 1 condo unit |

Held verbatim (never reworded): "No, pets are not allowed at Holiday Inn Virginia Beach - Norfolk." / "... at Crowne Plaza Virginia Beach
Town Center."; "We love pets; however, we are not a pet friendly hotel." (The Sitio); "Yes! Pets are allowed, $20.00 PER NIGHT PER PET
charged" beside "No pets allowed" (Brentwood Inn & Suites); "Limit 2 dogs, under 75lbs. per room. No cats. Non-refundable pet cleaning fee
of 100USD per pet ..." (WoodSpring VB).

## City coverage (Phase 3 / 19)

| City | Census | PF | NP | Unresolved |
|---|---|---|---|---|
| Virginia Beach | 103 | 31 | 30 | 42 |
| Norfolk | 34 | 16 | 14 | 4 |
| Chesapeake | 49 | 14 | 11 | 24 |
| Portsmouth | 4 | 1 | 3 | 0 |
| Hampton | 17 | 9 | 4 | 4 |
| Newport News | 32 | 11 | 6 | 15 |
| Suffolk | 15 | 7 | 3 | 5 |
| Yorktown (US-17) | 8 | 4 | 1 | 3 |
| Smithfield | 2 | 1 | 0 | 1 |

**Market balance check:** Virginia Beach leads because the Oceanfront strip is the region's largest cluster; every core city was reached
by at least two independent lanes. Portsmouth's small count matches the map and brand lanes (Renaissance, Quality Inn Olde Town, Red Roof,
map motels) — real inventory, not a failed lane. Norfolk's and Hampton's bureaus could not be read (WordPress without a listing API / 403),
so their independents rest on the map and brand lanes: a recorded lane gap.

## Corridor coverage (page threshold: 5 pet-friendly)

| Corridor | Class | Census | PF | NP | Unres | Page |
|---|---|---|---|---|---|---|
| virginia-beach-oceanfront | CORE | 71 | 18 | 21 | 32 | YES |
| virginia-beach-town-center | CORE | 18 | 9 | 3 | 6 | YES |
| virginia-beach-central-bayside | CORE | 14 | 4 | 6 | 4 | NO |
| norfolk-downtown | CORE | 8 | 3 | 4 | 1 | NO |
| norfolk-airport-military-highway | CORE | 24 | 12 | 10 | 2 | YES |
| norfolk-ocean-view | CORE | 2 | 1 | 0 | 1 | NO |
| chesapeake-greenbrier | CORE | 31 | 12 | 6 | 13 | YES |
| chesapeake-great-bridge-south | CORE | 5 | 0 | 2 | 3 | NO |
| chesapeake-western-branch | CORE | 13 | 2 | 3 | 8 | NO |
| portsmouth | CORE | 4 | 1 | 3 | 0 | NO |
| hampton-coliseum-central | CORE | 15 | 9 | 3 | 3 | YES |
| hampton-mercury-downtown | CORE | 2 | 0 | 1 | 1 | NO |
| newport-news-city-center | CORE | 10 | 3 | 4 | 3 | NO |
| newport-news-i-64-denbigh | CORE | 22 | 8 | 2 | 12 | YES |
| suffolk | CORRIDOR | 15 | 7 | 3 | 5 | YES |
| smithfield | FRINGE | 2 | 1 | 0 | 1 | NO |
| yorktown-route-17 | FRINGE | 8 | 4 | 1 | 3 | NO |

7 of 17 corridor pages publish; the FAST cold build rendered exactly these 7. No thin page was manufactured.

## Census lanes and gap challenge (Phases 8–10)

- OSM (Virginia Geofabrik extract): 480 elements in the observation box.
- Brand inventory: Marriott owned 52 + VA sitemap page; Hilton 14 city pages + 103 sub-pages (42 in-market properties read); Wyndham sitemap
  (68 routes: 34 read, 34 retired); WoodSpring sitemap. Plain-client 403: IHG, Best Western, Red Roof, Hyatt, Radisson, Omni; timeouts: Choice, Motel 6.
- Attended reads: IHG destination pages (25), Hyatt service (7), Choice city pages (41 codes; 31 served, wall), Best Western sitemap (10),
  Marriott (50), Hilton (42), Red Roof sitemap (12), ESA city pages (8), 3 independents.
- City bureaus: Visit Virginia Beach (CRM WordPress API, 165 accommodations of 1,268), Visit Chesapeake (50), Visit Newport News (23).
  Visit Norfolk, Visit Hampton, Visit Portsmouth: no readable listing service (lane gap).
- Independents' own sites: 113 static targets, 57 policy-page sites.
- **Competitor gap: 16 BringFido leads, 11 matched first-party identities, 5 name-only duplicates of census identities, 0 true missing hotels.**

## Shared-factory notes (recorded, not repaired)

1. The shared reader does not read "No, pets are not allowed at Holiday Inn Virginia Beach - Norfolk." (or Crowne Plaza Town Center) as a
   refusal, though it reads the same IHG sentence for other hotels; nor "We love pets; however, we are not a pet friendly hotel."
2. Hilton "Service animals only" petsInfo is held SERVICE_ANIMAL_ONLY (7 properties).

Market-local fixes in this order: "Hampton" is a city here, so the Hilton flag test reads "Hampton Inn" only; the IHG
service-animal conflict guard accepts "Bring up to 2 ... dogs or cats" acceptance wording; Williamsburg pin rule bounded by longitude
(Cape Charles was mis-refused); military name rule keeps commercial hotels named for a base ("Econo Lodge Naval Station Norfolk").

## Shadow package (Phases 20–22)

| Item | Value |
|---|---|
| Package | `pkg-hampton-roads-va-27d1707231cbfb4a` |
| Digest | `sha256:27d1707231cbfb4a3a5a5c02e25b0f1ee4bf60ba5def03ef79b1254db2efb7da` |
| Receipt | `sha256:5600a48c5c4a990eebc91e58b3202f544775571b471ee0e1e0c510e46c4d087b` |
| Zone | SHADOW_UNTIL_REGISTERED |
| Source commit | `d38797e6` |
| Parent | Atlanta-live (branch lineage) |
| Package path | `markets/staging/hampton-roads-va/shadow_packages/hampton-roads-va/` |
| Receipt path | `markets/staging/hampton-roads-va/shadow_receipts/hampton-roads-va/` |
| FAST | **15/15 PASS**, 0 unknown, 0 failed, determinism BYTE_IDENTICAL |
| First-party gate | 166/166 eligible |
| Reproduction | Clean worktree at `d38797e6` with a copied document store: zero content difference (only the eol-unattributed discovery config checks out CRLF); a separate-process seal gives the same digest. |

Two earlier seals (71981771 at ceaf8efb; 6592a381 at 4503d568, whose committed staged census copy was stale) were superseded and removed.

## Not done, by design

No shared factory code changed. No registry, participation, closure, contract, global, identity-resolution or live-state edit. No broad
regression. No final candidate. No founder authorization. No deploy.

## Next order — registration and reseal (when Hampton Roads reaches the front of the lane)

1. Read CURRENT VERIFIED LIVE and merge that parent into this branch. The Atlanta binding of this package then fails FAST rule N **by design**.
2. Copy the staged documents into their registered paths and repoint the helpers: `markets/proposed/hampton-roads-va.json` → `markets/hampton-roads-va.json`;
   `identity_census_proposed/hampton-roads-va.json` → `identity_census/hampton-roads-va.json`; the staged `hotel_policy_facts_hampton-roads-va.json`,
   `hampton_roads_va_final_partition_007.json` and authority shard → registered paths. Re-stage the census copy after ANY census edit.
3. No same-campus resolution is required by this census (no co-location or directional hold raised); recheck after new reads.
4. `market_registration_cli --write`, `build_global_authority --write` then `--check`, the release contract.
5. `registration_release_lane register` and `seal --work-order` (a **new** package id), FAST.
6. `regression_delta classify` (expect COMPOSITE_FRESH_MARKET_DATA_ONLY); compose and reproduce the candidate; founder packet; deploy only on founder authorization.
7. Before sealing, strengthen evidence: re-probe Choice beyond the wall (va904 va384 va358 va761 va050), Motel 6 / Studio 6, Sea View, Ocean Cove,
   Belvedere and the TLS-failing Chesapeake motels; read IHG Garner Hotel VB North (orfaa) and Sonesta Simply Suites Hampton; settle the Oceanfront
   timeshare resorts' public hotel operation; resolve the two Red Roof geography holds with address-bearing first-party documents; try the
   Norfolk and Hampton bureaus again.
