"""PTF-LOUISVILLE-PROMOTION-AND-APPLICATION-002 -- apply the reader-validated clean rows.

Promotes the publication-grade rows PTF-LOUISVILLE-PARALLEL-REVALIDATION-001 left pending,
into the policy package and this market's exclusion shard. Nothing else moves.

WHERE THE FACTS COME FROM
-------------------------
Not from the revalidation order's hand-parse of the captured text, and not from this
module's opinion of it. Each row's policy block is handed to the repository's own reader
(``brightdata.policy_reading``) and the facts published are the ones IT derives, including
every field it refuses to derive. A promotion order is not the place to overrule a reader.

WHY 7 PET-FRIENDLY ROWS AND NOT 11
----------------------------------
The revalidation order left 11 CLEAN_PET_FRIENDLY rows. Handing each one's block to the
committed reader, four of them come back with ``pets_allowed`` WITHHELD, and a record
whose central claim no reader will derive cannot be published as VERIFIED_PET_FRIENDLY on
this module's say-so. They are held, with the reason recorded per row in HELD_BY_READER,
and the evidence stays committed so a later reader order can close them without
re-acquiring anything. Three are reader GAPS and one is the reader being right:

  * 21c Museum Hotel -- "Pets are always welcome at 21c." The acceptance patterns allow
    filler words BEFORE "is/are" but not between "are" and "welcome", so an adverb defeats
    them. A gap.
  * Drury Inn & Suites Louisville and Louisville North -- "Dogs and cats accepted." The
    species-acceptance path fires on "dogs ... are allowed/welcome/permitted" and has no
    branch for "accepted". A gap, and a visible one: the reader derives
    species_allowed=[cat, dog] on the same sentence while withholding the allowance.
  * Super 8 Louisville Airport -- "Maximum of 2 pets ... at a nonrefundable charge of
    25USD per pet per night." There is no acceptance verb at all; the permission is implied
    only by the price. The reader refuses to read an allowance out of a price, and it is
    RIGHT to. This row needs a different sentence, not a wider pattern.

THE BLOCKS ARE CONTIGUOUS AND VERBATIM
--------------------------------------
Each block below is a contiguous substring of the artifact its digest covers. Where the
brand's markup concatenates a heading onto the first sentence ("Pet & Service Animal
PolicyDogs only please."), the block starts AFTER the heading rather than rewriting the
text, so the reader sees the property's own words and nothing is normalised into it.

IDENTITY IS NEVER POSITIONAL
----------------------------
Every row is looked up by identity key, and every block carries the digest of the document
it was read from. Nothing binds by array order.

Read-only with respect to every other market. No network.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Dict, List, Mapping

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import hotel_exclusions as HX             # noqa: E402
from scripts.pettripfinder import market_authority as MA             # noqa: E402
from scripts.pettripfinder.brightdata import policy_reading as PR    # noqa: E402
from scripts.pettripfinder.contracts import enums                    # noqa: E402
from scripts.pettripfinder.contracts import evidence as EV           # noqa: E402
from scripts.pettripfinder.contracts import policy_schema as PS      # noqa: E402
from scripts.pettripfinder.contracts import service_animal as SA      # noqa: E402
from scripts.pettripfinder.contracts import withholding as WH        # noqa: E402
from scripts.pettripfinder.policy_migration import (                 # noqa: E402
    evidence_hash, evidence_ref_for, record_hash)
from scripts.pettripfinder.site_data import normalize_name           # noqa: E402

WORK_ORDER = "PTF-LOUISVILLE-PROMOTION-AND-APPLICATION-002"
MARKET = "louisville-ky"
APPLIED_ON = "2026-09-05"

PACKAGE = _REPO_ROOT / "launch_packages" / "pettripfinder"
POLICY_PATH = PACKAGE / ("hotel_policy_facts_%s.json" % MARKET)
# Ask the sharding module where this market's exclusion shard lives rather than
# rebuilding the path. The generated global carries the same basename, and this
# helper is the one place that knows which is which.
SHARD_PATH = MA.exclusions_shard_path(MARKET)
EVIDENCE_DIR = (PACKAGE / "markets" / "evidence" / MARKET
                / "parallel_revalidation_001")
CLEAN_INVENTORY = (PACKAGE / "markets" / "reports"
                   / "louisville_parallel_revalidation_001_clean_inventory.json")

#: The operative policy block per row: a contiguous, verbatim substring of the
#: artifact whose digest the clean inventory carries.
BLOCKS: Dict[str, str] = {
    "hotel bourre bonne": (
        "Is Hotel Bourré Bonne a pet-friendly property? Yes, well-behaved pets "
        "are welcome at Hotel Bourré Bonne! Pets up to 100 pounds are welcome, "
        "and there is a $75 per pet fee applied at check-in."),
    "the bellwether hotel": (
        "What is the hotel's pet policy? The Bellwether Hotel allows dogs only with "
        "the following restrictions: Dogs are only allowed in first floor rooms. We "
        "allow up to two dogs to stay as long as their combined weight is not over 50 "
        "pounds, or one dog not over 50 pounds. A $35 pet fee will be required at time "
        "of booking."),
    "baymont by wyndham louisville airport south": (
        "Dogs only please.Two dogs up to 25 lbs are allowed for a non-refundable "
        "charge of Dollar 20 plus tax per pet per night with a Dollar 100 refundable "
        "deposit. ADA defined service animals are also welcome at this hotel."),
    "candlewood suites louisville airport": (
        "Pets are welcome with a nonrefundable fee The charge is 30 USD per pet per "
        "night For stays of 7 nights or more a flat fee of 150 USD per pet applies"),
    "hawthorn suites by wyndham louisville east": (
        "Service Animals - ADA-defined service animals welcome. / Pets Allowed - 2 "
        "pets max. Dogs and cats only. 75lbs or less per pet. / Fees – 75USD per "
        "stay for 1–4 nights. 125USD per stay 5+ nights. 25USD per additional pet."),
    "staybridge suites": (
        "Our Pet Policy: Pets allowed with a non refundable fee of 75 plus tax for 1 "
        "to 6 nights and for 7 plus nights it is 150 plus tax."),
    "travelodge by wyndham sellersburg louisville north": (
        "Dogs and birds are allowed for a non-refundable charge of 20.00 USD per "
        "night. 1 pet maximum. Sorry no cats allowed. Pet Sanitation Fee is 150 USD if "
        "applicable. ADA defined service animals are welcome at this hotel."),
}

PET_FRIENDLY = tuple(BLOCKS)

NO_PETS = (
    "the brown hotel",
    "hotel louisville downtown",
    "holiday inn express and suites jeffersonville",
)

#: The refusal quote per excluded row, verbatim from its artifact.
REFUSALS: Dict[str, str] = {
    "the brown hotel":
        "Are you pet friendly? Pets not allowed (service animals are welcome, and are "
        "exempt from fees).",
    "hotel louisville downtown":
        "Is Hotel Louisville pet-friendly? No, only service animals are welcome at the "
        "property.",
    "holiday inn express and suites jeffersonville":
        "Can I bring my pet to Holiday Inn Express & Suites Louisville N - "
        "Jeffersonville? No, pets are not allowed at Holiday Inn Express & Suites "
        "Louisville N - Jeffersonville.",
}

#: Rows the revalidation called CLEAN_PET_FRIENDLY that the committed reader will not
#: back. Held, not published, and not silently dropped either.
HELD_BY_READER: Dict[str, str] = {
    "21c museum hotel":
        "reader withholds pets_allowed=SOURCE_SILENT on 'Pets are always welcome at "
        "21c.' -- the acceptance patterns permit filler words before 'is/are' but not "
        "between 'are' and 'welcome'. READER GAP.",
    "drury inn and suites louisville":
        "reader withholds pets_allowed=SOURCE_SILENT on 'Dogs and cats accepted.' -- "
        "the species-acceptance path has no branch for the verb 'accepted', yet derives "
        "species_allowed=[cat, dog] from the same sentence. READER GAP.",
    "drury inn and suites louisville north":
        "reader withholds pets_allowed=SOURCE_SILENT on 'Dogs and cats accepted.' -- "
        "same gap as the Louisville row; both pages state the identical brand policy.",
    "super 8 by wyndham louisville airport":
        "reader withholds pets_allowed=SOURCE_SILENT on 'Maximum of 2 pets ... at a "
        "nonrefundable charge of 25USD per pet per night.' -- there is no acceptance "
        "verb and the permission is implied only by the price. The reader refuses to "
        "read an allowance out of a price and is CORRECT; this row needs a different "
        "sentence, not a wider pattern.",
}

#: A charge the page states beside the fee that the single ``pet_fee`` slot cannot hold.
#:
#: EMPTY, deliberately. The Baymont row states two charges -- a 20-per-night fee and a
#: 100 refundable deposit -- but Firecrawl's markdown renders the currency symbol as the
#: WORD "Dollar", so the reader parses neither and withholds pet_fee as SOURCE_SILENT.
#: Hand-adding the deposit here while the fee stayed absent would publish a record
#: showing a deposit and no nightly fee, which reads as "no fee" and is worse than
#: silence on both. Either the reader reads the money or this record stays silent about
#: money; it does not get to be half-read by this order's judgement.
SECOND_CHARGE: Dict[str, Dict] = {}

#: The published NAME must round-trip: ``normalize_name(name)`` has to equal the
#: identity key, because BOTH the verified-only display join and the public route
#: are derived from it. ``normalize_name`` DELETES an accented character rather
#: than folding it, so "Hotel Bourré Bonne" normalises to "hotel bourr bonne" and
#: would never match the census key "hotel bourre bonne" -- the join fails closed
#: and the market cannot assemble. The ASCII spelling is published, the accented
#: spelling is recorded in the market's name_corrections overlay as the display a
#: reader should be shown, and the census row is not touched.
NAME_OVERRIDES: Dict[str, str] = {
    "hotel bourre bonne": "Hotel Bourre Bonne",
}

#: Prose the reader does not lift but the schema carries verbatim.
PROSE: Dict[str, Dict[str, str]] = {
    "the bellwether hotel": {
        "pet_room_restriction": "Dogs are only allowed in first floor rooms.",
    },
}


def _fail(msg: str) -> None:
    raise SystemExit("%s: %s" % (WORK_ORDER, msg))


def _load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, doc: Dict) -> None:
    path.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")


def clean_rows() -> Dict[str, Dict]:
    doc = _load(CLEAN_INVENTORY)
    return {r["identity_key"]: r for r in doc["rows"]}


def census() -> Dict[str, Dict]:
    doc = _load(PACKAGE / "identity_census" / ("%s.json" % MARKET))
    return {h["identity_key"]: h for h in doc["hotels"]}


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


def build_pet_friendly(key: str, row: Mapping, block: str, name: str) -> Dict:
    """One published record, with its facts derived by the committed reader."""
    url = row["canonical_url"]
    sha = row["document_sha256"]
    lane = row["lane"]
    captured_at = (row["captured_at"] or "")[:10]
    grade = "PT1_FIRST_PARTY"
    method = "firecrawl_rendered" if lane == "FIRECRAWL" else "direct_static_fetch"

    reading = PR.parse(block)
    ex = PR.to_extraction(reading, location=url)
    derived = dict(ex.extraction)
    withheld_in = dict(ex.withheld or {})

    facts: Dict[str, object] = {}
    evidence: List[Dict] = []

    def cite(field: str, quote: str) -> None:
        if quote and quote not in block:
            _fail("%s: the %s quote is not verbatim in its own block" % (key, field))
        evidence.append(_evidence_entry(field, quote, url, sha, grade, method,
                                        captured_at))

    # -- pets_allowed: the reader decides, or this row does not publish -----
    if derived.get("pets_allowed") is not True:
        _fail("%s: the reader did not derive pets_allowed=True (withheld: %s)"
              % (key, withheld_in.get("pets_allowed")))
    facts["pets_allowed"] = True
    cite("pets_allowed", reading.pets_allowed_quote)

    # -- the fee, exactly as the reader placed it --------------------------
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

    # -- a deposit is a SECOND charge, never the fee -----------------------
    second = SECOND_CHARGE.get(key)
    if second:
        extra = dict(second)
        quote = extra.pop("quote")
        facts.setdefault("other_charges", []).append(extra)
        cite("other_charges", quote)

    # -- weight ------------------------------------------------------------
    weight = derived.get("weight_limit")
    if isinstance(weight, Mapping):
        facts["weight_limit"] = {"value": weight["value"], "unit": weight["unit"],
                                 "operator": "lte", "scope": "per_pet"}
        cite("weight_limit", reading.weight_quote)

    # -- count -------------------------------------------------------------
    if derived.get("pet_count_limit"):
        facts["pet_count_limit"] = derived["pet_count_limit"]
        if derived.get("pet_count_scope"):
            facts["pet_count_scope"] = derived["pet_count_scope"]
        cite("pet_count_limit", reading.pet_count_quote)

    # -- species, only as the reader enumerated them -----------------------
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

    # -- prose the schema carries verbatim ---------------------------------
    for field, quote in (PROSE.get(key) or {}).items():
        facts[field] = quote
        cite(field, quote)

    allowed_refs = [e["evidence_ref"] for e in evidence if e["field"] == "pets_allowed"]
    # SOURCE_SILENT is not a withholding. The contract refuses it here in as many
    # words -- "genuine silence is the ABSENCE of the field, not an entry claiming a
    # decision was made" -- so a silent field is dropped from withheld_fields and
    # reported in projection_notes instead, exactly as this market's committed
    # records already do.
    silent = sorted(f for f, r in withheld_in.items()
                    if r == enums.SOURCE_SILENT and f in PS.KNOWN_FACT_FIELDS)
    withheld_fields = {
        field: WH.withheld(
            field, reason, "the committed reader refused this field: %s" % reason,
            allowed_refs, withheld_at=APPLIED_ON, withheld_by=WORK_ORDER)
        for field, reason in sorted(withheld_in.items())
        if field in PS.KNOWN_FACT_FIELDS and reason != enums.SOURCE_SILENT
    }
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
        "computation_class": (enums.COMPUTATION_CLASSES[1]
                              if facts.get("pet_count_limit") == 1
                              else enums.COMPUTATION_CLASSES[0]),
        "acquisition_lane": lane,
        "applied_by": WORK_ORDER,
    }
    if withheld_fields:
        record["withheld_fields"] = withheld_fields
    if projection_notes:
        record["projection_notes"] = projection_notes

    # The service-animal sentence is a legal access category, never a pet
    # permission. It is a TOP-LEVEL record field with a structured shape -- a bare
    # quote string is renderer-fatal -- and its charges_stated is classified by the
    # contract's own module rather than by this order reading the sentence.
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
            "PTF-LOUISVILLE-PARALLEL-REVALIDATION-001 published for review and directed "
            "its application. The facts here are the committed reader's, including every "
            "field it refused; four rows the revalidation called clean are HELD because "
            "the reader would not derive their pets_allowed." % (WORK_ORDER, APPLIED_ON),
        ],
    }
    return record


def build_exclusion(key: str, row: Mapping, cen: Mapping) -> Dict:
    """One VERIFIED_NO_PETS exclusion, hashed by the contract's own functions."""
    name = cen["canonical_name"]
    record = {
        "exclusion_id": "lk-" + key.replace(" ", "-"),
        "canonical_name": name,
        "normalized_name": normalize_name(name),
        "address": cen.get("address") or "",
        "city": cen.get("city") or "",
        "state": cen.get("state") or "KY",
        "postal_code": cen.get("postal_code") or "",
        "official_url": row["canonical_url"],
        "exclusion_state": HX.VERIFIED_NO_PETS,
        "evidence_quote": REFUSALS[key],
        "evidence_context": REFUSALS[key],
        "source_url": row["canonical_url"],
        "observed_at": (row["captured_at"] or "")[:10],
        "source_hash": row["document_sha256"],
        "reviewer_id": "jfields80",
        "reviewed_at": APPLIED_ON,
        "notes": (
            "Affirmative, property-specific refusal read from the property's own page. "
            "The service-animal wording beside it is a legal access category and is "
            "never read as a pet permission. Captured at $0.00 by "
            "PTF-LOUISVILLE-PARALLEL-REVALIDATION-001 on the %s lane, with the digest "
            "taken in the same fetch as the quote. NOTE: the committed policy reader "
            "derives pets_allowed=TRUE from the Hotel Louisville sentence because it "
            "matches 'pet-friendly' in the QUESTION and ignores the 'No' that answers "
            "it; that is why these refusals are recorded through the exclusion "
            "contract, which reads the quote, and never through the policy reader. "
            "Applied under %s." % (row["lane"], WORK_ORDER)),
        "market_id": MARKET,
        "decision_source": WORK_ORDER,
    }
    record["record_hash"] = HX.record_hash(record)
    record["approval_hash"] = HX.approval_hash(record)
    return record


def apply(write: bool = False) -> Dict:
    rows = clean_rows()
    cen = census()
    package = _load(POLICY_PATH)
    shard = _load(SHARD_PATH)

    existing_policy = {h["identity_key"] for h in package["hotels"]}
    existing_excl = {r["normalized_name"] for r in shard["exclusions"]}

    new_records: List[Dict] = []
    for key in PET_FRIENDLY:
        row = rows.get(key)
        if row is None:
            _fail("%s is not in the committed clean inventory" % key)
        if row["disposition"] != "CLEAN_PET_FRIENDLY":
            _fail("%s is not CLEAN_PET_FRIENDLY" % key)
        if key in existing_policy:
            _fail("%s is already published; this order adds only new rows" % key)
        name = NAME_OVERRIDES.get(key, cen[key]["canonical_name"])
        if normalize_name(name) != key:
            _fail("%s: the published name %r normalises to %r, which is not this "
                  "record's identity key -- the display join and the public route "
                  "both derive from it and would break"
                  % (key, name, normalize_name(name)))
        new_records.append(build_pet_friendly(key, row, BLOCKS[key], name))

    new_exclusions: List[Dict] = []
    for key in NO_PETS:
        row = rows.get(key)
        if row is None:
            _fail("%s is not in the committed clean inventory" % key)
        if row["disposition"] != "CLEAN_VERIFIED_NO_PETS":
            _fail("%s is not CLEAN_VERIFIED_NO_PETS" % key)
        record = build_exclusion(key, row, cen[key])
        if record["normalized_name"] in existing_excl:
            _fail("%s is already excluded" % key)
        new_exclusions.append(record)

    # APPEND, never re-sort. The committed 46 are not in identity-key order, so
    # sorting would rewrite every one and bury seven real additions in a
    # thousands-of-lines reordering diff.
    package["hotels"] = list(package["hotels"]) + new_records
    shard["exclusions"] = list(shard["exclusions"]) + new_exclusions
    shard["count"] = len(shard["exclusions"])

    issues = PS.validate_package(package)
    for record in new_records:
        issues = issues + EV.validate(record) + WH.validate(record)
    if issues:
        for issue in issues:
            print("  SCHEMA ISSUE %s %s: %s" % (issue.path, issue.code, issue.detail))
        _fail("%d contract issue(s); nothing written" % len(issues))
    HX.validate({"schema": HX.SCHEMA, "exclusions": shard["exclusions"]})

    if write:
        _write(POLICY_PATH, package)
        _write(SHARD_PATH, shard)

    return {
        "work_order": WORK_ORDER, "market_id": MARKET, "written": write,
        "policy_records_added": len(new_records),
        "exclusions_added": len(new_exclusions),
        "policy_total": len(package["hotels"]),
        "exclusion_total": shard["count"],
        "pet_friendly": list(PET_FRIENDLY),
        "verified_no_pets": list(NO_PETS),
        "held_by_reader": HELD_BY_READER,
        "withheld": {r["identity_key"]: sorted(r.get("withheld_fields") or {})
                     for r in new_records if r.get("withheld_fields")},
    }


if __name__ == "__main__":
    print(json.dumps(apply(write="--write" in sys.argv), indent=1))
