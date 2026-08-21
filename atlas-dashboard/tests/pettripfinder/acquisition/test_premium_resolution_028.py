"""PTF-HYATT-BEST-WESTERN-PREMIUM-RESOLUTION-028.

WHAT THESE TESTS GUARD
----------------------
Two things, and the second is the one that has been wrong all year.

The first is the bucket: exactly six identities, both premium brands, derived
from the committed queue rather than typed out, and no third brand allowed to
drift in behind them.

The second is the DENOMINATOR. ``observed + unresolved == 127`` was an equation
about the routable subset and it was reported for four work orders as though it
were the market. The market is 147. These tests require every census identity
to appear in exactly one final state and the states to sum to 147, so a future
run cannot quietly answer the smaller question again.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import premium_resolution_028 as P
from scripts.pettripfinder.acquisition import readers as READERS
from scripts.pettripfinder.acquisition import registry as REGISTRY
from scripts.pettripfinder.brightdata import cross_brand_pilot_002 as P2
from scripts.pettripfinder.brightdata import policy_surface as PS
from pettripfinder.acquisition import reader_freeze as READER_FREEZE


# --------------------------------------------------------------------------- #
# 1 / 2 -- the six, and only the six.
# --------------------------------------------------------------------------- #

def test_the_excluded_bucket_is_exactly_six_and_is_derived():
    rows = P.assert_bucket()
    assert len(rows) == 6
    doc = json.loads(P.QUEUE_PATH.read_text(encoding="utf-8-sig"))
    derived = [row["identity_key"] for row in doc["items"]
               if row["brand_excluded"]]
    assert sorted(derived) == sorted(row["identity_key"] for row in rows)
    assert doc["brand_excluded_total"] == 6


def test_no_brand_outside_the_premium_pair_enters_this_work_order():
    brands = {row["brand"] for row in P.assert_bucket()}
    assert brands == {"HYATT", "BEST_WESTERN"}
    assert sorted(REGISTRY.excluded_brands()) == ["BEST_WESTERN", "HYATT"]
    for row in P.journal_rows():
        assert row["brand"] in P.PREMIUM_BRANDS


def test_the_bucket_is_a_cost_exclusion_not_a_capability_one():
    """Why this could be reopened at all.

    Every row's recorded reason names the Bright Data plan. Nothing in the
    resolver ever refused these brands -- ``excluded_brands`` is advisory -- so
    the lane was always there and the plan was the only thing in the way.
    """
    for row in P.assert_bucket():
        assert "premium domain" in row["brand_exclusion_reason"]
        route = REGISTRY.resolve(brand=row["brand"], url=row["official_url"])
        assert route.provider == "brightdata_browser"


# --------------------------------------------------------------------------- #
# 3 -- active versus retired.
# --------------------------------------------------------------------------- #

def test_every_excluded_identity_gets_exactly_one_disposition():
    entries = P.classified()
    assert len(entries) == 6
    allowed = {P.ACTIVE, P.RETIRED, P.DUPLICATE, P.CATEGORY_EXCLUDED,
               P.BOUNDARY_EXCLUDED, P.IDENTITY_UNRESOLVED}
    for entry in entries:
        assert entry["disposition"] in allowed
        assert entry["acquisition_required"] == (entry["disposition"] == P.ACTIVE)


def test_disposition_is_read_from_the_census_never_decided_here():
    """A property is ACTIVE because the census says so, not because we want it."""
    for entry in P.classified():
        if entry["disposition"] != P.ACTIVE:
            continue
        assert entry["identity_state"] == "IDENTITY_CONFIRMED"
        assert entry["lodging_state"] == "LODGING_CONFIRMED"
        assert entry["census_disposition"] == "canonical"
        assert entry["partition_state"] == "AWAITING_POLICY_OBSERVATION"
        assert entry["valid_lodging_inventory"] is True


def test_a_previously_held_best_western_is_not_dragged_in_by_the_brand():
    """Historical identity disposition stays controlling.

    The census carries a fourth Best Western whose identity is UNRESOLVED --
    the state registry lists it, the brand's own sitemap does not. Premium
    access says nothing about whether that property exists, so it stays out.
    """
    census = P.census()
    held = census["best western plus milwaukee west"]
    assert held["identity_state"] == "IDENTITY_UNRESOLVED"
    assert held["identity_key"] not in {row["identity_key"]
                                        for row in P.assert_bucket()}
    assert held["identity_key"] not in {row["identity_key"]
                                        for row in P.journal_rows()}


# --------------------------------------------------------------------------- #
# 4 / 5 -- the lane.
# --------------------------------------------------------------------------- #

def test_every_active_property_runs_the_premium_browser_lane():
    for entry in P.classified():
        if not entry["acquisition_required"]:
            continue
        resolved = P.lane(entry)
        assert resolved["provider"] == "brightdata_browser"
        assert resolved["premium_domain"] is True
        assert resolved["ladder"][0] == "brightdata_browser"


def test_no_firecrawl_first_experiment_is_performed():
    """Not "Firecrawl lost the comparison" -- it was never in the ladder."""
    for entry in P.classified():
        if not entry["acquisition_required"]:
            continue
        assert P.lane(entry)["firecrawl_in_ladder"] is False
    for row in P.journal_rows():
        providers = [record.get("provider")
                     for record in row.get("attempt_records") or ()]
        assert "firecrawl" not in providers
        assert providers[0] == "brightdata_browser"


def test_only_the_committed_fallback_was_used():
    permitted = {"brightdata_browser", "brightdata_web_unlocker"}
    for row in P.journal_rows():
        assert set(row["providers_tried"]) <= permitted


# --------------------------------------------------------------------------- #
# Source verification, and the identity brand.
# --------------------------------------------------------------------------- #

def test_source_verification_binds_the_property_code_without_reading_policy():
    for entry in P.classified():
        if not entry["acquisition_required"]:
            continue
        check = P.verify_source(entry)
        assert check["first_party_host"] is True
        assert check["code_binding"] is True
        assert check["code_in_url"] == check["code_in_census"]
        assert check["verified"] is True
        assert check["policy_wording_inspected"] is False


def test_both_premium_brands_have_a_property_code_pattern():
    assert "HYATT" in PS.PROPERTY_CODE_PATTERNS
    assert "BEST_WESTERN" in PS.PROPERTY_CODE_PATTERNS
    assert PS.property_code(
        "https://www.hyatt.com/hyatt-place/en-US/mkeza-x", "HYATT") == "mkeza"
    assert PS.property_code(
        "https://www.bestwestern.com/en_US/book/hotels-in-x/y/"
        "propertyCode.50056.html", "BEST_WESTERN") == "50056"


def test_the_identity_brand_is_not_the_locator_brand():
    """The defect this run surfaced, pinned.

    A route may read a coded brand with the GENERIC walk, and both Hyatt and
    Best Western do. The capture then received an empty brand, re-derived the
    property code as empty, compared it to a real expected code and threw away
    three perfect Best Western pages as UNEXPECTED_PAGE. Two concepts, two
    fields.
    """
    assert READERS.locator_brand_for("generic") == ""
    row = P.queue()["best western germantown inn"]
    target = P2.target_for(P._record_for(row))
    assert target.identity_brand == "BEST_WESTERN"
    assert target.property_code == "50140"
    assert PS.property_code(target.requested_url, target.identity_brand) \
        == target.property_code


def test_every_branded_capture_still_agrees_on_both_brands():
    """For a brand whose reader names it, the two brands are the same string."""
    for reader_id, brand in (("marriott", "MARRIOTT"), ("ihg", "IHG"),
                             ("choice_static", "CHOICE"),
                             ("hilton_competing", "HILTON")):
        assert READERS.locator_brand_for(reader_id) == brand


# --------------------------------------------------------------------------- #
# 6 / 7 -- locator persistence and reader semantics.
# --------------------------------------------------------------------------- #

def test_the_canonical_locator_persisted_for_every_publication_grade_row():
    from scripts.pettripfinder.brightdata import policy_locator as PL
    assert PL.CONTRACT == "ptf-policy-locator/1.0"
    graded = [row for row in P.journal_rows() if row["publication_grade"]]
    assert graded
    for row in graded:
        artifacts = row["canonical_artifacts"]
        assert artifacts["present"] is True
        assert artifacts["policy_block"] is True
        assert artifacts["locator_json"] is True
        assert artifacts["replay_status"] == "REPLAYED_FROM_CANONICAL_ARTIFACT"
        assert artifacts["canonical"] is True


def test_no_reader_gate_was_relaxed_for_the_premium_bucket():
    """028 published nothing the reader had not represented.

    It used to say so by freezing ``policy_reading.py``. 029 was commissioned
    to change that file -- the two Best Western pages state a count, a weight
    and a daily rate the reader was missing -- so the claim is made through the
    protections themselves instead, which is what it was ever about.

    The two rows are no longer HELD, and that is the point of 029: the fee is
    now REPRESENTED rather than guessed. What must still hold is that every
    held row names what it withheld.
    """
    READER_FREEZE.assert_reader_protections_unchanged()
    store = json.loads(P.STORE.read_text(encoding="utf-8-sig"))
    premium = [row for row in store["items"]
               if row["source_run"] == P.RUN_ID]
    assert premium
    for row in premium:
        if row["review_status"] == "HELD_INSUFFICIENT_EVIDENCE":
            assert row["withheld_fields"]
    READER_FREEZE.assert_reader_protections_unchanged()

def test_a_refusal_the_regex_missed_is_still_read_as_a_refusal():
    """Best Western writes "Pets are not accepted", which no pattern matched.

    The reader extracted ``pets_allowed = False`` and the store records a
    refusal. The usable-policy checks now ask the reader rather than the regex,
    so a complete answer stopped failing the shell check for being short.
    """
    store = json.loads(P.STORE.read_text(encoding="utf-8-sig"))
    row = next(item for item in store["items"]
               if item["identity_key"] == "best western germantown inn")
    assert row["is_refusal"] is True
    assert row["proposed_facts"]["pets_allowed"] is False
    assert row["review_status"] == "REFUSAL_FOUNDER_REVIEW"


# --------------------------------------------------------------------------- #
# 7 / 8 -- the premium audit keeps access apart from content.
# --------------------------------------------------------------------------- #

def test_a_page_that_arrived_is_never_called_a_provider_failure():
    for audit in P.audits():
        if audit["page_reached"]:
            assert audit["verdict"] != P.PREMIUM_ACCESS_FAILURE


def test_every_audit_verdict_is_from_the_declared_taxonomy():
    allowed = {P.PREMIUM_ACCESS_SUCCESS,
               P.PREMIUM_ACCESS_BUT_POLICY_NOT_PRESENT,
               P.PREMIUM_ACCESS_BUT_READER_OR_LOCATOR_ISSUE,
               P.PREMIUM_ACCESS_FAILURE}
    audits = P.audits()
    assert len(audits) == 6
    for audit in audits:
        assert audit["verdict"] in allowed
        assert audit["correct_identity"] is True


# --------------------------------------------------------------------------- #
# 8 -- the store.
# --------------------------------------------------------------------------- #

def test_the_store_keeps_one_row_per_identity():
    store = json.loads(P.STORE.read_text(encoding="utf-8-sig"))
    keys = [row["identity_key"] for row in store["items"]]
    assert len(keys) == len(set(keys))


def test_only_publication_grade_rows_reached_the_store():
    store = json.loads(P.STORE.read_text(encoding="utf-8-sig"))
    in_store = {row["identity_key"] for row in store["items"]
                if row["source_run"] == P.RUN_ID}
    graded = {row["identity_key"] for row in P.journal_rows()
              if row["publication_grade"]}
    assert in_store == graded


def test_the_integration_never_removes_or_duplicates_a_row():
    """What 028 added is pinned from the store; the report belongs to whoever
    ran the integration last.

    ``changed_facts`` was asserted empty because 028 only added. 029 then
    re-derived four identities from their persisted evidence, which is a
    legitimate change to the same shared report, so the invariants that survive
    a later integration are asserted here and 028's own contribution is pinned
    by source run.
    """
    doc = json.loads(
        (REPO / "atlas-dashboard" / "launch_packages" / "pettripfinder"
         / "markets" / "reports"
         / "ptf_milwaukee_store_integration_025.json").read_text(
            encoding="utf-8-sig"))
    assert doc["removed"] == []
    assert doc["duplicates"] == []
    assert doc["conflicts"] == []
    assert len({row["identity_key"] for row in
                json.loads(P.STORE.read_text(encoding="utf-8-sig"))["items"]
                if row["source_run"] == P.RUN_ID}) == 4


# --------------------------------------------------------------------------- #
# 9 / 10 -- the full census.
# --------------------------------------------------------------------------- #

def test_every_census_identity_appears_exactly_once():
    reconciliation = P.full_census()
    assert reconciliation["census_total"] == 147
    assert reconciliation["unique_identities"] == 147
    assert reconciliation["each_identity_exactly_once"] is True
    keys = [row["identity_key"] for row in reconciliation["rows"]]
    assert sorted(keys) == sorted(P.census())


def test_the_final_states_sum_to_147():
    reconciliation = P.full_census()
    assert reconciliation["sum_of_final_states"] == 147
    assert reconciliation["phase11_sum"] == 147
    assert reconciliation["phase11_final_states"]["CENSUS_TOTAL"] == 147


def test_the_old_127_equation_is_not_the_market_equation():
    """127 was the routable subset and was reported as though it were Milwaukee.

    The active-eligible total is the queue, not the census, and the census is
    larger than both. All three numbers are distinct and this test says so.
    """
    reconciliation = P.full_census()
    assert reconciliation["census_total"] == 147
    assert reconciliation["active_eligible_total"] == 133
    routable = sum(1 for row in P.queue().values()
                   if not row["brand_excluded"])
    assert routable == 127
    assert reconciliation["census_total"] != routable
    assert reconciliation["active_eligible_total"] != routable


def test_active_eligible_splits_into_observed_and_unresolved_exactly():
    reconciliation = P.full_census()
    assert (reconciliation["active_eligible_observed"]
            + reconciliation["active_eligible_unresolved"]
            == reconciliation["active_eligible_total"])


def test_acquisition_exceptions_are_kept_apart_from_census_dispositions():
    queues = P.exception_queue()
    active = queues["active_acquisition_exceptions"]
    non_active = queues["non_active_census_dispositions"]
    assert set(row["identity_key"] for row in active["queue"]).isdisjoint(
        row["identity_key"] for row in non_active["queue"])
    reconciliation = P.full_census()
    assert active["count"] == reconciliation["active_eligible_unresolved"]
    assert non_active["count"] == 14


def test_held_observations_are_not_counted_as_acquisition_failures():
    held = P.held_structured_data()
    queues = P.exception_queue()["active_acquisition_exceptions"]
    store = json.loads(P.STORE.read_text(encoding="utf-8-sig"))
    observed = {row["identity_key"] for row in store["items"]}
    for row in queues["queue"]:
        assert row["identity_key"] not in observed
    assert held["HELD_SCHEMA_CANNOT_REPRESENT"] >= 0
    assert held["CURRENT_STATE_CONFLICT"] == 0


# --------------------------------------------------------------------------- #
# 11 / 12 / 13 -- authority, publication, and unrelated routes.
# --------------------------------------------------------------------------- #

def test_no_milwaukee_policy_authority_exists():
    root = REPO / "atlas-dashboard" / "launch_packages" / "pettripfinder"
    assert list(root.rglob("*hotel_policy_facts*milwaukee*")) == []
    store = json.loads(P.STORE.read_text(encoding="utf-8-sig"))
    assert store["authority_written"] is False
    assert store["founder_approvals_created"] == 0


def test_nothing_is_published():
    store = json.loads(P.STORE.read_text(encoding="utf-8-sig"))
    assert all(not row.get("published") for row in store["items"])


def test_unrelated_routes_are_unchanged():
    from scripts.pettripfinder.acquisition import providers as PROVIDERS
    for brand, provider in (("HILTON", PROVIDERS.BRIGHTDATA_BROWSER),
                            ("MARRIOTT", PROVIDERS.BRIGHTDATA_BROWSER),
                            ("CHOICE", PROVIDERS.FIRECRAWL),
                            ("WYNDHAM", PROVIDERS.FIRECRAWL),
                            ("IHG", PROVIDERS.FIRECRAWL),
                            ("MOTEL6", PROVIDERS.BRIGHTDATA_BROWSER),
                            ("RED_ROOF", PROVIDERS.BRIGHTDATA_BROWSER)):
        assert REGISTRY.resolve(brand=brand,
                                url="https://example.com/x").provider == provider
    for path in ("atlas-dashboard/scripts/pettripfinder/acquisition/routes.json",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/registry.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/router.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/providers.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/readers.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/source_discovery.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/source_selection.py",
                 "atlas-dashboard/launch_packages/pettripfinder/identity_census",
                 "atlas-dashboard/launch_packages/pettripfinder/milwaukee_final_partition_001.json"):
        changed = subprocess.run(["git", "status", "--porcelain", "--", path],
                                 cwd=str(REPO), capture_output=True,
                                 text=True).stdout.strip()
        assert changed == "", "%s was modified by 028" % path
    READER_FREEZE.assert_reader_protections_unchanged()

def test_the_policy_locator_surface_is_untouched():
    from pettripfinder.acquisition import locator_freeze as LOCATOR_FREEZE
    LOCATOR_FREEZE.assert_locator_surface_unchanged()


def test_this_work_order_writes_only_under_its_own_run_directory():
    assert P.RUN_ROOT.name == P.RUN_ID
    assert P.JOURNAL.parent == P.RUN_ROOT
    assert P.RUN_DIR.parent == P.RUN_ROOT
    assert P.COST_PATH.parent == P.RUN_ROOT
