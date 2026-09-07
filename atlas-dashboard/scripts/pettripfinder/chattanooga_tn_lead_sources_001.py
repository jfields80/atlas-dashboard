"""PTF-CHATTANOOGA-TN-NEW-MARKET-001 -- Phases 3, 4C and 4D: the free lead lanes.

Five zero-cost sources, in the ladder's own order, each read first-party and
each treated as an IDENTITY lead rather than authority:

* rank 0, OWNED_EVIDENCE -- the committed Dayton brand-directory harvest
  (``dayton_oh_brand_directory_harvest_001.json``) already holds Marriott's whole
  published roster and the Cincinnati brand-inventory audit already holds
  Sonesta's Tennessee slice. Both are read from disk. Zero requests.
* rank 1, LOCAL_FREE_DISCOVERY -- the official Chattanooga Tourism Co. roster at
  ``visitchattanooga.com``, Hilton's own Chattanooga city page, Wyndham's
  published per-brand property sitemaps, and the Drury / Sonesta / WoodSpring
  city pages.

WHAT A LEAD IS
--------------
A row here proposes that a lodging identity EXISTS and states the address that
identity's own source printed. It never decides market membership, never names a
pet policy and never publishes. The Tennessee/Georgia border is decided in
Phase 6 against the address, never against a page that markets itself as
"Chattanooga".

FOUR TRAPS THIS RUN CHECKS RATHER THAN ASSUMES
----------------------------------------------
1. **A property-code prefix SELECTS, the page ADMITS.** Marriott's ``cha`` prefix
   and Hilton's ``cha`` CTYHOCN prefix both reach Cleveland TN, Dalton GA,
   Calhoun GA, Ellijay GA and Rome GA. Every code is carried with the address its
   own source states, and the address decides.
2. **A locality token is not an identity.** ``ewrrb-courtyard-lincroft-red-bank``
   is Red Bank, NEW JERSEY, and Chattanooga has a Red Bank too. Rejected on the
   airport-code prefix its own URL carries.
3. **A non-en-us locale is normalised, never dropped.** Marriott publishes some
   properties only under ``/en-gb/``; the row is kept and the locale rewritten.
4. **A destination bureau's amenity flag is not a policy.** The Chattanooga
   Tourism Co. listing payload carries an accessibility amenity reading "Service
   Dogs Allowable in the Building". That is a service-animal statement on an
   accessibility tab. It is recorded as a NON_POLICY_SIGNAL and can never reach
   the policy lane.

The bureau's own website button is a click-counting redirect under
``/plugins/crm/count/``, which its robots.txt disallows. This run does not fetch
it, so -- unlike Toledo -- the bureau is an IDENTITY lane here and not a routing
lane. Its crawl-delay of 2 seconds is honoured.

No paid provider is called. Output is Chattanooga-local.

Output:
  launch_packages/pettripfinder/markets/reports/chattanooga_tn_lead_sources_001.json
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
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-CHATTANOOGA-TN-NEW-MARKET-001"
MARKET_ID = "chattanooga-tn"
SCHEMA = "ptf-market-lead-sources/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CACHE = os.path.join(_DASH, "data", "discovery", "chattanooga_tn_lead_sources_001")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/128.0 Safari/537.36")

#: The Chattanooga Tourism Co. publishes ``Crawl-delay: 2``. Honoured.
CVB_SPACING = 2.1
BRAND_SPACING = 1.2

CVB_SITEMAP = "https://www.visitchattanooga.com/sitemap.xml"
CVB_ROBOTS = "https://www.visitchattanooga.com/robots.txt"
#: Category hubs read for completeness: a slug pattern can miss an independent
#: whose name carries no lodging word ("The Read House", "The Chattanoogan").
CVB_HUBS = [
    "https://www.visitchattanooga.com/hotels/",
    "https://www.visitchattanooga.com/hotels/downtown/",
    "https://www.visitchattanooga.com/hotels/near-airport/",
    "https://www.visitchattanooga.com/hotels/near-lookout-mountain/",
    "https://www.visitchattanooga.com/hotels/bed-and-breakfasts/",
]

HILTON_CITY = "https://www.hilton.com/en/locations/usa/tennessee/chattanooga/"
WYNDHAM_SITEMAP_INDEX = "https://www.wyndhamhotels.com/sitemap.xml"
DRURY_CITY = "https://www.druryhotels.com/locations/chattanooga-tn"
SONESTA_CITY = "https://www.sonesta.com/locations/us/tennessee/chattanooga"
WOODSPRING_CITY = ("https://www.woodspring.com/extended-stay-hotels/locations/"
                   "tennessee/chattanooga/hotels")

#: Families whose own site refused a plain first-party client on this run. A
#: refusal is recorded with its status so the Firecrawl rung has a measured
#: reason, and so the next order re-probes rather than assuming.
REFUSAL_PROBES = [
    ("IHG", "https://www.ihg.com/services/sitemaps/sitemap-index.xml"),
    ("CHOICE", "https://www.choicehotels.com/sitemapindex.xml"),
    ("RED_ROOF", "https://www.redroof.com/sitemap.xml"),
    ("ESA", "https://www.extendedstayamerica.com/hotels/tn/chattanooga"),
    ("BEST_WESTERN", "https://www.bestwestern.com/en_US/book/hotels-in-chattanooga/"),
    ("HYATT", "https://www.hyatt.com/explore-hotels/destinations/united-states/chattanooga"),
]

OWNED_HARVEST = os.path.join(REPORTS, "dayton_oh_brand_directory_harvest_001.json")
OWNED_CINCY_AUDIT = os.path.join(REPORTS, "cincinnati_oh_brand_inventory_audit_002.json")

#: Places a Chattanooga-area lead may name. Deliberately generous: this selects a
#: LEAD, and the address on the source's own page admits or rejects it.
AREA_TOKENS = (
    "chattanooga", "hixson", "ooltewah", "east ridge", "east-ridge", "eastridge",
    "collegedale", "apison", "harrison", "red bank", "red-bank", "signal mountain",
    "signal-mountain", "soddy", "lookout mountain", "lookout-mountain", "lookout",
    "tiftonia", "brainerd", "hamilton place", "hamilton-place", "lakesite", "walden",
    "ridgeside", "lupton",
)
#: Georgia places just over the state line. Fetched on purpose so the border audit
#: has rows to rule on rather than a silent gap.
GA_FRINGE_TOKENS = ("fort oglethorpe", "fort-oglethorpe", "ft-oglethorpe", "ft oglethorpe",
                    "ringgold", "rossville", "chickamauga", "lafayette-ga", "catoosa")

#: A slug that reads like lodging. Generous on purpose; the listing page's own
#: schema.org @type and address decide what it is.
_LODGING_SLUG = re.compile(
    r"(hotel|motel|-inn|inn-|^inn|suites|lodge|resort|hostel|bed-and-breakfast|b-and-b"
    r"|extended-stay|homewood|hampton|marriott|hilton|hyatt|sheraton|westin|renaissance"
    r"|courtyard|residence|towneplace|springhill|fairfield|doubletree|embassy|candlewood"
    r"|staybridge|holiday|crowne|radisson|ramada|baymont|wyndham|super-8|days-|quality"
    r"|comfort|sleep-|clarion|econo|travelodge|howard-johnson|red-roof|motel-6|studio"
    r"|woodspring|sonesta|drury|best-western|la-quinta|home2|tru-|element-|aloft|moxy"
    r"|edwin|dwell|kinley|chattanoogan|read-house|choo-choo|clemons|mainstay|microtel"
    r"|knights|douglas|chanticleer|mayors-mansion|garden-walk|riverside|treehouse"
    r"|guesthouse|guest-house|cottage|cabin|campground|rv-park|rv-resort|caption)", re.I)
#: Slugs the pattern above catches that are NOT a lodging property: a hotel's
#: restaurant, a hotel's meeting-information stub, a management company.
_NOT_LODGING_SLUG = re.compile(
    r"(meeting[s]?-information|meeting-venue|-at-the-|\(the-|%28the-|bar-moxy|marketplace-by"
    r"|property-management|management-company|chamber|convention-and-visitors|realty"
    r"|relocation|construction|supply|laundry|linen|staffing|insurance|marketing"
    r"|design-group|factory-store|museum|conservancy|outfitters|rafting|paragliding"
    r"|sign-services|print-services|escape-experience|arena|sports-complex|park/"
    r"|steak-house|innovate|preserve-chattanooga|institute)", re.I)


# --------------------------------------------------------------------------- io

def _get(url, timeout=30):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Encoding": "gzip", "Accept-Language": "en-US,en;q=0.9"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read()
            if r.headers.get("Content-Encoding") == "gzip" or data[:2] == b"\x1f\x8b":
                try:
                    data = gzip.GzipFile(fileobj=io.BytesIO(data)).read()
                except Exception:  # noqa: BLE001
                    pass
            return r.status, r.geturl(), data
    except urllib.error.HTTPError as e:
        return e.code, url, b""
    except Exception as e:  # noqa: BLE001
        return "ERR:" + type(e).__name__, url, b""


def cached_get(url, stats, spacing=BRAND_SPACING):
    """One HTTPS GET, cached on disk by URL. Every fetch keeps its own provenance."""
    os.makedirs(CACHE, exist_ok=True)
    key = hashlib.sha256(url.encode("utf-8")).hexdigest()
    meta_path = os.path.join(CACHE, key + ".json")
    body_path = os.path.join(CACHE, key + ".bin")
    if os.path.exists(meta_path):
        meta = json.load(open(meta_path, encoding="utf-8"))
        body = open(body_path, "rb").read() if os.path.exists(body_path) else b""
        return meta, body
    time.sleep(spacing)
    st, final, body = _get(url)
    stats["free_http_requests"] += 1
    stats["status"][str(st)] += 1
    meta = OrderedDict([
        ("requested_url", url), ("status", st), ("final_url", final),
        ("bytes", len(body)),
        ("sha256", hashlib.sha256(body).hexdigest() if body else ""),
        ("fetched_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
    ])
    if body:
        open(body_path, "wb").write(body)
    json.dump(meta, open(meta_path, "w", encoding="utf-8"))
    return meta, body


def _text(body):
    return body.decode("utf-8", "replace") if body else ""


_LOC = re.compile(r"<loc>\s*(.*?)\s*</loc>", re.S | re.I)
_LD = re.compile(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', re.S | re.I)
_NEXT_DATA = re.compile(r'id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)


def _lead(source, family, name, street, city, region, postal, phone,
          lat, lng, url, property_code, note=""):
    return OrderedDict([
        ("source", source), ("family", family), ("name", (name or "").strip()),
        ("street", (street or "").strip()), ("city", (city or "").strip()),
        ("region", (region or "").strip()), ("postal_code", (postal or "").strip()),
        ("phone", (phone or "").strip()),
        ("latitude", lat), ("longitude", lng),
        ("source_url", url), ("property_code", (property_code or "").strip().lower()),
        ("note", note),
    ])


def _area_hit(*fields):
    blob = " ".join(str(f or "") for f in fields).lower()
    return any(t in blob for t in AREA_TOKENS) or any(t in blob for t in GA_FRINGE_TOKENS)


# ------------------------------------------------------------------ rank 0, owned

def owned_evidence():
    """Chattanooga-area rows already committed to this repository. Zero requests."""
    out, files = [], []
    if os.path.exists(OWNED_HARVEST):
        files.append(os.path.relpath(OWNED_HARVEST, _DASH).replace("\\", "/"))
        doc = json.load(open(OWNED_HARVEST, encoding="utf-8"))
        seen = {}
        for family, block in (doc.get("families") or {}).items():
            for url in block.get("property_urls") or []:
                m = re.search(r"/hotels/([a-z0-9]{5})-([a-z0-9\-]+)", url.lower())
                if not m or family != "MARRIOTT":
                    continue
                code, slug = m.group(1), m.group(2)
                if not code.startswith("cha"):
                    continue
                # Trap 3: normalise a non-en-us locale rather than dropping the row.
                canonical = re.sub(r"/en-[a-z]{2}/", "/en-us/", url.split("/overview")[0]) + "/"
                seen.setdefault(code, (slug, canonical))
        for code, (slug, url) in sorted(seen.items()):
            out.append(_lead(
                "OWNED_DAYTON_BRAND_HARVEST", "MARRIOTT",
                slug.replace("-", " ").title(), "", "", "", "", "", None, None,
                url, code,
                "Marriott code prefix 'cha' is REGIONAL: it reaches Cleveland TN, Dalton GA, "
                "Calhoun GA, Ellijay GA and Rome GA as well as Chattanooga. The code selects; "
                "the property page's own address admits."))
    if os.path.exists(OWNED_CINCY_AUDIT):
        files.append(os.path.relpath(OWNED_CINCY_AUDIT, _DASH).replace("\\", "/"))
        blob = json.dumps(json.load(open(OWNED_CINCY_AUDIT, encoding="utf-8")))
        for url in sorted(set(re.findall(
                r'"(https://www\.sonesta\.com/[^"]*?(?:tn|tennessee)/[^"]*?chattanooga[^"]*)"',
                blob, re.I))):
            slug = url.rstrip("/").rsplit("/", 1)[-1]
            out.append(_lead(
                "OWNED_CINCINNATI_BRAND_AUDIT", "SONESTA",
                slug.replace("-", " ").title(), "", "Chattanooga", "TN", "", "",
                None, None, url, slug,
                "Recorded by the Cincinnati audit as an out-of-market row; a lead here."))
    return out, files


# ------------------------------------------------- rank 1, the destination bureau

def cvb_roster(stats):
    """The Chattanooga Tourism Co.'s own published listing roster."""
    meta, body = cached_get(CVB_ROBOTS, stats, CVB_SPACING)
    robots = _text(body)
    meta, body = cached_get(CVB_SITEMAP, stats, CVB_SPACING)
    locs = sorted(set(_LOC.findall(_text(body))))
    listings = [u for u in locs if "/listing/" in u]
    leads, considered, hub_only = [], [], []

    # Category hubs first: a hub row that the slug filter would have missed is a
    # real gap, and this run reports it rather than absorbing it silently.
    hub_slugs = set()
    for hub in CVB_HUBS:
        m, b = cached_get(hub, stats, CVB_SPACING)
        hub_slugs.update(re.findall(r'href="/listing/([^"/]+/\d+)/"', _text(b)))

    selected = []
    for url in listings:
        slug = url.split("/listing/")[-1].rstrip("/")
        if _NOT_LODGING_SLUG.search(slug):
            continue
        if _LODGING_SLUG.search(slug) or slug in hub_slugs:
            selected.append(url)
            if slug in hub_slugs and not _LODGING_SLUG.search(slug):
                hub_only.append(slug)
    selected = sorted(set(selected))

    for url in selected:
        m, b = cached_get(url, stats, CVB_SPACING)
        html = _text(b)
        considered.append(url)
        if m["status"] != 200 or not html:
            continue
        for raw in _LD.finditer(html):
            try:
                doc = json.loads(raw.group(1).strip())
            except Exception:  # noqa: BLE001
                continue
            for d in (doc if isinstance(doc, list) else [doc]):
                if not isinstance(d, dict):
                    continue
                atype = str(d.get("@type") or "")
                if atype not in ("Hotel", "Motel", "BedAndBreakfast", "Resort",
                                 "LodgingBusiness", "Hostel", "Campground",
                                 "ExtendedStayHotel"):
                    continue
                addr = d.get("address") if isinstance(d.get("address"), dict) else {}
                geo = d.get("geo") if isinstance(d.get("geo"), dict) else {}
                leads.append(_lead(
                    "CVB_VISIT_CHATTANOOGA", "", d.get("name"),
                    addr.get("streetAddress"), addr.get("addressLocality"),
                    addr.get("addressRegion"), addr.get("postalCode"),
                    d.get("telephone"), geo.get("latitude"), geo.get("longitude"),
                    url, "", "schema.org @type=%s on the bureau's own listing page" % atype))
    return OrderedDict([
        ("robots_crawl_delay_honoured", "Crawl-delay: 2" in robots),
        ("sitemap_locs", len(locs)),
        ("listing_pages_published", len(listings)),
        ("listing_pages_selected", len(selected)),
        ("listing_pages_fetched", len(considered)),
        ("selected_only_by_a_category_hub", sorted(hub_only)),
        ("website_button_lane", "NOT_FETCHED -- the bureau's Visit Website button is a "
                                "/plugins/crm/count/ click redirect, which its own robots.txt "
                                "disallows. The bureau is an IDENTITY lane here, not a routing "
                                "lane."),
        ("amenity_lane", "NON_POLICY_SIGNAL -- the listing payload's accessibility tab carries "
                         "'Service Dogs Allowable in the Building'. A service-animal statement "
                         "is not ordinary-pet acceptance and never reaches the policy lane."),
        ("leads", leads),
    ])


# ------------------------------------------------------------- rank 1, the brands

def hilton_city_page(stats):
    meta, body = cached_get(HILTON_CITY, stats)
    html = _text(body)
    leads = []
    # Hilton's canonical property route is /en/hotels/<ctyhocn>-<slug>/. A route
    # built from the code ALONE is the Detroit PASS-008 failure class: the
    # property-code parser reads nothing from it and every row is reported
    # PROPERTY_CODE_UNPARSEABLE_ROUTING_REPAIR_REQUIRED. The slug is published
    # on this same page, in the hotel cards' own links.
    slugs = {}
    for full in set(re.findall(r"/en/hotels/([a-z0-9]{5,9}-[a-z0-9-]+)/", html, re.I)):
        slugs[full.split("-", 1)[0].lower()] = full.lower()
    m = _NEXT_DATA.search(html)
    if m:
        try:
            doc = json.loads(m.group(1))
        except Exception:  # noqa: BLE001
            doc = None
        rows, seen = [], set()

        def walk(o):
            if isinstance(o, dict):
                for k, v in o.items():
                    if k == "hotels" and isinstance(v, list):
                        rows.extend(x for x in v if isinstance(x, dict))
                    else:
                        walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
        walk(doc)
        for row in rows:
            code = str(row.get("ctyhocn") or "").lower()
            if not code or code in seen:
                continue
            seen.add(code)
            addr = row.get("address") if isinstance(row.get("address"), dict) else {}
            contact = row.get("contactInfo") if isinstance(row.get("contactInfo"), dict) else {}
            leads.append(_lead(
                "HILTON_CITY_PAGE", "HILTON", row.get("name"),
                addr.get("addressLine1") or addr.get("addressLine"),
                addr.get("city"), addr.get("state") or addr.get("stateCode"),
                addr.get("postalCode"), contact.get("phoneNumber"),
                None, None,
                "https://www.hilton.com/en/hotels/%s/" % slugs.get(code, code), code,
                "Hilton's CTYHOCN 'cha' prefix is REGIONAL; the address on Hilton's own row "
                "admits or rejects the property. The route carries the code AND the slug "
                "Hilton itself publishes, because a code-only route is unparseable to the "
                "property-code parser (the Detroit PASS-008 failure class)."))
    return OrderedDict([("requested_url", HILTON_CITY), ("status", meta["status"]),
                        ("sha256", meta["sha256"]),
                        ("codes_with_a_published_slug", len(slugs)),
                        ("leads", leads)])


#: The city-state segment Wyndham's own canonical URL carries, for the towns
#: this market and its Georgia fringe actually contain. This is a STRUCTURED
#: field in the brand's location taxonomy, and it is what selects a row.
#:
#: A loose token match over the whole US roster does NOT work here, and this
#: run measured why: "harrison" reached Harrison OHIO, Harrison ARKANSAS,
#: Harrisonburg VIRGINIA, Harrisonville MISSOURI and Harrison Hot Springs
#: BRITISH COLUMBIA; "brainerd" reached Baxter, MINNESOTA; "catoosa" reached
#: Catoosa, OKLAHOMA; and "walden" reached Beaumont, TEXAS. A locality token is
#: not an identity.
_WYNDHAM_CITY_SEGMENTS = {
    "chattanooga-tennessee", "east-ridge-tennessee", "hixson-tennessee",
    "ooltewah-tennessee", "collegedale-tennessee", "red-bank-tennessee",
    "soddy-daisy-tennessee", "harrison-tennessee", "signal-mountain-tennessee",
    "apison-tennessee", "lookout-mountain-tennessee", "lakesite-tennessee",
    # the Georgia fringe, fetched on purpose so the border audit can rule on it
    "fort-oglethorpe-georgia", "ringgold-georgia", "rossville-georgia",
    "chickamauga-georgia", "lookout-mountain-georgia",
}


def wyndham_sitemaps(stats, max_children=40):
    """Wyndham publishes one property sitemap per brand. Free, and it walks the wall."""
    meta, body = cached_get(WYNDHAM_SITEMAP_INDEX, stats)
    children = [u for u in _LOC.findall(_text(body))
                if "_en-us_" in u and "_properties_" in u]
    leads, fetched, seen = [], [], set()
    for child in children[:max_children]:
        m, b = cached_get(child, stats)
        fetched.append(child)
        for url in _LOC.findall(_text(b)):
            low = url.lower()
            parts = [p for p in low.split("/") if p]
            city_state = next((p for p in parts if p in _WYNDHAM_CITY_SEGMENTS), "")
            if not city_state:
                continue
            # One row per property: Wyndham publishes /overview, /rooms-rates and
            # more for the same building.
            if parts[-1] != "overview":
                continue
            city = city_state.rsplit("-", 1)[0].replace("-", " ").title()
            region = "TN" if city_state.endswith("-tennessee") else "GA"
            slug = parts[-2]
            if slug in seen:
                continue
            seen.add(slug)
            leads.append(_lead(
                "WYNDHAM_BRAND_SITEMAP", "WYNDHAM", slug.replace("-", " ").title(),
                "", city, region, "", "", None, None,
                url if url.startswith("http") else "https://www.wyndhamhotels.com" + url,
                slug, "Route from Wyndham's own published per-brand property sitemap; the row is "
                      "selected by the city-state segment of the brand's OWN canonical URL, not "
                      "by a token anywhere in it."))
    return OrderedDict([("sitemap_index", WYNDHAM_SITEMAP_INDEX),
                        ("status", meta["status"]),
                        ("en_us_property_children_published", len(children)),
                        ("children_fetched", len(fetched)),
                        ("selection_rule",
                         "the city-state segment of Wyndham's own canonical URL, against a "
                         "committed list of this market's towns and its Georgia fringe. A loose "
                         "token match over the US roster reached Harrison OHIO, Harrison "
                         "ARKANSAS, Baxter MINNESOTA (Brainerd), Catoosa OKLAHOMA and Beaumont "
                         "TEXAS (Walden) on this run's own data."),
                        ("leads", leads)])


def _ld_lodging(html, url, source, family):
    out = []
    for raw in _LD.finditer(html):
        try:
            doc = json.loads(raw.group(1).strip())
        except Exception:  # noqa: BLE001
            continue
        for d in (doc if isinstance(doc, list) else [doc]):
            if not isinstance(d, dict):
                continue
            if str(d.get("@type") or "") not in ("Hotel", "Motel", "LodgingBusiness",
                                                 "Resort", "ExtendedStayHotel"):
                continue
            addr = d.get("address") if isinstance(d.get("address"), dict) else {}
            geo = d.get("geo") if isinstance(d.get("geo"), dict) else {}
            out.append(_lead(source, family, d.get("name"), addr.get("streetAddress"),
                             addr.get("addressLocality"), addr.get("addressRegion"),
                             addr.get("postalCode"), d.get("telephone"),
                             geo.get("latitude"), geo.get("longitude"),
                             str(d.get("url") or url), "", "schema.org on the brand's own page"))
    return out


def simple_city_page(stats, url, source, family, href_pattern):
    meta, body = cached_get(url, stats)
    html = _text(body)
    leads = _ld_lodging(html, url, source, family)
    if not leads and href_pattern:
        for href in sorted(set(re.findall(href_pattern, html, re.I))):
            full = href if href.startswith("http") else url.split("/", 3)[0] + "//" + \
                url.split("/", 3)[2] + href
            slug = full.rstrip("/").rsplit("/", 1)[-1]
            if not _area_hit(full):
                continue
            leads.append(_lead(source, family, slug.replace("-", " ").title(),
                               "", "", "", "", "", None, None, full, slug,
                               "Route from the brand's own city page link list."))
    return OrderedDict([("requested_url", url), ("status", meta["status"]),
                        ("sha256", meta["sha256"]), ("leads", leads)])


def refusal_probes(stats):
    rows = []
    for family, url in REFUSAL_PROBES:
        meta, _ = cached_get(url, stats)
        rows.append(OrderedDict([
            ("family", family), ("requested_url", url), ("status", meta["status"]),
            ("outcome", "SERVED" if meta["status"] == 200 else "REFUSED_OR_FAILED"),
            ("note", "A refusal is a measured CHANNEL failure and is what makes this family "
                     "eligible for the Firecrawl rung. Re-probe on the next order: refusals "
                     "go stale in days."),
        ]))
    return rows


# ------------------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=os.path.join(
        REPORTS, "chattanooga_tn_lead_sources_001.json"))
    ap.add_argument("--max-wyndham-children", type=int, default=40)
    args = ap.parse_args(argv)

    stats = {"free_http_requests": 0, "status": Counter()}
    owned, owned_files = owned_evidence()
    cvb = cvb_roster(stats)
    hilton = hilton_city_page(stats)
    wyndham = wyndham_sitemaps(stats, args.max_wyndham_children)
    drury = simple_city_page(stats, DRURY_CITY, "DRURY_CITY_PAGE", "DRURY",
                             r'href="(/locations/[a-z0-9\-]+/[a-z0-9\-]+)"')
    sonesta = simple_city_page(stats, SONESTA_CITY, "SONESTA_CITY_PAGE", "SONESTA",
                               r'href="(/[a-z0-9\-]+/tn/[a-z0-9\-]+/[a-z0-9\-]+)"')
    woodspring = simple_city_page(
        stats, WOODSPRING_CITY, "WOODSPRING_CITY_PAGE", "WOODSPRING",
        r'href="(/extended-stay-hotels/locations/tennessee/[a-z0-9\-]+/[a-z0-9\-]+)"')
    refusals = refusal_probes(stats)

    lanes = OrderedDict([
        ("OWNED_EVIDENCE", OrderedDict([("files_read", owned_files),
                                        ("requests", 0), ("leads", owned)])),
        ("CVB_VISIT_CHATTANOOGA", cvb),
        ("HILTON_CITY_PAGE", hilton),
        ("WYNDHAM_BRAND_SITEMAP", wyndham),
        ("DRURY_CITY_PAGE", drury),
        ("SONESTA_CITY_PAGE", sonesta),
        ("WOODSPRING_CITY_PAGE", woodspring),
    ])
    all_leads = []
    for name, block in lanes.items():
        all_leads.extend(block.get("leads") or [])

    document = OrderedDict([
        ("schema", SCHEMA), ("work_order", WORK_ORDER),
        ("phase", "3 / 4C / 4D -- owned evidence and the free lead lanes"),
        ("market_id", MARKET_ID),
        ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
        ("what_this_is", __doc__.strip().splitlines()[0]),
        ("paid_provider_calls", 0), ("usd_spent", 0.0),
        ("firecrawl_credits", 0),
        ("free_http_requests_this_run", stats["free_http_requests"]),
        ("unique_urls_fetched_cumulative", len(
            [n for n in os.listdir(CACHE) if n.endswith(".json")])
            if os.path.isdir(CACHE) else stats["free_http_requests"]),
        ("http_status_counts_this_run", OrderedDict(sorted(stats["status"].items()))),
        ("cache_note",
         "Every fetch is cached on disk under data/discovery/, which is gitignored. A rerun "
         "makes no request and therefore reports zero for this run; the cumulative figure is the "
         "number of distinct URLs this order has fetched in total, and it is the honest cost."),
        ("lanes", lanes),
        ("refusal_probes", refusals),
        ("lead_counts", OrderedDict([
            ("total", len(all_leads)),
            ("by_lane", OrderedDict(sorted(Counter(l["source"] for l in all_leads).items()))),
        ])),
        ("leads", all_leads),
    ])
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(document, fh, indent=1)
        fh.write("\n")
    print("free http requests : %d %s" % (stats["free_http_requests"],
                                          dict(sorted(stats["status"].items()))))
    for name, block in lanes.items():
        print("%-26s : %d leads" % (name, len(block.get("leads") or [])))
    for row in refusals:
        print("refusal probe %-14s : %s %s" % (row["family"], row["status"], row["outcome"]))
    print("total leads        : %d" % len(all_leads))
    print("written            : %s" % os.path.relpath(args.out, _DASH).replace("\\", "/"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
