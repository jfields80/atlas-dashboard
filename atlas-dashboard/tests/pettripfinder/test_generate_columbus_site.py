"""AES-SITE-001 -- end-to-end integration test for the real Columbus site
build. No network (the whole generator is local-file-only); writes to a
pytest tmp_path, never the operational ``data/site_builds/`` root used for
manual inspection."""

from __future__ import annotations

import json
import re

import pytest

from scripts.generate_pettripfinder_columbus_site import _llms_txt, run
from scripts.pettripfinder.market_context import production_market
from scripts.pettripfinder.site_data import load_published_hotel_policy_facts

# Non-profile directories under /pet-friendly-hotels/: the comparison page
# plus every corridor slug the market config could publish (PTF-CORRIDORS-002:
# corridor pages are config-driven, so tests derive the set from the config
# rather than naming corridors).
_NON_PROFILE_DIRS = {"policy-comparison"} | {
    c.slug for c in production_market().corridors}

# PTF-PROD-002A: the generator's verified pet-policy content now comes from the
# TRACKED publishable package (launch_packages/pettripfinder/hotel_policy_facts.json),
# not the gitignored operational corpus -- so this end-to-end test runs in a
# clean checkout. The guard remains only as defence against the package being
# absent entirely (e.g. before its first export); normally it is committed and
# this test runs everywhere.
_HAS_PUBLISHED_FACTS = bool(load_published_hotel_policy_facts())

pytestmark = pytest.mark.skipif(
    not _HAS_PUBLISHED_FACTS,
    reason="tracked hotel_policy_facts.json package absent -- run "
           "scripts/pettripfinder/export_hotel_policy_facts.py",
)


@pytest.fixture(scope="module")
def built_site(tmp_path_factory):
    out = tmp_path_factory.mktemp("ptf_columbus_site")
    exit_code = run(str(out))
    assert exit_code == 0
    return out


def test_build_succeeds_and_reports_launch_ready(built_site):
    report = json.loads((built_site / "_build_report.json").read_text(encoding="utf-8"))
    assert report["launch_inventory_ready"] is True
    assert report["hotel_count"] == 88   # PTF-COLUMBUS-HYATT-002: verified-only public hotels
    assert report["park_count"] == 14
    assert report["restaurant_count"] == 13
    assert not report["warnings"]


class TestLlmsTxtNamesOnlyRoutesThatExist:
    """PTF-CLEVELAND-DAYTON-WORKER-INTEGRATION-001. llms.txt used to hard-code
    Columbus's five routes for every market, so Dayton and Cleveland shipped a
    machine-readable index pointing at pages they do not publish. The internal
    link checker reads HTML and never saw it."""

    def test_a_full_market_advertises_every_section(self):
        routes = ["/pet-friendly-hotels/", "/pet-friendly-parks/",
                  "/pet-friendly-restaurants/", "/methodology/"]
        out = _llms_txt("Columbus", routes, "/pet-friendly-hotels/policy-comparison/")
        assert "- Pet-friendly parks: /pet-friendly-parks/" in out
        assert "- Pet-friendly restaurants: /pet-friendly-restaurants/" in out
        assert ("- Hotel pet-policy comparison: "
                "/pet-friendly-hotels/policy-comparison/") in out

    def test_a_hotels_only_market_advertises_no_parks_or_restaurants(self):
        out = _llms_txt("Dayton & West Central Ohio",
                        ["/pet-friendly-hotels/", "/methodology/"],
                        "/pet-friendly-hotels/dayton-oh/policy-comparison/")
        assert "/pet-friendly-parks/" not in out
        assert "/pet-friendly-restaurants/" not in out
        assert "# PetTripFinder Dayton & West Central Ohio" in out

    def test_the_comparison_route_follows_the_markets_route_mode(self):
        """A market-prefixed comparison page must not be advertised at the
        market-less Columbus path."""
        cmp_route = "/pet-friendly-hotels/cleveland-akron-canton/policy-comparison/"
        out = _llms_txt("Cleveland", ["/pet-friendly-hotels/", "/methodology/"], cmp_route)
        assert cmp_route in out
        assert "- Hotel pet-policy comparison: /pet-friendly-hotels/policy-comparison/" not in out

    def test_every_advertised_route_is_one_the_build_wrote(self, built_site):
        """End-to-end: parse the real file and require each path to exist."""
        text = (built_site / "llms.txt").read_text(encoding="utf-8")
        advertised = re.findall(r"^- .+?: (/\S*)$", text, flags=re.M)
        assert advertised
        for route in advertised:
            assert (built_site / route.strip("/") / "index.html").is_file(), route


def test_quality_report_clean(built_site):
    report = json.loads((built_site / "_quality_report.json").read_text(encoding="utf-8"))
    assert report["failures"] == []
    assert report["unique_canonicals"] == report["real_content_pages"]


def test_broken_link_report_clean(built_site):
    report = json.loads((built_site / "_broken_link_report.json").read_text(encoding="utf-8"))
    assert report["broken_links"] == []


def test_core_pages_exist(built_site):
    for rel in ("index.html", "sitemap.xml", "robots.txt", "llms.txt", "styles.css",
                "methodology/index.html", "pet-friendly-hotels/index.html",
                "pet-friendly-hotels/policy-comparison/index.html",
                # PROD-004 verified-only: Dublin still clears the corridor minimum;
                # Downtown Columbus now has 4 verified hotels (< the minimum of 5)
                # and is intentionally not generated (and never linked -- see the
                # dynamic hub corridor links).
                "pet-friendly-hotels/dublin/index.html"):
        assert (built_site / rel).exists(), rel
    # PTF-INVENTORY-001: Downtown reached CORRIDOR_MIN_PROPERTIES (5) when the
    # Red Roof Convention Center property was promoted, so it now earns an
    # indexable corridor route it previously did not.
    assert (built_site / "pet-friendly-hotels" / "downtown-columbus" / "index.html").exists()
    # PTF-CORRIDORS-002: the explicit operator-reviewed Easton assignment
    # gives Easton five verified members, so it publishes on current data.
    assert (built_site / "pet-friendly-hotels" / "easton" / "index.html").exists()
    # PTF-CORRIDORS-003: Airport reached six verified members under the
    # 70-hotel authority, crossing the five-member minimum, so it now
    # publishes on the same explicit-assignment terms as Easton. It was
    # asserted absent here while it stood at four.
    assert (built_site / "pet-friendly-hotels" / "airport" / "index.html").exists()
    # Grove City crossed minimum_published_hotels when
    # PTF-COLUMBUS-INTEGRATE-UNRESOLVED-001 published Candlewood Suites Grove
    # City, taking it from four members to five, so it now routes.
    assert (built_site / "pet-friendly-hotels" / "grove-city" / "index.html").exists()
    # Corridors still below the minimum stay suppressed -- no route.
    # Hilliard crossed its minimum when PTF-COLUMBUS-FINAL-CLOSURE-001
    # published Red Roof Inn Columbus West Hilliard.
    assert (built_site / "pet-friendly-hotels" / "hilliard-west-columbus"
            / "index.html").exists()
    assert not (built_site / "pet-friendly-hotels" / "worthington-north-columbus").exists()


def test_hotel_profile_with_facts_rendered_by_approved_renderer(built_site):
    # DESIGN-004: hotel profiles come from the founder-approved profile design
    # (hotel_profile_page -> approved_hotel_profile), not the old debug-like
    # layout. A verified hotel shows the approved verified chip and the
    # approved six-fact strip -- never the old ptf-policy-table/badge markup.
    text = (built_site / "pet-friendly-hotels" / "drury-inn-suites-columbus-grove-city"
           / "index.html").read_text(encoding="utf-8")
    assert "Policy verified" in text
    assert 'class="hp-facts"' in text          # approved fact strip
    assert 'class="hp-chip"' in text           # approved verified chip
    assert "$50" in text
    assert "ptf-policy-table" not in text       # old markup path is gone
    assert "ptf-badge--verified" not in text


def test_held_manual_review_hotel_has_no_public_profile(built_site):
    # PROD-004 verified-only: a seed hotel absent from the committed policy package
    # no longer receives a public profile at all -- the unverified-state renderer
    # still exists and is exercised by the renderer's own fixture tests, but the
    # public build never emits an unverified hotel page.
    #
    # Aloft was this test's example until PTF-CAPTURE-003F published it, then
    # Drury Plaza until PTF-COLUMBUS-SELECTOR-CLOSEOUT-001 published that.
    # Two are named so a single future promotion cannot empty the assertion
    # without anyone noticing; Hyatt House is ADR-blocked and Extended Stay
    # Dublin holds an unresolved policy contradiction, so neither is close.
    # PTF-COLUMBUS-HYATT-002 published Hyatt House Short North from
    # operator-supplied screenshots, so it left this list. Extended Stay
    # Dublin remains held on an unresolved fee contradiction, and Hyatt
    # Place Polaris remains ADR-blocked with no evidence supplied.
    assert not (built_site / "pet-friendly-hotels"
                / "extended-stay-america-suites-columbus-dublin" / "index.html").exists()


def test_no_production_row_ever_shows_no_pets_badge(built_site):
    # Production contains zero no-pets rows (004I finding) -- confirm the
    # site never fabricates one.
    for path in (built_site / "pet-friendly-hotels").rglob("index.html"):
        if path.parent.name in _NON_PROFILE_DIRS:
            continue
        if path.parent == built_site / "pet-friendly-hotels":
            continue
        text = path.read_text(encoding="utf-8")
        assert "ptf-badge--no-pets" not in text


def test_go_pages_are_noindex(built_site):
    go_pages = list((built_site / "go").rglob("index.html"))
    assert len(go_pages) > 0
    for p in go_pages:
        text = p.read_text(encoding="utf-8")
        assert 'content="noindex, nofollow"' in text


def test_go_page_destination_matches_real_official_url(built_site):
    text = (built_site / "go" / "drury-inn-suites-columbus-grove-city" / "official-website"
           / "index.html").read_text(encoding="utf-8")
    assert "druryhotels.com" in text


def test_sitemap_excludes_go_pages(built_site):
    sitemap = (built_site / "sitemap.xml").read_text(encoding="utf-8")
    assert "/go/" not in sitemap


def test_sitemap_includes_comparison_and_corridor_pages(built_site):
    sitemap = (built_site / "sitemap.xml").read_text(encoding="utf-8")
    assert "/pet-friendly-hotels/policy-comparison/" in sitemap
    assert "/pet-friendly-hotels/dublin/" in sitemap
    # PTF-INVENTORY-001: Downtown now meets CORRIDOR_MIN_PROPERTIES and IS
    # generated, so it must appear in the sitemap exactly like Dublin.
    assert "/pet-friendly-hotels/downtown-columbus/" in sitemap
    # PTF-CORRIDORS-002: published corridors from the market config appear;
    # suppressed (below-minimum) corridors never do.
    assert "/pet-friendly-hotels/easton/" in sitemap
    # PTF-CORRIDORS-003: Airport publishes at six members under the
    # 70-hotel authority; a still-suppressed corridor keeps the negative.
    assert "/pet-friendly-hotels/airport/" in sitemap
    assert "/pet-friendly-hotels/grove-city/" in sitemap


def test_sitemap_covers_every_indexable_route_exactly_once(built_site):
    """PTF-LAUNCH-001 regression.

    The homepage's bundle key is ``index.html`` with no directory prefix, so an
    ``endswith("/index.html")`` filter silently dropped the site's most
    important URL. Assert the sitemap is exactly the set of on-disk indexable
    routes -- homepage included, /go/ interstitials excluded, no duplicates.
    """
    locs = re.findall(r"<loc>([^<]+)</loc>",
                      (built_site / "sitemap.xml").read_text(encoding="utf-8"))

    # every entry is absolute on the canonical host
    assert locs, "sitemap contains no <loc> entries"
    for loc in locs:
        assert loc.startswith("https://pettripfinder.com/"), loc

    assert len(locs) == len(set(locs)), "sitemap contains duplicate <loc> entries"

    def route_of(path):
        rel = path.parent.relative_to(built_site).as_posix()
        return "/" if rel == "." else "/%s/" % rel

    on_disk = {route_of(p) for p in built_site.rglob("index.html")}
    indexable = {r for r in on_disk if not r.startswith("/go/")}
    go_routes = {r for r in on_disk if r.startswith("/go/")}
    in_sitemap = {loc[len("https://pettripfinder.com"):] for loc in locs}

    # the homepage specifically -- the defect this test exists for
    assert "/" in in_sitemap
    assert sum(1 for loc in locs if loc == "https://pettripfinder.com/") == 1

    # exact coverage: nothing missing, nothing invented
    assert in_sitemap == indexable, (
        "missing=%s unexpected=%s"
        % (sorted(indexable - in_sitemap), sorted(in_sitemap - indexable)))

    # /go/ interstitials are noindex and must never be advertised
    assert go_routes, "expected /go/ interstitials to exist in the build"
    assert not (in_sitemap & go_routes)


def test_robots_allows_ai_and_search_crawlers(built_site):
    robots = (built_site / "robots.txt").read_text(encoding="utf-8")
    for agent in ("GPTBot", "OAI-SearchBot", "ClaudeBot", "anthropic-ai", "Googlebot", "Bingbot"):
        assert agent in robots
    assert "Disallow: /go/" in robots
    assert not re.search(r"User-agent: \*\s*\nDisallow: /\s*$", robots, re.M)


def test_comparison_page_lists_the_verified_hotels(built_site):
    # PROD-004 verified-only: the comparison table lists exactly the committed
    # package hotels; no held/manual-review hotel appears.
    text = (built_site / "pet-friendly-hotels" / "policy-comparison" / "index.html").read_text(encoding="utf-8")
    rows = re.findall(r"<tr>", text)
    assert len(rows) == 89  # header + 88 verified hotels
    # Held properties are named in FULL: "Red Roof" alone is no longer a valid
    # exclusion probe now that the Convention Center property is published
    # (PTF-INVENTORY-001), and a bare-brand check would silently pass forever.
    for held in (
                 # Sonesta Simply Suites was promoted 2026-08-02 and is now
                 # published, so it is deliberately NOT an exclusion probe.
                 # PTF-PROMOTION-002: "Extended Stay" alone stopped being a
                 # valid probe once Hawthorn Extended Stay by Wyndham published
                 # -- the bare brand now matches a hotel that SHOULD appear, so
                 # the held property is named in full, exactly as the Red Roof
                 # entries already are.
                 # PTF-COLUMBUS-FINAL-CLOSURE-001 published both Red Roofs, so
                 # they left this list and are asserted PRESENT below.
                 # PTF-COLUMBUS-SELECTOR-CLOSEOUT-001 published Drury Plaza
                 # Hotel Columbus Downtown, which left it for the same reason.
                 "Extended Stay America Suites Columbus Dublin",
                 "Extended Stay America Suites Columbus Dublin"):
        assert held not in text
    # The published hotel whose name contains the held brand must still appear.
    assert "Hawthorn Extended Stay by Wyndham Columbus West" in text
    # ...and the newly promoted properties ARE present.
    assert "Red Roof PLUS+ Columbus Downtown Convention Center" in text
    # PTF-CAPTURE-003F: Aloft University District now publishes.
    assert "Aloft Columbus University District" in text
    # PTF-PROMOTE: Staybridge publishes from prose, with its fee withheld.
    assert "Staybridge Suites Columbus Dublin" in text


def test_every_profile_has_exactly_one_structured_data_lodging_or_place_entry(built_site):
    for slug, ld_type in (("pet-friendly-hotels", "LodgingBusiness"),
                          ("pet-friendly-parks", "Park"), ("pet-friendly-restaurants", "Restaurant")):
        found_any = False
        for path in (built_site / slug).iterdir():
            if not path.is_dir() or path.name in _NON_PROFILE_DIRS:
                continue
            text = (path / "index.html").read_text(encoding="utf-8")
            payloads = re.findall(r'<script type="application/ld\+json">(.*?)</script>', text)
            types = [json.loads(p.replace("<\\/", "</")).get("@type") for p in payloads]
            assert ld_type in types, path
            found_any = True
        assert found_any


def test_css_appended_and_referenced(built_site):
    css = (built_site / "styles.css").read_text(encoding="utf-8")
    assert ".ptf-policy-table" in css
    assert ".ptf-badge--verified" in css


def test_skip_link_present_on_content_pages_not_go_pages(built_site):
    # The approved coded homepage carries its own skip link ("skip skip-link");
    # /go/ redirect pages have no <main> and intentionally none.
    hub = (built_site / "index.html").read_text(encoding="utf-8")
    assert "skip-link" in hub and 'href="#main"' in hub
    go_page = (built_site / "go" / "drury-inn-suites-columbus-grove-city" / "official-website"
              / "index.html").read_text(encoding="utf-8")
    assert "skip-link" not in go_page
