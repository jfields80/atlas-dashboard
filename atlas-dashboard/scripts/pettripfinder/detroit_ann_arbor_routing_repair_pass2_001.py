# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-ROUTING-REPAIR-PASS2-001.

Routing-only repair for the 5 properties left short of AWAITING_POLICY_
OBSERVATION after Pass 1: Delta Hotels (dead link), Courtyard Detroit
Pontiac Bloomfield (directory-only URL), DoubleTree by Hilton Detroit Novi
(generic brand URL), Hawthorn Suites by Wyndham Southfield Detroit (no URL),
Hotel Indigo Detroit Downtown (stale property code).

This is a SURGICAL patch, not a full rebuild: the committed census and
partition are already correct for the other 138 rows (Pass 1 verified
this), so re-deriving the whole market from CANDIDATES + REPAIRS + policy
decisions here would risk drifting rows this work order has no mandate to
touch. Instead this script loads the committed documents and patches
exactly the 5 target rows, then asserts byte-identity on every other row.

No policy authority is read, written, or referenced. No exclusion, no
approval, no hash in hotel_policy_facts_detroit-ann-arbor-mi.json or
hotel_exclusions.json is touched.
"""
from __future__ import annotations

import argparse
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

WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-ROUTING-REPAIR-PASS2-001"
PRIOR_COMMIT = "e7e8a37"
MARKET = "detroit-ann-arbor-mi"
AS_OF = "2026-08-17"

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
CENSUS_PATH = LP / "identity_census" / ("%s.json" % MARKET)
PARTITION_PATH = LP / "detroit_ann_arbor_final_partition_001.json"
EVIDENCE_PATH = LP / "detroit_ann_arbor_routing_repair_pass2_001.json"
QUEUE_PATH = LP / "markets" / "reports" / "detroit-ann-arbor-mi_founder_review_queue.json"


# ==========================================================================
# The 5 durable routing findings
# ==========================================================================

ROUTING = OrderedDict([
    ("delta hotels by marriott detroit metro airport", dict(
        canonical_name="Delta Hotels by Marriott Detroit Metro Airport",
        current_url="https://www.marriott.com/hotels/travel/dtwd",
        candidate_urls_tried=[
            "https://www.marriott.com/en-us/hotels/dtwde-delta-hotels-detroit-metro-airport/overview/",
            "https://www.marriott.com/en-us/hotels/dtwrm-detroit-metro-airport-marriott/overview/",
        ],
        final_url="https://www.bestwestern.com/en_US/book/hotels-in-romulus/"
                  "skyline-hotel-detroit-airport-surestay-collection-by-bw/"
                  "propertyCode.54306.html",
        source_relationship="EXACT_PROPERTY_FIRST_PARTY (Best Western property page)",
        property_code="54306",
        identity_signals={
            "address_match": True, "zip_match": True, "phone_match": True,
            "name_match": False,
            "note": "31500 Wick Road, Romulus, MI 48174, +1 (734) 721-3315 -- "
                    "identical to the committed record on all 3 non-name signals.",
        },
        final_verdict="CENSUS_REVIEW",
        reason="Both the committed URL (dtwd) and a guessed current-format "
               "Marriott code (dtwde) 404. Marriott's own live find-hotels "
               "search for the DTW/Romulus area (92 results, sorted by "
               "distance) returns ZERO Delta-branded properties at any "
               "distance -- the nearest Marriott-family property at this "
               "address does not exist under any Marriott code. Independent "
               "corroboration (commercial real-estate listings, OTA history) "
               "shows this building's brand lineage: Radisson Hotel Detroit "
               "Metro Airport (closed) -> Delta Hotels by Marriott Detroit "
               "Metro Airport -> Skyline Hotel Detroit Airport, SureStay "
               "Collection by BW. Best Western's own first-party property "
               "page for the SureStay Collection property confirms the "
               "identical street address AND identical phone number "
               "(+1 734-721-3315) as the committed Delta Hotels record. This "
               "is almost certainly the same physical property under a new "
               "brand flag, not a closure -- but a brand/identity change "
               "this large is a founder decision, not something this script "
               "may apply silently.",
        next_action="Founder review: replace the identity "
                    "\"Delta Hotels by Marriott Detroit Metro Airport\" with "
                    "\"Skyline Hotel Detroit Airport, SureStay Collection by "
                    "BW\" (same address/phone, new brand family) via a "
                    "proper identity-rename work order, or confirm/retire it "
                    "as a closure if further evidence contradicts the "
                    "conversion reading.",
        capture_readiness="N/A (identity pending census review; not "
                          "policy-observable under either name until "
                          "resolved)",
        new_official_url=None,   # census not mutated for a CENSUS_REVIEW row
        new_url_shape=None,
        census_review=True,
    )),
    ("courtyard detroit pontiac bloomfield", dict(
        canonical_name="Courtyard Detroit Pontiac Bloomfield",
        current_url="https://visitdetroit.com/directory/courtyard-by-marriott-detroit-pontiac-auburn-hills/",
        candidate_urls_tried=[],
        final_url="https://www.marriott.com/en-us/hotels/dtwcp-courtyard-detroit-pontiac-auburn-hills/overview/",
        source_relationship="EXACT_PROPERTY_FIRST_PARTY (Marriott.com destination search + property page)",
        property_code="dtwcp",
        identity_signals={
            "address_match": True, "zip_match": True, "phone_match": True,
            "name_match": True,
            "note": "Marriott's own address-search autosuggest for 3555 "
                    "Centerpoint Pkwy, Pontiac, MI resolved directly to "
                    "\"Courtyard by Marriott Detroit Pontiac/Auburn Hills\"; "
                    "the resulting property page's JSON-LD confirms street, "
                    "city, region, ZIP, and phone all exact.",
        },
        final_verdict="ROUTING_REPLACED",
        reason="The committed URL was a third-party Visit Detroit directory "
               "page, never a Marriott property-level route. Marriott's own "
               "destination search resolves the exact committed address "
               "directly to this property with an identical phone number.",
        next_action="",
        capture_readiness="EVIDENCE_READY",
        new_official_url="https://www.marriott.com/en-us/hotels/dtwcp-courtyard-detroit-pontiac-auburn-hills/overview/",
        new_url_shape="property",
        census_review=False,
    )),
    ("doubletree by hilton detroit novi", dict(
        canonical_name="DoubleTree by Hilton Detroit Novi",
        current_url="https://doubletree.hilton.com/",
        candidate_urls_tried=[],
        final_url="https://www.hilton.com/en/hotels/dtwnvdt-doubletree-detroit-novi/",
        source_relationship="EXACT_PROPERTY_FIRST_PARTY (Hilton.com property page)",
        property_code="dtwnvdt",
        identity_signals={
            "address_match": True, "zip_match": True, "phone_match": True,
            "name_match": True,
            "note": "42100 Crescent Blvd, Novi, Michigan, 48375, USA and "
                    "+1 248-344-8800 both exact matches to the committed "
                    "record, read directly off the live property page.",
        },
        final_verdict="ROUTING_REPLACED",
        reason="The committed URL was the generic DoubleTree brand landing "
               "page (doubletree.hilton.com), not a property-level route. "
               "The exact property page was located and verified directly.",
        next_action="",
        capture_readiness="EVIDENCE_READY",
        new_official_url="https://www.hilton.com/en/hotels/dtwnvdt-doubletree-detroit-novi/",
        new_url_shape="property",
        census_review=False,
    )),
    ("hawthorn suites by wyndham southfield detroit", dict(
        canonical_name="Hawthorn Suites by Wyndham Southfield Detroit",
        current_url="",
        candidate_urls_tried=[
            "https://www.wyndhamhotels.com/hawthorn-suites/southfield-michigan/hawthorn-suites-detroit-southfield/overview",
        ],
        final_url="",
        source_relationship="ABSENCE confirmed via Wyndham's own live "
                            "property search (no first-party route exists)",
        property_code="",
        identity_signals={
            "address_match": None, "zip_match": None, "phone_match": None,
            "name_match": None,
            "note": "No first-party page exists to check signals against. "
                    "Wyndham's own destination search centered on 26700 "
                    "Central Park Blvd, Southfield, MI returns 35 hotels "
                    "market-wide; the nearest is 7.1 miles away -- zero "
                    "Wyndham-flagged properties exist at or near this "
                    "address today.",
        },
        final_verdict="PROPERTY_CLOSED_OR_CONVERTED",
        reason="A guessed current-format Wyndham URL 404s. Wyndham's own "
               "live find-hotels search near the exact committed address "
               "returns no Wyndham property within 7+ miles. Convergent "
               "third-party evidence (not itself authoritative but "
               "corroborating the first-party absence) shows the property "
               "converted from Hawthorn Suites by Wyndham to an independent "
               "\"Springwood Suites\" brand at the same address, which is "
               "itself marked CLOSED on the review aggregator that tracked "
               "it (updated August 2025); no independent official website "
               "was found for Springwood Suites at all. No evidence of a "
               "still-operating hotel at this address was found anywhere.",
        next_action="Census review: confirm closure (or find a surviving "
                    "first-party page this search missed) before retiring "
                    "the identity; do not route policy capture here.",
        capture_readiness="N/A (closed)",
        new_official_url=None,
        new_url_shape=None,
        census_review=True,
    )),
    ("hotel indigo detroit downtown", dict(
        canonical_name="Hotel Indigo Detroit Downtown",
        current_url="https://www.ihg.com/hotelindigo/hotels/us/en/detroit/dttid/hoteldetail",
        candidate_urls_tried=[],
        final_url="https://www.ihg.com/hotelindigo/hotels/us/en/detroit/dttwb/hoteldetail",
        source_relationship="EXACT_PROPERTY_FIRST_PARTY (IHG.com destination search + property page)",
        property_code="dttwb",
        identity_signals={
            "address_match": True, "zip_match": True, "phone_match": False,
            "name_match": True,
            "note": "IHG's own destination search for \"Hotel Indigo Detroit "
                    "Downtown\" geocoded to 1020 Washington Blvd, Detroit, MI "
                    "48226 and returned this exact property 0.04 mi from "
                    "that point, same name, same street/city/ZIP. Phone "
                    "shown (1-888-233-0353) is IHG's central reservations "
                    "line, not the committed direct line (313-887-7000) -- "
                    "an expected variance, not a conflict.",
        },
        final_verdict="ROUTING_REPLACED",
        reason="The previously committed property code (dttid) no longer "
               "resolves on ihg.com. IHG's own destination search for this "
               "exact address and hotel name resolves to the SAME property "
               "-- identical name, street, city, ZIP -- under a new "
               "property code (dttwb). This is a property-code migration, "
               "not an identity change; the prior pass's ROUTING_UNRESOLVED "
               "flag was correct to withhold the old code rather than trust "
               "it.",
        next_action="",
        capture_readiness="EVIDENCE_READY (IHG hoteldetail pages have a "
                          "known CDP-freeze on full outerHTML reads in this "
                          "corpus; query `[class*=\"faq\"]` innerHTML instead "
                          "when this property is captured)",
        new_official_url="https://www.ihg.com/hotelindigo/hotels/us/en/detroit/dttwb/hoteldetail",
        new_url_shape="property",
        census_review=False,
    )),
])


def load_json(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_lf(path: Path, doc) -> None:
    text = json.dumps(doc, indent=2, ensure_ascii=False) + "\n"
    path.write_text(text.replace("\r\n", "\n"), encoding="utf-8", newline="\n")


def build_evidence_doc() -> Dict:
    items = []
    for key, r in ROUTING.items():
        items.append(OrderedDict([
            ("identity_key", key),
            ("canonical_name", r["canonical_name"]),
            ("current_url", r["current_url"]),
            ("candidate_urls_tried", r["candidate_urls_tried"]),
            ("final_url", r["final_url"]),
            ("source_relationship", r["source_relationship"]),
            ("property_code", r["property_code"]),
            ("identity_signals", r["identity_signals"]),
            ("final_verdict", r["final_verdict"]),
            ("reason", r["reason"]),
            ("next_action", r["next_action"]),
            ("capture_readiness", r["capture_readiness"]),
        ]))
    verdict_counts: Dict[str, int] = {}
    for r in ROUTING.values():
        verdict_counts[r["final_verdict"]] = verdict_counts.get(r["final_verdict"], 0) + 1
    return OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-routing-repair-pass2/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET),
        ("as_of", AS_OF),
        ("prior_commit", PRIOR_COMMIT),
        ("note", "Routing-only repair for the 5 properties left short of "
                 "AWAITING_POLICY_OBSERVATION after "
                 "PTF-DETROIT-ANN-ARBOR-PASS1-DECISION-APPLICATION-001. No "
                 "pet-policy facts were browsed, read, or recorded. No "
                 "policy authority, exclusion, or approval was touched."),
        ("count", len(items)),
        ("verdict_counts", verdict_counts),
        ("items", items),
    ])


def patch_census_and_partition() -> Dict:
    census_doc = load_json(CENSUS_PATH)
    partition_doc = load_json(PARTITION_PATH)

    census_by_key = {r["identity_key"]: r for r in census_doc["hotels"]}
    partition_by_key = {i["identity_key"]: i for i in partition_doc["items"]}

    for key in ROUTING:
        if key not in census_by_key:
            raise SystemExit("STOP: %r not in committed census" % key)
        if key not in partition_by_key:
            raise SystemExit("STOP: %r not in committed partition" % key)

    census_before = json.dumps(census_doc, sort_keys=True)
    partition_before = json.dumps(partition_doc, sort_keys=True)

    for key, r in ROUTING.items():
        crow = census_by_key[key]
        if r["new_official_url"] is not None:
            crow["official_url"] = r["new_official_url"]
        if r["new_url_shape"] is not None:
            crow["url_shape"] = r["new_url_shape"]

        prow = partition_by_key[key]
        if r["census_review"]:
            new_state = enums.AWAITING_CENSUS_REVIEW
        else:
            new_state = enums.AWAITING_POLICY_OBSERVATION
        prow["final_state"] = new_state
        terminal = new_state in enums.TERMINAL_STATES
        prow["resolved"] = terminal
        prow["next_action"] = "" if terminal else next_action_for(new_state)
        prow["next_action_source"] = ("" if terminal
                                       else "identity_census/detroit-ann-arbor-mi.json")
        prow["determined_by"] = WORK_ORDER
        prow["updated_at"] = AS_OF
        prow["official_url"] = crow["official_url"]
        prow["state_override_reason"] = (
            "%s: %s" % (WORK_ORDER, r["final_verdict"])
            if r["census_review"] else "")

    # Freeze proof: every row NOT in ROUTING must be byte-identical to what
    # was loaded. Compare the untouched subsets rather than the whole
    # document (whose touched rows legitimately differ now).
    untouched_census_before = [row for row in json.loads(census_before)["hotels"]
                               if row["identity_key"] not in ROUTING]
    untouched_census_after = [row for row in census_doc["hotels"]
                              if row["identity_key"] not in ROUTING]
    if untouched_census_before != untouched_census_after:
        raise SystemExit("STOP: an unrelated census row changed")

    untouched_partition_before = [row for row in json.loads(partition_before)["items"]
                                  if row["identity_key"] not in ROUTING]
    untouched_partition_after = [row for row in partition_doc["items"]
                                 if row["identity_key"] not in ROUTING]
    if untouched_partition_before != untouched_partition_after:
        raise SystemExit("STOP: an unrelated partition row changed")

    counts: Dict[str, int] = {}
    for item in partition_doc["items"]:
        counts[item["final_state"]] = counts.get(item["final_state"], 0) + 1
    partition_doc["final_state_counts"] = counts
    partition_doc["final_state_meanings"] = {
        state: PART.STATE_MEANINGS[state] for state in sorted(counts)}
    partition_doc["work_order"] = WORK_ORDER
    partition_doc["as_of"] = AS_OF
    partition_doc["note"] = ("Routing repaired for 5 properties by "
                              "%s: 3 ROUTING_REPLACED (Courtyard Pontiac, "
                              "DoubleTree Novi, Hotel Indigo Downtown) move "
                              "to AWAITING_POLICY_OBSERVATION; Delta Hotels "
                              "(CENSUS_REVIEW) and Hawthorn Suites Southfield "
                              "(PROPERTY_CLOSED_OR_CONVERTED) retain an "
                              "honest AWAITING_CENSUS_REVIEW blocker. "
                              "published=6 and verified_no_pets=5 are "
                              "UNCHANGED -- no policy authority was touched."
                              % WORK_ORDER)
    census_doc["work_order"] = WORK_ORDER
    census_doc["captured_at"] = AS_OF

    issues = CENSUS.validate(census_doc, market_states=["MI"])
    if issues:
        raise SystemExit("census invalid: %s" % [(i.path, i.code, i.detail) for i in issues])
    p_issues = PART.validate(partition_doc)
    if p_issues:
        raise SystemExit("partition invalid: %s" % [(i.path, i.code, i.detail) for i in p_issues])
    rec = PART.reconcile(CENSUS.identity_keys(census_doc), partition_doc, market_id=MARKET)
    rec_issues = PART.reconciliation_issues(rec)
    if rec_issues or not rec.agrees:
        raise SystemExit("reconciliation failed: %s" % (rec_issues,))
    if rec.published != 6 or rec.verified_no_pets != 5:
        raise SystemExit("AUTHORITY FREEZE VIOLATED: published=%s no_pets=%s"
                         % (rec.published, rec.verified_no_pets))

    queue_doc = load_json(QUEUE_PATH)
    by_key_q = {item["identity_key"]: item for item in queue_doc["items"]}
    for key, r in ROUTING.items():
        item = by_key_q.get(key)
        if item is None:
            continue
        prow = partition_by_key[key]
        item["address"] = census_by_key[key]["address"]
        item["phone"] = census_by_key[key]["phone"]
        item["official_candidate_url"] = census_by_key[key]["official_url"]
        item["corridor"] = census_by_key[key]["corridor"]
        item["current_classification"] = prow["final_state"]
        item["blocking_reason"] = prow["final_state"]
        item["requested_evidence"] = ("citable pet-policy artifact from the "
            "property's own page" if census_by_key[key]["official_url"]
            else "property-level official URL and a citable pet-policy artifact")
        item["next_action"] = prow["next_action"]
        payload = json.dumps({k: v for k, v in item.items() if k != "row_sha256"},
                             sort_keys=True, ensure_ascii=False)
        import hashlib
        item["row_sha256"] = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    queue_doc["as_of"] = AS_OF
    queue_doc["work_order"] = WORK_ORDER

    return dict(census_doc=census_doc, partition_doc=partition_doc, queue_doc=queue_doc,
                rec=rec, counts=counts)


def run(apply: bool) -> None:
    evidence_doc = build_evidence_doc()
    patched = patch_census_and_partition()

    print("ROUTING_CONFIRMED:", sum(1 for r in ROUTING.values() if r["final_verdict"] == "ROUTING_CONFIRMED"))
    print("ROUTING_REPLACED:", sum(1 for r in ROUTING.values() if r["final_verdict"] == "ROUTING_REPLACED"))
    print("CENSUS_REVIEW:", sum(1 for r in ROUTING.values() if r["final_verdict"] == "CENSUS_REVIEW"))
    print("PROPERTY_CLOSED_OR_CONVERTED:", sum(1 for r in ROUTING.values() if r["final_verdict"] == "PROPERTY_CLOSED_OR_CONVERTED"))
    print("ROUTING_UNRESOLVED:", sum(1 for r in ROUTING.values() if r["final_verdict"] == "ROUTING_UNRESOLVED"))
    print("ATTENDED_REQUIRED:", sum(1 for r in ROUTING.values() if r["final_verdict"] == "ATTENDED_REQUIRED"))
    print("partition_counts:", json.dumps(patched["counts"], sort_keys=True))
    print("published:", patched["rec"].published, "verified_no_pets:", patched["rec"].verified_no_pets)

    if not apply:
        print("dry run: nothing written")
        return

    if EVIDENCE_PATH.is_file():
        raise SystemExit("STOP: %s already exists" % EVIDENCE_PATH.name)

    write_lf(EVIDENCE_PATH, evidence_doc)
    write_lf(CENSUS_PATH, patched["census_doc"])
    write_lf(PARTITION_PATH, patched["partition_doc"])
    write_lf(QUEUE_PATH, patched["queue_doc"])
    print("applied. wrote:", EVIDENCE_PATH.name, CENSUS_PATH.name,
          PARTITION_PATH.name, QUEUE_PATH.name)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    run(apply=args.apply)


if __name__ == "__main__":
    main()
