"""PTF-AUGUSTA-GA-HARDENED-V2-SOURCE-READY-001 -- Phase 11/12/15: the real
Firecrawl acquisition pass over the router-classified FIRECRAWL cohort
(scripts/pettripfinder/acquisition/firecrawl_capture.py; existing authorized
provider capacity per the founder's Stage-3b authorization, $10 cap, 544
credits confirmed available before this run).

For every row the acquisition-cost-plan (003) routed to FIRECRAWL: one
``firecrawl_capture.fetch`` call, full durable evidence persisted (requested
URL, final URL, capture lane, provider, timestamp, identity signals, durable
content reference by sha256, content hash, byte length, extracted pet
sentences / JSON-LD as candidate operative quotes -- NOT yet a policy
classification, that is Phase 16-18's job in the next script), source class.
No byte-length-only or ephemeral evidence: every captured document is written
to disk and referenced by its sha256.

Output:
  launch_packages/pettripfinder/markets/reports/augusta_ga_firecrawl_acquisition_005.json
  data/acquisition/augusta_ga_firecrawl_005/<sha256>.html
"""
from __future__ import annotations

import html as H
import json
import os
import re
import sys
import time
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.acquisition import firecrawl_capture as FC  # noqa: E402

WORK_ORDER = "PTF-AUGUSTA-GA-HARDENED-V2-SOURCE-READY-001"
MARKET_ID = "augusta-ga"
AUTHORIZED_CAP_USD = 10.0
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
PLAN = os.path.join(PKG, "markets", "reports", "augusta_ga_acquisition_cost_plan_003.json")
CENSUS = os.path.join(PKG, "identity_census_proposed", "augusta-ga.json")
DOCS = os.path.join(_DASH, "data", "acquisition", "augusta_ga_firecrawl_005")
OUT = os.path.join(PKG, "markets", "reports", "augusta_ga_firecrawl_acquisition_005.json")

_PET = re.compile(r"[^.<>\n]{0,220}\b(pets?|dogs?|cats?|animals?|canine|furry)\b[^.<>\n]{0,260}", re.I)


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
                    found.append(OrderedDict([("street", a.get("streetAddress")), ("city", a.get("addressLocality")),
                                              ("region", a.get("addressRegion")), ("postal", a.get("postalCode")),
                                              ("name", x.get("name"))]))
                stack.extend(v for v in x.values() if isinstance(v, (dict, list)))
            elif isinstance(x, list):
                stack.extend(x)
    return found


def persist(body_str):
    import hashlib
    body = body_str.encode("utf-8")
    digest = hashlib.sha256(body).hexdigest()
    os.makedirs(DOCS, exist_ok=True)
    path = os.path.join(DOCS, digest + ".html")
    if not os.path.exists(path):
        with open(path, "wb") as fh:
            fh.write(body)
    return digest, len(body)


def main():
    plan = json.load(open(PLAN, encoding="utf-8"))
    targets = [d for d in plan["decisions"] if d["next_lane"] == "FIRECRAWL"]
    census = json.load(open(CENSUS, encoding="utf-8"))
    by_key = {h["identity_key"]: h for h in census["hotels"]}

    retry_only = os.environ.get("AUGUSTA_FC_RETRY_404_ONLY") == "1"
    if retry_only and os.path.exists(OUT):
        prior = json.load(open(OUT, encoding="utf-8"))
        prior_by_key = {r["identity_key"]: r for r in prior.get("rows", [])}
        already_ok = {k for k, r in prior_by_key.items() if r.get("status") == 200}
        targets = [d for d in targets if d["identity_key"] not in already_ok]
        print("retry mode: skipping %d already-200 rows, retrying %d" % (len(already_ok), len(targets)))

    credits_before = FC.credits_remaining()
    rows = []
    for d in targets:
        h = by_key.get(d["identity_key"])
        url = d["url"]
        started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        row = OrderedDict([
            ("identity_key", d["identity_key"]), ("canonical_name", h.get("canonical_name") if h else None),
            ("family", d["family"]), ("requested_url", url), ("capture_lane", "FIRECRAWL"),
            ("provider", "firecrawl"), ("captured_at", started),
        ])
        try:
            result = FC.fetch(url)
        except Exception as exc:  # noqa: BLE001
            row["ok"] = False
            row["error"] = "%s: %s" % (type(exc).__name__, exc)
            row["source_class"] = "FIRECRAWL_FAILED"
            rows.append(row)
            continue
        prov = result.get("provenance", {})
        html_text = result.get("html") or ""
        digest, nbytes = (persist(html_text) if html_text else (None, 0))
        plain = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html_text, flags=re.S | re.I)
        plain = H.unescape(re.sub(r"<[^>]+>", "\n", plain))
        pets = []
        for m in _PET.finditer(plain):
            s = m.group(0).strip()
            if s and s not in pets:
                pets.append(s)
        addrs = jsonld_addresses(html_text)
        identity_confirmed = bool(h) and (
            (h.get("canonical_name") or "").split()[0].lower() in html_text.lower()[:20000]
            if h.get("canonical_name") else False)
        if not result.get("ok") or not html_text:
            source_class = "FIRECRAWL_BLOCKED" if "SCRAPE_ALL_ENGINES_FAILED" in str(result.get("error", "")) else "FIRECRAWL_FAILED"
        elif not identity_confirmed:
            source_class = "FIRECRAWL_IDENTITY_ONLY"
        elif pets:
            source_class = "FIRECRAWL_PUBLICATION_GRADE"
        elif addrs:
            source_class = "FIRECRAWL_IDENTITY_ONLY"
        else:
            source_class = "FIRECRAWL_SOURCE_SILENT"
        row.update([
            ("ok", bool(result.get("ok"))), ("final_url", prov.get("final_url")),
            ("status", prov.get("status")), ("content_sha256", digest), ("content_bytes", nbytes),
            ("credits_used", prov.get("credits_used")), ("provider_request_id", prov.get("provider_request_id")),
            ("error", prov.get("error") or None), ("identity_confirmed_on_page", identity_confirmed),
            ("jsonld_addresses", addrs[:3]), ("pet_sentences", pets[:15]), ("source_class", source_class),
        ])
        rows.append(row)

    if retry_only and os.path.exists(OUT):
        kept = [r for r in prior.get("rows", []) if r["identity_key"] in already_ok]
        rows = kept + rows

    credits_after = FC.credits_remaining()
    used = (credits_before - credits_after) if (credits_before is not None and credits_after is not None) else None
    doc = OrderedDict([
        ("schema", "ptf-firecrawl-acquisition/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("as_of", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
        ("authorized_cap_usd", AUTHORIZED_CAP_USD),
        ("credits_before", credits_before), ("credits_after", credits_after), ("credits_used", used),
        ("attempted", len(rows)), ("by_source_class", dict(Counter(r.get("source_class") for r in rows))),
        ("by_family", {}), ("documents_persisted_at", os.path.relpath(DOCS, _DASH).replace("\\", "/")),
        ("rows", rows),
    ])
    fam_class = OrderedDict()
    for r in rows:
        fam_class.setdefault(r["family"], Counter())[r.get("source_class", "?")] += 1
    doc["by_family"] = {k: dict(v) for k, v in fam_class.items()}

    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("attempted", len(rows), "by_source_class", doc["by_source_class"], "credits_used", used)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
