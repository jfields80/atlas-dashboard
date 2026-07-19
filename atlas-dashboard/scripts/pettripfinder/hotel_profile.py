"""PTF-PROD-001 -- production hotel-profile renderer (narrow slice).

Translates the approved final-hybrid design authority
(design/prototypes/pettripfinder/ptf-design-001/final-hybrid/) into a
production, data-driven hotel-profile renderer. This is a narrow view-model
adapter + a single reusable render function -- NOT a new engine and NOT a
broadening of the AES-WEB component architecture (whose components remain
PROPOSED with unvalidated emitters). One template + one section order renders
all five verification states.

Doctrine preserved from the importer/site pipeline:
  * facts come only from repository-authorized verified evidence (READY
    candidates) or the promoted production CSV -- never invented;
  * an unstated field is shown as "Not stated by the reviewed source",
    never guessed and never rendered as "no";
  * VERIFIED_NO_PETS and POLICY_UNVERIFIED never use verified-pet-friendly
    styling or language;
  * no coordinates exist, so no distance/"nearby" is ever shown;
  * no internal HTTP/blocking/automation wording is ever exposed publicly.

No network. No provider calls. Reads production/candidate data, never writes
inventory or evidence.
"""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from scripts.pettripfinder.site_data import (
    normalize_name,
    read_production_rows,
)

REPO_ROOT = Path(__file__).resolve().parents[2]

STATE_VERIFIED = "VERIFIED_PET_FRIENDLY"
STATE_NO_PETS = "VERIFIED_NO_PETS"
STATE_UNVERIFIED = "POLICY_UNVERIFIED"

_MEDIA_CAP = 'Property photo unavailable. <a href="/methodology/#photos">How we handle photos</a>'
_NOT_STATED = "Not stated by the reviewed source"
_HOME_SVG = ('<svg class="glyph" width="34" height="34" viewBox="0 0 24 24" fill="none" '
             'stroke="#f6f1e7" stroke-width="1.4" aria-hidden="true">'
             '<path d="M3 21V9l9-5 9 5v12"/><path d="M9 21v-6h6v6"/><path d="M3 21h18"/></svg>')


def _e(s: str) -> str:
    return html.escape(s or "", quote=False)


_MONTHS = ("January", "February", "March", "April", "May", "June", "July",
           "August", "September", "October", "November", "December")


def _friendly_date(value: Optional[str]) -> str:
    """Render an ISO date (YYYY-MM-DD) as "Month D, YYYY" to match the approved
    design authority. Any non-ISO / empty value is returned unchanged."""
    if not value:
        return ""
    m = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", value.strip())
    if not m:
        return value
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return "%s %d, %d" % (_MONTHS[mo - 1], d, y)


def _cap_first(s: str) -> str:
    s = (s or "").strip()
    return (s[:1].upper() + s[1:]) if s else s


# --------------------------------------------------------------------------- #
# Authoritative display-corridor taxonomy (PTF-PROD-001A correction 1).
#
# Presentation-only. Deliberately NOT site_data.assign_corridor: that adapter's
# Downtown/Dublin grouping drives the >=5-property *indexable-corridor* logic
# used by the site build / reconciliation, and must keep its exact semantics.
# This produces the display label the approved design authority uses:
# "<Area> corridor · Columbus, OH", anchored to the Columbus market. A suburb
# city becomes "<City> corridor"; a Columbus-city hotel is placed into a named
# sub-area corridor by ADDRESS markers (never a marketing name), with an
# airport fallback used only when no street address is available.
# --------------------------------------------------------------------------- #

_DOWNTOWN_MARKERS = ("nationwide blvd", "state street", "capitol square")
_HIGH_ST_RE = re.compile(r"\b(\d{1,4})\s+(?:north|south|n|s)?\.?\s*high\s+st", re.I)
_METRO_ANCHOR = "Columbus, OH"


def _corridor_area(city: str, address: str, name: str = "") -> str:
    c = (city or "").strip()
    addr = (address or "").lower()
    if c.lower() == "columbus":
        if any(m in addr for m in _DOWNTOWN_MARKERS):
            return "Downtown corridor"
        m = _HIGH_ST_RE.search(addr)
        if m and int(m.group(1)) < 1000:
            return "Downtown corridor"
        if "west hilliard" in addr or "westbelt" in addr:
            return "West Hilliard corridor"
        if "polaris" in addr:
            return "Polaris corridor"
        if "airport" in addr:
            return "Airport corridor"
        if not addr and "airport" in (name or "").lower():
            return "Airport corridor"     # last-resort hint when no address exists
        return "Columbus corridor"
    if c:
        return "%s corridor" % c
    return "Columbus corridor"


def _corridor_label(city: str, address: str, name: str = "") -> str:
    return "%s · %s" % (_corridor_area(city, address, name), _METRO_ANCHOR)


def _related_fact(ff: Dict[str, str]) -> str:
    """One useful supported pet-policy fact for a related card, in priority
    order. "" when the source stated nothing usable -- never inferred."""
    if ff.get("pet_fee"):
        basis = ff.get("fee_basis")
        return "%s%s" % (ff["pet_fee"], (" " + basis) if basis else "")
    sp = (ff.get("species_allowed") or "").lower()
    if "dog" in sp and "cat" in sp:
        return "Dogs and cats accepted"
    if "cat" in sp:
        return "Cats accepted"
    if "dog" in sp:
        return "Dogs accepted"
    if ff.get("pet_count_limit"):
        return "Up to %s pets" % ff["pet_count_limit"]
    if ff.get("pets_allowed") == "true":
        return "Pets welcome"
    return ""


def _initials(name: str) -> str:
    words = re.sub(r"[^A-Za-z0-9 ]", " ", name or "").split()
    letters = [w[0] for w in words if w and w[0].isalpha()]
    return ("".join(letters[:2]) or "PT").upper()


# --------------------------------------------------------------------------- #
# View model.
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class RelatedHotel:
    name: str
    area: str
    fact: str          # one supported pet-policy fact, or "" (omitted)
    verified_at: str
    route: str


@dataclass(frozen=True)
class HotelProfileVM:
    state: str
    name: str
    corridor: str
    initials: str
    address: str
    phone: str
    official_url: str
    verified_at: Optional[str]
    source_name: Optional[str]
    summary: str
    facts: Tuple[Tuple[str, str, str], ...]           # (label, value, cls)
    verif_badge_text: str
    verif_badge_cls: str                               # ok | stop | neutral
    verif_chip: str                                    # short chip in media
    trust_cls: str
    trust_line: str
    evidence_quote: Optional[str]
    details_rows: Tuple[Tuple[str, str, str], ...] = ()   # (label, value, cls)
    details_plain: str = ""
    details_note: str = ""
    service_note: str = ""
    prov_status: str = ""                              # non-empty => unverified provenance
    actions_mode: str = "book"                         # book | alt | unverif
    related: Tuple[RelatedHotel, ...] = ()

    @property
    def media_state(self) -> str:
        return self.verif_badge_cls


# --------------------------------------------------------------------------- #
# Summary / facts / details composition (deterministic; evidence-only).
# --------------------------------------------------------------------------- #

def _species_phrase(species: str) -> str:
    sp = (species or "").lower()
    if "dog" in sp and "cat" in sp:
        return "Dogs and cats are accepted."
    if "dog" in sp:
        return "Dogs are accepted."
    if "cat" in sp:
        return "Cats are accepted."
    return "Pets are welcome."


def _verified_summary(f: Dict[str, str]) -> str:
    if not any(f.get(k) for k in ("species_allowed", "pet_fee", "pet_count_limit", "weight_limit")):
        return ("Pets are welcome. The reviewed official source did not state the species, "
                "fee, pet limit, or weight limit.")
    parts = [_species_phrase(f.get("species_allowed", ""))]
    fee, basis = f.get("pet_fee"), f.get("fee_basis")
    if fee:
        s = "A %s fee applies" % fee
        if basis:
            s += " %s" % basis.lower()
        parts.append(s + ".")
    tail = []
    if f.get("pet_count_limit"):
        tail.append("up to %s pets" % f["pet_count_limit"])
    if f.get("weight_limit"):
        tail.append("a combined weight limit of %s" % f["weight_limit"])
    if tail:
        parts.append(("Allowed " + " with ".join(tail) + ".").replace("Allowed up to", "Up to"))
    return " ".join(parts)


def _verified_facts(f: Dict[str, str]) -> Tuple[Tuple[str, str, str], ...]:
    sp = (f.get("species_allowed") or "").lower()
    sparse = not any(f.get(k) for k in ("species_allowed", "pet_fee", "pet_count_limit", "weight_limit"))
    dogs = ("Accepted", "yes") if "dog" in sp else (("Welcome", "yes") if sparse else ("Not stated", "dim"))
    cats = ("Accepted", "yes") if "cat" in sp else ("Not stated", "dim")
    def cell(v):
        return (v, "") if v else ("Not stated", "dim")
    return (
        ("Dogs", dogs[0], dogs[1]),
        ("Cats", cats[0], cats[1]),
        ("Pet charge", *cell(f.get("pet_fee"))),
        ("Charge basis", *(lambda v: (_cap_first(v), "sm") if v else ("Not stated", "dim"))(f.get("fee_basis"))),
        ("Max pets", *cell(f.get("pet_count_limit"))),
        ("Weight limit", *cell(f.get("weight_limit"))),
    )


def _verified_details(f: Dict[str, str]) -> Tuple[Tuple, str, str]:
    sparse = not any(f.get(k) for k in ("species_allowed", "pet_fee", "pet_count_limit", "weight_limit"))
    svc = "A separate legal access category — not treated as a pet-policy exception."
    if sparse:
        rows = (
            ("Accepted species", "Pets welcome (species not specified)", ""),
            ("Fee, pet limit, weight limit", _NOT_STATED, "dim"),
            ("Breed / unattended rules", _NOT_STATED, "dim"),
            ("Service animals", svc, ""),
        )
        note = ("“Not stated” means the reviewed source did not address the field — not that "
                "the answer is no. Confirm specifics with the property before booking.")
        return rows, "", note
    def d(v):
        return (v, "") if v else (_NOT_STATED, "dim")
    rows = (
        ("Accepted species", *(lambda v: (_cap_first(v), "") if v else (_NOT_STATED, "dim"))(f.get("species_allowed"))),
        ("Maximum pets", *(lambda v: (v + " per room", "") if v else (_NOT_STATED, "dim"))(f.get("pet_count_limit"))),
        ("Pet charge", *d(f.get("pet_fee"))),
        ("Charge basis", *(lambda v: (_cap_first(v), "") if v else (_NOT_STATED, "dim"))(f.get("fee_basis"))),
        ("Weight restriction", *d(f.get("weight_limit"))),
        ("Refundable deposit", *d(f.get("pet_deposit"))),
        ("Breed restrictions", *d(f.get("breed_restrictions"))),
        ("Unattended-pet rule", *d(f.get("unattended_policy"))),
        ("Service animals", svc, ""),
    )
    return rows, "", ""


# --------------------------------------------------------------------------- #
# Adapters.
# --------------------------------------------------------------------------- #

def _related_from_production(self_name: str, all_hotel_rows, facts_map, limit=3) -> Tuple[RelatedHotel, ...]:
    out = []
    for row in sorted(all_hotel_rows, key=lambda r: normalize_name(r["name"])):
        if normalize_name(row["name"]) == normalize_name(self_name):
            continue
        fe = facts_map.get(normalize_name(row["name"]))
        fact = _related_fact(fe["facts"]) if fe else ""
        date = _friendly_date((fe["verified_at"] if fe else "") or row.get("observed_at", ""))
        out.append(RelatedHotel(
            name=row["name"], area=_corridor_area(row.get("city", ""), row.get("address", ""), row["name"]),
            fact=fact, verified_at=date,
            route="/pet-friendly-hotels/%s/" % _slug(row["name"])))
        if len(out) >= limit:
            break
    return tuple(out)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").strip().lower()).strip("-")


def build_vm_from_production(row: Dict[str, str], facts_entry: Optional[Dict],
                            all_hotel_rows, facts_map) -> HotelProfileVM:
    """Verified pet-friendly VM from a production seed row + its READY-candidate
    facts. Rich when the candidate stated fee/species/limits; sparse when it
    stated only that pets are welcome. Never invents a field."""
    f = (facts_entry or {}).get("facts", {}) if facts_entry else {}
    date = _friendly_date((facts_entry or {}).get("verified_at", "") or row.get("observed_at", ""))
    rows, plain, note = _verified_details(f)
    # exact wording, carried on the fixture facts entry (committed, reproducible)
    quote = (facts_entry or {}).get("evidence_quote") if facts_entry else None
    return HotelProfileVM(
        state=STATE_VERIFIED, name=row["name"],
        corridor=_corridor_label(row.get("city", ""), row.get("address", ""), row["name"]),
        initials=_initials(row["name"]),
        address="%s, %s, %s %s" % (row.get("address", ""), row.get("city", ""), row.get("state", ""), row.get("postal_code", "")),
        phone=row.get("phone", ""), official_url=row.get("website_url", ""),
        verified_at=date, source_name="the official %s website" % _brand_of(row.get("website_url", "")),
        summary=_verified_summary(f),
        facts=_verified_facts(f),
        verif_badge_text="Policy verified · %s" % date, verif_badge_cls="ok", verif_chip="✓ Verified policy",
        trust_cls="ok",
        trust_line="Policy verified %s from %s." % (date, "the official %s website" % _brand_of(row.get("website_url", ""))),
        evidence_quote=quote,
        details_rows=rows, details_plain=plain, details_note=note,
        actions_mode="book",
        related=_related_from_production(row["name"], all_hotel_rows, facts_map))


def build_vm_from_no_pets(cand: Dict, all_hotel_rows, facts_map) -> HotelProfileVM:
    proposed = dict(cand.get("proposed_fields", []))
    name = proposed.get("name") or cand["context"]["candidate_name"]
    city = proposed.get("city") or cand["context"]["expected_city"]
    date = _friendly_date(cand.get("snapshot", {}).get("observed_at", ""))
    quote = next((e["snapshot_quote"] for e in cand.get("evidence", [])
                  if e["field_name"] == "pets_allowed"), None)
    facts = (
        ("Dogs", "Not accepted", "no"), ("Cats", "Not accepted", "no"),
        ("Pet charge", "Does not apply", "dim"), ("Charge basis", "Does not apply", "dim"),
        ("Max pets", "Does not apply", "dim"), ("Weight limit", "Does not apply", "dim"),
    )
    return HotelProfileVM(
        state=STATE_NO_PETS, name=name, corridor=_corridor_label(city, proposed.get("address", ""), name),
        initials=_initials(name),
        address="%s, %s, OH" % (proposed.get("address", ""), city),
        phone="", official_url=proposed.get("website_url", "") or cand.get("snapshot", {}).get("requested_url", ""),
        verified_at=date, source_name="the official property website",
        summary=("This property does <b>not</b> accept pets. We’re showing it so you can rule it "
                 "out and find a stay that welcomes your dog or cat."),
        facts=facts,
        verif_badge_text="Verified · Pets not accepted", verif_badge_cls="stop", verif_chip="Pets not accepted",
        trust_cls="stop",
        trust_line="Verified %s from the official property website: pets are not accepted." % date,
        evidence_quote=quote,
        details_plain=("Pets are not accepted at this property, so there is no fee, pet limit, or "
                       "weight allowance to show."),
        service_note=("The official source states service animals are welcome. Service animals are a "
                      "legal access category under the ADA — not a pet-policy exception — and we "
                      "never present them as one."),
        actions_mode="alt",
        related=_related_from_production(name, all_hotel_rows, facts_map))


def build_vm_from_unverified(cand: Dict, all_hotel_rows, facts_map) -> HotelProfileVM:
    name = cand["context"]["candidate_name"]
    city = cand["context"]["expected_city"]
    facts = tuple((lbl, "Not verified", "dim") for lbl in
                  ("Dogs", "Cats", "Pet charge", "Charge basis", "Max pets", "Weight limit"))
    return HotelProfileVM(
        state=STATE_UNVERIFIED, name=name, corridor=_corridor_label(city, "", name),
        initials=_initials(name),
        address="%s, OH" % city,
        phone="", official_url=cand.get("snapshot", {}).get("requested_url", ""),
        verified_at=None, source_name=None,
        summary=("We could not confirm this property’s current pet policy from an approved "
                 "official source."),
        facts=facts,
        verif_badge_text="Pet policy not verified", verif_badge_cls="neutral", verif_chip="Not verified",
        trust_cls="neutral",
        trust_line=("We could not confirm this property’s current pet policy from an approved "
                    "official source."),
        evidence_quote=None,
        details_plain=("No verified pet-policy details are available for this property. Please "
                       "confirm directly with the property before you travel with a pet."),
        prov_status="not verified",
        actions_mode="unverif",
        related=_related_from_production(name, all_hotel_rows, facts_map))


_BRAND_MAP = {"druryhotels.com": "Drury Hotels", "daysinncolumbusohio.com": "Days Inn",
              "sonesta.com": "Sonesta", "wyndhamhotels.com": "Wyndham",
              "plazahotelcolumbus.com": "property"}


def _brand_of(url: str) -> str:
    from urllib.parse import urlsplit
    host = (urlsplit(url).hostname or "").lower().lstrip("www.")
    for k, v in _BRAND_MAP.items():
        if k in host:
            return v
    return "property"


# --------------------------------------------------------------------------- #
# Render.
# --------------------------------------------------------------------------- #

def _facts_html(vm: HotelProfileVM) -> str:
    cells = "".join(
        '<div class="fh-cell"><div class="k">%s</div><div class="v %s">%s</div></div>'
        % (_e(lbl), cls, _e(val)) for lbl, val, cls in vm.facts)
    return '<div class="fh-facts">%s</div>' % cells


def _actions_html(vm: HotelProfileVM) -> str:
    call = '<a class="btn btn-line" href="/go/%s/call/">Call %s</a>' % (_slug(vm.name), _e(vm.phone)) if vm.phone else ""
    if vm.actions_mode == "book":
        return ('<a class="btn btn-primary" href="/go/%s/booking/">Check booking options</a>'
                '<div class="secondaries"><a class="btn btn-line" href="/go/%s/official-website/">Visit official site</a>'
                '<a class="btn btn-line" href="/go/%s/directions/">Directions</a>%s</div>'
                % (_slug(vm.name), _slug(vm.name), _slug(vm.name), call))
    if vm.actions_mode == "alt":
        return ('<a class="btn btn-primary alt" href="/pet-friendly-hotels/">Find pet-friendly alternatives</a>'
                '<div class="secondaries"><a class="btn btn-line" href="/go/%s/official-website/">Visit official site</a></div>'
                % _slug(vm.name))
    return ('<a class="btn btn-primary alt" href="/go/%s/official-website/">Visit official site</a>'
            '<div class="secondaries"><a class="btn btn-line" href="/methodology/">How to confirm the policy</a></div>'
            % _slug(vm.name))


def _mobilebar_html(vm: HotelProfileVM) -> str:
    if vm.actions_mode == "book":
        return ('<a class="btn btn-primary" href="/go/%s/booking/">Check booking options</a>'
                '<a class="btn btn-line" href="/go/%s/official-website/">Official site</a>'
                % (_slug(vm.name), _slug(vm.name)))
    if vm.actions_mode == "alt":
        return ('<a class="btn btn-primary alt" href="/pet-friendly-hotels/">Find alternatives</a>'
                '<a class="btn btn-line" href="/go/%s/official-website/">Official site</a>' % _slug(vm.name))
    return ('<a class="btn btn-primary alt" href="/go/%s/official-website/">Visit official site</a>'
            '<a class="btn btn-line" href="/methodology/">How to confirm</a>' % _slug(vm.name))


def _trust_html(vm: HotelProfileVM) -> str:
    icon = {"ok": "✓", "stop": "✕", "neutral": "•"}[vm.trust_cls]
    q = ('<details><summary>Exact wording available</summary><p class="quote">“%s”</p></details>'
         % _e(vm.evidence_quote)) if vm.evidence_quote else ""
    return '<div class="fh-trust %s"><span class="badge">%s %s</span>%s</div>' % (
        vm.trust_cls, icon, _e(vm.trust_line), q)


def _details_html(vm: HotelProfileVM) -> str:
    if vm.details_plain:
        svc = '<div class="fh-service"><b>Service animals:</b> %s</div>' % _e(vm.service_note) if vm.service_note else ""
        return '<p class="fh-plain">%s</p>%s' % (_e(vm.details_plain), svc)
    rows = "".join('<div class="row"><dt>%s</dt><dd class="%s">%s</dd></div>' % (_e(l), c, _e(v))
                   for l, v, c in vm.details_rows)
    note = '<p class="fh-fallback" style="margin-top:24px">%s</p>' % _e(vm.details_note) if vm.details_note else ""
    return '<dl class="fh-details">%s</dl>%s' % (rows, note)


def _prov_html(vm: HotelProfileVM) -> str:
    if vm.prov_status:
        return ('<div class="fh-prov"><div>Status: <b>not verified</b>. No approved official source has '
                'confirmed this property’s pet policy.</div><div class="links"><a href="/methodology/">How verification works ›</a></div></div>')
    q = ('<details><summary>See the exact recorded wording</summary><p class="quote">“%s”</p></details>'
         % _e(vm.evidence_quote)) if vm.evidence_quote else ""
    return ('<div class="fh-prov"><div>Read from <b>%s</b>, verified <b>%s</b>.</div>%s'
            '<div class="links"><a href="/methodology/">How we verify ›</a> · '
            '<a href="/go/%s/report-change/">Report an outdated policy ›</a></div></div>'
            % (_e(vm.source_name or "the official source"), _e(vm.verified_at or ""), q, _slug(vm.name)))


def _related_html(vm: HotelProfileVM) -> str:
    cards = []
    for r in vm.related:
        fact = '<div class="rf">%s</div>' % _e(r.fact) if r.fact else ""
        date = '<div class="rv">✓ Verified · %s</div>' % _e(r.verified_at) if r.verified_at else ""
        cards.append('<a class="fh-rel" href="%s"><div class="rn">%s</div><div class="ra">%s</div>%s%s<div class="rl">View policy ›</div></a>'
                     % (r.route, _e(r.name), _e(r.area), fact, date))
    return '<div class="fh-rel-grid">%s</div>' % "".join(cards)


def render_hotel_profile(vm: HotelProfileVM, *, css_href: str = "hotel_profile.css",
                         diag: bool = False) -> str:
    crumb_area = vm.corridor.split(" ·")[0]
    hero = (
        '<section class="fh-hero">'
        '<div class="fh-media-wrap">'
        '<figure class="fh-media" data-media-slot="hotel-primary" role="img" aria-label="Branded placeholder for %s. No approved photograph of this property is available.">'
        '%s<div class="init">%s</div>'
        '<div class="mrow">%s<small>%s</small></div>'
        '<span class="mchip">%s</span></figure>'
        '<p class="fh-media-cap">%s</p></div>'
        '<span class="fh-corridor">%s</span>'
        '<h1 class="fh-name">%s</h1>'
        '<span class="fh-verif %s"><span class="dot" aria-hidden="true"></span>%s</span>'
        '<p class="fh-summary">%s</p>'
        '%s'
        '<div class="fh-actions">%s</div>'
        '</section>'
    ) % (_e(vm.name), _HOME_SVG, _e(vm.initials), _e(vm.name.split(" Columbus")[0]),
         _e(crumb_area), vm.verif_chip, _MEDIA_CAP, _e(vm.corridor), _e(vm.name),
         vm.verif_badge_cls, _e(vm.verif_badge_text), vm.summary, _facts_html(vm), _actions_html(vm))

    body = (
        _trust_html(vm)
        + '<div class="fh-body">'
        + '<section class="fh-sec" style="border-top:0;padding-top:0"><h2 class="fh-h2">Full policy details</h2>%s</section>' % _details_html(vm)
        + '<section class="fh-sec"><h2 class="fh-h2">Address &amp; directions</h2><p class="fh-addr">%s · <a href="/go/%s/directions/">Get directions ›</a></p></section>' % (_e(vm.address), _slug(vm.name))
        + '<section class="fh-sec"><h2 class="fh-h2">Traveling with a pet in Columbus</h2>'
          '<p class="fh-plain">Distance-based recommendations aren’t available for this property yet.</p>'
          '<p class="fh-fallback"><a href="/columbus-oh/">Explore Columbus pet-travel resources ›</a></p></section>'
        + '<section class="fh-sec"><h2 class="fh-h2">Verification &amp; provenance</h2>%s</section>' % _prov_html(vm)
        + '<section class="fh-sec"><h2 class="fh-h2">More verified pet-friendly stays</h2>%s</section>' % _related_html(vm)
        + '</div>'
    )

    menu_js = ("<script>var b=document.querySelector('.fh-menu'),n=document.getElementById('sitenav');"
               "if(b&&n){b.addEventListener('click',function(){var o=n.getAttribute('data-open')==='true';"
               "n.setAttribute('data-open',String(!o));b.setAttribute('aria-expanded',String(!o));});}</script>")
    diag_js = ""
    if diag:
        diag_js = ("<script>requestAnimationFrame(function(){var iw=innerWidth,sw=document.documentElement.scrollWidth,o=sw>iw+1;"
                   "var d=document.createElement('div');d.style.cssText='position:fixed;top:6px;left:6px;z-index:999;font:12px monospace;background:'+(o?'#c00':'#0a7a0a')+';color:#fff;padding:4px 8px;border-radius:4px';"
                   "d.textContent='innerW='+iw+' scrollW='+sw+' '+(o?'OVERFLOW':'no-overflow');document.body.appendChild(d);});</script>")

    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>%s — Pet Policy | PetTripFinder</title>'
        '<meta name="description" content="%s">'
        '<link rel="stylesheet" href="%s"></head><body>'
        '<a class="skip-link" href="#main">Skip to main content</a>'
        '<header class="fh-header"><div class="wrap">'
        '<a class="fh-brand" href="/">PetTripFinder<b> · Columbus</b></a>'
        '<button class="fh-menu" aria-expanded="false" aria-controls="sitenav">Menu</button>'
        '<nav class="fh-nav" id="sitenav" aria-label="Main"><a href="/pet-friendly-hotels/">Hotels</a><a href="/pet-friendly-parks/">Parks</a><a href="/methodology/">How we verify</a></nav>'
        '</div></header>'
        '<div class="wrap"><nav class="fh-crumbs" aria-label="Breadcrumb"><ol>'
        '<li><a href="/columbus-oh/">Columbus</a></li><li><a href="/pet-friendly-hotels/">Pet-Friendly Hotels</a></li>'
        '<li><a href="#">%s</a></li><li aria-current="page">%s</li></ol></nav>'
        '%s<main id="main">%s</main></div>'
        '<footer class="fh-footer"><div class="wrap"><div>© 2026 PetTripFinder · Your verified Columbus pet-travel guide'
        '<br><span style="font-size:12.5px">Some booking links are affiliate links; using them may earn PetTripFinder a commission and never changes a property’s placement or its verified policy.</span></div>'
        '<div><a href="/methodology/">How we verify</a> · <a href="/about/">About</a> · <a href="/contact/">Contact</a></div></div></footer>'
        '<div class="fh-mobilebar">%s</div>'
        '%s%s</body></html>'
    ) % (_e(vm.name), _e(re.sub("<[^>]+>", "", vm.summary))[:150], css_href,
         _e(crumb_area), _e(vm.name), hero, body, _mobilebar_html(vm), menu_js, diag_js)


# --------------------------------------------------------------------------- #
# Controlled fixture builders.
#
# The fixture DATA is committed (hotel_profile_fixtures.json), transcribed
# verbatim from the repository-authorized verified importer candidates, so the
# renderer, the fixture runner, and the tests are fully reproducible in a clean
# checkout -- they never read the gitignored operational data/ tree. Property
# IDENTITY (address/phone/URL) still comes from the tracked production seed CSV
# via read_production_rows(); only the verified pet-policy FACTS and the two
# out-of-inventory (no-pets / unverified) records live in the committed fixture
# file.
# --------------------------------------------------------------------------- #

_FIXTURE_DATA_PATH = Path(__file__).resolve().parent / "hotel_profile_fixtures.json"


def _load_fixture_data() -> Dict:
    return json.loads(_FIXTURE_DATA_PATH.read_text(encoding="utf-8"))


def build_fixture_vms() -> Dict[str, HotelProfileVM]:
    """The five controlled production fixtures. rich/sparse/no-photo combine the
    promoted production CSV identity with committed verified facts; no-pets and
    unverified come from committed, repository-authorized candidate excerpts
    (intentionally not part of the verified pet-friendly production set). No
    gitignored operational data is read -- reproducible from a clean checkout."""
    rows = read_production_rows()
    hotels = [r for r in rows if r["category"] == "pet-friendly-hotels"]
    data = _load_fixture_data()
    facts_map = data["verified_facts"]

    def row_by(name_start):
        return next(r for r in hotels if r["name"].startswith(name_start))

    rich_row = row_by("Drury Inn & Suites Columbus Grove City")
    sparse_row = row_by("Days Inn by Wyndham Grove City")

    np = data["no_pets"]
    cand_no_pets = {
        "context": {"candidate_name": np["name"], "expected_city": np["city"]},
        "proposed_fields": [["name", np["name"]], ["city", np["city"]],
                            ["address", np["address"]], ["website_url", np["website_url"]]],
        "snapshot": {"observed_at": np["verified_at"], "requested_url": np["website_url"]},
        "evidence": [{"field_name": "pets_allowed", "snapshot_quote": np["evidence_quote"]}],
    }
    uv = data["unverified"]
    cand_unverified = {
        "context": {"candidate_name": uv["name"], "expected_city": uv["city"]},
        "proposed_fields": [], "evidence": [],
        "snapshot": {"requested_url": uv["official_url"]},
    }

    return {
        "rich": build_vm_from_production(rich_row, facts_map.get(normalize_name(rich_row["name"])), hotels, facts_map),
        "sparse": build_vm_from_production(sparse_row, facts_map.get(normalize_name(sparse_row["name"])), hotels, facts_map),
        # no-photo is the same verified record as rich -- every hotel is
        # photo-less, so the placeholder is the default; this proves the media
        # region is stable whether a photo or the placeholder fills it.
        "no-photo": build_vm_from_production(rich_row, facts_map.get(normalize_name(rich_row["name"])), hotels, facts_map),
        "no-pets": build_vm_from_no_pets(cand_no_pets, hotels, facts_map),
        "unverified": build_vm_from_unverified(cand_unverified, hotels, facts_map),
    }
