"""PTF-CLEVELAND-LIGHT-RECERTIFICATION-001 Pass 2 -- attended-capture integration.

Turns the cleveland-attended-capture-002 worker-tree captures into committed,
verifiable outputs WITHOUT publishing anything:

* ``cleveland_pass2_capture_results.json`` -- every one of the 49 queue rows
  exactly once, with its outcome, artifact hashes recomputed from the bytes on
  disk, mechanical identity binding, and quote verification.
* ``cleveland_pass2_founder_review_packet.json`` -- the decision packets: one
  per positive publication candidate (canonical facts proposed ONLY where the
  captured page states them, each fact carrying its exact quote), one per
  VERIFIED_NO_PETS candidate (the refusal sentence, verbatim), and the two
  Drury artifact re-attestation deltas.
* The ONLY authority change applied here is the Drury artifact upgrade the
  work order names: entry-level publication-grade bindings citing the byte-
  retained Pass-2 captures. Facts and quotes are untouched; record_hash moves,
  so both founder approvals are downgraded to pending-operator with the prior
  approval preserved verbatim -- the established rule. No approval is written
  under any operator's name.

Every proposed fact is loader-asserted: its quote must appear (whitespace-
collapsed) in the captured page text or, where a surface renders its policy
from an embedded data payload (Drury), in the captured page HTML. A quote that
fails the assertion aborts the run rather than shipping a claim the artifact
does not carry.

The three Hyatt rows are not captured and not guessed at: Hyatt automation is
ADR-forbidden (Kasada; PTF-COLUMBUS-UNRESOLVED-CAPTURE-003), so those rows are
classified for the operator-manual screenshot route.

Run:  python -m scripts.pettripfinder.cleveland_pass2_capture_integration \
          [--data-root PATH] [--apply]
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.contracts import enums                            # noqa: E402
from scripts.pettripfinder.contracts import evidence as evidence_contract    # noqa: E402
from scripts.pettripfinder.policy_migration import (                         # noqa: E402
    evidence_hash, evidence_ref_for, record_hash,
)

MARKET = "cleveland-akron-canton-oh"
WORK_ORDER = "PTF-CLEVELAND-LIGHT-RECERTIFICATION-001-PASS2"
PASS_DATE = "2026-08-15"
AGENT_IDENTITY = "claude-fable-5 (%s, agent)" % WORK_ORDER

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
FACTS_PATH = LP / ("hotel_policy_facts_%s.json" % MARKET)
CONTRACT_PATH = (_REPO_ROOT / "deploy" / "netlify" / "release_contracts"
                 / ("%s.json" % MARKET))
RESULTS_PATH = LP / "cleveland_pass2_capture_results.json"
PACKET_PATH = LP / "cleveland_pass2_founder_review_packet.json"

RAW_REL = Path("worker_runs/pettripfinder/cleveland-attended-capture-002/raw")
QUEUE_CSV_REL = Path("operator_evidence/cleveland-attended-artifact-002"
                     "/cleveland-attended-artifact-queue.csv")

HYATT_NOTE = ("HYATT_ADR_FORBIDDEN: Hyatt's anti-automation terms forbid "
              "driving its pages (Kasada); the lawful route is an operator-"
              "manual screenshot session, as used for Columbus Hyatt.")


def _c(value: str) -> str:
    return " ".join((value or "").split())


def _digits(value: str) -> str:
    return "".join(ch for ch in (value or "") if ch.isdigit())


# --------------------------------------------------------------------------- #
# Adjudication table. Facts are proposed ONLY where the page states them; the
# quote beside each value is asserted against the captured artifact.
# ``None`` outcome fields never propose facts.
# --------------------------------------------------------------------------- #

def F(field: str, value, quote: str, note: str = "") -> Dict:
    entry = OrderedDict([("field", field), ("value", value), ("quote", quote)])
    if note:
        entry["note"] = note
    return entry


ROWS: "OrderedDict[str, Dict]" = OrderedDict()

# ---- GROUP A: structured-positive ---------------------------------------- #
ROWS["CLE-AAQ-001-A01"] = {
    "artifact": "A01-comfort-inn-alliance.json",
    "outcome": "AFFIRMATIVE_STRUCTURED",
    "candidate": True,
    "facts": [
        F("pets_allowed", True, "Pets Allowed: Yes"),
        F("pet_fee", {"amount_cents": 5000, "currency": "USD",
                      "basis": "per_night", "scope": "per_pet"},
          "Pet charge is 50 USD per night per pet"),
        F("weight_limit", {"value": 40, "unit": "lb", "operator": "lte",
                           "scope": "per_pet"},
          "A maximum of 40 pounds per pet", "per-pet stated in words"),
        F("pet_count_limit", 2, "a maximum of 2 pets per room"),
        F("pet_count_scope", "room", "a maximum of 2 pets per room"),
        F("service_animal_statement",
          {"stated": True, "charges_stated": "no_charge"},
          "Service animals are permitted, without charge."),
    ],
    "notes": ["page JSON-LD street reads 2222 Quality Dr. while the census "
              "carries 2500 W. State St.; phone, ZIP and name bind -- census "
              "address forms to review, not an identity failure"],
}
ROWS["CLE-AAQ-001-A02"] = {
    "artifact": "A02-comfort-inn-canton.json",
    "outcome": "AFFIRMATIVE_STRUCTURED",
    "candidate": True,
    "facts": [
        F("pets_allowed", True, "Pets Allowed: Yes"),
        F("pet_fee", {"amount_cents": 2500, "currency": "USD",
                      "basis": "per_night", "scope": "per_pet"},
          "25.00 USD Per Pet per night"),
        F("pet_deposit", {"amount_cents": 10000, "currency": "USD",
                          "refundable": True},
          "100.00 USD refundable deposit required",
          "the property's own word is 'refundable'; this is a true deposit, "
          "not the Hilton-template label conflict"),
        F("weight_limit", {"value": 30, "unit": "lb", "operator": "lte",
                           "scope": "per_pet"},
          "A maximum of 30 pounds per Pet", "per-pet stated in words"),
        F("pet_count_limit", 2, "2 Pets per room"),
        F("pet_count_scope", "room", "2 Pets per room"),
        F("service_animal_statement",
          {"stated": True, "charges_stated": "no_charge"},
          "Service animals are permitted, without charge."),
        F("general_restrictions",
          "A 200.00 USD penalty for pets that are not declared and properly "
          "registered upon arrival at check in.",
          "A 200.00 USD penalty for pets that are not declared and properly "
          "registered upon arrival at check in."),
    ],
    "notes": ["page displays the property as 'Comfort Inn - Hall of Fame'; "
              "street 5345 Broadmoor Circle NW, ZIP and phone bind the "
              "identity -- display-name observation for census hygiene"],
}
ROWS["CLE-AAQ-001-A03"] = {
    "artifact": "A03-econo-lodge-akron-copley-northwest.json",
    "outcome": "AFFIRMATIVE_STRUCTURED",
    "candidate": True,
    "facts": [
        F("pets_allowed", True, "Pets Allowed: Yes"),
        F("pet_fee", {"amount_cents": 1000, "currency": "USD",
                      "basis": "per_night"},
          "There is a 10 USD charge per night",
          "scope deliberately unstated -- the page does not say per pet or "
          "per room"),
        F("weight_limit", {"value": 50, "unit": "lb", "operator": "lte",
                           "scope": "per_pet"},
          "pets must be 50 lbs or less",
          "each-pet reading of 'pets must be'; convention, founder may hold"),
        F("service_animal_statement",
          {"stated": True, "charges_stated": "no_charge"},
          "Service animals are permitted, without charge."),
    ],
}
ROWS["CLE-AAQ-001-A04"] = {
    "artifact": None, "outcome": "ACCESS_BLOCKED", "candidate": False,
    "notes": [HYATT_NOTE],
}
ROWS["CLE-AAQ-001-A05"] = {
    "artifact": None, "outcome": "ACCESS_BLOCKED", "candidate": False,
    "notes": [HYATT_NOTE],
}
ROWS["CLE-AAQ-001-A06"] = {
    "artifact": "A06-courtyard-akron-downtown.json",
    "outcome": "AFFIRMATIVE_STRUCTURED",
    "candidate": True,
    "facts": [
        F("pets_allowed", True, "Pets Welcome"),
        F("species", {"dogs": "accepted"}, "Dogs only."),
        F("weight_limit", {"value": 40, "unit": "lb", "operator": "lte",
                           "scope": "per_pet"},
          "Each pet may weigh up to 40.0 lbs",
          "the FAQ states per-pet and inclusive; the prose 'Must be under 40 "
          "lbs' reads exclusive -- founder decides lte vs lt; lte follows the "
          "structured field, and the packet flags the tension"),
        F("pet_count_limit", 2, "Max of 2 dogs per room."),
        F("pet_count_scope", "room", "Max of 2 dogs per room."),
    ],
    "notes": ["'Pet Fee applies' with NO amount anywhere on the page -- fee "
              "is proposed as ABSENT (schema cannot carry an amountless fee); "
              "renderer will state no fee figure"],
}
ROWS["CLE-AAQ-001-A07"] = {
    "artifact": "A07-residence-inn-akron-south-green.json",
    "outcome": "AFFIRMATIVE_STRUCTURED",
    "candidate": True,
    "facts": [
        F("pets_allowed", True, "Pets Welcome"),
        F("pet_fee", {"amount_cents": 10000, "currency": "USD",
                      "basis": "per_stay"},
          "Non-Refundable Pet Fee Per Stay: $100.00",
          "the prose calls the same $100 a 'non-refundable deposit'; a "
          "non-refundable deposit is a fee (house rule), no deposit proposed"),
        F("weight_limit", {"value": 25, "unit": "lb", "operator": "lte",
                           "scope": "per_pet"},
          "Each pet may weigh up to 25.0 lbs"),
        F("pet_count_limit", 2, "Maximum Number of Pets in Room: 2"),
        F("pet_count_scope", "room", "Maximum Number of Pets in Room: 2"),
    ],
}
ROWS["CLE-AAQ-001-A08"] = {
    "artifact": "A08-aloft-beachwood.json",
    "outcome": "AFFIRMATIVE_STRUCTURED",
    "candidate": True,
    "facts": [
        F("pets_allowed", True, "Pets Welcome"),
        F("species", {"dogs": "accepted", "cats": "prohibited"},
          "Dogs only- no cats, no birds, no reptiles.",
          "cats named and refused -- explicit prohibition"),
        F("weight_limit", {"value": 60, "unit": "lb", "operator": "lte",
                           "scope": "per_pet"},
          "Each pet may weigh up to 60.0 lbs"),
        F("pet_count_limit", 2, "Maximum Number of Pets in Room: 2"),
        F("pet_count_scope", "room", "Maximum Number of Pets in Room: 2"),
    ],
    "notes": ["no fee stated anywhere -- silence, nothing proposed"],
}
ROWS["CLE-AAQ-001-A09"] = {
    "artifact": "A09-courtyard-canton.json",
    "outcome": "AFFIRMATIVE_STRUCTURED",
    "candidate": True,
    "facts": [
        F("pets_allowed", True, "Pets Welcome"),
        F("pet_fee", {"amount_cents": 7500, "currency": "USD"},
          "75.00 pet fee",
          "basis and scope unstated on the page -- neither is invented"),
        F("unattended_policy", "pets can not be left unattended",
          "pets can not be left unattended"),
        F("pet_room_restriction", "not allowed in public areas",
          "not allowed in public areas"),
        F("pet_count_limit", 2, "Maximum Number of Pets in Room: 2"),
        F("pet_count_scope", "room", "Maximum Number of Pets in Room: 2"),
    ],
}
ROWS["CLE-AAQ-001-A10"] = {
    "artifact": "A10-residence-inn-canton.json",
    "outcome": "AFFIRMATIVE_STRUCTURED",
    "candidate": True,
    "facts": [
        F("pets_allowed", True, "Pets Welcome"),
        F("species", {"dogs": "accepted"}, "Dogs are allowed"),
        F("pet_fee", {"amount_cents": 7500, "currency": "USD",
                      "basis": "per_stay", "scope": "per_room"},
          "non-refundable fee of USD 75 per room per stay"),
        F("weight_limit", {"value": 50, "unit": "lb", "operator": "lte",
                           "scope": "per_pet"},
          "Each pet may weigh up to 50.0 lbs"),
        F("pet_count_limit", 2, "Maximum Number of Pets in Room: 2"),
        F("pet_count_scope", "room", "Maximum Number of Pets in Room: 2"),
    ],
}
ROWS["CLE-AAQ-001-A11"] = {
    "artifact": "A11-aloft-cleveland-downtown.json",
    "outcome": "AFFIRMATIVE_PARTIAL",
    "candidate": True,
    "facts": [
        F("pets_allowed", True, "Pets Welcome"),
        F("pet_count_limit", 2, "Maximum Number of Pets in Room: 2"),
        F("pet_count_scope", "room", "Maximum Number of Pets in Room: 2"),
    ],
    "notes": ["'We do not require a deposit' is explicit no-deposit; the "
              "schema has no deposit_stated_none field, so it is recorded "
              "here and in the packet rather than invented into a field",
              "no fee, species or weight stated -- silence"],
}
ROWS["CLE-AAQ-001-A12"] = {
    "artifact": "A12-sheraton-suites-akron-cuyahoga-falls.json",
    "outcome": "AFFIRMATIVE_STRUCTURED",
    "candidate": True,
    "facts": [
        F("pets_allowed", True, "Pets Welcome"),
        F("pet_fee", {"amount_cents": 5000, "currency": "USD",
                      "basis": "per_stay", "scope": "per_room"},
          "USD 50 fee per room per stay"),
        F("weight_limit", {"value": 40, "unit": "lb", "operator": "lte",
                           "scope": "per_pet"},
          "Each pet may weigh up to 40.0 lbs",
          "the FAQ's per-pet sentence resolves the prose '2 pets 40 lbs max "
          "per room', which alone could read combined"),
        F("pet_count_limit", 2, "Maximum Number of Pets in Room: 2"),
        F("pet_count_scope", "room", "Maximum Number of Pets in Room: 2"),
        F("reservation_requirement", "signed waiver", "signed waiver"),
    ],
}
ROWS["CLE-AAQ-001-A13"] = {
    "artifact": "A13-residence-inn-akron-fairlawn.json",
    "outcome": "AFFIRMATIVE_STRUCTURED",
    "candidate": True,
    "facts": [
        F("pets_allowed", True, "Pets Welcome"),
        F("pet_fee", {"amount_cents": 10000, "currency": "USD",
                      "basis": "per_stay"},
          "Non-Refundable Pet Fee Per Stay: $100.00"),
        F("general_restrictions",
          "Additional fees may apply based on length of stay. Contact hotel "
          "for details.",
          "Additional fees may apply based on length of stay. Contact hotel "
          "for details."),
        F("pet_count_limit", 2, "Maximum Number of Pets in Room: 2"),
        F("pet_count_scope", "room", "Maximum Number of Pets in Room: 2"),
    ],
}
ROWS["CLE-AAQ-001-A14"] = {
    "artifact": "A14-residence-inn-mentor.json",
    "outcome": "AFFIRMATIVE_PARTIAL",
    "candidate": True,
    "facts": [
        F("pets_allowed", True, "Pets Welcome"),
        F("pet_fee", {"amount_cents": 10000, "currency": "USD",
                      "basis": "per_stay"},
          "Non-Refundable Pet Fee Per Stay: $100.00"),
    ],
    "withheld": [{
        "field": "cleaning_fee",
        "reason_code": "SOURCE_AMBIGUOUS",
        "reason": "A second nightly amount appears beside the per-stay fee "
                  "with no stated relationship between them. Publishing it "
                  "as additive would assert a total the page never states.",
        "quote": "Non-Refundable Pet Fee Per Night: $5.00",
    }],
    "notes": ["same $100/stay + $5/night pattern the founder already "
              "adjudicated on the two published Residence Inns; no count or "
              "weight stated"],
}
ROWS["CLE-AAQ-001-A15"] = {
    "artifact": "A15-aloft-cleveland-airport.json",
    "outcome": "AFFIRMATIVE_STRUCTURED",
    "candidate": True,
    "facts": [
        F("pets_allowed", True, "Pets Welcome"),
        F("weight_limit", {"value": 40, "unit": "lb", "operator": "lte",
                           "scope": "per_pet"},
          "Each pet may weigh up to 40.0 lbs"),
        F("pet_count_limit", 2, "Maximum Number of Pets in Room: 2"),
        F("pet_count_scope", "room", "Maximum Number of Pets in Room: 2"),
    ],
    "notes": ["no fee stated -- silence"],
}
ROWS["CLE-AAQ-001-A16"] = {
    "artifact": "A16-red-roof-inn-north-canton.json",
    "outcome": "AFFIRMATIVE_STRUCTURED",
    "candidate": True,
    "facts": [
        F("pets_allowed", True,
          "One, well-behaved domestic pet (cat or dog) Stays Free!"),
        F("species", {"dogs": "accepted", "cats": "accepted"},
          "domestic pet (cat or dog)"),
        F("pet_count_limit", 2, "Up to 2 pets allowed per room."),
        F("pet_count_scope", "room", "Up to 2 pets allowed per room."),
        F("fee_pet_schedule",
          [{"pet_ordinal": 1, "amount_cents": 0, "currency": "USD",
            "quote": "One, well-behaved domestic pet (cat or dog) Stays Free!"},
           {"pet_ordinal": 2, "amount_cents": 1500, "currency": "USD",
            "basis": "per_night",
            "cap": {"amount_cents": 10500, "basis": "per_stay",
                    "scope": "per_pet",
                    "quote": "not to exceed 7 nights or $105 per pet per stay"},
            "quote": "Second pet $15/ night"}],
          "Second pet $15/ night, not to exceed 7 nights or $105 per pet per "
          "stay.",
          "same shape the founder attested on the Columbus Red Roofs: the "
          "cap belongs to the SECOND pet, never to the property"),
        F("weight_limit", {"value": 80, "unit": "lb", "operator": "lte",
                           "scope": "per_pet"},
          "Pet not to exceed 80 pounds."),
        F("reservation_requirement", "Pets must be declared at check-in.",
          "Pets must be declared at check-in."),
        F("service_animal_statement",
          {"stated": True, "charges_stated": "no_charge"},
          "Service and emotional support animals are always welcome.",
          "the ESA half is a legal access category; per the Columbus "
          "Red Roof founder decision it is promoted here and never into "
          "general_restrictions"),
    ],
    "notes": ["the page JSON-LD names Red Roof HQ (7815 Walton Parkway); the "
              "identity binding below therefore rests on the visible page "
              "text, which carries the property's own address and ZIP"],
}
ROWS["CLE-AAQ-001-A17"] = {
    "artifact": "A17-americas-best-value-inn-alliance.json",
    "outcome": "AFFIRMATIVE_STRUCTURED",
    "candidate": True,
    "facts": [
        F("pets_allowed", True,
          "Pets are welcome for a charge of $10 per pet per night"),
        F("pet_fee", {"amount_cents": 1000, "currency": "USD",
                      "basis": "per_night", "scope": "per_pet"},
          "a charge of $10 per pet per night"),
    ],
}

# ---- GROUP B: known refusals ---------------------------------------------- #
_CHOICE_REFUSAL = ("Pets Allowed: No General: Only service animals are "
                   "permitted, free of charge.")
for qid, art in [
    ("CLE-AAQ-001-B01", "B01-comfort-inn-downtown.json"),
    ("CLE-AAQ-001-B02", "B02-comfort-inn-akron-south.json"),
    ("CLE-AAQ-001-B03", "B03-comfort-inn-independence.json"),
    ("CLE-AAQ-001-B04", "B04-comfort-inn-cleveland-south-richfield.json"),
    ("CLE-AAQ-001-B05", "B05-comfort-inn-suites-streetsboro.json"),
    ("CLE-AAQ-001-B06", "B06-cambria-hotel-akron-canton-airport.json"),
]:
    ROWS[qid] = {"artifact": art, "outcome": "NEGATIVE", "candidate": False,
                 "refusal_quote": _CHOICE_REFUSAL}
for qid, art in [
    ("CLE-AAQ-001-B07", "B07-blu-tique-akron.json"),
    ("CLE-AAQ-001-B08", "B08-fairfield-inn-suites-canton.json"),
    ("CLE-AAQ-001-B09", "B09-fairfield-inn-suites-canton-south.json"),
    ("CLE-AAQ-001-B10", "B10-courtyard-independence.json"),
    ("CLE-AAQ-001-B11", "B11-courtyard-akron-fairlawn.json"),
    ("CLE-AAQ-001-B13", "B13-marriott-cleveland-east.json"),
    ("CLE-AAQ-001-B14", "B14-courtyard-willoughby.json"),
]:
    ROWS[qid] = {"artifact": art, "outcome": "NEGATIVE", "candidate": False,
                 "refusal_quote": "Pet Policy Pets Not Allowed"}
ROWS["CLE-AAQ-001-B12"] = {
    "artifact": "B12-springhill-suites-canton.json", "outcome": "NEGATIVE",
    "candidate": False,
    "refusal_quote": "Pets Not Allowed No pets allowed-service animals only",
}
ROWS["CLE-AAQ-001-B15"] = {
    "artifact": "B15-oneil-house-bed-and-breakfast.json", "outcome": "NEGATIVE",
    "candidate": False,
    "refusal_quote": "No smoking or pets allowed.",
}

# ---- GROUP C: attended policy-surface ------------------------------------- #
ROWS["CLE-AAQ-001-C01"] = {
    "artifact": "C01-economy-inn.json", "outcome": "POLICY_NOT_FOUND",
    "candidate": False,
    "notes": ["home, rooms, amenities and explore surfaces all captured or "
              "visited; no pet wording exists anywhere on the site. Silence, "
              "never a refusal."],
}
ROWS["CLE-AAQ-001-C02"] = {
    "artifact": "C02-extended-stay-america-select-akron-south.json",
    "outcome": "AFFIRMATIVE_STRUCTURED",
    "candidate": True,
    "facts": [
        F("pets_allowed", True,
          "A maximum of two pets are allowed in each suite."),
        F("pet_count_limit", 2,
          "A maximum of two pets are allowed in each suite."),
        F("pet_count_scope", "room",
          "A maximum of two pets are allowed in each suite."),
        F("dimension_constraints",
          "pets can be no longer than 36 inches and no taller than 36 inches",
          "pets can be no longer than 36 inches and no taller than 36 inches"),
        F("fee_tiers",
          [{"amount_cents": 2500, "currency": "USD", "basis": "per_night",
            "scope": "per_pet", "condition_type": "stay_length_range",
            "condition_min": 1, "condition_max": 6, "boundary_unit": "nights",
            "role": "REPLACEMENT_PRICE", "tax_relationship": "plus_tax",
            "quote": "up to a $25 (+ tax) per day non-refundable cleaning fee "
                     "for the first six (6) nights, per pet"},
           {"amount_cents": 1500, "currency": "USD", "basis": "per_night",
            "scope": "per_pet", "condition_type": "stay_length_range",
            "condition_min": 7, "boundary_unit": "nights",
            "role": "REPLACEMENT_PRICE", "tax_relationship": "plus_tax",
            "quote": "Each day thereafter there is a pet cleaning fee not to "
                     "exceed $15 non-refundable fee (+tax) per day, per pet"}],
          "up to a $25 (+ tax) per day non-refundable cleaning fee for the "
          "first six (6) nights, per pet",
          "ESA's brand-standard schedule; mirror the shape the Dayton ESA "
          "records carry so the corpus spells it one way"),
    ],
}
for qid, art, refusal in [
    ("CLE-AAQ-001-C03", "C03-holiday-inn-express-brookpark.json",
     "No, pets are not allowed at Holiday Inn Express Cleveland Airport - "
     "Brook Park."),
    ("CLE-AAQ-001-C04", "C04-holiday-inn-express-akron-nw-fairlawn.json",
     "No, pets are not allowed at Holiday Inn Express Akron NW - Fairlawn."),
    ("CLE-AAQ-001-C05", "C05-holiday-inn-express-suites-alliance.json",
     "No, pets are not allowed at Holiday Inn Express & Suites Alliance."),
    ("CLE-AAQ-001-C06", "C06-crowne-plaza-cleveland-playhouse-square.json",
     "No, pets are not allowed at Crowne Plaza Cleveland at Playhouse "
     "Square."),
    ("CLE-AAQ-001-C07", "C07-holiday-inn-cleveland-mayfield.json",
     "No, pets are not allowed at Holiday Inn Cleveland-Mayfield."),
    ("CLE-AAQ-001-C08", "C08-holiday-inn-mentor.json",
     "No, pets are not allowed at Holiday Inn Cleveland Northeast - Mentor."),
]:
    ROWS[qid] = {"artifact": art, "outcome": "NEGATIVE", "candidate": False,
                 "refusal_quote": refusal}
ROWS["CLE-AAQ-001-C09"] = {
    "artifact": "C09-motel-6-richfield.json",
    "outcome": "AFFIRMATIVE_PARTIAL",
    "candidate": True,
    "facts": [
        F("pets_allowed", True, "Pets Allowed",
          "the property page's own amenity row; its 'Pets Stay Free' label "
          "links to the brand policy captured as C09b"),
    ],
    "supplementary_artifact": "C09b-motel6-brand-reservation-policies.json",
    "notes": ["the page lists reservations line 330-659-6116 while the census carries 330-293-3647; street, ZIP and name bind -- census phone to review","the fee-free statement and the 2-pet limit live on the BRAND "
              "policy page ('service animals and well-behaved pets always "
              "stay free', 'Pet limit of 2 pets per room') -- PT2_BRAND "
              "evidence; the packet proposes nothing from it beyond what the "
              "founder rules, and it must never be represented as "
              "property-level wording"],
}
ROWS["CLE-AAQ-001-C10"] = {
    "artifact": "C10-super-8-copley-akron.json",
    "outcome": "AFFIRMATIVE_STRUCTURED",
    "candidate": True,
    "facts": [
        F("pets_allowed", True, "Pets Allowed - Dogs only - 2 Dogs max."),
        F("species", {"dogs": "accepted"}, "Dogs only"),
        F("pet_count_limit", 2, "2 Dogs max."),
        F("pet_fee", {"amount_cents": 2500, "currency": "USD",
                      "basis": "per_night", "scope": "per_pet"},
          "Non-refundable 25USD per pet per night."),
        F("service_animal_statement",
          {"stated": True, "charges_stated": "not_addressed"},
          "Service Animals - ADA-defined service animals welcome."),
    ],
}
ROWS["CLE-AAQ-001-C11"] = {
    "artifact": "C11-baymont-copley-akron.json",
    "outcome": "AFFIRMATIVE_STRUCTURED",
    "candidate": True,
    "facts": [
        F("pets_allowed", True, "Dogs Allowed - 2 pets max. Dogs only."),
        F("species", {"dogs": "accepted"}, "Dogs only."),
        F("pet_count_limit", 2, "2 pets max."),
        F("pet_fee", {"amount_cents": 2500, "currency": "USD",
                      "basis": "per_night", "scope": "per_pet"},
          "25USD per pet per night."),
        F("service_animal_statement",
          {"stated": True, "charges_stated": "not_addressed"},
          "Service Animals - ADA-defined service animals welcome."),
    ],
}
ROWS["CLE-AAQ-001-C12"] = {
    "artifact": "C12-days-inn-lakewood.json",
    "outcome": "AFFIRMATIVE_STRUCTURED",
    "candidate": True,
    "facts": [
        F("pets_allowed", True, "Pets are allowed at a 10 USD per day charge."),
        F("pet_fee", {"amount_cents": 1000, "currency": "USD",
                      "basis": "per_night"},
          "Pets are allowed at a 10 USD per day charge.",
          "scope unstated -- not invented"),
        F("breed_restrictions", "Local city ordinance forbids pit bulls.",
          "Local city ordinance forbids pit bulls."),
        F("service_animal_statement",
          {"stated": True, "charges_stated": "not_addressed"},
          "ADA defined service animals are also welcome at this hotel."),
    ],
    "notes": ["'There is no deposit required.' is explicit no-deposit; "
              "recorded here (no schema field exists for stated-none "
              "deposits)"],
}
for qid, art, refusal in [
    ("CLE-AAQ-001-C13", "C13-travelodge-lakewood.json",
     "ADA defined service animals are welcome at this hotel. Sorry no other "
     "pets are allowed."),
    ("CLE-AAQ-001-C14", "C14-microtel-north-canton.json",
     "ADA defined service animals are welcome at this hotel. Sorry no other "
     "pets are allowed."),
]:
    ROWS[qid] = {"artifact": art, "outcome": "NEGATIVE", "candidate": False,
                 "refusal_quote": refusal}

# ---- GROUP D: routing review ---------------------------------------------- #
ROWS["CLE-AAQ-001-D01"] = {
    "artifact": None, "outcome": "ACCESS_BLOCKED", "candidate": False,
    "notes": [HYATT_NOTE,
              "routing stays HELD: no first-party identity evidence can be "
              "read without driving a Hyatt surface; queue for the "
              "operator-manual session"],
}

# ---- GROUP E: Drury artifact upgrades ------------------------------------- #
DRURY = OrderedDict([
    ("drury inn and suites beachwood", {
        "row_id": 48,
        "artifact": "E48-drury-inn-and-suites-beachwood.json",
    }),
    ("drury plaza hotel", {
        "row_id": 49,
        "artifact": "E49-drury-plaza-hotel-cleveland-downtown.json",
    }),
])


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
    """Recompute the capture's own content hashes."""
    return {
        "html_sha256": sha_text(doc.get("html", "")),
        "text_sha256": sha_text(doc.get("text", "")),
        "html_agrees": sha_text(doc.get("html", "")) == doc.get("html_sha256"),
        "text_agrees": sha_text(doc.get("text", "")) == doc.get("text_sha256"),
    }


def quote_backed(quote: str, doc: Dict) -> str:
    """Where the quote lives in the artifact: text, html, or nowhere."""
    if evidence_contract.quote_is_contiguous(quote, doc.get("text", "")):
        return "text"
    if evidence_contract.quote_is_contiguous(quote, doc.get("html", "")):
        return "html"
    return "MISSING"


def identity_binding(row: Dict, doc: Dict) -> Dict:
    """Signals binding the capture to the queue identity, from the page.

    The full rendered HTML is part of the haystack: several surfaces (Red
    Roof, Motel 6) carry the property's own address, ZIP and phone in markup
    or data payloads that the collapsed innerText does not repeat.
    """
    hay = " ".join((_c(doc.get("text", "")),
                    _c(" ".join(doc.get("jsonld") or [])),
                    _c(doc.get("html", ""))))
    phone = _digits(row.get("phone", ""))[-10:]
    street_no = (row.get("address", "").strip().split(" ", 1) or [""])[0]
    zip5 = _digits(row.get("zip", ""))[:5]
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


# --------------------------------------------------------------------------- #
# Drury upgrade (the only authority change this pass applies).
# --------------------------------------------------------------------------- #

def upgrade_drury(facts: Dict, captures: Dict[str, Dict],
                  raw_dir: Path) -> List[Dict]:
    deltas = []
    for hotel in facts["hotels"]:
        key = hotel["identity_key"]
        if key not in DRURY:
            continue
        doc = captures[key]
        integrity = verify_capture(doc)
        if not (integrity["html_agrees"] and integrity["text_agrees"]):
            raise AssertionError("%s: capture bytes disagree with their own "
                                 "recorded hashes" % key)
        for entry in hotel["evidence"]:
            where = quote_backed(entry["quote"], doc)
            if where == "MISSING":
                raise AssertionError(
                    "%s: quote %r is no longer carried by the captured page; "
                    "facts may not be upgraded against it"
                    % (key, entry["quote"][:60]))
        before_refs = sorted(e["evidence_ref"] for e in hotel["evidence"])
        prior_approval = copy.deepcopy(hotel["approval"])
        if record_hash(hotel) != prior_approval["record_hash"]:
            raise AssertionError("%s: record drifted before upgrade" % key)
        for entry in hotel["evidence"]:
            entry["artifact_class"] = enums.PUBLICATION_GRADE_EVIDENCE
            entry["artifact_sha256"] = "sha256:%s" % integrity["html_sha256"]
            entry["artifact_kind"] = enums.ARTIFACT_RENDERED_HTML
            entry["captured_at"] = doc["captured_at"]
            entry["capture_method"] = "attended_browser"
            entry["source_grade"] = enums.GRADE_PT1_FIRST_PARTY
        if before_refs != sorted(evidence_ref_for(e)
                                 for e in hotel["evidence"]):
            raise AssertionError("%s: upgrade moved an evidence ref" % key)
        issues = evidence_contract.validate(hotel)
        if issues:
            raise AssertionError("%s: fails evidence contract after upgrade: "
                                 "%s" % (key, issues))
        new_evidence_hash = evidence_hash(hotel["evidence"])
        if new_evidence_hash != prior_approval["evidence_hash"]:
            raise AssertionError("%s: evidence set moved; upgrade must only "
                                 "bind artifacts" % key)
        hotel["approval"] = OrderedDict([
            ("decision", enums.MACHINE_REVIEWED_PENDING_OPERATOR),
            ("operator", AGENT_IDENTITY),
            ("approval_date", PASS_DATE),
            ("supersedes", prior_approval),
            ("caveats", [
                "%s. Publication-grade bindings were added citing the byte-"
                "retained attended capture (%s, html sha256:%s...); every "
                "published quote was re-asserted contiguous in that capture "
                "-- the page now carries its pet policy in its embedded data "
                "payload rather than as always-rendered text, and the quotes "
                "verify against the retained HTML. Facts, quotes and the "
                "evidence set are unchanged (evidence_hash identical); "
                "record_hash moved with the bindings, so the founder "
                "approval preserved verbatim under 'supersedes' no longer "
                "binds and re-attestation against the hashes below is "
                "required. worker_result_hash keeps naming the 2026-08-11 "
                "deterministic fetch as historical provenance."
                % (WORK_ORDER, DRURY[key]["artifact"],
                   integrity["html_sha256"][:16]),
            ]),
            ("record_hash", ""),
            ("evidence_hash", new_evidence_hash),
        ])
        hotel["approval"]["record_hash"] = record_hash(hotel)
        deltas.append(OrderedDict([
            ("identity_key", key),
            ("row", DRURY[key]["row_id"]),
            ("artifact", DRURY[key]["artifact"]),
            ("artifact_sha256", "sha256:%s" % integrity["html_sha256"]),
            ("captured_at", doc["captured_at"]),
            ("entries_upgraded", len(hotel["evidence"])),
            ("facts_changed", False),
            ("record_hash_before", prior_approval["record_hash"]),
            ("record_hash_after", hotel["approval"]["record_hash"]),
            ("evidence_hash_unchanged", True),
            ("approval_action",
             "SUPERSEDED_PENDING_REATTESTATION_RECORD_HASH_MOVED"),
            ("rendering_note",
             "the property page renders its pet policy from an embedded data "
             "payload; the verbatim paragraph is contiguous in the retained "
             "HTML and identical to the published quotes"),
        ]))
    if len(deltas) != 2:
        raise AssertionError("expected exactly 2 Drury records, found %d"
                             % len(deltas))
    return deltas


# --------------------------------------------------------------------------- #
# Run.
# --------------------------------------------------------------------------- #

def run(data_root: Path, apply: bool) -> Dict:
    raw_dir = data_root / RAW_REL
    queue_rows = {r["queue_id"]: r for r in csv.DictReader(
        (data_root / QUEUE_CSV_REL).open(encoding="utf-8-sig"))}
    if len(queue_rows) != 47:
        raise SystemExit("STOP: queue source does not carry 47 rows")

    results: List[Dict] = []
    packet_positive: List[Dict] = []
    packet_negative: List[Dict] = []
    counts: Dict[str, int] = {}

    for qid, spec in ROWS.items():
        queue_row = queue_rows[qid]
        outcome = spec["outcome"]
        counts[outcome] = counts.get(outcome, 0) + 1
        row = OrderedDict([
            ("queue_id", qid),
            ("queue_class", queue_row["queue_class"]),
            ("hotel", queue_row["exact_hotel_name"]),
            ("hotel_id", queue_row["hotel_id"]),
            ("outcome", outcome),
        ])
        if spec.get("artifact"):
            path = raw_dir / spec["artifact"]
            doc = load_json(path)
            integrity = verify_capture(doc)
            binding = identity_binding(queue_row, doc)
            row.update([
                ("artifact_file", spec["artifact"]),
                ("artifact_bytes", path.stat().st_size),
                ("artifact_file_sha256", hashlib.sha256(
                    path.read_bytes()).hexdigest()),
                ("html_sha256", integrity["html_sha256"]),
                ("text_sha256", integrity["text_sha256"]),
                ("content_hashes_agree",
                 integrity["html_agrees"] and integrity["text_agrees"]),
                ("captured_at", doc.get("captured_at")),
                ("capture_method", "attended_browser"),
                ("final_url", doc.get("final_url")),
                ("identity_binding", binding),
            ])
            if not (integrity["html_agrees"] and integrity["text_agrees"]):
                raise AssertionError("%s: capture integrity failure" % qid)

            if outcome == "NEGATIVE":
                where = quote_backed(spec["refusal_quote"], doc)
                if where == "MISSING":
                    raise AssertionError("%s: refusal quote not in capture"
                                         % qid)
                row["refusal_quote"] = spec["refusal_quote"]
                row["quote_backed_by"] = where
                packet_negative.append(OrderedDict([
                    ("queue_id", qid),
                    ("hotel", queue_row["exact_hotel_name"]),
                    ("hotel_id", queue_row["hotel_id"]),
                    ("proposed_state", "VERIFIED_NO_PETS"),
                    ("refusal_quote", spec["refusal_quote"]),
                    ("source_url", doc.get("final_url")),
                    ("artifact_file", spec["artifact"]),
                    ("artifact_sha256",
                     "sha256:%s" % integrity["html_sha256"]),
                    ("artifact_kind", "rendered_html"),
                    ("captured_at", doc.get("captured_at")),
                    ("identity_binding", binding),
                    ("recommendation", "APPROVE_VERIFIED_NO_PETS"),
                ]))
            if spec.get("candidate"):
                checked = []
                for fact in spec.get("facts", []):
                    where = quote_backed(fact["quote"], doc)
                    if where == "MISSING":
                        raise AssertionError(
                            "%s: quote %r not carried by the capture"
                            % (qid, fact["quote"][:60]))
                    fact = OrderedDict(fact)
                    fact["quote_backed_by"] = where
                    checked.append(fact)
                packet_positive.append(OrderedDict([
                    ("queue_id", qid),
                    ("hotel", queue_row["exact_hotel_name"]),
                    ("hotel_id", queue_row["hotel_id"]),
                    ("outcome", outcome),
                    ("source_url", doc.get("final_url")),
                    ("artifact_file", spec["artifact"]),
                    ("artifact_sha256",
                     "sha256:%s" % integrity["html_sha256"]),
                    ("artifact_kind", "rendered_html"),
                    ("captured_at", doc.get("captured_at")),
                    ("capture_method", "attended_browser"),
                    ("source_grade", enums.GRADE_PT1_FIRST_PARTY),
                    ("identity_binding", binding),
                    ("proposed_facts", checked),
                    ("proposed_withheld", spec.get("withheld", [])),
                    ("supplementary_artifact",
                     spec.get("supplementary_artifact")),
                    ("notes", spec.get("notes", [])),
                    ("recommendation",
                     "APPROVE_PUBLICATION" if outcome ==
                     "AFFIRMATIVE_STRUCTURED" else
                     "APPROVE_PARTIAL_PUBLICATION"),
                ]))
        else:
            row["artifact_file"] = None
        if spec.get("notes"):
            row["notes"] = spec["notes"]
        results.append(row)

    # Drury rows 48-49 in the same ledger.
    facts = load_json(FACTS_PATH)
    drury_captures = {key: load_json(raw_dir / meta["artifact"])
                      for key, meta in DRURY.items()}
    facts_work = copy.deepcopy(facts)
    deltas = upgrade_drury(facts_work, drury_captures, raw_dir)
    for delta in deltas:
        counts["DRURY_ARTIFACT_UPGRADE"] = \
            counts.get("DRURY_ARTIFACT_UPGRADE", 0) + 1
        results.append(OrderedDict([
            ("queue_id", "CLE-AAQ-001-E%d" % delta["row"]),
            ("queue_class", "E"),
            ("hotel", delta["identity_key"]),
            ("outcome", "DRURY_ARTIFACT_UPGRADE"),
            ("artifact_file", delta["artifact"]),
            ("delta", delta),
        ]))

    ledger = OrderedDict([
        ("schema", "ptf-cleveland-pass2-capture-results/1.0"),
        ("work_order", WORK_ORDER),
        ("as_of", PASS_DATE),
        ("market_id", MARKET),
        ("captured_by", AGENT_IDENTITY),
        ("capture_method",
         "attended browser (operator's Chrome, extension-driven); rendered "
         "HTML and page text retained as bytes in the gitignored worker tree "
         "at data/%s; committed output is hashes and verdicts only, because "
         "captured brand pages embed third-party credentials and are never "
         "committed" % RAW_REL.as_posix()),
        ("rows_total", 49),
        ("rows_captured", sum(1 for r in results
                              if r.get("artifact_file"))),
        ("rows_not_driven", [qid for qid, s in ROWS.items()
                             if not s.get("artifact")]),
        ("outcome_counts", counts),
        ("rule",
         "A failed or forbidden capture is never negative evidence; a "
         "refusal is proposed only where the property's own page states it; "
         "no fact is proposed without its exact quote verified against the "
         "retained artifact bytes."),
        ("results", results),
    ])

    packet = OrderedDict([
        ("schema", "ptf-cleveland-pass2-founder-review-packet/1.0"),
        ("work_order", WORK_ORDER),
        ("as_of", PASS_DATE),
        ("prepared_by", AGENT_IDENTITY),
        ("status", "AWAITING_FOUNDER_DECISION"),
        ("rule",
         "Nothing here is published. Every proposed fact carries the exact "
         "first-party quote that supports it, verified contiguous in the "
         "hash-bound artifact named beside it; withholding is proposed only "
         "where the source contradicts or garbles itself, never for "
         "silence. Approving a candidate authorizes writing its canonical "
         "record with publication-grade evidence and a founder approval "
         "bound to the final record_hash -- performed in the next pass, "
         "never here."),
        ("positive_candidates", packet_positive),
        ("negative_candidates", packet_negative),
        ("drury_reattestation_deltas", deltas),
        ("not_driven",
         [{"queue_id": qid, "hotel": queue_rows[qid]["exact_hotel_name"]
           if qid in queue_rows else qid,
           "reason": HYATT_NOTE} for qid, s in ROWS.items()
          if not s.get("artifact")]),
    ])

    if apply:
        payload = write_lf(FACTS_PATH, facts_work)
        new_sha = hashlib.sha256(payload).hexdigest()
        contract = load_json(CONTRACT_PATH)
        contract["policy_package"]["expected_sha256"] = new_sha
        write_lf(CONTRACT_PATH, contract)
        # Continue the sha trail the Pass-1 report carries, so the contract
        # pin is always traceable to the pass that moved it.
        report_path = LP / "cleveland_artifact_verification_001.json"
        report = load_json(report_path)
        report["facts_sha256_after_pass2"] = new_sha
        write_lf(report_path, report)
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
    print("rows: %d | captured: %d | not driven: %s"
          % (ledger["rows_total"], ledger["rows_captured"],
             ",".join(ledger["rows_not_driven"])))
    for name, count in sorted(ledger["outcome_counts"].items()):
        print("  %-26s %d" % (name, count))
    if not args.apply:
        print("dry run: nothing written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
