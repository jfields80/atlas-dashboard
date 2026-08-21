"""PTF-MARRIOTT-OBSERVATION-CLOSURE-022.

021 hardened the Marriott locator and left three records whose stored reading
disagrees with what the corrected locator and reader produce. This work order
confirmed the fix on one fresh live capture and superseded exactly those three.

WHAT THESE TESTS GUARD
----------------------
The live confirmation, because it is the only thing an offline differential
cannot establish: the Playwright walk needs a browser, and 021 could only prove
which container the selectors BIND, not that the live walk would reach it.

The three supersessions, because each is a different kind of change and
collapsing them would repeat the error 018 named -- re-parsing a stored block
is a re-derivation, selecting a different block changes what the record is
about.

And the safety behaviour, because the whole point is that no Marriott record
now asserts a fee its own surface contradicts.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import marriott_closure_022 as C     # noqa: E402
from scripts.pettripfinder.acquisition import marriott_decision_020 as D    # noqa: E402
from scripts.pettripfinder.acquisition import marriott_template_021 as T    # noqa: E402
from scripts.pettripfinder.acquisition import providers as PROVIDERS        # noqa: E402
from scripts.pettripfinder.acquisition import registry as REGISTRY          # noqa: E402
from scripts.pettripfinder.brightdata import marriott_surface as MS         # noqa: E402
from scripts.pettripfinder.brightdata import policy_locator as PL           # noqa: E402
from scripts.pettripfinder.contracts import enums                           # noqa: E402
from pettripfinder.acquisition import locator_freeze as LOCATOR_FREEZE

TRADE = "The Trade, Autograph Collection"
POPLAR = "Residence Inn by Marriott Milwaukee Brookfield at Poplar Creek"
SHERATON = "Sheraton Milwaukee Brookfield Hotel"


def live():
    return json.loads(C.CONFIRMATION.read_text(encoding="utf-8-sig"))


def supersession():
    return json.loads(C.SUPERSESSION.read_text(encoding="utf-8-sig"))


def record(name):
    return next(r for r in supersession()["records"]
                if r["canonical_name"] == name)


def counts():
    return json.loads(C.COUNTS.read_text(encoding="utf-8-sig"))


# --------------------------------------------------------------------------- #
# 1-3. The fresh live confirmation.
# --------------------------------------------------------------------------- #

def test_the_fresh_capture_used_the_accordion_locator():
    """What no offline differential could prove: the LIVE walk binds it."""
    doc = live()
    assert doc["passed"]
    assert doc["verdict"]["policy_locator"] == "pet_policy_accordion_panel"
    assert doc["subject"] == TRADE


def test_the_fresh_capture_took_the_registered_route_unoverridden():
    doc = live()
    assert doc["routing_overridden"] is False
    assert doc["route_used"]["provider"] == PROVIDERS.BRIGHTDATA_BROWSER
    assert doc["route_used"]["providers_tried"] == [PROVIDERS.BRIGHTDATA_BROWSER]


def test_the_fresh_block_contains_both_charge_components():
    block = live()["verdict"]["block_text"].lower()
    assert "deposit" in block and "$125" in block
    assert "$20" in block and "daily" in block
    # and the terms that must survive alongside them
    assert "weight" in block and "number of pets" in block


def test_every_live_gate_passed():
    doc = live()
    assert doc["verdict"]["failed_gates"] == []
    assert set(doc["verdict"]["gates"]) == {name for name, _ in C.LIVE_GATES}


def test_the_fresh_capture_replays_offline():
    doc = live()
    assert doc["verdict"]["replay_status"] == PL.REPLAYED
    assert doc["verdict"]["gates"]["replay_reproduces_the_block"]
    attempt = REPO / doc["verdict"]["attempt_dir"]
    assert (attempt / PL.BLOCK_ARTIFACT).is_file()
    assert (attempt / PL.LOCATOR_ARTIFACT).is_file()
    replayed = PL.replay(attempt)
    assert replayed.status == PL.REPLAYED
    assert replayed.text.strip() == doc["verdict"]["block_text"].strip()


def test_a_failed_live_confirmation_would_block_supersession(monkeypatch):
    """The gate is real: no confirmation, no supersession."""
    monkeypatch.setattr(C, "CONFIRMATION", REPO / "does-not-exist.json")
    with pytest.raises(SystemExit):
        C.build_supersession(live={"passed": False})


# --------------------------------------------------------------------------- #
# 4. History survives.
# --------------------------------------------------------------------------- #

def test_the_old_the_trade_reading_is_preserved_verbatim():
    old = record(TRADE)["superseded"]
    assert old["work_order"] == D.WORK_ORDER
    assert old["run_id"] == D.PRODUCTION_RUN_ID
    assert old["policy_locator"] == "generic_signal_walk"
    assert "Yes, pets are welcome at The Trade" in old["policy_block"]
    assert "pet_fee" in old["fields_asserted"]
    assert old["policy_block_sha256"]


def test_the_020_capture_still_exists_on_disk():
    """The fresh capture is an addition, not a replacement."""
    old_attempt = D._attempt_dir_for(T.RUN_ROOT, D._slug_of(TRADE))
    assert old_attempt is not None
    assert (old_attempt / PL.BLOCK_ARTIFACT).is_file()
    stored = (old_attempt / PL.BLOCK_ARTIFACT).read_text(encoding="utf-8")
    assert "Yes, pets are welcome at The Trade" in stored


def test_the_020_reports_and_journals_were_not_edited():
    for path in ("atlas-dashboard/launch_packages/pettripfinder/markets/reports/"
                 "ptf_marriott_milwaukee_run_020.json",
                 "atlas-dashboard/launch_packages/pettripfinder/markets/reports/"
                 "ptf_marriott_decision_020.json",
                 "atlas-dashboard/launch_packages/pettripfinder/markets/reports/"
                 "ptf_marriott_template_021.json",
                 "atlas-dashboard/launch_packages/pettripfinder/markets/reports/"
                 "ptf_marriott_rederivation_queue_021.json"):
        changed = subprocess.run(["git", "status", "--porcelain", "--", path],
                                 cwd=str(REPO.parent), capture_output=True,
                                 text=True).stdout.strip()
        assert changed == "", "%s was modified by 022" % path


def test_the_lineage_is_mechanically_inspectable():
    """020 observed -> 021 proved the defect -> 022 confirmed -> superseded."""
    for name in (TRADE, POPLAR, SHERATON):
        lineage = record(name)["lineage"]
        assert [step["event"] for step in lineage] == [
            "observed", "locator_defect_proved",
            "corrected_locator_confirmed_live", "superseded"]
        assert lineage[0]["work_order"] == D.WORK_ORDER
        assert lineage[1]["work_order"] == T.WORK_ORDER
        assert lineage[2]["work_order"] == C.WORK_ORDER
        assert lineage[3]["work_order"] == C.WORK_ORDER
        # The hashes tie each step to the bytes it was about.
        assert lineage[0]["policy_block_sha256"]
        assert lineage[3]["policy_block_sha256"]


# --------------------------------------------------------------------------- #
# 5-7. The safety behaviour, per record.
# --------------------------------------------------------------------------- #

def test_the_trade_no_longer_asserts_an_understated_simple_fee():
    current = record(TRADE)["current"]
    assert "pet_fee" not in current["extraction"]
    assert "fee_basis" not in current["extraction"]
    assert current["withheld"]["pet_fee"] == enums.SCHEMA_CANNOT_REPRESENT
    assert current["withheld"]["fee_basis"] == enums.SCHEMA_CANNOT_REPRESENT
    # 12500 per_stay was the old answer and must not survive anywhere in the
    # current reading.
    assert 12500 not in current["extraction"].values()


def test_the_trade_keeps_the_facts_that_are_safe():
    current = record(TRADE)["current"]
    assert current["extraction"]["pets_allowed"] is True
    assert current["extraction"]["weight_limit"] == {"value": 100.0, "unit": "lb"}
    assert current["extraction"]["pet_count_limit"] == 2


def test_the_trade_evidence_names_the_multiple_components():
    components = {u["kind"] for u
                  in record(TRADE)["current"]["unrepresented_charge_components"]}
    assert "recurring_charge_not_represented" in components
    assert "deposit_not_represented" in components


def test_the_trade_uses_the_fresh_capture_as_its_evidence_subject():
    current = record(TRADE)["current"]
    assert current["evidence_source"] == C.FRESH_LIVE_CAPTURE
    assert current["policy_locator"] == "pet_policy_accordion_panel"
    assert current["run_id"] == C.FRESH_RUN_ID
    assert record(TRADE)["update_kind"] == C.LOCATOR_AND_READER


def test_poplar_creek_tier_cannot_flatten_to_the_first_tier():
    row = record(POPLAR)
    block = row["current"]["policy_block"]
    assert "$75" in block and "$150" in block          # both tiers preserved
    assert row["current"]["withheld"]["pet_fee"] == enums.SCHEMA_CANNOT_REPRESENT
    assert "pet_fee" not in row["current"]["extraction"]
    assert any(u["amount_minor"] == 15000
               for u in row["current"]["unrepresented_charge_components"])


def test_poplar_creek_is_a_relocation_within_its_persisted_document():
    row = record(POPLAR)
    assert row["current"]["evidence_source"] == C.PERSISTED_020_DOCUMENT
    assert row["update_kind"] == C.LOCATOR_AND_READER
    assert row["current"]["run_id"] == D.PRODUCTION_RUN_ID   # not re-acquired
    assert row["block_changed"]


def test_sheraton_conflicting_fee_components_are_withheld():
    row = record(SHERATON)
    block = row["current"]["policy_block"]
    assert "$75 per pet" in block and "$150.00" in block
    assert row["current"]["withheld"]["pet_fee"] == enums.SCHEMA_CANNOT_REPRESENT
    assert "pet_fee" not in row["current"]["extraction"]
    assert "pet_fee" in row["superseded"]["fields_asserted"]


def test_sheraton_is_reader_only_and_was_not_relocated():
    """Its block did not change; relocating it merely because a new locator
    exists would move what the record is about for no reason."""
    row = record(SHERATON)
    assert row["update_kind"] == C.READER_ONLY
    assert row["current"]["evidence_source"] == C.PERSISTED_020_BLOCK
    assert row["block_changed"] is False
    assert (row["current"]["policy_block"].strip()
            == row["superseded"]["policy_block"].strip())
    assert (row["current"]["policy_locator"]
            == row["superseded"]["policy_locator"])


@pytest.mark.parametrize("name", [TRADE, POPLAR, SHERATON])
def test_no_record_is_marked_ready(name):
    row = record(name)
    assert row["published"] is False
    assert row["founder_approved"] is False
    assert row["review_status"] == "HELD_SCHEMA_CANNOT_REPRESENT"


# --------------------------------------------------------------------------- #
# 8-9. Exactly three, and no fourth.
# --------------------------------------------------------------------------- #

def test_exactly_three_observations_are_superseded():
    doc = supersession()
    assert doc["records_superseded"] == 3 == C.EXPECTED_QUEUE
    assert {r["canonical_name"] for r in doc["records"]} == {TRADE, POPLAR, SHERATON}


def test_the_differential_is_clean_with_no_unexpected_rows():
    check = supersession()["differential"]
    assert check["clean"]
    assert check["unexpected_rows"] == []
    assert sorted(check["expected_rows"]) == sorted(check["rows_that_differ"])
    assert check["identity_unchanged"]
    assert check["publication_unchanged"]
    assert check["founder_approval_unchanged"]


def test_no_fourth_marriott_record_changed():
    """The other fourteen 020 records are untouched by this work order."""
    doc = supersession()
    superseded = {r["canonical_name"] for r in doc["records"]}
    run = json.loads(D.RUN_REPORT.read_text(encoding="utf-8-sig"))
    others = [r for r in run["rows"] if r["canonical_name"] not in superseded]
    assert len(others) == 14
    assert doc["differential"]["fourth_marriott_record_changed"] is False


def test_the_current_state_store_regeneration_is_a_no_op():
    """These three have no row in the store, so nothing there moves.

    Reported rather than fixed: widening the store's journal would add 17 rows,
    14 of them unexamined here.
    """
    check = supersession()["differential"]
    assert check["store_regeneration_is_a_no_op"]
    assert check["store_rows_before"] == check["store_rows_after_regeneration"]
    assert check["superseded_rows_present_in_store"] == []
    assert check["marriott_rows_in_store"] == 11


def test_only_one_provider_call_was_made():
    doc = supersession()
    assert doc["provider_calls"] == 1
    assert live()["route_used"]["attempts"] == 1


# --------------------------------------------------------------------------- #
# 10-13. Freezes.
# --------------------------------------------------------------------------- #

def test_the_marriott_route_is_unchanged():
    route = REGISTRY.resolve(
        brand="MARRIOTT",
        url="https://www.marriott.com/en-us/hotels/mkedd-x/overview/")
    assert route.provider == PROVIDERS.BRIGHTDATA_BROWSER
    assert route.ladder == (PROVIDERS.BRIGHTDATA_BROWSER,
                            PROVIDERS.BRIGHTDATA_WEB_UNLOCKER)
    assert route.reader == "marriott"


def test_the_global_locator_contract_is_unchanged():
    assert PL.CONTRACT == "ptf-policy-locator/1.0"
    for path in ("atlas-dashboard/scripts/pettripfinder/brightdata/policy_locator.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/routes.json",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/router.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/providers.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/readers.py"):
        changed = subprocess.run(["git", "status", "--porcelain", "--", path],
                                 cwd=str(REPO.parent), capture_output=True,
                                 text=True).stdout.strip()
        assert changed == "", "%s was modified by 022" % path
    LOCATOR_FREEZE.assert_locator_surface_unchanged()

def test_hilton_was_not_touched():
    route = REGISTRY.resolve(brand="HILTON", url="https://www.hilton.com/x")
    assert route.provider == PROVIDERS.BRIGHTDATA_BROWSER
    assert route.reader == "hilton_competing"
    remaining = counts()["remaining_by_brand"]
    assert remaining.get("HILTON") == 11


def test_no_milwaukee_policy_authority_exists():
    found = list((REPO / "launch_packages" / "pettripfinder")
                 .rglob("*hotel_policy_facts*milwaukee*"))
    assert not found, found
    assert counts()["milwaukee_policy_authority_files"] == 0


def test_nothing_is_published():
    assert counts()["published_policy_count"] == 0
    assert counts()["founder_approved_count"] == 0
    assert supersession()["published"] is False
    assert supersession()["authority_written"] is False
    assert live()["published"] is False


# --------------------------------------------------------------------------- #
# Phase 11 -- the counters.
# --------------------------------------------------------------------------- #

def test_every_counter_has_a_stated_predicate():
    doc = counts()
    for key in ("routable_total", "touched", "publication_grade",
                "observed", "unresolved", "remaining", "published"):
        assert key in doc["definitions"], key


def test_the_counters_are_internally_consistent():
    doc = counts()
    assert doc["queue_total"] - doc["brand_excluded"] == doc["routable_total"] == 127
    assert doc["touched"] == 84
    assert (doc["touched_by_run"]["milwaukee-router-001"]
            + doc["touched_by_run"][D.PRODUCTION_RUN_ID] == doc["touched"])
    assert doc["touched_by_run"]["overlap"] == 0
    assert doc["remaining_production_queue"] == doc["routable_total"] - doc["touched"]
    assert doc["publication_grade"] == 75
    assert doc["unresolved_acquisition"] == doc["touched"] - doc["publication_grade"]


def test_the_counters_are_not_interchangeable():
    """The point of the reconciliation: four predicates, four numbers."""
    doc = counts()
    assert doc["touched"] > doc["publication_grade"] > doc["observed_current_state"]
    assert doc["published_policy_count"] == 0
    assert doc["reconciliation"]["nothing_was_altered"] is True
    assert sum(doc["remaining_by_brand"].values()) == doc["remaining_production_queue"]
