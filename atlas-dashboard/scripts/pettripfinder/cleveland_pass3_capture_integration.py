"""PTF-CLEVELAND-ATTENDED-PASS-3-001 -- driveable-queue capture integration.

Turns the cleveland-attended-capture-003 worker-tree captures into committed,
verifiable outputs WITHOUT changing any authority file:

* ``cleveland_pass3_capture_results.json`` -- every one of the 68 queue rows
  exactly once, with its outcome, artifact hashes recomputed from the bytes on
  disk, mechanical identity binding, quote verification, and the session speed
  benchmark.
* ``cleveland_pass3_founder_review_packet.json`` -- one decision packet per
  positive candidate (canonical facts proposed ONLY where the captured page
  states them, each fact carrying its exact quote), one per VERIFIED_NO_PETS
  candidate (the refusal sentence, verbatim), the operator-manual instructions
  for the three ADR-blocked Hyatt surfaces, and the routing-review
  observations this pass surfaced.

NO authority transition happens here: no facts file edit, no approval, no
partition change, no census change. Every proposed fact is loader-asserted:
its quote must appear (whitespace-collapsed) in the captured page text or,
where a surface keeps its policy in markup the collapsed innerText does not
repeat (IHG's aria-hidden FAQ regions), in the captured page HTML. A quote
that fails the assertion aborts the run rather than shipping a claim the
artifact does not carry.

Run:  python -m scripts.pettripfinder.cleveland_pass3_capture_integration \
          [--data-root PATH] [--apply]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.contracts import enums                            # noqa: E402
from scripts.pettripfinder.contracts import evidence as evidence_contract    # noqa: E402

MARKET = "cleveland-akron-canton-oh"
WORK_ORDER = "PTF-CLEVELAND-ATTENDED-PASS-3-001"
PASS_DATE = "2026-08-16"
AGENT_IDENTITY = "claude-fable-5 (%s, agent)" % WORK_ORDER

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
QUEUE_PATH = LP / "cleveland_pass3_queue.json"
RESULTS_PATH = LP / "cleveland_pass3_capture_results.json"
PACKET_PATH = LP / "cleveland_pass3_founder_review_packet.json"

RAW_REL = Path("worker_runs/pettripfinder/cleveland-attended-capture-003/raw")
START_EPOCH_PATH = Path("C:/t/pass3_start_epoch.txt")

HILTON_BLOCK_NOTE = (
    "Hilton's Akamai edge rate-limited this session after sixteen rapid "
    "Hilton-family captures; the block lifted for every OTHER property "
    "URL after roughly an hour (nine further captures succeeded at a "
    "slower pace), but this URL -- the one used for the repeated "
    "cool-down probes -- kept serving the block page ('Hilton Page "
    "Reference Code') through the end of the session. A block page is "
    "never policy evidence; the row stays capturable and should be "
    "re-driven in a later session (twenty-five sibling captures prove "
    "the surface serves this browser when unthrottled).")

WEIGHT_CONVENTION_NOTE = (
    "widget/label wording states no per-pet or per-room scope; per_pet "
    "follows the reading convention the founder reviewed and kept on four "
    "Cleveland records (KEEP_AS_IS, Pass-1 closeout)")


def _c(value: str) -> str:
    return " ".join((value or "").split())


def _digits(value: str) -> str:
    return "".join(ch for ch in (value or "") if ch.isdigit())


# --------------------------------------------------------------------------- #
# Adjudication table. Facts are proposed ONLY where the page states them; the
# quote beside each value is asserted against the captured artifact.
# --------------------------------------------------------------------------- #

def F(field: str, value, quote: str, note: str = "") -> Dict:
    entry = OrderedDict([("field", field), ("value", value), ("quote", quote)])
    if note:
        entry["note"] = note
    return entry


def W(field: str, reason_code: str, reason: str, quote: str) -> Dict:
    return OrderedDict([("field", field), ("reason_code", reason_code),
                        ("reason", reason), ("quote", quote)])


ROWS: "OrderedDict[str, Dict]" = OrderedDict()

# ---- OBSERVATION rows 001-030 --------------------------------------------- #

ROWS["CLE-P3-001"] = {
    "artifact": "P3-001-ariel-broadway-hotel.json",
    "outcome": "POLICY_NOT_FOUND", "candidate": False,
    "notes": ["homepage captured; no pet or animal wording anywhere in the "
              "rendered text. Silence, never a refusal."],
}
ROWS["CLE-P3-002"] = {
    "artifact": "P3-002-cambria-hotel-suites-avon.json",
    "outcome": "CAPTURE_FAILED", "candidate": False,
    "notes": ["url_dead: the queued property page "
              "choicehotels.com/ohio/avon/cambria-hotels/oh598 redirects to "
              "the brand's Avon city listing (?brand=BR). The property page "
              "no longer serves; routing-review candidate. The redirect "
              "target was captured as proof."],
}
ROWS["CLE-P3-003"] = {
    "artifact": "P3-003-cleveland-house-hotels.json",
    "outcome": "POLICY_NOT_FOUND", "candidate": False,
    "notes": ["homepage captured; no pet or animal wording in the rendered "
              "text."],
}
ROWS["CLE-P3-004"] = {
    "artifact": "P3-004b-doubletree-canton-downtown-hilton.json",
    "supplementary_artifact": "P3-004-doubletree-canton-downtown.json",
    "outcome": "NEGATIVE", "candidate": False,
    "refusal_quote": "Pets not allowed",
    "notes": ["the queued official URL is https://www.330barandgrill.com/ "
              "-- captured as the supplementary artifact, it is the "
              "HOTEL'S OWN RESTAURANT's site (the property page's dining "
              "section names 330 Bar and Grill as its restaurant) with no "
              "lodging or pet content; routing-review candidate: the "
              "property page is hilton.com/en/hotels/cakcodt-doubletree-"
              "canton-downtown/, whose amenity list states 'Pets not "
              "allowed'. The refusal is the property page's own words; "
              "identity binds by JSON-LD (320 Market Avenue South, 44702, "
              "330-471-8000)."],
}
ROWS["CLE-P3-005"] = {
    "artifact": "P3-005-emerald-necklace-inn.json",
    "supplementary_artifact": "P3-005b-emerald-necklace-inn-policy.json",
    "quote_artifact": "P3-005b-emerald-necklace-inn-policy.json",
    "outcome": "AFFIRMATIVE_STRUCTURED", "candidate": True,
    "facts": [
        F("pets_allowed", True,
          "We welcome your pets at our Inn. Only in Parkview Suite."),
        F("pet_room_restriction", "Only in Parkview Suite.",
          "Only in Parkview Suite."),
        F("pet_fee", {"amount_cents": 2500, "currency": "USD",
                      "basis": "per_stay"},
          "There is a $25.00 service charge per visit.",
          "the page's own basis word is 'per visit'; per_stay is the "
          "nearest schema basis and the quote preserves the original"),
        F("unattended_policy",
          "Please do not leave pets unattended in your room.",
          "Please do not leave pets unattended in your room."),
        F("general_restrictions",
          "Pets are not permitted in dining areas. All pets must be leashed "
          "outside of guest suite.",
          "Pets are not permitted in dining areas. All pets must be leashed "
          "outside of guest suite."),
    ],
    "notes": ["policy lives on /policy/ (supplementary artifact is the "
              "quote source); damages are billed to the card on file per "
              "the same section"],
}
ROWS["CLE-P3-006"] = {
    "artifact": "P3-006-fidelity-hotel.json",
    "supplementary_artifact": "P3-006b-fidelity-hotel-faq.json",
    "quote_artifact": "P3-006b-fidelity-hotel-faq.json",
    "outcome": "AFFIRMATIVE_PARTIAL", "candidate": True,
    "facts": [
        F("pets_allowed", True,
          "Yes, Cleveland\u2019s Fidelity Hotel is proud to be pet friendly, "
          "offering amenities for our furry guests. No pet fees."),
        F("pet_fee", {"amount_cents": 0, "currency": "USD"},
          "No pet fees.",
          "an explicit fee-free statement; founder rules whether a zero-"
          "amount pet_fee is the canonical spelling"),
    ],
    "notes": ["species, count and weight are unstated on the FAQ; nothing "
              "is inferred"],
}
ROWS["CLE-P3-007"] = {
    "artifact": "P3-007-holiday-inn-canton.json",
    "outcome": "IDENTITY_UNCERTAIN", "candidate": False,
    "notes": ["the queued official URL is https://www.twenty20taphouse.com/ "
              "-- a restaurant site with no lodging or pet content; nothing "
              "on it can be bound to the Holiday Inn Canton identity. "
              "Routing-review candidate."],
}
ROWS["CLE-P3-008"] = {
    "artifact": "P3-008-holiday-inn-cleveland-clinic.json",
    "supplementary_artifact": "P3-008b-holiday-inn-cleveland-clinic-faq.json",
    "outcome": "POLICY_NOT_FOUND", "candidate": False,
    "notes": ["homepage and hotel-FAQ page both captured; neither carries "
              "any pet or animal wording (this property runs a vanity site, "
              "not an ihg.com surface)."],
}
ROWS["CLE-P3-009"] = {
    "artifact": "P3-009-holiday-inn-rockside.json",
    "supplementary_artifact": "P3-009b-holiday-inn-rockside-amenities.json",
    "outcome": "POLICY_NOT_FOUND", "candidate": False,
    "notes": ["homepage and amenities page both captured on the vanity site "
              "hirockside.com; no pet or animal wording on either."],
}
ROWS["CLE-P3-010"] = {
    "artifact": "P3-010-hotel-cleveland.json",
    "supplementary_artifact": "P3-010b-hotel-cleveland-stay.json",
    "outcome": "POLICY_NOT_FOUND", "candidate": False,
    "notes": ["homepage and /stay.htm both captured; no pet or animal "
              "wording on either."],
}
ROWS["CLE-P3-011"] = {
    "artifact": "P3-011-inn-at-brandywine-falls.json",
    "supplementary_artifact": "P3-011b-inn-at-brandywine-falls-faqs.json",
    "outcome": "POLICY_NOT_FOUND", "candidate": False,
    "notes": ["homepage and FAQs page both captured; no pet or animal "
              "wording on either."],
}
ROWS["CLE-P3-012"] = {
    "artifact": "P3-012-inn-cahoots.json",
    "outcome": "POLICY_NOT_FOUND", "candidate": False,
    "capture_method": "deterministic_fetch",
    "notes": ["the identity's own site is a bar-and-grill site (nav: New "
              "Index, Gallery, Cart) with no lodging or pet content. The "
              "attended browser loaded the page but blob downloads are "
              "silently blocked on this origin, so the retained artifact is "
              "a deterministic fetch of the same static page (the site is "
              "static; no bot wall)."],
}
ROWS["CLE-P3-013"] = {
    "artifact": "P3-013-inn-on-coventry.json",
    "outcome": "POLICY_NOT_FOUND", "candidate": False,
    "notes": ["homepage captured; no pet or animal wording."],
}
ROWS["CLE-P3-014"] = {
    "artifact": "P3-014-kent-state-hotel.json",
    "supplementary_artifact": "P3-014c-kent-state-hotel-faq-expanded.json",
    "outcome": "POLICY_NOT_FOUND", "candidate": False,
    "notes": ["homepage, FAQ page, and FAQ with accordions expanded all "
              "captured; no pet or animal wording on any surface."],
}
ROWS["CLE-P3-015"] = {
    "artifact": "P3-015-kimpton-schofield.json",
    "supplementary_artifact": "P3-015b-kimpton-schofield-pet-friendly.json",
    "quote_artifact": "P3-015b-kimpton-schofield-pet-friendly.json",
    "outcome": "AFFIRMATIVE_STRUCTURED", "candidate": True,
    "facts": [
        F("pets_allowed", True,
          "Our Pet Friendly Hotel in Cleveland welcomes your pet with:"),
        F("pet_deposit", {"amount_cents": 0, "currency": "USD"},
          "No deposit or cleaning fees charged",
          "explicit none-charged statement; founder rules the canonical "
          "spelling for stated-zero deposits"),
    ],
    "withheld": [
        W("weight_limit", "SCHEMA_CANNOT_REPRESENT",
          "The page states there is NO size or weight limit; the schema has "
          "no representation for an explicit no-limit, and publishing "
          "nothing would misread the page as silent.",
          "No size/weight limit"),
        W("pet_count_limit", "SCHEMA_CANNOT_REPRESENT",
          "The page states there is NO limit on the number of pets; the "
          "schema has no representation for an explicit no-limit.",
          "No limit on number of pets allowed"),
    ],
    "notes": ["the page welcomes dogs, cats and 'feathery or scaly' family "
              "members ('as long as they fit in the elevator'); species is "
              "deliberately NOT narrowed to dogs+cats",
              "cleaning fee: 'No deposit or cleaning fees charged' -- the "
              "no-fee statement covers deposit and cleaning fee; the page "
              "does not say 'no pet fee' in general, so pet_fee is not "
              "proposed as zero"],
}
ROWS["CLE-P3-016"] = {
    "artifact": "P3-016-metropolitan-at-the-9.json",
    "outcome": "POLICY_NOT_FOUND", "candidate": False,
    "notes": ["homepage captured; no pet or animal wording."],
}
ROWS["CLE-P3-017"] = {
    "artifact": "P3-017-palmantiers-motel.json",
    "outcome": "POLICY_NOT_FOUND", "candidate": False,
    "notes": ["homepage captured; no pet or animal wording."],
}
ROWS["CLE-P3-018"] = {
    "artifact": "P3-018-punderson-manor.json",
    "supplementary_artifact": "P3-018b-punderson-pet-cabins.json",
    "quote_artifact": "P3-018b-punderson-pet-cabins.json",
    "outcome": "AFFIRMATIVE_PARTIAL", "candidate": True,
    "facts": [
        F("pets_allowed", True,
          "we love welcoming pets into our select pet-friendly cabins"),
        F("pet_room_restriction",
          "select pet-friendly cabins",
          "we love welcoming pets into our select pet-friendly cabins"),
    ],
    "withheld": [
        W("pet_fee", "SCHEMA_CANNOT_REPRESENT",
          "The page states the pet fee is included in the nightly rate; no "
          "separate amount exists to record, and the schema has no "
          "included-in-rate representation.",
          "Pet fee is included in the rate per night on reservations."),
    ],
    "notes": ["lodge rooms vs cabins: the pet welcome is scoped to cabins "
              "by the page's own words; nothing is claimed for the lodge"],
}
ROWS["CLE-P3-019"] = {
    "artifact": "P3-019-radisson-akron-fairlawn.json",
    "outcome": "CAPTURE_FAILED", "candidate": False,
    "notes": ["url_dead: radissonhotels.com/en-us/hotels/radisson-akron "
              "redirects to the Radisson brand page; the property page no "
              "longer serves (property likely left the system). "
              "Routing-review candidate. The redirect target was captured "
              "as proof."],
}
ROWS["CLE-P3-020"] = {
    "artifact": "P3-020-roost-cleveland.json",
    "supplementary_artifact": "P3-020b-roost-cleveland-faq.json",
    "quote_artifact": "P3-020b-roost-cleveland-faq.json",
    "outcome": "AFFIRMATIVE_STRUCTURED", "candidate": True,
    "facts": [
        F("pets_allowed", True, "Yes! We love pets!"),
        F("weight_limit", {"value": 40, "unit": "lb", "operator": "lte",
                           "scope": "per_pet"},
          "we do not allow pets above 40 lbs",
          "each-pet reading of 'pets above'; convention, founder may hold"),
        F("species", {"dogs": "accepted", "cats": "accepted"},
          "We only allow dogs and cats."),
        F("breed_restrictions",
          "Breed restrictions are enforced, please call for more "
          "information.",
          "Breed restrictions are enforced, please call for more "
          "information."),
    ],
    "withheld": [
        W("cleaning_fee", "SCHEMA_CANNOT_REPRESENT",
          "The fee is a ceiling that varies with length of stay ('up to "
          "$350 ... depending on length of stay'); publishing the ceiling "
          "as a price would assert an amount the page never charges "
          "every guest.",
          "We charge a cleaning fee up to $350 pet for all pets (depending "
          "on length of stay)."),
    ],
    "notes": ["homepage JSON-LD carries petsAllowed:true, binding the "
              "identity (105 Prospect Ave E, 44115)"],
}
ROWS["CLE-P3-021"] = {
    "artifact": "P3-021-shady-oaks-farm.json",
    "supplementary_artifact": "P3-021b-shady-oaks-faqs.json",
    "quote_artifact": "P3-021b-shady-oaks-faqs.json",
    "outcome": "NEGATIVE", "candidate": False,
    "refusal_quote": "PETS: WE DO NOT PERMIT GUESTS TO BRING PETS TO ENSURE "
                     "AN ALLERGY FREE ENVIRONMENT FOR OUR GUESTS.",
}
ROWS["CLE-P3-022"] = {
    "artifact": "P3-022-skyview-lodge.json",
    "outcome": "POLICY_NOT_FOUND", "candidate": False,
    "notes": ["homepage captured; no pet or animal wording."],
}
ROWS["CLE-P3-023"] = {
    "artifact": "P3-023-sonesta-simply-suites-cleveland-airport.json",
    "supplementary_artifact": "P3-023b-sonesta-simply-suites-pet-policy.json",
    "quote_artifact": "P3-023b-sonesta-simply-suites-pet-policy.json",
    "outcome": "AFFIRMATIVE_STRUCTURED", "candidate": True,
    "facts": [
        F("pets_allowed", True,
          "Sonesta Simply Suites Cleveland Airport hotel is pet friendly "
          "and welcomes well-mannered pets."),
        F("pet_count_limit", 2,
          "Up to two pets are permitted per suite"),
        F("pet_count_scope", "suite",
          "Up to two pets are permitted per suite"),
        F("weight_limit", {"value": 50, "unit": "lb", "operator": "lte",
                           "scope": "per_pet"},
          "weighing up to 50lbs each",
          "'each' states per-pet"),
        F("pet_fee", {"amount_cents": 500, "currency": "USD",
                      "basis": "per_stay", "scope": "per_pet"},
          "A $5 fee applies per pet, per stay"),
        F("pet_deposit", {"amount_cents": 5000, "currency": "USD"},
          "along with a $50 deposit.",
          "refundability unstated -- not invented"),
    ],
    "notes": ["the page brands the property 'Sonesta Simply Suites' while "
              "the census carries 'Sonesta ES Suites' -- same address "
              "(17525 Rosbough), same phone; rebrand observation for census "
              "hygiene, not an identity failure"],
}
ROWS["CLE-P3-024"] = {
    "artifact": "P3-024-stone-gables-inn.json",
    "outcome": "POLICY_NOT_FOUND", "candidate": False,
    "notes": ["homepage captured; no pet or animal wording."],
}
ROWS["CLE-P3-025"] = {
    "artifact": "P3-025-terry-point-motel.json",
    "supplementary_artifact": "P3-025b-terry-point-faq.json",
    "quote_artifact": "P3-025b-terry-point-faq.json",
    "outcome": "NEGATIVE", "candidate": False,
    "refusal_quote": "Do you accept pets? No, sadly at this time we do not "
                     "allow pets.",
    "notes": ["same operator as The Ohio Motel (each site links the other "
              "as 'our Sister Motel'; identical FAQ copy)"],
}
ROWS["CLE-P3-026"] = {
    "artifact": "P3-026-bertram-inn.json",
    "supplementary_artifact": "P3-026b-bertram-inn-amenities.json",
    "outcome": "POLICY_NOT_FOUND", "candidate": False,
    "notes": ["homepage and amenities page both captured; no pet or animal "
              "wording on either."],
}
ROWS["CLE-P3-027"] = {
    "artifact": "P3-027-hotel-at-oberlin.json",
    "supplementary_artifact": "P3-027b-hotel-at-oberlin-pet-friendly.json",
    "quote_artifact": "P3-027b-hotel-at-oberlin-pet-friendly.json",
    "outcome": "AFFIRMATIVE_STRUCTURED", "candidate": True,
    "facts": [
        F("pets_allowed", True,
          "we're delighted to welcome dogs to our eco-friendly oasis in the "
          "heart of Oberlin, Ohio"),
        F("species", {"dogs": "accepted"},
          "we're delighted to welcome dogs to our eco-friendly oasis in the "
          "heart of Oberlin, Ohio",
          "the page speaks only of dogs; nothing is claimed for cats"),
        F("pet_fee", {"amount_cents": 7500, "currency": "USD",
                      "basis": "per_stay"},
          "For just $75 per stay, you can bring one dog along on your next "
          "trip to Oberlin!"),
        F("pet_count_limit", 1,
          "For just $75 per stay, you can bring one dog along on your next "
          "trip to Oberlin!"),
    ],
}
ROWS["CLE-P3-028"] = {
    "artifact": "P3-028-inn-at-amish-door.json",
    "outcome": "IDENTITY_UNCERTAIN", "candidate": False,
    "notes": ["the queued official URL is https://www.milanaballroom.com/ "
              "-- an event-venue site with no lodging or pet content; "
              "nothing on it can be bound to The Inn at Amish Door "
              "identity. Routing-review candidate."],
}
ROWS["CLE-P3-029"] = {
    "artifact": "P3-029-ohio-motel.json",
    "supplementary_artifact": "P3-029b-ohio-motel-faq.json",
    "quote_artifact": "P3-029b-ohio-motel-faq.json",
    "outcome": "NEGATIVE", "candidate": False,
    "refusal_quote": "Do you accept pets? No, sadly at this time we do not "
                     "allow pets.",
    "notes": ["same operator as Terry Point Motel (mutual 'Sister Motel' "
              "links; identical FAQ copy)"],
}
ROWS["CLE-P3-030"] = {
    "artifact": "P3-030-walden-country-inn.json",
    "supplementary_artifact": "P3-030b-walden-policies.json",
    "outcome": "POLICY_NOT_FOUND", "candidate": False,
    "notes": ["homepage and /policies both captured; no pet or animal "
              "wording on either."],
}

# ---- MARKETING_ONLY_ARTIFACT rows 031-068 ---------------------------------- #

ROWS["CLE-P3-031"] = {
    "artifact": "P3-031-best-western-plus-north-canton.json",
    "outcome": "CAPTURE_FAILED", "candidate": False,
    "notes": ["url_dead: the queued bestwestern.com property URL (code "
              "36148) lands on a hotel-search page, not a property page. "
              "Routing-review candidate. The redirect target was captured "
              "as proof."],
}
ROWS["CLE-P3-032"] = {
    "artifact": "P3-032-doubletree-akron-fairlawn.json",
    "outcome": "AFFIRMATIVE_STRUCTURED", "candidate": True,
    "facts": [
        F("pets_allowed", True, "Pets allowed Yes"),
        F("pet_fee", {"amount_cents": 10000, "currency": "USD",
                      "scope": "per_pet"},
          "Deposit Yes. $100.00 Non-refundable Fee",
          "the widget's own next line states the scope: 'Note the $100 fee "
          "is per dog'; basis (per stay vs per night) is unstated -- not "
          "invented; 'Deposit' is the Hilton template label for what the "
          "same line calls a non-refundable fee"),
        F("weight_limit", {"value": 50, "unit": "lb", "operator": "lte",
                           "scope": "per_pet"},
          "Max weight 50 lbs", WEIGHT_CONVENTION_NOTE),
        F("species", {"dogs": "accepted"},
          "Dogs only accepted."),
    ],
}
ROWS["CLE-P3-033"] = {
    "artifact": "P3-033-esa-akron-copley-east.json",
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
        F("fee_tiers",
          [{"amount_cents": 2500, "currency": "USD",
            "tax_relationship": "plus_tax", "basis": "per_night",
            "scope": "per_pet", "basis_stated": True,
            "role": "REPLACEMENT_PRICE",
            "condition_type": "stay_length_range", "condition_min": 1,
            "condition_max": 6, "boundary_unit": "nights"}],
          "There will be up to a $25 (+ tax) per day non-refundable "
          "cleaning fee for the first six (6) nights, per pet.",
          "identical brand-standard wording to ESA Select Suites Akron "
          "South; mirrors the shape the founder attested there (tier 1-6 "
          "recorded as the price; the 'up to' qualifier and the 7+ ceiling "
          "handled by the withheld entry)"),
    ],
    "withheld": [
        W("cleaning_fee", "SCHEMA_CANNOT_REPRESENT",
          "Nights seven onward carry only a not-to-exceed ceiling; the "
          "schema cannot state a ceiling as a price. Same withholding the "
          "founder attested on ESA Select Suites Akron South (Dayton ESA "
          "precedent).",
          "Each day thereafter there is a pet cleaning fee not to exceed "
          "$15 non-refundable fee (+tax) per day, per pet."),
    ],
    "notes": ["homepage JSON-LD carries petsAllowed:true (185 Montrose "
              "West Ave., 44321)"],
}

_HAMPTON_TIERS = [
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
    "pet information' line spells out -- same resolution the founder "
    "attested on Hampton Streetsboro")

ROWS["CLE-P3-034"] = {
    "artifact": "P3-034-hampton-akron-fairlawn.json",
    "outcome": "AFFIRMATIVE_STRUCTURED", "candidate": True,
    "facts": [
        F("pets_allowed", True, "Pets allowed Yes"),
        F("fee_tiers", _HAMPTON_TIERS,
          "1-4 night stay $75; 5+ night stay $125", _HILTON_TEMPLATE_NOTE),
        F("pet_count_limit", 2, "2 pets max"),
        F("species", {"dogs": "accepted", "cats": "accepted"},
          "dog or cat only"),
    ],
    "notes": ["'Max weight 0 lbs' is the Hilton template zero for an "
              "unstated limit -- never published (established Pass-2 "
              "rule)"],
}
ROWS["CLE-P3-035"] = {
    "artifact": "P3-035-hampton-akron-south.json",
    "outcome": "AFFIRMATIVE_STRUCTURED", "candidate": True,
    "facts": [
        F("pets_allowed", True, "Pets allowed Yes"),
        F("pet_fee", {"amount_cents": 12500, "currency": "USD"},
          "Deposit Yes. $125.00 Non-refundable Fee",
          "no 'Other pet information' ladder on this page; the widget "
          "amount is the only fee stated (Home2 Beachwood precedent for "
          "widget-only fees); basis and scope unstated -- not invented"),
        F("weight_limit", {"value": 75, "unit": "lb", "operator": "lte",
                           "scope": "per_pet"},
          "Max weight 75 lbs", WEIGHT_CONVENTION_NOTE),
    ],
}
ROWS["CLE-P3-036"] = {
    "artifact": "P3-036-hampton-suites-alliance.json",
    "outcome": "AFFIRMATIVE_STRUCTURED", "candidate": True,
    "facts": [
        F("pets_allowed", True, "Pets allowed Yes"),
        F("fee_tiers", _HAMPTON_TIERS,
          "1-4 night stay $75; 5+ night stay $125", _HILTON_TEMPLATE_NOTE),
        F("weight_limit", {"value": 75, "unit": "lb", "operator": "lte",
                           "scope": "per_pet"},
          "Max weight 75 lbs", WEIGHT_CONVENTION_NOTE),
        F("pet_count_limit", 2, "2 pets max"),
        F("species", {"dogs": "accepted", "cats": "accepted"},
          "dog or cat only"),
    ],
}
ROWS["CLE-P3-037"] = {
    "artifact": "P3-037-hampton-suites-beachwood.json",
    "outcome": "AFFIRMATIVE_STRUCTURED", "candidate": True,
    "facts": [
        F("pets_allowed", True, "Pets allowed Yes"),
        F("fee_tiers", _HAMPTON_TIERS,
          "1-4 night stay $75 5+ night stay $125", _HILTON_TEMPLATE_NOTE),
        F("weight_limit", {"value": 75, "unit": "lb", "operator": "lte",
                           "scope": "per_pet"},
          "Max weight 75 lbs", WEIGHT_CONVENTION_NOTE),
        F("pet_count_limit", 2, "2 pets max"),
        F("species", {"dogs": "accepted", "cats": "accepted"},
          "dog or cat only"),
    ],
}
ROWS["CLE-P3-038"] = {
    "artifact": "P3-038-hampton-suites-canton.json",
    "outcome": "AFFIRMATIVE_STRUCTURED", "candidate": True,
    "facts": [
        F("pets_allowed", True, "Pets allowed Yes"),
        F("fee_tiers", _HAMPTON_TIERS,
          "$75 1-4 nights / $125 5 or more nights", _HILTON_TEMPLATE_NOTE),
    ],
    "notes": ["no weight, count or species stated on this page"],
}
ROWS["CLE-P3-039"] = {
    "artifact": "P3-039-hampton-suites-cleveland-airport-middleburg.json",
    "outcome": "AFFIRMATIVE_STRUCTURED", "candidate": True,
    "facts": [
        F("pets_allowed", True, "Pets allowed Yes"),
        F("fee_tiers", _HAMPTON_TIERS,
          "$75(1-4n),$125(5+n) 2pets Max/dog or cat only",
          _HILTON_TEMPLATE_NOTE),
        F("weight_limit", {"value": 75, "unit": "lb", "operator": "lte",
                           "scope": "per_pet"},
          "Max weight 75 lbs", WEIGHT_CONVENTION_NOTE),
        F("pet_count_limit", 2, "2pets Max"),
        F("species", {"dogs": "accepted", "cats": "accepted"},
          "dog or cat only"),
    ],
    "notes": ["the 'Other pet information' line is operator shorthand "
              "('$75(1-4n),$125(5+n)') -- captured verbatim from the page, "
              "not transcriber prose"],
}
ROWS["CLE-P3-040"] = {
    "artifact": "P3-040-hampton-suites-cleveland-independence.json",
    "outcome": "AFFIRMATIVE_STRUCTURED", "candidate": True,
    "facts": [
        F("pets_allowed", True, "Pets allowed Yes"),
        F("fee_tiers", _HAMPTON_TIERS,
          "1-4 night stay $75; 5+ night stay $125", _HILTON_TEMPLATE_NOTE),
        F("weight_limit", {"value": 75, "unit": "lb", "operator": "lte",
                           "scope": "per_pet"},
          "Max weight 75 lbs", WEIGHT_CONVENTION_NOTE),
        F("pet_count_limit", 2, "2 pets max"),
        F("species", {"dogs": "accepted", "cats": "accepted"},
          "dog or cat only"),
    ],
}
ROWS["CLE-P3-041"] = {
    "artifact": "P3-041-hampton-cleveland-airport-tiedeman.json",
    "outcome": "AFFIRMATIVE_STRUCTURED", "candidate": True,
    "facts": [
        F("pets_allowed", True, "Pets allowed Yes"),
        F("fee_tiers", _HAMPTON_TIERS,
          "$75(1-4n),$125(5+n)", _HILTON_TEMPLATE_NOTE),
        F("combined_weight_limit",
          {"value": 75, "unit": "lb", "operator": "lte"},
          "75 lb COMBINED weight limit",
          "the page's own 'Other pet information' states COMBINED "
          "explicitly, overriding the widget's scopeless 'Max weight 75 "
          "lbs' -- Drury precedent shape; no per_pet weight_limit is "
          "proposed"),
        F("pet_count_limit", 2, "2petsMax"),
        F("species", {"dogs": "accepted", "cats": "accepted"},
          "dog/cat only"),
    ],
}
ROWS["CLE-P3-042"] = {
    "artifact": "P3-042-hampton-cleveland-downtown.json",
    "outcome": "AFFIRMATIVE_STRUCTURED", "candidate": True,
    "facts": [
        F("pets_allowed", True, "Pets allowed Yes"),
        F("pet_fee", {"amount_cents": 7500, "currency": "USD"},
          "Deposit Yes. $75.00 Non-refundable Fee",
          "no ladder on this page; widget-only fee (Home2 Beachwood "
          "precedent); basis and scope unstated -- not invented"),
        F("weight_limit", {"value": 60, "unit": "lb", "operator": "lte",
                           "scope": "per_pet"},
          "Max weight 60 lbs", WEIGHT_CONVENTION_NOTE),
    ],
}
ROWS["CLE-P3-043"] = {
    "artifact": "P3-043-hampton-massillon.json",
    "outcome": "AFFIRMATIVE_STRUCTURED", "candidate": True,
    "facts": [
        F("pets_allowed", True, "Pets allowed Yes"),
        F("fee_tiers", _HAMPTON_TIERS,
          "$75(1-4n),$125(5+n)", _HILTON_TEMPLATE_NOTE),
        F("weight_limit", {"value": 75, "unit": "lb", "operator": "lte",
                           "scope": "per_pet"},
          "Max weight 75 lbs", WEIGHT_CONVENTION_NOTE),
        F("pet_count_limit", 2, "2petsMax"),
        F("species", {"dogs": "accepted", "cats": "accepted"},
          "dog/cat onl",
          "the page's own line truncates to 'dog/cat onl' -- quoted "
          "verbatim; the species reading is 'dog/cat only'"),
    ],
}
ROWS["CLE-P3-044"] = {
    "artifact": "P3-044-hampton-north-olmsted.json",
    "outcome": "AFFIRMATIVE_STRUCTURED", "candidate": True,
    "facts": [
        F("pets_allowed", True, "Pets allowed Yes"),
        F("pet_fee", {"amount_cents": 7500, "currency": "USD"},
          "Deposit Yes. $75.00 Non-refundable Fee",
          "no ladder on this page; widget-only fee (Home2 Beachwood "
          "precedent); basis and scope unstated -- not invented"),
        F("weight_limit", {"value": 75, "unit": "lb", "operator": "lte",
                           "scope": "per_pet"},
          "Max weight 75 lbs", WEIGHT_CONVENTION_NOTE),
    ],
}
ROWS["CLE-P3-045"] = {
    "artifact": "P3-045-hampton-stow.json",
    "outcome": "AFFIRMATIVE_STRUCTURED", "candidate": True,
    "facts": [
        F("pets_allowed", True, "Pets allowed Yes"),
        F("fee_tiers",
          [{"amount_cents": 7500, "currency": "USD", "basis": "per_night",
            "basis_stated": True, "condition_type": "stay_length_range",
            "boundary_unit": "nights", "condition_min": 1,
            "condition_max": 4, "role": "REPLACEMENT_PRICE"},
           {"amount_cents": 12500, "currency": "USD", "basis": "per_night",
            "basis_stated": True, "condition_type": "stay_length_range",
            "boundary_unit": "nights", "condition_min": 5,
            "role": "REPLACEMENT_PRICE"}],
          "Pet fee $75/night 1-4 nights, $125/night 5+ nights.",
          "UNLIKE every sibling Hampton this page states the basis as PER "
          "NIGHT ('$75/night'); the tiers carry basis per_night, "
          "basis_stated true -- founder should confirm this outlier "
          "before publication"),
        F("weight_limit", {"value": 75, "unit": "lb", "operator": "lte",
                           "scope": "per_pet"},
          "Max weight 75 lbs", WEIGHT_CONVENTION_NOTE),
        F("pet_count_limit", 2, "2 pet max, dogs and cats only."),
        F("species", {"dogs": "accepted", "cats": "accepted"},
          "dogs and cats only"),
    ],
}
ROWS["CLE-P3-046"] = {
    "artifact": "P3-046-hampton-westlake.json",
    "outcome": "AFFIRMATIVE_STRUCTURED", "candidate": True,
    "facts": [
        F("pets_allowed", True, "Pets allowed Yes"),
        F("fee_tiers", _HAMPTON_TIERS,
          "1-4 night stay $75; 5+ night stay $125", _HILTON_TEMPLATE_NOTE),
        F("pet_count_limit", 2, "2 pets max"),
        F("species", {"dogs": "accepted", "cats": "accepted"},
          "dog or cat only"),
    ],
    "notes": ["no weight stated on this page"],
}
ROWS["CLE-P3-047"] = {
    "artifact": "P3-047-hilton-cleveland-downtown.json",
    "outcome": "AFFIRMATIVE_STRUCTURED", "candidate": True,
    "facts": [
        F("pets_allowed", True, "Pets allowed Yes"),
        F("weight_limit", {"value": 125, "unit": "lb", "operator": "lte",
                           "scope": "per_pet"},
          "Max weight 125 lbs", WEIGHT_CONVENTION_NOTE),
        F("pet_count_limit", 2, "2 pets max."),
        F("species", {"dogs": "accepted", "cats": "accepted"},
          "Dog/cat only."),
    ],
    "withheld": [
        W("pet_fee", "CONTRADICTORY",
          "The widget states a $75 non-refundable fee while the same "
          "page's 'Other pet information' states $81 (1-4 nights) / $135 "
          "(5+ nights); the two amounts cannot both be the price and the "
          "page states no relationship between them.",
          "$81 (1-4 night stays), $135 (5+ night stays). 2 pets max."),
    ],
    "notes": ["the contradicting widget line reads 'Deposit Yes. $75.00 "
              "Non-refundable Fee' -- both quotes verified in the "
              "artifact"],
}
ROWS["CLE-P3-048"] = {
    "artifact": "P3-048-hilton-garden-inn-akron.json",
    "outcome": "AFFIRMATIVE_STRUCTURED", "candidate": True,
    "facts": [
        F("pets_allowed", True, "Pets allowed Yes"),
        F("fee_tiers", _HAMPTON_TIERS,
          "1-4 night $75, 5+ night $125", _HILTON_TEMPLATE_NOTE),
        F("weight_limit", {"value": 75, "unit": "lb", "operator": "lte",
                           "scope": "per_pet"},
          "Max weight 75 lbs", WEIGHT_CONVENTION_NOTE),
        F("pet_count_limit", 2, "up to 2 pets"),
        F("species", {"dogs": "accepted", "cats": "accepted"},
          "Dogs and cats"),
        F("reservation_requirement",
          "pet fee charged upon check in",
          "pet fee charged upon check in"),
    ],
}

ROWS["CLE-P3-049"] = {
    "artifact": None, "outcome": "ACCESS_BLOCKED", "candidate": False,
    "notes": [HILTON_BLOCK_NOTE],
}
ROWS["CLE-P3-050"] = {
    "artifact": "P3-050-hilton-garden-inn-cleveland-airport.json",
    "outcome": "AFFIRMATIVE_STRUCTURED", "candidate": True,
    "facts": [
        F("pets_allowed", True, "Pets allowed Yes"),
        F("fee_tiers",
          [{"amount_cents": 5000, "currency": "USD",
            "condition_type": "stay_length_range", "boundary_unit":
            "nights", "basis_stated": False, "condition_min": 1,
            "condition_max": 4, "role": "REPLACEMENT_PRICE"},
           {"amount_cents": 7500, "currency": "USD",
            "condition_type": "stay_length_range", "boundary_unit":
            "nights", "basis_stated": False, "condition_min": 5,
            "role": "REPLACEMENT_PRICE"}],
          "1-4 night stay $50; 5+ night stay $75",
          "a $50/$75 ladder -- NOT the $75/$125 Hampton standard; the "
          "widget's 'Deposit Yes. $50.00 Non-refundable Fee' is tier one "
          "under the same template resolution"),
        F("pet_count_limit", 2, "2 pets max"),
        F("species", {"dogs": "accepted", "cats": "accepted"},
          "dog or cat only"),
    ],
    "notes": ["no weight stated on this page"],
}
ROWS["CLE-P3-051"] = {
    "artifact": "P3-051-hilton-garden-inn-cleveland-east-mayfield-village"
                ".json",
    "outcome": "AFFIRMATIVE_STRUCTURED", "candidate": True,
    "facts": [
        F("pets_allowed", True, "Pets allowed Yes"),
        F("fee_tiers", _HAMPTON_TIERS,
          "$75 per 1-4 Nights, $125 for 5+ Nights.",
          _HILTON_TEMPLATE_NOTE),
        F("weight_limit", {"value": 75, "unit": "lb", "operator": "lte",
                           "scope": "per_pet"},
          "Max weight 75 lbs", WEIGHT_CONVENTION_NOTE),
        F("pet_count_limit", 2, "Max 2 Pets, Cats and Dogs Only."),
        F("species", {"dogs": "accepted", "cats": "accepted"},
          "Cats and Dogs Only."),
    ],
}
ROWS["CLE-P3-052"] = {
    "artifact": "P3-052-hilton-garden-inn-cleveland-twinsburg.json",
    "outcome": "AFFIRMATIVE_STRUCTURED", "candidate": True,
    "facts": [
        F("pets_allowed", True, "Pets allowed Yes"),
        F("fee_tiers", _HAMPTON_TIERS,
          "$75 1-4 nights/$125 5+ nights", _HILTON_TEMPLATE_NOTE),
        F("pet_count_limit", 2, "2 pets max"),
    ],
    "notes": ["no weight or species stated on this page"],
}
ROWS["CLE-P3-053"] = {
    "artifact": "P3-053-hilton-garden-inn-downtown-cleveland.json",
    "outcome": "AFFIRMATIVE_STRUCTURED", "candidate": True,
    "facts": [
        F("pets_allowed", True, "Pets allowed Yes"),
        F("pet_fee", {"amount_cents": 7500, "currency": "USD"},
          "Deposit Yes. $75.00 Non-refundable Fee",
          "no ladder on this page; widget-only fee (Home2 Beachwood "
          "precedent); basis and scope unstated -- not invented"),
        F("weight_limit", {"value": 75, "unit": "lb", "operator": "lte",
                           "scope": "per_pet"},
          "Max weight 75 lbs", WEIGHT_CONVENTION_NOTE),
        F("pet_count_limit", 2,
          "No more than (2) Cats/Dogs permitted."),
        F("species", {"dogs": "accepted", "cats": "accepted"},
          "No more than (2) Cats/Dogs permitted."),
    ],
}
ROWS["CLE-P3-055"] = {
    "artifact": "P3-055-home2-suites-canton.json",
    "outcome": "AFFIRMATIVE_STRUCTURED", "candidate": True,
    "facts": [
        F("pets_allowed", True, "Pets allowed Yes"),
        F("fee_tiers", _HAMPTON_TIERS,
          "$75(1-4n), $125(5+n)", _HILTON_TEMPLATE_NOTE),
        F("pet_count_limit", 2, "2pets Max"),
        F("species", {"dogs": "accepted", "cats": "accepted"},
          "dog/cat only"),
    ],
    "notes": ["no weight stated on this page"],
}
ROWS["CLE-P3-056"] = {
    "artifact": "P3-056-home2-suites-stow-akron.json",
    "outcome": "AFFIRMATIVE_STRUCTURED", "candidate": True,
    "facts": [
        F("pets_allowed", True, "Pets allowed Yes"),
        F("fee_tiers", _HAMPTON_TIERS,
          "1-4 night stay $75; 5+ night stay $125",
          "the widget label reads 'Deposit Yes. $125.00 Non-refundable "
          "Fee' -- the TIER-TWO amount -- while the ladder line states "
          "$75/$125; the ladder governs per the Streetsboro resolution "
          "and the label inconsistency is noted for the founder"),
        F("weight_limit", {"value": 75, "unit": "lb", "operator": "lte",
                           "scope": "per_pet"},
          "Max weight 75 lbs", WEIGHT_CONVENTION_NOTE),
        F("pet_count_limit", 2, "2 pets max"),
        F("species", {"dogs": "accepted", "cats": "accepted"},
          "dog or cat only"),
    ],
}
ROWS["CLE-P3-057"] = {
    "artifact": "P3-057-homewood-suites-solon.json",
    "outcome": "AFFIRMATIVE_STRUCTURED", "candidate": True,
    "facts": [
        F("pets_allowed", True, "Pets allowed Yes"),
        F("fee_tiers", _HAMPTON_TIERS,
          "$75(1-4n)$125(5+n)",
          "the widget label reads 'Deposit Yes. $125.00 Non-refundable "
          "Fee' -- the TIER-TWO amount -- while the ladder line states "
          "$75/$125; the ladder governs per the Streetsboro resolution "
          "and the label inconsistency is noted for the founder"),
        F("pet_count_limit", 2, "2petsMax,dog/cat only"),
        F("species", {"dogs": "accepted", "cats": "accepted"},
          "dog/cat only"),
    ],
    "notes": ["no weight stated on this page"],
}
ROWS["CLE-P3-058"] = {
    "artifact": "P3-058-homewood-suites-akron-fairlawn.json",
    "outcome": "AFFIRMATIVE_STRUCTURED", "candidate": True,
    "facts": [
        F("pets_allowed", True, "Pets allowed Yes"),
        F("fee_tiers", _HAMPTON_TIERS,
          "$75(1-4n), $125(5+n)", _HILTON_TEMPLATE_NOTE),
        F("weight_limit", {"value": 75, "unit": "lb", "operator": "lte",
                           "scope": "per_pet"},
          "Max weight 75 lbs", WEIGHT_CONVENTION_NOTE),
        F("pet_count_limit", 2, "2petsMax"),
        F("species", {"dogs": "accepted", "cats": "accepted"},
          "dog/cat only"),
    ],
}
ROWS["CLE-P3-059"] = {
    "artifact": "P3-059b-homewood-suites-cleveland-beachwood.json",
    "supplementary_artifact": "P3-059-homewood-suites-cleveland-beachwood"
                              ".json",
    "outcome": "AFFIRMATIVE_STRUCTURED", "candidate": True,
    "facts": [
        F("pets_allowed", True, "Pets allowed Yes"),
        F("fee_tiers", _HAMPTON_TIERS,
          "1-4 night stay $75; 5+ night stay $125", _HILTON_TEMPLATE_NOTE),
        F("weight_limit", {"value": 75, "unit": "lb", "operator": "lte",
                           "scope": "per_pet"},
          "Max weight 75 lbs", WEIGHT_CONVENTION_NOTE),
        F("pet_count_limit", 2, "2 pets max"),
        F("species", {"dogs": "accepted", "cats": "accepted"},
          "dog or cat only"),
    ],
}

ROWS["CLE-P3-054"] = {
    "artifact": "P3-054-home2suites-brand.json",
    "outcome": "POLICY_NOT_FOUND", "candidate": False,
    "notes": ["the queued official URL is the brand homepage "
              "(home2suites.com -> hilton.com/en/brands/home2-suites/); no "
              "property-level policy surface can exist at this URL. The "
              "brand page's pet text ('We welcome wagging tails ... *Fees "
              "apply and vary by hotel') is PT4 brand marketing, never "
              "property policy. Discovery-lane candidate: the identity "
              "needs a property-level URL (6200 Patriots Way, "
              "Independence)."],
}
ROWS["CLE-P3-060"] = {
    "artifact": "P3-060-knights-inn-macedonia.json",
    "supplementary_artifact": "P3-060b-knights-inn-macedonia-amenities.json",
    "outcome": "AFFIRMATIVE_PARTIAL", "candidate": True,
    "facts": [
        F("pets_allowed", True, "Pet Friendly",
          "the property page's own amenity row, present in both captures; "
          "no fee, count, weight or species stated anywhere on the "
          "property site"),
    ],
    "notes": ["property-level marketing chip only; founder precedent P17 "
              "(Pass 2) published pets_allowed alone for exactly this "
              "shape"],
}
ROWS["CLE-P3-061"] = {
    "artifact": "P3-061-la-quinta-cleveland-airport-west.json",
    "outcome": "IDENTITY_UNCERTAIN", "candidate": False,
    "notes": ["the queued URL serves 'La Quinta Inn & Suites by Wyndham "
              "Cleveland Airport West' at 25105 Country Club Blvd, North "
              "Olmsted 44070, phone 440-734-4477 -- while the queue "
              "identity is La Quinta Inn & Suites Cleveland Airport NORTH "
              "at 4222 West 150th St, Cleveland 44135, phone 216.251.8500. "
              "Zero identity signals bind (different street, ZIP and "
              "phone). This is a different property; routing-review "
              "candidate. The page's own policy (2 pets max, cats and "
              "dogs, 75lbs per pet, $25 nightly / max $75 per stay) "
              "belongs to Airport West and is NOT proposed for this "
              "identity."],
}
ROWS["CLE-P3-062"] = {
    "artifact": "P3-062-la-quinta-independence.json",
    "outcome": "AFFIRMATIVE_STRUCTURED", "candidate": True,
    "facts": [
        F("pets_allowed", True,
          "Pets Allowed - 2 pets max. Cats and dogs only. 75lbs or less "
          "per pet."),
        F("pet_count_limit", 2, "2 pets max."),
        F("species", {"dogs": "accepted", "cats": "accepted"},
          "Cats and dogs only."),
        F("weight_limit", {"value": 75, "unit": "lb", "operator": "lte",
                           "scope": "per_pet"},
          "75lbs or less per pet."),
        F("pet_fee", {"amount_cents": 2500, "currency": "USD",
                      "basis": "per_night", "scope": "per_room"},
          "Fees - Non-refundable 25 USD nightly for up to 2 pets.",
          "'nightly for up to 2 pets' prices the room's pets together; "
          "per_room follows the Wyndham Independence precedent the "
          "founder attested"),
        F("service_animal_statement",
          {"stated": True, "charges_stated": "no_charge"},
          "Service Animals - ADA-defined service animals are welcome free "
          "of charge."),
    ],
    "withheld": [
        W("pet_fee_cap", "SCHEMA_CANNOT_REPRESENT",
          "The nightly fee carries a per-stay cap ('Max 75 USD per stay') "
          "and the schema can only attach a cap inside fee_pet_schedule, "
          "which this flat nightly fee does not use; founder rules the "
          "representation.",
          "Max 75 USD per stay."),
    ],
}
ROWS["CLE-P3-063"] = {
    "artifact": "P3-063-staybridge-stow.json",
    "supplementary_artifact": "P3-063b-staybridge-stow-faq.json",
    "outcome": "AFFIRMATIVE_STRUCTURED", "candidate": True,
    "facts": [
        F("pets_allowed", True,
          "Pets are welcome at Staybridge Suites Akron-Stow-Cuyahoga "
          "Falls."),
        F("weight_limit", {"value": 80, "unit": "lb", "operator": "lt",
                           "scope": "per_pet"},
          "Each pet must weigh less than 80lbs.",
          "'less than' is exclusive: operator lt, per the page's own "
          "words"),
        F("fee_tiers",
          [{"amount_cents": 7500, "currency": "USD",
            "condition_type": "stay_length_range", "boundary_unit":
            "nights", "basis_stated": False, "condition_min": 1,
            "condition_max": 6, "role": "REPLACEMENT_PRICE"}],
          "75 dollar fee for 1 to 6 nights",
          "tier one is stated cleanly; the upper tier is withheld for the "
          "boundary garble"),
        F("general_restrictions",
          "Pet agreement must be signed at check in. Record of complete "
          "and up to date vaccinations required.",
          "Pet agreement must be signed at check in. Record of complete "
          "and up to date vaccinations required.",
          "vaccination requirement follows the Indigo Beachwood "
          "general_restrictions precedent"),
    ],
    "withheld": [
        W("fee_tiers_upper", "SOURCE_AMBIGUOUS",
          "The upper tier reads 'for more than 7 nights', which read "
          "literally leaves night seven priced by neither tier; the "
          "boundary is garbled and inventing one would assert a price the "
          "page never states.",
          "150 dollar fee for more than 7 nights"),
        W("pet_deposit", "CONTRADICTORY",
          "The same FAQ answer calls the charge a per-stay deposit and, "
          "one sentence later, a nonrefundable fee ('Pets allowed with "
          "nonrefundable fee'); a deposit that is nonrefundable is not a "
          "deposit, and the page states no reconciliation. Same IHG "
          "template conflict the corpus already withholds elsewhere.",
          "There is a pet deposit per stay of 75 USD"),
    ],
    "notes": ["the FAQ answer lives in an aria-hidden accordion region; "
              "quotes verify against the captured HTML, which retains it"],
}
ROWS["CLE-P3-064"] = {
    "artifact": "P3-064-staybridge-canton.json",
    "outcome": "AFFIRMATIVE_STRUCTURED", "candidate": True,
    "facts": [
        F("pets_allowed", True,
          "Pets are welcome at Staybridge Suites Canton."),
        F("weight_limit", {"value": 80, "unit": "lb", "operator": "lt",
                           "scope": "per_pet"},
          "Each pet must weigh less than 80lbs.",
          "'less than' is exclusive: operator lt"),
        F("fee_tiers",
          [{"amount_cents": 12500, "currency": "USD",
            "condition_type": "stay_length_range", "boundary_unit":
            "nights", "basis_stated": False, "condition_min": 1,
            "condition_max": 6, "role": "REPLACEMENT_PRICE"}],
          "Pets fee is nonrefundable 125 for 1 to 6 nights",
          "tier one is stated cleanly; the upper tier is withheld for the "
          "boundary garble"),
        F("general_restrictions",
          "Pet agreement must be signed at check in. Record of complete "
          "up to date vaccinations required.",
          "Pet agreement must be signed at check in. Record of complete "
          "up to date vaccinations required."),
    ],
    "withheld": [
        W("fee_tiers_upper", "SOURCE_AMBIGUOUS",
          "The upper tier reads '200.00 for 7 nights', which states a "
          "price for exactly seven nights and none for eight or more; the "
          "boundary is garbled and inventing '7 or more' would assert "
          "wording the page does not carry.",
          "200.00 for 7 nights"),
    ],
    "notes": ["the FAQ answer lives in an aria-hidden accordion region; "
              "quotes verify against the captured HTML, which retains it"],
}
ROWS["CLE-P3-065"] = {
    "artifact": "P3-065-staybridge-mayfield-heights.json",
    "outcome": "AFFIRMATIVE_STRUCTURED", "candidate": True,
    "facts": [
        F("pets_allowed", True,
          "Pets are welcome at Staybridge Suites Cleveland Mayfield Hts "
          "Beachwd."),
        F("general_restrictions",
          "A pet agreement must be signed at check in",
          "A pet agreement must be signed at check in"),
    ],
    "withheld": [
        W("fee_tiers", "CONTRADICTORY",
          "The page states the ladder twice with different boundaries: "
          "the FAQ says $75 'for under 6 nights' (excluding six) while "
          "the marketing section says $75 'for up to six nights' "
          "(including six); the amounts agree but a six-night stay is "
          "priced differently by the two statements and the page states "
          "no reconciliation.",
          "a non refundable pet fee of 75.00 dollars for under 6 nights "
          "and 150.00 dollars for 7 or more nights"),
        W("pet_deposit", "CONTRADICTORY",
          "The same FAQ answer calls the charge a per-stay deposit and "
          "then a non refundable pet fee; a deposit that is nonrefundable "
          "is not a deposit, and the page states no reconciliation. Same "
          "IHG template conflict as the Stow sibling.",
          "There is a pet deposit per stay of 75 USD"),
    ],
    "notes": ["the conflicting marketing sentence reads 'a minimal fee of "
              "$75 for up to six nights and $150 for seven or more "
              "nights' -- both quotes verified in the artifact",
              "the FAQ answer lives in an aria-hidden accordion region; "
              "quotes verify against the captured HTML, which retains it"],
}
ROWS["CLE-P3-066"] = {
    "artifact": "P3-066-super-8-akron-s-green-uniontown.json",
    "outcome": "AFFIRMATIVE_STRUCTURED", "candidate": True,
    "facts": [
        F("pets_allowed", True,
          "2 Pets allowed at a non-refundable charge of 20.00 USD per "
          "night."),
        F("pet_count_limit", 2,
          "2 Pets allowed at a non-refundable charge of 20.00 USD per "
          "night."),
        F("pet_fee", {"amount_cents": 2000, "currency": "USD",
                      "basis": "per_night"},
          "2 Pets allowed at a non-refundable charge of 20.00 USD per "
          "night.",
          "scope (per pet vs per room) unstated -- not invented"),
        F("weight_limit", {"value": 20, "unit": "lb", "operator": "lte",
                           "scope": "per_pet"},
          "Maximum weight 20 LBS.", WEIGHT_CONVENTION_NOTE),
        F("species", {"cats": "refused"},
          "Sorry no cats are allowed.",
          "the page refuses cats explicitly and never names an accepted "
          "species; dogs are NOT inferred"),
        F("unattended_policy",
          "Pet must be crated if left unattended in room.",
          "Pet must be crated if left unattended in room."),
        F("general_restrictions",
          "200.00 USD pet sanitation fee if applicable.",
          "200.00 USD pet sanitation fee if applicable.",
          "a contingent penalty, not a price -- general_restrictions per "
          "the Comfort Inn Canton penalty precedent"),
        F("service_animal_statement",
          {"stated": True, "charges_stated": "not_addressed"},
          "ADA defined service animals are also welcome at this hotel."),
    ],
}
ROWS["CLE-P3-067"] = {
    "artifact": "P3-067-super-8-richfield-cleveland.json",
    "outcome": "AFFIRMATIVE_STRUCTURED", "candidate": True,
    "facts": [
        F("pets_allowed", True, "Pets Allowed. 2 pets max."),
        F("pet_count_limit", 2, "2 pets max."),
        F("pet_fee", {"amount_cents": 1500, "currency": "USD",
                      "basis": "per_night", "scope": "per_pet"},
          "Fees - 15USD per pet per night."),
        F("service_animal_statement",
          {"stated": True, "charges_stated": "not_addressed"},
          "Service Animals - ADA-defined service animals welcome."),
    ],
    "withheld": [
        W("weight_limit", "SCHEMA_CANNOT_REPRESENT",
          "The page states there is NO maximum weight limit; the schema "
          "has no representation for an explicit no-limit, and publishing "
          "nothing would misread the page as silent.",
          "there is no maximum weight limit"),
    ],
    "notes": ["'hotel does not charge a pet sanitation fee' is an explicit "
              "none-charged statement, recorded here (no schema field "
              "exists for stated-none sanitation fees)"],
}
ROWS["CLE-P3-068"] = {
    "artifact": "P3-068-woodspring-brand.json",
    "outcome": "POLICY_NOT_FOUND", "candidate": False,
    "notes": ["the queued official URL is the WoodSpring brand homepage; "
              "no property-level policy surface can exist at this URL. "
              "The brand page's pet text ('We offer pet friendly hotel "
              "rooms at most of our locations') is PT4 brand marketing, "
              "never property policy. Discovery-lane candidate: the "
              "identity needs a property-level URL (20829 Emerald Pkwy, "
              "44135)."],
}

# --------------------------------------------------------------------------- #
# Hyatt operator-manual instructions (ADR-forbidden surfaces; never driven).
# --------------------------------------------------------------------------- #

HYATT_MANUAL = [
    OrderedDict([
        ("identity_key", "hyatt regency"),
        ("hotel", "Hyatt Regency Cleveland at The Arcade"),
        ("open_url", "https://cleveland.regency.hyatt.com"),
        ("targets", [
            "the property page's Policies / 'Hotel Policies' section",
            "any 'Pet Policy' or pet FAQ entry (expand it before shooting)",
        ]),
        ("instructions",
         "Sign in to nothing; browse as a guest in your own Chrome. Open "
         "the URL, accept no marketing prompts, open the policies section, "
         "and take full-window screenshots that show (1) the browser "
         "address bar with the hyatt.com URL, (2) the property name, and "
         "(3) the complete pet wording including any fee, count, weight "
         "and service-animal sentences. One screenshot per policy "
         "surface; do not crop. Save as PNG with today's date in the "
         "filename."),
    ]),
    OrderedDict([
        ("identity_key", "hyatt place cleveland lyndhurst legacy village"),
        ("hotel", "Hyatt Place Cleveland/Lyndhurst/Legacy Village"),
        ("open_url",
         "https://clevelandlyndhurst.place.hyatt.com/en/hotel/home.html"),
        ("targets", [
            "the property page's Policies / 'Hotel Policies' section",
            "any 'Pet Policy' or pet FAQ entry (expand it before shooting)",
        ]),
        ("instructions",
         "Same procedure as the Regency: guest browsing, full-window "
         "screenshots showing address bar, property name, and the "
         "complete pet wording; one per surface; no crops; PNG with "
         "date."),
    ]),
    OrderedDict([
        ("identity_key", "hyatt place cleveland westlake crocker park"),
        ("hotel", "Hyatt Place Cleveland/Westlake/Crocker Park"),
        ("open_url", "https://hyattplaceclevelandwestlake.com"),
        ("targets", [
            "confirm where the vanity domain lands (it should forward to "
            "a hyatt.com property page -- the landing URL itself is the "
            "routing evidence this identity needs)",
            "the landing page's Policies section and pet wording, if the "
            "domain resolves to a property page",
        ]),
        ("instructions",
         "This identity is AWAITING_ROUTING_REVIEW: shoot the address bar "
         "BEFORE and AFTER the vanity domain settles, then the policies "
         "section as with the others. If the domain parks or errors, one "
         "screenshot of that outcome is the finding."),
    ]),
]

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


def speed_benchmark(captured_ats: List[str]) -> Dict:
    start_epoch = int(START_EPOCH_PATH.read_text().strip()) \
        if START_EPOCH_PATH.is_file() else None
    stamps = sorted(
        datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
        for ts in captured_ats if ts)
    if not stamps:
        return {"available": False}
    gaps = [b - a for a, b in zip(stamps, stamps[1:])]
    first, last = stamps[0], stamps[-1]
    elapsed = (last - start_epoch) if start_epoch else (last - first)
    bench = OrderedDict([
        ("available", True),
        ("start_epoch", start_epoch),
        ("first_capture_utc", datetime.fromtimestamp(
            first, timezone.utc).isoformat()),
        ("last_capture_utc", datetime.fromtimestamp(
            last, timezone.utc).isoformat()),
        ("session_elapsed_seconds", round(elapsed)),
        ("captures", len(stamps)),
        ("mean_seconds_per_capture",
         round(elapsed / len(stamps), 1)),
        ("median_inter_capture_gap_seconds",
         round(statistics.median(gaps), 1) if gaps else None),
        ("captures_per_hour", round(len(stamps) / (elapsed / 3600.0), 1)),
        ("note", "elapsed runs from the recorded session start epoch to "
                 "the last capture; the Hilton cool-down waits and the "
                 "adjudication work between captures are inside it, so "
                 "the per-capture mean is a whole-session figure, not a "
                 "page-drive figure. The median inter-capture gap is the "
                 "honest page-drive pace."),
    ])
    return bench


# --------------------------------------------------------------------------- #
# Assembly.
# --------------------------------------------------------------------------- #

def run(data_root: Path, apply: bool) -> Dict:
    raw_dir = data_root / RAW_REL
    queue = load_json(QUEUE_PATH)
    queue_rows = {r["queue_id"]: r for r in queue["rows"]}
    if len(queue_rows) != 68:
        raise SystemExit("STOP: queue does not carry 68 rows")
    if set(queue_rows) != set(ROWS):
        raise SystemExit("STOP: adjudication table does not cover the "
                         "queue exactly once")

    results: List[Dict] = []
    packet_positive: List[Dict] = []
    packet_negative: List[Dict] = []
    routing_observations: List[Dict] = []
    counts: Dict[str, int] = {}
    captured_ats: List[str] = []

    for qid in sorted(ROWS):
        spec = ROWS[qid]
        queue_row = queue_rows[qid]
        outcome = spec["outcome"]
        counts[outcome] = counts.get(outcome, 0) + 1
        row = OrderedDict([
            ("queue_id", qid),
            ("group", queue_row["group"]),
            ("hotel", queue_row["name"]),
            ("identity_key", queue_row["identity_key"]),
            ("prior_state", queue_row["prior_state"]),
            ("outcome", outcome),
        ])
        if spec.get("artifact"):
            path = raw_dir / spec["artifact"]
            doc = load_json(path)
            integrity = verify_capture(doc)
            binding = identity_binding(queue_row, doc)
            method = spec.get("capture_method",
                              doc.get("capture_method", "attended_browser"))
            captured_ats.append(doc.get("captured_at"))
            row.update([
                ("artifact_file", spec["artifact"]),
                ("artifact_bytes", path.stat().st_size),
                ("artifact_file_sha256",
                 hashlib.sha256(path.read_bytes()).hexdigest()),
                ("html_sha256", integrity["html_sha256"]),
                ("text_sha256", integrity["text_sha256"]),
                ("content_hashes_agree",
                 integrity["html_agrees"] and integrity["text_agrees"]),
                ("captured_at", doc.get("captured_at")),
                ("capture_method", method),
                ("final_url", doc.get("final_url")),
                ("identity_binding", binding),
            ])
            if spec.get("supplementary_artifact"):
                sup_path = raw_dir / spec["supplementary_artifact"]
                sup_doc = load_json(sup_path)
                sup_integrity = verify_capture(sup_doc)
                if not (sup_integrity["html_agrees"]
                        and sup_integrity["text_agrees"]):
                    raise AssertionError("%s: supplementary capture "
                                         "integrity failure" % qid)
                captured_ats.append(sup_doc.get("captured_at"))
                row["supplementary_artifact"] = OrderedDict([
                    ("artifact_file", spec["supplementary_artifact"]),
                    ("artifact_file_sha256", hashlib.sha256(
                        sup_path.read_bytes()).hexdigest()),
                    ("html_sha256", sup_integrity["html_sha256"]),
                    ("final_url", sup_doc.get("final_url")),
                ])
            if not (integrity["html_agrees"] and integrity["text_agrees"]):
                raise AssertionError("%s: capture integrity failure" % qid)

            quote_doc, quote_meta = doc, None
            if spec.get("quote_artifact"):
                qa_path = raw_dir / spec["quote_artifact"]
                quote_doc = load_json(qa_path)
                quote_meta = OrderedDict([
                    ("artifact_file", spec["quote_artifact"]),
                    ("artifact_sha256", "sha256:%s"
                     % verify_capture(quote_doc)["html_sha256"]),
                    ("source_url", quote_doc.get("final_url")),
                    ("captured_at", quote_doc.get("captured_at")),
                ])

            if outcome == "NEGATIVE":
                where = quote_backed(spec["refusal_quote"], quote_doc)
                if where == "MISSING":
                    raise AssertionError("%s: refusal quote not in capture"
                                         % qid)
                row["refusal_quote"] = spec["refusal_quote"]
                row["quote_backed_by"] = where
                packet_negative.append(OrderedDict([
                    ("queue_id", qid),
                    ("hotel", queue_row["name"]),
                    ("identity_key", queue_row["identity_key"]),
                    ("proposed_state", "VERIFIED_NO_PETS"),
                    ("refusal_quote", spec["refusal_quote"]),
                    ("source_url", quote_doc.get("final_url")),
                    ("artifact_file", spec.get("quote_artifact")
                     or spec["artifact"]),
                    ("artifact_sha256", "sha256:%s"
                     % verify_capture(quote_doc)["html_sha256"]),
                    ("artifact_kind", "rendered_html"),
                    ("captured_at", quote_doc.get("captured_at")),
                    ("identity_binding", binding),
                    ("notes", spec.get("notes", [])),
                    ("recommendation", "APPROVE_VERIFIED_NO_PETS"),
                ]))
            if spec.get("candidate"):
                checked = []
                for fact in spec.get("facts", []):
                    where = quote_backed(fact["quote"], quote_doc)
                    if where == "MISSING" and quote_doc is not doc:
                        where = quote_backed(fact["quote"], doc)
                    if where == "MISSING":
                        raise AssertionError(
                            "%s: quote %r not carried by the capture"
                            % (qid, fact["quote"][:60]))
                    fact = OrderedDict(fact)
                    fact["quote_backed_by"] = where
                    checked.append(fact)
                for withheld in spec.get("withheld", []):
                    where = quote_backed(withheld["quote"], quote_doc)
                    if where == "MISSING" and quote_doc is not doc:
                        where = quote_backed(withheld["quote"], doc)
                    if where == "MISSING":
                        raise AssertionError(
                            "%s: withheld quote %r not carried by the "
                            "capture" % (qid, withheld["quote"][:60]))
                packet_positive.append(OrderedDict([
                    ("queue_id", qid),
                    ("hotel", queue_row["name"]),
                    ("identity_key", queue_row["identity_key"]),
                    ("outcome", outcome),
                    ("source_url", (quote_doc or doc).get("final_url")),
                    ("artifact_file", spec.get("quote_artifact")
                     or spec["artifact"]),
                    ("artifact_sha256", "sha256:%s"
                     % verify_capture(quote_doc)["html_sha256"]),
                    ("artifact_kind", "rendered_html"),
                    ("captured_at", (quote_doc or doc).get("captured_at")),
                    ("capture_method", method),
                    ("source_grade", enums.GRADE_PT1_FIRST_PARTY),
                    ("identity_binding", binding),
                    ("quote_source", quote_meta),
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
        if outcome in ("CAPTURE_FAILED", "IDENTITY_UNCERTAIN"):
            routing_observations.append(OrderedDict([
                ("queue_id", qid),
                ("identity_key", queue_row["identity_key"]),
                ("hotel", queue_row["name"]),
                ("queued_url", queue_row["official_url"]),
                ("observed", (spec.get("notes") or [""])[0]),
            ]))
        if spec.get("notes"):
            row["notes"] = spec["notes"]
        results.append(row)

    bench = speed_benchmark(captured_ats)

    ledger = OrderedDict([
        ("schema", "ptf-cleveland-pass3-capture-results/1.0"),
        ("work_order", WORK_ORDER),
        ("as_of", PASS_DATE),
        ("market_id", MARKET),
        ("captured_by", AGENT_IDENTITY),
        ("capture_method",
         "attended browser (operator's Chrome, extension-driven); rendered "
         "HTML and page text retained as bytes in the gitignored worker "
         "tree at data/%s; committed output is hashes and verdicts only, "
         "because captured brand pages embed third-party credentials and "
         "are never committed. One artifact (P3-012) is a deterministic "
         "fetch; its row says why." % RAW_REL.as_posix()),
        ("rows_total", 68),
        ("rows_captured", sum(1 for r in results if r.get("artifact_file"))),
        ("rows_not_driven", [qid for qid, s in ROWS.items()
                             if not s.get("artifact")]),
        ("outcome_counts", OrderedDict(sorted(counts.items()))),
        ("speed_benchmark", bench),
        ("rule",
         "A failed, blocked or misrouted capture is never negative "
         "evidence; a refusal is proposed only where the property's own "
         "page states it; no fact is proposed without its exact quote "
         "verified against the retained artifact bytes; no authority file "
         "changes in this pass."),
        ("results", results),
    ])

    packet = OrderedDict([
        ("schema", "ptf-cleveland-pass3-founder-review-packet/1.0"),
        ("work_order", WORK_ORDER),
        ("as_of", PASS_DATE),
        ("prepared_by", AGENT_IDENTITY),
        ("status", "AWAITING_FOUNDER_DECISION"),
        ("rule",
         "Nothing here is published and no authority file moved. Every "
         "proposed fact carries the exact first-party quote that supports "
         "it, verified contiguous in the hash-bound artifact named beside "
         "it; withholding is proposed only where the source contradicts "
         "or garbles itself or states something the schema cannot "
         "represent, never for silence. Approving a candidate authorizes "
         "writing its canonical record with publication-grade evidence "
         "and a founder approval bound to the final record_hash -- "
         "performed in a later pass, never here."),
        ("positive_candidates", packet_positive),
        ("negative_candidates", packet_negative),
        ("routing_review_observations", routing_observations),
        ("hyatt_operator_manual_instructions", HYATT_MANUAL),
        ("not_driven",
         [{"queue_id": qid, "hotel": queue_rows[qid]["name"],
           "reason": HILTON_BLOCK_NOTE}
          for qid, s in ROWS.items() if not s.get("artifact")]),
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
    print("rows: %d | captured: %d | not driven: %d"
          % (ledger["rows_total"], ledger["rows_captured"],
             len(ledger["rows_not_driven"])))
    for name, count in ledger["outcome_counts"].items():
        print("  %-26s %d" % (name, count))
    bench = ledger["speed_benchmark"]
    if bench.get("available"):
        print("benchmark: %ss elapsed, %s captures, median gap %ss, "
              "%s/hour"
              % (bench["session_elapsed_seconds"], bench["captures"],
                 bench["median_inter_capture_gap_seconds"],
                 bench["captures_per_hour"]))
    if not args.apply:
        print("dry run: nothing written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
