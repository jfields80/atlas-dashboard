# -*- coding: utf-8 -*-
"""PTF-CINCINNATI-SPECIES-KEY-REBIND-011 -- canonicalise eight species keys.

    python -m scripts.pettripfinder.cincinnati_species_key_rebind_011
    python -m scripts.pettripfinder.cincinnati_species_key_rebind_011 --write

THE DEFECT
----------
Eight Cincinnati records written on 2026-08-17 store their species under
``dog`` / ``cat``. ``canonical_view.dogs_state`` and ``cats_state`` read
``dogs`` / ``cats``, so all eight project an empty species state and their
species never reach a public surface. The stored authority is correct; only the
projection is wrong. This was first reported by
PTF-CINCINNATI-FOUNDER-REVIEW-AND-APPLICATION-004 and has been carried as a
deferred defect through every order since.

WHAT THIS CHANGES, AND WHAT IT MUST NOT
---------------------------------------
Key names. Nothing else. Not a state, not an operator, not a scope, not a
quote, not an evidence entry, not a fee, not a count, not a weight, not a
service-animal reading, not the pets_allowed boolean, and no record outside the
mechanically located cohort. The module proves that per record rather than
asserting it: ``semantic_diff`` compares the whole record before and after with
the species keys normalised on both sides, and refuses if anything but the key
spelling moved.

WHY THE APPROVAL NEEDS A REBINDING BLOCK
----------------------------------------
``record_hash`` is taken over the record minus ``approval``, so renaming a key
inside ``facts`` moves it. The founder's approval signed the OLD bytes. Writing
the new hash into ``record_hash`` and saying nothing would quietly claim the
founder had signed a representation they never saw.

So each approval gains a ``rebinding`` block naming the old hash, the new hash,
and the four things that did NOT change. It lives INSIDE ``approval`` -- the
region ``record_hash`` excludes -- because a block at the record root would be
part of the hashed payload and could never reproduce.
PTF-CINCINNATI-HARDENED-SYNC-002 learned that the hard way: a
``schema_migration`` block placed on the record made all twenty-one hashes of
the day unreproducible.

``evidence_hash`` is untouched throughout. No evidence entry is edited, so the
hash that binds them must not move.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import canonical_view as CV                # noqa: E402
from scripts.pettripfinder import policy_migration as PM              # noqa: E402
from scripts.pettripfinder.contracts import policy_schema             # noqa: E402

WORK_ORDER = "PTF-CINCINNATI-SPECIES-KEY-REBIND-011"
MARKET_ID = "cincinnati-oh"
AS_OF = "2026-08-31"
REASON = "SPECIES_KEY_CANONICALIZATION"

PKG = _REPO_ROOT / "launch_packages" / "pettripfinder"
PACKAGE = PKG / "hotel_policy_facts_cincinnati-oh.json"
REPORT = PKG / "markets" / "reports" / "cincinnati_species_key_rebind_011.json"

#: The only rename this module performs.
RENAME = {"dog": "dogs", "cat": "cats"}
EXPECTED = 8


class RebindError(RuntimeError):
    pass


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def needs_rebind(record: Dict) -> bool:
    species = (record.get("facts") or {}).get("species")
    return isinstance(species, dict) and bool(set(species) & set(RENAME))


def rename_species(species: Dict) -> "OrderedDict":
    """Rename in place, preserving the record's existing key order.

    Four of the eight store ``cat`` before ``dog``; reordering them would make
    the diff larger than the change.
    """
    return OrderedDict((RENAME.get(name, name), state)
                       for name, state in species.items())


def _normalised(record: Dict) -> Dict:
    """The record with species keys canonical on either side of the change.

    Comparing two of these is how "only the key spelling moved" is PROVED
    rather than asserted.
    """
    probe = copy.deepcopy(record)
    probe.pop("approval", None)
    species = (probe.get("facts") or {}).get("species")
    if isinstance(species, dict):
        probe["facts"]["species"] = dict(rename_species(species))
    return probe


def semantic_diff(before: Dict, after: Dict) -> List[str]:
    """Everything that changed other than the species key spelling."""
    problems = []
    if _normalised(before) != _normalised(after):
        problems.append("the record changed beyond its species key names")

    old_species = (before.get("facts") or {}).get("species") or {}
    new_species = (after.get("facts") or {}).get("species") or {}
    if list(new_species.keys()) != [RENAME.get(k, k) for k in old_species]:
        problems.append("species keys were reordered or altered")
    if list(new_species.values()) != list(old_species.values()):
        problems.append("a species state changed")
    if set(new_species) - {"dogs", "cats"}:
        problems.append("a species key is still not canonical")

    for field in ("evidence", "evidence_quote", "source_url",
                  "service_animal_statement", "withheld_fields",
                  "verification_state", "computation_class"):
        if before.get(field) != after.get(field):
            problems.append("%s changed" % field)
    old_facts = dict(before.get("facts") or {})
    new_facts = dict(after.get("facts") or {})
    old_facts.pop("species", None)
    new_facts.pop("species", None)
    if old_facts != new_facts:
        problems.append("a non-species fact changed")

    old_ap = before.get("approval") or {}
    new_ap = after.get("approval") or {}
    for field in ("decision", "operator", "approval_date", "caveats",
                  "evidence_hash"):
        if old_ap.get(field) != new_ap.get(field):
            problems.append("approval.%s changed" % field)
    return problems


def projection(record: Dict) -> Tuple[str, str]:
    view = CV.build(record, market_id=MARKET_ID)
    return view.dogs_state, view.cats_state


def rebind(record: Dict) -> Tuple[Dict, Dict]:
    """One record, rebound. Returns the new record and its report row."""
    before = copy.deepcopy(record)
    after = copy.deepcopy(record)
    after["facts"]["species"] = rename_species(after["facts"]["species"])

    old_hash = (before.get("approval") or {}).get("record_hash", "")
    computed_old = PM.record_hash(before)
    if old_hash != computed_old:
        raise RebindError("%s: its committed record_hash does not reproduce "
                          "before any change" % record["identity_key"])

    problems = semantic_diff(before, after)
    if problems:
        raise RebindError("%s: %s" % (record["identity_key"], problems))

    approval = after["approval"]
    new_hash = PM.record_hash(after)
    approval["record_hash"] = new_hash
    approval["rebinding"] = OrderedDict((
        ("reason", REASON),
        ("old_record_hash", old_hash),
        ("new_record_hash", new_hash),
        ("semantic_change", False),
        ("evidence_change", False),
        ("source_change", False),
        ("authority_change", False),
        ("work_order", WORK_ORDER),
        ("rebound_on", AS_OF),
        ("what_moved",
         "The species keys were renamed %s. canonical_view reads "
         "species['dogs'] and species['cats'], so these records projected an "
         "empty species state and their species never reached a public "
         "surface. record_hash is taken over the record minus approval, so "
         "renaming a key inside facts moves it; the founder's decision, its "
         "caveats, every evidence entry and evidence_hash are unchanged, and "
         "this block records that the hash the founder signed was the old one."
         % ", ".join("%s -> %s" % (k, v) for k, v in sorted(RENAME.items()))),
    ))

    before_dogs, before_cats = projection(before)
    after_dogs, after_cats = projection(after)
    row = OrderedDict((
        ("identity_key", record["identity_key"]),
        ("approval_date", approval["approval_date"]),
        ("species_before", OrderedDict(before["facts"]["species"])),
        ("species_after", OrderedDict(after["facts"]["species"])),
        ("projection_before", OrderedDict((("dogs_state", before_dogs),
                                           ("cats_state", before_cats)))),
        ("projection_after", OrderedDict((("dogs_state", after_dogs),
                                          ("cats_state", after_cats)))),
        ("old_record_hash", old_hash),
        ("new_record_hash", new_hash),
        ("evidence_hash", approval["evidence_hash"]),
        ("evidence_hash_unchanged",
         approval["evidence_hash"] == (before["approval"]["evidence_hash"])),
        ("semantic_changes", 0),
    ))
    if before_dogs or before_cats:
        raise RebindError("%s: it already projected a species state, so it is "
                          "not the defect this order repairs"
                          % record["identity_key"])
    if not (after_dogs or after_cats):
        raise RebindError("%s: it still projects nothing after the rebind"
                          % record["identity_key"])
    return after, row


def build():
    package = _load(PACKAGE)
    hotels = package["hotels"]

    cohort = [h for h in hotels if needs_rebind(h)]
    if len(cohort) != EXPECTED:
        raise RebindError("cohort is %d records, expected %d -- STOP and "
                          "report" % (len(cohort), EXPECTED))
    for record in cohort:
        species = record["facts"]["species"]
        if set(species) & set(RENAME.values()):
            raise RebindError("%s already carries a canonical key beside a "
                              "singular one" % record["identity_key"])

    keys = {h["identity_key"] for h in cohort}
    rows, rebuilt = [], []
    for record in hotels:
        if record["identity_key"] in keys:
            new_record, row = rebind(record)
            rebuilt.append(new_record)
            rows.append(row)
        else:
            rebuilt.append(record)

    # Nothing outside the cohort may move, byte for byte.
    for old, new in zip(hotels, rebuilt):
        if old["identity_key"] in keys:
            continue
        if old is not new or json.dumps(old, sort_keys=True) != \
                json.dumps(new, sort_keys=True):
            raise RebindError("%s changed and it is not in the cohort"
                              % old["identity_key"])

    package["hotels"] = rebuilt
    issues = policy_schema.validate_package(package)
    if issues:
        raise RebindError("package does not validate: %s"
                          % [str(i) for i in issues[:6]])
    problems = PM.validate_migrated(package)
    if problems:
        raise RebindError("migration validation failed: %s" % problems[:6])
    return package, rows


def audit_all(package) -> Dict:
    """Every published record's species projection, after the change."""
    projects, empty, no_species = [], [], []
    for record in package["hotels"]:
        species = (record.get("facts") or {}).get("species")
        if not species:
            no_species.append(record["identity_key"])
            continue
        dogs, cats = projection(record)
        (projects if (dogs or cats) else empty).append(record["identity_key"])
    return OrderedDict((
        ("records", len(package["hotels"])),
        ("with_species_evidence", len(projects) + len(empty)),
        ("projecting_a_species_state", len(projects)),
        ("projecting_nothing", len(empty)),
        ("projecting_nothing_keys", sorted(empty)),
        ("no_species_block", len(no_species)),
    ))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    try:
        package, rows = build()
    except RebindError as exc:
        print("REFUSED: %s" % exc)
        return 2

    audit = audit_all(package)
    print("records rebound        : %d" % len(rows))
    print("semantic changes       : 0")
    print("evidence changes       : 0")
    print("package records        : %d" % audit["records"])
    print("with species evidence  : %d" % audit["with_species_evidence"])
    print("projecting a state     : %d" % audit["projecting_a_species_state"])
    print("projecting nothing     : %d" % audit["projecting_nothing"])
    for row in rows:
        print("  %-42s %s -> %s" % (row["identity_key"][:42],
                                    json.dumps(row["species_before"]),
                                    json.dumps(row["species_after"])))
    if not args.write:
        print("(check only -- pass --write)")
        return 0

    PACKAGE.write_text(json.dumps(package, indent=1, ensure_ascii=False) + "\n",
                       encoding="utf-8", newline="\n")
    print("WROTE %s" % PACKAGE.name)

    report = OrderedDict((
        ("schema", "ptf-market-record-rebind/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("as_of", AS_OF),
        ("reason", REASON),
        ("first_reported_by",
         "PTF-CINCINNATI-FOUNDER-REVIEW-AND-APPLICATION-004, which found the "
         "defect while applying Capture Pass 3 and declined to rewrite "
         "founder-approved records silently."),
        ("what_changed", "Species key names only: %s."
         % ", ".join("%s -> %s" % (k, v) for k, v in sorted(RENAME.items()))),
        ("what_did_not_change",
         "No species state, no fee, count, weight or service-animal reading, "
         "no evidence entry, no evidence_hash, no founder decision or caveat, "
         "no pets_allowed boolean, and no record outside these eight."),
        ("provider_calls", 0),
        ("paid_spend_usd", 0.0),
        ("count", len(rows)),
        ("rows", rows),
        ("projection_audit", audit),
    ))
    REPORT.write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n",
                      encoding="utf-8", newline="\n")
    print("WROTE %s" % REPORT.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
