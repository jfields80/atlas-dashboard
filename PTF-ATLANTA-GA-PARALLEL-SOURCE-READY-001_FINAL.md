# PTF-ATLANTA-GA-PARALLEL-SOURCE-READY-001 — FINAL

Market `atlanta-ga` ("Atlanta, Georgia"), branch `worker/ptf-atlanta-ga-market-001`, built from zero on the
Asheville-live parent `e312caa6` (18 markets / 1195 profiles / 1408 routes).

**State: SOURCE READY — SHADOW_UNTIL_REGISTERED.** Atlanta is fifth in the release queue:
Fayetteville (authorized, Netlify deploy blocked) → Jacksonville → Greenville → Atlanta. It does not jump the queue.

Machine-readable accounting: `atlas-dashboard/launch_packages/pettripfinder/markets/reports/atlanta_ga_source_ready_accounting_009.json`

## Timings (UTC, 2026-09-13)

| Phase | Observed |
|---|---|
| Start | 16:49:42Z |
| Geography and corridor model | 16:52Z–16:58:02Z (22 corridors: 9 CORE, 9 CORRIDOR, 4 FRINGE; 103 admitted ZIPs) |
| Census lanes | Georgia OSM extract, OSM lane 308.6 s; brand inventory 695.7 s (872 leads) |
| Attended first-party browser reads | 17:15Z–18:40Z: Marriott 155, Hilton 101, IHG 165, Choice 38, Hyatt 41, plus BW, Omni, Motel 6 and refusals |
| Static lanes | Wyndham property service 45.6 s (143 routes); static first-party 43.3 s (41 targets) |
| Adjudication and reconciliation | through 18:56Z; inputs commits `482e89f9` and `3f0bffee` |
| Shadow seal and FAST | First seal 18:46:46Z scored 13/15 (rule J caught 2 dual-brand buildings). Corrected seal ran 18:57:00Z–19:01:03Z and passed **15/15** |
| Independent reproduction | 19:01:23Z–19:02:14Z in a clean worktree: byte-identical |
| **ZERO_TO_SOURCE_READY** | **2 h 11 min 21 s** |

## Accounting

| Measure | Value |
|---|---|
| Total discovered (identity-graph candidates) | **814** |
| Qualifying proposed census | **468** |
| Valid pet-friendly | **240** |
| Valid verified-no-pets | **117** |
| Resolved / unresolved | **357 / 111** |
| Non-admitted | 346 total: OUTSIDE_MARKET 160, NAME_ONLY_UNRESOLVED 106, IDENTITY_REVIEW_REQUIRED 74 (includes 2 geography holds), NON_LODGING 5, REBRAND 1 |

Every census identity has exactly one disposition, and every identity key is unique.

**Partition of the 468:**

| State | Count |
|---|---|
| PUBLISHED_PET_FRIENDLY | 240 |
| VERIFIED_NO_PETS | 117 |
| AWAITING_OFFICIAL_URL | 50 |
| AWAITING_POLICY_OBSERVATION | 35 |
| ACCESS_BLOCKED | 26 |

**Pet-friendly by family:**

| Family | Count |
|---|---|
| Hilton | 91 |
| Marriott | 61 |
| Wyndham | 25 |
| IHG | 20 |
| Hyatt | 16 |
| Choice | 14 |
| Sonesta | 6 |
| Drury | 3 |
| Omni | 2 |
| Loews | 1 |
| Independent | 1 |

## Holds by class

| Class | Count | Notes |
|---|---|---|
| IDENTITY | 179 | 72 review + 106 name-only + 1 rebrand (non-admitted, never published) |
| ROUTING | 50 | AWAITING_OFFICIAL_URL |
| ACCESS_BLOCKED | 26 | 19 brand-family refusals (Choice after bot defence, ESA, Radisson, Red Roof, Four Seasons); 7 own sites |
| EVIDENCE | 35 | AWAITING_POLICY_OBSERVATION. Separately, the clean set's 29 rejected policy records sit in the unresolved states: 12 policy-not-found, 5 non-operative quotes, 5 service-animal-only, 4 co-location rulings, 2 first-party conflicts, 1 fee-only |
| GEOGRAPHY | 2 | Brand-stated municipality contradicts the postal code |
| PAID | 19 | Same rows as the ACCESS_BLOCKED brand-family cohort; $0 spent |
| FOUNDER | 0 | — |
| CLOSED / RETIRED routes | 67 | Wyndham redirects, plus Marriott atlbh 404 and Hilton atldhhx 404 |
| OUTSIDE | 160 | — |
| NON_HOTEL | 5 | — |

## Corridor coverage

The table lists census / pet-friendly / verified-no-pets / unresolved for each corridor. The last column shows whether the corridor page publishes, which needs at least 5 pet-friendly hotels.

| Corridor | Class | Census | PF | NP | Unres | Page |
|---|---|---|---|---|---|---|
| downtown | CORE | 35 | 19 | 8 | 8 | yes |
| midtown | CORE | 39 | 26 | 3 | 10 | yes |
| buckhead | CORE | 33 | 23 | 5 | 5 | yes |
| atl-airport | CORE | 55 | 34 | 14 | 7 | yes |
| perimeter | CORE | 27 | 17 | 7 | 3 | yes |
| cumberland-galleria | CORE | 26 | 17 | 6 | 3 | yes |
| smyrna | CORE | 9 | 4 | 3 | 2 | no |
| decatur-emory | CORE | 18 | 4 | 7 | 7 | no |
| southside-atlanta | CORE | 7 | 0 | 2 | 5 | no |
| airport-south | CORRIDOR | 14 | 2 | 8 | 4 | no |
| chamblee-doraville | CORRIDOR | 5 | 2 | 1 | 2 | no |
| marietta | CORRIDOR | 26 | 8 | 6 | 12 | yes |
| north-fulton | CORRIDOR | 41 | 24 | 6 | 11 | yes |
| norcross-peachtree-corners | CORRIDOR | 20 | 7 | 7 | 6 | yes |
| duluth-johns-creek | CORRIDOR | 24 | 14 | 5 | 5 | yes |
| tucker-stone-mountain | CORRIDOR | 20 | 11 | 4 | 5 | yes |
| kennesaw | CORRIDOR | 23 | 8 | 7 | 8 | yes |
| suwanee | CORRIDOR | 6 | 0 | 4 | 2 | no |
| morrow | FRINGE | 8 | 5 | 3 | 0 | yes |
| stockbridge | FRINGE | 14 | 7 | 6 | 1 | yes |
| lithonia-stonecrest | FRINGE | 6 | 3 | 2 | 1 | no |
| douglasville | FRINGE | 12 | 5 | 3 | 4 | yes |

15 of 22 corridor pages publish. The accounting report carries the requested-area overlay (Downtown, Midtown, Buckhead, ATL Airport, College Park, Hapeville, Sandy Springs, Perimeter, Galleria, Marietta, Alpharetta, Norcross, and others).

## Owned evidence reused

- **Identities: 0.**
- **Routes: 157.** These are Marriott Atlanta-area routes from the committed national harvest `dayton_oh_brand_directory_harvest_001`. All were also on Marriott's own Georgia page.
- **Policy evidence: 0.** Every policy record is a new first-party capture from this order.

Competitor audit (BringFido and guides, used as identity leads only):

- 24 names were checked; 19 matched first-party identities.
- **The Georgian Terrace Hotel** is the one credible true-missing hotel. Its own site returns 403, so it is held.

## Shadow package

| Item | Value |
|---|---|
| Package | `pkg-atlanta-ga-e7af2d4bfb43d96e` |
| Digest | `sha256:e7af2d4bfb43d96eb580c82e422a111f66374bfb6db1f9bdb5b99de8c8148a19` |
| Receipt | `sha256:0bc45a43346ac785ee0b68fb8a34bcf47f344ac96c51674a86d92b89bf756bdf` |
| Execution zone | SHADOW_UNTIL_REGISTERED |
| Source commit | `3f0bffee` |
| Package path | `markets/staging/atlanta-ga/shadow_packages/atlanta-ga/` |
| Receipt path | `markets/staging/atlanta-ga/shadow_receipts/atlanta-ga/` |
| FAST | 15/15 PASS, 0 unknown, 0 failed, determinism BYTE_IDENTICAL |
| Peak working set | 666 MB |
| Reproduction | Clean worktree at `3f0bffee`; separate-process seal gives the same digest; full chain rebuilt from committed captures with zero content difference (only the CRLF checkout of an eol-unattributed config file differs) |

## Not done, by design

- No factory or shared code changed.
- No registry, participation, closure, contract, global or live-state edit.
- No `identity_resolutions.json` edit.
- No broad regression.
- No final production candidate.
- No founder authorization.
- No deploy.
- Paid provider cost: $0.
- No founder intervention.

**Blocker recorded for the registration order (not repaired here):**
- Two dual-brand buildings need same-campus resolutions in the shared `identity_resolutions.json`:
  - 97 10th St NW: Hilton Garden Inn and Homewood Suites Atlanta Midtown.
  - 2975 Ring Road NW: Tru and Home2 Suites Atlanta NW Kennesaw.
- Their 4 pet-friendly records are held market-locally until then.

## Next order — registration and reseal (after Fayetteville, Jacksonville and Greenville are live)

1. Read the new live parent. Rebase `worker/ptf-atlanta-ga-market-001` onto it.
2. Copy the proposed documents into their registered paths:
   - `markets/proposed/atlanta-ga.json` → `markets/atlanta-ga.json`
   - `identity_census_proposed/atlanta-ga.json` → `identity_census/atlanta-ga.json`
   - The staged launch_package policy facts, partition and authority shard → their registered paths.
3. Add the two same-campus `co_located_distinct` resolutions to `identity_resolutions.json`, then re-admit the 4 held pet-friendly records through the clean set.
4. Run `market_registration_cli --write`, then `build_global_authority --write` and `--check`, then the release contract.
5. Run `registration_release_lane register` and `seal --work-order`. This produces a **new** package id: this shadow package fails FAST rule N by design once the parent moves.
6. Run `regression_delta classify` (expect COMPOSITE_FRESH_MARKET_DATA_ONLY). Then compose and reproduce the candidate and prepare the founder packet. Deploy only on founder authorization.
7. Before sealing, re-probe the refusing families: Choice, Extended Stay America, Radisson, Red Roof, Motel 6 and Four Seasons (refusals go stale), and The Georgian Terrace.
