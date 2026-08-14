"""PTF-RENDERER-FIDELITY-001 -- the renderer reachability gate.

Dead structured data is a release failure.

Phase A proved the contracts read every committed record; it also proved that
reading them was not enough. Twelve of fourteen committed ``fee_scope`` values
reached no public surface, sixty-six withholding decisions rendered as generic
silence, three explicit cat refusals rendered as "Not stated", and six
service-animal statements rendered nowhere at all. Every one of those was
extracted, evidenced, reviewed, committed -- and invisible.

This module is the gate that makes that impossible to repeat. For every fact
the renderer claims to support there is a row in ``SUPPORTED_FIELDS`` naming
the surfaces it must reach, and a test that builds the smallest record carrying
that fact and asserts it arrives.

Adding a field to the renderer without adding it here is a test failure, not an
oversight nobody notices for two markets.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.pettripfinder import canonical_view
from scripts.pettripfinder.hotel_profile import (
    WITHHELD_CLS, _verified_details, _verified_facts, _verified_summary,
    cap_qualifier_note, fee_qualifier_phrase, fee_scope_display,
)
from scripts.pettripfinder.markets import load_markets, market_by_id
from scripts.pettripfinder.site_pages import build_comparison_page

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_DIR = REPO_ROOT / "launch_packages" / "pettripfinder"

#: The exact silence copy. A withheld field must never carry it.
NOT_STATED = "Not stated by the reviewed source"

PROFILE = "profile"
COMPARISON = "comparison"

#: field -> (surfaces it must reach, minimal facts, expected fragment)
#:
#: "profile" covers the summary sentence, the fact chips and the detail table
#: taken together -- a fact may legitimately live in one of the three. Where a
#: field is intentionally profile-only that is recorded here by the absence of
#: COMPARISON, and the reason is given in the comment beside it.
SUPPORTED_FIELDS = {
    "pets_allowed": ((PROFILE,), {"pets_allowed": "true"}, "Pets"),
    "dogs_accepted": ((PROFILE, COMPARISON),
                      {"pets_allowed": "true", "species_allowed": "dogs"}, "Dogs"),
    "cats_accepted": ((PROFILE, COMPARISON),
                      {"pets_allowed": "true", "species_allowed": "dogs, cats",
                       "cats_allowed": "true"}, "Cats"),
    "cats_prohibited": ((PROFILE, COMPARISON),
                        {"pets_allowed": "true", "species_allowed": "dogs",
                         "cats_allowed": "false"}, "Not allowed"),
    "pet_count_limit": ((PROFILE, COMPARISON),
                        {"pets_allowed": "true", "pet_count_limit": "2"}, "2"),
    "pet_fee": ((PROFILE, COMPARISON),
                {"pets_allowed": "true", "pet_fee": "$50.00",
                 "fee_basis": "per stay"}, "$50"),
    "fee_basis": ((PROFILE, COMPARISON),
                  {"pets_allowed": "true", "pet_fee": "$50.00",
                   "fee_basis": "per stay"}, "per stay"),
    "fee_scope_per_room": ((PROFILE, COMPARISON),
                           {"pets_allowed": "true", "pet_fee": "$50.00",
                            "fee_basis": "per night", "fee_scope": "per_room"},
                           "per room"),
    "fee_scope_per_pet": ((PROFILE, COMPARISON),
                          {"pets_allowed": "true", "pet_fee": "$15.00",
                           "fee_basis": "per night", "fee_scope": "per pet",
                           "pet_count_limit": "2"}, "per pet"),
    "fee_tiers": ((PROFILE, COMPARISON),
                  {"pets_allowed": "true", "fee_tiers": [
                      {"role": "ONE_TIME_CHARGE", "amount": "75.00",
                       "currency": "USD", "condition_min": 1, "condition_max": 4,
                       "boundary_unit": "nights", "scope": "unstated",
                       "basis_stated": False},
                      {"role": "ONE_TIME_CHARGE", "amount": "125.00",
                       "currency": "USD", "condition_min": 5,
                       "condition_max": None, "boundary_unit": "nights",
                       "scope": "unstated", "basis_stated": False}]}, "$125"),
    "additive_tier": ((PROFILE,),   # profile-only: the table shows a range
                      {"pets_allowed": "true", "fee_tiers": [
                          {"role": "ONE_TIME_CHARGE", "amount": "100.00",
                           "currency": "USD", "condition_min": 1,
                           "condition_max": 6, "boundary_unit": "nights",
                           "scope": "unstated", "basis_stated": False},
                          {"role": "ONE_TIME_CHARGE", "amount": "200.00",
                           "currency": "USD", "condition_min": 7,
                           "condition_max": 30, "boundary_unit": "nights",
                           "scope": "unstated", "basis_stated": False,
                           "additive": True}]}, "additional"),
    "fee_cap": ((PROFILE, COMPARISON),
                {"pets_allowed": "true", "pet_fee": "$50.00",
                 "fee_basis": "per night", "pet_count_limit": "1",
                 "fee_cap": {"amount": "150.00", "currency": "USD",
                             "basis": "per stay"}}, "150"),
    "pet_deposit": ((PROFILE,),     # profile-only: a deposit is not a fee
                    {"pets_allowed": "true",
                     "pet_deposit": {"amount": "150.00", "currency": "USD"}},
                    "150"),
    "cleaning_fee": ((PROFILE,),    # profile-only, and never a pet-fee tier
                     {"pets_allowed": "true", "cleaning_fee": "$100.00"},
                     "100"),
    "weight_limit": ((PROFILE, COMPARISON),
                     {"pets_allowed": "true", "weight_limit": "50 pounds"},
                     "50"),
    "combined_weight": ((PROFILE, COMPARISON),
                        {"pets_allowed": "true", "weight_limit": "50 pounds",
                         "weight_limit_combined": "75 pounds"}, "75"),
    "weight_stated_none": ((PROFILE,),
                           {"pets_allowed": "true", "pet_count_limit": "2",
                            "weight_limit_stated_none": "true"},
                           "no pet weight limit"),
    "breed_restrictions": ((PROFILE,),
                           {"pets_allowed": "true",
                            "breed_restrictions": "No aggressive breeds."},
                           "aggressive"),
    "unattended_policy": ((PROFILE,),
                          {"pets_allowed": "true",
                           "unattended_policy": "not permitted"}, "permitted"),
    "reservation_requirement": ((PROFILE,),
                                {"pets_allowed": "true",
                                 "reservation_requirement": "Declare at check-in."},
                                "check-in"),
    "general_restrictions": ((PROFILE,),
                             {"pets_allowed": "true",
                              "general_restrictions": "Pets must be leashed."},
                             "leashed"),
}


def _record(facts, **kw):
    rec = {"key": "test hotel", "name": "Test Hotel", "facts": dict(facts),
           "evidence_quote": "", "verified_at": "2026-08-10",
           "source_url": "https://example.com/"}
    rec.update(kw)
    return rec


def profile_text(record):
    """Everything a visitor reads on the profile, as one searchable string."""
    f = record["facts"]
    parts = [_verified_summary(f, record.get("evidence_quote") or "")]
    parts += ["%s %s" % (l, v) for l, v, _c in _verified_facts(f)]
    parts += ["%s %s" % (l, v) for l, v, _c in _verified_details(f, record)[0]]
    return " | ".join(parts)


def comparison_html(record):
    f = record["facts"]
    view = canonical_view.build(record)
    row = {
        "name": record["name"], "route": "/x/", "area": "Columbus, OH",
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
    market = market_by_id(load_markets(), "columbus-oh")
    return build_comparison_page([row], market)


class TestReachability:
    """Every supported fact reaches every surface the matrix names."""

    @pytest.mark.parametrize("field", sorted(SUPPORTED_FIELDS))
    def test_reaches_the_profile(self, field):
        surfaces, facts, fragment = SUPPORTED_FIELDS[field]
        if PROFILE not in surfaces:
            pytest.skip("%s is not a profile field" % field)
        text = profile_text(_record(facts))
        assert fragment.lower() in text.lower(), \
            "%s never reaches the profile: %s" % (field, text[:300])

    @pytest.mark.parametrize("field", sorted(SUPPORTED_FIELDS))
    def test_reaches_the_comparison_table(self, field):
        surfaces, facts, fragment = SUPPORTED_FIELDS[field]
        if COMPARISON not in surfaces:
            pytest.skip("%s is intentionally profile-only" % field)
        html = comparison_html(_record(facts))
        assert fragment.lower() in html.lower(), \
            "%s never reaches the comparison table" % field

    def test_the_matrix_covers_every_mandated_field(self):
        """The work order's list, pinned so nothing quietly drops out."""
        mandated = {
            "pets_allowed", "dogs_accepted", "cats_accepted", "cats_prohibited",
            "pet_count_limit", "pet_fee", "fee_basis", "fee_scope_per_room",
            "fee_scope_per_pet", "fee_tiers", "additive_tier", "fee_cap",
            "pet_deposit", "cleaning_fee", "weight_limit", "combined_weight",
            "weight_stated_none", "breed_restrictions", "unattended_policy",
            "reservation_requirement", "general_restrictions",
        }
        assert mandated <= set(SUPPORTED_FIELDS), mandated - set(SUPPORTED_FIELDS)


class TestWithheldNeverReadsAsSilence:
    """The distinction the whole phase exists to make."""

    CONFLICT = _record({"pets_allowed": "true", "pet_count_limit": "2",
                        "fee_conflict": {"reason": "conflicting_fee_terms",
                                         "detail": ["two amounts"],
                                         "evidence_quote": "$75 and $125"}})
    RANGE = _record({"pets_allowed": "true", "pet_count_limit": "2",
                     "fee_withheld": {"reason": "unrepresentable_fee_range",
                                      "detail": ["fee_range_75_to_150"],
                                      "evidence_quote": "75 to 150 dollars"}})

    @pytest.mark.parametrize("record", [CONFLICT, RANGE])
    def test_no_silence_copy_for_the_withheld_fee(self, record):
        rows = {l: v for l, v, _c in _verified_details(record["facts"], record)[0]}
        assert NOT_STATED not in rows.get("Pet charge", "")
        assert NOT_STATED not in rows.get("Charge basis", "")

    @pytest.mark.parametrize("record", [CONFLICT, RANGE])
    def test_withheld_uses_its_own_class(self, record):
        classes = {l: c for l, v, c in _verified_details(record["facts"], record)[0]}
        assert classes["Charge basis"] == WITHHELD_CLS
        chips = {l: c for l, v, c in _verified_facts(record["facts"])}
        assert chips["Pet charge"] == WITHHELD_CLS
        assert chips["Charge basis"] == WITHHELD_CLS

    @pytest.mark.parametrize("record", [CONFLICT, RANGE])
    def test_no_scalar_fee_leaks(self, record):
        text = profile_text(record)
        assert "$75" not in text and "$125" not in text and "$150" not in text

    @pytest.mark.parametrize("record", [CONFLICT, RANGE])
    def test_comparison_marks_it_withheld_not_unknown(self, record):
        html = comparison_html(record)
        assert 'class="ptf-withheld"' in html

    def test_silence_and_withheld_use_different_classes(self):
        silent = _record({"pets_allowed": "true", "pet_count_limit": "2"})
        classes = {l: c for l, v, c in _verified_details(silent["facts"], silent)[0]}
        assert classes["Pet charge"] == "dim"
        assert classes["Pet charge"] != WITHHELD_CLS

    def test_silence_still_says_not_stated(self):
        silent = _record({"pets_allowed": "true", "pet_count_limit": "2"})
        rows = {l: v for l, v, _c in _verified_details(silent["facts"], silent)[0]}
        assert rows["Pet charge"] == NOT_STATED


class TestServiceAnimalSeparation:
    """A legal access category never mixes with commercial terms."""

    RECORD = _record({"pets_allowed": "true", "pet_fee": "$50.00",
                      "fee_basis": "per night", "pet_count_limit": "1",
                      "weight_limit": "50 pounds",
                      "service_animal_exception": "true"})

    def test_the_statement_reaches_the_profile(self):
        rows = {l: v for l, v, _c in _verified_details(self.RECORD["facts"],
                                                       self.RECORD)[0]}
        assert "Property statement on service animals" in rows

    def test_it_never_reaches_the_comparison_table(self):
        html = comparison_html(self.RECORD)
        assert "service animal" not in html.lower()

    def test_it_is_not_a_pet_policy_fact(self):
        chips = {l for l, _v, _c in _verified_facts(self.RECORD["facts"])}
        assert not any("service" in c.lower() for c in chips)

    def test_nothing_is_invented_without_a_statement(self):
        plain = _record({"pets_allowed": "true", "pet_fee": "$50.00"})
        rows = {l for l, _v, _c in _verified_details(plain["facts"], plain)[0]}
        assert "Property statement on service animals" not in rows
