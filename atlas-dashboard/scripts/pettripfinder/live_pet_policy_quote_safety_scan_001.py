"""PTF-FIRST-PARTY-QUESTION-NEGATION-AND-LIVE-CORRECTION-001 -- the live pet-policy quote safety scan.

READ ONLY. Classifies every LIVE pet-friendly policy record and every live verified-no-pets exclusion by the quotes
it cites, through the SHARED first-party reader exactly as FAST rule C applies it
(``first_party_binding.classify_quote`` over each publication-grade ``pets_allowed`` entry, with the other quotes
cited from the same page as context), and says, per record, what the reader makes of it.

WHY IT IMPORTS FROM THE WORKING DIRECTORY
------------------------------------------
The same file measures the reader BEFORE and AFTER a repair: run from a checkout of the old tree it imports the old
reader, run from this tree it imports the new one. ``scan`` therefore puts the current working directory (an
``atlas-dashboard`` checkout) first on ``sys.path``; ``compare`` joins two scans into the report.

    cd <old atlas-dashboard> && python <this file> scan --label before --out before.json
    cd <new atlas-dashboard> && python <this file> scan --label after  --out after.json
    python <this file> compare --before before.json --after after.json
    cd <corrected atlas-dashboard> && python <this file> scan --label candidate --out candidate.json
    python <this file> rescan --before before.json --candidate candidate.json    # the corrected candidate

CLASSES (per live pet-friendly record)
---------------------------------------
  AFFIRMATIVE_ACCEPTANCE  at least one cited pets_allowed quote is an operative acceptance
  EXPLICIT_REFUSAL        a cited pets_allowed quote reads as a refusal of pets
  QUESTION_ONLY           no operative acceptance, no refusal, and the acceptance the OLD reader took sat in a
                          question (decided in ``compare``; a scan alone reports NOT_OPERATIVE)
  AMBIGUOUS               the quote both asserts and denies, or the reader withholds the acceptance
  UNREADABLE              no publication-grade pets_allowed quote at all
  OTHER                   anything else, named by the reader's own class
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from collections import Counter, OrderedDict

WORK_ORDER = "PTF-FIRST-PARTY-QUESTION-NEGATION-AND-LIVE-CORRECTION-001"
SCHEMA = "ptf-live-pet-policy-quote-safety-scan/1.0"
PKG_REL = os.path.join("launch_packages", "pettripfinder")
REPORT_REL = os.path.join(PKG_REL, "markets", "reports", "live_pet_policy_quote_safety_scan_001.json")
RESCAN_REL = os.path.join(PKG_REL, "markets", "reports", "live_pet_policy_quote_safety_rescan_001.json")


def _live_markets(pkg):
    """The markets the production bundle admits: FOUNDER_AUTHORIZED_FOR_LAUNCH in the participation record."""
    doc = json.load(open(os.path.join(os.path.dirname(os.path.dirname(pkg)), "deploy", "netlify",
                                      "launch_participation.json"), encoding="utf-8"))
    return sorted(r["market_id"] for r in doc["markets"] if r.get("launch_status") == "FOUNDER_AUTHORIZED_FOR_LAUNCH")


def scan(label):
    sys.path.insert(0, os.getcwd())
    from scripts.pettripfinder import first_party_binding as FPB
    from scripts.pettripfinder.brightdata import policy_reading as READER
    from scripts.pettripfinder.contracts import enums
    from scripts.pettripfinder.contracts import evidence as EVIDENCE

    pkg = os.path.join(os.getcwd(), PKG_REL)
    markets = _live_markets(pkg)
    accept_fields = set(EVIDENCE.coverage_names("pets_allowed"))
    records = []
    repo = os.path.dirname(os.path.dirname(pkg))
    for m in markets:
        # The package a market publishes is the one its release contract names (Columbus, the anchor market,
        # publishes the legacy hotel_policy_facts.json); a glob over hotel_policy_facts_*.json would miss it.
        contract = json.load(open(os.path.join(repo, "deploy", "netlify", "release_contracts", "%s.json" % m),
                                  encoding="utf-8"))
        path = os.path.join(repo, contract["policy_package"]["path"])
        doc = json.load(open(path, encoding="utf-8"))
        for h in doc.get("hotels") or ():
            if (h.get("facts") or {}).get("pets_allowed") is not True:
                continue
            if h.get("market_id") not in (None, "", m):
                continue
            pub = [e for e in h.get("evidence") or () if e.get("artifact_class") == enums.PUBLICATION_GRADE_EVIDENCE]
            acc = [e for e in pub if str(e.get("field") or "") in accept_fields]
            quotes = []
            for e in acc:
                ctx = " ".join(dict.fromkeys(str(x.get("quote") or "") for x in pub
                                             if x is not e and x.get("artifact_sha256") == e.get("artifact_sha256")))
                q = str(e.get("quote") or "")
                cls, why = FPB.classify_quote(q, kind=FPB.KIND_PET_FRIENDLY, context=ctx)
                quotes.append(OrderedDict([("quote", q), ("source_url", e.get("source_url")),
                                           ("artifact_sha256", e.get("artifact_sha256")),
                                           ("reader_pets_allowed", READER.parse(q).pets_allowed),
                                           ("classify", cls), ("why", why[:300])]))
            if not acc:
                klass = "UNREADABLE"
            elif any(q["classify"] == FPB.ELIGIBLE for q in quotes):
                klass = "AFFIRMATIVE_ACCEPTANCE"
            elif any(q["reader_pets_allowed"] is False for q in quotes):
                klass = "EXPLICIT_REFUSAL"
            elif any(q["classify"] == FPB.CLASS_QUOTE_NOT_OPERATIVE for q in quotes):
                klass = "NOT_OPERATIVE"
            elif any(q["classify"] == FPB.CLASS_QUOTE_CONTRADICTS for q in quotes):
                klass = "AMBIGUOUS"
            else:
                klass = "OTHER"
            records.append(OrderedDict([("market_id", m), ("identity_key", h.get("identity_key")),
                                        ("name", h.get("name")), ("class", klass), ("quotes", quotes)]))
    excl = json.load(open(os.path.join(pkg, "hotel_exclusions.json"), encoding="utf-8"))["exclusions"]
    live = set(markets)
    exclusions = []
    for x in excl:
        if x.get("market_id") not in live or x.get("exclusion_state") != "VERIFIED_NO_PETS":
            continue
        q = str(x.get("evidence_quote") or "")
        cls, why = FPB.classify_quote(q, kind=FPB.KIND_NO_PETS, context=str(x.get("evidence_context") or ""))
        exclusions.append(OrderedDict([("market_id", x["market_id"]), ("exclusion_id", x.get("exclusion_id")),
                                       ("name", x.get("canonical_name")), ("classify", cls)]))
    return OrderedDict([("schema", SCHEMA + "/scan"), ("label", label), ("markets", markets),
                        ("pet_friendly_records", records), ("no_pets_exclusions", exclusions)])


def compare(before, after):
    b = {(r["market_id"], r["identity_key"]): r for r in before["pet_friendly_records"]}
    a = {(r["market_id"], r["identity_key"]): r for r in after["pet_friendly_records"]}
    assert set(a) == set(b), "the two scans must read the same live corpus"
    rows = []
    for k in sorted(a):
        ra, rb = a[k], b[k]
        klass = ra["class"]
        if klass == "NOT_OPERATIVE" and rb["class"] == "AFFIRMATIVE_ACCEPTANCE":
            klass = "QUESTION_ONLY"
        elif klass == "NOT_OPERATIVE":
            klass = "OTHER"
        before_class = "OTHER" if rb["class"] == "NOT_OPERATIVE" else rb["class"]
        rows.append(OrderedDict([("market_id", k[0]), ("identity_key", k[1]), ("name", ra["name"]),
                                 ("class_before", before_class), ("class", klass),
                                 ("defect", klass != "AFFIRMATIVE_ACCEPTANCE"),
                                 ("quotes", ra["quotes"])]))
    bx = {(x["market_id"], x["exclusion_id"]): x for x in before["no_pets_exclusions"]}
    ax = {(x["market_id"], x["exclusion_id"]): x for x in after["no_pets_exclusions"]}
    excl_moved = [OrderedDict([("market_id", k[0]), ("exclusion_id", k[1]), ("name", ax[k]["name"]),
                               ("before", bx[k]["classify"]), ("after", ax[k]["classify"])])
                  for k in sorted(ax) if ax[k]["classify"] != bx[k]["classify"]]
    counts = Counter(r["class"] for r in rows)
    defects = [r for r in rows if r["defect"]]
    return OrderedDict([
        ("schema", SCHEMA), ("work_order", WORK_ORDER),
        ("what_this_is", "Every LIVE pet-friendly policy record (the root hotel_policy_facts package of every "
                         "FOUNDER_AUTHORIZED_FOR_LAUNCH market) classified by its cited pets_allowed quotes through the "
                         "shared reader exactly as FAST rule C applies it, BEFORE and AFTER the question / negation "
                         "repair; and every live verified-no-pets exclusion re-read the same way."),
        ("markets_scanned", len(after["markets"])), ("markets", after["markets"]),
        ("LIVE_PET_FRIENDLY_RECORDS_SCANNED", len(rows)),
        ("classes_after_repair", OrderedDict(sorted(counts.items()))),
        ("classes_before_repair", OrderedDict(sorted(Counter(r["class_before"] for r in rows).items()))),
        ("EXPLICIT_REFUSAL_CONTRADICTIONS", counts.get("EXPLICIT_REFUSAL", 0)),
        ("QUESTION_ONLY_RECORDS", counts.get("QUESTION_ONLY", 0)),
        ("AMBIGUOUS", counts.get("AMBIGUOUS", 0)),
        ("OTHER_DEFECTS", counts.get("OTHER", 0) + counts.get("UNREADABLE", 0)),
        ("records_whose_class_moved", sum(1 for r in rows if r["class"] != r["class_before"])),
        ("defects", [OrderedDict((k, v) for k, v in r.items()) for r in defects]),
        ("LIVE_NO_PETS_EXCLUSIONS_SCANNED", len(ax)),
        ("no_pets_exclusions_eligible_before", sum(1 for x in bx.values() if x["classify"] == "ELIGIBLE")),
        ("no_pets_exclusions_eligible_after", sum(1 for x in ax.values() if x["classify"] == "ELIGIBLE")),
        ("no_pets_exclusions_whose_class_moved", excl_moved),
    ])


def rescan(before, candidate):
    """The corrected candidate, judged by the repaired reader.

    A candidate record is QUESTION_ONLY when the repaired reader finds no operative acceptance and no refusal and
    the reader it replaced DID accept it -- the same rule ``compare`` applies. The candidate set is the live set
    minus what the correction removed, so the two scans are joined by identity rather than required to match.
    """
    b = {(r["market_id"], r["identity_key"]): r for r in before["pet_friendly_records"]}
    c = {(r["market_id"], r["identity_key"]): r for r in candidate["pet_friendly_records"]}
    rows = []
    for k in sorted(c):
        rc, rb = c[k], b.get(k)
        klass = rc["class"]
        if klass == "NOT_OPERATIVE":
            klass = "QUESTION_ONLY" if rb and rb["class"] == "AFFIRMATIVE_ACCEPTANCE" else "OTHER"
        rows.append(OrderedDict([("market_id", k[0]), ("identity_key", k[1]), ("name", rc["name"]),
                                 ("class_under_prior_reader", (rb or {}).get("class")), ("class", klass),
                                 ("quotes", rc["quotes"])]))
    counts = Counter(r["class"] for r in rows)
    return OrderedDict([
        ("schema", SCHEMA + "/rescan"), ("work_order", WORK_ORDER),
        ("what_this_is", "Every pet-friendly record of the CORRECTED candidate (the root policy package of every "
                         "FOUNDER_AUTHORIZED_FOR_LAUNCH market in the corrected tree) re-read by the repaired "
                         "reader exactly as FAST rule C applies it."),
        ("markets_scanned", len(candidate["markets"])),
        ("CANDIDATE_PET_FRIENDLY_RECORDS_SCANNED", len(rows)),
        ("live_records_not_in_candidate", sorted("%s/%s" % k for k in set(b) - set(c))),
        ("candidate_records_not_live", sorted("%s/%s" % k for k in set(c) - set(b))),
        ("classes", OrderedDict(sorted(counts.items()))),
        ("PET_FRIENDLY_RECORDS_WITH_EXPLICIT_REFUSAL", counts.get("EXPLICIT_REFUSAL", 0)),
        ("QUESTION_ONLY_PET_FRIENDLY_RECORDS", counts.get("QUESTION_ONLY", 0)),
        ("AMBIGUOUS", counts.get("AMBIGUOUS", 0)),
        ("records_the_prior_reader_also_did_not_accept",
         [OrderedDict([("market_id", r["market_id"]), ("identity_key", r["identity_key"]), ("class", r["class"]),
                       ("class_under_prior_reader", r["class_under_prior_reader"])])
          for r in rows if r["class"] != "AFFIRMATIVE_ACCEPTANCE"]),
    ])


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("scan")
    s.add_argument("--label", required=True)
    s.add_argument("--out", required=True)
    c = sub.add_parser("compare")
    c.add_argument("--before", required=True)
    c.add_argument("--after", required=True)
    c.add_argument("--out", default=None)
    r = sub.add_parser("rescan")
    r.add_argument("--before", required=True)
    r.add_argument("--candidate", required=True)
    r.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    if args.cmd == "rescan":
        doc = rescan(json.load(open(args.before, encoding="utf-8")), json.load(open(args.candidate, encoding="utf-8")))
        out = args.out or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", RESCAN_REL)
        with open(out, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(doc, fh, indent=1, ensure_ascii=False)
            fh.write("\n")
        for k in ("CANDIDATE_PET_FRIENDLY_RECORDS_SCANNED", "classes", "PET_FRIENDLY_RECORDS_WITH_EXPLICIT_REFUSAL",
                  "QUESTION_ONLY_PET_FRIENDLY_RECORDS", "AMBIGUOUS", "live_records_not_in_candidate",
                  "candidate_records_not_live"):
            print(k, "=", doc[k])
        return 0 if not doc["PET_FRIENDLY_RECORDS_WITH_EXPLICIT_REFUSAL"] and not doc["QUESTION_ONLY_PET_FRIENDLY_RECORDS"] else 1
    if args.cmd == "scan":
        doc = scan(args.label)
        out = args.out
    else:
        doc = compare(json.load(open(args.before, encoding="utf-8")), json.load(open(args.after, encoding="utf-8")))
        out = args.out or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", REPORT_REL)
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    if args.cmd == "compare":
        for k in ("LIVE_PET_FRIENDLY_RECORDS_SCANNED", "classes_before_repair", "classes_after_repair",
                  "EXPLICIT_REFUSAL_CONTRADICTIONS", "QUESTION_ONLY_RECORDS", "AMBIGUOUS", "OTHER_DEFECTS",
                  "LIVE_NO_PETS_EXCLUSIONS_SCANNED", "no_pets_exclusions_eligible_before",
                  "no_pets_exclusions_eligible_after"):
            print(k, "=", doc[k])
        for r in doc["defects"]:
            print("  %-22s %-24s %-44s %s" % (r["market_id"], r["class"], r["name"][:44],
                                            (r["quotes"][0]["quote"] if r["quotes"] else "")[:110]))
        for x in doc["no_pets_exclusions_whose_class_moved"]:
            print("  NP MOVED", x)
    else:
        print(args.label, "pf", len(doc["pet_friendly_records"]), "np", len(doc["no_pets_exclusions"]),
              Counter(r["class"] for r in doc["pet_friendly_records"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
