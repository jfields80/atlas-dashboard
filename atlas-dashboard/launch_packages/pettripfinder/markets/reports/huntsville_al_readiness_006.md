# PTF-HUNTSVILLE-AL-NEW-MARKET-001 — readiness note

Prepared by PTF-NASHVILLE-POST-LAUNCH-TEST-HARNESS-CLEANUP-006. **Nothing is
started.** This records what Huntsville should begin from, and why that answer
is not "the canonical lineage" any more.

## Start from

| | |
|---|---|
| branch | `worker/ptf-nashville-new-lane-launch-002` |
| commit | the tip of this cleanup, pushed |
| production it inherits | 13 markets / 902 profiles / 1078 routes, deploy `6aa212a8ba9f174305c0441a` |

Not `f94a75a` and not `f75aa95`. Those were the required base while the
redesigned factory was being built; the Nashville launch is the first release
that went out through the ATLAS-THROUGHPUT lane end to end, and this cleanup is
the first branch on which a routine launch closure is cheap. Starting Huntsville
anywhere earlier would re-inherit the two defects this order closed.

## What the benchmark measures

Zero → census → routing → current evidence → registered authority → sealed
package → FAST validation → final candidate → founder authorization → live.

One market, built from nothing, with **no legacy migration and no old shadow
evidence**. Toledo and Lexington are the closest precedents; Nashville is not,
because Nashville carried a pre-redesign shadow and spent a whole order
recovering evidence a legacy attended lane had recorded without a document hash.

## What this cleanup changed underneath it

- **Evidence must carry a real document hash from the first capture.** Nashville
  paid an entire order to recover 84 rows whose attended capture stored a byte
  length. A fresh market has no excuse: hash the page in the same call that
  reads the quote.
- **The participation writer now extends the decision block.**
  `launch_participation.extend_decision` carries `supersedes` and `lineage`
  forward, and `decision_problems` refuses a block that drops them. Huntsville's
  launch inherits the repair: its participation write is the one that puts the
  chain back into the record, using
  `what_the_next_participation_write_must_carry` from
  `nashville_tn_participation_lineage_defect_005.json`.
- **A routine closure no longer renders the site.** The composition claims are
  proved from committed indexes in
  `test_release_composition_contract_006`, and the reviewed market list lives in
  one constant there. Huntsville's launch edits that one line; it does not need
  to run either full-assembly module to prove the line right.

## What has NOT changed and must not be assumed away

- A market's own suites and per-market contract rows still run.
- An assembler, shared-runtime, shared-schema or deployment-architecture change
  still selects `test_global_deployment_architecture_045` and
  `test_launch_participation_046`, which still render the whole site.
- The production gate allowlist is EMPTY and stays empty until a founder opens
  it for one market and one candidate.

## Open item Huntsville inherits

`deploy/netlify/launch_participation.json` still carries the stale `note` on the
`nashville-tn` row: it reads "8 pet-friendly profiles … NOT AUTHORIZED for
launch". The row's `launch_status` and `founder_decision` are correct; only the
prose is stale. It is sha256-bound into the live authorization and is corrected
by the next participation write, alongside the lineage.

HUNTSVILLE_READY_TO_START = YES — on this branch, after this commit is pushed.
Do not start it here.
