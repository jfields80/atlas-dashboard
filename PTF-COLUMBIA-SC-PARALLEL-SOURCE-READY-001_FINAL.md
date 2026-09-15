# PTF-COLUMBIA-SC-PARALLEL-SOURCE-READY-001 — FINAL

Market `columbia-sc` ("Columbia, South Carolina"), branch `worker/ptf-columbia-sc-market-001`. Built from zero on the
branch lineage `6825851b`, whose committed live index is **Atlanta-live** (deploy `6aa7f125a91c73ba2363139e`, 23 markets / 1500
profiles / 1744 routes, read mechanically by the seal). Production has since moved on other branches; at the time of this run the
operator's launch record names **Outer Banks** as live (26 markets / 1703 profiles / 1972 routes, deploy `6aa8992493a75f80cd0e3887`).
The shadow package records the Atlanta binding for integrity; FAST rule N will fail it by design once registration merges the
then-current live parent.

**State: SOURCE READY — SHADOW_UNTIL_REGISTERED.** Columbia waits for its turn in the serialized release lane.

Machine-readable accounting: `atlas-dashboard/launch_packages/pettripfinder/markets/reports/columbia_sc_source_ready_accounting_009.json`

## Timings (UTC, 2026-09-15)

| Phase | Observed |
|---|---|
| **COLUMBIA_START_TIMESTAMP** | **00:18:26Z** |
| Precheck, template read, chain clone | 00:18Z–00:25Z (Hampton Roads VA chain @87249b80; its browser JS extracted from its transcript; SC Geofabrik extract of 2026-09-10 copied from the Charleston worktree) |
| Geography | 00:27:25Z (PO-box ZIP 29171 added 00:52Z) |
| Census lanes | OSM 207.3 s; brand inventory ~24 min detached; Experience Columbia SC listing service (plain client) 00:31Z |
| Routing | Wyndham property service 10.6 s; static lane 31.0 s; policy-page lane 5.0 s |
| Browser evidence | 00:33Z–00:52Z (IHG 13, Marriott 30, Hilton 33, Choice 26, Hyatt 2, Best Western 8, Red Roof 2, ESA 4, Motel 6 / Studio 6 4, stayAPT 1, Historic Stays 1) |
| Identity | 00:45Z–00:58Z |
| Policy adjudication | 00:50Z–00:58Z |
| Reconciliation | 00:58Z–00:59Z (inputs committed at `fe2d1b6a`) |
| Shadow package + FAST | 01:00:48Z–01:02:53Z, 15/15 |
| Independent reproduction | 01:04:10Z–01:04:37Z, byte-identical |
| **ZERO_TO_SOURCE_READY** | **44 min 27 s** (reproduction confirmed at 46 min 11 s) |

Peak memory: not measured. Paid provider cost: **$0**. Founder intervention: **none**.

## Geography (Phases 2–4)

Postal-code partition, 13 corridors, 25 admitted ZIPs. Every corridor names the mailing municipalities its ZIPs carry
(`CITY_OF_CORRIDOR`); a property whose own page states a known town outside that set beside its ZIP is a GEOGRAPHY_HOLD.

| Class | Corridor | Mailing towns | ZIPs |
|---|---|---|---|
| CORE | downtown-vista-usc | Columbia | 29201 29208 29205 |
| CORE | north-columbia-medical | Columbia | 29203 29204 |
| CORE | fort-jackson-forest-acres | Columbia, Forest Acres, Arcadia Lakes | 29206 29209 |
| CORE | northeast-two-notch | Columbia | 29223 |
| CORE | sandhills-clemson-road | Columbia | 29229 |
| CORE | st-andrews-bush-river | Columbia | 29210 |
| CORE | harbison-irmo | Columbia, Irmo, Ballentine | 29212 29063 29002 29221 |
| CORE | west-columbia-cayce | West Columbia, Cayce, Springdale | 29169 29033 |
| CORE | cae-airport | West Columbia, Cayce, Pine Ridge, Springdale | 29170 29172 29171 |
| CORE | lexington | Lexington, Pine Ridge, Red Bank, South Congaree, Oak Grove | 29072 29073 29071 |
| CORRIDOR | blythewood | Blythewood | 29016 |
| FRINGE | chapin | Chapin | 29036 |
| FRINGE | elgin | Elgin | 29045 |

**Adjudications.** Downtown, the Vista, USC and Five Points share one corridor, and the order's named areas are reported as overlays.
Prisma Health Richland and north Columbia form their own medical corridor. The Fort Jackson **installation ZIP 29207 is OUTSIDE (MILITARY_NONPUBLIC)**, while the commercial
gate corridors (Garners Ferry / Forest Drive, Two Notch, Clemson Road) are admitted. West Columbia / Cayce and CAE are two CORE corridors, never
relabelled "Columbia". Blythewood is CORRIDOR; Chapin and Elgin are FRINGE. Gaston / Swansea / Pelion / Gilbert and Eastover / Hopkins were
evaluated and refused (no hotel core). Camden / Lugoff, Sumter / Shaw AFB, Orangeburg / Santee, Newberry, Winnsboro, Batesburg-Leesville,
Aiken / Augusta, Florence, Rock Hill and Charlotte are OUTSIDE by name. The I-20, I-26 and I-77 corridors cross several postal corridors and are
reported as overlays, never pages.

## Owned data (Phase 5)

- **OWNED IDENTITIES: 0.**
- **OWNED ROUTES: 30.** These are CAE-coded Marriott routes from `dayton_oh_brand_directory_harvest_001`. Every one was re-read on Marriott's own page; 6 are Santee, Orangeburg, Sumter or Camden, which are outside.
- **OWNED VALID POLICY EVIDENCE: 0.**

## Accounting (Phases 15–16)

| Measure | Value |
|---|---|
| TOTAL DISCOVERED | **206** |
| PROPOSED CENSUS | **125** |
| VALID PET-FRIENDLY | **64** |
| VALID VERIFIED NO-PETS | **42** |
| RESOLVED / UNRESOLVED | **106 / 19** |

Every census identity has exactly one disposition, and every identity key is unique. The partition has 0 contract issues. The first-party gate passed 106 of 106.

| Hold class | Count | Contents |
|---|---|---|
| IDENTITY (non-census) | 37 | Brand-flag map rows the brand's own inventory does not list at that address: Days Inn at 7300 Garners Ferry, Quality Inn & Suites at 2210 Bush River, Suburban at 150 Stoneridge, Red Roof Inn Columbia East at 7580 Two Notch. Bare-label map duplicates of hotels already read: Sheraton, Sleep Inn. Flutter Wing (lodging category unconfirmed). The Wyndham Garden / Hawthorn / Wyndham Garden rows at 1539 Horseshoe Drive (same-campus, unproved). 23 name-only map motels and competitor aliases. |
| ROUTING | 2 | Knights Inn Columbia Airport/Cayce and Travelers Inn: map only, with no first-party route. |
| ACCESS_BLOCKED | 0 | None. Every surface that names a census identity served the plain client or the attended browser. |
| EVIDENCE | 17 | See the breakdown below. |
| GEOGRAPHY | 1 | Holiday Inn Express & Suites Columbia Downtown – The Vista: IHG's own JSON-LD puts "901 Washington Street" beside ZIP 29229 (Sandhills). |
| MILITARY / NONPUBLIC | 3 | IHG Palmetto Fort Jackson Hotel, Holiday Inn Express Fort Jackson Inn (29207), IHG Army Hotels |
| PAID | 0 | Budget was $0; no paid lane was used or reserved. |
| FOUNDER | 0 | — |
| CLOSED / RETIRED | 15 | Wyndham routes that now redirect to the brand's city search (Microtel Two Notch and Harbison, Super 8 West Columbia Airport, Wingate Fort Jackson and Lexington, Travelodge Columbia West, among others). |
| OUTSIDE | 33 | Camden, Lugoff, Sumter, Newberry, Leesville, Gilbert, Swansea, Eastover and Hopkins rows, plus name-only Santee, Orangeburg and Florence Marriott routes. |
| NON-HOTEL | 10 | 4 bureau campgrounds and RV parks, 3 map apartment units (The Hub at Columbia, the two "Companion at The Palms" rows), Heartwood Furnished Homes, and Historic Stays of Columbia with its 1425 Inn apartments. |

**Evidence holds (17):**
- **SERVICE_ANIMAL_ONLY:** Hilton Columbia Center, DoubleTree Columbia.
- **Reader-rejected service-animal read:** Days Inn & Suites Columbia Airport ("Maximum 2 pets up to 100 lbs allowed ...").
- **FEE_ONLY:** Baymont Columbia Northwest.
- **QUOTE_NOT_OPERATIVE:** Hotel Trundle ("While we love pets, we kindly ask that you leave your furry friends at home.").
- **AMENITY_CHIP_ONLY:** the 4 Extended Stay America properties; Motel 6 Columbia East ("Pets welcome throughout your stay", with no ZIP on the page).
- **ADDRESS_NOT_ON_DOCUMENT:** the 3 InTown Suites ("No pets allowed at InTown Suites Columbia SC – ...").
- **POLICY_NOT_FOUND:** Staybridge Suites (FAQ question with no answer), StudioRes Harbison (no Pet Policy row).
- **CO_LOCATION_RULING_REQUIRED:** Homewood Suites and Tru Columbia Downtown, both pet-friendly, sharing 400 Gervais Street.

Held verbatim, never reworded.

## City and corridor coverage (Phase 16; page threshold: 5 pet-friendly)

| Corridor | Class | Census | PF | NP | Unres | Page |
|---|---|---|---|---|---|---|
| downtown-vista-usc | CORE | 23 | 10 | 8 | 5 | YES |
| north-columbia-medical | CORE | 7 | 6 | 1 | 0 | YES |
| fort-jackson-forest-acres | CORE | 16 | 8 | 7 | 1 | YES |
| northeast-two-notch | CORE | 14 | 6 | 6 | 2 | YES |
| sandhills-clemson-road | CORE | 2 | 1 | 1 | 0 | NO |
| st-andrews-bush-river | CORE | 17 | 6 | 6 | 5 | YES |
| harbison-irmo | CORE | 18 | 10 | 5 | 3 | YES |
| west-columbia-cayce | CORE | 10 | 8 | 1 | 1 | YES |
| cae-airport | CORE | 6 | 3 | 1 | 2 | NO |
| lexington | CORE | 7 | 3 | 4 | 0 | NO |
| blythewood | CORRIDOR | 4 | 2 | 2 | 0 | NO |
| chapin | FRINGE | 0 | 0 | 0 | 0 | NO |
| elgin | FRINGE | 1 | 1 | 0 | 0 | NO |

**7 of 13 corridor pages publish.** The FAST cold build rendered exactly these 7, and no thin page was manufactured.
- **Sandhills (29229):** only 2 identities, because the Killian Road hotels on Roberts Branch Parkway are mailed 29203, north Columbia.
- **Chapin:** no lane returned a lodging identity there. The corridor is empty; the lane did not fail.

City totals:

| City | Census | PF | NP | Unresolved |
|---|---|---|---|---|
| Columbia | 97 | 47 | 34 | 16 |
| West Columbia | 16 | 11 | 2 | 3 |
| Lexington | 7 | 3 | 4 | 0 |
| Blythewood | 4 | 2 | 2 | 0 |
| Elgin | 1 | 1 | 0 | 0 |

The West Columbia row includes the Cayce postal codes.

## Census lanes and quality challenge (Phases 6–8, 17)

**OSM** (Geofabrik South Carolina extract): 157 elements in the observation box.

**Brand inventory:**
- Marriott: 30 owned routes plus the SC sitemap page, all 30 read.
- Hilton: city pages and 42 sub-pages; 33 properties read.
- IHG: SC destination pages; 13 read.
- Choice: 8 city pages, 31 codes; 26 in-market properties read with **no 403 wall**.
- Hyatt: the explore-hotels service; 2 read.
- Best Western: hotels-details sitemap; 2 in-market.
- Red Roof: sitemap; 2 read.
- Extended Stay America: city pages; 4 read.
- Wyndham: sitemap plus the property service; 34 routes, of which 19 were read and 15 are retired.
- WoodSpring: sitemap; 2 read.
- InTown: brand city page; 3 read.
- Motel 6 / Studio 6: sitemap; 4 pages read.

**Tourism:** Experience Columbia SC, the Columbia CVB's Simpleview listing service under catid 22, returned 116 lodging listings.

**Competitor gap:**
- 17 leads came from BringFido search summaries and hotelguides.com lists.
- 6 matched census identities outright.
- The other 11 are aliases, rebrands or retired listings of census rows:
  - Graduate by Hilton
  - Motel 6 Fort Jackson (the same building as 7541 Nates Rd)
  - Lexington Inn & Suites (now the Fairfield at 131 Innkeeper Dr)
  - Best Western Plus Northeast (now the Holiday Inn & Suites at 7525 Two Notch)
  - Days Inn Riverbanks Zoo (the Days Inn at 1144 Bush River)
  - La Quinta Maingate (the La Quinta SE Fort Jackson)
  - Extended Stay America Irmo (ESA Northwest/Harbison)
  - Wingate Lexington (retired route; the Lexington Expo Hotel at 108 Saluda Pointe)
  - Microtel and Super 8 (name-only ties)
  - Embassy Suites Greystone (no longer in Hilton's Columbia inventory)
- **True missing hotels: 0.**

## Shadow package (Phases 18–20)

| Item | Value |
|---|---|
| Package | `pkg-columbia-sc-dcc242956732dee0` |
| Digest | `sha256:dcc242956732dee00448fb8597ca2e64d7e552f58097de5dae3758a6d471a8f9` |
| Receipt | `sha256:69f8bb7ce3af6e5b7a1af5479b9285243e392d8a421223768424b3662db4987b` |
| Zone | SHADOW_UNTIL_REGISTERED |
| Source commit | `fe2d1b6a` |
| Parent | Atlanta-live (branch lineage) |
| Package path | `markets/staging/columbia-sc/shadow_packages/columbia-sc/` |
| Receipt path | `markets/staging/columbia-sc/shadow_receipts/columbia-sc/` |
| FAST | **15/15 PASS**, 0 unknown, 0 failed, determinism BYTE_IDENTICAL, 72 declared routes |
| Reproduction | A clean worktree at `fe2d1b6a` with a copied document store rebuilt geography, brand pages, capture, census, clean set, staged authority, partition and shard with zero content difference. The eol-unattributed discovery config checks out as CRLF, but the rebuilt file equals the committed blob. A separate-process digest-only seal gave the same digest. |

## Not done, by design

- No shared factory code was changed.
- No registry, participation, closure, contract, global, identity-resolution or live-state file was edited.
- No broad regression was run.
- No final candidate was created.
- No founder authorization was created.
- Nothing was deployed.

Shared-factory observations, recorded and not repaired: the shared reader does not treat Hotel Trundle's refusal wording as operative; it classes Motel 6's "Pets welcome throughout your stay" as an amenity label; and it reads the Days Inn Airport acceptance as a service-animal statement.

## Next order — registration and reseal (when Columbia reaches the front of the lane)

1. Read CURRENT VERIFIED LIVE and merge that parent into this branch. This package's Atlanta binding then fails FAST rule N **by design**.
2. Copy the staged documents into their registered paths and repoint the helpers:
   - `markets/proposed/columbia-sc.json` → `markets/columbia-sc.json`
   - `identity_census_proposed/columbia-sc.json` → `identity_census/columbia-sc.json`
   - the staged `hotel_policy_facts_columbia-sc.json`, `columbia_sc_final_partition_007.json` and the authority shard → their registered paths

   Re-stage the census copy after ANY census edit.
3. Record a same-campus resolution in `identity_resolutions.json` for **400 Gervais Street** (Homewood Suites `caecahw` / Tru `caeruru`), which releases both pet-friendly holds. The Wyndham Garden / Hawthorn pair at 1539 Horseshoe Drive needs a first-party proof of two bookable hotels first.
4. Run `market_registration_cli --write`, `build_global_authority --write` then `--check`, and write the release contract.
5. Run `registration_release_lane register` and `seal --work-order` (a **new** package id), then FAST.
6. Run `regression_delta classify` (expect COMPOSITE_FRESH_MARKET_DATA_ONLY), compose and reproduce the candidate, and prepare the founder packet. Deploy only on founder authorization.
7. Before sealing, strengthen evidence:
   - re-read IHG `caedt` for a corrected postal code, IHG `caers` (Staybridge) for an FAQ answer, and Marriott `caenr` (StudioRes) for a Pet Policy row
   - find address-bearing InTown and Motel 6 documents
   - settle Flutter Wing's lodging category
   - route the map-only Knights Inn and Travelers Inn
