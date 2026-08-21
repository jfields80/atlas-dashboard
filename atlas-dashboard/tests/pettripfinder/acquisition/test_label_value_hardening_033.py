"""PTF-LABEL-VALUE-POLICY-READER-HARDENING-033.

WHAT THESE TESTS GUARD
----------------------
Teaching a reader to accept "LABEL : VALUE" is teaching it to read a table --
and a hotel page is mostly tables that have nothing to do with pets. Room
rates, member rates, parking, resort fees, smoking fees and occupancy counts
are all written in exactly this shape, three inches from the word "pet".

So most of what follows is refusal. Nine negative controls say what must NOT
become a pet fact, four prose controls say that the sentences the reader
already read are unmoved, and the two complexity cases say that a banded price
is still withheld rather than flattened to whichever number comes first.
"""

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import label_value_corpus_033 as CORPUS
from scripts.pettripfinder.acquisition import label_value_hardening_033 as R
from scripts.pettripfinder.brightdata import policy_locator as PL
from scripts.pettripfinder.brightdata import policy_reading as PR
from scripts.pettripfinder.contracts import enums

from . import locator_freeze as LOCATOR_FREEZE
from . import reader_freeze as READER_FREEZE


def read(text):
    return PR.to_extraction(PR.parse(text), location="test-033")


def store():
    return json.loads(R.STORE.read_text(encoding="utf-8-sig"))


# --------------------------------------------------------------------------- #
# 1 -- the corpus, whole.
# --------------------------------------------------------------------------- #

#: The commit 033 made. Its freezes are claims about THAT commit, not
#: about everything anyone has done to these files since -- 035 was
#: commissioned to change one of them.
COMMIT_033 = "fe4b42f"


def _touched_by(commit):
    return subprocess.run(
        ["git", "show", "--pretty=format:", "--name-only", commit],
        cwd=str(REPO), capture_output=True, text=True).stdout.split()


def test_every_corpus_case_gets_the_answer_it_must_get():
    failed = []
    for case in CORPUS.available():
        result = read(case.block())
        for field in case.must_extract:
            if field not in result.extraction:
                failed.append("%s: %s not extracted" % (case.case_id, field))
        for field in case.must_not_extract:
            if field in result.extraction:
                failed.append("%s: %s extracted" % (case.case_id, field))
        for field in case.must_withhold:
            if field not in result.withheld:
                failed.append("%s: %s not withheld" % (case.case_id, field))
    assert failed == []


def test_the_corpus_holds_the_controls_it_claims_to():
    kinds = [case.kind for case in CORPUS.available()]
    assert kinds.count(CORPUS.NEGATIVE) == 9
    assert kinds.count(CORPUS.REGRESSION) == 4
    assert kinds.count(CORPUS.TARGET) == 2


# --------------------------------------------------------------------------- #
# 2 -- the two targets.
# --------------------------------------------------------------------------- #

def test_the_simple_label_value_table_is_read_in_full():
    row = next(r for r in R.rederivation()
               if r["identity_key"] == "hyatt regency milwaukee")
    assert row["reading_before"] == {}
    facts = row["reading_after"]
    assert facts["pet_fee"] == 4000
    assert facts["fee_basis"] == enums.BASIS_PER_NIGHT
    assert facts["fee_currency"] == "USD"
    assert facts["weight_limit"] == {"value": 150.0, "unit": "lb"}
    assert facts["pet_count_limit"] == 2


def test_the_banded_table_gives_up_its_safe_facts_and_withholds_the_price():
    """The count and the weights are stated plainly; the price is a band.

    $100 for one to six nights and $200 for seven to thirty is two prices, and
    the vocabulary holds one. Flattening it to $100 would understate a long
    stay by a hundred dollars and would be a wrong fact, not a partial one.
    """
    row = next(r for r in R.rederivation()
               if r["identity_key"] == "hyatt place milwaukee airport")
    facts, withheld = row["reading_after"], row["withheld_after"]
    assert facts["weight_limit"] == {"value": 50.0, "unit": "lb"}
    assert facts["pet_count_limit"] == 2
    assert "pet_fee" not in facts
    assert withheld["pet_fee"] == enums.SCHEMA_CANNOT_REPRESENT
    assert withheld["fee_basis"] == enums.SCHEMA_CANNOT_REPRESENT


def test_a_band_of_the_pet_price_never_becomes_a_cleaning_fee():
    """The defect 032 found and could only route around.

    Its reader called the FIRST band -- the $100 a guest pays for one to six
    nights -- a cleaning fee, because the word "cleaning" labels the $200 band
    twenty-five characters later and the rule looked backwards. 032 kept it out
    of the store by refusing the row; here it is kept out of the READING.
    """
    row = next(r for r in R.rederivation()
               if r["identity_key"] == "hyatt place milwaukee airport")
    assert "cleaning_fee" not in row["reading_after"]
    assert row["withheld_after"]["cleaning_fee"] == enums.SOURCE_AMBIGUOUS
    assert row["reading_before"] == {"cleaning_fee": 10000}


# --------------------------------------------------------------------------- #
# 3 -- cleaning charges, in both orders.
# --------------------------------------------------------------------------- #

def test_a_cleaning_charge_the_source_names_is_still_read():
    result = read("Pets welcome. Pet fee $50 per stay. "
                  "Cleaning fee : $75 per stay.")
    assert result.extraction["pet_fee"] == 5000
    assert result.extraction["cleaning_fee"] == 7500


def test_a_pet_named_cleaning_fee_stays_the_pet_charge():
    """"There is a pet cleaning fee of $100 per stay" is the price of a pet.

    Saint Kate publishes exactly that and nothing else. Filing it under
    ``cleaning_fee`` alone would leave the record with no pet price at all,
    which reads to a guest as "pets are free".
    """
    result = read("Yes, Saint Kate is a pet-friendly hotel. There is a pet "
                  "cleaning fee of $100 per stay.")
    assert result.extraction["pet_fee"] == 10000
    assert result.extraction["fee_basis"] == enums.BASIS_PER_STAY
    assert "cleaning_fee" not in result.extraction


# --------------------------------------------------------------------------- #
# 4 -- weights.
# --------------------------------------------------------------------------- #

def test_the_individual_weight_wins_where_the_surface_states_both():
    result = read("Pets welcome. Individual pet weight limit : 50 Pounds "
                  "Combined pets weight limit : 75 Pounds")
    assert result.extraction["weight_limit"] == {"value": 50.0, "unit": "lb"}


def test_a_combined_weight_alone_is_still_never_an_individual_limit():
    result = read("Pets welcome. Up to two dogs, combined weight not to "
                  "exceed 100 pounds.")
    assert "weight_limit" not in result.extraction


# --------------------------------------------------------------------------- #
# 5 -- counts.
# --------------------------------------------------------------------------- #

def test_a_count_stated_after_its_label_is_read():
    for block, expected in (("Pets welcome. Maximum number of pets is 2.", 2),
                            ("Pets welcome. Max number of pets : 3", 3),
                            ("Pets welcome. Maximum number of dogs is two.", 2)):
        assert read(block).extraction.get("pet_count_limit") == expected, block


def test_an_occupancy_count_is_not_a_pet_count():
    result = read("Pets welcome. Maximum number of guests is 4.")
    assert "pet_count_limit" not in result.extraction


# --------------------------------------------------------------------------- #
# 6 -- what a labelled amount must NOT be read as.
# --------------------------------------------------------------------------- #

def test_a_charge_every_guest_pays_is_never_the_pet_fee():
    for block in ("Pets welcome. Resort fee : $29 per night.",
                  "Pets welcome. Smoking fee : $250 per stay.",
                  "Pets allowed. Self-parking $35 per night.",
                  "Pets allowed. Valet parking : $45 per night.",
                  "Pets Welcome. 1 King Bed 4 Guests "
                  "Discounted rate: $160 USD /night",
                  "No Pets Allowed Member Rate 160.00 per night"):
        assert "pet_fee" not in read(block).extraction, block


def test_a_pet_word_in_the_previous_sentence_qualifies_nothing():
    """The rule that let the resort fee through, stated directly.

    A purpose the pet wording QUALIFIES is exempt -- "pet security deposit" is
    a deposit for a pet. The exemption was reaching across a full stop, so
    "Pets welcome." fourteen characters earlier exempted the resort fee that
    followed it and the charge was published as the price of a pet.
    """
    assert PR._pet_qualifies("A $75 pet security deposit applies.", 11)
    assert not PR._pet_qualifies("Pets welcome. Resort fee : $29.", 14)


# --------------------------------------------------------------------------- #
# 7 -- the prose the reader already read.
# --------------------------------------------------------------------------- #

def test_the_prose_controls_read_exactly_as_they_did_before():
    old = R.baseline_reader()
    for case in CORPUS.available():
        if case.kind != CORPUS.REGRESSION:
            continue
        before = R.read_with(old, case.block())
        after = R.read_with(PR, case.block())
        assert before["extraction"] == after["extraction"], case.case_id
        assert before["withheld"] == after["withheld"], case.case_id


def test_the_change_touches_almost_nothing_already_captured():
    """Two blocks in a hundred and twenty-five, and both are the targets'.

    The dry run reads every persisted block GENERICALLY, which is not how the
    store reads all of them -- Marriott's surface has its own reader -- so the
    count that matters is the one attributed to the generic reader.
    """
    # Measured against the reader 033 COMMITTED, not against HEAD: 035 changed
    # the same file, and read live this count silently becomes "everything any
    # later work order changed", which is not 033's claim.
    doc = R.corpus_wide_dry_run(new_reader=R.reader_at(R.COMMIT_033))
    assert doc["blocks_scanned"] > 100
    assert doc["blocks_changed_that_the_store_reads_generically"] == 2
    for change in doc["affected"]:
        assert change["added_fields"] or change["withheld_added"], change["slug"]


# --------------------------------------------------------------------------- #
# 8 -- evidence, lineage and cost.
# --------------------------------------------------------------------------- #

def test_the_whole_repair_needed_no_provider_call():
    assert R.cost()["provider_calls"] == 0
    assert R.cost()["incremental_spend_usd"] == 0.0
    for row in R.rederivation():
        assert row["provider_calls"] == 0
        assert row["source_run"] == "milwaukee-premium-028"


def test_the_persisted_evidence_carries_the_document_it_came_from():
    for entry in R.journal_rows():
        directory = R.REPO / entry["attempt_dir"]
        assert (directory / "policy-block.txt").is_file()
        assert (directory / "locator.json").is_file()
        record = json.loads((directory / "locator.json")
                            .read_text(encoding="utf-8"))
        block = (directory / "policy-block.txt").read_text(encoding="utf-8")
        assert record["block_sha256"] == PL.sha256_text(block)
        assert record["block_chars"] == len(block)
        assert record["document_sha256"] == \
            entry["recovered_from"]["document_sha256"]
        assert entry["recovered_from"]["provider_calls"] == 0


def test_the_original_captures_were_not_rewritten():
    for row in R.rederivation():
        original = R.REPO / row["source_attempt_dir"] / "policy-block.txt"
        assert original.is_file()
        assert original.read_text(encoding="utf-8") != row["policy_block"]


# --------------------------------------------------------------------------- #
# 9 -- the store, the counters, and what is still forbidden.
# --------------------------------------------------------------------------- #

def test_the_store_gained_exactly_the_two_targets():
    rows = {row["identity_key"]: row for row in store()["items"]}
    assert len(rows) == 117
    for key in R.targets():
        assert rows[key]["source_run"] == R.RUN_ID
        assert rows[key]["proposed_facts"]


def test_the_counters_reconcile_over_the_whole_census():
    counters = R.counters()
    assert counters["census_total"] == 147
    assert counters["sum_of_final_states"] == 147
    assert counters["active_eligible"] == 133
    assert counters["observed"] == 117
    assert counters["active_unresolved"] == 16
    assert counters["published"] == 0


def test_nothing_is_published_and_no_authority_exists():
    doc = store()
    assert not doc.get("authority_written")
    assert all(not row.get("published") for row in doc["items"])
    assert not list((R.REPO / "launch_packages" / "pettripfinder")
                    .rglob("*hotel_policy_facts*milwaukee*"))


def test_routing_source_selection_and_the_locator_are_unchanged():
    """This work order was allowed to change the reader and nothing else."""
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
                 "atlas-dashboard/launch_packages/pettripfinder/identity_census",
                 "atlas-dashboard/launch_packages/pettripfinder/milwaukee_final_partition_001.json"):
        assert not any(name == path or name.startswith(path.rstrip("/") + "/")
                       for name in _touched_by(COMMIT_033)), \
            "%s was modified by 033" % path
    LOCATOR_FREEZE.assert_locator_surface_unchanged()


def test_the_readers_own_safeguards_still_hold():
    READER_FREEZE.assert_reader_protections_unchanged()
