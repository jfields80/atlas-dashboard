"""What may back a published fact.

The rule everything here serves
-------------------------------
Hashing a transcription proves the TYPING was not altered. It proves nothing
about what the webpage said. A CSV of operator-typed policy text, however
carefully hash-bound, is a record of someone's keyboard -- and a fact published
from it is a fact whose only witness is the person who entered it.

Cleveland reached this conclusion the hard way and wrote it down: its
work-browser package is classified ``OPERATOR_TRANSCRIBED_BROWSER_REVIEW`` with
``publishable_without_a_page_artifact: false``, and its screenshot census found
135 directories containing 0 image files. Seventy-one rows carry a known policy
wording that cannot publish. That determination was correct, and this module
makes it universal rather than one market's local discipline.

Refusal before claim
--------------------
Where no publication-grade artifact exists, the correct output is a blocker
state -- never a lower-confidence fact. A market with zero published hotels and
an honest partition is in better standing than one with forty records backed by
transcriptions.

An ACCESS_BLOCKED verdict is itself evidence-bearing and must be probed rather
than assumed: a fabricated property code returns the same 403 as a real one, so
a refusal proves nothing about the property. The blocker records the FETCH
OUTCOME, never a conclusion about the hotel.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, FrozenSet, List, Mapping, Sequence, Tuple

from scripts.pettripfinder.contracts import enums
from scripts.pettripfinder.contracts.policy_schema import Issue

#: Fields every publication-grade evidence entry must carry. Each exists
#: because its absence has actually let something wrong through.
PUBLICATION_GRADE_REQUIRED: Tuple[str, ...] = (
    "evidence_ref",     # so withholding decisions and facts can cite it
    "field",            # per-field, never one blanket citation per record
    "quote",            # the source's own words, contiguous
    "source_url",       # where it was read
    "source_grade",     # how much authority that source carries
    "artifact_class",   # what kind of artifact this is
    "artifact_sha256",  # hash of the PAGE, not of a row about the page
    "artifact_kind",    # rendered page, operator screenshot, or PDF
    "captured_at",
)

#: Canonical fact key -> the evidence field names that may cite it.
#:
#: Schema 1.2 renamed several FACT keys without renaming the EVIDENCE field that
#: supports them, so a fact whose citation sits in the same record under the old
#: name read as uncited. The corpus proves this is a vocabulary seam and not
#: missing evidence: across Dayton and Cleveland together, every fact reported
#: uncited resolves through this map and none is cited under neither name.
#:
#: An alias is a SECOND acceptable name, never a replacement. A field always
#: cites itself -- ``coverage_names`` includes the canonical key -- so a market
#: that authors a direct pointer keeps it, and one that carries only the legacy
#: name is no longer accused of publishing an unevidenced fact.
#:
#: What this deliberately does NOT do is rewrite anything. Renaming a committed
#: evidence field would move ``evidence_ref``, and therefore ``evidence_hash``,
#: and therefore every approval bound to it, across three markets -- to fix a
#: reader. So the reader learns the alias and the records are left alone.
FACT_EVIDENCE_ALIASES: Dict[str, Tuple[str, ...]] = {
    # A species map is authored from the prose list and the cats boolean.
    "species": ("species_allowed", "cats_allowed"),
    # A combined limit and its operator are two entries for one constraint.
    "combined_weight_limit": ("weight_limit_combined",
                              "weight_limit_combined_operator"),
    # Height/length constraints are read out of the restriction sentence.
    "dimension_constraints": ("general_restrictions",),
    # A named charge is cited by the charge it names.
    "other_charges": ("cleaning_fee", "pet_deposit"),
}


def coverage_names(field: str) -> Tuple[str, ...]:
    """Every evidence-field name that counts as citing ``field``.

        >>> coverage_names("species")
        ('species', 'species_allowed', 'cats_allowed')
        >>> coverage_names("pet_fee")
        ('pet_fee',)
    """
    return (field,) + FACT_EVIDENCE_ALIASES.get(field, ())


#: Capability -> the artifact classes that hold it.
CAPABILITY_MATRIX: Dict[str, FrozenSet[str]] = {
    "publish_facts": enums.MAY_PUBLISH_FACTS,
    "propose_facts": enums.MAY_PROPOSE_FACTS,
    "propose_routing": enums.MAY_PROPOSE_ROUTING,
    "confirm_identity": enums.MAY_CONFIRM_IDENTITY,
}


@dataclass(frozen=True)
class EvidenceEntry:
    """One evidence record, normalised."""

    evidence_ref: str
    field: str
    quote: str
    source_url: str
    source_grade: str
    artifact_class: str
    artifact_sha256: str
    artifact_kind: str
    captured_at: str
    capture_method: str = ""
    value: Any = None

    @property
    def may_publish(self) -> bool:
        return self.artifact_class in enums.MAY_PUBLISH_FACTS

    @property
    def is_first_party(self) -> bool:
        return self.source_grade in enums.FIRST_PARTY_GRADES


def can(artifact_class: str, capability: str) -> bool:
    """Whether an artifact class holds a capability.

        >>> can("TRANSCRIPTION_ONLY", "publish_facts")
        False
        >>> can("TRANSCRIPTION_ONLY", "propose_routing")
        True
    """
    if capability not in CAPABILITY_MATRIX:
        raise KeyError("unknown capability %r; known: %s"
                       % (capability, sorted(CAPABILITY_MATRIX)))
    return artifact_class in CAPABILITY_MATRIX[capability]


def parse(entries: Sequence[Mapping]) -> Tuple[EvidenceEntry, ...]:
    """Read an evidence array into typed entries, tolerating legacy shapes."""
    out: List[EvidenceEntry] = []
    for entry in entries or ():
        if not isinstance(entry, Mapping):
            continue
        out.append(EvidenceEntry(
            evidence_ref=str(entry.get("evidence_ref") or ""),
            field=str(entry.get("field") or ""),
            quote=str(entry.get("quote") or ""),
            source_url=str(entry.get("source_url") or ""),
            source_grade=str(entry.get("source_grade") or ""),
            artifact_class=str(entry.get("artifact_class") or ""),
            artifact_sha256=str(entry.get("artifact_sha256") or ""),
            artifact_kind=str(entry.get("artifact_kind") or ""),
            captured_at=str(entry.get("captured_at") or ""),
            capture_method=str(entry.get("capture_method") or ""),
            value=entry.get("value"),
        ))
    return tuple(out)


def quote_is_contiguous(quote: str, artifact_text: str) -> bool:
    """Whether ``quote`` appears verbatim and unbroken in the artifact.

    A stitched quote is a forgery. A prior sprint passed a naive substring
    check with halves nine thousand characters apart, producing a "quotation"
    the page never contained -- so contiguity is ASSERTED here rather than
    assumed by testing the pieces separately.

    Whitespace is collapsed on both sides before comparison because rendered
    HTML wraps text unpredictably; nothing else is normalised, since altering
    the words is the thing being guarded against.
    """
    if not quote.strip():
        return False
    needle = " ".join(quote.split())
    haystack = " ".join((artifact_text or "").split())
    return needle in haystack


def validate_entry(entry: Mapping, index: int) -> Tuple[Issue, ...]:
    """Validate one evidence entry."""
    out: List[Issue] = []
    path = "evidence[%d]" % index
    if not isinstance(entry, Mapping):
        return (Issue(path, "NOT_OBJECT", "an evidence entry must be an object"),)

    cls = entry.get("artifact_class")
    if not enums.is_member(cls if isinstance(cls, str) else "",
                           enums.ARTIFACT_CLASSES):
        out.append(Issue(path + ".artifact_class", "BAD_ENUM",
                         "%r not in %s" % (cls, list(enums.ARTIFACT_CLASSES))))
        return tuple(out)

    grade = entry.get("source_grade")
    if grade is not None and not enums.is_member(grade, enums.SOURCE_GRADES):
        out.append(Issue(path + ".source_grade", "BAD_ENUM",
                         "%r not in %s" % (grade, list(enums.SOURCE_GRADES))))

    kind = entry.get("artifact_kind")
    if kind and not enums.is_member(kind, enums.ARTIFACT_KINDS):
        out.append(Issue(path + ".artifact_kind", "BAD_ENUM",
                         "%r not in %s" % (kind, list(enums.ARTIFACT_KINDS))))

    if cls != enums.PUBLICATION_GRADE_EVIDENCE:
        return tuple(out)

    for required in PUBLICATION_GRADE_REQUIRED:
        if not entry.get(required):
            out.append(Issue("%s.%s" % (path, required), "MISSING_REQUIRED",
                             "%s is mandatory for publication-grade evidence"
                             % required))

    if grade and grade not in enums.FIRST_PARTY_GRADES:
        out.append(Issue(path + ".source_grade", "NOT_FIRST_PARTY",
                         "publication-grade evidence must be first-party; "
                         "%s may propose but never publish" % grade))
    return tuple(out)


def validate(record: Mapping) -> Tuple[Issue, ...]:
    """Validate a record's evidence array and its fitness to publish."""
    out: List[Issue] = []
    entries = record.get("evidence")
    if entries is None:
        return (Issue("evidence", "MISSING_REQUIRED",
                      "a record with no evidence cannot be reviewed"),)
    if not isinstance(entries, Sequence) or isinstance(entries, (str, bytes)):
        return (Issue("evidence", "NOT_LIST", "evidence must be a list"),)

    for index, entry in enumerate(entries):
        out.extend(validate_entry(entry, index))

    parsed = parse(entries)
    seen: Dict[str, int] = {}
    for entry in parsed:
        if entry.evidence_ref:
            seen[entry.evidence_ref] = seen.get(entry.evidence_ref, 0) + 1
    for ref, count in sorted(seen.items()):
        if count > 1:
            out.append(Issue("evidence", "DUPLICATE_REF",
                             "%d entries share evidence_ref %r" % (count, ref)))
    return tuple(out)


def unevidenced_facts(record: Mapping) -> Tuple[str, ...]:
    """Published fact fields with no evidence entry citing them.

    A published fact with no evidence is unverifiable by definition. Fields
    marked as derived in ``derived_fields`` are exempt, because a derivation is
    a declared computation rather than a claim about a source.

    A fact is cited by its own name OR by any of its ``FACT_EVIDENCE_ALIASES``;
    matching field names literally reported 43 records across two markets as
    publishing an unevidenced fact when the citation was sitting in the same
    record under the name schema 1.2 renamed away from. What this does not
    soften is the actual question: a fact cited under neither its own name nor
    an approved alias is still reported, which is the whole point of the check.
    """
    facts = record.get("facts") or {}
    if not isinstance(facts, Mapping):
        return ()
    cited = {e.field for e in parse(record.get("evidence") or ()) if e.field}
    declared = set(record.get("derived_fields") or ())
    return tuple(sorted(
        field for field in facts
        if field not in declared
        and not cited.intersection(coverage_names(field))))


def publication_blockers(record: Mapping) -> Tuple[str, ...]:
    """Every reason this record may not publish, evidence-wise.

    Returns an empty tuple when the record is publishable. Deliberately
    exhaustive rather than short-circuiting: a reviewer fixing one blocker
    should see the others in the same pass.
    """
    blockers: List[str] = []
    parsed = parse(record.get("evidence") or ())

    publishable = [e for e in parsed if e.may_publish]
    if not publishable:
        classes = sorted({e.artifact_class for e in parsed}) or ["<none>"]
        blockers.append(
            "no publication-grade evidence; the record carries only %s"
            % ", ".join(classes))

    if any(e.artifact_class == enums.TRANSCRIPTION_ONLY for e in parsed) \
            and not publishable:
        blockers.append(
            "the policy wording is known only from a transcription; hashing a "
            "transcription binds the typing, not the page")

    for entry in publishable:
        if not entry.artifact_sha256:
            blockers.append("evidence %r has no artifact hash" % entry.evidence_ref)
        if not entry.is_first_party:
            blockers.append("evidence %r is not first-party" % entry.evidence_ref)

    missing = unevidenced_facts(record)
    if missing:
        blockers.append("published fact(s) with no evidence: %s"
                        % ", ".join(missing))
    return tuple(blockers)
