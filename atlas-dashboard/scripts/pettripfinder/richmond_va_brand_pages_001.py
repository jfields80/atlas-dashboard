"""PTF-RICHMOND-VA-PARALLEL-SOURCE-READY-001 -- Phase 13: the independents' and plain-client brands' operative quotes.

Cloned from the Charleston SC builder (itself from Savannah GA). Every row below is ONE operative first-party
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
  launch_packages/pettripfinder/markets/staging/richmond-va/raw_captures/brand_pages.json
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
RAW = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "staging", "richmond-va", "raw_captures")
OUT = os.path.join(RAW, "brand_pages.json")
POLICY_LANE = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports",
                           "richmond_va_policy_pages_lane_001.json")

SURFACE = "the property's own website (the page whose sha256 is recorded)"
METHOD = "HOUSE_NUMBER_AND_POSTAL_CODE_ON_THE_SAME_OWN_SITE_DOCUMENT"

#: (seed, brand, name, street, city, postal, phone, sha256 prefix, quote, extraction, conflict)
ROWS = [
    # pet-friendly
    ("woodspring-suites-ashland-richmond-north", "WOODSPRING", "WoodSpring Suites Ashland-Richmond North",
     "11530 Lakeridge Pkwy", "Ashland", "23005", "", "e5f6d937b700",
     "Pets allowed. A Non refundable pet registration fee of 50.00 USD and 10.00 USD per night per pet. Max 75 lbs, "
     "2 dogs per room. No cats.",
     # two charges (a registration fee and a nightly charge) -- no single fee is published
     {"pets_allowed": True, "weight_limit": 75.0, "weight_limit_unit": "lb", "pet_count_limit": 2,
      "species_allowed": ["dog"]}, None),
    ("woodspring-suites-richmond-airport", "WOODSPRING", "WoodSpring Suites Richmond Airport", "4615 Williamsburg Rd.",
     "Richmond", "23231", "", "a0ea844233a8",
     "Pets Allowed. Pet Charge 10 USD Per Pet,Per Night. Non-Refundable deposit of 50 USD is required Per Stay. Pet "
     "limit 2 Pet Per Room. Max 75 Pounds. No cats.",
     {"pets_allowed": True, "pet_fee": 1000, "fee_currency": "USD", "fee_basis": "per_night", "fee_scope": "per_pet",
      "weight_limit": 75.0, "weight_limit_unit": "lb", "pet_count_limit": 2}, None),
    ("drury-plaza-hotel-richmond", "DRURY", "Drury Plaza Hotel Richmond", "11049 West Broad Street", "Glen Allen",
     "23060", "", "dae6e61f4546",
     "Dogs and cats accepted. Rooms with pets will be charged a daily fee of $65 before tax for one pet and $75 before "
     "tax for 2 pets in the room.",
     # a fee that depends on the number of pets -- no single fee is published
     {"pets_allowed": True, "species_allowed": ["cat", "dog"]}, None),
    ("quirk-hotel-richmond", "INDEPENDENT", "Quirk Hotel Richmond", "201 West Broad Street", "Richmond", "23220", "",
     "1d4dd47b23ae",
     "We welcome dogs! There is a one time $75 charge, per stay and a maximum of 2 dogs per room.",
     {"pets_allowed": True, "pet_fee": 7500, "fee_currency": "USD", "fee_basis": "per_stay", "pet_count_limit": 2,
      "species_allowed": ["dog"]}, None),
    ("the-commonwealth", "INDEPENDENT", "The Commonwealth", "901 Bank Street", "Richmond", "23219", "", "9bab8d79c6d9",
     "Our 2nd and 3rd floors are designated as dog friendly, and to make our furry guests comfortable we offer a treat "
     "gift upon check-in, plush doggy beds upon request, and a door hanger to alert staff that your pet is in the room. "
     "Directly across the street is Capitol Square, a perfect place to let your pooch walk and unwind. We require that "
     "dogs weigh no more than 40 pounds, and assess a $100 pet fee per stay.",
     {"pets_allowed": True, "pet_fee": 10000, "fee_currency": "USD", "fee_basis": "per_stay", "weight_limit": 40.0,
      "weight_limit_unit": "lb", "species_allowed": ["dog"]}, None),
    ("the-henry-clay-inn", "INDEPENDENT", "The Henry Clay Inn", "114 N Railroad Avenue", "Ashland", "23005", "",
     "785834dfa177",
     "The Henry Clay Inn is a pet-friendly hotel. A $50 fee per pet will be charged.",
     # the fee's basis (per night or per stay) is not stated -- no fee is published
     {"pets_allowed": True}, None),
    # Linden Row Inn is NOT here: its own FAQ ("Linden Row Inn has a small number of pet-friendly rooms available for
    # reservation by direct booking only.") reads as an acceptance, but the census binds the identity to its Best Western
    # (WorldHotels Distinctive) route, whose page says only "Pets may be accepted. Please contact the hotel for full
    # details." The sealed-package writer refuses a read from another host than the census route (INVALID_ROUTE); the row
    # is held on the Best Western read and the own-site sentence is recorded in the final report.
    ("brentwood-inn-richmond-south", "INDEPENDENT", "Brentwood Inn", "2125 Willis Road", "Richmond", "23237", "",
     "d1da057e1b43", "Pets Are Allowed: Yes Pet Charges: 20$ Per Pet Per Night",
     {"pets_allowed": True, "pet_fee": 2000, "fee_currency": "USD", "fee_basis": "per_night", "fee_scope": "per_pet"},
     None),
    # verified no-pets
    ("the-boulevard-inn", "INDEPENDENT", "The Boulevard Inn", "1 North Arthur Ashe Boulevard", "Richmond", "23220", "",
     "d29e049c3ab8", "No pets allowed.", {"pets_allowed": False}, None),
    ("diamond-inn-and-suites", "INDEPENDENT", "Diamond Inn & Suites", "1600 Robin Hood Road", "Richmond", "23220", "",
     "a787497d8ec2", "Pets are not allowed.", {"pets_allowed": False}, None),
]

#: The URL each reviewed document was read from, where the lane's re-renders make the sentence ambiguous.
DOCUMENT_URL = {
}

#: Red Roof property pages (attended same-origin fetch): the property record's own
#: ``description`` (name), ``street1`` / ``postalCode`` beside its ``propertyId``, and the
#: page's own pet paragraph. The payload's canonical-JSON sha256 is checked.
REDROOF_PAYLOAD = ("redroof_rows.json", "f90633414f0794b06f06f549aa313bcea9a4f458ffe6c1f560e646cfc37b9cea")
#: RICHMOND: the property record's own city, except where it states a postal-facility alias. Red Roof
#: Richmond - Airport/Sandston's record writes "Richmond IAP Byrd Field" (the airport's post-office name for
#: 23150); the HomeTowne Studios in the same building's other wing writes "Sandston", which is used.
REDROOF_CITY = {
    "rri1405": "Sandston",
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
    if REDROOF_PAYLOAD[1] is None:
        return []
    rows = json.load(open(os.path.join(RAW, REDROOF_PAYLOAD[0]), encoding="utf-8"))
    got = hashlib.sha256(json.dumps(rows, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
    if got != REDROOF_PAYLOAD[1]:
        raise SystemExit("red roof payload digest %s != %s" % (got, REDROOF_PAYLOAD[1]))
    out = []
    for r in rows:
        name, city = r["n"], REDROOF_CITY.get(r["c"], (r.get("ci") or "").strip())
        # The page's own policy paragraph: Red Roof's "One, well-behaved domestic pet ..." sentence, or HomeTowne
        # Studios' refusal ("Sorry, no pets allowed." where the page states it; otherwise its only sentence).
        accept = [l for l in r["pets"] if l.startswith("One, well-behaved domestic pet")]
        refuse = [l for l in r["pets"] if l.startswith("Sorry, no pets allowed")] or \
                 [l for l in r["pets"] if l.startswith("This location does not accept pets")]
        if accept:
            quote = accept[0]
            ext = OrderedDict([("pets_allowed", True), ("pet_count_limit", 2), ("weight_limit", 80.0),
                               ("weight_limit_unit", "lb"), ("species_allowed", ["cat", "dog"])])
        elif refuse:
            quote = refuse[0]
            ext = OrderedDict([("pets_allowed", False)])
        else:
            continue
        out.append(OrderedDict([
            ("seed", r["c"]), ("brand", "RED_ROOF"), ("lane", "ATTENDED_BROWSER"), ("code", r["c"].lower()),
            ("name", name), ("street", r["st"]), ("city", city), ("postal", r["z"][:5]), ("phone", r["ph"]),
            ("url", r["u"]), ("sha256", r["h"]), ("bytes", r["b"]),
            ("surface", "the property's own page, its pet paragraph and property record"),
            ("quote", quote), ("extraction", ext), ("method", "PROPERTY_RECORD_ADDRESS_AND_PROPERTY_ID"),
            ("conflict", None),
        ]))
    return out


#: RICHMOND: Omni Richmond Hotel's own page (attended same-origin fetch; omnihotels.com refused the plain client): the
#: page's property record (propertyCode RICRIC, street, city, zipCode) and its own FAQ answer on pets, hashed in the same
#: browser call. The payload's canonical-JSON sha256 is checked.
OMNI_PAYLOAD = ("omni_rows.json", "73f226a0816424c9b7e041992961a7a6a651837d9831055c2ad6cfa9145682c7")


def omni_rows():
    rows = json.load(open(os.path.join(RAW, OMNI_PAYLOAD[0]), encoding="utf-8"))
    got = hashlib.sha256(json.dumps(rows, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
    if got != OMNI_PAYLOAD[1]:
        raise SystemExit("omni payload digest %s != %s" % (got, OMNI_PAYLOAD[1]))
    out = []
    for r in rows:
        quote = ("Yes, Omni Richmond Hotel is a pet friendly hotel for dogs up to 25 pounds. There is a one-time "
                 "non-refundable pet fee of $150 per reservation.")
        if quote not in r["p"]:
            raise SystemExit("omni: the quote is not verbatim in the page's own FAQ answer")
        ext = OrderedDict([("pets_allowed", True), ("species_allowed", ["dog"]), ("weight_limit", 25.0),
                           ("weight_limit_unit", "lb"), ("pet_fee", 15000), ("fee_currency", "USD"),
                           ("fee_basis", "per_stay"), ("fee_refundable", False)])
        out.append(OrderedDict([
            ("seed", r["c"].lower()), ("brand", "OMNI"), ("lane", "ATTENDED_BROWSER"), ("code", r["c"].lower()),
            ("name", r["n"]), ("street", r["st"]), ("city", r["ci"]), ("postal", r["z"][:5]), ("phone", r["ph"]),
            ("url", r["u"]), ("sha256", r["h"]), ("bytes", r["b"]),
            ("surface", "the property's own page, its FAQ answer on pets and property record"),
            ("quote", quote), ("extraction", ext), ("method", "PROPERTY_RECORD_ADDRESS_AND_PROPERTY_CODE"),
            ("conflict", None),
        ]))
    return out


def build():
    urls, by_sentence = _url_by_sha()
    rows = []
    for seed, brand, name, street, city, postal, phone, prefix, quote, ext, conflict in ROWS:
        files = sorted({os.path.basename(f): f for f in
                        glob.glob(os.path.join(ACQ, "richmond_va_*", prefix + "*.bin"))}.values())
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
        # A page whose server re-renders on every read can name two URLs by its sentence alone; the page the reviewed
        # document was read from is then stated explicitly (DOCUMENT_URL).
        url = DOCUMENT_URL.get(seed) or _url_for(sha, quote, urls, by_sentence)
        if not url:
            raise SystemExit("%s: no lane row names the URL of %s" % (seed, sha))
        rows.append(OrderedDict([
            ("seed", seed), ("brand", brand), ("lane", "DIRECT_STATIC_FETCH"),
            ("name", name), ("street", street), ("city", city), ("postal", postal), ("phone", phone),
            ("url", url), ("sha256", sha), ("bytes", len(raw)), ("surface", SURFACE),
            ("quote", quote), ("extraction", OrderedDict(ext)), ("method", METHOD), ("conflict", conflict),
        ]))
    return rows + redroof_rows() + omni_rows()


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
