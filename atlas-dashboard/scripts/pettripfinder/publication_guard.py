"""PTF-EXCLUSIONS-002 -- the one gate every publication path calls.

``hotel_exclusions`` owns the tracked authority: what is excluded, and on whose
evidence. This module owns the DECISION that authority implies -- may this
identity become public -- and the refusal it produces when the answer is no.

It exists as its own module for one reason: there is more than one way for a
property to reach the public site (a seed writer, a policy-authority writer,
two candidate promoters, a machine-review approval, a display-row approval, and
the generation join itself), and a guard that lives inside any one of them is a
guard the other six can walk past. Every caller here raises the SAME structured
refusal, so a block reads identically no matter which boundary caught it.

TWO KINDS OF REFUSAL
--------------------

1. EXCLUDED IDENTITY. The proposed identity matches an active exclusion by
   normalized canonical name, by a recorded alias, or by street identity
   (number + distinctive street words + ZIP). The street basis is what stops
   the same building from publishing under a new name; a rename is not a new
   property.

   ``related_identity`` is deliberately NOT a blocking basis. On a
   ``DUPLICATE_IDENTITY``/``SUPERSEDED_IDENTITY`` record it names the record
   that SURVIVES -- the one that should publish. Blocking on it would suppress
   the live hotel and keep the dead one. It is carried into the refusal as
   lineage, so a reviewer sees the chain, and an identity that is itself
   excluded is still caught by its own name.

2. UNRESOLVED ADDRESS COLLISION. A proposed identity shares a street identity
   with an already-published identity of a different name. Two businesses can
   genuinely occupy one campus -- a hotel and the taproom beside it -- so this
   is not treated as a duplicate and neither record is merged or dropped. It is
   treated as UNREVIEWED: publication waits for an explicit
   ``same_campus_distinct_entity`` resolution that a human recorded, and that
   resolution must keep the identities distinct (different names, different
   slugs, and, when the categories are the same, a stated reason).

Both refusals are the same exception type carrying structured blocks, because a
caller that must fail a batch atomically needs one place to look.

Read-only. No network. Loads two tracked files and nothing else.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.hotel_exclusions import (  # noqa: E402
    ExclusionContractError,
    address_key,
    load_exclusions,
    normalize_name,
)

HOTEL_CATEGORY = "pet-friendly-hotels"

#: Match bases, in the order they are tried.
MATCH_NAME = "normalized_canonical_name"
MATCH_ALIAS = "recorded_alias"
MATCH_ADDRESS = "street_identity"

#: Block reasons.
BLOCK_EXCLUDED = "excluded_identity"
BLOCK_UNRESOLVED_COLLISION = "unresolved_address_collision"
BLOCK_RESOLUTION_NOT_DISTINCT = "resolution_does_not_distinguish_identities"

#: A refusal report lists at most this many blocks before summarising the rest,
#: so a bad batch cannot produce an unbounded error string.
MAX_LISTED_BLOCKS = 20

REMEDIATION = {
    BLOCK_EXCLUDED: (
        "This identity is barred by the tracked exclusion authority. To publish it, "
        "record a reviewed supersession on the named exclusion "
        "(hotel_exclusions.supersede, which requires NEW official-source evidence and a "
        "named reviewer) and re-run. There is no bypass flag."),
    BLOCK_UNRESOLVED_COLLISION: (
        "Two distinct identities share one street identity. If they are genuinely "
        "separate businesses on one campus, record a reviewed "
        "'same_campus_distinct_entity' resolution naming BOTH identities, then re-run. "
        "If they are the same business, do not publish the second one."),
    BLOCK_RESOLUTION_NOT_DISTINCT: (
        "The same-campus resolution does not keep the identities apart. Give each a "
        "distinct display name and slug, and -- when both sit in one category -- a "
        "stated distinct_reason."),
}


# --------------------------------------------------------------------------- #
# The refusal.
# --------------------------------------------------------------------------- #

class PublicationBlockedError(ExclusionContractError):
    """One or more proposed identities may not be published.

    Subclasses ``ExclusionContractError`` so the pre-existing callers that catch
    the exclusion contract error keep working; carries ``blocks`` so a caller can
    report or assert on the detail without re-deriving it.
    """

    def __init__(self, blocks: Sequence[Mapping]):
        self.blocks: Tuple[Mapping, ...] = tuple(blocks)
        super().__init__(format_blocks(blocks))


def _block_sort_key(block: Mapping) -> tuple:
    identity = block.get("proposed_identity") or {}
    return (str(identity.get("normalized_name", "")), str(block.get("reason", "")),
            str(block.get("exclusion_id") or block.get("resolution_id") or ""))


def format_blocks(blocks: Sequence[Mapping]) -> str:
    """Deterministic, bounded refusal text.

    Sorted by identity then reason so the same batch always produces the same
    message, and truncated so a thousand-row mistake cannot produce a
    thousand-line exception.
    """
    ordered = sorted(blocks, key=_block_sort_key)
    lines = ["refusing to publish %d identity/identities:" % len(ordered)]
    for block in ordered[:MAX_LISTED_BLOCKS]:
        identity = block.get("proposed_identity") or {}
        lines.append("  %s [%s]" % (identity.get("name", ""), block.get("reason", "")))
        lines.append("      address        : %s %s" % (identity.get("address", ""),
                                                       identity.get("postal_code", "")))
        lines.append("      category       : %s" % identity.get("category", ""))
        if block.get("exclusion_id"):
            lines.append("      exclusion      : %s (%s)" % (block["exclusion_id"],
                                                             block.get("exclusion_state", "")))
        if block.get("collides_with"):
            lines.append("      collides with  : %s" % block["collides_with"])
        lines.append("      match basis    : %s" % block.get("match_basis", ""))
        lineage = block.get("lineage") or {}
        for field in ("source_url", "evidence_quote", "observed_at", "reviewer_id",
                      "reviewed_at", "record_hash", "approval_hash", "related_identity"):
            if lineage.get(field):
                lines.append("      %-14s : %s" % (field, lineage[field]))
        lines.append("      remediation    : %s" % block.get("remediation", ""))
    if len(ordered) > MAX_LISTED_BLOCKS:
        lines.append("  ... and %d more" % (len(ordered) - MAX_LISTED_BLOCKS))
    return "\n".join(lines)


def _identity(row: Mapping) -> Dict[str, str]:
    name = str(row.get("name", "") or row.get("canonical_name", "")).strip()
    return {
        "name": name,
        "normalized_name": normalize_name(name),
        "address": str(row.get("address", "") or "").strip(),
        "postal_code": str(row.get("postal_code", "") or "").strip(),
        "category": str(row.get("category", "") or "").strip(),
    }


def as_rows(items: Iterable) -> List[Dict[str, str]]:
    """Accept the shapes callers already hold: dicts, or (name, address, zip[, category])."""
    rows: List[Dict[str, str]] = []
    for item in items:
        if isinstance(item, Mapping):
            rows.append(_identity(item))
        elif isinstance(item, str):
            rows.append(_identity({"name": item}))
        else:
            seq = list(item)
            rows.append(_identity({
                "name": seq[0] if seq else "",
                "address": seq[1] if len(seq) > 1 else "",
                "postal_code": seq[2] if len(seq) > 2 else "",
                "category": seq[3] if len(seq) > 3 else "",
            }))
    return rows


# --------------------------------------------------------------------------- #
# Exclusion matching.
# --------------------------------------------------------------------------- #

def _active(records: Iterable[Mapping]) -> List[Mapping]:
    return [r for r in records if not (r.get("supersession") or {}).get("reopened")]


def _aliases(record: Mapping) -> List[str]:
    return [normalize_name(a) for a in (record.get("aliases") or []) if str(a).strip()]


def match_exclusion(row: Mapping, records: Sequence[Mapping]
                    ) -> Optional[Tuple[Mapping, str]]:
    """(exclusion, match_basis) for the first active exclusion this row matches."""
    identity = _identity(row)
    key = address_key(identity["address"], identity["postal_code"])
    for record in _active(records):
        if record["normalized_name"] == identity["normalized_name"]:
            return record, MATCH_NAME
        if identity["normalized_name"] and identity["normalized_name"] in _aliases(record):
            return record, MATCH_ALIAS
        if key.strip("|") and address_key(record["address"], record["postal_code"]) == key:
            return record, MATCH_ADDRESS
    return None


def _exclusion_block(row: Mapping, record: Mapping, basis: str) -> Dict:
    return {
        "reason": BLOCK_EXCLUDED,
        "proposed_identity": _identity(row),
        "exclusion_id": record.get("exclusion_id", ""),
        "exclusion_state": record.get("exclusion_state", ""),
        "match_basis": basis,
        "lineage": {
            "source_url": record.get("source_url", ""),
            "evidence_quote": record.get("evidence_quote", ""),
            "observed_at": record.get("observed_at", ""),
            "reviewer_id": record.get("reviewer_id", ""),
            "reviewed_at": record.get("reviewed_at", ""),
            "record_hash": record.get("record_hash", ""),
            "approval_hash": record.get("approval_hash", ""),
            # Reported, never used to block: it names the record that survives.
            "related_identity": record.get("related_identity", ""),
        },
        "remediation": REMEDIATION[BLOCK_EXCLUDED],
    }


def exclusion_blocks(candidates: Iterable, records: Sequence[Mapping] = None,
                     path: Path = None, category: str = HOTEL_CATEGORY,
                     resolutions: Sequence[Mapping] = None,
                     resolutions_path: Path = None) -> List[Dict]:
    """Blocks for every candidate barred by the exclusion authority.

    ``category`` scopes the check to the category this authority governs. The
    authority is ``ptf-hotel-exclusions``: ``OUT_OF_CURRENT_CATEGORY`` means "not
    a hotel today", so applying it to a restaurant row would be the authority
    speaking outside its own subject. A row with no category is checked (callers
    that hold only a name are promoting a hotel).

    A match on ``street_identity`` -- and ONLY on street identity -- is waived
    when a reviewed ``same_campus_distinct_entity`` resolution names BOTH this
    candidate and the excluded record at that address. That is the case the
    resolution authority exists for and could not previously reach: two hotels
    share one dual-brand building and the founder has ruled them distinct, so
    the second hotel's refusal is a fact about the OTHER hotel. Milwaukee's
    dual-brand pair never exercised this because neither half was excluded.

    A match on NAME or ALIAS is never waived: that is the property itself, and
    no resolution about an address may publish a hotel that said no.
    """
    recs = records if records is not None else load_exclusions(path)
    if not recs:
        return []
    resolved = None
    blocks = []
    for row in as_rows(candidates):
        if category and row["category"] and row["category"] != category:
            continue
        hit = match_exclusion(row, recs)
        if not hit:
            continue
        record, basis = hit
        if basis == MATCH_ADDRESS:
            if resolved is None:
                resolved = (resolutions if resolutions is not None
                            else load_resolutions(resolutions_path))
            if _same_campus_distinguishes(row, record, resolved):
                continue
        blocks.append(_exclusion_block(row, record, basis))
    return blocks


def _same_campus_distinguishes(row: Mapping, record: Mapping,
                               resolutions: Sequence[Mapping]) -> bool:
    """Is this candidate/exclusion pair a reviewed same-campus pair?

    Every clause must hold: the resolution is a same-campus one, its address key
    is the key the two actually share, and it names BOTH normalized identities.
    Absent or partial means UNRESOLVED, which blocks.
    """
    identity = _identity(row)
    key = address_key(identity["address"], identity["postal_code"])
    if not key.strip("|"):
        return False
    excluded_name = normalize_name(record.get("canonical_name", "")
                                   or record.get("normalized_name", ""))
    for resolution in resolutions or ():
        if resolution.get("resolution_type") != SAME_CAMPUS:
            continue
        if resolution.get("address_key") != key:
            continue
        covered = {normalize_name(i.get("canonical_name", ""))
                   for i in resolution.get("identities") or ()}
        if identity["normalized_name"] in covered and excluded_name in covered:
            return True
    return False


# --------------------------------------------------------------------------- #
# Same-campus distinct entities.
# --------------------------------------------------------------------------- #

RESOLUTIONS_SCHEMA = "ptf-identity-resolutions/1.0"
RESOLUTIONS_PATH = _REPO_ROOT / "launch_packages" / "pettripfinder" / "identity_resolutions.json"
SAME_CAMPUS = "same_campus_distinct_entity"
RESOLUTION_TYPES = (SAME_CAMPUS,)
RESOLUTION_REQUIRED_FIELDS = ("resolution_id", "resolution_type", "address_key",
                              "identities", "evidence", "reviewer_id", "reviewed_at",
                              "resolution_hash")


def resolution_hash(resolution: Mapping) -> str:
    body = {
        "resolution_type": resolution.get("resolution_type"),
        "address_key": resolution.get("address_key"),
        "identities": [{k: i.get(k) for k in ("canonical_name", "category", "slug")}
                       for i in resolution.get("identities", [])],
        "reviewer_id": resolution.get("reviewer_id"),
        "reviewed_at": resolution.get("reviewed_at"),
    }
    return "sha256:" + hashlib.sha256(
        json.dumps(body, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def validate_resolutions(document: Mapping) -> List[Dict]:
    """Fail closed on a resolution that would let two records blur together."""
    if document.get("schema") != RESOLUTIONS_SCHEMA:
        raise ExclusionContractError("expected schema %r, got %r"
                                     % (RESOLUTIONS_SCHEMA, document.get("schema")))
    resolutions = document.get("resolutions")
    if not isinstance(resolutions, list):
        raise ExclusionContractError("'resolutions' must be a list")
    seen = set()
    for r in resolutions:
        missing = [f for f in RESOLUTION_REQUIRED_FIELDS if not r.get(f)]
        if missing:
            raise ExclusionContractError("%s: missing required field(s) %s"
                                         % (r.get("resolution_id"), missing))
        if r["resolution_type"] not in RESOLUTION_TYPES:
            raise ExclusionContractError("%s: unknown resolution_type %r"
                                         % (r["resolution_id"], r["resolution_type"]))
        if r["resolution_id"] in seen:
            raise ExclusionContractError("duplicate resolution_id %r" % r["resolution_id"])
        seen.add(r["resolution_id"])
        identities = r["identities"]
        if not isinstance(identities, list) or len(identities) < 2:
            raise ExclusionContractError("%s: a resolution names at least two identities"
                                         % r["resolution_id"])
        for i in identities:
            for field in ("canonical_name", "category", "slug"):
                if not str(i.get(field, "")).strip():
                    raise ExclusionContractError("%s: identity missing %s"
                                                 % (r["resolution_id"], field))
        names = [normalize_name(i["canonical_name"]) for i in identities]
        slugs = [str(i["slug"]).strip() for i in identities]
        if len(set(names)) != len(names):
            raise ExclusionContractError("%s: identities must have distinct names"
                                         % r["resolution_id"])
        if len(set(slugs)) != len(slugs):
            raise ExclusionContractError("%s: identities must have distinct slugs -- two "
                                         "records sharing a slug share a route"
                                         % r["resolution_id"])
        if len(set(i["category"] for i in identities)) == 1 and not str(
                r.get("distinct_reason", "")).strip():
            raise ExclusionContractError(
                "%s: same-category identities at one address need a stated distinct_reason"
                % r["resolution_id"])
        if resolution_hash(r) != r["resolution_hash"]:
            raise ExclusionContractError("%s: resolution_hash does not re-derive"
                                         % r["resolution_id"])
    return resolutions


def load_resolutions(path: Path = None) -> List[Dict]:
    """Validated resolutions, or [] when none has been recorded.

    Absent means UNRESOLVED, not permitted: with no file, every address
    collision blocks. That is the fail-closed default.
    """
    p = Path(path) if path else RESOLUTIONS_PATH
    if not p.exists():
        return []
    return validate_resolutions(json.loads(p.read_text(encoding="utf-8-sig")))


def distinct_entity_groups(resolutions: Sequence[Mapping] = None,
                           path: Path = None) -> Tuple[Tuple[str, ...], ...]:
    """Reviewed same-campus identity sets, as display-name groups.

    The dataset builder's address dedup rule would collapse a reviewed pair back
    into one listing, silently deleting a real business. This hands it the exact
    exception a human recorded -- nothing wider.
    """
    resolved = resolutions if resolutions is not None else load_resolutions(path)
    return tuple(
        tuple(sorted(str(i["canonical_name"]) for i in r.get("identities", [])))
        for r in resolved if r.get("resolution_type") == SAME_CAMPUS)


def _resolution_for(key: str, names: Sequence[str], resolutions: Sequence[Mapping]
                    ) -> Optional[Mapping]:
    """The resolution covering this address key and every colliding name."""
    wanted = set(names)
    for r in resolutions:
        if r.get("address_key") != key:
            continue
        covered = {normalize_name(i["canonical_name"]) for i in r.get("identities", [])}
        if wanted <= covered:
            return r
    return None


def collision_blocks(candidates: Iterable, published: Iterable = (),
                     resolutions: Sequence[Mapping] = None,
                     path: Path = None, cross_category_only: bool = True) -> List[Dict]:
    """Blocks for address collisions that no reviewed resolution covers.

    A candidate colliding with ITSELF (same normalized name already published)
    is not a collision -- that is the same record, and re-publishing it is the
    normal idempotent case.

    ``cross_category_only`` is the default because that is the case this
    mechanism was built for: a hotel and the taproom on its campus are two real
    businesses, and the categories are what make them distinguishable. Two
    DIFFERENTLY NAMED rows in the SAME category at one address are a different
    question -- most often a near-duplicate listing -- and that question already
    belongs to the importer's duplicate detection. Answering it here as well
    would change promotion semantics this work order was told to leave alone.
    Pass ``cross_category_only=False`` to surface those pairs too.
    """
    resolved = resolutions if resolutions is not None else load_resolutions(path)
    candidate_rows = as_rows(candidates)
    published_rows = as_rows(published)

    by_key: Dict[str, List[Dict]] = {}
    for row in published_rows:
        key = address_key(row["address"], row["postal_code"])
        if key.strip("|"):
            by_key.setdefault(key, []).append(row)

    blocks: List[Dict] = []
    seen_pairs = set()
    for row in candidate_rows:
        key = address_key(row["address"], row["postal_code"])
        if not key.strip("|"):
            continue
        neighbours = [o for o in by_key.get(key, [])
                      if o["normalized_name"] != row["normalized_name"]]
        # Candidates in the same batch collide with each other too.
        neighbours += [o for o in candidate_rows
                       if o is not row
                       and address_key(o["address"], o["postal_code"]) == key
                       and o["normalized_name"] != row["normalized_name"]]
        if cross_category_only:
            neighbours = [o for o in neighbours if o["category"] != row["category"]]
        if not neighbours:
            continue
        names = sorted({row["normalized_name"]} | {o["normalized_name"] for o in neighbours})
        pair = (key, tuple(names))
        if pair in seen_pairs:
            continue
        seen_pairs.add(pair)
        resolution = _resolution_for(key, names, resolved)
        if resolution is None:
            blocks.append({
                "reason": BLOCK_UNRESOLVED_COLLISION,
                "proposed_identity": row,
                "collides_with": ", ".join(
                    "%s (%s)" % (o["name"], o["category"] or "uncategorised")
                    for o in sorted(neighbours, key=lambda x: x["normalized_name"])),
                "match_basis": MATCH_ADDRESS,
                "lineage": {"address_key": key},
                "remediation": REMEDIATION[BLOCK_UNRESOLVED_COLLISION],
            })
            continue
        # A resolution exists. It must still keep the two records apart on the
        # surfaces that make them separate businesses to a reader.
        by_name = {normalize_name(i["canonical_name"]): i for i in resolution["identities"]}
        slugs = {n: by_name[n]["slug"] for n in names if n in by_name}
        if len(set(slugs.values())) != len(slugs):
            blocks.append({
                "reason": BLOCK_RESOLUTION_NOT_DISTINCT,
                "proposed_identity": row,
                "resolution_id": resolution["resolution_id"],
                "collides_with": ", ".join(names),
                "match_basis": MATCH_ADDRESS,
                "lineage": {"address_key": key,
                            "reviewer_id": resolution.get("reviewer_id", ""),
                            "reviewed_at": resolution.get("reviewed_at", ""),
                            "resolution_hash": resolution.get("resolution_hash", "")},
                "remediation": REMEDIATION[BLOCK_RESOLUTION_NOT_DISTINCT],
            })
    return blocks


# --------------------------------------------------------------------------- #
# The gate itself.
# --------------------------------------------------------------------------- #

#: A published record may reference a reviewed resolution by ID and by nothing
#: else. These substrings are the shapes an operational leak would take -- a
#: path, a corpus location, a candidate or run identifier, a status word.
FORBIDDEN_REFERENCE_SUBSTRINGS = ("/", "\\", "..", "candidate", "cand-", "tmp",
                                  "temp", "run-", "run_", "data", "worker",
                                  "pending", "draft", "status")

BLOCK_REFERENCE_MALFORMED = "resolution_reference_malformed"
BLOCK_REFERENCE_UNKNOWN = "resolution_reference_unknown"
BLOCK_REFERENCE_WRONG_PAIR = "resolution_reference_wrong_pair"
BLOCK_REFERENCE_WRONG_ADDRESS = "resolution_reference_wrong_address"

REMEDIATION_REFERENCE = (
    "A published record's same_campus_resolution must name an existing "
    "ptf-identity-resolutions/1.0 resolution that covers THIS identity at THIS "
    "street address, by id alone. Correct the reference or remove it; a reference "
    "that cannot be resolved is not publishable.")


def resolution_reference_blocks(records: Iterable[Mapping],
                                resolutions: Sequence[Mapping] = None,
                                path: Path = None) -> List[Dict]:
    """Blocks for published records whose same_campus_resolution does not hold up.

    The reference is the only reason a reader can tell WHY two businesses share
    one address legitimately, so an unresolvable one is worse than none: it
    asserts a review that cannot be produced. Missing is fine -- most records
    have no collision to explain. Present-and-wrong fails closed.

    ``load_resolutions`` validates the whole authority on read, so a resolution
    whose hash no longer re-derives never reaches this function: it raises
    first. That is deliberate -- a tampered authority must not be selectively
    survivable.
    """
    resolved = resolutions if resolutions is not None else load_resolutions(path)
    by_id = {r["resolution_id"]: r for r in resolved}
    blocks: List[Dict] = []
    for record in records:
        reference = record.get("same_campus_resolution")
        if not reference:
            continue
        identity = _identity(record)
        base = {"proposed_identity": identity, "resolution_id": reference,
                "match_basis": MATCH_NAME, "remediation": REMEDIATION_REFERENCE}
        text = str(reference)
        if (not text.strip() or text != text.strip()
                or any(bad in text.lower() for bad in FORBIDDEN_REFERENCE_SUBSTRINGS)):
            blocks.append(dict(base, reason=BLOCK_REFERENCE_MALFORMED,
                               lineage={"rejected_reference": text}))
            continue
        resolution = by_id.get(text)
        if resolution is None:
            blocks.append(dict(base, reason=BLOCK_REFERENCE_UNKNOWN,
                               lineage={"known_resolution_ids": sorted(by_id)[:MAX_LISTED_BLOCKS]}))
            continue
        covered = {normalize_name(i["canonical_name"]) for i in resolution.get("identities", [])}
        if identity["normalized_name"] not in covered or len(covered) < 2:
            blocks.append(dict(base, reason=BLOCK_REFERENCE_WRONG_PAIR,
                               lineage={"resolution_covers": ", ".join(sorted(covered))}))
            continue
        key = address_key(identity["address"], identity["postal_code"])
        if key.strip("|") and resolution.get("address_key") != key:
            blocks.append(dict(base, reason=BLOCK_REFERENCE_WRONG_ADDRESS,
                               lineage={"record_address_key": key,
                                        "resolution_address_key": resolution.get("address_key", "")}))
    return blocks


def assert_resolution_references(records: Iterable[Mapping], **kwargs) -> None:
    """Raise unless every same_campus_resolution reference resolves correctly."""
    blocks = resolution_reference_blocks(records, **kwargs)
    if blocks:
        raise PublicationBlockedError(blocks)


def publication_blocks(candidates: Iterable, published: Iterable = (), *,
                       exclusions: Sequence[Mapping] = None,
                       resolutions: Sequence[Mapping] = None,
                       exclusions_path: Path = None,
                       resolutions_path: Path = None,
                       category: str = HOTEL_CATEGORY,
                       check_collisions: bool = True,
                       cross_category_only: bool = True) -> List[Dict]:
    """Every reason these candidates may not publish. Pure inspection: no raise.

    Used directly by preview/analysis surfaces, which are allowed to REPORT an
    exclusion; only the assert form refuses.
    """
    blocks = exclusion_blocks(candidates, exclusions, exclusions_path, category,
                              resolutions=resolutions,
                              resolutions_path=resolutions_path)
    if check_collisions:
        blocks += collision_blocks(candidates, published, resolutions, resolutions_path,
                                   cross_category_only)
    return blocks


def assert_publishable(candidates: Iterable, published: Iterable = (), **kwargs) -> None:
    """Raise :class:`PublicationBlockedError` unless every candidate may publish.

    Collects ALL blocks before raising, so a caller that must fail a batch
    atomically gets the whole picture from one refusal rather than discovering
    the next offender on the next attempt.
    """
    blocks = publication_blocks(candidates, published, **kwargs)
    if blocks:
        raise PublicationBlockedError(blocks)
