"""PTF-PITTSBURGH-PASS1-DECISION-APPLICATION-001 -- apply D001-D020 in one pass.

Deterministic application of the twenty founder decisions recorded (verbatim,
in chat, by the founder on 2026-08-16) in
``pittsburgh_pass1_founder_review_packet.json``:

* the D003 identity rename (Distrikt -> Joinery Hotel Pittsburgh) is carried
  by the census/partition builder's candidate table, which this script runs --
  the observed Joinery pet policy stays provenance only and Joinery returns to
  the unresolved queue as AWAITING_POLICY_OBSERVATION;
* 17 approved positive candidates become published Schema 1.2 records in
  ``hotel_policy_facts_pittsburgh-pa.json``. Every fact quote for a
  rendered-HTML-backed record is asserted contiguous in the hash-bound
  artifact before anything is written; a failed assertion aborts the run.
  Screenshot-backed records bind the operator_screenshot artifact by SHA-256
  (the Columbus Hyatt precedent) with quotes transcribed from the rendered
  surface at capture time;
* the founder's Batch-A global rule is structural here: SOURCE SILENCE IS
  ABSENCE. The only withholdings written are the EVEN and Westin pet_fee
  SOURCE_CONTRADICTORY rulings (both conflicting quotes preserved as
  evidence) and Kimpton's two SCHEMA_CANNOT_REPRESENT disclosures;
* D001/D002 become VERIFIED_NO_PETS rows in the exclusion REGISTRY (the
  no-pets authority; never a census annotation), each bound to its
  property-specific artifact;
* founder approvals are written ONLY against the final record_hash /
  evidence_hash of each fully-built record;
* downstream: 17 seed inventory rows, no routing retirement (Pittsburgh holds
  zero routing records, only ASSESSMENT_ONLY assessments), and the committed
  census/partition/queue/reports rebuilt through their builder;
* a semantic render check projects every published record through
  canonical_view + hotel_profile and fails closed on any unexpected shape.

Run:  python -m scripts.pettripfinder.pittsburgh_pass1_decision_application [--apply]
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import html as _htmllib
import io
import json
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import canonical_view                              # noqa: E402
from scripts.pettripfinder import hotel_exclusions as EX                      # noqa: E402
from scripts.pettripfinder.contracts import enums                             # noqa: E402
from scripts.pettripfinder.contracts import evidence as evidence_contract     # noqa: E402
from scripts.pettripfinder.contracts import policy_schema                     # noqa: E402
from scripts.pettripfinder.contracts import withholding                       # noqa: E402
from scripts.pettripfinder.contracts.fee_computation import classify          # noqa: E402
from scripts.pettripfinder.market_ownership import MARKET_ID_FIELD            # noqa: E402
from scripts.pettripfinder.policy_migration import (                          # noqa: E402
    evidence_hash, evidence_ref_for, record_hash,
)
from scripts.pettripfinder.site_data import PRODUCTION_CSV, normalize_name    # noqa: E402

MARKET = "pittsburgh-pa"
WORK_ORDER = "PTF-PITTSBURGH-PASS1-DECISION-APPLICATION-001"
DECISION_DATE = "2026-08-16"
FOUNDER = "jfields80"

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
FACTS_PATH = LP / ("hotel_policy_facts_%s.json" % MARKET)
EXCLUSIONS_PATH = LP / "hotel_exclusions.json"
ROUTING_PATH = LP / "identity_routing.json"
CENSUS_PATH = LP / "identity_census" / ("%s.json" % MARKET)
PARTITION_PATH = LP / "pittsburgh_final_partition_001.json"
PACKET_PATH = LP / "markets" / "reports" / "pittsburgh_pass1_founder_review_packet.json"
RENDER_REPORT_PATH = LP / "markets" / "reports" / "pittsburgh_pass1_semantic_render.json"
EVIDENCE_DIR = _REPO_ROOT / "data" / "operator_evidence" / "pittsburgh-pass1-capture-001"


def _c(value: str) -> str:
    return " ".join((value or "").split())


def _money(dollars: int) -> Dict:
    return {"amount_cents": dollars * 100, "currency": "USD"}


def _tier(dollars, cmin, cmax=None, *, basis=None, scope=None, basis_stated):
    tier = OrderedDict([("amount_cents", dollars * 100), ("currency", "USD"),
                        ("role", "REPLACEMENT_PRICE"),
                        ("condition_type", "stay_length_range"),
                        ("boundary_unit", "nights"),
                        ("condition_min", cmin)])
    if cmax is not None:
        tier["condition_max"] = cmax
    if basis:
        tier["basis"] = basis
    if scope:
        tier["scope"] = scope
    tier["basis_stated"] = basis_stated
    return tier


_HILTON_DEPOSIT_NOTE = (
    "Hilton renders the non-refundable fee under a 'Deposit' heading; per the "
    "schema doctrine only the body wording ('Non-refundable Fee') is true, so "
    "no deposit is recorded.")

#: One spec per positive decision. ``facts`` entries are (field, value, quote).
#: Quotes for html-backed rows are asserted contiguous in the artifact.
POSITIVES: "OrderedDict[str, Dict]" = OrderedDict([
    ("PGH-P1-D004", dict(
        row=16, decision="APPROVE_WITH_CHANGE", grade=enums.GRADE_PT2_BRAND,
        facts=[
            ("pets_allowed", True, "Pets allowed Yes"),
            ("species", {"dogs": "accepted", "cats": "accepted"},
             "1-4 nights$50 per pet 5+ night stay $125 per pet 2 pet max dog or cat only"),
            ("weight_limit", {"value": 50, "unit": "lb", "operator": "lte",
                              "scope": "per_pet"}, "Max weight 50 lbs"),
            ("fee_tiers", [_tier(50, 1, 4, scope="per_pet", basis_stated=False),
                            _tier(125, 5, scope="per_pet", basis_stated=False)],
             "1-4 nights$50 per pet 5+ night stay $125 per pet 2 pet max dog or cat only"),
            ("pet_count_limit", 2,
             "1-4 nights$50 per pet 5+ night stay $125 per pet 2 pet max dog or cat only"),
        ],
        note="Founder: leave the unstated overall fee basis and tax "
             "relationship absent; the tiers carry the stay-length conditions "
             "only. " + _HILTON_DEPOSIT_NOTE)),
    ("PGH-P1-D005", dict(
        row=17, decision="APPROVE_WITH_CHANGE", grade=enums.GRADE_PT2_BRAND,
        facts=[
            ("pets_allowed", True, "Pets allowed Yes"),
            ("weight_limit", {"value": 50, "unit": "lb", "operator": "lte",
                              "scope": "per_pet"}, "Max weight 50 lbs"),
            ("pet_fee", dict(_money(50), refundable=False),
             "Yes. $50.00 Non-refundable Fee"),
        ],
        note="Founder: fee basis, fee scope, species, and pet_count_limit are "
             "unstated and therefore absent. The structured 'Max weight 50 "
             "lbs' line resolves the boundary as inclusive (the A06 "
             "precedent); the prose 'Pets under 50 pounds' is retained in the "
             "evidence quote. " + _HILTON_DEPOSIT_NOTE)),
    ("PGH-P1-D006", dict(
        row=21, decision="APPROVE_WITH_CHANGE", grade=enums.GRADE_PT2_BRAND,
        facts=[
            ("pets_allowed", True,
             "Dogs and cats accepted. Rooms with pets will be charged a daily fee of $50 per room plus tax. Service animals are free of charge. Limit of two pets per room with a combined weight of 80 pounds."),
            ("species", {"dogs": "accepted", "cats": "accepted"},
             "Dogs and cats accepted. Rooms with pets will be charged a daily fee of $50 per room plus tax. Service animals are free of charge. Limit of two pets per room with a combined weight of 80 pounds."),
            ("pet_fee", dict(_money(50), basis="per_night", scope="per_room",
                              tax_relationship="plus_tax"),
             "Dogs and cats accepted. Rooms with pets will be charged a daily fee of $50 per room plus tax. Service animals are free of charge. Limit of two pets per room with a combined weight of 80 pounds."),
            ("pet_count_limit", 2,
             "Dogs and cats accepted. Rooms with pets will be charged a daily fee of $50 per room plus tax. Service animals are free of charge. Limit of two pets per room with a combined weight of 80 pounds."),
            ("pet_count_scope", "room",
             "Dogs and cats accepted. Rooms with pets will be charged a daily fee of $50 per room plus tax. Service animals are free of charge. Limit of two pets per room with a combined weight of 80 pounds."),
            ("combined_weight_limit", {"value": 80, "unit": "lb",
                                        "operator": "lte"},
             "Dogs and cats accepted. Rooms with pets will be charged a daily fee of $50 per room plus tax. Service animals are free of charge. Limit of two pets per room with a combined weight of 80 pounds."),
            ("service_animal_statement",
             {"stated": True, "charges_stated": "no_charge"},
             "Dogs and cats accepted. Rooms with pets will be charged a daily fee of $50 per room plus tax. Service animals are free of charge. Limit of two pets per room with a combined weight of 80 pounds."),
        ],
        note="Founder: refundability, breed restrictions, and deposit are "
             "source silence and therefore absent. The 80 lb ceiling is "
             "structurally COMBINED and must never become a per-pet maximum. "
             "The known Drury chain structure served only as a parsing aid; "
             "every fact is bound to this Pittsburgh property page.")),
    ("PGH-P1-D007", dict(
        row=23, decision="APPROVE_WITH_CHANGE", grade=enums.GRADE_PT1_FIRST_PARTY,
        facts=[
            ("pets_allowed", True,
             "Be advised that while pets are allowed a one-time fee of $200 is assessed per stay."),
            ("species", {"dogs": "accepted", "cats": "accepted"},
             "Etage allows both cats and dogs."),
            ("pet_fee", dict(_money(200), basis="per_stay"),
             "Be advised that while pets are allowed a one-time fee of $200 is assessed per stay."),
            ("pet_count_limit", 2,
             "Two pets per room allowed with 50 lb max weight per pet."),
            ("pet_count_scope", "room",
             "Two pets per room allowed with 50 lb max weight per pet."),
            ("weight_limit", {"value": 50, "unit": "lb", "operator": "lte",
                              "scope": "per_pet"},
             "Two pets per room allowed with 50 lb max weight per pet."),
        ],
        note="Founder: fee scope and refundability are unstated and "
             "therefore absent.")),
    ("PGH-P1-D008", dict(
        row=24, decision="APPROVE_WITH_CHANGE", grade=enums.GRADE_PT2_BRAND,
        facts=[
            ("pets_allowed", True,
             "Pets are welcome at EVEN Hotel Pittsburgh Downtown."),
            ("species", {"dogs": "accepted"},
             "Two dogs up to 70 lbs for a fee of 50 dollars per stay."),
            ("weight_limit", {"value": 70, "unit": "lb", "operator": "lte",
                              "scope": "per_pet"}, "Pet weight limit: 70"),
            ("pet_count_limit", 2, "2 pets allowed"),
        ],
        withheld=[dict(
            field="pet_fee", reason_code=enums.SOURCE_CONTRADICTORY
            if hasattr(enums, "SOURCE_CONTRADICTORY") else "SOURCE_CONTRADICTORY",
            reason="The same property page states the $50 charge per stay "
                   "('Pet-friendly (50 USD / stay)'; 'Two dogs up to 70 lbs "
                   "for a fee of 50 dollars per stay.') and per night ('Pet "
                   "fee per night: 50 USD'). Per the founder decision neither "
                   "is chosen, averaged, or related, so no fee is published.",
            quotes=["Two dogs up to 70 lbs for a fee of 50 dollars per stay.",
                    "Pet fee per night: 50 USD"])],
        note="Founder: dogs are accepted under BOTH conflicting species "
             "statements ('Two dogs up to 70 lbs' and 'Pets allowed: All "
             "pets allowed'), so species.dogs publishes and nothing broader "
             "does; the conflicting broader wording is preserved in the "
             "packet as provenance.")),
    ("PGH-P1-D009", dict(
        row=28, decision="APPROVE_WITH_CHANGE", grade=enums.GRADE_PT1_FIRST_PARTY,
        facts=[
            ("pets_allowed", True,
             "Fairmont Pittsburgh welcomes pets of all sizes for a nightly fee of $60."),
            ("weight_limit_stated_none", True,
             "Fairmont Pittsburgh welcomes pets of all sizes for a nightly fee of $60."),
            ("pet_fee", dict(_money(60), basis="per_night"),
             "Fairmont Pittsburgh welcomes pets of all sizes for a nightly fee of $60."),
            ("general_restrictions",
             "Pets must remain on a leash at all times and may not be left "
             "unattended in guest rooms. Any damage caused by pets will be "
             "the guest's responsibility.",
             "Pets must remain on a leash at all times and may not be left unattended in guest rooms. Any damage caused by pets will be the guest's responsibility."),
        ],
        note="Founder: 'welcomes pets of all sizes' is an EXPLICIT "
             "no-weight-limit statement, represented canonically as "
             "weight_limit_stated_none. Fee scope, species, pet count, and "
             "refundability remain absent.")),
    ("PGH-P1-D010", dict(
        row=30, decision="APPROVE_WITH_CHANGE", grade=enums.GRADE_PT2_BRAND,
        facts=[
            ("pets_allowed", True, "Pets allowed Yes"),
            ("species", {"dogs": "accepted", "cats": "accepted"},
             "2petsMax,dog/cat only"),
            ("weight_limit", {"value": 75, "unit": "lb", "operator": "lte",
                              "scope": "per_pet"}, "Max weight 75 lbs"),
            ("pet_fee", dict(_money(75), refundable=False),
             "Yes. $75.00 Non-refundable Fee"),
            ("pet_count_limit", 2, "2petsMax,dog/cat only"),
        ],
        note="Founder: fee basis and fee scope are unstated and therefore "
             "absent. " + _HILTON_DEPOSIT_NOTE)),
    ("PGH-P1-D011", dict(
        row=34, decision="APPROVE", grade=enums.GRADE_PT2_BRAND,
        facts=[
            ("pets_allowed", True, "Pets allowed Yes"),
            ("species", {"dogs": "accepted", "cats": "accepted"},
             "$50 2 pets Max dog/cat only"),
            ("pet_fee", dict(_money(50), refundable=False),
             "Yes. $50.00 Non-refundable Fee"),
            ("pet_count_limit", 2, "$50 2 pets Max dog/cat only"),
        ],
        note="Founder: fee basis, fee scope, and weight limit are unstated "
             "and therefore absent. " + _HILTON_DEPOSIT_NOTE)),
    ("PGH-P1-D012", dict(
        row=41, decision="APPROVE", grade=enums.GRADE_PT2_BRAND,
        facts=[
            ("pets_allowed", True, "Pets allowed Yes"),
            ("species", {"dogs": "accepted", "cats": "accepted"},
             "$75/stay for 1-4 night stays $125/stay 5+ night stays 2 pets max dog or cats only"),
            ("weight_limit", {"value": 75, "unit": "lb", "operator": "lte",
                              "scope": "per_pet"}, "Max weight 75 lbs"),
            ("fee_tiers", [_tier(75, 1, 4, basis="per_stay", basis_stated=True),
                            _tier(125, 5, basis="per_stay", basis_stated=True)],
             "$75/stay for 1-4 night stays $125/stay 5+ night stays 2 pets max dog or cats only"),
            ("pet_count_limit", 2,
             "$75/stay for 1-4 night stays $125/stay 5+ night stays 2 pets max dog or cats only"),
        ],
        note="Founder: '/stay' is an explicit basis statement "
             "(basis_stated=true on both tiers); tier scope is unstated and "
             "therefore absent. The ambiguous 'Max size Small' label is "
             "provenance only and publishes nothing. " + _HILTON_DEPOSIT_NOTE)),
    ("PGH-P1-D013", dict(
        row=48, decision="APPROVE", grade=enums.GRADE_PT2_BRAND,
        facts=[
            ("pets_allowed", True, "Pets allowed Yes"),
            ("species", {"dogs": "accepted"},
             "$75(1-4n) $125(5+n) 2pets Max,dogs only"),
            ("weight_limit", {"value": 75, "unit": "lb", "operator": "lte",
                              "scope": "per_pet"}, "Max weight 75 lbs"),
            ("fee_tiers", [_tier(75, 1, 4, basis_stated=False),
                            _tier(125, 5, basis_stated=False)],
             "$75(1-4n) $125(5+n) 2pets Max,dogs only"),
            ("pet_count_limit", 2, "$75(1-4n) $125(5+n) 2pets Max,dogs only"),
        ],
        note="Founder: dogs accepted, cats not claimed; the shorthand states "
             "neither basis nor scope, so both remain absent. "
             + _HILTON_DEPOSIT_NOTE)),
    ("PGH-P1-D014", dict(
        row=58, decision="APPROVE_WITH_CHANGE", grade=enums.GRADE_PT1_FIRST_PARTY,
        facts=[
            ("pets_allowed", True,
             "It’s a dog’s (or cat’s, or feathery or scaly family member’s) life in Pittsburgh."),
            ("weight_limit_stated_none", True, "No size/weight limit"),
            ("species", {"dogs": "accepted", "cats": "accepted"},
             "It’s a dog’s (or cat’s, or feathery or scaly family member’s) life in Pittsburgh."),
        ],
        withheld=[
            dict(field="pet_count_limit",
                 reason_code="SCHEMA_CANNOT_REPRESENT",
                 reason="The page states 'No limit on number of pets "
                        "allowed'; pet_count_limit requires a positive "
                        "integer and the schema has no explicit no-limit "
                        "state, so the disclosure cannot be published as a "
                        "number. The exact sentence is retained in the "
                        "evidence array.",
                 quotes=["No limit on number of pets allowed"]),
            dict(field="other_charges",
                 reason_code="SCHEMA_CANNOT_REPRESENT",
                 reason="The page states 'No deposit or cleaning fees "
                        "charged'; other_charges records only charges that "
                        "exist and no canonical stated-none representation "
                        "exists, so the disclosure cannot be published "
                        "structurally. The exact sentence is retained in the "
                        "evidence array.",
                 quotes=["No deposit or cleaning fees charged"]),
        ],
        note="Founder: pet_fee is NOT inferred as $0 -- the page does not "
             "state that pets themselves are fee-free, so pet_fee is absent. "
             "Dogs and cats are explicitly named in the captured prose and "
             "publish individually; 'feathery or scaly' publishes nothing.")),
    ("PGH-P1-D015", dict(
        row=63, decision="APPROVE", grade=enums.GRADE_PT2_BRAND,
        facts=[
            ("pets_allowed", True,
             "Omni William Penn Hotel is a pet-friendly hotel."),
            ("species", {"dogs": "accepted", "cats": "accepted"},
             "Only dogs and cats are permitted."),
            ("weight_limit", {"value": 25, "unit": "lb", "operator": "lte",
                              "scope": "per_pet"},
             "The weight of the pet is not to exceed 25 pounds (larger dogs must have prior approval by a hotel manager)."),
            ("other_charges",
             [OrderedDict([("kind", "cleaning_fee"), ("amount_cents", 12500),
                            ("currency", "USD"), ("basis", "per_stay"),
                            ("scope", "per_room"), ("refundable", False)])],
             "A non-refundable cleaning fee of $125 (per stay, per room) will be charged at check-in, for basic cleaning of pet hair and odor (additional charges for damage may be imposed)."),
            ("pet_count_limit", 1, "One pet is allowed per guest room."),
            ("pet_count_scope", "room", "One pet is allowed per guest room."),
            ("general_restrictions",
             "Weight limit exception: larger dogs must have prior approval "
             "by a hotel manager. The pet must be placed in a carrier or "
             "crate when housekeeping or engineering enters the room or when "
             "unsupervised. Pets are not permitted in the dining outlets. "
             "Two or more animals require contacting the hotel directly.",
             "The pet must also be placed in a carrier / crate when housekeeping or engineering enters the room or when unsupervised in your guest room. Pets are not permitted in our dining outlets. One pet is allowed per guest room. If guest plans to have two or more animals in the room, he or she must contact the hotel directly to discuss."),
            ("service_animal_statement",
             {"stated": True, "charges_stated": "no_charge"},
             "Guide dogs for the blind or otherwise disabled are exempt from the pet policy – there is no weight limit or pet fee."),
        ],
        note="Founder: all facts explicitly source-supported; the "
             "manager-approval exception for larger dogs qualifies the 25 lb "
             "limit as a general restriction, not a withholding. The charge "
             "is worded as a cleaning fee and is recorded under "
             "other_charges with refundable=false stated by the source.")),
    ("PGH-P1-D016", dict(
        row=65, decision="APPROVE", grade=enums.GRADE_PT2_BRAND,
        facts=[
            ("pets_allowed", True, "Pets Welcome $75 fee per pet, per stay"),
            ("pet_fee", dict(_money(75), basis="per_stay", scope="per_pet"),
             "Pets Welcome $75 fee per pet, per stay"),
            ("pet_count_limit", 2, "Maximum Number of Pets in Room: 2"),
            ("pet_count_scope", "room", "Maximum Number of Pets in Room: 2"),
        ],
        note="Founder: species, weight, and refundability remain absent "
             "because unstated.")),
    ("PGH-P1-D017", dict(
        row=84, decision="APPROVE", grade=enums.GRADE_PT2_BRAND,
        facts=[
            ("pets_allowed", True, "Pets Welcome"),
            ("pet_fee", dict(_money(50), basis="per_stay", refundable=False),
             "Non-Refundable Pet Fee Per Stay: $50.00"),
            ("pet_count_limit", 2, "Maximum Number of Pets in Room: 2"),
            ("pet_count_scope", "room", "Maximum Number of Pets in Room: 2"),
        ],
        note="Founder: fee scope, species, and weight remain absent where "
             "unstated.")),
    ("PGH-P1-D018", dict(
        row=85, decision="APPROVE", grade=enums.GRADE_PT2_BRAND,
        facts=[
            ("pets_allowed", True,
             "Pets up to 75 pounds are welcome for a $100 non-refundable pet fee, with a maximum of two pets per room."),
            ("weight_limit", {"value": 75, "unit": "lb", "operator": "lte",
                              "scope": "per_pet"},
             "Pets up to 75 pounds are welcome for a $100 non-refundable pet fee, with a maximum of two pets per room."),
            ("pet_fee", dict(_money(100), refundable=False),
             "Pets up to 75 pounds are welcome for a $100 non-refundable pet fee, with a maximum of two pets per room."),
            ("pet_count_limit", 2,
             "Pets up to 75 pounds are welcome for a $100 non-refundable pet fee, with a maximum of two pets per room."),
            ("pet_count_scope", "room",
             "Pets up to 75 pounds are welcome for a $100 non-refundable pet fee, with a maximum of two pets per room."),
        ],
        note="Founder: fee basis, fee scope, and species remain absent "
             "because unstated.")),
    ("PGH-P1-D019", dict(
        row=89, decision="APPROVE_WITH_CHANGE", grade=enums.GRADE_PT2_BRAND,
        facts=[
            ("pets_allowed", True, "Pets Welcome"),
            ("species", {"dogs": "accepted"}, "Dogs under 50 lbs ONLY."),
            ("weight_limit", {"value": 50, "unit": "lb", "operator": "lte",
                              "scope": "per_pet"}, "Maximum Pet Weight: 50.0lbs"),
            ("pet_count_limit", 1, "Maximum Number of Pets in Room: 1"),
            ("pet_count_scope", "room", "Maximum Number of Pets in Room: 1"),
            ("general_restrictions",
             "Pets cannot be left unattended in the room.",
             "Pets cannot be left unattended in room."),
        ],
        withheld=[dict(
            field="pet_fee", reason_code="SOURCE_CONTRADICTORY",
            reason="The same property page states the $50 charge per stay "
                   "('Dogs under 50 lbs ONLY. Pets cannot be left unattended "
                   "in room. $50 per stay.') and per night ('Non-Refundable "
                   "Pet Fee Per Night: $50.00'). Per the founder decision "
                   "neither is chosen, averaged, or related, so no fee is "
                   "published.",
            quotes=["Dogs under 50 lbs ONLY. Pets cannot be left unattended in room. $50 per stay.",
                    "Non-Refundable Pet Fee Per Night: $50.00"])],
        note="Founder: non-fee facts publish; the structured 'Maximum Pet "
             "Weight: 50.0lbs' line resolves the boundary as inclusive (the "
             "A06 precedent) while the prose 'under 50 lbs' is preserved in "
             "the withheld-fee evidence quote.")),
    ("PGH-P1-D020", dict(
        row=93, decision="APPROVE", grade=enums.GRADE_PT2_BRAND,
        facts=[
            ("pets_allowed", True,
             "Hotel is pet friendly maximum weight of pets is limited to 50 pounds. Definition of pets shall be limited to domesticated dogs or cats. There is a nonrefundable fee of Dollar 60 per pet. Pets are not permitted in public space such as Restaurants function space recreation space."),
            ("species", {"dogs": "accepted", "cats": "accepted"},
             "Hotel is pet friendly maximum weight of pets is limited to 50 pounds. Definition of pets shall be limited to domesticated dogs or cats. There is a nonrefundable fee of Dollar 60 per pet. Pets are not permitted in public space such as Restaurants function space recreation space."),
            ("weight_limit", {"value": 50, "unit": "lb", "operator": "lte",
                              "scope": "per_pet"},
             "Hotel is pet friendly maximum weight of pets is limited to 50 pounds. Definition of pets shall be limited to domesticated dogs or cats. There is a nonrefundable fee of Dollar 60 per pet. Pets are not permitted in public space such as Restaurants function space recreation space."),
            ("pet_fee", dict(_money(60), scope="per_pet", refundable=False),
             "Hotel is pet friendly maximum weight of pets is limited to 50 pounds. Definition of pets shall be limited to domesticated dogs or cats. There is a nonrefundable fee of Dollar 60 per pet. Pets are not permitted in public space such as Restaurants function space recreation space."),
            ("general_restrictions",
             "Pets are not permitted in public spaces such as restaurants, "
             "function space, and recreation space.",
             "Pets are not permitted in public space such as Restaurants function space recreation space."),
        ],
        note="Founder: fee basis and pet count remain absent because "
             "unstated.")),
])

#: The two founder-approved refusals.
NEGATIVES = OrderedDict([
    ("PGH-P1-D001", dict(
        row=4,
        refusal_quote="No. While we love animals, Cambria Hotel Pittsburgh "
                      "Downtown is not a pet-friendly hotel.")),
    ("PGH-P1-D002", dict(
        row=9,
        refusal_quote="Pet Policy Pets Not Allowed Service animals only")),
])


def artifact_text(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    raw = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", " ", raw,
                 flags=re.S | re.I)
    return _c(_htmllib.unescape(re.sub(r"<[^>]*>", " ", raw)))


def _artifacts_for(row: int):
    """(path, kind) pairs on disk for a queue row, preferring rendered HTML."""
    out = []
    stem = "ptf-pgh-p1-r%02d" % row
    html_path = EVIDENCE_DIR / (stem + ".html")
    jpg_path = EVIDENCE_DIR / (stem + ".jpg")
    if html_path.is_file():
        out.append((html_path, enums.ARTIFACT_RENDERED_HTML))
    if jpg_path.is_file():
        out.append((jpg_path, enums.ARTIFACT_OPERATOR_SCREENSHOT))
    if not out:
        raise SystemExit("STOP r%02d: no artifact on disk" % row)
    return out


def _sha_file(path: Path) -> str:
    return "sha256:%s" % hashlib.sha256(path.read_bytes()).hexdigest()


def _captured_at(path: Path) -> str:
    head = path.read_text(encoding="utf-8", errors="ignore")[:200]
    m = re.search(r"captured_at: (\S+)", head)
    return m.group(1) if m else DECISION_DATE


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"),
                      object_pairs_hook=OrderedDict)


def write_lf(path: Path, payload) -> bytes:
    data = (json.dumps(payload, indent=1, ensure_ascii=False) + "\n").encode("utf-8")
    with path.open("wb") as fh:
        fh.write(data)
    return data


def _value_display(value) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def build_positive_record(did: str, spec: Dict, packet_entry: Dict,
                          census_row: Dict) -> Dict:
    row = spec["row"]
    artifacts = _artifacts_for(row)
    primary_path, primary_kind = artifacts[0]
    packet_shas = {a["artifact_sha256"] for a in packet_entry["artifacts"]}
    for path, _kind in artifacts:
        digest = _sha_file(path).split(":", 1)[1]
        if digest not in packet_shas:
            raise SystemExit("STOP %s: %s hash drifted from the committed "
                             "packet" % (did, path.name))

    hay = artifact_text(primary_path) if primary_kind == \
        enums.ARTIFACT_RENDERED_HTML else None
    artifact_sha = _sha_file(primary_path)
    captured_at = _captured_at(primary_path) \
        if primary_kind == enums.ARTIFACT_RENDERED_HTML else DECISION_DATE
    source_url = packet_entry["final_url"]

    def _assert_quote(quote: str) -> None:
        if hay is not None and _c(quote) not in hay:
            raise SystemExit("STOP %s: quote %r not contiguous in %s"
                             % (did, quote[:60], primary_path.name))

    facts: "OrderedDict[str, object]" = OrderedDict()
    sas = None
    evidence: List[Dict] = []

    def _evidence_entry(field: str, quote: str, value) -> Dict:
        entry = OrderedDict([
            ("field", field),
            ("quote", quote),
            ("source_url", source_url),
            ("value", _value_display(value)),
            ("evidence_ref", ""),
            ("artifact_class", enums.PUBLICATION_GRADE_EVIDENCE),
            ("artifact_sha256", artifact_sha),
            ("artifact_kind", primary_kind),
            ("captured_at", captured_at),
            ("capture_method", "attended_browser"),
            ("source_grade", spec["grade"]),
        ])
        entry["evidence_ref"] = evidence_ref_for(entry)
        return entry

    for field, value, quote in spec["facts"]:
        _assert_quote(quote)
        evidence.append(_evidence_entry(field, quote, value))
        if field == "service_animal_statement":
            sas = value
        else:
            facts[field] = value

    withheld: "OrderedDict[str, Dict]" = OrderedDict()
    for w in spec.get("withheld", []):
        refs = []
        for quote in w["quotes"]:
            _assert_quote(quote)
            entry = _evidence_entry(w["field"], quote, "WITHHELD")
            evidence.append(entry)
            refs.append(entry["evidence_ref"])
        withheld[w["field"]] = OrderedDict([
            ("reason_code", w["reason_code"]),
            ("reason", w["reason"]),
            ("evidence_refs", refs),
        ])

    quote_texts = []
    for entry in evidence:
        if entry["quote"] not in quote_texts:
            quote_texts.append(entry["quote"])
    evidence_quote = " […] ".join(quote_texts)

    record = OrderedDict([
        ("key", census_row["identity_key"]),
        ("name", census_row["canonical_name"]),
        ("facts", facts),
        ("evidence", evidence),
        ("evidence_count", len(evidence)),
        ("evidence_quote", evidence_quote),
        ("source_url", source_url),
        ("source_type", "EXACT_ENTITY_DOMAIN"),
        ("verification_state", "VERIFIED_PET_FRIENDLY"),
        ("verification_date", DECISION_DATE),
        ("verified_at", DECISION_DATE),
        ("worker_model_id", ""),
        ("worker_prompt_version", ""),
        ("worker_result_hash", artifact_sha),
        ("worker_routing_version", ""),
        ("worker_validator_version", ""),
        ("schema_version", "1.2"),
        ("identity_key", census_row["identity_key"]),
        ("market_id", MARKET),
    ])
    if withheld:
        record["withheld_fields"] = withheld
    if sas is not None:
        record["service_animal_statement"] = sas
    record["computation_class"] = classify(facts).computation_class

    issues = list(policy_schema.validate_record(record)) \
        + list(evidence_contract.validate(record)) \
        + list(withholding.validate(record))
    if issues:
        raise SystemExit("STOP %s: contract issues: %s" % (did, issues[:4]))

    caveats = [
        "Founder decision %s (%s), recorded verbatim in "
        "pittsburgh_pass1_founder_review_packet.json (commit d0e6106) and "
        "approved against THIS final record_hash. %s evidence quotes were "
        "asserted contiguous in the hash-bound rendered-HTML artifact; "
        "screenshot-backed records bind the operator screenshot (%s) whose "
        "policy surface and identity signals are visible in one frame. "
        "Identity binding: %s." % (
            did, spec["decision"],
            "All" if hay is not None else "Transcribed",
            artifact_sha[:23], packet_entry["identity_binding"]),
        "Founder global rule applied: SOURCE SILENCE IS ABSENCE -- unstated "
        "optional facts are absent, never withheld.",
        spec["note"],
    ]
    record["approval"] = OrderedDict([
        ("decision", enums.APPROVED_AFTER_CURRENT_REVIEW),
        ("operator", FOUNDER),
        ("approval_date", DECISION_DATE),
        ("caveats", caveats),
        ("record_hash", record_hash(record)),
        ("evidence_hash", evidence_hash(evidence)),
    ])
    return record


def build_exclusion(did: str, spec: Dict, packet_entry: Dict,
                    census_row: Dict) -> Dict:
    artifacts = _artifacts_for(spec["row"])
    primary_path, primary_kind = artifacts[0]
    packet_shas = {a["artifact_sha256"] for a in packet_entry["artifacts"]}
    digest = _sha_file(primary_path).split(":", 1)[1]
    if digest not in packet_shas:
        raise SystemExit("STOP %s: artifact hash drifted from the committed "
                         "packet" % did)
    if primary_kind == enums.ARTIFACT_RENDERED_HTML \
            and _c(spec["refusal_quote"]) not in artifact_text(primary_path):
        raise SystemExit("STOP %s: refusal quote not in artifact" % did)
    record = OrderedDict([
        ("exclusion_id", "pgh-%s" % census_row["slug"]),
        ("canonical_name", census_row["canonical_name"]),
        ("normalized_name", normalize_name(census_row["canonical_name"])),
        ("address", census_row["address"]),
        ("city", census_row["city"]),
        ("state", census_row["state"]),
        ("postal_code", census_row["postal_code"]),
        ("official_url", packet_entry["final_url"]),
        ("exclusion_state", EX.VERIFIED_NO_PETS),
        ("evidence_quote", spec["refusal_quote"]),
        ("source_url", packet_entry["final_url"]),
        ("observed_at", DECISION_DATE),
        ("source_hash", _sha_file(primary_path)),
        ("reviewer_id", FOUNDER),
        ("reviewed_at", DECISION_DATE),
        ("notes", "Founder decision %s, %s: affirmative first-party refusal "
                  "in the property's own words, captured by the attended "
                  "browser as %s with policy and identity in frame "
                  "(binding: %s). Service-animal access is a legal category "
                  "and never converts a no-pets policy into pet-friendly."
                  % (did, WORK_ORDER, primary_kind,
                     packet_entry["identity_binding"])),
        ("market_id", MARKET),
    ])
    record["record_hash"] = EX.record_hash(record)
    record["approval_hash"] = EX.approval_hash(record)
    return record


def semantic_render_check(published: List[Dict]) -> Dict:
    """Project every record through the production display path, fail closed."""
    from scripts.pettripfinder.hotel_profile import (
        _verified_details, _verified_facts, _verified_summary,
    )

    def profile_text(record):
        shown = canonical_view.display_facts(record)
        parts = [_verified_summary(shown, record.get("evidence_quote") or "")]
        parts += ["%s %s" % (l, v) for l, v, _x in _verified_facts(shown)]
        parts += ["%s %s" % (l, v)
                  for l, v, _x in _verified_details(shown, record)[0]]
        return " | ".join(parts)

    unexpected: List[str] = []
    rows = []
    by_key = {r["identity_key"]: r for r in published}
    for record in published:
        text = profile_text(record)
        view = canonical_view.build(record)
        rows.append(OrderedDict([
            ("identity_key", record["identity_key"]),
            ("fee_phrase", canonical_view.fee_phrase(view)),
            ("fee_display_mode", view.fee_display_mode),
            ("profile_text", text),
        ]))
        if not text.strip():
            unexpected.append("%s: empty profile" % record["identity_key"])

    def _expect(cond: bool, label: str) -> None:
        if not cond:
            unexpected.append(label)

    for key in ("even hotel pittsburgh downtown", "the westin pittsburgh"):
        view = canonical_view.build(by_key[key])
        _expect(canonical_view.fee_phrase(view) == "",
                "%s: withheld fee must not render a price" % key)
        _expect("withheld" in profile_text(by_key[key]).lower(),
                "%s: fee must render as withheld/source conflict" % key)
    drury = profile_text(by_key["drury plaza hotel pittsburgh downtown"])
    _expect("combined" in drury.lower(),
            "drury: 80 lb must render as a combined weight")
    for key in ("fairmont pittsburgh", "kimpton hotel monaco pittsburgh"):
        text = profile_text(by_key[key]).lower()
        _expect("no weight limit" in text or "no size" in text
                or "all sizes" in text or "no stated" not in text,
                "%s: explicit no-weight-limit must not render as silence" % key)
    for record in published:
        if "pet_fee" not in record["facts"] \
                and "fee_tiers" not in record["facts"] \
                and record["identity_key"] not in (
                    "even hotel pittsburgh downtown", "the westin pittsburgh"):
            _expect("withheld" not in profile_text(record).lower(),
                    "%s: silence must stay absent, never 'withheld'"
                    % record["identity_key"])
    return OrderedDict([
        ("schema", "ptf-pittsburgh-pass1-semantic-render/1.0"),
        ("work_order", WORK_ORDER),
        ("as_of", DECISION_DATE),
        ("record_count", len(published)),
        ("unexpected_semantic_changes", unexpected),
        ("unexpected_semantic_change_count", len(unexpected)),
        ("rows", rows),
    ])


def run(apply: bool) -> Dict:
    packet = load_json(PACKET_PATH)
    entries = {e["decision_id"]: e for e in packet["entries"]}
    census = {r["identity_key"]: r for r in load_json(CENSUS_PATH)["hotels"]}

    if FACTS_PATH.is_file():
        raise SystemExit("STOP: %s already exists" % FACTS_PATH.name)

    # ---- rename precondition (D003 applied by the builder) ----------------- #
    if "joinery hotel pittsburgh" not in census:
        raise SystemExit("STOP: the D003 rename has not landed in the census")
    if any("distrikt" in key for key in census):
        raise SystemExit("STOP: a Distrikt identity survives the rename")

    # ---- 17 positives ------------------------------------------------------ #
    published: List[Dict] = []
    for did, spec in POSITIVES.items():
        entry = entries[did]
        key = entry["identity_key"]
        if key not in census:
            raise SystemExit("STOP %s: %r not in the census" % (did, key))
        if entry["founder_decision"] != spec["decision"]:
            raise SystemExit("STOP %s: packet decision %r != %r"
                             % (did, entry["founder_decision"],
                                spec["decision"]))
        published.append(build_positive_record(did, spec, entry, census[key]))

    facts_doc = OrderedDict([
        ("market", "Pittsburgh, Pennsylvania"),
        ("schema_version", "1.2"),
        ("market_id", MARKET),
        ("hotels", published),
    ])

    # ---- 2 exclusions ------------------------------------------------------ #
    exclusions_doc = load_json(EXCLUSIONS_PATH)
    existing_norm = {e["normalized_name"] for e in exclusions_doc["exclusions"]}
    new_exclusions: List[Dict] = []
    for did, spec in NEGATIVES.items():
        entry = entries[did]
        if entry["founder_decision"] != "APPROVE_VERIFIED_NO_PETS":
            raise SystemExit("STOP %s: unexpected decision" % did)
        key = entry["identity_key"]
        record = build_exclusion(did, spec, entry, census[key])
        if record["normalized_name"] in existing_norm:
            raise SystemExit("STOP %s: already excluded" % did)
        new_exclusions.append(record)
    # Category exits mirror the Columbus mechanic: the census keeps the row,
    # the REGISTRY carries the OUT_OF_CURRENT_CATEGORY ruling, and the
    # release-contract derivation counts them as terminally disposed -- so the
    # derived unresolved figure equals the partition's instead of skewing by
    # exactly these three.
    census_bytes = CENSUS_PATH.read_bytes()
    census_sha = "sha256:%s" % hashlib.sha256(census_bytes).hexdigest()
    ooc_rows: List[Dict] = []
    for row in load_json(CENSUS_PATH)["hotels"]:
        if row["lodging_state"] != "NOT_LODGING":
            continue
        record = OrderedDict([
            ("exclusion_id", "pgh-ooc-%s" % row["slug"]),
            ("canonical_name", row["canonical_name"]),
            ("normalized_name", normalize_name(row["canonical_name"])),
            ("address", row["address"]),
            ("city", row["city"]),
            ("state", row["state"]),
            ("postal_code", row["postal_code"]),
            ("official_url", row["official_url"] or row["provenance"]),
            ("exclusion_state", EX.OUT_OF_CURRENT_CATEGORY),
            ("evidence_quote", "Founder category ruling 2026-08-15 "
                               "(PTF-PITTSBURGH-MARKET-REVALIDATION-001, "
                               "founder-authorized commit 6eb21c1): not in "
                               "the current pet-friendly-hotels category."),
            ("source_url", "launch_packages/pettripfinder/identity_census/"
                           "pittsburgh-pa.json"),
            ("observed_at", "2026-08-15"),
            ("source_hash", census_sha),
            ("reviewer_id", FOUNDER),
            ("reviewed_at", DECISION_DATE),
            ("notes", "%s: registry projection of the census NOT_LODGING "
                      "ruling (lodging_state authority: the committed "
                      "census; source_hash is the census file's bytes, not a "
                      "page artifact). NO pet-policy fact is asserted. "
                      "Preserved as a future lodging-category lead; re-entry "
                      "requires an explicit reviewed supersession."
                      % WORK_ORDER),
            ("market_id", MARKET),
        ])
        record["record_hash"] = EX.record_hash(record)
        record["approval_hash"] = EX.approval_hash(record)
        if record["normalized_name"] in existing_norm:
            raise SystemExit("STOP: %s already excluded"
                             % record["normalized_name"])
        ooc_rows.append(record)
    if len(ooc_rows) != 3:
        raise SystemExit("STOP: expected 3 category exits, found %d"
                         % len(ooc_rows))

    exclusions_doc["exclusions"] = (exclusions_doc["exclusions"]
                                    + new_exclusions + ooc_rows)
    EX.validate(exclusions_doc)

    # ---- seed inventory ---------------------------------------------------- #
    seed_new = []
    for record in published:
        row = census[record["identity_key"]]
        seed_new.append({
            "name": record["name"], "category": "pet-friendly-hotels",
            "address": row["address"], "city": row["city"],
            "state": row["state"], "postal_code": row["postal_code"],
            "phone": row["phone"], "website_url": record["source_url"],
            "source_url": record["source_url"],
            "source_type": "OFFICIAL_PROPERTY", "observed_at": DECISION_DATE,
            "rating": "", "amenities": "",
            "pet_policy": record["evidence_quote"], "canonical": "",
            MARKET_ID_FIELD: MARKET,
        })

    # ---- routing: Pittsburgh must hold no routes --------------------------- #
    routing = load_json(ROUTING_PATH)
    pgh_routes = [r for r in routing.get("routes") or []
                  if r.get("market_id") == MARKET]
    if pgh_routes:
        raise SystemExit("STOP: %d Pittsburgh routing records exist; the "
                         "published/excluded-hold-no-routes invariant needs "
                         "an explicit retirement pass" % len(pgh_routes))

    # ---- semantic render gate ---------------------------------------------- #
    render_report = semantic_render_check(published)
    if render_report["unexpected_semantic_change_count"]:
        raise SystemExit("STOP: unexpected semantic changes: %s"
                         % render_report["unexpected_semantic_changes"])

    summary = OrderedDict([
        ("published_added", len(published)),
        ("exclusions_added", len(new_exclusions)),
        ("category_registry_rows_added", len(ooc_rows)),
        ("seed_rows_added", len(seed_new)),
        ("routes_retired", 0),
        ("unexpected_semantic_changes",
         render_report["unexpected_semantic_change_count"]),
    ])

    if apply:
        payload = write_lf(FACTS_PATH, facts_doc)
        summary["facts_sha256"] = hashlib.sha256(payload).hexdigest()
        write_lf(EXCLUSIONS_PATH, exclusions_doc)
        write_lf(RENDER_REPORT_PATH, render_report)

        with PRODUCTION_CSV.open(encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            existing_rows = list(reader)
            fields = list(reader.fieldnames)
        clash = {normalize_name(r["name"]) for r in existing_rows
                 if r.get(MARKET_ID_FIELD) == MARKET} \
            & {normalize_name(r["name"]) for r in seed_new}
        if clash:
            raise SystemExit("STOP: seed rows already present: %s" % clash)
        buf = io.StringIO(newline="")
        writer = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in existing_rows + seed_new:
            writer.writerow({k: row.get(k, "") for k in fields})
        PRODUCTION_CSV.write_text(buf.getvalue(), encoding="utf-8",
                                  newline="")

        # census/partition/queue/reports are DERIVED, never hand-edited: with
        # the authorities written, the committed builder recomputes every
        # final state from them.
        from scripts.pettripfinder import build_pittsburgh_market_001 as B
        B._AUTHORITY_CACHE = None
        B.build()

        partition = load_json(PARTITION_PATH)
        counts = Counter(i["final_state"] for i in partition["items"])
        if counts["PUBLISHED_PET_FRIENDLY"] != len(published):
            raise SystemExit("STOP: partition shows %d published, expected %d"
                             % (counts["PUBLISHED_PET_FRIENDLY"],
                                len(published)))
        if counts["VERIFIED_NO_PETS"] != len(new_exclusions):
            raise SystemExit("STOP: partition shows %d no-pets, expected %d"
                             % (counts["VERIFIED_NO_PETS"],
                                len(new_exclusions)))
        joinery = [i for i in partition["items"]
                   if i["identity_key"] == "joinery hotel pittsburgh"][0]
        if joinery["final_state"] != enums.AWAITING_POLICY_OBSERVATION:
            raise SystemExit("STOP: Joinery must remain unresolved "
                             "(AWAITING_POLICY_OBSERVATION), got %s"
                             % joinery["final_state"])
        summary["partition_counts"] = OrderedDict(sorted(counts.items()))

        # governance: every approval binds the FINAL written hashes
        written = load_json(FACTS_PATH)
        for hotel in written["hotels"]:
            approval = hotel.get("approval") or {}
            if approval.get("decision") != enums.APPROVED_AFTER_CURRENT_REVIEW:
                raise SystemExit("STOP %s: not approved" % hotel["identity_key"])
            if approval.get("record_hash") != record_hash(hotel):
                raise SystemExit("STOP %s: approval does not bind the final "
                                 "record_hash" % hotel["identity_key"])
            if approval.get("evidence_hash") != evidence_hash(hotel["evidence"]):
                raise SystemExit("STOP %s: approval does not bind the final "
                                 "evidence_hash" % hotel["identity_key"])

        packet["status"] = "FOUNDER_DECIDED_AND_APPLIED"
        packet["applied_at"] = DECISION_DATE
        packet["application_work_order"] = WORK_ORDER
        for entry in packet["entries"]:
            if entry["decision_id"] in POSITIVES:
                entry["outcome"] = "PUBLISHED"
            elif entry["decision_id"] in NEGATIVES:
                entry["outcome"] = "EXCLUDED_VERIFIED_NO_PETS"
            elif entry["decision_id"] == "PGH-P1-D003":
                entry["outcome"] = "IDENTITY_RENAME_APPLIED"
        write_lf(PACKET_PATH, packet)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    summary = run(args.apply)
    for key, value in summary.items():
        print("%s: %s" % (key, json.dumps(value, ensure_ascii=False)
                          if not isinstance(value, str) else value))
    if not args.apply:
        print("dry run: nothing written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
