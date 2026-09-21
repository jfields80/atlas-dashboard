"""PTF-FORT-LAUDERDALE-FL-HARDENED-SOURCE-READY-001 -- Phases 14, 15 and 16: the attended-browser lane.

WHAT THIS LANE IS
-----------------
The committed route table sends MARRIOTT and HILTON to a PAID browser provider and EXCLUDES HYATT and
BEST_WESTERN from its paid lanes on cost. This order has no authorization for new paid spend, so the lane it
actually exercises is the SUPPORTED ATTENDED BROWSER (claude-in-chrome): navigate to the property's own page on
the brand's own host, then read the page's own accessibility tree.

  * No paid provider was called. Bright Data was not used.
  * Akamai was never bypassed. When marriott.com or hilton.com served a challenge or an Access Denied page, the
    lane PAUSED and retried later in a bounded window; a still-denied row is recorded as denied, never forced.
  * No browser-JS exfiltration and no local relay. Only navigate + the accessibility tree.

WHY THE QUOTES READ THE WAY THEY DO
------------------------------------
Two shapes of first-party policy block were read, and each is quoted in the page's OWN label vocabulary:

  HILTON  the property's own ``/hotel-info/`` page renders a PETS block as label/value pairs. The labels were
          verified VERBATIM by a full page-text read on two properties (fllbmdt Bahia Mar and fllcyhx Hampton
          Cypress Creek): "Pets allowed: Yes" / "Pets not allowed", "Non-refundable fee: $75.00",
          "Max weight: 75 lbs", "Max size: medium", "Pet policy: <text>". Every other Hilton row's VALUES are
          that property's own page values, read from its own accessibility tree.
  MARRIOTT the property's own ``/overview/`` page renders a HOTEL INFORMATION row labelled "Pet Policy" whose
          value is "Pets Welcome" or "Pets Not Allowed", optionally followed by the property's own fee sentence
          and the structured "Non-Refundable Pet Fee Per Stay / Maximum Pet Weight / Maximum Number of Pets in
          Room" fields.
  BEST_WESTERN the property's own booking-path page renders a "Pet Policy" heading with the property's own
          sentence ("Pets are not accepted.").

WHAT IS NEVER READ AS A POLICY
-------------------------------
An amenity chip ("Pet-Friendly"), a parking or smoking fee that happens to sit beside the pet block, a weight,
a fee or a count on its own, and a page whose own address does not match the census row's premises. A read whose
returned address belongs to the PREVIOUS property (a stale DOM) is DISCARDED, not repaired.

Output (the shape fort_lauderdale_fl_clean_authority_001 consumes):
  launch_packages/pettripfinder/markets/staging/fort-lauderdale-fl/raw_captures/browser_closure_rows.json
  launch_packages/pettripfinder/markets/reports/fort_lauderdale_fl_browser_lane_001.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-FORT-LAUDERDALE-FL-HARDENED-SOURCE-READY-001"
MARKET_ID = "fort-lauderdale-fl"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
STAGING = os.path.join(PKG, "markets", "staging", "fort-lauderdale-fl", "raw_captures")
READS = os.path.join(STAGING, "browser_reads_001.jsonl")
CENSUS = os.path.join(PKG, "identity_census", "fort-lauderdale-fl.json")
ROWS_OUT = os.path.join(STAGING, "browser_closure_rows.json")
REPORT_OUT = os.path.join(REPORTS, "fort_lauderdale_fl_browser_lane_001.json")

#: The Hilton PETS-block labels, verified verbatim by a full page-text read on two properties.
_HILTON_LABEL_WITNESSES = ("fllbmdt", "fllcyhx")


def _load(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _house(street):
    m = re.match(r"\s*(\d+)", street or "")
    return m.group(1) if m else ""


def _zip5(v):
    return "".join(ch for ch in str(v or "") if ch.isdigit())[:5]


def compose_quote(row):
    """The property's own policy block, in the page's own label vocabulary.

    The labels come from the brand's own page (see the module docstring); the VALUES are this property's own.
    Returns "" when the read produced no operative statement.
    """
    fam, parsed = row.get("family"), (row.get("parsed") or {})
    raw = row.get("operative_quote") or ""
    if row.get("read_outcome") in ("REJECTED_STALE_DOM_ADDRESS_MISMATCH", "CHALLENGE_DENIED_AKAMAI_ACCESS_DENIED",
                                   "NAVIGATION_FAILED_ERROR_PAGE", "AMENITY_CHIP_ONLY_NOT_OPERATIVE",
                                   "IDENTITY_BOUND_POLICY_SOURCE_SILENT",
                                   # an EXCLUDED row publishes nothing, not even the refusal its page states
                                   "IDENTITY_READ_ROW_EXCLUDED_AS_TIMESHARE"):
        return ""
    if fam != "HILTON":
        return raw
    if parsed.get("pets_allowed") is False:
        return "PETS | Pets not allowed"
    if parsed.get("pets_allowed") is not True:
        return ""
    parts = ["PETS", "Pets allowed: Yes"]
    tail = raw.split("|")
    for seg in tail:
        seg = seg.strip()
        if seg.startswith("$"):
            parts.append("Non-refundable fee: %s" % seg)
        elif re.match(r"^\d+\s*lbs$", seg, re.I):
            parts.append("Max weight: %s" % seg)
        elif seg.lower().startswith("max size"):
            parts.append(seg[0].upper() + seg[1:])
        elif seg.lower().startswith("pet policy"):
            parts.append(seg)
    return " | ".join(parts)


def bind(row, census_hotels):
    """The census identity this read belongs to, and how it was bound. Never a name alone."""
    code = (row.get("property_code") or "").strip().lower()
    street = row.get("census_street") or ""
    postal = _zip5(row.get("census_postal"))
    page_addr = row.get("page_address_line") or ""
    page_zip = _zip5((re.findall(r"\b\d{5}\b", page_addr) or [""])[0])
    house = _house(street)
    page_house = _house(page_addr)

    # 1. the brand's own property code on the brand's own page, matched to a census row carrying that code
    if code:
        hits = [h for h in census_hotels if (h.get("property_code") or "").lower() == code]
        if len(hits) == 1:
            return hits[0]["identity_key"], "BRAND_PROPERTY_CODE %s on the brand's own page" % code
    # 2. the page's own house number + postal code, matched to exactly one census row
    if page_house and page_zip:
        hits = [h for h in census_hotels
                if _house(h.get("street")) == page_house and _zip5(h.get("postal_code")) == page_zip]
        if len(hits) == 1:
            return hits[0]["identity_key"], ("the page's own street number %s + postal code %s"
                                             % (page_house, page_zip))
    # 3. the census row this queue entry was built from (street + ZIP), when the page agrees on the house number
    if house and postal and (not page_house or page_house == house):
        hits = [h for h in census_hotels
                if _house(h.get("street")) == house and _zip5(h.get("postal_code")) == postal]
        if len(hits) == 1:
            return hits[0]["identity_key"], ("the queue row's street number %s + postal code %s, with the page's "
                                             "own address agreeing" % (house, postal))
    return "", "UNBOUND"


def build():
    census = _load(CENSUS, {}) or {}
    hotels = census.get("hotels") or []
    reads = []
    with open(READS, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                reads.append(json.loads(line))

    rows, unbound, discarded = [], [], []
    for r in reads:
        quote = compose_quote(r)
        outcome = "READ" if quote else (r.get("read_outcome") or "NO_OPERATIVE_STATEMENT")
        key, basis = bind(r, hotels)
        rec = OrderedDict([
            ("seq", r.get("seq")),
            ("family", r.get("family")),
            ("property_code", r.get("property_code")),
            ("identity_key", key),
            ("binding", basis),
            ("requested_url", r.get("requested_url")),
            ("final_url", r.get("final_url")),
            ("capture_method", r.get("capture_method")),
            ("provider", "claude-in-chrome (supported attended browser; no paid provider, no relay, "
                         "no browser-JS exfiltration, Akamai not bypassed)"),
            ("captured_at", r.get("captured_at")),
            ("page_title", r.get("page_title")),
            ("page_address_line", r.get("page_address_line")),
            ("census_street", r.get("census_street")),
            ("census_postal", r.get("census_postal")),
            ("full_premises_match", r.get("full_premises_match")),
            ("outcome", outcome),
            ("operative_quote", quote),
            ("quote_byte_length", len(quote.encode("utf-8"))),
            ("transcription_sha256", _sha(json.dumps(
                [r.get("requested_url"), r.get("final_url"), r.get("page_title"), r.get("page_address_line"),
                 quote, r.get("parsed")], sort_keys=True, ensure_ascii=False))),
            ("parsed_facts", r.get("parsed") or {}),
            ("source_class", r.get("source_class")),
            ("note", r.get("note", "")),
        ])
        if outcome != "READ":
            discarded.append(rec)
        if not key:
            unbound.append(rec)
        rows.append(rec)

    read_rows = [r for r in rows if r["outcome"] == "READ" and r["identity_key"]]
    by_family = Counter(r["family"] for r in rows)
    reads_by_family = Counter(r["family"] for r in read_rows)
    denied = [r for r in rows if r["outcome"] == "CHALLENGE_DENIED_AKAMAI_ACCESS_DENIED"]

    doc = OrderedDict([
        ("schema", "ptf-attended-browser-lane/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("phase", "14 + 15 + 16 -- attended-browser acquisition, paced, with durable evidence"),
        ("provider", "claude-in-chrome (supported attended browser)"),
        ("paid_provider_calls", 0), ("usd_spent", 0.0),
        ("akamai_bypassed", False),
        ("browser_js_exfiltration_used", False),
        ("local_relay_used", False),
        ("hilton_label_witnesses", list(_HILTON_LABEL_WITNESSES)),
        ("attempts", len(rows)),
        ("attempts_by_family", OrderedDict(sorted(by_family.items()))),
        ("reads", len(read_rows)),
        ("reads_by_family", OrderedDict(sorted(reads_by_family.items()))),
        ("challenge_denied", len(denied)),
        ("unbound", len(unbound)),
        ("rows", rows),
    ])
    return doc, rows


def main(argv=None):
    ap = argparse.ArgumentParser()
    args = ap.parse_args(argv)
    doc, rows = build()
    os.makedirs(STAGING, exist_ok=True)
    with open(ROWS_OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(OrderedDict([("schema", "ptf-browser-closure-rows/1.0"), ("work_order", WORK_ORDER),
                               ("market_id", MARKET_ID), ("rows", rows)]), fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    os.makedirs(REPORTS, exist_ok=True)
    with open(REPORT_OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("attempts", doc["attempts"], "reads", doc["reads"], "denied", doc["challenge_denied"],
          "unbound", doc["unbound"])
    print("attempts by family:", json.dumps(doc["attempts_by_family"]))
    print("reads by family   :", json.dumps(doc["reads_by_family"]))
    for r in rows:
        if r["outcome"] == "READ" and not r["identity_key"]:
            print("  UNBOUND READ:", r["family"], r["property_code"], r["census_street"], r["census_postal"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
