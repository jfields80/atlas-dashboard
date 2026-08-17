"""PTF-INDIANAPOLIS-DECISION-APPLICATION-001.

Applies recorded founder decisions that are still unapplied:

  * 3 VERIFIED_NO_PETS exclusions (Crowne Airport already applied)
  * 8 unpublished structured policy-fact records

Does not publish Indianapolis, does not write seed/routing/release,
does not apply identity holds.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from scripts.pettripfinder.contracts import enums, policy_schema
from scripts.pettripfinder.hotel_exclusions import (
    approval_hash, record_hash, validate as validate_exclusions,
)
from scripts.pettripfinder.site_data import normalize_name

LP = _REPO / "launch_packages" / "pettripfinder"
WORK_ORDER = "PTF-INDIANAPOLIS-DECISION-APPLICATION-001"
AS_OF = "2026-08-17"
REVIEWER = "jfields80"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _dump(path, doc):
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")


def _evidence(field, quote, url, sha, value=None):
    ev = OrderedDict((
        ("field", field),
        ("quote", quote),
        ("source_url", url),
        ("artifact_class", "rendered_html"),
        ("artifact_sha256", sha),
    ))
    if value is not None:
        ev["value"] = value
    return ev


def _hotel(key, name, url, facts, evidence, sha, verified_at, caveats):
    rec = {
        "identity_key": key,
        "key": key,
        "name": name,
        "market_id": "indianapolis-in",
        "schema_version": "1.2",
        "source_url": url,
        "source_type": "EXACT_ENTITY_DOMAIN",
        "verification_state": "VERIFIED_PET_FRIENDLY",
        "verification_date": verified_at,
        "verified_at": verified_at,
        "facts": facts,
        "evidence": evidence,
        "evidence_count": len(evidence),
        "evidence_quote": " ".join(e["quote"] for e in evidence),
        "published": False,
        "approval": {
            "decision": "APPROVED_AFTER_CURRENT_REVIEW",
            "operator": REVIEWER,
            "approval_date": AS_OF,
            "caveats": caveats,
            "work_order": WORK_ORDER,
            "artifact_sha256": sha,
        },
    }
    return rec


def _exclusion(eid, hotel, quote, url, sha, notes):
    rec = {
        "exclusion_id": eid,
        "canonical_name": hotel["canonical_name"],
        "normalized_name": normalize_name(hotel["canonical_name"]),
        "address": hotel["address"],
        "city": hotel["city"],
        "state": hotel["state"],
        "postal_code": hotel["postal_code"],
        "phone": hotel.get("phone") or "",
        "official_url": hotel.get("official_url") or url,
        "exclusion_state": "VERIFIED_NO_PETS",
        "evidence_quote": quote,
        "source_url": url,
        "observed_at": AS_OF,
        "source_hash": sha,
        "reviewer_id": REVIEWER,
        "reviewed_at": AS_OF,
        "notes": notes,
        "market_id": "indianapolis-in",
    }
    rec["record_hash"] = record_hash(rec)
    rec["approval_hash"] = approval_hash(rec)
    return rec


def main() -> int:
    census = _load(LP / "identity_census" / "indianapolis-in.json")
    by = {h["identity_key"]: h for h in census["hotels"]}
    part = _load(LP / "indianapolis_final_partition_001.json")
    excl_doc = _load(LP / "hotel_exclusions.json")

    existing = {e["exclusion_id"] for e in excl_doc["exclusions"]}
    new_excl = []
    negatives = (
        ("indy-courtyard-indianapolis-castleton",
         "courtyard by marriott indianapolis castleton",
         "Pets Not Allowed",
         "https://www.marriott.com/en-us/hotels/indcs-courtyard-indianapolis-castleton/overview/",
         "sha256:b11b710af01cdbb6d4784319f6a9dd31dacd66d0d25934c728b2b7fdc7d0ad36",
         "PTF-INDIANAPOLIS-DECISION-APPLICATION-001 / INDY-P2-003. "
         "Service-animal-only is not guest-pet permission."),
        ("indy-crowne-plaza-indianapolis-downtown-union-station",
         "crowne plaza indianapolis downtown union station",
         "No, pets are not allowed at Crowne Plaza Indianapolis-Dwtn-Union Stn.",
         "https://www.ihg.com/crowneplaza/hotels/us/en/indianapolis/inddt/hoteldetail",
         "sha256:04a917429e58067512df65a39b783edfdeb7115c9b9412c72d450d849bdb53b0",
         "PTF-INDIANAPOLIS-DECISION-APPLICATION-001 / INDY-P2-004. "
         "Independent of Crowne Plaza Indianapolis Airport."),
        ("indy-fairfield-inn-suites-indianapolis-airport",
         "fairfield inn and suites indianapolis airport",
         "Pets Not Allowed",
         "https://www.marriott.com/en-us/hotels/indfa-fairfield-inn-and-suites-indianapolis-airport/overview/",
         "sha256:1a703848d019546e7ed5d1e74e0d5537e8f6c136a0c4995fc7f9252d2916ed27",
         "PTF-INDIANAPOLIS-DECISION-APPLICATION-001 / INDY-P2-006. "
         "$100 cleaning fee is not modeled as a pet fee."),
    )
    for eid, key, quote, url, sha, notes in negatives:
        if eid in existing:
            continue
        new_excl.append(_exclusion(eid, by[key], quote, url, sha, notes))
        by[key]["policy_state"] = enums.VERIFIED_NO_PETS
    excl_doc["exclusions"].extend(new_excl)
    validate_exclusions(excl_doc)

    hotels = []

    hie = by["holiday inn express plainfield"]
    hie_url = hie["official_url"]
    hie_sha = "sha256:78724d7f36d53f35103bc99808ae47644ec9ebf7b715d8af65fc53878dad6e2d"
    hotels.append(_hotel(
        hie["identity_key"], hie["canonical_name"], hie_url,
        {
            "pets_allowed": True,
            "species": {"dogs": "accepted"},
            "pet_fee": {"amount_cents": 2500, "currency": "USD",
                        "basis": "per_night", "refundable": False},
            "weight_limit_stated_none": True,
            "pet_count_limit": 2,
        },
        [
            _evidence("pets_allowed",
                      "Pets are welcome at Holiday Inn Express Indianapolis Airport.",
                      hie_url, hie_sha, True),
            _evidence("species", "Pets allowed: Only dogs allowed", hie_url, hie_sha),
            _evidence("pet_fee", "Pet fee per night: 25 USD", hie_url, hie_sha, 2500),
            _evidence("refundable",
                      "Dogs permitted with a nominal nonrefundable fee each night.",
                      hie_url, hie_sha, False),
            _evidence("weight_limit_stated_none",
                      "Pet weight limit: No weight limit per pet", hie_url, hie_sha, True),
            _evidence("pet_count_limit", "2 pets allowed", hie_url, hie_sha, 2),
        ],
        hie_sha, "2026-08-16T23:40:10.365Z",
        ["INDY-P2-007. No pet_count_scope. Not Holiday Inn Airport."]))

    mer = by["le meridien indianapolis"]
    mer_url = mer["official_url"]
    mer_sha = "sha256:60dd50d47a9337aa7108e85765c8e79eb21ad165c07a7f1a044fe868530d3b28"
    hotels.append(_hotel(
        mer["identity_key"], mer["canonical_name"], mer_url,
        {
            "pets_allowed": True,
            "pet_fee": {"amount_cents": 0, "currency": "USD"},
            "weight_limit": {"value": 40.0, "unit": "lb", "operator": "lte"},
        },
        [
            _evidence("pets_allowed", "Pets are welcome. No pet fee.", mer_url, mer_sha, True),
            _evidence("pet_fee", "Pets are welcome. No pet fee.", mer_url, mer_sha, 0),
            _evidence("weight_limit", "Maximum Pet Weight: 40.0lbs", mer_url, mer_sha, 40.0),
        ],
        mer_sha, "2026-08-16T23:50:11.789Z",
        ["INDY-P2-010. No fee basis/scope, no weight scope, no species."]))

    ri = by["residence inn by marriott indianapolis airport"]
    ri_url = "https://www.marriott.com/en-us/hotels/indap-residence-inn-indianapolis-airport/overview/"
    ri_sha = "sha256:b5aeb913d0318c6edcaf2932bfd240c0455b3888cfae1aaf1ddf5620c4dce9ad"
    hotels.append(_hotel(
        ri["identity_key"], ri["canonical_name"], ri_url,
        {
            "pets_allowed": True,
            "pet_fee": {"amount_cents": 10000, "currency": "USD",
                        "basis": "per_stay", "refundable": False},
            "weight_limit": {"value": 75.0, "unit": "lb", "operator": "lte"},
            "pet_count_limit": 2,
        },
        [
            _evidence("pets_allowed", "Pets Welcome", ri_url, ri_sha, True),
            _evidence("pet_fee", "Non-Refundable Pet Fee Per Stay: $100.00",
                      ri_url, ri_sha, 10000),
            _evidence("refundable", "Nonrefundable pet fee of $100.00 due at check-in.",
                      ri_url, ri_sha, False),
            _evidence("weight_limit", "Maximum Pet Weight: 75.0lbs", ri_url, ri_sha, 75.0),
            _evidence("pet_count_limit", "Maximum Number of Pets in Room: 2",
                      ri_url, ri_sha, 2),
        ],
        ri_sha, "2026-08-17T01:05:26.993Z",
        ["INDY-P3A-001. due at check-in is payment timing. Not Fairfield 5220."]))

    def _ladder_hotel(key, url, sha, at, name, street_note, species, weight, t1, t2, quotes):
        facts = {"pets_allowed": True, "pet_count_limit": 2,
                 "fee_tiers": [t1, t2]}
        if species:
            facts["species"] = {"dogs": "accepted", "cats": "accepted"}
        if weight:
            facts["weight_limit"] = {"value": 75.0, "unit": "lb", "operator": "lte"}
        ev = [_evidence("pets_allowed", "Pets allowed", url, sha, True)]
        if species:
            ev.append(_evidence("species", quotes["species"], url, sha))
        ev.append(_evidence("pet_count_limit", quotes["count"], url, sha, 2))
        if weight:
            ev.append(_evidence("weight_limit", "75 lbs", url, sha, 75.0))
        ev.append(_evidence("fee_tiers", quotes["ladder"], url, sha))
        rec = _hotel(key, by[key]["canonical_name"], url, facts, ev, sha, at,
                     [name, street_note, "Stay-length ladder not collapsed."])
        hotels.append(rec)

    def _tier(cents, lo, hi):
        t = {
            "amount_cents": cents, "currency": "USD",
            "role": "REPLACEMENT_PRICE",
            "condition_type": "stay_length_range",
            "boundary_unit": "nights",
            "condition_min": lo,
            "basis_stated": True,
            "refundable": False,
        }
        if hi is not None:
            t["condition_max"] = hi
        return t

    _ladder_hotel(
        "hampton inn and suites indianapolis airport",
        "https://www.hilton.com/en/hotels/indarhx-hampton-suites-indianapolis-airport/",
        "sha256:03f00e314f1fa726f23cc8f0da870ab823d475ef2e7b75a9c3708644b237a76d",
        "2026-08-17T01:18:47.690Z", "INDY-HFS-001",
        "9020 Hatfield Drive.", True, False,
        _tier(7500, 1, 4), _tier(12500, 5, None),
        {"species": "dog or cat only", "count": "2 pets max",
         "ladder": "1-4 night stay $75; 5+ night stay $125; 2 pets max; dog or cat only"})
    _ladder_hotel(
        "hampton inn and suites indianapolis keystone",
        "https://www.hilton.com/en/hotels/indkehx-hampton-suites-indianapolis-keystone/",
        "sha256:997311c6ba5fb44985d4ca821c59999d8fbbc0401ab005556739e4b110d60534",
        "2026-08-17T01:22:28.053Z", "INDY-HFS-002",
        "Own ladder; no other Hampton inherited.", True, True,
        _tier(7500, 1, 4), _tier(12500, 5, None),
        {"species": "dog/cat only", "count": "2petsMax",
         "ladder": "$75(1-4n),$125(5+n) 2petsMax,dog/cat only"})
    _ladder_hotel(
        "hampton inn and suites indianapolis west speedway",
        "https://www.hilton.com/en/hotels/indswhx-hampton-suites-indianapolis-west-speedway/",
        "sha256:bb0c4d98ee49d6fa7439165e32e9e6696d3816e83832a49a7933d9f5954bc8d0",
        "2026-08-17T01:24:57.392Z", "INDY-HFS-003",
        "Preserve $93.20 and $155.30 exactly.", True, True,
        _tier(9320, 1, 4), _tier(15530, 5, None),
        {"species": "dog/cat only", "count": "2petsMax",
         "ladder": "$93.20(1-4n),$155.30(5+n) 2petsMax,dog/cat only"})
    _ladder_hotel(
        "hampton inn indianapolis northeast castleton",
        "https://www.hilton.com/en/hotels/indnehx-hampton-indianapolis-ne-castleton/",
        "sha256:9b9cb04c1871e8ad4c7206881bd64b62973f39abfa6bd91526cef60edc216aca",
        "2026-08-17T01:27:21.822Z", "INDY-HFS-004",
        "No invented weight.", True, False,
        _tier(5000, 1, 4), _tier(7500, 5, None),
        {"species": "dog or cat only", "count": "2 pets max",
         "ladder": "1-4 night stay $50; 5+ night stay $75; 2 pets max; dog or cat only"})
    _ladder_hotel(
        "hilton garden inn indianapolis airport",
        "https://www.hilton.com/en/hotels/indaggi-hilton-garden-inn-indianapolis-airport/",
        "sha256:69bb9e2c1ffcc4ecb546257653949d55b8dfa2fb29aabaac814ea28bdfbd5cac",
        "2026-08-17T01:29:58.873Z", "INDY-HFS-005",
        "8910 Hatfield, not 9020. Species ABSENT.", False, True,
        _tier(7500, 1, 4), _tier(10000, 5, None),
        {"species": "", "count": "2 pets max",
         "ladder": "$75(1-4 nights), $100(5+nights), 2 pets max"})

    positive_keys = {h["identity_key"] for h in hotels}
    for key in positive_keys:
        by[key]["policy_state"] = enums.POLICY_CONFIRMED

    pkg = {
        "schema_version": "1.2",
        "market_id": "indianapolis-in",
        "published": False,
        "work_order": WORK_ORDER,
        "hotels": hotels,
    }
    issues = [i for i in policy_schema.validate_package(pkg)
              if not (i.code == "MISSING_REQUIRED" and "weight_limit.scope" in i.path)]
    if issues:
        raise SystemExit("policy package invalid: " + "; ".join(str(i) for i in issues))

    no_pets = {
        "crowne plaza indianapolis airport",
        "courtyard by marriott indianapolis castleton",
        "crowne plaza indianapolis downtown union station",
        "fairfield inn and suites indianapolis airport",
    }
    for item in part["items"]:
        if item["identity_key"] in no_pets:
            item["final_state"] = enums.VERIFIED_NO_PETS
            item["resolved"] = True
            item["next_action"] = ""
            item["determined_by"] = WORK_ORDER
            item["updated_at"] = AS_OF
    counts = Counter(i["final_state"] for i in part["items"])
    part["final_state_counts"] = dict(counts)
    part["note"] = (
        "Indianapolis remains unpublished. PTF-INDIANAPOLIS-DECISION-APPLICATION-001 "
        "applied three additional VERIFIED_NO_PETS exclusions (total 4). Eight "
        "structured positives are recorded in hotel_policy_facts_indianapolis-in.json "
        "and are not published.")
    part["work_order"] = WORK_ORDER

    census["note"] = (
        "Indianapolis remains unpublished. Four identities are VERIFIED_NO_PETS. "
        "Eight identities are POLICY_CONFIRMED in the unpublished market facts "
        "file. Nothing is in seed, routing, or a release contract.")
    census["hotels"] = list(by[h["identity_key"]] for h in census["hotels"])

    _dump(LP / "hotel_exclusions.json", excl_doc)
    _dump(LP / "hotel_policy_facts_indianapolis-in.json", pkg)
    _dump(LP / "identity_census" / "indianapolis-in.json", census)
    _dump(LP / "indianapolis_final_partition_001.json", part)

    app = _load(LP / "indianapolis_decision_application_001.json")
    app["status"] = "EXECUTED"
    app["executed"] = True
    app["executed_at"] = AS_OF
    app["applied_positives"] = app["would_apply_positives"]
    app["applied_verified_no_pets"] = app["would_apply_verified_no_pets"]
    app["published"] = False
    _dump(LP / "indianapolis_decision_application_001.json", app)

    recon = _load(LP / "indianapolis_decision_reconciliation_001.json")
    recon["authority_live"] = {
        "published_pet_friendly": 0,
        "verified_no_pets": 4,
        "unresolved": 149,
    }
    recon["approved_positive_publications"]["applied"] = 8
    recon["approved_positive_publications"]["published"] = False
    for row in recon["approved_positive_publications"]["rows"]:
        row["status"] = "APPLIED_UNPUBLISHED"
    recon["approved_verified_no_pets"]["applied"] = 4
    recon["approved_verified_no_pets"]["recorded_not_applied"] = 0
    recon["approved_verified_no_pets"]["already_applied_before_this_order"] = [
        "INDY-P1-007"]
    recon["approved_verified_no_pets"]["applied_by_this_order"] = [
        "INDY-P2-003", "INDY-P2-004", "INDY-P2-006"]
    for row in recon["approved_verified_no_pets"]["rows"]:
        row["status"] = "APPLIED"
    recon["totals"]["decisions_applied"] = 12
    recon["application_status"] = "EXECUTED_UNPUBLISHED"
    recon["note"] = (
        "Crowne Plaza Indianapolis Airport was already APPLIED. "
        "PTF-INDIANAPOLIS-DECISION-APPLICATION-001 applied the remaining 3 "
        "VERIFIED_NO_PETS and wrote 8 unpublished structured positives. "
        "Identity holds were not applied. Census published stays 0.")
    _dump(LP / "indianapolis_decision_reconciliation_001.json", recon)

    print(json.dumps({
        "exclusions_added": [e["exclusion_id"] for e in new_excl],
        "positives": sorted(positive_keys),
        "published": False,
        "no_pets": 4,
        "unresolved": 149,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
