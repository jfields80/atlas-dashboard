"""PTF-CINCINNATI-SPECIES-KEY-REBIND-011 -- renaming eight keys, safely.

Eight records written on 2026-08-17 stored their species under ``dog`` / ``cat``
while ``canonical_view`` reads ``dogs`` / ``cats``, so their species never
reached a public surface. The defect was found by
PTF-CINCINNATI-FOUNDER-REVIEW-AND-APPLICATION-004, which declined to rewrite
founder-approved records silently, and carried through six orders since.

A rename is the smallest possible change and still has three ways to go wrong:

* it can change MORE than the key. A careless normaliser reorders keys, drops a
  species whose state it does not recognise, or rewrites a "conditional" into
  an "accepted". Three of these eight carry cats as CONDITIONAL, which is
  exactly the value a coarse repair would flatten;
* it can break the APPROVAL CHAIN. record_hash covers the record minus
  approval, so renaming a key inside facts moves it. Writing the new hash in
  and saying nothing would claim the founder signed bytes they never saw;
* it can touch a record it was not asked to. 91 records in this package were
  already correct.

These tests pin all three, and pin that the display defect is actually gone.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pettripfinder.market_state import current

from scripts.pettripfinder import canonical_view as CV
from scripts.pettripfinder import cincinnati_species_key_rebind_011 as R
from scripts.pettripfinder import policy_migration as PM
from scripts.pettripfinder.contracts import enums, policy_schema

REPO_ROOT = Path(__file__).resolve().parents[2]
PKG = REPO_ROOT / "launch_packages" / "pettripfinder"
PACKAGE = PKG / "hotel_policy_facts_cincinnati-oh.json"
REPORT = PKG / "markets" / "reports" / "cincinnati_species_key_rebind_011.json"
PARTITION = PKG / "cincinnati_final_partition_001.json"
AUTH = PKG / "markets" / "authority" / "cincinnati-oh"

REBOUND_ON = "2026-08-31"

#: The market's CURRENT counts. PTF-FACTORY-THROUGHPUT-HARDENING-001: a live
#: authority count is read from the pin, never restated in one more module.
NOW = current("cincinnati-oh")



def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


@pytest.fixture(scope="module")
def package():
    return _load(PACKAGE)


@pytest.fixture(scope="module")
def report():
    return _load(REPORT)


@pytest.fixture(scope="module")
def rebound(package):
    keys = {r["identity_key"] for r in _load(REPORT)["rows"]}
    return [h for h in package["hotels"] if h["identity_key"] in keys]


# ------------------------------------------------------ the defect is gone

def test_no_singular_species_key_survives(package):
    for record in package["hotels"]:
        species = (record.get("facts") or {}).get("species") or {}
        assert not (set(species) & {"dog", "cat"}), record["identity_key"]
        assert set(species) <= {"dogs", "cats"}, record["identity_key"]


def test_exactly_eight_records_were_rebound(report, rebound):
    assert report["count"] == len(report["rows"]) == 8
    assert len(rebound) == 8
    assert {r["approval_date"] for r in report["rows"]} == {"2026-08-17"}


def test_every_record_with_species_evidence_now_projects(package):
    """The whole point. Before this order, eight projected nothing."""
    projecting, empty = 0, []
    for record in package["hotels"]:
        if not (record.get("facts") or {}).get("species"):
            continue
        view = CV.build(record, market_id="cincinnati-oh")
        if view.dogs_state or view.cats_state:
            projecting += 1
        else:
            empty.append(record["identity_key"])
    assert empty == []
    assert projecting == 61


def test_the_report_records_the_before_and_after(report):
    for row in report["rows"]:
        before, after = row["projection_before"], row["projection_after"]
        assert before["dogs_state"] == "" and before["cats_state"] == ""
        assert after["dogs_state"] or after["cats_state"]
        assert set(row["species_before"]) & {"dog", "cat"}
        assert set(row["species_after"]) <= {"dogs", "cats"}


@pytest.mark.parametrize("identity_key,expected", [
    ("best western clermont", {"dogs": "accepted", "cats": "conditional"}),
    ("best western inn florence", {"dogs": "accepted", "cats": "conditional"}),
    ("best western plus whitewater inn",
     {"dogs": "accepted", "cats": "conditional"}),
    ("red roof inn cincinnati east eastgate",
     {"cats": "accepted", "dogs": "accepted"}),
    ("red roof inn cincinnati north mason",
     {"cats": "accepted", "dogs": "accepted"}),
    ("red roof inn greendale", {"cats": "accepted", "dogs": "accepted"}),
    ("red roof inn richwood", {"cats": "accepted", "dogs": "accepted"}),
    ("baymont by wyndham lawrenceburg", {"dogs": "accepted"}),
])
def test_each_repaired_record_carries_exactly_its_old_values(package,
                                                             identity_key,
                                                             expected):
    """Three of these say cats are CONDITIONAL -- the value a coarse repair
    would flatten into accepted."""
    record = next(h for h in package["hotels"]
                  if h["identity_key"] == identity_key)
    assert record["facts"]["species"] == expected
    for state in record["facts"]["species"].values():
        assert state in enums.SPECIES_STATES


def test_the_conditional_cats_are_still_conditional(package):
    conditional = [h["identity_key"] for h in package["hotels"]
                   if (h["facts"].get("species") or {}).get("cats")
                   == enums.SPECIES_CONDITIONAL]
    # Ashley Quarters also carries conditional cats and already used plural
    # keys, so it is untouched by this order and is not part of the cohort.
    rebound_conditional = sorted(set(conditional) & {r["identity_key"]
                                                     for r in _load(REPORT)["rows"]})
    assert rebound_conditional == ["best western clermont",
                                   "best western inn florence",
                                   "best western plus whitewater inn"]
    assert "ashley quarters hotel cincinnati airport" in conditional
    for key in conditional:
        record = next(h for h in package["hotels"]
                      if h["identity_key"] == key)
        assert CV.build(record, market_id="cincinnati-oh").cats_state == \
            enums.SPECIES_CONDITIONAL


def test_key_order_was_preserved(report):
    """Four of the eight store cats first. Reordering would make the diff
    larger than the change."""
    for row in report["rows"]:
        assert list(row["species_after"]) == \
            [R.RENAME.get(k, k) for k in row["species_before"]]


# --------------------------------------------------- nothing else moved

def test_no_semantic_or_evidence_change_was_recorded(report):
    assert "Species key names only" in report["what_changed"]
    for row in report["rows"]:
        assert row["semantic_changes"] == 0
        assert row["evidence_hash_unchanged"] is True


def test_the_semantic_guard_actually_catches_a_real_change(package):
    """Derived, so it is tested on a change this order did not make.

    If ``semantic_diff`` only ever saw safe input it would prove nothing.
    """
    import copy
    record = next(h for h in package["hotels"]
                  if h["identity_key"] == "best western clermont")
    before = copy.deepcopy(record)

    flattened = copy.deepcopy(record)
    flattened["facts"]["species"]["cats"] = "accepted"
    assert R.semantic_diff(before, flattened), "a state change slipped through"

    dropped = copy.deepcopy(record)
    dropped["facts"]["species"].pop("cats")
    assert R.semantic_diff(before, dropped), "a dropped species slipped through"

    refeed = copy.deepcopy(record)
    refeed["facts"]["pet_fee"] = {"amount_cents": 1, "currency": "USD"}
    assert R.semantic_diff(before, refeed), "a fee change slipped through"

    requoted = copy.deepcopy(record)
    requoted["evidence_quote"] = "something else"
    assert R.semantic_diff(before, requoted), "a quote change slipped through"

    # And the change this order DID make is clean.
    renamed = copy.deepcopy(record)
    renamed["facts"]["species"] = dict(
        R.rename_species(renamed["facts"]["species"]))
    assert R.semantic_diff(before, renamed) == []


def test_no_record_outside_the_cohort_was_touched(package, report):
    """91 records were already correct."""
    keys = {r["identity_key"] for r in report["rows"]}
    others = [h for h in package["hotels"] if h["identity_key"] not in keys]
    assert len(others) == 91
    for record in others:
        assert "rebinding" not in record["approval"] or \
            record["approval"]["rebinding"].get("work_order") != R.WORK_ORDER


def test_the_already_correct_records_still_reproduce_their_hashes(package,
                                                                  report):
    keys = {r["identity_key"] for r in report["rows"]}
    for record in package["hotels"]:
        if record["identity_key"] in keys:
            continue
        assert record["approval"]["record_hash"] == PM.record_hash(record), \
            record["identity_key"]


# ---------------------------------------------------- the approval chain

def test_every_rebound_record_reproduces_its_new_hash(rebound):
    for record in rebound:
        assert record["approval"]["record_hash"] == PM.record_hash(record)


def test_the_rebinding_points_old_hash_to_new(rebound, report):
    rows = {r["identity_key"]: r for r in report["rows"]}
    for record in rebound:
        block = record["approval"]["rebinding"]
        row = rows[record["identity_key"]]
        assert block["reason"] == "SPECIES_KEY_CANONICALIZATION"
        assert block["work_order"] == R.WORK_ORDER
        assert block["old_record_hash"] == row["old_record_hash"]
        assert block["new_record_hash"] == row["new_record_hash"]
        assert block["new_record_hash"] == record["approval"]["record_hash"]
        assert block["old_record_hash"] != block["new_record_hash"]
        assert block["semantic_change"] is False
        assert block["evidence_change"] is False
        assert block["source_change"] is False
        assert block["authority_change"] is False


def test_the_rebinding_lives_inside_approval_not_on_the_record(rebound):
    """A block at the record root would be inside the hashed payload and could
    never reproduce -- the defect PTF-CINCINNATI-HARDENED-SYNC-002 hit."""
    for record in rebound:
        assert "rebinding" in record["approval"]
        assert "rebinding" not in record
        # Proof: the hash excludes approval, so stripping it changes nothing.
        stripped = {k: v for k, v in record.items() if k != "approval"}
        assert PM.record_hash(stripped) == record["approval"]["record_hash"]


def test_the_founder_decision_and_evidence_are_untouched(rebound):
    for record in rebound:
        approval = record["approval"]
        assert approval["decision"] == "APPROVED_AFTER_CURRENT_REVIEW"
        assert approval["operator"] == "jfields80"
        assert approval["approval_date"] == "2026-08-17"
        assert approval["caveats"]
        assert approval["evidence_hash"] == PM.evidence_hash(record["evidence"])
        assert record["evidence"]


# ------------------------------------------------------------ authority held

def test_the_package_still_validates(package):
    assert policy_schema.validate_package(package) == ()
    assert PM.validate_migrated(package) == []


def test_no_count_moved(package):
    assert len(package["hotels"]) == NOW.pet_friendly
    # The rebind moved no count, which is what this test is about. The market
    # totals have since moved for an unrelated reason -- PTF-CINCINNATI-MAINSTAY-CENSUS-SPLIT-013 split one identity
    # into two -- so what is pinned is the package this order touched.
    counts = _load(PARTITION)["final_state_counts"]
    assert counts["PUBLISHED_PET_FRIENDLY"] == NOW.pet_friendly == len(package["hotels"])
    assert counts["OUT_OF_CURRENT_CATEGORY"] == NOW.out_of_category


def test_the_shards_were_not_rebuilt():
    """Only the package hash moved, so only the contract pin needed to."""
    assert _load(AUTH / "identity_routing.json")["count"] == 80
    exclusions = _load(AUTH / "hotel_exclusions.json")["exclusions"]
    assert sum(1 for e in exclusions
               if e["exclusion_state"] == "VERIFIED_NO_PETS") == 49


def test_the_contract_agrees_and_says_why_its_pin_moved():
    from scripts.pettripfinder import release_contracts as RC
    assert RC.verify_contract("cincinnati-oh") == []
    contract = _load(RC.contract_path("cincinnati-oh"))
    assert contract["policy_package"]["expected_record_count"] == NOW.pet_friendly
    assert "REBIND-011" in contract["policy_package"]["rebind_note"]
    assert contract["reconciliation"]["published_pet_friendly"] == NOW.pet_friendly
    assert contract["reconciliation"]["unresolved"] == NOW.unresolved


def test_this_order_cost_nothing(report):
    assert report["provider_calls"] == 0
    assert report["paid_spend_usd"] == 0.0
