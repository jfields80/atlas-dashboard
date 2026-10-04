"""PTF-PORTLAND-OR-HARDENED-SOURCE-READY-001 -- Phases 9 + 10: owned national inventory, then the brands' own
inventories (cloned in shape from the Seattle / San Antonio helper; Portland / Greater Portland localities, Oregon and
Vancouver-Washington surfaces).

WHAT THIS IS
------------
Rung 0 and rung 2 of the acquisition ladder, run together because they answer the same question -- WHICH
PROPERTIES EXIST, and at WHAT OFFICIAL ROUTE -- and because rung 0 must be exhausted before a new request.

  rung 0  OWNED.  The committed national brand directory harvest (``dayton_oh_brand_directory_harvest_001.json``)
          is a SHARED national inventory. Every Portland-metro Marriott route in it (PDX** codes) is already
          durable at zero requests.
  rung 2  THE BRAND'S OWN INVENTORY PAGE, then its own sitemap. One plain HTTPS GET each, bounded per family:
            MARRIOTT  the brand's own Oregon AND Washington hotel sitemap pages (MARSHA code, title, route)
            HILTON    the brand's own Oregon city pages (and Vancouver, WA) and every in-market interlink they publish
            WYNDHAM / ESA / SONESTA / WOODSPRING / ...  the brand's own sitemap
            CHOICE / IHG / BEST WESTERN / RED ROOF / MOTEL 6 / HYATT / OMNI / FOUR SEASONS / RADISSON
                      re-probed at their sitemap; what THIS client saw is recorded

A ROSTER ROW IS NOT A POLICY, AND NOT AN ADMISSION
--------------------------------------------------
Everything here is ROUTING and IDENTITY evidence. No route carries or implies a pet policy, and no route admits a
property: the postal code the property's OWN page states does that.

THE PORTLAND LEAD FILTER, AND WHY A CODE PREFIX IS NOT A PLACE
-------------------------------------------------------------
1. MARRIOTT'S MARSHA PREFIX PDX IS NOT THIS MARKET. It also codes Salem and Newberg hotels, which this market
   refuses, and Vancouver, Washington hotels, which it admits with their Washington identity. The code is a LEAD, a
   title's own place word is a LEAD, and a refused place token OUTRANKS both. The code never places a property; its
   own postal code does.
2. "PORTLAND" AND "VANCOUVER" ARE THE NAME TRAP AT ITS SHARPEST. Portland, MAINE (Marriott PWM**) carries hotels with
   the very same names ("Courtyard Portland Downtown Waterfront", "Residence Inn Portland Downtown Waterfront",
   "Courtyard Portland Airport"); Vancouver, BRITISH COLUMBIA carries the Sheraton Vancouver Wall Centre and dozens
   more. Neither word is a lead on its own: it needs an Oregon / Washington marker, a PDX code or a brand card stating
   its own Oregon or Washington-986 address. Hillsboro (Texas, Ohio), Gresham (Wisconsin), Sherwood (Arkansas),
   Fairview, Cornelius (North Carolina), Gladstone (Missouri, Michigan) and Happy Valley (Arizona) are generic too.
3. THE CHAINS PUT "PORTLAND" ON HOTELS FROM HOOD RIVER TO NEWBERG AND SALEM. "Fairfield Inn & Suites Portland
   Newberg" stands in Newberg; "Best Western Plus Hood River Inn" in Hood River. A refused place word refuses the URL
   unless an admitted city other than Portland is named beside it -- and every lead is placed afterwards by its own
   postal code anyway.

Outputs:
  launch_packages/pettripfinder/markets/reports/portland_or_brand_inventory_001.json
  data/acquisition/portland_or_brand_001/<sha256>.bin   (documents as returned)
"""
from __future__ import annotations

import argparse
import gzip
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

WORK_ORDER = "PTF-PORTLAND-OR-HARDENED-SOURCE-READY-001"
MARKET_ID = "portland-or"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
DOCS = os.path.join(_DASH, "data", "acquisition", "portland_or_brand_001")
OWNED = os.path.join(REPORTS, "dayton_oh_brand_directory_harvest_001.json")
OUT = os.path.join(REPORTS, "portland_or_brand_inventory_001.json")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")

#: Portland / Greater Portland places, as a brand spells them in a URL. A brand's marketing name never admits a
#: property -- these are LEAD filters only, and every lead is placed afterwards by its own postal code.
LOCALITIES = (
    "portland", "beaverton", "hillsboro", "tigard", "lake-oswego", "gresham", "tualatin", "wilsonville", "clackamas",
    "happy-valley", "troutdale", "fairview", "wood-village", "milwaukie", "oregon-city", "west-linn", "gladstone",
    "sherwood", "forest-grove", "cornelius", "vancouver", "jantzen-beach", "hayden-island", "cascade-station",
    "lloyd", "pearl-district", "riverplace", "tanasbourne", "king-city",
)
#: Tokens that need no state marker because no other place in the chains' inventories spells them this way.
UNIQUE_TOKENS = ("tigard", "lake-oswego", "tualatin", "wilsonville", "troutdale", "milwaukie", "clackamas",
                 "west-linn", "oregon-city", "beaverton", "jantzen-beach", "hayden-island", "tanasbourne")
#: A state marker: Oregon, or Washington ONLY beside Vancouver (every other Washington place is refused).
AZ_MARKERS = ("oregon", "-or-", "-or/", "_or", "-or.", "/or/", "-or_", "/oregon/", "/us/or/",
              "vancouver-wa", "vancouver-washington", "/wa/vancouver", "washington/vancouver", "vancouver/wa")
#: Look-alikes that carry a Portland-area word but are somewhere else entirely, and the refused neighbours. The
#: refused neighbours come FIRST: the chains put "Portland" on hotels well outside the metro's codes.
NEGATIVE = (
    # --- refused Oregon / south-west Washington neighbours (FUTURE_STANDALONE or refused by name) ---
    "salem", "keizer", "woodburn", "eugene", "springfield-or", "hood-river", "cascade-locks", "the-dalles",
    "stevenson", "white-salmon", "government-camp", "welches", "timberline", "mt-hood", "mount-hood", "seaside",
    "cannon-beach", "astoria", "warrenton", "tillamook", "lincoln-city", "newport", "depoe-bay", "bend", "sunriver",
    "redmond", "mcminnville", "dundee", "canby", "st-helens", "scappoose", "longview", "kelso", "kalama",
    "battle-ground", "ridgefield", "la-center", "albany", "corvallis", "medford", "ashland", "grants-pass",
    "roseburg", "klamath", "pendleton", "hermiston", "the-dalles", "tacoma", "olympia", "seattle", "chehalis",
    "centralia", "spokane", "yakima", "kennewick", "richland", "pasco",
    # --- look-alikes of Portland-area place words elsewhere ---
    "maine", "portland-me", "south-portland", "scarborough", "british-columbia", "vancouver-bc", "canada",
    "whistler", "richmond-bc", "burnaby", "surrey", "hillsboro-tx", "hillsboro-oh", "texas", "ohio", "arizona",
    "tennessee", "california", "florida", "colorado", "georgia", "carolina", "virginia",
    "pennsylvania", "new-york", "michigan", "minnesota", "missouri", "indiana", "wisconsin", "idaho", "montana",
    "alaska", "hawaii", "new-jersey", "maryland", "massachusetts", "kentucky", "illinois", "iowa", "nebraska",
    "connecticut", "new-hampshire", "vermont", "utah", "nevada", "new-mexico", "kansas", "oklahoma", "arkansas",
    "louisiana", "alabama", "mississippi",
)

#: AMBIGUOUS refusal tokens: refused ONLY when the URL / title names no admitted city beside them ("portland" does
#: not count) -- a Vancouver hotel slug that also names Camas is decided by its own page.
_ADMITTED_CITY_TOKEN = re.compile(r"(beaverton|hillsboro|tigard|lake-oswego|gresham|tualatin|wilsonville|clackamas|"
                                  r"happy-valley|troutdale|fairview|milwaukie|oregon-city|west-linn|sherwood|"
                                  r"forest-grove|cornelius|vancouver|jantzen|airport)", re.I)
_AMBIGUOUS_NEGATIVE = re.compile(r"(?<![a-z])(camas|washougal|newberg|sandy|woodland)(?![a-z])", re.I)

#: Negatives that need a WORD BOUNDARY, not a substring.
NEGATIVE_PATTERNS = (
    # look-alike place + state slugs (never Oregon; Washington only for Vancouver, handled by AZ_MARKERS)
    re.compile(r"(?:portland|vancouver|hillsboro|gresham|sherwood|fairview|cornelius|gladstone|happy-valley|"
               r"forest-grove|beaverton|milwaukie)-"
               r"(?:mn|in|nv|pa|ky|sc|de|dc|ma|oh|az|va|tx|il|mi|fl|ca|nm|al|ga|nc|ne|me|ia|tn|ny|nj|ok|co|bc|ar|"
               r"wi|ct|nh)(?![a-z])", re.I),
    re.compile(r"-(?:il|oh|ky|la|in|ca|nj|tx|md|ma|nh|wi|mi|pa|ne|mo|wy|ut|nm|ks|co|az|fl|nc|ga|nv|ok|ar|mn|sc|de|va|dc|al|ia|tn|ny|id|mt|ak|hi|me|bc)(?![a-z])/", re.I),
    re.compile(r"/(?:il|oh|ky|la|in|ca|nj|tx|md|ma|nh|wi|mi|pa|ne|mo|wy|ut|nm|ks|co|az|fl|nv|ok|ar|mn|sc|de|va|dc|al|ia|tn|ny|id|mt|ak|hi|me|bc)/", re.I),
)


def negative_hit(url):
    """The refusal token a URL carries, or ""."""
    u = (url or "").lower()
    for n in NEGATIVE:
        if n in u:
            return n
    for rx in NEGATIVE_PATTERNS:
        m = rx.search(u)
        if m:
            return m.group(0)
    m = _AMBIGUOUS_NEGATIVE.search(u)
    if m and not _ADMITTED_CITY_TOKEN.search(u):
        return m.group(0)
    return ""


CAP_PER_FAMILY = 200

#: A BRAND CARD IS DECIDED BY ITS OWN ADDRESS, NOT BY ITS URL. Hilton's city pages publish "the twenty nearest
#: properties" with each one's own structured address card, so a Portland seed page reaches Salem, Hood River and
#: Longview. Every card is kept or refused on its OWN street, city, state and postal code: Oregon 970-974 and 977 (the
#: metro and its refused ring -- Salem, Eugene, the coast, the Gorge, Mount Hood, Bend -- kept only so the boundary
#: audit SEES them and refuses them by postal code) and Washington 986 (Vancouver and Clark / Cowlitz / Skamania).
#: A card from any other state, or any other Washington prefix, cannot pass.
CARD_POSTAL_PREFIXES = {"OR": ("970", "971", "972", "973", "974", "977"), "WA": ("986",)}
CARD_STATES = {"OR": "OR", "OREGON": "OR", "WA": "WA", "WASHINGTON": "WA"}


def card_in_observation_box(card):
    """(kept, why) for a brand card, decided by the card's OWN address."""
    state = " ".join(str(card.get("state") or "").split()).upper()
    postal = "".join(ch for ch in str(card.get("postal_code") or "") if ch.isdigit())[:5]
    if not state or state not in CARD_STATES:
        return False, "the card's OWN state is %r; every corridor of this market is in Oregon or Washington" % state
    if not postal:
        return False, "the card states no postal code of its own, so nothing places it"
    if postal[:3] not in CARD_POSTAL_PREFIXES[CARD_STATES[state]]:
        return False, ("the card's OWN postal code %s is outside this market's observation box (north-west Oregon / "
                       "south-west Washington prefixes)" % postal)
    return True, "the card's OWN postal code %s is inside the observation box" % postal


HILTON_SEEDS = [
    "oregon/portland", "oregon/beaverton", "oregon/hillsboro", "oregon/tigard", "oregon/lake-oswego",
    "oregon/gresham", "oregon/tualatin", "oregon/wilsonville", "oregon/clackamas", "oregon/happy-valley",
    "oregon/troutdale", "oregon/fairview", "oregon/milwaukie", "oregon/oregon-city", "oregon/sherwood",
    "oregon/forest-grove", "oregon/west-linn", "washington/vancouver",
]


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


def fetch(url, stats, timeout=30):
    row = OrderedDict([("url", url), ("status", None), ("final_url", None), ("bytes", 0), ("sha256", None),
                       ("error", None), ("fetched_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))])
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9", "Accept-Encoding": "gzip, deflate"})
    stats.requests += 1
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = _decode(resp, resp.read())
            if body[:2] == b"\x1f\x8b":
                try:
                    body = gzip.GzipFile(fileobj=io.BytesIO(body)).read()
                except Exception:
                    pass
            row.update(status=resp.getcode(), final_url=resp.geturl(), bytes=len(body), sha256=persist(body))
            stats.bytes += len(body)
            return row, body
    except urllib.error.HTTPError as exc:
        row["status"], row["final_url"] = exc.code, url
        return row, b""
    except Exception as exc:
        row["error"] = "%s: %s" % (type(exc).__name__, str(exc)[:160])
        return row, b""


#: Marriott codes the Portland metro PDX** -- and PDX also codes Salem and Newberg hotels, so the code is a LEAD
#: filter only, deliberately weaker than a negative token, and never places a property. Hilton's ctyhocn for this
#: region is PDX + letters; IHG's is PDX + two.
_SAN_CODE = re.compile(r"/hotels/pdx[a-z0-9]{2}-", re.I)
_SAN_CTYHOCN = re.compile(r"/hotels/pdx[a-z]{4}\b", re.I)
_SAN_IHG = re.compile(r"/hotels/us/en/[a-z0-9-]+/pdx[a-z]{2}/", re.I)


def is_lead(url):
    u = url.lower()
    # A negative token wins over EVERYTHING, including a brand property code.
    if negative_hit(u):
        return False
    if _SAN_CODE.search(u) or _SAN_CTYHOCN.search(u) or _SAN_IHG.search(u):
        return True
    if any(t in u for t in UNIQUE_TOKENS):
        return True
    return any(t in u for t in LOCALITIES) and any(m in u for m in AZ_MARKERS)


# --------------------------------------------------------------------------- rung 0
def owned_leads():
    if not os.path.exists(OWNED):
        return [], {"present": False}
    doc = json.load(open(OWNED, encoding="utf-8"))
    out, seen = [], set()
    for cand in doc.get("candidates", []):
        url = cand.get("url") or ""
        if not is_lead(url):
            continue
        key = url.lower()
        m = re.search(r"/hotels/([a-z0-9]{5})-", key)
        code = (m.group(1) if m else (cand.get("property_code") or "")).lower()
        canon = re.sub(r"^https?://[^/]+/[a-z-]{2,5}/hotels/", "", key).split("/overview")[0]
        ident = (cand.get("family"), code or canon)
        if ident in seen:
            continue
        seen.add(ident)
        route = url
        if "/en-us/" not in route and "/hotels/" in route:
            route = re.sub(r"/[a-z]{2}(-[a-z]{2})?/hotels/", "/en-us/hotels/", route, count=1)
        route = re.sub(r"(/overview/?).*$", "/overview/", route)
        out.append(OrderedDict([("family", cand.get("family")), ("route", route), ("property_code", code),
                                ("lane", "BRAND_INVENTORY_OWNED"),
                                ("owned_source", "dayton_oh_brand_directory_harvest_001.json"),
                                ("owned_as_of", doc.get("as_of"))]))
    return out, {"present": True, "as_of": doc.get("as_of"), "total_routes_in_corpus": len(doc.get("candidates", []))}


# --------------------------------------------------------------------------- MARRIOTT state sitemap
MARRIOTT_STATE_SITEMAPS = ("https://www.marriott.com/en-us/hotel-sitemap/usa-oregon-hotel-sitemap",
                           "https://www.marriott.com/en-us/hotel-sitemap/usa-washington-hotel-sitemap")
MARRIOTT_STATE_SITEMAP = MARRIOTT_STATE_SITEMAPS[0]
_MARSHA = re.compile(r'\{"marsha":"([a-z0-9]{5})","title":"((?:[^"\\]|\\.)*)","url":"([^"]+)"\}', re.I)
#: Titles that name a place THIS market admits.
_TITLE_PLACES = re.compile(r"\b(portland|beaverton|hillsboro|tigard|lake oswego|gresham|tualatin|wilsonville|"
                           r"clackamas|happy valley|troutdale|fairview|wood village|milwaukie|oregon city|west linn|"
                           r"gladstone|sherwood|forest grove|cornelius|vancouver|jantzen beach|hayden island|"
                           r"lloyd|pearl district|riverplace)\b", re.I)
#: An admitted CITY in a title (not "Portland", which the chains put on everything).
_TITLE_ADMITTED_CITY = re.compile(r"\b(beaverton|hillsboro|tigard|lake oswego|gresham|tualatin|wilsonville|"
                                  r"clackamas|happy valley|troutdale|fairview|milwaukie|oregon city|west linn|"
                                  r"sherwood|forest grove|cornelius|vancouver|airport)\b", re.I)
#: Titles that name a place THIS market refuses. Checked FIRST -- unless the title also names an admitted city.
_TITLE_REFUSED = re.compile(r"\b(salem|keizer|woodburn|eugene|springfield|hood river|cascade locks|the dalles|"
                            r"stevenson|white salmon|government camp|welches|timberline|mt\.? hood|mount hood|"
                            r"seaside|cannon beach|astoria|warrenton|tillamook|lincoln city|newport|depoe bay|bend|"
                            r"sunriver|redmond|newberg|mcminnville|dundee|canby|st\.? helens|scappoose|longview|"
                            r"kelso|kalama|battle ground|ridgefield|camas|washougal|albany|corvallis|medford|"
                            r"ashland|grants pass|roseburg|klamath|pendleton|hermiston|tacoma|olympia|seattle|"
                            r"bellevue|everett|lynnwood|bothell|kirkland|renton|tukwila|seatac|spokane|yakima|"
                            r"kennewick|richland|pasco|centralia|chehalis|bellingham|bremerton|wenatchee)\b", re.I)


def marriott_state_sitemap(stats):
    fam = OrderedDict([("lane", "BRAND_STATE_SITEMAP_PAGE"), ("url", MARRIOTT_STATE_SITEMAP),
                       ("urls", list(MARRIOTT_STATE_SITEMAPS)), ("document", None), ("documents", []),
                       ("properties_listed", 0), ("routes", [])])
    seen = set()
    for sitemap in MARRIOTT_STATE_SITEMAPS:
        row, body = fetch(sitemap, stats, timeout=60)
        fam["documents"].append(row)
        if fam["document"] is None:
            fam["document"] = row
        washington = "washington" in sitemap
        text = body.decode("utf-8", "replace")
        for code, title, url in _MARSHA.findall(text):
            code = code.lower()
            if code in seen:
                continue
            seen.add(code)
            fam["properties_listed"] += 1
            title = json.loads('"%s"' % title)
            if _TITLE_REFUSED.search(title) and not _TITLE_ADMITTED_CITY.search(title):
                fam.setdefault("refused_by_title", []).append(
                    OrderedDict([("property_code", code), ("brand_title", title),
                                 ("why", "the brand's own title names a place this market refuses")]))
                continue
            # The Washington sitemap is read ONLY for Vancouver: every other Washington place is refused.
            if washington and not (re.search(r"\bvancouver\b", title, re.I) or code.startswith("pdx")):
                continue
            if not (code.startswith("pdx") or _TITLE_PLACES.search(title)):
                continue
            fam["routes"].append(OrderedDict([("family", "MARRIOTT"), ("route", url), ("property_code", code),
                                              ("brand_title", title), ("lane", "BRAND_STATE_SITEMAP_PAGE"),
                                              ("found_in", sitemap), ("found_in_sha256", row["sha256"])]))
    fam["disposition"] = ("STATE_SITEMAP_ANSWERED_THIS_CLIENT" if fam["routes"] else
                          "STATE_SITEMAP_STATUS_%s" % (fam["document"] or {}).get("status"))
    return fam


# --------------------------------------------------------------------------- HILTON city pages + interlinks
def hilton_page_hotels(text):
    """(hotels, interlinks) from a Hilton locations page's own __NEXT_DATA__."""
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', text, re.S)
    if not m:
        return [], []
    try:
        data = json.loads(m.group(1))
    except ValueError:
        return [], []
    hotels, links = [], []
    for q in (data.get("props", {}).get("pageProps", {}).get("dehydratedState", {}).get("queries") or []):
        gp = ((q.get("state") or {}).get("data") or {}).get("geocodePage") or {}
        for block in ((gp.get("location") or {}).get("pageInterlinks") or []):
            for link in block.get("links") or []:
                if link.get("uri"):
                    links.append(link["uri"])
        for h in ((gp.get("hotelSummaryOptions") or {}).get("hotels") or []):
            addr = h.get("address") or {}
            coord = ((h.get("localization") or {}).get("coordinate") or {})
            hotels.append(OrderedDict([
                ("ctyhocn", (h.get("ctyhocn") or "").lower()), ("name", h.get("name")),
                ("route", ((h.get("facilityOverview") or {}).get("homeUrlTemplate") or "")),
                ("brand_code", h.get("brandCode")), ("street", addr.get("addressLine1")), ("city", addr.get("city")),
                ("state", addr.get("state")), ("postal_code", addr.get("postalCode")),
                ("phone", (h.get("contactInfo") or {}).get("phoneNumber")),
                ("lat", coord.get("latitude")), ("lng", coord.get("longitude")),
                ("open", (h.get("display") or {}).get("open")),
                ("open_date", (h.get("display") or {}).get("openDate")),
            ]))
    return hotels, links


_HILTON_IN_MARKET_LINK = re.compile(r"^locations/usa/(%s)(/[a-z0-9-]+)?/?$" % "|".join(
    re.escape(s) for s in HILTON_SEEDS))


def hilton_city_pages(stats):
    fam = OrderedDict([("lane", "BRAND_CITY_PAGE"), ("request_cap", CAP_PER_FAMILY), ("pages", OrderedDict()),
                       ("routes", []), ("cards_refused_by_their_own_address", [])])
    queue = ["locations/usa/%s/" % s for s in HILTON_SEEDS]
    walked, seen = set(), set()
    spent = 0
    while queue and spent < CAP_PER_FAMILY:
        uri = queue.pop(0).strip("/") + "/"
        if uri in walked:
            continue
        walked.add(uri)
        url = "https://www.hilton.com/en/%s" % uri
        row, body = fetch(url, stats)
        spent += 1
        hotels, links = hilton_page_hotels(body.decode("utf-8", "replace"))
        row["hotels_on_page"] = len(hotels)
        new = 0
        for h in hotels:
            if not h["ctyhocn"] or h["ctyhocn"] in seen:
                continue
            seen.add(h["ctyhocn"])
            kept, why = card_in_observation_box(h)
            if not kept:
                fam["cards_refused_by_their_own_address"].append(OrderedDict([
                    ("property_code", h["ctyhocn"]), ("name", h.get("name")),
                    ("street", h.get("street")), ("city", h.get("city")), ("state", h.get("state")),
                    ("postal_code", h.get("postal_code")), ("found_in", url), ("why", why)]))
                continue
            new += 1
            fam["routes"].append(OrderedDict([
                ("family", "HILTON"), ("route", h["route"] or "https://www.hilton.com/en/hotels/%s/" % h["ctyhocn"]),
                ("property_code", h["ctyhocn"]), ("lane", "BRAND_CITY_PAGE"), ("found_in", url),
                ("found_in_sha256", row["sha256"]), ("brand_card", h)]))
        row["new_hotels"] = new
        fam["pages"][uri] = row
        for link in links:
            lk = link.strip("/")
            if _HILTON_IN_MARKET_LINK.match(lk) and (lk + "/") not in walked:
                queue.append(lk)
    fam["requests_spent"] = spent
    fam["cap_reached"] = bool(queue) and spent >= CAP_PER_FAMILY
    fam["disposition"] = "CITY_PAGES_ANSWERED_THIS_CLIENT" if fam["routes"] else "CITY_PAGES_YIELDED_NOTHING"
    return fam


# --------------------------------------------------------------------------- sitemaps
SITEMAP_FAMILIES = OrderedDict([
    ("WYNDHAM", "https://www.wyndhamhotels.com/sitemap.xml"),
    ("DRURY", "https://www.druryhotels.com/sitemap.xml"),
    ("LOEWS", "https://www.loewshotels.com/sitemap.xml"),
    ("ESA", "https://www.extendedstayamerica.com/sitemap.xml"),
    ("SONESTA", "https://www.sonesta.com/sitemap/sitemap-index.xml"),
    ("INTOWN", "https://www.intownsuites.com/sitemap.xml"),
    ("WOODSPRING", "https://www.woodspring.com/sitemap.xml"),
    ("CHOICE", "https://www.choicehotels.com/sitemapindex.xml"),
    ("IHG", "https://www.ihg.com/services/sitemaps/sitemap-index.xml"),
    ("BEST_WESTERN", "https://www.bestwestern.com/sitemap.xml"),
    ("RED_ROOF", "https://www.redroof.com/sitemap.xml"),
    ("MOTEL6", "https://www.motel6.com/sitemap.xml"),
    ("HYATT", "https://www.hyatt.com/sitemap.xml"),
    ("OMNI", "https://www.omnihotels.com/sitemap.xml"),
    ("FOUR_SEASONS", "https://www.fourseasons.com/sitemap.xml"),
    ("RADISSON", "https://www.radissonhotels.com/sitemapindex.xml"),
    ("STAYABLE", "https://www.stayable.com/sitemap.xml"),
    ("HOMETOWNE", "https://www.hometownestudios.com/sitemap.xml"),
    ("MANDARIN", "https://www.mandarinoriental.com/sitemap.xml"),
    ("ACCOR", "https://all.accor.com/sitemap.xml"),
    ("KIMPTON", "https://www.ihg.com/kimptonhotels/sitemap.xml"),
])
_LOC = re.compile(r"<loc>\s*([^<\s]+)\s*</loc>", re.I)
_CHILD_HINT = re.compile(r"hotel|propert|location|geo|main|sitemap-0|en[-_]us|america|north-america", re.I)
_CHILD_FIRST = re.compile(r"en[-_]us.*propert|propert.*en[-_]us|property-sitemap|/geo$", re.I)
_CHILD_SKIP = re.compile(r"_static|_interior|/(?!en-us)[a-z]{2}-[a-z]{2}/|sitemap_(?!en-us)[a-z]{2}-[a-z]{2}_|blog|article|news|"
                         r"rate-sitemap|travel-idea|post-sitemap|pointsofinterest", re.I)
#: A route that names ONE property, per family; everything else a sitemap lists (city indexes, locale
#: duplicates, rooms / meetings / dining sub-pages) is not a property route.
_PROPERTY_ROUTE = OrderedDict([
    ("WYNDHAM", re.compile(r"wyndhamhotels\.com/(?![a-z]{2}-[a-z]{2}/)[a-z0-9-]+/[a-z-]+-(?:oregon|washington)/[a-z0-9-]+/overview$", re.I)),
    ("DRURY", re.compile(r"druryhotels\.com/locations/[a-z-]+-(?:or|wa)/[a-z0-9-]+$", re.I)),
    ("LOEWS", re.compile(r"loewshotels\.com/[a-z0-9-]+/?$", re.I)),
    ("ESA", re.compile(r"extendedstayamerica\.com/hotels/(?:or|wa)/[a-z-]+/[a-z0-9-]+/?$", re.I)),
    ("SONESTA", re.compile(r"sonesta\.com/[a-z0-9-]+/(?:or|wa)/[a-z-]+/[a-z0-9-]+/?$", re.I)),
    ("INTOWN", re.compile(r"intownsuites\.com/extended-stay-locations/(?:oregon|washington)/[a-z-]+/[a-z0-9-]+/?$", re.I)),
    ("WOODSPRING", re.compile(r"woodspring\.com/extended-stay-hotels/locations/(?:oregon|washington)/[a-z-]+/[a-z0-9-]+/?$", re.I)),
])


def sitemap_family(name, entry, stats):
    fam = OrderedDict([("lane", "BRAND_SITEMAP"), ("entry_sitemap", entry), ("request_cap", CAP_PER_FAMILY),
                       ("requests_spent", 0), ("cap_reached", False), ("documents", []), ("routes", []),
                       ("disposition", None)])
    queue, walked, seen = [entry], set(), set()
    prop_rx = _PROPERTY_ROUTE.get(name)
    while queue and fam["requests_spent"] < CAP_PER_FAMILY:
        url = queue.pop(0)
        if url in walked:
            continue
        walked.add(url)
        row, body = fetch(url, stats, timeout=45)
        fam["requests_spent"] += 1
        text = body.decode("utf-8", "replace")
        locs = _LOC.findall(text)
        hits = [u for u in locs if is_lead(u) and (prop_rx is None or prop_rx.search(u.rstrip("/") if name == "WYNDHAM" else u))]
        row["locs"], row["property_routes"] = len(locs), len(hits)
        children = 0
        if "<sitemapindex" in text.lower() or (name == "ESA" and "sitemap" in url and not hits and locs):
            picked = [c for c in locs if _CHILD_HINT.search(c) and c not in walked and not _CHILD_SKIP.search(c)]
            picked.sort(key=lambda c: (0 if _CHILD_FIRST.search(c) else 1))
            for child in picked:
                queue.append(child)
                children += 1
        row["children_selected"] = children
        fam["documents"].append(row)
        for u in hits:
            if u in seen:
                continue
            seen.add(u)
            fam["routes"].append(OrderedDict([("family", name), ("route", u), ("property_code", ""),
                                              ("lane", "BRAND_SITEMAP"), ("found_in", url),
                                              ("found_in_sha256", row["sha256"])]))
    fam["cap_reached"] = bool(queue) and fam["requests_spent"] >= CAP_PER_FAMILY
    first = fam["documents"][0] if fam["documents"] else {}
    st = first.get("status")
    if st == 200 and fam["routes"]:
        fam["disposition"] = "SITEMAP_ANSWERED_THIS_CLIENT"
    elif st == 200:
        fam["disposition"] = "SITEMAP_ANSWERED_BUT_NO_MARKET_ROUTE_IN_THE_WALKED_SET"
    elif st in (403, 401, 429):
        fam["disposition"] = "SITEMAP_REFUSED_TO_THIS_CLIENT__STATUS_%s" % st
    elif st == 404:
        fam["disposition"] = "SITEMAP_NOT_AT_THIS_PATH__STATUS_404"
    elif first.get("error"):
        fam["disposition"] = "SITEMAP_UNREACHABLE__%s" % first["error"].split(":")[0]
    else:
        fam["disposition"] = "SITEMAP_STATUS_%s" % st
    return fam


def build(skip_network=False):
    stats = Stats()
    report = OrderedDict([
        ("schema", "ptf-brand-inventory/1.0"), ("work_order", WORK_ORDER),
        ("phase", "8 + 9D -- owned national inventory, then the brand's own inventory page and sitemap"),
        ("market_id", MARKET_ID), ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
        ("paid_provider_calls", 0), ("usd_spent", 0.0),
        ("a_roster_row_is_not_a_policy",
         "Everything here is ROUTING and IDENTITY evidence. No route carries or implies a pet policy, and no route "
         "admits a property to this market -- the postal code the property's OWN page states does that."),
        ("every_refusal_is_measured",
         "Each family was probed by THIS client at THIS moment. A refusal here is a fact about this request, never "
         "evidence that a family has no Portland property, and never inherited from an earlier order."),
        ("every_walk_is_bounded", "Each family carries a request cap of %d." % CAP_PER_FAMILY),
    ])
    owned, owned_meta = owned_leads()
    report["rung0_owned"] = OrderedDict([
        ("source", "launch_packages/pettripfinder/markets/reports/dayton_oh_brand_directory_harvest_001.json"),
        ("corpus", owned_meta), ("leads", len(owned)), ("by_family", dict(Counter(r["family"] for r in owned))),
        ("free_http_requests", 0)])
    families = OrderedDict()
    if not skip_network:
        families["MARRIOTT_STATE_SITEMAP"] = marriott_state_sitemap(stats)
        families["HILTON_CITY_PAGES"] = hilton_city_pages(stats)
        for name, entry in SITEMAP_FAMILIES.items():
            families[name] = sitemap_family(name, entry, stats)
            print("  %-14s %s routes=%d requests=%d" % (name, families[name]["disposition"], len(families[name]["routes"]),
                                                      families[name]["requests_spent"]), flush=True)
    routes = list(owned)
    for fam in families.values():
        routes.extend(fam.get("routes", []))
    dedup, seen = [], set()
    for r in routes:
        key = (r["family"], r["route"].rstrip("/").lower())
        if key in seen:
            continue
        seen.add(key)
        dedup.append(r)
    report["families"] = families
    report["free_http_requests"] = stats.requests
    report["bytes_read"] = stats.bytes
    report["dispositions"] = {k: v.get("disposition") for k, v in families.items() if v.get("disposition")}
    # The URL-token assertion applies to the lanes SELECTED BY URL. A brand city-page card is selected by its
    # OWN ADDRESS instead (card_in_observation_box), which is strictly better evidence than a slug, so its
    # routes are asserted on that and are exempt here. Hilton's own out-of-market cards are
    # slug and are refused by their postal code before this point.
    url_selected = [r for r in dedup if r.get("lane") != "BRAND_CITY_PAGE"]
    offenders = [r["route"] for r in url_selected if negative_hit(r["route"])]
    if offenders:
        raise SystemExit("a URL-selected route carries a NEGATIVE token; the lead filter is wrong:\n%s"
                         % "\n".join(offenders[:10]))
    card_selected = [r for r in dedup if r.get("lane") == "BRAND_CITY_PAGE"]
    bad_cards = [r["property_code"] for r in card_selected
                 if not card_in_observation_box(r.get("brand_card") or {})[0]]
    if bad_cards:
        raise SystemExit("a brand card outside the observation box was kept: %s" % bad_cards[:10])
    report["no_url_selected_route_carries_a_negative_token"] = True
    report["every_brand_card_kept_states_its_own_in_box_postal_code"] = True
    report["url_selected_routes"] = len(url_selected)
    report["card_selected_routes"] = len(card_selected)
    report["brand_cards_refused_by_their_own_address"] = [
        c for fam in families.values() for c in fam.get("cards_refused_by_their_own_address", [])]
    report["leads"] = dedup
    report["lead_count"] = len(dedup)
    report["leads_by_family"] = dict(Counter(r["family"] for r in dedup))
    report["leads_by_lane"] = dict(Counter(r["lane"] for r in dedup))
    report["documents_persisted_at"] = os.path.relpath(DOCS, _DASH).replace("\\", "/")
    return report


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--owned-only", action="store_true")
    args = ap.parse_args(argv)
    rep = build(skip_network=args.owned_only)
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rep, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("owned leads      :", rep["rung0_owned"]["leads"], rep["rung0_owned"]["by_family"])
    print("free requests    :", rep["free_http_requests"])
    for k, v in rep.get("dispositions", {}).items():
        print("  %-24s %s" % (k, v))
    print("TOTAL LEADS      :", rep["lead_count"], rep["leads_by_family"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
