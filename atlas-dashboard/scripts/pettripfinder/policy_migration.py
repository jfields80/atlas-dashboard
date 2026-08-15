"""PTF-POLICY-SCHEMA-MIGRATION-001 -- legacy policy authority to schema 1.2.

Phases A-E built the contract, made the renderer tell the truth, and fixed
identity, geography and routes. The one thing still speaking the old language
was the data itself: 156 published records in 1.0/1.1, carrying money as
``"$50.00"``, booleans as ``"true"``, a scope spelled ``"per room"``, a weight
operator overloaded with the word ``combined``, and 148 withholding decisions
written as English sentences that no consumer could group or re-adjudicate.

This module migrates them, under two rules that shape everything below.

PATCH, NEVER REBUILD
--------------------
Phase C learned this the expensive way: a migration that serialises a reduced
model silently deletes every field the model does not name. ``compat_readers``
is a READER -- its output holds ``identity_key``, ``facts``, ``evidence`` and
little else, dropping ``key``, ``evidence_count``, ``evidence_quote``,
``verification_date`` and all five ``worker_*`` fields. So its output is never
written. Each record is deep-copied, the fields migration OWNS are replaced,
the legacy keys it consumed are removed, and everything else -- including keys
this module has never heard of -- survives untouched. ``unowned_fields_kept``
in the report is the proof, per record.

NO SEMANTIC GUESSING
--------------------
Every change is MECHANICAL_LOSSLESS (a spelling the frozen table already maps),
REVIEWED_SOURCE_BACKED (a decision recorded in the decisions file, quoting the
committed evidence that establishes it), WITHHELD, or DEFERRED_BLOCKED. There
is no fifth kind. A legacy value with no mapping and no reviewed decision stops
that field -- it is never inferred from a hotel name, a brand, or what a chain
usually does.

    python -m scripts.pettripfinder.policy_migration --market cleveland-akron-canton-oh
    python -m scripts.pettripfinder.policy_migration --market dayton-oh --write
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.contracts import (                                # noqa: E402
    compat_readers, enums, evidence as evidence_contract, policy_schema,
    withholding,
)
from scripts.pettripfinder.contracts.fee_computation import classify         # noqa: E402
from scripts.pettripfinder.contracts.identity_key import ptf_identity_key    # noqa: E402
from scripts.pettripfinder.contracts.review_queue import POLICY_PACKAGES     # noqa: E402

PACKAGE_DIR = _REPO_ROOT / "launch_packages" / "pettripfinder"
DECISIONS_PATH = PACKAGE_DIR / "policy_migration_decisions.json"

DECISIONS_SCHEMA = "ptf-policy-migration-decisions/1.0"

#: Legacy fact keys this migration consumes. Every one is either translated
#: into a canonical field or deliberately dropped as silence; a legacy key NOT
#: in this set that survives into the output is a defect the report names,
#: because silently keeping it would leave 1.2 and 1.0 side by side in one
#: record.
CONSUMED_LEGACY_FACT_KEYS = frozenset({
    "pets_allowed", "pet_fee", "fee_basis", "fee_scope", "fee_tiers",
    "fee_cap", "fee_cap_tiers", "fee_pet_schedule", "fee_schedule",
    "fee_conflict", "fee_withheld", "cleaning_fee", "pet_deposit",
    "weight_limit", "weight_limit_operator", "weight_limit_combined",
    "weight_limit_combined_operator", "weight_limit_stated_none",
    "species_allowed", "cats_allowed", "species_weight_limits",
    "service_animal_exception", "pet_count_limit", "pet_count_scope",
    "breed_restrictions", "breed_restrictions_stated_none",
    "unattended_policy", "reservation_requirement", "pet_room_restriction",
    "general_restrictions", "age_restriction",
})

#: Record-level keys migration owns. Everything else is carried verbatim.
OWNED_RECORD_KEYS = ("schema_version", "identity_key", "market_id", "facts",
                     "evidence", "withheld_fields", "approval",
                     "service_animal_statement", "computation_class")

#: Phase F links evidence that already exists; it does not manufacture capture
#: metadata. Publication-grade evidence requires an artifact hash, an artifact
#: kind and a capture timestamp, and the committed corpus has none of the
#: three -- so every legacy entry is declared POINTER_TO_EVIDENCE, which is
#: exactly what it is: a verbatim quote and the URL it came from. Upgrading
#: these to publication grade is PTF-EVIDENCE-COMPLETION-001 (Phase G) and
#: would be fabrication here. This is the explicit, testable compatibility
#: exception section 27 requires.
LEGACY_ARTIFACT_CLASS = enums.POINTER_TO_EVIDENCE

MIGRATED_MECHANICALLY = "MIGRATED_MECHANICALLY"
MIGRATED_WITH_REVIEW = "MIGRATED_WITH_REVIEW"
MIGRATED_WITH_WITHHOLDING = "MIGRATED_WITH_WITHHOLDING"
BLOCKED = "BLOCKED"

#: Dispositions a reviewed withholding decision may take.
DISPOSITION_SILENCE = "SOURCE_SILENCE"          # drop; absence says it better
DISPOSITION_WITHHOLD = "TRUE_WITHHOLDING"       # keep, with a reason code
DISPOSITION_RESOLVED = "RESOLVED_BY_SCHEMA"     # 1.2 can now state the fact
DISPOSITIONS = (DISPOSITION_SILENCE, DISPOSITION_WITHHOLD, DISPOSITION_RESOLVED)


class MigrationError(RuntimeError):
    """A record cannot be migrated without guessing. Nothing is written."""


# --------------------------------------------------------------------------- #
# Decisions file.
# --------------------------------------------------------------------------- #

def load_decisions(path: Optional[Path] = None) -> Dict[str, Any]:
    """The reviewed decisions that turn legacy prose into canonical structure.

    Keyed by EXACT legacy string, never by keyword. A keyword rule would map
    "the page states no weight limit" and "the page states a per-dog maximum,
    never a combined one" to the same disposition; they are different findings
    about different fields, and only one of them is silence.
    """
    path = path or DECISIONS_PATH
    if not path.is_file():
        return {"schema": DECISIONS_SCHEMA, "withheld_prose": {}, "species": {},
                "records": {}}
    document = json.loads(path.read_text(encoding="utf-8-sig"))
    if document.get("schema") != DECISIONS_SCHEMA:
        raise MigrationError("decisions file declares schema %r, expected %r"
                             % (document.get("schema"), DECISIONS_SCHEMA))
    return document


def prose_key(field_path: str, prose: str) -> str:
    """The lookup key for one legacy withholding sentence."""
    return "%s|%s" % (field_path, prose)


def record_key(market_id: str, identity_key: str) -> str:
    return "%s|%s" % (market_id, identity_key)


# --------------------------------------------------------------------------- #
# Deterministic references and hashes (section 25).
# --------------------------------------------------------------------------- #

def _stable_json(node: Any) -> str:
    return json.dumps(node, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)


def evidence_ref_for(entry: Mapping) -> str:
    """A content-derived reference for one evidence entry.

    Derived from the quote, the URL and the field it supports, so it is stable
    across runs (idempotence), independent of array order, and changes when the
    evidence changes -- which is exactly what ``evidence_hash`` needs.
    """
    material = "\x1f".join((str(entry.get("field") or ""),
                            str(entry.get("quote") or ""),
                            str(entry.get("source_url") or "")))
    return "ev:%s" % hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]


def record_hash(record: Mapping) -> str:
    """Hash of the record's SUBSTANCE, excluding the approval that signs it.

    Excluding the approval block is what makes the binding meaningful: an
    approval is a statement ABOUT a record, so if signing the record changed
    the record, no approval could ever match what it approved.
    """
    material = {k: v for k, v in record.items() if k != "approval"}
    return "sha256:%s" % hashlib.sha256(
        _stable_json(material).encode("utf-8")).hexdigest()


def evidence_hash(entries: Sequence[Mapping]) -> str:
    """Hash over the SORTED SET of evidence references.

    Sorted, so re-ordering the array does not invalidate an approval; a set, so
    the hash answers "which evidence" rather than "in which order it happened
    to be written".
    """
    refs = sorted({str(e.get("evidence_ref") or evidence_ref_for(e))
                   for e in entries if isinstance(e, Mapping)})
    return "sha256:%s" % hashlib.sha256(
        _stable_json(refs).encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# Per-record migration.
# --------------------------------------------------------------------------- #

class RecordMigration:
    """The outcome of migrating one record, with everything the log needs."""

    def __init__(self, identity_key: str, name: str, market_id: str):
        self.identity_key = identity_key
        self.name = name
        self.market_id = market_id
        self.old_schema = ""
        self.mechanical: List[str] = []
        self.reviewed: List[str] = []
        self.withheld: List[str] = []
        self.silence_dropped: List[str] = []
        self.evidence_refs_added = 0
        self.approval_change = ""
        self.computation_class = ""
        self.unowned_fields_kept: List[str] = []
        self.unresolved: List[str] = []
        self.record: Dict[str, Any] = {}

    @property
    def status(self) -> str:
        if self.unresolved:
            return BLOCKED
        if self.withheld:
            return MIGRATED_WITH_WITHHOLDING
        if self.reviewed:
            return MIGRATED_WITH_REVIEW
        return MIGRATED_MECHANICALLY

    def as_log_row(self) -> "OrderedDict[str, Any]":
        return OrderedDict([
            ("market", self.market_id),
            ("identity_key", self.identity_key),
            ("name", self.name),
            ("old_schema", self.old_schema),
            ("new_schema", enums.POLICY_SCHEMA_VERSION),
            ("mechanical_changes", sorted(self.mechanical)),
            ("reviewed_changes", sorted(self.reviewed)),
            ("withheld_fields", sorted(self.withheld)),
            ("silence_markers_removed", sorted(self.silence_dropped)),
            ("evidence_refs_added", self.evidence_refs_added),
            ("approval_change", self.approval_change),
            ("computation_class", self.computation_class),
            ("unowned_fields_kept", sorted(self.unowned_fields_kept)),
            ("unresolved", sorted(self.unresolved)),
            ("status", self.status),
        ])


def _migrate_evidence(entries: Sequence[Mapping], out: RecordMigration
                      ) -> List[Dict[str, Any]]:
    """Name each existing evidence entry; never alter what it says.

    Only two keys are added -- ``evidence_ref`` and ``artifact_class`` -- and
    both describe the entry rather than its content. Quote text, source URL and
    value are copied through byte for byte (section 41).
    """
    migrated: List[Dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, Mapping):
            continue
        new = dict(entry)
        if not new.get("evidence_ref"):
            new["evidence_ref"] = evidence_ref_for(entry)
            out.evidence_refs_added += 1
        if not new.get("artifact_class"):
            new["artifact_class"] = LEGACY_ARTIFACT_CLASS
        migrated.append(new)
    return migrated


def _refs_for_path(field_path: str, entries: Sequence[Mapping]) -> List[str]:
    """Evidence references that speak to ``field_path``.

    Falls back to the whole record's evidence when no entry names the field:
    a withholding decision about a field the source never itemised is still
    grounded in the capture that shows the source not itemising it.
    """
    root = field_path.split(".", 1)[0]
    named = [str(e.get("evidence_ref")) for e in entries
             if isinstance(e, Mapping) and e.get("field") == root
             and e.get("evidence_ref")]
    if named:
        return sorted(set(named))
    return sorted({str(e.get("evidence_ref")) for e in entries
                   if isinstance(e, Mapping) and e.get("evidence_ref")})


def _migrate_withheld(record: Mapping, read: Mapping, decisions: Mapping,
                      market_id: str, identity_key: str,
                      evidence_entries: Sequence[Mapping],
                      out: RecordMigration) -> Dict[str, Any]:
    """Legacy prose -> reason-coded decisions, or nothing at all.

    The largest judgement block in the phase, and the one where the default
    must be to REMOVE rather than to keep: most legacy entries restate that the
    page said nothing, and an entry claiming a decision was made about a silent
    field tells a reader the hotel withheld something it never had.
    """
    rules = decisions.get("withheld_prose") or {}
    per_record = (decisions.get("records") or {}).get(
        record_key(market_id, identity_key)) or {}
    overrides = per_record.get("withheld_prose") or {}

    result: Dict[str, Any] = {}
    for path, entry in sorted((read.get("withheld_fields") or {}).items()):
        if isinstance(entry, Mapping) and entry.get("reason_code"):
            # Already canonical (Columbus's fee_conflict/fee_withheld arrive
            # this way from the reader). It still needs its evidence linked.
            new = dict(entry)
            if not new.get("evidence_refs"):
                new["evidence_refs"] = _refs_for_path(path, evidence_entries)
            result[path] = new
            out.withheld.append(path)
            continue

        prose = str(entry.get("reason") if isinstance(entry, Mapping) else entry)
        rule = overrides.get(path) or rules.get(prose_key(path, prose))
        if rule is None:
            out.unresolved.append(
                "withheld_fields.%s has no reviewed disposition: %r" % (path, prose))
            continue

        disposition = rule.get("disposition")
        if disposition == DISPOSITION_SILENCE:
            out.silence_dropped.append(path)
            continue
        if disposition == DISPOSITION_RESOLVED:
            # 1.2 can state the fact the legacy schema could not, so the
            # withholding is retired and the fact is published instead.
            out.reviewed.append("%s: %s" % (path, rule.get("note") or "resolved"))
            continue
        if disposition != DISPOSITION_WITHHOLD:
            out.unresolved.append("withheld_fields.%s has disposition %r, which is "
                                  "not one of %s" % (path, disposition, DISPOSITIONS))
            continue

        reason_code = rule.get("reason_code") or ""
        if reason_code == enums.SOURCE_SILENT:
            out.unresolved.append(
                "withheld_fields.%s uses SOURCE_SILENT, which is forbidden in a "
                "published record: silence is absence" % path)
            continue
        target = rule.get("path") or path
        result[target] = withholding.withheld(
            target, reason_code, rule.get("reason") or prose,
            _refs_for_path(target, evidence_entries))
        out.withheld.append(target)

    # A withholding the legacy record never recorded, added under review. The
    # corpus contains fields whose value the source DOES state in a form 1.2
    # cannot carry -- "$45 Non-Refundable Pet Fee Every 3 Nights" -- and leaving
    # those merely absent tells a reader the property said nothing, which is the
    # exact confusion between silence and withholding this phase removes.
    for path, rule in sorted((per_record.get("add_withheld") or {}).items()):
        reason_code = rule.get("reason_code") or ""
        if reason_code == enums.SOURCE_SILENT or not reason_code:
            out.unresolved.append("add_withheld.%s needs a reason code that is "
                                  "not SOURCE_SILENT" % path)
            continue
        result[path] = withholding.withheld(
            path, reason_code, rule.get("reason") or "",
            _refs_for_path(path, evidence_entries))
        out.withheld.append(path)
        out.reviewed.append("withheld_fields.%s added under review" % path)
    return result


def _migrate_species(legacy: Mapping, decisions: Mapping, market_id: str,
                     identity_key: str, out: RecordMigration) -> Dict[str, str]:
    """Prose species -> a state map, from a table decided once per spelling.

    ``"pets"`` yields nothing. The corpus contains five spellings and every one
    of them is decided explicitly in the decisions file; a spelling not in that
    table stops the record rather than being parsed here.
    """
    per_record = (decisions.get("records") or {}).get(
        record_key(market_id, identity_key)) or {}
    if "species" in per_record:
        out.reviewed.append("facts.species from record-level review")
        return dict(per_record["species"])

    prose = legacy.get("species_allowed")
    cats = legacy.get("cats_allowed")
    species: Dict[str, str] = {}
    if prose is not None:
        table = decisions.get("species") or {}
        mapped = table.get(str(prose))
        if mapped is None:
            out.unresolved.append("facts.species_allowed %r has no reviewed "
                                  "species mapping" % prose)
            return {}
        species.update(mapped)
        out.reviewed.append("facts.species from %r" % prose)

    if cats is not None:
        parsed = compat_readers.parse_bool(cats)
        if parsed is None:
            out.unresolved.append("facts.cats_allowed %r is not a boolean" % cats)
        elif parsed is False:
            species["cats"] = enums.SPECIES_PROHIBITED
            out.reviewed.append("facts.species.cats prohibited from cats_allowed")
        else:
            species["cats"] = enums.SPECIES_ACCEPTED
            out.reviewed.append("facts.species.cats accepted from cats_allowed")
    return species


def migrate_record(record: Mapping, *, market_id: str, decisions: Mapping,
                   package_schema: str = "") -> RecordMigration:
    """Migrate one legacy record to canonical 1.2, by patching."""
    name = record.get("name") or record.get("key") or ""
    identity_key = ptf_identity_key(name)
    out = RecordMigration(identity_key, name, market_id)
    out.old_schema = str(record.get("schema_version") or package_schema or "")

    per_record = (decisions.get("records") or {}).get(
        record_key(market_id, identity_key)) or {}

    # Already 1.2: idempotence path. Re-running must not rewrite anything, so
    # the record is returned as found rather than round-tripped through the
    # legacy reader, which would try to parse canonical objects as strings.
    if str(record.get("schema_version") or "") == enums.POLICY_SCHEMA_VERSION:
        out.record = copy.deepcopy(dict(record))
        out.computation_class = str(record.get("computation_class") or "")
        out.old_schema = enums.POLICY_SCHEMA_VERSION
        return out

    read = compat_readers.read_record(record, market_id=market_id).record
    legacy_facts = record.get("facts") or {}

    new = copy.deepcopy(dict(record))
    out.unowned_fields_kept = [k for k in new
                               if k not in OWNED_RECORD_KEYS]

    entries = _migrate_evidence(record.get("evidence") or (), out)

    facts: Dict[str, Any] = dict(read.get("facts") or {})
    if facts:
        out.mechanical.append("facts read as canonical 1.2 structures")

    species = _migrate_species(legacy_facts, decisions, market_id, identity_key, out)
    if species:
        facts["species"] = species

    # Tier roles are decided per tier, in the order the tiers appear, because
    # "$75 for 1-4 nights, $125 for 5+" and "$100 fee plus a $200 cleaning fee"
    # are the same shape with opposite meanings, and only the quote separates
    # them. A tier list whose length does not match the reviewed roles stops
    # the record rather than reusing the last decision.
    roles = per_record.get("tier_roles")
    tiers = facts.get("fee_tiers")
    # The legacy tier carried its basis in `stated_basis`, a key the reader
    # does not consume. Dropping it silently deleted "Per stay" from the one
    # ladder in Cleveland whose property actually states a basis, so the page
    # showed a stay-length ladder with no unit on it. The value is mapped
    # through the same frozen decomposition table every other basis uses.
    legacy_tiers = legacy_facts.get("fee_tiers") or ()
    if tiers and len(legacy_tiers) == len(tiers):
        for tier, legacy_tier in zip(tiers, legacy_tiers):
            if not (isinstance(legacy_tier, Mapping) and legacy_tier.get("basis_stated")):
                continue
            basis, _, _, recognised = compat_readers.decompose_fee_basis(
                legacy_tier.get("stated_basis"))
            if basis:
                tier["basis"] = basis
                out.mechanical.append("facts.fee_tiers basis from stated_basis")
            elif not recognised and legacy_tier.get("stated_basis"):
                out.unresolved.append(
                    "facts.fee_tiers stated_basis %r is not in the decomposition "
                    "table" % legacy_tier.get("stated_basis"))
    # The legacy tier already RECORDS whether it is a surcharge: PTF-COLUMBUS-
    # HYATT-002 reviewed those pages and set `additive`, and the renderer has
    # been publishing "$100 + $200" from it ever since. Absent has always meant
    # "this amount IS the charge for the band". So the role is derived from that
    # committed flag rather than re-decided here -- and a reviewed role that
    # CONTRADICTS it stops the record, which is how two Hyatt Place pages were
    # caught being called replacement prices when their own pages say the second
    # band is charged in addition.
    if tiers and len(legacy_tiers) == len(tiers):
        derived = [enums.ROLE_ADDITIONAL_CHARGE
                   if (isinstance(lt, Mapping) and lt.get("additive"))
                   else enums.ROLE_REPLACEMENT_PRICE for lt in legacy_tiers]
        if roles and list(roles) != derived:
            out.unresolved.append(
                "facts.fee_tiers reviewed roles %s contradict the committed "
                "additive flags, which derive %s" % (list(roles), derived))
        else:
            for tier, role in zip(tiers, derived):
                tier["role"] = role
            out.mechanical.append("facts.fee_tiers roles from committed additive "
                                  "flags: %s" % ", ".join(derived))
    elif tiers:
        if not roles:
            out.unresolved.append("facts.fee_tiers has %d tiers with no reviewed "
                                  "roles" % len(tiers))
        elif len(roles) != len(tiers):
            out.unresolved.append(
                "facts.fee_tiers has %d tiers but %d reviewed roles"
                % (len(tiers), len(roles)))
        else:
            for tier, role in zip(tiers, roles):
                tier["role"] = role
            out.reviewed.append("facts.fee_tiers roles: %s" % ", ".join(roles))

    # Reviewed structural overrides: weight moved out of an overloaded operator,
    # tier roles, other_charges, caps, allowances. Each is a decision recorded
    # against the quote that establishes it.
    for path, value in sorted((per_record.get("facts") or {}).items()):
        if value is None:
            facts.pop(path, None)
            out.reviewed.append("facts.%s removed under review" % path)
        else:
            facts[path] = copy.deepcopy(value)
            out.reviewed.append("facts.%s set under review" % path)

    statement = read.get("service_animal_statement") or {}
    if "service_animal_statement" in per_record:
        statement = copy.deepcopy(per_record["service_animal_statement"])
        out.reviewed.append("service_animal_statement from review")

    # A fact this migration CREATED under review needs its own pointer to the
    # sentence that establishes it -- otherwise the corpus contains a published
    # fact no evidence entry names, which is the one thing every evidence gate
    # exists to prevent. The quote is not written here: it must already appear,
    # verbatim, in the record's own captured page text, or no entry is added
    # and the fact is reported as unevidenced instead.
    _add_reviewed_evidence(record, per_record, facts, entries, out)

    withheld = _migrate_withheld(record, read, decisions, market_id,
                                 identity_key, entries, out)

    # Legacy fact keys that nothing consumed would leave 1.0 beside 1.2.
    unconsumed = sorted(k for k in legacy_facts
                        if k not in CONSUMED_LEGACY_FACT_KEYS)
    for key in unconsumed:
        out.unresolved.append("facts.%s is not consumed by this migration" % key)

    classification = classify(facts)
    out.computation_class = classification.computation_class

    new["schema_version"] = enums.POLICY_SCHEMA_VERSION
    new["identity_key"] = identity_key
    new["market_id"] = market_id
    new["facts"] = facts
    new["evidence"] = entries
    new["computation_class"] = classification.computation_class
    if withheld:
        new["withheld_fields"] = withheld
    else:
        new.pop("withheld_fields", None)
    if statement:
        new["service_animal_statement"] = statement
    else:
        new.pop("service_animal_statement", None)

    approval = _migrate_approval(record, per_record, new, entries, out)
    if approval:
        new["approval"] = approval
    else:
        new.pop("approval", None)

    out.record = new
    return out


#: Canonical fact names whose evidence was captured under a legacy field name.
#: The evidence text is never rewritten, so the alias is how a canonical fact
#: finds the quote it came from.
EVIDENCE_FIELD_ALIASES = {
    "species": "species_allowed",
    "combined_weight_limit": "weight_limit_combined",
    "other_charges": "cleaning_fee",
    "dimension_constraints": "general_restrictions",
}


def _add_reviewed_evidence(record: Mapping, per_record: Mapping,
                           facts: Mapping, entries: List[Dict[str, Any]],
                           out: RecordMigration) -> None:
    """Point a reviewed fact at the quote the reviewer read."""
    quote = str(per_record.get("quote") or "").strip()
    if not quote:
        return
    page = " ".join(str(record.get("evidence_quote") or "").split())
    named = {str(e.get("field")) for e in entries if isinstance(e, Mapping)}
    for key in sorted(per_record.get("facts") or {}):
        if facts.get(key) is None:
            continue
        if key in named or EVIDENCE_FIELD_ALIASES.get(key) in named:
            continue
        if " ".join(quote.split()) not in page:
            out.unresolved.append(
                "facts.%s was set under review but its quote is not contiguous "
                "in the record's captured page text" % key)
            continue
        entry = {"field": key, "quote": quote,
                 "source_url": record.get("source_url") or "",
                 "artifact_class": LEGACY_ARTIFACT_CLASS}
        entry["evidence_ref"] = evidence_ref_for(entry)
        entries.append(entry)
        out.evidence_refs_added += 1
        out.reviewed.append("evidence pointer added for facts.%s" % key)


def _migrate_approval(record: Mapping, per_record: Mapping, new: Mapping,
                      entries: Sequence[Mapping], out: RecordMigration
                      ) -> Dict[str, Any]:
    """Canonical, hash-bound approval -- never a back-dated one.

    A legacy decision string maps to its canonical form and keeps its caveats.
    A record with NO decision does not acquire one here: the decisions file
    must carry a review performed today, recorded as LEGACY_BASELINE_REVIEWED
    with a real date and a real operator, or the record is reported as lacking
    an approval rather than given one it never received.
    """
    legacy = record.get("approval")
    decided = per_record.get("approval")

    if decided:
        approval = copy.deepcopy(dict(decided))
        out.approval_change = "recorded %s" % approval.get("decision")
    elif isinstance(legacy, Mapping) and (legacy.get("decision") or "").strip():
        mapped = enums.LEGACY_APPROVAL_DECISIONS.get(legacy["decision"])
        if mapped is None:
            out.unresolved.append("approval.decision %r is not in the legacy map"
                                  % legacy["decision"])
            return dict(legacy)
        approval = {"decision": mapped,
                    "operator": legacy.get("operator") or "",
                    "approval_date": legacy.get("approval_date") or ""}
        caveat = enums.LEGACY_APPROVAL_CAVEATS.get(legacy["decision"])
        if caveat:
            approval["caveats"] = [caveat]
        out.approval_change = "%s -> %s" % (legacy["decision"], mapped)
    else:
        out.unresolved.append(
            "no approval decision; record a review performed today as "
            "LEGACY_BASELINE_REVIEWED in the decisions file")
        return {}

    # Hash binding is computed over the migrated record MINUS its approval, so
    # signing cannot change what was signed.
    signed = {k: v for k, v in new.items() if k != "approval"}
    approval["record_hash"] = record_hash(signed)
    approval["evidence_hash"] = evidence_hash(entries)
    return approval


# --------------------------------------------------------------------------- #
# Package migration.
# --------------------------------------------------------------------------- #

def migrate_package(document: Mapping, market_id: str, decisions: Mapping
                    ) -> Tuple[Dict[str, Any], List[RecordMigration]]:
    """Migrate a whole ``hotel_policy_facts`` document. Patch semantics."""
    package_schema = str(document.get("schema_version") or "")
    results = [migrate_record(r, market_id=market_id, decisions=decisions,
                              package_schema=package_schema)
               for r in document.get("hotels") or ()]
    new = copy.deepcopy(dict(document))
    new["schema_version"] = enums.POLICY_SCHEMA_VERSION
    new["market_id"] = market_id
    new["hotels"] = [r.record for r in results]
    return new, results


def validate_migrated(document: Mapping) -> List[str]:
    """Every contract's verdict on the migrated package, in one list."""
    problems = [str(i) for i in policy_schema.validate_package(document)]
    for record in document.get("hotels") or ():
        label = record.get("identity_key") or record.get("key") or "?"
        for issue in withholding.validate(record):
            problems.append("%s: %s" % (label, issue))
        for issue in evidence_contract.validate(record):
            problems.append("%s: %s" % (label, issue))
        stale = _computation_disagreement(record)
        if stale:
            problems.append("%s: %s" % (label, stale))
    return problems


def _computation_disagreement(record: Mapping) -> str:
    """A stored computation class that no longer matches recomputation."""
    stored = record.get("computation_class")
    if stored is None:
        return "computation_class is missing"
    recomputed = classify(record.get("facts") or {}).computation_class
    if stored != recomputed:
        return ("computation_class %r disagrees with recomputation %r"
                % (stored, recomputed))
    return ""


def write_package(document: Mapping, market_id: str) -> Path:
    path = PACKAGE_DIR / POLICY_PACKAGES[market_id]
    path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8", newline="\n")
    return path


def load_package(market_id: str) -> Dict[str, Any]:
    path = PACKAGE_DIR / POLICY_PACKAGES[market_id]
    return json.loads(path.read_text(encoding="utf-8-sig"))


# --------------------------------------------------------------------------- #
# CLI.
# --------------------------------------------------------------------------- #

def run(market_id: str, *, write: bool = False,
        decisions: Optional[Mapping] = None) -> Tuple[Dict[str, Any], List[RecordMigration]]:
    decisions = decisions if decisions is not None else load_decisions()
    document = load_package(market_id)
    migrated, results = migrate_package(document, market_id, decisions)
    problems = validate_migrated(migrated)

    blocked = [r for r in results if r.status == BLOCKED]
    print("=== %s: %d records" % (market_id, len(results)))
    counts: "OrderedDict[str, int]" = OrderedDict()
    for result in results:
        counts[result.status] = counts.get(result.status, 0) + 1
    for status, count in counts.items():
        print("  %-28s %d" % (status, count))
    classes: "OrderedDict[str, int]" = OrderedDict()
    for result in results:
        classes[result.computation_class] = classes.get(result.computation_class, 0) + 1
    for cls, count in sorted(classes.items()):
        print("  computation %-40s %d" % (cls, count))
    print("  silence markers removed :", sum(len(r.silence_dropped) for r in results))
    print("  withheld fields kept    :", sum(len(r.withheld) for r in results))
    print("  evidence refs added     :", sum(r.evidence_refs_added for r in results))
    print("  schema/contract problems:", len(problems))
    for problem in problems[:15]:
        print("      ", problem[:150])
    if blocked:
        print("  BLOCKED records         :", len(blocked))
        for result in blocked[:15]:
            print("      %s: %s" % (result.identity_key, result.unresolved[:2]))

    if write and not blocked and not problems:
        path = write_package(migrated, market_id)
        print("  written:", path)
    elif write:
        print("  NOT WRITTEN: resolve the problems above first")
    return migrated, results


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--market", action="append", dest="markets",
                        help="market id (repeatable); default all three")
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)

    markets = args.markets or list(POLICY_PACKAGES)
    decisions = load_decisions()
    for market_id in markets:
        run(market_id, write=args.write, decisions=decisions)
    return 0


if __name__ == "__main__":                            # pragma: no cover
    raise SystemExit(main())
