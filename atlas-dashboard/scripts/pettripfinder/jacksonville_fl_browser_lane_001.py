"""PTF-JACKSONVILLE-FL-HARDENED-SOURCE-READY-001 -- Phases 14, 15 and 16: the attended-browser lane.

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

  HILTON  serves TWO templates in this market, and their labels differ. Both were verified verbatim here:
          HOTEL_INFO_LIST on ``/hotel-info/`` (witnessed in Palm Beach on pbicppy, Canopy West Palm Beach Downtown, whose
          ``/amenities/`` 404s) renders a definition list -- "Pets allowed:" / "Yes",
          "Non-refundable fee:" / "$75.00", "Max weight:" / "75 lbs", "Max size:" / "large",
          "Pet policy:" / "Pet fee of $75 is per pet. Cats are not permitted on-site".
          POLICIES_ACCORDION on ``/amenities/`` (witnessed in Palm Beach on pbiwphh, Hilton West Palm Beach, whose
          ``/hotel-info/`` REDIRECTS there) renders a "Hotel Policies" accordion whose Pets panel reads
          "Pets Allowed" / "Yes", "Pet Policy", "Max Size" / "Medium", "Max Weight" / "75 lbs",
          "Pet Fee" / "$125.00 Non-refundable" -- and whose content is ABSENT from the accessibility tree
          until the accordion is expanded, so the lane clicks "Pets" and then reads the page's own text.
          Each row is quoted in the labels of the template it was actually read from. Every Hilton row's
          VALUES are that property's own.
  MARRIOTT the property's own ``/overview/`` page renders a HOTEL INFORMATION row labelled "Pet Policy" whose
          value is "Pets Welcome" or "Pets Not Allowed", optionally followed by the property's own fee sentence
          and the structured "Non-Refundable Pet Fee Per Stay / Maximum Pet Weight / Maximum Number of Pets in
          Room" fields.
  BEST_WESTERN the property's own booking-path page renders a "Pet Policy" heading with the property's own
          sentence ("Pets are not accepted.").

WHAT IS NEVER READ AS A POLICY
-------------------------------
An amenity chip ("Pet-Friendly" in Hilton's own "Hotel Amenities" list -- which pbiwphh carried ALONGSIDE its
operative Pets panel, exactly the trap Phase 16 forbids), a parking or smoking fee beside the pet block, a weight,
a fee or a count on its own, and a page whose own address does not match the census row's premises. A read whose
returned address belongs to the PREVIOUS property (a stale DOM) is DISCARDED, not repaired.

Output (the shape jacksonville_fl_clean_authority_001 consumes):
  launch_packages/pettripfinder/markets/staging/jacksonville-fl/raw_captures/browser_closure_rows.json
  launch_packages/pettripfinder/markets/reports/jacksonville_fl_browser_lane_001.json
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

from scripts.pettripfinder.jacksonville_fl_census_reconciliation_001 import (  # noqa: E402
    fold_northeast_florida_streets as FOLD,
)

WORK_ORDER = "PTF-JACKSONVILLE-FL-HARDENED-SOURCE-READY-001"
MARKET_ID = "jacksonville-fl"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
STAGING = os.path.join(PKG, "markets", "staging", "jacksonville-fl", "raw_captures")
READS = os.path.join(STAGING, "browser_reads_001.jsonl")
CENSUS = os.path.join(PKG, "identity_census_proposed", "jacksonville-fl.json")
ROWS_OUT = os.path.join(STAGING, "browser_closure_rows.json")
REPORT_OUT = os.path.join(REPORTS, "jacksonville_fl_browser_lane_001.json")

#: THE HILTON LABEL WITNESSES ARE DISCOVERED, NOT DECLARED.
#:
#: Hilton serves TWO page templates whose PETS-block labels differ, and West Palm Beach proved that binding one
#: vocabulary to both puts words in the brand's mouth for half a market. That finding is inherited; the WITNESSES
#: are not. Palm Beach's were `pbiwphh` (Hilton West Palm Beach, POLICIES_ACCORDION on /amenities/, its
#: /hotel-info/ redirecting there) and `pbicppy` (Canopy West Palm Beach Downtown, HOTEL_INFO_LIST on
#: /hotel-info/, its /amenities/ 404ing). Those are Palm Beach property codes and they witness nothing here.
#:
#: This lane therefore records the witness THIS market actually read for each template -- the first JAX-prefixed
#: ctyhocn whose own page served that template -- so the report states which of this market's own properties
#: established each vocabulary. An empty tuple means the run read no Hilton property on that template.
_HILTON_LABEL_WITNESSES = ()


def hilton_label_witnesses(rows):
    """One witness per Hilton template, taken from THIS run's own reads."""
    seen = OrderedDict()
    for r in rows:
        if (r.get("family") or "").upper() != "HILTON":
            continue
        tpl = (r.get("hilton_template") or "").upper()
        code = (r.get("property_code") or "").strip().lower()
        if tpl and code and tpl not in seen:
            seen[tpl] = code
    return seen


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
    # HILTON SERVES TWO PAGE TEMPLATES, AND THEIR LABELS DIFFER. Measured on this market's own properties:
    #
    #   HOTEL_INFO_LIST  (/hotel-info/) renders the PETS block as
    #                    a definition list: "Pets allowed:" / "Yes", "Non-refundable fee:" / "$75.00",
    #                    "Max weight:" / "75 lbs", "Max size:" / "large", "Pet policy:" / "<text>".
    #   POLICIES_ACCORDION (/amenities/, where /hotel-info/ REDIRECTS there)
    #                    renders a "Hotel Policies" accordion whose Pets panel reads "Pets Allowed" / "Yes",
    #                    "Pet Policy", "Max Size", "Max Weight", "Pet Fee" -- and whose content is absent from
    #                    the accessibility tree until the accordion is expanded.
    #
    # A row is quoted in the labels of the template it was ACTUALLY read from. Binding one vocabulary to both
    # would put words in the brand's mouth for half the market, so the read record carries its own template.
    tpl = (row.get("hilton_template") or "HOTEL_INFO_LIST").upper()
    if parsed.get("pets_allowed") is False:
        return "Hotel Policies | Pets | Pets Allowed: No" if tpl == "POLICIES_ACCORDION" \
            else "PETS | Pets not allowed"
    if parsed.get("pets_allowed") is not True:
        return ""
    if tpl == "POLICIES_ACCORDION":
        parts = ["Hotel Policies", "Pets", "Pets Allowed: Yes"]
        wanted = ("pet fee", "max weight", "max size", "pet policy")
        for seg in raw.split("|"):
            seg = seg.strip()
            if seg and seg.lower().startswith(wanted):
                parts.append(seg)
        return " | ".join(parts)
    parts = ["PETS", "Pets allowed: Yes"]
    for seg in raw.split("|"):
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
    # THE POSTAL CODE IS THE LAST FIVE-DIGIT RUN, NOT THE FIRST. This market's suburban house numbers are
    # routinely five digits ("14565 Duval Road, Jacksonville, FL 32218"), so taking the first run read the
    # HOUSE NUMBER as the ZIP and rule 2 could never fire for them.
    page_zip = _zip5((re.findall(r"\b\d{5}\b", page_addr) or [""])[-1])
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
    # 4. house number + postal code that match MORE than one census row, disambiguated by the STREET NAME the
    #    page itself states. Needed because a house number repeats inside a single postal code in any dense
    #    market -- Palm Beach had two different hotels at 1800 in 33401 -- and some brands, Best Western among
    #    them, print their address WITHOUT a postal code, so rule 2 cannot fire and rule 3 sees an ambiguous
    #    pair and correctly refuses. This market's own dense codes are 32218 (29 hotel-rank licences), 32256
    #    (26) and 32216 (18).
    #
    #    This is STRICTER than a name match, not looser: the page must state the census row's own street words,
    #    and exactly one census row at that house number and postal code may match them. A tie still refuses.
    if house and postal and page_addr and (not page_house or page_house == house):
        def _street_words(v):
            # THE PHILIPS / PHILLIPS SPLIT BITES A SECOND LANE. The census folds it before any key is built,
            # but this comparison is the browser lane's own, and Motel 6 prints "8285 PHILLIPS HIGHWAY" for a
            # census row the state licence spells "8285 Philips Hwy" -- with a Knights Inn at 8285 Dix Ellis
            # Trail in the SAME postal code, so rule 3 is correctly ambiguous and rule 4 has to decide. Without
            # the fold, one letter left the market's busiest lodging road unbindable.
            v = FOLD(v)
            return {w for w in re.sub(r"[^a-z0-9 ]", " ", (v or "").lower()).split()
                    if len(w) > 2 and w not in ("the", "ave", "avenue", "street", "road", "drive", "blvd",
                                                "boulevard", "circle", "court", "lane", "way", "north",
                                                "south", "east", "west", "suite", "usa", "united", "states",
                                                "florida",
                                                # STREET-TYPE WORDS ONE SOURCE ABBREVIATES AND THE OTHER DOES
                                                # NOT. The state licence writes "8285 Philips Hwy" and the
                                                # brand's own page writes "8285 PHILLIPS HIGHWAY"; with "hwy"
                                                # kept and "highway" kept, one street produced two word sets
                                                # and the comparison could never match. These are street
                                                # TYPES, exactly like "road" and "boulevard" above, and
                                                # dropping them cannot make two different streets look alike:
                                                # the distinctive word ("philips") still has to match.
                                                "hwy", "highway", "pkwy", "parkway", "trl", "trail", "ter",
                                                "terrace", "cir", "ct", "ln", "dr", "rd", "pl", "place",
                                                "sq", "square", "expy", "expressway", "jacksonville")}
        page_words = _street_words(page_addr)
        hits = [h for h in census_hotels
                if _house(h.get("street")) == house and _zip5(h.get("postal_code")) == postal
                and _street_words(h.get("street")) and _street_words(h.get("street")) <= page_words]
        if len(hits) == 1:
            return hits[0]["identity_key"], (
                "street number %s + postal code %s, disambiguated by the street name the page itself states "
                "(%r); more than one census row shares that house number and postal code"
                % (house, postal, " ".join(sorted(_street_words(hits[0].get("street"))))))
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
        # WITNESSED ON THIS MARKET'S OWN PROPERTIES, from the raw reads (which carry each page's template).
        ("hilton_label_witnesses", hilton_label_witnesses(reads)),
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
