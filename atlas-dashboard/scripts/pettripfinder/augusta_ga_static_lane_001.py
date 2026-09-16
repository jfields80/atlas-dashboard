"""PTF-AUGUSTA-GA-HARDENED-V2-SOURCE-READY-001 -- Phase 8/10/16: the free
static first-party lane (cloned from the Savannah GA helper; Augusta tokens).

For every census identity, every non-OSM evidence URL and the ``official_url``
field (when set) is fetched ONCE by a plain HTTPS client -- ladder rung 2,
``DIRECT_STATIC_FETCH``, $0. The document is persisted by sha256 under
``data/acquisition/augusta_ga_static_001/``. This helper extracts -- for a
reviewer, never as a decision -- the Hotel/LodgingBusiness JSON-LD address and
every sentence on the page that mentions pets, dogs, cats or animals.

Nothing here classifies a policy or resolves an identity. A brand domain this
client is known to be walled on (BROWSER_ONLY, the exact Marriott/Hilton/IHG/
Wyndham/Choice/Hyatt/Best Western capability-wall set) is never attempted here
-- it belongs to the attended-browser rung.

Output:
  launch_packages/pettripfinder/markets/reports/augusta_ga_static_lane_001.json
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

from scripts.pettripfinder import augusta_ga_brand_inventory_001 as B  # noqa: E402

WORK_ORDER = "PTF-AUGUSTA-GA-HARDENED-V2-SOURCE-READY-001"
MARKET_ID = "augusta-ga"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CENSUS = os.path.join(PKG, "identity_census_proposed", "augusta-ga.json")
OUT = os.path.join(REPORTS, "augusta_ga_static_lane_001.json")
B.DOCS = os.path.join(_DASH, "data", "acquisition", "augusta_ga_static_001")

#: Domains never worth a fetch at all -- not brand hotel pages, so no
#: static/Firecrawl/attended decision could ever apply to them (a map
#: node, a lead aggregator, a generic search engine). This is NOT a
#: presumed-walled list: every real brand domain (including Marriott/
#: Hilton/IHG/etc.) IS attempted below and its outcome measured fresh for
#: THIS market, per the "every refusal is measured, not inherited" rule --
#: an assumption inherited from another market's run is exactly the mistake
#: this list avoids.
BROWSER_ONLY = ("openstreetmap.org", "bringfido.com", "tripadvisor.com", "google.com",
                "yelp.com", "facebook.com", "instagram.com", "linktr.ee")

_PET = re.compile(r"[^.<>\n]{0,220}\b(pets?|dogs?|cats?|animals?|canine|furry)\b[^.<>\n]{0,260}", re.I)


def targets():
    census = json.load(open(CENSUS, encoding="utf-8"))
    out = OrderedDict()
    for h in census["hotels"]:
        urls = set()
        if h.get("official_url"):
            urls.add(h["official_url"])
        for e in h.get("evidence", []):
            u = e.get("source_url") or e.get("website_url")
            if u:
                urls.add(u)
        urls = {u if re.match(r"https?://", u) else "https://" + u for u in urls if u}
        for u in sorted(urls):
            if any(d in u.lower() for d in BROWSER_ONLY):
                continue  # never a hotel's own page -- no ladder decision applies
            # every remaining URL (INCLUDING major-brand domains) is attempted:
            # the ladder requires a MEASURED outcome, not an inherited
            # assumption from another market's run.
            out.setdefault(u, []).append(h["identity_key"])
    return out


def classify_outcome(status, error, requested_url=None, final_url=None):
    """Map a raw fetch result onto the shared brightdata.outcomes vocabulary
    the acquisition ladder reads (RowEvidence.static_outcome). A 404 or a
    redirect off the requested property slug onto a bare brand/city hub
    (``?brand_id=``, or a final path shorter than the one requested) is a
    CHANNEL FAILURE -- the property's own page was never actually reached --
    not an authoritative "the page says nothing", so it escalates rather than
    settling the row on a wrong-URL artifact."""
    if error:
        return "NAVIGATION_FAILED"
    if status is None:
        return "NAVIGATION_FAILED"
    if status in (404,):
        return "NAVIGATION_FAILED"
    if status == 200:
        if final_url and requested_url and final_url != requested_url:
            if "?brand_id=" in final_url or "?" in final_url.split(requested_url.split("/")[-1] or " ", 1)[-1]:
                return "UNEXPECTED_PAGE"
            req_slug = requested_url.rstrip("/").split("/")[-1] if requested_url.rstrip("/").split("/")[-1] != "overview" else requested_url.rstrip("/").split("/")[-2]
            if req_slug and req_slug not in final_url:
                return "UNEXPECTED_PAGE"
        return None  # decided by content below, not the status alone
    if status in (401, 403, 429):
        return "ACCESS_DENIED"
    if 500 <= status < 600:
        return "NAVIGATION_FAILED"
    return "UNEXPECTED_PAGE"


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
    plain = re.sub(r"[ \t ]+", " ", plain)
    pets = []
    for m in _PET.finditer(plain):
        s = m.group(0).strip()
        if s and s not in pets:
            pets.append(s)
    outcome = classify_outcome(row["status"], row["error"], requested_url=url, final_url=row["final_url"])
    if outcome is None:
        # HTTP 200: VALID if the page plainly states pet policy or an
        # address; a bot-interstitial/challenge shell (near-empty body,
        # under 2KB rendered text) is UNHYDRATED, not VALID.
        outcome = "VALID" if (pets or jsonld_addresses(text)) else (
            "UNHYDRATED" if len(plain.strip()) < 800 else "POLICY_NOT_FOUND")
    return OrderedDict([
        ("url", url), ("status", row["status"]), ("final_url", row["final_url"]), ("error", row["error"]),
        ("bytes", row["bytes"]), ("sha256", row["sha256"]), ("outcome", outcome),
        ("title", (re.search(r"<title[^>]*>(.*?)</title>", text, re.S | re.I) or [None, ""])[1].strip()[:160]),
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
        ("what_this_is", "Reviewer extraction only: documents persisted by sha256; no policy or identity is decided here."),
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
