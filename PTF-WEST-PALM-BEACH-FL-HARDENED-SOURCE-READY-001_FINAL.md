# PTF-WEST-PALM-BEACH-FL-HARDENED-SOURCE-READY-001 — FINAL

Market `west-palm-beach-fl` — **West Palm Beach / The Palm Beaches, Florida**.
Branch `worker/ptf-west-palm-beach-fl-market-001`, worktree `C:\Atlas-West-Palm-Beach-FL-Hardened-V1`.
Base: the CURRENT repaired lineage — participation-guard repair (`09851d50`), supersessions-lineage repair
(`9075596f`) and deployment work_order semantics (`efd22bc7`) on top of the live Fort Lauderdale release
(`e82120cc`). **Not** origin/main, which the resolver reported stale.

Built from zero: no prior West Palm Beach market, census row, policy fact or evidence row existed. Miami's and
Fort Lauderdale's builds were read for **discovery intelligence only** (§3); no policy row was imported from
either.

Status: **SHADOW_UNTIL_REGISTERED**. Nothing registered, participated, authorized, pinned or deployed.

---

## 1. Headline

| Metric | Value |
|---|---|
| Raw observations (9 lanes) | 2,895 |
| Florida DBPR licensed-lodging leads | 1,588 (200 in admitted ZIPs, 1,388 in named refused ZIPs) |
| OSM lodging elements in the observation box | 239 |
| Brand-inventory routes · CVB named leads · BringFido normalized | 177 · 199 · 747 |
| Graph nodes after hard-key identity merge | 2,455 (**0 merge conflicts**) |
| Proposed census (TRUE_HOTEL_IDENTITY) | **190** |
| Valid pet-friendly (CLEAN_PET_FRIENDLY) | **49** |
| Valid verified-no-pets (CLEAN_VERIFIED_NO_PETS) | **25** |
| Resolved / unresolved | **74 / 116** |
| Resolution rate | **38.95 %** |
| **ACTIONABLE unresolved** | **0** |
| Package | `pkg-west-palm-beach-fl-eb802c414bf12396`, FAST **15/15 PASS**, reproduced byte-identically |

For scale: Fort Lauderdale's comparable source-ready state was 30.00 %, Miami's 13.30 %, Tampa V2's 23.64 %.
The margin here is §7 — Hilton and Hyatt closed to **zero unresolved rows**.

## 2. Phase 1 — lineage and CURRENT VERIFIED LIVE

Live was resolved **mechanically** (`release_index live-source --fetch --verify-host`, 3.567 s), never assumed:

| | |
|---|---|
| CURRENT LIVE SOURCE COMMIT | `e82120cce7e48c62d3c1057a6c82785bed920485` (built_from `0cc2817b`) |
| CURRENT LIVE DEPLOYMENT | `6ab1a035c7ef3b14a23a4ec6` (fort-lauderdale-fl) |
| CURRENT LIVE BUNDLE SHA | `0ec5c6557d79eaf77a4065b6700c0a5807e9bfe282408dd4779804b33af3a40f` |
| CURRENT LIVE SITEMAP SHA | `e81961ae76454ce608fcb39624d5147c8779f52b269faab9449138397cb8fa3d` |
| CURRENT LIVE MARKETS / PROFILES | **32 / 2,375** |
| CURRENT LIVE RELEASE-INDEX / SERVED ROUTES | **2,646 / 2,711** |
| head_contains_live · origin_main_stale · **HOST VERIFIED** | true · true (never used) · **true** |

Every figure matches the order's expectation exactly. Live was read for context only; nothing in production was
touched (§13).

## 3. Phase 2 — the South Florida discovery intelligence, reused as intelligence

TWO live markets looked into Palm Beach County deliberately and refused every row. `west_palm_beach_fl_south_florida_reuse_001`
reads both committed graphs and hands this market a prior-discovery index:

| | |
|---|---|
| MIAMI-DISCOVERED PALM BEACH IDENTITIES | 85 of Miami's 2,332 graph nodes |
| FORT-LAUDERDALE PALM BEACH IDENTITIES | 191 of its 2,558 graph nodes |
| **DEDUPED SOUTH-FLORIDA IDENTITIES REUSED** | **202** (73 seen by both markets) |
| **POLICY EVIDENCE IMPORTED** | **0** — every Palm Beach row in both graphs is `POLICY_NOT_VERIFIED`, which the helper ASSERTS row by row and aborts on |
| NEW IDENTITIES DISCOVERED | 2,253 of the 2,455 graph nodes were not in either prior cohort |

Membership was re-decided here for every row by this market's own corridor registry. A prior `OUTSIDE_MARKET`
ruling is provenance, never an admission.

## 4. Phases 3–4 — the Palm Beaches geography

`west_palm_beach_fl_geography_001` → **15 corridors over 60 admitted postal codes**, a strict postal-code
partition (11 CORE / 2 CORRIDOR / 2 FRINGE), 17 observation cells (15 admitting, 2 observation-only reaching
Deerfield Beach and Hobe Sound). The registry collides with **none** of the 33 registered markets' postal codes.

**The market's defining identity trap is that SEVEN Palm Beach County municipalities carry "Palm" in the
name** — West Palm Beach, the Town of Palm Beach, Palm Beach Gardens, North Palm Beach, Royal Palm Beach, Palm
Beach Shores and Palm Springs. The mainland City of West Palm Beach (33401, Clematis Street, Rosemary Square,
the Convention Center, Brightline) and the island Town of Palm Beach (33480, Worth Avenue, The Breakers, the
Four Seasons, the Colony) are separate municipalities on separate postal codes with separate travel products.
A hotel's own postal code decides which it is in; its name decides nothing.

The county-coherence test is recorded in full in the report: one county, one commercial airport (PBI), one CVB
(Discover The Palm Beaches markets all 39 municipalities together), one Brightline spine. The order's
instruction was followed literally — the county-wide market was tested for coherence FIRST, and Boca Raton,
Delray Beach and the Town of Palm Beach are corridors inside it rather than separate markets, however large.

## 5. Phase 5 — the cruise test, and why this port gets NO corridor

**The opposite of the Port Everglades finding, and for a mechanical reason.** Port Everglades earned a corridor
in Broward because it sits inside 33316, a postal code full of hotels claimed by nothing else. **The Port of
Palm Beach sits in Riviera Beach 33404, already claimed in full by `riviera-beach-singer-island`.** A cruise
corridor here could only be built by SPLITTING that code — a per-property judgement the registry forbids — or by
duplicating it, which a partition forbids outright. 33404's 13 hotel-rank licences are Singer Island's
oceanfront, Palm Beach Shores at the inlet and Riviera Beach's Broadway blocks: the corridor's own inventory,
not a separate port district. This is the **PortMiami** finding. The port is a street-and-pin overlay.

**PBI Airport gets no corridor either, for the same reason FLL got none: it owns no postal code.** Its hotel
district spreads over Belvedere Road (33406), Palm Beach Lakes / Village Boulevard (33409) and 33415, which form
one inland corridor with 33405 and 33417. "PBI" is an overlay inside it.

## 6. Phase 5 — resort, condo and country-club safety

Palm Beach County carries **856 DBPR condominium (CNDO)** and **1,849 vacation-dwelling (DWEL)** licences and
**1,113 non-transient apartments** against just **197 hotel/motel/B&B** licences in admitted codes. None enters
the graph. A further **381** transient-apartment licences whose own name reads as an apartment community, RV
park, unit, stable or investment entity were refused by name. The county's particular exposures — PGA National's
villa programme (33418 carries 315 lodging licences and 2 hotel-rank), Wellington's equestrian-season rentals
(33414: 230 and 2), the Singer Island and Highland Beach towers — are counted and never admitted.

**TIMESHARE, proved first-party.** Marriott's Oceana Palms (MARSHA `pbisn`, 3200 North Ocean Drive, Riviera
Beach 33404) was in the census until the attended browser read the brand's own page, which carries the heading
"MARRIOTT'S OCEANA PALMS, A MARRIOTT VACATION CLUB® RESORT" and an Ownership section in both its navigation and
its footer. It is excluded as TIMESHARE **before any policy applies** — and its page's "Pets Not Allowed" line
is recorded as history and published nowhere, because an excluded row publishes nothing, not even a refusal.
Its neighbour at 3800 North Ocean Drive (`pbisg`, Palm Beach Marriott Singer Island) is a distinct hotel
premises and was read separately. Three timeshare rows were excluded in total.

## 7. Phases 13–14 — the attended-browser lane

The committed route table sends MARRIOTT and HILTON to a paid browser provider and excludes HYATT and
BEST_WESTERN from its paid lanes on cost. This order has no authorization for new paid spend, so the lane it
exercised is the **supported attended browser**.

| | |
|---|---|
| ATTEMPTS | **61** (Marriott 28, Hilton 28, Hyatt 3, Best Western 2) |
| PUBLICATION-GRADE READS | **49** (Marriott 17, Hilton 28, Hyatt 3, Best Western 2) |
| TIMESHARE EXCLUSION (read, published nowhere) | 1 |
| CHALLENGE DENIED (terminal) | **10**, all Marriott |
| UNBOUND READS | **1** — The Ben, correctly unbound because its census row is HELD (§9) |
| PAID PROVIDER CALLS · Bright Data | **0** · not used |
| AKAMAI BYPASSED · BROWSER-JS EXFILTRATION · LOCAL RELAY | **false · false · false** |

**Hilton and Hyatt closed completely: 28 of 28 and 3 of 3 routed properties read first-party, zero unresolved
rows in either family.** That is this market's margin.

**Marriott is the binding constraint, and it was measured rather than assumed.** 13 paced windows: window 1
allowed 12 reads, window 6 allowed 1, window 12 allowed 1, and the rest allowed none. The ceiling TIGHTENED
across the run instead of recovering. The lane never retried inside a window and never bypassed a challenge.
Firecrawl was then probed as an independent lane on a denied Marriott property and answered
`SCRAPE_ALL_ENGINES_FAILED` **at zero credits** — a capability statement, not a transient error. Every one of
the 28 routed Marriott properties was ATTEMPTED; the 10 that stayed denied have no authorized lane left.

### Hilton serves TWO templates, and their labels differ

Binding one vocabulary to both would have put words in the brand's mouth for half the market, so **both were
witnessed on this market's own properties rather than inherited from Fort Lauderdale**:

* `HOTEL_INFO_LIST` on `/hotel-info/` — witness `pbicppy` (Canopy West Palm Beach Downtown, whose `/amenities/`
  404s): "Pets allowed: / Yes", "Non-refundable fee: / $75.00", "Max weight: / 75 lbs", "Max size: / large",
  "Pet policy: / Pet fee of $75 is per pet. Cats are not permitted on-site".
* `POLICIES_ACCORDION` on `/amenities/` — witness `pbiwphh` (Hilton West Palm Beach, whose `/hotel-info/`
  REDIRECTS there): "Pets Allowed / Yes", "Pet Policy", "Max Size / Medium", "Max Weight / 75 lbs",
  "Pet Fee / $125.00 Non-refundable". Its content is **absent from the accessibility tree until the accordion is
  expanded**, so the lane clicks "Pets" and then reads the page's own text.

Marriott's vocabulary is unchanged from the Fort Lauderdale build, but its accessibility tree **truncates some
fee values to "…"**; those were read from the rendered page rather than inferred (Aloft Delray Beach's
"Non-Refundable Pet Fee Per Night: $25.00" — a PER NIGHT fee, not per stay).

## 8. Phases 11–12 — the rest of the router

| Lane | Result |
|---|---|
| Owned (rung 0) | 34 Marriott routes from the committed national harvest, 0 new requests |
| Brand inventories (rung 2) | Marriott's Florida sitemap and Hilton's own Florida city pages answered; Wyndham / Sonesta / WoodSpring / ESA / Drury / Loews / InTown / Mandarin sitemaps answered; **IHG, Best Western, Hyatt, Red Roof, Omni, Four Seasons, Radisson, Kimpton and Stayable answered 403**; Choice and Motel 6 timed out; Accor 404. 316 free requests, 177 routes |
| **Discover The Palm Beaches (the county CVB)** | **NAME-ONLY — see below** |
| Free static capture | 102 targets: 2 VALID, 87 ACCESS_DENIED, 8 identity mismatch, 4 unexpected page |
| Wyndham property service | 12 routes selected, 9 read, 3 retired |
| Extended Stay America | 3 routes, 3 served, 3 FAQ pet answers |
| Independents' own policy / FAQ pages | 46 targets, 34 bound on their own address or phone, 13 with pet sentences |
| **Google Places route discovery (existing key)** | **126 requests**: 110 of 116 unrouted rows bound on **street number + ZIP**, **81 with a website**; plus 10 gap verifications |
| Places-discovered sites | 46 read, 34 bound, 70 free requests |
| **Firecrawl** | **discovery 8 + brand pages 3 + policy pass 19 + 1 Marriott capability probe.** 4 publication-grade IHG reads, 15 new Choice routes, 3 brand pages with their own address. **Credits 1,235 → 1,199 (36), USD 0.00, no new plan, no new credits** |
| Bright Data / any other paid provider | **0** |

### The CVB is a NAME-ONLY lane, and the difference from Fort Lauderdale was MEASURED

Visit Lauderdale (a Simpleview CMS with a public listings REST service) handed that build **376 listings with
360 websites** — its single biggest routing win. This bureau is not that, and the gap was measured rather than
assumed:

* robots.txt ALLOWS every agent except `/*?`; this lane reads only sitemap-published path URLs and never
  constructs a query string.
* A plain client is refused **HTTP 403 on every path**, including `/sitemap_index.xml` which robots.txt allows.
* WordPress with the REST API **disabled** (`rest_no_route`); no listings service exists to call.
* Through Firecrawl the three sitemaps read cleanly (3 credits): 3,125 listing URLs, 624 of them English.
* **The listing pages carry NO street, NO postal code, NO telephone and NO outbound website** in any document
  this lane can read. Three profiles were tried: the routed `rawHtml` profile and a no-wait `rawHtml` profile
  both returned `SCRAPE_TIMEOUT`; the `markdown` profile returned HTTP 200 in ~6 s and contained none of those
  four fields. The bureau renders all four client-side from a Simpleview CRM this order cannot call.

Reading all 624 listings would have cost **624 credits for zero premises data**, so it was not done. The lane
contributes 199 lodging-named tier-3 leads, at a total cost of **5 credits**. The routing gap it left was
covered by Google Places instead.

## 9. Phases 9–10 — four defects the safety rules caught, each measured not inherited

**1. The same-name collision test was a CROSS-MARKET test.** This market's observation set deliberately carries
every Broward and Miami-Dade licence in a named OUTSIDE postal code so the Phase 22 boundary audit can count
them. Counted in the collision test, a generic chain flag in somebody else's market silently HELD a real hotel
in this one — the standing rule stated the other way round. Measured on the first pass: **Budget Inn** (828 S
Dixie Hwy, Lake Worth Beach 33460) held by Budget Inns in Pompano Beach 33069 and Miami 33147; **Relax Inn**
(7448 Lake Worth Rd 33467) by a Relax Inn in Fort Lauderdale 33316; **Super 8 Motel** (757 N US-1, Juno Beach
33408) by Super 8s in Dania Beach and Homestead; **Hilton West Palm Beach** (600 Okeechobee Blvd) by an
OSM-only pin spelling the same name at 6000 Okeechobee. Restricted to admitted-postal nodes the brand's own
inventory lists. **Recovered 5 hotels (191 → 196), and the genuine in-market pair stayed held.**

**2. US-1 — this county's lodging spine — was splitting into two merge keys.** `_merge_spelling` strips
punctuation before the general spelling table runs, so "U.S. Highway 1" became "U S  Highway 1", the `us`
alternative stopped matching, and the directional strip then ate the bare "S" — leaving the merge key
`U hwy 1` against the licence's `hwy 1`. Two keys, one street, on the road that carries Jupiter, Juno Beach,
North Palm Beach, Lake Park, Riviera Beach, Lantana, Delray Beach and Boca Raton lodging. It is the same class
of defect as Fort Lauderdale's "SR 84" / "State Road 84" split. `fold_us_highway` was added and audited over all
**1,772** streets in the market: **24 changed, every one a genuine US-1/US-27 variant**, with no corruption of
"Plus", "Columbus" or "Federal Highway" — and **six duplicate premises pairs unified**.

**3. Three one-premises-two-rows duplicates, each proved first-party and HELD, never silently repaired.**
A street is never rewritten by a lane; each hold names the exact resolution a registration order should make.

| Premises | The two rows | What the first-party read proved |
|---|---|---|
| Narcissus Avenue, West Palm Beach 33401 | "Ben West Palm" (251, DBPR licence HOT6014077) · "The Ben, Autograph Collection" (215, national harvest + OSM + competitor, MARSHA `pbiak`) | The brand's OWN page for `pbiak` states **251** N Narcissus Avenue — agreeing with the licence. **Both held**: publishing a hotel at a house number its own operator contradicts would send a guest to the wrong door |
| 1800 Centrepark Drive East, WPB 33401 | "Courtyard by Marriott West Palm Beach Airport" ('1800 Centre Dr. E.') · "Courtyard West Palm Beach Airport" (`pbicy`) | The brand's own page states **Centrepark**; the stale row is held and the coded row publishes |
| 2000 NW Executive Center Circle, Boca Raton 33431 | "Sonesta Select Boca Raton" · "Sonesta Select Boca Raton Town Center" | Both routes resolve to ONE property slug on the brand's own host; the abbreviated licence row is held and the Town Center row — which after the street merge carries both the operator's own name and its complete street — publishes |

**4. `BROWSER_CAPTURE_NEEDED` inherited Fort Lauderdale's extension-refusal text.** That build recorded
read-permission refusals on hilton.com, hyatt.com and bestwestern.com; **this session had none — it read 28
Hilton, 3 Hyatt and 2 Best Western properties first-party.** Carrying the text forward parked a Best Western row
as awaiting a browser that had already answered for its brand, which is exactly the Phase 11 rule 7 mislabel.
The blockers were restated from this run's own measurements, leaving Marriott as the one genuinely walled
family. **BROWSER_CAPTURE_NEEDED = 0.** The Best Western row's real problem is that the brand publishes no
property page for it: its own property-code route redirects to a hotel-search page and the brand's own Boca
Raton results do not list it. That same search page produced a **route repair** — the census carried a Best
Western row at 810 US-1 33477 with no route at all, and the brand named it Best Western Intracoastal Inn
(code 10267), whose own page gave both premises and policy.

## 10. Phases 16–17 — policy safety

No acceptance was inferred from an amenity chip, a fee, a weight or a count; no refusal from silence. Hyatt's
"Pet Friendly" chip and Embassy Suites Palm Beach Gardens' "Pet Friendly Hotel" page TITLE were both read past
to the property's own operative block. Service-animal clauses were never read as acceptance ("No pets
allowed-service animals only" is the refusal; the clause is not). Best Western Palm Beach Lakes' **refundable**
$100 damage deposit is recorded separately from its $25/day rate — a deposit is never reported as a pet fee.
Policy sentences truncated on the brand's own page ("Dog and .", "(NO CATS ALL", "Required Refundable Se",
"Comp") are quoted exactly as the page states them and never completed.

**One negation / shared-reader conflict was caught and held**: Casa Grandview Bed & Breakfast, where this order
read CLEAN_VERIFIED_NO_PETS and the shared `first_party_binding` reader classified the same quote
SERVICE_ANIMAL_ONLY. Disagreement between two readers over one quote is an EVIDENCE_HOLD, never a coin flip.

## 11. Phases 17–18 — one disposition per row (116 unresolved)

| Class | Rows | Exact root cause |
|---|---:|---|
| ROUTING | 58 | no first-party route: no brand, bureau or map website, no Places result at the row's own street number + ZIP, or only a brand/OTA host another lane owns |
| SOURCE_SILENT | 26 | the property's own page or site served, bound to the identity, and stated no operative pet policy |
| ACCESS_BLOCKED | 24 | every free/authorized lane attempted was refused (static plain client, Firecrawl where eligible, and for 10 Marriott rows the attended browser across 13 paced windows) |
| IDENTITY | 4 | two census rows share one premises (§9) |
| EVIDENCE | 4 | shared-reader disagreement, or fee/weight/count with no acceptance sentence |
| **BROWSER_CAPTURE** | **0** | every browser-required row is read or terminally classified |
| NEGATION / POLICY_NOT_FOUND / MIXED_RESORT / CONDO_HOTEL / PAID / GEOGRAPHY / FOUNDER / OTHER | 0 | — |

Partition states: PUBLISHED_PET_FRIENDLY 49, VERIFIED_NO_PETS 25, AWAITING_OFFICIAL_URL 58,
AWAITING_POLICY_OBSERVATION 30, ACCESS_BLOCKED 24, AWAITING_ROUTING_REPLACEMENT 4.
The partition contract reported **0 issues**; `uncorridored_rows` = 0.

**Exclusions**: vacation rental 80 · timeshare 3 · resort residence 0 · non-hotel 142 · closed 0 · outside
market 1,429 · duplicate listing 0 · same-campus-distinct 0. Graph residue: name-only unresolved 531,
identity-review 80. Never admitted at all: 855 CNDO, 1,849 DWEL, 1,113 NAPT, 381 apartment-named TAPT.
No row was classified CLOSED — DBPR extracts carry only active licences and no read stated a closure.

## 12. Phase 19 — actionability

| Class | Total | Actionable now | Router exhausted | New provider | New spend | Founder |
|---|---:|---:|---:|---:|---:|---:|
| ROUTING_HOLD | 58 | **0** | 58 | 0 | 0 | 0 |
| SOURCE_SILENT | 26 | **0** | 26 | 0 | 0 | 0 |
| ACCESS_BLOCKED | 24 | **0** | 24 | 0 | 0 | 0 |
| IDENTITY_MISMATCH_HOLD | 4 | **0** | 0 | 0 | 0 | 4 |
| EVIDENCE_HOLD | 4 | **0** | 0 | 0 | 0 | 4 |
| **TOTAL** | **116** | **0** | 108 | 0 | 0 | 8 |

**ACTIONABLE UNRESOLVED REMAINING = 0.** MATERIAL COVERAGE RISK = none.

## 13. Phase 20 — brand by brand

| Family | Census | PF | NP | Unres. | Firecrawl att./ok | Browser att./read/denied | Blocked |
|---|---:|---:|---:|---:|---|---|---:|
| MARRIOTT | 28 | 9 | 6 | 13 | 1 / 0 | **28 / 17 / 10** | 10 |
| HILTON | 27 | 24 | 3 | **0** | 1 / 0 | **28 / 28 / 0** | 0 |
| INDEPENDENT | 86 | 4 | 2 | 80 | 3 / 0 | 0 | 10 |
| WYNDHAM | 8 | 0 | 6 | 2 | 2 / 0 | 0 | 1 |
| IHG | 7 | 1 | 3 | 3 | **4 / 4** | 0 | 0 |
| CHOICE | 6 | 1 | 3 | 2 | 0 / 0 | 0 | 0 |
| LUXURY_INDEPENDENT | 8 | 2 | 1 | 5 | 1 / 0 | 0 | 0 |
| RESORT_INDEPENDENT | 5 | 2 | 0 | 3 | 0 / 0 | 0 | 0 |
| BEST_WESTERN | 4 | 1 | 1 | 2 | 0 / 0 | **2 / 2 / 0** | 1 |
| HYATT | 3 | 3 | 0 | **0** | 0 / 0 | **3 / 3 / 0** | 0 |
| EXTENDED_STAY_AMERICA | 3 | 2 | 0 | 1 | 0 / 0 | 0 | 1 |
| MOTEL6 / STUDIO6 | 2 | 0 | 0 | 2 | 0 / 0 | 0 | 0 |
| SONESTA / RED_ROOF / FOUR_SEASONS | 1 / 1 / 1 | 0 | 0 | all | 0 / 0 | 0 | 1 |

## 14. Phase 21 — corridor coverage (15 corridors, 60 ZIPs; **5 publish**)

| Corridor | Class | Census | PF | NP | Unres. | Rate | Page |
|---|---|---:|---:|---:|---:|---:|---|
| downtown-west-palm-beach | CORE | 18 | 7 | 2 | 9 | 50.0 % | **yes** |
| palm-beach-worth-avenue | CORE | 11 | 0 | 2 | 9 | 18.2 % | no |
| northwood-metrocentre | CORE | 12 | 2 | 2 | 8 | 33.3 % | no |
| riviera-beach-singer-island | CORE | 12 | 1 | 2 | 9 | 25.0 % | no |
| palm-beach-gardens | CORE | 10 | 5 | 1 | 4 | 60.0 % | **yes** |
| jupiter-tequesta | CORE | 12 | 1 | 3 | 8 | 33.3 % | no |
| palm-beach-international-airport | CORE | 18 | 7 | 2 | 9 | 50.0 % | **yes** |
| lake-worth-beach | CORE | 25 | 2 | 1 | 22 | 12.0 % | no |
| delray-beach | CORE | 15 | 7 | 0 | 8 | 46.7 % | **yes** |
| boca-raton | CORE | 25 | 8 | 4 | 13 | 48.0 % | **yes** |
| boynton-beach | CORE | 10 | 3 | 1 | 6 | 40.0 % | no |
| lantana-manalapan-hypoluxo | CORRIDOR | 7 | 1 | 3 | 3 | 57.1 % | no |
| north-palm-beach-juno-beach | CORRIDOR | 4 | 1 | 1 | 2 | 50.0 % | no |
| western-communities | FRINGE | 7 | 4 | 1 | 2 | 71.4 % | no |
| the-glades | FRINGE | 4 | 0 | 0 | 4 | 0.0 % | no |

A page publishes only where the existing threshold (5 verified pet-friendly hotels) is met mechanically. No thin
page was created, and none was created for a cruise, airport or equestrian keyword. **Lake Worth Beach is the
market's honest weak point**: 25 census rows — the largest corridor, and the densest motel row in the county —
resolved at 12.0 %, because its inventory is independent motor courts with no first-party site.

## 15. Phase 22 — the county boundary audit

Counted by each licence's OWN county; admission is by the corridor registry over the property's own postal code
and by nothing else.

| County | Hotel-rank licences | **Admitted here** | Owner |
|---|---:|---:|---|
| **Palm Beach (home)** | 197 in admitted codes | — | this market |
| Broward | 609 | **0** | **LIVE** `fort-lauderdale-fl` |
| Miami-Dade | 737 | **0** | **LIVE** `miami-fl` |
| Martin | 29 | **3** | future `treasure-coast-fl` |
| Monroe (the Keys) | 319 | **0** | future `florida-keys-fl` |
| St. Lucie | 58 | **0** | future `treasure-coast-fl` |

`live_market_inventory_admitted = 0`, and that is the invariant that matters: both southern neighbours are LIVE
markets that already publish that inventory, so a non-zero count there would be a **double publication**, not a
judgement call. Deerfield Beach 33441 / 33442 adjoins Boca Raton directly and belongs to fort-lauderdale-fl's
own `deerfield-beach` corridor; it is refused by the line, not by distance. `no_south_florida_sprawl` = true.
Graph nodes refused by place: Miami-Dade 611, Florida Keys 221, Boca-area strays 24, West Palm strays 28.

**The Martin County border case, which the order's clause names.** Postal code **33469** (Tequesta) is a Palm
Beach County code — 45 of its 51 lodging licences are Palm Beach — whose US-1 approach crosses the county line,
carrying 6 Martin-licensed lodging rows, 3 of them hotel-rank, every one addressed "TEQUESTA FL 33469". The
registry covers it **WHOLE**, because the governing rule of this market is the property's own postal code and
the DBPR "county" field is the LICENSING county, not the premises' postal geography. Splitting the code would be
exactly the per-property judgement the registry exists to forbid. The 3 rows are named individually in the
audit. **Every other Martin code — Hobe Sound 33455 and the 349xx Stuart / Jensen Beach / Palm City codes — is
refused by name**, as is all of St. Lucie.

**The Glades** (Belle Glade, Pahokee, South Bay, Canal Point) are admitted at FRINGE. They are forty miles
inland and agricultural rather than coastal-traveller, but they are Palm Beach County and Discover The Palm
Beaches territory; admitting them means the home county's own inventory is ACCOUNTED FOR rather than silently
dropped, and at 4 census rows the publication threshold guarantees no thin page.

## 16. Phase 8 — competitor gap challenge (BringFido, identity only)

37 Palm Beach County city slugs challenged, **972 raw rows → 747 normalized unique leads**:

| Class | Count |
|---|---:|
| EXACT_ATLAS_MATCH / ALIAS / DUPLICATE | 49 / 20 / 77 (**146 matched**, 69 distinct census identities) |
| VACATION_RENTAL | 368 |
| OUTSIDE (Broward, Miami-Dade, the Treasure Coast, other Florida cities BringFido's radius pulled in) | 44 |
| REVIEW (a listing title naming no establishment) | 176 |
| NON_HOTEL | 3 |
| **TRUE MISSING QUALIFYING** | **10** |
| **VERIFIED TRUE MISSING** | **0** |

Each true-missing candidate was verified through Google Places on the existing key: **3 were already in the
census by address or phone, 2 resolved outside the market, and 5 returned no lodging result.** Not one hotel
this market's own lanes had missed. No competitor pet text was read, stored or used.

**MATERIAL IDENTITY GAP = NO. MATERIAL POLICY GAP = NO** — the 69 matched-but-unresolved rows are the same §11
root causes, dominated by ROUTING and ACCESS_BLOCKED on the county's independent motel stock.

## 17. Phase 28 — isolation

| Check | Changes |
|---|---:|
| CROSS-MARKET FILE CHANGES | **0** |
| SHARED FACTORY CODE CHANGES | **0** |
| CURRENT LIVE CHANGES | **0** |
| DEPLOYMENT STATE CHANGES | **0** |

Every path changed is West Palm Beach owned and every helper added is prefixed `west_palm_beach_fl_`. The only
shared modules touched were *read*, never edited. `identity_resolutions.json` was not written. All acquisition
inputs (the 62.5 MB DBPR extracts, the Geofabrik Florida extract, the Firecrawl caches) are gitignored.

One self-inflicted slip is recorded rather than hidden: the first shadow seal was given a work directory whose
path the shell mangled into a repo-relative `twpb1a`, so a cold FAST build wrote output inside the repository.
**FAST rule J caught it exactly as designed** — "in-repo output must live under the gitignored data/ tree" — the
seal was re-run under `data/fast_work/`, and the stray directory was removed in its own commit.

## 18. Phases 25–27 — shadow package, FAST and reproduction

| Item | Value |
|---|---|
| Source commit holding every staged input | `04dce64360c1e879f5f419ab69cde5fdaddbaf12` |
| Package | `pkg-west-palm-beach-fl-eb802c414bf12396` |
| **PACKAGE DIGEST** | `sha256:eb802c414bf12396f96e6ae8ec12585ce137edb6de39243a65d720372fc5d941` |
| Execution zone | **SHADOW_UNTIL_REGISTERED** |
| FAST (A–O) | **15/15 PASS, 0 UNKNOWN, 0 FAILED**, `FAST_DATA_ONLY_RELEASE_ELIGIBLE = YES` |
| Declared public surface | 49 hotel profiles, 5 corridor pages, 1 comparison page, 243 `/go/` pages; **0 warnings, 0 broken internal links, 0 quality-gate failures** |
| REPRODUCTION A | this worktree, sealed twice in-process: identical digest |
| REPRODUCTION B | detached worktree `C:\t\wpb1b` at the same commit, **independent process**: identical digest **and an independent FAST 15/15 PASS** |
| **BYTE IDENTICAL** | **YES** |

**The seal-twice rule was observed, not discovered.** The seal derives four shard documents plus byte copies of
the proposed market document and census from the committed authority, so the FIRST seal always writes staged
inputs the sha it names does not yet carry. Those were committed (`04dce643`) and the seal re-run against the
commit that holds them, which is the fixed point the determinism proof needs. No staged input drifted afterwards.

## 19. Phase 29 — performance and cost

| Stage | Wall clock |
|---|---|
| Precheck + current-live resolution | ~4 min (resolver itself 3.6 s) |
| Geography (authoring + contract validation) | ~15 min |
| DBPR lane (download 62.5 MB + parse 7 extracts) | ~2 min |
| OSM lane (two-pass read of the Florida extract) | ~24 min |
| Brand inventory (23 families, 316 requests) | ~28 min |
| CVB probe + sitemaps (3 profiles measured) | ~6 min |
| Competitor challenge (37 cities) | ~6 min |
| Census reconciliation (per run, run 5 times) | ~11 min |
| Routing · static capture · Wyndham · ESA · independents | ~9 min |
| Places route discovery + gap verification (126 requests) | ~4 min |
| Firecrawl (discovery + brand pages + policy pass) | ~9 min |
| **Attended browser (61 attempts, paced)** | **~1 h 20 m wall, of which ~45 min is Marriott cooldown** |
| Adjudication + staging + partition + accounting | ~6 min |
| Shadow package + FAST (2 seals) | ~9 min |
| Independent reproduction + independent FAST | ~9 min |
| **ZERO → TECHNICAL SOURCE READY** | **~2 h 04 m** |
| **ZERO → COVERAGE READY** | **~2 h 04 m** |

| | |
|---|---|
| ACTIVE COMPUTE vs PROVIDER / COOLDOWN WAIT | ~1 h 19 m vs ~45 min |
| PROVIDER COST | Firecrawl **36 credits** (1,235 → 1,199) · Google Places **126 requests** on existing capacity · **USD 0.00** |
| **NEW PAID SPEND** | **0** — no new provider, no new key, no new plan, no credit purchase |
| Bright Data | not called |
| FOUNDER INTERVENTION | **0** |

## 20. Phase 24 — coverage readiness

`west_palm_beach_fl_actionability_001` decides this mechanically on the order's own eight conditions, never on a
percentage. All eight are true:

| Condition | |
|---|---|
| actionable unresolved = 0 | ✅ |
| no material identity gap | ✅ |
| no material unexplained policy gap | ✅ |
| authorized acquisition lanes exhausted | ✅ |
| Marriott queue terminally resolved or safely exhausted | ✅ 28 of 28 attempted; 17 read, 1 excluded, 10 terminal |
| browser-required brands processed or safely bounded | ✅ BROWSER_CAPTURE_NEEDED = 0 |
| publication set safe | ✅ 49 rows, each citing its own quote; 4 duplicate-premises halves held |
| package deterministic and FAST-clean | ✅ reproduced byte-identically, 15/15 |

- **TECHNICAL SOURCE READY = YES.** Deterministic, cross-worktree reproducible, FAST-clean, isolated, fully
  accounted: 190 = 74 resolved + 116 unresolved, one disposition per row, every hold carrying an exact reason.
- **COVERAGE READY = YES.** The 116 unresolved rows are a bounded and fully explained cohort: 108 have exhausted
  every rung the committed router opens for them, and 8 are founder-reviewable judgements on evidence already in
  hand. Not one is reachable by a lane this order was authorized to use and did not use.

The honest next levers are named and neither is a discovery problem. **First, Palm Beach County's independent
motor-court stock**: 86 independent plus 8 luxury-independent and 5 resort-independent rows are 76 % of the
unresolved set, concentrated in Lake Worth Beach (22 of 25 unresolved), and they are ROUTING (no first-party
site exists) or ACCESS_BLOCKED (their sites refuse every free client). Reaching them needs a provider
authorization this order does not have. **Second, the 10 Marriott rows** behind a wall that tightened from 12
reads per window to 1 over the course of the run; a paid browser provider would close them in minutes.

---

## FINAL ANSWERS

1. **START TIMESTAMP** = 2026-09-22T14:18:59Z
2. **ZERO_TO_SOURCE_READY** = ~2 h 04 m (≈1 h 19 m active compute, ≈45 min provider cooldown)
3. **ZERO_TO_COVERAGE_READY** = ~2 h 04 m
4. **TOTAL DISCOVERED** = 2,895 raw observations across 9 lanes
5. **NORMALIZED IDENTITIES** = 2,455 graph nodes (0 merge conflicts)
6. **QUALIFYING CENSUS** = **190**
7. **PET-FRIENDLY** = **49**
8. **VERIFIED NO-PETS** = **25**
9. **RESOLVED** = **74**
10. **UNRESOLVED** = **116**
11. **RESOLUTION RATE** = **38.95 %**
12. **ACTIONABLE UNRESOLVED** = **0**
13. **HOLDS BY CLASS** = ROUTING 58 · SOURCE_SILENT 26 · ACCESS_BLOCKED 24 · IDENTITY 4 · EVIDENCE 4 · BROWSER_CAPTURE 0 · NEGATION 0 · POLICY_NOT_FOUND 0 · MIXED_RESORT 0 · CONDO_HOTEL 0 · PAID 0 · GEOGRAPHY 0 · FOUNDER 0 · OTHER 0
14. **EXCLUSIONS BY CLASS** = vacation rental 80 · timeshare 3 · resort residence 0 · non-hotel 142 · closed 0 · outside market 1,429 · duplicate listing 0 · same-campus-distinct 0 (never admitted at all: 855 CNDO, 1,849 DWEL, 1,113 NAPT, 381 apartment-named TAPT)
15. **SOUTH-FLORIDA IDENTITIES REUSED** = **202** deduped (Miami 85, Fort Lauderdale 191, 73 seen by both); **0** policy rows imported
16. **NEW IDENTITIES** = 2,253 of 2,455 graph nodes
17. **PUBLISHING CORRIDORS** = **5** — downtown-west-palm-beach, palm-beach-gardens, palm-beach-international-airport, delray-beach, boca-raton (of 15 corridors over 60 admitted postal codes, 0 uncorridored rows)
18. **BROWARD ADMITTED** = **0** (609 hotel-rank licences discovered; the LIVE fort-lauderdale-fl market owns them)
19. **MIAMI-DADE ADMITTED** = **0** (737 discovered; the LIVE miami-fl market owns them)
20. **MARTIN COUNTY ADMITTED** = **3** (29 discovered) — all three on shared postal code 33469, which the registry covers whole, each row named in the audit; every 33455 / 349xx code refused by name
21. **COMPETITOR RAW / NORMALIZED / MATCHED / TRUE MISSING** = 972 / 747 / 146 / 10 — **0 verified true-missing**
22. **MATERIAL IDENTITY GAP** = **NO**
23. **MATERIAL POLICY GAP** = **NO**
24. **FIRECRAWL ATTEMPTED / SUCCESS** = 31 attempts (8 discovery + 3 brand pages + 19 policy pass + 1 Marriott capability probe) / 4 publication-grade reads + 15 new Choice routes + 3 brand pages with their own address
25. **MARRIOTT CENSUS** = **28**
26. **MARRIOTT BROWSER ATTEMPTED** = **28** (100 % of routed properties)
27. **MARRIOTT READ SUCCESS** = **17** (plus 1 read and excluded as TIMESHARE)
28. **MARRIOTT CHALLENGE DENIED** = **10**, terminal, across 13 paced windows
29. **MARRIOTT ACTIONABLE REMAINING** = **0**
30. **OTHER BROWSER ATTEMPTED / SUCCESS** = Hilton 28/28 · Hyatt 3/3 · Best Western 2/2
31. **ACCESS_BLOCKED AFTER ROUTER EXHAUSTION** = **24**
32. **EXISTING PROVIDER CREDITS USED** = Firecrawl **36** (1,235 → 1,199) · Google Places **126** requests
33. **NEW PAID SPEND** = **0**
34. **PROVIDER COST** = **USD 0.00**
35. **SHADOW PACKAGE CREATED** = **YES** — `pkg-west-palm-beach-fl-eb802c414bf12396`, SHADOW_UNTIL_REGISTERED
36. **PACKAGE REPRODUCIBLE** = **YES** — byte-identical in a detached worktree, independent process, with an independent FAST 15/15
37. **PACKAGE DIGEST** = `sha256:eb802c414bf12396f96e6ae8ec12585ce137edb6de39243a65d720372fc5d941`
38. **FAST** = **15/15 PASS, 0 UNKNOWN, 0 FAILED**
39. **TECHNICAL SOURCE READY** = **YES**
40. **COVERAGE READY** = **YES**
41. **CROSS-MARKET FILE CHANGES** = **0**
42. **FACTORY CODE CHANGED** = **NO**
43. **BROAD REGRESSION RUNS** = **0**
44. **FINAL CANDIDATE CREATED** = **NO**
45. **FOUNDER AUTHORIZATION CREATED** = **NO**
46. **WEST PALM BEACH DEPLOYED** = **NO**
47. **origin == HEAD** = YES
48. **tree clean** = YES

---

WEST PALM BEACH SOURCE READY = YES
WEST PALM BEACH COVERAGE READY = YES
ACTIONABLE UNRESOLVED = 0
FAST = 15/15 PASS
FACTORY CODE CHANGED = NO
BROAD REGRESSION RUNS = 0
WEST PALM BEACH FINAL CANDIDATE = NO
WEST PALM BEACH DEPLOYED = NO
WAITING FOR RELEASE QUEUE = YES
