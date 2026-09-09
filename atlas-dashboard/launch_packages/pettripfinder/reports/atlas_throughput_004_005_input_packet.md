# ATLAS-THROUGHPUT-004 → 005 input packet

Status: PROPOSED. 005 builds the ATOMIC RELEASE COORDINATOR + FINAL CANDIDATE LIFECYCLE. Nothing here is implemented in 004.

## What 005 has to build on (all measured, all committed)

| input | where | identity |
|---|---|---|
| SEALED PACKAGE | `markets/packages/<market>/<package_id>.json` (003) | `package_digest` |
| PERSISTENT VALIDATED MARKET BUNDLE | `data/bundle_cache/objects/<bundle sha>.zip` + `index/<key>.json` (004) | `output_bundle_digest` (the deployer's `bundle_digest` formula) |
| BUILD INPUT KEY | `bundle_cache.build_input_key(manifest)` | sha256 over the canonical manifest (closure-measured) |
| VALIDATION RECEIPTS | package receipt `markets/receipts/<market>/` (003, rules A–O); bundle receipt `data/bundle_cache/receipts/` (004) | `RECEIPT_DIGEST` / `receipt_digest` |
| CURRENT VERIFIED LIVE RELEASE | `release_index.current_verified_live()` (record ↔ manifest ↔ pin ↔ authorization) | deploy id + `live_index_digest` |
| INTENDED DELTA | the package's `intended_delta` (+ `INTENDED_DELTA_DIGEST` on the receipt) | digest |
| GLOBAL RELEASE INDEX | `release_index.compose/compare` (O(data), 0.8126 s at 100 markets) | `GLOBAL_INDEX_DIGEST` live / proposed |
| UNCHANGED BUNDLE REUSE | `BundleCache.build_or_reuse` → HIT in ~3.732 s per market, builder invocations 0 | `build_input_key` → `output_bundle_digest` |
| PARENT RELEASE DIGEST | `parent_live_state.live_index_digest` + the live bundle sha | digest |

## Global artifacts that must regenerate per release (Phase 14/15 map)

| artifact | depends on | class |
|---|---|---|
| per-market fragment (`pet-friendly-hotels/<market>/…`, `/go/<market>/…`) | the package + declared closure only (no other market, no counts, no commit, no wall-clock in the bytes) | PER-MARKET CACHEABLE (this order) |
| global home `index.html` (`build_global_home`: anchor page + visible markets) | membership, navigation, anchor shell | GLOBAL MUST REGENERATE |
| global hotel index `pet-friendly-hotels/index.html` | membership, per-market counts | GLOBAL MUST REGENERATE |
| `sitemap.xml` (`build_global_sitemap` over every indexable route) | every market's route set | GLOBAL MUST REGENERATE (cheap: O(routes) from the release index) |
| `robots.txt` | base_url only | GLOBAL INCREMENTAL (static per base_url) |
| `_headers`, `_redirects` | committed control files | GLOBAL INCREMENTAL (copied, hashed into the authorization) |
| the anchor market's global shell pages (about, contact, methodology) | the anchor bundle | PER-MARKET CACHEABLE via the anchor's bundle |
| search index | none exists (static site; no search artifact) | n/a |
| global counts embedded in market pages | none found (grep of the Dayton bundle: 0 other market names, 0 totals, 0 release ids) | n/a |
| the composed `bundle_sha256` + 27 global gates | all of the above | GLOBAL MUST REGENERATE — identity = f(sorted per-market bundle digests, control files, participation sha, assembler digest) |

Time-dependent output: none in the bytes (copyright year is a literal; `date.today()` feeds the launch-readiness
gate only and is recorded on the bundle receipt as `reference_date`).

## What still prevents CURRENT LIVE MANIFEST + ONE AUTHORIZED PACKAGE DELTA = ONE FINAL STAGED CANDIDATE

1. **The whole-site compose has no per-market identity.** `assemble_production_site` re-generates every fragment
   through the generator and re-runs 27 gates over the composed tree; it cannot take a cached bundle as a
   fragment. 005 needs a composer that accepts N trusted bundles by digest + the anchor's shell and produces
   the global artifacts above, with the composed digest = f(bundle digests, control files, participation sha,
   assembler digest).
2. **Only two live markets seal today** (Dayton, Cleveland); the other eight are refused by the writer on legacy
   authority facts (003's report). A composed candidate from packages needs every participating market sealed —
   or a documented "live fragment as-is" input class for unsealable markets, keyed by the committed authority
   bytes (a data order per market is the honest fix).
3. **Participation is not in the bundle key** (correct: the bundle does not read it) but IS a release input:
   the coordinator must key the candidate on `launch_participation.json`'s sha, as the manifest already does.
4. **Two receipt kinds must be joined**: the package receipt (release safety, rules A–O, expires when the live
   deploy moves) and the bundle receipt (artifact identity, expires on evidence revocation/expiry). Authorization
   must bind package digest + bundle digest + both receipt digests + parent live digest.
5. **The live and rollback bundles are not in durable release storage** by digest today (only the deployed
   record's `bundle_sha256`); the cache is evictable and must never be the only copy. 005 needs
   `release_store/<bundle sha>` for the current live and the rollback target, populated from the deploy, not
   from the cache.
6. **The 003 package receipt's rule L re-derives the package with the CURRENT writer**; 004 found that an
   additive scorecard field broke re-derivation of a committed package and fixed the writer to keep a supplied
   scorecard byte-stable while checking its counts. Receipt validity across writer versions needs an explicit
   compatibility rule in 005 (as `COMPATIBLE_POLICIES` does for bundle receipts).
7. **Windows path length**: a staged build fails above ~120 characters of work-dir prefix. The coordinator must
   allocate short scratch roots.

## Measurements 005 should take first

- Compose time from N trusted bundles vs the 400 s full compose (002/003 numbers), with the 27 gates.
- Whether the global hotel index and home page can be built from the release index alone (no render).
- The size of `release_store` for live + rollback (two bundles ≈ 1393048 bytes each, compressed).
