"""PTF-WORKERS -- what the production chain can actually render.

Routing used to withhold EVERY structured fee as
DOWNSTREAM_FEE_SCHEMA_UNSUPPORTED, on the grounds that the importer and
renderer were single-value. That stopped being true when fee_tiers shipped:
three published profiles render a stay-length ladder today. The blanket rule
was answering "is there a structured fee?" when the question is "can we render
THIS one honestly?".

These tests pin the capability, and the refusals matter more than the
permissions: the failure mode of getting this wrong is publishing a fee a guest
would actually be charged differently for.

Offline: no network, no model call, no production write.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from services.research_workers import routing as RT
from services.research_workers import vocabulary as V
from services.research_workers.contracts import PetFeePolicy, PetFeeTerm
from services.research_workers.fee_terms import downstream_fee_schema_support

_PKG = (pathlib.Path(__file__).resolve().parents[2] / "launch_packages" /
        "pettripfinder" / "hotel_policy_facts.json")


def term(amount, lo, hi, *, unit=V.BOUNDARY_UNIT_NIGHTS, currency="USD",
         role=V.FEE_ROLE_ONE_TIME_CHARGE,
         condition=V.FEE_CONDITION_STAY_LENGTH_RANGE):
    return PetFeeTerm(role=role, amount=amount, currency=currency,
                      basis=V.FEE_TERM_BASIS_ONE_TIME, scope=V.FEE_SCOPE_UNSTATED,
                      condition_type=condition, condition_min=lo, condition_max=hi,
                      boundary_unit=unit, evidence_quote="q",
                      source_url="https://ex.example/p", source_type="OFFICIAL_PROPERTY")


def policy(*terms):
    return PetFeePolicy(terms=tuple(terms), fee_policy_version=V.FEE_POLICY_VERSION)


SONESTA = policy(term("75.00", 1, 7), term("150.00", 8, None))
HAMPTON = policy(term("75.00", 1, 4), term("125.00", 5, None))


# --------------------------------------------------------------------------- #
# F / G / K. Supported shapes.
# --------------------------------------------------------------------------- #

class TestSupportedShapes:
    def test_f_sonesta_two_open_ended_tiers_are_supported(self):
        supported, reasons = downstream_fee_schema_support(SONESTA)
        assert supported and reasons == []

    def test_g_every_published_ladder_is_supported(self):
        """Exactly the shape the live profiles carry. Sonesta joined them on
        2026-08-02 as the first to arrive through the worker path."""
        pkg = json.loads(_PKG.read_text(encoding="utf-8-sig"))
        tiered = [h for h in pkg["hotels"] if h.get("facts", {}).get("fee_tiers")]
        assert len(tiered) == 25
        for h in tiered:
            terms = [term(t["amount"], t["condition_min"], t["condition_max"],
                          unit=t["boundary_unit"], currency=t["currency"],
                          role=t["role"], condition=t["condition_type"])
                     for t in h["facts"]["fee_tiers"]]
            supported, reasons = downstream_fee_schema_support(policy(*terms))
            assert supported, (h["key"], reasons)

    def test_three_tiers_are_supported(self):
        supported, _ = downstream_fee_schema_support(
            policy(term("50.00", 1, 3), term("75.00", 4, 7), term("100.00", 8, None)))
        assert supported

    def test_a_days_ladder_is_supported(self):
        supported, _ = downstream_fee_schema_support(
            policy(term("40.00", 1, 3, unit=V.BOUNDARY_UNIT_DAYS),
                   term("90.00", 4, None, unit=V.BOUNDARY_UNIT_DAYS)))
        assert supported

    def test_no_policy_is_trivially_supported(self):
        assert downstream_fee_schema_support(None) == (True, [])

    def test_k_a_tier_amount_with_unstated_basis_is_policy_not_a_trip_total(self):
        """The renderer states the amounts and says plainly that the source
        gives no basis. Nothing multiplies them into a stay cost."""
        from scripts.pettripfinder.hotel_profile import _verified_details, _tiered_fee_sentence
        tiers = [{"amount": "75.00", "currency": "USD", "role": "ONE_TIME_CHARGE",
                  "basis": "one_time", "basis_stated": False, "scope": "unstated",
                  "condition_type": "stay_length_range", "condition_min": 1,
                  "condition_max": 7, "boundary_unit": "nights"},
                 {"amount": "150.00", "currency": "USD", "role": "ONE_TIME_CHARGE",
                  "basis": "one_time", "basis_stated": False, "scope": "unstated",
                  "condition_type": "stay_length_range", "condition_min": 8,
                  "condition_max": None, "boundary_unit": "nights"}]
        rows = dict((l, v) for l, v, _c in _verified_details(
            {"pets_allowed": "true", "fee_tiers": tiers, "species_allowed": "dogs",
             "pet_count_limit": "2"})[0])
        charge_rows = {l: v for l, v in rows.items() if l.startswith("Pet charge,")}
        assert sorted(charge_rows.values()) == ["$150", "$75"]
        assert any("1" in l and "7" in l for l in charge_rows)      # the closed band
        assert any("8" in l and "more" in l for l in charge_rows)   # the open band
        assert "does not state" in rows["Charge basis"]
        sentence = _tiered_fee_sentence(tiers, "")
        for invented in ("per night", "per stay", "per pet", "total", "×", "x 7"):
            assert invented not in sentence.lower()


# --------------------------------------------------------------------------- #
# H / I / J / L. Refusals.
# --------------------------------------------------------------------------- #

class TestRefusedShapes:
    def test_h_overlapping_tiers_are_blocked(self):
        supported, reasons = downstream_fee_schema_support(
            policy(term("75.00", 1, 6), term("125.00", 4, None)))
        assert not supported and "downstream_ladder_overlaps" in reasons

    def test_i_a_gap_between_tiers_is_blocked(self):
        """Nothing states the price of a stay that falls in the hole, and the
        package schema has no way to say "unpriced between 5 and 8 nights"."""
        supported, reasons = downstream_fee_schema_support(
            policy(term("75.00", 1, 4), term("125.00", 9, None)))
        assert not supported and "downstream_ladder_has_gap" in reasons

    def test_j_an_open_tier_that_is_not_last_is_blocked(self):
        supported, reasons = downstream_fee_schema_support(
            policy(term("75.00", 1, None), term("125.00", 5, 9)))
        assert not supported
        assert "downstream_open_tier_not_last" in reasons

    def test_a_closed_final_tier_is_blocked(self):
        supported, reasons = downstream_fee_schema_support(
            policy(term("75.00", 1, 4), term("125.00", 5, 9)))
        assert not supported and "downstream_final_tier_not_open" in reasons

    def test_a_ladder_not_starting_at_one_is_blocked(self):
        supported, reasons = downstream_fee_schema_support(
            policy(term("75.00", 2, 4), term("125.00", 5, None)))
        assert not supported and "downstream_ladder_does_not_start_at_one" in reasons

    def test_a_single_tier_is_not_a_ladder(self):
        supported, reasons = downstream_fee_schema_support(policy(term("75.00", 1, None)))
        assert not supported and "downstream_single_tier_is_not_a_ladder" in reasons

    def test_l_a_cap_role_is_not_renderable_as_a_tier(self):
        """A CAP is a ceiling, not a stay band. Rendering it as one would tell a
        reader the maximum is the price for those nights."""
        supported, reasons = downstream_fee_schema_support(
            policy(term("75.00", 1, 4), term("150.00", 5, None, role=V.FEE_ROLE_CAP)))
        assert not supported and "downstream_role_not_renderable" in reasons

    def test_l_an_unconditional_term_is_not_a_stay_band(self):
        supported, reasons = downstream_fee_schema_support(
            policy(term("75.00", 1, 4),
                   term("125.00", 5, None, condition=V.FEE_CONDITION_UNCONDITIONAL)))
        assert not supported and "downstream_condition_not_stay_length" in reasons

    def test_a_non_usd_currency_is_blocked(self):
        """The renderer formats every amount with a literal "$"."""
        supported, reasons = downstream_fee_schema_support(
            policy(term("75.00", 1, 4), term("125.00", 5, None, currency="EUR")))
        assert not supported and "downstream_currency_not_renderable" in reasons

    def test_mixed_units_are_blocked(self):
        supported, reasons = downstream_fee_schema_support(
            policy(term("75.00", 1, 4),
                   term("125.00", 5, None, unit=V.BOUNDARY_UNIT_DAYS)))
        assert not supported and "downstream_mixed_or_unsupported_unit" in reasons

    def test_every_reason_is_a_declared_slug(self):
        from services.research_workers.fee_terms import DOWNSTREAM_UNSUPPORTED_REASONS
        for pol in (policy(term("75.00", 1, 6), term("125.00", 4, None)),
                    policy(term("75.00", 1, 4), term("125.00", 9, None)),
                    policy(term("75.00", 2, 4), term("125.00", 5, None)),
                    policy(term("75.00", 1, None))):
            _s, reasons = downstream_fee_schema_support(pol)
            assert set(reasons) <= set(DOWNSTREAM_UNSUPPORTED_REASONS), reasons


# --------------------------------------------------------------------------- #
# Routing consequence.
# --------------------------------------------------------------------------- #

class TestRoutingUsesCapabilityNotPresence:
    def _env(self, pol):
        from services.research_workers.contracts import (
            Assignment, SourceDocument, WorkerResult, content_hash,
        )
        from services.research_workers.contracts import ProposedField
        url = "https://ex.example/p"
        d = SourceDocument(url, V.SOURCE_OFFICIAL_PROPERTY, "t", "t", "Pets welcome.",
                           content_hash("x"), V.RETRIEVAL_OK)
        asg = Assignment("d-1", "columbus-oh", "d-1", "H", "1 St", url, (url,), (d,),
                         V.POLICY_FIELDS, "t")
        res = WorkerResult(
            assignment_id="d-1", listing_key="d-1", status=V.STATUS_COMPLETED,
            selected_source_url=url, selected_source_type=V.SOURCE_OFFICIAL_PROPERTY,
            proposed_facts=(ProposedField(V.FIELD_PETS_ALLOWED, V.SUPPORTED,
                                          value="true", evidence_quote="Pets welcome.",
                                          source_url=url,
                                          source_type=V.SOURCE_OFFICIAL_PROPERTY),),
            contradictions=(), warnings=(),
            evidence_quotes=("Pets welcome.",), unknown_fields=(),
            provider="openai", model="m", fee_policy=pol)
        return RT.route_result(asg, res, run_id="r", observed_at="2026-08-02")

    def test_a_supported_ladder_is_not_withheld_for_being_structured(self):
        env = self._env(SONESTA)
        assert RT.DOWNSTREAM_FEE_SCHEMA_UNSUPPORTED not in env.reason_codes

    def test_an_unsupported_shape_is_still_withheld(self):
        env = self._env(policy(term("75.00", 1, 4), term("125.00", 9, None)))
        assert RT.DOWNSTREAM_FEE_SCHEMA_UNSUPPORTED in env.reason_codes
        assert env.route == RT.ROUTE_REVIEW

    def test_the_reason_code_still_exists_for_real_cases(self):
        assert RT.DOWNSTREAM_FEE_SCHEMA_UNSUPPORTED in RT.REVIEW_REASONS
