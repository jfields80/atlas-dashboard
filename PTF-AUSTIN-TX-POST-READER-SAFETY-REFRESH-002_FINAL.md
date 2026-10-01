# PTF-AUSTIN-TX-POST-READER-SAFETY-REFRESH-002 — FINAL

**Austin / Central Texas (`austin-tx`) was refreshed under the repaired shared first-party reader and the
current production lineage.** The market was not rebuilt: no census, discovery or acquisition was repeated. The
existing durable captures were re-read.

- **New package:** `pkg-austin-tx-024e6fb46a9e6934`, SHADOW_UNTIL_REGISTERED.
- **FAST:** 15/15.
- **Reproduction:** independent, byte-identical.
- **Old package:** `pkg-austin-tx-3030caf7` is historical only and cannot be registered.
- **Status:** Austin is not registered, not authorized and not deployed.

Worktree `C:\Atlas-Austin-TX-Hardened-V1`, branch `worker/ptf-austin-tx-market-001`.

## 1. Current live (Phase 1)

The canonical resolver (`release_index live-source --fetch --verify-host`, recorded as
`markets/reports/austin_tx_current_live_002.json`) resolved current live as follows.

| | |
|---|---|
| CURRENT LIVE SOURCE COMMIT | `46e49a02fa6297c80c1052bfab815b490cdc1997` (built from `18f4f979`) |
| CURRENT LIVE DEPLOYMENT | `6abdbcb87e046e3e673760ac` (the first-party reader safety correction) |
| CURRENT LIVE BUNDLE | `63ae17cf40542101c731ce315a210da5fae6ebce4ba51fc76477c80e2364edd7` |
| CURRENT LIVE SITEMAP | `4ee064226b37e36e96e1ecaf91a5e1301985445547a0225fdce526dd7b06999d` |
| CURRENT LIVE MARKETS / PROFILES | 37 / 3,196 |
| CURRENT LIVE RELEASE-INDEX / SERVED ROUTES | 3,534 / 3,604 |
| HOST VERIFIED | YES |

## 2. Repaired production lineage integrated (Phase 2)

`origin/worker/ptf-question-negation-live-safety-001` (`1109a239`) was merged into the Austin branch as merge
commit `663b06b4`. `origin/main` was not used.

- **Disjoint paths.** Since the shared base `0e309868`, Austin changed 85 paths and the repair changed 73. No path
  changed on both sides, so the merge had no conflicts at all (UNEXPLAINED CONFLICTS = 0).
- **Repair state wins.** The shared reader, the global live state, the deployment state, the 7 corrected live
  markets and the release machinery are byte-for-byte the repair tip's. Outside Austin paths, the merged tree
  differs from `1109a239` only by Austin's own proposed-market and discovery-config files.
- **Austin data kept.** AUSTIN FILES LOST = 0: every Austin path from `fcca4aad` still exists and is unchanged by
  the merge.
- HEAD now contains live.

## 3. The old package is historical only (Phase 3)

`pkg-austin-tx-3030caf7703a9c57` was sealed under the reader the production repair replaced. It is kept as
historical evidence: its package, receipt and reports are untouched. The proof is in
`austin_tx_reader_refresh_002.json` under `old_package`.

- **FAST today fails.** FAST was re-run over the old package against current live, with the two builds declared
  not run. **Rule N FAILS** because the parent is Phoenix `6abc8387`, rollback `6aba7587`, while live is
  `6abdbcb8`. J and K are UNKNOWN by design. **ELIGIBLE = NO.**
- **No current receipt.** No canonical receipt selects it. Its one receipt is a historical file in staging, and
  it is selected only for its own superseded digest, never for the current package.
- **Its inputs are gone.** The dependency inputs it names (policy package, partition, exclusions) are no longer the
  committed bytes.
- **Registration cannot use it.** Registration seals a fresh package from committed inputs, never a shadow
  package.

OLD PACKAGE REGISTERABLE = **NO**. OLD PACKAGE AUTHORIZABLE = **NO**.

## 4. Policy re-interpretation (Phases 4, 5, 6)

The refreshed clean authority applies the repaired shared reader to every Austin operative quote: Austin's own
read first, then the FAST rule C gate.

All 289 bound quotes were classified (`austin_tx_reader_refresh_002.json` under `interpretation` / `rows`):

| disposition | classification | rows |
|---|---|---:|
| CLEAN_PET_FRIENDLY | AFFIRMATIVE_ACCEPTANCE | 190 |
| CLEAN_VERIFIED_NO_PETS | EXPLICIT_REFUSAL | 63 |
| EVIDENCE_HOLD | AFFIRMATIVE_ACCEPTANCE | 7 (held for route rulings or a conflicting own read, never by the reader) |
| EVIDENCE_HOLD | NOT_OPERATIVE | 5 |
| EVIDENCE_HOLD | SERVICE_ANIMAL_ONLY | 6 |
| IDENTITY_MISMATCH_HOLD | AFFIRMATIVE_ACCEPTANCE / EXPLICIT_REFUSAL | 16 / 2 |

- **Question-only is never acceptance.** No pet-friendly row is question-only, refusing or service-animal-only, and
  every one of the 190 pet-friendly quotes is an operative acceptance under the repaired reader.
- **An explicit refusal overrides pet words.** The four rows below move on their own unchanged quotes.
- **Service-animal-only stays held.** It never becomes ordinary acceptance (6 rows).

**Exactly 4 rows changed disposition**, all EVIDENCE_HOLD → CLEAN_VERIFIED_NO_PETS on their own unchanged
first-party quotes:
- Kalahari Round Rock;
- AT&T Hotel & Conference Center;
- Heywood Hotel;
- Sage Hill Inn & Spa. Sage Hill was counted router-exhausted, not founder-held; its "pets cannot be accommodated"
  is now read.

### Kalahari (Phase 5)

- **Quote:** "Are pets allowed? | With the exception of service animals certified under the American Disabilities
  Act (ADA), pets (including ESAs) are not permitted at Kalahari Resorts & Conventions…"
- **Repaired reader:** EXPLICIT_REFUSAL (rule C `no_pets` ELIGIBLE).
- **Path:** it passed through the canonical verified-no-pets path as exclusion
  `austin-tx--kalahari-resorts-and-conventions-round-rock-tx`. Its hashes were derived by `hotel_exclusions`.

**KALAHARI PET-FRIENDLY = NO.**

### The five old refusal-language holds (Phase 6)

| property | quote | old disposition | new classification | new disposition |
|---|---|---|---|---|
| Kalahari Round Rock | "…pets (including ESAs) are not permitted at Kalahari Resorts & Conventions…" | EVIDENCE_HOLD (founder) | EXPLICIT_REFUSAL | **VERIFIED_NO_PETS** |
| AT&T Hotel & Conference Center | "Pets are not allowed at the AT&T Hotel and Conference Center due to University of Texas at Austin regulations…" | EVIDENCE_HOLD (founder) | EXPLICIT_REFUSAL | **VERIFIED_NO_PETS** |
| Heywood Hotel | "…we are unfortunately unable to accommodate pets." | EVIDENCE_HOLD (founder) | EXPLICIT_REFUSAL | **VERIFIED_NO_PETS** |
| Mountain Star Lodge & Hotel | "Pets policy: \| No pets allowed in this property. Each violation is subject to $500 cleaning fee." | EVIDENCE_HOLD (founder) | NOT_OPERATIVE | EVIDENCE_HOLD (founder) |
| Strickland Arms B&B | "Please note that we can NOT accommodate children under 12 or pets of any kind" | EVIDENCE_HOLD (founder) | NOT_OPERATIVE | EVIDENCE_HOLD (founder) |

**3 resolved; 2 remain held.** The two remaining rows are not held because of the old defect: **the repaired
shared reader still returns no verdict on these exact quotes.**

- It reads "No pets allowed in this property." alone as a refusal, but not with the $500 violation-fee sentence
  beside it.
- It reads "we can NOT accommodate pets of any kind", but not with "children under 12" between the verb and
  "pets".

The shared reader is factory code, and this order changes none. Neither row is published as pet-friendly; both
are refusals waiting on either a further shared-reader repair or a founder ruling.

## 5. Founder-decision cohort (Phase 7)

| class | old | new |
|---|---:|---:|
| dual-brand rows (9 buildings) | 18 | 18 |
| Bunkhouse / operator-domain route rulings | 5 | 5 |
| refusal-language rows | 5 | 2 |
| **total** | **28** | **25** |

OLD FOUNDER ROWS = 28; ROWS RESOLVED BY REPAIRED READER = 3; NEW FOUNDER ROWS = 25.

- No dual-brand, shared-campus or operator-domain row was resolved, because no canonical rule resolves them.
- `identity_resolutions.json` was not written.

## 6. Other safe holds preserved (Phase 8)

- 11 SAME_CAMPUS_DISTINCT_ENTITY rows: unchanged in the census.
- Sentral East Austin 1630: IDENTITY_REVIEW_REQUIRED.
- Preopening rows: 0 found, 0 published.
- Timeshare / vacation ownership excluded by the census: Club Wyndham Austin, WorldMark Austin, Raintree Inn &
  Suites.
- The 12 cross-market collision holds and every bounded router hold: unchanged.
- Nothing was forced into publication.

**Static-lane re-read.** The plain-client lane recorded its own reader verdicts. The lane was not re-run, because
63 of its targets have no cached attempt and would be refetched. Instead, its 23 persisted reads were re-read
under the repaired reader. 6 moved from acceptance to no verdict, all question-plus-restriction blocks: Uptown
Suites Downtown and five WoodSprings. None was ever pet-friendly; the shared-reader gate holds them.

## 7. Fee safety (Phase 9)

- **Withholding module:** 31 single-basis fees published, 60 tiered withheld, 24 unsafe single fees withheld.
- **Independent check over the new package:** no per-stay fee whose quote says nightly or daily, and no published
  fee whose quote states two amounts.

**MISLEADING SINGLE FEES = 0.**

Nightly ≠ per-stay and daily ≠ per-stay are preserved, tiered fees are not flattened, and multi-amount structures
are not collapsed.

## 8. Market accounting (Phases 10–12)

| | old (`fcca4aad`) | new |
|---|---:|---:|
| QUALIFYING CENSUS | 407 | 407 |
| PET-FRIENDLY | 190 | 190 |
| VERIFIED NO-PETS | 59 | **63** |
| RESOLVED | 249 | **253** |
| UNRESOLVED | 158 | **154** |
| RESOLUTION RATE | 61.18 % | **62.16 %** |
| ACTIONABLE UNRESOLVED | 0 | **0** |

| unresolved class | total | router exhausted | requires new provider | requires new spend | requires founder | material coverage risk |
|---|---:|---:|---:|---:|---:|---|
| ROUTING_HOLD | 88 | 8 | 0 | 80 | 0 | NO (no route in any authorized lane; Places `websiteUri` is new spend) |
| EVIDENCE_HOLD | 25 | 18 | 0 | 0 | 7 | NO |
| IDENTITY_MISMATCH_HOLD | 20 | 2 | 0 | 0 | 18 | NO (dual-brand; held, never published) |
| SOURCE_SILENT | 15 | 15 | 0 | 0 | 0 | NO |
| ACCESS_BLOCKED | 6 | 6 | 0 | 0 | 0 | NO |
| **total** | **154** | **49** | **0** | **80** | **25** | — |

**TECHNICAL SOURCE READY = YES.** Every coverage condition is true.

**COVERAGE READY = FOUNDER DECISION**, recomputed mechanically and not carried forward: 105 unresolved rows are
reachable only through new spend (80) or a founder ruling (25).

## 9. New shadow package, FAST, receipt (Phases 13–15)

**Inputs.** Every staged input was re-derived and committed as `26ab90db`: clean authority, partition, staged
policy package / proposed authority / shards, fee report and actionability.

- The outputs are stamped by this order, with `reviewed_at` 2026-10-01.
- Capture dates are unchanged (`observed_at` 2026-09-30).
- The partition's `AS_OF` was a leftover Phoenix date (2026-09-29) and is corrected.
- `SEALED_AT = 2026-10-01T05:23:32Z`, real clock, when the inputs were frozen.
- **Beyond those stamps, the staged data changed exactly as intended:** the policy package is unchanged, the
  exclusions gain the 4 refusals, and the partition changes those same 4 items.

| | |
|---|---|
| NEW PACKAGE | `pkg-austin-tx-024e6fb46a9e6934`, SHADOW_UNTIL_REGISTERED, parent = current live `6abdbcb8` |
| NEW PACKAGE DIGEST | `sha256:024e6fb46a9e6934e4884ddb2ac2f4c42756a6154f6f0cd74d6674baf9e665b4` |
| FAST | **15/15 PASS, 0 UNKNOWN, 0 FAILED** |
| RULE J | PASS: file_count 1,157, html_count 1,141, output present, 0 output defects, bundle `6cc8b825…` |
| RULE K | PASS: BYTE_IDENTICAL, 4 cold builds, 0 reuse hits |
| Rule C | 253 / 253 eligible |
| Receipt | `pkg-austin-tx-024e6fb46a9e6934-74e62beb329c179c.json`, CURRENTLY ELIGIBLE = YES; the old-reader receipt is not selected for the current package |

The bundle digest equals the old package's. That is expected: the 4 moved rows become verified-no-pets
exclusions, which render no page, and the 190 published profiles are unchanged.

## 10. Independent reproduction (Phase 16)

Record: `markets/staging/austin-tx/reproduction/independent_reproduction_002.json`; the process record was
written before the process started.

**Setup.**
- Detached worktree `C:/t/atx2b-wt` at `26ab90db`.
- A separate OS process (`Start-Process`, PID 23188).
- Work dir `C:/t/atx2b`; the sealing run used `C:/t/atx2a`.
- The staged tree was re-derived with `--stage`.

**Results.**
- Same package ID and digest; the package file is byte-identical raw.
- **DATA DIFFERENCES = 0.** The 8 staged files are byte-identical raw.
- **SITE DIFFERENCES = 0.** Bundle `6cc8b825…` in both runs (1,157 / 1,141).
- FAST 15/15 and K BYTE_IDENTICAL in both runs.
- Receipts: 34 of 1,236 fields differ, all wall-clock seconds, timestamps, environment or work-dir-keyed cache
  keys.
- No provenance normalisation was needed, because both runs sealed from the same committed sha.

**BYTE IDENTICAL = YES.** The worktree and the scratch dirs were removed.

## 11. Austin reader-safety proof (Phase 17), over the new package

| | |
|---|---:|
| PET-FRIENDLY WITH EXPLICIT REFUSAL | 0 |
| QUESTION-ONLY PET-FRIENDLY | 0 |
| PREOPENING PROFILES PUBLISHED | 0 |
| VACATION-OWNERSHIP / TIMESHARE PROFILES PUBLISHED | 0 |
| MISLEADING SINGLE FEES | 0 |

The other 36 live markets were not rescanned or resealed; that production repair is complete.

## 12. Isolation and boundaries (Phases 18–19)

- **Changed paths.** Since the merge, this order changed 24 paths, all Austin-owned:
  - `scripts/pettripfinder/austin_tx_*` (market-local modules);
  - `markets/reports/austin_tx_*`;
  - `markets/staging/austin-tx/`;
  - this report.

  NEW UNRELATED MARKET SOURCE CHANGES = 0 and NEW FACTORY IMPLEMENTATION CHANGES = 0: no shared module, shared
  reader, global, pin, contract or deploy file was touched. The inherited production-repair changes arrived by
  merge and are not Austin changes.
- **Not done:** registration, founder authorization, a production candidate, deployment authorization, a deploy,
  or any participation or pin change.
- **Status:** AUSTIN LIVE = NO. CURRENT LIVE MODIFIED = NO.
- **Cost:** 0 broad regression runs, 0 provider spend, 0 new captures.

**Austin module changes** (all market-local):

- The policy-chain modules now stamp this order: `WORK_ORDER`, with `SOURCE_READY_ORDER` kept for provenance.
- The staging module separates `reviewed_at` from the capture date.
- The shadow report derives its parent text from the live state instead of hard-coding Phoenix.
- New module `austin_tx_reader_refresh_002.py` (read-only evidence).

**One mistake caught in my own check.** The first run of the new fee check reported 3 "misleading" fees: Hampton
Downtown, Marriott North and Residence Inn Dell Way. It had counted "$50.00" and "$50" as two amounts. Each quote
states one amount with an explicit per-stay basis. The check now compares amounts as numbers and reports 0.

## FINAL ANSWERS

1. CURRENT LIVE DEPLOYMENT = 6abdbcb87e046e3e673760ac (source 46e49a02, built from 18f4f979; bundle 63ae17cf…, sitemap 4ee06422…; host verified)
2. CURRENT LIVE MARKETS = 37 (3,196 profiles / 3,534 release-index routes / 3,604 served routes)
3. REPAIR LINEAGE INTEGRATED = YES. 1109a239 was merged as 663b06b4: 0 conflicts, 0 Austin files lost, 0 unexplained conflicts.
4. OLD AUSTIN PACKAGE = pkg-austin-tx-3030caf7703a9c57, historical only and kept
5. OLD PACKAGE REGISTERABLE = NO. FAST today fails N (Phoenix parent); no canonical receipt; its inputs are no longer committed.
6. KALAHARI PET-FRIENDLY = NO (VERIFIED_NO_PETS through the canonical exclusion path)
7. OLD REFUSAL-LANGUAGE HOLDS = 5
8. REFUSAL-LANGUAGE ROWS RESOLVED = 3 (Kalahari, AT&T Hotel, Heywood). Sage Hill also moved to NP; it had been router-exhausted, not founder-held.
9. REMAINING REFUSAL-LANGUAGE HOLDS = 2 (Mountain Star, Strickland Arms). The repaired shared reader still returns no verdict on their exact quotes; neither is published.
10. OLD FOUNDER-DECISION ROWS = 28
11. NEW FOUNDER-DECISION ROWS = 25 (18 dual-brand + 5 operator-domain + 2 refusal-language)
12. QUALIFYING CENSUS = 407
13. PET-FRIENDLY = 190
14. VERIFIED NO-PETS = 63
15. RESOLVED = 253
16. UNRESOLVED = 154
17. RESOLUTION RATE = 62.16 %
18. ACTIONABLE UNRESOLVED = 0
19. PREOPENING PROFILES PUBLISHED = 0
20. VACATION-OWNERSHIP / TIMESHARE PROFILES PUBLISHED = 0
21. MISLEADING SINGLE FEES = 0
22. PET-FRIENDLY WITH EXPLICIT REFUSAL = 0
23. QUESTION-ONLY PET-FRIENDLY = 0
24. TECHNICAL SOURCE READY = YES
25. COVERAGE READY = FOUNDER DECISION (80 rows need new spend and 25 need a founder ruling; actionable 0)
26. NEW PACKAGE = pkg-austin-tx-024e6fb46a9e6934 (SHADOW_UNTIL_REGISTERED)
27. NEW PACKAGE DIGEST = sha256:024e6fb46a9e6934e4884ddb2ac2f4c42756a6154f6f0cd74d6674baf9e665b4
28. RULE J NONEMPTY = PASS (1,157 files / 1,141 HTML / output present / 0 defects)
29. RULE K NONVACUOUS = PASS (BYTE_IDENTICAL, 4 cold builds, 0 reuse)
30. FAST = 15/15 PASS, 0 UNKNOWN, 0 FAILED
31. FAST RECEIPT CURRENTLY ELIGIBLE = YES (the new receipt; the old-reader receipt is not selected)
32. PACKAGE REPRODUCIBLE = YES (two in-process seals plus an independent process in a detached worktree)
33. DATA DIFFERENCES = 0
34. SITE DIFFERENCES = 0
35. NEW UNRELATED MARKET SOURCE CHANGES = 0
36. NEW FACTORY IMPLEMENTATION CHANGES = 0
37. BROAD REGRESSION RUNS = 0
38. CURRENT LIVE MODIFIED = NO
39. AUSTIN REGISTERED = NO
40. FOUNDER AUTHORIZATION CREATED = NO
41. AUSTIN DEPLOYED = NO
42. origin == HEAD = YES (verified after the final push)
43. tree clean = YES (verified after the final push)
44. READY FOR AUSTIN REGISTRATION = YES on the technical side: source-ready, actionable 0, and a FAST-clean, reproducible package parented on current live. Coverage remains a FOUNDER DECISION that the founder takes at registration or authorization.

```
AUSTIN POST-READER REFRESH = PASS
OLD AUSTIN PACKAGE REGISTERABLE = NO
PET-FRIENDLY RECORDS WITH EXPLICIT REFUSAL = 0
QUESTION-ONLY PET-FRIENDLY RECORDS = 0
ACTIONABLE UNRESOLVED = 0
TECHNICAL SOURCE READY = YES
AUSTIN COVERAGE READY = FOUNDER DECISION
RULE J NONEMPTY = PASS
RULE K NONVACUOUS = PASS
FAST = 15/15 PASS, 0 UNKNOWN, 0 FAILED
PACKAGE REPRODUCIBLE = YES
NEW FACTORY IMPLEMENTATION CHANGES = 0
BROAD REGRESSION RUNS = 0
CURRENT LIVE MODIFIED = NO
AUSTIN REGISTERED = NO
AUSTIN DEPLOYED = NO
READY FOR AUSTIN REGISTRATION = YES
```
