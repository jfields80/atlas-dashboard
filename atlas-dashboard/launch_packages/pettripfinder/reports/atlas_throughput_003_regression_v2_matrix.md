# ATLAS-THROUGHPUT-003 — Regression V2 extension

Committed matrix: `launch_packages/pettripfinder/regression_validation_matrix.json` (14 rows; the six
mandatory-full classes are byte-identical to V2-001; the new rows are `MARKET_DATA_PACKAGE` and
`MARKET_AUTHORITY_DATA_ONLY`). Machine form: `atlas_throughput_003_regression_v2_matrix.json`.

## Release surfaces

| surface | FAST_DATA_ONLY_RELEASE_REQUIRED | FULL_REGRESSION_REQUIRED | why |
|---|---|---|---|
| MARKET_LOCAL_TOOLING | NO | NO | five-condition isolation proof (ATLAS-THROUGHPUT-002) |
| MARKET_DATA_PACKAGE | NO | NO | inert data named by digest; the fast lane's input, never a build's |
| MARKET_AUTHORITY_DATA_ONLY | YES | CONDITIONAL | NO only with a committed ELIGIBLE receipt covering the exact bytes and production activation; YES otherwise |
| SHARED_SCHEMA_CHANGE | NO | YES | a contract change moves what every market derives |
| SHARED_RUNTIME_CHANGE | NO | YES | shared runtime every market executes |
| ASSEMBLER_CHANGE | NO | YES | the assembler is the proof the fast lane's rule J relies on |
| DEPLOYMENT_CHANGE | NO | YES | deployment doctrine is proven by a fresh assembly |
| CLASSIFIER_TEST_INFRA_CHANGE | NO | YES | the selector cannot authorize its own narrowing |
| UNKNOWN_MIXED | NO | YES | an unclaimed path or a mixed set is the broad suite by definition |
| NARROW_NON_RELEASE | NO | NO | prose, reports, baselines, bookkeeping and owned test expectations |

## How a change set becomes MARKET_AUTHORITY_DATA_ONLY

A whole-set verdict, never a path's: every AUTHORITY_CHANGE row is ONE registered market's own authority file, or a derived global whose diff names only that market; no shared runtime / schema / assembler / deployment / classifier / test-infra row in the set; nothing UNCLASSIFIED; no narrowing blocker in the set

The plan then reports `FAST_DATA_ONLY_RELEASE_REQUIRED = YES`. `FULL_REGRESSION_REQUIRED = NO` only when ALL
of these hold; every gap fails closed to `AUTHORITY_CHANGE` behaviour: a sealed package under markets/packages/<market>/ whose dependency digests cover the head bytes of every changed authority data file; a committed receipt for that package's digest with FAST_DATA_ONLY_RELEASE_ELIGIBLE = YES and no UNKNOWN rule (parent/live state verified by rule N); fast_release_activation.json ENABLED with the market in pilot_allowlist

Today `fast_release_activation.json` says `FAST_PATH_PRODUCTION_ACTIVATION = DISABLED` with an empty allowlist,
so no real change set can drop the broad regression through this path yet (proved by
`test_the_fast_requirement_fails_closed_without_a_package_receipt_or_activation`, which lifts it only under a
monkeypatched ENABLED activation).

## What stays broad

SHARED_SCHEMA_CHANGE, SHARED_RUNTIME_CHANGE, ASSEMBLER_CHANGE, DEPLOYMENT_CHANGE, CLASSIFIER_TEST_INFRA_CHANGE
and UNKNOWN_MIXED. This order's own change set classifies CLASSIFIER_TEST_INFRA_CHANGE + UNKNOWN_MIXED and owes
the broad suite — the migration audit.
