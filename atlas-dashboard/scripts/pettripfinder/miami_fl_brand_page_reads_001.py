"""PTF-MIAMI-FL-HARDENED-SOURCE-READY-001 -- the Choice / IHG property pages the Firecrawl route-discovery lane found.

Choice's own sitemap timed out to the plain client and IHG's answered 403, so neither family's routes reached the
census by name: a discovered route names a FLAG and a city ("/florida/miami/sleep-inn-hotels/fl123"), never the
building. This lane reads each discovered in-market route through Firecrawl (the rung the committed route table
assigns both families) and keeps what the PAGE ITSELF states: its own name, street, postal code and telephone from
its own JSON-LD, and every sentence on it that names pets or dogs.

BINDING IS THE PAGE'S OWN ADDRESS. Nothing here is keyed to a census row by name: the clean-authority pass joins a
row to a census identity only on house number + postal code. A page that states no address binds nothing.

NO POLICY IS DECIDED HERE. The sentences are candidate quotes; the negation guard and the shared first-party reader
in the clean authority decide, exactly as for every other lane.

Cost: one plan credit per page that answers, zero when every engine is refused. Existing plan credits only.

Outputs:
  launch_packages/pettripfinder/markets/staging/miami-fl/raw_captures/brand_page_rows.json
  launch_packages/pettripfinder/markets/reports/miami_fl_brand_page_reads_001.json
"""
from __future__ import annotations

import argparse
import hashlib
import html as _html
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

WORK_ORDER = "PTF-MIAMI-FL-HARDENED-SOURCE-READY-001"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
DISCOVERY = os.path.join(REPORTS, "miami_fl_firecrawl_discovery_001.json")
DOCS = os.path.join(_DASH, "data", "acquisition", "miami_fl_brand_page_reads_001")
RAW_OUT = os.path.join(PKG, "markets", "staging", "miami-fl", "raw_captures", "brand_page_rows.json")
REPORT_OUT = os.path.join(REPORTS, "miami_fl_brand_page_reads_001.json")
CAP = 34
FLOOR = 400
#: The market's own towns, as a Choice or IHG route spells them. A route naming another town is another market's.
IN_MARKET = ("miami", "miami-beach", "miami-springs", "doral", "coral-gables", "coconut-grove", "hialeah",
             "miami-lakes", "north-miami", "north-miami-beach", "aventura", "sunny-isles-beach", "bal-harbour",
             "surfside", "key-biscayne", "homestead", "florida-city", "kendall", "cutler-bay", "miami-gardens",
             "opa-locka", "sweetwater", "medley", "south-miami", "virginia-gardens")
_SENT = re.compile(r"[^.!?]{0,240}\b(pets?|dogs?|service animals?)\b[^.!?]{0,240}[.!?]", re.I)
_LD = re.compile(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', re.S | re.I)


def _text(doc):
    t = re.sub(r"(?s)<script.*?</script>|<style.*?</style>|<noscript.*?</noscript>", " ", doc)
    return " ".join(_html.unescape(re.sub(r"<[^>]+>", " ", t)).split())


def _hotel_ld(text):
    for m in _LD.finditer(text):
        try:
            data = json.loads(m.group(1))
        except ValueError:
            continue
        for node in (data if isinstance(data, list) else [data]):
            if isinstance(node, dict) and node.get("@type") in ("Hotel", "LodgingBusiness", "Resort", "Motel") \
                    and node.get("address"):
                return node
    return None


#: Choice's own property pages carry no Hotel JSON-LD; their own header states the address as one line
#: ("553 NE 1st Ave, Florida City, FL, 33034"). Read from the page's own text, never from a directory.
_ADDR_LINE = re.compile(
    r"\b(\d+[A-Za-z]?\s+(?:[NSEW]\.?W?\.?\s+)?[0-9A-Za-z.'\-]+(?:\s+[0-9A-Za-z.'\-]+){0,4}\s+"
    r"(?:St|Street|Ave|Avenue|Rd|Road|Dr|Drive|Blvd|Boulevard|Way|Ct|Court|Ter|Terrace|Pl|Place|Hwy|Highway|Cir|Circle|Cswy|Causeway)\.?)"
    r",\s*([A-Za-z .'\-]{3,28}),\s*FL,?\s*(\d{5})\b", re.I)


#: The street, taken from the RIGHTMOST house number in the matched run: the page prints its rating and review
#: count immediately before its address ("3 396 reviews 4343 Collins Ave."), and only the last number is the house.
_STREET_TAIL = re.compile(
    r"(\d+[A-Za-z]?\s+(?:[NSEW]\.?W?\.?\s+)?(?:(?!reviews\b)[0-9A-Za-z.'\-]+\s+){0,3}"
    r"(?:St|Street|Ave|Avenue|Rd|Road|Dr|Drive|Blvd|Boulevard|Way|Ct|Court|Ter|Terrace|Pl|Place|Hwy|Highway|Cir|Circle|Cswy|Causeway)\.?)$",
    re.I)


def address_from_text(text):
    m = _ADDR_LINE.search(text or "")
    if not m:
        return "", "", ""
    street = " ".join(m.group(1).split())
    tail = _STREET_TAIL.search(street)
    if tail:
        street = " ".join(tail.group(1).split())
    return street, m.group(2).strip(), m.group(3)


def town_of(route):
    m = re.search(r"choicehotels\.com/florida/([a-z-]+)/", route) or \
        re.search(r"ihg\.com/[a-z]+/hotels/us/en/([a-z-]+)/", route)
    return m.group(1) if m else ""


def targets():
    doc = json.load(open(DISCOVERY, encoding="utf-8"))
    seen, out = set(), []
    for r in sorted(doc.get("routes", []), key=lambda x: x["route"]):
        town = town_of(r["route"])
        if town not in IN_MARKET or r["route"] in seen:
            continue
        seen.add(r["route"])
        out.append(r)
    return out


def reparse():
    """PAY ONCE PER PAGE: re-read every page this lane already bought from its persisted document. No fetch, no
    credit. Used after the address reader learned Choice's own address-line shape."""
    doc = json.load(open(RAW_OUT, encoding="utf-8"))
    rows = []
    for rec in doc["rows"]:
        rec = OrderedDict(rec)
        path = os.path.join(DOCS, (rec.get("h") or "") + ".html")
        if rec.get("status") == 200 and rec.get("h") and os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                page = fh.read()
            ld = _hotel_ld(page) or {}
            addr = ld.get("address") or {}
            text = _text(page)
            rec["n"] = (ld.get("name") or "").strip() or rec.get("n") or ""
            if addr.get("streetAddress"):
                rec["st"], rec["ci"] = addr["streetAddress"].strip(), (addr.get("addressLocality") or "").strip()
                rec["z"] = (addr.get("postalCode") or "").strip()[:5]
                rec["address_basis"] = "PAGE_OWN_JSON_LD"
            else:
                st, ci, z = address_from_text(text)
                rec["st"], rec["ci"], rec["z"] = st, ci, z
                rec["address_basis"] = "PAGE_OWN_ADDRESS_LINE" if st else ""
            rec["ph"] = (ld.get("telephone") or "").strip() or rec.get("ph") or ""
            sents, seen_s = [], set()
            for m in _SENT.finditer(text):
                s = m.group(0).strip()
                if s.lower() in seen_s or len(sents) >= 8:
                    continue
                seen_s.add(s.lower())
                sents.append(s)
            rec["pet_sentences"] = sents
            rec["reparsed_from_persisted_document"] = True
        rows.append(rec)
    with open(RAW_OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(OrderedDict([("rows", rows)]), fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    report = json.load(open(REPORT_OUT, encoding="utf-8"))
    report["with_own_address"] = sum(1 for r in rows if r.get("st"))
    report["with_pet_sentences"] = sum(1 for r in rows if r.get("pet_sentences"))
    report["address_basis_counts"] = OrderedDict(sorted(Counter(r.get("address_basis") or "NONE" for r in rows).items()))
    report["reparse_note"] = ("the pages this lane already bought were re-read from their persisted documents after "
                              "the address reader learned Choice's own address-line shape; 0 further credits")
    with open(REPORT_OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(report, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("reparsed", len(rows), "with address", report["with_own_address"], "credits spent 0")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--cap", type=int, default=CAP)
    ap.add_argument("--reparse", action="store_true",
                    help="re-read the pages this lane already bought, from their persisted documents (0 credits)")
    args = ap.parse_args(argv)
    if args.reparse:
        return reparse()
    os.makedirs(DOCS, exist_ok=True)
    before = FC.credits_remaining()
    rows, spent = [], 0
    for t in targets():
        if spent >= args.cap:
            break
        live = FC.credits_remaining()
        if live is not None and live <= FLOOR:
            rows.append(OrderedDict([("route", t["route"]), ("stopped", "CREDIT_FLOOR")]))
            break
        rec = OrderedDict([("family", t["family"]), ("property_code", t.get("property_code", "")),
                           ("u", t["route"]), ("town_in_route", town_of(t["route"]))])
        try:
            r = FC.fetch(t["route"], profile=FC.ROUTED_PROFILE)
            doc = r.get("html") or ""
            sha = hashlib.sha256(doc.encode("utf-8")).hexdigest() if doc else ""
            if doc:
                with open(os.path.join(DOCS, sha + ".html"), "w", encoding="utf-8", newline="") as fh:
                    fh.write(doc)
            rec.update(status=r.get("status"), ok=r.get("ok"), h=sha, b=len(doc.encode("utf-8")),
                       final_url=r.get("final_url"), credits_used=r.get("credits_used"),
                       captured_at=(r.get("provenance") or {}).get("captured_at"))
            ld = _hotel_ld(doc) or {}
            addr = ld.get("address") or {}
            rec["n"] = (ld.get("name") or "").strip()
            rec["st"] = (addr.get("streetAddress") or "").strip()
            rec["ci"] = (addr.get("addressLocality") or "").strip()
            rec["z"] = (addr.get("postalCode") or "").strip()[:5]
            rec["ph"] = (ld.get("telephone") or "").strip()
            text = _text(doc)
            if not rec["st"]:
                rec["st"], rec["ci"], rec["z"] = address_from_text(text)
                rec["address_basis"] = "PAGE_OWN_ADDRESS_LINE" if rec["st"] else ""
            else:
                rec["address_basis"] = "PAGE_OWN_JSON_LD"
            sents, seen_s = [], set()
            for m in _SENT.finditer(text):
                s = m.group(0).strip()
                if s.lower() in seen_s or len(sents) >= 8:
                    continue
                seen_s.add(s.lower())
                sents.append(s)
            rec["pet_sentences"] = sents
        except Exception as exc:  # noqa: BLE001 -- recorded, never swallowed
            rec["error"] = "%s: %s" % (type(exc).__name__, FC.redact(str(exc))[:200])
        spent += 1
        rows.append(rec)
        print("  %-52s %s ld=%s sentences=%d" % (t["route"][-52:], rec.get("status"), bool(rec.get("st")),
                                                 len(rec.get("pet_sentences") or [])), flush=True)
        time.sleep(2)
    after = FC.credits_remaining()
    with open(RAW_OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(OrderedDict([("rows", rows)]), fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    report = OrderedDict([
        ("schema", "ptf-brand-page-reads/1.0"), ("work_order", WORK_ORDER), ("market_id", "miami-fl"),
        ("lane", "FIRECRAWL (the rung the committed route table assigns CHOICE and IHG); plan credits, no USD"),
        ("attempt_cap", args.cap), ("credit_floor", FLOOR), ("attempted", spent),
        ("answered", sum(1 for r in rows if r.get("status") == 200)),
        ("with_own_address", sum(1 for r in rows if r.get("st"))),
        ("with_pet_sentences", sum(1 for r in rows if r.get("pet_sentences"))),
        ("by_family", OrderedDict(sorted(Counter(r["family"] for r in rows if r.get("family")).items()))),
        ("credits", OrderedDict([("before", before), ("after", after),
                                 ("delta", (before - after) if before is not None and after is not None else None)])),
        ("binding_rule", "house number + postal code the PAGE states, joined in the clean authority; never a name"),
        ("raw_captures", os.path.relpath(RAW_OUT, _DASH).replace("\\", "/")),
    ])
    with open(REPORT_OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(report, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("attempted", spent, "answered", report["answered"], "with address", report["with_own_address"],
          "credits", before, "->", after)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
