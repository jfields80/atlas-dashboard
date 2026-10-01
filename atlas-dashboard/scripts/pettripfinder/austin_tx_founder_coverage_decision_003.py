"""PTF-AUSTIN-TX-REGISTRATION-AND-STAGING-003 -- record the founder's coverage decision for Austin.

    python -m scripts.pettripfinder.austin_tx_founder_coverage_decision_003 [--write]

Same mechanism and shape as Denver's, San Diego's and Phoenix's ``..._founder_coverage_decision_002.json``. It
TRANSCRIBES the decision the work order states and signs no reviewer name. Every count and every held row is
enumerated from the committed Austin reports, never typed, and the record refuses to write unless they agree with
the cohort the decision names.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-AUSTIN-TX-REGISTRATION-AND-STAGING-003"
SOURCE_READY_ORDER = "PTF-AUSTIN-TX-HARDENED-SOURCE-READY-001"
REFRESH_ORDER = "PTF-AUSTIN-TX-POST-READER-SAFETY-REFRESH-002"
MARKET_ID = "austin-tx"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
OUT = os.path.join(REPORTS, "austin_tx_founder_coverage_decision_003.json")
SOURCE_PACKAGE = "pkg-austin-tx-024e6fb46a9e6934"
SOURCE_DIGEST = "sha256:024e6fb46a9e6934e4884ddb2ac2f4c42756a6154f6f0cd74d6674baf9e665b4"
STALE_PACKAGE = "pkg-austin-tx-3030caf7703a9c57"
SOURCE_COMMIT = "26ab90db"

DECISION_AS_STATED = (
    "The founder approves Austin for launch using the CURRENT SAFE COHORT. COVERAGE READY = YES BY FOUNDER "
    "DECISION. Approved publication cohort: PET-FRIENDLY = 190. Verified no-pets: 63. Keep ALL unresolved/held "
    "rows unpublished. Specifically keep held: 80 rows requiring new spend; 18 dual-brand/shared-campus rows; 5 "
    "operator-domain / Bunkhouse rows; 2 unresolved refusal-language rows: Mountain Star, Strickland Arms; all "
    "other already-committed unresolved rows; same-campus rows outside the qualifying census; Sentral East Austin "
    "unless already canonically excluded/held; all preopening rows; all vacation-ownership/timeshare rows. No new "
    "paid spend is authorized. Do NOT write identity_resolutions.json. Do NOT resolve dual-brand buildings. Do "
    "NOT resolve operator-domain identity questions. Do NOT weaken evidence requirements.")


def _load(p):
    with open(p, encoding="utf-8-sig") as fh:
        return json.load(fh)


def build():
    act = _load(os.path.join(REPORTS, "austin_tx_actionability_001.json"))
    clean = _load(os.path.join(REPORTS, "austin_tx_clean_authority_001.json"))
    census = _load(os.path.join(PKG, "identity_census", "%s.json" % MARKET_ID))
    pf = sum(1 for r in clean["rows"] if r["disposition"] == "CLEAN_PET_FRIENDLY")
    np_ = sum(1 for r in clean["rows"] if r["disposition"] == "CLEAN_VERIFIED_NO_PETS")
    rows = act["rows"]
    by_class = Counter(r["actionability"] for r in rows)
    founder = [r for r in rows if r["actionability"] == "REQUIRES_FOUNDER"]
    dual = [r for r in founder if r["disposition"] == "IDENTITY_MISMATCH_HOLD"]
    domain = [r for r in founder if "two first-party routes" in (r.get("why") or "")]
    refusal = [r for r in founder if r not in dual and r not in domain]
    same_campus = sorted(h["canonical_name"] for h in census.get("non_admitted") or ()
                         if h.get("classification") == "SAME_CAMPUS_DISTINCT_ENTITY")
    sentral = [OrderedDict((("canonical_name", h["canonical_name"]), ("classification", h["classification"])))
               for h in census.get("non_admitted") or () if "sentral" in (h.get("canonical_name") or "").lower()]
    timeshare = sorted(h["canonical_name"] for h in census.get("non_admitted") or ()
                       if "TIMESHARE" in str(h.get("classification_reason") or "").upper())
    expect = OrderedDict((("pet_friendly", (pf, 190)), ("verified_no_pets", (np_, 63)),
                          ("new_spend", (by_class["REQUIRES_NEW_SPEND"], 80)), ("dual_brand", (len(dual), 18)),
                          ("operator_domain", (len(domain), 5)), ("refusal_language", (len(refusal), 2)),
                          ("actionable", (act["actionable_unresolved_remaining"], 0))))
    bad = {k: v for k, v in expect.items() if v[0] != v[1]}
    if bad:
        raise SystemExit("the committed reports disagree with the decision's cohort: %s" % bad)
    if sorted(r["identity_key"] for r in refusal) != ["mountain star lodge and hotel",
                                                      "strickland arms bed and breakfast"]:
        raise SystemExit("the refusal-language rows are not Mountain Star and Strickland Arms: %s" % refusal)
    unresolved = len(rows)
    return OrderedDict((
        ("schema", "ptf-founder-coverage-decision/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("source_package", SOURCE_PACKAGE), ("source_package_digest", SOURCE_DIGEST),
        ("source_ready_order", SOURCE_READY_ORDER), ("refresh_order", REFRESH_ORDER),
        ("source_commit", SOURCE_COMMIT),
        ("stale_package_not_covered_by_this_decision", STALE_PACKAGE),
        ("mechanical_coverage_result", act["COVERAGE_READY"]),
        ("founder_coverage_decision", OrderedDict((
            ("COVERAGE_READY", "YES"), ("basis", "FOUNDER DECISION"), ("decided_in", WORK_ORDER),
            ("decision", "APPROVED FOR LAUNCH WITH CURRENT SAFE COHORT"),
            ("decision_as_stated_in_the_work_order", DECISION_AS_STATED),
            ("basis_points", ["technical source ready (%s)" % act["TECHNICAL_SOURCE_READY"],
                              "repaired shared first-party quote reader applied (%s)" % REFRESH_ORDER,
                              "actionable unresolved = %d" % act["actionable_unresolved_remaining"],
                              "material unsafe publications = 0",
                              "unresolved / new-spend / founder-decision rows safely withheld"])))),
        ("approved_publication_cohort", OrderedDict((("pet_friendly_profiles", pf),
                                                     ("verified_no_pets_exclusions", np_)))),
        ("held_cohort", OrderedDict((
            ("new_spend_rows", by_class["REQUIRES_NEW_SPEND"]),
            ("founder_decision_rows", len(founder)),
            ("router_exhausted_evidence_and_source_silent_rows", by_class["AUTHORIZED_ROUTER_EXHAUSTED"]),
            ("preopening_rows", by_class["HELD_UNTIL_OPENING"]),
            ("unresolved_total", unresolved)))),
        ("founder_decision_rows_reconciled", OrderedDict((
            ("expected", 25), ("enumerated", len(founder)),
            ("source", "markets/reports/austin_tx_actionability_001.json rows with actionability REQUIRES_FOUNDER "
                       "(committed at %s)" % SOURCE_COMMIT),
            ("dual_brand_rows", sorted(r["identity_key"] for r in dual)), ("dual_brand_row_count", len(dual)),
            ("operator_domain_rows", sorted(r["identity_key"] for r in domain)),
            ("operator_domain_row_count", len(domain)),
            ("refusal_language_rows", sorted(r["identity_key"] for r in refusal)),
            ("refusal_language_row_count", len(refusal)),
            ("note", "Mountain Star and Strickland Arms state refusals the repaired shared reader still returns no "
                     "verdict on as captured; they stay held, never published as pet-friendly.")))),
        ("held_outside_the_qualifying_census", OrderedDict((
            ("same_campus_distinct_entity_rows", same_campus), ("sentral_east_austin", sentral),
            ("timeshare_vacation_ownership", timeshare)))),
        ("this_decision_does_not", [
            "authorize any new paid spend (Places or otherwise)",
            "convert any held or unresolved row into a resolved row",
            "publish any held row",
            "write identity_resolutions.json",
            "resolve a dual-brand / shared-campus building or an operator-domain identity question",
            "weaken any evidence requirement",
            "authorize, register or deploy the stale package %s" % STALE_PACKAGE]),
        ("attribution", "This record transcribes the decision the work order states. It is not a review signature: "
                        "no reviewer identity is written here, and nothing in this file claims a human read any "
                        "row."),
    ))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)
    doc = build()
    print(json.dumps(OrderedDict((k, doc[k]) for k in ("approved_publication_cohort", "held_cohort")), indent=1))
    print("founder rows:", doc["founder_decision_rows_reconciled"]["enumerated"],
          "| dual", doc["founder_decision_rows_reconciled"]["dual_brand_row_count"],
          "| domain", doc["founder_decision_rows_reconciled"]["operator_domain_row_count"],
          "| refusal", doc["founder_decision_rows_reconciled"]["refusal_language_row_count"])
    if args.write:
        with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(doc, fh, indent=1, ensure_ascii=False)
            fh.write("\n")
        print("written", os.path.relpath(OUT, _DASH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
