"""ATLAS-THROUGHPUT-003 -- the sealed market package contract.

A sealed market package is ONE immutable document describing a market's
proposed state: its geography, census, identity records, official routes,
pet-friendly policy records, verified-no-pets records, evidence references and
hashes, unresolved rows, founder holds, the delta the package intends against
the current live release, the digests of every input the writer consumed, and
the versions of the builder and of every owning contract it was validated
against.

It is NOT a second authority system. Every section carries the SAME documents
the existing owning contracts already define (``ptf-market/1.1``,
``ptf-market-identity-census/1.1``, policy schema 1.2/1.3 records,
``ptf-hotel-exclusions/1.0`` records, ``ptf-identity-routing/1.0`` records,
``ptf-market-final-partition/1.1``); the package is the envelope that binds
them together under one digest so that a release decision can name exactly
what it validated.

Immutability
------------
``package_digest`` is the sha256 of the canonical JSON of the body -- every
field except the seal fields listed in :data:`SEAL_FIELDS`. ``package_id``
derives from the digest. A package is written once, to a path that carries
its id; the writer refuses to overwrite a different document at the same path,
and a correction is therefore a NEW package with a new id. Nothing ever edits a
sealed package in place: validation results live in a separate receipt
(:mod:`fast_release_lane`) that names the package by digest.

Ownership
---------
Packages live under ``launch_packages/pettripfinder/markets/packages/<market_id>/``
and staging trees under ``markets/staging/<market_id>/`` -- both inside the
market's own execution zone in ``market_local_ownership.json``, so a market's
proposed state is local BY CONSTRUCTION rather than because a classifier
ignores a shared write.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
LAUNCH_PACKAGE = REPO_ROOT / "launch_packages" / "pettripfinder"
PACKAGES_DIR = LAUNCH_PACKAGE / "markets" / "packages"
STAGING_DIR = LAUNCH_PACKAGE / "markets" / "staging"
RECEIPTS_DIR = LAUNCH_PACKAGE / "markets" / "receipts"

SCHEMA = "ptf-sealed-market-package/1.0"
BUILDER_VERSION = "ptf-market-package-writer/1.0"

#: Where a package may be executed from. ``REGISTERED_LIVE`` is a package for a
#: market the registry already carries (a data-only change to a live market);
#: the two shadow zones mirror ``market_local_ownership.EXECUTION_ZONES``.
ZONE_SHADOW = "SHADOW"
ZONE_SHADOW_UNTIL_REGISTERED = "SHADOW_UNTIL_REGISTERED"
ZONE_REGISTERED_LIVE = "REGISTERED_LIVE"
ZONE_FROZEN_COPY = "FROZEN_COPY"
EXECUTION_ZONES = (ZONE_SHADOW, ZONE_SHADOW_UNTIL_REGISTERED,
                   ZONE_REGISTERED_LIVE, ZONE_FROZEN_COPY)

#: The one validation state a sealed package may declare about ITSELF. Every
#: other state is a receipt's to give.
VALIDATION_STATE_SEALED = "SEALED_UNVALIDATED"

#: Seal fields: written by :func:`seal`, excluded from the digest.
SEAL_FIELDS = ("package_id", "package_digest", "sealed_at")

#: Body fields, in the order the order lists them. Every one is required.
BODY_FIELDS: Tuple[str, ...] = (
    "schema",                     # PACKAGE_SCHEMA_VERSION
    "market_id",                  # MARKET_ID
    "created_from_source_sha",    # CREATED_FROM_SOURCE_SHA
    "execution_zone",             # EXECUTION_ZONE
    "census",                     # CENSUS (ptf-market-identity-census/1.1)
    "identity_records",           # IDENTITY RECORDS
    "market",                     # GEOGRAPHY / CORRIDOR ASSIGNMENTS (ptf-market/1.1)
    "official_routes",            # OFFICIAL ROUTES (ptf-identity-routing/1.0 records)
    "pet_friendly_records",       # PET-FRIENDLY POLICY RECORDS (schema 1.2/1.3)
    "verified_no_pets_records",   # VERIFIED NO-PETS RECORDS (ptf-hotel-exclusions/1.0)
    "seed_rows",                  # the display inventory the join is made against
    "partition",                  # ptf-market-final-partition/1.1
    "evidence_references",        # EVIDENCE REFERENCES
    "evidence_hashes",            # EVIDENCE HASHES (evidence_ref -> artifact sha256)
    "unresolved_rows",            # UNRESOLVED ROWS
    "founder_holds",              # FOUNDER HOLDS
    "intended_delta",             # INTENDED DELTA
    "parent_live_state",          # the live release the delta is stated against
    "dependency_input_digests",   # DEPENDENCY INPUT DIGESTS
    "builder_version",            # BUILDER VERSION
    "contract_versions",          # CONTRACT VERSIONS
    "coverage_scorecard",         # COVERAGE SCORECARD
    "validation_state",           # VALIDATION STATE
)

#: An evidence reference binds one captured artifact to one identity.
EVIDENCE_REFERENCE_FIELDS: Tuple[str, ...] = (
    "evidence_ref", "identity_key", "artifact_sha256", "source_url",
    "captured_at", "artifact_kind", "capture_lane", "source_grade",
    "artifact_available",
)
EVIDENCE_REFERENCE_OPTIONAL: Tuple[str, ...] = (
    "artifact_path", "paid_reservation", "byte_length", "final_url",
)

#: A paid reservation is the idempotency key a paid fetch was made under.
PAID_RESERVATION_FIELDS: Tuple[str, ...] = (
    "provider", "lane", "run_id", "attempt_id", "request_envelope_sha256",
)

#: Intended delta: what the package claims to change against the live release.
INTENDED_DELTA_FIELDS: Tuple[str, ...] = (
    "market_id", "add_property_ids", "update_property_ids",
    "remove_property_ids", "add_routes", "change_routes", "remove_routes",
    "expected_profile_delta", "expected_market_count_delta",
    "expected_participation_delta",
)

#: The live release a package's delta is stated against.
PARENT_LIVE_FIELDS: Tuple[str, ...] = (
    "live_deploy_id", "rollback_target", "source_commit",
    "participating_markets", "profile_counts", "total_profiles",
    "sitemap_route_count", "live_index_digest",
)

#: Explicit relation types an identity record may declare to another identity.
RELATION_NONE = "NONE"
RELATION_CO_LOCATED_DISTINCT = "CO_LOCATED_DISTINCT"
RELATION_REBRAND_OF = "REBRAND_OF"
RELATION_SUPERSEDES = "SUPERSEDES"
RELATION_TYPES = (RELATION_NONE, RELATION_CO_LOCATED_DISTINCT,
                  RELATION_REBRAND_OF, RELATION_SUPERSEDES)

_SHA256_PREFIXED = re.compile(r"^sha256:[0-9a-f]{64}$")
_SHA256_BARE = re.compile(r"^[0-9a-f]{64}$")
_GIT_SHA = re.compile(r"^[0-9a-f]{7,40}$")
_MARKET_ID = re.compile(r"^[a-z][a-z0-9]+(-[a-z0-9]+)*-[a-z]{2}$")


class PackageContractError(ValueError):
    """The package is not a sealed market package (fail closed)."""

    def __init__(self, issues: Sequence["Issue"]):
        self.issues = tuple(issues)
        super().__init__("; ".join(str(i) for i in self.issues[:8])
                         + (" (+%d more)" % (len(self.issues) - 8)
                            if len(self.issues) > 8 else ""))


class Issue(tuple):
    """``(path, code, detail)`` -- the same shape the owning contracts use."""

    __slots__ = ()

    def __new__(cls, path: str, code: str, detail: str):
        return tuple.__new__(cls, (path, code, detail))

    @property
    def path(self) -> str:
        return self[0]

    @property
    def code(self) -> str:
        return self[1]

    @property
    def detail(self) -> str:
        return self[2]

    def __str__(self) -> str:
        return "%s: %s (%s)" % (self[0], self[2], self[1])


# --------------------------------------------------------------------------- #
# Canonical serialization and digests.
# --------------------------------------------------------------------------- #

def canonical_json(document: Any) -> str:
    """Canonical JSON: sorted keys, no insignificant whitespace, UTF-8 text.

    Two documents with equal content produce equal bytes; the digest of a
    package is the digest of this text.
    """
    return json.dumps(document, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def sha256_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def is_sha256(value: Any) -> bool:
    return isinstance(value, str) and bool(_SHA256_PREFIXED.match(value))


def normalise_sha256(value: str) -> str:
    """``sha256:<hex>`` for either spelling the repository uses."""
    text = str(value or "").strip().lower()
    if _SHA256_BARE.match(text):
        return "sha256:" + text
    return text


def body_of(document: Mapping) -> "OrderedDict[str, Any]":
    """The digested part of a package: every field but the seal fields."""
    return OrderedDict((k, v) for k, v in document.items() if k not in SEAL_FIELDS)


def digest_of(document: Mapping) -> str:
    return sha256_text(canonical_json(body_of(document)))


def package_id_for(market_id: str, digest: str) -> str:
    return "pkg-%s-%s" % (market_id, digest.split(":", 1)[1][:16])


def seal(document: Mapping, *, sealed_at: str) -> "OrderedDict[str, Any]":
    """Return a sealed copy: body in :data:`BODY_FIELDS` order, then the seal.

    ``sealed_at`` is recorded but excluded from the digest, so two writes of
    the same body at different times seal to the same identity.
    """
    body = body_of(document)
    missing = [f for f in BODY_FIELDS if f not in body]
    if missing:
        raise PackageContractError([Issue(f, "MISSING_REQUIRED", "body field is required")
                                    for f in missing])
    unknown = sorted(set(body) - set(BODY_FIELDS))
    if unknown:
        raise PackageContractError([Issue(f, "UNKNOWN_FIELD", "not a package field")
                                    for f in unknown])
    ordered: "OrderedDict[str, Any]" = OrderedDict((f, body[f]) for f in BODY_FIELDS)
    digest = digest_of(ordered)
    ordered["package_id"] = package_id_for(str(body["market_id"]), digest)
    ordered["package_digest"] = digest
    ordered["sealed_at"] = sealed_at
    return ordered


def verify_seal(document: Mapping) -> Tuple[Issue, ...]:
    """The seal re-derives from the body: digest, and id from digest."""
    out: List[Issue] = []
    for field in SEAL_FIELDS:
        if not document.get(field):
            out.append(Issue(field, "MISSING_REQUIRED", "seal field is required"))
    if out:
        return tuple(out)
    digest = document["package_digest"]
    if not is_sha256(digest):
        out.append(Issue("package_digest", "NOT_SHA256", "malformed digest %r" % (digest,)))
        return tuple(out)
    actual = digest_of(document)
    if actual != digest:
        out.append(Issue("package_digest", "DIGEST_MISMATCH",
                         "body digests to %s, seal says %s" % (actual, digest)))
    expected_id = package_id_for(str(document.get("market_id") or ""), digest)
    if document["package_id"] != expected_id:
        out.append(Issue("package_id", "ID_MISMATCH",
                         "expected %s for this digest, got %s"
                         % (expected_id, document["package_id"])))
    return tuple(out)


# --------------------------------------------------------------------------- #
# Shape validation: the envelope only. Section CONTENT is validated by the
# owning contracts through the writer and the fast lane, never here.
# --------------------------------------------------------------------------- #

def _is_list(value: Any) -> bool:
    return isinstance(value, list)


def validate_shape(document: Mapping) -> Tuple[Issue, ...]:
    out: List[Issue] = []
    if not isinstance(document, Mapping):
        return (Issue("package", "NOT_OBJECT", "a package must be an object"),)
    if document.get("schema") != SCHEMA:
        out.append(Issue("schema", "BAD_SCHEMA", "expected %r, got %r"
                         % (SCHEMA, document.get("schema"))))
    for field in BODY_FIELDS:
        if field not in document:
            out.append(Issue(field, "MISSING_REQUIRED", "body field is required"))
    if out:
        return tuple(out)

    market_id = document["market_id"]
    if not isinstance(market_id, str) or not _MARKET_ID.match(market_id):
        out.append(Issue("market_id", "NOT_MARKET_ID", "%r is not a market id" % (market_id,)))
    sha = document["created_from_source_sha"]
    if not isinstance(sha, str) or not _GIT_SHA.match(sha):
        out.append(Issue("created_from_source_sha", "NOT_COMMIT", "%r is not a commit id" % (sha,)))
    if document["execution_zone"] not in EXECUTION_ZONES:
        out.append(Issue("execution_zone", "BAD_ENUM", "must be one of %s" % (EXECUTION_ZONES,)))
    if document["validation_state"] != VALIDATION_STATE_SEALED:
        out.append(Issue("validation_state", "BAD_ENUM",
                         "a package may only declare %r about itself; validation "
                         "results live in a receipt" % VALIDATION_STATE_SEALED))
    if document["builder_version"] != BUILDER_VERSION:
        out.append(Issue("builder_version", "UNSUPPORTED_BUILDER",
                         "expected %r, got %r" % (BUILDER_VERSION, document["builder_version"])))

    for section in ("identity_records", "official_routes", "pet_friendly_records",
                    "verified_no_pets_records", "seed_rows", "evidence_references",
                    "unresolved_rows", "founder_holds"):
        if not _is_list(document[section]):
            out.append(Issue(section, "NOT_LIST", "%s must be a list" % section))
    for section in ("census", "market", "partition", "evidence_hashes",
                    "intended_delta", "parent_live_state", "dependency_input_digests",
                    "contract_versions", "coverage_scorecard"):
        if not isinstance(document[section], Mapping):
            out.append(Issue(section, "NOT_OBJECT", "%s must be an object" % section))
    if out:
        return tuple(out)

    # Every section that names a market names THIS market.
    for section in ("census", "market", "partition"):
        declared = document[section].get("market_id")
        if declared != market_id:
            out.append(Issue(section + ".market_id", "WRONG_MARKET",
                             "%s declares %r, package is for %r" % (section, declared, market_id)))
    if document["intended_delta"].get("market_id") != market_id:
        out.append(Issue("intended_delta.market_id", "WRONG_MARKET",
                         "intended delta must name the package market"))

    # Evidence references and the hash index.
    refs_seen: Dict[str, int] = {}
    for index, ref in enumerate(document["evidence_references"]):
        path = "evidence_references[%d]" % index
        if not isinstance(ref, Mapping):
            out.append(Issue(path, "NOT_OBJECT", "an evidence reference must be an object"))
            continue
        for field in EVIDENCE_REFERENCE_FIELDS:
            if field not in ref or ref[field] in ("", None):
                out.append(Issue("%s.%s" % (path, field), "MISSING_REQUIRED",
                                 "%s is required on an evidence reference" % field))
        unknown = sorted(set(ref) - set(EVIDENCE_REFERENCE_FIELDS) - set(EVIDENCE_REFERENCE_OPTIONAL))
        if unknown:
            out.append(Issue(path, "UNKNOWN_FIELD", "unknown field(s) %s" % unknown))
        if "artifact_sha256" in ref and not is_sha256(ref.get("artifact_sha256")):
            out.append(Issue(path + ".artifact_sha256", "NOT_SHA256",
                             "expected sha256:<64 hex>, got %r" % (ref.get("artifact_sha256"),)))
        if not isinstance(ref.get("artifact_available"), bool):
            out.append(Issue(path + ".artifact_available", "NOT_BOOL",
                             "artifact_available must be true or false"))
        reservation = ref.get("paid_reservation")
        if reservation is not None:
            if not isinstance(reservation, Mapping):
                out.append(Issue(path + ".paid_reservation", "NOT_OBJECT", "expected an object"))
            else:
                for field in PAID_RESERVATION_FIELDS:
                    if not reservation.get(field):
                        out.append(Issue("%s.paid_reservation.%s" % (path, field),
                                         "MISSING_REQUIRED", "%s is required" % field))
        ev_ref = str(ref.get("evidence_ref") or "")
        if ev_ref:
            refs_seen[ev_ref] = refs_seen.get(ev_ref, 0) + 1
    for ev_ref, count in sorted(refs_seen.items()):
        if count > 1:
            out.append(Issue("evidence_references", "DUPLICATE_REF",
                             "%d references share evidence_ref %r" % (count, ev_ref)))
    hashes = document["evidence_hashes"]
    for ev_ref, digest in sorted(hashes.items()):
        if not is_sha256(digest):
            out.append(Issue("evidence_hashes.%s" % ev_ref, "NOT_SHA256",
                             "expected sha256:<64 hex>, got %r" % (digest,)))
    if set(hashes) != set(refs_seen):
        out.append(Issue("evidence_hashes", "INDEX_MISMATCH",
                         "the hash index must name exactly the evidence references: "
                         "index-only %s, references-only %s"
                         % (sorted(set(hashes) - set(refs_seen))[:5],
                            sorted(set(refs_seen) - set(hashes))[:5])))

    # Intended delta shape.
    delta = document["intended_delta"]
    for field in INTENDED_DELTA_FIELDS:
        if field not in delta:
            out.append(Issue("intended_delta." + field, "MISSING_REQUIRED", "required"))
    for field in ("add_property_ids", "update_property_ids", "remove_property_ids",
                  "add_routes", "change_routes", "remove_routes"):
        if field in delta and not _is_list(delta[field]):
            out.append(Issue("intended_delta." + field, "NOT_LIST", "must be a list"))
    for field in ("expected_profile_delta", "expected_market_count_delta"):
        value = delta.get(field)
        if field in delta and (not isinstance(value, int) or isinstance(value, bool)):
            out.append(Issue("intended_delta." + field, "NOT_INT", "must be an integer"))
    if delta.get("remove_property_ids") or delta.get("remove_routes"):
        authority = delta.get("removal_authority")
        if not isinstance(authority, Mapping) or not authority.get("ruling_ref") \
                or not authority.get("reason"):
            out.append(Issue("intended_delta.removal_authority", "MISSING_REQUIRED",
                             "a removal must name the ruling that authorised it and why"))

    # Parent live state shape.
    parent = document["parent_live_state"]
    for field in PARENT_LIVE_FIELDS:
        if field not in parent:
            out.append(Issue("parent_live_state." + field, "MISSING_REQUIRED", "required"))
    if "live_index_digest" in parent and not is_sha256(parent.get("live_index_digest")):
        out.append(Issue("parent_live_state.live_index_digest", "NOT_SHA256",
                         "expected sha256:<64 hex>"))

    # Dependency input digests.
    for name, digest in sorted(document["dependency_input_digests"].items()):
        if not is_sha256(digest):
            out.append(Issue("dependency_input_digests.%s" % name, "NOT_SHA256",
                             "expected sha256:<64 hex>, got %r" % (digest,)))
    if not document["dependency_input_digests"]:
        out.append(Issue("dependency_input_digests", "EMPTY",
                         "a package must name the inputs it was built from"))

    # Identity record relations.
    for index, record in enumerate(document["identity_records"]):
        path = "identity_records[%d]" % index
        if not isinstance(record, Mapping):
            out.append(Issue(path, "NOT_OBJECT", "an identity record must be an object"))
            continue
        relation = record.get("relation")
        if relation is not None:
            if not isinstance(relation, Mapping) or relation.get("type") not in RELATION_TYPES:
                out.append(Issue(path + ".relation", "BAD_ENUM",
                                 "relation.type must be one of %s" % (RELATION_TYPES,)))
            elif relation.get("type") != RELATION_NONE and (
                    not relation.get("related_identity_key") or not relation.get("ruling_ref")):
                out.append(Issue(path + ".relation", "MISSING_REQUIRED",
                                 "a declared relation names the related identity and the ruling"))
    return tuple(out)


def validate(document: Mapping) -> Tuple[Issue, ...]:
    """Shape plus seal. The envelope check the fast lane's rule A runs."""
    issues = list(validate_shape(document))
    if not issues:
        issues.extend(verify_seal(document))
    return tuple(issues)


# --------------------------------------------------------------------------- #
# Immutable storage.
# --------------------------------------------------------------------------- #

def package_dir(market_id: str, packages_dir: Optional[Path] = None) -> Path:
    return (Path(packages_dir) if packages_dir else PACKAGES_DIR) / market_id


def package_path(document: Mapping, packages_dir: Optional[Path] = None) -> Path:
    return package_dir(str(document["market_id"]), packages_dir) / ("%s.json" % document["package_id"])


def render(document: Mapping) -> str:
    """The stored form: indented for review, trailing newline, UTF-8."""
    return json.dumps(document, indent=1, ensure_ascii=False, allow_nan=False) + "\n"


def write_sealed(document: Mapping, packages_dir: Optional[Path] = None) -> Path:
    """Write a sealed package once. Never overwrites a different document.

    The same document may be written again (a byte-identical re-write is a
    no-op); any other content at the path is a corruption and is refused, so a
    "correction" can only ever become a new package with a new id.
    """
    issues = validate(document)
    if issues:
        raise PackageContractError(issues)
    path = package_path(document, packages_dir)
    text = render(document)
    if path.exists():
        existing = path.read_text(encoding="utf-8-sig")
        if existing != text:
            raise PackageContractError([Issue(
                "package_id", "IMMUTABLE",
                "%s already holds a different document; a sealed package is never "
                "rewritten in place -- a correction is a new package" % path.name)])
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)
    return path


def read_sealed(path: Path) -> "OrderedDict[str, Any]":
    """Read a package and refuse it unless its seal re-derives."""
    document = json.loads(Path(path).read_text(encoding="utf-8-sig"), object_pairs_hook=OrderedDict)
    issues = validate(document)
    if issues:
        raise PackageContractError(issues)
    expected_name = "%s.json" % document["package_id"]
    if Path(path).name != expected_name:
        raise PackageContractError([Issue("package_id", "PATH_MISMATCH",
                                          "file %s does not carry its package id (%s)"
                                          % (Path(path).name, expected_name))])
    return document


def list_packages(market_id: str, packages_dir: Optional[Path] = None) -> List[Path]:
    directory = package_dir(market_id, packages_dir)
    if not directory.is_dir():
        return []
    return sorted(directory.glob("pkg-*.json"))


__all__ = [
    "SCHEMA", "BUILDER_VERSION", "EXECUTION_ZONES", "BODY_FIELDS", "SEAL_FIELDS",
    "EVIDENCE_REFERENCE_FIELDS", "PAID_RESERVATION_FIELDS", "INTENDED_DELTA_FIELDS",
    "PARENT_LIVE_FIELDS", "RELATION_TYPES", "PACKAGES_DIR", "STAGING_DIR", "RECEIPTS_DIR",
    "Issue", "PackageContractError", "canonical_json", "sha256_text", "sha256_bytes",
    "is_sha256", "normalise_sha256", "body_of", "digest_of", "package_id_for", "seal",
    "verify_seal", "validate_shape", "validate", "package_dir", "package_path", "render",
    "write_sealed", "read_sealed", "list_packages",
]
