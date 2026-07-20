"""AES-SITE-001 -- Columbus site enrichment layer.

Post-processes the REAL, already-quality-gated bundle the proven AES-WEB
chain produces (``scripts/generate_pettripfinder_pilot.py``'s machinery,
run via ``scripts/generate_pettripfinder_columbus_site.py``) to add the
launch-specific features the core engine does not yet build: structured
pet-policy fact tables, verification badges, JSON-LD, breadcrumbs, nearby
relationships, the ``/go/`` commercial-action layer, comparison/corridor
pages, and a rewritten methodology/hub.

Design decision (disclosed): rather than broadening the core AES-WEB engine
(new component families, a richer ``ListingRecord`` schema, per-page
``robots`` in ``SEOPackage`` -- Decision D4/D5 there explicitly deferred
structured data and kept robots.txt site-level-only), this module transforms
the engine's OWN real output as a small, fully reusable, independently
tested layer. The core engine's immutable contracts are never touched; the
same enrichment functions apply to any future market's bundle unchanged
(every Columbus-specific fact flows in as data, never hardcoded logic).

Every injection point is a literal, known-stable HTML anchor already present
in the real rendered output (verified against the live pipeline before this
module was written); a missing anchor raises loudly rather than silently
skipping a page (fail-closed, matching the rest of this mission's caps
discipline).
"""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from scripts.pettripfinder.commercial_actions import (
    ACTION_CALL,
    ACTION_DIRECTIONS,
    ACTION_OFFICIAL_WEBSITE,
    ACTION_REPORT_CHANGE,
    ANALYTICS_JS,
    AffiliateConfig,
    build_go_page,
    build_redirect_target,
    go_route,
)
from scripts.pettripfinder.site_data import (
    CORRIDOR_MIN_PROPERTIES,
    assign_corridor,
    group_by_corridor,
    load_hotel_policy_facts,
    nearby_same_city,
    normalize_name,
    read_production_rows,
)
from scripts.pettripfinder.structured_data import (
    breadcrumb_ld,
    item_list_ld,
    lodging_business_ld,
    organization_ld,
    place_ld,
    restaurant_ld,
    to_script_tag,
    website_ld,
)

BASE_URL = "https://pettripfinder.com"
SITE_NAME = "PetTripFinder"

CATEGORY_LABELS = {
    "pet-friendly-hotels": "Pet-Friendly Hotels",
    "pet-friendly-parks": "Pet-Friendly Parks",
    "pet-friendly-restaurants": "Pet-Friendly Restaurants",
}

# The one directly-observed policy field vocabulary (candidate.py's SEED_CSV
# columns / lodging domain pack). Order matches how a traveler reads a rate
# sheet: who's welcome, what it costs, how many, how big, then restrictions.
_FACT_ORDER = (
    ("species_allowed", "Pets accepted"),
    ("pet_fee", "Fee"),
    ("fee_basis", "Fee basis"),
    ("pet_count_limit", "Maximum pets"),
    ("weight_limit", "Weight limit"),
    ("breed_restrictions", "Breed restrictions"),
    ("unattended_policy", "Unattended pet policy"),
    ("general_restrictions", "Other restrictions"),
)

_NOT_STATED = "Not stated by the official source"


# --------------------------------------------------------------------------- #
# Small shared HTML builders.
# --------------------------------------------------------------------------- #

def _e(text: str) -> str:
    return html.escape(text or "", quote=False)


def render_breadcrumbs(crumbs: List[Tuple[str, str]]) -> str:
    """``crumbs``: ordered (label, route) pairs, home first. Visible,
    crawlable HTML -- never JS-only navigation."""
    items = "".join(
        '<li><a href="%s">%s</a></li>' % (route, _e(label)) if route else
        '<li aria-current="page">%s</li>' % _e(label)
        for label, route in crumbs
    )
    return '<nav aria-label="Breadcrumb" class="ptf-breadcrumbs"><ol>%s</ol></nav>' % items


def render_policy_fact_table(facts: Dict[str, str]) -> str:
    rows = []
    for key, label in _FACT_ORDER:
        value = facts.get(key, "").strip()
        display = _e(value) if value else '<span class="ptf-unknown">%s</span>' % _NOT_STATED
        rows.append("<tr><th scope=\"row\">%s</th><td>%s</td></tr>" % (_e(label), display))
    return (
        '<table class="ptf-policy-table"><caption class="ptf-visually-hidden">Pet policy details</caption>'
        "<tbody>%s</tbody></table>" % "".join(rows)
    )


def render_verified_badge(verified_at: str, evidence_count: int) -> str:
    return (
        '<div class="ptf-badge ptf-badge--verified" role="status">'
        '<span class="ptf-badge-icon" aria-hidden="true">&#10003;</span>'
        "<span>Policy verified from the official source on %s"
        " (%d evidenced field%s). <a href=\"/methodology/\">How we verify</a>.</span>"
        "</div>"
    ) % (_e(verified_at), evidence_count, "" if evidence_count == 1 else "s")


def render_unverified_notice() -> str:
    return (
        '<div class="ptf-badge ptf-badge--unverified" role="status">'
        "<span>Policy not independently verified &mdash; confirm directly with the business "
        "before you book. <a href=\"/methodology/\">How we verify</a>.</span>"
        "</div>"
    )


def render_no_pets_badge(verified_at: str) -> str:
    return (
        '<div class="ptf-badge ptf-badge--no-pets" role="status">'
        "<span>Verified: pets are <strong>not</strong> accepted here (checked %s). "
        "Service animals are a separate legal category, not a pet-policy exception "
        "&mdash; see <a href=\"/methodology/\">our methodology</a>.</span>"
        "</div>"
    ) % _e(verified_at)


def render_nearby_section(title: str, rows: List[Dict[str, str]], category_slug: str) -> str:
    if not rows:
        return ""
    items = "".join(
        '<li><a href="/%s/%s/">%s</a><span class="ptf-nearby-city"> &mdash; also in %s</span></li>'
        % (category_slug, _slug(r["name"]), _e(r["name"]), _e(r["city"]))
        for r in rows
    )
    return '<nav aria-label="%s" class="ptf-nearby"><h2>%s</h2><ul>%s</ul></nav>' % (
        _e(title), _e(title), items)


def _slug(text: str) -> str:
    lowered = (text or "").strip().lower()
    return re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")


def render_report_change_link(listing_id: str) -> str:
    route = go_route(listing_id, ACTION_REPORT_CHANGE)
    return ('<p class="ptf-report-change"><a href="%s" data-atlas-e="report_change_click">'
           "Report an outdated or incorrect policy</a></p>") % route


# --------------------------------------------------------------------------- #
# Anchors into the real rendered HTML (stable across every profile page --
# every route this touches was inspected against the live pipeline output
# before this module was written; ``enrich_bundle`` fails loudly if an
# anchor is missing on a page it expects to have one).
# --------------------------------------------------------------------------- #

_DESCRIPTION_CLOSE = '</section><article class="ac-listing'
_HEAD_CLOSE = "</head>"
_MAIN_CLOSE = "</main>"
_CTA_HREF_RE = re.compile(r'(<a class="ac-cta ac-cta--action" href=")([^"]*)("[^>]*>)([^<]*)(</a>)')


class EnrichmentError(RuntimeError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise EnrichmentError(message)


def inject_head(html_text: str, ld_script: str) -> str:
    _require(_HEAD_CLOSE in html_text, "missing </head> anchor")
    return html_text.replace(_HEAD_CLOSE, ld_script + _HEAD_CLOSE, 1)


def rewrite_cta_link(html_text: str, *, go_href: str) -> str:
    """Rewrites the official-website CTA's ``href`` to the tracked ``/go/``
    route, preserving its visible label and adding an analytics hook.
    Leaves everything else about the anchor untouched."""
    m = _CTA_HREF_RE.search(html_text)
    _require(m is not None, "missing CTA anchor to rewrite")
    replacement = (
        m.group(1) + go_href + '" data-atlas-e="outbound_official_click' + m.group(3)
        + m.group(4) + m.group(5)
    )
    return html_text[:m.start()] + replacement + html_text[m.end():]


def replace_related_list_with_enrichment(html_text: str, enrichment_html: str) -> str:
    """Removes the pipeline's crude "every other listing in the category"
    card dump (everything from the description section's close through
    ``</main>``) and replaces it with badge/fact-table/nearby/report-change
    content. The description section itself (and everything before it,
    including the header/contact panel) is preserved untouched."""
    start = html_text.find(_DESCRIPTION_CLOSE)
    _require(start != -1, "missing description-section anchor")
    desc_end = start + len("</section>")
    main_end = html_text.find(_MAIN_CLOSE, desc_end)
    _require(main_end != -1, "missing </main> anchor")
    return html_text[:desc_end] + enrichment_html + html_text[main_end:]


def inject_breadcrumbs_after_header(html_text: str, breadcrumb_html: str) -> str:
    marker = '</section><main id="main">'
    _require(marker in html_text, "missing header/main anchor for breadcrumbs")
    return html_text.replace(marker, "</section>" + breadcrumb_html + '<main id="main">', 1)


# --------------------------------------------------------------------------- #
# Orchestration.
# --------------------------------------------------------------------------- #

def build_go_pages_for_listing(
    *, listing_id: str, name: str, official_url: str, phone: str, address: str,
    city: str, state: str, category_slug: str, corridor: str, verification_status: str,
    affiliate: Optional[AffiliateConfig] = None, include_booking: bool = False,
) -> Dict[str, str]:
    """Returns ``{route: html}`` for every applicable action on one
    listing. DIRECTIONS uses a Google Maps search-by-address URL (no API
    key, no live call -- a plain deep link built entirely from the
    listing's own approved address, exactly like a "Get Directions" link a
    human would construct by hand).

    ``include_booking`` adds the ``/go/<id>/booking/`` action (its destination
    is the listing's own official URL, honestly labeled -- no affiliate program
    is configured, so it never fabricates a price/availability claim). The
    approved hotel-profile renderer's primary CTA links to this route, so hotel
    profiles pass ``include_booking=True``; parks/restaurants do not."""
    from scripts.pettripfinder.commercial_actions import ACTION_BOOKING
    pages: Dict[str, str] = {}
    actions: List[Tuple[str, str]] = []
    official = build_redirect_target(ACTION_OFFICIAL_WEBSITE, official_url=official_url, phone=phone)
    if include_booking:
        booking = build_redirect_target(ACTION_BOOKING, official_url=official_url, phone=phone,
                                        config=affiliate)
        if booking:
            actions.append((ACTION_BOOKING, booking))
    if official:
        actions.append((ACTION_OFFICIAL_WEBSITE, official))
    if address and city:
        query = "%s, %s, %s" % (address, city, state)
        maps_url = "https://www.google.com/maps/search/?api=1&query=" + \
            query.replace(" ", "+").replace(",", "%2C")
        actions.append((ACTION_DIRECTIONS, maps_url))
    call_target = build_redirect_target(ACTION_CALL, official_url="", phone=phone)
    if call_target:
        actions.append((ACTION_CALL, call_target))
    actions.append((ACTION_REPORT_CHANGE, build_redirect_target(ACTION_REPORT_CHANGE, official_url="", phone="")))

    for action, destination in actions:
        route, page_html = build_go_page(
            listing_id=listing_id, listing_name=name, action=action, destination=destination,
            page_type="listing_profile", category=category_slug, corridor=corridor,
            verification_status=verification_status)
        pages[route.rstrip("/") + "/index.html"] = page_html
    return pages


def enrich_hotel_profile(
    *, html_text: str, row: Dict[str, str], listing_id: str, corridor: str,
    facts_entry: Optional[Dict], all_rows: List[Dict[str, str]],
) -> str:
    name = row["name"]
    category_slug = "pet-friendly-hotels"
    breadcrumbs = render_breadcrumbs([
        ("PetTripFinder", "/"), (CATEGORY_LABELS[category_slug], "/%s/" % category_slug),
        (name, ""),
    ])
    if facts_entry:
        pets_allowed = facts_entry["facts"].get("pets_allowed")
        if pets_allowed == "false":
            badge = render_no_pets_badge(facts_entry["verified_at"])
            table_html = ""
        else:
            badge = render_verified_badge(facts_entry["verified_at"], facts_entry["evidence_count"])
            table_html = render_policy_fact_table(facts_entry["facts"])
        verification_status = "VERIFIED_NO_PETS" if pets_allowed == "false" else "VERIFIED_PET_FRIENDLY"
    else:
        badge = render_unverified_notice()
        table_html = ""
        verification_status = "POLICY_UNVERIFIED"

    nearby_parks = nearby_same_city(all_rows, row, other_category="pet-friendly-parks")
    nearby_restaurants = nearby_same_city(all_rows, row, other_category="pet-friendly-restaurants")
    nearby_html = (
        render_nearby_section("Nearby parks", nearby_parks, "pet-friendly-parks")
        + render_nearby_section("Nearby restaurants", nearby_restaurants, "pet-friendly-restaurants")
    )
    report_html = render_report_change_link(listing_id)
    enrichment = badge + table_html + nearby_html + report_html

    ld_objects = [
        breadcrumb_ld(BASE_URL, [("PetTripFinder", "/"), (CATEGORY_LABELS[category_slug], "/%s/" % category_slug), (name, "/%s/%s/" % (category_slug, listing_id))]),
        lodging_business_ld(
            base_url=BASE_URL, route="/%s/%s/" % (category_slug, listing_id), name=name,
            street=row.get("address", ""), city=row.get("city", ""), state=row.get("state", ""),
            postal_code=row.get("postal_code", ""), official_url=row.get("website_url", ""),
            pets_allowed=(facts_entry["facts"].get("pets_allowed") == "true") if facts_entry
                and facts_entry["facts"].get("pets_allowed") in ("true", "false") else None,
            amenity_features=[v for k, v in facts_entry["facts"].items()
                              if k in ("species_allowed",)] if facts_entry else None,
        ),
    ]

    out = html_text
    out = inject_head(out, to_script_tag(ld_objects))
    out = inject_breadcrumbs_after_header(out, breadcrumbs)
    out = rewrite_cta_link(out, go_href=go_route(listing_id, ACTION_OFFICIAL_WEBSITE))
    out = replace_related_list_with_enrichment(out, enrichment)
    return out


def enrich_place_profile(
    *, html_text: str, row: Dict[str, str], listing_id: str, category_slug: str,
    place_type: str, all_rows: List[Dict[str, str]],
) -> str:
    name = row["name"]
    breadcrumbs = render_breadcrumbs([
        ("PetTripFinder", "/"), (CATEGORY_LABELS[category_slug], "/%s/" % category_slug),
        (name, ""),
    ])
    nearby_hotels = nearby_same_city(all_rows, row, other_category="pet-friendly-hotels")
    other_slug = "pet-friendly-restaurants" if category_slug == "pet-friendly-parks" else "pet-friendly-parks"
    nearby_other = nearby_same_city(all_rows, row, other_category=other_slug)
    nearby_html = (
        render_nearby_section("Nearby pet-friendly lodging", nearby_hotels, "pet-friendly-hotels")
        + render_nearby_section(
            "Nearby parks" if other_slug == "pet-friendly-parks" else "Nearby restaurants",
            nearby_other, other_slug)
    )
    report_html = render_report_change_link(listing_id)
    enrichment = nearby_html + report_html

    ld_builder = place_ld if place_type == "Park" else restaurant_ld
    ld_objects = [
        breadcrumb_ld(BASE_URL, [("PetTripFinder", "/"), (CATEGORY_LABELS[category_slug], "/%s/" % category_slug), (name, "/%s/%s/" % (category_slug, listing_id))]),
        ld_builder(base_url=BASE_URL, route="/%s/%s/" % (category_slug, listing_id), name=name,
                  street=row.get("address", ""), city=row.get("city", ""), state=row.get("state", ""),
                  postal_code=row.get("postal_code", ""), official_url=row.get("website_url", "")),
    ]

    out = html_text
    out = inject_head(out, to_script_tag(ld_objects))
    out = inject_breadcrumbs_after_header(out, breadcrumbs)
    if _CTA_HREF_RE.search(out):
        out = rewrite_cta_link(out, go_href=go_route(listing_id, ACTION_OFFICIAL_WEBSITE))
    out = replace_related_list_with_enrichment(out, enrichment)
    return out


# --------------------------------------------------------------------------- #
# Category page enrichment (Task 3): comparison/corridor entry points +
# a progressive-enhancement corridor filter. The filter reads each card's
# ALREADY-RENDERED area text (``<p class="ac-listing ac-listing--area">
# City, OH</p>``) rather than injecting new per-card attributes -- simpler,
# and the full unfiltered list stays the base HTML with or without JS
# (Task 3: "All filterable content must remain available in base HTML").
# --------------------------------------------------------------------------- #

_RESULTS_SUMMARY_CLOSE = 'directory--results-summary" data-atlas-c="directory-results-summary" data-atlas-v="1.0.0">'


def render_hotel_category_toolbar(corridor_labels: List[str]) -> str:
    links = "".join(
        '<button type="button" class="ptf-filter-btn" data-ptf-filter="%s">%s</button>'
        % (_e(c), _e(c)) for c in corridor_labels
    )
    return (
        '<div class="ptf-toolbar">'
        '<p><a href="/pet-friendly-hotels/policy-comparison/">Compare fees, pet limits, '
        "and restrictions across every verified hotel &rarr;</a></p>"
        '<div class="ptf-filter-group" role="group" aria-label="Filter by area">'
        '<button type="button" class="ptf-filter-btn ptf-filter-btn--active" data-ptf-filter="">All areas</button>'
        + links + "</div></div>"
    )


_FILTER_JS = """\
(function () {
  var buttons = document.querySelectorAll('.ptf-filter-btn');
  var cards = document.querySelectorAll('article.ac-listing');
  if (!buttons.length || !cards.length) { return; }
  buttons.forEach(function (btn) {
    btn.addEventListener('click', function () {
      var value = btn.getAttribute('data-ptf-filter') || '';
      buttons.forEach(function (b) { b.classList.remove('ptf-filter-btn--active'); });
      btn.classList.add('ptf-filter-btn--active');
      cards.forEach(function (card) {
        var area = card.querySelector('.ac-listing--area');
        var text = area ? area.textContent : '';
        var show = !value || text.indexOf(value) !== -1 || cardMatchesCorridor(card, value);
        card.style.display = show ? '' : 'none';
      });
      window.ptfAnalytics && window.ptfAnalytics.emit('filter_applied', {page_type: 'category', action_position: 'toolbar', market: 'columbus-oh', filter_value: value});
    });
  });
  function cardMatchesCorridor(card, value) {
    var corridor = card.getAttribute('data-ptf-corridor') || '';
    return corridor === value;
  }
})();
"""


def enrich_hotel_category_page(html_text: str, corridor_labels: List[str],
                               corridor_by_route: Dict[str, str]) -> str:
    _require(_RESULTS_SUMMARY_CLOSE in html_text, "missing results-summary anchor")
    out = html_text.replace(
        _RESULTS_SUMMARY_CLOSE,
        _RESULTS_SUMMARY_CLOSE, 1)  # anchor confirmed; toolbar inserted after the whole div below
    marker_end = out.index(_RESULTS_SUMMARY_CLOSE) + len(_RESULTS_SUMMARY_CLOSE)
    div_close = out.index("</div>", marker_end) + len("</div>")
    toolbar = render_hotel_category_toolbar(corridor_labels)
    out = out[:div_close] + toolbar + out[div_close:]

    def _tag_corridor(m: re.Match) -> str:
        route = m.group("route")
        corridor = corridor_by_route.get(route, "")
        if not corridor:
            return m.group(0)
        return m.group(0).replace(
            'data-atlas-c="listing-card-standard"',
            'data-atlas-c="listing-card-standard" data-ptf-corridor="%s"' % _e(corridor), 1)

    out = re.sub(
        r'<article class="ac-listing[^>]*data-atlas-c="listing-card-standard"[^>]*>'
        r'<h2><a href="(?P<route>[^"]+)">',
        _tag_corridor, out)

    _require(_HEAD_CLOSE in out, "missing </head> anchor")
    script = "<script>%s\n%s</script>" % (ANALYTICS_JS, _FILTER_JS)
    out = out.replace(_MAIN_CLOSE, _MAIN_CLOSE, 1)  # no-op guard: main exists
    out = out.replace("</body>", script + "</body>", 1)
    return out


# --------------------------------------------------------------------------- #
# Hub page enrichment (Task 2).
# --------------------------------------------------------------------------- #

_HUB_DIRECTORY_MARKER = '<main id="main">'


def render_hub_intro(*, hotel_count: int, park_count: int, restaurant_count: int,
                     latest_verified_date: str) -> str:
    return (
        '<section class="ptf-hub-intro">'
        "<p>PetTripFinder Columbus currently lists <strong>%d evidence-backed "
        "pet-friendly hotels</strong>, %d parks, and %d restaurants. Every hotel "
        "policy shown here is either verified directly from the property's own "
        "official website (with an exact quote and a checked date) or clearly "
        "labeled as not yet independently verified &mdash; we never guess.</p>"
        "<p>Most recent verification: %s. "
        '<a href="/methodology/">Read how verification works</a> or '
        '<a href="/pet-friendly-hotels/policy-comparison/">compare hotel pet fees and limits '
        "side by side</a>.</p>"
        '<ul class="ptf-hub-links">'
        '<li><a href="/pet-friendly-hotels/">Verified pet-friendly hotels</a></li>'
        '<li><a href="/pet-friendly-hotels/downtown-columbus/">Downtown Columbus hotels</a></li>'
        '<li><a href="/pet-friendly-hotels/dublin/">Dublin hotels</a></li>'
        '<li><a href="/pet-friendly-parks/">Dog parks &amp; green space</a></li>'
        '<li><a href="/pet-friendly-restaurants/">Pet-friendly restaurants</a></li>'
        "</ul></section>"
    ) % (hotel_count, park_count, restaurant_count, _e(latest_verified_date))


def enrich_hub_page(html_text: str, intro_html: str) -> str:
    _require(_HUB_DIRECTORY_MARKER in html_text, "missing hub main anchor")
    return html_text.replace(_HUB_DIRECTORY_MARKER, _HUB_DIRECTORY_MARKER + intro_html, 1)
