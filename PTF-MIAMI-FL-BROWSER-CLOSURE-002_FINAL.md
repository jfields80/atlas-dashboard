# PTF-MIAMI-FL-BROWSER-CLOSURE-002 — FINAL

Market `miami-fl`. Branch `worker/ptf-miami-fl-market-001`, worktree `C:\Atlas-Miami-FL-Hardened-V1`.
Sealed base: **d7756467** (PTF-MIAMI-FL-HARDENED-SOURCE-READY-001, `pkg-miami-fl-8f1ab377`).

A **targeted coverage-closure pass**, not a rebuild. The census was not rebuilt, discovery was not re-run, and no
completed Firecrawl work was repeated. The founder granted browser-extension read access for marriott.com,
hilton.com, hyatt.com and bestwestern.com; this order exercised that lane over the exact 116-row browser queue
SOURCE-READY-001 left, then stopped acquisition at the founder-bounded harvest (Option B) and sealed.

Status: **SHADOW_UNTIL_REGISTERED**. Nothing was registered, participated, authorized, pinned or deployed.

---

## 1. BEFORE vs AFTER

| Metric | Before (d7756467) | After | Δ |
|---|---:|---:|---:|
| Proposed census | 639 | **637** | −2 (two true duplicates merged, §4) |
| Pet-friendly | 57 | **118** | **+61** |
| Verified no-pets | 28 | **53** | **+25** |
| Resolved | 85 | **171** | **+86** |
| Unresolved | 554 | **466** | −88 |
| Resolution rate | 13.30 % | **26.84 %** | **+13.54 pts** |
| Corridors publishing | 3 | **10** | +7 |

### Holds by class

| Class | Before | After | Δ |
|---|---:|---:|---:|
| BROWSER_CAPTURE | 116 | **24** | **−92** |
| ACCESS_BLOCKED | 113 | 119 | +6 (Marriott challenge pages, §3) |
| ROUTING | 126 | 126 | 0 |
| SOURCE_SILENT | 124 | 125 | +1 |
| IDENTITY | 38 | 38 | 0 |
| EVIDENCE | 37 | 34 | −3 |
| NEGATION / POLICY_NOT_FOUND / MIXED_RESORT / CONDO_HOTEL / PAID / GEOGRAPHY / FOUNDER / OTHER | 0 | 0 | 0 |

### Corridors that changed

| Corridor | PF before → after | Publishes |
|---|---|---|
| downtown-brickell | 3 → 9 | no → **yes** |
| mid-beach | 2 → 7 | no → **yes** |
| airport-west-blue-lagoon | 3 → 7 | no → **yes** |
| midtown-wynwood-edgewater | 1 → 5 | no → **yes** |
| aventura | 0 → 5 | no → **yes** |
| kendall-south-dade | 2 → 5 | no → **yes** |
| homestead-florida-city | 3 → 7 | no → **yes** |
| doral | 6 → 15 | yes |
| mia-airport-miami-springs | 9 → 16 | yes |
| south-beach | 16 → 18 | yes |
| coral-gables | 0 → 4 | no (one short) |
| bal-harbour-surfside | 2 → 3 | no |

## 2. Phase 1–2 — the queue, and the domain canary

The queue was **reconstructed from the sealed base's own committed clean authority**, never from memory, and then
FROZEN as `miami_fl_browser_queue_002.json` so it could not shrink as this pass resolved rows.

**BROWSER QUEUE TOTAL = 116** — MARRIOTT 56, HILTON 44, HYATT 9, BEST WESTERN 7, OTHER 0. It reconciles exactly
against the base. Two Hilton rows are duplicates of rows that survive (§4), leaving **114 queue rows in the
current census**; the queue by family this pass worked is MARRIOTT 56, HILTON 42, HYATT 9, BEST WESTERN 7.

Canary, one representative property page per domain:

| Domain | Extension read access | Page readable | Challenge present |
|---|---|---|---|
| hilton.com | YES | YES | no |
| hyatt.com | YES | YES | no |
| bestwestern.com | YES | YES | no |
| marriott.com | YES | intermittently | **YES** — Akamai "Access Denied" / challenge page |

No challenge, CAPTCHA, anti-bot control or authentication was bypassed anywhere in this pass.

## 3. Phases 3–6 — the closure reads

| Family | Queue | Read | → PF | → No-pets | Held after reading | Challenge-denied | Not reached |
|---|---:|---:|---:|---:|---:|---:|---:|
| HILTON | 42 | **41** | 31 | 10 | 0 | 0 | 0 |
| HYATT | 9 | **8** | 8 | 0 | 0 | 0 | 0 |
| BEST WESTERN | 7 | **6** | 0 | 6 | 0 | 0 | 1 |
| MARRIOTT | 56 | **27** | 18 | 9 | 0 | 6 | 23 |
| **Total** | **114** | **82** | **57** | **25** | **0** | **6** | **24** |

The two non-reads that are not Marriott: **Hilton Cabana Miami Beach Resort** (a bespoke resort template that
serves no Hotel-policies panel → SOURCE_SILENT) and **Grand Hyatt Miami Beach** (an amenity chip "Pet Friendly"
and no policy section — an amenity chip is never a policy → SOURCE_SILENT). The one Best Western row not reached
routes to the brand's homepage, not a property page (ROUTING_HOLD, unchanged).

**Marriott (Phase 4).** marriott.com answered the authorized browser with its Akamai challenge repeatedly: after
roughly 17 rapid reads the brand rate-limited the session to about **one successful read per 20-minute window**,
and challenge pages were never bypassed. 27 of 56 were read. Six rows that met the challenge in this pass carry
**ACCESS_BLOCKED** with the measured blocker; the remaining 23 keep **BROWSER_CAPTURE_NEEDED** — the lane works,
it was simply not reached inside the founder-bounded harvest. No ACCESS_BLOCKED row was downgraded because the
browser had been tried.

**The founder-bounded harvest (Option B)** ran exactly the six corridor-impact targets authorized, in order:
JW Turnberry ✅, Residence Inn Surfside ✅, Residence Inn Sunny Isles ❌ (challenge ×3), Dua Miami ✅,
Marriott Stanton ✅, Moxy South Beach ❌ (challenge ×2). Acquisition stopped there; no full sweep was resumed.

**Binding (Phases 3, 5, 6).** Every read bound to its own premises, never to a partial address:

| Basis | Rows |
|---|---:|
| PROPERTY_CODE (the page's own code is the census row's) | 64 |
| BRAND_PAGE_NAME_AND_POSTAL | 11 |
| BRAND_PAGE_NAME_AND_FULL_STREET (page states no ZIP) | 5 |
| FULL_STREET_AND_POSTAL | 1 |
| BRAND_PAGE_FULL_STREET_AND_CITY (page states no ZIP) | 1 |
| **Unbound** | **0** |

A page that bound more than one census row would publish for none; after the duplicate merge (§4) no such case
remains. Hilton properties sharing a city, ZIP, campus or brand family never shared a policy: 42 Hilton rows
produced 41 distinct page bindings, 40 of them on the property's own `ctyhocn` code.

Every accepted read retains: requested URL, final URL, capture timestamp window, source domain, the page's own
name and full premises address, the binding basis, the operative quote (the page's own policy text nodes, in page
order), the quote's byte length, a TRANSCRIPTION_SHA256 over the canonical transcription, and its final
disposition — in `raw_captures/browser_closure_rows.json`, with this pass's raw reads committed beside it under
`raw_captures/browser_reads/`.

## 4. Defects this pass found and fixed

Six, each caught by real data and each fixed market-locally:

1. **Two census rows were one building.** "711 N.W 72nd Avenue" vs "711 NW 72nd Ave" (and the same for
   "2855 N.E 9th Street") — the dotted quadrant without a trailing dot split one hotel in two. The canonical
   street and the merge key now fold it: census 639 → **637**, and the two duplicate DoubleTree / Hampton rows
   became one each.
2. **A house number is five digits too.** The closure's postal reader took "12210" out of "12210 Biscayne
   Boulevard" as a ZIP and refused two correct Best Western bindings. It now reads a postal code only after the
   street segment.
3. **A truncated page heading is still the name.** The accessibility read cuts a long heading at ~41 characters;
   a heading that is a prefix of the census name (≥ 12 chars) now counts as the same name.
4. **A later read must supersede an earlier challenge.** Rows first met by a challenge and later read
   successfully were being frozen as ACCESS_BLOCKED by ingestion order (Aloft Aventura, JW Turnberry, Aloft
   Coral Gables). A READ now always wins: +4 published rows.
5. **"Maximum Pet Weight: 0.0lbs" is no stated limit**, not a zero-pound pet (Moxy Wynwood). Weights ≤ 0 are
   dropped.
6. **Two reader defects in the shared market-local readers**, both from this pass's own reads:
   *"Your pet is welcome, too" / "dog-friendly stays"* was not read as acceptance (Hyatt Centric Brickell and
   South Beach), and *"No pet fee"* was read as a refusal (Aloft Miami Brickell, whose page says "Pets Welcome").
   Fixing both lifted PF 111 → **118**.

## 5. Phase 7 — the four SOURCE-READY-001 invariants, re-tested

`miami_fl_closure_invariants_002.py`, run over this pass's own committed adjudication before sealing:

| # | Invariant | Result |
|---|---|---|
| 1 | Cross-property evidence attachment on a partial address | **PASS** — no published row cites a page another published row cites; 82 browser reads, 0 with no exact-premises binding |
| 2 | Weight text parsed as pet-count limit | **PASS** — "up to 25 lbs" yields no count |
| 3 | Ordinary amenity fee parsed as pet fee | **PASS** — amenity / destination / tax charges rejected; the pet amount wins |
| 4 | Route/host mismatch treated as valid evidence | **PASS** — 171 published rows checked, 0 published against an unrouted domain; the guard still refuses a synthetic foreign domain |

Negation safety is unchanged and still binding: 34 conflicts held, **0 rows published against a shared-reader
disagreement**.

## 6. Phases 8–9 — reclassification and full accounting

All 114 queue rows end in exactly one disposition; no row disappeared. Across the **whole 637-row census**:

PUBLISHED_PET_FRIENDLY 118 · VERIFIED_NO_PETS 53 · AWAITING_OFFICIAL_URL 126 · AWAITING_POLICY_OBSERVATION 159 ·
ACCESS_BLOCKED 119 · AWAITING_ATTENDED_CAPTURE 24 · AWAITING_ROUTING_REPLACEMENT 38. The partition contract
reports 0 issues and `uncorridored_rows` = 0.

Brand-by-brand after closure: HILTON 42 census → 31 PF / 10 NP / 1 unresolved; HYATT 9 → 8 / 0 / 1;
MARRIOTT 70 → 23 / 10 / 37; BEST WESTERN 8 → 0 / 6 / 2; IHG 27 → 9 / 5 / 13; CHOICE 14 → 3 / 1 / 10;
WYNDHAM 16 → 3 / 8 / 5; INDEPENDENT 397 → 29 / 13 / 355; LUXURY_INDEPENDENT 22 → 4 / 0 / 18.

## 7. Phase 10 — the non-browser unresolved audit

| Class | Remaining | Verdict | Why |
|---|---:|---|---|
| ROUTING_HOLD | 126 | EXHAUSTED_UNDER_CURRENT_ROUTER | no first-party route exists to read: Places route discovery bound no site at the row's own street + ZIP, or the only site named is a brand/OTA host another lane owns |
| SOURCE_SILENT | 125 | EXHAUSTED_UNDER_CURRENT_ROUTER | the property's own page served, bound to the identity, and states no operative pet policy |
| ACCESS_BLOCKED | 119 | EXHAUSTED_UNDER_CURRENT_ROUTER | every free and authorized lane attempted was refused (static, Firecrawl where the router made the row eligible, and — for brand rows — the authorized browser) |
| IDENTITY_MISMATCH_HOLD | 38 | REQUIRES_FOUNDER_DECISION | a page or site was read but never confirmed the row's premises; the identity, not the policy, is open |
| EVIDENCE_HOLD | 34 | REQUIRES_FOUNDER_DECISION | evidence exists but the safety rules refuse to publish it (fee/weight-only wording, shared-reader disagreement, route-domain conflict) |
| BROWSER_CAPTURE_NEEDED | **24** | **ACTIONABLE_NOW** | the authorized browser lane works for these rows; they were not reached inside the bounded harvest |

**REQUIRES_NEW_PROVIDER_OR_SPEND = 0.** No remaining row needs a provider this order is not authorized to use:
Marriott's own rate limiter, not a capability wall, bounds the 24 actionable rows, and they are reachable at
about one read per 20 minutes with no new spend.

## 8. Phase 11 — competitor recheck (no re-discovery)

The existing normalized reconciliation was re-run over the new dispositions; the 824-result discovery was not
repeated. 660 normalized unique leads: 282 matched (204 distinct census identities), 256 vacation rentals,
29 outside, 5 condo/residence, 3 non-hotel, 73 review, **12 TRUE_MISSING** — the same 12 verified in
SOURCE-READY-001 through Google Places, of which 8 were real at an admitted postal code (1 newly admitted, 4
already carried by the graph, 1 hostel, 1 apartment-hotel, 1 with no street) and 3 resolved outside the market.

**TRUE MISSING QUALIFYING IDENTITIES unresolved from the prior verified set = 0. MATERIAL IDENTITY GAP = NO.**
The remaining competitor-side policy gap is **123 matched-but-unresolved rows** (down from 170), every one of
which carries a §7 root cause — a bounded, explained gap, not an unexplained one.

## 9. Phase 12 — reseal, reproduction and FAST

| Item | Value |
|---|---|
| Source commit | `50a1a12c0d09d6a6871c1c4670e37d24eb8573fe` |
| Package | `pkg-miami-fl-81c54db348f08194` (supersedes `pkg-miami-fl-8f1ab377`) |
| PACKAGE DIGEST | `sha256:81c54db348f0819427598b8b9a05a38090ace9107df97dacfbb3cf739256ebdf` |
| Execution zone | SHADOW_UNTIL_REGISTERED |
| Receipt | `staging/miami-fl/shadow_receipts/miami-fl/pkg-miami-fl-81c54db348f08194-04a067d4ebc496c4.json` |
| FAST (A–O) | **15/15 PASS, 0 UNKNOWN, 0 FAILED**, `FAST_DATA_ONLY_RELEASE_ELIGIBLE = YES` |
| Declared public routes | 118 hotel profiles, 10 corridor pages, 1 comparison page, `/go/` affiliate pages; 0 warnings, 0 broken links, 0 quality-gate failures |
| REPRODUCTION A | this worktree, sealed twice in-process: identical digest |
| REPRODUCTION B | detached worktree `C:\t\mia5b` at the same commit, independent process: the whole deterministic chain (closure rows → clean authority → partition → staged policy package and authority) regenerated with **0 changed files**, then resealed to the same digest |
| BYTE IDENTICAL | **YES** |

A reproduction defect was found and fixed rather than reported around: the closure capture was first written as
`.jsonl`, which the repository's `eol=lf` attribute (scoped to `launch_packages/**/*.json` and `*.csv`) does not
cover, so a fresh checkout produced CRLF and the re-run produced LF — a one-file, content-identical difference.
The capture is now a `.json` array covered by the attribute, and reproduction B is unqualified.

## 10. Provider usage and isolation

- **Supported browser:** 82 reads (Hilton 41, Marriott 27, Hyatt 8, Best Western 6), 6 challenge-denied,
  24 not reached. Navigate + accessibility-tree reads only; no page script, no relay, no bypass.
- **FIRECRAWL RERUNS = 0. ADDITIONAL EXISTING PROVIDER CREDITS = 0** (credits unchanged at 1,346).
  **Google Places calls = 0. Bright Data = 0. NEW PAID SPEND = $0.00. New provider authorization = 0.**
- `git diff --name-only d7756467 HEAD`: **33 files, every one Miami-owned; 0 non-Miami paths.**
  CROSS-MARKET FILE CHANGES = 0 · SHARED FACTORY CODE CHANGES = 0 · CURRENT LIVE CHANGES = 0 ·
  DEPLOYMENT STATE CHANGES = 0 · BROAD REGRESSION RUNS = 0.
- **Cleanup:** reproduction worktrees `C:\t\mia3b`, `C:\t\mia4b`, `C:\t\mia5b` removed; scratch build dirs
  deleted; the browser tab group left with one tab, no background watcher, relay or HTTP server running.

## 11. Phase 13 — coverage decision

**MIAMI COVERAGE READY = NO.**

Mechanically, against the order's own eight criteria:

1. **Browser-actionable cohort completed or safely exhausted — NOT MET.** 82 of 114 rows were read; 24 remain
   ACTIONABLE_NOW on a lane that works. They were bounded by founder instruction, not by capability.
2. Remaining unresolved classes bounded — **met** (§7: every class has an exact, stated cause; 0 generic bucket).
3. Current authorized router exhausted where appropriate — **met** for ROUTING / SOURCE_SILENT / ACCESS_BLOCKED
   (370 rows); not applicable to the 24.
4. No material competitor identity gap — **met** (§8, 0 unresolved true-missing).
5. No material unexplained policy-acquisition gap — **met**; a bounded, explained gap of 466 rows remains.
6. Publication set safe — **met**: 4/4 invariants PASS, 34 conflicts held, 0 published against a disagreement,
   0 cross-property attachments, 0 unbound reads.
7. Package reproducible — **met** (§9, byte-identical).
8. FAST passes — **met** (15/15).

One criterion is unmet and it is a small, named, non-blocking one: **24 Marriott rows**, reachable at about one
read per 20-minute window under the brand's own rate limit, worth at most ~3.8 points of resolution rate and
likely one further corridor (coral-gables sits one pet-friendly short). The resolution rate itself (26.84 %) was
not used as the criterion in either direction.

---

## FINAL ANSWERS

1. **BROWSER QUEUE TOTAL** = 116 frozen from the sealed base (114 live in the current census after two duplicate merges; MARRIOTT 56 · HILTON 42 · HYATT 9 · BEST WESTERN 7 · OTHER 0)
2. **MARRIOTT QUEUE / READ / RESOLVED / REMAINING** = 56 / 27 / 27 (18 PF, 9 no-pets) / 29 (6 challenge-denied + 23 not reached)
3. **HILTON QUEUE / READ / RESOLVED / REMAINING** = 42 / 41 / 41 (31 PF, 10 no-pets) / 1 (Cabana: page serves no policy panel → SOURCE_SILENT)
4. **HYATT QUEUE / READ / RESOLVED / REMAINING** = 9 / 8 / 8 (8 PF) / 1 (Grand Hyatt: amenity chip only → SOURCE_SILENT)
5. **BEST WESTERN QUEUE / READ / RESOLVED / REMAINING** = 7 / 6 / 6 (6 no-pets) / 1 (route is the brand homepage, not a property page)
6. **OTHER BROWSER QUEUE** = 0
7. **NEW PET-FRIENDLY** = +61 (57 → 118)
8. **NEW VERIFIED NO-PETS** = +25 (28 → 53)
9. **TOTAL PET-FRIENDLY** = 118
10. **TOTAL VERIFIED NO-PETS** = 53
11. **TOTAL RESOLVED** = 171
12. **TOTAL UNRESOLVED** = 466
13. **RESOLUTION RATE** = 26.84 % (was 13.30 %)
14. **ROUTING REMAINING** = 126
15. **SOURCE_SILENT REMAINING** = 125
16. **BROWSER_CAPTURE REMAINING** = 24
17. **ACCESS_BLOCKED REMAINING** = 119
18. **IDENTITY REMAINING** = 38
19. **EVIDENCE REMAINING** = 34
20. **ACTIONABLE UNRESOLVED REMAINING** = 24
21. **MATERIAL POLICY GAP REMAINS** = NO unexplained gap; a bounded, explained gap of 466 rows, each with an exact cause (§7)
22. **COMPETITOR MATERIAL GAP** = NO (identity); 0 true-missing unresolved from the verified set; 123 matched-but-policy-unresolved, all §7-explained
23. **FIRECRAWL RERUNS** = 0
24. **ADDITIONAL EXISTING PROVIDER CREDITS** = 0 (Firecrawl unchanged at 1,346; Places calls 0)
25. **NEW PAID SPEND** = $0.00
26. **PACKAGE REPRODUCIBLE** = YES (0-file diff on a clean-worktree re-run, identical digest from an independent process)
27. **PACKAGE DIGEST** = `sha256:81c54db348f0819427598b8b9a05a38090ace9107df97dacfbb3cf739256ebdf`
28. **FAST** = 15/15 PASS (A–O), 0 UNKNOWN, 0 FAILED
29. **TECHNICAL SOURCE READY** = YES
30. **COVERAGE READY** = NO
31. **FACTORY CODE CHANGED** = NO
32. **BROAD REGRESSION RUNS** = 0
33. **FINAL PRODUCTION CANDIDATE CREATED** = NO
34. **MIAMI DEPLOYED** = NO
35. **origin == HEAD** = YES (verified after push, below)
36. **tree clean** = YES (verified after push, below)

MIAMI BROWSER CLOSURE = PASS
MIAMI SOURCE READY = YES
MIAMI COVERAGE READY = NO
ACTIONABLE UNRESOLVED = 24
FAST = 15/15 PASS
FACTORY CODE CHANGED = NO
BROAD REGRESSION RUNS = 0
MIAMI FINAL CANDIDATE = NO
MIAMI DEPLOYED = NO
WAITING FOR RELEASE QUEUE = YES

STOP.
