# ATLAS-THROUGHPUT-004 — persistent bundle cache contract

Module `scripts/pettripfinder/bundle_cache.py`; machine form `atlas_throughput_004_cache_contract.json`.

## The cacheable unit

    MARKET PACKAGE (sealed, by digest)
    + DECLARED BUILD DEPENDENCIES (the measured closure: 43 shared data files, the market's affiliate shard, 177 repository modules)
    + BUILDER VERSION (generator, pilot loader, staging, assembler source digests; the package's builder_version)
    + RELEVANT SHARED RUNTIME / TEMPLATE / ASSET INPUTS (part of the closure; digested separately as template / asset / data)
    + TOOLCHAIN / ENVIRONMENT IDENTITY (Python 3.13.5, platform, requirement lockfiles, installed package versions, locale, PTF_* env)
    + BUILD OPTIONS (context, cold, builder)
    = BUILD_INPUT_KEY (sha256 of the canonical manifest)

    -> MARKET BUNDLE BYTES (site/) + OUTPUT_BUNDLE_DIGEST + BUNDLE VALIDATION RECEIPT

The output digest is not an input to its own key. The validation policy version is carried on the manifest
but sits outside the byte key: a rule change never changes bytes, it changes what a receipt must prove.

## Storage, trust, lookup, publication

See the JSON: separate index rows and immutable objects; TRUSTED only through the publisher after every
listed check; a lookup re-extracts, re-hashes, re-reads and re-binds before it is a hit; quarantine on any
defect; archive → receipt → index row, each an atomic rename; per-key lock (O_EXCL file + thread lock,
stale locks broken); `cold_required` bypasses; `PTF_BUNDLE_CACHE_FORBID_BUILD=1` turns a miss into an error.

## Boundaries

A hit proves that these bytes are what these declared inputs produce. It does not authorise a release
(003's FAST lane does), it does not compose the site (005), and production does not consume it
(`PRODUCTION_RELEASE_CONSUMPTION = DISABLED`).
