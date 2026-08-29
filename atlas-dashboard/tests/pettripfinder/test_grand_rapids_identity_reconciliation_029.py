# -*- coding: utf-8 -*-
"""PTF-GRAND-RAPIDS-IDENTITY-RECONCILIATION-029 -- six identities settled for nothing.

THE HEADLINE IS THAT THE TARGET IS REACHED, and it is reached by one row. 028
left the market at a projected 42 against a target of 43, with six captures
refused by the identity gate on a street SUFFIX and their bytes still on disk.
This pass rules on those six and reads exactly one of them.

THE IDENTITY RULE IS WHAT THESE TESTS MOSTLY GUARD. Two agreeing signals, at
least one of which is NOT a telephone. The second clause is the load-bearing
one: a switchboard is shared by every hotel in a building, and this market
holds three pairs open on exactly that evidence. A test therefore proves that a
telephone ALONE cannot confirm, whatever else agrees.

THE STOP RULE IS OBEYED RATHER THAN OPTIMISED AROUND. One pet-friendly row
reaches 43 and the reading stops there. Three confirmed rows are left unread on
purpose and reported as unread -- pinning that is how a later reader can tell
"we did not look" from "there was nothing there".

AND THE BRAND-PAGE WITHHOLDING IS TESTED FOR ORDER-INDEPENDENCE. Both Extended
Stay America captures print the right name and the right address on a page
titled "Explore Our Nationwide Hotel Locations". They are withheld BEFORE the
stop rule is consulted, so they cannot escape classification by an accident of
the alphabet.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.pettripfinder import grand_rapids_holland_identity_reconciliation_029 as R  # noqa: E402

LP = REPO_ROOT / "launch_packages" / "pettripfinder"
REPORT = LP / "grand_rapids_holland_mi_identity_reconciliation_029.json"
PACKET = LP / "grand_rapids_holland_mi_founder_review_packet_029.json"


def _load(path):
    assert path.is_file(), "%s is missing" % path.name
    return json.loads(path.read_text(encoding="utf-8-sig"))


@pytest.fixture(scope="module")
def report():
    return _load(REPORT)


@pytest.fixture(scope="module")
def packet():
    return _load(PACKET)


# --------------------------------------------------------------------------- #
# Nothing was spent
# --------------------------------------------------------------------------- #

def test_no_provider_was_called(report):
    assert report["provider_calls"] == 0
    assert report["usd_spent"] == 0.0
    assert report["plan_credits_spent"] == 0.0
    assert "already paid for" in report["nothing_was_fetched"]
    joined = " ".join(report["nothing_else_was_run"]).lower()
    for provider in ("places", "bright data", "firecrawl", "discovery",
                     "acquisition"):
        assert provider in joined


def test_the_ledgers_did_not_move():
    """A pass that calls nothing adds nothing to either ledger."""
    discovery = _load(LP / "ptf_discovery_attempt_ledger_001.json")
    assert len([a for a in discovery["attempts"]
                if a["market_id"] == "grand-rapids-holland-mi"]) == 40
    paid = _load(LP / "ptf_paid_attempt_ledger_001.json")
    assert len([a for a in paid["attempts"]
                if a["market_id"] == "grand-rapids-holland-mi"]) == 89


def test_the_saved_captures_were_not_altered(report):
    assert report["policy_reread"]["saved_captures_were_not_altered"] is True


# --------------------------------------------------------------------------- #
# The identity rule
# --------------------------------------------------------------------------- #

def test_all_six_were_reviewed_and_confirmed(report):
    review = report["identity_review"]
    assert review["reviewed"] == 6
    assert review["same_property_confirmed"] == 6
    assert review["distinct_property"] == 0
    assert review["hold_identity"] == 0
    assert dict(review["counts"]) == {R.SAME_PROPERTY: 6}


def test_every_confirmation_rests_on_a_non_telephone_signal(report):
    """The load-bearing clause. Five of the six state no telephone at all on
    the page, and the sixth has five other signals besides."""
    for row in report["identity_review"]["rows"]:
        assert row["verdict"] == R.SAME_PROPERTY
        assert row["signal_count"] >= R.MIN_SIGNALS
        assert row["non_telephone_signal_count"] >= 1
        assert row["signals_agreeing"]


def test_a_telephone_alone_can_never_confirm():
    """This market holds three pairs open on a shared switchboard. The rule has
    to refuse that case even when the telephone matches exactly."""
    row = {
        "identity_key": "a bare name",
        "census": {"canonical_name": "Comfort Inn", "address": "",
                   "postal_code": "49418", "phone": "6166670733"},
        "places": {"returned_phone": "(616) 667-0733",
                   "premises_agreement": {}},
        "page_name": "", "page_address": "", "page_postal": "",
        "page_telephone": "", "page_title": "", "source_url": "",
        "declined_directory": "", "gate_detail": "",
    }
    signals = R.identity_signals(row)
    assert [s["signal"] for s in signals] == ["TELEPHONE"]
    ruling = R.rule_identity(row, {})
    assert ruling["verdict"] == R.HOLD_IDENTITY
    assert "switchboard is shared" in ruling["why"]


def test_nothing_agreeing_is_a_distinct_property():
    row = {
        "identity_key": "somewhere else",
        "census": {"canonical_name": "Riviera Motel",
                   "address": "4350 Remembrance Rd NW",
                   "postal_code": "49534", "phone": "6164532404"},
        "places": {"returned_phone": "", "premises_agreement": {}},
        "page_name": "Hotel Indigo Detroit", "page_address": "1000 Woodward Ave",
        "page_postal": "", "page_telephone": "", "page_title": "",
        "source_url": "", "declined_directory": "", "gate_detail": "",
    }
    assert R.rule_identity(row, {})["verdict"] == R.DISTINCT_PROPERTY


def test_an_identity_another_order_holds_open_is_not_closed_here(report):
    """019 opened two identity questions. A pass asked to reconcile a capture
    may not close one of them as a side effect."""
    row = {
        "identity_key": "comfort inn",
        "census": {"canonical_name": "Comfort Inn",
                   "address": "4520 Kenowa Avenue Southwest",
                   "postal_code": "49418", "phone": "6166670733"},
        "places": {"returned_phone": "", "premises_agreement": {}},
        "page_name": "Comfort Inn", "page_address": "4520 Kenowa Ave SW",
        "page_postal": "", "page_telephone": "", "page_title": "",
        "source_url": "", "declined_directory": "", "gate_detail": "",
    }
    prior = R.prior_identity_rulings()
    assert "comfort inn" in prior
    ruling = R.rule_identity(row, prior)
    assert ruling["verdict"] == R.HOLD_IDENTITY
    assert "may not close an identity question another order opened" in \
        ruling["why"]


def test_the_gate_declined_them_on_a_suffix_not_a_building(report):
    for row in report["identity_review"]["rows"]:
        assert "does not agree with expected" in row["gate_declined_because"]
        signals = {s["signal"] for s in row["signals_agreeing"]}
        assert "STREET_NUMBER" in signals, (
            "the street NUMBER agrees on every one of them; only the suffix "
            "differed")


# --------------------------------------------------------------------------- #
# The policy re-read
# --------------------------------------------------------------------------- #

def test_the_reread_uses_the_committed_locator_and_reader(report):
    assert "locate_policy_in_html" in report["policy_reread"]["stack"]
    assert "policy_reading.parse" in report["policy_reread"]["stack"]


def test_exactly_one_row_was_read_and_it_is_pet_friendly(report):
    counts = dict(report["policy_reread"]["counts"])
    assert counts.get(R.PET_FRIENDLY) == 1
    read = [r for r in report["policy_reread"]["rows"]
            if r["classification"] == R.PET_FRIENDLY]
    assert len(read) == 1
    row = read[0]
    assert row["identity_key"] == "comfort inn airport"
    assert row["reading"]["located"] is True
    assert row["reading"]["pets_allowed"] is True


def test_the_reading_is_the_labelled_block_not_the_amenity_chip(report):
    """The Comfort Inn page prints "Pet Friendly*" in a list beside "Free WiFi"
    and "Fitness Center". The order forbids inferring from an amenity token,
    and the locator does not: it finds the labelled statement."""
    row = [r for r in report["policy_reread"]["rows"]
           if r["classification"] == R.PET_FRIENDLY][0]
    block = row["reading"]["block"]
    assert "Pets are allowed" in block
    assert "25.00 USD Per Night Per Pet" in block
    assert "Pet Friendly*" not in block
    assert "Free WiFi" not in block


def test_the_service_animal_sentence_is_not_the_permission(report):
    """It evidences its OWN field and is never the reason pets are allowed.

    The block ends "Service animals are permitted, without charge", and the
    reader does quote that -- as the evidence for ``service_animal_exception``.
    What must never happen is the PERMISSION resting on it, which is why the
    leading quote is checked rather than the quote list as a whole.
    """
    row = [r for r in report["policy_reread"]["rows"]
           if r["classification"] == R.PET_FRIENDLY][0]
    extraction = row["reading"]["extraction"]
    quotes = row["reading"]["evidence_quotes"]

    assert extraction["pets_allowed"] is True
    assert quotes[0] == "Pets are allowed", (
        "the permission is evidenced by the pets sentence, first")
    assert "service" not in quotes[0].lower()

    # The service-animal sentence is present, and it is bound to its own field.
    assert extraction["service_animal_exception"] == \
        "Service animals are permitted, without charge."
    assert any("service animal" in q.lower() for q in quotes)


def test_the_extraction_carries_the_property_specific_facts(report):
    row = [r for r in report["policy_reread"]["rows"]
           if r["classification"] == R.PET_FRIENDLY][0]
    extraction = row["reading"]["extraction"]
    assert extraction["pet_fee"] == 2500
    assert extraction["fee_basis"] == "per_night"
    assert extraction["fee_scope"] == "per_pet"
    assert extraction["pet_deposit"] == 10000
    assert extraction["species_allowed"] == ["dog"]


# --------------------------------------------------------------------------- #
# The brand-page withholding, and the stop rule
# --------------------------------------------------------------------------- #

def test_both_extended_stay_america_rows_are_withheld(report):
    counts = dict(report["policy_reread"]["counts"])
    assert counts.get(R.WITHHELD_BRAND_PAGE) == 2
    withheld = [r for r in report["policy_reread"]["rows"]
                if r["classification"] == R.WITHHELD_BRAND_PAGE]
    assert {r["identity_key"] for r in withheld} == {
        "extended stay america select suites grand rapids kentwood",
        "extended stay america select suites grand rapids wyoming"}
    for row in withheld:
        assert "directory of properties" in row["why"]


def test_the_withholding_does_not_depend_on_where_the_stop_landed():
    """Tested as a rule rather than as an outcome: the ESA rows sort AFTER the
    row that stopped the reading, so a check placed downstream of the stop
    would have looked correct while doing nothing."""
    esa = {"page_title": "Explore Our Nationwide Hotel Locations | "
                         "Extended Stay America"}
    specific, why = R.page_is_property_specific(esa)
    assert specific is False
    assert "directory of properties" in why
    single = {"page_title": "Hotel in Grand Rapids, MI | Comfort Inn Grand "
                            "Rapids Airport"}
    assert R.page_is_property_specific(single)[0] is True


def test_the_stop_rule_fired_and_left_rows_deliberately_unread(report):
    stop = report["stop_rule"]
    assert stop["stopped_after"] == "comfort inn airport"
    assert stop["rows_left_unread"] == 3
    unread = [r for r in report["policy_reread"]["rows"]
              if r["classification"] == R.NOT_READ]
    assert {r["identity_key"] for r in unread} == {
        "holiday inn grand rapids airport",
        "staybridge suites grand rapids airport",
        "woodspring suites grand rapids kentwood"}
    assert "SAME_PROPERTY_CONFIRMED" in stop["their_identity_is_settled"]
    assert "bytes are on disk" in stop["their_identity_is_settled"]


def test_unread_is_distinguishable_from_empty(report):
    """"We did not look" and "there was nothing there" are different facts and
    a later reader must be able to tell them apart."""
    for row in report["policy_reread"]["rows"]:
        if row["classification"] == R.NOT_READ:
            assert "reading" not in row
            assert "stop" in row["why"] or "target was reached" in row["why"]


# --------------------------------------------------------------------------- #
# The target
# --------------------------------------------------------------------------- #

def test_the_market_reaches_43(report):
    target = report["target"]
    assert target["published_today"] == 35
    assert target["clean_pet_friendly_from_028"] == 7
    assert target["additional_pet_friendly_recovered"] == 1
    assert target["additional_verified_no_pets_recovered"] == 0
    assert target["clean_pet_friendly_candidates_total"] == 8
    assert target["projected_final_published_pet_friendly"] == 43
    assert target["target_reached"] is True


def test_projected_is_not_published(report):
    assert "PROJECTED, not published" in report["target"]["caveat"]
    assert "a FACT ruling is not a RECORD approval" in report["target"]["caveat"]


def test_cityflats_is_out_of_scope_and_says_why(report):
    unresolved = report["unresolved_remaining"]
    assert unresolved["unexpected_page_from_028"] == ["cityflatshotel grand rapids"]
    assert "kept no artifact" in unresolved["why_cityflats_is_not_here"]


# --------------------------------------------------------------------------- #
# The founder packet
# --------------------------------------------------------------------------- #

def test_the_packet_carries_both_passes_and_signs_nothing(packet):
    assert packet["counts"]["pet_friendly_from_028"] == 7
    assert packet["counts"]["verified_no_pets_from_028"] == 6
    assert packet["counts"]["newly_resolved_in_029"] == 1
    assert packet["counts"]["pet_friendly_total"] == 8
    assert packet["founder_decision"] == ""
    assert packet["founder_reviewer_id"] == ""
    assert packet["founder_reviewed_at"] == ""
    assert packet["review_status"] == "MACHINE_REVIEWED_PENDING_OPERATOR"
    assert "never sign an approval in the operator's name" in \
        packet["nothing_is_signed_here"]
    for group in ("pet_friendly_candidates_from_028",
                  "verified_no_pets_from_028", "newly_resolved_in_029"):
        for row in packet[group]:
            assert row["founder_decision"] == ""


def test_the_reconciled_row_asks_for_two_rulings_not_one(packet):
    """It was declined by the identity gate. Approving its policy without
    ruling on its identity would publish a record on evidence the gate
    refused."""
    row = packet["newly_resolved_in_029"][0]
    assert row["identity_key"] == "comfort inn airport"
    assert row["identity_verdict"] == R.SAME_PROPERTY
    assert "identity ruling AND a record approval" in row["needs"]
    assert row["policy_block"]
    assert row["extraction"]["pets_allowed"] is True


def test_the_packet_names_what_is_still_open(packet):
    still_open = packet["still_open_but_settled_on_identity"]
    assert len(still_open["left_unread_by_the_stop_rule"]) == 3
    assert len(still_open["withheld_brand_pages"]) == 2
    assert packet["remaining_identity_holds"] == []


def test_the_packet_agrees_with_the_report_on_the_target(packet, report):
    assert packet["target"]["if_every_row_here_is_approved"] == \
        report["target"]["projected_final_published_pet_friendly"] == 43
    assert packet["target"]["target_reached"] is True


# --------------------------------------------------------------------------- #
# Nothing else moved
# --------------------------------------------------------------------------- #

def test_no_authority_was_written():
    import subprocess
    result = subprocess.run(
        ["git", "status", "--porcelain", "--",
         "launch_packages/pettripfinder/markets",
         "launch_packages/pettripfinder/identity_census",
         "launch_packages/pettripfinder/hotel_policy_facts_grand-rapids-holland-mi.json",
         "deploy/netlify"],
        cwd=str(REPO_ROOT.parent), capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "", (
        "a reconciliation writes no authority: %r" % result.stdout)


def test_the_published_count_did_not_move():
    package = _load(LP / "hotel_policy_facts_grand-rapids-holland-mi.json")
    assert package["count"] == 35
