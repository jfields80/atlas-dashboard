"""PTF-APPROVAL-RESOLUTION -- letting a human resolve a specific false positive
without letting anyone switch the detector off.

The contradiction detector scans the WHOLE page, which is what makes it useful
and also what makes it noisy. Two La Quinta properties state one unambiguous
price each -- "25 USD per pet per night. Max 75 USD per stay" -- and the
scanner reports `conflicting_fee_basis_per_pet_vs_fee_basis_per_night` because
those words all appear, alongside a rewards banner and booking boilerplate it
also read. The promoter then withholds the fee, and the site tells a reader we
could not determine a price the hotel states plainly.

An approver can already write "those markers are artifacts" in a rationale.
Nothing downstream could act on it, because prose is not a decision a program
can check. This module is the checkable form of that decision.

WHAT IT IS CAREFUL NOT TO BE
---------------------------
* Not a way to ignore contradictions in general. A resolution names the exact
  markers it disposes of; anything unresolved still withholds.
* Not transferable. It is bound to one attestation ID *and* its content hash,
  so it cannot survive a re-capture, and it cannot be moved to another hotel.
* Not inferable from prose. A rationale with no structured resolution
  authorises nothing, and there is a test that says so.
* Not a deletion. The detector's original markers stay on the attestation
  exactly as recorded; a resolution is stored beside them, never instead.
"""

from __future__ import annotations

import re
from typing import Dict, List, Mapping, Sequence, Tuple

#: Marker families a human may dispose of. Deliberately a closed list: a new
#: family is a new decision about what a person is allowed to overrule, and
#: should be made deliberately rather than inherited by prefix matching.
FAMILY_FEE_BASIS = "conflicting_fee_basis"
FAMILY_SPECIES = "conflicting_species"
RESOLVABLE_FAMILIES = (FAMILY_FEE_BASIS, FAMILY_SPECIES)

#: What the approver is saying. Both mean "do not withhold on this", and they
#: differ in WHY, which a later reviewer will want to know.
DISPOSITION_FALSE_POSITIVE = "false_positive"
DISPOSITION_NOT_A_POLICY_CONFLICT = "not_a_policy_conflict"
DISPOSITIONS = (DISPOSITION_FALSE_POSITIVE, DISPOSITION_NOT_A_POLICY_CONFLICT)

APPROVAL_APPROVED = "APPROVED"

#: Every field a resolution must carry to be actionable.
REQUIRED_FIELDS = (
    "marker_family", "markers", "disposition", "approver_id",
    "approval_record_id", "attestation_id", "attestation_hash",
    "rationale", "resolved_at",
)

MIN_RATIONALE_CHARS = 40

_HASH_RE = re.compile(r"^sha256:[0-9a-f]{32,64}$")


class ResolutionError(ValueError):
    """A resolution that cannot be trusted. Always carries the reason."""


def family_of(marker: str) -> str:
    """The family a detector marker belongs to, or "" if it is not resolvable."""
    m = (marker or "").strip()
    for family in RESOLVABLE_FAMILIES:
        if m.startswith(family):
            return family
    return ""


def build_resolution(*, markers: Sequence[str], disposition: str,
                     approver_id: str, approval_record_id: str,
                     attestation_id: str, attestation_hash: str,
                     rationale: str, resolved_at: str) -> Dict:
    """One structured resolution, validated at construction.

    Raises rather than returning something half-formed: a resolution is a
    safety decision, and a partially-specified one is not a weaker decision,
    it is not a decision.
    """
    markers = [str(m).strip() for m in markers if str(m).strip()]
    if not markers:
        raise ResolutionError("a resolution must name at least one marker")
    families = {family_of(m) for m in markers}
    if "" in families:
        bad = sorted(m for m in markers if not family_of(m))
        raise ResolutionError("markers outside the resolvable families: %s" % bad)
    if len(families) != 1:
        raise ResolutionError("one resolution covers one family, got %s"
                              % sorted(families))
    if disposition not in DISPOSITIONS:
        raise ResolutionError("disposition must be one of %s" % (DISPOSITIONS,))
    if len((rationale or "").strip()) < MIN_RATIONALE_CHARS:
        raise ResolutionError("rationale must explain the decision (>= %d chars)"
                              % MIN_RATIONALE_CHARS)
    if not _HASH_RE.match(attestation_hash or ""):
        raise ResolutionError("attestation_hash must be a sha256:<hex> digest")
    for name, value in (("approver_id", approver_id),
                        ("approval_record_id", approval_record_id),
                        ("attestation_id", attestation_id),
                        ("resolved_at", resolved_at)):
        if not (value or "").strip():
            raise ResolutionError("%s is required" % name)

    return {
        "marker_family": families.pop(),
        "markers": sorted(set(markers)),
        "disposition": disposition,
        "approver_id": approver_id.strip(),
        "approval_record_id": approval_record_id.strip(),
        "attestation_id": attestation_id.strip(),
        "attestation_hash": attestation_hash.strip(),
        "rationale": rationale.strip(),
        "resolved_at": resolved_at.strip(),
    }


def validate_resolution(resolution: Mapping) -> Tuple[bool, str]:
    """Structural check of a STORED resolution. ``(ok, reason)``."""
    if not isinstance(resolution, Mapping):
        return (False, "resolution_not_an_object")
    for field in REQUIRED_FIELDS:
        if field not in resolution:
            return (False, "missing_field:%s" % field)
    if resolution["disposition"] not in DISPOSITIONS:
        return (False, "unknown_disposition:%s" % resolution["disposition"])
    markers = resolution.get("markers") or []
    if not isinstance(markers, (list, tuple)) or not markers:
        return (False, "no_markers")
    families = {family_of(str(m)) for m in markers}
    if families != {resolution["marker_family"]}:
        return (False, "markers_do_not_match_family")
    if resolution["marker_family"] not in RESOLVABLE_FAMILIES:
        return (False, "family_not_resolvable:%s" % resolution["marker_family"])
    if len(str(resolution.get("rationale") or "").strip()) < MIN_RATIONALE_CHARS:
        return (False, "rationale_too_short")
    if not _HASH_RE.match(str(resolution.get("attestation_hash") or "")):
        return (False, "attestation_hash_malformed")
    return (True, "")


def resolutions_for(record: Mapping) -> Tuple[Dict, ...]:
    """Every stored resolution on an attestation record."""
    approval = record.get("approval") or {}
    got = approval.get("resolutions") or []
    return tuple(r for r in got if isinstance(r, Mapping))


def resolved_markers(record: Mapping) -> Tuple[str, ...]:
    """Markers this record's approval actually authorises ignoring.

    Fails closed at every step: a record that is not APPROVED, not publishable,
    or whose resolution does not match its own id and hash authorises nothing.
    """
    approval = record.get("approval") or {}
    if approval.get("state") != APPROVAL_APPROVED:
        return ()
    if not record.get("publishable"):
        return ()

    att_id = str(record.get("attestation_id") or "")
    att_hash = str(record.get("attestation_hash") or "")
    if not att_id or not _HASH_RE.match(att_hash):
        return ()

    out: List[str] = []
    for res in resolutions_for(record):
        ok, _ = validate_resolution(res)
        if not ok:
            continue
        # Bound to THIS attestation, by id and by content hash. A re-capture
        # changes the hash, and the resolution stops applying -- which is the
        # point: it was a judgement about evidence somebody actually read.
        if str(res.get("attestation_id")) != att_id:
            continue
        if str(res.get("attestation_hash")) != att_hash:
            continue
        if str(res.get("approval_record_id")) != str(approval.get("approval_record_id")):
            continue
        out.extend(str(m) for m in res.get("markers") or [])
    return tuple(sorted(set(out)))


def family_fully_resolved(record: Mapping, family: str) -> bool:
    """Is EVERY recorded marker in this family resolved?

    Partial resolution is not resolution. If a detector reported three
    fee-basis conflicts and a human disposed of two, something in that field is
    still contested and the value stays withheld.
    """
    recorded = [str(m) for m in (record.get("contradictions") or [])
                if family_of(str(m)) == family]
    if not recorded:
        return False
    resolved = set(resolved_markers(record))
    return all(m in resolved for m in recorded)


def authorizing_resolution(record: Mapping, family: str) -> Dict:
    """The resolution that authorised a family, for the audit trail. {} if none."""
    if not family_fully_resolved(record, family):
        return {}
    for res in resolutions_for(record):
        if res.get("marker_family") == family:
            ok, _ = validate_resolution(res)
            if ok:
                return dict(res)
    return {}


def attach_resolutions(record: Dict, resolutions: Sequence[Mapping]) -> Dict:
    """Add resolutions to an ALREADY-APPROVED record, additively.

    Returns a NEW record. The attested content is untouched -- so the hash is
    unchanged and still describes exactly what was attested -- and the
    detector's original ``contradictions`` list is left exactly as recorded.
    A resolution is stored beside the markers, never instead of them.
    """
    approval = dict(record.get("approval") or {})
    if approval.get("state") != APPROVAL_APPROVED:
        raise ResolutionError("only an APPROVED attestation may carry resolutions "
                              "(state=%s)" % approval.get("state"))

    att_id = str(record.get("attestation_id") or "")
    att_hash = str(record.get("attestation_hash") or "")
    existing = list(approval.get("resolutions") or [])

    for res in resolutions:
        ok, reason = validate_resolution(res)
        if not ok:
            raise ResolutionError("invalid resolution: %s" % reason)
        if str(res.get("attestation_id")) != att_id:
            raise ResolutionError("resolution names attestation %r, record is %r"
                                  % (res.get("attestation_id"), att_id))
        if str(res.get("attestation_hash")) != att_hash:
            raise ResolutionError("resolution hash does not match this attestation")
        if str(res.get("approval_record_id")) != str(approval.get("approval_record_id")):
            raise ResolutionError("resolution names a different approval record")
        recorded = {str(m) for m in (record.get("contradictions") or [])}
        unknown = [m for m in res["markers"] if m not in recorded]
        if unknown:
            raise ResolutionError("resolution names markers the detector never "
                                  "reported: %s" % sorted(unknown))
        existing.append(dict(res))

    approval["resolutions"] = existing
    updated = dict(record)
    updated["approval"] = approval
    return updated
