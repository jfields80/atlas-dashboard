"""PTF-ORLANDO-FL-HARDENED-V2-SOURCE-READY-001 -- Phase 12F: Loews Hotels (Universal Orlando's Loews-operated hotels), plain client.

loewshotels.com answers a plain HTTPS client. Each property's own page carries its address (Hotel JSON-LD) and, in its
own "Hotel Policies" text, the sentence that opens "Pet Policy:". That sentence -- up to the end of the policy
paragraph -- is the operative quote. Routes are the eight Universal Orlando routes the brand's own sitemap lists
(orlando_fl_v2_brand_inventory_001). Documents persisted by sha256 under data/acquisition/orlando_fl_v2_loews_001/.

Outputs:
  launch_packages/pettripfinder/markets/staging/orlando-fl/raw_captures/loews_rows.json
  launch_packages/pettripfinder/markets/reports/orlando_fl_v2_loews_lane_001.json
"""
from __future__ import annotations

import html
import json
import os
import re
import sys
import time
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import orlando_fl_v2_brand_inventory_001 as B  # noqa: E402

WORK_ORDER = "PTF-ORLANDO-FL-HARDENED-V2-SOURCE-READY-001"
B.DOCS = os.path.join(_DASH, "data", "acquisition", "orlando_fl_v2_loews_001")
REPORTS = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports")
RAW_OUT = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "staging", "orlando-fl", "raw_captures", "loews_rows.json")
REPORT_OUT = os.path.join(REPORTS, "orlando_fl_v2_loews_lane_001.json")


def _text(body):
    t = re.sub(r"(?s)<script.*?</script>|<style.*?</style>", " ", body)
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", t)).split())


def _address(body):
    for m in re.finditer(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', body, re.S | re.I):
        try:
            data = json.loads(m.group(1))
        except ValueError:
            continue
        for node in (data if isinstance(data, list) else [data]):
            if isinstance(node, dict) and isinstance(node.get("address"), dict):
                a = node["address"]
                return node.get("name"), a.get("streetAddress"), a.get("addressLocality"), a.get("postalCode"), node.get("telephone")
    return None, None, None, None, None


def main():
    inv = json.load(open(os.path.join(REPORTS, "orlando_fl_v2_brand_inventory_001.json"), encoding="utf-8"))
    routes = sorted({l["route"].rstrip("/") for l in inv["leads"] if l["family"] == "LOEWS"})
    st = B.Stats()
    rows = []
    for u in routes:
        time.sleep(1.0)
        row, body = B.fetch(u, st, timeout=40)
        b = body.decode("utf-8", "replace")
        if "�" in b:
            b = body.decode("cp1252", "replace")
        t = _text(b)
        name, street, city, z, ph = _address(b)
        m = (re.search(r"(Pet Policy):\s*(.{20,900}?)(?=\s(?:Standard|Smoking|Parking|Resort Fee|Rollaway|Cancellation|"
                       r"Age Requirements|[A-Z][a-z]+ Policy:)|$)", t)
             or re.search(r"(Pets):\s*(.{10,300}?)(?=\s[A-Z][A-Za-z ]{2,30}\*?:|$)", t))
        rows.append(OrderedDict([("u", u), ("s", row["status"]), ("final_url", row["final_url"]), ("h", row["sha256"]), ("b", row["bytes"]),
                                 ("n", name), ("st", street), ("ci", city), ("z", (z or "")[:5]), ("ph", ph),
                                 ("p", ("%s: %s" % (m.group(1), m.group(2).strip())) if m else "")]))
        print(u, row["status"], name, z, (m.group(2)[:80] if m else ""), flush=True)
    os.makedirs(os.path.dirname(RAW_OUT), exist_ok=True)
    json.dump(OrderedDict([("rows", rows)]), open(RAW_OUT, "w", encoding="utf-8", newline="\n"), indent=1, ensure_ascii=False)
    json.dump(OrderedDict([("schema", "ptf-brand-first-party-lane/1.0"), ("work_order", WORK_ORDER), ("market_id", "orlando-fl"),
                           ("lane", "DIRECT_STATIC_FETCH (loewshotels.com property pages)"), ("paid_provider_calls", 0),
                           ("usd_spent", 0.0), ("free_http_requests", st.requests), ("routes", len(routes)),
                           ("with_pet_policy_sentence", sum(1 for r in rows if r["p"]))]),
              open(REPORT_OUT, "w", encoding="utf-8", newline="\n"), indent=1)


if __name__ == "__main__":
    main()
