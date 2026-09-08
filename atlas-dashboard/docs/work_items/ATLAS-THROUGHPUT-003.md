# ATLAS-THROUGHPUT-003 — critical fast release lane + sealed market package writer

Branch `worker/atlas-throughput-001`, continued from the pushed 002 head `e982aad`. Engineering only:
no market authority changed, nothing promoted, nothing deployed, no paid provider call.

## What exists now

| piece | module | what it proves |
|---|---|---|
| Sealed market package contract | `scripts/pettripfinder/sealed_market_package.py` | one immutable document (`ptf-sealed-market-package/1.0`) per proposed market state; digest over canonical JSON, id from the digest, never rewritten in place |
| Typed writer | `scripts/pettripfinder/market_package_writer.py` | the ONE path from proposed state to a package; rejects before serialization on every owning contract (policy schema, evidence, census, partition, exclusions, routing, market, identity key, display join, same premises) |
| Staging | `scripts/pettripfinder/package_staging.py` | a repository-shaped staging tree + an overlay of the loaders' path constants; the changed market builds through the real per-market assembler with committed authority untouched |
| Whole-release index | `scripts/pettripfinder/release_index.py` | CURRENT_VERIFIED_LIVE from the deployed record + manifest + pin (they must agree; the rollback chain is checked), the O(data) identity/route index, compose + compare with intended-delta accounting |
| First-party gate | `scripts/pettripfinder/first_party_binding.py` | eight machine checks per clean record; competitor evidence is LEAD ONLY; a fee / count / weight / amenity chip / service-animal sentence alone establishes nothing (the owning reader decides) |
| The lane + receipt | `scripts/pettripfinder/fast_release_lane.py` | rules A–O, UNKNOWN ⇒ NOT ELIGIBLE, two COLD builds for determinism, the machine-readable receipt under `markets/receipts/<market>/` |
| Regression V2 | `scripts/pettripfinder/regression_delta.py` | `MARKET_DATA_PACKAGE`, `MARKET_AUTHORITY_DATA_ONLY` (whole-set verdict), release surfaces, `FAST_DATA_ONLY_RELEASE_REQUIRED`, fail-closed activation boundary |
| Policy files | `launch_packages/pettripfinder/fast_release_activation.json`, `evidence_revocations.json` | `FAST_PATH_PRODUCTION_ACTIVATION = DISABLED`, empty pilot allowlist; an empty revocation registry rule M consults |
| Ownership | `launch_packages/pettripfinder/market_local_ownership.json` | `markets/packages/<id>/`, `markets/staging/<id>/`, `markets/receipts/<id>/` inside every zone |
| Pilot | `scripts/pettripfinder/atlas_throughput_003_pilot.py` | four frozen packages measured; the Dayton withdrawal package and its ELIGIBLE receipt committed under `markets/packages/dayton-oh/` and `markets/receipts/dayton-oh/` |
| Tests | `tests/pettripfinder/test_atlas_throughput_003.py` | 69 tests including the 25-case adversarial matrix (one `slow` test executes two real cold builds) |

Reports: `launch_packages/pettripfinder/reports/atlas_throughput_003_*` (package contract, fast-lane report,
safety matrix, adversarial results, performance, validation receipt example, Regression V2 matrix, 004 input
packet, migration audit). Runbook: `docs/PTF_HARDENED_FACTORY_RUNBOOK.md` § FAST_DATA_ONLY_RELEASE.

## How to use it

```
python -m scripts.pettripfinder.atlas_throughput_003_pilot --work-dir <tmp> --out <report.json> --no-commit
python -m scripts.pettripfinder.regression_delta classify --base <sha>     # release_surfaces, fast_data_only_release
python -m pytest tests/pettripfinder/test_atlas_throughput_003.py -m "not slow"
```

A market order that wants the fast lane: build `PackageInputs` from its proposed state (the pilot shows the
derivation for a shadow branch and for committed authority), `build_sealed_package`, `write_sealed` under the
market's packages directory, `run_fast_lane` with builds, `write_receipt`. The receipt's
`FAST_DATA_ONLY_RELEASE_ELIGIBLE` is the proof; whether a plan may act on it is `fast_release_activation.json`'s
decision, closed until 004/005.

## What it found in the live authority (not changed here)

Only Dayton's committed authority satisfies the owning contracts as a data-only package, and even Dayton
carries five records the first-party gate refuses (three bare acceptance labels, one fee sentence cited as the
acceptance, one bare `"petsAllowed": false`). Fifteen live records declare a bare-brand identity key. Every
other live market is refused by the writer on legacy facts (uncited facts, missing capture hashes, partitions
that predate their promotion, dangling routing records, unproven same-premises pairs). These are recorded in
`atlas_throughput_003_fast_lane_report.md`; each is a data order's repair.
