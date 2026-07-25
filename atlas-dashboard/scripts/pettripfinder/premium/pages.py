"""PETTRIPFINDER-DESIGN-002 -- premium page renderers.

Full-page renderers for the consumer surfaces (homepage, hotel/park/restaurant
listings, park/restaurant profiles, comparison, corridor, methodology) built on
the shared design system in ``theme.py`` and the placeholder media in
``media.py``. Pure presentation: every fact is supplied by the caller from the
committed launch package / real seed data; unstated values render as
"Not stated", never guessed; no photography, ratings, prices, reviews, or
amenities are invented.
"""

from __future__ import annotations

import html
import re
from typing import Dict, List, Optional, Sequence, Tuple

from scripts.pettripfinder.premium import theme
from scripts.pettripfinder.premium.media import (
    CATEGORY_BRAND, CATEGORY_CITY, CATEGORY_HOTEL, CATEGORY_PARK,
    CATEGORY_RESTAURANT, MediaSpec, render_media,
)

BASE_URL = "https://pettripfinder.com"


def _e(s: str) -> str:
    return html.escape(s or "", quote=False)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").strip().lower()).strip("-")


# Inline decorative icons (currentColor).
IC_PIN = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" '
          'stroke-linecap="round" stroke-linejoin="round"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/>'
          '<circle cx="12" cy="10" r="2.6"/></svg>')
IC_CHECK = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round"><path d="m20 6-11 11-5-5"/></svg>')
IC_DOC = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" '
          'stroke-linecap="round" stroke-linejoin="round"><path d="M6 2h9l5 5v15H6z"/>'
          '<path d="M14 2v6h6"/><path d="M9 13h6M9 17h6"/></svg>')
IC_PAW = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" '
          'stroke-linecap="round" stroke-linejoin="round"><circle cx="5.5" cy="12.5" r="1.8"/>'
          '<circle cx="9.5" cy="7.5" r="1.8"/><circle cx="14.5" cy="7.5" r="1.8"/>'
          '<circle cx="18.5" cy="12.5" r="1.8"/>'
          '<path d="M12 12c-2.5 0-5 2-5 4.5C7 18.5 9 20 12 20s5-1.5 5-3.5C17 14 14.5 12 12 12Z"/></svg>')
IC_X = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
        'stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18M6 6l12 12"/></svg>')
IC_ARROW = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round" style="width:15px;height:15px">'
            '<path d="M5 12h14M13 6l6 6-6 6"/></svg>')


# --------------------------------------------------------------------------- #
# Hotel card data + rendering (used by home + hotel listing).
# --------------------------------------------------------------------------- #

def hotel_card(*, name: str, area: str, route: str, verified_at: str,
               facts: Dict[str, str], initials: str = "", featured: bool = False) -> str:
    spec = MediaSpec(category=CATEGORY_HOTEL, label=name.split(" Columbus")[0].strip() or name,
                     sublabel=area, initials=initials)
    pill = theme.verified_pill("Verified policy", "ok")
    chips = "".join('<span class="pt-fact%s">%s</span>' % ((" is-dim" if dim else ""), v)
                    for v, dim in _hotel_card_chips(facts))
    vdate = ('<span class="pt-card-vdate">%s %s</span>'
             % (IC_CHECK_MINI, _e("Verified " + verified_at)) if verified_at else "")
    return (
        '<article class="pt-card">'
        '<div class="pt-card-media"><span class="pt-card-pill">%s</span>%s</div>'
        '<div class="pt-card-body">'
        '<span class="pt-card-area">%s</span>'
        '<h3 class="pt-card-name"><a href="%s">%s</a></h3>'
        '<div class="pt-card-facts">%s</div>'
        '<div class="pt-card-foot"><a class="pt-card-link" href="%s">View pet policy %s</a>%s</div>'
        '</div></article>'
    ) % (pill, render_media(spec, ratio="4x3", variant="card", label=False),
         _e(area), route, _e(name), chips, route, IC_ARROW, vdate)


IC_CHECK_MINI = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" '
                 'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" '
                 'style="width:13px;height:13px;color:#2f7a52;display:inline-block;vertical-align:-1px">'
                 '<path d="m20 6-11 11-5-5"/></svg>')


def _hotel_card_chips(f: Dict[str, str]) -> List[Tuple[str, bool]]:
    """Up to three honest chips. Never infers dogs/cats from a generic
    'pets allowed'; never turns a missing value into 'No'."""
    sp = (f.get("species_allowed") or "").lower()
    sparse = not any(f.get(k) for k in ("species_allowed", "pet_fee", "pet_count_limit", "weight_limit"))
    chips: List[Tuple[str, bool]] = []
    if sparse:
        return [("<b>Pets welcome</b>", False), ("Details not stated", True)]
    if "dog" in sp and "cat" in sp:
        chips.append(("Dogs &amp; cats", False))
    elif "dog" in sp:
        chips.append(("Dogs <b>accepted</b>", False))
    elif "cat" in sp:
        chips.append(("Cats <b>accepted</b>", False))
    else:
        chips.append(("Pets welcome", False))
    if f.get("pet_fee"):
        basis = (f.get("fee_basis") or "").replace("per room ", "").replace("per ", "/")
        chips.append(("Fee <b>%s</b>%s" % (_e(f["pet_fee"]),
                      (" " + _e(basis)) if basis else ""), False))
    else:
        chips.append(("Fee not stated", True))
    if f.get("pet_count_limit"):
        chips.append(("Up to <b>%s</b> pets" % _e(f["pet_count_limit"]), False))
    elif f.get("weight_limit"):
        chips.append(("Under <b>%s</b>" % _e(f["weight_limit"]), False))
    return chips[:3]


# --------------------------------------------------------------------------- #
# Homepage.
# --------------------------------------------------------------------------- #

def render_home(*, hotel_count: int, park_count: int, restaurant_count: int,
                latest_verified_date: str, featured: Sequence[Dict],
                corridors: Sequence[Dict], head_extra: str = "") -> str:
    hero = _home_hero(hotel_count, latest_verified_date)
    search = _home_search()
    stats = _home_stats(hotel_count, park_count, restaurant_count, latest_verified_date)
    featured_sec = _home_featured(featured)
    categories = _home_categories(hotel_count, park_count, restaurant_count)
    verify = _home_verify()
    explore = _home_explore(corridors, hotel_count)
    cta = _home_cta()
    body = (
        '<div class="pt-hero"><div class="pt-hero-bg"></div><div class="pt-hero-scrim"></div>'
        '<div class="pt-container pt-hero-in">%s</div></div>'
        '<div class="pt-container">%s</div>'
        '<section class="pt-section--tight"><div class="pt-container">%s</div></section>'
        '%s%s%s%s%s'
    ) % (hero, search, stats, featured_sec, categories, verify, explore, cta)
    return theme.page(
        title="Pet-Friendly Travel in Columbus, Ohio | PetTripFinder",
        description=("Verified pet-friendly hotels, dog parks, and restaurants in Columbus, Ohio. "
                     "Every hotel pet policy is read straight from the property's own official "
                     "website — real fees, limits, and species, never guessed."),
        route="/", body=body, active="", head_extra=head_extra, css_href="/styles.css")


def _home_hero(hotel_count: int, latest: str) -> str:
    media = render_media(
        MediaSpec(category=CATEGORY_CITY, label="Columbus, Ohio",
                  sublabel="Pet-friendly city guide",
                  alt="Branded PetTripFinder placeholder artwork for Columbus, Ohio. "
                      "No stock or third-party photograph is used."),
        ratio="hero", variant="hero", label=False)
    trust = "".join('<span>%s%s</span>' % (IC_CHECK, t) for t in (
        "Read from official sources", "Exact fees & limits", "Honest “Not stated”"))
    return (
        '<div class="pt-hero-copy">'
        '<span class="pt-hero-loc">%s Columbus, Ohio</span>'
        '<h1>Travel anywhere with your pet, without the check-in surprises.</h1>'
        '<p class="pt-hero-sub">PetTripFinder verifies each hotel&rsquo;s pet policy directly from its '
        'own official website &mdash; the real fee, pet limit, and which animals are welcome &mdash; '
        'so you know before you book.</p>'
        '<div class="pt-hero-actions">'
        '<a class="btn btn-accent" href="/pet-friendly-hotels/">Browse verified hotels</a>'
        '<a class="btn btn-onhero" href="/methodology/">How verification works</a></div>'
        '<div class="pt-hero-trust">%s</div>'
        '</div>'
        '<div class="pt-hero-media">%s'
        '<div class="pt-hero-badge"><b>%d</b><span>evidence-backed hotels, verified from official sources</span></div>'
        '</div>'
    ) % (IC_PIN, trust, media, hotel_count)


def _home_search() -> str:
    return (
        '<div class="pt-search"><div class="pt-search-card">'
        '<div class="pt-search-row">'
        '<div class="pt-field"><label>Destination</label>'
        '<div class="pt-fake">%s Columbus, Ohio <small>&middot; more cities coming</small></div></div>'
        '<div class="pt-field"><label>Traveling with</label>'
        '<div class="pt-petchips">'
        '<a class="pt-chip" href="/pet-friendly-hotels/">%s Dog</a>'
        '<a class="pt-chip" href="/pet-friendly-hotels/">%s Cat</a>'
        '<a class="pt-chip" href="/pet-friendly-hotels/policy-comparison/">Compare policies</a>'
        '</div></div>'
        '<a class="btn btn-ever btn-block" href="/pet-friendly-hotels/">Find verified stays</a>'
        '</div>'
        '<p class="pt-search-note">Browse verified pet policies &mdash; PetTripFinder does not sell '
        'rooms or show live availability. You always book with the hotel or its official partner.</p>'
        '</div></div>'
    ) % (IC_PIN, IC_PAW, IC_PAW)


def _home_stats(h: int, p: int, r: int, latest: str) -> str:
    def stat(n, label):
        return '<div class="pt-stat"><b>%s</b><span>%s</span></div>' % (n, label)
    return ('<div class="pt-stats">%s%s%s%s</div>'
            % (stat(h, "Verified pet-friendly hotels"),
               stat(p, "Dog parks &amp; green spaces"),
               stat(r, "Pet-welcoming restaurants"),
               stat("100%", "Read from official sources")))


def _home_featured(featured: Sequence[Dict]) -> str:
    cards = "".join(hotel_card(**c) for c in featured[:6])
    return (
        '<section class="pt-section pt-band"><div class="pt-container">'
        '<div class="pt-sec-head">%s<h2 class="pt-h2">Featured verified stays</h2>'
        '<p class="pt-lead">A hand-checked look at Columbus hotels whose pet policies we read '
        'directly from the source. Every fee and limit below is quoted &mdash; never estimated.</p></div>'
        '<div class="pt-grid pt-grid--3" style="margin-top:34px">%s</div>'
        '<div style="margin-top:34px"><a class="btn btn-ghost" href="/pet-friendly-hotels/">'
        'See all verified hotels %s</a></div>'
        '</div></section>'
    ) % (theme.eyebrow("Where to stay"), cards, IC_ARROW)


def _home_categories(h: int, p: int, r: int) -> str:
    def cat(category, title, desc, route):
        spec = MediaSpec(category=category, label="", initials="")
        return ('<a class="pt-cat" href="%s">%s<div class="pt-cat-in"><h3>%s</h3><p>%s</p>'
                '<span class="pt-cat-go">Explore %s</span></div></a>'
                % (route, render_media(spec, ratio="1x1", variant="tile", label=False),
                   _e(title), _e(desc), IC_ARROW))
    blocks = (
        cat(CATEGORY_HOTEL, "Verified hotels", "%d hotels with evidence-backed pet policies." % h,
            "/pet-friendly-hotels/")
        + cat(CATEGORY_PARK, "Dog parks", "%d parks & green spaces to run and play." % p,
              "/pet-friendly-parks/")
        + cat(CATEGORY_RESTAURANT, "Pet-friendly dining", "%d patios & taprooms that welcome dogs." % r,
              "/pet-friendly-restaurants/")
        + cat(CATEGORY_BRAND, "Compare policies", "Fees, limits & species side by side.",
              "/pet-friendly-hotels/policy-comparison/")
    )
    return (
        '<section class="pt-section"><div class="pt-container">'
        '<div class="pt-sec-head">%s<h2 class="pt-h2">Browse by trip need</h2></div>'
        '<div class="pt-grid pt-grid--4" style="margin-top:30px">%s</div>'
        '</div></section>'
    ) % (theme.eyebrow("Plan the trip"), blocks)


def _home_verify() -> str:
    gen = ("Pets allowed", "No fee or limit given", "Which animals? Unclear",
           "“Call to confirm”")
    ptf = ("Dogs accepted · Cats not stated (never guessed)",
           "Exact fee &amp; fee basis, quoted from the source",
           "Weight &amp; pet limits reported honestly",
           "Service animals kept separate, with a checked date")
    gen_li = "".join('<li><span class="pt-vs-ic">%s</span>%s</li>' % (IC_X, _e(t)) for t in gen)
    ptf_li = "".join('<li><span class="pt-vs-ic">%s</span>%s</li>' % (IC_CHECK, t) for t in ptf)
    return (
        '<section class="pt-section pt-band"><div class="pt-container">'
        '<div class="pt-sec-head center">%s<h2 class="pt-h2">Not just &ldquo;pets allowed.&rdquo; '
        'The actual policy.</h2>'
        '<p class="pt-lead">Most listings stop at two vague words. We read each property&rsquo;s own '
        'official page and record exactly what it says &mdash; and honestly mark what it doesn&rsquo;t.</p></div>'
        '<div class="pt-vs">'
        '<div class="pt-vs-card is-generic"><h3><span class="pt-vs-tag">Typical listing</span></h3>'
        '<ul class="pt-vs-list">%s</ul></div>'
        '<div class="pt-vs-mid"><span>vs.</span></div>'
        '<div class="pt-vs-card is-ptf"><h3><span class="pt-vs-tag">PetTripFinder</span></h3>'
        '<ul class="pt-vs-list">%s</ul></div>'
        '</div>'
        '<div class="pt-sec-head center" style="margin-top:30px"><a class="btn btn-ghost" '
        'href="/methodology/">Read our full methodology %s</a></div>'
        '</div></section>'
    ) % (theme.eyebrow("Why it's different"), gen_li, ptf_li, IC_ARROW)


def _home_explore(corridors: Sequence[Dict], hotel_count: int) -> str:
    map_media = render_media(
        MediaSpec(category=CATEGORY_CITY, label="Columbus corridors",
                  sublabel="Downtown · Dublin · Polaris · Grove City",
                  alt="Branded placeholder map of the Columbus, Ohio pet-travel corridors."),
        ratio="4x3", variant="card")
    rows = []
    for c in corridors:
        sub = "%d verified %s" % (c["count"], "hotel" if c["count"] == 1 else "hotels")
        rows.append('<a class="pt-corridor" href="%s"><span><b>%s</b><span>%s</span></span>'
                    '<span class="pt-corridor-go">%s</span></a>'
                    % (c["route"], _e(c["name"]), sub, IC_ARROW))
    if not rows:
        rows.append('<a class="pt-corridor" href="/pet-friendly-hotels/"><span><b>All Columbus hotels</b>'
                    '<span>%d verified stays</span></span><span class="pt-corridor-go">%s</span></a>'
                    % (hotel_count, IC_ARROW))
    return (
        '<section class="pt-section"><div class="pt-container"><div class="pt-explore">'
        '<div class="pt-explore-map">%s</div>'
        '<div><div class="pt-sec-head">%s<h2 class="pt-h2">Plan a Columbus pet trip</h2>'
        '<p class="pt-lead">Columbus is compact and dog-friendly. Start from a corridor near your '
        'plans, then pair a verified hotel with nearby parks and patios.</p></div>'
        '<ul class="pt-corridors">%s</ul></div>'
        '</div></div></section>'
    ) % (map_media, theme.eyebrow("Explore the city"), "".join(rows))


def _home_cta() -> str:
    bg = render_media(MediaSpec(category=CATEGORY_HOTEL, label="", initials=""),
                      ratio="16x9", variant="hero", glyph=False, label=False)
    return (
        '<section class="pt-section"><div class="pt-container">'
        '<div class="pt-ctaband">%s<div class="pt-ctaband-in">'
        '<h2>Your next trip, planned around your pet.</h2>'
        '<p>Compare verified pet policies, then book the stay that actually welcomes your dog or cat.</p>'
        '<div class="pt-ctaband-actions">'
        '<a class="btn btn-accent" href="/pet-friendly-hotels/">Browse verified hotels</a>'
        '<a class="btn btn-onhero" href="/pet-friendly-hotels/policy-comparison/">Compare policies</a>'
        '</div></div></div>'
        '</div></section>'
    ) % bg


# --------------------------------------------------------------------------- #
# Breadcrumbs (inner pages).
# --------------------------------------------------------------------------- #

def crumbs(items: Sequence[Tuple[str, str]], *, on_dark: bool = True) -> str:
    cls = "pt-crumbs" if on_dark else "pt-crumbs pt-crumbs--ink"
    lis = "".join(
        ('<li><a href="%s">%s</a></li>' % (r, _e(n)) if r else '<li aria-current="page">%s</li>' % _e(n))
        for n, r in items)
    return '<nav aria-label="Breadcrumb"><ol class="%s">%s</ol></nav>' % (cls, lis)


# --------------------------------------------------------------------------- #
# Hotel listing.
# --------------------------------------------------------------------------- #

def render_hotel_listing(*, cards: Sequence[Dict], hotel_count: int,
                         latest_verified_date: str, head_extra: str = "") -> str:
    grid = "".join(hotel_card(**c) for c in cards)
    body = (
        '<div class="pt-pagehead"><div class="pt-container">%s'
        '<h1>Verified pet-friendly hotels in Columbus, Ohio</h1>'
        '<p class="pt-lead">%d hotels whose pet policy we read directly from the property&rsquo;s own '
        'official website &mdash; the real fee, pet limit, and which animals are welcome. Most recently '
        'verified %s.</p></div></div>'
        '<section class="pt-section--tight"><div class="pt-container">'
        '<div class="pt-note">Every policy below is quoted from an official source. Where a source '
        'doesn&rsquo;t state a value, we show &ldquo;Not stated&rdquo; rather than guess. '
        '<a href="/pet-friendly-hotels/policy-comparison/">Compare them side by side &rarr;</a></div>'
        '<div class="pt-grid pt-grid--3" style="margin-top:22px">%s</div>'
        '</div></section>'
    ) % (crumbs([("PetTripFinder", "/"), ("Pet-friendly hotels", "")]),
         hotel_count, _e(latest_verified_date), grid)
    return theme.page(
        title="Verified Pet-Friendly Hotels in Columbus, Ohio | PetTripFinder",
        description=("Browse %d Columbus hotels with evidence-backed pet policies — real fees, pet "
                     "limits, and species, read from each property's official website." % hotel_count),
        route="/pet-friendly-hotels/", body=body, active="hotels",
        head_extra=head_extra, css_href="/styles.css")


# --------------------------------------------------------------------------- #
# Park / restaurant listing.
# --------------------------------------------------------------------------- #

def _place_card(row: Dict, category_slug: str, category: str) -> str:
    name = row["name"]
    spec = MediaSpec(category=category, label=name, sublabel="%s, OH" % row.get("city", ""))
    policy = (row.get("pet_policy") or "").strip()
    if len(policy) > 150:
        policy = policy[:147].rsplit(" ", 1)[0] + "…"
    route = "/%s/%s/" % (category_slug, _slug(name))
    pill = theme.verified_pill("Pet-welcoming", "ok")
    body_policy = '<p style="margin:0;color:var(--ink-2);font-size:14.5px">%s</p>' % _e(policy) if policy else ""
    return (
        '<article class="pt-card">'
        '<div class="pt-card-media"><span class="pt-card-pill">%s</span>%s</div>'
        '<div class="pt-card-body"><span class="pt-card-area">%s, OH</span>'
        '<h3 class="pt-card-name"><a href="%s">%s</a></h3>%s'
        '<div class="pt-card-foot"><a class="pt-card-link" href="%s">View details %s</a></div>'
        '</div></article>'
    ) % (pill, render_media(spec, ratio="4x3", variant="card", label=False), _e(row.get("city", "")),
         route, _e(name), body_policy, route, IC_ARROW)


def render_place_listing(*, category_slug: str, category: str, title: str, lead: str,
                         eyebrow_text: str, rows: Sequence[Dict], head_extra: str = "") -> str:
    grid = "".join(_place_card(r, category_slug, category) for r in rows)
    active = {"pet-friendly-parks": "parks", "pet-friendly-restaurants": "restaurants"}.get(category_slug, "")
    crumbslabel = title
    body = (
        '<div class="pt-pagehead"><div class="pt-container">%s'
        '<h1>%s</h1><p class="pt-lead">%s</p></div></div>'
        '<section class="pt-section--tight"><div class="pt-container">'
        '<div class="pt-grid pt-grid--3">%s</div></div></section>'
    ) % (crumbs([("PetTripFinder", "/"), (crumbslabel, "")]), _e(title), lead, grid)
    return theme.page(
        title="%s | PetTripFinder Columbus" % title,
        description=re.sub("<[^>]+>", "", lead)[:180],
        route="/%s/" % category_slug, body=body, active=active,
        head_extra=head_extra, css_href="/styles.css")


# --------------------------------------------------------------------------- #
# Park / restaurant profile.
# --------------------------------------------------------------------------- #

def nearby_block(groups: Sequence[Tuple[str, str, Sequence[Dict]]]) -> str:
    """``groups``: (title, category_slug, rows). Renders a premium 'nearby'
    section with small linked cards. City-based only (no fabricated distance)."""
    sections = []
    for title, cat_slug, rows in groups:
        if not rows:
            continue
        items = "".join(
            '<a class="pt-corridor" href="/%s/%s/"><span><b>%s</b>'
            '<span>Also in %s, OH</span></span><span class="pt-corridor-go">%s</span></a>'
            % (cat_slug, _slug(r["name"]), _e(r["name"]), _e(r.get("city", "")), IC_ARROW)
            for r in rows)
        sections.append('<div><h2 class="pt-h3" style="margin-bottom:12px">%s</h2>'
                        '<div class="pt-corridors">%s</div></div>' % (_e(title), items))
    if not sections:
        return ""
    return ('<section class="pt-section--tight" style="grid-column:1/-1"><div class="pt-grid pt-grid--2">%s</div></section>'
            % "".join(sections))


def render_place_profile(*, row: Dict, category_slug: str, category: str, place_type: str,
                         go_official: str, go_directions: str, nearby_html: str = "",
                         head_extra: str = "") -> str:
    name = row["name"]
    city = row.get("city", "")
    addr = ", ".join(x for x in (row.get("address", ""), city, row.get("state", ""),
                                 row.get("postal_code", "")) if x)
    policy = (row.get("pet_policy") or "").strip()
    spec = MediaSpec(category=category, label=name, sublabel="%s, OH" % city)
    active = {"pet-friendly-parks": "parks", "pet-friendly-restaurants": "restaurants"}.get(category_slug, "")
    label = {"pet-friendly-parks": "Pet-friendly parks",
             "pet-friendly-restaurants": "Pet-friendly restaurants"}[category_slug]
    src_host = re.sub(r"^https?://(www\.)?", "", row.get("source_url", "") or row.get("website_url", "")).rstrip("/")
    evidence = ('<div class="pt-note"><b>What we checked:</b> %s welcomes pets according to its own '
                'published information. <a rel="nofollow noopener external" target="_blank" href="%s">'
                'View the source %s</a></div>'
                % (_e(place_type.lower()), _e(row.get("source_url", "") or row.get("website_url", "")), IC_ARROW)
                ) if (row.get("source_url") or row.get("website_url")) else ""
    body = (
        '<div class="pt-container" style="padding-top:22px">%s</div>'
        '<section class="pt-section--tight"><div class="pt-container">'
        '<div class="pt-explore" style="align-items:start">'
        '<div class="pt-explore-map">%s</div>'
        '<div><span class="pt-card-area">%s, OH &middot; %s</span>'
        '<h1 class="pt-h2" style="margin:6px 0 12px">%s</h1>'
        '%s%s'
        '<p style="margin:14px 0 0;color:var(--ink-2)"><b>Address.</b> %s'
        ' &middot; <a href="%s" rel="nofollow noopener">Get directions %s</a></p>'
        '<div style="display:flex;flex-wrap:wrap;gap:12px;margin-top:22px">'
        '<a class="btn btn-ever" href="%s" rel="nofollow noopener">Visit official site</a>'
        '<a class="btn btn-ghost" href="/%s/">More %s %s</a></div>'
        '</div></div>%s</div></section>'
    ) % (crumbs([("PetTripFinder", "/"), (label, "/%s/" % category_slug), (name, "")], on_dark=False),
         render_media(spec, ratio="4x3", variant="card"),
         _e(city), _e(place_type), _e(name),
         ('<p style="font-size:17.5px;color:var(--ink-2);margin:0 0 6px">%s</p>' % _e(policy)) if policy else "",
         evidence, _e(addr), go_directions, IC_ARROW, go_official, category_slug, label.lower(), IC_ARROW,
         nearby_html)
    return theme.page(
        title="%s — Pet-Friendly in Columbus | PetTripFinder" % name,
        description=(re.sub("<[^>]+>", "", policy)[:180] or
                     "%s in Columbus, Ohio welcomes pets. See details on PetTripFinder." % name),
        route="/%s/%s/" % (category_slug, _slug(name)), body=body, active=active,
        head_extra=head_extra, css_href="/styles.css")


# --------------------------------------------------------------------------- #
# Comparison.
# --------------------------------------------------------------------------- #

_CMP_COLS = (("area", "Area"), ("species", "Pets accepted"), ("fee", "Fee"),
             ("fee_basis", "Fee basis"), ("count", "Max pets"),
             ("weight", "Weight limit"), ("verified_at", "Verified"))


def render_comparison(*, rows: Sequence[Dict], head_extra: str = "") -> str:
    header = "".join('<th scope="col">%s</th>' % _e(l) for _, l in _CMP_COLS)
    body_rows = []
    for r in sorted(rows, key=lambda x: x["name"].lower()):
        cells = ['<th scope="row"><a href="%s">%s</a></th>' % (r["route"], _e(r["name"]))]
        for key, _ in _CMP_COLS:
            v = (r.get(key) or "").strip()
            cells.append("<td>%s</td>" % (_e(v) if v else '<span class="pt-ns">Not stated</span>'))
        body_rows.append("<tr>%s</tr>" % "".join(cells))
    table = (
        '<div class="pt-table-wrap"><table class="pt-table">'
        '<caption>Verified pet-friendly hotel policies in Columbus, compared side by side. '
        'Fees and limits can change &mdash; always confirm with the hotel before booking.</caption>'
        '<thead><tr><th scope="col">Hotel</th>%s</tr></thead><tbody>%s</tbody></table></div>'
    ) % (header, "".join(body_rows))
    body = (
        '<div class="pt-pagehead"><div class="pt-container">%s'
        '<h1>Compare verified hotel pet policies</h1>'
        '<p class="pt-lead">Every row comes from that hotel&rsquo;s own official website, checked and '
        'quoted directly &mdash; never estimated. Blank values show &ldquo;Not stated&rdquo; rather than '
        'a guess.</p></div></div>'
        '<section class="pt-section--tight"><div class="pt-container">%s</div></section>'
    ) % (crumbs([("PetTripFinder", "/"), ("Pet-friendly hotels", "/pet-friendly-hotels/"),
                 ("Compare policies", "")]), table)
    return theme.page(
        title="Hotel Pet Policy Comparison | PetTripFinder Columbus",
        description=("Compare verified pet fees, weight limits, and pet counts across every "
                     "evidence-backed pet-friendly hotel in Columbus, Ohio."),
        route="/pet-friendly-hotels/policy-comparison/", body=body, active="compare",
        head_extra=head_extra, css_href="/styles.css")


# --------------------------------------------------------------------------- #
# Corridor.
# --------------------------------------------------------------------------- #

def render_corridor(*, corridor_name: str, corridor_slug: str, cards: Sequence[Dict],
                    head_extra: str = "") -> str:
    grid = "".join(hotel_card(**c) for c in cards)
    route = "/pet-friendly-hotels/%s/" % corridor_slug
    body = (
        '<div class="pt-pagehead"><div class="pt-container">%s'
        '<h1>Pet-friendly hotels in %s</h1>'
        '<p class="pt-lead">%d verified pet-friendly hotels in the %s area, each linking to its full, '
        'evidence-backed pet policy.</p></div></div>'
        '<section class="pt-section--tight"><div class="pt-container">'
        '<div class="pt-grid pt-grid--3">%s</div></div></section>'
    ) % (crumbs([("PetTripFinder", "/"), ("Pet-friendly hotels", "/pet-friendly-hotels/"),
                 (corridor_name, "")]), _e(corridor_name), len(cards), _e(corridor_name), grid)
    return theme.page(
        title="Pet-Friendly Hotels in %s | PetTripFinder Columbus" % corridor_name,
        description=("Verified pet-friendly hotels in the %s area of Columbus, Ohio, with real pet "
                     "fees and policies from each hotel's own website." % corridor_name),
        route=route, body=body, active="hotels", head_extra=head_extra, css_href="/styles.css")


# --------------------------------------------------------------------------- #
# Methodology (editorial).
# --------------------------------------------------------------------------- #

def render_methodology(*, head_extra: str = "") -> str:
    prose = (
        '<p class="pt-lead" style="margin-bottom:1.4em">PetTripFinder verifies pet policies directly '
        'from each business&rsquo;s own official website. When a listing is marked '
        '<strong>Policy verified</strong>, we fetched the official page, found the exact sentence '
        'stating the pet policy, and recorded the fee, pet count, weight limit, and restrictions '
        'exactly as written &mdash; never estimated or inferred from a name, category, or reputation.</p>'
        '<h2>What each status means</h2><ul>'
        '<li><strong>Policy verified</strong> &mdash; the pet policy shown was read directly from the '
        'business&rsquo;s own official website on the date shown.</li>'
        '<li><strong>Verified: pets not accepted</strong> &mdash; the official website explicitly states '
        'pets are not allowed. This is distinct from a service-animal policy, a separate legal category '
        'we never treat as a pet-acceptance signal.</li>'
        '<li><strong>Policy not independently verified</strong> &mdash; we have identified and listed the '
        'business, but have not yet confirmed its pet policy from an official source.</li></ul>'
        '<h2>What we never do</h2><ul>'
        '<li>We never mark a business pet-friendly from its brand, category, or marketing language alone.</li>'
        '<li>We never use third-party directories or review sites as pet-policy evidence &mdash; only the '
        'business&rsquo;s own official page.</li>'
        '<li>We never fabricate a fee, weight limit, or pet count. Unstated fields show '
        '<span class="pt-ns">Not stated</span>, never a default or estimate.</li></ul>'
        '<h2>Freshness and corrections</h2>'
        '<p>Pet policies can change. Every verified listing shows the date it was checked. If you find a '
        'policy that has changed, use the <strong>Report an outdated or incorrect policy</strong> link on '
        'that listing&rsquo;s page.</p>'
        '<h2 id="photos">Photos</h2>'
        '<p>We only show a property photograph when we have the right to publish one. Until a property '
        'supplies or licenses an image, we display an intentional branded placeholder rather than a stock '
        'or third-party photo &mdash; a placeholder never implies anything about the property beyond its '
        'verified pet policy.</p>'
        '<h2>Limitations</h2>'
        '<p>Some official hotel-chain websites actively block automated access; for those properties we '
        'list identifying information but do not display an unverified pet policy. We do not attempt to '
        'bypass these blocks.</p>'
    )
    body = (
        '<div class="pt-pagehead"><div class="pt-container">%s'
        '<h1>How PetTripFinder verifies pet policies</h1>'
        '<p class="pt-lead">Real evidence, honest gaps, and a checked date on every claim.</p>'
        '</div></div>'
        '<section class="pt-section--tight"><div class="pt-container">'
        '<div class="pt-prose">%s</div></div></section>'
    ) % (crumbs([("PetTripFinder", "/"), ("How we verify", "")]), prose)
    return theme.page(
        title="Our Methodology | PetTripFinder",
        description=("How PetTripFinder verifies pet policies directly from official business websites, "
                     "and what each verification status means."),
        route="/methodology/", body=body, active="verify", head_extra=head_extra, css_href="/styles.css")


def _editorial(*, title: str, lead: str, prose: str, route: str, description: str,
               active: str = "", head_extra: str = "") -> str:
    body = (
        '<div class="pt-pagehead"><div class="pt-container">%s'
        '<h1>%s</h1><p class="pt-lead">%s</p></div></div>'
        '<section class="pt-section--tight"><div class="pt-container">'
        '<div class="pt-prose">%s</div></div></section>'
    ) % (crumbs([("PetTripFinder", "/"), (title, "")]), _e(title), lead, prose)
    return theme.page(title="%s | PetTripFinder" % title, description=description, route=route,
                      body=body, active=active, head_extra=head_extra, css_href="/styles.css")


def render_about(*, head_extra: str = "") -> str:
    prose = (
        '<p class="pt-lead" style="margin-bottom:1.4em">PetTripFinder is a verified pet-travel guide. '
        'We help people traveling with a dog or cat find places that genuinely welcome them &mdash; '
        'starting in Columbus, Ohio.</p>'
        '<h2>Why we exist</h2>'
        '<p>&ldquo;Pet-friendly&rdquo; is one of the most abused phrases in travel. A listing says '
        '&ldquo;pets allowed,&rdquo; you drive across the state, and at check-in you learn about a fee, '
        'a weight limit, or a &ldquo;dogs only&rdquo; rule nobody mentioned. We built PetTripFinder so the '
        'real policy is on the page before you book.</p>'
        '<h2>How we&rsquo;re different</h2>'
        '<p>Every verified hotel policy on PetTripFinder is read directly from that property&rsquo;s own '
        'official website &mdash; the exact fee, pet limit, weight limit, and which animals are welcome. '
        'When a source doesn&rsquo;t state something, we say so, rather than guessing. Read the full '
        '<a href="/methodology/">verification methodology</a>.</p>'
        '<h2>What&rsquo;s next</h2>'
        '<p>Columbus is our first city. As we verify more properties &mdash; and add authorized '
        'photography &mdash; you&rsquo;ll see the guide grow, always on the same evidence-first footing.</p>'
    )
    return _editorial(
        title="About PetTripFinder",
        lead="A verified pet-travel guide that shows the real policy before you book.",
        prose=prose, route="/about/",
        description="PetTripFinder is a verified pet-travel guide showing real, evidence-backed pet "
                    "policies for hotels, parks, and restaurants — starting in Columbus, Ohio.",
        active="", head_extra=head_extra)


def render_contact(*, head_extra: str = "") -> str:
    prose = (
        '<p class="pt-lead" style="margin-bottom:1.4em">We&rsquo;d love to hear from you &mdash; whether '
        'you spotted a policy that changed, run a pet-friendly business, or just have a question.</p>'
        '<h2>Report an outdated policy</h2>'
        '<p>Pet policies change. If a verified listing looks out of date, use the '
        '<strong>Report an outdated or incorrect policy</strong> link on that listing&rsquo;s page &mdash; '
        'it tells us exactly which property and detail to re-check.</p>'
        '<h2>Business owners</h2>'
        '<p>If you own or manage a pet-friendly hotel, park, or restaurant in Columbus and want your '
        'current policy reflected accurately, let us know where your official pet policy is published and '
        'we&rsquo;ll verify it from the source.</p>'
        '<h2>General questions</h2>'
        '<p>For anything else, see <a href="/methodology/">how we verify</a> or '
        '<a href="/about/">about PetTripFinder</a>. We keep this guide deliberately small and honest, '
        'and we read every note.</p>'
    )
    return _editorial(
        title="Contact PetTripFinder",
        lead="Corrections, business listings, and questions &mdash; we read every note.",
        prose=prose, route="/contact/",
        description="Contact PetTripFinder to report an outdated pet policy, list a pet-friendly "
                    "business, or ask a question about our Columbus pet-travel guide.",
        active="", head_extra=head_extra)
