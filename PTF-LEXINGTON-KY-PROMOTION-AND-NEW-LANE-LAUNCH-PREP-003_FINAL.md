# PTF-LEXINGTON-KY-PROMOTION-AND-NEW-LANE-LAUNCH-PREP-003 — FINAL

Lexington is registered, sealed, validated on the redesigned release lane, and
composed into an exact final candidate. **Nothing is deployed, nothing is
activated, and no authorization exists.** Production is untouched: eleven live
markets, 803 profiles, 966 routes on deploy `6a9e0476`.

---

## PRECHECK

| | |
|---|---|
| Worktree | `C:\Atlas-Lexington-Launch-V2` |
| Branch | `worker/ptf-lexington-new-lane-launch-003` |
| HEAD at start | `d335c509e8e4b0f54796d07c4bd4abdff00cb801` |
| Tree | clean |
| Lineage | the Toledo launch commit; `2163c4e` (Cincinnati-live) is its merge base with the throughput branch |

---

## CURRENT VERIFIED LIVE

Derived from `deploy/netlify/deployment_records/`, the global deployment
manifest and the committed pin, which agree with zero problems.

| | |
|---|---|
| Deployment id | `6a9e047690ec8bdaf99bcad2` |
| Release digest | `895248738c79bc27f26da5bba1d2a490361ce6bd4959698adf3fb6f892aad8b0` |
| Sitemap digest | `dfdac840be527d5431d0752e702b55fd41d3ee0d2f3635bed6796044d869d56a` |
| Markets | 11 |
| Profiles | 803 |
| Routes | 966 |

Participating: cincinnati-oh, cleveland-akron-canton-oh, columbus-oh, dayton-oh,
grand-rapids-holland-mi, indianapolis-in, louisville-ky, milwaukee-wi,
pittsburgh-pa, st-louis-mo, **toledo-oh**. Detroit remains registered and
withheld.

---

## THROUGHPUT ENGINEERING INTEGRATION

`origin/worker/atlas-throughput-001` forked at `2163c4e`, the Cincinnati-live
commit, and never saw Louisville's successor, Pittsburgh, Indianapolis or
Toledo. It was merged **into** the Toledo-live lineage rather than the reverse,
so current production is the base. Merge commit `fa08b22`.

Conflict classification — one conflict:

| Class | Path | Resolution |
|---|---|---|
| STALE GENERATED STATE | `reports/factory_throughput_001_test_inventory.{json,md}` | Neither side wins. Regenerated from the MERGED tree by `regression_inventory.py`: 400 modules / 1,589 sites, up from 393 (Toledo) and 397 (throughput). |

Three shared files auto-merged with orthogonal hunks (`assemble_production_site`,
`regression_lanes`, `test_global_assembler`). Every production-data path —
`deploy/netlify/**`, `ptf_global_authority_manifest.json`,
`hotel_exclusions.json`, `tests/pettripfinder/pins/**` — was byte-identical to
Toledo-live after the merge. No stale Cincinnati-only generated state was
imported over current live state.

---

## ONE-TIME INTEGRATION AUDIT

Regression V2 classified the integration `FULL_REGRESSION_REQUIRED = YES` on six
independent grounds (two UNCLASSIFIED paths, shared runtime, assembler,
DEPLOYMENT_CHANGE, AUTHORITY_CHANGE). Exactly one broad run was executed.

| | |
|---|---|
| Collected | 17,874 |
| Failures | 164 |
| Baseline (`f75aa95`) | 160 |
| PRE_EXISTING | 160 |
| TRUE_NEW_FAILURE | 4 |
| TRUE_NEW after closure | **0** |
| Second broad run required | NO |
| Remote broad jobs | 0 |
| Wall clock | 4,588.5 s (1 h 16 m) |

Each TRUE_NEW node was fixed at its cause and re-run **by node id**:

1. `test_atlas_throughput_003 :: test_current_verified_live_agrees_across_record_manifest_and_pin`
   — a DEPLOYMENT_EPOCH_INVARIANT restating deploy `6a9d33f5` and 786 profiles
   as literals. Now reads the committed live pin; the agreement of record,
   manifest and pin is still what the test checks.
2. `test_atlas_throughput_003 :: test_case_17_the_stale_pittsburgh_like_package_cannot_remove_newer_indianapolis_like_state`
   — the same epoch literal. The proposed release is current live with the
   stale package substituted, so its total is live's, whatever epoch live is at.
3. `test_atlas_throughput_004 :: test_case_2_a_second_process_hits_the_persistent_cache`
   — the committed Dayton fixture package was sealed against the Cincinnati
   parent, so rule N failed it and every bundle built from it published
   UNTRUSTED. Re-sealed at the current parent with the identical record set;
   `dayton_package()` now selects **by parent** instead of by the last filename
   alphabetically, which was an arbitrary pick that only looked correct while
   one package existed.
4. `test_atlas_throughput_004 :: test_the_fast_lane_reports_market_build_required_no_on_a_trusted_bundle`
   — the same stale parent plus an undeclared read. `bundle_cache_closure.json`
   enumerates every registered market's contract and release contract by name;
   Toledo's pair and Lexington's pair were missing, so the cache called them
   undeclared and published every bundle UNTRUSTED. Re-measured, +4 paths.

Nothing was deselected, relaxed or retired.

---

## LEXINGTON SOURCE

`C:\Atlas-Lexington-Hardened-V1`, branch `worker/ptf-lexington-new-market-001`,
HEAD `f1e0435`, clean. Two additive commits over the same `2163c4e` base, 35
added files and one shared file. Only the Kentucky OSM extract entry was taken
from that shared file, inserted surgically (11 lines) rather than reformatted.

---

## LEXINGTON QUALITY FREEZE

Read from `lexington_ky_shadow_market_002.json`, never typed, and reproduced
EXACTLY by the count gate before any row was allowed to move:

| | |
|---|---|
| Census | 61 |
| Clean pet-friendly | 28 |
| Clean verified-no-pets | 14 |
| Resolved | 42 |
| Unresolved | 19 |
| Corridors | 7 |
| Evidence records | 42, every one with a content hash and an exact quote |

---

## REGISTRATION

Built by `lexington_ky_registration_003.py` through the owning contracts.

- `markets/lexington-ky.json` — `ptf-market/1.1`, 7 corridors, route mode
  `market_prefixed`, `census_membership_basis = MARKET_GEOGRAPHY`.
- `identity_census/lexington-ky.json` — `ptf-market-identity-census/1.1`, 57
  admitted, validates with zero issues, every key canonical.
- `lexington_ky_final_partition_001.json` — every registered identity once.
- `markets/authority/lexington-ky/{seed_businesses.csv, hotel_exclusions.json, identity_routing.json, affiliate_destinations.json}`
- `hotel_policy_facts_lexington-ky.json`
- `deploy/netlify/release_contracts/lexington-ky.json`
- The three generated globals regenerated from the shards; `check_generated_artifacts()` is empty.

**Why MARKET_GEOGRAPHY.** A postal-code partition of these corridors does not
exist: ZIP 40505 falls in both Hamburg and I-75/Winchester Road, 40509 in both
Hamburg and Richmond Road, and seventeen census rows state no ZIP at all. The
contract's own basis for this shape (Grand Rapids, Fort Wayne) is used, and the
corridors classify by `explicit_hotel_ids` reproducing the shadow's assignment
identity for identity.

---

## AUTHORITY MIGRATION

Three reshapings, none of them new research:

- **Identity key.** The shadow keyed `name--street` to break two same-name
  collisions. `ptf_identity_key/1.0` keys on the canonical name alone. A
  colliding group admits at most the one row carrying a published fact; nothing
  is renamed.
- **City and postal.** Filled from the row's OWN first-party evidence
  (`postal_on_page`, `address_on_page`), with the basis recorded on the row.
- **Official URL.** A row this market READ takes its official URL from the page
  the read came from, which is also the repaired route — the 002 order found
  five rows sharing one wrong URL (a Comfort Inn in Winchester) and re-bound
  each on the address its own page states. Omitting this field was a defect of
  this order's own first pass: it made the evidence gate call two
  Hilton-family properties WRONG_PROPERTY, and supplying the field the shadow
  already stated closed both without touching a gate.

---

## MODERN EVIDENCE GATE

| | Original clean | Valid modern | Held |
|---|---|---|---|
| Pet-friendly | 28 | **20** | 8 |
| Verified no-pets | 14 | **10** | 4 |
| Total | 42 | 30 | 12 |

Plus three unresolved rows held by the identity contract: **15 held in total**,
each named in `lexington_ky_identity_holds_003.json`.

**IDENTITY_HOLD (3)** — Holiday Inn Express (1935 Stanton Way), Red Roof Inn
(1980 Haggard Court), Red Roof Inn (2651 Wilhite Drive). All three were already
unresolved and publish nothing.

**CROSS_MARKET_IDENTITY_COLLISION (1)** — Holiday Inn Express, 2255 Buena Vista
Road. Cleveland already publishes the identity key `holiday inn express` as
VERIFIED_NO_PETS. A published identity key is globally unique in this repository
(836 across eleven live markets, no duplicate) and
`hotel_exclusions.validate` refuses the second by name.

**MODERN_EVIDENCE_GATE_HOLD (5)** — `first_party_binding` refuses:

| Identity | Class | Why |
|---|---|---|
| Clarion Hotel Conference Center Lexington North | AMENITY_CHIP_ONLY | "Pets Allowed: Yes" is a label, not a policy |
| Econo Lodge | AMENITY_CHIP_ONLY | same |
| Sleep Inn | AMENITY_CHIP_ONLY | same |
| Hilton Lexington/Downtown | SERVICE_ANIMAL_ONLY | "Service animals only" is not a refusal the reader reads |
| The Sire Hotel | SERVICE_ANIMAL_ONLY | same |

**PAID_PROVENANCE_HOLD (6)** — Days Inn, Holiday Inn Express & Suites Lexington
Dtwn Area-Keeneland, Holiday Inn Lexington - Hamburg, La Quinta Inn & Suites
Lexington South / Hamburg, La Quinta Inn - Lexington, Super 8 by Wyndham
Lexington Winchester Rd. Their evidence was bought through Firecrawl and run
`lexington_ky_firecrawl_002` was never ingested into
`ptf_paid_attempt_ledger_001.json` (806 attempts, seven markets, none for
Lexington). Rule O wants the reservation that bought the page including a
request-envelope hash the committed record does not carry, and an invented
provenance hash is worse than a missing one.

**This is the cheapest hold to clear and needs no re-capture.** Ingesting that
run into the paid-attempt ledger takes Lexington to 25 published / 11
verified-no-pets. It is a later order's work; this one will not fabricate a
hash.

No gate was lowered. The evidence gate runs again over the survivors and the
applier raises if it still refuses a row.

---

## SEALED PACKAGE

| | |
|---|---|
| Package id | `pkg-lexington-ky-e5d26fd63bb2d2e2` |
| Package digest | `sha256:e5d26fd63bb2d2e2d3d632134cc40cd832d1a4d4c5e1b82f003aa58dc52c5380` |
| Pet-friendly records | 20 |
| Verified-no-pets records | 10 |
| Census count | 57 |
| Unresolved | 27 |

---

## DATA-ONLY CLASSIFICATION

Two different questions, and conflating them is how a shared change escapes its
regression.

**Registering** Lexington is NOT data-only. `FULL_REGRESSION_REQUIRED = YES`.
The dependencies that widen it, named:

| Path | Class |
|---|---|
| `deploy/netlify/launch_participation.json` | DEPLOYMENT_CHANGE |
| `deploy/netlify/release_contracts/lexington-ky.json` | DEPLOYMENT_CHANGE |
| `scripts/pettripfinder/assemble_production_site.py` | DEPLOYMENT_CHANGE (the partition table a registered market must join) |
| `launch_packages/pettripfinder/lexington_ky_identity_holds_003.json` | UNCLASSIFIED — the classifier has no rule for `*_identity_holds_*.json`; Toledo's file carries the same gap. Teaching it one is shared infrastructure and belongs to a later order. This order will not edit the classifier to make its own change look narrower. |

**A routine Lexington release** is data-only. The fast lane's own receipt records
`CHANGE_CLASS = MARKET_AUTHORITY_DATA_ONLY`,
`FAST_DATA_ONLY_RELEASE_ELIGIBLE = YES`,
`FULL_REGRESSION_REQUIRED_BY_LANE = NO`, remote broad jobs 0.

---

## FAST RELEASE-SAFETY LANE

All fifteen rules PASS. Zero UNKNOWN, zero FAIL.

```
A schema  B identity  C first-party  D policy   E routes
F partition  G collisions  H preservation  I intended delta
J build  K determinism  L hashes  M freshness  N rollback  O paid provenance
```

`FAST_DATA_ONLY_RELEASE_ELIGIBLE = YES`.
Receipt digest `sha256:d72b64ffd74bb60c5cdf40835e44781142dec55494cd6166bd773d31ab463404`.
`PRODUCTION_ACTIVATION_ALLOWED = NO` — the flags are still closed.

Rules C and O each failed on the first pass and each failure is a real finding,
recorded above. Neither was silenced.

---

## CURRENT PARENT RECHECK

Re-read immediately before staging: still deploy `6a9e047690ec8bdaf99bcad2`,
803 profiles, 966 routes, eleven markets, zero problems. Rule N re-checks the
package's declared parent against it and passes.

---

## FINAL CANDIDATE

Composed with Lexington **PARTICIPATING**, because a pre-flip candidate can never
carry the digest a launch produces — the lesson
PTF-TOLEDO-OH-DEPLOYMENT-AND-LAUNCH-AUTHORIZATION-003 paid for. Assembled twice
in a throwaway worktree from a participation document differing from the
committed one in exactly one field, and reproduced **byte-identically**.

| | |
|---|---|
| Candidate digest | `67fe8617b79febb9b2248895441c31ac65931cf9fdcfa4da4f8014ee190cde78` |
| Sitemap digest | `dd0d87f2da07615776016690af64452d42cafc24d3c82e310b5f44efc6f7e611` |
| Markets | 12 |
| Profiles | 823 |
| Routes | 991 |
| HTML pages | 5,025 |
| All gates pass | yes |
| Broken links | 0 |
| `deployment_authorized` | **false** |

Detroit, Nashville, Chattanooga and Fort Wayne all stay out.

---

## RELEASE DIFF

| | Parent | Candidate |
|---|---|---|
| Markets | 11 | 12 |
| Profiles | 803 | 823 |
| Routes | 966 | 991 |

Markets added: `lexington-ky`. Updated: none. Removed: none.
Lexington contributes 20 profiles and 25 routes (20 hotels + 3 corridors + hub +
comparison). Every other market's profile count is identical to live.

**Unexpected profile changes 0. Unexpected route changes 0. Unexpected market
changes 0. Release-index findings: 0.**

---

## CACHE / REUSE

`UNCHANGED_MARKETS_REBUILT = 0` — and that is a fact about what the lane DID,
not a cache hit rate. The redesigned lane never renders an unchanged market:
rule J stages and builds the changed market alone, and rules G/H/I compare
release indexes derived from committed authority. The other eleven markets were
neither built, reused, nor rebuilt.

For the changed market the persistent cache reports a MISS with reason "no entry
for this input key" — Lexington has never been built before, so there is nothing
to reuse and the lane builds it cold.

---

## PERFORMANCE

Routine Lexington release path, measured separately from the one-time
integration audit:

| Stage | Seconds |
|---|---|
| Live parent read | 4.2 |
| Package inputs | 0.04 |
| Package seal | 0.02 |
| First-party evidence gate | 0.03 |
| Fast release lane (rules A–O, two cold builds) | 20.1 |
| Candidate index compose + diff | 0.06 |
| Regression V2 classification | 2.5 |
| Cache lookup | 0.5 |
| **Total through candidate staging** | **27.4 s** |

Target ≤ 60 minutes; preferred ≤ 15 minutes. Actual: under half a minute.
The one-time integration audit was 4,588.5 s and is not part of this figure.

Full-bundle assembly of the twelve-market candidate is a separate ~35-minute
step that a launch order runs, not the data-only release path.

---

## PRODUCTION ENABLEMENT PLAN

`lexington_ky_production_enablement_plan_003.json`, status
**PROPOSED_NOT_APPLIED**, scope LEXINGTON_ONLY. Five fields across two files:

| File | Field | Current | Proposed |
|---|---|---|---|
| `fast_release_activation.json` | `FAST_PATH_PRODUCTION_ACTIVATION` | DISABLED | ENABLED |
| `fast_release_activation.json` | `pilot_allowlist` | `[]` | `["lexington-ky"]` |
| `fast_release_activation.json` | `PRODUCTION_RELEASE_CONSUMPTION` | DISABLED | ENABLED_FOR_PILOT_ALLOWLIST (optional) |
| `release_production_gate.json` | `RELEASE_COORDINATOR_PRODUCTION_ENABLED` | NO | YES |
| `release_production_gate.json` | `RELEASE_COORDINATOR_PRODUCTION_ALLOWED_MARKETS` | `[]` | `["lexington-ky"]` |

Not applied. Applying it would make Lexington deployable by the release
coordinator before a founder authorization exists, which is the ordering these
flags were built to prevent. No flag is set to a value that admits every market:
both allowlists are empty today, so the coordinator refuses all thirteen
registered markets including the eleven that are live, and the proposal adds
exactly one market id to each.

---

## ROLLBACK

| | |
|---|---|
| Target deployment id | `6a9e047690ec8bdaf99bcad2` |
| Target release digest | `895248738c79bc27f26da5bba1d2a490361ce6bd4959698adf3fb6f892aad8b0` |
| Markets / profiles / routes | 11 / 803 / 966 |
| Is the current verified parent | YES |

**Stale-rollback guard.** The rollback target is the CURRENT live deployment
read from the committed record, NOT the live deploy's own `rollback_target`
(`6a9d33f5dc8c3d1cf9464376`), which is the Cincinnati deploy Toledo replaced.
Rolling back to that would un-deploy Toledo.

---

## FOUNDER AUTHORIZATION PACKET

`launch_packages/pettripfinder/markets/reports/lexington_deployment_authorization_004_PROPOSED.json`

Status **AWAITING_FOUNDER_AUTHORIZATION**. `authorized_by` and `authorized_at`
are null. It is deliberately NOT in `deploy/netlify/deployment_authorizations/`,
because a file in that directory IS an authorization and only a founder creates
one. All seventeen DEPLOYMENT_READY gates derive true.

Bound digests:

| | |
|---|---|
| Parent release | `895248738c79bc27f26da5bba1d2a490361ce6bd4959698adf3fb6f892aad8b0` |
| Final candidate | `67fe8617b79febb9b2248895441c31ac65931cf9fdcfa4da4f8014ee190cde78` |
| Intended delta | `sha256:82e57491638b8fc471e691ba6ddbc376e11d371b1599740361af10c7fd6a76db` |
| Deployment artifact | `67fe8617b79febb9b2248895441c31ac65931cf9fdcfa4da4f8014ee190cde78` |
| Sealed package | `sha256:e5d26fd63bb2d2e2d3d632134cc40cd832d1a4d4c5e1b82f003aa58dc52c5380` |
| Fast-lane receipt | `sha256:d72b64ffd74bb60c5cdf40835e44781142dec55494cd6166bd773d31ab463404` |

What the founder would be authorizing: one field change in
`deploy/netlify/launch_participation.json` — the `lexington-ky` row's
`launch_status` from SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH to
FOUNDER_AUTHORIZED_FOR_LAUNCH, plus the founder's own decision block. Nothing
else in the repository changes to produce the candidate digest above.

---

## HARD STOP

No production activation was enabled. No founder authorization was created. No
host was called. No live participation record was mutated. No live verification
was performed. Nothing was pushed to production.
