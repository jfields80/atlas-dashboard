# Inherited failures the broad run surfaced — PTF-NASHVILLE-POST-LAUNCH-TEST-HARNESS-CLEANUP-006

The one broad regression this order ran classified 160 PRE_EXISTING and 18
TRUE_NEW against the `f75aa95` baseline. That baseline predates both the
Lexington and the Nashville launches, so it counts anything those launches moved
as new.

**Measured against `ba55ec8`, the commit this order started from, 17 of the 18
already failed.** Node-ID closure, run in a scratch worktree at that commit:

```
17 failed, 1 passed in 591.24s
```

The one that passed there — `test_factory_throughput_001::TestTheHarness::
test_the_committed_baseline_manifest_names_its_sha_and_node_ids` — was this
order's own-goal: `--out run_006_full.json` made the lane runner create a
*directory* by that name inside `regression_baselines/`, where the test globs
`*.json`. Run artifacts moved to the reports tree; fixed.

**So this order caused zero new failures, and closed eleven it did not cause.**

## Closed here

| node | why it failed | fix |
|---|---|---|
| `test_market_authority_sharding::TestWriteDiscipline` (×2) | the Nashville launch script composed a shard path inline inside the authorization's note, so the whole authorization expression read as a name bound to a generated global | read the counts through `market_authority.exclusions_shard_path` and bind them before the record is built |
| `test_launch_participation_046::…excludes_only_the_two…` | `NOT_READY` still listed Nashville as withheld | Nashville left that list by founder decision |
| `test_st_louis_production_safety_001::…names_what_it_supersedes` | the dropped decision chain | read through `launch_participation.decision_chain` |
| `test_grand_rapids_launch_participation_032` (×2) | the dropped chain, and a set enumerating three admissions when there are four | the chain contract, and Nashville enumerated |
| `test_louisville_publication_008::…binds_the_bundle…` | the dropped chain | the chain contract |
| `test_global_assembler` (×2) | the enumerated live set stopped at Toledo — the **Lexington** launch never updated it | the twelfth and thirteenth markets enumerated |
| `test_nashville_tn_new_market_001::…moved_no_live_market` | asserted Nashville is not live; it is, by a later founder decision | asserts what registration did: the market is absent from the release that was live when it registered |
| `test_toledo_oh_promotion_002::…derived_from_artifacts…` | named the two newest deploys, and three have landed since | the packet's rollback target must be a real DEPLOYED release, which does not need rewriting every launch |

## Open, and why each is a separate order

Six remain. None was caused by this order and none is a test-bookkeeping fix.
Two of them are findings about live data.

**A live cross-market identity collision.**
`test_indianapolis_authority_promotion_017::TestTheCrossMarketCollision::
test_the_scan_finds_nothing_else` and `::test_the_other_bare_names_are_clean`.
The bare identity key `tru` is now claimed by **both** `indianapolis-in` and
`lexington-ky`. The test's own point is that `tru` was "equally bare and did NOT
collide" — evidence-driven, not a rule about short names. That is no longer
true. A bare brand name normalises identically in every market, and two
buildings cannot share one identity key. This needs an identity ruling on the
address, phone or property code, not a test edit; editing the test to accept the
collision would paper over a possible defect in published data. Caused by
PTF-LEXINGTON-KY-PROMOTION-AND-NEW-LANE-LAUNCH-PREP-003.

**A property-code parser gap.**
`test_marriott_short_property_link::TestNothingElseMoved::
test_the_columbus_seed_still_parses_end_to_end` and
`test_property_code_redroof_choice::TestLiveSeedUrlsAllParse::
test_every_columbus_seed_url_with_a_known_shape_still_resolves`.
`extract_property_code_from_url("https://www.hilton.com/en/hotels/lexrrdt/hotel-info/")`
returns `""` for a Lexington DoubleTree. The code shape is real and the
extractor does not recognise it, so a live seed URL resolves to nothing. Caused
by the same Lexington registration.

**Two throughput budgets.**
`test_atlas_throughput_003::TestReleaseIndex::
test_the_index_is_o_data_and_fast_at_a_hundred_markets` asserts
`6904 > 7000` — a rate budget the index no longer meets at a hundred markets.
`test_atlas_throughput_004::TestBoundaries::
test_the_fast_lane_reports_market_build_required_no_on_a_trusted_bundle` fails
its boundary. Both belong to the ATLAS-THROUGHPUT lane and neither is a launch
fact.

## The rule this leaves behind

A launch that ships red tests hides the next launch's real findings. Both live
findings above sat unnoticed through two launches because the broad run that
would have shown them was never classified against the right baseline. Classify
against the commit the order started from, not against the oldest baseline on
disk.
