ATLAS-THROUGHPUT-001
BASELINE, INSTRUMENTATION, AND SUCCESS-CRITERIA FREEZE

STATUS: EXECUTED (see the FINAL report at the git root,
`ATLAS-THROUGHPUT-001_FINAL.md`, and the artifacts under
`launch_packages/pettripfinder/reports/atlas_throughput_001_*`).

WORKTREE
C:\Atlas-Throughput-V1

BRANCH
worker/atlas-throughput-001

MISSION

A bounded Atlas / PetTripFinder factory-throughput redesign begins here. The
business problem is operational throughput: market acquisition has become fast
(Pittsburgh mature revalidation ~48 min, Louisville ~56 min, Toledo new market
~135 min to promotion-ready, Nashville ~181 census / 80 PF / 19 no-pets in
~98 min of market work) while the dominant remaining delay appears to be broad
regression, repeated assembly, broad classification of market-local tooling,
repeated validation after narrow repairs, hardware contention and release
complexity. A broad regression collects ~17,000+ tests and has required
100-115 minutes uncontended.

This order MEASURES. It does not change policy, architecture, market
authority, validation scope, or any safety guard.

PRIMARY OBJECTIVE

Produce a trustworthy baseline that answers: why Regression V2 classifies each
change category as narrow or broad; which tests consume the most wall time;
which tests cause market assembly; how many times the same market/input is
assembled in one broad run; time spent in collection, execution, assembly,
fixture setup/teardown, release assembly, historical validation, subprocess
work; peak memory of the pytest process, the process tree and assembly
subprocesses; which byte-identical inputs are rebuilt; which market-local
helper files trigger broad classification; why TestEveryMarketAssembles exists
and what it executes; the current critical launch-safety invariants; which of
the ~160 known baseline failures are relevant to identity, policy, artifact
integrity or release correctness; and which work could become cacheable.

FACTORY REDESIGN CONTEXT (evaluated, NOT implemented here)

MARKET WORKER -> SEALED MARKET PACKAGE -> MARKET-LOCAL / FAST VALIDATION ->
READY QUEUE -> RELEASE COORDINATOR -> REUSE UNCHANGED VALIDATED MARKET BUNDLES
-> BUILD CHANGED MARKET / REQUIRED DEPENDENTS ONLY -> CHEAP GLOBAL CONSISTENCY
CHECK -> FINAL CANDIDATE -> FOUNDER AUTHORIZATION -> DEPLOY EXACT TESTED BYTES
-> TARGETED LIVE VERIFICATION

SAFETY / SCOPE

Engineering-only worktree. Do NOT mutate any market census, PF authority,
no-pets authority, current-state pins, production participation, source
promotion state, deployment authorization, deployment records, live host
state, paid-provider ledgers, Firecrawl / Bright Data / Places state, or
founder rulings. No browser research, no evidence acquisition, no deploy, no
promotion. Instrumentation must be read-only regarding production authority,
deterministic where practical, removable or intentionally reusable, and
isolated from production runtime.

PHASES

1  Mechanical precheck (worktree, branch, HEAD, upstream, tree status; locate
   the real implementations of Regression V2, the classifier, the lane runner,
   the baseline machinery, the assemblers, TestEveryMarketAssembles, the
   contracts, the pins and the production truth).
2  Current production / release model: every representation of release truth
   with OWNER / WRITER / READER / DERIVED-OR-AUTHORITATIVE / HASHED INTO
   RELEASE / MUTABLE BEFORE DEPLOY.
3  Regression V2 audit: every change class and trigger; classification ONLY
   of representative market-local paths (Nashville, Toledo); rename,
   deletion, new-file, conftest, schema, test-infrastructure and unknown-path
   behaviour.
4  Full test inventory (node id, file, class, markers, fixtures,
   parametrization, analytical category); exact collected count.
5  Assembly call graph; TestEveryMarketAssembles in detail; duplicate builds;
   fixture scopes; xdist multiplication; reusable hashes.
6  Instrumentation: minimal, JSONL/CSV, fail-safe, no semantic change.
7  Existing log reconstruction FIRST; no new broad run merely for
   completeness.
8  ONE solitary instrumented broad baseline, only after checking no other
   heavy Atlas lane is running (else WAITING_FOR_HEAVY_LANE).
9  Broad run profile: wall / collection / execution / peak memory / counts;
   top 25 nodes, top 20 fixtures, top 20 assembly input keys, assembly
   invocations, unique inputs, repeated identical assemblies and their cost.
10 Failure baseline audit: group the ~160 known failures; waive nothing.
11 Market-local change case study (Nashville / Toledo): what fact makes
   Regression V2 demand a broad run; is isolation provable.
12 Release safety invariants: the minimum current checks for 13 hazards and
   whether each can be tested without full all-market rendering.
13 Performance baseline table by phase.
14 Bottleneck ranking: verified / strongly indicated / speculative.
15 Freeze success criteria as a machine-readable proof contract.
16 Define (do not execute) the three-market throughput experiment.
17 Design input for ATLAS-THROUGHPUT-002, every recommendation tied to
   measured evidence.
18 Durable artifacts under the existing reporting location.
19 Targeted tests for the instrumentation; the one solitary baseline is its
   broad validation; TRUE_NEW_FAILURE = 0 relative to the known baseline.
20 Git: commit instrumentation, tooling, reports, criteria and 002 planning
   only; push to origin/worker/atlas-throughput-001; origin == HEAD; clean.

FINAL REPORT

Precheck, release model, Regression V2, test inventory, assembly call graph,
baseline profile, memory profile, failure baseline, market-local case study,
critical safety invariants, bottleneck ranking, frozen success criteria,
three-market experiment, artifacts, git; then the seven closing answers
(biggest measured source of delay; identical assembly builds and their cost;
why a market-local helper required a broad run; whether that is provably too
broad; what 002 implements first; whether the 7-day redesign is still
plausible).

STOP. Do not begin 002. Do not modify production authority. Do not deploy.
Do not launch another broad regression. Do not expand beyond the measured
problem.
