"""PTF-CINCINNATI-HARDENED-SYNC-002 Phase 5 -- Cincinnati's policy package to 1.3.

    python -m scripts.pettripfinder.cincinnati_schema_13_migration_002
    python -m scripts.pettripfinder.cincinnati_schema_13_migration_002 --write

WHAT 1.3 IS
-----------
Purely additive over 1.2, and ``enums.CANONICAL_POLICY_SCHEMA_VERSIONS`` holds
both: the amendment added two optional fields and removed nothing, so a 1.2
package is not malformed and this is not a repair. Cincinnati's package
validates with zero issues at 1.2 before this runs and zero after.

One of the two added fields is the reason to run it. Seven Cincinnati records
ALREADY carry ``service_animal_statement`` with ``stated`` and
``charges_stated``; what they lack is the 1.3 addition, ``quote``. Founder
Decision 2 of PTF-ST-LOUIS-PUBLICATION-SCHEMA-DECISIONS-010 required that a
verified service-animal statement not be dropped and that it be sourced from
explicit quoted property evidence -- "``stated`` and ``charges_stated`` alone
cannot carry the sentence, so the quote had nowhere to live." Cincinnati's seven
sentences were captured 2026-08-17, are quoted in each record's own evidence
array, and were explicitly ruled on by the founder at review time:

  * HomeTowne Studios (Batch B) carries the statement in ``approved_facts``
    verbatim, narrowed by the founder from the proposal's "exempt, always
    welcome, not counted as pets" to only what the source supports.
  * Baymont Lawrenceburg and Days Inn Cincinnati North (Batch C) each record
    ``charge state ... not_addressed`` in the founder's own restriction notes.
  * The four Red Roof rows (Batch B) record "Service/ESA statement preserved
    separately as source-supported text".

So nothing here is a new claim. The founder approved these sentences in August;
the schema simply had no field to publish the words in.

CHARGE SEMANTICS ARE VERIFIED, NEVER INVENTED
----------------------------------------------
This run does not decide ``charges_stated`` -- the founder already did, and all
seven records already say ``not_addressed``. What it does is CHECK that value
against ``contracts.service_animal.classify``, the classifier
PTF-MILWAUKEE-SERVICE-ANIMAL-CORRECTION-011 wrote after four LIVE profiles
published "a charge applies" from sources that said the opposite. The run
REFUSES to write unless every one of the seven quotes independently reads
ALLOWED, whose wire value is ``not_addressed``, and unless that agrees with the
value already committed. Acceptance is stated; a charge is not; silence about a
fee stays silence. A disagreement would be a founder question and would stop
the run rather than be resolved here.

PATCH, NEVER REBUILD
--------------------
Each record is deep-copied and exactly three things may change: the record's
``schema_version``, the ``quote`` inside an existing ``service_animal_statement``,
and the ``record_hash`` inside the approval block. Facts, evidence, withholding,
computation class, verification state, the founder's decision, and the
``stated`` / ``charges_stated`` the founder already wrote are all asserted
byte-identical afterwards. Any other movement aborts the run.

THE APPROVAL BINDING: REBOUND, NOT RE-ASKED
--------------------------------------------
``record_hash`` is a sha256 over the whole record minus its approval, so
stamping a version moves it. That is the binding doing its job, and it leaves
two bad options and one good one:

  * leave the old hash -- all twenty-one approvals silently stop binding, which
    is PTF-MILWAUKEE-FULL-CLOSURE-038's defect exactly: fifteen of sixteen
    withdrawn approvals had no substantive change at all; or
  * recompute it silently -- that is signing in the founder's name, which
    PTF-PHASE-F is the standing reason never to do; or
  * recompute it and SAY SO, which is what ``approval_binding`` /
    PTF-...-APPROVAL-BINDING-039 established: rebind, record the old and new
    hash and the reason, and never let a rebinding pass for an approval.

This module takes the third. Every approval gains a ``rebinding`` block naming
the work order, the prior hash, and what moved. That block lives INSIDE
``approval`` for a mechanical reason worth stating: ``record_hash`` is taken
over the record minus its approval, so a note stored anywhere else on the
record would be hashed into the very value it reports, and the committed hash
would no longer be reproducible by ``policy_migration.record_hash`` -- the one
function a later reader will check it with. ``evidence_hash`` is asserted
UNCHANGED: the evidence a founder approved is not touched here, and if that
hash ever moves, this run aborts rather than rebinding.

WHAT IT WILL NOT DO
-------------------
It does not change a founder decision, add a fact, re-fetch a page, alter a
quote, or touch the reshaped envelope. Two of the seven approved quotes are
condensations rather than verbatim spans of the captured artifact; they are
published as the FOUNDER approved them and reported, never silently rewritten
to this module's preference.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import policy_migration as PM          # noqa: E402
from scripts.pettripfinder.contracts import enums                 # noqa: E402
from scripts.pettripfinder.contracts import service_animal as SA  # noqa: E402

WORK_ORDER = "PTF-CINCINNATI-HARDENED-SYNC-002"
MARKET_ID = "cincinnati-oh"
PACKAGE = (_REPO_ROOT / "launch_packages" / "pettripfinder"
           / "hotel_policy_facts_cincinnati-oh.json")

SA_FIELD = "service_animal_statement"

#: The only interpretation this run will publish. A quote that reads as an
#: exemption or as an explicit charge is a DIFFERENT founder question and stops
#: the run rather than being published under a decision nobody made.
REQUIRED_READING = SA.ALLOWED

#: Fields whose bytes must be identical before and after. The migration owns
#: three things; everything else is somebody else's authority.
FROZEN = ("key", "identity_key", "name", "market_id", "facts", "evidence",
          "evidence_count", "evidence_quote", "source_url", "source_type",
          "verification_state", "verification_date", "verified_at",
          "computation_class", "withheld_fields")


class MigrationError(RuntimeError):
    pass


def _statement_evidence(record: Mapping) -> str:
    """The founder-approved quote for this record's service-animal statement.

    Read from the record's OWN evidence array, so a record with no such entry
    gets no statement. The quote is never composed, and never taken from the
    roll-up ``evidence_quote``, which concatenates fields.
    """
    for entry in record.get("evidence") or ():
        if entry.get("field") == SA_FIELD:
            return str(entry.get("quote") or "").strip()
    return ""


def quoted_statement(existing: Mapping, quote: str) -> "OrderedDict":
    """The committed statement, plus the 1.3 quote, having agreed on the rest.

    ``stated`` and ``charges_stated`` are the founder's and are carried over
    untouched. The classifier is run as a CHECK against them, so a source whose
    words disagree with the committed charge state stops the run instead of
    being published under a reading nobody made.
    """
    reading = SA.classify(quote)
    if reading.interpretation != REQUIRED_READING:
        raise MigrationError(
            "%r reads as %s (%s), not %s -- that is a founder question, not a "
            "migration" % (quote, reading.interpretation, reading.reason,
                           REQUIRED_READING))
    committed = existing.get("charges_stated")
    if committed != reading.charges_stated:
        raise MigrationError(
            "committed charges_stated %r disagrees with the classifier's %r "
            "for %r -- the founder and the source must be reconciled by a "
            "person, not by a schema stamp"
            % (committed, reading.charges_stated, quote))
    if not enums.is_member(committed, enums.SERVICE_ANIMAL_CHARGE_STATES):
        raise MigrationError("%r is not a charge state" % committed)
    if existing.get("stated") is not True:
        raise MigrationError("%r carries a quote but stated is %r"
                             % (quote, existing.get("stated")))
    out = OrderedDict(existing)
    out["quote"] = quote
    return out


def migrate_record(record: Mapping) -> Tuple[Dict, Dict]:
    """``(new_record, note)``. Patch semantics; the note is for the report."""
    new = copy.deepcopy(dict(record))
    prior_record_hash = (record.get("approval") or {}).get("record_hash", "")
    prior_evidence_hash = (record.get("approval") or {}).get("evidence_hash", "")

    changed: List[str] = []
    if new.get("schema_version") != enums.POLICY_SCHEMA_VERSION:
        changed.append("schema_version %s -> %s"
                       % (new.get("schema_version"),
                          enums.POLICY_SCHEMA_VERSION))
        new["schema_version"] = enums.POLICY_SCHEMA_VERSION

    quote = _statement_evidence(record)
    existing = record.get(SA_FIELD)
    statement = None
    if quote:
        if not isinstance(existing, Mapping):
            raise MigrationError(
                "%s quotes a %s in its evidence but carries no such statement; "
                "adding one is a founder decision, not a schema stamp"
                % (record.get("identity_key"), SA_FIELD))
        if existing.get("quote"):
            raise MigrationError("%s already carries a %s.quote"
                                 % (record.get("identity_key"), SA_FIELD))
        statement = quoted_statement(existing, quote)
        new[SA_FIELD] = statement
        changed.append("%s.quote published (charges_stated=%s, verified "
                       "against contracts.service_animal)"
                       % (SA_FIELD, statement["charges_stated"]))
    elif isinstance(existing, Mapping):
        raise MigrationError(
            "%s carries a %s with no evidence entry quoting it"
            % (record.get("identity_key"), SA_FIELD))

    # The statement the founder committed may gain a quote and nothing else.
    if statement is not None:
        was = {k: v for k, v in existing.items() if k != "quote"}
        now = {k: v for k, v in statement.items() if k != "quote"}
        if was != now:
            raise MigrationError("%s: the committed %s moved: %r -> %r"
                                 % (record.get("identity_key"), SA_FIELD,
                                    was, now))

    # Nothing else the migration does not own may move.
    for field in FROZEN:
        if json.dumps(record.get(field), sort_keys=True) != \
                json.dumps(new.get(field), sort_keys=True):
            raise MigrationError("%s: migration moved %r, which it does not own"
                                 % (record.get("identity_key"), field))

    approval = new.get("approval")
    if not isinstance(approval, Mapping):
        raise MigrationError("%s has no approval block"
                             % record.get("identity_key"))
    approval = OrderedDict(approval)
    new_evidence_hash = PM.evidence_hash(new.get("evidence") or ())
    if new_evidence_hash != prior_evidence_hash:
        raise MigrationError(
            "%s: evidence_hash moved (%s -> %s). This migration does not touch "
            "evidence; a moved evidence hash is a real withdrawal and belongs "
            "to the founder, not to a schema stamp."
            % (record.get("identity_key"), prior_evidence_hash,
               new_evidence_hash))

    # Rebind, and say so -- INSIDE the approval block.
    #
    # record_hash is a hash over the record MINUS its approval, so the note
    # that records the rebinding cannot live on the record: hashing it would
    # make the committed hash unreproducible by ``policy_migration.record_hash``,
    # which is the one function any later reader will check it with. The
    # approval namespace is already the excluded one, and a statement about an
    # approval is what this is.
    approval["record_hash"] = PM.record_hash(
        {k: v for k, v in new.items() if k != "approval"})
    approval["rebinding"] = OrderedDict((
        ("work_order", WORK_ORDER),
        ("from_schema", str(record.get("schema_version") or "")),
        ("to_schema", enums.POLICY_SCHEMA_VERSION),
        ("changed", changed),
        ("prior_record_hash", prior_record_hash),
        ("evidence_hash_unchanged", True),
        ("note",
         "The founder's decision, facts, withholding, evidence and committed "
         "service-animal charge state are byte-identical; what moved is the "
         "schema stamp and, on seven records, the 1.3 quote field that "
         "publishes a sentence this founder had already approved. record_hash "
         "is taken over the whole record, so it moves with them. This REBINDS "
         "the existing approval to the record it now describes. It is not "
         "itself an approval: no decision was re-asked, and none was "
         "re-signed."),
    ))
    new["approval"] = approval
    return new, {"identity_key": record.get("identity_key"),
                 "changed": changed,
                 "prior_record_hash": prior_record_hash,
                 "record_hash": approval["record_hash"],
                 "statement": statement}


def run(write: bool) -> int:
    document = json.loads(PACKAGE.read_text(encoding="utf-8"))
    before = PM.validate_migrated(document)
    if before:
        raise MigrationError("the package does not validate BEFORE migration; "
                             "fix that first: %s" % before[:5])

    new = copy.deepcopy(document)
    notes = []
    records = []
    for record in document.get("hotels") or ():
        migrated, note = migrate_record(record)
        records.append(migrated)
        notes.append(note)
    new["schema_version"] = enums.POLICY_SCHEMA_VERSION
    new["hotels"] = records

    problems = PM.validate_migrated(new)
    if problems:
        raise MigrationError("migrated package does not validate: %s"
                             % problems[:10])

    statements = [n for n in notes if n["statement"]]
    print("package        : %s -> %s"
          % (document.get("schema_version"), new["schema_version"]))
    print("records        : %d (before %d)"
          % (len(records), len(document.get("hotels") or ())))
    print("rebound        : %d" % sum(1 for n in notes if n["changed"]))
    print("%-15s: %d" % (SA_FIELD, len(statements)))
    for n in statements:
        print("   %-50s %-14s %s"
              % (n["identity_key"], n["statement"]["charges_stated"],
                 n["statement"]["quote"][:60]))
    print("contract issues: %d" % len(problems))

    if write:
        PACKAGE.write_text(
            json.dumps(new, indent=1, ensure_ascii=False) + "\n",
            encoding="utf-8", newline="\n")
        print("WROTE %s" % PACKAGE.name)
    else:
        print("(check only -- pass --write)")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    try:
        return run(args.write)
    except MigrationError as exc:
        print("REFUSED: %s" % exc)
        return 2


if __name__ == "__main__":                                # pragma: no cover
    raise SystemExit(main())
