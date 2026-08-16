"""What "we are not publishing this" means, and what it requires.

The defect this closes
----------------------
``withheld_fields`` is written by six integration scripts and read by NO
renderer. Sixty-six records across Cleveland and Dayton carry deliberate,
carefully reasoned withholding decisions that reach the public as the generic
dim "Not stated by the reviewed source" -- telling a reader the hotel said
nothing when in fact the hotel contradicted itself and we declined to publish
the contradiction. The discipline those two markets built correctly currently
buys nothing.

Its stored shape is also weaker than it looks: a flat ``{field: "prose"}`` map
with no reason code and no evidence reference, so nothing can group, query or
re-adjudicate it.

    "courtyard by marriott dayton north": {
      "fee_scope": "the page states an amount without saying whether it is
                    charged per pet or per room",
      "pet_count_limit": "the page states no pet count"
    }

Note what those two entries actually are: the first is a real ambiguity, the
second is a restatement of silence. Under this contract they diverge -- one
becomes a withheld field, the other becomes ABSENCE.

The rule that makes the structure worth having
----------------------------------------------
``withheld_fields`` means exactly one thing: WE KNOW SOMETHING AND ARE CHOOSING
NOT TO PUBLISH IT. ``SOURCE_SILENT`` is therefore invalid inside it. Admitting
silence would make the map a mixture of editorial decisions and non-events,
force every consumer to read the reason code to tell which, and require a
sparse brand page to enumerate fifteen entries of nothing.

The public consequence, which the renderer contract must honour: "Not stated"
and "Stated, but withheld because the source contradicts itself" are different
claims about a hotel and must never share a visual treatment.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Sequence, Tuple

from scripts.pettripfinder.contracts import enums
from scripts.pettripfinder.contracts.policy_schema import Issue

#: Public copy per reason. Kept beside the taxonomy rather than in the renderer
#: so that adding a reason code without deciding what a reader is told is a
#: visible omission rather than a silent fallback to the silence string.
PUBLIC_COPY: Dict[str, str] = {
    enums.SOURCE_AMBIGUOUS:
        "The hotel's wording is unclear on this.",
    enums.SOURCE_CONTRADICTORY:
        "The hotel's own page states conflicting terms.",
    enums.SCHEMA_CANNOT_REPRESENT:
        "The hotel states terms we cannot summarise accurately.",
    enums.ARTIFACT_INSUFFICIENT: "",
    enums.IDENTITY_NOT_CONFIRMED: "",
}

#: What silence renders as. Present here only so a test can assert that no
#: withheld copy is ever equal to it.
NOT_STATED_COPY = "Not stated by the reviewed source"

#: CSS classes the renderer contract requires to be distinct.
WITHHELD_CSS_CLASS = "ptf-withheld"
NOT_STATED_CSS_CLASS = "ptf-unknown"


@dataclass(frozen=True)
class WithheldField:
    """One withholding decision, normalised."""

    path: str
    reason_code: str
    reason: str
    evidence_refs: Tuple[str, ...]
    withheld_at: str = ""
    withheld_by: str = ""
    #: PTF-POLICY-SCHEMA-MIGRATION-001A. The sentence THIS decision shows a
    #: reader, where the generic one for its reason code would be too vague to
    #: act on. "The hotel's own page states conflicting terms" is true of every
    #: contradiction; it does not tell a guest that the conflict is between a
    #: nightly rate and a per-stay rate, which is the part they can ask about.
    public_copy: str = ""
    #: The same decision's wording for a table CELL, where a sentence will not
    #: fit. "Range by stay" is right for a $75-$150 spread and wrong for a fee
    #: charged every three nights; one short label cannot serve both.
    public_label: str = ""

    @property
    def blocks_record(self) -> bool:
        """True when this reason says the evidence CHAIN is broken.

        A record cannot publish some facts from a chain it does not trust for
        others, so these reasons disqualify the whole record rather than one
        field.
        """
        return self.reason_code in enums.RECORD_BLOCKING_REASONS

    @property
    def reader_copy(self) -> str:
        """This decision's own sentence, or the generic one for its code."""
        return self.public_copy or PUBLIC_COPY.get(self.reason_code, "")


def withheld(path: str, reason_code: str, reason: str,
             evidence_refs: Sequence[str], *, withheld_at: str = "",
             withheld_by: str = "", public_copy: str = "",
             public_label: str = "") -> Dict[str, Any]:
    """Build a canonical withheld-field entry."""
    entry: Dict[str, Any] = {
        "reason_code": reason_code,
        "reason": reason,
        "evidence_refs": list(evidence_refs),
    }
    if public_copy:
        entry["public_copy"] = public_copy
    if public_label:
        entry["public_label"] = public_label
    if withheld_at:
        entry["withheld_at"] = withheld_at
    if withheld_by:
        entry["withheld_by"] = withheld_by
    return entry


def parse(withheld_fields: Mapping) -> Tuple[WithheldField, ...]:
    """Read a ``withheld_fields`` map into typed decisions.

    Tolerant on purpose: malformed entries are surfaced by ``validate``, and a
    caller that wants to survey the corpus should not have to catch parse
    errors record by record.
    """
    out: List[WithheldField] = []
    for path, entry in sorted((withheld_fields or {}).items()):
        if isinstance(entry, Mapping):
            refs = entry.get("evidence_refs") or ()
            out.append(WithheldField(
                path=path,
                reason_code=str(entry.get("reason_code") or ""),
                reason=str(entry.get("reason") or ""),
                evidence_refs=tuple(str(r) for r in refs),
                withheld_at=str(entry.get("withheld_at") or ""),
                withheld_by=str(entry.get("withheld_by") or ""),
                public_copy=str(entry.get("public_copy") or ""),
                public_label=str(entry.get("public_label") or ""),
            ))
        else:
            # The legacy flat-prose shape. Recorded with an empty reason code
            # so the migration report can count it rather than crash on it.
            out.append(WithheldField(path=path, reason_code="",
                                     reason=str(entry), evidence_refs=()))
    return tuple(out)


def _root_field(path: str) -> str:
    """``pet_fee.scope`` -> ``pet_fee``.

    Dotted sub-paths are permitted so a record can publish a fee amount while
    withholding its scope -- the single commonest real shape in the corpus.
    """
    return path.split(".", 1)[0]


def validate(record: Mapping) -> Tuple[Issue, ...]:
    """Validate a record's withholding block against the frozen contract."""
    out: List[Issue] = []
    block = record.get("withheld_fields")
    if block is None:
        return ()
    if not isinstance(block, Mapping):
        return (Issue("withheld_fields", "NOT_OBJECT",
                      "withheld_fields must be a map of field path to decision"),)

    facts = record.get("facts") or {}
    known_refs = {str(e.get("evidence_ref")) for e in (record.get("evidence") or ())
                  if isinstance(e, Mapping) and e.get("evidence_ref")}

    for decision in parse(block):
        path = "withheld_fields.%s" % decision.path

        if not decision.reason_code:
            out.append(Issue(path, "MISSING_REASON_CODE",
                             "a withholding decision needs a reason code; "
                             "prose alone cannot be grouped or re-adjudicated"))
        elif decision.reason_code == enums.SOURCE_SILENT:
            # The rule that gives the structure its meaning.
            out.append(Issue(
                path, "SILENCE_IS_NOT_WITHHOLDING",
                "SOURCE_SILENT is invalid here: genuine silence is the ABSENCE "
                "of the field, not an entry claiming a decision was made"))
        elif not enums.is_member(decision.reason_code,
                                 tuple(sorted(enums.WITHHELD_FIELD_REASONS))):
            out.append(Issue(path, "BAD_REASON_CODE",
                             "%r is not a withholding reason"
                             % decision.reason_code))

        if not decision.reason.strip():
            out.append(Issue(path, "MISSING_REASON",
                             "a reviewer needs the sentence, not only the code"))

        if not decision.evidence_refs:
            # A withholding decision with no evidence is unreviewable, and
            # cannot be re-adjudicated when a better capture arrives.
            out.append(Issue(path, "MISSING_EVIDENCE_REFS",
                             "at least one evidence_ref is required"))
        else:
            for ref in decision.evidence_refs:
                if known_refs and ref not in known_refs:
                    out.append(Issue(path, "DANGLING_EVIDENCE_REF",
                                     "evidence_ref %r is not in this record's "
                                     "evidence" % ref))

        # A field present in both would leak into the comparison table, the
        # JSON-LD and every fee filter while the profile claims it is withheld.
        root = _root_field(decision.path)
        if root in facts:
            if "." not in decision.path:
                out.append(Issue(path, "WITHHELD_BUT_PRESENT",
                                 "%r is withheld yet present in facts" % root))
            else:
                leaf = decision.path.split(".", 1)[1]
                container = facts.get(root)
                if isinstance(container, Mapping) and leaf in container:
                    out.append(Issue(path, "WITHHELD_BUT_PRESENT",
                                     "%r is withheld yet present in facts"
                                     % decision.path))
    return tuple(out)


def blocks_publication(record: Mapping) -> Tuple[str, ...]:
    """Reasons this record may not publish at all.

    ``ARTIFACT_INSUFFICIENT`` and ``IDENTITY_NOT_CONFIRMED`` both say the
    evidence chain is broken. A record cannot publish some facts from a chain
    it distrusts for others, so these disqualify the record rather than the
    field.
    """
    return tuple(
        "%s is withheld as %s, which blocks the whole record"
        % (d.path, d.reason_code)
        for d in parse(record.get("withheld_fields") or {})
        if d.blocks_record)


def render_state(record: Mapping, field_path: str) -> str:
    """What the public surface must show for one field.

    Returns ``"stated"``, ``"withheld"`` or ``"not_stated"``. The renderer
    contract requires the last two to differ in both copy and CSS class -- they
    are different claims about a hotel, and sharing the dim silence treatment
    between them is the current defect in code form.
    """
    facts = record.get("facts") or {}
    root = _root_field(field_path)
    if "." in field_path:
        container = facts.get(root)
        leaf = field_path.split(".", 1)[1]
        if isinstance(container, Mapping) and leaf in container:
            return "stated"
    elif root in facts:
        return "stated"
    if field_path in (record.get("withheld_fields") or {}):
        return "withheld"
    return "not_stated"
