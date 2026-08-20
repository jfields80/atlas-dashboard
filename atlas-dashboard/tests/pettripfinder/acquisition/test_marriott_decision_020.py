"""PTF-MARRIOTT-ACQUISITION-DECISION-020.

Marriott was the last brand still leading with the Bright Data Browser API.
This work order tested whether it could move to Firecrawl like Choice, Wyndham
and IHG did, and concluded RETAIN_BROWSER: Firecrawl acquired 0 of 8 decision
subjects and the Browser API acquired 8 of 8.

WHAT THESE TESTS GUARD
----------------------
The route did NOT change, so the routing tests here are freeze tests: Marriott
must still lead with the Browser API, the three Firecrawl brands must be
untouched, and the canonical locator must remain wired.

The rest guard the judgement, because the judgement is where this work order
could most easily have gone wrong. Three defects in the scoring were found and
corrected AFTER the measured run, and each has a test that fails if it comes
back:

  * a property-bound REFUSAL is a complete policy and must count as usable
  * a page that states its policy in Marriott's SECOND template is a LOCATOR
    gap, not a reader failure and not a genuine absence
  * a "Firecrawl with a limitation" route may not be offered for a lane that
    acquired nothing, because there is no working subset to limit
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import marriott_decision_020 as M  # noqa: E402
from scripts.pettripfinder.acquisition import providers as PROVIDERS      # noqa: E402
from scripts.pettripfinder.acquisition import registry as REGISTRY        # noqa: E402
from scripts.pettripfinder.brightdata import policy_locator as PL         # noqa: E402

MARRIOTT_URL = "https://www.marriott.com/en-us/hotels/mkeak-hotel-metro/overview/"


def decision_report():
    return json.loads(M.DECISION_REPORT.read_text(encoding="utf-8-sig"))


# --------------------------------------------------------------------------- #
# The cohort is computed, not typed.
# --------------------------------------------------------------------------- #

def test_the_remaining_marriott_cohort_is_seventeen():
    """The assertion the work order requires before any request."""
    assert len(M.remaining_cohort()) == M.EXPECTED_REMAINING == 17


def test_the_cohort_is_the_queue_minus_what_was_already_acquired():
    """Derived by subtraction, so it cannot drift from the record."""
    rows = M.remaining_cohort()
    done = M._already_acquired()
    assert rows and all(r["identity_key"] not in done for r in rows)
    assert all(r["brand"] == "MARRIOTT" and not r["brand_excluded"] for r in rows)


def test_the_decision_cohort_is_selected_before_any_outcome():
    """One representative per structural group, alphabetically first.

    Re-running selection must give the same eight; a selection that depended on
    an outcome could not.
    """
    rows = M.remaining_cohort()
    first, held_a, _ = M.decision_cohort(rows)
    second, held_b, _ = M.decision_cohort(rows)
    assert [r["identity_key"] for r in first] == [r["identity_key"] for r in second]
    assert [r["identity_key"] for r in held_a] == [r["identity_key"] for r in held_b]
    assert len(first) + len(held_a) == len(rows) == 17
    assert len(first) <= M.DECISION_COHORT_MAX
    for row in first:
        group = [r for r in rows
                 if M.sub_brand_of(r["official_url"])
                 == M.sub_brand_of(row["official_url"])]
        assert row["canonical_name"] == min(r["canonical_name"] for r in group)


def test_every_marriott_subject_shares_one_host_and_one_url_form():
    """The finding that makes sub-brand the only structural axis."""
    shapes = {(M.url_shape(r["official_url"])["host"],
               M.url_shape(r["official_url"])["path_form"])
              for r in M.remaining_cohort()}
    assert len(shapes) == 1
    (host, _), = shapes
    assert host == "www.marriott.com"


# --------------------------------------------------------------------------- #
# Source audit.
# --------------------------------------------------------------------------- #

def test_every_decision_subject_is_source_ready():
    """Firecrawl was judged on sound inputs, not on pages nobody should ask for."""
    for row in M.decision_cohort(M.remaining_cohort())[0]:
        audit = M.source_audit(row)
        assert audit["classification"] == M.SOURCE_READY, row["canonical_name"]
        assert audit["property_code"]
        assert audit["problems"] == []


def test_a_url_without_a_property_code_is_ambiguous_not_ready():
    """The control: the audit can fail, so passing it means something."""
    audit = M.source_audit({"identity_key": "x", "canonical_name": "X",
                            "official_url": "https://www.marriott.com/en-us/"})
    assert audit["classification"] == M.SOURCE_AMBIGUOUS
    assert audit["problems"]


# --------------------------------------------------------------------------- #
# The route did not change.
# --------------------------------------------------------------------------- #

def test_marriott_still_leads_with_the_browser_api():
    route = REGISTRY.resolve(brand="MARRIOTT", url=MARRIOTT_URL)
    assert route.provider == PROVIDERS.BRIGHTDATA_BROWSER
    assert route.ladder == (PROVIDERS.BRIGHTDATA_BROWSER,
                            PROVIDERS.BRIGHTDATA_WEB_UNLOCKER)
    assert route.reader == "marriott"


def test_the_firecrawl_brands_are_untouched_by_this_work_order():
    for brand, reader in (("CHOICE", "choice_static"), ("WYNDHAM", "wyndham"),
                          ("IHG", "ihg")):
        route = REGISTRY.resolve(brand=brand, url="https://example.com/x")
        assert route.provider == PROVIDERS.FIRECRAWL, brand
        assert route.reader == reader
        assert PROVIDERS.BRIGHTDATA_BROWSER in route.forbidden_providers


def test_routes_json_was_not_written_by_this_work_order():
    """The decision test drove an in-memory copy; the file must be older."""
    last = subprocess.run(
        ["git", "log", "-1", "--format=%H", "--",
         "atlas-dashboard/scripts/pettripfinder/acquisition/routes.json"],
        cwd=str(REPO.parent), capture_output=True, text=True).stdout.strip()
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(REPO.parent),
                          capture_output=True, text=True).stdout.strip()
    assert last and last != head
    assert decision_report()["routes_json_written"] is False


def test_the_in_memory_override_changes_marriott_and_nothing_else():
    override = M.registry_override(
        provider=PROVIDERS.FIRECRAWL, fallbacks=(),
        forbid=(PROVIDERS.BRIGHTDATA_BROWSER,))
    assert REGISTRY.resolve(brand="MARRIOTT", url=MARRIOTT_URL,
                            registry=override).provider == PROVIDERS.FIRECRAWL
    # Every other brand row survives the copy untouched.
    live = REGISTRY.load()
    for brand in live["brands"]:
        if brand == "MARRIOTT":
            continue
        assert override["brands"][brand] == live["brands"][brand], brand
    assert override["domains"] == live["domains"]
    # And the on-disk registry still routes Marriott to the Browser API.
    assert REGISTRY.resolve(brand="MARRIOTT", url=MARRIOTT_URL).provider \
        == PROVIDERS.BRIGHTDATA_BROWSER


def test_the_canonical_locator_contract_is_still_active():
    assert PL.CONTRACT == "ptf-policy-locator/1.0"
    assert PL.LOCATOR_ARTIFACT == "locator.json"


def test_source_selection_stays_independent_of_provider_routing():
    """Which page we read and which lane fetches it are separate decisions."""
    row = M.remaining_cohort()[0]
    audit = M.source_audit(row)
    assert audit["route_url"] == row["official_url"]


# --------------------------------------------------------------------------- #
# Defect 1: a refusal is a policy.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("block", [
    "Pet Policy Pets Not Allowed",
    "No, pets are not allowed at Milwaukee Marriott Downtown.",
    "Pets are not permitted at this hotel.",
])
def test_a_refusal_is_recognised(block):
    assert M.states_a_refusal(block)


def test_a_qualified_refusal_is_not_a_refusal():
    """PTF-ACQUISITION-BRAND-REPAIR-003's error, guarded from both directions.

    "no other pets are allowed" sits INSIDE an acceptance. Reading it as a
    refusal would withhold a real policy; reading it as an acceptance nearly
    published a no-pets hotel. It is neither, and this module says so.
    """
    assert not M.states_a_refusal(
        "Dogs up to 50 lbs are welcome; no other pets are allowed.")


def test_a_property_bound_refusal_counts_as_usable_policy():
    """A refusal carries no fee, weight or count because there is nothing to
    charge for. Demanding one would score the clearest possible answer as a
    failure."""
    document = M._PersistedDocument(
        policy_text="Pet Policy Pets Not Allowed",
        policy_locator="pet_policy_heading_parent",
        rendered_html_path="",
        observation={"extraction": {}, "evidence": []},
        withheld_fields={},
        identity={"signals": {"property_code_on_page": "mkemr"}})
    verdict = M.usable_policy(document, expected_code="mkemr")
    assert verdict["verdict"] == M.USABLE
    assert verdict["states_a_refusal"]


def test_an_amenity_blurb_is_not_usable_policy():
    """The exclusion the work order names: a 'pet friendly' claim is not a
    policy, however many words it uses to say it."""
    document = M._PersistedDocument(
        policy_text=("Enjoy the peace of mind of traveling with your pet. Our "
                     "dog-friendly hotel provides a Heavenly dog bed, dog bowl "
                     "and doggy treats."),
        policy_locator="generic_signal_walk",
        rendered_html_path="",
        observation={"extraction": {}, "evidence": []},
        withheld_fields={},
        identity={"signals": {"property_code_on_page": "mkeiw"}})
    verdict = M.usable_policy(document, expected_code="mkeiw")
    assert verdict["verdict"] == M.NOT_USABLE
    assert not verdict["states_a_refusal"]


def test_a_wrong_property_page_is_never_usable():
    document = M._PersistedDocument(
        policy_text="Pet Policy Pets Welcome. Maximum Pet Weight: 50.0lbs",
        policy_locator="pet_policy_heading_parent",
        rendered_html_path="",
        observation={"extraction": {"weight_limit": 50}, "evidence": []},
        withheld_fields={},
        identity={"signals": {"property_code_on_page": "mkexx"}})
    assert M.usable_policy(document, expected_code="mkeak")["verdict"] \
        == M.NOT_USABLE


# --------------------------------------------------------------------------- #
# Defect 2: Marriott's second template is a locator gap.
# --------------------------------------------------------------------------- #

ACCORDION = """<div class="accordion-content d-inline-block w-100 py-3 pr-4">
    <b class="d-block t-font-m pb-2 mb-1">Pet Policy</b>
    <p class="t-font-s pb-2 m-0">Pets Welcome.</p>
    <p class="t-font-s pb-2 m-0">Dogs only up to 75 pounds. Limit of 2.</p>
</div>"""

ICON_TEMPLATE = """<div class="d-flex align-items-start">
  <span class="icon-pet-friendly hotel-info-icon icon-m mr-2"></span>
  <div class="t-font-s"><div class="pb-2 t-font-s">Pet Policy</div>
  <div class="t-font-xs">Pets Welcome</div></div></div>"""


def test_the_accordion_template_is_detected():
    found = M.alternate_template_policy(ACCORDION)
    assert "Dogs only up to 75 pounds" in found


def test_the_icon_template_is_not_mistaken_for_the_accordion():
    """The locator already reaches this one; reporting it as missed would
    invent a gap that is not there."""
    assert M.alternate_template_policy(ICON_TEMPLATE) == ""


def test_a_page_that_states_a_policy_we_missed_is_a_locator_failure(tmp_path):
    """Not a reader failure, and not a genuine absence. This is the
    distinction the whole work order turns on."""
    page = tmp_path / "rendered.html"
    page.write_text(ACCORDION, encoding="utf-8")
    document = M._PersistedDocument(
        policy_text="Our dog-friendly hotel provides a Heavenly dog bed.",
        policy_locator="generic_signal_walk",
        rendered_html_path=str(page),
        observation={"extraction": {}, "evidence": []},
        withheld_fields={},
        identity={"signals": {"property_code_on_page": "mkeiw"}})
    verdict = M.usable_policy(document, expected_code="mkeiw")
    attribution = M.attribute_failure(
        source={"classification": M.SOURCE_READY, "problems": []},
        result=None, document=document, usable=verdict)
    assert attribution["cause"] == M.LOCATOR_FAILURE
    assert "Dogs only up to 75 pounds" in attribution["page_states_but_locator_missed"]


def test_a_page_with_no_policy_in_either_template_is_a_genuine_absence(tmp_path):
    page = tmp_path / "rendered.html"
    page.write_text("<html><body><p>Free parking.</p></body></html>",
                    encoding="utf-8")
    document = M._PersistedDocument(
        policy_text="", policy_locator="", rendered_html_path=str(page),
        observation={"extraction": {}, "evidence": []}, withheld_fields={},
        identity={"signals": {"property_code_on_page": "mkeak"}})
    verdict = M.usable_policy(document, expected_code="mkeak")
    attribution = M.attribute_failure(
        source={"classification": M.SOURCE_READY, "problems": []},
        result=None, document=document, usable=verdict)
    assert attribution["cause"] == M.POLICY_NOT_PRESENT


def test_a_page_that_never_arrived_is_charged_to_the_provider():
    attribution = M.attribute_failure(
        source={"classification": M.SOURCE_READY, "problems": []},
        result=type("R", (), {"failure": "ACCESS_DENIED",
                              "escalation_stopped_because": ""})(),
        document=None, usable={"checks": {}})
    assert attribution["cause"] == M.FIRECRAWL_ACCESS_FAILURE


def test_a_bad_source_is_charged_to_the_source_not_the_provider():
    attribution = M.attribute_failure(
        source={"classification": M.SOURCE_AMBIGUOUS, "problems": ["no code"]},
        result=None, document=None, usable={"checks": {}})
    assert attribution["cause"] == M.SOURCE_URL_FAILURE


# --------------------------------------------------------------------------- #
# Defect 3: a limitation route needs a working subset.
# --------------------------------------------------------------------------- #

def _row(usable, cause="", acquired=True):
    return {"usable_policy": M.USABLE if usable else M.NOT_USABLE,
            "acquisition_status": "ACQUIRED" if acquired else "NOT_ACQUIRED",
            "publication_grade": usable,
            "attribution": {"cause": cause, "why": ""}}


def test_a_lane_that_acquired_nothing_cannot_earn_a_limitation_route():
    """The defect this work order's own first verdict contained.

    With Firecrawl at 0 of 8 there is no mechanically identifiable subset on
    which it works, so APPROVE_FIRECRAWL_WITH_LIMITATION would name a
    limitation of nothing.
    """
    firecrawl = [_row(False, M.FIRECRAWL_ACCESS_FAILURE, acquired=False)
                 for _ in range(8)]
    control = [_row(True) for _ in range(7)]
    verdict = M.decide(firecrawl, control, [{"classification": M.SOURCE_READY}] * 8)
    assert verdict["decision"] == M.RETAIN_BROWSER


def test_firecrawl_is_approved_when_it_works_everywhere():
    firecrawl = [_row(True) for _ in range(8)]
    verdict = M.decide(firecrawl, [], [{"classification": M.SOURCE_READY}] * 8)
    assert verdict["decision"] == M.APPROVE_FIRECRAWL


def test_a_page_absence_is_never_a_reason_to_pay_for_the_browser():
    """Firecrawl acquired everything; some pages simply had no policy. That
    follows the page to any lane."""
    firecrawl = [_row(True) for _ in range(6)] + \
                [_row(False, M.POLICY_NOT_PRESENT) for _ in range(2)]
    verdict = M.decide(firecrawl, [], [{"classification": M.SOURCE_READY}] * 8)
    assert verdict["decision"] == M.APPROVE_FIRECRAWL


def test_a_partly_working_lane_earns_the_limitation_route():
    firecrawl = [_row(True) for _ in range(5)] + \
                [_row(False, M.FIRECRAWL_ACCESS_FAILURE, acquired=False)
                 for _ in range(3)]
    control = [_row(True) for _ in range(3)]
    verdict = M.decide(firecrawl, control, [{"classification": M.SOURCE_READY}] * 8)
    assert verdict["decision"] == M.APPROVE_WITH_LIMITATION


def test_bad_inputs_stop_a_provider_verdict_being_reached():
    firecrawl = [_row(False, M.SOURCE_URL_FAILURE) for _ in range(8)]
    sources = [{"classification": M.SOURCE_AMBIGUOUS}] * 8
    assert M.decide(firecrawl, [], sources)["decision"] \
        == M.SOURCE_STRATEGY_REQUIRED


# --------------------------------------------------------------------------- #
# What the measured run recorded.
# --------------------------------------------------------------------------- #

def test_the_committed_decision_is_retain_browser():
    doc = decision_report()
    assert doc["verdict"]["decision"] == M.RETAIN_BROWSER
    assert doc["remaining_marriott"] == 17
    assert len(doc["decision_cohort"]) == 8
    assert len(doc["held_for_production"]) == 9


def test_firecrawl_reached_no_marriott_property():
    rows = decision_report()["firecrawl_rows"]
    assert len(rows) == 8
    assert all(r["acquisition_status"] == "NOT_ACQUIRED" for r in rows)
    assert all(r["attribution"]["cause"] == M.FIRECRAWL_ACCESS_FAILURE
               for r in rows)


def test_the_browser_control_acquired_every_subject():
    rows = decision_report()["browser_control_rows"]
    assert len(rows) == 8
    assert all(r["acquisition_status"] == "ACQUIRED" for r in rows)
    usable = [r for r in rows if r["usable_policy"] == M.USABLE]
    assert len(usable) == 7
    # Two of the seven are refusals, which is a finding and not a shortfall.
    assert sum(1 for r in usable
               if r["usable_policy_detail"].get("states_a_refusal")) == 2


def test_the_one_browser_shortfall_is_our_locator_not_the_provider():
    rows = decision_report()["browser_control_rows"]
    failed = [r for r in rows if r["usable_policy"] != M.USABLE]
    assert len(failed) == 1
    assert failed[0]["attribution"]["cause"] == M.LOCATOR_FAILURE
    assert failed[0]["attribution"]["page_states_but_locator_missed"]


# --------------------------------------------------------------------------- #
# The template audit: a complete-looking record that understates the cost.
# --------------------------------------------------------------------------- #

def run_report():
    return json.loads(M.RUN_REPORT.read_text(encoding="utf-8-sig"))


def _audit_row(block, accordion, locator, tmp_path):
    page = tmp_path / "slug" / "attempt-01"
    page.mkdir(parents=True)
    (page / PL.BLOCK_ARTIFACT).write_text(block, encoding="utf-8")
    (page / "rendered.html").write_text(accordion, encoding="utf-8")
    rows = [{"canonical_name": "slug",
             "usable_policy_detail": {"block_text": block,
                                      "policy_locator": locator}}]
    return M.template_audit(rows, tmp_path)


def test_a_block_missing_a_recurring_charge_is_flagged(tmp_path):
    """The Trade's shape: the FAQ states the per-stay fee and omits the daily
    one, so a record built from it understates what a guest pays."""
    audit = _audit_row(
        "A non-refundable pet fee of $125.00 per stay applies.",
        "<b>Pet Policy</b><p>Pet deposit starts at $125 + $20 daily pet fee.</p></div>",
        "generic_signal_walk", tmp_path)
    assert audit["understating_records"] == 1
    finding = audit["findings"][0]
    assert finding["understates_the_cost"]
    assert "$20" in finding["charge_terms_only_in_accordion"]


def test_two_surfaces_that_agree_are_not_flagged(tmp_path):
    audit = _audit_row(
        "No, pets are not allowed at Milwaukee Marriott Downtown.",
        "<b>Pet Policy</b><p>Pets Not Allowed</p></div>",
        "generic_signal_walk", tmp_path)
    assert audit["understating_records"] == 0
    assert audit["findings"][0]["charge_terms_only_in_accordion"] == []


def test_a_page_without_the_accordion_is_not_audited(tmp_path):
    audit = _audit_row(
        "Pet Policy Pets Welcome Maximum Pet Weight: 40.0lbs",
        "<div class='pb-2 t-font-s'>Pet Policy</div>",
        "pet_policy_heading_parent", tmp_path)
    assert audit["properties_on_the_accordion_template"] == 0


def test_the_run_flagged_exactly_one_understating_record():
    """17 of 17 scored usable, and one of those is still not safe to publish.

    Recorded so the headline number cannot be read as "17 clean records".
    """
    audit = run_report()["template_audit"]
    assert audit["properties_on_the_accordion_template"] == 3
    assert audit["reached_by_the_brand_locator"] == 0
    assert audit["understating_records"] == 1
    assert audit["held_for_review"] == ["The Trade, Autograph Collection"]


def test_the_run_acquired_and_read_every_marriott_property():
    doc = run_report()
    assert doc["subject_count"] == 17
    assert doc["subject_assertion_held"] is True
    assert doc["acquired"] == 17
    assert doc["usable_policy_successes"] == 17
    assert doc["unresolved"] == 0
    assert doc["refusals"] == 3


def test_the_run_used_the_committed_route_and_its_fallback():
    doc = run_report()
    assert doc["route_used"]["provider"] == PROVIDERS.BRIGHTDATA_BROWSER
    assert doc["provider_mix"] == {PROVIDERS.BRIGHTDATA_BROWSER: 15,
                                   PROVIDERS.BRIGHTDATA_WEB_UNLOCKER: 2}
    assert doc["fallback_uses"] == 2
    assert doc["cost"]["delta"]["firecrawl_credits_consumed"] == 0


def test_nothing_was_published_by_the_run():
    doc = run_report()
    assert doc["authority_written"] is False
    assert doc["published"] is False


def test_nothing_was_published_by_the_decision():
    doc = decision_report()
    assert doc["authority_written"] is False
    assert doc["published"] is False
    assert doc["readers_changed"] is False


def test_no_milwaukee_policy_authority_exists():
    found = list((REPO / "launch_packages" / "pettripfinder")
                 .rglob("*hotel_policy_facts*milwaukee*"))
    assert not found, found
