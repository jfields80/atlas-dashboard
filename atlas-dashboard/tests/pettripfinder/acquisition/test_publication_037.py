"""PTF-MILWAUKEE-PUBLICATION-037 -- publication, prepared and blocked.

WHAT THESE TESTS GUARD
----------------------
Publication turned out to need three things and only one of them was a flag.
The inventory is the interesting one: the site builds profiles from a market's
seed rows joined to its policy package, Milwaukee had none, and
``verified_public_hotels`` fails closed on a committed record with no display
row. So most of what follows is about the DERIVATION -- one row per approved
record, every field from a committed source, and a refusal for anything the
authorities do not state.

The rest is about the blocker. Two Hilton brands share 515 N Jefferson St, the
repository treats an unreviewed shared address as unresolved by design, and
without that review the builder drops one hotel while three pages still link
to it. The flag is therefore still false, and these tests pin that state: the
market is prepared, not published, and the two held properties are absent from
every set either way.
"""

import copy
import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder import market_authority as MA
from scripts.pettripfinder import publication_guard as PG
from scripts.pettripfinder import site_data as SD
from scripts.pettripfinder.acquisition import authority_build_036 as A
from scripts.pettripfinder.acquisition import founder_decisions_036 as D
from scripts.pettripfinder.acquisition import founder_review_036 as F
from scripts.pettripfinder.acquisition import publication_037 as P
from scripts.pettripfinder.contracts import policy_schema as SCHEMA


def authority():
    return json.loads(P.AUTHORITY.read_text(encoding="utf-8"))


def seed_rows():
    """The DERIVED inventory, computed in memory.

    It is deliberately not read from the shard: the shard is still empty. The
    dataset builder drops one of the two hotels sharing 515 N Jefferson St
    until a human reviews the collision, so committing inventory now would
    commit a row the builder silently deletes -- which is what
    test_listing_renderability_boundary caught.
    """
    rows, refused = P.seed_rows()
    assert refused == [], refused
    return rows


def prepared_contract():
    return json.loads(P.PREPARED_CONTRACT.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# 1 -- the state publication starts from.
# --------------------------------------------------------------------------- #

def test_the_start_state_is_exactly_what_036_left():
    state = P.assert_start_state()
    assert state["authority_records"] == 70
    assert state["exclusion_records"] == 26
    assert state["all_exclusions_verified_no_pets"] is True
    assert state["held_in_authority"] == []
    assert state["held_in_exclusions"] == []
    assert len(state["held_identities"]) == 2


def test_the_two_held_properties_are_read_from_the_ledger_not_listed():
    """A hand-typed hold is a hold that can be mistyped."""
    import inspect
    assert sorted(P.held_identities()) == ["hyatt regency milwaukee",
                                           "saint kate the arts hotel"]
    source = inspect.getsource(P.held_identities)
    assert "hyatt" not in source.lower()
    assert "saint kate" not in source.lower()


# --------------------------------------------------------------------------- #
# 2 / 3 -- the inventory, derived.
# --------------------------------------------------------------------------- #

def test_the_seed_inventory_is_one_row_per_approved_record():
    rows = seed_rows()
    assert len(rows) == 70
    names = [row["name"] for row in rows]
    assert len(names) == len(set(names))
    assert sorted(names) == sorted(record["name"] for record in authority()["hotels"])
    for row in rows:
        assert row["market_id"] == "milwaukee-wi"
        assert row["category"] == "pet-friendly-hotels"


def test_every_seed_field_comes_from_a_committed_authority():
    census = F.census_rows()
    records = {record["identity_key"]: record for record in authority()["hotels"]}
    by_name = {record["name"]: key for key, record in records.items()}
    for row in seed_rows():
        key = by_name[row["name"]]
        identity = census[key]
        assert row["address"] == identity["address"]
        assert row["city"] == identity["city"]
        assert row["postal_code"] == identity["postal_code"]
        assert row["source_url"] == records[key]["source_url"]
        # The policy sentence is the record's own evidence quote, never composed.
        assert row["pet_policy"] == records[key]["evidence_quote"]


def test_a_record_the_authorities_do_not_describe_is_refused():
    record = copy.deepcopy(authority()["hotels"][0])
    record["source_url"] = ""
    with pytest.raises(P.PublicationError):
        P.seed_row(record)
    unknown = copy.deepcopy(authority()["hotels"][0])
    unknown["identity_key"] = "a hotel not in the census"
    with pytest.raises(P.PublicationError):
        P.seed_row(unknown)


def test_no_held_property_has_an_inventory_row():
    keys = {SD.normalize_name(row["name"]) for row in seed_rows()}
    for held in P.held_identities():
        assert held not in keys, held


def test_no_refusal_has_an_inventory_row():
    """A verified no-pets finding must never become pet-friendly inventory."""
    refusals = {row["normalized_name"] for row in MA.load_market_exclusions("milwaukee-wi")}
    assert len(refusals) == 26
    for row in seed_rows():
        assert SD.normalize_name(row["name"]) not in refusals


# --------------------------------------------------------------------------- #
# 4 -- the flag, and nothing else.
# --------------------------------------------------------------------------- #

def test_publishing_changes_no_record():
    doc, changes = P.published_document()
    assert changes == []
    assert doc["published"] is True
    assert doc["hotels"] == authority()["hotels"]
    for record in doc["hotels"]:
        assert record["approval"]["operator"] == D.FOUNDER
        assert SCHEMA.validate_record(record) == ()


def test_the_published_document_is_deterministic():
    """The release contract pins its sha256, so the clock may not touch it."""
    first, _ = P.published_document()
    second, _ = P.published_document()
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert "published_at" not in first["publication"]


def test_the_inventory_is_derived_and_not_yet_committed():
    """Prepared, provably correct, and withheld until the collision is reviewed."""
    from scripts.pettripfinder import market_authority as MA
    assert len(MA.load_market_seed_rows("milwaukee-wi")) == 0
    assert len(seed_rows()) == 70
    assert len(MA.assemble_seed_rows()) == 296


def test_the_market_is_prepared_and_not_published():
    doc = authority()
    assert doc["published"] is False
    assert SD.load_published_hotel_policy_facts("milwaukee-wi") == {}
    assert P.counters()["published"] == 0
    assert P.counters()["deployed_live"] == 0


# --------------------------------------------------------------------------- #
# 5 -- the release contract.
# --------------------------------------------------------------------------- #

def test_the_prepared_contract_states_this_market_and_its_derived_numbers():
    contract = prepared_contract()
    assert contract["market_id"] == "milwaukee-wi"
    assert contract["policy_package"]["expected_record_count"] == 70
    assert contract["policy_package"]["expected_schema_version"] == "1.2"
    assert contract["public_surface"]["public_hotel_profile_count"] == 70
    assert contract["public_surface"]["excluded_public_profile_count"] == 0
    assert contract["public_surface"]["seed_hotel_rows"] == 70
    assert contract["routes"]["hotel_route_count"] == 70
    assert contract["routes"]["published_corridor_route_count"] == 7
    recon = contract["reconciliation"]
    assert recon["confirmed_identities"] == 147
    assert recon["published_pet_friendly"] == 70
    assert recon["verified_no_pets"] == 26
    assert recon["resolved"] == 96
    assert recon["unresolved"] == 51
    assert recon["confirmed_identities"] - recon["resolved"] == recon["unresolved"]


def test_the_contract_pins_the_sha_the_published_package_will_have():
    from scripts.pettripfinder.assemble_netlify_bundle import content_sha256
    doc, _ = P.published_document()
    payload = (json.dumps(doc, indent=1, ensure_ascii=False) + "\n").encode("utf-8")
    assert prepared_contract()["policy_package"]["expected_sha256"] == \
        content_sha256(payload)


def test_the_prepared_contract_is_not_in_the_live_directory():
    """verify_all() checks every contract it finds there, and this one is
    calibrated to a state the market has not entered."""
    assert P.PREPARED_CONTRACT.is_file()
    assert not P.CONTRACT.is_file()
    from scripts.pettripfinder.release_contracts import available_market_ids
    assert "milwaukee-wi" not in set(available_market_ids())


def test_the_contract_grants_no_deployment():
    contract = prepared_contract()
    assert contract["deployment_authorization"]["grants_deployment"] is False
    assert contract["deployment_authorization"]["asserts_market_complete"] is False
    assert "content.zero_broken_links" in contract["minimum_release_gates"]
    assert "route.all_held_absent" in contract["minimum_release_gates"]


# --------------------------------------------------------------------------- #
# 6 -- the blocker, and who may clear it.
# --------------------------------------------------------------------------- #

def test_the_shared_address_is_real_and_unreviewed():
    from scripts.pettripfinder.hotel_exclusions import address_key
    rows = {row["name"]: row for row in seed_rows()}
    pair = ("Home2 Suites by Hilton Milwaukee Downtown",
            "Tru by Hilton Milwaukee Downtown")
    keys = {address_key(rows[name]["address"], rows[name]["postal_code"])
            for name in pair}
    assert len(keys) == 1, "the pair no longer shares an address"
    assert keys == {"515|jefferson|53202"}
    reviewed = {tuple(sorted(group)) for group in PG.distinct_entity_groups()}
    assert tuple(sorted(pair)) not in reviewed, (
        "a reviewer has resolved this -- publication can proceed and this "
        "test should be replaced by the published-state assertions")


def test_the_review_request_is_unsigned():
    request = json.loads(P.REVIEW_REQUEST.read_text(encoding="utf-8"))
    assert request["status"] == "AWAITING_REVIEWER"
    proposed = request["proposed_resolution_record"]
    assert proposed["reviewer_id"].startswith("<UNSIGNED")
    assert proposed["reviewed_at"].startswith("<UNSIGNED")
    assert proposed["address_key"] == "515|jefferson|53202"
    covered = {identity["canonical_name"] for identity in proposed["identities"]}
    assert covered == {"Home2 Suites by Hilton Milwaukee Downtown",
                       "Tru by Hilton Milwaukee Downtown"}


def test_this_module_cannot_sign_a_resolution():
    """It may prepare the question. It has no code path that answers it."""
    import inspect
    source = inspect.getsource(P)
    # It NAMES the requirement in its report -- that is the point of the
    # report. What it must not have is a way to satisfy it: no import of the
    # resolutions authority, no writer for it, no hash for one.
    # The module NAMES what a human must supply -- the report exists to say so
    # -- and has no way to supply it: it never imports the resolutions
    # authority, never computes a resolution hash, and writes no file that
    # could carry a signature.
    for forbidden in ("RESOLUTIONS_PATH", "validate_resolutions",
                      "resolution_hash", "publication_guard",
                      "import identity_resolutions"):
        assert forbidden not in source, forbidden
    written = [line for line in source.splitlines() if ".write_text(" in line]
    assert written, "the module does write -- just not an attestation"
    for line in written:
        assert "resolution" not in line.lower(), line


# --------------------------------------------------------------------------- #
# 7 -- nothing leaked, nothing else moved.
# --------------------------------------------------------------------------- #

def test_the_derived_inventory_would_lose_a_row_to_the_unreviewed_collision():
    """The reason the inventory is not committed, asserted rather than argued.

    The dataset builder de-duplicates by address unless a reviewed resolution
    names the pair, so one of the two hotels at 515 N Jefferson St is dropped
    and every seed row no longer becomes a listing.
    """
    from scripts.generate_pettripfinder_pilot import load_launch_package
    from scripts.pettripfinder.listing_dataset_builder import build_listing_dataset
    package = load_launch_package()
    rows = seed_rows()
    result = build_listing_dataset(
        seed_businesses=rows,
        categories=package["categories"],
        locations=package["locations"],
        distinct_entity_groups=PG.distinct_entity_groups())
    assert result.ok, result.errors
    # One row in, one row short out: the pair at 515 N Jefferson St collapses.
    assert len(result.dataset.listings) == len(rows) - 1
    dropped = str(getattr(result, "notes", "")) + str(result)
    assert "duplicate" in dropped.lower(), dropped[:400]


def test_the_built_site_contains_no_milwaukee_route():
    bundle = Path("C:/b037c/global_bundle_manifest.json")
    if not bundle.is_file():
        pytest.skip("no local bundle in this checkout")
    manifest = json.loads(bundle.read_text(encoding="utf-8"))
    assert "milwaukee-wi" not in manifest["market_fragments_included"]
    assert manifest["broken_links"] == 0
    assert manifest["collision_count"] == 0
    assert manifest["canonical_violations"] == 0


def test_the_held_properties_appear_in_no_public_set():
    doc = authority()
    keys = {record["identity_key"] for record in doc["hotels"]}
    excluded = {row["normalized_name"] for row in MA.load_market_exclusions("milwaukee-wi")}
    inventory = {SD.normalize_name(row["name"]) for row in seed_rows()}
    for key in P.held_identities():
        assert key not in keys
        assert key not in excluded
        assert key not in inventory


def test_the_exclusion_registry_still_assembles_for_every_market():
    from scripts.pettripfinder import hotel_exclusions as EX
    registry = MA.assemble_exclusions_document()
    rows = EX.validate(registry)
    assert len(rows) == 101
    assert MA.check_generated_artifacts() == []


def test_the_other_markets_seed_inventory_is_untouched():
    rows = MA.assemble_seed_rows()
    by_market = {}
    for row in rows:
        by_market[row["market_id"]] = by_market.get(row["market_id"], 0) + 1
    assert by_market["columbus-oh"] == 116
    assert by_market["cleveland-akron-canton-oh"] == 99
    assert by_market["dayton-oh"] == 47
    assert by_market["pittsburgh-pa"] == 26
    assert by_market["indianapolis-in"] == 8
    assert "milwaukee-wi" not in by_market
    assert sum(by_market.values()) == 296


def test_no_provider_was_called_and_nothing_was_deployed():
    report = P.build_report()
    assert report["cost"]["provider_calls"] == 0
    assert report["cost"]["brightdata_spend_usd"] == 0.0
    assert report["deployment_performed"] is False
    import inspect
    # "netlify" appears as a PATH -- the release contracts live under
    # deploy/netlify/ -- so the check is on what could be invoked.
    source = inspect.getsource(P).lower()
    for token in ("netlify deploy", "--prod", "requests.get", "httpx",
                  "assemble_netlify_bundle", "subprocess"):
        assert token not in source, token


def test_the_authority_facts_and_the_review_artifacts_are_untouched():
    changed = subprocess.run(
        ["git", "status", "--porcelain", "--",
         "atlas-dashboard/launch_packages/pettripfinder/milwaukee_founder_review_036",
         "atlas-dashboard/launch_packages/pettripfinder/milwaukee_founder_decisions_036.json",
         "atlas-dashboard/launch_packages/pettripfinder/identity_census",
         "atlas-dashboard/launch_packages/pettripfinder/markets/reports/"
         "milwaukee-wi_policy_proposals_001.json",
         "atlas-dashboard/scripts/pettripfinder/brightdata/policy_reading.py",
         "atlas-dashboard/scripts/pettripfinder/contracts/policy_schema.py"],
        cwd=str(REPO), capture_output=True, text=True).stdout.strip()
    assert changed == "", changed
    for record in authority()["hotels"]:
        assert record["approval"]["decision_source"]["ledger"] == F.LEDGER.name
