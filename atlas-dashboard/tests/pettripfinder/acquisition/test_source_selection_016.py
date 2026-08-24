"""PTF-GENERIC-READER-HARDENING-AND-SOURCE-WIRING-016 -- Phase 3.

Source resolution is proved BEFORE the reader is touched, because a reader
improvement measured on the wrong page proves nothing about either.
"""

import ast
import inspect
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import registry as REGISTRY      # noqa: E402
from scripts.pettripfinder.acquisition import router as ROUTER          # noqa: E402
from scripts.pettripfinder.acquisition import source_discovery as SD    # noqa: E402
from scripts.pettripfinder.acquisition import source_selection as SS    # noqa: E402
from scripts.pettripfinder.brightdata import corpus as CORPUS           # noqa: E402
from scripts.pettripfinder import milwaukee_resume_007 as RESUME        # noqa: E402

MARKET = "milwaukee-wi"
OVERLAY = SD.overlay_path(REPO, MARKET)
#: Milwaukee's committed source of ``official_url`` -- the acquisition queue
#: the runner itself reads. Named here rather than remembered, so the freeze
#: assertion below is against the file acquisition actually consults.
CENSUS = (REPO / "launch_packages" / "pettripfinder" / "markets" / "reports"
          / "milwaukee-wi_policy_acquisition_queue_001.json")


def _overlay():
    return json.loads(OVERLAY.read_text(encoding="utf-8-sig"))


def _found_row():
    return next(r for r in _overlay()["records"]
                if r["status"] == SD.POLICY_URL_FOUND)


def _unresolved_row():
    return next(r for r in _overlay()["records"]
                if r["status"] != SD.POLICY_URL_FOUND)


def _record(identity_key, url):
    return CORPUS.BenchmarkRecord(
        identity_key=identity_key, name="The Pfister Hotel", market_id=MARKET,
        brand="INDEPENDENT", bucket=CORPUS.bucket_of("INDEPENDENT"),
        source_url=url, pets_allowed=None, facts={}, quotes=(),
        withheld_fields={}, service_animal_statement="",
        categories=frozenset(), origin="census")


# --------------------------------------------------------------------------- #
# 1. an overlay-backed property resolves to the discovered policy URL
# --------------------------------------------------------------------------- #

def test_an_overlay_backed_property_resolves_to_the_discovered_policy_url():
    row = _found_row()
    got = SS.select(row["identity_key"], row["original_source_url"],
                    market_id=MARKET)
    assert got.selected_url == row["discovered_url"]
    assert got.source == SS.FROM_DISCOVERY
    assert got.changed is True


def test_every_found_row_in_the_overlay_is_actually_selected():
    """Not one sample: every row the overlay carries, end to end."""
    for row in _overlay()["records"]:
        got = SS.select(row["identity_key"], row["original_source_url"],
                        market_id=MARKET)
        if row["status"] == SD.POLICY_URL_FOUND:
            assert got.selected_url == row["discovered_url"], row["identity_key"]
        else:
            assert got.selected_url == row["original_source_url"], row["identity_key"]


# --------------------------------------------------------------------------- #
# 2. an unresolved property falls back to the census official_url
# --------------------------------------------------------------------------- #

def test_an_unresolved_property_falls_back_to_the_census_url():
    row = _unresolved_row()
    got = SS.select(row["identity_key"], row["original_source_url"],
                    market_id=MARKET)
    assert got.selected_url == row["original_source_url"]
    assert got.source == SS.FROM_CENSUS
    assert got.changed is False
    # present in the overlay, but carrying no usable URL. The distinction has
    # to survive, or "we never looked" and "we looked and found nothing"
    # collapse into one report line.
    assert got.overlay_present is True


def test_a_property_with_no_overlay_row_falls_back_to_the_census_url():
    got = SS.select("a property no overlay mentions",
                    "https://example.test/", market_id=MARKET)
    assert got.selected_url == "https://example.test/"
    assert got.source == SS.FROM_CENSUS
    assert got.overlay_present is False


def test_a_market_with_no_overlay_file_behaves_as_before_the_seam_existed():
    got = SS.select("anything", "https://example.test/page",
                    market_id="a-market-with-no-overlay")
    assert got.selected_url == "https://example.test/page"
    assert got.source == SS.FROM_CENSUS


# --------------------------------------------------------------------------- #
# 3. deleting an overlay row restores census behaviour
# --------------------------------------------------------------------------- #

def test_deleting_an_overlay_row_restores_census_behaviour(tmp_path):
    row = _found_row()
    doc = _overlay()
    doc["records"] = [r for r in doc["records"]
                      if r["identity_key"] != row["identity_key"]]
    fake = (tmp_path / "launch_packages" / "pettripfinder" / "markets"
            / "discovered_policy_urls")
    fake.mkdir(parents=True)
    (fake / ("%s.json" % MARKET)).write_text(json.dumps(doc), encoding="utf-8")

    got = SS.select(row["identity_key"], row["original_source_url"],
                    market_id=MARKET, repo=tmp_path)
    assert got.selected_url == row["original_source_url"]
    assert got.source == SS.FROM_CENSUS
    # and the committed overlay is unaffected by having been read
    assert SS.select(row["identity_key"], row["original_source_url"],
                     market_id=MARKET).selected_url == row["discovered_url"]


# --------------------------------------------------------------------------- #
# 4. census data is never mutated
# --------------------------------------------------------------------------- #

def test_selection_never_mutates_the_census_url_authority():
    before = CENSUS.read_bytes()
    for row in _overlay()["records"]:
        SS.select(row["identity_key"], row["original_source_url"],
                  market_id=MARKET)
    assert CENSUS.read_bytes() == before


def test_the_census_url_for_every_overlay_row_still_matches_the_census():
    """The overlay copy of the census URL is a copy, and a copy can drift."""
    census = json.loads(CENSUS.read_text(encoding="utf-8-sig"))
    by_key = {r["identity_key"]: r for r in census["items"]}
    for row in _overlay()["records"]:
        entry = by_key[row["identity_key"]]
        assert entry["official_url"] == row["original_source_url"], \
            row["identity_key"]


def test_resolving_a_target_does_not_edit_the_record():
    record = _record("the pfister hotel", "https://www.thepfisterhotel.com/")
    target, selection = SS.resolved_target(record, market_id=MARKET)
    assert record.source_url == "https://www.thepfisterhotel.com/"
    assert target.requested_url == selection.selected_url
    assert target.requested_url != record.source_url
    # identity rides across unchanged: a different PAGE, never a different HOTEL
    assert target.identity_key == record.identity_key
    assert target.hotel == record.name


# --------------------------------------------------------------------------- #
# 5. the provider route is unchanged by source resolution
# --------------------------------------------------------------------------- #

def test_the_route_url_is_the_census_url_and_not_the_selected_one():
    selection = SS.select("the pfister hotel",
                          "https://www.thepfisterhotel.com/", market_id=MARKET)
    assert selection.changed is True
    assert selection.route_url == selection.census_url
    assert selection.route_url != selection.selected_url


def test_source_resolution_does_not_change_the_resolved_lane():
    for row in _overlay()["records"]:
        selection = SS.select(row["identity_key"], row["original_source_url"],
                              market_id=MARKET)
        census_route = REGISTRY.resolve(brand="INDEPENDENT",
                                        url=selection.census_url,
                                        identity_key=row["identity_key"])
        wired_route = REGISTRY.resolve(brand="INDEPENDENT",
                                       url=selection.route_url,
                                       identity_key=row["identity_key"])
        assert wired_route.provider == census_route.provider
        assert wired_route.reader == census_route.reader


def test_the_router_defaults_route_url_to_the_target_it_is_given():
    """Callers written before this seam existed must be unaffected."""
    signature = inspect.signature(ROUTER.route_property)
    assert signature.parameters["route_url"].default == ""


def test_the_runner_passes_the_census_url_as_the_route_url():
    """The wiring itself, not only the helper it calls."""
    source = Path(RESUME.__file__).read_text(encoding="utf-8")
    calls = [n for n in ast.walk(ast.parse(source))
             if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Attribute)
             and n.func.attr == "route_property"]
    assert calls, "the runner no longer calls route_property"
    for call in calls:
        keywords = {k.arg for k in call.keywords}
        assert "route_url" in keywords, \
            ("route_property is called without route_url; the lane would be "
             "resolved from the discovered page")


# --------------------------------------------------------------------------- #
# 6. provenance records both the original and the selected URL
# --------------------------------------------------------------------------- #

def test_provenance_records_both_urls_and_the_reason():
    row = _found_row()
    got = SS.select(row["identity_key"], row["original_source_url"],
                    market_id=MARKET).to_dict()
    assert got["census_official_url"] == row["original_source_url"]
    assert got["selected_source_url"] == row["discovered_url"]
    assert got["source"] == SS.FROM_DISCOVERY
    assert got["overlay_changed_source"] is True
    assert got["provenance"]["contract"] == SD.CONTRACT


def test_the_runner_records_which_source_url_it_actually_used():
    source = Path(RESUME.__file__).read_text(encoding="utf-8")
    keys = {n.value for n in ast.walk(ast.parse(source))
            if isinstance(n, ast.Constant) and isinstance(n.value, str)}
    assert "source_selection" in keys, \
        "the per-property report row no longer carries the source selection"


# --------------------------------------------------------------------------- #
# 7. cache keys cannot collide across properties sharing a path
# --------------------------------------------------------------------------- #

def test_two_properties_publishing_the_same_path_get_different_cache_keys():
    """The exact class of bug found in 015: a cache keyed on the URL PATH.

    A path is not a property. Keying on one served a document belonging to a
    different hotel, and a longer path slug would not have helped.
    """
    a = SS.cache_key("the iron horse hotel",
                     "https://www.theironhorsehotel.com/faq")
    b = SS.cache_key("saint kate - the arts hotel",
                     "https://www.saintkatearts.com/faq")
    assert a != b


def test_every_pair_of_milwaukee_independents_gets_a_distinct_cache_key():
    """Not two hand-picked hotels -- every row, on a path they all share."""
    keys = {}
    for row in _overlay()["records"]:
        key = SS.cache_key(row["identity_key"], "https://example.test/faq")
        assert key not in keys, ("%s collides with %s"
                                 % (row["identity_key"], keys.get(key)))
        keys[key] = row["identity_key"]
    assert len(keys) == len(_overlay()["records"])


def test_two_pages_of_one_property_get_different_cache_keys():
    a = SS.cache_key("the pfister hotel",
                     "https://www.thepfisterhotel.com/faq")
    b = SS.cache_key("the pfister hotel",
                     "https://www.thepfisterhotel.com/accommodations/pets/")
    assert a != b


def test_the_cache_key_is_stable_for_the_same_property_and_url():
    args = ("the pfister hotel",
            "https://www.thepfisterhotel.com/accommodations/pets/")
    assert SS.cache_key(*args) == SS.cache_key(*args)


def test_the_cache_key_names_the_property_so_a_collision_is_visible():
    key = SS.cache_key("the pfister hotel",
                       "https://www.thepfisterhotel.com/faq")
    assert key.startswith("the-pfister-hotel--")
