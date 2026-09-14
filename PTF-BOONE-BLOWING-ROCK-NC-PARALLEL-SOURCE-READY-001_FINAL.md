# PTF-BOONE-BLOWING-ROCK-NC-PARALLEL-SOURCE-READY-001 — FINAL

Market `boone-blowing-rock-nc` ("Boone – Blowing Rock, North Carolina"), branch `worker/ptf-boone-blowing-rock-nc-market-001`,
built from zero on the Asheville-live parent `e312caa6` (18 markets / 1195 profiles / 1408 routes).

**State: SOURCE READY — SHADOW_UNTIL_REGISTERED.** Boone – Blowing Rock is seventh in the release queue:
Fayetteville (authorized, Netlify deploy blocked) → Jacksonville → Greenville → Atlanta → Outer Banks → Boone – Blowing Rock.

Machine-readable accounting: `atlas-dashboard/launch_packages/pettripfinder/markets/reports/boone_blowing_rock_nc_source_ready_accounting_009.json`

## Timings (UTC)

| Phase | Observed |
|---|---|
| **BOONE_BLOWING_ROCK_START_TIMESTAMP** | **2026-09-14T00:29:27Z** (2026-09-13 20:29:27 EDT) |
| Geography and corridor model | by 00:41Z (5 corridors, 9 ZIPs) |
| OSM lane | 404.3 s (301 hotel / motel / guest_house / chalet / apartment elements) |
| Brand lanes | Marriott NC sitemap page, 18 Hilton city pages, Wyndham sitemap + property service, family probes (97 requests) |
| Destination rosters | Explore Boone listing service (8 "Hotels & Cabins" sub-categories, Crawl-delay 2); High Country Host roster |
| First-party reads | attended Hilton 2, Marriott 5, IHG 4; Wyndham 1 (5 retired routes); independents' own sites (40 sites, 114 documents) |
| Inputs committed | 00:57:43Z (`7adbafd1`) |
| Shadow seal + FAST | 00:57:52Z–00:58:40Z, **15/15 PASS** |
| Independent reproduction | 00:59:00Z–01:01Z, byte-identical |
| **ZERO_TO_SOURCE_READY** | **29 min 13 s** |

## Geography

Membership is the property's own postal code joined to a postal-code partition.

| Class | Corridors (ZIPs) |
|---|---|
| CORE | Boone / Appalachian State (28607, 28608); Blowing Rock (28605) |
| CORRIDOR | Valle Crucis / Vilas (28691, 28692); Deep Gap / US-421 East (28618) |
| FRINGE | Sugar Grove / Zionville / Todd (28679, 28698, 28684) |
| OUTSIDE | Everything else, refused by name: Banner Elk / Sugar Mountain / Seven Devils / Beech Mountain (28604) and the rest of Avery County (Linville, Newland, Elk Park, Crossnore, Pineola); West Jefferson / Jefferson (Ashe); Lenoir; Wilkesboro; Spruce Pine; Tennessee |

**Banner Elk / Sugar / Beech is a separate lodging cluster and is preserved for a future `banner-elk-sugar-beech-nc` submarket.**
It is an Avery County ski-and-golf resort cluster ~30 minutes from Boone, sharing ZIP 28604 across Banner Elk, Sugar Mountain,
Seven Devils and much of Beech Mountain. 28 of the 50 OUTSIDE rows carry the `FUTURE_SUBMARKET banner-elk-sugar-beech-nc` reason.

Edge cases, decided by the ZIP and recorded: Foscoe and the NC-105 side of Seven Devils admit only on a Boone 28607 address;
The Mast Farm Inn (Valle Crucis area) states Banner Elk 28604 and is preserved with the future submarket, not absorbed.

## Accounting

| Measure | Value |
|---|---|
| TOTAL DISCOVERED (identity-graph candidates) | **161** |
| PROPOSED CENSUS | **44** |
| VALID PET-FRIENDLY | **11** |
| VALID VERIFIED-NO-PETS | **5** |
| RESOLVED / UNRESOLVED | **16 / 28** |
| Non-admitted | 117: NON-HOTEL 51, OUTSIDE 50, NAME_ONLY 11, IDENTITY_REVIEW 5 |

Every census identity has exactly one disposition; every identity key is unique.
Partition of the 44: PUBLISHED_PET_FRIENDLY 11, VERIFIED_NO_PETS 5, AWAITING_POLICY_OBSERVATION 21, ACCESS_BLOCKED 6, AWAITING_OFFICIAL_URL 1.

**Pet-friendly (11):** Home2 Suites Boone, Hampton Inn & Suites Boone (Hilton); Fairfield Inn & Suites Boone, TownePlace Suites Boone
(Marriott); Holiday Inn Express Blowing Rock South (IHG); La Quinta Inn & Suites Boone University (Wyndham); Graystone Lodge,
Meadowbrook Inn, Azalea Garden Inn, Mountainaire Inn & Log Cabins, Blowing Rock Inn (own sites).

**Verified no-pets (5):** Courtyard Boone, SpringHill Suites Boone (Marriott Pet Policy row), Holiday Inn Boone – University Area,
Holiday Inn Express Boone (IHG FAQ), Hidden Valley Motel (own policies page).

## Vacation-rental / cabin filter (51 NON-HOTEL, every one with a stated reason)

| Kind | Count |
|---|---|
| Cabins, cottages & condos (bureau sub-category) | 32 |
| Cabin rental companies | 9 |
| Campgrounds / RV | 5 |
| Farm stays / event venues | 3 |
| Map cabins / cottages | 2 |

Map rows tagged `tourism=apartment` / `tourism=chalet` that no other lane typed as a hotel are refused as condo units / rental
chalets. The Explore Boone rule reads **every** sub-category a listing carries, because the bureau files the Holiday Inn Express
and La Quinta under "Meetings Facilities" first. Art of Living Retreat Center and Willow Valley Resort are held as
LODGING_CATEGORY_UNCONFIRMED (retreat campus; homeowner / legacy condo resort), never admitted.

## Holds by class

| Class | Count | Rows |
|---|---|---|
| IDENTITY | 16 | review 5 (Art of Living, Willow Valley, Blowing Rock Lodge and Hotel Portofino with no ZIP, a tied "Courtyard by Marriott" lead); name-only 11 (Chetola ×2, Green Park Inn ×2, Park Vista Inn ×2, Best Western Blue Ridge Plaza, Homestead Inn, Scottish Inns, Greenes Motel, Inn at the Ponds) |
| ROUTING | 1 | Aspen Acres Motel |
| ACCESS-BLOCKED | 6 | Comfort Suites, Quality Inn, Sleep Inn (Choice bot-challenge shells); Country Inn & Suites (Radisson); Ridgeway Inn (403); Yonahlossee (no answer) |
| EVIDENCE | 21 | see below |
| GEOGRAPHY | 0 | — |
| PAID | 4 | the Choice + Radisson rows (same rows as ACCESS-BLOCKED); $0 spent |
| FOUNDER | 0 | — |
| OUTSIDE | 50 | 28 future `banner-elk-sugar-beech-nc`; the rest Ashe, Lenoir, Wilkesboro and brand-page neighbours |
| NON-HOTEL | 51 | table above |
| Closed / retired routes | 5 | Wyndham: Days Inn Blowing Rock, Super 8 Boone, legacy La Quinta Boone route; Days Inn West Jefferson, Days Inn Lenoir |

Evidence holds (21):
- **Shared reader does not read the refusal / acceptance (held, never reworded):** The 1850 Hotel, The Windmoor Hotel, The Blowing Rock Manor ("is not pet-friendly"), Hemlock Inn ("pet-free"), Village Inn of Blowing Rock (operator sentence), Hillwinds Inn (amenity-chip wording).
- **FEE_ONLY to the shared reader:** Alpine Village Inn, Cliff Dwellers Inn, Rhode's Motor Lodge, The Inn at Crestwood.
- **Policy page states no bindable street + ZIP:** The Horton Hotel (FAQ: five pet-friendly rooms), Westglow (Lodges 2 and 3 only), Highland Hills (no ZIP), Lazy Bear Lodge ("No Pets").
- **Conditional / non-operative:** Lovill House Inn ("certain circumstances ... pet house"); Boxwood Lodge (own site no answer).
- **No pet wording on own site:** Blue Ridge Tourist Court, Gideon Ridge Inn, Hellbender Bed & Beverage, The Embers Hotel, The Inn at Ragged Gardens.

## Corridor coverage

| Corridor | Class | Census | PF | NP | Unres | Page (≥5 PF) |
|---|---|---|---|---|---|---|
| Boone / App State | CORE | 23 | 6 | 5 | 12 | yes |
| Blowing Rock | CORE | 20 | 5 | 0 | 15 | yes |
| Valle Crucis / Vilas | CORRIDOR | 1 | 0 | 0 | 1 | no |
| Deep Gap | CORRIDOR | 0 | 0 | 0 | 0 | no |
| Sugar Grove / Zionville / Todd | FRINGE | 0 | 0 | 0 | 0 | no |

Route overlay (reporting only — own stated street, then pin):

| Area | Census | PF | NP | Unres |
|---|---|---|---|---|
| Boone Downtown / App State | 5 | 2 | 0 | 3 |
| Boone US-321 | 4 | 2 | 1 | 1 |
| Boone US-421 | 5 | 1 | 1 | 3 |
| Boone NC-105 / Foscoe | 9 | 1 | 3 | 5 |
| Blowing Rock village | 13 | 4 | 0 | 9 |
| Blue Ridge Parkway / resort corridor | 7 | 1 | 0 | 6 |
| Valle Crucis / Vilas | 1 | 0 | 0 | 1 |
| Deep Gap | 0 | 0 | 0 | 0 |
| Banner Elk / Sugar / Beech | not included — future submarket | — | — | — |

## Identity findings

- The Windmoor Hotel's and The Blowing Rock Manor's JSON-LD carry The 1850 Hotel's address (775 W King St, Boone) — a shared
  operator template. Each is bound to the street its own page text states (125 Sunset Drive; 567 Main Street).
- The map draws TownePlace Suites Boone at 2240 Blowing Rock Road; the brand's own page states 1110 Meadowview Drive. The map row
  joins the read by its route.
- The Village Inns of Blowing Rock operate Village Inn, Hillwinds Inn and Boxwood Lodge as three distinct buildings.
- Competitor gap challenge: 17 leads, 11 matched first-party identities, 6 competitor-only leads remain name-only; no competitor-only hotel admitted.

## Shadow package

| Item | Value |
|---|---|
| Package | `pkg-boone-blowing-rock-nc-f96555872b51866d` |
| Digest | `sha256:f96555872b51866d162c0247bfbe1ddc4770a315ea5890d40c8b991cb6629b24` |
| Receipt | `sha256:ec396b132489c5b1647c2266230dd37363dbb069341f86ecb1b8f5502826ea7c` |
| Staged input digest | `sha256:6495b8f86d1a556d433e7f6e5432ea1b8fb0f7dfe462880e64af4b278a42f549` |
| Zone | SHADOW_UNTIL_REGISTERED |
| Source | `7adbafd1` |
| Package path | `markets/staging/boone-blowing-rock-nc/shadow_packages/boone-blowing-rock-nc/` |
| Receipt path | `markets/staging/boone-blowing-rock-nc/shadow_receipts/boone-blowing-rock-nc/` |
| FAST | 15/15 PASS, 0 unknown, 0 failed, determinism BYTE_IDENTICAL |

Reproduction: sealed twice in-process (equal digests); a separate process in a clean `git worktree` at `7adbafd1` sealed the same
digest; geography, brand pages, capture, census, clean set, staged authority, partition and staged shard were rebuilt there from
committed captures with zero content difference (only the CRLF checkout of the eol-unattributed discovery config differed); the
package sealed to the same digest a third time.

Parent binding: the package names the Asheville live release. FAST rule N fails it by design once the parent moves; it is never
selectable as a production release.

## Not done, by design

No factory or shared code changed. No registry, participation, closure, pin, contract, global or `identity_resolutions.json` change.
No broad regression. No final candidate. No founder authorization. No deploy. $0 paid.

## Next order (after Fayetteville, Jacksonville, Greenville, Atlanta and Outer Banks are live)

1. Read the live parent; rebase this branch onto it.
2. Copy `markets/proposed/boone-blowing-rock-nc.json`, `identity_census_proposed/boone-blowing-rock-nc.json` and the staged
   launch_package documents into their registered paths.
3. `market_registration_cli --write`, `build_global_authority --write` / `--check`, release contract.
4. `registration_release_lane register` + `seal --work-order` (new package id), `regression_delta classify`, compose and reproduce
   the candidate, founder packet; deploy only on authorization.
5. Before sealing, re-probe Choice, Country Inn & Suites, Best Western Blue Ridge Plaza, Ridgeway Inn, Homestead Inn and
   Yonahlossee; find first-party addresses for Chetola and Green Park Inn.
