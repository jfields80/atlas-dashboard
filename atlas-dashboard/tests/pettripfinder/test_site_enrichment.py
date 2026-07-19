"""AES-SITE-001 -- site enrichment transform tests. Synthetic fixture HTML
matches the REAL pipeline's exact output shape (captured from a live probe
build before this module was written); no network."""

from __future__ import annotations

import json
import re

import pytest

from scripts.pettripfinder.site_enrichment import (
    EnrichmentError,
    build_go_pages_for_listing,
    enrich_hotel_profile,
    enrich_place_profile,
    inject_breadcrumbs_after_header,
    inject_head,
    render_no_pets_badge,
    render_policy_fact_table,
    render_unverified_notice,
    render_verified_badge,
    replace_related_list_with_enrichment,
    rewrite_cta_link,
)

_FIXTURE_HTML = (
    '<!doctype html><html lang="en"><head><meta charset="utf-8">'
    "<title>Example Hotel | PetTripFinder</title></head>"
    '<body><header><nav aria-label="Main"><ul><li><a href="/">PetTripFinder</a></li></ul></nav></header>'
    '<section class="ac-profile ac-profile--header-business ac-profile--standard" '
    'data-atlas-c="profile-header-business"><h1>Example Hotel</h1></section>'
    '<main id="main"><aside class="ac-profile ac-profile--contact-panel ac-profile--sidebar" '
    'data-atlas-c="profile-contact-panel" data-atlas-e="phone_click">'
    "<address><p>1 A St, Columbus, OH, 43215</p><p><a href=\"tel:6145550100\">614-555-0100</a></p>"
    '<p><a class="ac-cta ac-cta--action" href="https://example-hotel.test/" rel="noopener">Visit website</a></p>'
    "</address></aside>"
    '<section class="ac-content ac-content--description-business" data-atlas-c="content-description-business">'
    "<p>Pet policy: Dogs are accepted.</p></section>"
    '<article class="ac-listing ac-listing--card-standard"><h2><a href="/pet-friendly-hotels/other/">Other</a></h2></article>'
    "</main><footer><p>(c) 2026 PetTripFinder.</p></footer></body></html>"
)


def test_inject_head_before_close():
    out = inject_head(_FIXTURE_HTML, "<script>1</script>")
    assert "<script>1</script></head>" in out


def test_inject_head_missing_anchor_raises():
    with pytest.raises(EnrichmentError):
        inject_head("<html><body></body></html>", "<script></script>")


def test_inject_breadcrumbs_after_header():
    out = inject_breadcrumbs_after_header(_FIXTURE_HTML, "<nav>BC</nav>")
    assert '</section><nav>BC</nav><main id="main">' in out


def test_rewrite_cta_preserves_label_adds_tracking():
    out = rewrite_cta_link(_FIXTURE_HTML, go_href="/go/example-hotel/official-website/")
    assert 'href="/go/example-hotel/official-website/"' in out
    assert "https://example-hotel.test/" not in out
    assert "Visit website</a>" in out
    assert 'data-atlas-e="outbound_official_click"' in out


def test_rewrite_cta_missing_anchor_raises():
    with pytest.raises(EnrichmentError):
        rewrite_cta_link("<html><body>no cta</body></html>", go_href="/go/x/official-website/")


def test_replace_related_list_preserves_prefix_and_suffix():
    out = replace_related_list_with_enrichment(_FIXTURE_HTML, "<div>NEW CONTENT</div>")
    assert "<div>NEW CONTENT</div>" in out
    assert "Other</a>" not in out    # the old related-listing dump is gone
    assert "<h1>Example Hotel</h1>" in out
    assert "</main><footer>" in out  # tail preserved


def test_policy_fact_table_shows_unknown_for_missing_fields():
    table = render_policy_fact_table({"pet_fee": "$50"})
    assert "$50" in table
    assert table.count("Not stated by the official source") == len(
        [k for k, _ in [("species_allowed", ""), ("fee_basis", ""), ("pet_count_limit", ""),
                         ("weight_limit", ""), ("breed_restrictions", ""),
                         ("unattended_policy", ""), ("general_restrictions", "")]])


def test_policy_fact_table_never_fabricates_a_value():
    table = render_policy_fact_table({})
    assert "Not stated by the official source" in table
    # every field is the honest fallback -- no field silently becomes "" or "unknown"
    assert table.count("Not stated by the official source") == 8


def test_verified_badge_shows_date_and_count():
    badge = render_verified_badge("2026-07-18", 12)
    assert "2026-07-18" in badge and "12 evidenced field" in badge


def test_no_pets_badge_mentions_service_animals_distinctly():
    badge = render_no_pets_badge("2026-07-18")
    assert "not" in badge.lower()
    assert "service animal" in badge.lower()


def test_unverified_notice_is_neutral_not_negative():
    notice = render_unverified_notice()
    assert "not independently verified" in notice
    assert "no pets" not in notice.lower()


def test_html_escaping_in_injected_content():
    out = rewrite_cta_link(
        _FIXTURE_HTML.replace("https://example-hotel.test/", "https://example-hotel.test/?a=1&b=2"),
        go_href="/go/x/official-website/")
    assert "/go/x/official-website/" in out


# --------------------------------------------------------------------------- #
# Full profile enrichment (integration of the transforms above).
# --------------------------------------------------------------------------- #

_ROW = {"name": "Example Hotel", "address": "1 A St", "city": "Columbus",
        "state": "OH", "postal_code": "43215", "website_url": "https://example-hotel.test/",
        "phone": "614-555-0100", "category": "pet-friendly-hotels"}
_ALL_ROWS = [
    _ROW,
    {"name": "Example Park", "address": "", "city": "Columbus", "state": "OH",
     "postal_code": "", "website_url": "https://park.test/", "category": "pet-friendly-parks"},
]


def test_enrich_hotel_profile_with_verified_facts():
    facts_entry = {
        "facts": {"pets_allowed": "true", "species_allowed": "dogs and cats", "pet_fee": "$50"},
        "verified_at": "2026-07-18", "evidence_count": 5,
    }
    out = enrich_hotel_profile(
        html_text=_FIXTURE_HTML, row=_ROW, listing_id="example-hotel", corridor="",
        facts_entry=facts_entry, all_rows=_ALL_ROWS)
    assert "Policy verified" in out
    assert "$50" in out
    assert '"@type": "LodgingBusiness"' in out or '"@type":"LodgingBusiness"' in out
    assert "/go/example-hotel/official-website/" in out
    assert "Example Park" in out   # nearby section
    assert "/go/example-hotel/report-change/" in out


def test_enrich_hotel_profile_no_pets_shows_no_pets_badge_not_table():
    facts_entry = {"facts": {"pets_allowed": "false"}, "verified_at": "2026-07-18", "evidence_count": 2}
    out = enrich_hotel_profile(
        html_text=_FIXTURE_HTML, row=_ROW, listing_id="example-hotel", corridor="",
        facts_entry=facts_entry, all_rows=_ALL_ROWS)
    assert "not</strong> accepted" in out
    assert "ptf-policy-table" not in out


def test_enrich_hotel_profile_without_facts_shows_unverified_notice():
    out = enrich_hotel_profile(
        html_text=_FIXTURE_HTML, row=_ROW, listing_id="example-hotel", corridor="",
        facts_entry=None, all_rows=_ALL_ROWS)
    assert "not independently verified" in out
    assert "ptf-policy-table" not in out


def test_enrich_hotel_profile_json_ld_omits_pets_allowed_when_unverified():
    out = enrich_hotel_profile(
        html_text=_FIXTURE_HTML, row=_ROW, listing_id="example-hotel", corridor="",
        facts_entry=None, all_rows=_ALL_ROWS)
    m = re.search(r'<script type="application/ld\+json">(.*?)</script>', out)
    payloads = re.findall(r'<script type="application/ld\+json">(.*?)</script>', out)
    found_lodging = False
    for p in payloads:
        obj = json.loads(p.replace("<\\/", "</"))
        if obj.get("@type") == "LodgingBusiness":
            found_lodging = True
            assert "petsAllowed" not in obj
    assert found_lodging


def test_enrich_place_profile_park():
    park_row = _ALL_ROWS[1]
    out = enrich_place_profile(
        html_text=_FIXTURE_HTML.replace("Example Hotel", "Example Park"),
        row=park_row, listing_id="example-park", category_slug="pet-friendly-parks",
        place_type="Park", all_rows=_ALL_ROWS)
    payloads = re.findall(r'<script type="application/ld\+json">(.*?)</script>', out)
    types = [json.loads(p.replace("<\\/", "</")).get("@type") for p in payloads]
    assert "Park" in types
    assert "Example Hotel" in out   # nearby hotels


# --------------------------------------------------------------------------- #
# /go/ page generation per listing.
# --------------------------------------------------------------------------- #

def test_build_go_pages_for_listing_includes_expected_actions():
    pages = build_go_pages_for_listing(
        listing_id="example-hotel", name="Example Hotel", official_url="https://example-hotel.test/",
        phone="614-555-0100", address="1 A St", city="Columbus", state="OH",
        category_slug="pet-friendly-hotels", corridor="", verification_status="VERIFIED_PET_FRIENDLY")
    routes = list(pages.keys())
    assert "/go/example-hotel/official-website/index.html" in routes
    assert "/go/example-hotel/directions/index.html" in routes
    assert "/go/example-hotel/call/index.html" in routes
    assert "/go/example-hotel/report-change/index.html" in routes


def test_build_go_pages_skips_call_without_phone():
    pages = build_go_pages_for_listing(
        listing_id="x", name="X", official_url="https://x.test/", phone="",
        address="1 A St", city="Columbus", state="OH", category_slug="pet-friendly-hotels",
        corridor="", verification_status="VERIFIED_PET_FRIENDLY")
    assert "/go/x/call/index.html" not in pages


def test_build_go_pages_skips_directions_without_address():
    pages = build_go_pages_for_listing(
        listing_id="x", name="X", official_url="https://x.test/", phone="614-555-0100",
        address="", city="", state="", category_slug="pet-friendly-hotels",
        corridor="", verification_status="VERIFIED_PET_FRIENDLY")
    assert "/go/x/directions/index.html" not in pages


def test_directions_url_built_from_approved_address_only():
    pages = build_go_pages_for_listing(
        listing_id="x", name="X", official_url="https://x.test/", phone="",
        address="1 A St", city="Columbus", state="OH", category_slug="pet-friendly-hotels",
        corridor="", verification_status="VERIFIED_PET_FRIENDLY")
    directions_html = pages["/go/x/directions/index.html"]
    assert "google.com/maps/search" in directions_html
    assert "1+A+St" in directions_html or "1%20A%20St" in directions_html


# --------------------------------------------------------------------------- #
# Category page / hub page enrichment.
# --------------------------------------------------------------------------- #

_CATEGORY_FIXTURE = (
    '<!doctype html><html lang="en"><head><meta charset="utf-8">'
    "<title>Pet-Friendly Hotels | PetTripFinder</title></head>"
    '<body><header></header><section class="ac-hero"><h1>Pet-Friendly Hotels</h1></section>'
    '<main id="main"><div class="ac-directory ac-directory--results-summary" '
    'data-atlas-c="directory-results-summary" data-atlas-v="1.0.0">Showing 2 listings</div>'
    '<article class="ac-listing ac-listing--card-standard ac-listing--standard" '
    'data-atlas-c="listing-card-standard" data-atlas-e="listing_click" data-atlas-v="1.0.0">'
    '<h2><a href="/pet-friendly-hotels/a-hotel/">A Hotel</a></h2>'
    '<p class="ac-listing ac-listing--area">Columbus, OH</p></article>'
    '<article class="ac-listing ac-listing--card-standard ac-listing--standard" '
    'data-atlas-c="listing-card-standard" data-atlas-e="listing_click" data-atlas-v="1.0.0">'
    '<h2><a href="/pet-friendly-hotels/b-hotel/">B Hotel</a></h2>'
    '<p class="ac-listing ac-listing--area">Dublin, OH</p></article>'
    "</main><footer></footer></body></html>"
)


def test_enrich_hotel_category_page_adds_toolbar_and_corridor_tags():
    from scripts.pettripfinder.site_enrichment import enrich_hotel_category_page
    out = enrich_hotel_category_page(
        _CATEGORY_FIXTURE, ["Downtown Columbus", "Dublin"],
        {"/pet-friendly-hotels/b-hotel/": "Dublin"})
    assert "policy-comparison" in out
    assert 'data-ptf-corridor="Dublin"' in out
    assert "A Hotel</a>" in out and "B Hotel</a>" in out  # base HTML unaffected
    assert "<script>" in out


def test_enrich_hotel_category_page_missing_anchor_raises():
    from scripts.pettripfinder.site_enrichment import EnrichmentError, enrich_hotel_category_page
    with pytest.raises(EnrichmentError):
        enrich_hotel_category_page("<html><body>no anchor</body></html>", [], {})


_HUB_FIXTURE = (
    '<!doctype html><html><head></head><body><header></header>'
    '<section class="ac-hero"><h1>Travel anywhere with your pet</h1></section>'
    '<main id="main"><section class="ac-directory"><ul><li><a href="/pet-friendly-hotels/">Hotels</a></li></ul></section></main>'
    "<footer></footer></body></html>"
)


def test_enrich_hub_page_inserts_intro():
    from scripts.pettripfinder.site_enrichment import enrich_hub_page, render_hub_intro
    intro = render_hub_intro(hotel_count=25, park_count=14, restaurant_count=13,
                             latest_verified_date="2026-07-18")
    out = enrich_hub_page(_HUB_FIXTURE, intro)
    assert "25 evidence-backed" in out
    assert "2026-07-18" in out
    assert '<main id="main">' in out


def test_render_hub_intro_no_fabricated_claims():
    from scripts.pettripfinder.site_enrichment import render_hub_intro
    intro = render_hub_intro(hotel_count=25, park_count=14, restaurant_count=13,
                             latest_verified_date="2026-07-18")
    for banned in ("best", "top-rated", "guaranteed", "#1"):
        assert banned not in intro.lower()
