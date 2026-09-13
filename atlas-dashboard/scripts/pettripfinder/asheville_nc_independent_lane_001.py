"""PTF-ASHEVILLE-NC-NORMAL-PRODUCTION-001 -- Phases 4E + 9: independent and resort first-party lane.

Asheville's downtown boutiques, Biltmore Estate lodging, historic resorts and
Tunnel Road / Patton Avenue motor courts are independents that no brand
inventory lists. This lane reads each property's OWN website with a plain
HTTPS client: the home page, then at most a bounded number of same-site pages
whose link text or path names pets, policies, FAQ or amenities. Every document is
persisted under its own sha256, and every sentence that states something about
pets is kept verbatim with the url and document hash it came from.

A property is SEEDED here only by its own domain (from the map lane's website
tag, or a search result that names the property's own site). A directory,
booking engine or competitor page is never fetched as policy authority.

A sentence found here is a CANDIDATE quote. Whether it is operative evidence is
decided by the clean-authority helper, never by this lane.

No paid provider. No credential.

Outputs:
  launch_packages/pettripfinder/markets/reports/asheville_nc_independent_lane_001.json
  data/acquisition/asheville_nc_independent_001/<sha256>.bin
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
import time
import urllib.parse
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import asheville_nc_brand_inventory_001 as BI  # noqa: E402

WORK_ORDER = "PTF-ASHEVILLE-NC-NORMAL-PRODUCTION-001"
MARKET_ID = "asheville-nc"
REPORTS = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports")
OUT = os.path.join(REPORTS, "asheville_nc_independent_lane_001.json")
DOCS = os.path.join(_DASH, "data", "acquisition", "asheville_nc_independent_001")

#: (seed key, property's own site, how the site was found)
SEEDS = [
    ("omni-grove-park", "https://www.omnihotels.com/hotels/asheville-grove-park", "OSM website tag"),
    ("inn-on-biltmore", "https://www.biltmore.com/stay/the-inn-on-biltmore-estate/", "search result naming the property's own site"),
    ("village-hotel-biltmore", "https://www.biltmore.com/stay/village-hotel-on-biltmore-estate/", "search result naming the property's own site"),
    ("biltmore-faq", "https://www.biltmore.com/faq/", "the estate's own FAQ (pets)"),
    ("haywood-park", "https://www.haywoodpark.com/", "OSM name; own domain probed"),
    ("windsor", "https://www.windsorasheville.com/", "OSM name; own domain probed"),
    ("restoration", "https://therestorationhotel.com/", "OSM website tag"),
    ("artful-way", "https://www.artfulwayhotel.com/", "OSM website tag"),
    ("downtown-inn", "https://www.downtowninnandsuites.com/", "OSM name; own domain probed"),
    ("log-cabin-motor-court", "https://www.cabinlodge.com/", "OSM name; own domain probed"),
    ("mountaineer-inn", "https://www.mountaineerinn.com/", "OSM name; own domain probed"),
    ("in-town-motor-lodge", "https://www.intownmotorlodge.com/", "OSM name; own domain probed"),
    ("mount-vue", "https://www.mountvueasheville.com/", "OSM name; own domain probed"),
    ("thunderbird", "https://www.thunderbirdmotelasheville.com/", "OSM name; own domain probed"),
    ("town-house-motel", "https://www.townhousemotelasheville.com/", "OSM name; own domain probed"),
    ("rock-haven", "https://www.rockhavenmotel.com/", "OSM name; own domain probed"),
    ("asheville-inn", "https://www.theashevilleinn.com/", "OSM name; own domain probed"),
    ("whispering-pines", "https://www.whisperingpinesmotelasheville.com/", "OSM name; own domain probed"),
    ("plantation-motel", "https://www.plantationmotel.com/", "OSM name; own domain probed"),
    ("residences-at-biltmore", "https://www.residencesatbiltmore.com/", "OSM website tag"),
    ("monte-vista", "https://montevistanc.com/", "OSM website tag"),
    ("acorn-motel", "https://www.acornmotelblackmountain.us/", "OSM website tag"),
    ("apple-blossom", "http://appleblossommotel.com/", "OSM website tag"),
    ("carolina-bb", "https://www.carolinabb.com/", "OSM name; own domain probed"),
    ("beaucatcher", "https://www.thebeaucatcher.com/", "OSM name; own domain probed"),
    ("bunn-house", "https://www.bunnhouse.com/", "search result naming the property's own site"),
    ("hotel-arras", "https://www.hotelarras.com/", "brand destination page (IHG Kimpton); own domain probed"),
    ("woodspring", "https://www.woodspring.com/extended-stay-hotels/locations/north-carolina/asheville-brevard/woodspring-suites-asheville", "brand sitemap route"),
    ("esa-kenilworth", "https://www.extendedstayamerica.com/hotels/nc/asheville/tunnel-rd", "OSM name; brand route probed"),
    ("cvb-lodging", "https://www.exploreasheville.com/places-to-stay/hotels/", "official tourism lodging resource (discovery only)"),
]

_LINK = re.compile(r"""<a\b[^>]*href=["']([^"'#]+)["'][^>]*>(.*?)</a>""", re.I | re.S)
_WANT = re.compile(r"pet|dog|polic|faq|amenit|question|rules|info", re.I)
_PET_SENT = re.compile(r"[^.!?\n]{0,260}\b(pets?|dogs?|cats?|animals?|pet[- ]friendly)\b[^.!?\n]{0,260}[.!?]?", re.I)
PAGE_CAP = 6


class Stats(object):
    def __init__(self):
        self.requests = 0
        self.bytes = 0


def text_of(body):
    t = body.decode("utf-8", "replace")
    t = re.sub(r"(?is)<(script|style|noscript)\b.*?</\1>", " ", t)
    t = re.sub(r"(?s)<[^>]+>", " ", t)
    return re.sub(r"\s+", " ", html.unescape(t)).strip()


def read_site(seed, stats):
    key, home, found = seed
    site = OrderedDict([("seed", key), ("home", home), ("seeded_by", found), ("pages", []),
                        ("pet_sentences", [])])
    row, body = BI.fetch(home, stats, timeout=20)
    site["pages"].append(row)
    if not body or (row.get("status") or 0) >= 400:
        site["disposition"] = "SITE_NOT_READ__%s" % (row.get("status") or (row.get("error") or "").split(":")[0])
        return site
    host = urllib.parse.urlparse(row.get("final_url") or home).netloc.lower().replace("www.", "")
    queue = []
    for href, label in _LINK.findall(body.decode("utf-8", "replace")):
        u = urllib.parse.urljoin(row.get("final_url") or home, href.strip())
        p = urllib.parse.urlparse(u)
        if p.scheme not in ("http", "https") or p.netloc.lower().replace("www.", "") != host:
            continue
        if _WANT.search(p.path) or _WANT.search(re.sub(r"<[^>]+>", " ", label)):
            u = u.split("#")[0]
            if u not in queue and u.rstrip("/") != (row.get("final_url") or home).rstrip("/"):
                queue.append(u)
    docs = [(row, body)]
    for u in queue[:PAGE_CAP]:
        r2, b2 = BI.fetch(u, stats, timeout=20)
        site["pages"].append(r2)
        if b2 and (r2.get("status") or 0) < 400:
            docs.append((r2, b2))
    seen = set()
    for r, b in docs:
        for m in _PET_SENT.finditer(text_of(b)):
            s = m.group(0).strip()
            k = s.lower()
            if k in seen or len(s) < 12:
                continue
            seen.add(k)
            site["pet_sentences"].append(OrderedDict([
                ("url", r.get("final_url") or r["url"]), ("document_sha256", r.get("sha256")),
                ("document_bytes", r.get("bytes")), ("fetched_at", r.get("fetched_at")),
                ("sentence", s)]))
    site["disposition"] = "SITE_READ"
    return site


def build():
    BI.DOCS = DOCS
    stats = Stats()
    with ThreadPoolExecutor(max_workers=8) as ex:
        sites = list(ex.map(lambda s: read_site(s, stats), SEEDS))
    return OrderedDict([
        ("schema", "ptf-independent-first-party-lane/1.0"), ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID), ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
        ("lane", "DIRECT_STATIC_FETCH of each property's own website"),
        ("paid_provider_calls", 0), ("usd_spent", 0.0),
        ("free_http_requests", stats.requests),
        ("page_cap_per_site", PAGE_CAP),
        ("a_sentence_is_a_candidate",
         "Sentences are kept verbatim with their document hash. Operative status is decided by "
         "the clean-authority helper."),
        ("documents_persisted_at", os.path.relpath(DOCS, _DASH).replace("\\", "/")),
        ("sites", sites),
    ])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args(argv)
    rep = build()
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rep, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    for s in rep["sites"]:
        print("%-22s %-28s pages=%d pet_sentences=%d" % (s["seed"], s["disposition"], len(s["pages"]),
                                                         len(s["pet_sentences"])))
    print("requests:", rep["free_http_requests"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
