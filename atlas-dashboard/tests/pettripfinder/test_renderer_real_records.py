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


def shown(record):
    """Display values, exactly as the production renderer obtains them.

    PTF-POLICY-SCHEMA-MIGRATION-001: authority is canonical 1.2 now, and every
    render path goes through the projection. A test reading record["facts"]
    straight would be exercising a path production does not have.
    """
    return canonical_view.display_facts(record)


def profile_text(record):
    f = shown(record)
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
        # 1.2 replaced the two fee-specific legacy markers with one
        # reason-coded withholding decision.
        return [r for r in load("columbus-oh")
                if "pet_fee" in (r.get("withheld_fields") or {})]

    def test_the_cohort_is_the_expected_size(self):
        assert len(self.cohort()) == 7

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
                    _verified_details(shown(record), record)[0]}
            value, cls = rows["Charge basis"]
            assert cls == WITHHELD_CLS, record["key"]
            assert "Not stated by the reviewed source" not in value, record["key"]

    def test_generalising_withheld_fields_did_not_open_a_fee(self):
        """The whole cohort still shows no amount anywhere on the page."""
        for record in self.cohort():
            text = profile_text(record)
            reason = record["withheld_fields"]["pet_fee"]["reason"]
            for amount in ("$75", "$125", "$150", "$80"):
                if amount in reason:
                    assert amount not in text, "%s leaked %s" % (record["key"], amount)


class TestB_DaytonPerPetCohort:
    """Dayton fee-scope values that reached no public surface at all.

    Ten at Phase B; twelve now, because Phase F recovered the scope of two
    La Quinta records from the property's own "for up to 2 pets" wording.
    """

    def cohort(self):
        return [r for r in load("dayton-oh")
                if (r["facts"].get("pet_fee") or {}).get("scope")]

    def test_every_scope_is_canonical(self):
        for record in self.cohort():
            assert canonical_fee_scope(shown(record)) in (
                enums.SCOPE_PER_ROOM, enums.SCOPE_PER_PET), record["key"]

    def test_the_cohort_is_twelve_records(self):
        assert len(self.cohort()) == 12

    def test_per_pet_is_visible_on_every_per_pet_record(self):
        per_pet = [r for r in self.cohort()
                   if canonical_fee_scope(shown(r)) == enums.SCOPE_PER_PET]
        assert len(per_pet) == 8
        for record in per_pet:
            # A property with no fee amount has nothing to scope; every one
            # that states an amount must show who it attaches to.
            if not shown(record).get("pet_fee"):
                continue
            assert "per pet" in profile_text(record).lower(), record["key"]


class TestC_DaysInnSidney:
    """$15 per pet per night must never read as $15 for the room."""

    def record(self):
        return find("dayton-oh", "days inn by wyndham sidney")

    def test_the_summary_states_per_pet(self):
        record = self.record()
        summary = _verified_summary(shown(record),
                                    record.get("evidence_quote") or "")
        assert "per pet per night" in summary
        assert "$15" in summary

    def test_the_chip_states_per_pet(self):
        chips = {l: v for l, v, _c in _verified_facts(shown(self.record()))}
        assert "per pet" in chips["Charge basis"].lower()

    def test_the_detail_row_states_per_pet(self):
        rows = {l: v for l, v, _c in
                _verified_details(shown(self.record()), self.record())[0]}
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

    def test_the_ladder_the_property_stated_is_now_published(self):
        """Phase B could only WARN that $50 was not the whole charge, because
        the legacy structure had nowhere to put a 1-6 / 7+ ladder. 1.2 does, so
        the reader is given the property's actual prices instead of a caution
        about the one they were shown."""
        tiers = self.record()["facts"]["fee_tiers"]
        assert [(t["amount_cents"], t["condition_min"], t.get("condition_max"))
                for t in tiers] == [(5000, 1, 6), (15000, 7, None)]
        assert all(t["scope"] == enums.SCOPE_PER_PET for t in tiers)

    def test_the_comparison_never_shows_fifty_alone_as_the_fee(self):
        """The defect this record exists to guard: $50 standing as THE fee."""
        html = comparison_html(self.record())
        assert ">$50.00<" not in html
        assert "$50–$150" in html or "$50" not in html

    def test_the_scope_is_still_shown(self):
        """Suppressing the amount must not suppress what IS known."""
        assert canonical_fee_scope(shown(self.record())) == enums.SCOPE_PER_PET
        assert "per pet" in profile_text(self.record()).lower()


class TestE_ColumbusExplicitNoWeightLimit:
    """An affirmative "no weight limit" is the opposite of silence."""

    def cohort(self):
        return [r for r in load("columbus-oh")
                if r["facts"].get("weight_limit_stated_none") is True]

    def test_the_cohort_exists(self):
        # Two at migration; three since PTF-POLICY-SCHEMA-MIGRATION-001A read
        # "with no breed or weight restrictions" off a page it had skipped.
        assert len(self.cohort()) == 3

    def test_it_never_reads_as_not_stated(self):
        for record in self.cohort():
            text = profile_text(record)
            assert "no pet weight limit" in text.lower(), record["key"]

    def test_the_weight_cell_is_not_the_silence_string(self):
        for record in self.cohort():
            assert weight_display(shown(record)) != ""
            rows = {l: (v, c) for l, v, c in
                    _verified_details(shown(record), record)[0]}
            value, cls = rows["Weight restriction"]
            assert cls != "dim", record["key"]


class TestF_CombinedWeightNeverBecomesIndividual:
    """Drury's combined limit must not be read as a per-animal ceiling."""

    def records(self):
        # The overload cohort, canonically: a combined limit standing ALONE.
        # Under 1.1 these carried the value in weight_limit with the operator
        # slot overloaded to "combined"; 1.2 gives the fact its own field, and
        # Phase F moved two more Drury records here that the legacy shape had
        # recorded as per-pet maxima their pages never granted.
        out = []
        for market in PACKAGES:
            out += [r for r in load(market)
                    if r["facts"].get("combined_weight_limit")
                    and not r["facts"].get("weight_limit")]
        return out

    def test_the_cohort_exists(self):
        assert len(self.records()) == 9  # +Hampton Tiedeman (Pass 3)

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
                    if (r["facts"].get("species") or {}).get("cats") == "prohibited"]
        return out

    def test_the_cohort_exists(self):
        # Three at migration; five since the evidence reconciliation carried
        # across two more properties that refuse cats in their own words; six
        # since Pass 2 published Aloft Beachwood ("Dogs only- no cats...").
        assert len(self.records()) == 7  # +Super 8 Uniontown (Pass 3)

    def test_the_chip_says_not_allowed(self):
        for record in self.records():
            chips = {l: v for l, v, _c in _verified_facts(shown(record))}
            assert chips["Cats"] == "Not allowed", record["key"]

    def test_the_detail_table_states_the_refusal(self):
        for record in self.records():
            rows = {l: v for l, v, _c in
                    _verified_details(shown(record), record)[0]}
            assert "Cats" in rows, record["key"]
            assert "Not accepted" in rows["Cats"], record["key"]

    def test_it_is_never_the_silence_string(self):
        for record in self.records():
            chips = {l: v for l, v, _c in _verified_facts(shown(record))}
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
                if not shown(record).get("pet_fee"):
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
                    amount = shown(record)["pet_fee"].rstrip("0").rstrip(".")
                    assert amount in text or "$" in text, record["key"]

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
