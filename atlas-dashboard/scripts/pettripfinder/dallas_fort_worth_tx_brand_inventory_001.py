"""PTF-DALLAS-FORT-WORTH-TX-HARDENED-SOURCE-READY-001 -- Phase 12: owned national inventory, then the brands' own
inventories (cloned in shape from the Fort Myers / Salt Lake City / New Orleans helper; Metroplex localities, Texas
surfaces).

WHAT THIS IS
------------
Rung 0 and rung 2 of the acquisition ladder, run together because they answer the same question -- WHICH
PROPERTIES EXIST, and at WHAT OFFICIAL ROUTE -- and because rung 0 must be exhausted before a new request.

  rung 0  OWNED.  The committed national brand directory harvest (``dayton_oh_brand_directory_harvest_001.json``)
          is a SHARED national inventory. Every Metroplex Marriott route in it (DAL** / DFW** codes) is already
          durable at zero requests.
  rung 2  THE BRAND'S OWN INVENTORY PAGE, then its own sitemap. One plain HTTPS GET each, bounded per family:
            MARRIOTT  the brand's own Texas hotel sitemap page (MARSHA code, title, route)
            HILTON    the brand's own Metroplex city pages and every in-market interlink they publish
            WYNDHAM / ESA / SONESTA / WOODSPRING / DRURY / ...  the brand's own sitemap
            CHOICE / IHG / BEST WESTERN / RED ROOF / MOTEL 6 / HYATT / RADISSON / OMNI / LOEWS / ...
                      re-probed at their sitemap; what THIS client saw is recorded

A ROSTER ROW IS NOT A POLICY, AND NOT AN ADMISSION -- AND NOT PROOF OF OPERATION
------------------------------------------------------------------------------
Everything here is ROUTING and IDENTITY evidence. No route carries or implies a pet policy, no route admits a
property (the postal code the property's OWN page states does that), and no route proves a hotel is operating today:
a brand sitemap can still list a converted or pre-opening hotel. The property's own CURRENT page decides.

THE METROPLEX LEAD FILTER, AND WHY A CODE PREFIX IS NOT A PLACE
--------------------------------------------------------------
1. MARRIOTT'S MARSHA PREFIXES DAL AND DFW ARE NOT THIS MARKET. They code Denton, Rockwall, Waxahachie, Weatherford,
   Sherman and Waco too, which this market refuses. The code is a LEAD, a title's own place word is a LEAD, and a
   refused place token OUTRANKS both unless an admitted place is named beside it. The code never places a property.
2. MANY METROPLEX NAMES ARE NOT UNIQUE: Arlington (Virginia), Frisco (Colorado), Addison (Illinois), Allen,
   Richardson, Garland, Mesquite (Nevada), Dallas (Georgia, Oregon, Pennsylvania). Outside the few unique tokens
   (Fort Worth, Las Colinas, Grand Prairie, Farmers Branch, The Colony, Flower Mound, North Richland Hills), a URL lead
   needs a Texas marker; a Hilton card is decided by its own Texas postal code.
3. THE CHAINS PUT "DALLAS" ON HOTELS IN IRVING, ADDISON, FARMERS BRANCH, RICHARDSON, PLANO AND FRISCO, "FORT WORTH" ON
   HOTELS IN SAGINAW, ROANOKE AND BURLESON, AND "DFW AIRPORT" ON HOTELS IN FIVE CITIES. Every lead is placed by its
   own postal code; its MUNICIPALITY by its own premises.

Outputs:
  launch_packages/pettripfinder/markets/reports/dallas_fort_worth_tx_brand_inventory_001.json
  data/acquisition/dallas_fort_worth_tx_brand_001/<sha256>.bin   (documents as returned)
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

WORK_ORDER = "PTF-DALLAS-FORT-WORTH-TX-HARDENED-SOURCE-READY-001"
MARKET_ID = "dallas-fort-worth-tx"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
DOCS = os.path.join(_DASH, "data", "acquisition", "dallas_fort_worth_tx_brand_001")
OWNED = os.path.join(REPORTS, "dayton_oh_brand_directory_harvest_001.json")
OUT = os.path.join(REPORTS, "dallas_fort_worth_tx_brand_inventory_001.json")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")

#: Metroplex places, as a brand spells them in a URL. A brand's marketing name never admits a property -- these are
#: LEAD filters only, and every lead is placed afterwards by its own postal code.
LOCALITIES = (
    "dallas", "fort-worth", "ft-worth", "irving", "las-colinas", "grapevine", "coppell", "euless", "bedford", "hurst",
    "arlington", "grand-prairie", "addison", "richardson", "plano", "frisco", "carrollton", "farmers-branch",
    "the-colony", "lewisville", "allen", "mckinney", "flower-mound", "southlake", "roanoke", "trophy-club",
    "westlake", "northlake", "mansfield", "mesquite", "garland", "rowlett", "desoto", "duncanville", "cedar-hill",
    "lancaster", "north-richland-hills", "keller", "colleyville", "haltom-city", "white-settlement", "saginaw",
    "alliance", "dfw", "love-field", "galleria", "legacy", "stonebriar", "stockyards", "hutchins", "seagoville",
    "balch-springs", "sachse", "highland-village", "kennedale", "crowley", "benbrook", "lake-worth", "azle",
    "university-park", "highland-park", "centreport",
)
#: Tokens that need no state marker because no other place in the chains' inventories spells them this way.
UNIQUE_TOKENS = ("fort-worth", "ft-worth", "las-colinas", "grand-prairie", "farmers-branch", "the-colony",
                 "flower-mound", "north-richland-hills", "dfw-airport", "dallas-fort-worth", "dallas-love-field",
                 "haltom-city", "white-settlement", "centreport")
#: A state marker: Texas -- on a word boundary.
_STATE_MARKER = re.compile(r"(?<![a-z])texas(?![a-z])|[-_/]tx(?:[-_/.]|$)", re.I)
AZ_MARKERS = ()
#: The refused neighbours and every other state. Matched on WORD boundaries (a token never matches inside a word:
#: "ennis" is not in "tennis"). The refused North Texas neighbours come FIRST.
NEGATIVE = (
    # --- refused North Texas neighbours (FUTURE_STANDALONE or refused after careful evaluation) ---
    "denton", "corinth", "lake-dallas", "rockwall", "royse-city", "waxahachie", "ennis", "midlothian", "red-oak",
    "weatherford", "willow-park", "aledo", "cleburne", "burleson", "decatur", "granbury", "glen-rose",
    "mineral-wells", "forney", "terrell", "corsicana", "greenville", "sherman", "denison", "gainesville", "waco",
    "prosper", "celina", "little-elm", "wylie", "anna", "melissa", "princeton", "texoma",
    # --- other Texas markets and regions ---
    "austin", "san-antonio", "houston", "galveston", "el-paso", "lubbock", "amarillo", "corpus-christi", "laredo",
    "mcallen", "brownsville", "killeen", "temple", "college-station", "tyler", "longview", "beaumont", "midland",
    "odessa", "abilene", "san-angelo", "wichita-falls", "texarkana", "new-braunfels", "san-marcos", "round-rock",
    "georgetown", "katy", "sugar-land", "the-woodlands", "conroe", "pearland", "league-city", "baytown",
    # --- every other state (Texas is NOT here) ---
    "oregon", "florida", "ohio", "arizona", "tennessee", "california", "utah", "colorado", "georgia", "carolina",
    "virginia", "pennsylvania", "new-york", "michigan", "indiana", "wisconsin", "idaho", "montana", "alaska", "hawaii",
    "new-jersey", "maryland", "massachusetts", "kentucky", "illinois", "iowa", "nebraska", "connecticut",
    "new-hampshire", "vermont", "louisiana", "nevada", "new-mexico", "oklahoma", "arkansas", "missouri", "kansas",
    "alabama", "mississippi", "dakota", "minnesota", "wyoming", "washington-dc", "canada", "ontario", "manitoba",
    "mexico", "bahamas", "caribbean", "puerto-rico",
)
_NEGATIVE_RX = [(n, re.compile(r"(?<![a-z])%s(?![a-z])" % re.escape(n))) for n in NEGATIVE]

#: AMBIGUOUS refusal tokens: refused ONLY when the URL / title names no admitted place beside them. None here: the
#: refused neighbours have no Metroplex alias.
_ADMITTED_CITY_TOKEN = re.compile(r"(dallas|fort-worth|irving|las-colinas|grapevine|arlington|plano|frisco)", re.I)
_AMBIGUOUS_NEGATIVE = re.compile(r"(?!x)x")

#: Negatives that need a WORD BOUNDARY, not a substring.
NEGATIVE_PATTERNS = (
    # a state suffix other than Texas on a route segment
    re.compile(r"-(?:or|wa|il|oh|ky|mo|in|ca|nj|fl|md|ma|nh|wi|mi|pa|ne|mn|wy|la|nm|co|az|ut|nc|ga|nv|ok|ar|sc|de|va|dc|al|ia|tn|ny|id|mt|ak|hi|me|bc|nd|sd|ks|ms)(?![a-z])/", re.I),
    re.compile(r"/(?:or|wa|il|oh|ky|mo|in|ca|nj|fl|md|ma|nh|wi|mi|pa|ne|mn|wy|la|nm|co|az|ut|nv|ok|ar|sc|de|va|dc|al|ia|tn|ny|id|mt|ak|hi|me|bc|nd|sd|ks|ms)/", re.I),
)


def negative_hit(url):
    """The refusal token a URL carries, or ""."""
    u = (url or "").lower()
    for n, rx in _NEGATIVE_RX:
        if rx.search(u):
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
#: properties" with each one's own structured address card, so a Dallas seed page reaches Denton, Rockwall and
#: Waxahachie. Every card is kept or refused on its OWN street, city, state and postal code: the Dallas and Fort Worth
#: sectional centers (750-753 / 760-762) -- the refused neighbours inside them kept only so the boundary audit SEES
#: them and refuses them by postal code. A card from any other state cannot pass, and a card whose state its own
#: postal code contradicts cannot pass either.
CARD_POSTAL_PREFIXES = {"TX": ("750", "751", "752", "753", "760", "761", "762")}
CARD_STATES = {"TX": "TX", "TEXAS": "TX"}


def card_in_observation_box(card):
    """(kept, why) for a brand card, decided by the card's OWN address."""
    state = " ".join(str(card.get("state") or "").split()).upper()
    postal = "".join(ch for ch in str(card.get("postal_code") or "") if ch.isdigit())[:5]
    if not state or state not in CARD_STATES:
        return False, "the card's OWN state is %r; every corridor of this market is in Texas" % state
    if not postal:
        return False, "the card states no postal code of its own, so nothing places it"
    if postal[:3] not in CARD_POSTAL_PREFIXES[CARD_STATES[state]]:
        return False, ("the card's OWN postal code %s is outside this market's observation box (%s prefixes)"
                       % (postal, CARD_STATES[state]))
    return True, "the card's OWN postal code %s is inside the observation box" % postal


HILTON_SEEDS = [
    "texas/dallas", "texas/fort-worth", "texas/irving", "texas/arlington", "texas/grapevine", "texas/plano",
    "texas/frisco", "texas/addison", "texas/richardson", "texas/grand-prairie", "texas/lewisville",
    "texas/the-colony", "texas/carrollton", "texas/farmers-branch", "texas/coppell", "texas/euless", "texas/bedford",
    "texas/hurst", "texas/north-richland-hills", "texas/southlake", "texas/flower-mound", "texas/allen",
    "texas/mckinney", "texas/mesquite", "texas/garland", "texas/rowlett", "texas/mansfield", "texas/duncanville",
    "texas/desoto", "texas/cedar-hill", "texas/lancaster", "texas/roanoke", "texas/keller", "texas/saginaw",
    "texas/haltom-city", "texas/white-settlement", "texas/benbrook", "texas/colleyville", "texas/denton",
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


#: Marriott codes the Metroplex DAL** / DFW** -- and Denton, Rockwall, Waxahachie and Sherman alike -- so the code is
#: a LEAD filter only, deliberately weaker than a negative token, and never places a property. Hilton's ctyhocn for
#: this region is DAL / DFW / FTW / AFW / ADS + letters; IHG's is DAL / DFW / FTW + two.
_SAN_CODE = re.compile(r"/hotels/(?:dal|dfw)[a-z0-9]{2}-", re.I)
_SAN_CTYHOCN = re.compile(r"/hotels/(?:dal|dfw|ftw|afw|ads)[a-z]{4}\b", re.I)
_SAN_IHG = re.compile(r"/hotels/us/en/[a-z0-9-]+/(?:dal|dfw|ftw|afw)[a-z]{2}/", re.I)


def is_lead(url):
    u = url.lower()
    # A negative token wins over EVERYTHING, including a brand property code.
    if negative_hit(u):
        return False
    if _SAN_CODE.search(u) or _SAN_CTYHOCN.search(u) or _SAN_IHG.search(u):
        return True
    if any(re.search(r"(?<![a-z])%s(?![a-z])" % re.escape(t), u) for t in UNIQUE_TOKENS):
        return True
    return (any(re.search(r"(?<![a-z])%s(?![a-z])" % re.escape(t), u) for t in LOCALITIES)
            and bool(_STATE_MARKER.search(u)))


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
MARRIOTT_STATE_SITEMAPS = ("https://www.marriott.com/en-us/hotel-sitemap/usa-texas-hotel-sitemap",)
MARRIOTT_STATE_SITEMAP = MARRIOTT_STATE_SITEMAPS[0]
_MARSHA = re.compile(r'\{"marsha":"([a-z0-9]{5})","title":"((?:[^"\\]|\\.)*)","url":"([^"]+)"\}', re.I)
_DFW_TITLE_WORDS = (r"dallas|fort worth|ft\.? worth|irving|las colinas|grapevine|coppell|euless|bedford|hurst|"
                    r"arlington|grand prairie|addison|richardson|plano|frisco|carrollton|farmers branch|the colony|"
                    r"lewisville|allen|mckinney|flower mound|southlake|roanoke|trophy club|westlake|northlake|mansfield|"
                    r"mesquite|garland|rowlett|desoto|duncanville|cedar hill|lancaster|north richland hills|keller|"
                    r"colleyville|alliance|dfw|love field|galleria|legacy|stonebriar|stockyards")
#: Titles that name a place THIS market admits.
_TITLE_PLACES = re.compile(r"\b(%s)\b" % _DFW_TITLE_WORDS, re.I)
#: An admitted PLACE in a title.
_TITLE_ADMITTED_CITY = _TITLE_PLACES
#: Titles that name a place THIS market refuses. Checked FIRST -- unless the title also names an admitted place.
_TITLE_REFUSED = re.compile(r"\b(denton|corinth|rockwall|royse city|waxahachie|ennis|midlothian|red oak|weatherford|"
                            r"willow park|aledo|cleburne|burleson|decatur|granbury|glen rose|mineral wells|forney|"
                            r"terrell|corsicana|greenville|sherman|denison|gainesville|waco|prosper|celina|little elm|"
                            r"wylie|austin|san antonio|houston)\b", re.I)


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
        text = body.decode("utf-8", "replace")
        for code, title, url in _MARSHA.findall(text):
            code = code.lower()
            if code in seen:
                continue
            seen.add(code)
            fam["properties_listed"] += 1
            title = json.loads('"%s"' % title)
            # A refusal token in the brand's OWN route outranks a title word -- Marriott's DAL / DFW prefixes title
            # Denton, Rockwall and Waxahachie hotels too.
            if negative_hit(url):
                fam.setdefault("refused_by_title", []).append(
                    OrderedDict([("property_code", code), ("brand_title", title),
                                 ("why", "the brand's own route names a place this market refuses (%s)"
                                  % negative_hit(url))]))
                continue
            if _TITLE_REFUSED.search(title) and not _TITLE_ADMITTED_CITY.search(title):
                fam.setdefault("refused_by_title", []).append(
                    OrderedDict([("property_code", code), ("brand_title", title),
                                 ("why", "the brand's own title names a place this market refuses")]))
                continue
            if not (code.startswith(("dal", "dfw")) or _TITLE_PLACES.search(title)):
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
    ("WYNDHAM", re.compile(r"wyndhamhotels\.com/(?![a-z]{2}-[a-z]{2}/)[a-z0-9-]+/[a-z-]+-texas/[a-z0-9-]+/overview$", re.I)),
    ("DRURY", re.compile(r"druryhotels\.com/locations/[a-z-]+-tx/[a-z0-9-]+$", re.I)),
    ("LOEWS", re.compile(r"loewshotels\.com/[a-z0-9-]+/?$", re.I)),
    ("ESA", re.compile(r"extendedstayamerica\.com/hotels/tx/[a-z-]+/[a-z0-9-]+/?$", re.I)),
    ("SONESTA", re.compile(r"sonesta\.com/[a-z0-9-]+/tx/[a-z-]+/[a-z0-9-]+/?$", re.I)),
    ("INTOWN", re.compile(r"intownsuites\.com/extended-stay-locations/texas/[a-z-]+/[a-z0-9-]+/?$", re.I)),
    ("WOODSPRING", re.compile(r"woodspring\.com/extended-stay-hotels/locations/texas/[a-z-]+/[a-z0-9-]+/?$", re.I)),
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
        ("phase", "12 -- owned national inventory, then the brand's own inventory page and sitemap"),
        ("market_id", MARKET_ID), ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
        ("paid_provider_calls", 0), ("usd_spent", 0.0),
        ("a_roster_row_is_not_a_policy",
         "Everything here is ROUTING and IDENTITY evidence. No route carries or implies a pet policy, and no route "
         "admits a property to this market -- the postal code the property's OWN page states does that."),
        ("every_refusal_is_measured",
         "Each family was probed by THIS client at THIS moment. A refusal here is a fact about this request, never "
         "evidence that a family has no Metroplex property, and never inherited from an earlier order."),
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
