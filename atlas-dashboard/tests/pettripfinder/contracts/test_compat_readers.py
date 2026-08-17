"""PTF-CONTRACT-FOUNDATION-001 -- reading today's records as 1.2.

Two jobs are tested here. The mechanical transformations must be exact, and
the reader must REFUSE to guess where the legacy form does not determine the
1.2 form -- because a reader that guesses produces a migration nobody can
review.

The corpus tests run against committed authority. They skip rather than fail
when a package is absent, so a worktree without the launch package still runs
the rest of the suite honestly.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.pettripfinder.contracts import enums
from scripts.pettripfinder.contracts import policy_schema as ps
from scripts.pettripfinder.contracts.compat_readers import (
    decompose_fee_basis, parse_bool, parse_fee_scope, parse_money, parse_weight,
    read_package, read_record,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_DIR = REPO_ROOT / "launch_packages" / "pettripfinder"

PACKAGES = {
    "columbus-oh": "hotel_policy_facts.json",
    "cleveland-akron-canton-oh": "hotel_policy_facts_cleveland-akron-canton-oh.json",
    "dayton-oh": "hotel_policy_facts_dayton-oh.json",
}

#: What the three committed packages hold today. Pinned so a change to
#: committed authority shows up here rather than silently altering a count the
#: rest of the program reasons about.
EXPECTED_RECORDS = {"columbus-oh": 88, "cleveland-akron-canton-oh": 99,  # after PTF-CLEVELAND-PASS4-DECISION-APPLICATION-001
                    "dayton-oh": 47}


def load(market_id):
    path = PACKAGE_DIR / PACKAGES[market_id]
    if not path.is_file():
        pytest.skip("%s is not present in this worktree" % path.name)
    return json.loads(path.read_text(encoding="utf-8-sig"))


def review_codes(items):
    return {i.code for i in items}


class TestMoney:

    @pytest.mark.parametrize("value,cents", [
        ("$50.00", 5000), ("$50", 5000), ("$100.00", 10000), ("$15.00", 1500),
        ("50.00", 5000), ("75", 7500), ("$0.29", 29), ("$1.05", 105),
    ])
    def test_parses(self, value, cents):
        assert parse_money(value) == {"amount_cents": cents, "currency": "USD"}

    def test_cents_are_exact(self):
        """Via string, not float: 0.29 * 100 is 28.999999999999996."""
        assert parse_money("$0.29")["amount_cents"] == 29

    @pytest.mark.parametrize("value", ["free", "", "varies", "75 to 150", None])
    def test_rejects_non_money(self, value):
        assert parse_money(value) is None


class TestWeight:

    @pytest.mark.parametrize("value,expected", [
        ("75 pounds", (75.0, "lb")), ("80 lb", (80.0, "lb")),
        ("40.0 pounds", (40.0, "lb")), ("20 lbs", (20.0, "lb")),
        ("30 kg", (30.0, "kg")),
    ])
    def test_parses_every_corpus_spelling(self, value, expected):
        got = parse_weight(value)
        assert (got["value"], got["unit"]) == expected

    @pytest.mark.parametrize("value", ["large dogs", "", None, "no limit"])
    def test_rejects_non_weight(self, value):
        assert parse_weight(value) is None


class TestBooleans:

    @pytest.mark.parametrize("value,expected", [
        ("true", True), ("false", False), ("True", True), (True, True),
        (False, False),
    ])
    def test_parses(self, value, expected):
        assert parse_bool(value) is expected

    @pytest.mark.parametrize("value", ["maybe", "", None, "1"])
    def test_rejects(self, value):
        assert parse_bool(value) is None


class TestFeeScope:

    @pytest.mark.parametrize("value,expected", [
        ("per_room", "per_room"), ("per room", "per_room"),
        ("per_pet", "per_pet"), ("per pet", "per_pet"),
    ])
    def test_translates_every_spelling(self, value, expected):
        scope, recognised = parse_fee_scope(value)
        assert (scope, recognised) == (expected, True)

    @pytest.mark.parametrize("value", ["unknown", "unstated", ""])
    def test_sentinels_become_absence(self, value):
        """Recognised, and correctly translated to nothing at all."""
        assert parse_fee_scope(value) == (None, True)

    def test_unrecognised_is_flagged_not_guessed(self):
        assert parse_fee_scope("per bed") == (None, False)


class TestBasisDecomposition:

    @pytest.mark.parametrize("legacy,basis,scope,allowance", [
        ("per night", "per_night", None, None),
        ("per stay", "per_stay", None, None),
        ("per day", "per_day", None, None),
        ("per room per night", "per_night", "per_room", None),
        ("per room per day", "per_day", "per_room", None),
        ("per pet per night", "per_night", "per_pet", None),
        ("per stay per pet", "per_stay", "per_pet", None),
        ("per night for up to 2 pets", "per_night", "per_room", 2),
    ])
    def test_every_corpus_compound(self, legacy, basis, scope, allowance):
        got_basis, got_scope, got_allowance, recognised = decompose_fee_basis(legacy)
        assert recognised
        assert (got_basis, got_scope, got_allowance) == (basis, scope, allowance)

    def test_unknown_compound_is_flagged(self):
        assert decompose_fee_basis("per week")[3] is False


class TestWeightOperatorConvention:
    """Absence means inclusive -- preserving what production already renders."""

    def test_absent_operator_becomes_lte(self):
        """The renderer has published these as "Maximum pet weight is N".

        Reading absence as lte preserves that meaning exactly. Sending them to
        review would be the change, not the preservation.
        """
        result = read_record({"name": "Test Inn",
                              "facts": {"weight_limit": "75 pounds"}})
        assert result.record["facts"]["weight_limit"]["operator"] == enums.OP_LTE
        assert "MISSING_OPERATOR" not in review_codes(result.review)

    def test_explicit_lt_is_preserved(self):
        """"Under 80 lbs" turns an 80-pound dog away and must keep doing so."""
        result = read_record({"name": "Test Inn", "facts": {
            "weight_limit": "80 pounds", "weight_limit_operator": "lt"}})
        assert result.record["facts"]["weight_limit"]["operator"] == enums.OP_LT

    def test_combined_token_moves_scope_and_asks_for_review(self):
        """"combined" in the operator slot lost the comparison entirely."""
        result = read_record({"name": "Test Inn", "facts": {
            "weight_limit": "75 pounds", "weight_limit_operator": "combined"}})
        facts = result.record["facts"]
        assert "weight_limit" not in facts
        assert facts["combined_weight_limit"]["value"] == 75.0
        assert "COMBINED_IN_OPERATOR_SLOT" in review_codes(result.review)


class TestRefusesToGuess:
    """Every legacy shape whose 1.2 form needs a human."""

    def test_species_prose_goes_to_review(self):
        """"pets" alone is not dogs+cats, and parsing here would infer it."""
        result = read_record({"name": "Test Inn",
                              "facts": {"species_allowed": "dogs, cats"}})
        assert "SPECIES_PROSE" in review_codes(result.review)
        assert "species" not in result.record["facts"]

    def test_withheld_prose_goes_to_review(self):
        result = read_record({
            "name": "Test Inn", "facts": {},
            "withheld_fields": {"fee_scope": "the page states an amount without "
                                             "saying whether it is per pet or per room"}})
        assert "WITHHELD_PROSE" in review_codes(result.review)

    def test_blank_approval_is_never_back_dated(self):
        result = read_record({"name": "Test Inn", "facts": {},
                              "approval": {"decision": "", "operator": "",
                                           "approval_date": ""}})
        assert "NO_APPROVAL_DECISION" in review_codes(result.review)
        assert "approval" not in result.record

    def test_missing_approval_block_is_reported(self):
        result = read_record({"name": "Test Inn", "facts": {}})
        assert "NO_APPROVAL_DECISION" in review_codes(result.review)

    def test_qualified_approval_keeps_its_caveat(self):
        result = read_record({"name": "Test Inn", "facts": {}, "approval": {
            "decision": "APPROVED_TIERED_FEE_OMITTED", "operator": "jfields80",
            "approval_date": "2026-07-01"}})
        approval = result.record["approval"]
        assert approval["decision"] == enums.APPROVED_AFTER_CURRENT_REVIEW
        assert approval["caveats"] == ["tiered_fee_omitted"]

    def test_cap_qualifiers_are_never_inherited(self):
        """A room-scoped fee says nothing about its cap's scope."""
        result = read_record({"name": "Test Inn", "facts": {
            "pet_fee": "$25.00", "fee_basis": "per night", "fee_scope": "per room",
            "fee_cap": {"amount": "75.00", "currency": "USD", "basis": "per stay",
                        "evidence_quote": "Max 75 USD per stay"}}})
        cap = result.record["facts"]["fee_cap"]
        assert "scope" not in cap
        assert cap["qualifier_stated"] is False
        assert "CAP_QUALIFIERS_INCOMPLETE" in review_codes(result.review)

    def test_tier_role_is_never_assumed(self):
        result = read_record({"name": "Test Inn", "facts": {"fee_tiers": [
            {"amount": "75.00", "currency": "USD", "condition_type": "stay_length_range",
             "boundary_unit": "nights", "condition_min": 1, "condition_max": 4,
             "role": "ONE_TIME_CHARGE", "basis_stated": False}]}})
        assert "role" not in result.record["facts"]["fee_tiers"][0]
        assert "TIER_ROLE_UNSET" in review_codes(result.review)

    def test_deposit_refundability_is_never_inferred(self):
        result = read_record({"name": "Test Inn", "facts": {"pet_deposit": {
            "amount": "150.00", "currency": "USD",
            "evidence_quote": "Pet deposit is 150 USD"}}})
        assert "DEPOSIT_SHAPE" in review_codes(result.review)


class TestLegacyFeeWithholding:

    def test_fee_conflict_becomes_contradictory(self):
        result = read_record({"name": "Test Inn", "facts": {"fee_conflict": {
            "reason": "conflicting_fee_terms_in_official_source",
            "detail": ["deposit_row_states_75_while_pet_line_states_fees_vary"],
            "evidence_quote": "Deposit Yes. $75.00 Non-refundable Fee"}}})
        entry = result.record["withheld_fields"]["pet_fee"]
        assert entry["reason_code"] == enums.SOURCE_CONTRADICTORY

    def test_fee_withheld_becomes_unrepresentable(self):
        result = read_record({"name": "Test Inn", "facts": {"fee_withheld": {
            "reason": "unrepresentable_fee_range_in_official_source",
            "detail": ["fee_range_75_to_150"], "evidence_quote": "75 to 150 dollars"}}})
        entry = result.record["withheld_fields"]["pet_fee"]
        assert entry["reason_code"] == enums.SCHEMA_CANNOT_REPRESENT


class TestServiceAnimalMove:

    def test_moves_out_of_facts(self):
        result = read_record({"name": "Test Inn",
                              "facts": {"service_animal_exception": "true"}})
        assert "service_animal_exception" not in result.record["facts"]
        assert result.record["service_animal_statement"]["stated"] is True

    def test_never_claims_no_charge_without_a_quote(self):
        result = read_record({"name": "Test Inn",
                              "facts": {"service_animal_exception": "true"}})
        statement = result.record["service_animal_statement"]
        assert statement["charges_stated"] == enums.SERVICE_ANIMAL_NOT_ADDRESSED
        assert "SERVICE_ANIMAL_MOVED" in review_codes(result.review)


class TestCommittedCorpus:
    """The Phase A exit criterion, on real data."""

    @pytest.mark.parametrize("market_id", sorted(PACKAGES))
    def test_every_record_reads(self, market_id):
        document, _ = read_package(load(market_id))
        assert len(document["hotels"]) == EXPECTED_RECORDS[market_id]
        assert document["schema_version"] == enums.POLICY_SCHEMA_VERSION

    @pytest.mark.parametrize("market_id", sorted(PACKAGES))
    def test_every_record_gets_a_canonical_identity_key(self, market_id):
        document, _ = read_package(load(market_id))
        from scripts.pettripfinder.contracts.identity_key import is_canonical_key
        for record in document["hotels"]:
            assert is_canonical_key(record["identity_key"]), record["name"]

    @pytest.mark.parametrize("market_id", sorted(PACKAGES))
    def test_remaining_issues_are_only_undecidable_ones(self, market_id):
        """Nothing the reader COULD have translated is left untranslated.

        After compatibility reading, the only structural gaps left must be the
        two things a machine genuinely cannot decide: which role a tier plays,
        and whether a schedule rung is additive. Any other code appearing here
        means the reader stopped short of a mechanical transformation it should
        have made.
        """
        document, _ = read_package(load(market_id))
        paths = {i.path.split(".", 1)[-1] for i in ps.validate_package(document)}
        undecidable = {"facts.fee_tiers[].role",
                       "facts.fee_pet_schedule.entries[].additive"}
        import re
        normalised = {re.sub(r"\[[^\]]*\]", "[]", p) for p in paths}
        assert normalised <= undecidable, sorted(normalised - undecidable)

    @pytest.mark.parametrize("market_id", sorted(PACKAGES))
    def test_no_legacy_fee_scope_survives(self, market_id):
        document, _ = read_package(load(market_id))
        for record in document["hotels"]:
            scope = (record["facts"].get("pet_fee") or {}).get("scope")
            assert scope in (None, "per_room", "per_pet"), record["name"]

    def test_dayton_per_pet_fees_become_reachable(self):
        """Dayton's eight per-pet fees currently render as nothing at all.

        The renderer matches only ``per_room``, so ``"per pet"`` reaches no
        public surface -- a $30 two-dog stay showing $15. After compatibility
        reading they are canonical ``per_pet`` and can be rendered.
        """
        document, _ = read_package(load("dayton-oh"))
        per_pet = [r for r in document["hotels"]
                   if (r["facts"].get("pet_fee") or {}).get("scope") == "per_pet"]
        assert len(per_pet) == 8

    def test_the_columbus_approval_gap_is_closed(self):
        """It was 26 -- 21 blank decisions plus 5 records with no approval
        block at all. PTF-POLICY-SCHEMA-MIGRATION-001 closed it by REVIEWING
        each record and recording LEGACY_BASELINE_REVIEWED with the date the
        review actually happened. This asserts the gap stays closed: a record
        arriving without a decision would reopen it."""
        _, review = read_package(load("columbus-oh"))
        missing = [r for r in review if r.code == "NO_APPROVAL_DECISION"]
        assert missing == []

    def test_the_combined_operator_overload_is_gone(self):
        """Five records carried a SCOPE in the operator slot -- the word
        "combined" where {lt, lte} belongs. 1.2 gives a combined limit its own
        field, so the overload cannot be expressed any more, and no committed
        record still uses it."""
        total = 0
        for market_id in PACKAGES:
            _, review = read_package(load(market_id))
            total += sum(1 for r in review
                         if r.code == "COMBINED_IN_OPERATOR_SLOT")
        assert total == 0

    def test_review_queue_is_never_silently_empty(self):
        """A reader that reported nothing would mean it had guessed."""
        for market_id in PACKAGES:
            _, review = read_package(load(market_id))
            assert review, market_id

    def test_unsupported_schema_version_is_refused(self):
        with pytest.raises(ValueError):
            read_package({"schema_version": "0.9", "hotels": []})
