"""PTF-DALLAS-FORT-WORTH-TX-HARDENED-SOURCE-READY-001 -- Phases 4, 19, 20, 21, 22 and 29: the pre-seal publication-safety audit.

Reads the STAGED policy package and proposed authority (never fetches) and checks every published record against
the order's hard publication rules, with the SHARED first-party reader that FAST rule C re-runs at seal time:

  PET-FRIENDLY WITH EXPLICIT REFUSAL = 0   no pet-friendly record whose own quote states an ordinary-pet refusal
  QUESTION-ONLY PET-FRIENDLY = 0           no pet-friendly record whose only acceptance words sit in a question
  SERVICE-ANIMAL-ONLY PET-FRIENDLY = 0     no pet-friendly record whose only acceptance is a service-animal sentence
  PREOPENING / CLOSED PUBLISHED = 0        no record names a hotel that states it has not opened
  TIMESHARE / VACATION-OWNERSHIP = 0       no record is a vacation-club, villa or residence-club product
  MILITARY-RESTRICTED PUBLISHED = 0        no record sits at an installation's own postal code or name
  MISLEADING SINGLE FEES = 0               every published fee is one amount with a basis its own quote states
  SUBURBAN HOTELS MISLABELED DALLAS = 0    no record publishes "Dallas" on premises another municipality contains
  SUBURBAN HOTELS MISLABELED FORT WORTH = 0  ... nor "Fort Worth"
  WRONG-CITY IDENTITIES = 0                every record's city is the municipality its premises are in
  REFUSED COUNTY ADMITTED = 0              no record's premises or permit sit in a refused county
  NONOPERATING PUBLISHED = 0               no record carries a closure / not-operating signal (own page or Places)
  PRIVATE APARTMENT / RESIDENCE = 0        no record is a serviced-apartment, corporate-housing or residence product

A failure here is a stop: the package is not sealed until it reads 0 on every line.

Output: launch_packages/pettripfinder/markets/reports/dallas_fort_worth_tx_publication_safety_audit_001.json
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

from scripts.pettripfinder import dallas_fort_worth_tx_clean_authority_001 as CA  # noqa: E402
from scripts.pettripfinder import dallas_fort_worth_tx_geography_001 as GEO  # noqa: E402
from scripts.pettripfinder import dallas_fort_worth_tx_nonhotel_rulings_001 as NH  # noqa: E402
from scripts.pettripfinder import dallas_fort_worth_tx_registration_staging_001 as ST  # noqa: E402
from scripts.pettripfinder import dallas_fort_worth_tx_census_reconciliation_001 as CR  # noqa: E402
CENSUS = os.path.join(_DASH, "launch_packages", "pettripfinder", "identity_census_proposed", "dallas-fort-worth-tx.json")

WORK_ORDER = "PTF-DALLAS-FORT-WORTH-TX-HARDENED-SOURCE-READY-001"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
STAGING = os.path.join(PKG, "markets", "staging", "dallas-fort-worth-tx")
POLICY = os.path.join(STAGING, "launch_package", "hotel_policy_facts_dallas-fort-worth-tx.json")
AUTHORITY = os.path.join(STAGING, "dallas_fort_worth_tx_proposed_authority_001.json")
OUT = os.path.join(PKG, "markets", "reports", "dallas_fort_worth_tx_publication_safety_audit_001.json")
BROWSER_LANE = os.path.join(PKG, "markets", "reports", "dallas_fort_worth_tx_browser_lane_001.json")
PLACES = os.path.join(PKG, "markets", "reports", "dallas_fort_worth_tx_places_route_discovery_001.json")


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
        "wrong_city_label_published", "outside_partition_published", "suburban_mislabeled_dallas",
        "suburban_mislabeled_fort_worth", "refused_county_admitted",
        "boundary_name_published", "nonoperating_signal_published", "vacation_rental_or_condo_published",
        "private_apartment_or_residence_published", "shared_reader_disagrees"))
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
    # DALLAS-FORT WORTH: the published city is the municipality the premises are IN (the Census boundary over the
    # census row's own coordinates, or the single municipality of its postal code); "Dallas" or "Fort Worth" on a
    # suburban premises is a MISLABEL; no record sits outside the admitted partition or in a refused county; no record
    # names a refused outer place; and no record carries a closure / not-operating signal -- its own page's closure or
    # pre-opening statement, or Google Places' CLOSED_PERMANENTLY / CLOSED_TEMPORARILY business status.
    _closed = {}
    for _br in (_load_opt(BROWSER_LANE).get("rows") or []):
        if _br.get("identity_key") and (_br.get("closure_statement") or _br.get("preopening_statement")):
            _closed[_br["identity_key"]] = "own page: %s" % (_br.get("closure_statement") or _br.get("preopening_statement"))
    for _pr in (_load_opt(PLACES).get("rows") or []):
        _st = ((_pr.get("place") or {}).get("business_status") or "")
        if _pr.get("bound") and _st.startswith("CLOSED") and _pr.get("identity_key"):
            _closed.setdefault(_pr["identity_key"], "Google Places business_status %s" % _st)
    _census = {h["identity_key"]: h for h in _load(CENSUS).get("hotels", [])}
    _published = [_census[r["identity_key"]] for r in authority["pet_friendly"] + authority["verified_no_pets"]
                  if r["identity_key"] in _census]
    for k in CR.wrong_city_identities(_published):
        findings["wrong_city_label_published"].append(k)
    for k in CR.suburban_mislabeled(_published, "dallas"):
        findings["suburban_mislabeled_dallas"].append(k)
    for k in CR.suburban_mislabeled(_published, "fort worth"):
        findings["suburban_mislabeled_fort_worth"].append(k)
    for k in CR.collier_licensed_rows(_published):
        findings["refused_county_admitted"].append(k)
    for rec in authority["pet_friendly"] + authority["verified_no_pets"]:
        name, postal = rec["canonical_name"], (rec.get("postal_code") or "")[:5]
        if rec["identity_key"] not in _census:
            findings["outside_partition_published"].append((name, postal, "not an admitted census row"))
        entry = GEO.POSTAL_PARISH.get(postal)
        if not entry:
            findings["outside_partition_published"].append((name, postal))
        if GEO.boundary_name_reason(name, rec.get("address") or ""):
            findings["boundary_name_published"].append(name)
        if re.search(r"\b(apartments?|corporate housing|furnished|residences|sonder|kasa|mint house|placemakr|"
                     r"blueground|lark|zeus|stayapt|aparthotel)\b", name, re.I):
            findings["private_apartment_or_residence_published"].append(name)
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
        ("schema", "ptf-publication-safety-audit/1.0"), ("work_order", WORK_ORDER), ("market_id", "dallas-fort-worth-tx"),
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
