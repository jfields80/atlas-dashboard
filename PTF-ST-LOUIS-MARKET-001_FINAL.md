# PTF-ST-LOUIS-MARKET-001 — Fresh-Market Benchmark, FINAL

**Market:** `st-louis-mo` (St. Louis, Missouri — bi-state MO/IL)
**Branch:** `feature/ptf-st-louis-market-001`
**Start HEAD:** `cb550e7`
**Status:** censused, closed, packaged for founder review.
**PUBLISHED = FALSE. DEPLOYED = FALSE. NOT REGISTERED. NOT LAUNCH-AUTHORIZED.**

The durable machine-readable form of everything below is
`launch_packages/pettripfinder/st_louis_mo_benchmark_001.json`. Every number in
it is read out of another committed artifact, so any of them can be re-derived.

---

## A. Start state

The production-verified Atlas baseline after PTF-047: five markets live
(Columbus, Cleveland-Akron-Canton, Dayton, Milwaukee, Pittsburgh), 333 profiles,
bundle `a324b1bf5023…`, Netlify deployment `6a8a2dada6e73cb0d819c9d0`.
Indianapolis source-ready and withheld. St. Louis did not exist in any form.

**The environment holds no paid acquisition credential.** `FIRECRAWL_API_KEY`
and `BRIGHTDATA_BROWSER_AUTH` are both unset, so every route in `routes.json`
resolves to a lane that cannot run. `GOOGLE_PLACES_API_KEY` is present. This is
the single most important fact about the acquisition numbers below and it is not
a property of Atlas.

## B. Market geography

Authored, not derived, and written down in full in
`launch_packages/pettripfinder/markets/pending/st-louis-mo.json` (`_boundary_note`).

- **Centre** 38.63, −90.20. **Bounds** 38.35–38.98 N, −90.95–−89.75 W.
- **18 discovery cells**, 70 municipalities, **16 corridors**, **105 postal codes**,
  every ZIP claimed by exactly one corridor.
- **Included:** City of St. Louis; all of St. Louis County; northern Jefferson
  County to Arnold/Imperial; eastern St. Charles County to Wentzville/Foristell;
  the Eureka–Pacific I-44 shoulder; Illinois Metro East (Madison and St. Clair
  counties, plus Columbia in Monroe County).
- **Excluded, each with its reason and its discovered lodging recorded in the
  candidate ledger:** Waterloo IL, Pevely, House Springs, Festus/Crystal City,
  St. Clair MO, New Melle, Wright City, Ste. Genevieve.
- Assignment is **postal-code first** throughout. The mailing city "St. Louis"
  spans thirty ZIPs across four counties and eight traveller areas; a city-first
  assignment puts an airport hotel downtown.

## C. Census — 357 identities

| | |
|---|---|
| Raw discovered candidates | **565** (deduplicated by the shared engine) |
| Admitted to census | **357** |
| Absorbed into another identity | 95 |
| Not lodging in current category | 24 |
| Out of market — geography | 52 |
| Out of market — boundary decision | 1 |
| Identity-key collision, held for review | 8 |
| No locality (no city), held in ledger | 21 |
| Unnamed candidate | 7 |
| **Ledger total** | **565** — sums exactly |

Identity: **357 / 357 IDENTITY_CONFIRMED (100%)**, 0 provisional, 0 unresolved.
Every row carries a city and a state; 6 rows had their state derived from the
corridor that claims their postal code, and the derivation is recorded per row.

Sources: Google Places API (New) Text Search (72 bounded-radius requests) and
OpenStreetMap/Overpass (36 bounded-bbox requests). 63 identities were seen by
both. Recall spot-check found Four Seasons, Chase Park Plaza, The Last Hotel,
Angad Arts, Union Station Curio, Moonrise, Live! by Loews, 21c, Magnolia,
Ritz-Carlton, The Westin and both casino hotels.

`suspected_duplicates_for_review` lists **32 near-duplicate pairs** the strict
absorption rule deliberately will not merge (e.g. "Ritz-Carlton Hotel St. Louis"
vs "The Ritz-Carlton, St. Louis", 3 m apart). Reported, never merged.

## D. Active-eligible population — 357

Derived mechanically from census fields only: IDENTITY_CONFIRMED **and** in
category **and** claimed by a corridor. **357 of 357.** Zero not-active, zero
mystery rows.

## E. Source discovery

| | |
|---|---|
| Official URL present | 297 / 357 (**83.2%**) |
| Property page | 289 |
| Brand redirect (normalised) | 7 |
| Brand index | 1 |
| No URL | 60 |

## F. Routing — 283 / 357 (79.3%)

| State | Count |
|---|---|
| ROUTED | **283** |
| ROUTE_NEEDS_OFFICIAL_URL | 60 |
| ROUTE_BRAND_EXCLUDED (Hyatt 3, Best Western 10) | 13 |
| ROUTE_NEEDS_PROPERTY_URL | 1 |

Brands: Hilton 43, Marriott 40, Wyndham 37, Choice 33, IHG 19, Drury 17,
Motel 6 6, Sonesta 6, ESA 6, Red Roof 4, independents 73.

**Zero provider decisions reopened. Zero new source families.** Every brand St.
Louis exposes was already a measured row in the acquisition registry.

## G. Acquisition — 19 of 138 attempted

The only lane this environment can run is the one this work order built:
`direct_http`, the provider slot the router reserved and never implemented.

| Outcome | Count |
|---|---|
| VALID | **19** |
| IDENTITY_MISMATCH | 35 |
| UNHYDRATED (client-side template) | 38 |
| UNEXPECTED_PAGE | 16 |
| POLICY_NOT_FOUND | 14 |
| ACCESS_DENIED | 9 |
| NAVIGATION_FAILED | 7 |
| **Attempted** | **138** |
| Skipped — brand measured to refuse this lane | 145 |

By brand: ESA 5/6, Sonesta 5/6, independents 7/73, Wyndham 2/37, Drury 0/16.
Marriott, Hilton, IHG and Red Roof return HTTP 403 at the edge; Choice and
Motel 6 do not answer inside 25 s. Those are capability walls, measured at one
probe each, not retry problems.

49 declined captures preserved their document under the existing
`ptf-declined-capture/1.0` contract.

## H. Provider cost — $2.52 of a $10.00 cap

| Provider | Calls | Cost |
|---|---|---|
| Google Places Text Search | 72 | $2.52 (estimated at the $0.035 Enterprise SKU) |
| Overpass / OpenStreetMap | 36 | $0.00 |
| direct_http | 199 fetches over 138 properties (mean 1.44) | $0.00 |
| Firecrawl | **0** | $0.00 |
| Bright Data Browser | **0** | $0.00 |
| Bright Data Web Unlocker | **0** | $0.00 |

No STOP was needed. The binding constraint was credentials, not money.

## I. Reader / fact quality

19 observations, all built **offline** from persisted artifacts — zero network,
zero spend. Blocks were re-parsed from `policy-block.txt` and checked against
`locator.json`'s `block_sha256`; nothing was re-located.

- Publication grade: **17 CONFIRMED, 2 REJECTED**
- Readiness: 11 POLICY_CONFIRMED, 2 CONFIRMED_WITH_AMBIGUITY,
  1 POLICY_NEGATIVE_CONFIRMED, 5 POLICY_NOT_FOUND
- pets_allowed: 15 true, 1 false, 3 unstated
- One record is SCHEMA-representable only as tiers (Sonesta ES Chesterfield:
  $75 up to 7 nights, $150 beyond) and is recommended HOLD.

### Zero-cost recovery (§11)

Run before any repeated acquisition, offline, $0.00, 0 network calls. All 49
preserved declined documents were re-read with every tag stripped — script and
noscript bodies included, which the painted-text walk removes.

- **35** name a different property (routing-repair inputs).
- **14** are as silent read whole as they were read painted — which is what makes
  their `POLICY_NOT_FOUND` disposition falsifiable rather than asserted.
- **0 recoveries.** There was nothing in those documents the walk had missed.

## J. Observation store

`st_louis_mo_observation_store_001.json`. Every row carries source, capture,
locator (contract, walk, strategy, block sha256, document sha256), evidence,
reader provenance, current facts, withheld fields and `review_state:
AWAITING_FOUNDER_REVIEW`. One reader epoch only — a test asserts it.

## K. Closure — 357 / 357 (100%)

| Disposition | Count |
|---|---|
| HELD_REVIEW | **17** |
| ACCESS_UNRESOLVED | 263 |
| INSUFFICIENT_EVIDENCE | 63 |
| POLICY_NOT_FOUND | 14 |
| AUTHORITY_PET_FRIENDLY | **0** |
| AUTHORITY_VERIFIED_NO_PETS | **0** |
| **Total** | **357** |

**Denominator proof:** the ledger refuses to exist unless it reconciles by SET.
`missing=[] foreign=[] duplicate=[]`, active_denominator 357, rows 357.

`POLICY_NOT_FOUND` is said of **14** properties and only of properties whose own
page served its content and was silent — a test enforces it. The 145 never
fetched and the 38 that arrived as unrendered templates are `ACCESS_UNRESOLVED`,
which is a statement about us, not about the hotel.

Partition (`ptf-market-final-partition/1.1`), 357 rows, published 0:
AWAITING_POLICY_OBSERVATION 159, AWAITING_ATTENDED_CAPTURE 89,
AWAITING_OFFICIAL_URL 60, **AWAITING_FOUNDER_DECISION 17**, ACCESS_BLOCKED 16,
AWAITING_ROUTING_REVIEW 13, AWAITING_POLICY_ARTIFACT 2,
AWAITING_PROPERTY_LEVEL_URL 1.

## L. Founder-review candidates — 17 (4.8% of active)

15 recommend pet-friendly, 1 recommend verified-no-pets, 1 recommend hold.
Every row is `MACHINE_REVIEWED_PENDING_OPERATOR` with empty decision fields and
carries its `semantic-approval/1.0` projection and hash.

Live! By Loews · The Ritz-Carlton, St. Louis · The Royal Sonesta Chase Park Plaza ·
Clayton Plaza Hotel · Baymont By Wyndham Bridgeton · Travelodge St. Louis Airport ·
Red Lion Inn & Suites Pontoon Beach · The Landing Hub (no-pets) ·
Sonesta ES Suites Chesterfield (hold) · 5 × Extended Stay America ·
3 × WoodSpring Suites

## M. New architecture

**10 new generic modules. 0 St-Louis-specific scripts.** (Milwaukee, Pittsburgh,
Detroit-Ann-Arbor and Indianapolis needed ~4,600 lines of market-specific
factory code between them.)

`discovery/census_projection.py` · `market_census_cli.py` ·
`acquisition/market_routing.py` · `acquisition/direct_http_capture.py` ·
`acquisition/direct_http_pilot.py` · `acquisition/market_observation_store.py` ·
`acquisition/zero_cost_recovery.py` · `contracts/closure.py` ·
`market_closure_cli.py` · `market_founder_review_cli.py` ·
`market_benchmark_cli.py`

**3 shared files modified, all additive:** the partition blocker state
`AWAITING_FOUNDER_DECISION` (in `contracts/enums.py`), its written meaning
(`contracts/partition.py`) and its next action (`census_partition_builder.py`).

**2 config files:** the discovery geography (resolved by CONVENTION — zero code,
zero registry edits, zero merge conflict with any other market branch) and the
pending market contract.

**6 defects found and fixed**, none caught by an existing gate — full detail in
the benchmark manifest's `architecture.custom_fixes`. The three that would have
been worst:

1. An unqualified brand name is a valid identity key, so deduplicating the
   census by key was about to reduce **25 distinct buildings at 25 distinct
   street addresses to 3**.
2. Wyndham serves `Pet Policy {{pets}}`. Read as POLICY_NOT_FOUND, that asserts
   **26 hotels state nothing about pets**.
3. The first closure run merged "the page said nothing" with "nobody fetched
   it": **198 identities reported POLICY_NOT_FOUND, 146 never fetched**.

## N. Benchmark scorecard

| Metric | Target | Actual | Verdict |
|---|---|---|---|
| Automatic routing | ≥ 90% | **79.3%** | MISS |
| Observed / acquired | ≥ 85% | **13.8%** | MISS |
| Publication-grade of active | ≥ 80% | **4.8%** | MISS |
| Active closure | = 100% | **100.0%** | MET (required) |
| Provider spend | ≤ $10 | **$2.52** | MET |
| Manual / custom architecture | minimal | 10 generic modules, **0 market-specific scripts** | MET |
| Elapsed | 4–8 h | **2.01 h** | UNDER |

The three acquisition misses have one cause: **145 of 283 routed properties were
never fetched because no paid provider credential exists in this environment.**
Over the 138 properties a lane could actually reach, the free lane returned 19
publication-grade candidates for $0.00. The benchmark does not claim what the
paid lanes would have done; it reports that they did not run.

## O. Production safety

Confirmed by `tests/pettripfinder/test_st_louis_production_safety_001.py`
(14 tests, all pass):

- The five live markets are still the only founder-authorized set; Indianapolis
  is still SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED.
- `launch_participation.json` still hashes to what the manifest pins.
- `global_deployment.verify_manifest` returns `[]`.
- `ptf-deploy-047-…` and `ptf-auth-047-…` are byte-untouched.
- Measurement disabled, config hash unchanged. Zero affiliates enrolled.
- No St. Louis route, release contract, authority shard or registry entry exists.

**The registration finding.** Creating `markets/st-louis-mo.json` registers the
market; a registered market with no `launch_participation.json` row fails the
global assembler gate; adding the row changes that file's sha256; that sha256 is
pinned by the deployment manifest AND copied into the founder's signed
authorization. So registering a market **invalidates the current production
deployment record**. The St. Louis contract is therefore a valid, parseable,
deliberately unregistered document in `markets/pending/`. Moving it one
directory up is the whole of the registration change, and it is a founder step
taken at the same moment the participation row is written.

## P. St. Louis status

```
ST. LOUIS CENSUS COMPLETE          = YES  (357 identities, ledger sums to 565)
ST. LOUIS ACTIVE CLOSURE COMPLETE  = YES  (357/357, reconciled by set)
ST. LOUIS FOUNDER REVIEW READY     = YES  (17 candidates)
ST. LOUIS PUBLISHED                = FALSE
ST. LOUIS DEPLOYED                 = FALSE
ST. LOUIS REGISTERED               = FALSE
ST. LOUIS LAUNCH PARTICIPATION     = UNLISTED (fail-closed; never authorized)
```

## Q. Next recommendation

**Founder review of the 17 candidates is available but is not the highest-value
next action.** The market cannot reach five published hotels' worth of coverage
from 17 candidates concentrated in three brands.

Recommended order:

1. **Restore a paid provider credential** and re-run the routed population.
   145 of 283 routed properties — every Marriott, Hilton, IHG, Choice, Motel 6
   and Red Roof — have never been fetched. This is the only change that moves
   the acquisition number.
2. **A bounded source-discovery pass** over the 60 identities with no official
   URL, using the existing `acquisition/source_discovery.py`.
3. **Census correction**: settle the 32 suspected duplicate pairs, the 8 held
   identity-key collisions and the 21 no-locality rows.
4. **Founder review** last, once the candidate set is worth one sitting.
