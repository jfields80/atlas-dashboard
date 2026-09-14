# PTF-PINEHURST-SOUTHERN-PINES-NC-PARALLEL-SOURCE-READY-001 — FINAL

Market `pinehurst-southern-pines-nc` ("Pinehurst – Southern Pines – Aberdeen, North Carolina"), branch
`worker/ptf-pinehurst-southern-pines-nc-market-001`, built from zero.

**Live parent.** The branch started at the Asheville-live commit `e312caa6`. Before any commit, the live-state record moved:
Fayetteville went live (`ec764bef`, deploy `6aa750d8fa36419d3c84ecbc`, 19 markets / 1221 profiles / 1438 routes). The branch
was fast-forwarded to `ec764bef`, so the shadow package binds to **Fayetteville** as the current verified live parent.

**State: SOURCE READY — SHADOW_UNTIL_REGISTERED.** Release queue: Jacksonville → Greenville → Atlanta → Outer Banks →
Boone – Blowing Rock → Pinehurst – Southern Pines.

Machine-readable accounting: `atlas-dashboard/launch_packages/pettripfinder/markets/reports/pinehurst_southern_pines_nc_source_ready_accounting_009.json`

## Timings (UTC)

| Phase | Observed |
|---|---|
| **PINEHURST_SOUTHERN_PINES_START_TIMESTAMP** | **2026-09-14T01:31:50Z** (2026-09-13 21:31:50 EDT) |
| Geography and corridor model | by 01:52Z (7 corridors, 11 ZIPs) |
| OSM lane | 438.7 s (40 lodging elements) |
| Brand lanes | Marriott NC sitemap page, 17 Hilton city pages, Wyndham sitemap + property service, family probes (96 requests) |
| Destination roster | the CVB lodging page plus the one partner-index query it declares (49 listings, 2 requests) |
| First-party reads | attended Marriott 4, IHG 1, Best Western 1; Hilton 3 reused (owned); Wyndham 3 plain-client; independents' own sites (22 sites, 87 documents, plus 4 attended) |
| Inputs committed | 02:03:14Z (`9690624b`) |
| Shadow seal + FAST | 02:03:21Z–02:03:47Z, **15/15 PASS** |
| Independent reproduction | 02:04Z–02:06Z, byte-identical |
| **ZERO_TO_SOURCE_READY** | **31 min 57 s** |

## Geography

Membership comes from the property's own postal code, looked up in a postal-code partition.

| Class | Corridors (ZIPs) |
|---|---|
| CORE | Pinehurst incl. Taylortown, the resort district and the Moore Regional ring (28374, PO 28370); Southern Pines (28387, PO 28388); Aberdeen (28315) |
| CORRIDOR | Pinebluff (28373); Whispering Pines / Carthage (28327, one shared ZIP) |
| FRINGE | Vass / Lakeview / Cameron (28394, 28326); Seven Lakes / West End / Foxfire / Jackson Springs (27376, 27281) |
| OUTSIDE | Refused by name: Robbins / Eagle Springs (northern Moore); Sanford (Lee); Fayetteville / Spring Lake / Fort Liberty / Hope Mills; Raeford (Hoke); Rockingham / Hamlet / Hoffman / Ellerbe (Richmond); Laurinburg (Scotland); Candor / Biscoe / Troy / Star (Montgomery) |

The Moore County medical / business cluster (FirstHealth Moore Regional) sits inside Pinehurst 28374. It is reported as a
coverage overlay, not a separate corridor. It is not materially distinct.

**Golf / resort rule applied.** A resort complex is decided by premises. The Pinehurst Resort buildings are separate hotel
identities: the Carolina Hotel (80 Carolina Vista Dr), the Holly Inn (155 Cherokee Rd), the Manor (5 Community Rd) and
the Magnolia Inn (65 Magnolia Rd, whose own domain now redirects to pinehurst.com). The bureau lists "Pinehurst Resort" at
the Carolina Hotel's street, so that row is named for the hotel. The resort's "Carolina Villas" and "Condos at Pinehurst"
also print that street. A guard stops them folding into the hotel, and they are refused as condos/villas. Golf-package
operators (Maples, Talamore, Legacy, First Tee), the Mid South lodges, Knollwood Village, rental companies and a
whole-property rental (The Old Church) are NON-HOTEL.

## Accounting

| Measure | Value |
|---|---|
| TOTAL DISCOVERED (identity-graph candidates) | **89** |
| PROPOSED CENSUS | **25** |
| VALID PET-FRIENDLY | **8** |
| VALID VERIFIED-NO-PETS | **2** |
| RESOLVED / UNRESOLVED | **10 / 15** |
| Non-admitted | 64: OUTSIDE 30, NON-HOTEL 21, NAME_ONLY 11, IDENTITY_REVIEW 2 |

Every census identity has exactly one disposition, and every identity key is unique.
Partition of the 25: PUBLISHED_PET_FRIENDLY 8, VERIFIED_NO_PETS 2, AWAITING_POLICY_OBSERVATION 12, ACCESS_BLOCKED 3.

**Pet-friendly (8):** Hampton Inn & Suites Southern Pines-Pinehurst, Hilton Garden Inn Southern Pines Pinehurst, Homewood
Suites Olmsted Village (Hilton, owned reads); Courtyard Southern Pines Aberdeen, Residence Inn Pinehurst Southern Pines,
TownePlace Suites Southern Pines Aberdeen (Marriott Pet Policy row); Microtel Inn & Suites Southern Pines / Pinehurst
(Wyndham property service); SureStay Plus Southern Pines Pinehurst (Best Western property page).

**Verified no-pets (2):** SpringHill Suites Pinehurst Southern Pines ("Pets Not Allowed"); Holiday Inn Express & Suites
Southern Pines-Pinehurst Area (IHG FAQ).

Fee guards (market-local):
- Tiered fees publish no amount: the Hilton rows ("$50(1-4n),$100(5+n)"), Courtyard and TownePlace.
- Residence Inn's "Per Stay: $150.00" label sits beside "USD 50 per night fee up to USD 150 max". That is a nightly fee
  with a cap, so no fee is published.
- SureStay's quote stops before its separate refundable-deposit sentence, so no refundability is read onto the fee.

## Holds by class

| Class | Count | Rows |
|---|---|---|
| IDENTITY | 13 | review 2: Duncraig Manor (now an event venue; lodging unconfirmed); Econo-Lodge, 408 W Morganton Rd (its only labels collide with registered keys in Lexington, Toledo, Fayetteville and Grand Rapids, and Choice served a bot shell). Name-only 11: map "Motel 6" label on the AmeriVu site; stale competitor flags Days Inn Conference Center and Super 8 Aberdeen; a competitor spelling of SureStay Plus; competitor B&B names with no first-party address (Knollwood House — domain lapsed — Beggar's Ride, Conroy B&B, Pine Gables of Aberdeen, Duck Smith House, Lucky Bar Farm, The MacPherson House) |
| ROUTING | 0 | — |
| ACCESS-BLOCKED | 3 | Clarion Inn, Comfort Inn Pinehurst, Quality Inn Pinehurst (Choice: sitemap timeout plus an attended bot-challenge shell, never bypassed) |
| EVIDENCE | 12 | see below |
| GEOGRAPHY | 0 | — |
| PAID | 3 | the three Choice rows (same rows as ACCESS-BLOCKED); $0 spent |
| FOUNDER | 0 | — |
| OUTSIDE | 30 | Sanford, Fayetteville / Spring Lake, Raeford, Rockingham, Laurinburg, Lumberton, Pittsboro, Asheboro, Holly Springs / Cary brand-page neighbours, and Solomon's Inn (Robbins) |
| NON-HOTEL | 21 | condo / villa / rental management 10, campground / RV 5, golf-package villas 2, vacation rental 2, farm / venue 1, map cottage 1 |
| Closed / retired routes | 4 | Wyndham: Days Inn Conference Center Southern Pines (now Clarion Inn), Super 8 Aberdeen (now AmeriVu), legacy Microtel route, Days Inn Rockingham |

Evidence holds (12):
- **Shared reader does not read the refusal (held, never reworded):** The Carolina Hotel, The Holly Inn, The Manor,
  The Magnolia Inn. Pinehurst Resort's FAQ says "Pinehurst is a pet-free facility." The reader returns
  QUOTE_NOT_OPERATIVE, and the FAQ page states no street for each hotel.
- **Amenity chip only:** AmeriVu Inn & Suites Aberdeen ("Pet-Friendly").
- **No pet wording on the property's own pages:** Pine Crest Inn, Pine Needles Lodge & Golf Club, The Inn at Mid Pines,
  The Jefferson Inn (the operator's FAQ names dog-friendly rooms only at an Elkin property), Carolina Pine Inn, The Old
  Buggy Inn, 1878 Bed and Breakfast.

## Corridor coverage

| Corridor | Class | Census | PF | NP | Unres | Page (≥5 PF) |
|---|---|---|---|---|---|---|
| Pinehurst | CORE | 8 | 1 | 1 | 6 | no |
| Southern Pines | CORE | 8 | 3 | 1 | 4 | no |
| Aberdeen | CORE | 6 | 4 | 0 | 2 | no |
| Pinebluff | CORRIDOR | 1 | 0 | 0 | 1 | no |
| Whispering Pines / Carthage | CORRIDOR | 1 | 0 | 0 | 1 | no |
| Vass / Cameron | FRINGE | 1 | 0 | 0 | 1 | no |
| Seven Lakes / West End / Foxfire | FRINGE | 0 | 0 | 0 | 0 | no |

Market total PF = 8, which meets the market minimum of 5. No corridor page meets its own threshold of 5.

Area overlay (reporting only):

| Area | Census | PF | NP | Unres |
|---|---|---|---|---|
| Pinehurst village / resort district | 6 | 1 | 0 | 5 |
| Moore Regional medical / business ring | 2 | 0 | 1 | 1 |
| Southern Pines downtown | 7 | 2 | 1 | 4 |
| US-1 corridor | 3 | 1 | 0 | 2 |
| Aberdeen US-15-501 / NC-5 | 5 | 4 | 0 | 1 |
| Whispering Pines / Carthage | 1 | 0 | 0 | 1 |
| Vass / Cameron | 1 | 0 | 0 | 1 |
| Seven Lakes / West End / Foxfire | 0 | 0 | 0 | 0 |

## Owned data

- **OWNED IDENTITIES:** 18 Moore County rows are observed in the registered Fayetteville census, all OUTSIDE_MARKET there.
  None was imported. Every identity here was rebuilt from this order's lanes.
- **OWNED ROUTES:** 7 Southern Pines brand routes appear in Fayetteville's brand lanes (4 Marriott, 3 Hilton), plus
  Wyndham's Microtel / Days Inn / Super 8 routes. The committed national harvest has no Sandhills route. Every route was
  re-derived from the brand's current inventory.
- **OWNED VALID POLICY EVIDENCE:** 3 — the Fayetteville order's attended Hilton reads from 2026-09-13 (HGI, Hampton,
  Homewood). They were reused with their document sha256s and the source payload digest recorded.

## Identity findings

- SpringHill Suites: the brand page states 10024 US Highway 15/501, **Pinehurst 28374**. The map says Southern Pines 28387.
  The bureau prints "NC 10024". The page wins; the map and bureau rows join it by route.
- 1408 N Sandhills Blvd has three names in the evidence: Super 8 (map, retired Wyndham route), Motel 6 (a directory) and
  AmeriVu Inn & Suites (the bureau and the hotel's own site). The own site's current name is used.
- 805 SW Service Road: the Days Inn Conference Center route is retired, and the bureau and map list the building as
  Clarion Inn.
- Competitor gap challenge: 16 leads. 6 matched first-party identities; 10 are competitor-only and remain name-only. No
  competitor-only hotel was admitted.

## Shadow package

| Item | Value |
|---|---|
| Package | `pkg-pinehurst-southern-pines-nc-d3268420b13808f8` |
| Digest | `sha256:d3268420b13808f8cff892a6b93dc190565b7612f4c40f55c03b0c4fe67f8206` |
| Receipt | `sha256:3bdbdd648b35ff8a0a4e90f952b0e656135e8d957ed657a079584b65475a4173` |
| Staged input digest | `sha256:dd27b2692279ed4f58c7be1ae746ce78de0bf131b64862175469a41de48a853f` |
| Zone | SHADOW_UNTIL_REGISTERED |
| Source | `9690624b` |
| Package path | `markets/staging/pinehurst-southern-pines-nc/shadow_packages/pinehurst-southern-pines-nc/` |
| Receipt path | `markets/staging/pinehurst-southern-pines-nc/shadow_receipts/pinehurst-southern-pines-nc/` |
| FAST | 15/15 PASS, 0 unknown, 0 failed, determinism BYTE_IDENTICAL |

**Reproduction.** The package was sealed twice in-process with equal digests. A separate process in a clean `git worktree`
at `9690624b` sealed the same digest. In that worktree, geography, brand pages, capture, census, clean set, staged
authority, partition and staged shard were rebuilt from committed captures, with zero content difference. The only
difference was the worktree's CRLF checkout of the eol-unattributed discovery config. The package sealed to the same
digest a third time.

**Parent binding.** The package names the Fayetteville live release. FAST rule N fails it by design once the parent moves,
so it can never be selected as a production release.

## Not done, by design

- No factory or shared code changed.
- No registry, participation, closure, pin, contract, global or `identity_resolutions.json` change. Shared censuses were
  read only, for the cross-market key check.
- No broad regression, no final candidate, no founder authorization, no deploy. $0 paid.

## Next order (after Jacksonville, Greenville, Atlanta, Outer Banks and Boone – Blowing Rock are live)

1. Read the live parent and rebase this branch onto it.
2. Copy `markets/proposed/pinehurst-southern-pines-nc.json`, `identity_census_proposed/pinehurst-southern-pines-nc.json`
   and the staged launch_package documents into their registered paths.
3. Run `market_registration_cli --write`, `build_global_authority --write` / `--check`, and the release contract.
4. Run `registration_release_lane register` + `seal --work-order` (new package id) and `regression_delta classify`;
   compose and reproduce the candidate and the founder packet. Deploy only on authorization.
5. Before sealing:
   - re-probe Choice (Clarion, Comfort Inn, Quality Inn, Econo Lodge — the Econo Lodge also needs its first-party name);
   - seek a per-hotel Pinehurst Resort policy statement the reader interprets;
   - re-read Pine Crest Inn's script-rendered pages.
