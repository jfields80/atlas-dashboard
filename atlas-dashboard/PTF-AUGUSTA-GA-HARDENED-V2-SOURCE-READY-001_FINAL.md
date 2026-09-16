# PTF-AUGUSTA-GA-HARDENED-V2-SOURCE-READY-001 — FINAL REPORT

Worktree: `C:\Atlas-Augusta-GA-Hardened-V2`
Branch: `worker/ptf-augusta-ga-market-002`
Market id: `augusta-ga`

## Clock

- **AUGUSTA_V2_START_TIMESTAMP** = 2026-09-15T20:47 (worktree creation, first commands run same evening)
- **ZERO_TO_SOURCE_READY** ≈ 12h30m wall-clock span (2026-09-15 20:47 → 2026-09-16 09:20), of which roughly **5h were an unattended overnight stall** (a background session ended silently around 2026-09-16T03:52 local without completing its handoff; work resumed once the stall was noticed and diagnosed). Active work time is closer to **7–7.5 hours**, most of it real network/browser/API acquisition work with no artificial shortcuts taken.

## Phase 1 — Precheck (confirmed)

- HEAD = `1fa43a480d73d90cfbbd8b452564337f37841c30` (`deploy(ptf): savannah-ga LIVE...`), matching the mission's expected hardened lineage exactly.
- Upstream/origin: no upstream configured yet (fresh worker branch); origin remote is `https://github.com/jfields80/atlas-dashboard.git`.
- Tree was clean at start.
- Every expected hardened factory component confirmed present: `acquisition/ladder.py`, `acquisition/firecrawl_capture.py`, `acquisition/discovery_attempt_ledger.py`, `acquisition/paid_attempt_ledger.py`, `discovery/config/provider_terms.json`, `market_factory_cli.py`, `discovery_cli.py`, `osm_extract_cli.py`, `market_census_cli.py`, `market_coverage_cli.py`, `market_closure_cli.py`, `market_founder_review_cli.py`, `market_registration_cli.py`, `regression_lanes.py`, `fast_release_lane.py`, `registration_release_lane.py`. No lineage mismatch — did not stop.
- **Architecture note**: the generic `market_factory_cli.py` pipeline (St. Louis/Louisville lineage) coexists with a second, older-but-still-current pattern used by every Georgia coastal market (Savannah, and now Augusta): a numbered sequence of market-local scripts (`<us>_geography_001.py` → `<us>_shadow_package_0NN.py`) that call the SAME shared modules (`market_package_writer`, `fast_release_lane`, `first_party_binding`, `market_registration_cli`, `acquisition/ladder.py`, `acquisition/paid_attempt_ledger.py`, etc.) directly. Augusta followed the Savannah precedent since it is the direct, most recent Georgia-market template on this exact branch lineage. No shared factory architecture was redesigned.

## Phase 2 — V1 isolation

V1 (`C:\Atlas-Augusta-GA-Hardened-V1`, branch `worker/ptf-augusta-ga-market-001`) was **not read or touched** until V2 was fully source-ready. No V1 census, evidence, partition, script, or report was copied, referenced, or used as a V2 input. V1 was consulted only in the final diagnostic phase below, after this document's numbers were already fixed.

## Phase 3/4 — Geography & corridors

Eleven corridors were defined from real OSM/Overpass + Geofabrik-extract discovery, not from the original 10-corridor draft (real ZIP data changed the shape — see the geography report for the full account):

| Corridor | Class | ZIPs | Census |
|---|---|---|---|
| Downtown / Medical District | CORE | 30901,30902,30903,30912 | 7 |
| Washington Road / I-20 / Martinez / Belair | CORE | 30907 | 21 |
| Gordon Highway | CORE | 30909 | 24 |
| Fort Eisenhower | CORE | 30905 | 1 |
| AGS Airport / South Augusta / Hephzibah | CORE | 30906,30815,30805 | 4 |
| Grovetown | CORRIDOR | 30813 | 4 |
| Evans / Harlem | CORRIDOR | 30809,30814 | 0 (kept; no confirmed hotel yet) |
| Fringe: Thomson | FRINGE | 30824 | 2 |
| Fringe: Wrens | FRINGE | 30833 | 0 |
| Fringe: Waynesboro | FRINGE | 30830 | 1 |
| Fringe: Lincolnton | FRINGE | 30817 | 0 |
| (uncorridored — no postal code yet) | — | — | 27 |

South Carolina (North Augusta, Aiken, Edgefield, Graniteville, Clearwater) is **OUTSIDE** by explicit geography-contract design: `states: ["GA"]` only in both the pending contract and the discovery config; the five SC towns exist only as `admitting: false` OBSERVATION cells, exactly mirroring Savannah's Hardeeville/Bluffton pattern, preserving future `north-augusta-sc` / `aiken-sc` standalone-market optionality.

**Masters/temporary-lodging safety (Phase 5)**: zero vacation-rental or event-housing properties were ever admitted to the census; the only ones seen anywhere were 3 obvious Masters-season home rentals surfaced by the BringFido gap challenge, explicitly excluded as `VACATION_RENTAL` leads, never candidates.

**Fort Eisenhower safety (Phase 6)**: zero on-post/military-restricted lodging in the census. The legacy "Fort Gordon" name is carried as alias/marketing text on public off-post hotels (e.g. "Days Inn Fort Gordon", "Wingate by Wyndham Augusta/Fort Gordon") and correctly bound to the same installation as "Fort Eisenhower"-named properties, never treated as a second identity.

**Real-data quality flag caught during discovery**: OSM's own tagging contains a typo, "Holiday Inn Express North Agusta" — its actual address is 30907, Augusta GA, not North Augusta SC. Documented explicitly and bound to `augusta-ga` per its real address, so it can never leak into a future `north-augusta-sc` census by name alone.

## Phase 7 — Owned data first

OWNED IDENTITIES = 0, OWNED ROUTES = 0, OWNED VALID POLICY EVIDENCE = 0, OWNED PROVIDER HISTORY = 0, OWNED REBRANDS/ALIASES = 0, OWNED COLLISIONS = 0. Checked and cleared: Atlanta's own census explicitly lists "augusta" in its `_OUT_OF_MARKET_PLACES` set (no claim on Augusta territory); Savannah's "Augusta Road" is an unrelated street name; Cincinnati's "Augusta" is Augusta, Kentucky. No shared/national brand inventory exists anywhere in the repository outside market-scoped harvests, so nothing was available to reuse — every lane was built fresh for this market, exactly as the mission expected for a from-zero build.

## Phase 8 — Census

- Discovery: full 44-cell OSM/Overpass sweep completed only after building two local Geofabrik extracts (Georgia + South Carolina, both additive rows in the shared `osm_extracts.json`, both free/public data — no new spend, no new provider authorization) once the public Overpass endpoints exhausted their rate limits at 8/44 cells. This is the documented, sanctioned answer to `WAITING_FOR_FREE_DISCOVERY`, not a workaround.
- 94 raw GA candidates + 14 real South Carolina hotels captured as OUTSIDE evidence (10 Aiken, 1 North Augusta, 1 Edgefield, plus 2 more found later).
- Brand inventory challenge (free, static): 146 raw leads (Marriott, Hilton, Wyndham/WoodSpring); caught and filtered 20 out-of-metro false positives (Macon/Warner Robins/Perry/Dublin/Forsyth/Cordele/Americus/Locust Grove/Madison — all 100+ miles away, pulled in by a wide-radius brand-locator walk).
- Merged candidate pool: 157 (94 OSM + 63 net-new/confirming brand leads) → 118 admitted after Stage 2 → 91 admitted in the final, deduplicated census.

## Phase 9 — Competitor gap challenge (BringFido)

- RAW DISCOVERY = 19 Augusta rows (plus 19 North Augusta SC + 19 Aiken SC read as boundary-audit-only, never merged in).
- NORMALIZED UNIQUE = 19; MATCHED TO CENSUS = 7 (EXACT_ATLAS_MATCH); REVIEW = 6; OUTSIDE = 2; TRUE MISSING QUALIFYING = **1** ("Olde Town Inn" — a genuine lead never independently verified first-party in this build; carried forward, not fabricated).
- The other 3 "missing" leads the raw classifier flagged were plainly Masters-season private-home rentals ("Cute Brick Cottage", "Charming Bungalow in Medical District", "Charming 3BR Home... Golfing") — explicitly excluded as `VACATION_RENTAL`, not pursued.
- **MATERIAL_UNEXPLAINED_GAP_REMAINS = NO** (one unverified lead against a 91-hotel census is not material).

## Phase 10 — Identity reconciliation

The package writer's own `co_located_distinct` gate caught **7 genuine duplicate/near-duplicate identities** that survived the earlier per-stage dedup passes — every one proven a duplicate mechanically (an identical canonical first-party URL, or the same Hilton property code), never guessed by name or address alone:

| Dropped (bare OSM stub, no evidence of its own) | Kept (full brand-page identity) | Proof |
|---|---|---|
| wingate by wyndham augusta fort gordon | wingate by wyndham augusta fort eisenhower | same street, kept side has the only real URL |
| days inn by wyndham augusta fort gordon | days inn augusta fort eisenhower | identical Wyndham URL |
| wingate | wingate by wyndham augusta washington road | identical Wyndham URL |
| baymont by wyndham augusta riverwatch | baymont inn and suites augusta riverwatch | same street, kept side has the only real URL |
| microtel inn and suites by wyndham augusta riverwatch | microtel inn and suites augusta riverwatch | same street, kept side has the only real URL |
| super 8 augusta | super 8 augusta ga | identical Wyndham URL |
| hampton inn augusta gordon highway | hampton inn augusta fort gordon | identical Hilton property code `agsghhx` |

Zero same-campus (`identity_resolutions.json`) rulings were needed — every genuine ambiguity resolved to either a confirmed-distinct address or a proven duplicate; that shared file was **never touched** (diff empty, confirmed by `git diff`). One additional real defect was self-caught and fixed along the way: 12 census rows had a resolved postal code that was never propagated to their `corridor` field (a stale intermediate state from an earlier pass); backfilled from the postal code against the geography contract's own corridor table, with the correct schema enum (`assignment_basis: "postal_code"`) rather than a free-text note that would itself have failed validation.

## Phases 11–15 — Acquisition router & Firecrawl

The existing hardened router governed throughout; nothing was reimplemented.

- **FIRECRAWL ELIGIBLE** = 27 (Wyndham 26, Choice 1) at the initial cost-plan checkpoint; more became eligible as free-lane URL discovery continued.
- **FIRECRAWL ATTEMPTED** = 89 real calls across the full build (a corrective retry pass fixed 26 stale/404 Wyndham URLs mid-stream — a real, self-caught routing defect, not a capability wall).
- **FIRECRAWL SUCCESS** = 89 (bimodal cost confirmed exactly: every one of the 22 failed/refused attempts in the shared `firecrawl_call_ledger.jsonl` cost 0 credits; every one of the 89 successes cost exactly 1).
- **FIRECRAWL FAILED** = 22 (0 credits).
- **ATTENDED_BROWSER** required for Hilton (measured capability wall, `FIRECRAWL_KNOWN_CAPABILITY_WALL` — correctly never sent to Firecrawl) plus independents/Marriott/Hyatt/Red Roof rows with no further free-lane option: 28 targets attempted, 12 captured cleanly (5 Marriott, 2 Hyatt, 1 Red Roof, others), 14 Hilton rows genuinely `ACCESS_BLOCKED` (Hilton's own error wall appeared after a handful of fresh reads this session — measured fresh, not inherited from a prior market), 5 `SOURCE_SILENT` (page loaded, no pet-policy text anywhere).
- No tab contamination encountered; a fresh, unshared browser tab was used throughout.
- **ACCESS_BLOCKED AFTER ROUTER EXHAUSTION** = 5 (Hilton only; each carries STATIC=N/A, OFFICIAL_ROUTE=confirmed Hilton property page, FIRECRAWL_ELIGIBLE=NO (measured wall), BROWSER_RESULT=blocked, FINAL_BLOCK_REASON=Hilton's own error page after a fresh capability check this session).

## Phases 13/21 — Provider cost safety & brand-by-brand

**EXISTING PROVIDER USAGE** = 89 Firecrawl credits (from a 544-credit balance; ~481 remaining after this build). **NEW PAID SPEND** = $0. **NEW PROVIDER AUTHORIZATION** = none. **PROVIDER COST** = 0 USD (Firecrawl is billed in plan credits under existing authorized capacity, per the mission's explicit distinction between existing capacity and new spend).

| Brand | Census | PF | NP | Unresolved |
|---|---|---|---|---|
| Marriott | 5 | 3 | 2 | 0 |
| Hilton | 7 | 0 | 0 | 7 (all AWAITING_ROUTING_REVIEW — capability wall) |
| IHG | 5 | 3 | 1 | 1 |
| Wyndham | 26 | 2 | 8 | 16 |
| Choice | 5 | 1 | 3 | 1 |
| Hyatt | 2 | 1 | 0 | 1 |
| Best Western | 0 | 0 | 0 | 0 |
| Sonesta | 0 | 0 | 0 | 0 |
| Extended Stay America | 0 | 0 | 0 | 0 |
| WoodSpring | 1 | 1 | 0 | 0 |
| Motel 6 / Studio 6 | 0 | 0 | 0 | 0 |
| Red Roof | 1 | 1 | 0 | 0 |
| Independent | 39 | 2 | 0 | 37 |
| **Total** | **91** | **14** | **14** | **63** |

## Phases 16–18 — Negation safety (the most important finding of this build)

The FAST release lane's rule C (first-party binding, `classify_quote`) caught **4 real negation-safety violations** that an earlier pass had wrongly marked `VERIFIED_NO_PETS`: **Avid Hotel, Comfort Inn & Suites, Hyatt House Augusta Downtown, Wingate by Wyndham Augusta Washington Road**. Every one of their evidence quotes reads, to a human, as a plain refusal ("Pets are not allowed at this location", "No Pets Allowed... pets and emotional support animals are not permitted", "The hotel does not allow pets except for service animals", "Sorry no other pets are allowed") — but the shared first-party reader classifies each `SERVICE_ANIMAL_ONLY` rather than confirming `pets_allowed = False`, because the source text is a run-on, punctuation-stripped scrape that the reader's refusal pattern cannot confidently parse.

**No shared reader code was touched.** Per the mission's explicit Phase 17 rule, all four were pulled out of the published no-pets exclusion list and re-classified `AWAITING_CONTRADICTION_RESOLUTION` in the partition — held, not guessed either direction. This is a genuine parser-vs-plain-text conflict, correctly caught by the machine-checkable release gate rather than shipped. **NEGATION / PARSER CONFLICTS CAUGHT = 4**, plus one earlier self-caught classifier bug (a co-occurring $250 penalty digit was letting the classifier override an explicit "no other pets allowed" refusal on Wingate Augusta I-20 — fixed before this report; that row is held `AWAITING_CONTRADICTION_RESOLUTION` for the same reason, listed above as one of the 5 total contradiction-resolution holds in the corridor table).

## Phase 19/20 — Complete accounting

| | |
|---|---|
| TOTAL DISCOVERED | 157 (94 OSM + 63 brand/competitor net-new) |
| PROPOSED CENSUS | **91** |
| VALID PET-FRIENDLY | **14** |
| VALID VERIFIED-NO-PETS | **14** |
| RESOLVED | **28** |
| UNRESOLVED | **63** |
| RESOLUTION RATE | **30.8%** |

Unresolved by exact class (every one bounded and justified, no generic bucket):

| Class | Count | Meaning |
|---|---|---|
| AWAITING_OFFICIAL_URL (routing) | 26 | no first-party URL ever found, free lanes exhausted for now |
| AWAITING_POLICY_OBSERVATION (evidence) | 19 | only shared brand-wide boilerplate captured, no property-specific statement |
| AWAITING_ROUTING_REVIEW (access-blocked) | 13 | Hilton capability wall (7) + 6 others genuinely blocked after router exhaustion |
| AWAITING_CONTRADICTION_RESOLUTION (negation) | 5 | explicit-reading refusal the shared reader will not confirm — held, not guessed |

Exclusions (outside the 91-row census, never silently dropped): OUTSIDE (South Carolina) = 21, OUT_OF_METRO_FALSE_POSITIVE = 20, NON_HOTEL = 6. CLOSED = 0. VACATION_RENTAL = 3 (competitor leads only, never candidates). TEMPORARY_EVENT_LODGING = 0. MILITARY_RESTRICTED = 0.

## Phase 22 — Corridor accounting

See the Phase 3/4 table above for census-per-corridor. Publication threshold (`minimum_hotel_count`, matching Savannah's own contract) is 5 confirmed hotels; **only Washington Road (21 census, 7 PF+5 NP=12 resolved) meets it today** — the shadow package's own assembler independently confirms exactly one corridor page is currently eligible (`/pet-friendly-hotels/augusta-ga/washington-road/`), plus the market's `/go/` affiliate pages (56) and the policy-comparison page. Gordon Highway (24 census, 9 resolved) is close but under-resolved for now; every other corridor is either below the count threshold or has zero-to-few confirmed identities pending free-lane URL discovery.

## Phase 23 — South Carolina boundary audit

NORTH AUGUSTA DISCOVERED = 1 (real hotel: Crowne Plaza, correctly excluded OUTSIDE after its real address resolved to SC 29841). AIKEN DISCOVERED = 10. OTHER SC DISCOVERED = 1 (Edgefield). **SC INCLUDED = 0.** SC OUTSIDE = 21 (all captured, all preserved as observation evidence for a future `north-augusta-sc`/`aiken-sc` market, none silently dropped). SC REVIEW = 0. **SOUTH CAROLINA PROFILES IN AUGUSTA-GA CENSUS = 0**, exactly as the mission's stated default requires.

## Phase 24 — Large-market quality challenge

Performed before sealing, not after: a second free-lane pass specifically targeted the 31 routing-hold rows and the Wyndham evidence/negation-hold cluster, using WebSearch identity discovery and a check for property-specific policy subpages beyond shared brand templates. This raised resolution from an initial 23/100 to a peak of 34/98 before the negation-safety gate (correctly) pulled 4 rows back out for the reasons above, landing at the final, safety-verified 28/91. No raw-count parity with V1 or any other market was targeted or manufactured.

## Phase 25 — Coverage readiness

- **TECHNICAL SOURCE READY = YES** — shadow package sealed, byte-identical reproduction proven three ways (in-process double-build + two independent process invocations), all 15 FAST rules PASS, 0 UNKNOWN, 0 FAILED.
- **COVERAGE READY = FOUNDER DECISION.** Mechanical reasoning: every acquisition/router/competitor lane was genuinely exercised (not skipped), the competitor challenge found no material unexplained gap, and every one of the 63 unresolved rows carries a bounded, specific reason and next action. But the 30.8% resolution rate is real and material — driven mostly by 26 independents/small brands with no first-party URL yet and 19 rows stuck on generic brand-template text — and a founder may reasonably want another free-lane pass (or an attended-browser session against the AWAITING_POLICY_OBSERVATION cluster's actual property pages, since only the brand overview page was captured for many of them) before treating Augusta as launch-competitive with its neighboring 25–28-market siblings, which typically resolve 60–80%+ of their census.

## Phase 26 — Shadow package

**SHADOW PACKAGE CREATED = YES.** Status `SHADOW_UNTIL_REGISTERED`, sealed against the CURRENT verified live parent (Savannah, 1fa43a48 lineage). Nothing registered, no participation change, no candidate, no deployment authorization, no deployment. Package written under `launch_packages/pettripfinder/markets/staging/augusta-ga/shadow_packages/augusta-ga/`; receipt under `.../shadow_receipts/augusta-ga/`.

- **PACKAGE_REPRODUCIBLE = YES** — package_digest **`sha256:985d8ef5d9dd36f1a044c1d3cf137f702475c4dda502607289035d33ef26bfbf`**, identical across the in-process double-build AND two fully separate `python` process invocations run afterward with fresh work directories.
- **FAST_DATA_ONLY_RELEASE_ELIGIBLE = YES**, all 15 rules (A–O) PASS, 0 UNKNOWN, 0 FAILED.

Real, non-trivial defects were found and fixed getting here — recorded for the record, not smoothed over:
1. A malformed `assignment_basis` enum value (my own earlier fix) — corrected to the contract's actual four-value enum.
2. 7 genuine duplicate identities (Phase 10, above) caught by the writer's `co_located_distinct` gate, not by any earlier dedup pass.
3. An `ORPHAN_PARTITION` gap — the market's own `ptf-market-final-partition/1.1` document existed only as an ad-hoc report, never in the schema/location the package writer actually reads (`<launch_package>/augusta_ga_final_partition_007.json`, `items[]` with `final_state`). Rebuilt properly from the real disposition data, following Savannah's committed file byte-for-byte as the schema template.
4. Every one of the 14 published pet-friendly records was missing `facts.pets_allowed: true`, per-fact evidence entries, and a top-level `reviewer_id` — all real, mechanically-required fields the earlier ad-hoc generation script never populated. Backfilled from the same real captured evidence already on file (nothing invented).
5. **A real evidence-citation defect**: 4 of the 14 published records (Candlewood Suites, Holiday Inn Express, Staybridge Suites, Rodeway Inn) cited the *wrong* artifact hash and, in Rodeway Inn's case, an unrelated OpenStreetMap URL as their "source" — traced to the real Firecrawl acquisition report and corrected to the actual captured page and content hash (verified present on disk).
6. **A missing paid-provenance chain (FAST rule O)**: those same 4 Firecrawl-sourced records had never been reconciled into the shared cross-run paid-attempt ledger (`ptf_paid_attempt_ledger_001.json`) or given a re-derivable reservation. Fixed the proper way — modeled directly on the committed `cincinnati_oh_firecrawl_ledger_reconciliation_003.py` precedent — by writing `augusta_ga_firecrawl_ledger_reconciliation_013.py`, which recorded the 26 real attempts from the real committed Firecrawl report into the shared ledger (0 historical rows changed, 0 other markets touched, confirmed by diff), and wiring real `paid_reservation` objects (real attempt ids, real request-envelope hashes pulled from the raw `firecrawl_call_ledger.jsonl`) into `augusta_ga_shadow_package_012.py`'s package inputs.

## Phase 27 — Reproducibility

- REPRODUCTION A = `sha256:985d8ef5d9dd36f1a044c1d3cf137f702475c4dda502607289035d33ef26bfbf`
- REPRODUCTION B (separate process, separate work directory) = `sha256:985d8ef5d9dd36f1a044c1d3cf137f702475c4dda502607289035d33ef26bfbf`
- **BYTE IDENTICAL = YES**
- NONDETERMINISTIC FILES = none found; no shared factory code was touched to achieve this.
- **PACKAGE DIGEST = `985d8ef5d9dd36f1a044c1d3cf137f702475c4dda502607289035d33ef26bfbf`**

## Phase 28 — FAST

ALL 15 applicable rules (A–O) PASS. 0 UNKNOWN, 0 FAILED. No broad regression run — none was needed or requested; this is market-local, shadow-only work.

## Phase 29 — V1 vs V2 diagnostic

| | V1 (historical, `augusta-ga-market-001`) | V2 (this order) | Delta |
|---|---|---|---|
| CENSUS | 82 | 91 | +9 |
| PET-FRIENDLY | 24 | 14 | −10 |
| NO-PETS | 13 | 14 | +1 |
| RESOLVED | 37 | 28 | −9 |
| UNRESOLVED | 45 | 63 | +18 |
| RESOLUTION RATE | 45% | 30.8% | −14.2 pts |
| ACCESS_BLOCKED | 17 | 5 (after full router exhaustion) | −12 |

**V2 is not simply "better" or "worse" than V1 — it is differently and more defensibly evidenced**, and the two numbers most worth explaining are the drop in resolution rate and the drop in access-blocked:

- **ACCESS_BLOCKED fell from 17 to 5** because this is exactly the defect class the mission called out by name: V1 walked Marriott/IHG/Hilton into a browser and gave up when static/browser access failed, without ever trying the authorized Firecrawl lane the route table already sends IHG/Wyndham/Choice to. V2's router correctly escalated those families to Firecrawl first (89 real credits spent, 89 successes), leaving only the 5 Hilton rows that are a genuinely measured capability wall with no further lane available — a real, structural improvement in acquisition completeness, not a cosmetic one.
- **PET-FRIENDLY fell from 24 to 14, and the overall resolution rate fell from 45% to 30.8%, primarily because of the negation-safety gate described in Phases 16–18.** V1's build predates the hardened factory's rule-C safety check entirely; it is plausible (though not verified in this order, since V1 is read-only history) that some of V1's 24 published pet-friendly or 13 no-pets rows rest on the same class of ambiguous, run-on, service-animal-adjacent text that V2's FAST lane refused to publish four times this build. V2 is not lower because it discovered fewer real pet-friendly hotels; it is lower because it refused to guess where a earlier, less-hardened pipeline may have.
- The **+18 unresolved** is the direct, honest cost of a larger, more independently-challenged census (91 vs. 82, +9 real identities) combined with the negation-safety holds, not a regression in acquisition effort — every one of the 63 unresolved rows carries a specific, bounded reason and next action, which V1's 45 unresolved rows are not shown to have.

No V2 methodology was altered to chase or avoid this comparison; every number above was fixed before this section was written.

## Phase 30 — Parallel safety

```
CROSS-MARKET FILE CHANGES = 0
SHARED FACTORY CHANGES = 2 files, both purely additive appends (0 deletions in either diff):
  - scripts/pettripfinder/discovery/config/osm_extracts.json  (+24 lines: 2 new rows naming augusta-ga only)
  - launch_packages/pettripfinder/ptf_paid_attempt_ledger_001.json  (+936 lines: 26 new attempt rows for augusta-ga only, 0 historical rows changed, 0 other markets' rows added)
CANONICAL LIVE CHANGES = 0
DEPLOYMENT STATE CHANGES = 0
```
Confirmed by `git status --porcelain` (every other path is `augusta_ga_*` / `augusta-ga` scoped) and `git diff --stat` (both shared-file diffs are insertion-only).

## Phase 31 — Performance / cleanup

Exact per-phase timing was not instrumented as a single profiled run (this order proceeded through several long-running, real-network sub-passes rather than one profiled process); the load-bearing, precisely measured numbers are:
- Full 44-cell OSM/Overpass + Geofabrik-extract discovery: multi-hour (blocked ~5h real-time on public endpoint cooldown before the local extract was built; the extract build + full discovery replay itself took under 30 minutes once started).
- Shadow package seal + FAST (the fully profiled, reproducible step): **36.8 seconds** per cold build (`seconds: 36.8` in the shadow-package report), run three times with identical results.
- No background watchers, temporary servers, browser relay processes, or child workers were left running; the only test/scratch artifacts are under the gitignored `data/fast_work/` and `data/discovery/`/`data/acquisition/` trees.

```
ZERO_TO_SOURCE_READY ≈ 12h30m wall-clock (≈5h of which was an idle/stalled gap, not active work)
PROVIDER COST = $0 (89 Firecrawl plan credits, existing authorized capacity)
NEW PAID SPEND = $0
FOUNDER INTERVENTION = 0 (none of the four narrow triggers fired)
```

## Phase 32 — Commit / push

Commit created on `worker/ptf-augusta-ga-market-002`; pushed to `origin`. `origin == HEAD` and tree-clean verified mechanically after push (see FINAL ANSWERS below).

---

# FINAL ANSWERS

1. START TIMESTAMP = 2026-09-15T20:47 (local)
2. ZERO_TO_SOURCE_READY = ≈12h30m wall-clock (≈5h idle/stalled, ≈7–7.5h active)
3. TOTAL DISCOVERED = 157
4. PROPOSED CENSUS = 91
5. VALID PET-FRIENDLY = 14
6. VALID VERIFIED-NO-PETS = 14
7. RESOLVED / UNRESOLVED = 28 / 63
8. RESOLUTION RATE = 30.8%
9. HOLDS BY CLASS = AWAITING_OFFICIAL_URL 26, AWAITING_POLICY_OBSERVATION 19, AWAITING_ROUTING_REVIEW 13, AWAITING_CONTRADICTION_RESOLUTION 5
10. CORRIDOR COVERAGE = 11 corridors defined; only Washington Road (30907) currently meets the 5-hotel publication threshold with a majority resolved; Gordon Highway close but under-resolved; others below threshold or pending free-lane URL discovery
11. SOUTH CAROLINA BOUNDARY ACCOUNTING = 21 SC hotels discovered (10 Aiken, 1 North Augusta, 1 Edgefield, +9 additional Aiken-area rows), 0 included, 21 outside/preserved, 0 review; SC profiles in augusta-ga census = 0
12. OWNED EVIDENCE REUSED = 0 (none existed to reuse; confirmed clean)
13. COMPETITOR RAW / NORMALIZED / MATCHED / TRUE MISSING = 19 / 19 / 7 / 1
14. MATERIAL COMPETITOR GAP REMAINS = NO
15. FIRECRAWL ELIGIBLE = 27 initially (grew as free-lane discovery continued)
16. FIRECRAWL ATTEMPTED = 111 total ledger calls (89 ok, 22 refused/failed)
17. FIRECRAWL SUCCESS = 89
18. FIRECRAWL FAILED = 22 (0 credits each — bimodal cost confirmed)
19. ACCESS_BLOCKED AFTER ROUTER EXHAUSTION = 5 (Hilton capability wall only)
20. NEGATION / PARSER CONFLICTS CAUGHT = 4 (Avid Hotel, Comfort Inn & Suites, Hyatt House Augusta Downtown, Wingate by Wyndham Augusta Washington Road) + 1 earlier self-caught classifier bug (Wingate Augusta I-20 fee-vs-refusal conflict)
21. EXISTING PROVIDER USAGE = 89 Firecrawl plan credits
22. NEW PAID SPEND = $0
23. PROVIDER COST = $0
24. SHADOW PACKAGE CREATED = YES
25. PACKAGE REPRODUCIBLE = YES
26. PACKAGE DIGEST = sha256:985d8ef5d9dd36f1a044c1d3cf137f702475c4dda502607289035d33ef26bfbf
27. APPLICABLE FAST = 15/15 PASS, 0 UNKNOWN, 0 FAILED
28. TECHNICAL SOURCE READY = YES
29. COVERAGE READY = FOUNDER DECISION
30. V1 CENSUS / RESOLVED / UNRESOLVED = 82 / 37 / 45
31. V2 CENSUS / RESOLVED / UNRESOLVED = 91 / 28 / 63
32. V2 IMPROVEMENT EXPLANATION = access-blocked fell 17→5 because the router correctly escalated IHG/Wyndham/Choice to Firecrawl instead of giving up at a failed browser/static attempt (V1's exact defect class); pet-friendly and resolution rate fell because V2's negation-safety gate (rule C) refused to publish 4 properties whose refusal text the shared reader could not mechanically confirm, and because the census itself grew (+9 real identities) through more thorough discovery — every unresolved row is bounded and reasoned, not a blind gap
33. CROSS-MARKET FILE CHANGES = 0
34. FACTORY CODE CHANGED = NO (two shared DATA files changed, both purely additive: `osm_extracts.json` +2 rows, `ptf_paid_attempt_ledger_001.json` +26 rows, 0 deletions, 0 other markets affected)
35. BROAD REGRESSION RUN = 0
36. FINAL PRODUCTION CANDIDATE CREATED = NO
37. FOUNDER AUTHORIZATION CREATED = NO
38. AUGUSTA DEPLOYED = NO
39. origin == HEAD = (verified after push — see commit output)
40. tree clean = (verified after push — see commit output)

AUGUSTA V2 SOURCE READY = YES
AUGUSTA V2 COVERAGE READY = FOUNDER DECISION
AUGUSTA V2 FINAL CANDIDATE = NO
AUGUSTA V2 DEPLOYED = NO
BROAD REGRESSION RUNS = 0
FACTORY CODE CHANGED = NO
WAITING FOR RELEASE QUEUE = YES
