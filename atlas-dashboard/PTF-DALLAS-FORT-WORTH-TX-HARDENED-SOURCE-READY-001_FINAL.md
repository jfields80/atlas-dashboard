# PTF-DALLAS-FORT-WORTH-TX-HARDENED-SOURCE-READY-001 — FINAL (with CONTINUE)

Market `dallas-fort-worth-tx`, branch `worker/ptf-dallas-fort-worth-tx-market-001`, worktree
`C:\Atlas-Dallas-Fort-Worth-TX-Hardened-V1`.

**Result:** the market is TECHNICALLY SOURCE READY. Its SHADOW_UNTIL_REGISTERED package `pkg-dallas-fort-worth-tx-e8a841396faeffec` passed FAST 15/15:
- Rule J nonempty: 2,613 files and 2,597 HTML files.
- Rule K: BYTE_IDENTICAL.

The receipt is currently eligible. An independent reproduction in a detached worktree matched the package byte for byte.

**COVERAGE READY = FOUNDER DECISION, not YES.**
- ACTIONABLE UNRESOLVED is 0 and MARRIOTT ACTIONABLE REMAINING is 0.
- 29 unresolved rows can only move with a decision this order may not make:
  - 25 small independents have no free route and would need new Places spend.
  - 4 rows need a founder routing or naming ruling.
- Nothing was registered, authorized or deployed.

Commits:

| Commit | Contents |
|---|---|
| `573d07d0` | checkpoint (previous session) |
| `df4da832` | seal inputs |
| `b1101285` | sealed package + receipt |
| this report's commit | final report |

---

## CONTINUE-order reports

### Phase 1–2 — timer and memory
The 02:10Z window had passed when checked (02:17:29Z), so batch H launched directly. No duplicate waiter was kept.

No seal, FAST, reproduction or other large process ran until Marriott finished. Every heavy step after that ran detached and strictly one at a time:
- pipeline passes;
- seal + FAST;
- reproduction.

### Phase 3 — Marriott batch H, and the full cooldown history

| Window | What happened |
|---|---|
| Batch A | 49 reads, then an Akamai block |
| Batches C, E | about 1 read per ~22 min (throttled); the last request before cooldown 1 was ~19:05Z |
| Cooldown 1 | ~19:05Z → 22:05Z (about 3 h idle; no requests, no bypass) |
| Batch G | 22:05:10Z–23:09:33Z: 40 of 42 rows read. **Akamai Access Denied** at `dfwfn` at 23:09:40Z, ref `18.8a89cc17.1791587376.841022a`, still denied after one ordinary recheck. Stopped. |
| Cooldown 2 | 23:09:40Z → 02:17Z (about 3 h 08 m idle; no requests) |
| Batch H (the later authorized window) | first navigation ~02:18:02Z, ~90 s pacing. 39 queue rows attempted with 41 navigations: rows 25 and 36 used old `/hotels/travel/` URLs that 404'd, and each took one second navigation to the `/overview/` route built from the code in its URL. **38 first-party reads** (recorder seq 764–801): 24 accept pets, 14 state "Pets Not Allowed". |
| **Terminal result** | The 41st navigation (`dalsh`, SpringHill Suites Dallas Addison Quorum) drew **Akamai "Access Denied"** at ~03:20:46Z, ref `#18.8a89cc17.1791602447.af47e47`. One ordinary recheck ~20 s later (03:21:30Z) gave the same denial and the same reference. Recorded at seq 802 (03:21:46Z). **Marriott requests STOPPED.** |

No bypass, no browser-JS exfiltration, no relay, no evasion of the challenge page, and no hammering. Per the CONTINUE order, no further cooldown or retry loop was started without a genuinely new authorized window.

**Rows beyond the stop:**
- **What happened to them.** The 31 queue rows the window never reached (rows 40–70) are classified consistently by one measured rule, MARRIOTT_AUTHORIZED_WINDOW_CLOSED:
  - The rule lives in the market's own clean-authority and actionability modules.
  - It is derived from the recorder's own last Marriott record. It holds a row only when that record is an anti-bot denial.
  - Each row is held as ACCESS_BLOCKED (24) or ROUTING_HOLD (7), classed AUTHORIZED_ROUTER_EXHAUSTED.
  - Each row cites the exact blocker: seq, timestamp and Akamai reference.
- **What would reopen them.** A genuinely new authorized Marriott window.

**Per-row fields.** Each recorder line (seq 764–802 of `raw_captures/browser_reads_001.jsonl`) records the CONTINUE order's capture fields:
- requested URL, final URL, property code, trade name (`page_title`), address (`page_address_line`);
- identity match (`full_premises_match`, binder), operative pet quote, parsed status;
- fee wording, content reference (note / transcription), timestamp and result.

City, state and ZIP are parsed from the address line. The phone and content reference are in each note.

**Name or address differences the window reported** (none is a different premises):
- **Name only differs:**
  - `dfwfd`: the name adds "/Convention Center".
  - `dfwsh`: the full name is "Dallas Arlington North".
  - `dfwsy`: the name adds "Historic Stockyards".
  - `dfwrf`: the name lacks "/Waterside".
- **City printed differently:** `dalre` and `dalsl` print Dallas 75234 / 75244, where the census uses the place boundary (Farmers Branch).
- **Spelling only:** `dalsa`, `dalrp` and `dfwak`.

**Fee wording that is daily, nightly, tiered, capped or conflicting** is all withheld (Phase 11):
- `dfwfd`: $5/day + $50 per stay.
- `dalre`: $50 per night.
- `dalrd`: $50 per pet per night, up to $150, an extra fee after 6 nights.
- `dalpr`: $5/day + $100 per stay.
- `dalls`: $20/day + $100 per stay.
- `dalsi`: $75 per day.
- `dalrp`: free text "USD 150/200 per stay" vs the structured "$100 per stay".

### Phase 4 — dedup (ONE PREMISES = ONE HOTEL IDENTITY)
- **Census rule.** The census now folds 10 same-premises duplicate listings (DUPLICATE_LISTING, each citing its surviving row and pin distance). Comfort Inn DFW Airport North and Candlewood DFW North stay distinct: different phones, streets and pins.
- **dfwts:** "Tps Fort Worth" (4200 International Plaza) is folded into **TownePlace Suites – Southwest (dfwts)**, one identity. dfwts was in the unreached part of batch H, so it is held on the closed window.

**Marriott accounting**

| Figure | Value |
|---|---|
| MARRIOTT RAW QUEUE (batch H) | 70 |
| UNIQUE PREMISES (Marriott census) | 166 |
| DUPLICATE-ALIAS ROWS folded | 1 (Tps Fort Worth → dfwts) |
| RESOLVED | 128 (77 PF / 51 NP) |
| TERMINAL HOLDS | 38 |
| ACTIONABLE REMAINING | **0** |

The 38 terminal holds are:
- 32 AUTHORIZED_ROUTER_EXHAUSTED:
  - 31 held on the closed window;
  - 1 on its own read's terminal outcome.
- 6 REQUIRES_FOUNDER:
  - 4 dual-brand rows (AC/Residence Inn 1712 Commerce, Courtyard/Residence Inn 480 E John Carpenter);
  - 2 Fairfield rows in a site-title collision.

### Phase 5 — Beeman Hotel vs Hotel Mockingbird (row 64, `dalnb`)

| Question | Determination |
|---|---|
| SAME PREMISES | **NOT PROVEN** — no first-party `dalnb` page was ever read: row 64 was beyond the batch H stop. |
| CURRENT TRADE NAME | not verified first-party. Marriott's state sitemap titles `dalnb` "Hotel Mockingbird, Dallas, a Tribute Portfolio Hotel", but no page read binds it to 6070 N Central Expy. |
| CURRENT OPERATOR | not verified |
| CURRENT MARRIOTT / BRAND BINDING | NOT EXACT — a route only, named by Places for the Beeman row; no page read |
| CURRENT PROPERTY CODE | `dalnb` (routing claim only) |
| OLD IDENTITY RETIRED | NO |
| POLICY EVIDENCE MIGRATION SAFE | **NO** |

The row is **HELD** (ROUTING_HOLD, AUTHORIZED_ROUTER_EXHAUSTED on the closed window). No evidence was reused on the strength of a matching address.

### Four Points Arlington (row 2)
The vanity domain `fourpointsarlington.com` redirected to marriott.com **`dfwfa`**, "Four Points by Sheraton Dallas Arlington Entertainment District". The page prints "2451 East Randol Mill Road, Arlington, Texas, USA, 76011" (the census address) and phone +1 817-640-5454.

The page states **Pets Not Allowed**, so the row is CLEAN_VERIFIED_NO_PETS. The name on the page is fuller than the queue's; same premises.

### Phase 6 — ZIP 76028 / E Alsbury rows (folded in without rereading)
- **FORT WORTH MUNICIPALITY BINDING = PASS.** The 8 rows at Jake Ct / Pace Alsbury Ct / E Alsbury Blvd at I-35W (about 32.564 N, −97.316) are placed by CENSUS_PLACE_BOUNDARY inside the City of Fort Worth, Tarrant County. OSM and the bureau pins agree.
  - The brands' own pages say "Burleson".
  - Their premises sit inside Fort Worth city limits.
  - They are labelled Fort Worth, never Burleson (Johnson County).
- **Super 8 by Wyndham Burleson Fort Worth Area** (151 E Alsbury Blvd): uses the saved first-party read. **PET-FRIENDLY**, max 2 pets. The fee "non-refundable charge of 20.00 USD per pet per day" is daily, so it is **WITHHELD**.
- **La Quinta Inn & Suites by Wyndham Ft. Worth – Burleson** (225 E Alsbury Blvd, +1-817-349-7574): the old route was retired and the live route was read. **PET-FRIENDLY**: 2 pets, cats and dogs, 75 lb. The fee "Non-refundable 25 USD nightly for up to 2 pets. Max 75 USD per stay." is **WITHHELD** (fee = none) and never flattened into one figure.

### Phase 7 — acquisition: every unresolved row has one class (325 rows)

| Disposition | Total | Router exhausted | New spend | Founder | Until opening | Actionable now |
|---|---|---|---|---|---|---|
| ACCESS_BLOCKED | 39 | 39 | 0 | 0 | 0 | 0 |
| EVIDENCE_HOLD | 50 | 41 | 0 | 5 | 4 | 0 |
| IDENTITY_MISMATCH_HOLD | 41 | 25 | 0 | 16 | 0 | 0 |
| ROUTING_HOLD | 146 | 121 | 25 | 0 | 0 | 0 |
| SOURCE_SILENT | 49 | 49 | 0 | 0 | 0 | 0 |
| **Total** | **325** | **275** | **25** | **21** | **4** | **0** |

- **AUTHORIZED LANE REMAINING:** none for any row.
  - **Places** spent its free Enterprise allowance: 215 of the 215 this order may make, on top of earlier orders' 775 this month.
  - **Firecrawl** has 60 credits, all of them the protected reserve, so 0 are usable; 0 attempts.
  - **Marriott** is closed by the Akamai denial.
- **Terminal hold reasons:** each row's reason is in `reports/dallas_fort_worth_tx_actionability_001.json` (`rows[].why`).

**The 29 rows that gate coverage:**
- **REQUIRES_NEW_SPEND (25), each a ROUTING_HOLD independent with no free route:** 183 Motel, Americas Best Value Inn & Suites Fort Worth, Benbrook Inn & Suites, Best Budget Suites, Bingham 1883, Comfort Suites Lake Worth, Dude Inn Motel, Gold Inn, Golden Inn, Golden Inn Dallas, Intown Suites Rufe Snow, La Mirage Inn, Linfield Inn, Mesquite Inn, Mm Inn and Suites, Motel 6 Bedford, Plaza Motel, Romantic Inn & Suites, Royal Inn & Suites, Scottis Inn & Suites, Shamrock Motel, Shangrila Courts, Studio 6 Burleson, West Worth Inn & Suites, Western Skies Motel.
- **REQUIRES_FOUNDER not covered by the safe-hold rule (4):**
  - ROUTE_DOMAIN_CONFLICT: Executive Inn and Sonesta Select Fort Worth Fossil Creek, each with two first-party routes for one premises.
  - SITE TITLE COLLISION: two Fairfield by Marriott Inn & Suites Dallas DFW rows share a 60-character title.
- **The other 17 founder rows are safely held:**
  - 14 dual-brand rows (7 buildings);
  - 3 refusals the shared reader cannot interpret: Buzen Suites, Crowne Plaza Dallas Market Center, Holiday Inn Dallas Market Center.

### Phase 8 — final adjudication
The pipeline was rerun to a **fixed point**: two consecutive full passes changed **0** files.

Two market-owned defects were found and fixed on the way:
1. **Red Roof names.** Redroof.com page headings print only the location ("Fort Worth South", "Hutchins"), and those became display names. "Fort Worth South" collided with the corridor route `/fort-worth-south/`, so the seal refused (INVALID_ROUTE).
   - All 14 Red Roof rows now carry the brand label from the brand's own route family ("Red Roof …", "HomeTowne Studios by Red Roof …").
   - No sub-flag is invented.
   - A pass with and without the label classifies every census row the same way.
2. **The Studio 6 Mesquite read (3601 U.S. 80) prints no ZIP.** It took 75150 only from the census row it bound to, and the census alternated 966 / 965 between passes.
   - It is now bound to 75150, the ZIP the Texas licence and OSM rows at the same house number state.
   - The building is held as a Motel 6 → Studio 6 rebrand (SAME_IDENTITY_REBRAND_SUCCESSOR); nothing publishes.

**Safety counts:**
- PF with explicit refusal 0; question-only PF 0; service-animal-only 0; misleading single fees 0.
- Suburban mislabeled Dallas 0; suburban mislabeled Fort Worth 0.
- Plano labeled Dallas 0; Frisco labeled Dallas 0.
- Wrong-city 0; refused-county admitted 0.
- Preopening/closed published 0; timeshare published 0; vacation-rental/condo published 0; private residence published 0; military published 0.
- Shared reader disagrees 0. The publication safety audit is `all_zero = True`.

### Phase 9 — coverage challenge
Census / PF / NP / unresolved by municipality (CENSUS_PLACE_BOUNDARY placement):

| Area | Figures |
|---|---|
| Dallas | 205 / 73 / 43 / 89 |
| Fort Worth | 178 / 66 / 36 / 76 |
| Irving (incl. Las Colinas) | 96 / 47 / 20 / 29 |
| Arlington | 64 / 30 / 14 / 20 |
| Plano | 59 / 34 / 14 / 11 |
| Frisco | 29 / 18 / 7 / 4 |
| Grapevine | 17 / 9 / 5 / 3 |
| DFW Airport corridor | 10 / 3 / 2 / 5 |

Every named area of the order, including Mid-Cities, Addison, Richardson, Carrollton/Farmers Branch, Lewisville/The Colony and Alliance/North Fort Worth, has a publishing corridor. There are 26 publishing corridors.

**Inventory challenge:**
- OSM: 1,166 elements.
- Brand inventories: 567 leads.
- Tourism bureaus: 1,120 roster rows.
- BringFido: 1,380 raw / 649 normalized / 485 matched (459 distinct) / 22 true missing. Places gap verification of those 22 found 10 already in the census, 10 verified missing (admitted), and 2 outside.

**MATERIAL IDENTITY GAP = NO; MATERIAL POLICY GAP = NO.** Every unresolved row has an explicit, bounded reason. No broad rediscovery was run.

### Phase 10 — final accounting
- **Census and resolution:**
  - Qualifying census 965: **440 PET-FRIENDLY / 200 VERIFIED NO-PETS**.
  - Resolved 640, unresolved 325, resolution rate **66.32%**.
- **By county** (census / PF / NP / unresolved):

  | County | Census | PF | NP | Unresolved |
  |---|---|---|---|---|
  | Dallas | 437 | 187 | 93 | 157 |
  | Tarrant | 350 | 145 | 70 | 135 |
  | Collin | 129 | 80 | 28 | 21 |
  | Denton | 49 | 28 | 9 | 12 |

  They sum to 965.
- **Machine-readable accountings** (in `launch_packages/pettripfinder/markets/reports/`): source, provider, brand, county, city, corridor, DFW-airport, competitor reconciliation, actionability, boundary, marriott, fee withholding, publication safety and clone residue (`dallas_fort_worth_tx_*_001.json`).

### Phase 11 — fees
- Single-basis fees published: 63.
- Tiered withheld: 150.
- Unsafe single fees withheld: 47 (basis not stated 34, stay-length condition 9, sentence cut 3, amount range 1).
- **MISLEADING SINGLE FEES = 0.**

Every day/daily/nightly, capped or multi-amount fee is withheld, including La Quinta's $25 nightly / max $75 and Super 8's $20 per pet per day.

### Phase 12 — clone and boundary
- CLONE MARKET TEXT / COORDINATE / BOUNDARY RESIDUE = 0 / 0 / 0.
- No leakage from Weatherford, Waxahachie, Corsicana, Greenville, Sherman/Denison or Waco: each is a refused FUTURE_SUBMARKET or a refused county, with 0 admitted.
  - Denton graph nodes: 39, 0 admitted.
  - Rockwall graph nodes: 15, 0 admitted.

### Phase 13 — coverage decision
- **TECHNICAL SOURCE READY = YES.**
- **COVERAGE READY = FOUNDER DECISION.**
  - Every YES condition holds: actionable 0, Marriott actionable 0, no material gaps, cohorts exhausted or bounded, identity safety, the exclusions, a reproducible package, FAST all pass.
  - Two things block YES:
    - 25 rows can only be routed with NEW paid Places spend, a founder escalation under the order's own list.
    - 4 rows need a founder routing or naming ruling that is not one of the order's listed safe-hold kinds.
  - Nothing unsafe publishes in either case.

### Phases 14–16 — seal, FAST, memory, reproduction

| Item | Value |
|---|---|
| Package | `pkg-dallas-fort-worth-tx-e8a841396faeffec` |
| Package digest | `sha256:e8a841396faeffecd1e4b15d94fdde0949ac75e2729a80f0322be8c1bd768f9d` |
| Execution zone | SHADOW_UNTIL_REGISTERED |
| Sealed at | 2026-10-10T03:31:52Z (after the last capture, 03:21:46Z) |
| Built from source sha | `df4da832c4899e1659247519ef140b61fb029b25` |
| Work dir | `C:/t/dfw1` |
| FAST | 15/15 PASS, FAST_DATA_ONLY_RELEASE_ELIGIBLE = YES, receipt `821f46f2…` |
| Rule J | PASS: file_count 2,613 > 0, html_count 2,597 > 0, output present, bundle `8dd45272…` |
| Rule K | PASS: BYTE_IDENTICAL, 4 cold builds, 0 reuse hits |
| Receipt currently eligible | YES — `eligible_receipts(..., receipts_dir=shadow_receipts)` returns it |
| Seal/FAST process | exited by itself (exit 0); none was terminated |

**Reproduction:**
- **Setup.** Detached worktree `C:/t/dfwr` at `df4da832`, work dir `C:/t/dfw2`. It was never concurrent with the seal and was removed afterwards.
- **PACKAGE DIGEST MATCH = YES.** Both package files have SHA256 `A5F11AB6…`.
- **DATA DIFFERENCES = 0:** the staged input digest `df1b97f5…` and contract `60957a66…` are identical.
- **SITE DIFFERENCES = 0:** bundle `8dd45272…`, 2,613 files.
- **BYTE IDENTICAL = YES.**
- **Receipts:** they differ only in run timing, environment and timestamp fields. No rule status differs.

### Phase 18 — isolation and cleanup
- **Isolation counts:**
  - Cross-market file changes: 0.
  - Shared factory and shared policy-reader changes: 0. Only `dallas_fort_worth_tx_*` modules changed.
  - Current live changes: 0; deployment state changes: 0.
- **Processes:** every process this order started (pipeline, seal, reproduction, monitors) has exited. The pre-existing Python process 14180 and the older node processes were left alone.
- **Out of scope, noted only:** Jacksonville FL's live census also carries location-only Red Roof names ("Jacksonville Airport", "Jacksonville – Cruise Port"). It was not touched; it needs its own order.

---

## Timing (Phase 46)

| Measure | Value |
|---|---|
| START TIMESTAMP | 2026-10-09T14:00:14Z |
| ZERO_TO_SOURCE_READY | 14 h 41 m 42 s (to reproduction confirmed, 2026-10-10T04:41:56Z; FAST eligible at 04:28:08Z = 14 h 27 m 54 s) |
| ZERO_TO_COVERAGE_READY | not reached (FOUNDER DECISION) |
| ACTIVE COMPUTE TIME | ≈ 8 h 34 m (wall clock less the Marriott cooldowns; includes attended browser work) |
| PROVIDER / COOLDOWN WAIT | ≈ 6 h 08 m: Marriott cooldown 1 ≈ 3 h 00 m and cooldown 2 ≈ 3 h 08 m, plus throttled batches C/E |
| CENSUS TIME | ≈ 4 m 45 s per census pass. This continuation ran 6 full pipeline passes of ≈ 5 m each, plus a 2-build in-memory diagnostic. |
| ACQUISITION TIME | ≈ 1 h 00 m (start → first browser capture; census lanes, static, roster and Places). Not separately metered. |
| BROWSER TIME | 12 h 21 m 36 s wall (15:00:10Z → 03:21:46Z), of which ≈ 6 h 08 m was Marriott cooldown |
| SEAL TIME | 10 m 58 s seal + FAST (04:17:10Z → 04:28:08Z); seal alone ≈ 1 m 24 s |
| FAST TIME | 9 m 34 s (J build 316.8 s + K builds 257.2 s) |
| REPRODUCTION TIME | 12 m 30 s (04:29:26Z → 04:41:56Z) |

---

## FINAL ANSWERS

1. START TIMESTAMP = 2026-10-09T14:00:14Z
2. ZERO_TO_SOURCE_READY = 14 h 41 m 42 s (FAST eligible at 14 h 27 m 54 s)
3. ZERO_TO_COVERAGE_READY = NOT REACHED (COVERAGE READY = FOUNDER DECISION)
4. CURRENT LIVE DEPLOYMENT = 6ac8d0c021f9d04e6aa82455 (Fort Myers live; bundle aad66024)
5. CURRENT LIVE SOURCE COMMIT = 35a044135578f6bdf824baed92b14291910ac072 (built_from ab616e2e)
6. CURRENT LIVE MARKETS = 46 (4,430 profiles / 4,948 sitemap routes)
7. AUTOMATIC BASE DERIVES = YES (HEAD contains live = True)
8. DERIVED BASE = 35a044135578f6bdf824baed92b14291910ac072
9. TOTAL DISCOVERED = 5,673 observations
10. NORMALIZED IDENTITIES = 2,073
11. QUALIFYING CENSUS = 965
12. PET-FRIENDLY = 440
13. VERIFIED NO-PETS = 200
14. RESOLVED = 640
15. UNRESOLVED = 325
16. RESOLUTION RATE = 66.32%
17. ACTIONABLE UNRESOLVED = 0
18. HOLDS BY CLASS = ACCESS_BLOCKED 39, EVIDENCE_HOLD 50, IDENTITY_MISMATCH_HOLD 41, ROUTING_HOLD 146, SOURCE_SILENT 49. By actionability: AUTHORIZED_ROUTER_EXHAUSTED 275, REQUIRES_NEW_SPEND 25, REQUIRES_FOUNDER 21, HELD_UNTIL_OPENING 4, REQUIRES_NEW_PROVIDER 0, ACTIONABLE_NOW 0.
19. EXCLUSIONS BY CLASS = DUPLICATE_LISTING 10, IDENTITY_REVIEW_REQUIRED 462, NAME_ONLY_UNRESOLVED 144, NON_LODGING 127, OUTSIDE_MARKET 349, SAME_CAMPUS_DISTINCT_ENTITY 12, SAME_IDENTITY_REBRAND_SUCCESSOR 4
20. DALLAS COUNTY QUALIFYING = 437 (187 PF / 93 NP)
21. TARRANT COUNTY QUALIFYING = 350 (145 PF / 70 NP)
22. COLLIN COUNTY QUALIFYING = 129 (80 PF / 28 NP)
23. DENTON COUNTY QUALIFYING = 49 (28 PF / 9 NP)
24. DALLAS QUALIFYING = 205 (73 PF / 43 NP)
25. FORT WORTH QUALIFYING = 178 (66 PF / 36 NP)
26. DFW AIRPORT QUALIFYING = 10 (3 PF / 2 NP)
27. IRVING QUALIFYING = 96 (47 PF / 20 NP)
28. GRAPEVINE QUALIFYING = 17 (9 PF / 5 NP)
29. ARLINGTON QUALIFYING = 64 (30 PF / 14 NP)
30. PLANO QUALIFYING = 59 (34 PF / 14 NP)
31. FRISCO QUALIFYING = 29 (18 PF / 7 NP)
32. SUBURBAN HOTELS MISLABELED DALLAS = 0
33. SUBURBAN HOTELS MISLABELED FORT WORTH = 0
34. PREOPENING IDENTITIES = 4 (HELD_UNTIL_OPENING)
35. PREOPENING PUBLISHED = 0
36. CLOSED IDENTITIES = 13 map rows that Places reported closed (12 permanently, 1 temporarily), never admitted; plus 1 held row whose only route serves an error page
37. CLOSED PUBLISHED = 0
38. TIMESHARE / VACATION-OWNERSHIP IDENTITIES = 3 (identity reads excluded as timeshare)
39. TIMESHARE / VACATION-OWNERSHIP PUBLISHED = 0
40. PRIVATE APARTMENT / RESIDENCE IDENTITIES = 45 (33 non-hotel apartment inventory, 10 tourism=apartment map rows, 2 private cottage/house), plus 82 vacation-rental listings, all NON_LODGING
41. PRIVATE APARTMENT / RESIDENCE PUBLISHED = 0
42. DUAL-BRAND / SHARED-CAMPUS BUILDINGS = 7 dual-brand buildings (14 rows, safely held REQUIRES_FOUNDER) + 12 SAME_CAMPUS_DISTINCT_ENTITY rows (retained, not aliased)
43. FOUNDER-DECISION ROWS = 21 REQUIRES_FOUNDER (17 safely held + 4 routing/naming rulings) + 25 REQUIRES_NEW_SPEND; 29 of these gate coverage
44. PUBLISHING CORRIDORS = 26
45. COMPETITOR RAW / NORMALIZED / MATCHED / TRUE MISSING = 1,380 / 649 / 485 (459 distinct identities) / 22
46. MATERIAL IDENTITY GAP = NO
47. MATERIAL POLICY GAP = NO
48. FIRECRAWL ATTEMPTED / SUCCESS = 0 / 0 (60 credits = protected reserve; usable 0)
49. GOOGLE PLACES REQUESTS = 561 (215 Enterprise route discovery at its cap + 346 Pro; existing free capacity, $0)
50. MARRIOTT CENSUS = 166
51. MARRIOTT ATTEMPTED = 148 (139 distinct routes)
52. MARRIOTT READ SUCCESS = 137 (11 Akamai denials)
53. MARRIOTT ACTIONABLE REMAINING = 0 (38 terminal holds, 31 of them on the closed window, ref 18.8a89cc17.1791602447.af47e47)
54. OTHER BROWSER ATTEMPTED / SUCCESS = 654 / 510
55. SINGLE-BASIS FEES PUBLISHED = 63
56. TIERED FEES WITHHELD = 150
57. UNSAFE / MULTI-AMOUNT FEES WITHHELD = 47
58. MISLEADING SINGLE FEES = 0
59. PET-FRIENDLY WITH EXPLICIT REFUSAL = 0
60. QUESTION-ONLY PET-FRIENDLY = 0
61. SERVICE-ANIMAL-ONLY ACCEPTANCE = 0
62. EXISTING PROVIDER CREDITS USED = Firecrawl 0; Google Places 561 requests within the existing free allowance
63. NEW PAID SPEND = $0
64. PROVIDER COST = $0
65. CLONE MARKET TEXT RESIDUE = 0
66. CLONE COORDINATE RESIDUE = 0
67. CLONE BOUNDARY RESIDUE = 0
68. RULE J NONEMPTY = PASS (2,613 files / 2,597 html / output present)
69. RULE K NONVACUOUS = PASS (BYTE_IDENTICAL, 4 cold builds)
70. FAST RECEIPT CURRENTLY ELIGIBLE = YES
71. SHADOW PACKAGE = pkg-dallas-fort-worth-tx-e8a841396faeffec (SHADOW_UNTIL_REGISTERED)
72. PACKAGE REPRODUCIBLE = YES (in-process and independent detached worktree; byte identical)
73. PACKAGE DIGEST = sha256:e8a841396faeffecd1e4b15d94fdde0949ac75e2729a80f0322be8c1bd768f9d
74. FAST = 15/15 PASS, ELIGIBLE YES
75. TECHNICAL SOURCE READY = YES
76. COVERAGE READY = FOUNDER DECISION
77. CROSS-MARKET FILE CHANGES = 0
78. FACTORY CODE CHANGED = NO
79. SHARED READER CHANGED = NO
80. BROAD REGRESSION RUNS = 0
81. FINAL PRODUCTION CANDIDATE CREATED = NO
82. FOUNDER AUTHORIZATION CREATED = NO
83. DFW DEPLOYED = NO
84. origin == HEAD = YES
85. tree clean = YES

DALLAS-FORT WORTH SOURCE READY = YES
DALLAS-FORT WORTH COVERAGE READY = FOUNDER DECISION
ACTIONABLE UNRESOLVED = 0
SUBURBAN HOTELS MISLABELED DALLAS = 0
SUBURBAN HOTELS MISLABELED FORT WORTH = 0
PET-FRIENDLY RECORDS WITH EXPLICIT REFUSAL = 0
QUESTION-ONLY PET-FRIENDLY RECORDS = 0
SERVICE-ANIMAL-ONLY ACCEPTANCE = 0
PREOPENING PROFILES PUBLISHED = 0
TIMESHARE / VACATION-OWNERSHIP PROFILES PUBLISHED = 0
PRIVATE APARTMENT / RESIDENCE PROFILES PUBLISHED = 0
MISLEADING SINGLE FEES = 0
CLONE MARKET TEXT RESIDUE = 0
CLONE COORDINATE RESIDUE = 0
CLONE BOUNDARY RESIDUE = 0
RULE J NONEMPTY = PASS
RULE K NONVACUOUS = PASS
FAST = 15/15 PASS (ELIGIBLE)
FACTORY CODE CHANGED = NO
SHARED READER CHANGED = NO
BROAD REGRESSION RUNS = 0
DALLAS-FORT WORTH FINAL CANDIDATE = NO
DALLAS-FORT WORTH DEPLOYED = NO
WAITING FOR RELEASE QUEUE = YES
STOP.
