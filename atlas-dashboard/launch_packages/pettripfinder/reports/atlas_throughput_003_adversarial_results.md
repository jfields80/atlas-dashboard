# ATLAS-THROUGHPUT-003 — adversarial test matrix

`tests/pettripfinder/test_atlas_throughput_003.py`: 69 passed, 0 failed, 0 skipped (junit in
`atlas_throughput_003_adversarial_results.json`). Every case mutates the REAL Dayton authority as the pilot
sealed it, or the real live-release index — never a synthetic shape the gate was written to recognise.

| # | claim | proof | outcome |
|---|---|---|---|
| 1 | valid sealed data-only package ⇒ PASS | `TestFastLane::test_case_1_the_corrected_dayton_package_passes_every_non_build_rule; TestFastLane::test_case_15_identical_changed_market_builds_are_deterministic_and_cold; TestCommittedPilot` | PASS |
| 2 | wrong hotel evidence ⇒ FAIL | `TestFirstPartyGate::test_case_2_wrong_hotel_page_bound_to_the_right_record; test_same_brand_wrong_property` | FAIL (WRONG_PROPERTY) |
| 3 | competitor-only policy evidence ⇒ FAIL | `TestFirstPartyGate::test_case_3_competitor_only_evidence_is_lead_only` | FAIL (LEAD_ONLY; writer PUBLICATION_BLOCKED) |
| 4 | fee-only acceptance inference ⇒ FAIL | `TestFirstPartyGate::test_case_4_fee_present_acceptance_absent` | FAIL (FEE_ONLY) |
| 5 | service-animal-only acceptance ⇒ FAIL | `TestFirstPartyGate::test_case_5_service_animals_only` | FAIL (SERVICE_ANIMAL_ONLY) |
| 6 | invalid fee basis/enum ⇒ FAIL | `TestTypedWriter::test_case_6_invalid_fee_basis_enum_and_currency` | FAIL (POLICY_BAD_ENUM …) |
| 7 | orphaned partition ⇒ FAIL | `TestTypedWriter::test_case_7_orphaned_partition` | FAIL (ORPHAN_PARTITION) |
| 8 | duplicate identity ⇒ FAIL | `TestTypedWriter::test_case_8_duplicate_identity` | FAIL (DUPLICATE_IDENTITY) |
| 9 | legitimate same-campus distinct hotel ⇒ PASS | `TestSamePremises::test_case_9_legitimate_same_campus_distinct_hotels_pass; test_a_declared_relation_admits_a_pair…` | PASS |
| 10 | cross-market canonical identity collision ⇒ FAIL | `TestReleaseIndex::test_case_10_cross_market_canonical_identity_collision` | FAIL (CROSS_MARKET_IDENTITY_COLLISION + OWNERSHIP_MOVEMENT) |
| 11 | unintended unrelated-market removal ⇒ FAIL | `TestReleaseIndex::test_case_11_an_unrelated_live_market_cannot_disappear` | FAIL (MISSING_LIVE_MARKET / MISSING_UNRELATED_PROFILE / ROUTE) |
| 12 | intended explicit removal ⇒ PASS only under authority | `TestReleaseIndex::test_case_12_and_13…; TestSealedPackageContract::test_a_removal_without_a_ruling_cannot_even_seal` | PASS with removal_authority; refused without |
| 13 | unintended route loss ⇒ FAIL | `TestReleaseIndex::test_case_12_and_13_removals_and_route_loss_must_be_declared` | FAIL (UNINTENDED_ROUTE_CHANGE on the two corridor routes) |
| 14 | wrong-market route ownership ⇒ FAIL | `TestTypedWriter::test_case_14_invalid_market_assignment…; TestReleaseIndex::test_case_14_a_route_claimed_by_two_markets_is_a_duplicate` | FAIL (INVALID_MARKET_ASSIGNMENT / DUPLICATE_ROUTE) |
| 15 | identical changed-market build ⇒ deterministic PASS | `TestFastLane::test_case_15_identical_changed_market_builds_are_deterministic_and_cold` | PASS (BYTE_IDENTICAL, 2 cold builds, 0 reuse hits) |
| 16 | nondeterministic changed-market build ⇒ FAIL | `TestFastLane::test_case_16_a_nondeterministic_build_fails_the_gate; test_two_cache_hits_can_never_pass…` | FAIL (DIFFERENT; a warm build fails J and K) |
| 17 | stale parent/live state ⇒ NOT FAST-ELIGIBLE | `TestReleaseIndex::test_case_17_the_stale_pittsburgh_like_package…` | NOT ELIGIBLE (rule N; H passes from CURRENT live; nothing rebuilt) |
| 18 | malformed package digest ⇒ FAIL | `TestSealedPackageContract::test_case_18_a_malformed_or_tampered_digest_fails` | FAIL (rule A; read_sealed refuses) |
| 19 | evidence hash mismatch ⇒ FAIL | `TestTypedWriter::test_case_19_evidence_hash_mismatch_and_missing_binding` | FAIL (MISSING_EVIDENCE_BINDING; rule L on artifact bytes) |
| 20 | unresolved row incorrectly promoted clean ⇒ FAIL | `TestTypedWriter::test_case_20_an_unresolved_row_promoted_clean` | FAIL (UNRESOLVED_PROMOTED_CLEAN) |
| 21 | paid evidence without reservation provenance ⇒ FAIL | `TestFastLane::test_case_21_paid_evidence_without_reservation_provenance_fails` | FAIL (rule O) |
| 22 | correctly reserved paid evidence ⇒ PASS, no provider call | `TestFastLane::test_case_22_a_correctly_reserved_paid_capture_passes_without_a_provider_call` | PASS (attempt_id re-derives; ledger cross-checked); UNKNOWN ledger ⇒ NOT ELIGIBLE |
| 23 | unknown dependency ⇒ NOT FAST-ELIGIBLE / broad | `TestRegressionV2Extension::test_case_23_an_unknown_dependency_is_not_data_only` | not data-only; UNKNOWN_MIXED; full regression |
| 24 | shared runtime change ⇒ NOT DATA-ONLY | `TestRegressionV2Extension::test_case_24_a_shared_runtime_change_is_not_data_only` | SHARED_RUNTIME_CHANGE / SHARED_SCHEMA_CHANGE; full regression |
| 25 | shared assembler change ⇒ NOT DATA-ONLY | `TestRegressionV2Extension::test_case_25_a_shared_assembler_change_is_not_data_only` | ASSEMBLER_CHANGE; full regression |

Also proven: the seal is deterministic and `sealed_at` is outside it; a sealed package is never rewritten in
place; the receipt carries every field the order names; UNKNOWN ⇒ NOT ELIGIBLE (build=False leaves J/K UNKNOWN
and the corrected package NOT ELIGIBLE); the lane builds only the changed market; staging restores every
patched constant and leaves committed authority untouched; the mandatory-full class set is unchanged;
packages/staging/receipts are MARKET_DATA_PACKAGE and market-owned; the fast requirement fails closed without
a package, without a receipt, with a NOT-eligible receipt, and with an ELIGIBLE receipt while activation is
DISABLED; the committed activation is DISABLED with an empty allowlist; this order's own change set is broad.
