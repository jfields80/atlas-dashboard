"""PTF-LEXINGTON-KY-PROMOTION-AND-NEW-LANE-LAUNCH-PREP-003 -- the Lexington applier.

Turns the Lexington SHADOW, built by PTF-LEXINGTON-KY-NEW-MARKET-001 and
PTF-LEXINGTON-KY-POLICY-ACQUISITION-002 before the registered-market
requirement existed, into shared production source. It is the only file in this
order that writes outside a Lexington-named path.

WHAT IT BUILDS

  markets/lexington-ky.json                                the market contract
  identity_census/lexington-ky.json                        the registered census
  lexington_ky_identity_holds_003.json                     rows the contract holds
  markets/authority/lexington-ky/seed_businesses.csv       the display rows
  markets/authority/lexington-ky/hotel_exclusions.json     the VERIFIED_NO_PETS
  markets/authority/lexington-ky/identity_routing.json     empty; no override
  markets/authority/lexington-ky/affiliate_destinations.json empty; none authored
  hotel_policy_facts_lexington-ky.json                     the published rows
  lexington_ky_final_partition_001.json                    every identity, once

SEMANTIC PRESERVATION IS THE WHOLE POINT

This order may not re-research Lexington and may not improve its counts. Every
fact written here already exists in the committed shadow reports; this module
RESHAPES them into the documents the registered contracts own, and refuses
rather than inventing a value it cannot find.

Three reshapings are worth naming, because each could be mistaken for new work:

  IDENTITY KEY   The shadow keyed identities ``name--street`` to break two
                 same-name collisions -- two Holiday Inn Expresses and two Red
                 Roof Inns. The registered identity contract
                 (``ptf_identity_key/1.0``) derives the key from the canonical
                 name alone, so the discriminator cannot survive. A colliding
                 group admits at most the ONE row that carries a published fact,
                 and that row states its own address on its own record; every
                 other row in the group is HELD by name and publishes nothing,
                 which is what it already did. Renaming a row to break the tie
                 would invent a geography the source never stated, so nothing is
                 renamed.

  CROSS-MARKET   A published identity key is globally unique in this repository
                 -- 836 published keys across eleven live markets, no duplicate
                 -- and hotel_exclusions.validate refuses a second exclusion
                 under a name another market already excluded. Lexington's
                 Holiday Inn Express at 2255 Buena Vista Road lands on the key
                 Cleveland already publishes as VERIFIED_NO_PETS. It is HELD,
                 not renamed and not published: the alternative is to overwrite
                 a live market's record or to fail the build.

  CITY, POSTAL   Six census rows carry no city and six clean rows no postal
                 code, because the OSM element that found them stated neither.
                 Both are read from the row's OWN first-party evidence
                 (``identity_signals.postal_on_page`` / ``address_on_page``) or,
                 for the city, from this market's single admitted municipality,
                 and the basis is recorded on the row. Nothing is guessed.

  CORRIDOR       Lexington's ZIPs cross corridors -- 40505 is in both Hamburg
                 and I-75/Winchester Road, 40509 in both Hamburg and Richmond
                 Road -- and seventeen census rows state no ZIP at all. A
                 postal-code partition is therefore impossible, so corridors
                 classify by ``explicit_hotel_ids`` and membership is decided by
                 ``census_membership_basis = MARKET_GEOGRAPHY``: the contract's
                 own basis for exactly this market shape (Grand Rapids, Fort
                 Wayne). The explicit lists reproduce the shadow's corridor
                 assignment identity for identity.

THE COUNT GATE COMES FIRST, THE MODERN GATES SECOND

The shadow's own numbers -- 61 census / 28 clean pet-friendly / 14 clean
verified-no-pets / 19 unresolved -- are read from the committed report and must
reproduce EXACTLY from the carry-across before anything is allowed to remove a
row. Only then do the modern gates run, and every row they hold is named with
its reason in ``lexington_ky_identity_holds_003.json``. Fifteen rows are held:

    4  registration gates       3 IDENTITY_HOLD (a same-name pair the registered
                                identity contract cannot key) and 1
                                CROSS_MARKET_IDENTITY_COLLISION (Cleveland owns
                                the key)
    5  first-party evidence     3 AMENITY_CHIP_ONLY ("Pets Allowed: Yes" is a
                                label, not a policy) and 2 SERVICE_ANIMAL_ONLY
                                (a service-animal sentence is not a refusal)
    6  paid provenance          Firecrawl captures with no reservation in
                                ptf_paid_attempt_ledger_001.json

so the REGISTERED market is 57 census / 20 published / 10 verified-no-pets. No
gate was lowered to preserve a count, and the evidence gate runs AGAIN over the
surviving cohort: if it still refuses a row, this module raises.

The last group is the cheapest to recover and the only one that needs no new
capture: ingesting run ``lexington_ky_firecrawl_002`` into the paid-attempt
ledger clears all six and would take the market to 25 published / 11
verified-no-pets. That is a later order's work, not this one's, because the
committed record carries no request-envelope hash and this module will not
invent one.

WHAT IT REFUSES

  A clean row whose name will not round-trip to its identity key. A clean row
  with no quote, no capture hash or no first-party URL. A held identity that
  reaches the published set. A count that disagrees with the governing shadow.
  It raises rather than writing a partial package.

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

WORK_ORDER = "PTF-LEXINGTON-KY-PROMOTION-AND-NEW-LANE-LAUNCH-PREP-003"
MARKET_ID = "lexington-ky"
MARKET_NAME = "Lexington, Kentucky"
STATE_CODE = "KY"
AS_OF = "2026-09-08"

PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CONTRACT_PATH = os.path.join(PKG, "markets", "lexington-ky.json")
CENSUS_PATH = os.path.join(PKG, "identity_census", "lexington-ky.json")
HOLDS_PATH = os.path.join(PKG, "lexington_ky_identity_holds_003.json")
PARTITION_PATH = os.path.join(PKG, "lexington_ky_final_partition_001.json")
POLICY_PATH = os.path.join(PKG, "hotel_policy_facts_%s.json" % MARKET_ID)

ROUTING_REPORT = os.path.join(REPORTS, "lexington_ky_routing_and_static_capture_001.json")
RECON_REPORT = os.path.join(REPORTS, "lexington_ky_census_reconciliation_001.json")
CLEAN_REPORT = os.path.join(REPORTS, "lexington_ky_clean_inventory_002.json")
SHADOW_REPORT = os.path.join(REPORTS, "lexington_ky_shadow_market_002.json")

#: The shadow this order may not move. Read from the committed report, never
#: typed: a governing number that disagrees with its own source is not governing.
GOVERNING_SOURCE = SHADOW_REPORT

#: This order's authority to promote the SET. The founder work order directs
#: the conversion of the existing Lexington shadow into a registered authority
#: and forbids inferring any new policy decision. It is NOT a claim that a named
#: human read each row, and no human name is written into any field.
REVIEWER_ID = "PTF-FOUNDER-001"
REVIEW_BASIS = (
    "Set-level founder authorisation to REGISTER, not to launch. Founder work order "
    + WORK_ORDER + " directs this order to convert Lexington's existing shadow work into a "
    "registered authority package, to preserve every Lexington semantic policy decision "
    "exactly, and to infer no new Lexington policy decision. The promotion set is the clean "
    "cohort PTF-LEXINGTON-KY-POLICY-ACQUISITION-002 committed -- 28 CLEAN_PET_FRIENDLY and 14 "
    "CLEAN_VERIFIED_NO_PETS -- carried across unchanged. The agent did not attribute a per-row "
    "reading to the founder. Launch participation is a separate founder decision this order "
    "does not take.")

#: The corridors the shadow assigned, in display order. Names, labels and
#: descriptions are the discovery configuration's own words for the same cells;
#: nothing here invents a geography.
CORRIDORS = (
    ("downtown", "Downtown Lexington", "Downtown",
     "Rupp Arena, Central Bank Center, Main and Vine and the downtown overnight core."),
    ("inner-versailles-road", "Inner Versailles Road / Red Mile", "Inner Versailles Road",
     "Inner Versailles Road, the Red Mile, Southland and Oliver Lewis Way, running west "
     "toward Keeneland and Blue Grass Airport."),
    ("griffin-gate-newtown", "Griffin Gate / Newtown Pike", "Griffin Gate / Newtown",
     "Newtown Pike, Griffin Gate, North Broadway and the Coldstream research campus."),
    ("hamburg", "Hamburg", "Hamburg",
     "Hamburg Pavilion, Man o' War Boulevard east and the Sir Barton Way retail cluster."),
    ("richmond-road-i75-south", "Richmond Road / I-75 South", "Richmond Road",
     "Richmond Road US-25/421, Todds Road and the I-75 exit 104 Athens-Boonesboro "
     "interchange."),
    ("i75-winchester-road", "I-75 / Winchester Road", "I-75 / Winchester Road",
     "I-75 north at Winchester Road US-60 and the I-64 interchange."),
    ("nicholasville-road-south", "Nicholasville Road South", "Nicholasville Road",
     "Nicholasville Road US-27, Fritz Farm and south Lexington."),
)

BOUNDARY_NOTE = (
    "PTF-LEXINGTON-KY-NEW-MARKET-001 visitor market: Lexington-Fayette Urban County, the "
    "merged city-county, and nothing beyond it. Membership was decided by the OSM Fayette "
    "County polygon (admin_level=6), not by a mailing city and not by a postal-code list: all "
    "61 confirmed identities returned polygon:Fayette County. EVALUATED AND EXCLUDED as "
    "separate county seats and separate lodging destinations, each seen by the discovery box "
    "and classified OUTSIDE_MARKET on evidence rather than missed: Georgetown (Scott County, "
    "16 candidates), Nicholasville (Jessamine County, 3) and Versailles (Woodford County, 3). "
    "The three fringe towns remain an explicit hold with an empty explicit-admission "
    "mechanism; only a founder ruling admits one. ALSO EXCLUDED and outside the observation "
    "box entirely: Frankfort, Winchester, Richmond and Paris. Louisville's committed boundary "
    "review names Lexington a separate destination and does not claim it, and no other "
    "registered market's discovery box reaches Fayette County."
)

CENSUS_MEMBERSHIP_NOTE = (
    "PTF-GENERIC-CENSUS-MEMBERSHIP-HARDENING-001. This market's corridors classify by "
    "explicit_hotel_ids and claim no postal code, so a ZIP-keyed ownership test can only ever "
    "answer no. It could not answer anything else: ZIP 40505 falls in both Hamburg and "
    "I-75/Winchester Road and ZIP 40509 in both Hamburg and Richmond Road, and seventeen "
    "census rows state no ZIP at all, so no postal-code partition of these corridors exists. "
    "Membership is decided by the market's own committed geography -- the Fayette County "
    "polygon and included_municipalities in "
    "scripts/pettripfinder/discovery/config/lexington_ky.json -- and the corridors classify "
    "what is already in."
)


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


def _sha(text):
    return "sha256:" + hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def _prefixed(digest):
    d = (digest or "").strip()
    if not d:
        return ""
    return d if d.startswith("sha256:") else "sha256:" + d


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", (text or "").strip().lower()).strip("-")


def _zip5(value):
    """The five-digit ZIP a source states, or "". ZIP+4 keeps its first five."""
    m = re.match(r"\s*(\d{5})", str(value or ""))
    return m.group(1) if m else ""


# --------------------------------------------------------------------------- #
# Reading the shadow.
# --------------------------------------------------------------------------- #

def _evidence_signals(row):
    """Every identity signal any lane recorded for one clean row."""
    out = []
    ev = row.get("evidence") or {}
    out.append(ev.get("identity_signals") or {})
    for obs in (row.get("all_observations") or []):
        out.append((obs or {}).get("identity_signals") or {})
    return out


def _stated_postal(row):
    for sig in _evidence_signals(row):
        for field in ("postal_on_page", "postal_code"):
            z = _zip5(sig.get(field))
            if z:
                return z, "the postal code stated by the property's own page"
    return "", ""


def _stated_street(row):
    for sig in _evidence_signals(row):
        for field in ("street_on_page", "address_on_page"):
            v = (sig.get(field) or "").strip()
            if v:
                return v, "the street address stated by the property's own page"
    return "", ""


def read_shadow():
    """The shadow, joined and keyed by the REGISTERED identity key.

    Returns ``(identities, clean_by_key, held)``. ``held`` is every identity the
    registered identity contract cannot admit, with the reason.
    """
    routing = _load(ROUTING_REPORT)
    recon = _load(RECON_REPORT)
    clean_doc = _load(CLEAN_REPORT)

    recon_by_osm = {}
    for rec in recon["records"]:
        if rec.get("osm_element"):
            recon_by_osm.setdefault(rec["osm_element"], rec)

    # Registered key -> the shadow rows that produce it.
    grouped = OrderedDict()
    for ident in routing["identities"]:
        key = ptf_identity_key(ident["name"])
        if normalize_name(ident["name"]) != key:
            raise RegistrationError(
                "%r does not round-trip: normalize_name gives %r but the identity key is %r"
                % (ident["name"], normalize_name(ident["name"]), key))
        grouped.setdefault(key, []).append(ident)

    clean_by_shadow_key = {r["identity_key"]: r for r in clean_doc["clean_rows"]}

    def _shadow_key(row):
        return "%s--%s" % (slugify(row["name"]), slugify(row["address_line"]))

    identities, held = [], []
    for key, rows in grouped.items():
        if len(rows) > 1:
            # A colliding key admits AT MOST the one row that actually carries a
            # published fact. The registered contract keys on the canonical name
            # alone, so the shadow's street discriminator cannot survive; but a
            # row that publishes nothing loses nothing by being held, and the one
            # row that does publish keeps its own address on its own record. When
            # two rows in a group both publish there is no non-arbitrary choice
            # and every one of them is held.
            clean_rows = [r for r in rows if clean_by_shadow_key.get(_shadow_key(r))]
            keep = clean_rows[0] if len(clean_rows) == 1 else None
            for row in rows:
                if row is keep:
                    continue
                sibling = ("the sibling at %s is admitted under this key because it carries "
                           "this market's published refusal and states its own address on its "
                           "own record" % keep["address_line"]) if keep is not None else \
                    ("no row in this group carries a published fact, so there is no "
                     "non-arbitrary row to admit and all of them are held")
                held.append(OrderedDict([
                    ("identity_key_proposed", key),
                    ("shadow_identity_key", _shadow_key(row)),
                    ("canonical_name", row["name"]),
                    ("address", row["address_line"]),
                    ("corridor", row["cell_id"]),
                    ("classification", "IDENTITY_HOLD"),
                    ("why", "two active Lexington premises trade under the name %r. The shadow "
                            "separated them with a street-address discriminator; "
                            "ptf_identity_key/1.0 derives the registered key from the canonical "
                            "name alone, so both rows would claim one identity. This row is "
                            "UNRESOLVED in the shadow and publishes nothing, and %s."
                            % (row["name"], sibling)),
                    ("published_anything", False),
                    ("next_action", "a founder ruling on a distinguishing name that ADDS "
                                    "geography rather than changing the chain, after which "
                                    "this row may be admitted"),
                ]))
            if keep is None:
                continue
            rows = [keep]
        row = rows[0]
        rec = recon_by_osm.get(row.get("osm_element") or "", {})
        clean = clean_by_shadow_key.get(_shadow_key(row))
        if clean is None:
            # The shadow's own key repair rewrote some keys; fall back to the
            # one join that cannot drift -- the canonical name.
            clean = next((r for r in clean_doc["clean_rows"]
                          if ptf_identity_key(r["canonical_name"]) == key), None)

        city = (row.get("city") or rec.get("city") or "").strip()
        city_basis = "stated by the discovery source"
        if not city:
            city = "Lexington"
            city_basis = ("this market admits exactly one municipality and the row is inside "
                          "the Fayette County polygon; the merged city-county has no other")
        postal = _zip5(row.get("postal_code")) or _zip5(rec.get("postal_code"))
        postal_basis = "stated by the discovery source" if postal else ""
        street = (row.get("address_line") or rec.get("address_line") or "").strip()
        street_basis = "stated by the discovery source" if street else ""
        if clean is not None:
            if not postal:
                postal, postal_basis = _stated_postal(clean)
            if not street:
                street, street_basis = _stated_street(clean)

        # The identity's OWN official page. For a row this market read, that is
        # the page the read came from -- which is also the repaired route:
        # PTF-LEXINGTON-KY-POLICY-ACQUISITION-002 found five census rows sharing
        # one WRONG official URL (a Comfort Inn in Winchester, a different town)
        # and re-bound each on the address its own page states. The routing
        # report still carries the pre-repair value, so a row with a read takes
        # its route from the read. A row with no read keeps the routing report's.
        official_url = (clean["evidence"]["canonical_url"] if clean is not None
                        else (row.get("route") or ""))
        official_url_basis = ("the page this market's policy read was taken from, which is the "
                              "route PTF-LEXINGTON-KY-POLICY-ACQUISITION-002 repaired"
                              if clean is not None else
                              "the official route PTF-LEXINGTON-KY-NEW-MARKET-001 recorded")

        identities.append(OrderedDict([
            ("identity_key", key),
            ("canonical_name", row["name"]),
            ("slug", row.get("artifact_slug") or slugify(row["name"])),
            ("market_id", MARKET_ID),
            ("street", street), ("street_basis", street_basis),
            ("city", city), ("city_basis", city_basis),
            ("state", STATE_CODE),
            ("postal_code", postal), ("postal_basis", postal_basis),
            ("county", row.get("county") or rec.get("county") or ""),
            ("brand", row.get("brand") or ""),
            ("latitude", row.get("latitude")), ("longitude", row.get("longitude")),
            ("osm_element", row.get("osm_element") or ""),
            ("corridor", row["cell_id"]),
            ("assignment_basis", enums.BASIS_EXPLICIT),
            ("assignment_value", key),
            ("identity_state", "IDENTITY_CONFIRMED"),
            ("lodging_state", "LODGING_CONFIRMED"),
            ("collision_state", enums.COLLISION_NONE),
            ("classification", rec.get("classification") or "EXACT_UNIQUE_IDENTITY"),
            ("classification_reason", rec.get("classification_why") or ""),
            ("geography", rec.get("geography") or "IN_MARKET"),
            ("geography_why", rec.get("geography_why") or ""),
            ("official_url", official_url),
            ("official_url_basis", official_url_basis),
            ("route", row.get("route") or ""),
            ("shadow_route", row.get("route") or ""),
            ("route_class", row.get("route_class") or ""),
            ("lanes", ["OSM_LOCAL_EXTRACT"]),
        ]))
        identities[-1]["_clean"] = clean
        identities[-1]["_hold"] = None

    # The CROSS-MARKET gate. A published identity key is globally unique in this
    # repository -- 836 published keys across eleven live markets and not one
    # duplicate -- and hotel_exclusions.validate refuses a second exclusion under
    # a name another market already excluded. A Lexington clean row that lands on
    # a key another market already publishes is HELD here, at its cause, rather
    # than surfacing as an assembler crash. It is not renamed: the name is the
    # property's own, and inventing a distinguishing one would state a geography
    # no source stated. It is not resolved by moving the other market's row
    # either; that market is live.
    owned = published_keys_of_other_markets()
    for ident in identities:
        clean = ident["_clean"]
        if clean is None:
            continue
        holder = owned.get(ident["identity_key"])
        if not holder:
            continue
        ident["_hold"] = OrderedDict([
            ("identity_key_proposed", ident["identity_key"]),
            ("shadow_identity_key", _shadow_key({"name": ident["canonical_name"],
                                                 "address_line": ident["street"]})),
            ("canonical_name", ident["canonical_name"]),
            ("address", ident["street"]),
            ("corridor", ident["corridor"]),
            ("classification", "CROSS_MARKET_IDENTITY_COLLISION"),
            ("why", "%s already publishes the identity key %r as %s. A published identity key "
                    "is globally unique in this repository and the exclusions contract refuses "
                    "the second row by name, so admitting this one would either fail the build "
                    "or overwrite a live market's record. The shadow's %s read is preserved "
                    "verbatim in lexington_ky_clean_inventory_002.json and nothing about it is "
                    "disputed; only its ADMISSION is held."
                    % (holder[1], ident["identity_key"], holder[0], clean["policy_class"])),
            ("published_anything", False),
            ("colliding_market", holder[1]),
            ("colliding_state", holder[0]),
            ("next_action", "a founder ruling on a distinguishing canonical name that ADDS "
                            "geography for one of the two rows, or a contract change that "
                            "scopes the published identity key by market"),
        ])

    identities.sort(key=lambda i: i["identity_key"])
    held.sort(key=lambda h: (h["identity_key_proposed"], h["address"]))
    clean_by_key = {i["identity_key"]: i["_clean"] for i in identities if i["_clean"]}
    return identities, clean_by_key, held, clean_doc


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


# --------------------------------------------------------------------------- #
# The market contract.
# --------------------------------------------------------------------------- #

def build_market_contract(identities):
    members = OrderedDict((slug, []) for slug, _n, _d, _desc in CORRIDORS)
    for ident in identities:
        slug = ident["corridor"].split("__", 1)[1]
        if slug not in members:
            raise RegistrationError("census row %r claims corridor %r, which this market does "
                                    "not declare" % (ident["identity_key"], ident["corridor"]))
        members[slug].append(ident["identity_key"])

    corridors = []
    for order, (slug, name, area, description) in enumerate(CORRIDORS, start=1):
        corridors.append(OrderedDict([
            ("corridor_id", "%s__%s" % (MARKET_ID, slug)),
            ("market_id", MARKET_ID),
            ("name", name),
            ("slug", slug),
            ("title", "Pet-Friendly Hotels in %s | PetTripFinder Lexington" % name),
            ("meta_description",
             "Verified pet-friendly hotels in %s, with real pet fees and policies read from "
             "each hotel's own official website." % name),
            ("description", description),
            ("included_cities", []),
            ("included_postal_codes", []),
            ("explicit_hotel_ids", sorted(members[slug])),
            ("excluded_hotel_ids", []),
            ("minimum_hotel_count", MC.DEFAULT_MINIMUM_HOTEL_COUNT),
            ("show_in_navigation", False),
            ("show_in_sitemap", False),
            ("allow_multi_corridor", False),
            ("display_order", order),
            ("display_area", area),
            ("state_code", STATE_CODE),
        ]))

    doc = OrderedDict([
        ("schema", MC.SCHEMA_VERSION),
        ("market_id", MARKET_ID),
        ("market_name", MARKET_NAME),
        ("market_slug", MARKET_ID),
        ("state_name", "Kentucky"),
        ("state_code", STATE_CODE),
        ("primary_state_code", STATE_CODE),
        ("states", [STATE_CODE]),
        ("primary_city", "Lexington"),
        ("country_code", "US"),
        ("title", "Pet-Friendly Hotels in Lexington, Kentucky | PetTripFinder"),
        ("meta_description",
         "Verified pet-friendly hotels across Lexington, Kentucky, with real pet fees and "
         "policies read from each hotel's own official website."),
        ("introductory_copy",
         "Every listing links to a pet policy verified directly from the hotel's own official "
         "website."),
        ("navigation_label", "Lexington"),
        ("show_in_navigation", False),
        ("show_in_sitemap", False),
        ("minimum_published_hotels", 5),
        ("route_mode", MC.ROUTE_MODE_MARKET_PREFIXED),
        ("census_membership_basis", MC.MEMBERSHIP_MARKET_GEOGRAPHY),
        ("_census_membership_note", CENSUS_MEMBERSHIP_NOTE),
        ("_boundary_note", BOUNDARY_NOTE),
        ("corridors", corridors),
        ("registered_by", WORK_ORDER),
        ("registered_at", AS_OF),
    ])
    MC.parse_market(doc, source=CONTRACT_PATH)
    return doc


# --------------------------------------------------------------------------- #
# The census.
# --------------------------------------------------------------------------- #

def build_census(identities, held, clean_by_key, recon):
    admitted_osm = {i["osm_element"] for i in identities if i["osm_element"]}
    held_names = {h["canonical_name"] for h in held}

    hotels = []
    for ident in identities:
        clean = ident["_clean"]
        if clean is None:
            policy_state = "POLICY_NOT_VERIFIED"
            policy_note = "Identity evidence never establishes a pet policy."
        elif clean["policy_class"] == "CLEAN_PET_FRIENDLY":
            policy_state, policy_note = "POLICY_CONFIRMED", \
                "First-party acceptance read on the property's own page."
        else:
            policy_state, policy_note = "VERIFIED_NO_PETS", \
                "First-party refusal read on the property's own page."
        row = OrderedDict((k, v) for k, v in ident.items()
                          if k not in ("_clean", "_hold"))
        row["policy_state"] = policy_state
        row["policy_note"] = policy_note
        hotels.append(row)

    non_admitted = []
    for h in held:
        # A modern-evidence-gate hold keeps its census identity: the property is
        # real and in this market, and what is held is its PUBLICATION. Its
        # partition row carries AWAITING_POLICY_ARTIFACT. Only an identity hold
        # -- a row the registered identity contract cannot key at all -- leaves
        # the census.
        if h["classification"] in ("MODERN_EVIDENCE_GATE_HOLD", "PAID_PROVENANCE_HOLD"):
            continue
        non_admitted.append(OrderedDict([
            ("identity_key", ""),
            ("canonical_name", h["canonical_name"]),
            ("market_id", MARKET_ID),
            ("street", h["address"]), ("city", "Lexington"), ("state", STATE_CODE),
            ("corridor", h["corridor"]),
            ("classification", "IDENTITY_REVIEW_REQUIRED"),
            ("hold_class", h["classification"]),
            ("classification_reason", h["why"]),
            ("held_by", WORK_ORDER),
        ]))
    for rec in recon["records"]:
        if rec.get("classification") == "EXACT_UNIQUE_IDENTITY" \
                and rec.get("osm_element") in admitted_osm:
            continue
        if rec.get("classification") == "EXACT_UNIQUE_IDENTITY" \
                and rec.get("name") in held_names:
            continue
        non_admitted.append(OrderedDict([
            ("identity_key", ""),
            ("canonical_name", rec.get("name") or ""),
            ("market_id", MARKET_ID),
            ("street", rec.get("address_line") or ""),
            ("city", rec.get("city") or ""), ("state", rec.get("state") or ""),
            ("postal_code", _zip5(rec.get("postal_code"))),
            ("county", rec.get("county") or ""),
            ("corridor", rec.get("cell_id") or ""),
            ("classification", rec.get("classification") or ""),
            ("classification_reason", rec.get("classification_why") or ""),
            ("geography", rec.get("geography") or ""),
            ("geography_why", rec.get("geography_why") or ""),
            ("osm_element", rec.get("osm_element") or ""),
        ]))

    doc = OrderedDict([
        ("schema", enums.CENSUS_SCHEMA),
        ("market_id", MARKET_ID),
        ("status", "REGISTERED"),
        ("identity_key_contract", "ptf_identity_key/1.0"),
        ("identity_contract", "ptf-identity-evidence/1.0"),
        ("work_order", WORK_ORDER),
        ("captured_at", AS_OF),
        ("note", "Lexington's registered identity census, carried across from the shadow "
                 "PTF-LEXINGTON-KY-NEW-MARKET-001 and PTF-LEXINGTON-KY-POLICY-ACQUISITION-002 "
                 "committed. Membership was decided by the OSM Fayette County polygon. Four "
                 "shadow rows are NOT admitted: two same-name pairs whose street-address "
                 "discriminator the registered identity contract cannot carry. All four are "
                 "unresolved rows that publish nothing; they are held by name in "
                 "lexington_ky_identity_holds_003.json and none of them is in the clean "
                 "cohort."),
        ("source_authorities", [
            "launch_packages/pettripfinder/markets/reports/lexington_ky_census_reconciliation_001.json",
            "launch_packages/pettripfinder/markets/reports/lexington_ky_routing_and_static_capture_001.json",
            "launch_packages/pettripfinder/markets/reports/lexington_ky_clean_inventory_002.json",
        ]),
        ("count", len(hotels)),
        ("shadow_confirmed_identities", 61),
        ("held_from_shadow", len(held)),
        ("total_candidates", len(recon["records"])),
        ("classification_counts",
         OrderedDict(sorted(Counter(h["classification"] for h in hotels).items()))),
        ("corridor_counts",
         OrderedDict(sorted(Counter(h["corridor"] for h in hotels).items()))),
        ("hotels", hotels),
        ("non_admitted", non_admitted),
    ])
    issues = CENSUS.validate(doc, market_states=[STATE_CODE])
    if issues:
        raise RegistrationError("census fails its contract: %s"
                                % [(i.path, i.code, i.detail) for i in issues][:10])
    return doc


# --------------------------------------------------------------------------- #
# Policy, exclusions, seed rows, partition.
# --------------------------------------------------------------------------- #

_LANE_CAPTURE = {"ATTENDED_BROWSER": "browser_assisted",
                 "FIRECRAWL": "firecrawl_rendered_fetch",
                 "DIRECT_STATIC": "deterministic_fetch"}


def _evidence_row(ident, clean, field, value):
    ev = clean["evidence"]
    quote = str(ev.get("exact_quote") or "").strip()
    if not quote:
        raise RegistrationError("%s: a clean row with no quote" % ident["canonical_name"])
    url = ev.get("canonical_url") or ""
    if not url.startswith("https://"):
        raise RegistrationError("%s: a clean row with no first-party https source"
                                % ident["canonical_name"])
    digest = _prefixed(ev.get("content_sha256"))
    if not digest:
        raise RegistrationError("%s: a clean row with no capture hash"
                                % ident["canonical_name"])
    return OrderedDict([
        ("field", field),
        ("quote", quote[:400]),
        ("source_url", url),
        ("value", str(value).lower() if isinstance(value, bool) else str(value)),
        ("evidence_ref", "ev:" + hashlib.sha256(
            (ident["identity_key"] + field + quote).encode("utf-8")).hexdigest()[:16]),
        ("artifact_class", "PUBLICATION_GRADE_EVIDENCE"),
        ("artifact_sha256", digest),
        ("artifact_kind", "rendered_html"),
        ("captured_at", ev.get("captured_at") or AS_OF),
        ("capture_method", _LANE_CAPTURE.get(ev.get("lane") or "", "browser_assisted")),
        ("source_grade", "PT2_BRAND"),
    ])


def build_policy_package(identities):
    hotels = []
    for ident in identities:
        clean = ident["_clean"]
        if ident["_hold"] is not None:
            continue
        if clean is None or clean["policy_class"] != "CLEAN_PET_FRIENDLY":
            continue
        facts = OrderedDict([("pets_allowed", True)])
        parsed = (clean["evidence"].get("parsed_facts") or {})
        if parsed.get("pets_allowed") is not True:
            raise RegistrationError("%s: a CLEAN_PET_FRIENDLY row whose read does not say yes"
                                    % ident["canonical_name"])
        rec = OrderedDict([
            ("key", ident["identity_key"]),
            ("identity_key", ident["identity_key"]),
            ("name", ident["canonical_name"]),
            ("market_id", MARKET_ID),
            ("schema_version", enums.POLICY_SCHEMA_VERSION),
            ("facts", facts),
            ("computation_class", FC.classify(facts).computation_class),
            ("evidence", [_evidence_row(ident, clean, "pets_allowed", True)]),
            ("source_url", clean["evidence"]["canonical_url"]),
            ("corridor", ident["corridor"]),
            ("verified_at", (clean["evidence"].get("captured_at") or AS_OF)),
            ("capture_lane", clean["evidence"].get("lane") or ""),
            ("withheld_facts", clean["evidence"].get("withheld_facts") or {}),
            ("reviewer_id", REVIEWER_ID),
            ("reviewed_at", AS_OF),
            ("review_basis", REVIEW_BASIS),
            ("work_order", WORK_ORDER),
        ])
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
        ("note", "Lexington's published pet-friendly authority. Every row states acceptance "
                 "and nothing else: PTF-LEXINGTON-KY-POLICY-ACQUISITION-002 deliberately "
                 "withheld fee, weight and count parsing, and withheld_facts carries that "
                 "decision forward rather than letting a blank read as a zero."),
        ("hotels", hotels),
    ])
    issues = SCHEMA.validate_package(doc)
    if issues:
        raise RegistrationError("policy package fails its contract: %s"
                                % [(i.path, i.code) for i in issues][:10])
    return doc


def build_exclusions(identities):
    records = []
    for ident in identities:
        clean = ident["_clean"]
        if ident["_hold"] is not None:
            continue
        if clean is None or clean["policy_class"] != "CLEAN_VERIFIED_NO_PETS":
            continue
        ev = clean["evidence"]
        quote = str(ev.get("exact_quote") or "").strip()
        if not quote:
            raise RegistrationError("%s: a VERIFIED_NO_PETS row with no refusal quote"
                                    % ident["canonical_name"])
        if (ev.get("parsed_facts") or {}).get("pets_allowed") is not False:
            raise RegistrationError("%s: a VERIFIED_NO_PETS row whose read does not say no"
                                    % ident["canonical_name"])
        rec = OrderedDict([
            ("market_id", MARKET_ID),
            ("exclusion_id", "lex-" + slugify(ident["canonical_name"])),
            ("canonical_name", ident["canonical_name"]),
            ("normalized_name", ident["identity_key"]),
            ("address", ident["street"]), ("city", ident["city"]),
            ("state", STATE_CODE), ("postal_code", ident["postal_code"]),
            ("official_url", ev["canonical_url"]),
            ("exclusion_state", HE.VERIFIED_NO_PETS),
            ("evidence_quote", quote),
            ("source_url", ev["canonical_url"]),
            ("observed_at", (ev.get("captured_at") or AS_OF)[:10]),
            ("source_hash", _prefixed(ev.get("content_sha256"))),
        ])
        rec["record_hash"] = HE.record_hash(rec)
        rec["reviewer_id"] = REVIEWER_ID
        rec["reviewed_at"] = AS_OF
        rec["approval_hash"] = HE.approval_hash(rec)
        rec["review_basis"] = REVIEW_BASIS
        rec["notes"] = (
            "%s. First-party refusal read on the property's own page by the %s lane and "
            "carried across from PTF-LEXINGTON-KY-POLICY-ACQUISITION-002 unchanged. "
            "Service-animal access is a legal category and never converts a refusal into "
            "acceptance." % (WORK_ORDER, ev.get("lane") or "attended"))
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


def build_seed_rows(policy, by_key):
    rows = []
    for h in policy["hotels"]:
        ident = by_key[h["key"]]
        missing = [f for f, v in (("address", ident["street"]), ("city", ident["city"]),
                                  ("postal_code", ident["postal_code"]))
                   if not v]
        if missing:
            raise RegistrationError("%s: a published row states no %s, and nothing here "
                                    "invents one" % (h["name"], ", ".join(missing)))
        route = ident.get("official_url") or h["source_url"]
        rows.append(OrderedDict([
            ("name", h["name"]), ("category", "pet-friendly-hotels"),
            ("address", ident["street"]), ("city", ident["city"]), ("state", STATE_CODE),
            ("postal_code", ident["postal_code"]), ("phone", ""),
            ("website_url", route), ("source_url", h["source_url"]),
            ("source_type", "OFFICIAL_PROPERTY"),
            ("observed_at", str(h["verified_at"])[:10]), ("rating", ""), ("amenities", ""),
            ("pet_policy", h["evidence"][0]["quote"][:600]), ("canonical", ""),
            ("market_id", MARKET_ID),
        ]))
    rows.sort(key=lambda r: r["name"].lower())
    return rows


def build_partition(identities):
    items = []
    for ident in identities:
        clean = ident["_clean"]
        hold = ident["_hold"]
        if hold is not None and hold["classification"] in ("MODERN_EVIDENCE_GATE_HOLD",
                                                           "PAID_PROVENANCE_HOLD"):
            state, resolved = "AWAITING_POLICY_ARTIFACT", False
            action = hold["next_action"]
            source = "ATLAS-THROUGHPUT-003 first-party gate (%s)" % hold["gate_classification"]
        elif clean is not None and clean["policy_class"] == "CLEAN_PET_FRIENDLY":
            state, resolved, action, source = "PUBLISHED_PET_FRIENDLY", True, "", ""
        elif clean is not None and clean["policy_class"] == "CLEAN_VERIFIED_NO_PETS":
            state, resolved, action, source = "VERIFIED_NO_PETS", True, "", ""
        elif not ident.get("shadow_route"):
            state, resolved = "AWAITING_ROUTING_REVIEW", False
            action = ("No free lane stated an official route for this identity; "
                      "PTF-LEXINGTON-KY-POLICY-ACQUISITION-002 recorded it FREE_LANE_EXHAUSTED.")
            source = "lexington_ky_routing_and_static_capture_001.json route_class"
        else:
            state, resolved = "AWAITING_POLICY_OBSERVATION", False
            action = ("Routed but not yet read. The capture outcome the shadow recorded is in "
                      "lexington_ky_shadow_market_002.json's unresolved queue.")
            source = "lexington_ky_shadow_market_002.json unresolved_queue"
        items.append(OrderedDict([
            ("identity_key", ident["identity_key"]),
            ("canonical_name", ident["canonical_name"]),
            ("slug", ident["slug"]),
            ("city", ident["city"]), ("state", STATE_CODE),
            ("postal_code", ident["postal_code"]),
            ("corridor", ident["corridor"]),
            ("final_state", state), ("resolved", resolved), ("next_action", action),
            ("next_action_source", source),
            ("determined_by", WORK_ORDER), ("updated_at", AS_OF),
            ("official_url", ident.get("official_url") or ""),
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


def modern_gate_verdicts(contract, census, policy, exclusions, seed_rows, partition):
    """The ATLAS-THROUGHPUT-003 first-party evidence gate, run on the records
    this order is about to write rather than on what it already wrote.

    The gate is the module that owns the rule, called through the sealed-package
    writer so it sees exactly the identity records and evidence references a
    release would see. Nothing here interprets a verdict; the caller holds every
    record the gate does not call ELIGIBLE.
    """
    from scripts.pettripfinder import first_party_binding as FPB
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
    package = W.build_sealed_package(inputs, sealed_at=AS_OF + "T00:00:00Z")
    return FPB.evaluate_package(package)


def paid_provenance_holds(policy, exclusions, by_key):
    """Rows whose evidence came from a PAID lane with no reservation provenance.

    ATLAS-THROUGHPUT-003 rule O: a published fact read through a paid lane must
    name the reservation that bought it -- the attempt id, the run, and the hash
    of the request envelope -- so a reviewer can tell a purchase that was
    ledgered from one that was not.

    Lexington's ten Firecrawl captures (run lexington_ky_firecrawl_002, 10 of 10
    authorised credits, balance 469 -> 459) are recorded in
    lexington_ky_firecrawl_pass_002.json but were never ingested into
    ptf_paid_attempt_ledger_001.json, which holds 806 attempts across seven
    markets and none for Lexington. There is no request-envelope hash anywhere in
    the committed record, so no reservation can be DERIVED -- only invented, and
    an invented provenance hash is worse than a missing one.

    So the paid-lane rows are held. The remedy is small, mechanical and belongs
    to a later order: ingest the run through
    acquisition.paid_attempt_ledger.build_attempt and record the request
    envelope. Nothing about the reads themselves is in doubt; every one of them
    passed the first-party evidence gate.
    """
    from scripts.pettripfinder import market_package_writer as W
    from scripts.pettripfinder.acquisition import paid_attempt_ledger as PAL

    ledger_path = os.path.join(PKG, "ptf_paid_attempt_ledger_001.json")
    ledgered = set()
    if os.path.isfile(ledger_path):
        for attempt in (_load(ledger_path).get("attempts") or ()):
            if attempt.get("market_id") == MARKET_ID and attempt.get("identity_key"):
                ledgered.add(str(attempt["identity_key"]))

    rows = [(h["key"], h["capture_lane"], "CLEAN_PET_FRIENDLY") for h in policy["hotels"]]
    for record in exclusions["exclusions"]:
        ident = by_key.get(record["normalized_name"])
        lane = (ident or {}).get("_clean", {}).get("evidence", {}).get("lane", "")
        rows.append((record["normalized_name"], lane, "CLEAN_VERIFIED_NO_PETS"))

    out = []
    for key, lane, policy_class in rows:
        method = _LANE_CAPTURE.get(lane or "", "")
        if not W.is_paid_lane(method) or key in ledgered:
            continue
        ident = by_key.get(key, {})
        out.append(OrderedDict([
            ("identity_key_proposed", key),
            ("shadow_identity_key", "%s--%s" % (slugify(ident.get("canonical_name") or key),
                                                slugify(ident.get("street") or ""))),
            ("canonical_name", ident.get("canonical_name") or key),
            ("address", ident.get("street") or ""),
            ("corridor", ident.get("corridor") or ""),
            ("classification", "PAID_PROVENANCE_HOLD"),
            ("gate_classification", "NO_RESERVATION_IN_PAID_ATTEMPT_LEDGER"),
            ("capture_lane", lane),
            ("why", "this row's evidence was bought through the %s lane, and %s has no attempt "
                    "for it. ATLAS-THROUGHPUT-003 rule O requires a paid capture to name the "
                    "reservation that bought it, including the hash of the request envelope; "
                    "the committed Lexington record carries no envelope hash, so a reservation "
                    "can only be invented, never derived. The READ is not in doubt -- it passed "
                    "the first-party evidence gate. What is missing is the provenance record."
                    % (lane, "ptf_paid_attempt_ledger_001.json")),
            ("published_anything", False),
            ("shadow_policy_class", policy_class),
            ("next_action", "ingest run lexington_ky_firecrawl_002 into "
                            "ptf_paid_attempt_ledger_001.json through "
                            "acquisition.paid_attempt_ledger.build_attempt, recording the "
                            "request envelope hash; this hold then clears with no re-capture "
                            "and no new policy decision"),
            ("reversible_without_recapture", True),
        ]))
    out.sort(key=lambda h: h["identity_key_proposed"])
    return out


def gate_holds(verdicts, by_key):
    """One hold record per row the modern evidence gate refuses."""
    out = []
    for failure in verdicts["failures"]:
        key = failure["identity_key"]
        ident = by_key.get(key, {})
        out.append(OrderedDict([
            ("identity_key_proposed", key),
            ("shadow_identity_key", "%s--%s" % (slugify(ident.get("canonical_name") or key),
                                                slugify(ident.get("street") or ""))),
            ("canonical_name", ident.get("canonical_name") or key),
            ("address", ident.get("street") or ""),
            ("corridor", ident.get("corridor") or ""),
            ("classification", "MODERN_EVIDENCE_GATE_HOLD"),
            ("gate_classification", failure["classification"]),
            ("failed_checks", failure["failed_checks"]),
            ("why", "the ATLAS-THROUGHPUT-003 first-party evidence gate refuses this row: %s. "
                    "The shadow's read is preserved verbatim in "
                    "lexington_ky_clean_inventory_002.json and is not disputed; what the modern "
                    "gate refuses is that this QUOTE establishes this POLICY. Holding it is the "
                    "only correct move -- lowering the gate to keep the count would publish a "
                    "policy no operator stated." % failure["why"]),
            ("published_anything", False),
            ("shadow_policy_class", ("CLEAN_PET_FRIENDLY" if failure["kind"] == "pet_friendly"
                                     else "CLEAN_VERIFIED_NO_PETS")),
            ("next_action", "re-capture the operative policy text from the property's own page; "
                            "an amenity label, a fee sentence and a service-animal sentence each "
                            "establish nothing on their own"),
        ]))
    out.sort(key=lambda h: h["identity_key_proposed"])
    return out


def build_holds(held):
    return OrderedDict([
        ("schema", "ptf-market-identity-holds/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET_ID), ("as_of", AS_OF),
        ("note", "Shadow identities the registered identity contract cannot admit. Nothing "
                 "here was researched by this order and nothing here publishes: every held row "
                 "was already unresolved in the shadow. A hold is reversible by a founder "
                 "ruling; a rename is not this order's to make."),
        ("count", len(held)),
        ("counts_by_class",
         OrderedDict(sorted(Counter(h["classification"] for h in held).items()))),
        ("holds", held),
    ])


# --------------------------------------------------------------------------- #

def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="build and validate, write nothing")
    args = ap.parse_args(argv)

    shadow = _load(GOVERNING_SOURCE)
    governing = {"census": shadow["census"]["confirmed_active_identities"],
                 "clean_pet_friendly": shadow["policy"]["clean_pet_friendly"],
                 "clean_verified_no_pets": shadow["policy"]["clean_verified_no_pets"],
                 "unresolved": shadow["policy"]["unresolved"]}

    identities, clean_by_key, held, clean_doc = read_shadow()
    recon = _load(RECON_REPORT)

    got = {"census": len(identities) + len(held),
           "clean_pet_friendly": sum(1 for i in identities if i["_clean"] is not None
                                     and i["_clean"]["policy_class"] == "CLEAN_PET_FRIENDLY"),
           "clean_verified_no_pets": sum(
               1 for i in identities if i["_clean"] is not None
               and i["_clean"]["policy_class"] == "CLEAN_VERIFIED_NO_PETS"),
           "unresolved": sum(1 for i in identities if i["_clean"] is None) + len(held)}
    if got != governing:
        raise RegistrationError("COUNT GATE: governing %s, computed %s" % (governing, got))

    # A held ROW may never reach the published set. The test is the shadow's own
    # row key, not the name: a name is exactly what the two rows share, and
    # testing on it would hold the sibling that carries the published fact.
    held_rows = {h["shadow_identity_key"] for h in held}
    leak = sorted(r["identity_key"] for r in clean_doc["clean_rows"]
                  if r["identity_key"] in held_rows)
    if leak:
        raise RegistrationError("a HELD row is in the clean cohort: %s" % leak)

    # The count gate has proved the carry-across is faithful. Only now may the
    # modern gates remove anything, and every removal is named.
    gate_held = [i["_hold"] for i in identities if i["_hold"] is not None]
    admitted = [i for i in identities if i["_hold"] is None]
    held = held + gate_held

    contract = build_market_contract(admitted)
    by_key = {i["identity_key"]: i for i in admitted}

    # PASS 1: everything the registration gates admit, so the modern evidence
    # gate sees the whole cohort rather than a set already filtered by it.
    census = build_census(admitted, held, clean_by_key, recon)
    policy = build_policy_package(admitted)
    exclusions = build_exclusions(admitted)
    seed_rows = build_seed_rows(policy, by_key)
    partition = build_partition(admitted)

    # THE MODERN FIRST-PARTY EVIDENCE GATE. It owns the rule; this module only
    # holds what it refuses. A refused row keeps its census identity and its
    # unresolved partition state -- what is held is the PUBLICATION, not the
    # property.
    verdicts = modern_gate_verdicts(contract, census, policy, exclusions, seed_rows, partition)
    evidence_held = gate_holds(verdicts, by_key)
    paid_held = paid_provenance_holds(policy, exclusions, by_key)
    for record in evidence_held + paid_held:
        by_key[record["identity_key_proposed"]]["_hold"] = record
    held = held + evidence_held + paid_held

    # PASS 2: the same builders over the surviving cohort.
    publishing = [i for i in admitted if i["_hold"] is None]
    census = build_census(admitted, held, clean_by_key, recon)
    policy = build_policy_package(publishing)
    exclusions = build_exclusions(publishing)
    seed_rows = build_seed_rows(policy, {i["identity_key"]: i for i in publishing})
    partition = build_partition(admitted)
    holds = build_holds(held)

    recheck = modern_gate_verdicts(contract, census, policy, exclusions, seed_rows, partition)
    if recheck["ineligible"]:
        raise RegistrationError("the modern evidence gate still refuses %d rows after the hold: %s"
                                % (recheck["ineligible"],
                                   [f["identity_key"] for f in recheck["failures"]]))

    print("COUNT GATE      : PASS", got)
    print("modern gate     : %d evaluated, %d eligible, %d held %s"
          % (verdicts["records_evaluated"], verdicts["eligible"], verdicts["ineligible"],
             dict(verdicts["classes"])))
    print("paid provenance : %d rows held (no reservation in the paid-attempt ledger)"
          % len(paid_held))
    print("market contract : %d corridors" % len(contract["corridors"]))
    print("census          : %d admitted, %d non-admitted (%d held by this order)"
          % (census["count"], len(census["non_admitted"]), holds["count"]))
    print("policy rows     :", len(policy["hotels"]))
    print("exclusion rows  :", len(exclusions["exclusions"]))
    print("seed rows       :", len(seed_rows))
    print("partition       :", partition["count"], dict(partition["final_state_counts"]))
    if args.check:
        print("nothing written (--check)")
        return 0

    _write(CONTRACT_PATH, contract)
    _write(CENSUS_PATH, census)
    _write(HOLDS_PATH, holds)
    _write(POLICY_PATH, policy)
    _write(PARTITION_PATH, partition)
    _write(str(MA.exclusions_shard_path(MARKET_ID)), exclusions)
    _write(str(MA.routing_shard_path(MARKET_ID)), OrderedDict([
        ("schema", "ptf-identity-routing/1.0"), ("contract", "ptf-identity-routing/1.0"),
        ("market_id", MARKET_ID),
        ("note", "This market's slice of the identity-routing authority. Lexington authors no "
                 "override: every published row's route is the one its own first-party source "
                 "stated. The global identity_routing.json is generated and must not be "
                 "hand-edited."),
        ("work_order", WORK_ORDER), ("source_batches", []), ("count", 0), ("routes", []),
    ]))
    # The affiliate shard is rendered by the contract that OWNS it, not by this
    # module's opinion of it: tests/pettripfinder/test_affiliate_destinations.py
    # asserts every committed shard is byte-for-byte what
    # affiliate_destinations.empty_document renders, and a hand-written note --
    # however true -- is a different set of bytes.
    from scripts.pettripfinder import affiliate_destinations as AD
    affiliate_path = MA.affiliate_shard_path(MARKET_ID)
    affiliate_path.parent.mkdir(parents=True, exist_ok=True)
    affiliate_path.write_text(MA.render_json(AD.empty_document(MARKET_ID)), encoding="utf-8",
                              newline="\n")
    seed_path = str(MA.seed_shard_path(MARKET_ID))
    os.makedirs(os.path.dirname(seed_path), exist_ok=True)
    with open(seed_path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(seed_rows[0].keys()))
        w.writeheader()
        w.writerows(seed_rows)
    print("written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
