"""PTF-DISCOVERY-P0-001 -- advisory coverage-audit tests.

Every anomaly code gets a boundary pair (fires at the boundary, silent one
step inside), plus the clean market, accepted-gap suppression, independence
collapse, unzoned surfacing, determinism, and a live smoke run over both
real markets asserting SHAPE only -- the live anomaly CONTENT is operator
review material, never a test expectation (the audit is advisory and its
thresholds are uncalibrated priors).
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from scripts.pettripfinder.coverage_audit import (
    ANOMALY_CODES,
    CA_BRAND_FAMILY_GAP,
    CA_DENSITY_HIGH,
    CA_DENSITY_LOW,
    CA_EMPTY_EXPECTED_ZONE,
    CA_SINGLE_FAMILY_SHARE_HIGH,
    CA_SOURCE_FRAGILITY,
    CA_ZONE_BELOW_MIN,
    CENSUS_KIND_IDENTITY,
    DEFAULT_THRESHOLDS,
    CoverageAuditError,
    audit_market,
    load_coverage_config,
    run_audit,
)


def _market(corridors=()):
    return SimpleNamespace(
        market_id="test-market",
        corridors=[SimpleNamespace(slug=slug, name=slug.title(),
                                   minimum_hotel_count=minimum)
                   for slug, minimum in corridors])


def _config(**overrides):
    config = {
        "schema": "ptf-coverage-config/1.0",
        "market_id": "test-market",
        "census_kind": CENSUS_KIND_IDENTITY,
        "population": 100000,
        "thresholds": dict(DEFAULT_THRESHOLDS),
        "non_independent_family_pairs": [],
        "source_family_overrides": {},
        "zones_min_expected": {},
        "accepted_gaps": [],
    }
    config.update(overrides)
    return config


def _records(count, zone_id="downtown", family="CVB", name="Sample Hotel"):
    return [{"name": "%s %d" % (name, i), "city": "Sampleton",
             "postal_code": "44100", "zone_id": zone_id, "family": family}
            for i in range(count)]


def _run(market, config, records):
    return audit_market(market, config, records, "2026-08-07", [])


def _codes(report):
    return [a["code"] for a in report["anomalies"]]


#: A census that fires NOTHING under the default thresholds: enough
#: properties for density, three independent families, share forced under
#: the ceiling by a below-threshold single-family ceiling override... the
#: simplest honest way is a family-untracked census (family checks are then
#: not evaluable) with healthy density and full zones.
def _clean_setup():
    market = _market([("downtown", 5)])
    config = _config(population=100000)
    records = _records(10, family="")
    return market, config, records


class TestCleanMarket:
    def test_clean_market_fires_nothing(self):
        report = _run(*_clean_setup())
        assert report["anomalies"] == []
        assert report["suppressed"] == []


class TestZoneAnomalies:
    def test_empty_expected_zone_fires_high(self):
        market = _market([("downtown", 5), ("airport", 1)])
        report = _run(market, _config(), _records(10, family=""))
        assert _codes(report) == [CA_EMPTY_EXPECTED_ZONE]
        assert report["anomalies"][0]["zone_id"] == "airport"
        assert report["anomalies"][0]["severity"] == "HIGH"

    def test_zone_at_zero_expectation_stays_silent_when_empty(self):
        market = _market([("downtown", 5), ("optional", 0)])
        report = _run(market, _config(), _records(10, family=""))
        assert report["anomalies"] == []

    def test_below_minimum_fires_medium_and_at_minimum_is_silent(self):
        market = _market([("downtown", 5)])
        below = _run(market, _config(), _records(4))
        assert CA_ZONE_BELOW_MIN in _codes(below)
        at_minimum = _run(market, _config(), _records(5))
        assert CA_ZONE_BELOW_MIN not in _codes(at_minimum)

    def test_config_can_override_a_zone_minimum(self):
        market = _market([("downtown", 5)])
        report = _run(market, _config(zones_min_expected={"downtown": 2}),
                      _records(4))
        assert CA_ZONE_BELOW_MIN not in _codes(report)


class TestDensity:
    def test_below_floor_fires_and_at_floor_is_silent(self):
        market = _market([("downtown", 1)])
        at_floor = _run(market, _config(), _records(8))      # 0.8 per 10k
        assert CA_DENSITY_LOW not in _codes(at_floor)
        below = _run(market, _config(), _records(7))         # 0.7 per 10k
        assert CA_DENSITY_LOW in _codes(below)

    def test_above_ceiling_fires_low_severity(self):
        market = _market([("downtown", 1)])
        report = _run(market, _config(population=10000), _records(9))  # 9.0
        anomaly = next(a for a in report["anomalies"]
                       if a["code"] == CA_DENSITY_HIGH)
        assert anomaly["severity"] == "LOW"


class TestSourceFamilies:
    def _three_family_records(self):
        return (_records(4, family="CVB")
                + _records(4, family="OTA", name="Ota Hotel")
                + _records(4, family="GDS", name="Gds Hotel"))

    def test_at_min_families_silent_below_fires(self):
        market = _market([("downtown", 1)])
        three = _run(market, _config(population=10000),
                     self._three_family_records())
        assert CA_SOURCE_FRAGILITY not in _codes(three)
        two = _run(market, _config(population=10000),
                   _records(6, family="CVB") + _records(6, family="OTA"))
        assert CA_SOURCE_FRAGILITY in _codes(two)

    def test_declared_pair_collapses_and_fires(self):
        market = _market([("downtown", 1)])
        report = _run(
            market,
            _config(population=10000,
                    non_independent_family_pairs=[["OTA", "GDS"]]),
            self._three_family_records())
        assert CA_SOURCE_FRAGILITY in _codes(report)
        assert "2 independent" in next(
            a for a in report["anomalies"]
            if a["code"] == CA_SOURCE_FRAGILITY)["detail"]

    def test_single_family_share_fires_over_ceiling_only(self):
        market = _market([("downtown", 1)])
        fired = _run(market, _config(population=10000), _records(12))
        assert CA_SINGLE_FAMILY_SHARE_HIGH in _codes(fired)
        config = _config(population=10000)
        config["thresholds"]["single_family_ceiling"] = 1.0
        silent = _run(market, config, _records(12))  # share == 1.0, not >
        assert CA_SINGLE_FAMILY_SHARE_HIGH not in _codes(silent)

    def test_untracked_census_reports_no_family_anomalies(self):
        market = _market([("downtown", 1)])
        report = _run(market, _config(population=10000),
                      _records(12, family=""))
        assert CA_SOURCE_FRAGILITY not in _codes(report)
        assert CA_SINGLE_FAMILY_SHARE_HIGH not in _codes(report)
        assert report["metrics"]["source_family_tracked"] is False
        assert report["metrics"]["single_family_share"] is None


class TestBrandFamilies:
    def _branded_records(self, brands):
        return [{"name": "%s Sampleton" % brand, "city": "Sampleton",
                 "postal_code": "44100", "zone_id": "downtown", "family": ""}
                for brand in brands]

    SIX_BRANDS = ("Hampton Inn", "Courtyard by Marriott", "Hyatt Place",
                  "Holiday Inn Express", "Super 8", "Comfort Inn")

    def test_below_floor_fires_at_floor_silent(self):
        market = _market([("downtown", 1)])
        config = _config(population=250000)
        config["thresholds"]["density_floor_per_10k"] = 0.0
        silent = _run(market, config, self._branded_records(self.SIX_BRANDS))
        assert CA_BRAND_FAMILY_GAP not in _codes(silent)
        fired = _run(market, config,
                     self._branded_records(self.SIX_BRANDS[:5]))
        assert CA_BRAND_FAMILY_GAP in _codes(fired)

    def test_small_market_is_exempt(self):
        market = _market([("downtown", 1)])
        config = _config(population=249999)
        config["thresholds"]["density_floor_per_10k"] = 0.0
        report = _run(market, config, self._branded_records(("Hampton Inn",)))
        assert CA_BRAND_FAMILY_GAP not in _codes(report)

    def test_brand_matching_is_word_bounded(self):
        market = _market([("downtown", 1)])
        config = _config(population=10000)
        # "Fairfield" must not be found inside another word, and a fragment
        # must never match ("Travelodge" contains "lodge" but only the whole
        # brand phrase counts).
        report = _run(market, config, self._branded_records(
            ("The Unfairfielded Grand",)))
        assert report["metrics"]["brand_families_present"] == []


class TestSuppression:
    def test_matching_accepted_gap_moves_anomaly_to_suppressed(self):
        market = _market([("downtown", 5), ("airport", 1)])
        config = _config(accepted_gaps=[{
            "anomaly_code": CA_EMPTY_EXPECTED_ZONE, "zone_id": "airport",
            "note": "airport corridor intentionally deferred to next batch"}])
        report = _run(market, config, _records(10, family=""))
        assert report["anomalies"] == []
        assert len(report["suppressed"]) == 1
        assert report["suppressed"][0]["accepted_gap_note"].startswith(
            "airport corridor")

    def test_non_matching_entry_suppresses_nothing(self):
        market = _market([("downtown", 5), ("airport", 1)])
        config = _config(accepted_gaps=[{
            "anomaly_code": CA_EMPTY_EXPECTED_ZONE, "zone_id": "downtown",
            "note": "wrong zone"}])
        report = _run(market, config, _records(10, family=""))
        assert _codes(report) == [CA_EMPTY_EXPECTED_ZONE]
        assert report["suppressed"] == []


class TestUnzonedAndDeterminism:
    def test_unzoned_records_surface_in_metrics_not_zones(self):
        market = _market([("downtown", 1)])
        records = _records(5) + [{"name": "Floating Inn", "city": "",
                                  "postal_code": "", "zone_id": "",
                                  "family": "CVB"}]
        report = _run(market, _config(population=10000), records)
        assert report["metrics"]["unzoned_count"] == 1
        assert report["metrics"]["unzoned_names"] == ["Floating Inn"]
        assert report["zones"][0]["active_count"] == 5
        assert report["metrics"]["active_count"] == 6

    def test_identical_inputs_produce_byte_identical_reports(self):
        market, config, records = _clean_setup()
        one = json.dumps(_run(market, config, records))
        two = json.dumps(_run(market, config, records))
        assert one == two


class TestConfigValidation:
    def test_unknown_threshold_fails_closed(self, tmp_path):
        path = tmp_path / "m.json"
        path.write_text(json.dumps(_config(
            market_id="m", thresholds={"density_floor": 1})), encoding="utf-8")
        with pytest.raises(CoverageAuditError, match="unknown threshold"):
            load_coverage_config("m", path)

    def test_accepted_gap_without_note_fails_closed(self, tmp_path):
        path = tmp_path / "m.json"
        path.write_text(json.dumps(_config(
            market_id="m",
            accepted_gaps=[{"anomaly_code": CA_DENSITY_LOW, "note": ""}])),
            encoding="utf-8")
        with pytest.raises(CoverageAuditError, match="WHY"):
            load_coverage_config("m", path)

    def test_missing_config_fails_closed(self):
        with pytest.raises(CoverageAuditError, match="no coverage config"):
            load_coverage_config("no-such-market")


class TestLiveMarkets:
    """Shape-only smoke over the two real markets (spec SS6.8, adapted)."""

    @pytest.mark.parametrize("market_id", ["columbus-oh",
                                           "cleveland-akron-canton-oh"])
    def test_live_audit_shape_and_determinism(self, market_id):
        report = run_audit(market_id)
        assert report["schema"] == "ptf-coverage-audit/1.0"
        assert report["market_id"] == market_id
        assert report["metrics"]["active_count"] > 0
        for anomaly in report["anomalies"] + report["suppressed"]:
            assert anomaly["code"] in ANOMALY_CODES
            assert anomaly["severity"] in ("HIGH", "MEDIUM", "LOW")
            assert anomaly["detail"]
        assert json.dumps(report) == json.dumps(run_audit(market_id))

    def test_cleveland_census_is_family_tracked_columbus_is_not(self):
        cleveland = run_audit("cleveland-akron-canton-oh")
        assert cleveland["metrics"]["source_family_tracked"] is True
        columbus = run_audit("columbus-oh")
        assert columbus["metrics"]["source_family_tracked"] is False
        assert columbus["data_gaps"]
