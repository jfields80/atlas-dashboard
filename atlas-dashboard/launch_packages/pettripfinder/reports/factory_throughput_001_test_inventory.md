# PetTripFinder test pin inventory (A1)

Schema `ptf-test-pin-inventory/1.0`. 390 modules scanned, 263 carry pins, 1554 sites.

| class | sites |
|---|---|
| CURRENT_STATE_INVARIANT | 160 |
| HISTORICAL_COHORT_INVARIANT | 828 |
| HISTORICAL_ARTIFACT_INVARIANT | 183 |
| DEPLOYMENT_EPOCH_INVARIANT | 126 |
| GENERIC_SCHEMA_INVARIANT | 194 |
| CROSS_MARKET_INVARIANT | 63 |

## Modules asserting whole-package counts

- `tests/pettripfinder/acquisition/test_authority_build_036.py`
- `tests/pettripfinder/acquisition/test_closure_038.py`
- `tests/pettripfinder/acquisition/test_closure_assessment_031.py`
- `tests/pettripfinder/acquisition/test_founder_decision_040.py`
- `tests/pettripfinder/acquisition/test_hilton_closure_023.py`
- `tests/pettripfinder/acquisition/test_hilton_decision_023.py`
- `tests/pettripfinder/acquisition/test_identity_binding_027.py`
- `tests/pettripfinder/acquisition/test_label_value_hardening_033.py`
- `tests/pettripfinder/acquisition/test_locator_recovery_032.py`
- `tests/pettripfinder/acquisition/test_marriott_decision_020.py`
- `tests/pettripfinder/acquisition/test_milwaukee_validation_016.py`
- `tests/pettripfinder/acquisition/test_normalization_041.py`
- `tests/pettripfinder/acquisition/test_premium_resolution_028.py`
- `tests/pettripfinder/acquisition/test_publication_042.py`
- `tests/pettripfinder/acquisition/test_reader_hardening_029.py`
- `tests/pettripfinder/acquisition/test_store_integration_025.py`
- `tests/pettripfinder/brightdata/test_brightdata_marriott_pilot_001.py`
- `tests/pettripfinder/contracts/test_market_authorities.py`
- `tests/pettripfinder/contracts/test_market_geography.py`
- `tests/pettripfinder/discovery/test_census_recandidacy.py`
- `tests/pettripfinder/discovery/test_google_places.py`
- `tests/pettripfinder/discovery/test_identity_dedup.py`
- `tests/pettripfinder/discovery/test_prior_build_reconciliation.py`
- `tests/pettripfinder/discovery/test_queue_seam.py`
- `tests/pettripfinder/discovery/test_resolution_fetch_plan.py`
- `tests/pettripfinder/policy/test_authority_safety.py`
- `tests/pettripfinder/policy/test_m10_code_and_address_override.py`
- `tests/pettripfinder/test_build_capture_queue.py`
- `tests/pettripfinder/test_cincinnati_founder_application_004.py`
- `tests/pettripfinder/test_cincinnati_free_lane_application_010.py`
- `tests/pettripfinder/test_cincinnati_hilton_close_marriott_retry_015.py`
- `tests/pettripfinder/test_cincinnati_independent_probe_009.py`
- `tests/pettripfinder/test_cincinnati_mainstay_census_split_013.py`
- `tests/pettripfinder/test_cincinnati_marriott_scale_batch_016.py`
- `tests/pettripfinder/test_cincinnati_species_key_rebind_011.py`
- `tests/pettripfinder/test_cincinnati_zero_cost_capture_003.py`
- `tests/pettripfinder/test_cleveland_attended_artifact_queue_001.py`
- `tests/pettripfinder/test_cleveland_capture_003.py`
- `tests/pettripfinder/test_cleveland_final_partition_002.py`
- `tests/pettripfinder/test_cleveland_hardened_application_005.py`
- `tests/pettripfinder/test_cleveland_hardened_policy_003.py`
- `tests/pettripfinder/test_cleveland_pass1_artifact_verification.py`
- `tests/pettripfinder/test_cleveland_pass3_capture_results.py`
- `tests/pettripfinder/test_cleveland_pass4_capture_results.py`
- `tests/pettripfinder/test_dayton_hardened_application_002.py`
- `tests/pettripfinder/test_dayton_pass_b_founder_decisions.py`
- `tests/pettripfinder/test_dayton_recovery_002.py`
- `tests/pettripfinder/test_dayton_work_browser_001.py`
- `tests/pettripfinder/test_detroit_ann_arbor_capture_pass2_001.py`
- `tests/pettripfinder/test_detroit_ann_arbor_capture_pass3_001.py`
- `tests/pettripfinder/test_fee_forms.py`
- `tests/pettripfinder/test_fee_tiers.py`
- `tests/pettripfinder/test_generate_columbus_site.py`
- `tests/pettripfinder/test_global_assembler.py`
- `tests/pettripfinder/test_grand_rapids_census_pin_024.py`
- `tests/pettripfinder/test_grand_rapids_cross_run_ledger_sync_018.py`
- `tests/pettripfinder/test_grand_rapids_founder_rulings_020.py`
- `tests/pettripfinder/test_grand_rapids_holland_market_001.py`
- `tests/pettripfinder/test_grand_rapids_review_prep_019.py`
- `tests/pettripfinder/test_grand_rapids_source_promotion_022.py`
- `tests/pettripfinder/test_identity_evidence.py`
- `tests/pettripfinder/test_identity_routing.py`
- `tests/pettripfinder/test_ihg_recertification_011.py`
- `tests/pettripfinder/test_indianapolis_backlog_cost_plan_015.py`
- `tests/pettripfinder/test_indianapolis_founder_review_013.py`
- `tests/pettripfinder/test_indianapolis_founder_rulings_013.py`
- `tests/pettripfinder/test_indianapolis_identity_address_cleanup_012.py`
- `tests/pettripfinder/test_indianapolis_identity_routing_repair_001.py`
- `tests/pettripfinder/test_indianapolis_pass1_capture.py`
- `tests/pettripfinder/test_indianapolis_pass2_capture.py`
- `tests/pettripfinder/test_indianapolis_recovery_005.py`
- `tests/pettripfinder/test_listing_renderability_boundary.py`
- `tests/pettripfinder/test_louisville_authority.py`
- `tests/pettripfinder/test_louisville_final_006.py`
- `tests/pettripfinder/test_market_ownership.py`
- `tests/pettripfinder/test_market_recensus_sandbox.py`
- `tests/pettripfinder/test_milwaukee_market_001.py`
- `tests/pettripfinder/test_policy_precision.py`
- `tests/pettripfinder/test_prod003_promotion_readpath.py`
- `tests/pettripfinder/test_prod005_netlify_config.py`
- `tests/pettripfinder/test_profile_fee_dimensions.py`
- `tests/pettripfinder/test_promotion_preserves_structured_facts.py`
- `tests/pettripfinder/test_publication_guard.py`
- `tests/pettripfinder/test_publication_schema_decisions_010.py`
- `tests/pettripfinder/test_renderer_real_records.py`
- `tests/pettripfinder/test_service_animal_reattestation_012.py`
- `tests/pettripfinder/test_sonesta_identity_and_scope.py`

## Per module

| module | market | default | sites | by class |
|---|---|---|---|---|
| `acquisition/test_acceptance_modifier_clause_p7.py` |  | HISTORICAL_ARTIFACT_INVARIANT | 1 | HISTORICAL_ARTIFACT 1 |
| `acquisition/test_acquisition_ladder.py` |  | HISTORICAL_ARTIFACT_INVARIANT | 1 | HISTORICAL_ARTIFACT 1 |
| `acquisition/test_acquisition_router.py` |  | HISTORICAL_ARTIFACT_INVARIANT | 2 | HISTORICAL_ARTIFACT 2 |
| `acquisition/test_approval_binding_039.py` |  | HISTORICAL_COHORT_INVARIANT | 3 | HISTORICAL_COHORT 3 |
| `acquisition/test_authority_build_036.py` |  | HISTORICAL_COHORT_INVARIANT | 24 | HISTORICAL_COHORT 24 |
| `acquisition/test_authorized_cohort.py` |  | HISTORICAL_ARTIFACT_INVARIANT | 8 | HISTORICAL_ARTIFACT 8 |
| `acquisition/test_choice_route_application_006.py` |  | HISTORICAL_COHORT_INVARIANT | 1 | HISTORICAL_COHORT 1 |
| `acquisition/test_choice_route_closure_005.py` |  | HISTORICAL_COHORT_INVARIANT | 3 | HISTORICAL_COHORT 3 |
| `acquisition/test_closure_038.py` |  | HISTORICAL_COHORT_INVARIANT | 5 | HISTORICAL_COHORT 5 |
| `acquisition/test_closure_assessment_031.py` |  | HISTORICAL_COHORT_INVARIANT | 3 | HISTORICAL_COHORT 3 |
| `acquisition/test_cohort_cost_plan.py` |  | HISTORICAL_ARTIFACT_INVARIANT | 2 | HISTORICAL_ARTIFACT 2 |
| `acquisition/test_double_buy_url_level_p4.py` |  | HISTORICAL_ARTIFACT_INVARIANT | 2 | HISTORICAL_ARTIFACT 2 |
| `acquisition/test_final_pass_026.py` |  | HISTORICAL_COHORT_INVARIANT | 9 | HISTORICAL_ARTIFACT 3, HISTORICAL_COHORT 6 |
| `acquisition/test_firecrawl_choice_validation_004.py` |  | HISTORICAL_COHORT_INVARIANT | 11 | HISTORICAL_COHORT 11 |
| `acquisition/test_founder_decision_040.py` |  | HISTORICAL_COHORT_INVARIANT | 24 | CROSS_MARKET 7, HISTORICAL_ARTIFACT 1, HISTORICAL_COHORT 16 |
| `acquisition/test_founder_review_036.py` |  | HISTORICAL_COHORT_INVARIANT | 10 | HISTORICAL_ARTIFACT 1, HISTORICAL_COHORT 9 |
| `acquisition/test_fresh_proof_019a.py` |  | HISTORICAL_COHORT_INVARIANT | 4 | HISTORICAL_ARTIFACT 2, HISTORICAL_COHORT 2 |
| `acquisition/test_generic_reader_024.py` |  | HISTORICAL_COHORT_INVARIANT | 2 | HISTORICAL_ARTIFACT 1, HISTORICAL_COHORT 1 |
| `acquisition/test_generic_reader_diagnostic_013.py` |  | HISTORICAL_COHORT_INVARIANT | 1 | HISTORICAL_COHORT 1 |
| `acquisition/test_hilton_closure_023.py` |  | HISTORICAL_COHORT_INVARIANT | 12 | HISTORICAL_ARTIFACT 3, HISTORICAL_COHORT 9 |
| `acquisition/test_hilton_decision_023.py` |  | HISTORICAL_COHORT_INVARIANT | 12 | HISTORICAL_ARTIFACT 6, HISTORICAL_COHORT 6 |
| `acquisition/test_identity_binding_027.py` |  | HISTORICAL_COHORT_INVARIANT | 3 | HISTORICAL_COHORT 3 |
| `acquisition/test_ihg_firecrawl_route_009.py` |  | HISTORICAL_COHORT_INVARIANT | 2 | HISTORICAL_COHORT 2 |
| `acquisition/test_independent_url_discovery_014.py` |  | HISTORICAL_COHORT_INVARIANT | 3 | HISTORICAL_COHORT 3 |
| `acquisition/test_label_value_hardening_033.py` |  | HISTORICAL_COHORT_INVARIANT | 14 | HISTORICAL_ARTIFACT 2, HISTORICAL_COHORT 12 |
| `acquisition/test_locator_recovery_032.py` |  | HISTORICAL_COHORT_INVARIANT | 8 | HISTORICAL_COHORT 8 |
| `acquisition/test_market_routing.py` |  | HISTORICAL_ARTIFACT_INVARIANT | 1 | HISTORICAL_ARTIFACT 1 |
| `acquisition/test_marriott_closure_022.py` |  | HISTORICAL_COHORT_INVARIANT | 6 | HISTORICAL_ARTIFACT 4, HISTORICAL_COHORT 2 |
| `acquisition/test_marriott_decision_020.py` |  | HISTORICAL_COHORT_INVARIANT | 14 | HISTORICAL_ARTIFACT 6, HISTORICAL_COHORT 8 |
| `acquisition/test_marriott_template_021.py` |  | HISTORICAL_COHORT_INVARIANT | 5 | CROSS_MARKET 1, HISTORICAL_ARTIFACT 3, HISTORICAL_COHORT 1 |
| `acquisition/test_milwaukee_acquisition_run_001.py` | milwaukee-wi | HISTORICAL_COHORT_INVARIANT | 3 | HISTORICAL_COHORT 3 |
| `acquisition/test_milwaukee_validation_016.py` | milwaukee-wi | HISTORICAL_COHORT_INVARIANT | 4 | HISTORICAL_ARTIFACT 3, HISTORICAL_COHORT 1 |
| `acquisition/test_motel6_firecrawl_decision_012.py` |  | HISTORICAL_COHORT_INVARIANT | 1 | HISTORICAL_COHORT 1 |
| `acquisition/test_normalization_041.py` |  | HISTORICAL_COHORT_INVARIANT | 21 | CROSS_MARKET 6, HISTORICAL_COHORT 15 |
| `acquisition/test_observation_rederivation_018.py` |  | HISTORICAL_COHORT_INVARIANT | 6 | HISTORICAL_ARTIFACT 2, HISTORICAL_COHORT 4 |
| `acquisition/test_paid_attempt_ledger.py` |  | HISTORICAL_ARTIFACT_INVARIANT | 1 | HISTORICAL_ARTIFACT 1 |
| `acquisition/test_parser_semantics_017.py` |  | HISTORICAL_COHORT_INVARIANT | 2 | HISTORICAL_COHORT 2 |
| `acquisition/test_premium_resolution_028.py` |  | HISTORICAL_COHORT_INVARIANT | 9 | HISTORICAL_ARTIFACT 3, HISTORICAL_COHORT 6 |
| `acquisition/test_publication_037.py` |  | HISTORICAL_COHORT_INVARIANT | 5 | DEPLOYMENT_EPOCH 2, HISTORICAL_COHORT 3 |
| `acquisition/test_publication_042.py` |  | HISTORICAL_COHORT_INVARIANT | 23 | CROSS_MARKET 6, DEPLOYMENT_EPOCH 1, HISTORICAL_COHORT 16 |
| `acquisition/test_reader_hardening_016.py` |  | HISTORICAL_COHORT_INVARIANT | 7 | CROSS_MARKET 1, HISTORICAL_COHORT 6 |
| `acquisition/test_reader_hardening_029.py` |  | HISTORICAL_COHORT_INVARIANT | 8 | HISTORICAL_ARTIFACT 1, HISTORICAL_COHORT 7 |
| `acquisition/test_reader_to_tiers_034.py` |  | HISTORICAL_COHORT_INVARIANT | 8 | HISTORICAL_ARTIFACT 1, HISTORICAL_COHORT 7 |
| `acquisition/test_recurring_and_parity_035.py` |  | HISTORICAL_COHORT_INVARIANT | 6 | HISTORICAL_COHORT 6 |
| `acquisition/test_source_discovery_015.py` |  | HISTORICAL_COHORT_INVARIANT | 5 | HISTORICAL_COHORT 5 |
| `acquisition/test_spider_benchmark_001.py` |  | HISTORICAL_COHORT_INVARIANT | 1 | HISTORICAL_COHORT 1 |
| `acquisition/test_store_integration_025.py` |  | HISTORICAL_COHORT_INVARIANT | 3 | HISTORICAL_COHORT 3 |
| `acquisition/test_store_reader_sync_030.py` |  | HISTORICAL_COHORT_INVARIANT | 9 | HISTORICAL_ARTIFACT 1, HISTORICAL_COHORT 8 |
| `acquisition/test_vocabulary_normalization_043.py` |  | HISTORICAL_COHORT_INVARIANT | 18 | CROSS_MARKET 6, DEPLOYMENT_EPOCH 3, HISTORICAL_COHORT 9 |
| `brightdata/test_brand_repair_003.py` |  | HISTORICAL_COHORT_INVARIANT | 2 | HISTORICAL_COHORT 2 |
| `brightdata/test_brightdata_cross_brand_pilot_002.py` |  | HISTORICAL_COHORT_INVARIANT | 3 | HISTORICAL_COHORT 3 |
| `brightdata/test_brightdata_marriott_pilot_001.py` |  | HISTORICAL_COHORT_INVARIANT | 5 | HISTORICAL_COHORT 5 |
| `brightdata/test_reader_remediation_005.py` |  | HISTORICAL_COHORT_INVARIANT | 6 | HISTORICAL_COHORT 6 |
| `contracts/test_census_partition.py` |  | GENERIC_SCHEMA_INVARIANT | 2 | GENERIC_SCHEMA 2 |
| `contracts/test_closure.py` |  | GENERIC_SCHEMA_INVARIANT | 4 | GENERIC_SCHEMA 4 |
| `contracts/test_compat_readers.py` |  | GENERIC_SCHEMA_INVARIANT | 1 | GENERIC_SCHEMA 1 |
| `contracts/test_market_authorities.py` |  | CURRENT_STATE_INVARIANT | 4 | CURRENT_STATE 4 |
| `contracts/test_market_geography.py` |  | GENERIC_SCHEMA_INVARIANT | 3 | CURRENT_STATE 3 |
| `contracts/test_service_animal.py` |  | GENERIC_SCHEMA_INVARIANT | 1 | GENERIC_SCHEMA 1 |
| `discovery/test_census_projection.py` |  | GENERIC_SCHEMA_INVARIANT | 1 | GENERIC_SCHEMA 1 |
| `discovery/test_census_recandidacy.py` |  | GENERIC_SCHEMA_INVARIANT | 6 | CURRENT_STATE 4, GENERIC_SCHEMA 2 |
| `discovery/test_census_url_recovery.py` |  | HISTORICAL_COHORT_INVARIANT | 1 | HISTORICAL_COHORT 1 |
| `discovery/test_deduplicate.py` |  | GENERIC_SCHEMA_INVARIANT | 8 | GENERIC_SCHEMA 8 |
| `discovery/test_google_places.py` |  | GENERIC_SCHEMA_INVARIANT | 2 | CURRENT_STATE 1, GENERIC_SCHEMA 1 |
| `discovery/test_identity_dedup.py` |  | GENERIC_SCHEMA_INVARIANT | 5 | CURRENT_STATE 2, GENERIC_SCHEMA 3 |
| `discovery/test_identity_observation.py` |  | GENERIC_SCHEMA_INVARIANT | 1 | GENERIC_SCHEMA 1 |
| `discovery/test_identity_resolution.py` |  | GENERIC_SCHEMA_INVARIANT | 1 | GENERIC_SCHEMA 1 |
| `discovery/test_import_batch_builder.py` |  | GENERIC_SCHEMA_INVARIANT | 3 | GENERIC_SCHEMA 3 |
| `discovery/test_import_plan.py` |  | GENERIC_SCHEMA_INVARIANT | 1 | GENERIC_SCHEMA 1 |
| `discovery/test_lodging_dedup.py` |  | GENERIC_SCHEMA_INVARIANT | 10 | GENERIC_SCHEMA 10 |
| `discovery/test_market_config.py` |  | GENERIC_SCHEMA_INVARIANT | 1 | GENERIC_SCHEMA 1 |
| `discovery/test_osm_extract_cli.py` |  | GENERIC_SCHEMA_INVARIANT | 5 | GENERIC_SCHEMA 5 |
| `discovery/test_overpass_endpoints.py` |  | GENERIC_SCHEMA_INVARIANT | 3 | GENERIC_SCHEMA 3 |
| `discovery/test_overpass_resilience.py` |  | GENERIC_SCHEMA_INVARIANT | 6 | GENERIC_SCHEMA 6 |
| `discovery/test_pittsburgh_overpass_replay.py` | pittsburgh-pa | HISTORICAL_COHORT_INVARIANT | 5 | HISTORICAL_COHORT 5 |
| `discovery/test_prior_build_reconciliation.py` |  | GENERIC_SCHEMA_INVARIANT | 1 | CURRENT_STATE 1 |
| `discovery/test_progress_gate.py` |  | GENERIC_SCHEMA_INVARIANT | 3 | GENERIC_SCHEMA 3 |
| `discovery/test_property_identity.py` |  | GENERIC_SCHEMA_INVARIANT | 1 | GENERIC_SCHEMA 1 |
| `discovery/test_query_plan.py` |  | GENERIC_SCHEMA_INVARIANT | 1 | GENERIC_SCHEMA 1 |
| `discovery/test_queue_seam.py` |  | GENERIC_SCHEMA_INVARIANT | 2 | CURRENT_STATE 1, GENERIC_SCHEMA 1 |
| `discovery/test_resolution_fetch_plan.py` |  | GENERIC_SCHEMA_INVARIANT | 6 | CURRENT_STATE 3, GENERIC_SCHEMA 3 |
| `discovery/test_resolution_runner.py` |  | GENERIC_SCHEMA_INVARIANT | 4 | GENERIC_SCHEMA 4 |
| `discovery/test_revalidate.py` |  | GENERIC_SCHEMA_INVARIANT | 1 | GENERIC_SCHEMA 1 |
| `discovery/test_source_families.py` |  | GENERIC_SCHEMA_INVARIANT | 1 | GENERIC_SCHEMA 1 |
| `importer/test_aggregate_approval_promotion.py` |  | GENERIC_SCHEMA_INVARIANT | 3 | GENERIC_SCHEMA 3 |
| `importer/test_aggregate_merge.py` |  | GENERIC_SCHEMA_INVARIANT | 1 | GENERIC_SCHEMA 1 |
| `importer/test_aggregate_name_reconciliation_002d.py` |  | HISTORICAL_COHORT_INVARIANT | 1 | HISTORICAL_COHORT 1 |
| `importer/test_aggregate_recommendation.py` |  | GENERIC_SCHEMA_INVARIANT | 2 | GENERIC_SCHEMA 2 |
| `importer/test_batch_contract.py` |  | GENERIC_SCHEMA_INVARIANT | 4 | GENERIC_SCHEMA 4 |
| `importer/test_batch_report.py` |  | GENERIC_SCHEMA_INVARIANT | 3 | GENERIC_SCHEMA 3 |
| `importer/test_batch_resume.py` |  | GENERIC_SCHEMA_INVARIANT | 1 | GENERIC_SCHEMA 1 |
| `importer/test_batch_runner.py` |  | GENERIC_SCHEMA_INVARIANT | 3 | GENERIC_SCHEMA 3 |
| `importer/test_batch_usage.py` |  | GENERIC_SCHEMA_INVARIANT | 4 | CROSS_MARKET 2, GENERIC_SCHEMA 2 |
| `importer/test_domain_packs.py` |  | GENERIC_SCHEMA_INVARIANT | 1 | GENERIC_SCHEMA 1 |
| `importer/test_fetch_hardening.py` |  | GENERIC_SCHEMA_INVARIANT | 1 | GENERIC_SCHEMA 1 |
| `importer/test_gold_benchmark.py` |  | GENERIC_SCHEMA_INVARIANT | 6 | GENERIC_SCHEMA 6 |
| `importer/test_lodging_accessibility.py` |  | GENERIC_SCHEMA_INVARIANT | 3 | GENERIC_SCHEMA 3 |
| `importer/test_lodging_reconciliation.py` |  | GENERIC_SCHEMA_INVARIANT | 2 | GENERIC_SCHEMA 2 |
| `importer/test_service_pack_aggregate.py` |  | GENERIC_SCHEMA_INVARIANT | 2 | GENERIC_SCHEMA 2 |
| `importer/test_source_applicability.py` |  | GENERIC_SCHEMA_INVARIANT | 1 | GENERIC_SCHEMA 1 |
| `importer/test_veterinary_aggregate.py` |  | GENERIC_SCHEMA_INVARIANT | 1 | GENERIC_SCHEMA 1 |
| `importer/test_veterinary_pack.py` |  | GENERIC_SCHEMA_INVARIANT | 1 | GENERIC_SCHEMA 1 |
| `policy/test_adversarial_fixtures.py` |  | GENERIC_SCHEMA_INVARIANT | 2 | GENERIC_SCHEMA 2 |
| `policy/test_authority_safety.py` |  | GENERIC_SCHEMA_INVARIANT | 3 | CURRENT_STATE 1, GENERIC_SCHEMA 2 |
| `policy/test_drury_and_sonesta.py` |  | GENERIC_SCHEMA_INVARIANT | 2 | GENERIC_SCHEMA 2 |
| `policy/test_m10_code_and_address_override.py` |  | GENERIC_SCHEMA_INVARIANT | 1 | CURRENT_STATE 1 |
| `test_build_capture_queue.py` |  | HISTORICAL_COHORT_INVARIANT | 4 | HISTORICAL_COHORT 4 |
| `test_cincinnati_brightdata_pilot_014.py` | cincinnati-oh | HISTORICAL_COHORT_INVARIANT | 9 | CROSS_MARKET 4, HISTORICAL_ARTIFACT 1, HISTORICAL_COHORT 4 |
| `test_cincinnati_capture_pass1_001.py` | cincinnati-oh | HISTORICAL_COHORT_INVARIANT | 11 | HISTORICAL_ARTIFACT 3, HISTORICAL_COHORT 8 |
| `test_cincinnati_founder_application_004.py` | cincinnati-oh | HISTORICAL_COHORT_INVARIANT | 8 | HISTORICAL_COHORT 8 |
| `test_cincinnati_founder_review_queue_002.py` | cincinnati-oh | HISTORICAL_COHORT_INVARIANT | 10 | HISTORICAL_COHORT 10 |
| `test_cincinnati_free_brand_probe_005.py` | cincinnati-oh | HISTORICAL_COHORT_INVARIANT | 11 | HISTORICAL_COHORT 11 |
| `test_cincinnati_free_lane_application_010.py` | cincinnati-oh | HISTORICAL_COHORT_INVARIANT | 13 | HISTORICAL_COHORT 13 |
| `test_cincinnati_free_lane_scale_006.py` | cincinnati-oh | HISTORICAL_COHORT_INVARIANT | 14 | HISTORICAL_ARTIFACT 3, HISTORICAL_COHORT 11 |
| `test_cincinnati_hilton_close_marriott_retry_015.py` | cincinnati-oh | HISTORICAL_COHORT_INVARIANT | 8 | HISTORICAL_ARTIFACT 1, HISTORICAL_COHORT 7 |
| `test_cincinnati_independent_probe_008.py` | cincinnati-oh | HISTORICAL_COHORT_INVARIANT | 12 | HISTORICAL_ARTIFACT 1, HISTORICAL_COHORT 11 |
| `test_cincinnati_independent_probe_009.py` | cincinnati-oh | HISTORICAL_COHORT_INVARIANT | 16 | HISTORICAL_COHORT 16 |
| `test_cincinnati_mainstay_census_split_013.py` | cincinnati-oh | HISTORICAL_COHORT_INVARIANT | 4 | HISTORICAL_COHORT 4 |
| `test_cincinnati_marriott_scale_batch_016.py` | cincinnati-oh | HISTORICAL_COHORT_INVARIANT | 7 | HISTORICAL_COHORT 7 |
| `test_cincinnati_species_key_rebind_011.py` | cincinnati-oh | HISTORICAL_COHORT_INVARIANT | 5 | HISTORICAL_ARTIFACT 1, HISTORICAL_COHORT 4 |
| `test_cincinnati_url_routing_progress_001.py` | cincinnati-oh | HISTORICAL_COHORT_INVARIANT | 5 | HISTORICAL_COHORT 5 |
| `test_cincinnati_zero_cost_capture_003.py` | cincinnati-oh | HISTORICAL_COHORT_INVARIANT | 6 | HISTORICAL_ARTIFACT 3, HISTORICAL_COHORT 3 |
| `test_cleveland_attended_artifact_queue_001.py` | cleveland-akron-canton-oh | HISTORICAL_COHORT_INVARIANT | 1 | HISTORICAL_COHORT 1 |
| `test_cleveland_authority.py` | cleveland-akron-canton-oh | CURRENT_STATE_INVARIANT | 3 | CURRENT_STATE 3 |
| `test_cleveland_capture_003.py` | cleveland-akron-canton-oh | HISTORICAL_COHORT_INVARIANT | 5 | HISTORICAL_COHORT 5 |
| `test_cleveland_final_partition_002.py` | cleveland-akron-canton-oh | HISTORICAL_COHORT_INVARIANT | 20 | CROSS_MARKET 1, HISTORICAL_COHORT 19 |
| `test_cleveland_hardened_application_002.py` | cleveland-akron-canton-oh | HISTORICAL_COHORT_INVARIANT | 1 | HISTORICAL_COHORT 1 |
| `test_cleveland_hardened_application_005.py` | cleveland-akron-canton-oh | HISTORICAL_COHORT_INVARIANT | 2 | HISTORICAL_COHORT 2 |
| `test_cleveland_hardened_policy_003.py` | cleveland-akron-canton-oh | HISTORICAL_COHORT_INVARIANT | 2 | HISTORICAL_COHORT 2 |
| `test_cleveland_hardened_policy_004.py` | cleveland-akron-canton-oh | HISTORICAL_COHORT_INVARIANT | 2 | HISTORICAL_COHORT 2 |
| `test_cleveland_hardened_revalidation_001.py` | cleveland-akron-canton-oh | HISTORICAL_COHORT_INVARIANT | 3 | HISTORICAL_ARTIFACT 1, HISTORICAL_COHORT 2 |
| `test_cleveland_pass1_artifact_verification.py` | cleveland-akron-canton-oh | HISTORICAL_COHORT_INVARIANT | 1 | HISTORICAL_COHORT 1 |
| `test_cleveland_pass3_capture_results.py` | cleveland-akron-canton-oh | HISTORICAL_COHORT_INVARIANT | 3 | HISTORICAL_ARTIFACT 1, HISTORICAL_COHORT 2 |
| `test_cleveland_pass4_capture_results.py` | cleveland-akron-canton-oh | HISTORICAL_COHORT_INVARIANT | 6 | HISTORICAL_ARTIFACT 1, HISTORICAL_COHORT 5 |
| `test_cleveland_work_browser_001.py` | cleveland-akron-canton-oh | HISTORICAL_COHORT_INVARIANT | 9 | HISTORICAL_ARTIFACT 3, HISTORICAL_COHORT 6 |
| `test_combined_weight_and_restriction_rows.py` |  | GENERIC_SCHEMA_INVARIANT | 1 | GENERIC_SCHEMA 1 |
| `test_coverage_audit.py` |  | GENERIC_SCHEMA_INVARIANT | 2 | GENERIC_SCHEMA 2 |
| `test_dayton_artifact_cohort_verification.py` | dayton-oh | HISTORICAL_COHORT_INVARIANT | 4 | HISTORICAL_ARTIFACT 1, HISTORICAL_COHORT 3 |
| `test_dayton_authority.py` | dayton-oh | CURRENT_STATE_INVARIANT | 9 | CROSS_MARKET 2, CURRENT_STATE 7 |
| `test_dayton_hardened_application_002.py` | dayton-oh | HISTORICAL_COHORT_INVARIANT | 7 | HISTORICAL_ARTIFACT 2, HISTORICAL_COHORT 5 |
| `test_dayton_hardened_revalidation_001.py` | dayton-oh | HISTORICAL_COHORT_INVARIANT | 3 | HISTORICAL_ARTIFACT 2, HISTORICAL_COHORT 1 |
| `test_dayton_pass_a_artifact_verification.py` | dayton-oh | HISTORICAL_COHORT_INVARIANT | 8 | CROSS_MARKET 3, HISTORICAL_ARTIFACT 3, HISTORICAL_COHORT 2 |
| `test_dayton_pass_b_founder_decisions.py` | dayton-oh | HISTORICAL_COHORT_INVARIANT | 7 | HISTORICAL_ARTIFACT 4, HISTORICAL_COHORT 3 |
| `test_dayton_pass_b_policy_corrections.py` | dayton-oh | HISTORICAL_COHORT_INVARIANT | 9 | HISTORICAL_COHORT 9 |
| `test_dayton_pass_c_decision_application.py` | dayton-oh | HISTORICAL_COHORT_INVARIANT | 12 | HISTORICAL_ARTIFACT 8, HISTORICAL_COHORT 4 |
| `test_dayton_recovery_002.py` | dayton-oh | HISTORICAL_COHORT_INVARIANT | 14 | HISTORICAL_ARTIFACT 1, HISTORICAL_COHORT 13 |
| `test_dayton_work_browser_001.py` | dayton-oh | HISTORICAL_COHORT_INVARIANT | 19 | HISTORICAL_ARTIFACT 5, HISTORICAL_COHORT 14 |
| `test_deployment_012.py` |  | DEPLOYMENT_EPOCH_INVARIANT | 16 | CROSS_MARKET 3, DEPLOYMENT_EPOCH 13 |
| `test_deployment_authorization_047.py` |  | DEPLOYMENT_EPOCH_INVARIANT | 7 | DEPLOYMENT_EPOCH 7 |
| `test_detroit_ann_arbor_capture_pass2_001.py` | detroit-ann-arbor-mi | HISTORICAL_COHORT_INVARIANT | 9 | HISTORICAL_ARTIFACT 1, HISTORICAL_COHORT 8 |
| `test_detroit_ann_arbor_capture_pass3_001.py` | detroit-ann-arbor-mi | HISTORICAL_COHORT_INVARIANT | 8 | HISTORICAL_ARTIFACT 2, HISTORICAL_COHORT 6 |
| `test_detroit_ann_arbor_market_001.py` | detroit-ann-arbor-mi | HISTORICAL_COHORT_INVARIANT | 1 | HISTORICAL_COHORT 1 |
| `test_export_authority_guard.py` |  | GENERIC_SCHEMA_INVARIANT | 8 | GENERIC_SCHEMA 8 |
| `test_factory_throughput_001.py` |  | DEPLOYMENT_EPOCH_INVARIANT | 6 | DEPLOYMENT_EPOCH 6 |
| `test_fee_forms.py` |  | GENERIC_SCHEMA_INVARIANT | 6 | CURRENT_STATE 1, GENERIC_SCHEMA 5 |
| `test_fee_tiers.py` |  | GENERIC_SCHEMA_INVARIANT | 2 | CURRENT_STATE 1, GENERIC_SCHEMA 1 |
| `test_founder_decisions_006.py` |  | HISTORICAL_COHORT_INVARIANT | 1 | HISTORICAL_COHORT 1 |
| `test_founder_finalize_007.py` |  | HISTORICAL_COHORT_INVARIANT | 11 | HISTORICAL_ARTIFACT 3, HISTORICAL_COHORT 8 |
| `test_founder_remediation_004.py` |  | HISTORICAL_COHORT_INVARIANT | 2 | HISTORICAL_COHORT 2 |
| `test_founder_review_analysis_003.py` |  | HISTORICAL_COHORT_INVARIANT | 3 | HISTORICAL_COHORT 3 |
| `test_founder_signature_005.py` |  | HISTORICAL_COHORT_INVARIANT | 9 | HISTORICAL_ARTIFACT 7, HISTORICAL_COHORT 2 |
| `test_generate_columbus_site.py` | columbus-oh | HISTORICAL_COHORT_INVARIANT | 4 | HISTORICAL_ARTIFACT 3, HISTORICAL_COHORT 1 |
| `test_global_assembler.py` |  | CURRENT_STATE_INVARIANT | 1 | CURRENT_STATE 1 |
| `test_global_deployment_architecture_045.py` |  | DEPLOYMENT_EPOCH_INVARIANT | 8 | DEPLOYMENT_EPOCH 8 |
| `test_grand_rapids_census_pin_024.py` | grand-rapids-holland-mi | HISTORICAL_COHORT_INVARIANT | 14 | HISTORICAL_ARTIFACT 2, HISTORICAL_COHORT 12 |
| `test_grand_rapids_cross_run_ledger_sync_018.py` | grand-rapids-holland-mi | HISTORICAL_COHORT_INVARIANT | 8 | CROSS_MARKET 1, HISTORICAL_ARTIFACT 2, HISTORICAL_COHORT 5 |
| `test_grand_rapids_founder_rulings_020.py` | grand-rapids-holland-mi | HISTORICAL_COHORT_INVARIANT | 13 | HISTORICAL_ARTIFACT 2, HISTORICAL_COHORT 11 |
| `test_grand_rapids_founder_signature_021.py` | grand-rapids-holland-mi | HISTORICAL_COHORT_INVARIANT | 8 | HISTORICAL_ARTIFACT 4, HISTORICAL_COHORT 4 |
| `test_grand_rapids_founder_signature_030.py` | grand-rapids-holland-mi | HISTORICAL_COHORT_INVARIANT | 11 | HISTORICAL_ARTIFACT 1, HISTORICAL_COHORT 10 |
| `test_grand_rapids_holland_market_001.py` | grand-rapids-holland-mi | HISTORICAL_COHORT_INVARIANT | 35 | HISTORICAL_ARTIFACT 10, HISTORICAL_COHORT 25 |
| `test_grand_rapids_identity_reconciliation_029.py` | grand-rapids-holland-mi | HISTORICAL_COHORT_INVARIANT | 13 | HISTORICAL_ARTIFACT 5, HISTORICAL_COHORT 8 |
| `test_grand_rapids_launch_participation_032.py` | grand-rapids-holland-mi | DEPLOYMENT_EPOCH_INVARIANT | 19 | DEPLOYMENT_EPOCH 19 |
| `test_grand_rapids_places_batch_027.py` | grand-rapids-holland-mi | HISTORICAL_COHORT_INVARIANT | 10 | CROSS_MARKET 3, HISTORICAL_ARTIFACT 1, HISTORICAL_COHORT 6 |
| `test_grand_rapids_places_pilot_026.py` | grand-rapids-holland-mi | HISTORICAL_COHORT_INVARIANT | 1 | HISTORICAL_COHORT 1 |
| `test_grand_rapids_policy_acquisition_028.py` | grand-rapids-holland-mi | HISTORICAL_COHORT_INVARIANT | 11 | HISTORICAL_ARTIFACT 3, HISTORICAL_COHORT 8 |
| `test_grand_rapids_review_prep_019.py` | grand-rapids-holland-mi | HISTORICAL_COHORT_INVARIANT | 24 | HISTORICAL_COHORT 24 |
| `test_grand_rapids_source_promotion_022.py` | grand-rapids-holland-mi | HISTORICAL_COHORT_INVARIANT | 14 | HISTORICAL_COHORT 14 |
| `test_grand_rapids_target_recovery_025.py` | grand-rapids-holland-mi | HISTORICAL_COHORT_INVARIANT | 11 | CROSS_MARKET 1, HISTORICAL_ARTIFACT 1, HISTORICAL_COHORT 9 |
| `test_homepage_market_awareness.py` |  | GENERIC_SCHEMA_INVARIANT | 6 | DEPLOYMENT_EPOCH 1, GENERIC_SCHEMA 5 |
| `test_hotel_profile.py` |  | CURRENT_STATE_INVARIANT | 1 | CURRENT_STATE 1 |
| `test_identity_evidence.py` |  | GENERIC_SCHEMA_INVARIANT | 3 | CROSS_MARKET 1, CURRENT_STATE 1, GENERIC_SCHEMA 1 |
| `test_identity_routing.py` |  | GENERIC_SCHEMA_INVARIANT | 10 | CURRENT_STATE 2, GENERIC_SCHEMA 8 |
| `test_ihg_recertification_011.py` |  | HISTORICAL_COHORT_INVARIANT | 10 | HISTORICAL_ARTIFACT 4, HISTORICAL_COHORT 6 |
| `test_indianapolis_acquisition_012.py` | indianapolis-in | HISTORICAL_COHORT_INVARIANT | 1 | HISTORICAL_COHORT 1 |
| `test_indianapolis_acquisition_016.py` | indianapolis-in | HISTORICAL_COHORT_INVARIANT | 14 | HISTORICAL_ARTIFACT 5, HISTORICAL_COHORT 9 |
| `test_indianapolis_acquisition_preflight_012.py` | indianapolis-in | HISTORICAL_COHORT_INVARIANT | 2 | HISTORICAL_COHORT 2 |
| `test_indianapolis_authority_promotion_017.py` | indianapolis-in | HISTORICAL_COHORT_INVARIANT | 4 | HISTORICAL_ARTIFACT 1, HISTORICAL_COHORT 3 |
| `test_indianapolis_backlog_cost_plan_015.py` | indianapolis-in | HISTORICAL_COHORT_INVARIANT | 13 | HISTORICAL_ARTIFACT 1, HISTORICAL_COHORT 12 |
| `test_indianapolis_decision_reconciliation.py` | indianapolis-in | HISTORICAL_COHORT_INVARIANT | 4 | HISTORICAL_COHORT 4 |
| `test_indianapolis_discovery_replay_007.py` | indianapolis-in | HISTORICAL_COHORT_INVARIANT | 4 | HISTORICAL_COHORT 4 |
| `test_indianapolis_final_cleanup_018.py` | indianapolis-in | HISTORICAL_COHORT_INVARIANT | 5 | CROSS_MARKET 1, HISTORICAL_ARTIFACT 1, HISTORICAL_COHORT 3 |
| `test_indianapolis_founder_review_013.py` | indianapolis-in | HISTORICAL_COHORT_INVARIANT | 16 | HISTORICAL_ARTIFACT 2, HISTORICAL_COHORT 14 |
| `test_indianapolis_founder_rulings_013.py` | indianapolis-in | HISTORICAL_COHORT_INVARIANT | 10 | HISTORICAL_ARTIFACT 1, HISTORICAL_COHORT 9 |
| `test_indianapolis_hilton_fresh_session.py` | indianapolis-in | HISTORICAL_COHORT_INVARIANT | 2 | HISTORICAL_COHORT 2 |
| `test_indianapolis_home2_reparse_014.py` | indianapolis-in | HISTORICAL_COHORT_INVARIANT | 3 | HISTORICAL_COHORT 3 |
| `test_indianapolis_identity_address_cleanup_012.py` | indianapolis-in | HISTORICAL_COHORT_INVARIANT | 5 | CROSS_MARKET 2, HISTORICAL_COHORT 3 |
| `test_indianapolis_identity_routing_repair_001.py` | indianapolis-in | HISTORICAL_COHORT_INVARIANT | 7 | HISTORICAL_ARTIFACT 1, HISTORICAL_COHORT 6 |
| `test_indianapolis_market_001.py` | indianapolis-in | HISTORICAL_COHORT_INVARIANT | 2 | HISTORICAL_COHORT 2 |
| `test_indianapolis_name_normalization_009.py` | indianapolis-in | HISTORICAL_COHORT_INVARIANT | 1 | HISTORICAL_COHORT 1 |
| `test_indianapolis_paid_attempt_ledger_sync_001.py` | indianapolis-in | HISTORICAL_COHORT_INVARIANT | 3 | HISTORICAL_ARTIFACT 1, HISTORICAL_COHORT 2 |
| `test_indianapolis_pass1_capture.py` | indianapolis-in | HISTORICAL_COHORT_INVARIANT | 4 | HISTORICAL_COHORT 4 |
| `test_indianapolis_pass2_capture.py` | indianapolis-in | HISTORICAL_COHORT_INVARIANT | 9 | CROSS_MARKET 6, HISTORICAL_COHORT 3 |
| `test_indianapolis_pass2_founder_decision.py` | indianapolis-in | HISTORICAL_COHORT_INVARIANT | 6 | HISTORICAL_COHORT 6 |
| `test_indianapolis_pass3a_capture.py` | indianapolis-in | HISTORICAL_COHORT_INVARIANT | 4 | HISTORICAL_COHORT 4 |
| `test_indianapolis_pass3a_founder_decision.py` | indianapolis-in | HISTORICAL_COHORT_INVARIANT | 1 | HISTORICAL_COHORT 1 |
| `test_indianapolis_payload_rebind_011.py` | indianapolis-in | HISTORICAL_COHORT_INVARIANT | 5 | HISTORICAL_COHORT 5 |
| `test_indianapolis_places_broader_010.py` | indianapolis-in | HISTORICAL_COHORT_INVARIANT | 9 | HISTORICAL_ARTIFACT 2, HISTORICAL_COHORT 7 |
| `test_indianapolis_places_qualification_008.py` | indianapolis-in | HISTORICAL_COHORT_INVARIANT | 7 | HISTORICAL_ARTIFACT 3, HISTORICAL_COHORT 4 |
| `test_indianapolis_promotion_and_assembly_014.py` | indianapolis-in | HISTORICAL_COHORT_INVARIANT | 1 | HISTORICAL_COHORT 1 |
| `test_indianapolis_promotion_validation_003.py` | indianapolis-in | HISTORICAL_COHORT_INVARIANT | 1 | HISTORICAL_COHORT 1 |
| `test_indianapolis_recovery_005.py` | indianapolis-in | HISTORICAL_COHORT_INVARIANT | 3 | HISTORICAL_COHORT 3 |
| `test_indianapolis_url_discovery_007.py` | indianapolis-in | HISTORICAL_COHORT_INVARIANT | 2 | HISTORICAL_COHORT 2 |
| `test_indianapolis_url_recovery_006.py` | indianapolis-in | HISTORICAL_COHORT_INVARIANT | 2 | CROSS_MARKET 1, HISTORICAL_COHORT 1 |
| `test_inventory_validation.py` |  | CURRENT_STATE_INVARIANT | 3 | CURRENT_STATE 3 |
| `test_launch_participation_046.py` |  | DEPLOYMENT_EPOCH_INVARIANT | 9 | DEPLOYMENT_EPOCH 9 |
| `test_listing_dataset_builder.py` |  | CURRENT_STATE_INVARIANT | 3 | CURRENT_STATE 3 |
| `test_listing_renderability_boundary.py` |  | CURRENT_STATE_INVARIANT | 4 | CURRENT_STATE 4 |
| `test_louisville_authority.py` | louisville-ky | CURRENT_STATE_INVARIANT | 46 | CURRENT_STATE 46 |
| `test_louisville_final_006.py` | louisville-ky | HISTORICAL_COHORT_INVARIANT | 3 | HISTORICAL_ARTIFACT 1, HISTORICAL_COHORT 2 |
| `test_louisville_publication_008.py` | louisville-ky | DEPLOYMENT_EPOCH_INVARIANT | 16 | DEPLOYMENT_EPOCH 16 |
| `test_market_coverage_cli.py` |  | GENERIC_SCHEMA_INVARIANT | 18 | GENERIC_SCHEMA 18 |
| `test_market_factory_cli.py` |  | GENERIC_SCHEMA_INVARIANT | 1 | GENERIC_SCHEMA 1 |
| `test_market_isolation.py` |  | CURRENT_STATE_INVARIANT | 7 | CURRENT_STATE 7 |
| `test_market_ownership.py` |  | CURRENT_STATE_INVARIANT | 10 | CURRENT_STATE 10 |
| `test_market_policy_package_009.py` |  | HISTORICAL_COHORT_INVARIANT | 6 | HISTORICAL_COHORT 6 |
| `test_market_recensus_sandbox.py` |  | GENERIC_SCHEMA_INVARIANT | 3 | CURRENT_STATE 1, GENERIC_SCHEMA 2 |
| `test_markets.py` |  | GENERIC_SCHEMA_INVARIANT | 3 | GENERIC_SCHEMA 3 |
| `test_measurement.py` |  | CURRENT_STATE_INVARIANT | 2 | CURRENT_STATE 2 |
| `test_milwaukee_market_001.py` | milwaukee-wi | HISTORICAL_COHORT_INVARIANT | 5 | HISTORICAL_COHORT 5 |
| `test_official_capture_extension.py` |  | HISTORICAL_COHORT_INVARIANT | 1 | HISTORICAL_ARTIFACT 1 |
| `test_per_market_release_contracts.py` |  | CURRENT_STATE_INVARIANT | 5 | CURRENT_STATE 4, DEPLOYMENT_EPOCH 1 |
| `test_pittsburgh_market_001.py` | pittsburgh-pa | HISTORICAL_COHORT_INVARIANT | 2 | HISTORICAL_COHORT 2 |
| `test_pittsburgh_pass4_claude_capture_001.py` | pittsburgh-pa | HISTORICAL_COHORT_INVARIANT | 4 | HISTORICAL_ARTIFACT 3, HISTORICAL_COHORT 1 |
| `test_pittsburgh_pass4_decision_application_001.py` | pittsburgh-pa | HISTORICAL_COHORT_INVARIANT | 2 | HISTORICAL_ARTIFACT 2 |
| `test_pittsburgh_pass4_decision_application_001_prep.py` | pittsburgh-pa | HISTORICAL_COHORT_INVARIANT | 2 | HISTORICAL_COHORT 2 |
| `test_policy_precision.py` |  | GENERIC_SCHEMA_INVARIANT | 2 | CURRENT_STATE 1, GENERIC_SCHEMA 1 |
| `test_policy_schema_migration.py` |  | CURRENT_STATE_INVARIANT | 7 | CURRENT_STATE 7 |
| `test_prod003_package_preview.py` |  | CURRENT_STATE_INVARIANT | 1 | CURRENT_STATE 1 |
| `test_prod003_promotion_readpath.py` |  | CURRENT_STATE_INVARIANT | 3 | CURRENT_STATE 3 |
| `test_prod003_worker_approvals.py` |  | CURRENT_STATE_INVARIANT | 3 | CURRENT_STATE 3 |
| `test_prod004_verified_only.py` |  | CURRENT_STATE_INVARIANT | 4 | CURRENT_STATE 4 |
| `test_prod005_netlify_config.py` |  | CURRENT_STATE_INVARIANT | 11 | CURRENT_STATE 11 |
| `test_production_deploy_012.py` |  | DEPLOYMENT_EPOCH_INVARIANT | 14 | CROSS_MARKET 1, DEPLOYMENT_EPOCH 13 |
| `test_profile_fee_dimensions.py` |  | GENERIC_SCHEMA_INVARIANT | 4 | CURRENT_STATE 1, GENERIC_SCHEMA 3 |
| `test_promotion_preserves_structured_facts.py` |  | GENERIC_SCHEMA_INVARIANT | 1 | CURRENT_STATE 1 |
| `test_publication_cleanup_008b.py` |  | DEPLOYMENT_EPOCH_INVARIANT | 14 | CROSS_MARKET 1, DEPLOYMENT_EPOCH 13 |
| `test_publication_guard.py` |  | GENERIC_SCHEMA_INVARIANT | 7 | CURRENT_STATE 2, GENERIC_SCHEMA 5 |
| `test_publication_schema_decisions_010.py` |  | HISTORICAL_COHORT_INVARIANT | 12 | DEPLOYMENT_EPOCH 1, HISTORICAL_COHORT 11 |
| `test_reader_tiered_fee_hardening_010.py` |  | HISTORICAL_COHORT_INVARIANT | 3 | CROSS_MARKET 1, HISTORICAL_COHORT 2 |
| `test_register_publish_011.py` |  | DEPLOYMENT_EPOCH_INVARIANT | 7 | DEPLOYMENT_EPOCH 7 |
| `test_regression_delta_001.py` |  | HISTORICAL_COHORT_INVARIANT | 3 | HISTORICAL_COHORT 3 |
| `test_renderer_real_records.py` |  | GENERIC_SCHEMA_INVARIANT | 7 | CURRENT_STATE 2, GENERIC_SCHEMA 5 |
| `test_routing_property_code_scope.py` |  | GENERIC_SCHEMA_INVARIANT | 3 | GENERIC_SCHEMA 3 |
| `test_service_animal_correction_011.py` |  | HISTORICAL_COHORT_INVARIANT | 1 | CROSS_MARKET 1 |
| `test_service_animal_reattestation_012.py` |  | HISTORICAL_COHORT_INVARIANT | 4 | HISTORICAL_ARTIFACT 1, HISTORICAL_COHORT 3 |
| `test_site_data.py` |  | CURRENT_STATE_INVARIANT | 2 | CURRENT_STATE 2 |
| `test_site_enrichment.py` |  | CURRENT_STATE_INVARIANT | 1 | CURRENT_STATE 1 |
| `test_sonesta_identity_and_scope.py` |  | GENERIC_SCHEMA_INVARIANT | 2 | CURRENT_STATE 1, GENERIC_SCHEMA 1 |
| `test_st_louis_market_001.py` | st-louis-mo | HISTORICAL_COHORT_INVARIANT | 1 | HISTORICAL_COHORT 1 |
| `test_st_louis_production_safety_001.py` | st-louis-mo | DEPLOYMENT_EPOCH_INVARIANT | 6 | DEPLOYMENT_EPOCH 6 |
| `test_structured_data.py` |  | CURRENT_STATE_INVARIANT | 2 | CURRENT_STATE 2 |
| `test_two_market_compat.py` |  | GENERIC_SCHEMA_INVARIANT | 4 | CROSS_MARKET 1, GENERIC_SCHEMA 3 |
| `test_worker_artifact_backup.py` |  | GENERIC_SCHEMA_INVARIANT | 6 | GENERIC_SCHEMA 6 |
