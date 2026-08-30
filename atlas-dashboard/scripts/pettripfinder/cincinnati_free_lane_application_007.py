# -*- coding: utf-8 -*-
"""PTF-CINCINNATI-FREE-LANE-APPLICATION-007 -- apply the free lane.

    python -m scripts.pettripfinder.cincinnati_free_lane_application_007
    python -m scripts.pettripfinder.cincinnati_free_lane_application_007 --write

WHAT THE FOUNDER AUTHORISED
---------------------------
The reconciled 32-row clean block from PROBE-005 and SCALE-006 together -- 9
pet-friendly and 23 verified-no-pets -- plus ten individually reasoned rulings.
The original order carried a stale 5 + 20; the founder replaced it with the
reconciled figure after Phase 1 showed PROBE-005's seven clean rows had never
been applied.

Two of the ten do not produce a policy record:

  #1 Comfort Suites MainStay -- HOLD_FOR_IDENTITY_REVIEW. Three of four
     identity signals disagree and only the street number overlaps, on a page
     that qualifies it "Building B". Neither published nor excluded, and its
     route is explicitly NOT withdrawn: the founder ordered it kept unresolved
     until identity is mechanically settled, and a withdrawn route is how a
     row stops being worked.
  #2 Holiday Inn Express & Suites Bellevue -- RENAME, then EXCLUDE. The rename
     supersedes; the refusal is then registered against the new name.

WHAT THIS MODULE WILL NOT DO
----------------------------
It does not widen a shared reader to encode a founder decision, and it does not
convert a unit. Two properties state a fee of 50 USD per WEEK and the schema's
bases are per_night / per_day / per_stay; the amount is withheld as
SCHEMA_CANNOT_REPRESENT and the wording is preserved verbatim in
``general_restrictions``. Staybridge Florence states tier boundaries in DAYS and
its third clause is garbled at source; its fee is withheld whole rather than
read as nights or repaired.

THE IHG STRUCTURED FIELD
------------------------
SCALE-006 established that IHG emits "Pet fee per night: <X> USD" regardless of
the basis its own prose states -- Holiday Inn Cincinnati Airport says "75.00 USD
per stay" in prose and "per night" in the field, in the same panel. The founder
ruled the prose authoritative on every affected row. Each contradicted
structured reading is preserved as SOURCE_CONTRADICTORY rather than dropped, so
the reason a number was not published survives with the record.

EVIDENCE HASHES
---------------
``artifact_sha256`` is the PAGE digest, not the policy-surface digest. Choice
renders a byte-identical refusal block for every no-pets property -- seven of
them share one surface digest -- so the surface digest proves what was said and
never by whom. The page digest is unique per property, and it is what a
published claim must rest on.
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
from scripts.pettripfinder.contracts.fee_computation import classify  # noqa: E402
from scripts.pettripfinder.contracts.identity_key import ptf_identity_key  # noqa: E402

WORK_ORDER = "PTF-CINCINNATI-FREE-LANE-APPLICATION-007"
MARKET_ID = "cincinnati-oh"
OPERATOR = "jfields80"
DECISION_DATE = "2026-08-30"
OBSERVED_AT = "2026-08-29"

PKG = _REPO_ROOT / "launch_packages" / "pettripfinder"
REPORTS = PKG / "markets" / "reports"
PACKAGE = PKG / "hotel_policy_facts_cincinnati-oh.json"
CENSUS = PKG / "identity_census" / "cincinnati-oh.json"
PROBE = REPORTS / "cincinnati_probe005_results.json"
SCALE = REPORTS / "cincinnati_scale006_results.json"
DECISIONS = REPORTS / "cincinnati_free_lane_founder_decisions_007.json"
WITHDRAWALS = REPORTS / "cincinnati_free_lane_route_withdrawals_007.json"

RENAME_FROM = "holiday inn express and suites bellevue"
RENAME_TO = "Holiday Inn Express & Suites Cincinnati SE Newport"
HELD = "comfort suites mainstay hotel"


class ApplicationError(Exception):
    pass


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def _money(cents, currency="USD"):
    return OrderedDict((("amount_cents", cents), ("currency", currency)))


def _tier(cents, lo, hi=None, role="REPLACEMENT_PRICE"):
    """One stay-length tier. ``role`` is what stops "$75 fee + $100 cleaning"
    from rendering as a $75-$100 range."""
    t = OrderedDict((("amount_cents", cents), ("currency", "USD"),
                     ("role", role), ("condition_type", "stay_length_range"),
                     ("boundary_unit", "nights"), ("condition_min", lo),
                     ("basis_stated", True)))
    if hi is not None:
        t["condition_max"] = hi
    return t


def _weight(value, operator="lte", scope="per_pet"):
    return OrderedDict((("value", value), ("unit", "lb"),
                        ("operator", operator), ("scope", scope)))


#: The founder's ten rulings, verbatim in ``ruling``. ``facts`` is what each
#: authorises for publication and ``withheld`` is what it holds back and why.
#: Nothing here is derived from the source a second time -- SCALE-006 read the
#: pages, the founder ruled on the readings, and this applies the rulings.
RULINGS = OrderedDict((
 (HELD, {
   "founder_decision": "HOLD_FOR_IDENTITY_REVIEW",
   "publishes": False, "excludes": False, "withdraw_route": False,
   "ruling": "Do not publish or exclude. The evidence is not strong enough to "
             "determine that the census row and the MainStay Suites Cincinnati "
             "University - Uptown page are the same hotel. Three of four "
             "identity signals disagree: name, ZIP, phone. Only the street "
             "number overlaps, and the page identifies Building B. Keep the "
             "row unresolved until identity is mechanically settled. Do not "
             "withdraw its route.",
 }),
 (RENAME_FROM, {
   "founder_decision": "RENAME_THEN_VERIFIED_NO_PETS",
   "publishes": False, "excludes": True, "withdraw_route": True,
   "ruling": "Rename the census identity to Holiday Inn Express & Suites "
             "Cincinnati SE Newport. Preserve prior identity key, rename "
             "provenance and founder disposition. Do not merge it with "
             "another identity. After the rename, approve the property's "
             "explicit refusal: pets_allowed = false. Register as "
             "VERIFIED_NO_PETS.",
 }),
 ("holiday inn cincinnati airport", {
   "founder_decision": "APPROVE_PARTIAL", "publishes": True,
   "excludes": False, "withdraw_route": True,
   "ruling": "Approve the property's prose as authoritative for the fee "
             "basis: pets_allowed true, pet count 2, weight limit 75 lb, dogs "
             "and cats, $75 per stay. Do NOT publish the structured 'per "
             "night' basis. Preserve the conflicting structured field as "
             "SOURCE_CONTRADICTORY evidence.",
   "facts": OrderedDict((
     ("pets_allowed", True),
     ("pet_fee", OrderedDict(list(_money(7500).items())
                             + [("basis", "per_stay")])),
     ("pet_count_limit", 2),
     ("weight_limit", _weight(75)),
     ("species", {"dogs": "accepted", "cats": "accepted"}))),
   "withheld": {"fee_basis_per_night": (
     "SOURCE_CONTRADICTORY",
     "The structured field states 'Pet fee per night: 75 USD' while the "
     "property's own prose states '75.00 USD per stay'. The founder ruled the "
     "prose authoritative; the nightly reading is preserved here and not "
     "published. Over a seven-night stay the two readings differ by 450 USD.")},
 }),
 ("candlewood suites erlanger south cincinnati", {
   "founder_decision": "APPROVE_PARTIAL", "publishes": True,
   "excludes": False, "withdraw_route": True,
   "ruling": "Approve: pets_allowed true, dogs only, pet count 2, weight "
             "limit 80 lb, fee tier $75 for stays 1-6 nights, fee tier $150 "
             "for stays 7+ nights. Do NOT publish the structured 'Pet fee per "
             "night' interpretation. Use the property's prose tiers.",
   "facts": OrderedDict((
     ("pets_allowed", True),
     ("fee_tiers", [_tier(7500, 1, 6), _tier(15000, 7)]),
     ("pet_count_limit", 2),
     ("weight_limit", _weight(80)),
     ("species", {"dogs": "accepted", "cats": "prohibited"}))),
   "withheld": {"pet_fee": (
     "SOURCE_CONTRADICTORY",
     "The structured field states 'Pet fee per night: 75 USD' while the prose "
     "states 75 USD for one to six nights and 150 USD for seven or more. The "
     "founder ruled the prose tiers authoritative, so no single nightly "
     "headline fee is published.")},
 }),
 ("holiday inn express hotel and suites mason", {
   "founder_decision": "APPROVE_PARTIAL", "publishes": True,
   "excludes": False, "withdraw_route": True,
   "ruling": "Approve: pets_allowed true, pet count 2, dogs and cats, fee "
             "tier $75 for 1-4 nights, fee tier $125 for 5+ nights. Do NOT "
             "publish 'Pet fee per night: 125 USD' or 'Pet damage deposit: 75 "
             "USD'. Preserve those structured readings as contradictory "
             "evidence.",
   "facts": OrderedDict((
     ("pets_allowed", True),
     ("fee_tiers", [_tier(7500, 1, 4), _tier(12500, 5)]),
     ("pet_count_limit", 2),
     ("species", {"dogs": "accepted", "cats": "accepted"}))),
   "withheld": {
     "pet_fee": ("SOURCE_CONTRADICTORY",
                 "The structured field reports 'Pet fee per night: 125 USD', "
                 "which is the 5-or-more-nights tier amount relabelled as a "
                 "nightly rate. The founder ruled the prose tiers "
                 "authoritative."),
     "other_charges": ("SOURCE_CONTRADICTORY",
                       "The structured field also reports 'Pet damage "
                       "deposit: 75 USD', which is the 1-4 night tier amount "
                       "relabelled as a deposit. Both tier amounts are reused "
                       "by the template as different kinds of charge, so "
                       "neither structured reading is published.")},
 }),
 ("candlewood suites cincinnati northeast mason", {
   "founder_decision": "APPROVE_PARTIAL", "publishes": True,
   "excludes": False, "withdraw_route": True,
   "ruling": "Preserve the charges as separate concepts. Approve: "
             "pets_allowed true, dogs only, pet count 2, 50 lb per pet, 75 lb "
             "combined cap. Represent only charge components the existing "
             "schema can express without collapsing meanings. Do NOT collapse "
             "the $75 nonrefundable charge, the $100 cleaning charge and the "
             "$75 damage deposit into one headline pet fee. If any individual "
             "charge cannot be represented safely by the current schema, "
             "withhold that charge and preserve the exact source wording.",
   "facts": OrderedDict((
     ("pets_allowed", True),
     ("fee_tiers", [_tier(7500, 1, 6),
                    _tier(10000, 7, 30, role="ADDITIONAL_CHARGE")]),
     ("pet_count_limit", 2),
     ("weight_limit", _weight(50)),
     ("combined_weight_limit", OrderedDict((("value", 75), ("unit", "lb"),
                                            ("operator", "lte")))),
     ("species", {"dogs": "accepted", "cats": "prohibited"}),
     ("unattended_policy", "Pets must not be left unattended."),
     ("general_restrictions",
      "A pet agreement must be signed at check in. Source wording: '75 USD "
      "nonrefundable fee applies for 1 to 6 nights; stays of 7 to 30 nights "
      "incur an additional 100 USD cleaning fee. Pet damage deposit: 75 USD'."))),
   "withheld": {"other_charges": (
     "SOURCE_AMBIGUOUS",
     "The 75 USD 'Pet damage deposit' comes from the same structured template "
     "field that rulings 5 and 7 rejected on two sibling properties, and it "
     "duplicates the 1-6 night tier amount. The source never states whether it "
     "is refundable, and the schema's deposit kinds would force that choice, "
     "so the charge is withheld and its wording preserved in "
     "general_restrictions rather than published under a refundability this "
     "hotel never stated.")},
 }),
 ("holiday inn express cincinnati west", {
   "founder_decision": "APPROVE_PARTIAL", "publishes": True,
   "excludes": False, "withdraw_route": True,
   "ruling": "Approve: pets_allowed true, pet count 2, dogs and cats, weight "
             "operator LT, weight limit 40 lb, $75 tier for 1-3 nights, $125 "
             "tier for 4-7 nights. DO NOT PUBLISH THE $500 CHARGE. The source "
             "itself creates an unresolved semantic conflict by calling it a "
             "'deposit' and also saying it is nonrefundable. Do not classify "
             "it as either a fee or a deposit until the source or schema can "
             "resolve that contradiction. Also do not publish the duplicate "
             "structured $75 damage-deposit field. Preserve all source "
             "wording in evidence.",
   "facts": OrderedDict((
     ("pets_allowed", True),
     ("fee_tiers", [_tier(7500, 1, 3), _tier(12500, 4, 7)]),
     ("pet_count_limit", 2),
     ("weight_limit", _weight(40, operator="lt")),
     ("species", {"dogs": "accepted", "cats": "accepted"}),
     ("general_restrictions",
      "Source wording, preserved: '1 to 3 nights 75 USD, 4 to 7 nights 125 "
      "USD. 8 plus nights requires a 500 USD deposit. Pet deposit is "
      "nonrefundable. Please contact hotel directly for further information.' "
      "Guests staying eight nights or more should contact the hotel."))),
   "withheld": {"other_charges": (
     "SOURCE_CONTRADICTORY",
     "The 500 USD charge for stays of eight nights or more is called a "
     "'deposit' and then said to be nonrefundable, which the schema cannot "
     "hold as either kind without deciding what the source leaves unresolved. "
     "The separate structured 'Pet damage deposit: 75 USD' duplicates the "
     "first tier amount. Neither is published.")},
 }),
 ("staybridge suites cincinnati north", {
   "founder_decision": "APPROVE_PARTIAL", "publishes": True,
   "excludes": False, "withdraw_route": True,
   "ruling": "Approve: pets_allowed true. WITHHOLD the $50 per-week fee "
             "because the schema cannot represent per_week. Do not divide by "
             "seven. Do not convert it to per-night or per-stay. Preserve "
             "'$50 per week' verbatim in evidence/general restrictions where "
             "supported.",
   "facts": OrderedDict((
     ("pets_allowed", True),
     ("general_restrictions",
      "Source wording, preserved: 'We have a non refundable pet fee of 50 "
      "dollars per week.' A pet agreement must be signed at check in and a "
      "record of complete and up to date vaccinations is required."))),
   "withheld": {"pet_fee": (
     "SCHEMA_CANNOT_REPRESENT",
     "The property states a non-refundable fee of 50 dollars per WEEK. The "
     "schema's fee bases are per_night, per_day and per_stay; there is no "
     "per_week. 50 divided by seven is a number this hotel never stated, so "
     "the amount is withheld and the wording preserved verbatim.")},
 }),
 ("staybridge suites milford", {
   "founder_decision": "APPROVE_PARTIAL", "publishes": True,
   "excludes": False, "withdraw_route": True,
   "ruling": "Same ruling as Staybridge Suites Cincinnati North. Approve: "
             "pets_allowed true. WITHHOLD the $50 per-week fee. Do not "
             "convert the unit. Preserve the exact weekly wording.",
   "facts": OrderedDict((
     ("pets_allowed", True),
     ("general_restrictions",
      "Source wording, preserved: 'We have a nonrefundable pet fee of 50 "
      "dollars per week. Minimum Fee is 50 dollars.' Guests must have a crate "
      "for the animal when leaving the premises, all pets must be up to date "
      "on mandatory vaccinations, and a pet agreement must be signed at check "
      "in."))),
   "withheld": {"pet_fee": (
     "SCHEMA_CANNOT_REPRESENT",
     "The second per-week fee in this market, identical in shape and amount "
     "to Staybridge Suites Cincinnati North. The schema has no per_week basis "
     "and the unit was not converted.")},
 }),
 ("staybridge suites florence", {
   "founder_decision": "APPROVE_PARTIAL", "publishes": True,
   "excludes": False, "withdraw_route": True,
   "ruling": "Approve: pets_allowed true, maximum 1 dog, weight limit 40 lb, "
             "cats prohibited, supported service-animal facts only through "
             "the committed classifier. WITHHOLD pet_fee and fee_tiers. Do "
             "not convert tier boundaries stated in DAYS into nights. Do not "
             "try to repair or infer the garbled third tier.",
   "facts": OrderedDict((
     ("pets_allowed", True),
     ("pet_count_limit", 1),
     ("weight_limit", _weight(40)),
     ("species", {"dogs": "accepted", "cats": "prohibited"}),
     ("general_restrictions",
      "Source wording, preserved: 'Max 1 dog permitted up to 40lbs with a "
      "nonrefundable fee of 75 for stays between 1 to 6 days, 150 between 7 "
      "to 29 days, and 250 of 30 days. Pet Policy must be signed upon "
      "arrival.' Emotional support animals do not qualify."))),
   "withheld": {
     "pet_fee": ("SCHEMA_CANNOT_REPRESENT",
                 "The three tier boundaries are stated in DAYS and the "
                 "schema's tier boundary units are nights or pets. Reading "
                 "days as nights is an inference, not a reading."),
     "fee_tiers": ("SCHEMA_CANNOT_REPRESENT",
                   "Same reason, and the third clause is garbled at source "
                   "('and 250 of 30 days'). The founder ruled against "
                   "repairing or inferring it.")},
 }),
))


# ------------------------------------------------------------------- builders

def _evidence(row: Dict, fields: List[str]) -> List[Dict]:
    """One entry per published field, all citing the same rendered page.

    The artifact digest is the PAGE digest. For Choice the policy-surface
    digest is shared by seven properties in this market, so it cannot carry a
    property-specific claim.
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


def _normalise(facts: Dict) -> Dict:
    """SHAPE only. No value is added, removed or reinterpreted.

    The capture artifacts record a fee as amount + basis + scope; the validator
    also requires an explicit currency, because a bare 2500 is not a price.
    """
    out = OrderedDict()
    for name, value in facts.items():
        if name in ("pet_fee",) and isinstance(value, dict)                 and "currency" not in value:
            value = OrderedDict([("amount_cents", value["amount_cents"]),
                                 ("currency", "USD")]
                                + [(k, v) for k, v in value.items()
                                   if k != "amount_cents"])
        out[name] = value
    return out


def _service_animal(row: Dict) -> Dict:
    """The committed classifier arbitrates, never a plausible human reading.

    PTF-MILWAUKEE-SERVICE-ANIMAL-CORRECTION-011 is why this is not decided
    here, and ruling 4 of APPLICATION-004 is why the classifier is not widened
    to suit a market.
    """
    from scripts.pettripfinder.contracts import service_animal as SA
    quote = row["service_animal_statement"]["quote"]
    return OrderedDict((("stated", True),
                        ("charges_stated", SA.charges_stated(quote)),
                        ("quote", quote)))


def build_record(row: Dict, ruling: Dict = None) -> Dict:
    facts = _normalise(ruling["facts"] if ruling else row["facts"])
    withheld = dict((ruling or {}).get("withheld") or {})

    fields = [k for k in facts if k != "pets_allowed"]
    entries = _evidence(row, ["pets_allowed"] + fields)

    record = OrderedDict((
        ("key", row["identity_key"]),
        ("name", row["page_identity"]["name"] or row["canonical_name"]),
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
        "%s. Founder block authorization of the reconciled 32-row clean block "
        "from PTF-CINCINNATI-FREE-BRAND-PROBE-005 and "
        "PTF-CINCINNATI-FREE-LANE-SCALE-006, applied against THIS record_hash."
        % WORK_ORDER,
        "Observed by attended browser only: provider calls 0, spend $0.00. The "
        "artifact digest is a SHA256 over the page's rendered outerHTML with "
        "the quote taken from the same DOM in the same JavaScript call.",
    ]
    if row.get("identity_disagreements"):
        caveats.append(
            "Identity difference recorded and NOT corrected (%s): %s"
            % (row.get("difference_kind") or "recorded",
               "; ".join(row["identity_disagreements"])))
    if ruling:
        caveats.insert(0, "FOUNDER EXCEPTION RULING (%s): %s"
                       % (ruling["founder_decision"], ruling["ruling"]))
    record["approval"] = OrderedDict((
        ("decision", "APPROVED_AFTER_CURRENT_REVIEW"),
        ("operator", OPERATOR),
        ("approval_date", DECISION_DATE),
        ("caveats", caveats),
        ("record_hash", PM.record_hash(record)),
        ("evidence_hash", PM.evidence_hash(entries)),
    ))
    return record


def build_exclusion(row: Dict, ruling: Dict = None,
                    identity_key: str = None) -> Dict:
    key = identity_key or row["identity_key"]
    page = row["page_identity"]
    note = ("%s: affirmative, property-specific refusal in the property's own "
            "words, captured by attended browser at zero cost. %s"
            % (WORK_ORDER, row.get("notes", "")))
    if ruling:
        note = "FOUNDER RULING (%s): %s | %s" % (
            ruling["founder_decision"], ruling["ruling"], note)
    # canonical_name must be the name the identity key DERIVES from -- the
    # census name, or the renamed one. The page's own name is recorded in the
    # notes instead: the registry keys on census identity, and a page name that
    # does not normalise back to the key fails the exclusion contract.
    canonical = RENAME_TO if key != row["identity_key"] else row["canonical_name"]
    if page["name"] and page["name"] != canonical:
        note = "Property page states the name %r. %s" % (page["name"], note)
    record = OrderedDict((
        ("exclusion_id", "cin-" + key.replace(" ", "-")),
        ("canonical_name", canonical),
        ("normalized_name", key),
        ("address", page.get("street") or ""),
        ("city", page.get("city") or ""),
        ("state", page.get("state") or ""),
        ("postal_code", page.get("postal_code") or ""),
        ("phone", page.get("phone") or ""),
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


# --------------------------------------------------------------------- rename

def rename_census(census):
    """Ruling #2. A rename SUPERSEDES: it never overwrites and never merges."""
    rows = census["hotels"]
    row = next((h for h in rows if h["identity_key"] == RENAME_FROM), None)
    if row is None:
        raise ApplicationError("%s is not in the census" % RENAME_FROM)
    new_key = ptf_identity_key(RENAME_TO)
    if any(h["identity_key"] == new_key for h in rows):
        raise ApplicationError("%r already exists; a rename must never collide"
                               % new_key)
    row["prior_identity_key"] = RENAME_FROM
    row["identity_key"] = new_key
    row["canonical_name"] = RENAME_TO
    row["display_name"] = RENAME_TO
    row["slug"] = new_key.replace(" ", "-")
    row["provenance"] = WORK_ORDER
    row["observed_at"] = OBSERVED_AT
    row["rename"] = OrderedDict((
        ("from_canonical_name", "Holiday Inn Express & Suites Bellevue"),
        ("from_identity_key", RENAME_FROM),
        ("ruled_by", OPERATOR), ("ruled_on", DECISION_DATE),
        ("work_order", WORK_ORDER),
        ("evidence",
         "The property's own page at ihg.com/holidayinnexpress (property code "
         "cvgbv) states 'Holiday Inn Express & Suites Cincinnati SE Newport'. "
         "Street (110 Landmark Drive), postal code (41073) and phone "
         "(859-957-2320) all bind exactly to the census row; only the brand "
         "string moved. Observed attended 2026-08-29 at zero cost."),
        ("not_merged_with", ""),
        ("not_merged_because",
         "No merge was performed. The founder ruled the rename explicitly and "
         "forbade merging this identity with another."),
    ))
    return new_key, row


# ---------------------------------------------------------------------- build

def _free_lane_rows():
    rows = _load(PROBE)["rows"] + _load(SCALE)["rows"]
    keys = [r["identity_key"] for r in rows]
    if len(set(keys)) != len(keys):
        raise ApplicationError("an identity appears in both passes")
    return {r["identity_key"]: r for r in rows}


def build():
    rows = _free_lane_rows()
    if len(rows) != 42:
        raise ApplicationError("free lane is %d rows, expected 42" % len(rows))

    clean_pf = [r for r in rows.values()
                if r["triage"] == "CLEAN_PET_FRIENDLY_CANDIDATE"]
    clean_np = [r for r in rows.values()
                if r["triage"] == "CLEAN_VERIFIED_NO_PETS_CANDIDATE"]
    exceptions = [r for r in rows.values() if r["triage"] == "FOUNDER_EXCEPTION"]
    if len(clean_pf) != 9 or len(clean_np) != 23 or len(exceptions) != 10:
        raise ApplicationError(
            "reconciled block is %d/%d/%d, expected 9/23/10"
            % (len(clean_pf), len(clean_np), len(exceptions)))
    if set(RULINGS) != {r["identity_key"] for r in exceptions}:
        raise ApplicationError("the rulings do not cover the exceptions exactly")

    census = _load(CENSUS)
    new_key, _renamed = rename_census(census)

    package = _load(PACKAGE)
    published = {h["identity_key"] for h in package["hotels"]}

    new_records = [build_record(r) for r in
                   sorted(clean_pf, key=lambda r: r["identity_key"])]
    for key, ruling in RULINGS.items():
        if ruling["publishes"]:
            new_records.append(build_record(rows[key], ruling))

    new_exclusions = [build_exclusion(r) for r in
                      sorted(clean_np, key=lambda r: r["identity_key"])]
    for key, ruling in RULINGS.items():
        if ruling.get("excludes"):
            new_exclusions.append(
                build_exclusion(rows[key], ruling, identity_key=new_key))

    for rec in new_records:
        if rec["identity_key"] in published:
            raise ApplicationError("%s is already published" % rec["identity_key"])
    keys = [r["identity_key"] for r in new_records]
    if len(set(keys)) != len(keys):
        raise ApplicationError("duplicate identity in the applied set")
    ex_keys = [e["normalized_name"] for e in new_exclusions]
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

    # Ruling #1 keeps its route; every identity entering authority loses its.
    withdraw = sorted(set(keys) | set(ex_keys) | {RENAME_FROM})
    withdraw = [k for k in withdraw if k != new_key] + [new_key]
    return package, census, new_records, new_exclusions, withdraw, new_key


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    try:
        package, census, records, exclusions, withdraw, new_key = build()
    except ApplicationError as exc:
        print("REFUSED: %s" % exc)
        return 2

    print("clean pet-friendly applied : 9")
    print("clean verified-no-pets     : 23")
    print("founder rulings applied    : %d of 10 (1 holds, 1 renames+excludes)"
          % sum(1 for r in RULINGS.values()
                if r["publishes"] or r.get("excludes")))
    print("new policy records         : %d" % len(records))
    print("new exclusions             : %d" % len(exclusions))
    print("package total              : %d" % len(package["hotels"]))
    print("routes to withdraw         : %d (%s keeps its route)"
          % (len(withdraw) - 1, HELD))
    print("schema                     : %s" % package["schema_version"])
    if not args.write:
        return 0

    CENSUS.write_text(json.dumps(census, indent=1, ensure_ascii=False) + "\n",
                      encoding="utf-8", newline="\n")
    print("WROTE %s (rename applied)" % CENSUS.name)

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
        ("parent_work_orders", ["PTF-CINCINNATI-FREE-BRAND-PROBE-005",
                                "PTF-CINCINNATI-FREE-LANE-SCALE-006"]),
        ("market_id", MARKET_ID), ("as_of", DECISION_DATE),
        ("operator", OPERATOR),
        ("note", "The founder's ten rulings, verbatim, plus the block "
                 "authorization of the reconciled 32-row clean block. The "
                 "original order carried a stale 5 + 20; Phase 1 showed "
                 "PROBE-005's seven clean rows had never been applied and the "
                 "founder replaced the count with the reconciled figure."),
        ("block_authorization", OrderedDict((
            ("clean_pet_friendly", 9), ("clean_verified_no_pets", 23),
            ("verified_before_application", True),
            ("candidates_removed_from_block", 0),
            ("supersedes_stale_count", "5 + 20"),
        ))),
        ("count", len(RULINGS)),
        ("decision_counts", OrderedDict(sorted(Counter(
            r["founder_decision"] for r in RULINGS.values()).items()))),
        ("rows", [OrderedDict((
            ("identity_key", k),
            ("founder_decision", v["founder_decision"]),
            ("ruling", v["ruling"]),
            ("publishes", v["publishes"]),
            ("excludes", bool(v.get("excludes"))),
            ("route_withdrawn", bool(v.get("withdraw_route"))),
        )) for k, v in RULINGS.items()]),
    ))
    DECISIONS.write_text(json.dumps(decisions, indent=1, ensure_ascii=False)
                         + "\n", encoding="utf-8", newline="\n")
    print("WROTE %s" % DECISIONS.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
