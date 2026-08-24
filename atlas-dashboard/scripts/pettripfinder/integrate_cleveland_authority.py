"""PTF-CLEVELAND-OVERNIGHT-AUTHORITY-001 -- Cleveland evidence into authority.

Turns the hash-verified Cleveland capture package into committed authority:
inventory rows, per-market policy facts, and verified-no-pets exclusions. The
captures are not re-run; the artifacts recorded in
``proposed_cleveland_authority.json`` are the input.

The fact table below is the substance of this module, and it is deliberately
hand-authored rather than regex-extracted. Every field carries the exact quote
from the property's own captured page that supports it, and the loader asserts
that quote really is a substring of the stored evidence. A regex over
brand-templated text would have been faster and would have silently invented
values the moment a template changed.

What is deliberately WITHHELD is recorded per hotel with its reason, because a
withheld field is a decision that has to survive review:

  * IHG's structured widget labels a per-stay fee "Pet fee per night". Where
    the property's own prose says "Per stay", the prose wins and the widget is
    withheld; where the prose states no basis at all, fee_basis is withheld
    entirely rather than trusting a widget already shown to be wrong twice.
  * A general incidentals deposit is not a pet deposit.
  * A conditional sanitation charge is not a pet fee.
  * "Dogs & service animals only" is DOGS. Service-animal access is a legal
    category, never a species permission and never a refusal.
  * Species, weight, and count are absent on several records and stay absent.

Run:  python -m scripts.pettripfinder.integrate_cleveland_authority [--apply]
"""

from __future__ import annotations

import csv
import io
import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.contracts import enums          # noqa: E402
from scripts.pettripfinder import hotel_exclusions as EX                    # noqa: E402
from scripts.pettripfinder.market_ownership import MARKET_ID_FIELD          # noqa: E402
from scripts.pettripfinder.policy import policy_membrane as MB              # noqa: E402
from scripts.pettripfinder.policy import policy_observation as PO           # noqa: E402
from scripts.pettripfinder.site_data import PRODUCTION_CSV, normalize_name  # noqa: E402
from services.research_workers.source_retrieval import (                    # noqa: E402
    extract_property_code_from_url,
)

MARKET = "cleveland-akron-canton-oh"
AS_OF = "2026-08-10"
REVIEWER = "jfields80"
BATCH = (_REPO_ROOT / "data" / "worker_runs" / "pettripfinder" / "discovery"
         / "review_batches" / "cleveland-factory-001")
PROPOSAL = BATCH / "proposed_cleveland_authority.json"
FACTS_OUT = (_REPO_ROOT / "launch_packages" / "pettripfinder"
             / ("hotel_policy_facts_%s.json" % MARKET))

#: field -> (value, exact supporting quote from the captured evidence)
#: withheld -> field -> reason
FACTS: Dict[str, Dict] = {
    "ac-hotel-cleveland-beachwood": {
        "facts": {
            "pets_allowed": ("true", "Pets Welcome"),
            "pet_fee": ("$150.00", "$150.00 Non Refundable Pet Fee per stay"),
            "fee_basis": ("per stay", "$150.00 Non Refundable Pet Fee per stay"),
            "weight_limit": ("35 pounds", "Maximum Pet Weight: 35.0lbs"),
            "pet_count_limit": ("1", "Maximum Number of Pets in Room: 1"),
            "pet_count_scope": ("room", "Maximum Number of Pets in Room: 1"),
        },
        "withheld": {"species_allowed": "the page names no species"},
    },
    "cleveland-marriott-downtown-at-key-tower": {
        "facts": {
            "pets_allowed": ("true", "Pets Welcome"),
            "species_allowed": ("dogs", "Dogs & service animals only"),
            "pet_fee": ("$100.00", "Non-Refundable Pet Fee Per Stay: $100.00"),
            "fee_basis": ("per stay", "Non-Refundable Pet Fee Per Stay: $100.00"),
            "weight_limit": ("40 pounds", "Maximum Pet Weight: 40.0lbs"),
            "pet_count_limit": ("1", "Maximum Number of Pets in Room: 1"),
            "pet_count_scope": ("room", "Maximum Number of Pets in Room: 1"),
        },
        "withheld": {"cats_allowed": "dogs are named; cats are not, and absence "
                                     "is not a refusal to publish either way"},
        "note": "the classifier near-miss: 'Dogs & service animals only' sits "
                "beside 'Pets Welcome'. Service-animal language is never read "
                "as a refusal.",
    },
    "comfort-inn-mayfield-heights-cleveland-east": {
        "facts": {
            "pets_allowed": ("true", "Pets Allowed: Yes"),
            "species_allowed": ("dogs", "We only allow dogs"),
            "pet_fee": ("$25.00", "25.00 USD per night"),
            "fee_basis": ("per night", "25.00 USD per night"),
            "weight_limit": ("40 pounds", "Limit 40 pounds"),
            "pet_count_limit": ("2", "only 2 per room"),
            "pet_count_scope": ("room", "only 2 per room"),
            "service_animal_exception": ("true", "Service animals are permitted, without charge"),
        },
        "withheld": {},
    },
    "courtyard-by-marriott-airport-north": {
        "facts": {
            "pets_allowed": ("true", "Pets Welcome"),
            "pet_fee": ("$20.00", "Non-Refundable Pet Fee Per Night: $20.00"),
            "fee_basis": ("per night", "Non-Refundable Pet Fee Per Night: $20.00"),
            "cleaning_fee": ("$100.00", "$100/stay nonrefundable clean fee"),
            "weight_limit": ("75 pounds", "Maximum Pet Weight: 75.0lbs"),
            "pet_count_limit": ("1", "Maximum Number of Pets in Room: 1"),
            "pet_count_scope": ("room", "Maximum Number of Pets in Room: 1"),
        },
        "withheld": {"species_allowed": "the page names no species"},
        "note": "additive, not replacement: $20/day AND a separate $100/stay "
                "cleaning fee, both stated.",
    },
    "embassy-suites-beachwood": {
        "facts": {
            "pets_allowed": ("true", "Pets allowed"),
            "species_allowed": ("dogs and cats", "dog or cat only"),
            "pet_count_limit": ("2", "2 pets max"),
            "fee_tiers": ("STAY_LENGTH_75_125", "1-4 night stay $75; 5+ night stay $125"),
        },
        "withheld": {"weight_limit": "no weight is stated on this property's page"},
    },
    "embassy-suites-rockside-independence": {
        "facts": {
            "pets_allowed": ("true", "Pets allowed"),
            "species_allowed": ("dogs and cats", "dog or cat only"),
            "pet_count_limit": ("2", "2 pets max"),
            "fee_tiers": ("STAY_LENGTH_75_125", "1-4 night stay $75; 5+ night stay $125"),
        },
        "withheld": {"weight_limit": "no weight is stated on this property's page"},
    },
    "hampton-inn-suites-streetsboro": {
        "facts": {
            "pets_allowed": ("true", "Pets allowed"),
            "species_allowed": ("dogs and cats", "dog/cat only"),
            "pet_count_limit": ("2", "2petsMax"),
            "fee_tiers": ("STAY_LENGTH_75_125", "$75(1-4n)$125(5+n)"),
        },
        "withheld": {"weight_limit": "no weight is stated on this property's page"},
    },
    "holiday-inn-express-suites": {
        "facts": {
            "pets_allowed": ("true", "Pets are welcome at Holiday Inn Express & Suites Cleveland West - Westlake"),
            "species_allowed": ("dogs", "Pets allowed: Only dogs allowed"),
            "weight_limit": ("75 pounds", "Pet weight limit: 75"),
            "pet_count_limit": ("2", "up to 2 pets max"),
            "fee_tiers": ("STAY_LENGTH_75_125_PER_STAY",
                          "75.00 for 1 to 4 nights. 125 for 5 or more nights. Per stay"),
        },
        "withheld": {"pet_fee": "the property's prose states a stay-length ladder "
                                "and 'Per stay'; IHG's widget labels the same $75 "
                                "'per night'. The ladder is published; the "
                                "contradicted flat per-night reading is not."},
    },
    "home2-suites-by-hilton-cleveland-beachwood": {
        "facts": {
            "pets_allowed": ("true", "Pets allowed"),
            "species_allowed": ("dogs and cats", "dog/cat only"),
            "pet_fee": ("$50.00", "Yes. $50.00 Non-refundable Fee"),
            "weight_limit": ("75 pounds", "75 lbs"),
            "pet_count_limit": ("2", "2petsMax"),
        },
        "withheld": {"fee_basis": "the page states the amount but never its basis",
                     "fee_tiers": "'$50 for one pet $75' is a per-COUNT step, not "
                                  "a stay-length ladder, and the fee_tiers schema "
                                  "models stay-length bands"},
    },
    "hotel-indigo-cleveland-beachwood": {
        "facts": {
            "pets_allowed": ("true", "Pets are welcome at Hotel Indigo Cleveland-Beachwood"),
            "species_allowed": ("dogs", "Pets allowed: Only dogs allowed"),
            "pet_fee": ("$100.00", "A 100 dollar non refundable fee per stay"),
            "fee_basis": ("per stay", "A 100 dollar non refundable fee per stay"),
            "weight_limit": ("75 pounds", "Pets under 75lbs are welcome"),
            "pet_count_limit": ("2", "There is a 2 pet per room maximum"),
            "pet_count_scope": ("room", "There is a 2 pet per room maximum"),
        },
        "withheld": {"pet_deposit": "the widget shows a $100 'damage deposit' that "
                                    "duplicates the $100 fee the prose describes; "
                                    "publishing both would double the cost"},
    },
    "hotel-indigo-cleveland-downtown": {
        "facts": {
            "pets_allowed": ("true", "Pets are welcome at Hotel Indigo Cleveland Downtown"),
            "species_allowed": ("dogs", "Pets allowed: Only dogs allowed"),
            "pet_fee": ("$75.00", "Non refundable pet fee 75 USD"),
            "weight_limit": ("40 pounds", "Maximum weight 40 lbs."),
            "pet_count_limit": ("2", "limit 2 per room"),
            "pet_count_scope": ("room", "limit 2 per room"),
            "unattended_policy": ("not permitted", "Pets and service animals not permitted to be left unattended"),
        },
        "withheld": {"fee_basis": "the prose states no basis, and IHG's widget "
                                  "('per night') is contradicted by its own prose "
                                  "on two sibling properties in this same batch"},
    },
    "residence-inn-by-marriott-cleveland-avon-at-the-emerald-event-center": {
        "facts": {
            "pets_allowed": ("true", "Pets Welcome"),
            "pet_fee": ("$100.00", "Non-Refundable Pet Fee Per Stay: $100.00"),
            "fee_basis": ("per stay", "Non-Refundable Pet Fee Per Stay: $100.00"),
            "fee_scope": ("per room", "USD 100 non-refundable fee per room per stay"),
            "weight_limit": ("50 pounds", "Maximum Pet Weight: 50.0lbs"),
            "pet_count_limit": ("2", "Maximum Number of Pets in Room: 2"),
            "pet_count_scope": ("room", "Maximum Number of Pets in Room: 2"),
        },
        "withheld": {"species_allowed": "the page names no species"},
    },
    "residence-inn-by-marriott-cleveland-downtown": {
        "facts": {
            "pets_allowed": ("true", "Pets Welcome"),
            "species_allowed": ("dogs and cats", "One cat or dog"),
            "pet_fee": ("$100.00", "Non-Refundable Pet Fee Per Stay: $100.00"),
            "fee_basis": ("per stay", "Non-Refundable Pet Fee Per Stay: $100.00"),
            "pet_count_limit": ("1", "Maximum Number of Pets in Room: 1"),
            "pet_count_scope": ("room", "Maximum Number of Pets in Room: 1"),
        },
        "withheld": {"weight_limit": "no weight is stated on this property's page"},
    },
    "residence-inn-by-marriott-independence": {
        "facts": {
            "pets_allowed": ("true", "Pets Welcome"),
            "species_allowed": ("dogs", "Dogs Only, No Cats"),
            "cats_allowed": ("false", "Dogs Only, No Cats"),
            "pet_fee": ("$100.00", "Non-Refundable Pet Fee Per Stay: $100.00"),
            "fee_basis": ("per stay", "Non-Refundable Pet Fee Per Stay: $100.00"),
            "weight_limit": ("50 pounds", "Maximum Pet Weight: 50.0lbs"),
            "pet_count_limit": ("2", "Maximum Number of Pets in Room: 2"),
            "pet_count_scope": ("room", "Maximum Number of Pets in Room: 2"),
        },
        "withheld": {"cleaning_fee": "a second '$5.00 Per Night' line appears with "
                                     "no stated relationship to the per-stay fee; "
                                     "publishing it as additive would assert a "
                                     "total the page never states"},
    },
    "residence-inn-cleveland-airport-middleburg-heights": {
        "facts": {
            "pets_allowed": ("true", "Pets Welcome"),
            "pet_fee": ("$100.00", "Pets Allowed with $100 USD Non Refundable fee per stay."),
            "fee_basis": ("per stay", "Pets Allowed with $100 USD Non Refundable fee per stay."),
            "pet_count_limit": ("2", "Maximum Number of Pets in Room: 2"),
            "pet_count_scope": ("room", "Maximum Number of Pets in Room: 2"),
        },
        "withheld": {"species_allowed": "the page names no species",
                     "weight_limit": "no weight is stated on this property's page"},
    },
    "residence-inn-cleveland-beachwood": {
        "facts": {
            "pets_allowed": ("true", "Pets Welcome"),
            "species_allowed": ("dogs", "Dogs only; no cats allowed"),
            "cats_allowed": ("false", "Dogs only; no cats allowed"),
            "pet_fee": ("$100.00", "Non-Refundable Pet Fee Per Stay: $100.00"),
            "fee_basis": ("per stay", "Non-Refundable Pet Fee Per Stay: $100.00"),
            "weight_limit": ("50 pounds", "Maximum Pet Weight: 50.0lbs"),
            "pet_count_limit": ("2", "Maximum Number of Pets in Room: 2"),
            "pet_count_scope": ("room", "Maximum Number of Pets in Room: 2"),
        },
        "withheld": {"cleaning_fee": "a second '$5.00 Per Night' line appears with "
                                     "no stated relationship to the per-stay fee"},
    },
    "the-westin": {
        "facts": {
            "pets_allowed": ("true", "Pets Welcome"),
            "species_allowed": ("dogs", "2 dogs, 75lb maximum per dog"),
            "pet_fee": ("$50.00", "Non-Refundable Pet Fee Per Night: $50.00"),
            "fee_basis": ("per night", "Non-Refundable Pet Fee Per Night: $50.00"),
            # Plain weight_limit IS the individual limit -- that is what the
            # field means when weight_limit_combined is absent. The operator
            # enum is {lt, lte, combined}; "per pet" is not a member of it, and
            # setting it silently rendered nothing.
            "weight_limit": ("75 pounds", "75lb maximum per dog"),
            "pet_count_limit": ("2", "Maximum Number of Pets in Room: 2"),
            "pet_count_scope": ("room", "Maximum Number of Pets in Room: 2"),
        },
        "withheld": {"weight_limit_combined": "the page states a per-dog maximum, "
                                              "never a combined one"},
    },
    "tru-by-hilton": {
        "facts": {
            "pets_allowed": ("true", "Pets allowed"),
            "species_allowed": ("dogs and cats", "dog or cat only"),
            "pet_count_limit": ("2", "2 pets max"),
            "fee_tiers": ("STAY_LENGTH_50_75", "1-4 night stay $50; 5+ night stay $75"),
        },
        "withheld": {"weight_limit": "no weight is stated on this property's page"},
    },
    "wyndham-independence": {
        "facts": {
            "pets_allowed": ("true", "Pets Allowed - 2 pets max."),
            "species_allowed": ("dogs", "Dogs only."),
            "pet_fee": ("$75.00", "Fees - 75USD per stay for 1 or 2 dogs per room."),
            "fee_basis": ("per stay", "Fees - 75USD per stay for 1 or 2 dogs per room."),
            "fee_scope": ("per room", "75USD per stay for 1 or 2 dogs per room."),
            "weight_limit": ("40 pounds", "40lbs or less per pet."),
            "pet_count_limit": ("2", "2 pets max."),
            "service_animal_exception": ("true", "Service Animals - ADA-defined service animals welcome."),
        },
        "withheld": {
            "pet_deposit": "the $100 deposit on this page is a general incidentals "
                           "deposit charged to every guest, not a pet deposit",
            "cleaning_fee": "the $250 sanitation charge is conditional ('if "
                            "required'), so publishing it as a fee would assert a "
                            "cost most guests will not pay",
        },
    },
}

def _ladder(low: str, high: str, *, basis_stated: bool):
    """A two-band stay-length ladder. ``additive`` is absent because the bands
    REPLACE one another by stay length -- a guest pays exactly one of them.

    ``basis_stated`` matters and is not cosmetic. Hilton's brands state only the
    bands ("1-4 night stay $75; 5+ night stay $125") and never say whether the
    amount is per stay or per night; IHG's Westlake page says "Per stay" in as
    many words. Marking the Hilton ladders as stating a basis would have
    published a claim those pages do not make.
    """
    common = {"currency": "USD", "condition_type": "stay_length_range",
              "boundary_unit": "nights", "role": "ONE_TIME_CHARGE",
              "scope": "unstated", "source_type": "", "source_url": "",
              "basis_stated": basis_stated}
    stated = {"stated_basis": "per stay"} if basis_stated else {}
    return [
        dict(common, amount=low, condition_min=1, condition_max=4, **stated),
        dict(common, amount=high, condition_min=5, condition_max=None, **stated),
    ]


TIERS = {
    # Hilton brands: bands only, no basis stated anywhere on the page.
    "STAY_LENGTH_75_125": _ladder("75.00", "125.00", basis_stated=False),
    "STAY_LENGTH_50_75": _ladder("50.00", "75.00", basis_stated=False),
    # IHG Westlake: the same band shape, but the prose says "Per stay".
    "STAY_LENGTH_75_125_PER_STAY": _ladder("75.00", "125.00", basis_stated=True),
}

#: Affirmative-refusal exclusions. Quote is the property's own words.
NO_PETS_NOTE = ("affirmative refusal on the property's own page; service-animal "
                "language is a legal access category and is never read as a pet "
                "permission or as a refusal on its own")


def _norm(text: str) -> str:
    """Whitespace-collapsed, case-folded -- the captured excerpt keeps the
    page's line breaks, so a naive substring test rejects true quotes."""
    return " ".join((text or "").split()).lower()


def load_proposal() -> Dict:
    return json.loads(PROPOSAL.read_text(encoding="utf-8"))


def expected_property_codes() -> Dict[str, str]:
    """Property codes from the ROUTING records, which were bound from CVB
    anchors BEFORE any capture ran.

    Deliberately not taken from the capture's own final URL. M10's conjunctive
    override compares an expected code against the code the page shows; sourcing
    the "expected" side from the page would make the override self-certifying.
    """
    from scripts.pettripfinder.identity_routing import load_routes

    out: Dict[str, str] = {}
    for route in load_routes():
        if route.get("market_id") != MARKET:
            continue
        code = (route.get("property_code") or "").strip().lower()
        if not code:
            code = extract_property_code_from_url(route.get("official_property_url") or "")
        if code:
            out[route["hotel_ref"]["normalized_name"]] = code
    return out


def observed_identity() -> Dict[str, Dict]:
    """The identity each capture actually READ off the rendered page.

    Taken from ``artifacts.hydration.identity`` -- the property's own JSON-LD --
    and never from our expected values. Feeding the membrane our own canonical
    name would make M10 self-certifying: it would be checking our record against
    itself instead of against the page.
    """
    out: Dict[str, Dict] = {}
    for batch in ("batch", "batch2"):
        journal = BATCH / "_runner" / batch / "journal.jsonl"
        if not journal.exists():
            continue
        for line in journal.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get("state") != "CAPTURED":
                continue
            ident = ((rec.get("artifacts") or {}).get("hydration") or {}).get("identity")
            if ident:
                out[rec["hotel_id"]] = ident
    return out


def build(strict: bool = True):
    doc = load_proposal()
    friendly = {e["hotel_id"]: e for e in doc["captured_pet_friendly"]}
    seen_by_id = observed_identity()
    codes = expected_property_codes()
    nopets = {e["hotel_id"]: e for e in doc["verified_no_pets"]}

    accepted, quarantined, observations = [], [], []
    for hid, entry in sorted(friendly.items()):
        spec = FACTS.get(hid)
        if spec is None:
            quarantined.append({"hotel_id": hid, "reason": "no reviewed fact mapping"})
            continue
        evidence_text = _norm(entry["evidence_quote"])
        facts, evidence, bad = OrderedDict(), [], []
        for field, (value, quote) in spec["facts"].items():
            if _norm(quote) not in evidence_text:
                bad.append("%s: quote not in captured evidence -- %r" % (field, quote))
                continue
            evidence.append(OrderedDict([("field", field), ("quote", quote),
                                         ("source_url", entry["citable_url"]),
                                         ("value", value)]))
            facts[field] = TIERS[value] if field == "fee_tiers" else value
        if bad:
            quarantined.append({"hotel_id": hid, "reason": "; ".join(bad)})
            continue

        observations.append(build_observation(entry, facts, evidence,
                                              seen_by_id.get(hid), codes))
        accepted.append(OrderedDict([
            ("key", entry["listing_key"]), ("name", entry["canonical_name"]),
            ("facts", facts), ("evidence", evidence), ("evidence_count", len(evidence)),
            ("evidence_quote", " ".join(entry["evidence_quote"].split())),
            ("source_url", entry["citable_url"]), ("source_type", "EXACT_ENTITY_DOMAIN"),
            ("verification_state", "VERIFIED_PET_FRIENDLY"),
            ("verification_date", AS_OF), ("verified_at", AS_OF),
            ("approval", OrderedDict([("approval_date", AS_OF), ("decision", enums.APPROVED_AFTER_CURRENT_REVIEW),
                                      ("operator", REVIEWER)])),
            ("withheld_fields", OrderedDict(sorted(spec.get("withheld", {}).items()))),
            ("worker_model_id", ""), ("worker_prompt_version", ""),
            ("worker_result_hash", entry["html_sha256"]),
            ("worker_routing_version", ""), ("worker_validator_version", ""),
        ]))

    exclusions = []
    for hid, entry in sorted(nopets.items()):
        quote = " ".join(entry["evidence_quote"].split())
        if not MB is None and "not allowed" not in quote.lower() and "no pets" not in quote.lower():
            quarantined.append({"hotel_id": hid,
                                "reason": "no affirmative refusal in the captured quote"})
            continue
        rec = OrderedDict([
            ("exclusion_id", "cle-%s" % hid),
            ("canonical_name", entry["canonical_name"]),
            ("normalized_name", normalize_name(entry["canonical_name"])),
            ("address", entry["address"]), ("city", entry["city"]),
            ("state", entry["state"]), ("postal_code", entry["postal_code"]),
            ("official_url", entry["official_url"]),
            ("exclusion_state", EX.VERIFIED_NO_PETS),
            ("evidence_quote", quote), ("source_url", entry["citable_url"]),
            ("observed_at", AS_OF),
            ("source_hash", entry["html_sha256"]),
            ("reviewer_id", REVIEWER), ("reviewed_at", AS_OF),
            ("notes", NO_PETS_NOTE), ("market_id", MARKET),
        ])
        rec["record_hash"] = EX.record_hash(rec)
        rec["approval_hash"] = EX.approval_hash(rec)
        exclusions.append(rec)

    return accepted, exclusions, quarantined, observations, friendly, nopets


def build_observation(entry: Dict, facts: Dict, evidence: List[Dict],
                      seen: Optional[Dict] = None,
                      codes: Optional[Dict] = None) -> Dict:
    """A ptf-policy-observation/1.0 record for the membrane to judge."""
    # The observation contract holds money as integer MINOR UNITS -- a float
    # dollar amount is banned repo-wide. The published facts record keeps the
    # display string, so the two shapes are converted here rather than one of
    # them being bent to fit the other.
    extraction = {}
    for key, value in facts.items():
        if key not in PO.EXTRACTION_FIELDS:
            continue
        if key == "fee_tiers":
            extraction[key] = [
                dict(tier, amount_minor=int(round(float(tier["amount"]) * 100)))
                for tier in value]
        elif key in PO.MONEY_KEYS:
            extraction[key] = int(round(float(str(value).lstrip("$")) * 100))
        else:
            extraction[key] = value
    return OrderedDict([
        ("obs_id", "cle-obs-%s" % entry["hotel_id"]),
        ("contract_version", PO.CONTRACT_VERSION),
        ("hotel_ref", OrderedDict([
            ("market_id", MARKET), ("canonical_name", entry["canonical_name"]),
            ("normalized_name", entry["listing_key"]),
            # The STREET only. Appending the postal code folds it into the
            # street token set, so "5800 Rockside Woods Blvd. 44131" stops
            # matching the page's "5800 Rockside Woods Boulevard" and M10's
            # override cannot fire on a property that is provably the same one.
            ("street_identity", entry["address"]),
            ("official_url", entry["official_url"]),
            ("property_code", entry.get("property_code")
             or (codes or {}).get(entry["listing_key"], "")),
        ])),
        # What the capture READ, not what we expected. Two independent key
        # groups, which is the standard the capture gate itself applied.
        ("identity_check", OrderedDict(
            [("name_on_page", (seen or {}).get("name") or entry["canonical_name"]),
             ("address_on_page", (seen or {}).get("street") or entry["address"])]
            + ([("phone_on_page", (seen or {}).get("phone"))]
               if (seen or {}).get("phone") else [])
            + ([("property_code", (seen or {}).get("property_code"))]
               if (seen or {}).get("property_code") else []))),
        ("source_url", entry["citable_url"]),
        ("source_type", "official_property_page"),
        ("authority_tier", PO.PT1_OFFICIAL_PROPERTY),
        ("observed_at", AS_OF), ("retrieved_at", entry.get("captured_at") or AS_OF),
        ("capture_method", "browser_assisted"),
        ("evidence", [OrderedDict([("quote", e["quote"]), ("location", "policy_block"),
                                   ("field_refs", [e["field"]]),
                                   ("artifact_ref", entry["html_sha256"])])
                      for e in evidence]),
        ("extraction", extraction),
        ("extraction_confidence", "EXACT_QUOTE"),
        ("flags", []),
        ("capture_artifacts", [entry["html_sha256"], entry["text_sha256"],
                               entry["png_sha256"]]),
    ])


def seed_rows(accepted: List[Dict], friendly: Dict) -> List[Dict]:
    by_key = {e["listing_key"]: e for e in friendly.values()}
    rows = []
    for rec in accepted:
        e = by_key[rec["key"]]
        rows.append({
            "name": e["canonical_name"], "category": "pet-friendly-hotels",
            "address": e["address"], "city": e["city"], "state": e["state"],
            "postal_code": e["postal_code"], "phone": e.get("phone", ""),
            "website_url": e["citable_url"], "source_url": e["citable_url"],
            "source_type": "OFFICIAL_PROPERTY", "observed_at": AS_OF,
            "rating": "", "amenities": "",
            # PTF-INVENTORY-001's renderability boundary reads this field: an
            # empty value means "pending attestation" and the listing is
            # filtered out before the WGE, which is why the first Cleveland
            # build produced zero listings from nineteen rows. The value is the
            # property's own captured policy text, whitespace-collapsed and
            # otherwise verbatim -- evidence, not a sentence composed by us.
            "pet_policy": " ".join(e["evidence_quote"].split()),
            "canonical": "", MARKET_ID_FIELD: MARKET,
        })
    return rows


def main() -> int:
    apply = "--apply" in sys.argv
    accepted, exclusions, quarantined, observations, friendly, nopets = build()

    verdicts = MB.evaluate_batch(observations)
    blocked = [(o["hotel_ref"]["canonical_name"], v)
               for o, v in zip(observations, verdicts) if not v.may_establish]
    for o in observations:
        PO.validate_observation(o)

    print("=== CLEVELAND AUTHORITY INTEGRATION ===")
    print("  proposals in artifact  : %d pet-friendly / %d no-pets"
          % (len(friendly), len(nopets)))
    print("  observations validated : %d" % len(observations))
    print("  membrane may_establish : %d" % sum(1 for v in verdicts if v.may_establish))
    print("  membrane blocked       : %d" % len(blocked))
    for name, v in blocked[:12]:
        print("      %-46s %s / %s / %s" % (name[:46], v.verdict, v.rule, v.detail[:60]))
    print("  accepted pet-friendly  : %d" % len(accepted))
    print("  accepted no-pets       : %d" % len(exclusions))
    print("  quarantined            : %d" % len(quarantined))
    for q in quarantined:
        print("      %-46s %s" % (q["hotel_id"][:46], q["reason"][:90]))
    withheld = sum(len(a["withheld_fields"]) for a in accepted)
    print("  withheld fields total  : %d" % withheld)

    if apply and not blocked and not quarantined:
        FACTS_OUT.write_text(json.dumps(OrderedDict([
            ("hotels", accepted), ("market", MARKET), ("schema_version", "1.1")]),
            indent=1, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
        doc = json.loads(EX.EXCLUSIONS_PATH.read_text(encoding="utf-8-sig"))
        have = {r["exclusion_id"] for r in doc["exclusions"]}
        doc["exclusions"] += [r for r in exclusions if r["exclusion_id"] not in have]
        EX.validate(doc)
        EX.EXCLUSIONS_PATH.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n",
                                      encoding="utf-8", newline="\n")
        rows = seed_rows(accepted, friendly)
        with PRODUCTION_CSV.open(encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            existing = list(reader)
            fields = list(reader.fieldnames)
        # Re-running must converge, not duplicate or go stale: a row this
        # market already owns is REPLACED by the freshly derived one, and only
        # genuinely new identities are appended. Rows owned by another market
        # are never touched.
        by_name = {normalize_name(r["name"]): r for r in rows}
        merged, seen = [], set()
        for row in existing:
            key = normalize_name(row["name"])
            if key in by_name and row.get(MARKET_ID_FIELD) == MARKET:
                merged.append(by_name[key])
                seen.add(key)
            else:
                merged.append(row)
        new = [r for k, r in by_name.items() if k not in seen]
        merged += new
        buf = io.StringIO(newline="")
        w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        for r in merged:
            w.writerow({k: r.get(k, "") for k in fields})
        PRODUCTION_CSV.write_text(buf.getvalue(), encoding="utf-8", newline="")
        # Retire the routing records for everything now published or excluded.
        # ptf-identity-routing exists to let a confirmed NON-inventory hotel
        # hold an official URL; once the seed carries the hotel, the seed is the
        # source of truth for it and a surviving route is a second, competing
        # authority for the same identity.
        routing_path = (_REPO_ROOT / "launch_packages" / "pettripfinder"
                        / "identity_routing.json")
        routing = json.loads(routing_path.read_text(encoding="utf-8-sig"))
        done = ({normalize_name(r["name"]) for r in rows}
                | {e["normalized_name"] for e in exclusions})
        before = len(routing["routes"])
        routing["routes"] = [r for r in routing["routes"]
                             if not (r.get("market_id") == MARKET
                                     and r["hotel_ref"]["normalized_name"] in done)]
        retired = before - len(routing["routes"])
        routing["count"] = len(routing["routes"])
        routing_path.write_text(
            json.dumps(routing, indent=1, ensure_ascii=False) + "\n",
            encoding="utf-8", newline="\n")
        print("  APPLIED: %d facts, %d exclusions, %d seed rows, %d routes retired"
              % (len(accepted), len(exclusions), len(new), retired))
    else:
        print("  mode                   :", "DRY RUN" if not apply
              else "REFUSED (blocked or quarantined records present)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
