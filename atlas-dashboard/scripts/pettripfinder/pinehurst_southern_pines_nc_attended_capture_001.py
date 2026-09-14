"""PTF-PINEHURST-SOUTHERN-PINES-NC-PARALLEL-SOURCE-READY-001 -- Phases 10-14: the first-party policy reads.

Cloned from the Boone - Blowing Rock NC capture helper (Outer Banks, Greenville lineage). Families and surfaces:

  MARRIOTT  same-origin fetch of the property overview page in the operator's
            attended Chrome session (the server HTML carries the Hotel JSON-LD and
            the HOTEL INFORMATION "Pet Policy" row, read up to the next label).
  HILTON    same-origin fetch of the property page; the ``__NEXT_DATA__``
            ``petsInfo`` node and the address node beside it.
  IHG       same-origin fetch of ``hoteldetail``; the property FAQ's own answer to
            "Can I bring my pet to X?" and the Hotel JSON-LD address.
  WYNDHAM   plain-client reads (``pinehurst_southern_pines_nc_wyndham_lane_001``): the overview page
            (identifier; a redirect to the brand's city search is a RETIRED route)
            and the brand's own property service, whose ``hotelPolicies.petpolicy``
            is the text of the page's ``.pet-policy-desc`` element.
  BRAND_PAGES / STATIC  other first-party pages read one at a time (see below).

DURABILITY
----------
Every row carries the requested and final URL, the capture lane and time, the
identity signals the page itself states, the SHA-256 and byte length of the
document the quote was read from (computed in the same browser call as the
quote, or on the plain client's persisted bytes), the operative quote verbatim
(runs of blanks collapsed), the facts parsed from it, and the sha256 of the
operative excerpt. Raw browser payloads live under
``data/acquisition/pinehurst_southern_pines_nc_attended/``; each payload file's canonical JSON
sha256 was checked equal to the digest the browser computed over the same
payload before it was written (see ``payload_digests``).

GUARDS ADDED FOR ATLANTA
------------------------
* A Marriott Pet Policy row that says "Pets Welcome" and, in the hotel's own
  words, "No pets allowed" (SpringHill Suites Alpharetta) is a FIRST-PARTY
  CONFLICT and publishes neither.
* A Marriott labelled fee whose amount the hotel's own narrative contradicts
  ("100 USD ... per stay" beside "Per Night: $50.00") publishes no fee.
* An IHG structured fee whose basis or amount the narrative contradicts ("50
  dollars per pet, per day" beside "Pet fee per stay: 50 USD"; "75.00 flat fee"
  beside "Pet fee per night: 0 USD") publishes no fee.
* A Wyndham structured ``petPolicyindicator`` that disagrees with the operative
  text ("N" beside "Pets Allowed. 2 pets max") is a FIRST-PARTY CONFLICT.

No paid provider. No credential. No bot check answered.

Output:
  launch_packages/pettripfinder/markets/reports/pinehurst_southern_pines_nc_attended_capture_001.json
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

WORK_ORDER = "PTF-PINEHURST-SOUTHERN-PINES-NC-PARALLEL-SOURCE-READY-001"
MARKET_ID = "pinehurst-southern-pines-nc"
SCHEMA = "ptf-attended-capture/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
#: Raw browser payloads and plain-client extracts, COMMITTED in the market zone so the chain
#: rebuilds from committed captures (the original session copies stay under data/acquisition/).
RAW = os.path.join(PKG, "markets", "staging", "pinehurst-southern-pines-nc", "raw_captures")
REGISTRY = os.path.join(REPORTS, "pinehurst_southern_pines_nc_corridor_registry_001.json")
OUT = os.path.join(REPORTS, "pinehurst_southern_pines_nc_attended_capture_001.json")
CAPTURED_AT = "2026-09-14"

#: The canonical-JSON sha256 each browser payload was verified against before it
#: was committed to disk (the browser computed it over the same payload).
PAYLOAD_DIGESTS = OrderedDict([
    # OWNED REUSE, not a new browser read: the three Moore County rows of the Fayetteville order's attended
    # Hilton payload (PTF-FAYETTEVILLE-NC-NORMAL-PRODUCTION-001, captured 2026-09-13, source payload file
    # sha256 9e15ef6245cdee06cc1f28f27e6cb8a8803b44c470982dc5b6f5e5559147365c), copied value-for-value with
    # the pin keys renamed lat/lng -> la/lo and the route slug added. The digest is this file's own.
    ("hilton_rows.json", "92b06b8461e0d4999abd336045eac2b0be7f28587162ea5af3579b7cc0651b89"),
    ("marriott_rows.json", "51414b192256a5e3c81558445474a4f54f455f6f14197e13f961ae6482a767a1"),
    ("ihg_rows.json", "75e367f34e2dd49f1d9b2593a90b147febaff1cc92ca87d0f1f9bb08618e8e6a"),
])

_WEIGHT = re.compile(r"(\d+(?:\.\d+)?)\s*(?:lbs?|pounds)\b", re.I)
_WORDS = {"one": 1, "two": 2, "three": 3}


def _load(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _excerpt_sha(text):
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def zips_of_registry():
    reg = _load(REGISTRY)
    return {z: c["corridor_id"] for c in reg["corridors"] for z in c["included_postal_codes"]}


def _count(text):
    for rx in (r"(?:no more than|maximum(?: of)?|max(?:imum)?(?: of)?|limit(?:ed)? (?:of|to)|up to)\s+\(?(\d|one|two|three)\)?\s+(?:pets?|dogs?)",
               r"(\d)\s*(?:pets?|dogs?)\s*(?:max|per room|allowed)",
               r"(\d)\s*pet\s*max", r"(\d)max\b", r"max(?:imum)? number of pets in room:\s*(\d)",
               r"max(?:imum)?\s+(\d)\s+pets?", r"-\s*max of (\d)", r"(\d)\s*pets?\s*Max"):
        m = re.search(rx, text, re.I)
        if m:
            v = m.group(1).lower()
            return _WORDS.get(v) or int(v)
    return None


def _species(text):
    if re.search(r"cats?\s*(?:and|/|or|&)\s*dogs?\s*only|dogs?\s*(?:and|/|or|&)\s*cats?\s*(?:only|accepted|allowed)"
                 r"|only dogs and cats|cats/dogs|dog/cat only|dogs or cats only|cat/dog only", text, re.I):
        return ["cat", "dog"]
    if re.search(r"\bdogs only\b|only dogs allowed|dog only\b", text, re.I):
        return ["dog"]
    return None


def _amounts(text):
    return {float(a) for a in re.findall(r"(?:\$|USD\s*)\s*([0-9]+(?:\.[0-9]{1,2})?)", text, re.I)} | \
           {float(a) for a in re.findall(r"([0-9]+(?:\.[0-9]{1,2})?)\s*(?:USD|dollars)", text, re.I)}


# --------------------------------------------------------------------------- #
# per-family parsers: each returns (extraction, quote, conflict)
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
        tier = re.search(r"\$?\s*([0-9]+)(?:\.00)?\s*(?:\(\s*1\s*-|fee\s+1\s*-|for\s+1\s*-)", desc, re.I)
        tiered_mismatch = bool(tier and r.get("f") is not None and int(tier.group(1)) != int(r["f"]))
        amounts = {int(float(a)) for a in re.findall(r"\$\s*([0-9]+(?:\.[0-9]{2})?)", desc)}
        if len(amounts) > 1:
            tiered_mismatch = True
        # "$75(1-4n),$125(5+n)" -- a tier without a second "$" is still a tier.
        if re.search(r"\(\s*\d+\s*-\s*\d+\s*n|\d+\+\s*n|5\+|per day|per night|up to \w+ (?:days|nights)|more than \d+ nights|after \d+ days|first pet", desc, re.I):
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
    return ext, desc, None


_LABELLED_FEE = re.compile(r"Pet\s+Fee\s+Per\s+(Night|Stay)\s*:\s*\$?\s*([0-9]+(?:\.[0-9]{2})?)", re.I)


def parse_marriott(r):
    raw = (r.get("p") or "").strip()
    text = re.sub(r"\s+", " ", raw.replace("\n", " \n "))
    text = re.sub(r"\s*\n\s*", " ", text)
    ext = OrderedDict()
    conflict = None
    head = raw.split("\n", 1)[0].strip()
    narrative = raw.split("Non-Refundable Pet Fee")[0].split("Maximum Pet Weight")[0].split("Maximum Number of Pets")[0]
    narrative = narrative[len(head):]
    if re.match(r"Pets?\s+Not\s+Allowed", head, re.I):
        ext["pets_allowed"] = False
        if re.search(r"\bpets?\s+(?:are\s+)?(?:welcome|allowed)\b", narrative, re.I) and not \
                re.search(r"no\s+pets|not\s+allowed", narrative, re.I):
            conflict = "the row's heading says 'Pets Not Allowed' and the hotel's own words accept pets: %r" % narrative.strip()[:200]
    elif re.match(r"Pets?\s+Welcome|Pets?\s+Allowed", head, re.I):
        ext["pets_allowed"] = True
        if re.search(r"no\s+pets\s+allowed|pets\s+(?:are\s+)?not\s+allowed", narrative, re.I):
            conflict = "the row's heading says 'Pets Welcome' and the hotel's own words refuse pets: %r" % narrative.strip()[:200]
    if ext.get("pets_allowed"):
        labels = _LABELLED_FEE.findall(text)
        bases = {b.lower() for b, _ in labels}
        if re.search(r"\baddl\b|additional\s+(?:pet|dog)|for\s+2nd|second\s+(?:pet|dog)|first\s+pet", text, re.I):
            labels = []
        narr_amounts = _amounts(narrative)
        # BOONE GUARD. TownePlace Suites Boone labels "Per Stay: $100.00" beside its own words "a Non-Refundable
        # Fee of $100 per every 7 nights of stays" -- a charge that recurs by week is not a per-stay fee.
        if re.search(r"per\s+every\s+\d+\s+nights?", narrative, re.I):
            labels = []
        # PINEHURST GUARD. Residence Inn Pinehurst Southern Pines labels "Per Stay: $150.00" beside its own words
        # "USD 50 per night fee up to USD 150 max charge per stay" -- a nightly charge with a cap, not a flat
        # per-stay fee. A per-stay label whose narrative prices the pet by the night publishes no fee.
        if len(bases) == 1 and labels and labels[0][0].lower() == "stay" and \
                re.search(r"per\s+night|nightly|per\s+day", narrative, re.I):
            labels = []
        if len(bases) == 1 and labels:
            basis, amount = labels[0]
            if narr_amounts and float(amount) not in narr_amounts:
                labels = []   # the hotel's own words price the pet differently
            elif re.search(r"1\s*-\s*\d+\s*n|\d+\+\s*n|5\+|6\+|nights?\s*[;.]|\bor\b\s*\$", narrative, re.I) and \
                    len(narr_amounts) > 1:
                labels = []   # a tiered charge the single label cannot hold
        if len(bases) == 1 and labels:
            basis, amount = labels[0]
            ext["pet_fee"] = int(round(float(amount) * 100))
            ext["fee_currency"] = "USD"
            ext["fee_basis"] = "per_night" if basis.lower() == "night" else "per_stay"
            if re.search(r"non-?refundable", text, re.I):
                ext["fee_refundable"] = False
            # Scope only when the words sit on the CHARGE: "30lbs max per pet per room
            # with non-refundable fee" scopes a weight, not the fee.
            _charge = r"(?:\$\s*\d+|\d+\s*USD|USD\s*\d+)[^.;]{0,40}?"
            if re.search(_charge + r"per\s+pet", narrative, re.I):
                ext["fee_scope"] = "per_pet"
            elif re.search(_charge + r"per\s+room", narrative, re.I):
                ext["fee_scope"] = "per_room"
        m = re.search(r"Maximum Pet Weight:\s*([0-9.]+)\s*lbs", text, re.I)
        narrative_w = {float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s*l?bs?\b|(\d+(?:\.\d+)?)\s*pounds", narrative, re.I) for x in x if x}
        if m and narrative_w and float(m.group(1)) not in narrative_w:
            m = None
        if m and float(m.group(1)) > 0:
            ext["weight_limit"] = float(m.group(1))
            ext["weight_limit_unit"] = "lb"
            if re.search(r"combined", narrative, re.I):
                ext.pop("weight_limit")
                ext.pop("weight_limit_unit")
        mc = re.search(r"Maximum Number of Pets in Room:\s*(\d)", text, re.I)
        nc = _count(narrative)
        if mc and (nc is None or nc == int(mc.group(1))):
            ext["pet_count_limit"] = int(mc.group(1))
        s = _species(narrative)
        if re.search(r"\bdogs only\b|we allow dogs|dog friendly|welcomes dogs", narrative, re.I):
            s = ["dog"]
        if s:
            ext["species_allowed"] = s
    return ext, text, conflict


_USD = re.compile(r"(?:charge of\s+|fees?\s*-\s*(?:non-refundable\s+)?)?([0-9]+(?:\.[0-9]{2})?)\s*USD", re.I)


def parse_wyndham(r):
    text = (r.get("p") or "").strip()
    ext = OrderedDict()
    conflict = None
    if re.search(r"no other pets are allowed|pets? (?:are )?not allowed|no pets allowed", text, re.I):
        ext["pets_allowed"] = False
    elif re.search(r"(?:^|[/.]\s*)(?:pets?|dogs?)\s+(?:is\s+|are\s+)?allowed|pets are welcome|pets allowed", text, re.I):
        ext["pets_allowed"] = True
    elif re.match(r"\s*pets\b.{0,60}?\bwelcome\b", text, re.I | re.S):
        ext["pets_allowed"] = True
    elif re.search(r"\b(?:\d|one|two|up to \d)\s+pets?\b.*\ballowed\b|maximum of \d pets? allowed|maximum of \d dogs", text, re.I):
        ext["pets_allowed"] = True
    elif re.search(r"\b(?:pets?|dogs?)\b[^./]{0,90}\b(?:are |is )?allowed\b", text, re.I) and not \
            re.search(r"\bno\b[^./]{0,30}\b(?:pets?|dogs?)\b|not allowed", text, re.I):
        # "Pets with a maximum weight of 75 lbs are allowed for a non-refundable charge"
        ext["pets_allowed"] = True
    ind = (r.get("pet_indicator") or "").upper()
    if "pets_allowed" in ext and ind in ("Y", "N") and (ind == "Y") != ext["pets_allowed"]:
        conflict = ("the brand's structured pet indicator is %r and the property's own policy text reads %s"
                    % (ind, "an acceptance" if ext["pets_allowed"] else "a refusal"))
    if ext.get("pets_allowed"):
        seg = re.search(r"Fees?\s*-\s*(.*?)(?:/|Other information|$)", text, re.I)
        fee_part = seg.group(1) if seg else text
        fee_part = re.split(r"sanitation fee|max(?:imum)?\s+[0-9]+\s*USD per stay|deposit", fee_part, flags=re.I)[0]
        m = _USD.search(fee_part)
        if m and re.search(r"\bfor no charge\b", text, re.I) and re.search(r"additional pets", text, re.I):
            m = None
        if m and re.search(r"subsequent pets|1st night|each additional", fee_part, re.I):
            m = None
        # A BASIS IS NEVER DEFAULTED. "Fees - 25USD per pet" states no night or stay.
        basis = ("per_night" if m and re.search(r"per\s+(?:pet\s+per\s+)?night|nightly|per\s+night\s+per\s+pet|per\s+day", fee_part, re.I)
                 else "per_stay" if m and re.search(r"per\s+stay|one[- ]time|per\s+visit", fee_part, re.I) else None)
        if m and (basis is None or re.search(r"\d+\s*-\s*\d+\s*nigh", text, re.I)):
            m = None
        if m:
            ext["pet_fee"] = int(round(float(m.group(1)) * 100))
            ext["fee_currency"] = "USD"
            ext["fee_basis"] = basis
            if re.search(r"per\s+pet|per\s+dog", fee_part, re.I):
                ext["fee_scope"] = "per_pet"
            elif re.search(r"for up to \d+ pets", fee_part, re.I):
                ext["fee_scope"] = "per_room"
            if re.search(r"non-?refundable", fee_part, re.I):
                ext["fee_refundable"] = False
        weights = {float(x) for x in _WEIGHT.findall(text)}
        if len(weights) == 1:
            ext["weight_limit"] = weights.pop()
            ext["weight_limit_unit"] = "lb"
            if re.search(r"combined", text, re.I):
                ext["weight_basis"] = "combined"
        c = _count(text)
        if c:
            ext["pet_count_limit"] = c
        s = _species(text)
        if s:
            ext["species_allowed"] = s
    return ext, text, conflict


def parse_ihg(r):
    text = html.unescape(r.get("p") or "")
    ext = OrderedDict()
    conflict = None
    if re.match(r"\s*No,\s*pets\s+are\s+not\s+allowed", text, re.I):
        ext["pets_allowed"] = False
    elif re.match(r"\s*Pets\s+are\s+welcome", text, re.I):
        ext["pets_allowed"] = True
        # OUTER BANKS GUARD. Holiday Inn Express Kitty Hawk's FAQ heading says "Pets are
        # welcome", but the hotel's OWN policy description speaks only of ADA service
        # animals and refuses emotional-support animals. A heading that accepts pets beside
        # a description that admits only service animals is two first-party statements
        # that disagree; neither publishes.
        _desc = re.search(r"Pet policy description\.\s*(.*?)(?:\nPet fee per|\nPet weight limit|$)", text, re.I | re.S)
        _desc = _desc.group(1) if _desc else ""
        if _desc and re.search(r"service animals?", _desc, re.I) and not re.search(
                r"\bwe welcome\b|\bpets?\b(?! related)[^.]{0,40}\b(?:welcome|allowed|accepted|fee)\b", _desc, re.I):
            conflict = ("the FAQ heading says 'Pets are welcome' and the hotel's own pet policy description "
                        "admits only service animals: %r" % _desc.strip()[:240])
    if ext.get("pets_allowed"):
        narrative = text.split("Pet fee per")[0].split("Pet weight limit")[0]
        m = re.search(r"Pet fee per (stay|night):\s*([0-9]+)\s*USD", text, re.I)
        if m and re.search(r"for up to \d+ nights|greater than \d+ nights|\d+ nights and beyond"
                           r"|reduces to|longer than \d+ nights|\d+\s*to\s*\d+\s*night", text, re.I):
            m = None
        if m and m.group(1).lower() == "night" and re.search(r"upon arrival|one[- ]time|per stay|flat fee|during check[- ]?in|at check[- ]?in", narrative, re.I):
            m = None
        if m and m.group(1).lower() == "stay" and re.search(r"per day|per night|nightly|daily", narrative, re.I):
            m = None
        if m:
            na = _amounts(narrative)
            if na and float(m.group(2)) not in na:
                m = None
            elif int(m.group(2)) == 0:
                m = None   # a zero in the fee field is not a published amount
            elif re.search(r"first pet|second pet|additional", narrative, re.I):
                m = None
        if m:
            ext["pet_fee"] = int(m.group(2)) * 100
            ext["fee_currency"] = "USD"
            ext["fee_basis"] = "per_stay" if m.group(1).lower() == "stay" else "per_night"
            if re.search(r"non-?\s?refundable", text, re.I):
                ext["fee_refundable"] = False
        structured = re.search(r"Pet weight limit:\s*([0-9]+)\b", text, re.I)
        narrative_w = _WEIGHT.search(narrative)
        if structured and (not narrative_w or float(narrative_w.group(1)) == float(structured.group(1))) \
                and not re.search(r"combined|all pets", narrative, re.I):
            ext["weight_limit"] = float(structured.group(1))
            ext["weight_limit_unit"] = "lb"
        c = re.search(r"\b(\d)\s+pets allowed", text, re.I)
        if c:
            nc = _count(narrative)
            if nc is None or nc == int(c.group(1)):
                ext["pet_count_limit"] = int(c.group(1))
        if re.search(r"Pets allowed:\s*Only dogs and cats allowed", text, re.I):
            ext["species_allowed"] = ["cat", "dog"]
        elif re.search(r"Pets allowed:\s*Only dogs allowed", text, re.I):
            ext["species_allowed"] = ["dog"]
    return ext, text, conflict


def parse_choice(r):
    """Choice's property page 'Pets' item: 'Pets Allowed: Yes|No / General: <the hotel's words>'.

    'Pets Allowed: No' is visible text on the property's own page, not a hidden
    boolean, and the shared first-party gate reads it as a refusal; the service-animal
    sentence beside it is carried verbatim and publishes nothing on its own. An
    acceptance label beside general words that refuse pets is a conflict.
    """
    text = (r.get("pet") or "").strip()
    ext = OrderedDict()
    conflict = None
    general = text.split("General:", 1)[1] if "General:" in text else ""
    general = re.split(r"\.\s*Service animals are permitted", general)[0]
    if re.match(r"\s*Pets Allowed:\s*No\b", text, re.I):
        ext["pets_allowed"] = False
        if re.search(r"\bpets?\s+(?:are\s+)?(?:allowed|welcome)\b", general, re.I) and not re.search(r"only service", general, re.I):
            conflict = "the page's label says 'Pets Allowed: No' and its general words accept pets: %r" % general[:200]
    elif re.match(r"\s*Pets Allowed:\s*Yes\b", text, re.I):
        ext["pets_allowed"] = True
        if re.search(r"no pets|pets are not allowed|only service animals", general, re.I):
            conflict = "the page's label says 'Pets Allowed: Yes' and its general words refuse pets: %r" % general[:200]
    if ext.get("pets_allowed"):
        amts = re.findall(r"(?:\$\s*([0-9]+(?:\.[0-9]{2})?)|([0-9]+(?:\.[0-9]{2})?)\s*USD)", general)
        fees = [float(a or b) for a, b in amts]
        refundable_deposit = re.search(r"refundable\s+(?:pet\s+)?deposit|deposit", general, re.I)
        pet_fee_amounts = []
        for m in re.finditer(r"(?:\$\s*([0-9]+(?:\.[0-9]{2})?)|\b([0-9]+(?:\.[0-9]{2})?)\s*USD)", general):
            tail = re.split(r"[,.;](?!\d)", general[m.end():m.end() + 50])[0]
            head = general[max(0, m.start() - 35):m.start()]
            if re.search(r"deposit|authorization|security", tail + " " + head, re.I):
                continue
            pet_fee_amounts.append((float(m.group(1) or m.group(2)), tail))
        if len(pet_fee_amounts) == 1:
            amount, tail = pet_fee_amounts[0]
            ctx = general
            basis = ("per_night" if re.search(r"per\s+night|nightly|per\s+day", ctx, re.I)
                     else "per_stay" if re.search(r"per\s+stay|one[- ]time", ctx, re.I) else None)
            if basis:
                ext["pet_fee"] = int(round(amount * 100))
                ext["fee_currency"] = "USD"
                ext["fee_basis"] = basis
                if re.search(r"per\s+pet|per\s+Pet", ctx, re.I):
                    ext["fee_scope"] = "per_pet"
                if re.search(r"non-?refundable", ctx, re.I):
                    ext["fee_refundable"] = False
        weights = {float(x) for x in re.findall(r"(\d+(?:\.\d+)?)\s*-?\s*(?:lbs?|pounds?|LB)\b", general, re.I)}
        if len(weights) == 1 and not re.search(r"combined", general, re.I):
            ext["weight_limit"] = weights.pop()
            ext["weight_limit_unit"] = "lb"
        c = _count(general) or (lambda m: int(m.group(1)) if m else None)(re.search(r"(\d)\s+pets?\s+per\s+room", general, re.I))
        if c:
            ext["pet_count_limit"] = c
        if re.search(r"dogs only", general, re.I):
            ext["species_allowed"] = ["dog"]
        _ = fees, refundable_deposit
    return ext, text, conflict


def parse_hyatt(r):
    """Hyatt's property page pet module: a heading ('Pets Are Welcome' / 'We Are Pet
    Friendly'), the hotel's own paragraph, then labelled Pet Fees and Weight Limits."""
    text = (r.get("p") or "").strip()
    ext = OrderedDict()
    if not text:
        return ext, text, None
    parts = [p.strip() for p in text.split("|")]
    head = parts[0]
    narrative = " ".join(parts[1:parts.index("Pet Fees")]) if "Pet Fees" in parts else " ".join(parts[1:])
    if re.match(r"(Pets Are Welcome|We Are Pet Friendly)$", head, re.I):
        ext["pets_allowed"] = True
    elif re.match(r"(No Pets|Pets? (?:are )?Not (?:Allowed|Permitted))", head, re.I):
        ext["pets_allowed"] = False
    if ext.get("pets_allowed"):
        fees = parts[parts.index("Pet Fees") + 1:parts.index("Weight Limits")] if "Pet Fees" in parts and "Weight Limits" in parts \
            else parts[parts.index("Pet Fees") + 1:] if "Pet Fees" in parts else []
        amounts = [p for p in fees if re.fullmatch(r"\$\d+(?:\.\d{2})?", p)]
        narr_amounts = _amounts(narrative)
        if len(amounts) == 1 and not narr_amounts and "STAY" in fees and not re.search(r"night", " ".join(fees), re.I):
            ext["pet_fee"] = int(round(float(amounts[0][1:]) * 100))
            ext["fee_currency"] = "USD"
            ext["fee_basis"] = "per_stay"
            if re.search(r"non-?refundable", " ".join(fees) + " " + narrative, re.I):
                ext["fee_refundable"] = False
        m = re.search(r"Individual pet weight limit \| (\d+) \| Pounds", text)
        nw = {float(x) for x in _WEIGHT.findall(narrative)}
        if m and (not nw or float(m.group(1)) in nw):
            ext["weight_limit"] = float(m.group(1))
            ext["weight_limit_unit"] = "lb"
        c = re.search(r"Maximum number of pets is (\d)", text)
        nc = _count(narrative)
        if c and (nc is None or nc == int(c.group(1))):
            ext["pet_count_limit"] = int(c.group(1))
        if re.search(r"\bdogs only\b|only dogs", narrative, re.I):
            ext["species_allowed"] = ["dog"]
    return ext, text, None


#: First-party pages read one at a time. Filled from the static and attended passes.
#: (seed, brand, name on page, street, city, postal, phone, url, sha256, bytes, lane,
#:  surface, quote, extraction, binding method, conflict)
BRAND_PAGES = []


def _row(brand, lane, code, req, final, sig, sha, nbytes, surface, quote, ext, zips, method, conflict=None):
    z = (sig.get("postal_code") or "")[:5]
    confirmed = bool(sig.get("address_on_page") and z)
    from scripts.pettripfinder import pinehurst_southern_pines_nc_geography_001 as GEO
    if GEO.classify_postal(z, sig.get("locality"))[0] == "OUTSIDE":
        zips = {k: v for k, v in zips.items() if k != z}
    return OrderedDict([
        ("brand", brand), ("lane", lane), ("property_code", code),
        ("requested_url", req), ("final_url", final), ("captured_at", CAPTURED_AT),
        ("document_bytes", nbytes), ("document_sha256", sha),
        ("identity_signals", sig), ("identity_confirmed", confirmed),
        ("identity_binding_method", method), ("surface", surface),
        ("exact_quote", quote), ("operative_excerpt_sha256", _excerpt_sha(quote)),
        ("extraction", ext), ("first_party_conflict", conflict),
        ("in_market", z in zips), ("corridor", zips.get(z, "")),
        ("market_verdict", ("IN_MARKET" if z in zips else "OUTSIDE_MARKET") if confirmed
         else "IDENTITY_NOT_STATED"),
    ])


def _f(v):
    try:
        return float(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


def build():
    zips = zips_of_registry()
    out = []
    digests = OrderedDict()
    for name, want in PAYLOAD_DIGESTS.items():
        rows = _load(os.path.join(RAW, name), [])
        got = hashlib.sha256(json.dumps(rows, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
        if got != want:
            raise SystemExit("payload %s digest %s != the browser's %s" % (name, got, want))
        digests[name] = got

    for r in _load(os.path.join(RAW, "hilton_rows.json"), []):
        ext, quote, conflict = parse_hilton(r)
        sig = OrderedDict([("name_on_page", r.get("n")), ("address_on_page", r.get("st")),
                           ("postal_code", (r.get("z") or "")[:5]), ("locality", r.get("ci")),
                           ("region", r.get("rg")), ("phone_on_page", r.get("ph")),
                           ("property_code_on_page", r["c"]), ("lat", _f(r.get("la"))), ("lng", _f(r.get("lo")))])
        u = "https://www.hilton.com/en/hotels/%s-%s/" % (r["c"], r["sl"])
        out.append(_row("HILTON", "ATTENDED_BROWSER", r["c"], u, u, sig, r.get("h"), r.get("b"),
                        "__NEXT_DATA__ petsInfo node", quote, ext, zips,
                        "PROPERTY_CODE_AND_ADDRESS_FROM_THE_PAGES_OWN_DATA", conflict))

    for r in _load(os.path.join(RAW, "marriott_rows.json"), []):
        if r.get("s") != 200 or not r.get("st"):
            continue
        ext, quote, conflict = parse_marriott(r)
        code = r["c"][:5]
        u = "https://www.marriott.com/en-us/hotels/%s/overview/" % r["c"]
        sig = OrderedDict([("name_on_page", r.get("n")), ("address_on_page", r.get("st")),
                           ("postal_code", (r.get("z") or "")[:5]), ("locality", r.get("ci")),
                           ("region", "NC"), ("phone_on_page", r.get("ph")), ("property_code_on_page", code),
                           ("lat", _f(r.get("la"))), ("lng", _f(r.get("lo")))])
        out.append(_row("MARRIOTT", "ATTENDED_BROWSER", code, u, u, sig, r.get("h"), r.get("b"),
                        "HOTEL INFORMATION block, Pet Policy row", quote, ext, zips,
                        "HOTEL_JSONLD_ADDRESS_AND_PROPERTY_CODE", conflict))

    wyn = _load(os.path.join(RAW, "wyndham_rows.json"), {})
    for r in wyn.get("rows", []):
        ext, quote, conflict = parse_wyndham(r)
        sig = OrderedDict([("name_on_page", r.get("n")), ("address_on_page", r.get("st")),
                           ("postal_code", (r.get("z") or "")[:5]), ("locality", r.get("ci")),
                           ("region", r.get("rg")), ("phone_on_page", r.get("ph")),
                           ("property_code_on_page", r.get("id")), ("lat", _f(r.get("lat"))), ("lng", _f(r.get("lng")))])
        out.append(_row("WYNDHAM", "DIRECT_STATIC_FETCH", r.get("id"), r["u"], r.get("api_url"), sig,
                        r.get("h"), r.get("b"), "the brand's own property service hotelPolicies.petpolicy (the page's .pet-policy-desc text)",
                        quote, ext, zips, "PROPERTY_SERVICE_ADDRESS_AND_PROPERTY_ID", conflict))

    for r in _load(os.path.join(RAW, "ihg_rows.json"), []):
        if r.get("outside") or not r.get("st"):
            continue
        ext, quote, conflict = parse_ihg(r)
        name = re.sub(r"^Can I bring my pet to\s+|\?$", "", html.unescape(r.get("q") or ""))
        u = "https://www.ihg.com/%s/hotels/us/en/%s/%s/hoteldetail" % (r["br"], r["ct"], r["c"])
        sig = OrderedDict([("name_on_page", r.get("n") or name), ("address_on_page", r.get("st")),
                           ("postal_code", (r.get("z") or "")[:5]), ("locality", r.get("ci")), ("region", "NC"),
                           ("phone_on_page", r.get("ph")), ("property_code_on_page", r["c"]),
                           ("lat", _f(r.get("la"))), ("lng", _f(r.get("lo")))])
        out.append(_row("IHG", "ATTENDED_BROWSER", r["c"], u, u, sig, r.get("h"), r.get("b"),
                        "the brand's own FAQ answer to 'Can I bring my pet to X?'",
                        quote, ext, zips, "HOTEL_JSONLD_ADDRESS_AND_PROPERTY_CODE", conflict))

    for r in _load(os.path.join(RAW, "choice_rows.json"), []):
        if r.get("s") != 200 or not r.get("st"):
            continue
        ext, quote, conflict = parse_choice(r)
        u = "https://www.choicehotels.com/north-carolina/%s/%s" % (r["path"], r["c"])
        sig = OrderedDict([("name_on_page", r.get("n")), ("address_on_page", r.get("st")),
                           ("postal_code", (r.get("z") or "")[:5]), ("locality", r.get("ci")), ("region", "NC"),
                           ("phone_on_page", r.get("ph")), ("property_code_on_page", r["c"]),
                           ("lat", _f(r.get("la"))), ("lng", _f(r.get("lo")))])
        out.append(_row("CHOICE", "ATTENDED_BROWSER", r["c"], u, u, sig, r.get("h"), r.get("b"),
                        "the property page's own 'Pets' item (label and general policy words)",
                        quote, ext, zips, "HOTEL_JSONLD_ADDRESS_AND_PROPERTY_CODE", conflict))

    for r in _load(os.path.join(RAW, "hyatt_rows.json"), []):
        if r.get("outside") or r.get("s") != 200 or not r.get("st"):
            continue
        ext, quote, conflict = parse_hyatt(r)
        sig = OrderedDict([("name_on_page", r.get("n")), ("address_on_page", r.get("st")),
                           ("postal_code", (r.get("z") or "")[:5]), ("locality", r.get("ci")), ("region", "NC"),
                           ("phone_on_page", r.get("ph")), ("property_code_on_page", r["c"]),
                           ("lat", _f(r.get("la"))), ("lng", _f(r.get("lo")))])
        out.append(_row("HYATT", "ATTENDED_BROWSER", r["c"], r["u"], r["u"], sig, r.get("h"), r.get("b"),
                        "the property page's own pet module (heading, the hotel's paragraph, Pet Fees, Weight Limits)",
                        quote, ext, zips, "HOTEL_JSONLD_ADDRESS_AND_PROPERTY_CODE", conflict))

    for extra in _load(os.path.join(RAW, "brand_pages.json"), []) + BRAND_PAGES:
        sig = OrderedDict([("name_on_page", extra["name"]), ("address_on_page", extra["street"]),
                           ("postal_code", extra["postal"]), ("locality", extra["city"]), ("region", "NC"),
                           ("phone_on_page", extra.get("phone")), ("property_code_on_page", extra.get("code")),
                           ("lat", extra.get("lat")), ("lng", extra.get("lng"))])
        row = _row(extra["brand"], extra["lane"], extra.get("code"), extra["url"], extra.get("final_url") or extra["url"],
                   sig, extra["sha256"], extra["bytes"], extra["surface"], extra["quote"],
                   OrderedDict(extra.get("extraction") or {}), zips, extra["method"], extra.get("conflict"))
        row["brand_page_seed"] = extra.get("seed")
        out.append(row)

    in_market = [r for r in out if r["in_market"]]
    return OrderedDict([
        ("schema", SCHEMA), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "10-14 -- first-party reads: Marriott, Hilton, IHG (attended same-origin), Wyndham (plain client) and brand pages"),
        ("as_of", CAPTURED_AT),
        ("lane", "ATTENDED_BROWSER (the operator's real Chrome session; free) + DIRECT_STATIC_FETCH"),
        ("authorization", "the operator's work order authorises the attended lane; no credential entered"),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("firecrawl_credits", 0),
        ("payload_digests", digests),
        ("wyndham_retired_routes", wyn.get("retired_routes_redirected_to_brand_search", [])),
        ("wyndham_error_rows", wyn.get("errors", [])),
        ("no_bot_check_was_answered",
         "every page served a plain navigation, same-origin fetch or plain client request."),
        ("counts", OrderedDict([
            ("pages_read", len(out)),
            ("by_brand", OrderedDict(sorted(Counter(r["brand"] for r in out).items()))),
            ("identity_confirmed", sum(1 for r in out if r["identity_confirmed"])),
            ("in_market", len(in_market)),
            ("outside_market", len(out) - len(in_market)),
            ("in_market_pets_allowed_true", sum(1 for r in in_market if r["extraction"].get("pets_allowed") is True)),
            ("in_market_pets_allowed_false", sum(1 for r in in_market if r["extraction"].get("pets_allowed") is False)),
            ("in_market_first_party_conflicts", sum(1 for r in in_market if r.get("first_party_conflict"))),
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
