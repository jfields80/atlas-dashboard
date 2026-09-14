"""PTF-BOONE-BLOWING-ROCK-NC-PARALLEL-SOURCE-READY-001 -- Phase 11B: the independents' own policy pages.

High Country independents (like the Outer Banks') publish their pet policy on a subpage (``/pet-policy``,
``/policies``, ``/faq``), not on the home page the static lane reads. For every
census identity the static lane reached on a plain client (status 200), this lane
reads the property's OWN home page again, follows at most ``LINK_CAP`` same-site
links whose URL or anchor text names pets, policies, FAQs or amenities, and
persists every document as returned (sha256-addressed, under
``data/acquisition/boone_blowing_rock_nc_policy_pages_001/``).

For a reviewer it extracts, per document, the Hotel / LodgingBusiness JSON-LD
address and every sentence that mentions pets, dogs, cats or animals. Nothing
here classifies a policy: the operative quotes chosen from these documents are
recorded in ``markets/staging/boone-blowing-rock-nc/raw_captures/brand_pages.json``
with the sha256 of the document they were read from, and the capture helper binds
them.

Output:
  launch_packages/pettripfinder/markets/reports/boone_blowing_rock_nc_policy_pages_lane_001.json
"""
from __future__ import annotations

import html as H
import json
import os
import re
import sys
import time
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin, urlparse

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import boone_blowing_rock_nc_brand_inventory_001 as B  # noqa: E402
from scripts.pettripfinder import boone_blowing_rock_nc_static_lane_001 as S      # noqa: E402

WORK_ORDER = "PTF-BOONE-BLOWING-ROCK-NC-PARALLEL-SOURCE-READY-001"
MARKET_ID = "boone-blowing-rock-nc"
REPORTS = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports")
STATIC = os.path.join(REPORTS, "boone_blowing_rock_nc_static_lane_001.json")
OUT = os.path.join(REPORTS, "boone_blowing_rock_nc_policy_pages_lane_001.json")
DOCS = os.path.join(_DASH, "data", "acquisition", "boone_blowing_rock_nc_policy_pages_001")
LINK_CAP = 6
#: Official sites of census rows the static lane did not target (rows that were identity reviews
#: or name-only on its first pass), each taken from the Visitors Bureau listing or the map's website tag.
EXTRA_TARGETS = [
    ("https://cliffdwellers.com/", "cliff dwellers inn"),
    ("https://www.azaleagardeninn.com/", "azalea garden inn"),
    ("https://www.mountainaireinn.com/", "mountainaire inn and log cabins"),
    ("https://www.thevillageinnsofblowingrock.com/", "village inn of blowing rock"),
    ("https://www.boxwoodlodge.com/", "boxwood lodge"),
    ("https://www.blowingrockinn.com/", "blowing rock inn"),
    ("http://greenparkinn.com/", "green park inn"),
    ("https://www.homestead-inn.com/", "homestead inn"),
    ("https://www.gideonridge.com/", "gideon ridge inn"),
    ("https://www.windmoorhotel.com/", "the windmoor hotel"),
    ("https://www.chetola.com/", "chetola resort"),
    ("https://www.ragged-gardens.com/", "inn at ragged gardens"),
    ("https://www.hemlockinn.net/", "hemlock inn"),
    ("https://blowingrockmanor.com/", "the blowing rock manor"),
    ("https://www.hellbender.bar/", "hellbender bed and beverage"),
    ("https://www.ridgewayinn-nc.com/", "ridgeway inn"),
    ("https://www.meadowbrook-inn.com/", "meadowbrook inn"),
    ("https://www.hotelembers.com/", "the embers hotel"),
    ("https://www.innatlittlepondfarm.com/", "inn at little pond farm"),
    ("https://www.willowvalley-resort.com/", "willow valley resort"),
    ("https://www.graystonelodge.com/", "graystone lodge ascend hotel collection"),
    ("https://www.yonahlossee.com/", "yonahlossee resort accommodations"),
    ("https://www.thehorton.com/faq", "the horton hotel"),
]
_LINK_WORDS = re.compile(r"pet|dog|polic|faq|question|amenit|info|rules|terms", re.I)
_A = re.compile(r"<a\b[^>]*href=[\"']([^\"'#]+)[\"'][^>]*>(.*?)</a>", re.I | re.S)


def _extract(url):
    st = B.Stats()
    row, body = B.fetch(url, st, timeout=30)
    if row["status"] is None:
        # one bounded retry: small independent hosts drop concurrent connections
        time.sleep(3)
        row, body = B.fetch(url, st, timeout=45)
    text = body.decode("utf-8", "replace")
    plain = re.sub(r"<script.*?</script>|<style.*?</style>", " ", text, flags=re.S | re.I)
    plain = H.unescape(re.sub(r"<[^>]+>", "\n", plain))
    plain = re.sub(r"[ \t ]+", " ", plain)
    pets = []
    for m in S._PET.finditer(plain):
        s = m.group(0).strip()
        if s and s not in pets:
            pets.append(s)
    return row, text, OrderedDict([
        ("url", url), ("status", row["status"]), ("final_url", row["final_url"]), ("error", row["error"]),
        ("bytes", row["bytes"]), ("sha256", row["sha256"]),
        ("jsonld_addresses", S.jsonld_addresses(text)[:3]), ("pet_sentences", pets[:40]),
    ])


def site(target):
    url, keys = target
    row, text, home = _extract(url)
    base = row["final_url"] or url
    host = urlparse(base).netloc.lower().replace("www.", "")
    links = []
    for href, label in _A.findall(text):
        full = urljoin(base, href.strip())
        p = urlparse(full)
        if p.scheme not in ("http", "https") or p.netloc.lower().replace("www.", "") != host:
            continue
        lab = re.sub(r"<[^>]+>", " ", label)
        if not (_LINK_WORDS.search(p.path) or _LINK_WORDS.search(lab)):
            continue
        full = full.split("?")[0]
        if full.rstrip("/") != base.rstrip("/") and full not in links:
            links.append(full)
    links.sort(key=lambda u: (0 if re.search(r"pet|dog", u, re.I) else 1 if re.search(r"polic|faq", u, re.I) else 2, u))
    pages = [home] + [_extract(u)[2] for u in links[:LINK_CAP]]
    return OrderedDict([("census_identity_keys", keys), ("site", url), ("links_found", len(links)),
                        ("links_read", links[:LINK_CAP]), ("pages", pages)])


def main():
    B.DOCS = DOCS
    t0 = time.time()
    static = json.load(open(STATIC, encoding="utf-8"))
    seen, targets = set(), []
    for r in static["rows"]:
        if r["status"] != 200:
            continue
        key = (r["final_url"] or r["url"]).rstrip("/").lower()
        if key in seen:
            continue
        seen.add(key)
        targets.append((r["final_url"] or r["url"], r["census_identity_keys"]))
    for url, key in EXTRA_TARGETS:
        if url.rstrip("/").lower() not in seen:
            seen.add(url.rstrip("/").lower())
            targets.append((url, [key]))
    with ThreadPoolExecutor(max_workers=3) as ex:
        rows = list(ex.map(site, targets))
    # A transient failure on a re-read never erases a document an earlier run of this lane
    # already persisted and recorded: the earlier row for that site is carried forward.
    if os.path.exists(OUT):
        prior = {r["site"]: r for r in json.load(open(OUT, encoding="utf-8"))["rows"]}
        for i, r in enumerate(rows):
            old = prior.get(r["site"])
            if old and r["pages"][0]["status"] is None and old["pages"][0]["status"] is not None:
                old = OrderedDict(old)
                old["carried_forward_from_an_earlier_run_because_this_read_failed"] = r["pages"][0]["error"]
                rows[i] = old
    doc = OrderedDict([
        ("schema", "ptf-static-first-party-lane/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("as_of", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
        ("paid_provider_calls", 0), ("usd_spent", 0.0),
        ("what_this_is", "Reviewer extraction only: each property's own home page and at most %d same-site "
                         "policy / pet / FAQ pages, persisted by sha256; no policy is decided here." % LINK_CAP),
        ("sites", len(rows)), ("seconds", round(time.time() - t0, 1)),
        ("documents_persisted_at", os.path.relpath(DOCS, _DASH).replace("\\", "/")),
        ("rows", rows),
    ])
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("sites", len(rows), "pages", sum(len(r["pages"]) for r in rows), "seconds", doc["seconds"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
