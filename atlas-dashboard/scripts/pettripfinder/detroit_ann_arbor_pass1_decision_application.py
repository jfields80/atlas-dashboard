"""PTF-DETROIT-ANN-ARBOR-PASS1-DECISION-APPLICATION-001 -- apply DTW-P1-01..12.

Applies the twelve founder decisions recorded (verbatim, in chat, by the
founder on 2026-08-17) against ``detroit_ann_arbor_pass1_founder_review_packet.json``:

* 6 approved positive candidates become published Schema 1.2 records in
  ``hotel_policy_facts_detroit-ann-arbor-mi.json``. Every record binds an
  operator-screenshot artifact (this pass retained no raw HTML bytes locally;
  the full-page HTML was hashed in-browser and the hash is carried as
  provenance only) whose sha256 is asserted to match the committed capture
  packet before anything is written;
* 5 approved VERIFIED_NO_PETS decisions become exclusion-registry rows, each
  bound to its property-specific screenshot artifact;
* Delta Hotels by Marriott Detroit Metro Airport (DTW-P1-06) gets NO founder
  policy decision: its official URL 404s and it is absent from Marriott's own
  live property search. It is force-classified AWAITING_ROUTING_REPLACEMENT
  regardless of what the ordinary identity/URL-shape derivation would say,
  because the URL that derivation trusts is now proven dead;
* founder approvals are written ONLY against the final record_hash /
  evidence_hash of each fully-built record;
* census/partition/reports are rebuilt through the SAME candidate table +
  repair overrides as the prior two passes, plus this pass's own decided
  states and the one routing-problem override -- never hand-edited;
* a semantic render check projects every published record through
  canonical_view + hotel_profile and fails closed on any unexpected shape.

Run:  python -m scripts.pettripfinder.detroit_ann_arbor_pass1_decision_application [--apply]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import canonical_view                              # noqa: E402
from scripts.pettripfinder import hotel_exclusions as EX                      # noqa: E402
from scripts.pettripfinder import market_authority as MA                      # noqa: E402
from scripts.pettripfinder.contracts import enums                             # noqa: E402
from scripts.pettripfinder.contracts import evidence as evidence_contract     # noqa: E402
from scripts.pettripfinder.contracts import policy_schema                     # noqa: E402
from scripts.pettripfinder.contracts import withholding                       # noqa: E402
from scripts.pettripfinder.contracts.fee_computation import classify          # noqa: E402
from scripts.pettripfinder.contracts.identity_key import ptf_identity_key     # noqa: E402
from scripts.pettripfinder.policy_migration import (                          # noqa: E402
    evidence_hash, evidence_ref_for, record_hash,
)
from scripts.pettripfinder.site_data import normalize_name                    # noqa: E402

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-PASS1-DECISION-APPLICATION-001"
CAPTURE_WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-CAPTURE-PASS1-001"
DECISION_DATE = "2026-08-17"
FOUNDER = "jfields80"

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
FACTS_PATH = LP / ("hotel_policy_facts_%s.json" % MARKET)
# PTF-ACTIVE-BRANCH-SHARD-MIGRATION-001. This market's exclusions live in its
# OWN authority shard, never in the shared global file. The global
# launch_packages/pettripfinder/hotel_exclusions.json is a GENERATED
# compatibility artifact assembled from every market's shard, so writing it
# here would both conflict with every other market's branch and be overwritten
# by the next assembly.
EXCLUSIONS_SHARD_PATH = MA.exclusions_shard_path(MARKET)
CENSUS_PATH = LP / "identity_census" / ("%s.json" % MARKET)
PARTITION_PATH = LP / "detroit_ann_arbor_final_partition_001.json"
PACKET_PATH = LP / "detroit_ann_arbor_pass1_founder_review_packet.json"
CAPTURE_RESULTS_PATH = LP / "detroit_ann_arbor_pass1_capture_results.json"
RENDER_REPORT_PATH = LP / "markets" / "reports" / "detroit_ann_arbor_pass1_semantic_render.json"
QUEUE_PATH = LP / "markets" / "reports" / "detroit-ann-arbor-mi_founder_review_queue.json"
RAW_DIR = (_REPO_ROOT / "data" / "worker_runs" / "pettripfinder"
           / "detroit-ann-arbor-capture-pass1-001" / "raw")


def _money(dollars) -> Dict:
    cents = int(round(dollars * 100))
    return {"amount_cents": cents, "currency": "USD"}


def _tier(dollars, cmin, cmax=None, *, basis=None, scope=None, basis_stated):
    tier = OrderedDict([("amount_cents", int(round(dollars * 100))), ("currency", "USD"),
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


_DEPOSIT_LABEL_NOTE = (
    "This brand's own page renders the non-refundable fee under a 'Deposit' "
    "heading; per the schema doctrine only the body wording ('Non-refundable "
    "Fee') is true, so no deposit is recorded -- the self-contradictory "
    "label is flagged for awareness only.")

# ---------------------------------------------------------------------------
# 6 founder-approved positive decisions.
# ---------------------------------------------------------------------------
POSITIVES: "OrderedDict[str, Dict]" = OrderedDict([
    ("DTW-P1-01", dict(
        decision="APPROVE_AFFIRMATIVE_STRUCTURED", grade=enums.GRADE_PT2_BRAND,
        facts=[
            ("pets_allowed", True,
             "2 Pets are allowed with a maximum weight of 50 lbs at a non-refundable charge of 25 USD for the first night and 10 USD for each additional night. ADA defined service animals are also welcome at this hotel."),
            ("weight_limit", {"value": 50, "unit": "lb", "operator": "lte",
                              "scope": "per_pet"},
             "2 Pets are allowed with a maximum weight of 50 lbs at a non-refundable charge of 25 USD for the first night and 10 USD for each additional night. ADA defined service animals are also welcome at this hotel."),
            ("fee_tiers", [_tier(25, 1, 1, basis_stated=True),
                            _tier(10, 2, basis_stated=True)],
             "2 Pets are allowed with a maximum weight of 50 lbs at a non-refundable charge of 25 USD for the first night and 10 USD for each additional night. ADA defined service animals are also welcome at this hotel."),
            ("pet_count_limit", 2,
             "2 Pets are allowed with a maximum weight of 50 lbs at a non-refundable charge of 25 USD for the first night and 10 USD for each additional night. ADA defined service animals are also welcome at this hotel."),
            ("service_animal_statement", {"stated": True, "charges_stated": "not_addressed"},
             "ADA defined service animals are also welcome at this hotel."),
        ],
        note="Founder: fee scope (per room vs per pet) is not established by "
             "the source and is left absent, never inferred. The property's "
             "separate $100.00 USD security deposit appears under 'General "
             "Information', not inside the Pet & Service Animal Policy "
             "block, and is NOT attributed to pet policy.")),
    ("DTW-P1-07", dict(
        decision="APPROVE_AFFIRMATIVE_STRUCTURED", grade=enums.GRADE_PT2_BRAND,
        facts=[
            ("pets_allowed", True, "Pets Welcome"),
            ("pet_count_limit", 2, "Maximum Number of Pets in Room: 2"),
            ("pet_count_scope", "room", "Maximum Number of Pets in Room: 2"),
            ("weight_limit", {"value": 40.0, "unit": "lb", "operator": "lte",
                              "scope": "per_pet"}, "Maximum Pet Weight: 40.0lbs"),
            ("pet_fee", dict(_money(150), basis="per_stay", refundable=False),
             "Non-Refundable Pet Fee Per Stay: $150.00"),
            ("general_restrictions", "Pet waiver must be signed at check-in.",
             "Pet waiver must be signed at check-in."),
        ],
        note="Founder: 'Pet waiver must be signed at check-in' is a "
             "check-in-time requirement, not a pre-booking/reservation "
             "requirement -- represented as a general restriction rather "
             "than translated into reservation_requirement, since the "
             "source does not say anything must happen before arrival.")),
    ("DTW-P1-08", dict(
        decision="APPROVE_WITH_CHANGE", grade=enums.GRADE_PT2_BRAND,
        facts=[
            ("pets_allowed", True,
             "Dogs allowed only, up to 2 dogs, must register at check-in, $100 fee per pet"),
            ("species", {"dogs": "accepted", "cats": "prohibited"},
             "Dogs allowed only, up to 2 dogs, must register at check-in, $100 fee per pet"),
            ("pet_count_limit", 2, "Maximum Number of Pets in Room: 2"),
            ("pet_count_scope", "room", "Maximum Number of Pets in Room: 2"),
            ("weight_limit", {"value": 100.0, "unit": "lb", "operator": "lte",
                              "scope": "per_pet"}, "Maximum Pet Weight: 100.0lbs"),
            ("general_restrictions", "Must register pets at check-in.",
             "Dogs allowed only, up to 2 dogs, must register at check-in, $100 fee per pet"),
        ],
        withheld=[dict(
            field="pet_fee", reason_code="SOURCE_CONTRADICTORY",
            reason="The property's own page states the fee two incompatible "
                   "ways: the free-text line reads '$100 fee per pet' "
                   "(implying up to $200 for 2 dogs), while the structured "
                   "field directly below reads 'Non-Refundable Pet Fee Per "
                   "Stay: $100.00' (implying one flat $100 regardless of pet "
                   "count). Per the founder decision, neither reading is "
                   "chosen, averaged, or related, and no amount is "
                   "published under any interpretation -- the schema cannot "
                   "truthfully represent $100 without implying one of the "
                   "two disputed scopes.",
            quotes=["Dogs allowed only, up to 2 dogs, must register at check-in, $100 fee per pet",
                    "Non-Refundable Pet Fee Per Stay: $100.00"])],
        note="Founder: dogs-only and the 2-dog/100 lb limits are "
             "unambiguous and publish; the monetary amount is withheld "
             "entirely rather than guessed at either scope.")),
    ("DTW-P1-09", dict(
        decision="APPROVE_AFFIRMATIVE_STRUCTURED", grade=enums.GRADE_PT2_BRAND,
        facts=[
            ("pets_allowed", True, "Pets allowed: Yes"),
            ("species", {"dogs": "accepted", "cats": "accepted"},
             "1-4 night stay $75; 5+ night stay $125; 2 pets max; dog or cat only"),
            ("weight_limit", {"value": 75, "unit": "lb", "operator": "lte",
                              "scope": "per_pet"}, "Max weight: 75 lbs"),
            ("fee_tiers", [_tier(75, 1, 4, basis_stated=False),
                            _tier(125, 5, basis_stated=False)],
             "1-4 night stay $75; 5+ night stay $125; 2 pets max; dog or cat only"),
            ("pet_count_limit", 2,
             "1-4 night stay $75; 5+ night stay $125; 2 pets max; dog or cat only"),
        ],
        note="Founder: independently observed on this property's own "
             "first-party page, not inherited from a sibling Hilton "
             "property. " + _DEPOSIT_LABEL_NOTE)),
    ("DTW-P1-10", dict(
        decision="APPROVE_AFFIRMATIVE_STRUCTURED", grade=enums.GRADE_PT2_BRAND,
        facts=[
            ("pets_allowed", True, "Pets allowed: Yes"),
            ("species", {"dogs": "accepted", "cats": "accepted"},
             "1-4 night stay $75; 5+ night stay $125; 2 pets max; dog or cat only"),
            ("weight_limit", {"value": 75, "unit": "lb", "operator": "lte",
                              "scope": "per_pet"}, "Max weight: 75 lbs"),
            ("fee_tiers", [_tier(75, 1, 4, basis_stated=False),
                            _tier(125, 5, basis_stated=False)],
             "1-4 night stay $75; 5+ night stay $125; 2 pets max; dog or cat only"),
            ("pet_count_limit", 2,
             "1-4 night stay $75; 5+ night stay $125; 2 pets max; dog or cat only"),
        ],
        note="Founder: independently observed on this property's own "
             "first-party page, not inherited from a sibling Hilton "
             "property. " + _DEPOSIT_LABEL_NOTE)),
    ("DTW-P1-11", dict(
        decision="APPROVE_AFFIRMATIVE_STRUCTURED", grade=enums.GRADE_PT2_BRAND,
        facts=[
            ("pets_allowed", True, "Pets allowed: Yes"),
            ("species", {"dogs": "accepted", "cats": "accepted"},
             "1-4 night stay $75; 5+ night stay $125; 2 pets max; dog or cat only"),
            ("weight_limit", {"value": 75, "unit": "lb", "operator": "lte",
                              "scope": "per_pet"}, "Max weight: 75 lbs"),
            ("fee_tiers", [_tier(75, 1, 4, basis_stated=False),
                            _tier(125, 5, basis_stated=False)],
             "1-4 night stay $75; 5+ night stay $125; 2 pets max; dog or cat only"),
            ("pet_count_limit", 2,
             "1-4 night stay $75; 5+ night stay $125; 2 pets max; dog or cat only"),
        ],
        note="Founder: independently observed on this property's own "
             "first-party page, not inherited from a sibling Hilton "
             "property. " + _DEPOSIT_LABEL_NOTE)),
])

# ---------------------------------------------------------------------------
# 5 founder-approved VERIFIED_NO_PETS decisions.
# ---------------------------------------------------------------------------
NEGATIVES: "OrderedDict[str, Dict]" = OrderedDict([
    ("DTW-P1-02", dict(refusal_quote=
        "ADA defined service animals are welcome at this hotel. Sorry no other pets are allowed.")),
    ("DTW-P1-03", dict(refusal_quote=
        "ADA defined service animals are welcome at this hotel. Sorry no other pets are allowed.")),
    ("DTW-P1-04", dict(refusal_quote=
        "ADA Defined service animals are welcome at this hotel. Sorry no other pets are allowed")),
    ("DTW-P1-05", dict(refusal_quote=
        "ADA-defined service animals are welcome at this hotel. Sorry no other pets are allowed.")),
    ("DTW-P1-12", dict(refusal_quote=
        "Pets Allowed: No. General: Only service animals are permitted, free of charge.")),
])

#: The one routing hold. No policy decision; forced blocker state only.
ROUTING_HOLD_KEY = "delta hotels by marriott detroit metro airport"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=OrderedDict)


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


def _sha_file(path: Path) -> str:
    return "sha256:%s" % hashlib.sha256(path.read_bytes()).hexdigest()


def _c(value: str) -> str:
    return " ".join((value or "").split())


def _screenshot_files() -> Dict[str, str]:
    """queue_id -> screenshot filename, from the committed capture results."""
    doc = load_json(CAPTURE_RESULTS_PATH)
    return {r["queue_id"]: r["screenshot_file"] for r in doc["results"]}


def build_positive_record(did: str, spec: Dict, packet_entry: Dict,
                          census_row: Dict, screenshot_files: Dict[str, str]) -> Dict:
    screenshot_path = RAW_DIR / screenshot_files[packet_entry["queue_id"]]
    if not screenshot_path.is_file():
        raise SystemExit("STOP %s: no screenshot artifact on disk at %s"
                         % (did, screenshot_path))
    artifact_sha = _sha_file(screenshot_path)
    if artifact_sha.split(":", 1)[1] != packet_entry["artifact_sha256_screenshot"]:
        raise SystemExit("STOP %s: screenshot hash drifted from the "
                         "committed packet" % did)

    source_url = packet_entry["final_url"]
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
            ("artifact_kind", enums.ARTIFACT_OPERATOR_SCREENSHOT),
            ("captured_at", DECISION_DATE),
            ("capture_method", "attended_browser"),
            ("source_grade", spec["grade"]),
        ])
        entry["evidence_ref"] = evidence_ref_for(entry)
        return entry

    for field, value, quote in spec["facts"]:
        evidence.append(_evidence_entry(field, quote, value))
        if field == "service_animal_statement":
            sas = value
        else:
            facts[field] = value

    withheld: "OrderedDict[str, Dict]" = OrderedDict()
    for w in spec.get("withheld", []):
        refs = []
        for quote in w["quotes"]:
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
        "detroit_ann_arbor_pass1_founder_review_packet.json and "
        "approved against THIS final record_hash. Quotes were transcribed "
        "from the property's own rendered policy surface at capture time "
        "and are bound to the operator screenshot artifact (%s), whose "
        "policy surface and identity signals are visible in one frame. "
        "Identity binding: %s." % (
            did, spec["decision"], artifact_sha[:23],
            packet_entry["identity_binding"]),
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
                    census_row: Dict, screenshot_files: Dict[str, str]) -> Dict:
    screenshot_path = RAW_DIR / screenshot_files[packet_entry["queue_id"]]
    if not screenshot_path.is_file():
        raise SystemExit("STOP %s: no screenshot artifact on disk at %s"
                         % (did, screenshot_path))
    artifact_sha = _sha_file(screenshot_path)
    if artifact_sha.split(":", 1)[1] != packet_entry["artifact_sha256_screenshot"]:
        raise SystemExit("STOP %s: screenshot hash drifted from the "
                         "committed packet" % did)
    record = OrderedDict([
        ("exclusion_id", "dtw-%s" % census_row["slug"]),
        ("canonical_name", census_row["canonical_name"]),
        ("normalized_name", normalize_name(census_row["canonical_name"])),
        ("address", packet_entry["address"]),
        ("city", packet_entry["city"]),
        ("state", packet_entry["state"]),
        ("postal_code", packet_entry["postal_code"]),
        ("official_url", packet_entry["final_url"]),
        ("exclusion_state", EX.VERIFIED_NO_PETS),
        ("evidence_quote", spec["refusal_quote"]),
        ("source_url", packet_entry["final_url"]),
        ("observed_at", DECISION_DATE),
        ("source_hash", artifact_sha),
        ("reviewer_id", FOUNDER),
        ("reviewed_at", DECISION_DATE),
        ("notes", "Founder decision %s, %s: affirmative first-party refusal "
                  "in the property's own words, captured by the attended "
                  "browser as operator_screenshot with policy and identity "
                  "in frame (binding: %s). Service-animal access is a legal "
                  "category and never converts a no-pets policy into "
                  "pet-friendly."
                  % (did, WORK_ORDER, packet_entry["identity_binding"])),
        ("market_id", MARKET),
    ])
    record["record_hash"] = EX.record_hash(record)
    record["approval_hash"] = EX.approval_hash(record)
    return record


def semantic_render_check(published: List[Dict]) -> Dict:
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

    key = "towneplace suites by marriott detroit belleville"
    view = canonical_view.build(by_key[key])
    _expect(canonical_view.fee_phrase(view) == "",
            "%s: withheld fee must not render a price" % key)
    _expect("withheld" in profile_text(by_key[key]).lower(),
            "%s: fee must render as withheld/source conflict" % key)

    baymont = "baymont by wyndham detroit airport romulus"
    _expect("100" not in profile_text(by_key[baymont]),
            "%s: general $100 deposit must not render on the profile" % baymont)

    for record in published:
        if "pet_fee" not in record["facts"] \
                and "fee_tiers" not in record["facts"] \
                and record["identity_key"] != key:
            _expect("withheld" not in profile_text(record).lower(),
                    "%s: silence must stay absent, never 'withheld'"
                    % record["identity_key"])
    return OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-pass1-semantic-render/1.0"),
        ("work_order", WORK_ORDER),
        ("as_of", DECISION_DATE),
        ("record_count", len(published)),
        ("unexpected_semantic_changes", unexpected),
        ("unexpected_semantic_change_count", len(unexpected)),
        ("rows", rows),
    ])


def rebuild_census_and_partition() -> Dict:
    """Rebuild through the SAME candidate/repair table as the prior two
    passes, layering this pass's decided states + the one routing-problem
    override. Never hand-edits committed authority."""
    from scripts.pettripfinder import detroit_ann_arbor_identity_routing_repair_001 as R
    from scripts.pettripfinder.markets import assign_hotels, load_markets, market_by_id, slugify
    from scripts.pettripfinder.contracts import census as CENSUS
    from scripts.pettripfinder.contracts import partition as PART
    from scripts.pettripfinder.census_partition_builder import next_action_for

    market = market_by_id(load_markets(), MARKET)
    facts_doc = load_json(FACTS_PATH) if FACTS_PATH.is_file() else None
    # This market's shard, not the generated global. The loop below filters by
    # market_id anyway, so the shard is exactly the rows it was ever reading.
    exclusions_doc = MA.build_exclusions_shard(MARKET, MA.load_market_exclusions(MARKET))
    packet_doc = load_json(PACKET_PATH)
    pass1_address = {
        c["identity_key"]: c
        for c in packet_doc["candidates"]
    }

    decided: Dict[str, str] = {}
    if facts_doc:
        for hotel in facts_doc["hotels"]:
            if hotel.get("market_id") == MARKET and hotel.get("approval"):
                decided[hotel["identity_key"]] = enums.PUBLISHED_PET_FRIENDLY
    for entry in exclusions_doc.get("exclusions", []):
        if entry.get("market_id") == MARKET and entry.get("exclusion_state") == "VERIFIED_NO_PETS":
            decided[entry["normalized_name"]] = enums.VERIFIED_NO_PETS

    canonical = []
    for raw in R.CANDIDATES:
        if (raw.get("disposition") or "canonical") != "canonical":
            continue
        name = raw["name"]
        key = ptf_identity_key(name)
        slug = slugify(name)
        row = {
            "identity_key": key, "canonical_name": name, "display_name": name,
            "slug": slug, "market_id": MARKET,
            "address": raw.get("address") or "", "city": raw.get("city") or "",
            "state": "MI", "postal_code": (raw.get("postal") or "")[:5],
            "phone": raw.get("phone") or "",
            "identity_state": raw["ident"], "lodging_state": raw["lodging"],
            "policy_state": enums.POLICY_NOT_VERIFIED,
            "collision_state": enums.COLLISION_NONE,
            "official_url": raw.get("url") or "", "corridor": "",
            "assignment_basis": "", "assignment_value": "",
            "source": raw["source"], "source_id": slug,
            "observed_at": R.PHASE1_AS_OF,
            "provenance": "PTF-DETROIT-ANN-ARBOR-MARKET-FACTORY-001:%s" % raw["source"],
            "normalized_name": normalize_name(name), "former_name": raw.get("former") or "",
            "url_shape": raw.get("url_shape") or "none", "disposition": "canonical",
            "street_identity": "",
        }
        repair = R.REPAIRS.get(name)
        if repair:
            if repair.get("address") is not None:
                row["address"] = repair["address"]
            if repair.get("city"):
                row["city"] = repair["city"]
            if repair.get("postal") is not None:
                row["postal_code"] = (repair["postal"] or "")[:5]
            if repair.get("phone"):
                row["phone"] = repair["phone"]
            if repair.get("url") is not None:
                row["official_url"] = repair["url"]
            if repair.get("url_shape"):
                row["url_shape"] = repair["url_shape"]
            if repair.get("ident"):
                row["identity_state"] = repair["ident"]
            row["observed_at"] = R.AS_OF
            row["provenance"] = "%s:%s" % (R.WORK_ORDER, raw["source"])
        pass1 = pass1_address.get(key)
        if pass1 and pass1.get("identity_binding", {}).get("bound"):
            if pass1.get("address"):
                row["address"] = pass1["address"]
            if pass1.get("city"):
                row["city"] = pass1["city"]
            if pass1.get("postal_code"):
                row["postal_code"] = str(pass1["postal_code"])[:5]
            if pass1.get("phone"):
                row["phone"] = pass1["phone"]
            row["observed_at"] = DECISION_DATE
            row["provenance"] = "%s:attended_browser" % WORK_ORDER
        row["street_identity"] = R._street_identity(row["address"], row["postal_code"])
        canonical.append(row)

    assign_rows = [{"name": r["identity_key"], "city": r["city"],
                    "state": r["state"], "postal_code": r["postal_code"]}
                   for r in canonical]
    assignment = assign_hotels(market, assign_rows, fail_closed=True)
    for row in canonical:
        corridors = assignment.corridor_of.get(row["identity_key"]) or ()
        if not corridors:
            raise SystemExit("unassigned: %s" % row["canonical_name"])
        row["corridor"] = corridors[0]
        basis, value = assignment.basis_of[row["identity_key"]]
        row["assignment_basis"] = basis
        row["assignment_value"] = value

    collision_detail = {}
    by_street = {}
    for row in canonical:
        sid = row["street_identity"]
        if sid:
            by_street.setdefault(sid, []).append(row["canonical_name"])
    for sid, names in by_street.items():
        if len(names) > 1:
            collision_detail[sid] = names
            for row in canonical:
                if row["street_identity"] == sid:
                    row["collision_state"] = enums.COLLISION_SHARED_ADDRESS

    hotels = sorted(canonical, key=lambda r: r["identity_key"])

    def blocker_for(row: dict) -> str:
        if row["lodging_state"] == enums.NOT_LODGING:
            return enums.OUT_OF_CURRENT_CATEGORY
        state = decided.get(row["identity_key"]) or decided.get(row["normalized_name"])
        if state:
            return state
        if row["identity_key"] == ROUTING_HOLD_KEY:
            return enums.AWAITING_ROUTING_REPLACEMENT
        if row["identity_state"] in (enums.IDENTITY_PROVISIONAL, enums.IDENTITY_UNRESOLVED):
            return enums.AWAITING_IDENTITY_RESOLUTION
        if row.get("url_shape") == "brand_index":
            return enums.AWAITING_PROPERTY_LEVEL_URL
        if row.get("official_url"):
            return enums.AWAITING_POLICY_OBSERVATION
        return enums.AWAITING_OFFICIAL_URL

    census_doc = OrderedDict((
        ("schema", enums.CENSUS_SCHEMA), ("market_id", MARKET),
        ("identity_key_contract", "ptf_identity_key/1.0"),
        ("identity_contract", "ptf-identity-evidence/1.0"),
        ("work_order", WORK_ORDER), ("captured_at", DECISION_DATE),
        ("note", "PTF-DETROIT-ANN-ARBOR-PASS1-DECISION-APPLICATION-001 applied "
                 "6 published + 5 VERIFIED_NO_PETS founder decisions from the "
                 "DTW/Romulus capture pilot. Delta Hotels by Marriott Detroit "
                 "Metro Airport is force-held at AWAITING_ROUTING_REPLACEMENT: "
                 "its committed official_url is a confirmed 404 and the "
                 "property is absent from Marriott's own live search, "
                 "discovered during PTF-DETROIT-ANN-ARBOR-CAPTURE-PASS1-001. "
                 "No other identity's state was hand-edited."),
        ("source_authorities", [
            "https://visitdetroit.com/detroit-hotel-guide/",
            "https://www.annarbor.org/places-to-stay/hotels/",
            "https://www.dearbornareachamber.org/directory/",
            "https://business.auburnhillschamber.com/list/category/hotels-479",
            "https://www.vibeshowplace.com/hotels",
            "hotel_policy_facts_detroit-ann-arbor-mi.json", "hotel_exclusions.json",
        ]),
        ("count", len(hotels)), ("base_commit", "be6cbbac7a5636371180ea552e08b3d0140de7af"),
        ("collision_audit", {
            "duplicate_names_found": 0, "duplicate_names": {},
            "phone_collisions": 0, "address_collisions": len(collision_detail),
            "address_collision_detail": collision_detail, "out_of_boundary": 0,
            "cross_market_collisions": 0,
            "notes": "Hotel Indigo Detroit North - Troy and EVEN Hotel Detroit "
                     "North - Troy remain a dual-branded shared-address pair.",
            "status": "PROVISIONAL_FLAGS_OPEN" if collision_detail else "NO_OPEN_CONFLICTS",
            "open_conflict_count": len(collision_detail),
        }),
        ("identity_state_counts", {
            "IDENTITY_CONFIRMED": sum(1 for r in hotels if r["identity_state"] == enums.IDENTITY_CONFIRMED),
            "IDENTITY_PROVISIONAL": sum(1 for r in hotels if r["identity_state"] == enums.IDENTITY_PROVISIONAL),
            "IDENTITY_UNRESOLVED": sum(1 for r in hotels if r["identity_state"] == enums.IDENTITY_UNRESOLVED),
        }),
        ("source_methodology", "Unchanged from the identity/routing repair "
                                "pass; this pass only overlays founder policy "
                                "decisions and one routing-problem hold."),
        ("worker_branch", "worker/ptf-detroit-ann-arbor-capture-pass1-001"),
        ("worker_run", WORK_ORDER), ("hotels", hotels),
    ))
    issues = CENSUS.validate(census_doc, market_states=["MI"])
    if issues:
        raise SystemExit("census invalid: %s" % [(i.path, i.code, i.detail) for i in issues])

    items = []
    for row in hotels:
        state = blocker_for(row)
        terminal = state in enums.TERMINAL_STATES
        items.append(OrderedDict((
            ("identity_key", row["identity_key"]), ("canonical_name", row["canonical_name"]),
            ("slug", row["slug"]), ("city", row["city"]), ("state", row["state"]),
            ("postal_code", row["postal_code"]), ("final_state", state),
            ("resolved", terminal),
            ("next_action", "" if terminal else next_action_for(state)),
            ("next_action_source", "" if terminal else "identity_census/detroit-ann-arbor-mi.json"),
            ("determined_by", WORK_ORDER if row["identity_key"] in decided
             or row["identity_key"] == ROUTING_HOLD_KEY else R.WORK_ORDER),
            ("updated_at", DECISION_DATE if row["identity_key"] in decided
             or row["identity_key"] == ROUTING_HOLD_KEY else R.AS_OF),
            ("official_url", row["official_url"]),
            ("state_override_reason",
             ("%s: confirmed 404 during attended capture; the official_url on "
              "record is provably wrong and must be replaced before any "
              "policy work can start." % CAPTURE_WORK_ORDER)
             if row["identity_key"] == ROUTING_HOLD_KEY else ""),
        )))
    items.sort(key=lambda r: r["identity_key"])
    counts: Dict[str, int] = {}
    for item in items:
        counts[item["final_state"]] = counts.get(item["final_state"], 0) + 1
    meanings = {state: PART.STATE_MEANINGS[state] for state in sorted(counts)}
    partition_doc = OrderedDict((
        ("schema", enums.PARTITION_SCHEMA), ("work_order", WORK_ORDER),
        ("market_id", MARKET), ("as_of", DECISION_DATE),
        ("note", "6 published + 5 verified-no-pets from founder decisions "
                 "DTW-P1-01..12. Delta Hotels held at "
                 "AWAITING_ROUTING_REPLACEMENT, not published or excluded."),
        ("source_authorities", ["identity_census/detroit-ann-arbor-mi.json"]),
        ("count", len(items)), ("final_state_counts", counts),
        ("final_state_meanings", meanings), ("items", items),
    ))
    p_issues = PART.validate(partition_doc)
    if p_issues:
        raise SystemExit("partition invalid: %s" % [(i.path, i.code, i.detail) for i in p_issues])
    rec = PART.reconcile(CENSUS.identity_keys(census_doc), partition_doc, market_id=MARKET)
    rec_issues = PART.reconciliation_issues(rec)
    if rec_issues or not rec.agrees:
        raise SystemExit("reconciliation failed: %s" % (rec_issues,))

    hotels_by_key = {h["identity_key"]: h for h in hotels}
    queue_items = []
    seq = 0
    for item in items:
        if item["resolved"]:
            continue
        seq += 1
        batch = "batch-%03d" % (((seq - 1) // 10) + 1)
        row = hotels_by_key[item["identity_key"]]
        queue_items.append(OrderedDict((
            ("row_number", seq),
            ("identity_key", item["identity_key"]),
            ("hotel_id", item["identity_key"]),
            ("canonical_name", item["canonical_name"]),
            ("address", row["address"]),
            ("phone", row["phone"]),
            ("official_candidate_url", item["official_url"]),
            ("corridor", row["corridor"]),
            ("current_classification", item["final_state"]),
            ("blocking_reason", item["final_state"]),
            ("requested_evidence", "property-level official URL and a citable "
             "pet-policy artifact" if not item["official_url"] else
             "citable pet-policy artifact from the property's own page"),
            ("next_action", item["next_action"]),
            ("batch", batch),
            ("review_status", "NOT_STARTED"),
        )))
        payload = json.dumps(queue_items[-1], sort_keys=True, ensure_ascii=False)
        queue_items[-1]["row_sha256"] = hashlib.sha256(payload.encode("utf-8")).hexdigest()

    queue_doc = OrderedDict((
        ("schema", "ptf-detroit-ann-arbor-founder-review-queue/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", DECISION_DATE),
        ("note", "Regenerated by PTF-DETROIT-ANN-ARBOR-PASS1-DECISION-APPLICATION-001 "
                 "to remove the 11 rows resolved to PUBLISHED_PET_FRIENDLY/"
                 "VERIFIED_NO_PETS and re-flag Delta Hotels' routing hold."),
        ("count", len(queue_items)), ("batch_size", 10), ("items", queue_items),
    ))

    return dict(census_doc=census_doc, partition_doc=partition_doc, queue_doc=queue_doc,
                rec=rec, counts=counts, hotels_by_key=hotels_by_key)


def run(apply: bool) -> Dict:
    packet = load_json(PACKET_PATH)
    entries = {e["decision_id"]: e for e in packet["candidates"]}
    census = {r["identity_key"]: r for r in load_json(CENSUS_PATH)["hotels"]}

    if FACTS_PATH.is_file():
        raise SystemExit("STOP: %s already exists" % FACTS_PATH.name)

    screenshot_files = _screenshot_files()

    published: List[Dict] = []
    for did, spec in POSITIVES.items():
        entry = entries[did]
        key = entry["identity_key"]
        if key not in census:
            raise SystemExit("STOP %s: %r not in the census" % (did, key))
        if entry.get("founder_decision") != spec["decision"]:
            raise SystemExit("STOP %s: packet founder_decision %r != %r -- "
                             "decisions must be recorded in the packet before "
                             "authority is applied"
                             % (did, entry.get("founder_decision"), spec["decision"]))
        published.append(build_positive_record(did, spec, entry, census[key], screenshot_files))

    facts_doc = OrderedDict([
        ("market", "Detroit-Ann Arbor, Michigan"), ("schema_version", "1.2"),
        ("market_id", MARKET), ("hotels", published),
    ])

    # Only THIS market's exclusions. The cross-market duplicate check has not
    # been lost -- it moved to where it belongs: the assembler revalidates the
    # union of every shard, so an identity excluded by two markets still fails
    # closed, and it now fails in the place that can see both.
    existing_exclusions = MA.load_market_exclusions(MARKET)
    existing_norm = {e["normalized_name"] for e in existing_exclusions}
    new_exclusions: List[Dict] = []
    for did, spec in NEGATIVES.items():
        entry = entries[did]
        key = entry["identity_key"]
        if entry.get("founder_decision") != "APPROVE_VERIFIED_NO_PETS":
            raise SystemExit("STOP %s: packet founder_decision %r != "
                             "'APPROVE_VERIFIED_NO_PETS'" % (did, entry.get("founder_decision")))
        record = build_exclusion(did, spec, entry, census[key], screenshot_files)
        if record["normalized_name"] in existing_norm:
            raise SystemExit("STOP %s: already excluded" % did)
        new_exclusions.append(record)
    exclusions_doc = MA.build_exclusions_shard(
        MARKET, existing_exclusions + new_exclusions)
    EX.validate(exclusions_doc)

    delta_entry = entries["DTW-P1-06"]
    if delta_entry["identity_key"] != ROUTING_HOLD_KEY:
        raise SystemExit("STOP: DTW-P1-06 identity_key mismatch")
    if delta_entry.get("founder_decision") != "NO_FOUNDER_POLICY_DECISION":
        raise SystemExit("STOP: DTW-P1-06 packet founder_decision %r != "
                         "'NO_FOUNDER_POLICY_DECISION'" % delta_entry.get("founder_decision"))

    render_report = semantic_render_check(published)
    if render_report["unexpected_semantic_change_count"]:
        raise SystemExit("STOP: unexpected semantic changes: %s"
                         % render_report["unexpected_semantic_changes"])

    summary = OrderedDict([
        ("published_added", len(published)),
        ("exclusions_added", len(new_exclusions)),
        ("routing_hold", 1),
        ("unexpected_semantic_changes", render_report["unexpected_semantic_change_count"]),
    ])

    if apply:
        payload = write_lf(FACTS_PATH, facts_doc)
        summary["facts_sha256"] = hashlib.sha256(payload).hexdigest()
        EXCLUSIONS_SHARD_PATH.write_bytes(
            MA.render_json(exclusions_doc).encode("utf-8"))
        # Regenerate the global compatibility artifacts from ALL shards. This
        # is also the union revalidation: a collision with another market's
        # authority raises here rather than being committed.
        MA.write_generated_artifacts()
        write_lf(RENDER_REPORT_PATH, render_report)

        rebuilt = rebuild_census_and_partition()
        write_lf(CENSUS_PATH, rebuilt["census_doc"])
        write_lf(PARTITION_PATH, rebuilt["partition_doc"])
        write_lf(QUEUE_PATH, rebuilt["queue_doc"])

        counts = rebuilt["counts"]
        if counts.get("PUBLISHED_PET_FRIENDLY", 0) != len(published):
            raise SystemExit("STOP: partition shows %d published, expected %d"
                             % (counts.get("PUBLISHED_PET_FRIENDLY", 0), len(published)))
        if counts.get("VERIFIED_NO_PETS", 0) != len(new_exclusions):
            raise SystemExit("STOP: partition shows %d no-pets, expected %d"
                             % (counts.get("VERIFIED_NO_PETS", 0), len(new_exclusions)))
        delta_item = rebuilt["hotels_by_key"].get(ROUTING_HOLD_KEY)
        if delta_item is None:
            raise SystemExit("STOP: Delta Hotels missing from rebuilt census")
        partition_by_key = {i["identity_key"]: i for i in rebuilt["partition_doc"]["items"]}
        if partition_by_key[ROUTING_HOLD_KEY]["final_state"] != enums.AWAITING_ROUTING_REPLACEMENT:
            raise SystemExit("STOP: Delta Hotels must be AWAITING_ROUTING_REPLACEMENT, got %s"
                             % partition_by_key[ROUTING_HOLD_KEY]["final_state"])
        summary["partition_counts"] = OrderedDict(sorted(counts.items()))

        written = load_json(FACTS_PATH)
        for hotel in written["hotels"]:
            approval = hotel.get("approval") or {}
            if approval.get("decision") != enums.APPROVED_AFTER_CURRENT_REVIEW:
                raise SystemExit("STOP %s: not approved" % hotel["identity_key"])
            if approval.get("operator") != FOUNDER:
                raise SystemExit("STOP %s: approval operator is not the founder" % hotel["identity_key"])
            if approval.get("record_hash") != record_hash(hotel):
                raise SystemExit("STOP %s: approval does not bind the final record_hash" % hotel["identity_key"])
            if approval.get("evidence_hash") != evidence_hash(hotel["evidence"]):
                raise SystemExit("STOP %s: approval does not bind the final evidence_hash" % hotel["identity_key"])
        for entry in MA.load_market_exclusions(MARKET):
            if entry.get("market_id") != MARKET or entry.get("exclusion_state") != "VERIFIED_NO_PETS":
                continue
            if entry.get("reviewer_id") != FOUNDER:
                raise SystemExit("STOP %s: exclusion reviewer is not the founder" % entry["exclusion_id"])
            if entry.get("record_hash") != EX.record_hash(entry):
                raise SystemExit("STOP %s: exclusion record_hash drifted" % entry["exclusion_id"])
            if entry.get("approval_hash") != EX.approval_hash(entry):
                raise SystemExit("STOP %s: exclusion approval_hash drifted" % entry["exclusion_id"])

        packet["status"] = "FOUNDER_DECIDED_AND_APPLIED"
        packet["applied_at"] = DECISION_DATE
        packet["application_work_order"] = WORK_ORDER
        for entry in packet["candidates"]:
            did = entry["decision_id"]
            if did in POSITIVES:
                entry["founder_decision"] = POSITIVES[did]["decision"]
                entry["outcome"] = "PUBLISHED"
            elif did in NEGATIVES:
                entry["founder_decision"] = "APPROVE_VERIFIED_NO_PETS"
                entry["outcome"] = "EXCLUDED_VERIFIED_NO_PETS"
            elif did == "DTW-P1-06":
                entry["founder_decision"] = "NO_FOUNDER_POLICY_DECISION"
                entry["outcome"] = "ROUTING_HOLD_AWAITING_ROUTING_REPLACEMENT"
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
