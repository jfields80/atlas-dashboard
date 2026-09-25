"""PTF-JACKSONVILLE-FL-HARDENED-SOURCE-READY-001 -- Phase 10: BringFido gap reconciliation (identity only, never policy).

BringFido stays DISCOVERY / GAP CHALLENGE ONLY. Its JSON-LD carries no street address, so a lead is matched by NAME
against every census node -- the admitted identities AND the non-admitted graph residue (outside-market, non-hotel,
vacation-rental, duplicate, review) -- so each lead lands in exactly one class:

  EXACT_ATLAS_MATCH      the lead's normalised name equals an admitted identity's name or alias
  ALIAS                  containment match against an admitted identity (brand-suffix / city-suffix variants)
  DUPLICATE              a second BringFido listing of an identity another lead already matched
  OUTSIDE                matched to a census node refused by geography, or its own name states a refused place
  NON_HOTEL / VACATION_RENTAL / CONDO_RESIDENCE / TIMESHARE
                         matched to a census node refused under that class, or its own name reads as one
  REVIEW                 matched to a census node held for identity review / name-only
  TRUE_MISSING           a lodging-establishment name no census node carries (worked by
                         jacksonville_fl_competitor_additions_001 through an authoritative identity lane)

A name match PROPOSES an identity; it never decides one. BringFido's pet claims are never read.

Output:
  launch_packages/pettripfinder/markets/reports/jacksonville_fl_competitor_reconciliation_001.json
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import jacksonville_fl_census_reconciliation_001 as CR  # noqa: E402

WORK_ORDER = "PTF-JACKSONVILLE-FL-HARDENED-SOURCE-READY-001"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CENSUS = os.path.join(PKG, "identity_census", "jacksonville-fl.json")
COMPETITOR = os.path.join(REPORTS, "jacksonville_fl_competitor_challenge_001.json")
CLEAN = os.path.join(REPORTS, "jacksonville_fl_clean_authority_001.json")
OUT = os.path.join(REPORTS, "jacksonville_fl_competitor_reconciliation_001.json")

_STOP = re.compile(r"\b(hotel|hotels|inn|suites?|by|the|and|resort|resorts|motel|at|of|a|an|hilton|marriott|"
                   r"collection|autograph|tapestry|ascend|curio|tribute|jacksonville|jax|amelia|fernandina|ponte vedra|sawgrass|orange park|fleming island|yulee|baymeadows|deerwood|butler|mayport|southbank|riverside|avondale|mandarin|bartram|arlington|fl|florida|spa|beach)\b", re.I)
_NONWORD = re.compile(r"[^a-z0-9 ]")
_LODGING = re.compile(r"\b(hotel|inn|suites?|motel|lodge|hostel|resort|b&b|bed and breakfast)\b", re.I)
_VR = re.compile(r"\b(cottage|bungalow|home|homes|condo(?:minium)?s?|apartments?|apt|getaway|retreat|casa|casita|"
                 r"bedroom|br\b|studio|house|cabin|villas?|unit \d|#\d|private (?:home|pool)|vacation rentals?|"
                 r"loft|penthouse|ocean ?view|oceanfront \d|airbnb|vrbo|sonder|kasa|vacasa|luxury rentals?|"
                 r"\d+\s*/\s*\d+|\d\s*br\b)\b", re.I)
#: A unit number or unit description inside a listing title is a short-term-rental unit, not an establishment.
_UNIT = re.compile(r"\b(suite|hotel|unit|apt)\s+#?\d{3,4}\b|\bprivate (suite|condo|room|studio)\b|\b\d-bedroom\b|"
                   r"\bbedroom\b|@|\b\d+\s*/\s*\d+\b|homes\s+-|\bretreat collection\b|\bsleek escape\b|"
                   r"\b(global luxury suites|avantstay|sobe lux|luxury suites on|access to hotel amenities|stunning|"
                   r"perfect for|stay at the)\b", re.I)
_RV = re.compile(r"\brv (resort|park)\b|\bcampground\b", re.I)
#: Florida places outside this market that BringFido's radius widening pulls onto small-city pages.
_OTHER_FLORIDA = re.compile(r"\b(vero beach|tallahassee|jacksonville|pensacola|destin|cocoa beach|port canaveral|"
                            r"marco (island|polo)|naples|orlando|tampa|key west|key largo|islamorada|palm beach|"
    r"st augustine|saint augustine|palm coast|daytona|gainesville|ormond|palatka|"
    r"kingsland|st marys|brunswick|st simons|jekyll|savannah|waycross|"
                            r"fort lauderdale|hollywood|hallandale|pompano|deerfield|miami|daytona|st\.? augustine|sarasota|stuart|port st\.? lucie|"
                            r"fort myers|clearwater|panama city|gainesville|ocala|melbourne)\b", re.I)
_TIMESHARE = re.compile(r"\b(vacation club|grand vacations|hgv|marriott vacation|timeshare|residence club)\b", re.I)
_CONDO_RES = re.compile(r"\b(residences?|condo[- ]hotel)\b", re.I)
_REFUSED_CLASS = {
    "OUTSIDE_MARKET": "OUTSIDE", "NON_LODGING": None, "DUPLICATE_LISTING": "DUPLICATE",
    "IDENTITY_REVIEW_REQUIRED": "REVIEW", "NAME_ONLY_UNRESOLVED": "REVIEW",
    "SAME_CAMPUS_DISTINCT_ENTITY": "REVIEW", "SAME_IDENTITY_REBRAND_SUCCESSOR": "REVIEW",
}


def norm(name):
    n = _NONWORD.sub(" ", (name or "").lower())
    n = _STOP.sub(" ", n)
    return " ".join(n.split())


def _load(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def nonlodging_class(reason):
    head = (reason or "").split(" --", 1)[0].strip()
    if head in ("VACATION_RENTAL", "TIMESHARE", "RESORT_RESIDENCE"):
        return {"RESORT_RESIDENCE": "CONDO_RESIDENCE"}.get(head, head)
    if "rental" in (reason or "").lower() or "apartment" in (reason or "").lower() or "condo" in (reason or "").lower():
        return "VACATION_RENTAL"
    return "NON_HOTEL"


def build():
    census = _load(CENSUS)
    comp = _load(COMPETITOR)
    clean = _load(CLEAN, {}) or {}
    disp = {r["identity_key"]: r["disposition"] for r in clean.get("rows", [])}
    admitted, refused = {}, {}
    for h in census["hotels"]:
        for a in [h["canonical_name"]] + list(h.get("identity_key_aliases") or []):
            if norm(a):
                admitted.setdefault(norm(a), h)
    for r in census.get("non_admitted", []):
        # competitor-only nodes are the leads themselves -- matching a lead to its own node proves nothing
        if set(r.get("lanes") or []) <= {"COMPETITOR_LEAD"}:
            continue
        if norm(r["canonical_name"]):
            refused.setdefault(norm(r["canonical_name"]), r)
    adm_keys = sorted(admitted, key=lambda k: (-len(k), k))
    matched_ids = set()
    rows, counts = [], Counter()
    for lead in comp["leads"]:
        name = lead["name"]
        n = norm(name)
        rec = OrderedDict([("bringfido_name", name), ("bringfido_url", lead["bringfido_url"]),
                           ("first_seen_city", lead.get("first_seen_city")), ("normalized", n)])
        hit, kind = None, None
        if n and n in admitted:
            hit, kind = admitted[n], "EXACT_ATLAS_MATCH"
        elif n:
            for k in adm_keys:
                if len(k) >= 6 and len(n) >= 6 and (k in n or n in k):
                    hit, kind = admitted[k], "ALIAS"
                    break
        if hit is not None:
            if hit["identity_key"] in matched_ids:
                kind = "DUPLICATE"
            matched_ids.add(hit["identity_key"])
            rec["classification"] = kind
            rec["matched_identity_key"] = hit["identity_key"]
            rec["matched_canonical_name"] = hit["canonical_name"]
            rec["matched_disposition"] = disp.get(hit["identity_key"])
        elif n in refused:
            r = refused[n]
            cls = _REFUSED_CLASS.get(r["classification"], "REVIEW")
            if r["classification"] == "NON_LODGING":
                cls = nonlodging_class(r.get("classification_reason"))
            rec["classification"] = cls
            rec["matched_non_admitted"] = r["canonical_name"]
            rec["matched_non_admitted_reason"] = (r.get("classification_reason") or "")[:240]
        else:
            places = CR.places_in(name)
            if (places and places <= CR._OUT_OF_MARKET_PLACES) or _OTHER_FLORIDA.search(name):
                cls = "OUTSIDE"
            elif _RV.search(name):
                cls = "NON_HOTEL"
            elif _UNIT.search(name):
                cls = "VACATION_RENTAL"
            elif _TIMESHARE.search(name):
                cls = "TIMESHARE"
            elif _VR.search(name) and not re.search(r"\b(hotel|motel|inn)\b", name, re.I):
                cls = "VACATION_RENTAL"
            elif _CONDO_RES.search(name) and not _LODGING.search(name):
                cls = "CONDO_RESIDENCE"
            elif not _LODGING.search(name):
                cls = "REVIEW"
            else:
                cls = "TRUE_MISSING"
            rec["classification"] = cls
        counts[rec["classification"]] += 1
        rows.append(rec)
    matched = counts["EXACT_ATLAS_MATCH"] + counts["ALIAS"] + counts["DUPLICATE"]
    policy_unresolved = sum(1 for r in rows if r.get("matched_identity_key") and r["classification"] != "DUPLICATE"
                            and r.get("matched_disposition") not in ("CLEAN_PET_FRIENDLY", "CLEAN_VERIFIED_NO_PETS"))
    return OrderedDict([
        ("schema", "ptf-competitor-reconciliation/1.0"), ("work_order", WORK_ORDER), ("market_id", "jacksonville-fl"),
        ("competitor", "BringFido"), ("never_policy_authority", True),
        ("competitor_raw_discovery", comp["raw_captured"]),
        ("normalized_unique", comp["normalized_unique"]),
        ("matched_to_census", matched),
        ("matched_distinct_identities", len(matched_ids)),
        ("matched_but_policy_unresolved", policy_unresolved),
        ("true_missing_qualifying_candidates", counts["TRUE_MISSING"]),
        ("excluded_stale_outside", sum(counts[c] for c in ("OUTSIDE", "NON_HOTEL", "VACATION_RENTAL",
                                                             "CONDO_RESIDENCE", "TIMESHARE"))),
        ("review", counts["REVIEW"]),
        ("counts", OrderedDict(sorted(counts.items()))),
        ("method",
         "Name-only matching (BringFido publishes no street): exact normalised name, then containment of >= 6 "
         "characters against admitted identities; otherwise against the census graph's non-admitted residue (outside, "
         "non-hotel, rental, review) so each refusal carries its reason; otherwise a name-pattern triage. A match "
         "proposes, never decides; TRUE_MISSING leads are worked only through an authoritative identity lane."),
        ("rows", rows),
    ])


def main():
    rep = build()
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rep, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print(json.dumps(rep["counts"]), "matched", rep["matched_to_census"], "true-missing",
          rep["true_missing_qualifying_candidates"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
