"""PTF-FORT-MYERS-FL-HARDENED-SOURCE-READY-001 -- Phases 13, 14 and 20: the pre-seal publication-safety audit.

Reads the STAGED policy package and proposed authority (never fetches) and checks every published record against
the order's hard publication rules, with the SHARED first-party reader that FAST rule C re-runs at seal time:

  PET-FRIENDLY WITH EXPLICIT REFUSAL = 0   no pet-friendly record whose own quote states an ordinary-pet refusal
  QUESTION-ONLY PET-FRIENDLY = 0           no pet-friendly record whose only acceptance words sit in a question
  SERVICE-ANIMAL-ONLY PET-FRIENDLY = 0     no pet-friendly record whose only acceptance is a service-animal sentence
  PREOPENING / CLOSED PUBLISHED = 0        no record names a hotel that states it has not opened
  TIMESHARE / VACATION-OWNERSHIP = 0       no record is a vacation-club, villa or residence-club product
  MILITARY-RESTRICTED PUBLISHED = 0        no record sits at an installation's own postal code or name
  MISLEADING SINGLE FEES = 0               every published fee is one amount with a basis its own quote states
  WRONG-CITY FORT MYERS IDENTITIES = 0     every record's city is its premises' real municipality for its own code
  NAPLES ADMITTED = 0                      no record sits in Collier County or publishes the city Naples
  NONOPERATING PUBLISHED = 0               no record carries a closure / not-operating signal (own page or Places)

A failure here is a stop: the package is not sealed until it reads 0 on every line.

Output: launch_packages/pettripfinder/markets/reports/fort_myers_fl_publication_safety_audit_001.json
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

from scripts.pettripfinder import fort_myers_fl_clean_authority_001 as CA  # noqa: E402
from scripts.pettripfinder import fort_myers_fl_geography_001 as GEO  # noqa: E402
from scripts.pettripfinder import fort_myers_fl_nonhotel_rulings_001 as NH  # noqa: E402
from scripts.pettripfinder import fort_myers_fl_registration_staging_001 as ST  # noqa: E402

WORK_ORDER = "PTF-FORT-MYERS-FL-HARDENED-SOURCE-READY-001"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
STAGING = os.path.join(PKG, "markets", "staging", "fort-myers-fl")
POLICY = os.path.join(STAGING, "launch_package", "hotel_policy_facts_fort-myers-fl.json")
AUTHORITY = os.path.join(STAGING, "fort_myers_fl_proposed_authority_001.json")
OUT = os.path.join(PKG, "markets", "reports", "fort_myers_fl_publication_safety_audit_001.json")
BROWSER_LANE = os.path.join(PKG, "markets", "reports", "fort_myers_fl_browser_lane_001.json")
PLACES = os.path.join(PKG, "markets", "reports", "fort_myers_fl_places_route_discovery_001.json")


def _load(p):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def _load_opt(p):
    return _load(p) if os.path.exists(p) else {}


def main():
    policy = _load(POLICY)
    authority = _load(AUTHORITY)
    findings = OrderedDict((k, []) for k in (
        "pet_friendly_with_explicit_refusal", "question_only_pet_friendly", "service_animal_only_pet_friendly", "preopening_or_closed_published", "timeshare_or_vacation_ownership_published",
        "military_restricted_published", "misleading_single_fee_published", "no_pets_quote_without_refusal",
        "wrong_city_label_published", "outside_partition_published", "naples_or_collier_admitted",
        "boundary_island_published", "nonoperating_signal_published", "vacation_rental_or_condo_published",
        "shared_reader_disagrees"))
    for rec in authority["pet_friendly"]:
        q = rec.get("evidence_quote") or ""
        name = rec["canonical_name"]
        if CA._REFUSAL.search(q):
            findings["pet_friendly_with_explicit_refusal"].append((name, q[:200]))
        if not CA._accepts(q):
            findings["question_only_pet_friendly"].append((name, q[:200]))
        stripped = CA._SERVICE_ANIMAL_PHRASE.sub(" ", q)
        if not CA._ACCEPT.search(CA._QUESTION_CLAUSE.sub(" ", stripped)):
            findings["service_animal_only_pet_friendly"].append((name, q[:200]))
    for rec in authority["verified_no_pets"]:
        q = rec.get("evidence_quote") or ""
        if not CA._REFUSAL.search(q):
            findings["no_pets_quote_without_refusal"].append((rec["canonical_name"], q[:200]))
    for rec in authority["pet_friendly"] + authority["verified_no_pets"]:
        name, url = rec["canonical_name"], rec.get("official_url") or rec.get("source_url") or ""
        if CA._PREOPENING.search(name) or re.search(r"\b(?:temporarily|permanently)\s+closed\b", name, re.I):
            findings["preopening_or_closed_published"].append(name)
        if NH._TIMESHARE.search(name) or NH.timeshare_by_route(url):
            findings["timeshare_or_vacation_ownership_published"].append(name)
        if GEO.military_postal(rec.get("postal_code")) or GEO.nonpublic_reason(name):
            findings["military_restricted_published"].append(name)
    # FORT MYERS: the published city is the premises' REAL municipality for its own code (a "Fort Myers" label on a
    # Cape Coral, Fort Myers Beach, Sanibel, Estero or Bonita Springs premises is a WRONG-CITY identity); no record sits
    # outside the admitted partition or in Collier County (Naples is a future submarket); no record names a refused
    # boat-access island, Pine Island or Gasparilla premises; and no record carries a closure / not-operating signal
    # -- its own page's closure or pre-opening statement, a brand route that redirects away, or Google Places'
    # CLOSED_PERMANENTLY / CLOSED_TEMPORARILY business status. Each is checked on every staged record.
    _closed = {}
    for _br in (_load_opt(BROWSER_LANE).get("rows") or []):
        if _br.get("identity_key") and (_br.get("closure_statement") or _br.get("preopening_statement")):
            _closed[_br["identity_key"]] = "own page: %s" % (_br.get("closure_statement") or _br.get("preopening_statement"))
    for _pr in (_load_opt(PLACES).get("rows") or []):
        _st = ((_pr.get("place") or {}).get("business_status") or "")
        if _pr.get("bound") and _st.startswith("CLOSED") and _pr.get("identity_key"):
            _closed.setdefault(_pr["identity_key"], "Google Places business_status %s" % _st)
    for rec in authority["pet_friendly"] + authority["verified_no_pets"]:
        name, postal = rec["canonical_name"], (rec.get("postal_code") or "")[:5]
        city = GEO.normalise_municipality(rec.get("city") or "")
        entry = GEO.POSTAL_PARISH.get(postal)
        if not entry:
            findings["outside_partition_published"].append((name, postal))
        elif city not in entry[1]:
            findings["wrong_city_label_published"].append((name, rec.get("city"), postal, list(entry[1])))
        if city == "naples" or (postal.startswith("341") and postal not in GEO.POSTAL_PARISH):
            findings["naples_or_collier_admitted"].append((name, rec.get("city"), postal))
        if GEO.boundary_name_reason(name, rec.get("address") or ""):
            findings["boundary_island_published"].append(name)
        if rec["identity_key"] in _closed:
            findings["nonoperating_signal_published"].append((name, _closed[rec["identity_key"]]))
        _nh = NH.nonhotel_by_name(name, ["PROPERTY_PAGE_ATTENDED"], rec.get("address") or "")
        if _nh and NH.exclusion_class(_nh) in ("VACATION_RENTAL", "TIMESHARE", "RESORT_RESIDENCE"):
            findings["vacation_rental_or_condo_published"].append((name, _nh[:120]))
    # THE SHARED READER, IN ADVANCE. FAST rule C re-runs first_party_binding over the sealed package; running the same
    # reader here on every staged record's own quote means a disagreement stops the order BEFORE the seal.
    from scripts.pettripfinder import first_party_binding as FPB  # noqa: E402
    # A pet-friendly record is read on the text the SEALED package carries for its pets_allowed field (the quote plus
    # its captured context, from one artifact) -- exactly what FAST rule C reads.
    _pkg_quote = {h["identity_key"]: next((e["quote"] for e in h["evidence"] if e["field"] == "pets_allowed"), "")
                  for h in policy["hotels"]}
    for rec in authority["pet_friendly"]:
        cls, why = FPB.classify_quote(_pkg_quote.get(rec["identity_key"]) or rec.get("evidence_quote") or "",
                                      kind=FPB.KIND_PET_FRIENDLY)
        if cls != FPB.ELIGIBLE:
            findings["shared_reader_disagrees"].append((rec["canonical_name"], "pet_friendly", cls))
    for rec in authority["verified_no_pets"]:
        cls, why = FPB.classify_quote(rec.get("evidence_quote") or "", kind=FPB.KIND_NO_PETS)
        if cls != FPB.ELIGIBLE:
            findings["shared_reader_disagrees"].append((rec["canonical_name"], "no_pets", cls))
    for h in policy["hotels"]:
        fee = h["facts"].get("pet_fee")
        if not fee:
            continue
        q = " ".join(e["quote"] for e in h["evidence"] if e["field"] == "pet_fee")
        if len(ST._stated_amounts(q)) > 1 or ST._fee_withhold_reason(q):
            findings["misleading_single_fee_published"].append((h["name"], fee, q[:200]))
    doc = OrderedDict([
        ("schema", "ptf-publication-safety-audit/1.0"), ("work_order", WORK_ORDER), ("market_id", "fort-myers-fl"),
        ("pet_friendly_records", len(authority["pet_friendly"])),
        ("verified_no_pets_records", len(authority["verified_no_pets"])),
        ("shared_reader_gate", "applied at seal time over the sealed package (shadow report first_party_gate)"),
        ("counts", OrderedDict((k, len(v)) for k, v in findings.items())),
        ("findings", findings),
        ("all_zero", all(not v for v in findings.values())),
    ])
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print(json.dumps(doc["counts"]))
    for k, v in findings.items():
        for x in v[:6]:
            print("  !", k, x)
    print("ALL ZERO =", doc["all_zero"])
    return 0 if doc["all_zero"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
