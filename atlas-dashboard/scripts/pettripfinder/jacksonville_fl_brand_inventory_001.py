"""PTF-JACKSONVILLE-FL-HARDENED-SOURCE-READY-001 -- Phases 8 + 9D: owned national inventory, then the brands'
own inventories (cloned in shape from the West Palm Beach helper; Northeast Florida localities, Florida surfaces).

WHAT THIS IS
------------
Rung 0 and rung 2 of the acquisition ladder, run together because they answer the same question -- WHICH
PROPERTIES EXIST, and at WHAT OFFICIAL ROUTE -- and because rung 0 must be exhausted before a new request.

  rung 0  OWNED.  The committed national brand directory harvest (``dayton_oh_brand_directory_harvest_001.json``)
          is a SHARED national inventory. Every JAX-coded Marriott route in it is already durable at zero requests.
  rung 2  THE BRAND'S OWN INVENTORY PAGE, then its own sitemap. One plain HTTPS GET each, bounded per family:
            MARRIOTT  the brand's own Florida hotel sitemap page (MARSHA code, title, route)
            HILTON    the brand's own Florida city pages and every in-market interlink they publish
            WYNDHAM / DRURY / LOEWS / ESA / SONESTA / INTOWN / WOODSPRING  the brand's own sitemap
            CHOICE / IHG / BEST WESTERN / RED ROOF / MOTEL 6 / HYATT / OMNI / FOUR SEASONS / RADISSON / STAYABLE
                      re-probed at their sitemap; what THIS client saw is recorded

A ROSTER ROW IS NOT A POLICY, AND NOT AN ADMISSION
--------------------------------------------------
Everything here is ROUTING and IDENTITY evidence. No route carries or implies a pet policy, and no route admits a
property: the postal code the property's OWN page (or its DBPR licence) states does that.

THE "JACKSONVILLE" LEAD FILTER IS THE HARDEST ONE THIS FACTORY HAS BUILT, FOR THREE REASONS
------------------------------------------------------------------------------------------
1. THERE ARE AT LEAST SIX JACKSONVILLES. Florida's is the largest, but the chains also publish hotels in
   Jacksonville, NORTH CAROLINA (a LIVE PetTripFinder market), Jacksonville, Arkansas, Jacksonville, Texas,
   Jacksonville, Illinois, Jacksonville, Alabama and Jacksonville, Oregon. Every one is refused by an explicit
   negative token, and the North Carolina tokens are listed first because that market is LIVE and a double
   admission would publish one hotel twice.
2. MARRIOTT'S MARSHA PREFIX JAX IS NOT THIS MARKET. It also codes St. Augustine (Casa Monica, World Golf
   Village, the historic-downtown Renaissance, two Courtyards, a Fairfield, an AC, a City Express and a Tribute
   hotel) and WAYCROSS, GEORGIA. A code is authoritative for the brand's identity and decides nothing about
   geography, so a NEGATIVE TOKEN OVERRIDES A CODE MATCH here.
3. SEVERAL JACKSONVILLE NEIGHBOURHOOD NAMES BELONG TO OTHER PLACES ENTIRELY. "Mandarin" is a global luxury
   brand; "Arlington" is in Virginia and Texas; "Riverside" is in California; "Atlantic Beach" is also in North
   Carolina and New York; "Middleburg" is also in Virginia; "Deerwood" is also in Minnesota. None of those words
   is used as a bare lead token: each either requires a Florida marker or is not used at all.

A LANE-HYGIENE FINDING CARRIED FORWARD RATHER THAN CLONED
---------------------------------------------------------
The West Palm Beach helper's Marriott state-sitemap filter still carried Fort Lauderdale's title list, so it
selected 53 BROWARD routes (``fll*`` codes, "W Fort Lauderdale", "Hollywood Beach Marriott") into that market's
lead set. They were harmless -- every one was later refused by its own postal code -- but they were noise inside
a 177-route count. The filter here is written for THIS market's places and MARSHA prefix, and the selection is
ASSERTED: no route this lane keeps may carry a negative token.

Outputs:
  launch_packages/pettripfinder/markets/reports/jacksonville_fl_brand_inventory_001.json
  data/acquisition/jacksonville_fl_brand_001/<sha256>.bin   (documents as returned)
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

WORK_ORDER = "PTF-JACKSONVILLE-FL-HARDENED-SOURCE-READY-001"
MARKET_ID = "jacksonville-fl"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
DOCS = os.path.join(_DASH, "data", "acquisition", "jacksonville_fl_brand_001")
OWNED = os.path.join(REPORTS, "dayton_oh_brand_directory_harvest_001.json")
OUT = os.path.join(REPORTS, "jacksonville_fl_brand_inventory_001.json")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36")

#: Northeast Florida places, as a brand spells them in a URL. A brand's marketing name never admits a property
#: -- these are LEAD filters only, and every lead is placed afterwards by its own postal code.
LOCALITIES = (
    "jacksonville", "jacksonville-beach", "jax-beach", "jacksonville-airport", "jacksonville-downtown",
    "jacksonville-south", "jacksonville-north", "jacksonville-east", "jacksonville-west",
    "atlantic-beach", "neptune-beach", "mayport", "baldwin", "middleburg", "deerwood", "callahan",
    "ponte-vedra", "ponte-vedra-beach", "sawgrass", "amelia-island", "fernandina", "fernandina-beach",
    "orange-park", "fleming-island", "green-cove-springs", "yulee", "hilliard", "oakleaf", "nocatee",
    "baymeadows", "butler-boulevard", "st-johns-town-center", "town-center", "tapestry-park",
    "mayo-clinic", "bartram", "flagler-center", "southbank", "riverwalk", "san-marco", "avondale",
    "julington-creek", "fruit-cove", "st-johns",
)
#: Tokens that need no Florida marker because no other place in the chains' inventories spells them this way.
UNIQUE_TOKENS = ("jacksonville-fl", "jacksonville-florida", "jacksonvillefl", "ponte-vedra", "sawgrass",
                 "amelia-island", "fernandina", "orange-park-fl", "orange-park-florida", "fleming-island",
                 "green-cove-springs", "yulee", "neptune-beach", "mayport", "baymeadows", "tapestry-park",
                 "st-johns-town-center", "butler-boulevard", "flagler-center", "julington-creek",
                 "jacksonville-beach", "jax-beach", "duval-county", "bartram-park", "oakleaf", "nocatee",
                 "mayo-clinic")
FL_MARKERS = ("florida", "-fl-", "-fl/", "_fl", "-fl.", "/fl/", "-fl_", "/florida/", "/us/fl/")
#: Look-alikes that carry a Jacksonville-area word but are somewhere else entirely. The NORTH CAROLINA tokens
#: come first because jacksonville-nc is a LIVE market and a double admission would publish one hotel twice.
#: The St. Augustine, World Golf Village and Waycross tokens come next because Marriott's JAX MARSHA prefix
#: reaches all three, so a code match must not outrank them.
NEGATIVE = (
    # --- Jacksonville, NORTH CAROLINA: a LIVE PetTripFinder market ---
    "jacksonville-north-carolina", "north-carolina", "camp-lejeune", "camplejeune",
    "onslow", "new-river", "hotels-in-jacksonville-nc", "richlands", "sneads-ferry", "swansboro", "hubert",
    "midway-park",
    # --- the other Jacksonvilles: only the UNAMBIGUOUS spellings live here. The two-letter state suffixes
    # --- are in NEGATIVE_PATTERNS below, because "jacksonville-or" matches inside
    # --- "jacksonville-orange-park" -- a real Marriott route in THIS market. The assertion caught it.
    "jacksonville-arkansas", "little-rock",
    "jacksonville-texas", "jacksonville-illinois",
    "jacksonville-alabama", "jacksonville-oregon",
    # --- Northeast Florida places this market REFUSES ---
    "st-augustine", "saint-augustine", "world-golf-village", "casa-monica",
    "palm-coast", "flagler-beach", "bunnell", "palatka", "crescent-city", "keystone-heights",
    "macclenny", "lake-city", "gainesville", "daytona", "ormond-beach", "deland", "new-smyrna",
    # --- GEORGIA ---
    "waycross", "brunswick", "st-simons", "saint-simons", "jekyll", "kingsland", "st-marys", "saint-marys",
    "savannah", "georgia", "golden-isles", "sea-island",
    # --- other live Florida markets ---
    "orlando", "kissimmee", "tampa", "st-petersburg", "clearwater", "miami", "fort-lauderdale",
    "west-palm-beach", "boca-raton", "sarasota", "naples", "ocala", "pensacola", "tallahassee",
    # --- non-Florida look-alikes of Jacksonville neighbourhood names ---
    "mandarin-oriental", "mandarinoriental", "arlington-va", "arlington-tx", "arlington-virginia",
    "riverside-ca", "riverside-california", "atlantic-beach-nc", "atlantic-beach-ny",
    "middleburg-va", "middleburg-virginia", "deerwood-mn", "minnesota",
)

#: Negatives that need a WORD BOUNDARY, not a substring. Measured, not assumed: the plain token
#: "jacksonville-or" (Jacksonville, Oregon) matches inside "jacksonville-orange-park", and Marriott publishes
#: TWO real Jacksonville hotels at that slug (jaxco Courtyard and jaxop Fairfield Inn & Suites Orange Park).
#: The build-time assertion caught both, which is what it is for. A two-letter state suffix is therefore matched
#: only when nothing alphabetic follows it.
NEGATIVE_PATTERNS = (
    re.compile(r"jacksonville-(?:nc|ar|tx|il|al|or)(?![a-z])", re.I),
    re.compile(r"-ga(?![a-z])", re.I),
    re.compile(r"/ga/", re.I),
    re.compile(r"-(?:nc|ar|tx|il|al)(?![a-z])/", re.I),
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
    return ""


CAP_PER_FAMILY = 150

#: A BRAND CARD IS DECIDED BY ITS OWN ADDRESS, NOT BY ITS URL -- and this is the second half of the
#: "a brand prefix is not a market" finding, measured here rather than inherited.
#:
#: Hilton's city pages publish "the twenty nearest properties" with each one's own structured address card, so a
#: Florida seed page reaches across the state line: this client was handed `jaxklht` (Home2 Suites KINGSLAND,
#: GEORGIA), `jaxgape` (Spark Kingsland), `kngldhx` (Hampton Kingsland), `jaxmahx` (Hampton MACCLENNY, Baker
#: County) and `ustsggv` (Hilton Vacation Club ST. AUGUSTINE) from this market's own seeds. Hilton's CTYHOCN
#: prefix JAX therefore reaches Georgia exactly as Marriott's MARSHA prefix JAX reaches St. Augustine and
#: Waycross.
#:
#: A URL-token test is the wrong instrument for these, because the card carries something better: the property's
#: OWN street, city, state and postal code. Every card is therefore kept or refused on THAT, using the same
#: postal-prefix box the census lane uses -- 320 and 322 (Duval, Clay, Nassau, St. Johns and the refused
#: St. Augustine codes), 321 (Volusia / Flagler) and 326 (Alachua). A Georgia card cannot pass at all, which is
#: the state-line refusal expressed mechanically. The refusals are RECORDED with their own premises rather than
#: dropped, so the boundary audit sees them.
CARD_POSTAL_PREFIXES = ("320", "322", "321", "326")
CARD_STATES = ("FL", "FLORIDA")


def card_in_observation_box(card):
    """(kept, why) for a brand card, decided by the card's OWN address."""
    state = " ".join(str(card.get("state") or "").split()).upper()
    postal = "".join(ch for ch in str(card.get("postal_code") or "") if ch.isdigit())[:5]
    if state and state not in CARD_STATES:
        return False, "the card's OWN state is %r; every corridor of this market is in Florida" % state
    if not postal:
        return False, "the card states no postal code of its own, so nothing places it"
    if postal[:3] not in CARD_POSTAL_PREFIXES:
        return False, ("the card's OWN postal code %s is outside this market's observation box (320/322 "
                       "Duval-Clay-Nassau-St. Johns, 321 Volusia-Flagler, 326 Alachua)" % postal)
    return True, "the card's OWN postal code %s is inside the observation box" % postal

HILTON_SEEDS = [
    "florida/jacksonville", "florida/jacksonville-beach", "florida/atlantic-beach", "florida/neptune-beach",
    "florida/ponte-vedra-beach", "florida/ponte-vedra", "florida/amelia-island", "florida/fernandina-beach",
    "florida/orange-park", "florida/fleming-island", "florida/middleburg", "florida/green-cove-springs",
    "florida/yulee", "florida/saint-johns", "florida/baldwin", "florida/callahan",
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


#: Marriott codes Northeast Florida properties JAX** (JAX is the MARSHA prefix built on the airport code:
#: JAXFL, JAXMD, JAXSW ...). The code is the brand's own identity for the premises and is a LEAD filter only,
#: and here it is DELIBERATELY WEAKER than a negative token: the JAX prefix also codes St. Augustine and
#: Waycross, Georgia, so `jaxbr-world-golf-village` and `jaxfw-fairfield-inn-and-suites-waycross` must lose.
#: The code never places a property. Its own postal code does.
_JAX_CODE = re.compile(r"/hotels/jax[a-z0-9]{2}-", re.I)
#: Hilton's ctyhocn for this region is JAX + four letters (JAXDTDT, JAXBHHX ...); IHG's is JAX + two.
_JAX_CTYHOCN = re.compile(r"/hotels/jax[a-z]{4}\b", re.I)
_JAX_IHG = re.compile(r"/hotels/us/en/[a-z0-9-]+/jax[a-z]{2}/", re.I)


def is_lead(url):
    u = url.lower()
    # A negative token wins over EVERYTHING, including a brand property code. That ordering is the whole
    # defence against Marriott's JAX prefix reaching St. Augustine and Waycross, and against the five other
    # Jacksonvilles the chains publish.
    if negative_hit(u):
        return False
    if _JAX_CODE.search(u) or _JAX_CTYHOCN.search(u) or _JAX_IHG.search(u):
        return True
    if any(t in u for t in UNIQUE_TOKENS):
        return True
    return any(t in u for t in LOCALITIES) and any(m in u for m in FL_MARKERS)


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
MARRIOTT_STATE_SITEMAP = "https://www.marriott.com/en-us/hotel-sitemap/usa-florida-hotel-sitemap"
_MARSHA = re.compile(r'\{"marsha":"([a-z0-9]{5})","title":"((?:[^"\\]|\\.)*)","url":"([^"]+)"\}', re.I)
#: Titles that name a place THIS market admits. Written for this market rather than inherited (see the
#: lane-hygiene finding in the module docstring).
_TITLE_PLACES = re.compile(r"\b(jacksonville|jax|jacksonville beach|atlantic beach|neptune beach|mayport|"
                           r"ponte vedra|sawgrass|amelia island|fernandina|orange park|fleming island|"
                           r"middleburg|green cove springs|yulee|baymeadows|deerwood|butler boulevard|"
                           r"st\.? johns town center|tapestry park|mayo clinic|bartram|flagler center|"
                           r"southbank|riverwalk|san marco|avondale|julington creek|nocatee|oakleaf|"
                           r"baldwin|callahan|hilliard)\b", re.I)
#: Titles that name a place THIS market refuses, even under the JAX prefix. Checked FIRST.
#: Titles that name a place THIS market refuses, even under the JAX prefix. Checked FIRST, and it has to carry
#: the other LIVE Florida markets too: Marriott's Florida sitemap titles "AC Hotel Fort Lauderdale SAWGRASS
#: Mills Sunrise", and "Sawgrass" is one of THIS market's own place words (TPC Sawgrass, Ponte Vedra Beach). A
#: place word is not a place. The refusal list is checked before the admission list so the Broward hotel loses.
_TITLE_REFUSED = re.compile(r"\b(st\.? augustine|saint augustine|world golf village|casa monica|waycross|"
                            r"palm coast|flagler beach|gainesville|daytona|ormond|palatka|lake city|"
                            r"brunswick|st\.? simons|jekyll|kingsland|st\.? marys|savannah|"
                            r"north carolina|camp lejeune|"
                            r"fort lauderdale|ft\.? lauderdale|sawgrass mills|sunrise|plantation|weston|"
                            r"hollywood|pompano|deerfield|dania|hallandale|coral springs|"
                            r"west palm|palm beach|boca raton|delray|boynton|jupiter|wellington|"
                            r"miami|miami beach|coral gables|doral|aventura|key biscayne|homestead|"
                            r"orlando|kissimmee|lake buena vista|celebration|altamonte|sanford|"
                            r"tampa|st\.? petersburg|clearwater|brandon|lakeland|bradenton|sarasota|"
                            r"naples|fort myers|bonita|estero|punta gorda|cape coral|"
                            r"key west|key largo|islamorada|marathon|"
                            r"tallahassee|pensacola|destin|panama city|fort walton|navarre|"
                            r"ocala|melbourne|cocoa|titusville|viera|port st\.? lucie|stuart|vero beach|"
                            r"sebring|winter haven|haines city|davenport|leesburg|"
                            r"valdosta|tifton|macon|atlanta|columbus ga)\b", re.I)


def marriott_state_sitemap(stats):
    fam = OrderedDict([("lane", "BRAND_STATE_SITEMAP_PAGE"), ("url", MARRIOTT_STATE_SITEMAP), ("document", None),
                       ("properties_listed", 0), ("routes", [])])
    row, body = fetch(MARRIOTT_STATE_SITEMAP, stats, timeout=60)
    fam["document"] = row
    text = body.decode("utf-8", "replace")
    seen = set()
    for code, title, url in _MARSHA.findall(text):
        code = code.lower()
        if code in seen:
            continue
        seen.add(code)
        fam["properties_listed"] += 1
        title = json.loads('"%s"' % title)
        if _TITLE_REFUSED.search(title):
            fam.setdefault("refused_by_title", []).append(
                OrderedDict([("property_code", code), ("brand_title", title),
                             ("why", "the brand's own title names a place this market refuses; the JAX "
                                     "MARSHA prefix is not this market")]))
            continue
        if not (code.startswith("jax") or _TITLE_PLACES.search(title)):
            continue
        fam["routes"].append(OrderedDict([("family", "MARRIOTT"), ("route", url), ("property_code", code),
                                          ("brand_title", title), ("lane", "BRAND_STATE_SITEMAP_PAGE"),
                                          ("found_in", MARRIOTT_STATE_SITEMAP), ("found_in_sha256", row["sha256"])]))
    fam["disposition"] = ("STATE_SITEMAP_ANSWERED_THIS_CLIENT" if fam["routes"] else "STATE_SITEMAP_STATUS_%s" % row["status"])
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


_HILTON_IN_MARKET_LINK = re.compile(r"^locations/usa/florida/(%s)(/[a-z0-9-]+)?/?$" % "|".join(
    re.escape(s.split("/")[1]) for s in HILTON_SEEDS))


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
    ("WYNDHAM", re.compile(r"wyndhamhotels\.com/(?![a-z]{2}-[a-z]{2}/)[a-z0-9-]+/[a-z-]+-florida/[a-z0-9-]+/overview$", re.I)),
    ("DRURY", re.compile(r"druryhotels\.com/locations/[a-z-]+-fl/[a-z0-9-]+$", re.I)),
    ("LOEWS", re.compile(r"loewshotels\.com/[a-z0-9-]+/?$", re.I)),
    ("ESA", re.compile(r"extendedstayamerica\.com/hotels/fl/[a-z-]+/[a-z0-9-]+/?$", re.I)),
    ("SONESTA", re.compile(r"sonesta\.com/[a-z0-9-]+/fl/[a-z-]+/[a-z0-9-]+/?$", re.I)),
    ("INTOWN", re.compile(r"intownsuites\.com/extended-stay-locations/florida/[a-z-]+/[a-z0-9-]+/?$", re.I)),
    ("WOODSPRING", re.compile(r"woodspring\.com/extended-stay-hotels/locations/florida/[a-z-]+/[a-z0-9-]+/?$", re.I)),
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
         "admits a property to this market -- the postal code the property's OWN page or DBPR licence states does that."),
        ("every_refusal_is_measured",
         "Each family was probed by THIS client at THIS moment. A refusal here is a fact about this request, never "
         "evidence that a family has no Northeast Florida property, and never inherited from an earlier order."),
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
    # routes are asserted on that and are exempt here. Hilton's own Georgia routes carry "kingsland" in the
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
