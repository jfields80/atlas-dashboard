# PTF-JACKSONVILLE-FL-HARDENED-SOURCE-READY-001 — FINAL

Market `jacksonville-fl` — **Jacksonville / Northeast Florida**.
Branch `worker/ptf-jacksonville-fl-market-001`, worktree `C:\Atlas-Jacksonville-FL-Hardened-V1`.
Base: the CURRENT hardened lineage — lineage-test-047 semantics repair (`bf7a54c3`) on top of the live West Palm
Beach release (`e3efa221`). **Not** origin/main, which the resolver reported stale.

Built from zero: no prior Jacksonville FLORIDA market, census row, policy fact or evidence row existed, and — as
§3 measures — **no prior market of the 33 live ones holds a single node in any of this market's 47 admitted
postal codes.** This is a genuine cold start for identity.

Status: **SHADOW_UNTIL_REGISTERED**. Nothing registered, participated, authorized, pinned or deployed.

---

## 1. Phase 1 — lineage

The worktree opened on `efd22bc7` (the deployment work_order repair on the Fort-Lauderdale-live release), which
predates West Palm Beach going live. The order forbids building on stale ancestry, so the branch was
fast-forwarded to `bf7a54c3` — a strict descendant — after verifying that it contains every repair the order
names:

| Repair | Commit | In `bf7a54c3` |
|---|---|---|
| release-factory reuse | `0b6ad264` | ✅ |
| deployed-bundle parent lookup | (content of `cd8cb3d7`, cherry-picked into `0b6ad264`) | ✅ |
| canonical authorized-nonlive re-registration | `4cbe6e4c` | ✅ |
| FAST non-empty bundle guard | `f182cc08` | ✅ |
| FAST receipt-reader guard | `e59883f7` | ✅ |
| participation guard repair | `09851d50` | ✅ |
| supersessions lineage repair | `9075596f` | ✅ |
| deployment work_order semantics | `efd22bc7` | ✅ |
| lineage test 047 semantics | `bf7a54c3` | ✅ |
| West Palm Beach LIVE | `e3efa221` | ✅ |

The fast-forward conflicted with nothing: the tree was clean and held no Jacksonville work.

## 2. Phase 2 — CURRENT VERIFIED LIVE

Resolved **mechanically**, never assumed (`release_index live-source --verify-host`, 2.8 s):

| | |
|---|---|
| CURRENT LIVE SOURCE COMMIT | `e3efa2210f759886aaad830b07fa241231a8f734` (built_from `ff6b506d`) |
| CURRENT LIVE DEPLOYMENT | `6ab599163f833ab7f48b395d` (west-palm-beach-fl) |
| CURRENT LIVE BUNDLE SHA | `23728b4bff71c66d0a9a063de3882d744f92465f5f568f72b3caf16ca8641d78` |
| CURRENT LIVE SITEMAP SHA | `8ae34cea1c7e384f0f4c8499066c5ff2f9ca841d099c344a5860041b4b6c7546` |
| CURRENT LIVE MARKETS / PROFILES | **33 / 2,424** |
| CURRENT LIVE SERVED ROUTES | **2,767** |
| head_contains_live · origin_main_stale · **HOST VERIFIED** | true · true (never used) · **true** |

West Palm Beach live ✅ · Fort Lauderdale live ✅ · **Detroit absent from the participating set** ✅.
Nothing in production was touched (§14).

## 3. Phase 8 — owned data first, and the answer was ZERO

Every committed market graph in the repository was scanned row by row for a node whose own postal code this
market admits. **Not one of the 33 live markets has a node in any of the 47 admitted codes.** The three South
Florida markets' observation boxes stopped at the Treasure Coast, Orlando V2's and Tampa V2's south of the
St. Johns River, Savannah's at the Georgia coast.

| | |
|---|---|
| OWNED IDENTITIES in admitted codes | **0** |
| OWNED VALID POLICY EVIDENCE | **0** (none exists to import; asserted row by row) |
| OWNED ROUTES | **53** Marriott JAX-prefix routes from the committed national harvest, at **0** new requests |
| OWNED REBRANDS / CLOSURES applicable | 0 |
| OWNED COLLISIONS | **3** — see §4 |
| PRIOR PROVIDER HISTORY | 46 Firecrawl calls, **0** for a Jacksonville URL |

What the neighbours *did* see is recorded as provenance: Orlando V2 holds 760 nodes in codes this market names
OUTSIDE, Savannah 237, jacksonville-nc 29 (its own), miami-fl 1, tampa-fl 3, greenville-nc 2.

## 4. THE MARKET'S DEFINING HAZARD: "Jacksonville" DECIDES NOTHING

This market is named after a city that exists at least six times, and one of the others is **LIVE**.

**ACROSS STATES.** `jacksonville-nc` is production market #22 — Jacksonville, Onslow County, North Carolina
(Camp Lejeune; ZIPs 285xx). Every national chain publishes near-identically named hotels in both cities.

**AND THE SHARED EXCLUSION REGISTRY MATCHES ON NAME FIRST.** `hotel_exclusions.exclusion_for` compares the
normalised canonical name *before* anything else and returns a hit **regardless of address**. The committed file
carries three jacksonville-nc exclusions qualified by nothing beyond the word "Jacksonville":

* `courtyard by marriott jacksonville` — 5046 Henderson Drive, Jacksonville **NC** 28546
* `fairfield by marriott inn and suites jacksonville` — 121 Circuit Lane, Jacksonville **NC** 28546
* `microtel inn and suites by wyndham camp lejeune jacksonville` — 2411 Commerce Rd, Jacksonville **NC** 28546

A Florida row whose own trade name normalises to one of those would be **silently excluded by another market's
premises** — and a state licence record routinely drops a brand's marketing suffix, so it is a realistic row.
`foreign_name_collision` checks every admitted row against those strings and HOLDS any hit with the exact
reason. **Measured this run: 0 rows collided.** The exposure is real, bounded and now watched.

This order did **not** edit the shared file and did **not** supersede another market's exclusion: that is a
cross-market change and a founder decision.

**INSIDE FLORIDA.** Duval County is a CONSOLIDATED city-county, so the postal city "JACKSONVILLE" is the postal
city of 25 lodging-bearing codes across 39 miles — from the Georgia line to the St. Johns County line and from
the Atlantic to Baldwin. "Jacksonville" places nothing here either. Only the postal code does.

## 5. Phases 3–6 — the geography

`jacksonville_fl_geography_001` → **17 corridors over 47 admitted postal codes**, a strict postal-code partition
(13 CORE / 3 CORRIDOR / 1 FRINGE), 22 observation cells (17 admitting, 5 observation-only reaching St. Augustine,
Palm Coast, Baker County, Putnam County and across the GEORGIA line to Kingsland). The registry collides with
**none** of the 34 registered markets' postal codes, and `jacksonville-nc`'s own ZIPs are named in the OUTSIDE
table so the two can never be confused.

### DOWNTOWN JACKSONVILLE IS NOT THE MARKET

The order's first instruction, and the state's own register settles it. Downtown (32202 + 32206) carries **5**
hotel-rank lodging licences of the market's 258 — **under 2 %**. The weight is suburban, airport and island:

| Code | Place | Hotel-rank licences |
|---|---|---:|
| 32218 | JAX Airport / Dunn Ave / River City Marketplace | **29** |
| 32034 | Amelia Island / Fernandina Beach | **32** |
| 32256 | Deerwood / Baymeadows / Southpoint | **26** |
| 32216 | Southside / University Blvd / Philips Hwy | **18** |
| 32250 | Jacksonville Beach | **16** |
| 32073 | Orange Park (CLAY) | **14** |
| 32207 | Southbank / San Marco | **13** |
| 32246 | St. Johns Town Center | **12** |
| **32202 + 32206** | **DOWNTOWN** | **5** |

Modelling this market as downtown Jacksonville would have discarded 98 % of it.

### THE AIRPORT TEST ANSWERS **YES** HERE — THE FIRST TIME IN FLORIDA

PBI and FLL each got no corridor because neither owned a postal code. **JAX owns 32218**, which carries 29
hotel-rank licences — the market's largest single code. The corridor exists, and is named
`jax-airport-northside` rather than "airport" because the same postal system carries Dunn Avenue, Oceanway,
Dames Point and the northwest Duval blocks.

### AND THE CRUISE, MILITARY AND MEDICAL TESTS ALL ANSWER **NO** — MECHANICALLY

| Overlay | Test | Result |
|---|---|---|
| JAXPORT cruise terminal | owns a hotel-bearing code no corridor claims? | **NO** — Dames Point is 32226, 1 licence, already claimed. The PortMiami / Port of Palm Beach finding, not Port Everglades. |
| Naval Station Mayport | 32227 / 32228 lodging licences | **ZERO.** Mayport Village's inventory is addressed ATLANTIC BEACH 32233. Overlay. |
| NAS Jacksonville | 32212 lodging licences | **ZERO.** Overlay. Navy Lodge / Navy Gateway billeting refused by name as non-public lodging. |
| Mayo Clinic Jacksonville | owns a code? | **NO** — San Pablo Road is 32224 with UNF and Tinseltown. A demand driver, never a premises fact. |

### THE FOUR-COUNTY TEST, AND THREE OF THE FOUR ARE SPLIT

This is the first market in the factory with **no single home county**. County inclusion is not traveller-market
inclusion, and the split is the proof.

| County | Hotel-rank discovered | **Admitted** | Ruling |
|---|---:|---:|---|
| **Duval** | 193 | **193** | admitted whole — the consolidated city-county |
| **Clay** | 20 | **19** | SPLIT — Orange Park / Fleming Island / Middleburg / Green Cove Springs / Oakleaf in; **Keystone Heights out** |
| **Nassau** | 42 | **42** | admitted, SPLIT BY TIER — Amelia Island CORRIDOR, mainland FRINGE |
| **St. Johns** | 124 | **6** | SPLIT HARDEST — Ponte Vedra Beach and Fruit Cove in; **every St. Augustine code out** |
| Baker | 5 | **0** | refused by name |
| Putnam | 19 | **0** | refused by name |
| Flagler | 26 | **0** | refused by name — future palm-coast-flagler-fl |
| Alachua | 69 | **0** | refused by name — future gainesville-fl |
| Volusia | 236 | **0** | refused by name — future daytona-beach-fl |

**ST. AUGUSTINE IS REFUSED ENTIRELY**, and the register makes that a market-scale fact rather than a judgement:
**110 hotel-rank licences under the St. Augustine city names, 29 more in 32080 (St. Augustine Beach) and 9 in
32092 (World Golf Village)** — a larger hotel-rank inventory than most PetTripFinder markets publish in total.
It has its own CVB, the nation's oldest historic district and a separate resort-golf destination. Absorbing it
would destroy a future market rather than extend this one. **ADMITTED: 0.**

**KEYSTONE HEIGHTS** is this market's smallest and clearest proof: it is CLAY COUNTY — the same county as Orange
Park — and it is refused, because it sits 45 miles inland in the Trail Ridge lake district and is oriented to
Gainesville. One hotel-rank licence, admitted **0**.

### AMELIA ISLAND: CORRIDOR, AND THE CHOICE IS ON THE RECORD

The order requires an explicit choice among CORRIDOR, FRINGE and FUTURE STANDALONE. **CORRIDOR.** Nassau County
is inside the Jacksonville MSA, JAX is the island's airport with no closer commercial field, the A1A / I-95
exit 373 approach is a Jacksonville traveller flow, and 32 hotel-rank licences is real inventory no other market
publishes. It is admitted at CORRIDOR tier and not CORE **precisely because** it is recorded here as this
market's NAMED first candidate for promotion to a standalone market — its own CVB, its own county, two flagship
resort campuses. A founder can promote it later on this record instead of discovering the question after
publication.

### PONTE VEDRA: WHERE THE CVB TEST AND THE TRAVELLER TEST DISAGREE, AND THE DISAGREEMENT IS RECORDED

Florida's Historic Coast markets Ponte Vedra Beach together with St. Augustine. The traveller reality is that
Ponte Vedra Beach is the next beach south of Jacksonville Beach on A1A with no gap between them, and its resorts
route guests through JAX 25 miles north. **The traveller test governs and the CVB fact is written down rather
than hidden.** 32082 is admitted; every St. Augustine code is not.

And the market proved the point on its own inventory, in both directions:

* `jaxpbhx` — "Hampton Inn **Jacksonville/Ponte Vedra Beach**-Mayo Clinic Area" — own address **Jacksonville
  Beach 32250**, and Hilton's own breadcrumb files it under "Jacksonville Beach Hotels". Placed in
  `jacksonville-beach`.
* `jaxpvgi` — "Hilton Garden Inn **Jacksonville** Ponte Vedra Sawgrass" — own address **Ponte Vedra Beach 32082**.
  Placed in `ponte-vedra-beach-sawgrass`.

Two hotels, two names that each claim the other's town, each placed by its own postal code.

## 6. Phases 7 and 9 — the resort / condo / vacation-rental wall

Northeast Florida's lodging register is overwhelmingly rental stock, and none of it entered the graph.

| Rank in ADMITTED codes | Count | Treatment |
|---|---:|---|
| CNDO (resort condominium units) | **1,349** | never admitted |
| DWEL (resort / vacation dwellings) | **1,920** | never admitted |
| NAPT (non-transient apartments) | **959** | never admitted |
| TAPT refused by their own name | **60** | apartment / RV / unit / investment entities |
| HOTL / MOTL / BNB / hotel-named TAPT | 160 / 74 / 11 / 15 | the census leads |

**Nassau County carries 1,130 resort-condominium licences against 32 hotel-rank ones** — Amelia Island
Plantation's and the Omni resort's villa programmes, licensed unit by unit. St. Johns carries 1,472 CNDO and
2,139 DWEL. Duval carries 1,268 vacation dwellings against 193 hotel-rank licences.

`NOT_LODGING_WHY` is **EMPTY at authoring time and nothing was inherited**: West Palm Beach's Marriott's Oceana
Palms timeshare ruling names a Riviera Beach premises and was not carried here, exactly as Fort Lauderdale's
BeachPlace Towers ruling was not carried into that market.

## 7. Phases 10–13 — the census backbone, built from public registers

| Lane | What it read | Requests | Cost |
|---|---|---:|---:|
| **Florida DBPR** public-lodging register (`hrlodge1..7.csv`) | 9 counties, rank-classified | 7 | $0 |
| **Geofabrik / OSM** Florida extract, two-pass pyosmium | 488 elements (hotel 274, apartment 114, motel 66, guest_house 34); 206 with a postcode, 209 with a street | 1 (cached extract) | $0 |
| **Brand inventory** (rung 2 — each brand's own directory) | 144 leads: MARRIOTT 48, HILTON 50, WYNDHAM 31, ESA 7, SONESTA 1, WOODSPRING 7 | 288 | $0 |
| **Destination roster** (4 bureaux) | 391 rows → 237 admitted / 154 refused; 218 websites, 236 phones, 237 full premises | 2,788 | $0 |
| **Competitor directories** (AUDIT lane only) | 915 raw → 699 normalized | 96 | $0 |
| **Places** | route discovery + policy pages | 82 | $0 |
| **Firecrawl** | discovery 8 + brand pages 44 + policy pass 70 | 122 credits | **$0.00** (existing capacity) |

**Free HTTP total: 3,089 requests.** No new provider was authorized, no new spend was incurred, and Firecrawl
was drawn only from already-authorized capacity (balance 1196 → 1074). Per the standing rule the cap was set on
ATTEMPTS, not on the balance, because the balance settles late.

### The four bureaux, and why each needed its own reader

| Bureau | Discovery | Rows | Category signal |
|---|---|---:|---|
| Visit Jacksonville | `SITEMAP_DIRECTORY` | — | page category: Restaurant 766, **Hotel 168** |
| Florida's Historic Coast | `SEED_PAGE` | — | **Accommodation 155** (observation-only: St. Augustine) |
| Amelia Island CVB | `SEED_PAGE` | — | **LodgingBusiness 53**, read off the JSON-LD `@type` |
| Ponte Vedra / Beaches | `SEED_PAGE` | — | Accommodation |

The category was read **off each page**, never off the link text — the standing rule that page code beats a
name-bound code. The Amelia CVB publishes no category taxonomy at all, so its rows were classified by schema
type instead, which is why the reader exposes `_schema_types()`.

### Three roster defects found and fixed, all of them identity-critical

1. **A bureau street carried the cross-street.** "4670 Salisbury Road | I-95 &amp; J.Turner Butler Blvd." parsed
   as a street, producing **two rows for one premises**. Fixed by parsing the address **from the END** (the
   postal code is the anchor, never the head) plus a double `html.unescape`. Re-run with `--reparse` over the
   **persisted bytes** — 391 rows reparsed at **0 new requests**.
2. **A substring reseller test refused 40 first-party links.** `hotels.com` is a substring of
   `choicehotels.com`, `wyndhamhotels.com` and `magnusonhotels.com` — three brands' OWN hosts. Replaced with a
   registrable-**host** test plus a booking-engine-subdomain rule; 16 test cases, 0 failures; refusals fell to
   **13 genuine** resellers (Agoda, WebRez, ResNexus, ThinkReservations, pegsbe, guestreservations).
3. **A bureau link outranked the brand's own route.** A census route-preference pass repointed **9 rows** to the
   brand's own property page. Tier 1 PROPERTY_PAGE outranks a tier 3 bureau link — always.

The same substring class of defect appeared in the brand lane: **`jacksonville-or` matched inside
`jacksonville-orange-park`** and would have thrown away two real Marriott hotels. Fixed with boundary-aware
patterns, 8 test cases, all passing. Both defects were in code this order authored; neither is in shared factory
code.

## 8. Phase 14 — the acquisition ladder, rung by rung

Every rung was attempted in order and the cheapest sufficient one won.

| Rung | Lane | Outcome |
|---|---|---|
| 0 | owned national corpus | 53 Marriott routes at 0 requests; **0** owned identities (§3) |
| 2 | brand's own inventory / sitemap | 144 leads, $0 — the backbone of brand coverage |
| 3 | static plain client | **48** first-party policy reads |
| 4 | Firecrawl | **30** reads (8 discovery-derived + 22 brand pages) |
| 5 | supported attended browser | **120** reads recorded; the only rung that answers Hilton and Marriott |

Kept first-party policy reads: **78** — DIRECT_STATIC_FETCH 48, FIRECRAWL 8, FIRECRAWL_BRAND_PAGE 22.
Refused: **441**, of which the largest single class is `browser_no_name_on_page: 74` — a **measured limit of this
order's own browser recording**, documented in the module rather than papered over (§10).

## 9. Phase 15 — brand-family closure, including the one the order forbids postponing

### MARRIOTT — closed, and the ceiling is measured, not asserted

The order says Marriott closure may not be postponed and that every Marriott row must end RESOLVED or
TERMINALLY HELD WITH AN EXACT REASON. It is closed.

* **43** Marriott properties are in-market (of 53 owned JAX-prefix routes; 10 PRESUMED_OUTSIDE).
* **All 43 were ATTEMPTED.** **24 were read.**
* The remaining **19 are TERMINALLY HELD as `ACCESS_BLOCKED / akamai_bot_manager`**, each with its property
  code, the attempt count, and the window in which it was attempted.
* **MARRIOTT ACTIONABLE REMAINING = 0** — every row has a disposition; none is awaiting an action this order
  could take.

**The Akamai ceiling, measured:** window 1 returned **17** reads. Every window after it returned **exactly 1**,
across **8 further windows**. That is a per-window quota, not a transient failure, and it means the remaining 19
would cost 19 more pacing windows for reads Akamai has already rate-limited. The order forbids bypassing Akamai,
Browser-JS exfiltration, relay hacks and hammering. **None was used.** No JS exfiltration, no opener relay, no
blob transfer, no CAPTCHA interaction, no header spoofing, no proxy.

### EXTENDED STAY AMERICA — terminal for the whole family, and the reason is a CAPTCHA

ESA answered a plain client **one market earlier**. In this market it returns **403 at both the city directory
and the property pages**, and the attended browser shows a **DataDome CAPTCHA**. Solving or bypassing a CAPTCHA
is prohibited, so the lane was **NOT ATTEMPTED past the wall** — recorded as terminal for the family with the
exact blocker. The 7 ESA leads are held `ACCESS_BLOCKED`, not dropped.

### HILTON — 50 leads, and 4 rows held on a two-reader disagreement

Hilton answered well. Four rows were held `AMENITY_CHIP_ONLY`, and rather than guess, the pages were **re-read**:
those PETS blocks genuinely carry no free-text sentence — only a chip. A chip is not a policy statement, so the
hold is correct. Where two readers disagree the answer is an `EVIDENCE_HOLD`, never a coin flip.

### WYNDHAM / CHOICE / SONESTA / WOODSPRING

Wyndham 31 leads and Choice both answered the free lanes. No new provider was needed for any family.

## 10. Phase 16 — the attended browser, and the limit it hit

**120 reads** were recorded by hand into
`markets/staging/jacksonville-fl/raw_captures/browser_reads_001.jsonl` — durable bytes on disk, not an ephemeral
transcript. Per the order, no evidence in this market is ephemeral-only or byte-count-only.

Two browser defects were found and fixed:

1. **`page_zip` read the house number as the postal code** ("14565 Duval Road" → "14565"). Fixed by taking the
   **LAST** five-digit run, never the first.
2. **Motel 6 would not bind**: the census states "8285 PHILLIPS HIGHWAY", the page "8285 Philips Hwy", and a
   *different* hotel (Knights Inn, 8285 Dix Ellis Trail) shares the house number **and** the ZIP. Fixed by
   applying the market's street fold in the browser lane and adding street-type tokens to the drop list — so the
   fold decides on the distinctive words and the near-collision still refuses.

**The measured limit:** 74 attended-browser rows carry no `page_title`, so `_row()` — which refuses a nameless
page rather than mint an empty identity key — refused them. That is honest: the alternative was to **invent
names**, and an invented name is worse than a recorded gap. It is written into the module docstring and counted
in the accounting as `browser_no_name_on_page: 74`.

This also caught a real crash first: census pass 5 failed with
`IdentityKeyError: name '' produces an empty identity key`. The fix was to refuse the row, not to loosen the
shared key contract.

## 11. Phase 17 — the street fold, audited in both directions

Northeast Florida has four street spellings that split one premises into two keys. The fold is applied **to the
merge key only, never to the stated address**:

| Fold | Why this market needs it | Keys changed |
|---|---|---:|
| `PHILLIPS → PHILIPS` | Philips Highway is spelled both ways by the state and the brands | 6 |
| `A-1-A / A1A / SR A1A → A1A` | the coastal highway through Ponte Vedra, the Beaches and Amelia | 20 |
| `SAINT → ST` | St. Johns, St. Augustine Road | 2 |
| `J.Turner Butler → Butler` | JTB Boulevard, written six ways | 1 |
| ordinal words → digits | Beaches street grids ("Third Street" / "3rd St") | 8 merge keys |

**Audit: 1,641 streets seen, 29 changed, `no_unrelated_street_rewritten = True`.** A fold that rewrote anything
it was not aimed at would be a silent data corruption; it was proved not to.

## 12. Phase 18 — the competitor lane is an AUDIT lane

Per the standing rule, competitor directories may challenge coverage but may never acquire it. Nothing in the
graph came from a competitor.

| | |
|---|---:|
| Raw competitor rows | 915 |
| Normalized | 699 |
| Matched to Atlas | 168 (123 distinct) |
| **TRUE_MISSING** | **4** |
| VERIFIED from a competitor | **0** |

Disposition: VACATION_RENTAL 251 · REVIEW 229 · EXACT_ATLAS_MATCH 95 · DUPLICATE 45 · OUTSIDE 44 · ALIAS 28 ·
NON_HOTEL 3 · TRUE_MISSING 4. The four TRUE_MISSING rows are carried as challenges with their exact source, not
as inventory.

**The census's own competitor accounting agrees: 589 competitor-only nodes, of which TRUE HOTELS = 0.**

## 13. Phases 19–22 — the census, the graph and the 268

| | |
|---|---:|
| Raw observations | **2,906** |
| Graph nodes (hard key) | **2,007** |
| Name attachment | bound 229 · ambiguous 26 · unbound 697 |
| Merge conflicts caught | **44** |
| **Confirmed identities (TRUE_HOTEL_IDENTITY)** | **268** |

Lane yields: DBPR 1,168 · OSM 412 · brand owned 48 · brand city page 50 · brand sitemap 60 ·
destination organisation 391 · competitor leads 699 · **first-party PROPERTY_PAGE 78**.

Classification of the 2,007 nodes: OUTSIDE_MARKET **1,031** · NAME_ONLY_UNRESOLVED 458 · NON_LODGING 217 ·
IDENTITY_REVIEW_REQUIRED 33 · **TRUE_HOTEL_IDENTITY 268**. That a clear majority of nodes classify OUTSIDE is the
geography working: the DBPR extract and the OSM extract both reach far past this market's box, and the postal
code sends them back.

### Routing — 268 rows, every one with a state

| Routing state | Rows |
|---|---:|
| ROUTED_OFFICIAL_DESTINATION | 110 |
| ROUTED_OFFICIAL_INVENTORY | 76 |
| INDEPENDENT_REVIEW | 50 |
| FREE_LANE_EXHAUSTED | 26 |
| ROUTED_MAP_WEBSITE | 5 |
| ROUTE_BRAND_MISMATCH | 1 |

By family: INDEPENDENT 116 · MARRIOTT 41 · HILTON 36 · IHG 22 · CHOICE 14 · WYNDHAM 13 · ESA 6 · BEST_WESTERN 5 ·
HYATT 4 · MOTEL6 4 · OMNI 2 · RADISSON 2 · RED_ROOF 2 · SONESTA 1. 14 routes were filled from the owned corpus
(MARRIOTT 13, INDEPENDENT 1) at zero requests.

**A late defect worth recording.** Eight Marriott census rows reached through the destination organisation carry
an EMPTY `property_code` — a bureau never publishes one — while their route is still Marriott's own property page,
which spells the code in its path. The read-to-census rebind indexed only the explicit field, so those rows saw
none of their own attempts, and the adjudicator reported **SpringHill Suites Jacksonville Airport** as
`BROWSER_CAPTURE_NEEDED` — awaiting a read it had already been denied three times. Fixed by reading the MARSHA
code off **both** sides' URLs, which is the brand's own identifier and not a name. `BROWSER_CAPTURE_NEEDED` went
from 1 to **0** and the row took its correct terminal state, `ACCESS_BLOCKED`.

## 14. Phase 23 — adjudication: 95 publishable, 18 no-pets, 155 held

| Disposition | Rows |
|---|---:|
| **CLEAN_PET_FRIENDLY** | **95** |
| **CLEAN_VERIFIED_NO_PETS** | **18** |
| ACCESS_BLOCKED | 53 |
| ROUTING_HOLD | 43 |
| SOURCE_SILENT | 25 |
| EVIDENCE_HOLD | 22 |
| IDENTITY_MISMATCH_HOLD | 12 |
| **BROWSER_CAPTURE_NEEDED** | **0** |
| **RESOLVED / rate** | **113 of 268 — 42.2 %** |

**Negation conflicts caught: 20.** Twenty rows where one source's phrasing would have published a hotel that its
own page contradicts. Silence never became a "no", and an amenity chip never became a policy: both rules are
asserted as fields in the adjudication artifact (`no_inference_from_silence`,
`no_inference_from_amenity_alone`).

Every one of the 155 held rows carries an exact reason, and **not one is actionable** (§16).

### The dual-brand hold this order deliberately did NOT resolve

1201 Kings Avenue carries two Hilton property codes — `jaxsbgi` and `jaxdnhw`. By the standing rule that is
**TWO hotels**, not one, and resolving it means writing `identity_resolutions.json`. That file is **shared,
multi-market data** and its contract requires `reviewer_id` and `reviewed_at` — a *reviewed* decision. Signing a
review in the operator's name is forbidden, and editing a shared file is outside this order. So the pair is left
as a founder-reviewable `IDENTITY_MISMATCH_HOLD` with both codes, the address and the reasoning recorded.
**CROSS-MARKET FILE CHANGES = 0** is preserved, and a registration order can resolve it in one edit.

## 15. Phase 24 — the partition, and what it publishes

`contract issues = 0`.

| Publication state | Rows |
|---|---:|
| **PUBLISHED_PET_FRIENDLY** | **95** |
| **VERIFIED_NO_PETS** | **18** |
| ACCESS_BLOCKED | 53 |
| AWAITING_POLICY_OBSERVATION | 47 |
| AWAITING_OFFICIAL_URL | 43 |
| AWAITING_ROUTING_REPLACEMENT | 12 |

**10 of the 17 corridors publish**: jax-airport-northside, westside-i10-i295, southside-university-boulevard,
st-johns-town-center-gate-parkway, deerwood-baymeadows, mandarin-bartram-julington-creek, jacksonville-beach,
atlantic-neptune-beach-mayport, orange-park-fleming-island, amelia-island-fernandina-beach. Seven corridors
publish nothing yet and are held rather than deleted — a corridor with no publishable row is a coverage fact, not
a geography error.

Staged authority: **95 policy records, 0 refused, 0 package issues**; pet-fee computability
`COMPUTATION_SAFE_ONE_PET_ONLY 53 / NOT_COMPUTABLE 42` — the fee is computed only where the page states enough to
compute it, and 42 rows publish the policy without a computed fee rather than guess one.

Both documents were written **inside the market's own staging tree**, not at the package root, because the root is
where a REGISTERED market's documents live. The staged name is already the role name a later registration order
needs (`jacksonville_fl_proposed_authority_001.json`), so that step is a move and not a rename — the mistake that
cost Orlando all fifteen checks.

## 16. Phase 28 — ACTIONABLE UNRESOLVED = 0, each class on its own terms

| Hold class | Rows | **Actionable** | Why not actionable |
|---|---:|---:|---|
| ACCESS_BLOCKED | 53 | **0** | Akamai / DataDome walls; every row attempted, bypass prohibited |
| ROUTING_HOLD | 43 | **0** | no first-party route exists in any authorized free lane |
| SOURCE_SILENT | 25 | **0** | the property's own page states no pet policy — UNKNOWN is a valid answer |
| EVIDENCE_HOLD | 22 | **0** | two readers disagree, or only an amenity chip exists |
| IDENTITY_MISMATCH_HOLD | 12 | **0** | needs a *reviewed* shared-data decision, outside this order |
| **TOTAL** | **155** | **0** | |

Conditions measured, not asserted: `actionable_unresolved_is_zero` ✅ · `no_material_identity_gap` ✅ ·
`no_material_unexplained_policy_gap` ✅ · `authorized_acquisition_lanes_exhausted` ✅ ·
`marriott_queue_terminally_resolved_or_exhausted` ✅ · `browser_required_brands_processed_or_bounded` ✅ ·
`publication_set_safe` ✅.

## 17. Phase 26 — the shadow seal, and the THREE REAL DEFECTS the first FAST run caught

The first seal produced `pkg-jacksonville-fl-aa0fe302`, reproducible in process, and FAST refused it: **C FAIL, G FAIL,
J FAIL, K UNKNOWN**. Every one of the three was a genuine data defect in this market's own modules, and the most
serious would have published a row belonging to a LIVE market. They are recorded here because a guard that fires
is the guard working.

### RULE G — a bare CHAIN label claimed an identity that **miami-fl already publishes**

> `identity 'home2 suites by hilton' is published by jacksonville-fl and miami-fl`
> `identity 'home2 suites by hilton' moves from miami-fl to jacksonville-fl`

The row is **Home2 Suites by Hilton Fernandina Beach / Amelia Island** (`jaxfbht`, 2246 Sadler Rd, 32034). Its
own tier-1 brand page names it in full — the full name was even sitting in its own alias list — but the canonical
name came out as the bare chain "Home2 Suites by Hilton". Published, it would have **taken Miami's identity**.

The census already had a repair pass for exactly this (`name_bare_identities`, for a map source that leaves a
property named after its chain). It skipped this row because its bareness test was a **token count**: more than
two words and the name was assumed specific. Four words of pure chain walked through.

**The test is now on what the tokens ARE**, not how many there are: a name built only from chain words and words
that distinguish nothing ("by", "suites", "inn", "stay", "america") names a **chain**, however long it is.
Self-tested on 13 cases — `Home2 Suites by Hilton`, `Hampton Inn & Suites`, `Extended Stay America`,
`Four Points by Sheraton`, `Holiday Inn Express`, `Courtyard by Marriott` all read as chains, while
`Home2 Suites by Hilton Jacksonville Airport`, `Hampton Inn & Suites Middleburg`, `Omni Amelia Island Resort`,
`Florida House Inn`, `Sea Cottages of Amelia` and `Casa Marina Hotel` all read as properties.

**This is the §4 hazard arriving from the direction nobody watched.** The collision guard this order built watches
Florida rows against *jacksonville-nc's* names. This collision came the other way: a Florida row with no place in
its name colliding with *miami-fl's* row of the same bare name. The guard that caught it was the shared release
lane's, and it earned its place.

### RULE C — a campaign link is not a route (2 rows), and a TIERED fee is not one number (2 rows)

> `hyatt place jacksonville st johns town center: WRONG_PROPERTY — page carries HYATT property code 'jaxzs', the identity is 'hotel'`

The identity's own `official_url` ended `?src=vanity_hyattplacejacksonvillestjohnstowncenter.com`. The **shared**
`brand_scoped_property_identity` reader cannot see a property code past a query string, so it read the code as the
literal word **"hotel"** out of `/en-US/hotel/florida/…` — and the identity then disagreed with its own page.
**15 census routes carried campaign or session query strings** (`?src=`, `utm_*`, `gclid`, `iata=`, `cid=`,
`_ga=`, a bare `?`) and **3 still carried `&amp;`** from the source's HTML, because a Google Business Profile and a
bureau publish the campaign URL rather than the page.

The repair is on **this market's data, never on the shared reader**: a route is the property's page, so tracking
parameters are stripped and entities unescaped, while a parameter a page actually needs
(`?propertyCode=AHB`) survives. Self-tested on 7 URLs; after the repair the shared reader reads `jaxzs` and
`jaxrj` correctly.

> `hampton inn and suites middleburg: FACT_CONTRADICTED — pet_fee 7500 cents, cited quote reads [12500]`

Hilton states **"1-4nts $75, 5+nts $125 per stay"**. Publishing 7500 cents asserts a fee the page does not state
for a five-night stay, and the binding was right to refuse it. A quote naming **more than one distinct amount** is
now **NOT COMPUTABLE**: acceptance, weight limit, count and species still publish from the same quote — the page
states each of those exactly once — and the fee does not. A quote that repeats the *same* amount
("1-6 nights: $100 / STAY | 7-30 nights (includes $100 cleaning fee)") is not tiered and still computes, which is
why Hyatt Place Jacksonville Airport passed on the first run and still does.

### RULE J — the work directory, and a Windows path that ate itself

> `build failed: in-repo output must live under the gitignored data/ tree … : tjax1a/oa`

`C:\t\jax1a` reached Python as `C:` + a TAB character, so `Path` produced the **relative** `tjax1a` inside the
repository and the non-empty-bundle guard refused to build there. The standing rule is a SHORT ABSOLUTE work path;
the missing half is that on Windows it must be written with **forward slashes** (`C:/t/jax1a`) so no shell layer
can read `\t` as a tab. Rule K reported `determinism not executed` purely as a consequence: with no build there
was nothing to compare.

**And the mangled path did real damage before it was noticed.** Building into `atlas-dashboard/tjax1a/` left **44
files of OTHER markets' data** inside the repository — every live market's document, the global authority manifest,
the shared `hotel_exclusions.json` and `identity_resolutions.json` — and a blanket `git add -A` swept them into
the repairs commit. They were removed and the commit amended before anything was pushed, so the final history
contains **0 non-Jacksonville paths**, proved by `git diff --name-only bf7a54c3 HEAD`. The lesson is not only the
path: **a build directory that lands inside the repository turns the next `git add -A` into a cross-market
change**, and the isolation check has to be run again *after* every commit, not once at the start.
