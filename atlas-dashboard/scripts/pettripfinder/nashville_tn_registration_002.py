"""PTF-NASHVILLE-TN-PROMOTION-AND-NEW-LANE-LAUNCH-PREP-002 -- the Nashville applier.

Turns the Nashville SHADOW that PTF-NASHVILLE-TN-NEW-MARKET-001 committed --
``markets/proposed/nashville-tn.json`` and
``identity_census_proposed/nashville-tn.json`` -- into registered production
source on the redesigned release lane. It is the only module in this order that
writes outside a Nashville-named path.

WHAT IT BUILDS

  markets/nashville-tn.json                                 the market contract
  identity_census/nashville-tn.json                         the registered census
  nashville_tn_identity_holds_002.json                      rows the gates hold
  nashville_tn_final_partition_001.json                     every identity, once
  hotel_policy_facts_nashville-tn.json                      the published rows
  markets/authority/nashville-tn/seed_businesses.csv        the display rows
  markets/authority/nashville-tn/hotel_exclusions.json      the VERIFIED_NO_PETS
  markets/authority/nashville-tn/identity_routing.json      empty; no override
  markets/authority/nashville-tn/affiliate_destinations.json empty; none authored

SEMANTIC PRESERVATION IS THE WHOLE POINT

This order may not re-research Nashville, may not re-run its census, its
browser lane or its Firecrawl lane, and may not improve its counts. Every fact
written here already exists in the committed shadow; this module RESHAPES it
into the documents the registered contracts own and refuses rather than
inventing a value it cannot find.

Nashville arrives in far better shape than Lexington did, because
PTF-NASHVILLE-TN-NEW-MARKET-001 already built on the modern contracts:

  * every canonical name round-trips through ``ptf_identity_key/1.0`` and the
    181 registered keys are distinct, so there is no same-name collapse to
    break and no row is renamed;
  * the proposed market contract parses under ``markets.contract`` unchanged;
  * corridors are a real postal partition
    (``census_membership_basis = CORRIDOR_REGISTRY``), so no membership basis
    has to be restated.

FOUR MECHANICAL SERIALIZATION REPAIRS, AND NOTHING ELSE

The proposed census predates four fields the registered census contract
requires. Each is derived, never decided:

  slug             ``slugify(canonical_name)``, the same derivation every other
                   registered market uses.
  market_id        the market this file is for.
  identity_state   IDENTITY_CONFIRMED. Every proposed row is classified
                   TRUE_HOTEL_IDENTITY by the committed reconciliation, which is
                   that judgement under the shadow's own vocabulary.
  lodging_state    LODGING_CONFIRMED, for the same reason: the reconciliation
                   separates NON_LODGING into its own class and admits none of
                   them.

Plus two rows that state no city. Both are filled from the row's OWN
first-party read (``identity_signals.locality`` / the census address), and the
basis is recorded on the row. Nothing is guessed.

THE COUNT GATE COMES FIRST, THE MODERN GATES SECOND

The shadow's own numbers -- 181 census / 80 clean pet-friendly / 19 clean
verified-no-pets / 82 unresolved -- are read from the committed report, never
typed, and must reproduce EXACTLY from the carry-across before anything is
allowed to remove a row. Only then do the modern gates run, and every row they
hold is named with its reason in ``nashville_tn_identity_holds_002.json``.

WHAT THE MODERN EVIDENCE GATE FINDS, AND WHY IT IS NOT NEGOTIABLE

Nashville's attended browser lane read 154 property pages in two same-origin
navigations for $0 -- an excellent lane -- and recorded ``document_bytes`` for
each page but NO ``document_sha256``. 84 of the 99 clean rows therefore carry no
capture hash, and there is no artifact to hash after the fact: the acquisition
directories the shadow named are gitignored and empty.

``first_party_binding`` refuses those rows on CAPTURE_HASH, and this module
holds every one of them. It does NOT do what
``toledo_oh_promotion_application_002.evidence_rows`` does, which is to fall
back to ``sha256(source_url + quote)`` when the lane recorded no document hash.
That value is a hash of the citation, not of the document: it can be computed
without ever having fetched the page, so it proves exactly nothing, and
publishing it would satisfy the gate by manufacturing the evidence the gate
exists to demand. A missing hash is a hold. An invented one is worse.

The remedy is cheap and is a later order's: re-read those 84 pages on the same
attended same-origin lane, at $0, hashing each document in the same call that
takes the quote (the PTF-PITTSBURGH precedent). It is a RE-CAPTURE, which this
order is forbidden to perform.

WHAT IT REFUSES

  A clean row whose name will not round-trip to its identity key. A clean row
  that resolves to no registered census identity. Two clean reads on one
  identity. A held identity that reaches the published set. A count that
  disagrees with the governing shadow. It raises rather than writing a partial
  package.

Nothing here deploys and nothing here flips launch participation.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.contracts import census as CENSUS          # noqa: E402
from scripts.pettripfinder.contracts import enums                     # noqa: E402
from scripts.pettripfinder.contracts import fee_computation as FC     # noqa: E402
from scripts.pettripfinder.contracts import policy_schema as SCHEMA   # noqa: E402
from scripts.pettripfinder.contracts.identity_key import ptf_identity_key  # noqa: E402
from scripts.pettripfinder import hotel_exclusions as HE              # noqa: E402
from scripts.pettripfinder import market_authority as MA              # noqa: E402
from scripts.pettripfinder.markets import contract as MC              # noqa: E402
from scripts.pettripfinder.site_data import normalize_name            # noqa: E402

WORK_ORDER = "PTF-NASHVILLE-TN-PROMOTION-AND-NEW-LANE-LAUNCH-PREP-002"
SHADOW_ORDER = "PTF-NASHVILLE-TN-NEW-MARKET-001"
MARKET_ID = "nashville-tn"
MARKET_NAME = "Greater Nashville, Tennessee"
STATE_CODE = "TN"
AS_OF = "2026-09-09"
FIRECRAWL_RUN_ID = "nashville_tn_firecrawl_001"

PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")

PROPOSED_CONTRACT = os.path.join(PKG, "markets", "proposed", "%s.json" % MARKET_ID)
PROPOSED_CENSUS = os.path.join(PKG, "identity_census_proposed", "%s.json" % MARKET_ID)
CONTRACT_PATH = os.path.join(PKG, "markets", "%s.json" % MARKET_ID)
CENSUS_PATH = os.path.join(PKG, "identity_census", "%s.json" % MARKET_ID)
HOLDS_PATH = os.path.join(PKG, "nashville_tn_identity_holds_002.json")
PARTITION_PATH = os.path.join(PKG, "nashville_tn_final_partition_001.json")
POLICY_PATH = os.path.join(PKG, "hotel_policy_facts_%s.json" % MARKET_ID)
LEDGER_PATH = os.path.join(PKG, "ptf_paid_attempt_ledger_001.json")

SHADOW_REPORT = os.path.join(REPORTS, "nashville_tn_shadow_market_001.json")
CLEAN_REPORT = os.path.join(REPORTS, "nashville_tn_clean_authority_001.json")
AUDIT_REPORT = os.path.join(REPORTS, "nashville_tn_evidence_audit_001.json")
ROUTING_REPORT = os.path.join(REPORTS, "nashville_tn_routing_001.json")
RECON_REPORT = os.path.join(REPORTS, "nashville_tn_census_reconciliation_001.json")
FIRECRAWL_REPORT = os.path.join(REPORTS, "nashville_tn_firecrawl_pass_001.json")

#: The shadow this order may not move. Read from the committed report, never
#: typed: a governing number that disagrees with its own source is not governing.
GOVERNING_SOURCE = SHADOW_REPORT

#: This order's authority to REGISTER the set. The founder work order directs
#: the conversion of the existing Nashville shadow into registered authority and
#: forbids inferring any new policy decision. It is NOT a claim that a named
#: human read each row, and no human name is written into any field.
REVIEWER_ID = "PTF-FOUNDER-001"
REVIEW_BASIS = (
    "Set-level founder authorisation to REGISTER, not to launch. Founder work order "
    + WORK_ORDER + " directs this order to convert Nashville's existing shadow work into a "
    "registered authority package, to preserve every Nashville semantic policy decision "
    "exactly, and to infer no new Nashville policy decision. The promotion set is the clean "
    "cohort " + SHADOW_ORDER + " committed -- 80 CLEAN_PET_FRIENDLY and 19 "
    "CLEAN_VERIFIED_NO_PETS -- carried across unchanged and then filtered ONLY by the modern "
    "production gates, each removal named. The agent did not attribute a per-row reading to the "
    "founder. Launch participation is a separate founder decision this order does not take.")

CENSUS_MEMBERSHIP_NOTE = (
    "PTF-GENERIC-CENSUS-MEMBERSHIP-HARDENING-001. This market's corridors are a postal-code "
    "partition: every admitted lodging ZIP is claimed by exactly one corridor, so "
    "census_membership_basis is CORRIDOR_REGISTRY and a discovered hotel is never placed by "
    "mailing city -- 'Nashville' is the mailing city of Antioch, Hermitage, Bellevue, Donelson, "
    "Green Hills and Old Hickory alike and decides nothing. ONE EXCEPTION, authored by "
    + SHADOW_ORDER + " and carried across unchanged: ZIP 37214 carries both the Donelson/BNA "
    "cluster and the Music Valley Drive / Opryland cluster, four miles apart and two different "
    "traveler markets. 37214 is claimed by airport-donelson for MEMBERSHIP; Opryland and "
    "Vanderbilt/West End claim their properties by explicit_hotel_ids, which is tier 2 in "
    "markets.assignment.assign_hotels and outranks the tier-3 ZIP match, so display stays true "
    "without making membership ambiguous.")

REGISTRATION_NOTE = (
    "Nashville's registered identity census, carried across from the shadow " + SHADOW_ORDER
    + " committed. Membership was decided by this market's committed corridor postal partition, "
    "not by a mailing city. Every one of the shadow's 181 confirmed identities is registered: "
    "the registered identity contract admits all of them, because the shadow already keyed on "
    "ptf_identity_key/1.0 and its 181 keys are distinct. Four fields the registered contract "
    "requires and the proposed file predates -- slug, market_id, identity_state, lodging_state "
    "-- are DERIVED here, and two rows that stated no city take it from their own first-party "
    "read. No row's address, corridor or policy was changed. Rows whose PUBLICATION the modern "
    "gates hold keep their census identity and are named in "
    "nashville_tn_identity_holds_002.json.")


class RegistrationError(RuntimeError):
    """Refuse to write a partial or unprovable package."""


def _load(path):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def _write(path, doc):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")


def _prefixed(digest):
    d = (digest or "").strip()
    if not d:
        return ""
    return d if d.startswith("sha256:") else "sha256:" + d


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", (text or "").strip().lower()).strip("-")


# --------------------------------------------------------------------------- #
# Facts. The shadow's reader decided these; this only reshapes them.
# --------------------------------------------------------------------------- #

_NIGHT_RANGE = re.compile(
    r"\$?\s*([\d,]+(?:\.\d{2})?)\s*\(?\s*(\d+)\s*(?:-|to|through)\s*(\d+)?\s*\+?\s*"
    r"(?:n|nights?)\s*\)?", re.I)
_NIGHT_PLUS = re.compile(r"\$?\s*([\d,]+(?:\.\d{2})?)\s*\(?\s*(\d+)\s*\+\s*(?:n|nights?)\s*\)?",
                         re.I)

_BASIS_WORDS = (
    (enums.BASIS_PER_NIGHT, r"per\s+night|/\s*night|nightly|per\s+room\s+per\s+night"),
    (enums.BASIS_PER_STAY, r"per\s+stay|/\s*stay|non-?refundable\s+fee\s+per\s+stay"),
    (enums.BASIS_PER_DAY, r"per\s+day|/\s*day|daily"),
)


def _stated_basis(quote):
    """The fee period the source actually states, or "" when it states none."""
    for basis, pattern in _BASIS_WORDS:
        if re.search(pattern, quote or "", re.I):
            return basis
    return ""


def fee_from(quote, headline_cents, refundable, stated_basis, stated_scope):
    """A per-night LADDER when the source states one, else a single fee.

    ``fee_tiers`` requires a real condition, because a tier exists to say WHEN a
    price applies. A flat fee has no condition and belongs in ``pet_fee``.
    ``basis`` and ``scope`` come from the reader's own extraction where it
    recorded one and from the quote otherwise; neither is asserted when the
    source states none.
    """
    tiers = []
    for m in _NIGHT_RANGE.finditer(quote or ""):
        amt = int(round(float(m.group(1).replace(",", "")) * 100))
        lo, hi = int(m.group(2)), m.group(3)
        t = OrderedDict([("amount_cents", amt), ("currency", "USD"),
                         ("role", enums.ROLE_REPLACEMENT_PRICE),
                         ("condition_type", enums.CONDITION_STAY_LENGTH_RANGE),
                         ("boundary_unit", enums.BOUNDARY_NIGHTS),
                         ("condition_min", lo)])
        if hi:
            t["condition_max"] = int(hi)
        t["scope"] = stated_scope or enums.SCOPE_PER_PET
        t["basis_stated"] = False
        tiers.append(t)
    for m in _NIGHT_PLUS.finditer(quote or ""):
        amt = int(round(float(m.group(1).replace(",", "")) * 100))
        lo = int(m.group(2))
        if any(t["amount_cents"] == amt and t["condition_min"] == lo for t in tiers):
            continue
        tiers.append(OrderedDict([("amount_cents", amt), ("currency", "USD"),
                                  ("role", enums.ROLE_REPLACEMENT_PRICE),
                                  ("condition_type", enums.CONDITION_STAY_LENGTH_RANGE),
                                  ("boundary_unit", enums.BOUNDARY_NIGHTS),
                                  ("condition_min", lo),
                                  ("scope", stated_scope or enums.SCOPE_PER_PET),
                                  ("basis_stated", False)]))
    tiers.sort(key=lambda t: (t["condition_min"], t["amount_cents"]))
    if len(tiers) >= 2:
        return "fee_tiers", tiers
    if headline_cents is None:
        return None, None
    fee = OrderedDict([("amount_cents", int(headline_cents)), ("currency", "USD"),
                       ("scope", stated_scope or enums.SCOPE_PER_PET)])
    basis = stated_basis or _stated_basis(quote)
    if basis:
        fee["basis"] = basis
    if refundable is not None:
        fee["refundable"] = bool(refundable)
    return "pet_fee", fee


def facts_from_read(row):
    """The published facts for one clean pet-friendly read.

    Withheld fields are honoured: the shadow's ``withheld_fields`` records a
    deliberate decision NOT to publish a term, and a blank must never read as a
    zero.
    """
    ext = dict(row.get("extraction") or {})
    withheld = {str(f) for f in (row.get("withheld_fields") or ())}
    quote = " ".join(str(e.get("quote") or "") for e in (row.get("evidence") or []))
    facts = OrderedDict()
    facts["pets_allowed"] = ext["pets_allowed"]

    species = ext.get("species_allowed")
    if species and "species_allowed" not in withheld:
        pairs = []
        if "dog" in species:
            pairs.append(("dogs", "accepted"))
        if "cat" in species:
            pairs.append(("cats", "accepted"))
        if pairs:
            facts["species"] = OrderedDict(pairs)

    wl = ext.get("weight_limit")
    if wl is not None and "weight_limit" not in withheld:
        if isinstance(wl, dict):
            value, unit = wl.get("value"), wl.get("unit")
        else:
            value, unit = wl, ext.get("weight_limit_unit")
        if value is None:
            raise RegistrationError("%s: a weight limit with no value" % row["canonical_name"])
        facts["weight_limit"] = OrderedDict([
            ("value", float(value)), ("unit", unit or "lb"),
            ("operator", ext.get("weight_limit_operator") or "lte"),
            ("scope", ext.get("weight_limit_scope") or "per_pet")])

    fee = ext.get("pet_fee")
    if fee is not None and "pet_fee" not in withheld:
        field, value = fee_from(quote, fee, ext.get("fee_refundable"),
                                ext.get("fee_basis"), ext.get("fee_scope"))
        if field:
            facts[field] = value

    if ext.get("pet_count_limit") is not None and "pet_count_limit" not in withheld:
        facts["pet_count_limit"] = ext["pet_count_limit"]

    return facts


def service_animal_statement(row):
    """The record-level service-animal statement, or None.

    It is NOT a fact: policy_schema flags ``facts.service_animal_exception`` as
    a MISPLACED_FIELD by name, because a legal access category must not sit in
    the commercial-terms namespace. It is STRUCTURED -- a bare quote string
    crashes the renderer -- and ``charges_stated`` reports whether the property
    addressed a charge at all rather than inferring one from silence.
    """
    ext = row.get("extraction") or {}
    sa = ext.get("service_animal_statement")
    quote = ""
    if isinstance(sa, dict):
        quote = str(sa.get("quote") or "")
    elif sa:
        quote = str(sa)
    if not quote.strip():
        return None
    low = quote.lower()
    if re.search(r"exempt|no (additional |extra )?(charge|fee)|free of charge|without charge",
                 low):
        charges = "no_charge"
    elif re.search(r"[$]|fee|charge", low):
        charges = "charge_stated"
    else:
        charges = "not_addressed"
    return OrderedDict([("stated", True), ("charges_stated", charges),
                        ("quote", quote.strip()[:400])])


#: A PUBLISHED field name and the READER field names whose quotes support it.
_PUBLISHED_FROM_READER = {
    "fee_tiers": {"pet_fee", "fee_currency", "fee_refundable", "fee_basis", "fee_cap",
                  "fee_scope"},
    "pet_fee": {"pet_fee", "fee_currency", "fee_refundable", "fee_basis", "fee_cap",
                "fee_scope"},
    "species": {"species_allowed", "species"},
    "weight_limit": {"weight_limit", "weight_limit_unit", "weight_limit_operator",
                     "weight_limit_scope"},
    "pet_count_limit": {"pet_count_limit", "pet_count_scope"},
    "pets_allowed": {"pets_allowed"},
    "service_animal_statement": {"service_animal_statement", "service_animal_exception"},
}

_LANE_CAPTURE = {"ATTENDED_BROWSER": "attended_browser",
                 "FIRECRAWL": "firecrawl_rendered_fetch",
                 "DIRECT_STATIC": "direct_http"}
_LANE_GRADE = {"ATTENDED_BROWSER": "PT2_BRAND",
               "FIRECRAWL": "PT2_BRAND",
               "DIRECT_STATIC": "PT1_FIRST_PARTY"}


def _published_field_for(reader_field, facts):
    candidates = [pub for pub, readers in _PUBLISHED_FROM_READER.items()
                  if reader_field in readers]
    for pub in candidates:
        if pub in facts:
            return pub
    return candidates[0] if candidates else reader_field


def evidence_rows(key, row, facts):
    """One evidence row per published field, carrying the quote and the artifact.

    ``artifact_sha256`` is the hash the LANE recorded for the document, or the
    empty string when the lane recorded none. It is never manufactured from the
    URL and the quote: such a value can be computed without ever fetching the
    page, so it would satisfy the capture-hash check by fabricating exactly the
    thing that check exists to demand. A row with no document hash is refused by
    ``first_party_binding`` and held by this module.
    """
    out, seen = [], set()
    digest = _prefixed(row.get("document_sha256"))
    for e in row.get("evidence") or []:
        quote = str(e.get("quote") or "").strip()
        if not quote:
            continue
        for reader_field in (e.get("field_refs") or []):
            field = _published_field_for(reader_field, facts)
            marker = (field, quote)
            if field not in facts or marker in seen:
                continue
            seen.add(marker)
            value = facts[field]
            out.append(OrderedDict([
                ("field", field), ("quote", quote[:400]),
                ("source_url", row["source_url"]),
                ("value", json.dumps(value, sort_keys=True)
                 if isinstance(value, (dict, list))
                 else str(value).lower() if isinstance(value, bool) else str(value)),
                ("evidence_ref", "ev:" + hashlib.sha256(
                    (key + field + quote).encode("utf-8")).hexdigest()[:16]),
                ("artifact_class", "PUBLICATION_GRADE_EVIDENCE"),
                ("artifact_sha256", digest),
                ("artifact_kind", "rendered_html"),
                ("captured_at", row.get("captured_at") or ""),
                ("capture_method", _LANE_CAPTURE[row["lane"]]),
                ("source_grade", _LANE_GRADE[row["lane"]]),
            ]))
    for field in facts:
        if not any(r["field"] == field for r in out):
            raise RegistrationError("%s: published field %r carries no quote"
                                    % (row["canonical_name"], field))
    return out


# --------------------------------------------------------------------------- #
# Reading the shadow.
# --------------------------------------------------------------------------- #

def admitted_municipalities():
    """The municipalities this market's committed discovery configuration admits."""
    path = os.path.join(_DASH, "scripts", "pettripfinder", "discovery", "config",
                        "nashville_tn.json")
    return [str(m) for m in (_load(path).get("included_municipalities") or ())]


def _stated_city(row, clean, municipalities):
    """The city a row's OWN first-party evidence states, with the basis.

    This applies the SHADOW's own committed backfill rule (see
    ``nashville_tn_census_reconciliation_001.json``'s ``city_backfill``) rather
    than a new one: the property's own page, then the city segment of the
    property's own canonical URL -- and never the brand's marketing name, which
    in this market calls almost every hotel in Antioch, Hermitage, Bellevue,
    Donelson, Green Hills and Old Hickory 'Nashville'.

    The URL segment is accepted only when it names a municipality this market
    ADMITS. WoodSpring files the Hermitage property under
    ``/locations/tennessee/chattanooga/``, 130 miles away and flatly contradicted
    by the 37076 the same page states; reading a city off that segment would
    publish a geography no source asserts.
    """
    if clean:
        sig = clean.get("identity_signals") or {}
        for field in ("locality", "city_on_page", "city"):
            value = str(sig.get(field) or "").strip()
            if value:
                return value, "the locality stated by the property's own page"
    url = str(row.get("official_url") or "")
    segments = [s for s in url.split("/") if s]
    lowered = {m.lower(): m for m in municipalities}
    for segment in segments:
        match = lowered.get(segment.replace("-", " ").lower())
        if match:
            return match, ("the city segment of the property's own canonical URL, which names a "
                           "municipality this market admits")
    return "", ""


def read_source():
    """The proposed census, repaired to the registered contract, joined to the
    clean cohort by the census's own identity keys and aliases."""
    census_doc = _load(PROPOSED_CENSUS)
    clean_doc = _load(CLEAN_REPORT)

    by_key = {}
    for row in census_doc["hotels"]:
        by_key[row["identity_key"]] = row
        for alias in row.get("identity_key_aliases") or []:
            by_key.setdefault(alias, row)

    clean_of = {}
    for policy_class, rows in (("CLEAN_PET_FRIENDLY", clean_doc["clean_pet_friendly"]),
                               ("CLEAN_VERIFIED_NO_PETS", clean_doc["clean_verified_no_pets"])):
        for row in rows:
            target = by_key.get(row["identity_key"])
            if target is None:
                raise RegistrationError(
                    "clean row %r resolves to no registered census identity"
                    % row["identity_key"])
            key = target["identity_key"]
            if key in clean_of:
                raise RegistrationError(
                    "two clean reads resolve to one census identity %r (%r and %r)"
                    % (key, clean_of[key][1]["identity_key"], row["identity_key"]))
            clean_of[key] = (policy_class, row)

    municipalities = admitted_municipalities()
    identities, migration_holds = [], []
    for row in census_doc["hotels"]:
        key = row["identity_key"]
        name = row["canonical_name"]
        derived = ptf_identity_key(name)
        if derived != key or normalize_name(name) != key:
            raise RegistrationError(
                "%r does not round-trip: normalize_name %r, identity key %r, stored %r"
                % (name, normalize_name(name), derived, key))
        clean = clean_of.get(key)
        city = str(row.get("city") or "").strip()
        city_basis = "stated by the discovery source"
        if not city:
            city, city_basis = _stated_city(row, clean[1] if clean else None, municipalities)
        if not city:
            # The registered census contract requires a city on every row, and
            # no committed source states one for this identity that survives its
            # own contradiction. It is held OUT of the registration rather than
            # given a city this repository would then treat as evidence.
            migration_holds.append(OrderedDict([
                ("identity_key_proposed", key),
                ("canonical_name", name),
                ("address", str(row.get("street") or "")),
                ("corridor", row["corridor"]),
                ("classification", "CONTRACT_MIGRATION_ERROR"),
                ("gate_classification", "CITY_NOT_STATED_BY_ANY_COMMITTED_SOURCE"),
                ("capture_lane", (clean[1]["lane"] if clean else "")),
                ("why", "the registered census contract requires a city on every row and no "
                        "committed Nashville source states one for this identity. The shadow's "
                        "own city backfill left it blank on purpose: no other admitted row shares "
                        "its postal code %r, and the city segment of its canonical URL names "
                        "Chattanooga, 130 miles away and contradicted by the postal code the "
                        "same page states. A brand's marketing name is never read as a city in "
                        "this market. Registering it would require inventing a geography."
                        % str(row.get("postal_code") or "")),
                ("published_anything", False),
                ("shadow_policy_class", clean[0] if clean else "UNRESOLVED"),
                ("reversible_without_recapture", True),
                ("next_action", "a founder ruling naming this property's mailing city, after "
                                "which the row registers with no new capture and no new policy "
                                "decision"),
            ]))
            continue
        ident = OrderedDict([
            ("identity_key", key),
            ("canonical_name", name),
            ("slug", slugify(name)),
            ("market_id", MARKET_ID),
            ("street", str(row.get("street") or "")),
            ("city", city), ("city_basis", city_basis),
            ("state", str(row.get("state") or STATE_CODE)),
            ("postal_code", str(row.get("postal_code") or "")),
            ("phone", str(row.get("phone") or "")),
            ("brand", str(row.get("brand") or "")),
            ("property_code", str(row.get("property_code") or "")),
            ("latitude", row.get("latitude")), ("longitude", row.get("longitude")),
            ("corridor", row["corridor"]),
            ("assignment_basis", row.get("assignment_basis") or enums.BASIS_EXPLICIT),
            ("assignment_value", row.get("assignment_value") or key),
            ("best_tier", row.get("best_tier")),
            ("identity_state", "IDENTITY_CONFIRMED"),
            ("lodging_state", "LODGING_CONFIRMED"),
            ("collision_state", enums.COLLISION_NONE),
            ("classification", row.get("classification") or "TRUE_HOTEL_IDENTITY"),
            ("classification_reason", row.get("classification_reason") or ""),
            ("identity_key_aliases", list(row.get("identity_key_aliases") or ())),
            ("official_url", str(row.get("official_url") or "")),
            ("street_identity", str(row.get("street_identity") or "")),
            ("phone_key", str(row.get("phone_key") or "")),
            ("lanes", list(row.get("lanes") or ())),
        ])
        ident["_clean"] = clean
        ident["_hold"] = None
        identities.append(ident)

    identities.sort(key=lambda i: i["identity_key"])
    migration_holds.sort(key=lambda h: h["identity_key_proposed"])
    return identities, migration_holds, census_doc, clean_doc


def published_keys_of_other_markets():
    """``identity key -> (state, market_id)`` for every OTHER market's published
    and refused rows, read from the committed authority rather than assumed."""
    import glob
    owned = {}
    for path in sorted(glob.glob(os.path.join(PKG, "hotel_policy_facts_*.json"))):
        doc = _load(path)
        if doc.get("market_id") == MARKET_ID:
            continue
        for row in doc.get("hotels") or []:
            key = row.get("key") or row.get("identity_key")
            if key:
                owned.setdefault(key, ("PUBLISHED_PET_FRIENDLY", doc.get("market_id")))
    for path in sorted(glob.glob(os.path.join(PKG, "markets", "authority", "*",
                                              "hotel_exclusions.json"))):
        doc = _load(path)
        if doc.get("market_id") == MARKET_ID:
            continue
        for row in doc.get("exclusions") or []:
            key = row.get("normalized_name")
            if key:
                owned.setdefault(key, ("VERIFIED_NO_PETS", doc.get("market_id")))
    return owned


def cross_market_holds(identities):
    """Rows whose REGISTERED key another market already publishes.

    A published identity key is globally unique in this repository and
    ``hotel_exclusions.validate`` refuses a second row by name, so a Nashville
    row that lands on a key another market publishes is held HERE, at its cause,
    rather than surfacing as an assembler crash. It is not renamed: the name is
    the property's own.
    """
    owned = published_keys_of_other_markets()
    out = []
    for ident in identities:
        holder = owned.get(ident["identity_key"])
        if not holder:
            continue
        clean = ident["_clean"]
        record = OrderedDict([
            ("identity_key_proposed", ident["identity_key"]),
            ("canonical_name", ident["canonical_name"]),
            ("address", ident["street"]),
            ("corridor", ident["corridor"]),
            ("classification", "CROSS_MARKET_COLLISION"),
            ("gate_classification", "GLOBAL_PUBLISHED_IDENTITY_KEY_ALREADY_OWNED"),
            ("why", "%s already publishes the identity key %r as %s. A published identity key is "
                    "globally unique in this repository, so this Nashville row may never reach "
                    "the published set under this name. It was ALREADY unresolved in the "
                    "shadow -- it carries no clean first-party read -- so nothing is lost by "
                    "holding it, and holding it now stops a later order from publishing it into "
                    "an assembler failure."
                    % (holder[1], ident["identity_key"], holder[0])),
            ("published_anything", False),
            ("shadow_policy_class", clean[0] if clean else "UNRESOLVED"),
            ("colliding_market", holder[1]),
            ("colliding_state", holder[0]),
            ("reversible_without_recapture", True),
            ("next_action", "a founder ruling on a distinguishing canonical name that ADDS "
                            "geography for one of the two rows, or a contract change that scopes "
                            "the published identity key by market"),
        ])
        out.append(record)
    out.sort(key=lambda h: h["identity_key_proposed"])
    return out


# --------------------------------------------------------------------------- #
# The registered documents.
# --------------------------------------------------------------------------- #

def build_market_contract(identities):
    """The proposed contract, registered. Corridor membership is the shadow's
    own postal partition and explicit lists, carried across untouched."""
    proposed = _load(PROPOSED_CONTRACT)
    declared = {c["corridor_id"] for c in proposed["corridors"]}
    for ident in identities:
        if ident["corridor"] not in declared:
            raise RegistrationError("census row %r claims corridor %r, which this market does "
                                    "not declare" % (ident["identity_key"], ident["corridor"]))

    doc = OrderedDict()
    for field, value in proposed.items():
        if field == "_registration_note":
            continue
        doc[field] = value
    doc["_census_membership_note"] = CENSUS_MEMBERSHIP_NOTE
    doc["registered_by"] = WORK_ORDER
    doc["registered_at"] = AS_OF
    doc["authored_by"] = SHADOW_ORDER
    MC.parse_market(doc, source=CONTRACT_PATH)
    return doc


def build_census(identities, holds, proposed):
    held_by_key = {h["identity_key_proposed"]: h for h in holds}
    hotels = []
    for ident in identities:
        clean = ident["_clean"]
        if clean is None:
            policy_state = "POLICY_NOT_VERIFIED"
            policy_note = "Identity evidence never establishes a pet policy."
        elif ident["_hold"] is not None:
            policy_state = "POLICY_NOT_VERIFIED"
            policy_note = ("A first-party read exists and is preserved verbatim in "
                           "nashville_tn_clean_authority_001.json; its PUBLICATION is held by "
                           "%s." % held_by_key[ident["identity_key"]]["classification"])
        elif clean[0] == "CLEAN_PET_FRIENDLY":
            policy_state = "POLICY_CONFIRMED"
            policy_note = "First-party acceptance read on the property's own page."
        else:
            policy_state = "VERIFIED_NO_PETS"
            policy_note = "First-party refusal read on the property's own page."
        row = OrderedDict((k, v) for k, v in ident.items() if not k.startswith("_"))
        row["policy_state"] = policy_state
        row["policy_note"] = policy_note
        hold = held_by_key.get(ident["identity_key"])
        if hold is not None:
            row["publication_hold_class"] = hold["classification"]
            row["publication_hold_reason"] = hold["gate_classification"]
        hotels.append(row)

    doc = OrderedDict([
        ("schema", enums.CENSUS_SCHEMA),
        ("market_id", MARKET_ID),
        ("status", "REGISTERED"),
        ("identity_key_contract", "ptf_identity_key/1.0"),
        ("identity_contract", "ptf-identity-evidence/1.0"),
        ("work_order", WORK_ORDER),
        ("captured_at", AS_OF),
        ("note", REGISTRATION_NOTE),
        ("source_authorities", list(proposed.get("source_authorities") or ())),
        ("count", len(hotels)),
        ("shadow_confirmed_identities", proposed["count"]),
        ("held_from_shadow", 0),
        ("publication_holds", len(holds)),
        ("total_candidates", proposed.get("total_candidates")),
        ("classification_counts",
         OrderedDict(sorted(Counter(h["classification"] for h in hotels).items()))),
        ("corridor_counts",
         OrderedDict(sorted(Counter(h["corridor"] for h in hotels).items()))),
        ("hotels", hotels),
        ("non_admitted", list(proposed.get("non_admitted") or ())),
    ])
    issues = CENSUS.validate(doc, market_states=[STATE_CODE])
    if issues:
        raise RegistrationError("census fails its contract: %s"
                                % [(i.path, i.code, i.detail) for i in issues][:10])
    return doc


def build_policy_package(publishing):
    hotels = []
    for ident in publishing:
        clean = ident["_clean"]
        if clean is None or clean[0] != "CLEAN_PET_FRIENDLY":
            continue
        row = clean[1]
        key = ident["identity_key"]
        facts = facts_from_read(row)
        if facts.get("pets_allowed") is not True:
            raise RegistrationError("%s: a CLEAN_PET_FRIENDLY row whose read does not say yes"
                                    % ident["canonical_name"])
        rec = OrderedDict([
            ("key", key), ("identity_key", key), ("name", ident["canonical_name"]),
            ("market_id", MARKET_ID), ("schema_version", enums.POLICY_SCHEMA_VERSION),
            ("facts", facts),
        ])
        sa = service_animal_statement(row)
        if sa:
            rec["service_animal_statement"] = sa
        # The contract's OWN classifier decides this; never a literal.
        rec["computation_class"] = FC.classify(facts).computation_class
        rec["evidence"] = evidence_rows(key, row, facts)
        rec["source_url"] = row["source_url"]
        rec["corridor"] = ident["corridor"]
        rec["verified_at"] = row.get("captured_at") or ""
        rec["capture_lane"] = row["lane"]
        rec["withheld_facts"] = OrderedDict(
            (str(f), "withheld by %s" % SHADOW_ORDER) for f in (row.get("withheld_fields") or ()))
        rec["reviewer_id"] = REVIEWER_ID
        rec["reviewed_at"] = AS_OF
        rec["review_basis"] = REVIEW_BASIS
        rec["work_order"] = WORK_ORDER
        hotels.append(rec)
    hotels.sort(key=lambda h: h["key"])
    for h in hotels:
        issues = SCHEMA.validate_record(h)
        if issues:
            raise RegistrationError("%s fails the record contract: %s"
                                    % (h["name"], [(i.path, i.code) for i in issues]))
    keys = [h["key"] for h in hotels]
    if len(keys) != len(set(keys)):
        raise RegistrationError("two clean reads resolved to one published identity: %s"
                                % sorted(k for k, n in Counter(keys).items() if n > 1))
    doc = OrderedDict([
        ("market", MARKET_NAME), ("schema_version", "1.3"), ("market_id", MARKET_ID),
        ("work_order", WORK_ORDER), ("as_of", AS_OF),
        ("note", "Nashville's published pet-friendly authority. Every fact was decided by the "
                 "reader " + SHADOW_ORDER + " ran against a first-party page, carries the quote "
                 "that supports it, and names the lane and the document hash it came from. "
                 "withheld_facts carries that order's deliberate decisions forward so a blank "
                 "can never read as a zero."),
        ("hotels", hotels),
    ])
    issues = SCHEMA.validate_package(doc)
    if issues:
        raise RegistrationError("policy package fails its contract: %s"
                                % [(i.path, i.code) for i in issues][:10])
    return doc


def build_exclusions(publishing):
    records = []
    for ident in publishing:
        clean = ident["_clean"]
        if clean is None or clean[0] != "CLEAN_VERIFIED_NO_PETS":
            continue
        row = clean[1]
        quote = next((str(e.get("quote") or "").strip()
                      for e in (row.get("evidence") or [])
                      if "pets_allowed" in (e.get("field_refs") or [])
                      and str(e.get("quote") or "").strip()), "")
        if not quote:
            raise RegistrationError("%s: a VERIFIED_NO_PETS row with no refusal quote"
                                    % ident["canonical_name"])
        if (row.get("extraction") or {}).get("pets_allowed") is not False:
            raise RegistrationError("%s: a VERIFIED_NO_PETS row whose read does not say no"
                                    % ident["canonical_name"])
        rec = OrderedDict([
            ("market_id", MARKET_ID),
            ("exclusion_id", "nsh-" + slugify(ident["canonical_name"])),
            ("canonical_name", ident["canonical_name"]),
            ("normalized_name", ident["identity_key"]),
            ("address", ident["street"]), ("city", ident["city"]),
            ("state", STATE_CODE), ("postal_code", ident["postal_code"]),
            ("official_url", row["source_url"]),
            ("exclusion_state", HE.VERIFIED_NO_PETS),
            ("evidence_quote", quote),
            ("source_url", row["source_url"]),
            ("observed_at", (row.get("captured_at") or AS_OF)[:10]),
            ("source_hash", _prefixed(row.get("document_sha256"))),
        ])
        # The lane is declared on the record, so rule O SEES a paid refusal.
        # Without it the package writer labels the reference "recorded" and a
        # verified-no-pets row bought through a paid lane escapes the paid
        # provenance rule entirely -- which is how this was found.
        rec["capture_method"] = _LANE_CAPTURE[row["lane"]]
        rec["source_grade"] = _LANE_GRADE[row["lane"]]
        rec["record_hash"] = HE.record_hash(rec)
        rec["reviewer_id"] = REVIEWER_ID
        rec["reviewed_at"] = AS_OF
        rec["approval_hash"] = HE.approval_hash(rec)
        rec["review_basis"] = REVIEW_BASIS
        rec["notes"] = (
            "%s. First-party refusal read on the property's own page by the %s lane and carried "
            "across from %s unchanged. Service-animal access is a legal category and never "
            "converts a refusal into acceptance." % (WORK_ORDER, row["lane"], SHADOW_ORDER))
        records.append(rec)
    records.sort(key=lambda r: r["exclusion_id"])
    names = [r["normalized_name"] for r in records]
    if len(names) != len(set(names)):
        raise RegistrationError("two refusals resolved to one identity: %s"
                                % sorted(k for k, n in Counter(names).items() if n > 1))
    doc = OrderedDict([
        ("schema", HE.SCHEMA), ("contract", HE.SCHEMA), ("market_id", MARKET_ID),
        ("note", "This market's slice of the hotel-exclusions authority. The global "
                 "launch_packages/pettripfinder/hotel_exclusions.json is generated from every "
                 "market's shard and must not be hand-edited."),
        ("work_order", WORK_ORDER), ("count", len(records)), ("exclusions", records),
    ])
    HE.validate(doc)
    return doc


def build_seed_rows(policy, by_key, routes_by_key):
    rows = []
    for h in policy["hotels"]:
        ident = by_key[h["key"]]
        missing = [f for f, v in (("address", ident["street"]), ("city", ident["city"]),
                                  ("postal_code", ident["postal_code"]))
                   if not v]
        if missing:
            raise RegistrationError("%s: a published row states no %s, and nothing here invents "
                                    "one" % (h["name"], ", ".join(missing)))
        quote = " ".join(e["quote"] for e in h["evidence"][:4])
        rows.append(OrderedDict([
            ("name", h["name"]), ("category", "pet-friendly-hotels"),
            ("address", ident["street"]), ("city", ident["city"]), ("state", STATE_CODE),
            ("postal_code", ident["postal_code"]), ("phone", ident["phone"]),
            ("website_url", routes_by_key.get(h["key"]) or ident["official_url"]
             or h["source_url"]),
            ("source_url", h["source_url"]), ("source_type", "OFFICIAL_PROPERTY"),
            ("observed_at", str(h["verified_at"])[:10]), ("rating", ""), ("amenities", ""),
            ("pet_policy", quote[:600]), ("canonical", ""), ("market_id", MARKET_ID),
        ]))
    rows.sort(key=lambda r: r["name"].lower())
    return rows


def build_partition(identities, routes_by_key, held_reads):
    items = []
    for ident in identities:
        clean, hold = ident["_clean"], ident["_hold"]
        key = ident["identity_key"]
        if hold is not None:
            state, resolved = "AWAITING_POLICY_ARTIFACT", False
            action = hold["next_action"]
            source = "%s (%s)" % (hold["classification"], hold["gate_classification"])
        elif clean is not None and clean[0] == "CLEAN_PET_FRIENDLY":
            state, resolved, action, source = "PUBLISHED_PET_FRIENDLY", True, "", ""
        elif clean is not None and clean[0] == "CLEAN_VERIFIED_NO_PETS":
            state, resolved, action, source = "VERIFIED_NO_PETS", True, "", ""
        elif key in held_reads:
            state, resolved = "AWAITING_FOUNDER_DECISION", False
            action = ("A first-party read exists but the shadow's wrong-evidence audit held it: "
                      "this building's identity is not settled.")
            source = "nashville_tn_evidence_audit_001.json held reads"
        elif not routes_by_key.get(key):
            state, resolved = "AWAITING_ROUTING_REVIEW", False
            action = "No free lane stated an official route for this identity."
            source = "nashville_tn_routing_001.json routing_state"
        else:
            state, resolved = "AWAITING_POLICY_OBSERVATION", False
            action = ("Routed but not yet read. The brand walls the shadow could not pass free "
                      "are named in nashville_tn_paid_readiness_001.json.")
            source = "nashville_tn_paid_readiness_001.json"
        items.append(OrderedDict([
            ("identity_key", key), ("canonical_name", ident["canonical_name"]),
            ("slug", ident["slug"]),
            ("city", ident["city"]), ("state", STATE_CODE),
            ("postal_code", ident["postal_code"]),
            ("corridor", ident["corridor"]),
            ("final_state", state), ("resolved", resolved), ("next_action", action),
            ("next_action_source", source),
            ("determined_by", WORK_ORDER), ("updated_at", AS_OF),
            ("official_url", routes_by_key.get(key) or ident["official_url"] or ""),
            ("state_override_reason", ""),
        ]))
    items.sort(key=lambda i: i["identity_key"])
    counts = Counter(i["final_state"] for i in items)
    return OrderedDict([
        ("schema", "ptf-market-final-partition/1.1"), ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID), ("as_of", AS_OF),
        ("note", "Every registered census identity appears exactly once. Resolved means the "
                 "market owes nothing further on the row: it is published, refused, or out of "
                 "category."),
        ("count", len(items)),
        ("final_state_counts", OrderedDict(sorted(counts.items()))),
        ("items", items),
    ])


def build_holds(holds):
    return OrderedDict([
        ("schema", "ptf-market-identity-holds/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET_ID), ("as_of", AS_OF),
        ("note", "Nashville rows whose PUBLICATION the modern production gates hold. Nothing "
                 "here was researched by this order, nothing here publishes, and every held row "
                 "keeps its registered census identity: what is held is the publication, not the "
                 "property. No gate was lowered to preserve a count."),
        ("count", len(holds)),
        ("counts_by_class",
         OrderedDict(sorted(Counter(h["classification"] for h in holds).items()))),
        ("counts_by_gate_classification",
         OrderedDict(sorted(Counter(h["gate_classification"] for h in holds).items()))),
        ("reversible_without_recapture",
         sum(1 for h in holds if h.get("reversible_without_recapture"))),
        ("holds", holds),
    ])


# --------------------------------------------------------------------------- #
# The modern gates.
# --------------------------------------------------------------------------- #

def firecrawl_reservations():
    """``artifact sha -> reservation`` DERIVED from the committed Firecrawl run.

    Rule O wants the reservation a paid fetch was made under: the provider, the
    run, an attempt id that re-derives, and the hash of the REQUEST ENVELOPE.
    Nashville's committed Firecrawl report carries the request envelope for
    every row it attempted -- the endpoint and the exact body -- so the envelope
    hash is DERIVED from stored run data rather than invented. This is the one
    thing Lexington could not do, and it is the difference between a provenance
    record and a fabrication.
    """
    from scripts.pettripfinder.acquisition.paid_attempt_ledger import attempt_id
    from scripts.pettripfinder import sealed_market_package as SMP

    doc = _load(FIRECRAWL_REPORT)
    run_id = str(doc.get("run_id") or FIRECRAWL_RUN_ID)
    out = {}
    for row in doc.get("rows") or ():
        digest = _prefixed(row.get("page_sha256"))
        envelope = row.get("request_envelope")
        if not digest or not isinstance(envelope, dict):
            continue
        out[digest] = OrderedDict([
            ("provider", "Firecrawl"), ("lane", "firecrawl"), ("run_id", run_id),
            ("attempt_id", None),  # filled per identity by _bind_reservations
            ("request_envelope_sha256",
             SMP.sha256_text(SMP.canonical_json(envelope))),
        ])
        out[digest]["_shadow_identity_key"] = str(row.get("identity_key") or "")
    return run_id, out


def bind_reservations(identities, reservations, run_id):
    """The reservation for each PUBLISHED identity, keyed by artifact digest.

    ``attempt_id`` is derived with the REGISTERED identity key, because that is
    the key rule O re-derives with -- the reference carries the census identity,
    not the short name the lane captured under.
    """
    from scripts.pettripfinder.acquisition.paid_attempt_ledger import attempt_id
    bound = {}
    for ident in identities:
        clean = ident["_clean"]
        if clean is None:
            continue
        digest = _prefixed(clean[1].get("document_sha256"))
        reservation = reservations.get(digest)
        if not reservation:
            continue
        record = OrderedDict((k, v) for k, v in reservation.items()
                             if not k.startswith("_"))
        record["attempt_id"] = attempt_id(MARKET_ID, run_id, ident["identity_key"], "firecrawl")
        bound[digest] = record
    return bound


def capture_hash_holds(identities):
    """Clean rows whose LANE recorded no document hash.

    ``first_party_binding`` refuses these on CAPTURE_HASH -- both
    ``evaluate_policy_record`` and ``evaluate_exclusion_record`` require
    ``SMP.is_sha256`` of the artifact digest -- and the exclusions contract will
    not even serialize a record without ``source_hash``, so the hold has to be
    taken before the shards are built rather than after.

    For the pet-friendly half the refusal is not asserted, it is DEMONSTRATED:
    the record is built and handed to the gate, and its verdict is recorded on
    the hold.

    Nashville's attended browser lane read 154 pages for $0 and recorded
    ``document_bytes`` for each, but no ``document_sha256``, and the acquisition
    directory it named is gitignored and empty. No hash can be derived from
    anything committed, and hashing the URL and the quote instead -- which
    ``toledo_oh_promotion_application_002`` falls back to -- would produce a
    value computable without ever fetching the page. That is not a capture hash.
    """
    from scripts.pettripfinder import first_party_binding as FPB
    from scripts.pettripfinder import sealed_market_package as SMP

    out = []
    for ident in identities:
        clean = ident["_clean"]
        if clean is None or ident["_hold"] is not None:
            continue
        policy_class, row = clean
        digest = SMP.normalise_sha256(_prefixed(row.get("document_sha256")))
        stamped = FPB.parse_timestamp(str(row.get("captured_at") or "")) is not None
        if SMP.is_sha256(digest) and stamped:
            continue
        if not SMP.is_sha256(digest):
            gate_class, missing = "NO_CAPTURE_HASH", "document hash"
            why = ("the lane that read this page recorded no document hash. The modern "
                   "first-party evidence gate refuses a published fact whose captured document "
                   "cannot be identified, and nothing committed by %s can supply one: the "
                   "attended lane stored a byte LENGTH, and the acquisition directory it named "
                   "is gitignored and empty. The read itself is not disputed and is preserved "
                   "verbatim in nashville_tn_clean_authority_001.json; what is refused is "
                   "publishing a fact this repository cannot tie to a document." % SHADOW_ORDER)
            remedy = ("re-read this page on the same lane at $0 and hash the document in the "
                      "SAME call that takes the quote. That is a RE-CAPTURE, which this order "
                      "is forbidden to perform.")
        else:
            gate_class, missing = "NO_TIMESTAMP", "capture timestamp"
            why = ("the lane that read this page recorded no capture timestamp. The evidence "
                   "contract makes captured_at mandatory on publication-grade evidence and the "
                   "fast lane's freshness rule has nothing to measure without it, so the row "
                   "cannot be published even though its document IS hashed. The read is "
                   "preserved verbatim and is not disputed.")
            remedy = ("re-read this page on the same free static lane at $0, recording the "
                      "capture timestamp. That is a RE-CAPTURE, which this order is forbidden "
                      "to perform.")
        confirmed = "the %s predicate both gate evaluators apply" % gate_class
        if policy_class == "CLEAN_PET_FRIENDLY":
            facts = facts_from_read(row)
            record = OrderedDict([
                ("key", ident["identity_key"]), ("identity_key", ident["identity_key"]),
                ("name", ident["canonical_name"]),
                ("facts", facts), ("reviewer_id", REVIEWER_ID),
                ("evidence", evidence_rows(ident["identity_key"], row, facts)),
            ])
            verdict = FPB.evaluate_policy_record(record, ident, {})
            confirmed = ("first_party_binding.evaluate_policy_record: %s on %s"
                         % (verdict["classification"], verdict["failed_checks"]))
        out.append(OrderedDict([
            ("identity_key_proposed", ident["identity_key"]),
            ("canonical_name", ident["canonical_name"]),
            ("address", ident["street"]), ("corridor", ident["corridor"]),
            ("classification", "MODERN_EVIDENCE_GATE_HOLD"),
            ("gate_classification", gate_class),
            ("capture_lane", row["lane"]),
            ("gate_confirmed_by", confirmed),
            ("why", why),
            ("missing", missing),
            ("published_anything", False),
            ("shadow_policy_class", policy_class),
            ("reversible_without_recapture", False),
            ("next_action", remedy),
        ]))
    out.sort(key=lambda h: h["identity_key_proposed"])
    return out


def gate_package(contract, census, policy, exclusions, seed_rows, partition, reservations):
    """Build the sealed-package shape the gates read, over the records this
    module is about to write."""
    from scripts.pettripfinder import market_package_writer as W
    from scripts.pettripfinder import sealed_market_package as SMP

    def digest(doc):
        return SMP.sha256_text(SMP.canonical_json(doc))

    inputs = W.PackageInputs(
        market_id=MARKET_ID,
        execution_zone=SMP.ZONE_REGISTERED_LIVE,
        created_from_source_sha="0" * 7,
        market=contract, census=census,
        pet_friendly_records=list(policy["hotels"]),
        verified_no_pets_records=list(exclusions["exclusions"]),
        official_routes=[], seed_rows=list(seed_rows), partition=partition,
        paid_reservations=reservations,
        intended_delta=OrderedDict((
            ("market_id", MARKET_ID), ("add_property_ids", []), ("update_property_ids", []),
            ("remove_property_ids", []), ("add_routes", []), ("change_routes", []),
            ("remove_routes", []), ("expected_profile_delta", 0),
            ("expected_market_count_delta", 0), ("expected_participation_delta", []))),
        parent_live_state=OrderedDict((("live_deploy_id", "gate-only"),
                                       ("rollback_target", ""), ("source_commit", ""),
                                       ("participating_markets", []), ("profile_counts", {}),
                                       ("total_profiles", 0), ("sitemap_route_count", 0),
                                       ("live_index_digest", "sha256:" + "0" * 64))),
        dependency_input_digests=OrderedDict((
            ("market", digest(contract)), ("census", digest(census)),
            ("policy_package", digest(policy)), ("exclusions", digest(exclusions)),
            ("partition", digest(partition)))))
    return W.build_sealed_package(inputs, sealed_at=AS_OF + "T00:00:00Z")


def modern_gate_verdicts(package):
    from scripts.pettripfinder import first_party_binding as FPB
    return FPB.evaluate_package(package)


_GATE_REMEDY = {
    "NO_CAPTURE_HASH": (
        "re-read the page on the same attended same-origin lane at $0 and hash the document in "
        "the SAME call that takes the quote. The shadow's attended lane recorded document_bytes "
        "and no document_sha256, and the acquisition directory it named is gitignored and empty, "
        "so no hash can be derived from anything committed", False),
    "NO_TIMESTAMP": (
        "re-capture the page and record the capture timestamp; the committed row states none",
        False),
    "AMENITY_CHIP_ONLY": (
        "re-capture the operative policy text from the property's own page; an amenity label "
        "states no policy", False),
    "SERVICE_ANIMAL_ONLY": (
        "re-capture the operative policy text; a service-animal sentence is a legal access "
        "category and never a pet acceptance or a refusal", False),
    "FEE_ONLY": (
        "re-capture the acceptance sentence; a fee, count or weight alone does not establish "
        "acceptance", False),
    "QUOTE_NOT_OPERATIVE": (
        "re-capture the operative policy text from the property's own page", False),
    "STRUCTURED_NO_PETS_INSUFFICIENT": (
        "re-capture the operative refusal text; a bare machine field is not the page's policy",
        False),
    "WRONG_PROPERTY": (
        "re-bind the identity's official URL on the address its own page states", True),
    "IDENTITY_UNBOUND": (
        "bind the record's identity key to the census identity", True),
    "LEAD_ONLY": (
        "re-capture from a first-party surface; a lead grade never publishes", False),
    "NOT_FIRST_PARTY_URL": (
        "re-capture from the property's own first-party endpoint", False),
    "FACT_UNCITED": (
        "cite every published fact, or withhold the fact the source does not state", True),
    "FACT_CONTRADICTED": (
        "resolve the disagreement between a published fact and the quote cited for it", True),
    "QUOTE_CONTRADICTS_CLAIM": (
        "the cited quote states the opposite of the claim; re-read the page", False),
    "STATUS_INVALID": (
        "record the review the publishable status requires", True),
}


def gate_holds(verdicts, by_key):
    """One hold record per row the modern evidence gate refuses."""
    out = []
    for failure in verdicts["failures"]:
        key = failure["identity_key"]
        ident = by_key.get(key, {})
        remedy, reversible = _GATE_REMEDY.get(
            failure["classification"],
            ("re-capture the evidence the gate requires", False))
        out.append(OrderedDict([
            ("identity_key_proposed", key),
            ("canonical_name", ident.get("canonical_name") or key),
            ("address", ident.get("street") or ""),
            ("corridor", ident.get("corridor") or ""),
            ("classification", "MODERN_EVIDENCE_GATE_HOLD"),
            ("gate_classification", failure["classification"]),
            ("failed_checks", failure["failed_checks"]),
            ("capture_lane", ((ident.get("_clean") or (None, {}))[1] or {}).get("lane", "")),
            ("why", "the ATLAS-THROUGHPUT-003 first-party evidence gate refuses this row: %s. "
                    "The shadow's read is preserved verbatim in "
                    "nashville_tn_clean_authority_001.json and is not disputed; what the modern "
                    "gate refuses is that this EVIDENCE establishes this POLICY to production "
                    "standard. Holding it is the only correct move -- lowering the gate to keep "
                    "the count would publish a fact the record cannot support."
                    % failure["why"]),
            ("published_anything", False),
            ("shadow_policy_class", ("CLEAN_PET_FRIENDLY" if failure["kind"] == "pet_friendly"
                                     else "CLEAN_VERIFIED_NO_PETS")),
            ("reversible_without_recapture", reversible),
            ("next_action", remedy),
        ]))
    out.sort(key=lambda h: h["identity_key_proposed"])
    return out


def paid_provenance_holds(package, ledgered_attempt_ids):
    """Rows whose evidence came from a PAID lane with no usable reservation.

    Rule O: a published fact read through a paid lane must name the reservation
    that bought it -- the run, an attempt id that re-derives, and the hash of the
    request envelope -- so a reviewer can tell a purchase that was ledgered from
    one that was not.
    """
    from scripts.pettripfinder import market_package_writer as W
    from scripts.pettripfinder import sealed_market_package as SMP
    from scripts.pettripfinder.acquisition.paid_attempt_ledger import attempt_id

    out = {}
    for ref in package["evidence_references"]:
        if not W.is_paid_lane(str(ref.get("capture_lane") or "")):
            continue
        key = str(ref.get("identity_key") or "")
        reservation = ref.get("paid_reservation")
        problem = ""
        if not isinstance(reservation, dict):
            problem = "NO_RESERVATION_FOR_A_PAID_CAPTURE"
        elif not SMP.is_sha256(SMP.normalise_sha256(
                str(reservation.get("request_envelope_sha256") or ""))):
            problem = "NO_REQUEST_ENVELOPE_HASH"
        elif reservation.get("attempt_id") != attempt_id(
                MARKET_ID, str(reservation.get("run_id") or ""), key,
                str(reservation.get("lane") or "")):
            problem = "ATTEMPT_ID_DOES_NOT_REDERIVE"
        elif reservation.get("attempt_id") not in ledgered_attempt_ids:
            problem = "NO_ATTEMPT_IN_THE_PAID_ATTEMPT_LEDGER"
        if problem:
            out[key] = problem
    return out


# --------------------------------------------------------------------------- #

def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="build and validate, write nothing")
    args = ap.parse_args(argv)

    shadow = _load(GOVERNING_SOURCE)
    projected = shadow["projected"]
    governing = {"census": projected["census"],
                 "clean_pet_friendly": projected["pet_friendly"],
                 "clean_verified_no_pets": projected["verified_no_pets"],
                 "unresolved": projected["unresolved"]}

    identities, migration_holds, proposed_census, clean_doc = read_source()
    audit = _load(AUDIT_REPORT)
    routing = _load(ROUTING_REPORT)
    routes_by_key = {}
    alias_of = {}
    for ident in identities:
        for alias in ident["identity_key_aliases"]:
            alias_of[alias] = ident["identity_key"]
        alias_of[ident["identity_key"]] = ident["identity_key"]
    for route in routing["routes"]:
        key = alias_of.get(route["identity_key"], route["identity_key"])
        if route.get("url"):
            routes_by_key.setdefault(key, route["url"])
    held_reads = {alias_of.get(r["identity_key"], r["identity_key"])
                  for r in audit["reads"] if r["audit_verdict"] == "HELD"}

    # THE COUNT GATE. It runs over the carry-across BEFORE any gate removes a
    # row, so the migration holds are counted back in: a governing number that a
    # later filter is allowed to move is not governing.
    held_pf = sum(1 for h in migration_holds if h["shadow_policy_class"] == "CLEAN_PET_FRIENDLY")
    held_np = sum(1 for h in migration_holds
                  if h["shadow_policy_class"] == "CLEAN_VERIFIED_NO_PETS")
    got = {"census": len(identities) + len(migration_holds),
           "clean_pet_friendly": held_pf + sum(
               1 for i in identities
               if i["_clean"] and i["_clean"][0] == "CLEAN_PET_FRIENDLY"),
           "clean_verified_no_pets": held_np + sum(
               1 for i in identities
               if i["_clean"] and i["_clean"][0] == "CLEAN_VERIFIED_NO_PETS"),
           "unresolved": sum(1 for i in identities if i["_clean"] is None)
                         + sum(1 for h in migration_holds
                               if h["shadow_policy_class"] == "UNRESOLVED")}
    if got != governing:
        raise RegistrationError("COUNT GATE: governing %s, computed %s" % (governing, got))

    by_key = {i["identity_key"]: i for i in identities}

    # GATE 1 -- cross-market identity. A published key is globally unique.
    collisions = cross_market_holds(identities)
    for record in collisions:
        by_key[record["identity_key_proposed"]]["_hold"] = record
    holds = list(migration_holds) + list(collisions)

    # GATE 2 -- the capture hash. Taken before the shards are built, because the
    # exclusions contract will not serialize a record without one.
    hash_held = capture_hash_holds(identities)
    for record in hash_held:
        by_key[record["identity_key_proposed"]]["_hold"] = record
    holds = holds + hash_held

    contract = build_market_contract(identities)
    run_id, raw_reservations = firecrawl_reservations()

    def _compose(publishing_set):
        census = build_census(identities, holds, proposed_census)
        policy = build_policy_package(publishing_set)
        exclusions = build_exclusions(publishing_set)
        seed_rows = build_seed_rows(policy, by_key, routes_by_key)
        partition = build_partition(identities, routes_by_key, held_reads)
        reservations = bind_reservations(publishing_set, raw_reservations, run_id)
        return census, policy, exclusions, seed_rows, partition, reservations

    # PASS 1: everything the registration gates admit, so the modern evidence
    # gate sees the whole cohort rather than a set already filtered by it.
    publishing = [i for i in identities if i["_hold"] is None]
    census, policy, exclusions, seed_rows, partition, reservations = _compose(publishing)
    package = gate_package(contract, census, policy, exclusions, seed_rows, partition,
                           reservations)
    verdicts = modern_gate_verdicts(package)
    evidence_held = gate_holds(verdicts, by_key)
    for record in evidence_held:
        by_key[record["identity_key_proposed"]]["_hold"] = record
    holds = holds + evidence_held

    # GATE 3 -- paid provenance, over the rows the evidence gate admitted.
    publishing = [i for i in identities if i["_hold"] is None]
    census, policy, exclusions, seed_rows, partition, reservations = _compose(publishing)
    package = gate_package(contract, census, policy, exclusions, seed_rows, partition,
                           reservations)
    ledgered = ledger_attempt_ids()
    paid_problems = paid_provenance_holds(package, ledgered)
    paid_held = []
    for key, problem in sorted(paid_problems.items()):
        ident = by_key[key]
        paid_held.append(OrderedDict([
            ("identity_key_proposed", key),
            ("canonical_name", ident["canonical_name"]),
            ("address", ident["street"]), ("corridor", ident["corridor"]),
            ("classification", "PAID_PROVENANCE_HOLD"),
            ("gate_classification", problem),
            ("capture_lane", ident["_clean"][1]["lane"]),
            ("why", "this row's evidence was bought through a paid lane and rule O of the fast "
                    "release lane refuses it: %s. The READ is not in doubt -- it passed the "
                    "first-party evidence gate. What is missing is the provenance record."
                    % problem),
            ("published_anything", False),
            ("shadow_policy_class", ident["_clean"][0]),
            ("reversible_without_recapture", True),
            ("next_action", "ingest run %s into ptf_paid_attempt_ledger_001.json through "
                            "acquisition.paid_attempt_ledger, recording the request envelope the "
                            "committed run already carries" % run_id),
        ]))
        ident["_hold"] = paid_held[-1]
    holds = holds + paid_held

    # PASS 2: the same builders over the surviving cohort, and the gates again.
    publishing = [i for i in identities if i["_hold"] is None]
    census, policy, exclusions, seed_rows, partition, reservations = _compose(publishing)
    package = gate_package(contract, census, policy, exclusions, seed_rows, partition,
                           reservations)
    recheck = modern_gate_verdicts(package)
    if recheck["ineligible"]:
        raise RegistrationError("the modern evidence gate still refuses %d rows after the hold: "
                                "%s" % (recheck["ineligible"],
                                        [f["identity_key"] for f in recheck["failures"]]))
    still_paid = paid_provenance_holds(package, ledgered)
    if still_paid:
        raise RegistrationError("rule O still refuses %d rows after the hold: %s"
                                % (len(still_paid), sorted(still_paid)))
    holds_doc = build_holds(holds)

    print("COUNT GATE      : PASS", got)
    print("migration holds : %d (registered census contract cannot carry the row)"
          % len(migration_holds))
    print("cross-market    : %d held" % len(collisions))
    print("evidence serial : %d held %s"
          % (len(hash_held), dict(Counter(h["gate_classification"] for h in hash_held))))
    print("modern gate     : %d evaluated, %d eligible, %d held %s"
          % (verdicts["records_evaluated"], verdicts["eligible"], verdicts["ineligible"],
             dict(verdicts["classes"])))
    print("paid provenance : %d rows held, %d reservations bound, %d ledger attempts"
          % (len(paid_held), len(reservations), len(ledgered)))
    print("market contract : %d corridors" % len(contract["corridors"]))
    print("census          : %d registered, %d publication holds"
          % (census["count"], holds_doc["count"]))
    print("policy rows     :", len(policy["hotels"]))
    print("exclusion rows  :", len(exclusions["exclusions"]))
    print("seed rows       :", len(seed_rows))
    print("partition       :", partition["count"], dict(partition["final_state_counts"]))
    if args.check:
        print("nothing written (--check)")
        return 0

    _write(CONTRACT_PATH, contract)
    _write(CENSUS_PATH, census)
    _write(HOLDS_PATH, holds_doc)
    _write(POLICY_PATH, policy)
    _write(PARTITION_PATH, partition)
    _write(str(MA.exclusions_shard_path(MARKET_ID)), exclusions)
    _write(str(MA.routing_shard_path(MARKET_ID)), OrderedDict([
        ("schema", "ptf-identity-routing/1.0"), ("contract", "ptf-identity-routing/1.0"),
        ("market_id", MARKET_ID),
        ("note", "This market's slice of the identity-routing authority. Nashville authors no "
                 "override: every published row's route is the one its own first-party source "
                 "stated. The global identity_routing.json is generated and must not be "
                 "hand-edited."),
        ("work_order", WORK_ORDER), ("source_batches", []), ("count", 0), ("routes", []),
    ]))
    # The affiliate shard is rendered by the contract that OWNS it: the affiliate
    # test asserts every committed shard is byte-for-byte what
    # affiliate_destinations.empty_document renders.
    from scripts.pettripfinder import affiliate_destinations as AD
    affiliate_path = MA.affiliate_shard_path(MARKET_ID)
    affiliate_path.parent.mkdir(parents=True, exist_ok=True)
    affiliate_path.write_text(MA.render_json(AD.empty_document(MARKET_ID)), encoding="utf-8",
                              newline="\n")
    seed_path = str(MA.seed_shard_path(MARKET_ID))
    os.makedirs(os.path.dirname(seed_path), exist_ok=True)
    # The authority module owns the committed CSV style -- LF line endings,
    # minimal quoting, the frozen column order -- so the shard is rendered by
    # it rather than by a local DictWriter. A local writer emits CRLF, which
    # made this the only seed shard in the repository with CRLF; git normalised
    # it on commit, so the working tree and the committed blob disagreed and
    # the package's `seed` dependency digest did not reproduce from a fresh
    # checkout.
    with open(seed_path, "w", encoding="utf-8", newline="") as fh:
        fh.write(MA.render_seed_csv(seed_rows))
    print("written.")
    return 0


def ledger_attempt_ids():
    """Every attempt id the committed paid-attempt ledger holds."""
    if not os.path.isfile(LEDGER_PATH):
        return set()
    return {str(a.get("attempt_id") or "") for a in (_load(LEDGER_PATH).get("attempts") or ())}


if __name__ == "__main__":
    raise SystemExit(main())
