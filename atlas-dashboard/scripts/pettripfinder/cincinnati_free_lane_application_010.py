# -*- coding: utf-8 -*-
"""PTF-CINCINNATI-FREE-LANE-APPLICATION-010 -- apply the independent probes.

    python -m scripts.pettripfinder.cincinnati_free_lane_application_010
    python -m scripts.pettripfinder.cincinnati_free_lane_application_010 --write

Applies the accumulated zero-cost evidence from PROBE-008 and PROBE-009: a
clean block of 1 pet-friendly and 7 verified-no-pets, plus five founder
rulings covering eight exception rows.

ONE GATE FLAG, AND IT WAS THE CHECK
-----------------------------------
The Phase 2 no-pets gate looks for an affirmative refusal. Its first
implementation searched for "not allowed" / "pets allowed: no" / "no pets", and
The Marcum says "Only service animals as defined by the ADA are permitted, all
other animals are prohibited". That is affirmative, explicit and property-bound
-- the phrase list was incomplete, the evidence was not. The list now includes
"prohibited", and it still refuses silence: a row with no quote at all cannot
pass.

FOUR RULINGS PUBLISH, ONE HOLDS
-------------------------------
  A  Drury x4 -- pet-friendly on the property-specific payload. The same pages'
     JSON-LD says petsAllowed:false; the founder ruled that bare boolean
     SOURCE_CONTRADICTORY and not controlling. It is preserved on every one of
     the four records, never deleted, and the disposition is bound to each
     identity separately rather than encoded in a shared reader.
  B  The Warehouse -- APPROVE_PARTIAL. Its DOM policy is unambiguous about
     species, count and charges; "2 pets max, 60 lb weight limit" never says
     whether 60 lb is per pet or combined, so the weight is withheld.
  C  Wildwood -- APPROVE_PARTIAL. "an assortment of pet friendly rooms" states
     acceptance and nothing else, so acceptance is all that publishes. The
     superseded POLICY_NOT_FOUND observation is preserved in provenance.
  E  The Summit -- APPROVE_PARTIAL. Its dog policy publishes; the $50 surcharge
     that applies only to two named room types has nowhere to live in a schema
     whose tier conditions are stay length and pet count, so it is withheld
     with its wording kept.
  D  Studio 6 -- HELD. The page says pets are welcome and states two different
     street addresses, and its only fee claim is a corporate link. It publishes
     nothing and KEEPS ITS ROUTE: a withdrawn route is how a row stops being
     worked, and this one still needs working.

GREAT WOLF
----------
Applied as VERIFIED_NO_PETS on its own /mason/faq prose -- "we do not allow any
pets into the lodge", with Mason-area kennel referrals binding it to this
property. Ruling #2 of APPLICATION-004 held this row pending exactly that, and
declined the bare JSON-LD flag. The page's JSON-LD is a corporate Chicago
address and is not what this rests on.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import hotel_exclusions as EX            # noqa: E402
from scripts.pettripfinder import market_authority as MA            # noqa: E402
from scripts.pettripfinder import policy_migration as PM            # noqa: E402
from scripts.pettripfinder.contracts import enums                   # noqa: E402
from scripts.pettripfinder.contracts import service_animal as SA    # noqa: E402
from scripts.pettripfinder.contracts.fee_computation import classify  # noqa: E402

WORK_ORDER = "PTF-CINCINNATI-FREE-LANE-APPLICATION-010"
MARKET_ID = "cincinnati-oh"
OPERATOR = "jfields80"
DECISION_DATE = "2026-08-31"

PKG = _REPO_ROOT / "launch_packages" / "pettripfinder"
REPORTS = PKG / "markets" / "reports"
PACKAGE = PKG / "hotel_policy_facts_cincinnati-oh.json"
CENSUS = PKG / "identity_census" / "cincinnati-oh.json"
PENDING = REPORTS / "cincinnati_free_lane_pending_application.json"
PROBE008 = REPORTS / "cincinnati_probe008_results.json"
PROBE009 = REPORTS / "cincinnati_probe009_results.json"
DECISIONS = REPORTS / "cincinnati_independent_founder_decisions_010.json"

HELD = "studio 6 extended stay fairfield oh cincinnati"

#: The affirmative-refusal gate. A quote must SAY the hotel refuses pets --
#: "prohibited" belongs here as much as "not allowed", and no phrase in this
#: list can be satisfied by an empty quote.
REFUSAL_PHRASES = ("not allowed", "pets allowed: no", "do not allow",
                   "no pets", "prohibited", "not permitted")


class ApplicationError(Exception):
    pass


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def _money(cents):
    return [("amount_cents", cents), ("currency", "USD")]


def _tier(cents, lo, hi=None, role="REPLACEMENT_PRICE", basis=None):
    t = OrderedDict(_money(cents) + [
        ("role", role), ("condition_type", "stay_length_range"),
        ("boundary_unit", "nights"), ("condition_min", lo),
        ("basis_stated", True)])
    if hi is not None:
        t["condition_max"] = hi
    if basis:
        t["basis"] = basis
    return t


def _weight(value, operator="lte", scope="per_pet"):
    return OrderedDict((("value", value), ("unit", "lb"),
                        ("operator", operator), ("scope", scope)))


DRURY = ("drury inn and suites cincinnati northeast mason",
         "drury inn and suites cincinnati sharonville",
         "drury inn and suites middletown franklin",
         "drury plaza hotel cincinnati florence")

DRURY_RULING = (
    "APPROVE PET_FRIENDLY FROM PROPERTY-SPECIFIC PROSE/PAYLOAD. The pages "
    "contain complete property-specific pet terms: dogs and cats, $50 per room "
    "per night plus tax, maximum 2 pets, 80 lb combined weight. The same pages "
    "also contain JSON-LD petsAllowed: false. Treat that bare structured "
    "boolean as SOURCE_CONTRADICTORY. Do NOT use it as the controlling policy "
    "fact. The property-specific policy prose/payload is the stronger evidence "
    "because it expressly states operative pet terms. Approve the four Drury "
    "properties as pet-friendly using only the fields directly supported by "
    "their property-specific policy text. Preserve the conflicting JSON-LD "
    "flag in evidence/provenance as SOURCE_CONTRADICTORY. Do not delete or "
    "hide the contradiction. Do not widen a shared reader globally merely to "
    "force this outcome. Bind the disposition identity-specifically to each of "
    "the four properties.")

DRURY_FACTS = OrderedDict((
    ("pets_allowed", True),
    ("pet_fee", OrderedDict(_money(5000) + [
        ("basis", "per_night"), ("scope", "per_room"),
        ("tax_relationship", "plus_tax")])),
    ("pet_count_limit", 2),
    ("combined_weight_limit", OrderedDict((("value", 80), ("unit", "lb"),
                                           ("operator", "lte")))),
    ("species", OrderedDict((("dogs", "accepted"), ("cats", "accepted")))),
))

DRURY_WITHHELD = {"structured_pets_allowed_flag": (
    "SOURCE_CONTRADICTORY",
    "The same property page carries JSON-LD stating petsAllowed: "
    "http://schema.org/False, which contradicts the property-specific pet "
    "terms published here. The founder ruled the bare structured boolean is "
    "not the controlling policy fact and must be preserved rather than "
    "deleted. PTF-CINCINNATI-INDEPENDENT-FREE-PROBE-008 read only that flag "
    "and recorded POLICY_NOT_FOUND for the Mason property; "
    "PROBE-009 found the payload and superseded it.")}


#: identity_key -> what this order publishes for it. Only rows that produce a
#: policy record or an exclusion appear; NO_AUTHORITY_ACTION rows do not.
RULINGS = OrderedDict()

for _key in DRURY:
    RULINGS[_key] = {
        "founder_decision": "APPROVE_PET_FRIENDLY_ON_PROPERTY_PAYLOAD",
        "publishes": True, "excludes": False, "withdraw_route": True,
        "ruling": DRURY_RULING, "facts": DRURY_FACTS,
        "withheld": DRURY_WITHHELD,
        "bound_identity_specifically": True,
    }

RULINGS["the warehouse hotel at champion mill"] = {
    "founder_decision": "APPROVE_PARTIAL",
    "publishes": True, "excludes": False, "withdraw_route": True,
    "ruling": "APPROVE_PARTIAL if the re-read property-specific DOM policy "
              "cleanly supports pet acceptance. Use the textContent/DOM "
              "evidence recovered in Probe 009, not the earlier innerText "
              "silence. Publish only facts directly supported by that "
              "property-specific policy. If any field remains ambiguous: "
              "withhold that field. Do not infer from hidden markup unless it "
              "is demonstrably part of the rendered property page DOM and "
              "identity-bound.",
    "facts": OrderedDict((
        ("pets_allowed", True),
        ("pet_fee", OrderedDict(_money(5000) + [("basis", "per_stay")])),
        ("fee_tiers", [_tier(1000, 4, role="ADDITIONAL_CHARGE",
                             basis="per_night")]),
        ("pet_count_limit", 2),
        ("species", OrderedDict((("dogs", "accepted"), ("cats", "accepted")))),
        ("general_restrictions",
         "Source wording, preserved: 'Cats & Dogs ONLY - 2 pets max, 60 lb "
         "weight limit. Limited to Standard Room types (King Sofa & 2 Queen "
         "Bed) There will be a fee of $50 per stay, any stay longer than 3 "
         "nights will require an additional $10/night.' Pets are accepted "
         "only in Standard Room types."))),
    "withheld": {"weight_limit": (
        "SOURCE_AMBIGUOUS",
        "The property states '2 pets max, 60 lb weight limit' and never says "
        "whether 60 lb is per pet or combined. Publishing either reading would "
        "tell some guests they qualify when they may not, so the limit is "
        "withheld and its wording preserved verbatim.")},
}

RULINGS["wildwood inn"] = {
    "founder_decision": "APPROVE_PARTIAL",
    "publishes": True, "excludes": False, "withdraw_route": True,
    "ruling": "APPROVE_PARTIAL if the corrected textContent/embedded evidence "
              "provides property-specific pet acceptance terms. The earlier "
              "POLICY_NOT_FOUND result is superseded by the corrected "
              "capture. Publish only explicitly supported fields. Preserve "
              "the prior incorrect observation in provenance; do not erase it.",
    "facts": OrderedDict((
        ("pets_allowed", True),
        ("general_restrictions",
         "Source wording, preserved: 'With African Safari style huts, 13 "
         "uniquely themed suites (including the Grand Canyon, Treehouse, "
         "Rome, and our Vintage Cars suites), 14 family style suites and an "
         "assortment of pet friendly rooms, you can experience something new "
         "every time.' The property states that only some of its rooms accept "
         "pets and does not say which, so guests should confirm at booking."))),
    "withheld": {},
    "supersedes": ("PTF-CINCINNATI-INDEPENDENT-FREE-PROBE-008 recorded this "
                   "row POLICY_NOT_FOUND. That reading came from an innerText "
                   "sweep; the statement is present in the page DOM (2,832 "
                   "characters against 694 visible) and PROBE-009 recovered "
                   "it. The incorrect observation is preserved here rather "
                   "than erased."),
}

RULINGS["the summit hotel"] = {
    "founder_decision": "APPROVE_PARTIAL",
    "publishes": True, "excludes": False, "withdraw_route": True,
    "ruling": "APPROVE_PARTIAL. Use the property-specific "
              "/about-us/hotel-policies evidence recovered in Probe 008. "
              "Approve only directly supported dog-policy fields. Do not "
              "infer unsupported species/fee/count/weight semantics.",
    "facts": OrderedDict((
        ("pets_allowed", True),
        ("pet_fee", OrderedDict(_money(5000) + [
            ("basis", "per_stay"), ("refundable_stated", False)])),
        ("pet_count_limit", 2),
        ("weight_limit", _weight(50, operator="lt")),
        ("species", OrderedDict((("dogs", "accepted"),
                                 ("cats", "prohibited")))),
        ("general_restrictions",
         "Source wording, preserved: 'The Summit welcomes dogs under 50 "
         "pounds. Pets must be declared upon check-in. Maximum (2) dogs per "
         "room. A non-refundable $50 fee applies. An additional $50 fee "
         "applies for One Bedroom Suites and the Presidential Suite.' Pets "
         "must be declared at check-in."))),
    "withheld": {"other_charges": (
        "SCHEMA_CANNOT_REPRESENT",
        "A second $50 applies only to One Bedroom Suites and the Presidential "
        "Suite. The schema's tier conditions are stay_length_range and "
        "pet_count_range, so a ROOM-TYPE condition has nowhere to live, and "
        "publishing the surcharge unconditioned would tell every guest they "
        "might owe it. The wording is preserved instead.")},
}

RULINGS[HELD] = {
    "founder_decision": "HOLD_FOR_IDENTITY_ADDRESS_CLARIFICATION",
    "publishes": False, "excludes": False, "withdraw_route": False,
    "ruling": "HOLD FOR IDENTITY/ADDRESS CLARIFICATION. The property is "
              "free-capturable and the page says pets are welcome, but the "
              "page states two different street addresses and the "
              "fee-relevant 'Pets Stay Free' statement is corporate/unbound. "
              "Do NOT publish policy yet. Do not infer which address is "
              "authoritative. Keep unresolved until the address identity "
              "issue is mechanically settled.",
}


# ------------------------------------------------------------------- builders

def _evidence(row: Dict, fields: List[str]) -> List[Dict]:
    """One entry per published field, all citing the same rendered page.

    The artifact digest is the PAGE digest throughout. Drury's four properties
    share one policy payload byte for byte, so a surface digest could not tell
    them apart -- the same reason SCALE-006 gave for Choice's refusal block.
    """
    entries = []
    for field in fields:
        entry = OrderedDict((
            ("field", field),
            ("quote", row["quote"]),
            ("source_url", row["official_property_url"]),
            ("artifact_class", "PUBLICATION_GRADE_EVIDENCE"),
            ("artifact_sha256", "sha256:%s" % row["sha256_page"].replace("-", "")),
            ("artifact_kind", "rendered_html"),
            ("captured_at", row["observed_at"]),
            ("capture_method", "attended_chrome_render"),
            ("source_grade", "PT1_FIRST_PARTY"),
        ))
        entry["evidence_ref"] = PM.evidence_ref_for(entry)
        entries.append(entry)
    return entries


def _service_animal(row: Dict) -> Dict:
    quote = row["service_animal_statement"]["quote"]
    return OrderedDict((("stated", True),
                        ("charges_stated", SA.charges_stated(quote)),
                        ("quote", quote)))


def build_record(row: Dict, ruling: Dict) -> Dict:
    facts = _normalise(ruling["facts"])
    withheld = dict(ruling.get("withheld") or {})
    fields = [k for k in facts if k != "pets_allowed"]
    entries = _evidence(row, ["pets_allowed"] + fields)

    record = OrderedDict((
        ("key", row["identity_key"]),
        ("name", row.get("canonical_name") or row["identity_key"]),
        ("facts", facts),
        ("evidence", entries),
        ("evidence_count", len(entries)),
        ("evidence_quote", row["quote"]),
        ("source_url", row["official_property_url"]),
        ("source_type", "EXACT_ENTITY_DOMAIN"),
        ("verification_state", "VERIFIED_PET_FRIENDLY"),
        ("verification_date", row["observed_at"]),
        ("verified_at", row["observed_at"]),
        ("worker_model_id", ""), ("worker_prompt_version", ""),
        ("worker_result_hash", row["sha256_page"].replace("-", "")),
        ("worker_routing_version", ""), ("worker_validator_version", ""),
        ("schema_version", enums.POLICY_SCHEMA_VERSION),
        ("identity_key", row["identity_key"]),
        ("market_id", MARKET_ID),
    ))
    if row.get("service_animal_statement"):
        record["service_animal_statement"] = _service_animal(row)
    record["computation_class"] = classify(facts).computation_class
    if withheld:
        record["withheld_fields"] = OrderedDict(
            (field, OrderedDict((
                ("reason_code", code), ("reason", why),
                ("evidence_refs", [entries[0]["evidence_ref"]]))))
            for field, (code, why) in sorted(withheld.items()))

    caveats = [
        "FOUNDER RULING (%s): %s" % (ruling["founder_decision"],
                                     ruling["ruling"]),
        "%s. Applied from the zero-cost attended-Chrome evidence of "
        "PTF-CINCINNATI-INDEPENDENT-FREE-PROBE-008 and -009, against THIS "
        "record_hash." % WORK_ORDER,
        "Attended browser only: provider calls 0, spend $0.00. The artifact "
        "digest is a SHA256 over the page's rendered outerHTML with the quote "
        "taken from the same DOM in the same JavaScript call.",
    ]
    if ruling.get("bound_identity_specifically"):
        caveats.append(
            "This disposition is bound to THIS identity. Four Cincinnati Drury "
            "properties share the ruling and each carries it on its own "
            "record; no shared reader was widened to encode it.")
    if ruling.get("supersedes"):
        caveats.append("SUPERSEDES: %s" % ruling["supersedes"])
    record["approval"] = OrderedDict((
        ("decision", "APPROVED_AFTER_CURRENT_REVIEW"),
        ("operator", OPERATOR),
        ("approval_date", DECISION_DATE),
        ("caveats", caveats),
        ("record_hash", PM.record_hash(record)),
        ("evidence_hash", PM.evidence_hash(entries)),
    ))
    return record


def build_exclusion(row: Dict, census: Dict) -> Dict:
    key = row["identity_key"]
    census_row = census.get(key)
    if census_row is None:
        raise ApplicationError("%s is not in the census" % key)
    note = ("%s: affirmative, property-specific refusal in the property's own "
            "words, captured by attended browser at zero cost." % WORK_ORDER)
    # A row released from a founder HOLD must say what released it, or the
    # record loses the only trace of why the hold lifted.
    if row.get("satisfies_hold"):
        note = "%s RELEASED FROM FOUNDER HOLD: %s" % (note, row["satisfies_hold"])
    record = OrderedDict((
        ("exclusion_id", "cin-" + key.replace(" ", "-")),
        ("canonical_name", census_row["canonical_name"]),
        ("normalized_name", key),
        ("address", census_row.get("address", "")),
        ("city", census_row.get("city", "")),
        ("state", census_row.get("state", "")),
        ("postal_code", census_row.get("postal_code", "")),
        ("phone", census_row.get("phone", "")),
        ("official_url", row["official_property_url"]),
        ("exclusion_state", "VERIFIED_NO_PETS"),
        ("evidence_quote", row["quote"]),
        ("source_url", row["official_property_url"]),
        ("observed_at", row["observed_at"]),
        ("source_hash", "sha256:%s" % row["sha256_page"].replace("-", "")),
        ("reviewer_id", OPERATOR),
        ("reviewed_at", DECISION_DATE),
        ("notes", note),
        ("market_id", MARKET_ID),
    ))
    record["record_hash"] = EX.record_hash(record)
    record["approval_hash"] = EX.approval_hash(record)
    return record


# ---------------------------------------------------------------------- build

def _normalise(facts: Dict) -> Dict:
    """SHAPE only -- currency and refundability are required, never inferred.

    The probe artifacts record a charge as amount + basis; the validator also
    demands an explicit currency, and for other_charges an explicit
    ``refundable``. Erlanger's source says the 100 USD is "Refundable", so that
    is a reading and not an inference; a charge whose source did not say would
    have to be withheld instead.
    """
    out = OrderedDict()
    for name, value in facts.items():
        if name == "pet_fee" and isinstance(value, dict)                 and "currency" not in value:
            value = OrderedDict(_money(value["amount_cents"])
                                + [(k, v) for k, v in value.items()
                                   if k != "amount_cents"])
        elif name == "other_charges" and isinstance(value, list):
            charges = []
            for charge in value:
                if "currency" in charge and "refundable" in charge:
                    charges.append(charge)
                    continue
                fixed = OrderedDict(_money(charge["amount_cents"]))
                for k, v in charge.items():
                    if k != "amount_cents":
                        fixed[k] = v
                fixed.setdefault(
                    "refundable", charge["kind"] == "refundable_deposit")
                charges.append(fixed)
            value = charges
        out[name] = value
    return out


def _observations():
    """Every probe row, with PROBE-009's corrections applied.

    PROBE-008's Drury Mason and Wildwood rows carry the readings PROBE-009
    disproved -- an empty quote and no facts. Building a record from those
    would publish a founder ruling against evidence that does not exist.
    """
    rows = {}
    for path in (PROBE008, PROBE009):
        for row in _load(path)["rows"]:
            rows[row["identity_key"]] = row
    for key, fix in _load(PROBE009)["probe_008_corrections"].items():
        if fix["was"] == fix["now"]:
            continue
        row = OrderedDict(rows[key])
        row["outcome"] = fix["now"]
        row["quote"] = fix["quote"]
        row["facts"] = fix["facts"]
        row["sha256_page"] = fix["sha256_page"]
        row["sha256_policy_surface"] = fix["sha256_policy_surface"]
        row["policy_surface_found"] = True
        row["corrected_by"] = "PTF-CINCINNATI-INDEPENDENT-FREE-PROBE-009"
        rows[key] = row
    return rows


def build():
    pending = _load(PENDING)
    obs = _observations()
    census = {h["identity_key"]: h for h in _load(CENSUS)["hotels"]}

    clean_pf = pending["buckets"]["CLEAN_PET_FRIENDLY"]
    clean_np = pending["buckets"]["CLEAN_VERIFIED_NO_PETS"]
    exceptions = pending["buckets"]["FOUNDER_EXCEPTION"]
    if len(clean_pf) != 1 or len(clean_np) != 7 or len(exceptions) != 8:
        raise ApplicationError("pending inventory is %d/%d/%d, expected 1/7/8"
                               % (len(clean_pf), len(clean_np),
                                  len(exceptions)))
    if {e["identity_key"] for e in exceptions} != set(RULINGS):
        raise ApplicationError("the rulings do not cover the exceptions exactly")

    # ---- Phase 2 gates, run before any record is built.
    rejected = []
    for entry in clean_pf + clean_np:
        key = entry["identity_key"]
        row = obs[key]
        if not row.get("quote"):
            rejected.append((key, "no quote"))
        if not row.get("sha256_page"):
            rejected.append((key, "no evidence hash"))
        if key not in census:
            rejected.append((key, "not in census"))
        if entry in clean_np:
            quote = (row.get("quote") or "").lower()
            if not any(p in quote for p in REFUSAL_PHRASES):
                rejected.append((key, "refusal not affirmative"))
        else:
            if row["facts"].get("pets_allowed") is not True:
                rejected.append((key, "allowance not explicit"))
            if not census[key].get("address"):
                rejected.append((key, "no street address for a seed row"))
    if rejected:
        raise ApplicationError("clean-block gate failures: %s" % rejected)

    package = _load(PACKAGE)
    published = {h["identity_key"] for h in package["hotels"]}

    new_records = [build_record(obs[clean_pf[0]["identity_key"]],
                                {"founder_decision": "BLOCK_AUTHORIZED_CLEAN",
                                 "ruling": "Founder block authorization of the "
                                           "clean pet-friendly candidate from "
                                           "the zero-cost independent probes.",
                                 "facts": obs[clean_pf[0]["identity_key"]]["facts"],
                                 "withheld": {}})]
    for key, ruling in RULINGS.items():
        if ruling["publishes"]:
            new_records.append(build_record(obs[key], ruling))

    new_exclusions = [build_exclusion(obs[e["identity_key"]], census)
                      for e in clean_np]

    for rec in new_records:
        if rec["identity_key"] in published:
            raise ApplicationError("%s is already published"
                                   % rec["identity_key"])
    keys = [r["identity_key"] for r in new_records]
    ex_keys = [e["normalized_name"] for e in new_exclusions]
    if len(set(keys)) != len(keys):
        raise ApplicationError("duplicate identity in the applied set")
    if len(set(ex_keys)) != len(ex_keys):
        raise ApplicationError("duplicate identity in the exclusion set")
    if set(keys) & set(ex_keys):
        raise ApplicationError("an identity is both published and excluded")
    if HELD in set(keys) | set(ex_keys):
        raise ApplicationError("the held identity was applied")

    package["hotels"] = package["hotels"] + new_records
    problems = PM.validate_migrated(package)
    if problems:
        raise ApplicationError("package does not validate: %s" % problems[:8])

    return package, new_records, new_exclusions, sorted(set(keys) | set(ex_keys))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    try:
        package, records, exclusions, withdraw = build()
    except ApplicationError as exc:
        print("REFUSED: %s" % exc)
        return 2

    print("clean pet-friendly applied : 1")
    print("clean verified-no-pets     : 7")
    print("founder rulings applied    : %d of 5 (Studio 6 holds)"
          % len({r["founder_decision"] for r in RULINGS.values()
                 if r["publishes"]}))
    print("new policy records         : %d" % len(records))
    print("new exclusions             : %d" % len(exclusions))
    print("package total              : %d" % len(package["hotels"]))
    print("routes to withdraw         : %d (%s keeps its route)"
          % (len(withdraw), HELD))
    if not args.write:
        return 0

    PACKAGE.write_text(json.dumps(package, indent=1, ensure_ascii=False) + "\n",
                       encoding="utf-8", newline="\n")
    print("WROTE %s (%d records)" % (PACKAGE.name, len(package["hotels"])))

    doc = MA.load_market_exclusions_document(MARKET_ID)
    doc["exclusions"] = doc["exclusions"] + exclusions
    doc["count"] = len(doc["exclusions"])
    MA.exclusions_shard_path(MARKET_ID).write_text(
        MA.render_json(doc), encoding="utf-8", newline="\n")
    print("WROTE exclusions shard (%d rows)" % doc["count"])

    decisions = OrderedDict((
        ("schema", "ptf-market-founder-decisions/1.0"),
        ("work_order", WORK_ORDER),
        ("parent_work_orders", ["PTF-CINCINNATI-INDEPENDENT-FREE-PROBE-008",
                                "PTF-CINCINNATI-INDEPENDENT-FREE-PROBE-009"]),
        ("market_id", MARKET_ID), ("as_of", DECISION_DATE),
        ("operator", OPERATOR),
        ("note", "The founder's five rulings, verbatim, plus the block "
                 "authorization of 1 clean pet-friendly and 7 clean "
                 "verified-no-pets candidates from the zero-cost independent "
                 "probes."),
        ("block_authorization", OrderedDict((
            ("clean_pet_friendly", 1), ("clean_verified_no_pets", 7),
            ("verified_before_application", True),
            ("candidates_removed_from_block", 0),
            ("gate_note",
             "The affirmative-refusal check initially flagged The Marcum, "
             "whose refusal reads 'all other animals are prohibited'. The "
             "phrase list was incomplete, not the evidence; 'prohibited' was "
             "added and the gate still refuses an empty quote.")))),
        ("count", len(RULINGS)),
        ("decision_counts", OrderedDict(sorted(Counter(
            r["founder_decision"] for r in RULINGS.values()).items()))),
        ("rows", [OrderedDict((
            ("identity_key", k),
            ("founder_decision", v["founder_decision"]),
            ("ruling", v["ruling"]),
            ("publishes", v["publishes"]),
            ("route_withdrawn", bool(v.get("withdraw_route"))),
        )) for k, v in RULINGS.items()]),
    ))
    DECISIONS.write_text(json.dumps(decisions, indent=1, ensure_ascii=False)
                         + "\n", encoding="utf-8", newline="\n")
    print("WROTE %s" % DECISIONS.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
