"""PTF-OUTER-BANKS-NC-PARALLEL-SOURCE-READY-001 -- Phase 12: the independents' operative quotes.

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
  launch_packages/pettripfinder/markets/staging/outer-banks-nc/raw_captures/brand_pages.json
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
RAW = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "staging", "outer-banks-nc", "raw_captures")
OUT = os.path.join(RAW, "brand_pages.json")
POLICY_LANE = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports",
                           "outer_banks_nc_policy_pages_lane_001.json")

SURFACE = "the property's own website (the page whose sha256 is recorded)"
METHOD = "HOUSE_NUMBER_AND_POSTAL_CODE_ON_THE_SAME_OWN_SITE_DOCUMENT"

#: (seed, name, street, city, postal, phone, sha256 prefix, quote, extraction, conflict)
ROWS = [
    ("colonial-inn", "Colonial Inn", "3329 South Virginia Dare Trail", "Nags Head", "27959", "", "0cc341b65af8",
     "We are pleased to welcome your pets! Dogs and cats are allowed based on room availability. A daily fee is "
     "charged per pet (a maximum of 2 pets are allowed in a room).",
     {"pets_allowed": True, "pet_count_limit": 2, "species_allowed": ["cat", "dog"]}, None),
    ("mariner-inn", "Mariner Inn & Suites", "1801 N Virginia Dare Trail", "Kill Devil Hills", "27948", "", "9d1d5357033c",
     "Pets are ONLY allowed in designated pet-friendly rooms and up to two pets/room The pet fee is $25/night for each pet.",
     {"pets_allowed": True, "pet_fee": 2500, "fee_currency": "USD", "fee_basis": "per_night", "fee_scope": "per_pet",
      "pet_count_limit": 2}, None),
    ("dolphin-oceanfront-motel", "Dolphin Oceanfront Motel", "8017 S. Old Oregon Inlet Road", "Nags Head", "27959", "",
     "57cce81d761a",
     "Dolphin Oceanfront Motel is proud to offer Pet Friendly rooms. We accept dogs for a nightly fee of $10 per night. "
     "2 pets maximum per room.",
     {"pets_allowed": True, "pet_fee": 1000, "fee_currency": "USD", "fee_basis": "per_night", "pet_count_limit": 2,
      "species_allowed": ["dog"]}, None),
    # The motor lodge's own Pet Policy page. (Its FAQ answer -- "allows dogs and cats ... $25 per pet/day" -- was
    # read first; the shared reader classifies that answer FEE_ONLY, so the policy page's own sentence is cited.)
    ("heart-of-manteo", "Heart of Manteo Motor Lodge", "100 US-64", "Manteo", "27954", "", "c911a6fd0cab",
     "Dogs and cats are allowed based on room availability. A daily fee is charged per pet (a maximum of 2 pets are "
     "allowed in a room).",
     {"pets_allowed": True, "pet_count_limit": 2, "species_allowed": ["cat", "dog"]}, None),
    ("island-guesthouse-motel", "The Island Guesthouse & Motel", "706 N Hwy 64", "Manteo", "27954", "252-473-2434",
     "7ae1ff360004",
     "Pets: We have several pet-friendly rooms available on the property. Advanced notice is required if your pet is "
     "accompanying you. You will be charged a pet fee of $40 per pet/ per night. Additional nights will be only $25.",
     # Two nightly amounts ($40 first night, $25 additional) -- the fee is left UNKNOWN.
     {"pets_allowed": True}, None),
    ("john-yancey-inn", "John Yancey Oceanfront Inn", "2009 S. Virginia Dare Trail", "Kill Devil Hills", "27948", "",
     "34fe74f07eee",
     "Yes, we are dog friendly! Dogs are allowed in designated pet friendly rooms. We do require a pet liability waiver "
     "to be signed at check in. Please inquire with the reservations team when making your reservation. The pet fee is "
     "$40 plus taxes per pet, max of 2 dogs per hotel room not to exceed 80lbs total.",
     # "per pet" states no night or stay -- the fee basis is never defaulted, so no fee is published.
     {"pets_allowed": True, "pet_count_limit": 2, "weight_limit": 80.0, "weight_limit_unit": "lb",
      "weight_basis": "combined", "species_allowed": ["dog"]}, None),
    ("mias-boutique-hotel", "Mia's Boutique Hotel", "7115 South Virginia Dare Trail", "Nags Head", "27959", "",
     "95a5a653bacc",
     "Pet Policies Dogs and cats are allowed If you intend to bring your pet, please make sure to mention your pet while "
     "booking your room.",
     {"pets_allowed": True, "species_allowed": ["cat", "dog"]}, None),
    ("ocean-sands", "Ocean Sands Beach Boutique Inn", "1003 S Croatan Hwy", "Kill Devil Hills", "27948", "",
     "0304521f9f8b",
     "At Ocean Sands Beach Boutique Inn in Kill Devil Hills, we welcome well behaved dogs and cats in select rooms so "
     "you can enjoy the shoreline together.",
     {"pets_allowed": True, "species_allowed": ["cat", "dog"]}, None),
    ("roanoke-island-inn", "Roanoke Island Inn", "305 Fernando Street", "Manteo", "27954", "(252) 473-5511",
     "6748d2d8e6b7",
     "Dogs are welcome in rooms 2, 3, the Bungalow and Dot's Cottage and require a $50 cleaning fee.",
     {"pets_allowed": True, "species_allowed": ["dog"]}, None),
    ("sea-foam-motel", "Sea Foam Motel", "7111 S. Virginia Dare Trail", "Nags Head", "27959", "", "96e34efad346",
     "We have select rooms that are pet-friendly and invite you to bring your canine companion (Pet fee applies)",
     {"pets_allowed": True}, None),
    ("seahorse-inn", "Seahorse Inn & Cottages", "7218 S Virginia Dare Trail", "Nags Head", "27959", "252-441-5242",
     "0a02959a2481",
     "Not ALL rooms are pet friendly. Pets are ONLY allowed in designated pet friendly rooms (RMS 140, 141, 142 and 143). "
     "Pet fees are $25 per pet, per night.",
     {"pets_allowed": True, "pet_fee": 2500, "fee_currency": "USD", "fee_basis": "per_night", "fee_scope": "per_pet"},
     None),
    ("see-sea-motel", "See Sea Motel", "1234 South Virginia Dare Trail", "Kill Devil Hills", "27948", "",
     "4537008887ea",
     "We’re thrilled to be a pet-friendly motel and welcome dogs in selected rooms.",
     {"pets_allowed": True, "species_allowed": ["dog"]}, None),
    ("tar-heel-motel", "Tar Heel Motel", "7010 South Virginia Dare Trail", "Nags Head", "27959", "", "368a8d7beaa0",
     "The Tar Heel Motel offers pet-friendly rooms, and only dogs are allowed at the facility.",
     {"pets_allowed": True, "species_allowed": ["dog"]}, None),
    ("blue-heron-motel", "Blue Heron Motel", "6811 Virginia Dare Trail", "Nags Head", "27959", "252-441-7447",
     "3953a6952deb",
     "At the Blue Heron, we understand that pets are family — and we’re happy to welcome yours! Our Pet Policy is "
     "simple: Dogs and cats are allowed based on room availability. A daily fee is charged per pet (a maximum of 2 pets "
     "are allowed in a room).",
     {"pets_allowed": True, "pet_count_limit": 2, "species_allowed": ["cat", "dog"]}, None),
    ("the-sanderling", "The Sanderling Resort", "1461 Duck Road", "Duck", "27949", "", "160c965c0af1",
     "The Sanderling welcomes dogs staying with their owners .The fee is $300 for guest rooms and $400 for the "
     "residences. The maximum allowance is two (2) dogs, under 60 pounds each, per guestroom or vacation home.",
     # Two amounts (guest rooms vs residences) -- the fee is left UNKNOWN.
     {"pets_allowed": True, "pet_count_limit": 2, "weight_limit": 60.0, "weight_limit_unit": "lb",
      "species_allowed": ["dog"]}, None),
    ("surf-side-hotel", "Surf Side Hotel", "6701 S. Virginia Dare Trail", "Nags Head", "27959", "252 441-2105",
     "1705cad480b4",
     "Do you allow pets? Yes. We have a couple of pet friendly rooms in our condo building. Condo rentals allow up to two "
     "dogs under 50 pounds with a nightly fee.",
     {"pets_allowed": True, "pet_count_limit": 2, "weight_limit": 50.0, "weight_limit_unit": "lb",
      "species_allowed": ["dog"]}, None),
    ("sea-ranch-resort", "Sea Ranch Resort", "1731 N. Virginia Dare Trail", "Kill Devil Hills", "27948", "",
     "176095d3d1d5",
     "we have a limited number of guest rooms designated as dog-friendly and welcome your visit.",
     {"pets_allowed": True}, None),
    ("outer-banks-motor-lodge", "Outer Banks Motor Lodge", "1509 S. Virginia Dare Trail", "Kill Devil Hills", "27948", "",
     "bc533ce06b7f",
     "Do you allow pets? We only have 4 rooms that are pet friendly, to reserve one of our pet rooms, be sure the "
     "description of the room says \"pet friendly\". Our oceanfront rooms are not pet friendly. If you need a pet "
     "friendly room, it is best to call the motel to be sure you get the room you need. Is there a pet fee? Yes, we "
     "have an additional $25 per night pet fee.",
     {"pets_allowed": True, "pet_fee": 2500, "fee_currency": "USD", "fee_basis": "per_night"}, None),
    ("the-pearl-hotel", "The Pearl Hotel", "100 Old Tom Ave", "Manteo", "27954", "", "3b04458313fb",
     "Pets: Pearl is a No Pet facility with the exception of our Soundscape Family Suite, #205. The dog must be 15 "
     "pounds or smaller.",
     {"pets_allowed": True},
     "the hotel's own policy calls it 'a No Pet facility' and in the same sentence accepts a dog of 15 lb or less in one "
     "suite (#205); a single-suite exception to a no-pet facility is neither a pet-friendly hotel nor a verified "
     "no-pets hotel, so neither publishes"),
    # verified no-pets
    ("cypress-moon-inn", "Cypress Moon Inn", "1206 Harbor Court", "Kitty Hawk", "27949", "", "d3dc8ffaa364",
     "Although pets cannot stay at the inn there are some very good local boarding options close by that allow you to "
     "spend the day with your pet.",
     {"pets_allowed": False}, None),
    ("oasis-suites", "Oasis Suites Hotel", "7721 South Virginia Dare Trail", "Nags Head", "27959", "(252) 441-5211",
     "606b611abe58",
     "Pets : Oasis is a “No Pet” facility.",
     {"pets_allowed": False}, None),
    ("scarborough-inn", "Scarborough Inn", "524 US Highway 64", "Manteo", "27954", "+1-252-473-3979", "9220b10df98e",
     "Pet Policies Pets not allowed.",
     {"pets_allowed": False}, None),
    ("shutters-on-the-banks", "Shutters on the Banks", "405 S. Virginia Dare Trail", "Kill Devil Hills", "27948",
     "252-441-5581", "bbdc57eefba6",
     "In deference to our other guests, pets are not allowed at Shutters on the Banks.",
     {"pets_allowed": False}, None),
]

#: The one attended read: tranquilhouseinn.com refused a plain client (403) and served the operator's
#: Chrome session. The sha256 and byte length were computed in the browser over the document in the same
#: JavaScript call that located the quote and the page's own address (405 Queen Elizabeth Avenue Manteo, NC 27954).
ATTENDED = [
    OrderedDict([
        ("seed", "tranquil-house-inn"), ("brand", "INDEPENDENT"), ("lane", "ATTENDED_BROWSER"),
        ("name", "The Tranquil House Inn"), ("street", "405 Queen Elizabeth Avenue"), ("city", "Manteo"),
        ("postal", "27954"), ("phone", "(252) 473-1404"),
        ("url", "https://www.tranquilhouseinn.com/manteo-inn-amenities"),
        ("sha256", "9ae6aab0a7b7d546a0d5f11b6f3aa59bcb241c4a8f580baf0fc1dfe9dc4f332e"), ("bytes", 74397),
        ("surface", SURFACE), ("quote", "No guest pets allowed."),
        ("extraction", OrderedDict([("pets_allowed", False)])),
        ("method", "BROWSER_HASHED_DOCUMENT_STATING_THE_PROPERTYS_OWN_ADDRESS"), ("conflict", None),
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
                        glob.glob(os.path.join(ACQ, "outer_banks_nc_*", prefix + "*.bin"))}.values())
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
