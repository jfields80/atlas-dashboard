ATLAS-THROUGHPUT-002
MARKET-LOCAL OWNERSHIP, REGRESSION SCOPE, AND IN-RUN ASSEMBLY REUSE

STATUS: EXECUTED (see `ATLAS-THROUGHPUT-002_FINAL.md` at the git root and
`launch_packages/pettripfinder/reports/atlas_throughput_002_*`).

WORKTREE C:\Atlas-Throughput-V1 — BRANCH worker/atlas-throughput-001 —
continued from the clean, pushed ATLAS-THROUGHPUT-001 head 0a623a0.

MISSION

001 measured that routine market work pays for validation unrelated to its
blast radius: an instrumented broad run of 7,955 s of which the demo-media
suite was 5,630 s (71 %); 56 PetTripFinder assembly calls, 1,882 s, 37
identical builds over 19 keys (~710 s repeated, ~3,800 s more inside
demo-media); the whole site composed three times from identical inputs;
Columbus generated 15 times; and every Nashville / Toledo / Lexington /
Chattanooga helper forced broad by `prefix scripts/pettripfinder/` with some
routing filenames adding ROUTING_SEMANTIC_CHANGE. Regression V2 had no
notion of namespace ownership, import closure, write roots, reverse imports,
runtime reachability or market registration. 001 proved representative
helpers isolated by a five-condition mechanical proof and concluded
PROVABLY_TOO_BROAD = YES.

THREE OBJECTIVES

1. Mechanically enforced MARKET_LOCAL_TOOLING classification.
2. Demo-media removed from routine MARKET_LOCAL_TOOLING validation while
   preserved as explicit broad/audit coverage.
3. Repeated identical assembly work eliminated WITHIN a validation session by
   safe input-keyed reuse.

NOT in 002: market package promotion, release manifest redesign,
participation lifecycle, deployment coordinator, CI migration, persistent
cross-run cache, historical-test migration beyond touched tests, database
authority, production authority changes.

CRITICAL SAFETY RULE

Only MARKET-LOCAL / SHADOW tooling may be narrowed, and only after mechanical
isolation is proven. MARKET_AUTHORITY_CHANGE / PROMOTION keep the current
conservative release behaviour until ATLAS-THROUGHPUT-003 establishes the
replacement critical FAST launch lane.

PHASES (as executed)

1  Read 001 artifacts; confirm 001 HEAD, origin == HEAD, tree clean, 001
   TRUE_NEW = 0.
2  Locate the owning implementations (classifier, lanes, runner, broad
   selection, demo-media, per-market / whole-site assembly, generator,
   fixtures, contract tests, existing hashes).
3  One market ownership registry: MARKET, EXECUTION_ZONE, OWNED_PATHS,
   ALLOWED_SHARED_IMPORTS, ALLOWED_WRITE_ROOTS, ALLOWED_READ_ROOTS,
   OWNED_TESTS, PRODUCTION_RUNTIME_INCLUDED; Nashville, Toledo, Lexington,
   Chattanooga (and Fort Wayne) registered; no blanket claim over
   scripts/pettripfinder.
4  The five-condition isolation proof: namespace, import closure, write
   roots, reverse-import / runtime reachability (plugin registries,
   subprocess entry points, dynamic imports, directory enumeration), market
   registration / production reachability.
5  Fail-closed rules: unknown / malformed / multi-owner ownership, shared
   write, shared reverse import, unresolved dynamic dependency, classifier or
   ownership policy or test infrastructure changed, rename whose old OR new
   path fails, deleted file with consumers, shared schema / parser /
   identity / routing / assembler / deployment change. UNKNOWN stays broad.
6  Routing-name false positives corrected: a proven-local
   `<market>_routing_*.py` is not ROUTING_SEMANTIC_CHANGE for its name; a
   shared routing module still is.
7  Demo-media lane correction: `website_generation_integration` lane,
   BROAD_AUDIT role, still inside every full regression, never selected by a
   market-local plan; nothing deleted, skipped or weakened.
8-11 Session-local assembly reuse: one build per input key per process for
   the generator, the per-market bundle and the whole-site compose; key from
   build args + content fingerprint of every input root + patched registry /
   census dirs + PTF_* env + builder module state + interpreter; verified
   copies per consumer; failed builds never stored; `cold()` for cold-claim
   tests; profiler distinguishes BUILD_EXECUTED / REUSE_HIT with
   INPUT_KEY / BUILD_COUNT / REUSE_COUNT / BUILD_SECONDS /
   REUSED_SECONDS_AVOIDED. Demo-media: consumer reuse via one module fixture,
   cold claims kept.
12 Adversarial classifier matrix, cases A–N, from actual dependency evidence.
13 BEFORE/AFTER plans for Nashville, Chattanooga, Lexington, Toledo 001,
   Toledo 002/003.
14 Production / promotion safety freeze proven.
15 Targeted tests green.
16 Performance: representative MARKET_LOCAL run vs the 001 broad baseline;
   cold / reuse benchmark.
17 ONE-TIME migration audit (old-equivalent broad coverage incl. demo-media),
   TRUE_NEW_FAILURE = 0, waiting for any heavy lane first.
18 001 safety gaps recorded unchanged as REQUIRED INPUTS FOR 003.
19 Artifacts in the existing throughput reporting location.
20 Success criteria 1–15.
21 Git: separate commits, pushed, origin == HEAD, clean.

STOP. Do not start 003. No market authority change, no promotion, no deploy.
