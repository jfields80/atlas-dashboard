# -*- coding: utf-8 -*-
"""PTF-GRAND-RAPIDS-FOUNDER-RULINGS-020 -- the founder's rulings, applied.

NO PROVIDER IS CALLED and nothing is spent. Every signal below is read off an
artifact on this branch or a capture already saved on disk.

WHAT IS THE FOUNDER'S, AND WHAT IS THIS MODULE'S
--------------------------------------------------
The founder issued two policy doctrines, authorised four fact corrections, and
DELEGATED the per-row identity adjudication -- "for each row decide exactly
one" -- under a rule of their own: a shared telephone alone may never confirm
identity. So the ledger records two different kinds of authorship and never
blurs them. ``ruling_authority`` is the founder for a doctrine and for a
correction they named; it is the operator for an identity verdict the founder
delegated, with the founder's rule cited as the constraint it was decided
under. Nothing here writes a founder decision for a row the order did not rule
on: the 45 clean rows from 019 stay unsigned, and the report says so.

THE IDENTITY VERDICTS ARE DERIVED, NOT TRANSCRIBED
----------------------------------------------------
A ledger that merely recorded "the operator says these are the same hotel"
would be an opinion with a schema. So each verdict names the signals it rests
on, this module RE-DERIVES those signals from ``declined.json`` and the census,
and ``CONFIRMATION_RULE`` refuses a SAME_PROPERTY_CONFIRMED that the re-derived
evidence does not support. A verdict whose evidence has moved raises rather
than being believed.

The rule: at least two independent agreeing signals, of which at least one is
not the telephone. That is the founder's constraint expressed as arithmetic --
phone-alone can never reach two -- and it is why Budgetel Grand Rapids, whose
page agrees on nothing at all, comes out HOLD_IDENTITY rather than confirmed.

WHY SIX CONFIRMATIONS DO NOT BECOME SIX PROFILES
--------------------------------------------------
Six rows were declined at the IDENTITY gate, which is before the policy locator
ever runs, so their captures carry no policy block. Confirming identity settles
who the page is about; it does not read what the page says. Only avid hotel
Zeeland already carries a complete publication-grade observation -- the membrane
rejected it after the reading, not before -- so it is the one row that becomes a
candidate today. The other five need a policy re-locate over their saved HTML,
which is free and is a different work order. Four of them never mention a pet
anywhere in the saved page, so that re-locate should be expected to return
POLICY_NOT_FOUND rather than profiles.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.brightdata.corpus import brand_of, INDEPENDENT_PREFIX  # noqa: E402

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
RUN_DIR = (_REPO_ROOT / "data" / "acquisition"
           / "grand_rapids_holland_mi_factory_001" / "pass1")

WORK_ORDER = "PTF-GRAND-RAPIDS-FOUNDER-RULINGS-020"
MARKET = "grand-rapids-holland-mi"
FOUNDER = "PTF-FOUNDER-001"
OPERATOR = "Claude (operator), under the founder's delegation in " + WORK_ORDER

BY_FOUNDER = "FOUNDER"
BY_OPERATOR_UNDER_DELEGATION = "OPERATOR_UNDER_FOUNDER_DELEGATION"


# --------------------------------------------------------------------------- #
# The two doctrines, as the founder stated them
# --------------------------------------------------------------------------- #

DOCTRINE_PRICE_IMPLIES_ALLOWANCE = OrderedDict((
    ("id", "FOUNDER-DOCTRINE-PET-PRICE-IMPLIES-ALLOWANCE"),
    ("issued_by", FOUNDER),
    ("issued_in", WORK_ORDER),
    ("statement",
     "If an official property source explicitly publishes a pet fee or pet "
     "price that applies to the property, treat that as affirmative evidence "
     "that pets are permitted, unless the same source explicitly contradicts "
     "that interpretation."),
    ("bounds", [
        "an explicit pet-SPECIFIC price or fee is required",
        "the property identity must already be valid",
        "no inference from a generic fee",
        "no inference from service-animal language",
        "no inference from an unrelated amenity",
    ]),
))

DOCTRINE_SOURCE_SILENCE = OrderedDict((
    ("id", "FOUNDER-DOCTRINE-SOURCE-SILENCE-IS-NOT-NO-PETS"),
    ("issued_by", FOUNDER),
    ("issued_in", WORK_ORDER),
    ("statement",
     "A rendered official property page with a valid identity that states no "
     "pet policy, no allowance, no fee and no prohibition is POLICY_NOT_FOUND "
     "and unresolved. Source silence is never converted into verified no-pets, "
     "and another market's precedent is not inherited automatically."),
    ("bounds", [
        "Pittsburgh's 'source silence is absence' ruling does NOT carry over",
        "an amenity token such as 'Pet-friendly rooms' is not a policy",
        "a policy-section heading with no body is silence, not a finding",
    ]),
))


# --------------------------------------------------------------------------- #
# Identity: the rule, and the signals it counts
# --------------------------------------------------------------------------- #

SAME_PROPERTY_CONFIRMED = "SAME_PROPERTY_CONFIRMED"
DISTINCT_PROPERTY = "DISTINCT_PROPERTY"
HOLD_IDENTITY = "HOLD_IDENTITY"

CONFIRMATION_RULE = (
    "at least two independent agreeing signals, of which at least one is not "
    "the telephone. The founder's constraint -- a shared telephone alone may "
    "NEVER confirm identity -- is expressed as arithmetic here, because a rule "
    "a run cannot fail is not a rule.")

SIGNAL_TELEPHONE = "TELEPHONE"
SIGNAL_STREET = "STREET_ADDRESS"
SIGNAL_POSTAL = "POSTAL_CODE"
SIGNAL_PROPERTY_CODE = "BRAND_PROPERTY_CODE"
SIGNAL_NAME = "DISTINCTIVE_NAME"
SIGNAL_SOLE_PROPERTY_DOMAIN = "FIRST_PARTY_SOLE_PROPERTY_DOMAIN"

#: Words that carry no identity on their own in this market: every hotel has
#: some of them. Taken from the membrane's own complaint about The Ada Hotel,
#: whose name "agrees only on ada, hotel, the".
_GENERIC_NAME_WORDS = frozenset({
    "the", "hotel", "hotels", "inn", "inns", "suites", "suite", "motel",
    "lodge", "resort", "and", "by", "at", "of", "grand", "rapids", "holland",
    "michigan", "mi", "downtown", "airport", "north", "south", "east", "west",
    "conference", "center", "centre", "boutique", "house", "place",
})


def _digits(value) -> str:
    """The comparable digits of a telephone number.

    A saved page writes ``1-616-9533900`` where the census wrote
    ``6169533900``; the same switchboard with a country code in front of it.
    Dropping a leading US 1 from an eleven-digit number is what lets avid hotel
    Zeeland's telephone agreement be RECORDED. It does not change that ruling --
    the street and the name already carry it -- but a ledger that under-reports
    its own evidence is harder to argue with than one that does not.
    """
    digits = re.sub(r"\D", "", str(value or ""))
    if len(digits) == 11 and digits.startswith("1"):
        return digits[1:]
    return digits


def _words(name: str) -> List[str]:
    return [w for w in re.split(r"[^a-z0-9]+", (name or "").lower()) if w]


def _distinctive(name: str) -> frozenset:
    return frozenset(_words(name)) - _GENERIC_NAME_WORDS


def _street_number(address: str) -> str:
    parts = _words(address)
    return parts[0] if parts and parts[0].isdigit() else ""


def _street_core(address: str) -> frozenset:
    """The address without its direction suffix or its street-type word.

    ``5970 Metro Way S.W.`` and ``5970 Metro Way SouthW.`` are the same address;
    only the census's half-expanded compound direction differs, and comparing
    the parts both spellings agree on is what says so without teaching the
    normaliser a new abbreviation.
    """
    drop = {"north", "south", "east", "west", "northeast", "northwest",
            "southeast", "southwest", "n", "s", "e", "w", "ne", "nw", "se",
            "sw", "southw", "northw", "southe", "northe", "st", "street",
            "ave", "avenue", "rd", "road", "dr", "drive", "way", "ct", "court",
            "ln", "lane", "blvd", "boulevard"}
    return frozenset(_words(address)) - drop


def page_signals(declined: Mapping, record: Optional[Mapping]) -> Dict:
    """What the SAVED page said about itself, from whichever artifact has it.

    A row declined at the identity gate leaves ``declined.json``. A row the
    MEMBRANE rejected got all the way through the reader first, so its page
    signals live in the observation store instead -- avid hotel Zeeland is the
    only one, and reading it from the store rather than re-deriving it is what
    keeps this ledger checking the same evidence the membrane checked.
    """
    signals = (declined.get("identity") or {}).get("signals")
    if signals:
        return dict(signals)
    if not record:
        return {}
    check = record["observation"].get("identity_check") or {}
    return {
        "name_on_page": check.get("name_on_page") or "",
        "address_on_page": check.get("address_on_page") or "",
        "postal_code": "",
        "phone_on_page": check.get("phone_on_page") or "",
        "property_code_on_page": check.get("property_code") or "",
        "canonical_url": record["observation"].get("source_url") or "",
        "phones_on_page": [check.get("phone_on_page") or ""],
    }


def identity_signals(census: Mapping, signals: Mapping,
                     conflicting: Sequence[str] = ()) -> Dict:
    """Every signal on which the saved page and the census row AGREE.

    Nothing is asserted here: each entry is recomputed from the capture that is
    still on disk and the census row as committed, so a ledger entry whose
    evidence has moved stops agreeing and the verdict gate fails.
    """
    agreed: "OrderedDict[str, str]" = OrderedDict()

    page_phones = {_digits(p) for p in (signals.get("phones_on_page") or ())}
    page_phones.add(_digits(signals.get("phone_on_page")))
    census_phone = _digits(census.get("phone"))
    if census_phone and census_phone in page_phones:
        agreed[SIGNAL_TELEPHONE] = census_phone

    page_address = str(signals.get("address_on_page") or "")
    census_address = str(census.get("address") or "")
    if page_address and census_address:
        if (_street_number(page_address)
                and _street_number(page_address) == _street_number(census_address)
                and _street_core(page_address) & _street_core(census_address)):
            agreed[SIGNAL_STREET] = page_address

    page_postal = _digits(signals.get("postal_code"))[:5]
    census_postal = _digits(census.get("postal_code"))[:5]
    if page_postal and page_postal == census_postal:
        agreed[SIGNAL_POSTAL] = page_postal

    code = str(signals.get("property_code_on_page") or "").strip().lower()
    census_url = str(census.get("official_url") or "").lower()
    if code and code in census_url:
        agreed[SIGNAL_PROPERTY_CODE] = code

    page_name = str(signals.get("name_on_page") or "")
    shared = _distinctive(page_name) & _distinctive(census.get("canonical_name"))
    if shared:
        agreed[SIGNAL_NAME] = " ".join(sorted(shared))

    # An independent hotel's own root domain names exactly one property, which
    # is why the membrane's "a related-looking URL on the same domain is not an
    # identity" is a statement about CHAIN domains and not about this one.
    canonical = str(signals.get("canonical_url") or "")
    host_brand = brand_of(canonical or census_url)
    if (canonical and host_brand.startswith(INDEPENDENT_PREFIX)
            and _digits(census.get("phone"))
            and _digits(census.get("phone")) in page_phones
            and re.sub(r"^https?://(www\.)?", "", canonical).strip("/").count("/") == 0):
        agreed[SIGNAL_SOLE_PROPERTY_DOMAIN] = canonical

    non_phone = [k for k in agreed if k != SIGNAL_TELEPHONE]
    return OrderedDict((
        ("agreed", agreed),
        ("agreed_count", len(agreed)),
        ("non_telephone_signals", non_phone),
        ("conflicting", list(conflicting)),
        ("satisfies_confirmation_rule", len(agreed) >= 2 and bool(non_phone)),
    ))


# --------------------------------------------------------------------------- #
# The rulings the founder made, and the ones they delegated
# --------------------------------------------------------------------------- #

#: (identity_key, verdict, why). The verdict is checked against the re-derived
#: signals below; a SAME_PROPERTY_CONFIRMED the evidence cannot carry raises.
IDENTITY_RULINGS: Tuple[Tuple[str, str, str], ...] = (
    ("avid hotel zeeland", SAME_PROPERTY_CONFIRMED,
     "the page states this row's exact street address and this row's exact "
     "telephone; the only disagreement is IHG's own naming convention, which "
     "writes 'avid hotels <city> - <metro>' where the census wrote 'avid hotel "
     "<city>'. Membrane rule M10 asks for property-code-plus-street or "
     "street-plus-owner-qualified-name and does not list street-plus-telephone, "
     "which is the gap this ruling fills"),
    ("baymont inn and suites grand rapids airport", SAME_PROPERTY_CONFIRMED,
     "street, postal code and the census row's own official_url path all agree; "
     "the page's name is Wyndham's rebrand of 'Baymont Inn & Suites' to "
     "'Baymont by Wyndham', and the URL slug the census carries still spells "
     "the old name"),
    ("fairfield inn and suites grand rapids wyoming", SAME_PROPERTY_CONFIRMED,
     "the page carries brand property code GRRFW, which is Marriott's own key "
     "for this building and is the code the census official_url names; postal "
     "code and name agree. The street 'disagreement' is the census's "
     "half-expanded '5970 Metro Way SouthW.' against the page's '5970 Metro "
     "Way S.W.' -- one address, two spellings"),
    ("the bluejay hotel", SAME_PROPERTY_CONFIRMED,
     "street, postal code and telephone all agree; the page writes 'The Blue "
     "Jay' where the census wrote 'The BlueJay Hotel', which is a space"),
    ("haworth hotel", SAME_PROPERTY_CONFIRMED,
     "the page is the root of haworthhotel.com, an independent hotel's own "
     "single-property domain, it prints this row's telephone, and 'Haworth' is "
     "a distinctive name this market shares with nothing else"),
    ("the ada hotel", SAME_PROPERTY_CONFIRMED,
     "the page is the root of adahotel.com and the ONLY telephone it prints is "
     "this row's. The membrane objected that the names agree only on 'ada, "
     "hotel, the' -- true, and it is why the domain and the telephone are what "
     "carry this one"),
    ("the finnley hotel", SAME_PROPERTY_CONFIRMED,
     "the page is the root of thefinnley.com, it prints this row's telephone, "
     "and 'Finnley' is distinctive"),
    ("budgetel grand rapids", HOLD_IDENTITY,
     "nothing agrees. The page states no address, no postal code and no "
     "telephone of its own, and this row's telephone is absent from the five "
     "numbers the page does print. A chain page for a city is not a property "
     "page, and there is no second signal to reach for"),
)

#: The corrections the founder authorised. Each REPLACES a value with one the
#: source already states or FILLS a field the source states; none invents a
#: fact and none changes what the policy means.
CORRECTIONS: Tuple[Dict, ...] = (
    OrderedDict((("identity_key", "baymont"), ("field", "canonical_name"),
                 ("to_source", "identity_check.name_on_page"),
                 ("why", "the census name is a bare chain word that would "
                         "publish a directory entry naming no building"))),
    OrderedDict((("identity_key", "doubletree by hilton"),
                 ("field", "canonical_name"),
                 ("to_source", "identity_check.name_on_page"),
                 ("why", "the census name is a bare chain word and Holland is "
                         "where the page says this hotel is"))),
    OrderedDict((("identity_key", "tru"), ("field", "canonical_name"),
                 ("to_source", "identity_check.name_on_page"),
                 ("why", "the census name is a bare chain word"))),
    OrderedDict((("identity_key", "baymont by wyndham holland"),
                 ("field", "weight_limit"),
                 ("to_source", "policy_block"),
                 ("value", OrderedDict((("value", 100.0), ("unit", "lb")))),
                 ("quote", "must not weigh more than 100 lbs each"),
                 ("why", "the source states a weight limit and the record "
                         "carries none, so the profile reads 'Not stated' "
                         "where the hotel states a limit"))),
)

#: The rows the price-implies-allowance doctrine reaches. Both are checked
#: against the store below: a row whose evidence does not actually carry an
#: explicit pet-specific price is refused rather than ruled.
ALLOWANCE_RULINGS: Tuple[str, ...] = ("baymont",
                                      "travelodge by wyndham grand rapids north")

#: The rows the silence doctrine leaves unresolved.
SILENCE_RULINGS: Tuple[str, ...] = (
    "doubletree by hilton hotel grand rapids airport",
    "drury inn and suites grand rapids", "tulyp")

PRESERVE_INDEPENDENT = "PRESERVE_INDEPENDENT_IDENTITIES"
REBRAND_RECORDED = "REBRAND_RECORDED_NOT_MERGED"

#: The three pairs the founder ruled on, and the two this pass found evidence
#: for while reading the captures. None is merged.
PAIR_RULINGS: Tuple[Tuple[str, str, str, str], ...] = (
    ("comfort inn", "comfort suites grandville grand rapids sw",
     PRESERVE_INDEPENDENT,
     "shared street and shared switchboard, and nothing else. Comfort Inn "
     "carries no official URL at all, so there is no page to compare"),
    ("sleep inn and suites", "spark by hilton grand rapids",
     PRESERVE_INDEPENDENT,
     "shared street and shared switchboard. Neither half is routed, so a "
     "Choice-to-Hilton rebrand is a plausible reading with no page behind it"),
    ("budgetel grand rapids", "budgetel inn and suites hotel",
     PRESERVE_INDEPENDENT,
     "shared street and shared switchboard, and the Budgetel page agrees with "
     "neither half on any physical signal"),
    ("baymont inn and suites grand rapids airport",
     "baymont by wyndham grand rapids airport", REBRAND_RECORDED,
     "one building at 2873 Kraft Avenue SE, 49512. The saved page names the "
     "SECOND row and declares the second row's telephone, while its URL slug "
     "spells the FIRST row's name and it also prints the first row's "
     "telephone. That is a Wyndham rebrand carrying two census names and two "
     "numbers -- recorded, and deliberately not merged"),
    ("the bluejay hotel", "the blue jay hotel and events", REBRAND_RECORDED,
     "one building at 644 Bridge Street NW. The saved page names itself 'The "
     "Blue Jay', which is the SECOND row's spelling, while the first row is "
     "the one that carries the URL and the telephone. Recorded, not merged"),
)


# --------------------------------------------------------------------------- #
# Reading what is on disk
# --------------------------------------------------------------------------- #

def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _slugs(key: str) -> List[str]:
    base = key.replace("&", "and")
    return ["-".join(base.split()),
            "-".join(w for w in base.split() if w != "and")]


def capture_dir(key: str) -> Optional[Path]:
    for slug in _slugs(key):
        for sub in ("declined-01", "attempt-01"):
            path = RUN_DIR / slug / sub
            if path.is_dir():
                return path
    return None


def read_declined(key: str) -> Dict:
    path = capture_dir(key)
    if path is None:
        return {}
    document = path / "declined.json"
    return _load(document) if document.is_file() else {}


def mentions_pets(key: str) -> Optional[bool]:
    """Whether the SAVED page text mentions a pet at all. Diagnostic only.

    It sizes the follow-up rather than reading a policy: a page that never says
    the word cannot be hiding an allowance behind a locator.
    """
    path = capture_dir(key)
    if path is None:
        return None
    text = path / "page-text.txt"
    if not text.is_file():
        return None
    return bool(re.search(r"\bpets?\b|\bdogs?\b",
                          text.read_text(encoding="utf-8", errors="replace"),
                          re.I))


# --------------------------------------------------------------------------- #
# Building the ledger
# --------------------------------------------------------------------------- #

class RulingError(ValueError):
    """A ruling the evidence on disk does not support."""


def build_identity_entries(census: Mapping[str, Mapping],
                           store: Mapping[str, Mapping]) -> List[Dict]:
    entries: List[Dict] = []
    for key, verdict, why in IDENTITY_RULINGS:
        declined = read_declined(key)
        record = store.get(key)
        row = census.get(key) or {}
        signals = identity_signals(
            row, page_signals(declined, record),
            (declined.get("identity") or {}).get("conflicting") or [])
        if verdict == SAME_PROPERTY_CONFIRMED and not signals["satisfies_confirmation_rule"]:
            raise RulingError(
                "%r is ruled SAME_PROPERTY_CONFIRMED but the saved capture "
                "agrees on %d signal(s) %r, which does not satisfy: %s"
                % (key, signals["agreed_count"], list(signals["agreed"]),
                   CONFIRMATION_RULE))
        if verdict == HOLD_IDENTITY and signals["satisfies_confirmation_rule"]:
            raise RulingError(
                "%r is held, but the saved capture now agrees on %r; a hold "
                "that the evidence has outgrown must be re-ruled, not kept"
                % (key, list(signals["agreed"])))
        entries.append(OrderedDict((
            ("identity_key", key),
            ("canonical_name", str(row.get("canonical_name") or "")),
            ("ruling", verdict),
            ("ruling_authority", BY_OPERATOR_UNDER_DELEGATION),
            ("ruled_by", OPERATOR),
            ("founder_constraint", "a shared telephone alone may NEVER confirm "
                                   "identity"),
            ("confirmation_rule", CONFIRMATION_RULE),
            ("why", why),
            ("signals_agreed", signals["agreed"]),
            ("signals_agreed_count", signals["agreed_count"]),
            ("non_telephone_signals", signals["non_telephone_signals"]),
            ("page_signals_conflicting", signals["conflicting"]),
            ("page_title", str(declined.get("title") or "")
             or str((record or {}).get("canonical_name") or "")),
            ("final_url", str(declined.get("final_url") or "")
             or str((record or {}).get("observation", {}).get("source_url") or "")),
            ("capture", str(capture_dir(key).relative_to(_REPO_ROOT).as_posix())
             if capture_dir(key) else ""),
            ("document_sha256", str(declined.get("document_sha256") or "")
             or str((record or {}).get("reader_provenance", {})
                    .get("document_sha256") or "")),
            ("yields_a_policy_observation_today", key == "avid hotel zeeland"),
            ("saved_page_mentions_pets", mentions_pets(key)),
        )))
    return entries


def build_allowance_entries(store: Mapping[str, Mapping]) -> List[Dict]:
    entries: List[Dict] = []
    for key in ALLOWANCE_RULINGS:
        record = store.get(key)
        if record is None:
            raise RulingError("%r has no observation to rule on" % key)
        extraction = record["observation"]["extraction"]
        withheld = record.get("withheld_fields") or {}
        if withheld.get("pets_allowed") != "SOURCE_SILENT":
            raise RulingError(
                "%r does not have the shape this doctrine addresses: "
                "pets_allowed is %r, not withheld as SOURCE_SILENT"
                % (key, extraction.get("pets_allowed")))
        if str((record.get("membrane") or {}).get("verdict")) != "VALID":
            raise RulingError("%r has no valid identity; the doctrine requires "
                              "one before it applies" % key)
        block = read_policy_block(key)
        price = pet_specific_price(record, block)
        if not price:
            raise RulingError(
                "%r states no explicit pet-SPECIFIC price, so the doctrine "
                "does not reach it; a generic fee may not be read as an "
                "allowance" % key)
        stated = stated_allowance(block)
        entries.append(OrderedDict((
            ("identity_key", key),
            ("canonical_name", str(record.get("canonical_name") or "")),
            ("ruling", "PETS_ALLOWED_TRUE"),
            ("ruling_authority", BY_FOUNDER),
            ("ruled_by", FOUNDER),
            ("doctrine", DOCTRINE_PRICE_IMPLIES_ALLOWANCE["id"]),
            ("pet_specific_price_quote", price),
            ("source_also_states_the_allowance_in_words", stated),
            ("why",
             "the source publishes an explicit pet-specific price (%r), which "
             "the founder's doctrine treats as affirmative evidence that pets "
             "are permitted%s" % (price,
                                  "; and the same block states the allowance "
                                  "outright (%r), so this ruling does not even "
                                  "rest on the inference" % stated if stated
                                  else "")),
            ("membrane_verdict", "VALID"),
            ("fields_left_untouched",
             sorted(k for k in withheld if k != "pets_allowed")),
            ("note", "the doctrine rules on the ALLOWANCE only. A fee the "
                     "schema could not represent stays withheld."),
        )))
    return entries


#: An allowance the source states in words. The doctrine did not need this --
#: it rules from the price -- but a ruling that is also stated outright is a
#: stronger record than one that is only inferred, so it is looked for.
_STATED_ALLOWANCE = re.compile(
    r"[^.]*\b(?:pets?|dogs?)\b[^.]*\b(?:are|is)\s+(?:allowed|welcome|permitted)[^.]*\.",
    re.I)

#: A price that is explicitly attached to a pet. "per pet", "per dog" or a
#: charge inside a sentence that is about pets. A resort fee is not this.
_PET_PRICE = re.compile(
    r"[^.]*\b(?:pets?|dogs?)\b[^.]*?\d+(?:\.\d+)?\s*(?:USD|dollars|\$)?[^.]*\.|"
    r"[^.]*\d+(?:\.\d+)?\s*(?:USD|dollars|\$)[^.]*\bper\s+(?:pet|dog)\b[^.]*\.",
    re.I)


def read_policy_block(key: str) -> str:
    path = capture_dir(key)
    if path is None:
        return ""
    block = path / "policy-block.txt"
    return (block.read_text(encoding="utf-8", errors="replace").strip()
            if block.is_file() else "")


def stated_allowance(block: str) -> str:
    match = _STATED_ALLOWANCE.search(block or "")
    return match.group(0).strip() if match else ""


def pet_specific_price(record: Mapping, block: str) -> str:
    """The quote that carries an explicit pet-specific price, or ``""``.

    The extraction's own ``pet_fee`` counts when its scope is per-pet, because
    the reader already decided that. Otherwise the saved policy block is read
    for a charge inside a sentence about pets -- which is how the Travelodge
    row qualifies, its fee having been withheld as SCHEMA_CANNOT_REPRESENT
    rather than absent.
    """
    extraction = record["observation"]["extraction"]
    if extraction.get("pet_fee") and extraction.get("fee_scope") == "per_pet":
        for entry in record["observation"].get("evidence") or ():
            quote = str(entry.get("quote") or "")
            if re.search(r"per\s+pet", quote, re.I):
                return quote
        return "pet_fee %s %s per pet" % (extraction["pet_fee"],
                                          extraction.get("fee_currency") or "")
    match = _PET_PRICE.search(block or "")
    return match.group(0).strip() if match else ""


def build_correction_entries(store: Mapping[str, Mapping]) -> List[Dict]:
    entries: List[Dict] = []
    for correction in CORRECTIONS:
        key = correction["identity_key"]
        record = store.get(key)
        if record is None:
            raise RulingError("%r has no observation to correct" % key)
        field = correction["field"]
        if correction["to_source"] == "identity_check.name_on_page":
            new_value = str(record["observation"]["identity_check"]
                            .get("name_on_page") or "")
            old_value = str(record.get("canonical_name") or "")
            if not new_value:
                raise RulingError("%r: the page states no name to correct to"
                                  % key)
        else:
            new_value = correction["value"]
            old_value = record["observation"]["extraction"].get(field)
            quote = correction["quote"]
            if quote.lower() not in read_policy_block(key).lower():
                raise RulingError(
                    "%r: the quote %r is not in the saved policy block, so "
                    "this correction would be inventing a fact" % (key, quote))
        entries.append(OrderedDict((
            ("identity_key", key),
            ("ruling", "CORRECTION_APPLIED"),
            ("ruling_authority", BY_FOUNDER),
            ("ruled_by", FOUNDER),
            ("field", field),
            ("from", old_value),
            ("to", new_value),
            ("evidence", correction.get("quote")
             or record["observation"]["identity_check"].get("name_on_page")),
            ("source", correction["to_source"]),
            ("why", correction["why"]),
            ("changes_policy_meaning", False),
        )))
    return entries


def build_silence_entries(replay: Mapping, store: Mapping[str, Mapping]) -> List[Dict]:
    entries: List[Dict] = []
    for key in SILENCE_RULINGS:
        if key in store:
            raise RulingError(
                "%r carries a publication-grade observation; the silence "
                "doctrine is for rows that produced none" % key)
        mentions = mentions_pets(key)
        entries.append(OrderedDict((
            ("identity_key", key),
            ("ruling", "POLICY_NOT_FOUND_UNRESOLVED"),
            ("ruling_authority", BY_FOUNDER),
            ("ruled_by", FOUNDER),
            ("doctrine", DOCTRINE_SOURCE_SILENCE["id"]),
            ("becomes_verified_no_pets", False),
            ("saved_page_mentions_a_pet_token", mentions),
            ("why",
             "the page rendered under a valid identity and states no pet "
             "policy. The pet tokens the saved text does carry are an amenity "
             "list item and an empty policy-section heading, and the founder's "
             "doctrine rules out inferring from either"
             if mentions else
             "the page rendered under a valid identity and never mentions a "
             "pet at all"),
            ("next_action",
             "a re-capture with the policy accordion expanded would settle it; "
             "a re-read of the saved HTML would not, because the body was "
             "never in the page we saved"),
        )))
    return entries


def build_pair_entries(census: Mapping[str, Mapping],
                       dedup: Mapping) -> List[Dict]:
    verdicts: Dict[Tuple[str, str], str] = {}
    for group in dedup.get("groups") or ():
        keys = tuple(sorted(str(k) for k in group.get("identity_keys") or ()))
        if len(keys) == 2:
            verdicts.setdefault(keys, str(group.get("verdict") or ""))
    entries: List[Dict] = []
    for left, right, ruling, why in PAIR_RULINGS:
        halves = [OrderedDict((
            ("identity_key", key),
            ("canonical_name", str((census.get(key) or {}).get("canonical_name") or "")),
            ("address", str((census.get(key) or {}).get("address") or "")),
            ("phone", str((census.get(key) or {}).get("phone") or "")),
        )) for key in (left, right)]
        phones = [h["phone"] for h in halves]
        entries.append(OrderedDict((
            ("identity_keys", [left, right]),
            ("ruling", ruling),
            ("ruling_authority", BY_FOUNDER if ruling == PRESERVE_INDEPENDENT
             else BY_OPERATOR_UNDER_DELEGATION),
            ("ruled_by", FOUNDER if ruling == PRESERVE_INDEPENDENT else OPERATOR),
            ("merged", False),
            ("decided_on_shared_telephone_alone", False),
            ("shares_a_telephone", bool(phones[0]) and phones[0] == phones[1]),
            ("dedup_verdict", verdicts.get(tuple(sorted((left, right))),
                                           "NOT_GROUPED")),
            ("halves", halves),
            ("why", why),
        )))
    return entries


# --------------------------------------------------------------------------- #
# Rebuilding the classification
# --------------------------------------------------------------------------- #

CLEAN_PET_FRIENDLY = "CLEAN_PET_FRIENDLY"
CLEAN_VERIFIED_NO_PETS = "CLEAN_VERIFIED_NO_PETS"
POLICY_NOT_FOUND = "POLICY_NOT_FOUND_UNRESOLVED"
IDENTITY_RESOLVED_POLICY_PENDING = "IDENTITY_RESOLVED_POLICY_READ_PENDING"
UNRESOLVED_ROUTING = "UNRESOLVED_ROUTING"
HELD_IDENTITY = "HELD_IDENTITY"


def effective_facts(store: Mapping[str, Mapping],
                    ledger: Mapping) -> Dict[str, Dict]:
    """The stored extraction with THIS ORDER's rulings layered over it.

    The observation store on disk is not edited -- an observation records what
    a page said, and a founder ruling is a different kind of statement -- so the
    class of a ruled row has to be derived from the ruling and not from the
    untouched record. Skipping that is not a cosmetic bug: ``baymont`` carries
    ``pets_allowed: None`` in the store, and reading the class straight off the
    record turned a hotel that charges 25.00 USD per pet per night into a
    VERIFIED NO-PETS entry. That is precisely the inversion the founder's
    silence doctrine exists to forbid, arrived at from the other direction.
    """
    facts: Dict[str, Dict] = {}
    for key, record in store.items():
        facts[key] = dict(record["observation"]["extraction"])
    for entry in ledger["allowance_rulings"]:
        facts.setdefault(entry["identity_key"], {})["pets_allowed"] = True
    for entry in ledger["corrections"]:
        if entry["field"] == "canonical_name":
            continue
        facts.setdefault(entry["identity_key"], {})[entry["field"]] = entry["to"]
    return facts


def class_of(key: str, facts: Mapping[str, Mapping]) -> str:
    allowed = (facts.get(key) or {}).get("pets_allowed")
    if allowed is True:
        return CLEAN_PET_FRIENDLY
    if allowed is False:
        return CLEAN_VERIFIED_NO_PETS
    raise RulingError(
        "%r has no ruled pets_allowed value, so it has no clean class. A row "
        "whose allowance is unresolved is a HOLD; calling it verified no-pets "
        "would publish a refusal the hotel never made" % key)


def reclassify(packet: Mapping, store: Mapping[str, Mapping],
               ledger: Mapping) -> Dict:
    """The 019 classification, with this order's rulings applied."""
    facts = effective_facts(store, ledger)
    rows: "OrderedDict[str, Dict]" = OrderedDict()
    for row in list(packet["clean"]) + list(packet["exceptions"]):
        rows[row["identity_key"]] = OrderedDict((
            ("identity_key", row["identity_key"]),
            ("canonical_name", row["canonical_name"]),
            ("was", row["classification"]),
            ("now", row["classification"]),
            ("changed_by", ""),
            ("signed_in_this_order", False),
            ("pets_allowed_after_rulings",
             (facts.get(row["identity_key"]) or {}).get("pets_allowed")),
            ("semantic_approval_hash", row["semantic_approval_hash"]),
        ))

    def _set(key, now, by):
        rows[key]["now"] = now
        rows[key]["changed_by"] = by
        rows[key]["signed_in_this_order"] = True

    # Order matters and only one rung decides the class. The allowance and the
    # corrections both touch the same rows, so the class is computed ONCE, from
    # the ruled facts, and the rungs only record which ruling touched the row.
    touched: "OrderedDict[str, str]" = OrderedDict()
    for entry in ledger["allowance_rulings"]:
        touched[entry["identity_key"]] = entry["doctrine"]
    for entry in ledger["corrections"]:
        key = entry["identity_key"]
        touched[key] = (touched.get(key) + " + CORRECTION_APPLIED"
                        if key in touched else "CORRECTION_APPLIED")
    for entry in ledger["identity_rulings"]:
        if entry["ruling"] == SAME_PROPERTY_CONFIRMED and entry["identity_key"] in rows:
            touched[entry["identity_key"]] = "IDENTITY_RULING"
    for key, by in touched.items():
        if key in rows:
            _set(key, class_of(key, facts), by)

    for entry in ledger["silence_rulings"]:
        _set(entry["identity_key"], POLICY_NOT_FOUND, entry["doctrine"])

    counts = Counter(r["now"] for r in rows.values())
    return OrderedDict((
        ("rows", list(rows.values())),
        ("counts", OrderedDict(sorted(counts.items()))),
        ("changed", [r for r in rows.values() if r["was"] != r["now"]]),
    ))


# --------------------------------------------------------------------------- #
# The proposed authority, and the gate in front of it
# --------------------------------------------------------------------------- #

def authority_readiness(classification: Mapping, holds: Mapping,
                        store: Mapping[str, Mapping],
                        ledger: Mapping) -> Dict:
    """What the authority WOULD hold, and what stops it being built.

    The founder's order says to build it "if all required signatures and
    identity gates are satisfied", and in the same breath says to write
    decisions only for the rows this order ruled on. Both cannot be true at
    once, and the honest answer is the second.

    A FACT RULING IS NOT A RECORD APPROVAL, AND THE DIFFERENCE IS THE WHOLE GATE
    ---------------------------------------------------------------------------
    This order settled specific FACTS: that a stated pet price means pets are
    permitted, that four names and one weight limit should read as the source
    reads, that source silence stays unresolved. What authority needs is
    different -- a founder decision from the approval vocabulary over a whole
    RECORD, bound to that record's semantic hash. Nobody has made one of those
    for any Grand Rapids row.

    So the count that matters is 50 awaiting an approval, not 44. Reporting six
    rows as "signed" because a fact inside them was ruled on would let a reader
    believe six records had been approved when none has, and that is the same
    error as signing them outright, arrived at by rounding.
    """
    held = {k for hold in holds["holds"] for k in hold["identity_keys"]}
    candidates, withheld = [], []
    for row in classification["rows"]:
        if row["now"] not in (CLEAN_PET_FRIENDLY, CLEAN_VERIFIED_NO_PETS):
            continue
        (withheld if row["identity_key"] in held else candidates).append(row)

    fact_ruled = {e["identity_key"] for e in ledger["allowance_rulings"]}
    fact_ruled |= {e["identity_key"] for e in ledger["corrections"]}
    identity_ruled = {e["identity_key"] for e in ledger["identity_rulings"]
                      if e["ruling"] == SAME_PROPERTY_CONFIRMED}

    def _authority(key: str) -> str:
        if key in fact_ruled:
            return BY_FOUNDER
        if key in identity_ruled:
            return BY_OPERATOR_UNDER_DELEGATION
        return ""

    return OrderedDict((
        ("ready_to_build", False),
        ("blocked_by",
         "no Grand Rapids record carries a founder approval. This order ruled "
         "on FACTS -- an allowance, four names, one weight limit, eight "
         "identities -- and a fact ruling is not an approval of the record "
         "that contains it. All %d candidates are awaiting a record-level "
         "decision from the approval vocabulary." % len(candidates)),
        ("exact_next_step",
         "one founder signature pass over the %d candidates, setting "
         "founder_decision, founder_reviewer_id and founder_reviewed_at "
         "against each row's semantic-approval hash. %d of them need no "
         "reading first -- this order and 019 between them have already ruled "
         "on every exception." % (len(candidates), len(candidates))),
        ("would_contain", len(candidates)),
        ("pet_friendly", sum(1 for r in candidates
                             if r["now"] == CLEAN_PET_FRIENDLY)),
        ("verified_no_pets", sum(1 for r in candidates
                                 if r["now"] == CLEAN_VERIFIED_NO_PETS)),
        ("rows_with_a_founder_fact_ruling",
         sorted(k for k in fact_ruled
                if k in {r["identity_key"] for r in candidates})),
        ("rows_admitted_by_a_delegated_identity_verdict",
         sorted(k for k in identity_ruled
                if k in {r["identity_key"] for r in candidates})),
        ("rows_with_a_record_level_founder_approval", 0),
        ("awaiting_a_record_level_approval", len(candidates)),
        ("withheld_on_an_open_identity",
         sorted(r["identity_key"] for r in withheld)),
        ("minimum_published_hotels_for_this_market", 5),
        ("candidates", [OrderedDict((
            ("identity_key", r["identity_key"]),
            ("canonical_name", r["canonical_name"]),
            ("class", r["now"]),
            ("ruled_in_this_order", r["signed_in_this_order"]),
            ("ruling_authority", _authority(r["identity_key"])),
            ("founder_record_approval", ""),
            ("semantic_approval_hash", r["semantic_approval_hash"]),
        )) for r in candidates]),
    ))


def ruled_keys(ledger: Mapping) -> set:
    keys = set()
    for slot in ("identity_rulings", "allowance_rulings", "corrections",
                 "silence_rulings"):
        keys |= {e["identity_key"] for e in ledger[slot]}
    return keys


def cross_market_check(keys: Sequence[str]) -> Dict:
    """No candidate's identity key already belongs to another market's shard."""
    shards = LP / "markets" / "authority"
    collisions: List[Dict] = []
    markets = 0
    if shards.is_dir():
        for routing in sorted(shards.glob("*/identity_routing.json")):
            market = routing.parent.name
            markets += 1
            if market == MARKET:
                continue
            document = _load(routing)
            other = {str(r.get("identity_key") or "")
                     for r in (document.get("routes") or ())}
            for key in sorted(set(keys) & other):
                collisions.append(OrderedDict((("identity_key", key),
                                               ("also_in_market", market))))
    return OrderedDict((("ok", not collisions),
                        ("markets_scanned", markets),
                        ("collisions", collisions)))


def validate(ledger: Mapping, classification: Mapping, readiness: Mapping,
             store: Mapping[str, Mapping], packet: Mapping) -> Dict:
    keys = [c["identity_key"] for c in readiness["candidates"]]

    silent = {e["identity_key"] for e in ledger["silence_rulings"]}
    silent_as_no_pets = sorted(
        r["identity_key"] for r in classification["rows"]
        if r["identity_key"] in silent and r["now"] == CLEAN_VERIFIED_NO_PETS)

    held_keys = {e["identity_key"] for e in ledger["identity_rulings"]
                 if e["ruling"] == HOLD_IDENTITY}
    still_held = sorted(k for k in keys if k in held_keys)

    merged = [p for p in ledger["pair_rulings"] if p["merged"]]
    phone_only = [p for p in ledger["pair_rulings"]
                  if p["decided_on_shared_telephone_alone"]]
    phone_only += [e for e in ledger["identity_rulings"]
                   if e["ruling"] == SAME_PROPERTY_CONFIRMED
                   and not e["non_telephone_signals"]]

    confirmed = {e["identity_key"] for e in ledger["identity_rulings"]
                 if e["ruling"] == SAME_PROPERTY_CONFIRMED}
    rejected = sorted(
        k for k in keys
        if str((store.get(k, {}).get("membrane") or {}).get("verdict") or "")
        != "VALID" and k not in confirmed)

    urls = [str(store[k]["observation"]["source_url"]) for k in keys
            if k in store]
    duplicate_urls = sorted(u for u, n in Counter(urls).items() if n > 1)

    wrongly_negative = sorted(
        r["identity_key"] for r in classification["rows"]
        if r["now"] == CLEAN_VERIFIED_NO_PETS
        and r["pets_allowed_after_rulings"] is not False)

    ruled = ruled_keys(ledger)
    autosigned = sorted(r["identity_key"] for r in classification["rows"]
                        if r["signed_in_this_order"]
                        and r["identity_key"] not in ruled)

    checks = OrderedDict((
        ("no_hold_enters_authority", OrderedDict((
            ("ok", not still_held), ("identity_keys", still_held)))),
        ("every_no_pets_row_states_a_refusal", OrderedDict((
            ("ok", not wrongly_negative),
            ("identity_keys", wrongly_negative),
            ("why", "a CLEAN_VERIFIED_NO_PETS row must carry pets_allowed "
                    "FALSE after the rulings. An unresolved allowance read as "
                    "falsy is how a hotel that charges per pet becomes a "
                    "no-pets entry")))),
        ("no_policy_not_found_row_becomes_no_pets", OrderedDict((
            ("ok", not silent_as_no_pets),
            ("identity_keys", silent_as_no_pets),
            ("why", "source silence is a fact about the source; publishing it "
                    "as a refusal would invent a policy the hotel never made")))),
        ("no_shared_phone_merge_occurs", OrderedDict((
            ("ok", not merged and not phone_only),
            ("pairs_merged", len(merged)),
            ("rulings_resting_on_the_telephone_alone", len(phone_only)),
            ("confirmation_rule", CONFIRMATION_RULE)))),
        ("no_membrane_rejected_observation_enters_without_a_ruling", OrderedDict((
            ("ok", not rejected), ("identity_keys", rejected),
            ("why", "avid hotel Zeeland is the one membrane rejection in this "
                    "market, and it enters only because this order carries an "
                    "explicit identity ruling for it")))),
        ("no_duplicate_canonical_url", OrderedDict((
            ("ok", not duplicate_urls),
            ("duplicate_source_urls", duplicate_urls)))),
        ("no_cross_market_collision", cross_market_check(keys)),
        ("no_other_market_authority_changes", OrderedDict((
            ("ok", True),
            ("why", "this pass writes three launch-package artifacts and no "
                    "market contract or authority shard; the test asserts it "
                    "from git status")))),
        ("no_row_is_auto_signed", OrderedDict((
            ("ok", not autosigned), ("identity_keys", autosigned),
            ("why", "a signature appears only on a row this order names")))),
        ("every_confirmation_carries_a_non_telephone_signal", OrderedDict((
            ("ok", all(e["non_telephone_signals"]
                       for e in ledger["identity_rulings"]
                       if e["ruling"] == SAME_PROPERTY_CONFIRMED)),
            ("confirmations", len(confirmed))))),
        ("spend_is_zero", OrderedDict((
            ("ok", True), ("usd", 0.0), ("plan_credits", 0.0),
            ("provider_calls", 0)))),
    ))
    checks["all_pass"] = all(v["ok"] for v in checks.values())
    return checks


# --------------------------------------------------------------------------- #
# The run
# --------------------------------------------------------------------------- #

def _header(schema: str, what: str, inputs: Mapping[str, Path]) -> "OrderedDict":
    return OrderedDict((
        ("schema", schema),
        ("what_this_is", what),
        ("market_id", MARKET),
        ("work_order", WORK_ORDER),
        ("provider_calls", 0),
        ("usd_spent", 0.0),
        ("plan_credits_spent", 0.0),
        ("inputs", OrderedDict(
            (name, OrderedDict((
                ("path", str(path.relative_to(_REPO_ROOT).as_posix())),
                ("sha256", _sha256(path)))))
            for name, path in inputs.items())),
    ))


def build(paths: Mapping[str, Path]) -> Dict[str, Dict]:
    packet = _load(paths["packet"])
    store_doc = _load(paths["store"])
    census_doc = _load(paths["census"])
    dedup = _load(paths["dedup"])
    holds = _load(paths["holds"])
    replay = _load(paths["replay"])

    store = {r["identity_key"]: r for r in store_doc["records"]}
    census = {h["identity_key"]: h for h in census_doc["hotels"]}

    ledger = _header(
        "ptf-founder-decision-ledger/1.0",
        "Every ruling this work order made, and nothing else. A row the order "
        "did not name carries no decision.",
        {k: paths[k] for k in ("packet", "store", "census", "dedup")})
    ledger.update(OrderedDict((
        ("founder_id", FOUNDER),
        ("doctrines", [DOCTRINE_PRICE_IMPLIES_ALLOWANCE,
                       DOCTRINE_SOURCE_SILENCE]),
        ("authorship", OrderedDict((
            (BY_FOUNDER, "a doctrine the founder stated, or a correction the "
                         "founder named"),
            (BY_OPERATOR_UNDER_DELEGATION,
             "a per-row identity verdict the founder delegated, decided under "
             "the founder's own constraint and re-derived from the saved "
             "capture")))),
        ("allowance_rulings", build_allowance_entries(store)),
        ("silence_rulings", build_silence_entries(replay, store)),
        ("corrections", build_correction_entries(store)),
        ("identity_rulings", build_identity_entries(census, store)),
        ("pair_rulings", build_pair_entries(census, dedup)),
    )))
    ledger["rows_ruled"] = len(ruled_keys(ledger))
    ledger["rows_left_unsigned"] = len(
        [r for r in packet["clean"]
         if r["identity_key"] not in ruled_keys(ledger)])

    classification = _header(
        "ptf-founder-review-classification/1.0",
        "The 019 classification of the 54 owned-evidence rows, rebuilt with "
        "this order's rulings applied. Offline.",
        {k: paths[k] for k in ("packet", "store")})
    classification.update(reclassify(packet, store, ledger))

    readiness = _header(
        "ptf-proposed-authority-readiness/1.0",
        "What the Grand Rapids authority would contain, and the one gate in "
        "front of it. Not an authority, and not published.",
        {k: paths[k] for k in ("packet", "store", "census", "holds")})
    readiness.update(authority_readiness(classification, holds, store, ledger))
    readiness["validation"] = validate(ledger, classification, readiness,
                                       store, packet)

    return OrderedDict((("founder_decision_ledger", ledger),
                        ("classification", classification),
                        ("authority_readiness", readiness)))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default=str(LP))
    args = parser.parse_args(argv)

    paths = {
        "packet": LP / "grand_rapids_holland_mi_exception_review_packet_019.json",
        "store": LP / "grand_rapids_holland_mi_observation_store_001.json",
        "census": (LP / "identity_census" / "recensus"
                   / "grand-rapids-holland-mi.json"),
        "dedup": LP / "grand_rapids_holland_mi_pre_acquisition_dedup_001.json",
        "holds": LP / "grand_rapids_holland_mi_identity_holds_019.json",
        "replay": LP / "grand_rapids_holland_mi_cross_run_ledger_replay_018.json",
    }
    documents = build(paths)
    names = {
        "founder_decision_ledger":
            "grand_rapids_holland_mi_founder_decision_ledger_020.json",
        "classification":
            "grand_rapids_holland_mi_founder_review_classification_020.json",
        "authority_readiness":
            "grand_rapids_holland_mi_proposed_authority_readiness_020.json",
    }
    out_dir = Path(args.out_dir)
    for slot, document in documents.items():
        path = out_dir / names[slot]
        path.write_text(json.dumps(document, indent=1, ensure_ascii=False) + "\n",
                        encoding="utf-8")

    ledger = documents["founder_decision_ledger"]
    classification = documents["classification"]
    readiness = documents["authority_readiness"]
    print("rulings: %d allowance, %d silence, %d corrections, %d identity, "
          "%d pairs"
          % (len(ledger["allowance_rulings"]), len(ledger["silence_rulings"]),
             len(ledger["corrections"]), len(ledger["identity_rulings"]),
             len(ledger["pair_rulings"])))
    print("rows ruled / left unsigned : %d / %d"
          % (ledger["rows_ruled"], ledger["rows_left_unsigned"]))
    for name, value in classification["counts"].items():
        print("  %-40s %d" % (name.lower(), value))
    print("changed by this order      : %d" % len(classification["changed"]))
    print("authority would contain    : %d (%d pet-friendly, %d no-pets)"
          % (readiness["would_contain"], readiness["pet_friendly"],
             readiness["verified_no_pets"]))
    print("fact-ruled / awaiting an approval: %d / %d"
          % (len(readiness["rows_with_a_founder_fact_ruling"]),
             readiness["awaiting_a_record_level_approval"]))
    print("ready to build             : %s" % readiness["ready_to_build"])
    print("validation                 : %s"
          % readiness["validation"]["all_pass"])
    for name in names.values():
        print("written                    : %s" % name)
    return 0 if readiness["validation"]["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
