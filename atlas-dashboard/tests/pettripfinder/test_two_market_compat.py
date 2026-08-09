"""PTF-MULTIMARKET-001 -- Columbus must not care that a second market exists.

Registering a market is a data change: one JSON file under
``launch_packages/pettripfinder/markets/``. Before this work order that data
change broke the Columbus build outright, because six production call sites
resolved their market as "the only one configured" via ``default_market``,
which correctly refuses to guess between two. These tests configure a SECOND
market -- a fixture, never registered in the launch package -- and prove the
whole Columbus build path is indifferent to it.

The guard itself is not weakened, and the last test here proves it: a caller
with no market context still fails closed under ambiguity. The fix was to
stop the production path from ever being such a caller.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from scripts.pettripfinder.market_context import PRODUCTION_MARKET_ID, production_market
from scripts.pettripfinder.markets import (
    MarketContractError,
    default_market,
    load_markets,
    market_by_id,
)
from scripts.pettripfinder.markets import contract as market_contract

REPO_ROOT = Path(__file__).resolve().parents[2]
REAL_MARKETS_DIR = REPO_ROOT / "launch_packages" / "pettripfinder" / "markets"
CLEVELAND_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "cleveland_oh_market_example.json"

SECOND_MARKET_ID = "cleveland-akron-canton-oh"


def _second_market_doc() -> dict:
    """A syntactically real second market, derived from the committed Cleveland
    readiness fixture. It is a TEST fixture: this work order does not register
    Cleveland-Akron-Canton, and nothing here writes to the launch package."""
    doc = json.loads(CLEVELAND_FIXTURE.read_text(encoding="utf-8"))
    old_id = doc["market_id"]
    doc["market_id"] = SECOND_MARKET_ID
    doc["market_slug"] = SECOND_MARKET_ID
    doc["market_name"] = "Cleveland-Akron-Canton"
    for corridor in doc["corridors"]:
        corridor["market_id"] = SECOND_MARKET_ID
        corridor["corridor_id"] = corridor["corridor_id"].replace(old_id, SECOND_MARKET_ID, 1)
    return doc


@pytest.fixture(scope="module")
def two_markets(tmp_path_factory):
    """A markets directory holding columbus-oh AND a second market, installed
    over the loader's directory for the duration of the module."""
    directory = tmp_path_factory.mktemp("two_markets")
    shutil.copy2(REAL_MARKETS_DIR / "columbus-oh.json", directory / "columbus-oh.json")
    (directory / ("%s.json" % SECOND_MARKET_ID)).write_text(
        json.dumps(_second_market_doc(), indent=2), encoding="utf-8")

    import scripts.pettripfinder.hotel_profile as hotel_profile
    import scripts.pettripfinder.market_reports as market_reports

    previous_dir = market_contract.MARKETS_DIR
    previous_reports_dir = market_reports.MARKETS_DIR
    previous_cache = hotel_profile._MARKET_DISPLAY_CONTEXT
    market_contract.MARKETS_DIR = directory
    market_reports.MARKETS_DIR = directory
    hotel_profile._MARKET_DISPLAY_CONTEXT = {}
    try:
        assert len(load_markets()) == 2
        yield directory
    finally:
        market_contract.MARKETS_DIR = previous_dir
        market_reports.MARKETS_DIR = previous_reports_dir
        hotel_profile._MARKET_DISPLAY_CONTEXT = previous_cache


# --------------------------------------------------------------------------- #
# The guard is intact.
# --------------------------------------------------------------------------- #

def test_an_ambiguous_caller_still_fails_closed(two_markets):
    """No context, two markets -> refuse. This is the behaviour that broke the
    build, and it is correct: it must survive the fix."""
    with pytest.raises(MarketContractError, match="requires exactly one configured market"):
        default_market(load_markets())


def test_an_unknown_market_id_fails_closed_rather_than_falling_back(two_markets):
    with pytest.raises(MarketContractError, match="no configured market with market_id"):
        market_by_id(load_markets(), "toledo-oh")


def test_explicit_resolution_is_indifferent_to_the_other_market(two_markets):
    market = production_market()
    assert market.market_id == PRODUCTION_MARKET_ID == "columbus-oh"
    assert len(market.corridors) == 10
    assert market.route_mode == "legacy_unprefixed"


# --------------------------------------------------------------------------- #
# Every production surface, with two markets configured.
# --------------------------------------------------------------------------- #

def test_site_data_corridor_grouping_uses_columbus(two_markets):
    from scripts.pettripfinder.site_data import (
        group_by_corridor, load_published_hotel_policy_facts, read_production_rows,
        verified_public_hotels,
    )
    rows = [r for r in read_production_rows() if r["category"] == "pet-friendly-hotels"]
    verified = verified_public_hotels(rows, load_published_hotel_policy_facts())
    groups = group_by_corridor(verified)
    assert {name: len(members) for name, members in groups.items()} == {
        "Dublin": 13, "Downtown Columbus": 11, "Polaris": 9, "OSU / University Area": 7,
        "Reynoldsburg / East Columbus": 6, "Airport": 6, "Easton": 5,
        "Grove City": 5,
    }


def test_hotel_profile_display_labels_use_columbus(two_markets):
    from scripts.pettripfinder.hotel_profile import _corridor_area, _corridor_label
    assert _corridor_area("Columbus", "Hilton Columbus at Easton") == "Easton corridor"
    assert _corridor_area("Dublin", "Homewood Suites Columbus-Dublin") == "Dublin corridor"
    assert "Easton" in _corridor_label("Columbus", "Hilton Columbus at Easton")


def test_homepage_corridor_navigation_uses_columbus(two_markets):
    from scripts.pettripfinder.approved_home.render import render_home
    from scripts.pettripfinder.site_data import (
        load_published_hotel_policy_facts, read_production_rows, verified_public_hotels,
    )
    facts = load_published_hotel_policy_facts()
    rows = [r for r in read_production_rows() if r["category"] == "pet-friendly-hotels"]
    verified = verified_public_hotels(rows, facts)
    html = render_home(verified, facts, hotel_count=len(verified),
                       park_count=14, restaurant_count=13)
    # Columbus corridor routes, in legacy_unprefixed mode -- no market segment,
    # and nothing belonging to the second market.
    assert '"/pet-friendly-hotels/dublin/"' in html
    assert '"/pet-friendly-hotels/easton/"' in html
    assert "cleveland" not in html.lower()
    assert "/columbus-oh/" not in html


def test_market_reports_are_written_for_columbus(two_markets):
    from scripts.pettripfinder.market_reports import write_reports
    review_path, migration_path = write_reports()
    assert review_path.name == "columbus-oh_assignment_review.json"
    review = json.loads(review_path.read_text(encoding="utf-8"))
    assert review["market_id"] == "columbus-oh"
    # Written under the patched directory, never into the real launch package.
    assert two_markets in review_path.parents


def test_columbus_site_generation_succeeds_with_two_markets(two_markets, tmp_path_factory):
    """The end-to-end proof: the full public build, unchanged, while a second
    market is configured."""
    from scripts.generate_pettripfinder_columbus_site import run
    out = tmp_path_factory.mktemp("two_market_site")
    assert run(str(out)) == 0
    report = json.loads((out / "_build_report.json").read_text(encoding="utf-8"))
    assert report["hotel_count"] == 80
    assert not report["warnings"]
    quality = json.loads((out / "_quality_report.json").read_text(encoding="utf-8"))
    assert quality["failures"] == []
    corridor_dirs = {p.name for p in (out / "pet-friendly-hotels").iterdir()
                     if p.is_dir() and (p / "index.html").exists()}
    for slug in ("dublin", "downtown-columbus", "polaris", "osu-university-area",
                 "reynoldsburg-east-columbus", "airport", "easton"):
        assert slug in corridor_dirs
    # A second market's corridors must not have leaked into the build.
    assert not [name for name in corridor_dirs if "cleveland" in name]


def test_columbus_assembler_succeeds_with_two_markets(two_markets, tmp_path_factory):
    from scripts.pettripfinder.assemble_netlify_bundle import assemble
    out = tmp_path_factory.mktemp("two_market_bundle")
    manifest = assemble("production", str(out))
    assert manifest["all_gates_pass"] is True
    assert manifest["hotel_profile_routes"] == 80
