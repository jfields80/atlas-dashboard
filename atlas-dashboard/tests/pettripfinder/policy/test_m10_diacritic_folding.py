"""PTF-COLUMBUS-SELECTOR-CLOSEOUT-001 -- M10 and the accented hotel name.

Marriott serves "Le Méridien Columbus, The Joseph". The record says "Le
Meridien Columbus, The Joseph". Those are the same hotel to any reader, and the
capture-time identity gate agreed: it CONFIRMED on property code ``cmhdm`` plus
the street address before the observation was ever built.

M10 rejected it anyway, and the reason is worth keeping in front of whoever
reads this next. ``_tokens`` split on ``[^a-z0-9]+``, so the accented character
was not folded, it was treated as a SEPARATOR: "méridien" arrived as the two
tokens "m" and "ridien". The page's token set was then neither a subset nor a
superset of the record's, and the conjunctive code-plus-address override could
not save it either, because the record's "620 N High St" and the page's "620
North High Street" normalise to different street identities.

So the fix is at the root: fold combining marks before tokenising.

The direction matters. Folding can only equate names differing by a diacritic.
What it REMOVES is the genuine hazard -- a bare "m" is a one-character token
free to turn up inside unrelated hotels' names, and the subset test is exactly
where a loose fragment does damage. The rejection tests below are the ones that
have to hold.
"""

from __future__ import annotations

import pytest

from scripts.pettripfinder.policy.policy_membrane import (
    REJECT_WRONG_PROPERTY, VALID, _tokens, evaluate,
)

PAGE_NAME = "Le Méridien Columbus, The Joseph"
RECORD_NAME = "Le Meridien Columbus, The Joseph"
URL = "https://www.marriott.com/en-us/hotels/cmhdm-le-meridien-columbus-the-joseph/overview/"


def observation(*, page_name=PAGE_NAME, canonical=RECORD_NAME,
                normalized="le meridien columbus the joseph",
                page_code="cmhdm", ref_code="cmhdm",
                ref_street="620 N High St", page_street="620 North High Street"):
    return {
        "obs_id": "m10-diacritic-test", "contract_version": "1.0.0",
        "hotel_ref": {"market_id": "columbus-oh", "canonical_name": canonical,
                      "normalized_name": normalized, "official_url": URL,
                      "property_code": ref_code, "street_identity": ref_street},
        "identity_check": {"name_on_page": page_name, "property_code": page_code,
                           "address_on_page": page_street},
        "source_url": URL, "source_type": "official_property_page",
        "authority_tier": "PT1", "observed_at": "2026-08-09",
        "retrieved_at": "2026-08-09", "capture_method": "browser_assisted",
        "evidence": [{"quote": "Pets Welcome.", "location": "Pet Policy block",
                      "field_refs": ["pets_allowed"]}],
        "extraction": {"pets_allowed": True},
        "extraction_confidence": "EXACT_QUOTE", "flags": [],
    }


class TestTheDefect:

    def test_an_accent_used_to_shatter_the_word_into_fragments(self):
        """Not a subtle mismatch -- a one-character token and a stem."""
        assert _tokens(PAGE_NAME) != {"le", "m", "ridien", "columbus", "the", "joseph"}

    def test_the_two_spellings_now_tokenise_identically(self):
        assert _tokens(PAGE_NAME) == _tokens(RECORD_NAME)
        assert "meridien" in _tokens(PAGE_NAME)
        assert "m" not in _tokens(PAGE_NAME)

    def test_the_real_observation_is_accepted(self):
        v = evaluate(observation())
        assert v.verdict == VALID, v.detail

    def test_it_is_the_folding_and_not_the_override_doing_the_work(self):
        """The record's abbreviated street and the page's spelled-out one do
        NOT normalise together, so the code-plus-address escape was never
        available here."""
        assert evaluate(observation(page_name="Something Else Entirely")
                        ).verdict == REJECT_WRONG_PROPERTY


class TestFoldingIsGeneralAndNotHotelSpecific:

    @pytest.mark.parametrize("accented,plain", [
        ("Le Méridien", "Le Meridien"),
        ("Hôtel Café", "Hotel Cafe"),
        ("Hyatt Regency Zürich", "Hyatt Regency Zurich"),
        ("Renäissance", "Renaissance"),
    ])
    def test_accented_and_plain_spellings_agree(self, accented, plain):
        assert _tokens(accented) == _tokens(plain)

    def test_the_ampersand_rule_still_applies(self):
        assert _tokens("Bed & Breakfast") == _tokens("Bed and Breakfast")


class TestADifferentHotelIsStillADifferentHotel:
    """Folding must not have bought the match by widening the rule."""

    def test_a_genuinely_different_name_is_rejected(self):
        v = evaluate(observation(page_name="Hilton Columbus Downtown",
                                 page_code="", ref_code=""))
        assert v.verdict == REJECT_WRONG_PROPERTY
        assert v.rule == "M10"

    def test_a_sibling_marriott_downtown_is_rejected(self):
        assert evaluate(observation(page_name="Courtyard Columbus Downtown",
                                    page_code="cmhcd", ref_code="cmhdm")
                        ).verdict == REJECT_WRONG_PROPERTY

    def test_an_accent_cannot_manufacture_a_match_that_was_not_there(self):
        """"Le Méridien" folded is "le meridien" -- never "le sheraton"."""
        assert _tokens("Le Méridien Columbus") != _tokens("Le Sheraton Columbus")

    def test_folding_never_grows_the_token_set(self):
        """A fold merges characters; it cannot invent a token. Anything the
        folded set contains, the accented spelling contained a form of."""
        assert len(_tokens(PAGE_NAME)) <= len(
            {"le", "m", "ridien", "columbus", "the", "joseph"})
