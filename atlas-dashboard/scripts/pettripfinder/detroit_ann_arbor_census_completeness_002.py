# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-CENSUS-COMPLETENESS-002.

Additive census-closure audit against the committed 142-identity Detroit-
Ann Arbor census. NOT a rebuild: the 142 rows are asserted byte-identical
before writing anything new. No pet policy was browsed; no policy
authority was touched (published=7, verified_no_pets=7 frozen and
verified unchanged).

Discovery method: re-checked Visit Detroit's and Destination Ann Arbor's
own CVB pages (already-registered Phase 1 sources), then targeted
brand/city web searches for Dearborn, Royal Oak/Birmingham, Livonia,
Troy, Southfield, and Ann Arbor, each new candidate independently
confirmed via the property's own first-party brand page (or, where a
brand page could not be captured this pass, at least two independent
listing sources agreeing on name+address) before being added. WebSearch
budget was exhausted mid-audit; Downtown Detroit, DTW/Romulus (beyond one
Marriott find), Novi/Wixom, and Farmington Hills (beyond one Marriott
find) did NOT get an independent brand-by-brand sweep this pass -- see
REMAINING_BLOCKERS in the report.

19 new CANONICAL_CENSUS rows, 2 BOUNDARY_EXCLUDED (cities not in any
corridor's included_cities -- a corridor-config change is a founder
decision, not something this script makes silently), 1 CLOSED_OR_
CONVERTED (found not-yet-in-census, and already-closed -- retired via
the same 'closed' disposition mechanism as Hawthorn Suites Southfield).
The previously-documented Macomb County cluster (5 hotels) remains
BOUNDARY_EXCLUDED per the standing Phase 1 decision; reconfirmed, not
re-litigated.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.contracts import census as CENSUS                  # noqa: E402
from scripts.pettripfinder.contracts import enums                             # noqa: E402
from scripts.pettripfinder.contracts import partition as PART                 # noqa: E402
from scripts.pettripfinder.census_partition_builder import next_action_for    # noqa: E402
from scripts.pettripfinder.contracts.identity_key import ptf_identity_key     # noqa: E402
from scripts.pettripfinder.markets import assign_hotels, load_markets, market_by_id  # noqa: E402
from scripts.pettripfinder.site_data import normalize_name                    # noqa: E402

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-CENSUS-COMPLETENESS-002"
AS_OF = "2026-08-17"

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
CENSUS_PATH = LP / "identity_census" / ("%s.json" % MARKET)
PARTITION_PATH = LP / "detroit_ann_arbor_final_partition_001.json"
QUEUE_PATH = LP / "markets" / "reports" / "detroit-ann-arbor-mi_founder_review_queue.json"
LEDGER_PATH = LP / "markets" / "reports" / "detroit-ann-arbor-mi_duplicate_ledger.json"
SOURCE_REGISTRY_PATH = LP / "markets" / "reports" / "detroit-ann-arbor-mi_source_registry.json"
EVIDENCE_PATH = LP / "detroit_ann_arbor_census_completeness_002.json"


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").strip().lower()).strip("-")


def _street_identity(address: str, postal_code: str) -> str:
    a = re.sub(r"[^a-z0-9]+", " ", (address or "").strip().lower()).strip()
    p = (postal_code or "").strip()[:5]
    return ("%s|%s" % (a, p)) if a and p else ""


def _c(name, address, city, postal, phone, url, url_shape, source):
    return dict(name=name, address=address, city=city, postal=postal, phone=phone,
               url=url, url_shape=url_shape, source=source)


# ==========================================================================
# 19 new canonical candidates -- each independently confirmed to exist as a
# real, distinct, currently-operating property before being added here.
# ==========================================================================
NEW_CANONICAL = [
    _c("Best Western Premier Detroit Southfield Hotel", "26555 Telegraph Rd",
       "Southfield", "48033", "",
       "https://www.bestwestern.com/en_US/book/hotel-rooms.23171.html",
       "property", "visit_detroit"),
    _c("Detroit Metro Airport Marriott", "30559 Flynn Dr", "Romulus", "48174",
       "+1 734-729-7555",
       "https://www.marriott.com/en-us/hotels/dtwrm-detroit-metro-airport-marriott/overview/",
       "property", "visit_detroit"),
    _c("The Vanguard Ann Arbor, Autograph Collection", "", "Ann Arbor", "", "",
       "https://www.marriott.com/en-us/hotels/dtwaa-the-vanguard-ann-arbor-autograph-collection/overview/",
       "property", "destination_ann_arbor"),
    _c("Residence Inn by Marriott Ann Arbor North", "", "Ann Arbor", "", "",
       "", "none", "chain_locator_002"),
    _c("Residence Inn by Marriott Ann Arbor South", "", "Ann Arbor", "", "",
       "", "none", "chain_locator_002"),
    _c("TownePlace Suites by Marriott Detroit Dearborn", "6141 Mercury Dr",
       "Dearborn", "48126", "", "", "none", "chain_locator_002"),
    _c("SpringHill Suites by Marriott Detroit Dearborn", "6335 Mercury Dr",
       "Dearborn", "48126", "(313) 336-3900",
       "https://www.marriott.com/en-us/hotels/dttsd-springhill-suites-detroit-dearborn/overview/",
       "property", "chain_locator_002"),
    _c("Courtyard by Marriott Detroit Dearborn", "5200 Mercury Dr", "Dearborn",
       "48126", "",
       "https://www.marriott.com/en-us/hotels/dttdb-courtyard-detroit-dearborn/overview/",
       "property", "chain_locator_002"),
    _c("Residence Inn by Marriott Detroit Dearborn", "6275 Mercury Dr",
       "Dearborn", "48126", "", "", "none", "chain_locator_002"),
    _c("Hampton Inn by Hilton Detroit Dearborn", "22324 Michigan Ave",
       "Dearborn", "48124", "",
       "https://www.hilton.com/en/hotels/dttmahx-hampton-detroit-dearborn/",
       "property", "chain_locator_002"),
    _c("Holiday Inn Express & Suites Dearborn SW - Detroit Area",
       "24041 Michigan Ave", "Dearborn", "48124", "(313) 565-1800",
       "https://www.ihg.com/holidayinnexpress/hotels/us/en/dearborn/dttde/hoteldetail",
       "property", "chain_locator_002"),
    _c("Hyatt House Royal Oak/Birmingham", "30955 Woodward Ave", "Royal Oak",
       "48073", "1-248-837-2128",
       "https://www.hyatt.com/hyatt-house/en-US/dtwxr-hyatt-house-royal-oak-birmingham",
       "property", "chain_locator_002"),
    _c("Staybridge Suites Detroit North - Royal Oak", "5150 Coolidge Hwy",
       "Royal Oak", "48073", "",
       "https://www.ihg.com/staybridge/hotels/us/en/royal-oak/dtwro/hoteldetail",
       "property", "chain_locator_002"),
    _c("Best Western Detroit Livonia", "16999 S Laurel Park Dr", "Livonia",
       "48154", "(734) 464-0050",
       "https://www.bestwestern.com/en_US/book/hotel-details.23120.html",
       "property", "chain_locator_002"),
    _c("Hyatt Place Detroit/Livonia", "19300 Haggerty Rd", "Livonia", "48152",
       "(734) 953-9224",
       "https://www.hyatt.com/hyatt-place/en-US/detzl-hyatt-place-detroit-livonia",
       "property", "chain_locator_002"),
    _c("HomeTowne Studios by Red Roof Detroit - Livonia", "11808 Middlebelt Rd",
       "Livonia", "48150", "",
       "https://www.redroof.com/extendedstay/hometownestudios/property/mi/livonia/hts1022",
       "property", "chain_locator_002"),
    _c("Holiday Inn Detroit Northwest - Livonia", "17123 N Laurel Park Dr",
       "Livonia", "48152", "(734) 245-4700",
       "https://www.ihg.com/holidayinn/hotels/us/en/livonia/dttlv/hoteldetail",
       "property", "chain_locator_002"),
    _c("Sonesta Simply Suites Detroit Troy", "2550 Troy Center Dr", "Troy",
       "48084", "",
       "https://www.sonesta.com/sonesta-simply-suites/mi/troy/sonesta-simply-suites-detroit-troy",
       "property", "chain_locator_002"),
    _c("MainStay Suites Southfield-Detroit", "1 Corporate Dr", "Southfield",
       "48076", "",
       "https://www.choicehotels.com/michigan/southfield/mainstay-hotels/mi691",
       "property", "chain_locator_002"),
]

# Cities not in any corridor's included_cities -- assign_hotels would fail
# closed on these. A corridor-config change is a founder decision.
BOUNDARY_REVIEW = [
    dict(name="TownePlace Suites by Marriott Detroit Commerce", city="Commerce Township",
        note="Real Marriott property, ~4.4 mi from Farmington Hills. "
             "'Commerce Township' is not in farmington-hills' included_cities "
             "(['Farmington Hills', 'West Bloomfield']). Adding it would "
             "silently widen the corridor's geographic definition -- a "
             "founder decision, not this script's to make."),
    dict(name="Baymont by Wyndham Ferndale/Royal Oak", city="Ferndale",
        address="11000 West 8 Mile Road", postal="48220",
        note="Real Wyndham property, adjacent to Royal Oak. 'Ferndale' is "
             "not in birmingham-royal-oak-rochester's included_cities. Same "
             "treatment as Commerce Township -- flagged, not silently added "
             "or silently dropped."),
]

# Found not-yet-in-census, and independently confirmed closed.
CLOSED_FOUND = [
    dict(name="Hawthorn Suites by Wyndham Troy", address="2600 Livernois Road",
        city="Troy", postal="48083",
        note="Yelp-confirmed CLOSED (updated December 2025). A different "
             "property from the already-retired Hawthorn Suites by Wyndham "
             "Southfield Detroit -- distinct address, distinct city. Never "
             "canonical in this census; retired straight to the 'closed' "
             "disposition rather than added and then immediately closed."),
]

# Reconfirmed, not re-litigated: the Phase 1 boundary decision on Macomb
# County stands. Still no named corridor in this market covers it.
MACOMB_STILL_EXCLUDED = [
    "Wyndham Garden Sterling Heights", "Hampton Inn & Suites Chesterfield Township",
    "Hyatt Place Utica", "Cambria Hotel Shelby Township",
    "TownePlace Suites by Marriott Detroit Sterling Heights",
]


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=OrderedDict)


def write_lf(path: Path, payload) -> None:
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    path.write_text(text.replace("\r\n", "\n"), encoding="utf-8", newline="\n")


def build() -> Dict:
    market = market_by_id(load_markets(), MARKET)
    census_doc = load_json(CENSUS_PATH)
    partition_doc = load_json(PARTITION_PATH)
    queue_doc = load_json(QUEUE_PATH)
    ledger_doc = load_json(LEDGER_PATH)

    hotels = census_doc["hotels"]
    existing_keys = {r["identity_key"] for r in hotels}
    hotels_before = list(hotels)

    new_rows = []
    for cand in NEW_CANONICAL:
        key = ptf_identity_key(cand["name"])
        if key in existing_keys:
            raise SystemExit("STOP: %r collides with an existing census identity" % cand["name"])
        row = OrderedDict([
            ("identity_key", key), ("canonical_name", cand["name"]),
            ("display_name", cand["name"]), ("slug", _slugify(cand["name"])),
            ("market_id", MARKET), ("address", cand["address"]), ("city", cand["city"]),
            ("state", "MI"), ("postal_code", cand["postal"]), ("phone", cand["phone"]),
            ("identity_state", enums.IDENTITY_CONFIRMED),
            ("lodging_state", enums.LODGING_CONFIRMED),
            ("policy_state", enums.POLICY_NOT_VERIFIED),
            ("collision_state", enums.COLLISION_NONE),
            ("official_url", cand["url"]), ("corridor", ""),
            ("assignment_basis", ""), ("assignment_value", ""),
            ("source", cand["source"]), ("source_id", _slugify(cand["name"])),
            ("observed_at", AS_OF),
            ("provenance", "%s:%s" % (WORK_ORDER, cand["source"])),
            ("normalized_name", normalize_name(cand["name"])), ("former_name", ""),
            ("url_shape", cand["url_shape"]), ("disposition", "canonical"),
            ("street_identity", _street_identity(cand["address"], cand["postal"])),
        ])
        new_rows.append(row)
        existing_keys.add(key)

    assign_rows = [{"name": r["identity_key"], "city": r["city"], "state": r["state"],
                    "postal_code": r["postal_code"]} for r in new_rows]
    assignment = assign_hotels(market, assign_rows, fail_closed=True)
    for row in new_rows:
        corridors = assignment.corridor_of.get(row["identity_key"]) or ()
        if not corridors:
            raise SystemExit("unassigned: %s" % row["canonical_name"])
        row["corridor"] = corridors[0]
        basis, value = assignment.basis_of[row["identity_key"]]
        row["assignment_basis"] = basis
        row["assignment_value"] = value

    hotels.extend(new_rows)
    census_doc["count"] = len(hotels)
    census_doc["work_order"] = WORK_ORDER
    census_doc["captured_at"] = AS_OF

    issues = CENSUS.validate(census_doc, market_states=["MI"])
    if issues:
        raise SystemExit("census invalid: %s" % [(i.path, i.code, i.detail) for i in issues])

    untouched_after = [r for r in hotels if r["identity_key"] not in
                       {r2["identity_key"] for r2 in new_rows}]
    if hotels_before != untouched_after:
        raise SystemExit("STOP: an existing census row changed")

    # ---- partition: append one AWAITING_* row per new identity ----
    items = partition_doc["items"]
    items_before = list(items)
    for row in new_rows:
        state = (enums.AWAITING_POLICY_OBSERVATION if row["official_url"]
                else enums.AWAITING_OFFICIAL_URL)
        items.append(OrderedDict([
            ("identity_key", row["identity_key"]), ("canonical_name", row["canonical_name"]),
            ("slug", row["slug"]), ("city", row["city"]), ("state", row["state"]),
            ("postal_code", row["postal_code"]), ("final_state", state),
            ("resolved", False), ("next_action", next_action_for(state)),
            ("next_action_source", "identity_census/detroit-ann-arbor-mi.json"),
            ("determined_by", WORK_ORDER), ("updated_at", AS_OF),
            ("official_url", row["official_url"]), ("state_override_reason", ""),
        ]))
    if items[:len(items_before)] != items_before:
        raise SystemExit("STOP: an existing partition row changed")
    partition_doc["count"] = len(items)
    counts: Dict[str, int] = {}
    for item in items:
        counts[item["final_state"]] = counts.get(item["final_state"], 0) + 1
    partition_doc["final_state_counts"] = counts
    partition_doc["final_state_meanings"] = {s: PART.STATE_MEANINGS[s] for s in sorted(counts)}
    partition_doc["work_order"] = WORK_ORDER
    partition_doc["as_of"] = AS_OF
    partition_doc["note"] = ("%s added 19 canonical identities found materially "
                             "missing from the committed 142 (Dearborn +6, "
                             "Livonia +4, Ann Arbor +3, Royal Oak +2, "
                             "Southfield +2, DTW/Romulus +1, Troy +1). "
                             "published=7 and verified_no_pets=7 UNCHANGED -- "
                             "no policy authority was touched." % WORK_ORDER)

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

    # ---- founder review queue: append the newly unresolved rows ----
    q_items = queue_doc["items"]
    q_before = list(q_items)
    existing_batches = [q["batch"] for q in q_items if "batch" in q]
    seq = len(q_items)
    for row in new_rows:
        seq += 1
        item = next(i for i in items if i["identity_key"] == row["identity_key"])
        batch = "batch-%03d" % (((seq - 1) // 10) + 1)
        q_items.append(OrderedDict([
            ("row_number", seq), ("identity_key", row["identity_key"]),
            ("hotel_id", row["identity_key"]), ("canonical_name", row["canonical_name"]),
            ("address", row["address"]), ("phone", row["phone"]),
            ("official_candidate_url", row["official_url"]), ("corridor", row["corridor"]),
            ("current_classification", item["final_state"]),
            ("blocking_reason", item["final_state"]),
            ("requested_evidence", "citable pet-policy artifact from the property's "
             "own page" if row["official_url"] else
             "property-level official URL and a citable pet-policy artifact"),
            ("next_action", item["next_action"]), ("batch", batch),
            ("review_status", "NOT_STARTED"),
        ]))
        payload = json.dumps({k: v for k, v in q_items[-1].items() if k != "row_sha256"},
                             sort_keys=True, ensure_ascii=False)
        q_items[-1]["row_sha256"] = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    if q_items[:len(q_before)] != q_before:
        raise SystemExit("STOP: an existing queue row changed")
    queue_doc["count"] = len(q_items)
    queue_doc["as_of"] = AS_OF
    queue_doc["work_order"] = WORK_ORDER

    # ---- duplicate/disposition ledger: boundary + closed finds ----
    ledger_items = ledger_doc["items"]
    for b in BOUNDARY_REVIEW:
        ledger_items.append(OrderedDict([
            ("identity_key", ptf_identity_key(b["name"])), ("canonical_name", b["name"]),
            ("disposition", "boundary_excluded"), ("duplicate_of", ""),
            ("notes", "%s: %s" % (WORK_ORDER, b["note"])),
            ("source", "chain_locator_002"),
        ]))
    for c in CLOSED_FOUND:
        ledger_items.append(OrderedDict([
            ("identity_key", ptf_identity_key(c["name"])), ("canonical_name", c["name"]),
            ("disposition", "closed"), ("duplicate_of", ""),
            ("notes", "%s: %s" % (WORK_ORDER, c["note"])),
            ("source", "chain_locator_002"),
        ]))
    ledger_doc["counts"]["canonical"] = len(hotels)
    ledger_doc["counts"]["boundary_excluded"] = ledger_doc["counts"].get("boundary_excluded", 0) + len(BOUNDARY_REVIEW)
    ledger_doc["counts"]["closed"] = ledger_doc["counts"].get("closed", 0) + len(CLOSED_FOUND)
    ledger_doc["as_of"] = AS_OF
    ledger_doc["work_order"] = WORK_ORDER

    # ---- source registry: register chain_locator_002 ----
    registry_doc = load_json(SOURCE_REGISTRY_PATH)
    if not any(s["source_id"] == "chain_locator_002" for s in registry_doc["sources"]):
        registry_doc["sources"].append(OrderedDict([
            ("source_id", "chain_locator_002"),
            ("name", "Brand/city locator sweep (Pass 002 completeness audit)"),
            ("organization", "various (Marriott, Hilton, IHG, Hyatt, Choice, "
                             "Wyndham, Best Western, Red Roof, Sonesta property "
                             "pages)"),
            ("source_type", "CHAIN"), ("family", "CHAIN"),
            ("url", ""), ("geographic_coverage",
             "Dearborn, Royal Oak/Birmingham, Livonia, Troy, Southfield, Ann Arbor"),
            ("data_categories", ["lodging"]), ("access_date", AS_OF),
            ("status", "authority_for_identity"),
            ("limitations", "Each candidate confirmed via its own first-party "
                            "brand page (or 2+ independent listing sources "
                            "agreeing on name+address) before being added."),
            ("automated_access", "static_html"),
        ]))
        registry_doc["count"] = len(registry_doc["sources"])

    return dict(census_doc=census_doc, partition_doc=partition_doc, queue_doc=queue_doc,
                ledger_doc=ledger_doc, registry_doc=registry_doc, rec=rec, counts=counts,
                new_rows=new_rows)


def build_evidence_doc(built: Dict) -> Dict:
    return OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-census-completeness-002/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("note", "Additive census-closure audit. No pet policy browsed. "
                 "published=7/verified_no_pets=7 unchanged."),
        ("census_before", 142), ("census_after", len(built["census_doc"]["hotels"])),
        ("new_canonical_count", len(built["new_rows"])),
        ("new_canonical", [OrderedDict([
            ("identity_key", r["identity_key"]), ("canonical_name", r["canonical_name"]),
            ("corridor", r["corridor"]), ("address", r["address"]), ("city", r["city"]),
            ("official_url", r["official_url"]), ("url_shape", r["url_shape"]),
        ]) for r in built["new_rows"]]),
        ("boundary_review", BOUNDARY_REVIEW),
        ("closed_found", CLOSED_FOUND),
        ("macomb_still_excluded", MACOMB_STILL_EXCLUDED),
        ("remaining_blockers", [
            "Downtown Detroit: no independent brand-by-brand sweep this pass "
            "(CVB cross-check only; 22 rows already committed).",
            "DTW/Romulus: only Detroit Metro Airport Marriott checked beyond "
            "the existing 11 rows; no full brand sweep.",
            "Novi/Wixom: no independent sweep this pass beyond what the "
            "existing 13-row census and the Farmington Hills-centered "
            "Marriott search incidentally covered.",
            "Farmington Hills: only the Marriott-centered search performed; "
            "no Hilton/IHG/Choice/Wyndham sweep.",
            "Birmingham: no independent sweep beyond what the Royal Oak "
            "search incidentally covered.",
            "WebSearch budget was exhausted mid-audit (200/200) -- the "
            "brand/corridor matrix above was not exhaustively completed.",
        ]),
        ("published", built["rec"].published), ("verified_no_pets", built["rec"].verified_no_pets),
        ("partition_counts", built["counts"]),
    ])


def run(apply: bool) -> None:
    built = build()
    evidence_doc = build_evidence_doc(built)

    print("census_before: 142  census_after:", len(built["census_doc"]["hotels"]))
    print("new_canonical:", len(built["new_rows"]))
    print("boundary_review:", len(BOUNDARY_REVIEW))
    print("closed_found:", len(CLOSED_FOUND))
    print("partition_counts:", json.dumps(built["counts"], sort_keys=True))
    print("published:", built["rec"].published, "verified_no_pets:", built["rec"].verified_no_pets)

    if not apply:
        print("dry run: nothing written")
        return

    if EVIDENCE_PATH.is_file():
        raise SystemExit("STOP: %s already exists" % EVIDENCE_PATH.name)

    write_lf(EVIDENCE_PATH, evidence_doc)
    write_lf(CENSUS_PATH, built["census_doc"])
    write_lf(PARTITION_PATH, built["partition_doc"])
    write_lf(QUEUE_PATH, built["queue_doc"])
    write_lf(LEDGER_PATH, built["ledger_doc"])
    write_lf(SOURCE_REGISTRY_PATH, built["registry_doc"])
    print("applied. wrote: evidence, census, partition, queue, ledger, source_registry")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    run(apply=args.apply)


if __name__ == "__main__":
    main()
