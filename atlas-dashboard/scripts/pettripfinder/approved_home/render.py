"""Founder-approved coded homepage — exact-prototype renderer.

Reproduces pettripfinder_exact_prototype_v3/index.html VERBATIM (CSS + markup
structure) and fills it with the 14 verified production hotel records, real
inventory counts, and live routes. Only data, links, asset paths, and a real
(vs. placeholder-alert) mobile nav are integrated. Facts are copied through from
the committed package — unstated values are shown honestly, never invented.
"""

from __future__ import annotations

import html
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from scripts.pettripfinder.hotel_profile import _corridor_area

_ASSETS_DIR = Path(__file__).resolve().parent / "assets"


def _e(s: str) -> str:
    return html.escape(s or "", quote=False)


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").strip().lower()).strip("-")


# --------------------------------------------------------------------------- #
# Verbatim prototype stylesheet (byte-for-byte from the approved index.html),
# plus a clearly separated integration addition for a real mobile nav (the
# prototype used a placeholder alert). The approved rules are untouched.
# --------------------------------------------------------------------------- #

PROTOTYPE_CSS = r""":root{
  --ever:#123e31;--ever-2:#1f5a46;--ever-3:#e6efe7;--cream:#fbf8f1;
  --paper:#fffdf9;--ink:#15372f;--muted:#67746f;--line:#ddd7cb;--warm:#c65f3c;
  --shadow:0 18px 48px rgba(26,50,41,.14);--radius:16px;--max:1380px;
}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--cream);color:var(--ink);font-family:Inter, ui-sans-serif, system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;line-height:1.45}.serif,h1,h2,h3{font-family:Georgia,'Times New Roman',serif}.wrap{width:min(var(--max),calc(100% - 40px));margin:auto}.skip{position:absolute;left:-9999px}.skip:focus{left:16px;top:12px;z-index:100;background:#fff;padding:10px 14px;border-radius:8px}.topbar{height:72px;background:rgba(255,253,249,.96);border-bottom:1px solid #ece6da;display:flex;align-items:center;position:sticky;top:0;z-index:30;backdrop-filter:blur(10px)}.nav{display:flex;align-items:center;justify-content:space-between;gap:28px}.brand{display:flex;align-items:center;gap:10px;text-decoration:none;color:var(--ever);font-family:Georgia,serif;font-size:27px;font-weight:800;white-space:nowrap}.paw{width:42px;height:38px;display:block;color:var(--ever);flex:0 0 auto}.paw svg{display:block;width:100%;height:100%;fill:currentColor}.brand small{display:block;color:var(--warm);font-family:Inter,sans-serif;font-size:14px;line-height:1;margin-top:-2px}.links{display:flex;gap:30px;align-items:center}.links a,.saved{color:#233b34;text-decoration:none;font-size:14px;font-weight:650}.links a:hover{color:var(--warm)}.nav-actions{display:flex;align-items:center;gap:18px}.saved{display:flex;gap:7px}.btn{display:inline-flex;align-items:center;justify-content:center;gap:9px;border-radius:10px;padding:13px 20px;border:1px solid transparent;text-decoration:none;font-weight:800;font-size:14px;cursor:pointer}.btn-primary{background:var(--ever);color:#fff}.btn-primary:hover{background:#0e3328}.btn-outline{background:#fff;color:var(--ever);border-color:#bdc9c3}.menu{display:none;background:none;border:0;font-size:27px;color:var(--ever)}
.hero{position:relative;overflow:visible;background:#fbf8f1;min-height:510px;border-bottom:1px solid #d9d3c8}.hero:before{content:"";position:absolute;inset:0 0 0 42%;background:url('assets/hero-right.jpg') center/cover no-repeat}.hero:after{content:"";position:absolute;inset:0;background:linear-gradient(90deg,#fbf8f1 0%,#fbf8f1 34%,rgba(251,248,241,.94) 43%,rgba(251,248,241,.34) 57%,rgba(251,248,241,0) 72%);pointer-events:none}.hero-inner{position:relative;z-index:1;padding:48px 0 190px}.hero-copy{max-width:650px}.hero h1{font-size:60px;line-height:1.01;letter-spacing:-1.5px;margin:0 0 16px;color:var(--ever)}.hero h1 em{color:var(--warm);font-weight:500}.hero p{font-size:18px;max-width:560px;margin:0;color:#263c35}.searchbar{position:absolute;left:50%;bottom:72px;transform:translateX(-50%);z-index:3;width:min(1320px,calc(100% - 72px));display:grid;grid-template-columns:1.35fr 1.2fr 1.25fr .78fr 210px;background:rgba(255,255,255,.98);border:1px solid #d9d3c8;border-radius:15px;box-shadow:0 16px 38px rgba(31,57,48,.16);overflow:hidden}.field{padding:16px 22px;display:flex;align-items:center;gap:14px;min-height:78px;border-right:1px solid #e7e1d8}.field .line-icon{width:25px;height:25px;display:block;flex:0 0 auto;color:#182f28}.field .line-icon svg{width:100%;height:100%;display:block;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}.field:last-of-type{border-right:0}.field .icon{font-size:22px}.field b{display:block;font-size:13px}.field span{display:block;color:#6e7974;font-size:12px}.search-btn{margin:11px;border:0;border-radius:9px;background:var(--ever);color:#fff;font-weight:850;font-size:16px;display:flex;align-items:center;justify-content:center;gap:10px}.search-btn svg{width:22px;height:22px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round}.stats{position:absolute;z-index:4;left:50%;bottom:-32px;transform:translateX(-50%);width:min(1320px,calc(100% - 72px));height:80px;background:linear-gradient(90deg,#174733,#0f3b2e);border-radius:12px;color:#fff;display:grid;grid-template-columns:repeat(4,1fr);box-shadow:0 12px 30px rgba(10,43,33,.22)}.stat{display:flex;align-items:center;justify-content:center;gap:14px;border-right:1px solid rgba(255,255,255,.22);padding:0 18px}.stat:last-child{border-right:0}.stat .ico{width:36px;height:36px;display:block;color:#f4e7c0;flex:0 0 auto}.stat .ico svg{width:100%;height:100%;display:block;fill:none;stroke:currentColor;stroke-width:1.7;stroke-linecap:round;stroke-linejoin:round}.stat strong{font-family:Georgia,serif;font-size:34px;font-weight:500}.stat small{font-size:12px;line-height:1.2;color:#e8f1eb}.main{padding-top:84px}.section{padding:28px 0}.section-title{display:flex;align-items:end;justify-content:space-between;margin-bottom:14px}.section-title h2{margin:0;font-size:28px}.section-title a{font-size:13px;color:var(--ever);font-weight:800}.hotel-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:14px}.hotel{background:#fff;border:1px solid #e0dbd1;border-radius:13px;overflow:hidden;box-shadow:0 3px 14px rgba(38,55,49,.05);transition:.2s transform,.2s box-shadow}.hotel:hover{transform:translateY(-4px);box-shadow:0 12px 28px rgba(31,58,48,.14)}.photo{height:158px;background-size:cover;background-position:center;position:relative}.verified{position:absolute;left:10px;bottom:9px;background:rgba(22,68,51,.94);color:#fff;border-radius:999px;padding:5px 9px;font-size:11px;font-weight:800}.heart{position:absolute;right:9px;top:9px;width:30px;height:30px;border:0;border-radius:50%;background:#fff;color:#234b3d;font-size:17px}.hotel-body{padding:12px}.hotel h3{font-size:17px;line-height:1.1;margin:0 0 5px}.place{font-size:12px;color:#6e746f;margin-bottom:11px}.facts{display:flex;justify-content:space-between;gap:7px;font-size:11px;border-top:1px solid #eee7dc;padding-top:10px}.facts b{display:block;font-size:12px}.mini-icons{margin-top:10px;color:#4f615a;font-size:14px;display:flex;gap:10px}.mini-icons svg{width:17px;height:17px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}.trust-panel{background:#f6f1e7;border:1px solid #e5ded2;border-radius:15px;padding:22px;margin-top:10px;display:grid;grid-template-columns:1.05fr .75fr 1.55fr;gap:28px;align-items:center}.trust-panel h3{font-size:23px;margin:0 0 7px}.trust-panel p{margin:0 0 12px;color:#4f5f59;font-size:14px}.checklist{padding:0;margin:0;list-style:none}.checklist li{margin:8px 0;font-size:13px}.checklist li:before{content:'✓';display:inline-grid;place-items:center;width:18px;height:18px;border:1px solid #6d9b85;border-radius:50%;margin-right:9px;color:#1e6a4b;font-weight:900}.compare-box{background:#fff;border:1px solid #ddd7cc;border-radius:12px;padding:22px}.compare-box h3{font-size:20px;margin:0 0 4px}.compare-box p{font-size:13px}.compare-table{font-size:12px;width:100%;border-collapse:collapse}.compare-table th,.compare-table td{padding:8px 7px;border-bottom:1px solid #e9e2d7;text-align:left}.compare-table th{font-size:11px;color:#4e5f59}.trip-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}.trip-card{display:grid;grid-template-columns:1fr 1.05fr;min-height:145px;border:1px solid #dfd8cd;border-radius:12px;background:#fff;overflow:hidden;text-decoration:none;color:var(--ink)}.trip-card img{width:100%;height:100%;object-fit:cover}.trip-copy{padding:16px}.trip-copy h3{font-size:18px;margin:0 0 8px}.trip-copy p{font-size:12px;color:#53645d;min-height:38px}.trip-copy span{font-size:12px;font-weight:850;text-decoration:underline}.footer{padding:30px 0 45px;margin-top:24px;border-top:1px solid #e2dbd0;background:#fff}.footer-grid{display:grid;grid-template-columns:2fr repeat(3,1fr);gap:28px}.footer h4{margin:0 0 10px}.footer a{display:block;color:#53615c;text-decoration:none;font-size:13px;margin:7px 0}.note{margin-top:12px;font-size:12px;color:#74817b}
@media(max-width:1100px){.links{display:none}.menu{display:block}.saved{display:none}.hero h1{font-size:48px}.searchbar{grid-template-columns:1fr 1fr 1fr 160px}.field:nth-child(4){display:none}.hotel-grid{grid-template-columns:repeat(3,1fr)}.hotel:nth-child(n+4){display:none}.trip-grid{grid-template-columns:repeat(2,1fr)}.trust-panel{grid-template-columns:1fr 1fr}.compare-table-wrap{grid-column:1/-1}}
@media(max-width:720px){.wrap{width:min(100% - 24px,var(--max))}.topbar{height:60px}.brand{font-size:21px}.nav-actions .btn{display:none}.hero{min-height:650px;background:#fbf8f1}.hero:before{inset:auto 0 0 0;height:54%;background-position:68% center}.hero:after{background:linear-gradient(180deg,#fbf8f1 0%,#fbf8f1 47%,rgba(251,248,241,.78) 61%,rgba(251,248,241,.1) 82%)}.hero-inner{padding:28px 0 360px}.hero h1{font-size:43px;max-width:430px}.hero p{font-size:16px}.searchbar{bottom:106px;grid-template-columns:1fr;width:calc(100% - 24px);border-radius:14px}.field{min-height:56px;padding:10px 14px}.field:nth-child(2),.field:nth-child(3),.field:nth-child(4){display:none}.search-btn{height:48px}.stats{bottom:-120px;width:calc(100% - 24px);height:auto;grid-template-columns:1fr 1fr;padding:8px}.stat{min-height:70px;border-right:0;border-bottom:1px solid rgba(255,255,255,.16);justify-content:flex-start}.stat:nth-child(3),.stat:nth-child(4){border-bottom:0}.stat strong{font-size:25px}.main{padding-top:145px}.section{padding:22px 0}.section-title h2{font-size:24px}.hotel-grid{grid-template-columns:1fr;gap:14px}.hotel:nth-child(n){display:block}.hotel:nth-child(n+4){display:none}.photo{height:210px}.trust-panel{grid-template-columns:1fr;padding:18px}.trip-grid{grid-template-columns:1fr}.trip-card{min-height:150px}.footer-grid{grid-template-columns:1fr 1fr}.footer-grid>div:first-child{grid-column:1/-1}.stats .ico{font-size:22px}.stat{padding:0 9px}.stat small{font-size:10px}.field span{font-size:11px}}"""

# Integration addition only: reveal the nav as a dropdown when the burger is
# tapped (prototype shipped a placeholder alert). Desktop visuals are untouched.
_INTEGRATION_CSS = r"""
/* --- integration additions (do not alter the approved rules above) --- */
/* Cards are anchors (whole card links to the profile). A class rule keeps the
   article-like block display while staying LESS specific than the approved
   .hotel:nth-child(n+4){display:none} responsive hide, so the mobile/tablet
   card count matches the prototype exactly. */
.hotel{display:block;text-decoration:none;color:inherit}
/* functional mobile navigation (prototype shipped a placeholder alert) */
@media(max-width:1100px){.links.pt-open{display:flex;position:absolute;top:72px;left:0;right:0;flex-direction:column;align-items:flex-start;gap:0;background:#fffdf9;border-bottom:1px solid #ece6da;padding:6px 20px 14px;box-shadow:0 18px 40px rgba(26,50,41,.12);z-index:29}.links.pt-open a{padding:13px 0;width:100%;font-size:16px}}
@media(max-width:720px){.links.pt-open{top:60px}}"""

_MOBILE_NAV_JS = ("<script>(function(){var b=document.querySelector('.menu'),"
                  "l=document.querySelector('.links');if(b&&l){b.setAttribute('aria-expanded','false');"
                  "b.addEventListener('click',function(){var o=l.classList.toggle('pt-open');"
                  "b.setAttribute('aria-expanded',String(o));});}})();</script>")

# Exact SVGs lifted verbatim from the approved prototype.
_PAW = ('<span class="paw" aria-hidden="true"><svg viewBox="0 0 48 42">'
        '<ellipse cx="24" cy="29" rx="12.5" ry="10.5"/>'
        '<ellipse cx="8.5" cy="18" rx="5" ry="7" transform="rotate(-18 8.5 18)"/>'
        '<ellipse cx="18" cy="8.5" rx="5" ry="7" transform="rotate(-7 18 8.5)"/>'
        '<ellipse cx="30" cy="8.5" rx="5" ry="7" transform="rotate(7 30 8.5)"/>'
        '<ellipse cx="39.5" cy="18" rx="5" ry="7" transform="rotate(18 39.5 18)"/></svg></span>')
_ICON_PIN = ('<span class="line-icon" aria-hidden="true"><svg viewBox="0 0 24 24">'
             '<path d="M20 10c0 5-8 12-8 12S4 15 4 10a8 8 0 1 1 16 0Z"/><circle cx="12" cy="10" r="2.5"/></svg></span>')
_ICON_PAWLINE = ('<span class="line-icon" aria-hidden="true"><svg viewBox="0 0 24 24">'
                 '<circle cx="5.5" cy="10" r="2"/><circle cx="10" cy="5.8" r="2"/><circle cx="14.5" cy="5.8" r="2"/>'
                 '<circle cx="19" cy="10" r="2"/><path d="M12 11.5c-3 0-5.5 2.2-5.5 5 0 2.1 2.3 3.7 5.5 3.7s5.5-1.6 5.5-3.7c0-2.8-2.5-5-5.5-5Z"/></svg></span>')
_ICON_CAL = ('<span class="line-icon" aria-hidden="true"><svg viewBox="0 0 24 24">'
             '<rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 10h18"/></svg></span>')
_ICON_GUEST = ('<span class="line-icon" aria-hidden="true"><svg viewBox="0 0 24 24">'
               '<circle cx="12" cy="8" r="4"/><path d="M4.5 21c.8-5 3.2-7 7.5-7s6.7 2 7.5 7"/></svg></span>')
_SEARCH_SVG = ('<svg aria-hidden="true" viewBox="0 0 24 24"><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></svg>')
_MINI_PAW = ('<svg aria-hidden="true" viewBox="0 0 24 24"><circle cx="5.5" cy="10" r="2"/><circle cx="10" cy="5.8" r="2"/>'
             '<circle cx="14.5" cy="5.8" r="2"/><circle cx="19" cy="10" r="2"/>'
             '<path d="M12 11.5c-3 0-5.5 2.2-5.5 5 0 2.1 2.3 3.7 5.5 3.7s5.5-1.6 5.5-3.7c0-2.8-2.5-5-5.5-5Z"/></svg>')
_MINI_HEART = ('<svg aria-hidden="true" viewBox="0 0 24 24"><path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.9-8.6a5.5 5.5 0 0 0-.1-7.8Z"/></svg>')
_STAT_HOTEL = '<svg viewBox="0 0 40 40"><path d="M8 35V12h24v23M14 12V6h12v6M4 35h32M14 18h4v4h-4zM22 18h4v4h-4zM14 27h4v4h-4zM22 27h4v4h-4z"/></svg>'
_STAT_PARK = '<svg viewBox="0 0 40 40"><path d="M20 5c-5 0-8 4-8 8-4 1-6 4-6 8 0 5 4 8 9 8h10c5 0 9-3 9-8 0-4-3-7-7-8 0-4-3-8-7-8Z"/><path d="M20 29v7M15 36h10"/></svg>'
_STAT_REST = '<svg viewBox="0 0 40 40"><path d="M10 5v13M6 5v8c0 3 2 5 4 5s4-2 4-5V5M10 18v17M27 5c-4 3-5 8-5 13h7v17M29 5v13"/></svg>'
_STAT_SHIELD = '<svg viewBox="0 0 40 40"><path d="M20 4 33 9v9c0 9-5 14-13 18C12 32 7 27 7 18V9l13-5Z"/><path d="m14 20 4 4 8-9"/></svg>'


# --------------------------------------------------------------------------- #
# Fact formatting (honest; copied from the committed package, never invented).
# --------------------------------------------------------------------------- #

def _fee(f: Dict[str, str]) -> str:
    fee = (f.get("pet_fee") or "").strip()
    if not fee:
        return "Fee not stated"
    b = (f.get("fee_basis") or "").lower()
    unit = ("night" if "night" in b else "day" if "day" in b else "stay" if "stay" in b
            else "week" if "week" in b else "")
    return "%s / %s" % (fee, unit) if unit else fee


def _pets(f: Dict[str, str]) -> str:
    c = (f.get("pet_count_limit") or "").strip()
    if not c:
        return "Pets not stated"
    return "%s pet" % c if c == "1" else "%s pets" % c


def _weight(f: Dict[str, str]) -> str:
    w = (f.get("weight_limit") or "").strip()
    if not w:
        return "Weight not stated"
    m = re.search(r"(\d+)", w)
    if m and re.search(r"(lb|pound)", w, re.I):
        return "Up to %s lbs" % m.group(1)      # normalize any pounds/lb(s) form
    return "Up to %s" % w


def _species(f: Dict[str, str]) -> str:
    sp = (f.get("species_allowed") or "").lower()
    if "dog" in sp and "cat" in sp:
        return "Dogs, cats"
    if "dog" in sp:
        return "Dogs"
    if "cat" in sp:
        return "Cats"
    return "Not stated"


def _display_name(name: str) -> str:
    """Concise brand label for a card heading (the corridor carries the
    location), mirroring the prototype's short names. Identity/route/policy are
    unchanged — the full name remains on the profile page."""
    cut = re.split(r"\s+Columbus\b", name, maxsplit=1)[0].strip()
    return cut or name


# --------------------------------------------------------------------------- #
# Data selection.
# --------------------------------------------------------------------------- #

# The exact five hotels the approved prototype featured, in the same order (so
# the same review photos align with the same properties). Each is a real
# verified record; facts are shown honestly (unstated -> "Not stated"). Missing
# names back-fill with any other verified hotel so the row is always five reals.
_PREFERRED_FEATURED = (
    "The Westin Great Southern Columbus",
    "Hyatt Regency Columbus",
    "Drury Inn & Suites Columbus Grove City",
    "Sonesta Columbus Downtown",
    "Home2 Suites by Hilton Columbus Dublin",
)


def select_featured(hotel_rows: List[Dict], facts_map: Dict, limit: int = 5) -> List[Dict]:
    by_name = {r["name"]: r for r in hotel_rows}
    chosen: List[Dict] = []
    used = set()
    for pref in _PREFERRED_FEATURED:
        row = by_name.get(pref)
        if row and pref not in used:
            chosen.append(row)
            used.add(pref)
    # Back-fill (only if a preferred record is ever missing): prefer other
    # fee-stated hotels, then any remaining, deterministically by name.
    if len(chosen) < limit:
        pool = sorted((r for r in hotel_rows if r["name"] not in used), key=lambda r: r["name"].lower())
        pool.sort(key=lambda r: (0 if _facts_of(r["name"], facts_map).get("pet_fee") else 1))
        for r in pool:
            if len(chosen) >= limit:
                break
            chosen.append(r)
            used.add(r["name"])
    return chosen[:limit]


# --------------------------------------------------------------------------- #
# Render.
# --------------------------------------------------------------------------- #

def _facts_of(name: str, facts_map: Dict) -> Dict[str, str]:
    from scripts.pettripfinder.site_data import normalize_name
    entry = facts_map.get(normalize_name(name))
    return (entry or {}).get("facts", {}) if entry else {}


def _hotel_card(row: Dict, facts_map: Dict, photo: str) -> str:
    name = row["name"]
    f = _facts_of(name, facts_map)
    place = _corridor_area(row.get("city", ""), row.get("address", ""), name)
    route = "/pet-friendly-hotels/%s/" % _slug(name)
    return (
        '<a class="hotel" href="%s">'
        '<div class="photo" style="background-image:url(\'assets/%s\')">'
        '<span class="verified">&#10003; Verified policy</span>'
        '<span class="heart" aria-hidden="true">&#9825;</span></div>'
        '<div class="hotel-body"><h3>%s</h3><div class="place">%s</div>'
        '<div class="facts"><span><b>%s</b></span><span><b>%s</b></span><span><b>%s</b></span></div>'
        '<div class="mini-icons">%s%s</div></div></a>'
    ) % (route, _e(photo), _e(_display_name(name)), _e(place),
         _e(_fee(f)), _e(_pets(f)), _e(_weight(f)), _MINI_PAW, _MINI_HEART)


def _compare_table(hotel_rows: List[Dict], facts_map: Dict) -> str:
    # The prototype's three compare columns, as real records (Drury / Hyatt / Westin).
    picks = ["Drury Inn & Suites Columbus Grove City", "Hyatt Regency Columbus",
             "The Westin Great Southern Columbus"]
    by_name = {r["name"]: r for r in hotel_rows}
    cols = [by_name[n] for n in picks if n in by_name][:3]
    if len(cols) < 3:
        cols = (cols + sorted(hotel_rows, key=lambda r: r["name"].lower()))[:3]
    heads = "".join("<th>%s</th>" % _e(_display_name(r["name"])) for r in cols)
    facts = [_facts_of(r["name"], facts_map) for r in cols]

    def rowcells(fn):
        return "".join("<td>%s</td>" % _e(fn(f)) for f in facts)
    return (
        '<table class="compare-table"><thead><tr><th></th>%s</tr></thead><tbody>'
        '<tr><th>Pet fee</th>%s</tr>'
        '<tr><th>Max pets</th>%s</tr>'
        '<tr><th>Weight limit</th>%s</tr>'
        '<tr><th>Species</th>%s</tr>'
        '</tbody></table>'
    ) % (heads, rowcells(_fee),
         rowcells(lambda f: (f.get("pet_count_limit") or "").strip() or "Not stated"),
         rowcells(lambda f: _weight(f).replace("Weight not stated", "Not stated")),
         rowcells(_species))


def render_home(hotel_rows: List[Dict], facts_map: Dict, *, hotel_count: int,
                park_count: int, restaurant_count: int) -> str:
    featured = select_featured(hotel_rows, facts_map, 5)
    photos = ["hotel1.jpg", "hotel2.jpg", "hotel3.jpg", "hotel4.jpg", "hotel5.jpg"]
    cards = "".join(_hotel_card(r, facts_map, photos[i % len(photos)]) for i, r in enumerate(featured))
    compare = _compare_table(hotel_rows, facts_map)

    nav = (
        '<a href="/pet-friendly-hotels/">Hotels</a>'
        '<a href="/pet-friendly-parks/">Parks</a>'
        '<a href="/pet-friendly-restaurants/">Restaurants</a>'
        '<a href="/pet-friendly-hotels/policy-comparison/">Compare</a>'
        '<a href="/methodology/">How it works</a>')
    header = (
        '<header class="topbar"><div class="wrap nav">'
        '<a class="brand" href="/">%s<span>PetTripFinder<small>Columbus</small></span></a>'
        '<nav class="links" aria-label="Primary">%s</nav>'
        '<div class="nav-actions"><a class="saved" href="/pet-friendly-hotels/">&#9825; Saved</a>'
        '<a class="btn btn-primary" href="/pet-friendly-hotels/">Browse verified hotels</a>'
        '<button class="menu" aria-label="Open menu" aria-expanded="false">&#9776;</button>'
        '</div></div></header>'
    ) % (_PAW, nav)

    hero = (
        '<section class="hero"><div class="wrap hero-inner"><div class="hero-copy">'
        '<h1>Find a Columbus hotel<br>that <em>actually</em> works for<br>your pet.</h1>'
        '<p>Compare real pet policies, exact fees, pet limits, and amenities &mdash; all verified from '
        'official sources.</p></div></div>'
        '<div class="searchbar">'
        '<div class="field">%s<div><b>Where to?</b><span>Neighborhood, area, or address</span></div></div>'
        '<div class="field">%s<div><b>Pet needs</b><span>Any size, breed, or number</span></div></div>'
        '<div class="field">%s<div><b>Check-in &mdash; Check-out</b><span>Add dates</span></div></div>'
        '<div class="field">%s<div><b>Guests</b><span>1 guest</span></div></div>'
        '<a class="search-btn" href="/pet-friendly-hotels/">%sSearch hotels</a></div>'
        '<div class="stats">'
        '<div class="stat"><span class="ico" aria-hidden="true">%s</span><strong>%d</strong>'
        '<small>verified<br>pet-friendly hotels</small></div>'
        '<div class="stat"><span class="ico" aria-hidden="true">%s</span><strong>%d</strong>'
        '<small>parks &amp;<br>green spaces</small></div>'
        '<div class="stat"><span class="ico" aria-hidden="true">%s</span><strong>%d</strong>'
        '<small>pet-friendly<br>restaurants</small></div>'
        '<div class="stat"><span class="ico" aria-hidden="true">%s</span>'
        '<small><b style="font-family:Georgia;font-size:18px">Every policy</b><br>verified from official sources</small></div>'
        '</div></section>'
    ) % (_ICON_PIN, _ICON_PAWLINE, _ICON_CAL, _ICON_GUEST, _SEARCH_SVG,
         _STAT_HOTEL, hotel_count, _STAT_PARK, park_count, _STAT_REST, restaurant_count, _STAT_SHIELD)

    hotels = (
        '<section id="hotels" class="section"><div class="wrap">'
        '<div class="section-title"><h2>Featured verified stays in Columbus</h2>'
        '<a href="/pet-friendly-hotels/">View all hotels &rarr;</a></div>'
        '<div class="hotel-grid">%s</div></div></section>'
    ) % cards

    trust = (
        '<section id="trust" class="section"><div class="wrap trust-panel">'
        '<div><h3>We show you what matters.</h3>'
        '<p>Exact fees, pet limits, and rules pulled from official hotel websites and brand policies.</p>'
        '<ul class="checklist"><li>Exact pet fees and deposits</li><li>Species, size, and weight limits</li>'
        '<li>Up-to-date policy details</li><li>Sources you can trust</li></ul></div>'
        '<div id="compare" class="compare-box"><h3>Compare policies side by side</h3>'
        '<p>See the real differences before you book.</p>'
        '<a class="btn btn-outline" href="/pet-friendly-hotels/policy-comparison/">Compare hotels</a></div>'
        '<div class="compare-table-wrap">%s</div></div></section>'
    ) % compare

    trip = (
        '<section id="trip" class="section"><div class="wrap">'
        '<div class="section-title"><h2>Plan the perfect pet-friendly trip in Columbus</h2></div>'
        '<div class="trip-grid">'
        '<a class="trip-card" href="/pet-friendly-parks/"><div class="trip-copy"><h3>Dog parks &amp;<br>green spaces</h3>'
        '<p>Explore off-leash parks and scenic trails.</p><span>Explore parks &rarr;</span></div>'
        '<img src="assets/trip1.jpg" alt="Dog in a park"></a>'
        '<a class="trip-card" href="/pet-friendly-restaurants/"><div class="trip-copy"><h3>Pet-friendly<br>dining</h3>'
        '<p>Find patios and spots that welcome pets.</p><span>Explore restaurants &rarr;</span></div>'
        '<img src="assets/trip2.jpg" alt="Dog at a restaurant"></a>'
        '<a class="trip-card" href="/pet-friendly-hotels/policy-comparison/"><div class="trip-copy"><h3>Compare<br>policies</h3>'
        '<p>Side-by-side hotel policy and fee comparisons.</p><span>Compare hotels &rarr;</span></div>'
        '<img src="assets/trip3.jpg" alt="Traveler with a dog"></a>'
        '<a class="trip-card" href="/pet-friendly-hotels/dublin/"><div class="trip-copy"><h3>Explore Columbus<br>corridors</h3>'
        '<p>Neighborhood guides for pet travelers.</p><span>Explore guide &rarr;</span></div>'
        '<img src="assets/trip4.jpg" alt="Columbus skyline"></a>'
        '</div></div></section>')

    footer = (
        '<footer class="footer"><div class="wrap footer-grid">'
        '<div><a class="brand" href="/">%s<span>PetTripFinder<small>Columbus</small></span></a>'
        '<p class="note">Verified pet-travel guide for Columbus, Ohio. Temporary imagery shown for this '
        'review will be replaced by compliant Google Places media and approved city imagery.</p></div>'
        '<div><h4>Directory</h4><a href="/pet-friendly-hotels/">Hotels</a><a href="/pet-friendly-parks/">Parks</a>'
        '<a href="/pet-friendly-restaurants/">Restaurants</a></div>'
        '<div><h4>Planning</h4><a href="/pet-friendly-hotels/policy-comparison/">Compare policies</a>'
        '<a href="/pet-friendly-hotels/dublin/">Columbus corridors</a>'
        '<a href="/methodology/">How verification works</a></div>'
        '<div><h4>Company</h4><a href="/about/">About</a><a href="/contact/">Contact</a>'
        '<a href="/methodology/">Privacy</a></div></div></footer>'
    ) % _PAW

    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>Pet-Friendly Hotels in Columbus, Ohio | PetTripFinder</title>'
        '<meta name="description" content="Find a Columbus hotel that actually works for your pet. Compare '
        'real, verified pet policies, exact fees, and pet limits for 14 evidence-backed hotels.">'
        '<meta name="robots" content="index, follow">'
        '<link rel="canonical" href="https://pettripfinder.com/">'
        '<style>%s\n%s</style></head><body>'
        '<a class="skip skip-link" href="#main">Skip to content</a>'
        '%s%s<main id="main" class="main">%s%s%s</main>%s%s</body></html>'
    ) % (PROTOTYPE_CSS, _INTEGRATION_CSS, header, hero, hotels, trust, trip, footer, _MOBILE_NAV_JS)


def copy_assets(out_dir: Path) -> int:
    """Copy the approved temporary prototype assets into ``<out_dir>/assets/``.
    Returns the number of files copied."""
    dst = Path(out_dir) / "assets"
    dst.mkdir(parents=True, exist_ok=True)
    n = 0
    for p in sorted(_ASSETS_DIR.glob("*.jpg")):
        shutil.copyfile(p, dst / p.name)
        n += 1
    return n
