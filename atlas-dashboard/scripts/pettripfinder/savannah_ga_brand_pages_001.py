"""PTF-SAVANNAH-GA-PARALLEL-SOURCE-READY-001 -- Phase 12: the independents' and plain-client brands' operative quotes.

Every row below is ONE operative first-party statement chosen by review from a
document the static / policy-page lanes persisted, plus the Red Roof rows read
in the attended browser (whose documents were hashed in the same browser call).
For the persisted documents this builder PROVES each choice before it commits it:

  * the quote occurs verbatim (whitespace-collapsed) in the persisted document;
  * the property's own house number and postal code occur in that same document,
    so the read binds to the building by the page's OWN street identity;
  * the sha256 and byte length come from the document on disk, never typed.

A row that fails either proof raises and nothing is written. The capture helper
reads the result (``raw_captures/brand_pages.json``); the shared first-party
binding gate still decides whether each quote is operative.

Statements the shared reader does NOT read ("We do not allow pets of any kind",
"Pets are always welcome", "No, pets are strictly prohibited on our property",
"We cannot accomodate pets at this time", ...) are NOT here: they are held in the
final partition with their exact wording, never reworded.

Output:
  launch_packages/pettripfinder/markets/staging/savannah-ga/raw_captures/brand_pages.json
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
RAW = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "staging", "savannah-ga", "raw_captures")
OUT = os.path.join(RAW, "brand_pages.json")
POLICY_LANE = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports",
                           "savannah_ga_policy_pages_lane_001.json")

SURFACE = "the property's own website (the page whose sha256 is recorded)"
METHOD = "HOUSE_NUMBER_AND_POSTAL_CODE_ON_THE_SAME_OWN_SITE_DOCUMENT"

#: (seed, brand, name, street, city, postal, phone, sha256 prefix, quote, extraction, conflict)
ROWS = [
    # pet-friendly
    ("bellwether-house", "INDEPENDENT", "Bellwether House", "211 E Gaston Street", "Savannah", "31401", "646.397.9720",
     "b0f9934e3b60",
     "At Bellwether House, we welcome four-legged guests with open arms. Our pet-friendly rooms are thoughtfully "
     "appointed to ensure a comfortable stay for you and your furry companion. We allow dogs weighing 40 lbs or less. "
     "To guarantee availability and proper room assignment, all pet reservations must be made over the phone. $125 per "
     "night - only 1 pet allowed.",
     {"pets_allowed": True, "pet_fee": 12500, "fee_currency": "USD", "fee_basis": "per_night",
      "weight_limit": 40.0, "weight_limit_unit": "lb", "pet_count_limit": 1, "species_allowed": ["dog"]}, None),
    ("east-bay-inn", "INDEPENDENT", "East Bay Inn", "225 East Bay Street", "Savannah", "31401", "912-238-1225",
     "f8be4a73bd79", "We are a pet-friendly property!", {"pets_allowed": True}, None),
    ("foley-house-inn", "INDEPENDENT", "Foley House Inn", "14 West Hull Street", "Savannah", "31401", "(800) 647-3708",
     "d5342ed77854",
     "A pet friendly Savannah bed and breakfast? Yes! Just because you’re traveling doesn’t mean you have to leave "
     "your pets behind. Four-legged guests are always welcome at the Foley House Inn in the heart of the Savannah, "
     "Georgia Historic District.",
     {"pets_allowed": True}, None),
    # "one dog up to 50 lbs, or two dogs with a combined weight of 75 lbs" is two regimes; no weight or count is published.
    ("hotel-bardo", "INDEPENDENT", "Hotel Bardo Savannah", "700 Drayton Street", "Savannah", "31401", "912-238-5158",
     "796aea5cf055",
     "Hotel Bardo is a dog-friendly resort. Other animals are not permitted. We allow one dog up to 50 lbs, or two dogs "
     "with a combined weight of 75 lbs. There is an additional $200 non-refundable fee per stay.",
     {"pets_allowed": True, "pet_fee": 20000, "fee_currency": "USD", "fee_basis": "per_stay", "fee_refundable": False,
      "species_allowed": ["dog"]}, None),
    ("iris-garden-inn", "INDEPENDENT", "Iris Garden Inn", "347 Main Street", "Savannah", "31408", "(912) 777-5002",
     "985e2c03eae2",
     "Pets Pets allowed (dogs only) * Specific rooms only, restrictions apply * 2 per room (up to 110.23 lb)",
     {"pets_allowed": True, "pet_count_limit": 2, "species_allowed": ["dog"]}, None),
    ("woodspring-west-chatham", "WOODSPRING", "WoodSpring Suites Savannah West Chatham Parkway", "115 Woodspring Drive",
     "Savannah", "31405", "912-800-7973", "329e93a99e53",
     "Pets Allowed. Pet Charge 20 USD Per Pet,Per Night. Pet limit 2 Pet Per Room. Max 75 Pounds",
     {"pets_allowed": True, "pet_fee": 2000, "fee_currency": "USD", "fee_basis": "per_night", "fee_scope": "per_pet",
      "pet_count_limit": 2, "weight_limit": 75.0, "weight_limit_unit": "lb"}, None),
    ("drury-plaza-pooler", "DRURY", "Drury Plaza Hotel Savannah Pooler", "500 East US-80", "Pooler", "31322",
     "912-330-0400", "af3c576d5665",
     "Dogs and cats accepted. Rooms with pets will be charged a daily fee of $50 per room plus tax. Service animals are "
     "free of charge. Limit of two pets per room with a combined weight of 80 pounds.",
     {"pets_allowed": True, "pet_fee": 5000, "fee_currency": "USD", "fee_basis": "per_night", "fee_scope": "per_room",
      "pet_count_limit": 2, "weight_limit": 80.0, "weight_limit_unit": "lb", "weight_basis": "combined",
      "species_allowed": ["cat", "dog"]}, None),
    # verified no-pets
    ("the-douglas", "INDEPENDENT", "The Douglas", "14 E Oglethorpe Ave", "Savannah", "31401", "(912) 236-1484",
     "1a3099aacf33", "No, pets are not allowed on the premises.", {"pets_allowed": False}, None),
]

#: Red Roof property pages (attended same-origin fetch): the property record's own
#: ``description`` (name), ``street1`` / ``postalCode`` beside its ``propertyId``, and the
#: page's own pet paragraph. The payload's canonical-JSON sha256 is checked. The payload's
#: ``n`` for rri583 and rri1206 is a neighbouring "RediClean" label and its ``ci`` for rri1397
#: is a nearby-cities list; the property record's own description and city (read beside the
#: propertyId in the same documents) are used instead.
REDROOF_PAYLOAD = ("redroof_rows.json", "2d18909854ae1f2e02d4516841a6db02fd155d222ea0ece05b73c85fe46c6562")
REDROOF_RECORD = {
    "rri583": ("Red Roof Inn & Suites Savannah Airport", "Pooler"),
    "rri1209": ("Red Roof Inn Savannah - Richmond Hill/ I-95", "Richmond Hill"),
    "rri1253": ("Red Roof Inn Savannah - Southside/Midtown", "Savannah"),
    "rri1206": ("Red Roof PLUS+ & Suites Savannah - I-95", "Savannah"),
    "rri1397": ("Red Roof Inn Savannah North I-95 - Port Wentworth", "Port Wentworth"),
}


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
    """The document's URL. A page whose server re-renders on every request (Foley House Inn's pet page carries a
    changing nonce) persists under a new sha256 each time the lane reads it; the reviewed document is still the one
    on disk, and its URL is the ONE lane page that serves the same pet sentence."""
    if sha in urls:
        return urls[sha]
    # the lane's pet sentences end at a full stop, so the head is the quote's first sentence without its stop
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
                        glob.glob(os.path.join(ACQ, "savannah_ga_*", prefix + "*.bin"))}.values())
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
        url = _url_for(sha, quote, urls, by_sentence)
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
