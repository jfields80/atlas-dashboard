"""PTF-ORLANDO-FL-HARDENED-V2-SOURCE-READY-001 -- Phases 12-16: every first-party policy read, in one shape.

Consolidates the reads each acquisition lane persisted into the attended-capture row shape the census and the clean
authority consume (identity signals the page itself states, the durable document reference, the operative quote,
the parsed facts and any first-party conflict):

  WYNDHAM   DIRECT_STATIC_FETCH -- the brand's own property service (orlando_fl_v2_wyndham_lane_001 raw rows)
  STATIC    DIRECT_STATIC_FETCH -- the shared direct_http_capture lane (orlando_fl_v2_free_static_capture_001)
  FIRECRAWL FIRECRAWL           -- the routed / discovered / probe Firecrawl pass (orlando_fl_v2_firecrawl_pass_001)
  MARRIOTT  ATTENDED_BROWSER    -- property overview pages read through the supported accessibility reader
  HILTON    ATTENDED_BROWSER    -- property hotel-info pages read through the supported accessibility reader

The per-family parsers (Marriott, Wyndham, Hilton, IHG, Choice, Hyatt, Best Western) are the Savannah GA helper's,
copied market-locally with every guard they carry. A fact is written only when the page states it; a basis or scope is
never defaulted.

DURABILITY. Static and Firecrawl rows reference the persisted rendered document (sha256 of rendered.html under
data/acquisition/<run>/). Wyndham rows reference the persisted property-service document (sha256). ATTENDED_BROWSER
rows reference the committed transcription line under markets/staging/orlando-fl/raw_captures/: the accessibility
reader returns the page's text nodes verbatim, and the row's document_sha256 is the sha256 of that canonical JSON
transcription (declared as TRANSCRIPTION_SHA256, never passed off as a page hash).

Output:
  launch_packages/pettripfinder/markets/reports/orlando_fl_v2_policy_reads_001.json
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

from scripts.pettripfinder import orlando_fl_v2_geography_001 as GEO  # noqa: E402

WORK_ORDER = "PTF-ORLANDO-FL-HARDENED-V2-SOURCE-READY-001"
MARKET_ID = "orlando-fl"
SCHEMA = "ptf-attended-capture/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
RAW = os.path.join(PKG, "markets", "staging", "orlando-fl", "raw_captures")
REGISTRY = os.path.join(REPORTS, "orlando_fl_v2_corridor_registry_001.json")
STATIC = os.path.join(REPORTS, "orlando_fl_v2_free_static_capture_001.json")
FIRECRAWL = os.path.join(REPORTS, "orlando_fl_v2_firecrawl_pass_001.json")
OUT = os.path.join(REPORTS, "orlando_fl_v2_policy_reads_001.json")
CAPTURED_AT = "2026-09-15"


def _load(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def _jsonl(path):
    out = []
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8-sig") as fh:
        for line in fh:
            line = line.strip().lstrip("\ufeff")
            if line:
                out.append(json.loads(line))
    return out


def _excerpt_sha(text):
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def zips_of_registry():
    reg = _load(REGISTRY)
    return {z: c["corridor_id"] for c in reg["corridors"] for z in c["included_postal_codes"]}


def _f(v):
    try:
        return float(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


_WEIGHT = re.compile(r"(\d+(?:\.\d+)?)\s*(?:lbs?|pounds)\b", re.I)
_WORDS = {"one": 1, "two": 2, "three": 3}


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
    # SAVANNAH GUARD. The Westin Savannah Harbor's row has no "Pets Welcome" heading: the block
    # opens ">\nPet Policy\n<the resort's own paragraph>" and runs on into career and award copy.
    # Only the paragraph is the operative statement; nothing after it is quoted.
    if re.match(r">\s*\nPet Policy\n", raw):
        para = raw.split("\n")[2] if len(raw.split("\n")) > 2 else ""
        ext = OrderedDict()
        if re.search(r"welcome to bring a dog", para, re.I):
            ext["pets_allowed"] = True
            w = re.search(r"dog weighing up to (\d+) pounds", para, re.I)
            if w:
                ext["weight_limit"] = float(w.group(1))
                ext["weight_limit_unit"] = "lb"
            if re.search(r"No other pets are permitted", para, re.I):
                ext["species_allowed"] = ["dog"]
            m = re.search(r"A (\d+) USD non-refundable daily fee", para, re.I)
            if m:
                ext["pet_fee"] = int(m.group(1)) * 100
                ext["fee_currency"] = "USD"
                ext["fee_basis"] = "per_night"
                ext["fee_refundable"] = False
        return ext, para, None
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
        # SAVANNAH GUARDS. A labelled fee beside the hotel's own tier ("$75 for 1–5 nights; call hotel
        # for stays over 5 nights") or cap ("USD $50 per night fee up to USD $150 max charge") is a charge
        # the single label cannot hold; no fee publishes.
        if re.search(r"\d+\s*[-–]\s*\d+\s*nights|over\s+\d+\s+nights|\d\+\s*nights|max(?:imum)?\s+charge", narrative, re.I):
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
    # SAVANNAH GUARDS. "Pets are not allowed in designated rooms" / "in suite rooms" restricts rooms and
    # refuses nothing; "We welcome pets at a rate of ..." and "Pets are accepted for ..." accept.
    if re.match(r"\s*(?:we welcome pets\b|pets are accepted\b)", text, re.I):
        ext["pets_allowed"] = True
    elif re.search(r"no other pets are allowed|pets? (?:are )?not allowed(?!\s+in\b)|no pets allowed", text, re.I):
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
        # SAVANNAH GUARD: "35.00 USD per pet per night with a max charge of 50.00 USD per pet per reservation"
        # is a capped charge the single amount cannot hold.
        if m and re.search(r"max(?:imum)?\s+charge", text, re.I):
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
                # SAVANNAH GUARD: "Non-Refundable deposit of 50.00 USD" describes a deposit, not the fee.
                if re.search(r"non-?refundable\s+(?:pet\s+)?(?:fee|charge)", ctx, re.I):
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
    elif re.match(r"We Are Dog Friendly$", head, re.I) and re.search(r"Your dog is welcome to stay", text, re.I):
        # SAVANNAH: Hyatt Regency Savannah's module is headed "We Are Dog Friendly".
        ext["pets_allowed"] = True
        ext["species_allowed"] = ["dog"]
    elif re.match(r"(No Pets|Pets? (?:are )?Not (?:Allowed|Permitted))", head, re.I):
        ext["pets_allowed"] = False
    if ext.get("pets_allowed") and not re.search(r"\d+\s*[-–]\s*\d+\s*nights|or more nights|nights or more", text, re.I):
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


def parse_bestwestern(r):
    """Best Western's property page FAQ: 'Q. Is the X Pet Friendly?' and the hotel's own answer.

    'Pets are not accepted.' is the page's own refusal. 'Pets may be accepted. Please contact the
    hotel for full details.' states neither acceptance nor refusal and publishes nothing. The
    JSON-LD ``petsAllowed`` boolean is never read (it is false on the page whose FAQ accepts dogs)."""
    text = (r.get("p") or "").strip()
    ext = OrderedDict()
    if re.match(r"Pets are not accepted\.?$", text, re.I):
        ext["pets_allowed"] = False
    elif re.match(r"We are Pet Friendly\b", text, re.I):
        ext["pets_allowed"] = True
        w = re.search(r"size limit for any one dog shall be (\d+) pounds", text, re.I)
        if w:
            ext["weight_limit"] = float(w.group(1))
            ext["weight_limit_unit"] = "lb"
        c = re.search(r"allow up to (two|\d) dogs", text, re.I)
        if c:
            ext["pet_count_limit"] = _WORDS.get(c.group(1).lower()) or int(c.group(1))
        m = re.search(r"rate is (\d+) USD per day", text, re.I)
        if m:
            ext["pet_fee"] = int(m.group(1)) * 100
            ext["fee_currency"] = "USD"
            ext["fee_basis"] = "per_night"
    return ext, text, None




def _row(brand, lane, code, req, final, sig, sha, nbytes, surface, quote, ext, zips, method, conflict=None,
         sha_kind="DOCUMENT_SHA256", extra=None):
    z = (sig.get("postal_code") or "")[:5]
    confirmed = bool(sig.get("address_on_page") and z)
    if GEO.classify_postal(z, sig.get("locality"))[0] == "OUTSIDE":
        zips = {k: v for k, v in zips.items() if k != z}
    row = OrderedDict([
        ("brand", brand), ("lane", lane), ("property_code", code),
        ("requested_url", req), ("final_url", final), ("captured_at", CAPTURED_AT),
        ("document_bytes", nbytes), ("document_sha256", sha), ("document_sha256_kind", sha_kind),
        ("identity_signals", sig), ("identity_confirmed", confirmed),
        ("identity_binding_method", method), ("surface", surface),
        ("exact_quote", quote), ("operative_excerpt_sha256", _excerpt_sha(quote)),
        ("extraction", ext), ("first_party_conflict", conflict),
        ("in_market", z in zips), ("corridor", zips.get(z, "")),
        ("market_verdict", ("IN_MARKET" if z in zips else "OUTSIDE_MARKET") if confirmed else "IDENTITY_NOT_STATED"),
    ])
    for k, v in (extra or {}).items():
        row[k] = v
    return row


def _split_address(addr):
    """'7499 Augusta National Drive, Orlando, Florida, USA, 32822' (Marriott) or
    '191 East Pine Street, Orlando, Florida, 32801, USA' (Hilton) -> street, city, state, zip."""
    parts = [p.strip() for p in (addr or "").split(",") if p.strip()]
    z = next((p for p in parts if re.fullmatch(r"\d{5}(-\d{4})?", p)), "")
    rest = [p for p in parts if p != z and p.upper() not in ("USA", "US", "UNITED STATES")]
    street = rest[0] if rest else ""
    city = rest[1] if len(rest) > 1 else ""
    state = rest[2] if len(rest) > 2 else ""
    return street, city, state, z[:5]


def _transcription_sha(r):
    return hashlib.sha256(json.dumps(r, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")).hexdigest()


def marriott_rows(zips):
    out = []
    seen = set()
    for path in ("marriott_browser_rows.jsonl", "marriott_browser_rows_agent.jsonl", "marriott_browser_rows_retry.jsonl"):
        for r in _jsonl(os.path.join(RAW, path)):
            if r.get("status", "OK") != "OK" or r["c"] in seen:
                continue
            seen.add(r["c"])
            pet = [p for p in (r.get("pet") or []) if p != "Pet Policy"]
            # one line per text node, the order the page renders them: the shape parse_marriott reads
            raw = "\n".join(pet)
            street, city, state, z = _split_address(r.get("addr"))
            ext, quote, conflict = parse_marriott({"p": raw})
            quote = "Pet Policy: " + " | ".join(pet)
            sig = OrderedDict([("name_on_page", r.get("n")), ("address_on_page", street), ("postal_code", z),
                               ("locality", city), ("region", "FL" if state.lower() in ("florida", "fl") else state),
                               ("phone_on_page", re.sub(r"^Contact us at phone\s*", "", r.get("ph") or "")),
                               ("property_code_on_page", r["c"]), ("lat", None), ("lng", None)])
            u = r.get("final_url") or r["u"]
            out.append(_row("MARRIOTT", "ATTENDED_BROWSER", r["c"], r["u"], u, sig, _transcription_sha(r),
                            len(json.dumps(r, ensure_ascii=False).encode("utf-8")),
                            "HOTEL INFORMATION block, Pet Policy row (accessibility-tree text nodes, verbatim)",
                            quote, ext, zips, "PROPERTY_CODE_IN_ROUTE_AND_ADDRESS_ON_THE_PAGE", conflict,
                            sha_kind="TRANSCRIPTION_SHA256", extra={"raw_capture": "raw_captures/" + path}))
    return out


def _hilton_fields(pets):
    """Pair each Hilton label with its value; the reader returns values before or after their labels."""
    vals = [p for p in pets if p and p != "Pets"]
    labels = ("Pets allowed:", "Non-refundable fee:", "Refundable deposit:", "Pet policy:", "Service animals:",
              "Deposit:", "Fee:", "Max weight:", "Max pets:")
    out = OrderedDict()
    for i, v in enumerate(vals):
        if v in labels:
            nxt = vals[i + 1] if i + 1 < len(vals) and vals[i + 1] not in labels else None
            prv = vals[i - 1] if i > 0 and vals[i - 1] not in labels else None
            out[v] = (nxt, prv)
    return vals, out


def hilton_rows(zips):
    out = []
    seen = set()
    # the retry pass (after hilton.com's error-page wall lifted) fills codes the first pass recorded BLOCKED or never
    # reached; a code read OK in the first pass is never re-read
    for path in ("hilton_browser_rows.jsonl", "hilton_browser_rows_retry.jsonl"):
      for r in _jsonl(os.path.join(RAW, path)):
        if r.get("status") != "OK":
            continue
        code = (re.search(r"/hotels/([a-z0-9]+)-", r["u"]) or [None, ""])[1]
        if code in seen:
            continue
        seen.add(code)
        vals, fields = _hilton_fields(r.get("pets") or [])
        # the value belongs to the label beside which it renders; a value that renders BEFORE its label (the
        # reader's ref order) is taken when the label is followed by another label
        def val(label):
            nxt, prv = fields.get(label, (None, None))
            order_values_first = bool(vals) and vals[0] not in fields
            return (prv if order_values_first else nxt) or nxt or prv
        pa_text = (val("Pets allowed:") or "").strip()
        pa = True if pa_text.lower().startswith("yes") else False if pa_text.lower().startswith("no") else None
        # a section that renders only the sentence "Pets not allowed" (no labelled rows) is the page's own refusal
        if pa is None and any(re.fullmatch(r"\s*pets\s+(?:are\s+)?not\s+allowed\.?\s*", v, re.I) for v in vals):
            pa, pa_text = False, ""
            standalone = next(v for v in vals if re.fullmatch(r"\s*pets\s+(?:are\s+)?not\s+allowed\.?\s*", v, re.I))
        else:
            standalone = ""
        fee = val("Non-refundable fee:")
        desc = val("Pet policy:") or ""
        fnum = (re.search(r"\$\s*([0-9]+(?:\.[0-9]{2})?)", fee or "") or [None, None])[1]
        ext, _q, conflict = parse_hilton({"pa": pa, "d": ("Pets allowed" if pa else "No pets" if pa is False else "") + ". " + desc,
                                         "f": float(fnum) if fnum else None})
        parts = ["Pets allowed: %s" % pa_text] if pa_text else ([standalone] if standalone else [])
        if fee:
            parts.append("Non-refundable fee: %s" % fee)
        if desc:
            parts.append("Pet policy: %s" % desc)
        quote = ". ".join(parts)
        street, city, state, z = _split_address(r.get("addr"))
        sig = OrderedDict([("name_on_page", r.get("n")), ("address_on_page", street), ("postal_code", z),
                           ("locality", city), ("region", "FL" if state.lower() in ("florida", "fl") else state),
                           ("phone_on_page", r.get("ph")), ("property_code_on_page", code), ("lat", None), ("lng", None)])
        out.append(_row("HILTON", "ATTENDED_BROWSER", code, r["u"], r.get("final_url") or r["u"], sig,
                        _transcription_sha(r), len(json.dumps(r, ensure_ascii=False).encode("utf-8")),
                        "hotel-info page Pets section (accessibility-tree text nodes, verbatim)", quote, ext, zips,
                        "PROPERTY_CODE_IN_ROUTE_AND_ADDRESS_ON_THE_PAGE", conflict, sha_kind="TRANSCRIPTION_SHA256",
                        extra={"raw_capture": "raw_captures/" + path}))
    return out


def wyndham_rows(zips):
    out = []
    wyn = _load(os.path.join(RAW, "wyndham_rows.json"), {}) or {}
    for r in wyn.get("rows", []):
        ext, quote, conflict = parse_wyndham(r)
        sig = OrderedDict([("name_on_page", r.get("n")), ("address_on_page", r.get("st")),
                           ("postal_code", (r.get("z") or "")[:5]), ("locality", r.get("ci")),
                           ("region", r.get("rg")), ("phone_on_page", r.get("ph")),
                           ("property_code_on_page", r.get("id")), ("lat", _f(r.get("lat"))), ("lng", _f(r.get("lng")))])
        out.append(_row("WYNDHAM", "DIRECT_STATIC_FETCH", r.get("id"), r["u"], r.get("api_url"), sig, r.get("h"), r.get("b"),
                        "the brand's own property service hotelPolicies.petpolicy (the page's .pet-policy-desc text)",
                        quote, ext, zips, "PROPERTY_SERVICE_ADDRESS_AND_PROPERTY_ID", conflict))
    return out, wyn


_WORD_NUM = {"one": 1, "two": 2, "three": 3}


def _split_us_address(addr):
    """'9801 International Drive, Orlando, FL 32819, United States of America' (Hyatt) or
    '5618 Vineland Road, Orlando, Florida 32819 United States' (Best Western) -> street, city, state, zip."""
    z = (re.search(r"\b(\d{5})(?:-\d{4})?\b(?!.*\b\d{5}\b)", addr or "") or [None, ""])[1]
    parts = [p.strip() for p in re.sub(r"\b\d{5}(?:-\d{4})?\b", "", addr or "").split(",")]
    parts = [re.sub(r"\s*United States( of America)?\s*$", "", p).strip() for p in parts]
    parts = [p for p in parts if p]
    street = parts[0] if parts else ""
    city = parts[1] if len(parts) > 1 else ""
    state = parts[2] if len(parts) > 2 else ""
    return street, city, state, z


def hyatt_rows(zips):
    out = []
    for r in _jsonl(os.path.join(RAW, "hyatt_browser_rows.jsonl")):
        if r.get("status") != "OK":
            continue
        pet = r.get("pet") or []
        ext, _q, conflict = parse_hyatt({"p": " | ".join(pet)})
        quote = " | ".join(pet)
        street, city, state, z = _split_us_address(r.get("addr"))
        sig = OrderedDict([("name_on_page", r.get("n")), ("address_on_page", street), ("postal_code", z), ("locality", city),
                           ("region", "FL"), ("phone_on_page", r.get("ph")), ("property_code_on_page", r["c"]),
                           ("lat", None), ("lng", None)])
        out.append(_row("HYATT", "ATTENDED_BROWSER", r["c"], r["u"], r.get("final_url") or r["u"], sig, _transcription_sha(r),
                        len(json.dumps(r, ensure_ascii=False).encode("utf-8")),
                        "the property page's own pet module (accessibility-tree text nodes, verbatim)", quote, ext, zips,
                        "PROPERTY_CODE_IN_ROUTE_AND_ADDRESS_ON_THE_PAGE", conflict, sha_kind="TRANSCRIPTION_SHA256",
                        extra={"raw_capture": "raw_captures/hyatt_browser_rows.jsonl"}))
    return out


def resort_rows(zips):
    """Resort collections read one page at a time (Disney's own resort pages): the page's own dog / pet section."""
    out = []
    for r in _jsonl(os.path.join(RAW, "resort_browser_rows.jsonl")):
        if r.get("status") != "OK":
            continue
        pet = r.get("pet") or []
        text = " ".join(pet)
        ext = OrderedDict()
        if re.search(r"dog-friendly accommodations", text, re.I) and re.search(r"bring your .{0,30}(pooch|dog)", text, re.I):
            ext["pets_allowed"] = True
            ext["species_allowed"] = ["dog"]
            m = re.search(r"Limit (\d) dogs per room", text)
            if m:
                ext["pet_count_limit"] = int(m.group(1))
        sig = OrderedDict([("name_on_page", r.get("n")), ("address_on_page", r.get("st")), ("postal_code", r.get("z")),
                           ("locality", r.get("ci")), ("region", "FL"), ("phone_on_page", ""), ("property_code_on_page", ""),
                           ("lat", None), ("lng", None)])
        out.append(_row(r["brand"], "ATTENDED_BROWSER", "", r["u"], r.get("final_url") or r["u"], sig, _transcription_sha(r),
                        len(json.dumps(r, ensure_ascii=False).encode("utf-8")),
                        "the resort's own page, Dog-Friendly Accommodations section (accessibility-tree text, verbatim)",
                        " | ".join(pet), ext, zips, "ADDRESS_ON_THE_RESORTS_OWN_PAGE", None, sha_kind="TRANSCRIPTION_SHA256",
                        extra={"raw_capture": "raw_captures/resort_browser_rows.jsonl"}))
    return out


def choice_rows(zips):
    """Choice property pages fetched by Firecrawl and re-read offline (orlando_fl_v2_choice_reread_001)."""
    out = []
    for r in _load(os.path.join(RAW, "choice_rows.json"), []) or []:
        if not r.get("st") or not r.get("pet"):
            continue
        ext, quote, conflict = parse_choice(r)
        sig = OrderedDict([("name_on_page", r.get("n")), ("address_on_page", r.get("st")), ("postal_code", r.get("z")),
                           ("locality", r.get("ci")), ("region", "FL"), ("phone_on_page", r.get("ph")),
                           ("property_code_on_page", r.get("c")), ("lat", None), ("lng", None)])
        out.append(_row("CHOICE", "FIRECRAWL", r.get("c"), r["u"], r.get("final_url") or r["u"], sig, r.get("h"), r.get("b"),
                        "the property page's own 'Pets' item (label and general policy words), rendered by Firecrawl",
                        quote, ext, zips, "PROPERTY_CODE_AND_ADDRESS_FROM_THE_PAGES_OWN_DATA", conflict,
                        extra={"artifact_dir": r.get("artifact"), "raw_capture": "raw_captures/choice_rows.json"}))
    return out


def ihg_rows(zips):
    """IHG pages rendered by Firecrawl, re-read offline (orlando_fl_v2_ihg_reread_001): the property FAQ's pet answer."""
    out = []
    for r in _load(os.path.join(RAW, "ihg_rows.json"), []) or []:
        if not r.get("st") or not r.get("p"):
            continue
        ext, quote, conflict = parse_ihg(r)
        sig = OrderedDict([("name_on_page", r.get("n")), ("address_on_page", r.get("st")), ("postal_code", r.get("z")),
                           ("locality", ""), ("region", "FL"), ("phone_on_page", r.get("ph")),
                           ("property_code_on_page", r.get("c")), ("lat", None), ("lng", None)])
        out.append(_row("IHG", "FIRECRAWL", r.get("c"), r["u"], r.get("final_url") or r["u"], sig, r.get("h"), r.get("b"),
                        "the brand's own FAQ answer to 'Can I bring my pet to X?', rendered by Firecrawl",
                        (r.get("q") or "") + "\n" + quote, ext, zips, "PROPERTY_CODE_AND_ADDRESS_FROM_THE_PAGES_OWN_DATA",
                        conflict, extra={"artifact_dir": r.get("artifact"), "raw_capture": "raw_captures/ihg_rows.json"}))
    return out


def loews_rows(zips):
    out = []
    for r in (_load(os.path.join(RAW, "loews_rows.json"), {}) or {}).get("rows", []):
        if r.get("s") != 200 or not r.get("st") or not r.get("p"):
            continue
        text = r["p"]
        ext = OrderedDict()
        if re.search(r"\bpets are permitted\b", text, re.I):
            ext["pets_allowed"] = True
            if re.search(r"no more than two pets", text, re.I):
                ext["pet_count_limit"] = 2
        elif re.search(r"\b(no pets are permitted|pets are not permitted)\b", text, re.I):
            ext["pets_allowed"] = False
        sig = OrderedDict([("name_on_page", r.get("n")), ("address_on_page", r.get("st")), ("postal_code", r.get("z")),
                           ("locality", r.get("ci")), ("region", "FL"), ("phone_on_page", r.get("ph")),
                           ("property_code_on_page", ""), ("lat", None), ("lng", None)])
        out.append(_row("LOEWS", "DIRECT_STATIC_FETCH", "", r["u"], r.get("final_url") or r["u"], sig, r.get("h"), r.get("b"),
                        "the property page's own Hotel Policies pet sentence", text, ext, zips,
                        "HOTEL_JSONLD_ADDRESS_ON_THE_PROPERTYS_OWN_PAGE", None))
    return out


def bestwestern_rows(zips):
    out = []
    for r in _jsonl(os.path.join(RAW, "bestwestern_browser_rows.jsonl")):
        if r.get("status") != "OK":
            continue
        pet = [p for p in (r.get("pet") or []) if p != "Pet Policy"]
        text = " ".join(pet)
        ext, _q, conflict = parse_bestwestern({"p": text})
        street, city, state, z = _split_us_address(r.get("addr"))
        sig = OrderedDict([("name_on_page", r.get("n")), ("address_on_page", street), ("postal_code", z), ("locality", city),
                           ("region", "FL"), ("phone_on_page", r.get("ph")), ("property_code_on_page", r["c"]),
                           ("lat", None), ("lng", None)])
        out.append(_row("BEST_WESTERN", "ATTENDED_BROWSER", r["c"], r["u"], r.get("final_url") or r["u"], sig,
                        _transcription_sha(r), len(json.dumps(r, ensure_ascii=False).encode("utf-8")),
                        "the property page's own Hotel Policies 'Pet Policy' item (accessibility-tree text, verbatim)",
                        "Pet Policy: " + text, ext, zips, "PROPERTY_CODE_IN_ROUTE_AND_ADDRESS_ON_THE_PAGE", conflict,
                        sha_kind="TRANSCRIPTION_SHA256", extra={"raw_capture": "raw_captures/bestwestern_browser_rows.jsonl"}))
    return out


def esa_rows(zips):
    """Extended Stay America: the property page's own FAQPage answer to 'Is <property> pet friendly?'."""
    out = []
    doc = _load(os.path.join(RAW, "esa_rows.json"), {}) or {}
    for r in doc.get("rows", []):
        if r.get("s") != 200 or not r.get("st") or not r.get("p"):
            continue
        ans = r["p"].strip()
        ext = OrderedDict()
        if re.match(r"yes\b", ans, re.I) and re.search(r"pet[- ]friendly|pets? (?:are )?(?:welcome|allowed)", ans, re.I):
            ext["pets_allowed"] = True
            m = re.match(r"A maximum of (two|one|three|\d) pets are allowed in each suite", r.get("count_sentence") or "")
            if m:
                ext["pet_count_limit"] = _WORD_NUM.get(m.group(1).lower()) or int(m.group(1))
        elif re.match(r"no\b", ans, re.I):
            ext["pets_allowed"] = False
        quote = "%s %s" % (r.get("q") or "", ans)
        if ext.get("pet_count_limit"):
            quote += " " + r["count_sentence"] + "."
        sig = OrderedDict([("name_on_page", r.get("n")), ("address_on_page", r.get("st")), ("postal_code", r.get("z")),
                           ("locality", r.get("ci")), ("region", r.get("rg")), ("phone_on_page", r.get("ph")),
                           ("property_code_on_page", ""), ("lat", None), ("lng", None)])
        out.append(_row("EXTENDED_STAY", "DIRECT_STATIC_FETCH", "", r["u"], r.get("final_url") or r["u"], sig, r.get("h"),
                        r.get("b"), "the property page's own FAQPage answer to 'Is <property> pet friendly?'", quote.strip(),
                        ext, zips, "HOTEL_JSONLD_ADDRESS_ON_THE_PROPERTYS_OWN_PAGE", None))
    return out


def independent_rows(zips):
    """Independents' own policy / FAQ pages (orlando_fl_v2_independent_reads_001): verbatim sentences, explicit facts."""
    out = []
    for r in (_load(os.path.join(RAW, "independent_rows.json"), {}) or {}).get("rows", []):
        sig = OrderedDict([("name_on_page", r.get("n")), ("address_on_page", r.get("st")), ("postal_code", r.get("z")),
                           ("locality", ""), ("region", "FL"), ("phone_on_page", r.get("ph")),
                           ("property_code_on_page", ""), ("lat", None), ("lng", None)])
        out.append(_row("INDEPENDENT", "DIRECT_STATIC_FETCH", "", r["u"], r.get("final_url") or r["u"], sig, r.get("h"),
                        r.get("b"), "the property's own pet policy / FAQ page (verbatim sentences)", r["q"],
                        OrderedDict(r["extraction"]), zips, r["binding"], None,
                        extra={"read_for_identity_key": r["identity_key"],
                               "raw_capture": "raw_captures/independent_rows.json"}))
    return out


def _lane_rows(doc, lane, zips):
    out = []
    for r in (doc or {}).get("rows", []):
        if r.get("outcome") != "VALID":
            continue
        ident = (r.get("identity_assessment") or {})
        sig0 = ident.get("signals") or {}
        obs = r.get("observation") or {}
        ext = OrderedDict((obs.get("extraction") or {}))
        # the shared reader writes a weight as {"value", "unit"}; the staging writer takes the flat form. A deposit
        # is not a fee and is not staged; cats_allowed / service-animal wording are not schema facts here.
        w = ext.get("weight_limit")
        if isinstance(w, dict):
            ext["weight_limit"] = w.get("value")
            ext["weight_limit_unit"] = w.get("unit") or "lb"
            if w.get("basis") == "combined" or w.get("scope") == "combined":
                ext["weight_basis"] = "combined"
        for drop in ("pet_deposit", "cats_allowed", "service_animal_exception", "pet_count_scope"):
            ext.pop(drop, None)
        quotes = [e.get("quote") for e in (obs.get("evidence") or []) if e.get("quote")]
        quote = " | ".join(OrderedDict.fromkeys(quotes))
        grade = str(((obs.get("publication_grade") or {}).get("verdict")) or "")
        sig = OrderedDict([("name_on_page", sig0.get("name_on_page")), ("address_on_page", sig0.get("address_on_page")),
                           ("postal_code", (sig0.get("postal_code") or "")[:5]), ("locality", sig0.get("locality") or ""),
                           ("region", "FL"), ("phone_on_page", sig0.get("phone_on_page")),
                           ("property_code_on_page", sig0.get("property_code_on_page")), ("lat", None), ("lng", None)])
        row = _row((r.get("brand") or r.get("family") or "INDEPENDENT"), lane, r.get("property_code") or "",
                   r["requested_url"], r.get("final_url"), sig, r.get("page_sha256"), None,
                   "bounded policy container located by the shared reader", quote, ext, zips,
                   ident.get("binding_method") or "SHARED_IDENTITY_ASSESSMENT", None,
                   extra={"read_for_identity_key": r.get("identity_key"), "publication_grade_verdict": grade,
                          "identity_confirmed_by_adapter": bool(ident.get("confirmed")),
                          "artifact_dir": r.get("artifact_dir"), "cohort": r.get("cohort")})
        row["identity_confirmed"] = bool(ident.get("confirmed")) and row["identity_confirmed"]
        if lane == "FIRECRAWL" and r.get("cohort") == "WALL_REPROBE":
            row["diagnostic_only"] = True
        out.append(row)
    return out


def build():
    zips = zips_of_registry()
    out = []
    out += marriott_rows(zips)
    out += hilton_rows(zips)
    wy, wyn = wyndham_rows(zips)
    out += wy
    out += esa_rows(zips)
    out += ihg_rows(zips)
    out += hyatt_rows(zips)
    out += bestwestern_rows(zips)
    out += resort_rows(zips)
    out += choice_rows(zips)
    out += loews_rows(zips)
    out += independent_rows(zips)
    out += _lane_rows(_load(STATIC, {}), "DIRECT_STATIC_FETCH", zips)
    out += [r for r in _lane_rows(_load(FIRECRAWL, {}), "FIRECRAWL", zips) if not r.get("diagnostic_only")]
    in_market = [r for r in out if r["in_market"]]
    return OrderedDict([
        ("schema", SCHEMA), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "12-16 -- first-party reads from every lane, one shape"),
        ("as_of", CAPTURED_AT),
        ("lanes", ["DIRECT_STATIC_FETCH", "FIRECRAWL", "ATTENDED_BROWSER"]),
        ("paid_provider_calls", 0), ("usd_spent", 0.0),
        ("wyndham_retired_routes", wyn.get("retired_routes_redirected_to_brand_search", [])),
        ("wyndham_error_rows", wyn.get("errors", [])),
        ("no_bot_check_was_answered", "every page served a plain navigation, a plain client request or a Firecrawl render; "
                                      "no page script was run in the browser and nothing was relayed out of it."),
        ("counts", OrderedDict([
            ("pages_read", len(out)),
            ("by_lane", OrderedDict(sorted(Counter(r["lane"] for r in out).items()))),
            ("by_brand", OrderedDict(sorted(Counter(r["brand"] for r in out).items()))),
            ("identity_confirmed", sum(1 for r in out if r["identity_confirmed"])),
            ("in_market", len(in_market)), ("outside_market", len(out) - len(in_market)),
            ("in_market_pets_allowed_true", sum(1 for r in in_market if r["extraction"].get("pets_allowed") is True)),
            ("in_market_pets_allowed_false", sum(1 for r in in_market if r["extraction"].get("pets_allowed") is False)),
            ("in_market_first_party_conflicts", sum(1 for r in in_market if r.get("first_party_conflict"))),
        ])),
        ("rows", out),
    ])


def main(argv=None):
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
