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
        policy_by_key = {row["identity_key"]: row["policy_state"]
                         for row in doc["hotels"]}
        assert policy_by_key["bellwether hotel"] == enums.POLICY_CONFIRMED
        assert policy_by_key["econo lodge downtown"] == enums.VERIFIED_NO_PETS
        for row in doc["hotels"]:
            assert row["market_id"] == MARKET
            if row["identity_key"] == "bellwether hotel":
                assert row["policy_state"] == enums.POLICY_CONFIRMED
            elif row["identity_key"] == "econo lodge downtown":
                assert row["policy_state"] == enums.VERIFIED_NO_PETS
            else:
                assert row["policy_state"] == enums.POLICY_NOT_VERIFIED
            assert row["state"] in {"KY", "IN"}
            assert is_canonical_key(row["identity_key"])
            assert row["identity_key"] == ptf_identity_key(row["canonical_name"])
            assert row["corridor"] not in (None, "")

    def test_membership_and_partition_counts(self):
        rec = partition.reconcile(census.identity_keys(_census()), _partition(),
                                  market_id=MARKET)
        assert rec.agrees
        assert rec.published == 1
        assert rec.verified_no_pets == 1
        assert rec.out_of_category == 1
        assert rec.unresolved == 127
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
        assert hotel["policy_state"] == enums.POLICY_NOT_VERIFIED
        assert "Wayside Christian Mission" in hotel["notes"]
        assert "15 hotel rooms + 2 suites" in hotel["notes"]
        assert item["final_state"] == enums.AWAITING_POLICY_OBSERVATION
        assert item["resolved"] is False
        assert item["next_action"].startswith("Capture the property's pet-policy")
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

    def test_not_in_policy_routing_seed_or_contracts(self):
        for name in ("hotel_policy_facts.json",
                     "hotel_policy_facts_cleveland-akron-canton-oh.json",
                     "hotel_policy_facts_dayton-oh.json"):
            blob = (PKG / name).read_text(encoding="utf-8")
            assert "louisville-ky" not in blob
        exclusions = json.loads((PKG / "hotel_exclusions.json").read_text(
            encoding="utf-8-sig"))
        louisville_exclusions = [
            e for e in exclusions.get("exclusions", ())
            if e.get("market_id") == MARKET
        ]
        assert [e["normalized_name"] for e in louisville_exclusions] == [
            "econo lodge downtown"
        ]
        assert louisville_exclusions[0]["exclusion_state"] == enums.VERIFIED_NO_PETS
        assert louisville_exclusions[0]["evidence_quote"] == "No Pets Allowed"
        assert louisville_exclusions[0]["source_hash"] == (
            "sha256:5c854fa35d3420f346c9e1e73a6bb58d3faeb4ca6e92f2d6df9e9f147333a579"
        )
        routing = json.loads((PKG / "identity_routing.json").read_text(
            encoding="utf-8-sig"))
        assert not any(r.get("market_id") == MARKET for r in routing.get("routes", ()))
        seed = (PKG / "seed_businesses.csv").read_text(encoding="utf-8")
        assert "louisville-ky" not in seed
        assert not (REPO / "deploy" / "netlify" / "release_contracts"
                    / "louisville-ky.json").exists()
        assert MARKET not in set(available_market_ids())
        assert not (PKG / "markets" / "coverage" / "louisville-ky.json").exists()
        assert not (PKG / "hotel_policy_facts_louisville-ky.json").exists()


class TestAssignmentAndAssembler:
    def test_recompute_is_zero_diff(self):
        _, changes = recompute(MARKET)
        assert changes == []

    def test_honest_zero_is_not_assembled(self):
        market = market_by_id(load_markets(), MARKET)
        row = market_eligibility(market)
        assert row["published_count"] == 0
        assert row["assemblable"] is False
        chosen, rows = select_markets()
        assert MARKET not in [m.market_id for m in chosen]
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
        assert report["row_count"] == len(unresolved) == 127
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
        assert rec.published == 1
        assert rec.verified_no_pets == 1
        assert rec.unresolved == 127
        assert _partition()["final_state_counts"][enums.AWAITING_POLICY_OBSERVATION] == 89
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
        assert packet["founder_approvals_written"] is True
        assert packet["decision_count"] == 6

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

    def test_production_policy_file_absent(self):
        assert not (PKG / "hotel_policy_facts_louisville-ky.json").exists()
        rec = partition.reconcile(census.identity_keys(_census()), _partition(),
                                  market_id=MARKET)
        assert rec.published == 1
        assert rec.verified_no_pets == 1
        assert rec.unresolved == 127


class TestPass1FounderDecisions:
    def test_d001_d002_d003_are_authorized_d004_is_not(self):
        decisions = json.loads((
            PKG / "markets" / "reports"
            / "louisville_pass1_founder_decisions.json"
        ).read_text(encoding="utf-8-sig"))
        assert [d["decision_id"] for d in decisions["decisions"]] == [
            "D001", "D002", "D003"
        ]
        assert decisions["d004_galt_house"] == "NOT_DECIDED"
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
        held = items["21c museum hotel louisville"]
        assert held["final_state"] == enums.AWAITING_POLICY_OBSERVATION
        assert held["resolved"] is False
        assert "HOLD_PARTIAL_AFFIRMATIVE" in held["state_override_reason"]
        assert "fee basis" in held["next_action"]
        assert "fee scope" in held["next_action"]
        assert items["bellwether hotel"]["final_state"] == enums.PUBLISHED_PET_FRIENDLY
        assert items["bellwether hotel"]["resolved"] is True
        assert items["econo lodge downtown"]["final_state"] == enums.VERIFIED_NO_PETS
        assert items["econo lodge downtown"]["resolved"] is True
        for key in ("galt house hotel", "hotel louisville downtown",
                    "the brown hotel", "hotel genevieve"):
            assert items[key]["final_state"] == enums.AWAITING_POLICY_OBSERVATION
            assert items[key]["resolved"] is False
        assert decisions["published"] == 1
        assert decisions["verified_no_pets"] == 1
        assert decisions["unresolved"] == 127
        assert decisions["site_assembled"] is False
        assert decisions["release_contract_written"] is False
        assert not (PKG / "hotel_policy_facts_louisville-ky.json").exists()

    def test_d002_approves_only_source_supported_bellwether_facts(self):
        approved = json.loads((
            PKG / "markets" / "reports"
            / "louisville_pass1_approved_policy_records.json"
        ).read_text(encoding="utf-8-sig"))
        assert [h["identity_key"] for h in approved["hotels"]] == ["bellwether hotel"]
        facts = approved["hotels"][0]["facts"]
        assert facts["pets_allowed"] is True
        assert facts["species"] == {"dogs": enums.SPECIES_ACCEPTED}
        assert facts["pet_count_limit"] == 2
        assert facts["combined_weight_limit"] == {
            "value": 50, "unit": "lb", "operator": enums.OP_LTE
        }
        assert "pet_fee" not in facts
        assert "cats" not in facts["species"]
        withheld = approved["hotels"][0]["withheld_fields"]
        assert "pet_fee" in withheld
        assert approved["hotels"][0]["founder_decision_id"] == "D002"

    def test_d003_binds_econo_exclusion_to_captured_artifact(self):
        exclusions = json.loads((PKG / "hotel_exclusions.json").read_text(
            encoding="utf-8-sig"))
        econo = next(e for e in exclusions["exclusions"]
                     if e["normalized_name"] == "econo lodge downtown")
        assert econo["market_id"] == MARKET
        assert econo["exclusion_state"] == enums.VERIFIED_NO_PETS
        assert econo["evidence_quote"] == "No Pets Allowed"
        assert econo["source_url"].endswith("louisville-ky-hotel-amenities.html")
        assert econo["source_hash"] == (
            "sha256:5c854fa35d3420f346c9e1e73a6bb58d3faeb4ca6e92f2d6df9e9f147333a579"
        )
        assert "Service-animal access is not pet-friendly" in econo["notes"]
