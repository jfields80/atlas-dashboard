"""PTF-DETROIT-ANN-ARBOR-EVIDENCE-VOCABULARY-AND-PROMOTION-004 -- apply the
founder's decisions on the Detroit Capture Pass 3 packet.

WHY THIS RUNS NOW AND NOT IN PASS 3
-----------------------------------
The 30-row packet has been evidence-complete and hash-stable since Pass 3, and
it still could not be approved: its artifacts are TEXT EXTRACTS, and
``text_extract`` was not a registered artifact kind, so every publication
candidate failed the evidence contract at ``artifact_kind``. A second, purely
mechanical defect sat behind it -- the packet recorded the Python CONSTANT NAME
``GRADE_PT1_FIRST_PARTY`` where the contract expects that constant's VALUE,
``PT1_FIRST_PARTY``, and an unrecognised grade cannot be shown to be
first-party, so the contract refused to publish it as well.

Founder decision B-003-1 registered the kind under eight conditions, and this
run is the first that may sign against it.

WHAT THIS DOES NOT DO
---------------------
* It does not re-fetch or re-capture anything. Every artifact is read from
  disk and re-hashed; nothing is acquired.
* It does not convert SOURCE SILENCE into a refusal. The two POLICY_NOT_FOUND
  rows stay held and never enter authority.
* It does not promote the shadow census, admit a boundary municipality, or
  touch any market but Detroit.

WHAT IT VERIFIES BEFORE IT SIGNS ANYTHING
-----------------------------------------
Per row: the artifact exists; its sha256 reproduces and matches BOTH the
committed manifest and the committed packet; the identity resolves to a census
row; the source grade normalises to a first-party value; the evidence entries
pass the publication contract; and every quote appears verbatim and contiguously
in the artifact BYTES. That last one is the check a hash cannot perform -- a
hash proves the file is unaltered, not that the quotation came out of it.

Any failure stops the whole run. A partial authority write is worse than none.
"""

from __future__ import annotations

import hashlib
import json
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List

from scripts.pettripfinder import hotel_exclusions as EX
from scripts.pettripfinder import market_authority as MA
from scripts.pettripfinder.contracts import enums
from scripts.pettripfinder.contracts import evidence as evidence_contract
from scripts.pettripfinder.contracts import policy_schema
from scripts.pettripfinder.policy_migration import evidence_ref_for, record_hash, evidence_hash

_REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE = _REPO_ROOT / "launch_packages" / "pettripfinder"
RAW = (_REPO_ROOT / "data" / "worker_runs" / "pettripfinder"
       / "detroit-ann-arbor-capture-pass3-001" / "raw")

MARKET = "detroit-ann-arbor-mi"
# PTF-ACTIVE-BRANCH-SHARD-MIGRATION-001. This market's exclusions live in its
# OWN authority shard. The global launch_packages/pettripfinder/
# hotel_exclusions.json is a GENERATED compatibility artifact assembled from
# every market's shard: writing it here would conflict with every other
# market's branch and be overwritten by the next assembly. The shard path comes
# from market_authority so this module never names a generated global at all.
EXCLUSIONS_SHARD_PATH = MA.exclusions_shard_path("detroit-ann-arbor-mi")
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-EVIDENCE-VOCABULARY-AND-PROMOTION-004"
DECISION_DATE = "2026-08-29"
CAPTURE_DATE = "2026-08-17"
FOUNDER = "jfields80"

#: The founder wrote the Pass 3 split into the work order itself: 10
#: APPROVE_PUBLISH, 18 APPROVE_VERIFIED_NO_PETS, 2 HOLD. The packet's own
#: recommendation for every row is checked against that split before anything
#: is signed, so a packet edited after the order was written cannot slip a row
#: into authority under an authorisation that never named it.
AUTHORISED_SPLIT = {"APPROVE_PUBLISH": 10,
                    "APPROVE_VERIFIED_NO_PETS": 18,
                    "HOLD_FOR_FURTHER_RESEARCH": 2}

#: The ONLY grade rewrite this run performs: constant NAME -> constant VALUE.
#: Anything else passes through untouched so the contract can refuse it. A
#: coercion that turned an unknown grade into PT1 would be exactly the upgrade
#: the founder forbade.
GRADE_NORMALISATION = {"GRADE_PT1_FIRST_PARTY": enums.GRADE_PT1_FIRST_PARTY}


class Stop(SystemExit):
    pass


def _sha_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(name: str) -> Dict:
    return json.loads((PACKAGE / name).read_text(encoding="utf-8"))


def _write(path: Path, doc) -> None:
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8", newline="\n")


def normalise_grade(raw: str) -> str:
    return GRADE_NORMALISATION.get(raw, raw)


def _value_display(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True)
    return str(value)


def verify_artifact(cand: Dict, manifest: Dict) -> tuple:
    """(artifact_sha_with_prefix, artifact_text). Stops on any mismatch."""
    qid = cand["queue_id"]
    entry = manifest.get(qid)
    if entry is None:
        raise Stop("STOP %s: no manifest entry" % qid)
    path = RAW / Path(entry["artifact_file"]).name
    if not path.is_file():
        raise Stop("STOP %s: artifact missing on disk at %s" % (qid, path))
    actual = _sha_file(path)
    if actual != entry["artifact_sha256"]:
        raise Stop("STOP %s: artifact hash drifted from the committed manifest" % qid)
    if actual != cand["artifact_sha256"]:
        raise Stop("STOP %s: artifact hash drifted from the committed packet" % qid)
    return "sha256:" + actual, path.read_text(encoding="utf-8")


def build_evidence(cand: Dict, artifact_sha: str) -> List[Dict]:
    grade = normalise_grade(cand["source_grade"])
    out: List[Dict] = []
    for fact in cand["proposed_schema_1_2_facts"]:
        entry = OrderedDict([
            ("field", fact["field"]), ("quote", fact["quote"]),
            ("source_url", cand["final_url"]),
            ("value", _value_display(fact["value"])), ("evidence_ref", ""),
            ("artifact_class", enums.PUBLICATION_GRADE_EVIDENCE),
            ("artifact_sha256", artifact_sha),
            ("artifact_kind", enums.ARTIFACT_TEXT_EXTRACT),
            ("captured_at", CAPTURE_DATE),
            ("capture_method", "attended_browser"),
            ("source_grade", grade),
        ])
        entry["evidence_ref"] = evidence_ref_for(entry)
        out.append(entry)
    return out


def build_publication_record(cand: Dict, census_row: Dict, artifact_sha: str,
                             artifact_text: str) -> Dict:
    evidence = build_evidence(cand, artifact_sha)

    # Founder condition 6, where the bytes are in hand. A hash proves the file
    # is unaltered; only this proves the quote came out of it.
    for entry in evidence:
        blockers = evidence_contract.text_extract_publication_blockers(
            entry, artifact_text)
        if blockers:
            raise Stop("STOP %s: %s (%r)" % (cand["queue_id"], blockers[0],
                                             entry["quote"][:60]))

    facts: "OrderedDict[str, object]" = OrderedDict()
    sas = None
    for fact in cand["proposed_schema_1_2_facts"]:
        if fact["field"] == "service_animal_statement":
            sas = fact["value"]
        else:
            facts[fact["field"]] = fact["value"]

    quotes: List[str] = []
    for entry in evidence:
        if entry["quote"] not in quotes:
            quotes.append(entry["quote"])

    record = OrderedDict([
        ("key", census_row["identity_key"]), ("name", census_row["canonical_name"]),
        ("facts", facts), ("evidence", evidence), ("evidence_count", len(evidence)),
        ("evidence_quote", " […] ".join(quotes)),
        ("source_url", cand["final_url"]),
        ("source_type", "EXACT_ENTITY_DOMAIN"),
        ("verification_state", "VERIFIED_PET_FRIENDLY"),
        ("verification_date", DECISION_DATE), ("verified_at", DECISION_DATE),
        ("worker_model_id", ""), ("worker_prompt_version", ""),
        ("worker_result_hash", artifact_sha), ("worker_routing_version", ""),
        ("worker_validator_version", ""), ("schema_version", "1.2"),
        ("identity_key", census_row["identity_key"]), ("market_id", MARKET),
    ])
    if sas is not None:
        record["service_animal_statement"] = sas

    from scripts.pettripfinder import canonical_view
    record["computation_class"] = canonical_view.classify(facts).computation_class \
        if hasattr(canonical_view, "classify") else "DIRECT"

    issues = list(policy_schema.validate_record(record)) \
        + list(evidence_contract.validate(record))
    if issues:
        raise Stop("STOP %s: contract issues %s" % (cand["queue_id"], issues[:4]))

    record["approval"] = OrderedDict([
        ("decision", enums.APPROVED_AFTER_CURRENT_REVIEW),
        ("operator", FOUNDER),
        ("approval_date", DECISION_DATE),
        ("authorisation", OrderedDict([
            ("instrument", WORK_ORDER),
            ("clause", "PASS 3 FOUNDER APPROVAL -- 10 APPROVE_PUBLISH, 18 "
                       "APPROVE_VERIFIED_NO_PETS, 2 HOLD_FOR_FURTHER_RESEARCH"),
            ("packet_recommendation", cand["recommended_founder_decision"]),
            ("basis", "The operator authorised this split in writing in the work order "
                      "named above, against the packet's own per-row recommendations. It "
                      "is a blanket authorisation of the recorded classification, not a "
                      "per-row note written at a review desk, and is labelled that way "
                      "deliberately."),
        ])),
        ("caveats", [
            "Founder decision %s (%s), recorded verbatim in "
            "detroit_ann_arbor_capture_pass3_founder_review_packet.json. Evidence is a "
            "TEXT EXTRACT of the property's own policy surface, admitted as "
            "publication-grade under founder decision B-003-1: the artifact was hashed in "
            "the browser at capture time, persisted, and its sha256 re-verified from disk "
            "at approval time (%s). Every quote was checked to appear verbatim and "
            "contiguously in those bytes. Identity binding: %s."
            % (cand["decision_id"], cand["recommended_founder_decision"],
               artifact_sha[:23], cand["identity_binding"]),
            "Founder global rule applied: SOURCE SILENCE IS ABSENCE -- unstated optional "
            "facts are absent, never withheld.",
            cand.get("general_note") or "",
        ]),
        ("record_hash", record_hash(record)),
        ("evidence_hash", evidence_hash(evidence)),
    ])
    return record


def build_exclusion_record(cand: Dict, census_row: Dict, artifact_sha: str,
                           artifact_text: str) -> Dict:
    quote = cand["exact_quote"]
    if not evidence_contract.quote_is_contiguous(quote, artifact_text):
        raise Stop("STOP %s: the refusal quote is not verbatim in the artifact"
                   % cand["queue_id"])
    record = OrderedDict([
        ("exclusion_id", "dtw-%s" % census_row["slug"]),
        ("canonical_name", census_row["canonical_name"]),
        ("normalized_name", census_row["identity_key"]),
        ("address", census_row["address"]), ("city", census_row["city"]),
        ("state", census_row["state"]), ("postal_code", census_row["postal_code"]),
        ("official_url", cand["final_url"]),
        ("exclusion_state", EX.VERIFIED_NO_PETS),
        ("evidence_quote", quote),
        ("source_url", cand["final_url"]),
        ("observed_at", CAPTURE_DATE), ("source_hash", artifact_sha),
        ("reviewer_id", FOUNDER), ("reviewed_at", DECISION_DATE),
        ("notes",
         "Founder decision %s (%s), authorised by %s. Affirmative first-party refusal in "
         "the property's own words, captured as a TEXT EXTRACT of its own policy surface "
         "and admitted under founder decision B-003-1; the artifact sha256 was re-verified "
         "from disk at approval time and the refusal quote checked verbatim against those "
         "bytes. Identity binding: %s. Service-animal access is a legal category and never "
         "converts a no-pets policy into pet-friendly."
         % (cand["decision_id"], cand["recommended_founder_decision"], WORK_ORDER,
            cand["identity_binding"])),
        ("market_id", MARKET),
    ])
    record["record_hash"] = EX.record_hash(record)
    record["approval_hash"] = EX.approval_hash(record)
    return record


def main(argv=None) -> int:
    packet = _load("detroit_ann_arbor_capture_pass3_founder_review_packet.json")
    manifest = {m["queue_id"]: m for m in
                _load("detroit_ann_arbor_capture_pass3_001_evidence_manifest.json")["items"]}
    census = _load("identity_census/detroit-ann-arbor-mi.json")
    by_key = {h["identity_key"]: h for h in census["hotels"]}

    cands = packet["candidates"]
    seen_split: Dict[str, int] = {}
    for c in cands:
        seen_split[c["recommended_founder_decision"]] = \
            seen_split.get(c["recommended_founder_decision"], 0) + 1
    if seen_split != AUTHORISED_SPLIT:
        raise Stop("STOP: the packet's split %s is not the split the work order "
                   "authorised %s" % (seen_split, AUTHORISED_SPLIT))

    facts_doc = _load("hotel_policy_facts_detroit-ann-arbor-mi.json")
    excl_doc = json.loads(EXCLUSIONS_SHARD_PATH.read_text(encoding="utf-8"))
    published_before = len(facts_doc["hotels"])
    excluded_before = len(excl_doc["exclusions"])
    already = {h["identity_key"] for h in facts_doc["hotels"]}
    already |= {e["normalized_name"] for e in excl_doc["exclusions"]}

    new_facts: List[Dict] = []
    new_excl: List[Dict] = []
    holds: List[Dict] = []

    for cand in cands:
        decision = cand["recommended_founder_decision"]
        if decision == "HOLD_FOR_FURTHER_RESEARCH":
            holds.append(cand)
            continue
        key = cand["identity_key"]
        row = by_key.get(key)
        if row is None:
            raise Stop("STOP %s: %r is not in the committed census" % (cand["queue_id"], key))
        if key in already:
            raise Stop("STOP %s: %r is already answered" % (cand["queue_id"], key))
        artifact_sha, artifact_text = verify_artifact(cand, manifest)
        if decision == "APPROVE_PUBLISH":
            new_facts.append(build_publication_record(cand, row, artifact_sha, artifact_text))
        elif decision == "APPROVE_VERIFIED_NO_PETS":
            new_excl.append(build_exclusion_record(cand, row, artifact_sha, artifact_text))
        else:
            raise Stop("STOP %s: unknown decision %r" % (cand["queue_id"], decision))

    if len(new_facts) != AUTHORISED_SPLIT["APPROVE_PUBLISH"]:
        raise Stop("STOP: built %d publications, expected %d"
                   % (len(new_facts), AUTHORISED_SPLIT["APPROVE_PUBLISH"]))
    if len(new_excl) != AUTHORISED_SPLIT["APPROVE_VERIFIED_NO_PETS"]:
        raise Stop("STOP: built %d exclusions, expected %d"
                   % (len(new_excl), AUTHORISED_SPLIT["APPROVE_VERIFIED_NO_PETS"]))
    if len(holds) != AUTHORISED_SPLIT["HOLD_FOR_FURTHER_RESEARCH"]:
        raise Stop("STOP: %d holds, expected %d" % (len(holds),
                                                    AUTHORISED_SPLIT["HOLD_FOR_FURTHER_RESEARCH"]))

    facts_doc["hotels"] = facts_doc["hotels"] + new_facts
    facts_doc["work_order"] = WORK_ORDER
    _write(PACKAGE / "hotel_policy_facts_detroit-ann-arbor-mi.json", facts_doc)

    excl_doc["exclusions"] = excl_doc["exclusions"] + new_excl
    excl_doc["count"] = len(excl_doc["exclusions"])
    excl_doc["note"] = excl_doc["note"] + (
        " %s applied the Pass 3 founder decisions: %d further VERIFIED_NO_PETS records, each "
        "on an affirmative first-party refusal in the property's own words. The two "
        "POLICY_NOT_FOUND rows were NOT converted -- source silence is absence, not a refusal."
        % (WORK_ORDER, len(new_excl)))
    _write(EXCLUSIONS_SHARD_PATH, excl_doc)

    print("published : %d -> %d" % (published_before, len(facts_doc["hotels"])))
    print("no-pets   : %d -> %d" % (excluded_before, excl_doc["count"]))
    print("holds preserved (never entered authority): %s"
          % [h["hotel"] for h in holds])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
