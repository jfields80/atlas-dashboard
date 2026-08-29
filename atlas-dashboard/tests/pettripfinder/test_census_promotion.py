"""census_promotion: a founder-approved plan applied to a COPY of a census, validated, re-keyed."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.pettripfinder import census_promotion as CP  # noqa: E402


def _row(name, key=None, **extra):
    from scripts.pettripfinder.contracts.identity_key import ptf_identity_key
    key = key or ptf_identity_key(name)
    row = {"identity_key": key, "canonical_name": name, "display_name": name, "slug": key.replace(" ", "-"),
           "market_id": "testville-xx", "address": "1 Main Street", "city": "Testville", "state": "XX",
           "postal_code": "46000", "phone": "", "official_url": "", "identity_state": "IDENTITY_CONFIRMED",
           "lodging_state": "LODGING", "policy_state": "POLICY_NOT_VERIFIED", "corridor": "testville__core",
           "assignment_basis": "postal_code", "assignment_value": "46000", "normalized_name": key}
    row.update(extra)
    return row


def _census():
    return {"schema": "ptf-market-identity-census/1.1", "market_id": "testville-xx", "count": 6, "hotels": [
        _row("Courtyard", address="11550 Whistle Drive", phone="3175587588", official_url="https://www.marriott.com/indcf"),
        _row("Courtyard by Marriott Testville Fishers", address="9690 North by Northeast Boulevard"),
        _row("Hampton Inn Testville Northeast Castleton", address="6817 East 82nd Street"),
        _row("Hampton Inn Testville - NE / Castleton", address="6817 East 82nd Street", phone="3175760220",
             official_url="https://www.hilton.com/en/hotels/indnehx"),
        _row("Cambria Hotel Testville", address="2244 East Main Street", phone="3172792394",
             official_url="https://www.choicehotels.com/indiana/whitestown/woodspring-hotels"),
        _row("The Westin Testville", address="241 West Washington Street", postal_code="46204"),
    ]}


def _plan(**over):
    plan = {"schema": CP.PLAN_SCHEMA, "market_id": "testville-xx", "work_order": "PTF-TEST", "decided_by": "PTF-FOUNDER-001",
            "retirements": [{"retired_identity_key": "courtyard by marriott testville fishers",
                             "in_favour_of": "courtyard by marriott testville fishers", "why": "stale twin"}],
            "merges": [{"surviving_identity_key": "hampton inn testville northeast castleton",
                        "retired_identity_key": "hampton inn testville ne castleton",
                        "observation_from_identity_key": "hampton inn testville ne castleton",
                        "census_fields_from_retired_row": ["phone", "official_url"], "ledger_rows": [25, 26]}],
            "renames": [{"identity_key": "courtyard", "from": "Courtyard", "to": "Courtyard by Marriott Testville Fishers",
                         "new_identity_key": "courtyard by marriott testville fishers", "ledger_row": 5}],
            "phone_corrections": [{"identity_key": "cambria hotel testville", "clear_phone": "3172792394"}],
            "url_corrections": [{"identity_key": "cambria hotel testville",
                                 "from": "https://www.choicehotels.com/indiana/whitestown/woodspring-hotels", "to": ""}],
            "address_supersessions": [{"identity_key": "the westin testville", "prior_census_address": "50 South Capitol Avenue, 46204",
                                       "first_party_address": "241 West Washington Street, 46204"}]}
    plan.update(over)
    return plan


def _pilot():
    return {"market_id": "testville-xx", "results": [
        {"identity_key": "courtyard", "canonical_name": "Courtyard", "outcome": "VALID", "artifact_dir": "a"},
        {"identity_key": "hampton inn testville ne castleton", "canonical_name": "Hampton Inn Testville - NE / Castleton", "outcome": "VALID", "artifact_dir": "b"},
        {"identity_key": "hampton inn testville northeast castleton", "canonical_name": "Hampton Inn Testville Northeast Castleton", "outcome": "VALID", "artifact_dir": "c"},
        {"identity_key": "the westin testville", "canonical_name": "The Westin Testville", "outcome": "VALID", "artifact_dir": "d"},
    ]}


def test_the_plan_reshapes_a_copy_and_the_input_is_untouched():
    census = _census()
    before = [h["identity_key"] for h in census["hotels"]]
    shadow, key_map, report = CP.apply_plan(_plan(), census)
    assert [h["identity_key"] for h in census["hotels"]] == before
    keys = [h["identity_key"] for h in shadow["hotels"]]
    assert keys == ["cambria hotel testville", "courtyard by marriott testville fishers",
                    "hampton inn testville northeast castleton", "the westin testville"]
    assert shadow["count"] == 4 and report["from_count"] == 6 and report["to_count"] == 4


def test_a_rename_rekeys_by_the_identity_contract_and_records_where_it_came_from():
    shadow, key_map, _ = CP.apply_plan(_plan(), _census())
    row = next(h for h in shadow["hotels"] if h["identity_key"] == "courtyard by marriott testville fishers")
    assert row["canonical_name"] == "Courtyard by Marriott Testville Fishers"
    assert row["slug"] == "courtyard-by-marriott-testville-fishers" and row["normalized_name"] == row["identity_key"]
    assert row["name_before_promotion"] == "Courtyard" and row["promotion"]["renamed_from"] == "courtyard"
    assert row["phone"] == "3175587588"  # the renamed OSM row keeps its own values
    assert key_map["courtyard"] == "courtyard by marriott testville fishers"
    assert key_map["courtyard by marriott testville fishers"] == "courtyard by marriott testville fishers"


def test_a_rename_into_a_key_that_still_exists_refuses():
    with pytest.raises(CP.PromotionError):
        CP.apply_plan(_plan(retirements=[]), _census())


def test_a_merge_takes_only_what_the_survivor_lacks():
    shadow, key_map, report = CP.apply_plan(_plan(), _census())
    row = next(h for h in shadow["hotels"] if h["identity_key"] == "hampton inn testville northeast castleton")
    assert row["phone"] == "3175760220" and row["official_url"] == "https://www.hilton.com/en/hotels/indnehx"
    assert row["canonical_name"] == "Hampton Inn Testville Northeast Castleton"
    assert row["promotion"]["merged_from"] == ["hampton inn testville ne castleton"]
    assert key_map["hampton inn testville ne castleton"] == "hampton inn testville northeast castleton"
    assert report["merged"][0]["fields_taken_from_retired_row"] == {"phone": "3175760220", "official_url": "https://www.hilton.com/en/hotels/indnehx"}


def test_phone_and_url_corrections_clear_proven_wrong_values_without_inventing():
    shadow, _, report = CP.apply_plan(_plan(), _census())
    row = next(h for h in shadow["hotels"] if h["identity_key"] == "cambria hotel testville")
    assert row["phone"] == "" and row["official_url"] == ""
    assert row["promotion"]["phone_cleared"] == "3172792394"
    assert {c["field"] for c in report["corrections"]} == {"phone", "official_url"}


def test_a_correction_that_does_not_match_the_row_refuses():
    with pytest.raises(CP.PromotionError):
        CP.apply_plan(_plan(phone_corrections=[{"identity_key": "cambria hotel testville", "clear_phone": "0000000000"}]), _census())


def test_an_address_supersession_is_verified_against_the_prior_census_not_applied():
    prior = {"hotels": [_row("The Westin Testville", address="50 South Capitol Avenue", postal_code="46204")]}
    shadow, _, report = CP.apply_plan(_plan(), _census(), prior_census=prior)
    row = next(h for h in shadow["hotels"] if h["identity_key"] == "the westin testville")
    assert row["address"] == "241 West Washington Street"
    assert report["address_supersessions_verified"][0]["prior_census_address"] == "50 South Capitol Avenue, 46204"


def test_an_unknown_key_anywhere_in_the_plan_refuses():
    with pytest.raises(CP.PromotionError):
        CP.apply_plan(_plan(retirements=[{"retired_identity_key": "nobody", "in_favour_of": "x"}]), _census())


def test_the_pilot_is_rekeyed_and_the_merged_away_capture_is_superseded_not_dropped():
    shadow, key_map, _ = CP.apply_plan(_plan(), _census())
    rekeyed, report = CP.rekey_pilot(_pilot(), _plan(), key_map, shadow)
    keys = [r["identity_key"] for r in rekeyed["results"]]
    assert keys == ["courtyard by marriott testville fishers", "hampton inn testville northeast castleton", "the westin testville"]
    survivor = rekeyed["results"][1]
    assert survivor["artifact_dir"] == "b" and survivor["promotion_identity_key_was"] == "hampton inn testville ne castleton"
    assert survivor["canonical_name"] == "Hampton Inn Testville Northeast Castleton"
    assert rekeyed["results"][0]["canonical_name"] == "Courtyard by Marriott Testville Fishers"
    assert report["superseded"][0]["identity_key"] == "hampton inn testville northeast castleton"
    assert report["results_in"] == 4 and report["results_out"] == 3


def test_roll_ups_are_recomputed_for_the_shadow():
    census = _census()
    census["identity_state_counts"] = {"IDENTITY_CONFIRMED": 6}
    census["identity_key_collisions"] = [{"identity_key": "courtyard by marriott testville fishers", "note": "prior twin"},
                                         {"identity_key": "the westin testville", "note": "kept"}]
    shadow, _, _ = CP.apply_plan(_plan(), census)
    assert shadow["identity_state_counts"] == {"IDENTITY_CONFIRMED": 4}
    assert [c["identity_key"] for c in shadow["identity_key_collisions"]] == [
        "courtyard by marriott testville fishers", "the westin testville"]


def test_the_cli_refuses_to_overwrite_its_input(tmp_path):
    import json
    census = tmp_path / "census.json"
    census.write_text(json.dumps(_census()), encoding="utf-8")
    (tmp_path / "plan.json").write_text(json.dumps(_plan()), encoding="utf-8")
    (tmp_path / "pilot.json").write_text(json.dumps(_pilot()), encoding="utf-8")
    with pytest.raises(CP.PromotionError):
        CP.main(["--market", "testville-xx", "--plan", str(tmp_path / "plan.json"), "--census", str(census),
                 "--pilot", str(tmp_path / "pilot.json"), "--out-census", str(census),
                 "--out-pilot", str(tmp_path / "p.json"), "--out-report", str(tmp_path / "r.json")])
