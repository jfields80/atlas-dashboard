# ATLAS-THROUGHPUT-003 → 004 input packet

Status: PROPOSED. 004 builds the PERSISTENT CONTENT-ADDRESSED MARKET BUNDLE CACHE. Nothing here is implemented in 003.

## What 003 delivered that 004 builds on

- A sealed package digest (`package_digest`, canonical JSON, `sealed_at` outside it) and a dependency digest
  (`dependency_input_digests` → `DEPENDENCY_DIGEST` in the receipt).
- A validation receipt naming the package, its parent live release (`live_deploy_id`, `live_index_digest`), the
  staged input digest, the derived contract digest, the changed-market bundle digest A/B, the global index
  digests, the rule results, and the conditions under which the receipt stops being true.
- A staging tree whose content is a pure function of (package digest, shared control files, contract sections)
  — `staged_input_digest` = sha256 over every staged file's hash (P2: `sha256:a6ba205ac580b5ca`).
- 002's session cache with BUILD_EXECUTED / REUSE_HIT accounting, and the proof that the changed-market bundle
  is byte-deterministic for identical staged inputs (K: `6340911b0605e4e2` twice).
- Measured build results: changed market 28.656 s per cold build (Dayton, 334 HTML files); live index 4.865 s.

## What currently prevents safe cross-run reuse (measured, not inferred)

1. **The bundle digest depends on more than the package.** The staged tree carries every registered market's
   registry entry, the shared control files (`headers.*`, `redirects`, `measurement.json`,
   `affiliate_providers.json`), `identity_resolutions.json`, and the four shared contract sections copied from
   the committed release contracts. 002's session key already fingerprints the whole `launch_packages/`,
   `deploy/netlify`, `scripts`, `engines`, `templates`, `static` trees (2,000+ files) — any byte there
   invalidates every key. A persistent cache needs a DECLARED input closure per build kind: the package digest,
   the shared-file digests it actually reads, and the code digest of the generator + assembler, not "the tree".
2. **The generator reads module state, not only files.** `module_state_signature` covers 26 modules' public
   values; a persistent key must pin the code identity (a commit sha of the build path modules, or a
   content hash of them) explicitly, since a cached bundle from a different assembler is exactly what H9 forbids.
3. **`release_name` and `generated_from_commit` carry the build's commit** (informational) — a persistent cache
   must either exclude them from the identity (semantic identity + excluded metadata, which the order permits
   only where the contract genuinely allows it) or accept a miss per commit. The bundle_sha256 P2 measured
   excludes nothing today: it was byte-identical across two builds in one tree.
4. **The whole-site compose is not keyed per market.** `assemble_production_site` composes 10 fragments and then
   runs 27 global gates over the composed tree; the per-market fragment is reusable by digest, the composition
   is not (002 measured 340.9 s for a preview compose whose fragments all hit). 004 needs a composed-bundle
   identity = f(sorted per-market bundle digests, control files, participation sha, assembler code digest).
5. **Nothing survives the process.** The session cache store is a per-process temp dir deleted at exit; the
   verify-on-hit re-hash exists (`SessionCache` refuses a stored copy whose digest moved) and is the model for
   a persistent store's integrity check.
6. **Receipts expire on live movement.** `EXPIRY_REVOCATION_CONDITIONS` name the live deploy id and index digest;
   a cached bundle validated against one parent release must not be served after production moves — the
   cache key must include the parent live digest, or the coordinator must re-run rules G/H/I/N (seconds) on
   every reuse.
7. **The legacy authority facts** (`atlas_throughput_003_fast_lane_report.md`, "Legacy facts") mean only Dayton
   currently seals; a persistent cache of bundles built from packages has one live market to cache until the
   data orders repair the others.

## Measurements 004 should take first

- Cold vs persistent-hit time for the changed-market bundle across two PROCESSES with an identical staged
  input digest (target: the 2.2 s copy 002 measured in-process).
- The size of the declared input closure per build kind (files, bytes) and how often each element changes
  across the last 20 commits.
- Whether `staged_input_digest` alone predicts `bundle_sha256` over the 11 committed markets (build each twice
  in a scratch worktree; expect 11/11 byte-identical).

## Hand-offs that are NOT 004's

- Repairing the legacy authority facts (a data order per market; production authority change = 0 here).
- Coordinating the paid call sites (H13) — the reservation contract is enforced at the package boundary only.
- Activating the fast path (`fast_release_activation.json`) — 005's release coordinator consumes receipts.
