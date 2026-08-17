"""PTF-CINCINNATI-PASS1-AUTHORITY-APPLICATION-001 -- apply the founder's 26 rulings.

Deterministic application of the 26 ready decisions recorded across
cincinnati_capture_pass1_founder_decisions_batch{A,B,C}.json (checkpoint
087ee11). 20 publish to hotel_policy_facts_cincinnati-oh.json, 6 become
VERIFIED_NO_PETS exclusions in the Cincinnati shard. Cincinnati's Fidelity
Hotel (HOLD_PREOPENING) and 21c Museum Hotel (HOLD_FOR_RECAPTURE,
ARTIFACT_INSUFFICIENT) are outside this application.

EVIDENCE-CAPTURE CAVEAT (recorded once, here, rather than repeated per
record): PTF-CINCINNATI-CAPTURE-PASS1-001 recorded each row's artifact
SHA256 (computed in-browser via crypto.subtle.digest against the page's
live outerHTML) and an exact_quote extracted from that same live DOM in
the same JavaScript call, but did not persist the raw HTML/text bytes to
disk the way Cleveland's cleveland_pass4_capture_integration.py did. That
means this application cannot re-run Cleveland's own verify_capture()
byte-for-byte cross-check against stored raw artifacts -- there are no
stored bytes left to check against, only the sha256 and quote captured at
the time. Every quote below is a single contiguous slice taken directly
from a regex/indexOf match against the live page (never concatenated
across distant ranges), so the specific forgery verify_capture() guards
against does not apply here, but the independent re-verification step
itself did not run. Recorded as a real limitation of this capture design,
not glossed over.

Run:  python -m scripts.pettripfinder.cincinnati_pass1_decision_application \
          [--apply]
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import hotel_exclusions as EX                     # noqa: E402
from scripts.pettripfinder import market_authority as MA                     # noqa: E402
from scripts.pettripfinder.contracts import enums                            # noqa: E402
from scripts.pettripfinder.contracts import evidence as evidence_contract    # noqa: E402
from scripts.pettripfinder.contracts import policy_schema                    # noqa: E402
from scripts.pettripfinder.contracts import withholding                      # noqa: E402
from scripts.pettripfinder.contracts.evidence import quote_is_contiguous     # noqa: E402
from scripts.pettripfinder.contracts.fee_computation import classify         # noqa: E402
from scripts.pettripfinder.market_ownership import MARKET_ID_FIELD           # noqa: E402
from scripts.pettripfinder.policy_migration import (                         # noqa: E402
    evidence_hash, evidence_ref_for, record_hash,
)

WORK_ORDER = "PTF-CINCINNATI-PASS1-AUTHORITY-APPLICATION-001"
MARKET = "cincinnati-oh"
DECISION_DATE = "2026-08-17"
FOUNDER = "jfields80"
CAPTURED_AT = "2026-08-17"
CAPTURE_METHOD = "attended_chrome_render"
GRADE = enums.GRADE_PT1_FIRST_PARTY

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
CENSUS_PATH = LP / "identity_census" / "cincinnati-oh.json"
FACTS_PATH = LP / "hotel_policy_facts_cincinnati-oh.json"

EVIDENCE_CAVEAT = (
    "Artifact evidence for this record consists of a SHA256 computed live "
    "against the page's rendered outerHTML and a quote extracted from the "
    "same DOM in the same JavaScript call, both captured under "
    "PTF-CINCINNATI-CAPTURE-PASS1-001. Raw HTML/text bytes were not "
    "persisted to disk, so this application could not independently "
    "re-verify the quote against stored artifact bytes the way "
    "cleveland_pass4_capture_integration.py's verify_capture() does; the "
    "sha256 and quote are taken as recorded at capture time."
)


def _money(cents: int, currency: str = "USD") -> Dict:
    return {"amount_cents": cents, "currency": currency}


def _weight(value: float, unit: str, scope: str, operator: str = "lte") -> Dict:
    return {"value": value, "unit": unit, "operator": operator, "scope": scope}


def _evidence(field: str, quote: str, source_url: str, value_disp: str,
             artifact_sha: Optional[str]) -> Dict:
    entry = OrderedDict([
        ("field", field),
        ("quote", quote),
        ("source_url", source_url),
        ("value", value_disp),
        ("evidence_ref", ""),
        ("artifact_class", enums.PUBLICATION_GRADE_EVIDENCE),
        ("artifact_sha256", ("sha256:%s" % artifact_sha) if artifact_sha else ""),
        ("artifact_kind", enums.ARTIFACT_RENDERED_HTML),
        ("captured_at", CAPTURED_AT),
        ("capture_method", CAPTURE_METHOD),
        ("source_grade", GRADE),
    ])
    entry["evidence_ref"] = evidence_ref_for(entry)
    return entry


def _withhold(field: str, reason_code: str, reason: str, refs: List[str]) -> Dict:
    return OrderedDict([
        ("reason_code", reason_code),
        ("reason", reason),
        ("evidence_refs", refs),
    ])


# --------------------------------------------------------------------------- #
# Per-row specs: (identity_key, source_url, artifact_sha256_or_None,
# facts-builder). Each builder returns (facts, evidence_list, withheld_dict,
# service_animal_statement_or_None).
# --------------------------------------------------------------------------- #

def _positive(identity_key, source_url, sha, builder):
    return dict(identity_key=identity_key, source_url=source_url, sha=sha,
               builder=builder)


def spec_best_western_clermont(url, sha):
    quote = ("PET POLICY\nWe are Pet Friendly and allow up to two dogs in a "
             "limited number of rooms. The size limit for any one dog shall "
             "be 80 pounds. Other pet types (e.g., cats) may be allowed upon "
             "the hotel’s approval prior to arrival. The Pet Friendly "
             "rate is 40 USD per day.")
    facts = OrderedDict()
    facts["pets_allowed"] = True
    facts["species"] = OrderedDict([("dog", "accepted"), ("cat", "conditional")])
    facts["pet_count_limit"] = 2
    facts["pet_count_scope"] = "room"
    facts["weight_limit"] = _weight(80, "lb", "per_pet")
    facts["pet_fee"] = dict(_money(4000), basis="per_day", scope="per_pet")
    ev = [
        _evidence("pets_allowed", quote, url, "true", sha),
        _evidence("species", quote, url, "dog=accepted, cat=conditional", sha),
        _evidence("pet_count_limit", quote, url, "2", sha),
        _evidence("weight_limit", quote, url, "80 lb per dog", sha),
        _evidence("pet_fee", quote, url, "$40.00 per day", sha),
    ]
    return facts, ev, {}, None


def spec_best_western_inn_florence(url, sha):
    quote = ("PET POLICY\nWe are Pet Friendly and allow up to two dogs in a "
             "limited number of rooms. The size limit for any one dog shall "
             "be 80 pounds. Other pet types (e.g., cats) may be allowed upon "
             "the hotel’s approval prior to arrival. The Pet Friendly "
             "rate is 30 USD per day.")
    facts = OrderedDict()
    facts["pets_allowed"] = True
    facts["species"] = OrderedDict([("dog", "accepted"), ("cat", "conditional")])
    facts["pet_count_limit"] = 2
    facts["pet_count_scope"] = "room"
    facts["weight_limit"] = _weight(80, "lb", "per_pet")
    facts["pet_fee"] = dict(_money(3000), basis="per_day", scope="per_pet")
    ev = [
        _evidence("pets_allowed", quote, url, "true", sha),
        _evidence("species", quote, url, "dog=accepted, cat=conditional", sha),
        _evidence("pet_count_limit", quote, url, "2", sha),
        _evidence("weight_limit", quote, url, "80 lb per dog", sha),
        _evidence("pet_fee", quote, url, "$30.00 per day", sha),
    ]
    return facts, ev, {}, None


def spec_best_western_whitewater(url, sha):
    quote = ("PET POLICY\nWe are Pet Friendly and allow up to two dogs in a "
             "limited number of rooms. The size limit for any one dog shall "
             "be 80 pounds. Other pet types (e.g., cats) may be allowed upon "
             "the hotel’s approval prior to arrival. The Pet Friendly "
             "rate is 20 USD per day.")
    facts = OrderedDict()
    facts["pets_allowed"] = True
    facts["species"] = OrderedDict([("dog", "accepted"), ("cat", "conditional")])
    facts["pet_count_limit"] = 2
    facts["pet_count_scope"] = "room"
    facts["weight_limit"] = _weight(80, "lb", "per_pet")
    facts["pet_fee"] = dict(_money(2000), basis="per_day", scope="per_pet")
    ev = [
        _evidence("pets_allowed", quote, url, "true", sha),
        _evidence("species", quote, url, "dog=accepted, cat=conditional", sha),
        _evidence("pet_count_limit", quote, url, "2", sha),
        _evidence("weight_limit", quote, url, "80 lb per dog", sha),
        _evidence("pet_fee", quote, url, "$20.00 per day", sha),
    ]
    return facts, ev, {}, None


def _esa_bare(name):
    def _b(url, sha):
        quote = ("Yes. %s offers pet-friendly rooms, so you can bring your "
                 "furry companion along for your stay." % name)
        facts = OrderedDict([("pets_allowed", True)])
        ev = [_evidence("pets_allowed", quote, url, "true", sha)]
        return facts, ev, {}, None
    return _b


def _bare_pets_allowed(quote):
    def _b(url, sha):
        facts = OrderedDict([("pets_allowed", True)])
        ev = [_evidence("pets_allowed", quote, url, "true", sha)]
        return facts, ev, {}, None
    return _b


def spec_doubletree_airport(url, sha):
    quote = "Pets\nNon-refundable fee: $25.00\nMax weight: 25 lbs\nMax size: Medium"
    facts = OrderedDict()
    facts["pets_allowed"] = True
    facts["pet_fee"] = dict(_money(2500), refundable=False)
    facts["weight_limit"] = _weight(25, "lb", "per_pet")
    ev = [
        _evidence("pets_allowed", quote, url, "true", sha),
        _evidence("pet_fee", quote, url, "$25.00, non-refundable", sha),
        _evidence("weight_limit", quote, url, "25 lb, max size Medium", sha),
    ]
    withheld = {
        "pet_fee.basis": _withhold(
            "pet_fee.basis", enums.SOURCE_AMBIGUOUS,
            "The page states only the dollar amount; it never says per-night "
            "or per-stay. No basis is invented merely because the amount is "
            "explicit.", [ev[1]["evidence_ref"]]),
    }
    return facts, ev, withheld, None


def spec_hometowne_studios(url, sha):
    quote = ("Pet Policy:  Service animals and Emotional Support Animals "
             "(“Assistance Animals”) are welcome at all of our "
             "properties and must be declared at check-in. Pets are "
             "permitted with a $10.00 fee per night up to $100.00 a month.")
    facts = OrderedDict()
    facts["pets_allowed"] = True
    facts["pet_fee"] = dict(_money(1000), basis="per_night")
    ev = [
        _evidence("pets_allowed", quote, url, "true", sha),
        _evidence("pet_fee", quote, url, "$10.00 per night", sha),
        _evidence("monthly_cap", quote, url, "up to $100.00 a month", sha),
    ]
    withheld = {
        "monthly_fee_cap": _withhold(
            "monthly_fee_cap", enums.SCHEMA_CANNOT_REPRESENT,
            "Schema 1.2's fee_basis enum is exactly (per_night, per_day, "
            "per_stay) -- no per_month member exists. The $100/month cap is "
            "not converted to a per-stay cap, not turned into a synthesized "
            "night limit, and the property is not dropped.",
            [ev[2]["evidence_ref"]]),
    }
    sas = ({"stated": True, "charges_stated": "not_addressed"},
          "Service animals and Emotional Support Animals are welcome and "
          "must be declared at check-in.")
    return facts, ev, withheld, sas


def _red_roof(name):
    def _b(url, sha):
        quote = ("Pet Policy: One, well-behaved domestic pet (cat or dog) "
                 "Stays Free! Pets must be declared at check-in. Up to 2 "
                 "pets allowed per room. Second pet $15/ night, not to "
                 "exceed 7 nights or $105 per pet per stay. Pet not to "
                 "exceed 80 pounds. Service and emotional support animals "
                 "are always welcome.")
        facts = OrderedDict()
        facts["pets_allowed"] = True
        facts["species"] = OrderedDict([("cat", "accepted"), ("dog", "accepted")])
        facts["pet_count_limit"] = 2
        facts["pet_count_scope"] = "room"
        facts["pet_fee"] = dict(_money(1500), basis="per_night", scope="per_pet")
        facts["fee_cap"] = dict(_money(10500), basis="per_stay",
                                qualifier_stated=True,
                                applies_to_pet_ordinal=2, trigger_max_nights=7)
        ev = [
            _evidence("pets_allowed", quote, url, "true", sha),
            _evidence("species", quote, url, "cat=accepted, dog=accepted", sha),
            _evidence("pet_count_limit", quote, url, "2", sha),
            _evidence("pet_fee", quote, url, "$15.00 per night (second pet)", sha),
            _evidence("fee_cap", quote, url, "$105 per stay, second pet, "
                     "max 7 nights", sha),
            _evidence("weight_limit", quote, url, "80 lb (scope ambiguous)", sha),
        ]
        withheld = {
            "weight_limit": _withhold(
                "weight_limit", enums.SOURCE_AMBIGUOUS,
                "The singular 'Pet not to exceed 80 pounds' does not "
                "disambiguate individual vs combined scope, and weight_limit "
                "requires a scope to publish structurally -- withheld rather "
                "than guessed.", [ev[5]["evidence_ref"]]),
        }
        sas = ({"stated": True, "charges_stated": "not_addressed"},
              "Service and emotional support animals are always welcome.")
        return facts, ev, withheld, sas
    return _b


def spec_baymont_lawrenceburg(url, sha):
    quote = ("PET & SERVICE ANIMAL POLICY\nService Animals - ADA-defined "
             "service animals welcome / Dogs Allowed - 2 pets max. Dogs "
             "only. / Fees - 25USD per pet per night. / Other Information - "
             "Contact hotel for additional details and availability.")
    facts = OrderedDict()
    facts["pets_allowed"] = True
    facts["species"] = OrderedDict([("dog", "accepted")])
    facts["pet_count_limit"] = 2
    facts["pet_fee"] = dict(_money(2500), basis="per_night", scope="per_pet")
    ev = [
        _evidence("pets_allowed", quote, url, "true", sha),
        _evidence("species", quote, url, "dog=accepted (dogs only)", sha),
        _evidence("pet_count_limit", quote, url, "2", sha),
        _evidence("pet_fee", quote, url, "$25.00 per pet per night", sha),
    ]
    sas = ({"stated": True, "charges_stated": "not_addressed"},
          "ADA-defined service animals welcome.")
    return facts, ev, {}, sas


def spec_days_inn_north(url, sha):
    quote = ("PET & SERVICE ANIMAL POLICY\nService Animals - ADA-defined "
             "service animals welcome. / Pets Allowed. / Fees - 15USD per "
             "night. / Other Information - All pets must be registered at "
             "the time of check in. Contact hotel for additional details "
             "and availability.")
    facts = OrderedDict()
    facts["pets_allowed"] = True
    facts["pet_fee"] = dict(_money(1500), basis="per_night")
    facts["general_restrictions"] = "All pets must be registered at the time of check in."
    ev = [
        _evidence("pets_allowed", quote, url, "true", sha),
        _evidence("pet_fee", quote, url, "$15.00 per night", sha),
        _evidence("general_restrictions", quote, url,
                 "must be registered at check-in", sha),
    ]
    sas = ({"stated": True, "charges_stated": "not_addressed"},
          "ADA-defined service animals welcome.")
    return facts, ev, {}, sas


def spec_butler_inn(url, sha):
    quote = "Pets are allowed. Charges may apply."
    facts = OrderedDict([("pets_allowed", True)])
    ev = [
        _evidence("pets_allowed", quote, url, "true", sha),
        _evidence("pet_fee", quote, url, "unquantified -- 'charges may apply'", sha),
    ]
    withheld = {
        "pet_fee": _withhold(
            "pet_fee", enums.SOURCE_AMBIGUOUS,
            "The source acknowledges a fee exists without quantifying it. "
            "No amount, basis or scope is invented; no other_charges entry "
            "is created merely to hold an unknown figure.",
            [ev[1]["evidence_ref"]]),
    }
    return facts, ev, withheld, None


def spec_sonesta_east(url, sha):
    quote = ("Sonesta ES Suites Cincinnati - Sharonville East is "
             "pet-friendly and welcomes well-mannered pets, with no breed "
             "or weight restrictions. One pet is permitted per suite. $75 "
             "fee applies for stays up to 7 nights; a $150 fee applies per "
             "month for all longer stays.")
    facts = OrderedDict()
    facts["pets_allowed"] = True
    facts["pet_count_limit"] = 1
    facts["pet_count_scope"] = "room"
    facts["weight_limit_stated_none"] = True
    facts["pet_fee"] = dict(_money(7500), basis="per_stay")
    ev = [
        _evidence("pets_allowed", quote, url, "true", sha),
        _evidence("pet_count_limit", quote, url, "1", sha),
        _evidence("weight_limit_stated_none", quote, url,
                 "no breed or weight restrictions", sha),
        _evidence("pet_fee", quote, url, "$75 for stays up to 7 nights", sha),
        _evidence("long_stay_fee", quote, url,
                 "$150 fee applies per month for all longer stays", sha),
    ]
    withheld = {
        "long_stay_fee": _withhold(
            "long_stay_fee", enums.SCHEMA_CANNOT_REPRESENT,
            "fee_basis has no per_month member; the $150/month long-stay "
            "term is withheld rather than converted or dropped.",
            [ev[4]["evidence_ref"]]),
    }
    return facts, ev, withheld, None


def spec_sonesta_west(url, sha):
    quote = ("Sonesta ES Suites Cincinnati - Sharonville West is "
             "pet-friendly and welcomes well-mannered pets, with no breed "
             "or weight restrictions. Up to two pets are permitted per "
             "suite. $75 fee applies for stays up to 7 nights; $150 for "
             "all longer stays.")
    facts = OrderedDict()
    facts["pets_allowed"] = True
    facts["pet_count_limit"] = 2
    facts["pet_count_scope"] = "room"
    facts["weight_limit_stated_none"] = True
    facts["pet_fee"] = dict(_money(7500), basis="per_stay")
    ev = [
        _evidence("pets_allowed", quote, url, "true", sha),
        _evidence("pet_count_limit", quote, url, "2", sha),
        _evidence("weight_limit_stated_none", quote, url,
                 "no breed or weight restrictions", sha),
        _evidence("pet_fee", quote, url, "$75 for stays up to 7 nights", sha),
        _evidence("long_stay_fee", quote, url,
                 "$150 for all longer stays (no basis stated)", sha),
    ]
    withheld = {
        "long_stay_fee": _withhold(
            "long_stay_fee", enums.SOURCE_AMBIGUOUS,
            "This property's own wording states no basis at all (not per "
            "month, stay, night or pet) for the $150 term -- genuine source "
            "ambiguity, not the schema gap East has. East's 'per month' "
            "wording is not imported onto this property.",
            [ev[4]["evidence_ref"]]),
    }
    return facts, ev, withheld, None


POSITIVE_SPECS: List[Tuple[str, str, Optional[str], "callable"]] = [
    ("best western clermont",
     "https://www.bestwestern.com/en_US/book/hotels-in-cincinnati/best-western-clermont/propertyCode.36135.html",
     "527679fdd7239c99740d93a52705141275d7043865c0208a86ed2a9c30ed539e",
     spec_best_western_clermont),
    ("best western inn florence",
     "https://www.bestwestern.com/en_US/book/hotels-in-florence/best-western-inn-florence/propertyCode.18070.html",
     "6c3d237991d90bf3a0c3a8eea053e12ad07ce9fa4d2ffe33b1c0504b4baca071",
     spec_best_western_inn_florence),
    ("best western plus whitewater inn",
     "https://www.bestwestern.com/en_US/book/hotels-in-harrison/best-western-plus-whitewater-inn/propertyCode.36158.html",
     "11a5f84ea71450123c9332216d2e193cc42e09d9566ea2291468c48dd43c3503",
     spec_best_western_whitewater),
    ("extended stay america florence meijer drive",
     "https://www.extendedstayamerica.com/hotels/oh/cincinnati/florence-meijer-drive",
     "4adda3dfa03de011c9165a269357f137327ffc8e7d252c25ff4a1a9688417ce5",
     _esa_bare("Extended Stay America Cincinnati - Florence - Meijer Drive")),
    ("extended stay america florence turfway road",
     "https://www.extendedstayamerica.com/hotels/oh/cincinnati/florence-turfway-rd",
     "9c80ad6d29ac966e82af728264f1cdfc082026a2acb090df296175c88bd9a7a0",
     _esa_bare("Extended Stay America Cincinnati - Florence - Turfway Rd.")),
    ("extended stay america suites cincinnati covington",
     "https://www.extendedstayamerica.com/hotels/oh/cincinnati/covington",
     "002bee18ecc56311520ae6e681ea4a5a15b38057ee722ab315a4c9c4babe4d1a",
     _esa_bare("Extended Stay America Cincinnati - Covington")),
    ("motel 6 florence commerce dr",
     "https://www.motel6.com/property/motel-florence-kentucky-us-294340/",
     "7719be8a1041dc2cc47bce7a837d89d731f645f3db1b61a83297ca2d7ac082d1",
     _bare_pets_allowed("Amenities\nPets Allowed")),
    ("motel 6 sharonville",
     "https://www.motel6.com/property/motel-cincinnati-oh-ohio-us-294230/",
     "21ebd9cf60e379f53f1f155eda2708fbd75a50dfcf1f34b4b5c214f89bc5d27d",
     _bare_pets_allowed("Amenities\nPets Allowed")),
    ("motel 6 walton richwood",
     "https://www.motel6.com/property/motel-walton-kentucky-us-294341/",
     "2d85e43fbe224abccc3c9dac8001225bc655ab38ee2f361d1cbe6492332c6489",
     _bare_pets_allowed("Amenities\nPets Allowed")),
    ("doubletree by hilton cincinnati airport",
     "https://www.hilton.com/en/hotels/cvghbdt-doubletree-cincinnati-airport/hotel-info/",
     "268203661af5d869dd7f55c863859e1df1483c14eb49c867298cffde90d67208",
     spec_doubletree_airport),
    ("hometowne studios florence cincinnati airport",
     "https://www.redroof.com/extendedstay/hometownestudios/property/ky/florence/hts1360",
     "6dfb5d3db11adef6522936512011da0d2611ec55a9b9b2193c491d2ccc562585",
     spec_hometowne_studios),
    ("red roof inn cincinnati east eastgate",
     "https://www.redroof.com/property/oh/cincinnati/rri080",
     "a266b77223339c3a325d0cbc9f940d6b5767d1d764d43384e609589e903cfc2d",
     _red_roof("east")),
    ("red roof inn cincinnati north mason",
     "https://www.redroof.com/property/oh/cincinnati/rri770",
     "e4b6f42e0dba370a761d3cdce2e3aaf469f048ac0b6ea04f5c5eda5ecf1ad5c7",
     _red_roof("north mason")),
    ("red roof inn greendale",
     "https://www.redroof.com/property/in/greendale/rri1301",
     "2abf808eae3547f9b53ab6b01f2f52240725c80413ea479ddca18788250f74a1",
     _red_roof("greendale")),
    ("red roof inn richwood",
     "https://www.redroof.com/property/ky/walton/rri1334",
     "c44d64c66239b427b99fd8a490ffa3a65397e65a09332cebc8a27ae4b30e1d1c",
     _red_roof("richwood")),
    ("sonesta es suites cincinnati sharonville east",
     "https://www.sonesta.com/sonesta-es-suites/oh/cincinnati/sonesta-es-suites-cincinnati-sharonville-east",
     "b248a7e66803e4e889ba53f2de15f301527fcfdb84eb4483566a68e66d90d96a",
     spec_sonesta_east),
    ("sonesta es suites cincinnati sharonville west",
     "https://www.sonesta.com/sonesta-es-suites/oh/cincinnati/sonesta-es-suites-cincinnati-sharonville-west",
     "dba9e4c320c3fba88b4dcc144e34dc73dd1dd54b5d402d876c5789e60fb39501",
     spec_sonesta_west),
    ("baymont by wyndham lawrenceburg",
     "https://www.wyndhamhotels.com/baymont/lawrenceburg-indiana/baymont-inn-suites-lawrenceburg/overview",
     "7e3b0a677ad590cf2e676e27da952f1049c156c905b11f0ac480e126d15f3f70",
     spec_baymont_lawrenceburg),
    ("days inn and suites by wyndham cincinnati north",
     "https://www.wyndhamhotels.com/days-inn/cincinnati-ohio/days-inn-and-suites-cincinnati-north/overview",
     "bcfc1a8888d24995a26e39a13d8a06582b4883e07e7d28f1841ebb9cd6d5f075",
     spec_days_inn_north),
    ("butler inn",
     "https://butlerinnoxford.com/policies",
     "9adee76ba546daaa34c518bb2c492a541ce8d68dc041edb814273018bf452128",
     spec_butler_inn),
]

NEGATIVE_SPECS: List[Tuple[str, str, Optional[str], str]] = [
    ("best western plus hannaford inn and suites",
     "https://www.bestwestern.com/en_US/book/hotels-in-cincinnati/best-western-plus-hannaford-inn-suites/propertyCode.36163.html",
     "50a2159fb26751aa61ef3c76228dd835e2c71b0e9ba7aa7c629ade75b979e054",
     "PET POLICY\nPets are not accepted."),
    ("best western premier mariemont inn",
     "https://www.bestwestern.com/en_US/book/hotels-in-cincinnati/best-western-premier-mariemont-inn/propertyCode.36077.html",
     "c05d05b4e25f09232b4260037492259b86235cb09681f0bc15c2681f1e8a8a6e",
     "PET POLICY\nPets are not accepted."),
    ("doubletree by hilton lawrenceburg",
     "https://www.hilton.com/en/hotels/cvgladt-doubletree-lawrenceburg/hotel-info/",
     "77af49d9058c03c596df9090c3603f26ab6e62f361ad724175b993a3f3f5107f",
     "Pets\nPets allowed: No"),
    ("baymont by wyndham monroe",
     "https://www.wyndhamhotels.com/baymont/monroe-ohio/baymont-monroe-ohio/overview",
     "f1a48de0f0b35609f3bc534731cd3d7a7616ded4391c046249a9f546a8f757c1",
     "PET & SERVICE ANIMAL POLICY\nService Animals - ADA defined service "
     "animals are welcome free of charge. Sorry no other pets are allowed."),
    ("days inn batavia",
     "https://www.wyndhamhotels.com/days-inn/batavia-ohio/days-inn-by-wyndham-batavia-ohio/overview",
     "0d2deb707529b2c1f95d7b7a08d1e47f9756df0571fcfdf75ce57e6e5a30f300",
     "PET POLICY\nADA defined service animals are welcome at this hotel. "
     "Sorry no other pets are allowed"),
    ("days inn cincinnati east",
     "https://www.wyndhamhotels.com/days-inn/cincinnati-ohio/days-inn-cincinnati-east/overview",
     "85e69eaf7f5a0931fd3c99a4b912c5afff7e3b5331e3a9fb5d1f6cdabb806d3e",
     "PET & SERVICE ANIMAL POLICY\nService Animals - ADA-defined service "
     "animals welcome. / Sorry no other animals allowed."),
]


def load_json(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, doc) -> None:
    path.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")


def build_positive_record(identity_key: str, source_url: str,
                          sha: Optional[str], builder, census_row: Dict) -> Dict:
    facts, evidence, withheld, sas_spec = builder(source_url, sha)

    evidence_quote_parts = []
    seen_q = set()
    for e in evidence:
        if e["quote"] not in seen_q:
            evidence_quote_parts.append(e["quote"])
            seen_q.add(e["quote"])
    evidence_quote = " ".join(evidence_quote_parts)
    for e in evidence:
        if not quote_is_contiguous(e["quote"], evidence_quote):
            raise AssertionError("%s: evidence quote for %s escapes evidence_quote"
                                 % (identity_key, e["field"]))

    record = OrderedDict([
        ("key", identity_key),
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
        ("worker_result_hash", sha or ""),
        ("worker_routing_version", ""),
        ("worker_validator_version", ""),
        ("schema_version", "1.2"),
        ("identity_key", identity_key),
        ("market_id", MARKET),
    ])
    if withheld:
        record["withheld_fields"] = withheld
    if sas_spec is not None:
        sas_obj, sas_quote = sas_spec
        record["service_animal_statement"] = sas_obj
        evidence.append(_evidence("service_animal_statement", sas_quote,
                                  source_url, str(sas_obj), sha))
        record["evidence_count"] = len(evidence)
        if sas_quote not in evidence_quote:
            record["evidence_quote"] = evidence_quote + " " + sas_quote
    record["computation_class"] = classify(facts).computation_class

    issues = list(policy_schema.validate_record(record)) \
        + list(evidence_contract.validate(record)) \
        + list(withholding.validate(record))
    if issues:
        raise AssertionError("%s: contract issues: %s"
                             % (identity_key, [str(i) for i in issues[:6]]))

    record["approval"] = OrderedDict([
        ("decision", enums.APPROVED_AFTER_CURRENT_REVIEW),
        ("operator", FOUNDER),
        ("approval_date", DECISION_DATE),
        ("caveats", [
            "PTF-CINCINNATI-CAPTURE-PASS1-FOUNDER-DECISIONS. Founder decision "
            "approved against THIS record_hash, applied under %s." % WORK_ORDER,
            EVIDENCE_CAVEAT,
        ]),
        ("record_hash", record_hash(record)),
        ("evidence_hash", evidence_hash(record["evidence"])),
    ])
    return record


def build_exclusion(identity_key: str, source_url: str, sha: Optional[str],
                    refusal_quote: str, census_row: Dict) -> Dict:
    record = OrderedDict([
        ("exclusion_id", "cin-%s" % census_row["slug"]),
        ("canonical_name", census_row["canonical_name"]),
        ("normalized_name", identity_key),
        ("address", census_row["address"]),
        ("city", census_row["city"]),
        ("state", census_row["state"]),
        ("postal_code", census_row["postal_code"]),
        ("phone", census_row.get("phone", "")),
        ("official_url", source_url),
        ("exclusion_state", EX.VERIFIED_NO_PETS),
        ("evidence_quote", refusal_quote),
        ("source_url", source_url),
        ("observed_at", DECISION_DATE),
        ("source_hash", ("sha256:%s" % sha) if sha else ""),
        ("reviewer_id", FOUNDER),
        ("reviewed_at", DECISION_DATE),
        ("notes", "PTF-CINCINNATI-CAPTURE-PASS1-FOUNDER-DECISIONS: affirmative, "
                 "property-specific refusal in the property's own words. "
                 + EVIDENCE_CAVEAT + " Service-animal access is a legal "
                 "category and is never read as a pet permission or as part "
                 "of the refusal itself."),
        ("market_id", MARKET),
    ])
    record["record_hash"] = EX.record_hash(record)
    record["approval_hash"] = EX.approval_hash(record)
    return record


def run(apply: bool) -> Dict:
    census_doc = load_json(CENSUS_PATH)
    census_rows = {h["identity_key"]: h for h in census_doc["hotels"]}

    facts_doc = (load_json(FACTS_PATH) if FACTS_PATH.exists() else
                {"schema_version": "1.2", "market": "Cincinnati, OH",
                 "market_id": MARKET, "hotels": []})
    exclusions_shard = load_json(MA.exclusions_shard_path(MARKET))
    seed_shard_path = MA.seed_shard_path(MARKET)

    before = OrderedDict([
        ("census", census_doc["count"]),
        ("published", len(facts_doc["hotels"])),
        ("verified_no_pets", exclusions_shard["count"]),
    ])
    if before["published"] != 0 or before["verified_no_pets"] != 0:
        raise SystemExit("STOP: Cincinnati baseline is not 0/0: %s" % before)

    have = {h["identity_key"] for h in facts_doc["hotels"]}
    published: List[Dict] = []
    for identity_key, source_url, sha, builder in POSITIVE_SPECS:
        if identity_key not in census_rows:
            raise SystemExit("STOP %s: not in the census" % identity_key)
        if identity_key in have:
            raise SystemExit("STOP %s: already published" % identity_key)
        published.append(build_positive_record(
            identity_key, source_url, sha, builder, census_rows[identity_key]))
    if len(published) != 20:
        raise SystemExit("STOP: expected 20 publications, built %d" % len(published))

    existing_norm = {e["normalized_name"] for e in exclusions_shard["exclusions"]}
    new_exclusions: List[Dict] = []
    for identity_key, source_url, sha, refusal_quote in NEGATIVE_SPECS:
        if identity_key not in census_rows:
            raise SystemExit("STOP %s: not in the census" % identity_key)
        record = build_exclusion(identity_key, source_url, sha, refusal_quote,
                                 census_rows[identity_key])
        if record["normalized_name"] in existing_norm:
            raise SystemExit("STOP %s: already excluded" % identity_key)
        new_exclusions.append(record)
    if len(new_exclusions) != 6:
        raise SystemExit("STOP: expected 6 exclusions, built %d" % len(new_exclusions))

    seed_new = []
    for record in published:
        row = census_rows[record["identity_key"]]
        seed_new.append(OrderedDict([
            ("name", record["name"]), ("category", "pet-friendly-hotels"),
            ("address", row["address"]), ("city", row["city"]),
            ("state", row["state"]), ("postal_code", row["postal_code"]),
            ("phone", row.get("phone", "")), ("website_url", record["source_url"]),
            ("source_url", record["source_url"]),
            ("source_type", "OFFICIAL_PROPERTY"), ("observed_at", DECISION_DATE),
            ("rating", ""), ("amenities", ""),
            ("pet_policy", record["evidence_quote"]), ("canonical", ""),
            (MARKET_ID_FIELD, MARKET),
        ]))

    facts_doc["hotels"] = facts_doc["hotels"] + published
    exclusions_shard["exclusions"] = exclusions_shard["exclusions"] + new_exclusions
    exclusions_shard["count"] = len(exclusions_shard["exclusions"])
    EX.validate(exclusions_shard)

    after = OrderedDict([
        ("census", census_doc["count"]),
        ("published", len(facts_doc["hotels"])),
        ("verified_no_pets", exclusions_shard["count"]),
    ])

    result = OrderedDict([
        ("before", before), ("after", after),
        ("published_added", len(published)),
        ("verified_no_pets_added", len(new_exclusions)),
    ])

    if apply:
        write_json(FACTS_PATH, facts_doc)
        write_json(MA.exclusions_shard_path(MARKET), exclusions_shard)
        header = ["name", "category", "address", "city", "state", "postal_code",
                  "phone", "website_url", "source_url", "source_type",
                  "observed_at", "rating", "amenities", "pet_policy", "canonical",
                  MARKET_ID_FIELD]
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=header)
        w.writeheader()
        for row in seed_new:
            w.writerow(row)
        with open(seed_shard_path, "a", encoding="utf-8", newline="") as f:
            f.write(buf.getvalue()[buf.getvalue().index("\n") + 1:])
        result["applied"] = True
    else:
        result["applied"] = False
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    result = run(apply=args.apply)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
