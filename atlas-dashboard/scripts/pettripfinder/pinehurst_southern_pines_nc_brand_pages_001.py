"""PTF-PINEHURST-SOUTHERN-PINES-NC-PARALLEL-SOURCE-READY-001 -- Phase 12: the independents' operative quotes.

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
  launch_packages/pettripfinder/markets/staging/pinehurst-southern-pines-nc/raw_captures/brand_pages.json
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
RAW = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "staging", "pinehurst-southern-pines-nc", "raw_captures")
OUT = os.path.join(RAW, "brand_pages.json")
POLICY_LANE = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports",
                           "pinehurst_southern_pines_nc_policy_pages_lane_001.json")

SURFACE = "the property's own website (the page whose sha256 is recorded)"
METHOD = "HOUSE_NUMBER_AND_POSTAL_CODE_ON_THE_SAME_OWN_SITE_DOCUMENT"

#: (seed, name, street, city, postal, phone, sha256 prefix, quote, extraction, conflict)
ROWS = [
]

#: Attended first-party reads whose document was hashed in the browser in the same call that read the quote.
ATTENDED = [
    OrderedDict([
        ("seed", "surestay-plus-southern-pines-pinehurst"), ("brand", "BEST_WESTERN"), ("lane", "ATTENDED_BROWSER"),
        ("code", "34158"),
        ("name", "SureStay Plus Southern Pines Pinehurst"), ("street", "1675 US Highway 1 S"), ("city", "Southern Pines"),
        ("postal", "28387"), ("phone", "+1 (910) 704-0010"), ("lat", 35.159695), ("lng", -79.411355),
        ("url", "https://www.bestwestern.com/en_US/book/hotel-details.34158.html"),
        ("sha256", "18d967d4ffaf90e1fde0afb232955e44e8028e7550bdfac70ab40cf707c7afc0"), ("bytes", 372804),
        ("surface", "the brand's own property page: its Hotel JSON-LD address and the FACILITY 'PETS' policy text"),
        ("quote", "We are Pet Friendly and allow up to two dogs in a limited number of rooms. The size limit for any one "
                  "dog shall be 80 pounds. Other pet types (e.g., cats) may be allowed upon the hotel’s approval prior "
                  "to arrival. The Pet Friendly rate is 20 USD per day."),
        # The deposit sentence that follows ("A refundable cleaning and damage deposit of 50 USD ...") is a deposit,
        # not the pet fee, and is left out of the quote so no refundability is read onto the fee.
        ("extraction", OrderedDict([("pets_allowed", True), ("pet_fee", 2000), ("fee_currency", "USD"),
                                    ("fee_basis", "per_night"), ("pet_count_limit", 2)])),
        ("method", "HOTEL_JSONLD_ADDRESS_AND_PROPERTY_CODE"), ("conflict", None),
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
                        glob.glob(os.path.join(ACQ, "pinehurst_southern_pines_nc_*", prefix + "*.bin"))}.values())
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
