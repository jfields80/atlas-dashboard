# PTF-HICKORY-NC-PARALLEL-SOURCE-READY-001 — FINAL

Market `hickory-nc` ("Hickory – Newton – Conover, North Carolina"), branch `worker/ptf-hickory-nc-market-001`,
built from zero.

**Live parent.** The worktree started at the Fayetteville-live commit `ec764bef`. The branch had no commits of its own,
so it was fast-forwarded to the current verified live commit before any work: **Greenville** (`595bfeeb`, deploy
`6aa75f87aebd8377ccd67304`, 20 markets / 1229 profiles / 1449 routes). The live state was checked again before the
first commit, and it had not moved.

**State: SOURCE READY — SHADOW_UNTIL_REGISTERED.** Hickory waits in the source-ready release queue. The queue itself is
handled separately.

Machine-readable accounting: `atlas-dashboard/launch_packages/pettripfinder/markets/reports/hickory_nc_source_ready_accounting_009.json`

## Timings (UTC)

| Phase | Observed |
|---|---|
| **HICKORY_START_TIMESTAMP** | **2026-09-14T02:51:52Z** (2026-09-13 22:51:52 EDT) |
| Precheck, fast-forward, template read | 02:51Z–02:58Z |
| Geography and corridor model | by 03:05Z (9 corridors, 12 ZIPs) |
| Census lanes | OSM 421.5 s (run detached); brand inventory 97 requests; Visit Hickory Metro listing service 5 requests |
| Identity work | three census passes, plus the non-hotel and rebrand rulings |
| Routing and static evidence | Wyndham property service 1.8 s (15 routes); static pages 1.3 s; policy-page lane 1.4 s |
| Browser evidence | 03:07Z–03:17Z (Marriott 3, Hilton 3, IHG 3, Best Western, Red Roof, Motel 6 / Studio 6, 4 independents) |
| Policy adjudication and reconciliation | 03:12Z–03:20Z |
| Inputs committed | 03:20:50Z (`61dd835a`), re-staged at `3400a148` (see Reproduction) |
| Shadow seal + FAST | 03:23:00Z–03:23:47Z, **15/15 PASS** |
| Independent reproduction | 03:23:50Z–03:24:17Z, byte-identical |
| **ZERO_TO_SOURCE_READY** | **31 min 55 s** |
| Peak memory | not instrumented |

## Geography

Membership comes from the property's own postal code, looked up in a postal-code partition.

| Class | Corridors (ZIPs) |
|---|---|
| CORE | Hickory, including Long View and Mountain View, which use Hickory ZIPs (28601, 28602, PO 28603); Conover (28613); Newton (28658) |
| CORRIDOR | Claremont, I-40 exit 135 (28610); Granite Falls / Sawmills, US-321 north (28630) |
| FRINGE | Hildebran / Icard, I-40 exits 118–119 (28637, 28666); Maiden (28650); Catawba (28609); Hudson (28638) |
| OUTSIDE | **Lenoir (28645 / 28633), kept as future submarket `lenoir-nc`**; Morganton / Valdese (Burke); Statesville; Taylorsville; Lincolnton; Denver / Sherrills Ford / Mooresville (Lake Norman); Boone / Blowing Rock; Collettsville |

**Lenoir was evaluated explicitly.** It is the Caldwell County seat, 20–25 minutes up US-321, past Granite Falls and
Hudson. Its hotels sit on US-321 / Blowing Rock Boulevard and NC-18, and they serve Lenoir itself and the Blue Ridge
gateway. That makes it a separate lodging cluster. Four Lenoir hotels (Hampton Inn & Suites, Days Inn, Comfort Inn,
American Motel) are recorded OUTSIDE as `FUTURE_SUBMARKET lenoir-nc`.

## Accounting

| Measure | Value |
|---|---|
| TOTAL DISCOVERED (identity-graph candidates, whole observation box) | **137** |
| PROPOSED CENSUS | **22** |
| VALID PET-FRIENDLY | **9** |
| VALID VERIFIED-NO-PETS | **4** |
| RESOLVED / UNRESOLVED | **13 / 9** |
| Non-admitted | 115: OUTSIDE 90, NON-HOTEL 15, IDENTITY 10 (review 4, name-only 4, rebrand / co-location 2) |

Every census identity has exactly one disposition, and every census identity key is unique.
Partition of the 22: PUBLISHED_PET_FRIENDLY 9, VERIFIED_NO_PETS 4, AWAITING_POLICY_OBSERVATION 5, AWAITING_OFFICIAL_URL 4.

**Pet-friendly (9):**
- Hilton: Hampton Inn Hickory, Hilton Garden Inn Hickory, Home2 Suites Hickory.
- Marriott: TownePlace Suites Hickory.
- IHG: Crowne Plaza Hickory (pet rooms on the first floor).
- Wyndham property service: Days Inn & Suites Hickory, Days Inn Conover-Hickory.
- Red Roof Inn Hickory.
- Affordable Suites of America Hickory/Conover, from its own location page.

**Verified no-pets (4):** Fairfield Inn & Suites Hickory ("Pets Not Allowed"); Holiday Inn Express Hickory-Hickory Mart
and Holiday Inn Express & Suites Conover (IHG FAQ); The Trott House Inn, Newton ("pets are not permitted at the inn").

Fee rules applied (market-local):
- Tiered fees publish no amount. This covers the Hilton "$75(1-4n),$125(5+n)" style rows and TownePlace, which carries
  both a per-stay and a per-night label.
- Red Roof's first pet stays free and a second pet costs $15/night with a cap, so no single fee is published.
- Affordable Suites publishes $25 per pet per night, non-refundable, as stated. Its $150 cap is recorded only in the quote.
- Crowne Plaza publishes $55 per stay, non-refundable. Its separate $55 damage deposit is not read onto the fee.

## Holds by class

| Class | Count | Rows |
|---|---|---|
| IDENTITY | 10 | **Choice:** Sleep Inn, 1179 13th Ave Dr SE (its bare key is already Charlotte's); Quality Suites, 1125 13th Ave Dr SE (key already Louisville's); Comfort Inn & MainStay Suites, 1607 Fairgrove Church Rd — one bureau listing, two Choice flags in search summaries, and a map label for La Quinta, whose route is retired. **G6:** Motel 6 / Studio 6 Hickory, two property ids at 484 US-70 SW, co-location unproven. **Lodging category unconfirmed:** The Lodge at Rock Barn (member club; its lodging page returns 404); Henry River Mill Village (an attraction offering "overnight accommodations" but no room inventory). **Name-only:** map "Econo Lodge" pin beside the Red Roof; Comfort Inn Conover-Hickory, MainStay Suites Conover-Hickory, Budget Inn Express Hickory |
| ROUTING | 4 | Gateway Extended Stay (915 Hotel Dr SW); Fran Mar Motel (2710 US-70 SW); Lowman's Motor Court (Hildebran); Claremont Inn & Suites (former Super 8 Claremont). All are map-only, with no first-party route |
| ACCESS-BLOCKED | 0 | Choice served an empty document (nc146), but its three buildings are identity holds, not census rows |
| EVIDENCE | 5 | Baymont Hickory — the shared reader returns **SERVICE_ANIMAL_ONLY** for "Up to 2 pets … are welcome for a non-refundable charge of 20.00 USD per night …"; held, never reworded. Courtyard Hickory — its own row prints "Pets Welcome" above "Pets Not Allowed" (FIRST_PARTY_CONFLICT). Best Western Hickory — "Pets may be accepted. Please contact the hotel" (QUOTE_NOT_OPERATIVE). 2nd Street Inn and The Dragonfly Inn — no operative pet wording |
| GEOGRAPHY | 0 | — |
| PAID | 0 | $0 spent; the Choice rows become paid candidates only after their identity clears |
| FOUNDER | 0 | — |
| OUTSIDE | 90 | Statesville, Mooresville / Cornelius / Lake Norman, Morganton / Connelly Springs, Lenoir (future submarket), Lincolnton, Taylorsville, Boone, Wilkesboro, Jonesville, plus name-only map pins outside every admitting cell |
| NON-HOTEL | 15 | 8 apartment rows (map tourism=apartment); campgrounds / RV 3; Catholic Conference Center (retreat facility) and Rock Barn Country Club; the Townhomes at Rock Barn; Flying Squirrel Cottages (rental company) |
| Closed / retired routes | 8 | Wyndham: La Quinta Hickory (Conover), Ramada Conover-Hickory Area, Super 8 Claremont; outside the market, Baymont / Ramada / Super 8 Statesville, Days Inn Lenoir, Days Inn & Suites Morganton |

## Corridor coverage

| Corridor | Class | Census | PF | NP | Unres | Page (≥5 PF) |
|---|---|---|---|---|---|---|
| Hickory | CORE | 16 | 7 | 2 | 7 | **yes** |
| Conover | CORE | 3 | 2 | 1 | 0 | no |
| Newton | CORE | 1 | 0 | 1 | 0 | no |
| Claremont | CORRIDOR | 1 | 0 | 0 | 1 | no |
| Granite Falls / Sawmills | CORRIDOR | 0 | 0 | 0 | 0 | no |
| Hildebran / Icard | FRINGE | 1 | 0 | 0 | 1 | no |
| Maiden, Catawba, Hudson | FRINGE | 0 | 0 | 0 | 0 | no |

Area overlay (reporting only):

| Area | Census | PF | NP | Unres |
|---|---|---|---|---|
| Hickory downtown / central | 2 | 0 | 0 | 2 |
| I-40 Hickory (13th Ave Dr / Lenoir-Rhyne Blvd / US-70) | 12 | 6 | 2 | 4 |
| US-321 Hickory | 0 | 0 | 0 | 0 |
| Long View / Mountain View | 0 | 0 | 0 | 0 |
| Hickory (other) | 2 | 1 | 0 | 1 |
| Conover | 3 | 2 | 1 | 0 |
| Newton | 1 | 0 | 1 | 0 |

- The US-321 south-west strip has no census hotel. The map, the bureau and the brand rosters list none there. Hickory's
  lodging clusters at I-40 exits 125–126.
- Long View's map rows (Fran Mar Motel, on US-70 SW) report under the I-40 / US-70 overlay.
- Only the Hickory corridor meets the page threshold. FAST's cold build generated `/pet-friendly-hotels/hickory-nc/hickory/`.

## Owned data

- **OWNED IDENTITIES:** 0. No registered census holds a row in any Hickory-market ZIP.
- **OWNED ROUTES:** 0. The committed national harvest has no Hickory-area lead.
- **OWNED VALID POLICY EVIDENCE:** 0. Every record is a new first-party capture from this order.

## Identity findings and competitor gap

- **1607 Fairgrove Church Road, Conover.** The bureau lists "Comfort Inn & Main Stay Suites" there (Choice nc408). The map
  still says La Quinta, whose Wyndham route is retired. Search summaries describe two Choice hotels ("Building A").
  Choice's page cannot be read, so the site is held rather than split or merged by guess.
- **Motel 6 and Studio 6 Hickory** were found through the brand's own city page. They were absent from OSM, the bureau
  and the rosters. Both property pages state 484 US-70 SW 28602. They are held as one unproven co-location.
- **Red Roof Inn Hickory** (1184 Lenoir-Rhyne Blvd). The bureau row had no street; the brand page supplied it. A stale map
  "Econo Lodge" pin sits on the same spot and stays name-only.
- **TownePlace Suites.** Its own page states 28601, while the bureau says 28602. The page wins, and both ZIPs belong to the
  same corridor.
- **Competitor challenge:** 12 leads.
  - EXACT MATCH or ALIAS: 9. Motel 6 and Studio 6 count here, as missing identities returned through the brand's own pages.
  - REVIEW: 2 (the two Choice flags at Fairgrove Church Road).
  - REBRAND: 1 (Budget Inn Express, a booking slug for the Motel 6).
  - No competitor-only hotel was admitted, and no competitor pet claim was read.

## Shadow package

| Item | Value |
|---|---|
| Package | `pkg-hickory-nc-40470cd4656e71cb` |
| Digest | `sha256:40470cd4656e71cba17f03e51c541f8fa97d028b9958a97499306b53488ef61d` |
| Receipt | `markets/staging/hickory-nc/shadow_receipts/hickory-nc/pkg-hickory-nc-40470cd4656e71cb-71a33da73a895cdf.json` |
| Zone | SHADOW_UNTIL_REGISTERED |
| Source | `3400a148` |
| FAST | 15/15 PASS, 0 unknown, 0 failed |

**Reproduction.**
- The package was sealed twice in-process, with equal digests.
- A clean `git worktree` at `3400a148` rebuilt geography, brand pages, capture, census, clean set, staged authority,
  partition and staged shard from committed captures. The rebuild showed zero content difference; the discovery config
  differed only by line endings (CRLF checkout of an eol-unattributed file). A separate-process seal there produced the
  same digest.
- The first clean-worktree rebuild, at `61dd835a`, found a real market-local defect. The staged
  `launch_package/identity_census` copy had been taken before two source-authority lines were corrected. That first seal
  (`pkg-hickory-nc-5f172c50`) was never committed and was discarded. The copy was re-staged (`3400a148`), and the package
  was re-sealed and reproduced.

**Parent binding.** The package names the Greenville live release. FAST rule N will fail it by design once the parent
moves, so it can never be selected as a production release.

## Not done, by design

- No factory or shared code changed.
- No change to the registry, participation, closure, pins, contracts, globals or `identity_resolutions.json`.
  Registered censuses were read only, for the cross-market key check.
- No broad regression, no final candidate, no founder authorization, no deploy. $0 paid. No founder intervention.

## Next order (when Hickory reaches the front of the release queue)

1. Read CURRENT VERIFIED LIVE and rebase onto it.
2. Copy the proposed market, the proposed census and the staged launch_package documents into their registered paths.
3. Run `market_registration_cli --write`, `build_global_authority --write` / `--check`, and the release contract.
4. Run `registration_release_lane register` + `seal --work-order` (new package id), then `regression_delta classify`.
   Compose and reproduce the candidate, then prepare the founder packet.
5. Before sealing:
   - re-probe Choice (Sleep Inn, Quality Suites, Comfort Inn / MainStay Conover);
   - open Motel 6 / Studio 6's client-rendered pet policy;
   - look for first-party routes for Gateway Extended Stay, Fran Mar Motel, Lowman's Motor Court and Claremont Inn & Suites.
