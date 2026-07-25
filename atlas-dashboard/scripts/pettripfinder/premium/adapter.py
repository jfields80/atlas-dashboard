"""PetTripFinder — adapters that build reusable Atlas Directory view models from
PetTripFinder's pet data + copy. All pet-policy field logic and Columbus copy
live here; the reusable renderers hold none of it. No fact is invented: values
are copied through from the committed package / seed data, or omitted as
"Not stated".
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Sequence, Tuple

from scripts.atlas_directory.viewmodels import (
    Action, Badge, CardVM, CategoryCardVM, ComparisonVM, Crumb, EditorialVM,
    ExploreItemVM, ExploreVM, FactChip, HeroVM, HomeVM, ListingVM, MediaSpec,
    NearbyGroupVM, PageHeadVM, ProfileVM, SearchFieldVM, SearchVM, SectionVM,
    StatVM, VerifyVM, VsColumnVM,
)
from scripts.atlas_directory.config import (
    FAMILY_BRAND, FAMILY_CITY, FAMILY_NATURE, FAMILY_PRIMARY, FAMILY_WARM,
)
from scripts.atlas_directory.pages import IC_PIN, IC_ARROW
from scripts.pettripfinder.premium import config as ptf
from scripts.pettripfinder.hotel_profile import _corridor_area, _friendly_date, _initials
from scripts.pettripfinder.structured_data import (
    breadcrumb_ld, item_list_ld, place_ld, restaurant_ld, to_script_tag,
)

BASE_URL = ptf.BASE_URL
_IC_PAW = ('<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" '
           'stroke-linecap="round" stroke-linejoin="round"><circle cx="5.5" cy="12.5" r="1.8"/>'
           '<circle cx="9.5" cy="7.5" r="1.8"/><circle cx="14.5" cy="7.5" r="1.8"/>'
           '<circle cx="18.5" cy="12.5" r="1.8"/>'
           '<path d="M12 12c-2.5 0-5 2-5 4.5C7 18.5 9 20 12 20s5-1.5 5-3.5C17 14 14.5 12 12 12Z"/></svg>')


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").strip().lower()).strip("-")


def _e(s: str) -> str:
    import html
    return html.escape(s or "", quote=False)


# --------------------------------------------------------------------------- #
# Hotel cards (pet-policy chips are PetTripFinder-specific).
# --------------------------------------------------------------------------- #

def hotel_card_dict(row: Dict, facts_entry: Optional[Dict]) -> Dict:
    name = row["name"]
    f = (facts_entry or {}).get("facts", {}) if facts_entry else {}
    return dict(
        name=name,
        area=_corridor_area(row.get("city", ""), row.get("address", ""), name),
        route="/pet-friendly-hotels/%s/" % _slug(name),
        verified_at=_friendly_date((facts_entry or {}).get("verified_at", "")) if facts_entry else "",
        facts=f,
        initials=_initials(name),
    )


def featured_order(cards: List[Dict]) -> List[Dict]:
    def richness(c: Dict) -> Tuple:
        f = c["facts"]
        return (-1 if f.get("pet_fee") else 0,
                -sum(1 for k in ("species_allowed", "pet_count_limit", "weight_limit") if f.get(k)),
                c["name"].lower())
    return sorted(cards, key=richness)


def _hotel_chips(f: Dict[str, str]) -> Tuple[FactChip, ...]:
    sp = (f.get("species_allowed") or "").lower()
    sparse = not any(f.get(k) for k in ("species_allowed", "pet_fee", "pet_count_limit", "weight_limit"))
    if sparse:
        return (FactChip("<b>Pets welcome</b>"), FactChip("Details not stated", dim=True))
    chips: List[FactChip] = []
    if "dog" in sp and "cat" in sp:
        chips.append(FactChip("Dogs &amp; cats"))
    elif "dog" in sp:
        chips.append(FactChip("Dogs <b>accepted</b>"))
    elif "cat" in sp:
        chips.append(FactChip("Cats <b>accepted</b>"))
    else:
        chips.append(FactChip("Pets welcome"))
    if f.get("pet_fee"):
        basis = (f.get("fee_basis") or "").replace("per room ", "").replace("per ", "/")
        chips.append(FactChip("Fee <b>%s</b>%s" % (_e(f["pet_fee"]), (" " + _e(basis)) if basis else "")))
    else:
        chips.append(FactChip("Fee not stated", dim=True))
    if f.get("pet_count_limit"):
        chips.append(FactChip("Up to <b>%s</b> pets" % _e(f["pet_count_limit"])))
    elif f.get("weight_limit"):
        chips.append(FactChip("Under <b>%s</b>" % _e(f["weight_limit"])))
    return tuple(chips[:3])


def hotel_card_vm(c: Dict) -> CardVM:
    return CardVM(
        title=c["name"], route=c["route"], area_label=c["area"],
        media=MediaSpec(family=FAMILY_PRIMARY, label=c["name"].split(" Columbus")[0].strip() or c["name"],
                        initials=c["initials"]),
        badge=Badge("Verified policy", "ok"),
        chips=_hotel_chips(c["facts"]),
        footnote=("Verified " + c["verified_at"]) if c["verified_at"] else "",
        link_label="View pet policy")


# --------------------------------------------------------------------------- #
# Place cards / profiles.
# --------------------------------------------------------------------------- #

def place_card_vm(row: Dict, category_slug: str) -> CardVM:
    cat = ptf.category_by_slug(category_slug)
    name = row["name"]
    policy = (row.get("pet_policy") or "").strip()
    if len(policy) > 150:
        policy = policy[:147].rsplit(" ", 1)[0] + "…"
    body = ('<p style="margin:0;color:var(--ink-2);font-size:14.5px">%s</p>' % _e(policy)) if policy else ""
    return CardVM(
        title=name, route="/%s/%s/" % (category_slug, _slug(name)),
        area_label="%s, OH" % row.get("city", ""),
        media=MediaSpec(family=cat.media_family, glyph=cat.glyph, label=name,
                        sublabel="%s, OH" % row.get("city", "")),
        badge=Badge("Pet-welcoming", "ok"), body_html=body)


def place_profile_vm(row: Dict, category_slug: str, place_type: str, *, go_official: str,
                     go_directions: str, nearby: Tuple[NearbyGroupVM, ...]) -> ProfileVM:
    cat = ptf.category_by_slug(category_slug)
    name = row["name"]
    city = row.get("city", "")
    addr = ", ".join(x for x in (row.get("address", ""), city, row.get("state", ""),
                                 row.get("postal_code", "")) if x)
    policy = (row.get("pet_policy") or "").strip()
    src = row.get("source_url", "") or row.get("website_url", "")
    intro = ('<p style="font-size:17.5px;color:var(--ink-2);margin:0 0 6px">%s</p>' % _e(policy)) if policy else ""
    evidence = ('<div class="pt-note"><b>What we checked:</b> %s welcomes pets according to its own '
                'published information. <a rel="nofollow noopener external" target="_blank" href="%s">'
                'View the source %s</a></div>' % (_e(place_type.lower()), _e(src), IC_ARROW)) if src else ""
    detail = ('<p style="margin:14px 0 0;color:var(--ink-2)"><b>Address.</b> %s &middot; '
              '<a href="%s" rel="nofollow noopener">Get directions %s</a></p>'
              % (_e(addr), go_directions, IC_ARROW))
    return ProfileVM(
        crumbs=(Crumb("PetTripFinder", "/"), Crumb(_cat_plural(category_slug), "/%s/" % category_slug),
                Crumb(name)),
        area_label=city, kind_label=place_type, title=name,
        media=MediaSpec(family=cat.media_family, glyph=cat.glyph, label=name, sublabel="%s, OH" % city),
        intro_html=intro, evidence_html=evidence, detail_html=detail,
        actions=(Action("Visit official site", go_official, "ever", rel="nofollow noopener"),
                 Action("More %s" % _cat_plural(category_slug).lower(), "/%s/" % category_slug, "ghost")),
        nearby=nearby,
        meta_description=(re.sub("<[^>]+>", "", policy)[:180] or
                          "%s in Columbus, Ohio welcomes pets. See details on PetTripFinder." % name),
        route="/%s/%s/" % (category_slug, _slug(name)),
        active_nav=cat.key, title_tag="%s — Pet-Friendly in Columbus | PetTripFinder" % name)


def _cat_plural(category_slug: str) -> str:
    return {"pet-friendly-parks": "Pet-friendly parks",
            "pet-friendly-restaurants": "Pet-friendly restaurants"}.get(category_slug, "Listings")


def nearby_groups(specs: Sequence[Tuple[str, str, Sequence[Dict]]]) -> Tuple[NearbyGroupVM, ...]:
    out = []
    for title, cat_slug, rows in specs:
        if not rows:
            continue
        items = tuple(ExploreItemVM(r["name"], "Also in %s, OH" % r.get("city", ""),
                                    "/%s/%s/" % (cat_slug, _slug(r["name"]))) for r in rows)
        out.append(NearbyGroupVM(title, items))
    return tuple(out)


# --------------------------------------------------------------------------- #
# Comparison (pet columns are PetTripFinder-specific).
# --------------------------------------------------------------------------- #

COMPARISON_COLUMNS = (("area", "Area"), ("species", "Pets accepted"), ("fee", "Fee"),
                      ("fee_basis", "Fee basis"), ("count", "Max pets"),
                      ("weight", "Weight limit"), ("verified_at", "Verified"))


def comparison_row(row: Dict, facts_entry: Optional[Dict]) -> Dict:
    f = (facts_entry or {}).get("facts", {}) if facts_entry else {}
    return dict(
        name=row["name"], route="/pet-friendly-hotels/%s/" % _slug(row["name"]),
        area="%s, %s" % (row.get("city", ""), row.get("state", "")),
        species=f.get("species_allowed", ""), fee=f.get("pet_fee", ""),
        fee_basis=f.get("fee_basis", ""), count=f.get("pet_count_limit", ""),
        weight=f.get("weight_limit", ""),
        verified_at=_friendly_date((facts_entry or {}).get("verified_at", "")) if facts_entry else "")


# --------------------------------------------------------------------------- #
# JSON-LD heads.
# --------------------------------------------------------------------------- #

def place_profile_head(row: Dict, category_slug: str, place_type: str) -> str:
    route = "/%s/%s/" % (category_slug, _slug(row["name"]))
    builder = place_ld if place_type == "Park" else restaurant_ld
    return to_script_tag([
        breadcrumb_ld(BASE_URL, [("PetTripFinder", "/"), (_cat_plural(category_slug), "/%s/" % category_slug),
                                 (row["name"], route)]),
        builder(base_url=BASE_URL, route=route, name=row["name"], street=row.get("address", ""),
                city=row.get("city", ""), state=row.get("state", ""),
                postal_code=row.get("postal_code", ""), official_url=row.get("website_url", ""))])


def listing_head(category_slug: str, rows: List[Dict], label: str) -> str:
    route = "/%s/" % category_slug
    entries = [(r["name"], "%s%s/" % (route, _slug(r["name"]))) for r in rows]
    return to_script_tag([breadcrumb_ld(BASE_URL, [("PetTripFinder", "/"), (label, route)]),
                          item_list_ld(BASE_URL, label, entries)])


# --------------------------------------------------------------------------- #
# Home view model (all PetTripFinder / Columbus copy).
# --------------------------------------------------------------------------- #

def build_home_vm(*, hotel_count: int, park_count: int, restaurant_count: int,
                  latest_verified_date: str, featured: Sequence[Dict],
                  corridors: Sequence[Dict]) -> HomeVM:
    hero = HeroVM(
        location_label="Columbus, Ohio",
        headline="Travel anywhere with your pet, without the check-in surprises.",
        subcopy=("PetTripFinder verifies each hotel’s pet policy directly from its own official website "
                 "— the real fee, pet limit, and which animals are welcome — so you know before you book."),
        primary=Action("Browse verified hotels", "/pet-friendly-hotels/", "accent"),
        secondary=Action("How verification works", "/methodology/", "onhero"),
        trust_points=("Read from official sources", "Exact fees & limits", "Honest “Not stated”"),
        media=MediaSpec(family=FAMILY_CITY, label="Columbus, Ohio", sublabel="Pet-friendly city guide"),
        badge_value=str(hotel_count),
        badge_label="evidence-backed hotels, verified from official sources")
    search = SearchVM(
        fields=(
            SearchFieldVM("Destination", "static",
                          static_html="%s Columbus, Ohio <small>&middot; more cities coming</small>" % IC_PIN),
            SearchFieldVM("Traveling with", "chips", chips=(
                Action("Dog", "/pet-friendly-hotels/"),
                Action("Cat", "/pet-friendly-hotels/"),
                Action("Compare policies", "/pet-friendly-hotels/policy-comparison/"))),
        ),
        cta=Action("Find verified stays", "/pet-friendly-hotels/", "ever"),
        note=("Browse verified pet policies — PetTripFinder does not sell rooms or show live availability. "
              "You always book with the hotel or its official partner."))
    # NB: StatVM labels are plain text (the reusable renderer escapes them), so use
    # literal characters here, never HTML entities.
    stats = (StatVM(str(hotel_count), "Verified pet-friendly hotels"),
             StatVM(str(park_count), "Dog parks & green spaces"),
             StatVM(str(restaurant_count), "Pet-welcoming restaurants"),
             StatVM("100%", "Read from official sources"))
    featured_cards = tuple(hotel_card_vm(c) for c in list(featured)[:6])
    mono = "PT"   # PetTripFinder brand mark for decorative (label-less) tiles
    cats = (
        CategoryCardVM("Verified hotels", "%d hotels with evidence-backed pet policies." % hotel_count,
                       "/pet-friendly-hotels/", MediaSpec(family=FAMILY_PRIMARY, glyph="home", initials=mono)),
        CategoryCardVM("Dog parks", "%d parks & green spaces to run and play." % park_count,
                       "/pet-friendly-parks/", MediaSpec(family=FAMILY_NATURE, glyph="leaf", initials=mono)),
        CategoryCardVM("Pet-friendly dining", "%d patios & taprooms that welcome dogs." % restaurant_count,
                       "/pet-friendly-restaurants/", MediaSpec(family=FAMILY_WARM, glyph="fork", initials=mono)),
        CategoryCardVM("Compare policies", "Fees, limits & species side by side.",
                       "/pet-friendly-hotels/policy-comparison/",
                       MediaSpec(family=FAMILY_BRAND, glyph="brand", initials=mono)),
    )
    verify = VerifyVM(
        head=SectionVM("Why it's different",
                       "Not just “pets allowed.” The actual policy.",
                       "Most listings stop at two vague words. We read each property’s own official page "
                       "and record exactly what it says — and honestly mark what it doesn’t.", center=True),
        generic=VsColumnVM("Typical listing",
                           ("Pets allowed", "No fee or limit given", "Which animals? Unclear",
                            "“Call to confirm”"), positive=False),
        ours=VsColumnVM("PetTripFinder",
                        ("Dogs accepted · Cats not stated (never guessed)",
                         "Exact fee &amp; fee basis, quoted from the source",
                         "Weight &amp; pet limits reported honestly",
                         "Service animals kept separate, with a checked date"), positive=True),
        cta=Action("Read our full methodology", "/methodology/", "ghost"))
    explore = ExploreVM(
        head=SectionVM("Explore the city", "Plan a Columbus pet trip",
                       "Columbus is compact and dog-friendly. Start from a %s near your plans, then pair a "
                       "verified hotel with nearby parks and patios." % ptf.CONFIG.geo_term.singular),
        media=MediaSpec(family=FAMILY_CITY, label="Columbus corridors",
                        sublabel="Downtown · Dublin · Polaris · Grove City"),
        items=tuple(ExploreItemVM(c["name"], "%d verified %s" % (c["count"], "hotel" if c["count"] == 1 else "hotels"),
                                  c["route"]) for c in corridors)
              or (ExploreItemVM("All Columbus hotels", "%d verified stays" % hotel_count,
                                "/pet-friendly-hotels/"),))
    from scripts.atlas_directory.viewmodels import CtaBandVM
    cta_band = CtaBandVM(
        headline="Your next trip, planned around your pet.",
        sub="Compare verified pet policies, then book the stay that actually welcomes your dog or cat.",
        actions=(Action("Browse verified hotels", "/pet-friendly-hotels/", "accent"),
                 Action("Compare policies", "/pet-friendly-hotels/policy-comparison/", "onhero")),
        media=MediaSpec(family=FAMILY_PRIMARY, initials="PT"))
    return HomeVM(
        hero=hero, search=search, stats=stats,
        featured_head=SectionVM("Where to stay", "Featured verified stays",
                                "A hand-checked look at Columbus hotels whose pet policies we read directly "
                                "from the source. Every fee and limit below is quoted — never estimated."),
        featured_cards=featured_cards,
        featured_cta=Action("See all verified hotels", "/pet-friendly-hotels/", "ghost"),
        categories_head=SectionVM("Plan the trip", "Browse by trip need"),
        categories=cats, verify=verify, explore=explore, cta_band=cta_band)
