# PTF-RICHMOND-VA-PARALLEL-SOURCE-READY-001 — FINAL

Market `richmond-va` ("Richmond, Virginia"), branch `worker/ptf-richmond-va-market-001`. Built from zero on the
**Atlanta-live** release (`6825851b`, deploy `6aa7f125a91c73ba2363139e`, 23 markets / 1500 profiles / 1744 routes, read
mechanically from the live index by the seal).

**State: SOURCE READY — SHADOW_UNTIL_REGISTERED.** Richmond waits for its turn in the serialized release lane.

Machine-readable accounting: `atlas-dashboard/launch_packages/pettripfinder/markets/reports/richmond_va_source_ready_accounting_009.json`

## Timings (UTC, 2026-09-14)

| Phase | Observed |
|---|---|
| **RICHMOND_START_TIMESTAMP** | **15:53:55Z** |
| Precheck, template read, Virginia extract download | 15:53Z–16:02Z |
| Geography | 16:02:34Z |
| Census lanes | OSM 380.9 s (Virginia extract); brand inventory ~12 min detached; Visit Richmond VA listing service, one call |
| Routing | Wyndham property service 10.9 s; static lane 63.4 s; policy-page lane 22.6 s |
| Browser evidence | 16:12Z–16:40Z (IHG 22, Hyatt 6, Hilton 33, Marriott 40, Choice 57 [22 served, then a 403 wall], Best Western 20, Red Roof 9, ESA 7, Omni 1, InTown 2) |
| Identity / policy adjudication | 16:20Z–16:40Z |
| Reconciliation | 16:38Z–16:42Z |
| Shadow package + FAST | 16:47:39Z–16:49:19Z at `6f587cc6`: **15/15** (an earlier 15/15 seal at `e5f1ea44`, 16:45:02Z, was superseded by an identity fix) |
| Independent reproduction | 16:48:10Z–16:49:46Z: byte-identical |
| **ZERO_TO_SOURCE_READY** | **55 min 24 s** (first FAST-passed seal: 51 min 7 s) |

- Peak memory: not measured. Paid provider cost: **$0**. Founder intervention: **none**.

## Geography (Phases 2–3)

Postal-code partition: 12 corridors, 43 admitted ZIPs. Membership = the property's own postal code.

| Class | Corridor | ZIPs |
|---|---|---|
| CORE | Downtown / Shockoe / Riverfront / VCU Medical Center | 23219, 23218, 23223, 23298, 23241, 23261 |
| CORE | VCU Monroe Park / The Fan / Museum District | 23220, 23221, 23284 |
| CORE | West End / Willow Lawn / Glenside / Parham / Regency | 23226, 23229, 23230, 23294, 23238, 23288, 23173 |
| CORE | Short Pump / Gaskins | 23233 |
| CORE | Innsbrook / Glen Allen | 23060, 23058 |
| CORE | RIC Airport / Sandston / Henrico I-64 East | 23150, 23250, 23231, 23075 |
| CORE | I-95 North / Chamberlayne / Parham Rd / Virginia Center | 23222, 23227, 23228, 23059 |
| CORE | I-95 South / Jefferson Davis Hwy / Chippenham | 23224, 23225, 23234, 23237 |
| CORE | Midlothian / Bon Air / Chesterfield | 23112, 23113, 23114, 23235, 23236, 23832, 23120 |
| CORRIDOR | Mechanicsville | 23111, 23116 |
| CORRIDOR | Ashland | 23005 |
| CORRIDOR | Chester | 23831, 23836 |

**Adjudications:**
- **Petersburg / Colonial Heights / Hopewell / Prince George / Fort Gregg-Adams → OUTSIDE, preserved for a future `petersburg-tri-cities-va` market** (a materially separate I-95 / I-295 / US-460 cluster; 38 rows carry the future-market reason).
- Chester admitted as CORRIDOR (I-95 exit 61 / Route 10 serves the Richmond south side).
- Glen Allen split by ZIP: Innsbrook 23060 → innsbrook-glen-allen; Virginia Center 23059 → i-95-north.
- Hanover split: Mechanicsville and Ashland admitted; Hanover Courthouse and Doswell (Kings Dominion) OUTSIDE.
- Powhatan, Goochland, Rockville, New Kent OUTSIDE (no hotel core). Williamsburg, Fredericksburg, Charlottesville, Farmville, Tidewater, far I-95/I-85 refused by name.
- VCU Medical Center, Shockoe, Scott's Addition, Bon Air and Henrico I-64 East share ZIPs with another area; reported as overlays, never separate pages.

## Owned data (Phase 4)

- **OWNED IDENTITIES: 0.**
- **OWNED ROUTES: 40** RIC-coded Marriott routes (`dayton_oh_brand_directory_harvest_001`), each re-read on Marriott's own page (35 in market).
- **OWNED VALID POLICY EVIDENCE: 0.**

## Accounting (Phase 15)

| Measure | Value |
|---|---|
| TOTAL DISCOVERED | **294** |
| PROPOSED CENSUS | **196** |
| VALID PET-FRIENDLY | **89** |
| VALID VERIFIED NO-PETS | **45** |
| RESOLVED / UNRESOLVED | **134 / 62** |

Every census identity has exactly one disposition; every identity key is unique.

| Hold class | Count | Contents |
|---|---|---|
| IDENTITY | 21 | 16 review (brand-flag rows the brand's inventory does not list, Regency Inn same-name pair, 4 rows with no stated municipality, 2 lodging-category reviews, 2 name-only ties) + 5 name-only map rows |
| ROUTING | 26 | map-only / directory-only motels with no first-party route (Midlothian Tpke, Brook Rd, Jefferson Davis Hwy clusters), dead or third-party-only websites |
| ACCESS_BLOCKED | 7 | Motel 6 / Studio 6 ×4 (timeouts), Quality Inn Richmond Airport (Choice 403 wall), V.I.P. Inn (403), Inn at Patrick Henry's (DNS failure) |
| EVIDENCE | 29 | ESA ×6 AMENITY_CHIP_ONLY; SERVICE_ANIMAL_ONLY ×4 (DoubleTree Airport, DoubleTree Midlothian, Hilton Short Pump, HomeTowne Studios W Broad); co-location ×3 (Hampton + Home2 Chester at 12500 Chestnut Hill Rd; Residence Inn Downtown beside the Courtyard's refusal at 1320 E Cary St); directional collision ×1 (Quality Inn & Suites Ashland, 107 N. vs 107 South Carter Rd); POLICY_NOT_FOUND (Hyatt House Short Pump, avid Ashland, Colony House, Mankin Mansion, Virginia Cliffe Inn, Knights Inn Ashland); QUOTE_NOT_OPERATIVE (SpringHill Suites North/Glen Allen, Linden Row Inn, The Jefferson, Museum District B&B, Brentwood Inn Glen Allen); ADDRESS_NOT_ON_DOCUMENT (InTown Suites ×2); FEE_ONLY (WoodSpring Richmond West); chip (Express Airport Inn) |
| GEOGRAPHY | 0 | — |
| PAID | 0 | budget $0; no lane used or reserved |
| FOUNDER | 0 | — |
| CLOSED / RETIRED | 19 | Wyndham routes redirecting to brand search |
| OUTSIDE | 70 | 38 Petersburg / Tri-Cities future market |
| NON-HOTEL | 7 | Eileen RVA (apartment units), University Forest Apartments, Pinball Pete's BnB, two map cottages / guest houses, a chamber of commerce office, Richmond Raceway |

Held verbatim (never reworded): "This location does not accept pets. Service and emotional support animals are always welcome." (HomeTowne W Broad); "We do not accept animals, but there are boarding facilities and pet friendly hotels nearby" (Museum District B&B); "Pets Not Allowed / Daily cleaning fee of $5/ day in addition to the one time non-refundable pet fee" (SpringHill North); "Pet policies and fees apply; we recommend contacting the hotel in advance" (The Jefferson); "No pets allowed at InTown Suites Richmond VA – Chester / – Green Springs" (no postal code on the page).

## Corridor coverage (page threshold: 5 pet-friendly)

| Corridor | Class | Census | PF | NP | Unres | Page |
|---|---|---|---|---|---|---|
| downtown | CORE | 15 | 8 | 3 | 4 | YES |
| vcu-fan-museum-district | CORE | 7 | 2 | 2 | 3 | NO |
| west-end | CORE | 21 | 9 | 6 | 6 | YES |
| short-pump | CORE | 14 | 10 | 2 | 2 | YES |
| innsbrook-glen-allen | CORE | 16 | 9 | 2 | 5 | YES |
| ric-airport-sandston | CORE | 27 | 11 | 7 | 9 | YES |
| i-95-north | CORE | 19 | 9 | 4 | 6 | YES |
| i-95-south | CORE | 24 | 8 | 2 | 14 | YES |
| midlothian-chesterfield | CORE | 17 | 6 | 7 | 4 | YES |
| mechanicsville | CORRIDOR | 2 | 1 | 1 | 0 | NO |
| ashland | CORRIDOR | 15 | 7 | 2 | 6 | YES |
| chester | CORRIDOR | 19 | 9 | 7 | 3 | YES |

10 of 12 corridor pages publish; the FAST cold build rendered exactly these 10.

## Census lanes and quality challenge (Phases 5–7, 16)

- OSM (Virginia Geofabrik extract): 246 elements in the observation box.
- Brand inventory: owned Marriott 40; Marriott VA sitemap page (211 VA properties; no non-RIC Richmond-area property); Hilton VA city pages + sub-pages (33 in market); Wyndham sitemap (40 routes: 20 read, 19 retired); Drury and WoodSpring sitemaps. Plain-client 403: IHG, Best Western, Red Roof, Hyatt, Radisson, Omni, Four Seasons; timeouts: Choice, Motel 6.
- Attended reads: IHG destination pages (22 codes), Hyatt service (5 in market), Choice city pages (57 codes, 22 served), Best Western sitemap, Red Roof sitemap, ESA city page, Omni, InTown.
- Visit Richmond VA (Simpleview listing service): 200 lodging listings.
- Independents' own sites: 84 static targets, 38 policy-page sites.
- **Competitor gap: 13 leads, 12 matched first-party identities, 1 non-hotel (Pinball Pete's BnB). No true missing hotel.**
- Recorded gaps: Choice beyond the 403 wall; Motel 6 / Studio 6; the independent motel strips on Midlothian Turnpike, Brook Road and Jefferson Davis Highway (map-only, no route); The Massad House Hotel (map name only).

## Shared-factory notes (recorded, not repaired)

1. The shared reader treats "This location does not accept pets. Service …" as SERVICE_ANIMAL_ONLY and "We do not accept animals, but …" as self-contradicting; rows held verbatim.
2. The shared `address_key` drops directionals: 107 N. Carter Rd and 107 South Carter Rd (Ashland) collide; the pet-friendly record is held.
3. The sealed-package writer refuses a read from a host other than the census route (INVALID_ROUTE): Linden Row Inn's own FAQ acceptance cannot publish while the census binds it to its Best Western (WorldHotels) route.

Market-local fixes in this order: roster listings bound to a read brand code (Courtyard / Residence Inn Downtown, Hampton Inn Richmond-West); a Choice route refused by the brand is ACCESS_BLOCKED, not "unlisted"; third-party booking JSON-LD refused as identity; map rows folded beside a read within ten house numbers (ESA, WoodSpring).

## Shadow package (Phases 17–19)

| Item | Value |
|---|---|
| Package | `pkg-richmond-va-68a86efaa588c103` |
| Digest | `sha256:68a86efaa588c103449a70a4b606a4edbc4f3f0d362f0bf264f7e7ff504dfa98` |
| Receipt | `sha256:f7f04b2efe5935dec1f1defff34bd29c1ae554639b73faf7b7f4d394f214fc50` |
| Zone | SHADOW_UNTIL_REGISTERED |
| Source commit | `6f587cc6` |
| Parent | Atlanta-live |
| Package path | `markets/staging/richmond-va/shadow_packages/richmond-va/` |
| Receipt path | `markets/staging/richmond-va/shadow_receipts/richmond-va/` |
| FAST | **15/15 PASS**, 0 unknown, 0 failed, determinism BYTE_IDENTICAL |
| First-party gate | 134/134 eligible |
| Declared routes | 100 |
| Reproduction | Clean worktree at `6f587cc6` with a copied document store: zero content difference (only the eol-unattributed discovery config checks out CRLF); a separate-process seal gives the same digest. |

## Not done, by design

No shared factory code changed. No registry, participation, closure, contract, global, identity-resolution or live-state edit. No broad regression. No final candidate. No founder authorization. No deploy.

## Next order — registration and reseal (when Richmond reaches the front of the lane)

1. Read CURRENT VERIFIED LIVE and merge that parent into this branch. The Atlanta binding of this package then fails FAST rule N **by design**.
2. Copy the staged documents into their registered paths and repoint the helpers: `markets/proposed/richmond-va.json` → `markets/richmond-va.json`; `identity_census_proposed/richmond-va.json` → `identity_census/richmond-va.json`; the staged `hotel_policy_facts_richmond-va.json`, `richmond_va_final_partition_007.json` and authority shard → registered paths.
3. Record same-campus resolutions in `identity_resolutions.json` and re-admit held records: 12500 Chestnut Hill Rd (Hampton Inn Richmond Chester + Home2 Suites Richmond Chester); 1320 East Cary St (Courtyard + Residence Inn Richmond Downtown); the directional pair 107 N. / 107 South Carter Rd, Ashland.
4. `market_registration_cli --write`, `build_global_authority --write` then `--check`, the release contract.
5. `registration_release_lane register` and `seal --work-order` (a **new** package id), FAST.
6. `regression_delta classify` (expect COMPOSITE_FRESH_MARKET_DATA_ONLY); compose and reproduce the candidate; founder packet; deploy only on founder authorization.
7. Before sealing, strengthen evidence: re-probe Choice (va033 and remaining city pages), Motel 6 / Studio 6, vipmotorinn.com; find an address-bearing InTown document; resolve Linden Row's route conflict; read The Jefferson's policy page.
