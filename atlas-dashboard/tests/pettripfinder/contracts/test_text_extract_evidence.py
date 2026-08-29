"""PTF-DETROIT-ANN-ARBOR-EVIDENCE-VOCABULARY-AND-PROMOTION-004 -- founder
decision B-003-1: a persisted, byte-verifiable text extract may publish.

What was decided, and what was NOT
----------------------------------
Detroit Capture Pass 3 needed publication-grade evidence for 28 properties
while the browser screenshot subsystem was broken. It took the policy-bearing
TEXT of each first-party page, hashed it in the browser at capture time,
persisted it, and cross-verified that hash against a second one computed from
the saved file. The chain of custody is arguably tighter than a screenshot's --
a screenshot has to be read by a human before anyone knows what it says, while
this artifact IS the words the quote is drawn from. But ``text_extract`` was
never a registered artifact kind, so none of it could publish.

The founder registered it under EIGHT conditions. The decision that matters is
the eighth, and these tests exist mostly to defend it:

    the text is not merely a search snippet, model summary, paraphrase, or
    manually typed note.

PROVENANCE CANNOT BE READ OFF THE BYTES. A verbatim extract of a hotel's pet
policy and a model's summary of that same policy are both text, both hash
cleanly, and both re-hash forever. Nothing in the file distinguishes them. So
the entry must DECLARE how it was captured, and only a method that put a real
client on the real page may carry publication grade.

Registering the kind must not turn "plaintext" into "evidence", and the
negative cases below are the whole point of the amendment.
"""

from __future__ import annotations

import hashlib

import pytest

from scripts.pettripfinder.contracts import enums
from scripts.pettripfinder.contracts import evidence as EV

ARTIFACT_TEXT = (
    "Pet Policy\n\nPets Welcome\n\n"
    "Non-Refundable Pet Fee Per Stay: $150.00\n\n"
    "Maximum Pet Weight: 50.0lbs"
)
GOOD_SHA = hashlib.sha256(ARTIFACT_TEXT.encode("utf-8")).hexdigest()


def entry(**kw):
    e = {
        "evidence_ref": "r1",
        "field": "pets_allowed",
        "quote": "Pets Welcome",
        "source_url": "https://www.marriott.com/en-us/hotels/dtwad-ac-hotel/overview/",
        "value": "true",
        "source_grade": enums.GRADE_PT1_FIRST_PARTY,
        "artifact_class": enums.PUBLICATION_GRADE_EVIDENCE,
        "artifact_sha256": GOOD_SHA,
        "artifact_kind": enums.ARTIFACT_TEXT_EXTRACT,
        "captured_at": "2026-08-17",
        "capture_method": "attended_browser",
    }
    e.update(kw)
    return e


def codes(e):
    return {i.code for i in EV.validate_entry(e, 0)}


# --------------------------------------------------------------------------- #
# the amendment itself
# --------------------------------------------------------------------------- #

class TestTheKindIsRegistered:

    def test_text_extract_is_an_allowed_artifact_kind(self):
        assert enums.ARTIFACT_TEXT_EXTRACT == "text_extract"
        assert enums.is_member(enums.ARTIFACT_TEXT_EXTRACT, enums.ARTIFACT_KINDS)

    def test_the_three_prior_kinds_are_untouched(self):
        """An amendment adds; it does not renumber what was already lawful."""
        for kind in ("rendered_html", "operator_screenshot", "pdf"):
            assert enums.is_member(kind, enums.ARTIFACT_KINDS)

    def test_all_eight_founder_conditions_are_recorded(self):
        assert len(enums.TEXT_EXTRACT_CONDITIONS) == 8

    def test_a_conforming_text_extract_publishes(self):
        assert EV.validate_entry(entry(), 0) == ()


# --------------------------------------------------------------------------- #
# the negative cases -- the reason the amendment is safe
# --------------------------------------------------------------------------- #

class TestPlaintextIsNotEvidence:
    """Each of these is text. None of them may publish."""

    def test_unpersisted_text_is_refused(self):
        """Nothing to re-hash means nothing to verify later."""
        assert "NOT_REHASHABLE" in codes(entry(artifact_sha256=""))

    def test_a_missing_hash_is_refused(self):
        e = entry()
        del e["artifact_sha256"]
        assert {"NOT_REHASHABLE", "MISSING_REQUIRED"} & codes(e)

    @pytest.mark.parametrize("bad", [
        "not-a-hash",
        "sha256:short",
        GOOD_SHA[:63],            # truncated
        GOOD_SHA.upper(),         # not the canonical lowercase form
        "md5:" + GOOD_SHA,        # a different algorithm
    ])
    def test_a_malformed_hash_is_refused(self, bad):
        assert "NOT_REHASHABLE" in codes(entry(artifact_sha256=bad))

    def test_a_hash_mismatch_is_caught_where_the_bytes_are_in_hand(self):
        """The contract sees a record, not a file, so the byte-level check
        lives with whoever holds the artifact. What a hash CANNOT catch is the
        quote never having been in the file -- that is condition 6."""
        e = entry(quote="Pets stay free")
        assert EV.validate_entry(e, 0) == ()          # the record is well formed
        blockers = EV.text_extract_publication_blockers(e, ARTIFACT_TEXT)
        assert blockers and "verbatim" in blockers[0]

    def test_a_quote_actually_in_the_artifact_passes_condition_six(self):
        assert EV.text_extract_publication_blockers(entry(), ARTIFACT_TEXT) == ()

    def test_a_stitched_quote_is_refused(self):
        """Two real fragments, far apart, presented as one quotation."""
        e = entry(quote="Pets Welcome Maximum Pet Weight: 50.0lbs")
        assert EV.text_extract_publication_blockers(e, ARTIFACT_TEXT)

    @pytest.mark.parametrize("method", [
        "manual_note",          # somebody typed what they remembered
        "operator_transcription",
        "search_snippet",       # a result page, not the page
        "serp_snippet",
        "model_summary",        # a paraphrase that reads like a quote
        "llm_extraction",
        "paraphrase",
        "third_party_copy",
    ])
    def test_a_non_page_capture_method_may_never_publish(self, method):
        """The eighth condition, and the only one the bytes cannot answer."""
        assert "NOT_PUBLICATION_CAPTURE" in codes(entry(capture_method=method))

    def test_an_undeclared_capture_method_is_refused(self):
        """Silence is not a claim of provenance."""
        e = entry()
        del e["capture_method"]
        assert "MISSING_REQUIRED" in codes(e)

    def test_a_non_first_party_source_may_not_be_passed_as_pt1(self):
        """PT3 and PT4 may propose but never publish.

        PT2_BRAND is deliberately NOT in this list: the contract has always
        counted a brand's own property page as first-party for publication
        (``FIRST_PARTY_GRADES``), and this amendment does not relitigate that.
        """
        for grade in (enums.GRADE_PT3_THIRD_PARTY, enums.GRADE_PT4_UNVERIFIED):
            assert "NOT_FIRST_PARTY" in codes(entry(source_grade=grade))

    def test_the_brand_grade_keeps_the_authority_it_already_had(self):
        assert "NOT_FIRST_PARTY" not in codes(entry(source_grade=enums.GRADE_PT2_BRAND))

    def test_an_unknown_grade_spelling_is_refused(self):
        """The exact defect this order normalises: the packet wrote the Python
        CONSTANT NAME instead of its value."""
        assert "BAD_ENUM" in codes(entry(source_grade="GRADE_PT1_FIRST_PARTY"))

    def test_a_text_extract_must_name_the_page_it_came_from(self):
        assert "MISSING_REQUIRED" in codes(entry(source_url=""))


class TestTheOtherKindsAreUnaffected:
    """The new rules apply to text extracts and to nothing else -- a screenshot
    has never had to declare a capture method to publish."""

    def test_a_screenshot_still_publishes_without_a_capture_method(self):
        e = entry(artifact_kind=enums.ARTIFACT_OPERATOR_SCREENSHOT)
        del e["capture_method"]
        assert EV.validate_entry(e, 0) == ()

    def test_a_screenshot_is_not_subjected_to_the_capture_method_whitelist(self):
        e = entry(artifact_kind=enums.ARTIFACT_OPERATOR_SCREENSHOT,
                  capture_method="operator_transcription")
        assert "NOT_PUBLICATION_CAPTURE" not in codes(e)
