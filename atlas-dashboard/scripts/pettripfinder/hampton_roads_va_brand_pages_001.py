"""PTF-HAMPTON-ROADS-VA-PARALLEL-SOURCE-READY-001 -- Phase 13: the independents' and plain-client brands' operative quotes.

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
  launch_packages/pettripfinder/markets/staging/hampton-roads-va/raw_captures/brand_pages.json
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
RAW = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "staging", "hampton-roads-va", "raw_captures")
OUT = os.path.join(RAW, "brand_pages.json")
POLICY_LANE = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports",
                           "hampton_roads_va_policy_pages_lane_001.json")

SURFACE = "the property's own website (the page whose sha256 is recorded)"
METHOD = "HOUSE_NUMBER_AND_POSTAL_CODE_ON_THE_SAME_OWN_SITE_DOCUMENT"

#: (seed, brand, name, street, city, postal, phone, sha256 prefix, quote, extraction, conflict)
ROWS = [
    # pet-friendly
    ("woodspring-suites-yorktown-newport-news", "WOODSPRING", "WoodSpring Suites Yorktown Newport News",
     "2420 George Washington Memorial Highway", "Yorktown", "23693", "", "cde59b948a8a",
     "Pets allowed. A Non refundable pet registration fee of 50.00 USD and 10.00 USD per night. Max 75 lbs, 2 dogs per "
     "room. No cats.",
     # two charges (a registration fee and a nightly charge) -- no single fee is published
     {"pets_allowed": True, "weight_limit": 75.0, "weight_limit_unit": "lb", "pet_count_limit": 2,
      "species_allowed": ["dog"]}, None),
    # verified no-pets
    ("angies-guest-cottage", "INDEPENDENT", "Angie’s Guest Cottage Bed & Breakfast", "302 24th Street", "Virginia Beach",
     "23451", "", "ed3d77aa5886", "Sorry, no pets are permitted.", {"pets_allowed": False}, None),
    ("coastal-hotel-and-suites", "INDEPENDENT", "Coastal Hotel & Suites Virginia Beach Oceanfront", "2015 Atlantic Avenue",
     "Virginia Beach", "23451", "", "dc91c1a35bf6", "No pets allowed", {"pets_allowed": False}, None),
    ("sandcastle-resort", "INDEPENDENT", "Sandcastle Resort", "1307 Atlantic Avenue", "Virginia Beach", "23451", "",
     "aad8ad8587fd", "Pets not allowed", {"pets_allowed": False}, None),
    ("the-oceanfront-inn", "INDEPENDENT", "The Oceanfront Inn", "2901 Atlantic Avenue", "Virginia Beach", "23451", "",
     "5a1d2c2661c2", "No pets accepted", {"pets_allowed": False}, None),
]

#: The URL each reviewed document was read from, where the lane's re-renders make the sentence ambiguous.
DOCUMENT_URL = {
}

#: Red Roof property pages (attended same-origin fetch): the property record's own
#: ``description`` (name), ``street1`` / ``postalCode`` beside its ``propertyId``, and the
#: page's own pet paragraph. The payload's canonical-JSON sha256 is checked.
REDROOF_PAYLOAD = ("redroof_rows.json", "1f253438c4b709029a966039b60ed703a7c9cbb9248721b1afdf11d9a77134d7")
#: HAMPTON ROADS: the property record's own city, trimmed (two records carry a trailing blank: "Newport News ").
REDROOF_CITY = {
}
#: HAMPTON ROADS: two property records state no property name at all (their ``description`` field is the "RediClean(R)"
#: programme label). The name is the brand's own route (``/property/va/<city>/rri<code>``: a Red Roof Inn property in that
#: city) and, for rri1392, the page's own location label ("Virginia Beach \u2013 Seaside").
REDROOF_NAME = {
    "rri1392": "Red Roof Inn Virginia Beach - Seaside",
    "rri1371": "Red Roof Inn Newport News",
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
        if r.get("outside") or r.get("s") != 200:
            continue
        name, city = REDROOF_NAME.get(r["c"], r["n"]), REDROOF_CITY.get(r["c"], (r.get("ci") or "").strip())
        # The page's own policy paragraph: Red Roof's "One, well-behaved domestic pet ..." sentence, or HomeTowne
        # Studios' refusal ("Sorry, no pets allowed." where the page states it; otherwise its only sentence).
        accept = [l for l in r["pets"] if l.startswith("One, well-behaved domestic pet")]
        refuse = [l for l in r["pets"] if l.startswith("Sorry, no pets allowed")] or \
                 [l for l in r["pets"] if l.startswith("This location does not accept pets")]
        if accept:
            quote = accept[0]
            # "One, well-behaved domestic pet (cat or dog) Stays Free! ... Up to 2 pets allowed per room. Second pet $15/
            # night, not to exceed 7 nights or $105 per pet per stay. Pet not to exceed 80 pounds." -- a second-pet charge
            # with a cap is not one fee; no fee is published.
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
OMNI_PAYLOAD = None


def omni_rows():
    if OMNI_PAYLOAD is None:
        return []
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


#: HAMPTON ROADS: independents' own pages read in the attended browser (their sites refused the plain client or failed its
#: TLS handshake), each document hashed in the same browser call as its pet lines and its house-number / postal-code test.
#: (seed, brand, name, street, city, postal, url, sha256, bytes, quote, extraction, number-and-zip-on-document)
BROWSER_READ_ROWS = [
    ("ambassadors-inn-and-suites", "INDEPENDENT", "Ambassadors Inn & Suites", "716 21st Street", "Virginia Beach", "23451",
     "https://www.ambassadorsvb.com/amenities.php", "ec4781415a2280ba3514edb91c094de4c31b172b08fc739385f7989725def6d2", 14073,
     "Pets Welcome (Dogs only)", {"pets_allowed": True, "species_allowed": ["dog"]}, True),
]


def browser_read_rows():
    out = []
    for seed, brand, name, street, city, postal, url, sha, nbytes, quote, ext, on_doc in BROWSER_READ_ROWS:
        if not on_doc:
            raise SystemExit("%s: the browser read did not find house number and postal code on the document" % seed)
        out.append(OrderedDict([
            ("seed", seed), ("brand", brand), ("lane", "ATTENDED_BROWSER"), ("name", name), ("street", street),
            ("city", city), ("postal", postal), ("phone", ""), ("url", url), ("sha256", sha), ("bytes", nbytes),
            ("surface", "the property's own website, read in the attended browser (document hashed in the same call)"),
            ("quote", quote), ("extraction", OrderedDict(ext)), ("method", METHOD), ("conflict", None),
        ]))
    return out


def build():
    urls, by_sentence = _url_by_sha()
    rows = []
    for seed, brand, name, street, city, postal, phone, prefix, quote, ext, conflict in ROWS:
        files = sorted({os.path.basename(f): f for f in
                        glob.glob(os.path.join(ACQ, "hampton_roads_va_*", prefix + "*.bin"))}.values())
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
    return rows + redroof_rows() + omni_rows() + browser_read_rows()


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
