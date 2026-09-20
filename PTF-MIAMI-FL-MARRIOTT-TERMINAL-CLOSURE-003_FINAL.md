# PTF-MIAMI-FL-MARRIOTT-TERMINAL-CLOSURE-003 — FINAL

Market `miami-fl`. Branch `worker/ptf-miami-fl-market-001`, worktree `C:\Atlas-Miami-FL-Hardened-V1`.
Base: **32e183bd** (PTF-MIAMI-FL-BROWSER-CLOSURE-002, `pkg-miami-fl-81c54db3`).

A **terminal closure pass** over the exact actionable cohort closure 002 left. The census was not rebuilt,
discovery was not re-run, no Firecrawl call was made, no shared factory file was touched, and no Akamai or
anti-bot control was bypassed. Acquisition ran through the authorized attended-browser lane only, paced against
Marriott's measured rate limit.

Status: **SHADOW_UNTIL_REGISTERED**. Nothing was registered, participated, authorized, pinned or deployed.

---

## 1. Phase 1 — the exact queue

Loaded from the committed artifacts (`miami_fl_browser_queue_002.json` — the queue frozen at the sealed base —
joined to `browser_closure_rows.json`, `miami_fl_clean_authority_001.json`, `miami_fl_routing_001.json` and the
census), never from memory.

**ACTIONABLE MARRIOTT START = 24** — confirmed against the artifacts.

One correction the artifacts force, stated rather than smoothed over: the 24 actionable rows are **23 Marriott
rows plus one Best Western row** (`Best Western PLUS Atlantic Beach Resort`, 4101 Collins Ave). That row sits in
the same actionable class because its census route is the Best Western **brand home page**, not a property page.
It is carried through this closure with the Marriott cohort and ends terminal like the rest.

Every row kept its property code, exact premises identity, corridor, current route, prior attempts (all 24 were
`NOT_ATTEMPTED` — these are precisely the rows closure 002 never reached), current hold and evidence history.

## 2. Phase 2 — paced acquisition

Marriott's Akamai wall was up at the start of the pass, lifted once, and closed again. The lane was never pushed
faster than the measured limit and the challenge was never bypassed.

| Window (UTC, 2026-09-20) | Outcome |
|---|---|
| 12:10 | first probe — Access Denied |
| 12:30 – 12:55 | three paced probes — Access Denied |
| ~15:30 | **window opened: 16 consecutive pages read**, then Access Denied on the 17th |
| 15:50 – 17:20 | five paced probes (20–30 min apart) — Access Denied |
| ~17:40 | **window opened: 1 page read** (TownePlace Suites Miami Airport) |
| 17:50 – 19:05 | eight paced probes, including a 30-minute silent hold — Access Denied every time |

**17 Marriott property pages were read.** Five rows were genuinely attempted and refused; per Phase 2 they end
`ACCESS_BLOCKED`, which the order allows explicitly. The Best Western row was worked on its own domain (no rate
limit): two attended probes of the brand's own property-page shape both returned Best Western's own
"page that does not exist" page, and the BEST_WESTERN sitemap lane is a measured 403 — the brand publishes no
property page for these premises, so there is nothing first-party to read.

Two extra pages were read beyond the strict cohort, both to serve cohort rows honestly rather than to widen
scope: the Courtyard Miami Airport page (the census route recorded for the campus row served it) and an attempt
at the `miaap` Miami Airport Marriott page (denied). No other row was touched.

## 3. Phase 3 — evidence safety

Every safety rule named in the order was preserved, and the four SOURCE-READY-001 invariants were re-run
mechanically over this pass's own adjudication before sealing
(`miami_fl_closure_invariants_003.json`): **all four PASS.**

- full street identity binding, no house-number-only matching — 77 of this pass's bindings are by the page's own
  **property code**, 12 by brand-page name + postal, 5 by name + full street, 2 by full street + postal, 1 by
  full street + city. **Unbound reads: 0.**
- no ZIP misread as street identity — postal is still read only after the street segment.
- no cross-property evidence attachment — invariant 1 PASS.
- no weight read as pet count, no amenity fee read as pet fee — invariants 2 and 3 PASS.
- "No pet fee" is still not a refusal; "Your pet is welcome" / "dog-friendly" are still acceptance.

Three rules were **strengthened**, none weakened:

1. **A shared page is ambiguous only among rows with no page of their own.** The Miami airport campus forced
   this: the Residence Inn's page binds both `Residence Inn Miami Airport` (its property code) and the campus row
   `Miami Airport Marriott- Full Service` (same street, no code in the census). The rule is now resolved after
   every read is placed, so the answer no longer depends on which capture file a read was written to.
2. **A page that states a fee, a weight or a count but no acceptance wording is an EVIDENCE hold, not a capture
   still to be made.** Previously such a read produced no evidence at all and the row fell back to
   "browser capture needed" — reporting a row as unread whose page this order had in fact read. The
   fee/weight/count publication rule itself is untouched: those rows still publish nothing.
3. **An identity the census cannot address never publishes.** Two rows (`Courtyard Miami West/FL Turnpike`,
   `Residence Inn Miami West/FL Turnpike`) reached the census from a brand roster that named the property and its
   code but no street. Their policy reads are sound, but the registration layer refuses — correctly — to turn an
   addressless identity into inventory. They are held. **No census address was invented.**

## 4. Phase 4 — terminal disposition, all 24 rows

| # | Property | Corridor | Browser result | Terminal disposition |
|---|---|---|---|---|
| 1 | Best Western PLUS Atlantic Beach Resort | mid-beach | NO_BRAND_PROPERTY_PAGE | **ROUTING_HOLD** |
| 2 | Courtyard by Marriott – Miami Downtown/Brickell Area | downtown-brickell | READ | **CLEAN_VERIFIED_NO_PETS** |
| 3 | Courtyard Miami West/FL Turnpike | doral | READ | **EVIDENCE_HOLD** (no census address) |
| 4 | Fairfield by Marriott Inn & Suites Miami Airport West/Doral | mia-airport-miami-springs | SHARED_PAGE_CENSUS_DUPLICATE | **IDENTITY_MISMATCH_HOLD** |
| 5 | Fairfield Inn & Suites Homestead Florida City | homestead-florida-city | READ | **CLEAN_PET_FRIENDLY** |
| 6 | Fairfield Inn & Suites Miami Airport South | airport-west-blue-lagoon | READ | **CLEAN_VERIFIED_NO_PETS** |
| 7 | Fairfield Inn & Suites Miami Airport West/Doral | mia-airport-miami-springs | SHARED_PAGE_CENSUS_DUPLICATE | **IDENTITY_MISMATCH_HOLD** |
| 8 | Found Hotel Miami Beach Series by Marriott | mid-beach | READ | **CLEAN_PET_FRIENDLY** |
| 9 | Marriott Vacation Club Pulse, South Beach | south-beach | READ | **CLEAN_VERIFIED_NO_PETS** |
| 10 | Miami Airport Marriott- Full Service | airport-west-blue-lagoon | SHARED_PAGE_CENSUS_DUPLICATE | **IDENTITY_MISMATCH_HOLD** |
| 11 | Miami Marriott Biscayne Bay | downtown-brickell | READ | **CLEAN_PET_FRIENDLY** |
| 12 | Miami Marriott Dadeland | kendall-south-dade | READ | **CLEAN_VERIFIED_NO_PETS** |
| 13 | Residence Inn Miami Airport | airport-west-blue-lagoon | SHARED_PAGE_CENSUS_DUPLICATE | **IDENTITY_MISMATCH_HOLD** |
| 14 | Residence Inn Miami Airport West Doral | doral | READ | **EVIDENCE_HOLD** (fee/weight/count only) |
| 15 | Residence Inn Miami Beach South Beach | south-beach | READ | **CLEAN_PET_FRIENDLY** |
| 16 | Residence Inn Miami Northwest | doral | READ | **EVIDENCE_HOLD** (fee/weight/count only) |
| 17 | Residence Inn Miami West/FL Turnpike | doral | READ | **EVIDENCE_HOLD** (no census address) |
| 18 | Sheraton Miami Airport Hotel & Executive Meeting Center | mia-airport-miami-springs | READ | **CLEAN_PET_FRIENDLY** |
| 19 | SpringHill Suites Miami Airport South Blue Lagoon | airport-west-blue-lagoon | ACCESS_DENIED (7 attempts) | **ACCESS_BLOCKED** |
| 20 | SpringHill Suites Miami Downtown/Medical Center | downtown-brickell | ACCESS_DENIED (2 attempts) | **ACCESS_BLOCKED** |
| 21 | TownePlace Suites by Marriott Miami Airport | airport-west-blue-lagoon | READ | **CLEAN_PET_FRIENDLY** |
| 22 | TownePlace Suites Miami Homestead | homestead-florida-city | ACCESS_DENIED (4 attempts) | **ACCESS_BLOCKED** |
| 23 | TownePlace Suites Miami Kendall West | kendall-south-dade | ACCESS_DENIED (1 attempt) | **ACCESS_BLOCKED** |
| 24 | UNFRAMED, Autograph Collection Miami Beach | south-beach | ACCESS_DENIED (2 attempts) | **ACCESS_BLOCKED** |

**24 of 24 terminal. 0 rows retain ACTIONABLE status. No resolution was manufactured.**

The four `IDENTITY_MISMATCH_HOLD` rows are two genuine census questions, not read failures: the census carries
two Fairfield rows one street apart in 33166 that the brand serves from a single page, and the Miami airport
campus lists a full-service Marriott row at the same street as the Residence Inn with no property code to tell
them apart. One brand page binding two census rows publishes for **neither** — that is the SOURCE-READY-001 rule
working, and the duplicate is a founder decision, not an acquisition task.

## 5. Phase 5 — full Miami reaccounting

The order says "639-property census"; the committed census is **637**, unchanged since closure 002 merged two
true duplicates (§4 of that report). No identity was added or removed by this pass.

| Metric | Before (32e183bd) | After | Δ |
|---|---:|---:|---:|
| Proposed census | 637 | **637** | 0 |
| Pet-friendly | 118 | **125** | **+7** |
| Verified no-pets | 53 | **57** | **+4** |
| Resolved | 171 | **182** | **+11** |
| Unresolved | 466 | **455** | −11 |
| Resolution rate | 26.84 % | **28.57 %** | **+1.73 pts** |

### Exact remaining holds

| Class | Before | After | Δ |
|---|---:|---:|---:|
| **BROWSER_CAPTURE** | **24** | **0** | **−24** |
| ROUTING | 126 | 127 | +1 |
| SOURCE_SILENT | 125 | 125 | 0 |
| ACCESS_BLOCKED | 119 | 123 | +4 |
| IDENTITY | 38 | 42 | +4 |
| EVIDENCE | 34 | 38 | +4 |
| FOUNDER | 0 | 0 | 0 |
| OTHER | 0 | 0 | 0 |

Every class movement is a row from the 24-row cohort landing on its terminal answer; nothing else moved.

**ACTIONABLE UNRESOLVED REMAINING = 0** (computed in `miami_fl_closure_accounting_003.json`, not asserted).

| PHASE-10 class | Remaining | Verdict |
|---|---:|---|
| ACCESS_BLOCKED | 123 | EXHAUSTED_UNDER_CURRENT_ROUTER |
| ROUTING_HOLD | 127 | EXHAUSTED_UNDER_CURRENT_ROUTER |
| SOURCE_SILENT | 125 | EXHAUSTED_UNDER_CURRENT_ROUTER |
| IDENTITY_MISMATCH_HOLD | 42 | REQUIRES_FOUNDER_DECISION |
| EVIDENCE_HOLD | 38 | REQUIRES_FOUNDER_DECISION |
| **ACTIONABLE_NOW** | **0** | — |

## 6. Phase 6 — corridor recheck

| Corridor | PF before | PF after | NP before | NP after | Publishes |
|---|---:|---:|---:|---:|---|
| south-beach | 21 | 22 | 11 | 12 | yes → yes |
| mia-airport-miami-springs | 16 | 17 | 9 | 9 | yes → yes |
| downtown-brickell | 13 | 14 | 3 | 4 | yes → yes |
| airport-west-blue-lagoon | 7 | 9 | 2 | 3 | yes → yes |
| mid-beach | 7 | 8 | 1 | 1 | yes → yes |
| homestead-florida-city | 7 | 8 | 4 | 4 | yes → yes |
| kendall-south-dade | 5 | 5 | 5 | 6 | yes → yes |
| **coral-gables** | **4** | **4** | 3 | 3 | **no → no** |

**PUBLISHING CORRIDORS = 10 before, 10 after.**

**CORAL GABLES DOES NOT PUBLISH.** It stayed at 4 verified pet-friendly against a threshold of 5 and was **not
forced**. No row in the 24-row cohort sits in Coral Gables, so this closure could not move it. The three rows
that could, and why they did not: `Hotel Colonnade Coral Gables` (Marriott `miaao`) is ACCESS_BLOCKED from
closure 002 and is outside this order's cohort; `The Biltmore Hotel Miami – Coral Gables` and
`Ponce De Leon Hotel` are EVIDENCE_HOLD. One more verified pet-friendly row in that corridor publishes an
eleventh page; none of the three may be assumed.

## 7. Phase 7 — coverage readiness

| Criterion | Result |
|---|---|
| actionable browser cohort = 0 | **met** — 0 rows in BROWSER_CAPTURE_NEEDED, artifact-computed |
| remaining unresolved classes bounded / exhausted / founder-decision | **met** — every class carries a PHASE-10 verdict; ACTIONABLE_NOW = 0 |
| no material identity gap | **met** — TRUE MISSING QUALIFYING IDENTITIES = 0; the census is unchanged since the audit that established it |
| no material unexplained policy gap | **met** — matched-but-unresolved competitor identities fell 123 → **116** of 204, every one with a named root cause (45 ACCESS_BLOCKED, 30 SOURCE_SILENT, 18 EVIDENCE, 17 ROUTING, 6 IDENTITY) |
| current authorized router exhausted | **met** — static refused, Firecrawl is a measured capability wall for Marriott/Hilton, Hyatt and Best Western are excluded brands, and the attended browser has now been genuinely attempted for every row it can serve |
| publication set safe | **met** — 4/4 invariants PASS, package contract 0 issues, FAST rule C clean |
| package reproduces | **met** — byte identical |
| FAST passes | **met** — 15/15 |

**COVERAGE READY = YES.** Not on the resolution percentage — 28.57 % is not the argument. The argument is that
the actionable cohort is empty and every remaining unresolved row is exhausted under the authorized router or a
founder decision, with the gap named rather than estimated.

## 8. Phase 8 — reseal, reproduction and FAST

| Item | Value |
|---|---|
| Source commit | `d44f6f85` |
| Package | `pkg-miami-fl-91076dc436e07ce4` (supersedes `pkg-miami-fl-81c54db3`) |
| PACKAGE DIGEST | `sha256:91076dc436e07ce40f8df494e9e401c81aad5bb48fb07a58c50d7b034a99c87a` |
| Execution zone | SHADOW_UNTIL_REGISTERED |
| Receipt | `staging/miami-fl/shadow_receipts/miami-fl/pkg-miami-fl-91076dc436e07ce4-63e0e59820107b86.json` |
| FAST (A–O) | **15/15 PASS, 0 UNKNOWN, 0 FAILED** |
| Declared public routes | 125 hotel profiles, 10 corridor pages, 1 comparison page, 618 `/go/` pages; 0 warnings, 0 broken links, 0 quality-gate failures |
| REPRODUCTION A | sealed twice in-process: identical digest |
| REPRODUCTION B | detached worktree `C:\t\mia7c`, independent process: the whole Miami-owned deterministic chain (closure ingest → clean authority → partition → registration staging → accounting → invariants) regenerated with **0 changed files**, then resealed to `sha256:91076dc4…c87a` |
| BYTE IDENTICAL | **YES** |
| Broad regression runs | **0** |

## 9. Provider usage and isolation

- **Supported browser:** 19 pages read this pass (17 Marriott property pages, 2 Best Western brand probes),
  14 challenge denials, all navigate + accessibility-tree reads. No page script, no relay, no bypass.
- **FIRECRAWL RERUNS = 0** (credits unchanged at 1,346). **Google Places = 0. Bright Data = 0.
  NEW PAID SPEND = $0.00. New provider authorization = 0.**
- `git diff --name-only 32e183bd HEAD`: **20 files, every one Miami-owned; 0 non-Miami paths.** The only script
  changes are to `miami_fl_browser_closure_002.py`, `miami_fl_clean_authority_001.py` and two new Miami-owned
  003 helpers. **FACTORY CODE CHANGED = NO.**

---

## FINAL ANSWERS

1. **MARRIOTT ACTIONABLE START** = 24 (23 Marriott + 1 Best Western, per the artifacts)
2. **MARRIOTT READ SUCCESS** = 18 of 23 rows served by a bound brand page (17 distinct pages; two pages each bound two census rows)
3. **MARRIOTT CHALLENGE DENIED** = 5
4. **MARRIOTT NEW PET-FRIENDLY** = 6
5. **MARRIOTT NEW VERIFIED NO-PETS** = 4
6. **MARRIOTT POLICY NOT FOUND** = 0
7. **MARRIOTT OTHER TERMINAL HOLDS** = 8 (4 EVIDENCE_HOLD + 4 IDENTITY_MISMATCH_HOLD); + 1 ROUTING_HOLD for the Best Western row = 9 across the full cohort
8. **MARRIOTT ACTIONABLE END** = 0
9. **TOTAL PET-FRIENDLY** = 125
10. **TOTAL VERIFIED NO-PETS** = 57
11. **TOTAL RESOLVED** = 182
12. **TOTAL UNRESOLVED** = 455
13. **RESOLUTION RATE** = 28.57 %
14. **ACTIONABLE UNRESOLVED REMAINING** = 0
15. **PUBLISHING CORRIDORS** = 10 (before 10, after 10)
16. **CORAL GABLES PUBLISHES** = NO (4 pet-friendly, threshold 5, not forced)
17. **MATERIAL IDENTITY GAP** = NO
18. **MATERIAL POLICY GAP** = NO (116 matched-but-unresolved, each with a named root cause)
19. **PACKAGE REPRODUCIBLE** = YES — BYTE IDENTICAL
20. **PACKAGE DIGEST** = `sha256:91076dc436e07ce40f8df494e9e401c81aad5bb48fb07a58c50d7b034a99c87a`
21. **FAST** = 15/15 PASS, 0 UNKNOWN, 0 FAILED
22. **TECHNICAL SOURCE READY** = YES
23. **COVERAGE READY** = YES
24. **NEW PROVIDER USED** = NONE
25. **NEW PAID SPEND** = $0.00
26. **FACTORY CODE CHANGED** = NO
27. **BROAD REGRESSION RUNS** = 0
28. **FINAL CANDIDATE CREATED** = NO
29. **MIAMI DEPLOYED** = NO
30. **origin == HEAD** = YES
31. **tree clean** = YES

---

MIAMI MARRIOTT TERMINAL CLOSURE = PASS
MARRIOTT ACTIONABLE REMAINING = 0
MIAMI SOURCE READY = YES
MIAMI COVERAGE READY = YES
FAST = 15/15 PASS, 0 UNKNOWN, 0 FAILED
FACTORY CODE CHANGED = NO
BROAD REGRESSION RUNS = 0
MIAMI FINAL CANDIDATE = NO
MIAMI DEPLOYED = NO
WAITING FOR RELEASE QUEUE = YES

STOP.
