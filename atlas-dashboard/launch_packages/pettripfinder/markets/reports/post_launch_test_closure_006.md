# PTF-NASHVILLE-POST-LAUNCH-TEST-HARNESS-CLEANUP-006

Production was not touched. It still serves 13 markets / 902 profiles / 1078
routes on deploy `6aa212a8ba9f174305c0441a`, Nashville at 79.

## The 39 fixture errors were not what they looked like

They looked like an assembler defect: a rendered Columbus profile fragment
missing from one run, a shared asset missing from another's composed bundle, in
both cases a file the build had just written. The work order's premise, that a
missing Columbus fragment is the defect, described the symptom.

`test_global_deployment_architecture_045` and `test_launch_participation_046`
each rendered the whole site into ONE hard-coded absolute path — `C:/t/ptf045t`
and `C:/t/ptf046t` — and each tore that path down with `shutil.rmtree`. The
house rule for proving a regression is to run the suite at HEAD and again in a
scratch worktree at the parent commit, and the obvious way to do that is to run
both at once. Two pytest processes then wrote into and deleted the same
directory.

The run log settles it:

| run | wall | result |
|---|---|---|
| alone, at HEAD | 18m 56s | 29 failed, 222 passed, **0 errors** |
| alone, at the parent commit | 16m 57s | 7 failed, 244 passed, **0 errors** |
| concurrent pair | 3m 00s | 21 failed, 191 passed, **39 errors** |
| concurrent pair | 1m 33s | 15 failed, 197 passed, **39 errors** |

Identical error counts, finishing two seconds apart, in a fraction of the time a
real assembly takes, because each build died when the other deleted its tree. A
standalone thirteen-market assembly run outside pytest completed cleanly in
623.9 s, which rules out the assembler, the participation record and Nashville.
Free disk space was 696 GB, which rules out the other obvious explanation.

**One root cause, not several.** Both symptoms are the same collision seen from
two builds.

**Fix:** `pettripfinder.conftest.assembly_scratch` returns a build root private
to the process, kept short because a long root trips the Windows 260-character
limit mid-build and produces the same missing-file symptom from a different
cause. `test_assembly_scratch_isolation_006` holds the rule, including a check
that no module hard-codes a machine-wide root again — and it asks a second
interpreter for its root rather than reasoning about `getpid`.

## The participation writer

The Nashville launch rebuilt the `decision` block from scratch and dropped
`supersedes` and `lineage`. The record loaded cleanly afterwards because
`load_participation` checked four fields and neither was among them. **The
defect was that the contract did not ask.**

- `extend_decision` builds the next block FROM the predecessor, so a writer
  cannot drop the chain: the predecessor becomes the newest ancestor and the
  ancestors it carried come forward whole. Where a repair record covers the
  record being extended, the ancestors come from the repair, so the next write
  puts the chain back rather than starting a new one-link chain.
- `decision_problems` refuses a block with no chain, a repeated ancestor, a
  shrinking authorized set, a `supersedes` that does not name the newest
  ancestor, a record listed as its own ancestor, and a decision that drops a
  market the previous one authorized. `load_participation` raises on any of it.
- The one exception is documented and per-record: a chain may be missing only
  while a repair record names that exact participation sha256. A stale repair
  covers nothing.
- `epochs.participation_decision_chain` is now a re-export, so the suites read
  the same implementation the writer and the assembler do.

The live Nashville authorization was not touched. The chain returns to the
record on the next participation write, which is Huntsville's.

## What a routine closure costs now

| | before | after |
|---|---|---|
| wall | 1136.98 s | 19.7 s |
| full-site assemblies | 2 | 0 |
| markets rendered | 26 | 0 |
| tests | 251 | 269 |

That is 57.7x, and no assertion was dropped to get it.

Thirty-five nodes across the two heavy modules require the full-assembly
fixture. Nine of them prove something that needs no rendered bytes at all, and
those claims now live in `test_release_composition_contract_006`, which executes
the derivations rather than describing them: `select_markets` really runs, and
its answer is compared with the participation record, the composed manifest and
what production serves. Seven need only the changed market's bytes. The
remaining nineteen genuinely need the composed multi-market bundle and were not
moved.

## Full integration is preserved

`test_global_deployment_architecture_045` and `test_launch_participation_046`
keep every claim about rendered bytes: control files, security headers,
canonical sitemap routes, route collisions, global shadowing, the live-route
migration gate and the byte-for-byte bundle comparisons. Both are in the
`deployment_architecture` and `full_regression` lanes and **neither is in
`market_targeted`** — which was already true. What pulled them into the
Nashville closure was their hard-coded market list; that list is now one
reviewed constant, held to reality by a module that builds nothing.

## Regression V2

`launch_participation.py` and `regression_lanes.py` are shared runtime modules,
so the classifier returns `FULL_REGRESSION_REQUIRED = YES`. Exactly one broad
regression was run and classified against the `f75aa95` baseline. No second run,
and no repeated loop.

A `MARKET_AUTHORITY_DATA_ONLY` launch now selects the three cheap modules
through `market_targeted` and does not select the two heavy ones.
