"""PTF-SAVANNAH-GA-PARALLEL-SOURCE-READY-001 -- Phase 10/11: the free static first-party lane.

For every census identity (OUTER BANKS: all of them, so the lane's target set does not
shrink as reads resolve rows and a re-run reproduces the reviewed report), the official website
the map source names (and any first-party route the census already holds) is
fetched ONCE by a plain HTTPS client. The document is persisted as returned,
addressed by sha256, under ``data/acquisition/savannah_ga_static_001/``, and this
helper extracts -- for a reviewer, never as a decision -- the Hotel / LodgingBusiness
JSON-LD address and every sentence on the page that mentions pets, dogs, cats or
animals.

Nothing here classifies a policy. Operative quotes chosen from these documents are
recorded in ``savannah_ga_attended/brand_pages.json`` with the document sha256 they
were read from, and the capture helper binds them. A refusal (403 / 429 / timeout /
challenge shell) is recorded as a FETCH OUTCOME -- the attended browser is the next
rung -- and a known-blocked domain is not retried here.

Output:
  launch_packages/pettripfinder/markets/reports/savannah_ga_static_lane_001.json
"""
from __future__ import annotations

import html as H
import json
import os
import re
import sys
import time
from collections import Counter, OrderedDict
from concurrent.futures import ThreadPoolExecutor

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import savannah_ga_brand_inventory_001 as B  # noqa: E402

WORK_ORDER = "PTF-SAVANNAH-GA-PARALLEL-SOURCE-READY-001"
MARKET_ID = "savannah-ga"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CENSUS = os.path.join(PKG, "identity_census_proposed", "savannah-ga.json")
CLEAN = os.path.join(REPORTS, "savannah_ga_clean_authority_001.json")
OUT = os.path.join(REPORTS, "savannah_ga_static_lane_001.json")
B.DOCS = os.path.join(_DASH, "data", "acquisition", "savannah_ga_static_001")

#: Domains the brand lane measured refusing this client on this run (plain 403 /
#: timeout); read in the attended browser instead.
BROWSER_ONLY = ("marriott.com", "hilton.com", "ihg.com", "choicehotels.com", "hyatt.com",
                "bestwestern.com", "redroof.com", "motel6.com", "extendedstayamerica.com", "reservations.com", "visitsavannah.com",
                "omnihotels.com", "radissonhotels.com", "fourseasons.com", "yelp.com", "sonder.com", "vrbo.com", "airbnb.com",
                "facebook.com", "instagram.com", "linktr.ee", "sellmytimesharenow.com", "wyndhamhotels.com", "stories.hilton.com")

_PET = re.compile(r"[^.<>\n]{0,220}\b(pets?|dogs?|cats?|animals?|canine|furry)\b[^.<>\n]{0,260}", re.I)


def targets():
    census = json.load(open(CENSUS, encoding="utf-8"))
    out = OrderedDict()
    for h in census["hotels"]:
        urls = {o.get("website_url") for o in h["evidence"] if o.get("website_url")}
        if h.get("official_url"):
            urls.add(h["official_url"])
        # a map website tag without a scheme ("elizabethaninn.com") is read over https
        urls = {u if re.match(r"https?://", u) else "https://" + u for u in urls if u}
        for u in sorted(urls):
            if any(d in u for d in BROWSER_ONLY):
                continue
            out.setdefault(u, []).append(h["identity_key"])
    return out


def jsonld_addresses(text):
    found = []
    for m in re.finditer(r"<script[^>]*application/ld\+json[^>]*>(.*?)</script>", text, re.S | re.I):
        try:
            j = json.loads(m.group(1))
        except Exception:  # noqa: BLE001
            continue
        stack = j if isinstance(j, list) else [j]
        while stack:
            x = stack.pop()
            if isinstance(x, dict):
                if isinstance(x.get("address"), dict) and x.get("address").get("streetAddress"):
                    a = x["address"]
                    found.append(OrderedDict([("type", x.get("@type")), ("name", x.get("name")),
                                              ("street", a.get("streetAddress")), ("city", a.get("addressLocality")),
                                              ("region", a.get("addressRegion")), ("postal", a.get("postalCode")),
                                              ("phone", x.get("telephone"))]))
                stack.extend(v for v in x.values() if isinstance(v, (dict, list)))
            elif isinstance(x, list):
                stack.extend(x)
    return found


def read(url):
    st = B.Stats()
    row, body = B.fetch(url, st, timeout=30)
    text = body.decode("utf-8", "replace")
    plain = re.sub(r"<script.*?</script>|<style.*?</style>", " ", text, flags=re.S | re.I)
    plain = H.unescape(re.sub(r"<[^>]+>", "\n", plain))
    plain = re.sub(r"[ \t ]+", " ", plain)
    pets = []
    for m in _PET.finditer(plain):
        s = m.group(0).strip()
        if s and s not in pets:
            pets.append(s)
    return OrderedDict([
        ("url", url), ("status", row["status"]), ("final_url", row["final_url"]), ("error", row["error"]),
        ("bytes", row["bytes"]), ("sha256", row["sha256"]), ("title", (re.search(r"<title[^>]*>(.*?)</title>", text, re.S | re.I) or [None, ""])[1].strip()[:160]),
        ("jsonld_addresses", jsonld_addresses(text)[:4]), ("pet_sentences", pets[:25]),
    ])


def main():
    t0 = time.time()
    tg = targets()
    with ThreadPoolExecutor(max_workers=8) as ex:
        rows = list(ex.map(read, list(tg)))
    for r in rows:
        r["census_identity_keys"] = tg[r["url"]]
    doc = OrderedDict([
        ("schema", "ptf-static-first-party-lane/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("as_of", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
        ("paid_provider_calls", 0), ("usd_spent", 0.0),
        ("what_this_is", "Reviewer extraction only: documents persisted by sha256; no policy is decided here."),
        ("browser_only_domains", BROWSER_ONLY),
        ("targets", len(tg)), ("by_status", dict(Counter(str(r["status"]) for r in rows))),
        ("seconds", round(time.time() - t0, 1)),
        ("documents_persisted_at", os.path.relpath(B.DOCS, _DASH).replace("\\", "/")),
        ("rows", rows),
    ])
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("targets", len(tg), doc["by_status"], "seconds", doc["seconds"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
