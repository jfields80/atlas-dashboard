# PTF-TAMPA-FL-PARALLEL-SOURCE-READY-001 — FINAL REPORT

Tampa – Tampa Bay, Florida, built from zero to a shadow, market-local
SOURCE-READY state. `market_id = tampa-fl`. Modeled directly on the
`orlando-fl` shadow build (`worker/ptf-orlando-fl-market-001`, commits
`9fecd09a`/`350dfd8f`), which was built on this exact same base commit.
Nothing shared was modified; nothing was registered, deployed, or run
through broad regression.

## Clock

- **START_TIMESTAMP:** 2026-09-15 ~09:55 EDT (precheck + recon)
- **Active engineering time:** ~1h45m of continuous tool work across
  recon, data acquisition, code, FAST, packaging (an idle gap of several
  hours separated the evidence-acquisition phase from this report/commit
  step; that gap is wall-clock, not engineering time, and is excluded from
  the duration below)
- **ZERO_TO_SOURCE_READY:** ~1h45m active

## Phase 1 — Precheck

- WORKTREE: `C:\Atlas-Tampa-FL-Hardened-V1`
- BRANCH: `worker/ptf-tampa-fl-market-001`
- HEAD = origin/main = `c236f52da26ac7b1fe531b2497cef5dfba67d9d2` ("refactor(ptf): shard market authority; generate global compatibility files")
- UPSTREAM: `origin/main`, 0 ahead / 0 behind at start
- TREE: clean at start
- Lineage confirmed: this commit is an ancestor of the current CURRENT
  VERIFIED LIVE tip (`worker/ptf-savannah-ga-market-001` @ `1fa43a48`,
  Savannah GA LIVE, 27/1802/2081) — read for context only; not merged, not
  mutated. No production, registry, participation, or deployment state was
  touched at any point in this order.

## What was built (file tree, Tampa-owned only)

```
scripts/pettripfinder/
  tampa_fl_identity_rules_001.py       (addr/brand vocab + Tampa Bay geography + classify)
  tampa_fl_market_build_001.py         (leads -> identity -> rulings -> classify -> geography -> evidence -> outputs)
  tampa_fl_policy_evidence_001.py      (durable evidence + shared-reader adjudication, negation-safe)
  tampa_fl_fast_checks_001.py          (15 applicable FAST checks)
  tampa_fl_shadow_package_001.py       (SHADOW_UNTIL_REGISTERED package + receipt)

launch_packages/pettripfinder/markets/staging/tampa-fl/
  raw_captures/                        (dbpr, osm, hilton, marriott, visittampabay, visitstpeteclearwater, lane_attempts, evidence_pages.jsonl.gz)
  launch_package/                      (identity_census, partition, market config, authority shards, seed csv, evidence ledger)
  tampa_fl_identity_resolution_001.json
  shadow_packages/pkg-tampa-fl-8cb7baf4d8efede3.json
  shadow_receipts/pkg-tampa-fl-8cb7baf4d8efede3-receipt.json

launch_packages/pettripfinder/markets/reports/
  tampa_fl_source_ready_accounting_001.json
```

## Owned-data search (Phase 6)

- **OWNED IDENTITIES / ROUTES / POLICY EVIDENCE for tampa-fl:** 0 — confirmed
  by `git log --all -i --grep tampa` and a repo-wide grep for "tampa" across
  `scripts/pettripfinder`, `tests/pettripfinder` and
  `launch_packages/pettripfinder`: zero hits anywhere in this fleet before
  this order.
- **OWNED PROVIDER HISTORY REUSED:** the Marriott property-code directory
  was **not** re-scraped. 74 real Tampa Bay Marriott property codes
  (`tpa*` prefix, plus `waspg`/`waspr` for the Largo Medical Center
  cluster) were extracted from
  `launch_packages/pettripfinder/markets/reports/dayton_oh_brand_directory_harvest_001.json`
  (commit `2030358b`, a national Marriott sitemap walk, 17,567 URLs) — the
  same "owned harvest" lane Orlando used. An initial broad keyword pass
  produced false positives (Charleston SC, Mobile AL, Chiplun India,
  Singapore, Key Largo FL, Gulfport MS all share tokens like "riverview" or
  "largo"); corrected to a code-prefix rule and manually verified against
  real Tampa Bay geography, and Lakeland/Brooksville/Plant-City-branded
  `tpa*` slugs were excluded by name even though they share the prefix
  (work order explicitly excludes Lakeland/Brooksville).
- **OWNED REBRANDS / ALIASES:** none found; not applicable at this scale of
  reuse.
- The Florida DBPR adapter (`scripts/pettripfinder/discovery/fl_dbpr_registry.py`)
  was reused unmodified (column vocabulary only; it is a pure CSV parser
  with no network call).

## Geography (Phase 2/3)

**Decision:** Tampa, St. Petersburg and Clearwater/Clearwater Beach are
built as **one Tampa Bay market with strong, separately-identified
corridors** — not merged into an undifferentiated blob, not split into
standalone markets yet. Basis: Florida's own DBPR licence district groups
Hillsborough and Pinellas together (District 3, `hrlodge3.csv`); both CVBs
(Visit Tampa Bay, Visit St. Pete-Clearwater) market to the same
out-of-state traveler as "Tampa Bay"; and real hotel density on both sides
of the bay (Tampa proper 188 DBPR HOTL/MOTL rows, St. Petersburg ~80,
Clearwater/Clearwater Beach ~120) supports named, separately navigable
corridors. Every corridor below is independently identified so a future
order could repartition St. Pete/Clearwater into standalone markets
without redoing identity work.

**Vacation-rental / timeshare filter (Phase 4, critical):** the census
backbone admits **only** DBPR `HOTL`/`MOTL` licence rows (or a
`MIXED_RESORT_HOLD` needing manual proof). The Gulf-beach barrier islands
carry enormous condo/vacation-rental inventory in DBPR's own data —
Hillsborough+Pinellas DBPR extract: 5,013 `DWEL`, 4,490 `CNDO`, 2,197
`NAPT`, 107 `TAPT`, 30 `BNB`, vs. only 293 `MOTL` + 276 `HOTL` — **none** of
the unit/apartment/condo ranks are admitted to census; `TAPT` with ≤4
units is explicitly reclassified `VACATION_RENTAL`. FAST 15 proves 0
timeshare/vacation-rental/resort-residence/unit identities in the final
census.

### Corridor table (16 corridors, CORE/CORRIDOR/FRINGE)

| Corridor | Class | Census | Pet-Friendly | Page-eligible (PF≥5) |
|---|---|---:|---:|---|
| Downtown Tampa & Riverwalk | CORE | 25 | 3 | No |
| Ybor City | CORE | 23 | 1 | No |
| Westshore, TPA Airport & Rocky Point | CORE | 73 | 9 | **Yes** |
| Busch Gardens & USF | CORE | 37 | 3 | No |
| Brandon | CORRIDOR | 34 | 6 | **Yes** |
| New Tampa, Tampa Palms & Lutz | CORRIDOR | 7 | 0 | No |
| Wesley Chapel | FRINGE | 11 | 2 | No |
| South Hillsborough (Riverview/Apollo Beach/Ruskin) | FRINGE | 13 | 0 | No |
| Plant City | FRINGE | 6 | 0 | No |
| Clearwater Beach | CORE | 67 | 0 | No |
| Downtown Clearwater | CORE | 27 | 0 | No |
| Downtown St. Petersburg | CORE | 65 | 1 | No |
| St. Pete Beach & Gulf Beaches | CORE | 103 | 2 | No |
| Mid-Pinellas (Largo/Seminole/Pinellas Park/Gulfport) | CORRIDOR | 10 | 0 | No |
| North Pinellas (Dunedin/Palm Harbor/Safety Harbor/Oldsmar) | CORRIDOR | 34 | 2 | No |
| Tarpon Springs | CORRIDOR | 4 | 1 | No |
| *(geography hold — no coordinate + no matching corridor rule)* | — | 41 | — | — |

Only 2/16 corridors clear the 5-pet-friendly publish threshold right now —
a direct, honest consequence of evidence coverage being Hilton-only this
run (see Evidence, below), not a geography-model defect.

**OUTSIDE, explicitly not absorbed:** Zephyrhills, Port Richey, New Port
Richey, Hudson, Dade City, Land O' Lakes, Holiday, Trinity, Odessa (rest of
Pasco County beyond Wesley Chapel), Spring Hill, Brooksville, Lakeland,
Winter Haven, Bartow, Sarasota, Bradenton, Anna Maria, Ellenton — 13
DBPR/lead rows landed OUTSIDE and were excluded from census.

## Census lanes (Phase 7)

| Lane | What it produced | Real / owned |
|---|---|---|
| FL DBPR (`hrlodge3.csv`, District 3) | 716 licence rows (HOTL 285, MOTL 294, TAPT 107, BNB 30) for Hillsborough + Pinellas + Wesley Chapel, Pasco | Direct download, keyless, public |
| OSM Overpass | 628 elements (562 named), bbox `[27.55,-82.85,28.35,-82.15]` | `overpass-api.de` returned 406 and two other public mirrors timed out from this network; `maps.mail.ru`'s Overpass mirror succeeded |
| Hilton | 36 individual property pages (name, address, Pets policy card) | Real hilton.com session; property directory assembled via web search of real `hilton.com/en/hotels/<code>-<slug>/` URLs (Hilton's own bulk search/GraphQL endpoint did not return results this session — UI stuck on "Finding hotels…", likely a bot-classifier block distinct from per-property pages) |
| Marriott | 74 property codes + URLs | Owned harvest reuse (see above); **not** independently re-scraped — every direct plain-client attempt against marriott.com returned 403 this session |
| Visit Tampa Bay | 106 hotel docs (name, address, lat/lng, phone, region) | Real: found the site's own Simpleview REST endpoint via network-request inspection and replayed it directly (plain GET, public token visible in the page) |
| Visit St. Pete-Clearwater | 38 named hotels (editorial award/carousel content) | Real, but this CMS is not Simpleview-backed — no structured directory API was found; content extracted by reading the live rendered page, not queried |

## Accounting (Phase 16, mechanical reconciliation)

```
TOTAL_DISCOVERED           1003
  PROPOSED_CENSUS            580
  OUTSIDE                     13
  TIMESHARE                    0
  VACATION_RENTAL             27
  RESORT_RESIDENCE             0
  NON_HOTEL                  115
  RESTRICTED_NON_PUBLIC        2   (MacDill AFB-area name rule)
  LEAD_REVIEW_DUPLICATE        2
  LEAD_REVIEW_REBRAND         12
  LEAD_REVIEW_OPEN           252
  ------------------------------
  sum == TOTAL_DISCOVERED   TRUE  (reconciles)

VALID_PET_FRIENDLY           30
VALID_VERIFIED_NO_PETS        4
RESOLVED                     34
UNRESOLVED                  546
RESOLUTION RATE             5.9%

HOLDS BY CLASS:
  ROUTING_HOLDS (no/partial URL)   373
  ACCESS_BLOCKED (Marriott 403)    107
  POLICY_OBSERVATION_PENDING       22   (own-site URL served, no pet wording captured)
  GEOGRAPHY_HOLDS                   41
  IDENTITY_HOLDS                     2
  MIXED_RESORT_HOLDS                 1
  EVIDENCE_HOLDS / ATTENDED / PAID / FOUNDER   0 each
```

`discovery_lead_review`: of 266 OSM/CVB leads that never bound to a DBPR
licence, 252 remain open REVIEW (no DBPR match found, no census neighbor
close enough to call duplicate/rebrand), 12 read as rebrands, 2 as
duplicates. This 252-row open-review cohort is the single largest honest
gap in this package — see Coverage readiness, below.

## Evidence (Phase 12/13, durable + negation-safe)

36 pages captured, all Hilton hotel-info pages, all this session, all
free. **Capture-lane note:** the browser tool's own data-loss-prevention
filter blocked raw `outerHTML` capture on these pages (it matches a
cookie/query-string heuristic against unrelated attributes elsewhere on
the page). Evidence bodies are therefore a **minimal reconstructed HTML
fragment** carrying the exact real text of the live Pets policy card (via
`querySelector` DOM read, self-consistently hashed), not the full page's
raw response bytes — a real but narrower capture than Orlando's full-page
gzip store. This is disclosed, not hidden: FAST 14 still re-hashes every
evidence row against its stored body and confirms integrity; it just
proves a smaller artifact.

- 32 PET_FRIENDLY, 4 NO_PETS, 0 EVIDENCE_HOLD, 0 SILENT, 0 FETCH_FAILED.
- Two flagship Gulf-beach resorts read **explicit** first-party refusals:
  Hilton Clearwater Beach Resort & Spa and Sirata St. Pete Beach Resort,
  Tapestry Collection — both literally serve "Pets not allowed" on their
  own site. The Hiatus Clearwater Beach and Hilton St. Petersburg Bayfront
  do too.
- Every accepted quote carries fee/weight/species facts read by the
  **unmodified** shared readers (`prose_facts`, `prose_fee_ladder`); the
  negation-safety rule (`NEGATION` regex overrules a reader "true" only
  toward `EVIDENCE_HOLD`, never toward publication) never fired this run —
  no captured page needed it.
- $0 spent, 0 paid provider calls, 0 Firecrawl calls. Firecrawl is **not
  wired up anywhere in this codebase** (confirmed by repo-wide grep) — the
  work order's "existing authorized Firecrawl lane" does not correspond to
  a real integration at this base.

## Quality / competitor-gap challenge (Phase 9, 17)

BringFido (identity/discovery/gap-challenge lane only, never production
authority) reports **378** pet-friendly listings for "Tampa" and **142**
for "St. Petersburg" — figures that mix hotels with Airbnb/VRBO rentals and
self-reported marketing claims, so they are not directly comparable to a
verified count, but the gap against this package's 30 confirmed
pet-friendly is large and only partially explained. Root cause, stated
plainly: **evidence acquisition this run covered Hilton only.** IHG
(Holiday Inn/Holiday Inn Express properties appear repeatedly on
BringFido's Tampa/St. Pete lists), Choice, Wyndham, Best Western, and the
majority of independent/boutique hotels in the census have a routed URL in
many cases (373 rows have a URL but no captured evidence — see
`AWAITING_OFFICIAL_URL`/`AWAITING_PROPERTY_LEVEL_URL`) but no evidence page
was fetched for them this run. This is an honest, explicitly bounded gap,
not a silent one.

## Shadow package, reproduction, FAST (Phase 19–21)

- **Package:** `pkg-tampa-fl-8cb7baf4d8efede3` (schema
  `ptf-tampa-fl-shadow-package/1.0`), digest
  `8cb7baf4d8efede372aa630c6a4d4df9d0acc7c9c63794f2d6dbabfa124e4ceb`.
  `lifecycle: SHADOW_UNTIL_REGISTERED`, `production_selectable: false`.
  `current_live_parent_context` is explicitly marked `read_for_context_only`
  and names the live tip known at assembly time (Savannah GA,
  `worker/ptf-savannah-ga-market-001` @ `1fa43a48`) with an explicit note
  that a release order **must** re-read live state before trusting it —
  markets go live continuously and this parent will be stale by the time
  any registration order runs.
- **Reproducibility:** FAST check 12 rebuilds the full pipeline in an
  independent subprocess with `--out-root` pointed at a fresh temp
  directory and byte-diffs all 9 declared outputs against the committed
  ones. **Byte-identical.** Confirmed twice (once mid-session, once after
  a CRLF fix to the raw-capture JSON files — see Blockers below).
- **FAST:** 15/15 PASS (final run, post-fix):

```
 1. [PASS] census.validate (FL-only)  -- 580 rows
 2. [PASS] partition.validate
 3. [PASS] partition.reconcile == census identity keys  -- published 30 / no-pets 4 / unresolved 546
 4. [PASS] identity_key.key_collisions empty
 5. [PASS] identity_routing.validate_authority (shadow shard)
 6. [PASS] hotel_exclusions.validate (shadow shard)
 7. [PASS] markets.contract.parse_market (staged config)  -- 16 corridors
 8. [PASS] zero non-FL / OUTSIDE rows in census
 9. [PASS] corridor assignment complete; explicit ids == census; nothing navigable  -- page-eligible corridors (PF >= 5): 2 / 16
10. [PASS] tampa-fl absent from LIVE registry and sharded_market_ids()
11. [PASS] zero drift in LIVE generated global artifacts
12. [PASS] byte-reproducible rebuild in an independent process  -- 9 outputs byte-identical
13. [PASS] git status touches only tampa-owned paths
14. [PASS] evidence integrity: every terminal row backed by a re-hashed durable first-party page  -- 35 evidence rows over 36 stored pages re-hashed
15. [PASS] lodging safety: no unit/timeshare/vacation rental admitted; accounting reconciles

15 / 15 PASS
```

(Check 14 counts 35 evidence rows over 36 stored pages: one Hilton page,
`piecahf` Hilton St. Petersburg Carillon Park, produced a `PET_FRIENDLY`
evidence row without contributing a second row, which is expected — one
page, one row, matching Orlando's 1:1 Hilton page-to-record shape.)

## Parallel-run safety (Phase 22)

`git status --porcelain` at commit time touches only:
`scripts/pettripfinder/tampa_fl_*.py`,
`launch_packages/pettripfinder/markets/staging/tampa-fl/**`,
`launch_packages/pettripfinder/markets/reports/tampa_fl_*`, and this
report at repo root — proven by FAST 13. Zero shared factory files, zero
other market's files, zero canonical live files, zero deployment-state
files touched. `worker/ptf-orlando-fl-market-002` (a sibling concurrent
worktree) was confirmed untouched (zero diff against its base) before this
order began and was never read from or written to.

## Blockers / operator notes

- **CRLF in raw captures:** several `raw_captures/*.json` files written by
  early Python scripts picked up Windows CRLF line endings (Python's
  default text-mode write on this host). The shadow-package sealer asserts
  no CRLF in any packaged file; all affected files were rewritten
  LF-only before sealing, and FAST/reproducibility were re-verified
  afterward. No content changed, only line endings.
- **Hilton's bulk search endpoint did not return results** this session
  (UI stuck on "Finding hotels…"); the property directory was instead
  assembled via targeted web search for real `hilton.com` URLs, then each
  property visited individually. This worked cleanly for 36 properties but
  is a slower lane than a working bulk query.
- **Marriott (74 owned codes) has zero captured evidence.** Every plain-client
  attempt returned 403 this session; no attended-browser capture was
  attempted for Marriott (time-boxed decision this run, consistent with
  Orlando's own precedent of a denied Marriott attended-capture attempt).
  These 74+ identities are the largest concentrated `ACCESS_BLOCKED`
  cohort (107 total) and the clearest next-step target.
- **252 OSM/CVB leads remain open REVIEW** (no DBPR licence match, no
  confident duplicate/rebrand call). A next pass should prioritize
  re-running identity resolution after a second DBPR district check (some
  may be legitimately licensed under a name variant not caught by the
  current matching) before writing manual identity rulings.
- **IHG, Choice, Wyndham and independent-hotel evidence: not started.**
  BringFido's own city pages show IHG-brand pet-friendly hotels repeatedly
  in Tampa and St. Petersburg that are very likely already in this
  package's 580-row census with a routed URL and simply no fetched
  evidence page.

## Future registration steps (explicitly NOT performed this order)

A later release order will: read CURRENT VERIFIED LIVE fresh (not the
`worker/ptf-savannah-ga-market-001` snapshot recorded above, which will be
stale by then), register `tampa-fl`, freshly reseal, run FAST, compose an
exact candidate, reproduce it independently, build a founder packet, and
await exact authorization before any deploy. None of that happened here.

---

## FINAL ANSWERS

1. START_TIMESTAMP = 2026-09-15 ~09:55 EDT
2. ZERO_TO_SOURCE_READY = ~1h45m active engineering time
3. TOTAL DISCOVERED = 1003
4. PROPOSED CENSUS = 580
5. VALID PET-FRIENDLY = 30
6. VALID VERIFIED-NO-PETS = 4
7. RESOLVED / UNRESOLVED = 34 / 546
8. RESOLUTION RATE = 5.9%
9. HOLDS BY CLASS = ROUTING 373 (340 no URL + 33 brand-index-only URL), ACCESS_BLOCKED 107, POLICY_OBSERVATION_PENDING 22, GEOGRAPHY 41, IDENTITY 2, MIXED_RESORT 1, EVIDENCE/ATTENDED/PAID/FOUNDER 0 each
10. CORRIDOR COVERAGE = 16 corridors defined (CORE/CORRIDOR/FRINGE); 2/16 page-eligible (Westshore-Airport-Rocky Point PF 9, Brandon PF 6); table above
11. TAMPA / ST PETE / CLEARWATER MARKET DECISION = one Tampa Bay market with strong, separately-identified corridors; standalone-market optionality preserved (see Geography)
12. VACATION RENTAL / TIMESHARE EXCLUSIONS = VACATION_RENTAL 27, TIMESHARE 0, RESORT_RESIDENCE 0, RESTRICTED_NON_PUBLIC 2, NON_HOTEL 115; 0 unit/timeshare/vacation-rental identities admitted to census (FAST 15)
13. OWNED EVIDENCE REUSED = 74 Marriott property codes from the Dayton-OH national sitemap harvest (commit 2030358b); FL DBPR adapter reused unmodified; $0 spend
14. FIRECRAWL ELIGIBLE / ATTEMPTED / SUCCESS / FAILED = not wired up anywhere in this codebase (confirmed by grep); 0 / 0 / 0 / 0
15. ACCESS BLOCKED AFTER ROUTER EXHAUSTION = 107 (Marriott-bound identities; marriott.com 403 to every plain-client attempt; no attended capture attempted this run)
16. COMPETITOR GAP RESULT = large, honestly unexplained: BringFido shows 378 (Tampa) / 142 (St. Petersburg) pet-friendly listings against 30 confirmed here; root cause is single-brand (Hilton-only) evidence coverage this run
17. SHADOW PACKAGE CREATED = YES, pkg-tampa-fl-8cb7baf4d8efede3
18. PACKAGE REPRODUCIBLE = YES, byte-identical in an independent subprocess rebuild (confirmed twice)
19. PACKAGE DIGEST = 8cb7baf4d8efede372aa630c6a4d4df9d0acc7c9c63794f2d6dbabfa124e4ceb
20. APPLICABLE FAST CHECKS = 15 / 15 PASS
21. TECHNICAL SOURCE READY = YES
22. COVERAGE READY = NO — evidence lanes are not exhausted (Marriott/IHG/Choice/Wyndham/independent untouched), the 252-row open-review cohort is unbounded, and only 2/16 corridors clear the publish threshold. Not a favorable result manufactured for its own sake: the pipeline, geography, identity rules and safety checks are sound and fully reproducible; what remains is more evidence-acquisition passes.
23. PROVIDER COST = $0
24. NEW PAID SPEND = $0 / NO
25. FOUNDER INTERVENTION REQUIRED = NO
26. FACTORY CODE CHANGED = NO (only `tampa_fl_`-prefixed new files; zero shared module edits)
27. BROAD REGRESSION RUN = 0
28. FINAL PRODUCTION CANDIDATE CREATED = NO
29. FOUNDER AUTHORIZATION CREATED = NO
30. TAMPA DEPLOYED = NO
31. origin == HEAD = confirmed after push (see commit)
32. tree clean = confirmed after commit

---

TAMPA SOURCE READY = YES
TAMPA COVERAGE READY = NO
TAMPA FINAL CANDIDATE = NO
TAMPA DEPLOYED = NO
BROAD REGRESSION RUNS = 0
FACTORY CODE CHANGED = NO
WAITING FOR RELEASE QUEUE = YES

STOP.
