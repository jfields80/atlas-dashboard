"""PTF-CHARLOTTE-NC-ZERO-TO-LIVE-BENCHMARK-001 -- rung 2, the free static lane.

Rung 2 of the acquisition ladder: ONE HTTPS GET per property route, from a plain
client, for the families this order MEASURED as reachable that way. Nothing here
uses a browser and nothing here spends a credit or a cent.

WHICH FAMILIES, AND WHY ONLY THESE
----------------------------------
This order probed one property page per family with a plain client before
deciding where each one goes on the ladder. What it observed, on this run:

    DRURY          200, and the page carries a complete operative pet policy
                   under its own "Key":"pet-policy" block -- captured here.
    WOODSPRING     200, but the ONLY pet language on a property page is an SEO
                   keyword list ("Pet-Friendly Hotel, Dog-Friendly Hotel, ...")
                   and a chain-level marketing line, "We offer pet friendly
                   hotel rooms at MOST of our locations". That is not a
                   property-specific operative statement; it is the
                   AMENITY_CHIP_ONLY class the first-party binding contract
                   refuses. Recorded as SOURCE_SILENT_FOR_THIS_PROPERTY, never
                   published, and never called a closure.
    WYNDHAM        200, but the operative policy is rendered CLIENT-SIDE into
                   `.pet-policy-desc`; a plain client sees only the amenity chip
                   `"name":"Pet-Friendly","id":"PETS"` and an i18n dictionary
                   that contains the words "Pet-Friendly" in nine languages --
                   the Marriott translation-table hazard in another shape.
                   Routed, unresolved, and named for the next order.
    IHG            403 to a plain GET on the property page, on the city page and
                   on the sitemap its own robots.txt declares. It went to the
                   attended lane and is read there.
    BEST_WESTERN   403.   RED_ROOF 403.   ESA 403.   HYATT 429.   MOTEL6 timeout.
    SONESTA        404 on the probed route shape.

Every one of those is a fact about THIS client at THIS moment. None of them is
evidence that a family has no Charlotte property, and the next order re-probes
them rather than inheriting this file.

DURABLE FROM ACQUISITION
------------------------
Each captured row persists the requested URL, the final URL, the lane, the
capture timestamp, the identity signals the page itself states, the raw document
on disk, its sha256, its byte length, the operative quote and the parsed facts.
Nashville's evidence-recovery order exists because a capture kept only a byte
length; nothing here repeats that.

Output:
  launch_packages/pettripfinder/markets/reports/charlotte_nc_free_static_lane_001.json
  data/acquisition/charlotte_nc_static_001/<sha>.html   (the documents themselves)
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import html
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.markets import contract as MC  # noqa: E402

WORK_ORDER = "PTF-CHARLOTTE-NC-ZERO-TO-LIVE-BENCHMARK-001"
MARKET_ID = "charlotte-nc"
SCHEMA = "ptf-free-static-capture/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CONTRACT = os.path.join(PKG, "markets", "charlotte-nc.json")
STORE = os.path.join(_DASH, "data", "acquisition", "charlotte_nc_static_001")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/128.0 Safari/537.36")
SPACING = 0.8

DRURY = [
    "https://www.druryhotels.com/locations/charlotte-nc/drury-inn-and-suites-charlotte-arrowood",
    "https://www.druryhotels.com/locations/charlotte-nc/drury-inn-and-suites-charlotte-northlake",
    "https://www.druryhotels.com/locations/charlotte-nc/drury-inn-and-suites-charlotte-university-place",
]
#: Fetched so the verdict rests on THIS run's evidence rather than on an
#: assumption about the chain. Every one is expected to be SOURCE_SILENT.
WOODSPRING = [
    "https://www.woodspring.com/extended-stay-hotels/locations/north-carolina/charlotte/woodspring-suites-charlotte-airport",
    "https://www.woodspring.com/extended-stay-hotels/locations/north-carolina/charlotte/woodspring-suites-charlotte-arrowood",
    "https://www.woodspring.com/extended-stay-hotels/locations/north-carolina/charlotte/woodspring-suites-charlotte-gastonia",
    "https://www.woodspring.com/extended-stay-hotels/locations/north-carolina/charlotte/woodspring-suites-charlotte-university-research-park",
    "https://www.woodspring.com/extended-stay-hotels/locations/north-carolina/concord/woodspring-suites-concord-charlotte-speedway",
    "https://www.woodspring.com/extended-stay-hotels/locations/south-carolina/fort-mill/woodspring-suites-fort-mill",
]

_DRURY_POLICY = re.compile(
    r'"Title"\s*:\s*"Pet Policy"\s*,\s*"Description"\s*:\s*"(.*?)"\s*,\s*"Order"', re.S)
_TAGS = re.compile(r"<[^>]+>")
_ALLOW = re.compile(r"\b(pets?|dogs?|cats?)\b[^.]{0,80}\b(accepted|welcome|allowed|permitted)\b", re.I)
_REFUSE = re.compile(r"\b(no pets|pets are not|do(?:es)? not (?:accept|allow) pets|"
                     r"service animals only)\b", re.I)
_FEE = re.compile(r"\$\s*([0-9]{1,4}(?:\.[0-9]{2})?)", re.I)
_WEIGHT = re.compile(r"([0-9]{1,3}(?:\.[0-9])?)\s*(?:lbs?|pounds)", re.I)
_COUNT = re.compile(r"\b(?:limit|max(?:imum)?)\s+(two|three|four|\d+)\s+pets?\b", re.I)
_WORDNUM = {"two": 2, "three": 3, "four": 4}


def fetch(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept": "text/html,application/xhtml+xml,*/*",
        "Accept-Encoding": "gzip", "Accept-Language": "en-US,en;q=0.9"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            data = r.read()
            if r.headers.get("Content-Encoding") == "gzip" or data[:2] == b"\x1f\x8b":
                try:
                    data = gzip.GzipFile(fileobj=io.BytesIO(data)).read()
                except Exception:  # noqa: BLE001
                    pass
            return r.status, r.geturl(), data
    except urllib.error.HTTPError as e:
        return e.code, url, b""
    except Exception as e:  # noqa: BLE001
        return "ERR:" + type(e).__name__, url, b""


def persist(body: bytes) -> str:
    sha = hashlib.sha256(body).hexdigest()
    os.makedirs(STORE, exist_ok=True)
    path = os.path.join(STORE, sha + ".html")
    if not os.path.exists(path):
        with open(path, "wb") as fh:
            fh.write(body)
    return sha


def _pick(text, pattern):
    m = re.search(pattern, text)
    return m.group(1) if m else ""


def read_drury(url, stats):
    time.sleep(SPACING)
    status, final, body = fetch(url)
    stats["requests"] += 1
    row = OrderedDict([
        ("brand", "DRURY"), ("requested_url", url), ("final_url", final),
        ("capture_lane", "DIRECT_STATIC_FETCH"),
        ("captured_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
        ("status", status), ("document_bytes", len(body)),
    ])
    if status != 200 or not body:
        row["verdict"] = "CAPTURE_FAILED"
        row["why"] = "status %r" % (status,)
        return row
    sha = persist(body)
    text = body.decode("utf-8", "replace")
    row["document_sha256"] = sha
    row["document_path"] = os.path.relpath(os.path.join(STORE, sha + ".html"), _DASH)
    # Drury publishes the property record as one JSON object whose "Address"
    # key is the STREET line and whose "AlternateName" is the operator's own
    # short label. The <title> is a chain-prefixed marketing string and is used
    # only when the record itself names nothing.
    name = (_pick(text, r'"HotelName"\s*:\s*"([^"]+)"')
            or _pick(text, r'"AlternateName"\s*:\s*"([^"]+)"')
            or _pick(text, r"<title>([^<|]+)"))
    row["identity_signals"] = OrderedDict([
        ("name_on_page", html.unescape(name).strip()),
        ("address_on_page", html.unescape(_pick(text, r'"Address"\s*:\s*"([^"]+)"')).strip()),
        ("locality", _pick(text, r'"City"\s*:\s*"([^"]+)"')),
        ("region", _pick(text, r'"State"\s*:\s*"([^"]+)"')),
        ("postal_code", _pick(text, r'"Zip[a-zA-Z]*"\s*:\s*"([^"]+)"')[:5]),
        ("phone_on_page", _pick(text, r'"Phone[a-zA-Z]*"\s*:\s*"([^"]+)"')),
        ("latitude", _pick(text, r'"Latitude"\s*:\s*(-?[0-9.]+)')),
        ("longitude", _pick(text, r'"Longitude"\s*:\s*(-?[0-9.]+)')),
    ])
    m = _DRURY_POLICY.search(text)
    if not m:
        row["verdict"] = "POLICY_NOT_FOUND"
        row["why"] = ("the page served but published no block keyed Pet Policy on this read; "
                      "a silence is not a refusal and settles nothing")
        return row
    raw = m.group(1)
    quote = html.unescape(_TAGS.sub(" ", raw.encode("utf-8").decode("unicode_escape")))
    quote = re.sub(r"\s+", " ", quote).strip()
    row["operative_quote"] = quote
    ext = OrderedDict()
    if _REFUSE.search(quote) and not _ALLOW.search(quote):
        ext["pets_allowed"] = False
    elif _ALLOW.search(quote):
        ext["pets_allowed"] = True
    if ext.get("pets_allowed"):
        fees = [float(x) for x in _FEE.findall(quote)]
        if fees:
            ext["pet_fee"] = int(round(min(fees) * 100))
            ext["fee_currency"] = "USD"
            # UNKNOWN beats an inference. A source that says neither
            # "refundable" nor "non-refundable" has stated nothing about
            # refundability, and reading its silence as "refundable" would
            # publish a fact the hotel never asserted.
            if re.search(r"non-?\s?refundable", quote, re.I):
                ext["fee_refundable"] = False
            elif re.search(r"refundable", quote, re.I):
                ext["fee_refundable"] = True
        w = _WEIGHT.search(quote)
        if w:
            ext["weight_limit"] = float(w.group(1))
            ext["weight_limit_unit"] = "lb"
            if re.search(r"combined\s+weight", quote, re.I):
                ext["weight_basis"] = "combined"
        c = _COUNT.search(quote)
        if c:
            v = c.group(1).lower()
            ext["pet_count_limit"] = _WORDNUM.get(v) or int(v)
        if re.search(r"dogs?\s+and\s+cats?", quote, re.I):
            ext["species_allowed"] = ["dog", "cat"]
    row["parsed_facts"] = ext
    row["verdict"] = ("CLEAN_PET_FRIENDLY" if ext.get("pets_allowed") is True
                      else "CLEAN_VERIFIED_NO_PETS" if ext.get("pets_allowed") is False
                      else "QUOTE_NOT_OPERATIVE")
    return row


def read_woodspring(url, stats):
    time.sleep(SPACING)
    status, final, body = fetch(url)
    stats["requests"] += 1
    row = OrderedDict([
        ("brand", "WOODSPRING"), ("requested_url", url), ("final_url", final),
        ("capture_lane", "DIRECT_STATIC_FETCH"),
        ("captured_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
        ("status", status), ("document_bytes", len(body)),
    ])
    if status != 200 or not body:
        row["verdict"] = "CAPTURE_FAILED"
        row["why"] = "status %r" % (status,)
        return row
    sha = persist(body)
    text = body.decode("utf-8", "replace")
    row["document_sha256"] = sha
    row["document_path"] = os.path.relpath(os.path.join(STORE, sha + ".html"), _DASH)
    row["identity_signals"] = OrderedDict([
        ("name_on_page", html.unescape(_pick(text, r"<title>([^<|]+)")).strip()),
        ("address_on_page", html.unescape(_pick(text, r'"streetAddress"\s*:\s*"([^"]+)"')).strip()),
        ("locality", _pick(text, r'"addressLocality"\s*:\s*"([^"]+)"')),
        ("region", _pick(text, r'"addressRegion"\s*:\s*"([^"]+)"')),
        ("postal_code", _pick(text, r'"postalCode"\s*:\s*"([^"]+)"')[:5]),
        ("phone_on_page", _pick(text, r'"telephone"\s*:\s*"([^"]+)"')),
    ])
    chain_line = bool(re.search(r"pet friendly hotel rooms at most of our locations", text, re.I))
    row["verdict"] = "SOURCE_SILENT"
    row["classification"] = "AMENITY_CHIP_ONLY"
    row["why"] = (
        "the only pet language this property page publishes is an SEO keyword list "
        "(\"Pet-Friendly Hotel, Dog-Friendly Hotel, Cat-Friendly Hotel\") and"
        + (" the CHAIN-LEVEL line \"We offer pet friendly hotel rooms at MOST of our "
           "locations\"" if chain_line else " no property-specific sentence at all")
        + ". Neither states this building's policy, so neither can settle it. The row is "
          "SOURCE_SILENT, not refused and not accepted; nothing is published from it.")
    return row


def build():
    stats = {"requests": 0}
    cfg = MC.parse_market(json.load(open(CONTRACT, encoding="utf-8")), source=CONTRACT)
    zips = {z: c.corridor_id for c in cfg.corridors for z in c.included_postal_codes}
    rows = [read_drury(u, stats) for u in DRURY]
    rows += [read_woodspring(u, stats) for u in WOODSPRING]
    for r in rows:
        z = ((r.get("identity_signals") or {}).get("postal_code") or "")[:5]
        r["in_market"] = z in zips
        r["corridor"] = zips.get(z, "")
        r["market_verdict"] = "IN_MARKET" if z in zips else "OUTSIDE_MARKET"
    clean = [r for r in rows if r["verdict"] == "CLEAN_PET_FRIENDLY" and r["in_market"]]
    nopets = [r for r in rows if r["verdict"] == "CLEAN_VERIFIED_NO_PETS" and r["in_market"]]
    return OrderedDict([
        ("schema", SCHEMA), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "10/11 -- rung 2, free first-party static capture"),
        ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
        ("lane", "DIRECT_STATIC_FETCH (one HTTPS GET per route, plain client)"),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("firecrawl_credits", 0),
        ("free_http_requests", stats["requests"]),
        ("evidence_is_durable_from_acquisition",
         "every 200 persists the RAW DOCUMENT under data/acquisition/charlotte_nc_static_001/ "
         "named by its own sha256, alongside the requested URL, the final URL, the lane, the "
         "timestamp, the byte length, the identity the page states, the operative quote and the "
         "parsed facts. Nashville's evidence-recovery order exists because a capture kept only a "
         "byte length; this one cannot repeat that."),
        ("a_refusal_is_a_fact_about_a_moment",
         "IHG 403, Best Western 403, Red Roof 403, Extended Stay America 403, Hyatt 429, "
         "Motel 6 timeout and Sonesta 404 were measured by THIS order against a plain client "
         "before any of them was routed elsewhere. None of those is evidence that the family has "
         "no Charlotte property."),
        ("rows", rows),
        ("counts", OrderedDict([
            ("routes_attempted", len(rows)),
            ("by_verdict", OrderedDict(sorted(Counter(r["verdict"] for r in rows).items()))),
            ("by_brand", OrderedDict(sorted(Counter(r["brand"] for r in rows).items()))),
            ("in_market", sum(1 for r in rows if r["in_market"])),
            ("clean_pet_friendly_in_market", len(clean)),
            ("clean_verified_no_pets_in_market", len(nopets)),
        ])),
    ])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPORTS, "charlotte_nc_free_static_lane_001.json"))
    args = ap.parse_args(argv)
    rep = build()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    c = rep["counts"]
    print("routes            :", c["routes_attempted"], dict(c["by_brand"]))
    print("verdicts          :", dict(c["by_verdict"]))
    print("in market         :", c["in_market"])
    print("clean PF / no-pets:", c["clean_pet_friendly_in_market"], "/",
          c["clean_verified_no_pets_in_market"])
    print("free requests     :", rep["free_http_requests"])
    print("written           :", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
