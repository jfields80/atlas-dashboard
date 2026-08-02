"""PTF-PROMOTION -- the promotion boundary must not lose a fact Gate-1 proved.

A validated stay-length ladder reached Gate-1 and then vanished: the mapper
reads ``supported_facts``, the ladder lives in ``fee_policy``, and nothing
carried one into the other. ``unmapped_facts`` was empty, so the loss was not
merely unfixed -- it was invisible. A hotel whose fee we had, validated and
renderable, would have published with no fee at all.

These tests pin the mapping and, more importantly, the fail-closed completeness
check that makes such a loss impossible to repeat: every supported Gate-1 fact
must be MAPPED or explicitly ACCOUNTED FOR, and an unknown field stops the
promotion loudly.

Offline: no network, no model call, no production write.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from scripts.pettripfinder import promote_worker_candidates as PROM

_REPO = pathlib.Path(__file__).resolve().parents[2]
URL = ("https://www.sonesta.com/sonesta-simply-suites/oh/dublin/"
       "sonesta-simply-suites-dublin-columbus")


def _fact(field, value, quote, stype="OFFICIAL_PROPERTY"):
    return {"field_name": field, "value": value, "evidence_quote": quote,
            "source_url": URL, "source_type": stype}


def _tier(amount, lo, hi, scope):
    return {"amount": amount, "currency": "USD", "role": "ONE_TIME_CHARGE",
            "basis": "one_time", "scope": scope, "condition_type": "stay_length_range",
            "condition_min": lo, "condition_max": hi, "boundary_unit": "nights",
            "evidence_quote": "$75 fee, per pet, applies for stays up to 7 nights",
            "source_url": URL, "source_type": "OFFICIAL_PROPERTY"}


def _g1(facts=None, fee_policy=None, supported=True):
    return {
        "listing_key": "sonesta simply suites dublin columbus",
        "listing_name": "Sonesta Simply Suites Dublin Columbus",
        "candidate_identity": "sha256:" + "0" * 64,
        "final_route": "REVIEW",
        "reason_codes": ["MODEL_OVERCLAIM"],
        "supported_facts": facts if facts is not None else [
            _fact("pets_allowed", "true", "welcomes well-mannered pets"),
            _fact("cats_accepted", "false", "cats are not permitted."),
            _fact("maximum_pets", "2", "Up to two pets are permitted per suite."),
            _fact("breed_restrictions", "false", "with no breed or weight restrictions."),
        ],
        "source_urls": [URL],
        "fee_policy": fee_policy,
        "downstream_fee_schema_supported": supported,
        "model_id": "m", "extraction_prompt_version": "1.7.0",
        "rederivation_validator_version": "1.5.0", "rederivation_routing_version": "1.4.0",
    }


_APPROVAL = {
    "listing_key": "sonesta simply suites dublin columbus",
    "result_hash": "sha256:" + "0" * 64,
    "verification_date": "2026-08-02",
    "decision": "APPROVE_WITH_DIAGNOSTIC_ACKNOWLEDGEMENT",
    "operator": "Jonathan Fields", "approval_date": "2026-08-02",
}

SONESTA_POLICY = {"terms": [_tier("75.00", 1, 7, "per_pet"),
                            _tier("150.00", 8, None, "unstated")]}


def _build(g1):
    return PROM.build_mapping(_APPROVAL, g1, "Sonesta Simply Suites Dublin Columbus")


def _facts(candidate):
    return dict(candidate["pet_facts"])


# --------------------------------------------------------------------------- #
# 1-6. The Sonesta mapping.
# --------------------------------------------------------------------------- #

class TestFeeLadderSurvivesPromotion:
    def test_1_fee_policy_promotes_to_two_fee_tiers(self):
        cand, _t, _u, fail = _build(_g1(fee_policy=SONESTA_POLICY))
        assert fail is None and cand is not None
        tiers = _facts(cand)["fee_tiers"]
        assert [(t["amount"], t["condition_min"], t["condition_max"]) for t in tiers] == [
            ("75.00", 1, 7), ("150.00", 8, None)]

    def test_4_the_open_ended_final_tier_survives(self):
        cand, _t, _u, _f = _build(_g1(fee_policy=SONESTA_POLICY))
        tiers = _facts(cand)["fee_tiers"]
        assert tiers[-1]["condition_max"] is None
        assert all(t["condition_max"] is not None for t in tiers[:-1])

    def test_5_tier_scope_is_preserved_exactly_as_stated(self):
        cand, _t, _u, _f = _build(_g1(fee_policy=SONESTA_POLICY))
        assert [t["scope"] for t in _facts(cand)["fee_tiers"]] == ["per_pet", "unstated"]

    def test_6_no_scalar_fee_is_created(self):
        cand, _t, _u, _f = _build(_g1(fee_policy=SONESTA_POLICY))
        f = _facts(cand)
        assert "pet_fee" not in f and "fee_basis" not in f and "fee_cap" not in f

    def test_no_basis_or_cap_is_inferred(self):
        cand, _t, _u, _f = _build(_g1(fee_policy=SONESTA_POLICY))
        tiers = _facts(cand)["fee_tiers"]
        assert all(t["basis"] == "one_time" for t in tiers)
        assert all(t["basis_stated"] is False for t in tiers)

    def test_source_wording_and_provenance_travel_with_each_tier(self):
        cand, _t, _u, _f = _build(_g1(fee_policy=SONESTA_POLICY))
        for t in _facts(cand)["fee_tiers"]:
            assert t["evidence_quote"] and t["source_url"] == URL
            assert t["source_type"] == "OFFICIAL_PROPERTY"
            assert t["currency"] == "USD"

    def test_a_stated_basis_sets_basis_stated(self):
        """Derived from the term's own vocabulary, not guessed at."""
        policy = {"terms": [dict(_tier("50.00", 1, 4, "unstated"), basis="per_night"),
                            dict(_tier("75.00", 5, None, "unstated"), basis="per_night")]}
        cand, _t, _u, _f = _build(_g1(fee_policy=policy))
        assert all(t["basis_stated"] is True for t in _facts(cand)["fee_tiers"])

    def test_an_unrenderable_ladder_fails_closed(self):
        _c, _t, _u, fail = _build(_g1(fee_policy=SONESTA_POLICY, supported=False))
        assert fail == "fee_policy_not_downstream_supported"


class TestSpeciesFacts:
    def test_2_the_explicit_cats_negative_is_preserved_not_dropped(self):
        """species_allowed is a POSITIVE list and cannot say "cats excluded", so
        the negative is recorded in provenance with an explicit reason rather
        than force-fit into an unrelated field or silently lost."""
        _c, _t, unmapped, _f = _build(_g1(fee_policy=SONESTA_POLICY))
        cats = [u for u in unmapped if u["field"] == "cats_accepted"]
        assert len(cats) == 1
        assert cats[0]["value"] == "false"
        assert cats[0]["reason"] == PROM.SPECIES_NEGATIVE_REASON
        assert cats[0]["evidence_quote"] == "cats are not permitted."

    def test_3_dogs_remain_absent_and_are_never_inferred(self):
        cand, _t, _u, _f = _build(_g1(fee_policy=SONESTA_POLICY))
        f = _facts(cand)
        assert "species_allowed" not in f          # nothing positive was stated
        assert "dogs" not in json.dumps(f).lower()

    def test_an_explicitly_accepted_species_still_publishes(self):
        g1 = _g1(facts=[_fact("pets_allowed", "true", "Pets welcome"),
                        _fact("dogs_accepted", "true", "Dogs are welcome")],
                 fee_policy=None)
        cand, _t, _u, _f = _build(g1)
        assert _facts(cand)["species_allowed"] == "dogs"


# --------------------------------------------------------------------------- #
# 7. The check that makes the original loss impossible to repeat.
# --------------------------------------------------------------------------- #

class TestFailClosedCompleteness:
    def test_7_an_unknown_supported_fact_blocks_promotion_loudly(self):
        g1 = _g1(facts=[_fact("pets_allowed", "true", "Pets welcome"),
                        _fact("some_future_field", "x", "quote")])
        cand, _t, _u, fail = _build(g1)
        assert cand is None
        assert fail == "unmapped_supported_facts:some_future_field"

    def test_the_reason_names_every_unmapped_field(self):
        g1 = _g1(facts=[_fact("pets_allowed", "true", "Pets welcome"),
                        _fact("alpha_field", "x", "q"), _fact("beta_field", "y", "q")])
        _c, _t, _u, fail = _build(g1)
        assert fail == "unmapped_supported_facts:alpha_field,beta_field"

    @pytest.mark.parametrize("field", [
        "pets_allowed", "maximum_pets", "weight_limit", "breed_restrictions",
        "unattended_pet_rule", "pet_fee", "fee_basis",
        "dogs_accepted", "cats_accepted", "fee_currency", "refundable_deposit",
        "service_animal_note",
    ])
    def test_every_known_field_is_accounted_for(self, field):
        """Each is either mapped into the corpus record or explicitly recorded
        in provenance -- never merely tolerated."""
        quote = "two pets 50 lbs deposit service animals per night"
        g1 = _g1(facts=[_fact("pets_allowed", "true", "Pets welcome"),
                        _fact(field, "per_night" if field == "fee_basis" else "2", quote)])
        _c, _t, _u, fail = _build(g1)
        assert fail is None or not fail.startswith("unmapped_supported_facts")

    def test_a_present_fee_policy_can_never_be_silently_dropped(self):
        cand, _t, _u, fail = _build(_g1(fee_policy=SONESTA_POLICY))
        assert fail is None
        assert "fee_tiers" in _facts(cand)


# --------------------------------------------------------------------------- #
# 8-9. Nothing already published moved.
# --------------------------------------------------------------------------- #

class TestPublishedRecordsUnaffected:
    def _pkg(self):
        return json.loads((_REPO / "launch_packages" / "pettripfinder" /
                           "hotel_policy_facts.json").read_text(encoding="utf-8-sig"))

    #: The three ladders that were live BEFORE this sprint, with the exact
    #: values they published. Sonesta joins them; none of them may move.
    _PRE_EXISTING = {
        "hampton inn columbus airport": [("75.00", 1, 4), ("125.00", 5, None)],
        "hilton garden inn columbus airport": [("75.00", 1, 4), ("125.00", 5, None)],
        "home2 suites new albany columbus": [("50.00", 1, 4), ("75.00", 5, None)],
    }

    def test_8_the_pre_existing_published_ladders_are_unchanged(self):
        """Sonesta's arrival must not disturb a single value on the ladders that
        were already live -- amounts, bounds, scope or basis flag."""
        tiered = {h["key"]: h["facts"]["fee_tiers"]
                  for h in self._pkg()["hotels"] if h.get("facts", {}).get("fee_tiers")}
        assert set(self._PRE_EXISTING) <= set(tiered)
        for key, expected in self._PRE_EXISTING.items():
            tiers = tiered[key]
            assert [(t["amount"], t["condition_min"], t["condition_max"])
                    for t in tiers] == expected, key
            assert all(t["scope"] == "unstated" for t in tiers), key
            assert all(t["basis_stated"] is False for t in tiers), key

    def test_8b_sonesta_publishes_its_ladder_with_the_stated_scope(self):
        tiers = {h["key"]: h["facts"].get("fee_tiers")
                 for h in self._pkg()["hotels"]}["sonesta simply suites dublin columbus"]
        assert [(t["amount"], t["condition_min"], t["condition_max"], t["scope"])
                for t in tiers] == [("75.00", 1, 7, "per_pet"),
                                    ("150.00", 8, None, "unstated")]
        assert all(t["basis_stated"] is False for t in tiers)

    def test_9_the_committed_package_holds_38_records(self):
        """37 published hotels plus Sonesta, promoted through the fixed
        boundary. No other record was added or removed."""
        pkg = self._pkg()
        assert len(pkg["hotels"]) == 38
        s = [h for h in pkg["hotels"] if h["key"] == "sonesta simply suites dublin columbus"]
        assert len(s) == 1
        assert "pet_fee" not in s[0]["facts"]          # never flattened to a scalar
