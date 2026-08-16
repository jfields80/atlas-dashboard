"""PTF-CINCINNATI-CENSUS-RECONCILIATION-001 -- rebuild Cincinnati from discovery.

The prior Cincinnati census was built FROM the corridor registry rather than
from independent discovery: every one of its 121 postal codes was already in
the registry, no hotel was ever found outside it, and 27 of the 57 registered
ZIPs held nothing at all -- including the CVG airport cluster, Florence,
Uptown/Clifton and Kenwood. A boundary that only ever confirms itself is not
evidence of completeness, so this work order rebuilds the census from official
destination-marketing directories and reconciles the old roster against it.

The pipeline, in order
----------------------
1. SOURCE LISTINGS  ``cincinnati_source_listings_001.json`` holds one row per
   listing as the source published it -- 239 rows across six official CVB
   directories. Nothing is collapsed there; it is evidence, not inventory.
2. CANDIDATES       listings collapse into candidate identities by street
   address + ZIP, then by name within a city. An address match additionally
   requires a compatible brand anchor, because two different hotels share one
   building often enough to matter (a Hampton and a Homewood both sit at 617
   Vine Street) and a bare address match would silently merge them.
3. RECONCILIATION   every candidate is matched against the prior 121-row census
   and every prior identity receives an explicit disposition. No prior identity
   disappears without one.
4. CENSUS/PARTITION the surviving identities are written as
   ``ptf-market-identity-census/1.1`` and ``ptf-market-final-partition/1.1``,
   with corridors assigned by the one assignment authority
   (``markets.assignment``), never by hand.
5. QUEUE            a founder/browser review queue is regenerated from the new
   partition. The old 121-row queue is a discovery lead, never authority.

What this module deliberately does NOT do
-----------------------------------------
It asserts no pet policy. Every row it writes is ``POLICY_NOT_VERIFIED`` and
every unresolved row carries exactly one honest blocker. Publication states are
not invented for a market that has captured nothing.

Adjudication that needed a human decision is a named constant below rather than
a heuristic, so a reviewer can read the ruling instead of re-deriving it.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Mapping, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.pettripfinder.contracts import enums                      # noqa: E402
from scripts.pettripfinder.contracts.identity_key import ptf_identity_key  # noqa: E402
from scripts.pettripfinder.markets.assignment import assign_hotels, assignment_basis  # noqa: E402
from scripts.pettripfinder.markets.contract import (                    # noqa: E402
    load_markets, market_by_id, slugify,
)
from scripts.pettripfinder.site_data import normalize_name              # noqa: E402

WORK_ORDER = "PTF-CINCINNATI-CENSUS-RECONCILIATION-001"
MARKET_ID = "cincinnati-oh"
AS_OF = "2026-08-16"

PKG = REPO_ROOT / "launch_packages" / "pettripfinder"
SOURCE_LISTINGS = PKG / "cincinnati_source_listings_001.json"
#: The 121-row census as it stood at d14cdc4, pinned as an INPUT. Reading the
#: live census here instead would make the builder read its own output on the
#: second run, and every prior-identity disposition would silently describe the
#: rebuilt roster rather than the one being reconciled.
PRIOR_CENSUS_PATH = PKG / "cincinnati_prior_census_001.json"
CENSUS_PATH = PKG / "identity_census" / "cincinnati-oh.json"
MARKET_PATH = PKG / "markets" / "cincinnati-oh.json"
LEDGER_PATH = PKG / "cincinnati_candidate_ledger_001.json"
PARTITION_PATH = PKG / "cincinnati_final_partition_001.json"
QUEUE_PATH = PKG / "markets" / "reports" / "cincinnati-oh_founder_review_queue.json"
BOUNDARY_PATH = PKG / "identity_census" / "cincinnati-dayton-boundary-review.json"

#: Every other market whose census could collide with Cincinnati's.
NEIGHBOUR_MARKETS: Tuple[str, ...] = ("dayton-oh", "columbus-oh",
                                      "cleveland-akron-canton-oh")

class IdentityCollision(ValueError):
    """One identity key would cover two different properties (fail closed)."""


# --------------------------------------------------------------------------- #
# Ledger dispositions.
# --------------------------------------------------------------------------- #

CANONICAL_CENSUS = "CANONICAL_CENSUS"
IDENTITY_UNRESOLVED = "IDENTITY_UNRESOLVED"
CONFIRMED_DUPLICATE = "CONFIRMED_DUPLICATE"
BOUNDARY_EXCLUDED = "BOUNDARY_EXCLUDED"
CATEGORY_EXCLUDED = "CATEGORY_EXCLUDED"
CLOSED_OR_CONVERTED = "CLOSED_OR_CONVERTED"
ALREADY_ACCOUNTED_FOR = "SOURCE_LISTING_ALREADY_ACCOUNTED_FOR"
NOT_LODGING = "SOURCE_LISTING_NOT_LODGING"

# Prior-identity dispositions (section 9 of the work order).
RETAIN = "RETAIN"
RENAME = "RENAME"
MERGE_DUPLICATE = "MERGE_DUPLICATE"
HOLD_IDENTITY_REVIEW = "HOLD_IDENTITY_REVIEW"

# --------------------------------------------------------------------------- #
# Human adjudication.
# --------------------------------------------------------------------------- #

#: Source listings that are food-and-beverage outlets carrying their host
#: hotel's street address. Collapsing them by address would quietly give a hotel
#: a second name; each is dispositioned on its own instead.
FNB_OUTLET_LISTINGS: Tuple[str, ...] = (
    "On The Rocks Bourbon Bar and Restaurant",   # inside Delta Hotels Sharonville
    "BLU Restaurant & Bar",                      # inside Embassy Suites Cincinnati NE
    "Red Roost Tavern",                          # inside Hyatt Regency Cincinnati
    "North by Hotel Covington",                  # inside Hotel Covington
)

#: Short-term rentals and guesthouses. Columbus ruled this category
#: OUT_OF_CURRENT_CATEGORY (hotel_exclusions.json: 50-lincoln-short-north,
#: timbrook-guesthouse) and the same rule is applied here rather than inventing
#: a second standard. The first five share one telephone number
#: (859-350-6328) in the source data, which is one operator's rental portfolio
#: listed as five properties.
CATEGORY_EXCLUDED_LISTINGS: Tuple[str, ...] = (
    "Life on the Globe",
    "Luxury Artist's Condo",
    "Southgate Trolley House",
    "The Pickle Factory",
    "Translucency BnB & Gallery",
    "First Farm Inn",
)

#: Candidate listing name -> prior census identity_key. Every pair was read by
#: hand: the automatic matcher proposed nineteen merges and eleven of them were
#: brand collisions between different properties (a Courtyard downtown against a
#: Courtyard in Mason, a Tru in Sharonville against a Tru in Monroe). Only the
#: eight below are the same property under two names.
MERGE_DECISIONS: Dict[str, str] = {
    "Courtyard By Marriott Blue Ash": "courtyard by marriott cincinnati blue ash",
    "Doubletree Suites by Hilton Cincinnati Blue Ash":
        "doubletree suites by hilton hotel cincinnati blue ash",
    "Hyatt Place Blue Ash": "hyatt place cincinnati blue ash",
    "Embassy Suites Cincinnati RiverCenter":
        "embassy suites by hilton cincinnati rivercenter",
    "Red Roof Inn Erlanger": "red roof inn cincinnati airport florence erlanger",
    "Hotel Covington": "hotel covington cincinnati riverfront",
    "LivINN Hotel Cincinnati Sharonville":
        "livinn hotel cincinnati sharonville convention center",
    "Quality Inn West Chester": "quality inn i 75 west chester north cincinnati",
}

#: Prior identities the sources contradict or cannot corroborate, with the
#: ruling. Absent from here means the identity is RETAINed on its prior
#: evidence -- the Warren County directory this run could only expose twelve
#: featured properties, so its Mason cluster is uncorroborated for a reason that
#: has nothing to do with whether those hotels exist.
PRIOR_IDENTITY_RULINGS: Dict[str, Tuple[str, str]] = {
    "baymont by wyndham mason": (
        HOLD_IDENTITY_REVIEW,
        "Name-only prior row. The Butler County directory carries a Baymont by "
        "Wyndham at 40 New Garver Rd, Monroe OH 45050; no source this run "
        "places a Baymont in Mason. Held for identity review rather than "
        "merged, because merging would move a property fifteen miles on a "
        "brand-name match alone."),
    "hampton inn and suites cincinnati downtown": (
        RETAIN,
        "Distinct from Homewood Suites by Hilton Cincinnati Downtown despite "
        "sharing 617 Vine Street: two Hilton brands operate in one building. "
        "The address matcher's brand guard is what keeps them apart."),
}

#: ``(listing name, city, state) -> canonical name``. Destination-marketing
#: directories publish bare brand names, and three unrelated "Red Roof Inn"
#: rows in one market would collapse into one identity key and silently delete
#: two hotels. Each canonical name below adds only the locality the source
#: itself published for that row; nothing about the property is invented, and
#: the verbatim listing name stays in the ledger and the source-listings file.
#: The Home2 Suites entry additionally resolves a CROSS-market collision: the
#: bare key already belongs to a Cleveland property in Independence, Ohio.
DISAMBIGUATION: Dict[Tuple[str, str, str], Tuple[str, str]] = {
    ("Home2 Suites by Hilton", "Florence", "KY"): (
        "Home2 Suites by Hilton Florence Cincinnati Airport South",
        "The bare name collides with cleveland-akron-canton-oh's Home2 Suites "
        "by Hilton in Independence, Ohio. The property name is taken from the "
        "brand property page the directory links to, "
        "home2suites3.hilton.com/en/hotels/kentucky/"
        "home2-suites-by-hilton-florence-cincinnati-airport-south-CVGFCHT/."),
    ("Red Roof Inn", "Richwood", "KY"): (
        "Red Roof Inn Richwood",
        "Three directories publish the bare name \"Red Roof Inn\" for three "
        "different hotels. The Clermont County and Dearborn County rows resolve "
        "onto prior census identities that were already disambiguated; this "
        "Boone County property is new and needs its own name."),
    ("Microtel Inn & Suites", "Florence", "KY"): (
        "Microtel Inn & Suites Florence",
        "The bare brand name would collide with the prior census's Microtel "
        "Inn & Suites by Wyndham Mason/Kings Island lineage."),
    ("Sleep Inn & Suites", "Oxford", "OH"): (
        "Sleep Inn & Suites Oxford",
        "Butler County publishes the bare brand name for its Oxford property."),
}

#: Postal codes the source published that do not exist in their stated city.
#: They are preserved verbatim -- correcting them would be fabrication -- and
#: the corridor engine falls through to its city+state tier, which places both
#: properties correctly and records ``city_state`` as the basis that fired.
KNOWN_SOURCE_ZIP_DEFECTS: Dict[str, str] = {
    "Extended Stay America Florence Meijer Drive":
        "source publishes 40142 (Hardin County KY) for a Florence, Boone "
        "County property",
    "LaQuinta Inn & Suites Florence":
        "source publishes 41242 (Johnson County KY) for a Florence, Boone "
        "County property",
}

# --------------------------------------------------------------------------- #
# Normalisation helpers.
# --------------------------------------------------------------------------- #

_ABBR = [(r"\bstreet\b", "st"), (r"\broad\b", "rd"), (r"\bdrive\b", "dr"),
         (r"\bavenue\b", "ave"), (r"\bboulevard\b", "blvd"), (r"\bparkway\b", "pkwy"),
         (r"\bhighway\b", "hwy"), (r"\blane\b", "ln"), (r"\bcircle\b", "cir"),
         (r"\bcourt\b", "ct"), (r"\bplace\b", "pl"), (r"\bnorth\b", "n"),
         (r"\bsouth\b", "s"), (r"\beast\b", "e"), (r"\bwest\b", "w")]

_NAME_STOP = {"by", "the", "a", "at", "of", "and", "hotel", "hotels", "inn", "inns",
              "suites", "suite", "motel", "lodge", "cincinnati", "cincinnatis", "near"}

#: Brand anchors. Two listings at one street address belong to one identity only
#: when their brand anchors are compatible; a Hampton and a Homewood at 617 Vine
#: Street are two hotels, and nothing but the brand tells you so.
_BRAND_ANCHORS = (
    "hampton", "homewood", "home2", "hilton", "doubletree", "embassy", "tru", "spark",
    "curio", "marriott", "courtyard", "fairfield", "residence", "springhill",
    "towneplace", "renaissance", "westin", "aloft", "moxy", "delta", "ac", "sheraton",
    "autograph", "tribute", "holiday", "candlewood", "staybridge", "avid", "voco",
    "indigo", "crowne", "comfort", "quality", "sleep", "clarion", "econo", "rodeway",
    "mainstay", "suburban", "days", "super", "baymont", "microtel", "wingate", "ramada",
    "travelodge", "laquinta", "quinta", "hawthorn", "wyndham", "hyatt", "roof",
    "sonesta", "drury", "studio", "extended", "hometowne", "woodspring", "intown",
    "livinn", "radisson", "kinley", "graduate", "glendalia", "lytle", "phelps",
    "summit", "blu", "cincinnatian", "netherland", "celare", "golden", "lamb",
    "turfside", "wildwood", "ashley", "chester", "fidelity", "budget", "surestay",
    "western", "country", "hollywood", "star", "butler", "elms", "marcum", "sycamore",
    "mariemont", "whitewater", "hannaford", "wolf", "great", "kings", "empire",
    "countryside", "symphony", "glendale",
)


def norm_addr(value: str) -> str:
    out = re.sub(r"[^a-z0-9 ]", " ", (value or "").lower())
    for pat, rep in _ABBR:
        out = re.sub(pat, rep, out)
    return re.sub(r"\s+", " ", out).strip()


def street_number(value: str) -> str:
    match = re.match(r"\s*(\d+)", value or "")
    return match.group(1) if match else ""


def address_key(address: str, postal_code: str) -> Tuple[str, str, str]:
    tokens = norm_addr(address).split()
    return (street_number(address), tokens[1] if len(tokens) > 1 else "",
            (postal_code or "")[:5])


def name_tokens(value: str) -> frozenset:
    text = re.sub(r"[^a-z0-9 ]", " ", (value or "").lower().replace("&", " and "))
    return frozenset(w for w in text.split() if w and w not in _NAME_STOP)


def brand_anchors(value: str) -> frozenset:
    tokens = name_tokens(value)
    return frozenset(b for b in _BRAND_ANCHORS if b in tokens)


def brands_compatible(left: str, right: str) -> bool:
    """True unless both names name a brand and the brands disagree."""
    lb, rb = brand_anchors(left), brand_anchors(right)
    if not lb or not rb:
        return True
    return bool(lb & rb)


def city_key(value: str) -> str:
    return re.sub(r"[^a-z ]", " ", (value or "").lower().replace(".", "")).strip()


# --------------------------------------------------------------------------- #
# Stage 1 -- collapse source listings into candidates.
# --------------------------------------------------------------------------- #

def build_candidates(listings: Sequence[Mapping]) -> Tuple[List[Dict], List[Dict]]:
    """``(candidates, non_lodging_rows)``.

    Deterministic: listings are processed in file order and the first listing to
    claim an address or a name owns the candidate, so the same input always
    produces the same collapse.
    """
    candidates: List[Dict] = []
    fnb: List[Dict] = []
    by_addr: Dict[Tuple[str, str, str], List[Dict]] = {}
    by_name: Dict[Tuple[frozenset, str, str], Dict] = {}

    for row in listings:
        name = row.get("listing_name", "")
        if name in FNB_OUTLET_LISTINGS:
            fnb.append(dict(row))
            continue

        akey = address_key(row.get("address", ""), row.get("postal_code", ""))
        nkey = (name_tokens(name), city_key(row.get("city", "")), row.get("state", ""))

        target = None
        if akey[0] and akey[2]:
            for cand in by_addr.get(akey, ()):
                if brands_compatible(name, cand["canonical_name"]):
                    target = cand
                    break
        if target is None:
            target = by_name.get(nkey)

        if target is None:
            target = {
                "canonical_name": name,
                "address": row.get("address", ""),
                "city": row.get("city", ""),
                "state": row.get("state", ""),
                "postal_code": row.get("postal_code", ""),
                "phone": row.get("phone", ""),
                "listings": [],
            }
            candidates.append(target)
            if akey[0] and akey[2]:
                by_addr.setdefault(akey, []).append(target)
            by_name[nkey] = target

        target["listings"].append(dict(row))
        for field in ("address", "postal_code", "phone"):
            if not target[field] and row.get(field):
                target[field] = row[field]
    return candidates, fnb


# --------------------------------------------------------------------------- #
# Stage 2 -- reconcile candidates against the prior census.
# --------------------------------------------------------------------------- #

def reconcile(candidates: Sequence[Dict], prior: Sequence[Mapping]) -> Tuple[Dict, Dict]:
    """``(candidate_key -> prior identity_key, prior identity_key -> candidate)``."""
    prior_by_addr: Dict[Tuple[str, str, str], List[Mapping]] = {}
    for row in prior:
        if row.get("address", "").strip() and row.get("postal_code"):
            prior_by_addr.setdefault(
                address_key(row["address"], row["postal_code"]), []).append(row)

    matched: Dict[int, str] = {}
    claimed: Dict[str, Dict] = {}
    for index, cand in enumerate(candidates):
        hit = None
        akey = address_key(cand["address"], cand["postal_code"])
        if akey[0] and akey[2]:
            for row in prior_by_addr.get(akey, ()):
                if brands_compatible(cand["canonical_name"], row["canonical_name"]):
                    hit = row
                    break
        if hit is None:
            target_key = MERGE_DECISIONS.get(cand["canonical_name"])
            if target_key:
                hit = next((r for r in prior if r["identity_key"] == target_key), None)
        if hit is None:
            # A source that publishes names without addresses (the Warren County
            # directory exposes only twelve featured properties and no address
            # fields) cannot be matched on city, so the city test is skipped for
            # those rows and the name threshold is raised instead. Matching them
            # is what keeps one hotel from entering the census twice.
            cityless = not city_key(cand["city"])
            threshold = 0.8 if cityless else 0.7
            ctok = name_tokens(cand["canonical_name"])
            for row in prior:
                if row["state"] != cand["state"]:
                    continue
                if not cityless and city_key(row["city"]) != city_key(cand["city"]):
                    continue
                if not brands_compatible(cand["canonical_name"], row["canonical_name"]):
                    continue
                htok = name_tokens(row["canonical_name"])
                if not ctok or not htok:
                    continue
                overlap = len(ctok & htok) / len(ctok | htok)
                contained = bool(ctok) and ctok <= htok
                if overlap >= threshold or (cityless and contained):
                    hit = row
                    break
        if hit is not None and hit["identity_key"] not in claimed:
            matched[index] = hit["identity_key"]
            claimed[hit["identity_key"]] = cand
    return matched, claimed


# --------------------------------------------------------------------------- #
# Stage 3 -- identities.
# --------------------------------------------------------------------------- #

def identity_state_for(row: Mapping) -> str:
    """A confirmed identity needs an independently sourced street address."""
    if row.get("address", "").strip() and row.get("postal_code", "").strip():
        return enums.IDENTITY_CONFIRMED
    if row.get("address", "").strip() or row.get("postal_code", "").strip():
        return enums.IDENTITY_PROVISIONAL
    return enums.IDENTITY_UNRESOLVED


def build_identities(candidates, matched, prior, rulings) -> Tuple[List[Dict], List[Dict]]:
    """``(identities, ledger_rows)`` -- one identity per surviving property."""
    prior_by_key = {r["identity_key"]: r for r in prior}
    ledger: List[Dict] = []
    identities: List[Dict] = []
    seen_keys: Dict[str, Dict] = {}

    def emit(name, address, city, state, postal, phone, sources, prior_row, official_url):
        key = ptf_identity_key(name)
        existing = seen_keys.get(key)
        if existing is not None:
            # Two properties, one name. Directories publish bare brand names
            # ("Red Roof Inn", "Comfort Inn & Suites") for hotels a hundred
            # miles apart, and a bare identity key would silently merge them --
            # dropping a real hotel out of the census with no error anywhere.
            # Fail closed unless a ruling says how to tell them apart.
            same_place = (norm_addr(existing["address"]) == norm_addr(address)
                          and existing["postal_code"] == postal)
            if same_place:
                return existing, False
            raise IdentityCollision(
                "identity key %r would cover two different properties: %s, %s %s "
                "and %s, %s %s. Add a ruling to DISAMBIGUATION."
                % (key, existing["address"], existing["city"], existing["postal_code"],
                   address, city, postal))
        rec = {
            "identity_key": key,
            "canonical_name": name,
            "display_name": name,
            "slug": slugify(name),
            "market_id": MARKET_ID,
            "address": address,
            "city": city,
            "state": state,
            "postal_code": postal,
            "phone": phone,
            "official_url": official_url,
            "identity_state": "",
            "lodging_state": enums.LODGING_CONFIRMED,
            "policy_state": enums.POLICY_NOT_VERIFIED,
            "collision_state": enums.COLLISION_NONE,
            "corridor": "",
            "assignment_basis": "",
            "assignment_value": "",
            "source": "+".join(sorted(set(sources))) if sources else "prior_census",
            "observed_at": AS_OF,
            "provenance": WORK_ORDER,
            "prior_identity_key": prior_row["identity_key"] if prior_row else "",
        }
        rec["identity_state"] = identity_state_for(rec)
        identities.append(rec)
        seen_keys[key] = rec
        return rec, True

    # -- candidates ---------------------------------------------------------
    for index, cand in enumerate(candidates):
        listing_name = cand["canonical_name"]
        renamed, rename_reason = DISAMBIGUATION.get(
            (listing_name, cand["city"], cand["state"]), ("", ""))
        name = renamed or listing_name
        sources = [l["source"] for l in cand["listings"]]
        prior_key = matched.get(index)
        prior_row = prior_by_key.get(prior_key) if prior_key else None
        if name in CATEGORY_EXCLUDED_LISTINGS:
            disposition, reason = CATEGORY_EXCLUDED, (
                "Short-term rental or guesthouse, not a hotel in the current "
                "category (Columbus precedent).")
            rec, _ = emit(name, cand["address"], cand["city"], cand["state"],
                          cand["postal_code"], cand["phone"], sources, prior_row, "")
            rec["lodging_state"] = enums.NOT_LODGING
        elif prior_row is not None:
            disposition, reason = ALREADY_ACCOUNTED_FOR, (
                "Corroborates prior census identity %r; the sourced address, "
                "postal code and telephone are adopted." % prior_key)
            rec, _ = emit(prior_row["canonical_name"],
                          cand["address"] or prior_row.get("address", ""),
                          cand["city"] or prior_row.get("city", ""),
                          prior_row["state"],
                          cand["postal_code"] or prior_row.get("postal_code", ""),
                          cand["phone"] or prior_row.get("phone", ""),
                          sources, prior_row, prior_row.get("official_url", ""))
        else:
            disposition, reason = CANONICAL_CENSUS, (
                "New identity: present in an official destination-marketing "
                "directory and absent from the prior census.")
            rec, _ = emit(name, cand["address"], cand["city"], cand["state"],
                          cand["postal_code"], cand["phone"], sources, None, "")
            if rec["identity_state"] != enums.IDENTITY_CONFIRMED:
                disposition = IDENTITY_UNRESOLVED
                reason = ("Sourced without a usable street address or postal "
                          "code; identity must be resolved before any capture.")
            if renamed:
                disposition = RENAME
                reason = rename_reason
        ledger.append({
            "ledger_id": "CIN-CAND-%03d" % (len(ledger) + 1),
            "candidate_name": name,
            "source_listing_name_verbatim": listing_name,
            "identity_key": rec["identity_key"],
            "address": cand["address"], "city": cand["city"],
            "state": cand["state"], "postal_code": cand["postal_code"],
            "phone": cand["phone"],
            "sources": sorted(set(sources)),
            "source_urls": sorted({l["source_url"] for l in cand["listings"]}),
            "source_listing_names": sorted({l["listing_name"] for l in cand["listings"]}),
            "disposition": disposition,
            "disposition_reason": reason,
            "prior_identity_key": prior_key or "",
            "postal_code_defect": KNOWN_SOURCE_ZIP_DEFECTS.get(name, ""),
        })

    # -- prior identities ---------------------------------------------------
    claimed = set(matched.values())
    for row in prior:
        key = row["identity_key"]
        ruling, reason = rulings.get(key, (None, ""))
        if key in claimed:
            outcome = RETAIN if ruling in (None, RETAIN) else ruling
            reason = reason or "Corroborated this run by an official directory."
        elif ruling == HOLD_IDENTITY_REVIEW:
            outcome = HOLD_IDENTITY_REVIEW
        else:
            outcome = RETAIN
            reason = reason or (
                "Not corroborated this run. The directory that produced it was "
                "not fully reachable in this pass, and silence from a source is "
                "absence of evidence, not evidence of absence.")
        if key not in claimed:
            rec, created = emit(row["canonical_name"], row.get("address", ""),
                                row.get("city", ""), row["state"],
                                row.get("postal_code", ""), row.get("phone", ""),
                                [], row, row.get("official_url", ""))
            if created:
                rec["source"] = row.get("source", "prior_census")
                rec["observed_at"] = row.get("observed_at", AS_OF)
                rec["provenance"] = (
                    "worker/ptf-cincinnati-market-001 (prior census), retained by "
                    + WORK_ORDER)
                # An uncorroborated row learned nothing this run, so its identity
                # state is carried over rather than re-derived. Re-deriving would
                # read the prior census's postal code as evidence, and that
                # postal code was inferred from the corridor registry, never
                # sourced -- it is the very inference this work order exists to
                # undo. A state may fall here; it may never rise.
                rec["identity_state"] = row.get(
                    "identity_state", enums.IDENTITY_UNRESOLVED)
                if outcome == HOLD_IDENTITY_REVIEW:
                    rec["identity_state"] = enums.IDENTITY_UNRESOLVED
        ledger.append({
            "ledger_id": "CIN-PRIOR-%03d" % (len(ledger) + 1),
            "candidate_name": row["canonical_name"],
            "identity_key": key,
            "address": row.get("address", ""), "city": row.get("city", ""),
            "state": row["state"], "postal_code": row.get("postal_code", ""),
            "phone": row.get("phone", ""),
            "sources": ["prior_census"],
            "source_urls": [],
            "source_listing_names": [row["canonical_name"]],
            "disposition": outcome,
            "disposition_reason": reason,
            "prior_identity_key": key,
            "postal_code_defect": "",
        })
    return identities, ledger


# --------------------------------------------------------------------------- #
# Stage 4 -- geography, then documents.
# --------------------------------------------------------------------------- #

def assign_geography(identities: List[Dict]) -> Dict[str, int]:
    market = market_by_id(load_markets(MARKET_PATH.parent), MARKET_ID)
    rows = [dict(r, name=r["canonical_name"]) for r in identities]
    result = assign_hotels(market, rows, fail_closed=False)
    for rec in identities:
        key = normalize_name(rec["canonical_name"])
        corridors = result.corridor_of.get(key, ())
        basis, value = assignment_basis(result, key)
        # An unassigned row stores a null corridor, never an empty string: the
        # basis-integrity gate reads `corridor is None` as the proof that
        # "unassigned" was the tier that actually fired.
        rec["corridor"] = corridors[0] if corridors else None
        rec["assignment_basis"] = basis
        rec["assignment_value"] = value
    return {
        "unassigned": sum(1 for r in identities if not r["corridor"]),
        "conflicts": len(result.conflicts),
    }


def mark_collisions(identities: List[Dict]) -> int:
    groups: Dict[str, List[Dict]] = {}
    for rec in identities:
        if rec["address"].strip() and rec["postal_code"]:
            groups.setdefault(
                "%s|%s" % (norm_addr(rec["address"]), rec["postal_code"]), []).append(rec)
    shared = 0
    for members in groups.values():
        if len(members) > 1:
            shared += len(members)
            for rec in members:
                rec["collision_state"] = enums.COLLISION_SHARED_ADDRESS
    return shared


def partition_item(rec: Mapping) -> Dict:
    if rec["lodging_state"] == enums.NOT_LODGING:
        return {
            "identity_key": rec["identity_key"],
            "canonical_name": rec["canonical_name"],
            "slug": rec["slug"], "city": rec["city"], "state": rec["state"],
            "postal_code": rec["postal_code"],
            "final_state": enums.OUT_OF_CURRENT_CATEGORY,
            "resolved": True,
            "next_action": "",
            "next_action_source": "cincinnati_candidate_ledger_001.json",
            "determined_by": WORK_ORDER, "updated_at": AS_OF,
            "official_url": rec["official_url"], "state_override_reason": "",
        }
    if rec["identity_state"] != enums.IDENTITY_CONFIRMED:
        state = enums.AWAITING_IDENTITY_RESOLUTION
        action = ("Recover an independently sourced street address and telephone "
                  "for this property before any policy work binds to it.")
    elif not rec["official_url"].strip():
        state = enums.AWAITING_OFFICIAL_URL
        action = ("Recover the property-level first-party or brand property URL "
                  "(and its property code) before attempting capture.")
    else:
        state = enums.AWAITING_POLICY_OBSERVATION
        action = ("Open the bound official page and record the pet policy, or its "
                  "absence, verbatim.")
    return {
        "identity_key": rec["identity_key"],
        "canonical_name": rec["canonical_name"],
        "slug": rec["slug"], "city": rec["city"], "state": rec["state"],
        "postal_code": rec["postal_code"],
        "final_state": state, "resolved": False,
        "next_action": action,
        "next_action_source": "identity_census/cincinnati-oh.json",
        "determined_by": WORK_ORDER, "updated_at": AS_OF,
        "official_url": rec["official_url"], "state_override_reason": "",
    }


#: Brand hosts that answer an automated fetcher with 403 and need an attended
#: browser. Recorded as a lane, never as ACCESS_BLOCKED: this programme has
#: repeatedly read these same pages in an attended session, so calling them
#: blocked would be a false terminal state.
_WALLED_BRAND_HOSTS = ("marriott.com", "hilton.com", "ihg.com", "choicehotels.com",
                       "wyndhamhotels.com", "bestwestern.com", "hyatt.com",
                       "redroof.com")

#: Identities that already carry a pet-policy quote from an earlier run. The
#: quote is a transcription with no retained artifact, so the row still needs a
#: capture -- but it needs a re-capture and a fee confirmation, not a first look.
TRANSCRIBED_POLICY_KNOWN: Tuple[str, ...] = (
    "countryside inn and suites mount orab",
)


def url_grade(url: str) -> str:
    if not url.strip():
        return "MISSING_URL"
    host = re.sub(r"^https?://", "", url).split("/")[0].lower()
    if any(brand in host for brand in _WALLED_BRAND_HOSTS):
        return "BRAND_PROPERTY_PAGE"
    return "EXACT_PROPERTY_FIRST_PARTY"


def capture_lane(item: Mapping) -> str:
    """The full capture-readiness vocabulary, derived, never guessed."""
    state = item["final_state"]
    if state == enums.AWAITING_IDENTITY_RESOLUTION:
        return "IDENTITY_REVIEW"
    if state == enums.AWAITING_OFFICIAL_URL:
        return "PROPERTY_LEVEL_URL_RECOVERY"
    if item["identity_key"] in TRANSCRIBED_POLICY_KNOWN:
        return "STRUCTURED_POLICY_ALREADY_KNOWN"
    if url_grade(item["official_url"]) == "BRAND_PROPERTY_PAGE":
        return "ATTENDED_POLICY_SURFACE"
    return "POLICY_OBSERVATION_REQUIRED"


def boundary_review(identities: Sequence[Mapping]) -> Dict:
    """Re-derive the cross-market boundary check the registry cites.

    The registry's ``_boundary_note`` has pointed at
    ``cincinnati-dayton-boundary-review.json`` since the market was created, and
    that file existed in no git ref -- an authority citing an artifact nobody
    could read. It is regenerated here from the committed censuses so the
    citation resolves and the claim is checkable rather than asserted.
    """
    collisions: List[Dict] = []
    neighbours: Dict[str, int] = {}
    mine_name = {r["identity_key"]: r for r in identities}
    mine_street = collections.defaultdict(list)
    mine_phone = collections.defaultdict(list)
    for rec in identities:
        if rec["address"].strip() and rec["postal_code"]:
            mine_street["%s|%s" % (norm_addr(rec["address"]), rec["postal_code"])].append(rec)
        digits = re.sub(r"\D", "", rec["phone"] or "")
        if len(digits) >= 10:
            mine_phone[digits[-10:]].append(rec)

    for market_id in NEIGHBOUR_MARKETS:
        path = PKG / "identity_census" / ("%s.json" % market_id)
        if not path.is_file():
            continue
        rows = json.loads(path.read_text(encoding="utf-8-sig"))["hotels"]
        neighbours[market_id] = len(rows)
        for row in rows:
            key = row.get("identity_key") or ptf_identity_key(row["canonical_name"])
            reasons = []
            if key in mine_name:
                reasons.append("identity_key")
            street = "%s|%s" % (norm_addr(row.get("address", "")), row.get("postal_code", ""))
            if row.get("address", "").strip() and street in mine_street:
                reasons.append("street_identity")
            digits = re.sub(r"\D", "", row.get("phone", "") or "")
            if len(digits) >= 10 and digits[-10:] in mine_phone:
                reasons.append("phone")
            if reasons:
                collisions.append({"market_id": market_id,
                                   "canonical_name": row["canonical_name"],
                                   "city": row.get("city", ""), "state": row.get("state", ""),
                                   "matched_on": reasons})

    reviewed = [
        {"identity_key": r["identity_key"], "canonical_name": r["canonical_name"],
         "city": r["city"], "state": r["state"], "postal_code": r["postal_code"],
         "corridor": r["corridor"], "neighbour_match": "NONE",
         "owner": MARKET_ID}
        for r in identities
        if (r["corridor"] or "").endswith(("middletown-monroe", "lebanon-warren-county"))
    ]
    return {
        "schema": "ptf-market-boundary-review/1.1",
        "work_order": WORK_ORDER,
        "market_id": MARKET_ID,
        "as_of": AS_OF,
        "method": (
            "Every Cincinnati identity is compared against every other committed "
            "market census on three keys: the canonical identity key, "
            "normalised street address plus postal code, and the last ten "
            "digits of the telephone number. The northern Warren and Butler "
            "County corridors that abut Dayton are additionally listed row by "
            "row, because those are the rows a boundary dispute would be about."),
        "neighbour_censuses": neighbours,
        "cincinnati_identities": len(identities),
        "cross_market_collisions": len(collisions),
        "collisions": collisions,
        "dayton_boundary_note": (
            "Dayton's own discovery configuration excludes Warren County by "
            "name -- 'Warren County (Springboro, Cincinnati market) is south of "
            "the min_lat boundary' -- and none of Dayton's registered corridors "
            "covers Middletown, Monroe, Franklin or Lebanon. Cincinnati owns "
            "them; no Dayton identity moves, and none was moved."),
        "boundary_corridor_rows": len(reviewed),
        "reviewed": reviewed,
        "action_taken": (
            "NONE. No identity in any other market was moved, renamed or "
            "deleted by this work order."),
    }


def write_json(path: Path, document: Mapping) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8", newline="\n")


def build(write: bool = True) -> Dict:
    listings = json.loads(SOURCE_LISTINGS.read_text(encoding="utf-8-sig"))["listings"]
    prior_doc = json.loads(PRIOR_CENSUS_PATH.read_text(encoding="utf-8-sig"))
    prior = prior_doc["hotels"]

    candidates, fnb = build_candidates(listings)
    matched, _ = reconcile(candidates, prior)
    identities, ledger = build_identities(candidates, matched, prior,
                                          PRIOR_IDENTITY_RULINGS)
    for row in fnb:
        ledger.append({
            "ledger_id": "CIN-FNB-%03d" % (len(ledger) + 1),
            "candidate_name": row["listing_name"], "identity_key": "",
            "address": row.get("address", ""), "city": row.get("city", ""),
            "state": row.get("state", ""), "postal_code": row.get("postal_code", ""),
            "phone": row.get("phone", ""), "sources": [row["source"]],
            "source_urls": [row["source_url"]],
            "source_listing_names": [row["listing_name"]],
            "disposition": NOT_LODGING,
            "disposition_reason": (
                "A restaurant or bar listed at its host hotel's street address. "
                "Not a lodging identity; recorded so the listing is accounted "
                "for rather than silently absorbed into the hotel."),
            "prior_identity_key": "", "postal_code_defect": "",
        })

    identities.sort(key=lambda r: r["identity_key"])
    geo = assign_geography(identities)
    shared = mark_collisions(identities)

    items = [partition_item(r) for r in identities]
    counts = collections.Counter(i["final_state"] for i in items)

    census_doc = {
        "schema": enums.CENSUS_SCHEMA,
        "market_id": MARKET_ID,
        "identity_key_contract": "ptf_identity_key/1.0",
        "identity_contract": "ptf-identity-evidence/1.0",
        "work_order": WORK_ORDER,
        "captured_at": AS_OF,
        "note": (
            "Rebuilt from independent discovery, not from the corridor registry. "
            "Source listings are committed verbatim in "
            "cincinnati_source_listings_001.json and every identity's disposition "
            "is recorded in cincinnati_candidate_ledger_001.json. Nothing is "
            "published: policy_state is POLICY_NOT_VERIFIED on every row and no "
            "pet-policy fact is asserted anywhere in this file."),
        "source_authorities": [
            "launch_packages/pettripfinder/cincinnati_source_listings_001.json",
            "launch_packages/pettripfinder/cincinnati_candidate_ledger_001.json",
            "worker/ptf-cincinnati-market-001:identity_census/cincinnati-oh.json",
        ],
        "count": len(identities),
        "identity_state_counts": dict(sorted(
            collections.Counter(r["identity_state"] for r in identities).items())),
        "lodging_state_counts": dict(sorted(
            collections.Counter(r["lodging_state"] for r in identities).items())),
        "collision_audit": {
            "shared_address_identities": shared,
            "note": ("Shared street addresses are recorded, never merged: two "
                     "hotel brands in one building are two identities."),
        },
        "geography": {
            "assigned": len(identities) - geo["unassigned"],
            "unassigned": geo["unassigned"],
            "ambiguous": geo["conflicts"],
            "note": ("Corridors come from scripts.pettripfinder.markets.assignment, "
                     "the single assignment authority. An unassigned identity is a "
                     "reported result, not a failure: it publishes normally and "
                     "simply has no corridor page yet."),
        },
        "hotels": identities,
    }

    partition_doc = {
        "schema": enums.PARTITION_SCHEMA,
        "work_order": WORK_ORDER,
        "market_id": MARKET_ID,
        "as_of": AS_OF,
        "note": (
            "Every Cincinnati identity is unresolved except the guesthouses and "
            "short-term rentals ruled out of the current category. No policy "
            "evidence exists for this market, so no publication state is "
            "invented for it."),
        "source_authorities": [
            "launch_packages/pettripfinder/identity_census/cincinnati-oh.json",
            "launch_packages/pettripfinder/cincinnati_candidate_ledger_001.json",
        ],
        "count": len(items),
        "final_state_counts": dict(sorted(counts.items())),
        "final_state_meanings": {
            state: __import__(
                "scripts.pettripfinder.contracts.partition", fromlist=["STATE_MEANINGS"]
            ).STATE_MEANINGS[state] for state in sorted(counts)},
        "items": items,
    }

    queue_rows = []
    by_key = {r["identity_key"]: r for r in identities}
    for item in items:
        if item["resolved"]:
            continue
        rec = by_key[item["identity_key"]]
        queue_rows.append({
            "row_id": "CIN-Q-%03d" % (len(queue_rows) + 1),
            "identity_key": item["identity_key"],
            "hotel": item["canonical_name"],
            "city": item["city"], "state": item["state"],
            "postal_code": item["postal_code"],
            "corridor": rec["corridor"] or "(unassigned)",
            "official_url": item["official_url"],
            "url_grade": url_grade(item["official_url"]),
            "blocker": item["final_state"],
            "capture_lane": capture_lane(item),
            "next_action": item["next_action"],
            "review_status": "NOT_STARTED",
        })

    queue_doc = {
        "schema": "ptf-market-founder-review-queue/1.0",
        "work_order": WORK_ORDER,
        "market_id": MARKET_ID,
        "generated_at": AS_OF,
        "note": ("Rebuilt from the current census and partition. The prior "
                 "121-row queue is a discovery lead, never authority: it carried "
                 "no field capable of recording a review outcome, so no row in it "
                 "was ever reviewed."),
        "count": len(queue_rows),
        "lane_counts": dict(sorted(
            collections.Counter(r["capture_lane"] for r in queue_rows).items())),
        "rows": queue_rows,
    }

    boundary = boundary_review(identities)

    if write:
        write_json(CENSUS_PATH, census_doc)
        write_json(PARTITION_PATH, partition_doc)
        write_json(BOUNDARY_PATH, boundary)
        write_json(QUEUE_PATH, queue_doc)
        write_json(LEDGER_PATH, {
            "schema": "ptf-market-candidate-ledger/1.0",
            "work_order": WORK_ORDER, "market_id": MARKET_ID, "as_of": AS_OF,
            "note": ("One row per source-listing candidate and per prior census "
                     "identity. Every row carries exactly one disposition and the "
                     "reason for it; no identity leaves the census without one."),
            "source_listings": "launch_packages/pettripfinder/cincinnati_source_listings_001.json",
            "count": len(ledger),
            "disposition_counts": dict(sorted(
                collections.Counter(r["disposition"] for r in ledger).items())),
            "rows": ledger,
        })
    return {"identities": identities, "ledger": ledger, "items": items,
            "candidates": candidates, "geo": geo, "prior": prior,
            "boundary": boundary, "queue": queue_rows}


def main(argv: Sequence[str] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    result = build(write=not args.dry_run)
    ledger_counts = collections.Counter(r["disposition"] for r in result["ledger"])
    state_counts = collections.Counter(i["final_state"] for i in result["items"])
    out = sys.stdout
    out.write("%s%s\n" % (WORK_ORDER, "  (dry run)" if args.dry_run else ""))
    out.write("  prior census      %d\n" % len(result["prior"]))
    out.write("  candidates        %d\n" % len(result["candidates"]))
    out.write("  final census      %d\n" % len(result["identities"]))
    out.write("  unassigned        %d\n" % result["geo"]["unassigned"])
    out.write("  ledger rows       %d\n" % len(result["ledger"]))
    for key, value in sorted(ledger_counts.items()):
        out.write("      %-40s %d\n" % (key, value))
    out.write("  partition\n")
    for key, value in sorted(state_counts.items()):
        out.write("      %-40s %d\n" % (key, value))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
