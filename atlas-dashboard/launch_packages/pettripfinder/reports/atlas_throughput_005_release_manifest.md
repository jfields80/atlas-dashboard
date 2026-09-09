# ATLAS-THROUGHPUT-005 — release manifest contract

`ptf-release-manifest/1.0`, serialised canonically; the release digest is sha256 over the canonical document.

| field | shape | why |
|---|---|---|
| schema / release_schema_version | ptf-release-manifest/1.0 | the manifest's own contract version |
| coordinator_version | ptf-release-coordinator/1.0 | which coordinator composed it |
| created_at | ISO-8601 Z | when it was staged |
| parent_release_digest | sha256:... | the release this one is composed FROM |
| source_commit | 40 hex | the tree that staged it (never the membership authority) |
| context / base_url / anchor_market | production | preview | what the bundle is FOR |
| participating_markets | sorted market ids | FINAL membership, present before hashing |
| participation_sha256 | sha256 of the participation document | the founder decision that admits them |
| markets[] | market_id, package_digest, build_input_key, bundle_digest, validation_receipt_digest, fragment_source, fragment_digest, profile_count, route_count | one row per participating market: where its bytes came from and what it publishes |
| intended_delta / intended_delta_digest | the package's declared delta | what this release means to change |
| global_artifacts | {path: sha256} | every release-global file this release regenerated |
| global_index_digest | sha256:... | the composed release index (003's lightweight index) |
| deployment_artifact_digest | sha256 hex | bundle_digest(file_hashes(site)) — the deployable identity |
| sitemap_sha256 / total_profiles / sitemap_route_count / total_html_pages / total_files | counts | what the artifact contains |
| validation_policy_version | ptf-bundle-validation/1.0 | the bundle validation policy the reused bundles were validated under |
| assembler_digest / builder_digest | sha256 of the module sources | what composed it |
| status | SOURCE_READY | CANDIDATE_STAGED | FOUNDER_AUTHORIZED | LIVE | FAILED | ABANDONED | where in the lifecycle it is |

**Membership is an argument, not a later edit.** `release_manifest()` takes the participating markets and the
participation document's sha256 as inputs, so a candidate digest cannot exist before the participation
decision is inside it. That is what makes a pre-flip digest unusable as authorization for a post-flip release.
