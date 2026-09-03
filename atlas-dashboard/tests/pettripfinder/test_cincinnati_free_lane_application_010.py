"""PTF-CINCINNATI-FREE-LANE-APPLICATION-010 -- applying the independent probes.

Cincinnati goes 91 -> 99 published and 40 -> 47 refused. Eight rows come from
PROBE-008 and PROBE-009's clean block; eight more were founder exceptions, of
which seven publish and one is held.

Three things could have gone wrong here, and each has a test:

* a row could have been built from a SUPERSEDED reading. PROBE-008 recorded
  Drury Mason and Wildwood as POLICY_NOT_FOUND with empty quotes, and
  PROBE-009 disproved both. Building the founder's ruling against PROBE-008's
  row would have published an approval citing evidence that does not exist --
  the validator caught it, and the fix was to apply the corrections at load;
* the Drury contradiction could have been TIDIED AWAY. The founder ruled the
  JSON-LD flag SOURCE_CONTRADICTORY and said explicitly not to hide it, so it
  is recorded on all four records and none of them touches a shared reader;
* the HELD row could have quietly become resolved. Studio 6 publishes nothing
  and keeps its route, because a withdrawn route is how a row stops being
  worked.

The Phase 2 gate also flagged one row, and it was the gate: The Marcum refuses
pets with "all other animals are prohibited", which the phrase list did not
contain. Widening an incomplete implementation of a correct gate is not
relaxing it, and the gate still cannot pass an empty quote.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from pettripfinder.market_state import current

from scripts.pettripfinder import cincinnati_free_lane_application_010 as A
from scripts.pettripfinder.contracts import enums, policy_schema
from scripts.pettripfinder.contracts import service_animal as SA

REPO_ROOT = Path(__file__).resolve().parents[2]
PKG = REPO_ROOT / "launch_packages" / "pettripfinder"
REPORTS = PKG / "markets" / "reports"
AUTH = PKG / "markets" / "authority" / "cincinnati-oh"

PACKAGE = PKG / "hotel_policy_facts_cincinnati-oh.json"
PARTITION = PKG / "cincinnati_final_partition_001.json"
DECISIONS = REPORTS / "cincinnati_independent_founder_decisions_010.json"
WITHDRAWALS = REPORTS / "cincinnati_free_lane_route_withdrawals_010.json"

APPLIED_ON = "2026-08-31"
HELD = "studio 6 extended stay fairfield oh cincinnati"

#: The market's CURRENT counts. PTF-FACTORY-THROUGHPUT-HARDENING-001: a live
#: authority count is read from the pin, never restated in one more module.
NOW = current("cincinnati-oh")



def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


@pytest.fixture(scope="module")
def package():
    return _load(PACKAGE)


@pytest.fixture(scope="module")
def applied(package):
    return [h for h in package["hotels"]
            if h["approval"]["approval_date"] == APPLIED_ON]


@pytest.fixture(scope="module")
def exclusions():
    return _load(AUTH / "hotel_exclusions.json")["exclusions"]


# ------------------------------------------------------------------ the totals

def test_this_order_published_eight_and_refused_seven(package, applied,
                                                      exclusions):
    assert len(applied) == 8            # 1 clean + 7 publishing rulings
    assert len(package["hotels"]) == NOW.pet_friendly
    # Scoped by WORK ORDER, not by date: PTF-CINCINNATI-MAINSTAY-CENSUS-
    # SPLIT-013 registered two more refusals on the same day, and a date is
    # not an identifier.
    fresh = [e for e in exclusions if A.WORK_ORDER in e.get("notes", "")]
    assert len(fresh) == 7
    assert all(e["exclusion_state"] == "VERIFIED_NO_PETS" for e in fresh)
    assert sum(1 for e in exclusions
               if e["exclusion_state"] == "VERIFIED_NO_PETS") == 49


def test_the_partition_reconciles(package):
    partition = _load(PARTITION)
    counts = partition["final_state_counts"]
    assert sum(counts.values()) == NOW.census == len(partition["items"])
    keys = [i["identity_key"] for i in partition["items"]]
    assert len(set(keys)) == len(keys)
    assert counts["PUBLISHED_PET_FRIENDLY"] == NOW.pet_friendly == len(package["hotels"])
    # 47 -> 49 and 152/104 -> 154/103 at PTF-CINCINNATI-MAINSTAY-CENSUS-SPLIT-013, which registered a refusal for
    # each of the two hotels the conflated MainStay row denoted.
    assert counts["VERIFIED_NO_PETS"] == NOW.verified_no_pets
    assert counts["OUT_OF_CURRENT_CATEGORY"] == NOW.out_of_category
    resolved = sum(counts[s] for s in ("PUBLISHED_PET_FRIENDLY",
                                       "VERIFIED_NO_PETS",
                                       "OUT_OF_CURRENT_CATEGORY"))
    assert resolved == NOW.resolved
    assert sum(counts.values()) - resolved == NOW.unresolved


def test_nothing_is_both_published_and_refused(package, exclusions):
    published = {h["identity_key"] for h in package["hotels"]}
    assert published.isdisjoint({e["normalized_name"] for e in exclusions})
    keys = [h["identity_key"] for h in package["hotels"]]
    assert len(set(keys)) == len(keys)


def test_the_whole_package_validates(package):
    assert package["schema_version"] == enums.POLICY_SCHEMA_VERSION
    issues = policy_schema.validate_package(package)
    assert issues == (), [str(i) for i in issues[:6]]


# --------------------------------------------- superseded readings were not used

def test_no_record_was_built_from_a_disproved_reading(applied):
    """PROBE-008 recorded Drury Mason and Wildwood with EMPTY quotes.

    PROBE-009 disproved both. Building the founder's ruling against PROBE-008's
    rows would have published an approval whose evidence quote did not exist --
    which the schema validator refuses, and rightly.
    """
    for key in ("drury inn and suites cincinnati northeast mason",
                "wildwood inn"):
        record = next(r for r in applied if r["identity_key"] == key)
        assert record["evidence_quote"], key
        for entry in record["evidence"]:
            assert entry["quote"], key


def test_the_corrections_are_applied_at_load():
    """So the application and the probe can never disagree about a row."""
    obs = A._observations()
    for key in ("drury inn and suites cincinnati northeast mason",
                "wildwood inn"):
        assert obs[key]["corrected_by"].endswith("PROBE-009")
        assert obs[key]["outcome"] == "PUBLICATION_CANDIDATE"
        assert obs[key]["quote"]
    # A row PROBE-009 confirmed rather than reversed is left alone.
    assert "corrected_by" not in obs["golden lamb"]


def test_the_superseded_observation_is_preserved_not_erased(applied):
    record = next(r for r in applied if r["identity_key"] == "wildwood inn")
    caveats = " ".join(record["approval"]["caveats"])
    assert "SUPERSEDES" in caveats
    assert "POLICY_NOT_FOUND" in caveats
    assert "innerText" in caveats


# ------------------------------------------------------ the Drury contradiction

DRURY = ("drury inn and suites cincinnati northeast mason",
         "drury inn and suites cincinnati sharonville",
         "drury inn and suites middletown franklin",
         "drury plaza hotel cincinnati florence")


@pytest.mark.parametrize("identity_key", DRURY)
def test_every_drury_record_keeps_its_contradiction(applied, identity_key):
    """The founder said do not delete or hide it. Four records, four copies."""
    record = next(r for r in applied if r["identity_key"] == identity_key)
    withheld = record["withheld_fields"]["structured_pets_allowed_flag"]
    assert withheld["reason_code"] == "SOURCE_CONTRADICTORY"
    assert "petsAllowed" in withheld["reason"]
    assert withheld["evidence_refs"]


@pytest.mark.parametrize("identity_key", DRURY)
def test_every_drury_record_publishes_the_property_terms(applied, identity_key):
    record = next(r for r in applied if r["identity_key"] == identity_key)
    facts = record["facts"]
    assert facts["pets_allowed"] is True
    assert facts["pet_fee"]["amount_cents"] == 5000
    assert facts["pet_fee"]["basis"] == "per_night"
    assert facts["pet_fee"]["scope"] == "per_room"
    assert facts["pet_count_limit"] == 2
    assert facts["combined_weight_limit"]["value"] == 80
    assert "weight_limit" not in facts, "a combined limit is not a per-pet one"
    assert facts["species"] == {"dogs": "accepted", "cats": "accepted"}


@pytest.mark.parametrize("identity_key", DRURY)
def test_the_drury_ruling_is_bound_to_each_identity(applied, identity_key):
    """Not encoded once in a shared reader -- the founder forbade that."""
    record = next(r for r in applied if r["identity_key"] == identity_key)
    caveats = " ".join(record["approval"]["caveats"])
    assert "bound to THIS identity" in caveats
    assert "no shared reader was widened" in caveats


def test_the_shared_service_animal_classifier_was_not_widened(applied):
    for record in applied:
        stmt = record.get("service_animal_statement")
        if not stmt:
            continue
        assert stmt["charges_stated"] == SA.charges_stated(stmt["quote"])


# ------------------------------------------------------- the partial approvals

def test_an_unstated_weight_scope_was_withheld(applied):
    """Warehouse: "2 pets max, 60 lb weight limit" never says which."""
    record = next(r for r in applied
                  if r["identity_key"] == "the warehouse hotel at champion mill")
    assert "weight_limit" not in record["facts"]
    assert "combined_weight_limit" not in record["facts"]
    withheld = record["withheld_fields"]["weight_limit"]
    assert withheld["reason_code"] == "SOURCE_AMBIGUOUS"
    assert "60 lb weight limit" in record["facts"]["general_restrictions"]


def test_two_charges_with_different_bases_were_kept_apart(applied):
    """$50 per stay, then $10 per night beyond three nights."""
    record = next(r for r in applied
                  if r["identity_key"] == "the warehouse hotel at champion mill")
    facts = record["facts"]
    assert facts["pet_fee"]["amount_cents"] == 5000
    assert facts["pet_fee"]["basis"] == "per_stay"
    tiers = facts["fee_tiers"]
    assert len(tiers) == 1
    assert tiers[0]["amount_cents"] == 1000
    assert tiers[0]["role"] == "ADDITIONAL_CHARGE"
    assert tiers[0]["condition_min"] == 4      # "longer than 3 nights"
    assert tiers[0]["basis"] == "per_night"


def test_a_room_type_surcharge_has_nowhere_to_live_and_was_withheld(applied):
    assert enums.TIER_CONDITION_TYPES == ("stay_length_range", "pet_count_range")
    record = next(r for r in applied
                  if r["identity_key"] == "the summit hotel")
    withheld = record["withheld_fields"]["other_charges"]
    assert withheld["reason_code"] == "SCHEMA_CANNOT_REPRESENT"
    assert "ROOM-TYPE" in withheld["reason"]
    assert "One Bedroom Suites" in record["facts"]["general_restrictions"]
    assert "fee_tiers" not in record["facts"]


def test_the_summit_publishes_only_its_supported_dog_fields(applied):
    record = next(r for r in applied if r["identity_key"] == "the summit hotel")
    facts = record["facts"]
    assert facts["weight_limit"]["operator"] == "lt"   # "under 50 pounds"
    assert facts["weight_limit"]["value"] == 50
    assert facts["species"] == {"dogs": "accepted", "cats": "prohibited"}
    assert facts["pet_fee"]["refundable_stated"] is False
    assert facts["pet_count_limit"] == 2


def test_wildwood_publishes_only_acceptance(applied):
    """"an assortment of pet friendly rooms" states that and nothing else."""
    record = next(r for r in applied if r["identity_key"] == "wildwood inn")
    assert record["facts"]["pets_allowed"] is True
    assert set(record["facts"]) == {"pets_allowed", "general_restrictions"}
    assert "only some of its rooms" in record["facts"]["general_restrictions"]


def test_a_refundable_deposit_publishes_beside_its_fee_not_merged(applied):
    """The clean row: a per-night fee AND an explicitly refundable deposit."""
    record = next(r for r in applied
                  if r["identity_key"] == "country inn and suites erlanger")
    facts = record["facts"]
    assert facts["pet_fee"]["amount_cents"] == 2500
    assert facts["pet_fee"]["basis"] == "per_night"
    charges = facts["other_charges"]
    assert len(charges) == 1
    assert charges[0]["kind"] == "refundable_deposit"
    assert charges[0]["kind"] in enums.OTHER_CHARGE_KINDS
    assert charges[0]["amount_cents"] == 10000
    assert charges[0]["currency"] == "USD"
    assert charges[0]["refundable"] is True


# ------------------------------------------------------------------ Great Wolf

def test_great_wolf_was_registered_on_its_own_prose(exclusions):
    """Ruling #2 of APPLICATION-004 named the condition; it was met.

    The founder declined a bare JSON-LD flag for this row. What publishes it
    now is the property's own FAQ, and the record says so.
    """
    record = next(e for e in exclusions
                  if e["normalized_name"] == "great wolf lodge cincinnati mason")
    assert record["exclusion_state"] == "VERIFIED_NO_PETS"
    assert "we do not allow any pets into the lodge" in record["evidence_quote"]
    assert "/mason/faq" in record["official_url"] or "mason" in record["official_url"]
    assert "APPLICATION-004" in record["notes"]
    assert record["reviewed_at"] == APPLIED_ON


def test_no_refusal_rests_on_silence(exclusions):
    fresh = [e for e in exclusions if A.WORK_ORDER in e.get("notes", "")]
    for record in fresh:
        assert record["evidence_quote"], record["normalized_name"]
        assert record["source_hash"].startswith("sha256:")
        quote = record["evidence_quote"].lower()
        assert any(p in quote for p in A.REFUSAL_PHRASES), \
            record["normalized_name"]


def test_the_refusal_gate_still_refuses_an_empty_quote():
    """Widening the phrase list must not have widened the standard."""
    assert "prohibited" in A.REFUSAL_PHRASES
    assert not any(p in "" for p in A.REFUSAL_PHRASES)


# --------------------------------------------------------------- the held row

def test_the_held_row_publishes_nothing_and_keeps_its_route(package,
                                                            exclusions):
    published = {h["identity_key"] for h in package["hotels"]}
    refused = {e["normalized_name"] for e in exclusions}
    assert HELD not in published and HELD not in refused

    item = next(i for i in _load(PARTITION)["items"]
                if i["identity_key"] == HELD)
    assert item["resolved"] is False
    assert "two different street addresses" in item["state_override_reason"]

    routes = {r["hotel_ref"]["identity_key"]
              for r in _load(AUTH / "identity_routing.json")["routes"]}
    assert HELD in routes, "a withdrawn route is how a row stops being worked"
    withdrawals = _load(WITHDRAWALS)
    assert withdrawals["not_withdrawn"]["identity_key"] == HELD


def test_the_withdrawals_match_what_entered_authority(package, exclusions):
    withdrawals = _load(WITHDRAWALS)
    assert withdrawals["count"] == 15
    removed = {r["hotel_ref"]["identity_key"]
               for r in withdrawals["removed_routes"]}
    entered = ({h["identity_key"] for h in package["hotels"]
                if h["approval"]["approval_date"] == APPLIED_ON}
               | {e["normalized_name"] for e in exclusions
                  if A.WORK_ORDER in e.get("notes", "")})
    assert removed == entered
    # 79 after this order; 80 once SPLIT-013 replaced one conflated route
    # with one route per real property.
    assert _load(AUTH / "identity_routing.json")["count"] == 80
    for route in withdrawals["removed_routes"]:
        assert route["withdrawn_by"] == A.WORK_ORDER
        assert route["hotel_ref"]["identity_key"]


# ------------------------------------------------------------- provenance

def test_every_applied_record_binds_its_own_evidence(applied):
    from scripts.pettripfinder import policy_migration as PM
    for record in applied:
        assert record["approval"]["operator"] == "jfields80"
        assert record["approval"]["record_hash"] == PM.record_hash(record)
        assert record["approval"]["evidence_hash"] == \
            PM.evidence_hash(record["evidence"])
        for entry in record["evidence"]:
            assert entry["capture_method"] == "attended_chrome_render"
            assert entry["source_grade"] == "PT1_FIRST_PARTY"


def test_the_decisions_record_the_block_and_the_rulings():
    decisions = _load(DECISIONS)
    block = decisions["block_authorization"]
    assert block["clean_pet_friendly"] == 1
    assert block["clean_verified_no_pets"] == 7
    assert block["candidates_removed_from_block"] == 0
    assert "phrase list was incomplete" in block["gate_note"]
    assert decisions["count"] == 8          # 4 Drury + 3 partial + 1 hold
    held = [r for r in decisions["rows"] if not r["publishes"]]
    assert len(held) == 1 and held[0]["identity_key"] == HELD
    assert held[0]["route_withdrawn"] is False


def test_this_order_left_the_species_defect_and_mainstay_alone(package):
    """The species defect was deferred when this order ran and has since been
    repaired by PTF-CINCINNATI-SPECIES-KEY-REBIND-011. What holds permanently
    is that no record carries a singular key, and that MainStay is still held.
    """
    from scripts.pettripfinder import canonical_view as CV
    for record in package["hotels"]:
        species = (record.get("facts") or {}).get("species") or {}
        assert not (set(species) & {"dog", "cat"}), record["identity_key"]
        if species:
            view = CV.build(record, market_id="cincinnati-oh")
            assert view.dogs_state or view.cats_state, record["identity_key"]

    # The MainStay hold this order left standing was settled by
    # PTF-CINCINNATI-MAINSTAY-IDENTITY-012 and PTF-CINCINNATI-MAINSTAY-CENSUS-SPLIT-013. What holds permanently is
    # that THIS order neither published nor excluded it.
    applied = {h["identity_key"] for h in package["hotels"]
               if h["approval"]["approval_date"] == APPLIED_ON}
    assert "comfort suites mainstay hotel" not in applied
