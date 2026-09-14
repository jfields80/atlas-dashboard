# PTF-CHARLESTON-SC-PARALLEL-SOURCE-READY-001 — FINAL

Market `charleston-sc` ("Charleston, South Carolina"), branch `worker/ptf-charleston-sc-market-001`. Built from zero on the
**Atlanta-live** release (`6825851b`, deploy `6aa7f125a91c73ba2363139e`, 23 markets / 1500 profiles / 1744 routes, read
mechanically from the live index; live-index digest `sha256:b403b7a1…`).

**State: SOURCE READY — SHADOW_UNTIL_REGISTERED.** Charleston waits for its turn in the serialized release lane.

Machine-readable accounting: `atlas-dashboard/launch_packages/pettripfinder/markets/reports/charleston_sc_source_ready_accounting_009.json`

## Timings (UTC, 2026-09-14)

| Phase | Observed |
|---|---|
| **CHARLESTON_START_TIMESTAMP** | **14:08:03Z** |
| Precheck and template read | 14:08Z–14:18Z |
| Geography | 14:18:45Z |
| Census lanes | OSM 164.4 s; brand inventory ~15 min detached; Charleston Area CVB roster 21.2 s (plain client) |
| Routing | Wyndham property service 6.4 s; static lane 8.7 s |
| Browser evidence | 14:31Z–14:41Z (IHG 17, Hyatt 8, Choice 32, Marriott 34, Hilton 41, Best Western 8, Red Roof 2); ESA 5 at 14:55Z |
| Static evidence | policy-page lane 32–40 s per pass (3 passes, 88 sites) |
| Identity / policy adjudication | 14:41Z–15:00Z |
| Reconciliation | 15:00Z–15:06Z |
| Shadow package + FAST | 15:06:48Z–15:08:12Z at `fa4a9a47`: **15/15** (an earlier 15/15 seal at `3b3d1271`, 15:03:21Z, was superseded by an identity fix) |
| Independent reproduction | 15:08:30Z–15:08:52Z: byte-identical |
| **ZERO_TO_SOURCE_READY** | **1 h 0 min 9 s** (first FAST-passed seal: 55 min 18 s) |

- Peak memory: not measured.
- Paid provider cost: **$0**.
- Founder intervention during the run: **none**.

## Geography (Phases 2–4)

The corridor registry is a postal-code partition: 14 corridors, 36 admitted ZIPs. Kiawah Island and Seabrook Island share 29455 with Johns Island, so they are refused **by their own stated municipality** inside that ZIP.

| Class | Corridor | ZIPs |
|---|---|---|
| CORE | Historic District / Downtown | 29401, 29402, 29413, 29424, 29425 |
| CORE | Upper Peninsula / Meeting Street / Upper King | 29403, 29409 |
| CORE | West Ashley | 29407, 29414, 29416, 29417 |
| CORE | North Charleston / Rivers Ave / Hanahan | 29405, 29406, 29410, 29415, 29419, 29420, 29423 |
| CORE | CHS Airport / Convention Center / Coliseum / Tanger | 29418 |
| CORE | Mount Pleasant / Patriots Point | 29464, 29465, 29466 |
| CORE | Daniel Island / Cainhoy | 29492 |
| CORRIDOR | James Island | 29412, 29422 |
| CORRIDOR | Summerville | 29483, 29484, 29485, 29486 |
| CORRIDOR | Goose Creek | 29445 |
| CORRIDOR | Ladson / I-26 exit 203 | 29456 |
| FRINGE | Folly Beach | 29439 |
| FRINGE | Isle of Palms / Sullivan's Island | 29451, 29482 |
| FRINGE | Johns Island (Kiawah / Seabrook refused) | 29455, 29457 |

**Evaluated and OUTSIDE:**
- Moncks Corner, Awendaw / McClellanville, Ravenel / Hollywood, Wadmalaw, Huger
- Joint Base Charleston (military)
- Edisto, Walterboro, upper Dorchester County
- Beaufort, Hilton Head, Bluffton / Hardeeville, Georgetown / Pawleys, Myrtle Beach, Santee

**Hanahan** is admitted inside the North Charleston corridor.

### Beach and resort decisions (Phase 3)

| Place | Decision | Why |
|---|---|---|
| Isle of Palms | **B — FRINGE corridor** | Part of the metro via the Connector. Hotels are listed by the CVB, the hotel count is small and the rentals are refused. |
| Sullivan's Island | **B — FRINGE**, folded into isle-of-palms | Essentially no public hotels. |
| Folly Beach | **B — FRINGE corridor** | "Charleston's beach", 20 minutes from downtown, with a handful of hotels and inns. |
| Kiawah Island | **C — future `kiawah-seabrook-sc`**, OUTSIDE | A gated resort island: one resort hotel plus villa programmes, with its own search intent. |
| Seabrook Island | **C — with Kiawah**, OUTSIDE | A private club community; no public hotel identity. |

- 110 rows carry the future-market reason.
- Airport vs Convention/Tanger (29418) and Patriots Point vs Mount Pleasant (29464) cannot be split under a postal partition. They are reported as overlays in the accounting.

## Owned data (Phase 5)

- **OWNED IDENTITIES: 0.** No committed census or authority holds a 294xx identity.
- **OWNED ROUTES: 34.** These are CHS-coded Marriott routes from `dayton_oh_brand_directory_harvest_001`. Each was re-read on Marriott's own page.
- **OWNED VALID POLICY EVIDENCE: 0.**

## Accounting (Phases 16–17)

| Measure | Value |
|---|---|
| TOTAL DISCOVERED (identity-graph candidates) | **440** |
| PROPOSED CENSUS | **186** |
| VALID PET-FRIENDLY | **82** |
| VALID VERIFIED NO-PETS | **44** |
| RESOLVED / UNRESOLVED | **126 / 60** |

Every census identity has exactly one disposition, and every identity key is unique.

**The 60 unresolved identities by state:**

| State | Count |
|---|---|
| AWAITING_POLICY_OBSERVATION | 55 |
| AWAITING_OFFICIAL_URL | 3 |
| ACCESS_BLOCKED | 2 |

## Holds by class

| Class | Count | Contents |
|---|---|---|
| IDENTITY | 81 | 24 review, 55 name-only, 2 same-campus unproved (Hyatt House / The Lowline, 560 King St), plus the resort-component and unconfirmed-category rows |
| ROUTING | 3 | Country Victorian (Tripadvisor link only), Stay Express Inn, The Palmetto House Inn |
| ACCESS_BLOCKED | 2 | Starlight Motor Inn, The Cottages on Charleston Harbor (own-site 403) |
| EVIDENCE | 55 | 18 ADDRESS_NOT_ON_DOCUMENT (FAQ page with no street/ZIP); 15 POLICY_NOT_FOUND; 9 AMENITY_CHIP_ONLY (5 ESA, The Charleston Place, Seaside Inn, 360 King, Ansonborough); 8 QUOTE_NOT_OPERATIVE; 3 SERVICE_ANIMAL_ONLY (DoubleTree x3); 2 CO_LOCATION (HGI + Homewood Summerville, 406 Sigma Dr) |
| GEOGRAPHY | 0 | — |
| PAID | 0 | No census cohort needs a paid lane |
| FOUNDER | 3 | Hilton Grand Vacations / Hilton Club: Lodge Alley Inn, King 583, Liberty Place (timeshare rule) |
| CLOSED / RETIRED | 12 | Retired Wyndham routes |
| OUTSIDE | 123 | 110 are Kiawah / Seabrook future market |
| NON-HOTEL | 45 | 8 CVB vacation-rental companies; 32 map apartment / cottage / B&B-house units; 4 venue / booking / management / group sites; 1 private members' inn (Two Meeting Street, Kiawah Island Club) |

Two EVIDENCE sub-classes carry extra detail:
- **Held verbatim for QUOTE_NOT_OPERATIVE:** "While we love our furry friends, we do not accept pets" (20 South Battery), "As much as we love pets, we cannot accommodate them" (Fulton Lane), "We are unfortunately not a pet friendly hotel" (Planters Inn), "No, we do not allow pets on our property" (Shem Creek Inn), "…does allow dogs" (Charleston Harbor Resort), and Hotel Bennett's two-dog statement.
- **POLICY_NOT_FOUND** includes the Staybridge x3 and avid hotels rows whose IHG FAQ carries no pet answer.

**Resort identity (Phase 8).**
- Hyatt's single "Wild Dunes Resort – Sweetgrass Inn and Boardwalk Inn" listing names two hotels, and a second Residences listing resolves to the same page. It is held as RESORT_COMPONENT_IDENTITY. The resort FAQ refuses pets on a document that states no address.
- The Enclave at The Vendue and The Residences at Zero George are DUPLICATE_LISTING components of their hotels.

## Corridor coverage

A corridor page needs at least 5 pet-friendly hotels.

| Corridor | Class | Census | PF | NP | Unres | Page |
|---|---|---|---|---|---|---|
| historic-district | CORE | 40 | 9 | 5 | 26 | YES |
| upper-peninsula | CORE | 16 | 7 | 1 | 8 | YES |
| west-ashley | CORE | 14 | 8 | 6 | 0 | YES |
| north-charleston | CORE | 32 | 15 | 9 | 8 | YES |
| chs-airport-convention | CORE | 23 | 16 | 5 | 2 | YES |
| mount-pleasant | CORE | 33 | 18 | 8 | 7 | YES |
| daniel-island | CORE | 2 | 2 | 0 | 0 | NO |
| james-island | CORRIDOR | 0 | 0 | 0 | 0 | NO |
| summerville | CORRIDOR | 16 | 6 | 6 | 4 | YES |
| goose-creek | CORRIDOR | 3 | 0 | 2 | 1 | NO |
| ladson | CORRIDOR | 3 | 1 | 2 | 0 | NO |
| folly-beach | FRINGE | 2 | 0 | 0 | 2 | NO |
| isle-of-palms | FRINGE | 2 | 0 | 0 | 2 | NO |
| johns-island | FRINGE | 0 | 0 | 0 | 0 | NO |

7 of 14 corridor pages publish. The FAST cold build rendered exactly these 7.

## Census lanes and quality challenge (Phases 6, 9, 18)

**Lanes:**
- OSM: 393 elements.
- Owned Marriott harvest: 34 routes.
- Marriott SC sitemap page: 132 SC properties, 34 CHS leads.
- Hilton SC city pages and sub-pages: 47 SC cards.
- Brand sitemaps: Wyndham (25 routes, 13 read, 12 retired), Drury, WoodSpring. Plain-client 403s: IHG, Best Western, Red Roof, Hyatt, Radisson, Omni, Four Seasons.
- **Charleston Area CVB (charlestoncvb.com, Simpleview): 109 lodging listings, read by a plain client.** The JSON-LD carries no ZIP, so a market-local reader binds the independents' own-site lodging JSON-LD addresses.
- Visit Folly "Hotels & Inns": 8 names.
- Attended reads: IHG destination pages, Hyatt service, Choice city pages, Best Western hotel sitemap, Red Roof sitemap, ESA city page.
- Independents' own sites: 88.
- Competitor name leads: 24.

**Gap challenge:**
- 24 competitor names checked: 16 matched first-party identities and 8 are name-only.
- No true missing hotel was confirmed.
- Material gaps that remain, recorded rather than chased:
  - Folly Beach inns (Regatta Inn, Beachside Boutique Inn, Water's Edge Inn): their own sites gave no lodging address on this run.
  - Hotel Folly, Folliday Inn and Vera Hotel describe unit rentals.
  - InTown Suites x4, Motel 6 x2 (the brand refused the attended browser) and Hawthorn x2 (retired Wyndham routes) are map-only.
  - The Dunlin (Kiawah River, Johns Island) states no ZIP and is pinned in the Kiawah area.

## Shared-factory notes (recorded, not repaired)

1. **Hyatt route codes.** The shared `hotel_exclusions.co_located_distinct` does not read Hyatt route codes, so a Hyatt dual-brand building cannot be proved distinct. The sealed-package writer refused Hyatt House / The Lowline as SAME_PREMISES_UNPROVEN, and both are held market-locally.
2. **Reader gaps.** The shared first-party reader does not read the refusals and acceptances listed above; those rows are held verbatim.

A market-local census fix is included: a shared switchboard phone no longer merges two codes of one brand family. This kept Homewood Suites Summerville as its own identity.

## Shadow package (Phases 19–21)

| Item | Value |
|---|---|
| Package | `pkg-charleston-sc-b2987ee1c2bccb01` |
| Digest | `sha256:b2987ee1c2bccb01818e858f630b56f72fc1cde271fd9ca8e3dfce045788023f` |
| Receipt | `sha256:0abe82fc8aca6e508b7b36453d24003db4c1726f963b4b3a6d02525cb80e52ab` |
| Zone | SHADOW_UNTIL_REGISTERED |
| Source commit | `fa4a9a47` |
| Parent | Atlanta-live |
| Package path | `markets/staging/charleston-sc/shadow_packages/charleston-sc/` |
| Receipt path | `markets/staging/charleston-sc/shadow_receipts/charleston-sc/` |
| FAST | **15/15 PASS**, 0 unknown, 0 failed, determinism BYTE_IDENTICAL |
| First-party gate | 126/126 eligible |
| Declared routes | 90 |
| Reproduction | Clean worktree at `fa4a9a47` with a copied document store (not a junction). Zero content difference, apart from the CRLF checkout of the eol-unattributed discovery config. A separate-process seal gives the same digest. |

## Not done, by design

- No shared factory code changed.
- No registry, participation, closure, contract, global, identity-resolution or live-state edit.
- No broad regression.
- No final candidate.
- No founder authorization.
- No deploy.

## Next order — registration and reseal (when Charleston reaches the front of the lane)

1. Read CURRENT VERIFIED LIVE and merge that parent into this branch. The Atlanta binding of this shadow package then fails FAST rule N **by design**.
2. Copy the staged documents into their registered paths and repoint the helpers:
   - `markets/proposed/charleston-sc.json` → `markets/charleston-sc.json`
   - `identity_census_proposed/charleston-sc.json` → `identity_census/charleston-sc.json`
   - The staged `hotel_policy_facts_charleston-sc.json`, `charleston_sc_final_partition_007.json` and authority shard → their registered paths.
3. Record same-campus resolutions in `identity_resolutions.json`, then re-admit the held records:
   - 406 Sigma Drive: Hilton Garden Inn + Homewood Suites Summerville
   - 560 King Street: Hyatt House + The Lowline
4. Take the founder ruling on the three Hilton Grand Vacations / Hilton Club properties.
5. Run `market_registration_cli --write`, then `build_global_authority --write` and `--check`, then the release contract.
6. Run `registration_release_lane register` and `seal --work-order`. This produces a **new** package id. Then run FAST.
7. Run `regression_delta classify` (expect COMPOSITE_FRESH_MARKET_DATA_ONLY). Compose and reproduce the candidate and prepare the founder packet. Deploy only on founder authorization.
8. Before sealing, strengthen the evidence:
   - Re-probe the two 403 sites.
   - Read the Folly Beach inns and Country Inn Summerville on their own pages.
   - Find address-bearing policy documents for the FAQ-only independents: The Loutrel, The Pinch, The Nickel, The Spectator, Jasmine House, Elliott House, Andrew Pinckney, 86 Cannon, Market Pavilion, Francis Marion, Emeline, Tides.
