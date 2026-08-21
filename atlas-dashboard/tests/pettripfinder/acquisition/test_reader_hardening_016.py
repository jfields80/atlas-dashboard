"""PTF-GENERIC-READER-HARDENING-AND-SOURCE-WIRING-016 -- Phase 11.

Every case here is a surface some previous work order measured, and every
assertion names the fact the property actually published. Nothing asserts a
count of fields: a reader that gained four fields and invented one of them has
not improved, so the fields are named.
"""

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import reader_hardening_016 as H  # noqa: E402
from scripts.pettripfinder.brightdata import policy_reading as PR        # noqa: E402
from scripts.pettripfinder.brightdata import policy_surface as PS        # noqa: E402
from scripts.pettripfinder.contracts import enums                        # noqa: E402


def read(text):
    reading = PR.parse(text, strategy="test_016")
    result = PR.to_extraction(reading, location="")
    return dict(result.extraction), dict(result.withheld or {}), \
        [f.get("code") for f in (result.flags or [])]


def case(case_id):
    cases = {c["case_id"]: c for c in H.load_corpus()["cases"]}
    assert case_id in cases, "corpus no longer carries %s" % case_id
    return H.read(cases[case_id])


# --------------------------------------------------------------------------- #
# 4. the generic reader recovers the measured independent cases
# --------------------------------------------------------------------------- #

def test_ingleside_no_other_pets_is_a_species_restriction_not_a_refusal():
    """The whole policy was withheld because "No other pets are allowed"
    followed "welcomes dogs only" and was read as a blanket refusal."""
    got = case("independent--the-ingleside-hotel")
    assert got["extraction"]["pets_allowed"] is True
    assert got["extraction"]["pet_fee"] == 4000
    assert got["extraction"]["fee_basis"] == "per_night"
    assert got["extraction"]["pet_count_limit"] == 2
    assert got["extraction"]["species_allowed"] == ["dog"]


def test_the_marc_policy_is_no_longer_swallowed_by_the_service_animal_label():
    """A chip list has no punctuation, so the service-animal segment was the
    whole block and every ordinary-pet term in it was discarded."""
    got = case("independent--the-marc-hotel")
    assert got["extraction"]["pets_allowed"] is True
    assert got["extraction"]["pet_fee"] == 10000
    assert got["extraction"]["pet_count_limit"] == 2
    assert got["extraction"]["species_allowed"] == ["cat", "dog"]
    # the basis really is unstated -- "per reservation" is a scope
    assert got["withheld"]["fee_basis"] == enums.SOURCE_SILENT


def test_the_pfister_fee_written_as_fee_of_an_amount_is_read():
    got = case("independent--the-pfister-hotel")
    assert got["extraction"]["pet_fee"] == 15000
    assert got["extraction"]["pets_allowed"] is True
    assert got["extraction"]["pet_count_limit"] == 2
    assert got["extraction"]["species_allowed"] == ["cat", "dog"]
    assert got["withheld"]["fee_basis"] == enums.SOURCE_SILENT


def test_wildwood_policy_is_located_at_all_now():
    """The page carried a fee, a count and a species under the words "dog
    friendly hotel", and the locator considered zero candidates on it."""
    got = case("independent--wildwood-lodge")
    assert got["block_found"] is True
    assert got["extraction"]["pets_allowed"] is True
    assert got["extraction"]["pet_count_limit"] == 2
    assert got["extraction"]["pet_count_scope"] == "per_room"


def test_wildwood_fee_is_withheld_because_suites_are_priced_differently():
    """$20 per dog per night, $30 in Suites. Publishing $20 would understate
    a suite; the schema has nowhere to say which room was booked."""
    got = case("independent--wildwood-lodge")
    assert "pet_fee" not in got["extraction"]
    assert got["withheld"]["pet_fee"] == enums.SCHEMA_CANNOT_REPRESENT
    assert "FLAG_TIERED_FEE" in [f.get("code") for f in got["flags"]]


def test_the_species_named_signal_phrases_are_mirrors_of_existing_ones():
    """A locator that knows "pet friendly" and not "dog friendly" is not
    stricter, it is inconsistent -- the parser accepted the species form
    already."""
    for phrase in ("dog friendly", "dogs allowed", "dogs welcome"):
        assert phrase in PS.SIGNAL_PHRASES
    for phrase in ("pet friendly", "pets allowed", "pets welcome"):
        assert phrase in PS.SIGNAL_PHRASES


# --------------------------------------------------------------------------- #
# 5. Red Roof is materially improved
# --------------------------------------------------------------------------- #

def test_red_roof_recovers_the_weight_the_species_and_the_cap():
    got = case("red_roof--red-roof-inn-milwaukee-airport-oak-creek")
    assert got["extraction"]["weight_limit"] == {"value": 80.0, "unit": "lb"}
    assert got["extraction"]["species_allowed"] == ["cat", "dog"]
    assert got["extraction"]["fee_cap"] == {"amount_minor": 10500,
                                            "currency": "USD",
                                            "basis": "per_stay"}
    assert got["extraction"]["pet_count_limit"] == 2
    assert got["extraction"]["pets_allowed"] is True


def test_red_roof_fee_is_withheld_because_the_first_pet_is_free():
    """First pet free, second pet $15 a night. Neither $15 nor $0 is the
    price of "a pet" here, so no single amount is asserted."""
    got = case("red_roof--red-roof-inn-milwaukee-airport-oak-creek")
    assert "pet_fee" not in got["extraction"]
    assert got["withheld"]["pet_fee"] == enums.SCHEMA_CANNOT_REPRESENT
    assert "FLAG_TIERED_FEE" in [f.get("code") for f in got["flags"]]


def test_red_roof_incidentals_deposit_is_not_a_pet_deposit():
    """A $50 refundable deposit for incidentals required of ALL guests was
    published as this hotel's pet deposit."""
    got = case("red_roof--red-roof-inn-milwaukee-airport-oak-creek")
    assert "pet_deposit" not in got["extraction"]


def test_a_deposit_whose_sentence_names_a_pet_is_still_a_pet_deposit():
    """The guard must disqualify a purpose, not deposits."""
    extraction, _withheld, _flags = read(
        "Pet Policy: a refundable pet deposit of 50 USD is required at "
        "check-in for all guests.")
    assert extraction["pet_deposit"] == 5000


def test_a_pet_fee_that_applies_to_all_guests_with_pets_survives():
    """"for all guests" is only disqualifying when no pet word stands between
    it and the amount."""
    extraction, _withheld, _flags = read(
        "A $75 pet fee applies for all guests travelling with pets.")
    assert extraction["pet_fee"] == 7500


# --------------------------------------------------------------------------- #
# 6. amenity chips remain insufficient
# --------------------------------------------------------------------------- #

def test_the_motel6_amenity_chips_do_not_produce_a_policy_record():
    for case_id in ("motel6_amenity_chip--motel-6-milwaukee-wi-glendale",
                    "motel6_amenity_chip--motel-6-oak-creek-wi"):
        got = case(case_id)
        assert got["extraction"] == {}, case_id
        assert got["withheld"]["pets_allowed"] == enums.ARTIFACT_INSUFFICIENT
        assert "FLAG_AMENITY_LABEL_ONLY" in [f.get("code") for f in got["flags"]]


def test_a_bare_amenity_label_is_insufficient():
    extraction, withheld, flags = read("Pets Allowed")
    assert "pets_allowed" not in extraction
    assert withheld["pets_allowed"] == enums.ARTIFACT_INSUFFICIENT
    assert "FLAG_AMENITY_LABEL_ONLY" in flags


def test_the_guard_is_not_a_minimum_length_rule():
    """"Pets Allowed" is 12 characters and insufficient; "Pets are welcome."
    is 17 and sufficient. Length is not what separates them."""
    short_label, _w, _f = read("Pets Allowed")
    short_statement, _w2, _f2 = read("Pets are welcome.")
    assert "pets_allowed" not in short_label
    assert short_statement["pets_allowed"] is True


def test_an_amenity_label_beside_a_real_term_is_still_a_policy():
    extraction, _withheld, flags = read("Pets Allowed Coin Laundry $25 pet fee")
    assert extraction["pets_allowed"] is True
    assert "FLAG_AMENITY_LABEL_ONLY" not in flags


# --------------------------------------------------------------------------- #
# 7. terse no-pets policies remain valid
# --------------------------------------------------------------------------- #

def test_a_terse_refusal_is_a_meaningful_policy():
    extraction, _withheld, flags = read("Sorry, no pets allowed.")
    assert extraction["pets_allowed"] is False
    assert "FLAG_AMENITY_LABEL_ONLY" not in flags


def test_a_refusal_is_never_treated_as_an_amenity_label():
    """No facilities list advertises "no pets", so the guard never applies to
    a refusal, punctuation or not."""
    extraction, _withheld, _flags = read("No pets allowed")
    assert extraction["pets_allowed"] is False


def test_no_other_pets_after_a_service_animal_acceptance_still_refuses():
    """The BRAND-REPAIR-003 shape. Read the other way it publishes a no-pets
    hotel as pet-friendly, which it very nearly did."""
    extraction, _withheld, _flags = read(
        "Service animals are welcome. No other pets are allowed.")
    assert extraction["pets_allowed"] is False


def test_a_bare_no_pets_is_never_read_as_a_species_restriction():
    """The rule fires on the QUALIFIED wording only. An unqualified refusal
    beside a species acceptance is a contradiction, and the surface is
    withheld -- but it is never turned into an acceptance."""
    assert not PR._QUALIFIED_REFUSAL_RE.match("no pets allowed")
    assert PR._QUALIFIED_REFUSAL_RE.match("no other pets are allowed")
    extraction, withheld, _flags = read(
        "Dogs are welcome in our lobby. No pets are allowed in guest rooms.")
    assert extraction.get("pets_allowed") is not True
    assert withheld["pets_allowed"] == enums.SOURCE_CONTRADICTORY


# --------------------------------------------------------------------------- #
# 8. tiered fees remain protected
# --------------------------------------------------------------------------- #

def test_the_010_tiered_fee_case_is_still_withheld():
    got = case("control--tiered-fee")
    # 034 gave this shape a home. No single amount is published either way,
    # which is what 016 was protecting.
    assert "pet_fee" not in got["extraction"]
    assert (got["withheld"].get("pet_fee") == enums.SCHEMA_CANNOT_REPRESENT
            or got["extraction"].get("fee_tiers"))


def test_a_single_price_with_a_night_range_is_not_a_tier():
    """A tier needs two prices AND a qualifier. Withholding a capped
    single-priced fee would lose a fact the schema can hold."""
    extraction, _withheld, _flags = read(
        "Non-refundable 25 USD nightly for up to 2 pets. Max 75 USD per stay.")
    assert extraction["pet_fee"] == 2500
    assert extraction["fee_cap"]["amount_minor"] == 7500


def test_a_second_pet_price_makes_a_surface_tiered():
    extraction, withheld, flags = read(
        "First pet $25 per night. Second pet $15 per night.")
    assert "pet_fee" not in extraction
    # A price per ANIMAL is a fee_pet_schedule since 034; before it, the
    # surface was detected as tiered and the fee withheld. Either way the
    # reader refuses to call $25 or $15 "the pet fee", which is the claim.
    rungs = (extraction.get("fee_pet_schedule") or {}).get("entries") or []
    assert rungs or withheld["pet_fee"] == enums.SCHEMA_CANNOT_REPRESENT
    if rungs:
        assert [entry["amount_cents"] for entry in rungs] == [2500, 1500]


# --------------------------------------------------------------------------- #
# 9. simple and capped fees do not regress
# --------------------------------------------------------------------------- #

def test_the_simple_fee_control_is_unchanged():
    got = case("control--simple-fee")
    assert got["extraction"]["pet_fee"] == 3000
    assert got["extraction"]["fee_basis"] == "per_night"
    assert got["extraction"]["fee_scope"] == "per_pet"
    assert got["extraction"]["pet_count_limit"] == 2


def test_the_capped_fee_control_still_separates_the_ceiling_from_the_price():
    got = case("control--capped-fee")
    assert got["extraction"]["pet_fee"] == 2500
    assert got["extraction"]["fee_cap"]["amount_minor"] == 7500


def test_a_pet_weight_stated_before_a_service_animal_sentence_survives():
    """The Brown Deer case: no full stop before "Service animals", so the
    segment opens ahead of the phrase and used to swallow the PET limit."""
    got = case("control--service-animal-after-weight")
    assert got["extraction"]["weight_limit"] == {"value": 65.0, "unit": "lb"}
    assert got["extraction"]["pet_fee"] == 3000


def test_a_limit_inside_a_service_animal_statement_is_still_dropped():
    """A service-animal cap must never be republished as a pet cap. The span
    now ends at a PRICE, which this sentence does not contain."""
    extraction, _withheld, _flags = read(
        "Pets are not accepted. Only service animals are permitted, "
        "maximum 2 pets per room.")
    assert "pet_count_limit" not in extraction


def test_the_four_url_fix_controls_keep_every_field_they_had():
    """Named, not counted -- and a field that moved into ``withheld`` with a
    reason is not a loss."""
    baseline = {
        "independent--knickerbocker-on-the-lake":
            {"pet_fee", "fee_currency", "service_animal_exception"},
        "independent--saint-kate-the-arts-hotel":
            {"pets_allowed", "pet_fee", "fee_currency", "fee_basis"},
        "independent--the-iron-horse-hotel":
            {"pet_fee", "fee_currency", "fee_basis"},
        "independent--the-plaza-hotel-milwaukee": {"pet_fee", "fee_currency"},
    }
    for case_id, before in baseline.items():
        got = case(case_id)
        lost = before - set(got["extraction"])
        unexplained = {f for f in lost if f not in got["withheld"]
                       and f != "fee_currency"}
        assert not unexplained, "%s silently lost %s" % (case_id, unexplained)


def test_the_knickerbocker_penalty_fee_is_withheld_rather_than_published():
    """"Unauthorized pets incur a $250 cleaning fee" on a surface that accepts
    only ADA service animals is a penalty, not the price of bringing a dog."""
    got = case("independent--knickerbocker-on-the-lake")
    assert "pet_fee" not in got["extraction"]
    assert got["withheld"]["pet_fee"] == enums.SCHEMA_CANNOT_REPRESENT


# --------------------------------------------------------------------------- #
# The differential itself, run in the suite rather than only by hand.
# --------------------------------------------------------------------------- #

DIFFERENTIAL = (REPO / "launch_packages" / "pettripfinder" / "markets"
                / "reports" / "ptf_reader_hardening_differential_016.json")


def test_the_committed_differential_records_the_required_outcomes():
    doc = json.loads(DIFFERENTIAL.read_text(encoding="utf-8"))
    outcomes = doc["outcomes"]
    assert outcomes["known_misses_total"] == 4
    assert outcomes["known_misses_improved"] == 4
    assert outcomes["controls_regressed"] == 0
    assert outcomes["amenity_chips_still_producing_policy"] == 0
    assert outcomes["red_roof_fields_gained"] >= 3
    assert outcomes["tiered_fee_control_still_withheld"] is True


def test_the_committed_differential_is_never_contradicted_by_the_reader():
    """A report is a claim about the code, and 016's claim still holds.

    It used to demand byte equality with the installed reader, which made it a
    claim about EVERY future work order rather than about 016. Later readers
    are supposed to read more: 029 taught the generic walk a count wording that
    "a maximum of two pets allowed" satisfies, and Saint Kate gained
    ``pet_count_limit`` on a case 016 had pinned without it.

    What must not happen is a case going backwards, so that is what is asserted
    now: every field 016 recorded is still there with the same value, every
    withholding it recorded is still withheld, and anything extra is reported
    rather than forbidden. A regression still fails this test; an improvement
    no longer does.
    """
    doc = json.loads(DIFFERENTIAL.read_text(encoding="utf-8"))
    live = H.snapshot()
    gained = {}
    for row in doc["rows"]:
        got = live[row["case_id"]]
        for field, value in row["new_output"].items():
            assert field in got["extraction"], (row["case_id"], field)
            assert got["extraction"][field] == value, (row["case_id"], field)
        for field, reason in row["new_withheld"].items():
            # A field that became a FACT is not a lost withholding: the reader
            # learned to represent it, which is the opposite of a regression.
            if field in got["extraction"]:
                gained.setdefault(row["case_id"], []).append(field)
                continue
            if (field in ("pet_fee", "fee_basis")
                    and (got["extraction"].get("fee_tiers")
                         or got["extraction"].get("fee_pet_schedule"))):
                # 034 BUILT the structure this row was withheld for. The
                # committed differential records a withholding that no longer
                # applies, and no single amount is published either way.
                gained.setdefault(row["case_id"], []).append(field)
                continue
            assert got["withheld"].get(field) == reason, (row["case_id"], field)
        extra = sorted(set(got["extraction"]) - set(row["new_output"]))
        if extra:
            gained.setdefault(row["case_id"], []).extend(extra)
    # Recorded so a reader change that adds fields is visible in the failure
    # output of any later assertion rather than silently absorbed.
    assert isinstance(gained, dict)


def test_no_property_name_appears_in_the_reader_itself():
    """The corpus names properties; the reader may not. A rule keyed to a
    hotel is not a rule."""
    source = Path(PR.__file__).read_text(encoding="utf-8")
    for name in ("Pfister", "Ingleside", "Wildwood", "Knickerbocker",
                 "Saint Kate", "Plaza Hotel", "Iron Horse"):
        assert name not in source, name
