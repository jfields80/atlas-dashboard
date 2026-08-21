"""PTF-HILTON-023 CLOSURE.

023 measured the Hilton lane; 024 and 025 then changed what its records say.
This closes it from the artifacts on disk.

WHAT THESE TESTS GUARD
----------------------
That closing an experiment does not mean re-running it. Every input was
persisted, so the closure spends nothing, and a test asserts that rather than
trusting the report's own claim.

That the recovery rate is honest in both directions. Firecrawl lost seven
subjects, but one of those pages publishes no terms for any provider to
recover -- counting it as a recovery opportunity understates the Browser API,
and quietly dropping it from the failure count would flatter it. Both
denominators are pinned.

And that closure changed nothing it had no business changing: 025's store stays
at 101, Hilton stays at 25, the historical 023 reports keep the numbers they
measured, and no route moves because the committed one already matches.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import hilton_closure_023 as CL      # noqa: E402
from scripts.pettripfinder.acquisition import hilton_decision_023 as H      # noqa: E402
from scripts.pettripfinder.acquisition import providers as PROVIDERS        # noqa: E402
from scripts.pettripfinder.acquisition import registry as REGISTRY          # noqa: E402


def closure():
    return json.loads(CL.CLOSURE_REPORT.read_text(encoding="utf-8-sig"))


def store():
    return json.loads(CL.STORE.read_text(encoding="utf-8-sig"))


# --------------------------------------------------------------------------- #
# 1, 3. Existing results are used; nothing is re-acquired.
# --------------------------------------------------------------------------- #

def test_the_closure_made_no_provider_call():
    doc = closure()
    assert doc["provider_calls_made"] == 0
    assert doc["evidence_completeness"]["provider_calls_required"] == 0
    assert doc["evidence_completeness"]["missing"] == []


def test_the_control_evidence_was_already_complete_on_disk():
    """The reason no call was needed, checked against the files themselves."""
    blocks = list((CL.DATA / "hilton-decision-023-control").rglob("policy-block.txt"))
    assert len(blocks) == 7
    journal = CL.DATA / "hilton-decision-023-control" / "control-journal.jsonl"
    assert journal.is_file()
    rows = [l for l in journal.read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(rows) == 7


def test_the_firecrawl_phase_wrote_no_artifact_and_that_is_the_result():
    """Zero blocks is the measurement, not a gap that needs re-running."""
    blocks = list((CL.DATA / "hilton-decision-023").rglob("policy-block.txt"))
    assert blocks == []
    assert closure()["decision_cohort"]["firecrawl_acquired"] == 0


def test_the_production_run_was_not_rerun():
    doc = closure()
    assert doc["production"]["reran_production"] is False
    assert doc["production"]["acquired"] == 11
    blocks = list((CL.DATA / CL.PRODUCTION_RUN).rglob("policy-block.txt"))
    assert len(blocks) == 11


# --------------------------------------------------------------------------- #
# 2. The cohort is historically fixed.
# --------------------------------------------------------------------------- #

def test_the_decision_cohort_is_the_one_023_actually_ran():
    cohort = closure()["decision_cohort"]
    assert cohort["cohort_size"] == 7
    assert cohort["sub_brands"] == ["HOME2_SUITES", "HOMEWOOD_SUITES",
                                    "SPARK", "TRU"]
    recorded = json.loads(CL.FIRECRAWL_PHASE.read_text(encoding="utf-8-sig"))
    assert [r["canonical_name"] for r in cohort["rows"]] == \
        [r["canonical_name"] for r in recorded["firecrawl_rows"]]


def test_every_decision_subject_had_a_sound_source():
    """No failure is charged to a bad URL."""
    cohort = closure()["decision_cohort"]
    assert cohort["source_readiness"] == {"SOURCE_READY": 7}


def test_every_firecrawl_failure_is_an_access_failure():
    cohort = closure()["decision_cohort"]
    assert cohort["failure_causes"] == {H.FIRECRAWL_ACCESS_FAILURE: 7}
    assert all(not r["artifact_written"] for r in cohort["rows"])


# --------------------------------------------------------------------------- #
# 4. The decision follows the measured recovery.
# --------------------------------------------------------------------------- #

def test_the_browser_api_acquired_every_control_subject():
    ctrl = closure()["bright_data_control"]
    assert ctrl["control_subjects"] == 7
    assert ctrl["browser_acquired"] == 7
    assert all(r["identity_confirmed"] for r in ctrl["rows"])


def test_a_page_with_no_terms_is_not_a_recovery_opportunity():
    """Counting it would understate the lane; dropping it silently would
    flatter it. Both denominators are reported."""
    ctrl = closure()["bright_data_control"]
    assert ctrl["excluded_from_denominator"] == ["Spark by Hilton Milwaukee Airport"]
    assert ctrl["provider_attributable_firecrawl_failures"] == 7
    assert ctrl["recovery_opportunities"] == 6
    assert ctrl["browser_recoveries"] == 6
    assert ctrl["recovery_rate_over_opportunities"] == 1.0
    assert ctrl["recovery_rate_over_attributable_failures"] == pytest.approx(0.857,
                                                                            abs=0.001)


def test_page_level_causes_are_excluded_from_the_denominator():
    assert H.GENERIC_BRAND_ONLY in CL.PAGE_LEVEL_CAUSES
    assert H.POLICY_NOT_PRESENT in CL.PAGE_LEVEL_CAUSES
    assert H.FIRECRAWL_ACCESS_FAILURE not in CL.PAGE_LEVEL_CAUSES


def test_the_decision_is_retain_browser():
    assert closure()["final_decision"] == H.RETAIN_BROWSER


# --------------------------------------------------------------------------- #
# 5, 12. The route already matched, so nothing moved.
# --------------------------------------------------------------------------- #

def test_the_current_hilton_route_matches_the_decision():
    route = closure()["route"]
    assert route["status"] == CL.ROUTE_ALREADY_CORRECT
    assert route["routes_json_change_required"] is False
    live = REGISTRY.resolve(brand="HILTON", url="https://www.hilton.com/x")
    assert live.provider == PROVIDERS.BRIGHTDATA_BROWSER
    assert live.ladder == (PROVIDERS.BRIGHTDATA_BROWSER,
                           PROVIDERS.BRIGHTDATA_WEB_UNLOCKER)
    assert live.reader == "hilton_competing"


def test_no_route_file_was_touched():
    changed = subprocess.run(
        ["git", "status", "--porcelain", "--",
         "atlas-dashboard/scripts/pettripfinder/acquisition/routes.json"],
        cwd=str(REPO.parent), capture_output=True, text=True).stdout.strip()
    assert changed == ""


def test_no_unrelated_brand_route_changed():
    for brand, provider in (("MARRIOTT", PROVIDERS.BRIGHTDATA_BROWSER),
                            ("CHOICE", PROVIDERS.FIRECRAWL),
                            ("WYNDHAM", PROVIDERS.FIRECRAWL),
                            ("IHG", PROVIDERS.FIRECRAWL),
                            ("MOTEL6", PROVIDERS.BRIGHTDATA_BROWSER),
                            ("RED_ROOF", PROVIDERS.BRIGHTDATA_BROWSER)):
        assert REGISTRY.resolve(brand=brand,
                                url="https://example.com/x").provider == provider


# --------------------------------------------------------------------------- #
# 6, 7. History preserved; current semantics stated separately.
# --------------------------------------------------------------------------- #

def test_the_historical_023_reports_were_not_rewritten():
    for path in ("ptf_hilton_decision_023.json",
                 "ptf_hilton_decision_023_firecrawl.json",
                 "ptf_hilton_milwaukee_run_023.json",
                 "milwaukee-wi_counts_023.json"):
        changed = subprocess.run(
            ["git", "status", "--porcelain", "--",
             "atlas-dashboard/launch_packages/pettripfinder/markets/reports/" + path],
            cwd=str(REPO.parent), capture_output=True, text=True).stdout.strip()
        assert changed == "", "%s was rewritten" % path
    assert closure()["historical_reports_rewritten"] is False


def test_the_closure_states_both_readings():
    """What 023 observed, and what HEAD says now -- never one for the other."""
    semantics = closure()["semantics"]
    assert semantics["records"] == 10
    assert semantics["historical_report_rewritten"] is False
    for row in semantics["rows"]:
        assert "observed_at_023" in row and "current_under_head" in row
    assert semantics["fee_assertion_changed"] == 6
    assert semantics["held_schema_cannot_represent"] == 9


def test_024_semantics_are_the_current_reading():
    rows = [i for i in store()["items"]
            if i.get("source_run") == CL.PRODUCTION_RUN]
    held = [i for i in rows
            if i["withheld_fields"].get("pet_fee") == "SCHEMA_CANNOT_REPRESENT"]
    laddered = [i for i in rows if (i["proposed_facts"] or {}).get("fee_tiers")]
    # NARROWED by work order 034. These nine rows were held because Hilton
    # prices its pets in duration bands and the reader could only refuse them;
    # they now carry the ladder as fee_tiers, which is what 023's own evidence
    # always said. The claim that survives -- and the one 024 was about -- is
    # that not one of them publishes a single amount for a banded price.
    assert len(held) + len(laddered) == 9
    for row in held + laddered:
        assert "pet_fee" not in row["proposed_facts"]
    for row in held:
        assert row["review_status"] == "HELD_SCHEMA_CANNOT_REPRESENT"


# --------------------------------------------------------------------------- #
# 8, 9. 025's store is left exactly as it was.
# --------------------------------------------------------------------------- #

def test_the_closure_added_no_store_rows():
    """The closure measured 101 and wrote none of them.

    PTF-MILWAUKEE-FINAL-ACQUISITION-PASS-026 later acquired the last sixteen
    properties and the store grew, which is that work order's doing. What
    remains true of the closure is that its own contribution was zero: it
    recorded the count it saw and added nothing to it.
    """
    assert closure()["store_rows"] == 101
    rows = [i for i in store()["items"]
            if i.get("source_run") == CL.PRODUCTION_RUN]
    assert len(rows) == 10


def test_hilton_current_state_rows_stay_at_25():
    rows = [i for i in store()["items"] if i.get("brand") == "HILTON"]
    assert len(rows) == 25
    doc = closure()["production"]
    assert doc["hilton_rows_in_store_total"] == 25
    assert doc["hilton_rows_by_run"] == {"milwaukee-router-001": 15,
                                         "hilton-milwaukee-023": 10}


def test_the_ten_publication_grade_rows_are_the_ten_in_the_store():
    prod = closure()["production"]
    assert prod["publication_grade"] == 10
    assert prod["rows_in_current_store"] == 10
    assert prod["the_ten_match_the_store"] is True


def test_the_excluded_property_is_named_with_its_reason():
    excluded = closure()["production"]["excluded"]
    assert len(excluded) == 1
    row = excluded[0]
    assert row["canonical_name"] == "Spark by Hilton Milwaukee Airport"
    assert row["final_state"] == "ACQUIRED_NONPUBLICATION_GRADE"
    assert row["policy_block"] == "Pets allowed Yes"


# --------------------------------------------------------------------------- #
# The counter correction.
# --------------------------------------------------------------------------- #

def test_the_counter_correction_names_025_as_the_authority():
    counters = closure()["counters"]
    assert counters["authority"].endswith("025")
    assert counters["current"]["touched"] == 111
    assert counters["current"]["never_touched"] == 16
    assert counters["current"]["routable"] == 127
    assert counters["current"]["observed"] == 101
    assert counters["current"]["published"] == 0
    assert counters["never_touched_now"] == {"MOTEL6": 4, "independents": 11,
                                             "RED_ROOF": 1}


def test_the_historical_counter_artifact_keeps_its_own_number():
    counters = closure()["counters"]
    assert counters["historical_artifact_rewritten"] is False
    assert counters["as_reported_by_023"]["touched"] == 95


# --------------------------------------------------------------------------- #
# 10, 11. Authority and publication.
# --------------------------------------------------------------------------- #

def test_no_milwaukee_policy_authority_exists():
    found = list((REPO / "launch_packages" / "pettripfinder")
                 .rglob("*hotel_policy_facts*milwaukee*"))
    assert not found, found
    assert closure()["authority_written"] is False


def test_nothing_is_published():
    assert closure()["published"] is False
    assert sum(1 for i in store()["items"] if i.get("published")) == 0
    assert sum(1 for i in store()["items"] if i.get("founder_approved")) == 0


def test_the_cost_is_attributed_to_023_alone():
    cost = closure()["cost"]
    assert cost["attributed_to_023_only"] is True
    assert cost["firecrawl_credits"] == 0
    assert cost["browser_api_requests"] == 18      # 7 control + 11 production
    assert "meter_lag_caveat" in cost
