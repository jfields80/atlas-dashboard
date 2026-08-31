# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-IDENTITY-REPAIR-PASS2-001.

Applies the founder's two identity/census decisions from the Pass 2
routing-repair review:

  A. Delta Hotels by Marriott Detroit Metro Airport -> APPROVE_IDENTITY_
     CONVERSION -> Skyline Hotel Detroit Airport, SureStay Collection by
     BW. Same physical property (address+phone identical), new brand
     flag. Renamed IN PLACE: identity_key/canonical_name become the
     current name, former_name preserves the old one. Routes to
     AWAITING_POLICY_OBSERVATION now that an exact, live, first-party
     route exists.

  B. Hawthorn Suites by Wyndham Southfield Detroit -> APPROVE_CLOSED_OR_
     CONVERTED_OUT_OF_ACTIVE_CENSUS. No terminal "closed hotel" partition
     final_state exists in contracts/enums.py (only PUBLISHED_PET_
     FRIENDLY, VERIFIED_NO_PETS, OUT_OF_CURRENT_CATEGORY are terminal,
     and OUT_OF_CURRENT_CATEGORY means lodging_state=NOT_LODGING --
     "never was a hotel" -- which would misrepresent Hawthorn's real
     history). The precedented mechanism for a genuinely-closed
     property IS real: build_pittsburgh_market_001.py's candidate-
     ledger `disposition` vocabulary already includes "closed" as a
     first-class value alongside canonical/duplicate/boundary_excluded,
     and this market's own duplicate-ledger schema already carries a
     `closed` counter (committed at 0, unused until now). Retiring
     Hawthorn through that ledger -- removing it from the canonical
     census/partition/queue while preserving its full research history
     in the ledger -- is therefore the correct, faithful application of
     the founder's decision, not an invented shortcut.

Both revalidated immediately before mutation (see chat transcript):
Best Western's Skyline page is live with an exact address/phone match;
Marriott's dtwd/dtwde codes both still 404; Wyndham's live search still
returns nothing near Hawthorn's address and no newer active identity was
found anywhere.

No pet-policy fact is read, inferred, or recorded. published=6 and
verified_no_pets=5 are frozen and asserted unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
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
from scripts.pettripfinder.site_data import normalize_name                  # noqa: E402

WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-IDENTITY-REPAIR-PASS2-001"
ROUTING_PASS2_COMMIT = "699a553"
MARKET = "detroit-ann-arbor-mi"
AS_OF = "2026-08-17"
FOUNDER = "jfields80"

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
CENSUS_PATH = LP / "identity_census" / ("%s.json" % MARKET)
PARTITION_PATH = LP / "detroit_ann_arbor_final_partition_001.json"
QUEUE_PATH = LP / "markets" / "reports" / "detroit-ann-arbor-mi_founder_review_queue.json"
LEDGER_PATH = LP / "markets" / "reports" / "detroit-ann-arbor-mi_duplicate_ledger.json"
EVIDENCE_PATH = LP / "detroit_ann_arbor_identity_repair_pass2_001.json"

DELTA_OLD_KEY = "delta hotels by marriott detroit metro airport"
DELTA_NEW_NAME = "Skyline Hotel Detroit Airport, SureStay Collection by BW"
DELTA_NEW_URL = ("https://www.bestwestern.com/en_US/book/hotels-in-romulus/"
                  "skyline-hotel-detroit-airport-surestay-collection-by-bw/"
                  "propertyCode.54306.html")

HAWTHORN_KEY = "hawthorn suites by wyndham southfield detroit"


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").strip().lower()).strip("-")


def _ptf_identity_key(name: str) -> str:
    from scripts.pettripfinder.contracts.identity_key import ptf_identity_key
    return ptf_identity_key(name)


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

    hotels = census_doc["hotels"]
    by_key = {r["identity_key"]: r for r in hotels}
    if DELTA_OLD_KEY not in by_key:
        raise SystemExit("STOP: Delta not in committed census")
    if HAWTHORN_KEY not in by_key:
        raise SystemExit("STOP: Hawthorn not in committed census")

    untouched_before = [r for r in hotels
                        if r["identity_key"] not in (DELTA_OLD_KEY, HAWTHORN_KEY)]

    # ---- A. Delta -> Skyline (rename in place) ----
    delta_row = by_key[DELTA_OLD_KEY]
    new_key = _ptf_identity_key(DELTA_NEW_NAME)
    if new_key in by_key:
        raise SystemExit("STOP: new identity_key %r already exists in census" % new_key)
    delta_row["former_name"] = delta_row["canonical_name"]
    delta_row["canonical_name"] = DELTA_NEW_NAME
    delta_row["display_name"] = DELTA_NEW_NAME
    delta_row["identity_key"] = new_key
    delta_row["normalized_name"] = normalize_name(DELTA_NEW_NAME)
    delta_row["slug"] = _slugify(DELTA_NEW_NAME)
    delta_row["official_url"] = DELTA_NEW_URL
    delta_row["url_shape"] = "property"
    delta_row["identity_state"] = enums.IDENTITY_CONFIRMED
    delta_row["provenance"] = "%s: identity conversion, same address/phone, new brand flag (was %s:%s)" % (
        WORK_ORDER, ROUTING_PASS2_COMMIT, "PTF-DETROIT-ANN-ARBOR-ROUTING-REPAIR-PASS2-001")
    delta_row["observed_at"] = AS_OF

    # ---- B. Hawthorn -> retired via the "closed" disposition mechanism ----
    hawthorn_row = by_key.pop(HAWTHORN_KEY)
    hotels[:] = [r for r in hotels if r["identity_key"] != HAWTHORN_KEY]
    census_doc["count"] = len(hotels)

    issues = CENSUS.validate(census_doc, market_states=["MI"])
    if issues:
        raise SystemExit("census invalid: %s" % [(i.path, i.code, i.detail) for i in issues])

    untouched_after = [r for r in hotels if r["identity_key"] != new_key]
    if untouched_before != untouched_after:
        raise SystemExit("STOP: an unrelated census row changed")

    # ---- Partition ----
    items = partition_doc["items"]
    p_by_key = {i["identity_key"]: i for i in items}
    p_untouched_before = [i for i in items
                          if i["identity_key"] not in (DELTA_OLD_KEY, HAWTHORN_KEY)]

    delta_item = p_by_key[DELTA_OLD_KEY]
    delta_item["identity_key"] = new_key
    delta_item["canonical_name"] = DELTA_NEW_NAME
    delta_item["slug"] = delta_row["slug"]
    delta_item["official_url"] = DELTA_NEW_URL
    delta_item["final_state"] = enums.AWAITING_POLICY_OBSERVATION
    delta_item["resolved"] = False
    delta_item["next_action"] = next_action_for(enums.AWAITING_POLICY_OBSERVATION)
    delta_item["next_action_source"] = "identity_census/detroit-ann-arbor-mi.json"
    delta_item["determined_by"] = WORK_ORDER
    delta_item["updated_at"] = AS_OF
    delta_item["state_override_reason"] = (
        "%s: founder-approved identity conversion from Delta Hotels by "
        "Marriott Detroit Metro Airport (same address/phone, new brand "
        "flag); route revalidated live immediately before mutation." % WORK_ORDER)

    items[:] = [i for i in items if i["identity_key"] != HAWTHORN_KEY]
    partition_doc["count"] = len(items)

    p_untouched_after = [i for i in items if i["identity_key"] != new_key]
    if p_untouched_before != p_untouched_after:
        raise SystemExit("STOP: an unrelated partition row changed")

    counts: Dict[str, int] = {}
    for item in items:
        counts[item["final_state"]] = counts.get(item["final_state"], 0) + 1
    partition_doc["final_state_counts"] = counts
    partition_doc["final_state_meanings"] = {
        state: PART.STATE_MEANINGS[state] for state in sorted(counts)}
    partition_doc["work_order"] = WORK_ORDER
    partition_doc["as_of"] = AS_OF
    partition_doc["note"] = (
        "%s applied 2 founder identity/census decisions from the Pass 2 "
        "routing review: Delta Hotels by Marriott Detroit Metro Airport "
        "renamed in place to Skyline Hotel Detroit Airport, SureStay "
        "Collection by BW (same address+phone, new brand flag) and moved "
        "to AWAITING_POLICY_OBSERVATION; Hawthorn Suites by Wyndham "
        "Southfield Detroit retired from the active census via the "
        "'closed' disposition (Pittsburgh precedent), preserved in the "
        "duplicate ledger, never converted to a no-pets exclusion. "
        "published=6 and verified_no_pets=5 UNCHANGED." % WORK_ORDER)

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

    # ---- Founder review queue ----
    q_items = queue_doc["items"]
    q_by_key = {q["identity_key"]: q for q in q_items}
    q_untouched_before = [q for q in q_items
                          if q["identity_key"] not in (DELTA_OLD_KEY, HAWTHORN_KEY)]

    delta_q = q_by_key.get(DELTA_OLD_KEY)
    if delta_q is not None:
        delta_q["identity_key"] = new_key
        delta_q["hotel_id"] = new_key
        delta_q["canonical_name"] = DELTA_NEW_NAME
        delta_q["address"] = delta_row["address"]
        delta_q["phone"] = delta_row["phone"]
        delta_q["official_candidate_url"] = DELTA_NEW_URL
        delta_q["current_classification"] = enums.AWAITING_POLICY_OBSERVATION
        delta_q["blocking_reason"] = enums.AWAITING_POLICY_OBSERVATION
        delta_q["requested_evidence"] = "citable pet-policy artifact from the property's own page"
        delta_q["next_action"] = delta_item["next_action"]
        payload = json.dumps({k: v for k, v in delta_q.items() if k != "row_sha256"},
                             sort_keys=True, ensure_ascii=False)
        delta_q["row_sha256"] = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    q_items[:] = [q for q in q_items if q["identity_key"] != HAWTHORN_KEY]
    queue_doc["count"] = len(q_items)
    queue_doc["as_of"] = AS_OF
    queue_doc["work_order"] = WORK_ORDER

    q_untouched_after = [q for q in q_items if q["identity_key"] != new_key]
    if q_untouched_before != q_untouched_after:
        raise SystemExit("STOP: an unrelated queue row changed")

    # ---- Duplicate / disposition ledger ----
    ledger_items = ledger_doc["items"]
    ledger_items.append(OrderedDict([
        ("identity_key", HAWTHORN_KEY),
        ("canonical_name", hawthorn_row["canonical_name"]),
        ("disposition", "closed"),
        ("duplicate_of", ""),
        ("notes", "%s: founder-approved APPROVE_CLOSED_OR_CONVERTED_OUT_OF_"
                  "ACTIVE_CENSUS. Wyndham's own live inventory search near "
                  "the committed address (26700 Central Park Blvd, "
                  "Southfield, MI) returns zero Wyndham-branded properties "
                  "within 7+ miles. Convergent OTA evidence shows a "
                  "post-Wyndham independent rebrand ('Springwood Suites') "
                  "at the same address that is itself marked closed, with "
                  "no independent first-party website ever found for it. "
                  "Revalidated a second time immediately before this "
                  "mutation; no newer active hotel identity was found at "
                  "the address. Not a pet-policy decision -- no exclusion "
                  "was created." % WORK_ORDER),
        ("source", hawthorn_row["source"]),
    ]))
    ledger_doc["counts"]["canonical"] = len(hotels)
    ledger_doc["counts"]["closed"] = ledger_doc["counts"].get("closed", 0) + 1
    ledger_doc["as_of"] = AS_OF
    ledger_doc["work_order"] = WORK_ORDER

    return dict(census_doc=census_doc, partition_doc=partition_doc,
                queue_doc=queue_doc, ledger_doc=ledger_doc, rec=rec, counts=counts,
                delta_new_key=new_key)


def build_evidence_doc(applied: Dict) -> Dict:
    return OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-identity-repair-pass2/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET),
        ("as_of", AS_OF),
        ("founder", FOUNDER),
        ("prior_commit", ROUTING_PASS2_COMMIT),
        ("note", "Founder identity/census review of the 2 rows held "
                 "AWAITING_CENSUS_REVIEW after Pass 2 routing repair. No "
                 "pet-policy fact was read, inferred, or recorded."),
        ("decisions", [
            OrderedDict([
                ("row", "A"),
                ("old_identity_key", DELTA_OLD_KEY),
                ("old_canonical_name", "Delta Hotels by Marriott Detroit Metro Airport"),
                ("founder_decision", "APPROVE_IDENTITY_CONVERSION"),
                ("new_identity_key", applied["delta_new_key"]),
                ("new_canonical_name", DELTA_NEW_NAME),
                ("new_official_url", DELTA_NEW_URL),
                ("revalidation_immediately_before_mutation", OrderedDict([
                    ("street_address_match", True),
                    ("zip_match", True),
                    ("phone_match", True),
                    ("best_western_page_live", True),
                    ("old_marriott_delta_identity_absent", True),
                ])),
                ("disposition", "CURRENT_IDENTITY_RESOLVED"),
                ("new_final_state", enums.AWAITING_POLICY_OBSERVATION),
            ]),
            OrderedDict([
                ("row", "B"),
                ("identity_key", HAWTHORN_KEY),
                ("canonical_name", "Hawthorn Suites by Wyndham Southfield Detroit"),
                ("founder_decision", "APPROVE_CLOSED_OR_CONVERTED_OUT_OF_ACTIVE_CENSUS"),
                ("revalidation_immediately_before_mutation", OrderedDict([
                    ("wyndham_property_still_absent", True),
                    ("no_current_first_party_lodging_identity_found", True),
                    ("springwood_successor_evidence_still_points_to_closure", True),
                    ("no_newer_active_hotel_flag_found", True),
                ])),
                ("disposition", "PROPERTY_CLOSED_OR_CONVERTED"),
                ("mechanism", "Retired via the candidate-ledger 'closed' "
                              "disposition (build_pittsburgh_market_001.py "
                              "precedent) -- removed from the canonical "
                              "census/partition/queue, preserved in "
                              "detroit-ann-arbor-mi_duplicate_ledger.json. "
                              "NOT set to VERIFIED_NO_PETS; no exclusion "
                              "record created; not counted as policy-resolved."),
                ("schema_gap_note", "contracts/enums.py has no terminal "
                                    "'closed hotel' partition final_state "
                                    "(only PUBLISHED_PET_FRIENDLY, "
                                    "VERIFIED_NO_PETS, OUT_OF_CURRENT_"
                                    "CATEGORY are terminal, and the latter "
                                    "means lodging_state=NOT_LODGING / "
                                    "'never was a hotel', which would "
                                    "misrepresent this property's real "
                                    "history). The census-level 'closed' "
                                    "disposition is the faithful existing "
                                    "mechanism; a dedicated terminal-state "
                                    "addition to the shared partition "
                                    "vocabulary is out of scope for this "
                                    "single-market work order."),
            ]),
        ]),
        ("census_before", 143),
        ("census_after", len(applied["census_doc"]["hotels"])),
        ("published", applied["rec"].published),
        ("verified_no_pets", applied["rec"].verified_no_pets),
        ("unresolved_after", sum(n for s, n in applied["counts"].items()
                                 if s not in enums.TERMINAL_STATES)),
    ])


def run(do_apply: bool) -> None:
    applied = apply()
    evidence_doc = build_evidence_doc(applied)

    print("DELTA_NEW_KEY:", applied["delta_new_key"])
    print("CENSUS_BEFORE: 143  CENSUS_AFTER:", len(applied["census_doc"]["hotels"]))
    print("partition_counts:", json.dumps(applied["counts"], sort_keys=True))
    print("published:", applied["rec"].published, "verified_no_pets:", applied["rec"].verified_no_pets)
    print("unresolved_after:", evidence_doc["unresolved_after"])

    if not do_apply:
        print("dry run: nothing written")
        return

    if EVIDENCE_PATH.is_file():
        raise SystemExit("STOP: %s already exists" % EVIDENCE_PATH.name)

    write_lf(EVIDENCE_PATH, evidence_doc)
    write_lf(CENSUS_PATH, applied["census_doc"])
    write_lf(PARTITION_PATH, applied["partition_doc"])
    write_lf(QUEUE_PATH, applied["queue_doc"])
    write_lf(LEDGER_PATH, applied["ledger_doc"])
    print("applied. wrote:", EVIDENCE_PATH.name, CENSUS_PATH.name,
          PARTITION_PATH.name, QUEUE_PATH.name, LEDGER_PATH.name)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    run(do_apply=args.apply)


if __name__ == "__main__":
    main()
