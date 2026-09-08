# ATLAS-THROUGHPUT-004 — canonical build input manifest

`bundle_cache.build_input_manifest(package, staged_input_digest)`; key = `build_input_key(manifest)`.
Full example (the Dayton pilot entry) in `atlas_throughput_004_input_manifest.json`.

| field | source |
|---|---|
| PACKAGE_DIGEST, MARKET_ID, package schema | the sealed package |
| AUTHORITY DIGEST | census + no-pets records + official routes + seed rows |
| ROUTE DIGEST | the public routes the package publishes (release_index) |
| POLICY DIGEST | the pet-friendly records |
| EVIDENCE MANIFEST DIGEST | evidence references + hash index |
| GEOGRAPHY / IDENTITY DIGEST, MARKET CONFIG DIGEST, partition digest | market config, identity records, partition |
| RENDER INPUT DIGEST | sha over every staged file (package authority, registry copies, derived contract) |
| BUILDER DIGEST / ASSEMBLER DIGEST | generator + pilot loader + staging sources / assemble_netlify_bundle source |
| SHARED RUNTIME DEPENDENCY DIGEST | sha over the 177 repository modules the build loads (measured) |
| TEMPLATE / ASSET / SHARED DATA DIGESTS | the 43 shared files the build reads, split by extension; + the market's affiliate shard |
| LOCKFILE / TOOLCHAIN | requirements.txt + requirements-dev.txt digests, Python version/implementation, platform, installed versions of every declared package; Node: not applicable |
| BUILD ARGUMENTS, LOCALE, ENV INPUTS | context, cold, builder; preferred encoding + utf8 mode; PTF_* variables |
| VALIDATION POLICY VERSION, fast-lane version, contract versions, builder version | recorded; the policy version is outside the byte key |

Coverage rule: a build that reads a repository file outside the closure is UNTRUSTED (fail closed), never
a wider key computed after the fact. Undeclared reads in the pilot: {"data": [], "code": []}.
