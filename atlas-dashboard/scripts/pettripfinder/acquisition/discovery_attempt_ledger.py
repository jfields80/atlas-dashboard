# -*- coding: utf-8 -*-
"""PTF-GENERIC-CROSS-RUN-DISCOVERY-ATTEMPT-LEDGER-001 -- pay once to FIND a page, ever.

WHAT THE PAID-ATTEMPT LEDGER ALREADY DOES, AND WHERE IT STOPS
--------------------------------------------------------------
``paid_attempt_ledger`` remembers every page this project has ever paid to
FETCH, keyed on the page rather than on the name the census gave the building
that month. It ended a real leak: Indianapolis bought one Hampton Inn page
twice because a re-census renamed the identity key between passes.

It records three lanes -- ``brightdata_browser``, ``brightdata_web_unlocker``
and ``firecrawl`` -- and every one of them FETCHES a page you already have a
URL for. None of them can FIND one. So a paid lookup that asks a places
provider "where is this hotel's website?" is invisible to it, and the leak it
closed for policy capture is still wide open for discovery.

WHY THAT MATTERS NOW, WITH A NUMBER
------------------------------------
Indianapolis holds 143 identities that name no website. The proposed remedy is
a targeted Google Places lookup per identity. The discovery layer already
caches raw provider responses under a sha256 request fingerprint, so an
identical query costs nothing to repeat -- but ``GOOGLE_CACHE_RETENTION_DAYS``
is 30, and a re-census six weeks later renames keys and asks again. Cache is a
performance store with an expiry date. A LEDGER IS A MEMORY WITHOUT ONE, and
that difference is the entire reason this module exists.

THE CORE INVARIANT
------------------
    Same real property + materially unchanged discovery query:
    DO NOT LOOK IT UP AGAIN.

A repeat lookup is permitted only when one of five things is affirmatively
true, and the decision RECORDS which one:

    IDENTITY_CHANGED             the row now names a different property.
    PREMISES_CHANGED             the address, telephone or name evidence the
                                 query is built from materially changed.
    PROVIDER_CAPABILITY_CHANGED  the provider or field mask gained something
                                 that post-dates the prior lookup.
    DIFFERENT_DISCOVERY_METHOD   the prior lookup was unusable AND a different
                                 method is explicitly authorised. A failed
                                 lookup repeated by the same method is the
                                 definition of buying the same nothing twice.
    OPERATOR_OVERRIDE            a named human, with a durable reason.

WHAT THIS MODULE REFUSES TO DO
------------------------------
It will not collapse two hotels because they share a building, a switchboard, a
street or a brand. A Hampton Inn and a Homewood Suites share all four, and
suppressing one of them means it never gets a URL, never gets a policy and
never gets published. Losing a hotel is worse than paying twice to find it. So
the premises keys here PROPOSE and never decide: each needs a compatible name
or a shared telephone to confirm, and two disagreeing provider place ids refute
it outright.

And a suppressed row is never dropped. It moves to a named suppression list
that coverage still counts, because a property whose URL we already know is
routed, not missing.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.discovery import identity_dedup as DEDUP  # noqa: E402

SCHEMA = "ptf-discovery-attempt-ledger/1.0"
WHAT_THIS_IS = (
    "Every paid discovery lookup this project has ever made -- a request to a "
    "places provider asking where a named property's official website is. "
    "Keyed on the PROPERTY and on the QUERY rather than on the identity key, "
    "so a rename, a re-census or a later work order cannot buy the same answer "
    "twice. Durable on purpose: the provider response cache expires, this "
    "does not."
)

# --------------------------------------------------------------------------- #
# Match keys, strongest first
# --------------------------------------------------------------------------- #

#: The provider's own id for the place. If a prior lookup resolved to this id,
#: the provider has already told us what it knows about this property.
MATCH_PROVIDER_PLACE_ID = "PROVIDER_PLACE_ID"

#: The exact question, already asked. Same provider, same method, same field
#: mask, same premises -> the same answer, and the cache expiring does not make
#: it a different question.
MATCH_QUERY_FINGERPRINT = "QUERY_FINGERPRINT"

#: A switchboard. Strong, but shared by every hotel in a dual-brand building,
#: so it must be confirmed.
MATCH_TELEPHONE = "TELEPHONE"

#: A street and a postal code. The weakest key here and the one that groups
#: genuinely distinct hotels, so it never stands alone.
MATCH_PREMISES_EVIDENCE = "PREMISES_EVIDENCE"

MATCH_PRIORITY: Tuple[str, ...] = (
    MATCH_PROVIDER_PLACE_ID, MATCH_QUERY_FINGERPRINT, MATCH_TELEPHONE,
    MATCH_PREMISES_EVIDENCE,
)

#: The keys that name the PROPERTY or the QUESTION outright. A match on either
#: means a second lookup buys an answer we already own.
DECISIVE_KEYS: Tuple[str, ...] = (MATCH_PROVIDER_PLACE_ID,
                                  MATCH_QUERY_FINGERPRINT)

#: The keys that may NOT stand alone, for exactly the reason the paid-attempt
#: ledger gives: a Hampton Inn and a Homewood Suites share one address, one
#: switchboard and one brand. Brand-plus-address alone would collapse them into
#: a single lookup and leave one of the two hotels unroutable for ever.
CONFIRMATION_REQUIRED_KEYS: Tuple[str, ...] = (MATCH_TELEPHONE,
                                               MATCH_PREMISES_EVIDENCE)

# --------------------------------------------------------------------------- #
# What a prior lookup is still worth
# --------------------------------------------------------------------------- #

BIND_BOUND = "BOUND"
BIND_NO_RESULT = "UNBOUND_NO_RESULT"
BIND_NO_WEBSITE = "UNBOUND_NO_WEBSITE"
BIND_REJECTED_URL_SHAPE = "UNBOUND_REJECTED_URL_SHAPE"
BIND_NO_SANCTIONED_KEY = "UNBOUND_NO_SANCTIONED_KEY"

BIND_STATES: Tuple[str, ...] = (BIND_BOUND, BIND_NO_RESULT, BIND_NO_WEBSITE,
                                BIND_REJECTED_URL_SHAPE, BIND_NO_SANCTIONED_KEY)

#: A lookup that produced a usable URL. Its answer is owned; never re-buy.
ANSWERED_STATES = frozenset({BIND_BOUND})

#: Lookups that answered the QUESTION without producing a URL. The provider was
#: asked and said no -- "this place has no website on record", "the only URL is
#: a booking aggregator", "nothing here matches on a sanctioned key". Repeating
#: the identical query by the identical method buys the same nothing again, so
#: these suppress too, and say so differently.
ANSWERED_NEGATIVE_STATES = frozenset({BIND_NO_RESULT, BIND_NO_WEBSITE,
                                      BIND_REJECTED_URL_SHAPE,
                                      BIND_NO_SANCTIONED_KEY})

# --------------------------------------------------------------------------- #
# Decisions
# --------------------------------------------------------------------------- #

FIRST_DISCOVERY_LOOKUP = "FIRST_DISCOVERY_LOOKUP"

SUPPRESSED_URL_ALREADY_KNOWN = "SUPPRESSED_URL_ALREADY_KNOWN"
SUPPRESSED_ALREADY_LOOKED_UP = "SUPPRESSED_ALREADY_LOOKED_UP"
SUPPRESSED_SAME_METHOD_ALREADY_FAILED = "SUPPRESSED_SAME_METHOD_ALREADY_FAILED"

ALLOWED_IDENTITY_CHANGED = "ALLOWED_IDENTITY_CHANGED"
ALLOWED_PREMISES_CHANGED = "ALLOWED_PREMISES_CHANGED"
ALLOWED_CAPABILITY_CHANGED = "ALLOWED_CAPABILITY_CHANGED"
ALLOWED_DIFFERENT_METHOD = "ALLOWED_DIFFERENT_METHOD"
ALLOWED_OPERATOR_OVERRIDE = "ALLOWED_OPERATOR_OVERRIDE"

ALLOWED_DECISIONS: Tuple[str, ...] = (
    FIRST_DISCOVERY_LOOKUP, ALLOWED_IDENTITY_CHANGED, ALLOWED_PREMISES_CHANGED,
    ALLOWED_CAPABILITY_CHANGED, ALLOWED_DIFFERENT_METHOD,
    ALLOWED_OPERATOR_OVERRIDE,
)
SUPPRESSED_DECISIONS: Tuple[str, ...] = (
    SUPPRESSED_URL_ALREADY_KNOWN, SUPPRESSED_ALREADY_LOOKED_UP,
    SUPPRESSED_SAME_METHOD_ALREADY_FAILED,
)

MATERIAL_IDENTITY_CHANGED = "IDENTITY_CHANGED"
MATERIAL_PREMISES_CHANGED = "PREMISES_CHANGED"
MATERIAL_CAPABILITY_CHANGED = "PROVIDER_CAPABILITY_CHANGED"
MATERIAL_DIFFERENT_METHOD = "DIFFERENT_DISCOVERY_METHOD"
MATERIAL_OPERATOR_OVERRIDE = "OPERATOR_OVERRIDE"

MATERIAL_CHANGES: Tuple[str, ...] = (
    MATERIAL_IDENTITY_CHANGED, MATERIAL_PREMISES_CHANGED,
    MATERIAL_CAPABILITY_CHANGED, MATERIAL_DIFFERENT_METHOD,
    MATERIAL_OPERATOR_OVERRIDE,
)


class DiscoveryLedgerError(ValueError):
    """The ledger was handed something it cannot record honestly."""


# --------------------------------------------------------------------------- #
# Normalisation -- deliberately the same shapes the paid ledger uses
# --------------------------------------------------------------------------- #

_WS = re.compile(r"\s+")
_NOT_ALNUM = re.compile(r"[^a-z0-9]+")

_STREET_WORDS = {
    "street": "st", "avenue": "ave", "road": "rd", "drive": "dr",
    "boulevard": "blvd", "lane": "ln", "court": "ct", "circle": "cir",
    "parkway": "pkwy", "highway": "hwy", "place": "pl", "square": "sq",
    "terrace": "ter", "trail": "trl", "north": "n", "south": "s", "east": "e",
    "west": "w", "northeast": "ne", "northwest": "nw", "southeast": "se",
    "southwest": "sw", "suite": "", "ste": "", "unit": "",
}


def _text(value) -> str:
    return _WS.sub(" ", str(value or "")).strip()


def normalized_name(row: Mapping) -> str:
    raw = _text(row.get("canonical_name") or row.get("normalized_name")
                or row.get("name") or row.get("identity_key"))
    return _NOT_ALNUM.sub(" ", raw.lower()).strip()


def normalized_street(row: Mapping) -> str:
    raw = _text(row.get("street") or row.get("address") or row.get("address_line"))
    tokens = _NOT_ALNUM.sub(" ", raw.lower()).split()
    return " ".join(_STREET_WORDS.get(t, t) for t in tokens if _STREET_WORDS.get(t, t))


def normalized_phone(row: Mapping) -> str:
    digits = re.sub(r"\D", "", _text(row.get("telephone") or row.get("phone")))
    return digits[-10:] if len(digits) >= 10 else ""


def postal_code(row: Mapping) -> str:
    return _text(row.get("postal_code") or row.get("zip"))[:5]


def query_premises(row: Mapping) -> Dict[str, str]:
    """The facts a discovery query is BUILT from.

    Only these decide whether two queries are the same question. The identity
    key is deliberately absent: a rename changes the key and changes nothing
    about the building, and that is the whole leak this module closes.
    """
    return OrderedDict((
        ("name", normalized_name(row)),
        ("street", normalized_street(row)),
        ("city", _NOT_ALNUM.sub(" ", _text(row.get("city")).lower()).strip()),
        ("state", _text(row.get("state")).upper()[:2]),
        ("postal_code", postal_code(row)),
        ("telephone", normalized_phone(row)),
    ))


def query_fingerprint(row: Mapping, *, provider: str, method: str,
                      field_mask: Sequence[str] = ()) -> str:
    """A deterministic id for one discovery QUESTION.

    Provider, method and field mask are in the key because a richer mask is a
    different question that can return a website where a thinner one could not.
    """
    payload = OrderedDict((
        ("provider", str(provider)), ("method", str(method)),
        ("field_mask", sorted(str(f) for f in field_mask)),
        ("premises", query_premises(row)),
    ))
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def attempt_id(market_id: str, run_id: str, identity_key: str,
               fingerprint: str) -> str:
    seed = "|".join((str(market_id), str(run_id), str(identity_key),
                     str(fingerprint)))
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


# --------------------------------------------------------------------------- #
# Building a record
# --------------------------------------------------------------------------- #

def build_attempt(row: Mapping, *, market_id: str, work_order: str, run_id: str,
                  provider: str, method: str, field_mask: Sequence[str] = (),
                  attempted_at: str = "", place_id: str = "",
                  website_uri: str = "", national_phone_number: str = "",
                  bind_state: str = BIND_NO_RESULT, bind_method: str = "",
                  bind_result: str = "", outcome: str = "",
                  cache_pointer: str = "", paid_requests: int = 1,
                  cost_usd_minor: Optional[float] = None) -> Dict:
    """One paid discovery lookup, as it will be remembered for ever."""
    if bind_state not in BIND_STATES:
        raise DiscoveryLedgerError("unknown bind_state %r; expected one of %s"
                                   % (bind_state, ", ".join(BIND_STATES)))
    fingerprint = query_fingerprint(row, provider=provider, method=method,
                                    field_mask=field_mask)
    premises = query_premises(row)
    return OrderedDict((
        ("attempt_id", attempt_id(market_id, run_id,
                                  str(row.get("identity_key") or ""), fingerprint)),
        ("market_id", str(market_id)), ("work_order", str(work_order)),
        ("run_id", str(run_id)),
        ("identity_key", str(row.get("identity_key") or "")),
        ("normalized_name", premises["name"]),
        ("street", _text(row.get("street") or row.get("address"))),
        ("normalized_street", premises["street"]),
        ("city", _text(row.get("city"))), ("state", premises["state"]),
        ("postal_code", premises["postal_code"]),
        ("telephone", premises["telephone"]),
        ("provider", str(provider)), ("discovery_method", str(method)),
        ("query_fingerprint", fingerprint),
        ("field_mask", sorted(str(f) for f in field_mask)),
        ("query_premises", premises),
        ("attempted_at", str(attempted_at)),
        ("place_id", str(place_id)),
        ("website_uri", str(website_uri)),
        ("national_phone_number", str(national_phone_number)),
        ("bind_result", str(bind_result)), ("bind_method", str(bind_method)),
        ("bind_state", str(bind_state)),
        ("answered", bind_state in ANSWERED_STATES),
        ("outcome", str(outcome or bind_state)),
        ("cache_pointer", str(cache_pointer)),
        ("paid_requests", int(paid_requests)),
        ("cost_usd_minor", cost_usd_minor),
    ))


def new_ledger() -> Dict:
    return OrderedDict((("schema", SCHEMA), ("what_this_is", WHAT_THIS_IS),
                        ("attempts", [])))


def load(path) -> Dict:
    path = Path(path)
    if not path.is_file():
        return new_ledger()
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema") != SCHEMA:
        raise DiscoveryLedgerError("not a %s document: %r"
                                   % (SCHEMA, document.get("schema")))
    return document


def save(path, ledger: Mapping) -> None:
    Path(path).write_text(json.dumps(ledger, indent=2), encoding="utf-8")


def merge(ledger: Mapping, records: Sequence[Mapping]) -> Dict:
    """Append, idempotently. Re-ingesting a run never doubles its rows."""
    out = OrderedDict(ledger or new_ledger())
    attempts = [dict(a) for a in (out.get("attempts") or ())]
    seen = {str(a.get("attempt_id")) for a in attempts}
    for record in records:
        if not isinstance(record, Mapping):
            raise DiscoveryLedgerError("a ledger record must be a mapping, got %r"
                                       % type(record).__name__)
        if str(record.get("attempt_id")) in seen:
            continue
        attempts.append(dict(record))
        seen.add(str(record.get("attempt_id")))
    out["schema"] = SCHEMA
    out.setdefault("what_this_is", WHAT_THIS_IS)
    out["attempts"] = attempts
    return out


# --------------------------------------------------------------------------- #
# The index
# --------------------------------------------------------------------------- #

class DiscoveryIndex:
    """Every recorded lookup, indexed by each match key it carries."""

    def __init__(self, ledger: Mapping):
        self.attempts: List[Dict] = [dict(a) for a in (ledger.get("attempts") or ())]
        self._by: Dict[str, Dict[str, List[Dict]]] = {k: {} for k in MATCH_PRIORITY}
        for record in self.attempts:
            for kind, value in self._keys_of(record):
                self._by[kind].setdefault(value, []).append(record)

    @staticmethod
    def _keys_of(record: Mapping) -> List[Tuple[str, str]]:
        keys: List[Tuple[str, str]] = []
        if record.get("place_id"):
            keys.append((MATCH_PROVIDER_PLACE_ID, str(record["place_id"])))
        if record.get("query_fingerprint"):
            keys.append((MATCH_QUERY_FINGERPRINT, str(record["query_fingerprint"])))
        if record.get("telephone"):
            keys.append((MATCH_TELEPHONE, str(record["telephone"])))
        street, zipc = record.get("normalized_street"), record.get("postal_code")
        if street and zipc:
            keys.append((MATCH_PREMISES_EVIDENCE, "%s|%s" % (street, zipc)))
        return keys

    def lookup(self, row: Mapping, *, provider: str, method: str,
               field_mask: Sequence[str] = ()) -> Tuple[str, str, List[Dict]]:
        """``(match_key, value, attempts)`` -- the STRONGEST evidence that this
        property has been looked up before, or ``("", "", [])``.

        Walked in strength order, stopping at the first key that matches --
        except that a key needing confirmation which fails to get it does NOT
        stop the walk; it falls through to the next.
        """
        fingerprint = query_fingerprint(row, provider=provider, method=method,
                                        field_mask=field_mask)
        candidates = {
            MATCH_PROVIDER_PLACE_ID: str(row.get("place_id") or ""),
            MATCH_QUERY_FINGERPRINT: fingerprint,
            MATCH_TELEPHONE: normalized_phone(row),
            MATCH_PREMISES_EVIDENCE: "%s|%s" % (normalized_street(row),
                                                postal_code(row)),
        }
        row_place = candidates[MATCH_PROVIDER_PLACE_ID]
        for kind in MATCH_PRIORITY:
            value = candidates[kind]
            if not value or value.strip("|") == "":
                continue
            found = self._by[kind].get(value) or []
            if not found:
                continue
            if kind in CONFIRMATION_REQUIRED_KEYS:
                found = [a for a in found if self._confirmed(row, a, row_place)]
                if not found:
                    continue
            return (kind, value, found)
        return ("", "", [])

    @staticmethod
    def _confirmed(row: Mapping, record: Mapping, row_place: str) -> bool:
        """Whether a shared switchboard or street is the SAME property.

        Two different provider place ids are two places on the provider's own
        authority and refute the match outright. Otherwise it needs positive
        confirmation: a compatible name in the sense the census dedup already
        defines. A shared telephone alone is a fact about a phone line, not
        about a building.
        """
        record_place = str(record.get("place_id") or "")
        if row_place and record_place and row_place != record_place:
            return False
        return DEDUP.names_compatible(normalized_name(row),
                                      str(record.get("normalized_name") or ""))


# --------------------------------------------------------------------------- #
# The decision
# --------------------------------------------------------------------------- #

def validate_material(assertions: Optional[Mapping[str, str]]) -> None:
    """Refuse a malformed assertion BEFORE any branch reads it.

    Checked up front rather than where it is used, because the decision returns
    early on several paths and a claim that is never reached is a claim that is
    never checked. A caller who supplies a reason with no detail has written a
    guard that does nothing, and should hear about it whichever way the
    decision happens to fall.
    """
    if not assertions:
        return
    reason = assertions.get("reason") or assertions.get("kind")
    if reason not in MATERIAL_CHANGES:
        raise DiscoveryLedgerError(
            "unknown material change %r; expected one of %s"
            % (reason, ", ".join(MATERIAL_CHANGES)))
    if not str(assertions.get("detail") or "").strip():
        raise DiscoveryLedgerError(
            "a %s assertion must carry a durable 'detail' saying what changed "
            "and who says so; an unexplained override is how a guard becomes a "
            "formality" % reason)


def _material(assertions: Optional[Mapping[str, str]], kind: str) -> str:
    if not assertions:
        return ""
    reason = assertions.get("reason") or assertions.get("kind")
    if reason != kind:
        return ""
    return str(assertions.get("detail") or "").strip()


def _latest(attempts: Sequence[Mapping]) -> Mapping:
    return sorted(attempts, key=lambda a: str(a.get("attempted_at") or ""))[-1]


def decide(row: Mapping, index: DiscoveryIndex, *, provider: str, method: str,
           field_mask: Sequence[str] = (),
           material_change: Optional[Mapping[str, str]] = None) -> Dict:
    """Whether this row may be looked up for money, and the record of why."""
    validate_material(material_change)
    fingerprint = query_fingerprint(row, provider=provider, method=method,
                                    field_mask=field_mask)
    decision = OrderedDict((
        ("identity_key", str(row.get("identity_key") or "")),
        ("normalized_name", normalized_name(row)),
        ("provider", str(provider)), ("discovery_method", str(method)),
        ("query_fingerprint", fingerprint),
        ("query_premises", query_premises(row)),
        ("match_key", ""), ("match_value", ""), ("matched_attempts", []),
        ("prior_bind_state", ""), ("prior_website_uri", ""),
        ("prior_place_id", ""), ("prior_run_id", ""), ("prior_market_id", ""),
        ("prior_method", ""), ("prior_cache_pointer", ""),
        ("url_already_known", False),
        ("material_change_reason", ""),
        ("decision", FIRST_DISCOVERY_LOOKUP), ("reason", ""),
    ))

    # An override outranks everything, including a match that was never made.
    override = _material(material_change, MATERIAL_OPERATOR_OVERRIDE)

    match_key, value, found = index.lookup(row, provider=provider, method=method,
                                           field_mask=field_mask)
    if not found:
        if override:
            decision["decision"] = ALLOWED_OPERATOR_OVERRIDE
            decision["material_change_reason"] = override
            decision["reason"] = ("no prior lookup matched, and an operator "
                                  "override is recorded anyway: %s" % override)
            return decision
        decision["reason"] = ("no prior paid discovery lookup matches this "
                              "property or this question")
        return decision

    ordered = sorted(found, key=lambda a: str(a.get("attempted_at") or ""))
    last = _latest(ordered)
    decision["match_key"] = match_key
    decision["match_value"] = value
    decision["matched_attempts"] = [str(a.get("attempt_id")) for a in ordered]
    decision["prior_bind_state"] = str(last.get("bind_state") or "")
    decision["prior_website_uri"] = str(last.get("website_uri") or "")
    decision["prior_place_id"] = str(last.get("place_id") or "")
    decision["prior_run_id"] = str(last.get("run_id") or "")
    decision["prior_market_id"] = str(last.get("market_id") or "")
    decision["prior_method"] = str(last.get("discovery_method") or "")
    decision["prior_cache_pointer"] = str(last.get("cache_pointer") or "")

    answered = [a for a in ordered if a.get("bind_state") in ANSWERED_STATES]
    if answered:
        decision["url_already_known"] = True
        decision["prior_website_uri"] = str(_latest(answered).get("website_uri") or "")

    if override:
        decision["decision"] = ALLOWED_OPERATOR_OVERRIDE
        decision["material_change_reason"] = override
        decision["reason"] = ("an operator override permits this repeat lookup: "
                              "%s" % override)
        return decision

    identity_changed = _material(material_change, MATERIAL_IDENTITY_CHANGED)
    if identity_changed:
        decision["decision"] = ALLOWED_IDENTITY_CHANGED
        decision["material_change_reason"] = identity_changed
        decision["reason"] = ("this row no longer names the property the prior "
                              "lookup resolved: %s" % identity_changed)
        return decision

    premises_changed = _material(material_change, MATERIAL_PREMISES_CHANGED)
    if premises_changed:
        # Only real when the premises actually differ. An assertion that the
        # address changed, over a query that fingerprints identically, is a
        # claim contradicted by the ledger's own record.
        prior_premises = dict(last.get("query_premises") or {})
        if prior_premises and prior_premises != dict(query_premises(row)):
            decision["decision"] = ALLOWED_PREMISES_CHANGED
            decision["material_change_reason"] = premises_changed
            decision["reason"] = ("the evidence this query is built from "
                                  "changed since the prior lookup: %s"
                                  % premises_changed)
            return decision

    capability = _material(material_change, MATERIAL_CAPABILITY_CHANGED)
    if capability:
        decision["decision"] = ALLOWED_CAPABILITY_CHANGED
        decision["material_change_reason"] = capability
        decision["reason"] = ("a provider capability post-dates the prior "
                              "lookup: %s" % capability)
        return decision

    if decision["url_already_known"]:
        decision["decision"] = SUPPRESSED_URL_ALREADY_KNOWN
        decision["reason"] = (
            "a prior paid lookup (%s, run %r) already resolved this property to "
            "%s; a second lookup would buy a URL we already own"
            % (match_key.lower().replace("_", " "), decision["prior_run_id"],
               decision["prior_website_uri"] or "a website"))
        return decision

    different_method = _material(material_change, MATERIAL_DIFFERENT_METHOD)
    if different_method:
        if str(last.get("discovery_method") or "") == str(method):
            decision["decision"] = SUPPRESSED_SAME_METHOD_ALREADY_FAILED
            decision["reason"] = (
                "a different discovery method is asserted, but %r is the method "
                "that already failed here; repeating it buys the same nothing "
                "again" % method)
            return decision
        decision["decision"] = ALLOWED_DIFFERENT_METHOD
        decision["material_change_reason"] = different_method
        decision["reason"] = ("the prior lookup was unusable (%s) and a "
                              "different method is authorised: %s"
                              % (decision["prior_bind_state"], different_method))
        return decision

    if str(last.get("bind_state") or "") in ANSWERED_NEGATIVE_STATES:
        decision["decision"] = SUPPRESSED_SAME_METHOD_ALREADY_FAILED
        decision["reason"] = (
            "a prior paid lookup (run %r, method %r) asked this exact question "
            "and could not answer it (%s). Asking it again the same way buys "
            "the same nothing; what changes it is a different method, changed "
            "premises, or an operator override"
            % (decision["prior_run_id"], decision["prior_method"],
               decision["prior_bind_state"]))
        return decision

    decision["decision"] = SUPPRESSED_ALREADY_LOOKED_UP
    decision["reason"] = ("a prior paid lookup (%s, run %r) already covers this "
                          "property" % (match_key.lower().replace("_", " "),
                                        decision["prior_run_id"]))
    return decision


def suppress(cohort: Sequence[Mapping], ledger: Mapping, *, provider: str,
             method: str, field_mask: Sequence[str] = (),
             material_changes: Optional[Mapping[str, Mapping[str, str]]] = None
             ) -> Tuple[List[Dict], List[Dict]]:
    """``(payable, suppressed)`` over a discovery cohort. A partition, always.

    Every input row lands in exactly one list and neither invents a row, so
    coverage can keep counting the census it already counts. A suppressed row
    is a property whose URL we already know or already failed to find -- not a
    property that vanished.
    """
    index = DiscoveryIndex(ledger)
    payable: List[Dict] = []
    suppressed: List[Dict] = []
    for row in cohort:
        key = str(row.get("identity_key") or "")
        decision = decide(row, index, provider=provider, method=method,
                          field_mask=field_mask,
                          material_change=(material_changes or {}).get(key))
        enriched = OrderedDict(row)
        enriched["discovery_history"] = decision
        if decision["decision"] in ALLOWED_DECISIONS:
            payable.append(enriched)
        else:
            enriched["settled_because"] = decision["reason"]
            suppressed.append(enriched)
    return (payable, suppressed)


def summary(payable: Sequence[Mapping], suppressed: Sequence[Mapping]) -> Dict:
    """The discovery-history section of a cost plan or a discovery report."""
    def _count(rows):
        return Counter(r["discovery_history"]["decision"] for r in rows
                       if r.get("discovery_history"))
    out = OrderedDict()
    out["schema"] = SCHEMA
    out["payable"] = len(payable)
    out["suppressed"] = len(suppressed)
    out["payable_by_decision"] = OrderedDict(sorted(_count(payable).items()))
    out["suppressed_by_decision"] = OrderedDict(sorted(_count(suppressed).items()))
    out["suppressed_by_match_key"] = OrderedDict(sorted(Counter(
        r["discovery_history"]["match_key"] for r in suppressed
        if r.get("discovery_history")).items()))
    out["url_already_known"] = sum(
        1 for r in suppressed if r.get("discovery_history", {}).get("url_already_known"))
    # A partition, stated so coverage can assert it rather than trust it.
    out["accounted_for"] = len(payable) + len(suppressed)
    return out
