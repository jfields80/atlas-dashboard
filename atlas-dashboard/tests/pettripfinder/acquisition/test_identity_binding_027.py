"""PTF-CODELESS-INDEPENDENT-IDENTITY-BINDING-027.

WHAT THESE TESTS GUARD
----------------------
An identity gate is the one component where a false PASS is worse than any
number of false FAILs: a wrong binding publishes one hotel's policy under
another hotel's name, and nothing downstream can catch it. So the adversarial
half of this file is the important half, and it is deliberately larger than the
positive half.

The positives prove the repair does what it claims -- a hotel with no property
code and no two-segment path can bind when its page agrees with the census
about the building. The adversarials prove what it still refuses: a shared
domain, a shared street, a shared name in another state, a related-looking URL,
and a policy page that source discovery already validated.

Most of the pages here are real captures this corpus retained, because the
failure modes are real: one operator runs a Wildwood Lodge in Wisconsin and
another in Iowa and prints both telephone numbers in one footer, and 325 North
Brookfield Road holds two hotels with two census rows.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import fresh_proof_019a as PROOF
from scripts.pettripfinder.acquisition import identity_binding_027 as I
from scripts.pettripfinder.acquisition import identity_corpus_027 as CORPUS
from scripts.pettripfinder.brightdata import marriott_surface as MS
from scripts.pettripfinder.brightdata import policy_surface as PS


def _signals(**kwargs):
    return MS.IdentitySignals(**kwargs)


# --------------------------------------------------------------------------- #
# The cohort is derived, not listed.
# --------------------------------------------------------------------------- #

def test_the_identity_failure_cohort_is_ten_and_comes_from_026s_counters():
    keys = I.assert_cohort()
    assert len(keys) == 10
    counts = json.loads(I.COUNTS_026.read_text(encoding="utf-8"))
    declared = [row["identity_key"] for row
                in counts["acquisition_unresolved"]["queue"]
                if row["reason"] == "IDENTITY_FAILURE"]
    assert sorted(declared) == keys


# --------------------------------------------------------------------------- #
# 1 -- the exact canonical URL remains a strong positive.
# --------------------------------------------------------------------------- #

def test_a_matching_canonical_path_and_name_still_binds():
    """Cobblestone bound this way before the repair and must still bind.

    This is the rule the repair was NOT allowed to trade away: a code-less
    property whose canonical path is the path we asked for, with a name that
    agrees, was confirmed and stays confirmed.
    """
    case = next(c for c in CORPUS.CASES
                if c.case_id == "P1-cobblestone-canonical-path")
    result = I.evaluate_case(case)
    assert result["verdict"] == "PASS"
    assert result["binding_method"] == "CANONICAL_PATH_AND_NAME"
    assert "canonical_path" in result["matched"]


# --------------------------------------------------------------------------- #
# 2 -- code-less hotels can bind without canonical-path equality.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("case_id", ["P3-saint-kate-street-and-name",
                                     "P4-ingleside-street-and-name",
                                     "P5-marc-street-and-name"])
def test_a_codeless_hotel_binds_on_street_and_name_without_a_path(case_id):
    case = next(c for c in CORPUS.CASES if c.case_id == case_id)
    result = I.evaluate_case(case)
    assert result["verdict"] == "PASS"
    assert result["binding_method"] == "EXACT_ADDRESS_AND_NAME"
    # The point of the repair: no path signal was available at all.
    assert "canonical_path" not in result["matched"]


def test_a_self_declared_telephone_and_a_contained_name_bind():
    case = next(c for c in CORPUS.CASES
                if c.case_id == "P7-structured-phone-no-street")
    result = I.evaluate_case(case)
    assert result["verdict"] == "PASS"
    assert result["binding_method"] == "PHONE_AND_NAME"


# --------------------------------------------------------------------------- #
# 3 -- same domain alone cannot bind.
# --------------------------------------------------------------------------- #

def test_same_domain_is_not_an_identity():
    """A brand-wide FAQ on the property's own domain binds to nothing."""
    case = next(c for c in CORPUS.CASES if c.case_id == "A5-same-domain-generic-faq")
    result = I.evaluate_case(case)
    assert result["verdict"] == "FAIL"


def test_a_first_party_page_with_no_property_name_binds_to_nothing():
    case = next(c for c in CORPUS.CASES if c.case_id == "A7-contact-page-no-binding")
    result = I.evaluate_case(case)
    assert result["verdict"] == "FAIL"


def test_the_contract_has_no_same_domain_signal_at_all():
    """Not "domain agreement is outweighed" -- it is not a signal.

    A rule that scores the domain can be talked into binding by two weak
    agreements plus a shared host, which is how "this URL looks related"
    becomes "this is the property".
    """
    assert "domain" not in PS.PHYSICAL_SIGNALS
    assert "domain" not in PS.VETOING_SIGNALS
    source = (REPO / "atlas-dashboard" / "scripts" / "pettripfinder"
              / "brightdata" / "policy_surface.py").read_text(encoding="utf-8")
    body = source[source.index("def assess_identity("):
                  source.index("def path_identity(")]
    assert "registrable" not in body and "host_of" not in body


# --------------------------------------------------------------------------- #
# 4 -- weak name similarity alone cannot bind.
# --------------------------------------------------------------------------- #

def test_agreement_only_on_common_lodging_words_does_not_bind():
    case = next(c for c in CORPUS.CASES if c.case_id == "A6-common-name-tokens-only")
    result = I.evaluate_case(case)
    assert result["verdict"] == "FAIL"


def test_the_market_city_is_not_a_distinctive_token():
    overlap = PS.distinctive_overlap("Milwaukee Hotel Amenities",
                                     "The Plaza Hotel Milwaukee",
                                     locality="Milwaukee WI")
    assert overlap == frozenset()


def test_a_real_property_word_survives_the_generic_vocabulary():
    overlap = PS.distinctive_overlap("Dogs | The Iron Horse Hotel",
                                     "The Iron Horse Hotel",
                                     locality="Milwaukee WI")
    assert overlap == frozenset({"iron", "horse"})


# --------------------------------------------------------------------------- #
# 5 -- a wrong address blocks binding.
# --------------------------------------------------------------------------- #

def test_a_conflicting_street_blocks_binding_even_with_path_and_name():
    """The one deliberate withdrawal in this repair.

    The old rule confirmed on path and name because those were the only
    signals it had. A page that publishes a different street contradicts the
    census about which building it is, and once that is visible it has to fail
    closed -- including on the route that used to confirm without looking.
    """
    case = next(c for c in CORPUS.CASES
                if c.case_id == "A10-address-contradicts-census")
    result = I.evaluate_case(case)
    assert result["verdict"] == "FAIL"
    assert "street_identity" in result["conflicting"]
    assert "canonical_path" in result["matched"]


def test_a_street_without_a_house_number_is_no_signal_rather_than_a_conflict():
    assert PS._street_key("North Brookfield Road") == ""
    assert PS._street_key("325 North Brookfield Road") == "325 n brookfield rd"


def test_compass_words_are_folded_so_one_address_is_not_two():
    assert PS._street_key("1028 East Juneau Avenue") == \
        PS._street_key("1028 E. Juneau Avenue")


def test_the_zip_is_compared_separately_from_the_street():
    """A page's "53221-2824" and a census "53221" are one ZIP, not a conflict."""
    signals = _signals(name_on_page="Travelodge by Wyndham Milwaukee",
                       address_on_page="1716 W Layton Ave",
                       postal_code="53221-2824")
    result = PS.assess_identity(
        signals, expected_name="Travelodge by Wyndham Milwaukee",
        expected_property_code="", expected_url="https://example.com/",
        expected_postal_code="53221", expected_street="1716 W Layton Ave")
    assert "street_identity" in result.signals_matched
    assert "postal_code" in result.signals_matched
    assert not result.signals_conflicting


# --------------------------------------------------------------------------- #
# 6 -- the wrong property on the same operator's domain.
# --------------------------------------------------------------------------- #

def test_two_hotels_at_one_street_are_separated_by_the_name():
    """Motel 6 and Studio 6 share 325 North Brookfield Road.

    The street agrees for the honest reason that it IS the street. Only the
    name can tell the two census rows apart, so the code-less binding demands a
    name that contains or is contained by the other -- not a partial overlap.
    """
    case = next(c for c in CORPUS.CASES
                if c.case_id == "A3-same-operator-wrong-property-one-street")
    result = I.evaluate_case(case)
    assert result["verdict"] == "FAIL"
    assert "name" not in result["matched"]


@pytest.mark.parametrize("case_id", ["A1-same-name-wrong-city",
                                     "A2-same-name-wrong-city-faqs"])
def test_the_same_name_in_another_state_does_not_bind(case_id):
    case = next(c for c in CORPUS.CASES if c.case_id == case_id)
    result = I.evaluate_case(case)
    assert result["verdict"] == "FAIL"


def test_a_telephone_number_merely_printed_on_the_page_cannot_bind():
    """The Clive page prints the Pewaukee number; that must not be identity.

    A hotel group lists every location in one footer. Only the number the page
    declares as its own -- structured lodging data -- is allowed to confirm.
    """
    signals = _signals(name_on_page="Clive - Wildwood Lodge",
                       phones_on_page=("2625062000", "5152229876"))
    result = PS.assess_identity(
        signals, expected_name="Wildwood Lodge", expected_property_code="",
        expected_url="https://thewildwoodlodge.com/pewaukee/",
        expected_phone="2625062000", expected_locality="Pewaukee WI")
    assert not result.confirmed
    assert "phone" not in result.signals_matched


def test_a_different_declared_telephone_never_denies_an_identity():
    """One property publishes a front desk, a reservations and a toll-free line.

    Which one reaches the structured data is an authoring choice. A phone
    number may confirm here; it is never allowed to refuse.
    """
    signals = _signals(name_on_page="Potawatomi Casino Hotel",
                       address_on_page="1721 W Canal St", postal_code="53233",
                       phone_on_page="800-729-7244")
    result = PS.assess_identity(
        signals, expected_name="Potawatomi Casino Hotel",
        expected_property_code="", expected_url="https://example.com/",
        expected_postal_code="53233", expected_street="1721 W. Canal Street",
        expected_phone="8007298866", expected_locality="Milwaukee WI")
    assert "phone" not in result.signals_conflicting
    assert result.confirmed
    assert result.binding_method == "EXACT_ADDRESS_AND_NAME"


def test_an_unseparated_run_of_ten_digits_is_not_a_telephone_number():
    assert PS.phones_in("<p>order 4142768500 tracking</p>") == ()
    assert PS.phones_in('<a href="tel:+14142768500">call</a>') == ("4142768500",)
    assert PS.phones_in("<p>(414) 276-8500</p>") == ("4142768500",)


# --------------------------------------------------------------------------- #
# 7 -- property-code behaviour does not regress.
# --------------------------------------------------------------------------- #

def test_a_branded_property_still_binds_on_its_code():
    case = next(c for c in CORPUS.CASES if c.case_id == "P6-branded-property-code")
    result = I.evaluate_case(case)
    assert result["verdict"] == "PASS"
    assert result["binding_method"] == "PROPERTY_CODE"


def test_a_wrong_property_code_still_refuses_however_well_the_rest_agrees():
    signals = _signals(name_on_page="Hampton Inn Milwaukee Airport",
                       address_on_page="1200 W Airport Rd", postal_code="53221",
                       phone_on_page="414-555-0100",
                       property_code_on_page="mkeqqhx")
    result = PS.assess_identity(
        signals, expected_name="Hampton Inn Milwaukee Airport",
        expected_property_code="MKEAPHX",
        expected_url="https://www.hilton.com/en/hotels/mkeaphx-x/",
        expected_postal_code="53221", expected_street="1200 W Airport Rd",
        expected_phone="4145550100")
    assert not result.confirmed
    assert "property_code" in result.signals_conflicting


def test_the_codeless_route_is_unreachable_when_a_code_is_expected():
    """A branded property cannot fall back to street-and-name.

    Columbus holds three Embassy Suites whose names are token-identical; the
    code exists precisely because the softer signals cannot separate them, and
    a code-less shortcut on a coded brand would undo that.
    """
    signals = _signals(name_on_page="Embassy Suites Columbus",
                       address_on_page="2700 Corporate Exchange Dr",
                       postal_code="43231", property_code_on_page="")
    result = PS.assess_identity(
        signals, expected_name="Embassy Suites Columbus",
        expected_property_code="CMHAPES",
        expected_url="https://www.hilton.com/en/hotels/cmhapes-x/",
        expected_postal_code="43231",
        expected_street="2700 Corporate Exchange Dr")
    assert not result.confirmed
    assert result.binding_method == ""


# --------------------------------------------------------------------------- #
# 8 -- a discovered policy URL does not bypass identity.
# --------------------------------------------------------------------------- #

def test_a_validated_discovered_policy_url_does_not_confirm_an_identity():
    case = next(c for c in CORPUS.CASES
                if c.case_id == "A11-discovered-url-does-not-bypass")
    result = I.evaluate_case(case)
    assert result["verdict"] == "FAIL"


def test_source_provenance_is_not_among_the_signals():
    source = (REPO / "atlas-dashboard" / "scripts" / "pettripfinder"
              / "brightdata" / "policy_surface.py").read_text(encoding="utf-8")
    body = source[source.index("def assess_identity("):
                  source.index("def path_identity(")]
    for term in ("overlay", "discovered", "provenance", "source_origin"):
        assert term not in body


# --------------------------------------------------------------------------- #
# 9 / 10 -- the ten replay deterministically, and for free.
# --------------------------------------------------------------------------- #

def test_the_ten_replay_deterministically():
    first = I.replay_all()
    second = I.replay_all()
    assert [(row["identity_key"], row["new_verdict"], row["binding_method"],
             row["disposition"]) for row in first] == \
        [(row["identity_key"], row["new_verdict"], row["binding_method"],
          row["disposition"]) for row in second]
    assert len(first) == 10


def test_the_replay_contacts_no_provider():
    """Persisted evidence answers the identity question, so nothing is fetched.

    The legacy gate is warmed first: reading it costs a ``git show``, and the
    guard denies subprocess launches without being able to tell a repository
    read from a network call.
    """
    I.legacy_assess()
    with PROOF.no_provider_calls() as attempts:
        rows = I.replay_all()
    assert attempts == []
    assert len(rows) == 10


def test_every_replayed_row_explains_its_decision():
    for row in I.replay_all():
        assert row["previous_verdict"] == "FAIL"
        assert row["new_verdict"] in ("PASS", "FAIL", "UNDETERMINED")
        assert row["disposition"]
        assert row["disposition_why"]
        if row["new_verdict"] == "PASS":
            assert row["binding_method"]
            assert row["matched"]


def test_a_refused_capture_left_no_policy_block_so_policy_needs_a_capture():
    """Identity is free from disk; the policy is not.

    The gate runs before artifacts are written, and the canonical locator
    contract records a boundary at capture time on the live page. No retained
    discovery artifact carries one, so no amount of re-reading produces a
    publication-grade block.
    """
    for row in I.replay_all():
        assert row["policy_block_on_disk"] is False
        assert row["policy_requires_capture"] is True


def test_evidence_is_only_reused_for_the_url_that_was_actually_requested():
    index = I.retained_captures()
    assert all(isinstance(key, tuple) and len(key) == 2 for key in index)
    for row in I.replay_all():
        if row["artifact"]:
            assert (row["identity_key"],
                    row["selected_source_url"]) in index


# --------------------------------------------------------------------------- #
# The fixed corpus, and the blast radius.
# --------------------------------------------------------------------------- #

def test_the_fixed_corpus_is_complete_and_the_gate_agrees_with_all_of_it():
    summary = I.corpus_summary()
    assert summary["missing_artifacts"] == []
    assert summary["disagreeing"] == []
    assert summary["agreeing"] == summary["cases"]
    assert summary["adversarial"] >= summary["positives"]


def test_no_historical_capture_changes_verdict_from_the_rule_change_alone():
    """The rule is inert on everything already acquired.

    Fed the same inputs, old gate and new gate agree on every retained capture
    in the corpus. What recovers properties is the WIRING -- the census street
    and telephone finally reaching the gate -- and separating the two is the
    only way to say which did the work.
    """
    arm = I.blast_radius()["rule_only"]
    assert arm["fail_to_pass"] == 0
    assert arm["pass_to_fail"] == 0


def test_nothing_that_bound_before_stops_binding():
    radius = I.blast_radius()
    assert radius["as_production_ran"]["pass_to_fail"] == 0
    assert radius["captures_tested"] > 200


def test_every_newly_bound_capture_is_explained():
    radius = I.blast_radius()
    gained = [row for row in radius["changed"]
              if row["new"] == "PASS"
              and row["old_as_production_ran"] == "FAIL"]
    assert gained
    for row in gained:
        assert row["binding_method"] in ("EXACT_ADDRESS_AND_NAME",
                                         "PHONE_AND_NAME",
                                         "CANONICAL_PATH_AND_NAME")
        assert row["matched"]
        assert not row["conflicting"]


def test_no_branded_capture_is_among_the_newly_bound():
    """A property code decided those, and this repair did not touch that path."""
    rows = I.census()
    gained = [row for row in I.blast_radius()["changed"]
              if row["new"] == "PASS"]
    for row in gained:
        assert not rows[row["identity_key"]]["property_code"]


# --------------------------------------------------------------------------- #
# 11 / 12 / 13 -- the store, the authority, and publication.
# --------------------------------------------------------------------------- #

def test_the_store_keeps_one_row_per_identity():
    store = json.loads(I.STORE.read_text(encoding="utf-8-sig"))
    keys = [row["identity_key"] for row in store["items"]]
    assert len(keys) == len(set(keys))


def test_no_milwaukee_policy_authority_exists():
    root = REPO / "atlas-dashboard" / "launch_packages" / "pettripfinder"
    assert list(root.rglob("*hotel_policy_facts*milwaukee*")) == []
    store = json.loads(I.STORE.read_text(encoding="utf-8-sig"))
    assert store["authority_written"] is False
    assert store["founder_approvals_created"] == 0


def test_nothing_is_published():
    store = json.loads(I.STORE.read_text(encoding="utf-8-sig"))
    assert all(not row.get("published") for row in store["items"])


# --------------------------------------------------------------------------- #
# Freezes.
# --------------------------------------------------------------------------- #

def test_routes_and_providers_are_unchanged():
    for path in ("atlas-dashboard/scripts/pettripfinder/acquisition/routes.json",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/registry.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/router.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/providers.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/readers.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/source_discovery.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/source_selection.py",
                 "atlas-dashboard/scripts/pettripfinder/brightdata/policy_reading.py",
                 "atlas-dashboard/scripts/pettripfinder/brightdata/policy_locator.py",
                 "atlas-dashboard/launch_packages/pettripfinder/identity_census"):
        changed = subprocess.run(["git", "status", "--porcelain", "--", path],
                                 cwd=str(REPO), capture_output=True,
                                 text=True).stdout.strip()
        assert changed == "", "%s was modified by 027" % path


def test_the_policy_locator_contract_is_untouched():
    from pettripfinder.acquisition import locator_freeze as LOCATOR_FREEZE
    LOCATOR_FREEZE.assert_locator_surface_unchanged()


def test_this_work_order_writes_only_under_its_own_run_directory():
    """Historical evidence is READ here and never rewritten.

    ``data/`` is gitignored, so a ``git status`` check over it would pass
    vacuously and prove nothing. The real guarantee is structural: every path
    this module writes is under its own run id.
    """
    assert I.RUN_ROOT.name == I.RUN_ID
    assert I.JOURNAL.parent == I.RUN_ROOT
    assert I.RUN_DIR.parent == I.RUN_ROOT
    assert I.COST_PATH.parent == I.RUN_ROOT
    for path in (I.DISCOVERY_014, I.DIAGNOSTIC_013):
        assert I.RUN_ROOT not in path.parents and path != I.RUN_ROOT
