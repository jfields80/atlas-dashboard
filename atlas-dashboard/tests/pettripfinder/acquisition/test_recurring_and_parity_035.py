"""PTF-MILWAUKEE-RECURRING-CHARGE-AND-MARRIOTT-PARITY-035.

WHAT THESE TESTS GUARD
----------------------
Two things, and the second is the one that matters.

The first is a rule that had never run: two literal BACKSPACE characters where
``\\b`` was meant. The repair is two characters, so the tests here are mostly
about what the repaired rule must NOT do -- a parking charge billed daily is
not a pet charge, a one-off charge does not become recurring, and per_day is
still not per_night.

The second is that a reader which can read MORE is not automatically a reader
that should be preferred. The generic reader reads Courtyard Downtown's pet fee
where the Marriott reader withholds it -- and it was also about to publish that
page's $5-per-DAY cleaning charge as a bare "$5.00". The tests pin both halves:
the pet fee is read, and the recurring cleaning charge is refused by BOTH
readers rather than published cheap.
"""

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import recurring_and_parity_035 as R
from scripts.pettripfinder.brightdata import marriott_surface as MS
from scripts.pettripfinder.brightdata import policy_reading as PR
from scripts.pettripfinder.contracts import enums

from . import authority_freeze as AUTHORITY_FREEZE
from . import locator_freeze as LOCATOR_FREEZE
from . import reader_freeze as READER_FREEZE


def read(text):
    return PR.to_extraction(PR.parse(text), location="test-035")


def read_marriott(text):
    return MS.to_extraction(MS.parse_policy_block(text, locator_id="test-035"),
                            location="test-035")


def store():
    return R.R34.store_doc()


# --------------------------------------------------------------------------- #
# 1 / 2 -- the defect itself.
# --------------------------------------------------------------------------- #

def test_the_intended_pattern_matches_recurring_language():
    assert PR._RECURRING_WORD_RE.pattern == R.INTENDED_RECURRING_PATTERN
    for text in ("a $20 daily pet fee", "charged nightly", "Daily Pet Fee 5 USD"):
        assert PR._RECURRING_WORD_RE.search(text), text
    # ...and still only as whole words.
    assert not PR._RECURRING_WORD_RE.search("dailyish")


def test_no_reader_pattern_carries_a_control_character():
    """The defect class, not just this instance.

    A heredoc turns ``\\b`` into a backspace silently, and the result compiles,
    imports and matches nothing. Every compiled pattern in both readers is
    checked, so the next one is caught by a test rather than by a market.
    """
    import re as _re
    for module in (PR, MS):
        for name in dir(module):
            value = getattr(module, name)
            if not isinstance(value, _re.Pattern):
                continue
            for char in value.pattern:
                assert ord(char) >= 32 or char in "\n\t", \
                    "%s.%s carries %r" % (module.__name__, name, char)


# --------------------------------------------------------------------------- #
# 3 to 9 -- what the repaired rule does, and does not do.
# --------------------------------------------------------------------------- #

def test_a_recurring_pet_charge_beside_a_one_off_is_not_published():
    result = read("Daily Pet Fee 5 USD Per Pet along with Non-Refundable Pet "
                  "Fee of 100 USD required at check-in.")
    assert "pet_fee" not in result.extraction
    assert result.withheld["pet_fee"] == enums.SCHEMA_CANNOT_REPRESENT


def test_a_one_time_charge_stays_one_time():
    result = read("Pets welcome. A $150 non-refundable pet fee per stay applies.")
    assert result.extraction["pet_fee"] == 15000
    assert result.extraction["fee_basis"] == enums.BASIS_PER_STAY
    assert result.withheld == {}


def test_a_recurring_cleaning_charge_is_not_the_pet_fee():
    result = read("Pet Policy Pets Welcome Daily cleaning fee of $5/ day in "
                  "addition to the one time non-refundable pet fee "
                  "Non-Refundable Pet Fee Per Stay: $50.00")
    assert result.extraction["pet_fee"] == 5000
    assert result.extraction["fee_basis"] == enums.BASIS_PER_STAY
    assert "cleaning_fee" not in result.extraction
    assert result.withheld["cleaning_fee"] == enums.SCHEMA_CANNOT_REPRESENT


def test_a_recurring_charge_that_is_not_a_pets_is_excluded():
    result = read("Pets allowed. Self-parking is $35 daily. A nightly resort "
                  "fee of $29 applies.")
    assert "pet_fee" not in result.extraction
    assert "cleaning_fee" not in result.extraction
    # The words are there and the rule sees them; pet context is what stops it.
    assert PR._RECURRING_WORD_RE.search("Self-parking is $35 daily")
    assert result.withheld.get("pet_fee") == enums.SOURCE_SILENT


def test_per_day_stays_per_day_and_never_becomes_per_night():
    result = read("Pets welcome. The pet fee is 35.00 USD per day.")
    assert result.extraction["fee_basis"] == enums.BASIS_PER_DAY
    assert result.extraction["fee_basis"] != enums.BASIS_PER_NIGHT
    assert enums.BASIS_PER_DAY != enums.BASIS_PER_NIGHT
    # A charge already carrying a daily basis is represented, so the recurring
    # rule is guarded off rather than double-reporting it.
    assert result.withheld == {}


def test_a_recurring_fee_with_a_cap_keeps_the_cap_a_cap():
    result = read("Pets welcome. A $20 daily pet fee applies, up to a maximum "
                  "of $100 per stay.")
    assert result.extraction["fee_cap"]["amount_minor"] == 10000
    assert "pet_fee" not in result.extraction
    # And the silence is not claimed: the page named a fee this reader could
    # not read, which is not the same as a page that named none.
    assert result.withheld["pet_fee"] == enums.SCHEMA_CANNOT_REPRESENT


def test_the_recurring_corpus_answers_are_stable():
    rows = {row["case_id"]: row for row in R.recurring_corpus()}
    assert rows["R1-daily-plus-one-time"]["new_withheld"]["pet_fee"] == \
        enums.SCHEMA_CANNOT_REPRESENT
    assert rows["R5-one-time-only"]["new_facts"]["pet_fee"] == 15000
    assert rows["R7-recurring-already-represented"]["differs"] is False
    assert rows["R6-unrelated-recurring-charges"]["differs"] is False


# --------------------------------------------------------------------------- #
# 10 -- the one row in the market that moves.
# --------------------------------------------------------------------------- #

def test_the_woodspring_row_is_held_for_the_right_reason():
    row = next(r for r in store()["items"]
               if r["identity_key"] == "woodspring suites milwaukee menomonee falls")
    assert row["review_status"] == "HELD_SCHEMA_CANNOT_REPRESENT"
    assert row["withheld_fields"]["pet_fee"] == "SCHEMA_CANNOT_REPRESENT"
    assert "pet_fee" not in row["proposed_facts"]
    # The rest of the policy survives the demotion.
    assert row["proposed_facts"]["weight_limit"]["value"] == 50.0
    assert row["proposed_facts"]["pet_count_limit"] == 2


def test_exactly_one_row_in_the_market_changed():
    """One row, one reason, and not one fact.

    Asserted on the READING rather than on the store's current status: the
    store has since been rebuilt, so a before-state read from it would be the
    state this very change produced.
    """
    summary = R.differential_summary()
    assert summary["rows_changed"] == 1
    assert summary["identities"] == [
        "woodspring suites milwaukee menomonee falls"]
    assert summary["facts_added"] == {}
    assert summary["facts_removed"] == {}
    row = summary["rows"][0]
    assert row["old_withheld"]["pet_fee"] == enums.SOURCE_AMBIGUOUS
    assert row["new_withheld"]["pet_fee"] == enums.SCHEMA_CANNOT_REPRESENT
    assert row["review_state_after"] == "HELD_SCHEMA_CANNOT_REPRESENT"


# --------------------------------------------------------------------------- #
# 11 to 13 -- the parity audit and Courtyard.
# --------------------------------------------------------------------------- #

def test_the_two_readers_agree_wherever_the_semantics_are_equivalent():
    summary = R.parity_summary()
    assert summary["rows_compared"] == 28
    assert summary["by_classification"].get(R.EQUIVALENT, 0) == 24
    assert summary["by_classification"].get(R.CONFLICT_REQUIRES_HOLD, 0) == 0
    assert summary["by_classification"].get(R.MARRIOTT_BETTER, 0) == 0


def test_every_marriott_difference_is_the_generic_reader_reading_more():
    for row in R.marriott_parity():
        if row["classification"] == R.EQUIVALENT:
            continue
        assert row["classification"] == R.GENERIC_BETTER, row["identity_key"]
        for difference in row["differences"]:
            assert difference["kind"] != "VALUE_CONFLICT", row["identity_key"]


def test_courtyard_downtown_carries_the_pet_fee_and_refuses_the_cleaning_charge():
    case = R.courtyard_case()
    generic = case["generic_after"]
    assert generic["extraction"]["pet_fee"] == 5000
    assert generic["extraction"]["fee_basis"] == enums.BASIS_PER_STAY
    assert "cleaning_fee" not in generic["extraction"]
    assert generic["withheld"]["cleaning_fee"] == enums.SCHEMA_CANNOT_REPRESENT
    # Before 035 the generic reader would have published the recurring charge
    # as a flat amount. That is the half of 034's note that was wrong.
    assert case["generic_before"]["extraction"].get("cleaning_fee") == 500


def test_a_five_dollar_daily_cleaning_fee_can_never_replace_the_pet_fee():
    for reader in (read, read_marriott):
        result = reader("Pet Policy Pets Welcome Daily cleaning fee of $5/ day "
                        "in addition to the one time non-refundable pet fee "
                        "Non-Refundable Pet Fee Per Stay: $50.00")
        assert result.extraction.get("pet_fee") != 500
        assert result.extraction.get("cleaning_fee") is None


# --------------------------------------------------------------------------- #
# 14 to 19 -- the Marriott protections that must survive.
# --------------------------------------------------------------------------- #

def test_a_tiered_marriott_policy_is_still_refused():
    result = read_marriott(
        "Pet Policy Pets Welcome 2 pets 50lbs max per pet per room with "
        "non-refundable fee.0-5 nights $75 5+ $150 Non-Refundable Pet Fee Per "
        "Stay: $75.00 Maximum Pet Weight: 50.0lbs")
    assert "pet_fee" not in result.extraction
    assert result.withheld["pet_fee"] == enums.SCHEMA_CANNOT_REPRESENT


def test_the_021_understatement_defect_cannot_return():
    """A charge the reader parsed and no field carries still withholds the fee.

    021/022 added that guard because publishing the component that happened to
    parse understates the stay while looking complete.
    """
    result = read_marriott(
        "Pet Policy Pets Welcome $30 per night pet fee Non-Refundable Pet Fee "
        "Per Stay: $150.00 Maximum Number of Pets in Room: 2")
    assert "pet_fee" not in result.extraction
    assert result.withheld["pet_fee"] == enums.SCHEMA_CANNOT_REPRESENT


def test_multiple_charge_roles_never_merge_into_one_price():
    """Two charges, two roles -- or a withholding. Never one merged number.

    The readers answer differently here and both answers are safe: the generic
    one separates the roles, and the Marriott one withholds because its
    cleaning wording is bound to a structured row this surface does not have.
    What neither may do is publish one charge as though it were the price.
    """
    text = ("Pets Welcome $75 per stay cleaning fee. Non-Refundable Pet Fee "
            "Per Stay: $50.00")
    generic = read(text)
    assert generic.extraction["cleaning_fee"] == 7500
    assert generic.extraction["pet_fee"] == 5000

    marriott = read_marriott(text)
    assert marriott.extraction.get("pet_fee") != 7500
    if "pet_fee" not in marriott.extraction:
        assert marriott.withheld["pet_fee"] == enums.SCHEMA_CANNOT_REPRESENT


def test_a_marriott_fee_cap_is_still_a_cap():
    result = read_marriott(
        "Pets Welcome Non-Refundable Pet Fee Per Night: $25.00 Maximum pet fee "
        "$75 per stay Maximum Number of Pets in Room: 2")
    assert result.extraction.get("pet_fee") != 7500


def test_ambiguous_marriott_pricing_is_still_held():
    row = next(r for r in R.marriott_parity()
               if r["identity_key"] == "sheraton milwaukee brookfield hotel")
    assert row["store_review_state"] == "HELD_SCHEMA_CANNOT_REPRESENT"
    assert row["classification"] == R.EQUIVALENT


def _code_lines(module):
    """A module's CODE, with comments and docstring prose removed.

    Both readers cite the page that produced a defect in their comments, which
    is how this codebase documents a rule. What must never exist is a rule that
    BRANCHES on a property or a market, so the check is on code.
    """
    import inspect
    source = inspect.getsource(module)
    out, in_doc = [], False
    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        if stripped.count('"""') == 1:
            in_doc = not in_doc
            continue
        if in_doc:
            continue
        out.append(line.lower())
    return "\n".join(out)


def test_neither_reader_branches_on_a_property_or_a_market():
    for module in (PR, MS):
        code = _code_lines(module)
        for token in ("milwaukee", "woodspring", "courtyard", "clarion",
                      "country inn", "hyatt place", "hampton inn"):
            assert token not in code, "%s branches on %r" % (module.__name__,
                                                             token)


def test_the_schema_version_is_still_1_2():
    assert enums.POLICY_SCHEMA_VERSION == "1.2"
    assert store()["policy_schema_version"] == "1.2"
    assert R.freezes()["paths"][
        "atlas-dashboard/scripts/pettripfinder/contracts/policy_schema.py"] == "clean"


def test_the_whole_pass_needed_no_provider_call():
    cost = R.cost()
    assert cost["provider_calls"] == 0
    assert cost["firecrawl_calls"] == 0
    assert cost["browser_api_calls"] == 0
    assert cost["web_unlocker_calls"] == 0
    assert cost["brightdata_spend_usd"] == 0.0


def test_no_capture_artifact_was_rewritten():
    """Every row still points at the block it always pointed at."""
    for row in store()["items"]:
        block, path = R.R34.block_for(row)
        assert block, path
    changed = subprocess.run(
        ["git", "status", "--porcelain", "--",
         "atlas-dashboard/launch_packages/pettripfinder/markets/reports/"
         "ptf_marriott_milwaukee_run_020.json",
         "atlas-dashboard/launch_packages/pettripfinder/markets/reports/"
         "ptf_marriott_closure_022.json"],
        cwd=str(REPO), capture_output=True, text=True).stdout.strip()
    assert changed == ""


def test_routing_the_locator_and_discovery_are_unchanged():
    freezes = R.freezes()
    assert freezes["all_clean"], freezes["paths"]
    LOCATOR_FREEZE.assert_locator_surface_unchanged()


def test_the_readers_own_safeguards_still_hold():
    READER_FREEZE.assert_reader_protections_unchanged()


def test_no_authority_exists_and_nothing_is_published():
    doc = store()
    assert not doc.get("authority_written")
    assert all(not row.get("published") for row in doc["items"])
    assert all(not row.get("founder_approved") for row in doc["items"])
    # NARROWED. This claimed "recurring and parity 035 created no Milwaukee authority",
    # which was true and still is -- but read against the live filesystem
    # it became "Milwaukee may never have one", and the founder approved
    # 96 records in PTF-MILWAUKEE-FOUNDER-DECISION-036. The historical
    # claim is checked against the commit; the standing claim -- that
    # authority is recorded and never live inventory -- is checked too.
    AUTHORITY_FREEZE.assert_commit_created_no_authority("69538f6")
    AUTHORITY_FREEZE.assert_authority_is_recorded_not_live()


def test_the_projection_is_deterministic_on_a_second_run():
    """Re-projecting the store must produce the same rows, not drift."""
    first = R.store_dry_run()
    second = R.store_dry_run()
    assert first["rows_after"] == second["rows_after"] == 117
    for result in (first, second):
        assert result["added"] == []
        assert result["removed"] == []
        assert result["duplicates"] == []
        assert result["conflicts"] == []
        assert result["changed_facts"] == []


def test_the_counters_reconcile_and_the_candidate_count_is_measured():
    counters = R.counters()
    assert counters["census_total"] == 147
    assert counters["sum_of_final_states"] == 147
    assert counters["active_eligible"] == 133
    assert counters["observed"] == 117
    assert counters["published"] == 0
    assert counters["first_publication_candidates"] == (
        counters["founder_review_ready"] + counters["refusal_founder_review"])


def test_no_ready_row_carries_a_fee_the_vocabulary_could_not_represent():
    """The publication-readiness question, asserted rather than asserted about."""
    readiness = R.publication_readiness()
    assert readiness["blockers"] == []
    assert readiness["verdict"] == "READY_FOR_FIRST_PUBLICATION"
