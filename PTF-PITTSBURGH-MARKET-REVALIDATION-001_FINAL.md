# PTF-PITTSBURGH-MARKET-REVALIDATION-001 — Final founder handoff

**Status: `FOUNDER_AND_CLAUDE_REVIEW_REQUIRED`**

**Technical revalidation result: `REVALIDATED_UNPUBLISHED`**

This is the founder handoff for the Pittsburgh factory port onto canonical `fea73de`. It records measured counts from the destination artifacts. The original Pittsburgh source worktree was not modified. No commit, push, merge, publication, or deployment was performed.

`REVALIDATED_UNPUBLISHED` is the technical result only. This branch is not integration-eligible until founder and Claude review are complete.

---

## 1. Destination preflight

Recorded 2026-08-15 22:26:37 -04:00.

| Check | Required | Measured |
|---|---|---|
| Root | `C:\Atlas-Grok-Pittsburgh-Revalidate` | Yes |
| Working directory | `C:\Atlas-Grok-Pittsburgh-Revalidate\atlas-dashboard` | Yes |
| Branch | `grok/ptf-pittsburgh-revalidation-001` | Yes |
| HEAD | `fea73de1ec699289cf04b88fd7069cf23fa4d735` | Yes |
| Local `main` / `origin/main` | `fea73de1ec699289cf04b88fd7069cf23fa4d735` | Yes |
| Starting status | clean | Yes |
| Ending HEAD | `fea73de1ec699289cf04b88fd7069cf23fa4d735` | Unchanged. No commit. |

Worktree registration: `C:/Atlas-Grok-Pittsburgh-Revalidate` → `fea73de` `[grok/ptf-pittsburgh-revalidation-001]`.

---

## 2. Source-worktree proof (read-only)

| Check | Authorized | Measured after implementation |
|---|---|---|
| Root | `C:\Atlas-Grok-Pittsburgh` | Yes |
| Project | `C:\Atlas-Grok-Pittsburgh\atlas-dashboard` | Yes |
| Branch | `grok/ptf-pittsburgh-market-001` | Yes |
| HEAD | `2d885d139950f93dba4f02edd04fa849781a8a0a` | Yes, unchanged |
| Source handoff | `C:\Atlas-Grok-Pittsburgh\PTF-PITTSBURGH-MARKET-BUILD-001_FINAL.md` | Present |
| Writes | none | Source status is still the original uncommitted BUILD-001 package |

No write, commit, reset, clean, delete, rename, or rebase was performed under `C:\Atlas-Grok-Pittsburgh`. Indianapolis, Louisville, and Ohio worker worktrees were not used as sources and were not modified.

---

## 3. Current governing contracts (`fea73de`)

Used as-is. No contract, assembler, policy-schema, withholding, or release-contract file was edited.

- `ptf-market/1.1`
- `ptf-market-identity-census/1.1`
- `ptf-market-final-partition/1.1` (`enums.PARTITION_SCHEMA`)
- `ptf_identity_key/1.0`
- `ptf-source-families/1.0`
- Policy authority schema 1.2 — Ohio only; Pittsburgh has no policy package

Ohio published profile count on this baseline remains **156** (Columbus 88 + Cleveland 21 + Dayton 47). Cincinnati stays registered, unpublished, contractless, and not assembled. Pittsburgh now follows that same honest-zero pattern.

---

## 4. `2d885d1` → `fea73de` material changes

```
275d4e6  migrate policy authority to schema 1.2
2092dae  close Phase F with founder-attested approvals
aaab32f  verify Cleveland capture artifacts
fea73de  close Pass 1 governance with founder re-attestations
```

Those commits change Ohio policy authority, Cleveland evidence binding, renderer/canonical view, and Pass 1 governance. They do **not** change census, partition, identity-key, geography, or discovery `market_config` / `source_families` contracts.

Pittsburgh schema-1.2 drift: **nothing to migrate**. There is still no Pittsburgh policy document.

Shared files were not overwritten with their `2d885d1` counterparts. Pittsburgh intent was replayed onto the current files as the smallest additive hunks.

---

## 5–8. Inventory, dispositions, and measured counts

### Source measured counts (BUILD-001 handoff)

113 candidates = 96 canonical + 2 confirmed duplicates + 15 boundary excluded.

Census 96. Published 0. Verified no-pets 0. Out of category 3. Unresolved / queue 93.

### Recomputed destination counts

Identical membership. Regenerated from the same candidate table through current `assign_hotels` / census / partition validators.

| Measure | Source | Destination | Diff |
|---|---:|---:|---|
| Candidates | 113 | 113 | 0 |
| Canonical census | 96 | 96 | 0 |
| Confirmed duplicates | 2 | 2 | 0 |
| Boundary excluded | 15 | 15 | 0 |
| Category excluded (in census) | 3 | 3 | 0 |
| Closed / converted (in census) | 1 | 1 | 0 |
| Published | 0 | 0 | 0 |
| Verified no-pets | 0 | 0 | 0 |
| Unresolved | 93 | 93 | 0 |
| Queue | 93 | 93 | 0 |
| `IDENTITY_CONFIRMED` / `PROVISIONAL` | 58 / 38 | 58 / 38 | 0 |
| Utilities / quoted 24/7 vets | 12 / 2 | 12 / 2 | 0 |
| Corridor assignment diffs | 0 | 0 | 0 |

Candidate-ledger final dispositions (113):

| Disposition | Count |
|---|---:|
| `canonical_census` | 54 |
| `identity_unresolved` | 38 |
| `boundary_excluded` | 15 |
| `category_excluded` | 3 |
| `confirmed_duplicate` | 2 |
| `closed_or_converted` | 1 |

`54 + 38 + 3 + 1 = 96` census rows. No candidate disappeared.

### Old-path → new-path disposition

| Old path | Category | New path / action |
|---|---|---|
| `scripts/pettripfinder/build_pittsburgh_market_001.py` | 1. Recreate | Same path. Metadata restamped. Candidate table preserved. |
| `scripts/pettripfinder/discovery/config/pittsburgh_pa.json` | 1. Recreate | Same path. Added missing Strip / Lawrenceville cell. |
| `tests/pettripfinder/test_pittsburgh_market_001.py` | 1. Recreate | Same path. Added revalidation and queue `identity_key` gates. |
| `launch_packages/pettripfinder/markets/pittsburgh-pa.json` | 1. Recreate | Same path. `market_name` set to `Pittsburgh, Pennsylvania`. |
| `identity_census/pittsburgh-pa.json` | 1. Recreate | Regenerated by builder. `base_commit=fea73de`. |
| `pittsburgh_final_partition_001.json` | 1. Recreate | Regenerated. Filename kept so the current assembler glob finds it. |
| `markets/reports/pittsburgh-pa_*.json` (5 reports) | 1. Recreate | Regenerated. |
| `markets/coverage/pittsburgh-pa.json` | 1. Recreate | Regenerated from the source builder’s advisory coverage file. Population `2371000` remains uncalibrated and is not a gate. See §18. |
| `discovery/market_config.py` | 2. Shared replay | Current file + `"pittsburgh-pa": "pittsburgh_pa.json"`. |
| `discovery/source_families.py` | 2. Shared replay | Current file + nine Pittsburgh concrete-source mappings. |
| `tests/.../test_market_config.py` | 2. Shared replay | Current file + Pittsburgh load test. |
| `tests/.../test_source_families.py` | 2. Shared replay | Current file + Pittsburgh family assertions. |
| `tests/pettripfinder/test_markets.py` | 2. Shared replay | Current 4-market list + `pittsburgh-pa`. |
| `data/market_research/pittsburgh/*` | 3. Gitignored research | Regenerated, including the additional audit ledgers the current work order requires. |
| `data/operator_evidence/pittsburgh-founder-review-001/*` | 3. Gitignored queue | Regenerated with `identity_key`, `hotel_id`, SHA-256, rollup, and screenshot queue. |
| Ohio policy / seed / routing / release / assembler files | 5. Forbidden | Not transferred. |
| `PTF-PITTSBURGH-MARKET-BUILD-001_FINAL.md` | 4. Cite only | Not copied. Cited as the read-only source handoff. |

No category-6 unresolved source artifact required founder review before this port.

---

## 9. Boundary decisions

Visitor market, not the municipal line and not the full MSA. All fifteen named clusters retain the source INCLUDE/EXCLUDE decisions. No expansion into Cleveland, Ohio, West Virginia, Erie, or other separately marketed destinations.

**Included corridors (canonical hotel counts):**

| Ring | Corridor | Count |
|---|---|---:|
| Primary core | Downtown / Cultural District | 20 |
| Primary core | North Shore / Stadium District | 6 |
| Primary core | Strip District / Lawrenceville | 2 |
| Primary core | Oakland / University Medical | 7 |
| Primary core | Shadyside / East Liberty / Bakery Square | 11 |
| Primary core | South Side / Station Square | 4 |
| Airport / suburban | Green Tree / Parkway West | 2 |
| Airport / suburban | Robinson Township | 10 |
| Airport / suburban | Moon / Coraopolis / PIT | 14 |
| Outer ring | Monroeville / Parkway East | 5 |
| Outer ring | Homestead / Waterfront / West Mifflin | 2 |
| Outer ring | North Hills / McCandless / Wexford | 1 |
| Outer ring | Cranberry Township | 7 |
| Outer ring | South Hills / Bridgeville / Mt. Lebanon | 3 |
| Outer ring | Harmarville / Pittsburgh Mills | 2 |
| | **Total** | **96** |

Cranberry, South Hills, and Allegheny Valley remain included on Greater Pittsburgh Hotel Association Pittsburgh-member evidence from 2026-08-15.

**Excluded (ledger only, 15):** Beaver County / Monaca / Ambridge hotels; Washington PA / Meadow Lands / Southpointe; Greensburg / Latrobe; Nemacolin; Seven Springs. Places with no admitted identity: Beaver Falls / Beaver city; Butler city proper; New Castle; Johnstown; Erie; Wheeling WV; Youngstown OH.

ZIP 15205 is still not attached to any corridor. ZIP 15219/15222 still split Downtown / Strip / Station Square by explicit identity assignment.

---

## 10. Corridor decisions

Current `assign_hotels(..., fail_closed=True)` reproduces every stored corridor, basis, and value.

- Canonical lodging with a corridor: 96
- Unassigned: 0
- `corridor: null`: 0
- Stored-versus-recomputed diffs: **0**
- Review artifact: `data/market_research/pittsburgh/corridor_assignment_review.json`

No empty corridor was removed. Thin corridors (North Hills 1, Waterfront/Green Tree/Strip/Allegheny Valley 2) are preserved as first-pass facts.

---

## 11. Census and entity resolution

Every source candidate is on `candidate_ledger.json`. Identity keys were recomputed with `ptf_identity_key/1.0`. Census validates at 1.1 with `market_states=["PA"]`. Every row is `market_id=pittsburgh-pa`, `state=PA`, `policy_state=POLICY_NOT_VERIFIED`.

Confirmed duplicates (ledger only): Renaissance Pittsburgh Hotel → The Atterbury Hotel; Drury Inn & Suites Pittsburgh → Drury Plaza Hotel Pittsburgh Downtown.

Category excluded (in census): Inn on Negley; Choderwood; The Maverick by Kasa.

Closed / converted (in census): Ace Hotel Pittsburgh. Ace and Maverick share `120 South Whitfield Street` (`SHARED_ADDRESS`).

Cross-market isolation: Pittsburgh identity keys are disjoint from Columbus, Cleveland, Dayton, and Cincinnati censuses. No Pittsburgh routes in `identity_routing.json`. No Pittsburgh seed rows.

---

## 12. Partition-state mapping

Current `fea73de` enums only. Source blocker function produced the same states; no obsolete state was transferred.

| Final state | Count | Terminal? |
|---|---:|---|
| `AWAITING_POLICY_OBSERVATION` | 44 | No |
| `AWAITING_IDENTITY_RESOLUTION` | 38 | No |
| `AWAITING_OFFICIAL_URL` | 9 | No |
| `OUT_OF_CURRENT_CATEGORY` | 3 | Yes |
| `AWAITING_PROPERTY_LEVEL_URL` | 1 | No |
| `AWAITING_CENSUS_REVIEW` | 1 | No |
| `PUBLISHED_PET_FRIENDLY` | 0 | Yes |
| `VERIFIED_NO_PETS` | 0 | Yes |
| **Total** | **96** | |

`0 + 0 + 3 + 93 = 96`. Census keys == partition keys. Every unresolved row has exactly one current-contract next action.

---

## 13–17. Files

### Tracked files created

1. `atlas-dashboard/scripts/pettripfinder/build_pittsburgh_market_001.py`
2. `atlas-dashboard/scripts/pettripfinder/discovery/config/pittsburgh_pa.json`
3. `atlas-dashboard/tests/pettripfinder/test_pittsburgh_market_001.py`
4. `atlas-dashboard/launch_packages/pettripfinder/markets/pittsburgh-pa.json`
5. `atlas-dashboard/launch_packages/pettripfinder/identity_census/pittsburgh-pa.json`
6. `atlas-dashboard/launch_packages/pettripfinder/pittsburgh_final_partition_001.json`
7. `atlas-dashboard/launch_packages/pettripfinder/markets/coverage/pittsburgh-pa.json`
8. `atlas-dashboard/launch_packages/pettripfinder/markets/reports/pittsburgh-pa_source_registry.json`
9. `atlas-dashboard/launch_packages/pettripfinder/markets/reports/pittsburgh-pa_duplicate_ledger.json`
10. `atlas-dashboard/launch_packages/pettripfinder/markets/reports/pittsburgh-pa_routing_assessments.json`
11. `atlas-dashboard/launch_packages/pettripfinder/markets/reports/pittsburgh-pa_founder_review_queue.json`
12. `atlas-dashboard/launch_packages/pettripfinder/markets/reports/pittsburgh-pa_utility_inventory.json`

This handoff (not an implementation artifact of the launch package):

13. `C:\Atlas-Grok-Pittsburgh-Revalidate\PTF-PITTSBURGH-MARKET-REVALIDATION-001_FINAL.md`

### Shared files modified (Pittsburgh intent replayed onto `fea73de`)

1. `scripts/pettripfinder/discovery/market_config.py` — register `pittsburgh-pa`
2. `scripts/pettripfinder/discovery/source_families.py` — nine concrete sources
3. `tests/pettripfinder/test_markets.py` — add `pittsburgh-pa` to the committed id list
4. `tests/pettripfinder/discovery/test_market_config.py` — Pittsburgh load test
5. `tests/pettripfinder/discovery/test_source_families.py` — family assertions

Diffstat of those five files: `5 files changed, 36 insertions(+), 1 deletion(-)`.

### Gitignored artifacts regenerated

`data/market_research/pittsburgh/`: `source_registry.json`, `candidate_ledger.json`, `duplicate_ledger.json`, `boundary.json`, `boundary_exclusion_ledger.json`, `rename_conversion_history.json`, `corridor_assignment_review.json`, `reconciliation_report.json`, `routing_assessments.json`, `str_market_signal.json`, `utility_inventory.json`.

`data/operator_evidence/pittsburgh-founder-review-001/`: `batch-001` … `batch-010` review CSV + manifest, `queue-index.json`, `queue-rollup.csv`, `queue-rollup-manifest.json`, `screenshot-queue.json`.

### Obsolete / rejected

Source `PENDING_OPERATOR_REVIEW` queue status was mapped to current `NOT_STARTED`. Source `market_name: Pittsburgh` was restated as `Pittsburgh, Pennsylvania` to match the current expected identity. Source `base_commit` / `worker_branch` were restamped to this worktree. Source FINAL.md was not copied.

### Forbidden files (not created or modified)

No `hotel_policy_facts_pittsburgh-pa.json`, policy migration records, approvals, withholding authority, `hotel_exclusions.json` Pittsburgh rows, `identity_routing.json` Pittsburgh routes, seed rows, publication records, release contracts, Netlify config, assembler edits, or generated production pages.

---

## 18. Discovery and coverage

Discovery config is registered and loadable. Fifteen cells now match the fifteen committed corridors. Coordinates remain low-precision seed points, not a parcel boundary.

Source-family mappings on the current `fea73de` file:

| Source | Family |
|---|---|
| `visit_pittsburgh`, `cultural_trust` | CVB |
| `paacc`, `east_liberty_chamber`, `gpha`, `parks_conservancy` | DIRECTORY |
| `city_parks` | REGISTRY |
| `avets`, `veg_pittsburgh` | CHAIN |

**Coverage-file decision:** keep the source builder’s advisory `markets/coverage/pittsburgh-pa.json`. The source already authored it. Population `2371000` is an uncalibrated prior, not a cited visitor-boundary census, and nothing gates on it. A new coverage population was not invented.

---

## 19. Founder-review queue

Tracked index: `launch_packages/pettripfinder/markets/reports/pittsburgh-pa_founder_review_queue.json`.

Operator batches (gitignored): `data/operator_evidence/pittsburgh-founder-review-001/`.

Reconciliation:

- every queue row has `identity_key`
- that key equals the matching census key
- that key equals the matching unresolved partition key
- queue set == 93 unresolved partition identities
- zero duplicates, zero omissions
- `hotel_id == identity_key` on every row
- `review_status = NOT_STARTED`
- each row has corridor, official candidate URL, blocker/classification, requested evidence, one next action, and batch id
- batches of 10 (batch-010 has 3)
- rollup CSV + manifest SHA-256 `11e2b56e65313a8df0364146f27c65387a093b1676a0dd8ef2c9f1811b884ca9`
- screenshot queue has 93 `NOT_CAPTURED` targets and zero screenshots (this work order does not browse or capture)

Do not browser-approve, promote, or publish from this queue in this work order.

---

## 20. Utility revalidation

Twelve advisory rows, not seed inventory.

| Category | Count |
|---|---:|
| Dedicated off-leash dog parks | 6 |
| Trails / greenways | 1 |
| Emergency veterinary | 2 |
| Authoritatively verified 24/7 | 2 |
| Dog-friendly dining | 2 |
| Dog-friendly brewery | 1 |

`as_of` 2026-08-15. `revalidation_due` 2027-02-11 (180 days). Both 24/7 claims quote the facility’s own page (Avets; VEG Pittsburgh). Dining/brewery rows remain `TOURISM_BLOG_ONLY`.

Source research did not include recurring pet events or farmers markets. None were invented.

---

## 21. Tests and commands

Generator:

```
python -m scripts.pettripfinder.build_pittsburgh_market_001
```

Pittsburgh-specific + discovery/market:

```
python -m pytest tests/pettripfinder/test_pittsburgh_market_001.py tests/pettripfinder/discovery/test_source_families.py tests/pettripfinder/discovery/test_market_config.py tests/pettripfinder/test_markets.py -q
```

→ **69 passed**, 0 failed, 15.86s (first landing). After spec-gap edits the same surface plus homepage/assembler was **184 passed, 5 skipped**, 52.71s.

Touched-surface PetTripFinder (first landing):

```
python -m pytest tests/pettripfinder/contracts/ tests/pettripfinder/test_markets.py tests/pettripfinder/test_market_ownership.py tests/pettripfinder/test_market_isolation.py tests/pettripfinder/test_per_market_release_contracts.py tests/pettripfinder/test_homepage_market_awareness.py tests/pettripfinder/test_global_assembler.py tests/pettripfinder/discovery/test_source_families.py tests/pettripfinder/discovery/test_market_config.py tests/pettripfinder/test_pittsburgh_market_001.py -q
```

→ **708 passed, 5 skipped**, 125.19s.

Full regression after spec-gap edits:

```
python -m pytest tests -q
```

| Command | Collected | Passed | Failed | Skipped | Runtime |
|---|---:|---:|---:|---:|---|
| Full `tests` (`-v`, after first landing) | 11221 | 11090 | 0 | 131 | 789.35s |
| Full `tests` (`-q`, after spec-gap edits) | 11222 | **11091** | **0** | **131** | 976.62s |

No existing test was weakened, skipped, deleted, or rewritten to obtain a pass. Ohio 156 published-profile and Phase F / Cleveland recertification tests remained green.

---

## 22. Implementation sequence (what was done)

1. Confirmed destination `fea73de` clean and source `2d885d1` identity.
2. Copied only Pittsburgh-owned factory files.
3. Replayed Pittsburgh intent onto the five current shared files.
4. Added the Strip / Lawrenceville discovery cell and the four utility source-family mappings.
5. Restamped builder metadata to this work order and `fea73de`.
6. Set `market_name` to `Pittsburgh, Pennsylvania`.
7. Regenerated artifacts. Compared identity sets, corridors, states, queue, utilities, and ledger to the source: zero membership drift.
8. Added current-work-order audit ledgers, queue SHA-256 / rollup / screenshot index, and `NOT_STARTED` status.
9. Ran targeted, touched-surface, and full regression.
10. Wrote this handoff. Left the destination dirty.

---

## 23. Quality gates

| Gate | Result |
|---|---|
| Destination still `fea73de` | **Held** |
| Source unread/unmutated | **Held** |
| Boundary unchanged | **Held** |
| 113 = 96 + 2 + 15 | **Held** |
| Census / partition 96 = 96 | **Held** |
| 96 × `POLICY_NOT_VERIFIED` | **Held** |
| Queue `identity_key` set = 93 unresolved | **Held** |
| `hotel_id == identity_key` | **Held** |
| Corridor diffs = 0 | **Held** |
| Isolation from Ohio | **Held** |
| Unpublished / not assembled / no release contract | **Held** |
| No Pittsburgh policy document | **Held** |
| Full tests green | **Held** (11091 passed, 131 skipped) |
| Handoff status `FOUNDER_AND_CLAUDE_REVIEW_REQUIRED` | **This document** |

---

## 24. Stop conditions (none fired)

The destination was clean and current. The source worktree was unambiguous. Regenerated membership matched the source. No contract rejected a row. No Ohio authority file needed editing. No live collection was required.

---

## 25. Git status and review posture

HEAD remains `fea73de1ec699289cf04b88fd7069cf23fa4d735`.

Tracked dirty surface:

```
 M scripts/pettripfinder/discovery/market_config.py
 M scripts/pettripfinder/discovery/source_families.py
 M tests/pettripfinder/discovery/test_market_config.py
 M tests/pettripfinder/discovery/test_source_families.py
 M tests/pettripfinder/test_markets.py
?? launch_packages/pettripfinder/identity_census/pittsburgh-pa.json
?? launch_packages/pettripfinder/markets/coverage/pittsburgh-pa.json
?? launch_packages/pettripfinder/markets/pittsburgh-pa.json
?? launch_packages/pettripfinder/markets/reports/pittsburgh-pa_duplicate_ledger.json
?? launch_packages/pettripfinder/markets/reports/pittsburgh-pa_founder_review_queue.json
?? launch_packages/pettripfinder/markets/reports/pittsburgh-pa_routing_assessments.json
?? launch_packages/pettripfinder/markets/reports/pittsburgh-pa_source_registry.json
?? launch_packages/pettripfinder/markets/reports/pittsburgh-pa_utility_inventory.json
?? launch_packages/pettripfinder/pittsburgh_final_partition_001.json
?? scripts/pettripfinder/build_pittsburgh_market_001.py
?? scripts/pettripfinder/discovery/config/pittsburgh_pa.json
?? tests/pettripfinder/test_pittsburgh_market_001.py
```

Plus this handoff at the worktree root.

- Built and revalidated against canonical `fea73de`
- `FOUNDER_AND_CLAUDE_REVIEW_REQUIRED`
- Original Pittsburgh worktree preserved unchanged
- Revalidation worktree uncommitted
- Git status intentionally dirty only with approved Pittsburgh artifacts
- Not published
- Not deployed
- No policy authority created

No commit, push, merge, rebase, reset, clean, publish, or deploy was performed.

Before any later Pittsburgh commit, fetch `origin/main`. If it has advanced, update and rerun the complete Pittsburgh and touched-surface regression suite.

---

## Confirmation that no prohibited action occurred

The following were **not** done:

- Commit, push, merge, rebase, reset, `git clean`
- Publish or deploy / Netlify
- Install packages
- Write to `C:\Atlas-Grok-Pittsburgh`, `C:\Atlas`, Indianapolis, Louisville, or any Ohio worktree
- Create or modify Pittsburgh hotel-policy facts, exclusions, seeds, identity routing, or release contracts
- Modify `assemble_production_site.py`, `assemble_netlify_bundle.py`, `build_market_authorities.py`, or `build_market_manifest.py`
- Approve policy records or promote browser findings
- Spawn research subagents
- Bypass robots.txt, CAPTCHAs, authentication walls, or rate limits
- Represent inaccessible or aggregator evidence as verified policy
- Treat a routing assessment as `ROUTING_CONFIRMED`
- Treat `REVALIDATED_UNPUBLISHED` as integration eligibility

---

## Recommended next step (not this work order)

1. Founder review and Claude review of this dirty tree, the queue `identity_key` reconciliation, and the Git diff.
2. Only after both reviews complete may a later order consider commit or integration.
3. A still-later work order may run browser review of the 93-row queue. That is the first work allowed to observe property-level pet policy.
