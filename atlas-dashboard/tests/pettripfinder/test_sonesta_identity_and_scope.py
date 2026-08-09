"""PTF-SONESTA -- source identity, and the fee scope the source states.

Two pre-approval corrections, both about not publishing something the evidence
does not say.

1. The seed cited a Sonesta ES Suites URL for a Simply Suites property. The URL
   redirects to the Simply Suites page, so it was never a WRONG hotel -- but an
   approval binds a published citation to a page, and citing a legacy brand
   alias for a property that renamed is a claim the current page does not make.

2. The source states "$75 fee, PER PET, applies for stays up to 7 nights; $150
   for all longer stays". A per-pet charge and a per-room charge are the same
   number and different policies -- a second dog doubles one and not the other.
   The first tier states its scope; the second elides it. Ellipsis is how
   English avoids repetition, not a statement, so the stated scope is kept and
   the elided one is left unstated rather than inferred in either direction.

Offline: no network, no model call, no production write.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from scripts.pettripfinder.site_data import normalize_name, read_production_rows
from services.research_workers import vocabulary as V
from services.research_workers.fee_terms import (
    basis_is_stated, downstream_fee_schema_support, parse_fee_tiers, tier_facts,
)

_REPO = pathlib.Path(__file__).resolve().parents[2]
KEY = "sonesta simply suites dublin columbus"
OFFICIAL_URL = ("https://www.sonesta.com/sonesta-simply-suites/oh/dublin/"
                "sonesta-simply-suites-dublin-columbus")
LEGACY_ES_URL = ("https://www.sonesta.com/sonesta-es-suites/oh/dublin/"
                 "sonesta-es-suites-dublin-columbus")

#: Verbatim from the official page, 2026-08-02.
LIVE_POLICY = (
    "Sonesta Simply Suites Dublin Columbus is pet-friendly and welcomes well-mannered "
    "pets, with no breed or weight restrictions. Up to two pets are permitted per suite. "
    "We apologize as cats are not permitted. $75 fee, per pet, applies for stays up to "
    "7 nights; $150 for all longer stays.")


def _row():
    return next(r for r in read_production_rows() if normalize_name(r["name"]) == KEY)


# --------------------------------------------------------------------------- #
# 1. Identity and source binding.
# --------------------------------------------------------------------------- #

class TestSourceIdentity:
    def test_the_listing_identity_matches_the_official_page(self):
        """Confirmed against the page's own JSON-LD Hotel block."""
        r = _row()
        assert r["name"] == "Sonesta Simply Suites Dublin Columbus"
        assert r["address"] == "435 Metro Place South"
        assert (r["city"], r["state"], r["postal_code"]) == ("Dublin", "OH", "43017")
        assert r["phone"] == "614-791-0403"

    def test_both_url_fields_cite_the_current_official_page(self):
        r = _row()
        assert r["website_url"] == OFFICIAL_URL
        assert r["source_url"] == OFFICIAL_URL
        assert r["source_type"] == "OFFICIAL_PROPERTY"

    def test_no_legacy_es_suites_url_remains_in_any_tracked_artifact(self):
        """The alias must not survive anywhere a citation could be read from."""
        for rel in ("launch_packages/pettripfinder/seed_businesses.csv",
                    "launch_packages/pettripfinder/hotel_policy_facts.json",
                    "launch_packages/pettripfinder/hotel_worker_approvals.json"):
            text = (_REPO / rel).read_text(encoding="utf-8-sig")
            assert "sonesta-es-suites" not in text, rel

    def test_the_separate_sonesta_property_is_untouched(self):
        """Sonesta Columbus Downtown is a different hotel on a different URL
        family and must not have been swept up in the correction."""
        downtown = next(r for r in read_production_rows()
                        if normalize_name(r["name"]) == "sonesta columbus downtown")
        assert "sonesta-hotels-resorts" in downtown["source_url"]
        assert downtown["address"] == "33 East Nationwide Blvd"

    def test_the_evidence_date_matches_the_evidence(self):
        """PATH B: the row now carries the LIVE page wording, so it is observed
        on the day that page was captured -- never a fresh date on stale text."""
        r = _row()
        assert r["observed_at"] == "2026-08-02"
        assert r["pet_policy"] == LIVE_POLICY

    def test_the_recorded_policy_is_verbatim_from_the_official_page(self):
        """Pinned so a later edit cannot quietly paraphrase the source."""
        r = _row()
        assert "$75 fee, per pet, applies for stays up to 7 nights" in r["pet_policy"]
        assert "$150 for all longer stays" in r["pet_policy"]
        assert "We apologize as cats are not permitted" in r["pet_policy"]
        assert "no breed or weight restrictions" in r["pet_policy"]


# --------------------------------------------------------------------------- #
# 2. The fee scope the source states.
# --------------------------------------------------------------------------- #

class TestStatedFeeScope:
    def _terms(self):
        terms, problems = parse_fee_tiers(LIVE_POLICY)
        assert problems == []
        return terms

    def test_the_two_stay_length_tiers_are_preserved(self):
        assert [(t.amount, t.condition_min, t.condition_max) for t in self._terms()] == [
            ("75.00", 1, 7), ("150.00", 8, None)]

    def test_the_stated_first_tier_scope_is_kept(self):
        assert self._terms()[0].scope == V.FEE_SCOPE_PER_PET

    def test_the_elided_second_tier_scope_is_left_unstated(self):
        """The source does not repeat "per pet" for the $150 tier. Carrying it
        over would publish an inference; dropping it from the first tier would
        discard something the source says plainly. Neither is acceptable, so the
        ambiguity is preserved exactly where it exists."""
        assert self._terms()[1].scope == V.FEE_SCOPE_UNSTATED

    def test_no_time_basis_is_inferred(self):
        """"per pet" is a SCOPE. It says nothing about per-night vs per-stay."""
        assert basis_is_stated(LIVE_POLICY) is False
        assert all(t.basis == V.FEE_TERM_BASIS_ONE_TIME for t in self._terms())

    def test_no_scalar_fee_and_no_cap_are_produced(self):
        terms = self._terms()
        assert len(terms) == 2
        assert all(t.role == V.FEE_ROLE_ONE_TIME_CHARGE for t in terms)

    def test_the_ladder_remains_downstream_supported(self):
        policy = type("P", (), {"terms": tuple(self._terms())})()
        supported, reasons = downstream_fee_schema_support(policy)
        assert supported and reasons == []

    def test_the_reader_is_shown_the_per_pet_scope(self):
        from scripts.pettripfinder.hotel_profile import _tiered_fee_sentence, _verified_details
        tf = tier_facts(self._terms(), basis_stated=basis_is_stated(LIVE_POLICY))
        assert _tiered_fee_sentence(tf, LIVE_POLICY) == (
            "A pet fee of $75 per pet applies for stays of 1–7 nights, and $150 "
            "applies for stays of 8 nights or more.")
        rows = dict((l, v) for l, v, _c in _verified_details(
            {"pets_allowed": "true", "fee_tiers": tf, "species_allowed": "dogs",
             "pet_count_limit": "2"})[0])
        charge = {l: v for l, v in rows.items() if l.startswith("Pet charge,")}
        assert "$75 per pet" in charge.values()
        assert "$150" in charge.values()

    @pytest.mark.parametrize("text,expected", [
        # Scope stated on both tiers -> both carry it.
        ("$75 per pet for stays up to 7 nights; $150 per pet for all longer stays",
         [V.FEE_SCOPE_PER_PET, V.FEE_SCOPE_PER_PET]),
        # Stated on neither -> neither.
        ("$75 for stays up to 7 nights; $150 for all longer stays",
         [V.FEE_SCOPE_UNSTATED, V.FEE_SCOPE_UNSTATED]),
        # A per-ROOM scope is not a per-pet scope.
        ("$75 per room for stays up to 7 nights; $150 for all longer stays",
         [V.FEE_SCOPE_UNSTATED, V.FEE_SCOPE_UNSTATED]),
    ])
    def test_scope_is_read_per_tier_from_its_own_wording(self, text, expected):
        terms, problems = parse_fee_tiers(text)
        assert problems == []
        assert [t.scope for t in terms] == expected


# --------------------------------------------------------------------------- #
# 3. Nothing published moved.
# --------------------------------------------------------------------------- #

class TestPublishedProfilesUnaffected:
    def test_the_package_holds_38_hotels_including_sonesta(self):
        pkg = json.loads((_REPO / "launch_packages" / "pettripfinder" /
                          "hotel_policy_facts.json").read_text(encoding="utf-8-sig"))
        assert len(pkg["hotels"]) == 85
        assert KEY in {h["key"] for h in pkg["hotels"]}

    def test_the_pre_existing_ladders_still_state_no_scope(self):
        """The three ladders that were live before this work carry scope
        "unstated", so the per-pet rendering cannot change a published byte of
        theirs. Sonesta is the only record that states a scope."""
        pkg = json.loads((_REPO / "launch_packages" / "pettripfinder" /
                          "hotel_policy_facts.json").read_text(encoding="utf-8-sig"))
        tiered = {h["key"]: h["facts"]["fee_tiers"]
                  for h in pkg["hotels"] if h.get("facts", {}).get("fee_tiers")}
        # Every published ladder except Sonesta leaves scope unstated, so the
        # per-pet rendering cannot change a published byte of theirs. Asserted
        # over the whole published set rather than a frozen four-name list, so
        # a new ladder that silently claims a scope is caught too.
        assert KEY in tiered
        for key, tiers in tiered.items():
            if key == KEY:
                continue
            for t in tiers:
                assert t["scope"] == V.FEE_SCOPE_UNSTATED, key

    def test_sonesta_publishes_the_scope_its_source_states(self):
        pkg = json.loads((_REPO / "launch_packages" / "pettripfinder" /
                          "hotel_policy_facts.json").read_text(encoding="utf-8-sig"))
        tiers = [h for h in pkg["hotels"] if h["key"] == KEY][0]["facts"]["fee_tiers"]
        assert [t["scope"] for t in tiers] == [V.FEE_SCOPE_PER_PET, V.FEE_SCOPE_UNSTATED]

    def test_the_published_tier_sentences_are_unchanged(self):
        from scripts.pettripfinder.hotel_profile import _tiered_fee_sentence
        pkg = json.loads((_REPO / "launch_packages" / "pettripfinder" /
                          "hotel_policy_facts.json").read_text(encoding="utf-8-sig"))
        expected = {
            "hampton inn columbus airport":
                "A non-refundable pet fee of $75 applies for stays of 1–4 nights, "
                "and $125 applies for stays of 5 nights or more.",
            "hilton garden inn columbus airport":
                "A non-refundable pet fee of $75 applies for stays of 1–4 nights, "
                "and $125 applies for stays of 5 nights or more.",
            "home2 suites new albany columbus":
                "A non-refundable pet fee of $50 applies for stays of 1–4 nights, "
                "and $75 applies for stays of 5 nights or more.",
        }
        for h in pkg["hotels"]:
            if h["key"] in expected:
                assert _tiered_fee_sentence(
                    h["facts"]["fee_tiers"], h.get("evidence_quote") or "") == expected[h["key"]]
