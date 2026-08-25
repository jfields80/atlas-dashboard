"""PTF-INDIANAPOLIS-HARDENED-RECENSUS-002 -- re-censusing a REGISTERED market.

Indianapolis is registered, published in source, and its release contract pins
``identity_census/indianapolis-in.json`` at 153 rows. The generic factory reads
and writes the census by convention, so a rebuild on the generic path would have
overwritten the pinned file and broken ``verify_all()`` for every market. The
census location is therefore a run-level setting, and these tests prove every
generic tool in the factory chain honours it -- and that, unset, nothing moves.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from scripts.pettripfinder import census_location as CL

FACTORY_CHAIN = (
    "scripts.pettripfinder.market_census_cli",
    "scripts.pettripfinder.market_factory_cli",
    "scripts.pettripfinder.market_closure_cli",
    "scripts.pettripfinder.market_coverage_cli",
    "scripts.pettripfinder.market_founder_review_cli",
    "scripts.pettripfinder.market_benchmark_cli",
    "scripts.pettripfinder.market_reconciliation_report",
    "scripts.pettripfinder.normalize_census_geography",
    "scripts.pettripfinder.geography_assignment_diff",
    "scripts.pettripfinder.census_partition_builder",
    "scripts.pettripfinder.discovery.census_url_recovery",
    "scripts.pettripfinder.discovery.census_duplicate_scan",
    "scripts.pettripfinder.acquisition.market_paid_acquisition",
    "scripts.pettripfinder.acquisition.direct_http_pilot",
)


@pytest.fixture
def restore_modules():
    yield
    for name in FACTORY_CHAIN:
        importlib.reload(importlib.import_module(name))


class TestUnsetMeansCommitted:
    def test_the_default_is_the_committed_directory(self, monkeypatch):
        monkeypatch.delenv(CL.ENV, raising=False)
        assert CL.identity_census_dir() == CL.COMMITTED_CENSUS_DIR
        assert not CL.is_overridden()
        assert CL.relative_census_path("x-y") == \
            "launch_packages/pettripfinder/identity_census/x-y.json"

    def test_the_committed_directory_is_the_one_the_release_contracts_pin(self):
        assert CL.COMMITTED_CENSUS_DIR.as_posix().endswith(
            "launch_packages/pettripfinder/identity_census")
        assert (CL.COMMITTED_CENSUS_DIR / "indianapolis-in.json").is_file()


class TestSetMeansEveryToolMoves:
    def test_a_repo_relative_override_resolves_under_the_repo(self, monkeypatch):
        monkeypatch.setenv(CL.ENV, "launch_packages/pettripfinder/identity_census_proposed")
        assert CL.identity_census_dir() == CL.PROPOSED_CENSUS_DIR
        assert CL.is_overridden()
        assert CL.relative_census_path("indianapolis-in") == \
            "launch_packages/pettripfinder/identity_census_proposed/indianapolis-in.json"

    def test_an_absolute_override_is_taken_as_is(self, monkeypatch, tmp_path):
        monkeypatch.setenv(CL.ENV, str(tmp_path))
        assert CL.identity_census_dir() == tmp_path
        assert CL.identity_census_path("m") == tmp_path / "m.json"

    def test_every_generic_tool_in_the_factory_chain_honours_it(self, monkeypatch, tmp_path,
                                                                restore_modules):
        monkeypatch.setenv(CL.ENV, str(tmp_path))
        for name in FACTORY_CHAIN:
            module = importlib.reload(importlib.import_module(name))
            assert Path(module.CENSUS_DIR) == tmp_path, name

    def test_every_generic_tool_returns_to_the_committed_directory_when_unset(
            self, monkeypatch, restore_modules):
        monkeypatch.delenv(CL.ENV, raising=False)
        for name in FACTORY_CHAIN:
            module = importlib.reload(importlib.import_module(name))
            assert Path(module.CENSUS_DIR) == CL.COMMITTED_CENSUS_DIR, name

    def test_the_committed_indianapolis_census_is_never_the_rebuild_target(self, monkeypatch):
        """The whole point: the pinned file stays pinned."""
        monkeypatch.setenv(CL.ENV, "launch_packages/pettripfinder/identity_census_proposed")
        assert CL.identity_census_path("indianapolis-in") != \
            CL.COMMITTED_CENSUS_DIR / "indianapolis-in.json"
