"""PTF-LOUISVILLE-PASS1-FOUNDER-DECISIONS-001.

Applies the founder's Pass 1 decisions from the review packet:

- HOLD_PARTIAL_AFFIRMATIVE: 21c Museum Hotel Louisville
- APPROVE_AFFIRMATIVE_STRUCTURED: Bellwether Hotel, Galt House Hotel
- APPROVE_VERIFIED_NO_PETS: Econo Lodge Downtown, Hotel Louisville Downtown,
  The Brown Hotel
- HOLD_ACCESS_BLOCKED: Hotel Genevieve (no facts)

Does not write seed rows, a release contract, or a Netlify change.
Does not assemble or deploy Louisville.

    python -m scripts.pettripfinder.apply_louisville_pass1_founder_decisions
"""
from __future__ import annotations

import json
from collections import Counter, OrderedDict
from pathlib import Path

from scripts.pettripfinder.census_partition_builder import write_json
from scripts.pettripfinder.contracts import census, enums, partition
from scripts.pettripfinder.contracts import evidence as evidence_contract
from scripts.pettripfinder.contracts import policy_schema
from scripts.pettripfinder.hotel_exclusions import (
    EXCLUSIONS_PATH, approval_hash, record_hash as exclusion_record_hash,
    validate as validate_exclusions,
)
from scripts.pettripfinder.policy_migration import (
    evidence_hash, evidence_ref_for, record_hash,
)

REPO = Path(__file__).resolve().parents[2]
PKG = REPO / "launch_packages" / "pettripfinder"
CENSUS_PATH = PKG / "identity_census" / "louisville-ky.json"
PARTITION_PATH = PKG / "louisville_final_partition_001.json"
PACKET_PATH = PKG / "markets" / "reports" / "louisville_pass1_founder_review_packet.json"
RESULTS_PATH = PKG / "markets" / "reports" / "louisville_pass1_capture_results.json"
DECISIONS_PATH = PKG / "markets" / "reports" / "louisville_pass1_founder_decisions.json"
POLICY_PATH = PKG / "markets" / "reports" / "louisville_pass1_approved_policy_records.json"
WORK = "PTF-LOUISVILLE-PASS1-FOUNDER-DECISIONS-001"
AS_OF = "2026-08-16"
OPERATOR = "jfields80"
REVIEWED_AT = "2026-08-16T12:00:00-04:00"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _evidence(field, quote, url, sha, value=None):
    entry = OrderedDict((
        ("field", field),
        ("quote", quote),
        ("source_url", url),
        ("source_grade", enums.GRADE_PT1_FIRST_PARTY),
        ("artifact_class", enums.PUBLICATION_GRADE_EVIDENCE),
        ("artifact_sha256", "sha256:%s" % sha),
        ("artifact_kind", enums.ARTIFACT_RENDERED_HTML),
        ("captured_at", AS_OF),
        ("capture_method", "https_get_official_page"),
    ))
    if value is not None:
        entry["value"] = value
    entry["evidence_ref"] = evidence_ref_for(entry)
    return entry


def _policy_record(*, name, key, facts, evidence, withheld, source_url,
                   computation_class):
    issues = policy_schema.validate_facts(facts)
    if issues:
        raise SystemExit("%s facts: %s" % (name, issues))
    record = OrderedDict((
        ("key", key),
        ("name", name),
        ("facts", facts),
        ("evidence", evidence),
        ("evidence_count", len(evidence)),
        ("evidence_quote", " ".join(e["quote"] for e in evidence)),
        ("source_url", source_url),
        ("source_type", "EXACT_ENTITY_DOMAIN"),
        ("verification_state", "VERIFIED_PET_FRIENDLY"),
        ("verification_date", AS_OF),
        ("verified_at", AS_OF),
        ("schema_version", "1.2"),
        ("identity_key", key),
        ("market_id", "louisville-ky"),
        ("computation_class", computation_class),
        ("founder_attested", True),
        ("founder_work_order", WORK),
    ))
    if withheld:
        record["withheld_fields"] = withheld
    ev_issues = evidence_contract.validate(record)
    if ev_issues:
        raise SystemExit("%s evidence: %s" % (name, ev_issues))
    approval = OrderedDict((
        ("decision", enums.APPROVED_AFTER_CURRENT_REVIEW),
        ("operator", OPERATOR),
        ("approval_date", AS_OF),
        ("record_hash", record_hash(record)),
        ("evidence_hash", evidence_hash(evidence)),
        ("caveats", [
            "Founder decision %s. Reviewed against the Pass 1 capture "
            "packet and the retained official-page artifact." % WORK
        ]),
    ))
    record["approval"] = approval
    return record


def _set_terminal(item, state, reason):
    item["final_state"] = state
    item["resolved"] = True
    item["next_action"] = ""
    item["next_action_source"] = ""
    item["determined_by"] = ""
    item["updated_at"] = AS_OF
    item["state_override_reason"] = reason


def _set_hold(item, state, action, reason):
    from scripts.pettripfinder.census_partition_builder import next_action_for
    item["final_state"] = state
    item["resolved"] = False
    item["next_action"] = action or next_action_for(state)
    item["next_action_source"] = "markets/reports/louisville_pass1_founder_decisions.json"
    item["determined_by"] = WORK
    item["updated_at"] = AS_OF
    item["state_override_reason"] = reason


def main() -> None:
    census_doc = _load(CENSUS_PATH)
    part_doc = _load(PARTITION_PATH)
    packet = _load(PACKET_PATH)
    hotels = {h["identity_key"]: h for h in census_doc["hotels"]}
    items = {i["identity_key"]: i for i in part_doc["items"]}

    bell_sha = "f22f9436153498c752fa5ec655e97deab0551835568d5ad917a3ccbc5af8667d"
    galt_sha = "4998d9e65d934ff0898376dd07086a1652d68f42b7018507ca4197b0de5af355"
    econo_sha = "5c854fa35d3420f346c9e1e73a6bb58d3faeb4ca6e92f2d6df9e9f147333a579"
    hl_sha = "6328503c741d0223c6ac8eed72fcd2da06215d210563e0813b10fcbeec8c3436"
    brown_sha = "aed7d22e45f3583960e00eec849c3608fe404abd0201ae5332aef7426ff3bd1e"

    q_bell = (
        "The Bellwether Hotel allows dogs only with the following restrictions: "
        "Dogs are only allowed in first floor rooms. We allow up to two dogs to "
        "stay as long as their combined weight is not over 50 pounds, or one dog "
        "not over 50 pounds. A $35 pet fee will be required at time of booking."
    )
    q_galt = (
        "The hotel allows up to two dogs (45 lbs or less) per room for a fee "
        "of $50 per dog. You must request to have your room cleaned and "
        "accompany your dog while the room is being cleaned."
    )
    q_econo = "No Pets Allowed"
    q_hl = "Is Hotel Louisville pet-friendly? No, only service animals are welcome at the property."
    q_brown = "Pets not allowed (service animals are welcome, and are exempt from fees)."

    bell_ev = [
        _evidence("pets_allowed", q_bell,
                  "https://www.thebellwetherhotel.com/faqs", bell_sha, "true"),
        _evidence("species", q_bell,
                  "https://www.thebellwetherhotel.com/faqs", bell_sha, "dogs"),
        _evidence("pet_count_limit", q_bell,
                  "https://www.thebellwetherhotel.com/faqs", bell_sha, "2"),
        _evidence("combined_weight_limit", q_bell,
                  "https://www.thebellwetherhotel.com/faqs", bell_sha, "50 pounds"),
        _evidence("pet_room_restriction", q_bell,
                  "https://www.thebellwetherhotel.com/faqs", bell_sha),
        _evidence("unattended_policy",
                  "Pets must not be left unattended in room, or anywhere else on hotel property unless crated.",
                  "https://www.thebellwetherhotel.com/faqs", bell_sha),
        _evidence("reservation_requirement",
                  "Please notify us at time of booking if a dog will be staying.",
                  "https://www.thebellwetherhotel.com/faqs", bell_sha),
    ]
    galt_ev = [
        _evidence("pets_allowed", q_galt, "https://galthouse.com/hotel-faq/",
                  galt_sha, "true"),
        _evidence("species", q_galt, "https://galthouse.com/hotel-faq/",
                  galt_sha, "dogs"),
        _evidence("pet_count_limit", q_galt, "https://galthouse.com/hotel-faq/",
                  galt_sha, "2"),
        _evidence("pet_count_scope", q_galt, "https://galthouse.com/hotel-faq/",
                  galt_sha, "room"),
        _evidence("weight_limit", q_galt, "https://galthouse.com/hotel-faq/",
                  galt_sha, "45 pounds"),
        _evidence("pet_fee", q_galt, "https://galthouse.com/hotel-faq/",
                  galt_sha, "$50.00"),
        _evidence("unattended_policy", q_galt, "https://galthouse.com/hotel-faq/",
                  galt_sha),
    ]

    policy_hotels = [
        _policy_record(
            name="Bellwether Hotel", key="bellwether hotel",
            facts=OrderedDict((
                ("pets_allowed", True),
                ("species", {"dogs": enums.SPECIES_ACCEPTED}),
                ("pet_count_limit", 2),
                ("combined_weight_limit",
                 {"value": 50, "unit": "lb", "operator": enums.OP_LTE}),
                ("pet_room_restriction", "Dogs are only allowed in first floor rooms."),
                ("unattended_policy",
                 "Pets must not be left unattended in room, or anywhere else on hotel property unless crated."),
                ("reservation_requirement",
                 "Please notify us at time of booking if a dog will be staying."),
            )),
            evidence=bell_ev,
            withheld=OrderedDict((
                ("pet_fee", OrderedDict((
                    ("reason_code", "SOURCE_AMBIGUOUS"),
                    ("reason",
                     "A $35 pet fee is required at booking; the page does not "
                     "state stay/night basis or per-pet/per-room scope."),
                    ("evidence_refs", [bell_ev[0]["evidence_ref"]]),
                ))),
            )),
            source_url="https://www.thebellwetherhotel.com/faqs",
            computation_class=enums.NOT_COMPUTABLE,
        ),
        _policy_record(
            name="Galt House Hotel", key="galt house hotel",
            facts=OrderedDict((
                ("pets_allowed", True),
                ("species", {"dogs": enums.SPECIES_ACCEPTED}),
                ("pet_count_limit", 2),
                ("pet_count_scope", "room"),
                ("weight_limit", {
                    "value": 45, "unit": "lb", "operator": enums.OP_LTE,
                    "scope": "per_pet",
                }),
                ("pet_fee", {
                    "amount_cents": 5000, "currency": "USD",
                    "basis": enums.BASIS_PER_STAY, "scope": enums.SCOPE_PER_PET,
                }),
                ("unattended_policy",
                 "You must request to have your room cleaned and accompany your dog while the room is being cleaned."),
            )),
            evidence=galt_ev,
            withheld=OrderedDict(),
            source_url="https://galthouse.com/hotel-faq/",
            computation_class=enums.COMPUTATION_SAFE_ARBITRARY_ALLOWED_PET_COUNT,
        ),
    ]
    policy_doc = OrderedDict((
        ("schema_version", "1.2"),
        ("market", "louisville-ky"),
        ("work_order", WORK),
        ("note",
         "Louisville Pass 1 founder-approved records only. 21c is held "
         "partial. Hotel Genevieve is access-blocked. Not a full-market "
         "authority and not a release."),
        ("hotels", policy_hotels),
    ))
    write_json(POLICY_PATH, policy_doc)

    def exclusion(name, key, quote, url, sha, address, phone, zip5):
        row = OrderedDict((
            ("canonical_name", name),
            ("address", address),
            ("city", "Louisville"),
            ("state", "KY"),
            ("postal_code", zip5),
            ("phone", phone),
            ("official_url", url),
            ("exclusion_state", enums.VERIFIED_NO_PETS),
            ("evidence_quote", quote),
            ("source_url", url),
            ("observed_at", AS_OF),
            ("reviewer_id", OPERATOR),
            ("reviewed_at", REVIEWED_AT),
            ("notes",
             "Founder decision %s. PT1 official page. Artifact sha256:%s."
             % (WORK, sha)),
            ("exclusion_id", "excl-%s" % key.replace(" ", "-")),
            ("normalized_name", key),
            ("source_hash", "sha256:" + sha),
            ("market_id", "louisville-ky"),
        ))
        row["record_hash"] = exclusion_record_hash(row)
        row["approval_hash"] = approval_hash(row)
        return row

    excl_doc = _load(EXCLUSIONS_PATH)
    existing = [e for e in excl_doc["exclusions"]
                if e.get("market_id") != "louisville-ky"]
    new_excl = [
        exclusion("Econo Lodge Downtown", "econo lodge downtown", q_econo,
                  "http://www.econodowntown.com/louisville-ky-hotel-amenities.html",
                  econo_sha, "401 S 2nd St", "502-583-2841", "40202"),
        exclusion("Hotel Louisville Downtown", "hotel louisville downtown", q_hl,
                  "https://www.hotellouisville.org/rooms",
                  hl_sha, "120 W Broadway", "502-582-2241", "40202"),
        exclusion("The Brown Hotel", "the brown hotel", q_brown,
                  "https://www.brownhotel.com/frequently-asked-questions",
                  brown_sha, "335 W Broadway", "502-583-1234", "40202"),
    ]
    excl_doc["exclusions"] = existing + new_excl
    validate_exclusions(excl_doc)
    write_json(EXCLUSIONS_PATH, excl_doc)

    _set_terminal(
        items["bellwether hotel"], enums.PUBLISHED_PET_FRIENDLY,
        "FOUNDER_DECISION %s LVL-P1-002 APPROVE_AFFIRMATIVE_STRUCTURED." % WORK)
    _set_terminal(
        items["galt house hotel"], enums.PUBLISHED_PET_FRIENDLY,
        "FOUNDER_DECISION %s LVL-P1-004 APPROVE_AFFIRMATIVE_STRUCTURED." % WORK)
    _set_terminal(
        items["econo lodge downtown"], enums.VERIFIED_NO_PETS,
        "FOUNDER_DECISION %s LVL-P1-003 APPROVE_VERIFIED_NO_PETS." % WORK)
    _set_terminal(
        items["hotel louisville downtown"], enums.VERIFIED_NO_PETS,
        "FOUNDER_DECISION %s LVL-P1-006 APPROVE_VERIFIED_NO_PETS." % WORK)
    _set_terminal(
        items["the brown hotel"], enums.VERIFIED_NO_PETS,
        "FOUNDER_DECISION %s LVL-P1-007 APPROVE_VERIFIED_NO_PETS." % WORK)
    _set_hold(
        items["21c museum hotel louisville"], enums.AWAITING_POLICY_OBSERVATION,
        "Hold the partial $40 fee until basis and scope are stated; do not publish.",
        "FOUNDER_DECISION %s LVL-P1-001 HOLD_PARTIAL_AFFIRMATIVE." % WORK)
    _set_hold(
        items["hotel genevieve"], enums.ACCESS_BLOCKED, "",
        "FOUNDER_DECISION %s LVL-P1-005 HOLD_ACCESS_BLOCKED." % WORK)

    hotels["bellwether hotel"]["policy_state"] = enums.POLICY_CONFIRMED
    hotels["galt house hotel"]["policy_state"] = enums.POLICY_CONFIRMED
    hotels["econo lodge downtown"]["policy_state"] = enums.VERIFIED_NO_PETS
    hotels["hotel louisville downtown"]["policy_state"] = enums.VERIFIED_NO_PETS
    hotels["the brown hotel"]["policy_state"] = enums.VERIFIED_NO_PETS

    counts = OrderedDict()
    for state in enums.PARTITION_STATES:
        n = sum(1 for i in part_doc["items"] if i["final_state"] == state)
        if n:
            counts[state] = n
    from scripts.pettripfinder.contracts.partition import STATE_MEANINGS
    present = {i["final_state"] for i in part_doc["items"]}
    part_doc["final_state_counts"] = counts
    part_doc["final_state_meanings"] = OrderedDict(
        (s, STATE_MEANINGS[s]) for s in enums.PARTITION_STATES if s in present)
    part_doc["as_of"] = AS_OF
    part_doc["note"] = (
        "Louisville identities remain unpublished as a site. Pass 1 founder "
        "decisions placed two records in PUBLISHED_PET_FRIENDLY and three in "
        "VERIFIED_NO_PETS. Silence is not a refusal."
    )
    write_json(PARTITION_PATH, part_doc)
    write_json(CENSUS_PATH, census_doc)

    rec = partition.reconcile(
        census.identity_keys(census_doc), part_doc, market_id="louisville-ky")
    if not rec.agrees:
        raise SystemExit("census/partition disagree")
    issues = census.validate(census_doc, market_states=["KY", "IN"])
    if issues:
        raise SystemExit(issues)
    issues = partition.validate(part_doc)
    if issues:
        raise SystemExit(issues)

    packet["founder_approvals_written"] = True
    packet["applied_work_order"] = WORK
    packet["note"] = (
        "Founder decisions applied %s. Two records entered the Louisville "
        "policy authority. Three VERIFIED_NO_PETS exclusions were written. "
        "21c held partial. Genevieve remains ACCESS_BLOCKED. No seed, "
        "release contract, or deploy." % AS_OF
    )
    write_json(PACKET_PATH, packet)

    decisions = OrderedDict((
        ("schema", "ptf-louisville-pass1-founder-decisions/1.0"),
        ("work_order", WORK),
        ("market_id", "louisville-ky"),
        ("as_of", AS_OF),
        ("operator", OPERATOR),
        ("decisions", [
            OrderedDict((
                ("decision_id", "LVL-P1-001"),
                ("identity_key", "21c museum hotel louisville"),
                ("decision", "HOLD_PARTIAL_AFFIRMATIVE"),
                ("applied", True),
            )),
            OrderedDict((
                ("decision_id", "LVL-P1-002"),
                ("identity_key", "bellwether hotel"),
                ("decision", "APPROVE_AFFIRMATIVE_STRUCTURED"),
                ("applied", True),
            )),
            OrderedDict((
                ("decision_id", "LVL-P1-003"),
                ("identity_key", "econo lodge downtown"),
                ("decision", "APPROVE_VERIFIED_NO_PETS"),
                ("applied", True),
            )),
            OrderedDict((
                ("decision_id", "LVL-P1-004"),
                ("identity_key", "galt house hotel"),
                ("decision", "APPROVE_AFFIRMATIVE_STRUCTURED"),
                ("applied", True),
            )),
            OrderedDict((
                ("decision_id", "LVL-P1-005"),
                ("identity_key", "hotel genevieve"),
                ("decision", "HOLD_ACCESS_BLOCKED"),
                ("applied", True),
            )),
            OrderedDict((
                ("decision_id", "LVL-P1-006"),
                ("identity_key", "hotel louisville downtown"),
                ("decision", "APPROVE_VERIFIED_NO_PETS"),
                ("applied", True),
            )),
            OrderedDict((
                ("decision_id", "LVL-P1-007"),
                ("identity_key", "the brown hotel"),
                ("decision", "APPROVE_VERIFIED_NO_PETS"),
                ("applied", True),
            )),
        ]),
        ("published", rec.published),
        ("verified_no_pets", rec.verified_no_pets),
        ("unresolved", rec.unresolved),
        ("site_assembled", False),
        ("release_contract_written", False),
    ))
    write_json(DECISIONS_PATH, decisions)
    print("published", rec.published, "no_pets", rec.verified_no_pets,
          "unresolved", rec.unresolved, "ooc", rec.out_of_category)
    print("partition", dict(part_doc["final_state_counts"]))


if __name__ == "__main__":
    main()
