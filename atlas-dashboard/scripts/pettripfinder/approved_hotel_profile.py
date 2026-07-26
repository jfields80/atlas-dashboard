"""PETTRIPFINDER-DESIGN-004 -- founder-approved hotel-profile renderer.

Visual authority: ``pettripfinder-approved-hotel-profile.png`` (binding). This
module renders the SAME ``HotelProfileVM`` the previous approved renderer
consumed -- the data pipeline, fact composition, and honesty rules
(``hotel_profile.build_vm_from_production``: "Not stated by the reviewed
source", no inferred species, evidence-only) are unchanged. Only the visual
layer is new:

    dark evergreen top bar -> breadcrumbs -> media + identity lead ->
    six-cell fact strip -> actions -> verification banner ->
    full policy details | helpful places -> related hotels
    + desktop sidebar (plan / provenance / disclosure) + mobile sticky bar.

Honesty constraints carried through:
- Every fact/date/phone/URL comes from the VM (committed package + seed row).
- Nearby places are REAL inventory rows (parks/restaurants); no distances are
  shown because production carries no coordinates (doctrine: never fabricate).
- The media slot uses the approved temporary review imagery, captioned as
  temporary; Google Places media is a separate later phase.
- Primary CTA wording is "Visit official site" (founder instruction) and every
  outbound action routes through the tracked /go/ interstitials.
"""

from __future__ import annotations

import html
import re
from typing import Dict, Iterable, List, Optional, Sequence

from scripts.pettripfinder.commercial_actions import (
    ACTION_CALL,
    ACTION_DIRECTIONS,
    ACTION_OFFICIAL_WEBSITE,
    ACTION_REPORT_CHANGE,
    go_route,
)
from scripts.pettripfinder.hotel_profile import HotelProfileVM, STATE_VERIFIED

HOTEL_CSS_HREF = "/hotel-profile.css"


def _e(s: str) -> str:
    return html.escape(s or "", quote=False)


def _ea(s: str) -> str:
    return html.escape(s or "", quote=True)


# --------------------------------------------------------------------------- #
# Inline line-icon SVGs (thin-stroke, per the approved mockup; no emoji).
# --------------------------------------------------------------------------- #

_PAW = ('<span class="hp-paw" aria-hidden="true"><svg viewBox="0 0 48 42">'
        '<ellipse cx="24" cy="29" rx="12.5" ry="10.5"/>'
        '<ellipse cx="8.5" cy="18" rx="5" ry="7" transform="rotate(-18 8.5 18)"/>'
        '<ellipse cx="18" cy="8.5" rx="5" ry="7" transform="rotate(-7 18 8.5)"/>'
        '<ellipse cx="30" cy="8.5" rx="5" ry="7" transform="rotate(7 30 8.5)"/>'
        '<ellipse cx="39.5" cy="18" rx="5" ry="7" transform="rotate(18 39.5 18)"/></svg></span>')
_SVG_PIN = ('<svg viewBox="0 0 24 24" aria-hidden="true">'
            '<path d="M20 10c0 5-8 12-8 12S4 15 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/></svg>')
_SVG_CHECK = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m5 12.5 4.5 4.5L19 7.5"/></svg>'
_SVG_SHIELD = ('<svg viewBox="0 0 24 24" aria-hidden="true">'
               '<path d="M12 3 20 6v5.5c0 5-3 8.2-8 10.5-5-2.3-8-5.5-8-10.5V6l8-3Z"/>'
               '<path d="m8.5 12 2.5 2.5L16 9.5"/></svg>')
_SVG_EXT = ('<svg viewBox="0 0 24 24" aria-hidden="true">'
            '<path d="M14 5h5v5M19 5l-8 8M10 6H6a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-4"/></svg>')
_SVG_PHONE = ('<svg viewBox="0 0 24 24" aria-hidden="true">'
              '<path d="M5 4h4l2 5-2.5 1.5a12 12 0 0 0 5 5L15 13l5 2v4a2 2 0 0 1-2 2A16 16 0 0 1 3 6a2 2 0 0 1 2-2Z"/></svg>')
_SVG_DOG = ('<svg viewBox="0 0 24 24" aria-hidden="true">'
            '<path d="M4.5 10.5 3 6l3.5 1h4L14 4l1 4.5 4 1.5v3l-2.5 1v4.5h-3v-3h-5v3h-3v-6l-1-2.5Z"/>'
            '<circle cx="7.6" cy="9.3" r=".9" fill="currentColor" stroke="none"/></svg>')
_SVG_CAT = ('<svg viewBox="0 0 24 24" aria-hidden="true">'
            '<path d="M5 10V4l3.5 2.5h7L19 4v6a7 7 0 0 1-14 0Z"/>'
            '<circle cx="9.3" cy="10.6" r=".9" fill="currentColor" stroke="none"/>'
            '<circle cx="14.7" cy="10.6" r=".9" fill="currentColor" stroke="none"/>'
            '<path d="M12 13.4v1.2M2.5 17.5c2.5 1.5 5 2.2 9.5 2.2s7-.7 9.5-2.2"/></svg>')
_SVG_TREE = ('<svg viewBox="0 0 24 24" aria-hidden="true">'
             '<path d="M12 3 6.5 10h2L5 15.5h5V21h4v-5.5h5L15.5 10h2L12 3Z"/></svg>')
_SVG_FORK = ('<svg viewBox="0 0 24 24" aria-hidden="true">'
             '<path d="M7 3v6c0 1.7 1 3 2.5 3S12 10.7 12 9V3M9.5 3v18M17.5 3c-2 1.6-2.5 4.5-2.5 7h2.5v11M19 3v7"/></svg>')
_SVG_CARET = '<svg class="hp-caret" viewBox="0 0 24 24" aria-hidden="true"><path d="m6 9 6 6 6-6"/></svg>'

_PLACE_ICON = {"park": _SVG_TREE, "restaurant": _SVG_FORK}


# --------------------------------------------------------------------------- #
# Small derivations (all from the VM; nothing invented).
# --------------------------------------------------------------------------- #

def _corridor_parts(vm: HotelProfileVM) -> tuple:
    """('Grove City corridor', 'Grove City Corridor', 'COLUMBUS, OH')."""
    raw = vm.corridor or ""
    area = raw.split("·")[0].strip() or raw.strip()
    metro = raw.split("·")[1].strip() if "·" in raw else "Columbus, OH"
    return area, area.title(), metro.upper()


def _source_display(vm: HotelProfileVM) -> str:
    """'the official Drury Hotels website' -> 'Official Drury Hotels website'."""
    s = (vm.source_name or "").strip()
    if s.lower().startswith("the "):
        s = s[4:]
    return (s[:1].upper() + s[1:]) if s else "Official source"


def _checked_details(vm: HotelProfileVM) -> str:
    """Comma list of the policy fields the source actually stated, derived from
    the VM's fact cells (a cell is 'stated' when it is not the dim Not-stated
    presentation)."""
    stated: List[str] = []
    species_done = False
    for label, _value, cls in vm.facts:
        if cls == "dim":
            continue
        if label in ("Dogs", "Cats", "Species", "Pet policy"):
            if not species_done:
                stated.append("species")
                species_done = True
        elif label == "Pet charge":
            stated.append("fee")
        elif label == "Charge basis":
            stated.append("basis")
        elif label == "Max pets":
            stated.append("pet limit")
        elif label == "Weight limit":
            stated.append("weight limit")
    if not stated:
        stated = ["pet-friendly status"]
    joined = ", ".join(stated)
    return joined[:1].upper() + joined[1:]


def _fact_cell(label: str, value: str, cls: str) -> str:
    icon = ""
    if label == "Dogs" and cls == "yes":
        icon = _SVG_DOG
    elif label == "Cats" and cls == "yes":
        icon = _SVG_CAT
    vcls = ' class="dim"' if cls == "dim" else ""
    return ('<div class="hp-fact"><small>%s</small><b%s>%s<span>%s</span></b></div>'
            % (_e(label), vcls, icon, _e(value)))


def _action_buttons(vm: HotelProfileVM, listing_id: str, *, primary_first: bool = True) -> str:
    """Visit official site / Get directions / Call hotel -- every target is a
    tracked /go/ interstitial already built for this listing. The call button
    renders only when the seed row carries a real phone number."""
    parts = []
    if vm.official_url:
        parts.append('<a class="hp-btn hp-btn-primary" href="%s">Visit official site%s</a>'
                     % (_ea(go_route(listing_id, ACTION_OFFICIAL_WEBSITE)), _SVG_EXT))
    if vm.address and vm.address.strip(", "):
        parts.append('<a class="hp-btn" href="%s">%sGet directions</a>'
                     % (_ea(go_route(listing_id, ACTION_DIRECTIONS)), _SVG_PIN))
    if vm.phone:
        parts.append('<a class="hp-btn" href="%s">%sCall hotel&nbsp; %s</a>'
                     % (_ea(go_route(listing_id, ACTION_CALL)), _SVG_PHONE, _e(vm.phone)))
    return "".join(parts)


# --------------------------------------------------------------------------- #
# Sections.
# --------------------------------------------------------------------------- #

def _header() -> str:
    nav = ('<a href="/pet-friendly-hotels/">Hotels</a>'
           '<a href="/pet-friendly-parks/">Parks</a>'
           '<a href="/pet-friendly-restaurants/">Restaurants</a>'
           '<a href="/#trip">Trip planning</a>'
           '<a href="/methodology/">How we verify</a>')
    return ('<header class="hp-top"><div class="wrap">'
            '<a class="hp-brand" href="/">%sPetTripFinder<em>Columbus</em></a>'
            '<nav class="hp-nav" aria-label="Primary">%s</nav>'
            '<button class="hp-burger" aria-label="Open menu" aria-expanded="false">&#9776;</button>'
            '</div></header>') % (_PAW, nav)


def _breadcrumbs(vm: HotelProfileVM, corridor_href: Optional[str]) -> str:
    _, corridor_title, _ = _corridor_parts(vm)
    if corridor_href:
        corridor_html = '<a href="%s">%s</a>' % (_ea(corridor_href), _e(corridor_title))
    else:
        corridor_html = "<span>%s</span>" % _e(corridor_title)
    return ('<nav class="hp-crumbs" aria-label="Breadcrumb"><div class="wrap">'
            '<a href="/">Home</a><span class="sep">&rsaquo;</span>'
            '<a href="/pet-friendly-hotels/">Pet-Friendly Hotels</a><span class="sep">&rsaquo;</span>'
            '%s<span class="sep">&rsaquo;</span><span class="here">%s</span>'
            '</div></nav>') % (corridor_html, _e(vm.name))


def _lead(vm: HotelProfileVM, media_src: Optional[str]) -> str:
    if media_src:
        media = ('<figure class="hp-media"><img src="%s" alt="Temporary preview photo for %s">'
                 '<figcaption>Temporary preview imagery for founder review &mdash; replaced by '
                 'licensed property media in a later phase.</figcaption></figure>'
                 % (_ea(media_src), _ea(vm.name)))
    else:
        media = ('<figure class="hp-media"><figcaption>Property photo unavailable. '
                 '<a href="/methodology/#photos">How we handle photos</a></figcaption></figure>')
    checked = ('<span class="hp-checked">Checked %s</span>' % _e(vm.verified_at)) if vm.verified_at else ""
    source_line = ""
    if vm.source_name:
        source_line = ('<p class="hp-sourceline">All details come directly from %s.</p>'
                       % _e(vm.source_name))
    # The corridor label is rendered VERBATIM ("Grove City corridor ·
    # Columbus, OH"); the mockup's uppercase presentation comes from CSS
    # text-transform, keeping the source string intact on the page.
    return ('<div class="hp-lead">%s<div class="hp-id">'
            '<p class="hp-eyebrow">%s%s</p>'
            '<h1 class="hp-name">%s</h1>'
            '<p class="hp-verifline"><span class="hp-chip">%s%s</span>%s</p>'
            '<p class="hp-summary">%s</p>%s'
            '</div></div>'
            ) % (media, _SVG_PIN, _e(vm.corridor), _e(vm.name),
                 _SVG_CHECK, _e(vm.verif_chip.lstrip("✓ ").strip() or "Verified pet policy"),
                 checked, _e(vm.summary), source_line)


def _verifband(vm: HotelProfileVM) -> str:
    if not (vm.verified_at and vm.source_name):
        return ""
    return ('<div class="hp-verifband">%s<span><b>Policy verified %s</b> from %s.</span>'
            '<a href="/methodology/">See exactly how PetTripFinder verifies every policy &rarr;</a></div>'
            % (_SVG_SHIELD, _e(vm.verified_at), _e(vm.source_name)))


def _details_panel(vm: HotelProfileVM) -> str:
    rows = "".join(
        '<div><dt>%s</dt><dd%s>%s</dd></div>'
        % (_e(label), ' class="dim"' if cls == "dim" else "", _e(value))
        for label, value, cls in vm.details_rows)
    note = vm.details_note or ("Policies can change. Please confirm current details with the "
                               "property before you book.")
    return ('<details class="hp-panel hp-acc" id="policy-details">'
            '<summary><h2>Full pet policy details</h2>%s</summary>'
            '<dl class="hp-dl">%s</dl><p class="hp-smallnote">%s</p></details>'
            % (_SVG_CARET, rows, _e(note)))


def _nearby_panel(nearby: Sequence[Dict[str, str]]) -> str:
    if not nearby:
        return ""
    items = []
    for place in nearby:
        icon = _PLACE_ICON.get(place.get("kind", ""), _SVG_TREE)
        items.append(
            '<div class="hp-place"><span class="ico">%s</span><span class="txt">'
            '<b>%s</b><p>%s</p><span class="meta">%s</span></span>'
            '<a class="hp-minibtn" href="%s">%s</a></div>'
            % (icon, _e(place["name"]), _e(place.get("desc", "")), _e(place.get("meta", "")),
               _ea(place["href"]), _e(place.get("btn", "View details"))))
    return ('<details class="hp-panel hp-acc" id="nearby">'
            '<summary><h2>Helpful places near this hotel</h2>%s</summary>%s'
            '<p class="hp-smallnote">Distances are not shown: PetTripFinder lists real verified '
            'places from the same area and never estimates mileage.</p></details>'
            % (_SVG_CARET, "".join(items)))


def _related_section(vm: HotelProfileVM, corridor_href: Optional[str],
                     thumb_for: Dict[str, str]) -> str:
    if not vm.related:
        return ""
    _, corridor_title, _ = _corridor_parts(vm)
    see_all = corridor_href or "/pet-friendly-hotels/"
    cards = []
    for rel in vm.related:
        thumb = thumb_for.get(rel.route, "")
        img = '<img src="%s" alt="">' % _ea(thumb) if thumb else ""
        fact = '<span class="fact">%s</span>' % _e(rel.fact) if rel.fact else ""
        vdate = ('<span class="vdate">Verified&nbsp; %s</span>' % _e(rel.verified_at)) if rel.verified_at else ""
        cards.append('<div class="hp-relcard">%s<span class="txt"><b>%s</b>%s%s</span>'
                     '<a class="hp-minibtn" href="%s">View policy</a></div>'
                     % (img, _e(rel.name), vdate, fact, _ea(rel.route)))
    return ('<section class="hp-related"><div class="hp-sechead">'
            '<h2>More verified pet-friendly hotels in %s</h2>'
            '<a href="%s">View all hotels in this area &rarr;</a></div>'
            '<div class="hp-relgrid">%s</div></section>'
            % (_e(corridor_title), _ea(see_all), "".join(cards)))


def _sidebar(vm: HotelProfileVM, listing_id: str) -> str:
    plan = ('<div class="hp-card hp-plan"><h3>Plan your stay</h3>'
            '<p class="sub">Check current rates and availability directly with the hotel.</p>%s</div>'
            % _action_buttons(vm, listing_id))
    quote = ""
    if vm.evidence_quote:
        src_link = ('<a class="src" href="%s" rel="nofollow noopener" target="_blank">'
                    'View the source page %s</a>' % (_ea(vm.source_url), _SVG_EXT)) if vm.source_url else ""
        quote = ('<details class="hp-quote"><summary>See the exact recorded wording &rarr;</summary>'
                 '<blockquote>&ldquo;%s&rdquo;</blockquote>%s</details>'
                 % (_e(vm.evidence_quote), src_link))
    # The SOURCE value links to the EXACT committed policy-evidence URL
    # (PROD-004 launch-safety invariant: the exact source_url is reachable
    # from every verified profile).
    if vm.source_url:
        source_dd = ('<a class="hp-evidence-link" href="%s" rel="nofollow noopener" '
                     'target="_blank">%s</a>' % (_ea(vm.source_url), _e(_source_display(vm))))
    else:
        source_dd = _e(_source_display(vm))
    prov = ('<div class="hp-card hp-prov"><p class="hp-provhead">%sVerified provenance</p><dl>'
            '<dt>Source</dt><dd>%s</dd>'
            '<dt>Verified</dt><dd>%s</dd>'
            '<dt>Checked details</dt><dd>%s</dd></dl>%s'
            '<a class="hp-report" href="%s">Report an outdated or incorrect policy</a></div>'
            % (_SVG_CHECK, source_dd, _e(vm.verified_at or "—"),
               _e(_checked_details(vm)), quote, _ea(go_route(listing_id, ACTION_REPORT_CHANGE))))
    affil = ('<div class="hp-card"><p class="hp-affil">PetTripFinder may earn a commission when you '
             'use a booking link. This does not change the property&rsquo;s placement or verified '
             'policy information.</p></div>')
    return '<aside class="hp-side">%s%s%s</aside>' % (plan, prov, affil)


def _sticky(vm: HotelProfileVM, listing_id: str) -> str:
    cells = []
    if vm.official_url:
        cells.append('<a href="%s">%sVisit official site</a>'
                     % (_ea(go_route(listing_id, ACTION_OFFICIAL_WEBSITE)), _SVG_EXT))
    if vm.phone:
        cells.append('<a href="%s">%sCall hotel</a>'
                     % (_ea(go_route(listing_id, ACTION_CALL)), _SVG_PHONE))
    if not cells:
        return ""
    return '<div class="hp-sticky">%s</div>' % "".join(cells)


def _footer() -> str:
    return ('<footer class="hp-foot"><div class="wrap">'
            '<span>&copy; 2026 PetTripFinder Columbus</span>'
            '<nav><a href="/methodology/">How we verify</a><a href="/about/">About us</a>'
            '<a href="/contact/">Contact</a><a href="/methodology/">Privacy</a></nav>'
            '<span>Your trusted guide to pet-friendly travel in Columbus.</span>'
            '</div></footer>')


_JS = ("<script>(function(){var b=document.querySelector('.hp-burger'),"
       "n=document.querySelector('.hp-nav');if(b&&n){b.addEventListener('click',function(){"
       "var o=n.classList.toggle('hp-open');b.setAttribute('aria-expanded',String(o));});}"
       "if(window.matchMedia&&matchMedia('(min-width:861px)').matches){"
       "document.querySelectorAll('details.hp-acc').forEach(function(d){d.open=true;});}"
       "})();</script>")


# --------------------------------------------------------------------------- #
# Page.
# --------------------------------------------------------------------------- #

def render_approved_hotel_profile(
    vm: HotelProfileVM,
    *,
    listing_id: str,
    css_href: str = HOTEL_CSS_HREF,
    media_src: Optional[str] = None,
    nearby: Sequence[Dict[str, str]] = (),
    corridor_href: Optional[str] = None,
    related_thumbs: Optional[Dict[str, str]] = None,
) -> str:
    """Complete hotel-profile page in the founder-approved design. ``nearby``
    rows and ``related_thumbs`` are supplied by the site layer from REAL
    inventory; the renderer itself never invents a place, distance, or photo."""
    title = "%s Pet Policy | PetTripFinder Columbus" % vm.name
    desc = vm.summary if vm.state == STATE_VERIFIED else (
        "%s in Columbus, Ohio: pet policy not yet verified by PetTripFinder." % vm.name)
    body = (
        '<a class="skip skip-link" href="#main">Skip to content</a>'
        + _header()
        + _breadcrumbs(vm, corridor_href)
        + '<main id="main" class="hp-main"><div class="wrap"><div class="hp-grid">'
        + '<section class="hp-content">'
        + _lead(vm, media_src)
        + '<div class="hp-facts">' + "".join(_fact_cell(*cell) for cell in vm.facts) + "</div>"
        + '<div class="hp-actions">' + _action_buttons(vm, listing_id) + "</div>"
        + _verifband(vm)
        + '<div class="hp-cols">' + _details_panel(vm) + _nearby_panel(nearby) + "</div>"
        + _related_section(vm, corridor_href, related_thumbs or {})
        + "</section>"
        + _sidebar(vm, listing_id)
        + "</div></div></main>"
        + _footer()
        + _sticky(vm, listing_id)
        + _JS
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        "<title>%s</title>"
        '<meta name="description" content="%s">'
        '<meta name="robots" content="index, follow">'
        '<link rel="stylesheet" href="%s">'
        '</head><body class="hp">%s</body></html>'
    ) % (_e(title), _ea(re.sub(r"\s+", " ", desc)[:300]), _ea(css_href), body)
