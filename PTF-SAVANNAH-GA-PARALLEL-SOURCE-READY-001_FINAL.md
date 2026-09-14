# PTF-SAVANNAH-GA-PARALLEL-SOURCE-READY-001 — FINAL

Market `savannah-ga` ("Savannah, Georgia"), branch `worker/ptf-savannah-ga-market-001`, built from zero on the
Jacksonville-live parent `7b630cfa` (22 markets / 1256 profiles / 1483 routes, read mechanically from the live index).

**State: SOURCE READY — SHADOW_UNTIL_REGISTERED.** Savannah waits for its turn in the serialized release lane.

Machine-readable accounting: `atlas-dashboard/launch_packages/pettripfinder/markets/reports/savannah_ga_source_ready_accounting_009.json`

## Timings (UTC, 2026-09-14)

| Phase | Observed |
|---|---|
| Start | **05:12:13Z** |
| Precheck and template read | 05:12Z–05:19Z |
| Geography and corridor model | by 05:20:08Z |
| OSM lane | 387.8 s |
| Brand inventory | about 10 min, detached |
| Visit Savannah roster | 05:30Z–05:40Z (attended browser) |
| Visit Pooler roster | 06:02Z (plain client) |
| Browser evidence | 05:45Z–06:10Z: Marriott 42, Hilton 34, IHG 25, Hyatt 5, Choice 39, Best Western 10, Red Roof 5, ESA 2, Motel 6 / Studio 6 5 |
| Static evidence | Wyndham property service 10.5 s; static home pages 31 s; policy-page lane about 20 s |
| Policy adjudication and reconciliation | 06:10Z–06:31Z |
| Evidence-store incident and re-persist | 06:38Z–06:45Z (see below) |
| Shadow seal and FAST | 06:46:05Z–06:47:36Z at `c093cefd`: **15/15** |
| Independent reproduction | 06:47:54Z–06:48:12Z: byte-identical |
| **ZERO_TO_SOURCE_READY** | **1 h 35 min 23 s**. The first FAST-passed seal came at 1 h 21 min 51 s and was superseded. |

Peak working set: not measured on this run. Paid provider cost: **$0**. Founder intervention: **none**.

## Geography (Phase 2–3)

The corridor registry is a postal-code partition with 10 corridors and 15 admitted ZIPs.

| Class | Corridor | ZIPs |
|---|---|---|
| CORE | Historic District / Downtown / River Street | 31401, 31402, 31412 |
| CORE | Hutchinson Island | 31421 |
| CORE | Midtown / Chatham Parkway / Thunderbolt | 31404, 31405 |
| CORE | Southside | 31406 |
| CORE | SAV Airport / Garden City / West Savannah | 31408, 31415 |
| CORE | Pooler | 31322 |
| CORE | Gateway / I-95 exit 94 / Georgetown | 31419 |
| CORRIDOR | Port Wentworth / Crossroads | 31407 |
| FRINGE | Richmond Hill | 31324 |
| FRINGE | Wilmington / Whitemarsh / Skidaway Islands | 31410, 31411 |

**Tybee Island is OUTSIDE and preserved for a future `tybee-island-ga` market.** It is a separate beach-resort and vacation-rental market with its own search intent. Its 27 observed outside rows carry that reason (Tybee vacation-rental companies are refused as NON_HOTEL instead).

Also refused by name: Hilton Head, Bluffton, Beaufort, Hardeeville / Ridgeland, Rincon / Effingham, Bloomingdale, Hinesville / Midway, Pembroke, Statesboro, Brunswick / St. Simons, and Hunter Army Airfield (military, non-public).

River Street and the Eastern Wharf share 31401 with the Historic District, so they cannot be a separate corridor page. They are reported as a street-and-pin overlay: 20 census, 11 PF, 1 NP, 8 unresolved.

## Accounting

| Measure | Value |
|---|---|
| TOTAL DISCOVERED (identity-graph candidates) | **291** |
| QUALIFYING PROPOSED CENSUS | **187** |
| VALID PET-FRIENDLY | **96** |
| VALID VERIFIED NO-PETS | **40** |
| RESOLVED / UNRESOLVED | **136 / 51** |

Every census identity has exactly one disposition, and every identity key is unique.

**Partition of the 51 unresolved:**

| State | Count |
|---|---|
| AWAITING_POLICY_OBSERVATION | 39 |
| AWAITING_OFFICIAL_URL | 8 |
| ACCESS_BLOCKED | 4 |

## Holds by class

| Class | Count | Notes |
|---|---|---|
| IDENTITY | 27 | Non-admitted: 6 review, 17 name-only, 3 same-campus unproved, 1 rebrand |
| ROUTING | 8 | Presidents' Quarters (404), Recess (Instagram only), Sonesta Essentials (brand home page only), America's Best Value Inn (third-party site), Relax Inn, Sandman Motel, Savannah Inn, The Spanish Moss Inn |
| ACCESS_BLOCKED | 4 | Own-site 403: Catherine Ward House, Hamilton-Turner, The DeSoto, The Inn on West Liberty |
| EVIDENCE | 39 | Rejected reads by class: 5 service-animal-only, 6 policy-not-found, 1 first-party conflict, 1 non-operative, 3 co-location, 4 directional collisions. Also: independents' refusals the shared reader does not read (held verbatim), and ESA / Motel 6 amenity chips |
| GEOGRAPHY | 0 | — |
| PAID | 0 | No brand family refused the attended session |
| FOUNDER | 0 | — |
| CLOSED / RETIRED | 26 | Wyndham routes |
| OUTSIDE | 49 | 27 of them Tybee, future market |
| NON_HOTEL | 28 | 16 bureau vacation-rental / property-manager listings; 3 campground / RV / state park; 4 map apartment / cottage units; 3 STVR map rows; 2 venue / booking / management office |

## Corridor coverage

The last column shows whether the corridor page publishes, which needs at least 5 PF hotels.

| Corridor | Class | Census | PF | NP | Unres | Page |
|---|---|---|---|---|---|---|
| historic-district | CORE | 58 | 26 | 7 | 25 | yes |
| hutchinson-island | CORE | 1 | 1 | 0 | 0 | no |
| midtown | CORE | 19 | 10 | 4 | 5 | yes |
| southside | CORE | 9 | 5 | 3 | 1 | yes |
| sav-airport | CORE | 19 | 9 | 8 | 2 | yes |
| pooler | CORE | 21 | 10 | 6 | 5 | yes |
| gateway-i95 | CORE | 28 | 12 | 8 | 8 | yes |
| port-wentworth | CORRIDOR | 18 | 14 | 3 | 1 | yes |
| richmond-hill | FRINGE | 13 | 9 | 1 | 3 | yes |
| eastern-islands | FRINGE | 1 | 0 | 0 | 1 | no |

8 of 10 corridor pages publish.

## Owned evidence (Phase 4)

- **Identities: 0.** Wilmington's "The Savannah Inn" is a Carolina Beach hotel, so it is a name collision only.
- **Routes: 42.** These are SAV-coded Marriott routes from the committed national harvest, and each was re-read on Marriott's own page.
- **Valid policy evidence: 0.**

## Competitor gap (Phase 7, 16)

32 names were checked (BringFido, TripAdvisor / Expedia lists, Savannah.com, hotel-list aggregators). Only names were used; no competitor pet claims were read.

- 25 matched first-party identities.
- 7 are name-only and unresolved: Mansion on Forsyth Park (its domain does not resolve), McMillan Inn, Green Palm Inn, Zeigler House Inn, The Ballastone Inn (14 E Oglethorpe is now The Douglas), ESA Premier Suites Pooler (the name variant of the admitted ESA Pooler), and InTown Suites Garden City (its own page states no street).
- No true missing hotel was confirmed.

## Identity findings the order asked for

- **Street directionals.** The shared `address_key` drops E/W, so two different buildings collapse to one key:
  - 201 E Bay (Hampton Inn) and 201 W Bay (Hotel Indigo)
  - 11 Gateway Blvd E (Holiday Inn) and 11 W Gateway Blvd (TownePlace Suites South)

  The census merge refuses these joins market-locally, and the four PF records are held as ADDRESS_KEY_DIRECTIONAL_COLLISION. **This is a shared-factory blocker. It was recorded, not repaired.**
- **Dual-brand buildings held:**
  - 190 Pioneer Way: Courtyard and Residence Inn Richmond Hill
  - 100 Half Moon Way: TownePlace PF held beside Fairfield Pooler NP (caught by FAST rule J)
  - 6 Gateway Blvd E: Motel 6 and Studio 6
- **Rebrands and aliases:**
  - Atwell Suites and Hyatt Place Savannah Airport share one address and one phone, so they are held as a rebrand.
  - Visit Pooler's "Cottonwood Suites" is Wyndham's current Clarks Inn at 301B, folded as superseded.
  - OSM's "Best Western Plus 115 Oleary Rd" is Spark by Hilton, joined by an apostrophe-folded street key.
  - Bohemian Hotel is now Hotel Orielle.
  - The JW Marriott roster address (400) is superseded by Marriott's page (500).
  - The Cotton Sail's map row on River Street is folded into its Bay Street page.
- **Airport and Pooler naming.** Hotels marketed as "Savannah Airport" are placed by their own ZIP: Pooler 31322, Port Wentworth 31407, or SAV 31408.
- **Not admitted:** Signia by Hilton (not yet open), The Ann (Apartments by Marriott Bonvoy, category unconfirmed), and brand-flag map rows the brand's own inventory does not list (Econo Lodge South, Homewood Midtown, Wingate at 15 Sylvester C. Formey).

## Evidence-store incident (reported, recovered)

At 06:38Z I removed a reproduction worktree whose `data/` directory was a junction to this worktree's gitignored `data/`. `git worktree remove --force` followed the junction and deleted the persisted document store.

Recovery:
- The OSM extract was re-linked.
- The brand-inventory, static, policy-page, Wyndham and Visit Pooler lanes were re-run.
- Every quoted independent document was re-proved: the quote is verbatim, and the house number and ZIP appear on the same document. Three re-rendered pages (Foley House Inn, Hotel Bardo, Drury Plaza) now carry new sha256 values.
- The chain was rebuilt, resealed and reproduced. This time the reproduction used a **copy** of the store, not a junction.

Browser payloads were unaffected, because they are committed under `raw_captures/` with verified digests.

## Shadow package

| Item | Value |
|---|---|
| Package | `pkg-savannah-ga-b3497309a1a2729e` |
| Digest | `sha256:b3497309a1a2729e5efab35cb8b302b6830c010fd8adec042b1765bde00a4dcd` |
| Receipt | `sha256:b8e8c5a4ea743a98a7d36a887972221399e07835a8133d37a739637ec65f00a9` |
| Execution zone | SHADOW_UNTIL_REGISTERED |
| Source commit | `c093cefd` |
| Parent | the Jacksonville-live release |
| Package path | `markets/staging/savannah-ga/shadow_packages/savannah-ga/` |
| Receipt path | `markets/staging/savannah-ga/shadow_receipts/savannah-ga/` |
| FAST | 15/15 PASS, 0 unknown, 0 failed, determinism BYTE_IDENTICAL |
| First-party gate | 136/136 eligible |
| Declared routes | 105 |
| Reproduction | Clean worktree at `c093cefd`. The rebuilt chain has zero content difference, apart from the CRLF checkout of the eol-unattributed discovery config. A separate-process seal gives the same digest. |

## Not done, by design

- No factory or shared code changed.
- No registry, participation, closure, contract, global, identity-resolution or live-state edit.
- No broad regression.
- No final production candidate.
- No founder authorization.
- No deploy.

## Next order — registration and reseal (when Savannah reaches the front of the release lane)

1. Read CURRENT VERIFIED LIVE. Merge that parent into `worker/ptf-savannah-ga-market-001`; the stale Jacksonville binding is then invalid.
2. Copy the proposed documents into their registered paths and repoint the helpers' paths:
   - `markets/proposed/savannah-ga.json` → `markets/savannah-ga.json`
   - `identity_census_proposed/savannah-ga.json` → `identity_census/savannah-ga.json`
   - The staged `hotel_policy_facts_savannah-ga.json`, `savannah_ga_final_partition_007.json` and authority shard → their registered paths.
3. Add these resolutions to `identity_resolutions.json`, then re-admit the held PF records through the clean set:
   - Same-campus: 190 Pioneer Way (Courtyard / Residence Inn Richmond Hill)
   - Same-campus: 100 Half Moon Way (TownePlace / Fairfield Pooler)
   - Directional distinct-building: 201 E / 201 W Bay Street (Hampton Inn / Hotel Indigo)
   - Directional distinct-building: 11 E / 11 W Gateway Blvd (Holiday Inn / TownePlace South)

   If the shared layer cannot express a directional distinction, leave those four held and report it.
4. Run `market_registration_cli --write`, then `build_global_authority --write` and `--check`, then the release contract.
5. Run `registration_release_lane register` and `seal --work-order`. This produces a **new** package id: this shadow package fails FAST rule N by design once the parent moves.
6. Run `regression_delta classify` (expect COMPOSITE_FRESH_MARKET_DATA_ONLY). Then compose and reproduce the candidate and prepare the founder packet. Deploy only on founder authorization.
7. Before sealing:
   - Re-probe the 403 inns.
   - Find routes for the 8 routing holds.
   - Verify Mansion on Forsyth Park, McMillan Inn, Green Palm Inn and Zeigler House Inn on their own pages.
