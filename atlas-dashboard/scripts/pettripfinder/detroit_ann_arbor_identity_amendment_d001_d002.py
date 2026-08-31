# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-ROUTING-EXPANSION-004 identity-decision follow-up.

Applies the founder's two explicit identity decisions on the findings
ROUTING-EXPANSION-004 (062d7ed) surfaced but did not itself resolve:

  D001. Homewood Suites Novi duplicate -> CONFIRMED_DUPLICATE. "Homewood
        Suites by Hilton Novi" (added by IDENTITY-ROUTING-REPAIR-001) and
        "Homewood Suites by Hilton Novi Detroit" (added later by CENSUS-
        COMPLETENESS-003 under a second name, without recognizing the
        existing row) bind the identical hilton.com URL and the same
        address/phone modulo formatting -- one physical hotel, not two.
        "Homewood Suites by Hilton Novi" stays canonical (it already
        carries the market's only ROUTING_CONFIRMED record for this
        property, written by ROUTING-EXPANSION-004); the later duplicate
        is retired from the active census/partition/queue via the
        candidate-ledger `disposition="duplicate"` mechanism (the same
        real, precedented mechanism IDENTITY-REPAIR-PASS2-001 used for a
        genuinely-closed hotel, applied here to its sibling case). No
        second route is created; none existed for the duplicate to begin
        with -- ROUTING-EXPANSION-004 had already excluded it from
        routing for exactly this reason.

  D002. Best Western Greenfield Inn -> ADDRESS_HYGIENE_ONLY. Its census
        `city` has read "Dearborn" since Phase 1; bestwestern.com's own
        property page places the identical address/phone in Allen Park,
        MI. Corrected in place: `city` becomes "Allen Park". "Allen Park"
        is not in any corridor's `included_cities` (a prior pass already
        boundary-excluded a *different* Allen Park candidate for exactly
        that reason), so re-deriving this row's corridor by city match
        would make it UNASSIGNED under `assign_hotels(fail_closed=True)`
        -- a real regression from its current, correct membership in the
        Dearborn corridor. The market config gets one narrow addition
        instead: this single hotel's identity_key on the Dearborn
        corridor's `explicit_hotel_ids`, so assignment now resolves via
        the TIER_EXPLICIT tier (basis="explicit", value=identity_key) --
        honest, provable against the registry, and does not widen the
        corridor's city-matching for any other Allen Park property.
        identity_key, street address, ZIP, phone, property_code and
        official_property_url are all preserved byte-identical.

No pet-policy fact is read, inferred, or recorded. published=7 and
verified_no_pets=7 are frozen and asserted unchanged. Detroit's routing
shard is untouched by D002 (no route references city) and needs no new
record for D001 (the duplicate never had one); both are reverified valid
after the census mutation and the global authority check is re-run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.contracts import census as CENSUS               # noqa: E402
from scripts.pettripfinder.contracts import enums                           # noqa: E402
from scripts.pettripfinder.contracts import partition as PART               # noqa: E402
from scripts.pettripfinder.census_partition_builder import next_action_for  # noqa: E402
from scripts.pettripfinder.markets import assign_hotels                    # noqa: E402
from scripts.pettripfinder.markets.contract import parse_market             # noqa: E402
from scripts.pettripfinder import identity_routing as IR                    # noqa: E402
from scripts.pettripfinder import market_authority as MA                    # noqa: E402

WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-ROUTING-EXPANSION-004-IDENTITY-D001-D002"
PRIOR_COMMIT = "062d7ed"
MARKET = "detroit-ann-arbor-mi"
AS_OF = "2026-08-17"
FOUNDER = "jfields80"

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
CENSUS_PATH = LP / "identity_census" / ("%s.json" % MARKET)
PARTITION_PATH = LP / "detroit_ann_arbor_final_partition_001.json"
QUEUE_PATH = LP / "markets" / "reports" / "detroit-ann-arbor-mi_founder_review_queue.json"
LEDGER_PATH = LP / "markets" / "reports" / "detroit-ann-arbor-mi_duplicate_ledger.json"
MARKET_CONFIG_PATH = LP / "markets" / ("%s.json" % MARKET)
EVIDENCE_PATH = LP / "detroit_ann_arbor_identity_amendment_d001_d002.json"

CANONICAL_KEY = "homewood suites by hilton novi"
DUPLICATE_KEY = "homewood suites by hilton novi detroit"

GREENFIELD_KEY = "best western greenfield inn"
GREENFIELD_NEW_CITY = "Allen Park"


def load_json(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_lf(path: Path, doc) -> None:
    text = json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
    path.write_text(text.replace("\r\n", "\n"), encoding="utf-8", newline="\n")


def apply() -> Dict:
    census_doc = load_json(CENSUS_PATH)
    partition_doc = load_json(PARTITION_PATH)
    queue_doc = load_json(QUEUE_PATH)
    ledger_doc = load_json(LEDGER_PATH)
    market_config_doc = load_json(MARKET_CONFIG_PATH)

    hotels = census_doc["hotels"]
    by_key = {r["identity_key"]: r for r in hotels}
    for key in (CANONICAL_KEY, DUPLICATE_KEY, GREENFIELD_KEY):
        if key not in by_key:
            raise SystemExit("STOP: %r not in committed census" % key)

    touched = {DUPLICATE_KEY, GREENFIELD_KEY}
    untouched_before = [r for r in hotels if r["identity_key"] not in touched]

    # ---- D001: retire the duplicate ----
    duplicate_row = by_key.pop(DUPLICATE_KEY)
    hotels[:] = [r for r in hotels if r["identity_key"] != DUPLICATE_KEY]

    # ---- D002: Greenfield Inn city correction ----
    greenfield_row = by_key[GREENFIELD_KEY]
    old_city = greenfield_row["city"]
    old_corridor = greenfield_row["corridor"]
    old_address = greenfield_row["address"]
    old_postal = greenfield_row["postal_code"]
    old_phone = greenfield_row["phone"]
    old_url = greenfield_row["official_url"]
    greenfield_row["city"] = GREENFIELD_NEW_CITY
    greenfield_row["observed_at"] = AS_OF
    greenfield_row["provenance"] = (
        "%s: address-hygiene correction, city Dearborn -> Allen Park "
        "(bestwestern.com's own property page; address/ZIP/phone/URL "
        "unchanged, already correct)" % WORK_ORDER)

    # Market config: add the one-hotel explicit override so the corridor
    # membership this row already correctly had survives the city fix
    # without widening Dearborn's city-matching to any other Allen Park
    # property.
    dearborn_corridor = next(
        c for c in market_config_doc["corridors"]
        if c["corridor_id"] == "%s__dearborn" % MARKET)
    if GREENFIELD_KEY not in dearborn_corridor["explicit_hotel_ids"]:
        dearborn_corridor["explicit_hotel_ids"].append(GREENFIELD_KEY)

    census_doc["count"] = len(hotels)
    census_doc["work_order"] = WORK_ORDER
    census_doc["captured_at"] = AS_OF

    issues = CENSUS.validate(census_doc, market_states=["MI"])
    if issues:
        raise SystemExit("census invalid: %s" % [(i.path, i.code, i.detail) for i in issues])

    untouched_after = [r for r in hotels if r["identity_key"] not in touched]
    if untouched_before != untouched_after:
        raise SystemExit("STOP: an unrelated census row changed")

    # Re-derive Greenfield's corridor assignment against the amended config
    # (in-memory, not yet written to disk -- a dry run must see the same
    # result a real apply would).
    market = parse_market(market_config_doc, source=str(MARKET_CONFIG_PATH))
    assignment = assign_hotels(
        market, [{"name": GREENFIELD_KEY, "city": GREENFIELD_NEW_CITY,
                 "state": "MI", "postal_code": old_postal}],
        fail_closed=True)
    corridors = assignment.corridor_of.get(GREENFIELD_KEY) or ()
    if not corridors:
        raise SystemExit("STOP: Greenfield Inn is unassigned after the city correction")
    new_corridor = corridors[0]
    if new_corridor != old_corridor:
        raise SystemExit(
            "STOP: Greenfield Inn's corridor changed (%r -> %r) -- this "
            "amendment is address-hygiene only" % (old_corridor, new_corridor))
    basis, value = assignment.basis_of[GREENFIELD_KEY]
    greenfield_row["corridor"] = new_corridor
    greenfield_row["assignment_basis"] = basis
    greenfield_row["assignment_value"] = value

    # Preserved-field guard: exactly what D002 requires untouched.
    if (greenfield_row["address"], greenfield_row["postal_code"],
            greenfield_row["phone"], greenfield_row["official_url"],
            greenfield_row["identity_key"]) != (
            old_address, old_postal, old_phone, old_url, GREENFIELD_KEY):
        raise SystemExit("STOP: address-hygiene amendment touched a preserved field")

    # ---- Partition ----
    items = partition_doc["items"]
    p_by_key = {i["identity_key"]: i for i in items}
    p_untouched_before = [i for i in items if i["identity_key"] not in touched]

    items[:] = [i for i in items if i["identity_key"] != DUPLICATE_KEY]
    partition_doc["count"] = len(items)

    greenfield_item = p_by_key[GREENFIELD_KEY]
    greenfield_item["city"] = GREENFIELD_NEW_CITY
    greenfield_item["determined_by"] = WORK_ORDER
    greenfield_item["updated_at"] = AS_OF

    p_untouched_after = [i for i in items if i["identity_key"] not in touched]
    if p_untouched_before != p_untouched_after:
        raise SystemExit("STOP: an unrelated partition row changed")

    counts: Dict[str, int] = {}
    for item in items:
        counts[item["final_state"]] = counts.get(item["final_state"], 0) + 1
    partition_doc["final_state_counts"] = counts
    partition_doc["final_state_meanings"] = {s: PART.STATE_MEANINGS[s] for s in sorted(counts)}
    partition_doc["work_order"] = WORK_ORDER
    partition_doc["as_of"] = AS_OF
    partition_doc["note"] = (
        "%s applied 2 founder identity decisions: 'Homewood Suites by "
        "Hilton Novi Detroit' retired as a confirmed duplicate of "
        "'Homewood Suites by Hilton Novi' (same URL/address/phone); "
        "'Best Western Greenfield Inn' city corrected Dearborn -> Allen "
        "Park (address/ZIP/phone/URL/corridor unchanged, via a one-hotel "
        "explicit corridor override). published=7 and verified_no_pets=7 "
        "UNCHANGED." % WORK_ORDER)

    p_issues = PART.validate(partition_doc)
    if p_issues:
        raise SystemExit("partition invalid: %s" % [(i.path, i.code, i.detail) for i in p_issues])
    rec = PART.reconcile(CENSUS.identity_keys(census_doc), partition_doc, market_id=MARKET)
    rec_issues = PART.reconciliation_issues(rec)
    if rec_issues or not rec.agrees:
        raise SystemExit("reconciliation failed: %s" % (rec_issues,))
    if rec.published != 7 or rec.verified_no_pets != 7:
        raise SystemExit("AUTHORITY FREEZE VIOLATED: published=%s no_pets=%s"
                         % (rec.published, rec.verified_no_pets))

    # ---- Founder review queue ----
    q_items = queue_doc["items"]
    q_untouched_before = [q for q in q_items if q["identity_key"] not in touched]

    q_items[:] = [q for q in q_items if q["identity_key"] != DUPLICATE_KEY]
    queue_doc["count"] = len(q_items)
    queue_doc["as_of"] = AS_OF
    queue_doc["work_order"] = WORK_ORDER

    greenfield_q = next(q for q in q_items if q["identity_key"] == GREENFIELD_KEY)
    payload = json.dumps({k: v for k, v in greenfield_q.items() if k != "row_sha256"},
                         sort_keys=True, ensure_ascii=False)
    greenfield_q["row_sha256"] = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    q_untouched_after = [q for q in q_items if q["identity_key"] not in touched]
    if q_untouched_before != q_untouched_after:
        raise SystemExit("STOP: an unrelated queue row changed")

    # ---- Duplicate ledger ----
    ledger_items = ledger_doc["items"]
    ledger_items.append(OrderedDict([
        ("identity_key", DUPLICATE_KEY),
        ("canonical_name", duplicate_row["canonical_name"]),
        ("disposition", "duplicate"),
        ("duplicate_of", CANONICAL_KEY),
        ("notes", "%s: founder-confirmed CONFIRMED_DUPLICATE. Identical "
                  "hilton.com official_property_url and the same address/"
                  "phone (modulo 'Dr' vs 'Drive', '248-...' vs '+1 248-...') "
                  "as 'homewood suites by hilton novi', which was added "
                  "earlier (IDENTITY-ROUTING-REPAIR-001) and already carries "
                  "the market's routing record for this property; this row "
                  "was added later (CENSUS-COMPLETENESS-003) without "
                  "recognizing the existing identity. No second route was "
                  "ever created for it." % WORK_ORDER),
        ("source", duplicate_row["source"]),
    ]))
    ledger_doc["counts"]["canonical"] = len(hotels)
    ledger_doc["counts"]["duplicate"] = ledger_doc["counts"].get("duplicate", 0) + 1
    ledger_doc["as_of"] = AS_OF
    ledger_doc["work_order"] = WORK_ORDER

    # ---- Reverify Detroit's routing shard / global authority are still valid ----
    routes = MA.load_market_routes(MARKET)
    census_keys = set(CENSUS.identity_keys(census_doc))
    for r in routes:
        ref_key = r["hotel_ref"].get("identity_key")
        if ref_key and ref_key not in census_keys:
            raise SystemExit(
                "STOP: routing record %r references identity_key %r no "
                "longer in census" % (r["routing_id"], ref_key))
    IR.validate_authority(MA.build_routing_shard(MARKET, routes))

    return dict(census_doc=census_doc, partition_doc=partition_doc, queue_doc=queue_doc,
               ledger_doc=ledger_doc, market_config_doc=market_config_doc, rec=rec,
               counts=counts, duplicate_row=duplicate_row, routes_reverified=len(routes))


def build_evidence_doc(applied: Dict) -> Dict:
    return OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-identity-amendment/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("founder", FOUNDER), ("prior_commit", PRIOR_COMMIT),
        ("note", "Applies the founder's D001/D002 identity decisions on "
                 "findings ROUTING-EXPANSION-004 surfaced but did not "
                 "itself resolve. No pet-policy fact read, inferred, or "
                 "recorded."),
        ("decisions", [
            OrderedDict([
                ("id", "D001"),
                ("canonical_identity_key", CANONICAL_KEY),
                ("retired_identity_key", DUPLICATE_KEY),
                ("founder_decision", "CONFIRMED_DUPLICATE"),
                ("mechanism", "candidate-ledger disposition=duplicate, "
                              "duplicate_of=canonical key"),
                ("second_route_created", False),
                ("no_pets_or_closed_disposition_created", False),
            ]),
            OrderedDict([
                ("id", "D002"),
                ("identity_key", GREENFIELD_KEY),
                ("founder_decision", "ADDRESS_HYGIENE_ONLY"),
                ("city_before", "Dearborn"), ("city_after", GREENFIELD_NEW_CITY),
                ("corridor_unchanged", True),
                ("mechanism", "one-hotel explicit_hotel_ids override on the "
                              "Dearborn corridor config"),
                ("preserved_fields", ["identity_key", "address", "postal_code",
                                      "phone", "official_url", "property_code"]),
            ]),
        ]),
        ("census_before", 183), ("census_after", applied["census_doc"]["count"]),
        ("routing_records_reverified", applied["routes_reverified"]),
        ("reconciliation", OrderedDict([
            ("published", applied["rec"].published),
            ("verified_no_pets", applied["rec"].verified_no_pets),
            ("agrees", applied["rec"].agrees),
        ])),
    ])


def run(do_apply: bool) -> None:
    applied = apply()
    print("HOMEWOOD_DUPLICATE: CONFIRMED_DUPLICATE")
    print("GREENFIELD_CITY: ALLEN_PARK_ADDRESS_HYGIENE")
    print("CENSUS_BEFORE: 183")
    print("CENSUS_AFTER: %d" % applied["census_doc"]["count"])
    print("PUBLISHED: %d" % applied["rec"].published)
    print("VERIFIED_NO_PETS: %d" % applied["rec"].verified_no_pets)
    print("ROUTING_RECORDS_REVERIFIED: %d" % applied["routes_reverified"])

    if not do_apply:
        print("\n(dry run -- no files written; pass --apply to write)")
        return

    write_lf(CENSUS_PATH, applied["census_doc"])
    write_lf(PARTITION_PATH, applied["partition_doc"])
    write_lf(QUEUE_PATH, applied["queue_doc"])
    write_lf(LEDGER_PATH, applied["ledger_doc"])
    write_lf(MARKET_CONFIG_PATH, applied["market_config_doc"])
    write_lf(EVIDENCE_PATH, build_evidence_doc(applied))
    print("\nWROTE: census, partition, queue, ledger, market config, evidence")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()
    run(do_apply=args.apply)


if __name__ == "__main__":
    main()
