# PTF-FORT-LAUDERDALE-FL-REGISTRATION-AND-STAGING-002 — FINAL

**Worktree** `C:\Atlas-Fort-Lauderdale-FL-Hardened-V1`
**Branch** `worker/ptf-fort-lauderdale-fl-market-001`
**Market** `fort-lauderdale-fl`
**Source commit named by the order** `4045d973` — a transposition of the actual source-ready
commit `4a45d973`, which is the commit this order registered from and the commit the sealed
package records as `created_from_source_sha`. No other commit on this branch is close to that
prefix, so the identification is unambiguous.
**Registration commit** `9b4bf0f687f1c6eee810edd41a209c8f78d7cdc5`

**This order stopped where it was told to stop: AUTHORIZATION_READY + a VALIDATED PROJECTED
CANDIDATE.** Fort Lauderdale is registered and buildable. It is not authorized, not deployed,
and not live. No founder authorization and no deployment authorization exist for it.

---

## PHASE 1 — VERIFY CURRENT LIVE

Resolved mechanically with the repaired resolver
(`python -m scripts.pettripfinder.release_index live-source --fetch --verify-host`), not from
`origin/main`. The resolver itself reports `origin_main_stale = True` and
`origin_main_contains_live = False`, which is exactly why the order forbids it.

| | |
|---|---|
| CURRENT LIVE SOURCE COMMIT | `fbaf6f73a8e4ed7fa5cf3d81588219d513743bcd` |
| built_from_commit | `95d23162ea2ae6528045fb56648e15358ae0c6f7` |
| CURRENT LIVE DEPLOYMENT | `6ab071a5b7561c33aff6c17b` (`ptf-deploy-miami-006-…`) |
| CURRENT LIVE BUNDLE SHA | `b2ad54b9be8b8a0121b8b664ef95e6d4dcf3feb873b4b23558c3721cdc06732a` |
| CURRENT LIVE SITEMAP | `5ac34c75d6ba22d87b5da9d9ff40844dc2e986d7b778760849c03769bb088980` |
| CURRENT LIVE MARKETS | 31 |
| CURRENT LIVE PROFILES | 2290 |
| CURRENT LIVE ROUTES | 2614 served sitemap routes |
| HOST VERIFIED | **true** |

The order's expectation (31 / 2290 / 2614 after Miami) and the authoritative resolution agree.

This resolution was taken again at report time, after every write this order made, and is
byte-for-byte the same. Nothing this order did moved the live pointer.

**A note on two route numbers, because they are not interchangeable.** 2614 is the *served
sitemap* route count. The release index that the staging lane compares against counts 2550
participating routes for the same 31 markets. The difference of 64 is the non-market surface
the sitemap serves and the release index does not enumerate per market. Every projection below
is stated against the release-index basis, because that is the basis the gates compare on.

---

## PHASE 2 — VERIFY FORT LAUDERDALE SOURCE PACKAGE

HEAD contains `4a45d973`. The source-ready order's own final report
(`PTF-FORT-LAUDERDALE-FL-HARDENED-SOURCE-READY-001_FINAL.md`) closed at SOURCE READY = YES,
COVERAGE READY = YES, ACTIONABLE UNRESOLVED = 0, FAST 15/15, PACKAGE REPRODUCIBLE = YES.

Nothing was rebuilt. The census, the discovery lanes, the Firecrawl pass, the attended-browser
acquisition, the Marriott closure and the competitor challenge were all read from committed
bytes, never re-run. The only reason any acquisition-lane *module* appears in this order's
change set is the two source-level repairs described in Phase 6 — neither of which re-ran a
provider.

Sealed package resolved mechanically:

| | |
|---|---|
| Package | `pkg-fort-lauderdale-fl-398ca08f89a75b8a` |
| Package digest | `sha256:398ca08f89a75b8aab47af83a8a56ad4300075b37fa7f10c9ec31df4fdda0518` |
| created_from_source_sha | `4a45d973…` |
| Census | 461 registered identities |
| Published pet-friendly profiles | 85 |
| Verified no-pets | 53 |
| Unresolved | 323 |
| Declared routes | 96 |
| FAST receipt | `pkg-fort-lauderdale-fl-398ca08f89a75b8a-c90d906337683ff0.json` |
| FAST receipt digest | `sha256:c90d906337683ff09711bcf0d0028df5b042f00cfc497f3666364993f52deee3` |

The package the source-ready order sealed was `pkg-fort-lauderdale-fl-69b617cd4c8b6ba9`. This
order's package is a different id because registration **moves the package's own inputs** —
the census moves from `identity_census_proposed/` to `identity_census/`, the authority document
and the policy package move to the package root, and the market shard and release contract are
written for the first time. The package is derived from those paths, so its digest necessarily
changes. What must not change is the *content* it certifies, and the registration proof checks
exactly that: the registration input's counts reconcile, every identity is in the census, and
the written shard binds to it (`registration_input` PASS).

---

## PHASE 3 — PROMOTE / REGISTER

The canonical fresh-market registration transaction was performed in full.

**Five shared registration writes were blocked by auto mode's [Modify Shared Resources]
protection.** Per this order's own instruction — *"If tool permissions block those canonical
registration writes, request approval rather than routing around the protection"* — the five
were enumerated and put to the operator as a single approval, and were approved:

1. `build_global_authority --write` (deterministic global-authority regeneration)
2. the release contract `deploy/netlify/release_contracts/fort-lauderdale-fl.json`
3. `registration_release_lane register`
4. `registration_release_lane seal`
5. `registration_release_lane packet`

The approval was recorded as explicitly **not** extending to deployment authorizations,
deployment records, the live manifest, activation flags or Netlify. None of those was touched.

Writes made, all committed in `9b4bf0f6` (38 paths):

- Census promoted to `launch_packages/pettripfinder/identity_census/fort-lauderdale-fl.json`
- Registration input at the package root as `fort_lauderdale_fl_proposed_authority_001.json`
  — the **role name** the classifier recognises. (Orlando lost all fifteen checks to naming
  this file anything else; the name is part of the contract, not a convention.)
- Registered policy package `hotel_policy_facts_fort-lauderdale-fl.json`
- Market shard `markets/fort-lauderdale-fl.json`
- Authority shard `markets/authority/fort-lauderdale-fl/{affiliate_destinations, hotel_exclusions, identity_routing, seed_businesses.csv}`
- Final partition `fort_lauderdale_fl_final_partition_001.json` at the package root
- Deterministic global regeneration: `hotel_exclusions.json`,
  `ptf_global_authority_manifest.json`, `seed_businesses.csv`
- Release contract `deploy/netlify/release_contracts/fort-lauderdale-fl.json`
- `bundle_cache_closure.json` (two declared inputs + one note)
- `tests/pettripfinder/pins/market_state.json` (one block)
- `launch_participation.json` **reissued**, one row added
- Sealed package, FAST receipt, lane reports

Not written, and deliberately so: **`identity_resolutions.json`**. The source-ready order left
four dual-brand halves (315 NW 1st Ave and 200 N Ocean Blvd) on an IDENTITY_MISMATCH_HOLD
rather than invent a same-campus ruling. That is still the right state — the order's own rule
is that founder intervention is for what *cannot* safely be represented as a hold, and this
can. The classifier agrees: `identity_resolutions` PASS, *"no identity-resolution ruling in the
change set."* Those four rows stay unpublished until a ruling is authored on evidence.

---

## PHASE 4 — REGISTRATION TIMER

Reported honestly and separately, as the order requires. Nothing is hidden.

**A. TOTAL PROMOTION / REGISTRATION WALL CLOCK = 1 h 37 m 57 s** (13:34:14Z → 15:12:11Z)

That total decomposes as:

| Segment | Duration | What it was |
|---|---|---|
| 13:34:14Z → 14:54:13Z | 79 m 59 s | Fresh-market promotion work (repointing every market-local writer from the shadow zone to the registered zone, authoring the release contract) **interleaved with** the human permission wait on the five blocked shared writes. The request and its approval both fall inside this span, so the wait and the work overlap and cannot be cleanly separated — neither is claimed alone, and the whole 80 minutes is reported as one honest block rather than split by guess. |
| 14:54:13Z → 15:07:07Z | 12 m 54 s | Applying the approved writes, making the two source repairs of Phase 6, and reaching a clean pre-lane tree |
| 15:07:07Z → 15:12:11Z | 5 m 04 s | The registration commit plus the **generic registration lane** (the lane itself is 3 m 45 s of this) |

**B. GENERIC REPAIRED REGISTRATION-LANE TIME = 3 m 45 s**

| Step | Seconds |
|---|---|
| `registration_release_lane register` | ~3 |
| `registration_release_lane seal` | 155.2 (FAST 125.7 + live-parent read 27.8) |
| `registration_release_lane packet` | ~67 wall, of which 62.706 is the classifier's own measured time |

- REGISTRATION ≤ 5 m TARGET = **MET** (3 m 45 s)
- REGISTRATION ≤ 10 m HARD BOUND = **MET**

The honest reading: the *generic lane* is fast and got faster than its target. The *wall clock*
is dominated by two things that are not the lane — a human approval decision, and the one-time
work of promoting a market that has never been registered before. Both are real, both are
reported, and neither is a lane defect. The lane cannot be credited with the 1 h 38 m and must
not be blamed for it either.

One process note worth keeping: `packet` **refused on a dirty worktree** — *"the classifier
proves committed bytes."* That is correct behaviour and not a nuisance. The registration
transaction was committed first (`9b4bf0f6`), then `packet` ran against committed bytes. A
classifier that proved a working tree would prove nothing.

---

## PHASE 5 — AUTOMATIC CLASSIFICATION

The repaired classifier ran automatically inside `packet`. Report:
`launch_packages/pettripfinder/markets/reports/fort_lauderdale_fl_registration_classification.json`

| | |
|---|---|
| Proof version | `ptf-registration-data-only/2.0` |
| CHANGE CLASS | **`COMPOSITE_FRESH_MARKET_DATA_ONLY`** |
| ELIGIBLE | **YES** |
| Checks | **15 PASS / 0 FAIL / 0 UNKNOWN** |
| FULL_REGRESSION_REQUIRED | **NO** |
| REMOTE BROAD JOBS REQUIRED | **0** |
| BROAD REGRESSION RUNS | **0** |
| UNCHANGED MARKETS REBUILT | **0** |
| FAST | **15/15 PASS**, determinism `BYTE_IDENTICAL` |
| Classifier time | 62.706 s |
| Reaches | `AUTHORIZATION_READY` · `authorizes_deployment = False` |

The fifteen checks and what each one actually proved:

| Check | Result | What it proved |
|---|---|---|
| `change_set` | PASS | all 104 changed paths land in exactly one narrow bucket |
| `market_local_zone` | PASS | all 30 market-local paths passed all five isolation conditions |
| `discovery_config` | PASS | — |
| `registration_input` | PASS | correct role name, counts reconcile, every identity in census, shard binds |
| `identity_resolutions` | PASS | no ruling in the change set |
| `participation` | PASS | one row added by a non-founder writer; authorized set carried forward exactly |
| `release_contract` | PASS | every number derived, none typed |
| `build_closure` | PASS | exactly two declared inputs + one note; every build control unchanged |
| `derived_globals` | PASS | committed globals byte-identical to a regeneration from the shards |
| `sealed_package` | PASS | sealed from exactly the head bytes, for REGISTERED_LIVE |
| `fast_receipt` | PASS | 15/15, bound to package, parent, intended delta and lane version |
| `expected_release` | PASS | expected and actual agree as complete sets, 0 unexpected changes |
| `identity_routes` | PASS | `release_index.compare` clean on both expected and actual |
| `market_state_pin` | PASS | one block, eight counts equal to what the package derives |
| `release_integrity` | PASS | no authorization, record, manifest, flag, gate or pin moved |

`FULL_REGRESSION_REQUIRED` came back NO, so no broad suite was launched. Had it come back YES
this order would have stopped, as instructed.

---

## PHASE 6 — REGISTRATION SAFETY

### The path accounting

Five-bucket partition over the change set, from the proof itself:

| Bucket | Paths |
|---|---|
| MARKET_LOCAL_ACQUISITION | 30 |
| NEW_MARKET_REGISTRATION_DATA | 13 |
| PERMITTED_DERIVED_REGISTRATION_OUTPUT | 61 |
| **SHARED_BEHAVIOR_CHANGE** | **0** |
| **UNKNOWN** | **0** |
| TOTAL | 104 (`sum_equals_total: true`) |

- SHARED FACTORY IMPLEMENTATION CHANGES = **0**
- UNKNOWN CHANGE PATHS = **0**

Two paths are recorded as narrowing blockers — `bundle_cache_closure.json` and
`tests/pettripfinder/pins/market_state.json`. These are the two shared documents every
registration owes. They are not shared *behaviour*: the closure gained exactly this market's
two declared inputs and one note, and the pin gained exactly one block. Both were verified
byte-identical elsewhere. A registration that skipped them would publish every bundle UNTRUSTED
and cost a second broad run.

### The two source repairs this order made, and why they are not shared-behaviour changes

**1. The registered contract wants the final partition at the package root.**
The release contract refused to build: *"market `fort-lauderdale-fl` commits no
`launch_packages/pettripfinder/fort_lauderdale_fl_final_partition_*.json`."* The shadow order
had written it into the market's staging zone, which is correct for a shadow market and wrong
for a registered one. Fixed by repointing `OUT` in this market's own `final_partition_001.py`.
Market-local, one line, no behaviour shared with any other market.

**2. A cross-market exclusion collision — caught before it could publish.**
`release_contracts.verify_all()` refused with a `PublicationBlockedError`. Fort Lauderdale's
exclusion key `fort-lauderdale-fl--holiday-inn-express-and-suites` was barring **Cleveland's**
Holiday Inn Express & Suites at 30500 Clemens Rd, Westlake OH 44145, because the shared
exclusion registry matches on the normalized canonical name *across every market*.

The root cause was in this market, not Cleveland's: Florida DBPR licenses one Miramar property
as the bare chain flag "Holiday Inn Express & Suites", with no place word. A bare flag is not a
premises identity.

The fix was made **at the source and in this market only** — `name_bare_chain_flags()` in
`fort_lauderdale_fl_census_reconciliation_001.py`: when a node's chosen name is a bare chain
flag and that node's *own* observations agree on exactly one longer name that starts with the
flag and adds a place, take the longer name. Two different fuller names is a review, never a
coin flip. Four rows renamed; OSM and IHG's own property page agreed on "Holiday Inn Express &
Suites Miramar". Census 460 → 461. `verify_all()` then came back clean for all 33 markets.

The alternative — superseding Cleveland's exclusion — was available and was rejected. It would
have modified another market to paper over a defect in this one, which the order forbids and
which would have left the bad key in the registry to collide again with the next market that
licenses a bare flag.

### Current served production

| | |
|---|---|
| CURRENT LIVE DEPLOYMENT CHANGED | **NO** — still `6ab071a5b7561c33aff6c17b` |
| CURRENT SERVED SITEMAP CHANGED | **NO** — still `5ac34c75d6ba22d87b5da9d9ff40844dc2e986d7b778760849c03769bb088980` |
| FORT LAUDERDALE LIVE | **NO** |
| `protected_paths_touched` | `[]` |

---

## PHASE 7 — PROJECTED PARTICIPATION

The candidate's participation was composed **in memory** (`compose(..., participates=True)`)
for the staging comparison. Nothing about it was persisted as live participation.

What *was* persisted is the SOURCE_READY participation record the order explicitly authorizes:
`launch_participation.json` was **reissued** (never hand-edited — a hand-added row breaks the
decision chain and every market reads UNLISTED), rows 32 → 33, with Fort Lauderdale's row at
`SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH`, written by a non-founder writer.

**The founder-authorized set is byte-identical, still 31 markets.** The classifier verified
this independently: *"every other row, the authorized set and the chain are carried forward
exactly."*

Candidate state: **PROJECTED · NON-DEPLOYABLE**.

---

## PHASE 8 — PARENT RELEASE LOOKUP

The repaired deployed-content identity semantics were used: the parent is resolved by
**deployed bundle sha256**, not by a registration-sensitive release-manifest-only lookup. This
matters because the release-store key *moves* on registration — a manifest-only lookup would
have failed here for exactly that reason.

| | |
|---|---|
| PARENT LOOKUP | **PASS** |
| PARENT FOUND BY DEPLOYED BUNDLE | **PASS** — `6ab071a5b7561c33aff6c17b` via `b2ad54b9…` |
| Parent release digest | `sha256:1bbcb59d60b999065fe9be1f140cf544026a431c15d30c5049d7d23c25eaeac7` |
| PARENT ROUTES PRESERVED | **PASS** — `identity_routes` clean, every live member preserved |

---

## PHASE 9 — STAGE FORT LAUDERDALE

| | |
|---|---|
| UNCHANGED BUNDLES REUSED | **31** (= current live market count) |
| UNCHANGED MARKETS REBUILT | **0** |
| FORT LAUDERDALE BUNDLES BUILT | **1** |
| Fort Lauderdale bundle sha256 | `e823657e4e620abe552c3298976ad4a9d618e07bfac69d1819bf1bff2db0d37b` |

Matches the order's expectation exactly. 31 reused, 0 rebuilt, 1 built.

---

## PHASE 10 — CANDIDATE DELTA

`release_index.compare(live, candidate, intended_delta=...)`:

```
findings        []
finding_counts  {}
passed          true
```

| | |
|---|---|
| UNEXPECTED MARKET DELTA | `[]` |
| UNEXPECTED PROFILE DELTA | `[]` |
| UNEXPECTED ROUTE DELTA | `[]` |

`complete_sets_equal: true` — no cross-market identity collision, no duplicate route, no
ownership movement, every live member preserved, every change declared.

**On the two candidate digests.** The readiness packet records an
`expected_candidate_index_digest` of `sha256:e68857b4c564b2ed…` (live parent + sealed package,
projected) and an `actual_candidate_index_digest` of `sha256:74c368f237a64e9f…` (composed from
the committed authority). These are two separately-constructed documents carrying their own
provenance; the gate is **set equality**, not digest equality, and set equality is what passed
— 32 markets, 2375 profiles, 2646 routes on both sides, with 0 unexpected market, profile or
route changes and an empty findings list. The expected digest `e68857b4…` is the one that is
reproducible and was reproduced: composed twice by the lane and once independently, identical
every time.

---

## PHASE 11 — PROJECTED ACCOUNTING

Fort Lauderdale's own contribution:

| | |
|---|---|
| FORT LAUDERDALE PROJECTED PROFILES | **85** |
| FORT LAUDERDALE PROJECTED HUB ROUTES | **1** |
| FORT LAUDERDALE PROJECTED CORRIDOR ROUTES | **10** |
| FORT LAUDERDALE PROJECTED OTHER ROUTES | **0** |
| FORT LAUDERDALE TOTAL ROUTES | **96** |

Projected totals (release-index basis):

| | Live | + FTL | Projected |
|---|---|---|---|
| MARKETS | 31 | +1 | **32** |
| PROFILES | 2290 | +85 | **2375** |
| ROUTES | 2550 | +96 | **2646** |

Only the sealed approved pet-friendly cohort publishes — 85 profiles. The 53 verified-no-pets
rows and every held row stay in non-profile/exclusion state per the production contract. 10 of
18 corridors reach their own publication minimum; the other 8 are suppressed, which is a
threshold and not a gap. The market and its corridors carry
`show_in_navigation=false, show_in_sitemap=false` until a launch order says otherwise.

323 of 461 registered identities remain unresolved. The release contract says so in its own
text and does not pretend otherwise: a row publishes only on an operative first-party quote
from the property's own page, bound to its census identity. No gate was lowered to preserve a
count.

---

## PHASE 12 — STAGING GATES

**ALL GATES PASS.**

| Gate | Result |
|---|---|
| package identity | PASS — `sealed_package`, sealed from exactly the head bytes |
| registration classification | PASS — `COMPOSITE_FRESH_MARKET_DATA_ONLY`, ELIGIBLE YES, 15/15 |
| parent identity | PASS — found by deployed bundle, `release_integrity` verified |
| parent routes preserved | PASS — `identity_routes` clean |
| market preservation | PASS — 0 unexpected market changes |
| profile preservation | PASS — 0 unexpected profile changes |
| route preservation | PASS — 0 unexpected route changes |
| candidate delta | PASS — findings `[]`, `passed true` |
| participation projection | PASS — authorized set byte-identical at 31 |
| **deployment eligibility refusal** | **PASS (expected)** — `authorizes_deployment = false`, `founder_status = AWAITING_FOUNDER_AUTHORIZATION`, `authorized_by = null`, `authorized_at = null` |
| FAST | 15/15 PASS, `BYTE_IDENTICAL` |
| PACKAGE REPRODUCIBLE | YES |
| CANDIDATE REPRODUCIBLE | YES |

The readiness document is **prepared and UNSIGNED**. Its `authorized_by` and `authorized_at`
are null and were left null. Signing an approval in the operator's name is not something this
order authorizes and not something a worker may do.

---

## PHASE 13 — NO DEPLOYMENT

Not done, at all:

- ✗ founder authorization created
- ✗ deployment authorization created
- ✗ Netlify invoked
- ✗ live deployment record modified
- ✗ Fort Lauderdale marked LIVE
- ✗ any deployment authorization consumed

External re-verification against the live host, after every write:

| Probe | Result |
|---|---|
| `/pet-friendly-hotels/fort-lauderdale-fl/` | **404** |
| `/pet-friendly-hotels/fort-lauderdale-fl/dania-beach/` | **404** |
| `/pet-friendly-hotels/miami-fl/` | 200 |
| Served sitemap sha256 | `5ac34c75…` — matches the live record |
| Occurrences of `fort-lauderdale-fl` in the served sitemap | **0** |
| Live resolver re-read at report time | `fbaf6f73…` / `6ab071a5b7561c33aff6c17b` / 31 / 2290 / 2614, host verified |

CURRENT LIVE = **unchanged**. FORT LAUDERDALE SERVED LIVE = **NO**.

---

## PHASE 14 — REPORT / COMMIT / PUSH

Committed: the registration transaction `9b4bf0f6` (38 paths), then this report together with
the two documents `packet` wrote after that commit — the authorization readiness packet and the
registration classification proof. Both are generated registration outputs and both belong in
the branch.

---

## WHAT A FOUNDER IS ACTUALLY BEING ASKED TO DECIDE

Not whether the machinery worked — it did, and the proof is mechanical. The decision is whether
**85 published profiles over a 461-identity census** is the right size to launch Greater Fort
Lauderdale at. 323 identities are unresolved, mostly because the brands that own them wall
automated reads and the order forbids bypassing that wall. Four more are held on a dual-brand
identity question that deserves an evidence-based ruling rather than a guess. None of that is a
defect in this run; all of it is visible on purpose.

The second thing worth a founder's eye: the cross-market exclusion collision in Phase 6 was
caught by `verify_all()` *before* publication, not after. That guard earned its keep this run.

---

## FINAL ANSWERS

1. **CURRENT LIVE SOURCE COMMIT** = `fbaf6f73a8e4ed7fa5cf3d81588219d513743bcd`
2. **CURRENT LIVE DEPLOYMENT** = `6ab071a5b7561c33aff6c17b`
3. **CURRENT LIVE MARKETS** = 31
4. **CURRENT LIVE PROFILES** = 2290
5. **CURRENT LIVE ROUTES** = 2614 served sitemap routes (2550 on the release-index basis the gates compare on)
6. **FORT LAUDERDALE PACKAGE** = `pkg-fort-lauderdale-fl-398ca08f89a75b8a`
7. **PACKAGE DIGEST** = `sha256:398ca08f89a75b8aab47af83a8a56ad4300075b37fa7f10c9ec31df4fdda0518`
8. **REGISTRATION CLASS** = `COMPOSITE_FRESH_MARKET_DATA_ONLY`
9. **ELIGIBLE** = YES
10. **FULL_REGRESSION_REQUIRED** = NO
11. **TOTAL PROMOTION / REGISTRATION WALL CLOCK** = 1 h 37 m 57 s (13:34:14Z → 15:12:11Z) — an 80 m block in which one-time fresh-market promotion work and the human permission wait overlap and are not separable, then 12 m 54 s of post-approval promotion work, then 5 m 04 s of commit + lane
12. **GENERIC REGISTRATION-LANE TIME** = 3 m 45 s (register ~3 s + seal 155.2 s + packet ~67 s)
13. **REGISTRATION ≤ 5 M TARGET** = MET
14. **REGISTRATION ≤ 10 M HARD** = MET
15. **BROAD REGRESSION RUNS** = 0
16. **PARENT LOOKUP** = PASS (found by deployed bundle `b2ad54b9…`)
17. **PARENT ROUTES PRESERVED** = PASS
18. **UNCHANGED BUNDLES REUSED** = 31
19. **UNCHANGED MARKETS REBUILT** = 0
20. **FORT LAUDERDALE BUNDLES BUILT** = 1 (`e823657e4e620abe…`)
21. **ALL STAGING GATES** = PASS
22. **UNEXPECTED DELTA** = NONE — markets `[]`, profiles `[]`, routes `[]`, findings `[]`
23. **FORT LAUDERDALE PROJECTED PROFILES** = 85
24. **FORT LAUDERDALE PROJECTED ROUTES** = 96 (85 hotel + 1 hub + 10 corridor + 0 other)
25. **PROJECTED TOTAL MARKETS** = 32
26. **PROJECTED TOTAL PROFILES** = 2375
27. **PROJECTED TOTAL ROUTES** = 2646
28. **CANDIDATE MODE** = PROJECTED · NON-DEPLOYABLE
29. **DEPLOYMENT REFUSAL** = PASS (expected) — `authorizes_deployment = false`, `AWAITING_FOUNDER_AUTHORIZATION`, readiness unsigned
30. **CURRENT LIVE MODIFIED** = NO
31. **FORT LAUDERDALE DEPLOYED** = NO
32. **origin == HEAD** = YES
33. **tree clean** = YES
34. **READY FOR FOUNDER LAUNCH AUTHORIZATION** = YES

---

FORT LAUDERDALE REGISTRATION = PASS
FORT LAUDERDALE STAGING = PASS
FULL_REGRESSION_REQUIRED = NO
BROAD REGRESSION RUNS = 0
UNCHANGED MARKETS REBUILT = 0
FORT LAUDERDALE DEPLOYED = NO
CURRENT LIVE MODIFIED = NO
READY FOR FOUNDER LAUNCH AUTHORIZATION = YES

STOP.
