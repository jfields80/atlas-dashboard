"""PTF-CHOICE-READER-AND-ROUTE-CLOSURE-005 -- a refusal may not carry pet terms.

PTF-FIRECRAWL-CHOICE-VALIDATION-004 published a record that said, at once, that
the property did not allow pets and that pets were capped at 40 lb with a limit
of one per room. Both statements cannot be true, and the reader emitted them
together without noticing.

Every wording in this file is VERBATIM from a persisted Milwaukee capture. That
matters more than usual here: a test written from a paraphrase of the defect
proves the paraphrase parses, not that the defect is fixed.

Two faults share this shape and they need different answers
------------------------------------------------------------
A limit written INSIDE the service-animal statement is a limit on service
animals. Republishing it as a pet limit would invent a pet policy for a property
that has none, so the term is dropped and the refusal stands.

A limit written OUTSIDE it, alongside a refusal, means the SOURCE contradicts
itself. Neither side is taken, and the record is classified
SOURCE_CONTRADICTORY rather than tidied into whichever half looks more
plausible.

The boundary between them is a real edge, not a hypothetical one: Choice writes
"... Max 65 Pounds Service animals are permitted, without charge." with no full
stop before "Service", so a naive containment test swallows a genuine pet weight
limit stated ahead of the phrase. Brown Deer is in here to hold that line.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.pettripfinder.brightdata import policy_reading as PR

REPO_ROOT = Path(__file__).resolve().parents[2]
REPORTS = REPO_ROOT / "launch_packages" / "pettripfinder" / "markets" / "reports"
REDERIVE_REPORT = REPORTS / "ptf_choice_reader_rederive_005.json"

# --------------------------------------------------------------------------- #
# Verbatim source wordings. Do not paraphrase these.
# --------------------------------------------------------------------------- #

#: Country Inn & Suites by Radisson, Milwaukee Airport -- the defect itself.
DEFECT_BLOCK = ("Pets Allowed: No, only Service animals are permitted. Pet "
                "limit 1 Pet Per Room with Max 40 Pounds for stays 1-3 night "
                "only.")

#: Econo Lodge and Rodeway Inn Milwaukee Airport -- an ordinary clean refusal.
CLEAN_REFUSAL = ("Pets Allowed: No General: Only service animals are "
                 "permitted, free of charge.")

#: Country Inn & Suites by Radisson, Brown Deer -- the no-full-stop edge.
BROWN_DEER = ("Pets Allowed. Pet Charge 30.00 USD Per Pet, Per Night. Pet "
              "limit 2 Pet Per Room. Max 65 Pounds Service animals are "
              "permitted, without charge.")

#: Country Inn & Suites by Radisson, Milwaukee West (Brookfield).
BROOKFIELD = ("Pets Allowed. Non-refundable Pet Charge 100.00 USD Per Stay. "
              "Pet limit 2 Pet Per Room 50 lbs maximum. Service animals are "
              "permitted, without charge.")

#: Royle Hotel Milwaukee Airport.
ROYLE = ("Pets Allowed. Pet Charge 50.00 USD Per Pet, Per Stay. Pet limit 1 "
         "Pet Per Room. Max 100 Pounds Service animals are permitted, without "
         "charge.")

#: The mis-attribution case: the numbers belong to the service animals.
SERVICE_ANIMAL_LIMITS = ("Pets Allowed: No. Only service animals are "
                         "permitted, maximum 2 per room, up to 50 lbs.")

ORDINARY_PET_FIELDS = ("weight_limit", "pet_count_limit", "pet_fee",
                       "species_allowed")


def _extraction(block: str) -> dict:
    reading = PR.parse(block, strategy="static_html_walk")
    return dict(PR.to_extraction(reading, location="").extraction)


class TestTheInvariant:
    """A record may not refuse pets and state ordinary-pet terms at once."""

    @pytest.mark.parametrize("block", [
        DEFECT_BLOCK, CLEAN_REFUSAL, BROWN_DEER, BROOKFIELD, ROYLE,
        SERVICE_ANIMAL_LIMITS,
    ])
    def test_no_block_emits_a_refusal_together_with_pet_terms(self, block):
        extraction = _extraction(block)
        if extraction.get("pets_allowed") is not False:
            return
        offending = [f for f in ORDINARY_PET_FIELDS if f in extraction]
        assert not offending, (
            "refusal emitted with ordinary-pet terms %s from %r"
            % (offending, block))

    def test_the_defect_block_is_classified_source_contradictory(self):
        reading = PR.parse(DEFECT_BLOCK, strategy="static_html_walk")
        reasons = [c["withholding_reason"] for c in reading.contradictions
                   if c.get("field") == "pets_allowed"]
        assert "SOURCE_CONTRADICTORY" in reasons

    def test_the_defect_block_takes_neither_side(self):
        """Not repaired into a clean refusal and not into a clean allowance.
        The page says both; publishing either would be choosing for it."""
        extraction = _extraction(DEFECT_BLOCK)
        assert "pets_allowed" not in extraction
        for field in ORDINARY_PET_FIELDS:
            assert field not in extraction, field

    def test_the_contradiction_carries_both_sides_verbatim(self):
        """A contradiction asserted without the words that make it one is an
        opinion about a page."""
        reading = PR.parse(DEFECT_BLOCK, strategy="static_html_walk")
        contradiction = next(c for c in reading.contradictions
                             if c.get("field") == "pets_allowed")
        assert contradiction["quotes"]
        for quote in contradiction["quotes"]:
            assert quote in DEFECT_BLOCK
        assert set(contradiction["contradicted_fields"]) == {
            "pet_count_limit", "weight_limit"}


class TestServiceAnimalLimitsNeverBecomePetLimits:
    def test_a_limit_inside_the_service_animal_statement_is_dropped(self):
        extraction = _extraction(SERVICE_ANIMAL_LIMITS)
        assert "weight_limit" not in extraction
        assert "pet_count_limit" not in extraction

    def test_and_the_refusal_still_stands(self):
        """This is a mis-attribution, not a contradiction: the source said one
        coherent thing. The property genuinely refuses pets and that fact must
        survive, or a no-pets hotel silently loses its policy."""
        extraction = _extraction(SERVICE_ANIMAL_LIMITS)
        assert extraction["pets_allowed"] is False
        reading = PR.parse(SERVICE_ANIMAL_LIMITS, strategy="static_html_walk")
        assert not [c for c in reading.contradictions
                    if c.get("field") == "pets_allowed"]


class TestTheCleanCasesAreUntouched:
    def test_a_plain_refusal_is_still_a_refusal(self):
        assert _extraction(CLEAN_REFUSAL)["pets_allowed"] is False

    @pytest.mark.parametrize("block,weight,count", [
        (BROWN_DEER, 65.0, 2),
        (BROOKFIELD, 50.0, 2),
        (ROYLE, 100.0, 1),
    ])
    def test_an_acceptance_keeps_its_pet_terms(self, block, weight, count):
        """Choice runs the pet weight straight into the service-animal
        sentence with no full stop. A containment test that starts at the
        segment rather than the phrase deletes a real pet weight limit."""
        extraction = _extraction(block)
        assert extraction["pets_allowed"] is True
        assert extraction["weight_limit"]["value"] == weight
        assert extraction["pet_count_limit"] == count


class TestTheHeldRecordWasReDerivedOffline:
    def _doc(self):
        if not REDERIVE_REPORT.is_file():
            pytest.skip("re-derivation not run in this worktree")
        return json.loads(REDERIVE_REPORT.read_text(encoding="utf-8-sig"))

    def test_no_credit_was_spent_to_re_read_a_page_already_on_disk(self):
        doc = self._doc()
        assert doc["network_requests"] == 0
        assert doc["firecrawl_credits_spent"] == 0

    def test_the_held_record_now_resolves_to_source_contradictory(self):
        held = self._doc()["held_record"]
        assert held["state_class"] == "SOURCE_CONTRADICTORY"
        assert held["block_text"] == DEFECT_BLOCK

    def test_the_source_verdict_refuses_to_repair_the_page(self):
        held = self._doc()["held_record"]
        assert "SOURCE_CONTRADICTORY" in held["source_verdict"]
        assert "neither" in held["source_verdict"].lower()

    def test_the_wider_page_contradiction_is_quoted_not_summarised(self):
        """The bounded block is not the only place the page disagrees with
        itself, and the page's own words are what make the verdict checkable."""
        evidence = self._doc()["held_record"]["wider_page_evidence"]
        assert evidence["states_pet_terms"]
        assert evidence["states_refusal"]

    def test_exactly_one_choice_record_changed(self):
        """A reader change that moves eleven other records is not a narrow
        correction, whatever its diff looks like."""
        doc = self._doc()
        contradictory = [r for r in doc["rederived"]
                         if r["state_class"] == "SOURCE_CONTRADICTORY"]
        assert len(contradictory) == 1
