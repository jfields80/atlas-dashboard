"""AES-DATA-004A discovery -- CLI tests (Task 12/13). No network; provider
request budgets stay at 0 (or the credential is absent) in every test here,
so an accidental live call would surface as a connection error, not a
silent pass."""

from __future__ import annotations

import json

import pytest

from scripts.pettripfinder import discovery_cli
from scripts.pettripfinder.discovery import constants as C


def test_plan_command_makes_no_output_files(tmp_path, capsys):
    rc = discovery_cli.main([
        "plan", "--market", "columbus-oh", "--providers", "google,overpass",
        "--categories", "veterinary",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "total planned queries" in out
    assert list(tmp_path.iterdir()) == []   # plan wrote nothing anywhere


def test_plan_shows_credential_availability_without_leaking_value(monkeypatch, capsys):
    monkeypatch.setenv("GOOGLE_PLACES_API_KEY", "SECRET-VALUE-ONLY-FOR-THIS-TEST")
    rc = discovery_cli.main(["plan", "--market", "columbus-oh", "--providers", "google",
                             "--categories", "veterinary"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "GOOGLE_PLACES" in out
    assert "True" in out
    assert "SECRET-VALUE-ONLY-FOR-THIS-TEST" not in out


def test_run_with_zero_caps_makes_no_live_calls_and_writes_only_output_root(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("GOOGLE_PLACES_API_KEY", "fake-key-not-used")
    output_root = tmp_path / "run1"
    rc = discovery_cli.main([
        "run", "--market", "columbus-oh", "--providers", "google,overpass",
        "--categories", "dog_park", "--output-root", str(output_root),
        "--observed-at", "2026-07-18",
        "--max-google-requests", "0", "--max-overpass-requests", "0",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "google requests made    : 0" in out
    assert "overpass requests made  : 0" in out
    candidates_path = output_root / C.CANDIDATES_SUBDIR / "columbus-oh_candidates.json"
    assert candidates_path.exists()
    assert json.loads(candidates_path.read_text(encoding="utf-8")) == []
    # nothing written outside the given output_root
    assert list(tmp_path.iterdir()) == [output_root]


def test_run_refuses_to_exceed_google_cap(tmp_path, monkeypatch):
    monkeypatch.setenv("GOOGLE_PLACES_API_KEY", "fake-key-not-used")

    class FakeResp:
        status_code = 200
        content = b'{"places": []}'

        def json(self):
            return {"places": []}

    class CapCheckingSession:
        """The budget (max_google_requests=1) permits exactly one live call
        -- this session answers that first call normally and raises on any
        call beyond it, proving the cap is actually enforced rather than
        merely documented."""

        def __init__(self):
            self.calls = 0

        def post(self, *a, **kw):
            self.calls += 1
            if self.calls > 1:
                raise AssertionError("network call attempted despite exhausted budget")
            return FakeResp()

    from scripts.pettripfinder.discovery.google_places import GooglePlacesClient
    from scripts.pettripfinder.discovery.runner import RunConfig, execute_run

    config = RunConfig(
        market_id="columbus-oh", providers=(C.PROVIDER_GOOGLE_PLACES,),
        categories=(C.CATEGORY_DOG_PARK,), output_root=str(tmp_path / "run2"),
        observed_at="2026-07-18", max_google_requests=1,
    )
    # 13 cells x 1 template = 13 possible Google queries; budget allows only 1.
    session = CapCheckingSession()
    market, queries, results, candidates = execute_run(
        config, google_client=GooglePlacesClient(session=session))
    assert session.calls == 1
    completed_or_skipped = [r.state for r in results if r.provider == C.PROVIDER_GOOGLE_PLACES]
    assert completed_or_skipped.count(C.QUERY_STATE_SKIPPED_CAP_REACHED) >= 1
    total_google_requests = sum(r.requests_made for r in results if r.provider == C.PROVIDER_GOOGLE_PLACES)
    assert total_google_requests <= 1


def test_foursquare_absence_does_not_block_other_providers(tmp_path, monkeypatch):
    monkeypatch.setenv("GOOGLE_PLACES_API_KEY", "fake-key-not-used")
    monkeypatch.delenv(C.FOURSQUARE_API_KEY_ENV, raising=False)
    output_root = tmp_path / "run3"
    rc = discovery_cli.main([
        "run", "--market", "columbus-oh", "--providers", "google,overpass,foursquare",
        "--categories", "dog_park", "--output-root", str(output_root),
        "--observed-at", "2026-07-18",
        "--max-google-requests", "0", "--max-overpass-requests", "0",
    ])
    assert rc == 0   # no crash despite foursquare being unavailable


def test_report_command_regenerates_html_without_network(tmp_path, monkeypatch):
    monkeypatch.setenv("GOOGLE_PLACES_API_KEY", "fake-key-not-used")
    output_root = tmp_path / "run4"
    discovery_cli.main([
        "run", "--market", "columbus-oh", "--providers", "overpass",
        "--categories", "dog_park", "--output-root", str(output_root),
        "--observed-at", "2026-07-18", "--max-overpass-requests", "0",
    ])
    rc = discovery_cli.main(["report", "--market", "columbus-oh", "--output-root", str(output_root)])
    assert rc == 0
    html_path = output_root / C.REPORTS_SUBDIR / "columbus-oh_coverage.html"
    assert html_path.exists()


def test_report_command_missing_run_returns_error(tmp_path):
    rc = discovery_cli.main(["report", "--market", "columbus-oh",
                             "--output-root", str(tmp_path / "never-ran")])
    assert rc == 2


def test_dry_run_flag_on_run_command_makes_no_output(tmp_path, capsys):
    output_root = tmp_path / "run5"
    rc = discovery_cli.main([
        "run", "--market", "columbus-oh", "--providers", "google",
        "--categories", "veterinary", "--output-root", str(output_root),
        "--dry-run",
    ])
    assert rc == 0
    assert not output_root.exists()
    out = capsys.readouterr().out
    assert "total planned queries" in out


def test_unknown_provider_alias_rejected():
    import pytest
    with pytest.raises(SystemExit):
        discovery_cli.main(["plan", "--market", "columbus-oh", "--providers", "yelp"])


def test_unknown_category_rejected():
    import pytest
    with pytest.raises(SystemExit):
        discovery_cli.main(["plan", "--market", "columbus-oh", "--categories", "not_a_category"])


class TestOverpassEndpointIsExplicit:
    """PTF-INDIANAPOLIS-HARDENED-RECENSUS-002: overpass-api.de went dark (HTTP 000
    at the connect timeout, its lz4/z backends too) while two other public mirrors
    answered in a second. The client deliberately never falls back, so the run
    must let the operator NAME the mirror -- and record it."""

    def test_the_run_config_carries_the_endpoint_the_operator_named(self, monkeypatch):
        from scripts.pettripfinder.discovery import constants as C
        from scripts.pettripfinder import discovery_cli
        captured = {}

        def fake_execute(config, **_kw):
            captured["endpoint"] = config.overpass_endpoint
            raise SystemExit(0)

        monkeypatch.setattr(discovery_cli, "execute_run", fake_execute)
        monkeypatch.delenv(C.OVERPASS_ENDPOINT_ENV, raising=False)
        with pytest.raises(SystemExit):
            discovery_cli.main(["run", "--market", "columbus-oh", "--providers", "overpass",
                                "--max-overpass-requests", "1",
                                "--output-root", "data/discovery/_test_endpoint",
                                "--overpass-endpoint", "https://mirror.example/api/interpreter"])
        assert captured["endpoint"] == "https://mirror.example/api/interpreter"

    def test_the_environment_supplies_the_default_and_the_constant_is_the_last_resort(self, monkeypatch):
        from scripts.pettripfinder.discovery import constants as C
        from scripts.pettripfinder import discovery_cli
        import argparse
        monkeypatch.setenv(C.OVERPASS_ENDPOINT_ENV, "https://env.example/api/interpreter")
        p = argparse.ArgumentParser()
        discovery_cli._add_common_run_args(p)
        assert p.parse_args(["--market", "x"]).overpass_endpoint == "https://env.example/api/interpreter"
        monkeypatch.delenv(C.OVERPASS_ENDPOINT_ENV)
        p = argparse.ArgumentParser()
        discovery_cli._add_common_run_args(p)
        assert p.parse_args(["--market", "x"]).overpass_endpoint == C.OVERPASS_DEFAULT_ENDPOINT

    def test_the_runner_hands_the_named_endpoint_to_the_client(self):
        from scripts.pettripfinder.discovery.runner import RunConfig
        from scripts.pettripfinder.discovery import constants as C
        cfg = RunConfig(market_id="columbus-oh", providers=("OPENSTREETMAP",),
                        categories=("hotel",), output_root="x", observed_at="2026-08-25")
        assert cfg.overpass_endpoint == C.OVERPASS_DEFAULT_ENDPOINT
        cfg2 = RunConfig(market_id="columbus-oh", providers=("OPENSTREETMAP",),
                         categories=("hotel",), output_root="x", observed_at="2026-08-25",
                         overpass_endpoint="https://mirror.example/api/interpreter")
        assert cfg2.overpass_endpoint == "https://mirror.example/api/interpreter"
