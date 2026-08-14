"""PTF-MULTI-MARKET-HOMEPAGE-AWARENESS-001 -- the homepage is one market's.

The approved homepage renderer carried a single market's identity as literals:
page title and description, wordmark, hero headline, hero badge, search
location, trip-planning copy, the emergency-veterinarian Maps query, the
footer label, and a photograph of the Scioto riverfront. Every non-Columbus
build inherited all of it, so a Dayton reader was shown a Columbus skyline,
told they were on "PetTripFinder . Columbus", and handed a Maps link that
searched for emergency vets in the wrong city.

That identity is now configuration (``markets.homepage_config``), derived from
fields every market already declares. These tests hold both halves of the
guarantee:

  * the approved Columbus homepage is unchanged, byte for byte -- pinned here
    by the sha256 of the page as it was BUILT BEFORE this change, plus the
    production bundle hash that page contributes to;
  * no other market -- including one registered tomorrow -- can be handed
    Columbus's words, its photograph or its vet query.
"""

from __future__ import annotations

import ast
import hashlib
import html.parser
import json
import pathlib
import re

import pytest

from scripts.pettripfinder.approved_home import render as approved_home
from scripts.pettripfinder.approved_home.render import HomepageAssetError, render_home
from scripts.pettripfinder.markets import (
    MarketContractError,
    homepage_config,
    load_markets,
    market_by_id,
    market_route,
    parse_market,
)
from scripts.pettripfinder.markets.routes import market_route_table
from scripts.pettripfinder.markets import assign_hotels

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

COLUMBUS = "columbus-oh"
DAYTON = "dayton-oh"
CLEVELAND = "cleveland-akron-canton-oh"

#: The approved Columbus homepage, hashed from the page this build produced at
#: de2e467 -- BEFORE the renderer became market-aware. It is the witness for
#: "byte-identical": a homepage design change is an operator decision, and
#: re-pinning this constant is how that decision gets recorded.
COLUMBUS_HOME_SHA256 = "9da6c83a3a0e6b98f67f0b81a7fd0c122412d8359611f993408fe2b8b4cfe7a5"
COLUMBUS_HOME_BYTES = 42218

#: The frozen Columbus production bundle (PTF-COLUMBUS-FREEZE-DEPLOY-001).
#:
#: Re-pinned by PTF-RENDERER-FIDELITY-001. Phase B deliberately changes what
#: the pages SAY -- that is its entire purpose -- so byte-identity is not the
#: right test for it, and this constant moves for the first time since the
#: freeze. What still holds, and is asserted alongside it, is that every gate
#: passes and the bundle carries the same 88 hotel profiles.
#:
#: The change was reviewed as a public diff over all 156 committed records: 61
#: records changed, 146 field-level differences, 0 unexpected. Of Columbus's 54
#: differences, the substantive ones are the scope disclosure on records that
#: state an amount without saying who it attaches to (§9), and the withheld
#: treatment on the six conflict/withheld records that previously rendered
#: through the dim silence class (§6).
#:
#: Previous value, at PTF-COLUMBUS-FREEZE-DEPLOY-001 through Phase A:
#:     404c4ff58a085e102e061701fbe3db52fa6952c1cbe3d7657409c04e274818c4
COLUMBUS_BUNDLE_SHA256 = "f52b5f569d1aefce270f3f1c07cb395debe98241a6c8e849f47dee89eac334f3"

#: Words that belong to the Columbus market and to no other.
COLUMBUS_TERMS = ("Columbus", "Scioto", "Dublin", "Polaris", "Easton", "Grove City",
                  "Hilliard", "Reynoldsburg", "Gahanna", "Worthington", "Westerville")


# --------------------------------------------------------------------------- #
# Fixtures: real market configs, synthetic inventory.
#
# The identity under test is configuration, so the hotel rows deliberately are
# not: synthetic rows keep these tests independent of any market's inventory
# totals, which are owned by that market's own authority tests.
# --------------------------------------------------------------------------- #

def _rows(*names):
    return [{"name": n, "category": "pet-friendly-hotels", "city": "Somewhere",
             "state": "OH", "observed_at": "2026-08-10"} for n in names]


def _facts(*names):
    from scripts.pettripfinder.site_data import normalize_name
    return {normalize_name(n): {"verified_at": "2026-08-10",
                                "facts": {"pet_fee": "$50.00", "fee_basis": "per night",
                                          "pet_count_limit": "2",
                                          "weight_limit": "50 lb",
                                          "species_allowed": "dogs"}}
            for n in names}


SYNTHETIC_NAMES = ("Riverside Inn", "Airport Suites", "Downtown Lodge")


def home_for(market_id, *, published=("pet-friendly-hotels",)):
    market = market_by_id(load_markets(), market_id)
    rows = _rows(*SYNTHETIC_NAMES)
    return render_home(rows, _facts(*SYNTHETIC_NAMES), hotel_count=len(rows),
                       park_count=0, restaurant_count=0, market=market,
                       published_categories=list(published))


@pytest.fixture(scope="module")
def columbus_home():
    """The approved page, rendered exactly as the historical caller did."""
    from scripts.pettripfinder.site_data import (
        load_published_hotel_policy_facts, read_production_rows, verified_public_hotels,
    )
    facts = load_published_hotel_policy_facts()
    rows = [r for r in read_production_rows() if r["category"] == "pet-friendly-hotels"]
    verified = verified_public_hotels(rows, facts)
    return render_home(verified, facts, hotel_count=len(verified),
                       park_count=14, restaurant_count=13)


@pytest.fixture(scope="module")
def toledo_home():
    """A market registered with no ``homepage`` block at all -- the cheapest
    possible way to add market N+1."""
    market = parse_market(dict(FUTURE_MARKET), source="<test>")
    rows = _rows(*SYNTHETIC_NAMES)
    return render_home(rows, _facts(*SYNTHETIC_NAMES), hotel_count=len(rows),
                       park_count=0, restaurant_count=0, market=market,
                       corridor_nav=[], published_categories=["pet-friendly-hotels"])


@pytest.fixture(scope="module")
def dayton_home():
    return home_for(DAYTON)


@pytest.fixture(scope="module")
def cleveland_home():
    return home_for(CLEVELAND)


# --------------------------------------------------------------------------- #
# 1. Columbus is unchanged.
# --------------------------------------------------------------------------- #

class TestColumbusIsByteIdentical:

    def test_the_default_render_is_the_approved_page(self, columbus_home):
        payload = columbus_home.encode("utf-8")
        assert len(payload) == COLUMBUS_HOME_BYTES
        assert hashlib.sha256(payload).hexdigest() == COLUMBUS_HOME_SHA256

    def test_naming_columbus_explicitly_renders_the_same_bytes(self, columbus_home):
        """The production build now passes its market and its categories. That
        must be indistinguishable from the historical implicit call."""
        from scripts.pettripfinder.site_data import (
            load_published_hotel_policy_facts, read_production_rows,
            verified_public_hotels,
        )
        facts = load_published_hotel_policy_facts()
        rows = [r for r in read_production_rows() if r["category"] == "pet-friendly-hotels"]
        verified = verified_public_hotels(rows, facts)
        explicit = render_home(
            verified, facts, hotel_count=len(verified), park_count=14,
            restaurant_count=13, market=market_by_id(load_markets(), COLUMBUS),
            published_categories=["pet-friendly-hotels", "pet-friendly-parks",
                                  "pet-friendly-restaurants"])
        assert explicit == columbus_home

    def test_the_approved_hero_photograph_is_still_columbus_only(self, columbus_home):
        assert 'src="assets/hero-right.jpg"' in columbus_home
        assert "Scioto riverfront" in columbus_home
        assert "hero-media--neutral" not in columbus_home

    def test_no_supplement_css_is_emitted_for_columbus(self, columbus_home):
        for marker in ("hero-plate", "trip-grid--n", "glance--wrap", ".ph-top .brand{font-size"):
            assert marker not in columbus_home


class TestColumbusProductionBundle:
    """The deployed bundle hash is the outermost witness: it covers the
    homepage bytes, every hotel profile, and the assembler's own gates."""

    def test_the_frozen_bundle_hash_is_unchanged(self, tmp_path):
        from scripts.pettripfinder.assemble_netlify_bundle import assemble
        manifest = assemble("production", str(tmp_path / "bundle"))
        assert manifest["all_gates_pass"] is True
        assert manifest["hotel_profile_routes"] == 88
        assert manifest["bundle_sha256"] == COLUMBUS_BUNDLE_SHA256


# --------------------------------------------------------------------------- #
# 2/3. Dayton and Cleveland publish their own identity.
# --------------------------------------------------------------------------- #

class TestDaytonUsesDaytonConfiguration:

    def test_the_title_and_description_are_daytons(self, dayton_home):
        title = re.search(r"<title>(.*?)</title>", dayton_home).group(1)
        assert title == "Pet-Friendly Travel in Dayton &amp; West Central Ohio | PetTripFinder"
        description = re.search(r'name="description" content="(.*?)"', dayton_home).group(1)
        assert description == homepage_config(
            market_by_id(load_markets(), DAYTON)).meta_description

    def test_the_wordmark_and_footer_label_are_daytons(self, dayton_home):
        assert dayton_home.count("<em>Dayton</em>") == 2      # header + footer lockups
        assert "Verified pet-travel guide for Dayton &amp; West Central Ohio." in dayton_home

    def test_the_hero_names_dayton(self, dayton_home):
        assert "<h1>Find a Dayton trip<br>that <em>actually</em> works<br>for your pet.</h1>" \
            in dayton_home
        assert "<b>Dayton, OH</b>" in dayton_home                       # search location
        assert "Dayton &amp; West Central Ohio</b>" in dayton_home      # hero badge

    def test_the_trip_section_names_dayton(self, dayton_home):
        assert "<h2>Plan the rest of your pet-friendly trip in Dayton</h2>" in dayton_home

    def test_the_comparison_route_follows_daytons_route_mode(self, dayton_home):
        route = market_route(market_by_id(load_markets(), DAYTON)) + "policy-comparison/"
        assert route == "/pet-friendly-hotels/dayton-oh/policy-comparison/"
        assert route in dayton_home
        assert '"/pet-friendly-hotels/policy-comparison/"' not in dayton_home


class TestClevelandUsesClevelandConfiguration:

    def test_the_title_and_labels_are_clevelands(self, cleveland_home):
        title = re.search(r"<title>(.*?)</title>", cleveland_home).group(1)
        assert title == "Pet-Friendly Travel in Cleveland–Akron–Canton, Ohio | PetTripFinder"
        assert cleveland_home.count("<em>Cleveland–Akron–Canton</em>") == 2
        assert ("Verified pet-travel guide for Cleveland–Akron–Canton, Ohio."
                in cleveland_home)

    def test_the_hero_names_cleveland(self, cleveland_home):
        assert "<h1>Find a Cleveland trip<br>" in cleveland_home
        assert "<b>Cleveland, OH</b>" in cleveland_home
        assert "Cleveland–Akron–Canton, Ohio</b>" in cleveland_home

    def test_the_comparison_route_follows_clevelands_route_mode(self, cleveland_home):
        assert "/pet-friendly-hotels/cleveland-akron-canton/policy-comparison/" in cleveland_home
        assert '"/pet-friendly-hotels/policy-comparison/"' not in cleveland_home


# --------------------------------------------------------------------------- #
# 4/5. No cross-market leakage.
# --------------------------------------------------------------------------- #

class TestNoCrossMarketLeakage:

    @pytest.mark.parametrize("term", COLUMBUS_TERMS)
    def test_dayton_says_nothing_about_columbus(self, dayton_home, term):
        assert not re.search(r"\b%s\b" % term, dayton_home)

    @pytest.mark.parametrize("term", COLUMBUS_TERMS)
    def test_cleveland_says_nothing_about_columbus(self, cleveland_home, term):
        assert not re.search(r"\b%s\b" % term, cleveland_home)

    def test_cleveland_says_nothing_about_dayton(self, cleveland_home):
        assert not re.search(r"\bDayton\b", cleveland_home)

    def test_dayton_says_nothing_about_cleveland(self, dayton_home):
        for term in ("Cleveland", "Akron", "Canton"):
            assert not re.search(r"\b%s\b" % term, dayton_home)

    def test_neither_market_ships_the_columbus_photograph(self, dayton_home, cleveland_home):
        for page in (dayton_home, cleveland_home):
            assert "hero-right.jpg" not in page
            assert "hero.jpg" not in page
            assert 'class="hero-media hero-media--neutral"' in page

    def test_city_photography_is_not_copied_into_a_market_that_cannot_use_it(self, tmp_path):
        copied = approved_home.copy_assets(tmp_path, include_city_photography=False)
        names = {p.name for p in (tmp_path / "assets").glob("*")}
        assert "hero-right.jpg" not in names and "hero.jpg" not in names
        assert "trip1.jpg" in names and "hotel1.jpg" in names   # place-neutral imagery stays
        assert copied == len(names)

    def test_columbus_still_receives_its_own_photography(self, tmp_path):
        approved_home.copy_assets(tmp_path)
        names = {p.name for p in (tmp_path / "assets").glob("*")}
        assert {"hero.jpg", "hero-right.jpg"} <= names


# --------------------------------------------------------------------------- #
# 6. The emergency-veterinarian query.
# --------------------------------------------------------------------------- #

class TestEmergencyVeterinarianQuery:

    def test_columbus_keeps_its_exact_approved_deep_link(self):
        assert approved_home.emergency_maps_url("Columbus OH") == (
            "https://www.google.com/maps/search/?api=1"
            "&query=24+hour+emergency+veterinarian+Columbus+OH")

    @pytest.mark.parametrize("market_id,expected", [
        (DAYTON, "Dayton+OH"),
        (CLEVELAND, "Cleveland+OH"),
    ])
    def test_each_market_searches_its_own_city(self, market_id, expected):
        page = home_for(market_id)
        url = re.search(r"(https://www\.google\.com/maps/search/[^\"]*)", page).group(1)
        assert url.endswith("24+hour+emergency+veterinarian+" + expected)
        assert "Columbus" not in url


# --------------------------------------------------------------------------- #
# 7. A market registered tomorrow cannot inherit Columbus.
# --------------------------------------------------------------------------- #

FUTURE_MARKET = {
    "schema": "ptf-market/1.1",
    "market_id": "toledo-oh",
    "market_name": "Toledo",
    "market_slug": "toledo-oh",
    "state_name": "Ohio",
    "state_code": "OH",
    "primary_state_code": "OH",
    "states": ["OH"],
    "route_mode": "market_prefixed",
    "primary_city": "Toledo",
    "country_code": "US",
    "title": "Pet-Friendly Hotels in Toledo, Ohio | PetTripFinder",
    "meta_description": "Verified pet-friendly hotels across Toledo, Ohio.",
    "introductory_copy": "",
    "navigation_label": "Toledo",
    "show_in_navigation": False,
    "show_in_sitemap": False,
    "minimum_published_hotels": 5,
    "corridors": [],
}


class TestAFutureMarketCannotInheritColumbus:
    """A market registered with no ``homepage`` block at all still publishes
    its own identity."""

    @pytest.mark.parametrize("term", COLUMBUS_TERMS)
    def test_it_carries_no_columbus_copy(self, toledo_home, term):
        assert not re.search(r"\b%s\b" % term, toledo_home)

    def test_it_carries_its_own_identity(self, toledo_home):
        assert "<title>Pet-Friendly Travel in Toledo, Ohio | PetTripFinder</title>" in toledo_home
        assert "<em>Toledo</em>" in toledo_home
        assert "<h1>Find a Toledo trip<br>" in toledo_home
        assert "<b>Toledo, OH</b>" in toledo_home
        assert "veterinarian+Toledo+OH" in toledo_home
        assert "Verified pet-travel guide for Toledo, Ohio." in toledo_home

    def test_it_gets_the_neutral_hero_rather_than_someone_elses_city(self, toledo_home):
        assert 'class="hero-media hero-media--neutral" aria-hidden="true"' in toledo_home
        assert "<img" not in toledo_home.split('<div class="wrap hero-inner">')[0]

    def test_the_renderer_holds_no_market_shaped_literal(self):
        """The structural version of the same guarantee: after the docstrings
        and comments that EXPLAIN this defect are removed, no string the
        renderer emits names any market."""
        source = (REPO_ROOT / "scripts" / "pettripfinder" / "approved_home"
                  / "render.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        docstrings = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                                 ast.AsyncFunctionDef)):
                body = getattr(node, "body", None)
                if (body and isinstance(body[0], ast.Expr)
                        and isinstance(body[0].value, ast.Constant)
                        and isinstance(body[0].value.value, str)):
                    docstrings.add(id(body[0].value))
        offenders = []
        for node in ast.walk(tree):
            if (isinstance(node, ast.Constant) and isinstance(node.value, str)
                    and id(node) not in docstrings):
                for term in COLUMBUS_TERMS + ("Dayton", "Cleveland", "Akron", "Canton",
                                              "Toledo"):
                    if re.search(r"\b%s\b" % term, node.value):
                        offenders.append((node.lineno, term, node.value[:60]))
        assert not offenders, offenders


# --------------------------------------------------------------------------- #
# 8. The configuration contract fails closed.
# --------------------------------------------------------------------------- #

class TestHomepageConfigurationFailsClosed:

    def _doc(self, **homepage):
        doc = dict(FUTURE_MARKET)
        doc["homepage"] = homepage
        return doc

    def test_an_unknown_homepage_field_is_rejected(self):
        with pytest.raises(MarketContractError, match="unknown homepage field"):
            parse_market(self._doc(brand_labl="Toledo"), source="<test>")

    def test_a_documentation_key_is_allowed(self):
        market = parse_market(self._doc(_note="why this market overrides"), source="<test>")
        assert market.homepage.brand_label == "Toledo"

    def test_an_empty_required_field_is_rejected(self):
        with pytest.raises(MarketContractError, match="must be non-empty"):
            parse_market(self._doc(city_label="  "), source="<test>")

    def test_a_non_string_field_is_rejected(self):
        with pytest.raises(MarketContractError, match="must be a string"):
            parse_market(self._doc(city_label=7), source="<test>")

    def test_a_hero_photograph_without_alt_text_is_rejected(self):
        with pytest.raises(MarketContractError, match="must be set together"):
            parse_market(self._doc(hero_image="assets/hero-right.jpg"), source="<test>")

    def test_a_remote_hero_image_is_rejected(self):
        with pytest.raises(MarketContractError, match="approved asset directory"):
            parse_market(self._doc(hero_image="https://example.invalid/skyline.jpg",
                                   hero_image_alt="Someone else's city"), source="<test>")

    def test_a_hero_image_outside_the_asset_directory_is_rejected(self):
        with pytest.raises(MarketContractError, match="approved asset directory"):
            parse_market(self._doc(hero_image="../../secret.jpg",
                                   hero_image_alt="x"), source="<test>")

    def test_a_hero_asset_this_renderer_does_not_ship_fails_closed(self):
        market = parse_market(self._doc(hero_image="assets/toledo-hero.jpg",
                                        hero_image_alt="Toledo riverfront"),
                              source="<test>")
        with pytest.raises(HomepageAssetError, match="not an approved asset"):
            approved_home.resolve_homepage(market)

    def test_a_market_config_without_a_homepage_block_still_derives_one(self):
        market = parse_market(dict(FUTURE_MARKET), source="<test>")
        hp = homepage_config(market)
        assert hp.brand_label == "Toledo" and hp.market_label == "Toledo, Ohio"
        assert hp.hero_image == "" and hp.hero_image_alt == ""

    def test_the_state_is_not_repeated_when_the_name_already_carries_it(self):
        assert homepage_config(market_by_id(load_markets(), DAYTON)).market_label == (
            "Dayton & West Central Ohio")

    def test_curated_card_lists_must_be_lists_of_names(self):
        with pytest.raises(MarketContractError, match="must be a list"):
            parse_market(self._doc(featured_hotels="Riverside Inn"), source="<test>")

    def test_a_curated_name_absent_from_inventory_is_skipped_not_invented(self):
        """Curation selects; it never adds. A name the market does not
        publish leaves the deterministic fallback in charge."""
        from scripts.pettripfinder.approved_home.render import select_featured

        rows = _rows(*SYNTHETIC_NAMES)
        chosen = select_featured(rows, _facts(*SYNTHETIC_NAMES), 6,
                                 ("Airport Suites", "A Hotel That Does Not Exist"))
        names = [r["name"] for r in chosen]
        assert names[0] == "Airport Suites"
        assert "A Hotel That Does Not Exist" not in names
        assert sorted(names) == sorted(SYNTHETIC_NAMES)

    def test_columbus_curation_moved_into_configuration_intact(self):
        hp = homepage_config(market_by_id(load_markets(), COLUMBUS))
        assert len(hp.featured_hotels) == 6 and len(hp.glance_hotels) == 5
        assert hp.featured_hotels[0] == "Drury Inn & Suites Columbus Grove City"
        assert hp.glance_hotels[-1] == "Sonesta Columbus Downtown"

    def test_a_market_that_curates_nothing_still_renders_deterministically(self):
        market = parse_market(dict(FUTURE_MARKET), source="<test>")
        rows, facts = _rows(*SYNTHETIC_NAMES), _facts(*SYNTHETIC_NAMES)
        first = render_home(rows, facts, hotel_count=3, park_count=0,
                            restaurant_count=0, market=market, corridor_nav=[])
        second = render_home(list(reversed(rows)), facts, hotel_count=3, park_count=0,
                             restaurant_count=0, market=market, corridor_nav=[])
        assert first == second


# --------------------------------------------------------------------------- #
# 9. Structure: one homepage, one canonical, no duplicate routes.
# --------------------------------------------------------------------------- #

class _Structure(html.parser.HTMLParser):
    """Minimal structural audit: tag balance, headings, image alt text."""

    VOID = {"meta", "link", "img", "br", "input", "col", "hr", "source", "area"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.unbalanced = []
        self.h1 = 0
        self.images_without_alt = []
        self.canonicals = 0
        self.landmark_labels = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "h1":
            self.h1 += 1
        if tag == "img" and not (a.get("alt") or "").strip():
            self.images_without_alt.append(a.get("src"))
        if tag == "link" and a.get("rel") == "canonical":
            self.canonicals += 1
        if tag in ("nav", "aside") and (a.get("aria-label") or "").strip():
            self.landmark_labels += 1
        if tag not in self.VOID and not tag.startswith("!"):
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in self.VOID:
            return
        if not self.stack or self.stack[-1] != tag:
            self.unbalanced.append((tag, list(self.stack[-3:])))
            if tag in self.stack:
                while self.stack and self.stack.pop() != tag:
                    pass
            return
        self.stack.pop()


class TestStructureAndAccessibility:

    @pytest.mark.parametrize("market_id", [COLUMBUS, DAYTON, CLEVELAND])
    def test_the_markup_is_structurally_valid(self, market_id):
        page = home_for(market_id, published=("pet-friendly-hotels",)) \
            if market_id != COLUMBUS else home_for(
                market_id, published=("pet-friendly-hotels", "pet-friendly-parks",
                                      "pet-friendly-restaurants"))
        s = _Structure()
        s.feed(page)
        assert s.unbalanced == []
        assert s.stack == []
        assert s.h1 == 1                       # exactly one page heading
        assert s.canonicals == 1               # exactly one canonical
        assert s.images_without_alt == []      # every photograph is described
        assert s.landmark_labels >= 2          # nav + policy aside are labelled

    @pytest.mark.parametrize("market_id", [DAYTON, CLEVELAND])
    def test_the_neutral_hero_is_decorative_not_mislabelled(self, market_id):
        page = home_for(market_id)
        hero = page.split('<div class="wrap hero-inner">')[0]
        assert 'aria-hidden="true"' in hero
        assert "alt=" not in hero              # nothing to describe, nothing claimed

    @pytest.mark.parametrize("market_id", [COLUMBUS, DAYTON, CLEVELAND])
    def test_the_page_declares_a_language_and_a_mobile_viewport(self, market_id):
        page = home_for(market_id)
        assert '<html lang="en">' in page
        assert 'name="viewport" content="width=device-width, initial-scale=1"' in page

    @pytest.mark.parametrize("market_id", [DAYTON, CLEVELAND])
    def test_a_market_links_only_to_directories_it_builds(self, market_id):
        page = home_for(market_id, published=("pet-friendly-hotels",))
        assert "/pet-friendly-parks/" not in page
        assert "/pet-friendly-restaurants/" not in page
        assert "/pet-friendly-hotels/" in page

    @pytest.mark.parametrize("market_id", [COLUMBUS, DAYTON, CLEVELAND])
    def test_any_structured_data_names_only_the_selected_market(self, market_id):
        """The approved homepage carries no JSON-LD today. Asserting that
        explicitly means "metadata is market-aware" is a checked claim rather
        than an untested one, and the moment structured data IS added it has
        to pass the same market test as the visible copy."""
        page = home_for(market_id)
        blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>',
                            page, re.S)
        expected = homepage_config(market_by_id(load_markets(), market_id))
        for block in blocks:
            payload = json.dumps(json.loads(block))
            for term in COLUMBUS_TERMS:
                if re.search(r"\b%s\b" % term, payload):
                    assert term in expected.market_label or term in expected.city_label

    def test_no_market_creates_a_duplicate_route(self):
        """Registering these markets adds routes; it never collides them."""
        seen = {}
        for market in load_markets():
            table = market_route_table(market, assign_hotels(market, []), [])
            for route in table:
                assert route not in seen, (route, seen.get(route), market.market_id)
                seen[route] = market.market_id

    def test_every_market_publishes_exactly_one_homepage_at_the_site_root(self):
        """The homepage is a single global route. Making it market-aware must
        not have turned it into a second page or a second canonical."""
        for market_id in (COLUMBUS, DAYTON, CLEVELAND):
            page = home_for(market_id)
            assert page.count('rel="canonical"') == 1
            assert 'href="https://pettripfinder.com/"' in page


# --------------------------------------------------------------------------- #
# 10. The generated sites themselves, when a reviewer has built them.
# --------------------------------------------------------------------------- #

BUILD_DIRS = {
    DAYTON: REPO_ROOT / "data" / "site_builds" / "hma001_dayton-oh",
    CLEVELAND: REPO_ROOT / "data" / "site_builds" / "hma001_cleveland-akron-canton-oh",
}


@pytest.mark.parametrize("market_id", [DAYTON, CLEVELAND])
def test_a_generated_site_carries_no_columbus_label(market_id):
    """Belt and braces over the whole generated tree, skipped when the
    reviewer's build output is not present (it is gitignored)."""
    root = BUILD_DIRS[market_id]
    if not (root / "index.html").exists():
        pytest.skip("no local build for %s" % market_id)
    offenders = []
    for path in root.rglob("*.html"):
        text = path.read_text(encoding="utf-8")
        for term in COLUMBUS_TERMS:
            if re.search(r"\b%s\b" % term, text):
                offenders.append((str(path.relative_to(root)), term))
    assert offenders == []


def test_the_market_configs_on_disk_all_parse_with_a_homepage_identity():
    for market in load_markets():
        hp = homepage_config(market)
        assert hp.title and hp.brand_label and hp.market_label and hp.city_label
        assert hp.search_location and hp.vet_query_location and hp.meta_description
        assert bool(hp.hero_image) == bool(hp.hero_image_alt)


def test_the_columbus_config_records_its_approved_overrides():
    doc = json.loads((REPO_ROOT / "launch_packages" / "pettripfinder" / "markets"
                      / "columbus-oh.json").read_text(encoding="utf-8"))
    assert doc["homepage"]["hero_image"] == "assets/hero-right.jpg"
    assert "Scioto" in doc["homepage"]["hero_image_alt"]
