"""PTF-BANNER-ELK-SUGAR-BEECH-NC-PARALLEL-SOURCE-READY-001 -- Phase 4B: the official destination
lodging rosters (replaces the cloned Explore Boone listing-service reader).

WHAT THIS IS
------------
The Avery County ski towns have no single Simpleview bureau. Their official
destination and resort surfaces are read here, each once, from a plain client,
every document persisted by its own sha256:

  OWNED   Explore Boone (the Boone TDA) listing service, already read and committed
          by the Boone - Blowing Rock build
          (``boone_blowing_rock_nc_destination_roster_001.json``). Its Avery County
          listings are re-read from that committed report at ZERO requests.
  BANNER_ELK_TDA   ``bannerelk.com`` (Banner Elk Tourism Development Authority):
          its own Lodging categories Hotels, Bed & Breakfast Inns, Cabins, Condos
          and Vacation Homes, every index page and every listing page.
  BEECH_MOUNTAIN_TDA  ``beechmtn.com`` (Beech Mountain Visitor Center): its Lodging
          page and every ``/visit/<listing>/`` page it links.
  AVERY_CHAMBER   ``averycounty.com`` (Avery County Chamber of Commerce): its
          Accommodations directory category, every page, every listing.
  HIGH_COUNTRY_HOST  ``highcountryhost.com`` (the High Country regional visitor
          center): its Hotels / Motels / Inns, Bed & Breakfasts / Country Inns and
          Resorts categories; a listing page is read when its own slug names an
          Avery County place (the rest are the live Boone market's or Ashe
          County's, recorded by count).
  SUGAR_MOUNTAIN_RESORT  ``skisugar.com/lodging/``: the resort's own lodging
          partner list (name, phone and website only).

A DESTINATION ROSTER IS DISCOVERY AND IDENTITY EVIDENCE, TIER 2
---------------------------------------------------------------
It is not the property's own page. Its postal codes are carried as
``stated_postal_code`` and never key a building on their own; its phone as
``stated_phone``. The roster's own CATEGORY (cabins, condos, vacation homes,
campgrounds, camps) is recorded verbatim so the census refuses those rows BY
DECISION. Nothing a roster says about pets ("Pet Friendly" features, "NO PETS,
PLEASE!") is read as a policy.

Output:
  launch_packages/pettripfinder/markets/reports/banner_elk_sugar_beech_nc_destination_roster_001.json
  data/acquisition/banner_elk_sugar_beech_nc_destination_001/<sha256>.bin
"""
from __future__ import annotations

import html
import json
import os
import re
import sys
import time
from collections import Counter, OrderedDict
from urllib.parse import urljoin, urlparse

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import banner_elk_sugar_beech_nc_brand_inventory_001 as BI  # noqa: E402

WORK_ORDER = "PTF-BANNER-ELK-SUGAR-BEECH-NC-PARALLEL-SOURCE-READY-001"
MARKET_ID = "banner-elk-sugar-beech-nc"
REPORTS = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports")
OUT = os.path.join(REPORTS, "banner_elk_sugar_beech_nc_destination_roster_001.json")
OWNED_BOONE = os.path.join(REPORTS, "boone_blowing_rock_nc_destination_roster_001.json")
CONFIG = os.path.join(_DASH, "scripts", "pettripfinder", "discovery", "config", "banner_elk_sugar_beech_nc.json")
BI.DOCS = os.path.join(_DASH, "data", "acquisition", "banner_elk_sugar_beech_nc_destination_001")
POLITE_DELAY_SECONDS = 0.5

#: Places the address extractor recognises (the admitted towns and every observed neighbour).
PLACES = ("Banner Elk", "Beech Mountain", "Sugar Mountain", "Seven Devils", "Linville", "Newland", "Elk Park",
          "Pineola", "Montezuma", "Crossnore", "Minneapolis", "Plumtree", "Boone", "Blowing Rock", "Valle Crucis",
          "Vilas", "Foscoe", "Spruce Pine", "Roan Mountain", "Elizabethton", "West Jefferson", "Jefferson",
          "Newland", "Boomer", "Lenoir")
_ADDRESS = re.compile(
    r"(\d{1,6}[A-Za-z]?\s+[^|,]{2,60}?)\s*[,|]\s*(?:\|\s*)?(%s)\s*,?\s*(?:\|\s*)?(NC|TN|North Carolina|Tennessee)\s*,?\s*(\d{5})"
    % "|".join(re.escape(p) for p in PLACES), re.I)
_PHONE = re.compile(r"\(?\b(\d{3})\)?[\s.-]*(\d{3})[\s.-]*(\d{4})\b")
#: Footer addresses of the roster sites themselves, never a listing's own.
_SITE_ADDRESSES = ("6370 us highway 321", "1103 beech mountain parkway unit 2", "4501 tynecastle", "403 beech mountain parkway")
_SOCIAL = re.compile(r"facebook|instagram|twitter|x\.com|youtube|pinterest|linkedin|tiktok|google\.com/maps|"
                     r"maps\.app|constantcontact|vannoppen|appnet|wordpress|gravatar|w3\.org|schema\.org|"
                     r"highcountryhost|bannerelk\.com|bannerelk\.org|townofbannerelk|lmc\.edu|tweetsie|beechmtn\.com|averycounty\.com|skisugar\.com|tripadvisor", re.I)
_ASSET = re.compile(r"fonts\.|cdn\.|cdnjs|jsdelivr|fontawesome|googleapis|gstatic|\.css(?:$|\?)|\.js(?:$|\?)|cloudflare|recaptcha|"
                    r"addtoany|sharethis|mailto:", re.I)
_AVERY_SLUG = re.compile(r"banner|beech|sugar|linville|newland|elk-park|seven-devils|pineola|grandfather|avery", re.I)


def _plain(body):
    t = re.sub(r"<script.*?</script>|<style.*?</style>|<noscript.*?</noscript>", " ", body, flags=re.S | re.I)
    t = html.unescape(re.sub(r"<[^>]+>", "\n", t)).replace(" ", " ")
    return re.sub(r"\s*\n\s*", " | ", t)


def _title(body):
    m = re.search(r"<h1[^>]*>(.*?)</h1>", body, re.S | re.I)
    name = html.unescape(re.sub(r"<[^>]+>", " ", m.group(1))).strip() if m else ""
    if not name:
        m = re.search(r"<title[^>]*>(.*?)</title>", body, re.S | re.I)
        name = html.unescape(m.group(1)).split("|")[0].split(" - ")[0].strip() if m else ""
    return " ".join(name.split())


def extract_listing(url, body, source):
    text = _plain(body)
    addr = None
    for m in _ADDRESS.finditer(text):
        street = " ".join(m.group(1).replace("|", " ").split())
        if any(s in street.lower() for s in _SITE_ADDRESSES):
            continue
        addr = (street, m.group(2).title(), m.group(3), m.group(4))
        break
    phone = _PHONE.search(text)
    host = urlparse(url).netloc
    website = ""
    # The listing's OWN website: an anchor the roster labels as the website, else an external link whose
    # host shares a distinctive word with the listing's name. Never the roster's navigation or a sponsor.
    name_words = {w for w in re.findall(r"[a-z0-9]{4,}", _title(body).lower())
                  if w not in ("inn", "lodge", "hotel", "suites", "resort", "mountain", "banner", "beech", "sugar",
                               "the", "and")}
    anchors = re.findall(r"<a\s[^>]*?href=[\"'](https?://[^\"'#]+)[\"'][^>]*>(.*?)</a>", body, re.I | re.S)
    candidates = [(href.strip(), re.sub(r"<[^>]+>", " ", label)) for href, label in anchors
                  if urlparse(href).netloc != host and not _SOCIAL.search(href) and not _ASSET.search(href)]
    labelled = [h for h, label in candidates if re.search(r"website|visit\s+site|book\s+now", label, re.I)]
    named = [h for h, _label in candidates if any(w in urlparse(h).netloc.lower() for w in name_words)]
    if labelled or named:
        website = (labelled or named)[0].split("?")[0].replace("%20", "").strip()
    return OrderedDict([
        ("name", _title(body)),
        ("street", addr[0] if addr else ""), ("city", addr[1] if addr else ""),
        ("region", "NC" if not addr or addr[2].upper() in ("NC", "NORTH CAROLINA") else "TN"),
        ("stated_postal_code", addr[3] if addr else ""),
        ("stated_phone", "%s-%s-%s" % phone.groups() if phone else ""),
        ("website", website),
    ])


class Reader(object):
    def __init__(self):
        self.stats = BI.Stats()
        self.documents = []

    def get(self, url):
        time.sleep(POLITE_DELAY_SECONDS)
        row, body = BI.fetch(url, self.stats, timeout=40)
        self.documents.append(OrderedDict((k, row[k]) for k in ("url", "status", "final_url", "bytes", "sha256",
                                                                   "error", "fetched_at")))
        return row, body.decode("utf-8", "replace")


def banner_elk_tda(rd):
    base = "https://www.bannerelk.com/attractions/%s/"
    cats = OrderedDict([("hotels", "Hotels"), ("bed-breakfast-inns", "Bed & Breakfast Inns"), ("cabins", "Cabins"),
                        ("condos", "Condos"), ("vacation-homes", "Vacation Homes")])
    skip = {"/attractions/%s/" % c for c in ("attractions", "festivals-events", "lodging", "museums-the-arts",
                                             "outdoor-adventure", "restaurants", "shopping", "skiing-winter-sports",
                                             "spas-wellness", "wineries-breweries")} | {"/attractions/"}
    skip |= {"/attractions/%s/" % c for c in cats}
    found = OrderedDict()
    for slug, label in cats.items():
        page, seen_pages = 1, set()
        while page and page not in seen_pages and page <= 12:
            seen_pages.add(page)
            url = base % slug + ("?page=%d" % page if page > 1 else "")
            _row, text = rd.get(url)
            for href in re.findall(r"href=\"(/attractions/[a-z0-9-]+/)\"", text):
                if href not in skip:
                    found.setdefault(href, set()).add(label)
            pages = sorted({int(p) for p in re.findall(r"\?page=(\d+)", text)})
            page = next((p for p in pages if p > page), None)
    out = []
    for href, labels in found.items():
        url = urljoin("https://www.bannerelk.com", href)
        row, text = rd.get(url)
        rec = extract_listing(url, text, "BANNER_ELK_TDA")
        out.append((url, row, rec, sorted(labels)))
    return out


def beech_mountain_tda(rd):
    _row, text = rd.get("https://beechmtn.com/lodging/")
    out = []
    for url in sorted(set(re.findall(r"href=\"(https://beechmtn\.com/visit/[a-z0-9-]+/)\"", text))):
        row, body = rd.get(url)
        out.append((url, row, extract_listing(url, body, "BEECH_MOUNTAIN_TDA"), ["Lodging"]))
    return out


def avery_chamber(rd):
    found, url = OrderedDict(), "https://averycounty.com/single-category/accommodations/"
    walked = set()
    while url and url not in walked and len(walked) < 8:
        walked.add(url)
        _row, text = rd.get(url)
        for u in re.findall(r"href=\"(https://averycounty\.com/directory/[a-z0-9-]+/)\"", text):
            found.setdefault(u, True)
        nxt = sorted(set(re.findall(r"href=\"(https://averycounty\.com/single-category/accommodations/page/\d+/)\"", text)))
        url = next((n for n in nxt if n not in walked), None)
    out = []
    for u in found:
        row, body = rd.get(u)
        out.append((u, row, extract_listing(u, body, "AVERY_CHAMBER"), ["Accommodations"]))
    return out


def high_country_host(rd):
    cats = OrderedDict([("hotels-motels-and-inns", "Hotels, Motels and Inns"),
                        ("bed-breakfasts-and-country-inns", "Bed & Breakfasts and Country Inns"),
                        ("resorts", "Resorts")])
    out, not_read = [], Counter()
    for slug, label in cats.items():
        _row, text = rd.get("https://www.highcountryhost.com/lodging/%s" % slug)
        for u in sorted(set(re.findall(r"href=\"(https://www\.highcountryhost\.com/lodging/%s/[^\"#/]+)\"" % slug, text))):
            if not _AVERY_SLUG.search(u.rsplit("/", 1)[-1]):
                not_read[label] += 1
                continue
            row, body = rd.get(u)
            out.append((u, row, extract_listing(u, body, "HIGH_COUNTRY_HOST"), [label]))
    return out, not_read


def sugar_mountain_resort(rd):
    url = "https://skisugar.com/lodging/"
    row, text = rd.get(url)
    plain = _plain(text)
    out = []
    start = plain.find("| Lodging |", plain.find("Privacy Policy"))
    body = plain[start:]
    for m in re.finditer(r"\|\s*([^|]{3,80}?)\s*\|\s*\[ Visit Their Website \]\s*\|\s*([\d\-() .]{10,16})", body):
        name = m.group(1).strip()
        seg_start = text.find(html.escape(name).replace("&#x27;", "&#8217;")[:20])
        website = ""
        if seg_start >= 0:
            w = re.search(r"href=\"(https?://[^\"]+)\"", text[seg_start:seg_start + 1500])
            website = w.group(1) if w else ""
        out.append((url, row, OrderedDict([("name", name), ("street", ""), ("city", ""), ("region", "NC"),
                                           ("stated_postal_code", ""), ("stated_phone", m.group(2).strip()),
                                           ("website", website)]), ["Lodging partner"]))
    return out


def owned_explore_boone():
    doc = json.load(open(OWNED_BOONE, encoding="utf-8"))
    box = json.load(open(CONFIG, encoding="utf-8"))["geographic_bounds"]
    avery = {"28604", "28646", "28653", "28662", "28657", "28622", "28616", "28652", "28664"}
    out = []
    for l in doc["listings"]:
        inside = False
        try:
            inside = (box["min_lat"] <= float(l.get("lat")) <= box["max_lat"]
                      and box["min_lng"] <= float(l.get("lng")) <= box["max_lng"])
        except (TypeError, ValueError):
            pass
        if l.get("stated_postal_code") in avery or inside:
            out.append(l)
    return out, doc


def build():
    rd = Reader()
    listings = []

    def add(source, source_label, rows):
        for url, row, rec, labels in rows:
            if not rec["name"]:
                continue
            listings.append(OrderedDict([
                ("listing_url", url), ("source", source), ("source_label", source_label),
                ("status", row["status"]), ("document_sha256", row["sha256"]), ("document_bytes", row["bytes"]),
                ("fetched_at", row["fetched_at"]),
                ("bureau_category", "Lodging"),
                ("bureau_subcategory", labels[0] if labels else ""),
                ("bureau_all_subcategories", labels),
                ("name", rec["name"]), ("street", rec["street"]), ("city", rec["city"]), ("region", rec["region"]),
                ("stated_postal_code", rec["stated_postal_code"]), ("stated_phone", rec["stated_phone"]),
                ("lat", None), ("lng", None), ("website", rec["website"]),
            ]))

    owned, owned_doc = owned_explore_boone()
    for l in owned:
        l = OrderedDict(l)
        l["source"] = "EXPLORE_BOONE_OWNED"
        l["source_label"] = "Explore Boone (Boone TDA) listing service, owned from the Boone - Blowing Rock build"
        listings.append(l)
    add("BANNER_ELK_TDA", "bannerelk.com (Banner Elk TDA) lodging categories", banner_elk_tda(rd))
    add("BEECH_MOUNTAIN_TDA", "beechmtn.com (Beech Mountain Visitor Center) lodging", beech_mountain_tda(rd))
    add("AVERY_CHAMBER", "averycounty.com (Avery County Chamber) Accommodations directory", avery_chamber(rd))
    hch, hch_not_read = high_country_host(rd)
    add("HIGH_COUNTRY_HOST", "highcountryhost.com (High Country regional visitor center) lodging", hch)
    add("SUGAR_MOUNTAIN_RESORT", "skisugar.com (Sugar Mountain Resort) lodging partners", sugar_mountain_resort(rd))

    listings.sort(key=lambda r: (r["source"], r["name"].lower(), r["listing_url"]))
    return OrderedDict([
        ("schema", "ptf-destination-roster/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "4B -- the official Avery County destination and resort lodging rosters"),
        ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
        ("source", "bannerelk.com, beechmtn.com, averycounty.com, highcountryhost.com, skisugar.com (plain client, "
                   "one read per document) and the committed Explore Boone roster (owned, zero requests)"),
        ("owned_rows_reused", OrderedDict([("source", os.path.relpath(OWNED_BOONE, _DASH).replace("\\", "/")),
                                           ("as_of", owned_doc.get("as_of")), ("rows", len(owned)),
                                           ("free_http_requests", 0)])),
        ("high_country_host_listings_not_read_by_category", OrderedDict(sorted(hch_not_read.items()))),
        ("high_country_host_rule",
         "a regional roster listing is read only when its own slug names an Avery County place; the others are "
         "Boone / Blowing Rock / Ashe County listings the live Boone market already holds"),
        ("documents", rd.documents),
        ("polite_delay_seconds", POLITE_DELAY_SECONDS),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("free_http_requests", rd.stats.requests),
        ("tier", "2 -- destination organisation: discovery and identity evidence, never policy"),
        ("an_amenity_word_is_not_a_policy",
         "Nothing a roster publishes about pets is read; the roster is identity evidence only."),
        ("listing_count", len(listings)),
        ("listings_by_source", OrderedDict(sorted(Counter(l["source"] for l in listings).items()))),
        ("lodging_by_subcategory", OrderedDict(sorted(Counter(l["bureau_subcategory"] or "" for l in listings).items()))),
        ("unreadable_documents", [d for d in rd.documents if d["status"] != 200]),
        ("listings", listings),
    ])


def main():
    doc = build()
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("listings:", doc["listing_count"], dict(doc["listings_by_source"]))
    print("by subcategory:", dict(doc["lodging_by_subcategory"]))
    print("requests:", doc["free_http_requests"], "unreadable:", len(doc["unreadable_documents"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
