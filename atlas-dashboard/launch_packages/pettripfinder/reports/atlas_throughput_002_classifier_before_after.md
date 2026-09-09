# ATLAS-THROUGHPUT-002 — Regression V2 classifier BEFORE / AFTER on the real market branches

BEFORE = `regression_delta.py` at 0a623a0 (PTF-FACTORY-REGRESSION-V2-001 rules, byte for byte from git). AFTER = this order's classifier with the market-local ownership registry and the five-condition isolation proof. Both classify the same `git diff base..head`; nothing was checked out.

| branch | base..head | paths | OLD classes | OLD full | OLD drivers | NEW classes | NEW full | NEW drivers | MARKET_LOCAL paths | narrowing blockers |
|---|---|---|---|---|---|---|---|---|---|---|
| nashville-new-market-001 | d335c50..4f3dd7b | 45 | AUTHORITY_CHANGE, GENERIC_RUNTIME_CHANGE, ROUTING_SEMANTIC_CHANGE, TEST_EXPECTATION_CHANGE, DOCUMENTATION_ONLY, GENERATED_REPORT_ONLY, UNCLASSIFIED | YES | 21 | TEST_EXPECTATION_CHANGE, DOCUMENTATION_ONLY, GENERATED_REPORT_ONLY, MARKET_LOCAL_TOOLING, UNCLASSIFIED | YES | 1 | 20 | none |
| chattanooga-new-market-001 | d335c50..4e058a3 | 28 | AUTHORITY_CHANGE, GENERIC_RUNTIME_CHANGE, ROUTING_SEMANTIC_CHANGE, BOOKKEEPING_REGISTRATION_CHANGE, GENERATED_REPORT_ONLY, UNCLASSIFIED | YES | 12 | GENERIC_RUNTIME_CHANGE, ROUTING_SEMANTIC_CHANGE, BOOKKEEPING_REGISTRATION_CHANGE, GENERATED_REPORT_ONLY, MARKET_LOCAL_TOOLING | YES | 1 | 11 | none |
| lexington-new-market-001+002 | 2163c4e..f1e0435 | 36 | GENERIC_RUNTIME_CHANGE, SCHEMA_CHANGE, ROUTING_SEMANTIC_CHANGE, GENERATED_REPORT_ONLY | YES | 17 | GENERIC_RUNTIME_CHANGE, ROUTING_SEMANTIC_CHANGE, GENERATED_REPORT_ONLY, MARKET_LOCAL_TOOLING | YES | 1 | 16 | none |
| toledo-new-market-001 | 2163c4e..133b937 | 37 | AUTHORITY_CHANGE, GENERIC_RUNTIME_CHANGE, ROUTING_SEMANTIC_CHANGE, TEST_EXPECTATION_CHANGE, DOCUMENTATION_ONLY, GENERATED_REPORT_ONLY, UNCLASSIFIED | YES | 18 | TEST_EXPECTATION_CHANGE, DOCUMENTATION_ONLY, GENERATED_REPORT_ONLY, MARKET_LOCAL_TOOLING, UNCLASSIFIED | YES | 2 | 16 | none |
| toledo-promotion-002-and-launch-003 | 2163c4e..d335c50 | 82 | AUTHORITY_CHANGE, GENERIC_RUNTIME_CHANGE, ROUTING_SEMANTIC_CHANGE, DEPLOYMENT_CHANGE, TEST_EXPECTATION_CHANGE, DOCUMENTATION_ONLY, GENERATED_REPORT_ONLY, UNCLASSIFIED | YES | 46 | AUTHORITY_CHANGE, GENERIC_RUNTIME_CHANGE, ROUTING_SEMANTIC_CHANGE, DEPLOYMENT_CHANGE, TEST_EXPECTATION_CHANGE, DOCUMENTATION_ONLY, GENERATED_REPORT_ONLY, UNCLASSIFIED | YES | 46 | 0 | scripts/pettripfinder/regression_lanes.py, tests/pettripfinder/pins/deployment_state.json, tests/pettripfinder/pins/market_state.json, tests/pettripfinder/pins/supersessions.json |

## nashville-new-market-001 (d335c50..4f3dd7b)

Remaining full-regression drivers AFTER: `launch_packages/pettripfinder/nashville_tn_osm_extracts_001.json`

Selected suites AFTER (133 modules): the six lanes + owning modules (a mandatory-full class is present)

| path | status | OLD class | NEW class | why / proof |
|---|---|---|---|---|
| `launch_packages/pettripfinder/identity_census_proposed/nashville-tn.json` | A | AUTHORITY_CHANGE/ROUTING_SEMANTIC_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone nashville-tn on all five conditions) |
| `launch_packages/pettripfinder/markets/proposed/nashville-tn.json` | A | UNCLASSIFIED | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone nashville-tn on all five conditions) |
| `launch_packages/pettripfinder/nashville_tn_osm_extracts_001.json` | A | UNCLASSIFIED | UNCLASSIFIED | proof FAILED on reachability (matched no rule; market-local proof FAILED on reachability: directory launch_packages/pettripfinder is enumerated by shared code: tests/pettripfinder/test_build) |
| `scripts/pettripfinder/discovery/config/nashville_tn.json` | A | GENERIC_RUNTIME_CHANGE/ROUTING_SEMANTIC_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone nashville-tn on all five conditions) |
| `scripts/pettripfinder/nashville_tn_attended_capture_001.py` | A | GENERIC_RUNTIME_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone nashville-tn on all five conditions) |
| `scripts/pettripfinder/nashville_tn_brand_city_pages_001.py` | A | GENERIC_RUNTIME_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone nashville-tn on all five conditions) |
| `scripts/pettripfinder/nashville_tn_brand_sitemaps_001.py` | A | GENERIC_RUNTIME_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone nashville-tn on all five conditions) |
| `scripts/pettripfinder/nashville_tn_census_reconciliation_001.py` | A | GENERIC_RUNTIME_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone nashville-tn on all five conditions) |
| `scripts/pettripfinder/nashville_tn_corridor_explicit_002.py` | A | GENERIC_RUNTIME_CHANGE/ROUTING_SEMANTIC_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone nashville-tn on all five conditions) |
| `scripts/pettripfinder/nashville_tn_firecrawl_pass_001.py` | A | GENERIC_RUNTIME_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone nashville-tn on all five conditions) |
| `scripts/pettripfinder/nashville_tn_free_static_capture_001.py` | A | GENERIC_RUNTIME_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone nashville-tn on all five conditions) |
| `scripts/pettripfinder/nashville_tn_geography_001.py` | A | GENERIC_RUNTIME_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone nashville-tn on all five conditions) |
| `scripts/pettripfinder/nashville_tn_ladder_plan_001.py` | A | GENERIC_RUNTIME_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone nashville-tn on all five conditions) |
| `scripts/pettripfinder/nashville_tn_lead_sources_001.py` | A | GENERIC_RUNTIME_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone nashville-tn on all five conditions) |
| `scripts/pettripfinder/nashville_tn_owned_evidence_001.py` | A | GENERIC_RUNTIME_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone nashville-tn on all five conditions) |
| `scripts/pettripfinder/nashville_tn_parallel_safety_001.py` | A | GENERIC_RUNTIME_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone nashville-tn on all five conditions) |
| `scripts/pettripfinder/nashville_tn_regression_classification_001.py` | A | GENERIC_RUNTIME_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone nashville-tn on all five conditions) |
| `scripts/pettripfinder/nashville_tn_routing_001.py` | A | GENERIC_RUNTIME_CHANGE/ROUTING_SEMANTIC_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone nashville-tn on all five conditions) |
| `scripts/pettripfinder/nashville_tn_shadow_market_001.py` | A | GENERIC_RUNTIME_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone nashville-tn on all five conditions) |
| `scripts/pettripfinder/nashville_tn_speed_benchmark_004.py` | A | GENERIC_RUNTIME_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone nashville-tn on all five conditions) |
| `scripts/pettripfinder/nashville_tn_test_inventory_repin_003.py` | A | GENERIC_RUNTIME_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone nashville-tn on all five conditions) |
| `tests/pettripfinder/test_nashville_tn_new_market_001.py` | A | TEST_EXPECTATION_CHANGE | TEST_EXPECTATION_CHANGE | added or deleted module: there is no prior shape to compare against |

## chattanooga-new-market-001 (d335c50..4e058a3)

Remaining full-regression drivers AFTER: `scripts/pettripfinder/discovery/config/osm_extracts.json`

Selected suites AFTER (124 modules): the six lanes + owning modules (a mandatory-full class is present)

| path | status | OLD class | NEW class | why / proof |
|---|---|---|---|---|
| `launch_packages/pettripfinder/identity_census_proposed/chattanooga-tn.json` | A | AUTHORITY_CHANGE/ROUTING_SEMANTIC_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone chattanooga-tn on all five conditions) |
| `launch_packages/pettripfinder/markets/proposed/chattanooga-tn.json` | A | UNCLASSIFIED | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone chattanooga-tn on all five conditions) |
| `scripts/pettripfinder/chattanooga_tn_attended_capture_001.py` | A | GENERIC_RUNTIME_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone chattanooga-tn on all five conditions) |
| `scripts/pettripfinder/chattanooga_tn_census_reconciliation_001.py` | A | GENERIC_RUNTIME_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone chattanooga-tn on all five conditions) |
| `scripts/pettripfinder/chattanooga_tn_competitor_gap_001.py` | A | GENERIC_RUNTIME_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone chattanooga-tn on all five conditions) |
| `scripts/pettripfinder/chattanooga_tn_firecrawl_pass_001.py` | A | GENERIC_RUNTIME_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone chattanooga-tn on all five conditions) |
| `scripts/pettripfinder/chattanooga_tn_free_static_capture_001.py` | A | GENERIC_RUNTIME_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone chattanooga-tn on all five conditions) |
| `scripts/pettripfinder/chattanooga_tn_lead_sources_001.py` | A | GENERIC_RUNTIME_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone chattanooga-tn on all five conditions) |
| `scripts/pettripfinder/chattanooga_tn_routing_001.py` | A | GENERIC_RUNTIME_CHANGE/ROUTING_SEMANTIC_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone chattanooga-tn on all five conditions) |
| `scripts/pettripfinder/chattanooga_tn_shadow_market_001.py` | A | GENERIC_RUNTIME_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone chattanooga-tn on all five conditions) |
| `scripts/pettripfinder/discovery/config/chattanooga_tn.json` | A | GENERIC_RUNTIME_CHANGE/ROUTING_SEMANTIC_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone chattanooga-tn on all five conditions) |
| `scripts/pettripfinder/discovery/config/osm_extracts.json` | M | GENERIC_RUNTIME_CHANGE/ROUTING_SEMANTIC_CHANGE | GENERIC_RUNTIME_CHANGE/ROUTING_SEMANTIC_CHANGE | proof FAILED on namespace, imports, writes, reachability, registration (matched prefix:scripts/pettripfinder/discovery/; not market-local: inside the never_local fence) |
| `tests/pettripfinder/acquisition/test_store_integration_025.py` | M | BOOKKEEPING_REGISTRATION_CHANGE | BOOKKEEPING_REGISTRATION_CHANGE | only the elements of declared registration container(s) OTHER_MARKET_RUNS changed; no def, class, import or other module-level statement differs |

## lexington-new-market-001+002 (2163c4e..f1e0435)

Remaining full-regression drivers AFTER: `scripts/pettripfinder/discovery/config/osm_extracts.json`

Selected suites AFTER (134 modules): the six lanes + owning modules (a mandatory-full class is present)

| path | status | OLD class | NEW class | why / proof |
|---|---|---|---|---|
| `scripts/pettripfinder/discovery/config/lexington_ky.json` | A | GENERIC_RUNTIME_CHANGE/ROUTING_SEMANTIC_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone lexington-ky on all five conditions) |
| `scripts/pettripfinder/discovery/config/osm_extracts.json` | M | GENERIC_RUNTIME_CHANGE/ROUTING_SEMANTIC_CHANGE | GENERIC_RUNTIME_CHANGE/ROUTING_SEMANTIC_CHANGE | proof FAILED on namespace, imports, writes, reachability, registration (matched prefix:scripts/pettripfinder/discovery/; not market-local: inside the never_local fence) |
| `scripts/pettripfinder/lexington_ky_attended_policy_pass_002.py` | A | GENERIC_RUNTIME_CHANGE/SCHEMA_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone lexington-ky on all five conditions) |
| `scripts/pettripfinder/lexington_ky_brand_city_page_lane_001.py` | A | GENERIC_RUNTIME_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone lexington-ky on all five conditions) |
| `scripts/pettripfinder/lexington_ky_brand_directory_harvest_001.py` | A | GENERIC_RUNTIME_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone lexington-ky on all five conditions) |
| `scripts/pettripfinder/lexington_ky_brand_directory_harvest_002.py` | A | GENERIC_RUNTIME_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone lexington-ky on all five conditions) |
| `scripts/pettripfinder/lexington_ky_census_reconciliation_001.py` | A | GENERIC_RUNTIME_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone lexington-ky on all five conditions) |
| `scripts/pettripfinder/lexington_ky_clean_inventory_002.py` | A | GENERIC_RUNTIME_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone lexington-ky on all five conditions) |
| `scripts/pettripfinder/lexington_ky_competitor_census_challenge_001.py` | A | GENERIC_RUNTIME_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone lexington-ky on all five conditions) |
| `scripts/pettripfinder/lexington_ky_county_boundary_001.py` | A | GENERIC_RUNTIME_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone lexington-ky on all five conditions) |
| `scripts/pettripfinder/lexington_ky_firecrawl_pass_002.py` | A | GENERIC_RUNTIME_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone lexington-ky on all five conditions) |
| `scripts/pettripfinder/lexington_ky_founder_and_readiness_002.py` | A | GENERIC_RUNTIME_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone lexington-ky on all five conditions) |
| `scripts/pettripfinder/lexington_ky_free_census_001.py` | A | GENERIC_RUNTIME_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone lexington-ky on all five conditions) |
| `scripts/pettripfinder/lexington_ky_identity_key_repair_002.py` | A | GENERIC_RUNTIME_CHANGE/ROUTING_SEMANTIC_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone lexington-ky on all five conditions) |
| `scripts/pettripfinder/lexington_ky_paid_readiness_001.py` | A | GENERIC_RUNTIME_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone lexington-ky on all five conditions) |
| `scripts/pettripfinder/lexington_ky_routing_and_static_capture_001.py` | A | GENERIC_RUNTIME_CHANGE/ROUTING_SEMANTIC_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone lexington-ky on all five conditions) |
| `scripts/pettripfinder/lexington_ky_shadow_market_and_founder_packet_001.py` | A | GENERIC_RUNTIME_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone lexington-ky on all five conditions) |

## toledo-new-market-001 (2163c4e..133b937)

Remaining full-regression drivers AFTER: `launch_packages/pettripfinder/toledo_oh_founder_rulings_001.json`, `launch_packages/pettripfinder/toledo_oh_osm_extracts_001.json`

Selected suites AFTER (132 modules): the six lanes + owning modules (a mandatory-full class is present)

| path | status | OLD class | NEW class | why / proof |
|---|---|---|---|---|
| `launch_packages/pettripfinder/identity_census_proposed/toledo-oh.json` | A | AUTHORITY_CHANGE/ROUTING_SEMANTIC_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone toledo-oh on all five conditions) |
| `launch_packages/pettripfinder/markets/proposed/toledo-oh.json` | A | UNCLASSIFIED | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone toledo-oh on all five conditions) |
| `launch_packages/pettripfinder/toledo_oh_founder_rulings_001.json` | A | UNCLASSIFIED | UNCLASSIFIED | proof FAILED on reachability (matched no rule; market-local proof FAILED on reachability: directory launch_packages/pettripfinder is enumerated by shared code: tests/pettripfinder/test_build) |
| `launch_packages/pettripfinder/toledo_oh_osm_extracts_001.json` | A | UNCLASSIFIED | UNCLASSIFIED | proof FAILED on reachability (matched no rule; market-local proof FAILED on reachability: directory launch_packages/pettripfinder is enumerated by shared code: tests/pettripfinder/test_build) |
| `scripts/pettripfinder/discovery/config/toledo_oh.json` | A | GENERIC_RUNTIME_CHANGE/ROUTING_SEMANTIC_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone toledo-oh on all five conditions) |
| `scripts/pettripfinder/toledo_oh_attended_capture_001.py` | A | GENERIC_RUNTIME_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone toledo-oh on all five conditions) |
| `scripts/pettripfinder/toledo_oh_brand_city_pages_001.py` | A | GENERIC_RUNTIME_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone toledo-oh on all five conditions) |
| `scripts/pettripfinder/toledo_oh_brand_inventory_001.py` | A | GENERIC_RUNTIME_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone toledo-oh on all five conditions) |
| `scripts/pettripfinder/toledo_oh_census_reconciliation_001.py` | A | GENERIC_RUNTIME_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone toledo-oh on all five conditions) |
| `scripts/pettripfinder/toledo_oh_firecrawl_pass_001.py` | A | GENERIC_RUNTIME_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone toledo-oh on all five conditions) |
| `scripts/pettripfinder/toledo_oh_free_static_capture_001.py` | A | GENERIC_RUNTIME_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone toledo-oh on all five conditions) |
| `scripts/pettripfinder/toledo_oh_ladder_plan_001.py` | A | GENERIC_RUNTIME_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone toledo-oh on all five conditions) |
| `scripts/pettripfinder/toledo_oh_lead_sources_001.py` | A | GENERIC_RUNTIME_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone toledo-oh on all five conditions) |
| `scripts/pettripfinder/toledo_oh_owned_evidence_001.py` | A | GENERIC_RUNTIME_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone toledo-oh on all five conditions) |
| `scripts/pettripfinder/toledo_oh_parallel_safety_001.py` | A | GENERIC_RUNTIME_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone toledo-oh on all five conditions) |
| `scripts/pettripfinder/toledo_oh_regression_classification_001.py` | A | GENERIC_RUNTIME_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone toledo-oh on all five conditions) |
| `scripts/pettripfinder/toledo_oh_routing_001.py` | A | GENERIC_RUNTIME_CHANGE/ROUTING_SEMANTIC_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone toledo-oh on all five conditions) |
| `scripts/pettripfinder/toledo_oh_shadow_market_001.py` | A | GENERIC_RUNTIME_CHANGE | MARKET_LOCAL_TOOLING | proof PASSED (isolation proof passed for zone toledo-oh on all five conditions) |
| `tests/pettripfinder/test_toledo_oh_new_market_001.py` | A | TEST_EXPECTATION_CHANGE | TEST_EXPECTATION_CHANGE | added or deleted module: there is no prior shape to compare against |

## toledo-promotion-002-and-launch-003 (2163c4e..d335c50)

Remaining full-regression drivers AFTER: `deploy/netlify/deployment_authorizations/ptf-auth-toledo-003-895248738c79.json`, `deploy/netlify/deployment_records/ptf-deploy-toledo-003-6a9e047690ec8bdaf99bcad2.json`, `deploy/netlify/global_deployment_manifest.json`, `deploy/netlify/launch_participation.json`, `deploy/netlify/release_contracts/toledo-oh.json`, `launch_packages/pettripfinder/hotel_exclusions.json`, `launch_packages/pettripfinder/hotel_policy_facts_toledo-oh.json`, `launch_packages/pettripfinder/identity_census/toledo-oh.json` …

Selected suites AFTER (226 modules): the six lanes + owning modules (a mandatory-full class is present)

| path | status | OLD class | NEW class | why / proof |
|---|---|---|---|---|
| `deploy/netlify/deployment_authorizations/ptf-auth-toledo-003-895248738c79.json` | A | DEPLOYMENT_CHANGE | DEPLOYMENT_CHANGE | matched prefix:deploy/ |
| `deploy/netlify/deployment_records/ptf-deploy-toledo-003-6a9e047690ec8bdaf99bcad2.json` | A | DEPLOYMENT_CHANGE | DEPLOYMENT_CHANGE | matched prefix:deploy/ |
| `deploy/netlify/global_deployment_manifest.json` | M | DEPLOYMENT_CHANGE | DEPLOYMENT_CHANGE | matched prefix:deploy/ |
| `deploy/netlify/launch_participation.json` | M | DEPLOYMENT_CHANGE | DEPLOYMENT_CHANGE | matched prefix:deploy/ |
| `deploy/netlify/release_contracts/toledo-oh.json` | A | DEPLOYMENT_CHANGE | DEPLOYMENT_CHANGE | matched prefix:deploy/ |
| `launch_packages/pettripfinder/hotel_exclusions.json` | M | AUTHORITY_CHANGE | AUTHORITY_CHANGE | matched glob:launch_packages/pettripfinder/hotel_exclusions*.json |
| `launch_packages/pettripfinder/hotel_policy_facts_toledo-oh.json` | A | AUTHORITY_CHANGE | AUTHORITY_CHANGE | matched glob:launch_packages/pettripfinder/hotel_policy_facts*.json |
| `launch_packages/pettripfinder/identity_census/toledo-oh.json` | A | AUTHORITY_CHANGE/ROUTING_SEMANTIC_CHANGE | AUTHORITY_CHANGE/ROUTING_SEMANTIC_CHANGE | matched prefix:launch_packages/pettripfinder/identity_census |
| `launch_packages/pettripfinder/markets/authority/toledo-oh/affiliate_destinations.json` | A | AUTHORITY_CHANGE | AUTHORITY_CHANGE | matched prefix:launch_packages/pettripfinder/markets/authority/ |
| `launch_packages/pettripfinder/markets/authority/toledo-oh/hotel_exclusions.json` | A | AUTHORITY_CHANGE | AUTHORITY_CHANGE | matched prefix:launch_packages/pettripfinder/markets/authority/ |
| `launch_packages/pettripfinder/markets/authority/toledo-oh/identity_routing.json` | A | AUTHORITY_CHANGE | AUTHORITY_CHANGE | matched prefix:launch_packages/pettripfinder/markets/authority/ |
| `launch_packages/pettripfinder/markets/authority/toledo-oh/seed_businesses.csv` | A | AUTHORITY_CHANGE | AUTHORITY_CHANGE | matched prefix:launch_packages/pettripfinder/markets/authority/ |
| `launch_packages/pettripfinder/markets/toledo-oh.json` | A | AUTHORITY_CHANGE | AUTHORITY_CHANGE | matched glob:launch_packages/pettripfinder/markets/*.json |
| `launch_packages/pettripfinder/ptf_global_authority_manifest.json` | M | AUTHORITY_CHANGE | AUTHORITY_CHANGE | matched glob:launch_packages/pettripfinder/ptf_global_authority_manifest.json |
| `launch_packages/pettripfinder/seed_businesses.csv` | M | AUTHORITY_CHANGE | AUTHORITY_CHANGE | matched glob:launch_packages/pettripfinder/*seed_businesses*.csv |
| `launch_packages/pettripfinder/toledo_oh_final_partition_001.json` | A | AUTHORITY_CHANGE/ROUTING_SEMANTIC_CHANGE | AUTHORITY_CHANGE/ROUTING_SEMANTIC_CHANGE | matched glob:launch_packages/pettripfinder/*_final_partition_*.json |
| `launch_packages/pettripfinder/toledo_oh_founder_rulings_001.json` | A | UNCLASSIFIED | UNCLASSIFIED | matched no rule; market-local narrowing blocked: the change set touches scripts/pettripfinder/regression_lanes.py, tests/pettripfinder/pins/deployment_state.json, tests/pettripfinder/pins/market_state.json |
| `launch_packages/pettripfinder/toledo_oh_identity_holds_002.json` | A | UNCLASSIFIED | UNCLASSIFIED | matched no rule; market-local narrowing blocked: the change set touches scripts/pettripfinder/regression_lanes.py, tests/pettripfinder/pins/deployment_state.json, tests/pettripfinder/pins/market_state.json |
| `launch_packages/pettripfinder/toledo_oh_osm_extracts_001.json` | A | UNCLASSIFIED | UNCLASSIFIED | matched no rule; market-local narrowing blocked: the change set touches scripts/pettripfinder/regression_lanes.py, tests/pettripfinder/pins/deployment_state.json, tests/pettripfinder/pins/market_state.json |
| `launch_packages/pettripfinder/toledo_oh_promotion_halt_002.json` | A | UNCLASSIFIED | UNCLASSIFIED | matched no rule; market-local narrowing blocked: the change set touches scripts/pettripfinder/regression_lanes.py, tests/pettripfinder/pins/deployment_state.json, tests/pettripfinder/pins/market_state.json |
| `scripts/pettripfinder/assemble_production_site.py` | M | GENERIC_RUNTIME_CHANGE/DEPLOYMENT_CHANGE | GENERIC_RUNTIME_CHANGE/DEPLOYMENT_CHANGE | matched glob:scripts/pettripfinder/assemble_*.py |
| `scripts/pettripfinder/discovery/config/toledo_oh.json` | A | GENERIC_RUNTIME_CHANGE/ROUTING_SEMANTIC_CHANGE | GENERIC_RUNTIME_CHANGE/ROUTING_SEMANTIC_CHANGE | matched prefix:scripts/pettripfinder/discovery/; market-local narrowing blocked: the change set touches scripts/pettripfinder/regression_lanes.py, tests/pettripfinder/pins/deployment_state.json, tests/pettripfinder/pins/ |
| `scripts/pettripfinder/regression_lanes.py` | M | GENERIC_RUNTIME_CHANGE | GENERIC_RUNTIME_CHANGE | matched prefix:scripts/pettripfinder/; market-local narrowing blocked: the change set touches scripts/pettripfinder/regression_lanes.py, tests/pettripfinder/pins/deployment_state.json, tests/pettripfinder/pins/market_sta |
| `scripts/pettripfinder/toledo_oh_attended_capture_001.py` | A | GENERIC_RUNTIME_CHANGE | GENERIC_RUNTIME_CHANGE | matched prefix:scripts/pettripfinder/; market-local narrowing blocked: the change set touches scripts/pettripfinder/regression_lanes.py, tests/pettripfinder/pins/deployment_state.json, tests/pettripfinder/pins/market_sta |
| `scripts/pettripfinder/toledo_oh_brand_city_pages_001.py` | A | GENERIC_RUNTIME_CHANGE | GENERIC_RUNTIME_CHANGE | matched prefix:scripts/pettripfinder/; market-local narrowing blocked: the change set touches scripts/pettripfinder/regression_lanes.py, tests/pettripfinder/pins/deployment_state.json, tests/pettripfinder/pins/market_sta |
| `scripts/pettripfinder/toledo_oh_brand_inventory_001.py` | A | GENERIC_RUNTIME_CHANGE | GENERIC_RUNTIME_CHANGE | matched prefix:scripts/pettripfinder/; market-local narrowing blocked: the change set touches scripts/pettripfinder/regression_lanes.py, tests/pettripfinder/pins/deployment_state.json, tests/pettripfinder/pins/market_sta |
| `scripts/pettripfinder/toledo_oh_census_reconciliation_001.py` | A | GENERIC_RUNTIME_CHANGE | GENERIC_RUNTIME_CHANGE | matched prefix:scripts/pettripfinder/; market-local narrowing blocked: the change set touches scripts/pettripfinder/regression_lanes.py, tests/pettripfinder/pins/deployment_state.json, tests/pettripfinder/pins/market_sta |
| `scripts/pettripfinder/toledo_oh_deployment_packet_002.py` | A | GENERIC_RUNTIME_CHANGE/DEPLOYMENT_CHANGE | GENERIC_RUNTIME_CHANGE/DEPLOYMENT_CHANGE | matched glob:scripts/pettripfinder/*deploy*.py; market-local narrowing blocked: the change set touches scripts/pettripfinder/regression_lanes.py, tests/pettripfinder/pins/deployment_state.json, tests/pettripfinder/pins/m |
| `scripts/pettripfinder/toledo_oh_firecrawl_pass_001.py` | A | GENERIC_RUNTIME_CHANGE | GENERIC_RUNTIME_CHANGE | matched prefix:scripts/pettripfinder/; market-local narrowing blocked: the change set touches scripts/pettripfinder/regression_lanes.py, tests/pettripfinder/pins/deployment_state.json, tests/pettripfinder/pins/market_sta |
| `scripts/pettripfinder/toledo_oh_free_static_capture_001.py` | A | GENERIC_RUNTIME_CHANGE | GENERIC_RUNTIME_CHANGE | matched prefix:scripts/pettripfinder/; market-local narrowing blocked: the change set touches scripts/pettripfinder/regression_lanes.py, tests/pettripfinder/pins/deployment_state.json, tests/pettripfinder/pins/market_sta |
| `scripts/pettripfinder/toledo_oh_ladder_plan_001.py` | A | GENERIC_RUNTIME_CHANGE | GENERIC_RUNTIME_CHANGE | matched prefix:scripts/pettripfinder/; market-local narrowing blocked: the change set touches scripts/pettripfinder/regression_lanes.py, tests/pettripfinder/pins/deployment_state.json, tests/pettripfinder/pins/market_sta |
| `scripts/pettripfinder/toledo_oh_launch_authorization_003.py` | A | GENERIC_RUNTIME_CHANGE | GENERIC_RUNTIME_CHANGE | matched prefix:scripts/pettripfinder/; market-local narrowing blocked: the change set touches scripts/pettripfinder/regression_lanes.py, tests/pettripfinder/pins/deployment_state.json, tests/pettripfinder/pins/market_sta |
| `scripts/pettripfinder/toledo_oh_launch_participation_003.py` | A | GENERIC_RUNTIME_CHANGE | GENERIC_RUNTIME_CHANGE | matched prefix:scripts/pettripfinder/; market-local narrowing blocked: the change set touches scripts/pettripfinder/regression_lanes.py, tests/pettripfinder/pins/deployment_state.json, tests/pettripfinder/pins/market_sta |
| `scripts/pettripfinder/toledo_oh_lead_sources_001.py` | A | GENERIC_RUNTIME_CHANGE | GENERIC_RUNTIME_CHANGE | matched prefix:scripts/pettripfinder/; market-local narrowing blocked: the change set touches scripts/pettripfinder/regression_lanes.py, tests/pettripfinder/pins/deployment_state.json, tests/pettripfinder/pins/market_sta |
| `scripts/pettripfinder/toledo_oh_live_verification_003.py` | A | GENERIC_RUNTIME_CHANGE | GENERIC_RUNTIME_CHANGE | matched prefix:scripts/pettripfinder/; market-local narrowing blocked: the change set touches scripts/pettripfinder/regression_lanes.py, tests/pettripfinder/pins/deployment_state.json, tests/pettripfinder/pins/market_sta |
| `scripts/pettripfinder/toledo_oh_owned_evidence_001.py` | A | GENERIC_RUNTIME_CHANGE | GENERIC_RUNTIME_CHANGE | matched prefix:scripts/pettripfinder/; market-local narrowing blocked: the change set touches scripts/pettripfinder/regression_lanes.py, tests/pettripfinder/pins/deployment_state.json, tests/pettripfinder/pins/market_sta |
| `scripts/pettripfinder/toledo_oh_parallel_safety_001.py` | A | GENERIC_RUNTIME_CHANGE | GENERIC_RUNTIME_CHANGE | matched prefix:scripts/pettripfinder/; market-local narrowing blocked: the change set touches scripts/pettripfinder/regression_lanes.py, tests/pettripfinder/pins/deployment_state.json, tests/pettripfinder/pins/market_sta |
| `scripts/pettripfinder/toledo_oh_promotion_application_002.py` | A | GENERIC_RUNTIME_CHANGE | GENERIC_RUNTIME_CHANGE | matched prefix:scripts/pettripfinder/; market-local narrowing blocked: the change set touches scripts/pettripfinder/regression_lanes.py, tests/pettripfinder/pins/deployment_state.json, tests/pettripfinder/pins/market_sta |
| `scripts/pettripfinder/toledo_oh_regression_classification_001.py` | A | GENERIC_RUNTIME_CHANGE | GENERIC_RUNTIME_CHANGE | matched prefix:scripts/pettripfinder/; market-local narrowing blocked: the change set touches scripts/pettripfinder/regression_lanes.py, tests/pettripfinder/pins/deployment_state.json, tests/pettripfinder/pins/market_sta |
| `scripts/pettripfinder/toledo_oh_regression_classification_002.py` | A | GENERIC_RUNTIME_CHANGE | GENERIC_RUNTIME_CHANGE | matched prefix:scripts/pettripfinder/; market-local narrowing blocked: the change set touches scripts/pettripfinder/regression_lanes.py, tests/pettripfinder/pins/deployment_state.json, tests/pettripfinder/pins/market_sta |
| `scripts/pettripfinder/toledo_oh_release_contract_002.py` | A | GENERIC_RUNTIME_CHANGE | GENERIC_RUNTIME_CHANGE | matched prefix:scripts/pettripfinder/; market-local narrowing blocked: the change set touches scripts/pettripfinder/regression_lanes.py, tests/pettripfinder/pins/deployment_state.json, tests/pettripfinder/pins/market_sta |
| `scripts/pettripfinder/toledo_oh_routing_001.py` | A | GENERIC_RUNTIME_CHANGE/ROUTING_SEMANTIC_CHANGE | GENERIC_RUNTIME_CHANGE/ROUTING_SEMANTIC_CHANGE | matched glob:scripts/pettripfinder/*routing*.py; market-local narrowing blocked: the change set touches scripts/pettripfinder/regression_lanes.py, tests/pettripfinder/pins/deployment_state.json, tests/pettripfinder/pins/ |
| `scripts/pettripfinder/toledo_oh_shadow_market_001.py` | A | GENERIC_RUNTIME_CHANGE | GENERIC_RUNTIME_CHANGE | matched prefix:scripts/pettripfinder/; market-local narrowing blocked: the change set touches scripts/pettripfinder/regression_lanes.py, tests/pettripfinder/pins/deployment_state.json, tests/pettripfinder/pins/market_sta |
| `tests/pettripfinder/pins/deployment_state.json` | M | TEST_EXPECTATION_CHANGE | TEST_EXPECTATION_CHANGE | matched prefix:tests/ |
| `tests/pettripfinder/pins/market_state.json` | M | TEST_EXPECTATION_CHANGE | TEST_EXPECTATION_CHANGE | matched prefix:tests/ |
| `tests/pettripfinder/pins/supersessions.json` | M | TEST_EXPECTATION_CHANGE | TEST_EXPECTATION_CHANGE | matched prefix:tests/ |
| `tests/pettripfinder/test_global_assembler.py` | M | TEST_EXPECTATION_CHANGE | TEST_EXPECTATION_CHANGE | no registration container is declared for this module |
| `tests/pettripfinder/test_global_deployment_architecture_045.py` | M | TEST_EXPECTATION_CHANGE | TEST_EXPECTATION_CHANGE | no registration container is declared for this module |
| `tests/pettripfinder/test_grand_rapids_launch_participation_032.py` | M | TEST_EXPECTATION_CHANGE | TEST_EXPECTATION_CHANGE | no registration container is declared for this module |
| `tests/pettripfinder/test_launch_participation_046.py` | M | TEST_EXPECTATION_CHANGE | TEST_EXPECTATION_CHANGE | no registration container is declared for this module |
| `tests/pettripfinder/test_market_authority_sharding.py` | M | TEST_EXPECTATION_CHANGE | TEST_EXPECTATION_CHANGE | no registration container is declared for this module |
| `tests/pettripfinder/test_markets.py` | M | TEST_EXPECTATION_CHANGE | TEST_EXPECTATION_CHANGE | no registration container is declared for this module |
| `tests/pettripfinder/test_per_market_release_contracts.py` | M | TEST_EXPECTATION_CHANGE | TEST_EXPECTATION_CHANGE | no registration container is declared for this module |
| `tests/pettripfinder/test_st_louis_production_safety_001.py` | M | TEST_EXPECTATION_CHANGE | TEST_EXPECTATION_CHANGE | no registration container is declared for this module |
| `tests/pettripfinder/test_toledo_oh_launch_003.py` | A | TEST_EXPECTATION_CHANGE | TEST_EXPECTATION_CHANGE | added or deleted module: there is no prior shape to compare against |
| `tests/pettripfinder/test_toledo_oh_new_market_001.py` | A | TEST_EXPECTATION_CHANGE | TEST_EXPECTATION_CHANGE | added or deleted module: there is no prior shape to compare against |
| `tests/pettripfinder/test_toledo_oh_promotion_002.py` | A | TEST_EXPECTATION_CHANGE | TEST_EXPECTATION_CHANGE | added or deleted module: there is no prior shape to compare against |
| `tests/pettripfinder/test_two_market_compat.py` | M | TEST_EXPECTATION_CHANGE | TEST_EXPECTATION_CHANGE | no registration container is declared for this module |

