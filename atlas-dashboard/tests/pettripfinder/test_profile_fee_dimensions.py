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


# PTF-PROMOTION-002: these two dimensions are now genuinely published. The
# guard therefore stops asserting that nobody carries them -- which is no
# longer true and would have to be deleted to pass -- and instead pins WHICH
# records carry them and proves each renders completely. Both fields fail
# closed by design: half a staged schedule, or a ceiling missing its window,
# renders nothing at all, so "carries the field" and "renders it" must agree.
STAGED_FEE_IDENTITIES = ["hawthorn extended stay by wyndham columbus west"]
CAP_TIER_IDENTITIES = ["candlewood suites columbus north polaris by ihg"]


def test_only_the_reviewed_hotels_carry_the_new_fee_dimensions():
    hotels = json.loads(PACKAGE_FACTS.read_text(encoding="utf-8"))["hotels"]
    assert len(hotels) == 73
    staged = sorted(h["key"] for h in hotels
                    if (h.get("facts") or {}).get("fee_schedule"))
    capped = sorted(h["key"] for h in hotels
                    if (h.get("facts") or {}).get("fee_cap_tiers"))
    assert staged == STAGED_FEE_IDENTITIES
    assert capped == CAP_TIER_IDENTITIES
    for h in hotels:
        f = h.get("facts") or {}
        key = h["key"]
        # A record renders a dimension exactly when it carries it.
        assert (staged_fee(f) != ("", "")) is (key in STAGED_FEE_IDENTITIES), key
        assert (cap_tiers(f) != ()) is (key in CAP_TIER_IDENTITIES), key
    # Both stages of a staged schedule are present, never half of one.
    for h in hotels:
        if h["key"] in STAGED_FEE_IDENTITIES:
            first, additional = staged_fee(h["facts"])
            assert first and additional, h["key"]


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


def test_the_export_corpus_cannot_regress_the_production_package():
    """The export corpus no longer reconstructs the committed authority, and
    that is expected: records promoted through machine review are absent from
    it. The contract is therefore no longer "these must be equal" -- which
    would be satisfied only by deleting 32 published hotels -- but "the export
    path must refuse to make them equal by destroying the authority".

    The equality expectation this replaces would have passed happily the moment
    someone ran the exporter and lost the promoted records.
    """
    import scripts.pettripfinder.export_hotel_policy_facts as EX
    try:
        report = EX.build_preview()["report"]
    except (FileNotFoundError, KeyError):
        pytest.skip("operational promotion corpus absent (gitignored)")
    # Preview stays read-only and honest about the divergence.
    assert report["additions_count"] == 0
    assert report["old_count"] == 73
    before = EX.PUBLISHED_FACTS_PATH.read_bytes()
    delta = EX.authority_delta(before.decode("utf-8"), EX.serialize(EX.build_package()))
    if not EX.is_destructive(delta):
        # A corpus that legitimately reproduces the authority must still write.
        assert delta["identical"]
        return
    with pytest.raises(EX.AuthorityRegressionError):
        EX.write_package()
    assert EX.PUBLISHED_FACTS_PATH.read_bytes() == before


# --------------------------------------------------------------------------- #
# 8. PTF-REVIEW-B1 -- corrections raised during Columbus Batch 1 human review.
# --------------------------------------------------------------------------- #

from scripts.pettripfinder.promote_attested_candidates import (   # noqa: E402
    extract_pet_facts as _extract,
)

LA_QUINTA = ("Service Animals - ADA-defined service animals are welcome free of "
             "charge. / Pets Allowed - 2 pets max. Cats and dogs only. 75lbs or "
             "less per pet. / Fees - Non-refundable 25 USD nightly for up to 2 "
             "pets. Max 75 USD per stay.")
RENAISSANCE = ("Pet Policy Pets Welcome Pet fee of $50 per night. Maximum of "
               "$150 per stay for two (2) pets. Maximum Pet Weight: 50.0lbs "
               "Maximum Number of Pets in Room: 2")
REYNOLDSBURG = ("Can I bring my pet to Holiday Inn Express? Pets are welcome. "
                "Pet policy description. We gladly accept pet with a pet fee. "
                "Fee is per night. No more than one animal per room. Pet fee "
                "per night: 30 USD Pet weight limit: No weight limit per pet 1 "
                "pets allowed Pets allowed: Only dogs and cats allowed")


def test_a_stated_cap_basis_is_kept_in_the_structured_fact():
    """"Max 75 USD per stay" -- the basis must survive into the fact, not only
    into the sentence a renderer happens to build."""
    facts, _e, _b = _extract(LA_QUINTA)
    assert facts["fee_cap"]["basis"] == "per stay"


def test_a_cap_basis_is_never_inferred_when_the_source_omits_one():
    block = ("Pets Welcome Non-Refundable Pet Fee Per Stay: $100.00 up to a "
             "maximum of $300. Maximum Pet Weight: 75.0lbs")
    facts, _e, _b = _extract(block)
    assert "basis" not in (facts.get("fee_cap") or {})


def test_a_qualified_ceiling_keeps_its_qualifier_verbatim():
    """"for two (2) pets" bounds what TWO animals cost. It is not a per-pet
    charge, and the source says nothing about one animal."""
    facts, _e, _b = _extract(RENAISSANCE)
    cap = facts["fee_cap"]
    assert cap["amount"] == "150.00"
    assert cap["basis"] == "per stay"
    assert cap["applies_to"] == "for two (2) pets"
    assert facts["pet_fee"] == "$50.00" and facts["fee_basis"] == "per night"


def test_a_qualified_ceiling_is_attributed_and_never_read_as_a_per_pet_charge():
    facts, evidence, _b = _extract(RENAISSANCE)
    summary = _verified_summary(facts, " ".join(e["quote"] for e in evidence))
    assert "The hotel states a maximum of $150 per stay for two pets." in summary
    assert "per pet" not in summary
    # The cap must not be folded into the rate's own clause.
    assert "A $50 fee applies per night." in summary


def test_an_explicit_no_weight_limit_is_stated_not_shown_as_unknown():
    """"No weight limit per pet" is a FACT the hotel gave, not a gap."""
    facts, evidence, _b = _extract(REYNOLDSBURG)
    assert facts["weight_limit_stated_none"] == "true"
    assert "weight_limit" not in facts
    summary = _verified_summary(facts, " ".join(e["quote"] for e in evidence))
    assert "no pet weight limit stated by the hotel" in summary
    assert "Not stated" not in summary


def test_a_single_pet_allowance_reads_in_the_singular():
    facts, evidence, _b = _extract(REYNOLDSBURG)
    summary = _verified_summary(facts, " ".join(e["quote"] for e in evidence))
    assert "One pet is permitted per room" in summary
    assert "1 pets" not in summary


def test_a_multi_pet_allowance_still_reads_in_the_plural():
    facts, evidence, _b = _extract(LA_QUINTA)
    summary = _verified_summary(facts, " ".join(e["quote"] for e in evidence))
    assert "up to 2 pets permitted per room" in summary
    assert "2 pet " not in summary


# --------------------------------------------------------------------------- #
# 9. PTF-REVIEW-B2 -- corrections raised during Columbus Batch 2 human review.
# --------------------------------------------------------------------------- #

from scripts.pettripfinder.fee_forms import (                    # noqa: E402
    basis_for_amount, pet_deposit, recurrence_conflict,
)

DAYS_INN = ("Service Animals - ADA-defined service animals welcome./Pets "
            "Allowed.2 pets max.20lbs or less per pet./Fees - 50USD per stay. "
            "Pet Sanitation Fee 50USD if required./Other Information - Pet "
            "deposit is 150 USD.")
HIE_DUBLIN = ("Pets are welcome. Pet policy description. There is a limit of 2 "
              "dogs per room, 75lb weight limit. We do not accept cats at our "
              "property. There is a 75 USD, one time pet fee. Pet Fee is Non "
              "Refundable. Pet fee per night: 75 USD")
HILTON_POLARIS = ("Pets Smoking WiFi Pets allowed Yes Deposit Yes. $80.00 "
                  "Non-refundable Fee Max weight 50 lbs Other pet information "
                  "Max 2 cat(s) or 2 dog(s), Fee $80 for first pet and $50 for "
                  "second pet per stay.")
HGI_EASTON = ("Pets Smoking WiFi Pets allowed Yes Deposit Yes. $75.00 "
              "Non-refundable Fee Max weight 75 lbs Other pet information $75 "
              "per stay / dogs and cats only / max 2 pets per room")


# A. An explicitly pet-named deposit is its own obligation.

def test_an_explicit_pet_deposit_is_captured_separately():
    facts, _e, _b = _extract(DAYS_INN)
    assert facts["pet_deposit"]["amount"] == "150.00"
    assert facts["pet_fee"] == "$50.00" and facts["fee_basis"] == "per stay"


def test_a_conditional_sanitation_fee_is_never_merged_into_the_pet_fee():
    """"$50 if required" is contingent. It is not the price of bringing a pet."""
    facts, _e, _b = _extract(DAYS_INN)
    assert facts["pet_fee"] == "$50.00"
    assert "sanitation" not in json.dumps(facts).lower()


def test_an_incidentals_deposit_is_still_not_a_pet_deposit():
    assert pet_deposit("A refundable deposit of up to 50.00 USD is required at "
                       "check-in for incidentals.") is None


def test_the_pet_deposit_renders_as_a_separate_refundable_sentence():
    facts, evidence, _b = _extract(DAYS_INN)
    summary = _verified_summary(facts, " ".join(e["quote"] for e in evidence))
    assert "A separate refundable pet deposit of $150 is also stated." in summary
    assert "A $50 fee applies per stay." in summary


# B. One-time versus per-night is a contradiction even at the same amount.

def test_equal_amounts_with_conflicting_recurrence_are_a_contradiction():
    """$75 once or $75 a night: five nights is $75 or $375. The amounts
    agreeing does not make the terms agree."""
    clash = recurrence_conflict(HIE_DUBLIN)
    assert clash is not None
    assert clash.detail == "one_time_fee_conflicts_with_nightly_fee"
    assert clash.ladder_quote == "There is a 75 USD, one time pet fee"
    assert clash.rate_quote == "Pet fee per night: 75 USD"


def test_the_recurrence_contradiction_withholds_the_fee_and_the_basis():
    facts, evidence, _b = _extract(HIE_DUBLIN)
    assert "pet_fee" not in facts and "fee_basis" not in facts
    assert facts["fee_conflict"]["quotes"] == [
        "There is a 75 USD, one time pet fee", "Pet fee per night: 75 USD"]
    assert len([e for e in evidence if e["field"] == "fee_conflict"]) == 2
    assert facts["pets_allowed"] == "true"


def test_a_trailing_weight_limit_phrase_is_read():
    """"75lb weight limit" states a ceiling as plainly as "75lbs or less"."""
    facts, _e, _b = _extract(HIE_DUBLIN)
    assert facts["weight_limit"] == "75.0 pounds"


def test_a_cap_is_not_a_recurrence_contradiction():
    assert recurrence_conflict("Pets welcome. $25 per night, max $75 per stay.") is None


# C. The per-animal ladder must reach the reader.

def test_the_per_animal_ladder_is_rendered_for_the_customer():
    facts, evidence, _b = _extract(HILTON_POLARIS)
    summary = _verified_summary(facts, " ".join(e["quote"] for e in evidence))
    assert ("The first pet costs $80 per stay, and a second pet costs an "
            "additional $50 per stay.") in summary
    assert "$160" not in summary            # never multiplied
    assert "per pet" not in summary          # never flattened


def test_a_property_with_a_fee_never_renders_as_free():
    facts, evidence, _b = _extract(HILTON_POLARIS)
    summary = _verified_summary(facts, " ".join(e["quote"] for e in evidence))
    assert "$" in summary, "a paying property must not read as free"


# D. A basis stated beside the same amount is recovered.

def test_a_basis_stated_beside_the_same_amount_is_recovered():
    facts, _e, _b = _extract(HGI_EASTON)
    assert facts["pet_fee"] == "$75.00" and facts["fee_basis"] == "per stay"


def test_basis_recovery_requires_an_exact_amount_match():
    """A different charge's recurrence must not attach to this fee."""
    assert basis_for_amount("Pet fee $75. Parking is $32 per night.", "75.00") == ("", "")


def test_basis_recovery_ignores_a_conditional_charge():
    assert basis_for_amount("Pet fee $50. Sanitation fee $50 per night if "
                            "required.", "50.00") == ("", "")


# --------------------------------------------------------------------------- #
# 10. PTF-REVIEW-B3 -- corrections raised during Columbus Batch 3 human review.
# --------------------------------------------------------------------------- #

from scripts.pettripfinder.prose_facts import (                  # noqa: E402
    extract_pet_count, extract_species,
)

TOWNEPLACE_OSU = ("Pet Policy Pets Welcome Birds/fish/2 well-mannered dogs or "
                  "cats per room with USD 100 non-refundable fee "
                  "Non-Refundable Pet Fee Per Stay: $100.00 Maximum Number of "
                  "Pets in Room: 2")
GROVE_CITY = ("Pets Smoking WiFi Pets allowed Yes Deposit Yes. $75.00 "
              "Non-refundable Fee Max weight 100 lbs Max size Medium Other pet "
              "information 1-4 nights $75.00 per stay or 5+ nights $100 per stay")
SCIOTO = ("Pets Smoking WiFi Pets allowed Yes Deposit Yes. $50.00 "
          "Non-refundable Fee Max weight 75 lbs Max size Large Other pet "
          "information $50 2petsMax,dog/cat only")


# A. Unspaced pet-count notation.

@pytest.mark.parametrize("text", [
    "$50 2petsMax,dog/cat only", "$75(1-4n)$125(5+n)2pet Max dog/cat only",
    "$75(1-4n),$125(5+n) 2petsMax,dog/cat", "2pets max", "2petsmaximum",
])
def test_compact_pet_count_notation_is_read(text):
    got = extract_pet_count(text)
    assert got is not None and got.value == "2"


def test_a_compact_count_reaches_the_facts():
    facts, _e, _b = _extract(SCIOTO)
    assert facts["pet_count_limit"] == "2"


@pytest.mark.parametrize("text", [
    "room 2 pets welcome",          # no explicit max word
    "Max weight 75 lbs",            # a weight, not a count
    "$50 fee 2 max",                # no pet noun
])
def test_a_compact_count_needs_integer_noun_and_max(text):
    assert extract_pet_count(text) is None


# B. A tier basis the source states must reach the reader.

def test_a_stated_tier_basis_is_rendered():
    facts, evidence, _b = _extract(GROVE_CITY)
    assert all(t["basis_stated"] for t in facts["fee_tiers"])
    assert all(t["stated_basis"] == "per stay" for t in facts["fee_tiers"])
    summary = _verified_summary(facts, " ".join(e["quote"] for e in evidence))
    assert ("A pet fee of $75 per stay applies for stays of 1–4 nights, and "
            "$100 per stay applies for stays of 5 nights or more.") in summary


def test_a_tier_basis_is_never_invented_when_unstated():
    block = ("Pets allowed Yes Deposit Yes. $125.00 Non-refundable Fee Max "
             "weight 50 lbs Other pet information 1-4 night stay $75; 5+ night "
             "stay $125; 2 pets max; dog or cat only")
    facts, evidence, _b = _extract(block)
    assert not any(t.get("stated_basis") for t in facts["fee_tiers"])
    summary = _verified_summary(facts, " ".join(e["quote"] for e in evidence))
    assert "per stay" not in summary and "per night" not in summary


# C. Every permitted species reaches the reader.

def test_all_explicitly_permitted_species_are_preserved():
    got = extract_species(TOWNEPLACE_OSU)
    assert got.value == "birds, fish, dogs, cats"
    facts, evidence, _b = _extract(TOWNEPLACE_OSU)
    summary = _verified_summary(facts, " ".join(e["quote"] for e in evidence))
    assert summary.startswith("Birds, fish, dogs, and cats are accepted.")


def test_well_mannered_is_not_read_as_a_breed_restriction():
    facts, _e, _b = _extract(TOWNEPLACE_OSU)
    assert "breed_restrictions" not in facts


@pytest.mark.parametrize("text, expected", [
    ("dog/cat only", "dogs, cats"), ("Only dogs and cats allowed", "dogs, cats"),
    ("dogs only", "dogs"), ("cats only", "cats"),
])
def test_ordinary_species_readings_are_unchanged(text, expected):
    assert extract_species(text).value == expected


# --------------------------------------------------------------------------- #
# 11. PTF-REVIEW-B3 -- a fee the source scopes to the room.
# --------------------------------------------------------------------------- #

from scripts.pettripfinder.fee_forms import room_scope_for_amount   # noqa: E402


def test_a_room_scoped_fee_says_so_to_the_reader():
    facts, evidence, _b = _extract(TOWNEPLACE_OSU)
    assert facts["fee_scope"] == "per_room"
    summary = _verified_summary(facts, " ".join(e["quote"] for e in evidence))
    assert summary == (
        "Birds, fish, dogs, and cats are accepted. A $100 non-refundable fee "
        "applies per stay for the room. Up to 2 pets are permitted per room.")


def test_a_count_qualifier_is_not_read_as_a_fee_scope():
    """"max 2 pets per room" says how many animals, not how the fee is charged.

    This is the dominant use of "per room" in the corpus. Reading it as a fee
    scope would attribute to the hotel a statement it did not make -- and would
    have silently rewritten two already-approved records.
    """
    for block in ("Pets allowed Yes Deposit Yes. $75.00 Non-refundable Fee "
                  "Other pet information dogs and cats only / max 2 pets per room",
                  "Pets Welcome 2 pets per room Non-Refundable Pet Fee: $50.00"):
        facts, _e, _b = _extract(block)
        assert "fee_scope" not in facts


def test_competing_pet_and_room_scopes_are_left_unresolved():
    """A source stating both scopes gets neither invented for it."""
    block = ("Pet Policy Pets Welcome 2 pets 75lbs max per pet per room with "
             "Non Refundable fee Non-Refundable Pet Fee Per Stay: $100.00")
    facts, _e, _b = _extract(block)
    assert "fee_scope" not in facts


@pytest.mark.parametrize("block, amount", [
    ("A $150 cleaning fee per room applies", "150"),
    ("Pets allowed Yes $100 fee. A $250 damage deposit per room", "250"),
    ("Deposit Yes. $50.00 Non-refundable Fee Max weight 75 lbs 2 pets max", "50.00"),
])
def test_no_room_scope_is_read_from_another_charge(block, amount):
    assert room_scope_for_amount(block, amount) == ("", "")


def test_a_fee_stated_to_cover_a_number_of_pets_is_room_scoped():
    assert room_scope_for_amount(
        "Pets welcome. A $120 fee applies for up to 2 pets.", "120")[0] == "per_room"


def test_an_unscoped_fee_stays_unscoped():
    facts, evidence, _b = _extract(SCIOTO)
    assert "fee_scope" not in facts
    summary = _verified_summary(facts, " ".join(e["quote"] for e in evidence))
    assert "for the room" not in summary


def test_the_room_scoped_verb_does_not_leak_into_other_profiles():
    """The verb belongs to the room-scoped sentence, not to every count.

    Adding it globally rewrote a line on eight already-published pages for no
    reason a reader would benefit from. The generated site must stay
    byte-identical, so the established phrasing stands everywhere else.
    """
    block = ("Pets allowed Yes Deposit Yes. $50.00 Non-refundable Fee "
             "Other pet information 2 pets max; dog or cat only")
    facts, evidence, _b = _extract(block)
    assert "fee_scope" not in facts
    summary = _verified_summary(facts, " ".join(e["quote"] for e in evidence))
    assert summary.endswith("Up to 2 pets permitted per room.")


def test_the_room_scoped_path_carries_its_verb():
    facts, evidence, _b = _extract(TOWNEPLACE_OSU)
    summary = _verified_summary(facts, " ".join(e["quote"] for e in evidence))
    assert summary.endswith("Up to 2 pets are permitted per room.")


# --------------------------------------------------------------------------- #
# 12. PTF-REVIEW-FINAL -- fee-scope conflict and species-bound weight.
# --------------------------------------------------------------------------- #

from scripts.pettripfinder.fee_forms import scope_conflict           # noqa: E402
from scripts.pettripfinder.prose_facts import species_bound_weight   # noqa: E402

SHERATON = ("Pet Policy Pets Welcome Small pets under 50 lbs are welcome. $75 "
            "nonrefundable fees charged per pet. Non-Refundable Pet Fee Per "
            "Stay: $75.00 Maximum Pet Weight: 50.0lbs Maximum Number of Pets "
            "in Room: 2")
TOWNEPLACE_DUBLIN = ("Pet Policy Pets Welcome Dogs and 20-lb. cats. $150 "
                     "non-refundable fee. Maximum Pet Weight: 20.0lbs "
                     "Maximum Number of Pets in Room: 2")


# A. The same money charged per pet and per stay is a conflict, not a price.

def test_a_fee_scoped_both_per_pet_and_per_stay_is_withheld():
    facts, _e, _b = _extract(SHERATON)
    assert facts["fee_conflict"]["detail"] == [
        "conflicting_fee_basis_per_pet_vs_fee_basis_per_stay"]
    assert facts["fee_conflict"]["quotes"] == [
        "$75 nonrefundable fees charged per pet",
        "Non-Refundable Pet Fee Per Stay: $75.00"]
    assert "pet_fee" not in facts and "fee_basis" not in facts


def test_neither_side_of_a_scope_conflict_is_rendered_as_authoritative():
    facts, evidence, _b = _extract(SHERATON)
    summary = _verified_summary(facts, " ".join(e["quote"] for e in evidence))
    assert "$75" not in summary
    assert "conflicting pet-fee terms" in summary
    # Facts the conflict does not touch still reach the reader.
    assert "Maximum pet weight is 50 pounds" in summary


@pytest.mark.parametrize("block", [
    # A weight per pet beside a per-stay cap states two different things.
    "Dogs Allowed - 2 dogs max. 75lbs or less per pet. Fees - Max 75 USD per stay.",
    # A per-pet rate under a per-stay ceiling is a structure, not a conflict.
    "Fees - 25 USD per pet per night. Max 75 USD per stay.",
    # Different amounts are not the same fee stated twice.
    "$50 charged per pet. Non-Refundable Pet Fee Per Stay: $75.00",
])
def test_no_scope_conflict_is_invented(block):
    assert scope_conflict(block) is None


# B. A weight the source binds to one species stays bound to it.

def test_a_species_bound_weight_is_not_flattened():
    facts, _e, _b = _extract(TOWNEPLACE_DUBLIN)
    assert facts["species_weight_limits"] == {
        "cats": {"value": "20 pounds",
                 "evidence_quote": facts["species_weight_limits"]["cats"]["evidence_quote"]}}
    assert "weight_limit" not in facts
    assert facts["species_allowed"] == "dogs, cats"
    assert facts["pet_fee"] == "$150.00" and "fee_basis" not in facts
    assert facts["pet_count_limit"] == "2"


def test_the_summary_never_implies_dogs_share_the_cat_limit():
    facts, evidence, _b = _extract(TOWNEPLACE_DUBLIN)
    summary = _verified_summary(facts, " ".join(e["quote"] for e in evidence))
    # PTF-POLICY-PRECISION-001 changed the fee clause for records that state an
    # amount but no basis: "a $150 fee applies" read as a complete answer to a
    # question this source never answered. The point of THIS test -- that the
    # cat-only weight limit is never extended to dogs -- is unchanged.
    assert summary == ("Dogs and cats are accepted. A $150 non-refundable pet fee is "
                       "stated; the fee basis is not specified. Cats must weigh 20 "
                       "pounds or less, with up to 2 pets permitted per room.")
    assert "Maximum pet weight" not in summary


def test_a_single_species_page_keeps_its_flat_weight():
    """On a dogs-only page the bound and flat readings describe one rule.

    Splitting it would churn established records to say the same thing.
    """
    assert species_bound_weight("2 dogs max. dogs under 50lbs.") is None
    facts, _e, _b = _extract("Pets Allowed - 2 dogs max. dogs under 50lbs. "
                             "Fees - 150USD per stay.")
    assert facts["weight_limit"] == "50.0 pounds"
    assert "species_weight_limits" not in facts


def test_an_adjective_governing_both_species_is_not_bound_to_one():
    """"dogs and cats under 25 lbs" limits both; only attributive forms bind."""
    assert species_bound_weight("dogs and cats under 25 lbs are welcome") is None
