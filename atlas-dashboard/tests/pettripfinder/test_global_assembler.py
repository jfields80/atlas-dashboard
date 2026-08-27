"""PTF-MULTI-MARKET-ASSEMBLER-001 -- one bundle, many markets.

Phase E replaced four whole-site builds that each believed they owned the
domain with market FRAGMENTS plus one global assembler. These tests defend the
two properties that makes safe:

  * a fragment may only claim routes its market owns, and
  * adding market N may not move a byte owned by markets 1..N-1.

Most of what follows is derivable without generating a site, and is asserted
directly against the committed authority -- routes, ownership, eligibility,
breadcrumbs, /go/ scoping. The handful of proofs that genuinely require
building the whole bundle (byte-level idempotence, Columbus preservation
against a pre-migration render) take tens of minutes, so they are opt-in via
``PTF_ASSEMBLER_FULL_BUILD=1`` and SKIP loudly rather than passing vacuously.
"""

from __future__ import annotations

import os
import pathlib
import re
import shutil
import tempfile

import pytest

from scripts.pettripfinder import assemble_production_site as gasm
from scripts.pettripfinder.assemble_production_site import (
    GLOBAL_FILES, GLOBAL_ROUTES, AssemblyError, anchor_market, build_global_llms,
    build_global_sitemap, canonical_violations, classify_fragment,
    market_eligibility, owned_routes, published_hotels, select_markets,
)
from scripts.pettripfinder.commercial_actions import (
    ACTION_CALL, go_market_prefix, go_route, set_go_market_prefix,
)
from scripts.pettripfinder.markets import (
    hotel_route, load_markets, market_by_id, market_route,
)
from scripts.pettripfinder.markets.contract import ROUTE_MODE_LEGACY_UNPREFIXED

COLUMBUS = "columbus-oh"
CLEVELAND = "cleveland-akron-canton-oh"
DAYTON = "dayton-oh"
CINCINNATI = "cincinnati-oh"
INDIANAPOLIS = "indianapolis-in"

FULL_BUILD = os.environ.get("PTF_ASSEMBLER_FULL_BUILD") == "1"
needs_build = pytest.mark.skipif(
    not FULL_BUILD,
    reason="generates every market's site; set PTF_ASSEMBLER_FULL_BUILD=1 to run")


@pytest.fixture()
def markets():
    return load_markets()


@pytest.fixture()
def short_out(tmp_path):
    """A build destination short enough for Windows.

    ``tmp_path`` is roughly 70 characters before the bundle even starts, and a
    Cleveland hotel slug ("residence-inn-by-marriott-cleveland-avon-at-the-
    emerald-event-center") spends 68 more, so materializing the bundle under it
    fails with WinError 206. This is a real constraint on the platform the
    build runs on, not a test artifact -- the same limit is why the operator
    runbook builds into a short path. Override the root with
    ``PTF_ASSEMBLER_OUT_ROOT`` if C: is not writable.
    """
    root = pathlib.Path(os.environ.get("PTF_ASSEMBLER_OUT_ROOT")
                        or ("C:/ptf_t" if os.name == "nt" else str(tmp_path)))
    root.mkdir(parents=True, exist_ok=True)
    dest = pathlib.Path(tempfile.mkdtemp(prefix="b", dir=str(root)))
    try:
        yield dest
    finally:
        shutil.rmtree(dest, ignore_errors=True)


@pytest.fixture(autouse=True)
def _restore_go_prefix():
    """The /go/ prefix is build state; never let one test leak into the next."""
    before = go_market_prefix()
    yield
    set_go_market_prefix(before)


# --------------------------------------------------------------------------- #
# Canonical routes (sections 5, 6, 7).
# --------------------------------------------------------------------------- #

def test_columbus_hotel_routes_stay_unprefixed(markets):
    market = market_by_id(markets, COLUMBUS)
    assert market.route_mode == ROUTE_MODE_LEGACY_UNPREFIXED
    assert hotel_route(market, "Aloft Columbus Easton") == \
        "/pet-friendly-hotels/aloft-columbus-easton/"


@pytest.mark.parametrize("market_id,expected", [
    (CLEVELAND, "/pet-friendly-hotels/cleveland-akron-canton/ac-hotel-cleveland-beachwood/"),
    (DAYTON, "/pet-friendly-hotels/dayton-oh/ac-hotel-dayton/"),
])
def test_prefixed_markets_nest_hotels_under_their_slug(markets, market_id, expected):
    market = market_by_id(markets, market_id)
    name = "AC Hotel Cleveland Beachwood" if market_id == CLEVELAND else "AC Hotel Dayton"
    assert hotel_route(market, name) == expected


def test_exactly_one_market_uses_the_legacy_namespace(markets):
    """The legacy market's routes ARE the global ones; two would collide."""
    legacy = [m for m in markets if m.route_mode == ROUTE_MODE_LEGACY_UNPREFIXED]
    assert [m.market_id for m in legacy] == [COLUMBUS]


def test_anchor_is_the_legacy_market_and_a_second_one_is_refused(markets):
    assert anchor_market(markets).market_id == COLUMBUS
    with pytest.raises(AssemblyError):
        anchor_market([m for m in markets if m.market_id != COLUMBUS])


# --------------------------------------------------------------------------- #
# Fragment ownership (sections 9, 20).
# --------------------------------------------------------------------------- #

def test_no_market_claims_a_global_route(markets):
    """The whole split rests on this: no market's namespace touches the site's."""
    for market in markets:
        try:
            routes = owned_routes(market)
        except Exception:
            continue                        # unassemblable markets claim nothing
        claimed = sorted(set(routes) & set(GLOBAL_ROUTES))
        # Columbus's hub IS the category root, which is a GLOBAL route -- and it
        # is the assembler, never the fragment, that writes it. So the fragment
        # must not DECLARE it either.
        assert claimed == [], "%s claims global route(s) %s" % (market.market_id, claimed)


def test_market_hub_exists_for_prefixed_markets_only(markets):
    for market_id, expected in ((CLEVELAND, "/pet-friendly-hotels/cleveland-akron-canton/"),
                                (DAYTON, "/pet-friendly-hotels/dayton-oh/")):
        routes = owned_routes(market_by_id(markets, market_id))
        assert routes.get(expected) == "market_hub"
    columbus = owned_routes(market_by_id(markets, COLUMBUS))
    assert "market_hub" not in columbus.values()
    assert market_route(market_by_id(markets, COLUMBUS)) == "/pet-friendly-hotels/"


def test_fragment_globals_are_discarded_not_published(tmp_path, markets):
    """A fragment generates the global pages; the assembler drops every one."""
    market = market_by_id(markets, DAYTON)
    root = tmp_path / "frag"
    for rel in GLOBAL_FILES:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("global", encoding="utf-8")
    owned_hotel = root / "pet-friendly-hotels" / "dayton-oh" / "x" / "index.html"
    owned_hotel.parent.mkdir(parents=True, exist_ok=True)
    owned_hotel.write_text("market", encoding="utf-8")

    owned, discarded, violations = classify_fragment(market, root)
    assert sorted(discarded) == sorted(GLOBAL_FILES)
    assert violations == []
    assert list(owned) == ["pet-friendly-hotels/dayton-oh/x/index.html"]


def test_global_route_set_covers_every_shared_surface():
    for route in ("/", "/about/", "/contact/", "/methodology/", "/pet-friendly-hotels/"):
        assert route in GLOBAL_ROUTES
    for name in ("sitemap.xml", "robots.txt", "llms.txt", "_headers", "_redirects"):
        assert name in GLOBAL_FILES


# --------------------------------------------------------------------------- #
# Collisions (section 19).
# --------------------------------------------------------------------------- #

def test_two_markets_never_share_a_public_route(markets):
    """The property the merge depends on, asserted over the real registry."""
    seen = {}
    for market in markets:
        try:
            routes = owned_routes(market)
        except Exception:
            continue
        for route in routes:
            assert route not in seen, \
                "route %s claimed by %s and %s" % (route, seen[route], market.market_id)
            seen[route] = market.market_id


def test_hotel_slug_shared_across_markets_does_not_collide(markets):
    """Two markets may hold the same hotel name; the routes must still differ."""
    cle = market_by_id(markets, CLEVELAND)
    day = market_by_id(markets, DAYTON)
    assert hotel_route(cle, "Hampton Inn Troy") != hotel_route(day, "Hampton Inn Troy")


# --------------------------------------------------------------------------- #
# /go/ ownership (section 18).
# --------------------------------------------------------------------------- #

def test_go_routes_are_scoped_for_prefixed_markets():
    set_go_market_prefix("")
    assert go_route("ac-hotel-dayton", ACTION_CALL) == "/go/ac-hotel-dayton/call/"
    set_go_market_prefix("dayton-oh")
    assert go_route("ac-hotel-dayton", ACTION_CALL) == "/go/dayton-oh/ac-hotel-dayton/call/"


def test_go_prefix_rejects_an_unsafe_value():
    with pytest.raises(ValueError):
        set_go_market_prefix("../etc")


def test_scoped_go_routes_cannot_collide_across_markets():
    set_go_market_prefix("dayton-oh")
    day = go_route("hampton-inn-troy", ACTION_CALL)
    set_go_market_prefix("cleveland-akron-canton")
    cle = go_route("hampton-inn-troy", ACTION_CALL)
    assert day != cle


# --------------------------------------------------------------------------- #
# Breadcrumbs and canonicals (sections 22, 23).
# --------------------------------------------------------------------------- #

def _breadcrumb_items(market_id, name):
    import json
    from scripts.pettripfinder.hotel_profile_page import _head_metadata
    head = _head_metadata({"name": name, "city": "", "state": "", "address": "",
                           "postal_code": "", "website_url": ""},
                          re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-"),
                          None, market_id=market_id)
    blob = re.search(r'<script type="application/ld\+json">(.*?)</script>', head, re.S)
    payload = json.loads(blob.group(1))
    objects = payload if isinstance(payload, list) else payload.get("@graph", [payload])
    crumb = next(o for o in objects if o.get("@type") == "BreadcrumbList")
    return [(e["name"], e["item"]) for e in crumb["itemListElement"]], head


def test_prefixed_profile_breadcrumbs_pass_through_the_market_hub():
    items, head = _breadcrumb_items(DAYTON, "AC Hotel Dayton")
    assert [i[1] for i in items] == [
        "https://pettripfinder.com/",
        "https://pettripfinder.com/pet-friendly-hotels/",
        "https://pettripfinder.com/pet-friendly-hotels/dayton-oh/",
        "https://pettripfinder.com/pet-friendly-hotels/dayton-oh/ac-hotel-dayton/",
    ]
    assert ('<link rel="canonical" href="https://pettripfinder.com'
            '/pet-friendly-hotels/dayton-oh/ac-hotel-dayton/">') in head


def test_columbus_profile_keeps_its_three_level_breadcrumb():
    items, head = _breadcrumb_items(COLUMBUS, "Aloft Columbus Easton")
    assert [i[1] for i in items] == [
        "https://pettripfinder.com/",
        "https://pettripfinder.com/pet-friendly-hotels/",
        "https://pettripfinder.com/pet-friendly-hotels/aloft-columbus-easton/",
    ]
    assert ('<link rel="canonical" href="https://pettripfinder.com'
            '/pet-friendly-hotels/aloft-columbus-easton/">') in head


def test_canonical_gate_catches_a_page_pointing_at_another_route(tmp_path):
    page = tmp_path / "pet-friendly-hotels" / "dayton-oh" / "x" / "index.html"
    page.parent.mkdir(parents=True)
    page.write_text('<link rel="canonical" href="https://pettripfinder.com'
                    '/pet-friendly-hotels/x/">', encoding="utf-8")
    problems = canonical_violations(tmp_path, "https://pettripfinder.com")
    assert len(problems) == 1 and "/pet-friendly-hotels/dayton-oh/x/" in problems[0]


def test_canonical_gate_catches_two_routes_sharing_one_canonical(tmp_path):
    for slug in ("a", "b"):
        page = tmp_path / slug / "index.html"
        page.parent.mkdir(parents=True)
        page.write_text('<link rel="canonical" href="https://pettripfinder.com/a/">',
                        encoding="utf-8")
    assert canonical_violations(tmp_path, "https://pettripfinder.com")


# --------------------------------------------------------------------------- #
# Internal links (section 24).
# --------------------------------------------------------------------------- #

def test_related_hotel_cards_use_the_market_route(markets):
    """The nearby/related block slugged its own routes and produced three dead
    links on every prefixed profile."""
    from scripts.pettripfinder.hotel_profile import _related_from_production
    rows = [{"name": "AC Hotel Dayton", "city": "Dayton", "state": "OH"},
            {"name": "Hampton Inn Troy", "city": "Troy", "state": "OH"}]
    related = _related_from_production("AC Hotel Dayton", rows, {}, market_id=DAYTON)
    assert related
    for card in related:
        assert card.route.startswith("/pet-friendly-hotels/dayton-oh/"), card.route


# --------------------------------------------------------------------------- #
# Market selection and honest zero (sections 25, 27).
# --------------------------------------------------------------------------- #

def test_cincinnati_is_registered_below_threshold_and_not_assembled(markets):
    row = market_eligibility(market_by_id(markets, CINCINNATI))
    assert row["published_count"] == 0
    assert row["conditions"]["census_present"] is True
    assert row["conditions"]["meets_minimum_published"] is False
    assert row["assemblable"] is False


def test_cincinnati_does_not_fail_the_global_selection(markets):
    chosen, rows = select_markets(markets)
    assert CINCINNATI not in [m.market_id for m in chosen]
    assert CINCINNATI in [r["market_id"] for r in rows]
    # Pittsburgh is currently assemblable but remains hidden from navigation;
    # Indianapolis is source-ready but withheld from the first multi-market
    # launch by founder decision (PTF-046, deploy/netlify/launch_participation.json).
    assert sorted(m.market_id for m in chosen) == sorted(
        [CLEVELAND, COLUMBUS, DAYTON, "pittsburgh-pa", "milwaukee-wi",
         "st-louis-mo",
         # PTF-LOUISVILLE-PUBLICATION-008: the seventh, admitted the same way.
         "louisville-ky"])


def test_indianapolis_is_registered_above_threshold_and_source_ready(markets):
    row = market_eligibility(market_by_id(markets, INDIANAPOLIS))
    assert row["published_count"] == 24  # PTF-INDIANAPOLIS-FOUNDER-PROMOTION-004
    assert row["conditions"]["census_present"] is True
    assert row["conditions"]["meets_minimum_published"] is True
    assert row["assemblable"] is True


def test_indianapolis_is_source_ready_but_not_in_the_global_selection(markets):
    """PTF-046: the founder withheld Indianapolis (8 profiles) from the first
    multi-market launch on coverage. Its source is untouched and still
    assemblable; participation is the separate, recorded decision."""
    chosen, rows = select_markets(markets)
    assert INDIANAPOLIS not in [m.market_id for m in chosen]
    row = next(r for r in rows if r["market_id"] == INDIANAPOLIS)
    assert row["assemblable"] is True
    assert row["launch_status"] == \
        "SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH"
    assert row["participates"] is False
    assert sorted(m.market_id for m in chosen) == sorted(
        [CLEVELAND, COLUMBUS, DAYTON, "pittsburgh-pa", "milwaukee-wi",
         "st-louis-mo",
         # PTF-LOUISVILLE-PUBLICATION-008: the seventh, admitted the same way.
         "louisville-ky"])


def test_participation_is_a_founder_decision_layered_on_source_readiness(markets):
    """``assemblable`` stays a pure source fact (the four conditions) and
    ``participates`` is that AND the founder's authorization -- reported apart
    so a withheld market is never mistaken for a broken one."""
    for row in (market_eligibility(m) for m in markets):
        assert row["assemblable"] is all(row["conditions"].values())
        assert row["participates"] is (row["assemblable"]
                                       and row["founder_authorized_for_launch"])
        assert "founder_authorized_for_launch" not in row["conditions"]


def test_navigation_visibility_is_not_an_assembly_condition(markets):
    """A market may be assembled and hidden; conflating them would let a
    visibility decision silently change what the bundle contains."""
    for row in (market_eligibility(m) for m in markets):
        assert "show_in_navigation" not in row["conditions"]


def test_current_live_inventory_preserves_all_assemblable_market_profiles(markets):
    """Section 28's target at the time, DERIVED -- not a constant in the code.
    176 since the Pass-2 founder decisions; 216 since
    PTF-CLEVELAND-PASS3-FOUNDER-DECISIONS-001 published forty more Cleveland
    hotels; 233 since PTF-PITTSBURGH-PASS1-DECISION-APPLICATION-001 published
    the first seventeen Pittsburgh hotels; 242 since
    PTF-PITTSBURGH-PASS2-DECISION-APPLICATION-001 published nine more; 250
    after Indianapolis published its eight founder-approved records; 268 since
    PTF-CLEVELAND-PASS4-DECISION-APPLICATION-001 published eighteen more
    Cleveland hotels (81 -> 99); 341 since PTF-MILWAUKEE-PUBLICATION-042
    published Milwaukee's seventy-three, approved across two founder sittings.
    Every other market's count is unchanged, which is the half of this
    assertion that says a new market did not disturb an old one."""
    counts = {m.market_id: len(published_hotels(m))
              for m in markets if market_eligibility(m)["assemblable"]}
    assert counts == {COLUMBUS: 88, CLEVELAND: 99, DAYTON: 47,
                      "pittsburgh-pa": 26,
                      # PTF-INDIANAPOLIS-FOUNDER-PROMOTION-004: 8 -> 24 founder-signed profiles over the
                      # promoted 257-identity census.
                      INDIANAPOLIS: 24,
                      "milwaukee-wi": 73,
                      # PTF-ST-LOUIS-REGISTER-PUBLISH-011: 82 founder-signed
                      # profiles. Every other count above is unchanged, which
                      # is the half of this assertion that says a new market
                      # did not disturb an old one.
                      "st-louis-mo": 82,
                      # PTF-LOUISVILLE-PUBLICATION-008: 46 founder-signed
                      # profiles over a 166-identity census. Same half of the
                      # assertion, same conclusion -- nothing above moved.
                      "louisville-ky": 46}
    # PTF-INDIANAPOLIS-FOUNDER-PROMOTION-004: 469 + Indianapolis's 16 further
    # founder-signed profiles (8 -> 24). Every other market's count above is
    # unchanged, so the whole of this movement is Indianapolis's.
    assert sum(counts.values()) == 485   # 423 + Louisville (46) + Indianapolis (+16)


# --------------------------------------------------------------------------- #
# Global surfaces (sections 14, 15, 16).
# --------------------------------------------------------------------------- #

def test_sitemap_is_exactly_the_routes_it_is_given():
    routes = ["/", "/pet-friendly-hotels/", "/pet-friendly-hotels/dayton-oh/"]
    xml = build_global_sitemap(routes, "https://pettripfinder.com")
    locs = re.findall(r"<loc>([^<]+)</loc>", xml)
    assert locs == ["https://pettripfinder.com" + r for r in routes]
    assert len(locs) == len(set(locs))


def test_llms_txt_names_only_markets_it_was_given():
    entries = [{"name": "Dayton", "route": "/pet-friendly-hotels/dayton-oh/",
                "comparison_route": "/pet-friendly-hotels/dayton-oh/policy-comparison/"}]
    text = build_global_llms(entries, "https://pettripfinder.com")
    assert "/pet-friendly-hotels/dayton-oh/" in text
    assert "cincinnati" not in text.lower()


def test_manifest_hotel_routes_match_the_canonical_helper(markets):
    """Defect I: the manifest must declare the routes the builder WRITES."""
    from scripts.pettripfinder.build_market_manifest import build_package
    for market_id in (COLUMBUS, CLEVELAND, DAYTON):
        market = market_by_id(markets, market_id)
        package = build_package(market_id)
        expected = sorted(hotel_route(market, r["name"])
                          for r in published_hotels(market))
        assert list(package.hotel_routes) == expected


# --------------------------------------------------------------------------- #
# Whole-bundle proofs (sections 21, 30, 34, 35) -- opt-in, they build the site.
# --------------------------------------------------------------------------- #

@needs_build
def test_combined_bundle_assembles_with_every_gate_passing(short_out):
    manifest = gasm.assemble(str(short_out / "bundle"))
    assert manifest["all_gates_pass"] is True
    assert manifest["broken_links"] == 0
    assert manifest["collision_count"] == 0
    assert manifest["global_shadowing_count"] == 0
    assert manifest["canonical_violations"] == 0
    assert manifest["deployment_authorized"] is False
    assert sum(len(f["hotel_routes"]) for f in manifest["fragments"].values()) == 176  # after Pass-2 decisions


@needs_build
def test_assembly_is_byte_identical_when_run_twice(short_out):
    first = gasm.assemble(str(short_out / "1"))
    second = gasm.assemble(str(short_out / "2"))
    assert first["bundle_sha256"] == second["bundle_sha256"]
    assert gasm.file_hashes(short_out / "1" / "site") == \
        gasm.file_hashes(short_out / "2" / "site")


@needs_build
def test_adding_a_market_moves_no_earlier_market_owned_byte(short_out, markets):
    only = [market_by_id(markets, COLUMBUS)]
    both = only + [market_by_id(markets, CLEVELAND)]
    gasm.assemble(str(short_out / "1"), markets=only)
    gasm.assemble(str(short_out / "2"), markets=both)
    before = gasm.file_hashes(short_out / "1" / "site")
    after = gasm.file_hashes(short_out / "2" / "site")
    owned = [k for k in before if k not in GLOBAL_FILES]
    assert owned
    for key in owned:
        assert key in after, "%s disappeared when a market was added" % key
        assert before[key] == after[key], "%s moved when a market was added" % key
