"""PTF-GREENVILLE-NC-PARALLEL-SOURCE-READY-001 -- Phases 9-13: the first-party policy reads.

Four brand families read in a real Chrome session with the operator's
authorisation (attended browser, free), plus Red Roof's own property pages
(attended, found in the brand's own sitemap):

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
  RED_ROOF  one top-level navigation per property page found in the brand's own
            sitemap; the Hotel JSON-LD street, the postal code from the page's
            own address data, and the page's "Pet Policy:" sentence verbatim.
  (InTown Suites, Affordable Suites and The 5th Street Inn were read too; none of
  them binds a policy -- see ``lanes_refused_this_run`` and the census's
  identity-only reads.)

DURABILITY
----------
Every row carries the requested and final URL, the capture lane and time, the
identity signals the page itself states, the SHA-256 and byte length of the
document the quote was read from (computed in the same browser call as the
quote), the operative quote verbatim, and the facts parsed from it. The raw
session payloads live under ``data/acquisition/greenville_nc_attended/``;
this committed report is the durable record, and each row also carries the
sha256 of its own operative excerpt so a later reader can prove the quote was
not edited.

A PROPERTY CODE SELECTS; THE PAGE ADMITS: every row is judged IN_MARKET or
OUTSIDE_MARKET on the postal code its own page states.

No paid provider. No credential. No bot check answered.

Output:
  launch_packages/pettripfinder/markets/reports/greenville_nc_attended_capture_001.json
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

WORK_ORDER = "PTF-GREENVILLE-NC-PARALLEL-SOURCE-READY-001"
MARKET_ID = "greenville-nc"
SCHEMA = "ptf-attended-capture/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
RAW = os.path.join(_DASH, "data", "acquisition", "greenville_nc_attended")
REGISTRY = os.path.join(REPORTS, "greenville_nc_corridor_registry_001.json")
OUT = os.path.join(REPORTS, "greenville_nc_attended_capture_001.json")
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
        # "$100.00 non-refundable fee ... $75 fee per stay" (Homewood Suites Greenville)
        # states two different amounts for one fee field; neither is published.
        amounts = {int(float(a)) for a in re.findall(r"\$\s*([0-9]+(?:\.[0-9]{2})?)", desc)}
        if len(amounts) > 1:
            tiered_mismatch = True
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
    elif re.match(r"\s*pets\b.{0,60}?\bwelcome\b", text, re.I | re.S):
        # Baymont Greenville: "Pets with a maximum weight of 25 lbs. welcome with fee."
        # The sentence STARTS with pets and says they are welcome; a service-animal
        # sentence never starts that way.
        ext["pets_allowed"] = True
    if ext.get("pets_allowed"):
        # The labelled "Fees -" segment when the page has one, so "75lbs or less
        # per pet" in the allowance segment never makes a room charge per-pet.
        seg = re.search(r"Fees?\s*-\s*(.*?)(?:/|Other information|$)", text, re.I)
        fee_part = seg.group(1) if seg else text
        fee_part = re.split(r"sanitation fee|max(?:imum)?\s+[0-9]+\s*USD per stay", fee_part, flags=re.I)[0]
        m = _USD.search(fee_part)
        # "Maximum 2 pets allowed up to 50lbs each for no charge. Additional pets require
        # ... 20.00 USD per pet per night" (Travelodge, Fayetteville's run): the allowed pets
        # stay free and the USD amount prices pets beyond the allowance, so it is
        # never the fee for the pets the policy admits.
        if m and re.search(r"\bfor no charge\b", text, re.I) and re.search(r"additional pets", text, re.I):
            m = None
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


#: Brand property pages read one at a time (Red Roof, attended). Every extraction
#: below is the literal content of its quote and nothing more.
#: (seed, brand, name on page, street on page, city, postal, phone on page, url,
#:  sha256, bytes, lane, surface, quote, extraction, binding method)
_RR_QUOTE = ("Pet Policy: One, well-behaved domestic pet (cat or dog) Stays Free! Pets must be declared "
             "at check-in. Up to 2 pets allowed per room. Second pet $15/ night, not to exceed 7 nights "
             "or $105 per pet per stay. Pet not to exceed 80 pounds. Service and emotional support "
             "animals are always welcome.")
#: One pet free and a second at $15 per night states two amounts for one fee
#: field; the fee is left UNKNOWN rather than publishing either as "the" fee.
_RR_EXT = OrderedDict([("pets_allowed", True), ("pet_count_limit", 2), ("weight_limit", 80.0),
                       ("weight_limit_unit", "lb"), ("species_allowed", ["cat", "dog"])])
BRAND_PAGES = [
    ("red-roof-rri1234", "RED_ROOF", "Red Roof Inn Greenville, NC", "301 Greenville Blvd SE",
     "Greenville", "27858", "1-937-328-4819", "https://www.redroof.com/property/nc/greenville/rri1234",
     "d2359104243df5930a4b6a26c365d093686d8bd8bc8f2c354bab7cf9fa151588", 398454, "ATTENDED_BROWSER",
     "the property's own page, Pet Policy sentence", _RR_QUOTE, _RR_EXT,
     "HOTEL_JSONLD_STREET_AND_PAGE_POSTAL_CODE_AND_PROPERTY_CODE"),
    ("red-roof-rri1374", "RED_ROOF", "Red Roof Inn Washington, NC", "1031 Carolina Ave",
     "Washington", "27889", "1-937-249-5544", "https://www.redroof.com/property/nc/washington/rri1374",
     "8e033c4aeb6a8a495885b735f09c53441f979b20920ad1a5214cad62ce23e4f6", 404323, "ATTENDED_BROWSER",
     "the property's own page, Pet Policy sentence", _RR_QUOTE, _RR_EXT,
     "HOTEL_JSONLD_STREET_AND_PAGE_POSTAL_CODE_AND_PROPERTY_CODE"),
]


def _row(brand, lane, code, req, final, sig, sha, nbytes, surface, quote, ext, zips, method):
    z = (sig.get("postal_code") or "")[:5]
    confirmed = bool(sig.get("address_on_page") and z)
    # The geography's own membership function decides, so a Greenville, SOUTH
    # CAROLINA page (296xx) is outside the market whatever its name.
    from scripts.pettripfinder import greenville_nc_geography_001 as GEO
    if GEO.classify_postal(z, sig.get("locality"))[0] == "OUTSIDE":
        zips = {k: v for k, v in zips.items() if k != z}
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
    # hilton_rows_outside.json: the other 20 codes the fourteen city pages listed
    # (Wilmington, New Bern, Havelock, Morehead City, Atlantic Beach, Kinston), read
    # in the same call so each is classified OUTSIDE on its own postal code rather
    # than left as an unaddressed roster row.
    for r in (_load(os.path.join(RAW, "hilton_rows.json"), [])
              + _load(os.path.join(RAW, "hilton_rows_outside.json"), [])):
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

    for (seed, brand, name, street, city, postal, phone, url, sha, nbytes, lane, surface, quote, ext,
         method) in BRAND_PAGES:
        sig = OrderedDict([("name_on_page", name), ("address_on_page", street),
                           ("postal_code", postal), ("locality", city), ("region", "NC"),
                           ("phone_on_page", phone), ("property_code_on_page", None)])
        row = _row(brand, lane, None, url, url, sig, sha, nbytes, surface, quote, OrderedDict(ext),
                   zips, method)
        row["brand_page_seed"] = seed
        out.append(row)

    in_market = [r for r in out if r["in_market"]]
    return OrderedDict([
        ("schema", SCHEMA), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "9-13 -- attended browser pass over Hilton, Marriott, Wyndham, IHG and Red Roof"),
        ("as_of", CAPTURED_AT),
        ("lane", "ATTENDED_BROWSER (a person in a real Chrome session; free) + DIRECT_STATIC_FETCH"),
        ("authorization", "the operator's work order authorises the attended lane; no credential entered"),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("firecrawl_credits", 0),
        ("lanes_refused_this_run", OrderedDict([
            ("CHOICE", "the plain client timed out on the sitemap and choicehotels.com is not a permitted navigation in the attended session this run; every Choice-flagged building (Comfort Inn & Suites, Quality Inn, Econo Lodge) is ACCESS_BLOCKED"),
            ("BEST_WESTERN", "the sitemap 403'd a plain client; the Best Western property route the attended session tried redirected to the brand's hotel-search page -- no property page was served; Best Western Plus Suites Greenville is ACCESS_BLOCKED"),
            ("MOTEL6", "motel6.com timed out a plain client and is not a permitted navigation in the attended session this run; Motel 6 (810 S Memorial Dr) is ACCESS_BLOCKED"),
            ("RADISSON", "the sitemap 403'd a plain client and the attended session rendered an empty 2,833-byte shell for radissonhotels.com/en-us/hotels/country-inn-winterville-nc; Country Inn & Suites Winterville is ACCESS_BLOCKED"),
            ("HYATT", "403 to a plain client on the sitemap; no Hyatt property was found in the market by any lane"),
            ("SONESTA", "the sitemap answered and holds no Greenville route; Knights Inn's own brand site (knightsinn.com) served only a chain page"),
            ("WOODSPRING", "the sitemap answered and lists no Greenville NC property"),
            ("EXTENDED_STAY", "the sitemap answered and lists no Greenville NC property"),
            ("INTOWN_SUITES", "the property's own page (intownsuites.com/extended-stay-hotels/north-carolina/greenville-nc/arlington-blvd/) served a plain client and answers 'Are Pets Allowed At InTown Suites Greenville NC? No pets allowed at InTown Suites Greenville NC' beside the street 2111 W Arlington Blvd -- but the page states NO postal code, so the read cannot bind by the page's own street identity; held, never published"),
            ("AFFORDABLE_SUITES", "the attended session served the property page (Hotel JSON-LD 101 Dansey Road 27834), whose only pet wording is a 'Pet-Friendly Rooms' amenity chip -- never operative"),
            ("INDEPENDENT_SITES", "the5thstreetinn.com served its home page (LocalBusiness JSON-LD 1105 E 5th St 27858) with no pet wording; Camelot Inn, Economy Inn, Greenville Motel and Knights Inn have no first-party property site any lane found"),
            ("BRINGFIDO", "not navigated; competitor names came from a web search result page (names only)"),
            ("CVB", "visitgreenvillenc.com's Hotels & Motels category renders client-side, so its own sitemap.xml and each lodging listing page were read by a plain client (greenville_nc_destination_roster_001.json)"),
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
