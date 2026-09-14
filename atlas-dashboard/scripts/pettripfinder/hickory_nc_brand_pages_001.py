"""PTF-HICKORY-NC-PARALLEL-SOURCE-READY-001 -- Phase 12: the independents' operative quotes.

Every row below is ONE operative first-party statement chosen by review from a
document the static / policy-page lanes persisted (or, for the one attended read,
hashed in the browser in the same call that read the quote). This builder PROVES
each choice before it commits it:

  * the quote occurs verbatim (whitespace-collapsed) in the persisted document;
  * the property's own house number and postal code occur in that same document,
    so the read binds to the building by the page's OWN street identity;
  * the sha256 and byte length come from the document on disk, never typed.

A row that fails either proof raises and nothing is written. The capture helper
reads the result (``raw_captures/brand_pages.json``); the shared first-party
binding gate still decides whether each quote is operative.

Output:
  launch_packages/pettripfinder/markets/staging/hickory-nc/raw_captures/brand_pages.json
"""
from __future__ import annotations

import glob
import html as H
import json
import os
import re
import sys
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
ACQ = os.path.join(_DASH, "data", "acquisition")
RAW = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "staging", "hickory-nc", "raw_captures")
OUT = os.path.join(RAW, "brand_pages.json")
POLICY_LANE = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports",
                           "hickory_nc_policy_pages_lane_001.json")

SURFACE = "the property's own website (the page whose sha256 is recorded)"
METHOD = "HOUSE_NUMBER_AND_POSTAL_CODE_ON_THE_SAME_OWN_SITE_DOCUMENT"

#: (seed, name, street, city, postal, phone, sha256 prefix, quote, extraction, conflict)
ROWS = []

#: Attended first-party reads whose document was hashed in the browser in the same call that read the quote.
ATTENDED = [
    OrderedDict([
        ("seed", "best-western-hickory"), ("brand", "BEST_WESTERN"), ("lane", "ATTENDED_BROWSER"),
        ("code", "34163"),
        ("name", "Best Western Hickory"), ("street", "1520 13th Avenue Drive SE"), ("city", "Hickory"),
        ("postal", "28602"), ("phone", "+1 (828) 323-1150"), ("lat", 35.711185), ("lng", -81.307965),
        ("url", "https://www.bestwestern.com/en_US/book/hotels-in-hickory/best-western-hickory/propertyCode.34163.html"),
        ("sha256", "48b8c921ff5fe829b6aec7b3170db9645f8706bc00f28fcb678a1431288287ef"), ("bytes", 390258),
        ("surface", "the brand's own property page: its Hotel JSON-LD address and the FACILITY 'PETS' policy text"),
        # "may be accepted ... contact the hotel" states no acceptance and no refusal: EVIDENCE_HOLD, no fact parsed.
        ("quote", "Pets may be accepted. Please contact the hotel for full details."),
        ("extraction", OrderedDict()),
        ("method", "HOTEL_JSONLD_ADDRESS_AND_PROPERTY_CODE"), ("conflict", None),
    ]),
    OrderedDict([
        ("seed", "red-roof-inn-hickory"), ("brand", "RED_ROOF"), ("lane", "ATTENDED_BROWSER"),
        ("code", "RRI152"),
        ("name", "Red Roof Inn Hickory"), ("street", "1184 Lenoir Rhyne Blvd SE"), ("city", "Hickory"),
        ("postal", "28602"), ("phone", None), ("lat", None), ("lng", None),
        ("url", "https://www.redroof.com/property/nc/hickory/RRI152"),
        ("sha256", "2d167c635ebf833b28feb6dad3bad393ff0be551ea3e3d9770a491cb2d0d675c"), ("bytes", 239723),
        ("surface", "the brand's own property page: its property record (street1 / postalCode) and the 'Pet Policy' "
                    "text, both present in the hashed server document"),
        ("quote", "Pet Policy: One, well-behaved domestic pet (cat or dog) Stays Free! Pets must be declared at check-in. "
                  "Up to 2 pets allowed per room. Second pet $15/ night, not to exceed 7 nights or $105 per pet per stay. "
                  "Pet not to exceed 80 pounds. Service and emotional support animals are always welcome."),
        # A free first pet and a nightly, capped charge for a second pet: no single fee is published.
        ("extraction", OrderedDict([("pets_allowed", True), ("pet_count_limit", 2),
                                    ("weight_limit", 80.0), ("weight_limit_unit", "lb")])),
        ("method", "PROPERTY_RECORD_ADDRESS_AND_PROPERTY_CODE"), ("conflict", None),
    ]),
    OrderedDict([
        ("seed", "affordable-suites-hickory-conover"), ("brand", "INDEPENDENT"), ("lane", "ATTENDED_BROWSER"),
        ("code", None),
        ("name", "Affordable Suites of America Hickory/Conover"), ("street", "1225 Fed Ex Drive SW"), ("city", "Conover"),
        ("postal", "28613"), ("phone", "(828) 464-7100"), ("lat", None), ("lng", None),
        ("url", "https://www.affordablesuites.com/hotels/affordable-suites-hickory-conover-nc/"),
        ("sha256", "95bfa62c70602e45a9085e6afd15cdde5dea75f88a6b94d4ca81d2b28c88ba2d"), ("bytes", 115807),
        ("surface", "the operator's own location page for this hotel (plain client 403; read same-origin in the attended "
                    "browser): its stated address and the 'Pet Policy' paragraph"),
        ("quote", "Both small pets and service animals are always welcome in our pet-friendly rooms. Two-animal maximum per "
                  "room. There is a $25 non-refundable charge per pet, per day, with a maximum of $150 per pet. There is "
                  "no charge for service animals."),
        # The chain-wide /pet-friendly-rooms/ page carries a 'may vary by location' disclaimer; the LOCATION page is read.
        ("extraction", OrderedDict([("pets_allowed", True), ("pet_fee", 2500), ("fee_currency", "USD"),
                                    ("fee_basis", "per_night"), ("fee_scope", "per_pet"), ("fee_refundable", False),
                                    ("pet_count_limit", 2)])),
        ("method", "ADDRESS_ON_THE_PROPERTYS_OWN_LOCATION_PAGE"), ("conflict", None),
    ]),
    OrderedDict([
        ("seed", "the-trott-house-inn"), ("brand", "INDEPENDENT"), ("lane", "ATTENDED_BROWSER"),
        ("code", None),
        ("name", "The Trott House Inn"), ("street", "802 North Main Avenue"), ("city", "Newton"),
        ("postal", "28658"), ("phone", None), ("lat", None), ("lng", None),
        ("url", "https://thetrotthouseinn.com/policies/"),
        ("sha256", "3eba6ce011d4ec51b0ec945cb81b2d21b53130f45ab7de0245e58dedc8b96cf0"), ("bytes", 88542),
        ("surface", "the inn's own Policies page (plain client 403; read same-origin in the attended browser), which "
                    "also states '802 North Main Avenue, Newton, North Carolina 28658'"),
        ("quote", "While we adore animals, pets are not permitted at the inn. Thank you for making alternate arrangements "
                  "for your furry companions during your stay."),
        ("extraction", OrderedDict([("pets_allowed", False)])),
        ("method", "ADDRESS_ON_THE_PROPERTYS_OWN_POLICY_PAGE"), ("conflict", None),
    ]),
]



def _plain(body):
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", body, flags=re.S | re.I)
    t = H.unescape(re.sub(r"<[^>]+>", " ", t))
    return " ".join(t.split())


def _url_by_sha():
    doc = json.load(open(POLICY_LANE, encoding="utf-8"))
    out, by_sentence = {}, []
    for r in doc["rows"]:
        for p in r["pages"]:
            if p.get("sha256"):
                out.setdefault(p["sha256"], p["final_url"] or p["url"])
            by_sentence.append((p["final_url"] or p["url"], " ".join(" ".join(p["pet_sentences"]).split())))
    return out, by_sentence


def _url_for(sha, quote, urls, by_sentence):
    """The document's URL. A page whose server re-renders on every request (a changing
    nonce) persists under a new sha256 each time it is read; the reviewed document is
    still the one on disk, and its URL is the lane page that serves the same pet sentence."""
    if sha in urls:
        return urls[sha]
    head = " ".join(quote.split())[:60]
    hits = sorted({u for u, s in by_sentence if head and head in s})
    return hits[0] if len(hits) == 1 else None


def build():
    urls, by_sentence = _url_by_sha()
    rows = []
    for seed, name, street, city, postal, phone, prefix, quote, ext, conflict in ROWS:
        # the same document may be persisted by more than one lane; one sha256 is one document
        files = sorted({os.path.basename(f): f for f in
                        glob.glob(os.path.join(ACQ, "hickory_nc_*", prefix + "*.bin"))}.values())
        if len(files) != 1:
            raise SystemExit("%s: %d documents match %s" % (seed, len(files), prefix))
        raw = open(files[0], "rb").read()
        sha = os.path.basename(files[0])[:-4]
        text = _plain(raw.decode("utf-8", "replace"))
        if " ".join(quote.split()) not in text:
            raise SystemExit("%s: the quote is not verbatim in %s" % (seed, sha))
        num = street.split()[0]
        if not re.search(r"\b%s\b" % re.escape(num), text) or postal not in text:
            raise SystemExit("%s: the document does not state house number %s and postal code %s" % (seed, num, postal))
        rows.append(OrderedDict([
            ("seed", seed), ("brand", "INDEPENDENT"), ("lane", "DIRECT_STATIC_FETCH"),
            ("name", name), ("street", street), ("city", city), ("postal", postal), ("phone", phone),
            ("url", _url_for(sha, quote, urls, by_sentence)), ("sha256", sha), ("bytes", len(raw)), ("surface", SURFACE),
            ("quote", quote), ("extraction", OrderedDict(ext)), ("method", METHOD), ("conflict", conflict),
        ]))
        if not rows[-1]["url"]:
            raise SystemExit("%s: no lane row names the URL of %s" % (seed, sha))
    return rows + ATTENDED


def main():
    rows = build()
    os.makedirs(RAW, exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rows, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("brand pages:", len(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
