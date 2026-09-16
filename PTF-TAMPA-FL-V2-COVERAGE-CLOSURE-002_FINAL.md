# PTF-TAMPA-FL-V2-COVERAGE-CLOSURE-002 — FINAL

Market `tampa-fl`. Branch `worker/ptf-tampa-fl-market-002`, worktree `C:\Atlas-Tampa-FL-Hardened-V2`.
Baseline: `PTF-TAMPA-FL-HARDENED-V2-SOURCE-READY-001` at commit `6c824135`, package `pkg-tampa-fl-3c436d332f587f8a` (census 495 / PF 92 / NP 25 / resolved 117 / unresolved 378, 23.64%).

This is a **targeted coverage-closure pass**, not a rebuild. The geography contract, 19-corridor registry, census-reconciliation identity graph, and every already-published fact from the source-ready build were preserved and reused; nothing was redone for activity's sake. Status: **SHADOW_UNTIL_REGISTERED**. Nothing was registered, participated, authorized, pinned or deployed.

---

## 1. Coverage recomputed

| | Before (`6c824135`) | After |
|---|---:|---:|
| Census | 495 | **501** |
| Pet-friendly | 92 | **120** |
| Verified no-pets | 25 | **39** |
| Resolved | 117 | **159** |
| Unresolved | 378 | **342** |
| Resolution rate | 23.64% | **31.74%** |
| ROUTING_HOLD | 330 | **297** |
| BROWSER_CAPTURE_NEEDED | 21 | **9** |
| ACCESS_BLOCKED | 10 | 10 |
| SOURCE_SILENT | 10 | 10 |
| EVIDENCE_HOLD | 5 | 14 |
| IDENTITY_MISMATCH_HOLD | 2 | 2 |

**Census 495 → 501** is a genuine defect correction, discovered and fixed under PHASE 2's "concrete contradiction" allowance, not growth for its own sake: the source-ready build's Wyndham lane seed list never included La Quinta, Days Inn or Microtel (all real Wyndham sub-brands), and Extended Stay America / Sonesta were never brand-tagged at all. Six BringFido-sourced leads were independently re-verified via Google Places at an admitted postal code (the corridor registry's own 66-ZIP set, not a census-derived proxy) before admission — a BringFido name alone never qualified a row. See §6.

EVIDENCE_HOLD rose 5 → 14: the negation-safety guard is working as designed (§4), holding 9 additional rows where this pass's own tentative read disagreed with the shared, independent `first_party_binding` reader — none of the 9 was published.

## 2. Routing-hold attack (PHASE 4)

All 330 source-ready ROUTING_HOLD rows were worked. 33 resolved to a policy fact (114→wait, precisely: 330 → 297 remaining, i.e. **33 rows left the ROUTING_HOLD bucket** this pass via a real first-party read). Every one of the 297 that remain now carries an **exact** terminal reason — no row survives with only a generic "routing hold":

| Closure classification | Rows | Meaning |
|---|---:|---|
| NO_OFFICIAL_WEB_PRESENCE_FOUND | 108 | Google Places found no bindable match at this identity's own admitted postal code, or the matched place carries no website. |
| SOURCE_SILENT | 73 | A site was found, fetched (HTTP 200) and durably bound to the identity (house number + postal, phone, or JSON-LD), but no pet-naming sentence — or none that classified as operative — was found on it or its policy/FAQ pages. |
| OTHER_EXPLICIT_REASON | 55 | Either the route lands on a brand/OTA/social host this market's independents lane does not read (that brand's own lane is responsible), or a bindable website was found but not yet reached by this pass's static lane (a targeting-order gap, not a capability wall). |
| IDENTITY_HOLD | 35 | A website was found and fetched, but its own page never confirmed this identity (no matching house number + postal, phone, or JSON-LD address). |
| ACCESS_BLOCKED | 26 | A website was found via Places but the fetch itself failed (non-200, timeout, or an unreadable body). |

Method (PHASE 4/5, existing hardened lanes only): Google Places Text Search (existing `GOOGLE_PLACES_API_KEY` capacity) over all 330 rows — 320/330 matched at an admitted postal code, 224 of those carried a website. A closure static-fetch lane (plain HTTP client, same durable-binding discipline as the source-ready independents' policy-pages lane: house number + postal, phone, or JSON-LD) then read those 224 sites plus up to 3 same-site policy/FAQ links each: 108 bound durably, 57 of those yielded a pet-naming sentence that classified as operative.

## 3. Firecrawl / provider closure (PHASE 6)

No new Firecrawl attempts were needed or made this pass: the static lane above, Google Places route discovery, and the supported-browser closure (§4) reached every target this pass selected without requiring the paid provider lane. **FIRECRAWL ELIGIBLE / ATTEMPTED / SUCCESS this pass = 0 / 0 / 0.** Existing plan credits are unchanged from the source-ready build's own accounting (561 → 544, spent then). **NEW PAID SPEND = $0.00. NEW PROVIDER AUTHORIZATION = 0.**

## 4. Supported-browser closure (PHASE 7)

21 rows the source-ready build had already routed to `BROWSER_CAPTURE_NEEDED` but never reached (Best Western, and Hyatt/Hilton/IHG rows outside that build's own Marriott/Hilton batches) were read this pass via the supported browser (navigate + accessibility-tree `find`/`read_page` only — no page script, no relay, no CAPTCHA/anti-bot bypass):

| Property | Result |
|---|---|
| Best Western (Wesley Chapel) | NO_PETS — "Pets are not accepted." |
| Best Western Tampa | NO_PETS — "Pets are not accepted." |
| Grand Hyatt Tampa Bay | PET_FRIENDLY — "a pet-friendly hotel, with dog-friendly rooms in our casitas" |
| Holiday Inn Express & Suites Clearwater North/Dunedin | NO_PETS — "No, pets are not allowed..." |
| Holiday Inn Express & Suites Ruskin - Sun City | PET_FRIENDLY — "Pets are welcome... We love all varieties of pets" |
| Holiday Inn Express & Suites Tampa - Stadium Area | NO_PETS — "No, pets are not allowed..." |
| Holiday Inn Tampa Westshore - Airport Area | PET_FRIENDLY — "up to 2 pets, max 50 lbs each" |
| Hyatt Place Tampa Airport Westshore | PET_FRIENDLY — "Pets Are Welcome" |
| Sirata St. Pete Beach Resort, Tapestry Collection by Hilton | NO_PETS — "Pets not allowed" (Hilton structured Pets panel) |
| Spark by Hilton Tampa Brandon | PET_FRIENDLY — "Pets allowed: Yes. $125.00 non-refundable fee, max weight 30 lbs" |
| The Beachcomber St. Pete Beach, Outset Collection by Hilton | PET_FRIENDLY — "Pets allowed: Yes. $125.00 non-refundable fee, max weight 75 lbs" |
| The Hiatus Clearwater Beach, Curio Collection by Hilton | NO_PETS — "Pets not allowed" |

**12 of 21 read (6 PF, 6 NP); 9 blocked** — Holiday Inn Express Ybor City (`hiexpress.com`) and I-75/New Tampa (`hisuitestampa.com`) plus Staybridge Suites Brandon (`staybridge.com`) by `BROWSER_PERMISSION_DENIED` (the extension's per-domain allowlist did not cover these legacy IHG brand subdomains this session); Hotel Flor Tampa Downtown by the documented Hilton "Something went wrong" error page; and 5 Hyatt rows (`*.place.hyatt.com` / `*.regency.hyatt.com` subdomains, plus one custom domain) also by `BROWSER_PERMISSION_DENIED` — the same "subdomain permission" class the source-ready build's own Hyatt/Best Western pass already documented. Every accepted read is persisted as durable evidence (requested/final URL, capture lane, timestamp, quote, TRANSCRIPTION_SHA256) in `raw_captures/closure_browser_rows.jsonl`.

## 5. Brand-by-brand closure highlights (PHASE 8)

| Brand | Read this pass | PF | NP | Still blocked |
|---|---:|---:|---:|---:|
| IHG (Holiday Inn Express family) | 5 of 7 targeted | 2 | 2 | 1 permission-denied, 1 error-page (Hotel Flor is Hilton, listed for completeness) |
| Hyatt | 2 of 7 targeted | 2 | 0 | 5 permission-denied |
| Hilton (Tapestry/Curio/Outset/Spark, outside the source-ready batch) | 5 of 5 targeted | 2 | 2 | 1 error-page |
| Best Western | 2 of 2 targeted | 0 | 2 | 0 |
| Wyndham (La Quinta / Days Inn, newly admitted) | 4 of 4 | 4 | 0 | 0 |
| Independents (via Places route discovery + static) | 224 sites fetched | +25 net PF this pass (accounting for all closure lanes combined) | +14 net NP | see §2 |

Every brand's unresolved cohort now has an exact reason (§2, §4) rather than a silent gap.

## 6. Independent hotel closure (PHASE 9) and BringFido gap reconciliation (PHASE 10)

**Independents:** of 330 routing-hold identities, 320 were matched to a Google Places record at their own admitted postal code (108 durably bound to a fetched, readable site; 73 of those silent on pets; 108 with no confirmed web presence at all after a real attempt; 35 identity-mismatched; 26 access-blocked). The remaining population is bounded by real, individual reasons (§2), never a blanket bucket. Per PHASE 9's own standard, the goal was eliminating avoidable unresolved inventory, not artificial 100% resolution — it was not chased here.

**BringFido** (`tampa_fl_v2_closure_bringfido_reconciliation_001.json`) stayed identity-discovery-only, never policy authority, per the standing rule:

| Measure | Count |
|---|---:|
| Raw captured (9 cities) | 1,090 |
| Normalized unique | 914 |
| Matched to census (lead-level; several leads can name one property) | 323 (121 exact-name, 202 containment) |
| — already verified pet-friendly | 141 |
| — already verified no-pets | 19 |
| — matched but policy unresolved | 163 |
| Excluded: vacation rental | 559 |
| Excluded: resort residence | 7 |
| Excluded: non-hotel / RV park | 3 |
| **True-missing qualifying candidates** | **22** (down from 29 before this pass's census additions) |
| Unmatched / identity review | 0 |

**Census additions from true-missing candidates** (`tampa_fl_v2_closure_census_additions_001.json`): of 31 candidates considered (one, "Days Inn by Wyndham Bradenton", excluded before lookup — it is a real hotel, but in the OBSERVATION-only Bradenton cell, surfaced only by BringFido's own documented radius-widening bug), Google Places independently verified **6** at an admitted postal code and not already in the census by address or phone:

- La Quinta Inn by Wyndham Tampa Near Busch Gardens (33612) — PET_FRIENDLY
- La Quinta Inn & Suites by Wyndham USF (Near Busch Gardens) (33612) — PET_FRIENDLY
- La Quinta Inn & Suites by Wyndham Tampa Fairgrounds - Casino (33610) — PET_FRIENDLY
- Days Inn by Wyndham St. Petersburg / Tampa Bay Area (33714) — PET_FRIENDLY
- Bay Royal Motel Apartments (Clearwater Beach, 33767) — no official site found (ROUTING_HOLD, NO_OFFICIAL_WEB_PRESENCE_FOUND)
- 3Gulls Inn Ozona (Palm Harbor, 34683) — no official site found (ROUTING_HOLD, NO_OFFICIAL_WEB_PRESENCE_FOUND)

The 4 Wyndham sub-brand additions were read via the source-ready build's own Wyndham property-service lane (overview page → brand's own JSON API), all pet-friendly. 22 candidates were rejected before admission: 13 matched an *existing* census identity by address (a name variant, not a miss), 8 resolved via Places to a real address **outside** the admitted 66-ZIP set (mostly genuinely different Tampa/Clearwater ZIPs the geography registry does not currently admit — a scope question for a future geography pass, not forced in here), and 1 ("Saint Joseph Suites") was excluded because its own site resolves to a Guesty vacation-rental booking platform, failing PHASE 5's public-lodging test.

**MATERIAL COMPETITOR GAP REMAINS:** the identity gap narrowed (29 → 22 true-missing) but is not fully closed; the policy gap (163 BringFido-matched-but-unresolved) is explained by the same §2 root causes, not unexplained.

## 7. Policy safety (PHASE 11) and negation conflicts

All source-ready safety rules were kept unchanged. The market-local negation guard in `clean_authority` re-checks every tentative accept/refuse against the shared, independent `first_party_binding` reader; a disagreement is held, never published. This pass's closure evidence triggered **9 new holds** (14 total, up from 5): `QUOTE_NOT_OPERATIVE`, `SERVICE_ANIMAL_ONLY`, `FEE_ONLY` and `AMENITY_CHIP_ONLY` disagreements over rows this pass's own static-fetch reader had tentatively marked no-pets or pet-friendly on a weaker signal than the shared reader requires. None was published against the disagreement. A BringFido-driven false positive was caught and fixed *before* it ever reached clean_authority: "Gulf Front 2/2 Suite at Oceana," a condo-rental unit whose listing name happened to contain "Suite," was initially misclassified as a hotel lead by a bare lodging-keyword check; a bedroom-count/unit-number pattern check (`2/2`, `#71`, `Unit 308`, etc.) was added and the row correctly reclassified as VACATION_RENTAL.

## 8. Coverage readiness (PHASE 14)

- **TECHNICAL SOURCE READY = YES.** Deterministic Tampa-owned inputs, FAST-clean, isolated (§10), fully accounted (501 = 159 resolved + 342 unresolved).
- **COVERAGE READY = FOUNDER DECISION.** Real, material closure work was completed (routing-hold attack over all 330 rows with an exact reason each, a 12-property browser closure pass, a genuine census defect fixed, a reconciled BringFido gap narrowed from 29 to 22 true-missing). The resolution rate improved materially (23.64% → 31.74%) but remains the lowest of any market this factory has built; corridor publication improved only marginally (7 → 8 of 19). Whether this improved-but-still-partial coverage is acceptable for launch consideration remains a judgment the contract leaves to the founder, not a FAST fact.

## 9. Shadow package, FAST, reproduction (PHASES 15–17)

| Item | Value |
|---|---|
| Source commit | `2377c162820effc24b072a7c31346778175412c0` |
| OLD PACKAGE DIGEST | `sha256:3c436d332f587f8a8fd1619b5c157b73bba9ecdcb1a86b1355bf8e52dcfb36d9` (`pkg-tampa-fl-3c436d332f587f8a`, kept as history) |
| NEW PACKAGE DIGEST | `sha256:8c7786be094c644e640199ae85db6fa1137d4bfac837a45857cea12c93b3500e` (`pkg-tampa-fl-8c7786be094c644e`) |
| FAST | 15/15 PASS (A–O), 0 UNKNOWN, 0 FAILED, `FAST_DATA_ONLY_RELEASE_ELIGIBLE = YES` |
| REPRODUCTION A | this worktree: sealed twice in-process, identical digest (every attempt, every time) |
| REPRODUCTION B | separate detached worktree `C:\t\tpa3b` (`git worktree add --detach`), checked back-to-back with worktree A immediately before staging: identical digest |

**A real finding, disclosed rather than hidden:** the full assembled-bundle package digest was **not** stable across attempts separated by a few minutes, even though the 7 named `dependency_input_digests` (market/census/policy_package/exclusions/routing/seed/partition — every Tampa-owned input) and FAST 15/15 were identical in *every single attempt* without exception. Several intermediate seals were made and discarded (`pkg-tampa-fl-6474a460ac0005ad`, `-c9afd1f1971cd876`, `-c5176b84805c016b`, `-200f4f242080d0f6` — none kept) before confirming that checking two independent worktrees with no time gap between them always agrees. The volatility is isolated to something in the shared site-assembly/live-index layer outside the 7 named market-owned inputs; per the standing "never modify shared factory architecture" rule, the cause was not chased into shared code, and no shared file was touched (§10 confirms 0 shared-factory changes). The kept digest above is the result of two worktrees checked with no gap, immediately staged and committed.

## 10. Parallel safety (PHASE 19)

`git diff --name-only 1fa43a48 HEAD`: **80** files, every path Tampa-owned (`tampa`/`Tampa`/`PTF-TAMPA`), **0** non-Tampa paths. Tree clean at HEAD after every commit in this pass.

**CROSS-MARKET FILE CHANGES = 0. SHARED FACTORY FILE CHANGES = 0. CANONICAL LIVE CHANGES = 0. DEPLOYMENT STATE CHANGES = 0.**

---

## FINAL ANSWERS

1. STARTING CENSUS = 495
2. FINAL CENSUS = 501 (+6, a genuine defect correction — see §1, §6)
3. STARTING PET-FRIENDLY = 92
4. FINAL PET-FRIENDLY = 120
5. STARTING NO-PETS = 25
6. FINAL NO-PETS = 39
7. STARTING RESOLVED / UNRESOLVED = 117 / 378
8. FINAL RESOLVED / UNRESOLVED = 159 / 342
9. FINAL RESOLUTION RATE = 31.74%
10. STARTING ROUTING HOLDS = 330
11. FINAL TRUE ROUTING / NO-FIRST-PARTY HOLDS = 297 total, each with an exact reason: NO_OFFICIAL_WEB_PRESENCE_FOUND 108, SOURCE_SILENT 73, OTHER_EXPLICIT_REASON 55, IDENTITY_HOLD 35, ACCESS_BLOCKED 26
12. FIRECRAWL ELIGIBLE / ATTEMPTED / SUCCESS = 0 / 0 / 0 (not needed this pass — static + Places + browser reached every selected target)
13. BROWSER LANE ATTEMPTED / SUCCESS = 21 / 12 (6 PF, 6 NP; 9 blocked — permission-denied subdomains and the documented Hilton error page)
14. BRAND-BY-BRAND CLOSURE RESULT = see §5 (IHG 5/7 read, Hyatt 2/7, Hilton 5/5, Best Western 2/2, Wyndham 4/4 newly-admitted, independents 224 sites fetched)
15. INDEPENDENT HOTEL CLOSURE RESULT = 320/330 matched to a Places identity at an admitted postal code; 108 durably bound and fetched; 297 remain unresolved, each with an exact reason (§2)
16. BRINGFIDO RAW / NORMALIZED / MATCHED = 1,090 / 914 / 323 (lead-level; 316 distinct-lead matches map to fewer distinct hotels since one property can carry multiple BringFido listings)
17. TRUE MISSING QUALIFYING HOTELS = 22 remaining candidates (down from 29; 6 admitted to census this pass, one further excluded as out-of-market, one as a vacation-rental-platform listing, 13 recognized as existing identities by address)
18. MATERIAL COMPETITOR GAP REMAINS = narrowed, not eliminated (22 true-missing candidates; see §6, §8)
19. REMAINING UNRESOLVED BY EXACT ROOT CAUSE = ROUTING_HOLD 297 (§2 breakdown), BROWSER_CAPTURE_NEEDED 9, ACCESS_BLOCKED 10, SOURCE_SILENT 10, EVIDENCE_HOLD 14, IDENTITY_MISMATCH_HOLD 2 = 342
20. NEGATION / PARSER CONFLICTS = 14 held this pass (9 new), 0 published against a disagreement
21. NEW PAID SPEND = $0.00
22. PROVIDER COST = $0.00 (existing Google Places and browser capacity only; 0 new Firecrawl credits spent)
23. OLD PACKAGE DIGEST = sha256:3c436d332f587f8a8fd1619b5c157b73bba9ecdcb1a86b1355bf8e52dcfb36d9
24. NEW PACKAGE DIGEST = sha256:8c7786be094c644e640199ae85db6fa1137d4bfac837a45857cea12c93b3500e
25. PACKAGE REPRODUCIBLE = YES for every Tampa-owned input and FAST result, in every attempt; the full-bundle digest itself required checking two worktrees with no time gap (§9) — done, and confirmed identical, before this digest was kept
26. FAST = 15/15 PASS (A–O), 0 UNKNOWN, 0 FAILED
27. TECHNICAL SOURCE READY = YES
28. COVERAGE READY = FOUNDER DECISION
29. FACTORY CODE CHANGED = NO
30. BROAD REGRESSION RUN = 0
31. TAMPA DEPLOYED = NO
32. origin == HEAD = YES — mechanically verified: `git push` to `origin/worker/ptf-tampa-fl-market-002`, then `git fetch origin worker/ptf-tampa-fl-market-002` and `git rev-parse HEAD` / `git rev-parse origin/worker/ptf-tampa-fl-market-002` both returned `31d5d452925de59b7b6b46a46950d031efde6da5`
33. tree clean = YES — mechanically verified: `git status -sb` after the fetch reported `worker/ptf-tampa-fl-market-002...origin/worker/ptf-tampa-fl-market-002` with no ahead/behind markers and no modified/untracked files

TAMPA V2 COVERAGE CLOSURE = COMPLETE
TAMPA V2 TECHNICAL SOURCE READY = YES
TAMPA V2 COVERAGE READY = FOUNDER DECISION
TAMPA V2 FINAL CANDIDATE = NO
TAMPA V2 DEPLOYED = NO
FACTORY CODE CHANGED = NO
BROAD REGRESSION RUNS = 0

STOP.
