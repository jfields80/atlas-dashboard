"""PTF-GRAND-RAPIDS-HOLLAND-MARKET-FACTORY-001 Phase-1 gates."""
from __future__ import annotations

import json
from pathlib import Path

from scripts.pettripfinder.contracts import census, partition
from scripts.pettripfinder.contracts.identity_key import ptf_identity_key
from scripts.pettripfinder.discovery.market_config import load_market_config
from scripts.pettripfinder.discovery.source_families import family_of
from scripts.pettripfinder.markets import assign_hotels, load_markets, market_by_id

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "launch_packages" / "pettripfinder"
MARKET = "grand-rapids-holland-mi"


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


#: PTF-GRAND-RAPIDS-CENSUS-PIN-AND-RELEASE-CONTRACT-024 promoted the 163-row
#: recensus into the pinned path and kept the 120-identity document this
#: module's Phase-1 gates are ABOUT. Those gates keep their subject: they
#: record what the 2025 build produced, and rewriting their numbers to the new
#: census would erase that record rather than extend it. The live census gets
#: its own assertions below.
def census_doc():
    """The census THIS work order produced, now superseded and preserved."""
    return _load(PACKAGE / "identity_census" / "superseded"
                 / (MARKET + "-120.json"))


def pinned_census_doc():
    """The census the market runs on today."""
    return _load(PACKAGE / "identity_census" / (MARKET + ".json"))


def partition_doc():
    return _load(PACKAGE / "grand_rapids_holland_final_partition_001.json")


def test_candidate_reconciliation_has_no_unexplained_disappearance():
    ledger = _load(PACKAGE / "grand_rapids_holland_candidate_ledger_001.json")
    counts = ledger["counts"]
    assert ledger["raw_listings"] == len(ledger["items"]) == 157
    assert counts == {
        "ADD_TO_CENSUS": 23,
        "BOUNDARY_EXCLUDED": 12,
        "CANONICAL_CENSUS": 96,
        "CATEGORY_EXCLUDED": 5,
        "CLOSED_OR_CONVERTED": 1,
        "SOURCE_LISTING_ALREADY_ACCOUNTED_FOR": 19,
        "SOURCE_LISTING_NOT_LODGING": 1,
    }
    assert sum(counts.values()) == ledger["raw_listings"]
    assert all(item["disposition"] for item in ledger["items"])


def test_the_pinned_census_is_the_promoted_one_and_is_contract_valid():
    """The live census: 163 identities, promoted from the recensus by 024."""
    doc = pinned_census_doc()
    assert doc["schema"] == "ptf-market-identity-census/1.1"
    assert doc["market_id"] == MARKET
    assert doc["count"] == len(doc["hotels"]) == 163
    assert census.validate(doc, market_states=["MI"]) == ()
    accounting = doc["prior_census_accounting"]
    assert accounting["prior_identities"] == 120
    assert accounting["survived_by_key"] == 110
    assert accounting["absorbed_into_a_fresh_sighting"] == 10
    assert accounting["unexplained_losses"] == []
    # Ten prior identities are absent because each was absorbed into a fresh
    # sighting of the same building; the count going up is not evidence that
    # nothing was lost, so every absorption is named.
    assert len(accounting["absorptions"]) == 10
    for row in accounting["absorptions"]:
        assert row["street_identity"] and row["basis"]


def test_census_is_independent_and_contract_valid():
    doc = census_doc()
    assert doc["schema"] == "ptf-market-identity-census/1.1"
    assert doc["market_id"] == MARKET
    assert doc["count"] == len(doc["hotels"]) == 120
    assert census.validate(doc, market_states=["MI"]) == ()
    for row in doc["hotels"]:
        assert row["market_id"] == MARKET
        assert row["identity_key"] == ptf_identity_key(row["canonical_name"])
        assert row["policy_state"] == "POLICY_NOT_VERIFIED"


def test_the_pinned_census_pairs_with_the_163_row_partition():
    """A census and a partition are a pair. The 120-era partition answers for
    the superseded census; the 163-row one answers for the pinned census."""
    doc = _load(PACKAGE / "grand_rapids_holland_mi_final_partition_001.json")
    reconciliation = partition.reconcile(
        census.identity_keys(pinned_census_doc()), doc, market_id=MARKET)
    assert reconciliation.agrees
    assert partition.validate(doc) == ()


def test_partition_is_honest_zero_policy_authority():
    doc = partition_doc()
    reconciliation = partition.reconcile(census.identity_keys(census_doc()), doc, market_id=MARKET)
    assert reconciliation.agrees
    assert reconciliation.published == 0
    assert reconciliation.verified_no_pets == 0
    assert reconciliation.out_of_category == 1
    assert reconciliation.unresolved == 119
    assert partition.validate(doc) == ()


def test_corridors_classify_the_existing_census_not_the_reverse():
    market = market_by_id(load_markets(), MARKET)
    rows = [{"name": row["identity_key"], "city": row["city"],
             "state": row["state"], "postal_code": row["postal_code"]}
            for row in census_doc()["hotels"] if row["lodging_state"] == "LODGING_CONFIRMED"]
    assignment = assign_hotels(market, rows, fail_closed=True)
    assert len(assignment.corridor_of) == 119
    assert assignment.unassigned == ()
    assert set(assignment.published) == {
        MARKET + "__downtown-grand-rapids",
        MARKET + "__grr-airport-kentwood",
        MARKET + "__holland-zeeland",
        MARKET + "__walker-northwest-grand-rapids",
        MARKET + "__wyoming-grandville",
        MARKET + "__east-grand-rapids-ada",
    }
    assert assignment.suppressed == ()


def test_sources_and_discovery_cells_are_registered():
    registry = _load(PACKAGE / "markets" / "reports" / (MARKET + "_source_registry.json"))
    assert len(registry["sources"]) == 24
    assert all(source["completeness"] == "PARTIAL" for source in registry["sources"])
    assert all(family_of(source["source_id"]) == source["family"] for source in registry["sources"])
    market = market_by_id(load_markets(), MARKET)
    cell_ids = {cell.cell_id for cell in load_market_config(MARKET).cells}
    corridor_ids = {corridor.corridor_id for corridor in market.corridors}
    # Every corridor still has its seed cell. PTF-GRAND-RAPIDS-HOLLAND-
    # GEOGRAPHY-HARDENING-002 added four cells that are NOT corridors: they
    # cover included municipalities and census lodging clusters the corridor
    # cells left outside every query radius. Cells seed discovery; corridors
    # classify the census. The two sets are no longer required to coincide.
    assert corridor_ids <= cell_ids
    assert cell_ids - corridor_ids == {
        MARKET + "__comstock-park-alpine",
        MARKET + "__ada-cascade-east",
        MARKET + "__northeast-grand-rapids-plainfield",
        MARKET + "__south-wyoming-cutlerville",
    }


def test_boundary_and_routing_reports_are_conservative():
    boundary = _load(PACKAGE / "grand_rapids_holland_boundary_review_001.json")
    assert len(boundary["items"]) == 12
    assert set(boundary["area_findings"]) == {"Grand Haven", "Muskegon", "Saugatuck / Douglas", "South Haven"}
    assert boundary["explicitly_excluded_areas"] == ["Lansing / East Lansing", "Traverse City / Northwest Michigan", "Kalamazoo / Battle Creek"]
    routing = _load(PACKAGE / "markets" / "reports" / (MARKET + "_routing_readiness.json"))
    assert routing["summary"] == {"property_level_urls": 39, "missing_urls": 80, "routing_ready": 39, "evidence_ready_estimate": 0, "manual_or_bot_wall": 0}
    assert all(item["assessment_status"] == "ASSESSMENT_ONLY" for item in routing["items"])
    capture = _load(PACKAGE / "grand_rapids_holland_capture_ready_queue_001.json")
    assert capture["count"] == 39
    assert all(item["routing_ready"] for item in capture["items"])


def test_completeness_pass_is_additive_and_retains_every_new_lead():
    ledger = _load(PACKAGE / "grand_rapids_holland_completeness_candidate_ledger_001.json")
    assert ledger["raw_listings"] == len(ledger["items"]) == 45
    assert ledger["counts"] == {
        "ADD_TO_CENSUS": 24,
        "BOUNDARY_EXCLUDED": 2,
        "IDENTITY_UNRESOLVED": 19,
    }
    assert sum(ledger["counts"].values()) == ledger["raw_listings"]


def test_additional_completeness_pass_is_additive_and_fail_closed():
    ledger = _load(PACKAGE / "grand_rapids_holland_completeness_candidate_ledger_002.json")
    assert ledger["raw_listings"] == len(ledger["items"]) == 45
    assert ledger["counts"] == {
        "BOUNDARY_EXCLUDED": 2,
        "CANONICAL_CENSUS": 40,
        "CATEGORY_EXCLUDED": 2,
        "SOURCE_LISTING_NOT_LODGING": 1,
    }
    report = _load(PACKAGE / "grand_rapids_holland_census_completeness_002.json")
    assert report["completeness_pass_reconciliation"] == {
        "census_before": 56,
        "new_discovery_candidates": 45,
        "new_valid_lodging_identities": 40,
        "proven_removals": 0,
        "final_census": 96,
        "identity_unresolved_before": 19,
        "identity_unresolved_after": 2,
    }
    assert report["verdict"] == "CENSUS_STILL_INCOMPLETE"
    assert report["policy_capture"] == "NOT_PERFORMED"


def test_final_closure_pass_is_exact_and_reconciles_the_last_leads():
    ledger = _load(PACKAGE / "grand_rapids_holland_completeness_candidate_ledger_003.json")
    assert ledger["raw_listings"] == len(ledger["items"]) == 31
    assert ledger["counts"] == {
        "BOUNDARY_EXCLUDED": 3,
        "CANONICAL_CENSUS": 25,
        "CATEGORY_EXCLUDED": 2,
        "CLOSED_OR_CONVERTED": 1,
    }
    assert sum(ledger["counts"].values()) == ledger["raw_listings"]
    report = _load(PACKAGE / "grand_rapids_holland_census_closure_003.json")
    assert report["reconciliation"] == {
        "census_before": 96,
        "new_discovery_candidates": 31,
        "new_valid_lodging_identities": 25,
        "proven_removals": 1,
        "final_census": 120,
        "identity_unresolved_before": 2,
        "identity_unresolved_after": 0,
        "duplicates": 0,
        "closed_or_converted": 1,
    }
    assert report["verdict"] == "CENSUS_COMPLETE"
    assert report["kent_county_reconciliation"]["complete_for_in_scope_lodging_reconciliation"]
    assert report["policy_capture"] == "NOT_PERFORMED"


def test_market_has_no_identity_collision_and_publishes_only_its_own():
    """The disjointness invariant is unchanged and is the half that mattered.

    The other half of this test asserted that Grand Rapids published NOTHING --
    true of a discovery-stage market and no longer true of one, since
    PTF-GRAND-RAPIDS-SOURCE-PROMOTION-022 wrote 35 founder-signed profiles and
    14 exclusions from a signed authority. Deleting the assertion would lose
    the guard it was really carrying, so it is replaced by the statement that
    survives the market growing up: whatever this market publishes is ITS OWN,
    and it publishes nothing on another market's behalf.
    """
    # The PINNED census shares three bare-chain keys with Cleveland -- and the
    # condition is systemic rather than this market's: Louisville and St. Louis
    # already share seven, and Louisville already publishes a record whose
    # identity_key is "tru". So the guard is no longer "disjoint" but "no NEW
    # collision appears without being recorded", checked against the pin
    # report's own list.
    ours = census.identity_keys(pinned_census_doc())
    # TWO RECORDS, UNIONED. 024 recorded 16 collisions against the markets on
    # this branch at the time. PTF-GRAND-RAPIDS-INDIANAPOLIS-LINEAGE-MERGE-033
    # brought Indianapolis's later recensus and five more became visible, and
    # they are recorded in that order's own document rather than back-written
    # into 024's -- 024's report is a dated statement of what that pass found
    # and editing it would rewrite history to make a later fact look old.
    recorded = {(r["identity_key"], r["also_in_market"]) for r in
                _load(PACKAGE / "grand_rapids_holland_mi_census_pin_024.json"
                      )["cross_market_collisions"]["rows"]}
    recorded |= {(r["identity_key"], r["also_in_market"]) for r in
                 _load(PACKAGE / "grand_rapids_holland_mi_cross_market_"
                       "collisions_033.json")["rows"]}
    for other in ("columbus-oh", "cleveland-akron-canton-oh", "dayton-oh",
                  "cincinnati-oh", "pittsburgh-pa", "detroit-ann-arbor-mi",
                  "indianapolis-in", "louisville-ky", "milwaukee-wi",
                  "st-louis-mo"):
        other_doc = _load(PACKAGE / "identity_census" / (other + ".json"))
        for key in sorted(ours & census.identity_keys(other_doc)):
            assert (key, other) in recorded, (
                "unrecorded cross-market identity collision: %s x %s"
                % (key, other))

    package_path = PACKAGE / ("hotel_policy_facts_" + MARKET + ".json")
    if package_path.exists():
        package = _load(package_path)
        assert package["market_id"] == MARKET
        assert package["count"] == len(package["hotels"])
    exclusions = [x for x in _load(PACKAGE / "hotel_exclusions.json")["exclusions"]
                  if x.get("market_id") == MARKET]
    for row in exclusions:
        assert row["market_id"] == MARKET
    # And no other market gained a row carrying this market's id.
    mine = {x["normalized_name"] for x in exclusions}
    for other in ("columbus-oh", "cleveland-akron-canton-oh", "dayton-oh",
                  "louisville-ky", "milwaukee-wi", "st-louis-mo"):
        other_rows = {x["normalized_name"] for x
                      in _load(PACKAGE / "hotel_exclusions.json")["exclusions"]
                      if x.get("market_id") == other}
        assert mine.isdisjoint(other_rows), other


def test_routing_repair_reconciles_the_fixed_active_universe():
    progress = _load(PACKAGE / "grand_rapids_holland_identity_routing_repair_001_progress.json")
    assert progress["total_universe"] == 119
    assert progress["processed"] + progress["remaining"] == 119
    assert (progress["route_confirmed"] + progress["url_recovery"] +
            progress["identity_review"] + progress["census_review"] +
            progress["routing_unresolved"]) == 119
    assert progress["route_confirmed"] == 110
    assert progress["url_recovery"] == 0
    assert progress["census_review"] == 0
    assert progress["routing_unresolved"] == 9
    # The progress report above is HISTORY and every number in it still holds.
    # The SHARD is live authority, and PTF-GRAND-RAPIDS-SOURCE-PROMOTION-022
    # withdrew the 31 routes that publication answered -- a route exists to
    # find a hotel's page, and the seed row is the source of truth once we
    # publish it. So the repair's 110 confirmations reconcile as 79 still
    # asking a question plus 31 answered, and the withdrawn records are
    # archived whole in that work order's report.
    routing = _load(PACKAGE / "markets" / "authority" / MARKET / "identity_routing.json")
    routes = routing["routes"]
    package_path = PACKAGE / ("hotel_policy_facts_" + MARKET + ".json")
    published = ({row["identity_key"] for row in _load(package_path)["hotels"]}
                 if package_path.exists() else set())
    withdrawn = _load(PACKAGE / "grand_rapids_holland_mi_source_promotion_022.json"
                      )["routes_withdrawn_by_publication"]
    # EACH PASS PINS ITS OWN END STATE, not the market's forever. 022 withdrew
    # 31 of the repair's 110 confirmations and ended at 79 -- that is a fact
    # about 022 and stays true. PTF-GRAND-RAPIDS-FOUNDER-SIGNATURE-PASS-030
    # then published five more hotels and withdrew the four of them that
    # carried a route, ending at 75. Asserting 022's end state as the CURRENT
    # count is what made this test fail the moment the market published again.
    assert withdrawn["routes_after"] == 79
    assert withdrawn["routes_for_a_published_identity_in_the_end_state"] == 0
    promotion_030 = _load(
        PACKAGE / "grand_rapids_holland_mi_source_promotion_030.json"
    )["routes_withdrawn_by_publication"]
    assert promotion_030["routes_after"] == 75
    assert promotion_030["routes_for_a_published_identity_in_the_end_state"] == 0
    # 031 cleared 030's three fee-cap holds, published them, and withdrew the
    # routes they answered: 75 -> 72. Each pass pins its own end state and the
    # LIVE shard is whatever the newest promotion left.
    promotion_031 = _load(
        PACKAGE / "grand_rapids_holland_mi_source_promotion_031.json"
    )["routes_withdrawn_by_publication"]
    assert len(routes) == promotion_031["routes_after"] == 72
    assert promotion_031["routes_for_a_published_identity_in_the_end_state"] == 0
    assert routing["count"] == len(routes)
    assert {row["hotel_ref"]["identity_key"] for row in routes} <= census.identity_keys(census_doc())
    assert len({row["official_property_url"] for row in routes}) == len(routes)
    # No route survives for a hotel this market now publishes.
    assert not ({row["hotel_ref"]["normalized_name"] for row in routes} & published)
    queue = _load(PACKAGE / "grand_rapids_holland_capture_ready_queue_002.json")
    assert queue["count"] == len(queue["items"]) == 110
    assert all(row["review_status"] == "NOT_STARTED" for row in queue["items"])
    review = _load(PACKAGE / "grand_rapids_holland_postclosure_census_review_001.json")
    assert review["census_count"] == 120
    assert review["active_lodging_count"] == 119
    assert review["current_routed_count"] == 67  # pre-continuation review baseline
    assert review["count"] == len(review["items"]) == 52
    assert review["reconciliation"] == {
        "property_level_url_recovery": 52,
        "structured_brand": 35,
        "independent_local": 17,
        "structured_brand_lanes": {
            "CHOICE": 5, "ESA": 2, "G6": 1, "HILTON": 9, "IHG": 3,
            "MARRIOTT": 4, "RADISSON": 5, "RED_ROOF": 1, "WOODSPRING": 1,
            "WYNDHAM": 4,
        },
    }
    assert review["review_partitions"] == {
        "ROUTING_RECOVERY_CLEAN": 35,
        "FOUNDER_IDENTITY_REVIEW": 0,
        "CLOSED_CONVERSION_REVIEW": 0,
        "ROUTING_UNRESOLVED": 0,
        "INDEPENDENT_FINAL_RECOVERY": 17,
    }
    assert review["routing_continuation_plan"]["next_batch_count"] == 35
    unresolved_keys = {
        row["identity_key"] for row in _load(
            PACKAGE / "markets" / "reports" / (MARKET + "_routing_results_001.json")
        )["rows"] if row["verdict"] == "ROUTING_UNRESOLVED"
    }
    independent_final = _load(PACKAGE / "grand_rapids_holland_independent_routing_final_001.json")
    assert len(independent_final["items"]) == 17
    assert unresolved_keys == {row["identity_key"] for row in independent_final["items"]
                              if row["outcome"] == "ROUTING_UNRESOLVED"}
    assert sum(row["outcome"] == "PROPERTY_LEVEL_ROUTE_CONFIRMED"
               for row in independent_final["items"]) == 8
    continuation = progress["continuation_003"]
    assert continuation["structured_recovery_batch"] == 35
    assert continuation["structured_routes_added"] == 35
    assert continuation["structured_census_review"] == 0
    assert continuation["structured_remaining"] == 0
    assert continuation["independent_final_recovery_deferred"] == 0
    assert continuation["independent_final_routed"] == 8
    assert continuation["independent_final_unresolved"] == 9
    assert continuation["reconciliation"] == {
        "active_lodging": 119,
        "structured_route_confirmed": 35,
        "structured_remaining": 0,
        "structured_census_review": 0,
        "independent_final_routed": 8,
        "independent_final_unresolved": 9,
    }
    assert all(row["census_action"] == "NO_CHANGE" for row in review["items"])

    census_review = _load(PACKAGE / "grand_rapids_holland_census_review_002.json")
    assert census_review["census_before"] == census_review["census_after"] == 120
    assert census_review["summary"] == {
        "NO_CENSUS_CHANGE": 0,
        "RENAME_IN_PLACE": 4,
        "ADDRESS_CORRECTION": 1,
        "BRAND_CONVERSION_IN_PLACE": 0,
        "CLOSED_OR_CONVERTED": 0,
        "CONFIRMED_DUPLICATE": 0,
        "IDENTITY_UNRESOLVED": 0,
        "FOUNDER_IDENTITY_REVIEW": 0,
    }
    assert all(not row["policy_observed"] for row in census_review["items"])

    capture_batch = _load(PACKAGE / "grand_rapids_holland_claude_capture_batch_001.json")
    assert capture_batch["count"] == len(capture_batch["items"]) == 25
    assert all(row["capture_mode"] == "FRESH_SESSION_REQUIRED" and
               row["review_status"] == "NOT_STARTED" for row in capture_batch["items"])


def test_grand_rapids_claude_capture_pass1_is_complete_and_capture_only():
    from scripts.pettripfinder.contracts.policy_schema import validate_facts
    capture = _load(PACKAGE / "grand_rapids_holland_capture_pass1_001.json")
    packet = _load(PACKAGE / "grand_rapids_holland_capture_pass1_founder_review_packet.json")
    index = _load(PACKAGE / "grand_rapids_holland_capture_pass1_artifact_index.json")

    rows = capture["terminal_rows"]
    assert capture["queue_total"] == capture["processed"] == len(rows) == 25
    assert capture["remaining"] == 0
    assert {row["terminal_outcome"] for row in rows} <= {
        "PUBLICATION_CANDIDATE", "VERIFIED_NO_PETS_CANDIDATE",
        "POLICY_NOT_FOUND", "ACCESS_BLOCKED", "IDENTITY_UNCERTAIN",
        "CAPTURE_FAILED", "SOURCE_AMBIGUOUS",
    }
    assert [row["queue_position"] for row in rows] == list(range(1, 26))
    assert all(row["artifact_sha256"].startswith("sha256:") and
               row["exact_contiguous_quote"] and
               row["artifact_class"] == "TRANSCRIPTION_ONLY"
               for row in rows)
    assert len(index["artifacts"]) == 25
    assert all(item["quote_contiguous"] for item in index["artifacts"])
    for row in rows:
        facts = {entry["field"]: entry["value"]
                 for entry in row["proposed_schema_1_2_facts"]}
        assert not validate_facts(facts)
    assert packet["approval_status"] == "NOT_REQUESTED"
    assert len(packet["decisions"]) == 24


def test_grand_rapids_pass1_evidence_grade_reconciliation_is_narrow():
    report = _load(PACKAGE / "grand_rapids_holland_capture_pass1_evidence_grade_reconciliation_001.json")
    recapture = _load(PACKAGE / "grand_rapids_holland_capture_pass1_recapture_queue_001.json")

    assert report["capture_total"] == 25
    assert report["actionable_candidates"] == 24
    assert report["publication_grade_before"] == report["publication_grade_after"] == 0
    assert report["classification_counts"] == {
        "ARTIFACT_INSUFFICIENT": 24,
        "POLICY_NOT_FOUND": 1,
    }
    assert report["mechanical_defect_fixed"] is False
    assert report["authority_changed"] is False
    assert len(report["rows"]) == 25
    assert recapture["count"] == len(recapture["items"]) == 24
    assert all(item["review_status"] == "NOT_STARTED" for item in recapture["items"])


def test_grand_rapids_publication_evidence_recapture_preserves_the_bar():
    report = _load(PACKAGE / "grand_rapids_holland_pass1_publication_evidence_recapture_001.json")
    progress = _load(PACKAGE / "grand_rapids_holland_pass1_publication_evidence_recapture_001_progress.json")

    assert report["recapture_total"] == report["recaptured"] == len(report["rows"]) == 24
    assert report["publication_grade"] == 0
    assert report["capture_failed"] == report["artifact_insufficient_remaining"] == 24
    assert report["screenshot_artifacts"] == report["other_accepted_rendered_artifacts"] == 0
    assert report["authority_changed"] is False
    assert report["founder_review_ready"] is False
    assert all(row["terminal_outcome"] == "CAPTURE_FAILED" and
               not row["quote_contiguous_in_attempted_html"]
               for row in report["rows"])
    assert progress["processed"] == 24 and progress["remaining"] == 0
