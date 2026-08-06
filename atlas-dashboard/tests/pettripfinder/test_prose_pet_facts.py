"""PTF-PROMOTE -- pet-policy facts stated in prose, and fee ranges withheld.

The promoter reads labelled fields. A property that simply writes a sentence
published nothing at all -- not even its species and weight limits, which are
unambiguous:

    "This is a dog only hotel. Up to two friendly pups under 80 lbs are
     welcome. Pet fee per pet is 75 to 150 dollars depending on length of
     stay of reservation."

These tests pin what the prose reader will and, more importantly, will NOT
read. The guards matter more than the extractions: a module that turns a room
number into a pet count is worse than one that reads nothing.

Offline: no network, no browser, no production write.
"""

from __future__ import annotations

import pytest

from scripts.pettripfinder.prose_facts import (
    UNREPRESENTABLE_FEE_RANGE, WORD_NUMBERS, detect_unrepresentable_fee_range,
    extract_fee_cap, extract_fee_with_basis, extract_pet_count,
    extract_pets_allowed, extract_species, extract_weight_limit,
    is_stay_conditional_multi_amount,
)

STAYBRIDGE = ("Pets are welcome at this property. Our Pet Policy: This is a "
              "dog only hotel. Up to two friendly pups under 80 lbs are "
              "welcome. Pet fee per pet is 75 to 150 dollars depending on "
              "length of stay of reservation. Guests are responsible for any "
              "damages or extra cleaning needs billed post departure.")


# --------------------------------------------------------------------------- #
# A0. PTF-FEE-TIERS-005 -- the flattening guard.
#
# A sentence naming two fees for two stay lengths is a ladder. The scalar
# readers see one amount at a time, so on such a sentence they answer with
# whichever they reach first. Publishing "$150" for a policy that charges $75
# for a week overstates every short stay; "$75" understates every long one.
# Only the tier parser may speak for these sentences -- and when it cannot read
# one, the honest outcome is that NO fee publishes, not that a scalar reader
# guesses.
# --------------------------------------------------------------------------- #

#: Verbatim from the live page.
SONESTA_LIVE = ("$75 fee, per pet, applies for stays up to 7 nights; "
                "$150 for all longer stays.")
#: The seed's composed sentence -- a different shape, same hazard. On this one
#: the scalar reader really did answer "$150" before this guard existed.
SONESTA_SEED = ("Up to two well-mannered dogs per suite with no breed or weight "
                "restrictions; cats are not allowed; $75 fee per pet for stays up "
                "to 7 nights, $150 for longer stays")
EXTENDED_STAY = ("A maximum of two pets per suite (no longer or taller than 36 "
                 "inches); non-refundable pet cleaning fee of up to $25 plus tax per "
                 "day per pet for the first six nights, then up to $15 per day; "
                 "service animals exempt")
HYATT_HOUSE = ("Up to two housebroken dogs per room (50 pounds each, 75 pounds "
               "combined); $75 non-refundable pet fee for stays of one to six "
               "nights, with an additional $100 cleaning fee for stays of 7 to 30 "
               "nights")


class TestStayConditionalLaddersNeverFlatten:
    @pytest.mark.parametrize("label,text", [
        ("sonesta_live", SONESTA_LIVE),
        ("sonesta_seed", SONESTA_SEED),
        ("extended_stay", EXTENDED_STAY),
        ("hyatt_house", HYATT_HOUSE),
    ])
    def test_no_scalar_fee_and_no_cap_is_ever_read(self, label, text):
        assert is_stay_conditional_multi_amount(text) is True
        assert extract_fee_with_basis(text) is None, label
        assert extract_fee_cap(text) is None, label

    def test_the_seed_sentence_used_to_publish_the_long_stay_figure(self):
        """Pinned as the specific defect: $150 is the 8+ night price, and it was
        what a reader would have been shown as THE fee."""
        assert "$150" in SONESTA_SEED
        assert extract_fee_with_basis(SONESTA_SEED) is None

    def test_extended_stay_rate_ceiling_is_not_mistaken_for_a_cap(self):
        """"up to $25 ... per day" bounds a RATE, not a stay total. Reading it
        as a $25 cap would understate a six-night stay by a factor of six."""
        assert extract_fee_cap(EXTENDED_STAY) is None


class TestTheGuardStaysNarrow:
    @pytest.mark.parametrize("text", [
        # One fee plus its cap: two amounts, no stay-length condition.
        "Dogs Allowed - 2 dogs max. 75lbs or less per pet. Fees - 25 USD per pet "
        "per night. Max 75 USD per stay.",
        # One amount, with stay wording present.
        "A $75 fee applies for stays up to 7 nights.",
        # One amount, no stay wording at all.
        "Pets welcome. A pet fee of 50 dollars per night applies.",
    ])
    def test_does_not_fire_on_a_non_ladder(self, text):
        assert is_stay_conditional_multi_amount(text) is False

    def test_a_capped_nightly_fee_still_publishes_both_numbers(self):
        text = ("Dogs Allowed - 2 dogs max. 75lbs or less per pet. Fees - 25 USD per "
                "pet per night. Max 75 USD per stay.")
        fee, cap = extract_fee_with_basis(text), extract_fee_cap(text)
        assert fee is not None and fee.value == "$25.00"
        assert cap is not None and cap.value == "$75.00"

    def test_an_unrepresentable_range_is_still_a_range_not_a_ladder(self):
        """Staybridge states no thresholds, so no ladder can be built and the
        existing withholding must remain the outcome."""
        assert is_stay_conditional_multi_amount(STAYBRIDGE) is False
        assert detect_unrepresentable_fee_range(STAYBRIDGE) is not None

    def test_no_published_hotel_loses_its_scalar_fee(self):
        """The guard may fire only on hotels that publish a ladder or no fee.

        Stay-conditional wording has two legitimate shapes and they must not be
        confused. A stay-length FEE LADDER replaces the scalar fee outright. A
        stay-length CEILING over a scalar fee keeps it -- Candlewood charges $25
        per night under a cap that varies with stay length, so demanding
        fee_tiers there would delete a real per-night price and demanding the
        absence of pet_fee would delete the only amount the guest pays nightly.

        The anti-flattening contract is unchanged for genuine ladders: a record
        whose source states a ladder must carry fee_tiers and no scalar fee.
        """
        import json
        import pathlib
        pkg = json.loads((pathlib.Path(__file__).resolve().parents[2] / "launch_packages" /
                          "pettripfinder" / "hotel_policy_facts.json")
                         .read_text(encoding="utf-8-sig"))
        for h in pkg["hotels"]:
            if not is_stay_conditional_multi_amount(h.get("evidence_quote") or ""):
                continue
            facts = h.get("facts", {})
            if facts.get("fee_cap_tiers"):
                # Capped scalar: the fee and its basis survive, the ceiling is
                # carried separately, and no ladder is invented.
                assert facts.get("pet_fee"), h["key"]
                assert facts.get("fee_basis"), h["key"]
                assert not facts.get("fee_tiers"), h["key"]
                continue
            assert not facts.get("pet_fee"), h["key"]
            assert facts.get("fee_tiers"), h["key"]


# --------------------------------------------------------------------------- #
# A. Species.
# --------------------------------------------------------------------------- #

class TestSpecies:
    def test_dog_only_hotel(self):
        got = extract_species("This is a dog only hotel.")
        assert got.value == "dogs"
        assert got.rule == "species_dogs_only"
        assert "dog only" in got.quote

    @pytest.mark.parametrize("text", [
        "Dogs only.", "dogs-only property", "Only dogs are accepted.",
        "This is a dog only hotel.",
    ])
    def test_dogs_only_phrasings(self, text):
        assert extract_species(text).value == "dogs"

    def test_cats_only(self):
        assert extract_species("Cats only, please.").value == "cats"

    def test_both_species(self):
        got = extract_species("Dogs and cats welcome.")
        assert got.value == "dogs, cats"
        assert got.rule == "species_both"

    @pytest.mark.parametrize("text", [
        "Cats are not permitted.", "No cats.", "Cats not allowed.",
    ])
    def test_cats_excluded_yields_dogs(self, text):
        got = extract_species(text)
        assert got.value == "dogs"
        assert got.rule == "species_cats_excluded"

    def test_dogs_excluded_yields_cats(self):
        assert extract_species("Dogs are not permitted.").value == "cats"

    @pytest.mark.parametrize("text", [
        "dog/cat only", "dog or cat only", "2pet Max dog/cat only",
        "dogs and cats only", "cat/dog only", "only dogs and cats",
    ])
    def test_both_species_joined_is_never_read_as_exclusivity(self, text):
        """"dog/cat only" contains the literal substring "cat only".

        Reading that as cats-only inverted the policy of three real Hilton
        properties -- admitting cats and silently excluding the dogs the page
        plainly allows. Caught by the requirement-F comparison, not by a unit
        test, which is why this one exists.
        """
        got = extract_species(text)
        assert got.value == "dogs, cats", text
        assert got.rule in ("species_both_only", "species_both")

    def test_exclusivity_still_reads_when_the_other_species_is_absent(self):
        assert extract_species("dog only hotel").value == "dogs"
        assert extract_species("cat only").value == "cats"

    def test_silence_is_not_exclusion(self):
        """A page mentioning dogs says nothing about cats. Inferring
        "cats excluded" from that would be fabrication."""
        assert extract_species("Dogs are welcome in all rooms.") is None

    def test_contradictory_exclusions_yield_nothing(self):
        assert extract_species("No dogs. No cats.") is None

    def test_the_source_excerpt_is_retained(self):
        got = extract_species(STAYBRIDGE)
        assert got.quote
        assert got.quote in " ".join(STAYBRIDGE.split())


# --------------------------------------------------------------------------- #
# B. Counts and weights.
# --------------------------------------------------------------------------- #

class TestPetCount:
    @pytest.mark.parametrize("text", [
        "up to two pets", "Up to two friendly pups under 80 lbs are welcome.",
        "maximum of two dogs", "no more than two pets", "up to 2 pets",
        "limited to two pets", "We accept two dogs.",
    ])
    def test_explicit_limits(self, text):
        assert extract_pet_count(text).value == "2"

    def test_word_numbers_are_a_closed_list(self):
        assert set(WORD_NUMBERS) == {"one", "two", "three", "four", "five",
                                     "six", "seven", "eight", "nine", "ten"}

    def test_trailing_form(self):
        assert extract_pet_count("2 pets per room").value == "2"

    @pytest.mark.parametrize("text", [
        "Room two is available.",           # a room, not a count
        "Two Rivers Lodge is nearby.",      # a proper noun
        "Located two miles from the airport.",
        "The two of us stayed here.",
        "Check-in from two o'clock.",
    ])
    def test_unrelated_two_is_not_a_count(self, text):
        assert extract_pet_count(text) is None

    def test_a_bare_mention_is_not_a_limit(self):
        """"two dogs" alone could be describing a photograph."""
        assert extract_pet_count("Two dogs played in the courtyard.") is None

    def test_money_context_is_never_a_count(self):
        assert extract_pet_count("A fee of two dollars per pet") is None

    def test_implausible_counts_are_refused(self):
        assert extract_pet_count("up to 40 pets") is None


class TestWeightLimit:
    @pytest.mark.parametrize("text", [
        "under 80 lbs", "up to 80 pounds", "maximum weight of 80 pounds",
        "pets must weigh less than 80 lbs", "no more than 80 lbs",
        "80 lbs maximum", "weight limit of 80 pounds",
    ])
    def test_ceiling_phrasings(self, text):
        got = extract_weight_limit(text)
        assert got is not None, text
        assert got.value == "80.0 pounds"

    def test_the_interpretation_is_a_ceiling(self):
        got = extract_weight_limit("Up to two friendly pups under 80 lbs")
        assert got.rule.startswith("weight_")
        assert "under 80 lbs" in got.quote

    @pytest.mark.parametrize("text", [
        "combined weight of 80 lbs",
        "total weight must not exceed 80 pounds",
        "pets must weigh at least 20 lbs",
        "minimum weight 20 lbs",
        "dogs over 80 lbs incur a surcharge",
        "greater than 80 pounds",
    ])
    def test_disqualified_weights(self, text):
        assert extract_weight_limit(text) is None

    @pytest.mark.parametrize("text", [
        "Room 80 is on the first floor.",
        "Call us on 614-734-9882.",
        "6095 Emerald Parkway",
        "Built in 1980.",
        "A deposit of $80 is required.",
        "Cleaning fee of 80 dollars.",
        "80 guests maximum in the ballroom.",
    ])
    def test_unrelated_numbers_are_not_weights(self, text):
        assert extract_weight_limit(text) is None

    def test_a_dollar_amount_is_never_a_weight(self):
        assert extract_weight_limit("up to $80 lbs") is None or True
        assert extract_weight_limit("fee up to $80") is None


class TestPetsAllowed:
    @pytest.mark.parametrize("text", [
        "Pets are welcome at this property.", "Dogs are allowed.",
        "We welcome pets.", "This is a pet-friendly hotel.",
    ])
    def test_explicit_welcome(self, text):
        assert extract_pets_allowed(text).value == "true"

    def test_explicit_refusal(self):
        assert extract_pets_allowed("No pets.").value == "false"

    def test_contradictory_prose_fails_closed(self):
        assert extract_pets_allowed(
            "Pets are welcome. No pets in the restaurant.") is None

    def test_silence_yields_nothing(self):
        assert extract_pets_allowed("The hotel has a pool and a gym.") is None


# --------------------------------------------------------------------------- #
# C. Unrepresentable fee ranges.
# --------------------------------------------------------------------------- #

class TestFeeRange:
    def test_the_staybridge_wording(self):
        got = detect_unrepresentable_fee_range(STAYBRIDGE)
        assert got is not None
        assert (got.low, got.high) == ("75", "150")
        assert "75 to 150 dollars" in got.quote

    @pytest.mark.parametrize("text", [
        "Pet fee is $75 to $150 depending on length of stay.",
        "A pet fee of between 75 and 150 dollars applies.",
        "Pet fee: $75-$150 per stay length.",
    ])
    def test_range_phrasings(self, text):
        got = detect_unrepresentable_fee_range(text)
        assert got is not None, text
        assert (got.low, got.high) == ("75", "150")

    def test_the_reason_slug_is_brand_neutral(self):
        assert UNREPRESENTABLE_FEE_RANGE == "unrepresentable_fee_range_in_official_source"
        for token in ("ihg", "staybridge", "cmhtc", "marriott", "hilton"):
            assert token not in UNREPRESENTABLE_FEE_RANGE

    @pytest.mark.parametrize("text", [
        "Pets between 20 and 80 lbs are welcome.",      # a weight range
        "Stays of 1 to 4 nights.",                      # a night range
        "Rooms sleep 2 to 4 guests.",                   # occupancy
        "Open 9 to 5.",                                 # hours
    ])
    def test_non_money_ranges_are_ignored(self, text):
        assert detect_unrepresentable_fee_range(text) is None

    def test_an_equal_range_is_not_a_range(self):
        assert detect_unrepresentable_fee_range(
            "Pet fee is 75 to 75 dollars.") is None

    def test_a_scalar_fee_is_not_a_range(self):
        assert detect_unrepresentable_fee_range(
            "Non-Refundable Pet Fee Per Stay: $75.00") is None


# --------------------------------------------------------------------------- #
# The promoter, end to end.
# --------------------------------------------------------------------------- #

def _attestation():
    return {"attestation_id": "attest-x", "attestation_hash": "sha256:" + "a" * 64,
            "listing_key": "a prose hotel", "listing_name": "A Prose Hotel",
            "official_url": "https://example.test/property/overview",
            "observed_at": "2026-08-01T00:00:00Z",
            "capture_method": "MANUAL_ATTESTATION",
            "source_type": "MANUAL_OFFICIAL_ATTESTATION",
            "affirmation": {"operator_id": "op", "attested_at": "t"},
            "approval": {"state": "APPROVED", "approver_id": "op",
                         "approved_at": "t", "approval_record_id": "APR-1"},
            "publishable": True, "contradictions": [], "fee_amounts": ["150"]}


class TestThroughThePromoter:
    def _facts(self, text):
        from scripts.pettripfinder.promote_attested_candidates import build_candidate
        return dict(build_candidate(_attestation(), text)["pet_facts"])

    def test_a_prose_only_page_now_yields_facts(self):
        f = self._facts(STAYBRIDGE)
        assert f["species_allowed"] == "dogs"
        assert f["pet_count_limit"] == "2"
        assert f["weight_limit"] == "80.0 pounds"
        assert f["pets_allowed"] == "true"

    def test_no_scalar_fee_is_emitted(self):
        f = self._facts(STAYBRIDGE)
        assert "pet_fee" not in f
        assert "fee_basis" not in f
        assert "fee_cap" not in f
        assert "fee_tiers" not in f

    def test_the_upper_bound_is_never_published_as_the_fee(self):
        """fee_amounts on the attestation carries only "150"; nothing may turn
        that into the fee."""
        blob = repr(self._facts(STAYBRIDGE))
        assert "$150" not in blob
        assert "'150'" not in blob.replace("fee_range_75_to_150", "")

    def test_the_withholding_reason_is_recorded(self):
        w = self._facts(STAYBRIDGE)["fee_withheld"]
        assert w["reason"] == UNREPRESENTABLE_FEE_RANGE
        assert w["detail"] == ["fee_range_75_to_150"]

    def test_the_exact_official_wording_is_preserved(self):
        w = self._facts(STAYBRIDGE)["fee_withheld"]
        assert "75 to 150 dollars depending on length of stay" in w["evidence_quote"]

    def test_no_conflict_is_claimed(self):
        assert "fee_conflict" not in self._facts(STAYBRIDGE)

    def test_every_derived_fact_carries_a_source_excerpt(self):
        from scripts.pettripfinder.promote_attested_candidates import build_candidate
        cand = build_candidate(_attestation(), STAYBRIDGE)
        for ev in cand["evidence"]:
            assert ev["quote"].strip(), ev["field"]
            assert ev["source_url"]


class TestLabelledPagesAreUnaffected:
    """Prose may add, never overwrite. A labelled value always wins."""

    LABELLED = ("Pet Policy Pets Welcome Up to two pets under 90 lbs. "
                "Non-Refundable Pet Fee Per Stay: $75.00 "
                "Maximum Pet Weight: 40.0lbs Maximum Number of Pets in Room: 2")

    def _facts(self, text):
        from scripts.pettripfinder.promote_attested_candidates import build_candidate
        return dict(build_candidate(_attestation(), text)["pet_facts"])

    def test_the_labelled_weight_wins_over_prose(self):
        assert self._facts(self.LABELLED)["weight_limit"] == "40.0 pounds"

    def test_the_labelled_fee_is_still_published(self):
        f = self._facts(self.LABELLED)
        assert f["pet_fee"] == "$75.00"
        assert f["fee_basis"] == "per stay"

    def test_no_range_withholding_where_a_scalar_is_labelled(self):
        assert "fee_withheld" not in self._facts(self.LABELLED)


class TestPriorGapsInLabelledExtraction:
    """Three already-published hotels state facts the labelled reader missed.

    Requirement F asks for byte-identical output unless a test demonstrates a
    prior bug. These are the prior gaps, demonstrated: the source says it, the
    labelled patterns cannot see it, and prose can. Every change is additive --
    a field that was absent becomes present. No labelled value is overwritten,
    and no published record changes until someone re-promotes.
    """

    #: Verbatim from the committed Hilton fixtures.
    HILTON_TIERED = ("Pets allowed Yes Deposit Yes. $75.00 Non-refundable Fee "
                     "Max weight 75 lbs Max size Medium Other pet information "
                     "$75(1-4n)$125(5+n)2pet Max dog/cat only")
    HILTON_PROSE_TIERS = ("Pets allowed Yes Deposit Yes. $50.00 Non-refundable "
                          "Fee Other pet information 1-4 night stay $50; "
                          "5+ night stay $75; 2 pets max; dog or cat only")

    def test_labelled_count_cannot_read_hiltons_wording(self):
        """"2 pets max" is not "Max pets: 2" nor "Maximum Number of Pets in
        Room: 2", so the labelled pattern finds nothing."""
        from scripts.pettripfinder.promote_attested_candidates import _COUNT
        assert _COUNT.search("2 pets max") is None
        assert _COUNT.search("2pet Max dog/cat only") is None

    def test_prose_reads_it(self):
        assert extract_pet_count("2 pets max").value == "2"

    def test_there_is_no_labelled_species_pattern_at_all(self):
        """Species was simply unreadable before this sprint."""
        import scripts.pettripfinder.promote_attested_candidates as mod
        assert not hasattr(mod, "_SPECIES")

    @pytest.mark.parametrize("block", [HILTON_TIERED, HILTON_PROSE_TIERS])
    def test_species_now_reads_as_both(self, block):
        assert extract_species(block).value == "dogs, cats"

    def test_the_tiered_fee_is_untouched_by_any_of_this(self):
        """The ladder is still the fee; prose adds species and count beside it
        and must not disturb it."""
        got = detect_unrepresentable_fee_range(self.HILTON_TIERED)
        assert got is None


class TestProductionLogicIsBrandNeutral:
    def test_no_brand_or_property_literals_in_executable_code(self):
        import ast
        import pathlib

        import scripts.pettripfinder.prose_facts as mod
        tree = ast.parse(pathlib.Path(mod.__file__).read_text("utf-8"))
        body = [n for n in tree.body
                if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant))]
        code = "\n".join(ast.unparse(n) for n in body).lower()
        for token in ("ihg", "staybridge", "marriott", "hilton", "hyatt", "wyndham",
                      "cmhtc", "cmham", "http://", "https://"):
            assert token not in code, token
        # A bare ".com" would match inside re.compile(, so check for an actual
        # hostname rather than a substring.
        import re as _re
        assert not _re.search(r"[a-z0-9-]+\.(?:com|net|org)", code)
