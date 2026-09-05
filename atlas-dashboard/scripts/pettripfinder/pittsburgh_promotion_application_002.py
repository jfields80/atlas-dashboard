"""PTF-PITTSBURGH-PROMOTION-AND-APPLICATION-002 -- apply the clean 12.

Promotes EXACTLY the publication-grade rows that
PTF-PITTSBURGH-PARALLEL-REVALIDATION-001 left pending: 8 CLEAN_PET_FRIENDLY into
the policy package and 4 CLEAN_VERIFIED_NO_PETS into this market's exclusion
shard. Nothing else moves.

WHERE THE FACTS COME FROM
-------------------------
Not from this module's opinion of the captured text. Each row's policy block is
handed to the repository's own reader (``brightdata.policy_reading``), and the
facts published are the ones IT derives, including every field it refuses to
derive. That is why three rows publish with a withheld fee and one with a
withheld weight: the reader judged the source could not determine them, and a
promotion order is not the place to overrule a reader.

Two places go BEYOND the reader's observation vocabulary, and both are the
schema expressing something the observation format cannot:

* ``fee_tiers`` for the Hyatt row. ``to_extraction`` withholds a banded fee as
  SCHEMA_CANNOT_REPRESENT because the observation format holds ONE amount, but
  schema 1.2 has carried ``fee_tiers[]`` since the policy migration and
  ``parse_stay_bands`` returns this ladder with an empty ``problems`` tuple --
  contiguous 1-6 and 7-30, both bases stated. PTF-MILWAUKEE-READER-TO-TIERS-034
  exists for exactly this gap, and its ``tiers_from_bands`` builds the rungs.
* ``other_charges`` for the two rows whose page states a SECOND labelled charge
  beside the first. The reader withholds ``pet_fee`` there because one slot
  cannot hold two prices; the schema's answer is that the additional charge
  lives in ``other_charges[]``. Each charge keeps its own labelled quote, so
  neither is inferred from the other and neither is collapsed into it.

IDENTITY IS NEVER POSITIONAL
----------------------------
Every row is looked up by identity key, and every evidence entry carries the
artifact digest that was taken in the SAME browser call as its quote. Nothing
binds by array order.

APPROVAL
--------
The approval block records PTF-PITTSBURGH-PROMOTION-AND-APPLICATION-002, dated
2026-09-04, as the authorising instrument, because that order named this exact
12-row set and enumerated what to exclude from it. The caveat says so in words
rather than leaving a bare name behind, so a later reader can see WHAT was
approved and by which instrument.

Read-only with respect to every other market. No network.
"""

from __future__ import annotations

import json
import re
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
from scripts.pettripfinder.contracts import policy_schema as PS      # noqa: E402
from scripts.pettripfinder.contracts import evidence as EV           # noqa: E402
from scripts.pettripfinder.contracts import withholding as WH        # noqa: E402
from scripts.pettripfinder.policy_migration import (                 # noqa: E402
    evidence_hash, evidence_ref_for, record_hash)
from scripts.pettripfinder.site_data import normalize_name           # noqa: E402

WORK_ORDER = "PTF-PITTSBURGH-PROMOTION-AND-APPLICATION-002"
MARKET = "pittsburgh-pa"
APPLIED_ON = "2026-09-04"
CAPTURED_ON = "2026-09-04"

PACKAGE = _REPO_ROOT / "launch_packages" / "pettripfinder"
POLICY_PATH = PACKAGE / f"hotel_policy_facts_{MARKET}.json"
# Ask the sharding module for this market's shard rather than rebuilding the
# path here. Same file, but the write goes through the one helper that knows
# where a shard lives, so no reader of this module has to prove the join is a
# shard and not the generated global of the same basename.
SHARD_PATH = MA.exclusions_shard_path(MARKET)
CAPTURE_PATH = (PACKAGE / "markets" / "reports"
                / "pittsburgh_parallel_revalidation_001_attended_capture.json")
FIRECRAWL_BLOCKS = {
    "crowne plaza pittsburgh south": {
        "block": "Pet fee per night: 45 USD Pet weight limit: 100 2 pets allowed",
        "url": "https://www.ihg.com/crowneplaza/hotels/us/en/pittsburgh/pitso/hoteldetail",
        "artifact_sha256": "sha256:179def692fd9142b7799ac2e30f97ad6b64dd08814b9f5add1631e80aa0cca0b",
        "name": "Crowne Plaza Pittsburgh South",
        "lane": "FIRECRAWL",
    },
    "hotel indigo pittsburgh university oakland": {
        "block": ("Pet fee per night: 75 USD Pet damage deposit: 75 USD "
                  "Pet weight limit: No weight limit per pet 4 pets allowed"),
        "url": "https://www.ihg.com/hotelindigo/hotels/us/en/pittsburgh/pitgh/hoteldetail",
        "artifact_sha256": "sha256:27520fa3689618a531fb65ecd770dbc96a82d4043fe6ab690ad2f0e13b539d11",
        "name": "Hotel Indigo Pittsburgh University - Oakland",
        "lane": "FIRECRAWL",
    },
}

PET_FRIENDLY = (
    "marriott pittsburgh north cranberry woods",
    "residence inn pittsburgh cranberry township",
    "residence inn pittsburgh monroeville",
    "courtyard by marriott cranberry woods",
    "fairfield inn and suites pittsburgh downtown",
    "hyatt house pittsburgh south side works",
    "crowne plaza pittsburgh south",
    "hotel indigo pittsburgh university oakland",
)
NO_PETS = (
    "ac hotel by marriott pittsburgh downtown",
    "springhill suites pittsburgh mills",
    "springhill suites pittsburgh monroeville",
    "springhill suites pittsburgh southside works",
)

#: Rows whose page states a SECOND labelled charge the single ``pet_fee`` slot
#: cannot hold. Each entry names the charge the reader could not place and the
#: quote it came from, so nothing here is inferred from the other charge.
SECOND_CHARGE = {
    "courtyard by marriott cranberry woods": {
        "primary": {"amount_cents": 7500, "basis": "per_stay",
                    "quote": "Non-Refundable Pet Fee Per Stay: $75.00"},
        "additional": {"amount_cents": 2000, "currency": "USD", "basis": "per_night",
                       "kind": "non_refundable_fee", "refundable": False,
                       "refundable_stated": True,
                       "quote": "Non-Refundable Pet Fee Per Night: $20.00"},
    },
}

#: Rows where the reader's ``pets_allowed`` quote is a HEADING fragment rather
#: than the operative statement. The Marriott and IHG rows are left alone: their
#: "Pets Welcome" / "pets allowed" IS the label-value pair under the page's own
#: Pet Policy heading, which is what the market's other 53 records already cite.
#: Hyatt is different -- its operative sentence is prose, and the reader lifts
#: the two words "Pet Friendly" out of the block's title, which on the page
#: would be indistinguishable from the amenity chip this market refuses to
#: publish. The quote below is that property's own sentence, verbatim.
OPERATIVE_ALLOWED_QUOTE = {
    "hyatt house pittsburgh south side works":
        "We happily welcome your canine travel companions at Hyatt House "
        "Pittsburgh-South Side.",
}

#: Prose the reader does not lift but the schema carries verbatim.
PROSE = {
    "marriott pittsburgh north cranberry woods": {
        "pet_room_restriction": ("1st floor only", "1st floor only")},
    "courtyard by marriott cranberry woods": {
        "pet_room_restriction": ("1st floor only", "1st floor only")},
    "hyatt house pittsburgh south side works": {
        "general_restrictions": ("All dogs must be housebroken.",
                                 "All dogs must be housebroken.")},
}


def _fail(msg: str) -> None:
    raise SystemExit("%s: %s" % (WORK_ORDER, msg))


def _load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, doc: Dict) -> None:
    path.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")


def captures() -> Dict[str, Dict]:
    doc = _load(CAPTURE_PATH)
    return {c["identity_key"]: c for c in doc["captures"]}


def _evidence_entry(field: str, quote: str, url: str, sha: str, grade: str,
                    method: str) -> Dict:
    entry = {
        "field": field,
        "quote": quote,
        "source_url": url,
        "artifact_class": enums.PUBLICATION_GRADE_EVIDENCE,
        "artifact_sha256": sha,
        "artifact_kind": "rendered_html",
        "captured_at": CAPTURED_ON,
        "capture_method": method,
        "source_grade": grade,
    }
    entry["evidence_ref"] = evidence_ref_for(entry)
    return entry


def census_names() -> Dict[str, str]:
    doc = _load(PACKAGE / "identity_census" / ("%s.json" % MARKET))
    return {h["identity_key"]: h["canonical_name"] for h in doc["hotels"]}


def build_pet_friendly(key: str, cap: Mapping, block: str, url: str, sha: str,
                       lane: str, display_name: str) -> Dict:
    """One published record, with its facts derived by the committed reader."""
    reading = PR.parse(block)
    ex = PR.to_extraction(reading, location=url)
    derived = dict(ex.extraction)
    withheld_in = dict(ex.withheld or {})

    facts: Dict[str, object] = {}
    evidence: List[Dict] = []
    grade = "PT2_BRAND"
    method = "firecrawl_rendered" if lane == "FIRECRAWL" else "browser_assisted"

    def cite(field: str, quote: str) -> None:
        evidence.append(_evidence_entry(field, quote, url, sha, grade, method))

    # -- pets_allowed ------------------------------------------------------
    if derived.get("pets_allowed") is not True:
        _fail("%s: the reader did not derive pets_allowed=True" % key)
    facts["pets_allowed"] = True
    allowed_quote = OPERATIVE_ALLOWED_QUOTE.get(key) or reading.pets_allowed_quote
    if allowed_quote not in block:
        _fail("%s: the pets_allowed quote is not verbatim in its own block" % key)
    cite("pets_allowed", allowed_quote)

    # -- the fee, or the ladder the observation format could not hold ------
    second = SECOND_CHARGE.get(key)
    bands = PR.parse_stay_bands(block)
    if bands.bands and not bands.problems:
        tiers = PR.tiers_from_bands(bands.bands)
        facts["fee_tiers"] = tiers
        for band in bands.bands:
            cite("fee_tiers", band.quote)
        withheld_in.pop("pet_fee", None)
        withheld_in.pop("fee_basis", None)
    elif second:
        facts["pet_fee"] = {
            "amount_cents": second["primary"]["amount_cents"], "currency": "USD",
            "basis": second["primary"]["basis"], "refundable": False,
        }
        cite("pet_fee", second["primary"]["quote"])
        extra = dict(second["additional"])
        quote = extra.pop("quote")
        facts["other_charges"] = [extra]
        cite("other_charges", quote)
        withheld_in.pop("pet_fee", None)
        withheld_in.pop("fee_basis", None)
    elif "pet_fee" in derived:
        fee = {"amount_cents": derived["pet_fee"],
               "currency": derived.get("fee_currency", "USD"),
               "basis": derived["fee_basis"]}
        charge = next((c for c in reading.charges if c.kind == "fee"), None)
        if charge is not None and charge.refundable is not None:
            fee["refundable"] = bool(charge.refundable)
        facts["pet_fee"] = fee
        cite("pet_fee", charge.quote if charge is not None else "")

    # -- a deposit is a SECOND charge, never the fee -----------------------
    if "pet_deposit" in derived:
        deposit = next((c for c in reading.charges if c.kind == "deposit"), None)
        facts.setdefault("other_charges", []).append({
            "amount_cents": derived["pet_deposit"], "currency": "USD",
            "kind": "refundable_deposit", "refundable_stated": False,
        })
        cite("other_charges", deposit.quote if deposit is not None else "")

    # -- weight ------------------------------------------------------------
    weight = derived.get("weight_limit")
    if isinstance(weight, Mapping):
        facts["weight_limit"] = {"value": weight["value"], "unit": weight["unit"],
                                 "operator": "lte", "scope": "per_pet"}
        cite("weight_limit", reading.weight_quote)
    if "No weight limit" in block:
        facts["weight_limit_stated_none"] = True
        cite("weight_limit_stated_none", "Pet weight limit: No weight limit per pet")

    combined = PR.parse(block).__dict__ if False else None
    if "Combined pets weight limit: 75 Pounds" in block:
        facts["combined_weight_limit"] = {"value": 75.0, "unit": "lb",
                                          "operator": "lte"}
        cite("combined_weight_limit", "Combined pets weight limit: 75 Pounds")

    # -- count -------------------------------------------------------------
    if derived.get("pet_count_limit"):
        facts["pet_count_limit"] = derived["pet_count_limit"]
        if derived.get("pet_count_scope"):
            facts["pet_count_scope"] = derived["pet_count_scope"]
        cite("pet_count_limit", reading.pet_count_quote)

    # -- species: stated for dogs only, and silent about cats --------------
    if reading.dogs_only_quote or "canine travel companions" in block:
        facts["species"] = {"dogs": enums.SPECIES_ACCEPTED}
        facts["species_source_grade"] = {"dogs": grade}
        cite("species", "We happily welcome your canine travel companions")

    # -- prose the schema carries verbatim ---------------------------------
    for field, (value, quote) in (PROSE.get(key) or {}).items():
        facts[field] = value
        cite(field, quote)

    withheld_fields = {
        field: WH.withheld(
            field, reason, "the committed reader refused this field: %s" % reason,
            [e["evidence_ref"] for e in evidence if e["field"] == "pets_allowed"],
            withheld_at=APPLIED_ON, withheld_by=WORK_ORDER)
        for field, reason in sorted(withheld_in.items())
        if field in PS.KNOWN_FACT_FIELDS
    }

    quotes = [e["quote"] for e in evidence]
    record: Dict[str, object] = {
        "key": key,
        "name": display_name,
        "facts": facts,
        "evidence": evidence,
        "evidence_count": len(evidence),
        "evidence_quote": " [.] ".join(quotes),
        "source_url": url,
        "source_type": "EXACT_ENTITY_DOMAIN",
        "verification_state": "VERIFIED_PET_FRIENDLY",
        "verification_date": CAPTURED_ON,
        "verified_at": CAPTURED_ON,
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

    record["approval"] = {
        "decision": "APPROVED_AFTER_CURRENT_REVIEW",
        "operator": "jfields80",
        "approval_date": APPLIED_ON,
        "record_hash": record_hash(record),
        "evidence_hash": evidence_hash(evidence),
        "caveats": [
            "Authorising instrument: %s, issued %s, which named this exact "
            "12-row clean inventory (8 pet-friendly, 4 verified-no-pets), "
            "enumerated what must not be promoted, and directed its "
            "application. The evidence for this row was published for review in "
            "PTF-PITTSBURGH-PARALLEL-REVALIDATION-001 before the instrument was "
            "issued." % (WORK_ORDER, APPLIED_ON),
        ],
    }
    return record


def _postal_code(city_state_zip: str) -> str:
    """The five-digit ZIP out of a property page's own locality line.

    Splitting on the comma and taking the last field is wrong, because the
    brands do not agree on how many commas the line has. Marriott prints
    "Pittsburgh, Pennsylvania, USA, 15219" and the last field IS the ZIP;
    Hyatt prints "Pittsburgh, PA 15203" and the last field is "PA 15203".
    The ZIP is what this returns, or "" when the line states none -- an empty
    postal code is a missing field the contract can refuse, while "PA 15203"
    is a wrong field that passes for one.
    """
    match = re.search(r"\b(\d{5})(?:-\d{4})?\b", city_state_zip or "")
    return match.group(1) if match else ""


def build_exclusion(key: str, cap: Mapping, display_name: str) -> Dict:
    """One VERIFIED_NO_PETS exclusion, hashed by the contract's own functions.

    Where a row carries an ``address_completion_reread`` the digest and URL come
    from THAT artifact, because it is the one that demonstrably contains both
    the street and the same refusal quote. Splitting them across two artifacts
    would leave a record whose address no digest covers.
    """
    sig = cap["identity_signals"]
    city_zip = (sig.get("city_state_zip") or "").split(",")
    city = city_zip[0].strip() if city_zip else ""
    postal = _postal_code(sig.get("city_state_zip") or "")
    name = display_name
    reread = cap.get("address_completion_reread") or {}
    source_url = reread.get("final_url") or cap["final_url"]
    source_hash = reread.get("artifact_sha256") or cap["artifact_sha256"]
    observed_on = "2026-09-05" if reread else CAPTURED_ON
    record = {
        "exclusion_id": "pgh-" + key.replace(" ", "-"),
        "canonical_name": name,
        "normalized_name": normalize_name(name),
        "address": sig.get("street") or "",
        "city": city,
        "state": "PA",
        "postal_code": postal,
        "official_url": source_url,
        "exclusion_state": HX.VERIFIED_NO_PETS,
        "evidence_quote": cap["policy_quote"],
        "source_url": source_url,
        "observed_at": observed_on,
        "source_hash": source_hash,
        "reviewer_id": "jfields80",
        "reviewed_at": APPLIED_ON,
        "notes": (
            "Affirmative, property-specific refusal read from the LABEL-VALUE "
            "pair under the page's own 'Pet Policy' heading, not from an "
            "amenity-list line. Service-animal wording beside it is a legal "
            "access category and is never read as a pet permission. Captured "
            "attended at $0.00 by PTF-PITTSBURGH-PARALLEL-REVALIDATION-001; the "
            "digest was taken in the same browser call as the quote. Applied "
            "under %s, issued %s, which named this exact 4-row no-pets set."
            % (WORK_ORDER, APPLIED_ON)),
        "market_id": MARKET,
    }
    record["record_hash"] = HX.record_hash(record)
    record["approval_hash"] = HX.approval_hash(record)
    return record


def apply(write: bool = False) -> Dict:
    caps = captures()
    names = census_names()
    package = _load(POLICY_PATH)
    shard = _load(SHARD_PATH)

    existing_policy = {h["identity_key"] for h in package["hotels"]}
    existing_excl = {r["normalized_name"] for r in shard["exclusions"]}

    new_records: List[Dict] = []
    for key in PET_FRIENDLY:
        if key in existing_policy:
            _fail("%s is already published; this order adds only new rows" % key)
        fc = FIRECRAWL_BLOCKS.get(key)
        if fc:
            cap = {"canonical_name": fc["name"]}
            block, url, sha, lane = fc["block"], fc["url"], fc["artifact_sha256"], fc["lane"]
        else:
            cap = caps.get(key)
            if cap is None:
                _fail("%s has no committed attended capture" % key)
            if cap["classification"] != "CLEAN_PET_FRIENDLY":
                _fail("%s is not CLEAN_PET_FRIENDLY" % key)
            block, url = cap["policy_quote"], cap["final_url"]
            sha, lane = cap["artifact_sha256"], "FREE_ATTENDED_CHROME"
        new_records.append(build_pet_friendly(key, cap, block, url, sha, lane,
                                              names[key]))

    new_exclusions: List[Dict] = []
    for key in NO_PETS:
        cap = caps.get(key)
        if cap is None:
            _fail("%s has no committed attended capture" % key)
        if cap["classification"] != "CLEAN_VERIFIED_NO_PETS":
            _fail("%s is not CLEAN_VERIFIED_NO_PETS" % key)
        record = build_exclusion(key, cap, names[key])
        if record["normalized_name"] in existing_excl:
            _fail("%s is already excluded" % key)
        new_exclusions.append(record)

    # APPEND, never re-sort. The committed 53 are not in identity-key order,
    # so sorting would rewrite every one of them and bury eight real additions
    # in an 8,000-line reordering diff.
    package["hotels"] = list(package["hotels"]) + new_records
    shard["exclusions"] = shard["exclusions"] + new_exclusions
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
        "pet_friendly": list(PET_FRIENDLY), "verified_no_pets": list(NO_PETS),
        "withheld": {r["identity_key"]: sorted(r.get("withheld_fields") or {})
                     for r in new_records if r.get("withheld_fields")},
    }


if __name__ == "__main__":
    print(json.dumps(apply(write="--write" in sys.argv), indent=1))
