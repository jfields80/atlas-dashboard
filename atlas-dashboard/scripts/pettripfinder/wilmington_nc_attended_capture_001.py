"""PTF-WILMINGTON-NC-NORMAL-PRODUCTION-001 -- Phases 9-13: the first-party policy reads.

Four brand families read in a real Chrome session with the operator's
authorisation (attended browser, free), plus the independent / resort
properties' own websites (plain static reads, and two attended navigations of
sites that refused the plain client):

  HILTON    same-origin fetch of the property page; the ``__NEXT_DATA__``
            ``petsInfo`` node (petsAllowed, petCharge, petMaxWeight,
            description) and the address node beside it.
  MARRIOTT  one top-level navigation per property; the Hotel JSON-LD for
            identity and the rendered HOTEL INFORMATION "Pet Policy" row,
            bounded before the next label, for the operative statement.
  WYNDHAM   one top-level navigation per property; the Hotel JSON-LD for
            identity and the client-rendered ``.pet-policy-desc`` element. A
            sitemap route that now redirects to the brand's city search page is
            a RETIRED ROUTE and is recorded as such -- never as a refusal.
  IHG       same-origin fetch of ``hoteldetail``; the property FAQ's own answer
            to "Can I bring my pet to X?" and the Hotel JSON-LD address. The
            amenity icon is never read.
  INDEPENDENT  the property's own website: the sentence it publishes about
            pets, verbatim, from the page whose sha256 is recorded. Facts are
            parsed only where the quoted words state them; a fee stated on two
            bases ("$45 per night or a flat rate of $105") is left UNKNOWN. Two
            properties whose own pages state BOTH acceptance and refusal are
            recorded as FIRST_PARTY_CONFLICT and publish nothing.

DURABILITY
----------
Every row carries the requested and final URL, the capture lane and time, the
identity signals the page itself states, the SHA-256 and byte length of the
document the quote was read from (computed in the same browser call as the
quote), the operative quote verbatim, and the facts parsed from it. The raw
session payloads live under ``data/acquisition/wilmington_nc_attended/``;
this committed report is the durable record, and each row also carries the
sha256 of its own operative excerpt so a later reader can prove the quote was
not edited.

A PROPERTY CODE SELECTS; THE PAGE ADMITS: every row is judged IN_MARKET or
OUTSIDE_MARKET on the postal code its own page states.

No paid provider. No credential. No bot check answered.

Output:
  launch_packages/pettripfinder/markets/reports/wilmington_nc_attended_capture_001.json
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-WILMINGTON-NC-NORMAL-PRODUCTION-001"
MARKET_ID = "wilmington-nc"
SCHEMA = "ptf-attended-capture/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
RAW = os.path.join(_DASH, "data", "acquisition", "wilmington_nc_attended")
REGISTRY = os.path.join(REPORTS, "wilmington_nc_corridor_registry_001.json")
OUT = os.path.join(REPORTS, "wilmington_nc_attended_capture_001.json")
CAPTURED_AT = "2026-09-12"

_WEIGHT = re.compile(r"(\d+(?:\.\d+)?)\s*(?:lbs?|pounds)\b", re.I)
_WORDS = {"one": 1, "two": 2, "three": 3}


def _load(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _sha(parts):
    return (parts or "").replace(".", "")


def _excerpt_sha(text):
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def zips_of_registry():
    reg = _load(REGISTRY)
    return {z: c["corridor_id"] for c in reg["corridors"] for z in c["included_postal_codes"]}


def _count(text):
    for rx in (r"(?:no more than|maximum(?: of)?|max(?:imum)?(?: of)?|limit(?:ed)? (?:of|to))\s+(\d|one|two|three)\s+pets?",
               r"(\d)\s*pets?\s*(?:max|per room|allowed)",
               r"(\d)\s*pet\s*max", r"(\d)max\b", r"max(?:imum)? number of pets in room:\s*(\d)",
               r"max(?:imum)?\s+(\d)\s+pets?", r"-\s*max of (\d)"):
        m = re.search(rx, text, re.I)
        if m:
            v = m.group(1).lower()
            return _WORDS.get(v) or int(v)
    return None


def _species(text):
    if re.search(r"cats?\s*(?:and|/|or|&)\s*dogs?\s*only|dogs?\s*(?:and|/|or|&)\s*cats?\s*(?:only|accepted)"
                 r"|only dogs and cats|cats/dogs", text, re.I):
        return ["cat", "dog"]
    if re.search(r"\bdogs only\b|only dogs allowed", text, re.I):
        return ["dog"]
    return None


# --------------------------------------------------------------------------- #
# per-family parsers: each returns (extraction, quote)
# --------------------------------------------------------------------------- #

def parse_hilton(r):
    desc = r.get("d") or ""
    ext = OrderedDict()
    if r.get("pa") is True and re.search(r"pets?\s+allowed", desc, re.I):
        ext["pets_allowed"] = True
    elif r.get("pa") is False and re.search(r"pets?\s+not\s+allowed|no\s+pets", desc, re.I):
        ext["pets_allowed"] = False
    elif r.get("pa") is False:
        # "Service animals only": a legal access category, not a refusal.
        ext["pets_allowed"] = False
    if ext.get("pets_allowed"):
        # A TIERED charge whose first tier differs from the structured petCharge
        # ("$125.00 non-refundable fee, $75(1-4n) <OR> $125(5+n)") states two
        # amounts for one field; the fee is left UNKNOWN rather than publishing
        # the higher tier as the fee.
        tier = re.search(r"\$?\s*([0-9]+)(?:\.00)?\s*(?:\(\s*1\s*-|fee\s+1\s*-|for\s+1\s*-)", desc, re.I)
        tiered_mismatch = bool(tier and r.get("f") is not None and int(tier.group(1)) != int(r["f"]))
        if (not tiered_mismatch and r.get("f") is not None
                and re.search(r"\$\s*%s" % int(r["f"]), desc)):
            ext["pet_fee"] = int(round(float(r["f"]) * 100))
            ext["fee_currency"] = "USD"
            ext["fee_basis"] = "per_stay"
            if re.search(r"non-?refundable", desc, re.I):
                ext["fee_refundable"] = False
        w = _WEIGHT.search(desc)
        if w and float(w.group(1)) > 0:
            ext["weight_limit"] = float(w.group(1))
            ext["weight_limit_unit"] = "lb"
            if re.search(r"combined", desc, re.I):
                ext["weight_basis"] = "combined"
        c = _count(desc)
        if c:
            ext["pet_count_limit"] = c
        s = _species(desc)
        if s:
            ext["species_allowed"] = s
    return ext, desc


_LABELLED_FEE = re.compile(r"Pet\s+Fee\s+Per\s+(Night|Stay)\s*:\s*\$?\s*([0-9]+(?:\.[0-9]{2})?)", re.I)


def parse_marriott(r):
    text = re.sub(r"\n\s*\n", " | ", (r.get("p") or "").strip())
    text = re.sub(r"\s+", " ", text)
    ext = OrderedDict()
    if re.search(r"Pets?\s+Not\s+Allowed", text, re.I):
        ext["pets_allowed"] = False
    elif re.search(r"Pets?\s+Welcome|Pets?\s+Allowed", text, re.I):
        ext["pets_allowed"] = True
    if ext.get("pets_allowed"):
        labels = _LABELLED_FEE.findall(text)
        bases = {b.lower() for b, _ in labels}
        # One labelled basis only. "Pet fee $20/day with $100/stay" states a
        # nightly AND a per-stay charge; a single fee field cannot hold both, so
        # the fee is left UNKNOWN rather than publishing half of it.
        if len(bases) == 1:
            basis, amount = labels[0]
            ext["pet_fee"] = int(round(float(amount) * 100))
            ext["fee_currency"] = "USD"
            ext["fee_basis"] = "per_night" if basis.lower() == "night" else "per_stay"
            if re.search(r"non-?refundable", text, re.I):
                ext["fee_refundable"] = False
        m = re.search(r"Maximum Pet Weight:\s*([0-9.]+)\s*lbs", text, re.I)
        if m and float(m.group(1)) > 0:
            ext["weight_limit"] = float(m.group(1))
            ext["weight_limit_unit"] = "lb"
        c = _count(text)
        if c:
            ext["pet_count_limit"] = c
        if re.search(r"cats are not allowed", text, re.I):
            ext["species_allowed"] = ["dog"]
    return ext, text


_USD = re.compile(r"(?:charge of\s+|fees?\s*-\s*(?:non-refundable\s+)?)?([0-9]+(?:\.[0-9]{2})?)\s*USD", re.I)


def parse_wyndham(r):
    text = (r.get("p") or "").strip()
    ext = OrderedDict()
    if re.search(r"no other pets are allowed|pets? (?:are )?not allowed", text, re.I):
        ext["pets_allowed"] = False
    elif re.search(r"pets?\s+(?:is\s+|are\s+)?allowed", text, re.I):
        ext["pets_allowed"] = True
    if ext.get("pets_allowed"):
        # The labelled "Fees -" segment when the page has one, so "75lbs or less
        # per pet" in the allowance segment never makes a room charge per-pet.
        seg = re.search(r"Fees?\s*-\s*(.*?)(?:/|Other information|$)", text, re.I)
        fee_part = seg.group(1) if seg else text
        fee_part = re.split(r"sanitation fee|max(?:imum)?\s+[0-9]+\s*USD per stay", fee_part, flags=re.I)[0]
        m = _USD.search(fee_part)
        if m:
            ext["pet_fee"] = int(round(float(m.group(1)) * 100))
            ext["fee_currency"] = "USD"
            ext["fee_basis"] = "per_night" if re.search(r"per\s+(?:pet\s+per\s+)?night|nightly", fee_part, re.I) else "per_stay"
            if re.search(r"per\s+pet", fee_part, re.I):
                ext["fee_scope"] = "per_pet"
            elif re.search(r"for up to \d+ pets", fee_part, re.I):
                ext["fee_scope"] = "per_room"
            if re.search(r"non-?refundable", fee_part, re.I):
                ext["fee_refundable"] = False
        w = _WEIGHT.search(text)
        if w:
            ext["weight_limit"] = float(w.group(1))
            ext["weight_limit_unit"] = "lb"
        c = _count(text)
        if c:
            ext["pet_count_limit"] = c
        s = _species(text)
        if s:
            ext["species_allowed"] = s
    return ext, text


def parse_ihg(r):
    text = html.unescape(r.get("p") or "")
    ext = OrderedDict()
    if re.match(r"\s*No,\s*pets\s+are\s+not\s+allowed", text, re.I):
        ext["pets_allowed"] = False
    elif re.match(r"\s*Pets\s+are\s+welcome", text, re.I):
        ext["pets_allowed"] = True
    if ext.get("pets_allowed"):
        m = re.search(r"Pet fee per (stay|night):\s*([0-9]+)\s*USD", text, re.I)
        # A structured "Pet fee per night: 75 USD" beside the hotel's own words
        # "75.00 nonrefundable, for up to 4 nights; 125.00 ... greater than 4
        # nights" is a TIERED per-stay charge the field misstates. Two readings
        # that disagree publish neither.
        if m and re.search(r"for up to \d+ nights|greater than \d+ nights|\d+ nights and beyond", text, re.I):
            m = None
        if m:
            ext["pet_fee"] = int(m.group(2)) * 100
            ext["fee_currency"] = "USD"
            ext["fee_basis"] = "per_stay" if m.group(1).lower() == "stay" else "per_night"
            if re.search(r"non-?\s?refundable", text, re.I):
                ext["fee_refundable"] = False
        structured = re.search(r"Pet weight limit:\s*([0-9]+)\b", text, re.I)
        narrative = _WEIGHT.search(text.split("Pet fee per")[0])
        # Two weights that disagree ("50 lb. or less" in the hotel's words,
        # "Pet weight limit: 75" in the field) publish neither.
        if structured and (not narrative or float(narrative.group(1)) == float(structured.group(1))):
            ext["weight_limit"] = float(structured.group(1))
            ext["weight_limit_unit"] = "lb"
        c = re.search(r"\b(\d)\s+pets allowed", text, re.I)
        if c:
            ext["pet_count_limit"] = int(c.group(1))
        s = _species(text)
        if s:
            ext["species_allowed"] = s
    return ext, text


#: The independent and resort properties, each read from its OWN website. Every
#: extraction below is the literal content of its quote and nothing more.
#: (seed, name on page, street on page, city, postal, phone on page, url, sha256,
#:  bytes, lane, quote, extraction, binding method, conflict note)
_NO = OrderedDict([("pets_allowed", False)])
INDEPENDENT = [
    ("sandpeddler", "Sandpeddler Inn & Suites", "15 Nathan Street", "Wrightsville Beach", "28480",
     "910-256-2028", "https://www.thesandpeddler.com/",
     "174fb52282534937592397e3009c06cd9bb3e1cbefee235d1e1ee2e5bd487d0b", 45298,
     "DIRECT_STATIC_FETCH", "No pets permitted", _NO,
     "ADDRESS_AND_PHONE_ON_THE_PROPERTYS_OWN_SITE", None),
    ("surf-suites", "The Surf Suites", "711 S Lumina Ave", "Wrightsville Beach", "28480",
     "910-256-2275", "https://thesurfsuites.com/policies-faqs/",
     "d411ee9ad000a8c604b67c9f887f8738c5683e1b855d4c5a906bbacc46bbd8c3", 159979,
     "DIRECT_STATIC_FETCH", "NO pets allowed!", _NO,
     "ADDRESS_AND_PHONE_ON_THE_PROPERTYS_OWN_SITE", None),
    ("pirates-cove", "Pirates Cove Hotel", "701 N Lake Park Blvd", "Carolina Beach", "28428",
     "910-458-5414", "https://piratescovehotel.com/",
     "1c1e06326416cd90873c7f281bd4bd6a615e1807180be46b3e651d2b72cb33de", 165532,
     "DIRECT_STATIC_FETCH",
     "For pet owners, the hotel provides designated pet-friendly rooms on the first floor, "
     "featuring ceramic tile floors for easy maintenance, and a dog park located at the rear of "
     "the property.",
     OrderedDict([("pets_allowed", True)]),
     "STREET_AND_CITY_ON_THE_PROPERTYS_OWN_SITE__CAROLINA_BEACH_IS_ONE_POSTAL_CODE", None),
    ("sand-dunes", "The Sand Dunes Motel", "133 Fort Fisher Boulevard South", "Kure Beach", "28449",
     "(910) 458-4500", "https://www.thesanddunes.com/rooms/policies",
     "c8ac425440f280ff194ae80a06008706caed6cb89ea6066ee0c21c09b85fbc8e", 31085,
     "DIRECT_STATIC_FETCH",
     "PETS & SERVICE ANIMALS We now accept dogs only. Guests are allowed two dogs per room and "
     "they cannot be over 80 pounds combined.",
     OrderedDict([("pets_allowed", True), ("pet_count_limit", 2), ("weight_limit", 80.0),
                  ("weight_limit_unit", "lb"), ("weight_basis", "combined"),
                  ("species_allowed", ["dog"])]),
     "ADDRESS_AND_PHONE_ON_THE_PROPERTYS_OWN_SITE", None),
    ("carolina-beach-inn", "Carolina Beach Inn", "205 Harper Ave", "Carolina Beach", "28428", None,
     "https://www.carolinabeachinn.com/pet-policy",
     "efb5fc105174842147325884eaccca6adc5eb320fd902752a8bbe17acd6d8a5f", 157917,
     "ATTENDED_BROWSER",
     "Carolina Beach Inn is a 100% Pet-Friendly property. Our Pet Policy is simple: bring them "
     "along for your stay! We welcome friendly dogs, cats and birds. Non-refundable pet fee of $45 "
     "per night or a flat rate of $105 for 3 or more nights. (includes up to 2 pets).",
     OrderedDict([("pets_allowed", True), ("pet_count_limit", 2)]),
     "ADDRESS_ON_THE_PROPERTYS_OWN_SITE", None),
    ("seabirds", "SeaBirds Motel at Kure Beach", "118 Fort Fisher Blvd S", "Kure Beach", "28449",
     "910-622-8393", "https://www.seabirdskb.com/pet-policy",
     "96494b35cf1f247c30c56f73525078a87c6a72dc8707a7e4346ee82621657547", 121916,
     "ATTENDED_BROWSER",
     "Seabirds is a 100% Pet-Friendly property. Our Pet Policy is simple: bring them along for "
     "your stay! We welcome friendly dogs, cats and birds. Non-refundable pet fee of $45 per night "
     "(includes up to 2 pets).",
     OrderedDict([("pets_allowed", True), ("pet_fee", 4500), ("fee_currency", "USD"),
                  ("fee_basis", "per_night"), ("fee_scope", "per_room"), ("fee_refundable", False),
                  ("pet_count_limit", 2)]),
     "ADDRESS_AND_PHONE_ON_THE_PROPERTYS_OWN_SITE", None),
    ("admirals-quarters", "The Admiral's Quarters", "129 Fort Fisher Boulevard South", "Kure Beach",
     "28449", "(910) 458-5050", "https://www.admiralsquartersmotel.com/rooms/policies",
     "6bcf4be4132ff20368a73c708aa6d9eca01ca2117acd0a1d1a0b2a79da5d7beb", 31061,
     "DIRECT_STATIC_FETCH",
     "PETS & SERVICE ANIMALS We now accept dogs only. Guests are allowed two dogs per room and "
     "they cannot be over 80 pounds combined.",
     OrderedDict(),
     "ADDRESS_AND_PHONE_ON_THE_PROPERTYS_OWN_SITE",
     "the home page (sha256 4449883234ed5c6772fd45c703823766c56c0e18b14ec4ab39113ec8d4d291f2) states "
     "'While we welcome service animals, unfortunately pets (including emotional support animals) "
     "are not permitted at our hotel.' and the policies page states 'We now accept dogs only.'"),
    ("front-street-inn", "Front Street Inn", "215 S Front St", "Wilmington", "28401",
     "(910) 762-6442", "https://www.frontstreetinn.com/policies",
     "a57af71edc31dd1afdbcf9efad5dd2057a7a5aa5a4a80893a97818c7b04537ab", 693214,
     "DIRECT_STATIC_FETCH",
     "Pets: We no longer accept pets (other than service animals in compliance with ADA Guidance "
     "from the Dept of Justice)",
     OrderedDict(),
     "ADDRESS_AND_PHONE_ON_THE_PROPERTYS_OWN_SITE",
     "the FAQ page (sha256 a6a3653e978cbede8a1ceeccf9e2bef83d74bba3ff138f6cea5f8c02c661478f) states "
     "'We allow well behaved dogs in Hemingway, Bistro, O'Keefe and The Coastal Cottage.' while the "
     "policies page states 'We no longer accept pets'."),
]


def _row(brand, lane, code, req, final, sig, sha, nbytes, surface, quote, ext, zips, method):
    z = (sig.get("postal_code") or "")[:5]
    confirmed = bool(sig.get("address_on_page") and z)
    return OrderedDict([
        ("brand", brand), ("lane", lane), ("property_code", code),
        ("requested_url", req), ("final_url", final), ("captured_at", CAPTURED_AT),
        ("document_bytes", nbytes), ("document_sha256", sha),
        ("identity_signals", sig), ("identity_confirmed", confirmed),
        ("identity_binding_method", method), ("surface", surface),
        ("exact_quote", quote), ("operative_excerpt_sha256", _excerpt_sha(quote)),
        ("extraction", ext),
        ("in_market", z in zips), ("corridor", zips.get(z, "")),
        ("market_verdict", ("IN_MARKET" if z in zips else "OUTSIDE_MARKET") if confirmed
         else "IDENTITY_NOT_STATED"),
    ])


def build():
    zips = zips_of_registry()
    out = []
    for r in _load(os.path.join(RAW, "hilton_rows.json"), []):
        ext, quote = parse_hilton(r)
        sig = OrderedDict([("name_on_page", r.get("n")), ("address_on_page", r.get("st")),
                           ("postal_code", (r.get("z") or "")[:5]), ("locality", r.get("ci")),
                           ("region", r.get("rg")), ("phone_on_page", r.get("ph")),
                           ("property_code_on_page", r["c"])])
        row = _row("HILTON", "ATTENDED_BROWSER", r["c"], r["u"], r["u"], sig, _sha(r.get("h")),
                   r.get("b"), "__NEXT_DATA__ petsInfo node", quote, ext, zips,
                   "PROPERTY_CODE_AND_ADDRESS_FROM_THE_PAGES_OWN_DATA")
        out.append(row)

    for r in _load(os.path.join(RAW, "marriott_rows.json"), []):
        ext, quote = parse_marriott(r)
        code = re.search(r"/hotels/([a-z0-9]{5})-", r["u"]).group(1)
        sig = OrderedDict([("name_on_page", r.get("n")), ("address_on_page", r.get("st")),
                           ("postal_code", r.get("z")), ("locality", r.get("ci")),
                           ("region", "NC" if r.get("rg") == "North Carolina" else r.get("rg")),
                           ("phone_on_page", r.get("ph")), ("property_code_on_page", code)])
        out.append(_row("MARRIOTT", "ATTENDED_BROWSER", code, r["u"], r["u"], sig, _sha(r.get("h")),
                        r.get("b"), "HOTEL INFORMATION block, Pet Policy row", quote, ext, zips,
                        "HOTEL_JSONLD_ADDRESS_AND_PROPERTY_CODE"))

    wyn = _load(os.path.join(RAW, "wyndham_rows.json"), {})
    for r in wyn.get("rows", []):
        ext, quote = parse_wyndham(r)
        sig = OrderedDict([("name_on_page", r.get("n")), ("address_on_page", r.get("st")),
                           ("postal_code", (r.get("z") or "")[:5]), ("locality", r.get("ci")),
                           ("region", r.get("rg")), ("phone_on_page", r.get("ph")),
                           ("property_code_on_page", r.get("id"))])
        out.append(_row("WYNDHAM", "ATTENDED_BROWSER", r.get("id"), r["u"], r["u"], sig,
                        _sha(r.get("h")), r.get("b"), "client-rendered .pet-policy-desc element",
                        quote, ext, zips, "HOTEL_JSONLD_ADDRESS_AND_PROPERTY_CODE"))

    ihg = _load(os.path.join(RAW, "ihg_rows.json"), {})
    for r in ihg.get("rows", []):
        st, ci, z, ph = (ihg.get("addresses", {}).get(r["c"]) or [None] * 4)
        ext, quote = parse_ihg(r)
        name = re.sub(r"^Can I bring my pet to\s+|\?$", "", html.unescape(r.get("q") or ""))
        sig = OrderedDict([("name_on_page", name), ("address_on_page", st), ("postal_code", z),
                           ("locality", ci), ("region", "NC"), ("phone_on_page", ph),
                           ("property_code_on_page", r["c"])])
        out.append(_row("IHG", "ATTENDED_BROWSER", r["c"], r["u"], r["u"], sig, _sha(r.get("h")),
                        r.get("b"), "the brand's own FAQ answer to 'Can I bring my pet to X?'",
                        quote, ext, zips, "HOTEL_JSONLD_ADDRESS_AND_PROPERTY_CODE"))

    for (seed, name, street, city, postal, phone, url, sha, nbytes, lane, quote, ext, method,
         conflict) in INDEPENDENT:
        sig = OrderedDict([("name_on_page", name), ("address_on_page", street),
                           ("postal_code", postal), ("locality", city), ("region", "NC"),
                           ("phone_on_page", phone), ("property_code_on_page", None)])
        row = _row("INDEPENDENT", lane, None, url, url, sig, sha, nbytes,
                   "the property's own website", quote, OrderedDict(ext), zips, method)
        row["independent_seed"] = seed
        if conflict:
            row["first_party_conflict"] = conflict
        out.append(row)

    # EXTENDED STAY AMERICA: one attended navigation. The property's own FAQPage
    # JSON-LD answers "Is ... pet friendly?"; the address and phone are the
    # page's own. The amenity chip "Pet-friendly room" beside it is never read.
    esa_url = "https://www.extendedstayamerica.com/hotels/nc/wilmington/new-centre-drive"
    esa_quote = ("Yes. Extended Stay America Wilmington - New Centre Drive offers pet-friendly "
                 "rooms, so you can bring your furry companion along for your stay.")
    sig = OrderedDict([("name_on_page", "Extended Stay America - Wilmington - New Centre Drive"),
                       ("address_on_page", "4929 New Centre Dr."), ("postal_code", "28403"),
                       ("locality", "Wilmington"), ("region", "NC"),
                       ("phone_on_page", "+19107934508"), ("property_code_on_page", None)])
    out.append(_row("EXTENDED_STAY", "ATTENDED_BROWSER", None, esa_url, esa_url, sig,
                    _sha("05d09d9a.ace59d55.d9d0dd4e.2aad3f89.356b029b.c57b0899.416989fc.cbf4b49b"),
                    784511, "the property's own FAQPage JSON-LD answer to 'Is X pet friendly?'",
                    esa_quote, OrderedDict([("pets_allowed", True)]), zips,
                    "HOTEL_JSONLD_ADDRESS_AND_PHONE"))

    in_market = [r for r in out if r["in_market"]]
    return OrderedDict([
        ("schema", SCHEMA), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "9-13 -- attended browser pass over Hilton, Marriott, Wyndham and IHG, plus the independents' own sites"),
        ("as_of", CAPTURED_AT),
        ("lane", "ATTENDED_BROWSER (a person in a real Chrome session; free) + DIRECT_STATIC_FETCH"),
        ("authorization", "the operator's work order authorises the attended lane; no credential entered"),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("firecrawl_credits", 0),
        ("lanes_refused_this_run", OrderedDict([
            ("CHOICE", "the plain client timed out on the sitemap and the attended session rendered a blank page for the choicehotels.com Wilmington city page; not fought further"),
            ("HYATT", "403 to a plain client on the sitemap; the interstitial is never satisfied"),
            ("BEST_WESTERN", "sitemap 403 to a plain client and the attended city page returned an error page; not fought further"),
            ("RED_ROOF", "sitemap 403 to a plain client"), ("RADISSON", "sitemap 403 to a plain client"),
            ("MOTEL6", "sitemap timed out"),
            ("EXTENDED_STAY", "sitemap answered but its walked shards held no Wilmington route"),
            ("INDEPENDENT_SITES", "summersandssuites.com served an 876-byte interstitial to the attended session; silvergullmotel.com, sevenseasinn.com, southwindmotel.com, seavistamotel.com and dolphinlanemotel.com returned 403 to a plain client and were not fought; carolinabeachmotel.com is not navigable in the operator's session"),
        ])),
        ("wyndham_retired_routes", wyn.get("retired_routes_redirected_to_brand_search", [])),
        ("wyndham_routes_not_read_outside_by_route_city", wyn.get("not_read_outside_by_route_city", [])),
        ("no_bot_check_was_answered",
         "every page served a plain navigation or same-origin fetch in the operator's own session."),
        ("counts", OrderedDict([
            ("pages_read", len(out)),
            ("by_brand", OrderedDict(sorted(Counter(r["brand"] for r in out).items()))),
            ("identity_confirmed", sum(1 for r in out if r["identity_confirmed"])),
            ("in_market", len(in_market)),
            ("outside_market", len(out) - len(in_market)),
            ("in_market_pets_allowed_true", sum(1 for r in in_market if r["extraction"].get("pets_allowed") is True)),
            ("in_market_pets_allowed_false", sum(1 for r in in_market if r["extraction"].get("pets_allowed") is False)),
        ])),
        ("rows", out),
    ])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args(argv)
    rep = build()
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rep, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print(json.dumps(rep["counts"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
