"""PTF-CLEVELAND-PASS3-FOUNDER-DECISIONS -- apply the founder's 44 rulings.

Deterministic application of the founder decisions given against the Pass-3
review packet (19e8909):

* 40 positive candidates become published Schema 1.2 records. Facts are taken
  from the same adjudication table the packet was built from
  (``cleveland_pass3_capture_integration.ROWS``) with the founder's nine
  APPROVE_WITH_CHANGE rulings applied on top, exactly:

  - D01 Emerald Necklace: Schema 1.2 has no ``per_visit`` fee basis
    (FEE_BASES is per_night/per_day/per_stay), so the $25 amount publishes
    with NO basis rather than a coerced ``per_stay``; the "per visit" quote
    is retained verbatim.
  - D03 Kimpton: Schema 1.2 has no stated-none deposit representation, so no
    $0 deposit object is invented; the explicit "No deposit or cleaning fees
    charged" joins the no-weight-limit and no-count-limit statements as
    SCHEMA_CANNOT_REPRESENT withholdings.
  - D09 ESA Copley East: CEILING != PRICE. "up to a $25" and "not to exceed
    $15" are both ceilings; the whole monetary schedule is withheld as
    SCHEMA_CANNOT_REPRESENT with both exact sentences retained.
  - D24 HGI Akron: "pet fee charged upon check in" is payment timing, not a
    guest requirement; it stays inside the evidence_quote and the approval
    caveat, never in reservation_requirement.
  - D35 La Quinta Independence: the $75/stay cap publishes as the canonical
    top-level ``fee_cap`` (qualifier_stated true, no invented scope);
    "for up to 2 pets" publishes as ``scope_pet_allowance`` on the per_room
    nightly fee -- the shape the founder attested on Wyndham Independence.
  - D36/D37 Staybridge Stow & Canton: "Pet agreement must be signed at check
    in." is a guest requirement (``reservation_requirement``); the
    vaccination sentence stays in ``general_restrictions``. Garbled upper
    tiers stay withheld SOURCE_AMBIGUOUS.
  - D38 Staybridge Mayfield Heights: agreement -> reservation_requirement;
    the twice-stated, boundary-conflicting ladder and the deposit-vs-fee
    conflict stay withheld SOURCE_CONTRADICTORY; a fee-less public record is
    the founder-accepted outcome because the withholding says the hotel's
    own terms conflict.
  - D39 Super 8 Uniontown: the contingent "$200 ... if applicable" sanitation
    fee is monetary, not a behavioral restriction; OTHER_CHARGE_KINDS has no
    sanitation kind and no contingency representation, so it is withheld as
    SOURCE_AMBIGUOUS with the exact quote -- never an unconditional charge
    and never general_restrictions. Cats publish as 'prohibited' (the
    canonical SPECIES_STATE for the founder's "cats prohibited only");
    dogs are not inferred.

* 4 refusal candidates become VERIFIED_NO_PETS exclusions, validated by the
  exclusion contract, each bound to its captured page by source_hash. The
  DoubleTree Canton Downtown exclusion cites the Hilton PROPERTY-page
  artifact (P3-004b), never the restaurant-site artifact; the routing
  correction remains a separate routing-lane observation and is not
  collapsed into this transition.

* The already-published ESA Select Suites Akron South record is remediated
  under the founder's CEILING != PRICE ruling (ESA_EXISTING_RECORD_
  REMEDIATION_AUTHORIZED): the exact-$25 tier is removed, the schedule is
  withheld SCHEMA_CANNOT_REPRESENT with the exact quotes retained, hashes
  are recomputed, and the record is re-attested with the prior approval
  preserved verbatim under ``supersedes``.

* Downstream authority follows the Pass-2 blueprint: seed inventory rows for
  the published forty, routing records retired for all 44 decided identities,
  the unresolved manifest reduced, the final partition RE-DERIVED by its own
  committed builder (never hand-edited), and the release contract re-derived.

Run:  python -m scripts.pettripfinder.cleveland_pass3_decision_application \
          [--data-root PATH] [--apply]
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import hotel_exclusions as EX                     # noqa: E402
from scripts.pettripfinder.contracts import enums                            # noqa: E402
from scripts.pettripfinder.contracts import evidence as evidence_contract    # noqa: E402
from scripts.pettripfinder.contracts import policy_schema                    # noqa: E402
from scripts.pettripfinder.contracts import withholding                      # noqa: E402
from scripts.pettripfinder.contracts.fee_computation import classify         # noqa: E402
from scripts.pettripfinder.cleveland_pass3_capture_integration import (      # noqa: E402
    ROWS, load_json, quote_backed, verify_capture, write_lf,
)
from scripts.pettripfinder.market_ownership import MARKET_ID_FIELD           # noqa: E402
from scripts.pettripfinder.policy_migration import (                         # noqa: E402
    evidence_hash, evidence_ref_for, record_hash,
)
from scripts.pettripfinder.site_data import PRODUCTION_CSV, normalize_name   # noqa: E402

MARKET = "cleveland-akron-canton-oh"
WORK_ORDER = "PTF-CLEVELAND-PASS3-FOUNDER-DECISIONS-001"
DECISION_DATE = "2026-08-16"
FOUNDER = "jfields80"
ESA_KEY = "extended stay america select suites akron south"

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
FACTS_PATH = LP / ("hotel_policy_facts_%s.json" % MARKET)
EXCLUSIONS_PATH = LP / "hotel_exclusions.json"
ROUTING_PATH = LP / "identity_routing.json"
CENSUS_PATH = LP / "identity_census" / ("%s.json" % MARKET)
PARTITION_PATH = LP / "cleveland_final_partition_002.json"
MANIFEST_PATH = LP / "cleveland_unresolved_manifest.json"
QUEUE_PATH = LP / "cleveland_pass3_queue.json"
PACKET_PATH = LP / "cleveland_pass3_founder_review_packet.json"
CONTRACT_PATH = (_REPO_ROOT / "deploy" / "netlify" / "release_contracts"
                 / ("%s.json" % MARKET))
RAW_REL = Path("worker_runs/pettripfinder/cleveland-attended-capture-003/raw")

#: Founder decisions, verbatim scope. Positives keyed by queue_id.
POSITIVE_DECISIONS: Dict[str, str] = {
    "CLE-P3-005": "APPROVE_WITH_CHANGE",   # D01
    "CLE-P3-006": "APPROVE",               # D02
    "CLE-P3-015": "APPROVE_WITH_CHANGE",   # D03
    "CLE-P3-018": "APPROVE",               # D04
    "CLE-P3-020": "APPROVE",               # D05
    "CLE-P3-023": "APPROVE",               # D06
    "CLE-P3-027": "APPROVE",               # D07
    "CLE-P3-032": "APPROVE",               # D08
    "CLE-P3-033": "APPROVE_WITH_CHANGE",   # D09
    "CLE-P3-034": "APPROVE",               # D10
    "CLE-P3-035": "APPROVE",               # D11
    "CLE-P3-036": "APPROVE",               # D12
    "CLE-P3-037": "APPROVE",               # D13
    "CLE-P3-038": "APPROVE",               # D14
    "CLE-P3-039": "APPROVE",               # D15
    "CLE-P3-040": "APPROVE",               # D16
    "CLE-P3-041": "APPROVE",               # D17
    "CLE-P3-042": "APPROVE",               # D18
    "CLE-P3-043": "APPROVE",               # D19
    "CLE-P3-044": "APPROVE",               # D20
    "CLE-P3-045": "APPROVE",               # D21
    "CLE-P3-046": "APPROVE",               # D22
    "CLE-P3-047": "APPROVE",               # D23
    "CLE-P3-048": "APPROVE_WITH_CHANGE",   # D24
    "CLE-P3-050": "APPROVE",               # D25
    "CLE-P3-051": "APPROVE",               # D26
    "CLE-P3-052": "APPROVE",               # D27
    "CLE-P3-053": "APPROVE",               # D28
    "CLE-P3-055": "APPROVE",               # D29
    "CLE-P3-056": "APPROVE",               # D30
    "CLE-P3-057": "APPROVE",               # D31
    "CLE-P3-058": "APPROVE",               # D32
    "CLE-P3-059": "APPROVE",               # D33
    "CLE-P3-060": "APPROVE",               # D34
    "CLE-P3-062": "APPROVE_WITH_CHANGE",   # D35
    "CLE-P3-063": "APPROVE_WITH_CHANGE",   # D36
    "CLE-P3-064": "APPROVE_WITH_CHANGE",   # D37
    "CLE-P3-065": "APPROVE_WITH_CHANGE",   # D38
    "CLE-P3-066": "APPROVE_WITH_CHANGE",   # D39
    "CLE-P3-067": "APPROVE",               # D40
}
DECISION_IDS: Dict[str, str] = {
    qid: "D%02d" % (i + 1) for i, qid in enumerate(POSITIVE_DECISIONS)
}
NEGATIVE_IDS = {"CLE-P3-021": "D41", "CLE-P3-025": "D42",
                "CLE-P3-029": "D43", "CLE-P3-004": "D44"}

#: Ruling text preserved into each record's approval caveats where the
#: founder said more than APPROVE.
RULING_NOTES: Dict[str, str] = {
    "CLE-P3-005": "Founder D01: do not coerce the page's 'per visit' into "
                  "per_stay; FEE_BASES has no per_visit, so the $25 amount "
                  "publishes with no basis and the exact source quote is "
                  "retained.",
    "CLE-P3-006": "Founder D02: the explicit 'No pet fees.' publishes as the "
                  "zero-amount pet_fee (contract-valid money); species, "
                  "count and weight are not inferred.",
    "CLE-P3-023": "Founder D06: refundability of the $50 deposit stays "
                  "unstated; other_charges makes the refundable flag "
                  "mandatory and never inferred, so the deposit is withheld "
                  "SCHEMA_CANNOT_REPRESENT with its exact quote instead of "
                  "publishing an invented flag. The ES-Suites-to-Simply-"
                  "Suites rebrand is census hygiene only, not an identity "
                  "failure.",
    "CLE-P3-015": "Founder D03: no $0 deposit object is invented for 'No "
                  "deposit or cleaning fees charged'; Schema 1.2 has no "
                  "stated-none deposit representation, so the statement is "
                  "withheld SCHEMA_CANNOT_REPRESENT beside the no-limit "
                  "disclosures, all with exact quotes.",
    "CLE-P3-033": "Founder D09: CEILING != PRICE. 'up to a $25 (+ tax)' and "
                  "'not to exceed $15' are both ceilings; the entire "
                  "monetary schedule is withheld SCHEMA_CANNOT_REPRESENT "
                  "with both exact sentences retained. This ruling "
                  "supersedes the older tier-1-as-exact reading.",
    "CLE-P3-043": "Founder D19: the page's own truncated 'dog/cat onl' is "
                  "quoted verbatim and recorded as a visibly truncated "
                  "property-entered rendering; canonical species is "
                  "dogs+cats because the wording is semantically "
                  "unambiguous in context.",
    "CLE-P3-045": "Founder D21: the explicit '$75/night' wording controls; "
                  "basis per_night with basis_stated true is published and "
                  "not normalized to the basis-unstated sibling pattern.",
    "CLE-P3-047": "Founder D23: the widget's $75 and the prose $81/$135 "
                  "cannot both be the price; pet_fee stays withheld "
                  "SOURCE_CONTRADICTORY -- no amount chosen, averaged, or "
                  "related.",
    "CLE-P3-048": "Founder D24: 'pet fee charged upon check in' is payment "
                  "timing, not a guest requirement; it is not forced into "
                  "reservation_requirement and remains verbatim inside the "
                  "evidence_quote.",
    "CLE-P3-050": "Founder D25: the property-specific $50/$75 ladder stands; "
                  "never replaced with the more common $75/$125 pattern.",
    "CLE-P3-056": "Founder D30: the widget's $125 label is the second tier "
                  "of the property's own $75/$125 ladder, not an "
                  "independent third price; the ladder governs and the "
                  "label quirk is provenance.",
    "CLE-P3-057": "Founder D31: same $125-label-as-tier-two resolution as "
                  "D30; provenance note preserved.",
    "CLE-P3-060": "Founder D34: 'Pet Friendly' on the exact property page "
                  "supports pets_allowed only; fee, species, count and "
                  "weight are not inferred.",
    "CLE-P3-062": "Founder D35: the $75/stay cap publishes as the canonical "
                  "top-level fee_cap (qualifier_stated true, no invented "
                  "scope), structurally separate from the $25 per_room "
                  "nightly fee whose 'for up to 2 pets' publishes as "
                  "scope_pet_allowance; the record is not forced into "
                  "fee_pet_schedule.",
    "CLE-P3-063": "Founder D36: the pet agreement is a guest requirement "
                  "(reservation_requirement); the vaccination record stays "
                  "in general_restrictions; the 'more than 7 nights' upper "
                  "tier stays SOURCE_AMBIGUOUS (night seven unpriced) and "
                  "the deposit-vs-nonrefundable-fee conflict stays "
                  "SOURCE_CONTRADICTORY.",
    "CLE-P3-064": "Founder D37: '200.00 for 7 nights' prices exactly seven "
                  "nights and is never converted to '7+'; agreement -> "
                  "reservation_requirement, vaccinations -> "
                  "general_restrictions.",
    "CLE-P3-065": "Founder D38: 'under 6 nights' vs 'up to six nights' "
                  "price a six-night stay differently, so the ladder stays "
                  "SOURCE_CONTRADICTORY beside the deposit conflict; a "
                  "fee-less public record is accepted because the "
                  "withholding states that the hotel's own terms conflict; "
                  "agreement -> reservation_requirement.",
    "CLE-P3-066": "Founder D39: cats publish as prohibited only (dogs never "
                  "inferred); the contingent '$200 ... if applicable' "
                  "sanitation fee is monetary, has no canonical kind or "
                  "contingency representation, and is withheld "
                  "SOURCE_AMBIGUOUS with the exact quote -- never an "
                  "unconditional charge, never general_restrictions.",
    "CLE-P3-067": "Founder D40: the explicit 'no maximum weight limit' is "
                  "preserved as SCHEMA_CANNOT_REPRESENT, never silence; the "
                  "explicit no-sanitation-fee statement remains recorded "
                  "evidence.",
}

#: evidence_quote regions per record, sliced verbatim from the artifact.
#: Records not listed here default to one region per distinct fact/withheld
#: quote (each quote is its own verbatim slice).
_HILTON_REGION = [("Pets allowed Yes", "All Policies")]
REGIONS: Dict[str, List[Tuple[str, str]]] = {
    "CLE-P3-005": [("We welcome your pets at our Inn.", "due to pets stay.")],
    "CLE-P3-006": [("Is the Fidelity Hotel pet-friendly?", "No pet fees.")],
    "CLE-P3-015": [("Our Pet Friendly Hotel in Cleveland welcomes your pet "
                    "with:", "No deposit or cleaning fees charged")],
    "CLE-P3-018": [("we love welcoming pets into our select pet-friendly "
                    "cabins",
                    "Pet fee is included in the rate per night on "
                    "reservations.")],
    "CLE-P3-020": [("Is Roost pet friendly?",
                    "Breed restrictions are enforced, please call for more "
                    "information.")],
    "CLE-P3-023": [("We love your furry friends as much as you do.",
                    "along with a $50 deposit.")],
    "CLE-P3-027": [("we're delighted to welcome dogs",
                    "on your next trip to Oberlin!")],
    "CLE-P3-060": [("Pet Friendly", "Pet Friendly")],
    "CLE-P3-062": [("PET & SERVICE ANIMAL POLICY",
                    "additional details and availability.")],
    "CLE-P3-066": [("PET POLICY", "welcome at this hotel.")],
    "CLE-P3-067": [("PET & SERVICE ANIMAL POLICY",
                    "additional details and availability.")],
}
for _qid in ("CLE-P3-032", "CLE-P3-034", "CLE-P3-035", "CLE-P3-036",
             "CLE-P3-037", "CLE-P3-038", "CLE-P3-039", "CLE-P3-040",
             "CLE-P3-041", "CLE-P3-042", "CLE-P3-043", "CLE-P3-044",
             "CLE-P3-045", "CLE-P3-046", "CLE-P3-047", "CLE-P3-048",
             "CLE-P3-050", "CLE-P3-051", "CLE-P3-052", "CLE-P3-053",
             "CLE-P3-055", "CLE-P3-056", "CLE-P3-057", "CLE-P3-058",
             "CLE-P3-059"):
    REGIONS[_qid] = list(_HILTON_REGION)


def _c(value: str) -> str:
    return " ".join((value or "").split())


def _clean_url(url: str) -> str:
    return (url or "").split("?", 1)[0]


# --------------------------------------------------------------------------- #
# The nine APPROVE_WITH_CHANGE rulings, applied to the adjudication specs.
# --------------------------------------------------------------------------- #

def founder_adjusted(qid: str, spec: Dict) -> Tuple[List[Dict], List[Dict]]:
    """Return (facts_list, withheld_list) with the founder's changes applied.

    Every returned withheld entry uses the canonical WITHHOLDING_REASONS
    vocabulary (the packet's shorthand 'CONTRADICTORY' becomes
    SOURCE_CONTRADICTORY).
    """
    facts = copy.deepcopy(list(spec.get("facts", [])))
    withheld = copy.deepcopy(list(spec.get("withheld", [])))
    for w in withheld:
        if w["reason_code"] == "CONTRADICTORY":
            w["reason_code"] = enums.SOURCE_CONTRADICTORY

    if qid == "CLE-P3-005":
        # D01: no per_visit basis exists; publish the amount alone.
        for f in facts:
            if f["field"] == "pet_fee":
                f["value"] = {"amount_cents": 2500, "currency": "USD"}
                f["note"] = ("the page's own basis word is 'per visit'; "
                             "Schema 1.2 has no per_visit basis, so no basis "
                             "is published (founder D01)")
    if qid == "CLE-P3-023":
        # D06: the founder kept refundability unstated; the canonical home
        # for a deposit (other_charges) makes `refundable` mandatory and
        # never inferred, so the $50 deposit cannot publish without
        # asserting a flag the page does not state. Withheld with the exact
        # quote; the $5/pet/stay fee publishes normally.
        deposit = [f for f in facts if f["field"] == "pet_deposit"]
        facts = [f for f in facts if f["field"] != "pet_deposit"]
        withheld.append({
            "field": "pet_deposit",
            "reason_code": enums.SCHEMA_CANNOT_REPRESENT,
            "reason": "The page states a $50 deposit without stating "
                      "whether it is refundable; Schema 1.2's other_charges "
                      "requires an explicit refundable flag that is never "
                      "inferred, so the deposit is withheld rather than "
                      "published with an invented flag (founder D06: "
                      "refundability stays unstated).",
            "quote": deposit[0]["quote"],
        })
    if qid == "CLE-P3-015":
        # D03: the stated-none deposit joins the no-limit withholdings.
        deposit = [f for f in facts if f["field"] == "pet_deposit"]
        facts = [f for f in facts if f["field"] != "pet_deposit"]
        withheld.append({
            "field": "pet_deposit",
            "reason_code": enums.SCHEMA_CANNOT_REPRESENT,
            "reason": "The page states that NO deposit or cleaning fees are "
                      "charged; Schema 1.2 has no stated-none deposit "
                      "representation, and a $0 deposit object would be a "
                      "fiction (founder D03).",
            "quote": deposit[0]["quote"],
        })
    if qid == "CLE-P3-033":
        # D09: ceiling != price -- the whole schedule is withheld.
        tiers = [f for f in facts if f["field"] == "fee_tiers"]
        facts = [f for f in facts if f["field"] != "fee_tiers"]
        withheld = [w for w in withheld if w["field"] != "cleaning_fee"]
        withheld.append({
            "field": "cleaning_fee",
            "reason_code": enums.SCHEMA_CANNOT_REPRESENT,
            "reason": "Both rungs of the property's schedule are ceilings "
                      "('up to a $25 (+ tax)' for nights one through six, "
                      "'not to exceed $15' thereafter). CEILING != PRICE: "
                      "Schema 1.2 tiers carry exact prices and no ceiling "
                      "qualifier, so no rung publishes as a charge; both "
                      "exact sentences are retained (founder D09).",
            "quote": tiers[0]["quote"],
            "extra_quotes": ["Each day thereafter there is a pet cleaning "
                             "fee not to exceed $15 non-refundable fee "
                             "(+tax) per day, per pet."],
        })
    if qid == "CLE-P3-048":
        # D24: payment timing is not a guest requirement.
        facts = [f for f in facts if f["field"] != "reservation_requirement"]
    if qid == "CLE-P3-062":
        # D35: canonical fee_cap + scope_pet_allowance; cap not withheld.
        for f in facts:
            if f["field"] == "pet_fee":
                f["value"] = {"amount_cents": 2500, "currency": "USD",
                              "basis": "per_night", "scope": "per_room",
                              "scope_pet_allowance": 2}
                f["note"] = ("'nightly for up to 2 pets' is the per_room "
                             "charge with scope_pet_allowance 2 -- the "
                             "shape the founder attested on Wyndham "
                             "Independence (founder D35)")
        withheld = [w for w in withheld if w["field"] != "pet_fee_cap"]
        facts.append({
            "field": "fee_cap",
            "value": {"amount_cents": 7500, "currency": "USD",
                      "basis": "per_stay", "qualifier_stated": True},
            "quote": "Max 75 USD per stay.",
            "note": "the cap's own sentence states per-stay and nothing "
                    "else; scope is not invented (founder D35)",
        })
    if qid in ("CLE-P3-063", "CLE-P3-064"):
        # D36/D37: split agreement (requirement) from vaccinations (docs).
        vac = ("Record of complete and up to date vaccinations required."
               if qid == "CLE-P3-063"
               else "Record of complete up to date vaccinations required.")
        facts = [f for f in facts if f["field"] != "general_restrictions"]
        facts.append({
            "field": "reservation_requirement",
            "value": "Pet agreement must be signed at check in.",
            "quote": "Pet agreement must be signed at check in.",
        })
        facts.append({
            "field": "general_restrictions",
            "value": vac,
            "quote": vac,
            "note": "vaccination documentation requirement; "
                    "general_restrictions is the most specific existing "
                    "canonical field (founder D36/D37)",
        })
    if qid == "CLE-P3-065":
        # D38: agreement is a requirement, never general_restrictions.
        facts = [f for f in facts if f["field"] != "general_restrictions"]
        facts.append({
            "field": "reservation_requirement",
            "value": "A pet agreement must be signed at check in",
            "quote": "A pet agreement must be signed at check in",
        })
    if qid == "CLE-P3-066":
        # D39: cats prohibited (canonical state); sanitation fee is monetary
        # and unrepresentable, withheld SOURCE_AMBIGUOUS.
        sanitation = [f for f in facts
                      if f["field"] == "general_restrictions"]
        facts = [f for f in facts if f["field"] != "general_restrictions"]
        for f in facts:
            if f["field"] == "species":
                f["value"] = {"cats": "prohibited"}
        withheld.append({
            "field": "other_charges",
            "reason_code": enums.SOURCE_AMBIGUOUS,
            "reason": "The page states a 200.00 USD pet sanitation fee 'if "
                      "applicable' without stating when it applies; "
                      "OTHER_CHARGE_KINDS has no sanitation kind and no "
                      "contingency representation, and publishing it "
                      "unconditionally would assert a charge the page does "
                      "not state (founder D39).",
            "quote": sanitation[0]["quote"],
        })
    return facts, withheld


# --------------------------------------------------------------------------- #
# Record construction (Pass-2 blueprint).
# --------------------------------------------------------------------------- #

def _slice_region(hay: str, start: str, end: str, who: str) -> str:
    hay_c, start_c, end_c = _c(hay), _c(start), _c(end)
    i = hay_c.find(start_c)
    if i < 0:
        raise AssertionError("%s: region start %r not in artifact"
                             % (who, start[:50]))
    j = hay_c.find(end_c, i)
    if j < 0:
        raise AssertionError("%s: region end %r not in artifact"
                             % (who, end[:50]))
    return hay_c[i:j + len(end_c)]


def build_evidence_quote(qid: str, doc: Dict, quotes: List[str]) -> str:
    regions = REGIONS.get(qid)
    if not regions:
        seen: List[str] = []
        for quote in quotes:
            if quote not in seen:
                seen.append(quote)
        regions = [(q, q) for q in seen]
    hay = doc.get("text", "")
    if quote_backed(regions[0][0], doc) == "html":
        hay = doc.get("html", "")
    parts = [_slice_region(hay, s, e, qid) for s, e in regions]
    return " […] ".join(parts)


def _value_display(value) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _evidence_entry(field: str, quote: str, source_url: str, value_disp: str,
                    artifact_sha: str, captured_at: str) -> Dict:
    entry = OrderedDict([
        ("field", field),
        ("quote", quote),
        ("source_url", source_url),
        ("value", value_disp),
        ("evidence_ref", ""),
        ("artifact_class", enums.PUBLICATION_GRADE_EVIDENCE),
        ("artifact_sha256", artifact_sha),
        ("artifact_kind", enums.ARTIFACT_RENDERED_HTML),
        ("captured_at", captured_at),
        ("capture_method", "attended_browser"),
        ("source_grade", enums.GRADE_PT1_FIRST_PARTY),
    ])
    entry["evidence_ref"] = evidence_ref_for(entry)
    return entry


def build_positive_record(qid: str, spec: Dict, census_row: Dict,
                          doc: Dict) -> Dict:
    integrity = verify_capture(doc)
    if not (integrity["html_agrees"] and integrity["text_agrees"]):
        raise AssertionError("%s: capture integrity failure" % qid)
    artifact_sha = "sha256:%s" % integrity["html_sha256"]
    source_url = _clean_url(doc["final_url"])

    facts_list, withheld_list = founder_adjusted(qid, spec)

    facts: "OrderedDict[str, object]" = OrderedDict()
    sas = None
    evidence: List[Dict] = []
    all_quotes: List[str] = []
    for fact in facts_list:
        if quote_backed(fact["quote"], doc) == "MISSING":
            raise AssertionError("%s: quote %r not in artifact"
                                 % (qid, fact["quote"][:60]))
        entry = _evidence_entry(fact["field"], fact["quote"], source_url,
                                _value_display(fact["value"]), artifact_sha,
                                doc["captured_at"])
        evidence.append(entry)
        all_quotes.append(fact["quote"])
        if fact["field"] == "service_animal_statement":
            sas = fact["value"]
        else:
            facts[fact["field"]] = fact["value"]

    withheld: "OrderedDict[str, Dict]" = OrderedDict()
    for w in withheld_list:
        refs = []
        for quote in [w["quote"]] + list(w.get("extra_quotes", [])):
            if quote_backed(quote, doc) == "MISSING":
                raise AssertionError("%s: withheld quote %r not in artifact"
                                     % (qid, quote[:60]))
            entry = _evidence_entry(w["field"], quote, source_url,
                                    "WITHHELD", artifact_sha,
                                    doc["captured_at"])
            evidence.append(entry)
            all_quotes.append(quote)
            refs.append(entry["evidence_ref"])
        withheld[w["field"]] = OrderedDict([
            ("reason_code", w["reason_code"]),
            ("reason", w["reason"]),
            ("evidence_refs", refs),
        ])

    evidence_quote = build_evidence_quote(qid, doc, all_quotes)
    for entry in evidence:
        if _c(entry["quote"]) not in _c(evidence_quote):
            raise AssertionError("%s: quote %r escapes evidence_quote"
                                 % (qid, entry["quote"][:60]))

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
        raise AssertionError("%s: contract issues: %s" % (qid, issues[:4]))

    caveats = [
        "Founder decision %s, %s, approved against THIS record_hash. Facts "
        "were constructed only from quotes verified contiguous in the "
        "hash-bound attended capture (%s); identity was bound on the page's "
        "own address/ZIP/phone signals recorded in "
        "cleveland_pass3_capture_results.json." % (
            DECISION_IDS[qid], WORK_ORDER, artifact_sha[:23]),
    ]
    note = RULING_NOTES.get(qid)
    if note:
        caveats.append(note)
    record["approval"] = OrderedDict([
        ("decision", enums.APPROVED_AFTER_CURRENT_REVIEW),
        ("operator", FOUNDER),
        ("approval_date", DECISION_DATE),
        ("caveats", caveats),
        ("record_hash", record_hash(record)),
        ("evidence_hash", evidence_hash(evidence)),
    ])
    return record


def build_exclusion(neg: Dict, census_row: Dict, doc: Dict) -> Dict:
    integrity = verify_capture(doc)
    if not (integrity["html_agrees"] and integrity["text_agrees"]):
        raise AssertionError("%s: capture integrity failure" % neg["queue_id"])
    if quote_backed(neg["refusal_quote"], doc) == "MISSING":
        raise AssertionError("%s: refusal quote not in artifact"
                             % neg["queue_id"])
    source_url = _clean_url(doc["final_url"])
    extra = ""
    if neg["queue_id"] == "CLE-P3-004":
        extra = (" The exclusion cites the property's own hilton.com page; "
                 "the queued restaurant-site URL (330barandgrill.com) is a "
                 "SEPARATE routing-lane observation, never part of this "
                 "transition (founder D44).")
    record = OrderedDict([
        ("exclusion_id", "cle-%s" % census_row["slug"]),
        ("canonical_name", census_row["canonical_name"]),
        ("normalized_name", normalize_name(census_row["canonical_name"])),
        ("address", census_row["address"]),
        ("city", census_row["city"]),
        ("state", census_row["state"]),
        ("postal_code", census_row["postal_code"]),
        ("official_url", source_url),
        ("exclusion_state", EX.VERIFIED_NO_PETS),
        ("evidence_quote", neg["refusal_quote"]),
        ("source_url", source_url),
        ("observed_at", DECISION_DATE),
        ("source_hash", "sha256:%s" % integrity["html_sha256"]),
        ("reviewer_id", FOUNDER),
        ("reviewed_at", DECISION_DATE),
        ("notes", "Founder decision %s, %s: affirmative refusal in the "
                  "property's own words, captured with retained bytes by "
                  "the attended browser (%s).%s Service-animal access is a "
                  "legal category and is never read as a pet permission or "
                  "as a refusal on its own." % (
                      NEGATIVE_IDS[neg["queue_id"]], WORK_ORDER,
                      neg["queue_id"], extra)),
        ("market_id", MARKET),
    ])
    record["record_hash"] = EX.record_hash(record)
    record["approval_hash"] = EX.approval_hash(record)
    return record


# --------------------------------------------------------------------------- #
# ESA Select Suites Akron South remediation (CEILING != PRICE).
# --------------------------------------------------------------------------- #

def remediate_esa(facts_doc: Dict) -> Dict:
    """Apply the founder's authorized ceiling!=price remediation in place."""
    hotel = next(h for h in facts_doc["hotels"]
                 if h["identity_key"] == ESA_KEY)
    if "fee_tiers" not in hotel["facts"]:
        raise SystemExit("STOP ESA: fee_tiers already absent; nothing to "
                         "remediate (unexpected state)")
    tier_entries = [e for e in hotel["evidence"] if e["field"] == "fee_tiers"]
    if len(tier_entries) != 1:
        raise SystemExit("STOP ESA: expected exactly one fee_tiers evidence "
                         "entry, found %d" % len(tier_entries))
    entry = tier_entries[0]

    prior_approval = copy.deepcopy(hotel["approval"])
    if record_hash(hotel) != prior_approval.get("record_hash"):
        raise SystemExit("STOP ESA: current record_hash does not match its "
                         "own approval; refusing to remediate a drifted "
                         "record")

    del hotel["facts"]["fee_tiers"]
    entry["value"] = "WITHHELD"
    entry["evidence_ref"] = evidence_ref_for(entry)
    hotel.setdefault("withheld_fields", OrderedDict())
    hotel["withheld_fields"]["fee_tiers"] = OrderedDict([
        ("reason_code", enums.SCHEMA_CANNOT_REPRESENT),
        ("reason", "The first-six-nights charge is stated only as a ceiling "
                   "('There will be up to a $25 (+ tax) per day non-"
                   "refundable cleaning fee for the first six (6) nights, "
                   "per pet.'). CEILING != PRICE: Schema 1.2 tiers carry "
                   "exact prices and no ceiling qualifier, so the rung no "
                   "longer publishes as an exact $25 charge. The exact "
                   "sentence is retained in the evidence array. Founder "
                   "remediation ruling, %s (ESA_EXISTING_RECORD_"
                   "REMEDIATION_AUTHORIZED)." % DECISION_DATE),
        ("evidence_refs", [entry["evidence_ref"]]),
    ])
    hotel["computation_class"] = classify(hotel["facts"]).computation_class

    issues = list(policy_schema.validate_record(hotel)) \
        + list(evidence_contract.validate(hotel)) \
        + list(withholding.validate(hotel))
    if issues:
        raise AssertionError("ESA remediation: contract issues: %s"
                             % issues[:4])

    hotel["approval"] = OrderedDict([
        ("decision", enums.APPROVED_AFTER_CURRENT_REVIEW),
        ("operator", FOUNDER),
        ("approval_date", DECISION_DATE),
        ("supersedes", prior_approval),
        ("caveats", [
            "Founder remediation, %s: CEILING != PRICE. The exact-$25 "
            "first-six-night tier derived from 'up to a $25 (+ tax)' no "
            "longer satisfies the evidence rule and is withheld "
            "SCHEMA_CANNOT_REPRESENT; pets_allowed, the two-pet suite "
            "limit and the 36-inch dimension constraints are unchanged; "
            "the exact source sentences are retained; the prior 2026-08-15 "
            "approval is preserved verbatim under 'supersedes'. Approved "
            "against THIS record_hash." % WORK_ORDER,
        ]),
        ("record_hash", record_hash(hotel)),
        ("evidence_hash", evidence_hash(hotel["evidence"])),
    ])
    return OrderedDict([
        ("identity_key", ESA_KEY),
        ("removed", "facts.fee_tiers (exact $25 rung)"),
        ("withheld_as", "fee_tiers / SCHEMA_CANNOT_REPRESENT"),
        ("record_hash_before", prior_approval["record_hash"]),
        ("record_hash_after", hotel["approval"]["record_hash"]),
        ("evidence_hash_after", hotel["approval"]["evidence_hash"]),
    ])


# --------------------------------------------------------------------------- #
# Application.
# --------------------------------------------------------------------------- #

def run(data_root: Path, apply: bool) -> Dict:
    raw_dir = data_root / RAW_REL
    packet = load_json(PACKET_PATH)
    queue_rows = {r["queue_id"]: r
                  for r in load_json(QUEUE_PATH)["rows"]}
    census = {r["identity_key"]: r for r in load_json(CENSUS_PATH)["hotels"]}

    facts_doc = load_json(FACTS_PATH)
    have = {h["identity_key"] for h in facts_doc["hotels"]}

    # ---- 40 positives ------------------------------------------------------ #
    published: List[Dict] = []
    for qid in POSITIVE_DECISIONS:
        spec = ROWS[qid]
        key = queue_rows[qid]["identity_key"]
        if key not in census:
            raise SystemExit("STOP %s: %r not in the census" % (qid, key))
        if key in have:
            raise SystemExit("STOP %s: %r already published" % (qid, key))
        artifact = spec.get("quote_artifact") or spec["artifact"]
        doc = load_json(raw_dir / artifact)
        record = build_positive_record(qid, spec, census[key], doc)
        published.append(record)

    # ---- ESA remediation --------------------------------------------------- #
    esa_delta = remediate_esa(facts_doc)
    facts_doc["hotels"] = facts_doc["hotels"] + published

    # ---- 4 exclusions ------------------------------------------------------ #
    exclusions_doc = load_json(EXCLUSIONS_PATH)
    existing_norm = {e["normalized_name"] for e in exclusions_doc["exclusions"]}
    new_exclusions: List[Dict] = []
    for neg in packet["negative_candidates"]:
        key = neg["identity_key"]
        if key not in census:
            raise SystemExit("STOP %s: %r not in the census"
                             % (neg["queue_id"], key))
        doc = load_json(raw_dir / neg["artifact_file"])
        record = build_exclusion(neg, census[key], doc)
        if record["normalized_name"] in existing_norm:
            raise SystemExit("STOP %s: already excluded" % neg["queue_id"])
        new_exclusions.append(record)
    exclusions_doc["exclusions"] = (exclusions_doc["exclusions"]
                                    + new_exclusions)
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

    # ---- routing retirement ------------------------------------------------ #
    routing = load_json(ROUTING_PATH)
    decided_norm = {normalize_name(r["name"]) for r in published} | \
                   {e["normalized_name"] for e in new_exclusions}
    before_routes = len(routing["routes"])
    routing["routes"] = [r for r in routing["routes"]
                         if not (r.get("market_id") == MARKET
                                 and r["hotel_ref"]["normalized_name"]
                                 in decided_norm)]
    routing["count"] = len(routing["routes"])
    routes_retired = before_routes - len(routing["routes"])

    # ---- unresolved manifest ------------------------------------------------ #
    new_state = {r["identity_key"]: "PUBLISHED_PET_FRIENDLY"
                 for r in published}
    new_state.update({e["normalized_name"]: "VERIFIED_NO_PETS"
                      for e in new_exclusions})
    manifest = load_json(MANIFEST_PATH)
    manifest_items = [i for i in manifest["items"]
                      if i["normalized_name"] not in new_state
                      and i.get("identity_key") not in new_state]
    removed = len(manifest["items"]) - len(manifest_items)
    if removed != 44:
        raise SystemExit("STOP: expected 44 manifest removals, got %d"
                         % removed)
    published_total = sum(
        1 for h in facts_doc["hotels"])
    no_pets_total = len(exclusions_doc["exclusions"])

    manifest["items"] = manifest_items

    summary = OrderedDict([
        ("published_added", len(published)),
        ("exclusions_added", len(new_exclusions)),
        ("esa_remediation", esa_delta),
        ("seed_rows_added", len(seed_new)),
        ("routes_retired", routes_retired),
        ("manifest_removed", removed),
    ])

    if apply:
        payload = write_lf(FACTS_PATH, facts_doc)
        new_sha = hashlib.sha256(payload).hexdigest()
        write_lf(EXCLUSIONS_PATH, exclusions_doc)
        write_lf(ROUTING_PATH, routing)

        with PRODUCTION_CSV.open(encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            existing_rows = list(reader)
            fields = list(reader.fieldnames)
        existing_names = {normalize_name(r["name"]) for r in existing_rows
                          if r.get(MARKET_ID_FIELD) == MARKET}
        clash = existing_names & {normalize_name(r["name"])
                                  for r in seed_new}
        if clash:
            raise SystemExit("STOP: seed rows already present: %s" % clash)
        buf = io.StringIO(newline="")
        writer = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in existing_rows + seed_new:
            writer.writerow({k: row.get(k, "") for k in fields})
        PRODUCTION_CSV.write_text(buf.getvalue(), encoding="utf-8",
                                  newline="")

        # The partition is DERIVED, never hand-edited: with the authorities
        # written, the committed builder recomputes every final state.
        # The manifest must carry the new disposition first.
        from scripts.pettripfinder.cleveland_final_partition_002 import \
            build_partition
        counts_probe = Counter()
        # Manifest counts follow the same terminal-state arithmetic the
        # Pass-2 application recorded.
        write_lf(MANIFEST_PATH, manifest)
        partition = build_partition()
        counts = Counter(i["final_state"] for i in partition["items"])
        terminal = ("PUBLISHED_PET_FRIENDLY", "VERIFIED_NO_PETS",
                    "OUT_OF_CURRENT_CATEGORY")
        resolved = sum(counts[s] for s in terminal)
        manifest["published_pet_friendly"] = counts["PUBLISHED_PET_FRIENDLY"]
        manifest["verified_no_pets"] = counts["VERIFIED_NO_PETS"]
        manifest["resolved"] = resolved
        manifest["unresolved"] = 188 - resolved
        manifest["classification_counts"] = OrderedDict(
            sorted(Counter(i["classification"]
                           for i in manifest_items).items()))
        manifest["as_of"] = DECISION_DATE
        manifest["pass3_update"] = (
            "%s removed 44 rows (40 published, 4 verified no-pets) after "
            "the Pass-3 attended capture pass; every removal is traceable "
            "in cleveland_pass3_capture_results.json." % WORK_ORDER)
        write_lf(MANIFEST_PATH, manifest)
        partition = build_partition()
        counts = Counter(i["final_state"] for i in partition["items"])
        resolved = sum(counts[s] for s in terminal)
        write_lf(PARTITION_PATH, partition)

        if counts["PUBLISHED_PET_FRIENDLY"] != len(
                [h for h in facts_doc["hotels"]]):
            raise SystemExit(
                "STOP: partition published count %d != facts records %d"
                % (counts["PUBLISHED_PET_FRIENDLY"],
                   len(facts_doc["hotels"])))

        contract = load_json(CONTRACT_PATH)
        contract["policy_package"]["expected_sha256"] = new_sha
        contract["policy_package"]["expected_record_count"] = \
            counts["PUBLISHED_PET_FRIENDLY"]
        contract["reconciliation"].update(
            {k: v for k, v in partition["reconciliation"].items()
             if k in contract["reconciliation"]})
        contract["public_surface"]["seed_hotel_rows"] = \
            counts["PUBLISHED_PET_FRIENDLY"]
        contract["public_surface"]["public_hotel_profile_count"] = \
            counts["PUBLISHED_PET_FRIENDLY"]
        contract["routes"]["hotel_route_count"] = \
            counts["PUBLISHED_PET_FRIENDLY"]
        # Corridor pages exist for corridors that HAVE published hotels;
        # forty new publications open new corridors, so the count is
        # re-derived from the same authority the release gate reads.
        from scripts.pettripfinder.build_market_manifest import build_package
        contract["routes"]["published_corridor_route_count"] = \
            len(build_package(MARKET).corridor_routes)
        import re as _re
        contract["deployment_authorization"]["means"] = _re.sub(
            r"\d+ of this market's 188",
            "%d of this market's 188" % (188 - resolved),
            contract["deployment_authorization"]["means"])
        write_lf(CONTRACT_PATH, contract)

        packet["status"] = "FOUNDER_DECIDED_AND_APPLIED"
        packet["decided_at"] = DECISION_DATE
        packet["decided_by"] = FOUNDER
        packet["decision_work_order"] = WORK_ORDER
        for cand in packet["positive_candidates"]:
            cand["founder_decision"] = POSITIVE_DECISIONS[cand["queue_id"]]
            cand["decision_id"] = DECISION_IDS[cand["queue_id"]]
            cand["outcome"] = "PUBLISHED"
        for cand in packet["negative_candidates"]:
            cand["founder_decision"] = "APPROVE_VERIFIED_NO_PETS"
            cand["decision_id"] = NEGATIVE_IDS[cand["queue_id"]]
            cand["outcome"] = "EXCLUDED_VERIFIED_NO_PETS"
        packet["esa_existing_record_remediation"] = OrderedDict(
            [("authorized", True), ("applied", True)] + list(esa_delta.items()))
        write_lf(PACKET_PATH, packet)

        report_path = LP / "cleveland_artifact_verification_001.json"
        report = load_json(report_path)
        report["facts_sha256_after_pass3_decisions"] = new_sha
        write_lf(report_path, report)

        summary["facts_sha256"] = new_sha
        summary["reconciliation"] = dict(partition["reconciliation"])
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path,
                        default=Path("C:/Atlas/atlas-dashboard/data"))
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    summary = run(args.data_root, args.apply)
    for key, value in summary.items():
        print("%s: %s" % (key, json.dumps(value, ensure_ascii=False)
                          if not isinstance(value, str) else value))
    if not args.apply:
        print("dry run: nothing written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
