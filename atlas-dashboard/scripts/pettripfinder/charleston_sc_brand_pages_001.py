"""PTF-CHARLESTON-SC-PARALLEL-SOURCE-READY-001 -- Phase 13: the independents' and plain-client brands' operative quotes.

Cloned from the Savannah GA builder. Every row below is ONE operative first-party
statement chosen by review from a document the static / policy-page lanes
persisted, plus the Red Roof rows read in the attended browser (whose documents
were hashed in the same browser call). For the persisted documents this builder
PROVES each choice before it commits it:

  * the quote occurs verbatim (whitespace-collapsed) in the persisted document;
  * the property's own house number and postal code occur in that same document,
    so the read binds to the building by the page's OWN street identity;
  * the sha256 and byte length come from the document on disk, never typed.

A row that fails either proof raises and nothing is written. The capture helper
reads the result (``raw_captures/brand_pages.json``); the shared first-party
binding gate still decides whether each quote is operative.

Statements the shared reader does NOT read are NOT here: they are held in the
final partition with their exact wording, never reworded.

Output:
  launch_packages/pettripfinder/markets/staging/charleston-sc/raw_captures/brand_pages.json
"""
from __future__ import annotations

import glob
import hashlib
import html as H
import json
import os
import re
import sys
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
ACQ = os.path.join(_DASH, "data", "acquisition")
RAW = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "staging", "charleston-sc", "raw_captures")
OUT = os.path.join(RAW, "brand_pages.json")
POLICY_LANE = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports",
                           "charleston_sc_policy_pages_lane_001.json")

SURFACE = "the property's own website (the page whose sha256 is recorded)"
METHOD = "HOUSE_NUMBER_AND_POSTAL_CODE_ON_THE_SAME_OWN_SITE_DOCUMENT"

#: (seed, brand, name, street, city, postal, phone, sha256 prefix, quote, extraction, conflict)
ROWS = [
    # pet-friendly
    ("john-rutledge-house-inn", "INDEPENDENT", "John Rutledge House Inn", "116 Broad Street", "Charleston", "29401", "",
     "b02fedbc4aa2", "We offer dog-friendly accommodations for an additional fee of $40 per day.",
     {"pets_allowed": True, "pet_fee": 4000, "fee_currency": "USD", "fee_basis": "per_night", "species_allowed": ["dog"]},
     None),
    ("kings-courtyard-inn", "INDEPENDENT", "Kings Courtyard Inn", "198 King Street", "Charleston", "29401", "",
     "a33b7b0b9b1c", "We offer dog-friendly accommodations for an additional fee of $40 per day.",
     {"pets_allowed": True, "pet_fee": 4000, "fee_currency": "USD", "fee_basis": "per_night", "species_allowed": ["dog"]},
     None),
    ("the-vendue", "INDEPENDENT", "The Vendue", "19 Vendue Range", "Charleston", "29401", "",
     "038606cc91fa", "The Vendue welcomes dogs for a one-time pet fee per stay.",
     {"pets_allowed": True, "species_allowed": ["dog"]}, None),
    # "a one time, nonrefundable fee of $50 per pet, per day" states two bases at once; no fee is published.
    ("barksdale-house-inn", "INDEPENDENT", "Barksdale House Inn", "27 George Street", "Charleston", "29401", "",
     "23196593505c", "Dogs and litter-trained cats are welcome!",
     {"pets_allowed": True, "species_allowed": ["cat", "dog"]}, None),
    ("drury-plaza-north-charleston", "DRURY", "Drury Plaza Hotel North Charleston", "2934 West Montague",
     "North Charleston", "29418", "843-938-1503", "91742b8b3b2a",
     "Dogs and cats accepted. Rooms with pets will be charged a daily fee of $50 per room plus tax.",
     {"pets_allowed": True, "pet_fee": 5000, "fee_currency": "USD", "fee_basis": "per_night", "fee_scope": "per_room",
      "species_allowed": ["cat", "dog"]}, None),
    # verified no-pets
    ("the-dewberry", "INDEPENDENT", "The Dewberry Charleston", "334 Meeting Street", "Charleston", "29403", "",
     "ebd7cfc29824", "We apologize for any inconvenience, but pets are not permitted.", {"pets_allowed": False}, None),
]

#: The URL each reviewed document was read from, where the lane's re-renders make the sentence ambiguous.
DOCUMENT_URL = {
    "john-rutledge-house-inn": "https://johnrutledgehouseinn.com/faq/",
    "kings-courtyard-inn": "https://kingscourtyardinn.com/faq-hotel-king-street-charleston-sc/",
    "the-vendue": "https://www.thevendue.com/faq/",
    "barksdale-house-inn": "https://www.barksdalehouse.com/policies/",
    "the-dewberry": "https://thedewberrycharleston.com/policies/",
    "drury-plaza-north-charleston": "https://www.druryhotels.com/locations/charleston-sc/drury-plaza-hotel-north-charleston",
}

#: Red Roof property pages (attended same-origin fetch): the property record's own
#: ``description`` (name), ``street1`` / ``postalCode`` beside its ``propertyId``, and the
#: page's own pet paragraph. The payload's canonical-JSON sha256 is checked.
REDROOF_PAYLOAD = ("redroof_rows.json", "2b81992ec9889cb2dae042447fc5e58051d5acc720a3988a528e529544fd5a72")
REDROOF_RECORD = {
    "rri142": ("Red Roof Inn North Charleston Coliseum", "North Charleston"),
    "rri242": ("Red Roof PLUS+ Mt Pleasant - Patriots Point", "Mount Pleasant"),
}


def _plain(body):
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", body, flags=re.S | re.I)
    t = H.unescape(re.sub(r"<[^>]+>", " ", t))
    return " ".join(t.split())


def _url_by_sha():
    if not os.path.exists(POLICY_LANE):
        return {}, []
    doc = json.load(open(POLICY_LANE, encoding="utf-8"))
    out, by_sentence = {}, []
    for r in doc["rows"]:
        for p in r["pages"]:
            if p.get("sha256"):
                out.setdefault(p["sha256"], p["final_url"] or p["url"])
            by_sentence.append((p["final_url"] or p["url"], " ".join(" ".join(p["pet_sentences"]).split())))
    return out, by_sentence


def _url_for(sha, quote, urls, by_sentence):
    """The document's URL. A page whose server re-renders on every request persists under a new
    sha256 each time the lane reads it; the reviewed document is still the one on disk, and its URL
    is the ONE lane page that serves the same pet sentence."""
    if sha in urls:
        return urls[sha]
    head = " ".join(quote.split()).split(".")[0][:40]
    hits = sorted({u for u, s in by_sentence if head and head in s})
    return hits[0] if len(hits) == 1 else None


def redroof_rows():
    rows = json.load(open(os.path.join(RAW, REDROOF_PAYLOAD[0]), encoding="utf-8"))
    got = hashlib.sha256(json.dumps(rows, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
    if got != REDROOF_PAYLOAD[1]:
        raise SystemExit("red roof payload digest %s != %s" % (got, REDROOF_PAYLOAD[1]))
    out = []
    for r in rows:
        name, city = REDROOF_RECORD[r["c"]]
        quote = r["p"]
        ext = OrderedDict([("pets_allowed", True), ("pet_count_limit", 2), ("weight_limit", 80.0),
                           ("weight_limit_unit", "lb"), ("species_allowed", ["cat", "dog"])])
        out.append(OrderedDict([
            ("seed", r["c"]), ("brand", "RED_ROOF"), ("lane", "ATTENDED_BROWSER"), ("code", r["c"]),
            ("name", name), ("street", r["st"]), ("city", city), ("postal", r["z"][:5]), ("phone", r["ph"]),
            ("url", r["u"]), ("sha256", r["h"]), ("bytes", r["b"]),
            ("surface", "the property's own page, its pet paragraph and property record"),
            ("quote", quote), ("extraction", ext), ("method", "PROPERTY_RECORD_ADDRESS_AND_PROPERTY_ID"),
            ("conflict", None),
        ]))
    return out


def build():
    urls, by_sentence = _url_by_sha()
    rows = []
    for seed, brand, name, street, city, postal, phone, prefix, quote, ext, conflict in ROWS:
        files = sorted({os.path.basename(f): f for f in
                        glob.glob(os.path.join(ACQ, "charleston_sc_*", prefix + "*.bin"))}.values())
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
        # CHARLESTON: the Charming Inns sites (John Rutledge House, Kings Courtyard, Wentworth Mansion) serve the same
        # pet sentence and re-render with a new sha256 on every read, so the sentence alone can name two URLs; the page
        # the reviewed document was read from is stated explicitly.
        url = DOCUMENT_URL.get(seed) or _url_for(sha, quote, urls, by_sentence)
        if not url:
            raise SystemExit("%s: no lane row names the URL of %s" % (seed, sha))
        rows.append(OrderedDict([
            ("seed", seed), ("brand", brand), ("lane", "DIRECT_STATIC_FETCH"),
            ("name", name), ("street", street), ("city", city), ("postal", postal), ("phone", phone),
            ("url", url), ("sha256", sha), ("bytes", len(raw)), ("surface", SURFACE),
            ("quote", quote), ("extraction", OrderedDict(ext)), ("method", METHOD), ("conflict", conflict),
        ]))
    return rows + redroof_rows()


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
