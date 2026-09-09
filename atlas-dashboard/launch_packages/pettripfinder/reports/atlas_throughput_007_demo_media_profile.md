# ATLAS-THROUGHPUT-007 — demo-media profile

Measured, not inferred from a pytest percentage.

## Before (006 audit)

One module, 18 tests, **1349.7 s**, five full real-chain builds at about 269.9 s each.

| test | setup s | call s | total s |
|---|---|---|---|
| TestDeterminism::test_repeated_real_build_identical | 0.0 | 530.8 | 530.8 |
| TestRealPilotIngestion::test_configured_listings_gain_hero | 280.9 | 0.0 | 280.9 |
| TestRealPilotIngestion::test_no_filesystem_path_in_dataset | 0.1 | 262.0 | 262.1 |
| TestZeroImageFallback::test_no_media_mapping_yields_zero_i | 0.1 | 256.3 | 257.2 |
| TestBundle::test_two_content_addressed_assets_materialized | 0.1 | 17.8 | 17.9 |
| TestGeneratedHtml::test_img_tags_sitewide_are_exactly_the_ | 0.0 | 0.4 | 0.4 |

Five builds: the module fixture, a second identical chain for the dataset-path claim, two for determinism, and
one for the no-media fallback.

## After (dedicated profiled run)

| module | seconds | tests | peak MB |
|---|---|---|---|
| test_pettripfinder_demo_media_determinism.py | 558.2 | 2 | 7863 |
| test_pettripfinder_demo_media.py | 315.2 | 16 | 7034 |
| test_pettripfinder_demo_media_fallback.py | 260.1 | 2 | 7863 |

| test | setup s | call s | total s |
|---|---|---|---|
| TestDeterminism::test_repeated_real_build_identical | 557.7 | 0.4 | 558.2 |
| TestRealPilotIngestion::test_configured_listings_gain_hero | 296.0 | 0.0 | 296.0 |
| TestZeroImageFallback::test_no_media_mapping_yields_zero_i | 259.6 | 0.2 | 259.8 |
| TestBundle::test_two_content_addressed_assets_materialized | 0.0 | 18.2 | 18.2 |
| TestGeneratedHtml::test_img_tags_sitewide_are_exactly_the_ | 0.0 | 0.3 | 0.3 |
| TestRequestSafety::test_every_img_src_is_bundled_local | 0.0 | 0.3 | 0.3 |

## The floor

The determinism claim needs two genuinely independent executions, so **558.2 s** is irreducible at module
granularity. Neither execution may be memoised: comparing a build against itself proves nothing.
