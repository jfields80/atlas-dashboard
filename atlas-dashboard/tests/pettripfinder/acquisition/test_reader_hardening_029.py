"""PTF-GENERIC-READER-BEST-WESTERN-HARDENING-029.

WHAT THESE TESTS GUARD
----------------------
A reader that learns to read more must not learn to read wrong, and the two
look identical in a summary. So the protections outnumber the recoveries here:
every one of tiered, banded, multi-component, contradictory-basis, amenity-only,
service-animal-only and the room-rate hole has its own case, and the room-rate
cases matter most because the repair touched the guard that keeps that hole
shut.

The two recovered surfaces are read from the artifacts 028 persisted, by hash,
so a test failure means the reader changed and never that the page did.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import premium_resolution_028 as P28
from scripts.pettripfinder.acquisition import reader_corpus_029 as CORPUS
from scripts.pettripfinder.acquisition import reader_hardening_029 as R
from scripts.pettripfinder.brightdata import policy_reading as PR
from scripts.pettripfinder.contracts import enums


def read(block: str):
    return PR.to_extraction(PR.parse(block), location="milwaukee-wi")


def target_case(case_id: str):
    return next(c for c in CORPUS.CASES if c.case_id == case_id)


# --------------------------------------------------------------------------- #
# The targets are derived, not chosen.
# --------------------------------------------------------------------------- #

def test_the_two_under_read_targets_are_derived_from_028():
    found = R.targets()
    assert len(found) == 2
    for key in found:
        row = next(r for r in P28.journal_rows() if r["identity_key"] == key)
        assert row["brand"] == "BEST_WESTERN"
        assert row["publication_grade"] is True
        assert P28.premium_audit(row)["verdict"] == \
            P28.PREMIUM_ACCESS_BUT_READER_OR_LOCATOR_ISSUE


# --------------------------------------------------------------------------- #
# 1 / 2 / 3 -- count, weight, fee.
# --------------------------------------------------------------------------- #

def test_a_spelled_out_count_with_a_species_parses():
    """"allow up to two dogs" -- no figures, no "max", no per-room scope."""
    result = read("Pets welcome. We allow up to two dogs in a limited "
                  "number of rooms.")
    assert result.extraction["pet_count_limit"] == 2
    # No scope is invented: the surface did not say per room.
    assert "pet_count_scope" not in result.extraction


def test_a_size_limit_stated_with_a_copula_parses():
    """"The size limit for any one dog shall be 80 pounds"."""
    result = read("Pets welcome. The size limit for any one dog shall be "
                  "80 pounds.")
    assert result.extraction["weight_limit"] == {"value": 80.0, "unit": "lb"}


def test_a_charge_the_surface_names_as_the_pets_parses():
    """The amount always matched; the rate-marker guard threw it away."""
    result = read("Pets welcome. The Pet Friendly rate is 35.00 USD per day.")
    assert result.extraction["pet_fee"] == 3500
    assert result.extraction["fee_currency"] == "USD"
    assert result.extraction["fee_basis"] == enums.BASIS_PER_DAY


@pytest.mark.parametrize("case_id", ["T1-multi-component-daily-rate",
                                     "T2-single-daily-rate"])
def test_the_persisted_targets_now_carry_count_weight_and_fee(case_id):
    case = target_case(case_id)
    result = read(case.block())
    assert result.extraction["pets_allowed"] is True
    assert result.extraction["pet_count_limit"] == 2
    assert result.extraction["weight_limit"] == {"value": 80.0, "unit": "lb"}
    assert result.extraction["pet_fee"] in (3000, 3500)
    assert result.extraction["fee_basis"] == enums.BASIS_PER_DAY


# --------------------------------------------------------------------------- #
# 4 -- per day.
# --------------------------------------------------------------------------- #

def test_per_day_follows_the_published_contract_and_invents_nothing():
    decision = R.per_day_decision()
    assert decision["decision"] == R.EXISTING_EQUIVALENCE
    assert decision["per_day_in_published_fee_bases"] is True
    assert decision["per_day_accepted_by_the_store_builder"] is True
    assert decision["new_vocabulary_created"] is False


def test_per_day_is_never_normalised_into_per_night():
    """The contract keeps them distinct and this layer does not choose."""
    assert enums.BASIS_PER_DAY != enums.BASIS_PER_NIGHT
    daily = read("Pets welcome. The Pet Friendly rate is 30.00 USD per day.")
    nightly = read("Pets welcome. The Pet Friendly rate is 30.00 USD per night.")
    assert daily.extraction["fee_basis"] == enums.BASIS_PER_DAY
    assert nightly.extraction["fee_basis"] == enums.BASIS_PER_NIGHT


# --------------------------------------------------------------------------- #
# 5 / 6 / 7 -- the fee protections.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("case_id", ["P1-tiered-fee", "P2-banded-fee",
                                     "P3-multi-component-fee"])
def test_a_fee_the_schema_cannot_hold_is_still_withheld(case_id):
    case = target_case(case_id)
    result = read(case.block())
    assert "pet_fee" not in result.extraction
    # 034 gave the banded case a structure. The claim 029 was making -- that
    # no single amount is asserted for a fee the vocabulary cannot hold -- is
    # unchanged; where the amount IS holdable, it is held as a ladder.
    assert ("pet_fee" in result.withheld
            or result.extraction.get("fee_tiers"))


def test_a_contradicted_basis_is_still_withheld():
    case = target_case("P4-contradictory-basis")
    result = read(case.block())
    assert result.extraction["pet_fee"] == 2000
    assert "fee_basis" not in result.extraction
    assert result.withheld["fee_basis"] == enums.SOURCE_CONTRADICTORY


def test_a_stated_ceiling_is_still_not_the_price():
    case = target_case("C4-capped-fee")
    result = read(case.block())
    assert result.extraction["pet_fee"] == 2000
    assert result.extraction["fee_cap"]["amount_minor"] == 10000


# --------------------------------------------------------------------------- #
# The room-rate hole -- the guard the fee repair had to work around.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("case_id", ["P7-room-rate-with-refusal",
                                     "P8-room-rate-member",
                                     "P9-room-rate-strikethrough"])
def test_the_room_rate_hole_stays_shut(case_id):
    case = target_case(case_id)
    result = read(case.block())
    assert "pet_fee" not in result.extraction


def test_a_clause_closing_word_stops_the_pet_word_naming_the_rate():
    """"No Pets Allowed ... Discounted rate" is two clauses, not one name.

    This is the whole discrimination the fee repair rests on: the pet word must
    MODIFY the charge noun, and a policy verb between them ends the pet
    statement.
    """
    assert PR._PET_NAMED_CHARGE_RE.search(
        "The Pet Friendly rate is 35.00 USD per day")
    assert not PR._PET_NAMED_CHARGE_RE.search(
        "No Pets Allowed Discounted rate: $160 USD /night")
    assert not PR._PET_NAMED_CHARGE_RE.search(
        "No Pets Allowed Member Rate 160.00 per night")


def test_the_pet_context_guard_itself_is_unchanged():
    """The repair worked around the guard and did not weaken it."""
    text = "No Pets Allowed Discounted rate: $160 USD /night"
    match = PR._SCOPED_CHARGE_USD_RE.search(text)
    assert match is not None
    assert PR._pet_context(text, match.start(), match.end()) is False


# --------------------------------------------------------------------------- #
# 9 / 10 -- amenity and service animals.
# --------------------------------------------------------------------------- #

def test_an_amenity_chip_is_still_not_a_policy():
    result = read(target_case("P5-amenity-only").block())
    assert "pet_fee" not in result.extraction
    assert "pet_count_limit" not in result.extraction
    assert result.extraction.get("pets_allowed") is None


def test_a_service_animal_sentence_is_still_not_a_pet_policy():
    result = read(target_case("P6-service-animal-only").block())
    assert "pets_allowed" not in result.extraction
    assert "pet_fee" not in result.extraction


# --------------------------------------------------------------------------- #
# 8 -- the refusal.
# --------------------------------------------------------------------------- #

def test_the_same_brands_refusal_is_still_a_refusal():
    result = read(target_case("C1-brand-refusal").block())
    assert result.extraction["pets_allowed"] is False
    assert "pet_fee" not in result.extraction
    assert "pet_count_limit" not in result.extraction


# --------------------------------------------------------------------------- #
# A combined weight is not an individual one.
# --------------------------------------------------------------------------- #

def test_a_combined_weight_is_never_read_as_an_individual_limit():
    """Found by the corpus, not by a capture.

    "combined weight not to exceed 100 pounds" was being published as the pet
    weight limit, which invites a guest to arrive with a hundred-pound dog the
    property never agreed to.
    """
    result = read(target_case("P10-combined-weight").block())
    assert "weight_limit" not in result.extraction
    assert result.extraction["pet_count_limit"] == 2


def test_an_individual_weight_beside_a_count_still_parses():
    result = read("Pets welcome. Up to two dogs, maximum weight 40 lbs each.")
    assert result.extraction["weight_limit"] == {"value": 40.0, "unit": "lb"}


# --------------------------------------------------------------------------- #
# 11 -- nothing property-specific.
# --------------------------------------------------------------------------- #

def test_no_property_or_brand_specific_logic_was_added():
    source = (REPO / "atlas-dashboard" / "scripts" / "pettripfinder"
              / "brightdata" / "policy_reading.py").read_text(encoding="utf-8")
    code = "\n".join(line for line in source.splitlines()
                     if not line.strip().startswith("#"))
    for term in ("bestwestern", "best_western", "milwaukee", "waukesha",
                 "germantown", "propertyCode", "50056", "50116", "50140"):
        assert term.lower() not in code.lower(), term


def test_the_repair_is_not_keyed_to_a_dollar_amount():
    """The same wording at a different price reads the same way."""
    for amount, minor in (("30.00", 3000), ("35.00", 3500), ("7.50", 750)):
        result = read("Pets welcome. The Pet Friendly rate is %s USD per day."
                      % amount)
        assert result.extraction["pet_fee"] == minor


def test_the_repair_generalises_beyond_the_brand_that_prompted_it():
    """Five brands' blocks improved, which is what makes it a generic repair."""
    brands = set(R.corpus_wide_dry_run()["changes_by_brand"])
    assert "BEST_WESTERN" in brands
    assert len(brands - {"BEST_WESTERN"}) >= 3


# --------------------------------------------------------------------------- #
# 12 -- no provider calls.
# --------------------------------------------------------------------------- #

def test_the_whole_work_order_needs_no_provider_call():
    from scripts.pettripfinder.acquisition import fresh_proof_019a as PROOF
    R.baseline_reader()          # warms the git read before the guard
    with PROOF.no_provider_calls() as attempts:
        rows = R.rederivation()
        differential = R.corpus_differential()
    assert attempts == []
    assert len(rows) == 2
    assert all(row["provider_calls"] == 0 for row in rows)
    assert differential["expectations_failed"] == []


# --------------------------------------------------------------------------- #
# 13 -- the evidence is unchanged.
# --------------------------------------------------------------------------- #

def test_the_028_artifacts_and_report_are_untouched():
    for path in ("atlas-dashboard/launch_packages/pettripfinder/markets/"
                 "reports/ptf_premium_resolution_028.json",
                 "atlas-dashboard/launch_packages/pettripfinder/markets/"
                 "reports/milwaukee-wi_full_census_028.json"):
        changed = subprocess.run(["git", "status", "--porcelain", "--", path],
                                 cwd=str(REPO), capture_output=True,
                                 text=True).stdout.strip()
        assert changed == "", path


def test_every_target_block_still_hashes_to_what_028_recorded():
    import hashlib
    for key in R.targets():
        row = next(r for r in P28.journal_rows() if r["identity_key"] == key)
        block = CORPUS.persisted_block(key)
        digest = hashlib.sha256(block.encode("utf-8")).hexdigest()
        assert digest == row["canonical_artifacts"]["block_sha256"]


def test_the_rederivation_carries_its_lineage():
    for row in R.rederivation():
        assert row["source_run"] == P28.RUN_ID
        assert row["block_sha256"]
        assert row["replay_status"] == "REPLAYED_FROM_CANONICAL_ARTIFACT"
        assert row["historical_028_reading"] == {"pets_allowed": True}
        assert row["rederived_extraction"]["pet_fee"]


# --------------------------------------------------------------------------- #
# The corpus-wide dry run.
# --------------------------------------------------------------------------- #

def test_no_field_is_removed_anywhere_in_the_persisted_corpus():
    """Except the one the combined-weight rule deliberately withdraws.

    That case is not in the Milwaukee corpus at all, so across everything this
    market has captured the change is purely additive.
    """
    # Measured against the reader 029 COMMITTED, not against HEAD. 033 was
    # commissioned to change the same file and deliberately withdraws one
    # wrong ``cleaning_fee``; read live, that removal would be reported here as
    # 029 having removed a field it never touched.
    # ...and over the evidence that EXISTED then: 032 and 033 registered new
    # runs, and 029 said nothing about blocks that had not been captured yet.
    doc = R.corpus_wide_dry_run(new_reader=R.reader_at(R.COMMIT_029),
                                runs=R.RUNS_AT_029)
    assert doc["blocks_scanned"] > 100
    assert doc["fields_removed"] == {}


def test_every_changed_block_gains_structure_or_gains_caution():
    affected = R.corpus_wide_dry_run(
        new_reader=R.reader_at(R.COMMIT_029), runs=R.RUNS_AT_029)["affected"]
    for change in affected:
        assert change["added_fields"] or change["withheld_added"], change["slug"]
        assert not change["removed_fields"], change["slug"]


# --------------------------------------------------------------------------- #
# 14 / 15 -- authority and publication.
# --------------------------------------------------------------------------- #

def test_the_store_keeps_one_row_per_identity():
    store = json.loads(R.STORE.read_text(encoding="utf-8-sig"))
    keys = [row["identity_key"] for row in store["items"]]
    assert len(keys) == len(set(keys))
    # The COUNT is not this test's claim, and later work orders move it: 032
    # recovered a property from evidence already on disk. One row per identity
    # is the invariant that belongs here.
    assert len(keys) >= 114


def test_no_milwaukee_policy_authority_exists():
    root = REPO / "atlas-dashboard" / "launch_packages" / "pettripfinder"
    assert list(root.rglob("*hotel_policy_facts*milwaukee*")) == []
    store = json.loads(R.STORE.read_text(encoding="utf-8-sig"))
    assert store["authority_written"] is False
    assert store["founder_approvals_created"] == 0


def test_nothing_is_published():
    store = json.loads(R.STORE.read_text(encoding="utf-8-sig"))
    assert all(not row.get("published") for row in store["items"])


def test_routing_and_providers_are_unchanged():
    for path in ("atlas-dashboard/scripts/pettripfinder/acquisition/routes.json",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/registry.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/router.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/providers.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/readers.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/source_discovery.py",
                 "atlas-dashboard/scripts/pettripfinder/acquisition/source_selection.py",
                 "atlas-dashboard/launch_packages/pettripfinder/identity_census",
                 "atlas-dashboard/launch_packages/pettripfinder/milwaukee_final_partition_001.json"):
        changed = subprocess.run(["git", "status", "--porcelain", "--", path],
                                 cwd=str(REPO), capture_output=True,
                                 text=True).stdout.strip()
        assert changed == "", "%s was modified by 029" % path
