"""PTF-POLICY-P0-001 -- Drury observation adapter and Sonesta pilot framework."""

from __future__ import annotations

import pytest

from scripts.pettripfinder.policy import policy_membrane as M
from scripts.pettripfinder.policy import readiness as R
from scripts.pettripfinder.policy.adapters import drury
from scripts.pettripfinder.policy.pilots import sonesta

#: The live text observed on the Drury Dublin property page during this work
#: order's §9 verification, quoted verbatim. It is a FIXTURE, not a fact source:
#: nothing here writes to the policy authority.
DRURY_DUBLIN_TEXT = (
    "Hotel Information. Dogs and cats accepted. Rooms with pets will be "
    "charged a daily fee of $50 per room plus tax. Service animals are free "
    "of charge. Limit of two pets per room with a combined weight of 80 pounds."
)

HOTEL_REF = {
    "market_id": "columbus-oh",
    "canonical_name": "Drury Inn & Suites Columbus Dublin",
    "normalized_name": "drury inn and suites columbus dublin",
    "official_url": "https://www.druryhotels.com/locations/columbus-oh/"
                    "drury-inn-and-suites-columbus-dublin",
}


def observe(text=DRURY_DUBLIN_TEXT, **kw):
    params = dict(
        text=text, hotel_ref=HOTEL_REF,
        source_url=HOTEL_REF["official_url"], obs_id="drury-dublin-1",
        observed_at="2026-08-08", retrieved_at="2026-08-08T12:00:00Z",
        name_on_page="Drury Inn & Suites Columbus Dublin",
        address_on_page="6170 Parkcenter Circle")
    params.update(kw)
    return drury.observe(**params)


def test_drury_extracts_every_field_the_page_states():
    extraction = drury.extract(DRURY_DUBLIN_TEXT)["extraction"]
    assert extraction["pets_allowed"] is True
    assert extraction["species_allowed"] == "dogs_and_cats"
    assert extraction["pet_fee"] == 5000            # integer minor units
    assert extraction["fee_currency"] == "USD"
    assert extraction["fee_basis"] == "per_night"   # "daily fee"
    assert extraction["fee_scope"] == "per_room"    # "per room"
    assert extraction["pet_count_limit"] == 2       # "two"
    assert extraction["weight_limit"] == 80
    assert extraction["weight_limit_operator"] == "combined"


def test_drury_never_invents_a_per_pet_weight_from_a_combined_one():
    extraction = drury.extract(DRURY_DUBLIN_TEXT)["extraction"]
    # The page says COMBINED. Dividing 80 by two pets would be an invention.
    assert extraction["weight_limit_operator"] == "combined"
    assert extraction["weight_limit"] == 80


def test_drury_captures_service_animal_text_without_reading_it_as_permission():
    extraction = drury.extract(DRURY_DUBLIN_TEXT)["extraction"]
    assert "service animals" in extraction["service_animal_exception"].lower()
    # pets_allowed came from "Dogs and cats accepted", not from the ADA line.
    assert extraction["pets_allowed"] is True


def test_drury_service_animal_only_page_establishes_nothing():
    text = "Hotel Information. Service animals are free of charge."
    result = drury.extract(text)
    assert "pets_allowed" not in result["extraction"]
    assert any(f["code"] == "FLAG_SERVICE_ANIMAL_ONLY" for f in result["flags"])


def test_drury_populates_nothing_from_a_page_that_says_nothing():
    result = drury.extract("Hotel Information. Free hot breakfast daily.")
    assert result["extraction"] == {}
    assert result["quote"] == ""


def test_drury_no_brand_default_leaks_into_a_silent_page():
    """The decisive anti-default test: a Drury page with no pet sentence must
    not inherit the $50/2-pets/80lb shape from its siblings."""
    result = drury.extract("Hotel Information. Indoor pool and fitness center.")
    assert result["extraction"] == {}


def test_drury_dogs_only_records_an_explicit_negative_for_cats():
    text = "Dogs only. A daily fee of $40 per room applies."
    extraction = drury.extract(text)["extraction"]
    assert extraction["species_allowed"] == "dogs_only"
    assert extraction["cats_allowed"] is False


def test_drury_ambiguous_basis_is_flagged_not_guessed():
    # The fee must be stated in a sentence that mentions pets. That discipline
    # is what stops a resort fee being read as a pet fee, so the fixture says
    # "pet fee" rather than a bare "fee".
    text = "Dogs and cats accepted. A pet fee of $50 applies."
    result = drury.extract(text)
    assert result["extraction"]["fee_basis"] == "unknown"
    assert result["extraction"]["fee_scope"] == "unknown"
    codes = {f["code"] for f in result["flags"]}
    assert "FLAG_AMBIGUOUS_BASIS" in codes and "FLAG_AMBIGUOUS_SCOPE" in codes


def test_drury_observation_passes_the_membrane_and_confirms():
    obs = observe()
    verdict = M.evaluate(obs)
    assert verdict.verdict == M.VALID
    assert verdict.may_establish is True
    assert R.derive([obs]).state == R.POLICY_CONFIRMED


def test_drury_every_populated_field_is_quote_backed():
    obs = observe()
    refs = set(obs["evidence"][0]["field_refs"])
    asserted = {k for k, v in obs["extraction"].items() if v not in ("", None, "not_stated")}
    assert asserted <= refs


def test_drury_on_a_booking_mirror_is_rejected():
    obs = observe(source_url="https://drury-dublin.h-rez.com/policies")
    assert M.evaluate(obs).verdict == M.REJECT_WRONG_PROPERTY


def test_drury_on_the_wrong_property_is_rejected():
    obs = observe(name_on_page="Hampton Inn Columbus Airport")
    assert M.evaluate(obs).verdict == M.REJECT_WRONG_PROPERTY


# --------------------------------------------------------------------------- #
# Sonesta pilot framework
# --------------------------------------------------------------------------- #

def rows(n):
    return [{"canonical_name": "Sonesta Sample %02d" % i,
             "official_url": "https://www.sonesta.com/sample-%02d" % i}
            for i in range(n)]


def test_pilot_is_bounded_at_ten_properties():
    with pytest.raises(sonesta.PilotError, match="bounded at 10"):
        sonesta.build_targets(rows(11), market_id="columbus-oh")


def test_pilot_plan_is_deterministic():
    targets = sonesta.build_targets(rows(3), market_id="columbus-oh")
    assert sonesta.plan(targets) == sonesta.plan(targets)


def test_pilot_targets_are_sorted_and_deduplicated():
    dupes = rows(2) + [{"canonical_name": "Sonesta Sample 00"}]
    targets = sonesta.build_targets(dupes, market_id="columbus-oh")
    assert len(targets) == 2
    assert [t.normalized_name for t in targets] == sorted(t.normalized_name for t in targets)


def test_pilot_target_mints_no_new_identifier():
    target = sonesta.build_targets(rows(1), market_id="columbus-oh")[0]
    assert set(target.hotel_ref()) <= {"market_id", "canonical_name",
                                       "normalized_name", "official_url",
                                       "street_identity"}


def test_pilot_plan_declares_it_did_not_run():
    plan = sonesta.plan(sonesta.build_targets(rows(2), market_id="columbus-oh"))
    assert "PLAN ONLY" in plan["authorisation_note"]
    assert plan["attempts_planned"] == 2 * len(sonesta.PILOT_LADDER)


def test_pilot_summary_promotes_nothing():
    summary = sonesta.summarize([])
    assert summary["promotion_performed"] is False
    assert "no promotion path" in summary["promotion_note"]


def test_pilot_summary_recomputes_readiness_rather_than_trusting_the_worker():
    bundle = {
        "hotel_ref": HOTEL_REF,
        "observations": [observe(obs_id="s1")],
        "observations_count": 1,
        "ladder_transcript": [{"attempt": 1, "step": "A",
                               "source_attempted": "x",
                               "capture_method": "browser_assisted",
                               "outcome": "SUCCESS"}],
        # A worker claiming a state the observations do not support.
        "proposed_readiness": R.POLICY_PARTIAL,
    }
    summary = sonesta.summarize([bundle])
    assert summary["per_hotel"][0]["derived_state"] == R.POLICY_CONFIRMED
    assert summary["per_hotel"][0]["worker_proposed"] == R.POLICY_PARTIAL


def test_no_sonesta_adapter_was_built_on_assumptions():
    """The work order forbids a full Sonesta adapter built from research
    assumptions. Assert the module really is framework-only."""
    import scripts.pettripfinder.policy.adapters as adapters_pkg
    from pathlib import Path
    names = {p.stem for p in Path(adapters_pkg.__file__).parent.glob("*.py")}
    assert "sonesta" not in names
