# PTF-NASHVILLE-TN-PROMOTION-AND-NEW-LANE-LAUNCH-PREP-002 — FINAL

Nashville is registered, sealed, validated on the redesigned release lane, and
composed into an exact final candidate. **Nothing is deployed, nothing is
activated, and no authorization exists.** Production is untouched: twelve live
markets, 823 profiles, 991 routes on deploy `6aa172121d37bb4013eb44a4`.

Nashville registers **180 identities and publishes eight.** The shadow's 80
pet-friendly and 19 verified-no-pets reads did not survive the modern
first-party evidence gate, and the reason is one line long: the attended browser
lane recorded each page's byte **length** and not its **hash**. That finding is
the most important thing in this report and section
[Modern evidence gate](#modern-evidence-gate) is where it is proved.

---

## PRECHECK

| | |
|---|---|
| Worktree | `C:\Atlas-Nashville-Launch-V2` |
| Branch | `worker/ptf-nashville-new-lane-launch-002` |
| HEAD at start | `a87503297170b1248897bd87e5d651c79088cc80` |
| Tree | clean |
| Lineage | the Lexington launch tip. The ATLAS-THROUGHPUT 001–008 engineering was already merged here by PREP-003, so this order integrated nothing and re-audited no infrastructure |

**No factory tax.** Lexington paid 4,588 s for a one-time integration audit.
Nashville pays none: there was no merge to make and no throughput branch to
reconcile.

---

## CURRENT VERIFIED LIVE

Derived three ways, and all three agree.

| | |
|---|---|
| Deployment id | `6aa172121d37bb4013eb44a4` |
| Release digest | `67fe8617b79febb9b2248895441c31ac65931cf9fdcfa4da4f8014ee190cde78` |
| Sitemap digest | `dd0d87f2da07615776016690af64452d42cafc24d3c82e310b5f44efc6f7e611` |
| Source commit | `b446d1bcce910b745e21e7d3a7a44488d26a6944` |
| Markets | 12 |
| Profiles | 823 |
| Routes | 991 |
| Rollback parent of that deploy | `6a9e047690ec8bdaf99bcad2` (Toledo) |

Participating: cincinnati-oh, cleveland-akron-canton-oh, columbus-oh, dayton-oh,
grand-rapids-holland-mi, indianapolis-in, **lexington-ky**, louisville-ky,
milwaukee-wi, pittsburgh-pa, st-louis-mo, **toledo-oh**. Detroit remains
registered and withheld.

**Verified against production itself, not only against the record.** The live
sitemap was read over HTTPS at `https://pettripfinder.com/sitemap.xml` and
hashes to `dd0d87f2da07615776016690af64452d42cafc24d3c82e310b5f44efc6f7e611`
with 991 routes — byte-for-byte the committed record. A record and a live site
that disagree is the one condition every count below is stated against, so it
was measured rather than assumed.

---

## NASHVILLE SOURCE

`C:\Atlas-Nashville-Hardened-V1`, branch `worker/ptf-nashville-new-market-001`,
HEAD `4f3dd7b`, clean. One additive commit over `d335c50`, the Toledo-live
commit, which is an ancestor of this worktree's HEAD.

45 paths, of which 44 are new and one is shared:
`reports/factory_throughput_001_test_inventory.json`, generated state. Neither
side of it was taken — it was regenerated from the merged tree, the same rule
Lexington's merge followed. The 44 additive paths were cherry-picked **by path**;
the old branch was never merged.

---

## NASHVILLE QUALITY FREEZE

Read from `nashville_tn_shadow_market_001.json`, never typed, and reproduced
EXACTLY by the count gate before any row was allowed to move:

| | |
|---|---|
| Census | 181 |
| Clean pet-friendly | 80 |
| Clean verified-no-pets | 19 |
| Resolved | 99 |
| Unresolved | 82 |
| Corridors declared | 19 |
| Founder items | 25 in five groups, 0 blockers |
| Evidence records | 110 audited reads, 99 clean |

Cost of the shadow: 618 free HTTP requests, 17 Firecrawl credits, $0.00.

---

## REGISTRATION

Nashville arrived in far better shape than Lexington did, because the shadow was
already built on the modern contracts. Three things Lexington had to reshape did
not need touching here:

- every canonical name round-trips through `ptf_identity_key/1.0`, and the 181
  registered keys are **distinct** — no same-name collapse, no rename, no
  identity hold;
- `markets/proposed/nashville-tn.json` parses under `markets.contract`
  unchanged, so the contract was **moved**, not rebuilt;
- corridors are a real postal partition
  (`census_membership_basis = CORRIDOR_REGISTRY`), with Opryland and
  Vanderbilt/West End claiming their properties by `explicit_hotel_ids` at tier
  2 so display stays true without making membership ambiguous.

Four fields the registered census contract requires and the proposed file
predates were **derived**, never decided: `slug` from the canonical name,
`market_id`, and `identity_state` / `lodging_state` from the classification the
committed reconciliation already gave every row (`TRUE_HOTEL_IDENTITY`, with
`NON_LODGING` separated into its own class).

Written: `markets/nashville-tn.json`, `identity_census/nashville-tn.json`,
`nashville_tn_identity_holds_002.json`, `nashville_tn_final_partition_001.json`,
`hotel_policy_facts_nashville-tn.json`, the four authority shards,
`deploy/netlify/release_contracts/nashville-tn.json`, a participation row, two
`bundle_cache_closure.json` paths, and the three generated globals regenerated
from the shards. `check_generated_artifacts()` is empty.

---

## AUTHORITY MIGRATION

No semantic re-research, no new policy decision. Four things are worth naming
because each could be mistaken for new work.

**The join is through the census's own alias table.** Eight clean rows are keyed
by the short name the lane captured them under; the census carries that as an
alias of a fuller canonical name. All 99 clean rows resolve 1:1 onto 99 distinct
census identities, and no two clean reads land on one identity.

**One apparent cross-market collision dissolved on that join.** `comfort inn and
suites` is a key Lexington already publishes as VERIFIED_NO_PETS — but that is
the READ's short key; the census identity is `comfort inn and suites nashville
bellevue area`, which nobody owns. Joining on what the tool joins on is the
difference between a hold and a phantom.

**Facts are published in full, not reduced to acceptance.** Nashville's reads
carry per-field quotes with `field_refs`, so `pet_fee`, `species`,
`weight_limit` and `pet_count_limit` are published with the operator quote that
supports each, and `withheld_facts` carries the shadow's deliberate omissions
forward so a blank can never read as a zero.

**The registered census keeps the observations that admitted each row.**
Dropping them was a defect of this order's own first pass, and the shadow's own
suite is what caught it: a registered identity whose admitting evidence lives
only in a report cannot be audited from the census. Toledo's registered census
carries the field for the same reason.

---

## IDENTITY / CROSS-MARKET AUDIT

| Check | Result |
|---|---|
| Names that do not round-trip to their key | 0 |
| Intra-Nashville key collisions | 0 |
| Two clean reads on one census identity | 0 |
| Clean rows landing on a key another market publishes | 0 |
| Census rows landing on a key another market publishes | **2** |

**CROSS_MARKET_COLLISION (2)** — `hampton` (1919 West End Avenue) and `hampton
inn and suites` (2324 Crestmoor Road). Detroit already publishes both bare keys.
Neither row is in the clean cohort, so neither publishes anything, and both were
already unresolved. They are held anyway, at the cause, so a later order cannot
publish them into an assembler failure. Detroit's rows are not moved: that
market is registered.

---

## MODERN EVIDENCE GATE

This is the finding.

| | Shadow clean | Modern valid | Held |
|---|---|---|---|
| Pet-friendly | 80 | **8** | 72 |
| Verified no-pets | 19 | **5** | 14 |
| Total | 99 | 13 | 86 |

Plus two cross-market holds on unresolved rows: **88 held in total**, each named
with its reason in `nashville_tn_identity_holds_002.json`.

| Hold class | Gate | Rows | Reversible without re-capture |
|---|---|---|---|
| MODERN_EVIDENCE_GATE_HOLD | NO_CAPTURE_HASH | 84 | NO |
| MODERN_EVIDENCE_GATE_HOLD | NO_TIMESTAMP | 1 | NO |
| CROSS_MARKET_COLLISION | key already owned | 2 | YES |
| CONTRACT_MIGRATION_ERROR | no city stated | 1 | YES |

**NO_CAPTURE_HASH (84).** The shadow's attended lane read 154 property pages in
two same-origin navigations for $0 — an excellent lane — and recorded
`document_bytes` for each page and no `document_sha256`. The acquisition
directories it named are gitignored and empty on disk. `first_party_binding`
refuses a published fact whose captured document cannot be identified, and
nothing committed can supply one. For the pet-friendly half the refusal is not
asserted, it is demonstrated: each record is built and handed to the gate, and
the gate's verdict is written onto the hold.

**This order does not do what `toledo_oh_promotion_application_002` does.** That
applier falls back to `sha256(source_url + quote)` when the lane recorded no
document hash. That value can be computed without ever fetching the page, so it
proves nothing and satisfies the capture-hash check by manufacturing exactly the
evidence the check exists to demand. It is not a hypothetical: **all 39 of
Toledo's live attended evidence entries carry that manufactured hash**, verified
by recomputing it against the committed live authority. Toledo is not touched
here — changing another market is outside this order — but the defect is real,
it is in production, and it is why Nashville declined the same shortcut.

**NO_TIMESTAMP (1).** A free-static read with no `captured_at`. The evidence
contract makes it mandatory and the freshness rule has nothing to measure
without it.

**CONTRACT_MIGRATION_ERROR (1).** WoodSpring Suites Hermitage — Nashville
Airport. The registered census requires a city and no committed source states
one that survives its own contradiction: no other admitted row shares ZIP 37076,
and WoodSpring files the property under a `/locations/tennessee/chattanooga/`
URL segment, 130 miles away and flatly contradicted by the 37076 the same page
states. The sibling at 515 Metroplex Drive takes "Nashville" from its own
canonical URL, which names a municipality this market admits — the shadow's own
committed backfill rule, applied mechanically. A brand's marketing name is never
read as a city in a market where almost every hotel in Antioch, Hermitage,
Bellevue, Donelson and Old Hickory is called "Nashville" by its operator.

**No gate was lowered and no count was preserved.** The evidence gate runs again
over the survivors and the applier raises if it still refuses a row. It does not.

---

## PAID PROVENANCE

All thirteen surviving rows came through Firecrawl, so rule O has a real
question to answer here and it is not a formality.

**Nashville's committed run carries the request envelope. Lexington's did not.**
`nashville_tn_firecrawl_pass_001.json` records, for all seventeen attempted
rows, the `request_envelope` the adapter sent — the endpoint and the exact body
— plus the page hash, the outcome, the identity assessment, the capture
timestamp and the credit delta that was the meter. Every field the ledger
contract wants is in committed bytes, so the reservation is **derived**, not
invented. That is precisely the carve-out this order's Phase 8 allows, and it is
why Lexington was right to hold six rows and this order is right not to.

Run `nashville_tn_firecrawl_001` was ingested into
`ptf_paid_attempt_ledger_001.json`: **806 → 823 attempts**, 17 rows, 15
publication-grade, 17 of 17 envelope hashes derived. Ledger rows are written
under the REGISTERED identity key, because that is the key rule O re-derives the
attempt id from; the captured key is preserved alongside.

**A real hole closed on the way.** An exclusion record carried no capture lane,
so the package writer labelled its evidence reference `"recorded"` and a
verified-no-pets row bought through a paid lane escaped rule O **entirely** —
five rows sailed through a rule that should have stopped them. The lane is now
declared on the record. That is how it was found: not by reading the rule, but by
watching rule O check eight rows when thirteen were paid for.

`PAID_PROVENANCE_HOLDS = 0`.

---

## RECONCILIATION

Every one of the shadow's 181 identities is accounted for exactly once.

| | Shadow | Registered |
|---|---|---|
| Census | 181 | 180 + 1 held = 181 |
| Clean pet-friendly | 80 | 8 valid + 72 held |
| Clean verified-no-pets | 19 | 5 valid + 14 held |
| Unresolved (no clean read) | 82 | 82 |
| Resolved | 99 | 13 |

Partition, 180 rows: PUBLISHED_PET_FRIENDLY 8, VERIFIED_NO_PETS 5,
AWAITING_POLICY_ARTIFACT 87, AWAITING_POLICY_OBSERVATION 40,
AWAITING_ROUTING_REVIEW 37, AWAITING_FOUNDER_DECISION 3. No silent omission.

---

## SEALED PACKAGE

| | |
|---|---|
| Package id | `pkg-nashville-tn-5b1bfbc861413944` |
| Package digest | `sha256:5b1bfbc861413944af90303ed1a2806fd519f8ae8fcc8cdd368f497246b5dc22` |
| Build input key | `sha256:1799d9cfafcc6936e234443aca91e026c31b64dd1b35781ae1b1c4062076da7f` |
| Pet-friendly records | 8 |
| Verified-no-pets records | 5 |
| Census count | 180 |
| Evidence references | 13, all paid, all with a reservation |
| Unresolved | 167 |

`FRESH_PACKAGE_REPRODUCIBLE = YES` — re-sealed in an independent worktree from a
fresh checkout of the committed tree and identical.

**It was not reproducible at first, and the reason is worth keeping.** The
`seed` dependency digest disagreed between the working tree and a fresh
checkout. A local `csv.DictWriter` emits CRLF, which made nashville-tn the only
seed shard in the repository with CRLF; git normalised it on commit, so the
bytes on disk and the bytes committed were different files. The fix is not a
newline argument, it is ownership: `market_authority.render_seed_csv` already
owns the committed CSV style — LF, minimal quoting, the frozen column order — so
the shard is rendered by it.

---

## REGRESSION V2

Two different questions, and conflating them is how a shared change escapes its
regression.

**Registering Nashville is NOT data-only.** `FULL_REGRESSION_REQUIRED = YES`, on
79 changed files. The dependencies that widen it:

| Path | Class |
|---|---|
| `deploy/netlify/launch_participation.json` | DEPLOYMENT_CHANGE |
| `deploy/netlify/release_contracts/nashville-tn.json` | DEPLOYMENT_CHANGE |
| `launch_packages/pettripfinder/bundle_cache_closure.json` | DEPLOYMENT_CHANGE, and a narrowing blocker |
| `launch_packages/pettripfinder/hotel_exclusions.json` | AUTHORITY_CHANGE |
| `launch_packages/pettripfinder/hotel_policy_facts_nashville-tn.json` | AUTHORITY_CHANGE |
| `launch_packages/pettripfinder/identity_census/nashville-tn.json` | AUTHORITY_CHANGE |
| `tests/pettripfinder/pins/market_state.json` | narrowing blocker |
| five `*_identity_holds_*` / `*_proposed/*` / ledger paths | UNCLASSIFIED |

**A routine Nashville release is data-only.** The fast lane's own receipt
records `CHANGE_CLASS = MARKET_AUTHORITY_DATA_ONLY`,
`FAST_DATA_ONLY_RELEASE_ELIGIBLE = YES`,
`FULL_REGRESSION_REQUIRED_BY_LANE = NO`, remote broad jobs 0.

### The one-time registration audit

Exactly one broad run. **The assembler's partition table cost it a restart, and
that is a finding, not an accident.** The first run was 25 minutes in when a
composed thirteen-market assembly refused:

```
AssemblyError: global assembly gates failed:
  ['global.launch_participation_agrees_with_source']
```

`_partition_path` resolves a market's partition through an explicit table first
and a glob second. Nashville had no entry, so the glob ran: `nashville-tn`
strips to `nashville`, it looked for `nashville_final_partition_*.json`, and the
committed file is `nashville_tn_final_partition_001.json`. Nothing matched,
`final_partition_present` read False, and a market with a valid partition and
eight published profiles came out NOT ASSEMBLABLE. Detroit, Grand Rapids,
Indianapolis, Toledo and Lexington each fell into the same trap. The run was
stopped and restarted against the corrected tree rather than spending a second
broad run to cover an assembler change made after the first.

| | |
|---|---|
| Collected | 18,095 |
| Passed | 17,651 |
| Skipped | 253 |
| Failures | 191 |
| Baseline (`f75aa95`) | 160 |
| PRE_EXISTING | 160 |
| TRUE_NEW reported by the classifier | 31 |
| Wall clock | 4,974.4 s (1 h 23 m) |
| Broad runs executed | 1 |
| Remote broad jobs | 0 |

**The classifier reported 31 TRUE_NEW. Only 15 are this order's.** Running those
exact node ids at the PARENT commit `a875032` splits them three ways:

| | Count | What it is |
|---|---|---|
| PRE_EXISTING_AT_PARENT | **16** | fails at `a875032` too, before this order touched anything |
| CAUSED_BY_THIS_ORDER | 7 | passes at the parent, fails here |
| IMPORTED SUITE | 8 | the shadow's own gates, falsified by promotion |

The 16 are absent from the committed baseline only because `f75aa95.json`
predates the Lexington launch and was never re-pinned. Seven belong to
`test_toledo_oh_launch_003`, two to the Indianapolis cross-market scan, and two
to `research_workers` seed parsing that trips on a **Lexington** URL. They are
reported in full and **not** absorbed: folding sixteen real failures into a
PRE_EXISTING bucket is the exact thing a baseline exists to prevent. Re-pinning
the baseline at the Lexington-live commit is a separate order's work.

The 15 that are this order's were closed: **10 by re-running the node id**, and
**5 retired by name** in `RETIRED_BOUNDARY_GATES`, each with what it guarded and
what discharged it, plus a gate asserting that record is present. A retired gate
is never counted as a passing one — it cannot be re-run, because its premise is
false and it no longer exists.

`TRUE_NEW_FAILURE_AFTER_CLOSURE = 0`. No second broad run. Nothing was
deselected, relaxed or deleted to make a count.

**One of the imported gates found a real defect** rather than merely going
stale: `test_every_admitted_identity_has_hard_evidence_and_a_corridor` failed
because the applier dropped `evidence` from every registered census row.
Carrying it across made the gate pass without touching the gate.

---

## FAST RELEASE-SAFETY LANE

All fifteen rules PASS. Zero UNKNOWN, zero FAIL.

```
A schema  B identity  C first-party  D policy   E routes
F partition  G collisions  H preservation  I intended delta
J build  K determinism  L hashes  M freshness  N rollback  O paid provenance
```

`FAST_DATA_ONLY_RELEASE_ELIGIBLE = YES`.
Receipt digest `sha256:c6fd61ffcc2f86af702be33f954ced6a740684d9a8c46f5dbd552b52981e7ddc`.
`PRODUCTION_ACTIVATION_ALLOWED = NO` — the flags are still closed.

Rule O failed on the first pass, twice, and each failure was a real finding
recorded above: no reservation on any paid reference, then five paid refusals
invisible to the rule because the record declared no lane. Neither was silenced.

---

## CURRENT PARENT RECHECK

Re-read immediately before staging, and again against the live site: still
deploy `6aa172121d37bb4013eb44a4`, 823 profiles, 991 routes, twelve markets,
zero problems. Rule N re-checks the package's declared parent against it and
passes.

---

## FINAL CANDIDATE

Composed with Nashville **PARTICIPATING**, because a pre-flip candidate can
never carry the digest a launch produces — the lesson
PTF-TOLEDO-OH-DEPLOYMENT-AND-LAUNCH-AUTHORIZATION-003 paid for. Assembled in
throwaway worktrees from a participation document differing from the committed
one in exactly one field.

| | |
|---|---|
| Candidate digest | `5f7566370613b3e0de301340205757fd48a52eff179e73a9ae23d92c5015812e` |
| Sitemap digest | `6f976936c420c6b25db1bb2190bc29c9b89c57accd50ac5096208df39857a033` |
| Markets | 13 |
| Profiles | 831 |
| Routes | 1,001 |
| HTML pages | 5,075 |
| Files | 5,093 |
| All gates pass | yes (27 of 27) |
| Broken links | 0 |
| `deployment_authorized` | **false** |

Detroit, Chattanooga and Fort Wayne all stay out. Chattanooga and Fort Wayne are
not registered at all, so no participation decision could admit them.

---

## RELEASE DIFF

| | Parent | Candidate |
|---|---|---|
| Markets | 12 | 13 |
| Profiles | 823 | 831 |
| Routes | 991 | 1,001 |

Markets added: `nashville-tn`. Updated: none. Removed: none. Every other
market's profile count is identical to live, market by market.

Nashville contributes 8 profiles and 10 routes — hub, eight hotel profiles and
the policy-comparison page. **Two route numbers appear in the artifacts and
neither is wrong:** the release index counts 9 (hub plus profiles), the
assembled sitemap 10 (it renders the comparison page, which the index does not
model). Both are stated in the packet so a reader never has to reconcile them.

0 of 19 corridors reach their own publication minimum at eight profiles, which
is a threshold and not a gap.

**Unexpected profile changes 0. Unexpected route changes 0. Unexpected market
changes 0. Routes removed vs the LIVE sitemap: 0. Release-index findings: 0.**

---

## CACHE / REUSE

`UNCHANGED_MARKETS_REBUILT = 0` — a fact about what the lane DID, not a hit
rate. The redesigned lane never renders an unchanged market: rule J stages and
builds the changed market alone, and rules G/H/I compare release indexes derived
from committed authority. The other twelve markets were neither built, reused,
nor rebuilt.

For the changed market the persistent cache reports a MISS, reason "no entry for
this input key" — Nashville has never been built, so there is nothing to reuse
and the lane builds it cold. Measured build input key
`sha256:1799d9cfafcc6936e234443aca91e026c31b64dd1b35781ae1b1c4062076da7f`.

---

## REPRODUCIBILITY

`FINAL_CANDIDATE_REPRODUCIBLE = YES`. Three independent assemblies, two
worktrees, two commits. All 5,093 files byte-identical; bundle and sitemap
digests identical.

The third assembly ran at a **later** commit than the first two and produced a
byte-identical bundle. That is also the proof that the registered census and the
test closures are not site inputs. The only manifest field that moves is
`generated_from_commit`, which records the commit the assembly ran at and is not
part of the bundle.

Full identifiers, no abbreviations:

| | |
|---|---|
| Parent release digest | `67fe8617b79febb9b2248895441c31ac65931cf9fdcfa4da4f8014ee190cde78` |
| Sealed package digest | `sha256:5b1bfbc861413944af90303ed1a2806fd519f8ae8fcc8cdd368f497246b5dc22` |
| Build input key | `sha256:1799d9cfafcc6936e234443aca91e026c31b64dd1b35781ae1b1c4062076da7f` |
| Intended delta digest | `sha256:ca822fbf97aca632258b8ae5c3f8d1ee09fed18bb6c90c6772737291e2af9493` |
| Final candidate digest | `5f7566370613b3e0de301340205757fd48a52eff179e73a9ae23d92c5015812e` |
| Deployment artifact digest | `5f7566370613b3e0de301340205757fd48a52eff179e73a9ae23d92c5015812e` |
| Candidate sitemap digest | `6f976936c420c6b25db1bb2190bc29c9b89c57accd50ac5096208df39857a033` |
| Fast-lane receipt digest | `sha256:c6fd61ffcc2f86af702be33f954ced6a740684d9a8c46f5dbd552b52981e7ddc` |

---

## PERFORMANCE

Routine Nashville release path, measured separately from the one-time
registration audit:

| Stage | Seconds |
|---|---|
| Live parent read | 5.2 |
| Package inputs | 0.07 |
| Package seal | 0.10 |
| First-party evidence gate | 0.01 |
| Fast release lane (rules A–O, two cold builds) | 15.65 |
| Candidate index compose + diff | 0.07 |
| Regression V2 classification | 2.38 |
| Cache lookup | 0.68 |
| **Total through candidate staging** | **24.18 s** |

Target ≤ 60 minutes; preferred ≤ 15 minutes. Actual: under half a minute, and
comparable to Lexington's 27.4 s.

Kept separate, because conflating them is how a one-time cost gets billed to a
routine one:

| | Seconds |
|---|---|
| One-time registration audit (one broad run) | 4,974.4 |
| Closure run (10 node ids) | 539.6 |
| Parent baseline-proof run (23 node ids at `a875032`) | 602.1 |
| Full 13-market bundle assembly, ×3 | ~1,800 each |

The full assembly is a LAUNCH order's step, not the data-only release path. This
order ran it three times only to bind and re-prove a digest.

Total wall time from order start to authorization-ready: **≈ 5 h 20 m**, of
which ≈ 1 h 23 m is the one broad run, ≈ 1 h 30 m the three assemblies, and ≈ 30
m the baseline-proof and closure runs.

---

## PRODUCTION ENABLEMENT PLAN

`nashville_tn_production_enablement_plan_002.json`, status
**PROPOSED_NOT_APPLIED**, scope NASHVILLE_ONLY. Five fields across two files:

| File | Field | Current | Proposed |
|---|---|---|---|
| `fast_release_activation.json` | `FAST_PATH_PRODUCTION_ACTIVATION` | DISABLED | ENABLED |
| `fast_release_activation.json` | `pilot_allowlist` | `[]` | `["nashville-tn"]` |
| `fast_release_activation.json` | `PRODUCTION_RELEASE_CONSUMPTION` | DISABLED | ENABLED_FOR_PILOT_ALLOWLIST (optional) |
| `release_production_gate.json` | `RELEASE_COORDINATOR_PRODUCTION_ENABLED` | NO | YES |
| `release_production_gate.json` | `RELEASE_COORDINATOR_PRODUCTION_ALLOWED_MARKETS` | `[]` | `["nashville-tn"]` |

Not applied. Applying it would make Nashville deployable by the release
coordinator before a founder authorization exists, which is the ordering these
flags were built to prevent. No flag is set to a value that admits every market:
both allowlists are empty today — Lexington launched without them ever being
opened — so the coordinator refuses all fourteen registered markets including the
twelve that are live, and the proposal adds exactly one market id to each.

---

## ROLLBACK

| | |
|---|---|
| Target deployment id | `6aa172121d37bb4013eb44a4` |
| Target release digest | `67fe8617b79febb9b2248895441c31ac65931cf9fdcfa4da4f8014ee190cde78` |
| Target sitemap digest | `dd0d87f2da07615776016690af64452d42cafc24d3c82e310b5f44efc6f7e611` |
| Markets / profiles / routes | 12 / 823 / 991 |
| Is the current verified parent | **YES** |

**Stale-rollback guard.** The target is the CURRENT live deployment read from
the committed record, NOT the live deploy's own `rollback_target`
(`6a9e047690ec8bdaf99bcad2`), which is the Toledo deploy Lexington replaced.
Rolling back to that would un-deploy Lexington.

---

## FOUNDER AUTHORIZATION PACKET

`launch_packages/pettripfinder/markets/reports/nashville_deployment_authorization_003_PROPOSED.json`

Status **AWAITING_FOUNDER_AUTHORIZATION**. `authorized_by` and `authorized_at`
are null. It is deliberately NOT in `deploy/netlify/deployment_authorizations/`,
because a file in that directory IS an authorization and only a founder creates
one. All eighteen DEPLOYMENT_READY gates derive true.

The packet states up front that it is **not byte-stable** in three
self-observing fields — the source commit, git HEAD, and the uncommitted-path
list — and that every digest and count it BINDS is stable. That property cost
PTF-LEXINGTON-KY-FRESH-PACKAGE-REAUTHORIZATION-PREP-005 a re-issue to discover.

What the founder would be authorizing: one field change in
`deploy/netlify/launch_participation.json` — the `nashville-tn` row's
`launch_status` from SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH to
FOUNDER_AUTHORIZED_FOR_LAUNCH, plus the founder's own decision block. Nothing
else in the repository changes to produce the candidate digest above.

---

## WHAT A LATER ORDER SHOULD DO, IN ORDER OF VALUE

1. **Re-read the 84 attended pages, hashing each document in the same call that
   takes the quote.** Free, attended, roughly two navigations. It would take
   Nashville from 8 published to about 78, and from 5 verified-no-pets to 19.
   This order is forbidden to re-capture, which is the only reason it did not.
2. **Fix the Toledo applier's manufactured hash and re-capture Toledo's 39
   attended entries.** They are live now.
3. **Re-pin the regression baseline at the Lexington-live commit.** Sixteen real
   failures are currently invisible to the classifier.
4. **Teach the change classifier a rule for `*_identity_holds_*.json`.** Toledo,
   Lexington and Nashville all carry the same UNCLASSIFIED gap.

---

## HARD STOP

No production activation was enabled. No founder authorization was created. No
host was called. No live participation record was mutated. No live verification
of a Nashville route was performed. Nothing was deployed. Chattanooga was not
started.
