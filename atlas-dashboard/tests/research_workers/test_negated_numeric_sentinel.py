"""PTF-WORKERS -- an absence sentinel in a field the source explicitly negates.

The model reads "no breed or weight restrictions" correctly, and then has
nowhere numeric to put that finding: ``weight_limit`` can hold a quantity and
nothing else. So it writes "none". The numeric rule rejected that as
``number_not_in_quote``, which routes INCOMPLETE_EXTRACTION -- never waivable --
and the property was blocked for a fact it had stated plainly and the model had
understood.

That is a field-shape mistake, not a missing extraction. It is normalized away
at the parsing boundary rather than rejected, so it can never become the
blocker; the source-supported negative fact stands on its own, and no numeric
limit is ever published.

The narrowness is the point. A sentinel is only normalized when the SOURCE
explicitly negates that exact field. Sent for a field the source quantifies, or
never mentions, it still fails closed exactly as before.

Offline: no network, no model call, no production write.
"""

from __future__ import annotations

import pytest

from services.research_workers import routing as RT
from services.research_workers import vocabulary as V
from services.research_workers.contracts import (
    Assignment, SourceDocument, content_hash,
)
from services.research_workers.evidence_validator import (
    NEGATED_FIELD_SENTINEL, explicitly_negated_fields, is_absence_sentinel,
    validate_proposal,
)
from services.research_workers.proposal import ModelProposal, RawFactClaim

URL = "https://ex.example/pets"

NO_LIMITS = ("Up to two well-mannered dogs per suite with no breed or weight "
             "restrictions; cats are not allowed; $75 fee per pet for stays up to "
             "7 nights, $150 for longer stays")
SILENT_ON_WEIGHT = ("Pets are welcome at this property. Up to two pets per room. "
                    "A $50 fee applies per night.")
REAL_WEIGHT = ("Pets welcome. Maximum Pet Weight: 50 lbs. "
               "Maximum Number of Pets in Room: 2. A $50 fee applies per night.")
COMBINED_ONLY = ("Dogs and cats accepted; limit two pets per room with a combined "
                 "weight of 80 pounds; service animals free of charge.")


def _asg(text, url=URL):
    doc = SourceDocument(url, V.SOURCE_OFFICIAL_PROPERTY, "2026-08-02T00:00:00Z", "t",
                         text, content_hash(text), V.RETRIEVAL_OK)
    return Assignment("sent-1", "columbus-oh", "sent-1", "H", "1 St", url,
                      (url,), (doc,), V.POLICY_FIELDS, "t")


def _run(text, facts):
    asg = _asg(text)
    prop = ModelProposal(claims=tuple(RawFactClaim(*f) for f in facts), fee_terms=(),
                         ok=True, structured_output_valid=True, provider="openai", model="m")
    res = validate_proposal(asg, prop)
    return res, RT.route_result(asg, res, run_id="r", observed_at="2026-08-02")


def _supported(res, field):
    return next((f.value for f in res.proposed_facts
                 if f.field_name == field and f.state == V.SUPPORTED), None)


# --------------------------------------------------------------------------- #
# The sentinel vocabulary: a CLOSED list of whole values.
# --------------------------------------------------------------------------- #

class TestAbsenceSentinel:
    @pytest.mark.parametrize("value", [
        "none", "None", "NONE", "no restriction", "no restrictions", "no limit",
        "no limits", "not applicable", "n/a", "na", "unrestricted", "unlimited",
        "no maximum", " none ", "none.",
    ])
    def test_recognised_sentinels(self, value):
        assert is_absence_sentinel(value) is True

    @pytest.mark.parametrize("value", [
        "50", "50 pounds", "80 combined", "5O lbs", "none of our rooms",
        "no dogs over 50 lbs", "limited to 40", "0", "", "true", "false",
        "under 80 pounds",
    ])
    def test_non_sentinels(self, value):
        assert is_absence_sentinel(value) is False


# --------------------------------------------------------------------------- #
# A-E. The required regression cases.
# --------------------------------------------------------------------------- #

class TestNormalizationCases:
    def test_a_negated_numeric_sentinel_is_normalized_away(self):
        res, env = _run(NO_LIMITS, (
            (V.FIELD_PETS_ALLOWED, "true", "Up to two well-mannered dogs per suite", URL),
            (V.FIELD_BREED_RESTRICTIONS, "false", "no breed or weight restrictions", URL),
            (V.FIELD_WEIGHT_LIMIT, "none", "no breed or weight restrictions", URL),
        ))
        assert ("%s:%s" % (NEGATED_FIELD_SENTINEL, V.FIELD_WEIGHT_LIMIT)) in res.warnings
        assert not any(w.startswith("rejected_%s" % V.FIELD_WEIGHT_LIMIT)
                       for w in res.warnings)                       # normalized, not rejected
        assert RT.INCOMPLETE_EXTRACTION not in env.reason_codes
        assert _supported(res, V.FIELD_WEIGHT_LIMIT) is None         # no number published
        assert _supported(res, V.FIELD_BREED_RESTRICTIONS) == "false"  # negative preserved
        assert _supported(res, V.FIELD_PETS_ALLOWED) == "true"

    def test_b_silence_keeps_the_existing_rejection(self):
        """The source never mentions weight. Unknown is not unlimited."""
        assert V.FIELD_WEIGHT_LIMIT not in explicitly_negated_fields(SILENT_ON_WEIGHT)
        res, env = _run(SILENT_ON_WEIGHT, (
            (V.FIELD_PETS_ALLOWED, "true", "Pets are welcome at this property", URL),
            (V.FIELD_WEIGHT_LIMIT, "none", "Pets are welcome at this property", URL),
        ))
        assert any(w.startswith("rejected_%s" % V.FIELD_WEIGHT_LIMIT) for w in res.warnings)
        assert RT.INCOMPLETE_EXTRACTION in env.reason_codes
        assert _supported(res, V.FIELD_WEIGHT_LIMIT) is None

    def test_c_a_real_stated_limit_makes_the_sentinel_a_missed_fact(self):
        """The source states 50 lbs. "none" is not a shape mistake here, it is
        a fact the model failed to extract -- and must stay blocking."""
        assert V.FIELD_WEIGHT_LIMIT not in explicitly_negated_fields(REAL_WEIGHT)
        res, env = _run(REAL_WEIGHT, (
            (V.FIELD_PETS_ALLOWED, "true", "Pets welcome", URL),
            (V.FIELD_WEIGHT_LIMIT, "none", "Maximum Pet Weight: 50 lbs", URL),
        ))
        assert any(w.startswith("rejected_%s" % V.FIELD_WEIGHT_LIMIT) for w in res.warnings)
        assert RT.INCOMPLETE_EXTRACTION in env.reason_codes
        assert _supported(res, V.FIELD_WEIGHT_LIMIT) is None

    def test_d_a_boolean_negated_field_is_handled_consistently(self):
        """breed_restrictions CAN hold this finding, so a sentinel there is the
        same shape mistake -- classified the same way, and never converted into
        a "false" the model did not state."""
        res, env = _run(NO_LIMITS, (
            (V.FIELD_PETS_ALLOWED, "true", "Up to two well-mannered dogs per suite", URL),
            (V.FIELD_BREED_RESTRICTIONS, "none", "no breed or weight restrictions", URL),
        ))
        assert ("%s:%s" % (NEGATED_FIELD_SENTINEL, V.FIELD_BREED_RESTRICTIONS)) in res.warnings
        assert RT.INCOMPLETE_EXTRACTION not in env.reason_codes
        assert _supported(res, V.FIELD_BREED_RESTRICTIONS) is None   # never fabricated

    def test_e_a_combined_limit_is_not_an_explicit_negation(self):
        """"combined weight of 80 pounds" states a REAL limit. Reading it as
        "unrestricted" would publish a hotel as accepting any size."""
        assert V.FIELD_WEIGHT_LIMIT not in explicitly_negated_fields(COMBINED_ONLY)
        res, env = _run(COMBINED_ONLY, (
            (V.FIELD_PETS_ALLOWED, "true", "Dogs and cats accepted", URL),
            (V.FIELD_WEIGHT_LIMIT, "none", "combined weight of 80 pounds", URL),
        ))
        assert any(w.startswith("rejected_%s" % V.FIELD_WEIGHT_LIMIT) for w in res.warnings)
        assert RT.INCOMPLETE_EXTRACTION in env.reason_codes


# --------------------------------------------------------------------------- #
# Nothing else moved.
# --------------------------------------------------------------------------- #

class TestNoGateWeakened:
    def test_contradictions_are_untouched(self):
        text = NO_LIMITS + " Elsewhere the page states a maximum of 3 pets per suite."
        res, env = _run(text, (
            (V.FIELD_MAXIMUM_PETS, "2", "Up to two well-mannered dogs per suite", URL),
            (V.FIELD_MAXIMUM_PETS, "3", "a maximum of 3 pets per suite", URL),
        ))
        assert res.contradictions
        assert RT.CONTRADICTORY_OFFICIAL_SOURCES in env.reason_codes

    def test_a_record_with_nothing_supported_is_still_incomplete(self):
        res, env = _run(NO_LIMITS, (
            (V.FIELD_WEIGHT_LIMIT, "none", "no breed or weight restrictions", URL),
        ))
        assert not any(f.state == V.SUPPORTED for f in res.proposed_facts)
        assert env.route != RT.ROUTE_READY

    def test_a_genuine_missing_fact_still_blocks(self):
        res, env = _run(REAL_WEIGHT, (
            (V.FIELD_PETS_ALLOWED, "true", "Pets welcome", URL),
            (V.FIELD_MAXIMUM_PETS, "9", "Maximum Number of Pets in Room: 2", URL),
        ))
        assert RT.INCOMPLETE_EXTRACTION in env.reason_codes

    def test_never_waivable_codes_unchanged(self):
        from scripts.pettripfinder.prod003_approvals import (
            NEVER_WAIVABLE_REASON_CODES, WAIVABLE_REASON_CODES,
        )
        assert WAIVABLE_REASON_CODES == frozenset({"STRUCTURED_FEE_REQUIRED"})
        assert "INCOMPLETE_EXTRACTION" in NEVER_WAIVABLE_REASON_CODES
        assert "CONTRADICTORY_OFFICIAL_SOURCES" in NEVER_WAIVABLE_REASON_CODES

    def test_capture_worthy_unchanged(self):
        from services.research_workers.operator_capture import CAPTURE_WORTHY
        assert CAPTURE_WORTHY == frozenset({
            "ACCESS_BLOCKED", "RENDER_REQUIRED", "BROWSER_ACCESS_BLOCKED",
            "PROPERTY_PAGE_NOT_FOUND"})

    def test_the_normalization_names_no_brand(self):
        import inspect
        from services.research_workers import evidence_validator as EV
        src = inspect.getsource(EV.is_absence_sentinel).lower()
        for token in ("sonesta", "hyatt", "hilton", "marriott", "wyndham", ".com"):
            assert token not in src
