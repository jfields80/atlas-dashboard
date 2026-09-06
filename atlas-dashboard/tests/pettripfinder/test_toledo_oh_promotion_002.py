"""PTF-TOLEDO-OH-PROMOTION-AND-APPLICATION-002 -- the promoted market's gates.

PTF-TOLEDO-OH-NEW-MARKET-001's suite proved a SHADOW: a market built from zero
and deliberately absent from every registry. Five of its gates asserted exactly
that absence, and this order moved it, so those five are retired there by name
through ``epochs.superseded``. This file is the other half: what must now be
true because Toledo is registered.

It also holds the founder's three rulings to the artifacts, because a ruling
that lives only in a JSON file nobody asserts against is a ruling the next
order can quietly undo.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import pytest

from scripts.pettripfinder import hotel_exclusions as HE
from scripts.pettripfinder import market_authority as MA
from scripts.pettripfinder import launch_participation as LP
from scripts.pettripfinder.markets import contract as MC
from scripts.pettripfinder.site_data import normalize_name

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE = REPO_ROOT / "launch_packages" / "pettripfinder"
REPORTS = PACKAGE / "markets" / "reports"
MARKET = "toledo-oh"
WORK_ORDER = "PTF-TOLEDO-OH-PROMOTION-AND-APPLICATION-002"

CONTRACT = PACKAGE / "markets" / "toledo-oh.json"
CENSUS = PACKAGE / "identity_census" / "toledo-oh.json"
POLICY = PACKAGE / "hotel_policy_facts_toledo-oh.json"
PARTITION = PACKAGE / "toledo_oh_final_partition_001.json"
RULINGS = PACKAGE / "toledo_oh_founder_rulings_001.json"
HOLDS = PACKAGE / "toledo_oh_identity_holds_002.json"
RELEASE = REPO_ROOT / "deploy" / "netlify" / "release_contracts" / "toledo-oh.json"
PINS = REPO_ROOT / "tests" / "pettripfinder" / "pins"

#: The founder's governing promotion set, after TOLEDO-R1A and TOLEDO-R3.
GOVERNING = {"census": 54, "pet_friendly": 17, "verified_no_pets": 9, "corridors": 13}


def _load(p: Path):
    return json.loads(p.read_text(encoding="utf-8-sig"))


# --------------------------------------------------------------------------- #
# Registered, and consistent with itself.
# --------------------------------------------------------------------------- #

def test_toledo_is_registered_everywhere_a_market_must_be():
    assert MARKET in {m.market_id for m in MC.load_markets()}
    assert MARKET in MA.registered_market_ids()
    assert MARKET in MA.sharded_market_ids()
    assert CENSUS.is_file() and POLICY.is_file() and PARTITION.is_file() and RELEASE.is_file()
    assert MARKET in _load(PINS / "market_state.json")["markets"]


def test_the_governing_promotion_set_is_what_was_promoted():
    """The founder stated 54 / 17 / 9 / 13. Nothing may quietly differ."""
    census = _load(CENSUS)
    policy = _load(POLICY)
    cfg = MC.parse_market(_load(CONTRACT), source=str(CONTRACT))
    got = {"census": census["count"], "pet_friendly": len(policy["hotels"]),
           "verified_no_pets": len(MA.load_market_exclusions(MARKET)),
           "corridors": len(cfg.corridors)}
    assert got == GOVERNING


def test_every_authority_agrees_with_every_other():
    census = _load(CENSUS)
    policy = _load(POLICY)
    partition = _load(PARTITION)
    pin = _load(PINS / "market_state.json")["markets"][MARKET]
    contract = _load(RELEASE)
    keys = {h["identity_key"] for h in census["hotels"]}

    assert partition["count"] == census["count"]
    assert {i["identity_key"] for i in partition["items"]} == keys
    assert len({i["identity_key"] for i in partition["items"]}) == len(partition["items"])

    counts = Counter(i["final_state"] for i in partition["items"])
    assert counts["PUBLISHED_PET_FRIENDLY"] == len(policy["hotels"])
    assert counts["VERIFIED_NO_PETS"] == len(MA.load_market_exclusions(MARKET))

    assert pin["census"] == census["count"] == contract["identity_census"]["expected_count"]
    assert pin["pet_friendly"] == len(policy["hotels"])
    assert pin["resolved"] + pin["unresolved"] == pin["census"]
    assert pin["last_moved_by"] == WORK_ORDER
    assert contract["reconciliation"]["confirmed_identities"] == census["count"]


def test_every_published_row_is_in_the_census_and_joins_on_its_own_name():
    census = {h["identity_key"]: h for h in _load(CENSUS)["hotels"]}
    for h in _load(POLICY)["hotels"]:
        assert h["key"] in census, h["name"]
        assert normalize_name(h["name"]) == h["key"], h["name"]
        assert census[h["key"]]["corridor"], h["name"]


def test_no_published_fact_lacks_the_quote_that_supports_it():
    for h in _load(POLICY)["hotels"]:
        fields = {e["field"] for e in h["evidence"]}
        for field in h["facts"]:
            if field == "service_animal_statement":
                continue
            assert field in fields, (h["name"], field)
        for e in h["evidence"]:
            assert e["quote"].strip(), (h["name"], e["field"])
            assert e["artifact_sha256"].startswith("sha256:"), (h["name"], e["field"])
            assert e["source_url"].startswith("https://"), (h["name"], e["field"])


def test_a_weight_limit_holds_a_number_not_another_object():
    for h in _load(POLICY)["hotels"]:
        w = h["facts"].get("weight_limit")
        if w is None:
            continue
        assert isinstance(w["value"], (int, float)), (h["name"], w)
        assert w["unit"] and w["operator"] and w["scope"]


def test_a_service_animal_statement_is_structured_never_a_bare_string():
    """A bare quote string crashes the renderer."""
    for h in _load(POLICY)["hotels"]:
        sa = h["facts"].get("service_animal_statement")
        if sa is None:
            continue
        assert isinstance(sa, dict), (h["name"], sa)
        assert sa.get("stated") is True and sa.get("quote")


def test_the_exclusion_shard_validates_and_owns_only_its_own_market():
    doc = _load(PACKAGE / "markets" / "authority" / MARKET / "hotel_exclusions.json")
    HE.validate(doc)
    for r in doc["exclusions"]:
        assert r["market_id"] == MARKET
        assert r["exclusion_state"] == HE.VERIFIED_NO_PETS
        assert r["evidence_quote"].strip()
        assert r["source_hash"].startswith("sha256:")
        assert r["record_hash"] == HE.record_hash(r)


def test_the_shared_globals_are_regenerated_not_hand_edited():
    assert MA.check_generated_artifacts() == []


# --------------------------------------------------------------------------- #
# The founder's rulings, held to the artifacts.
# --------------------------------------------------------------------------- #

def test_ruling_R1A_bowling_green_is_in_and_the_corridor_was_not_widened():
    rulings = {r["ruling_id"]: r for r in _load(RULINGS)["rulings"]}
    live = rulings["TOLEDO-R1A-BOWLING-GREEN-INCLUDED"]
    assert live["disposition"] == "ADMIT_AS_THE_TOLEDO_SOUTHERN_BOWLING_GREEN_CORRIDOR"
    assert rulings["TOLEDO-R1-BOWLING-GREEN"]["status"].startswith("SUPERSEDED")

    raw = [c for c in _load(CONTRACT)["corridors"] if c["slug"] == "bowling-green"][0]
    assert raw["included_postal_codes"] == ["43402"], "the corridor may not be widened"
    assert "TOLEDO-R1A" in raw["_boundary_note"] and "ADMITTED" in raw["_boundary_note"]
    assert "HELD FOR FOUNDER DECISION" not in raw["_boundary_note"]
    assert "KENTUCKY" in raw["_boundary_note"]
    assert "_bowling_green_exclusivity" in _load(CONTRACT)

    census = _load(CENSUS)
    bg = [h for h in census["hotels"] if h["corridor"].endswith("bowling-green")]
    assert len(bg) == 3
    published = {h["key"] for h in _load(POLICY)["hotels"]}
    refused = {r["normalized_name"] for r in MA.load_market_exclusions(MARKET)}
    assert len([h for h in bg if h["identity_key"] in published]) == 2
    assert len([h for h in bg if h["identity_key"] in refused]) == 1


def test_ruling_R2_holds_every_two_identity_address_out_of_publication():
    holds = _load(HOLDS)
    published = {h["key"] for h in _load(POLICY)["hotels"]}
    refused = {r["normalized_name"] for r in MA.load_market_exclusions(MARKET)}
    census = {h["identity_key"]: h for h in _load(CENSUS)["hotels"]}
    addresses = [h["address"] for h in holds["other_group_a_identities_held_by_TOLEDO_R2"]]
    addresses.append("%s, %s" % (holds["holds"][0]["census_street"],
                                 holds["holds"][0]["census_postal_code"]))
    assert len(addresses) >= 5
    street_of = {(h["street"] or "").lower(): k for k, h in census.items()}
    for addr in addresses:
        street = addr.split(",")[0].strip().lower()
        key = street_of.get(street)
        if key is None:
            continue
        assert key not in published, addr
        assert key not in refused, addr


def test_ruling_R3_holds_both_fremont_pike_reads_and_preserves_both_captures():
    hold = _load(HOLDS)["holds"][0]
    assert hold["proposed_future_action"] == (
        "SAME_PREMISES_DISTINCT_IDENTITIES / DUAL-BRAND SPLIT REVIEW")
    captures = hold["the_two_first_party_captures_preserved"]
    assert len(captures) == 2
    assert {c["pets_allowed"] for c in captures} == {True, False}, (
        "the whole point is that the two pages disagree")
    for c in captures:
        assert c["operative_quote"] and c["source_url"].startswith("https://")

    census = {h["identity_key"]: h for h in _load(CENSUS)["hotels"]}
    row = census[hold["census_identity_key"]]
    assert set(hold["census_aliases"]) <= set(row["identity_key_aliases"]), (
        "the aliases naming BOTH brands must survive for a later split")
    published = {h["key"] for h in _load(POLICY)["hotels"]}
    refused = {r["normalized_name"] for r in MA.load_market_exclusions(MARKET)}
    assert row["identity_key"] not in published and row["identity_key"] not in refused


def test_the_promotion_did_not_flip_launch_participation():
    assert LP.launch_status(MARKET) == "SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH"
    decision = _load(REPO_ROOT / "deploy" / "netlify" / "launch_participation.json")["decision"]
    assert decision["work_order"] != WORK_ORDER, (
        "this order may record source readiness; it may not author a launch decision")


def test_no_deployment_authorization_was_created():
    authz = REPO_ROOT / "deploy" / "netlify" / "deployment_authorizations"
    assert not list(authz.glob("*toledo*")), "only a founder creates an authorization"
    packet = REPORTS / "toledo_deployment_authorization_003_PROPOSED.json"
    if packet.is_file():
        doc = _load(packet)
        assert doc["status"] == "PROPOSED_UNEXECUTED"
        assert doc["authorized_by"] is None and doc["authorized_at"] is None


def test_production_is_untouched_by_this_order():
    live = _load(PINS / "deployment_state.json")["live"]
    assert live["deploy_id"] == "6a9d33f5dc8c3d1cf9464376"
    assert len(live["participating_markets"]) == 10
    assert MARKET not in live["participating_markets"]
    assert live["total_profiles"] == 786 and live["sitemap_route_count"] == 945


def test_the_assembler_names_toledos_partition_explicitly():
    """The glob would compute 'toledo' and match nothing."""
    src = (REPO_ROOT / "scripts" / "pettripfinder"
           / "assemble_production_site.py").read_text(encoding="utf-8")
    assert '"toledo-oh": "toledo_oh_final_partition_001.json"' in src


@pytest.mark.parametrize("other", [
    "cincinnati-oh", "cleveland-akron-canton-oh", "columbus-oh", "dayton-oh",
    "detroit-ann-arbor-mi", "grand-rapids-holland-mi", "indianapolis-in",
    "louisville-ky", "milwaukee-wi", "pittsburgh-pa", "st-louis-mo",
])
def test_no_other_market_moved(other):
    """Registering market N+1 must change no other market's numbers."""
    pin = _load(PINS / "market_state.json")["markets"][other]
    assert pin["last_moved_by"] != WORK_ORDER
    contract = _load(REPO_ROOT / "deploy" / "netlify" / "release_contracts"
                     / ("%s.json" % other))
    assert contract["reconciliation"]["confirmed_identities"] == pin["census"]
    assert contract["reconciliation"]["published_pet_friendly"] == pin["pet_friendly"]


# --------------------------------------------------------------------------
# The broad regression, and the readiness it does and does not establish.
# --------------------------------------------------------------------------

REGRESSION = REPORTS / "toledo_oh_regression_classification_002.json"
BASELINE = PACKAGE / "regression_baselines" / "f75aa95.json"
PACKET = REPORTS / "toledo_deployment_authorization_003_PROPOSED.json"


def test_the_broad_regression_was_classified_by_node_id_not_by_count():
    """A matching failure COUNT is not a proof.

    160 failures against a 160-failure baseline is equally consistent with one
    baseline failure having been fixed and one fresh failure having appeared.
    The committed report must assert SET IDENTITY, and it must show its work by
    listing both directions of the difference.
    """
    rep = _load(REGRESSION)
    run = rep["run_2"]
    assert run["in_run_not_in_baseline"] == []
    assert run["in_baseline_not_in_run"] == []
    assert run["failure_set_identical_to_baseline"] is True
    assert run["failed"] == _load(BASELINE)["failing_node_ids"].__len__()
    assert rep["classification"]["PRE_EXISTING"] == run["failed"]


def test_true_new_failure_is_zero():
    rep = _load(REGRESSION)
    assert rep["classification"]["TRUE_NEW_FAILURE"] == 0
    assert rep["classification"]["TEST_HARNESS_FLAKE"] == 0
    assert rep["verdict"].startswith("CLEAN")


def test_the_lane_was_the_full_suite_because_a_registration_is_never_narrow():
    rep = _load(REGRESSION)
    assert rep["lane"] == "full_regression"
    assert rep["run_2"]["collected"] > 17000


def test_run_ones_nine_new_failures_are_each_explained_and_none_were_scoped_away():
    """Every failure the first broad run added was this order's own.

    Three were real applier defects that would have shipped a package the record
    contract rejects. The rest were registry counts a twelfth market legitimately
    moves, plus one project test that had used ``toledo-oh`` as its example of an
    unregistered id. None was closed by weakening a gate.
    """
    r1 = _load(REGRESSION)["run_1"]
    assert r1["unexplained_new_failures"] == []
    causes = r1["every_new_failure_was_this_orders_own"]
    assert len(causes) == r1["true_new_failures"] == 9
    assert all(why.strip() for why in causes.values())


def test_deployment_ready_is_yes_and_every_gate_is_recorded():
    doc = _load(PACKET)
    assert doc["DEPLOYMENT_READY"] == "YES"
    gates = doc["deployment_ready_gates"]
    assert gates and all(gates.values()), [k for k, v in gates.items() if not v]
    assert gates["TRUE_NEW_FAILURE_is_zero"] is True
    assert gates["candidate_reproduces_the_live_bundle"] is True
    assert gates["toledo_does_not_participate"] is True


def test_deployment_ready_is_not_an_authorization_and_not_a_launch():
    """The two founder levers this order is forbidden to pull stay unpulled."""
    doc = _load(PACKET)
    assert doc["status"] == "PROPOSED_UNEXECUTED"
    assert doc["authorized_by"] is None and doc["authorized_at"] is None
    assert not list((REPO_ROOT / "deploy" / "netlify"
                     / "deployment_authorizations").glob("*toledo*"))
    assert LP.launch_status(MARKET) == "SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH"
    assert doc["bundle_sha256"] == _load(PINS / "deployment_state.json")["live"]["bundle_sha256"]


def test_the_packet_numbers_are_derived_from_artifacts_not_typed():
    """The Cincinnati launch order quoted a bundle SHA wrong in five characters."""
    doc = _load(PACKET)
    state = _load(PINS / "market_state.json")["markets"][MARKET]
    would = doc["what_toledo_would_bring_when_it_is_launched"]
    assert would["census"] == state["census"] == GOVERNING["census"]
    assert would["published_profiles"] == state["profiles"] == GOVERNING["pet_friendly"]
    assert would["verified_no_pets"] == state["verified_no_pets"] == GOVERNING["verified_no_pets"]
    assert doc["rollback_target"] == _load(PINS / "deployment_state.json")["live"]["deploy_id"]
