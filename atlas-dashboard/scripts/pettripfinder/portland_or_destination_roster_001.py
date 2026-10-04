"""PTF-PORTLAND-OR-HARDENED-SOURCE-READY-001 -- Phase 10: the official destination-marketing rosters.

EVERY BUREAU WAS MEASURED, NOT ASSUMED
--------------------------------------
The standing rule is to MEASURE a convention and visitors bureau before spending anything on it (the San Diego
and Jacksonville finding: never assume Simpleview, never assume a category filter works). The Portland-area bureaus
answered this plain client on 2026-10-03 like this:

  * TRAVEL PORTLAND (travelportland.com) -- WordPress (theme "dragonspell"), NOT Simpleview: ``get_simple_token``
    answers 301 to the home page. Its sitemaps publish only editorial pages, events and meeting venues; its partners
    are a custom post type ``poi`` exposed on the site's own public WordPress REST API (``/wp-json/wp/v2/poi``) with
    the bureau's own taxonomy ``poi-category`` -- category 57 "Lodging" holds 222 POIs (measured). The REST record
    carries the name, the bureau's own category, latitude / longitude and a Google place id but NO street; the
    bureau's own map card -- the call its pages make when a reader opens a POI, ``/wp-admin/admin-ajax.php?action=
    nmn_poi&poi_id=<id>`` -- states "postAddress" (street, city, state, ZIP), "postPhone", "postWebsite" and
    "postCategories". robots.txt disallows only /wp-admin/ and explicitly ALLOWS /wp-admin/admin-ajax.php. One
    request a second is used.
  * VISIT VANCOUVER USA (visitvancouverusa.com -> visitvancouverwa.com) -- a **Simpleview** install: robots.txt
    ``Crawl-delay: 2`` and ``Disallow: /plugins/crm/count/``; it issues its own ``get_simple_token`` (32 hex,
    measured) and answers its own public listings endpoint, which returns every partner WITH street, city, state,
    postal code, telephone, website and the bureau's own category. Read with an EMPTY filter, 100 rows a page,
    honouring the Crawl-delay. Washington partners keep their Washington state.
  * EXPLORE WASHINGTON COUNTY (tualatinvalley.org) -- answers this plain client 403 Forbidden on robots.txt and on
    its home page (an nginx access control). Not walked, and not worked around; Beaverton / Hillsboro / Tigard /
    Tualatin / Forest Grove are covered by the brand inventories, OSM, Travel Portland's own lodging POIs, Places
    and the competitor challenge instead.
  * OREGON'S MT. HOOD TERRITORY (mthoodterritory.com, Clackamas County) -- robots.txt ``Disallow: /partners/``, which
    is where its partner listings live. Honoured: not walked.
  * TRAVEL OREGON (traveloregon.com) -- statewide; no answer to this client inside 20 s. Not a lodging partner roster
    of this market; not walked.
  * TRAVEL SALEM, TRAVEL LANE COUNTY, HOOD RIVER COUNTY, VISIT THE OREGON COAST, VISIT BEND -- refused places'
    bureaus and never walked: a refused place's inventory is not this market's census.

A ROSTER ROW IS NOT A POLICY, AND NOT AN ADMISSION
--------------------------------------------------
Everything here is IDENTITY and ROUTING evidence (tier 3). The bureau's category proposes that a partner is
lodging; the property's own page decides what it is. Travel Portland's "pet-friendly" venue feature is a bureau
TAG and is never read as a policy. The bureau's own city label decides NOTHING: admission is the property's own
postal code against the corridor registry.

Outputs:
  launch_packages/pettripfinder/markets/reports/portland_or_destination_roster_001.json
  data/acquisition/portland_or_roster_001/<sha256>.bin   (kept partners' documents as returned)
"""
from __future__ import annotations

import argparse
import gzip
import html as _html
import hashlib
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import portland_or_geography_001 as GEO  # noqa: E402

WORK_ORDER = "PTF-PORTLAND-OR-HARDENED-SOURCE-READY-001"
MARKET_ID = "portland-or"
REPORTS = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports")
DOCS = os.path.join(_DASH, "data", "acquisition", "portland_or_roster_001")
OUT = os.path.join(REPORTS, "portland_or_destination_roster_001.json")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")

#: Each bureau publishes its partners differently, so each one carries its OWN discovery method, measured:
#:   SITEMAP_DIRECTORY  the sitemap index publishes every listing page (both Craft installs do)
#:   SEED_PAGE          the sitemap publishes only editorial pages, and one lodging page links every partner
#: (bureau id, label, robots url, method, entry url, listing-path marker, cap)
BUREAUS = [
    ("travel-portland", "Travel Portland (Portland's convention and visitors bureau)",
     "https://www.travelportland.com/robots.txt", "WP_REST_POI", "https://www.travelportland.com", "57", 300),
    ("visit-vancouver-usa", "Visit Vancouver USA (Vancouver, Washington's destination marketing organization)",
     "https://www.visitvancouverwa.com/robots.txt", "SIMPLEVIEW_API", "https://www.visitvancouverwa.com", "", 80),
    ("explore-washington-county", "Explore Washington County (Washington County Visitors Association)",
     "https://www.tualatinvalley.org/robots.txt", "REFUSED_ENTRY", "https://www.tualatinvalley.org/", "", 0),
]
#: The bureau's own robots.txt Crawl-delay, honoured between listing pages.
CRAWL_DELAY_SECONDS = 2.0

#: SITEMAP_WP_LISTING_NAMED: a WordPress bureau whose listing sitemap carries every kind of partner. Only a slug
#: that names lodging is fetched -- a DISCOVERY preselection, never a classification: the page's own text and
#: the property's own site decide what it is.
_LODGING_SLUG = re.compile(r"hotel|inn\b|inn-|-inn|suites|lodge|motel|resort|residence|hostel|"
                           r"bed-and-breakfast|b-and-b|hampton|marriott|hilton|hyatt|holiday|courtyard|"
                           r"fairfield|staybridge|candlewood|homewood|home2|springhill|towneplace|best-western|"
                           r"comfort|quality|la-quinta|days-inn|super-8|motel-6|extended-stay|origin|eddy", re.I)

#: Sitemap children that can hold partner listings. A Craft install names them `section-partnerDirectory`;
#: a WordPress + Yoast install names them `<posttype>-sitemap.xml`.
_CHILD_KEEP = re.compile(r"partnerdirectory|partner-directory|listing|directory|places|post-sitemap|"
                         r"page-sitemap|lodging|hotel", re.I)
_CHILD_SKIP = re.compile(r"event|blog|press|personaquiz|micrositepartner|image|attachment|category|"
                         r"author|tag|deal", re.I)
_LOC = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>", re.I)

#: Read off the page, never guessed. Any category containing one of these words is a LODGING category.
LODGING_CATEGORY_WORDS = ("hotel", "motel", "inn", "resort", "lodging", "lodge", "bed and breakfast",
                          "bed & breakfast", "b&b", "accommodation", "stay", "suites", "campground",
                          "rv park", "vacation rental", "condo", "hostel")
#: Lodging categories that are NEVER a census identity; kept for the accounting and refused by decision.
NON_CENSUS_CATEGORY_WORDS = ("vacation rental", "condo", "campground", "rv park", "house rental",
                             "home rental", "cottage rental")

_TITLE_SUMMARY = re.compile(
    r'data-mapinfo-title[^>]*>(?P<title>.*?)</span>\s*<span class="map-infowindow__summary">(?P<summary>.*?)</span>',
    re.S)
_CATEGORY = re.compile(r'data-dms-category-name="([^"]*)"')
_PARTNER_ID = re.compile(r'data-dms-partner-id="([0-9]+)"')
_WEBSITE = re.compile(r'href="(https?://[^"]+)"[^>]{0,400}?data-dms-partner-detail-website-click', re.S)
_WEBSITE_ALT = re.compile(r'data-dms-partner-detail-website-click[^>]{0,400}?href="(https?://[^"]+)"', re.S)
_TEL = re.compile(r'href="tel:([^"]+)"')
#: A Yoast/WordPress bureau publishes its premises in JSON-LD instead of a Craft map window.
_LDJSON = re.compile(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', re.S)
#: schema.org types that are themselves a lodging category statement by the bureau.
LODGING_SCHEMA_TYPES = ("lodgingbusiness", "hotel", "motel", "resort", "bedandbreakfast", "hostel",
                        "campground", "inn", "apartment", "vacationrental")
#: The bureau's map window is a FREE-TEXT block, not a structured address, and it does not always hold two
#: lines. Measured on this market's own partners:
#:   "4670 Salisbury Road | I-95 & J.Turner Butler Blvd. | Jacksonville, Florida 32256 |"   (a CROSS STREET)
#:   "1 Ocean Trace Blvd. | St. Augustine, Florida |"                                        (no postal code)
#:   "St. Augustine, Florida 32084 |"                                                        (no street at all)
#: Parsing it as "<street> | <city, state zip>" put the cross street INSIDE the street, which split one
#: premises into two census rows for Marriott Jacksonville (4670 Salisbury Road) and the Ramada at 3130
#: Hartley Road -- each appearing once with its cross street and once without. The parser therefore reads from
#: the END: the LAST segment that states "city, state ZIP" is the locality, the FIRST segment is the street,
#: and anything between them is a cross street or landmark, recorded separately and NEVER part of the street.
_CITY_STATE_ZIP = re.compile(r"^(?P<city>[^,|]+),\s*(?P<state>[A-Za-z .]+?)(?:\s+(?P<zip>\d{5})(?:-\d{4})?)?$")

_STATE_CODE = {"washington": "WA", "wa": "WA", "wash": "WA", "oregon": "OR", "or": "OR", "ore": "OR"}


class Stats(object):
    def __init__(self):
        self.requests = 0
        self.bytes = 0


def _decode(resp, raw):
    enc = (resp.headers.get("Content-Encoding") or "").lower()
    try:
        if "gzip" in enc:
            return gzip.GzipFile(fileobj=io.BytesIO(raw)).read()
        if "deflate" in enc:
            return zlib.decompress(raw, -zlib.MAX_WBITS)
    except Exception:
        return raw
    return raw


def persist(body):
    if not body:
        return None
    digest = hashlib.sha256(body).hexdigest()
    os.makedirs(DOCS, exist_ok=True)
    path = os.path.join(DOCS, digest + ".bin")
    if not os.path.exists(path):
        with open(path, "wb") as fh:
            fh.write(body)
    return digest


def fetch(url, stats, timeout=35, keep=False):
    row = OrderedDict([("url", url), ("status", None), ("final_url", None), ("bytes", 0), ("sha256", None),
                       ("error", None)])
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9", "Accept-Encoding": "gzip, deflate"})
    stats.requests += 1
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = _decode(resp, resp.read())
            row.update(status=resp.getcode(), final_url=resp.geturl(), bytes=len(body))
            if keep:
                row["sha256"] = persist(body)
            stats.bytes += len(body)
            return row, body
    except urllib.error.HTTPError as exc:
        row["status"], row["final_url"] = exc.code, url
        return row, b""
    except Exception as exc:
        row["error"] = "%s: %s" % (type(exc).__name__, str(exc)[:160])
        return row, b""


def _clean_html(fragment):
    txt = re.sub(r"<br\s*/?>", " | ", fragment or "")
    txt = re.sub(r"<[^>]+>", "", txt)
    # UNESCAPED TWICE, because this bureau double-escapes: a partner named "Ramada Hotel & Conference Center"
    # arrives as "&amp;amp;" and a single pass leaves "&amp;" sitting inside the street.
    txt = _html.unescape(_html.unescape(txt)).replace("\xa0", " ")
    return " ".join(txt.split())


def _parse_craft(text):
    """(name, street, city, state, zip, extras) from a Craft bureau's own map-window block."""
    m = _TITLE_SUMMARY.search(text)
    if not m:
        return None
    name = _clean_html(m.group("title"))
    summary = _clean_html(m.group("summary"))
    segs = [seg.strip() for seg in summary.split("|") if seg.strip()]
    city = state = zipc = ""
    locality_at = None
    for i in range(len(segs) - 1, -1, -1):
        am = _CITY_STATE_ZIP.match(segs[i])
        if am:
            city = am.group("city").strip()
            st = (am.group("state") or "").strip().rstrip(".").lower()
            state = _STATE_CODE.get(st, (am.group("state") or "").strip()[:2].upper())
            zipc = am.group("zip") or ""
            locality_at = i
            break
    if locality_at is None:
        return OrderedDict([("name", name), ("street", summary), ("city", ""), ("state", ""),
                            ("postal_code", ""), ("address_extras", [])])
    street = segs[0] if locality_at > 0 else ""
    extras = segs[1:locality_at]
    return OrderedDict([("name", name), ("street", street), ("city", city), ("state", state),
                        ("postal_code", zipc), ("address_extras", extras)])


def _ld_nodes(text):
    """Every schema.org node on the page, flattened, skipping the bureau's own identity."""
    for block in _LDJSON.findall(text):
        try:
            data = json.loads(block)
        except ValueError:
            continue
        nodes = data.get("@graph") if isinstance(data, dict) and data.get("@graph") else (
            data if isinstance(data, list) else [data])
        for node in nodes:
            if isinstance(node, dict) and "#identity" not in str(node.get("@id") or ""):
                yield node


def _schema_types(text):
    """The bureau's own schema.org types for the partner: its category statement in another vocabulary."""
    out = []
    for node in _ld_nodes(text):
        t = node.get("@type")
        for one in (t if isinstance(t, list) else [t]):
            one = str(one or "").strip()
            if one and one.lower() in LODGING_SCHEMA_TYPES and one not in out:
                out.append(one)
    return out


_WP_TITLE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.S)
_OG_TITLE = re.compile(r'<meta property="og:title" content="([^"]+)"')
_WP_ADDRESS = re.compile(r"(?P<street>\d{2,6}\s+(?:[NSEW]\.?\s+|North\s+|South\s+|East\s+|West\s+)?"
                         r"[A-Z][A-Za-z0-9 .'-]{2,40}?\s(?:Highway|Hwy|Street|St|Avenue|Ave|Boulevard|Blvd|Drive|"
                         r"Dr|Road|Rd|Way|Lane|Ln|Place|Pl|Parkway|Pkwy|Court|Ct|Circle|Cir|Loop|Trail|Tr)\.?)"
                         r"(?:,\s*|\s+)(?P<city>Portland|Beaverton|Hillsboro|Tigard|Lake Oswego|Gresham|"
                         r"Tualatin|Wilsonville|Clackamas|Happy Valley|Troutdale|Fairview|Wood Village|Milwaukie|"
                         r"Oregon City|West Linn|Gladstone|Sherwood|Forest Grove|Cornelius|Vancouver),?\s*"
                         r"(?:OR|Oregon|WA|Washington)\s+"
                         r"(?P<zip>\d{5})", re.I)


#: A PAGE-WIDE ADDRESS IS PAGE CHROME, NOT A PARTNER FACT -- measured, not assumed. Every one of Visit
#: Oceanside's 26 hotel pages carries the SAME advertising block ("928 North Coast Hwy, Oceanside, CA 92054" --
#: the Courtyard / SpringHill Suites building) a few hundred characters after its own title, and a first cut of
#: this parser bound that street to Oceanside Marina Suites, the Days Inn, the Motel 6 and the Ramada. An address,
#: or an outbound host, that appears on BOARD_MIN listing pages or more of ONE bureau is that bureau's chrome and
#: is never read as any partner's premises or route. The rule is order-independent: it is computed over the whole
#: walked set before any page is parsed.
BOARD_MIN = 3
_WP_ADDRESS_ALL = _WP_ADDRESS


def _address_key(street, zipc):
    return (" ".join((street or "").lower().replace(".", "").split()), zipc or "")


#: PHOENIX (measured on Tempe Tourism): the page prints "Phone 520-536-8100 Location 1929 E. Rio Salado Parkway
#: Tempe, AZ 85288" with no separator, and the address pattern began at the phone's last four digits ("8100
#: Location 1929 E. ..."). The street is the run from the RIGHTMOST house number that still has a street after it.
_LAST_HOUSE_NUMBER = re.compile(r".*\b(\d{1,6}\s+(?:[NSEW]\.?\s+)?[A-Z].*)$")


def _street_from_last_number(street):
    m = _LAST_HOUSE_NUMBER.match(street or "")
    return m.group(1) if m else street


def _wp_addresses(text):
    return [(_street_from_last_number(" ".join(a.group("street").split())), a.group("city"), a.group("zip"))
            for a in _WP_ADDRESS_ALL.finditer(_clean_html(text))]


def _wp_hosts(text):
    return {_registrable_host(u) for u in re.findall(r'href="(https?://[^"\'<>]+)"', text)}


def _parse_wp_text(text, chrome_addresses=frozenset()):
    """(name, street, city, state, zip) from a WordPress bureau page that states its address only in text. The
    street is taken ONLY together with a stated "City, CA ZIP" in the same run of text, and never when that
    address is the bureau's own page chrome (``chrome_addresses``). A page whose only full address is chrome
    keeps its NAME and its route and states no premises -- the property's own page supplies that."""
    m = _WP_TITLE.search(text)
    name = _clean_html(m.group(1)) if m else ""
    if not name:
        # PHOENIX (measured on Tempe Tourism): the partner's name is an <h2>, and the page's own og:title states it
        # as "<partner> - <bureau>". The bureau suffix is the bureau's own page chrome and is removed.
        og = _OG_TITLE.search(text)
        name = _clean_html(og.group(1)).rsplit(" - ", 1)[0].strip() if og else ""
    if not name:
        return None
    for street, city, zipc in _wp_addresses(text):
        if _address_key(street, zipc) in chrome_addresses:
            continue
        return OrderedDict([("name", name), ("street", street), ("city", city), ("state", GEO.state_for_postal(zipc)),
                            ("postal_code", zipc), ("address_extras", [])])
    return OrderedDict([("name", name), ("street", ""), ("city", ""), ("state", ""), ("postal_code", ""),
                        ("address_extras", [])])


def _wp_own_website(text, chrome_hosts):
    """The partner's own site on a WordPress bureau page: the FIRST outbound link after the page's own title that
    is neither a social / bureau host nor a host the bureau prints on every page."""
    i = text.find("<h1")
    for url in re.findall(r'href="(https?://[^"\'<>]+)"', text[max(i, 0):]):
        if _NOT_A_PARTNER_HOST.search(url) or _registrable_host(url) in chrome_hosts:
            continue
        if re.search(r"twitter\.com|x\.com|instagram|facebook|linkedin|edgepilot", url, re.I):
            continue
        return url
    return ""


def wp_chrome(texts):
    """(addresses, hosts) printed on BOARD_MIN or more of one bureau's listing pages."""
    addr, hosts = Counter(), Counter()
    for t in texts:
        for k in {_address_key(s, z) for s, _c, z in _wp_addresses(t)}:
            addr[k] += 1
        for h in _wp_hosts(t):
            hosts[h] += 1
    return (frozenset(k for k, n in addr.items() if n >= BOARD_MIN),
            frozenset(h for h, n in hosts.items() if n >= BOARD_MIN and h))


def _parse_ldjson(text):
    """(name, street, city, state, zip, phone) from a bureau's JSON-LD LodgingBusiness / Hotel node."""
    best = None
    for node in _ld_nodes(text):
        addr = node.get("address")
        if not isinstance(addr, dict) or not addr.get("streetAddress"):
            continue
        t = node.get("@type")
        types = [str(x or "").lower() for x in (t if isinstance(t, list) else [t])]
        if any(x in ("touristinformationcenter", "website", "webpage", "organization") for x in types):
            continue
        row = OrderedDict([("name", " ".join(str(node.get("name") or "").split())),
                           ("street", " ".join(str(addr.get("streetAddress") or "").split())),
                           ("city", " ".join(str(addr.get("addressLocality") or "").split())),
                           ("state", (str(addr.get("addressRegion") or "")[:2] or "").upper()),
                           ("postal_code", "".join(ch for ch in str(addr.get("postalCode") or "")
                                                   if ch.isdigit())[:5]),
                           ("phone", " ".join(str(node.get("telephone") or "").split()))])
        if any(x in LODGING_SCHEMA_TYPES for x in types):
            return row
        best = best or row
    return best


#: A BUREAU SOMETIMES LINKS A RESELLER, NOT THE PARTNER. Measured on this market's own partners: Visit
#: Jacksonville publishes an AGODA listing as River City Inn's outbound link, and a WEBREZ booking-engine
#: session as Sea Cottages of Amelia's; the Amelia Island CVB publishes ResNexus and ThinkReservations booking
#: sessions for seven of its historic inns. Those are places to BUY a room, not the property's own page, and a
#: census that adopts one as an identity's official_url binds the row to a reseller -- which then collides with
#: the property's own site when a capture lane reads it, and HOLDS a publishable row for a conflict this order
#: manufactured. The link is REFUSED as a route and RECORDED as what the bureau published, so nothing is hidden.
#:
#: THE TEST IS ON THE HOST, NOT ON A SUBSTRING, and that was measured the hard way: a first cut matched the
#: token "hotels.com" anywhere in the URL and refused FORTY links, because "hotels.com" is a substring of
#: "choicehotels.com", "wyndhamhotels.com" and "magnusonhotels.com" -- three brands' OWN hosts. It is the same
#: class of defect as "jacksonville-or" matching inside "jacksonville-orange-park" in the brand-inventory
#: filter. A host test cannot make that mistake.
RESELLER_HOSTS = frozenset("""
agoda.com booking.com expedia.com hotels.com priceline.com orbitz.com travelocity.com trivago.com kayak.com
hotwire.com tripadvisor.com airbnb.com vrbo.com hostelworld.com despegar.com trip.com ctrip.com
makemytrip.com guestreservations.com reservations.com roomkey.com snaptravel.com
webrez.com resnexus.com cloudbeds.com innroad.com thinkreservations.com synxis.com travelclick.com
pegsbe.com bookingengine.com securebooking.com reservenow.com opentable.com eventbrite.com
facebook.com instagram.com yelp.com google.com
""".split())


def _registrable_host(url):
    """The last two labels of a URL's host, lower-cased ("www.choicehotels.com" -> "choicehotels.com")."""
    m = re.match(r"https?://([^/?#]+)", (url or "").strip(), re.I)
    if not m:
        return ""
    host = m.group(1).split("@")[-1].split(":")[0].lower().strip(".")
    parts = [p for p in host.split(".") if p]
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def is_reseller_route(url):
    """True when the bureau's outbound link is a reseller or a booking engine rather than the partner's site."""
    host = _registrable_host(url)
    if not host:
        return False
    if host in RESELLER_HOSTS:
        return True
    # a booking-engine SUBDOMAIN of the property's own domain ("book.example.com", "reserve6.example.com")
    m = re.match(r"https?://([^/?#]+)", (url or "").strip(), re.I)
    sub = m.group(1).lower().split(".")[0] if m else ""
    return bool(re.match(r"^(book|booking|reserve|reservations|secure|bookdirect)\d*$", sub))


#: Hosts a bureau links for its own reasons, never the partner's own site.
_NOT_A_PARTNER_HOST = re.compile(
    r"(travelportland\.com|visitvancouverwa\.com|visitvancouverusa\.com|traveloregon|cloudinary|"
    r"dragonspell|skynav\.app|ecwid|"
    r"ecomm\.events|"
    r"google|gstatic|gmpg\.org|schema\.org|w3\.org|facebook|instagram|twitter|x\.com|youtube|pinterest|"
    r"tiktok|linkedin|ajax\.googleapis|fonts\.|cloudflare|cloudfront|wp\.com|gravatar|api\.w\.org|"
    r"simpleviewinc|tripadvisor|yelp|expedia|booking\.com|hotels\.com|opentable|eventbrite|"
    r"jsdelivr)", re.I)


def _outbound_website(text, listing_url):
    """The partner's OWN site, when the bureau publishes it as a plain outbound link."""
    for url in re.findall(r'href="(https?://[^"\'<>]+)"', text):
        if _NOT_A_PARTNER_HOST.search(url):
            continue
        if url.rstrip("/") == listing_url.rstrip("/"):
            continue
        return url
    return ""


def _is_lodging(categories):
    for c in categories:
        cl = c.lower()
        if any(w in cl for w in LODGING_CATEGORY_WORDS):
            return True
    return False


def _census_eligible(categories):
    """A lodging category that could be a hotel identity. A vacation-rental or condo category never is."""
    for c in categories:
        cl = c.lower()
        if any(w in cl for w in NON_CENSUS_CATEGORY_WORDS):
            continue
        if any(w in cl for w in LODGING_CATEGORY_WORDS):
            return True
    return False


SIMPLEVIEW_FIELDS = OrderedDict((k, 1) for k in (
    "recid", "title", "address1", "address2", "city", "state", "zip", "phone", "weburl", "categories",
    "latitude", "longitude", "detailURL", "typeName"))
#: MEASURED: with the full field set the endpoint answers 200 to 100 / 150 / 200-row pages and 403 to 250 and
#: 500 (a response-size ceiling, not a field rule); 100 is used, well inside it.
SIMPLEVIEW_PAGE = 100


def walk_simpleview(bureau, stats, cap):
    """Every partner from a Simpleview bureau's OWN public listings endpoint -- the call its listing pages make.
    The whole document set is paged SIMPLEVIEW_PAGE at a time; every page is persisted under its sha256."""
    bid, label, robots_url, method, host, _marker, _cap = bureau
    blk = OrderedDict([
        ("bureau_id", bid), ("label", label), ("cms", "SIMPLEVIEW"), ("discovery_method", method),
        ("robots", None), ("entry", None), ("children_walked", []), ("listing_urls_published", 0),
        ("listing_pages_read", 0), ("request_cap", cap), ("requests_spent", 0), ("cap_reached", False),
        ("categories_seen", OrderedDict()), ("schema_types_seen", OrderedDict()), ("lodging_partners", 0),
        ("rows", []), ("disposition", None),
    ])
    rrow, rbody = fetch(robots_url, stats)
    blk["robots"] = OrderedDict([("document", rrow), ("body", rbody.decode("utf-8", "replace").strip()[:900])])
    trow, tbody = fetch(host + "/plugins/core/get_simple_token/", stats)
    token = tbody.decode("utf-8", "replace").strip()
    blk["entry"] = trow
    if trow.get("status") != 200 or not re.match(r"^[0-9a-f]{16,64}$", token):
        blk["disposition"] = "SIMPLEVIEW_TOKEN_NOT_ISSUED__STATUS_%s" % trow.get("status")
        return blk
    docs, skip, total = [], 0, None
    while blk["requests_spent"] < cap:
        q = json.dumps(OrderedDict([("filter", OrderedDict()), ("options", OrderedDict([
            ("limit", SIMPLEVIEW_PAGE), ("skip", skip), ("count", True), ("fields", SIMPLEVIEW_FIELDS),
            ("sort", OrderedDict([("recid", 1)]))]))]), separators=(",", ":"))
        url = host + "/includes/rest_v2/plugins_listings_listings/find/?" + urllib.parse.urlencode(
            [("json", q), ("token", token)])
        if blk["requests_spent"]:
            time.sleep(CRAWL_DELAY_SECONDS)
        prow, pbody = fetch(url, stats, timeout=60, keep=True)
        blk["requests_spent"] += 1
        prow["url"] = prow["url"].split("&token=")[0] + "&token=<session>"
        blk["children_walked"].append(prow)
        try:
            page = json.loads(pbody.decode("utf-8", "replace")).get("docs") or {}
        except ValueError:
            break
        got = page.get("docs") or []
        total = page.get("count", total)
        docs.extend(got)
        skip += len(got)
        if not got or (total is not None and skip >= total):
            break
    blk["listing_urls_published"] = total or 0
    blk["listing_pages_read"] = len(docs)
    blk["cap_reached"] = total is not None and len(docs) < total
    cats = Counter()
    seen = set()
    for d in sorted(docs, key=lambda x: int(x.get("recid") or 0)):
        rec = d.get("recid")
        if rec in seen:
            continue
        seen.add(rec)
        categories = sorted({"%s / %s" % (c.get("catname") or "", c.get("subcatname") or "")
                             for c in (d.get("categories") or []) if isinstance(c, dict)})
        for c in categories:
            cats[c] += 1
        if not _is_lodging(categories):
            continue
        blk["lodging_partners"] += 1
        website = " ".join(str(d.get("weburl") or "").split())
        if website and not re.match(r"^https?://", website, re.I):
            website = "https://" + website.lstrip("/")
        refused_link = ""
        if website and is_reseller_route(website):
            refused_link, website = website, ""
        z = "".join(ch for ch in str(d.get("zip") or "") if ch.isdigit())[:5]
        city = " ".join(str(d.get("city") or "").split())
        klass, slug, why = GEO.classify_postal(z, city)
        street = " ".join(" ".join(str(d.get(k) or "") for k in ("address1",)).split())
        blk["rows"].append(OrderedDict([
            ("lane", "DESTINATION_ROSTER"),
            ("bureau_id", bid),
            ("partner_id", str(rec or "")),
            ("name", _html.unescape(" ".join(str(d.get("title") or "").split()))),
            ("street", street),
            ("city", city),
            ("state", (" ".join(str(d.get("state") or "").split()) or "")[:2].upper()),
            ("postal_code", z),
            ("phone", " ".join(str(d.get("phone") or "").split())),
            ("official_url", website),
            ("bureau_link_refused_as_a_route", refused_link),
            ("why_refused", ("the bureau published a RESELLER or booking-engine link rather than the partner's "
                             "own site; a place to buy a room is not a first-party route") if refused_link else ""),
            ("address_extras", [x for x in [" ".join(str(d.get("address2") or "").split())] if x]),
            ("bureau_categories", categories),
            ("bureau_schema_types", []),
            ("census_eligible_category", _census_eligible(categories)),
            ("listing_url", host + str(d.get("detailURL") or "")),
            ("listing_sha256", blk["children_walked"][-1]["sha256"] if blk["children_walked"] else None),
            ("lat", d.get("latitude")), ("lng", d.get("longitude")),
            ("geography_class", klass),
            ("corridor_slug", slug),
            ("membership_reason", why),
        ]))
    blk["categories_seen"] = OrderedDict(cats.most_common())
    blk["disposition"] = ("ROSTER_ANSWERED_THIS_CLIENT" if blk["rows"] else
                          "ROSTER_ANSWERED_BUT_NO_LODGING_PARTNER_FOUND")
    return blk


#: TRAVEL PORTLAND's own map card states its address as ONE line: "525 SW Morrison St, Portland, OR 97204". Read from
#: the END: the last "City, ST ZIP" run is the locality and everything before it is the street.
_TP_ADDRESS = re.compile(r"^(?P<street>.+?),\s*(?P<city>[A-Za-z][A-Za-z .'-]{1,40}?),\s*(?P<state>[A-Z]{2})\.?"
                         r"\s+(?P<zip>\d{5})(?:-\d{4})?(?:,\s*(?:USA|United States))?\s*$")
TP_REST_PAGE = 100


#: MEASURED on the bureau's own cards: some omit the comma between street and city ("1321 SW Washington St Portland,
#: OR 97205") and some state only the locality ("Rhododendron, OR 97049"). The street is then the run before a
#: municipality the card itself names; a locality-only card states no street and binds nothing by itself.
_TP_CITIES = ("Portland|Beaverton|Hillsboro|Tigard|Lake Oswego|Gresham|Tualatin|Wilsonville|Clackamas|Happy Valley|"
              "Troutdale|Fairview|Wood Village|Milwaukie|Oregon City|West Linn|Gladstone|Sherwood|Forest Grove|"
              "Cornelius|Vancouver|Camas|Washougal|Hood River|Salem|Newberg")
_TP_NO_COMMA = re.compile(r"^(?P<street>\d.+?)\s+(?P<city>%s),?\s*(?P<state>[A-Z]{2})\.?\s+(?P<zip>\d{5})(?:-\d{4})?"
                          r"(?:,\s*(?:USA|United States))?\s*$" % _TP_CITIES)
_TP_LOCALITY_ONLY = re.compile(r"^(?P<city>[A-Za-z][A-Za-z .'-]{1,40}?),\s*(?P<state>[A-Z]{2})\.?\s+(?P<zip>\d{5})"
                               r"(?:-\d{4})?\s*$")


def _parse_tp_address(line):
    line = " ".join(_html.unescape(line or "").replace("\xa0", " ").split())
    m = _TP_ADDRESS.match(line)
    if m and re.match(r"^\d", m.group("street")):
        return (" ".join(m.group("street").split()), m.group("city").strip(), m.group("state").upper(),
                m.group("zip"), "")
    m = _TP_NO_COMMA.match(line)
    if m:
        return (" ".join(m.group("street").split()), m.group("city").strip(), m.group("state").upper(),
                m.group("zip"), "")
    m = _TP_LOCALITY_ONLY.match(line)
    if m:
        return "", m.group("city").strip(), m.group("state").upper(), m.group("zip"), line
    if m is None and _TP_ADDRESS.match(line):
        m = _TP_ADDRESS.match(line)
        return "", m.group("city").strip(), m.group("state").upper(), m.group("zip"), line
    return "", "", "", "", line


def _tp_name(card, poi_title):
    """The bureau card's own title, or -- when the card's bytes carry a replacement character (an en dash the card
    endpoint did not encode as UTF-8) -- the same POI's REST title."""
    name = _html.unescape(" ".join(str(card.get("postTitle") or "").split()))
    if (not name or "\ufffd" in name) and poi_title:
        name = _html.unescape(" ".join(str(poi_title).split()))
    # both carry it: the byte the endpoint failed to encode is a dash between two name parts
    return name.replace("�", "-")


def walk_wp_rest_poi(bureau, stats, cap):
    """Every POI in the bureau's OWN lodging category (its public WordPress REST API), then each POI's own map card
    (the admin-ajax call its pages make), which states the premises."""
    bid, label, robots_url, method, host, category_id, _cap = bureau
    blk = OrderedDict([
        ("bureau_id", bid), ("label", label), ("cms", "WORDPRESS_DRAGONSPELL"), ("discovery_method", method),
        ("robots", None), ("entry", None), ("children_walked", []), ("listing_urls_published", 0),
        ("listing_pages_read", 0), ("request_cap", cap), ("requests_spent", 0), ("cap_reached", False),
        ("categories_seen", OrderedDict()), ("schema_types_seen", OrderedDict()), ("lodging_partners", 0),
        ("rows", []), ("disposition", None),
    ])
    rrow, rbody = fetch(robots_url, stats)
    blk["robots"] = OrderedDict([("document", rrow), ("body", rbody.decode("utf-8", "replace").strip()[:900])])
    pois, page = [], 1
    while page <= 10:
        url = "%s/wp-json/wp/v2/poi?poi-category=%s&per_page=%d&page=%d&orderby=id&order=asc" % (
            host, category_id, TP_REST_PAGE, page)
        prow, pbody = fetch(url, stats, timeout=60, keep=True)
        blk["requests_spent"] += 1
        blk["children_walked"].append(prow)
        if page == 1:
            blk["entry"] = prow
        try:
            got = json.loads(pbody.decode("utf-8", "replace"))
        except ValueError:
            got = []
        if prow.get("status") != 200 or not isinstance(got, list) or not got:
            break
        pois.extend(got)
        if len(got) < TP_REST_PAGE:
            break
        page += 1
        time.sleep(1.0)
    blk["listing_urls_published"] = len(pois)
    cats = Counter()
    for poi in sorted(pois, key=lambda x: int(x.get("id") or 0)):
        if blk["requests_spent"] >= cap:
            blk["cap_reached"] = True
            break
        pid = poi.get("id")
        time.sleep(1.0)
        crow, cbody = fetch("%s/wp-admin/admin-ajax.php?action=nmn_poi&poi_id=%s" % (host, pid), stats, timeout=45)
        blk["requests_spent"] += 1
        blk["listing_pages_read"] += 1
        try:
            card = (json.loads(cbody.decode("utf-8", "replace")) or {}).get("data") or {}
        except ValueError:
            card = {}
        if not card:
            continue
        crow["sha256"] = persist(cbody)
        categories = ["Lodging / %s" % (poi.get("category") or "lodging")]
        for c in [x.strip() for x in _html.unescape(str(card.get("postCategories") or "")).split(",") if x.strip()]:
            categories.append("Bureau card / %s" % c)
        for c in categories:
            cats[c] += 1
        blk["lodging_partners"] += 1
        street, city, state, zipc, unparsed = _parse_tp_address(card.get("postAddress") or "")
        website = " ".join(str(card.get("postWebsite") or "").split())
        refused_link = ""
        if website and is_reseller_route(website):
            refused_link, website = website, ""
        klass, slug, why = GEO.classify_postal(zipc, city)
        name = _tp_name(card, (poi.get("title") or {}).get("rendered") or "")
        blk["rows"].append(OrderedDict([
            ("lane", "DESTINATION_ROSTER"), ("bureau_id", bid), ("partner_id", str(pid)),
            ("name", name), ("street", street), ("city", city), ("state", state),
            ("postal_code", zipc), ("phone", " ".join(str(card.get("postPhone") or "").split())),
            ("official_url", website),
            ("bureau_link_refused_as_a_route", refused_link),
            ("why_refused", ("the bureau published a RESELLER or booking-engine link rather than the partner's "
                             "own site; a place to buy a room is not a first-party route") if refused_link else ""),
            ("address_extras", [unparsed] if unparsed else []), ("bureau_categories", categories),
            ("bureau_schema_types", []),
            ("census_eligible_category", (poi.get("category") or "") not in ("vacation-rental", "campground")),
            ("bureau_subtype", poi.get("category") or ""),
            ("listing_url", "%s/wp-json/wp/v2/poi/%s" % (host, pid)), ("listing_sha256", crow["sha256"]),
            ("rest_title", _html.unescape(" ".join(str((poi.get("title") or {}).get("rendered") or "").split()))),
            ("lat", poi.get("latitude")), ("lng", poi.get("longitude")),
            ("google_place_id", poi.get("google_place_id") or ""),
            ("geography_class", klass), ("corridor_slug", slug), ("membership_reason", why),
        ]))
    blk["categories_seen"] = OrderedDict(cats.most_common())
    blk["disposition"] = ("ROSTER_ANSWERED_THIS_CLIENT" if blk["rows"] else
                          "ROSTER_ANSWERED_BUT_NO_LODGING_PARTNER_FOUND")
    return blk


def walk_bureau(bureau, stats, cap_override=None):
    bid, label, robots_url, method, entry_url, marker, cap = bureau
    if cap_override:
        cap = min(cap, cap_override)
    if method == "SIMPLEVIEW_API":
        return walk_simpleview(bureau, stats, cap)
    if method == "WP_REST_POI":
        return walk_wp_rest_poi(bureau, stats, cap)
    blk = OrderedDict([
        ("bureau_id", bid), ("label", label), ("cms", None), ("discovery_method", method), ("robots", None),
        ("entry", None), ("children_walked", []), ("listing_urls_published", 0), ("listing_pages_read", 0),
        ("request_cap", cap), ("requests_spent", 0), ("cap_reached", False),
        ("categories_seen", OrderedDict()), ("schema_types_seen", OrderedDict()),
        ("lodging_partners", 0), ("rows", []), ("disposition", None),
    ])
    rrow, rbody = fetch(robots_url, stats)
    rtext = rbody.decode("utf-8", "replace")
    blk["robots"] = OrderedDict([("document", rrow), ("body", rtext.strip()[:900])])
    blk["cms"] = ("CRAFT_CMS" if "cpresources" in rtext else
                  "WORDPRESS_YOAST" if "YOAST" in rtext.upper() else "UNKNOWN")
    erow, ebody = fetch(entry_url, stats, timeout=45)
    blk["entry"] = erow
    if cap == 0 and erow.get("status") == 200:
        blk["disposition"] = "ENTRY_ANSWERED_BUT_NOT_WALKED_BY_THIS_ORDER"
        return blk
    if erow.get("status") != 200:
        blk["disposition"] = "ENTRY_REFUSED_TO_THIS_CLIENT__STATUS_%s" % erow.get("status")
        return blk
    etext = ebody.decode("utf-8", "replace")
    listing_urls = []
    if method == "SITEMAP_WP_HOTELS":
        listing_urls = [u for u in _LOC.findall(etext) if marker in u
                        and u.rstrip("/").split("/")[-1] not in ("hotels", "where-to-stay")]
    elif method == "SITEMAP_WP_LISTING_NAMED":
        children = [c for c in _LOC.findall(etext) if re.search(r"(listing|partner)-sitemap", c)]
        published = []
        for child in children:
            crow, cbody = fetch(child, stats, timeout=45)
            urls = [u for u in _LOC.findall(cbody.decode("utf-8", "replace")) if marker in u]
            crow["listing_urls"] = len(urls)
            blk["children_walked"].append(crow)
            published.extend(urls)
        blk["listing_urls_in_sitemap"] = len(set(published))
        listing_urls = [u for u in published if _LODGING_SLUG.search(u.rstrip("/").split("/")[-1])]
        blk["preselected_by_lodging_slug"] = len(set(listing_urls))
    elif method == "SITEMAP_DIRECTORY_NAMED":
        # a Craft directory of EVERY kind of partner: only a listing whose own slug names lodging is fetched -- a
        # DISCOVERY preselection; each fetched page's own map window and category decide
        children = [c for c in _LOC.findall(etext)
                    if _CHILD_KEEP.search(c) and not _CHILD_SKIP.search(c)]
        published = []
        for child in children:
            crow, cbody = fetch(child, stats, timeout=45)
            urls = [u for u in _LOC.findall(cbody.decode("utf-8", "replace")) if marker in u]
            crow["listing_urls"] = len(urls)
            blk["children_walked"].append(crow)
            published.extend(urls)
        blk["listing_urls_in_sitemap"] = len(set(published))
        listing_urls = [u for u in published if _LODGING_SLUG.search(u.rstrip("/").split("/")[-1])]
        blk["preselected_by_lodging_slug"] = len(set(listing_urls))
    elif method == "SITEMAP_DIRECTORY":
        children = [c for c in _LOC.findall(etext)
                    if _CHILD_KEEP.search(c) and not _CHILD_SKIP.search(c)]
        for child in children:
            crow, cbody = fetch(child, stats, timeout=45)
            urls = [u for u in _LOC.findall(cbody.decode("utf-8", "replace")) if marker in u]
            crow["listing_urls"] = len(urls)
            blk["children_walked"].append(crow)
            listing_urls.extend(urls)
    else:
        host = re.match(r"(https?://[^/]+)", entry_url).group(1)
        listing_urls = [u for u in re.findall(r'href="(%s[^"#?]*)"' % re.escape(host), etext) if marker in u]
    listing_urls = sorted(set(u.rstrip() for u in listing_urls))
    blk["listing_urls_published"] = len(listing_urls)
    cats, stypes = Counter(), Counter()
    fetched = []
    for url in listing_urls:
        if blk["requests_spent"] >= cap:
            blk["cap_reached"] = True
            break
        prow, pbody = fetch(url, stats)
        blk["requests_spent"] += 1
        blk["listing_pages_read"] += 1
        fetched.append((url, prow, pbody))
    chrome_addr, chrome_hosts, chrome_tels = frozenset(), frozenset(), frozenset()
    if method in ("SITEMAP_WP_HOTELS", "SITEMAP_WP_LISTING_NAMED"):
        texts = [b.decode("utf-8", "replace") for _u, _r, b in fetched]
        chrome_addr, chrome_hosts = wp_chrome(texts)
        tel_count = Counter(t for x in texts for t in set(_TEL.findall(x)))
        chrome_tels = frozenset(t for t, n in tel_count.items() if n >= BOARD_MIN)
        blk["page_chrome_refused"] = OrderedDict([
            ("rule", "an address, outbound host or telephone printed on %d or more of this bureau's listing pages "
                     "is the bureau's own chrome and never a partner fact" % BOARD_MIN),
            ("addresses", sorted("%s %s" % k for k in chrome_addr)),
            ("hosts", sorted(chrome_hosts)),
            ("telephones", sorted(chrome_tels)),
        ])
    for url, prow, pbody in fetched:
        text = pbody.decode("utf-8", "replace")
        categories = sorted({c for c in (_CATEGORY.findall(text) or []) if c.strip()})
        schema_types = _schema_types(text)
        for c in categories:
            cats[c] += 1
        for t in schema_types:
            stypes[t] += 1
        # The bureau's category statement, in whichever vocabulary IT publishes. A bureau whose sitemap is a
        # HOTEL sitemap has made its category statement in the sitemap's own name.
        if method == "SITEMAP_WP_HOTELS":
            categories = ["Hotels (the bureau's own hotel-sitemap.xml)"]
            cats[categories[0]] += 1
        elif method == "SITEMAP_WP_LISTING_NAMED":
            # No category is published; the preselection is recorded AS the category statement it is -- a
            # slug, which the census treats as a lead and the property's own page decides.
            categories = ["Lodging (listing slug preselection -- not a bureau category)"]
            cats[categories[0]] += 1
        if not (_is_lodging(categories) or schema_types):
            continue
        premises = _parse_craft(text) or _parse_ldjson(text) or (_parse_wp_text(text, chrome_addr)
                                                                 if method in ("SITEMAP_WP_HOTELS",
                                                                               "SITEMAP_WP_LISTING_NAMED")
                                                                 else None)
        if premises is None:
            continue
        blk["lodging_partners"] += 1
        prow["sha256"] = persist(pbody)
        website = (_WEBSITE.findall(text) or _WEBSITE_ALT.findall(text) or [""])[0]
        if not website:
            website = (_wp_own_website(text, chrome_hosts)
                       if method in ("SITEMAP_WP_HOTELS", "SITEMAP_WP_LISTING_NAMED")
                       else _outbound_website(text, url))
        refused_link = ""
        if website and is_reseller_route(website):
            refused_link, website = website, ""
        # A tel: href is URL-ENCODED ("%20(760)%20722-1561"); decoded before it is stored, or the digits-only phone
        # key reads "20" + the number and binds nothing.
        tel = " ".join(urllib.parse.unquote(([t for t in _TEL.findall(text) if t not in chrome_tels]
                                             or [premises.get("phone") or ""])[0]).split())
        z = premises.get("postal_code") or ""
        klass, slug, why = GEO.classify_postal(z, premises.get("city") or "")
        blk["rows"].append(OrderedDict([
            ("lane", "DESTINATION_ROSTER"),
            ("bureau_id", bid),
            ("partner_id", (_PARTNER_ID.findall(text) or [""])[0]),
            ("name", premises["name"]),
            ("street", premises["street"]),
            ("city", premises["city"]),
            ("state", premises["state"]),
            ("postal_code", z),
            ("phone", tel),
            ("official_url", website),
            ("bureau_link_refused_as_a_route", refused_link),
            ("why_refused", ("the bureau published a RESELLER or booking-engine link rather than the partner's "
                             "own site; a place to buy a room is not a first-party route")
             if refused_link else ""),
            ("address_extras", premises.get("address_extras") or []),
            ("bureau_categories", categories),
            ("bureau_schema_types", schema_types),
            ("census_eligible_category", _census_eligible(categories) if categories
             else bool([t for t in schema_types if t.lower() not in ("vacationrental", "campground",
                                                                    "apartment")])),
            ("listing_url", url),
            ("listing_sha256", prow["sha256"]),
            ("geography_class", klass),
            ("corridor_slug", slug),
            ("membership_reason", why),
        ]))
    blk["categories_seen"] = OrderedDict(cats.most_common())
    blk["schema_types_seen"] = OrderedDict(stypes.most_common())
    blk["cap_reached"] = blk["cap_reached"] or (blk["listing_pages_read"] < len(listing_urls))
    blk["disposition"] = ("ROSTER_ANSWERED_THIS_CLIENT" if blk["rows"] else
                          "ROSTER_ANSWERED_BUT_NO_LODGING_PARTNER_FOUND")
    return blk


def reparse(report_path):
    """Re-derive every row from the documents this lane already persisted -- ZERO new requests.

    The bureau walk costs well over a thousand free requests. When the PARSER is corrected, re-walking the bureaus
    would buy nothing and would make the lane's output depend on when it ran. Every kept partner's document is
    already on disk under its own sha256, so the rows are rebuilt from those exact bytes.
    """
    doc = json.load(open(report_path, encoding="utf-8"))
    rebuilt, missing = 0, 0
    for blk in doc.get("bureaus", {}).values():
        rows = []
        chrome = frozenset()
        if blk.get("discovery_method") == "WP_REST_POI":
            # each row's own map card is persisted under its sha256: re-read those exact bytes; the REST pages
            # (persisted too) supply each POI's own REST title
            titles = {}
            for page in blk.get("children_walked", []):
                ppath = os.path.join(DOCS, "%s.bin" % page.get("sha256"))
                if page.get("sha256") and os.path.exists(ppath):
                    for poi in json.loads(open(ppath, "rb").read().decode("utf-8", "replace")) or []:
                        titles[str(poi.get("id"))] = _html.unescape(
                            " ".join(str((poi.get("title") or {}).get("rendered") or "").split()))
            for r in blk.get("rows", []):
                r["rest_title"] = titles.get(str(r.get("partner_id")), r.get("rest_title") or "")
                path = os.path.join(DOCS, "%s.bin" % r.get("listing_sha256"))
                if not r.get("listing_sha256") or not os.path.exists(path):
                    missing += 1
                    continue
                card = (json.loads(open(path, "rb").read().decode("utf-8", "replace")) or {}).get("data") or {}
                street, city, state, zipc, unparsed = _parse_tp_address(card.get("postAddress") or "")
                klass, slug, why = GEO.classify_postal(zipc, city)
                r.update(name=_tp_name(card, r.get("rest_title") or ""), street=street, city=city, state=state,
                         postal_code=zipc, address_extras=[unparsed] if unparsed else [],
                         geography_class=klass, corridor_slug=slug, membership_reason=why)
                rebuilt += 1
            continue
        if blk.get("discovery_method") in ("SIMPLEVIEW_API", "REFUSED_ENTRY"):
            continue  # rows come from the persisted API pages, not per-listing HTML documents
        if blk.get("discovery_method") in ("SITEMAP_WP_HOTELS", "SITEMAP_WP_LISTING_NAMED"):
            texts = [open(os.path.join(DOCS, "%s.bin" % r["listing_sha256"]), "rb").read().decode("utf-8", "replace")
                     for r in blk.get("rows", []) if r.get("listing_sha256")
                     and os.path.exists(os.path.join(DOCS, "%s.bin" % r["listing_sha256"]))]
            chrome = wp_chrome(texts)[0]
        for r in blk.get("rows", []):
            sha = r.get("listing_sha256")
            path = os.path.join(DOCS, "%s.bin" % sha) if sha else ""
            if not sha or not os.path.exists(path):
                missing += 1
                rows.append(r)
                continue
            text = open(path, "rb").read().decode("utf-8", "replace")
            premises = _parse_craft(text) or _parse_ldjson(text) or _parse_wp_text(text, chrome)
            if premises is None:
                rows.append(r)
                continue
            rebuilt += 1
            z = premises.get("postal_code") or ""
            klass, slug, why = GEO.classify_postal(z, premises.get("city") or "")
            new = OrderedDict(r)
            new["name"] = premises["name"]
            new["street"] = premises["street"]
            new["city"] = premises["city"]
            new["state"] = premises["state"]
            new["postal_code"] = z
            new["address_extras"] = premises.get("address_extras") or []
            # RECOMPUTED, NOT INHERITED. A re-parse must re-decide from the link the bureau published, or a
            # verdict from an earlier parse survives its own correction -- which is exactly what happened when
            # the first, substring-based reseller test refused forty brand-own routes.
            link = (new.get("official_url") or new.get("bureau_link_refused_as_a_route") or "")
            new["bureau_link_refused_as_a_route"] = ""
            new["why_refused"] = ""
            new["official_url"] = link
            if link and is_reseller_route(link):
                new["bureau_link_refused_as_a_route"] = link
                new["why_refused"] = ("the bureau published a RESELLER or booking-engine link rather than the "
                                      "partner's own site; a place to buy a room is not a first-party route")
                new["official_url"] = ""
            new["geography_class"] = klass
            new["corridor_slug"] = slug
            new["membership_reason"] = why
            rows.append(new)
        blk["rows"] = rows
    rows = [r for blk in doc.get("bureaus", {}).values() for r in blk["rows"]]
    admitted = [r for r in rows if r["corridor_slug"]]
    doc["rows"] = rows
    doc["row_count"] = len(rows)
    doc["rows_in_admitted_postal_codes"] = len(admitted)
    doc["rows_refused_by_postal_code"] = len(rows) - len(admitted)
    doc["rows_with_an_official_website"] = sum(1 for r in admitted if r["official_url"])
    doc["rows_with_a_phone"] = sum(1 for r in admitted if r["phone"])
    doc["rows_with_a_full_premises"] = sum(1 for r in admitted if r["street"] and r["postal_code"])
    doc["census_eligible_rows_in_admitted_codes"] = sum(1 for r in admitted
                                                        if r["census_eligible_category"])
    doc["by_corridor"] = OrderedDict(sorted(Counter(r["corridor_slug"] for r in admitted).items()))
    doc["by_bureau"] = OrderedDict(sorted(Counter(r["bureau_id"] for r in rows).items()))
    doc["rows_with_a_cross_street_or_landmark_separated_from_the_street"] = sum(
        1 for r in rows if r.get("address_extras"))
    doc["bureau_links_refused_as_a_route"] = [
        OrderedDict([("name", r.get("name")), ("bureau_id", r.get("bureau_id")),
                     ("link", r.get("bureau_link_refused_as_a_route"))])
        for r in rows if r.get("bureau_link_refused_as_a_route")]
    doc["bureau_links_refused_as_a_route_count"] = len(doc["bureau_links_refused_as_a_route"])
    doc["reparsed_from_persisted_documents"] = OrderedDict([
        ("what_it_is", "The bureau walk's free requests were NOT repeated. Every kept partner's document "
                       "is on disk under its own sha256, and the corrected address parser was re-run over "
                       "those exact bytes."),
        ("documents_reparsed", rebuilt),
        ("documents_missing", missing),
        ("new_http_requests", 0),
    ])
    return doc


def build(cap_override=None, only=None, keep=None):
    """``only`` re-walks the named bureaus; every other bureau's block is KEPT from ``keep`` (the report already
    on disk), so a corrected reader never re-walks a bureau it did not change."""
    stats = Stats()
    bureaus = OrderedDict()
    prior_requests = 0
    for bureau in BUREAUS:
        if only and bureau[0] not in only:
            if keep and bureau[0] in (keep.get("bureaus") or {}):
                bureaus[bureau[0]] = keep["bureaus"][bureau[0]]
            continue
        blk = walk_bureau(bureau, stats, cap_override)
        bureaus[bureau[0]] = blk
        print("  %-24s %-34s cms=%-16s method=%-17s published=%4d read=%4d lodging=%3d req=%4d" % (
            bureau[0], blk["disposition"], blk["cms"], blk["discovery_method"],
            blk["listing_urls_published"], blk["listing_pages_read"], blk["lodging_partners"],
            blk["requests_spent"]), flush=True)
    rows = [r for blk in bureaus.values() for r in blk["rows"]]
    admitted = [r for r in rows if r["corridor_slug"]]
    return OrderedDict([
        ("schema", "ptf-destination-roster/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("phase", "7 -- the official destination-marketing rosters, measured before being trusted"),
        ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", stats.requests),
        ("bytes_read", stats.bytes),
        ("the_bureau_was_measured",
         "Travel Portland is WordPress (no Simpleview token): its own public REST API lists every POI in its own "
         "'Lodging' category and each POI's own map card states its premises. Visit Vancouver USA is a Simpleview "
         "install read through its own public listings endpoint with an EMPTY filter, honouring its Crawl-delay of 2 "
         "seconds. Explore Washington County refused this client (403) and was not walked."),
        ("the_category_filter_is_read_not_trusted",
         "Simpleview partners are pulled UNFILTERED and each partner's OWN categories are read, because a "
         "directory's category filter may be INERT."),
        ("a_roster_row_is_not_a_policy",
         "Tier-3 IDENTITY and ROUTING evidence. The bureau's category PROPOSES that a partner is lodging; the "
         "property's own page decides what it is. No roster row carries a pet policy."),
        ("the_bureau_does_not_decide_membership",
         "Admission is the property's OWN postal code against the corridor registry and nothing else."),
        ("bureaus_measured_and_not_walked", OrderedDict([
            ("tualatinvalley.org (Explore Washington County)", "robots.txt and the home page answer 403 Forbidden to "
                                                               "this client -- not walked, not worked around"),
            ("mthoodterritory.com (Clackamas County)", "robots.txt disallows /partners/, where its listings live -- "
                                                       "honoured"),
            ("traveloregon.com", "statewide tourism; no answer inside 20 s -- not a lodging partner roster"),
            ("travelsalem.com / eugenecascadescoast.org / hoodriver.org / visittheoregoncoast.com / visitbend.com",
             "refused places' bureaus -- never walked"),
        ])),
        ("bureaus", bureaus),
        ("row_count", len(rows)),
        ("rows_in_admitted_postal_codes", len(admitted)),
        ("rows_refused_by_postal_code", len(rows) - len(admitted)),
        ("rows_with_an_official_website", sum(1 for r in admitted if r["official_url"])),
        ("rows_with_a_phone", sum(1 for r in admitted if r["phone"])),
        ("rows_with_a_full_premises", sum(1 for r in admitted if r["street"] and r["postal_code"])),
        ("census_eligible_rows_in_admitted_codes", sum(1 for r in admitted if r["census_eligible_category"])),
        ("by_corridor", OrderedDict(sorted(Counter(r["corridor_slug"] for r in admitted).items()))),
        ("by_bureau", OrderedDict(sorted(Counter(r["bureau_id"] for r in rows).items()))),
        ("rows", rows),
        ("documents_persisted_at", os.path.relpath(DOCS, _DASH).replace("\\", "/")),
    ])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--cap", type=int, default=None, help="probe cap per bureau")
    ap.add_argument("--only", default=None)
    ap.add_argument("--reparse", action="store_true",
                    help="re-derive every row from the persisted documents; no new requests")
    args = ap.parse_args(argv)
    keep = None
    if args.only and os.path.exists(args.out):
        keep = json.load(open(args.out, encoding="utf-8"))
    rep = reparse(args.out) if args.reparse else build(cap_override=args.cap,
                                                       only=args.only.split(",") if args.only else None, keep=keep)
    if keep:
        rep["free_http_requests"] += int(keep.get("free_http_requests") or 0)
        rep["bytes_read"] += int(keep.get("bytes_read") or 0)
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rep, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("rows:", rep["row_count"], "admitted:", rep["rows_in_admitted_postal_codes"],
          "refused:", rep["rows_refused_by_postal_code"])
    print("with website:", rep["rows_with_an_official_website"],
          "with phone:", rep["rows_with_a_phone"], "full premises:", rep["rows_with_a_full_premises"])
    print("free requests:", rep["free_http_requests"])
    print("by corridor:", dict(rep["by_corridor"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
