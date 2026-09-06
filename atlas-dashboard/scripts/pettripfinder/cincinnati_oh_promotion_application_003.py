"""PTF-CINCINNATI-PROMOTION-AND-APPLICATION-003 -- apply the reader-validated clean rows.

Promotes the publication-grade rows PTF-CINCINNATI-PARALLEL-REVALIDATION-002 left
pending: pet-friendly records into the policy package and verified-no-pets rows
into this market's exclusion shard. The census does not move -- every row already
exists in it, and a new hotel would be an admission, which is a different order.

WHERE THE FACTS COME FROM
-------------------------
Not from the revalidation order's reading of the captured text, and not from this
module's opinion of it. Each row's operative block is handed to the repository's
own reader (``brightdata.policy_reading``) and the facts published are the ones IT
derives, including every field it refuses. A promotion order is not the place to
overrule a reader.

All 31 pet-friendly blocks return ``pets_allowed=True`` from the committed reader,
so none is held on reader grounds. That is worth stating plainly because the
comparable Louisville order held four of eleven for exactly that reason: the
outcome here is the reader agreeing, not the gate being loosened.

THE TWO FOUNDER DECISIONS THIS ORDER CARRIES
--------------------------------------------
Both were put to the operator as a single grouped question and both were answered.

  * HOLIDAY INN EXPRESS FAIRFIELD publishes with its fee WITHHELD. Founder item D1
    records that the page states three different charges for the same thing -- 50
    USD per stay on the amenity chip, "50 dollar pet fee Per pet" in the prose, and
    "Pet fee per night: 50 USD" one clause later. The reader sees only the prose
    block and derives a confident per-night fee; the document as a whole does not
    support it. The row publishes with everything unambiguous (two pets, dogs and
    cats, no weight limit) and NO price, which is D1's own first recommendation and
    matches the signed precedent of Pittsburgh's Residence Inn Monroeville and
    Louisville's Hawthorn. This is the one place this module declines a fact the
    reader offered, and it declines by WITHHOLDING rather than by substituting.

  * THE CINCINNATIAN HOTEL is HELD out of the no-pets cohort. Its only visible
    evidence is "Service animals only" beside Hilton's structured
    ``pets_allowed=false`` flag. This market already has a signed ruling that a
    bare structured flag is not a refusal (Great Wolf Lodge), and a service-animal
    sentence is a legal access category rather than a pet policy. Its hash and
    quote stay committed, so a later order closes it without re-acquiring anything.

A THIRD ROW IS HELD BY THE GUARD, NOT BY THE EVIDENCE
-----------------------------------------------------
26 exclusions are written and not 28. Beyond the founder's hold above, CINCINNATI
MARRIOTT AT RIVERCENTER is held because recording its refusal would un-publish a
hotel that is already live: ``address_key`` drops the street directional, so the
Marriott at 10 WEST RiverCenter Blvd and the Embassy Suites at 10 EAST share the
key "10|rivercenter|41011". The refusal is sound and first-party; the collision is
an artefact of a lossy key over two genuinely different hotels, which the exclusion
contract's own ``co_located_distinct`` confirms. See HELD_BY_FOUNDER for the full
reasoning and the instrument that would admit it.

WHY THE REFUSALS DO NOT GO THROUGH THE POLICY READER
----------------------------------------------------
The exclusion contract reads the quote; the policy reader reads for permissions and
has been observed deriving ``pets_allowed=True`` from sentences that refuse. A
refusal is recorded through the instrument built to carry one.

IDENTITY IS NEVER POSITIONAL
----------------------------
Every row is looked up by identity key against the committed census, and every
record carries the digest of the document its quote was read from. Nothing binds by
array order.

Read-only with respect to every other market. No network.
"""

from __future__ import annotations

import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import hotel_exclusions as HX             # noqa: E402
from scripts.pettripfinder import market_authority as MA             # noqa: E402
from scripts.pettripfinder.brightdata import policy_reading as PR    # noqa: E402
from scripts.pettripfinder.contracts import enums                    # noqa: E402
from scripts.pettripfinder.contracts.fee_computation import classify  # noqa: E402
from scripts.pettripfinder.contracts import policy_schema as PS      # noqa: E402
from scripts.pettripfinder.contracts import service_animal as SA     # noqa: E402
from scripts.pettripfinder.contracts import withholding as WH        # noqa: E402
from scripts.pettripfinder import publication_guard as PG            # noqa: E402
from scripts.pettripfinder.policy_migration import (                 # noqa: E402
    evidence_hash, evidence_ref_for, record_hash)
from scripts.pettripfinder.site_data import normalize_name           # noqa: E402

WORK_ORDER = "PTF-CINCINNATI-PROMOTION-AND-APPLICATION-003"
SOURCE_ORDER = "PTF-CINCINNATI-PARALLEL-REVALIDATION-002"
MARKET = "cincinnati-oh"
APPLIED_ON = "2026-09-05"

PACKAGE = _REPO_ROOT / "launch_packages" / "pettripfinder"
POLICY_PATH = PACKAGE / ("hotel_policy_facts_%s.json" % MARKET)
SHARD_PATH = MA.exclusions_shard_path(MARKET)
CENSUS_PATH = PACKAGE / "identity_census" / ("%s.json" % MARKET)
CLEAN_INVENTORY = (PACKAGE / "markets" / "reports"
                   / "cincinnati_oh_shadow_reconciliation_002.json")
REPORT_PATH = (PACKAGE / "markets" / "reports"
               / "cincinnati_oh_promotion_application_003.json")

#: Rows the founder held out of the promotion, with the reason. A held row is not
#: a failure and not a deletion: its evidence stays committed and a later order
#: closes it without buying anything again.
HELD_BY_FOUNDER: Dict[str, str] = {
    "the cincinnatian hotel": (
        "Its only visible evidence is 'Service animals only' beside Hilton's "
        "structured pets_allowed=false flag. This market's signed Great Wolf Lodge "
        "ruling declines a bare structured flag as a refusal, and a service-animal "
        "sentence is a legal access category rather than a pet policy. Operator "
        "decision recorded under %s." % WORK_ORDER),
    # Held by the publication guard, not by the evidence. The refusal itself is
    # sound -- marriott.com/cvgdr states "Pets Not Allowed" for this property --
    # but recording it would un-publish a hotel that is already live.
    #
    # ``address_key`` reduces both "10 West RiverCenter Blvd." and "10 East
    # RiverCenter Blvd." to "10|rivercenter|41011", dropping the directional, so
    # the Marriott's refusal reads as a refusal by the Embassy Suites ACROSS THE
    # STREET, which this market has published since its first release. The two are
    # different hotels: different directional street, different telephone, and the
    # exclusion contract's own ``co_located_distinct`` returns DISTINCT on
    # "distinct brand-scoped property codes MARRIOTT:cvgdr vs HILTON:cvgrces and
    # distinct canonical URLs".
    #
    # The instrument that would admit it is a reviewed same_campus_distinct_entity
    # resolution naming both identities, and authoring one is a NEW identity
    # ruling. This order was told not to invent an identity judgement to reach a
    # count, so the row is held with its evidence committed and carried to the
    # founder instead. Holding costs one exclusion; the alternative risked
    # withdrawing a live hotel on a lossy address key.
    "cincinnati marriott at rivercenter": (
        "Held by the publication guard. Its refusal is genuine and first-party, "
        "but address_key drops the street directional, so 10 West and 10 East "
        "RiverCenter Blvd share one key and the refusal would bar the already-"
        "published Embassy Suites by Hilton Cincinnati RiverCenter at 10 East. "
        "co_located_distinct rules the pair DISTINCT on brand-scoped property "
        "codes (MARRIOTT:cvgdr vs HILTON:cvgrces). Admitting it needs a reviewed "
        "same_campus_distinct_entity resolution, which is a new identity ruling "
        "this order may not author."),
}

#: Fields this order refuses to publish even though the reader derived them, with
#: the founder item that says why. Withholding is the only direction in which a
#: promotion may depart from the reader: it removes a claim, never adds one.
FOUNDER_WITHHELD: Dict[str, Dict[str, str]] = {
    "holiday inn express fairfield": {
        "pet_fee": enums.SOURCE_AMBIGUOUS,
        "fee_basis": enums.SOURCE_AMBIGUOUS,
    },
}
FOUNDER_WITHHELD_WHY = (
    "founder item D1: the document states three different charges for the same "
    "thing -- 50 USD per stay on the amenity chip, '50 dollar pet fee Per pet' in "
    "the prose, and 'Pet fee per night: 50 USD' one clause later. The reader sees "
    "only the prose block. Publishing any one of the three would publish a price "
    "the source does not support, so no price is published.")


def _fail(msg: str) -> None:
    raise SystemExit("%s: %s" % (WORK_ORDER, msg))


def _load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write(path: Path, doc: Dict) -> None:
    # LF-exact bytes. launch_packages/**/*.json is pinned to eol=lf, so a CRLF
    # write leaves the working tree disagreeing with the committed blob and fails
    # a byte comparison that has nothing to do with the facts.
    path.write_bytes((json.dumps(doc, indent=1) + "\n").encode("utf-8"))


def clean_inventory() -> Dict[str, List[Dict]]:
    doc = _load(CLEAN_INVENTORY)["phase_14_clean_pending_inventory"]
    return {"pet_friendly": list(doc["rows_pet_friendly"]),
            "no_pets": list(doc["rows_verified_no_pets"])}


def census() -> Dict[str, Dict]:
    return {h["identity_key"]: h for h in _load(CENSUS_PATH)["hotels"]}


def _lane_of(row: Mapping) -> str:
    lane = row.get("source_lane") or ""
    if lane.startswith("ATTENDED"):
        return "ATTENDED"
    if lane.startswith("FIRECRAWL"):
        return "FIRECRAWL"
    return "PAID_FETCH"


def _capture_method(lane: str) -> str:
    return {"ATTENDED": "attended_browser_same_origin_fetch",
            "FIRECRAWL": "firecrawl_rendered"}.get(lane, "brightdata_browser")


def _evidence_entry(field: str, quote: str, url: str, sha: str, grade: str,
                    method: str, captured_at: str) -> Dict:
    entry = {
        "field": field,
        "quote": quote,
        "source_url": url,
        "artifact_class": enums.PUBLICATION_GRADE_EVIDENCE,
        "artifact_sha256": sha,
        "artifact_kind": "rendered_html",
        "captured_at": captured_at,
        "capture_method": method,
        "source_grade": grade,
    }
    entry["evidence_ref"] = evidence_ref_for(entry)
    return entry


def build_pet_friendly(key: str, row: Mapping, name: str) -> Dict:
    """One published record, with its facts derived by the committed reader."""
    block = row["exact_quote"]
    url = row["canonical_url"]
    sha = row["document_sha256"]
    lane = _lane_of(row)
    captured_at = (row.get("captured_at") or "")[:10] or APPLIED_ON
    grade = "PT1_FIRST_PARTY"
    method = _capture_method(lane)

    reading = PR.parse(block)
    ex = PR.to_extraction(reading, location=url)
    derived = dict(ex.extraction)
    withheld_in = dict(ex.withheld or {})

    # The founder's refusals are applied BEFORE anything is built, so a field the
    # operator declined can never reach the record by another path.
    for field, reason in (FOUNDER_WITHHELD.get(key) or {}).items():
        derived.pop(field, None)
        withheld_in[field] = reason
    if key in FOUNDER_WITHHELD:
        derived.pop("fee_currency", None)
        derived.pop("fee_cap", None)

    facts: Dict[str, object] = {}
    evidence: List[Dict] = []

    def cite(field: str, quote: str) -> None:
        if quote and quote not in block:
            _fail("%s: the %s quote is not verbatim in its own block" % (key, field))
        evidence.append(_evidence_entry(field, quote, url, sha, grade, method,
                                        captured_at))

    if derived.get("pets_allowed") is not True:
        _fail("%s: the reader did not derive pets_allowed=True (withheld: %s)"
              % (key, withheld_in.get("pets_allowed")))
    facts["pets_allowed"] = True
    cite("pets_allowed", reading.pets_allowed_quote)

    if "pet_fee" in derived:
        fee: Dict[str, object] = {
            "amount_cents": derived["pet_fee"],
            "currency": derived.get("fee_currency", "USD"),
        }
        if derived.get("fee_basis"):
            fee["basis"] = derived["fee_basis"]
        charge = next((c for c in reading.charges if c.kind == "fee"), None)
        if charge is not None and charge.refundable is not None:
            fee["refundable"] = bool(charge.refundable)
        facts["pet_fee"] = fee
        cite("pet_fee", charge.quote if charge is not None else "")

    if derived.get("fee_tiers"):
        facts["fee_tiers"] = [dict(t) for t in derived["fee_tiers"]]
        # The reader derives tiers but exposes no span for them: there is no
        # ``tier`` charge and no ``fee_tiers_quote``. The three ways out are to
        # cite the flat-fee charge (which states a different number and would be
        # a MIS-citation), to withhold a fact the reader derived confidently, or
        # to cite the operative block itself. The block is verbatim, contiguous
        # and provably contains the tier sentence, so it is cited whole rather
        # than narrowed to a span this module would have to invent.
        tier_charge = next((c for c in reading.charges if c.kind == "tier"), None)
        cite("fee_tiers", tier_charge.quote if tier_charge is not None else block)

    if isinstance(derived.get("fee_cap"), Mapping):
        cap = dict(derived["fee_cap"])
        facts["fee_cap"] = {
            "amount_cents": cap.get("amount_minor"),
            "currency": cap.get("currency", "USD"),
            "basis": cap.get("basis"),
            "qualifier_stated": False,
        }
        cap_charge = next((c for c in reading.charges if c.kind == "cap"), None)
        cite("fee_cap", cap_charge.quote if cap_charge is not None else "")

    weight = derived.get("weight_limit")
    if isinstance(weight, Mapping):
        facts["weight_limit"] = {"value": weight["value"], "unit": weight["unit"],
                                 "operator": "lte", "scope": "per_pet"}
        cite("weight_limit", reading.weight_quote)

    if derived.get("pet_count_limit"):
        facts["pet_count_limit"] = derived["pet_count_limit"]
        if derived.get("pet_count_scope"):
            facts["pet_count_scope"] = derived["pet_count_scope"]
        cite("pet_count_limit", reading.pet_count_quote)

    species = derived.get("species_allowed") or []
    if species or derived.get("cats_allowed") is False:
        mapped: Dict[str, str] = {}
        for token in species:
            mapped[{"dog": "dogs", "cat": "cats", "bird": "birds"}.get(token, token)] = (
                enums.SPECIES_ACCEPTED)
        if derived.get("cats_allowed") is False:
            mapped["cats"] = enums.SPECIES_PROHIBITED
        facts["species"] = mapped
        facts["species_source_grade"] = {k: grade for k in mapped}
        cite("species", reading.dogs_only_quote or reading.pets_allowed_quote)

    allowed_refs = [e["evidence_ref"] for e in evidence if e["field"] == "pets_allowed"]

    # SOURCE_SILENT is the ABSENCE of a field, never a decision not to publish one.
    silent = sorted(f for f, r in withheld_in.items()
                    if r == enums.SOURCE_SILENT and f in PS.KNOWN_FACT_FIELDS)
    withheld_fields = {}
    for field, reason in sorted(withheld_in.items()):
        if field not in PS.KNOWN_FACT_FIELDS or reason == enums.SOURCE_SILENT:
            continue
        if key in FOUNDER_WITHHELD and field in FOUNDER_WITHHELD[key]:
            why = FOUNDER_WITHHELD_WHY
        else:
            why = "the committed reader refused this field: %s" % reason
        withheld_fields[field] = WH.withheld(
            field, reason, why, allowed_refs,
            withheld_at=APPLIED_ON, withheld_by=WORK_ORDER)
    projection_notes = [
        "%s: SOURCE_SILENT dropped from withheld_fields -- silence is the absence "
        "of a field, not a decision not to publish one" % field
        for field in silent
    ]

    quotes = [e["quote"] for e in evidence]
    record: Dict[str, object] = {
        "key": key,
        "name": name,
        "facts": facts,
        "evidence": evidence,
        "evidence_count": len(evidence),
        "evidence_quote": " [.] ".join(quotes),
        "source_url": url,
        "source_type": "EXACT_ENTITY_DOMAIN",
        "verification_state": "VERIFIED_PET_FRIENDLY",
        "verification_date": captured_at,
        "verified_at": captured_at,
        "worker_model_id": "",
        "worker_prompt_version": "",
        "worker_result_hash": sha.split(":", 1)[-1],
        "worker_routing_version": "",
        "worker_validator_version": "",
        "schema_version": "1.3",
        "identity_key": key,
        "market_id": MARKET,
        # Derived by the contract's OWN classifier over the facts actually
        # published, never picked from the enum by hand. validate_migrated
        # recomputes this field and compares, so a hand-chosen class is a defect
        # that ships silently until something re-derives it.
        "computation_class": classify(facts).computation_class,
        "acquisition_lane": lane,
        "applied_by": WORK_ORDER,
    }
    if withheld_fields:
        record["withheld_fields"] = withheld_fields
    if projection_notes:
        record["projection_notes"] = projection_notes

    sa = derived.get("service_animal_exception")
    if sa:
        reading_sa = SA.classify(sa)
        record["service_animal_statement"] = {
            "stated": True,
            "charges_stated": reading_sa.charges_stated,
            "quote": sa,
        }

    record["approval"] = {
        "decision": "APPROVED_AFTER_CURRENT_REVIEW",
        "operator": "jfields80",
        "approval_date": APPLIED_ON,
        "record_hash": record_hash(record),
        "evidence_hash": evidence_hash(evidence),
        "caveats": [
            "Authorising instrument: %s, issued %s, which named the clean inventory "
            "%s published for review and directed its application. The facts here "
            "are the committed reader's, including every field it refused."
            % (WORK_ORDER, APPLIED_ON, SOURCE_ORDER),
        ],
    }
    if key in FOUNDER_WITHHELD:
        record["approval"]["caveats"].append(
            "Operator decision on founder item D1, taken in the authorising "
            "session: %s" % FOUNDER_WITHHELD_WHY)
    return record


def build_exclusion(key: str, row: Mapping, cen: Mapping) -> Dict:
    """One VERIFIED_NO_PETS exclusion, hashed by the contract's own functions."""
    name = cen["canonical_name"]
    lane = _lane_of(row)
    record = {
        "exclusion_id": "cin-" + key.replace(" ", "-"),
        "canonical_name": name,
        "normalized_name": normalize_name(name),
        "address": cen.get("address") or "",
        "city": cen.get("city") or "",
        "state": cen.get("state") or "OH",
        "postal_code": cen.get("postal_code") or "",
        "phone": cen.get("phone") or "",
        "official_url": row["canonical_url"],
        "exclusion_state": HX.VERIFIED_NO_PETS,
        "evidence_quote": row["exact_quote"],
        "evidence_context": row["exact_quote"],
        "source_url": row["canonical_url"],
        "observed_at": (row.get("captured_at") or "")[:10] or APPLIED_ON,
        "source_hash": row["document_sha256"],
        "reviewer_id": "jfields80",
        "reviewed_at": APPLIED_ON,
        "notes": (
            "Affirmative, property-specific refusal read from the property's own "
            "page. The service-animal wording beside it is a legal access category "
            "and is never read as a pet permission. Captured at $0.00 by %s on the "
            "%s lane, with the digest taken in the same call as the quote. Recorded "
            "through the exclusion contract, which reads the quote, and never "
            "through the policy reader, which reads for permissions. Applied under "
            "%s." % (SOURCE_ORDER, lane, WORK_ORDER)),
        "market_id": MARKET,
        "decision_source": WORK_ORDER,
    }
    record["record_hash"] = HX.record_hash(record)
    record["approval_hash"] = HX.approval_hash(record)
    return record


def apply(write: bool = False) -> Dict:
    inv = clean_inventory()
    cen = census()
    package = _load(POLICY_PATH)
    shard = _load(SHARD_PATH)

    existing_policy = {h["key"] for h in package["hotels"]}
    existing_excl = {e["exclusion_id"] for e in shard["exclusions"]}
    existing_excl_names = {e["normalized_name"] for e in shard["exclusions"]}

    policy_before = json.dumps(package["hotels"], sort_keys=True)
    shard_before = json.dumps(shard["exclusions"], sort_keys=True)

    new_records: List[Dict] = []
    held: List[Dict] = []
    for row in inv["pet_friendly"]:
        key = row["identity_key"]
        if key in HELD_BY_FOUNDER:
            held.append({"identity_key": key, "cohort": "pet_friendly",
                         "why": HELD_BY_FOUNDER[key]})
            continue
        if key not in cen:
            _fail("%s: not in the committed census -- an admission is a different order" % key)
        if key in existing_policy:
            _fail("%s: already published; a promotion may not restate a live record" % key)
        new_records.append(build_pet_friendly(key, row, cen[key]["canonical_name"]))

    new_exclusions: List[Dict] = []
    for row in inv["no_pets"]:
        key = row["identity_key"]
        if key in HELD_BY_FOUNDER:
            held.append({"identity_key": key, "cohort": "verified_no_pets",
                         "why": HELD_BY_FOUNDER[key]})
            continue
        if key not in cen:
            _fail("%s: not in the committed census" % key)
        record = build_exclusion(key, row, cen[key])
        if record["exclusion_id"] in existing_excl:
            _fail("%s: exclusion id already present" % key)
        if record["normalized_name"] in existing_excl_names:
            _fail("%s: this market already excludes that name" % key)
        new_exclusions.append(record)

    overlap = {r["key"] for r in new_records} & {
        e["exclusion_id"][4:].replace("-", " ") for e in new_exclusions}
    if overlap:
        _fail("a row cannot be published and excluded at once: %s" % sorted(overlap))

    package["hotels"] = package["hotels"] + new_records
    shard["exclusions"] = shard["exclusions"] + new_exclusions
    shard["count"] = len(shard["exclusions"])

    # ``validate`` fails closed: it RAISES on the first violation and returns the
    # validated records. A non-empty return is the pass, not the failure.
    try:
        validated = HX.validate(shard)
    except HX.ExclusionContractError as exc:
        _fail("exclusion contract violation: %s" % exc)
    if len(validated) != len(shard["exclusions"]):
        _fail("the validator did not return every record")

    # A new exclusion must not bar a hotel this market already publishes. The
    # release contract would catch it two phases later; catching it here names the
    # offending pair while the applier still has both halves in hand. The guard
    # matches on a lossy street key, so this fires on real neighbours as well as on
    # real duplicates -- either way the promotion stops rather than withdrawing a
    # live hotel.
    publishable = [
        {"name": h["name"], "address": (cen.get(h["identity_key"]) or {}).get("address", ""),
         "postal_code": (cen.get(h["identity_key"]) or {}).get("postal_code", ""),
         "category": "pet-friendly-hotels"}
        for h in package["hotels"]
    ]
    try:
        PG.assert_publishable(publishable, exclusions=shard["exclusions"],
                              check_collisions=False)
    except PG.PublicationBlockedError as exc:
        _fail("a promoted exclusion would bar an already-published hotel: %s" % exc)

    report = OrderedDict()
    report["schema"] = "ptf-market-promotion-application/1.0"
    report["work_order"] = WORK_ORDER
    report["market_id"] = MARKET
    report["applied_on"] = APPLIED_ON
    report["source_order"] = SOURCE_ORDER
    report["facts_derived_by"] = (
        "scripts.pettripfinder.brightdata.policy_reading -- the committed reader, "
        "including every field it refused")
    report["pet_friendly_proposed"] = len(inv["pet_friendly"])
    report["pet_friendly_applied"] = len(new_records)
    report["no_pets_proposed"] = len(inv["no_pets"])
    report["no_pets_applied"] = len(new_exclusions)
    report["held_by_founder"] = held
    report["rows_held_by_the_reader"] = []
    report["founder_withheld_fields"] = {
        key: sorted(fields) for key, fields in FOUNDER_WITHHELD.items()}
    report["published_records_with_withheld_fields"] = {
        r["key"]: sorted(r["withheld_fields"]) for r in new_records
        if r.get("withheld_fields")}
    report["pre_existing_policy_records_changed"] = int(
        policy_before != json.dumps(package["hotels"][:len(package["hotels"])
                                                      - len(new_records)],
                                    sort_keys=True))
    report["pre_existing_exclusions_changed"] = int(
        shard_before != json.dumps(shard["exclusions"][:len(shard["exclusions"])
                                                       - len(new_exclusions)],
                                   sort_keys=True))
    report["policy_records_after"] = len(package["hotels"])
    report["exclusions_after"] = len(shard["exclusions"])
    report["exclusion_contract_violations"] = 0
    report["census_moved"] = 0

    if write:
        _write(POLICY_PATH, package)
        _write(SHARD_PATH, shard)
        _write(REPORT_PATH, report)
    return report


def main(argv: List[str]) -> int:
    report = apply(write="--write" in argv)
    print(json.dumps({k: report[k] for k in (
        "pet_friendly_proposed", "pet_friendly_applied",
        "no_pets_proposed", "no_pets_applied",
        "policy_records_after", "exclusions_after",
        "pre_existing_policy_records_changed",
        "pre_existing_exclusions_changed",
        "exclusion_contract_violations", "census_moved")}, indent=1))
    for h in report["held_by_founder"]:
        print("HELD %s (%s)" % (h["identity_key"], h["cohort"]))
    for key, fields in report["published_records_with_withheld_fields"].items():
        print("WITHHELD %s: %s" % (key, ", ".join(fields)))
    if "--write" not in argv:
        print("(dry run; pass --write to apply)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
