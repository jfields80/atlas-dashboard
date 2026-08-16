# PTF-INDIANAPOLIS-MARKET-REVALIDATION-001 — Final founder handoff

**Status: FOUNDER_AND_CLAUDE_REVIEW_REQUIRED**

**Technical result: REVALIDATED_UNPUBLISHED**

`REVALIDATED_UNPUBLISHED` is the technical result of this revalidation. It is not integration authorization. No merge, publication, or deployment was performed.

---

## 1. Repository root

`C:/Atlas-Grok-Indianapolis-Revalidate`

## 2. Working directory

`C:\Atlas-Grok-Indianapolis-Revalidate\atlas-dashboard`

## 3. Branch

`grok/ptf-indianapolis-revalidation-001`

## 4. Starting and ending HEAD

Starting HEAD: `fea73de1ec699289cf04b88fd7069cf23fa4d735`  
Package commit: `62fafdc3291b7f8bbd6cfeaeb9327cd022f4126a`

Required baseline confirmed before any write.

The original Indianapolis worktree at `C:\Atlas-Grok-Indianapolis` was not modified. Its HEAD remains `2d885d139950f93dba4f02edd04fa849781a8a0a`.

## 5. Git status before commit

Dirty worktree on `grok/ptf-indianapolis-revalidation-001`. Ten modified tracked files (Indianapolis registration and contract-gate assertions) and eight new tracked-path Indianapolis artifacts, plus this handoff at the worktree root. Gitignored research and founder-review artifacts live under `atlas-dashboard/data/`.

## 6. Market boundary

Indianapolis visitor market, not municipal limits and not the entire MSA. Documented in `atlas-dashboard/data/market_research/indianapolis/boundary.md`.

Included: Marion County visitor core and urban lodging corridors; IND airport lodging; Speedway; Hamilton County cities Carmel, Fishers, Noblesville, Westfield; Hendricks County Plainfield, Avon, Brownsburg; Greenwood I-65 Indianapolis-South cluster.

Excluded: Festival Country Indiana (Franklin, Whiteland, Bargersville); Zionsville; Hamilton County northern towns; Danville; distant Indiana destinations; Cincinnati-owned southeastern Indiana.

Fountain-Fletcher is a Visit Indy neighborhood but has no public hotel inventory after B&Bs are category-excluded, so it is not a corridor. Thin corridors (Broad Ripple = 2, north-central = 1, Mass Ave = 1) were not redrawn; the measured geography is unchanged.

## 7. Included municipalities and corridors

Municipalities: Indianapolis, Speedway, Southport, Carmel, Fishers, Noblesville, Westfield, Plainfield, Avon, Brownsburg, Greenwood.

Corridors and measured census counts (before = source BUILD-001; after = this revalidation):

| Corridor | Before | After |
|---|---:|---:|
| indianapolis-in__downtown | 34 | 34 |
| indianapolis-in__airport | 19 | 19 |
| indianapolis-in__keystone-castleton | 15 | 15 |
| indianapolis-in__carmel | 10 | 10 |
| indianapolis-in__plainfield | 10 | 10 |
| indianapolis-in__greenwood | 10 | 10 |
| indianapolis-in__northwest | 9 | 9 |
| indianapolis-in__fishers | 9 | 9 |
| indianapolis-in__east-i70 | 9 | 9 |
| indianapolis-in__hendricks-west | 6 | 6 |
| indianapolis-in__south | 6 | 6 |
| indianapolis-in__westfield | 4 | 4 |
| indianapolis-in__noblesville | 4 | 4 |
| indianapolis-in__speedway | 4 | 4 |
| indianapolis-in__broad-ripple | 2 | 2 |
| indianapolis-in__mass-ave | 1 | 1 |
| indianapolis-in__north-central | 1 | 1 |
| **Total** | **153** | **153** |

Unassigned canonical lodging: 0 before, 0 after.

## 8. Excluded candidates and reasons

Unchanged from BUILD-001.

| Name | Disposition | Reason |
|---|---|---|
| Marriott IndyPlace | confirmed duplicate | Campus name for the JW / Courtyard / SpringHill / Fairfield cluster |
| Holiday Inn Express Airport West | confirmed duplicate | Same IND courtesy-list URL and phone as Holiday Inn Indianapolis Airport |
| GentSpa Hilton Indianapolis | category excluded | Spa, not lodging |
| The Harney House Inn | category excluded | B&B |
| The Looking Glass Inn | category excluded | B&B |
| Nestle Inn | category excluded | B&B |
| Old Northside Bed and Breakfast | category excluded | B&B |
| Stone Soup Inn | category excluded | B&B |
| Fountainview Inn | category excluded | Inn / B&B |
| The Columbia Club | category excluded | Private club lodging |
| Park Place at City Centre | identity unresolved (held out of census) | Not confirmed as a public hotel |
| Signia by Hilton Indianapolis | closed or converted / not yet operating | Visit Indy: expected 2026 opening |
| Baymont Lawrenceburg | boundary excluded | Owned by cincinnati-oh |
| DoubleTree Lawrenceburg | boundary excluded | Owned by cincinnati-oh |

## 9. Exact before/after counts

Destination `fea73de` had no Indianapolis market. Source BUILD-001 held the measured universe. This revalidation regenerated that universe against current contracts.

| Measure | Destination before (fea73de) | Source BUILD-001 | After revalidation |
|---|---:|---:|---:|
| Indianapolis census identities | 0 (absent) | 153 | 153 |
| Identity keys preserved vs BUILD-001 | n/a | 153 | 153 (set equal) |
| Published / pet-friendly | 0 | 0 | 0 |
| Verified no-pets | 0 | 0 | 0 |
| Out of category (partition) | 0 | 0 | 0 |
| Unresolved | 0 (absent) | 153 | 153 |
| Capture-ready / publishable policy facts | 0 | 0 | 0 |
| Committed Indianapolis routing rows | 0 | 0 | 0 |
| Routing assessments (not authority) | 0 | 153 | 153 |
| Founder-review / browser-capture queue | 0 | 153 | 153 |
| Corridor-assigned / unassigned | 0 / 0 | 153 / 0 | 153 / 0 |
| Indianapolis policy package | absent | absent | absent |
| Indianapolis release contract | absent | absent | absent |
| Indianapolis seed / exclusion / nav / sitemap | absent | absent | absent |

Identity states after: 64 IDENTITY_CONFIRMED, 86 IDENTITY_PROVISIONAL, 3 IDENTITY_UNRESOLVED.

Partition next-action classes after: 89 AWAITING_IDENTITY_RESOLUTION, 35 AWAITING_PROPERTY_LEVEL_URL, 29 AWAITING_POLICY_OBSERVATION.

Starting classified candidates remain 167 (153 canonical + 14 non-canonical dispositions).

## 10. Source totals by family

Unchanged.

| Source | Family | Canonical census rows |
|---|---|---:|
| brand_locator_research | CHAIN | 86 |
| downtown_indy_inc | CVB | 29 |
| indianapolis_airport | CVB | 21 |
| visit_hamilton_county | CVB | 9 |
| visit_hendricks_county | CVB | 5 |
| visit_indy | CVB | 3 |

## 11. Duplicate, category, closed, and boundary counts

Unchanged: 2 confirmed duplicates; 8 category-excluded (held out of census); 1 closed/not operating; 1 identity-unresolved held out; 2 explicit Cincinnati Indiana boundary exclusions plus destination clusters in the boundary document.

## 12. Published / verified-no-pets / capture-ready

0 / 0 / 0. No Indianapolis policy artifact exists. 29 rows have a property-level URL assessment and are waiting for policy observation; that is not capture-ready publication. No pet-policy facts were fabricated or inferred from sibling hotels.

## 13. Browser / capture queue

153 rows. Queue identity_key set equals the unresolved partition set equals the census identity_key set. Zero duplicates. Zero omissions. No `hotel_id` column exists; every row carries `identity_key` matching census and partition. `review_status` is `NOT_STARTED`. 16 batches of at most 10.

Gitignored outgoing path:

`C:\Atlas-Grok-Indianapolis-Revalidate\atlas-dashboard\data\operator_evidence\indianapolis-founder-review-001\outgoing\work-browser-pass-001\`

Rollup CSV hash: `sha256:87373444f0ded32bc98c47c824c49067e2ed36af290ab7791daa2a3c2cd4f07e`

Screenshot queue hash: `sha256:3c5f7ec7590a819c66c28ddcab10adc151d9d1415e6918e510b22d41da82d2f7`

No screenshots or browser-derived binaries were created or committed.

## 14. Utility inventory

Unchanged and revalidated on disk: 3 dog parks; 5 trails/greenways; 5 veterinary facilities (4 authoritatively 24/7); index-level dining, brewery, and event records. Individual patio and taproom permissions were not inferred.

## 15. Identity collisions

Indianapolis identity keys are disjoint from Columbus, Cleveland, Dayton, Cincinnati, and every other committed (non-proposed) census in this worktree. Cincinnati Indiana identities and ZIPs 47001 / 47025 / 47040 / 47012 are absent.

## 16. Every file created (tracked)

- `atlas-dashboard/launch_packages/pettripfinder/markets/indianapolis-in.json`
- `atlas-dashboard/launch_packages/pettripfinder/markets/coverage/indianapolis-in.json`
- `atlas-dashboard/launch_packages/pettripfinder/identity_census/indianapolis-in.json`
- `atlas-dashboard/launch_packages/pettripfinder/indianapolis_final_partition_001.json`
- `atlas-dashboard/scripts/pettripfinder/discovery/config/indianapolis_in.json`
- `atlas-dashboard/scripts/pettripfinder/indianapolis_candidates.py`
- `atlas-dashboard/scripts/pettripfinder/indianapolis_market_factory.py`
- `atlas-dashboard/tests/pettripfinder/test_indianapolis_market_001.py`
- `PTF-INDIANAPOLIS-MARKET-REVALIDATION-001_FINAL.md` (this file)

## 17. Every file modified (tracked)

- `atlas-dashboard/scripts/pettripfinder/discovery/market_config.py`
- `atlas-dashboard/scripts/pettripfinder/discovery/source_families.py`
- `atlas-dashboard/tests/pettripfinder/test_markets.py`
- `atlas-dashboard/tests/pettripfinder/contracts/test_market_authorities.py`
- `atlas-dashboard/tests/pettripfinder/contracts/test_market_geography.py`
- `atlas-dashboard/tests/pettripfinder/contracts/test_identity_key.py`
- `atlas-dashboard/tests/pettripfinder/discovery/test_market_config.py`
- `atlas-dashboard/tests/pettripfinder/discovery/test_source_families.py`
- `atlas-dashboard/tests/pettripfinder/test_global_assembler.py`
- `atlas-dashboard/tests/pettripfinder/test_per_market_release_contracts.py`

No Ohio policy, exclusion, seed, routing-authority, migration, approval, Netlify, renderer, or Cleveland governance file was modified.

## 18. Gitignored research and queue (on disk, not committed)

- `atlas-dashboard/data/market_research/indianapolis/boundary.md`
- `atlas-dashboard/data/market_research/indianapolis/source_registry.json`
- `atlas-dashboard/data/market_research/indianapolis/candidate_ledger.json`
- `atlas-dashboard/data/market_research/indianapolis/duplicate_ledger.json`
- `atlas-dashboard/data/market_research/indianapolis/routing_assessment.json`
- `atlas-dashboard/data/market_research/indianapolis/policy_working_notes.json`
- `atlas-dashboard/data/market_research/indianapolis/reconciliation_report.json`
- `atlas-dashboard/data/market_research/indianapolis/str_market_signal.md`
- `atlas-dashboard/data/market_research/indianapolis/utilities/*.json` (6 files)
- `atlas-dashboard/data/operator_evidence/indianapolis-founder-review-001/outgoing/work-browser-pass-001/` (16 batch CSV/manifest pairs, rollup CSV/manifest, screenshot queue)

## 19. Every data-generation command

```
python -m scripts.pettripfinder.indianapolis_market_factory
python -m scripts.pettripfinder.indianapolis_market_factory --check
```

Factory result: census 153, published 0, verified_no_pets 0, out_of_category 0, unresolved 153, queue 153, agrees true, technical_result REVALIDATED_UNPUBLISHED.

`--check` repeated the same equations after write.

Assignment reproducibility: `scripts.pettripfinder.normalize_census_geography.recompute("indianapolis-in")` → 0 changes.

Compared to source BUILD-001 artifacts: identity-key set, assignment triples, identity/lodging/policy state quads, partition final_state map, and queue classification map are identical. Only provenance changed (`work_order`, `base_commit`).

## 20. Every test command and result

1. Targeted Indianapolis and touched-surface contract/release gates:

```
python -m pytest tests/pettripfinder/test_indianapolis_market_001.py tests/pettripfinder/test_markets.py tests/pettripfinder/discovery/test_source_families.py tests/pettripfinder/discovery/test_market_config.py tests/pettripfinder/contracts/test_market_authorities.py tests/pettripfinder/contracts/test_market_geography.py tests/pettripfinder/contracts/test_identity_key.py tests/pettripfinder/test_global_assembler.py tests/pettripfinder/test_per_market_release_contracts.py tests/pettripfinder/test_market_ownership.py tests/pettripfinder/test_market_isolation.py tests/pettripfinder/contracts/test_census_partition.py tests/pettripfinder/test_homepage_market_awareness.py tests/pettripfinder/test_publication_guard.py tests/pettripfinder/test_inventory_validation.py tests/pettripfinder/test_two_market_compat.py tests/pettripfinder/test_policy_schema_migration.py -q --tb=short
```

**723 passed, 5 skipped, 0 failed.** Runtime 178.31s. Skips are pre-existing data-/full-build skips, not Indianapolis failures.

2. Complete suite:

```
python -m pytest tests -v
```

**11124 passed, 131 skipped, 0 failed.** Runtime 1038.20s.

No tests were weakened or deleted.

## 21. Complete reconciliation equations

```
census.identity_keys == partition.identity_keys == queue.identity_keys
153 == 153 == 153

published + verified_no_pets + out_of_category + unresolved == census.count
0 + 0 + 0 + 153 == 153
```

All four counts derived from `final_state` via `partition.reconcile()`.  
Canonical census duplicates = 0. Partition overlap = 0. Unclassified candidates = 0.  
Queue identity set == unresolved partition set == 153.  
Assignment `recompute` diff = 0.  
No Ohio identity in Indianapolis. No Indianapolis identity in Ohio packages. No Cincinnati Indiana ZIP in Indianapolis.  
Assembler `assemblable` is False. `indianapolis-in` is not in `available_market_ids()`.

## 22. Protected Ohio authority hashes (unchanged)

| File | SHA-256 |
|---|---|
| hotel_policy_facts.json | d06681b291fdfa15b2f7a0dd62585b94966dfe205f3c9c6a658577c7cf1a9ee7 |
| hotel_policy_facts_cleveland-akron-canton-oh.json | 8cc741b189981cc3c04cf6e08adb0189d39135e63c2709120220711454511d9a |
| hotel_policy_facts_dayton-oh.json | 863bb9f90112e1231f6dccf8930904b567a3c470121b2526d1c991a86ac4a19b |
| hotel_exclusions.json | 70e1a0e34bcc14e55a893ec71bd5bf7d20054373753a29b6beba6c351d32903c |
| identity_routing.json | 06ae08848d4c6f71c3d6a882b2fec0dfca93cfd5bf51d3af4e08bb8e6350894e |
| seed_businesses.csv | be85ebf72e69c1e036c84531fe205ba2c902f692c437efa9ce4ad646dd9f81a5 |
| policy_migration_decisions.json | d1b7e6838e3ccf996ca81445f6195f23bcb2546582561985028daf8e2cf9ddf8 |
| hotel_worker_approvals.json | 590726f6a660c9d432a9820e106ea15233bdea221e37956655ffec62cbf28cd6 |

`hotel_policy_facts_indianapolis-in.json` does not exist.

## 23. Remaining risks

- Visit Indy and some county lodging widgets are JavaScript-hydrated; corridor hotels beyond official static directories were filled from brand-locator research and are mostly IDENTITY_PROVISIONAL.
- Several brand destination indexes are bot-walled. Routing is assessment only.
- Some addresses for provisional properties need capture-time confirmation, especially shared-address campus and dual-brand pairs.
- Fountain-Fletcher has no hotel corridor; a later hotel opening there would require a corridor amendment.
- Utility dining/brewery/event inventories are official indexes, not complete property-level patio lists.
- Broad Ripple and north-central corridors are thin (2 and 1 hotels). Geography was not redrawn.

## 24. Every unresolved property’s single next action

Complete per-property actions are in `indianapolis_final_partition_001.json` and the founder-review CSV.

| Count | final_state | Next action |
|---:|---|---|
| 89 | AWAITING_IDENTITY_RESOLUTION | Resolve the property's identity before binding any policy evidence to it. |
| 35 | AWAITING_PROPERTY_LEVEL_URL | Recover this property's own official page, not a brand index or tourism listing. |
| 29 | AWAITING_POLICY_OBSERVATION | Observe the pet policy on the property's own official page and capture an artifact. |

## 25. Exact founder-review output path

`C:\Atlas-Grok-Indianapolis-Revalidate\atlas-dashboard\data\operator_evidence\indianapolis-founder-review-001\outgoing\work-browser-pass-001\`

16 batches (`batch-001` through `batch-016`), plus rollup CSV/manifest and screenshot queue. `review_status` is `NOT_STARTED`. No founder approval was conducted.

## 26. Confirmation that no merge, publication, or deployment occurred

Confirmed. No merge, Netlify, or assemble-production command was run. Indianapolis is unpublished and absent from production assembly.

## 27. Confirmation that no Ohio or shared platform authority was modified

Confirmed. Shared canonical contracts (`contracts/census.py`, `partition.py`, `policy_schema.py`, `identity_key.py`, market assignment, assembler, renderer, homepage) were not edited. Discovery registration added Indianapolis-only map entries. Ohio census, partition, policy, exclusion, routing, seed, migration, approval, release-contract, and Cleveland governance files are byte-identical to the pre-revalidation hashes.

The original Indianapolis worktree was not cleaned, reset, rebased, staged, or committed.

## 28. Recommended next step

Founder and Claude review of this unpublished package. The first operational follow-on is the 153-row browser-review queue at the path in section 25. Do not publish hotels and do not create an Indianapolis release contract from this factory.

## 29. Status

**FOUNDER_AND_CLAUDE_REVIEW_REQUIRED**

Technical result only: **REVALIDATED_UNPUBLISHED**

This is not integration authorization.

## 42. Commit SHA

Package commit: `62fafdc3291b7f8bbd6cfeaeb9327cd022f4126a`

Pushed on `grok/ptf-indianapolis-revalidation-001`. Not merged. The tip SHA after this handoff update is the branch HEAD.
