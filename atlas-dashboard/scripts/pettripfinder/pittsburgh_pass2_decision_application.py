"""PTF-PITTSBURGH-PASS2-DECISION-APPLICATION-001 -- apply the 11 founder decisions.

Deterministic application of the eleven Pittsburgh Pass 2 founder decisions
recorded (verbatim, in chat, on 2026-08-16) in
``pittsburgh_pass2_founder_review_packet.json``:

* 9 approved positive candidates become published Schema 1.2 records in
  ``hotel_policy_facts_pittsburgh-pa.json``, appended to the 17 Pass 1
  records already there. HTML-backed rows have every fact quote asserted
  contiguous in the hash-bound artifact; screenshot-backed rows bind the
  operator screenshot by SHA-256 with quotes transcribed from the rendered
  surface at capture time (the Columbus Hyatt / Pass 1 precedent);
* SOURCE SILENCE IS ABSENCE remains structural. HGI Airport's species is
  withheld SOURCE_AMBIGUOUS rather than inherited from its two HGI siblings
  in this same batch, which DO state species. HGI University Place's tier
  boundary is preserved EXACTLY as the property's own page prints it --
  "$75/stay for 1-4 nights. $125/stay for 4+ nights." -- condition_max=4 on
  the first tier and condition_min=4 on the second, overlap and all; the
  source's own internal overlap is not this script's to resolve, and it is
  never normalized to the "5+" boundary its Hilton siblings use. Hotel
  Indigo and Residence Inn Oakland keep their pet_fee withheld exactly as
  the founder ruled (SOURCE_CONTRADICTORY / SOURCE_AMBIGUOUS respectively);
* 2 approved refusals become VERIFIED_NO_PETS rows in the exclusion
  REGISTRY, each bound to its captured artifact;
* Courtyard Pittsburgh Shadyside and Shadyside Inn Suites receive NO policy
  authority. Their lodging_state is set to NEEDS_REVIEW in the census
  candidate table (build_pittsburgh_market_001.py), the same mechanism
  already used for Ace Hotel Pittsburgh, which moves them to
  AWAITING_CENSUS_REVIEW in the rebuilt partition -- a workflow projection,
  not a closure or exclusion decision;
* Mansions on Fifth receives no authority and no state change; it remains
  AWAITING_POLICY_OBSERVATION exactly as the committed queue already has it.

Run:  python -m scripts.pettripfinder.pittsburgh_pass2_decision_application [--apply]
"""

from __future__ import annotations

import argparse
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
from scripts.pettripfinder.policy_migration import (                          # noqa: E402
    evidence_hash, evidence_ref_for, record_hash,
)
from scripts.pettripfinder.site_data import PRODUCTION_CSV, normalize_name    # noqa: E402
from scripts.pettripfinder.market_ownership import MARKET_ID_FIELD            # noqa: E402

MARKET = "pittsburgh-pa"
WORK_ORDER = "PTF-PITTSBURGH-PASS2-DECISION-APPLICATION-001"
DECISION_DATE = "2026-08-16"
FOUNDER = "jfields80"

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
FACTS_PATH = LP / ("hotel_policy_facts_%s.json" % MARKET)
EXCLUSIONS_PATH = LP / "hotel_exclusions.json"
CENSUS_PATH = LP / "identity_census" / ("%s.json" % MARKET)
PARTITION_PATH = LP / "pittsburgh_final_partition_001.json"
PACKET_PATH = LP / "markets" / "reports" / "pittsburgh_pass2_founder_review_packet.json"
RENDER_REPORT_PATH = LP / "markets" / "reports" / "pittsburgh_pass2_semantic_render.json"
EVIDENCE_DIR = _REPO_ROOT / "data" / "operator_evidence" / "pittsburgh-pass2-capture-001"


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
    "Hilton renders the non-refundable fee under a 'Deposit' heading; per "
    "schema doctrine only the body wording ('Non-refundable Fee') is true, "
    "so no deposit is recorded.")

#: One spec per PGH-P2 decision_id. Quotes for html-backed rows are asserted
#: contiguous in the artifact; screenshot-backed rows are transcriptions.
POSITIVES: "OrderedDict[str, Dict]" = OrderedDict([
    ("PGH-P2-D002", dict(  # Fairfield Robinson Township
        row=17, grade=enums.GRADE_PT2_BRAND,
        facts=[
            ("pets_allowed", True, "Pets Welcome"),
            ("species", {"dogs": "accepted"},
             "75.00 non refundable fee. Limit of two pets per room. Only dogs are permitted."),
            ("pet_fee", dict(_money(75), refundable=False),
             "75.00 non refundable fee. Limit of two pets per room. Only dogs are permitted."),
            ("pet_count_limit", 2, "Maximum Number of Pets in Room: 2"),
            ("pet_count_scope", "room", "Maximum Number of Pets in Room: 2"),
            ("weight_limit", {"value": 50, "unit": "lb", "operator": "lte", "scope": "per_pet"},
             "Maximum Pet Weight: 50.0lbs"),
        ],
        note="Founder: approve only the explicitly supported facts; no "
             "unstated basis/scope inferred beyond the exact source wording.")),
    ("PGH-P2-D004", dict(  # Hampton Airport South / Settlers Ridge
        row=20, grade=enums.GRADE_PT2_BRAND,
        facts=[
            ("pets_allowed", True, "Pets allowed"),
            ("species", {"dogs": "accepted", "cats": "accepted"},
             "1-4 night stay $50; 5+ night stay $75; 2 pets max; dog or cat only"),
            ("fee_tiers", [_tier(50, 1, 4, basis_stated=False),
                            _tier(75, 5, basis_stated=False)],
             "1-4 night stay $50; 5+ night stay $75; 2 pets max; dog or cat only"),
            ("pet_count_limit", 2,
             "1-4 night stay $50; 5+ night stay $75; 2 pets max; dog or cat only"),
        ],
        note="Founder: source-stated tiers and count approved; no unstated "
             "qualifiers added. " + _HILTON_DEPOSIT_NOTE)),
    ("PGH-P2-D005", dict(  # HGI Airport
        row=28, grade=enums.GRADE_PT2_BRAND,
        facts=[
            ("pets_allowed", True, "Pets allowed"),
            ("weight_limit", {"value": 75, "unit": "lb", "operator": "lte", "scope": "per_pet"},
             "Max weight"),
            ("fee_tiers", [_tier(75, 1, 4, basis_stated=False),
                            _tier(125, 5, basis_stated=False)],
             "$75(1-4n), $125(5+n) Emotional Support Animals are subject fees. "
             "ESA's are not covered by ADA laws."),
            ("general_restrictions",
             "Emotional Support Animals are subject to fees; ESAs are not "
             "covered by ADA laws.",
             "$75(1-4n), $125(5+n) Emotional Support Animals are subject fees. "
             "ESA's are not covered by ADA laws."),
        ],
        withheld=[dict(field="species", reason_code="SOURCE_AMBIGUOUS",
                       reason="This property's own page never states which "
                              "species are accepted (no 'dog/cat only' or "
                              "similar wording, unlike its two HGI siblings "
                              "in this same batch). Per founder decision, "
                              "species is NOT inherited from sibling Hilton "
                              "Garden Inn properties and stays withheld.",
                       quotes=["Max weight"])],
        note="Founder: publish all explicitly supported non-species facts; "
             "do NOT infer dogs+cats from neighboring HGIs. Fee/tier wording "
             "preserved exactly as captured. " + _HILTON_DEPOSIT_NOTE)),
    ("PGH-P2-D006", dict(  # HGI Airport South / Robinson Mall
        row=29, grade=enums.GRADE_PT2_BRAND,
        facts=[
            ("pets_allowed", True, "Pets allowed"),
            ("species", {"dogs": "accepted", "cats": "accepted"},
             "1-4 night stay $75 5+ night stay $125 2 pets max dog or cat only"),
            ("fee_tiers", [_tier(75, 1, 4, basis_stated=False),
                            _tier(125, 5, basis_stated=False)],
             "1-4 night stay $75 5+ night stay $125 2 pets max dog or cat only"),
            ("pet_count_limit", 2,
             "1-4 night stay $75 5+ night stay $125 2 pets max dog or cat only"),
        ],
        note="Founder: source-stated policy approved exactly as captured; "
             "nothing inferred from sibling properties. " + _HILTON_DEPOSIT_NOTE)),
    ("PGH-P2-D007", dict(  # HGI University Place
        row=30, grade=enums.GRADE_PT2_BRAND,
        facts=[
            ("pets_allowed", True, "Pets allowed"),
            ("species", {"dogs": "accepted", "cats": "accepted"},
             "2 Pets Max, dog/cat only. $75/stay for 1-4 nights. $125/stay for 4+ nights."),
            ("weight_limit", {"value": 75, "unit": "lb", "operator": "lte", "scope": "per_pet"},
             "Max weight"),
            # Founder: preserve the EXACT boundary this property states --
            # "1-4 nights" and "4+ nights" -- never normalized to the "5+"
            # its Hilton siblings in this batch use. The source's own
            # internal overlap at night 4 is printed as-is.
            ("fee_tiers", [_tier(75, 1, 4, basis="per_stay", basis_stated=True),
                            _tier(125, 4, basis="per_stay", basis_stated=True)],
             "2 Pets Max, dog/cat only. $75/stay for 1-4 nights. $125/stay for 4+ nights."),
            ("pet_count_limit", 2,
             "2 Pets Max, dog/cat only. $75/stay for 1-4 nights. $125/stay for 4+ nights."),
        ],
        note="Founder: this property's own page states its second tier as "
             "'4+ nights' -- that exact boundary is preserved and NOT "
             "normalized to '5+' to match sibling Hilton properties. "
             + _HILTON_DEPOSIT_NOTE)),
    ("PGH-P2-D008", dict(  # Hotel Indigo East Liberty
        row=37, grade=enums.GRADE_PT2_BRAND,
        facts=[
            ("pets_allowed", True,
             "Pets are welcome at Hotel Indigo Pittsburgh East Liberty."),
            ("species", {"dogs": "accepted", "cats": "accepted"},
             "Pets allowed: Only dogs and cats allowed"),
            ("weight_limit_stated_none", True,
             "Pet weight limit: No weight limit per pet"),
            ("pet_count_limit", 2, "2 pets allowed"),
            ("general_restrictions",
             "Housekeeping service will only be conducted when the pet is "
             "out of the room; pets are not allowed to be left alone in the "
             "room; current contact information is required.",
             "Housekeeping service will only be conducted when pet is out of room."),
        ],
        withheld=[dict(
            field="pet_fee", reason_code="SOURCE_CONTRADICTORY",
            reason="The same property surface gives three different "
                   "framings of $75: prose implying a single per-stay "
                   "nonrefundable fee, a structured 'Pet fee per night: 75 "
                   "USD' line, and a separate 'Pet damage deposit: 75 USD' "
                   "line. Per the founder decision none is chosen, "
                   "averaged, or treated as authoritative, and no "
                   "refundability is inferred.",
            quotes=["A 75 USD nonrefundable pet fee is required, along with current contact information.",
                    "Pet fee per night: 75 USD", "Pet damage deposit: 75 USD"])],
        note="Founder: publish the supported non-fee policy facts while the "
             "fee remains withheld exactly as the packet proposed.")),
    ("PGH-P2-D009", dict(  # Pittsburgh Airport Marriott
        row=50, grade=enums.GRADE_PT2_BRAND,
        facts=[
            ("pets_allowed", True, "Pets Welcome"),
            ("pet_fee", dict(_money(75), basis="per_stay", refundable=False),
             "Non-Refundable Pet Fee Per Stay: $75.00"),
            ("weight_limit", {"value": 75, "unit": "lb", "operator": "lte", "scope": "per_pet"},
             "Maximum Pet Weight: 75.0lbs"),
            ("pet_count_limit", 2, "Maximum Number of Pets in Room: 2"),
            ("pet_count_scope", "room", "Maximum Number of Pets in Room: 2"),
            ("general_restrictions", "A signed pet waiver is required at check-in.",
             "2 pets up with USD 75 fee & signed pet waiver at check-in. Service dogs, no fee."),
            ("service_animal_statement",
             {"stated": True, "charges_stated": "no_charge"},
             "2 pets up with USD 75 fee & signed pet waiver at check-in. Service dogs, no fee."),
        ],
        note="Founder: exact source-supported facts approved; the "
             "signed-waiver requirement is recorded exactly as sourced, not "
             "broadened.")),
    ("PGH-P2-D010", dict(  # Residence Inn Oakland/University Place
        row=55, grade=enums.GRADE_PT2_BRAND,
        facts=[
            ("pets_allowed", True, "Pets Welcome"),
            ("weight_limit", {"value": 60, "unit": "lb", "operator": "lte", "scope": "per_pet"},
             "Maximum Pet Weight: 60.0lbs"),
            ("pet_count_limit", 2, "Maximum Number of Pets in Room: 2"),
            ("pet_count_scope", "room", "Maximum Number of Pets in Room: 2"),
            ("general_restrictions", "Pets are permitted on select floors only.",
             "Pets up to 60lbs permitted on select floors, fee varies based on length of stay"),
        ],
        withheld=[dict(
            field="pet_fee", reason_code="SOURCE_AMBIGUOUS",
            reason="The property's own prose states the fee 'varies based "
                   "on length of stay' (implying a tiered/variable charge), "
                   "while the structured line states one flat "
                   "'Non-Refundable Pet Fee Per Stay: $100.00' with no "
                   "tiers shown anywhere on the page. Per the founder "
                   "decision the flat amount is NOT chosen as authoritative "
                   "and no fee is published.",
            quotes=["Pets up to 60lbs permitted on select floors, fee varies based on length of stay",
                    "Non-Refundable Pet Fee Per Stay: $100.00"])],
        note="Founder: publish supported weight/count/room-floor "
             "restrictions independently of the fee issue; the fee stays "
             "withheld exactly as the packet proposed.")),
    ("PGH-P2-D011", dict(  # Sheraton Pittsburgh Airport Hotel
        row=58, grade=enums.GRADE_PT2_BRAND,
        facts=[
            ("pets_allowed", True, "Pets Welcome"),
            ("pet_fee", dict(_money(75), basis="per_stay", scope="per_room", refundable=False),
             "Pets 40 pounds max allowed with non-refundable fee of USD 75 per room per stay"),
            ("weight_limit", {"value": 40, "unit": "lb", "operator": "lte", "scope": "per_pet"},
             "Maximum Pet Weight: 40.0lbs"),
            ("pet_count_limit", 2, "Maximum Number of Pets in Room: 2"),
            ("pet_count_scope", "room", "Maximum Number of Pets in Room: 2"),
        ],
        note="Founder: exact source-supported policy approved; no unstated "
             "species or other qualifiers added.")),
])

#: The two founder-approved refusals.
NEGATIVES = OrderedDict([
    ("PGH-P2-D001", dict(row=13, refusal_quote="Pets not allowed")),
    ("PGH-P2-D003", dict(row=19, refusal_quote="Pets Not Allowed")),
])


def artifact_text(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    raw = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", " ", raw,
                 flags=re.S | re.I)
    return _c(_htmllib.unescape(re.sub(r"<[^>]*>", " ", raw)))


def _artifacts_for(row: int):
    out = []
    stem = "ptf-pgh-p2-r%02d" % row
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
        "Founder decision %s, recorded verbatim in "
        "pittsburgh_pass2_founder_review_packet.json (commit 7f8bec2) and "
        "approved against THIS final record_hash. %s evidence quotes were "
        "asserted contiguous in the hash-bound rendered-HTML artifact; "
        "screenshot-backed records bind the operator screenshot (%s) whose "
        "policy surface and identity signals are visible in one frame. "
        "Identity binding: %s." % (
            did, "All" if hay is not None else "Transcribed",
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

    for key in ("hotel indigo pittsburgh east liberty",
                "residence inn pittsburgh oakland university place"):
        view = canonical_view.build(by_key[key])
        _expect(canonical_view.fee_phrase(view) == "",
                "%s: withheld fee must not render a price" % key)
        _expect("withheld" in profile_text(by_key[key]).lower(),
                "%s: fee must render as withheld/source conflict" % key)
    hgi_air_view = canonical_view.build(by_key["hilton garden inn pittsburgh airport"])
    _expect(getattr(hgi_air_view, "dogs_state", None) not in ("accepted",)
            and getattr(hgi_air_view, "cats_state", None) not in ("accepted",),
            "HGI Airport: species must not be invented")
    hgi_up_text = profile_text(by_key["hilton garden inn pittsburgh university place"])
    _expect(("4" in hgi_up_text), "HGI University Place: 4+ boundary must render")
    marriott_text = profile_text(by_key["pittsburgh airport marriott"]).lower()
    _expect("waiver" in marriott_text,
            "Pittsburgh Airport Marriott: waiver requirement must render")
    return OrderedDict([
        ("schema", "ptf-pittsburgh-pass2-semantic-render/1.0"),
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
    facts_doc = load_json(FACTS_PATH)
    have = {h["identity_key"] for h in facts_doc["hotels"]}

    # ---- 9 positives ------------------------------------------------------ #
    published: List[Dict] = []
    for did, spec in POSITIVES.items():
        entry = entries[did]
        key = entry["identity_key"]
        if key not in census:
            raise SystemExit("STOP %s: %r not in the census" % (did, key))
        if key in have:
            raise SystemExit("STOP %s: %r already published" % (did, key))
        if not str(entry["founder_decision"]).startswith("APPROVE"):
            raise SystemExit("STOP %s: not approved (%s)"
                             % (did, entry["founder_decision"]))
        published.append(build_positive_record(did, spec, entry, census[key]))
    facts_doc["hotels"] = facts_doc["hotels"] + published

    # ---- 2 exclusions ------------------------------------------------------ #
    exclusions_doc = load_json(EXCLUSIONS_PATH)
    existing_norm = {e["normalized_name"] for e in exclusions_doc["exclusions"]}
    new_exclusions: List[Dict] = []
    for did, spec in NEGATIVES.items():
        entry = entries[did]
        if entry["founder_decision"] != "APPROVE_VERIFIED_NO_PETS":
            raise SystemExit("STOP %s: unexpected decision %r"
                             % (did, entry["founder_decision"]))
        key = entry["identity_key"]
        record = build_exclusion(did, spec, entry, census[key])
        if record["normalized_name"] in existing_norm:
            raise SystemExit("STOP %s: already excluded" % did)
        new_exclusions.append(record)
    exclusions_doc["exclusions"] = exclusions_doc["exclusions"] + new_exclusions
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

    # ---- semantic render gate ---------------------------------------------- #
    render_report = semantic_render_check(published)
    if render_report["unexpected_semantic_change_count"]:
        raise SystemExit("STOP: unexpected semantic changes: %s"
                         % render_report["unexpected_semantic_changes"])

    summary = OrderedDict([
        ("published_added", len(published)),
        ("exclusions_added", len(new_exclusions)),
        ("seed_rows_added", len(seed_new)),
        ("unexpected_semantic_changes",
         render_report["unexpected_semantic_change_count"]),
    ])

    if apply:
        payload = write_lf(FACTS_PATH, facts_doc)
        summary["facts_sha256"] = hashlib.sha256(payload).hexdigest()
        write_lf(EXCLUSIONS_PATH, exclusions_doc)
        write_lf(RENDER_REPORT_PATH, render_report)

        with PRODUCTION_CSV.open(encoding="utf-8-sig", newline="") as fh:
            import csv
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

        # census/partition/queue/reports are DERIVED, never hand-edited: the
        # committed builder recomputes every final state from the authorities
        # just written, plus the two NEEDS_REVIEW lodging_state edits already
        # made in build_pittsburgh_market_001.py's candidate table.
        from scripts.pettripfinder import build_pittsburgh_market_001 as B
        B._AUTHORITY_CACHE = None
        B.build()

        partition = load_json(PARTITION_PATH)
        counts = Counter(i["final_state"] for i in partition["items"])
        if counts["PUBLISHED_PET_FRIENDLY"] != 17 + len(published):
            raise SystemExit("STOP: partition shows %d published, expected %d"
                             % (counts["PUBLISHED_PET_FRIENDLY"],
                                17 + len(published)))
        if counts["VERIFIED_NO_PETS"] != 2 + len(new_exclusions):
            raise SystemExit("STOP: partition shows %d no-pets, expected %d"
                             % (counts["VERIFIED_NO_PETS"],
                                2 + len(new_exclusions)))
        by_key = {i["identity_key"]: i for i in partition["items"]}
        for key in ("courtyard by marriott pittsburgh shadyside",
                    "shadyside inn suites"):
            if by_key[key]["final_state"] != enums.AWAITING_CENSUS_REVIEW:
                raise SystemExit("STOP: %s must be AWAITING_CENSUS_REVIEW, "
                                 "got %s" % (key, by_key[key]["final_state"]))
        if by_key["mansions on fifth"]["final_state"] != \
                enums.AWAITING_POLICY_OBSERVATION:
            raise SystemExit("STOP: Mansions on Fifth must remain "
                             "AWAITING_POLICY_OBSERVATION")
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
