# PTF-SAN-DIEGO-CA-HARDENED-SOURCE-READY-001 — FINAL

**San Diego / Coastal San Diego County, California** (`san-diego-ca`), built from zero to a market-local, independently
reproduced SHADOW package on the Jacksonville-live lineage. Worktree `C:\Atlas-San-Diego-CA-Hardened-V1`, branch
`worker/ptf-san-diego-ca-market-001`. Not registered, not authorized, not deployed.

| | |
|---|---|
| Shadow package | `pkg-san-diego-ca-919c1f7f8e8aa060` (`sha256:919c1f7f8e8aa060d845b0b4c44b2aac356e6d62a09137446f431a3143bc81af`), SHADOW_UNTIL_REGISTERED |
| Sealed from | `d1168e6c` (every staged input committed) |
| FAST | **15/15 PASS**, 0 UNKNOWN, 0 FAILED; receipt `sha256:c053f608…8668` |
| Rule J (non-empty) | PASS — 881 files, 865 HTML, output present, 0 output defects, bundle `9d07caac…6ffb` |
| Rule K (non-vacuous) | PASS — BYTE_IDENTICAL, 4 cold builds executed, 0 reuse hits |
| Independent reproduction | detached worktree, separate process, separate work dir: same package id/digest, same bundle, every rule identical; staged tree re-derived, **FILES COMPARED 8, DIFFERING FILES 0** |
| Census / published | 431 identities; **147 pet-friendly + 92 verified no-pets** = 239 resolved; 192 unresolved |
| Actionability | **ACTIONABLE UNRESOLVED 0**; 52 router-exhausted, 130 new spend, 10 founder |
| Coverage | **FOUNDER DECISION** (mechanical; see §9) |

## 1. Lineage and current live (Phase 1–2)

Started 2026-09-25T21:15:18Z on `c6d9f5bd` (tip of `origin/worker/ptf-jacksonville-fl-market-001`; the guard commits
f182cc08 / e59883f7 and the release-factory integration 0b6ad264 are ancestors). CURRENT VERIFIED LIVE (resolved
mechanically, host verified): Jacksonville — deploy `6ab6c8798bd9daf5038ae3e5`, source `e9a059e5`, built_from
`e7e02d43`, bundle `f82f0714…`, sitemap `d34b0e5d…`, 34 markets / 2,519 profiles / 2,807 release-index routes /
2,874 served routes. The shadow package's `parent_live_state` names that release; FAST rule N will fail it BY DESIGN
once any later market goes live — the registration order re-seals the same committed inputs as a new package id.

Commits on this branch: `5ea592a9` staged inputs → `0df549d6` staged policy package + shard documents (operator-
authorized `registration_staging --write`) → `d1168e6c` the fix the first FAST run measured → `f805840b` shadow
package → this report.

## 2. Geography (Phases 3–6)

20 corridors over 76 ZIPs, membership by the property's OWN postal code (`classify_postal`), never by name:
11 CORE (Downtown/Gaslamp/Waterfront, Point Loma/Shelter Island/Airport, Old Town/Midway, Mission Valley/Hotel
Circle, Ocean Beach, Mission & Pacific Beach, La Jolla, UTC/Golden Triangle/Sorrento, Uptown/Hillcrest/North Park,
Kearny Mesa/Clairemont, College Area/Mission Gorge), 7 CORRIDOR (Coronado, Del Mar/Solana Beach, Encinitas/Cardiff,
Carlsbad, Oceanside, South Bay/Chula Vista, Rancho Bernardo/Poway/I-15), 2 FRINGE (East County I-8,
Escondido/San Marcos/Vista). OUTSIDE by prefix: 922 (Palm Springs/Coachella), 925 (Riverside/Temecula), 926–928
(Orange County), 900–918 (Los Angeles), Mexico, military ZIPs, and SD County's rural north/backcountry/Borrego.
Coastal roles A–L recorded; FUTURE standalone markets named (temecula-valley-ca, orange-county-ca, palm-springs-ca,
north-county-coast optionality). Uncorridored admitted rows: **0**.

| corridor | class | census | PF | NP | unresolved | page publishes |
|---|---|---:|---:|---:|---:|---|
| downtown-gaslamp-waterfront | CORE | 78 | 31 | 12 | 35 | yes |
| point-loma-shelter-island-airport | CORE | 14 | 6 | 3 | 5 | yes |
| old-town-midway | CORE | 19 | 6 | 7 | 6 | yes |
| mission-valley-hotel-circle | CORE | 30 | 10 | 10 | 10 | yes |
| ocean-beach | CORE | 4 | 0 | 0 | 4 | no |
| mission-pacific-beach | CORE | 23 | 6 | 1 | 16 | yes |
| la-jolla | CORE | 21 | 8 | 0 | 13 | yes |
| utc-golden-triangle-sorrento | CORE | 8 | 6 | 1 | 1 | yes |
| uptown-hillcrest-north-park | CORE | 7 | 0 | 1 | 6 | no |
| kearny-mesa-clairemont | CORE | 9 | 3 | 2 | 4 | no |
| college-area-mission-gorge | CORE | 12 | 2 | 2 | 8 | no |
| coronado | CORRIDOR | 14 | 3 | 1 | 10 | no |
| del-mar-solana-beach | CORRIDOR | 19 | 7 | 4 | 8 | yes |
| encinitas-cardiff | CORRIDOR | 8 | 1 | 3 | 4 | no |
| carlsbad | CORRIDOR | 39 | 19 | 3 | 17 | yes |
| oceanside | CORRIDOR | 26 | 10 | 10 | 6 | yes |
| south-bay-chula-vista | CORRIDOR | 39 | 5 | 17 | 17 | yes |
| rancho-bernardo-poway-i15 | CORRIDOR | 16 | 11 | 3 | 2 | yes |
| east-county-i8 | FRINGE | 25 | 5 | 7 | 13 | yes |
| escondido-san-marcos-vista | FRINGE | 20 | 8 | 5 | 7 | yes |

14 corridor pages publish (each builds and links cleanly in FAST J: 0 warnings, 0 broken internal links).

### County / border audit (Phase 23)

| refused place | discovered | admitted |
|---|---:|---:|
| Orange County | 63 | **0** |
| Riverside County / Temecula | 28 | **0** |
| Palm Springs / Coachella | 8 | **0** |
| Mexico / Tijuana | 6 | **0** |
| Los Angeles | 0 | 0 |
| SD County refused places (Fallbrook, Ramona, Julian, Borrego, Camp Pendleton…) | 17 | **0** |

Rows admitted from a refused postal code: **0**.

## 3. Owned data, census lanes and exclusions (Phases 7–13)

Owned data first: 0 owned San Diego identities, 71 owned routes, 6,927 live identity names loaded for the
cross-market collision pass; 13 Firecrawl ledgers (972 calls) held 0 San Diego pages. Census lanes (raw observations
2,260): City of San Diego business-tax register 41 hotel leads (355 STR certificates and 20 rooming houses counted,
never admitted), OSM (Geofabrik SoCal extract after all three Overpass mirrors returned 504) 594, brand inventories
285 (owned 70, Hilton city pages 72, sitemaps 143), bureaux 87 (Visit Carlsbad, Visit Oceanside; sandiego.org 403 to
the plain client), competitor leads 948, Places-verified gap identities 14, property pages 291. Graph 1,468 nodes →
**431 admitted**. Exclusions: vacation rental 116, timeshare 9 (incl. Grand Pacific Palisades, MarBrisa HGV Club,
Club Wyndham Harbour Lights), non-hotel 125, outside 104, name-only residue 636, identity-review residue 47.
Cross-market live-identity collisions published: **0** (held rows carry CROSS_MARKET_LIVE_IDENTITY_COLLISION).

## 4. Acquisition (Phases 14–16)

* **Static plain client**: 187 targets, 46 new free requests (pay-once cache), VALID 7, ACCESS_DENIED 102.
* **Wyndham property service**: 72 routes, 36 read, 36 retired (redirect to brand search). Its own addresses now
  feed the census as tier-1 identity (fixed La Quinta Carlsbad's ZIP; moved the Days Inn Chula Vista route to
  394 Broadway).
* **Firecrawl** (existing credits, cap on attempts, floor 400): route discovery 12 pages / 66 routes (11 credits),
  brand pages 48 attempted / 35 answered (62 credits), routed pass 43 attempts / 5 publication-grade. Total
  **≈77 credits** (1,074 → ~997). USD 0.
* **Places** (existing key): gap verification only, PRO mask, 38 requests (16 verified missing → carried into the
  census, 12 already present, 9 no lodging, 1 outside). **Route discovery NOT run**: websiteUri is Enterprise-SKU and
  the month's free allowance is consumed — new spend, not authorized (renews 2026-10-01).
* **Attended browser** (claude-in-chrome; navigate + accessibility read; no JS exfiltration, no relay, no bypass,
  no CAPTCHA solved): 210 attempts.

| family | read | other outcomes |
|---|---:|---|
| Marriott | 69 | 5 Akamai denials (window ends), 3 no-statement, 3 REJECTED_OUT_OF_MARKET (cnmfi/cnmts Carlsbad **NM**, aunsh Auburn) |
| Hilton | 54 | 1 timeshare-excluded, 1 accordion not exposed |
| Choice | 23 | — (Akamai interstitial clears itself in ~18 s; never clicked) |
| Best Western | 14 | 1 conditional, 1 no property page |
| Hyatt 6, Sonesta 3(+1 silent), Omni 2, Loews 1, ESA 1 | 13 | ESA 1 DataDome CAPTCHA (never solved) |
| IHG | 0 | 1 no operative statement, 2 accordion not exposed |
| Independents | 2 | 5 silent, 4 error pages, 2 no statement, 1 lands on brand portfolio |
| Motel 6 | 0 | 3 amenity chip only |

**Marriott closure**: 6 paced windows (W4 17 reads, W5 20, W6 clean after a 96-min rest). MARRIOTT ACTIONABLE
REMAINING = **0** (69 census rows: 45 PF, 22 NP, 2 held — both dual-brand at 900 Bayfront Ct).

## 5. Policy and evidence rules (Phases 16–18)

Acceptance never from a fee, a weight, a count or an amenity chip; refusal never from silence; "No pet fee" is not a
refusal; weight never becomes a count. **30 stay-length / multi-part fees withheld** (acceptance and limits publish,
the single fee does not). **Conditional weights withheld** (7 rows, e.g. "1 dog 50 lbs, 2 dogs combined 75 lbs").
Every published quote passes the shared first-party reader (FAST rule C, gate 239/239). One disposition per row;
every hold carries its reason (0 holds without a reason).

## 6. Defects found and fixed in this market's own modules

1. **Marriott CNM = Carlsbad, New Mexico** — cnmts had joined San Diego's TownePlace Carlsbad/Vista by name. CNM
   dropped from the lead filter; the census refuses any brand lead whose own page states an out-of-market address.
2. **Unanchored `hotels\.com`** in the router rejected every choicehotels.com / wyndhamhotels.com route (inherited
   from the Jacksonville module — recorded, not touched).
3. **"Pets Allowed: No" read as acceptance** (label-value form missing from the refusal pattern) — 17 Choice
   refusals were held by the shared reader; now resolved as NO_PETS.
4. **Duplicate identities**: Myers/Meyers St (one Oceanside resort) and a 92008/92011 ZIP split (Fairfield
   Carlsbad) — merged; the census now refuses to write a duplicate identity key or brand code.
5. **Conditional weight published as one number** (San Diego Marriott La Jolla) — caught by the first FAST run
   (rule C FAIL on `pkg-san-diego-ca-b5751351`); weight withheld when a quote states more than one (§5).
6. Route precedence: the route of a page actually read outranks a roster route; a route whose own read states other
   premises is detached; evidence prefers the read that cites the bound route (Days Inn Oceanside, Days Inn Hotel
   Circle resolved).
7. IHG's comma-less address shape; browser reads with no address bind by their census route (non-publishing only);
   actionability rewritten per ROW (the Florida port bucketed whole dispositions and hid routed-but-unattempted rows).
8. Inherited backspace bytes in the nonhotel STR regex (also present in JAX/Miami/FLL/WPB — recorded, not touched).

## 7. Competitor challenge (BringFido — audit lane only, never policy)

23 SD cities, 1,254 raw / 948 unique: exact 129, alias 24, duplicate 69, vacation rental 461, review 225, non-hotel
9, outside 7, **true missing 24** — Places-verified: 16 at admitted ZIPs (carried in), 12 already present, 9 no
lodging, 1 outside. No material unexplained identity gap.

## 8. Actionability (Phase 21, per row)

| disposition | total | actionable | exhausted | new spend | founder |
|---|---:|---:|---:|---:|---:|
| ROUTING_HOLD | 138 | 0 | 8 | 130 | 0 |
| SOURCE_SILENT | 23 | 0 | 23 | 0 | 0 |
| EVIDENCE_HOLD | 14 | 0 | 14 | 0 | 0 |
| IDENTITY_MISMATCH_HOLD | 11 | 0 | 1 | 0 | 10 |
| ACCESS_BLOCKED | 6 | 0 | 6 | 0 | 0 |
| **total** | **192** | **0** | **52** | **130** | **10** |

* **130 new spend**: no first-party route in any authorized lane (brand inventories, three bureau rosters, the map,
  the brands' own area lists — e.g. Choice's own Chula Vista / Carlsbad area lists omit 9 de-flagged "Choice" rows).
  The only lane that finds a website is Places websiteUri (Enterprise SKU, allowance consumed). Left exactly as
  classified; Places not used before the 2026-10-01 renewal.
* **10 founder**: five dual-brand buildings (2424 Fenton Pkwy, 2137 Pacific Hwy, 1357 5th Ave, 900 Bayfront Ct,
  1500 Orange Ave) — each half proved by its own brand code and page; publishing them needs a
  same_campus_distinct_entity row in the SHARED identity_resolutions.json. **Left held.**
* The sandiego.org bureau serves the attended browser (136 lodging members) but its paginated list froze the
  renderer twice and its URL search returns nothing; bounded, not looped.

## 9. Coverage decision (Phase 26)

All eight coverage conditions are true (actionable 0; no material identity or unexplained policy gap; lanes
exhausted; Marriott closed; browser brands bounded; publication set safe; package deterministic and FAST clean). The
coverage contract still returns **FOUNDER DECISION** mechanically: 140 unresolved rows are reachable only through new
spend (130) or a founder ruling (10). Nothing is manufactured from ACTIONABLE = 0.

## 10. Reproduction (Phase 27)

Detached worktree `C:/t/sd1b-wt` at `f805840b`, separate OS process (process record written before start:
`reproduction/independent_reproduction_process.txt`), work dir `C:/t/sd1b`, staged tree re-derived with `--stage`.
Same package id and digest, bundle `9d07caac…`, all 15 rules PASS, DETERMINISM BYTE_IDENTICAL, ELIGIBLE YES.
Staged tree: **FILES COMPARED 8, DIFFERING FILES 0**. Receipt fields compared 1,052; the only differences are wall-clock
seconds, peak working set, the cache `input_key` (hashes the work-dir path; both runs `BUILD_EXECUTED`) and hence the
receipt digest (`c053f608…` vs `623ac2b7…`). The package document on disk in the worktree was the committed copy (the
writer leaves an identical file alone); the independent proof of the package is the reproduction process's own
two-seal digest. Worktree removed afterwards.

## 11. Isolation, boundaries and cleanup (Phases 29–33)

Changed paths since `c6d9f5bd`: San Diego-owned only (scripts `san_diego_ca_*`, config, reports `san_diego_ca_*`,
`markets/staging/san-diego-ca/`, proposed census/market, this report). **0 shared, 0 cross-market, 0 live, 0 deploy
paths.** Not registered, no founder or deployment authorization, no production candidate, no whole-site build,
participation / pin / identity_resolutions untouched, 0 broad regression runs, USD 0, no new provider. Browser tab
closed; no timers, watchers, servers or child workers remain.

Machine-readable accounting: `markets/reports/san_diego_ca_source_ready_accounting_001.json` (source, provider,
brand, corridor, competitor, boundary), `san_diego_ca_actionability_001.json` (per row), `san_diego_ca_shadow_package_001.json`,
`markets/staging/san-diego-ca/reproduction/`.

## FINAL ANSWERS

1. Lineage verified: YES — c6d9f5bd, guard commits ancestors.
2. Current live: Jacksonville, deploy 6ab6c8798bd9daf5038ae3e5, 34 / 2,519 / 2,807 / 2,874.
3. Market: san-diego-ca, San Diego / Coastal San Diego County, California.
4. Corridors: 20 (11 CORE, 7 CORRIDOR, 2 FRINGE), 76 ZIPs.
5. Corridors publishing: 14.
6. Uncorridored admitted rows: 0.
7. Owned identities reused: 0 (71 owned routes).
8. Raw observations: 2,260.
9. Graph nodes: 1,468.
10. Census admitted: 431.
11. Pet-friendly published: 147.
12. Verified no-pets published: 92.
13. Resolved: 239 (55.45 %).
14. Unresolved: 192.
15. ACTIONABLE UNRESOLVED: 0.
16. Router-exhausted: 52.
17. Requires new spend: 130 (Places websiteUri).
18. Requires new provider: 0.
19. Requires founder: 10 (dual-brand buildings, held).
20. Marriott actionable remaining: 0 (69 census rows: 45 PF / 22 NP / 2 dual-brand held).
21. Attended-browser attempts: 210 (175 reads); Akamai bypassed: NO; JS exfiltration: NO; relay: NO; CAPTCHA solved: NO.
22. Firecrawl credits: ≈77 (existing capacity).
23. USD spent: 0.
24. Places requests: 38 (gap verification, PRO mask); route discovery: NOT RUN.
25. Tiered / multi-part fees withheld: 30.
26. Conditional weights withheld: 7.
27. Inferences from silence / fee / weight / chip: 0.
28. Competitor raw / unique: 1,254 / 948; true missing 24 (16 carried in).
29. Orange County discovered / admitted: 63 / 0.
30. Riverside–Temecula discovered / admitted: 28 / 0.
31. Palm Springs discovered / admitted: 8 / 0.
32. Tijuana discovered / admitted: 6 / 0.
33. Cross-market identity collisions published: 0.
34. House-number-only or ZIP-only bindings: 0 (street words required).
35. Timeshare / vacation-rental admitted: 0.
36. Shadow package: pkg-san-diego-ca-919c1f7f8e8aa060, SHADOW_UNTIL_REGISTERED.
37. Sealed from: d1168e6c.
38. Re-seal idempotent: YES (same digest).
39. FAST: 15/15 PASS, 0 UNKNOWN, 0 FAILED.
40. Rule J: PASS — 881 files / 865 HTML / output present.
41. Rule K: PASS — BYTE_IDENTICAL, 4 cold builds, 0 reuse.
42. First-party gate: 239/239.
43. Independent reproduction: YES — detached worktree, separate process, DIFFERING FILES 0.
44. First FAST run defects: 1 (rule C, conditional weight) — fixed and re-sealed.
45. Coverage: FOUNDER DECISION.
46. Factory / shared code changed: NO.
47. Other markets touched: NO (inherited defects recorded only).
48. Registered / authorized / deployed: NO / NO / NO.
49. Broad regression runs: 0.
50. Branch pushed, origin == HEAD, tree clean: YES (verified after the final push).

```
SAN DIEGO SOURCE READY = YES
SAN DIEGO COVERAGE READY = FOUNDER DECISION
ACTIONABLE UNRESOLVED = 0
RULE J NONEMPTY = PASS
RULE K NONVACUOUS = PASS
FAST = 15/15 PASS, 0 UNKNOWN
FACTORY CODE CHANGED = NO
BROAD REGRESSION RUNS = 0
SAN DIEGO FINAL CANDIDATE = NO
SAN DIEGO DEPLOYED = NO
WAITING FOR RELEASE QUEUE = YES
```
