# PTF-LINEAGE-TEST-047-SEMANTICS-REPAIR-001 — FINAL

**Result: PASS.** One stale test semantic repaired. Test-only: no production record, code, data or deployment changed.

| | |
|---|---|
| Worktree | `C:\Atlas-PTF-Lineage-Test-047-Repair` |
| Branch | `worker/ptf-lineage-test-047-repair-001` |
| Base | `748db16f` (= `origin/worker/ptf-west-palm-beach-fl-market-001`) |
| File changed | `atlas-dashboard/tests/pettripfinder/test_deployment_authorization_047.py` (+ this report) |

---

## 1 — Current live (before and after)

Resolver: `python -m scripts.pettripfinder.release_index live-source --verify-host`, plus `release_index.live_index()`.

| | before | after |
|---|---|---|
| RESOLVED | YES | YES |
| CURRENT LIVE SOURCE COMMIT | `e3efa2210f759886aaad830b07fa241231a8f734` | same |
| CURRENT LIVE DEPLOYMENT | `6ab599163f833ab7f48b395d` (`ptf-deploy-west-palm-beach-007-…`) | same |
| bundle / sitemap | `23728b4b…` / `8ae34cea…` | same |
| MARKETS / PROFILES | 33 / 2424 | 33 / 2424 |
| RELEASE-INDEX ROUTES | 2701 (live_index, 0 problems) | 2701 |
| SERVED ROUTES | 2767 | 2767 |
| HOST VERIFIED | true | true |

West Palm Beach, Fort Lauderdale and Augusta are LIVE and `FOUNDER_AUTHORIZED_FOR_LAUNCH`. Detroit
(`detroit-ann-arbor-mi`) is `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH`, not in the live set, and has 0 URLs in the
served sitemap. The tree was clean at the start.

## 2 — The failure, reproduced

`test_deployment_authorization_047.py::test_the_lineage_is_ordered_and_ends_before_the_current_record` at base:
**FAILED**, `AssertionError: the authorized set only ever grew` (`assert counts == sorted(counts)`, line 233). The base
module ran 49 collected, 48 passed, 1 failed (this node only).

The decrease is at lineage record 33, `PTF-WEST-PALM-BEACH-FL-CORRECTED-REREGISTRATION-005`: **33 → 32**. The market
responsible is **`west-palm-beach-fl`**. Every other transition in the 34-record lineage grows or stays the same.

## 3 — The actual contract (read from the implementation)

`PTF-CANONICAL-REREGISTRATION-LANE-REPAIR-001` added the rule. It lives in `launch_participation.py`: the
`FOUNDER_AUTHORIZATION_SUPERSEDED` docstring, `supersession_problems`, `decision_record` and `decision_problems`.

- **Ordinary decision:** `decision_problems` refuses any market that the predecessor authorized and this decision
  drops, unless the market is named in this decision's `founder_authorization_superseded`. The error reads
  "drops market(s) the previous one authorized".
- **Authorized, non-live re-registration supersession:** `supersession_problems` validates each entry. An entry must
  carry exactly `market_id, authorizing_decision, superseded_package_digest, corrected_package_digest,
  deployment_authorizations, market_live, reauthorization_required`, in that order, and:
  - the predecessor authorized the market;
  - the market is no longer `FOUNDER_AUTHORIZED_FOR_LAUNCH` and reads `SOURCE_READY_BUT_NOT_…`;
  - `authorizing_decision` is a record of this decision's lineage, and that record authorized the market;
  - both package digests are well-formed and differ from each other;
  - every named deployment authorization is `SUPERSEDED` and binds a bundle;
  - `market_live` is `false`;
  - `reauthorization_required` is `true`.
- **Lineage:** `decision_record` carries the superseded market ids forward into every later lineage record.
  `decision_problems` requires that `len(authorized) + cumulative superseded` never shrinks.
- **Live market:** `market_live` must be false. `supersession_problems` does not read disk; the re-registration lane
  proves the live and authorization state.
- **New founder authorization:** an ordinary later decision that adds the market back
  (`decision_basis.registered_package_digest` = the corrected digest). The re-registration lane refuses a
  reissue that keeps the old founder authorization.

The order's expected wording matches. One refinement: the count-level check in `decision_problems` is looser than
the set-level rule each decision passed when it was written. The repaired test asserts the set-level rule.

## 4 — The West Palm Beach proof (from committed bytes: `git show <commit>:launch_participation.json`)

| decision | commit | participation sha | authorized | WPB | `decision_problems` |
|---|---|---|---|---|---|
| 003 founder | `d4da13d1` | `19328995…` | **33** | FOUNDER_AUTHORIZED | `[]` |
| 005 re-registration | `174d6b31` | `c3f5fc94…` | **32** | SOURCE_READY_BUT_NOT_… | `[]` |
| 006 new founder | `ff6b506d` | `837d37d3…` (current) | **33** | FOUNDER_AUTHORIZED | `[]` |

- Links: 005 `supersedes` = 003's sha, and 006 `supersedes` = 005's sha.
- 003 → 005 dropped exactly `[west-palm-beach-fl]` and added nothing. 005 → 006 added exactly
  `[west-palm-beach-fl]`. The 006 authorized set equals the 003 authorized set.
- The 005 entry has `authorizing_decision` = 003, digests `789c0187…` → `94d6f411…`, auth
  `ptf-auth-west-palm-beach-003-217f87eeba72` `SUPERSEDED`, `market_live: false`, `reauthorization_required: true`.
- **WPB was not live at 005.** At `174d6b31` there were 35 deployment records and none included WPB. Today the only
  record that includes WPB is `ptf-deploy-west-palm-beach-007-…`, which consumes the NEW auth.
- **The old authorization is terminal.** `217f87ee` is `SUPERSEDED` at 005 and at HEAD. Its history is
  `PREPARED → AUTHORIZED → SUPERSEDED`, never `DEPLOYED`, and no record consumes it (UNCONSUMED).
  `TRANSITIONS[SUPERSEDED] = ()`, and it is not in `DEPLOYABLE_STATUSES` (NON-DEPLOYABLE).
- **A new authorization was required and issued.** `ptf-auth-west-palm-beach-006-23728b4bff71` binds the 006
  participation (`837d37d3…`) and bundle `23728b4b…` (≠ `217f87ee…`). The 006 decision basis records
  `old_authorizations_authorize_this_package: false`. Nothing was transferred.

Every fact the order required holds, so the test is stale and production is correct.

## 5 — The repaired assertion

**Old invariant:** `counts == sorted(counts)`, meaning the raw founder-authorized count never decreases.

**New invariant:** `_lineage_problems(chain, current, authorizations, deployments) == []`, plus
`LP.decision_problems(current) == []`. The lineage covers every ancestor plus the current decision's own record, and
the check runs against every committed deployment authorization and record. For each transition:

- A decision may drop only markets it records in `founder_authorization_superseded`. Any other drop is refused.
- A superseded market must have been authorized by the predecessor and must not still be authorized.
- A superseded market must not have been **live**. That means no deployment record serves it under an authorization
  placed at or before the superseding decision. Each authorization is placed in time by the participation sha it
  signed, and an unplaceable one counts as old (fail closed).
- At least one old authorization must exist, and every old authorization of the market must be `SUPERSEDED` and
  never `DEPLOYED`.
- Every later authorization serving the market must bind a decision that authorizes it again, under a bundle that
  differs from every superseded one (no inheritance).
- The current decision's `supersedes` must equal the newest ancestor.
- The current decision must authorize every market served by the newest `DEPLOYED` record.

The node also keeps its original assertions: no repeated record, the current record is not an ancestor, and
`supersedes` names the newest ancestor. It adds that every raw shrink equals exactly the superseded set it records.
The rule is placed in time by the lineage itself, so it stays valid as later decisions extend the chain.

## 6 — Negative coverage (in-memory deep copies; no committed file is touched)

A new `test_the_west_palm_beach_supersession_is_33_32_33` pins the proof above. There are 20 negative nodes, each
asserting its specific refusal:

| # | case | node(s) |
|---|---|---|
| 1 | ordinary decision drops a market | `test_refuses_an_ordinary_decision_that_drops_a_market` |
| 2 | supersession metadata missing | `test_refuses_a_supersession_with_no_metadata` |
| 3 | supersession names the wrong market | `test_refuses_a_supersession_that_names_the_wrong_market` |
| 4 | drops two markets | `…_that_drops_a_second_market`, `…_that_names_a_second_live_market` |
| 5 | superseded market live | `test_refuses_superseding_a_live_market`, `test_refuses_a_next_decision_that_supersedes_the_now_live_market` |
| 6 | old authorization deployable / consumed / absent | `test_refuses_an_old_authorization_that_is_not_terminal` ×3 (AUTHORIZED, PREPARED, SUPERSEDED-after-DEPLOYED), `…_with_no_old_authorization` |
| 7 | corrected package inherits the old authorization | `…_keeps_the_market_authorized`, `…_bound_to_the_superseding_decision`, `…_bound_to_the_old_founder_decision`, `…_rebinds_the_old_bundle` |
| 8 | lineage reversed | `test_refuses_a_reversed_lineage` |
| 9 | predecessor link broken | `…_predecessor_is_not_the_newest_ancestor`, `…_authorizing_decision_cut_out`, `test_refuses_a_repeated_record` |
| 10 | current decision does not reconcile | `test_refuses_a_current_decision_that_drops_a_live_market` (and the live-supersession case in 5) |

All of them fail closed.

## 7 — Targeted tests (one pytest process at a time)

| run | collected | passed | failed | skipped | runtime | peak working set |
|---|---|---|---|---|---|---|
| A repaired node | 1 | 1 | 0 | 0 | 0.46 s | — |
| B `test_deployment_authorization_047.py` | 70 | 70 | 0 | 0 | 2.64 s (4.28 s wall) | 55.8 MB |
| C `test_reregistration_lane_001.py` | 75 | 75 | 0 | 0 | 101.56 s (103.04 s wall) | 67.3 MB |
| **B + C** | **145** | **145** | **0** | **0** | | |

C is the canonical re-registration and decision-chain battery. I did not run broad regression, whole-site assembly,
demo-media, throughput or unrelated launch modules.

## 8 — Differential

No targeted failure remains, so there is no node to run at base. The base module was run in a temporary detached
worktree at `748db16f`, which was then removed: 49 collected, 48 passed, 1 failed, and that failure was the stale
node. Of the 70 nodes now, 49 are the originals and 21 are new.

REPAIR_CAUSED = 0 · PRE_EXISTING = 0 remaining (the one stale failure is repaired) · CURRENT_REAL_DEFECT = 0 · UNRESOLVED = 0

## 9 — Zero production delta

`git diff --name-only` shows only the 047 test file (and this report).

Decision records, participation, founder authorization, deployment authorizations, deployment records,
`supersessions.json`, market data and production code: **0 changes**. Current live: unchanged. Deployment
performed: **NO**.

## 10 — Answers

```
1. CURRENT LIVE DEPLOYMENT = 6ab599163f833ab7f48b395d
2. CURRENT LIVE MARKETS = 33
3. FAILING TEST NODE = tests/pettripfinder/test_deployment_authorization_047.py::test_the_lineage_is_ordered_and_ends_before_the_current_record
4. OLD TEST INVARIANT = raw founder-authorized count never decreases (counts == sorted(counts))
5. CURRENT CANONICAL INVARIANT = a decision may drop only the markets it records in founder_authorization_superseded; each was authorized by its predecessor, is not live, has only terminal never-deployed old authorizations, and is served again only under a later decision that re-authorizes it with a different bundle
6. 003 AUTHORIZED COUNT = 33
7. 005 AUTHORIZED COUNT = 32
8. 006 AUTHORIZED COUNT = 33
9. 005 SUPERSESSION VALID = YES (decision_problems [] for 005 and 006)
10. WPB LIVE DURING 005 SUPERSESSION = NO
11. OLD WPB DEPLOY AUTH TERMINAL = YES (SUPERSEDED, never DEPLOYED, unconsumed)
12. OLD AUTH TRANSFERRED TO NEW PACKAGE = NO
13. TEST FILES CHANGED = 1
14. PRODUCTION FILES CHANGED = 0
15. NEGATIVE CASES = 20 (all 10 required classes)
16. TARGETED TESTS COLLECTED = 145
17. TARGETED TESTS PASSED = 145
18. TARGETED TESTS FAILED = 0
19. TARGETED TESTS SKIPPED = 0
20. REPAIR_CAUSED FAILURES = 0
21. PRE_EXISTING FAILURES = 0
22. CURRENT_REAL_DEFECTS = 0
23. UNRESOLVED = 0
24. DECISION RECORDS CHANGED = 0
25. PARTICIPATION CHANGED = 0
26. DEPLOYMENT RECORDS CHANGED = 0
27. CURRENT LIVE MODIFIED = NO
28. DEPLOYMENT PERFORMED = NO
29. WEST PALM BEACH STILL LIVE = YES
30. origin == HEAD = YES
31. tree clean = YES
32. READY TO RESUME MARKET EXPANSION = YES
```
