"""PetTripFinder — thin page delegators over the reusable Atlas Directory kit.

These keep the exact public API the Columbus generator calls, but hold only
PetTripFinder copy + configuration: they build reusable view models (via
``adapter``) and render them through ``scripts.atlas_directory.pages`` with the
PetTripFinder ``DirectoryConfig``. No layout or component logic lives here.
"""

from __future__ import annotations

from typing import Dict, Sequence, Tuple

from scripts.atlas_directory import pages as ad
from scripts.atlas_directory.viewmodels import (
    Crumb, EditorialVM, ListingVM, PageHeadVM, ComparisonVM, NearbyGroupVM,
)
from scripts.pettripfinder.premium import adapter
from scripts.pettripfinder.premium import config as ptf

CONFIG = ptf.CONFIG


# --------------------------------------------------------------------------- #
# Home.
# --------------------------------------------------------------------------- #

def render_home(*, hotel_count: int, park_count: int, restaurant_count: int,
                latest_verified_date: str, featured: Sequence[Dict],
                corridors: Sequence[Dict], head_extra: str = "") -> str:
    vm = adapter.build_home_vm(
        hotel_count=hotel_count, park_count=park_count, restaurant_count=restaurant_count,
        latest_verified_date=latest_verified_date, featured=featured, corridors=corridors)
    return ad.render_home(
        CONFIG, vm, head_extra=head_extra,
        title="Pet-Friendly Travel in Columbus, Ohio | PetTripFinder",
        description=("Verified pet-friendly hotels, dog parks, and restaurants in Columbus, Ohio. "
                     "Every hotel pet policy is read straight from the property's own official "
                     "website — real fees, limits, and species, never guessed."))


# --------------------------------------------------------------------------- #
# Listings.
# --------------------------------------------------------------------------- #

def render_hotel_listing(*, cards: Sequence[Dict], hotel_count: int,
                         latest_verified_date: str, head_extra: str = "") -> str:
    vm = ListingVM(
        head=PageHeadVM(
            crumbs=(Crumb("PetTripFinder", "/"), Crumb("Pet-friendly hotels")),
            title="Verified pet-friendly hotels in Columbus, Ohio",
            lead=("%d hotels whose pet policy we read directly from the property’s own official website "
                  "— the real fee, pet limit, and which animals are welcome. Most recently verified %s."
                  % (hotel_count, latest_verified_date))),
        note_html=("Every policy below is quoted from an official source. Where a source doesn’t state a "
                   "value, we show &ldquo;Not stated&rdquo; rather than guess. "
                   '<a href="/pet-friendly-hotels/policy-comparison/">Compare them side by side &rarr;</a>'),
        cards=tuple(adapter.hotel_card_vm(c) for c in cards))
    return ad.render_listing(
        CONFIG, vm, active="hotels", route="/pet-friendly-hotels/", head_extra=head_extra,
        title="Verified Pet-Friendly Hotels in Columbus, Ohio | PetTripFinder",
        description=("Browse %d Columbus hotels with evidence-backed pet policies — real fees, pet limits, "
                     "and species, read from each property's official website." % hotel_count))


def render_place_listing(*, category_slug: str, category: str, title: str, lead: str,
                         eyebrow_text: str, rows: Sequence[Dict], head_extra: str = "") -> str:
    import re
    label = {"pet-friendly-parks": "Pet-friendly parks",
             "pet-friendly-restaurants": "Pet-friendly restaurants"}.get(category_slug, "Listings")
    active = {"pet-friendly-parks": "parks", "pet-friendly-restaurants": "restaurants"}.get(category_slug, "")
    vm = ListingVM(
        head=PageHeadVM(crumbs=(Crumb("PetTripFinder", "/"), Crumb(title)), title=title, lead=lead),
        cards=tuple(adapter.place_card_vm(r, category_slug) for r in rows))
    return ad.render_listing(
        CONFIG, vm, active=active, route="/%s/" % category_slug, head_extra=head_extra,
        title="%s | PetTripFinder Columbus" % title,
        description=re.sub("<[^>]+>", "", lead)[:180])


# --------------------------------------------------------------------------- #
# Place profile.
# --------------------------------------------------------------------------- #

def nearby_block(specs) -> Tuple[NearbyGroupVM, ...]:
    return adapter.nearby_groups(specs)


def render_place_profile(*, row: Dict, category_slug: str, category: str, place_type: str,
                         go_official: str, go_directions: str,
                         nearby: Tuple[NearbyGroupVM, ...] = (), head_extra: str = "") -> str:
    vm = adapter.place_profile_vm(row, category_slug, place_type, go_official=go_official,
                                  go_directions=go_directions, nearby=nearby)
    return ad.render_profile(CONFIG, vm, head_extra=head_extra)


# --------------------------------------------------------------------------- #
# Comparison / corridor.
# --------------------------------------------------------------------------- #

def render_comparison(*, rows: Sequence[Dict], head_extra: str = "") -> str:
    vm = ComparisonVM(
        head=PageHeadVM(
            crumbs=(Crumb("PetTripFinder", "/"), Crumb("Pet-friendly hotels", "/pet-friendly-hotels/"),
                    Crumb("Compare policies")),
            title="Compare verified hotel pet policies",
            lead=("Every row comes from that hotel’s own official website, checked and quoted directly — "
                  "never estimated. Blank values show &ldquo;Not stated&rdquo; rather than a guess.")),
        identity_label="Hotel", columns=adapter.COMPARISON_COLUMNS, rows=tuple(rows),
        caption=("Verified pet-friendly hotel policies in Columbus, compared side by side. Fees and limits "
                 "can change — always confirm with the hotel before booking."))
    return ad.render_comparison(
        CONFIG, vm, active="compare", route="/pet-friendly-hotels/policy-comparison/", head_extra=head_extra,
        title="Hotel Pet Policy Comparison | PetTripFinder Columbus",
        description=("Compare verified pet fees, weight limits, and pet counts across every "
                     "evidence-backed pet-friendly hotel in Columbus, Ohio."))


def render_corridor(*, corridor_name: str, corridor_slug: str, cards: Sequence[Dict],
                    head_extra: str = "") -> str:
    vm = ListingVM(
        head=PageHeadVM(
            crumbs=(Crumb("PetTripFinder", "/"), Crumb("Pet-friendly hotels", "/pet-friendly-hotels/"),
                    Crumb(corridor_name)),
            title="Pet-friendly hotels in %s" % corridor_name,
            lead=("%d verified pet-friendly hotels in the %s area, each linking to its full, "
                  "evidence-backed pet policy." % (len(cards), corridor_name))),
        cards=tuple(adapter.hotel_card_vm(c) for c in cards))
    return ad.render_listing(
        CONFIG, vm, active="hotels", route="/pet-friendly-hotels/%s/" % corridor_slug, head_extra=head_extra,
        title="Pet-Friendly Hotels in %s | PetTripFinder Columbus" % corridor_name,
        description=("Verified pet-friendly hotels in the %s area of Columbus, Ohio, with real pet fees "
                     "and policies from each hotel's own website." % corridor_name))


# --------------------------------------------------------------------------- #
# Editorial (methodology / about / contact) — PetTripFinder copy.
# --------------------------------------------------------------------------- #

def _editorial(head: PageHeadVM, prose: str, *, route: str, title: str, description: str,
               active: str = "", head_extra: str = "") -> str:
    return ad.render_editorial(CONFIG, EditorialVM(head=head, prose_html=prose), route=route,
                               title=title, description=description, active=active, head_extra=head_extra)


def render_methodology(*, head_extra: str = "") -> str:
    prose = (
        '<p class="pt-lead" style="margin-bottom:1.4em">PetTripFinder verifies pet policies directly '
        'from each business’s own official website. When a listing is marked '
        '<strong>Policy verified</strong>, we fetched the official page, found the exact sentence '
        'stating the pet policy, and recorded the fee, pet count, weight limit, and restrictions '
        'exactly as written — never estimated or inferred from a name, category, or reputation.</p>'
        '<h2>What each status means</h2><ul>'
        '<li><strong>Policy verified</strong> — the pet policy shown was read directly from the '
        'business’s own official website on the date shown.</li>'
        '<li><strong>Verified: pets not accepted</strong> — the official website explicitly states pets '
        'are not allowed. This is distinct from a service-animal policy, a separate legal category we '
        'never treat as a pet-acceptance signal.</li>'
        '<li><strong>Policy not independently verified</strong> — we have identified and listed the '
        'business, but have not yet confirmed its pet policy from an official source.</li></ul>'
        '<h2>What we never do</h2><ul>'
        '<li>We never mark a business pet-friendly from its brand, category, or marketing language alone.</li>'
        '<li>We never use third-party directories or review sites as pet-policy evidence — only the '
        'business’s own official page.</li>'
        '<li>We never fabricate a fee, weight limit, or pet count. Unstated fields show '
        '<span class="pt-ns">Not stated</span>, never a default or estimate.</li></ul>'
        '<h2>Freshness and corrections</h2>'
        '<p>Pet policies can change. Every verified listing shows the date it was checked. If you find a '
        'policy that has changed, use the <strong>Report an outdated or incorrect policy</strong> link on '
        'that listing’s page.</p>'
        '<h2 id="photos">Photos</h2>'
        '<p>We only show a property photograph when we have the right to publish one. Until a property '
        'supplies or licenses an image, we display an intentional branded placeholder rather than a stock '
        'or third-party photo — a placeholder never implies anything about the property beyond its '
        'verified pet policy.</p>'
        '<h2>Limitations</h2>'
        '<p>Some official hotel-chain websites actively block automated access; for those properties we '
        'list identifying information but do not display an unverified pet policy. We do not attempt to '
        'bypass these blocks.</p>')
    head = PageHeadVM(crumbs=(Crumb("PetTripFinder", "/"), Crumb("How we verify")),
                      title="How PetTripFinder verifies pet policies",
                      lead="Real evidence, honest gaps, and a checked date on every claim.")
    return _editorial(head, prose, route="/methodology/", active="verify",
                      title="Our Methodology | PetTripFinder",
                      description=("How PetTripFinder verifies pet policies directly from official business "
                                   "websites, and what each verification status means."), head_extra=head_extra)


def render_about(*, head_extra: str = "") -> str:
    prose = (
        '<p class="pt-lead" style="margin-bottom:1.4em">PetTripFinder is a verified pet-travel guide. '
        'We help people traveling with a dog or cat find places that genuinely welcome them — starting in '
        'Columbus, Ohio.</p>'
        '<h2>Why we exist</h2>'
        '<p>&ldquo;Pet-friendly&rdquo; is one of the most abused phrases in travel. A listing says '
        '&ldquo;pets allowed,&rdquo; you drive across the state, and at check-in you learn about a fee, a '
        'weight limit, or a &ldquo;dogs only&rdquo; rule nobody mentioned. We built PetTripFinder so the '
        'real policy is on the page before you book.</p>'
        '<h2>How we’re different</h2>'
        '<p>Every verified hotel policy on PetTripFinder is read directly from that property’s own official '
        'website — the exact fee, pet limit, weight limit, and which animals are welcome. When a source '
        'doesn’t state something, we say so, rather than guessing. Read the full '
        '<a href="/methodology/">verification methodology</a>.</p>'
        '<h2>What’s next</h2>'
        '<p>Columbus is our first city. As we verify more properties — and add authorized photography — '
        'you’ll see the guide grow, always on the same evidence-first footing.</p>')
    head = PageHeadVM(crumbs=(Crumb("PetTripFinder", "/"), Crumb("About PetTripFinder")),
                      title="About PetTripFinder",
                      lead="A verified pet-travel guide that shows the real policy before you book.")
    return _editorial(head, prose, route="/about/",
                      title="About PetTripFinder | PetTripFinder",
                      description=("PetTripFinder is a verified pet-travel guide showing real, evidence-backed "
                                   "pet policies for hotels, parks, and restaurants — starting in Columbus, "
                                   "Ohio."), head_extra=head_extra)


def render_contact(*, head_extra: str = "") -> str:
    prose = (
        '<p class="pt-lead" style="margin-bottom:1.4em">We’d love to hear from you — whether you spotted a '
        'policy that changed, run a pet-friendly business, or just have a question.</p>'
        '<h2>Report an outdated policy</h2>'
        '<p>Pet policies change. If a verified listing looks out of date, use the '
        '<strong>Report an outdated or incorrect policy</strong> link on that listing’s page — it tells us '
        'exactly which property and detail to re-check.</p>'
        '<h2>Business owners</h2>'
        '<p>If you own or manage a pet-friendly hotel, park, or restaurant in Columbus and want your current '
        'policy reflected accurately, let us know where your official pet policy is published and we’ll '
        'verify it from the source.</p>'
        '<h2>General questions</h2>'
        '<p>For anything else, see <a href="/methodology/">how we verify</a> or '
        '<a href="/about/">about PetTripFinder</a>. We keep this guide deliberately small and honest, and '
        'we read every note.</p>')
    head = PageHeadVM(crumbs=(Crumb("PetTripFinder", "/"), Crumb("Contact PetTripFinder")),
                      title="Contact PetTripFinder",
                      lead="Corrections, business listings, and questions — we read every note.")
    return _editorial(head, prose, route="/contact/",
                      title="Contact PetTripFinder | PetTripFinder",
                      description=("Contact PetTripFinder to report an outdated pet policy, list a "
                                   "pet-friendly business, or ask a question about our Columbus pet-travel "
                                   "guide."), head_extra=head_extra)
