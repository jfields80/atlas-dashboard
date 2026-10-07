"""PTF-SALT-LAKE-CITY-UT-HARDENED-SOURCE-READY-001 -- Phases 13, 14 and 20: the pre-seal publication-safety audit.

Reads the STAGED policy package and proposed authority (never fetches) and checks every published record against
the order's hard publication rules, with the SHARED first-party reader that FAST rule C re-runs at seal time:

  PET-FRIENDLY WITH EXPLICIT REFUSAL = 0   no pet-friendly record whose own quote states an ordinary-pet refusal
  QUESTION-ONLY PET-FRIENDLY = 0           no pet-friendly record whose only acceptance words sit in a question
  SERVICE-ANIMAL-ONLY PET-FRIENDLY = 0     no pet-friendly record whose only acceptance is a service-animal sentence
  PREOPENING / CLOSED PUBLISHED = 0        no record names a hotel that states it has not opened
  TIMESHARE / VACATION-OWNERSHIP = 0       no record is a vacation-club, villa or residence-club product
  MILITARY-RESTRICTED PUBLISHED = 0        no record sits at an installation's own postal code or name
  MISLEADING SINGLE FEES = 0               every published fee is one amount with a basis its own quote states

A failure here is a stop: the package is not sealed until it reads 0 on every line.

Output: launch_packages/pettripfinder/markets/reports/salt_lake_city_ut_publication_safety_audit_001.json
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

from scripts.pettripfinder import salt_lake_city_ut_clean_authority_001 as CA  # noqa: E402
from scripts.pettripfinder import salt_lake_city_ut_geography_001 as GEO  # noqa: E402
from scripts.pettripfinder import salt_lake_city_ut_nonhotel_rulings_001 as NH  # noqa: E402
from scripts.pettripfinder import salt_lake_city_ut_registration_staging_001 as ST  # noqa: E402

WORK_ORDER = "PTF-SALT-LAKE-CITY-UT-HARDENED-SOURCE-READY-001"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
STAGING = os.path.join(PKG, "markets", "staging", "salt-lake-city-ut")
POLICY = os.path.join(STAGING, "launch_package", "hotel_policy_facts_salt-lake-city-ut.json")
AUTHORITY = os.path.join(STAGING, "salt_lake_city_ut_proposed_authority_001.json")
OUT = os.path.join(PKG, "markets", "reports", "salt_lake_city_ut_publication_safety_audit_001.json")


def _load(p):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def main():
    policy = _load(POLICY)
    authority = _load(AUTHORITY)
    findings = OrderedDict((k, []) for k in (
        "pet_friendly_with_explicit_refusal", "question_only_pet_friendly", "service_animal_only_pet_friendly", "preopening_or_closed_published", "timeshare_or_vacation_ownership_published",
        "military_restricted_published", "misleading_single_fee_published", "no_pets_quote_without_refusal",
        "park_city_labeled_salt_lake_city", "canyon_resort_published", "vacation_rental_or_condo_published",
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
    # SALT LAKE CITY: Park City is its own identity, never labelled Salt Lake City; a Big/Little Cottonwood Canyon
    # resort premises is a FUTURE submarket; a Park City condominium lodge or a residence-only product is never a
    # hotel record. Each is checked on every staged record, published or verified-no-pets.
    for rec in authority["pet_friendly"] + authority["verified_no_pets"]:
        name, postal = rec["canonical_name"], (rec.get("postal_code") or "")[:5]
        city = (rec.get("city") or "").strip().lower()
        if postal in ("84060", "84068", "84098") and (city != "park city" or "salt lake city" in name.lower()
                                                     and "park city" not in name.lower()):
            findings["park_city_labeled_salt_lake_city"].append((name, city, postal))
        if GEO.canyon_resort_reason(name, rec.get("address") or ""):
            findings["canyon_resort_published"].append(name)
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
        ("schema", "ptf-publication-safety-audit/1.0"), ("work_order", WORK_ORDER), ("market_id", "salt-lake-city-ut"),
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
