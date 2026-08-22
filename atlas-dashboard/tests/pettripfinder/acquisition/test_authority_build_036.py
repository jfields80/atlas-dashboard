"""PTF-MILWAUKEE-FOUNDER-DECISION-036 -- the decisions, applied.

WHAT THESE TESTS GUARD
----------------------
The conversion, mostly. A founder approved 96 records; turning them into
authority means rewriting every fact from the reader's vocabulary into schema
1.2, and the repository's own legacy converter reads this store's
``pet_fee: 5000`` as five THOUSAND dollars. So the first thing asserted here is
that fifty dollars is still fifty dollars, and the rest is the same question
asked of every other field: does the value in the authority say what the
property's page says?

The second thing is the boundary. Two rows were HELD, and a held row has no
path into authority; the ledger binds to hashes and stops applying the moment a
record moves; and the package is written ``published: false``, which is not a
comment -- the site loader returns nothing for it, and the build proves that by
producing 1,757 pages with no Milwaukee route among them.
"""

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder import hotel_exclusions as EX
from scripts.pettripfinder import site_data as SD
from scripts.pettripfinder.acquisition import authority_build_036 as A
from scripts.pettripfinder.acquisition import founder_decisions_036 as D
from scripts.pettripfinder.acquisition import founder_review_036 as F
from scripts.pettripfinder.contracts import enums, fee_computation
from scripts.pettripfinder.contracts import policy_schema as SCHEMA



FROZEN_BY_THIS_WORK_ORDER = (
    "atlas-dashboard/scripts/pettripfinder/contracts/policy_schema.py",
    "atlas-dashboard/scripts/pettripfinder/contracts/enums.py",
    "atlas-dashboard/scripts/pettripfinder/brightdata/policy_reading.py",
    "atlas-dashboard/scripts/pettripfinder/brightdata/marriott_surface.py",
    "atlas-dashboard/launch_packages/pettripfinder/identity_census",
    "atlas-dashboard/launch_packages/pettripfinder/markets/reports/"
    "milwaukee-wi_policy_proposals_001.json",
)


def files_changed_by(commit: str):
    return subprocess.run(["git", "show", "--name-only", "--format=", commit],
                          cwd=str(REPO), capture_output=True,
                          text=True).stdout.split()


def authority():
    return json.loads(A.AUTHORITY.read_text(encoding="utf-8"))


def exclusions():
    """The GENERATED global registry, as the shards produce it."""
    from scripts.pettripfinder import market_authority as MA
    return MA.assemble_exclusions_document()


def milwaukee_shard():
    from scripts.pettripfinder import market_authority as MA
    return MA.load_market_exclusions(A.MARKET)


# --------------------------------------------------------------------------- #
# The ledger.
# --------------------------------------------------------------------------- #

def test_the_ledger_reproduces_the_totals_the_founder_stated():
    counts = D.assert_matches_the_decision_order()
    assert counts["approved_pet_friendly"] == 70
    assert counts["approved_refusal"] == 26
    assert counts["approved"] == 96
    assert counts["held"] == 2
    assert counts["cohort"] == 98
    assert counts["bulk_ruling_rows"] == 93
    assert counts["individually_ruled_rows"] == 5


def test_the_ledger_is_bound_to_the_committed_package():
    ledger = A.ledger()
    package = {row["identity_key"]: row
               for row in D.committed_package()["candidates"]}
    assert ledger["decided_by"] == D.FOUNDER
    assert ledger["source_package"]["sha256"] == F._sha256_file(F.REVIEW_JSON)
    for decision in ledger["decisions"]:
        row = package[decision["identity_key"]]
        assert decision["record_hash"] == row["record_hash"]
        assert decision["evidence_hash"] == row["evidence_hash"]


def test_a_shorthand_that_names_two_hotels_is_refused():
    """"Super 8 Airport" naming two properties is not a decision about either."""
    candidates = D.committed_package()["candidates"]
    with pytest.raises(D.TranscriptionError):
        D.resolve("Hilton", candidates)          # many Hiltons in this market
    resolved = D.resolve("Super 8 Airport", candidates)
    assert resolved["identity_key"] == "super 8 by wyndham milwaukee airport"


def test_every_decision_still_binds_at_application_time():
    applicable, refused = A.bound_decisions()
    assert refused == []
    assert len(applicable) == 98


def test_a_moved_record_refuses_to_apply(monkeypatch):
    ledger = copy.deepcopy(A.ledger())
    ledger["decisions"][0]["record_hash"] = "sha256:moved"
    monkeypatch.setattr(F, "load_ledger", lambda: ledger)
    applicable, refused = A.bound_decisions()
    assert len(refused) == 1
    assert "moved since the founder saw it" in refused[0]["refusal_reason"]
    assert len(applicable) == 97


# --------------------------------------------------------------------------- #
# The conversion -- the dangerous part.
# --------------------------------------------------------------------------- #

def test_fifty_dollars_stays_fifty_dollars():
    """The store's pet_fee is MINOR UNITS. The legacy converter reads dollars.

    ``compat_readers.read_record`` turns this store's ``pet_fee: 5000`` into
    ``amount_cents: 500000``. Using it would have published a $50.00 pet fee as
    $5,000.00 on every priced record in the market.
    """
    row = next(r for r in F.cohort_rows()
               if (r["proposed_facts"] or {}).get("pet_fee") == 5000)
    facts, _notes = A.to_facts(row)
    assert facts["pet_fee"]["amount_cents"] == 5000
    assert facts["pet_fee"]["currency"] == "USD"

    from scripts.pettripfinder.contracts import compat_readers
    legacy = compat_readers.read_record(
        {"name": row["canonical_name"], "facts": dict(row["proposed_facts"])},
        market_id=A.MARKET)
    assert legacy.record["facts"]["pet_fee"]["amount_cents"] == 500000, (
        "if this ever equals 5000 the legacy reader has been fixed and this "
        "warning can be retired")


def test_every_priced_record_carries_the_amount_its_store_row_carried():
    live = {row["identity_key"]: row for row in F.cohort_rows()}
    checked = 0
    for record in authority()["hotels"]:
        fee = record["facts"].get("pet_fee")
        if not fee:
            continue
        checked += 1
        assert fee["amount_cents"] == live[record["identity_key"]]["proposed_facts"]["pet_fee"]
    assert checked >= 40


def test_a_weight_limit_takes_its_operator_from_the_source():
    for record in authority()["hotels"]:
        weight = record["facts"].get("weight_limit")
        if not weight:
            continue
        assert weight["operator"] in ("lt", "lte")
        assert weight["scope"] == "per_pet"


def test_a_weight_with_no_stated_comparison_is_refused_not_defaulted():
    row = copy.deepcopy(next(r for r in F.cohort_rows()
                             if (r["proposed_facts"] or {}).get("weight_limit")))
    for item in row["evidence"]:
        if "weight_limit" in (item.get("field_refs") or ()):
            item["quote"] = "50 pounds"          # a number, and no comparison
    with pytest.raises(A.AuthorityError):
        A.to_facts(row)


def test_a_deposit_needs_its_refundability_stated():
    row = copy.deepcopy(next(r for r in F.cohort_rows()
                             if (r["proposed_facts"] or {}).get("pet_deposit")))
    facts, _ = A.to_facts(row)
    charge = facts["other_charges"][0]
    assert charge["kind"] in enums.OTHER_CHARGE_KINDS
    assert isinstance(charge["refundable"], bool)

    stripped = copy.deepcopy(row)
    stripped["evidence"] = [item for item in stripped["evidence"]
                            if "pet_deposit" not in (item.get("field_refs") or ())]
    with pytest.raises(A.AuthorityError):
        A.to_facts(stripped)


def test_a_service_animal_statement_never_sits_in_the_facts():
    seen = 0
    for record in authority()["hotels"]:
        assert "service_animal_exception" not in record["facts"]
        statement = record.get("service_animal_statement")
        if statement:
            seen += 1
            assert statement["stated"] is True
            assert statement["charges_stated"] in \
                enums.SERVICE_ANIMAL_CHARGE_STATES
    assert seen >= 15


def test_species_is_an_affirmative_mention_and_never_a_prohibition():
    for record in authority()["hotels"]:
        species = record["facts"].get("species")
        if not species:
            continue
        assert all(state == enums.SPECIES_ACCEPTED for state in species.values())
        # A species the page does not name is absent, not prohibited.
        assert enums.SPECIES_PROHIBITED not in species.values()


def test_a_fee_ladder_survives_serialisation_into_authority():
    live = {row["identity_key"]: row for row in F.cohort_rows()}
    laddered = [r for r in authority()["hotels"] if r["facts"].get("fee_tiers")]
    assert len(laddered) == 20
    for record in laddered:
        stored = live[record["identity_key"]]["proposed_facts"]["fee_tiers"]
        assert record["facts"]["fee_tiers"] == stored
        assert "pet_fee" not in record["facts"]


def test_a_pet_schedule_survives_serialisation_into_authority():
    """No Milwaukee row states one, so the path is proven on a built row."""
    row = copy.deepcopy(F.cohort_rows()[0])
    row["proposed_facts"] = {
        "pets_allowed": True,
        "fee_pet_schedule": {"entries": [
            {"pet_ordinal": 1, "amount_cents": 1500, "currency": "USD",
             "additive": False},
            {"pet_ordinal": 2, "amount_cents": 2500, "currency": "USD",
             "additive": False}]}}
    facts, _ = A.to_facts(row)
    assert facts["fee_pet_schedule"]["entries"][1]["amount_cents"] == 2500
    assert SCHEMA.validate_facts(facts) == ()


def test_a_fee_cap_survives_and_is_still_a_cap():
    capped = [r for r in authority()["hotels"] if r["facts"].get("fee_cap")]
    assert len(capped) == 3
    for record in capped:
        cap = record["facts"]["fee_cap"]
        assert cap["amount_cents"] > 0
        assert cap["qualifier_stated"] is False
        # The store's legacy shape rendered as the empty string; the converted
        # one reaches the page.
        from scripts.pettripfinder import canonical_view as CV
        assert CV._display_money(cap).startswith("$")


def test_a_withheld_field_never_becomes_an_authority_fact():
    live = {row["identity_key"]: row for row in F.cohort_rows()}
    for record in authority()["hotels"]:
        withheld = live[record["identity_key"]]["withheld_fields"] or {}
        for field in withheld:
            assert field not in record["facts"], (record["identity_key"], field)


# --------------------------------------------------------------------------- #
# The records, and what may not be among them.
# --------------------------------------------------------------------------- #

def test_every_authority_record_validates_under_schema_1_2():
    doc = authority()
    assert doc["schema_version"] == "1.2"
    for record in doc["hotels"]:
        assert SCHEMA.validate_record(record) == (), record["identity_key"]
        assert fee_computation.classification_disagreements(record) == ()


def test_the_authority_holds_exactly_the_approved_pet_friendly_rows():
    doc = authority()
    assert len(doc["hotels"]) == 70
    assert doc["refused_records"] == []
    keys = [record["identity_key"] for record in doc["hotels"]]
    assert len(keys) == len(set(keys))
    approved = {d["identity_key"] for d in A.ledger()["decisions"]
                if d["decision"] == D.APPROVE}
    assert set(keys) == approved


def test_a_held_row_has_no_path_into_authority():
    held = [d["identity_key"] for d in A.ledger()["decisions"]
            if d["decision"] == D.HOLD]
    assert sorted(held) == ["hyatt regency milwaukee", "saint kate the arts hotel"]
    keys = {record["identity_key"] for record in authority()["hotels"]}
    for key in held:
        assert key not in keys
    normalized = {row["normalized_name"] for row in milwaukee_shard()}
    for key in held:
        assert key not in normalized


def test_no_held_or_unresolved_store_row_reached_authority():
    keys = {record["identity_key"] for record in authority()["hotels"]}
    for row in F.R34.store_doc()["items"]:
        if row["review_status"] in F.COHORT_STATES:
            continue
        assert row["identity_key"] not in keys, row["identity_key"]


def test_every_authority_record_carries_a_founder_approval():
    for record in authority()["hotels"]:
        approval = record["approval"]
        assert approval["operator"] == D.FOUNDER
        assert approval["decision"] == A.APPROVAL_DECISION
        assert approval["decision_source"]["ledger"] == F.LEDGER.name
        assert approval["reviewed_record_hash"].startswith("sha256:")
        assert approval["record_hash"].startswith("sha256:")


# --------------------------------------------------------------------------- #
# The refusals.
# --------------------------------------------------------------------------- #

def test_the_exclusion_registry_still_validates_for_every_market():
    """A malformed Milwaukee row does not fail Milwaukee -- it fails everyone.

    The first version of this build wrote rows without record_hash and
    approval_hash, and the site assembler reported an inventory error for five
    OTHER markets. The registry validates the whole file, so this does too.
    """
    rows = EX.validate(exclusions())
    assert len(rows) == 101
    milwaukee = [row for row in rows if row["market_id"] == A.MARKET]
    assert len(milwaukee) == 26


def test_every_milwaukee_exclusion_is_a_quoted_refusal_reviewed_by_a_human():
    for row in exclusions()["exclusions"]:
        if row.get("market_id") != A.MARKET:
            continue
        assert row["exclusion_state"] == A.VERIFIED_NO_PETS
        assert row["evidence_quote"].strip()
        assert row["reviewer_id"] == D.FOUNDER
        assert row["reviewed_at"] == D.DECIDED_AT
        assert row["record_hash"] == EX.record_hash(row)
        assert row["approval_hash"] == EX.approval_hash(row)


def test_a_contrastive_refusal_carries_the_sentence_that_disambiguates_it():
    contrastive = [row for row in exclusions()["exclusions"]
                   if row.get("market_id") == A.MARKET
                   and "other" in row["evidence_quote"].lower()]
    assert len(contrastive) == 3
    for row in contrastive:
        assert "service animals are welcome" in row["evidence_context"].lower()


def test_a_no_pets_property_can_never_appear_pet_friendly():
    excluded = {row["normalized_name"] for row in exclusions()["exclusions"]}
    for record in authority()["hotels"]:
        assert record["identity_key"] not in excluded
        assert record["facts"].get("pets_allowed") is not False


# --------------------------------------------------------------------------- #
# Authority is not publication.
# --------------------------------------------------------------------------- #

def test_the_authority_is_recorded_and_not_live():
    doc = authority()
    assert doc["published"] is False
    assert SD.load_published_hotel_policy_facts(A.MARKET) == {}
    # Dayton's package has no such flag and IS live inventory, so the flag is
    # doing the work rather than the absence of data.
    assert len(SD.load_published_hotel_policy_facts("dayton-oh")) > 0


def test_the_build_produces_no_milwaukee_route():
    """Proven by the assembler's own manifest, not by inspection."""
    bundle = Path("C:/b036/global_bundle_manifest.json")
    if not bundle.is_file():
        pytest.skip("no local bundle in this checkout")
    manifest = json.loads(bundle.read_text(encoding="utf-8"))
    assert A.MARKET not in manifest["market_fragments_included"]
    excluded = {row["market_id"]: row
                for row in manifest["markets_registered_but_excluded"]}
    assert excluded[A.MARKET]["published_count"] == 0
    assert manifest["broken_links"] == 0
    assert manifest["collision_count"] == 0
    assert manifest["canonical_violations"] == 0


def test_the_store_still_records_no_approval():
    """Approval lives in the ledger and on the authority record, by design.

    ``founder_approved`` on a proposals row is part of what ``record_hash``
    hashes, so flipping it would break the very binding the ledger rests on.
    The store stays the pre-decision projection of the evidence; the decision
    lives where it cannot be regenerated away.
    """
    doc = F.R34.store_doc()
    assert all(not row.get("founder_approved") for row in doc["items"])
    assert all(not row.get("published") for row in doc["items"])


# --------------------------------------------------------------------------- #
# Determinism, cost, freezes.
# --------------------------------------------------------------------------- #

def test_rebuilding_the_authority_is_byte_identical():
    before = A.AUTHORITY.read_bytes()
    shard_before = A.EXCLUSION_SHARD.read_bytes()
    A.write(apply=True)
    after = A.AUTHORITY.read_bytes()
    # Only the built_at stamp may move; every record must be identical.
    assert json.loads(after)["hotels"] == json.loads(before)["hotels"]
    assert A.EXCLUSION_SHARD.read_bytes() == shard_before


def test_applying_twice_adds_no_duplicate_exclusion():
    _shard, fresh, refused = A.exclusions_document()
    assert fresh == []
    assert refused == []
    rows = [row["exclusion_id"] for row in exclusions()["exclusions"]]
    assert len(rows) == len(set(rows))


def test_the_market_writes_its_shard_and_never_the_generated_global():
    """The standing rule from PTF-MARKET-AUTHORITY-SHARDING-001.

    Writing the global file directly is what this build did first, and it
    broke the site assembler's inventory for five other markets. The module
    now writes the shard and lets the global builder regenerate.
    """
    import inspect
    from scripts.pettripfinder import market_authority as MA
    source = inspect.getsource(A)
    assert "EXCLUSION_SHARD = MA.exclusions_shard_path" in source
    assert 'PKG / "hotel_exclusions.json"' not in source
    assert MA.check_generated_artifacts() == []
    assert len(milwaukee_shard()) == 26


def test_nothing_was_fetched_and_nothing_was_deployed():
    cost = A.counters()
    assert cost["deployed_live"] == 0
    assert F.cost()["provider_calls"] == 0
    import inspect
    source = inspect.getsource(A).lower()
    for token in ("netlify", "--prod", "requests.get", "httpx"):
        assert token not in source, token


def test_the_schema_and_the_capture_evidence_are_untouched():
    """The claim is about THIS work order, not about the future.

    It used to assert the working tree was clean, which made it fail the moment
    a later, authorised work order touched the reader --
    PTF-...-FULL-CLOSURE-038 repaired a place-qualified refusal. What is
    durable is that e7c8363 changed none of these files, and that is checked
    against its own commit.
    """
    assert enums.POLICY_SCHEMA_VERSION == "1.2"
    touched = set(files_changed_by('e7c8363')) & set(FROZEN_BY_THIS_WORK_ORDER)
    assert touched == set(), touched


def test_the_counters_reconcile_after_the_decision():
    counters = A.counters()
    assert counters["census_total"] == 147
    assert counters["observed"] == 117
    assert counters["founder_review_candidates"] == 98
    assert counters["founder_approved"] == 96
    assert counters["approved_pet_friendly"] == 70
    assert counters["approved_refusal"] == 26
    assert counters["held_by_founder"] == 2
    assert counters["authority_rows"] == 70
    assert counters["published"] == 0
    assert counters["deployed_live"] == 0
