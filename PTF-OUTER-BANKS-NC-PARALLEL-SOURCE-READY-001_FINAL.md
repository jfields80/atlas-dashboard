# PTF-OUTER-BANKS-NC-PARALLEL-SOURCE-READY-001 — FINAL

Market `outer-banks-nc` ("Outer Banks, North Carolina"), branch `worker/ptf-outer-banks-nc-market-001`, built from zero on
the Asheville-live parent `e312caa6` (18 markets / 1195 profiles / 1408 routes).

**State: SOURCE READY — SHADOW_UNTIL_REGISTERED.** Outer Banks is sixth in the release queue:
Fayetteville (authorized, Netlify deploy blocked) → Jacksonville → Greenville → Atlanta → Outer Banks. It does not jump the queue.

Machine-readable accounting: `atlas-dashboard/launch_packages/pettripfinder/markets/reports/outer_banks_nc_source_ready_accounting_009.json`

## Timings (UTC, 2026-09-13)

| Phase | Observed |
|---|---|
| Start | **22:22:40Z** |
| Geography and corridor model | by 22:29:06Z (8 corridors, 10 ZIPs) |
| OSM lane | 417.8 s (220 hotel / motel / guest_house elements) |
| Brand lanes | Marriott NC sitemap page, 21 Hilton city pages, Wyndham sitemap + property service, IHG NC page (attended) |
| Visitors Bureau roster | every one of 1,290 `/listing/` pages at the site's `Crawl-delay: 2` (lodging slugs first) |
| First-party reads | attended Hilton 5, Marriott 2, IHG 2, Tranquil House 1; Wyndham 4; independents' own policy pages (65 sites, 265 documents) |
| Inputs committed | 23:40:12Z (`e636dcd5`) |
| Shadow seal + FAST | 23:40:19Z–23:40:53Z, **15/15 PASS** |
| Independent reproduction | 23:41:12Z–23:41:52Z, byte-identical |
| **ZERO_TO_SOURCE_READY** | **1 h 18 min 13 s** |

## Geography

The partition is by postal code. Kitty Hawk, Southern Shores and Duck share ZIP 27949, so they form one corridor. The accounting still reports each town separately.

| Class | Corridors (ZIPs) |
|---|---|
| CORE | Kitty Hawk / Southern Shores / Duck (27949); Kill Devil Hills / Colington (27948); Nags Head (27959); Manteo / Roanoke Island (27954) |
| CORRIDOR | Wanchese (27981); Corolla / Carova (27927) |
| FRINGE | Manns Harbor (27953); Point Harbor / Powells Point / Harbinger (27964, 27966, 27941) |
| OUTSIDE | Everything else, refused by name. This includes the Currituck mainland beyond Point Harbor, Stumpy Point, Elizabeth City, Edenton and Virginia Beach. |

**Hatteras Island and Ocracoke are OUTSIDE and preserved for a future `hatteras-ocracoke-nc` submarket.**
- Hatteras Island starts across Oregon Inlet, after about 13 miles of refuge and National Seashore with no lodging. Rodanthe is about 25 miles from Whalebone Junction; Hatteras village is about 60.
- Ocracoke is reachable only by ferry and is in Hyde County.
- They were observed, not ignored: **76** of the 78 OUTSIDE rows carry the `FUTURE_SUBMARKET hatteras-ocracoke-nc` reason.

## Accounting

| Measure | Value |
|---|---|
| TOTAL DISCOVERED (identity-graph candidates) | **209** |
| PROPOSED CENSUS | **55** |
| VALID PET-FRIENDLY | **26** |
| VALID VERIFIED-NO-PETS | **5** |
| RESOLVED / UNRESOLVED | **31 / 24** |
| Non-admitted | 154: OUTSIDE 78, NON-HOTEL 71, IDENTITY_REVIEW 3, NAME_ONLY 2 |

Every census identity has exactly one disposition, and every identity key is unique.

**Partition of the 55:**

| State | Count |
|---|---|
| PUBLISHED_PET_FRIENDLY | 26 |
| VERIFIED_NO_PETS | 5 |
| AWAITING_POLICY_OBSERVATION | 17 |
| ACCESS_BLOCKED | 5 |
| AWAITING_OFFICIAL_URL | 2 |

**Pet-friendly by source:** 17 independents (own sites), Hilton 4, Wyndham 3, Marriott 1, IHG 1.

**Verified no-pets:** Days Inn Kill Devil Hills Oceanfront – Wilbur, Fairfield Inn & Suites Nags Head, Oasis Suites, Scarborough Inn, Shutters on the Banks.

## Vacation-rental filter (71 NON-HOTEL, all with a stated reason)

| Kind | Count |
|---|---|
| Vacation-rental houses and realty / rental agencies | 41 |
| Cottage collections / cottage courts | 13 |
| Campgrounds / RV parks | 6 |
| Condo units | 5 |
| Timeshare / vacation ownership | 4 |
| Other | 2 |

- The four timeshare / vacation-ownership rows are Hilton Vacation Club Beachwoods, Barrier Island Station, Sea Scape Beach & Golf Villas and Villas at Spa Koru.
- The two "other" rows are Kitty Hawk Pier, which is not lodging, and the Friends of Elizabeth II guest house.
- Rows are refused either by the Visitors Bureau's own sub-category, when no brand or property page reached them, or by a named ruling in `outer_banks_nc_nonhotel_rulings_001.py`.
- Three rows whose lodging category could not be settled are held as identity reviews and never admitted: Ocean Villas, Ocean Villas II and Pierhouse B&B.

## Holds by class

| Class | Count | Notes |
|---|---|---|
| IDENTITY | 5 | Ocean Villas, Ocean Villas II and Pierhouse B&B (lodging category unconfirmed); Ocean House Motel and Ocean Side Court (name only) |
| ROUTING | 2 | Cameron House Inn and Inn at Corolla Light: no first-party route found |
| ACCESS-BLOCKED | 5 | Comfort Inn On The Ocean and Comfort Inn South Oceanfront (Choice bot-challenge shells); Burrus House and White Doe Inn (403, and browser navigation not permitted); Island House of Wanchese (domain does not resolve) |
| EVIDENCE | 17 | See the breakdown below |
| GEOGRAPHY | 0 | — |
| PAID | 2 | The two Choice rows, the same rows as ACCESS-BLOCKED; $0 spent |
| FOUNDER | 0 | — |
| OUTSIDE | 78 | 76 are the future Hatteras / Ocracoke submarket |
| NON-HOTEL | 71 | See the table above |
| Closed / retired routes | 2 | Wyndham Baymont Kitty Hawk; Days Inn & Suites Mariner (the building now trades as Mariner Inn & Suites on its own site) |

The 17 evidence holds break down as follows:
- **No policy on the property's own site:** First Colony Inn, Cypress House Inn, Colington Creek Inn, The Manteo House, Cavalier by the Sea, The Roanoke Bungalow.
- **Shared reader does not read the quote:** Tranquil House Inn ("No guest pets allowed."), Cypress Moon Inn and Ocean Sands. These are held, never reworded.
- **First-party conflicts:** Holiday Inn Express Kitty Hawk's heading welcomes pets but its description admits only service animals. The Pearl Hotel is a "No Pet facility" with one suite excepted.
- **Page states no bindable address:** Islander Motel (P.O. Box only), Fin N' Feather and Sandspur (no ZIP on the page).
- **Non-operative or amenity-only wording:** Driftin' Sands (amenity item), Dare Haven (marketing line), Nags Head Beach Inn (the managing agency's non-operative sentence).

## Corridor coverage

Each corridor shows its census count, pet-friendly (PF), verified no-pets (NP) and unresolved rows. A corridor page publishes only at 5 or more pet-friendly hotels.

| Corridor | Class | Census | PF | NP | Unres | Page |
|---|---|---|---|---|---|---|
| Kitty Hawk / Southern Shores / Duck | CORE | 4 | 2 | 0 | 2 | no |
| Kill Devil Hills | CORE | 18 | 10 | 2 | 6 | yes |
| Nags Head | CORE | 17 | 9 | 2 | 6 | yes |
| Manteo / Roanoke Island | CORE | 13 | 4 | 1 | 8 | no |
| Wanchese | CORRIDOR | 1 | 0 | 0 | 1 | no |
| Corolla | CORRIDOR | 2 | 1 | 0 | 1 | no |
| Manns Harbor | FRINGE | 0 | 0 | 0 | 0 | no |
| Point Harbor | FRINGE | 0 | 0 | 0 | 0 | no |

Town overlay, using each property's own stated city:

| Town | Census | PF | NP | Unres |
|---|---|---|---|---|
| Kitty Hawk | 3 | 1 | 0 | 2 |
| Duck | 1 | 1 | 0 | 0 |
| Southern Shores | 0 | 0 | 0 | 0 |
| Hatteras-area | outside (future submarket) | — | — | — |

## Identity findings

- **Rebrands settled by the property's own page:**

  | Address | Map label (stale) | Current, per own page |
  |---|---|---|
  | 107 S Virginia Dare Trail | Best Western Ocean Reef | Home2 Suites |
  | 401 N Virginia Dare Trail | Quality Inn | Spark by Hilton |
  | 814 US-64 | Elizabethan Inn | Hotel Manteo, Trademark Collection |
  | 7115 S Virginia Dare Trail | Owens' Motel | Mia's Boutique Hotel |
  | 1801 N Virginia Dare Trail | Days Inn & Suites | Mariner Inn & Suites |

- **One resort, two map house numbers:**
  - Sea Ranch Resort is mapped at both 1725 and 1731; its own page states 1731.
  - Outer Banks Motor Lodge is mapped at 1511; its own page states 1509.
  - Each pair was folded into the building that was read.
- **Competitor gap challenge:** all 12 leads matched first-party identities, and no competitor-only hotel remained.

## Shadow package

| Item | Value |
|---|---|
| Package | `pkg-outer-banks-nc-a1672c70bb080fd3` |
| Digest | `sha256:a1672c70bb080fd37932238964d9eff3127bb6fa1a24aeb7597f737c72b8202f` |
| Receipt | `sha256:a6157892ab6435bcdc574b48a616cec6102d9811d6c86fc29f766f600baf0583` |
| Staged input digest | `sha256:6262aa5c85521521c8e9878909fb5a35c6d8e81dd724dbe0d926159ac6f1d7d1` |
| Zone | SHADOW_UNTIL_REGISTERED |
| Source | `e636dcd5` |
| Package path | `markets/staging/outer-banks-nc/shadow_packages/outer-banks-nc/` |
| Receipt path | `markets/staging/outer-banks-nc/shadow_receipts/outer-banks-nc/` |
| FAST | 15/15 PASS, 0 unknown, 0 failed, determinism BYTE_IDENTICAL |

**Reproduction:**
- Sealed twice in-process with equal digests.
- In a clean `git worktree` at `e636dcd5`, a separate process sealed again and got the same digest.
- The derived chain (geography, capture, census, clean set, partition, staged authority, staged shard) was rebuilt from committed captures with zero content difference. Only the CRLF checkout of the eol-unattributed discovery config differed.
- The package sealed to the same digest a third time.

**Parent binding:** the package names the Asheville live release as its parent. FAST rule N fails it by design once the parent moves, and it is never selectable as a production release.

## Not done, by design

- No factory or shared code changed.
- No registry, participation, closure, pin, contract or global state touched. `identity_resolutions.json` is unchanged.
- No broad regression.
- No final candidate.
- No founder authorization.
- No deploy.
- $0 paid.

Two further notes:
- A trial seal written to a long scratch work directory failed rule J on a Windows path-length write error. It was re-run from the short directory `C:\t\obxfast` and passed; nothing from the trial was kept.
- The shared first-party reader does not interpret three quotes (listed above). This is recorded here and was not repaired.

## Next order (after Fayetteville, Jacksonville, Greenville and Atlanta are live)

1. Read the live parent. Rebase this branch onto it.
2. Copy the proposed documents into their registered paths:
   - `markets/proposed/outer-banks-nc.json` → `markets/`
   - `identity_census_proposed/outer-banks-nc.json` → `identity_census/`
   - The staged launch_package policy facts, partition and authority shard → their registered paths.
3. Run `market_registration_cli --write`, then `build_global_authority --write` and `--check`, then the release contract.
4. Run `registration_release_lane register` and `seal --work-order`. This produces a new package id.
5. Run `regression_delta classify`. Then compose and reproduce the candidate, and prepare the founder packet. Deploy only on authorization.
6. Before sealing, re-probe Choice, Burrus House and White Doe Inn.
