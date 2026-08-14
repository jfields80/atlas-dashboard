"""PTF-RENDERER-FIDELITY-001 -- regression over the real committed corpus.

Synthetic reachability proves the renderer CAN carry a fact. These tests prove
it carries the facts actually committed, on the named properties whose current
output was wrong.

Every record here is loaded from committed authority through the Phase A
compatibility layer. Nothing is migrated; the authority stays byte-identical.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.pettripfinder import canonical_view
from scripts.pettripfinder.contracts import enums
from scripts.pettripfinder.hotel_profile import (
    WITHHELD_CLS, _verified_details, _verified_facts, _verified_summary,
    canonical_fee_scope, weight_display,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_DIR = REPO_ROOT / "launch_packages" / "pettripfinder"

PACKAGES = {
    "columbus-oh": "hotel_policy_facts.json",
    "cleveland-akron-canton-oh": "hotel_policy_facts_cleveland-akron-canton-oh.json",
    "dayton-oh": "hotel_policy_facts_dayton-oh.json",
}


def load(market_id):
    path = PACKAGE_DIR / PACKAGES[market_id]
    if not path.is_file():
        pytest.skip("%s is not present in this worktree" % path.name)
    return json.loads(path.read_text(encoding="utf-8-sig"))["hotels"]


def find(market_id, fragment):
    for record in load(market_id):
        if fragment in record["key"].lower():
            return record
    pytest.skip("no committed record matching %r" % fragment)


def profile_text(record):
    f = record["facts"]
    parts = [_verified_summary(f, record.get("evidence_quote") or "")]
    parts += ["%s %s" % (l, v) for l, v, _c in _verified_facts(f)]
    parts += ["%s %s" % (l, v) for l, v, _c in _verified_details(f, record)[0]]
    return " | ".join(parts)


def comparison_html(record):
    """The comparison row this record produces, rendered.

    Built here rather than imported from the reachability module: the two test
    files are independent gates and coupling them means one breaking takes the
    other with it.
    """
    from scripts.pettripfinder.hotel_profile import (
        cap_qualifier_note, fee_qualifier_phrase, fee_scope_display,
    )
    from scripts.pettripfinder.markets import load_markets, market_by_id
    from scripts.pettripfinder.site_pages import build_comparison_page

    f = record["facts"]
    view = canonical_view.build(record)
    row = {
        "name": record.get("name", record["key"]), "route": "/x/",
        "area": "Columbus, OH",
        "species_allowed": f.get("species_allowed", ""),
        "pet_fee": f.get("pet_fee", ""),
        "fee_basis": fee_qualifier_phrase(f) or f.get("fee_basis", ""),
        "fee_scope_display": fee_scope_display(f),
        "cats_state": view.cats_state,
        "fee_cap_qualifier": cap_qualifier_note(f),
        "fee_scalar_suppressed": bool(
            view.fee_display_mode == "withhold_scalar" and f.get("pet_fee")),
        "pet_count_limit": f.get("pet_count_limit", ""),
        "weight_limit": f.get("weight_limit", ""),
        "weight_limit_operator": f.get("weight_limit_operator", ""),
        "weight_limit_combined": f.get("weight_limit_combined", ""),
        "weight_limit_combined_operator": f.get("weight_limit_combined_operator", ""),
        "fee_tiers": f.get("fee_tiers") or [],
        "fee_cap": f.get("fee_cap") or {},
        "fee_conflict": f.get("fee_conflict"),
        "fee_withheld": f.get("fee_withheld"),
        "verified_at": record.get("verified_at", ""),
    }
    return build_comparison_page([row], market_by_id(load_markets(), "columbus-oh"))


class TestA_ColumbusFailsClosed:
    """The six conflict/withheld records must not gain a definitive fee."""

    def cohort(self):
        return [r for r in load("columbus-oh")
                if r["facts"].get("fee_conflict") or r["facts"].get("fee_withheld")]

    def test_the_cohort_is_the_expected_size(self):
        assert len(self.cohort()) == 6

    def test_no_record_publishes_a_scalar_fee(self):
        for record in self.cohort():
            view = canonical_view.build(record)
            assert view.fee_display_mode == "withhold_scalar", record["key"]
            assert canonical_view.fee_phrase(view) == "", record["key"]

    def test_no_record_is_computable(self):
        for record in self.cohort():
            view = canonical_view.build(record)
            assert view.computation_class == enums.NOT_COMPUTABLE, record["key"]

    def test_each_says_withheld_rather_than_not_stated(self):
        for record in self.cohort():
            rows = {l: (v, c) for l, v, c in
                    _verified_details(record["facts"], record)[0]}
            value, cls = rows["Charge basis"]
            assert cls == WITHHELD_CLS, record["key"]
            assert "Not stated by the reviewed source" not in value, record["key"]

    def test_generalising_withheld_fields_did_not_open_a_fee(self):
        """The whole cohort still shows no amount anywhere on the page."""
        for record in self.cohort():
            text = profile_text(record)
            quote = record["facts"].get("fee_conflict") or record["facts"]["fee_withheld"]
            for amount in ("$75", "$125", "$150", "$80"):
                if amount in str(quote.get("evidence_quote", "")):
                    assert amount not in text, "%s leaked %s" % (record["key"], amount)


class TestB_DaytonPerPetCohort:
    """Ten Dayton fee-scope values reached no public surface at all."""

    def cohort(self):
        return [r for r in load("dayton-oh") if r["facts"].get("fee_scope")]

    def test_every_scope_is_canonical(self):
        for record in self.cohort():
            assert canonical_fee_scope(record["facts"]) in (
                enums.SCOPE_PER_ROOM, enums.SCOPE_PER_PET), record["key"]

    def test_the_cohort_is_ten_records(self):
        assert len(self.cohort()) == 10

    def test_per_pet_is_visible_on_every_per_pet_record(self):
        per_pet = [r for r in self.cohort()
                   if canonical_fee_scope(r["facts"]) == enums.SCOPE_PER_PET]
        assert len(per_pet) == 8
        for record in per_pet:
            # A property with no fee amount has nothing to scope; every one
            # that states an amount must show who it attaches to.
            if not record["facts"].get("pet_fee"):
                continue
            assert "per pet" in profile_text(record).lower(), record["key"]


class TestC_DaysInnSidney:
    """$15 per pet per night must never read as $15 for the room."""

    def record(self):
        return find("dayton-oh", "days inn by wyndham sidney")

    def test_the_summary_states_per_pet(self):
        record = self.record()
        summary = _verified_summary(record["facts"],
                                    record.get("evidence_quote") or "")
        assert "per pet per night" in summary
        assert "$15" in summary

    def test_the_chip_states_per_pet(self):
        chips = {l: v for l, v, _c in _verified_facts(self.record()["facts"])}
        assert "per pet" in chips["Charge basis"].lower()

    def test_the_detail_row_states_per_pet(self):
        rows = {l: v for l, v, _c in
                _verified_details(self.record()["facts"], self.record())[0]}
        assert "per pet" in rows["Charge basis"].lower()

    def test_two_pets_are_priced_per_animal_not_per_room(self):
        """The record allows 2 pets, so the scope is what decides the bill."""
        view = canonical_view.build(self.record())
        assert view.fee.scope == enums.SCOPE_PER_PET
        assert view.facts["pet_count_limit"] == 2
        # Per-pet with a stated limit is fully computable; a reader can
        # multiply, and the page gives them the number to multiply.
        assert view.computation_class == \
            enums.COMPUTATION_SAFE_ARBITRARY_ALLOWED_PET_COUNT
        assert canonical_view.fee_phrase(view) == "$15 per pet per night"

    def test_no_total_is_asserted_by_the_renderer(self):
        """Showing the rate is right; inventing "$30 for two" is not."""
        assert "$30" not in profile_text(self.record())


class TestD_StaybridgeMiamisburg:
    """A $50 scalar over a source that also states $150."""

    def record(self):
        return find("dayton-oh", "staybridge suites miamisburg")

    def test_the_source_really_does_carry_a_higher_amount(self):
        restrictions = self.record()["facts"]["general_restrictions"]
        assert "150" in restrictions and "50 per pet" in restrictions

    def test_the_canonical_view_refuses_the_scalar(self):
        view = canonical_view.build(self.record())
        assert view.computation_class == enums.CONDITIONALLY_SAFE
        assert view.has_undeclared_second_amount is True
        assert view.fee_display_mode == "withhold_scalar"

    def test_the_comparison_no_longer_shows_fifty_as_the_fee(self):
        html = comparison_html(self.record())
        assert "See policy wording" in html
        # The bare scalar must not stand as the fee cell.
        assert ">$50.00<" not in html
        assert "$50.00" not in html

    def test_the_scope_is_still_shown(self):
        """Suppressing the amount must not suppress what IS known."""
        assert canonical_fee_scope(self.record()["facts"]) == enums.SCOPE_PER_PET


class TestE_ColumbusExplicitNoWeightLimit:
    """An affirmative "no weight limit" is the opposite of silence."""

    def cohort(self):
        return [r for r in load("columbus-oh")
                if r["facts"].get("weight_limit_stated_none") == "true"]

    def test_the_cohort_exists(self):
        assert len(self.cohort()) == 2

    def test_it_never_reads_as_not_stated(self):
        for record in self.cohort():
            text = profile_text(record)
            assert "no pet weight limit" in text.lower(), record["key"]

    def test_the_weight_cell_is_not_the_silence_string(self):
        for record in self.cohort():
            assert weight_display(record["facts"]) != ""
            rows = {l: (v, c) for l, v, c in
                    _verified_details(record["facts"], record)[0]}
            value, cls = rows["Weight restriction"]
            assert cls != "dim", record["key"]


class TestF_CombinedWeightNeverBecomesIndividual:
    """Drury's combined limit must not be read as a per-animal ceiling."""

    def records(self):
        out = []
        for market in ("cleveland-akron-canton-oh", "columbus-oh"):
            out += [r for r in load(market)
                    if r["facts"].get("weight_limit_operator") == "combined"]
        return out

    def test_the_cohort_exists(self):
        assert len(self.records()) == 5

    def test_canonical_moves_the_value_to_the_combined_field(self):
        for record in self.records():
            view = canonical_view.build(record)
            assert view.weight_combined is not None, record["key"]
            assert view.weight_individual is None, record["key"]

    def test_the_page_says_combined(self):
        for record in self.records():
            text = profile_text(record).lower()
            assert "combined" in text, record["key"]

    def test_no_canonical_record_keeps_combined_as_an_operator(self):
        """After canonicalisation the token is gone from every operator slot."""
        for market in PACKAGES:
            for record in load(market):
                view = canonical_view.build(record)
                for limit in (view.weight_individual, view.weight_combined):
                    if limit:
                        assert limit["operator"] in enums.WEIGHT_OPERATORS, \
                            record["key"]


class TestG_CatProhibition:
    """An explicit refusal must never render as silence."""

    def records(self):
        out = []
        for market in PACKAGES:
            out += [r for r in load(market)
                    if r["facts"].get("cats_allowed") == "false"]
        return out

    def test_the_cohort_exists(self):
        assert len(self.records()) == 3

    def test_the_chip_says_not_allowed(self):
        for record in self.records():
            chips = {l: v for l, v, _c in _verified_facts(record["facts"])}
            assert chips["Cats"] == "Not allowed", record["key"]

    def test_the_detail_table_states_the_refusal(self):
        for record in self.records():
            rows = {l: v for l, v, _c in
                    _verified_details(record["facts"], record)[0]}
            assert "Cats" in rows, record["key"]
            assert "Not accepted" in rows["Cats"], record["key"]

    def test_it_is_never_the_silence_string(self):
        for record in self.records():
            chips = {l: v for l, v, _c in _verified_facts(record["facts"])}
            assert chips["Cats"] != "Not stated", record["key"]


class TestNoRecordBecameLessInformative:
    """The safety net over the whole corpus.

    Phase B may change what a page says; it may not make a page say less. Any
    record that published a fee amount before must still communicate one, or
    say explicitly why it does not.
    """

    def test_every_record_with_a_fee_still_addresses_it(self):
        for market in PACKAGES:
            for record in load(market):
                if not record["facts"].get("pet_fee"):
                    continue
                text = profile_text(record)
                view = canonical_view.build(record)
                if view.fee_display_mode == "withhold_scalar":
                    # Suppressed on purpose -- the page must SAY so.
                    assert ("policy wording" in text.lower()
                            or "published wording" in text.lower()
                            or "withheld" in text.lower()
                            or "conflicting" in text.lower()), record["key"]
                else:
                    assert record["facts"]["pet_fee"].rstrip("0").rstrip(".") \
                        in text or "$" in text, record["key"]

    def test_no_page_carries_a_raw_enum(self):
        """No internal vocabulary leaks to a reader."""
        leaks = ("per_room", "per_pet", "per_night", "per_stay",
                 "SOURCE_CONTRADICTORY", "SCHEMA_CANNOT_REPRESENT",
                 "COMPUTATION_SAFE", "CONDITIONALLY_SAFE", "NOT_COMPUTABLE",
                 "ONE_TIME_CHARGE", "REPLACEMENT_PRICE")

        for market in PACKAGES:
            for record in load(market):
                text = profile_text(record)
                for token in leaks:
                    assert token not in text, "%s leaked %s" % (record["key"], token)
