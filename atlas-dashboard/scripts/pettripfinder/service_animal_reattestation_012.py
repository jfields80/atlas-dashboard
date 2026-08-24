"""PTF-MILWAUKEE-SERVICE-ANIMAL-REAUTHORIZE-012 -- the founder signs the fix.

PTF-...-CORRECTION-011 corrected four LIVE Milwaukee profiles that published
"service animals are welcome and that a charge applies" over sources saying
the opposite. It changed each record's final ``record_hash``, and founder
ruling GOV-01 (``contracts/evidence.py``) says that is precisely what requires
re-attestation. 011 stopped there and flagged it. This records the founder's
answer and applies it.

WHAT IS BEING SIGNED, AND WHAT IS NOT
--------------------------------------
Not a new claim about a hotel. The evidence did not move, the quote did not
move, and no pet-policy fact moved -- the guard below proves all three against
the pre-011 committed package before a byte is written. What moved is the
DERIVED INTERPRETATION of a sentence the founder had already read, from an
interpretation the source does not support to the one it does.

So the attestation is narrow on purpose and says so in the record: the founder
accepts the corrected final record, and the corrected ``record_hash``
supersedes the prior one for publication.

THE EARLIER APPROVAL IS PRESERVED, NEVER OVERWRITTEN
-----------------------------------------------------
Dayton's precedent (``dayton_pass_c_decision_application``) is followed
exactly: the prior approval is copied verbatim into ``approval.supersedes``
with the hashes it described, and a caveat says what it was and why it no
longer binds. Nothing pretends the 036 approval never happened -- it did, it
was honest, and it approved a record whose derived field was wrong.

``reviewed_record_hash`` / ``reviewed_evidence_hash`` are KEPT rather than
replaced. They bind the founder's ORIGINAL review to the acquisition store row
the founder actually read, that row has not moved, and
``publication_042.validate_pet_friendly`` binds a 036-era approval through
exactly those two fields. Dropping them would break the publication gate and
would delete the only link between the decision and the row it was about.

ATTRIBUTION
-----------
``decided_by`` is the founder because the founder gave this decision
explicitly and in writing, in the work order quoted verbatim in
``authorization_source`` below. That is the only circumstance in which their
name may appear on a decision. This module records the four decisions it was
given, refuses to write if any record has moved since, and can never reach a
fifth record: the table is literal and the guard counts it.

Run:
  python -m scripts.pettripfinder.service_animal_reattestation_012 --check
  python -m scripts.pettripfinder.service_animal_reattestation_012 --apply
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder import service_animal_correction_011 as C11       # noqa: E402
from scripts.pettripfinder.contracts import enums                            # noqa: E402
from scripts.pettripfinder.contracts import founder_approval as FA           # noqa: E402
from scripts.pettripfinder.contracts import policy_schema as SCHEMA          # noqa: E402
from scripts.pettripfinder.contracts import service_animal as SA             # noqa: E402
from scripts.pettripfinder.dayton_pass_b_founder_decisions import APPROVE    # noqa: E402
from scripts.pettripfinder.policy_migration import evidence_hash, record_hash  # noqa: E402

WORK_ORDER = "PTF-MILWAUKEE-SERVICE-ANIMAL-REAUTHORIZE-012"
MARKET = "milwaukee-wi"
FOUNDER = "jfields80"
DECIDED_AT = "2026-08-24"

#: The commit whose tree holds the package as the founder approved it in 036 --
#: before 011 touched a byte. Every "nothing else moved" claim below is checked
#: against THIS, not against a description of it.
PRE_CORRECTION_COMMIT = "cb550e7"

LP = REPO / "launch_packages" / "pettripfinder"
FACTS_PATH = LP / ("hotel_policy_facts_%s.json" % MARKET)
LEDGER_PATH = LP / "milwaukee_service_animal_reattestation_012.json"
REPORT_PATH = (LP / "service_animal_correction_011"
               / "service-animal-reattestation-012.json")

LF = chr(10)

#: The founder's authorization, quoted from the work order rather than
#: summarised. A decision recorded in someone's name must carry the words they
#: actually used, or the record is the recorder's opinion of them.
AUTHORIZATION_SOURCE = (
    "Work order PTF-MILWAUKEE-SERVICE-ANIMAL-REAUTHORIZE-012 (2026-08-24): "
    "'This prompt explicitly authorizes founder re-attestation of the four "
    "corrected records ONLY. Use the existing canonical founder: "
    "founder_reviewer_id / operator: jfields80. Preserve the original "
    "historical approval and record this as a later re-attestation to the "
    "corrected final record hash. Do not rewrite historical evidence or "
    "pretend the earlier approval never existed. Sign ONLY: 1. avid hotels "
    "oak creek 2. extended stay america milwaukee waukesha 3. extended stay "
    "america milwaukee wauwatosa 4. the pfister hotel. No other record may "
    "receive a new attestation.'")

#: What the founder is attesting to, stated as the work order required it to
#: be stated. Written onto every signed record as caveats, so a reader of the
#: record never has to find the ledger to learn what the signature covered.
ATTESTATION_TERMS: Tuple[str, ...] = (
    "The source evidence did not change: same source_url, same captured "
    "artifact, same evidence entries, same evidence_hash.",
    "The hotel policy facts did not change: no pet fee, weight limit, pet "
    "count, species, deposit, breed rule or any other fact moved.",
    "The derived service-animal interpretation was corrected: "
    "service_animal_statement.charges_stated moved from charge_stated to "
    "no_charge, because the property's own sentence states an exemption and "
    "the previous reading came from a token match on the word fee/charge.",
    "The founder reviewed and accepts the corrected final record.",
    "The corrected record_hash supersedes the prior final record_hash for "
    "publication.",
)

#: The ledger decision vocabulary, read from the module that established it
#: rather than retyped. PTF-DAYTON-RECERTIFICATION-001 Pass B approved exactly
#: this class of change under this word -- DAY-B07 and DAY-B08 are
#: service_animal_statement.charges_stated corrections, and DAY-B08's source
#: sentence is the SAME sentence as MKE-SA-02 and MKE-SA-03 below.
LEDGER_DECISION = APPROVE

#: The state a signed record carries. Canonical spelling, guarded on write.
RECORD_STATE = FA.CANONICAL_APPROVED

#: The four decisions the founder gave, exactly as given. Literal, so this
#: module cannot reach a fifth record however it is called.
DECISIONS: Tuple[Tuple[str, str], ...] = (
    ("MKE-SA-01", "avid hotels oak creek"),
    ("MKE-SA-02", "extended stay america milwaukee waukesha"),
    ("MKE-SA-03", "extended stay america milwaukee wauwatosa"),
    ("MKE-SA-04", "the pfister hotel"),
)

SIGNED_IDENTITIES: Tuple[str, ...] = tuple(key for _id, key in DECISIONS)


class ReattestationError(RuntimeError):
    """The attestation cannot be recorded or applied, and nothing is guessed."""


# --------------------------------------------------------------------------- #
# Reading both sides.
# --------------------------------------------------------------------------- #

def _git(*args: str) -> str:
    import subprocess
    out = subprocess.run(("git",) + args, capture_output=True,
                         cwd=str(REPO.parent))
    if out.returncode != 0:
        raise ReattestationError("git %s failed: %s"
                                 % (" ".join(args), out.stderr.decode("utf-8", "replace")))
    return out.stdout.decode("utf-8")


def pre_correction_records() -> Dict[str, Dict]:
    """The Milwaukee package as the founder approved it, read from git."""
    rel = FACTS_PATH.relative_to(REPO.parent).as_posix()
    doc = json.loads(_git("show", "%s:%s" % (PRE_CORRECTION_COMMIT, rel)))
    return {row["identity_key"]: row for row in doc["hotels"]}


def live_records() -> Dict[str, Dict]:
    doc = json.loads(FACTS_PATH.read_text(encoding="utf-8-sig"))
    return {row["identity_key"]: row for row in doc["hotels"]}


def _stable(value) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)


# --------------------------------------------------------------------------- #
# The guard. Nothing is signed until every one of these holds.
# --------------------------------------------------------------------------- #

def verify_one(identity: str, before: Mapping, after: Mapping) -> Dict:
    """Everything that must be true before this record may be signed."""
    sb = before.get("service_animal_statement") or {}
    sa = after.get("service_animal_statement") or {}
    ab = before.get("approval") or {}
    aa = after.get("approval") or {}

    substance_before = {k: v for k, v in before.items() if k != "approval"}
    substance_after = {k: v for k, v in after.items() if k != "approval"}
    substance_before.pop("service_animal_statement", None)
    substance_after.pop("service_animal_statement", None)

    statement_keys_moved = sorted(k for k in set(sb) | set(sa)
                                  if sb.get(k) != sa.get(k))
    reading = SA.classify(str(sa.get("quote") or ""))

    checks = OrderedDict([
        ("record_is_one_of_the_four", identity in SIGNED_IDENTITIES),
        ("everything_but_the_statement_is_identical",
         _stable(substance_before) == _stable(substance_after)),
        ("only_charges_stated_moved", statement_keys_moved == ["charges_stated"]),
        ("quote_unchanged", sb.get("quote") == sa.get("quote")),
        ("facts_unchanged", _stable(before.get("facts")) == _stable(after.get("facts"))),
        ("evidence_unchanged",
         _stable(before.get("evidence")) == _stable(after.get("evidence"))),
        ("evidence_hash_unchanged",
         ab.get("evidence_hash") == aa.get("evidence_hash")),
        ("evidence_hash_recomputes",
         evidence_hash(after.get("evidence") or []) == aa.get("evidence_hash")),
        ("reviewed_hashes_unchanged",
         ab.get("reviewed_record_hash") == aa.get("reviewed_record_hash")
         and ab.get("reviewed_evidence_hash") == aa.get("reviewed_evidence_hash")),
        ("prior_decision_is_an_approval",
         FA.is_publishable(ab.get("decision"))),
        ("prior_operator_is_the_founder", ab.get("operator") == FOUNDER),
        ("corrected_value_is_no_charge",
         sa.get("charges_stated") == enums.SERVICE_ANIMAL_NO_CHARGE),
        ("prior_value_was_charge_stated",
         sb.get("charges_stated") == enums.SERVICE_ANIMAL_CHARGE_STATED),
        ("source_states_an_exemption",
         reading.interpretation == SA.EXEMPT_FROM_PET_CHARGE),
        ("record_hash_recomputes", record_hash(after) == aa.get("record_hash")),
        ("record_hash_actually_moved",
         ab.get("record_hash") != aa.get("record_hash")),
        ("record_validates_under_schema",
         list(SCHEMA.validate_record(after)) == []),
        ("not_already_reattested",
         (aa.get("decision_source") or {}).get("work_order") != WORK_ORDER),
    ])
    return OrderedDict([
        ("identity_key", identity),
        ("name", after.get("name")),
        ("source_url", after.get("source_url")),
        ("quote", sa.get("quote")),
        ("interpretation", reading.interpretation),
        ("interpretation_reason", reading.reason),
        ("prior_record_hash", ab.get("record_hash")),
        ("target_record_hash", aa.get("record_hash")),
        ("evidence_hash", aa.get("evidence_hash")),
        ("prior_charges_stated", sb.get("charges_stated")),
        ("corrected_charges_stated", sa.get("charges_stated")),
        ("rendered_before", C11.rendered_copy(before, sb.get("charges_stated"))),
        ("rendered_after", C11.rendered_copy(after, sa.get("charges_stated"))),
        ("checks", checks),
        ("all_checks_pass", all(checks.values())),
    ])


def verify() -> Dict:
    """The whole market, not only the four: scope is proven, not asserted."""
    before, after = pre_correction_records(), live_records()
    if set(before) != set(after):
        raise ReattestationError("the Milwaukee identity set moved since %s"
                                 % PRE_CORRECTION_COMMIT)

    moved = sorted(k for k in before
                   if _stable({x: v for x, v in before[k].items() if x != "approval"})
                   != _stable({x: v for x, v in after[k].items() if x != "approval"}))
    unsigned_that_moved = [k for k in moved if k not in SIGNED_IDENTITIES]
    rows = [verify_one(key, before[key], after[key]) for key in SIGNED_IDENTITIES]

    return OrderedDict([
        ("market_id", MARKET),
        ("pre_correction_commit", PRE_CORRECTION_COMMIT),
        ("records_in_market", len(after)),
        ("records_whose_substance_moved", moved),
        ("records_outside_the_signed_four_that_moved", unsigned_that_moved),
        ("scope_is_exactly_the_four",
         moved == sorted(SIGNED_IDENTITIES) and not unsigned_that_moved),
        ("rows", rows),
        ("all_rows_pass", all(row["all_checks_pass"] for row in rows)),
    ])


def assert_verified() -> Dict:
    report = verify()
    problems: List[str] = []
    if not report["scope_is_exactly_the_four"]:
        problems.append(
            "records moved outside the four the founder signed: %s"
            % report["records_outside_the_signed_four_that_moved"])
    for row in report["rows"]:
        failed = [name for name, ok in row["checks"].items() if not ok]
        if failed:
            problems.append("%s: %s" % (row["identity_key"], ", ".join(failed)))
    if problems:
        raise ReattestationError(
            "nothing is signed while any of these hold: %s" % "; ".join(problems))
    return report


# --------------------------------------------------------------------------- #
# The ledger -- the founder's answer, in its own file.
# --------------------------------------------------------------------------- #

def build_ledger(report: Optional[Mapping] = None) -> Dict:
    report = report or assert_verified()
    rows = {row["identity_key"]: row for row in report["rows"]}
    decisions = []
    for decision_id, identity in DECISIONS:
        row = rows[identity]
        decisions.append(OrderedDict([
            ("decision_id", decision_id),
            ("identity_key", identity),
            ("name", row["name"]),
            ("decision", LEDGER_DECISION),
            ("decided_by", FOUNDER),
            ("decided_at", DECIDED_AT),
            ("source_url", row["source_url"]),
            ("source_quote", row["quote"]),
            ("field_corrected", "service_animal_statement.charges_stated"),
            ("prior_value", row["prior_charges_stated"]),
            ("approved_value", row["corrected_charges_stated"]),
            ("rendered_before", row["rendered_before"]),
            ("rendered_after", row["rendered_after"]),
            ("prior_record_hash", row["prior_record_hash"]),
            ("target_record_hash", row["target_record_hash"]),
            ("evidence_hash", row["evidence_hash"]),
        ]))
    return OrderedDict([
        ("schema", "ptf-milwaukee-service-animal-reattestation/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET),
        ("what_this_is",
         "The founder's re-attestation of the four records "
         "PTF-MILWAUKEE-SERVICE-ANIMAL-CORRECTION-011 corrected. It records a "
         "decision; the application order writes it onto the authority. The "
         "earlier 036 approval is preserved on every record under "
         "approval.supersedes and is not rewritten."),
        ("governance",
         ["GOV-01 applies: these four records require founder re-attestation "
          "because their final record_hash changed.",
          "The evidence, the quote and every pet-policy fact are unchanged, "
          "and that is verified against the committed package at %s per "
          "record before anything is signed." % PRE_CORRECTION_COMMIT,
          "Exactly four records may be signed. The identity list is literal "
          "in the module and the verifier refuses if any fifth Milwaukee "
          "record has moved.",
          "This is not a licence to batch-approve. It is one homogeneous "
          "class of change -- a derived interpretation corrected over "
          "unchanged evidence -- enumerated record by record."]),
        ("decided_by", FOUNDER),
        ("decided_at", DECIDED_AT),
        ("authorization_source", AUTHORIZATION_SOURCE),
        ("recorded_by",
         "claude-opus-5 (agent) -- transcription and verification only; the "
         "decision is the founder's, given in the work order quoted above."),
        ("attestation_terms", list(ATTESTATION_TERMS)),
        ("supersedes_work_order", "PTF-MILWAUKEE-FOUNDER-DECISION-036"),
        ("applied_to_authority", False),
        ("decisions", decisions),
    ])


def write_ledger(apply: bool = False) -> Dict:
    doc = build_ledger()
    if apply:
        LEDGER_PATH.write_text(
            json.dumps(doc, indent=1, ensure_ascii=False) + LF,
            encoding="utf-8", newline=LF)
    return doc


def load_ledger() -> Dict:
    if not LEDGER_PATH.is_file():
        raise ReattestationError(
            "no founder ledger at %s; a decision is recorded before it is "
            "applied" % LEDGER_PATH.relative_to(REPO).as_posix())
    return json.loads(LEDGER_PATH.read_text(encoding="utf-8-sig"))


# --------------------------------------------------------------------------- #
# Applying it to the authority.
# --------------------------------------------------------------------------- #

def signed_approval(record: Mapping, decision_row: Mapping) -> Dict:
    """The re-attested approval block, on Dayton's committed shape."""
    prior = dict(record.get("approval") or {})
    FA.assert_writable(RECORD_STATE, where=WORK_ORDER)

    # ``record_hash`` comes from the LEDGER, not from the block on disk. 011
    # recomputed ``approval.record_hash`` in place when it corrected the
    # record, so the block currently carries the CORRECTED hash -- copying it
    # here would record the 036 approval as having described a record it never
    # saw. The ledger's ``prior_record_hash`` is read from the committed
    # package at PRE_CORRECTION_COMMIT and is the hash that approval actually
    # covered.
    supersedes = OrderedDict([
        ("decision", prior.get("decision")),
        ("operator", prior.get("operator")),
        ("approval_date", prior.get("approval_date")),
        ("record_hash", decision_row["prior_record_hash"]),
        ("evidence_hash", prior.get("evidence_hash")),
        ("decision_source", prior.get("decision_source")),
        ("note",
         "The hash above is the record_hash this approval described in the "
         "committed package at %s. PTF-...-CORRECTION-011 recomputed the live "
         "approval.record_hash in place when it corrected the record; this "
         "restores what the 036 approval was actually about."
         % PRE_CORRECTION_COMMIT),
    ])
    caveats = [
        "%s. The founder re-attested this record after "
        "PTF-MILWAUKEE-SERVICE-ANIMAL-CORRECTION-011 corrected its derived "
        "service-animal interpretation. GOV-01 applies: the correction moved "
        "the final record_hash, so the earlier approval no longer bound this "
        "record and a new one was required." % WORK_ORDER,
        "The approval under 'supersedes' is the founder's own 036 attestation, "
        "preserved verbatim. It described this record before the correction "
        "and no longer binds it; it is history, not a mistake.",
    ]
    caveats.extend(ATTESTATION_TERMS)

    out = OrderedDict([
        ("decision", RECORD_STATE),
        ("operator", FOUNDER),
        ("approval_date", DECIDED_AT),
        ("decision_source", OrderedDict([
            ("kind", "POLICY_DECISION"),
            ("decision_id", decision_row["decision_id"]),
            ("work_order", WORK_ORDER),
            ("decided_by", FOUNDER),
            ("decided_at", DECIDED_AT),
            ("ledger", LEDGER_PATH.name),
        ])),
        ("supersedes", supersedes),
        ("caveats", caveats),
        ("record_hash", decision_row["target_record_hash"]),
        ("evidence_hash", decision_row["evidence_hash"]),
        # KEPT, not replaced: these bind the founder's ORIGINAL review to the
        # acquisition store row, which has not moved, and
        # publication_042.validate_pet_friendly binds a 036-era approval
        # through exactly these two fields.
        ("reviewed_record_hash", prior.get("reviewed_record_hash")),
        ("reviewed_evidence_hash", prior.get("reviewed_evidence_hash")),
        ("conversion_notes", list(prior.get("conversion_notes") or []) + [
            "%s: founder re-attestation recorded in %s (%s, %s). Evidence, "
            "quote and every pet-policy fact unchanged; only the derived "
            "service-animal interpretation was corrected. record_hash %s "
            "supersedes %s for publication."
            % (WORK_ORDER, LEDGER_PATH.name, FOUNDER, DECIDED_AT,
               decision_row["target_record_hash"],
               decision_row["prior_record_hash"])]),
    ])
    return out


def apply_to_authority(apply: bool = False) -> Dict:
    """Write the four signed approvals, and prove they were the only change."""
    report = assert_verified()
    ledger = load_ledger()
    if ledger["decided_by"] != FOUNDER or ledger["work_order"] != WORK_ORDER:
        raise ReattestationError("the committed ledger is not this work order's")
    if _stable(ledger["decisions"]) != _stable(build_ledger(report)["decisions"]):
        raise ReattestationError(
            "the committed ledger no longer describes the live records; a "
            "decision recorded against a record that has since moved is not a "
            "decision about that record")

    rows = {row["decision_id"]: row for row in ledger["decisions"]}
    doc = json.loads(FACTS_PATH.read_text(encoding="utf-8-sig"))
    envelope_before = _stable({k: v for k, v in doc.items() if k != "hotels"})
    index = {row["identity_key"]: row for row in doc["hotels"]}

    signed = []
    for decision_id, identity in DECISIONS:
        record = index[identity]
        before_material = _stable({k: v for k, v in record.items() if k != "approval"})
        record["approval"] = signed_approval(record, rows[decision_id])
        if _stable({k: v for k, v in record.items() if k != "approval"}) != before_material:
            raise ReattestationError(
                "%s: signing changed the record it signs" % identity)
        if record_hash(record) != rows[decision_id]["target_record_hash"]:
            raise ReattestationError(
                "%s: record_hash is not the hash the founder signed" % identity)
        if list(SCHEMA.validate_record(record)) != []:
            raise ReattestationError("%s: no longer validates" % identity)
        signed.append(identity)

    for identity, record in index.items():
        if identity in SIGNED_IDENTITIES:
            continue
        source = (record.get("approval") or {}).get("decision_source") or {}
        if source.get("work_order") == WORK_ORDER:
            raise ReattestationError(
                "%s carries this work order's attestation and was never "
                "signed" % identity)

    if _stable({k: v for k, v in doc.items() if k != "hotels"}) != envelope_before:
        raise ReattestationError("the package envelope moved")
    if len(doc["hotels"]) != len(index):
        raise ReattestationError("the record count moved")

    text = json.dumps(doc, indent=1, ensure_ascii=False) + LF
    result = OrderedDict([
        ("signed", signed),
        ("signed_count", len(signed)),
        ("other_records_signed", 0),
        ("package_sha256_before", C11._package_sha256(FACTS_PATH.read_bytes())),
        ("package_sha256_after", C11._package_sha256(text.encode("utf-8"))),
    ])
    if apply:
        FACTS_PATH.write_text(text, encoding="utf-8", newline=LF)
        doc2 = dict(load_ledger(), applied_to_authority=True)
        LEDGER_PATH.write_text(
            json.dumps(doc2, indent=1, ensure_ascii=False) + LF,
            encoding="utf-8", newline=LF)
    result["written"] = bool(apply)
    return result


def restamp_contract(apply: bool = False) -> Dict:
    """Re-pin the release contract's package digest. Nothing else moves."""
    return C11.restamp_contract(MARKET, apply=apply)


# --------------------------------------------------------------------------- #
# Reporting.
# --------------------------------------------------------------------------- #

def report(applied: Optional[Mapping] = None,
           contract: Optional[Mapping] = None) -> Dict:
    verification = verify()
    return OrderedDict([
        ("schema", "ptf-milwaukee-service-animal-reattestation-report/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET),
        ("ledger", LEDGER_PATH.relative_to(REPO).as_posix()),
        ("ledger_applied", load_ledger().get("applied_to_authority")
         if LEDGER_PATH.is_file() else None),
        ("verification", verification),
        ("application", applied),
        ("release_contract", contract),
    ])


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=WORK_ORDER)
    parser.add_argument("--check", action="store_true",
                        help="verify the four records; write nothing")
    parser.add_argument("--apply", action="store_true",
                        help="write the ledger, sign the four records, and "
                             "re-pin the release contract")
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args(argv)

    verification = assert_verified()
    if args.check:
        print(json.dumps(verification, indent=2, ensure_ascii=False))
        return 0

    write_ledger(apply=args.apply)
    applied = apply_to_authority(apply=args.apply)
    contract = restamp_contract(apply=args.apply)
    doc = report(applied=applied, contract=contract)
    if args.report:
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        REPORT_PATH.write_text(
            json.dumps(doc, indent=2, ensure_ascii=False) + LF,
            encoding="utf-8", newline=LF)
    print(json.dumps({k: v for k, v in doc.items() if k != "verification"},
                     indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":                            # pragma: no cover
    raise SystemExit(main())
