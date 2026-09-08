# ATLAS-THROUGHPUT-003 — sealed market package contract

Owning module: `scripts/pettripfinder/sealed_market_package.py` (schema `ptf-sealed-market-package/1.0`). The ONE writer:
`scripts/pettripfinder/market_package_writer.py` (`ptf-market-package-writer/1.0`). Machine form: `atlas_throughput_003_package_contract.json`.

## What a package is

One immutable document describing ONE market's proposed state, in the shapes the owning contracts
already define — never a second authority system:

| field | content | owning contract |
|---|---|---|
| `schema` | PACKAGE_SCHEMA_VERSION | sealed_market_package |
| `market_id` | MARKET_ID | ptf-market/1.1 |
| `package_id` / `package_digest` / `sealed_at` | the seal (digest over every body field; id from the digest; time outside it) | sealed_market_package |
| `created_from_source_sha` | CREATED_FROM_SOURCE_SHA | git |
| `execution_zone` | SHADOW, SHADOW_UNTIL_REGISTERED, REGISTERED_LIVE, FROZEN_COPY | market_local_ownership |
| `census` | CENSUS (`ptf-market-identity-census/1.1`) | contracts.census |
| `identity_records` | IDENTITY RECORDS derived from the census: canonical key, premises, brand family, property code, aliases, explicit relation | contracts.identity_key, hotel_exclusions |
| `market` | GEOGRAPHY / CORRIDOR ASSIGNMENTS (`ptf-market/1.1`) | markets.contract |
| `official_routes` | OFFICIAL ROUTES (`ptf-identity-routing/1.0` records) | identity_routing |
| `pet_friendly_records` | PET-FRIENDLY POLICY RECORDS (schema 1.2 / 1.3) | contracts.policy_schema, contracts.evidence |
| `verified_no_pets_records` | VERIFIED NO-PETS RECORDS (`ptf-hotel-exclusions/1.0`) | hotel_exclusions |
| `seed_rows` | the display inventory the verified-only join is made against | market_authority.SEED_COLUMNS |
| `partition` | `ptf-market-final-partition/1.1` | contracts.partition |
| `evidence_references` / `evidence_hashes` | EVIDENCE REFERENCES + HASHES: one reference per (identity, captured artifact) with URL, timestamp, kind, lane, grade, availability, optional paid reservation | contracts.evidence |
| `unresolved_rows` | UNRESOLVED ROWS (non-terminal partition rows) | contracts.partition |
| `founder_holds` | FOUNDER HOLDS | — |
| `intended_delta` | INTENDED DELTA: add / update / remove property ids, add / change / remove routes, expected profile, market-count, participation (and no-pets) deltas, `removal_authority` | release_index.compare |
| `parent_live_state` | the live release the delta is stated against (deploy id, rollback target, source commit, participation, profile counts, totals, live index digest) | release_index.current_verified_live |
| `dependency_input_digests` | DEPENDENCY INPUT DIGESTS (sha256 of every input the writer consumed) | — |
| `builder_version` / `contract_versions` | BUILDER / CONTRACT VERSION | — |
| `coverage_scorecard` | COVERAGE SCORECARD (counts, routes, references, artifacts available, paid references, partition state counts, reference source) | — |
| `validation_state` | always `SEALED_UNVALIDATED`: validation results live in a receipt, never in the package | fast_release_lane |

## Immutability

`package_digest` is sha256 over the canonical JSON of the body; `package_id = pkg-<market>-<digest16>`.
`write_sealed` writes once to `markets/packages/<market>/<package_id>.json` and refuses a different
document at that path; `read_sealed` refuses any document whose digest, id or filename does not re-derive.
A correction is a NEW package (pilot: P1 `pkg-dayton-oh-97f504ad2794e767` → P2 `pkg-dayton-oh-813f7f9f089b89c7`).

## What the writer rejects before serialization

Every rule is delegated to the module that owns it (see the JSON, `writer_rejections`). Measured on the
committed authority of this tree (a frozen copy, read only): Dayton seals as-is; every other live market is
refused on legacy facts the owning contracts state (`atlas_throughput_003_fast_lane_report.md`, "Legacy facts").

## Ownership

`markets/packages/<id>/`, `markets/staging/<id>/`, `markets/receipts/<id>/` were added to the zone template of
`market_local_ownership.json` and to Regression V2 as `MARKET_DATA_PACKAGE`: a market's proposed state is local
BY CONSTRUCTION. The pilot package is committed at `launch_packages/pettripfinder/markets/packages/dayton-oh/pkg-dayton-oh-813f7f9f089b89c7.json`, its receipt at `launch_packages/pettripfinder/markets/receipts/dayton-oh/pkg-dayton-oh-813f7f9f089b89c7-324148f81b55bc50.json`.
