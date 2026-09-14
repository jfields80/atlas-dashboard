"""PTF-BOONE-BLOWING-ROCK-NC-PARALLEL-SOURCE-READY-001 -- Phase 12: the independents' operative quotes.

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
  launch_packages/pettripfinder/markets/staging/boone-blowing-rock-nc/raw_captures/brand_pages.json
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
RAW = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "staging", "boone-blowing-rock-nc", "raw_captures")
OUT = os.path.join(RAW, "brand_pages.json")
POLICY_LANE = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports",
                           "boone_blowing_rock_nc_policy_pages_lane_001.json")

SURFACE = "the property's own website (the page whose sha256 is recorded)"
METHOD = "HOUSE_NUMBER_AND_POSTAL_CODE_ON_THE_SAME_OWN_SITE_DOCUMENT"

#: (seed, name, street, city, postal, phone, sha256 prefix, quote, extraction, conflict)
ROWS = [
    # pet-friendly
    ("meadowbrook-inn", "Meadowbrook Inn", "711 Main Street", "Blowing Rock", "28605", "1.828.295.4300", "4a16e6aaf163",
     "Our hotel features a limited number of pet friendly rooms that can only be reserved in advance by calling the "
     "hotel directly.",
     {"pets_allowed": True}, None),
    ("azalea-garden-inn", "Azalea Garden Inn", "793 Main Street", "Blowing Rock", "28605", "1.828.295.3272",
     "0ad07bda791d",
     "We know pets are part of the family, and we\u2019re delighted to welcome them at Azalea Garden Inn! A limited "
     "number of our accommodations are pet-friendly",
     {"pets_allowed": True}, None),
    ("mountainaire-inn", "Mountainaire Inn & Log Cabins", "827 Main Street", "Blowing Rock", "28605", "1.828.295.3272",
     "face797e84b6",
     "We know pets are part of the family, and we\u2019re delighted to welcome them at Mountainaire Inn & Log Cabins! A "
     "limited number of our accommodations are pet-friendly",
     {"pets_allowed": True}, None),
    ("blowing-rock-inn", "Blowing Rock Inn", "788 Main Street", "Blowing Rock", "28605", "1.828.295.7921", "3acfad02c138",
     "We know pets are part of the family, and we\u2019re delighted to welcome them at Blowing Rock Inn! A limited number "
     "of our accommodations are pet-friendly",
     {"pets_allowed": True}, None),
    # The lodge's own FAQ. "$40 plus tax per night" states an amount and a basis; the scope is unstated and left out.
    ("graystone-lodge", "Graystone Lodge", "2419 NC-105", "Boone", "28607", "828-264-4133", "943b93e05bed",
     "Yes, we offer pet-friendly rooms for an additional fee of $40 plus tax per night.",
     {"pets_allowed": True, "pet_fee": 4000, "fee_currency": "USD", "fee_basis": "per_night"}, None),
    # verified no-pets
    ("hidden-valley-motel", "Hidden Valley Motel", "8725 NC Hwy 105 South", "Boone", "28607", "(828) 963-4372",
     "7a7527773d80",
     "No pets on the premises, that includes being left in your vehicle",
     {"pets_allowed": False}, None),
]

#: No attended independent read this order.
ATTENDED = []


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
                        glob.glob(os.path.join(ACQ, "boone_blowing_rock_nc_*", prefix + "*.bin"))}.values())
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
