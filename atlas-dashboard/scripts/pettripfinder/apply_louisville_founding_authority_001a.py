"""Apply the recorded Louisville 001A founder decisions atomically."""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from scripts.pettripfinder.contracts import census, enums, partition, policy_schema
from scripts.pettripfinder.contracts import evidence as evidence_contract
from scripts.pettripfinder.hotel_exclusions import approval_hash, record_hash as exclusion_hash
from scripts.pettripfinder.market_authority import (
    build_exclusions_shard, build_routing_shard, render_json, render_seed_csv,
)
from scripts.pettripfinder.policy_migration import evidence_hash, evidence_ref_for, record_hash
from scripts.pettripfinder.site_data import normalize_name

REPO = Path(__file__).resolve().parents[2]
PKG = REPO / "launch_packages" / "pettripfinder"
REPORTS = PKG / "markets" / "reports"
SHARD = PKG / "markets" / "authority" / "louisville-ky"
MARKET = "louisville-ky"
WORK = "PTF-LOUISVILLE-FOUNDING-AUTHORITY-APPLICATION-001A"
AS_OF = "2026-08-17"
OPERATOR = "jfields80"


def load(path): return json.loads(path.read_text(encoding="utf-8-sig"))
def dump(path, document): path.write_text(json.dumps(document, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def species(*accepted, prohibited=()):
    out = {x: "accepted" for x in accepted}
    out.update({x: "prohibited" for x in prohibited})
    return out


def ev(field, quote, url, sha, captured_at, value=None):
    item = {"field": field, "quote": quote, "source_url": url,
            "source_grade": "PT1_FIRST_PARTY",
            "artifact_class": "PUBLICATION_GRADE_EVIDENCE",
            "artifact_sha256": "sha256:" + sha.removeprefix("sha256:"),
            "artifact_kind": "rendered_html", "captured_at": captured_at,
            "capture_method": "attended_official_property_surface"}
    if value is not None: item["value"] = value
    item["evidence_ref"] = evidence_ref_for(item)
    return item


def main():
    app = load(REPORTS / "louisville_founding_authority_application_001a_prepared.json")
    if app["executed"] or app["authority_applied"] or len(app["approved_row_contracts"]) != 18:
        raise SystemExit("001A preflight is not an unapplied 18-row application")
    census_doc = load(PKG / "identity_census" / "louisville-ky.json")
    part = load(PKG / "louisville_final_partition_001.json")
    pre = partition.reconcile(census.identity_keys(census_doc), part, market_id=MARKET)
    if (pre.published, pre.verified_no_pets, pre.unresolved) != (0, 0, 129):
        raise SystemExit("Louisville authority moved since 001A preparation")
    people = {h["identity_key"]: h for h in census_doc["hotels"]}
    p1 = {x["identity_key"]: x for x in load(REPORTS / "louisville_pass1_capture_results.json")["rows"]}
    p2 = {x["identity_key"]: x for x in load(REPORTS / "louisville_pass2_capture_results.json")["rows"]}
    d4 = {x["identity_key"]: x for x in load(REPORTS / "louisville_pass4_founder_decisions.json")["decisions"]}
    d1 = {x["identity_key"]: x for x in load(REPORTS / "louisville_pass1_founder_decisions.json")["decisions"]}
    d2 = {x["identity_key"]: x for x in load(REPORTS / "louisville_pass2_founder_decisions.json")["decisions"]}

    facts = {
      "bellwether hotel": {"pets_allowed": True, "species": species("dogs"), "pet_count_limit": 2,
        "combined_weight_limit": {"value": 50, "unit": "lb", "operator": "lte"},
        "pet_room_restriction": "Dogs are only allowed in first floor rooms.",
        "unattended_policy": "Pets must not be left unattended in room, or anywhere else on hotel property unless crated.",
        "reservation_requirement": "Please notify us at time of booking if a dog will be staying."},
      "galt house hotel": {"pets_allowed": True, "species": species("dogs"), "pet_count_limit": 2, "pet_count_scope": "per_room", "weight_limit": {"value": 45,"unit":"lb","operator":"lte","scope":"per_pet"}, "pet_fee": {"amount_cents":5000,"currency":"USD","basis":"per_stay","scope":"per_pet"}, "unattended_policy":"You must request to have your room cleaned and accompany your dog while the room is being cleaned."},
      "omni louisville hotel": {"pets_allowed":True,"species":species("dogs","cats"),"pet_count_limit":1,"pet_count_scope":"per_room","weight_limit":{"value":25,"unit":"lb","operator":"lte","scope":"per_pet"},"other_charges":[{"kind":"cleaning_fee","amount_cents":12500,"currency":"USD","basis":"per_stay","scope":"per_room","refundable":False}]},
      "drury inn and suites louisville north": {"pets_allowed":True,"species":species("dogs","cats"),"pet_count_limit":2,"pet_count_scope":"per_room","combined_weight_limit":{"value":80,"unit":"lb","operator":"lte"},"pet_fee":{"amount_cents":5000,"currency":"USD","basis":"per_day","scope":"per_room","tax_relationship":"plus_tax"}},
      "red roof inn louisville expo airport": {"pets_allowed":True,"species":species("dogs","cats"),"pet_count_limit":2,"pet_count_scope":"per_room","weight_limit":{"value":80,"unit":"lb","operator":"lte","scope":"per_pet"},"fee_pet_schedule":{"entries":[{"pet_ordinal":1,"amount_cents":0,"currency":"USD","additive":False},{"pet_ordinal":2,"amount_cents":1500,"currency":"USD","basis":"per_night","scope":"per_pet","additive":True,"cap":{"amount_cents":10500,"currency":"USD","basis":"per_stay","scope":"per_pet","qualifier_stated":True,"applies_to_pet_ordinal":2,"trigger_max_nights":7}}]}},
      "red roof inn louisville hurstbourne": {"pets_allowed":True,"species":species("dogs","cats"),"pet_count_limit":2,"pet_count_scope":"per_room","weight_limit":{"value":80,"unit":"lb","operator":"lte","scope":"per_pet"},"fee_pet_schedule":{"entries":[{"pet_ordinal":1,"amount_cents":0,"currency":"USD","additive":False},{"pet_ordinal":2,"amount_cents":1500,"currency":"USD","basis":"per_night","scope":"per_pet","additive":True,"cap":{"amount_cents":10500,"currency":"USD","basis":"per_stay","scope":"per_pet","qualifier_stated":True,"applies_to_pet_ordinal":2,"trigger_max_nights":7}}]}},
      "studio 6 louisville airport expo center": {"pets_allowed":True},
      "baymont by wyndham louisville airport south": {"pets_allowed":True,"species":species("dogs"),"pet_count_limit":2,"weight_limit":{"value":25,"unit":"lb","operator":"lte","scope":"per_pet"},"pet_fee":{"amount_cents":2000,"currency":"USD","basis":"per_night","scope":"per_pet","tax_relationship":"plus_tax","refundable":False},"other_charges":[{"kind":"refundable_deposit","amount_cents":10000,"currency":"USD","refundable":True}]},
      "hawthorn suites by wyndham louisville east": {"pets_allowed":True,"species":species("dogs","cats"),"pet_count_limit":2,"weight_limit":{"value":75,"unit":"lb","operator":"lte","scope":"per_pet"},"fee_tiers":[{"amount_cents":7500,"currency":"USD","role":"REPLACEMENT_PRICE","condition_type":"stay_length_range","boundary_unit":"nights","condition_min":1,"condition_max":4,"basis_stated":True},{"amount_cents":12500,"currency":"USD","role":"REPLACEMENT_PRICE","condition_type":"stay_length_range","boundary_unit":"nights","condition_min":5,"basis_stated":True}]},
      "travelodge by wyndham sellersburg louisville north": {"pets_allowed":True,"species":species("dogs","birds",prohibited=("cats",)),"pet_count_limit":1,"pet_fee":{"amount_cents":2000,"currency":"USD","basis":"per_night","refundable":False},"other_charges":[{"kind":"sanitation_fee","amount_cents":15000,"currency":"USD","conditional":True,"trigger":"if applicable"}]},
      "super 8 by wyndham louisville airport": {"pets_allowed":True,"pet_count_limit":2,"general_restrictions":"Maximum weight of 50 lbs per room.","pet_fee":{"amount_cents":2500,"currency":"USD","basis":"per_night","scope":"per_pet","refundable":False},"other_charges":[{"kind":"sanitation_fee","amount_cents":15000,"currency":"USD","conditional":True,"trigger":"if applicable"}]},
      "la quinta inn and suites by wyndham louisville northeast old henry": {"pets_allowed":True,"species":species("dogs","cats"),"pet_count_limit":2,"weight_limit":{"value":75,"unit":"lb","operator":"lte","scope":"per_pet"},"pet_fee":{"amount_cents":2500,"currency":"USD","basis":"per_night","scope":"per_room","scope_pet_allowance":2,"refundable":False},"fee_cap":{"amount_cents":7500,"currency":"USD","basis":"per_stay","qualifier_stated":True,"applies_to_pet_count":2}},
      "staybridge suites louisville east": {"pets_allowed":True,"fee_tiers":[{"amount_cents":7500,"currency":"USD","role":"REPLACEMENT_PRICE","condition_type":"stay_length_range","boundary_unit":"nights","condition_min":1,"condition_max":6,"basis_stated":True,"tax_relationship":"plus_tax"},{"amount_cents":15000,"currency":"USD","role":"REPLACEMENT_PRICE","condition_type":"stay_length_range","boundary_unit":"nights","condition_min":7,"basis_stated":True,"tax_relationship":"plus_tax"}]},
      "candlewood suites louisville airport": {"pets_allowed":True,"pet_count_limit":2,"general_restrictions":"Pet weight limit: 80 lb.","pet_fee":{"amount_cents":3000,"currency":"USD","basis":"per_night","scope":"per_pet","refundable":False},"fee_tiers":[{"amount_cents":15000,"currency":"USD","role":"REPLACEMENT_PRICE","condition_type":"stay_length_range","boundary_unit":"nights","condition_min":7,"basis_stated":True}]},
    }
    positives = app["application_set"]["positives"]
    negatives = app["application_set"]["verified_no_pets"]
    if set(facts) != set(positives): raise SystemExit("positive set drift")
    records=[]
    for key in positives:
        source = d4.get(key) or d1.get(key) or d2.get(key)
        if key in d4:
            quote = d4[key]["exact_quotes"][0] if d4[key]["exact_quotes"] else "Pets allowed"
            sha = d4[key]["artifacts"][0]["sha256"]
            url = d4[key]["official_url"]
        else:
            row=(p1.get(key) or p2.get(key)); quote=row["quotes"][0]; sha=row["artifact_sha256"]; url=row["final_url"]
        issue=policy_schema.validate_facts(facts[key])
        if issue: raise SystemExit("schema %s: %s"%(key,issue))
        evidence=[ev(field,quote,url,sha,AS_OF) for field in facts[key]]
        rec={"identity_key":key,"key":key,"name":people[key]["canonical_name"],"market_id":MARKET,"schema_version":"1.2","source_url":url,"source_type":"EXACT_ENTITY_DOMAIN","verification_state":"VERIFIED_PET_FRIENDLY","verification_date":AS_OF,"verified_at":AS_OF,"facts":facts[key],"evidence":evidence,"evidence_count":len(evidence),"evidence_quote":quote,"published":True}
        rec["approval"]={"decision":"APPROVED_AFTER_CURRENT_REVIEW","operator":OPERATOR,"approval_date":AS_OF,"record_hash":record_hash(rec),"evidence_hash":evidence_hash(evidence),"work_order":WORK,"founder_decision":source["decision"]}
        if evidence_contract.validate(rec): raise SystemExit("evidence invalid %s"%key)
        records.append(rec)
    pkg={"schema_version":"1.2","market_id":MARKET,"published":True,"work_order":WORK,"hotels":records}
    if policy_schema.validate_package(pkg): raise SystemExit("package invalid")
    exclusions=[]
    for key in negatives:
        dec=d4.get(key) or d1[key]
        if key in d4: quote=dec["exact_quotes"][0];sha=dec["artifacts"][0]["sha256"];url=dec["official_url"]
        else: quote=dec["evidence_quote"];sha=dec["artifact_sha256"];url=people[key]["official_url"]
        h=people[key]; x={"exclusion_id":"louisville-"+key.replace(" ","-"),"canonical_name":h["canonical_name"],"normalized_name":key,"address":h["address"],"city":h["city"],"state":h["state"],"postal_code":h["postal_code"],"phone":h.get("phone") or "","official_url":url,"exclusion_state":"VERIFIED_NO_PETS","evidence_quote":quote,"source_url":url,"observed_at":AS_OF,"source_hash":"sha256:"+sha.removeprefix("sha256:"),"reviewer_id":OPERATOR,"reviewed_at":AS_OF,"notes":WORK+" / "+dec["decision"],"market_id":MARKET};x["record_hash"]=exclusion_hash(x);x["approval_hash"]=approval_hash(x);exclusions.append(x)
    shard=build_exclusions_shard(MARKET,exclusions)
    from scripts.pettripfinder.hotel_exclusions import validate as validate_exclusions
    validate_exclusions(shard)
    for item in part["items"]:
        key=item["identity_key"]
        if key in positives: item.update(final_state="PUBLISHED_PET_FRIENDLY",resolved=True,next_action="",next_action_source="",determined_by=WORK,updated_at=AS_OF)
        elif key in negatives: item.update(final_state="VERIFIED_NO_PETS",resolved=True,next_action="",next_action_source="",determined_by=WORK,updated_at=AS_OF)
    part["final_state_counts"]=dict(Counter(x["final_state"] for x in part["items"]));part["work_order"]=WORK
    for key in positives: people[key]["policy_state"]="POLICY_CONFIRMED"
    for key in negatives: people[key]["policy_state"]="VERIFIED_NO_PETS"
    census_doc["hotels"]=[people[x["identity_key"]] for x in census_doc["hotels"]]
    final=partition.reconcile(census.identity_keys(census_doc),part,market_id=MARKET)
    if not final.agrees or (final.published,final.verified_no_pets,final.unresolved)!=(14,4,111): raise SystemExit("partition invalid")
    rows=[]
    for rec in records:
        h=people[rec["identity_key"]]; rows.append({"name":rec["name"],"category":"pet-friendly-hotels","address":h["address"],"city":h["city"],"state":h["state"],"postal_code":h["postal_code"],"phone":h.get("phone") or "","website_url":rec["source_url"],"source_url":rec["source_url"],"source_type":"OFFICIAL_PROPERTY","observed_at":AS_OF,"rating":"","amenities":"","pet_policy":rec["evidence_quote"],"canonical":"","market_id":MARKET})
    SHARD.mkdir(parents=True,exist_ok=True);dump(SHARD/"identity_routing.json",build_routing_shard(MARKET,[]));dump(SHARD/"hotel_exclusions.json",shard);(SHARD/"seed_businesses.csv").write_text(render_seed_csv(rows),encoding="utf-8",newline="")
    dump(PKG/"hotel_policy_facts_louisville-ky.json",pkg);dump(PKG/"louisville_final_partition_001.json",part);dump(PKG/"identity_census"/"louisville-ky.json",census_doc)
    app["executed"]=True;app["authority_applied"]=True;app["applied_positives"]=positives;app["applied_verified_no_pets"]=negatives;app["post_application"]={"published":14,"verified_no_pets":4,"out_of_current_category":1,"unresolved":111};dump(REPORTS/"louisville_founding_authority_application_001a_prepared.json",app)
    print("applied",len(records),len(exclusions),final)

if __name__=="__main__": main()
