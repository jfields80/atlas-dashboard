"""PTF-HILTON-ACQUISITION-DECISION-023.

Hilton was the last unresolved production lane. Firecrawl reached 0 of 7
decision subjects and the Bright Data Browser API reached all 7, so the brand
stays on the Browser API and ``routes.json`` is unchanged.

WHAT THESE TESTS GUARD
----------------------
The route is a FREEZE here: nothing changed, and these prove it.

The judgement is where this work order could have gone wrong twice, and both
mistakes were made and corrected during it:

  * the first Bright Data control returned 1 of 7 and would have read as "the
    Browser API cannot do Hilton either". It was session exhaustion from
    interrupted runs -- the successful capture took 100s and the six failures
    took 8s each. A verdict from that control would have been wrong.
  * a failure on the Browser API lane was labelled FIRECRAWL_ACCESS_FAILURE,
    naming a provider that never ran on the row.

And the template audit, because 11 of 11 acquired and 10 of 11 usable still
leaves 6 records that are not safe to publish.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import hilton_decision_023 as H     # noqa: E402
from scripts.pettripfinder.acquisition import providers as PROVIDERS       # noqa: E402
from scripts.pettripfinder.acquisition import registry as REGISTRY         # noqa: E402
from scripts.pettripfinder.brightdata import policy_locator as PL          # noqa: E402

HILTON_URL = "https://www.hilton.com/en/hotels/mkeaiht-home2-suites-x/"


def decision():
    return json.loads(H.DECISION_REPORT.read_text(encoding="utf-8-sig"))


def run():
    return json.loads(H.RUN_REPORT.read_text(encoding="utf-8-sig"))


# --------------------------------------------------------------------------- #
# Cohort and structure.
# --------------------------------------------------------------------------- #

def test_the_hilton_cohort_is_eleven():
    assert len(H.remaining_cohort()) == H.EXPECTED_REMAINING == 11


def test_every_hilton_property_shares_one_host_and_url_form():
    shapes = {(H.url_shape(r["official_url"])["host"],
               H.url_shape(r["official_url"])["path_form"])
              for r in H.remaining_cohort()}
    assert len(shapes) == 1
    (host, _), = shapes
    assert host == "www.hilton.com"


def test_the_cohort_covers_every_structural_group():
    rows = H.remaining_cohort()
    chosen, held, summary = H.decision_cohort(rows)
    groups = H.structural_groups(rows)
    assert summary["group_count"] == 4
    covered = {H.sub_brand_of(r["official_url"]) for r in chosen}
    assert covered == {H.sub_brand_of(v[0]["official_url"])
                       for v in groups.values()}
    assert len(chosen) <= H.DECISION_COHORT_MAX
    assert len(chosen) + len(held) == len(rows)


def test_the_cohort_selection_is_deterministic_and_outcome_blind():
    rows = H.remaining_cohort()
    first = [r["identity_key"] for r in H.decision_cohort(rows)[0]]
    second = [r["identity_key"] for r in H.decision_cohort(rows)[0]]
    assert first == second
    for row in H.decision_cohort(rows)[0]:
        group = [r for r in rows
                 if H.sub_brand_of(r["official_url"])
                 == H.sub_brand_of(row["official_url"])]
        assert row["canonical_name"] in sorted(
            r["canonical_name"] for r in group)[:H.PER_GROUP]


def test_every_decision_subject_is_source_ready():
    for row in H.decision_cohort(H.remaining_cohort())[0]:
        audit = H.source_audit(row)
        assert audit["classification"] == H.SOURCE_READY, row["canonical_name"]
        assert audit["property_code"] and not audit["problems"]


# --------------------------------------------------------------------------- #
# The route is unchanged.
# --------------------------------------------------------------------------- #

def test_hilton_still_leads_with_the_browser_api():
    route = REGISTRY.resolve(brand="HILTON", url=HILTON_URL)
    assert route.provider == PROVIDERS.BRIGHTDATA_BROWSER
    assert route.ladder == (PROVIDERS.BRIGHTDATA_BROWSER,
                            PROVIDERS.BRIGHTDATA_WEB_UNLOCKER)
    assert route.reader == "hilton_competing"


def test_routes_json_was_not_written():
    last = subprocess.run(
        ["git", "log", "-1", "--format=%H", "--",
         "atlas-dashboard/scripts/pettripfinder/acquisition/routes.json"],
        cwd=str(REPO.parent), capture_output=True, text=True).stdout.strip()
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(REPO.parent),
                          capture_output=True, text=True).stdout.strip()
    assert last and last != head
    assert decision()["routes_json_written"] is False
    changed = subprocess.run(
        ["git", "status", "--porcelain", "--",
         "atlas-dashboard/scripts/pettripfinder/acquisition/routes.json"],
        cwd=str(REPO.parent), capture_output=True, text=True).stdout.strip()
    assert changed == ""


def test_the_other_brands_are_untouched():
    for brand, provider, reader in (
            ("MARRIOTT", PROVIDERS.BRIGHTDATA_BROWSER, "marriott"),
            ("CHOICE", PROVIDERS.FIRECRAWL, "choice_static"),
            ("WYNDHAM", PROVIDERS.FIRECRAWL, "wyndham"),
            ("IHG", PROVIDERS.FIRECRAWL, "ihg")):
        route = REGISTRY.resolve(brand=brand, url="https://example.com/x")
        assert route.provider == provider, brand
        assert route.reader == reader, brand


def test_the_in_memory_override_changes_hilton_and_nothing_else():
    override = H.registry_override(
        provider=PROVIDERS.FIRECRAWL, fallbacks=(),
        forbid=(PROVIDERS.BRIGHTDATA_BROWSER, PROVIDERS.BRIGHTDATA_WEB_UNLOCKER))
    assert REGISTRY.resolve(brand="HILTON", url=HILTON_URL,
                            registry=override).ladder == (PROVIDERS.FIRECRAWL,)
    live = REGISTRY.load()
    for brand in live["brands"]:
        if brand == "HILTON":
            continue
        assert override["brands"][brand] == live["brands"][brand], brand
    assert override["domains"] == live["domains"]
    assert REGISTRY.resolve(brand="HILTON", url=HILTON_URL).provider \
        == PROVIDERS.BRIGHTDATA_BROWSER


def test_the_canonical_locator_contract_is_active_and_unchanged():
    assert PL.CONTRACT == "ptf-policy-locator/1.0"
    for path in ("atlas-dashboard/scripts/pettripfinder/brightdata/policy_locator.py",
                 "atlas-dashboard/scripts/pettripfinder/brightdata/policy_surface.py",
                 "atlas-dashboard/scripts/pettripfinder/brightdata/marriott_surface.py",
                 # policy_reading.py left this freeze in 024, which changed
                 # the generic reader deliberately. This work order still
                 # changed nothing there.
                 "atlas-dashboard/scripts/pettripfinder/acquisition/readers.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/router.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/providers.py"):
        changed = subprocess.run(["git", "status", "--porcelain", "--", path],
                                 cwd=str(REPO.parent), capture_output=True,
                                 text=True).stdout.strip()
        assert changed == "", "%s was modified by 023" % path


def test_source_selection_is_independent_of_provider_routing():
    row = H.remaining_cohort()[0]
    assert H.source_audit(row)["route_url"] == row["official_url"]


# --------------------------------------------------------------------------- #
# The measured decision.
# --------------------------------------------------------------------------- #

def test_the_committed_decision_is_retain_browser():
    doc = decision()
    assert doc["verdict"]["decision"] == H.RETAIN_BROWSER
    assert doc["remaining_hilton"] == 11


def test_firecrawl_reached_no_hilton_property():
    rows = decision()["firecrawl_rows"]
    assert len(rows) == 7
    assert all(r["acquisition_status"] == "NOT_ACQUIRED" for r in rows)
    assert all(r["attribution"]["cause"] == H.FIRECRAWL_ACCESS_FAILURE
               for r in rows)
    assert all(not r["artifact_written"] for r in rows)


def test_the_browser_control_reached_every_subject():
    rows = decision()["browser_control_rows"]
    assert len(rows) == 7
    assert all(r["acquisition_status"] == "ACQUIRED" for r in rows)
    assert sum(1 for r in rows if r["usable_policy"] == H.USABLE) == 6


def test_no_limitation_route_is_offered_without_a_working_subset():
    """With Firecrawl at 0, there is no subset to limit."""
    subset = decision()["verdict"]["subset_rule"]
    assert subset["sub_brands_succeeding"] == []
    assert subset["separable"] is False


def test_a_browser_failure_is_not_charged_to_firecrawl():
    """The defect corrected mid-work-order: a lane that never ran must not be
    named as the cause."""
    result = H.attribute_failure(
        source={"classification": H.SOURCE_READY, "problems": []},
        result=type("R", (), {"failure": "NAVIGATION_FAILED",
                              "escalation_stopped_because": ""})(),
        document=None, usable={"checks": {}},
        provider=PROVIDERS.BRIGHTDATA_BROWSER)
    assert result["cause"] == H.PROVIDER_ACCESS_FAILURE
    assert result["provider"] == PROVIDERS.BRIGHTDATA_BROWSER
    firecrawl = H.attribute_failure(
        source={"classification": H.SOURCE_READY, "problems": []},
        result=type("R", (), {"failure": "ACCESS_DENIED",
                              "escalation_stopped_because": ""})(),
        document=None, usable={"checks": {}}, provider=PROVIDERS.FIRECRAWL)
    assert firecrawl["cause"] == H.FIRECRAWL_ACCESS_FAILURE


def test_a_page_absence_is_never_charged_to_the_provider():
    result = H.attribute_failure(
        source={"classification": H.SOURCE_READY, "problems": []},
        result=None, document=object(),
        usable={"checks": {"identity_bound_to_this_property": True,
                           "policy_block_present": False}})
    assert result["cause"] == H.POLICY_NOT_PRESENT


def test_a_bad_source_is_charged_to_the_source():
    result = H.attribute_failure(
        source={"classification": H.SOURCE_AMBIGUOUS, "problems": ["no code"]},
        result=None, document=None, usable={"checks": {}})
    assert result["cause"] == H.SOURCE_URL_FAILURE


# --------------------------------------------------------------------------- #
# The usable-policy bar.
# --------------------------------------------------------------------------- #

def test_service_animal_only_text_is_not_a_pet_policy():
    assert H.service_animal_only("Service animals are always welcome.")
    assert not H.service_animal_only(
        "Pets allowed Yes Deposit Yes. $75.00 Non-refundable Fee. "
        "Service animals are welcome.")


def test_a_bare_allowed_flag_is_not_usable():
    row = next(r for r in run()["rows"]
               if r["canonical_name"] == "Spark by Hilton Milwaukee Airport")
    assert row["usable_policy"] == H.NOT_USABLE
    assert row["usable_policy_detail"]["block_text"] == "Pets allowed Yes"


# --------------------------------------------------------------------------- #
# The 11-property run and the template audit.
# --------------------------------------------------------------------------- #

def test_the_run_covered_exactly_eleven():
    doc = run()
    assert doc["subject_count"] == 11
    assert doc["subject_assertion_held"] is True
    assert doc["run_complete"] is True
    assert doc["acquired"] == 11
    assert doc["usable_policy_successes"] == 10


def test_the_run_used_the_committed_route():
    doc = run()
    assert doc["route_used"]["provider"] == PROVIDERS.BRIGHTDATA_BROWSER
    assert doc["provider_mix"] == {PROVIDERS.BRIGHTDATA_BROWSER: 11}
    assert doc["fallback_uses"] == 0


def test_tiered_fees_are_detected():
    assert H.tiers_in("Other pet information $50(1-4 nights),$125(5+ nights)")
    assert H.tiers_in("$75 for the first four nights, $125 for 5+")
    assert H.tiers_in("$50/stay for 1 night, $75/stay for 2-4 nights")
    assert not H.tiers_in("Pets allowed Yes Deposit Yes. $75.00 Non-refundable Fee")


def test_a_banded_fee_with_an_asserted_single_fee_is_held():
    """The Hilton form of the failure 021 ended for Marriott."""
    finding = H.audit_row({
        "canonical_name": "x", "policy_locator": "generic_signal_walk",
        "usable_policy_detail": {
            "block_text": "Pets allowed Yes Deposit Yes. $50.00 Non-refundable "
                          "Fee Other pet information $50(1-4 nights),$125(5+ nights)",
            "substantive_fields": ["pet_fee"], "withheld_fields": [],
            "block_chars": 120}})
    assert finding["verdict"] == H.TIERED_FEE_UNDERSTATED
    assert finding["highest_amount_stated"] == 125.0


def test_a_banded_fee_that_withholds_is_complete():
    finding = H.audit_row({
        "canonical_name": "x", "policy_locator": "generic_signal_walk",
        "usable_policy_detail": {
            "block_text": "Pets allowed Yes $75/stay 1-4 nights, $125/stay 5+ nights",
            "substantive_fields": [], "withheld_fields": ["pet_fee"],
            "block_chars": 60}})
    assert finding["verdict"] == H.COMPLETE


def test_a_thin_brand_container_block_is_held():
    """024 corrected the VERDICT this case earns.

    023 called it BRAND_CONTAINER_PREEMPTED without checking whether a richer
    candidate existed. With no persisted document to point at, the honest
    verdict is a thin surface: the property published a flag and no terms.
    The record is held either way; the reason is now the true one.
    """
    finding = H.audit_row({
        "canonical_name": "x", "policy_locator": "hilton_pet_panel",
        "usable_policy_detail": {"block_text": "Pets allowed Yes",
                                 "substantive_fields": [],
                                 "withheld_fields": [], "block_chars": 16}})
    assert finding["verdict"] == H.THIN_SURFACE
    assert finding["issues"]


def test_the_run_holds_six_records_and_says_so():
    """11 acquired and 10 usable is not 10 publishable records."""
    audit = run()["template_audit"]
    assert audit["materially_incomplete"] == 6
    assert audit["issue_counts"][H.TIERED_FEE_UNDERSTATED] == 5
    assert audit["issue_counts"][H.BRAND_CONTAINER_PREEMPTED] == 1
    assert len(audit["held_for_review"]) == 6


def test_usable_and_complete_is_a_set_difference_not_a_subtraction():
    """Spark is held AND not usable; subtracting counts would charge it twice."""
    doc = run()
    usable = {r["canonical_name"] for r in doc["rows"]
              if r["usable_policy"] == H.USABLE}
    held = set(doc["template_audit"]["held_for_review"])
    assert doc["usable_and_materially_complete"] == len(usable - held) == 5


def test_multiple_hilton_locators_were_observed():
    audit = run()["template_audit"]
    assert audit["locators_used"] == {"generic_signal_walk": 10,
                                      "hilton_pet_panel": 1}
    assert audit["multiple_templates"] is True


# --------------------------------------------------------------------------- #
# Freezes.
# --------------------------------------------------------------------------- #

def test_no_policy_authority_was_created():
    found = list((REPO / "launch_packages" / "pettripfinder")
                 .rglob("*hotel_policy_facts*milwaukee*"))
    assert not found, found
    assert run()["authority_written"] is False
    assert decision()["authority_written"] is False


def test_nothing_was_published():
    assert run()["published"] is False
    assert decision()["published"] is False
    assert decision()["readers_changed"] is False


def test_this_work_order_did_not_widen_the_observation_store():
    """Phase 16 held: 023 left the store alone.

    PTF-MILWAUKEE-OBSERVATION-STORE-INTEGRATION-025 later reconciled it and
    the Hilton rows are in it now, which is that work order's doing and not
    this one's. What stays true of 023 is that it declared no integration.
    """
    assert run()["authority_written"] is False
    assert run()["published"] is False
