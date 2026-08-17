"""PTF-POLICY-SCHEMA-MIGRATION-001 -- the policy authority, at schema 1.2.

Phase F moved 156 published records out of the display-string shapes they were
written in and into the frozen canonical schema. These tests defend the two
properties that made that safe to do:

  * nothing a source said was lost, invented, or quietly re-worded, and
  * nothing the migration does not OWN was touched.

Most assertions run against the committed corpus rather than fixtures, because
the thing being defended is the corpus. Where a fixture is used it is to prove
a rule fires at all -- a rule that only ever sees data satisfying it has not
been tested.
"""

from __future__ import annotations

import copy
import json
import subprocess

import pytest

from scripts.pettripfinder import canonical_view
from scripts.pettripfinder.contracts import (
    enums, evidence as evidence_contract, policy_schema, withholding,
)
from scripts.pettripfinder.contracts.fee_computation import classify
from scripts.pettripfinder.contracts.identity_key import is_canonical_key
from scripts.pettripfinder.contracts.review_queue import POLICY_PACKAGES
from scripts.pettripfinder.policy_migration import (
    BLOCKED, PACKAGE_DIR, evidence_aliases_for, evidence_hash, evidence_ref_for,
    load_decisions, load_package, migrate_package, record_hash,
    same_fact_aliases_for, validate_migrated,
)

MARKETS = tuple(POLICY_PACKAGES)
# Cleveland grew 21 -> 41 when PTF-CLEVELAND-PASS2-FOUNDER-DECISIONS-001
# published the founder-approved attended-capture candidates.
EXPECTED_PUBLISHED = {"columbus-oh": 88, "cleveland-akron-canton-oh": 99,
                      "dayton-oh": 47}

#: Legacy fact keys that must not survive anywhere in active authority.
FORBIDDEN_FACT_KEYS = frozenset({
    "fee_conflict", "fee_withheld", "cats_allowed", "species_allowed",
    "service_animal_exception", "weight_limit_operator",
    "weight_limit_combined", "weight_limit_combined_operator", "fee_basis",
    "fee_scope", "cleaning_fee", "pet_deposit", "fee_schedule",
    "fee_cap_tiers",
})

#: Legacy spellings that must not appear as VALUES either. "per room" as a
#: scope and per_room as a scope are the same fact; only one of them is
#: canonical, and a corpus carrying both drifts.
FORBIDDEN_VALUE_TOKENS = ('"per room"', '"per pet"', '"unknown"',
                          '"unstated"', '"combined"')


@pytest.fixture(scope="module")
def packages():
    return {market: load_package(market) for market in MARKETS}


@pytest.fixture(scope="module")
def records(packages):
    return [(market, record)
            for market in MARKETS for record in packages[market]["hotels"]]


# --------------------------------------------------------------------------- #
# The corpus is 1.2 (sections 7, 17, 36).
# --------------------------------------------------------------------------- #

def test_every_package_declares_schema_1_2(packages):
    for market, document in packages.items():
        assert document["schema_version"] == enums.POLICY_SCHEMA_VERSION, market
        assert document["market_id"] == market


def test_every_record_declares_schema_1_2(records):
    for market, record in records:
        assert record.get("schema_version") == enums.POLICY_SCHEMA_VERSION, \
            "%s / %s" % (market, record.get("key"))


def test_published_counts_are_unchanged(packages):
    counts = {m: len(packages[m]["hotels"]) for m in MARKETS}
    assert counts == EXPECTED_PUBLISHED
    assert sum(counts.values()) == 234


def test_every_record_validates_against_the_frozen_contract(packages):
    for market, document in packages.items():
        problems = validate_migrated(document)
        assert problems == [], "%s: %s" % (market, problems[:5])


def test_every_identity_key_is_canonical(records):
    for market, record in records:
        assert is_canonical_key(record["identity_key"]), record["identity_key"]


# --------------------------------------------------------------------------- #
# No legacy forms survive (section 32).
# --------------------------------------------------------------------------- #

def test_no_legacy_fact_key_survives(records):
    offenders = [(m, r["key"], k) for m, r in records
                 for k in (r.get("facts") or {}) if k in FORBIDDEN_FACT_KEYS]
    assert offenders == []


def test_no_legacy_scope_or_operator_spelling_survives(records):
    offenders = []
    for market, record in records:
        blob = json.dumps(record.get("facts") or {})
        offenders.extend((market, record["key"], token)
                         for token in FORBIDDEN_VALUE_TOKENS if token in blob)
    assert offenders == []


def test_every_fact_key_is_known_to_the_schema(records):
    for market, record in records:
        unknown = sorted(set(record.get("facts") or {})
                         - set(policy_schema.KNOWN_FACT_FIELDS))
        assert unknown == [], "%s: %s" % (record["key"], unknown)


def test_money_is_integer_cents_never_a_display_string(records):
    for market, record in records:
        fee = (record.get("facts") or {}).get("pet_fee")
        if fee is None:
            continue
        assert isinstance(fee, dict), record["key"]
        assert isinstance(fee["amount_cents"], int)
        assert not isinstance(fee["amount_cents"], bool)


def test_booleans_are_booleans(records):
    for market, record in records:
        allowed = (record.get("facts") or {}).get("pets_allowed")
        if allowed is not None:
            assert allowed is True or allowed is False, record["key"]


def test_weight_limits_carry_scope_and_a_two_member_operator(records):
    for market, record in records:
        limit = (record.get("facts") or {}).get("weight_limit")
        if limit is None:
            continue
        assert limit["operator"] in ("lt", "lte"), record["key"]
        assert limit["scope"] in enums.WEIGHT_SCOPES, record["key"]
        assert limit["unit"] in enums.WEIGHT_UNITS


def test_combined_weight_never_carries_a_scope_key(records):
    for market, record in records:
        combined = (record.get("facts") or {}).get("combined_weight_limit")
        if combined is None:
            continue
        assert "scope" not in combined, record["key"]
        assert combined["operator"] in ("lt", "lte")


def test_every_tier_states_its_role(records):
    for market, record in records:
        for tier in (record.get("facts") or {}).get("fee_tiers") or ():
            assert tier["role"] in enums.TIER_ROLES, record["key"]
            assert isinstance(tier["basis_stated"], bool)


def test_pet_schedules_are_ordinal_not_positional(records):
    for market, record in records:
        schedule = (record.get("facts") or {}).get("fee_pet_schedule")
        if schedule is None:
            continue
        assert "first_pet" not in schedule and "second_pet" not in schedule
        ordinals = [e["pet_ordinal"] for e in schedule["entries"]]
        assert ordinals == sorted(set(ordinals)), record["key"]
        for entry in schedule["entries"]:
            assert isinstance(entry["additive"], bool), record["key"]


# --------------------------------------------------------------------------- #
# Withholding (sections 21, 22).
# --------------------------------------------------------------------------- #

def test_no_withholding_survives_without_a_reason_code(records):
    for market, record in records:
        for path, entry in (record.get("withheld_fields") or {}).items():
            assert isinstance(entry, dict), "%s/%s" % (record["key"], path)
            assert entry.get("reason_code"), "%s/%s" % (record["key"], path)


def test_source_silent_is_forbidden_in_a_published_record(records):
    for market, record in records:
        for path, entry in (record.get("withheld_fields") or {}).items():
            assert entry["reason_code"] != enums.SOURCE_SILENT, \
                "%s/%s" % (record["key"], path)


def test_every_withholding_cites_evidence(records):
    for market, record in records:
        known = {e["evidence_ref"] for e in record.get("evidence") or ()
                 if e.get("evidence_ref")}
        for path, entry in (record.get("withheld_fields") or {}).items():
            assert entry["evidence_refs"], "%s/%s" % (record["key"], path)
            assert set(entry["evidence_refs"]) <= known, \
                "%s/%s cites evidence the record does not carry" % (record["key"], path)


def test_silence_restatements_were_dropped_not_recoded():
    """The 110 entries that merely said the page was silent are GONE.

    Keeping them with a reason code would have been the easy migration and the
    wrong one: an entry claiming a decision was made about a field the source
    never addressed tells a reader the hotel withheld something it never had.
    """
    total = sum(len(r.get("withheld_fields") or {})
                for m in MARKETS for r in load_package(m)["hotels"])
    # 37 after the migration; 38 since PTF-POLICY-SCHEMA-MIGRATION-001A withheld
    # Sheraton Worthington's weight, whose page disputes its own boundary;
    # 40 since the Pass-2 founder decisions withheld Residence Inn Mentor's
    # unexplained $5/night second amount and the ESA Akron South nights-7+
    # ceiling the schema cannot carry; 56 since the Pass-3 founder decisions
    # withheld fifteen more (no-limit and stated-none disclosures, ceilings,
    # garbled Staybridge tiers, and the Hilton Cleveland Downtown fee
    # contradiction) and the ESA ceiling!=price remediation one more.
    assert total == 63


def test_a_withheld_field_is_never_also_published(records):
    for market, record in records:
        assert withholding.validate(record) == (), record["key"]


# --------------------------------------------------------------------------- #
# Approval governance (sections 24, 25).
# --------------------------------------------------------------------------- #

def test_every_record_carries_a_canonical_approval(records):
    for market, record in records:
        approval = record.get("approval") or {}
        assert approval.get("decision") in enums.APPROVAL_DECISIONS, record["key"]
        assert approval.get("operator"), record["key"]
        assert approval.get("approval_date"), record["key"]


def test_approvals_are_hash_bound(records):
    for market, record in records:
        approval = record["approval"]
        signed = {k: v for k, v in record.items() if k != "approval"}
        assert approval["record_hash"] == record_hash(signed), record["key"]
        assert approval["evidence_hash"] == evidence_hash(record["evidence"])


def test_no_approval_was_back_dated(records):
    """A review recorded today says today. 26 Columbus records had no decision
    at all; none of them acquired one with a historical date."""
    for market, record in records:
        approval = record["approval"]
        if approval["decision"] == enums.LEGACY_BASELINE_REVIEWED:
            assert approval["approval_date"] == "2026-08-14", record["key"]


def test_changing_a_field_invalidates_the_record_hash(records):
    market, record = records[0]
    mutated = copy.deepcopy(record)
    mutated["facts"]["pet_count_limit"] = 99
    signed = {k: v for k, v in mutated.items() if k != "approval"}
    assert record_hash(signed) != record["approval"]["record_hash"]


def test_changing_only_the_approval_does_not_move_the_record_hash(records):
    market, record = records[0]
    mutated = copy.deepcopy(record)
    mutated["approval"]["operator"] = "someone-else"
    signed_before = {k: v for k, v in record.items() if k != "approval"}
    signed_after = {k: v for k, v in mutated.items() if k != "approval"}
    assert record_hash(signed_before) == record_hash(signed_after)


def test_evidence_hash_ignores_order_but_not_membership(records):
    market, record = records[0]
    entries = list(record["evidence"])
    assert evidence_hash(entries) == evidence_hash(list(reversed(entries)))
    assert evidence_hash(entries) != evidence_hash(entries[:-1])


def test_evidence_refs_are_content_derived_and_stable(records):
    for market, record in records:
        for entry in record["evidence"]:
            assert entry["evidence_ref"] == evidence_ref_for(entry), record["key"]


# --------------------------------------------------------------------------- #
# Computation class (section 26).
# --------------------------------------------------------------------------- #

def test_stored_computation_class_equals_recomputation(records):
    for market, record in records:
        stored = record["computation_class"]
        assert stored in enums.COMPUTATION_CLASSES, record["key"]
        assert stored == classify(record["facts"]).computation_class, record["key"]


# --------------------------------------------------------------------------- #
# Non-destructive migration (section 40).
# --------------------------------------------------------------------------- #

#: The authority as it stood BEFORE any of this migration ran. Pinned to the
#: commit rather than to HEAD: once the migration is committed, HEAD holds its
#: own output, and a test comparing the migration to itself proves nothing.
PRE_MIGRATION_REF = "2d885d1"


def _package_at_head(market):
    path = "atlas-dashboard/launch_packages/pettripfinder/%s" % POLICY_PACKAGES[market]
    blob = subprocess.run(["git", "show", "%s:%s" % (PRE_MIGRATION_REF, path)],
                          cwd=str(PACKAGE_DIR.parents[1]), capture_output=True,
                          check=True).stdout
    return json.loads(blob.decode("utf-8-sig"))


def test_migration_kept_every_field_it_does_not_own(packages):
    """The Phase C lesson, asserted: a reduced model drops what it cannot name.

    ``key``, ``evidence_count``, ``evidence_quote``, ``verification_date`` and
    five ``worker_*`` fields appear in no canonical contract, and the
    compatibility reader's output holds none of them -- so a migration written
    as "read, then serialise" would have deleted all nine from 156 records.
    """
    owned = {"schema_version", "identity_key", "market_id", "facts", "evidence",
             "withheld_fields", "approval", "service_animal_statement",
             "computation_class"}
    for market in MARKETS:
        was = {r["key"]: r for r in _package_at_head(market)["hotels"]}
        for record in packages[market]["hotels"]:
            if record["key"] not in was:
                # Published after the migration (Pass-2 founder decisions);
                # there is no pre-1.2 baseline for it to preserve.
                continue
            before = was[record["key"]]
            for name, value in before.items():
                if name in owned or name == "facts":
                    continue
                assert record.get(name) == value, \
                    "%s lost or changed %r" % (record["key"], name)


def test_source_quotes_were_never_altered(packages):
    for market in MARKETS:
        was = {r["key"]: r for r in _package_at_head(market)["hotels"]}
        for record in packages[market]["hotels"]:
            if record["key"] not in was:
                continue  # post-migration publication; no baseline quotes
            before = was[record["key"]]
            assert record.get("evidence_quote") == before.get("evidence_quote")
            assert record.get("source_url") == before.get("source_url")
            old_quotes = [e.get("quote") for e in before.get("evidence") or ()]
            new_quotes = [e.get("quote") for e in record.get("evidence") or ()]
            # Every original quote survives verbatim. The migration may ADD
            # pointers -- to a sentence a reviewer read, or to one the evidence
            # reconciliation carried across -- but only to text already in this
            # record's captured page, checked below. Membership rather than
            # prefix: an added pointer may land anywhere in the array, and where
            # it lands is not a fact about the hotel.
            assert set(old_quotes) <= set(new_quotes), record["key"]
            page = " ".join((record.get("evidence_quote") or "").split())
            # An added pointer must cite this record's own captured page --
            # UNLESS it declares that it does not. A citation recovered from a
            # legacy fee tier comes from a different read of the same property
            # URL, so it can never satisfy contiguity; the honest handling is to
            # record contiguity_verified=false on the entry rather than to
            # weaken the check for every entry. The flag is what makes the
            # exemption auditable: grep it and every such entry is listed.
            exempt = {e.get("quote") for e in record.get("evidence") or ()
                      if e.get("contiguity_verified") is False}
            for quote in set(new_quotes) - set(old_quotes) - exempt:
                assert " ".join(quote.split()) in page, record["key"]
            for entry in record.get("evidence") or ():
                if entry.get("contiguity_verified") is False:
                    # Never dressed up as more than it is.
                    assert entry.get("artifact_class") == enums.POINTER_TO_EVIDENCE
                    assert entry.get("provenance_note"), record["key"]


def test_migration_is_idempotent(packages):
    """Re-migrating an already-1.2 record returns it unchanged, byte for byte."""
    decisions = load_decisions()
    for market in MARKETS:
        again, results = migrate_package(packages[market], market, decisions)
        assert again["hotels"] == packages[market]["hotels"], market
        assert not [r for r in results if r.status == BLOCKED]


# --------------------------------------------------------------------------- #
# Named real records (sections 15, 18, 20, 30).
# --------------------------------------------------------------------------- #

def _record(market, key):
    for record in load_package(market)["hotels"]:
        if record["key"] == key:
            return record
    raise AssertionError("no record %r in %s" % (key, market))


@pytest.mark.parametrize("key", ["red roof inn columbus west hilliard",
                                 "red roof plus columbus dublin"])
def test_red_roof_cap_belongs_to_the_second_pet_rung(key):
    """The property's sentence: the first pet is free, the SECOND costs $15 a
    night, and $105 is that second pet's ceiling. A record-level cap would show
    a $105 figure against an animal that is never charged."""
    facts = _record("columbus-oh", key)["facts"]
    assert "fee_cap" not in facts
    entries = {e["pet_ordinal"]: e for e in facts["fee_pet_schedule"]["entries"]}
    assert entries[1]["amount_cents"] == 0
    assert entries[1]["additive"] is False

    second = entries[2]
    assert second["amount_cents"] == 1500
    assert second["basis"] == enums.BASIS_PER_NIGHT
    assert second["scope"] == enums.SCOPE_PER_PET
    assert second["additive"] is True

    cap = second["cap"]
    assert cap["amount_cents"] == 10500
    assert cap["basis"] == enums.BASIS_PER_STAY
    assert cap["scope"] == enums.SCOPE_PER_PET
    assert cap["applies_to_pet_ordinal"] == 2
    assert cap["trigger_max_nights"] == 7
    assert cap["qualifier_stated"] is True


def test_staybridge_miamisburg_publishes_the_property_ladder():
    """Phase B could only warn that the $50 was not the whole charge. 1.2 states
    the ladder the property actually wrote."""
    facts = _record("dayton-oh", "staybridge suites miamisburg")["facts"]
    tiers = facts["fee_tiers"]
    assert [(t["amount_cents"], t["condition_min"], t.get("condition_max"))
            for t in tiers] == [(5000, 1, 6), (15000, 7, None)]
    assert all(t["scope"] == enums.SCOPE_PER_PET for t in tiers)
    assert all(t["role"] == enums.ROLE_REPLACEMENT_PRICE for t in tiers)
    # The property's own sentence survives verbatim beside the structure.
    assert "one to six night stays" in facts["general_restrictions"]


@pytest.mark.parametrize("market,key", [
    ("cleveland-akron-canton-oh", "drury inn and suites beachwood"),
    ("cleveland-akron-canton-oh", "drury plaza hotel"),
    ("columbus-oh", "drury inn and suites columbus polaris"),
    ("columbus-oh", "drury inn and suites columbus dublin"),
    ("dayton-oh", "drury inn and suites dayton north"),
])
def test_combined_weight_never_becomes_a_per_pet_allowance(market, key):
    """Five properties state a weight for the pets TOGETHER. Recording that as
    a per-pet maximum would double the allowance the hotel granted."""
    facts = _record(market, key)["facts"]
    assert facts["combined_weight_limit"]["value"] == 80
    assert facts["combined_weight_limit"]["operator"] == "lte"
    assert "weight_limit" not in facts


def test_explicit_no_weight_limit_stays_an_affirmative_fact():
    # Two at migration; three since PTF-POLICY-SCHEMA-MIGRATION-001A read
    # "with no breed or weight restrictions" off Sonesta Dublin's own page.
    stated = [r for m in MARKETS for r in load_package(m)["hotels"]
              if (r["facts"].get("weight_limit_stated_none") is True)]
    assert len(stated) == 3
    for record in stated:
        assert "weight_limit" not in record["facts"]


@pytest.mark.parametrize("market,key", [
    ("cleveland-akron-canton-oh", "residence inn by marriott independence"),
    ("cleveland-akron-canton-oh", "residence inn cleveland beachwood"),
])
def test_cat_prohibition_is_explicit_in_the_species_map(market, key):
    """"Dogs Only, No Cats" is a refusal, and it must survive as one -- an
    absent cats entry would read as the property simply not mentioning them."""
    facts = _record(market, key)["facts"]
    assert facts["species"]["cats"] == enums.SPECIES_PROHIBITED
    assert facts["species"]["dogs"] == enums.SPECIES_ACCEPTED
    assert "cats_allowed" not in facts


def test_generic_pets_never_became_dogs_plus_cats():
    """A page naming only "pets" yields NO species. Twenty-six records reached
    1.2 with no species map at all, and that is the correct answer."""
    for market in MARKETS:
        for record in load_package(market)["hotels"]:
            species = record["facts"].get("species")
            if species is None:
                continue
            assert set(species) <= {"dogs", "cats", "birds", "fish"}, record["key"]
            assert all(v in enums.SPECIES_STATES for v in species.values())


def test_service_animal_statements_left_the_pet_policy_facts():
    statements = [(m, r) for m in MARKETS for r in load_package(m)["hotels"]
                  if r.get("service_animal_statement")]
    # Ten carried a legacy flag; eleven more state it in their own policy
    # sentence and were reconciled in by PTF-POLICY-SCHEMA-MIGRATION-001A;
    # seven more arrived with the Pass-2 founder-approved publications and
    # three more with the Pass-3 publications (La Quinta Independence and
    # the two Super 8s).
    assert len(statements) == 40
    for market, record in statements:
        assert "service_animal_exception" not in record["facts"]
        statement = record["service_animal_statement"]
        assert statement["stated"] is True
        assert statement["charges_stated"] in enums.SERVICE_ANIMAL_CHARGE_STATES


def test_no_charge_is_recorded_only_where_the_property_said_so():
    """Wyndham Independence says service animals are "welcome" and nothing about
    money; Drury says they are "free of charge". Only the second is no_charge."""
    wyndham = _record("cleveland-akron-canton-oh", "wyndham independence")
    assert wyndham["service_animal_statement"]["charges_stated"] == \
        enums.SERVICE_ANIMAL_NOT_ADDRESSED
    drury = _record("cleveland-akron-canton-oh", "drury inn and suites beachwood")
    assert drury["service_animal_statement"]["charges_stated"] == \
        enums.SERVICE_ANIMAL_NO_CHARGE


def test_hyatt_surcharge_stayed_a_surcharge():
    """"7-30 nights (additional fee)" and "7-30 nights (includes cleaning fee)"
    are three words apart and mean opposite things."""
    additive = _record("columbus-oh", "hyatt regency columbus")["facts"]["fee_tiers"]
    assert additive[1]["role"] == enums.ROLE_ADDITIONAL_CHARGE
    replacement = _record("columbus-oh", "hyatt house columbus osu short north")
    assert all(t["role"] == enums.ROLE_REPLACEMENT_PRICE
               for t in replacement["facts"]["fee_tiers"])


def test_deposit_refundability_is_never_inferred_from_a_heading():
    """Days Inn's page says "Pet deposit is 150 USD" and never says whether it
    comes back. The legacy record inferred refundable from the FIELD NAME and
    the page promised a refund the property never offered."""
    record = _record("columbus-oh", "days inn by wyndham columbus airport")
    assert "pet_deposit" not in record["facts"]
    decision = record["withheld_fields"]["pet_deposit"]
    assert decision["reason_code"] == enums.SOURCE_AMBIGUOUS


def test_explicit_refundability_is_published_where_the_source_states_it():
    facts = _record("cleveland-akron-canton-oh",
                    "courtyard by marriott airport north")["facts"]
    charge = facts["other_charges"][0]
    assert charge["kind"] == enums.CHARGE_CLEANING_FEE
    assert charge["refundable"] is False
    assert charge["amount_cents"] == 10000


# --------------------------------------------------------------------------- #
# The renderer reads 1.2 directly (section 31).
# --------------------------------------------------------------------------- #

def test_canonical_view_reads_a_1_2_record_without_the_compatibility_reader(monkeypatch):
    """Production must not depend on the legacy reader once authority is 1.2.

    Asserted by making the reader explode: if anything in the canonical path
    still calls it, this test fails rather than passing on a record that
    happened to survive being parsed twice.
    """
    def forbidden(*args, **kwargs):        # pragma: no cover - must not run
        raise AssertionError("compat_readers.read_record was called on a 1.2 record")

    monkeypatch.setattr(canonical_view, "read_record", forbidden)
    record = _record("columbus-oh", "aloft columbus easton")
    view = canonical_view.build(record)
    assert view.facts["pet_fee"]["amount_cents"] == 5000
    assert view.computation_class in enums.COMPUTATION_CLASSES


def test_display_projection_leaves_a_legacy_record_untouched():
    legacy = {"facts": {"pet_fee": "$50.00", "fee_basis": "per night"}}
    assert canonical_view.display_facts(legacy) == legacy["facts"]


def test_display_projection_restores_every_value_the_renderer_reads():
    record = _record("columbus-oh", "red roof inn columbus west hilliard")
    shown = canonical_view.display_facts(record)
    assert shown["fee_pet_schedule"]["first_pet"]["amount"] == "0.00"
    assert shown["fee_pet_schedule"]["second_pet"]["amount"] == "15.00"
    # The rung's ceiling still reaches the page, and says whose it is.
    assert shown["fee_cap"]["amount"] == "105.00"
    assert "second pet" in shown["fee_cap"]["applies_to"]


def test_display_projection_keeps_the_pet_allowance_visible():
    record = _record("columbus-oh", "la quinta inn by wyndham columbus dublin")
    shown = canonical_view.display_facts(record)
    assert shown["fee_basis"] == "per night for up to 2 pets"
    assert shown["fee_scope"] == "per room"


def test_display_projection_marks_a_withheld_fee_rather_than_silence():
    record = _record("columbus-oh", "courtyard columbus easton")
    shown = canonical_view.display_facts(record)
    assert shown.get("fee_conflict") or shown.get("fee_withheld")
    assert "pet_fee" not in shown


# --------------------------------------------------------------------------- #
# Evidence disposition (section 27).
# --------------------------------------------------------------------------- #

def test_every_evidence_entry_declares_what_it_is(records):
    for market, record in records:
        for entry in record["evidence"]:
            assert entry["artifact_class"] in enums.ARTIFACT_CLASSES
            assert evidence_contract.validate(record) == (), record["key"]


def test_legacy_evidence_is_declared_pointer_not_publication_grade(records):
    """The explicit, testable compatibility exception section 27 requires.

    Publication-grade evidence needs an artifact hash, an artifact kind and a
    capture timestamp. The migration found the committed corpus with none of
    the three, so calling those entries publication grade would have been
    fabrication -- and dropping the records instead would have unpublished 156
    hotels over a metadata gap. They were declared for what they are, and
    completing them was named as later work.

    PTF-CLEVELAND-LIGHT-RECERTIFICATION-001 Pass 1 completed Cleveland's slice
    by re-deriving every recorded capture hash from the worker-tree bytes
    (cleveland_artifact_verification_001.json), so the invariant is now the
    honest general form: an entry is a pointer, or it is publication grade and
    carries EVERYTHING publication grade requires. Nothing in between.
    """
    for market, record in records:
        for entry in record["evidence"]:
            if entry["artifact_class"] == enums.POINTER_TO_EVIDENCE:
                assert "artifact_sha256" not in entry
            else:
                assert entry["artifact_class"] == enums.PUBLICATION_GRADE_EVIDENCE
                for required in evidence_contract.PUBLICATION_GRADE_REQUIRED:
                    assert entry.get(required), (market, record["identity_key"],
                                                 entry["field"], required)


# --------------------------------------------------------------------------- #
# Evidence completeness (PTF-POLICY-SCHEMA-MIGRATION-001A founder sweep).
# --------------------------------------------------------------------------- #

#: Records the founder held because their only committed evidence text is
#: house-written or normalized prose rather than the property's own wording.
#: A published fact here is expected to be UNPOINTED: pointing at that prose
#: would make the record look better evidenced without being so.
HOUSE_PROSE_HELD = {
    "days inn by wyndham grove city columbus south",
    "drury inn and suites columbus grove city",
    "la quinta inn by wyndham columbus i 70e reynoldsburg",
    "sonesta columbus downtown",
    "the plaza hotel columbus at capitol square",
}


def test_every_published_fact_is_named_by_an_evidence_entry(records):
    """The corpus-wide coverage the founder sweep closed.

    Thirty-eight published facts were named by no evidence entry: ten because
    the quote was filed under a different field name, thirteen because the
    pointer was simply absent, and the rest because the fact or its provenance
    did not hold up. What remains unpointed is only the held cohort, and that
    is deliberate.
    """
    unpointed = []
    for market, record in records:
        named = {str(e.get("field")) for e in record["evidence"]}
        for field in record["facts"]:
            if not named.intersection(evidence_aliases_for(field)):
                unpointed.append((record["key"], field))
    assert {key for key, _ in unpointed} == HOUSE_PROSE_HELD, sorted(unpointed)


def test_the_held_cohort_carries_a_founder_hold_not_an_approval(records):
    for market, record in records:
        if record["key"] not in HOUSE_PROSE_HELD:
            continue
        approval = record["approval"]
        assert approval["decision"] == enums.HELD_FOR_REVIEW, record["key"]
        assert approval["decision"] not in enums.PUBLISHING_DECISIONS
        assert approval["operator"] == "jfields80", record["key"]


def test_species_evidence_resolves_under_either_legacy_spelling():
    """One canonical fact, several legacy field names, one alias lookup.

    ``species`` was captured as ``species_allowed`` by one worker generation
    and as the pair ``dogs_accepted``/``cats_accepted`` by another. A one-to-one
    alias saw only the first, which is why seven records read as publishing a
    species nobody had evidenced.
    """
    assert set(evidence_aliases_for("species")) == {
        "species", "species_allowed", "dogs_accepted", "cats_accepted",
        "cats_allowed", "dogs_allowed"}
    # Coverage and authoring ask different questions of the same table. A quote
    # filed under "fee_basis" COVERS pet_fee; it does not relieve a reviewed
    # pet_fee of its own pointer. Conflating them suppressed six pointers and
    # moved six record hashes, two of them already founder-approved.
    assert "fee_basis" in evidence_aliases_for("pet_fee")
    assert "fee_basis" not in same_fact_aliases_for("pet_fee")
    record = _record("columbus-oh", "drury inn and suites columbus dublin")
    named = {e["field"] for e in record["evidence"]}
    assert named.intersection(evidence_aliases_for("species"))
    assert "species" not in named          # the alias is doing the work


def test_an_unstated_pet_count_scope_is_absent_rather_than_assumed():
    """Founder decision, class FACT_NOT_SUPPORTED.

    Three records published ``pet_count_scope: room`` from sources that state a
    maximum pet count and no scope at all. The renderer happens to print "per
    room" when the field is absent, so removing it changes no page -- which is
    exactly why it had to be removed deliberately. A display default is not
    authority.
    """
    for key in ("embassy suites columbus airport corporate exchange",
                "graduate by hilton columbus",
                "hampton inn and suites canal winchester columbus"):
        record = _record("columbus-oh", key)
        assert "pet_count_scope" not in record["facts"], key
        assert record["facts"]["pet_count_limit"] == 2, key


def test_a_recovered_legacy_citation_declares_its_unverified_contiguity():
    """Founder decision, class OTHER: option A with governance modification.

    The legacy record carried this citation inside each fee tier, with its own
    source_url and source_type; the 1.2 tier conversion dropped it, leaving two
    published prices with no citation anywhere in the record. It is restored as
    what it is -- a pointer whose quote comes from a different read of the same
    property URL than the stored page capture -- and not upgraded to look like
    a verified one.
    """
    record = _record("columbus-oh", "sonesta simply suites dublin columbus")
    entries = [e for e in record["evidence"] if e["field"] == "fee_tiers"]
    assert len(entries) == 1
    entry = entries[0]
    assert entry["contiguity_verified"] is False
    assert entry["artifact_class"] == enums.POINTER_TO_EVIDENCE
    assert entry["source_type"] == "OFFICIAL_PROPERTY"
    assert "artifact_sha256" not in entry and "captured_at" not in entry
    assert " ".join(entry["quote"].split()) not in " ".join(
        record["evidence_quote"].split())


def test_an_approval_never_survives_the_record_it_signed(records):
    """Every stored approval binds the record it actually sits on.

    This is the whole governance claim of the phase, stated as arithmetic: if a
    correction moved the record, the signature that predates it must be gone,
    not recomputed under the earlier operator's name.
    """
    for market, record in records:
        approval = record["approval"]
        signed = {k: v for k, v in record.items() if k != "approval"}
        assert approval["record_hash"] == record_hash(signed), record["key"]
        assert approval["evidence_hash"] == evidence_hash(record["evidence"])
        if approval["decision"] == enums.MACHINE_REVIEWED_PENDING_OPERATOR:
            continue
        # An approval that stands was given by a person, under their own name.
        assert approval["operator"] and "claude" not in approval["operator"].lower()





# --------------------------------------------------------------------------- #
# Founder attestation (PTF-POLICY-SCHEMA-MIGRATION-001A closeout).
# --------------------------------------------------------------------------- #

def test_every_approval_names_a_person_and_binds_the_record_it_signed(records):
    """The governance claim of the phase, stated as arithmetic.

    An approval binds a record through its hash. If the record moved, the hash
    moved, and a signature that still sat on it would be a signature on
    something the operator never saw.
    """
    decisions = load_decisions()["records"]
    attested = 0
    for market, record in records:
        approval = record["approval"]
        signed = {k: v for k, v in record.items() if k != "approval"}
        assert approval["record_hash"] == record_hash(signed), record["key"]
        assert approval["evidence_hash"] == evidence_hash(record["evidence"])
        if approval["decision"] == enums.MACHINE_REVIEWED_PENDING_OPERATOR:
            # A pending-operator state is NOT an approval, and naming a person
            # on it would fabricate one. PTF-CLEVELAND-LIGHT-RECERTIFICATION-001
            # Pass 1 put Cleveland's nineteen artifact-upgraded records here.
            assert "jfields80" not in (approval["operator"] or ""), record["key"]
        else:
            assert "claude" not in (approval["operator"] or "").lower(), \
                record["key"]
        entry = decisions.get("%s|%s" % (market, record["identity_key"]), {})
        promised = entry.get("approved_record_hash")
        if not promised:
            continue
        # The hash recorded beside the founder's decision is the one they were
        # shown. Asserting it here is what makes "approved against THIS hash" a
        # checkable claim rather than a note in a report. Where a later pass
        # moved the record (Cleveland Pass 1's artifact bindings), the founder's
        # signature must survive VERBATIM under supersedes, still naming the
        # hash they saw -- and the binding block must say it awaits them.
        attested += 1
        assert entry["founder_attested"] is True
        if promised != approval["record_hash"]:
            assert approval["decision"] == \
                enums.MACHINE_REVIEWED_PENDING_OPERATOR, record["key"]
            assert approval["supersedes"]["record_hash"] == promised, \
                record["key"]
    assert attested == 53


def test_an_attested_record_keeps_the_history_its_approval_replaced(records):
    """A superseded attestation is unbound, never erased or rewritten.

    Thirty-two records carried a human approval that stopped describing them
    once the record was corrected; twenty-one carried a block the migration had
    written under an operator's name for a review they never performed. Both
    are kept, under names that say which is which.

    PTF-CLEVELAND-LIGHT-RECERTIFICATION-001 Pass 1 added sixteen more: the
    Cleveland approvals unbound when entry-level artifact bindings moved
    record_hash (Cleveland's three Class-B records already counted among the
    thirty-two and keep their attestation nested one level deeper). A prior
    from that era DOES record the hash it bound -- and the proof it was
    superseded rather than copied is that its hash no longer binds this record.
    """
    superseded = attributed = 0
    for market, record in records:
        approval = record["approval"]
        if approval.get("supersedes"):
            superseded += 1
            prior = approval["supersedes"]
            assert prior.get("operator") and "claude" not in prior["operator"].lower()
            if "record_hash" in prior:
                # A 1.2-era approval superseded later: unbound, never rebound.
                assert prior["record_hash"] != approval["record_hash"], \
                    record["key"]
            # A pre-1.2 legacy block carries no hash -- which is the point.
            # There is nothing in it that could bind a 1.2 record.
        if approval.get("invalidated_attribution"):
            attributed += 1
            assert approval["invalidated_attribution"]["decision"] == \
                enums.LEGACY_BASELINE_REVIEWED
    # 48 after the Pass-1 closeout; +2 when Pass 2 bound the Drury records'
    # byte-retained recaptures and unbound their 2026-08-11 approvals; +1
    # when the founder's Pass-3 ceiling!=price remediation re-attested ESA
    # Select Suites Akron South and unbound its 2026-08-15 approval.
    assert (superseded, attributed) == (51, 21)


def test_a_withdrawal_is_sticky_until_a_founder_clears_it():
    """Strip the attestations and every corrected record falls back to withdrawn.

    The migration re-derives from the pre-1.2 baseline on every run, where it
    reads the LEGACY approval afresh. A withdrawal decided by comparing hashes
    is therefore not stable: once a corrected record's hash matches the file
    again, the comparison finds no movement and the human's name rides back on.
    Eight of thirty-two came back exactly that way. The withdrawal is committed
    instead, and only ``founder_attested`` clears it -- which is what this
    removes, to prove the fallback is the withdrawn state and not the approved
    one.
    """
    decisions = copy.deepcopy(load_decisions())
    withdrawn = set()
    for key, entry in (decisions.get("records") or {}).items():
        if not entry.get("approval_withdrawn"):
            continue
        # The marker stays; only the founder's clearance is removed.
        entry.pop("founder_attested", None)
        entry.pop("approval", None)
        entry.pop("approved_record_hash", None)
        withdrawn.add(key)
    assert len(withdrawn) == 32
    seen = set()
    for market in MARKETS:
        migrated, _ = migrate_package(_package_at_head(market), market, decisions,
                                      prior=load_package(market))
        for record in migrated["hotels"]:
            key = "%s|%s" % (market, record["identity_key"])
            if key not in withdrawn:
                continue
            seen.add(key)
            approval = record["approval"]
            assert approval["decision"] not in enums.PUBLISHING_DECISIONS, key
            assert approval["supersedes"]["operator"]
    assert seen == withdrawn
