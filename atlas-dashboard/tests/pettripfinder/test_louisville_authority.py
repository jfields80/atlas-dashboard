"""PTF-LOUISVILLE-MARKET-BUILD-001 -- unpublished KY/IN factory isolation."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.pettripfinder.assemble_production_site import (
    market_eligibility, select_markets,
)
from scripts.pettripfinder.build_louisville_founder_review_queue import write_queue
from scripts.pettripfinder.contracts import census, enums, partition
from scripts.pettripfinder.contracts.identity_key import (
    is_canonical_key, ptf_identity_key,
)
from scripts.pettripfinder.discovery.market_config import load_market_config
from scripts.pettripfinder.discovery.source_families import FAMILY_CVB, family_of
from scripts.pettripfinder.markets import homepage_config, load_markets, market_by_id
from scripts.pettripfinder.normalize_census_geography import recompute
from scripts.pettripfinder.release_contracts import available_market_ids

REPO = Path(__file__).resolve().parents[2]
PKG = REPO / "launch_packages" / "pettripfinder"
MARKET = "louisville-ky"
CENSUS = 130
CURRENT_PUBLISHED = 14
CURRENT_NO_PETS = 4
CURRENT_UNRESOLVED = 111


def _census():
    return json.loads((PKG / "identity_census" / "louisville-ky.json").read_text(
        encoding="utf-8-sig"))


def _partition():
    return json.loads((PKG / "louisville_final_partition_001.json").read_text(
        encoding="utf-8-sig"))


class TestMarketIdentity:
    def test_registry_identity(self):
        market = market_by_id(load_markets(), MARKET)
        assert market.market_id == MARKET
        assert market.market_slug == MARKET
        assert market.market_name == "Louisville, Kentucky"
        assert market.primary_city == "Louisville"
        assert market.primary_state_code == "KY"
        assert list(market.states) == ["KY", "IN"]
        assert market.route_mode == "market_prefixed"
        assert market.show_in_navigation is False
        assert market.show_in_sitemap is False
        assert market.minimum_published_hotels == 5

    def test_homepage_is_derived_without_a_hero(self):
        hp = homepage_config(market_by_id(load_markets(), MARKET))
        assert hp.hero_image == ""
        assert hp.search_location == "Louisville, KY"
        assert hp.city_label == "Louisville"
        assert "Columbus" not in hp.title


class TestCensusAndPartition:
    def test_schema_and_policy_silence(self):
        doc = _census()
        assert doc["schema"] == enums.CENSUS_SCHEMA
        assert doc["count"] == len(doc["hotels"]) == CENSUS
        for row in doc["hotels"]:
            assert row["market_id"] == MARKET
            assert row["policy_state"] in {enums.POLICY_NOT_VERIFIED,
                                           enums.POLICY_CONFIRMED,
                                           enums.VERIFIED_NO_PETS}
            assert row["state"] in {"KY", "IN"}
            assert is_canonical_key(row["identity_key"])
            assert row["identity_key"] == ptf_identity_key(row["canonical_name"])
            assert row["corridor"] not in (None, "")

    def test_membership_and_partition_counts(self):
        rec = partition.reconcile(census.identity_keys(_census()), _partition(),
                                  market_id=MARKET)
        assert rec.agrees
        assert rec.published == CURRENT_PUBLISHED
        assert rec.verified_no_pets == CURRENT_NO_PETS
        assert rec.out_of_category == 1
        assert rec.unresolved == CURRENT_UNRESOLVED
        assert rec.published + rec.verified_no_pets + rec.out_of_category + rec.unresolved == CENSUS
        assert partition.validate(_partition()) == ()
        assert census.validate(_census(), market_states=["KY", "IN"]) == ()

    def test_unresolved_rows_have_one_action(self):
        for item in _partition()["items"]:
            if item["final_state"] in enums.TERMINAL_STATES:
                assert item["next_action"] == ""
                assert item["resolved"] is True
                continue
            assert item["next_action"].strip()
            assert item["next_action_source"]
            assert item["determined_by"]

    def test_hotel_louisville_downtown_include_in_census(self):
        hotel = next(h for h in _census()["hotels"]
                     if h["identity_key"] == "hotel louisville downtown")
        item = next(i for i in _partition()["items"]
                    if i["identity_key"] == "hotel louisville downtown")
        assert hotel["lodging_state"] == enums.LODGING_CONFIRMED
        assert hotel["identity_state"] == enums.IDENTITY_CONFIRMED
        assert hotel["policy_state"] == enums.VERIFIED_NO_PETS
        assert "Wayside Christian Mission" in hotel["notes"]
        assert "15 hotel rooms + 2 suites" in hotel["notes"]
        assert item["final_state"] == enums.VERIFIED_NO_PETS
        assert item["resolved"] is True
        assert item["next_action"] == ""
        names = {h["canonical_name"] for h in _census()["hotels"]}
        assert "Hospital Hospitality House of Louisville" not in names


class TestIsolation:
    def test_no_cross_market_identity(self):
        ours = census.identity_keys(_census())
        for other in ("columbus-oh", "cleveland-akron-canton-oh", "dayton-oh",
                      "cincinnati-oh"):
            foreign = census.identity_keys(json.loads(
                (PKG / "identity_census" / ("%s.json" % other)).read_text(
                    encoding="utf-8-sig")))
            assert ours & foreign == set(), other

    def test_no_cincinnati_zip_or_nky_city(self):
        forbidden_zips = {
            "41011", "41014", "41015", "41016", "41017", "41018", "41042",
            "41048", "41051", "41071", "41072", "41073", "41075", "41091",
            "41094", "41035", "41040", "41097", "41002", "41004", "41095",
            "47001", "47025", "47040", "47012",
        }
        forbidden_cities = {
            ("Covington", "KY"), ("Newport", "KY"), ("Florence", "KY"),
            ("Lawrenceburg", "IN"), ("Aurora", "IN"), ("Rising Sun", "IN"),
            ("Brookville", "IN"), ("Greendale", "IN"),
        }
        for row in _census()["hotels"]:
            assert row["postal_code"][:5] not in forbidden_zips, row["canonical_name"]
            assert (row["city"], row["state"]) not in forbidden_cities

    def test_louisville_authority_is_market_scoped(self):
        for name in ("hotel_policy_facts.json",
                     "hotel_policy_facts_cleveland-akron-canton-oh.json",
                     "hotel_policy_facts_dayton-oh.json"):
            blob = (PKG / name).read_text(encoding="utf-8")
            assert "louisville-ky" not in blob
        exclusions = json.loads((PKG / "hotel_exclusions.json").read_text(
            encoding="utf-8-sig"))
        louisville_exclusions = [e for e in exclusions.get("exclusions", ())
                                 if e.get("market_id") == MARKET]
        assert sum(e.get("exclusion_state") == enums.VERIFIED_NO_PETS
                   for e in louisville_exclusions) == CURRENT_NO_PETS
        assert sum(e.get("exclusion_state") == enums.OUT_OF_CURRENT_CATEGORY
                   for e in louisville_exclusions) == 1
        routing = json.loads((PKG / "identity_routing.json").read_text(
            encoding="utf-8-sig"))
        assert not any(r.get("market_id") == MARKET for r in routing.get("routes", ()))
        seed = (PKG / "seed_businesses.csv").read_text(encoding="utf-8")
        assert seed.count(",louisville-ky\n") == CURRENT_PUBLISHED
        contract_path = (REPO / "deploy" / "netlify" / "release_contracts"
                         / "louisville-ky.json")
        assert contract_path.is_file()
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        assert contract["market_id"] == MARKET
        assert contract["deployment_authorization"]["grants_deployment"] is False
        assert MARKET in set(available_market_ids())
        assert not (PKG / "markets" / "coverage" / "louisville-ky.json").exists()
        assert (PKG / "hotel_policy_facts_louisville-ky.json").exists()


class TestAssignmentAndAssembler:
    def test_recompute_is_zero_diff(self):
        _, changes = recompute(MARKET)
        assert changes == []

    def test_current_authority_is_assembled(self):
        market = market_by_id(load_markets(), MARKET)
        row = market_eligibility(market)
        assert row["published_count"] == CURRENT_PUBLISHED
        assert row["assemblable"] is True
        chosen, rows = select_markets()
        assert MARKET in [m.market_id for m in chosen]
        assert MARKET in [r["market_id"] for r in rows]


class TestDiscoveryAndQueue:
    def test_discovery_config_loads(self):
        m = load_market_config(MARKET)
        assert m.market_id == MARKET
        assert family_of("goto_louisville") == FAMILY_CVB
        assert family_of("soin_tourism") == FAMILY_CVB

    def test_queue_identity_set_equals_unresolved_partition(self, tmp_path):
        report = write_queue(tmp_path)
        unresolved = {i["identity_key"] for i in _partition()["items"]
                      if i["final_state"] not in enums.TERMINAL_STATES}
        assert set(report["identity_keys"]) == unresolved
        assert report["duplicates"] == 0
        assert report["omissions"] == 0
        assert report["row_count"] == len(unresolved) == CURRENT_UNRESOLVED
        assert "21c museum hotel louisville" in unresolved
        assert "bellwether hotel" not in unresolved
        assert "econo lodge downtown" not in unresolved
        assert report["review_status"] == "NOT_STARTED"
        import csv
        with (tmp_path / "work-browser-pass-001-review.csv").open(
                encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
        keys = [r["identity_key"] for r in rows]
        assert keys == report["identity_keys"]
        assert all(r["hotel ID"] == r["identity_key"] for r in rows)
        assert all(r["review_status"] == "NOT_STARTED" for r in rows)


class TestIdentityRoutingRepair:
    def test_desk_pass_covers_exactly_the_110(self):
        repair = json.loads((
            PKG / "markets" / "reports"
            / "louisville_identity_routing_repair_001.json"
        ).read_text(encoding="utf-8-sig"))
        keys = [r["identity_key"] for r in repair["rows"]]
        assert repair["desk_total"] == len(keys) == 110
        assert len(set(keys)) == 110
        assert repair["desk_class_counts"] == {
            "IDENTITY_REVIEW": 65,
            "PROPERTY_LEVEL_URL_RECOVERY": 42,
            "ROUTING_REPLACEMENT": 3,
        }
        assert "gotolouisville.com/directory" not in json.dumps([
            r["official_url"] for r in repair["rows"] if r["capture_ready"]
        ])

    def test_capture_ready_queue_002_is_bound_and_unpublished(self):
        ready = json.loads((
            PKG / "markets" / "reports"
            / "louisville_capture_ready_queue_002.json"
        ).read_text(encoding="utf-8-sig"))
        keys = [r["identity_key"] for r in ready["items"]]
        assert ready["count"] == len(keys) == 91
        assert ready["prior_ready"] == 19
        assert ready["newly_ready"] == 72
        assert len(set(keys)) == 91
        assert all(r["official_url"] for r in ready["items"])
        assert all("gotolouisville.com/directory" not in r["official_url"]
                   for r in ready["items"])
        rec = partition.reconcile(census.identity_keys(_census()), _partition(),
                                  market_id=MARKET)
        assert (rec.published, rec.verified_no_pets, rec.unresolved) == (
            CURRENT_PUBLISHED, CURRENT_NO_PETS, CURRENT_UNRESOLVED)
        assert _partition()["final_state_counts"][enums.AWAITING_POLICY_OBSERVATION] == 73
        assert _partition()["final_state_counts"][enums.AWAITING_CENSUS_REVIEW] == 6


class TestPass1Capture:
    BATCH = [
        "21c museum hotel louisville",
        "bellwether hotel",
        "econo lodge downtown",
        "galt house hotel",
        "hotel genevieve",
        "hotel louisville downtown",
        "the brown hotel",
    ]

    def _results(self):
        return json.loads((
            PKG / "markets" / "reports" / "louisville_pass1_capture_results.json"
        ).read_text(encoding="utf-8-sig"))

    def test_batch_is_exactly_the_seven_independents(self):
        doc = self._results()
        keys = [r["identity_key"] for r in doc["rows"]]
        assert doc["batch_total"] == len(keys) == 7
        assert keys == self.BATCH
        assert doc["authority_changed"] is False

    def test_outcomes_and_founder_packet(self):
        doc = self._results()
        by = {r["identity_key"]: r["outcome"] for r in doc["rows"]}
        assert by["21c museum hotel louisville"] == "AFFIRMATIVE_PARTIAL"
        assert by["bellwether hotel"] == "AFFIRMATIVE_STRUCTURED"
        assert by["econo lodge downtown"] == "NEGATIVE"
        assert by["galt house hotel"] == "AFFIRMATIVE_STRUCTURED"
        assert by["hotel genevieve"] == "ACCESS_BLOCKED"
        assert by["hotel louisville downtown"] == "NEGATIVE"
        assert by["the brown hotel"] == "NEGATIVE"
        assert doc["positive_candidates"] == 3
        assert doc["negative_candidates"] == 3
        assert doc["publication_grade_artifacts"] == 6
        packet = json.loads((
            PKG / "markets" / "reports"
            / "louisville_pass1_founder_review_packet.json"
        ).read_text(encoding="utf-8-sig"))
        assert packet["founder_approvals_written"] is False
        assert packet["founder_decisions_recorded"] is True
        assert packet["authority_applied"] is False
        assert packet["merged"] is False
        assert packet["deployed"] is False
        assert packet["decision_count"] == 6
        assert packet["recorded_decision_count"] == 6

    def test_quotes_are_contiguous_in_gitignored_artifacts(self):
        import hashlib
        art = REPO / "data" / "operator_evidence" / "louisville-pass1-capture-001"
        doc = self._results()
        for row in doc["rows"]:
            if not row["artifact_sha256"]:
                continue
            path = art / row["artifact_relpath"]
            payload = path.read_bytes()
            assert hashlib.sha256(payload).hexdigest() == row["artifact_sha256"]
            html = payload.decode("utf-8", "replace")
            if row["identity_key"] == "hotel louisville downtown":
                assert "No, only service animals are welcome at the property." in html
            else:
                for quote in row["quotes"]:
                    assert quote in html, row["identity_key"]

    def test_capture_was_later_materialized_by_founding_application(self):
        facts = json.loads((PKG / "hotel_policy_facts_louisville-ky.json").read_text(
            encoding="utf-8-sig"))
        assert len(facts["hotels"]) == CURRENT_PUBLISHED
        rec = partition.reconcile(census.identity_keys(_census()), _partition(),
                                  market_id=MARKET)
        assert (rec.published, rec.verified_no_pets, rec.unresolved) == (
            CURRENT_PUBLISHED, CURRENT_NO_PETS, CURRENT_UNRESOLVED)


class TestPass1FounderDecisions:
    def test_d001_through_d006_are_recorded_and_not_applied(self):
        decisions = json.loads((
            PKG / "markets" / "reports"
            / "louisville_pass1_founder_decisions.json"
        ).read_text(encoding="utf-8-sig"))
        assert [d["decision_id"] for d in decisions["decisions"]] == [
            "D001", "D002", "D003", "D004", "D005", "D006"
        ]
        assert decisions["authority_applied"] is False
        assert decisions["merged"] is False
        assert decisions["deployed"] is False
        assert decisions["d004_galt_house"] == "RECORDED_NOT_APPLIED"
        by_id = {d["decision_id"]: d for d in decisions["decisions"]}
        assert by_id["D001"]["applied"] is False
        assert by_id["D002"]["applied"] is False
        assert by_id["D003"]["applied"] is False
        assert by_id["D004"]["applied"] is False
        assert by_id["D005"]["applied"] is False
        assert by_id["D006"]["applied"] is False
        assert by_id["D004"]["identity_key"] == "galt house hotel"
        assert by_id["D005"]["identity_key"] == "hotel louisville downtown"
        assert by_id["D006"]["identity_key"] == "the brown hotel"
        d001 = decisions["decisions"][0]
        assert d001["identity_key"] == "21c museum hotel louisville"
        assert d001["decision"] == "HOLD_PARTIAL_AFFIRMATIVE"
        assert d001["publish"] is False
        assert d001["queue"] is True
        preserved = d001["preserved"]
        assert preserved["identity_binding"] == "BOUND"
        assert preserved["artifact_sha256"]
        assert preserved["exact_quotes"]
        assert preserved["captured_partial_facts"]["pets_allowed"] is True
        assert "fee basis" in preserved["next_action"]
        assert "fee scope" in preserved["next_action"]
        items = {i["identity_key"]: i for i in _partition()["items"]}
        assert items["bellwether hotel"]["final_state"] == enums.PUBLISHED_PET_FRIENDLY
        for key in ("econo lodge downtown", "hotel louisville downtown", "the brown hotel"):
            assert items[key]["final_state"] == enums.VERIFIED_NO_PETS
        for key in ("21c museum hotel louisville", "hotel genevieve"):
            assert items[key]["resolved"] is False
            assert items[key]["resolved"] is False
        assert decisions["published"] == 0
        assert decisions["verified_no_pets"] == 0
        assert decisions["unresolved"] == 129
        assert decisions["site_assembled"] is False
        assert decisions["release_contract_written"] is False
        assert (PKG / "hotel_policy_facts_louisville-ky.json").exists()
        assert not (PKG / "markets" / "reports"
                    / "louisville_pass1_approved_policy_records.json").exists()


class TestPass1DecisionsRecordedNotApplied:
    def _packet(self):
        return json.loads((
            PKG / "markets" / "reports"
            / "louisville_pass1_founder_review_packet.json"
        ).read_text(encoding="utf-8-sig"))

    def test_six_founder_decisions_are_recorded_verbatim(self):
        packet = self._packet()
        recorded = packet["founder_decisions"]
        assert [d["decision_id"] for d in recorded] == [
            "D001", "D002", "D003", "D004", "D005", "D006"
        ]
        assert packet["authority_applied"] is False
        assert packet["merged"] is False
        assert packet["deployed"] is False
        assert packet["recorded_summary"] == {
            "decisions_recorded": 6,
            "approvals_positive": 2,
            "verified_no_pets": 3,
            "holds": 1,
            "no_decision_blocked_rows": 1,
        }
        by_id = {d["decision_id"]: d for d in recorded}
        assert by_id["D001"]["decision"] == "HOLD_PARTIAL_AFFIRMATIVE"
        assert by_id["D002"]["decision"] == "APPROVE_AFFIRMATIVE_STRUCTURED"
        assert by_id["D003"]["decision"] == "APPROVE_VERIFIED_NO_PETS"
        assert by_id["D004"]["decision"] == "APPROVE_AFFIRMATIVE_STRUCTURED"
        assert by_id["D004"]["identity_key"] == "galt house hotel"
        assert by_id["D005"]["decision"] == "APPROVE_VERIFIED_NO_PETS"
        assert by_id["D005"]["identity_key"] == "hotel louisville downtown"
        assert by_id["D006"]["decision"] == "APPROVE_VERIFIED_NO_PETS"
        assert by_id["D006"]["identity_key"] == "the brown hotel"
        assert "SOURCE SILENCE = ABSENCE" in by_id["D004"]["verbatim"]
        assert "Hospital Hospitality House" in by_id["D005"]["verbatim"]
        assert packet["publish"] is False

    def test_d004_d005_d006_are_not_applied_to_authority(self):
        packet = self._packet()
        assert packet["authority_applied_for"] == []
        assert packet["authority_not_applied_for"] == [
            "D001", "D002", "D003", "D004", "D005", "D006"
        ]
        applied = {d["decision_id"]: d["authority_applied"]
                   for d in packet["founder_decisions"]}
        assert applied == {
            "D001": False, "D002": False, "D003": False,
            "D004": False, "D005": False, "D006": False,
        }
        items = {i["identity_key"]: i for i in _partition()["items"]}
        assert items["galt house hotel"]["final_state"] == enums.PUBLISHED_PET_FRIENDLY
        assert items["hotel louisville downtown"]["final_state"] == enums.VERIFIED_NO_PETS
        rec = partition.reconcile(census.identity_keys(_census()), _partition(),
                                  market_id=MARKET)
        assert (rec.published, rec.verified_no_pets, rec.unresolved) == (
            CURRENT_PUBLISHED, CURRENT_NO_PETS, CURRENT_UNRESOLVED)
        assert not (PKG / "markets" / "reports"
                    / "louisville_pass1_approved_policy_records.json").exists()
        exclusions = json.loads((PKG / "hotel_exclusions.json").read_text(
            encoding="utf-8-sig"))
        louisville = [e for e in exclusions["exclusions"]
                      if e.get("market_id") == MARKET]
        assert sum(e["exclusion_state"] == enums.VERIFIED_NO_PETS
                   for e in louisville) == CURRENT_NO_PETS
        assert sum(e["exclusion_state"] == enums.OUT_OF_CURRENT_CATEGORY
                   for e in louisville) == 1
        assert (PKG / "hotel_policy_facts_louisville-ky.json").exists()

    def test_hotel_genevieve_has_no_founder_policy_decision(self):
        packet = self._packet()
        blocked = packet["no_founder_policy_decision"]
        assert len(blocked) == 1
        genevieve = blocked[0]
        assert genevieve["identity_key"] == "hotel genevieve"
        assert genevieve["founder_policy_decision"] == "NONE"
        assert genevieve["decision_id"] is None
        assert genevieve["recommended_next_state"] == "AWAITING_ATTENDED_CAPTURE"
        assert genevieve["lane"] == "HYATT_MANUAL"
        row = next(r for r in packet["rows"]
                   if r["identity_key"] == "hotel genevieve")
        assert row["founder_decision"] == "NO_FOUNDER_POLICY_DECISION"
        assert row["founder_decision_id"] is None
        items = {i["identity_key"]: i for i in _partition()["items"]}
        assert items["hotel genevieve"]["final_state"] == enums.AWAITING_POLICY_OBSERVATION
        assert items["hotel genevieve"]["resolved"] is False

    def test_next_batch_was_the_five_independents(self):
        batch = json.loads((
            PKG / "markets" / "reports"
            / "louisville_pass2_capture_batch_prepared.json"
        ).read_text(encoding="utf-8-sig"))
        assert batch["executed"] is True
        assert batch["executed_work_order"] == (
            "PTF-LOUISVILLE-ATTENDED-CAPTURE-PASS2-001"
        )
        keys = [r["identity_key"] for r in batch["items"]]
        assert keys == [
            "omni louisville hotel",
            "drury inn and suites louisville",
            "drury inn and suites louisville north",
            "best western greentree inn",
            "radisson hotel louisville north",
        ]
        for row in batch["items"]:
            assert row["executed"] is False
            assert row["official_url"]
            assert row["identity_binding"]
            host = row["official_url"].split("/")[2]
            assert host not in {
                "www.hilton.com", "www.hyatt.com", "www.marriott.com"
            }
        east = batch["items"][1]
        assert east["identity_binding"] == "URL_BOUND_IDENTITY_CORRECTION_OPEN"
        assert east["official_url"].endswith("drury-inn-and-suites-louisville-east")


class TestPass2Capture:
    BATCH = [
        "omni louisville hotel",
        "drury inn and suites louisville",
        "drury inn and suites louisville north",
        "best western greentree inn",
        "radisson hotel louisville north",
    ]

    def _results(self):
        return json.loads((
            PKG / "markets" / "reports" / "louisville_pass2_capture_results.json"
        ).read_text(encoding="utf-8-sig"))

    def test_batch_is_exactly_the_five_prepared_independents(self):
        doc = self._results()
        keys = [r["identity_key"] for r in doc["rows"]]
        assert doc["batch_total"] == len(keys) == 5
        assert keys == self.BATCH
        assert doc["authority_changed"] is False
        for key in self.BATCH:
            host = next(r["queued_url"] for r in doc["rows"]
                        if r["identity_key"] == key).split("/")[2]
            assert host not in {
                "www.hilton.com", "www.hyatt.com", "www.marriott.com"
            }

    def test_outcomes_and_founder_packet(self):
        doc = self._results()
        by = {r["identity_key"]: r["outcome"] for r in doc["rows"]}
        assert by["omni louisville hotel"] == "AFFIRMATIVE_STRUCTURED"
        assert by["drury inn and suites louisville"] == (
            "POLICY_CAPTURED_PENDING_IDENTITY_CORRECTION"
        )
        assert by["drury inn and suites louisville north"] == (
            "AFFIRMATIVE_STRUCTURED"
        )
        assert by["best western greentree inn"] == "ACCESS_BLOCKED"
        assert by["radisson hotel louisville north"] == "ACCESS_BLOCKED"
        assert doc["positive_candidates"] == 2
        assert doc["negative_candidates"] == 0
        assert doc["identity_correction_candidates"] == 1
        assert doc["publication_grade_artifacts"] == 3
        assert doc["founder_decisions_required"] == 3
        packet = json.loads((
            PKG / "markets" / "reports"
            / "louisville_pass2_founder_review_packet.json"
        ).read_text(encoding="utf-8-sig"))
        assert packet["founder_approvals_written"] is False
        assert packet["decision_count"] == 3

    def test_identity_binding_and_drury_east_correction(self):
        by = {r["identity_key"]: r for r in self._results()["rows"]}
        assert by["omni louisville hotel"]["identity_binding"] == "BOUND"
        assert "Omni Louisville Hotel" in by["omni louisville hotel"]["identity_signals"]
        assert by["drury inn and suites louisville north"]["identity_binding"] == "BOUND"
        east = by["drury inn and suites louisville"]
        assert east["identity_binding"] == "URL_BOUND_IDENTITY_CORRECTION_OPEN"
        corr = east["identity_correction"]
        assert corr["census_canonical_name"] == "Drury Inn and Suites Louisville"
        assert corr["observed_official_name"] == (
            "Drury Inn & Suites Louisville East"
        )
        assert corr["census_address"] == corr["observed_address"] == (
            "9501 Blairwood Road"
        )
        assert "East" in corr["discrepancy"]
        assert "do not silently rename" in corr["proposed_identity_correction"].lower()
        assert by["best western greentree inn"]["identity_binding"] == "NOT_BOUND"
        assert by["radisson hotel louisville north"]["identity_binding"] == "NOT_BOUND"

    def test_quotes_are_contiguous_in_gitignored_artifacts(self):
        import hashlib
        art = REPO / "data" / "operator_evidence" / "louisville-pass2-capture-001"
        for row in self._results()["rows"]:
            if not row["artifact_sha256"]:
                continue
            path = art / row["artifact_relpath"]
            payload = path.read_bytes()
            assert hashlib.sha256(payload).hexdigest() == row["artifact_sha256"]
            html = payload.decode("utf-8", "replace")
            for quote in row["quotes"]:
                assert quote in html, row["identity_key"]

    def test_capture_provenance_survives_later_authority_application(self):
        rec = partition.reconcile(census.identity_keys(_census()), _partition(),
                                  market_id=MARKET)
        assert (rec.published, rec.verified_no_pets, rec.unresolved) == (14, 4, 111)
        assert (PKG / "hotel_policy_facts_louisville-ky.json").exists()
        packet = json.loads((
            PKG / "markets" / "reports"
            / "louisville_pass2_founder_review_packet.json"
        ).read_text(encoding="utf-8-sig"))
        assert packet["founder_approvals_written"] is False
        decisions = json.loads((
            PKG / "markets" / "reports"
            / "louisville_pass1_founder_decisions.json"
        ).read_text(encoding="utf-8-sig"))
        assert decisions["authority_applied"] is False
        assert all(d["applied"] is False for d in decisions["decisions"])


class TestPass2FounderDecisionsRecorded:
    def test_three_pass2_decisions_are_recorded_and_not_applied(self):
        decisions = json.loads((
            PKG / "markets" / "reports"
            / "louisville_pass2_founder_decisions.json"
        ).read_text(encoding="utf-8-sig"))
        assert [d["decision_id"] for d in decisions["decisions"]] == [
            "P2-001", "P2-002", "P2-003"
        ]
        assert decisions["authority_applied"] is False
        assert decisions["merged"] is False
        assert decisions["deployed"] is False
        by_id = {d["decision_id"]: d for d in decisions["decisions"]}
        assert by_id["P2-001"]["decision"] == "APPROVE_AFFIRMATIVE_STRUCTURED"
        assert by_id["P2-001"]["identity_key"] == "omni louisville hotel"
        assert "other_charges" in by_id["P2-001"]["approved_fact_keys"]
        assert "pet_fee" not in by_id["P2-001"]["approved_fact_keys"]
        assert by_id["P2-002"]["decision"] == "HOLD_IDENTITY_CORRECTION"
        assert by_id["P2-002"]["policy_approval"] is False
        assert by_id["P2-003"]["decision"] == "APPROVE_AFFIRMATIVE_STRUCTURED"
        assert by_id["P2-003"]["combined_weight_limit"]["value"] == 80
        assert "scope" not in by_id["P2-003"]["combined_weight_limit"]
        assert all(d["applied"] is False for d in decisions["decisions"])
        blocked = decisions["no_founder_policy_decision"]
        assert [b["identity_key"] for b in blocked] == [
            "best western greentree inn",
            "radisson hotel louisville north",
        ]
        assert all(b["founder_policy_decision"] == "NONE" for b in blocked)
        packet = json.loads((
            PKG / "markets" / "reports"
            / "louisville_pass2_founder_review_packet.json"
        ).read_text(encoding="utf-8-sig"))
        assert packet["founder_approvals_written"] is False
        assert packet["founder_decisions_recorded"] is True
        assert packet["recorded_summary"]["decisions_recorded"] == 3
        assert packet["recorded_summary"]["approvals_positive"] == 2

    def test_drury_east_identity_action_is_prepared_and_not_executed(self):
        action = json.loads((
            PKG / "markets" / "reports"
            / "louisville_drury_east_identity_resolution_action.json"
        ).read_text(encoding="utf-8-sig"))
        assert action["executed"] is False
        assert action["current_census_canonical_name"] == (
            "Drury Inn and Suites Louisville"
        )
        assert action["observed_property_name"] == (
            "Drury Inn & Suites Louisville East"
        )
        assert action["current_census_address"] == action["observed_property_address"]
        assert action["phone"] == "502-326-4170"
        assert action["drury_property_location_identifier"] == "0105"
        assert "East" in action["exact_mismatch"]
        assert "Do not silently rename" in action["next_action"]

    def test_pass1_plus_pass2_reconcile_is_mechanical(self):
        rec = json.loads((
            PKG / "markets" / "reports"
            / "louisville_pass1_plus_pass2_founder_decision_reconcile.json"
        ).read_text(encoding="utf-8-sig"))
        assert rec["authority_applied"] is False
        assert rec["combined"] == {
            "decisions_recorded": 9,
            "approvals_positive": 4,
            "verified_no_pets": 3,
            "holds": 2,
            "no_decision_blocked_rows": 3,
            "decisions_applied": 0,
        }
        p1 = rec["pass1"]
        p2 = rec["pass2"]
        assert (p1["decisions_recorded"] + p2["decisions_recorded"]
                == rec["combined"]["decisions_recorded"])
        assert (p1["approvals_positive"] + p2["approvals_positive"]
                == rec["combined"]["approvals_positive"])
        assert (p1["holds"] + p2["holds"] == rec["combined"]["holds"])
        assert (p1["no_decision_blocked_rows"] + p2["no_decision_blocked_rows"]
                == rec["combined"]["no_decision_blocked_rows"])

    def test_pass3_batch_is_prepared_clean_and_not_executed(self):
        batch = json.loads((
            PKG / "markets" / "reports"
            / "louisville_pass3_capture_batch_prepared.json"
        ).read_text(encoding="utf-8-sig"))
        assert batch["executed"] is True
        assert batch["executed_work_order"] == (
            "PTF-LOUISVILLE-ATTENDED-CAPTURE-PASS3-001"
        )
        assert 10 <= batch["count"] == len(batch["items"]) <= 15
        keys = [r["identity_key"] for r in batch["items"]]
        assert "myriad hotel" in keys
        assert "drury inn and suites louisville" not in keys
        assert "best western greentree inn" not in keys
        assert "radisson hotel louisville north" not in keys
        for row in batch["items"]:
            assert row["executed"] is False
            assert row["desk_identity_class"] != "IDENTITY_CORRECTION_REQUIRED"
            host = row["official_url"].split("/")[2]
            assert host not in {"www.hilton.com", "www.hyatt.com"}
        rec = partition.reconcile(census.identity_keys(_census()), _partition(),
                                  market_id=MARKET)
        assert (rec.published, rec.verified_no_pets, rec.unresolved) == (14, 4, 111)


class TestPass3Capture:
    BATCH = [
        "myriad hotel",
        "red roof inn louisville expo airport",
        "red roof inn louisville hurstbourne",
        "studio 6 louisville airport expo center",
        "baymont by wyndham louisville airport south",
        "hawthorn suites by wyndham louisville east",
        "travelodge by wyndham sellersburg louisville north",
        "super 8 by wyndham louisville airport",
        "la quinta inn and suites by wyndham louisville northeast old henry",
        "holiday inn express and suites jeffersonville",
        "staybridge suites louisville east",
        "candlewood suites louisville airport",
    ]

    def _results(self):
        return json.loads((
            PKG / "markets" / "reports" / "louisville_pass3_capture_results.json"
        ).read_text(encoding="utf-8-sig"))

    def test_batch_is_exactly_the_twelve_prepared_rows(self):
        doc = self._results()
        keys = [r["identity_key"] for r in doc["rows"]]
        assert doc["batch_total"] == len(keys) == 12
        assert keys == self.BATCH
        assert doc["authority_changed"] is False
        for row in doc["rows"]:
            host = row["queued_url"].split("/")[2]
            assert host not in {"www.hilton.com", "www.hyatt.com"}

    def test_outcomes_identity_and_packet(self):
        doc = self._results()
        by = {r["identity_key"]: r for r in doc["rows"]}
        assert by["myriad hotel"]["outcome"] == "POLICY_NOT_FOUND"
        assert by["myriad hotel"]["identity_binding"] == "BOUND"
        assert by["red roof inn louisville expo airport"]["outcome"] == "ACCESS_BLOCKED"
        assert by["red roof inn louisville hurstbourne"]["outcome"] == "ACCESS_BLOCKED"
        assert by["studio 6 louisville airport expo center"]["outcome"] == "CAPTURE_FAILED"
        assert by["baymont by wyndham louisville airport south"]["outcome"] == "POLICY_NOT_FOUND"
        assert by["hawthorn suites by wyndham louisville east"]["outcome"] == "POLICY_NOT_FOUND"
        assert by["travelodge by wyndham sellersburg louisville north"]["outcome"] == "POLICY_NOT_FOUND"
        assert by["super 8 by wyndham louisville airport"]["outcome"] == "POLICY_NOT_FOUND"
        lq = by["la quinta inn and suites by wyndham louisville northeast old henry"]
        assert lq["outcome"] == "POLICY_NOT_FOUND"
        assert lq["identity_binding"] == "BOUND"
        assert "Terra View" in " ".join(lq["identity_signals"])
        assert by["holiday inn express and suites jeffersonville"]["outcome"] == "ACCESS_BLOCKED"
        assert by["staybridge suites louisville east"]["outcome"] == "ACCESS_BLOCKED"
        assert by["candlewood suites louisville airport"]["outcome"] == "ACCESS_BLOCKED"
        assert doc["positive_candidates"] == 0
        assert doc["negative_candidates"] == 0
        assert doc["publication_grade_artifacts"] == 6
        packet = json.loads((
            PKG / "markets" / "reports"
            / "louisville_pass3_founder_review_packet.json"
        ).read_text(encoding="utf-8-sig"))
        assert packet["founder_approvals_written"] is False

    def test_artifact_hashes_and_identity_signals(self):
        import hashlib
        art = REPO / "data" / "operator_evidence" / "louisville-pass3-capture-001"
        for row in self._results()["rows"]:
            if not row["artifact_sha256"]:
                continue
            path = art / row["artifact_relpath"]
            payload = path.read_bytes()
            assert hashlib.sha256(payload).hexdigest() == row["artifact_sha256"]
            html = payload.decode("utf-8", "replace")
            for signal in row["identity_signals"]:
                assert signal in html, row["identity_key"]
            for quote in row["quotes"]:
                assert quote in html, row["identity_key"]

    def test_pass3_provenance_survives_later_authority_application(self):
        rec = partition.reconcile(census.identity_keys(_census()), _partition(),
                                  market_id=MARKET)
        assert (rec.published, rec.verified_no_pets, rec.unresolved) == (14, 4, 111)
        assert (PKG / "hotel_policy_facts_louisville-ky.json").exists()
        p1 = json.loads((
            PKG / "markets" / "reports"
            / "louisville_pass1_founder_decisions.json"
        ).read_text(encoding="utf-8-sig"))
        p2 = json.loads((
            PKG / "markets" / "reports"
            / "louisville_pass2_founder_decisions.json"
        ).read_text(encoding="utf-8-sig"))
        assert p1["authority_applied"] is False
        assert p2["authority_applied"] is False


class TestBrandSurfaceRepair001:
    def test_twelve_pass3_rows_reclassified_once(self):
        repair = json.loads((
            PKG / "markets" / "reports"
            / "louisville_brand_surface_repair_001.json"
        ).read_text(encoding="utf-8-sig"))
        p3 = json.loads((
            PKG / "markets" / "reports"
            / "louisville_pass3_capture_results.json"
        ).read_text(encoding="utf-8-sig"))
        keys = [r["identity_key"] for r in repair["rows"]]
        assert len(keys) == len(set(keys)) == 12
        assert keys == [r["identity_key"] for r in p3["rows"]]
        assert repair["retained_policy_not_found"] == 1
        assert repair["attended_policy_surface"] == 5
        assert repair["attended_required"] == 6
        assert repair["generic_capture_rerun"] is False
        assert repair["authority_changed"] is False
        for row in repair["rows"]:
            assert row["outcome_if_policy_remains_absent"].startswith(
                "POLICY_NOT_FOUND"
            )
        by = {r["identity_key"]: r for r in repair["rows"]}
        assert by["myriad hotel"]["reclassified_outcome"] == "POLICY_NOT_FOUND"
        assert by["myriad hotel"]["retain_policy_not_found"] is True
        for key in (
            "baymont by wyndham louisville airport south",
            "hawthorn suites by wyndham louisville east",
            "travelodge by wyndham sellersburg louisville north",
            "super 8 by wyndham louisville airport",
            "la quinta inn and suites by wyndham louisville northeast old henry",
        ):
            assert by[key]["reclassified_outcome"] == "ATTENDED_POLICY_SURFACE"
            assert by[key]["materially_different_path_exists"] is True
        lq = by["la quinta inn and suites by wyndham louisville northeast old henry"]
        assert "old-henry" in lq["final_url"]
        assert "Alliant" not in lq["identity_check"]
        for key in (
            "holiday inn express and suites jeffersonville",
            "staybridge suites louisville east",
            "candlewood suites louisville airport",
            "red roof inn louisville expo airport",
            "red roof inn louisville hurstbourne",
            "studio 6 louisville airport expo center",
        ):
            assert by[key]["reclassified_outcome"] == "ATTENDED_REQUIRED"

    def test_manual_queue_excludes_myriad_and_is_not_executed(self):
        queue = json.loads((
            PKG / "markets" / "reports"
            / "louisville_manual_capture_queue_001.json"
        ).read_text(encoding="utf-8-sig"))
        assert queue["executed"] is False
        assert queue["count"] == len(queue["items"]) == 11
        keys = [r["identity_key"] for r in queue["items"]]
        assert "myriad hotel" not in keys
        assert queue["excluded_from_queue"] == ["myriad hotel"]
        for row in queue["items"]:
            assert row["exact_property_url"]
            assert row["browser_path"]
            assert row["expected_policy_surface"]
            assert row["identity_check"]
            assert row["artifact_requirement"]
            assert row["rate_limit_session_caution"]
            assert row["outcome_if_policy_remains_absent"].startswith(
                "POLICY_NOT_FOUND"
            )
            assert "VERIFIED_NO_PETS" in row["outcome_if_policy_remains_absent"]
        rec = partition.reconcile(census.identity_keys(_census()), _partition(),
                                  market_id=MARKET)
        assert (rec.published, rec.verified_no_pets, rec.unresolved) == (14, 4, 111)


class TestRoutingVsEvidenceReady:
    def test_remaining_queue_is_routing_ready_not_evidence_ready(self):
        doc = json.loads((
            PKG / "markets" / "reports"
            / "louisville_routing_vs_evidence_ready_001.json"
        ).read_text(encoding="utf-8-sig"))
        assert doc["global_contract_changed"] is False
        assert doc["manual_queue_executed"] is False
        assert doc["remaining_legacy_ready"] == 67
        assert doc["evidence_ready_remaining"] == 0
        assert doc["routing_ready_remaining"] == 59
        assert doc["routing_ready_identity_hold"] == 8
        assert (doc["routing_ready_remaining"]
                + doc["routing_ready_identity_hold"]
                == doc["remaining_legacy_ready"])
        keys = [r["identity_key"] for r in doc["items"]]
        assert len(keys) == len(set(keys)) == 67
        assert all(r["legacy_capture_ready"] is True for r in doc["items"])
        assert all(r["readiness"] != "EVIDENCE_READY" for r in doc["items"])
        queue = json.loads((
            PKG / "markets" / "reports"
            / "louisville_manual_capture_queue_001.json"
        ).read_text(encoding="utf-8-sig"))
        assert queue["executed"] is False
        rec = partition.reconcile(census.identity_keys(_census()), _partition(),
                                  market_id=MARKET)
        assert (rec.published, rec.verified_no_pets, rec.unresolved) == (14, 4, 111)


class TestPass4Capture:
    BATCH = [
        "red roof inn louisville expo airport",
        "red roof inn louisville hurstbourne",
        "studio 6 louisville airport expo center",
        "baymont by wyndham louisville airport south",
        "hawthorn suites by wyndham louisville east",
        "travelodge by wyndham sellersburg louisville north",
        "super 8 by wyndham louisville airport",
        "la quinta inn and suites by wyndham louisville northeast old henry",
        "holiday inn express and suites jeffersonville",
        "staybridge suites louisville east",
        "candlewood suites louisville airport",
    ]

    VALID_OUTCOMES = frozenset({
        "PUBLICATION_CANDIDATE", "VERIFIED_NO_PETS_CANDIDATE",
        "POLICY_NOT_FOUND", "IDENTITY_UNCERTAIN", "ACCESS_BLOCKED",
        "CAPTURE_FAILED", "SOURCE_AMBIGUOUS",
    })

    def _results(self):
        return json.loads((
            PKG / "markets" / "reports"
            / "louisville_attended_capture_pass4_001.json"
        ).read_text(encoding="utf-8-sig"))

    def _packet(self):
        return json.loads((
            PKG / "markets" / "reports"
            / "louisville_attended_capture_pass4_founder_review_packet.json"
        ).read_text(encoding="utf-8-sig"))

    def test_batch_is_exactly_the_eleven_queued_rows(self):
        doc = self._results()
        keys = [r["identity_key"] for r in doc["rows"]]
        assert doc["batch_total"] == len(keys) == 11
        assert keys == self.BATCH
        assert len(set(keys)) == 11
        assert doc["authority_changed"] is False

    def test_every_row_has_a_terminal_outcome_and_identity_binding(self):
        doc = self._results()
        for row in doc["rows"]:
            assert row["outcome"] in self.VALID_OUTCOMES
            assert row["identity_binding"] == "BOUND"
            assert row["identity_signals"]
            assert row["artifacts"]

    def test_outcome_counts(self):
        doc = self._results()
        assert doc["outcome_counts"]["PUBLICATION_CANDIDATE"] == 10
        assert doc["outcome_counts"]["VERIFIED_NO_PETS_CANDIDATE"] == 1
        assert doc["outcome_counts"]["POLICY_NOT_FOUND"] == 0
        assert doc["outcome_counts"]["ACCESS_BLOCKED"] == 0
        assert doc["outcome_counts"]["CAPTURE_FAILED"] == 0
        assert doc["outcome_counts"]["IDENTITY_UNCERTAIN"] == 0
        assert doc["outcome_counts"]["SOURCE_AMBIGUOUS"] == 0
        assert doc["brand_counts"] == {
            "RED_ROOF": 2, "STUDIO6": 1, "WYNDHAM": 5, "IHG": 3,
        }
        assert doc["publication_grade_artifacts"] == 11

    def test_holiday_inn_express_is_explicit_no_pets_not_silence(self):
        doc = self._results()
        by = {r["identity_key"]: r for r in doc["rows"]}
        hie = by["holiday inn express and suites jeffersonville"]
        assert hie["outcome"] == "VERIFIED_NO_PETS_CANDIDATE"
        assert hie["proposed_facts"]["pets_allowed"] is False
        assert "No, pets are not allowed" in hie["quotes"][0]

    def test_red_roof_pair_share_the_same_bound_fee_schedule(self):
        doc = self._results()
        by = {r["identity_key"]: r for r in doc["rows"]}
        expo = by["red roof inn louisville expo airport"]
        hurst = by["red roof inn louisville hurstbourne"]
        assert expo["outcome"] == hurst["outcome"] == "PUBLICATION_CANDIDATE"
        assert (expo["proposed_facts"]["weight_limit_lbs"]
                == hurst["proposed_facts"]["weight_limit_lbs"] == 80)
        assert expo["queued_url"].endswith("rri118")
        assert hurst["queued_url"].endswith("rri034")

    def test_contradictions_and_ambiguities_are_withheld_not_resolved(self):
        doc = self._results()
        by = {r["identity_key"]: r for r in doc["rows"]}
        staybridge = by["staybridge suites louisville east"]
        assert "fee_refundable" not in staybridge["proposed_facts"]
        assert "CONTRADICTORY" in staybridge["withheld_fields"]["fee_refundable"]
        candlewood = by["candlewood suites louisville airport"]
        assert "AMBIGUOUS" in (
            candlewood["withheld_fields"]["deposit_vs_fee_relationship"])
        super8 = by["super 8 by wyndham louisville airport"]
        assert "species" in super8["withheld_fields"]
        assert "species" not in super8["proposed_facts"]

    def test_studio6_is_partial_not_fabricated(self):
        doc = self._results()
        studio6 = next(r for r in doc["rows"]
                        if r["identity_key"]
                        == "studio 6 louisville airport expo center")
        assert studio6["proposed_facts"] == {"pets_allowed": True}
        assert "fee" in studio6["withheld_fields"]
        assert "weight_limit" in studio6["withheld_fields"]

    def test_la_quinta_uses_the_corrected_old_henry_url(self):
        doc = self._results()
        lq = next(r for r in doc["rows"]
                  if r["identity_key"] == (
                      "la quinta inn and suites by wyndham louisville "
                      "northeast old henry"))
        assert "old-henry" in lq["final_url"]
        assert "Alliant" not in " ".join(lq["identity_signals"])

    def test_artifacts_exist_on_disk_and_hash_match(self):
        import hashlib
        art = REPO / "data" / "operator_evidence" / "louisville-pass4-capture-001"
        doc = self._results()
        for row in doc["rows"]:
            for a in row["artifacts"]:
                path = art / a["relpath"]
                assert path.is_file(), a["relpath"]
                payload = path.read_bytes()
                assert hashlib.sha256(payload).hexdigest() == a["sha256"]
                assert path.stat().st_size == a["bytes"]

    def test_quotes_are_contiguous_in_their_text_artifacts(self):
        art = REPO / "data" / "operator_evidence" / "louisville-pass4-capture-001"
        doc = self._results()
        for row in doc["rows"]:
            if not row["quotes"]:
                continue
            text_artifacts = [a for a in row["artifacts"]
                               if a["relpath"].endswith(".txt")]
            assert text_artifacts, row["identity_key"]
            blob = "\n".join(
                (art / a["relpath"]).read_text(encoding="utf-8")
                for a in text_artifacts)
            for quote in row["quotes"]:
                assert quote in blob, row["identity_key"]

    def test_founder_review_packet_covers_all_eleven_with_no_approvals(self):
        packet = self._packet()
        assert packet["founder_approvals_written"] is False
        assert packet["decision_count"] == 11
        assert len(packet["rows"]) == 11
        keys = [r["identity_key"] for r in packet["rows"]]
        assert keys == self.BATCH

    def test_authority_freeze_holds_after_pass4(self):
        rec = partition.reconcile(census.identity_keys(_census()), _partition(),
                                  market_id=MARKET)
        assert (rec.published, rec.verified_no_pets, rec.unresolved) == (14, 4, 111)
        assert (PKG / "hotel_policy_facts_louisville-ky.json").exists()
        queue = json.loads((
            PKG / "markets" / "reports"
            / "louisville_manual_capture_queue_001.json"
        ).read_text(encoding="utf-8-sig"))
        assert queue["executed"] is False


class TestPass4FounderDecisions:
    def test_all_eleven_founder_decisions_are_recorded_not_applied(self):
        decisions = json.loads((
            PKG / "markets" / "reports"
            / "louisville_pass4_founder_decisions.json"
        ).read_text(encoding="utf-8-sig"))
        assert decisions["recorded_decision_count"] == 11
        assert decisions["recorded_summary"] == {
            "approvals_positive": 10,
            "verified_no_pets": 1,
            "approve_with_change": 3,
            "decisions_applied": 0,
        }
        assert decisions["authority_applied"] is False
        assert all(d["applied"] is False for d in decisions["decisions"])
        by = {d["identity_key"]: d for d in decisions["decisions"]}
        assert by["studio 6 louisville airport expo center"]["approved_facts"] == {
            "pets_allowed": True
        }
        assert "property_wide_guest_deposit" in by[
            "red roof inn louisville hurstbourne"]["withheld_fields"]
        assert by["staybridge suites louisville east"]["decision"] == (
            "APPROVE_WITH_CHANGE"
        )
        assert "refundability" in by[
            "staybridge suites louisville east"]["withheld_fields"]
        assert by["holiday inn express and suites jeffersonville"][
            "decision"] == "APPROVE_VERIFIED_NO_PETS"

    def test_all_pass_reconciliation_and_atomic_application_are_prepared(self):
        rec = json.loads((
            PKG / "markets" / "reports"
            / "louisville_pass1_plus_pass2_plus_pass4_founder_decision_reconcile.json"
        ).read_text(encoding="utf-8-sig"))
        assert rec["combined"] == {
            "decisions_recorded": 20,
            "approvals_positive": 14,
            "verified_no_pets": 4,
            "holds": 2,
            "no_decision_blocked_rows": 3,
            "decisions_applied": 0,
        }
        application = json.loads((
            PKG / "markets" / "reports"
            / "louisville_pass4_decision_application_prepared.json"
        ).read_text(encoding="utf-8-sig"))
        assert application["work_order"] == (
            "PTF-LOUISVILLE-PASS4-DECISION-APPLICATION-001"
        )
        assert application["executed"] is False
        assert application["atomic_application"] is True
        assert len(application["approved_positive_keys"]) == 14
        assert len(application["approved_verified_no_pets_keys"]) == 4
        assert application["expected_post_application"] == {
            "published": 14, "verified_no_pets": 4, "unresolved": 111,
        }
        rec_state = partition.reconcile(census.identity_keys(_census()), _partition(),
                                        market_id=MARKET)
        assert (rec_state.published, rec_state.verified_no_pets) == (14, 4)


class TestLouisvilleAuthorityApplication001A:
    def test_contract_unblocker_and_partition_baseline_are_prepared(self):
        doc = json.loads((PKG / "markets" / "reports" /
            "louisville_founding_authority_application_001a_prepared.json"
        ).read_text(encoding="utf-8-sig"))
        assert doc["executed"] is True
        assert doc["contract_validation"]["travelodge_representable"] is True
        assert doc["contract_validation"]["super8_representable"] is True
        assert doc["contract_validation"]["sanitation_kind"] == "sanitation_fee"
        assert len(doc["approved_row_contracts"]) == 18
        assert {row["evidence_contract"] for row in doc["approved_row_contracts"]} == {
            "CONTRACT_VALID"
        }
        baseline = doc["partition_baseline"]
        assert baseline == {
            "census": 130, "published": 0, "verified_no_pets": 0,
            "out_of_current_category": 1,
            "out_of_current_category_keys": ["the inn at woodhaven"],
            "unresolved": 129,
            "other_terminal": 0, "reconciliation_agrees": True,
            "equation": "130 = 0 published + 0 verified_no_pets + 1 out_of_current_category + 129 unresolved + 0 other_terminal",
        }
