# ATLAS-THROUGHPUT-002 — the demo-media suite's validation role

Suite: `tests/website_generation/integration/test_pettripfinder_demo_media.py`
(18 tests). Nothing in it was deleted, skipped, xfailed or commented out.

## What 001 measured

| run | suite seconds | share of the broad run |
|---|---|---|
| ten lane-runner broad runs (Sep 2–7) | 3,489–4,440 | 57–66 % |
| 001 instrumented baseline | 5,630 | 71 % |
| process working set while it runs | 6.4–7.6 GB (the PetTripFinder tree stays under 0.5 GB) | |

Twelve real-chain builds of the same committed launch package, one per test,
~280–1,280 s each. The committed baselines c854469 and f75aa95 DESELECTED
it; `regression_lanes run --lane full_regression` did not.

## What defect class it protects

It drives the REAL launch package (`launch_packages/pettripfinder/`:
`seed_businesses.csv`, `categories.json`, the market seed shards through
`market_authority`, `demo_media.json` and the two committed demo PNGs)
through the whole website-generation engine chain — load → media ingestion →
listing dataset → information architecture → component compile → layout →
render → SEO → assembly — and asserts:

- A. manifest/config validation (absolute paths, traversal, missing fields, missing files refused);
- B. real pilot ingestion (HERO_IMAGE refs on exactly the configured listings, content-addressed hashes equal to the committed bytes, no filesystem path leaks into the dataset);
- C. generated HTML (card + profile `<img>` for imaged listings, none for image-less ones, the sitewide `<img>` count formula);
- D. bundle (two content-addressed assets, no duplicated bytes, materialisation);
- E. request safety (every `img src` is a bundled local asset, never remote / protocol-relative / data:);
- F. determinism (two cold builds identical);
- G. zero-image fallback (no manifest → zero `<img>`, generation succeeds).

These are contracts between the website-generation engines and the shared
launch package. They can be broken by a change to `engines/website_generation/**`,
`repositories/{artifact_store,site_bundle}_repository.py`,
`scripts/generate_pettripfinder_pilot.py`, `scripts/pettripfinder/{listing_dataset_builder,media_ingestion,publication_guard,market_authority}.py`,
or to the shared launch-package inputs. They CANNOT be broken by a
market-local helper: the isolation proof forbids a helper from writing
anywhere but its own proposed / report roots, and none of those files is
read by this chain.

## Its lane now

- Lane: `website_generation_integration` (`regression_lanes.WEBSITE_GENERATION_INTEGRATION_MODULES`,
  the eight `tests/website_generation/integration/` modules), marked at
  collection by `conftest.py`, selectable with `-m website_generation_integration`,
  runnable with `python scripts/pettripfinder/regression_lanes.py run --lane website_generation_integration --out <dir>`.
- Role: BROAD AUDIT. It remains inside `full_regression`, so every mandatory-full
  class (AUTHORITY, GENERIC_RUNTIME, SCHEMA, ROUTING_SEMANTIC, DEPLOYMENT,
  UNCLASSIFIED) still runs it — including every change to the engines, the
  assembler, the renderer and the shared launch-package inputs listed above
  (all of which classify GENERIC_RUNTIME_CHANGE / AUTHORITY_CHANGE).
- Not selected by a MARKET_LOCAL_TOOLING plan: that plan owes the zone's own
  tests, the per-market contract rows and reverse dependents, never a lane and
  never `tests`. Proved by `test_atlas_throughput_002.py::TestDemoMediaLane`.
- A market-local run is reported as exactly that (the plan's module list and
  the `regression_delta validate` document); it is never called a full
  regression.

## Repeated real-chain work inside the suite

Nine tests whose claim is about the RESULT of one with-media chain now read
one module-scoped fixture (`with_media_chain`); `TestDeterminism` still builds
twice, cold, because its claim IS two cold executions; `TestZeroImageFallback`
still builds its own no-media chain. Twelve builds → four. The cold-execution
claim and the consumer-reuse claim are separated in the source, not by a
memo the tests cannot see.
