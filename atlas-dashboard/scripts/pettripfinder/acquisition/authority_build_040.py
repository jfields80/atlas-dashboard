"""PTF-MILWAUKEE-FOUNDER-DECISION-040 -- four approvals into authority.

The founder approved three pet-friendly candidates and one refusal out of
039's six. This applies exactly those four and nothing else.

ADDITIVE, NOT A REBUILD
------------------------
036's authority document derives its seventy records from 036's ledger, every
time it is built. 040 does not touch that derivation: it takes those records
as they come out and appends its own, each carrying its own ledger, its own
work order and its own approval block. Two founder sittings, two lineages,
one file -- and the 036 half stays byte-identical, which is asserted.

THE CANDIDATES ARE NOT STORE ROWS
----------------------------------
Two of the three approvals were never production observations: their evidence
sat on disk from a provider decision test that 025 deliberately excludes from
the store. The third, Saint Kate, IS in the store, but with the reading the
store had BEFORE 038 repaired the place-restriction defect -- 038 declined to
re-project because doing so withdrew sixteen founder decisions, and that debt
is still recorded rather than paid.

So each approved candidate is turned into a store-row-shaped record built from
the committed 039 package -- the exact rows the founder read. That shape is
what the schema converter, the evidence builder and the binding contract all
already understand, so none of them needs a second implementation for this
work order.

WHAT IS NOT DONE HERE
---------------------
No provider call, no store re-projection, no identity-gate change, no schema
change, no publication, no deployment. The two held rows are not written
anywhere near authority.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder import approval_binding as AB                     # noqa: E402
from scripts.pettripfinder import hotel_exclusions as EX                     # noqa: E402
from scripts.pettripfinder import market_authority as MA                     # noqa: E402
from scripts.pettripfinder.acquisition import authority_build_036 as A36     # noqa: E402
from scripts.pettripfinder.acquisition import founder_decisions_040 as D40   # noqa: E402
from scripts.pettripfinder.acquisition import founder_review_036 as F36      # noqa: E402
from scripts.pettripfinder.acquisition import founder_review_039 as V39      # noqa: E402
from scripts.pettripfinder.contracts import enums                            # noqa: E402
from scripts.pettripfinder.contracts import policy_schema as SCHEMA          # noqa: E402
from scripts.pettripfinder.contracts import fee_computation                 # noqa: E402
from scripts.pettripfinder.policy_migration import evidence_hash, record_hash  # noqa: E402

WORK_ORDER = D40.WORK_ORDER
MARKET = A36.MARKET
AUTHORITY = A36.AUTHORITY
EXCLUSION_SHARD = A36.EXCLUSION_SHARD

REPORT = F36.REPORTS / "ptf_milwaukee_authority_build_040.json"

NEWLINE = chr(10)

VERIFIED_PET_FRIENDLY = "VERIFIED_PET_FRIENDLY"
VERIFIED_NO_PETS = "VERIFIED_NO_PETS"


class AuthorityError(RuntimeError):
    """Raised per record. One bad row never becomes a silently smaller file."""


def _sha(text: str) -> str:
    import hashlib
    return "sha256:%s" % hashlib.sha256(text.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# A candidate, in the shape everything downstream already understands.
# --------------------------------------------------------------------------- #

def _reader_evidence(candidate: Mapping) -> Tuple[List[Dict], List[str], Dict]:
    """The reader's own per-field citations over the candidate's own block.

    Re-read rather than stored: the 039 package carries the block and the
    facts, and the citations that tie one to the other are produced by the
    same reader that produced the facts. Recomputing them here would be a
    second implementation; asking the reader is one.
    """
    from scripts.pettripfinder.brightdata import policy_reading as PR
    from scripts.pettripfinder.brightdata import policy_locator as PL
    block = candidate["evidence_quote"]
    reading = PR.parse(block, strategy=WORK_ORDER)
    result = PR.to_extraction(reading, location=PL.BLOCK_ARTIFACT)
    return ([dict(item) for item in result.evidence],
            list(result.non_inferences),
            dict(result.withheld or {}))


#: A service-animal statement that begins above its own sentence. 039 flagged
#: these to the founder as an ambiguity; publishing the flagged text verbatim
#: would put another fact's words into the access statement a guest reads.
def _trim_service_animal_statement(statement: str) -> Tuple[str, str]:
    """(statement, note). Trims only a PREFIX, never a word of the sentence."""
    if not statement:
        return "", ""
    match = re.search(
        r"(?:only\s+)?(?:ADA\s+)?(?:certified\s+|trained\s+|registered\s+)?"
        r"(?:service|assistance|guide|support)\s+(?:animal|animals|dog|dogs)",
        statement, re.IGNORECASE)
    if not match or match.start() == 0:
        return statement, ""
    trimmed = statement[match.start():].strip()
    return trimmed, (
        "service-animal statement trimmed to its own sentence: the locator "
        "captured %r ahead of it, which belongs to another fact on the same "
        "line. Only a prefix was removed; the sentence itself is the source's "
        "words unchanged." % statement[:match.start()].strip())


def _observed_at(candidate: Mapping) -> Tuple[str, str]:
    """When this capture happened, on 025's own rule.

    None of these runs journalled a per-capture timestamp, so 025 already
    decided how to answer: the run report's completion time where one exists,
    the artifact's mtime otherwise, and the BASIS labelled either way. Deciding
    it a second time here would be a second answer to a settled question.
    """
    from scripts.pettripfinder.acquisition import store_integration_025 as S25
    from scripts.pettripfinder.brightdata import policy_locator as PL
    return S25.retrieved_at(candidate["run_id"],
                            REPO / candidate["attempt_dir"] / PL.BLOCK_ARTIFACT)


#: "Non-refundable Pet Charge 100.00 USD Per Stay". Schema 1.2's money node
#: accepts an optional ``refundable`` boolean and the reader does not emit one,
#: so the word would be dropped from a fee the source explicitly qualifies.
#:
#: Read from the SENTENCE THAT CARRIES THE FEE and nowhere else -- a
#: "non-refundable deposit" mentioned elsewhere on the page says nothing about
#: this charge. Silence stays silence: absent the word, the field is omitted
#: rather than defaulted, because "not stated" and "refundable" are different
#: claims and only one of them is the source's.
_NON_REFUNDABLE_RE = re.compile(r"\bnon[-\s]?refundable\b", re.IGNORECASE)
_REFUNDABLE_RE = re.compile(r"(?<!non[-\s])\brefundable\b", re.IGNORECASE)


def _sentence_around(block: str, quote: str) -> str:
    """The one sentence of ``block`` that contains ``quote``.

    Computed tightly rather than borrowed: 036's containing_sentence returns a
    wider window, and a window that spans three sentences would let a
    "non-refundable" belonging to a DEPOSIT qualify a pet FEE two clauses
    later. Bounded by the nearest terminator on each side.
    """
    if not block or not quote:
        return ""
    start = block.find(quote)
    if start < 0:
        return ""
    left = max((block.rfind(mark, 0, start) for mark in ".;!?"), default=-1)
    end = start + len(quote)
    right = min((pos for pos in (block.find(mark, end) for mark in ".;!?")
                 if pos != -1), default=len(block))
    return block[left + 1:right + 1].strip()


def _fee_refundability(row: Mapping, block: str) -> Tuple[Optional[bool], str]:
    """(refundable, sentence) as the fee's own sentence states it.

    Scoped to the SENTENCE, not the citation and not the block. The reader's
    citation for a fee starts at the amount -- "100.00 USD Per Stay" -- so the
    qualifier standing immediately before it ("Non-refundable Pet Charge") is
    outside the span while plainly being about that charge. The block is too
    wide in the other direction: a non-refundable DEPOSIT elsewhere on the page
    says nothing about this fee.
    """
    quote = A36._quotes_for(row, "pet_fee").strip()
    if not quote:
        return None, ""
    sentence = _sentence_around(block, quote) or quote
    if _NON_REFUNDABLE_RE.search(sentence):
        return False, sentence.strip()
    if _REFUNDABLE_RE.search(sentence):
        return True, sentence.strip()
    return None, ""


def semantic_row(candidate: Mapping) -> Dict:
    """A candidate as a record the binding contract and converter can read.

    Every key is one ``approval_binding`` classifies, so the projection cannot
    silently drop or admit anything: an unclassified field would raise.
    """
    evidence, non_inferences, withheld = _reader_evidence(candidate)
    facts = dict(candidate["proposed_publication_facts"] or {})
    census = F36.census_rows().get(candidate["identity_key"]) or {}
    block = candidate["evidence_quote"]
    stamp, basis = _observed_at(candidate)
    return OrderedDict([
        ("identity_key", candidate["identity_key"]),
        ("canonical_name", candidate["property_name"]),
        ("market_id", MARKET),
        ("brand", candidate["brand"]),
        ("policy_schema_version", enums.POLICY_SCHEMA_VERSION),
        ("proposed_facts", facts),
        ("withheld_fields", dict(candidate["withheld_fields"] or {})),
        ("non_inferences", non_inferences),
        ("evidence", evidence),
        ("service_animal_statement", ""),
        ("provenance", OrderedDict([
            ("source_url", candidate["source_url"]),
            ("final_url", candidate["source_url"]),
            ("authority_tier", "PT1"),
            ("source_type", "official_property_page"),
            ("retrieved_at", stamp),
            ("capture_method", "browser_assisted"),
            ("provider", ""),
            ("reader", "generic"),
            ("snapshot_hash", _sha(block)),
            ("raw_pointer", candidate["attempt_dir"]),
            ("obs_id", "%s::%s" % (candidate["run_id"],
                                   candidate["identity_key"])),
        ])),
        ("publication_grade", "PUBLICATION_GRADE_CONFIRMED"),
        ("identity_check", OrderedDict([
            ("name_on_page", candidate["property_name"]),
            ("address_on_page", census.get("address", "")),
            ("phone_on_page", ""),
        ])),
        ("source_run", candidate["run_id"]),
        ("review_status", candidate["status"]),
        ("frozen_semantics_violations", []),
        ("is_refusal", facts.get("pets_allowed") is False),
        ("published", False),
        ("founder_approved", False),
        ("rederivation", OrderedDict([
            ("superseded_by", WORK_ORDER),
            ("derivation", "the 039 founder-review candidate, read from the "
                           "block persisted by %s" % candidate["run_id"]),
            ("reader_commit", ""),
            ("evidence_block_path", candidate["attempt_dir"]),
            ("evidence_block_sha256", _sha(block)),
            ("previous_facts", {}),
            ("previous_withheld_fields", {}),
        ])),
    ])


def candidate_for(identity_key: str) -> Dict:
    package = D40.committed_package()
    for row in package["candidates"]:
        if row["identity_key"] == identity_key:
            return row
    raise AuthorityError("%s is not in the committed 039 package"
                         % identity_key)


# --------------------------------------------------------------------------- #
# The authority records.
# --------------------------------------------------------------------------- #

def authority_record(decision: Mapping) -> Dict:
    """One approved pet-friendly candidate as a schema-1.2 authority record."""
    candidate = candidate_for(decision["identity_key"])
    row = semantic_row(candidate)

    # The binding must still hold at application time. A candidate that has
    # moved since the founder answered is not the candidate they answered.
    if AB.semantic_hash(row) != decision["semantic_hash"]:
        raise AuthorityError(
            "the candidate has moved since the founder decided it (%s -> %s)"
            % (decision["semantic_hash"][:23], AB.semantic_hash(row)[:23]))

    facts, notes = A36.to_facts(row)
    refundable, refund_quote = _fee_refundability(
        row, candidate["evidence_quote"])
    if refundable is not None and isinstance(facts.get("pet_fee"), dict):
        facts["pet_fee"]["refundable"] = refundable
        notes.append(
            "pet_fee.refundable=%s read from the fee's own sentence (%r); the "
            "generic reader does not emit this field, so it is derived here "
            "from the quoted evidence and will not survive a store "
            "re-projection until the reader emits it"
            % (refundable, refund_quote[:80]))
    census = F36.census_rows().get(row["identity_key"]) or {}

    record: Dict = OrderedDict([
        ("key", row["identity_key"]),
        ("identity_key", row["identity_key"]),
        ("name", row["canonical_name"]),
        ("market_id", MARKET),
        ("schema_version", enums.POLICY_SCHEMA_VERSION),
        ("facts", facts),
    ])

    statement = A36.service_animal_statement(row)
    if statement:
        trimmed, note = _trim_service_animal_statement(statement["quote"])
        if note:
            statement = dict(statement, quote=trimmed)
            notes.append(note)
        record["service_animal_statement"] = statement

    record["computation_class"] = fee_computation.classify(
        facts).computation_class
    evidence = A36._evidence_entries(row, facts)
    record["evidence"] = evidence
    record["evidence_count"] = len(evidence)
    record["evidence_quote"] = re.sub(
        r"\s+", " ", (row.get("evidence") or [{}])[0].get("quote", "")).strip()
    record["source_url"] = row["provenance"]["source_url"]
    record["source_type"] = "EXACT_ENTITY_DOMAIN"
    record["verification_state"] = VERIFIED_PET_FRIENDLY
    record["verification_date"] = decision["decided_at"]
    # The capture time on 025's rule, not a blank: the publication layer
    # refuses a record with no observed_at rather than inventing one,
    # and leaving it empty here made three approved rows unpublishable.
    record["verified_at"] = row["provenance"]["retrieved_at"]
    record["address"] = census.get("address", "")
    record["city"] = census.get("city", "")
    record["state"] = census.get("state", "")
    record["postal_code"] = census.get("postal_code", "")

    issues = SCHEMA.validate_record(record)
    if issues:
        raise AuthorityError("schema 1.2: %s"
                             % "; ".join(str(issue) for issue in issues))
    disagreements = fee_computation.classification_disagreements(record)
    if disagreements:
        raise AuthorityError("; ".join(disagreements))

    record["approval"] = OrderedDict([
        ("decision", "APPROVED"),
        ("operator", decision["decided_by"]),
        ("approval_date", decision["decided_at"]),
        ("decision_source", OrderedDict([
            ("kind", "FOUNDER_DECISION"),
            ("work_order", WORK_ORDER),
            ("review_work_order", V39.WORK_ORDER),
            ("ledger", D40.LEDGER.name),
            ("candidate_package", V39.REVIEW_JSON.name),
            ("originating_work_order", decision["originating_work_order"]),
            ("decision_basis", decision["decision_basis"]),
            ("reason", decision["reason"]),
            ("decided_by", decision["decided_by"]),
            ("decided_at", decision["decided_at"]),
            ("evidence_origin", decision["evidence_origin"]),
            ("run_id", decision["run_id"]),
            ("run_kind", decision["run_kind"]),
        ])),
        # Both bindings recorded. The semantic one is what governs; the
        # record/evidence hashes stay so the file reads the same way as the
        # 036 half and so a reader of either era can check it.
        ("binding_contract", AB.BINDING_CONTRACT_VERSION),
        ("semantic_hash", AB.semantic_hash(row)),
        ("reviewed_semantic_hash", decision["semantic_hash"]),
        ("record_hash", record_hash(record)),
        ("evidence_hash", evidence_hash(evidence)),
        ("conversion_notes", notes),
    ])
    return record


def build_records() -> Tuple[List[Dict], List[Dict]]:
    """(admitted, refused) for 040's approvals. Fail closed, per record."""
    admitted: List[Dict] = []
    refused: List[Dict] = []
    for decision in D40.load_ledger()["decisions"]:
        if decision["decision"] != D40.APPROVE:
            continue
        try:
            admitted.append(authority_record(decision))
        except (AuthorityError, Exception) as exc:            # noqa: BLE001
            refused.append({"identity_key": decision["identity_key"],
                            "canonical_name": decision["canonical_name"],
                            "refusal_reason": str(exc)[:400]})
    return admitted, refused


# --------------------------------------------------------------------------- #
# The refusal.
# --------------------------------------------------------------------------- #

def exclusion_rows() -> Tuple[List[Dict], List[Dict]]:
    """040's approved refusals as registry rows, built with the registry's own
    functions -- a second implementation of a hash is a second answer."""
    rows: List[Dict] = []
    refused: List[Dict] = []
    for decision in D40.load_ledger()["decisions"]:
        if decision["decision"] != D40.APPROVE_REFUSAL:
            continue
        candidate = candidate_for(decision["identity_key"])
        row = semantic_row(candidate)
        facts = row["proposed_facts"]
        census = F36.census_rows().get(row["identity_key"]) or {}
        quote = A36._quotes_for(row, "pets_allowed").strip()
        if facts.get("pets_allowed") is not False or not quote:
            refused.append({"identity_key": row["identity_key"],
                            "refusal_reason": "no quoted refusal on the row"})
            continue
        if AB.semantic_hash(row) != decision["semantic_hash"]:
            refused.append({"identity_key": row["identity_key"],
                            "refusal_reason": "the candidate has moved since "
                                              "the founder decided it"})
            continue
        record = OrderedDict([
            ("exclusion_id", "mke-%s" % (census.get("slug")
                                         or row["identity_key"].replace(" ", "-"))),
            ("canonical_name", row["canonical_name"]),
            ("normalized_name", EX.normalize_name(row["canonical_name"])),
            ("address", census.get("address", "")),
            ("city", census.get("city", "")),
            ("state", census.get("state", "")),
            ("postal_code", census.get("postal_code", "")),
            ("official_url", census.get("official_url", "")
             or row["provenance"]["source_url"]),
            ("exclusion_state", VERIFIED_NO_PETS),
            ("evidence_quote", re.sub(r"\s+", " ", quote).strip()),
            # The whole statement, because three words are not a decision.
            ("evidence_context",
             re.sub(r"\s+", " ", candidate["evidence_quote"]).strip()[:400]),
            ("source_url", row["provenance"]["source_url"]),
            ("observed_at", (row["provenance"]["retrieved_at"] or "")[:10]),
            ("source_hash", row["provenance"]["snapshot_hash"]),
            ("reviewer_id", decision["decided_by"]),
            ("reviewed_at", decision["decided_at"]),
            ("notes", "affirmative refusal on the property's own page; "
                      "service-animal language is a legal access category and "
                      "is never read as a pet permission or as a refusal on "
                      "its own"),
            ("market_id", MARKET),
            ("decision_source", OrderedDict([
                ("work_order", WORK_ORDER),
                ("ledger", D40.LEDGER.name),
                ("review_work_order", V39.WORK_ORDER),
                ("decision_basis", decision["decision_basis"]),
                ("evidence_origin", decision["evidence_origin"]),
                ("run_id", decision["run_id"]),
                ("run_kind", decision["run_kind"]),
                ("binding_contract", AB.BINDING_CONTRACT_VERSION),
                ("semantic_hash", decision["semantic_hash"]),
            ])),
        ])
        record["record_hash"] = EX.record_hash(record)
        record["approval_hash"] = EX.approval_hash(record)

        missing = [field for field in EX.REQUIRED_FIELDS
                   if not str(record.get(field, "")).strip()]
        if missing:
            refused.append({"identity_key": row["identity_key"],
                            "refusal_reason": "the registry requires %s and "
                                              "this row states none"
                                              % ", ".join(missing)})
            continue
        if record["normalized_name"] != EX.normalize_name(
                record["canonical_name"]):
            refused.append({"identity_key": row["identity_key"],
                            "refusal_reason": "normalized_name does not "
                                              "derive from the canonical name"})
            continue
        rows.append(record)
    rows.sort(key=lambda item: item["exclusion_id"])
    return rows, refused


# --------------------------------------------------------------------------- #
# Documents.
# --------------------------------------------------------------------------- #

def authority_document() -> Dict:
    """036's records, untouched, plus 040's."""
    base = A36.authority_document()
    existing = list(base["hotels"])
    keys = {record["identity_key"] for record in existing}
    fresh, refused = build_records()
    duplicates = [record["identity_key"] for record in fresh
                  if record["identity_key"] in keys]
    if duplicates:
        raise AuthorityError("040 would re-admit rows 036 already holds: %s"
                             % duplicates)
    doc = OrderedDict(base)
    doc["hotels"] = existing + fresh
    doc["refused_records"] = list(base.get("refused_records") or ()) + refused
    doc["provenance"] = OrderedDict(base["provenance"])
    doc["provenance"]["founder_sittings"] = [
        OrderedDict([("work_order", A36.WORK_ORDER),
                     ("ledger", F36.LEDGER.name),
                     ("records", len(existing))]),
        OrderedDict([("work_order", WORK_ORDER),
                     ("ledger", D40.LEDGER.name),
                     ("review_work_order", V39.WORK_ORDER),
                     ("decided_by", D40.FOUNDER),
                     ("decided_at", D40.DECIDED_AT),
                     ("binding_contract", AB.BINDING_CONTRACT_VERSION),
                     ("records", len(fresh))]),
    ]
    return doc


def exclusions_document() -> Tuple[Dict, List[Dict], List[Dict]]:
    """Milwaukee's exclusion SHARD -- the only file a market may write."""
    shard = json.loads(EXCLUSION_SHARD.read_text(encoding="utf-8-sig"))
    existing = list(shard.get("exclusions") or ())
    keys = {row.get("normalized_name") for row in existing}
    added, refused = exclusion_rows()
    fresh = [row for row in added if row["normalized_name"] not in keys]
    shard["exclusions"] = existing + fresh
    shard["count"] = len(shard["exclusions"])
    return shard, fresh, refused


def write(apply: bool = False) -> Dict:
    authority = authority_document()
    shard, fresh, refused_exclusions = exclusions_document()
    registry = A36.assembled_registry(shard)
    _admitted, refused = build_records()
    generated = ""
    if apply:
        AUTHORITY.write_text(
            json.dumps(authority, indent=1, ensure_ascii=False) + NEWLINE,
            encoding="utf-8")
        EXCLUSION_SHARD.write_text(
            json.dumps(shard, indent=1, ensure_ascii=False) + NEWLINE,
            encoding="utf-8")
        # GENERATED from the shards, by their own builder. Writing a global
        # by hand is what the sharding work order forbids.
        from scripts.pettripfinder import build_global_authority as GLOBALS
        GLOBALS.main(["--write"])
        generated = "build_global_authority --write"
    return {
        "applied": apply,
        "authority_rows_total": len(authority["hotels"]),
        "authority_rows_added_by_040": len(authority["hotels"])
                                       - len(A36.authority_document()["hotels"]),
        "authority_refused": refused,
        "exclusion_shard_rows_added": len(fresh),
        "exclusion_shard_total": len(shard["exclusions"]),
        "exclusion_rows_refused": refused_exclusions,
        "registry_total_after_assembly": len(registry["exclusions"]),
        "globals_regenerated_by": generated,
        "published": authority["published"],
    }


def counters() -> Dict:
    doc = authority_document()
    shard, _fresh, _refused = exclusions_document()
    return {
        "pet_friendly": len(doc["hotels"]),
        "verified_no_pets": len(shard["exclusions"]),
        "total_founder_decided_authority": len(doc["hotels"])
                                           + len(shard["exclusions"]),
        "held_from_039": sum(1 for row in D40.load_ledger()["decisions"]
                             if row["decision"] == D40.HOLD),
        "by_040_decision": dict(Counter(
            row["decision"] for row in D40.load_ledger()["decisions"])),
        "published": doc["published"],
    }


def build_report() -> Dict:
    from scripts.pettripfinder.acquisition import closure_038 as C38
    from scripts.pettripfinder.acquisition import publication_037 as P37
    ledger = D40.load_ledger()
    return OrderedDict([
        ("schema", "ptf-milwaukee-authority-build/2.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET),
        ("decided_by", D40.FOUNDER),
        ("decided_at", D40.DECIDED_AT),
        ("binding_contract", AB.BINDING_CONTRACT_VERSION),
        ("decisions", [OrderedDict([
            ("canonical_name", row["canonical_name"]),
            ("decision", row["decision"]),
            ("semantic_hash", row["semantic_hash"]),
        ]) for row in ledger["decisions"]]),
        ("counters", counters()),
        ("closure", C38.reconciliation()),
        ("held_after_040", list(P37.held_identities())),
        ("provider_calls", 0),
        ("cost_usd", 0.0),
        ("published", 0),
        ("deployed", 0),
        ("carried_debt", OrderedDict([
            ("stale_prepared_release_contract",
             "037's prepared release contract pins the sha256 of the "
             "authority as it stood at 70 records. 040 admitted four more, so "
             "the pin is stale by construction. It was never applied and is "
             "not in the live directory; the publication work order that runs "
             "next must re-prepare it rather than inherit a number calibrated "
             "to a market that no longer exists."),
            ("pending_store_projection",
             "038's register still stands: the store and the reader disagree "
             "on one row, and re-projecting is a founder-facing question "
             "rather than a build step. 040 changed nothing about it."),
        ])),
    ])


def write_report() -> Dict:
    doc = build_report()
    REPORT.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + NEWLINE,
                      encoding="utf-8")
    return doc


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=WORK_ORDER)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--counters", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args(argv)
    if args.check:
        print(json.dumps(write(apply=False), indent=2, default=str))
    if args.counters:
        print(json.dumps(counters(), indent=2, default=str))
    if args.apply:
        print(json.dumps(write(apply=True), indent=2, default=str))
    if args.report:
        print(json.dumps(write_report()["counters"], indent=2, default=str))
    return 0


if __name__ == "__main__":                                  # pragma: no cover
    raise SystemExit(main())
