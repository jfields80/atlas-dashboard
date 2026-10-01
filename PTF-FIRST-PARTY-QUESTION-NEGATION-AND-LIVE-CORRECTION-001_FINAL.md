# PTF-FIRST-PARTY-QUESTION-NEGATION-AND-LIVE-CORRECTION-001 — FINAL

**PRODUCTION SAFETY CORRECTION IS LIVE.** Deploy `6abdbcb87e046e3e673760ac` (published 2026-10-01T01:52:12.836Z)
serves 37 markets / 3,196 profiles / 3,534 release-index routes / 3,604 served routes. Rollback is the Phoenix
deploy `6abc8387e81507b25eb94a0a`.

- **Branch:** `worker/ptf-question-negation-live-safety-001`
- **Worktree:** `C:\Atlas-PTF-Question-Negation-Safety`
- **Based on:** `0e309868`, the Phoenix-live branch head, which contains live source `e2d45272`.

## 1. Root cause

The shared first-party reader (`brightdata/policy_reading.parse`, used by FAST rule C through
`first_party_binding.classify_quote`) had two defects.

1. **It matched acceptance words anywhere, including inside FAQ questions.** "Are pets allowed?",
   "Is Honu Cove Pet Friendly?" and "Are you pet-friendly?" all matched an acceptance pattern (`pets? allowed`,
   `pet[- ]friendly`).
2. **It could not read several refusal shapes**, so it never applied the rule that a refusal wins:
   - an appositive or parenthetical subject: "pets (including ESAs) are not permitted",
     "Pets, including emotional support animals, are not permitted";
   - "we do not accept/allow pets";
   - "is not a pet-friendly hotel";
   - "a pet-free facility/community";
   - "strictly prohibited", "Animals are prohibited";
   - "a strict no-pet policy";
   - "pets aren't allowed".

Together, a page whose answer refused pets, but whose question named them, was published VERIFIED_PET_FRIENDLY.
A page that only asked the question, with no answer, was published the same way.

## 2. Reader repair (commit `7b9e7bcf`)

All changes are in `brightdata/policy_reading.py`. There are no hotel- or market-specific exceptions, and
service-animal handling is unchanged.

**Question guard.**
- `_first_acceptance` and every species path (`dogs_mentioned`, `_dogs_allowed_qualified`, both-species, the
  species pair) skip a match whose sentence ends in `?` within 120 characters, unless a new question starts in
  between.
- ALL-CAPS question openers count, so the WoodSpring chip "PETS ALLOWED" before an all-caps question is not
  swallowed.

**Refusal shapes added to `_PETS_REFUSED_RES`, which is checked before acceptance:**
- appositive, parenthetical or compound subjects;
- verb refusals ("do not / cannot / unable to accept / allow / permit / accommodate / welcome … pets");
- "not a pet-friendly hotel / property / …";
- "prohibited";
- "pet-free facility / community / complex" (including non-breaking hyphens);
- "no-pet(s) policy".

**Guards so restrictions are not read as refusals.**
- Count limits ("more than 2 pets"), sizes and numbers.
- Species exceptions ("other than dogs", "except").
- Room types ("in our Kitchenette suite").
- Room subjects ("Our oceanfront rooms are not pet friendly").

**Answer acceptances kept.**
- A "Yes" answer to a pet question, except when the question is about pet-free or allergy rooms, or the answer
  is service-animals-only.
- "welcome(s) … pets/dogs/cats".
- "four-legged/furry companions".
- "pets … are always welcome".
- "we (only) allow/accept … dogs / our four legged friends".

### Before/after on the order's cases (`qn_cases_before/after`)

| case | quote | before | after |
|---|---|---|---|
| A | Are pets allowed? | **ACCEPTANCE** (wrong) | not acceptance |
| B | Pets are not permitted. | refusal | refusal |
| C | Pets, including emotional support animals, are not permitted. | **not a refusal** (wrong) | refusal |
| D | Pets are welcome. | acceptance | acceptance |
| E | Pets are welcome. A $50 per stay pet fee applies. | acceptance | acceptance |
| F | Are pets allowed? Yes, dogs and cats are welcome. | acceptance | acceptance |
| G | Are pets allowed? No, pets are not permitted. | **ACCEPTANCE** (wrong) | refusal |
| H | Pets are not allowed. Service animals are welcome. | refusal | refusal |
| I | We do not allow pets. | **not a refusal** | refusal |
| K | Animals are prohibited. | **not a refusal** | refusal |
| KAL | Kalahari: "…pets (including ESAs) are not permitted…" | **ACCEPTANCE** | refusal |

Before the repair, 6 of 12 cases failed; after it, 12 of 12 pass.

### Tests (Phase 4)

- **New module:** `tests/pettripfinder/test_question_negation_reader_001.py`, 41 tests:
  - cases A–H;
  - the 14 live/Austin refusal quotes, verbatim;
  - the 2 question-only quotes;
  - 7 answer-acceptances the live corpus showed;
  - 5 restriction-not-refusal cases;
  - the all-caps chip, species-in-question, pet-free-room "Yes", four-legged friends and "Yes, service
    animals only".

  41/41 pass.
- **Existing coverage:** every test module importing `first_party_binding` or `policy_reading` (45 modules) ran on
  the repaired tree and on the baseline `0e309868`, sequentially:
  - after: 108 failed / 1468 passed;
  - baseline: 107 failed / 1428 passed.
- **Failure-set identity:** the 107 pre-existing failures are identical (historical Milwaukee acquisition
  fixtures). The one extra failure, `test_publication_042::test_nothing_outside_the_publication_surface_changed`,
  asserts that `git status` shows no uncommitted `policy_reading.py`. It passes once the reader is committed
  (re-run: 42 passed).
- **Evidence:** `markets/reports/question_negation_reader_tests_001.json`.
- **Broad regression runs:** 0.

## 3. Complete live corpus scan (Phase 5)

- **Reports:**
  - `markets/reports/live_pet_policy_quote_safety_scan_001.json` (every live PF record of all 37 markets, read
    through `classify_quote` exactly as FAST rule C reads it, under both readers);
  - `markets/reports/live_pet_policy_quote_safety_rescan_001.json` (the corrected tree).
- **Live PF records scanned:** 3,210.
- **Before the repair:** 3,073 affirmative, 44 other, 93 unreadable.
- **After the repair:**
  - 3,058 affirmative;
  - **11 explicit refusals**;
  - **3 question-only** (Clevelander, Essex House, and Amelia Surf & Racquet Club, whose answer refuses this
    complex but names the operator's other dog-friendly properties);
  - 2 whose question was the cited quote but whose own capture states the answer (The Scott, Vacation Village);
  - 1 improvement: Cleveland's Emerald Necklace Inn now reads as acceptance; it was already PF, so nothing
    changes.
- **Exactly 16 records moved out of acceptance.**
- **No-pets exclusions:** all 1,294 re-read. Eligible went 1,277 → 1,286 (9 improved), with 0 regressions.
- **Not touched:** the 136 live records that were already non-affirmative under the OLD reader (93 Columbus /
  legacy records with no publication-grade pets quote, 43 chip/fee-only). The rescan proves each one was
  already non-affirmative before this order.

## 4. All affected properties and corrections (Phase 6–8)

Ledger: `markets/reports/question_negation_live_correction_001.json`. Module:
`question_negation_live_correction_001.py`, commit `baf2691f`.

**Refusals → VERIFIED_NO_PETS** (canonical exclusion builder `market_registration_cli.exclusion_record`; the
hashes are derived by `hotel_exclusions`; `decided_by` is the work order, never a human signature):

| market | property | refusal cited (verbatim, own page) |
|---|---|---|
| FLL | Dolphin Hollywood | "…Are Pets Allowed? Unfortunately, we do not accept pets at this time…" |
| FLL | Honu Cove | "…Pets: Pets are strictly prohibited anywhere on property." |
| FLL | Mariner Motel Inc | "…our properties are currently pet-free to ensure a hypoallergenic environment…" |
| TPA | Bellweather Beach Resort | "…Bellwether Beach Resort is a pet-free facility…" |
| TPA | Bon Aire Motel Apts | "Are you pet friendly? No, we do not allow pets on the property." |
| TPA | Boutique Beach Retreat | "…we can not allow pets at the hotel… We do not allow pets at this property." |
| TPA | Crystal Palms Beach Resort at Treasure Island | "PETS: Pets and Emotional Support Animals are not allowed on property…" |
| TPA | Sunset Vistas Beachfront Suites | "…Unfortunately, pets aren't allowed." |
| TPA | Hotel South Tampa & Suites | "…we maintain a strict no-pet policy." |
| SD (additional) | Island Palms Hotel & Marina | "We are not a pet friendly hotel at Island Palms." |
| SD (additional) | Pacific Terrace Hotel | "Pacific Terrace Hotel is not a pet-friendly hotel." |
| JAX (additional) | Amelia Surf & Racquet Club | "The entire Surf & Racquet Club complex is a pet‑free community and does not allow pets of any kind." |

**Question-only rows → hold, not no-pets:**
- **MIA Clevelander South Beach.** The FAQ asks "Are you pet-friendly?" and the capture has no answer.
- **MIA Essex House Hotel.** It answers only "Please contact the hotel directly…".

Every committed capture lane of both identities was searched, and no first-party affirmative sentence exists.
Both partition items are now `AWAITING_POLICY_OBSERVATION` / `EVIDENCE_HOLD` with reason QUESTION_ONLY.

**Rebound to the answer on the same capture; they stay PF:**
- **PHX The Scott Resort & Spa:** "Yes, we allow our four legged friends to sleep in two buildings leaving the
  other three buildings pet-free."
- **ORL Vacation Village at Parkway:** "We are one of the few resorts in the area that offers a limited number of
  pet-friendly suites located in Buildings 5 and 6."

Each sentence is verbatim in the capture the record already cites, and is an operative acceptance under the
repaired reader. Profiles render facts, not quotes, so neither page changes a byte.

### Market-level accounting

| market | PF old → new | NP old → new | HELD old → new | corridor routes |
|---|---|---|---|---|
| fort-lauderdale-fl | 85 → 82 | 53 → 56 | 323 → 323 | 10 → 9 |
| tampa-fl | 148 → 142 | 45 → 51 | 314 → 314 | 11 → 11 |
| san-diego-ca | 147 → 145 | 92 → 94 | 192 → 192 | 14 → 14 |
| jacksonville-fl | 95 → 94 | 18 → 19 | 155 → 155 | 10 → 10 |
| miami-fl | 125 → 123 | 57 → 57 | 455 → 457 | 10 → 10 |
| phoenix-az | 256 → 256 | 59 → 59 | 169 → 169 | 18 → 18 |
| orlando-fl | 201 → 201 | 122 → 122 | 260 → 260 | 15 → 15 |
| **total** | **3,210 → 3,196 (−14)** | **+12** | **+2** | **−1** |

**FLL's `hollywood-beach` corridor (postal 33019)** published exactly 5 hotels, which is the market's minimum.
Two of them were Dolphin Hollywood and Mariner Motel. With 3 left, the corridor drops by FLL's own minimum rule.
The three remaining hotels stay published. This is a declared route removal.

### Phase 9 differential safety

36 files changed against HEAD, with **0 unexpected changes**: only the 16 ledger identities moved.
- **Packages:** −14 records, 2 rebound.
- **Seed shards:** −14 rows, 2 `pet_policy` rebound.
- **Exclusions:** +12.
- **Partitions:** 16 items changed.
- **Globals:** regenerated by `build_global_authority --write` (seed 3,359 → 3,345).
- **Release contracts:** only derived fields changed, plus a correction sentence on each note. 38/38 verify.

## 5. Package reseal results (Phase 10)

There is no canonical lane for correcting a live market: `seal`, `register` and `reregister` all refuse live
markets. `question_negation_reseal_001.py` runs the lane's own steps instead:

- `inputs_from_committed_market` with zone REGISTERED_LIVE;
- sealed twice and required to agree;
- a correction delta measured by the release index, with `removal_authority` naming this order and the ledger;
- `evaluate_package`;
- FAST A–O;
- `release_index.compare`.

**Which live index.** The live index comes from a checkout whose market data equals the live record's build
source, `63e410ff`. The committed tree is ahead of live, and `live_index` itself refuses there.

| market | package | FAST | J files / html | K | receipt eligible |
|---|---|---|---|---|---|
| fort-lauderdale-fl | pkg-fort-lauderdale-fl-79792a3015a43003 | 15/15 | 521 / 505 | BYTE_IDENTICAL | YES |
| tampa-fl | pkg-tampa-fl-fdaa6bdc3e26cb48 | 15/15 | 880 / 864 | BYTE_IDENTICAL | YES |
| san-diego-ca | pkg-san-diego-ca-d4c2f9daeb7680c2 | 15/15 | 869 / 853 | BYTE_IDENTICAL | YES |
| jacksonville-fl | pkg-jacksonville-fl-8573f63027aaf178 | 15/15 | 597 / 581 | BYTE_IDENTICAL | YES |
| miami-fl | pkg-miami-fl-90645d999f7c5ad2 | 15/15 | 764 / 748 | BYTE_IDENTICAL | YES |
| phoenix-az | pkg-phoenix-az-29c5cb7079715c5f | 15/15 | 1553 / 1537 | BYTE_IDENTICAL | YES |
| orlando-fl | pkg-orlando-fl-1c30633ec2c6d74e | 15/15 | 1238 / 1222 | BYTE_IDENTICAL | YES |

- Every package is reproducible, and every release diff passed.
- Market-state pins were re-derived from each package and held to its contract.
- **Unaffected markets are not reclassified:**
  - FAST rule C over all 23 committed sealed packages of the 19 unaffected markets with sealed packages: 0
    reclassified (`question_negation_unaffected_markets_001.json`).
  - The live scan covers all 37 markets' published packages: only the 16 rows moved.

## 6. Candidate, determinism and accounting (Phase 11)

- **Build A:** `assemble_production_site --output C:/t/qn4a`, started 22:44:40Z.
- **Build B:** `C:/t/qn4b`, started 00:13:33Z, after A had stopped. The two never ran concurrently.
- **Known post-manifest hang:** both builds wrote their manifests, removed their work dirs, then went idle. A
  showed 1.17 s CPU over 30 s and B 1.42 s, with manifests stable over 75 s. Only then were they terminated
  (15888 at 00:13:33Z, 15924 at 01:41:28Z).
- **Determinism:** BYTE_IDENTICAL. Bundle `63ae17cf…` = `63ae17cf…`, sitemap `4ee06422…` = `4ee06422…`, 19,352
  files compared, 0 differing, and both manifests' bytes are identical.
- **Candidate:** 37 markets / 3,196 profiles / 3,534 release-index routes / 3,604 served routes; 19,352 files /
  19,334 HTML; all gates pass; built from `18f4f979`.

**Accounting** (`question_negation_candidate_accounting_001.json`, ALL GATES PASS):

- **Release index.** It was carried forward one corrected market at a time, and each step passed
  `release_index.compare` against that market's own sealed delta. Every other market was carried unchanged.
- **Served routes.** 15 removed, exactly the declared set: 14 profiles plus `fort-lauderdale-fl/hollywood-beach/`.
  0 added.
- **Files.**
  - 0 added.
  - 84 removed, all in corrected markets.
  - 21 changed: 20 in corrected markets plus `sitemap.xml`.
  - **0 unaffected-market files changed.**
- **Removed identities.** None of the 14 has a profile page, a served route or a `/go/` page in the candidate.
- **Rebinds.** Both rebound profiles are served, byte-identical to live, and operative acceptances.
- **Rescan of the corrected candidate (Phase 12):** 3,196 PF, **0 explicit refusals, 0 question-only,
  0 ambiguous**.

## 7. Deployment authorization (Phase 13)

- **Authorization:** `ptf-auth-question-negation-001-63ae17cf4054`. It binds bundle `63ae17cf…` and sitemap
  `4ee06422…` (37 / 3,196 / 3,604) with rollback `6abc8387…`.
- **Source of authority:** the founder's order, quoted verbatim ("This order IS authorized to prepare and deploy
  the production safety correction, but only after all bounded safety gates pass.").
- **No new market is founder-authorized.** Participation is unchanged.

**Live parent re-verified immediately before the deploy:**
- `live-source --verify-host` resolved to `e2d45272` / `6abc8387` with the host verified.
- The served sitemap was still `647596dc…`.
- Netlify `getSite` published `6abc8387` (ready).
- `verify_target`, `verify_bundle_directory` and `deployability_problems` all returned `[]`.
- **The parent had not advanced.**

**Pre-deploy steps:**
- Baseline sweep: 3,619 / 3,619 routes return 200. 132 first returned curl `000` (a client gap); all 132
  returned 200 on refetch.
- The live manifest was written from the authorized bytes. It is identical to the candidate manifest, and
  `verify_manifest` returned `[]`.

## 8. Production deployment

```
netlify deploy --prod --no-build --dir C:\t\qn4a\site --site pettripfinder-prod
DEPLOY START 2026-10-01T01:51:25Z   END 01:52:12Z   EXIT 0   (21 files uploaded)
NETLIFY DEPLOYMENT ID = 6abdbcb87e046e3e673760ac
```

One run, no retry, no rebuild. According to the host, `6abdbcb8…` is ready in production and its previous
deploy is `6abc8387…`.

## 9. Post-deploy verification (Phase 14)

Report: `question_negation_live_verification_001.json`, **12/12 checks PASS**, ROLLBACK_REQUIRED NO.

- **Served state:** the served sitemap is the authorized `4ee06422…`, and the served route set is identical to
  the candidate's.
- **Routes:** all 3,604 return 200, which includes every unaffected prior route.
- **Removals:** all 15 declared removals return 404, and no removed profile's `/go/` page serves.
- **Bytes:** 136 / 136 sampled pages are byte-identical to the artifact. The sample covers:
  - every corrected market's hub, comparison and corridor pages;
  - both rebound profiles;
  - every unaffected market's hub;
  - the apex, the category root, robots.txt and llms.txt.
- **Markets:** 37 live; Detroit is still withheld (404).

**Live counts:**
- FALSE ACCEPTANCE CONTRADICTIONS LIVE = 0
- QUESTION-ONLY ACCEPTANCE LIVE = 0
- PRIOR MARKETS LOST = 0
- UNEXPECTED ROUTES LOST = 0

**Post-deploy state recorded:**
- deployment record `ptf-deploy-question-negation-001-6abdbcb87e046e3e673760ac`;
- the authorization is consumed;
- `supersessions.json` was extended:
  - Phoenix's entry is now historical and lists the 7 moved markets;
  - nine older entries that still bound the pre-correction contracts list them too;
  - the new current entry is empty;
- `deployment_state.json` live and source both point at `6abdbcb8`.

**Bounded post-deploy tests:** `test_market_state_pins.py` plus the new reader module: 292 / 292.
**Other post-deploy checks:**
- `release_contracts`: 38 / 38 agree.
- `build_global_authority --check`: every generated artifact matches the shards.
- `release_index live-source --verify-host`: resolved to deploy `6abdbcb8`, 3,196 profiles / 3,604 routes, host verified.
- A wider run of `tests/pettripfinder/contracts` plus `test_global_deployment_architecture_045` was **stopped at about 35% (0 failures so far)**. It was approaching a broad suite, and the order forbids one, so it is reported as partial and not counted.
- Post-deploy rescan of the live source: 3,196 PF, 0 refusals, 0 question-only, byte-identical to the committed rescan report.

**Correction made after the deploy.** The authorize step had bound `git rev-parse HEAD` (`56b68e13`, a
metadata-only commit after the build) as `source_commit`. The pin test requires the build commit, `18f4f979`.
The one field was corrected in the authorization, the record and the pin (commit `8da2c313`), and the authorize
step now binds the manifest's own build commit. The bundle and the deployed bytes are unchanged, and
`verify_record` and `verify_authorization` both return `[]`.

## 10. Austin impact (Phase 15)

- AUSTIN CURRENT SHADOW PACKAGE = `pkg-austin-tx-3030caf7703a9c57`
  (`sha256:3030caf7703a9c574c14177ebcb072bbd691e94a518f6b68a045506482026331`), branch
  `worker/ptf-austin-tx-market-001` at `fcca4aad`
- AUSTIN SHADOW CREATED UNDER OLD READER = YES
- AUSTIN PACKAGE REQUIRES REFRESH BEFORE REGISTRATION = YES. The shared reader, and therefore FAST rule C and the
  bundle-cache closure keys, changed.
- Austin was not modified, registered, authorized or deployed.

## FINAL ANSWERS

1. ROOT CAUSE = The shared first-party reader matched acceptance words inside FAQ QUESTIONS ("Are pets allowed?", "Is X pet friendly?") and could not read several refusal shapes ("pets (including ESAs) are not permitted", "we do not accept/allow pets", "is not a pet-friendly hotel", "pet-free facility", "prohibited", "no-pet policy"). A refusing or unanswered FAQ therefore published as VERIFIED_PET_FRIENDLY.
2. QUESTION-ONLY CURRENTLY CLASSIFIED ACCEPTANCE BEFORE = YES. 3 live records (Clevelander, Essex House, Amelia Surf & Racquet Club), plus cases A and G.
3. EXPLICIT REFUSAL FALSE POSITIVE BEFORE = YES. 11 live records were read as acceptance (Kalahari too, in Austin).
4. SHARED READER FIXED = YES (`brightdata/policy_reading.py`, commit 7b9e7bcf; no hotel or market exceptions; service-animal handling unchanged)
5. NEW REGRESSION TESTS = 41 (`tests/pettripfinder/test_question_negation_reader_001.py`, 41/41 pass; 45 existing reader-covering modules show the same failure set as the baseline)
6. LIVE PET-FRIENDLY RECORDS SCANNED = 3,210 (all 37 live markets), plus 1,294 no-pets exclusions
7. CONFIRMED FALSE ACCEPTANCE RECORDS FOUND = 12 explicit refusals: 11 refusal quotes, plus Amelia Surf & Racquet Club, whose own capture states the refusal
8. QUESTION-ONLY RECORDS FOUND = 2 held (MIA Clevelander, Essex House). 2 more had the question as the cited quote but the answer on the same capture, and were rebound (PHX The Scott, ORL Vacation Village).
9. FORT LAUDERDALE CORRECTIONS = 3 to VERIFIED_NO_PETS (Dolphin Hollywood, Honu Cove, Mariner Motel Inc). PF 85 -> 82, NP 53 -> 56. The hollywood-beach corridor fell below its minimum of 5 and is removed.
10. TAMPA CORRECTIONS = 6 to VERIFIED_NO_PETS (Bellweather, Bon Aire, Boutique Beach Retreat, Crystal Palms, Sunset Vistas, Hotel South Tampa). PF 148 -> 142, NP 45 -> 51.
11. MIAMI CORRECTIONS = 2 held as QUESTION_ONLY, not no-pets (Clevelander South Beach, Essex House Hotel). PF 125 -> 123, held 455 -> 457.
12. ADDITIONAL MARKETS AFFECTED = 4, each reported explicitly:
    - san-diego-ca: 2 refusals (Island Palms, Pacific Terrace)
    - jacksonville-fl: 1 refusal (Amelia Surf & Racquet Club)
    - phoenix-az: 1 rebind (The Scott)
    - orlando-fl: 1 rebind (Vacation Village at Parkway)
13. PET-FRIENDLY REFUSALS AFTER CORRECTION = 0
14. QUESTION-ONLY ACCEPTANCES AFTER CORRECTION = 0
15. AFFECTED PACKAGES = 7:
    - pkg-fort-lauderdale-fl-79792a3015a43003
    - pkg-tampa-fl-fdaa6bdc3e26cb48
    - pkg-san-diego-ca-d4c2f9daeb7680c2
    - pkg-jacksonville-fl-8573f63027aaf178
    - pkg-miami-fl-90645d999f7c5ad2
    - pkg-phoenix-az-29c5cb7079715c5f
    - pkg-orlando-fl-1c30633ec2c6d74e
16. ALL AFFECTED FAST = 15/15 x 7, receipts currently eligible, packages reproducible
17. RULE J NONEMPTY = YES (521 / 880 / 869 / 597 / 764 / 1553 / 1238 files)
18. RULE K NONVACUOUS = YES (BYTE_IDENTICAL x 7 on non-empty bundles)
19. CORRECTED CANDIDATE DETERMINISM = BYTE_IDENTICAL: bundle 63ae17cf..., 19,352 files compared, 0 differing
20. LIVE MARKET COUNT BEFORE = 37
21. LIVE MARKET COUNT AFTER = 37
22. PRIOR MARKETS LOST = 0
23. UNEXPECTED PROFILES LOST = 0. 14 declared removals: 12 to no-pets and 2 held.
24. UNEXPECTED ROUTES LOST = 0. 15 declared removals: 14 profiles plus fort-lauderdale-fl/hollywood-beach.
25. DEPLOYMENT PERFORMED = YES (Netlify --prod --no-build, run once, exit 0; host verification 12/12 PASS)
26. DEPLOYMENT ID = 6abdbcb87e046e3e673760ac
27. FALSE ACCEPTANCE CONTRADICTIONS LIVE = 0
28. QUESTION-ONLY ACCEPTANCE LIVE = 0
29. AUSTIN MODIFIED = NO
30. AUSTIN REFRESH REQUIRED = YES. pkg-austin-tx-3030caf7 was created under the old reader.
31. BROAD REGRESSION RUNS = 0
32. origin == HEAD = YES
33. tree clean = YES

FIRST-PARTY QUOTE READER REPAIR = PASS
LIVE FALSE PET-ACCEPTANCE CORRECTION = PASS
PET-FRIENDLY RECORDS WITH EXPLICIT REFUSAL = 0
QUESTION-ONLY PET-FRIENDLY RECORDS = 0
LIVE MARKETS = 37
PRIOR MARKETS LOST = 0
UNEXPECTED ROUTES LOST = 0
BROAD REGRESSION RUNS = 0
AUSTIN MODIFIED = NO
AUSTIN REQUIRES REFRESH = YES
PRODUCTION SAFETY REPAIR = PASS
