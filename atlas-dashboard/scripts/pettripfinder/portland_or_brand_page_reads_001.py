"""PTF-PORTLAND-OR-HARDENED-SOURCE-READY-001 -- the Choice / IHG property pages the Firecrawl route-discovery lane found.

Choice's own sitemap timed out to the plain client and IHG's answered 403, so neither family's routes reached the
census by name: a discovered route names a FLAG and a city ("/arizona/phoenix/sleep-inn-hotels/az123"), never the
building. This lane reads each discovered in-market route through Firecrawl (the rung the committed route table
assigns both families) and keeps what the PAGE ITSELF states: its own name, street, postal code and telephone from
its own JSON-LD, and every sentence on it that names pets or dogs.

BINDING IS THE PAGE'S OWN ADDRESS. Nothing here is keyed to a census row by name: the clean-authority pass joins a
row to a census identity only on house number + postal code. A page that states no address binds nothing.

NO POLICY IS DECIDED HERE. The sentences are candidate quotes; the negation guard and the shared first-party reader
in the clean authority decide, exactly as for every other lane.

Cost: one plan credit per page that answers, zero when every engine is refused. Existing plan credits only.

Outputs:
  launch_packages/pettripfinder/markets/staging/portland-or/raw_captures/brand_page_rows.json
  launch_packages/pettripfinder/markets/reports/portland_or_brand_page_reads_001.json
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

WORK_ORDER = "PTF-PORTLAND-OR-HARDENED-SOURCE-READY-001"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
DISCOVERY = os.path.join(REPORTS, "portland_or_firecrawl_discovery_001.json")
DOCS = os.path.join(_DASH, "data", "acquisition", "portland_or_brand_page_reads_001")
RAW_OUT = os.path.join(PKG, "markets", "staging", "portland-or", "raw_captures", "brand_page_rows.json")
REPORT_OUT = os.path.join(REPORTS, "portland_or_brand_page_reads_001.json")
CAP = 80
FLOOR = 300
IN_MARKET = ("portland", "beaverton", "aloha", "hillsboro", "tigard", "king-city", "lake-oswego", "gresham",
             "tualatin", "wilsonville", "clackamas", "happy-valley", "damascus", "troutdale", "wood-village",
             "fairview", "milwaukie", "oregon-city", "west-linn", "gladstone", "sherwood", "forest-grove",
             "cornelius", "vancouver")
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
#: ("1300 Airport Rd, Jacksonville, FL, 32218"). Read from the page's own text, never from a directory.
_ADDR_LINE = re.compile(
    r"\b(\d+[A-Za-z]?\s+(?:[NSEW]\.?W?\.?\s+)?[0-9A-Za-z.'\-]+(?:\s+[0-9A-Za-z.'\-]+){0,4}\s+"
    r"(?:St|Street|Ave|Avenue|Rd|Road|Dr|Drive|Blvd|Boulevard|Way|Ct|Court|Ter|Terrace|Pl|Place|Hwy|Highway|Cir|Circle|Cswy|Causeway"
    r"|Ln|Lane|Pkwy|Parkway|Loop|Trl|Trail)\.?)"
    r",\s*([A-Za-z .'\-]{3,28}),\s*(?:OR|WA),?\s*(\d{5})\b", re.I)


#: The street, taken from the RIGHTMOST house number in the matched run: the page prints its rating and review
#: count immediately before its address ("3 396 reviews 4343 Collins Ave."), and only the last number is the house.
_STREET_TAIL = re.compile(
    r"(\d+[A-Za-z]?\s+(?:[NSEW]\.?W?\.?\s+)?(?:(?!reviews\b)[0-9A-Za-z.'\-]+\s+){0,3}"
    r"(?:St|Street|Ave|Avenue|Rd|Road|Dr|Drive|Blvd|Boulevard|Way|Ct|Court|Ter|Terrace|Pl|Place|Hwy|Highway|Cir|Circle|Cswy|Causeway"
    r"|Ln|Lane|Pkwy|Parkway|Loop|Trl|Trail)\.?)$",
    re.I)


def _walk(node):
    if isinstance(node, dict):
        yield node
        for v in node.values():
            for x in _walk(v):
                yield x
    elif isinstance(node, list):
        for v in node:
            for x in _walk(v):
                yield x


def ld_address(page):
    """(street, locality, postal) from the FIRST address object in the page's own JSON-LD blocks (a Choice or IHG
    property page publishes its own premises there even where its node type is not a Hotel), or blanks. Only
    ld+json blocks are read -- never the page's app state, which also carries nearby properties."""
    for m in _LD.finditer(page or ""):
        try:
            data = json.loads(m.group(1))
        except ValueError:
            continue
        for node in _walk(data):
            if node.get("streetAddress") and node.get("postalCode"):
                return (" ".join(str(node["streetAddress"]).split()),
                        " ".join(str(node.get("addressLocality") or "").split()),
                        "".join(ch for ch in str(node["postalCode"]) if ch.isdigit())[:5])
    return "", "", ""


def address_from_text(text):
    m = _ADDR_LINE.search(text or "")
    if not m:
        return "", "", ""
    street = " ".join(m.group(1).split())
    tail = _STREET_TAIL.search(street)
    if tail:
        street = " ".join(tail.group(1).split())
    return street, m.group(2).strip(), m.group(3)


#: PHOENIX (measured on the persisted Choice documents): a Choice property page carries no Hotel JSON-LD NAME the
#: reader keeps, but its own <h1> is the property's own name ("Cambria Hotel Phoenix Chandler - Fashion Center").
#: A route that now lands on the brand's SEARCH page ("2 hotels near Mesa, AZ, USA match your filters", "Hotels
#: Near Me - Choice Hotels") is a RETIRED ROUTE: it names no property, binds nothing, and is recorded as retired.
_H1 = re.compile(r"<h1[^>]*>(.*?)</h1>", re.S | re.I)
_SEARCH_PAGE = re.compile(r"hotels near\b|match your filters|^book .* hotels in|hotels near me", re.I)
_TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.S | re.I)


#: PHOENIX (measured on the persisted Choice documents): a Choice property page states its policy ONCE, in its own
#: "Pets" essential-details block -- "Pets Allowed: Yes General: Pets Are Allowed. Dogs Only. 50USD Per night ..."
#: -- while its ROOM cards carry per-room chips ("No Pets Allowed Only service animals are permitted"). A room chip
#: is a room feature, not the hotel's policy, and mixing the two made a pet-friendly hotel read as a refusal. When
#: the block is present it is the ONLY pet text kept.
_CHOICE_BLOCK = re.compile(r"\bPets\s+(Pets Allowed:\s*(?:Yes|No)\s+General:\s*.{0,420}?)"
                           r"(?=\s+(?:Good to know|Hotel alerts|Accessibility|Cancellation)\b|$)", re.I)


def choice_policy_block(text):
    m = _CHOICE_BLOCK.search(text or "")
    return " ".join(m.group(1).split()) if m else ""


def page_own_name(page):
    """(name, retired) from a brand property page's own <h1>, refusing the brand's search page."""
    title = " ".join(_html.unescape(re.sub(r"<[^>]+>", "", (_TITLE.findall(page) or [""])[0])).split())
    h1 = [" ".join(_html.unescape(re.sub(r"<[^>]+>", "", h)).split()) for h in _H1.findall(page)]
    h1 = [h for h in h1 if h]
    if _SEARCH_PAGE.search(title) or (h1 and _SEARCH_PAGE.search(h1[0])) or not h1:
        return "", bool(_SEARCH_PAGE.search(title) or (h1 and _SEARCH_PAGE.search(h1[0])))
    return h1[0], False


def town_of(route):
    m = re.search(r"choicehotels\.com/(?:oregon|washington)/([a-z-]+)/", route) or \
        re.search(r"ihg\.com/[a-z]+/hotels/us/en/([a-z-]+)/", route)
    return m.group(1) if m else ""


def targets():
    doc = json.load(open(DISCOVERY, encoding="utf-8"))
    seen, out = set(), []
    for r in sorted(doc.get("routes", []), key=lambda x: x["route"]):
        town = town_of(r["route"])
        # IHG's Kimpton routes carry the town inside the property slug ("hotel-monaco-portland-or").
        in_market = town in IN_MARKET or any(town.endswith("-%s-or" % t) or town.endswith("-%s-wa" % t)
                                             for t in IN_MARKET)
        if not in_market or r["route"] in seen:
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
            _own, _retired = page_own_name(page)
            if _retired:
                rec["route_retired_to_brand_search"] = True
                rec["n"], rec["st"], rec["ci"], rec["z"] = "", "", "", ""
                rec["address_basis"] = ""
                rec["pet_sentences"] = []
                rec["reparsed_from_persisted_document"] = True
                rows.append(rec)
                continue
            if not rec["n"] and _own:
                rec["n"], rec["name_basis"] = _own, "PAGE_OWN_H1"
            if addr.get("streetAddress"):
                rec["st"], rec["ci"] = addr["streetAddress"].strip(), (addr.get("addressLocality") or "").strip()
                rec["z"] = (addr.get("postalCode") or "").strip()[:5]
                rec["address_basis"] = "PAGE_OWN_JSON_LD"
            else:
                st, ci, z = address_from_text(text)
                rec["st"], rec["ci"], rec["z"] = st, ci, z
                rec["address_basis"] = "PAGE_OWN_ADDRESS_LINE" if st else ""
                if not st:
                    st, ci, z = ld_address(page)
                    if st:
                        rec["st"], rec["ci"], rec["z"] = st, ci, z
                        rec["address_basis"] = "PAGE_OWN_JSON_LD_ADDRESS"
            rec["ph"] = (ld.get("telephone") or "").strip() or rec.get("ph") or ""
            sents, seen_s = [], set()
            for m in _SENT.finditer(text):
                s = m.group(0).strip()
                if s.lower() in seen_s or len(sents) >= 8:
                    continue
                seen_s.add(s.lower())
                sents.append(s)
            _block = choice_policy_block(text) if "choicehotels.com" in (rec.get("u") or "") else ""
            if _block:
                rec["policy_block"] = _block
                sents = [_block]
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
    report["routes_retired_to_brand_search"] = [r.get("u") for r in rows if r.get("route_retired_to_brand_search")]
    report["names_from_page_own_h1"] = sum(1 for r in rows if r.get("name_basis") == "PAGE_OWN_H1")
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
        ("schema", "ptf-brand-page-reads/1.0"), ("work_order", WORK_ORDER), ("market_id", "portland-or"),
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
