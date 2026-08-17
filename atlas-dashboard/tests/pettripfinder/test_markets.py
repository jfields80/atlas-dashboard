"""PTF-CORRIDORS-002 -- national market/corridor layer tests (Part G).

Covers the national scalability gates with SYNTHETIC markets (no real
Cleveland hotel data) plus the committed Cleveland readiness fixture
(Part H). Gate 15 -- "existing Columbus content still generates
successfully" -- is carried by the existing end-to-end suites
(test_generate_columbus_site.py, test_prod004_verified_only.py), which
build the real site through this same layer.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from scripts.pettripfinder.markets import (
    MARKETS_DIR,
    MarketAssignmentError,
    MarketContractError,
    MarketRouteError,
    assign_hotels,
    build_route_table,
    corridor_display_label,
    corridor_href_for,
    corridor_navigation,
    corridor_route,
    default_market,
    hotel_route,
    load_markets,
    market_by_id,
    market_route,
    parse_market,
    sitemap_corridor_routes,
)
from scripts.pettripfinder.markets.routes import market_route_table
from scripts.pettripfinder.site_pages import build_corridor_page

FIXTURES = Path(__file__).resolve().parent / "fixtures"
CLEVELAND_FIXTURE = FIXTURES / "cleveland_oh_market_example.json"


# --------------------------------------------------------------------------- #
# Synthetic config builders (never a real market).
# --------------------------------------------------------------------------- #

def corridor_doc(market_id, slug, name=None, *, cities=(), zips=(), explicit=(),
                 excluded=(), minimum=2, allow_multi=False, order=1, nav=True,
                 sitemap=True):
    return {
        "corridor_id": "%s__%s" % (market_id, slug),
        "market_id": market_id,
        "name": name or slug.replace("-", " ").title(),
        "slug": slug,
        "title": "Hotels in %s" % (name or slug),
        "meta_description": "Hotels in %s." % (name or slug),
        "description": "",
        "included_cities": list(cities),
        "included_postal_codes": list(zips),
        "explicit_hotel_ids": list(explicit),
        "excluded_hotel_ids": list(excluded),
        "minimum_hotel_count": minimum,
        "show_in_navigation": nav,
        "show_in_sitemap": sitemap,
        "allow_multi_corridor": allow_multi,
        "display_order": order,
    }


def market_doc(market_id="riverton-wa", *, slug=None, corridors=(), route_mode=None,
               minimum_published=1):
    doc = {
        "schema": "ptf-market/1.1",
        "market_id": market_id,
        "market_name": market_id.split("-")[0].title(),
        "market_slug": slug or market_id,
        "state_name": "Washington",
        "state_code": "WA",
        # PTF-GEOGRAPHY-NORMALIZATION-001: 1.1 requires the market to state
        # which states it spans and to choose its route mode explicitly.
        "primary_state_code": "WA",
        "states": ["WA"],
        "primary_city": market_id.split("-")[0].title(),
        "country_code": "US",
        "title": "Pet-Friendly Hotels | PetTripFinder",
        "meta_description": "Verified pet-friendly hotels.",
        "introductory_copy": "",
        "navigation_label": market_id.split("-")[0].title(),
        "show_in_navigation": True,
        "show_in_sitemap": True,
        "minimum_published_hotels": minimum_published,
        "corridors": list(corridors),
    }
    # 1.1 requires an explicit route mode: Cincinnati's config omitted it and
    # silently inherited one nobody chose. The fixture states the default so
    # every other test still exercises the failure it was written for.
    doc["route_mode"] = route_mode if route_mode is not None else "market_prefixed"
    return doc


def hotel(name, city="Riverton", postal_code=""):
    return {"name": name, "city": city, "postal_code": postal_code,
            "address": "1 Test St", "category": "pet-friendly-hotels"}


# --------------------------------------------------------------------------- #
# Contract validation (fail closed).
# --------------------------------------------------------------------------- #

def test_wrong_schema_version_fails():
    doc = market_doc()
    doc["schema"] = "ptf-market/9.9"
    with pytest.raises(MarketContractError):
        parse_market(doc)


def test_missing_required_field_fails():
    doc = market_doc()
    del doc["state_code"]
    with pytest.raises(MarketContractError):
        parse_market(doc)


def test_duplicate_market_slug_fails_closed(tmp_path):
    # Gate 5: market slugs are globally unique.
    a = market_doc("riverton-wa", slug="riverton")
    b = market_doc("riverton-or", slug="riverton")
    # state_code is the alias of primary_state_code at 1.1, so both move.
    b["state_name"], b["state_code"] = "Oregon", "OR"
    b["primary_state_code"], b["states"] = "OR", ["OR"]
    (tmp_path / "a.json").write_text(json.dumps(a), encoding="utf-8")
    (tmp_path / "b.json").write_text(json.dumps(b), encoding="utf-8")
    with pytest.raises(MarketContractError, match="duplicate market_slug"):
        load_markets(tmp_path)


def test_duplicate_corridor_slug_inside_market_fails():
    # Gate 6.
    doc = market_doc(corridors=[
        corridor_doc("riverton-wa", "downtown", order=1),
        corridor_doc("riverton-wa", "downtown", order=2),
    ])
    doc["corridors"][1]["corridor_id"] = "riverton-wa__downtown-2"
    with pytest.raises(MarketContractError, match="duplicate corridor slug"):
        parse_market(doc)


def test_non_normalized_explicit_hotel_id_fails():
    doc = market_doc(corridors=[
        corridor_doc("riverton-wa", "downtown", explicit=["Hôtel Fancy & Co"])])
    with pytest.raises(MarketContractError, match="normalized-name"):
        parse_market(doc)


def test_hotel_id_in_both_explicit_and_excluded_fails():
    doc = market_doc(corridors=[
        corridor_doc("riverton-wa", "downtown",
                     explicit=["some hotel"], excluded=["some hotel"])])
    with pytest.raises(MarketContractError, match="both explicit and excluded"):
        parse_market(doc)


def test_us_postal_codes_must_be_five_digits():
    doc = market_doc(corridors=[
        corridor_doc("riverton-wa", "downtown", zips=["9810"])])
    with pytest.raises(MarketContractError, match="five digits"):
        parse_market(doc)


def test_minimum_hotel_count_must_be_positive():
    doc = market_doc(corridors=[corridor_doc("riverton-wa", "downtown", minimum=0)])
    with pytest.raises(MarketContractError, match="minimum_hotel_count"):
        parse_market(doc)


def test_missing_markets_directory_fails_closed(tmp_path):
    with pytest.raises(MarketContractError, match="does not exist"):
        load_markets(tmp_path / "nope")


def test_default_market_requires_exactly_one():
    m1 = parse_market(market_doc("riverton-wa"))
    m2 = parse_market(market_doc("bayview-wa"))
    with pytest.raises(MarketContractError):
        default_market((m1, m2))
    assert default_market((m1,)) is m1


# --------------------------------------------------------------------------- #
# Deterministic assignment (Part C rules).
# --------------------------------------------------------------------------- #

def test_explicit_assignment_overrides_city_and_zip():
    # Gate 9: the hotel city-matches "suburb" AND zip-matches "eastside",
    # but its explicit assignment to "downtown" wins.
    market = parse_market(market_doc(corridors=[
        corridor_doc("riverton-wa", "downtown", explicit=["keyed hotel"], order=1),
        corridor_doc("riverton-wa", "suburb", cities=["Suburbia"], order=2),
        corridor_doc("riverton-wa", "eastside", zips=["98101"], order=3),
    ]))
    a = assign_hotels(market, [hotel("Keyed Hotel", city="Suburbia", postal_code="98101")])
    assert a.corridor_of["keyed hotel"] == ("riverton-wa__downtown",)
    assert a.tier_of["keyed hotel"] == "explicit"


def test_explicit_exclusion_overrides_every_inclusion_method():
    # Gate 8: excluded from "suburb" despite explicit+city+zip matches there;
    # exclusion is per-corridor, so the zip corridor still receives it.
    market = parse_market(market_doc(corridors=[
        corridor_doc("riverton-wa", "suburb", cities=["Suburbia"],
                     explicit=[], excluded=["banned hotel"], order=1),
        corridor_doc("riverton-wa", "eastside", zips=["98101"], order=2),
    ]))
    a = assign_hotels(market, [hotel("Banned Hotel", city="Suburbia", postal_code="98101")])
    assert a.corridor_of["banned hotel"] == ("riverton-wa__eastside",)
    # ...and excluding it everywhere leaves it unassigned but REPORTED.
    market2 = parse_market(market_doc(corridors=[
        corridor_doc("riverton-wa", "suburb", cities=["Suburbia"],
                     excluded=["banned hotel"], order=1),
        corridor_doc("riverton-wa", "eastside", zips=["98101"],
                     excluded=["banned hotel"], order=2),
    ]))
    a2 = assign_hotels(market2, [hotel("Banned Hotel", city="Suburbia", postal_code="98101")])
    assert [r["name"] for r in a2.unassigned] == ["Banned Hotel"]


def test_zip_match_beats_city_match():
    """PTF-GEOGRAPHY-NORMALIZATION-001 reversed these two tiers.

    A ZIP is a smaller unit than a mailing city, and mailing cities routinely
    span corridors while ZIPs rarely do. Four Cincinnati properties carrying
    the mailing city "Cincinnati" sit fifteen miles east in Eastgate; under the
    old order they resolved to Downtown Cincinnati.
    """
    market = parse_market(market_doc(corridors=[
        corridor_doc("riverton-wa", "suburb", cities=["Suburbia"], order=1),
        corridor_doc("riverton-wa", "eastside", zips=["98101"], order=2),
    ]))
    a = assign_hotels(market, [hotel("H", city="Suburbia", postal_code="98101")])
    assert a.corridor_of["h"] == ("riverton-wa__eastside",)
    assert a.tier_of["h"] == "postal_code"
    assert a.basis_of["h"] == ("postal_code", "98101")


def test_city_is_still_consulted_when_the_zip_resolves_nothing():
    market = parse_market(market_doc(corridors=[
        corridor_doc("riverton-wa", "suburb", cities=["Suburbia"], order=1),
        corridor_doc("riverton-wa", "eastside", zips=["98101"], order=2),
    ]))
    a = assign_hotels(market, [hotel("H", city="Suburbia", postal_code="99999")])
    assert a.corridor_of["h"] == ("riverton-wa__suburb",)
    assert a.tier_of["h"] == "city_state"


def test_a_duplicate_zip_is_now_rejected_by_the_CONFIG_not_by_a_hotel():
    """PTF-GEOGRAPHY-NORMALIZATION-001 moved this failure earlier.

    Two corridors claiming one ZIP with neither authorising sharing is knowable
    from the configuration alone, so it is rejected from the configuration
    alone -- once, loudly. Cincinnati carried exactly this defect for 45044 and
    nothing noticed until a hotel with that ZIP happened to be assigned, at
    which point the failure looked like a problem with the hotel.
    """
    with pytest.raises(MarketContractError, match="98101"):
        parse_market(market_doc(corridors=[
            corridor_doc("riverton-wa", "a", zips=["98101"], order=1),
            corridor_doc("riverton-wa", "b", zips=["98101"], order=2),
        ]))


def test_ambiguous_city_match_still_fails_closed_at_assignment():
    """Cities may legitimately repeat across corridors, so ambiguity there is
    still resolved per hotel rather than rejected outright."""
    market = parse_market(market_doc(corridors=[
        corridor_doc("riverton-wa", "a", cities=["Shared"], order=1),
        corridor_doc("riverton-wa", "b", cities=["Shared"], order=2),
    ]))
    with pytest.raises(MarketAssignmentError, match="ambiguous"):
        assign_hotels(market, [hotel("H", city="Shared")])
    a = assign_hotels(market, [hotel("H", city="Shared")], fail_closed=False)
    assert a.conflicts and a.conflicts[0]["hotel"] == "h"
    assert [r["name"] for r in a.unassigned] == ["H"]


def test_multi_corridor_allowed_only_when_every_match_authorizes():
    market = parse_market(market_doc(corridors=[
        corridor_doc("riverton-wa", "a", zips=["98101"], allow_multi=True, order=1),
        corridor_doc("riverton-wa", "b", zips=["98101"], allow_multi=True, order=2),
    ]))
    a = assign_hotels(market, [hotel("H", postal_code="98101")] +
                      [hotel("F%d" % i, postal_code="98101") for i in range(1)])
    assert a.corridor_of["h"] == ("riverton-wa__a", "riverton-wa__b")


def test_unassigned_hotels_reported_never_dropped():
    # Gate 11.
    market = parse_market(market_doc(corridors=[
        corridor_doc("riverton-wa", "downtown", zips=["98101"], order=1)]))
    a = assign_hotels(market, [hotel("Lonely Hotel", postal_code="99999")])
    assert [r["name"] for r in a.unassigned] == ["Lonely Hotel"]
    assert not a.conflicts


def test_below_minimum_and_empty_corridors_do_not_publish():
    # Gate 12.
    market = parse_market(market_doc(corridors=[
        corridor_doc("riverton-wa", "downtown", zips=["98101"], minimum=3, order=1),
        corridor_doc("riverton-wa", "ghost", zips=["98999"], minimum=1, order=2),
    ]))
    a = assign_hotels(market, [hotel("H1", postal_code="98101"),
                               hotel("H2", postal_code="98101")])
    assert a.published == ()
    reasons = {s["corridor_id"]: s["reason"] for s in a.suppressed}
    assert reasons["riverton-wa__downtown"] == "below_minimum"
    assert reasons["riverton-wa__ghost"] == "empty"


def test_duplicate_hotel_key_fails_closed():
    market = parse_market(market_doc(corridors=[
        corridor_doc("riverton-wa", "downtown", zips=["98101"], order=1)]))
    with pytest.raises(MarketAssignmentError, match="duplicate hotel key"):
        assign_hotels(market, [hotel("Same Hotel"), hotel("Same  Hotel!")])


# --------------------------------------------------------------------------- #
# Routes (Part A).
# --------------------------------------------------------------------------- #

def test_market_prefixed_routes_are_default():
    market = parse_market(market_doc(corridors=[
        corridor_doc("riverton-wa", "downtown", zips=["98101"], order=1)]))
    corridor = market.corridors[0]
    assert market_route(market) == "/pet-friendly-hotels/riverton-wa/"
    assert corridor_route(market, corridor) == "/pet-friendly-hotels/riverton-wa/downtown/"
    assert hotel_route(market, "Grand Hotel") == "/pet-friendly-hotels/riverton-wa/grand-hotel/"


def test_legacy_unprefixed_route_mode():
    market = parse_market(market_doc(
        route_mode="legacy_unprefixed",
        corridors=[corridor_doc("riverton-wa", "downtown", zips=["98101"], order=1)]))
    assert market_route(market) == "/pet-friendly-hotels/"
    assert corridor_route(market, market.corridors[0]) == "/pet-friendly-hotels/downtown/"


def test_two_markets_may_both_have_a_downtown_corridor():
    # Gates 2 + 3: same corridor slug in two markets; the prefixed routes
    # stay globally unique.
    m1 = parse_market(market_doc("riverton-wa", corridors=[
        corridor_doc("riverton-wa", "downtown", zips=["98101"], minimum=1, order=1)]))
    m2 = parse_market(market_doc("bayview-wa", corridors=[
        corridor_doc("bayview-wa", "downtown", zips=["98201"], minimum=1, order=1)]))
    a1 = assign_hotels(m1, [hotel("H1", postal_code="98101")])
    a2 = assign_hotels(m2, [hotel("H2", city="Bayview", postal_code="98201")])
    t1 = market_route_table(m1, a1, ["H1"])
    t2 = market_route_table(m2, a2, ["H2"])
    combined = build_route_table(list(t1.items()) + list(t2.items()))
    assert "/pet-friendly-hotels/riverton-wa/downtown/" in combined
    assert "/pet-friendly-hotels/bayview-wa/downtown/" in combined
    assert len(combined) == len(t1) + len(t2)


def test_duplicate_final_route_fails_closed():
    # Gates 4/7: a legacy-mode corridor slug colliding with a hotel slug is
    # exactly the shared-namespace hazard the table must reject.
    market = parse_market(market_doc(
        route_mode="legacy_unprefixed",
        corridors=[corridor_doc("riverton-wa", "downtown", zips=["98101"],
                                minimum=1, order=1)]))
    a = assign_hotels(market, [hotel("H%d" % i, postal_code="98101") for i in range(1)])
    with pytest.raises(MarketRouteError, match="duplicate route"):
        market_route_table(market, a, ["H0", "Downtown"])


# --------------------------------------------------------------------------- #
# Navigation / sitemap (Parts C + E).
# --------------------------------------------------------------------------- #

def _nav_market():
    return parse_market(market_doc(corridors=[
        corridor_doc("riverton-wa", "beta", zips=["98102"], minimum=1, order=2),
        corridor_doc("riverton-wa", "alpha", zips=["98101"], minimum=1, order=1),
        corridor_doc("riverton-wa", "hidden", zips=["98103"], minimum=1, order=3,
                     nav=False),
        corridor_doc("riverton-wa", "nomap", zips=["98104"], minimum=1, order=4,
                     sitemap=False),
        corridor_doc("riverton-wa", "starved", zips=["98105"], minimum=9, order=5),
    ]))


def test_navigation_contains_only_published_nav_visible_in_display_order():
    # Gate 13.
    market = _nav_market()
    a = assign_hotels(market, [
        hotel("A", postal_code="98101"), hotel("B", postal_code="98102"),
        hotel("C", postal_code="98103"), hotel("D", postal_code="98104"),
        hotel("E", postal_code="98105")])
    nav = corridor_navigation(market, a)
    assert [e.corridor_id for e in nav] == [
        "riverton-wa__alpha", "riverton-wa__beta", "riverton-wa__nomap"]
    assert nav[0].route == "/pet-friendly-hotels/riverton-wa/alpha/"


def test_sitemap_routes_only_published_sitemap_visible():
    # Gate 14.
    market = _nav_market()
    a = assign_hotels(market, [
        hotel("A", postal_code="98101"), hotel("C", postal_code="98103"),
        hotel("D", postal_code="98104"), hotel("E", postal_code="98105")])
    routes = sitemap_corridor_routes(market, a)
    assert routes == ("/pet-friendly-hotels/riverton-wa/alpha/",
                      "/pet-friendly-hotels/riverton-wa/hidden/")


def test_market_below_published_minimum_has_no_navigation():
    market = parse_market(market_doc(minimum_published=10, corridors=[
        corridor_doc("riverton-wa", "alpha", zips=["98101"], minimum=1, order=1)]))
    a = assign_hotels(market, [hotel("A", postal_code="98101")])
    assert corridor_navigation(market, a) == ()


def test_suppressed_corridor_produces_no_breadcrumb_href():
    market = parse_market(market_doc(corridors=[
        corridor_doc("riverton-wa", "downtown", zips=["98101"], minimum=5, order=1)]))
    a = assign_hotels(market, [hotel("H", postal_code="98101")])
    assert a.corridor_of["h"]                       # assigned...
    assert corridor_href_for(market, a, "H") is None  # ...but never linked


def test_display_label_uses_market_anchor_not_a_constant():
    market = parse_market(market_doc(corridors=[
        corridor_doc("riverton-wa", "downtown", "Downtown", zips=["98101"],
                     minimum=1, order=1)]))
    a = assign_hotels(market, [hotel("H", postal_code="98101")])
    assert corridor_display_label(market, a, "H", "Riverton") == \
        "Downtown corridor · Riverton, WA"
    assert corridor_display_label(market, a, "Unknown", "Elsewhere") == \
        "Elsewhere corridor · Riverton, WA"


# --------------------------------------------------------------------------- #
# No market leaks into another (Gate 4).
# --------------------------------------------------------------------------- #

def test_no_columbus_string_leaks_into_another_markets_pages():
    market = parse_market(market_doc(corridors=[
        corridor_doc("riverton-wa", "downtown", "Downtown", zips=["98101"],
                     minimum=1, order=1)]))
    page = build_corridor_page(market.corridors[0], market, [
        {"name": "Test Hotel", "route": "/pet-friendly-hotels/riverton-wa/test-hotel/",
         "city": "Riverton"}])
    assert "Columbus" not in page
    assert "Ohio" not in page
    assert ", WA" in page


# --------------------------------------------------------------------------- #
# Config-only second market + Cleveland readiness (Gates 1/2; Part H).
# --------------------------------------------------------------------------- #

def test_second_market_added_with_configuration_only(tmp_path):
    # Gate 1: the production Columbus config plus the Cleveland example
    # fixture load side by side through the SAME loader -- no code changes,
    # no special cases, globally unique ids enforced.
    shutil.copyfile(MARKETS_DIR / "columbus-oh.json", tmp_path / "columbus-oh.json")
    shutil.copyfile(CLEVELAND_FIXTURE, tmp_path / "cleveland-oh.json")
    markets = load_markets(tmp_path)
    assert [m.market_id for m in markets] == ["cleveland-oh", "columbus-oh"]
    cle = markets[0]
    assert cle.route_mode == "market_prefixed"      # new markets get the target routes
    assert markets[1].route_mode == "legacy_unprefixed"  # Columbus keeps live URLs


def test_cleveland_fixture_bootstraps_without_generator_changes():
    # Part H: synthetic hotels only -- no real Cleveland data, nothing
    # approved for production.
    cle = parse_market(json.loads(CLEVELAND_FIXTURE.read_text(encoding="utf-8")),
                       source="cleveland_oh_market_example.json")
    conceptual = {"Downtown Cleveland", "Airport", "Independence", "Beachwood",
                  "Westlake", "University Circle"}
    assert {c.name for c in cle.corridors} == conceptual
    rows = ([hotel("Downtown Test %d" % i, city="Cleveland", postal_code="44113")
             for i in range(5)]
            + [hotel("Independence Test %d" % i, city="Independence")
               for i in range(5)]
            + [hotel("Stray Test", city="Cleveland", postal_code="44199")])
    a = assign_hotels(cle, rows)
    published_names = {cle.corridor_by_id(cid).name for cid in a.published}
    assert published_names == {"Downtown Cleveland", "Independence"}
    assert [r["name"] for r in a.unassigned] == ["Stray Test"]
    assert corridor_route(cle, cle.corridor_by_id("cleveland-oh__downtown-cleveland")) \
        == "/pet-friendly-hotels/cleveland-oh/downtown-cleveland/"
    page = build_corridor_page(
        cle.corridor_by_id("cleveland-oh__downtown-cleveland"), cle,
        [{"name": r["name"], "route": "/x/", "city": r["city"]}
         for r in a.members_of("cleveland-oh__downtown-cleveland")])
    assert "Columbus" not in page
    assert "Downtown Cleveland" in page


def test_production_markets_dir_loads_and_is_single_market_columbus():
    # PTF-CLEVELAND-AKRON-CANTON-008: the committed set is no longer a single
    # market. Columbus is resolved BY NAME, exactly as the build resolves it,
    # so registering market N+1 cannot change what this test observes. The
    # previous revision asserted len(markets) == 1 as a record of the state at
    # the time, noting it was not something the build depended on -- and it
    # is that record, not the build, that this registration invalidated.
    # PTF-DAYTON-MARKET-FACTORY-001: dayton-oh added as worker-proposed market
    # (worker/ptf-dayton-market-001 branch). Columbus resolution by name is
    # unchanged -- adding dayton-oh cannot affect what PRODUCTION_MARKET_ID
    # resolves to.
    markets = load_markets()
    # PTF-GEOGRAPHY-NORMALIZATION-001: cincinnati-oh registered with the
    # tri-state contract. Columbus still resolves BY NAME, which is exactly
    # why this test resolves by name rather than by count.
    # PTF-DETROIT-ANN-ARBOR-MARKET-FACTORY-001: detroit-ann-arbor-mi
    # registered as a Phase 1 census-only market (no policy authority yet).
    # Columbus resolution by name is unchanged.
    assert sorted(m.market_id for m in markets) == \
        ["cincinnati-oh", "cleveland-akron-canton-oh", "columbus-oh",
         "dayton-oh", "detroit-ann-arbor-mi", "indianapolis-in", "louisville-ky",
         "pittsburgh-pa"]
    market = market_by_id(markets, "columbus-oh")
    assert market.market_id == "columbus-oh"
    assert market.route_mode == "legacy_unprefixed"
    assert len(market.corridors) == 10
    # The 43219 split is explicit on BOTH sides -- neither corridor may
    # carry the ambiguous ZIP.
    airport = market.corridor_by_id("columbus-oh__airport")
    easton = market.corridor_by_id("columbus-oh__easton")
    assert not airport.included_postal_codes and not easton.included_postal_codes
    assert len(airport.explicit_hotel_ids) == 6
    assert len(easton.explicit_hotel_ids) == 5
