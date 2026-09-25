"""PTF-JACKSONVILLE-FL-HARDENED-SOURCE-READY-001 -- Phase 9C: the official destination-marketing rosters.

THE BUREAU WAS MEASURED, NOT ASSUMED, AND THIS ONE IS THE BEST THE FACTORY HAS SEEN
----------------------------------------------------------------------------------
The standing rule from PTF-COLUMBIA-SC and PTF-WEST-PALM-BEACH is to MEASURE a convention and visitors bureau
before spending anything on it: Columbia's was a Simpleview CMS with a public listings service, Visit
Lauderdale's was the same and handed that market 376 listings with 360 websites, and Discover The Palm Beaches
was a WordPress install with its REST API disabled that answered 403 to every plain request and whose listing
pages carried NO street, NO postal code, NO telephone and NO outbound website -- 624 credits for nothing.

VISIT JACKSONVILLE IS NONE OF THOSE. It is a **Craft CMS** install (its own robots.txt gives it away:
`Disallow: /cpresources/`), it answers **HTTP 200 to a plain client on every path**, its robots.txt disallows
only `/cpresources/`, `/vendor/` and `/.env`, and its sitemap index publishes the ENTIRE partner directory --
2,156 listing pages across seven paginated sitemaps. Every listing page carries, in its own markup:

  * the partner's name                              (`map-infowindow__title`)
  * the FULL street address, city, state and ZIP    (`map-infowindow__summary`)
  * the telephone                                   (`href="tel:..."`)
  * the partner's OWN OUTBOUND WEBSITE              (`data-dms-partner-detail-website-click`)
  * the bureau's own CATEGORY for the partner       (`data-dms-category-name`)
  * a stable partner id                             (`data-dms-partner-id`)

That is premises-grade identity plus a first-party route, for free, with no provider and no credit.

WHY THIS LANE WALKS ALL 2,156 LISTINGS INSTEAD OF FILTERING BY SLUG
------------------------------------------------------------------
A slug filter would be cheaper and WRONG. "Omni Jacksonville Hotel", "Stay Sojo", "Margaritaville Beach Hotel"
and "The Bearded Pig" cannot be separated by the words in a URL, and the standing rule from
PTF-COMPETITOR-CENSUS is that a directory's CATEGORY FILTER MAY BE INERT -- so the category has to be read off
each page rather than trusted from a query string. Every listing is therefore fetched once, its own category is
read, and only lodging-category partners are kept. The walk is free (plain HTTPS GET, no provider), bounded by
an explicit cap, and it persists a document only for the partners it keeps, so it does not leave a gigabyte of
restaurant pages on disk.

A ROSTER ROW IS NOT A POLICY, AND NOT AN ADMISSION
--------------------------------------------------
Everything here is IDENTITY and ROUTING evidence (tier 3). The bureau's category proposes that a partner is
lodging; the DBPR licence and the property's own page decide what it is. The bureau's own city label decides
NOTHING: admission is the property's own postal code against the corridor registry, and Visit Jacksonville
markets Duval County including the beaches, which is NOT this market's boundary -- Amelia Island, Ponte Vedra
Beach and Orange Park have their own bureaus and are admitted here on their own postal codes.

THE SECOND AND THIRD BUREAUS
----------------------------
  * AMELIA ISLAND CVB (ameliaisland.com) -- a WordPress + Yoast install whose robots.txt allows everything.
    Nassau County is not Visit Jacksonville territory, so without this bureau the Amelia Island corridor would
    have no bureau lane at all.
  * FLORIDA'S HISTORIC COAST (floridashistoriccoast.com) -- the St. Johns County bureau, another Craft install.
    It is probed and its lodging partners are read ONLY so the Ponte Vedra Beach corridor has a bureau source
    and so the St. Augustine refusal can be COUNTED rather than assumed. Every St. Augustine partner it returns
    is refused by its own postal code, which is exactly the point.

Outputs:
  launch_packages/pettripfinder/markets/reports/jacksonville_fl_destination_roster_001.json
  data/acquisition/jacksonville_fl_roster_001/<sha256>.bin   (kept partners' documents as returned)
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
import urllib.request
import zlib
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import jacksonville_fl_geography_001 as GEO  # noqa: E402

WORK_ORDER = "PTF-JACKSONVILLE-FL-HARDENED-SOURCE-READY-001"
MARKET_ID = "jacksonville-fl"
REPORTS = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports")
DOCS = os.path.join(_DASH, "data", "acquisition", "jacksonville_fl_roster_001")
OUT = os.path.join(REPORTS, "jacksonville_fl_destination_roster_001.json")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")

#: Each bureau publishes its partners differently, so each one carries its OWN discovery method, measured:
#:   SITEMAP_DIRECTORY  the sitemap index publishes every listing page (both Craft installs do)
#:   SEED_PAGE          the sitemap publishes only editorial pages, and one lodging page links every partner
#: (bureau id, label, robots url, method, entry url, listing-path marker, cap)
BUREAUS = [
    ("visit-jacksonville", "Visit Jacksonville & the Beaches (Duval County)",
     "https://www.visitjacksonville.com/robots.txt", "SITEMAP_DIRECTORY",
     "https://www.visitjacksonville.com/sitemap.xml", "/directory/", 2600),
    ("amelia-island-cvb", "Amelia Island Convention & Visitors Bureau (Nassau County)",
     "https://www.ameliaisland.com/robots.txt", "SEED_PAGE",
     "https://www.ameliaisland.com/places-to-stay/", "/partners/", 400),
    ("floridas-historic-coast", "Florida's Historic Coast (St. Johns County -- Ponte Vedra AND the refused "
                                "St. Augustine codes)",
     "https://www.floridashistoriccoast.com/robots.txt", "SITEMAP_DIRECTORY",
     "https://www.floridashistoriccoast.com/sitemap.xml", "/directory/", 1600),
]

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

_STATE_CODE = {"florida": "FL", "georgia": "GA", "fl": "FL", "ga": "GA"}


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
    r"(ameliaisland|visitjacksonville|floridashistoriccoast|ameliaislandtdc|nassauflorida|islandchamber|"
    r"google|gstatic|gmpg\.org|schema\.org|w3\.org|facebook|instagram|twitter|x\.com|youtube|pinterest|"
    r"tiktok|linkedin|ajax\.googleapis|fonts\.|cloudflare|cloudfront|wp\.com|gravatar|api\.w\.org|"
    r"simpleviewinc|tripadvisor|yelp|expedia|booking\.com|hotels\.com|opentable|eventbrite|"
    r"visitflorida|floridasfirstcoast)", re.I)


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


def walk_bureau(bureau, stats, cap_override=None):
    bid, label, robots_url, method, entry_url, marker, cap = bureau
    if cap_override:
        cap = min(cap, cap_override)
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
    if erow.get("status") != 200:
        blk["disposition"] = "ENTRY_REFUSED_TO_THIS_CLIENT__STATUS_%s" % erow.get("status")
        return blk
    etext = ebody.decode("utf-8", "replace")
    listing_urls = []
    if method == "SITEMAP_DIRECTORY":
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
    for url in listing_urls:
        if blk["requests_spent"] >= cap:
            blk["cap_reached"] = True
            break
        prow, pbody = fetch(url, stats)
        blk["requests_spent"] += 1
        blk["listing_pages_read"] += 1
        text = pbody.decode("utf-8", "replace")
        categories = sorted({c for c in (_CATEGORY.findall(text) or []) if c.strip()})
        schema_types = _schema_types(text)
        for c in categories:
            cats[c] += 1
        for t in schema_types:
            stypes[t] += 1
        # The bureau's category statement, in whichever vocabulary IT publishes.
        if not (_is_lodging(categories) or schema_types):
            continue
        premises = _parse_craft(text) or _parse_ldjson(text)
        if premises is None:
            continue
        blk["lodging_partners"] += 1
        prow["sha256"] = persist(pbody)
        website = (_WEBSITE.findall(text) or _WEBSITE_ALT.findall(text) or [""])[0]
        if not website:
            website = _outbound_website(text, url)
        refused_link = ""
        if website and is_reseller_route(website):
            refused_link, website = website, ""
        tel = (_TEL.findall(text) or [premises.get("phone") or ""])[0]
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

    The bureau walk costs 2,788 free requests and 1.1 GB. When the PARSER is corrected, re-walking the bureaus
    would buy nothing and would make the lane's output depend on when it ran. Every kept partner's document is
    already on disk under its own sha256, so the rows are rebuilt from those exact bytes.
    """
    doc = json.load(open(report_path, encoding="utf-8"))
    rebuilt, missing = 0, 0
    for blk in doc.get("bureaus", {}).values():
        rows = []
        for r in blk.get("rows", []):
            sha = r.get("listing_sha256")
            path = os.path.join(DOCS, "%s.bin" % sha) if sha else ""
            if not sha or not os.path.exists(path):
                missing += 1
                rows.append(r)
                continue
            text = open(path, "rb").read().decode("utf-8", "replace")
            premises = _parse_craft(text) or _parse_ldjson(text)
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
        ("what_it_is", "The bureau walk's 2,788 free requests were NOT repeated. Every kept partner's document "
                       "is on disk under its own sha256, and the corrected address parser was re-run over "
                       "those exact bytes."),
        ("documents_reparsed", rebuilt),
        ("documents_missing", missing),
        ("new_http_requests", 0),
    ])
    return doc


def build(cap_override=None, only=None):
    stats = Stats()
    bureaus = OrderedDict()
    for bureau in BUREAUS:
        if only and bureau[0] != only:
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
        ("phase", "9C -- the official destination-marketing rosters, measured before being trusted"),
        ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", stats.requests),
        ("bytes_read", stats.bytes),
        ("the_bureau_was_measured",
         "Visit Jacksonville is a Craft CMS install that answers HTTP 200 to a plain client on every path and "
         "publishes its whole partner directory in its sitemap index. Its listing pages carry the full street, "
         "city, state, ZIP, telephone, the partner's OWN outbound website and the bureau's own category. That is "
         "premises-grade identity plus a first-party route, for free. Discover The Palm Beaches, measured the "
         "same way one market earlier, answered 403 on every path and carried none of those four fields."),
        ("the_category_filter_is_read_not_trusted",
         "Every listing page is fetched and its OWN data-dms-category-name is read, because the standing rule is "
         "that a directory's category filter may be INERT. A slug filter would have missed 'Omni Jacksonville "
         "Hotel' and 'Stay Sojo' and admitted 'Jax Yacht Charter'."),
        ("a_roster_row_is_not_a_policy",
         "Tier-3 IDENTITY and ROUTING evidence. The bureau's category PROPOSES that a partner is lodging; the "
         "DBPR licence and the property's own page decide what it is. No roster row carries a pet policy."),
        ("the_bureau_does_not_decide_membership",
         "Visit Jacksonville markets Duval County including the beaches, which is not this market's boundary; "
         "Amelia Island, Ponte Vedra Beach and Orange Park have their own bureaus. Admission is the property's "
         "OWN postal code against the corridor registry and nothing else -- which is why every St. Augustine "
         "partner Florida's Historic Coast returns is counted here and refused there."),
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
    rep = reparse(args.out) if args.reparse else build(cap_override=args.cap, only=args.only)
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
