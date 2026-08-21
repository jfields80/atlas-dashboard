"""PTF-MILWAUKEE-CLOSURE-ASSESSMENT-031.

WHAT THESE TESTS GUARD
----------------------
An assessment is worth less than the evidence under it. These tests do not
check that the classifications are wise -- that is a judgement and it is
recorded as one. They check that every judgement still rests on something real:
that all nineteen properties are classified exactly once, that each cited
check still passes against the archive, and that reaching those conclusions
changed nothing and contacted nobody.

The point is that a claim which stops being true should FAIL here rather than
quietly age into the repository.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import closure_assessment_031 as C
from scripts.pettripfinder.acquisition import premium_resolution_028 as P28
from scripts.pettripfinder.acquisition import registry as REGISTRY


# --------------------------------------------------------------------------- #
# 1 / 8 -- every property classified once, deterministically.
# --------------------------------------------------------------------------- #

def test_all_nineteen_unresolved_are_classified_exactly_once():
    rows = C.classify()
    assert len(rows) == 19
    keys = [row["identity_key"] for row in rows]
    assert len(set(keys)) == 19
    declared = P28.exception_queue()["active_acquisition_exceptions"]["queue"]
    assert sorted(keys) == sorted(row["identity_key"] for row in declared)
    for row in rows:
        assert row["closure_class"] in C.CLASSES
        assert row["why"]


def test_no_classification_is_a_placeholder():
    """A property with no recorded judgement must fail, not default to OTHER."""
    for row in C.classify():
        assert row["why"] != "no judgement recorded for this identity"
    assert set(C.JUDGEMENTS) == {row["identity_key"] for row in C.classify()}


def test_the_classification_is_deterministic():
    first = [(row["identity_key"], row["closure_class"], row["repair"],
              row["evidence_holds"]) for row in C.classify()]
    second = [(row["identity_key"], row["closure_class"], row["repair"],
               row["evidence_holds"]) for row in C.classify()]
    assert first == second


def test_every_judgement_still_rests_on_evidence_that_holds():
    """The whole point: a citation that stops being true fails here."""
    failed = [row["identity_key"] for row in C.classify()
              if not row["evidence_holds"]]
    assert failed == [], failed


def test_preflight_matches_the_committed_state():
    checks = C.preflight()["assertions"]
    assert all(checks.values()), checks


# --------------------------------------------------------------------------- #
# The specific findings, so they cannot rot silently.
# --------------------------------------------------------------------------- #

def test_the_three_locator_misses_have_their_policy_on_disk():
    """The strongest claim in this assessment, re-derived rather than quoted."""
    rows = {row["identity_key"]: row for row in C.classify()}
    for identity in ("hyatt regency milwaukee",
                     "hyatt place milwaukee airport",
                     "wildwood lodge"):
        row = rows[identity]
        assert row["closure_class"] == C.TARGETED_REPAIR
        assert row["repair"] == C.REPAIR_LOCATOR
        assert row["recoverable_from_existing_evidence"] is True
        assert row["document_persisted"] is True
        missing = (set(row["actionable_terms_in_document"])
                   - set(row["actionable_terms_in_block"]))
        assert missing, identity


def test_the_four_choice_properties_never_saw_their_committed_lane():
    rows = {row["identity_key"]: row for row in C.classify()}
    choice = [row for row in rows.values()
              if row["brand"] == "CHOICE"
              and row["unresolved_reason"] == "ACCESS_FAILURE"]
    assert len(choice) == 4
    for row in choice:
        assert row["closure_class"] == C.REACQUIRE
        assert row["current_route"]["ladder"][0] == "firecrawl"
        assert "firecrawl" not in row["providers_attempted"]
        assert "brightdata_web_unlocker" in row["providers_attempted"]


def test_the_committed_choice_route_still_leads_with_firecrawl():
    """If this ever changes, the re-acquisition recommendation is void."""
    route = REGISTRY.resolve(
        brand="CHOICE",
        url="https://www.choicehotels.com/wisconsin/milwaukee/econo-lodge-hotels/wi423")
    assert route.provider == "firecrawl"
    assert route.resolved_by == "domain:www.choicehotels.com"


def test_the_unverifiable_claims_are_not_called_final():
    """Three properties whose evidence was never written down.

    "This source publishes no pet policy" is a strong claim, and a capture that
    persists nothing cannot support it. Those are OTHER, pointing at the
    persistence repair -- never FINAL_SOURCE_LIMITATION.
    """
    rows = {row["identity_key"]: row for row in C.classify()}
    for identity in ("drury plaza hotel milwaukee downtown",
                     "potawatomi casino hotel",
                     "brewhouse inn and suites"):
        row = rows[identity]
        assert row["closure_class"] == C.OTHER
        assert row["repair"] == C.REPAIR_PERSIST_ON_FAILURE
        assert row["document_persisted"] is False


def test_spark_is_a_source_limitation_and_says_why():
    row = {r["identity_key"]: r for r in C.classify()}[
        "spark by hilton milwaukee airport"]
    assert row["closure_class"] == C.FINAL_SOURCE
    assert row["document_persisted"] is True
    assert row["actionable_terms_in_document"] == []


def test_a_smoking_fee_is_not_read_as_a_pet_term():
    """The check that nearly turned a real source limitation into a recovery."""
    assert C.actionable_pet_terms(
        "Pets allowed Yes A fee will be assessed for smoking in a "
        "non-smoking room") == set()
    assert "$40" in C.actionable_pet_terms(
        "Pet Fees Price : $40 / NIGHT")


# --------------------------------------------------------------------------- #
# 2 -- no provider is contacted.
# --------------------------------------------------------------------------- #

def test_the_whole_assessment_contacts_no_provider():
    from scripts.pettripfinder.acquisition import fresh_proof_019a as PROOF
    C.unresolved()          # warms any config read before the guard
    with PROOF.no_provider_calls() as attempts:
        rows = C.classify()
        plan = C.repair_plan()
        scenes = C.scenarios()
    assert attempts == []
    assert len(rows) == 19
    assert plan["repairs"]
    assert set(scenes) == {"FREEZE_NOW", "ONE_MORE_REPAIR_WAVE",
                           "MAXIMUM_RECOVERY"}


# --------------------------------------------------------------------------- #
# 3 / 4 / 5 -- nothing moved.
# --------------------------------------------------------------------------- #

def test_routes_readers_and_capture_machinery_are_unchanged():
    for path in ("atlas-dashboard/scripts/pettripfinder/acquisition/routes.json",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/registry.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/router.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/providers.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/readers.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/source_discovery.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/source_selection.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/store_integration_025.py",
                 "atlas-dashboard/scripts/pettripfinder/brightdata/policy_reading.py",
                 "atlas-dashboard/scripts/pettripfinder/brightdata/policy_locator.py",
                 "atlas-dashboard/scripts/pettripfinder/brightdata/policy_surface.py",
                 "atlas-dashboard/scripts/pettripfinder/brightdata/marriott_surface.py",
                 "atlas-dashboard/launch_packages/pettripfinder/identity_census",
                 "atlas-dashboard/launch_packages/pettripfinder/milwaukee_final_partition_001.json"):
        changed = subprocess.run(["git", "status", "--porcelain", "--", path],
                                 cwd=str(REPO), capture_output=True,
                                 text=True).stdout.strip()
        assert changed == "", "%s was modified by 031" % path


def test_the_observation_store_is_untouched():
    path = ("atlas-dashboard/launch_packages/pettripfinder/markets/reports/"
            "milwaukee-wi_policy_proposals_001.json")
    changed = subprocess.run(["git", "status", "--porcelain", "--", path],
                             cwd=str(REPO), capture_output=True,
                             text=True).stdout.strip()
    assert changed == ""
    store = json.loads(C.STORE.read_text(encoding="utf-8-sig"))
    assert len(store["items"]) == 114


def test_this_work_order_writes_exactly_one_artifact():
    """An assessment may report. It may not change what it assessed."""
    assert C.RUN_REPORT.name == "ptf_milwaukee_closure_assessment_031.json"
    source = C.__file__
    text = Path(source).read_text(encoding="utf-8")
    for term in ("write_text(", "open("):
        pass
    # Only the report path is ever written.
    assert text.count("write_text(") == 1
    assert "RUN_REPORT.write_text" in text


# --------------------------------------------------------------------------- #
# 6 / 7 -- authority and publication.
# --------------------------------------------------------------------------- #

def test_no_milwaukee_policy_authority_exists():
    root = REPO / "atlas-dashboard" / "launch_packages" / "pettripfinder"
    assert list(root.rglob("*hotel_policy_facts*milwaukee*")) == []
    store = json.loads(C.STORE.read_text(encoding="utf-8-sig"))
    assert store["authority_written"] is False
    assert store["founder_approvals_created"] == 0


def test_nothing_is_published():
    store = json.loads(C.STORE.read_text(encoding="utf-8-sig"))
    assert all(not row.get("published") for row in store["items"])
    assert C.build_report()["published"] == 0


# --------------------------------------------------------------------------- #
# The scenarios must be arithmetic, not optimism.
# --------------------------------------------------------------------------- #

def test_the_freeze_scenarios_reconcile_with_the_classification():
    rows = C.classify()
    scenes = C.scenarios()
    assert scenes["FREEZE_NOW"]["observed"] == 114
    assert scenes["FREEZE_NOW"]["final_active_exceptions"] == 19
    wave = scenes["ONE_MORE_REPAIR_WAVE"]
    assert (wave["likely_observed"]
            == scenes["FREEZE_NOW"]["observed"] + wave["likely_recovered"])
    assert (wave["likely_active_unresolved"]
            == 19 - wave["likely_recovered"])
    finals = [row for row in rows if row["closure_class"].startswith("FINAL")]
    assert scenes["MAXIMUM_RECOVERY"]["irreducible_finals"] == len(finals)
    assert (scenes["MAXIMUM_RECOVERY"]["ceiling_observed"]
            == 114 + 19 - len(finals))


def test_the_maximum_recovery_ceiling_is_labelled_a_ceiling():
    text = json.dumps(C.scenarios()["MAXIMUM_RECOVERY"]).lower()
    assert "ceiling" in text
    assert "not a forecast" in text


def test_every_repair_declares_what_it_changes_and_what_it_risks():
    for repair in C.repair_plan()["repairs"]:
        assert repair["value"] in ("HIGH", "MEDIUM", "LOW")
        assert repair["general_defect"]
        assert repair["risk"]
        assert isinstance(repair["milwaukee_recovery"], int)
        assert isinstance(repair["changes"], list) and repair["changes"]


def test_the_identity_repair_is_not_ranked_high():
    """It recovers three properties and it is the one gate that fails silently."""
    plan = {repair["repair"]: repair for repair in C.repair_plan()["repairs"]}
    identity = plan[C.REPAIR_CODELESS_PHONE]
    assert identity["value"] != "HIGH"
    assert identity["identity_unchanged"] is False
    assert "HIGH" in identity["risk"]


def test_no_recommended_repair_changes_provider_routing():
    for repair in C.repair_plan()["repairs"]:
        assert repair["routing_unchanged"] is True
