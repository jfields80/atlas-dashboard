"""PTF-CLEVELAND-ATTENDED-PASS-4-001 -- routing-repaired capture integration.

Drives the committed 30-row capture-ready queue produced by
PTF-CLEVELAND-ROUTING-REPAIR-001 and turns the resulting attended captures
into committed, verifiable outputs WITHOUT changing any authority file:

* ``cleveland_pass4_capture_results.json`` -- every one of the 30 rows
  exactly once, with its outcome, artifact hashes recomputed from the bytes
  on disk, mechanical identity binding and quote verification.
* ``cleveland_pass4_founder_review_packet.json`` -- one decision packet per
  positive candidate (Schema 1.2 facts proposed ONLY where the captured page
  states them, each fact carrying its exact quote), per VERIFIED_NO_PETS
  candidate (the refusal sentence, verbatim), and per conversion candidate
  whose policy was captured but whose census identity still carries the
  prior brand's name.

The Hilton rate-limit rule the work order set was honoured: CLE-RR-030
(P3-049, cakapgi) was the session's first navigation and served normally;
Embassy Suites followed after a cool-down, and no other Hilton page was
loaded. Both captured on the first attempt.

Standing extraction rules applied throughout: SOURCE SILENCE IS ABSENCE (no
withholding is created for a fact the page never addresses); generic "pets"
never becomes dogs+cats; refundability, fee basis and fee scope are never
inferred; combined weights never become per-pet; service-animal access is a
separate legal category; payment timing is not a reservation requirement;
"up to"/"not to exceed" is a CEILING and never an exact price; contradictions
are withheld rather than averaged; conditional money belongs in
other_charges or withholding, never in general_restrictions.

Three properties changed brands since the census was built (Days Inn
Richfield -> Quality Inn & Suites Richfield, DoubleTree Westlake -> Wyndham
Garden Westlake, Sonesta ES Suites Westlake -> Sonesta Simply Suites
Westlake). Their policies are captured and identity-verified, but they are
classified POLICY_CAPTURED_PENDING_IDENTITY_RENAME and are NOT proposed for
publication against the old canonical name; the rename is a separate founder
decision. A fourth conversion (Cambria Avon -> Wyndham Avon) states no pet
policy at all, so it is simply POLICY_NOT_FOUND with the conversion noted.

NO authority transition happens here: no facts file edit, no approval, no
exclusion, no partition change, no census change.

Run:  python -m scripts.pettripfinder.cleveland_pass4_capture_integration \
          [--data-root PATH] [--apply]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
from collections import Counter, OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.contracts import enums                            # noqa: E402
from scripts.pettripfinder.contracts import evidence as evidence_contract    # noqa: E402

MARKET = "cleveland-akron-canton-oh"
WORK_ORDER = "PTF-CLEVELAND-ATTENDED-PASS-4-001"
PASS_DATE = "2026-08-16"
AGENT_IDENTITY = "claude-fable-5 (%s, agent)" % WORK_ORDER

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
QUEUE_PATH = LP / "cleveland_routing_repair_001_capture_ready_queue.json"
CENSUS_PATH = LP / "identity_census" / ("%s.json" % MARKET)
RESULTS_PATH = LP / "cleveland_pass4_capture_results.json"
PACKET_PATH = LP / "cleveland_pass4_founder_review_packet.json"

RAW_REL = Path("worker_runs/pettripfinder/cleveland-attended-capture-004/raw")
START_EPOCH_PATH = Path("C:/t/pass4_start_epoch.txt")

OUTCOMES = (
    "AFFIRMATIVE_STRUCTURED", "AFFIRMATIVE_PARTIAL", "NEGATIVE",
    "POLICY_NOT_FOUND", "POLICY_CAPTURED_PENDING_IDENTITY_RENAME",
    "IDENTITY_UNCERTAIN", "ROUTING_PROBLEM", "ACCESS_BLOCKED",
    "CAPTURE_FAILED",
)

#: The Red Roof schedule the founder attested on the Columbus and North
#: Canton properties: the cap belongs to the SECOND pet, never the property.
_RED_ROOF_SCHEDULE = {
    "entries": [
        {"pet_ordinal": 1, "amount_cents": 0, "currency": "USD",
         "additive": False, "basis": "per_stay"},
        {"pet_ordinal": 2, "amount_cents": 1500, "currency": "USD",
         "basis": "per_night", "scope": "per_pet", "additive": True,
         "cap": {"amount_cents": 10500, "currency": "USD",
                 "basis": "per_stay", "scope": "per_pet",
                 "applies_to_pet_ordinal": 2, "trigger_max_nights": 7,
                 "qualifier_stated": True}},
    ]
}
_RED_ROOF_QUOTE = ("Second pet $15/ night, not to exceed 7 nights or $105 "
                   "per pet per stay.")
_HILTON_LADDER = [
    {"amount_cents": 7500, "currency": "USD",
     "condition_type": "stay_length_range", "boundary_unit": "nights",
     "basis_stated": False, "condition_min": 1, "condition_max": 4,
     "role": "REPLACEMENT_PRICE"},
    {"amount_cents": 12500, "currency": "USD",
     "condition_type": "stay_length_range", "boundary_unit": "nights",
     "basis_stated": False, "condition_min": 5,
     "role": "REPLACEMENT_PRICE"},
]
_HILTON_TEMPLATE_NOTE = (
    "the widget's 'Deposit Yes. $75.00 Non-refundable Fee' line is the "
    "Hilton template label; the $75 is tier one of the ladder the 'Other "
    "pet information' line spells out -- the resolution the founder "
    "attested on Hampton Streetsboro and re-attested across Pass 3")


def _c(value: str) -> str:
    return " ".join((value or "").split())


def _digits(value: str) -> str:
    return "".join(ch for ch in (value or "") if ch.isdigit())


def F(field: str, value, quote: str, note: str = "") -> Dict:
    entry = OrderedDict([("field", field), ("value", value), ("quote", quote)])
    if note:
        entry["note"] = note
    return entry


def W(field: str, reason_code: str, reason: str, quote: str) -> Dict:
    return OrderedDict([("field", field), ("reason_code", reason_code),
                        ("reason", reason), ("quote", quote)])


ROWS: "OrderedDict[str, Dict]" = OrderedDict()

# --------------------------------------------------------------------------- #
# A. Hilton (driven first, under the P3-049 rule)
# --------------------------------------------------------------------------- #

ROWS["CLE-RR-030"] = {
    "artifact": "RR-030-hilton-garden-inn-akron-canton-airport.json",
    "outcome": "AFFIRMATIVE_STRUCTURED", "candidate": True,
    "facts": [
        F("pets_allowed", True, "Pets allowed Yes"),
        F("fee_tiers", _HILTON_LADDER, "$75(1-4n) $125(5+)",
          _HILTON_TEMPLATE_NOTE),
        F("weight_limit", {"value": 75, "unit": "lb", "operator": "lte",
                           "scope": "per_pet"},
          "Max weight 75 lbs",
          "widget wording states no scope; per_pet follows the reading "
          "convention the founder reviewed and kept (KEEP_AS_IS, Pass-1 "
          "closeout)"),
        F("pet_count_limit", 2, "2petsMax"),
        F("species", {"dogs": "accepted", "cats": "accepted"}, "dog/cat"),
    ],
    "notes": ["P3-049 re-drive: driven as the session's FIRST navigation per "
              "the work order's Hilton rule; the page served normally and "
              "the Akamai block that ended Pass 3 did not recur."],
}
ROWS["CLE-RR-011"] = {
    "artifact": "RR-011-embassy-suites-akron-canton-airport.json",
    "outcome": "AFFIRMATIVE_STRUCTURED", "candidate": True,
    "facts": [
        F("pets_allowed", True, "Pets allowed Yes"),
        F("fee_tiers", _HILTON_LADDER, "$75 (14 nights), $125 (5+ nights)",
          _HILTON_TEMPLATE_NOTE + ". The page's own tier-one label reads "
          "'(14 nights)' -- a property-entered typo for the 1-4 night band "
          "this brand states everywhere else; quoted verbatim"),
        F("pet_count_limit", 2, "2 pets max"),
        F("species", {"dogs": "accepted", "cats": "accepted"},
          "dogs & cats only"),
    ],
    "notes": ["driven after a 60-second cool-down following CLE-RR-030, per "
              "the work order's Hilton rule; no weight is stated on this "
              "page"],
}

# --------------------------------------------------------------------------- #
# B. Independents
# --------------------------------------------------------------------------- #

ROWS["CLE-RR-004"] = {
    "artifact": "RR-004-inn-at-amish-door.json",
    "outcome": "POLICY_NOT_FOUND", "candidate": False,
    "notes": ["the property's own inn page carries no pet or animal wording; "
              "its only booking link (/TIAADOH884/) 404s on the same site. "
              "Silence, never a refusal."],
}
ROWS["CLE-RR-017"] = {
    "artifact": "RR-017-bertram-inn-at-glenmoor.json",
    "supplementary_artifact": "RR-017b-bertram-glenmoor-hotel-amenities.json",
    "outcome": "POLICY_NOT_FOUND", "candidate": False,
    "notes": ["the lodging page this repair bound (glenmoorcc.com/Hotel) and "
              "its Hotel Amenities subpage both carry no pet or animal "
              "wording."],
}
ROWS["CLE-RR-018"] = {
    "artifact": "RR-018-lakehouse-inn.json",
    "supplementary_artifact": "RR-018b-lakehouse-guest-rooms-policies.json",
    "quote_artifact": "RR-018b-lakehouse-guest-rooms-policies.json",
    "outcome": "NEGATIVE", "candidate": False,
    "refusal_quote": "We are unable to accommodate guest pets.",
    "notes": ["the same policies page states a $500 charge for an "
              "undeclared non-service animal -- a penalty for breaking the "
              "refusal, never a pet fee, and not proposed as one"],
}
ROWS["CLE-RR-007"] = {
    "artifact": "RR-007-cottages-at-the-lodge.json",
    "supplementary_artifact": "RR-007b-lodge-geneva-stay-policies.json",
    "quote_artifact": "RR-007b-lodge-geneva-stay-policies.json",
    "outcome": "NEGATIVE", "candidate": False,
    "refusal_quote": "All guest accommodations at The Lodge at "
                     "Geneva-on-the-Lake, including the Cottages, have a "
                     "no-pet policy.",
    "notes": ["the refusal names the Cottages explicitly, so it binds this "
              "identity rather than only its parent lodge; service animals "
              "are excepted by the same sentence and are a separate legal "
              "category"],
}
ROWS["CLE-RR-013"] = {
    "artifact": "RR-013-highlander-inn.json",
    "supplementary_artifact": "RR-013b-highlander-rooms.json",
    "outcome": "POLICY_NOT_FOUND", "candidate": False,
    "notes": ["the property's new domain (bound by the routing repair) "
              "carries no pet or animal wording on its home or rooms "
              "pages."],
}
ROWS["CLE-RR-014"] = {
    "artifact": "RR-014-intercontinental-suites.json",
    "supplementary_artifact": "RR-014b-intercontinental-suites-faqs.json",
    "outcome": "POLICY_NOT_FOUND", "candidate": False,
    "notes": ["home and FAQs pages carry no pet wording in visible text; the "
              "page's own JSON-LD sets petsAllowed to null, which is the "
              "absence of a statement rather than a refusal."],
}
ROWS["CLE-RR-029"] = {
    "artifact": "RR-029-villa-croatia-croatian-lodge.json",
    "supplementary_artifact": "RR-029b-villa-croatia-faq.json",
    "outcome": "POLICY_NOT_FOUND", "candidate": False,
    "capture_method": "deterministic_fetch",
    "notes": ["home and FAQ pages carry no pet wording. The site presents as "
              "an event venue and its FAQ addresses only events; whether "
              "this identity offers lodging at all is a census question the "
              "routing repair already flagged. Blob downloads are silently "
              "blocked on this origin (as on inncahootsbarandgrill in Pass "
              "3), so the retained artifacts are deterministic fetches of "
              "the same static pages the attended browser rendered."],
}
ROWS["CLE-RR-027"] = {
    "artifact": "RR-027-magnuson-extended-stay-canton.json",
    "outcome": "POLICY_NOT_FOUND", "candidate": False,
    "notes": ["the brand property page bound by the routing repair carries "
              "no pet or animal wording."],
}

# --------------------------------------------------------------------------- #
# C. Red Roof
# --------------------------------------------------------------------------- #

_RR_COMMON = [
    F("pets_allowed", True,
      "One, well-behaved domestic pet (cat or dog) Stays Free!"),
    F("species", {"dogs": "accepted", "cats": "accepted"},
      "domestic pet (cat or dog)"),
    F("pet_count_limit", 2, "Up to 2 pets allowed per room."),
    F("pet_count_scope", "room", "Up to 2 pets allowed per room."),
    F("fee_pet_schedule", _RED_ROOF_SCHEDULE, _RED_ROOF_QUOTE,
      "the shape the founder attested on the Columbus and North Canton Red "
      "Roofs: the cap belongs to the SECOND pet, never to the property"),
    F("weight_limit", {"value": 80, "unit": "lb", "operator": "lte",
                       "scope": "per_pet"},
      "Pet not to exceed 80 pounds."),
    F("reservation_requirement", "Pets must be declared at check-in.",
      "Pets must be declared at check-in."),
    F("service_animal_statement",
      {"stated": True, "charges_stated": "no_charge"},
      "Service and emotional support animals are always welcome.",
      "the ESA half is a legal access category; per the Columbus Red Roof "
      "founder decision it is promoted here and never into "
      "general_restrictions"),
]
_RR_NOTE = ("the page's JSON-LD names Red Roof HQ (7815 Walton Parkway, "
            "43054); the identity binding rests on the visible page, which "
            "carries this property's own street and ZIP")

for _qid, _art in (
        ("CLE-RR-020", "RR-020-red-roof-cleveland-east.json"),
        ("CLE-RR-021", "RR-021-red-roof-independence.json")):
    ROWS[_qid] = {
        "artifact": _art, "outcome": "AFFIRMATIVE_STRUCTURED",
        "candidate": True, "facts": list(_RR_COMMON), "notes": [_RR_NOTE],
    }
ROWS["CLE-RR-022"] = {
    "artifact": "RR-022-red-roof-middleburg-heights.json",
    "outcome": "AFFIRMATIVE_STRUCTURED", "candidate": True,
    "facts": list(_RR_COMMON) + [
        F("unattended_policy",
          "In consideration of all Red Roof guests, pets must never be left "
          "unattended in the guestroom.",
          "In consideration of all Red Roof guests, pets must never be left "
          "unattended in the guestroom."),
        F("general_restrictions",
          "Please keep your animal on a leash when outside your room.",
          "Please keep your animal on a leash when outside your room."),
    ],
    "notes": [_RR_NOTE],
}
ROWS["CLE-RR-023"] = {
    "artifact": "RR-023-red-roof-westlake.json",
    "outcome": "AFFIRMATIVE_STRUCTURED", "candidate": True,
    "facts": list(_RR_COMMON),
    "withheld": [
        W("other_charges", enums.SOURCE_AMBIGUOUS,
          "The page states a $100 refundable deposit required at check-in "
          "'for all guests' -- a property-wide deposit, not a pet deposit. "
          "Recording it under the pet policy would assert a pet charge the "
          "page does not state, so it is withheld with its exact sentence.",
          "A $100 refundable deposit is required at check-in for all "
          "guests."),
    ],
    "notes": [_RR_NOTE],
}

# --------------------------------------------------------------------------- #
# D. Wyndham family
# --------------------------------------------------------------------------- #

ROWS["CLE-RR-001"] = {
    "artifact": "RR-001-wyndham-avon.json",
    "supplementary_artifact": "RR-001b-wyndham-avon-policies.json",
    "outcome": "POLICY_NOT_FOUND", "candidate": False,
    "conversion": {
        "census_name": "Cambria Hotel & Suites Avon",
        "observed_name": "Wyndham Avon",
        "note": "the property converted from Cambria to Wyndham; the census "
                "identity still carries the prior name. No policy was "
                "captured, so no rename decision is forced by this pass -- "
                "the rename remains the routing repair's open proposal.",
    },
    "notes": ["the property page's Hotel Policies block states only check-in "
              "and check-out times; no pet section exists on it. Identity "
              "binds on street and ZIP (35600 Detroit Rd, 44011)."],
}
ROWS["CLE-RR-010"] = {
    "artifact": "RR-010-wyndham-garden-westlake.json",
    "outcome": "POLICY_CAPTURED_PENDING_IDENTITY_RENAME", "candidate": True,
    "conversion": {
        "census_name": "DoubleTree by Hilton Cleveland-Westlake",
        "observed_name": "Wyndham Garden Westlake",
        "note": "hilton.com/clecrdt is a genuine 404; this property now "
                "operates as Wyndham Garden Westlake at the same address. "
                "Identity binds on street, ZIP and phone, but the policy "
                "must NOT publish against the old canonical name.",
    },
    "facts": [
        F("pets_allowed", True, "Dogs only allowed. 2 dogs max per rm."),
        F("species", {"dogs": "accepted"}, "Dogs only allowed."),
        F("pet_count_limit", 2, "2 dogs max per rm."),
        F("pet_fee", {"amount_cents": 5000, "currency": "USD",
                      "basis": "per_stay", "scope": "per_pet"},
          "Fee is 50USD per dog per stay."),
        F("reservation_requirement", "Waiver must be signed at check-in.",
          "Waiver must be signed at check-in."),
        F("general_restrictions",
          "Dog relief area located at the back of the hotel.",
          "Dog relief area located at the back of the hotel."),
    ],
    "withheld": [
        W("other_charges", enums.SOURCE_AMBIGUOUS,
          "The 150 USD sanitation fee is charged only 'at hotel managements "
          "discretion for excessive dirtiness or damage'. "
          "OTHER_CHARGE_KINDS has no sanitation kind and no representation "
          "for a discretionary trigger, and publishing it unconditionally "
          "would assert a charge the page does not state -- the same "
          "treatment the founder ruled for Super 8 Uniontown (D39).",
          "Pet sanitation fee is 150USD and can be charged to a guest at "
          "hotel managements discretion for excessive dirtiness or damage "
          "to hotel property."),
    ],
}
ROWS["CLE-RR-005"] = {
    "artifact": "RR-005-la-quinta-cleveland-airport-north.json",
    "outcome": "AFFIRMATIVE_STRUCTURED", "candidate": True,
    "facts": [
        F("pets_allowed", True,
          "Pets Allowed - 2 pets max. Cats and dogs only. 75lbs or less per "
          "pet."),
        F("pet_count_limit", 2, "2 pets max."),
        F("species", {"dogs": "accepted", "cats": "accepted"},
          "Cats and dogs only."),
        F("weight_limit", {"value": 75, "unit": "lb", "operator": "lte",
                           "scope": "per_pet"},
          "75lbs or less per pet."),
        F("pet_fee", {"amount_cents": 2500, "currency": "USD",
                      "basis": "per_night", "scope": "per_room",
                      "scope_pet_allowance": 2},
          "Fees - Non-refundable 25 USD nightly for up to 2 pets.",
          "the shape the founder attested on La Quinta Independence (D35): "
          "'nightly for up to 2 pets' is the per_room charge with "
          "scope_pet_allowance 2"),
        F("fee_cap", {"amount_cents": 7500, "currency": "USD",
                      "basis": "per_stay", "qualifier_stated": True},
          "Max 75 USD per stay.",
          "canonical top-level fee_cap per founder ruling D35; the cap's "
          "own sentence states per-stay and nothing else, so no scope is "
          "invented"),
        F("service_animal_statement",
          {"stated": True, "charges_stated": "no_charge"},
          "Service Animals - ADA-defined service animals are welcome free "
          "of charge."),
    ],
    "notes": ["MANDATORY identity check performed and passed: the page "
              "carries 4222 W 150 Street, 44135 and 216-251-8500 -- all "
              "three census signals -- and the Airport WEST address (25105 "
              "Country Club Blvd) appears nowhere on it. The Pass-3 "
              "wrong-property redirect did not recur."],
}
ROWS["CLE-RR-026"] = {
    "artifact": "RR-026-travelodge-cleveland-airport.json",
    "outcome": "NEGATIVE", "candidate": False,
    "refusal_quote": "ADA defined service animals are welcome at this hotel. "
                     "Sorry no other pets are allowed.",
    "notes": ["the same Wyndham refusal wording the founder approved for "
              "Travelodge Lakewood and Microtel North Canton in Pass 2"],
}

# --------------------------------------------------------------------------- #
# E. Choice family
# --------------------------------------------------------------------------- #

ROWS["CLE-RR-003"] = {
    "artifact": "RR-003-radisson-akron-fairlawn.json",
    "outcome": "AFFIRMATIVE_STRUCTURED", "candidate": True,
    "facts": [
        F("pets_allowed", True, "Pets Allowed: Yes"),
        F("pet_fee", {"amount_cents": 1000, "currency": "USD",
                      "basis": "per_night", "scope": "per_pet"},
          "Pet Charge 10.00 USD Per Pet, Per Night."),
        F("pet_count_limit", 2, "Pet limit 2 Pet Per Room."),
        F("pet_count_scope", "room", "Pet limit 2 Pet Per Room."),
        F("weight_limit", {"value": 40, "unit": "lb", "operator": "lte",
                           "scope": "per_pet"},
          "Max 40 Pounds.",
          "scope unstated on the page; per_pet follows the reading "
          "convention the founder kept"),
        F("service_animal_statement",
          {"stated": True, "charges_stated": "no_charge"},
          "Service animals are permitted, without charge."),
    ],
    "notes": ["Radisson Americas moved to Choice Hotels; this is the "
              "choicehotels.com oh557 property page the routing repair "
              "bound, and its JSON-LD carries petsAllowed true"],
}
ROWS["CLE-RR-006"] = {
    "artifact": "RR-006-comfort-suites-hartville.json",
    "outcome": "AFFIRMATIVE_STRUCTURED", "candidate": True,
    "facts": [
        F("pets_allowed", True, "Pets Allowed: Yes"),
        F("species", {"dogs": "accepted"}, "Dogs Only."),
        F("pet_fee", {"amount_cents": 4500, "currency": "USD",
                      "basis": "per_night"},
          "45.00 USD per night.",
          "scope (per pet vs per room) unstated -- not invented"),
        F("pet_count_limit", 2, "Pet limit maximum of 2 dogs per room."),
        F("pet_count_scope", "room",
          "Pet limit maximum of 2 dogs per room."),
        F("pet_room_restriction",
          "Dogs permitted in designated pet friendly rooms only.",
          "Dogs permitted in designated pet friendly rooms only."),
        F("service_animal_statement",
          {"stated": True, "charges_stated": "no_charge"},
          "Service animals are permitted, without charge."),
    ],
}
ROWS["CLE-RR-009"] = {
    "artifact": "RR-009-quality-inn-suites-richfield.json",
    "outcome": "POLICY_CAPTURED_PENDING_IDENTITY_RENAME", "candidate": True,
    "conversion": {
        "census_name": "Days Inn Richfield",
        "observed_name": "Quality Inn & Suites Richfield",
        "note": "the property left Wyndham and now operates under Choice as "
                "Quality Inn & Suites Richfield at the same address. "
                "Identity binds on street and ZIP; the page phone "
                "((330) 523-5329) changed with the flag, which is a census "
                "hygiene item. The policy must NOT publish against the old "
                "canonical name.",
    },
    "facts": [
        F("pets_allowed", True, "Pets permitted."),
        F("pet_fee", {"amount_cents": 5000, "currency": "USD",
                      "basis": "per_stay"},
          "50.00 per stay.",
          "scope (per pet vs per room) unstated -- not invented"),
        F("pet_count_limit", 2, "Maximum of two pets per room."),
        F("pet_count_scope", "room", "Maximum of two pets per room."),
        F("weight_limit", {"value": 50, "unit": "lb", "operator": "lte",
                           "scope": "per_pet"},
          "Maximum 50 pounds each.",
          "'each' states per-pet"),
        F("reservation_requirement",
          "Pets must be registered at front desk upon arrival",
          "Pets must be registered at front desk upon arrival"),
        F("pet_room_restriction",
          "stay in Pet Friendly designated rooms",
          "stay in Pet Friendly designated rooms"),
        F("service_animal_statement",
          {"stated": True, "charges_stated": "no_charge"},
          "Service animals are permitted, without charge."),
    ],
}
ROWS["CLE-RR-019"] = {
    "artifact": "RR-019-comfort-suites-twinsburg.json",
    "outcome": "AFFIRMATIVE_STRUCTURED", "candidate": True,
    "facts": [
        F("pets_allowed", True, "Pets Allowed: Yes"),
        F("species", {"dogs": "accepted"}, "Dogs only."),
        F("fee_tiers",
          [{"amount_cents": 2500, "currency": "USD", "basis": "per_night",
            "scope": "per_pet", "basis_stated": True,
            "role": "REPLACEMENT_PRICE",
            "condition_type": "stay_length_range", "condition_min": 1,
            "condition_max": 1, "boundary_unit": "nights"},
           {"amount_cents": 500, "currency": "USD", "basis": "per_night",
            "basis_stated": True, "role": "REPLACEMENT_PRICE",
            "condition_type": "stay_length_range", "condition_min": 2,
            "boundary_unit": "nights"}],
          "Pets Are Allowed: 25.00 USD Per Night, Per Pet for 1st night, "
          "5.00 USD for each additional night during same stay.",
          "a first-night/additional-night ladder, not a stay-length "
          "discount: tier one is the first night at $25 per pet, tier two "
          "is every later night at $5. The page states per-pet scope only "
          "on the first-night rung, so the second rung carries no scope"),
        F("general_restrictions",
          "No pets are allowed in pool area and inside the pool.",
          "No pets are allowed in pool area and inside the pool."),
        F("service_animal_statement",
          {"stated": True, "charges_stated": "no_charge"},
          "Service animals are permitted, without charge."),
    ],
    "notes": ["the page's street reads 2716 Creekside Drive while the census "
              "carries 2715 Creekside Dr; ZIP, phone and property code "
              "bind -- a census address-form observation, not an identity "
              "failure"],
}
ROWS["CLE-RR-028"] = {
    "artifact": "RR-028-quality-inn-arlington-akron-south.json",
    "outcome": "NEGATIVE", "candidate": False,
    "refusal_quote": "Pets Allowed: No General: Only service animals are "
                     "permitted, free of charge.",
    "notes": ["the same Choice refusal wording the founder approved for six "
              "Cleveland properties in Pass 2",
              "the page brands this property 'Quality Inn Akron South' "
              "while the census carries 'Quality Inn Arlington'; street, "
              "ZIP and phone bind -- a census display-name observation"],
}

# --------------------------------------------------------------------------- #
# F. Marriott family
# --------------------------------------------------------------------------- #

ROWS["CLE-RR-016"] = {
    "artifact": "RR-016-springhill-suites-solon.json",
    "outcome": "AFFIRMATIVE_STRUCTURED", "candidate": True,
    "facts": [
        F("pets_allowed", True, "Pet Policy Pets Welcome"),
        F("fee_tiers", _HILTON_LADDER, "$75 (1-4 nights), $125 (5+ nights)",
          "the property's own ladder; the 'Non-Refundable Pet Fee Per "
          "Stay: $75.00' line beside it is tier one of the same ladder "
          "under the established template resolution"),
        F("weight_limit", {"value": 75, "unit": "lb", "operator": "lte",
                           "scope": "per_pet"},
          "Maximum Pet Weight: 75.0lbs",
          "scope unstated; per_pet follows the reading convention"),
        F("pet_count_limit", 2, "Maximum Number of Pets in Room: 2"),
        F("pet_count_scope", "room", "Maximum Number of Pets in Room: 2"),
    ],
}
ROWS["CLE-RR-024"] = {
    "artifact": "RR-024-residence-inn-university-circle.json",
    "outcome": "AFFIRMATIVE_STRUCTURED", "candidate": True,
    "facts": [
        F("pets_allowed", True, "Pet Policy Pets Welcome"),
        F("pet_fee", {"amount_cents": 15000, "currency": "USD",
                      "basis": "per_stay", "scope": "per_room"},
          "1 pet 50 pounds max per room with USD 150 non-refundable fee per "
          "room per stay",
          "the page states both scope and basis in its own words"),
        F("weight_limit", {"value": 50, "unit": "lb", "operator": "lte",
                           "scope": "per_pet"},
          "Maximum Pet Weight: 50.0lbs"),
        F("pet_count_limit", 1, "Maximum Number of Pets in Room: 1"),
        F("pet_count_scope", "room", "Maximum Number of Pets in Room: 1"),
    ],
}
ROWS["CLE-RR-025"] = {
    "artifact": "RR-025-towneplace-suites-solon.json",
    "outcome": "AFFIRMATIVE_STRUCTURED", "candidate": True,
    "facts": [
        F("pets_allowed", True, "Pet Policy Pets Welcome"),
        F("pet_fee", {"amount_cents": 5000, "currency": "USD",
                      "basis": "per_stay"},
          "Pets allowed. Non-refundable fee of $50 per stay.",
          "scope (per pet vs per room) unstated -- not invented"),
        F("pet_count_limit", 1, "Maximum Number of Pets in Room: 1"),
        F("pet_count_scope", "room", "Maximum Number of Pets in Room: 1"),
    ],
}

# --------------------------------------------------------------------------- #
# G. IHG
# --------------------------------------------------------------------------- #

ROWS["CLE-RR-002"] = {
    "artifact": "RR-002-holiday-inn-canton-belden-village.json",
    "outcome": "NEGATIVE", "candidate": False,
    "refusal_quote": "No, pets are not allowed at Holiday Inn Canton "
                     "(Belden Village).",
    "notes": ["the FAQ answer lives in an aria-hidden accordion region; the "
              "quote verifies against the captured HTML, which retains it. "
              "Same IHG shape the founder approved for five Cleveland "
              "properties in Pass 2."],
}
ROWS["CLE-RR-008"] = {
    "artifact": "RR-008-crowne-plaza-cleveland-airport.json",
    "outcome": "AFFIRMATIVE_STRUCTURED", "candidate": True,
    "facts": [
        F("pets_allowed", True,
          "Pets are welcome at Crowne Plaza Cleveland Airport."),
        F("pet_fee", {"amount_cents": 7500, "currency": "USD",
                      "basis": "per_night"},
          "Pet fee per night: 75 USD",
          "scope (per pet vs per room) unstated -- not invented"),
        F("weight_limit", {"value": 30, "unit": "lb", "operator": "lte",
                           "scope": "per_pet"},
          "Pet weight limit: 30",
          "the page states the number with no unit; pounds is the brand's "
          "unit throughout this corpus and the founder may hold this one"),
        F("pet_count_limit", 2, "2 pets allowed"),
        F("species", {"dogs": "accepted", "cats": "accepted"},
          "Pets allowed: Only dogs and cats allowed"),
    ],
    "withheld": [
        W("other_charges", enums.SOURCE_AMBIGUOUS,
          "The page states a 75 USD 'Pet damage deposit' without stating "
          "whether it is refundable; Schema 1.2's other_charges requires an "
          "explicit refundable flag that is never inferred, so the deposit "
          "is withheld rather than published with an invented flag -- the "
          "treatment the founder ruled for Sonesta Cleveland Airport (D06).",
          "Pet damage deposit: 75 USD"),
    ],
    "notes": ["the FAQ answer lives in an aria-hidden accordion region; the "
              "quotes verify against the captured HTML, which retains it"],
}

# --------------------------------------------------------------------------- #
# H. Tail
# --------------------------------------------------------------------------- #

ROWS["CLE-RR-015"] = {
    "artifact": "RR-015-sonesta-simply-suites-westlake.json",
    "supplementary_artifact": "RR-015b-sonesta-westlake-pet-policy.json",
    "quote_artifact": "RR-015b-sonesta-westlake-pet-policy.json",
    "outcome": "POLICY_CAPTURED_PENDING_IDENTITY_RENAME", "candidate": True,
    "conversion": {
        "census_name": "Sonesta ES Suites Cleveland Westlake",
        "observed_name": "Sonesta Simply Suites Cleveland Westlake",
        "note": "the same ES-Suites-to-Simply-Suites rebrand the founder "
                "ruled census-hygiene-only at Cleveland Airport (D06). "
                "Identity binds on street, ZIP and phone. Flagged here "
                "because the work order names this row a conversion "
                "candidate; the founder may rule it hygiene rather than a "
                "rename.",
    },
    "facts": [
        F("pets_allowed", True,
          "Sonesta Simply Suites Cleveland Westlake hotel is dog-friendly "
          "and welcomes well-mannered canine pets."),
        F("species", {"dogs": "accepted"},
          "dog-friendly and welcomes well-mannered canine pets",
          "the page speaks only of dogs; nothing is claimed for cats -- "
          "unlike its Cleveland Airport sibling, which says 'pets'"),
        F("pet_count_limit", 2, "Up to two pets are permitted per suite"),
        F("pet_count_scope", "suite",
          "Up to two pets are permitted per suite"),
        F("weight_limit", {"value": 60, "unit": "lb", "operator": "lte",
                           "scope": "per_pet"},
          "weighing up to 60 lbs each", "'each' states per-pet"),
        F("pet_fee", {"amount_cents": 500, "currency": "USD",
                      "basis": "per_night", "scope": "per_pet"},
          "A $5 fee applies per pet, per night"),
    ],
    "withheld": [
        W("other_charges", enums.SCHEMA_CANNOT_REPRESENT,
          "The page states a $50 deposit without stating whether it is "
          "refundable; other_charges requires an explicit refundable flag "
          "that is never inferred (founder D06).",
          "with a $50 deposit"),
    ],
}
ROWS["CLE-RR-012"] = {
    "artifact": "RR-012-esa-premier-suites-independence.json",
    "supplementary_artifact": "RR-012b-esa-independence-faq.json",
    "outcome": "AFFIRMATIVE_STRUCTURED", "candidate": True,
    "facts": [
        F("pets_allowed", True,
          "A maximum of two pets are allowed in each suite."),
        F("pet_count_limit", 2,
          "A maximum of two pets are allowed in each suite."),
        F("pet_count_scope", "suite",
          "A maximum of two pets are allowed in each suite."),
        F("general_restrictions",
          "Height and length restrictions apply-- pets can be no longer "
          "than 36 inches and no taller than 36 inches.",
          "Height and length restrictions apply-- pets can be no longer "
          "than 36 inches and no taller than 36 inches."),
        F("dimension_constraints",
          [{"axis": "length", "value": 36, "unit": "in", "operator": "lte"},
           {"axis": "height", "value": 36, "unit": "in", "operator": "lte"}],
          "pets can be no longer than 36 inches and no taller than 36 "
          "inches"),
    ],
    "withheld": [
        W("cleaning_fee", enums.SCHEMA_CANNOT_REPRESENT,
          "Both rungs of the property's schedule are ceilings ('up to a $25 "
          "(+ tax)' for nights one through six, 'not to exceed $15' "
          "thereafter). CEILING != PRICE (founder ruling D09, which also "
          "remediated the published ESA Akron South record): Schema 1.2 "
          "tiers carry exact prices and no ceiling qualifier, so no rung "
          "publishes as a charge and both exact sentences are retained.",
          "There will be up to a $25 (+ tax) per day non-refundable "
          "cleaning fee for the first six (6) nights, per pet.",
          ),
    ],
    "extra_withheld_quotes": {
        "cleaning_fee": ["Each day thereafter there is a pet cleaning fee "
                         "not to exceed $15 non-refundable fee (+tax) per "
                         "day, per pet."],
    },
    "notes": ["the brand-standard block lives in the page HTML rather than "
              "its visible text; quotes verify against the captured HTML"],
}


# --------------------------------------------------------------------------- #
# Verification helpers.
# --------------------------------------------------------------------------- #

def load_json(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_lf(path: Path, document) -> bytes:
    payload = (json.dumps(document, indent=2, ensure_ascii=False) + "\n") \
        .encode("utf-8")
    path.write_bytes(payload)
    return payload


def sha_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def verify_capture(doc: Dict) -> Dict:
    return {
        "html_sha256": sha_text(doc.get("html", "")),
        "text_sha256": sha_text(doc.get("text", "")),
        "html_agrees": sha_text(doc.get("html", "")) == doc.get("html_sha256"),
        "text_agrees": sha_text(doc.get("text", "")) == doc.get("text_sha256"),
    }


def quote_backed(quote: str, doc: Dict) -> str:
    if evidence_contract.quote_is_contiguous(quote, doc.get("text", "")):
        return "text"
    if evidence_contract.quote_is_contiguous(quote, doc.get("html", "")):
        return "html"
    return "MISSING"


def identity_binding(row: Dict, doc: Dict) -> Dict:
    hay = " ".join((_c(doc.get("text", "")),
                    _c(" ".join(doc.get("jsonld") or [])),
                    _c(doc.get("html", ""))))
    phone = _digits(row.get("phone", ""))[-10:]
    street_no = (row.get("address", "").strip().split(" ", 1) or [""])[0]
    zip5 = _digits(row.get("postal_code", ""))[:5]
    hay_digits = _digits(hay)
    signals = OrderedDict([
        ("phone", bool(phone) and phone in hay_digits),
        ("street_number", bool(street_no) and street_no.isdigit()
         and street_no in hay),
        ("zip", bool(zip5) and zip5 in hay),
    ])
    signals["bound"] = sum(1 for key in ("phone", "street_number", "zip")
                           if signals[key]) >= 2
    return signals


def speed_benchmark(stamps_iso: List[str]) -> Dict:
    start_epoch = int(START_EPOCH_PATH.read_text().strip()) \
        if START_EPOCH_PATH.is_file() else None
    stamps = sorted(
        datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
        for ts in stamps_iso if ts)
    if not stamps:
        return {"available": False}
    gaps = [b - a for a, b in zip(stamps, stamps[1:])]
    first, last = stamps[0], stamps[-1]
    elapsed = (last - start_epoch) if start_epoch else (last - first)
    return OrderedDict([
        ("available", True),
        ("start_epoch", start_epoch),
        ("first_capture_utc",
         datetime.fromtimestamp(first, timezone.utc).isoformat()),
        ("last_capture_utc",
         datetime.fromtimestamp(last, timezone.utc).isoformat()),
        ("session_elapsed_seconds", round(elapsed)),
        ("captures", len(stamps)),
        ("mean_seconds_per_capture", round(elapsed / len(stamps), 1)),
        ("median_inter_capture_gap_seconds",
         round(statistics.median(gaps), 1) if gaps else None),
        ("captures_per_hour", round(len(stamps) / (elapsed / 3600.0), 1)),
        ("note", "elapsed runs from the recorded session start epoch to the "
                 "last capture and includes the mandated Hilton cool-down "
                 "and the adjudication work between captures; the median "
                 "inter-capture gap is the honest page-drive pace."),
    ])


# --------------------------------------------------------------------------- #
# Assembly.
# --------------------------------------------------------------------------- #

def run(data_root: Path, apply: bool) -> Dict:
    raw_dir = data_root / RAW_REL
    queue = load_json(QUEUE_PATH)
    queue_rows = {r["queue_id"]: r for r in queue["rows"]}
    if len(queue_rows) != 30:
        raise SystemExit("STOP: queue does not carry 30 rows")
    if set(queue_rows) != set(ROWS):
        raise SystemExit("STOP: adjudication table does not cover the queue "
                         "exactly once: missing=%s extra=%s"
                         % (sorted(set(queue_rows) - set(ROWS)),
                            sorted(set(ROWS) - set(queue_rows))))
    census = {h["identity_key"]: h for h in load_json(CENSUS_PATH)["hotels"]}

    results: List[Dict] = []
    positives: List[Dict] = []
    negatives: List[Dict] = []
    renames: List[Dict] = []
    counts: Counter = Counter()
    stamps: List[str] = []

    for qid in sorted(ROWS):
        spec = ROWS[qid]
        queue_row = queue_rows[qid]
        outcome = spec["outcome"]
        if outcome not in OUTCOMES:
            raise SystemExit("STOP %s: %r is not an outcome class"
                             % (qid, outcome))
        counts[outcome] += 1

        path = raw_dir / spec["artifact"]
        doc = load_json(path)
        integrity = verify_capture(doc)
        if not (integrity["html_agrees"] and integrity["text_agrees"]):
            raise AssertionError("%s: capture integrity failure" % qid)
        binding = identity_binding(queue_row, doc)
        method = spec.get("capture_method",
                          doc.get("capture_method", "attended_browser"))
        stamps.append(doc.get("captured_at"))

        row = OrderedDict([
            ("queue_id", qid),
            ("hotel", queue_row["name"]),
            ("identity_key", queue_row["identity_key"]),
            ("brand", queue_row["brand"]),
            ("outcome", outcome),
            ("artifact_file", spec["artifact"]),
            ("artifact_bytes", path.stat().st_size),
            ("artifact_file_sha256",
             hashlib.sha256(path.read_bytes()).hexdigest()),
            ("html_sha256", integrity["html_sha256"]),
            ("text_sha256", integrity["text_sha256"]),
            ("content_hashes_agree", True),
            ("captured_at", doc.get("captured_at")),
            ("capture_method", method),
            ("requested_url", queue_row["official_url"]),
            ("final_url", doc.get("final_url")),
            ("identity_binding", binding),
        ])
        if spec.get("supplementary_artifact"):
            sup_path = raw_dir / spec["supplementary_artifact"]
            sup_doc = load_json(sup_path)
            sup_integrity = verify_capture(sup_doc)
            if not (sup_integrity["html_agrees"]
                    and sup_integrity["text_agrees"]):
                raise AssertionError("%s: supplementary integrity failure"
                                     % qid)
            stamps.append(sup_doc.get("captured_at"))
            row["supplementary_artifact"] = OrderedDict([
                ("artifact_file", spec["supplementary_artifact"]),
                ("artifact_file_sha256",
                 hashlib.sha256(sup_path.read_bytes()).hexdigest()),
                ("html_sha256", sup_integrity["html_sha256"]),
                ("final_url", sup_doc.get("final_url")),
            ])

        quote_doc = doc
        if spec.get("quote_artifact"):
            quote_doc = load_json(raw_dir / spec["quote_artifact"])
        quote_sha = "sha256:%s" % verify_capture(quote_doc)["html_sha256"]

        if outcome == "NEGATIVE":
            where = quote_backed(spec["refusal_quote"], quote_doc)
            if where == "MISSING":
                raise AssertionError("%s: refusal quote not in capture" % qid)
            row["refusal_quote"] = spec["refusal_quote"]
            row["quote_backed_by"] = where
            negatives.append(OrderedDict([
                ("decision_id", "P4N-%02d" % (len(negatives) + 1)),
                ("queue_id", qid),
                ("hotel", queue_row["name"]),
                ("identity_key", queue_row["identity_key"]),
                ("current_canonical_name",
                 census[queue_row["identity_key"]]["canonical_name"]),
                ("observed_property_name", doc.get("title", "")[:120]),
                ("url", queue_row["official_url"]),
                ("final_url", quote_doc.get("final_url")),
                ("identity_binding", binding),
                ("artifact_file", spec.get("quote_artifact")
                 or spec["artifact"]),
                ("artifact_sha256", quote_sha),
                ("artifact_kind", enums.ARTIFACT_RENDERED_HTML),
                ("captured_at", quote_doc.get("captured_at")),
                ("capture_method", method),
                ("source_grade", enums.GRADE_PT1_FIRST_PARTY),
                ("proposed_state", "VERIFIED_NO_PETS"),
                ("refusal_quote", spec["refusal_quote"]),
                ("notes", spec.get("notes", [])),
                ("recommended_founder_decision", "APPROVE_VERIFIED_NO_PETS"),
            ]))

        if spec.get("candidate"):
            checked = []
            for fact in spec.get("facts", []):
                where = quote_backed(fact["quote"], quote_doc)
                if where == "MISSING" and quote_doc is not doc:
                    where = quote_backed(fact["quote"], doc)
                if where == "MISSING":
                    raise AssertionError("%s: quote %r not carried by the "
                                         "capture" % (qid, fact["quote"][:60]))
                fact = OrderedDict(fact)
                fact["quote_backed_by"] = where
                checked.append(fact)
            withheld = []
            for w in spec.get("withheld", []):
                quotes = [w["quote"]] + list(
                    spec.get("extra_withheld_quotes", {}).get(w["field"], []))
                for quote in quotes:
                    where = quote_backed(quote, quote_doc)
                    if where == "MISSING" and quote_doc is not doc:
                        where = quote_backed(quote, doc)
                    if where == "MISSING":
                        raise AssertionError(
                            "%s: withheld quote %r not carried by the "
                            "capture" % (qid, quote[:60]))
                entry = OrderedDict(w)
                if len(quotes) > 1:
                    entry["additional_quotes"] = quotes[1:]
                withheld.append(entry)

            rename = spec.get("conversion")
            packet_row = OrderedDict([
                ("decision_id", "%s-%02d" % (
                    "P4R" if rename and outcome ==
                    "POLICY_CAPTURED_PENDING_IDENTITY_RENAME" else "P4P",
                    (len(renames) if rename and outcome ==
                     "POLICY_CAPTURED_PENDING_IDENTITY_RENAME"
                     else len(positives)) + 1)),
                ("queue_id", qid),
                ("hotel", queue_row["name"]),
                ("identity_key", queue_row["identity_key"]),
                ("current_canonical_name",
                 census[queue_row["identity_key"]]["canonical_name"]),
                ("observed_property_name",
                 (rename or {}).get("observed_name") or doc.get("title", "")[:120]),
                ("outcome", outcome),
                ("url", queue_row["official_url"]),
                ("final_url", (quote_doc or doc).get("final_url")),
                ("identity_binding", binding),
                ("artifact_file", spec.get("quote_artifact")
                 or spec["artifact"]),
                ("artifact_sha256", quote_sha),
                ("artifact_kind", enums.ARTIFACT_RENDERED_HTML),
                ("captured_at", (quote_doc or doc).get("captured_at")),
                ("capture_method", method),
                ("source_grade", enums.GRADE_PT1_FIRST_PARTY),
                ("proposed_facts", checked),
                ("proposed_withheld", withheld),
                ("conversion_note", rename or None),
                ("notes", spec.get("notes", [])),
                ("recommended_founder_decision",
                 "APPROVE_RENAME_THEN_PUBLISH" if outcome ==
                 "POLICY_CAPTURED_PENDING_IDENTITY_RENAME"
                 else "APPROVE_PUBLICATION"),
            ])
            if outcome == "POLICY_CAPTURED_PENDING_IDENTITY_RENAME":
                renames.append(packet_row)
            else:
                positives.append(packet_row)

        if spec.get("conversion") and not spec.get("candidate"):
            row["conversion_note"] = spec["conversion"]
        if spec.get("notes"):
            row["notes"] = spec["notes"]
        results.append(row)

    bench = speed_benchmark(stamps)

    ledger = OrderedDict([
        ("schema", "ptf-cleveland-pass4-capture-results/1.0"),
        ("work_order", WORK_ORDER),
        ("as_of", PASS_DATE),
        ("market_id", MARKET),
        ("captured_by", AGENT_IDENTITY),
        ("queue_source", QUEUE_PATH.name),
        ("capture_method",
         "attended browser (operator's Chrome, extension-driven); rendered "
         "HTML and page text retained as bytes in the gitignored worker "
         "tree at data/%s; committed output is hashes and verdicts only, "
         "because captured brand pages embed third-party credentials and "
         "are never committed. Two artifacts are deterministic fetches "
         "(croatianlodge.com silently blocks blob downloads); their rows "
         "say so." % RAW_REL.as_posix()),
        ("hilton_rate_limit_rule",
         "CLE-RR-030 (P3-049, cakapgi) was the session's FIRST navigation "
         "and served normally; Embassy Suites (caknaes) followed after a "
         "cool-down; no other hilton.com page was loaded. Neither row was "
         "re-probed, and no block page was recorded as evidence."),
        ("rows_total", 30),
        ("rows_captured", len(results)),
        ("outcome_counts", OrderedDict(sorted(counts.items()))),
        ("speed_benchmark", bench),
        ("rule",
         "A failed, blocked or misrouted capture is never negative "
         "evidence; a refusal is proposed only where the property's own "
         "page states it; no fact is proposed without its exact quote "
         "verified against the retained artifact bytes; source silence is "
         "absence, never a withholding; no authority file changes in this "
         "pass."),
        ("results", results),
    ])

    packet = OrderedDict([
        ("schema", "ptf-cleveland-pass4-founder-review-packet/1.0"),
        ("work_order", WORK_ORDER),
        ("as_of", PASS_DATE),
        ("prepared_by", AGENT_IDENTITY),
        ("status", "AWAITING_FOUNDER_DECISION"),
        ("rule",
         "Nothing here is published and no authority file moved. Every "
         "proposed fact carries the exact first-party quote that supports "
         "it, verified contiguous in the hash-bound artifact named beside "
         "it; withholding is proposed only where the source contradicts or "
         "garbles itself, states a ceiling rather than a price, or states "
         "something the schema cannot represent -- never for silence. "
         "Conversion candidates carry a captured policy AND a census "
         "identity that still names the prior brand; approving them "
         "authorizes the rename first and the publication second."),
        ("decision_totals", OrderedDict([
            ("positive_candidates", len(positives)),
            ("rename_candidates", len(renames)),
            ("negative_candidates", len(negatives)),
            ("total_founder_decisions",
             len(positives) + len(renames) + len(negatives)),
        ])),
        ("positive_candidates", positives),
        ("rename_candidates", renames),
        ("negative_candidates", negatives),
        ("hyatt_operator_manual_instructions",
         queue.get("operator_manual_only", [])),
        ("remaining_manual_work",
         "The three Hyatt identities remain ADR-forbidden for automation "
         "and were NOT driven; their operator-manual instructions are "
         "restated above unchanged. Best Western Plus North Canton remains "
         "ROUTING_HELD (its brand endpoint refuses to serve the property "
         "page), and ten small motels plus the Clarion Hudson remain "
         "without any first-party URL."),
    ])

    if apply:
        write_lf(RESULTS_PATH, ledger)
        write_lf(PACKET_PATH, packet)
    return ledger


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path,
                        default=Path("C:/Atlas/atlas-dashboard/data"))
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    ledger = run(args.data_root, args.apply)
    print("rows: %d | captured: %d" % (ledger["rows_total"],
                                       ledger["rows_captured"]))
    for name, count in ledger["outcome_counts"].items():
        print("  %-42s %d" % (name, count))
    bench = ledger["speed_benchmark"]
    if bench.get("available"):
        print("benchmark: %ss elapsed, %s captures, median gap %ss, %s/hour"
              % (bench["session_elapsed_seconds"], bench["captures"],
                 bench["median_inter_capture_gap_seconds"],
                 bench["captures_per_hour"]))
    if not args.apply:
        print("dry run: nothing written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
