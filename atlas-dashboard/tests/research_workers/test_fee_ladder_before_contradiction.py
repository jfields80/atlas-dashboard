"""PTF-FEE-TIERS-005A -- a stay-length ladder is read before its several
amounts are classified as a contradiction.

``detect_multiple_fee_amounts`` answers "does this evidence state more than one
pet-fee amount?", and a ladder always does. That is the right backstop against
a model FLATTENING a ladder into one misleading number, but it cannot tell a
ladder from a disagreement. So a property that stated its tiers perfectly
clearly was routed CONTRADICTORY_OFFICIAL_SOURCES for being clear about them --
and that reason is never waivable, so the hotel could never publish.

These tests pin the distinction. The guards matter more than the extraction: a
reader that turns "a $75 fee plus an additional $100 cleaning fee" into a
two-tier ladder would tell a guest the second number REPLACES the first when it
is added to it.

Offline: no network, no model call, no production write.
"""

from __future__ import annotations

import inspect

from services.research_workers import fee_terms as FT
from services.research_workers import routing as RT
from services.research_workers import vocabulary as V
from services.research_workers.contracts import (
    Assignment, SourceDocument, content_hash,
)
from services.research_workers.evidence_validator import validate_proposal
from services.research_workers.proposal import ModelProposal, RawFactClaim

URL = "https://ex.example/pets"

# --------------------------------------------------------------------------- #
# Wordings. Verbatim or faithfully composed from the real sources.
# --------------------------------------------------------------------------- #

SONESTA_LADDER = (
    "Up to two well-mannered dogs per suite with no breed or weight restrictions; "
    "cats are not allowed; $75 fee per pet for stays up to 7 nights, $150 for longer stays")
SONESTA_LIVE = (
    "pets, with no breed or weight restrictions. Up to two pets are permitted per suite. "
    "We apologize as cats are not permitted. $75 fee, per pet, applies for stays up to "
    "7 nights; $150 for all longer stays.")
GENUINE_CONFLICT = (
    "Pet Policy Pets Welcome. Non-Refundable Pet Fee Per Stay: $50.00. "
    "Elsewhere the same page states a pet fee of $95 per stay.")
HYATT_TWO_CHARGES = (
    "Up to two housebroken dogs per room (50 pounds each, 75 pounds combined); "
    "$75 non-refundable pet fee for stays of one to six nights, with an additional "
    "$100 cleaning fee for stays of 7 to 30 nights")
ESA_FIRST_SIX = (
    "A maximum of two pets per suite (no longer or taller than 36 inches); non-refundable "
    "pet cleaning fee of up to $25 plus tax per day per pet for the first six nights, then "
    "up to $15 per day; service animals exempt")
HAMPTON_COMPRESSED = (
    "Pets allowed Yes Deposit Yes. $75.00 Non-refundable Fee Other pet information "
    "$75(1-4n)$125(5+n)2pet Max dog/cat only")
NEW_ALBANY_RENDERED = (
    "Pets allowed Yes. Other pet information 1-4 night stay $50; 5+ night stay $75; "
    "2 pets max; dog or cat only")
FLAT_SCALAR = ("Pet Policy Pets Welcome Non-Refundable Pet Fee Per Night: $50.00 "
               "Maximum Number of Pets in Room: 2")


def _asg(text, url=URL, stype=V.SOURCE_OFFICIAL_PROPERTY):
    doc = SourceDocument(url, stype, "2026-08-02T00:00:00Z", "t", text,
                         content_hash(text), V.RETRIEVAL_OK)
    return Assignment("ladder-1", "columbus-oh", "ladder-1", "H", "1 St", url,
                      (url,), (doc,), V.POLICY_FIELDS, "t")


def _validate(text, facts=()):
    asg = _asg(text)
    prop = ModelProposal(claims=tuple(RawFactClaim(*f) for f in facts), fee_terms=(),
                         ok=True, structured_output_valid=True, provider="openai", model="m")
    return asg, validate_proposal(asg, prop)


def _route(text, facts=()):
    asg, res = _validate(text, facts)
    return res, RT.route_result(asg, res, run_id="r", observed_at="2026-08-02")


def _tiers(res):
    return ([(t.amount, t.condition_min, t.condition_max) for t in res.fee_policy.terms]
            if res.fee_policy else [])


def _scalar_fee(res):
    return next((f.value for f in res.proposed_facts
                 if f.field_name == V.FIELD_PET_FEE and f.state == V.SUPPORTED), None)


def _fee(v, q):
    return (V.FIELD_PET_FEE, v, q, URL)


# --------------------------------------------------------------------------- #
# A. A real ladder is a schedule, not a disagreement.
# --------------------------------------------------------------------------- #

class TestLadderIsNotAContradiction:
    def test_sonesta_ladder_clears_the_contradiction(self):
        res, env = _route(SONESTA_LADDER, (
            (V.FIELD_PETS_ALLOWED, "true", "Up to two well-mannered dogs per suite", URL),
            _fee("75", "$75 fee per pet for stays up to 7 nights"),
            _fee("150", "$150 for longer stays"),
        ))
        assert res.contradictions == ()
        assert RT.CONTRADICTORY_OFFICIAL_SOURCES not in env.reason_codes
        assert RT.STRUCTURED_FEE_REQUIRED not in env.reason_codes

    def test_the_tiers_are_exact(self):
        _asgn, res = _validate(SONESTA_LADDER)
        assert _tiers(res) == [("75.00", 1, 7), ("150.00", 8, None)]

    def test_the_live_page_wording_reads_identically(self):
        _asgn, res = _validate(SONESTA_LIVE)
        assert _tiers(res) == [("75.00", 1, 7), ("150.00", 8, None)]

    def test_no_scalar_fee_is_published_beside_a_ladder(self):
        _asgn, res = _validate(SONESTA_LADDER, (
            _fee("75", "$75 fee per pet for stays up to 7 nights"),
            _fee("150", "$150 for longer stays"),
        ))
        assert _scalar_fee(res) is None

    def test_no_fee_cap_is_invented(self):
        _asgn, res = _validate(SONESTA_LADDER)
        assert all(t.role != V.FEE_ROLE_CAP for t in res.fee_policy.terms)

    def test_no_basis_is_asserted(self):
        """"per pet" is a SCOPE. It says nothing about per-night vs per-stay."""
        _asgn, res = _validate(SONESTA_LADDER)
        assert all(t.basis == V.FEE_TERM_BASIS_ONE_TIME for t in res.fee_policy.terms)

    def test_the_final_tier_is_open_ended(self):
        _asgn, res = _validate(SONESTA_LADDER)
        assert res.fee_policy.terms[-1].condition_max is None


# --------------------------------------------------------------------------- #
# B-D. Everything that is NOT a ladder stays blocked.
# --------------------------------------------------------------------------- #

class TestNonLaddersStayBlocked:
    def test_b_two_genuinely_conflicting_statements(self):
        res, env = _route(GENUINE_CONFLICT, (
            (V.FIELD_PETS_ALLOWED, "true", "Pets Welcome", URL),
            _fee("50", "Non-Refundable Pet Fee Per Stay: $50.00"),
            _fee("95", "a pet fee of $95 per stay"),
        ))
        assert res.status == V.STATUS_CONTRADICTORY
        assert RT.CONTRADICTORY_OFFICIAL_SOURCES in env.reason_codes
        assert _tiers(res) == []

    def test_c_a_fee_plus_an_additional_fee_is_two_charges(self):
        """Reading this as a ladder would tell a guest the $100 REPLACES the
        $75 when the source adds it to it."""
        res, env = _route(HYATT_TWO_CHARGES, (
            (V.FIELD_PETS_ALLOWED, "true", "Up to two housebroken dogs per room", URL),
            _fee("75", "$75 non-refundable pet fee for stays of one to six nights"),
            _fee("100", "an additional $100 cleaning fee for stays of 7 to 30 nights"),
        ))
        assert _tiers(res) == []
        assert RT.CONTRADICTORY_OFFICIAL_SOURCES in env.reason_codes

    def test_d_extended_stay_wording_remains_blocked(self):
        """A word-number boundary and a "then" rate the parser cannot represent
        faithfully must stay blocked rather than be half-read."""
        res, env = _route(ESA_FIRST_SIX, (
            (V.FIELD_PETS_ALLOWED, "true", "A maximum of two pets per suite", URL),
            _fee("25", "fee of up to $25 plus tax per day per pet for the first six nights"),
            _fee("15", "then up to $15 per day"),
        ))
        assert _tiers(res) == []
        assert RT.CONTRADICTORY_OFFICIAL_SOURCES in env.reason_codes


# --------------------------------------------------------------------------- #
# E-F. Nothing that already worked changed.
# --------------------------------------------------------------------------- #

class TestExistingBehaviourUnchanged:
    def test_e_compressed_notations_read_the_same_ladders(self):
        for text, expected in ((HAMPTON_COMPRESSED, [("75.00", 1, 4), ("125.00", 5, None)]),
                               (NEW_ALBANY_RENDERED, [("50.00", 1, 4), ("75.00", 5, None)])):
            _asgn, res = _validate(text)
            assert _tiers(res) == expected
            assert _scalar_fee(res) is None

    def test_f_a_single_scalar_fee_still_routes_ready(self):
        res, env = _route(FLAT_SCALAR, (
            (V.FIELD_PETS_ALLOWED, "true", "Pets Welcome", URL),
            _fee("50", "Non-Refundable Pet Fee Per Night: $50.00"),
        ))
        assert _tiers(res) == []
        assert _scalar_fee(res) == "50"
        assert env.route == RT.ROUTE_READY

    def test_a_non_fee_field_disagreement_still_contradicts(self):
        """The ladder speaks for the fee and nothing else. A genuine
        disagreement about pet COUNT, on a page whose FEE is a clean ladder,
        must still contradict -- otherwise the ladder would be laundering an
        unrelated conflict."""
        text = (SONESTA_LADDER
                + " Elsewhere the page states a maximum of 3 pets per suite.")
        res, _env = _route(text, (
            (V.FIELD_MAXIMUM_PETS, "2", "Up to two well-mannered dogs per suite", URL),
            (V.FIELD_MAXIMUM_PETS, "3", "a maximum of 3 pets per suite", URL),
        ))
        assert any(c.startswith(V.FIELD_MAXIMUM_PETS) for c in res.contradictions)
        assert _tiers(res) == [("75.00", 1, 7), ("150.00", 8, None)]   # ladder still read


# --------------------------------------------------------------------------- #
# The reader itself: fails closed, and names no brand.
# --------------------------------------------------------------------------- #

class TestSourceLadderReaderFailsClosed:
    def test_a_partial_parse_yields_no_ladder(self):
        assert FT.source_stay_length_ladder(
            _asg("$75 fee applies for stays up to 7 nights").source_documents) == ()

    def test_two_sources_disagreeing_yield_no_ladder(self):
        a = SourceDocument("https://ex.example/a", V.SOURCE_OFFICIAL_PROPERTY, "t", "t",
                           "$75(1-4n)$125(5+n)", content_hash("a"), V.RETRIEVAL_OK)
        b = SourceDocument("https://ex.example/b", V.SOURCE_OFFICIAL_PROPERTY, "t", "t",
                           "$60(1-4n)$90(5+n)", content_hash("b"), V.RETRIEVAL_OK)
        assert FT.source_stay_length_ladder((a, b)) == ()

    def test_two_sources_agreeing_yield_that_ladder(self):
        a = SourceDocument("https://ex.example/a", V.SOURCE_OFFICIAL_PROPERTY, "t", "t",
                           "$75(1-4n)$125(5+n)", content_hash("a"), V.RETRIEVAL_OK)
        b = SourceDocument("https://ex.example/b", V.SOURCE_OFFICIAL_PROPERTY, "t", "t",
                           "$75 for 1-4 nights; $125 for 5 nights or more",
                           content_hash("b"), V.RETRIEVAL_OK)
        got = FT.source_stay_length_ladder((a, b))
        assert [(t.amount, t.condition_min, t.condition_max) for t in got] == [
            ("75.00", 1, 4), ("125.00", 5, None)]

    def test_a_non_contiguous_ladder_is_refused(self):
        """Tiers with a gap are not a schedule -- nothing states the price for
        the nights that fall in the hole."""
        assert FT.source_stay_length_ladder(
            _asg("$75 for 1-4 nights and $125 for 9 nights or more").source_documents) == ()

    def test_a_closed_final_tier_is_refused(self):
        assert FT.source_stay_length_ladder(
            _asg("$75 for 1-4 nights and $125 for 5-9 nights").source_documents) == ()

    def test_an_unusable_source_is_never_read(self):
        doc = SourceDocument("https://ex.example/x", V.SOURCE_OFFICIAL_PROPERTY, "t", "t",
                             "$75(1-4n)$125(5+n)", content_hash("x"), "ERROR")
        assert FT.source_stay_length_ladder((doc,)) == ()

    def test_the_reader_names_no_brand(self):
        src = inspect.getsource(FT.source_stay_length_ladder).lower()
        for token in ("sonesta", "hyatt", "hilton", "marriott", "wyndham",
                      "extendedstay", "redroof", "drury", ".com"):
            assert token not in src
