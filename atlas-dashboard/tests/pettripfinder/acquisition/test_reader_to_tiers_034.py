"""PTF-MILWAUKEE-READER-TO-TIERS-034.

WHAT THESE TESTS GUARD
----------------------
A reader that can build a fee ladder is a reader that can assert a price
schedule, and the failure mode is not a missing fact -- it is a price the hotel
never quoted. So most of what follows is refusal: fourteen negative controls
say what must NEVER become a structure, and four regression controls say the
simple prose fees the reader already read are untouched.

The one invariant that ties the work order together is at the bottom: the
classification of the twenty-nine held rows must agree, row for row, with what
the reader actually does. A classifier that claims a row is representable and a
reader that then refuses it is a report that cannot be trusted.
"""

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import reader_to_tiers_034 as R
from scripts.pettripfinder.acquisition import tier_corpus_034 as CORPUS
from scripts.pettripfinder.brightdata import policy_reading as PR
from scripts.pettripfinder.contracts import enums
from scripts.pettripfinder.contracts import policy_schema as SCHEMA

from . import authority_freeze as AUTHORITY_FREEZE
from . import locator_freeze as LOCATOR_FREEZE
from . import reader_freeze as READER_FREEZE


def read(text):
    return PR.to_extraction(PR.parse(text), location="test-034")


def tiers(text):
    return read(text).extraction.get("fee_tiers") or []


def store():
    return R.store_doc()


# --------------------------------------------------------------------------- #
# 1 / 2 -- a stay-length ladder, closed and open-ended.
# --------------------------------------------------------------------------- #

#: The commit 034 made. Its freezes are claims about THAT commit, not
#: about everything anyone has done to these files since -- 035 was
#: commissioned to change one of them.
COMMIT_034 = "285e12b"


def _touched_by(commit):
    return subprocess.run(
        ["git", "show", "--pretty=format:", "--name-only", commit],
        cwd=str(REPO), capture_output=True, text=True).stdout.split()


def test_a_two_rung_ladder_is_emitted_as_fee_tiers():
    built = tiers("Other pet information $75(1-4n), $125(5+n) 2 pets max")
    assert [t["amount_cents"] for t in built] == [7500, 12500]
    assert built[0]["condition_min"] == 1 and built[0]["condition_max"] == 4
    assert built[0]["condition_type"] == enums.CONDITION_STAY_LENGTH_RANGE
    assert built[0]["boundary_unit"] == enums.BOUNDARY_NIGHTS
    assert built[0]["role"] == enums.ROLE_REPLACEMENT_PRICE


def test_an_open_ended_rung_states_no_maximum():
    built = tiers("Other pet information $75(1-4n), $125(5+n)")
    assert "condition_max" not in built[1]
    assert built[1]["condition_min"] == 5


def test_a_ladder_replaces_the_simple_fee_rather_than_joining_it():
    """One authoritative price, which is the whole reason to build a ladder."""
    result = read("Other pet information $75(1-4n), $125(5+n)")
    assert "fee_tiers" in result.extraction
    assert "pet_fee" not in result.extraction
    assert "pet_fee" not in result.withheld
    assert any("no single amount is asserted" in note
               for note in result.non_inferences)


# --------------------------------------------------------------------------- #
# 3 / 4 / 5 -- per-animal ladders, and the scope vocabulary.
# --------------------------------------------------------------------------- #

def test_a_pet_count_schedule_is_emitted_with_its_ordinals():
    result = read("Pets welcome. 1 pet $15 per night, 2 pets $25 per night.")
    entries = result.extraction["fee_pet_schedule"]["entries"]
    assert [(e["pet_ordinal"], e["amount_cents"]) for e in entries] == \
        [(1, 1500), (2, 2500)]
    # additive is mandatory in 1.2 and is never inferred: these rungs state
    # each animal's own price, not a surcharge on the one below.
    assert all(entry["additive"] is False for entry in entries)
    assert "pet_fee" not in result.extraction


def test_a_per_pet_scope_is_carried_where_the_rung_states_it():
    built = tiers("Pets welcome. $50 per pet for 1-4 nights, $90 per pet for "
                  "5+ nights.")
    assert all(tier["scope"] == enums.SCOPE_PER_PET for tier in built)


def test_a_per_room_scope_is_carried_where_the_rung_states_it():
    built = tiers("Pets welcome. $50 per room for 1-4 nights, $90 per room "
                  "for 5+ nights.")
    assert all(tier["scope"] == enums.SCOPE_PER_ROOM for tier in built)


def test_scope_is_absent_where_the_surface_does_not_state_it():
    built = tiers("Other pet information $75(1-4n), $125(5+n)")
    assert all("scope" not in tier for tier in built)


# --------------------------------------------------------------------------- #
# 6 -- basis, stated and unstated.
# --------------------------------------------------------------------------- #

def test_basis_stated_is_true_only_when_the_rung_says_it():
    spoken = tiers("Other pet information $75/stay 1-4 nights, $125/stay 5+ "
                   "nights")
    assert all(tier["basis_stated"] is True for tier in spoken)
    assert all(tier["basis"] == enums.BASIS_PER_STAY for tier in spoken)

    silent = tiers("Other pet information $75(1-4n), $125(5+n)")
    assert all(tier["basis_stated"] is False for tier in silent)
    assert all("basis" not in tier for tier in silent)


def test_per_day_is_not_normalised_to_per_night():
    built = tiers("Pets welcome. $20/day for 1-4 nights, $30/day for 5+ "
                  "nights.")
    assert all(tier["basis"] == enums.BASIS_PER_DAY for tier in built)
    assert enums.BASIS_PER_DAY != enums.BASIS_PER_NIGHT


def test_an_unsupported_basis_is_neither_invented_nor_dropped():
    """"$75 per 7 day stay" names a recurrence FEE_BASES has no member for.

    Emitting the amount with ``basis_stated: false`` would say the source named
    no recurrence when it named one this schema cannot hold, so the whole
    ladder is refused and the words survive in the evidence.
    """
    result = read("Pets welcome. $75 per 7 day stay for 1-4 nights, $125 per "
                  "7 day stay for 5+ nights.")
    assert "fee_tiers" not in result.extraction
    assert "pet_fee" not in result.extraction
    assert result.withheld["pet_fee"] == enums.SCHEMA_CANNOT_REPRESENT
    assert "UNSUPPORTED_BASIS" in \
        PR.parse_stay_bands("Pets welcome. $75 per 7 day stay for 1-4 nights, "
                            "$125 per 7 day stay for 5+ nights.").problems


# --------------------------------------------------------------------------- #
# 7 / 8 -- caps.
# --------------------------------------------------------------------------- #

def test_a_capped_nightly_fee_keeps_its_price_and_its_cap_apart():
    result = read("Non-refundable 25 USD nightly for up to 2 pets. Max 75 USD "
                  "per stay.")
    assert result.extraction["pet_fee"] == 2500
    assert result.extraction["fee_cap"]["amount_minor"] == 7500
    assert "fee_tiers" not in result.extraction


def test_a_ceiling_never_becomes_a_rung():
    """CEILING != PRICE. A ladder whose rungs are ceilings prices nothing."""
    result = read("Pets allowed with nonrefundable fee. Up to 75 dollars for "
                  "1 to 6 nights, up to 150 dollars for 7+ nights.")
    assert "fee_tiers" not in result.extraction
    assert "pet_fee" not in result.extraction
    assert "CEILING_NOT_PRICE" in PR.parse_stay_bands(
        "Up to 75 dollars for 1 to 6 nights, up to 150 dollars for 7+ nights."
    ).problems


# --------------------------------------------------------------------------- #
# 9 / 10 / 11 / 12 -- the ladders that must stay unsafe.
# --------------------------------------------------------------------------- #

def test_overlapping_bands_are_refused():
    text = ("Pets Welcome 2 pets 50lbs max per pet per room with "
            "non-refundable fee.0-5 nights $75 5+ $150")
    assert "OVERLAPPING_BANDS" in PR.parse_stay_bands(text).problems
    result = read(text)
    assert "fee_tiers" not in result.extraction
    assert result.withheld["pet_fee"] == enums.SCHEMA_CANNOT_REPRESENT


def test_a_gap_between_bands_is_refused():
    text = ("Dogs are allowed with a 50 USD nonrefundable fee, per pet, for "
            "stays 1 to 6 nights, 150 USD for stays over 7 nights.")
    assert "GAP_BETWEEN_BANDS" in PR.parse_stay_bands(text).problems
    assert "fee_tiers" not in read(text).extraction


def test_a_contradictory_basis_stays_unsafe():
    result = read("Pets are welcome. We love pets, and the pet fee is 75.00 "
                  "USD per stay. A cleaning fee of 250.00 will be assessed "
                  "for the discovery of an unauthorized pet. Pet fee per "
                  "night: 75 USD")
    assert "fee_tiers" not in result.extraction
    assert "fee_basis" not in result.extraction
    assert result.withheld["pet_fee"] == enums.SCHEMA_CANNOT_REPRESENT


def test_an_additional_charge_role_keeps_the_ladder_ambiguous():
    text = ("Pet Fees 1-6 nights : $100 / STAY 7-30 nights + additional "
            "cleaning fee : $200 / STAY")
    assert "AMBIGUOUS_ROLE" in PR.parse_stay_bands(text).problems
    result = read(text)
    assert "fee_tiers" not in result.extraction
    assert "pet_fee" not in result.extraction


def test_a_cleaning_charge_never_becomes_a_rung_of_the_pet_price():
    result = read("Pet Fees 1-6 nights : $100 / STAY 7-30 nights + additional "
                  "cleaning fee : $200 / STAY")
    assert "cleaning_fee" not in result.extraction
    assert "fee_tiers" not in result.extraction


# --------------------------------------------------------------------------- #
# 13 / 14 / 15 -- conditions 1.2 has no field for.
# --------------------------------------------------------------------------- #

def test_a_room_type_condition_stays_held():
    text = ("It is an additional $20 fee per dog, per night ($30/dog/night in "
            "Suites) and we have a maximum of two (2) dogs per room.")
    assert "fee_tiers" not in read(text).extraction
    assert "pet_fee" not in read(text).extraction


def test_a_species_conditioned_price_stays_held():
    text = ("Pets welcome. Dogs $50 per night for 1-4 nights, cats $30 per "
            "night for 1-4 nights.")
    assert "fee_tiers" not in read(text).extraction


def test_a_weight_conditioned_price_stays_held():
    text = ("Pets welcome. $50 per stay under 25 lbs for 1-4 nights, $100 per "
            "stay over 25 lbs for 5+ nights.")
    assert "WEIGHT_CONDITIONED_PRICE" in PR.parse_stay_bands(text).problems
    assert "fee_tiers" not in read(text).extraction


def test_a_weight_limit_printed_beside_a_price_is_not_a_priced_condition():
    """Hilton ends its field "(2max under 75lbs)", which is a LIMIT.

    Reading that as weight-conditioned pricing held two readable ladders for a
    condition neither surface states.
    """
    built = tiers("Other pet information $75/stay 1-4 nights, $125/stay 5+ "
                  "nights (2max under 75lbs)")
    assert [tier["amount_cents"] for tier in built] == [7500, 12500]


# --------------------------------------------------------------------------- #
# 16 / 17 / 18 -- the corpus, whole, and the prose that must not move.
# --------------------------------------------------------------------------- #

def test_every_corpus_case_gets_the_answer_it_must_get():
    failed = []
    for case in CORPUS.cases():
        result = read(case.text)
        for field in case.must_extract:
            if field not in result.extraction:
                failed.append("%s: %s not extracted" % (case.case_id, field))
        for field in case.must_not_extract:
            if field in result.extraction:
                failed.append("%s: %s extracted" % (case.case_id, field))
        for field in case.must_withhold:
            if field not in result.withheld:
                failed.append("%s: %s not withheld" % (case.case_id, field))
        built = result.extraction.get("fee_tiers") or []
        if case.tiers:
            got = tuple((tier["amount_cents"], tier["condition_min"],
                         tier.get("condition_max")) for tier in built)
            if got != case.tiers:
                failed.append("%s: tiers %s" % (case.case_id, got))
        rungs = (result.extraction.get("fee_pet_schedule") or {}).get("entries") or []
        if case.rungs:
            got = tuple((entry["pet_ordinal"], entry["amount_cents"])
                        for entry in rungs)
            if got != case.rungs:
                failed.append("%s: rungs %s" % (case.case_id, got))
    assert failed == []


def test_the_corpus_carries_the_controls_it_claims_to():
    kinds = [case.kind for case in CORPUS.cases()]
    assert kinds.count(CORPUS.NEGATIVE) == 14
    assert kinds.count(CORPUS.REGRESSION) == 4


def test_simple_prose_fees_are_untouched():
    for text, amount, basis in (
            ("Pets Welcome. Pet fee $25 per night.", 2500,
             enums.BASIS_PER_NIGHT),
            ("Pets welcome. A $150 non-refundable pet fee per stay applies.",
             15000, enums.BASIS_PER_STAY),
            ("Pets welcome. The Pet Friendly rate is 35.00 USD per day.",
             3500, enums.BASIS_PER_DAY)):
        result = read(text)
        assert result.extraction["pet_fee"] == amount, text
        assert result.extraction["fee_basis"] == basis, text
        assert "fee_tiers" not in result.extraction, text


# --------------------------------------------------------------------------- #
# 19 / 20 / 21 / 22 -- cost, schema, authority, publication.
# --------------------------------------------------------------------------- #

def test_the_whole_repair_needed_no_provider_call():
    cost = R.cost()
    assert cost["provider_calls"] == 0
    assert cost["firecrawl_calls"] == 0
    assert cost["browser_api_calls"] == 0
    assert cost["web_unlocker_calls"] == 0
    assert cost["brightdata_spend_usd"] == 0.0


def test_this_work_order_did_not_change_the_policy_schema():
        # Restated by PTF-ST-LOUIS-PUBLICATION-SCHEMA-DECISIONS-010, which made
        # an authorised ADDITIVE amendment to 1.3. What this work order claimed
        # is that IT did not change the policy schema -- not that the schema is
        # frozen for all time. The durable form of that claim is the committed
        # artifact's own version, which is a fact about this work order's
        # output, plus the requirement that it still speaks a canonical schema.
    assert store()["policy_schema_version"] == "1.2"
    assert enums.is_canonical_policy_schema(store()["policy_schema_version"])


def test_no_milwaukee_policy_authority_exists():
    doc = store()
    assert not doc.get("authority_written")
    # NARROWED. This claimed "reader to tiers 034 created no Milwaukee authority",
    # which was true and still is -- but read against the live filesystem
    # it became "Milwaukee may never have one", and the founder approved
    # 96 records in PTF-MILWAUKEE-FOUNDER-DECISION-036. The historical
    # claim is checked against the commit; the standing claim -- that
    # authority is recorded and never live inventory -- is checked too.
    AUTHORITY_FREEZE.assert_commit_created_no_authority("285e12b")
    AUTHORITY_FREEZE.assert_authority_is_recorded_not_live()


def test_nothing_is_published_and_nothing_is_approved():
    doc = store()
    assert all(not row.get("published") for row in doc["items"])
    assert all(not row.get("founder_approved") for row in doc["items"])
    assert R.counters()["published"] == 0


# --------------------------------------------------------------------------- #
# The structures themselves, and the store they landed in.
# --------------------------------------------------------------------------- #

def test_every_emitted_structure_validates_against_schema_1_2():
    """The point of the work order: 1.2 could always hold these.

    Scoped to the two structures 034 builds. ``fee_cap`` is left exactly as it
    was -- this reader has always written it in the legacy ``amount_minor``
    shape, as it writes ``pet_fee`` as a bare integer, and converting either
    would rewrite rows for a reason that has nothing to do with fee ladders.
    """
    checked = 0
    for row in store()["items"]:
        facts = row.get("proposed_facts") or {}
        subset = {key: facts[key] for key in
                  ("fee_tiers", "fee_pet_schedule") if key in facts}
        if not subset:
            continue
        checked += 1
        assert SCHEMA.validate_facts(subset) == (), row["identity_key"]
    assert checked >= 20


def test_no_row_carries_a_ladder_and_a_simple_fee_at_once():
    for row in store()["items"]:
        facts = row.get("proposed_facts") or {}
        if facts.get("fee_tiers") or facts.get("fee_pet_schedule"):
            assert "pet_fee" not in facts, row["identity_key"]


def test_the_store_moved_only_by_changing_readings():
    integration = json.loads(
        (R.REPORTS / "ptf_milwaukee_store_integration_025.json")
        .read_text(encoding="utf-8-sig"))
    assert integration["rows_after"] == 117
    assert integration["added"] == []
    assert integration["removed"] == []
    assert integration["duplicates"] == []


def test_the_counters_reconcile_over_the_whole_census():
    counters = R.counters()
    assert counters["census_total"] == 147
    assert counters["sum_of_final_states"] == 147
    assert counters["active_eligible"] == 133
    assert counters["observed"] == 117
    assert counters["store_rows"] == 117
    assert counters["first_publication_candidates"] == (
        counters["founder_review_ready"] + counters["refusal_founder_review"])


def test_the_classification_agrees_with_what_the_reader_actually_does():
    """A report that claims a row is representable and is then refused is a
    report nobody can act on."""
    differential = {row["identity_key"]: row for row in R.held_differential()}
    for row in R.classification():
        assert row["representable_in_1_2"] == \
            differential[row["identity_key"]]["review_state_changes"], \
            row["identity_key"]


def test_every_row_that_stays_held_says_why():
    for row in R.held_differential():
        if not row["review_state_changes"]:
            assert row["reason"].strip(), row["identity_key"]


def test_the_corpus_wide_change_removes_no_field_from_any_record():
    doc = R.corpus_wide_dry_run()
    assert doc["blocks_scanned"] > 100
    assert doc["fields_removed"] == {}
    for change in doc["affected"]:
        # A change may also be a REASON becoming more specific: 035 repaired
        # the recurring-charge detector and one row's withholding moved from
        # SOURCE_AMBIGUOUS to SCHEMA_CANNOT_REPRESENT, which adds no key.
        reason_changed = change["old_withheld"] != change["new_withheld"]
        assert (change["added_fields"] or change["withheld_added"]
                or reason_changed), change["slug"]


# --------------------------------------------------------------------------- #
# Freezes.
# --------------------------------------------------------------------------- #

def test_routing_source_selection_and_the_locator_are_unchanged():
    for path in ("atlas-dashboard/scripts/pettripfinder/acquisition/routes.json",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/registry.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/router.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/providers.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/readers.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/source_discovery.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/source_selection.py",
                 "atlas-dashboard/scripts/pettripfinder/brightdata/policy_surface.py",
                 "atlas-dashboard/scripts/pettripfinder/brightdata/policy_locator.py",
                 "atlas-dashboard/scripts/pettripfinder/brightdata/marriott_surface.py",
                 "atlas-dashboard/scripts/pettripfinder/contracts/policy_schema.py",
                 "atlas-dashboard/scripts/pettripfinder/contracts/enums.py",
                 "atlas-dashboard/launch_packages/pettripfinder/identity_census",
                 "atlas-dashboard/launch_packages/pettripfinder/milwaukee_final_partition_001.json"):
        assert not any(name == path or name.startswith(path.rstrip("/") + "/")
                       for name in _touched_by(COMMIT_034)), \
            "%s was modified by 034" % path
    LOCATOR_FREEZE.assert_locator_surface_unchanged()


def test_the_readers_own_safeguards_still_hold():
    READER_FREEZE.assert_reader_protections_unchanged()
