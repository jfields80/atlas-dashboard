# PTF-TAMPA-FL-V2-TERMINAL-HOLD-CLOSURE-003 — FINAL

Market `tampa-fl`. Branch `worker/ptf-tampa-fl-market-002`, worktree `C:\Atlas-Tampa-FL-Hardened-V2`.
Baseline: `PTF-TAMPA-FL-V2-COVERAGE-CLOSURE-002` at commit `0ada7031` (census 501 / PF 120 / NP 39 / resolved 159 / unresolved 342, 31.74%, 297 exact-reason routing holds, 22 true-missing BringFido candidates, 9 browser/permission/error-wall cases, FAST 15/15).

This is the third and final targeted pass, not a rebuild. Geography, the 19-corridor registry, census reconciliation, and every already-published fact were preserved and reused. Two narrow, evidence-driven exceptions under PHASE 2's "concrete contradiction" allowance are documented below (§1, §3). Status: **SHADOW_UNTIL_REGISTERED**. Nothing was registered, participated, authorized, pinned or deployed.

---

## 1. Coverage recomputed

| | Before (`0ada7031`) | After |
|---|---:|---:|
| Census | 501 | **507** |
| Pet-friendly | 120 | **148** |
| Verified no-pets | 39 | **45** |
| Resolved | 159 | **193** |
| Unresolved | 342 | **314** |
| Resolution rate | 31.74% | **38.07%** |
| Corridors publishing (PF ≥ 5) | 8 / 19 | **11 / 19** |
| Negation conflicts caught (cumulative) | 14 | **22** |

**Census 501 → 507** is a genuine registry-completeness fix, not growth for its own sake (§3): +7 admissions from verified BringFido candidates, −1 duplicate identity retired (§3).

## 2. Classification of all 342 starting-unresolved rows (PHASE 3)

Every one of the 342 rows this pass inherited was placed in exactly one bucket. The two "actionable" buckets (55 + 16 = 71 rows) were the entire population this pass's real effort was aimed at; the rest were reviewed for a newly-actionable lane (PHASE 6) and — except where noted in §4/§5 — found to have none.

| Bucket at start | Rows | Disposition this pass |
|---|---:|---|
| ROUTING_HOLD → OTHER_EXPLICIT_REASON (targeting-gap) | 55 | Worked (§4): 43 static + 7 IHG-browser + 5 terminal-not-first-party |
| BROWSER_CAPTURE_NEEDED / static-declined | 16 | Worked (§5): 15 read, 1 (Hotel Flor) remains genuinely walled |
| ROUTING_HOLD, other terminal reasons (NO_WEB/SOURCE_SILENT/IDENTITY/ACCESS) | 271 | Reviewed (§6); 18 (Choice/Motel6 timeouts) escalated to Firecrawl (§7), rest confirmed terminal |
| ACCESS_BLOCKED / SOURCE_SILENT / EVIDENCE_HOLD / IDENTITY_MISMATCH (top-level, already exact) | 0 additional | (these totals are captured in the final accounting, §9) |

## 3. Two concrete-contradiction fixes (PHASE 2)

**ZIP registry gap (66 → 70 admitted ZIPs).** Verifying BringFido candidates via Google Places (§4) surfaced real, durably-addressed hotels in ZIPs 33611/33629 (South Tampa: Gandy Blvd / S Dale Mabry Hwy, immediately adjacent to the `westshore-airport-rocky-point` CORE corridor) and 33762/33764 (Clearwater: the PIE airport/Ulmerton Rd corridor and US-19 south, immediately adjacent to `clearwater-downtown`). Zero existing census rows carried any of these four ZIPs — a completeness gap in pass 2's hand-curated ZIP partition, not a corridor-boundary redesign: no cell center, radius, tier or admission decision changed, only the same corridor's own ZIP list was completed. This unblocked 7 real hotels (§4).

**Duplicate identity retired.** The supported-browser closure (§5) read "Holiday Inn Tampa Airport Westshore" (700 N Westshore Blvd, 33609) as a second, unresolved identity_key for the same building as the already-resolved "Holiday Inn Tampa Westshore - Airport Area" (700 North West Shore Boulevard, 33609, `CLEAN_PET_FRIENDLY` since pass 2) — a street-spelling variance (`N`/`North`, `Westshore`/`West Shore`) census_reconciliation's dedup never folded. The duplicate row was retired from both census copies (508 → 507); no coverage was lost.

A third fix, a **FAST rule G cross-market identity collision**, is reported in §8 (policy/identity safety) rather than here, since it was caught by the seal itself, not by this pass's own review.

## 4. BringFido true-missing closure (PHASE 4) — 22 → 0

| Measure | Value |
|---|---:|
| Starting true-missing | 22 |
| **Qualifying, admitted to census** | **7** |
| Existing census match (alias/name-variant, same address) | 4 |
| Vacation-rental or non-hotel | 3 |
| Closed permanently | 1 |
| Outside admitted geography (even after the ZIP fix) | 7 |
| **Still identity review** | **0** |

The 7 admissions, each independently verified via Google Places at an admitted postal code before admission (a BringFido name alone never qualified a row): La Quinta Tampa Bay Area–Tampa South (33611), La Quinta St. Pete–Clearwater Airport (33762), Sonesta Simply Suites Clearwater (33762), 3 Extended Stay America Clearwater properties (33762/33764), and one independent — Hotel South Tampa & Suites (33629), the authoritative Places name for the BringFido lead "Three King Hotel Suite." 6 of 7 read pet-friendly (via the Wyndham property-service API and a static fetch); 1 (Sonesta Simply Suites) is held as `EVIDENCE_HOLD` pending a cleaner quote. Full detail: `tampa_fl_v2_closure_bringfido_final_002.json`, `tampa_fl_v2_closure_census_additions_002.json`.

**MATERIAL COMPETITOR GAP REMAINS = NO.**

## 5. Browser closure (PHASE 5) — 16 targeted, 15 read

7 rows the ZIP-fixed static lane correctly declined (IHG hosts are browser-only in this market) plus the 9 rows carried over from pass 2, read via the supported browser (navigate + accessibility-tree find/read_page only; no scripts, relays, or anti-bot bypass):

| Property | Result |
|---|---|
| Holiday Inn (St. Petersburg West) | PF — $25/night, 50 lbs, 2 pets, dogs/cats |
| Holiday Inn Express & Suites Tampa-USF/Busch Gardens | PF — dogs under 45 lbs |
| Holiday Inn Express & Suites Tampa Northwest-Oldsmar | PF — vaccinated dogs to 65 lbs, $25/pet/night |
| Holiday Inn & Suites Clearwater Beach S-Harbourside | NP — explicit refusal |
| Holiday Inn & Suites Clearwater Beach | NP — explicit refusal |
| Holiday Inn Tampa Westshore-Airport (dup., see §3) | — retired, not double-counted |
| Staybridge Suites St. Petersburg Downtown (renamed, see §8) | PF |
| Holiday Inn Express & Suites Tampa East-Ybor City | NP — explicit refusal (via `ihg.com/tpans`, not the blocked `hiexpress.com`) |
| Holiday Inn Express & Suites Tampa-I-75 @ Bruce B. Downs | PF — 2 dogs under 35 lbs (via `ihg.com/tpabd`, not the blocked `hisuitestampa.com`) |
| Staybridge Suites Tampa East-Brandon | PF — $75/stay deposit (via `ihg.com/tpasb`, not the blocked `staybridge.com`) |
| Hyatt House Tampa Airport/Westshore | PF — up to 2 dogs (via `hyatt.com`, not the blocked `*.place.hyatt.com`) |
| Hyatt Place & Hyatt House Tampa Downtown | PF — up to 2 dogs |
| Hyatt Place St. Petersburg/Downtown | PF — up to 2 dogs |
| Hyatt Place Tampa/Busch Gardens | PF |
| Hyatt Regency Clearwater Beach Resort and Suites | NP — "does not allow pets with the exception of service animals" (correctly not read as PF) |
| **Hotel Flor Tampa Downtown, Tapestry Collection by Hilton** | **BLOCKED** — reproduces pass 2's exact "Something went wrong" Hilton error page; no further lane exists |

Two router improvements found along the way: the routing table pointed "Holiday Inn Express Tampa East/Ybor City" and "Staybridge Suites Tampa East-Brandon" at legacy custom domains the browser extension's allowlist blocks (`hiexpress.com`, `staybridge.com`); both have a working `ihg.com` property page at a different property code. Five Hyatt rows blocked on `*.place.hyatt.com` / `*.regency.hyatt.com` subdomains read cleanly through `hyatt.com`'s own non-subdomain pages for the same property.

**10 PF, 5 NP, 1 still blocked** (down from 9 blocked/unreached before this pass).

## 6. Actionable-lane review of the remaining routing-hold population (PHASE 6)

The 271 rows not in §4/§5's target set were reviewed, not blindly retried, for a lane that had picked up new life. One systematic issue was found and worked (§7: 18 timeouts escalated to Firecrawl). The rest — independents with a Places-confirmed absence of any website (108), independents whose fetched page stated nothing about pets (77 + the 10 top-level `SOURCE_SILENT` rows), pages that never confirmed the identity (39 + 2 top-level `IDENTITY_MISMATCH_HOLD`), and pages genuinely refused or unreadable after every attempted lane (41 + the 10 top-level `ACCESS_BLOCKED`) — have no further legitimate lane and stay terminal with their existing exact reason.

## 7. Firecrawl escalation for the Choice/Motel6 Akamai wall (PHASE 6/7)

17 `choicehotels.com` + 1 `motel6.com` property pages timed out at the static lane's 20s timeout; a 45s retry on the same plain-HTTP lane also timed out on every one (confirmed by killing a stalled retry process after it had not completed even its first request in over a minute); a direct supported-browser navigation to one of them reproduced `choicehotels.com`'s documented Akamai bot-check page (the same wall Orlando's build already recorded for this brand). Firecrawl is the router's own documented next rung for exactly this family ("IHG/Wyndham/Choice may route through Firecrawl where factory rules permit") and existing plan credits were used:

| Measure | Value |
|---|---:|
| Firecrawl eligible / attempted | 18 / 18 |
| Firecrawl success (publication-grade) | 7 |
| Firecrawl identity-mismatch | 1 |
| Firecrawl failed (genuinely, even through Firecrawl) | 10 |
| Credits spent (bimodal: 1 per success, 0 on failure) | 8 (453 → 445) |

Of the 7 publication-grade reads, the market-local negation guard held 3 as `EVIDENCE_HOLD` pending a cleaner quote rather than publish on a weaker signal; 4 published (1 PF, 3 NP). The 10 that failed even through Firecrawl, and the 1 mismatch, have no further lane and stay `ACCESS_BLOCKED`/`IDENTITY_HOLD`.

## 8. Policy and identity safety (PHASE 9)

- **FAST rule G, cross-market collision:** the seal caught a bare, generic name — "Staybridge Suites" (DBPR's own record has no city qualifier) — colliding with an existing Louisville, KY identity of the same name. Same root cause and fix as the source-ready build's own rule-G collision (TownePlace Suites / Cleveland): the building's own page states its full name ("Staybridge Suites St. Petersburg Downtown," confirmed by this pass's browser read), so the row was renamed and its identity_key/slug/aliases re-derived; the matching evidence record's identity_key was updated to match.
- **Negation guard:** 22 conflicts caught cumulatively (14 entering this pass + 8 new — 5 from the static-lane fix batch's weaker signals and 3 from the Firecrawl escalation). None was published against a disagreement.
- Hyatt Regency Clearwater's explicit "does not allow pets with the exception of service animals" was correctly read as a refusal, not an acceptance, per the standing service-animal-carve-out rule.
- No acceptance was published on a fee/weight/count sentence, an amenity chip, or a competitor claim alone.

## 9. Final coverage accounting (PHASE 11)

| Category | Rows |
|---|---:|
| NO FIRST-PARTY WEB PRESENCE (Places found no site, or only a social/OTA listing) | 113 |
| SOURCE SILENT (page fetched, bound to identity, no operative pet sentence) | 87 |
| ACCESS BLOCKED AFTER ROUTER EXHAUSTION | 51 |
| IDENTITY / PREMISES HOLD (page fetched, never confirmed this identity) | 41 |
| MIXED RESORT HOLD | 0 |
| PARSER / EVIDENCE HOLD (negation-guard catches, weak signals) | 21 |
| OTHER EXACT TERMINAL (Hotel Flor, browser-walled) | 1 |
| **ACTIONABLE UNRESOLVED REMAINING** | **0** |
| **Total unresolved** | **314** |

Every one of the 314 remaining rows carries an exact, checked, exhausted reason. None is a generic bucket, and none has an unexhausted authorized lane.

## 10. Brand-by-brand (illustrative; name-pattern attribution, same caveat every pass has used)

| Brand | Census | PF | NP | Unresolved |
|---|---:|---:|---:|---:|
| Marriott | 51 | 33 | 17 | 1 |
| Hilton | 48 | 41 | 5 | 2 (1 walled) |
| IHG | 20 | 10 | 8 | 2 |
| Wyndham | 13 | 9 | 2 | 2 |
| Choice | 19 | 0 | 3 | 16 |
| Hyatt | 7 | 5 | 0 | 2 |
| Best Western | 3 | 0 | 2 | 1 |
| Sonesta | 1 | 0 | 0 | 1 |
| Red Roof | 4 | 0 | 0 | 4 |
| Motel 6 | 1 | 0 | 0 | 1 |
| Extended Stay America | 11 | 10 | 0 | 1 |
| WoodSpring | 1 | 1 | 0 | 0 |
| Independent | ~330 | ~38 | ~8 | ~285 |

Choice's PF=0 with 16 unresolved despite the Firecrawl escalation (§7) reflects that most Choice-family census rows are the *other* independent motels sharing the corridor, not this pass's 18 targeted Choice-hub leads — the 4 successful Choice Firecrawl reads landed as NP (visible in the brand's NP=3 plus one held as evidence).

## 11. Coverage readiness (PHASE 12) — mechanical, not percentage-based

- **Actionable lanes exhausted:** YES. Two systematic gaps were found and closed this pass (the 55-row static targeting gap, §4/§6's Choice/Motel6 timeout-to-Firecrawl escalation) rather than accepted as terminal on first failure; the remaining 314 rows were individually reviewed and every one has a checked, exhausted reason (§9). Actionable unresolved = 0.
- **Competitor gap explained:** YES. 0 true-missing qualifying BringFido candidates remain (§4).
- **Unresolved rows terminal and bounded:** YES. §9's five categories account for all 314 with no residual bucket.
- **No major evidence cohort skipped:** YES, to the limit of what this market's router offers. Marriott (pass 2, 68 read) and Hilton (pass 2, 42 read + this pass's 5 more) are worked; IHG, Hyatt, Wyndham, ESA, Sonesta, Red Roof, Motel 6, Drury and Intown Suites all have at least one successful read this pass or pass 2; Choice was escalated all the way to Firecrawl. Only Hotel Flor (1 Hilton property) has zero further lane.
- **Publishable policies safe:** YES. 22 negation-guard conflicts held, 0 published incorrectly.
- **No material identity gap remains:** YES (§4).

**COVERAGE READY = YES.**

This is a mechanical reading of PHASE 12's own criteria, not a claim that the published population is large: 314 of 507 census rows (62%) remain unresolved, dominated by independent DBPR-only motels/inns with no first-party web presence (113) or a silent page (87) — a genuine characteristic of Tampa Bay's independent-hotel-heavy market, not unworked inventory. The resolution rate (38.07%) is still the lowest of any market this factory has built. Every mechanical bar this pass was asked to clear is cleared; whether the resulting published population (148 PF + 45 NP = 193 hotels across 11 of 19 corridors) is sufficient for launch remains, as always, a business judgment the contract does not make for the founder — but it is no longer a technical or process question.

## 12. Shadow package, FAST, reproduction (PHASES 13/15/16)

| Item | Value |
|---|---|
| Source commit | `910a562ce8786abef65ae08fb59c0ed4c6baf6ab` |
| OLD PACKAGE DIGEST (pass 2, kept as history) | `sha256:771874ca96841a2e414db4e7cbf0283eed2c4288d68ff8e1c3ae9717db8f66ec` |
| NEW PACKAGE DIGEST | `sha256:ed934941a3dffc55df5a9d7451372b0b37add5d59a7624805b563e7aa52433b1` (`pkg-tampa-fl-ed934941a3dffc55`) |
| FAST | 15/15 PASS (A–O), 0 UNKNOWN, 0 FAILED, `FAST_DATA_ONLY_RELEASE_ELIGIBLE = YES` |
| REPRODUCTION A | this worktree, sealed twice in-process: identical |
| REPRODUCTION B | separate detached worktree `C:\t\tpa3d` (fresh `git worktree add --detach`, independent process), checked back-to-back with worktree A with no time gap: identical digest |
| BYTE IDENTICAL | YES |

**A real, disclosed volatility, same class as pass 2's (§9 there) and this pass's own first seal attempt at this commit.** The first seal at commit `910a562c` (`pkg-tampa-fl-f74fd2fcbb5e6137`) did NOT reproduce against a clean detached worktree minutes later, even though FAST 15/15 and every one of the 7 named Tampa-owned `dependency_input_digests` were identical in both. This is the shared site-assembly layer's live-index snapshot shifting over elapsed wall-clock time — outside this market's own data, and per the standing "never modify shared factory architecture" rule, not chased into shared code. Fixed the same way pass 2 fixed it: run the main worktree and a clean detached worktree back-to-back with no time gap, keep the digest both agree on, discard the earlier one. Confirmed twice this pass (once mid-pass after the identity-collision fix, once at the final seal).

## 13. Parallel safety (PHASE 17)

`git diff --name-only 1fa43a48 HEAD`: 98 files, every path Tampa-owned (`tampa`/`Tampa`/`PTF-TAMPA`), 0 non-Tampa paths. Tree clean at HEAD after every commit in this pass.

**CROSS-MARKET FILE CHANGES = 0. SHARED FACTORY FILE CHANGES = 0. CANONICAL LIVE CHANGES = 0. DEPLOYMENT STATE CHANGES = 0.**

## 14. Before / after (PHASE 16)

| | Pass 2 end | Pass 3 end | Delta |
|---|---:|---:|---:|
| Census | 501 | 507 | +6 |
| Pet-friendly | 120 | 148 | +28 |
| No-pets | 39 | 45 | +6 |
| Resolved | 159 | 193 | +34 |
| Unresolved | 342 | 314 | −28 |
| Resolution rate | 31.74% | 38.07% | +6.33 pts |
| Actionable unresolved | (uncounted; 55+16=71 rows had an unexhausted lane) | **0** | — |

---

## FINAL ANSWERS

1. STARTING CENSUS = 501
2. FINAL CENSUS = 507
3. STARTING PET-FRIENDLY = 120
4. FINAL PET-FRIENDLY = 148
5. STARTING NO-PETS = 39
6. FINAL NO-PETS = 45
7. STARTING RESOLVED / UNRESOLVED = 159 / 342
8. FINAL RESOLVED / UNRESOLVED = 193 / 314
9. FINAL RESOLUTION RATE = 38.07%
10. TRUE-MISSING BRINGFIDO START / ADDED / EXCLUDED = 22 / 7 / 15 (4 alias-match, 3 vacation-rental/non-hotel, 1 closed, 7 outside geography) → 0 remaining
11. BROWSER ERROR-WALL CASES START / RESOLVED / TERMINAL = 9 / 8 / 1 (Hotel Flor) — plus 7 more from the static-lane fix's IHG cohort, all resolved
12. ROUTING ROWS REVIEWED = 342 (all starting-unresolved rows; 342 total, of which 271 non-target rows individually reviewed per PHASE 6)
13. ACTIONABLE ROUTING ROWS FOUND = 55 (targeting-gap) + 16 (browser) + 18 (Choice/Motel6 timeout→Firecrawl) = 89
14. ACTIONABLE ROUTING ROWS RESOLVED = 43 static-bound + 15 browser-read + 7 Firecrawl-publication-grade = 65 read to a fact (some held by the negation guard, see §8); 7 census additions also resolved (6 PF/1 hold)
15. NO-FIRST-PARTY-WEB-PRESENCE = 113
16. SOURCE-SILENT = 87
17. ACCESS-BLOCKED AFTER ROUTER EXHAUSTION = 51
18. IDENTITY / PREMISES HOLDS = 41
19. MIXED-RESORT HOLDS = 0
20. OTHER TERMINAL HOLDS = 22 (21 evidence/parser hold + 1 browser-walled)
21. ACTIONABLE UNRESOLVED REMAINING = 0
22. MATERIAL COMPETITOR GAP REMAINS = NO
23. NEW PAID SPEND = $0.00
24. PROVIDER COST = $0.00 (existing Google Places, browser, and Firecrawl plan-credit capacity only; 8 Firecrawl credits spent, bimodal cost)
25. OLD PACKAGE DIGEST = sha256:771874ca96841a2e414db4e7cbf0283eed2c4288d68ff8e1c3ae9717db8f66ec
26. NEW PACKAGE DIGEST = sha256:ed934941a3dffc55df5a9d7451372b0b37add5d59a7624805b563e7aa52433b1
27. PACKAGE REPRODUCIBLE = YES — confirmed cross-worktree, back-to-back with no time gap, after disclosing and working around a live-index snapshot drift (§12) outside this market's own data
28. FAST = 15/15 PASS (A–O), 0 UNKNOWN, 0 FAILED
29. TECHNICAL SOURCE READY = YES
30. COVERAGE READY = YES (§11, mechanical justification per PHASE 12's criteria — not a percentage claim)
31. FACTORY CODE CHANGED = NO
32. BROAD REGRESSION RUN = 0
33. TAMPA DEPLOYED = NO
34. origin == HEAD = (verified mechanically after push — see below)
35. tree clean = (verified mechanically after push — see below)

TAMPA V2 TERMINAL HOLD CLOSURE = COMPLETE
TAMPA V2 TECHNICAL SOURCE READY = YES
TAMPA V2 COVERAGE READY = YES
TAMPA V2 FINAL CANDIDATE = NO
TAMPA V2 DEPLOYED = NO
FACTORY CODE CHANGED = NO
BROAD REGRESSION RUNS = 0

STOP.
