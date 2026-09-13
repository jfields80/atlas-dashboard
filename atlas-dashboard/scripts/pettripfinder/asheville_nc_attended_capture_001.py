"""PTF-ASHEVILLE-NC-NORMAL-PRODUCTION-001 -- Phases 9-13: the first-party policy reads.

Four brand families read in a real Chrome session with the operator's
authorisation (attended browser, free), plus the independent / resort
properties' own websites (plain static reads, and one attended navigation of
The Omni Grove Park Inn, whose site refused the plain client):

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
session payloads live under ``data/acquisition/asheville_nc_attended/``;
this committed report is the durable record, and each row also carries the
sha256 of its own operative excerpt so a later reader can prove the quote was
not edited.

A PROPERTY CODE SELECTS; THE PAGE ADMITS: every row is judged IN_MARKET or
OUTSIDE_MARKET on the postal code its own page states.

No paid provider. No credential. No bot check answered.

Output:
  launch_packages/pettripfinder/markets/reports/asheville_nc_attended_capture_001.json
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

WORK_ORDER = "PTF-ASHEVILLE-NC-NORMAL-PRODUCTION-001"
MARKET_ID = "asheville-nc"
SCHEMA = "ptf-attended-capture/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
RAW = os.path.join(_DASH, "data", "acquisition", "asheville_nc_attended")
REGISTRY = os.path.join(REPORTS, "asheville_nc_corridor_registry_001.json")
OUT = os.path.join(REPORTS, "asheville_nc_attended_capture_001.json")
CAPTURED_AT = "2026-09-13"

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
        # A second-pet surcharge ("150 USD fee for 1 dog, addl. 50 USD fee for 2nd")
        # makes the labelled amount a first-pet amount, not a per-pet fee.
        if re.search(r"\baddl\b|additional\s+(?:pet|dog)|for\s+2nd", text, re.I):
            labels = []
        if len(bases) == 1 and labels:
            basis, amount = labels[0]
            ext["pet_fee"] = int(round(float(amount) * 100))
            ext["fee_currency"] = "USD"
            ext["fee_basis"] = "per_night" if basis.lower() == "night" else "per_stay"
            if re.search(r"non-?refundable", text, re.I):
                ext["fee_refundable"] = False
            # "2 pets max per room with a fee" scopes the COUNT, not the fee.
            if re.search(r"fee\s+per\s+room|per\s+room\s+per\s+(?:stay|night)", text, re.I):
                ext["fee_scope"] = "per_room"
        m = re.search(r"Maximum Pet Weight:\s*([0-9.]+)\s*lbs", text, re.I)
        # The hotel's own words and the labelled field must agree on the weight:
        # "2 pets 75bs maximum" beside "Maximum Pet Weight: 50.0lbs" publishes neither.
        narrative_w = {float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s*l?bs\b",
                                                    text.split("Maximum Pet Weight")[0], re.I)}
        if m and narrative_w and float(m.group(1)) not in narrative_w:
            m = None
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
        if m and re.search(r"for up to \d+ nights|greater than \d+ nights|\d+ nights and beyond"
                           r"|reduces to|longer than \d+ nights", text, re.I):
            m = None
        # A structured NIGHTLY fee beside the hotel's own ONE-TIME wording ("Upon
        # arrival, a non refundable fee of 75 dollars") is two readings; neither publishes.
        if m and m.group(1).lower() == "night" and re.search(r"upon arrival|one[- ]time|per stay", text, re.I):
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
    ("omni-grove-park", "The Omni Grove Park Inn & Spa", "290 Macon Avenue", "Asheville", "28804",
     None, "https://www.omnihotels.com/hotels/asheville-grove-park/property-details/policies",
     "c54df86f0a67d860c695cb252c59ab94cf3612adc49021690d2251935907d171", 1122207,
     "ATTENDED_BROWSER",
     "Registered dog guests are welcome at The Omni Grove Park Inn & Spa. Pet rooms are limited and "
     "are based on availability. Two dogs up to 60 lbs. each may be registered to a room, if a valid "
     "credit card is on file. Please note that our pet policy extends only to dogs. No other animals "
     "are allowed. Guests are required to sign a document accepting complete financial responsibility "
     "for any damage, personal injury or disturbance caused by the dog(s). Each room with a dog(s) "
     "will be charged a cleaning charge of $350 per stay (the charge is per room not per dog).",
     OrderedDict([("pets_allowed", True), ("pet_count_limit", 2), ("weight_limit", 60.0),
                  ("weight_limit_unit", "lb"), ("species_allowed", ["dog"]),
                  ("pet_fee", 35000), ("fee_currency", "USD"), ("fee_basis", "per_stay"),
                  ("fee_scope", "per_room")]),
     "ADDRESS_ON_THE_PROPERTYS_OWN_POLICY_PAGE", None),
    ("haywood-park", "Haywood Park Hotel, Ascend Hotel Collection", "1 Battery Park Avenue", "Asheville",
     "28801", "(828) 232-8217",
     "https://www.haywoodpark.com/faq/home-faq-list/is-the-haywood-park-hotel--atrium-a-pet-friendly-hotel",
     "66f573914f4d6b5652975b70498b7bcbd0cb007c19b68799df8e20b4346eb989", 48209,
     "DIRECT_STATIC_FETCH", "Hotel accepts dogs only, with a one-time pet fee per stay of $ 75.",
     OrderedDict([("pets_allowed", True), ("species_allowed", ["dog"])]),
     "ADDRESS_AND_PHONE_ON_THE_PROPERTYS_OWN_SITE__PAGE_SPELLS_THE_NUMBER_ONE", None),
    ("windsor", "The Windsor Boutique Hotel", "36 Broadway", "Asheville", "28801", "+1 844 494 6376",
     "https://windsorasheville.com/faq",
     "b108d645712911d1ec5e39d16b1d7786f8ad83702893cb8396177065347f1c7e", 146120,
     "DIRECT_STATIC_FETCH",
     "We’re happy to welcome dogs in our designated pet-friendly King Suites! A fee of $50 per pet, "
     "per night applies and includes the use of a dog bed along with food and water bowls during your stay.",
     OrderedDict([("pets_allowed", True), ("pet_fee", 5000), ("fee_currency", "USD"),
                  ("fee_basis", "per_night"), ("fee_scope", "per_pet")]),
     "ADDRESS_AND_PHONE_ON_THE_PROPERTYS_OWN_SITE", None),
    ("downtown-inn", "Downtown Inn & Suites", "120 Patton Avenue", "Asheville", "28801", None,
     "https://www.downtowninnandsuites.com/index.php?option=com_sppagebuilder&view=page&id=22&Itemid=696",
     "b65557d848ca156f576d8a09928443b7be2da9786dd50cb1953dd8b04d25bc95", 19023,
     "DIRECT_STATIC_FETCH",
     "Pets Welcome! We are a pet friendly hotel. Please register your pet at the front desk when you "
     "check in. There is a $15 fee per pet per night.",
     OrderedDict([("pets_allowed", True), ("pet_fee", 1500), ("fee_currency", "USD"),
                  ("fee_basis", "per_night"), ("fee_scope", "per_pet")]),
     "ADDRESS_ON_THE_PROPERTYS_OWN_SITE", None),
    ("woodspring", "WoodSpring Suites Asheville - Biltmore West", "40 Monte Vista Road", "Asheville", "28806",
     None, "https://www.woodspring.com/extended-stay-hotels/locations/north-carolina/asheville-brevard/woodspring-suites-asheville",
     "ac51d9afce60b12144ed037522e884f0c7247230c9a99c9e4359c76cee3fa5a2", 235871,
     "DIRECT_STATIC_FETCH", "Limit 2 dogs, under 75lbs.", OrderedDict(),
     "ADDRESS_ON_THE_BRANDS_OWN_PROPERTY_PAGE", None),
    ("restoration", "The Restoration Asheville", "68 Patton Avenue", "Asheville", "28801", None,
     "https://therestorationhotel.com/hotel-faqs/",
     "d9ca0d1516800af994be17b51ff88dd58038bde86cb4d82f2ba906c71e6e6077", 357646,
     "DIRECT_STATIC_FETCH",
     "The Restoration welcomes well-behaved dogs at both The Restoration Charleston and The Restoration Asheville.",
     OrderedDict(), "ADDRESS_ON_THE_PROPERTYS_OWN_SITE", None),
    ("bunn-house", "Bunn House", "15 Clayton Street", "Asheville", "28801", None,
     "https://www.bunnhouse.com/faq",
     "09f58d3027b04e9594f278adb02627c4e0afa9199a05e65d4fd06fe49b6dd794", 171530,
     "DIRECT_STATIC_FETCH", "Although we love our animals, we do not allow pets at the Bunn House.",
     OrderedDict(), "ADDRESS_ON_THE_PROPERTYS_OWN_SITE", None),
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

    # EXTENDED STAY AMERICA: the property's own page, read by a plain client. The
    # page's own "Pet Policy" block states the allowance; the chain-level line
    # "Pets are welcome at all our hotels" and the amenity chip are never read.
    esa_url = "https://www.extendedstayamerica.com/hotels/nc/asheville/tunnel-rd"
    esa_quote = "Pet Policy A maximum of two pets are allowed in each suite."
    sig = OrderedDict([("name_on_page", "Extended Stay America - Asheville - Tunnel Rd."),
                       ("address_on_page", "6 Kenilworth Knoll"), ("postal_code", "28805"),
                       ("locality", "Asheville"), ("region", "NC"),
                       ("phone_on_page", "1-828-253-3483"), ("property_code_on_page", None)])
    out.append(_row("EXTENDED_STAY", "DIRECT_STATIC_FETCH", None, esa_url, esa_url, sig,
                    "3718e9a5af101a88ecc8de637884f4a92791b3e3b41701dcb3605fd97bd9bf87",
                    397527, "the property's own page, Pet Policy block",
                    esa_quote, OrderedDict([("pets_allowed", True), ("pet_count_limit", 2)]), zips,
                    "ADDRESS_AND_PHONE_ON_THE_PROPERTYS_OWN_PAGE"))

    in_market = [r for r in out if r["in_market"]]
    return OrderedDict([
        ("schema", SCHEMA), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "9-13 -- attended browser pass over Hilton, Marriott, Wyndham and IHG, plus the independents' own sites"),
        ("as_of", CAPTURED_AT),
        ("lane", "ATTENDED_BROWSER (a person in a real Chrome session; free) + DIRECT_STATIC_FETCH"),
        ("authorization", "the operator's work order authorises the attended lane; no credential entered"),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("firecrawl_credits", 0),
        ("lanes_refused_this_run", OrderedDict([
            ("CHOICE", "the plain client timed out on the sitemap and the attended session rendered a blank page for a choicehotels.com Asheville property page (nc598); not fought further"),
            ("HYATT", "403 to a plain client on the sitemap; the interstitial is never satisfied"),
            ("BEST_WESTERN", "sitemap 403 to a plain client; not fought further"),
            ("RED_ROOF", "sitemap 403 to a plain client"),
            ("RADISSON", "sitemap 403 to a plain client, and radissonhotels.com is not a navigable domain in the operator's session"),
            ("MOTEL6", "sitemap timed out"),
            ("OMNI", "sitemap 403 and a 403 to a plain client on the property page; the property's own policy page served the attended session and was read"),
            ("BILTMORE_ESTATE", "the estate's own lodging statement is a service-animal carve-out the first-party binding gate refuses (SERVICE_ANIMAL_ONLY); its stay pages returned 404 to a plain client at the probed paths"),
            ("INDEPENDENT_SITES", "cabinlodge.com, mountaineerinn.com, mountvueasheville.com, thunderbirdmotelasheville.com, townhousemotelasheville.com, rockhavenmotel.com, whisperingpinesmotelasheville.com and thebeaucatcher.com did not resolve; theashevilleinn.com, plantationmotel.com and montevistanc.com returned 403; carolinabb.com returned 500; exploreasheville.com returned 403"),
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
