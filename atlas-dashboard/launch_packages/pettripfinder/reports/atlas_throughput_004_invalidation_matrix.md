# ATLAS-THROUGHPUT-004 — invalidation matrix

Measured on the pilot cache (every probe in a separate process with builds FORBIDDEN, so a miss is proven
without building): 18/18 match.

| case | expected | actual | match | seconds |
|---|---|---|---|---|
| baseline_unchanged | HIT | HIT | True | 4.542 |
| policy_mutation | MISS | MISS | True | 1.317 |
| route_mutation | MISS | MISS | True | 1.323 |
| geography_mutation | MISS | MISS | True | 1.29 |
| shadow_repo_unchanged | HIT | HIT | True | 5.236 |
| template_mutation | MISS | MISS | True | 1.271 |
| builder_mutation | MISS | MISS | True | 2.653 |
| shared_runtime_mutation | MISS | MISS | True | 2.616 |
| market_tooling_only_mutation | HIT | HIT | True | 5.157 |
| lockfile_mutation | MISS | MISS | True | 1.273 |
| validation_policy_version_change_compatible | REVALIDATE | REVALIDATE | True | 3.271 |
| corrupt_artifact | MISS | MISS | True | 1.332 |
| missing_artifact | MISS | MISS | True | 1.295 |
| zero_byte_artifact | MISS | MISS | True | 1.276 |
| missing_receipt | MISS | MISS | True | 3.835 |
| wrong_receipt | MISS | MISS | True | 3.657 |
| malformed_metadata | MISS | MISS | True | 1.257 |
| revoked_entry | MISS | MISS | True | 1.248 |

## Policy

| change | expected | proof | actual |
|---|---|---|---|
| MARKET AUTHORITY CHANGED | changed market miss | policy_mutation / route_mutation / geography_mutation | MISS (key moved: package + section digests) |
| ROUTES CHANGED | relevant market miss | route_mutation | MISS |
| POLICY CHANGED | relevant market miss | policy_mutation | MISS |
| GEOGRAPHY / IDENTITY CHANGED | relevant market miss | geography_mutation | MISS |
| EVIDENCE REFERENCE CHANGED | follow the render/validation dependency | evidence_manifest_digest is in the key; a reference change is a new package | MISS by key |
| SHARED TEMPLATE CHANGED | every dependent market miss | template_mutation; multi-market after_shared_template_change | MISS for A, B and C |
| SHARED RUNTIME CHANGED | every dependent market miss | shared_runtime_mutation | MISS |
| BUILDER CHANGED | dependent bundles miss | builder_mutation | MISS |
| SCHEMA / CONTRACT CHANGE | per compatibility | contract_versions + declared closure digest in the key | MISS (no compatibility table yet: fail closed) |
| BUILD ARGUMENT CHANGED | relevant miss | build_arguments in the key | MISS |
| LOCKFILE / TOOLCHAIN CHANGE | affected closure miss | lockfile_mutation | MISS |
| MARKET TOOLING ONLY CHANGED | HIT remains valid | market_tooling_only_mutation | HIT |
| TEST-ONLY CHANGE | bytes reusable | tests/ is outside the closure | HIT (receipt unaffected: the bundle policy does not run tests) |
| VALIDATION POLICY / RULE CHANGED | bytes valid, old receipt cannot satisfy new policy | validation_policy_version_change_compatible | REVALIDATE (no build) then HIT; incompatible => INVALID_POLICY_VERSION |
| PARTICIPATION CHANGE | bundle may remain valid | launch_participation.json is not in the closure (the market bundle does not read it) | HIT; the release manifest must change (005) |
| EVIDENCE EXPIRED / REVOKED | no stale approval | revoked_entry; evidence revocation and expiry in verify() | INVALID_REVOKED => rebuild, which is UNTRUSTED while the evidence stays revoked |
