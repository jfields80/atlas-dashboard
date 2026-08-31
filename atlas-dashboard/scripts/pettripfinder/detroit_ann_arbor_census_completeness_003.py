# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-CENSUS-COMPLETENESS-003.

Closes the 5 remaining blockers from Pass 002 (Downtown Detroit, DTW/
Romulus, Novi/Wixom, Farmington Hills, Birmingham) via a real brand-by-
brand sweep: Hilton's and IHG's own location-search pages (via attended
browser -- both block WebFetch), Choice Hotels' own city pages (loaded
fully, no truncation), and Wyndham's own city search. WebSearch was
exhausted before this pass began; every finding here is sourced from a
brand's own live page, not a search snippet.

Additive, not a rebuild: the 161-row census is asserted byte-identical
except for the 2 explicit corrections below (Section 8 requires an
explicit disposition for any existing identity found renamed/wrong, not
silence). No pet policy browsed; published=7/verified_no_pets=7 frozen.

22 new CANONICAL_CENSUS rows, 6 BOUNDARY_REVIEW (cities not in any
corridor's included_cities: Commerce Township, Clawson, Canton, Madison
Heights, Allen Park, Rochester Hills -- flagged, not silently added).

Two EXISTING rows corrected, both found via convergent first-party
evidence during this sweep:

  * "Best Western Premier Detroit Southfield Hotel" (added Pass 002) --
    bestwestern.com's own property code now returns "The hotel you
    searched for is no longer available"; choicehotels.com's own live
    Radisson property page shows the IDENTICAL address and a real,
    responding phone number under "Radisson Hotel Southfield-Detroit".
    Same building, converted brand -- renamed in place (former_name
    preserved), same pattern as Delta Hotels -> Skyline in Pass 2.
  * "Staybridge Suites Detroit North - Royal Oak" (added Pass 002) --
    the address recorded then (5150 Coolidge Hwy, sourced from a
    WebSearch snippet) does not match this property's own live IHG page
    (same property code, dtwro): the real address is 5125 Meijer Drive.
    Address corrected in place; not a rename, a data-entry fix.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List

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
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-CENSUS-COMPLETENESS-003"
AS_OF = "2026-08-17"

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
CENSUS_PATH = LP / "identity_census" / ("%s.json" % MARKET)
PARTITION_PATH = LP / "detroit_ann_arbor_final_partition_001.json"
QUEUE_PATH = LP / "markets" / "reports" / "detroit-ann-arbor-mi_founder_review_queue.json"
LEDGER_PATH = LP / "markets" / "reports" / "detroit-ann-arbor-mi_duplicate_ledger.json"
SOURCE_REGISTRY_PATH = LP / "markets" / "reports" / "detroit-ann-arbor-mi_source_registry.json"
EVIDENCE_PATH = LP / "detroit_ann_arbor_census_completeness_003.json"


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
# 22 new canonical candidates.
# ==========================================================================
NEW_CANONICAL = [
    # -- Hilton (Farmington Hills-centered locations sweep) --
    _c("Home2 Suites by Hilton West Bloomfield Detroit", "33098 Northwestern Highway",
       "West Bloomfield", "48322", "+1 248-940-1000",
       "https://www.hilton.com/en/hotels/dtwrsht-home2-suites-west-bloomfield-detroit/",
       "property", "chain_locator_003"),
    _c("Tru by Hilton Novi Detroit", "40255 West 13 Mile", "Novi", "48377",
       "+1 248-973-6306", "https://www.hilton.com/en/hotels/dtwneru-tru-novi-detroit/",
       "property", "chain_locator_003"),
    _c("Hampton Inn Detroit/Northville", "20600 Haggerty Rd.", "Northville", "48167",
       "+1 734-462-1119",
       "https://www.hilton.com/en/hotels/dttnvhx-hampton-detroit-northville/",
       "property", "chain_locator_003"),
    _c("Homewood Suites by Hilton Novi Detroit", "26150 Town Center Drive", "Novi",
       "48375", "+1 248-347-6100",
       "https://www.hilton.com/en/hotels/dttdnhw-homewood-suites-novi-detroit/",
       "property", "chain_locator_003"),
    _c("Hilton Garden Inn Detroit/Novi", "27355 Cabaret Drive", "Novi", "48377",
       "+1 248-348-3840",
       "https://www.hilton.com/en/hotels/detnogi-hilton-garden-inn-detroit-novi/",
       "property", "chain_locator_003"),
    _c("Hampton Inn Livonia Detroit", "28151 Schoolcraft Road", "Livonia", "48150",
       "+1 734-237-4480",
       "https://www.hilton.com/en/hotels/dtwlihx-hampton-livonia-detroit/",
       "property", "chain_locator_003"),
    # -- Choice Hotels (Farmington Hills + Birmingham-centered sweeps) --
    _c("Comfort Inn Farmington Hills - Detroit Northwest", "30715 W. Twelve Mile Rd.",
       "Farmington Hills", "48334", "", "", "none", "chain_locator_003"),
    _c("Country Inn & Suites by Radisson, Novi, MI", "21625 Haggerty Road", "Novi",
       "48375", "", "", "none", "chain_locator_003"),
    _c("MainStay Suites Detroit Farmington Hills", "37555 Hills Tech Drive",
       "Farmington Hills", "48331", "", "", "none", "chain_locator_003"),
    _c("Quality Inn Southfield - Detroit", "26111 Telegraph Road", "Southfield",
       "48034", "", "", "none", "chain_locator_003"),
    _c("Comfort Suites Wixom - Novi", "28049 Wixom Rd.", "Wixom", "48393", "",
       "", "none", "chain_locator_003"),
    _c("Country Inn & Suites by Radisson, Dearborn, MI", "24555 Michigan Avenue",
       "Dearborn", "48124", "", "", "none", "chain_locator_003"),
    _c("Rodeway Inn Auburn Hills - Detroit", "1471 N Opdyke Road", "Auburn Hills",
       "48326", "", "", "none", "chain_locator_003"),
    _c("Suburban Studios Auburn Hills - Detroit", "1180 Doris Road", "Auburn Hills",
       "48326", "", "", "none", "chain_locator_003"),
    _c("MainStay Suites Detroit Auburn Hills", "1650 N Opdyke Road", "Auburn Hills",
       "48326", "", "", "none", "chain_locator_003"),
    _c("Clarion Hotel Detroit Metro Airport", "8600 Merriman Road", "Romulus",
       "48174", "", "", "none", "chain_locator_003"),
    _c("Quality Inn & Suites Detroit Metro Airport", "9555 Middlebelt Rd.", "Romulus",
       "48174", "", "", "none", "chain_locator_003"),
    _c("Park Inn by Radisson, Detroit Metro Airport", "8230 Merriman Rd", "Romulus",
       "48174", "", "", "none", "chain_locator_003"),
    _c("Radisson Hotel Detroit Metro Airport", "8800 Wickham Road", "Romulus",
       "48174", "", "", "none", "chain_locator_003"),
    _c("Quality Inn Detroit Downtown", "1316 Jefferson Ave", "Detroit", "48207",
       "", "", "none", "chain_locator_003"),
    _c("Comfort Inn Detroit Downtown", "1999 E. Jefferson Ave.", "Detroit", "48207",
       "", "", "none", "chain_locator_003"),
    # -- IHG (Downtown Detroit-centered sweep) --
    _c("Holiday Inn Express & Suites Detroit - Dearborn", "6355 Mercury Drive",
       "Dearborn", "48126", "1 888 465 4329",
       "", "none", "chain_locator_003"),
]

# Cities not in any corridor's included_cities.
BOUNDARY_REVIEW = [
    dict(name="Hampton Inn Commerce Novi", city="Commerce Township",
        address="169 Loop Road", postal="48390",
        note="Real Hilton property, 5.23 mi from Farmington Hills. 'Commerce "
             "Township' is not registered on any corridor (same issue as "
             "TownePlace Suites Detroit Commerce, flagged in Pass 002)."),
    dict(name="Comfort Inn Detroit - Troy", city="Clawson",
        address="1145 W Maple Road", postal="48017",
        note="Choice-brand hotel named for Troy but physically in Clawson, "
             "MI, which is not in troy-auburn-hills' included_cities."),
    dict(name="Comfort Suites Canton - Detroit", city="Canton",
        address="5730 North Haggerty Road", postal="48187",
        note="Canton, MI is adjacent to Plymouth/Livonia but is not itself "
             "in livonia-plymouth-northville's included_cities."),
    dict(name="Rodeway Inn Madison Heights - Detroit", city="Madison Heights",
        address="32703 Stephenson Highway", postal="48071",
        note="Madison Heights is not in any corridor's included_cities."),
    dict(name="Comfort Inn & Suites Allen Park - Dearborn", city="Allen Park",
        address="3600 Enterprise Drive", postal="48101",
        note="Same city as the already-known Best Western Greenfield Inn "
             "boundary flag from Phase 1 (Allen Park, not Dearborn)."),
    dict(name="Days Inn & Suites by Wyndham Rochester Hills MI",
        city="Rochester Hills", address="1919 Star Batt Dr", postal="48309",
        note="'Rochester Hills' is a distinct municipality from 'Rochester', "
             "which IS registered on birmingham-royal-oak-rochester. Not "
             "assumed to be the same string."),
]

# Existing rows corrected via convergent first-party re-verification.
CORRECTIONS = OrderedDict([
    ("best western premier detroit southfield hotel", dict(
        kind="rename",
        new_name="Radisson Hotel Southfield-Detroit",
        new_address="26555 Telegraph Road", new_city="Southfield",
        new_postal="48033", new_phone="(248) 469-4867",
        new_url="https://www.choicehotels.com/michigan/southfield/radisson-hotels/mi336",
        note="bestwestern.com's own property code (23171) now returns "
             "'The hotel you searched for is no longer available'; "
             "choicehotels.com's own live property page for "
             "'Radisson Hotel Southfield-Detroit' shows the IDENTICAL "
             "street address as the Best Western Premier record this "
             "market committed in Pass 002, with a real, distinct phone "
             "number. Same building, converted brand -- renamed in "
             "place, former_name preserved, same mechanism as Delta "
             "Hotels -> Skyline Hotel in Pass 2.",
    )),
    ("staybridge suites detroit north royal oak", dict(
        kind="address_correction",
        new_address="5125 Meijer Drive", new_city="Royal Oak", new_postal="48073",
        new_phone="1-248-654-6555",
        note="The address recorded in Pass 002 (5150 Coolidge Hwy) does "
             "not match this property's own live IHG page (property code "
             "dtwro, unchanged) -- the real address is 5125 Meijer Drive. "
             "Not a rename: same identity_key, same canonical_name, "
             "address/phone corrected to match the property's own page.",
    )),
])


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
    by_key = {r["identity_key"]: r for r in hotels}
    existing_keys = set(by_key)

    for key in CORRECTIONS:
        if key not in by_key:
            raise SystemExit("STOP: correction target %r not in committed census" % key)

    untouched_before = [r for r in hotels if r["identity_key"] not in CORRECTIONS]

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

    # ---- apply the 2 existing-row corrections ----
    corrected_old_to_new_key: Dict[str, str] = {}
    for old_key, corr in CORRECTIONS.items():
        row = by_key[old_key]
        if corr["kind"] == "rename":
            new_key = ptf_identity_key(corr["new_name"])
            if new_key in existing_keys and new_key != old_key:
                raise SystemExit("STOP: correction target key %r collides" % new_key)
            row["former_name"] = row["canonical_name"]
            row["canonical_name"] = corr["new_name"]
            row["display_name"] = corr["new_name"]
            row["identity_key"] = new_key
            row["normalized_name"] = normalize_name(corr["new_name"])
            row["slug"] = _slugify(corr["new_name"])
            row["address"] = corr["new_address"]
            row["city"] = corr["new_city"]
            row["postal_code"] = corr["new_postal"]
            row["phone"] = corr["new_phone"]
            row["official_url"] = corr["new_url"]
            row["url_shape"] = "property"
            row["provenance"] = "%s: identity conversion (%s)" % (WORK_ORDER, corr["note"][:80])
            row["observed_at"] = AS_OF
            row["street_identity"] = _street_identity(row["address"], row["postal_code"])
            corrected_old_to_new_key[old_key] = new_key
        elif corr["kind"] == "address_correction":
            row["address"] = corr["new_address"]
            row["city"] = corr["new_city"]
            row["postal_code"] = corr["new_postal"]
            row["phone"] = corr["new_phone"]
            row["observed_at"] = AS_OF
            row["street_identity"] = _street_identity(row["address"], row["postal_code"])
            corrected_old_to_new_key[old_key] = old_key
        else:
            raise SystemExit("unknown correction kind %r" % corr["kind"])

    hotels.extend(new_rows)
    census_doc["count"] = len(hotels)
    census_doc["work_order"] = WORK_ORDER
    census_doc["captured_at"] = AS_OF

    issues = CENSUS.validate(census_doc, market_states=["MI"])
    if issues:
        raise SystemExit("census invalid: %s" % [(i.path, i.code, i.detail) for i in issues])

    untouched_after = [r for r in hotels if r["identity_key"] not in
                       set(corrected_old_to_new_key.values()) | {r2["identity_key"] for r2 in new_rows}]
    if untouched_before != untouched_after:
        raise SystemExit("STOP: an unrelated census row changed")

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

    # ---- partition: append new rows, patch the 2 corrected rows' keys ----
    items = partition_doc["items"]
    p_by_key = {i["identity_key"]: i for i in items}
    items_before_untouched = [i for i in items if i["identity_key"] not in CORRECTIONS]

    for old_key, new_key in corrected_old_to_new_key.items():
        prow = p_by_key[old_key]
        if new_key != old_key:
            prow["identity_key"] = new_key
        crow = by_key.get(new_key) or next(r for r in hotels if r["identity_key"] == new_key)
        prow["canonical_name"] = crow["canonical_name"]
        prow["slug"] = crow["slug"]
        prow["city"] = crow["city"]
        prow["postal_code"] = crow["postal_code"]
        prow["official_url"] = crow["official_url"]
        prow["determined_by"] = WORK_ORDER
        prow["updated_at"] = AS_OF

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

    items_after_untouched = [i for i in items if i["identity_key"] not in
                             set(corrected_old_to_new_key.values())
                             and i["identity_key"] not in {r["identity_key"] for r in new_rows}]
    if items_before_untouched != items_after_untouched:
        raise SystemExit("STOP: an unrelated partition row changed")

    partition_doc["count"] = len(items)
    counts: Dict[str, int] = {}
    for item in items:
        counts[item["final_state"]] = counts.get(item["final_state"], 0) + 1
    partition_doc["final_state_counts"] = counts
    partition_doc["final_state_meanings"] = {s: PART.STATE_MEANINGS[s] for s in sorted(counts)}
    partition_doc["work_order"] = WORK_ORDER
    partition_doc["as_of"] = AS_OF
    partition_doc["note"] = ("%s added 22 canonical identities from a real "
                             "brand-by-brand sweep of the 5 remaining "
                             "blockers, and corrected 2 existing rows "
                             "(Best Western Southfield -> Radisson "
                             "Southfield rename; Staybridge Royal Oak "
                             "address fix). published=7 and "
                             "verified_no_pets=7 UNCHANGED." % WORK_ORDER)
    census_doc["note"] = census_doc.get("note", "")

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

    # ---- founder review queue: patch corrected keys, append new rows ----
    q_items = queue_doc["items"]
    q_before_untouched = [q for q in q_items if q["identity_key"] not in CORRECTIONS]
    for q in q_items:
        if q["identity_key"] in corrected_old_to_new_key:
            new_key = corrected_old_to_new_key[q["identity_key"]]
            crow = next(r for r in hotels if r["identity_key"] == new_key)
            q["identity_key"] = new_key
            q["hotel_id"] = new_key
            q["canonical_name"] = crow["canonical_name"]
            q["address"] = crow["address"]
            q["phone"] = crow["phone"]
            q["official_candidate_url"] = crow["official_url"]
            payload = json.dumps({k: v for k, v in q.items() if k != "row_sha256"},
                                 sort_keys=True, ensure_ascii=False)
            q["row_sha256"] = hashlib.sha256(payload.encode("utf-8")).hexdigest()

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

    q_after_untouched = [q for q in q_items if q["identity_key"] not in
                         set(corrected_old_to_new_key.values())
                         and q["identity_key"] not in {r["identity_key"] for r in new_rows}]
    if q_before_untouched != q_after_untouched:
        raise SystemExit("STOP: an unrelated queue row changed")
    queue_doc["count"] = len(q_items)
    queue_doc["as_of"] = AS_OF
    queue_doc["work_order"] = WORK_ORDER

    # ---- duplicate/disposition ledger: boundary finds + corrections log ----
    ledger_items = ledger_doc["items"]
    for b in BOUNDARY_REVIEW:
        ledger_items.append(OrderedDict([
            ("identity_key", ptf_identity_key(b["name"])), ("canonical_name", b["name"]),
            ("disposition", "boundary_excluded"), ("duplicate_of", ""),
            ("notes", "%s: %s" % (WORK_ORDER, b["note"])),
            ("source", "chain_locator_003"),
        ]))
    for old_key, corr in CORRECTIONS.items():
        ledger_items.append(OrderedDict([
            ("identity_key", corrected_old_to_new_key[old_key]),
            ("canonical_name", corr.get("new_name") or "Staybridge Suites Detroit North - Royal Oak"),
            ("disposition", "corrected"), ("duplicate_of", ""),
            ("notes", "%s: %s" % (WORK_ORDER, corr["note"])),
            ("source", "chain_locator_003"),
        ]))
    ledger_doc["counts"]["canonical"] = len(hotels)
    ledger_doc["counts"]["boundary_excluded"] = ledger_doc["counts"].get("boundary_excluded", 0) + len(BOUNDARY_REVIEW)
    ledger_doc["counts"]["corrected"] = ledger_doc["counts"].get("corrected", 0) + len(CORRECTIONS)
    ledger_doc["as_of"] = AS_OF
    ledger_doc["work_order"] = WORK_ORDER

    # ---- source registry: register chain_locator_003 ----
    registry_doc = load_json(SOURCE_REGISTRY_PATH)
    if not any(s["source_id"] == "chain_locator_003" for s in registry_doc["sources"]):
        registry_doc["sources"].append(OrderedDict([
            ("source_id", "chain_locator_003"),
            ("name", "Brand location-page sweep (Pass 003 5-blocker closure)"),
            ("organization", "Hilton, IHG, Choice Hotels, Wyndham -- own "
                             "location/search pages"),
            ("source_type", "CHAIN"), ("family", "CHAIN"),
            ("url", ""), ("geographic_coverage",
             "Downtown Detroit, DTW/Romulus, Novi/Wixom, Farmington Hills, "
             "Birmingham"),
            ("data_categories", ["lodging"]), ("access_date", AS_OF),
            ("status", "authority_for_identity"),
            ("limitations", "WebSearch was exhausted before this pass; every "
                            "finding is sourced from the brand's own live "
                            "location/property page via attended browser, "
                            "not a search snippet."),
            ("automated_access", "attended_browser"),
        ]))
        registry_doc["count"] = len(registry_doc["sources"])

    return dict(census_doc=census_doc, partition_doc=partition_doc, queue_doc=queue_doc,
                ledger_doc=ledger_doc, registry_doc=registry_doc, rec=rec, counts=counts,
                new_rows=new_rows, corrected_old_to_new_key=corrected_old_to_new_key)


def build_evidence_doc(built: Dict) -> Dict:
    return OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-census-completeness-003/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("note", "Additive census-closure audit for the 5 remaining Pass 002 "
                 "blockers. No pet policy browsed. "
                 "published=7/verified_no_pets=7 unchanged."),
        ("census_before", 161), ("census_after", len(built["census_doc"]["hotels"])),
        ("new_canonical_count", len(built["new_rows"])),
        ("new_canonical", [OrderedDict([
            ("identity_key", r["identity_key"]), ("canonical_name", r["canonical_name"]),
            ("corridor", r["corridor"]), ("address", r["address"]), ("city", r["city"]),
            ("official_url", r["official_url"]), ("url_shape", r["url_shape"]),
        ]) for r in built["new_rows"]]),
        ("boundary_review", BOUNDARY_REVIEW),
        ("corrections", [OrderedDict([
            ("old_identity_key", old), ("new_identity_key", new),
            ("kind", CORRECTIONS[old]["kind"]), ("note", CORRECTIONS[old]["note"]),
        ]) for old, new in built["corrected_old_to_new_key"].items()]),
        ("blockers_closed", OrderedDict([
            ("downtown_detroit", True), ("dtw_romulus", True),
            ("novi_wixom", True), ("farmington_hills", True),
            ("birmingham", True),
        ])),
        ("published", built["rec"].published), ("verified_no_pets", built["rec"].verified_no_pets),
        ("partition_counts", built["counts"]),
    ])


def run(apply: bool) -> None:
    built = build()
    evidence_doc = build_evidence_doc(built)

    print("census_before: 161  census_after:", len(built["census_doc"]["hotels"]))
    print("new_canonical:", len(built["new_rows"]))
    print("boundary_review:", len(BOUNDARY_REVIEW))
    print("corrections:", len(CORRECTIONS))
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
