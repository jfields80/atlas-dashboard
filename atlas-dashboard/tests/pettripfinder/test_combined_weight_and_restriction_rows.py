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

    def test_drury_keeps_its_text_derived_combined_weight(self):
        """Three Drury records are published and they are NOT all alike, which
        is the point. Dublin and Polaris say "combined weight of 80 pounds";
        Grove City says "Pets may not exceed 80 lb", a per-pet ceiling. None
        carries a structured operator, so all three depend on the text scan --
        and it must keep telling them apart."""
        drury = {h["key"]: h for h in self._pkg() if h["key"].startswith("drury inn")}
        assert len(drury) == 3
        combined = {"drury inn and suites columbus dublin",
                    "drury inn and suites columbus polaris"}
        for key, h in drury.items():
            f = h.get("facts") or {}
            assert not f.get("weight_limit_operator"), key
            summary = _verified_summary(f, evidence=h.get("evidence_quote", ""))
            if key in combined:
                assert "combined weight limit" in summary, key
            else:
                assert "combined weight limit" not in summary, key

    def test_no_published_record_changes_its_combined_verdict(self):
        """The broadened stem must not newly relabel any live page. Every
        record that reads combined today must read combined for the same
        reason, and no other record may join them."""
        expected_combined = {"drury inn and suites columbus dublin",
                             "drury inn and suites columbus polaris",
                             # Published by PTF-COLUMBUS-INTEGRATE-UNRESOLVED-001.
                             # Its page reads "max combine weight of 80lbs for two
                             # pets", so the broadened stem matches it too -- but
                             # its record also carries the structured operator, so
                             # the text scan is never what decides it.
                             "candlewood suites columbus grove city"}
        actual = {h["key"] for h in self._pkg()
                  if _source_states_combined_weight(
                      h.get("evidence_quote", ""),
                      (h.get("facts") or {}).get("weight_limit", ""))}
        assert actual == expected_combined

    def test_only_the_intended_records_gain_a_restriction_row(self):
        """Exactly one PRE-EXISTING page gains a row: Sonesta Columbus Downtown
        already carried general_restrictions in the committed authority and the
        render layer was dropping it. That is the single intended disclosure to
        an already-published profile.

        The other two were published by this same work order and carry these
        fields from their own captures, so they add no row to anything that was
        live before."""
        rows_added = {h["key"] for h in self._pkg()
                      if any((h.get("facts") or {}).get(k) for k in
                             ("general_restrictions", "pet_room_restriction",
                              "eligible_room_types", "reservation_requirement"))}
        assert rows_added == {"sonesta columbus downtown",
                              "candlewood suites columbus grove city",
                              "hampton inn and suites canal winchester columbus"}

    def test_every_published_record_still_renders(self):
        for h in self._pkg():
            f = h.get("facts") or {}
            _verified_summary(f, evidence=h.get("evidence_quote", ""))
            _verified_details(f)
