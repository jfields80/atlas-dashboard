# PTF-FORT-MYERS-FL-HARDENED-SOURCE-READY-001 — FINAL

Market `fort-myers-fl` — Fort Myers / Cape Coral / Southwest Florida, Florida.
Branch `worker/ptf-fort-myers-fl-market-001`, worktree `C:\Atlas-Fort-Myers-FL-Hardened-V1`.
Built from zero to a reproducible, market-local SOURCE-READY state. **Not registered, not authorized, not deployed.**

## Lineage (resolved mechanically)

- Current verified live: **Salt Lake City**, deploy `6ac6f3d213d002249f9c3e67` — 45 markets / 4,373 profiles / 4,807 release-index / 4,885 served; lineage `3d812f28`, read by `release_index live-source --verify-host` and confirmed again at seal time by `RI.live_index()` (the shadow package's `parent_live_state`).
- Automatic base: `registration_release_lane.derive_registration_base('fort-myers-fl', '3d812f28')` → **`21dacb1c`** (the newest first-parent ancestor that names no Fort Myers path). Fort Myers' commits on top: `8f7af81d`, `f0096324`, `c3e1c931`, plus this report's commit.

## Headline

| | |
|---|---|
| Total discovered (raw observations, all lanes) | 1,236 |
| Normalized identities (graph nodes) | 658 |
| Qualifying census | **142** |
| Pet-friendly | **57** |
| Verified no-pets | **34** |
| Resolved | 91 |
| Unresolved (held) | 51 |
| Resolution rate | 64.1% |
| ACTIONABLE UNRESOLVED | **0** |

Lanes: Florida DBPR public-lodging licence register (304 leads; 8,825 CNDO/DWEL/NAPT unit/apartment rows counted, never leads), OpenStreetMap from the owned Florida extract (418 elements, 0 downloads), brand inventories (122 leads), Lee County VCB roster (200 listings), BringFido (196 normalized — identity challenge only), attended-browser reads (98 attempts), free static capture, Wyndham property service, Google Places (78 requests, free allowance).

**Holds by class (51):** ROUTING 25 · SOURCE_SILENT 16 · EVIDENCE 8 · IDENTITY 2 · ACCESS_BLOCKED 0 · NEGATION 0 · BROWSER_CAPTURE 0.

**Actionability (every held row):** AUTHORIZED_ROUTER_EXHAUSTED 49 · REQUIRES_FOUNDER 2 (Pink Shell Beach Resort and Edison Beach House: refusals stated on their own pages that the **shared** reader cannot interpret — held safely, never published; a shared-reader change this order may not make) · ACTIONABLE_NOW 0 · NEW PROVIDER 0 · NEW SPEND 0.

**Exclusions by class (graph residue, never census):** OUTSIDE 196 · VACATION_RENTAL 93 · NON_HOTEL 45 · TIMESHARE 5 · NAME_ONLY_UNRESOLVED 105 · IDENTITY_REVIEW_REQUIRED 69 · SAME_CAMPUS_DISTINCT_ENTITY 2 · SAME_IDENTITY_REBRAND_SUCCESSOR 1.

## Geography and boundary

- 14 corridors (5 CORE, 6 CORRIDOR, 3 FRINGE). Publishing corridors (≥5 PF): colonial-cleveland, daniels-six-mile, rsw-airport-gateway, bonita-springs.
- **WRONG-CITY FORT MYERS IDENTITIES = 0**; Fort Myers label on another municipality = 0; Collier/Charlotte/Hendry-licensed admitted = 0. Beach/island rows all publish their own municipality (Fort Myers Beach 16, Sanibel 18, Captiva 4; 0 labelled Fort Myers).
- **NAPLES ADMITTED = 0.** Refused graph nodes: Naples/North Naples 71, Marco Island 11, Everglades City 6, Immokalee 4, Punta Gorda 14, Port Charlotte 11, Englewood/Boca Grande 19, Pine Island 9, LaBelle/Clewiston 14, Sarasota-and-north 2+1 brand card; admitted from a refused code 0.
- **Founder geography ruling surfaced (held, not decided):** *Latitude 26 Waterfront Inn & Suites, 4701 Bonita Beach Rd, 34134* — the ZIP is Lee (Bonita Springs, admitted) but the State licence names **Collier** County. Held OUTSIDE (COUNTY_REFUSAL).
- RSW: 12 rows in rsw-airport-gateway.

## Operating status (post-hurricane)

Every admitted row classified from evidence observed in this order (`fort_myers_fl_operating_status_accounting_001.json`):
CURRENTLY OPEN 109 · REOPENED 6 · TEMPORARILY CLOSED 2 · CLOSED FOR REBUILD 0 · PERMANENTLY CLOSED 3 · DEMOLISHED 0 · PREOPENING 0 · STATUS UNKNOWN 22 (none published).

- Fort Myers Beach (16): open 11, reopened 3, permanently closed 2 (Wyndham Garden FMB — brand route retired + Places CLOSED_PERMANENTLY; Beach Shell Inn — domain parked for sale + Places CLOSED_PERMANENTLY).
- Sanibel (18): open 9, reopened 3, temporarily closed 2 (Song of the Sea — operator: "currently closed and is under review for redevelopment"; Sanibel Sunset Beach — operator route retired, Places CLOSED_TEMPORARILY), unknown 4.
- Captiva (4): open 4.
- **CURRENT OPERATION PROVEN for every published property = YES. NONOPERATING PROFILES PUBLISHED = 0.**
- Rebrand held for founder: 4760 S Cleveland Ave (Quality Inn now; Travelodge route retired). The former La Quinta I-75 at 9521 Marketplace Rd is the current Stay Well Inn & Suites (one row; a street-spelling fold merged the stale duplicate).

## Publication safety (shared reader run in advance of FAST rule C)

All 15 checks = 0: PF with explicit refusal, question-only PF, service-animal-only PF, preopening/closed, timeshare/vacation-ownership, military, misleading single fee, no-pets without refusal, wrong-city label, outside partition, Naples/Collier, boundary island, non-operating signal, vacation rental/condo, shared-reader disagreement.

**Fees:** 5 single-basis fees published (each one amount with its own stated basis); 22 tiered fees withheld; 5 unsafe single fees withheld (basis not stated 3, amount floor "$75.00+" 1, cut sentence 1); MISLEADING SINGLE FEES = 0. Multi-charge policies (Lighthouse Island: daily fee + cleaning fee + deposit; Captiva Island Inn: per-unit tiers; ESA: capped daily) publish acceptance only.

## Browser and providers

- Attended browser (claude-in-chrome): 98 attempts, 69 bound reads, 0 anti-bot denials; Akamai never bypassed; no JS exfiltration, no relay, no CAPTCHA. **Marriott: census 17, attempted 17, read 17, actionable 0** (done first). Other families: 81 attempted / 52 reads.
- Durable evidence: every quote is node text read by ref or a full-resolution screenshot transcription; the browser `find` summary paraphrased South Seas' FAQ answer (it invented an ESA exception) and was discarded for the on-screen text.
- Firecrawl: 0 attempted (no protected reserve touched). Google Places: 78 requests (45 Enterprise / 33 Pro) inside the free monthly allowance. **New paid spend $0.**

## Competitor (BringFido — identity only)

Raw 310 / normalized 196 / matched 60 (58 distinct) / **TRUE MISSING 0**. Unplaced leads resolved by the DBPR register: Off the Charts Inn and Two Fish Inn (Pine Island, OUTSIDE), Wyvern Hotel (Punta Gorda, OUTSIDE), Woodsmoke (RV), unit listings; one name ("23 Palms at Ivy Inn") names no licensed premises.

## Clone residue (before the first seal)

CLONE MARKET TEXT RESIDUE 0 · CLONE COORDINATE RESIDUE 0 · CLONE BOUNDARY RESIDUE 0 (two homonyms excused with reasons: Cleveland Avenue, Charlotte County).

## Package and FAST

- Seal 1 (commit `8f7af81d`): FAST **J FAIL** — the Choice route recorder had stored host-only routes (`www.choicehotels.com/...`) and the site builder refused them as unsafe `/go/` destinations. Fixed in the market's own route normaliser; every route then validated with the builder's own `_validate_destination`. Seal-1 outputs discarded.
- Seal 2 (commit `f0096324`), `SHADOW_UNTIL_REGISTERED`: **`pkg-fort-myers-fl-68b3cfa8bc4758c5`**, digest `sha256:68b3cfa8bc4758c5b0d935d385fee3404ab01ed569f65ca2dc52d0c1733a2415`. **FAST 15/15**; Rule J bundle `cc784255…` with 367 files / 351 HTML (non-empty); Rule K BYTE_IDENTICAL over 4 cold builds (non-vacuous); first-party gate PASS. Receipt `pkg-fort-myers-fl-68b3cfa8bc4758c5-4a056b97814fece9.json` (digest `sha256:4a056b97…`) is **currently eligible** (`fast_release_lane.eligible_receipts`). The seal changed outputs only (fixed point).
- **Independent reproduction** (separate process, detached worktree at `f0096324`, separate short work path `C:/t/fmy2w`, never concurrent with the seal): the same package id and digest `68b3cfa8…`, FAST 15/15, Rule J bundle `cc7842555030cede…` 367 / 351 (identical), Rule K BYTE_IDENTICAL ×4 cold. **PACKAGE REPRODUCIBLE = YES (byte-identical).** The temporary worktree and work directories were removed afterwards.

## Isolation

Cross-market file changes 0; factory/shared code changed: none (only `fort_myers_fl_*` modules, the market's discovery config, and its own staging/reports); broad regression runs 0; no registration, no founder authorization, no deployment authorization, no final production candidate, no deployment.

## Performance

- START TIMESTAMP = 2026-10-08T02:19:01Z
- ZERO_TO_SOURCE_READY = 2h 25m 32s (seal-2 FAST receipt finished 2026-10-08T04:44:33Z)
- ZERO_TO_COVERAGE_READY = 2h 27m 08s (actionability COVERAGE READY = YES at 04:46:09Z)
- Longest compute: OSM statewide extract scan ~24 min; each seal + FAST ~10 min (FAST itself 64 s); reproduction ~10 min — all run detached and one at a time on a ~16 GB machine (free memory ~2.4 GB at seal time).
- Provider / cooldown wait: none beyond page-load waits in the attended browser (Choice's Akamai interstitial cleared on its own).
- Firecrawl credits 0 · Places requests 78 · new paid spend $0 · provider cost $0 · founder intervention: none during the run.
- Cleanup: only processes this order created were run (two seals, one reproduction, monitors) and all exited; the pre-existing Python process (pid 14180) was left untouched; work dirs `C:/t/fmy0`, `fmy1a`, `fmy1b`, `fmy2w` and worktree `C:/t/fmy2` removed.

## Machine-readable accountings

`atlas-dashboard/launch_packages/pettripfinder/markets/reports/`: `fort_myers_fl_source_accounting_001.json`, `_provider_`, `_brand_`, `_corridor_`, `_beach_island_`, `_operating_status_`, `_competitor_reconciliation_accounting_` (+ `fort_myers_fl_competitor_reconciliation_001.json`), `fort_myers_fl_actionability_001.json`, `_boundary_`, `_municipality_`, plus `fort_myers_fl_publication_safety_audit_001.json`, `fort_myers_fl_fee_withholding_001.json`, `fort_myers_fl_clone_residue_scan_001.json`, `fort_myers_fl_shadow_package_001.json`.
