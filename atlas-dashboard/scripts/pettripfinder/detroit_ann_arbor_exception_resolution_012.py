# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-FOUNDER-EXCEPTIONS-AND-DISPLAY-REPAIR-012, Phases 1-3.

Resolves the five zero-cost exceptions order 011 left open, from evidence this
project already owns. NO PROVIDER IS CALLED.

EVERY ANSWER COMES OUT OF A DOCUMENT ALREADY ON DISK. The rendered first-party
pages bought in passes 008/009/010 are still persisted with their sha256, and
each one carries the property's OWN structured data. That is first-party
evidence and it is already paid for; re-fetching it would be buying a second
copy of a page whose bytes are in hand.

PHASE 1 -- the two policy holds. The founder ruled both VERIFIED_NO_PETS. Each
is recorded as an IDENTITY-SPECIFIC disposition against the exact quote, and
THE SHARED READER IS NOT TOUCHED. That is the whole point of the instruction:
"Sorry not other pets are allowed" is one property's malformed wording, and
teaching the global reader to accept "not other pets" would silently re-decide
every row in every market that has ever carried that phrasing.

PHASE 2 -- the two missing addresses, read from each property's own
``PostalAddress`` JSON-LD. Nothing is inferred: if a document does not state a
street and a postal code, the identity stays withheld.

PHASE 3 -- Troy. Both pages report the same street, and each reports its OWN
``hotelCode`` (dttoy, dttry), its own marketed name and its own telephone. That
is a dual-brand building: TWO DISTINCT MARKETED IDENTITIES on one campus, which
is what the reviewed same-campus mechanism exists to record. The global address
dedup rule is NOT weakened -- a reviewed exception is added for this one
address, and nothing wider.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import publication_guard as PG          # noqa: E402
from scripts.pettripfinder.brightdata import policy_surface as PS  # noqa: E402
from scripts.pettripfinder.hotel_exclusions import address_key     # noqa: E402

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-FOUNDER-EXCEPTIONS-AND-DISPLAY-REPAIR-012"
DECISION_DATE = "2026-08-29"
FOUNDER = "jfields80"

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
CANDIDATES = LP / "detroit_ann_arbor_reconciled_candidates_011.json"
CENSUS_PATH = LP / "identity_census" / ("%s.json" % MARKET)
DISPOSITIONS_PATH = LP / "detroit_ann_arbor_founder_dispositions_012.json"
ADDRESS_PATH = LP / "detroit_ann_arbor_address_recovery_012.json"
TROY_PATH = LP / "detroit_ann_arbor_troy_same_campus_012.json"

#: Founder dispositions, verbatim from the work order. Keyed by identity and
#: bound to the exact quote each was ruled on -- a disposition that does not
#: name the words it ruled on would silently cover a page that later changed.
DISPOSITIONS = {
    "days inn and suites by wyndham madison heights mi": {
        "decision": "VERIFIED_NO_PETS",
        "quote_must_contain": "Sorry not other pets are allowed",
        "founder_reasoning":
            "Treat 'not other pets' as the property's malformed wording for "
            "its explicit negative pet statement.",
        "scope": "THIS IDENTITY ONLY. The shared reader is not widened: the "
                 "phrase stays unresolved everywhere else until a founder "
                 "rules on it there too.",
    },
    "quality inn and suites banquet center livonia": {
        "decision": "VERIFIED_NO_PETS",
        "quote_must_contain": "Only service animals are permitted",
        "founder_reasoning":
            "An affirmative property-specific statement that only service "
            "animals are permitted.",
        "scope": "THIS IDENTITY ONLY. The shared reader still declines to turn "
                 "a service-animal sentence into a pet policy.",
    },
}

ADDRESS_RECOVERY = ("comfort suites auburn hills detroit",
                    "staybridge suites auburn hills")
TROY = ("hotel indigo detroit north troy", "even hotel detroit north troy")


class Stop(Exception):
    """Any failure stops the run. A partial authority write is worse than none."""


def load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_lf(path: Path, doc) -> None:
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8", newline="\n")


def candidate_rows() -> Dict[str, Dict]:
    doc = load(CANDIDATES)
    return {row["identity_key"]: row
            for group in ("clean_candidates", "rejected_candidates", "holds")
            for row in doc[group]}


def verified_document(row: Dict) -> Tuple[str, str]:
    """(html, sha256) -- re-hashed from disk before it is believed."""
    reading = row["reading"]
    path = _REPO_ROOT / reading["document_artifact"]
    if not path.is_file():
        raise Stop("%s: the source document is gone" % row["identity_key"])
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    recorded = reading.get("document_sha256") or ""
    if recorded and digest != recorded:
        raise Stop("%s: the document sha256 does not reproduce"
                   % row["identity_key"])
    return (raw.decode("utf-8", errors="replace"), digest)


def verified_block(row: Dict) -> Tuple[str, str]:
    reading = row["reading"]
    path = _REPO_ROOT / reading["block_artifact"]
    if not path.is_file():
        raise Stop("%s: the persisted block is gone" % row["identity_key"])
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    recorded = reading.get("block_sha256") or ""
    if recorded and digest != recorded:
        raise Stop("%s: the block sha256 does not reproduce"
                   % row["identity_key"])
    return (raw.decode("utf-8-sig", errors="replace"), digest)


def postal_address(html: str) -> Optional[Dict]:
    """The property's own PostalAddress, or None. Never inferred."""
    node = PS.any_hotel_jsonld(html)
    if not node:
        return None
    address = node.get("address")
    if not isinstance(address, dict):
        return None
    street = str(address.get("streetAddress") or "").strip()
    postal = str(address.get("postalCode") or "").strip()
    if not street or not postal:
        return None
    return OrderedDict([
        ("street", street), ("postal_code", postal),
        ("locality", str(address.get("addressLocality") or "").strip()),
        ("region", str(address.get("addressRegion") or "").strip()),
        ("stated_name", str(node.get("name") or "").strip()),
        ("telephone", str(node.get("telephone") or "").strip()),
    ])


def hotel_code(html: str) -> str:
    match = re.search(r'"hotelCode"\s*:\s*"([A-Za-z0-9]{3,10})"', html)
    return match.group(1).lower() if match else ""


def page_title(html: str) -> str:
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    return re.sub(r"\s+", " ", match.group(1)).strip() if match else ""


# --------------------------------------------------------------------------- #
# Phase 1
# --------------------------------------------------------------------------- #

def phase1(rows: Dict[str, Dict]) -> Dict:
    recorded = []
    for key, ruling in DISPOSITIONS.items():
        row = rows.get(key)
        if row is None:
            raise Stop("%s: not among the 011 exceptions" % key)
        block, block_sha = verified_block(row)
        _html, document_sha = verified_document(row)
        if ruling["quote_must_contain"] not in block:
            raise Stop("%s: the founder ruled on %r, which is not in the "
                       "persisted block" % (key, ruling["quote_must_contain"]))
        recorded.append(OrderedDict([
            ("identity_key", key),
            ("canonical_name", row["canonical_name"]),
            ("decision", ruling["decision"]),
            ("decided_by", FOUNDER),
            ("decided_at", DECISION_DATE),
            ("authorisation", WORK_ORDER),
            ("exact_quote_ruled_on", ruling["quote_must_contain"]),
            ("full_block_text", block.strip()),
            ("block_sha256", block_sha),
            ("document_sha256", document_sha),
            ("founder_reasoning", ruling["founder_reasoning"]),
            ("scope", ruling["scope"]),
            ("shared_reader_modified", False),
        ]))
    doc = OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-founder-dispositions/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET),
        ("as_of", DECISION_DATE), ("decided_by", FOUNDER),
        ("note",
         "IDENTITY-SPECIFIC founder dispositions on two policy holds. Each is "
         "bound to the exact quote it was ruled on, re-verified against the "
         "persisted block's bytes. THE SHARED READER IS UNCHANGED: widening it "
         "to accept these phrasings would silently re-decide every row in "
         "every market that carries them, which is the opposite of a founder "
         "ruling on one property."),
        ("shared_reader_modified", False),
        ("count", len(recorded)),
        ("dispositions", recorded),
    ])
    write_lf(DISPOSITIONS_PATH, doc)
    return doc


# --------------------------------------------------------------------------- #
# Phase 2
# --------------------------------------------------------------------------- #

def phase2(rows: Dict[str, Dict]) -> Dict:
    census = load(CENSUS_PATH)
    by_key = {row["identity_key"]: row for row in census["hotels"]}
    results, applied = [], 0
    for key in ADDRESS_RECOVERY:
        row = rows.get(key)
        if row is None:
            raise Stop("%s: not among the 011 exceptions" % key)
        html, document_sha = verified_document(row)
        found = postal_address(html)
        entry = OrderedDict([
            ("identity_key", key),
            ("canonical_name", row["canonical_name"]),
            ("evidence", "the property's own PostalAddress JSON-LD, in the "
                         "rendered first-party page already persisted for this "
                         "market"),
            ("document_artifact", row["reading"]["document_artifact"]),
            ("document_sha256", document_sha),
            ("paid_again", False),
        ])
        if found is None:
            entry["result"] = "WITHHELD"
            entry["why"] = ("the document states no street address and postal "
                            "code; nothing is inferred")
            results.append(entry)
            continue
        census_row = by_key.get(key)
        if census_row is None:
            raise Stop("%s: no census row" % key)
        entry["result"] = "RECOVERED"
        entry["recovered"] = found
        entry["census_before"] = OrderedDict([
            ("address", census_row.get("address") or ""),
            ("postal_code", census_row.get("postal_code") or ""),
        ])
        # Only ever FILLS a blank. A stated census value is not overwritten
        # from a page: that would be a silent re-identification, not a repair.
        for field, value in (("address", found["street"]),
                             ("postal_code", found["postal_code"])):
            if str(census_row.get(field) or "").strip():
                entry.setdefault("left_alone", []).append(field)
                continue
            census_row[field] = value
        if not str(census_row.get("phone") or "").strip() and found["telephone"]:
            census_row["phone"] = found["telephone"]
        census_row["street_identity"] = address_key(
            census_row.get("address") or "", census_row.get("postal_code") or "")
        entry["census_after"] = OrderedDict([
            ("address", census_row.get("address") or ""),
            ("postal_code", census_row.get("postal_code") or ""),
            ("street_identity", census_row["street_identity"]),
        ])
        applied += 1
        results.append(entry)

    if applied:
        census["note"] = (
            "%s recovered street addresses for %d identities from their own "
            "first-party PostalAddress JSON-LD, in pages this market had "
            "already paid for and persisted. No provider was called and no "
            "stated value was overwritten -- only blanks were filled. %s"
            % (WORK_ORDER, applied, census.get("note") or ""))
        write_lf(CENSUS_PATH, census)

    doc = OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-address-recovery/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET),
        ("as_of", DECISION_DATE),
        ("provider_calls", 0), ("spend_usd", 0.0),
        ("note",
         "Street addresses read from each property's own structured data in a "
         "document already on disk. Nothing is inferred and nothing stated is "
         "overwritten; an identity whose page does not state an address stays "
         "WITHHELD."),
        ("recovered", applied), ("withheld", len(results) - applied),
        ("results", results),
    ])
    write_lf(ADDRESS_PATH, doc)
    return doc


# --------------------------------------------------------------------------- #
# Phase 3
# --------------------------------------------------------------------------- #

def phase3(rows: Dict[str, Dict]) -> Dict:
    census = {row["identity_key"]: row for row in load(CENSUS_PATH)["hotels"]}
    facts = {row["identity_key"] for row in
             load(LP / ("hotel_policy_facts_%s.json" % MARKET))["hotels"]}
    observed = []
    for key in TROY:
        row = rows.get(key)
        if row is None:
            raise Stop("%s: not among the 011 exceptions" % key)
        html, document_sha = verified_document(row)
        address = postal_address(html) or {}
        observed.append(OrderedDict([
            ("identity_key", key),
            ("canonical_name", row["canonical_name"]),
            ("routed_url", row["canonical_url"]),
            ("document_sha256", document_sha),
            ("page_title", page_title(html)),
            ("hotel_code_in_the_page", hotel_code(html)),
            ("stated_name", address.get("stated_name") or ""),
            ("stated_street", address.get("street") or ""),
            ("stated_postal", address.get("postal_code") or ""),
            ("stated_telephone", address.get("telephone") or ""),
            ("already_published", key in facts),
        ]))

    codes = {row["hotel_code_in_the_page"] for row in observed}
    phones = {row["stated_telephone"] for row in observed}
    streets = {row["stated_street"].lower() for row in observed}
    names = {row["stated_name"] for row in observed}
    distinct = (len(codes) == 2 and "" not in codes
                and len(phones) == 2 and "" not in phones
                and len(names) == 2 and len(streets) == 1)

    determination = "A_TWO_DISTINCT_ENTITIES" if distinct else "B_UNDETERMINED"
    doc = OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-troy-same-campus/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET),
        ("as_of", DECISION_DATE),
        ("provider_calls", 0), ("spend_usd", 0.0),
        ("question", "are these two distinct marketed hotel identities at one "
                     "campus, or one property wearing two identities?"),
        ("determination", determination),
        ("evidence_basis",
         "each property's OWN rendered first-party page, already persisted and "
         "re-hashed here. Both state the same street, and each states its own "
         "hotelCode, its own marketed name and its own telephone number. A "
         "shared street with distinct codes, names and phones is a dual-brand "
         "building -- two businesses at one address. A SHARED TELEPHONE would "
         "have argued the other way, and these differ."),
        ("shared_street", sorted(streets)[0] if streets else ""),
        ("distinct_hotel_codes", sorted(codes)),
        ("distinct_telephones", sorted(phones)),
        ("distinct_marketed_names", sorted(names)),
        ("observed", observed),
        ("consequence",
         "a reviewed same-campus exception is recorded for THIS ADDRESS ONLY. "
         "The global address dedup rule is unchanged: every other collision "
         "still blocks until a human reviews it."
         if distinct else
         "no exception is recorded and Hotel Indigo stays withheld; a merge or "
         "rebrand is a founder decision and is not made here."),
    ])
    write_lf(TROY_PATH, doc)
    if not distinct:
        return doc

    # --- record the reviewed exception ---------------------------------- #
    resolutions = load(PG.RESOLUTIONS_PATH)
    key_for = lambda k: address_key(  # noqa: E731
        census[k].get("address") or "", census[k].get("postal_code") or "")
    addr_keys = {key_for(k) for k in TROY}
    if len(addr_keys) != 1:
        raise Stop("the two Troy identities do not share one address key: %s"
                   % sorted(addr_keys))
    resolution = OrderedDict([
        ("resolution_id", "res-ihg-dual-brand-575-big-beaver-troy"),
        ("resolution_type", PG.SAME_CAMPUS),
        ("address_key", sorted(addr_keys)[0]),
        ("identities", [
            OrderedDict([
                ("canonical_name", census[key]["canonical_name"]),
                ("category", "pet-friendly-hotels"),
                ("slug", census[key]["slug"]),
                ("official_url", rows[key]["canonical_url"]),
                ("booking_destination", rows[key]["canonical_url"]),
            ]) for key in sorted(TROY, key=lambda k: census[k]["canonical_name"])
        ]),
        ("distinct_reason",
         "A dual-brand IHG building at 575 W Big Beaver Rd. Each property's own "
         "page states a different hotelCode (%s), a different marketed name "
         "and a different telephone number; one brand property code is one "
         "hotel by the brand's own definition. Same category, so the reason is "
         "stated explicitly: these are two marketed hotels sharing a building, "
         "not one hotel listed twice."
         % ", ".join(sorted(codes))),
        ("evidence",
         "first-party rendered pages persisted by this market and re-hashed at "
         "review time: %s" % "; ".join(
             "%s -> %s (hotelCode %s, tel %s)"
             % (row["canonical_name"], row["document_sha256"][:16],
                row["hotel_code_in_the_page"], row["stated_telephone"])
             for row in observed)),
        ("reviewer_id", FOUNDER),
        ("reviewed_at", DECISION_DATE),
        ("work_order", WORK_ORDER),
    ])
    resolution["resolution_hash"] = PG.resolution_hash(resolution)
    if any(r["resolution_id"] == resolution["resolution_id"]
           for r in resolutions["resolutions"]):
        resolutions["resolutions"] = [
            r for r in resolutions["resolutions"]
            if r["resolution_id"] != resolution["resolution_id"]]
    resolutions["resolutions"].append(resolution)
    resolutions["note"] = (
        "Reviewed decisions that two identities sharing one street address are "
        "distinct businesses. Without a record here an address collision "
        "blocks publication: the guard treats a shared address as UNREVIEWED, "
        "never as an automatic duplicate and never as an automatic pass. A "
        "resolution asserts nothing about either property's policy.")
    resolutions.pop("market", None)
    resolutions["markets"] = sorted(
        {"columbus-oh", MARKET})
    write_lf(PG.RESOLUTIONS_PATH, resolutions)
    PG.load_resolutions()          # re-validate what was just written
    doc["resolution_recorded"] = resolution["resolution_id"]
    write_lf(TROY_PATH, doc)
    return doc


def run() -> None:
    rows = candidate_rows()
    one = phase1(rows)
    print("=== Phase 1: founder dispositions on the two holds ===")
    for entry in one["dispositions"]:
        print("  %-44s -> %s" % (entry["canonical_name"][:44],
                                 entry["decision"]))
    print("  shared reader modified:", one["shared_reader_modified"])

    two = phase2(rows)
    print()
    print("=== Phase 2: address recovery (first-party, $0) ===")
    for entry in two["results"]:
        if entry["result"] == "RECOVERED":
            print("  %-38s %s, %s"
                  % (entry["canonical_name"][:38],
                     entry["recovered"]["street"],
                     entry["recovered"]["postal_code"]))
        else:
            print("  %-38s WITHHELD -- %s"
                  % (entry["canonical_name"][:38], entry["why"]))

    three = phase3(rows)
    print()
    print("=== Phase 3: Troy same-campus review ===")
    print("  determination:", three["determination"])
    print("  shared street:", three["shared_street"])
    print("  hotel codes  :", three["distinct_hotel_codes"])
    print("  telephones   :", three["distinct_telephones"])
    if three.get("resolution_recorded"):
        print("  recorded     :", three["resolution_recorded"])
    print()
    print("wrote", DISPOSITIONS_PATH.name, ADDRESS_PATH.name, TROY_PATH.name)


if __name__ == "__main__":
    try:
        run()
    except Stop as stop:
        raise SystemExit("STOP: %s" % stop)
