"""PTF-CINCINNATI-FOUNDER-REVIEW-AND-APPLICATION-004 -- what was applied.

A founder authorised 57 clean candidates as a BLOCK and ruled individually on
eight exceptions. Two of those eight publish nothing, and that is the part an
application is most likely to get wrong: a HOLD that quietly becomes a
publication, or a RENAME that publishes the new brand's terms under the old
name, are both silent and both wrong on a public page.

These also pin the shape rules the application had to satisfy, each of which
the schema rejected on the first attempt and each of which is a real guard:

* ``withheld_fields`` means "we know something and decline to publish it".
  SOURCE_SILENT is invalid inside it, so a page that never mentions a weight
  limit produces ABSENCE, not a withholding entry;
* ``weight_limit`` requires a scope, and this market withholds the limit rather
  than guess one -- Hampton Airport North states "Total Combined Weight 50lbs"
  and a per-pet reading of that would tell the wrong guests they qualify;
* ``fee_tiers`` carry a role, a condition type and a boundary unit, because
  without a role "$100 pet fee + $200 cleaning" renders as a $100-$200 range.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.pettripfinder.contracts import enums, policy_schema
from scripts.pettripfinder.contracts.identity_key import ptf_identity_key

REPO_ROOT = Path(__file__).resolve().parents[2]
PKG = REPO_ROOT / "launch_packages" / "pettripfinder"
REPORTS = PKG / "markets" / "reports"
AUTH = PKG / "markets" / "authority" / "cincinnati-oh"

PACKAGE = PKG / "hotel_policy_facts_cincinnati-oh.json"
DECISIONS = REPORTS / "cincinnati_pass3_founder_decisions_004.json"
CENSUS = PKG / "identity_census" / "cincinnati-oh.json"
PARTITION = PKG / "cincinnati_final_partition_001.json"

APPLIED_ON = "2026-08-29"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


@pytest.fixture(scope="module")
def package():
    return _load(PACKAGE)


@pytest.fixture(scope="module")
def applied(package):
    return [h for h in package["hotels"]
            if h["approval"]["approval_date"] == APPLIED_ON]


@pytest.fixture(scope="module")
def decisions():
    return _load(DECISIONS)


# ----------------------------------------------------------------- the totals

def test_this_order_published_fifty_three(package, applied):
    """74 was the total when 004 ran; PTF-...-APPLICATION-007 took it to 91.

    What 004 is entitled to assert permanently is what IT applied, not what the
    market totalled afterwards. A count of everything is a fact about the last
    order to touch the market, and stating it here made this test expire on a
    later order's success.
    """
    assert len(applied) == 53          # 47 clean + 6 exception approvals
    assert len(package["hotels"]) >= 74


def test_this_order_registered_ten_refusals_and_left_six_exits():
    """Same correction: 004 added ten refusals to the six already registered.

    The six category exits are a closed set nothing since has touched, so that
    number IS 004's to hold. The refusal total is not.
    """
    exclusions = _load(AUTH / "hotel_exclusions.json")["exclusions"]
    states = [e["exclusion_state"] for e in exclusions]
    assert states.count("OUT_OF_CURRENT_CATEGORY") == 6
    applied = [e for e in exclusions if e.get("reviewed_at") == APPLIED_ON]
    assert len(applied) == 10
    assert all(e["exclusion_state"] == "VERIFIED_NO_PETS" for e in applied)
    assert states.count("VERIFIED_NO_PETS") >= 16


def test_the_partition_still_reconciles_to_the_census(package):
    """The invariant 004 really established: the partition partitions.

    Every census identity holds exactly one final state and the states sum to
    the census. That survives every later order; the specific 74/16/160 did
    not, and pinning it here would make this test fail whenever the market
    made progress.
    """
    partition = _load(PARTITION)
    counts = partition["final_state_counts"]
    assert sum(counts.values()) == 256 == len(partition["items"])
    keys = [i["identity_key"] for i in partition["items"]]
    assert len(set(keys)) == len(keys)
    assert counts["OUT_OF_CURRENT_CATEGORY"] == 6
    assert counts["PUBLISHED_PET_FRIENDLY"] == len(package["hotels"])
    resolved = sum(counts[s] for s in ("PUBLISHED_PET_FRIENDLY",
                                       "VERIFIED_NO_PETS",
                                       "OUT_OF_CURRENT_CATEGORY"))
    assert resolved == sum(1 for i in partition["items"] if i["resolved"])


def test_nothing_is_both_published_and_refused(package):
    published = {h["identity_key"] for h in package["hotels"]}
    exclusions = _load(AUTH / "hotel_exclusions.json")["exclusions"]
    assert published.isdisjoint({e["normalized_name"] for e in exclusions})


def test_no_identity_was_published_twice(package):
    keys = [h["identity_key"] for h in package["hotels"]]
    assert len(set(keys)) == len(keys)


# -------------------------------------------- the two rulings that publish nothing

def test_the_held_property_was_held_and_later_released_on_its_terms(package,
                                                                    decisions):
    """Great Wolf: the founder declined a bare structured-data flag.

    The whole risk of a HOLD is that it looks like an approval one step later.
    So what this test guards is not that the row stayed unresolved forever --
    it did not, and should not have -- but that it was released ONLY on the
    evidence the ruling named. PTF-CINCINNATI-INDEPENDENT-FREE-PROBE-009 found
    the property's own /mason/faq prose and
    PTF-CINCINNATI-FREE-LANE-APPLICATION-010 registered the refusal on it.

    004's own ruling is unchanged, it still publishes nothing itself, and the
    exclusion that exists now cites the condition it satisfied.
    """
    ruling = next(r for r in decisions["rows"]
                  if r["identity_key"] == "great wolf lodge cincinnati mason")
    assert ruling["founder_decision"] == "HOLD_FOR_PROSE_EVIDENCE"
    assert ruling["publishes"] is False
    # Still never published as pet-friendly, by any order.
    assert "great wolf lodge cincinnati mason" not in {
        h["identity_key"] for h in package["hotels"]}
    # And the refusal that does exist rests on prose, not on the flag 004
    # refused, and says which hold it released.
    exclusions = _load(AUTH / "hotel_exclusions.json")["exclusions"]
    record = next(e for e in exclusions
                  if e["normalized_name"] == "great wolf lodge cincinnati mason")
    assert record["reviewed_at"] > APPLIED_ON
    assert "we do not allow any pets into the lodge" in record["evidence_quote"]
    assert "RELEASED FROM FOUNDER HOLD" in record["notes"]


def test_the_renamed_property_carries_its_history_and_no_policy(decisions):
    """A rename SUPERSEDES. It never overwrites and never merges."""
    ruling = next(r for r in decisions["rows"]
                  if r["identity_key"] ==
                  "extended stay america cincinnati fairfield")
    assert ruling["publishes"] is False

    rows = {h["identity_key"]: h for h in _load(CENSUS)["hotels"]}
    new_key = ptf_identity_key("Studio 6 Extended Stay Fairfield, OH - Cincinnati")
    assert new_key in rows
    assert "extended stay america cincinnati fairfield" not in rows
    row = rows[new_key]
    assert row["prior_identity_key"] == \
        "extended stay america cincinnati fairfield"
    assert row["rename"]["ruled_by"] == "jfields80"
    assert row["rename"]["not_merged_with"] == "studio 6 cincinnati springdale"

    # The twin the founder forbade merging is still its own identity.
    twin = rows["studio 6 cincinnati springdale"]
    assert twin["address"] != row["address"]
    assert twin["city"] != row["city"]

    # And no policy was published against either name.
    published = {h["identity_key"] for h in _load(PACKAGE)["hotels"]}
    assert new_key not in published
    assert "extended stay america cincinnati fairfield" not in published


# -------------------------------------------------- the shape rules that bit

def test_the_whole_package_validates_at_one_point_three(package):
    assert package["schema_version"] == enums.POLICY_SCHEMA_VERSION == "1.3"
    issues = policy_schema.validate_package(package)
    assert issues == (), [str(i) for i in issues[:6]]


def test_withheld_fields_never_records_silence(applied):
    """SOURCE_SILENT inside withheld_fields is invalid by contract.

    Pass 3 listed a page's silences and its editorial withholdings in one flat
    list. Only the second kind is a withholding; the first is absence.
    """
    for record in applied:
        for field, decision in (record.get("withheld_fields") or {}).items():
            assert decision["reason_code"] in enums.WITHHELD_FIELD_REASONS
            assert decision["reason_code"] != "SOURCE_SILENT"
            assert decision["evidence_refs"]


def test_a_weight_limit_is_published_only_with_a_stated_scope(applied):
    for record in applied:
        limit = record["facts"].get("weight_limit")
        if limit is not None:
            assert limit["scope"] in enums.WEIGHT_SCOPES
            assert "per pet" in record["evidence_quote"].lower()


def test_the_combined_weight_property_never_got_a_per_pet_limit(applied):
    row = next(r for r in applied
               if r["identity_key"] == "hampton inn cincinnati airport north")
    assert row["facts"]["combined_weight_limit"]["value"] == 50
    assert "weight_limit" not in row["facts"]
    assert row["facts"]["species"]["cats"] == "prohibited"


def test_species_use_the_keys_the_display_projection_reads(applied):
    """canonical_view reads species["dogs"] / species["cats"], plural.

    The 21 records published before this pass use the singular form and their
    species therefore never reach a public surface. That is a real defect and
    it is reported, not silently rewritten -- those are founder-approved
    records. Everything applied here uses the form that renders.
    """
    for record in applied:
        for name in (record["facts"].get("species") or {}):
            assert name in ("dogs", "cats"), record["identity_key"]


def test_every_fee_tier_carries_its_role_and_boundary(applied):
    for record in applied:
        for tier in record["facts"].get("fee_tiers") or []:
            assert tier["role"] in enums.TIER_ROLES
            assert tier["condition_type"] in enums.TIER_CONDITION_TYPES
            assert tier["boundary_unit"] in enums.TIER_BOUNDARY_UNITS
            assert tier["currency"] == "USD"
            assert isinstance(tier["basis_stated"], bool)


# ------------------------------------------------ the founder's own overrides

def test_the_fee_the_founder_released_is_published(applied):
    """Two rows Pass 3 withheld entirely, because the page said two things."""
    netherland = next(r for r in applied
                      if r["identity_key"] == "hilton cincinnati netherland plaza")
    assert netherland["facts"]["pet_fee"]["amount_cents"] == 5000
    assert netherland["facts"]["pet_fee"]["refundable_stated"] is False
    assert "deposit" in netherland["withheld_fields"]
    assert netherland["withheld_fields"]["deposit"]["reason_code"] == \
        "SOURCE_CONTRADICTORY"

    mason = next(r for r in applied
                 if r["identity_key"] ==
                 "homewood suites by hilton cincinnati mason")
    # $75 -- the short-stay rate -- over the $125 the structured field showed.
    assert mason["facts"]["pet_fee"]["amount_cents"] == 7500
    assert mason["facts"]["fee_tiers"][0]["amount_cents"] == 7500
    assert mason["facts"]["fee_tiers"][1]["amount_cents"] == 12500


def test_the_truncated_row_published_only_its_clean_fee(applied):
    row = next(r for r in applied
               if r["identity_key"] ==
               "hampton inn and suites cincinnati kenwood")
    assert row["facts"]["pet_fee"]["amount_cents"] == 7500
    assert "species" not in row["facts"]
    assert "fee_tiers" not in row["facts"]
    assert set(row["withheld_fields"]) >= {"species", "pet_count_limit",
                                           "fee_tiers"}


def test_the_service_animal_classifier_was_not_widened(applied):
    """The founder forbade teaching a shared reader a market's special case."""
    row = next(r for r in applied
               if r["identity_key"] ==
               "hampton inn and suites newport cincinnati")
    assert row["service_animal_statement"]["charges_stated"] == "not_addressed"
    assert "Fee Exempts" in row["service_animal_statement"]["quote"]
    from scripts.pettripfinder.contracts import service_animal as SA
    assert SA.charges_stated(row["service_animal_statement"]["quote"]) == \
        "not_addressed"


# ------------------------------------------------------- provenance and cost

def test_every_applied_record_binds_its_own_evidence(applied):
    from scripts.pettripfinder import policy_migration as PM
    for record in applied:
        assert record["approval"]["operator"] == "jfields80"
        assert record["approval"]["record_hash"] == PM.record_hash(record)
        assert record["approval"]["evidence_hash"] == \
            PM.evidence_hash(record["evidence"])
        assert record["evidence"], record["identity_key"]
        for entry in record["evidence"]:
            assert entry["capture_method"] == "attended_chrome_render"
            assert entry["source_grade"] == "PT1_FIRST_PARTY"


def test_the_decisions_record_the_block_and_the_eight(decisions):
    block = decisions["block_authorization"]
    assert block["clean_pet_friendly"] == 47
    assert block["clean_verified_no_pets"] == 10
    assert block["verified_before_application"] is True
    assert block["candidates_removed_from_block"] == 0
    assert decisions["count"] == 8
    for row in decisions["rows"]:
        assert row["ruling"], row["identity_key"]
        assert isinstance(row["publishes"], bool)
