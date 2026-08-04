"""PTF-FEES-RENDER -- staged fee schedules and tiered fee ceilings on a profile.

Extraction can now read two dimensions the older fields could not carry, and
until this change both were extracted, evidenced, and silently invisible:

  * a STAGED fee -- "$45 for the 1st night and $10 for each additional night".
    There is no single "the fee". Showing $45 alone prices exactly one night and
    understates every longer stay;

  * a TIERED CEILING -- "a maximum of 75 dollars for stays 1 to 6 nights and 150
    dollars for 7 or more nights". A ceiling is not a charge. At a property
    charging $25 a night, showing the $75 six-night ceiling as the charge would
    treble a one-night stay.

These tests pin the wording, the fail-closed behaviour on partial data, and --
most of all -- that neither field disturbs a page that does not carry it.

Offline: no network, no browser, no production write.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from scripts.pettripfinder.hotel_profile import (
    HotelProfileVM, _verified_details, _verified_facts, _verified_summary,
    cap_tier_sentence, cap_tiers, render_hotel_profile, staged_fee,
    staged_fee_sentence,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_FACTS = REPO_ROOT / "launch_packages" / "pettripfinder" / "hotel_policy_facts.json"

# The facts exactly as the deterministic extractor produced them for the two
# captured properties, and the official wording that accompanies them.
HAWTHORN_EVIDENCE = (
    "Pets with a max weight of 40 lbs each are allowed for a non-refundable fee "
    "of 45 USD for the 1st night and 10 USD for each additional night to a "
    "maximum of 180USD per stay.")
HAWTHORN = {
    "pets_allowed": "true",
    "weight_limit": "40.0 pounds",
    "fee_schedule": {
        "first_night": {"amount": "45.00", "currency": "USD",
                        "basis": "first night", "evidence_quote": HAWTHORN_EVIDENCE},
        "additional_night": {"amount": "10.00", "currency": "USD",
                             "basis": "each additional night",
                             "evidence_quote": HAWTHORN_EVIDENCE},
        "evidence_quote": HAWTHORN_EVIDENCE,
    },
    "fee_cap": {"amount": "180.00", "currency": "USD", "basis": "per stay",
                "evidence_quote": HAWTHORN_EVIDENCE},
}

CANDLEWOOD_EVIDENCE = (
    "Nonrefundable pet fee of 25 dollars per night with a maximum of 75 dollars "
    "for stays 1 to 6 nights and 150 dollars for 7 or more nights.")
CANDLEWOOD = {
    "pets_allowed": "true",
    "species_allowed": "dogs, cats",
    "pet_count_limit": "2",
    "pet_fee": "$25.00",
    "fee_basis": "per night",
    "fee_cap_tiers": [
        {"amount": "75.00", "currency": "USD", "min_nights": 1, "max_nights": 6,
         "evidence_quote": CANDLEWOOD_EVIDENCE},
        {"amount": "150.00", "currency": "USD", "min_nights": 7, "max_nights": "",
         "evidence_quote": CANDLEWOOD_EVIDENCE},
    ],
}

FLAT_FEE = {"pets_allowed": "true", "species_allowed": "dogs, cats",
            "pet_fee": "$100.00", "fee_basis": "per stay",
            "pet_count_limit": "2", "weight_limit": "75.0 pounds"}

TIERED = {"pets_allowed": "true", "species_allowed": "dogs, cats",
          "pet_count_limit": "2", "weight_limit": "50 pounds",
          "fee_tiers": [
              {"role": "ONE_TIME_CHARGE", "amount": "75.00", "currency": "USD",
               "basis": "one_time", "scope": "unstated", "condition_min": 1,
               "condition_max": 4, "boundary_unit": "nights"},
              {"role": "ONE_TIME_CHARGE", "amount": "125.00", "currency": "USD",
               "basis": "one_time", "scope": "unstated", "condition_min": 5,
               "condition_max": None, "boundary_unit": "nights"}]}


def _rows(f, evidence=""):
    return {label: value for label, value, _cls in _verified_details(f)[0]}


def _chips(f):
    return {label: value for label, value, _cls in _verified_facts(f)}


# --------------------------------------------------------------------------- #
# 1. The staged schedule.
# --------------------------------------------------------------------------- #

def test_hawthorn_states_both_stages_and_flattens_neither():
    assert staged_fee(HAWTHORN) == ("$45", "$10")
    summary = _verified_summary(HAWTHORN, HAWTHORN_EVIDENCE)
    assert ("A non-refundable pet fee of $45 applies for the first night and "
            "$10 for each additional night.") in summary


def test_hawthorn_details_give_each_stage_its_own_row():
    rows = _rows(HAWTHORN)
    assert rows["Pet charge, first night"] == "$45"
    assert rows["Pet charge, each additional night"] == "$10"
    assert "Pet charge" not in rows          # never a single flattened charge


def test_hawthorn_chip_names_both_stages():
    chips = _chips(HAWTHORN)
    assert chips["Pet charge"] == "$45 first night, then $10"
    assert chips["Charge basis"] == "Staged by night"


def test_hawthorn_cap_is_rendered_separately_from_the_schedule():
    """A ceiling is not one of the stages and never joins their sentence."""
    summary = _verified_summary(HAWTHORN, HAWTHORN_EVIDENCE)
    assert "A maximum of $180 per stay applies." in summary
    assert "$180" not in staged_fee_sentence(HAWTHORN, HAWTHORN_EVIDENCE)
    assert _rows(HAWTHORN)["Maximum total"] == "$180 per stay"


def test_the_staged_basis_is_stated_not_left_blank():
    assert _rows(HAWTHORN)["Charge basis"] == (
        "Staged: the first night is charged at a different rate from each "
        "additional night.")


# --------------------------------------------------------------------------- #
# 2. Tiered ceilings.
# --------------------------------------------------------------------------- #

def test_candlewood_renders_every_tier_in_order():
    summary = _verified_summary(CANDLEWOOD, CANDLEWOOD_EVIDENCE)
    assert ("A maximum of $75 applies for stays of 1–6 nights, and $150 for "
            "stays of 7 or more nights.") in summary


def test_candlewood_keeps_the_nightly_rate_as_the_charge():
    """The $25 rate is what a guest pays per night; the tiers only bound it."""
    summary = _verified_summary(CANDLEWOOD, CANDLEWOOD_EVIDENCE)
    assert "A $25 non-refundable fee applies per night." in summary
    assert _chips(CANDLEWOOD)["Pet charge"] == "$25.00"
    assert _chips(CANDLEWOOD)["Charge basis"] == "Per night"


def test_a_ceiling_tier_is_never_labelled_a_pet_fee():
    rows = _rows(CANDLEWOOD)
    assert rows["Maximum total, stays of 1–6 nights"] == "$75"
    assert rows["Maximum total, stays of 7 or more nights"] == "$150"
    assert "Pet charge, stays of 1–6 nights" not in rows
    summary = _verified_summary(CANDLEWOOD, CANDLEWOOD_EVIDENCE)
    assert "fee of $75" not in summary and "fee of $150" not in summary


def test_a_single_tier_renders_without_a_conjunction():
    one = {"pets_allowed": "true", "pet_fee": "$25.00", "fee_basis": "per night",
           "fee_cap_tiers": [{"amount": "75.00", "currency": "USD",
                              "min_nights": 1, "max_nights": 6}]}
    assert cap_tier_sentence(cap_tiers(one)) == (
        "A maximum of $75 applies for stays of 1–6 nights.")


def test_a_three_tier_ladder_renders_every_rung():
    three = copy.deepcopy(CANDLEWOOD)
    three["fee_cap_tiers"] = [
        {"amount": "50.00", "min_nights": 1, "max_nights": 1},
        {"amount": "75.00", "min_nights": 2, "max_nights": 6},
        {"amount": "150.00", "min_nights": 7, "max_nights": ""},
    ]
    sentence = cap_tier_sentence(cap_tiers(three))
    assert sentence == ("A maximum of $50 applies for stays of 1 night, and $75 "
                        "for stays of 2–6 nights, and $150 for stays of 7 or "
                        "more nights.")


def test_a_tier_basis_is_shown_only_where_the_source_states_one():
    with_basis = {"pets_allowed": "true", "pet_fee": "$25.00",
                  "fee_cap_tiers": [{"amount": "75.00", "min_nights": 1,
                                     "max_nights": 6, "basis": "per stay"}]}
    assert "for stays of 1–6 nights" in cap_tier_sentence(cap_tiers(with_basis))
    assert "$75 per stay" in cap_tier_sentence(cap_tiers(with_basis))
    assert "per stay" not in cap_tier_sentence(cap_tiers(CANDLEWOOD))


# --------------------------------------------------------------------------- #
# 3. Partial and malformed data fails closed.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("missing", ["first_night", "additional_night"])
def test_half_a_schedule_renders_nothing(missing):
    """One stage alone reads as the whole price. Better to show no fee."""
    half = copy.deepcopy(HAWTHORN)
    del half["fee_schedule"][missing]
    assert staged_fee(half) == ("", "")
    summary = _verified_summary(half, HAWTHORN_EVIDENCE)
    assert "first night" not in summary and "additional night" not in summary
    assert "$45" not in summary and "$10" not in summary


@pytest.mark.parametrize("schedule", [
    None, {}, "45 USD", [], {"first_night": {}, "additional_night": {}},
    {"first_night": {"amount": ""}, "additional_night": {"amount": "10.00"}},
])
def test_a_malformed_schedule_never_reaches_the_page(schedule):
    f = dict(HAWTHORN, fee_schedule=schedule)
    assert staged_fee(f) == ("", "")
    _verified_summary(f, HAWTHORN_EVIDENCE)     # must not raise
    _verified_facts(f)
    _verified_details(f)


@pytest.mark.parametrize("tiers", [
    None, {}, "75", [], [{"amount": "75.00"}],                  # no stay window
    [{"min_nights": 1, "max_nights": 6}],                       # no amount
    [{"amount": "75.00", "min_nights": 1, "max_nights": 6}, {"amount": ""}],
])
def test_a_malformed_ceiling_ladder_renders_nothing(tiers):
    f = dict(CANDLEWOOD, fee_cap_tiers=tiers)
    assert cap_tiers(f) == ()
    summary = _verified_summary(f, CANDLEWOOD_EVIDENCE)
    assert "maximum" not in summary.lower()
    _verified_facts(f)
    _verified_details(f)


def test_no_empty_container_is_rendered():
    f = dict(CANDLEWOOD, fee_cap_tiers=[])
    rows = _rows(f)
    assert not any(label.startswith("Maximum total") for label in rows)
    assert not any(value == "" for value in rows.values())


def test_a_record_carrying_only_a_schedule_is_not_called_fee_less():
    only = {"pets_allowed": "true", "fee_schedule": HAWTHORN["fee_schedule"]}
    summary = _verified_summary(only, HAWTHORN_EVIDENCE)
    assert "did not state the species, fee" not in summary
    assert "$45" in summary and "$10" in summary


# --------------------------------------------------------------------------- #
# 4. Nothing that does not carry the fields may change.
# --------------------------------------------------------------------------- #

def test_a_flat_fee_page_is_unchanged():
    summary = _verified_summary(FLAT_FEE)
    assert summary == ("Dogs and cats are accepted. A $100 fee applies per stay. "
                       "Maximum pet weight is 75 pounds, with up to 2 pets "
                       "permitted per room.")
    assert _chips(FLAT_FEE)["Pet charge"] == "$100.00"
    assert _rows(FLAT_FEE)["Pet charge"] == "$100.00"


def test_a_flat_fee_with_a_scalar_cap_still_states_it_inline():
    f = dict(FLAT_FEE, fee_cap={"amount": "150.00", "currency": "USD"})
    assert "up to a maximum of $150." in _verified_summary(f)
    assert _rows(f)["Maximum total"] == "$150"
    assert _chips(f)["Pet charge"] == "$100.00 (max $150)"


def test_a_fee_tiers_page_is_unchanged():
    summary = _verified_summary(TIERED)
    assert ("A pet fee of $75 applies for stays of 1–4 nights, and $125 applies "
            "for stays of 5 nights or more.") in summary
    assert _chips(TIERED)["Charge basis"] == "Tiered by stay length"
    rows = _rows(TIERED)
    assert rows["Pet charge, 1–4 nights"] == "$75"
    assert rows["Pet charge, 5 nights or more"] == "$125"


def test_no_published_hotel_carries_either_new_field():
    """The 38 published pages cannot change, because none carries the fields."""
    hotels = json.loads(PACKAGE_FACTS.read_text(encoding="utf-8"))["hotels"]
    assert len(hotels) == 38
    blob = json.dumps(hotels)
    assert "fee_schedule" not in blob and "fee_cap_tiers" not in blob
    for h in hotels:
        f = h.get("pet_facts") or h
        assert staged_fee(f) == ("", "") and cap_tiers(f) == ()


# --------------------------------------------------------------------------- #
# 5. No page states the same money twice.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("facts, evidence", [
    (HAWTHORN, HAWTHORN_EVIDENCE), (CANDLEWOOD, CANDLEWOOD_EVIDENCE),
    (FLAT_FEE, ""), (TIERED, ""),
])
def test_no_amount_is_stated_twice_in_one_summary(facts, evidence):
    summary = _verified_summary(facts, evidence)
    for amount in ("$45", "$10", "$25", "$75", "$150", "$100", "$125", "$180"):
        assert summary.count(amount + " ") + summary.count(amount + ".") <= 1, \
            "%s repeated in %r" % (amount, summary)


def test_a_scalar_cap_never_appears_beside_a_tiered_one():
    both = dict(CANDLEWOOD, fee_cap={"amount": "999.00", "currency": "USD"})
    summary = _verified_summary(both, CANDLEWOOD_EVIDENCE)
    assert "$999" not in summary
    assert summary.count("A maximum of") == 1
    assert "Maximum total" not in _rows(both)


def test_a_staged_schedule_suppresses_any_stray_scalar_fee():
    """Extraction never emits both. If one ever arrived, the page shows one."""
    both = dict(HAWTHORN, pet_fee="$45.00", fee_basis="per night")
    summary = _verified_summary(both, HAWTHORN_EVIDENCE)
    assert "A $45 non-refundable fee applies per night." not in summary
    assert "for the first night and $10 for each additional night." in summary


# --------------------------------------------------------------------------- #
# 6. Page structure survives, on both layouts.
# --------------------------------------------------------------------------- #

def _vm(facts, evidence):
    rows, _plain, note = _verified_details(facts)
    return HotelProfileVM(
        state="VERIFIED_PET_FRIENDLY", name="Test Property",
        corridor="Columbus corridor · Columbus, OH", initials="TP",
        address="1 Test St", phone="614-555-0100",
        official_url="https://example.test/", verified_at="2026-08-04",
        source_name="Official site", summary=_verified_summary(facts, evidence),
        facts=_verified_facts(facts), verif_badge_text="Verified",
        verif_badge_cls="ok", verif_chip="Verified", trust_cls="ok",
        trust_line="Official source", evidence_quote=evidence,
        details_rows=rows, details_note=note)


@pytest.mark.parametrize("facts, evidence", [
    (HAWTHORN, HAWTHORN_EVIDENCE), (CANDLEWOOD, CANDLEWOOD_EVIDENCE)])
def test_desktop_and_mobile_structure_remains_valid(facts, evidence):
    html = render_hotel_profile(_vm(facts, evidence))
    assert html.count("<h1") == 1
    for landmark in ("<header", "<main", "<nav", "<footer"):
        assert landmark in html
    # The six-fact snapshot is the desktop chip grid; the mobile bar is the
    # small-screen surface. Both must survive the new rows.
    assert html.count('class="fh-cell"') == 6
    assert 'class="fh-mobilebar"' in html
    assert 'name="viewport"' in html


@pytest.mark.parametrize("facts, evidence", [
    (HAWTHORN, HAWTHORN_EVIDENCE), (CANDLEWOOD, CANDLEWOOD_EVIDENCE)])
def test_rendered_page_is_escaped_and_states_the_new_dimensions(facts, evidence):
    html = render_hotel_profile(_vm(facts, evidence))
    assert "<script>alert" not in html
    assert "Maximum total" in html
    assert ("Pet charge, first night" in html) == bool(staged_fee(facts)[0])


# --------------------------------------------------------------------------- #
# 7. Preview and production package are untouched by rendering.
# --------------------------------------------------------------------------- #

def test_preview_still_carries_noindex_and_production_does_not():
    """Rendering must not have disturbed the preview/production header split."""
    from scripts.pettripfinder.assemble_netlify_bundle import (
        HEADERS_PREVIEW_PATH, HEADERS_PRODUCTION_PATH, parse_headers_file,
    )
    prev = parse_headers_file(HEADERS_PREVIEW_PATH.read_text(encoding="utf-8"))["/*"]
    prod = parse_headers_file(HEADERS_PRODUCTION_PATH.read_text(encoding="utf-8"))["/*"]
    assert "noindex" in prev.get("X-Robots-Tag", "").lower()
    assert "X-Robots-Tag" not in prod


def test_the_production_package_has_no_pending_change():
    import scripts.pettripfinder.export_hotel_policy_facts as EX
    try:
        report = EX.build_preview()["report"]
    except (FileNotFoundError, KeyError):
        pytest.skip("operational promotion corpus absent (gitignored)")
    assert report["additions_count"] == 0
    assert report["removals_count"] == 0
    assert report["unintended_updates_count"] == 0
    assert report["before_package_sha256"] == report["after_package_sha256"]
    assert report["new_count"] == report["old_count"] == 38
