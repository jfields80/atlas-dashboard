"""PTF-CINCINNATI-MAINSTAY-IDENTITY-012 -- when the answer is "two hotels".

The census row "Comfort Suites Mainstay Hotel" was held because three of four
identity signals disagreed with its property page. The reason turned out not to
be a rename or a stale field: Choice's own listing shows TWO properties at 2347
Reading Road, oh720 in Building A and oh721 in Building B, with two phones and
two review counts. One census identity was standing where two hotels are.

The pressure in an order like this runs one way -- toward resolving. Both
properties refuse pets, the market has been held on this row for four orders,
and registering the refusal would close it. These tests exist because that
would have been wrong:

* an exclusion record carries ONE canonical name, street, postal code, phone
  and URL, and its normalized_name must derive from its canonical name. One
  record for two hotels is wrong about all of them for whichever hotel a reader
  wanted;
* the row keeps its route, because a withdrawn route is how a row stops being
  worked and this one still needs working;
* the routing record's own binding claim was overstated, and correcting a false
  claim is not the same as resolving the identity.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.pettripfinder import cincinnati_mainstay_identity_012 as M

REPO_ROOT = Path(__file__).resolve().parents[2]
PKG = REPO_ROOT / "launch_packages" / "pettripfinder"
AUTH = PKG / "markets" / "authority" / "cincinnati-oh"
CENSUS = PKG / "identity_census" / "cincinnati-oh.json"
PARTITION = PKG / "cincinnati_final_partition_001.json"
FINDING = PKG / "markets" / "reports" / "cincinnati_mainstay_identity_012.json"
PACKAGE = PKG / "hotel_policy_facts_cincinnati-oh.json"

KEY = "comfort suites mainstay hotel"


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


@pytest.fixture(scope="module")
def finding():
    return _load(FINDING)


LEDGER = PKG / "markets" / "reports" / "cincinnati_mainstay_census_split_013.json"


@pytest.fixture(scope="module")
def census_row():
    """The row as THIS order left it.

    PTF-CINCINNATI-MAINSTAY-CENSUS-SPLIT-013 retired it and put two real
    identities in its place, so it is no longer in the live census. The split
    ledger preserves it verbatim precisely so this order's work stays
    auditable, and reading it from there asserts the same facts against the
    same bytes rather than quietly re-scoping the test to whatever survived.
    """
    return _load(LEDGER)["retired_identity_census_row"]


@pytest.fixture(scope="module")
def route():
    """Likewise the route, preserved whole in the split ledger."""
    return _load(LEDGER)["retired_identity"]["route_retired"]


# ------------------------------------------------------------ it cost nothing

def test_the_determination_cost_nothing(finding):
    assert finding["provider_calls"] == 0
    assert finding["paid_spend_usd"] == 0.0
    assert finding["capture_method"] == "attended_chrome_render"


# ------------------------------------------------------------ the two hotels

def test_two_distinct_properties_share_the_street(finding):
    """The finding, and the whole reason this is not a rename."""
    observed = finding["observed_first_party"]
    assert set(observed) == {"oh720", "oh721"}
    a, b = observed["oh720"], observed["oh721"]
    assert a["street"].endswith("Building A")
    assert b["street"].endswith("Building B")
    assert a["street"].split(",")[0] == b["street"].split(",")[0] == \
        "2347 Reading Road"
    # Everything that distinguishes them.
    assert a["property_code"] != b["property_code"]
    assert a["phone"] != b["phone"]
    assert a["name"] != b["name"]
    assert a["reviews"] != b["reviews"]
    assert a["sha256_page"] != b["sha256_page"]


def test_the_census_row_matches_neither_property(finding, census_row):
    """Its phone matches neither and its postal code matches neither."""
    observed = finding["observed_first_party"]
    phones = {p["phone"] for p in observed.values()}
    postals = {p["postal_code"] for p in observed.values()}
    assert census_row["phone"] not in phones
    assert census_row["postal_code"] not in postals
    assert postals == {"45202"}
    assert census_row["postal_code"] == "45219"


def test_the_classification_is_separate_building(finding, census_row):
    assert finding["classification"] == "SEPARATE_BUILDING_IDENTITY"
    assert census_row["identity_review"]["classification"] == \
        "SEPARATE_BUILDING_IDENTITY"
    assert "not_a_rename" in census_row["identity_review"]


def test_a_shared_street_number_did_not_merge_anything(finding):
    """The weakest signal in the set is the only one they share."""
    assert "weakest signal" in finding["why_the_stronger_signals_win"]
    assert finding["policy_may_bind"] is False


def test_the_other_mainstay_was_not_merged_in(finding, census_row):
    """Brand similarity is not identity. Blue Ash is a different property."""
    affected = finding["other_identities_affected"]
    assert len(affected) == 1
    assert affected[0]["identity_key"] == "mainstay suites cincinnati blue ash"
    assert affected[0]["effect"].startswith("none")
    assert census_row["identity_review"]["not_merged_with"] == \
        "mainstay suites cincinnati blue ash"
    blue_ash = next(h for h in _load(CENSUS)["hotels"]
                    if h["identity_key"] == "mainstay suites cincinnati blue ash")
    assert blue_ash["postal_code"] == "45242"
    assert blue_ash["identity_state"] == "IDENTITY_UNRESOLVED"


# --------------------------------------------------- nothing was published

def test_no_policy_was_bound_to_the_unconfirmed_identity():
    """Both hotels refuse pets. That is not a reason to publish one record."""
    published = {h["identity_key"] for h in _load(PACKAGE)["hotels"]}
    excluded = {e["normalized_name"] for e in
                _load(AUTH / "hotel_exclusions.json")["exclusions"]}
    assert KEY not in published
    assert KEY not in excluded
    for code in ("oh720", "oh721"):
        assert code not in " ".join(published | excluded)


def test_the_refusal_was_withheld_for_a_stated_reason(census_row):
    reason = census_row["identity_review"]["policy_withheld"]
    assert "normalized_name must derive" in reason
    assert "two hotels are one" in reason


def test_no_census_identity_was_added_or_renamed(census_row):
    """This order is forbidden from adding identities, and did not."""
    assert census_row["identity_key"] == KEY
    assert census_row["canonical_name"] == "Comfort Suites Mainstay Hotel"
    assert census_row["address"] == "2347 Reading Rd."
    assert census_row["postal_code"] == "45219"
    assert census_row["phone"] == "5133946073"
    assert census_row.get("prior_identity_key", "") == ""
    assert "rename" not in census_row
    # The census was 256 when this order ran, and this order added nothing.
    ledger = _load(LEDGER)
    assert ledger["census_arithmetic"]["before"] == 256
    assert ledger["retired_identity"]["identity_key"] == KEY


def test_this_order_itself_changed_no_authority():
    """It asserted 99/47/152/104, which was the live state when it ran.

    PTF-CINCINNATI-MAINSTAY-CENSUS-SPLIT-013 then acted on this order's
    determination and moved them. What THIS order is entitled to claim is that
    IT changed nothing -- and that claim is in its own artifact, not in a
    market total that a later order is supposed to move.
    """
    assert _load(FINDING)["authority_change"] == "none"
    assert _load(FINDING)["policy_may_bind"] is False


# ------------------------------------------------------ the row keeps working

def test_the_row_was_left_unresolved_for_the_split_to_act_on(finding):
    """This order held the row; SPLIT-013 retired it and put two in its place.

    Asserting the row is still in the partition would make this test fail on
    its own finding being acted on, so what is pinned is that this order
    handed the split on with the reason, and that the successors exist.
    """
    follow = finding["follow_up_required"]
    assert follow["work_order"] == "PTF-CINCINNATI-MAINSTAY-CENSUS-SPLIT-013"
    keys = {i["identity_key"] for i in _load(PARTITION)["items"]}
    assert KEY not in keys
    assert "comfort suites cincinnati university downtown" in keys
    assert "mainstay suites cincinnati university uptown" in keys


def test_the_route_was_left_active_for_the_split_to_retire(route, finding):
    """A withdrawn route is how a row stops being worked.

    This order kept it so the row would keep being worked, and SPLIT-013 then
    retired it in favour of one route per real property -- which is the work
    getting done, not the route being abandoned.
    """
    assert route["status"] == "ROUTING_CONFIRMED"
    assert finding["route_remains_active"] is True
    live = {r["hotel_ref"]["identity_key"]
            for r in _load(AUTH / "identity_routing.json")["routes"]}
    assert KEY not in live
    assert "comfort suites cincinnati university downtown" in live
    assert "mainstay suites cincinnati university uptown" in live


# ----------------------------------------------- the overstated binding claim

def test_the_false_binding_signals_were_removed(route, finding):
    """The record claimed postal_code and phone matched. Neither does."""
    correction = finding["routing_signal_correction"]
    assert set(correction["removed"]) == {"binding:postal_code",
                                          "binding:phone"}
    assert "binding:postal_code" in correction["claimed"]
    assert "binding:phone" in correction["claimed"]
    assert "binding:postal_code" not in route["identity_signals_matched"]
    assert "binding:phone" not in route["identity_signals_matched"]
    assert route["identity_signals_matched"] == M.TRUE_SIGNALS


def test_the_surviving_signals_are_ones_that_actually_hold(route, finding):
    observed = finding["observed_first_party"]["oh721"]
    census = finding["census_before"]
    assert "binding:property_code" in route["identity_signals_matched"]
    assert observed["property_code"] == census["route_property_code"] == "oh721"
    assert "binding:city" in route["identity_signals_matched"]
    assert observed["city"] == "Cincinnati"
    # The street NUMBER is shared; the full street is not, which is why the
    # signal was split rather than left as a single "binding:street".
    assert "binding:street_number" in route["identity_signals_matched"]
    assert observed["street"].startswith("2347 Reading Road")
    assert census["census_street"] == "2347 Reading Rd."


def test_the_note_records_the_conflation_not_a_resolution(route):
    note = route["notes"]
    assert "IDENTITY CONFLATION" in note
    assert "oh720" in note and "oh721" in note
    assert "Building A" in note and "Building B" in note
    assert "NOT done here" in note


def test_the_correction_explains_where_the_false_claim_came_from(finding):
    why = finding["routing_signal_correction"]["why"]
    assert "BRAND_PROPERTY_URL_FOUND_2OF3" in why
    assert "template rather than a measurement" in why


def test_running_it_again_refuses(census_row):
    """Idempotence by refusal.

    When this order ran, the guard refused because the row already carried an
    identity_review. It still refuses, now because SPLIT-013 removed the row
    entirely -- either way it cannot run twice.
    """
    assert census_row.get("identity_review")
    with pytest.raises(M.IdentityError):
        M.build()


# ------------------------------------------------------------- the follow-up

def test_the_split_is_handed_on_with_its_evidence(finding):
    follow = finding["follow_up_required"]
    assert follow["work_order"] == "PTF-CINCINNATI-MAINSTAY-CENSUS-SPLIT-013"
    assert "forbidden from adding census identities" in follow["why_not_here"]
    assert "no new acquisition" in follow["evidence_already_owned"]
    # Both property pages' digests are already recorded, so the split is free.
    for prop in finding["observed_first_party"].values():
        assert prop["sha256_page"]
        assert prop["official_property_url"].startswith("https://")
        assert prop["pets"].startswith("Pets Allowed: No")
