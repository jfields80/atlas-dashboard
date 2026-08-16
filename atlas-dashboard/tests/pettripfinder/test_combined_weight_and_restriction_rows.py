"""PTF-COLUMBUS-INTEGRATE-UNRESOLVED-001 -- combined-weight semantics and the
four additive restriction rows.

WHY THESE TESTS EXIST
---------------------
Two different things can tell the renderer a weight limit is COMBINED rather
than per-pet:

  * ``weight_limit_operator == "combined"``, a structured value the Drury policy
    adapter has emitted since PTF-POLICY-P0-001; and
  * the word "combined" sitting next to the number in the raw evidence text.

Before this change only the second existed in the render layer, so a record
carrying the structured value rendered "Maximum pet weight is 80 pounds" -- a
per-pet promise the source never made. The fix honours the structured operator
and keeps the text scan as a fallback.

The dangerous direction is the other one: a text scan that overrides an
explicit per-pet operator would relabel a real per-pet ceiling as combined and
tell an owner of two 60-pound dogs they may bring both. ``test_explicit_per_pet
_operator_suppresses_the_text_fallback`` is the test that must never be deleted.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from scripts.pettripfinder.hotel_profile import (
    _source_states_combined_weight,
    _verified_details,
    _verified_summary,
    weight_display,
    weight_phrase,
)

_PKG = (pathlib.Path(__file__).resolve().parents[2]
        / "launch_packages" / "pettripfinder" / "hotel_policy_facts.json")


def _facts(**kw):
    base = {"pets_allowed": "true"}
    base.update(kw)
    return base


# --------------------------------------------------------------------------- #
# The structured operator.
# --------------------------------------------------------------------------- #

class TestCombinedOperator:

    def test_combined_operator_produces_combined_summary_prose(self):
        summary = _verified_summary(
            _facts(weight_limit="80 pounds", weight_limit_operator="combined",
                   pet_count_limit="2"), evidence="")
        assert "combined weight limit of 80 pounds" in summary
        # The per-pet promise must not appear anywhere in the same sentence set.
        assert "Maximum pet weight is 80 pounds" not in summary

    def test_combined_operator_needs_no_supporting_evidence_text(self):
        """The structured value is authoritative on its own. A record whose
        evidence quote was truncated or never stored still renders correctly."""
        assert "combined" in _verified_summary(
            _facts(weight_limit="80 pounds", weight_limit_operator="combined",
                   pet_count_limit="2"), evidence="")

    def test_combined_operator_marks_the_table_cells(self):
        f = _facts(weight_limit="80 pounds", weight_limit_operator="combined")
        assert weight_display(f) == "80 pounds combined"
        assert weight_phrase(f) == "80 pounds combined"

    def test_absent_operator_and_absent_evidence_stay_per_pet(self):
        summary = _verified_summary(
            _facts(weight_limit="80 pounds", pet_count_limit="2"), evidence="")
        assert "combined" not in summary

    def test_explicit_per_pet_operator_suppresses_the_text_fallback(self):
        """The load-bearing one. An explicit per-pet limit must survive evidence
        text that happens to contain the word 'combined' -- otherwise a real
        50-pound-per-pet ceiling is republished as a 50-pound combined one and
        the second dog is turned away at the desk."""
        evidence = ("Up to 50 pounds per pet (two dogs permitted if combined "
                    "weight is under 75 pounds).")
        summary = _verified_summary(
            _facts(weight_limit="50 pounds", weight_limit_operator="per_pet",
                   pet_count_limit="2"), evidence=evidence)
        assert "combined weight limit" not in summary

    def test_explicit_lt_operator_also_suppresses_the_text_fallback(self):
        evidence = "Two pets with a combined weight of 80 pounds are welcome."
        summary = _verified_summary(
            _facts(weight_limit="80 pounds", weight_limit_operator="lt",
                   pet_count_limit="2"), evidence=evidence)
        assert "combined weight limit" not in summary
        assert "under 80 pounds" in summary.lower()


# --------------------------------------------------------------------------- #
# The text fallback, and the stem it now matches.
# --------------------------------------------------------------------------- #

class TestCombinedTextFallback:

    @pytest.mark.parametrize("text", [
        "max combine weight of 80lbs for two pets",
        "maximum combined weight of 80 pounds",
        "two pets whose weights combine to 80 pounds or less",
        "80 lbs combined",
    ])
    def test_combine_family_words_are_detected(self, text):
        assert _source_states_combined_weight(text, "80 pounds")

    def test_a_combined_word_near_the_published_number_is_a_known_false_positive(self):
        """Documented limitation, asserted so nobody 'fixes' it by accident.

        In "Up to 50 pounds per pet; combined weight may not exceed 75 pounds"
        the word 'combined' falls inside the 30-character window after the
        published 50, so the text scan says combined and is WRONG. This
        predates the current change and the scan cannot resolve it -- both
        numbers are real and both words are real.

        What protects the reader is precedence, not the regex: a source stating
        both limits yields weight_limit_operator == 'per_pet' (see
        policy/adapters/drury.py), and the explicit operator wins outright. The
        test below is the one that matters; this one only pins the fallback's
        known shape."""
        text = "Up to 50 pounds per pet; combined weight may not exceed 75 pounds."
        assert _source_states_combined_weight(text, "50 pounds")
        # ...and the explicit operator overrides it, which is the real defence.
        assert "combined weight limit" not in _verified_summary(
            _facts(weight_limit="50 pounds", weight_limit_operator="per_pet",
                   pet_count_limit="2"), evidence=text)

    def test_a_distant_combine_word_does_not_match(self):
        text = ("Maximum pet weight is 80 pounds. Housekeeping will combine "
                "service requests where possible.")
        assert not _source_states_combined_weight(text, "80 pounds")

    def test_no_weight_limit_means_no_combined_claim(self):
        assert not _source_states_combined_weight("combined 80", "")

    def test_fallback_still_drives_the_summary_when_no_operator_recorded(self):
        summary = _verified_summary(
            _facts(weight_limit="80 pounds", pet_count_limit="2"),
            evidence="max combine weight of 80lbs for two pets")
        assert "combined weight limit of 80 pounds" in summary


# --------------------------------------------------------------------------- #
# The four additive rows.
# --------------------------------------------------------------------------- #

class TestAdditiveRestrictionRows:

    def _labels(self, f):
        rows, _, _ = _verified_details(f)
        return {r[0]: r[1] for r in rows}

    def test_general_restrictions_renders(self):
        cells = self._labels(_facts(pet_fee="$50.00",
                                    general_restrictions="Guests must be 21 or older."))
        assert cells["Other restrictions"] == "Guests must be 21 or older."

    def test_pet_room_restriction_renders(self):
        cells = self._labels(_facts(pet_fee="$50.00",
                                    pet_room_restriction="Limited number of pet rooms."))
        assert cells["Pet room availability"] == "Limited number of pet rooms."

    def test_eligible_room_types_renders(self):
        cells = self._labels(_facts(pet_fee="$50.00",
                                    eligible_room_types="Ground-floor rooms only."))
        assert cells["Eligible room types"] == "Ground-floor rooms only."

    def test_reservation_requirement_renders(self):
        cells = self._labels(_facts(pet_fee="$50.00",
                                    reservation_requirement="Valid CC on file at FD"))
        assert cells["Reservation requirement"] == "Valid CC on file at FD"

    @pytest.mark.parametrize("label", [
        "Other restrictions", "Pet room availability", "Eligible room types",
        "Reservation requirement"])
    def test_absent_fields_emit_no_row_at_all(self, label):
        """Not a dim 'Not stated' -- no row. These are new to the render layer
        and an unconditional row would add a line to every existing page to say
        nothing about a question no source was ever asked."""
        assert label not in self._labels(_facts(pet_fee="$50.00"))


# --------------------------------------------------------------------------- #
# The live authority must not drift.
# --------------------------------------------------------------------------- #

class TestPublishedRecordsDoNotDrift:

    def _pkg(self):
        return json.loads(_PKG.read_text(encoding="utf-8-sig"))["hotels"]

    def test_drury_keeps_its_combined_weight_distinct_from_a_per_pet_one(self):
        """Three Drury records are published and they are NOT all alike, which
        is the point. Dublin and Polaris say "combined weight of 80 pounds";
        Grove City says "Pets may not exceed 80 lb", a per-pet ceiling.

        PTF-POLICY-SCHEMA-MIGRATION-001 changed HOW they are told apart, not
        whether. All three previously depended on a scan of the evidence text
        at render time, because the legacy record put 80 pounds in the same
        field either way. 1.2 gives the combined limit its own field, so the
        distinction is now structural -- and this test checks BOTH the
        structure and the sentence a reader gets.
        """
        from scripts.pettripfinder import canonical_view
        drury = {h["key"]: h for h in self._pkg() if h["key"].startswith("drury inn")}
        assert len(drury) == 3
        combined = {"drury inn and suites columbus dublin",
                    "drury inn and suites columbus polaris"}
        for key, h in drury.items():
            f = h.get("facts") or {}
            shown = canonical_view.display_facts(h)
            summary = _verified_summary(shown, evidence=h.get("evidence_quote", ""))
            if key in combined:
                assert f["combined_weight_limit"]["value"] == 80, key
                assert "weight_limit" not in f, key
                assert "combined weight limit" in summary, key
            else:
                assert f["weight_limit"]["scope"] == "per_pet", key
                assert "combined_weight_limit" not in f, key
                assert "combined weight limit" not in summary, key

    def test_the_combined_verdict_no_longer_depends_on_a_text_scan(self):
        """The four records the scan used to identify are now identified by
        STRUCTURE, and nothing is left for the scan to decide.

        This test used to pin the scan's verdict on the live corpus, because
        the legacy record put a combined weight and a per-pet weight in the
        same field and only the evidence text told them apart. That was always
        a fallback -- it has a documented false positive, pinned above.
        PTF-POLICY-SCHEMA-MIGRATION-001 gave the fact its own field, so the
        four records now say what they are, and no published record needs the
        scan at all. The scan itself is kept, and kept tested, for records
        arriving from a source that has not been canonicalised yet.
        """
        from scripts.pettripfinder import canonical_view
        expected_combined = {"drury inn and suites columbus dublin",
                             "drury inn and suites columbus polaris",
                             "candlewood suites columbus grove city",
                             "drury plaza hotel columbus downtown"}
        structural = {h["key"] for h in self._pkg()
                      if (h.get("facts") or {}).get("combined_weight_limit")}
        assert expected_combined <= structural

        # Nothing published still relies on the fallback: every record that
        # states a combined limit says so in its structure, and no record whose
        # DISPLAY weight is a per-pet ceiling is caught by the scan.
        for record in self._pkg():
            shown = canonical_view.display_facts(record)
            if not shown.get("weight_limit"):
                continue
            assert not _source_states_combined_weight(
                record.get("evidence_quote", ""), shown["weight_limit"]),                 record["key"]

    def test_every_published_record_still_renders(self):
        for h in self._pkg():
            f = h.get("facts") or {}
            from scripts.pettripfinder import canonical_view
            _verified_summary(canonical_view.display_facts(h),
                              evidence=h.get("evidence_quote", ""))
            _verified_details(canonical_view.display_facts(h))


class TestPerPetScheduleReachesTheTable:
    """PTF-COLUMBUS-FINAL-CLOSURE-001.

    fee_pet_schedule reached the summary sentence and never the detail table, so
    Hilton Columbus Polaris published "Pet charge: Not stated by the reviewed
    source" directly beneath a sentence saying the first pet costs $80. One live
    page is corrected by this; two Red Roof promotions avoid inheriting it.
    """

    def _labels(self, f):
        rows, _, _ = _verified_details(f)
        return {r[0]: r[1] for r in rows}

    def _schedule(self, **kw):
        base = {"pets_allowed": "true", "fee_pet_schedule": {
            "first_pet": {"amount": "80.00", "basis": "per stay", "currency": "USD"},
            "second_pet": {"amount": "50.00", "basis": "per stay", "currency": "USD"}}}
        base.update(kw)
        return base

    def test_both_pet_rows_render(self):
        cells = self._labels(self._schedule())
        assert cells["Pet charge, first pet"] == "$80 per stay"
        assert cells["Pet charge, second pet"] == "$50 per stay"

    def test_the_misleading_not_stated_row_is_gone(self):
        assert "Pet charge" not in self._labels(self._schedule())

    def test_a_first_pet_that_is_free_still_renders(self):
        f = self._schedule(fee_pet_schedule={
            "first_pet": {"amount": "0.00", "basis": "per stay", "currency": "USD"},
            "second_pet": {"amount": "15.00", "basis": "per night", "currency": "USD"}})
        cells = self._labels(f)
        assert cells["Pet charge, first pet"] == "$0 per stay"
        assert cells["Pet charge, second pet"] == "$15 per night"

    def test_a_staged_schedule_still_wins(self):
        """Precedence is unchanged: exactly one account of the money speaks."""
        f = self._schedule(fee_schedule={
            "first_night": {"amount": "45.00", "basis": "first night", "currency": "USD"},
            "additional_night": {"amount": "10.00", "basis": "each additional night",
                                 "currency": "USD"}})
        cells = self._labels(f)
        assert "Pet charge, first night" in cells
        assert "Pet charge, first pet" not in cells

    def test_records_without_the_field_are_untouched(self):
        cells = self._labels({"pets_allowed": "true", "pet_fee": "$50.00"})
        assert cells["Pet charge"] == "$50.00"
        assert "Pet charge, first pet" not in cells
