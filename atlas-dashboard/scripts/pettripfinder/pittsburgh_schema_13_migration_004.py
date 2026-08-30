# -*- coding: utf-8 -*-
"""PTF-PITTSBURGH-HARDENED-SYNC-004 Phase 5 -- defect D1, and Pittsburgh's package to 1.3.

    python -m scripts.pettripfinder.pittsburgh_schema_13_migration_004
    python -m scripts.pettripfinder.pittsburgh_schema_13_migration_004 --write

THE DEFECT AND THE FIELD THAT ANSWERS IT
------------------------------------------
Two committed Pittsburgh records fail the current validator:

    residence inn pittsburgh north shore   facts.other_charges[0].refundable
    hyatt place pittsburgh north shore     facts.other_charges[0].refundable
    -> "refundable is required and is never inferred (MISSING_REQUIRED)"

Both charges are conditional cleaning fees whose sources state an amount and a
trigger and never say whether the money comes back. Under 1.2 that left two bad
options -- invent a boolean, or withhold a charge the source plainly states.

Schema 1.3 exists partly for this. Its second addition is
``other_charges[].refundable_stated``, whose entire purpose is to let a charge
say THE SOURCE DID NOT STATE REFUNDABILITY, which is a different claim from "it
is not refundable". ``policy_schema._check_other_charges`` even names these rows:
"a contingent charge must carry the source's own stated trigger (Pittsburgh Pass
3/4 conditional cleaning charges)".

So D1 is not repaired by choosing a boolean. It is repaired by migrating to the
schema that can express what the source actually said.

WHAT THE EVIDENCE ACTUALLY SAYS
--------------------------------
Checked against each record's own bound evidence, and this run REFUSES if it
ever stops being true:

* Residence Inn North Shore's page says "Non-Refundable Pet Fee Per Stay:
  $100.00". That "non-refundable" qualifies the PET FEE, which the record
  already carries as ``pet_fee.refundable = false``. It does not reach the
  separate $250 conditional cleaning fee two clauses away -- the exact
  over-reach ``authority_build_040`` was written to prevent. The page's other
  "refundable" strings are Hilton/Marriott UI template labels
  ("hws.refundPetDeposit"), not this property's facts.
* Hyatt Place North Shore states "7 - 30 nights : + $100 [.] Cleaning fee" and
  nothing about refundability anywhere.

Neither source states it. So ``refundable_stated = false`` is a statement about
the SOURCE, which is verifiable, and no ``refundable`` boolean is written.

PATCH, NEVER REBUILD
---------------------
Per record, exactly three things may move: ``schema_version``, the two named
charges' ``refundable_stated``, and ``approval.record_hash``. Everything else --
every other fact, all evidence, withholding, computation class, verification
state, and the founder's decision -- is asserted byte-identical afterwards.
Thirty-five of the 37 records change in nothing but their version stamp.

REBOUND, NOT RE-ASKED
----------------------
``record_hash`` is a sha256 over the record minus its approval, so both the
version stamp and the new field move it. Following PTF-...-APPROVAL-BINDING-039
and the Cincinnati precedent, each approval gains a ``rebinding`` block naming
the prior hash and the reason, INSIDE the approval -- a note anywhere else would
be hashed into the value it reports. ``evidence_hash`` must NOT move: no
evidence changes here, and a moved evidence hash would be a real withdrawal,
which belongs to the founder. The run aborts if one moves.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import policy_migration as PM          # noqa: E402
from scripts.pettripfinder.contracts import enums                 # noqa: E402

WORK_ORDER = "PTF-PITTSBURGH-HARDENED-SYNC-004"
MARKET_ID = "pittsburgh-pa"
PACKAGE_DIR = _REPO_ROOT / "launch_packages" / "pettripfinder"
PACKAGE = PACKAGE_DIR / ("hotel_policy_facts_%s.json" % MARKET_ID)

FROM_SCHEMA = "1.2"
TO_SCHEMA = enums.POLICY_SCHEMA_VERSION

#: identity_key -> (charge index, the quote that must remain the charge's
#: trigger, the phrase whose absence proves the source is silent on
#: refundability for THIS charge).
UNSTATED_REFUNDABILITY = {
    "residence inn pittsburgh north shore": (
        0,
        "Must sign waiver stating cats are neutered or a $250.00 cleaning fee may apply.",
        "the page's only refundability words, 'Non-Refundable Pet Fee Per Stay: "
        "$100.00', qualify the pet fee the record already carries as "
        "refundable=false; they do not reach this separate conditional cleaning fee",
    ),
    "hyatt place pittsburgh north shore": (
        0,
        "7 - 30 nights",
        "the source states the tier and the words 'Cleaning fee' and says "
        "nothing anywhere about refundability",
    ),
}

#: Everything that must be byte-identical after the patch. ``facts`` is NOT
#: here because this migration's whole purpose is one addition inside it; it is
#: policed instead by ``_assert_facts_moved_only_as_authorised``.
FROZEN = ("key", "identity_key", "name", "market_id", "evidence",
          "evidence_count", "evidence_quote", "source_url", "source_type",
          "verification_state", "verification_date", "verified_at",
          "computation_class", "withheld_fields", "service_animal_statement")

_NON_REFUNDABLE = re.compile(r"\bnon[-\s]?refundable\b", re.IGNORECASE)


class MigrationError(RuntimeError):
    pass


def _stable(node) -> str:
    return json.dumps(node, sort_keys=True, ensure_ascii=False)


def _assert_facts_moved_only_as_authorised(before: Mapping, after: Mapping,
                                           key: str) -> None:
    """The ONLY authorised movement inside facts is refundable_stated."""
    a, b = copy.deepcopy(dict(before)), copy.deepcopy(dict(after))
    for facts in (a, b):
        for charge in facts.get("other_charges") or ():
            charge.pop("refundable_stated", None)
    if _stable(a) != _stable(b):
        raise MigrationError("%s: facts moved beyond refundable_stated" % key)


def _patch_charges(record: Mapping, key: str) -> Tuple[Dict, bool]:
    """Return ``(facts, changed)`` with refundable_stated on the named charge."""
    facts = copy.deepcopy(record["facts"])
    if key not in UNSTATED_REFUNDABILITY:
        return facts, False
    index, trigger, _why = UNSTATED_REFUNDABILITY[key]
    charges = facts.get("other_charges") or []
    if index >= len(charges):
        raise MigrationError("%s: charge %d is gone" % (key, index))
    charge = charges[index]
    if "refundable" in charge:
        raise MigrationError(
            "%s: charge %d already states refundable=%r; this migration is for "
            "charges the source is SILENT about and must not overwrite a stated "
            "value" % (key, index, charge["refundable"]))
    if charge.get("refundable_stated") is not None:
        raise MigrationError("%s: charge %d already carries refundable_stated"
                             % (key, index))
    if trigger not in str(charge.get("trigger") or ""):
        raise MigrationError("%s: charge %d no longer carries the trigger this "
                             "migration was written against" % (key, index))
    # The source must still be silent. If a later capture ever states
    # refundability for this charge, that is a founder question.
    for entry in record.get("evidence") or ():
        if entry.get("field") != "other_charges":
            continue
        quote = str(entry.get("quote") or "")
        if _NON_REFUNDABLE.search(quote) or re.search(
                r"(?<!non[-\s])\brefundable\b", quote, re.IGNORECASE):
            raise MigrationError(
                "%s: an other_charges evidence quote now states refundability "
                "(%r); that is a founder question, not a migration" % (key, quote))
    charge["refundable_stated"] = False
    return facts, True


def migrate_record(record: Mapping) -> Tuple[Dict, List[str]]:
    key = record["identity_key"]
    before_facts = record["facts"]
    new = copy.deepcopy(dict(record))
    changed: List[str] = []

    if new.get("schema_version") != TO_SCHEMA:
        new["schema_version"] = TO_SCHEMA
        changed.append("schema_version")

    facts, patched = _patch_charges(record, key)
    if patched:
        new["facts"] = facts
        changed.append("facts.other_charges[].refundable_stated")
    _assert_facts_moved_only_as_authorised(before_facts, new["facts"], key)

    for field in FROZEN:
        if _stable(record.get(field)) != _stable(new.get(field)):
            raise MigrationError("%s: frozen field %r moved" % (key, field))

    approval = new["approval"]
    prior_record_hash = approval.get("record_hash")
    prior_evidence_hash = approval.get("evidence_hash")
    if PM.evidence_hash(new.get("evidence") or ()) != prior_evidence_hash:
        raise MigrationError(
            "%s: evidence_hash moved; no evidence changes in this migration and "
            "a real withdrawal belongs to the founder" % key)
    if not changed:
        return new, changed

    approval["record_hash"] = PM.record_hash(
        {k: v for k, v in new.items() if k != "approval"})
    approval["rebinding"] = OrderedDict((
        ("work_order", WORK_ORDER),
        ("from_schema", record.get("schema_version")),
        ("to_schema", TO_SCHEMA),
        ("changed", list(changed)),
        ("prior_record_hash", prior_record_hash),
        ("evidence_hash_unchanged", True),
        ("note",
         ("The founder's decision, its evidence and every published fact are "
          "unchanged. %s") % (
             ("Schema 1.3 adds other_charges[].refundable_stated, and this "
              "charge now says the SOURCE did not state refundability: %s. No "
              "refundable boolean is asserted."
              % UNSTATED_REFUNDABILITY[key][2])
             if patched else
             "Only the schema version stamp moved, which moves the hash the "
             "approval binds, so the binding is restated rather than re-asked.")),
    ))
    return new, changed


def run(write: bool) -> int:
    package = json.loads(PACKAGE.read_text(encoding="utf-8-sig"))
    before = PM.validate_migrated(package)
    expected = {"hotels[%s].facts.other_charges[%d].refundable" % (k, v[0])
                for k, v in UNSTATED_REFUNDABILITY.items()}
    unexpected = [p for p in before
                  if not any(e in p for e in expected)]
    if unexpected:
        raise MigrationError("the package fails validation for reasons this "
                             "migration does not address: %s" % unexpected[:5])
    print("validator issues before : %d (D1: %d)" % (len(before), len(expected)))

    records, patched, stamped = [], [], []
    for record in package["hotels"]:
        new, changed = migrate_record(record)
        records.append(new)
        if "facts.other_charges[].refundable_stated" in changed:
            patched.append(record["identity_key"])
        elif changed:
            stamped.append(record["identity_key"])

    out = OrderedDict(package)
    out["schema_version"] = TO_SCHEMA
    out["hotels"] = records

    after = PM.validate_migrated(out)
    if after:
        raise MigrationError("the migrated package does not validate: %s"
                             % after[:5])
    print("records patched (D1)    : %d %s" % (len(patched), patched))
    print("records version-stamped : %d" % len(stamped))
    print("validator issues after  : %d" % len(after))
    if not write:
        print("(check only -- pass --write)")
        return 0
    PACKAGE.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n",
                       encoding="utf-8", newline="\n")
    print("WROTE %s (schema %s, %d records)"
          % (PACKAGE.name, TO_SCHEMA, len(records)))
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


if __name__ == "__main__":
    raise SystemExit(main())
