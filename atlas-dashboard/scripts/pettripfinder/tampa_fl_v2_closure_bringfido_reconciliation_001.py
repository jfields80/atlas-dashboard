"""PTF-TAMPA-FL-V2-COVERAGE-CLOSURE-002 -- Phase 10 BringFido gap reconciliation.

BringFido stays DISCOVERY / IDENTITY CHALLENGE ONLY -- never policy authority
(the source-ready capture already restricted this file's `leads` to BringFido's
own Hotel-typed JSON-LD, so vacation-rental/timeshare exclusion is already
done upstream; this pass only reconciles identity).

Matching is name-based (BringFido's JSON-LD carries no street address): each
lead is normalized (case/punctuation/common-suffix folded) and matched against
every census identity_key alias by exact normalized-name equality, then by
containment for brand-suffix variants (e.g. "... by Hilton"). A name match
PROPOSES an identity; it is never treated as stronger than that.

Output:
  launch_packages/pettripfinder/markets/reports/tampa_fl_v2_closure_bringfido_reconciliation_001.json
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CENSUS = os.path.join(PKG, "identity_census_proposed", "tampa-fl.json")
COMPETITOR = os.path.join(REPORTS, "tampa_fl_v2_competitor_challenge_001.json")
FINAL_PARTITION = os.path.join(PKG, "markets", "staging", "tampa-fl", "launch_package",
                               "tampa_fl_final_partition_v2_001.json")
OUT = os.path.join(REPORTS, "tampa_fl_v2_closure_bringfido_reconciliation_001.json")

_STOPWORDS = re.compile(
    r"\b(hotel|inn|suites?|by|the|and|resort|motel|at|of|a|an|hilton|marriott|"
    r"garden|collection|autograph|tapestry|ascend|curio|tribute)\b", re.I)
_NONWORD = re.compile(r"[^a-z0-9 ]")
_LODGING_KW = re.compile(
    r"\b(hotel|inn|suites?|motel|lodge|hostel|bed and breakfast|b&b)\b", re.I)
_VR_KW = re.compile(
    r"\b(cottage|bungalow|home|condo(?:minium)?|apartment|apt|getaway|retreat|casa|casita|"
    r"bedroom|br\b|studio apt|house|cabin|villa|unit \d|#\d|private (?:home|pool)|"
    r"vacation rental|gated resort community)\b", re.I)
_RV_KW = re.compile(r"\brv (?:resort|park)\b|\b55\+\b", re.I)
_RESORT_CONDO_KW = re.compile(r"\bresort\b.{0,4}\bcondo|condo.{0,4}\bresort\b", re.I)
#: A bedroom-count / unit-number pattern ("2/2", "2BR", "Unit 308", "#71") is a
#: short-term-rental listing convention even when the name also contains a
#: word like "suite" -- caught live during closure after "Gulf Front 2/2
#: Suite at Oceana" (a condo unit) matched the bare _LODGING_KW check.
_UNIT_PATTERN_KW = re.compile(
    r"\d\s*/\s*\d\b|\b\d\s*br\b|\bunit\s*\d|#\s*\d|\bsuite\s*\d{2,}\b", re.I)


def norm(name):
    n = (name or "").lower()
    n = _NONWORD.sub(" ", n)
    n = _STOPWORDS.sub(" ", n)
    return " ".join(n.split())


def main():
    census = json.load(open(CENSUS, encoding="utf-8"))
    partition = json.load(open(FINAL_PARTITION, encoding="utf-8"))
    disp_by_key = {i["identity_key"]: i["disposition"] for i in partition["items"]}
    competitor = json.load(open(COMPETITOR, encoding="utf-8"))
    leads = competitor["leads"]

    census_by_norm = {}
    for h in census["hotels"]:
        n = norm(h["canonical_name"])
        if n:
            census_by_norm.setdefault(n, []).append(h)
        for alias in h.get("identity_key_aliases", []):
            na = norm(alias)
            if na:
                census_by_norm.setdefault(na, []).append(h)

    exact_norms = sorted(census_by_norm.keys(), key=len, reverse=True)

    classified = []
    counts = OrderedDict([
        ("EXACT_CENSUS_MATCH", 0), ("CONTAINMENT_MATCH", 0),
        ("MATCHED_ALREADY_VERIFIED_PET_FRIENDLY", 0), ("MATCHED_ALREADY_VERIFIED_NO_PETS", 0),
        ("MATCHED_BUT_POLICY_UNRESOLVED", 0),
        ("VACATION_RENTAL", 0), ("RESORT_RESIDENCE", 0), ("NON_HOTEL_RV_PARK", 0),
        ("TRUE_MISSING_QUALIFYING_CANDIDATE", 0), ("UNMATCHED_IDENTITY_REVIEW", 0),
    ])
    for lead in leads:
        n = norm(lead["name"])
        match_keys = []
        match_kind = None
        if n in census_by_norm:
            match_keys = census_by_norm[n]
            match_kind = "EXACT_CENSUS_MATCH"
        else:
            for cn in exact_norms:
                if len(cn) >= 6 and (cn in n or n in cn):
                    match_keys = census_by_norm[cn]
                    match_kind = "CONTAINMENT_MATCH"
                    break
        rec = OrderedDict([("bringfido_name", lead["name"]), ("bringfido_url", lead["bringfido_url"]),
                           ("first_seen_city", lead.get("first_seen_city")),
                           ("normalized", n)])
        if not match_kind:
            raw_name = lead["name"]
            if _RV_KW.search(raw_name):
                cls = "NON_HOTEL_RV_PARK"
            elif _RESORT_CONDO_KW.search(raw_name) or (not _LODGING_KW.search(raw_name) and re.search(r"\bresort\b", raw_name, re.I) and re.search(r"\bcondo|\bunit\b|#\d", raw_name, re.I)):
                cls = "RESORT_RESIDENCE"
            elif _UNIT_PATTERN_KW.search(raw_name):
                cls = "VACATION_RENTAL"
            elif not _LODGING_KW.search(raw_name) and _VR_KW.search(raw_name):
                cls = "VACATION_RENTAL"
            elif not _LODGING_KW.search(raw_name):
                # No lodging-establishment keyword and no recognized VR/resort-residence
                # pattern either -- most of these are still short-term-rental style listing
                # titles (a street address, a room description); held as VACATION_RENTAL
                # per the Phase 5 default (public-lodging status must be affirmatively
                # shown, not assumed), not counted toward the hotel-identity gap.
                cls = "VACATION_RENTAL"
            else:
                cls = "TRUE_MISSING_QUALIFYING_CANDIDATE"
            rec["classification"] = cls
            counts[cls] += 1
            classified.append(rec)
            continue
        counts[match_kind] += 1
        m = match_keys[0]
        rec["matched_identity_key"] = m["identity_key"]
        rec["matched_canonical_name"] = m["canonical_name"]
        disp = disp_by_key.get(m["identity_key"])
        rec["matched_disposition"] = disp
        if disp == "CLEAN_PET_FRIENDLY":
            rec["classification"] = "MATCHED_ALREADY_VERIFIED_PET_FRIENDLY"
            counts["MATCHED_ALREADY_VERIFIED_PET_FRIENDLY"] += 1
        elif disp == "CLEAN_VERIFIED_NO_PETS":
            rec["classification"] = "MATCHED_ALREADY_VERIFIED_NO_PETS"
            counts["MATCHED_ALREADY_VERIFIED_NO_PETS"] += 1
        else:
            rec["classification"] = "MATCHED_BUT_POLICY_UNRESOLVED"
            counts["MATCHED_BUT_POLICY_UNRESOLVED"] += 1
        classified.append(rec)

    matched_total = counts["EXACT_CENSUS_MATCH"] + counts["CONTAINMENT_MATCH"]
    out = OrderedDict([
        ("schema", "ptf-tampa-fl-v2-closure-bringfido-reconciliation/1.0"),
        ("work_order", "PTF-TAMPA-FL-V2-COVERAGE-CLOSURE-002"),
        ("bringfido_raw", competitor["raw_captured"]),
        ("bringfido_normalized_unique", competitor["normalized_unique"]),
        ("matched_to_census", matched_total),
        ("already_verified_pet_friendly", counts["MATCHED_ALREADY_VERIFIED_PET_FRIENDLY"]),
        ("matched_but_policy_unresolved", counts["MATCHED_BUT_POLICY_UNRESOLVED"]),
        ("already_verified_no_pets", counts["MATCHED_ALREADY_VERIFIED_NO_PETS"]),
        ("vacation_rental_excluded", counts["VACATION_RENTAL"]),
        ("resort_residence_excluded", counts["RESORT_RESIDENCE"]),
        ("non_hotel_rv_park_excluded", counts["NON_HOTEL_RV_PARK"]),
        ("true_missing_qualifying_candidates", counts["TRUE_MISSING_QUALIFYING_CANDIDATE"]),
        ("unmatched_identity_review", counts["UNMATCHED_IDENTITY_REVIEW"]),
        ("true_missing_qualifying_note",
         "BringFido carries no street address; a name match PROPOSES an identity, never decides one (PHASE 10). "
         "Unmatched leads are name-pattern classified: a lodging-establishment keyword (hotel/inn/suites/motel/"
         "lodge) with no vacation-rental/RV/resort-residence pattern is TRUE_MISSING_QUALIFYING_CANDIDATE and is "
         "worked in this pass (census_addition step); everything else (no lodging keyword, or an RV-park/"
         "resort-condo pattern) is excluded and never promoted to census membership. This heuristic can "
         "misclassify an edge case in either direction; it is a bounded triage, not an authority."),
        ("counts", counts),
        ("rows", classified),
    ])
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print(json.dumps(counts, indent=1))


if __name__ == "__main__":
    main()
