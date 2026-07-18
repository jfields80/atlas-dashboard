"""AES-DATA-003A -- domain-pack contracts (frozen, typed, self-contained).

Deliberately dependency-free: this module imports nothing from elsewhere in
the importer package (not even ``constants.py``), so it can never be part of
a circular import no matter what future module needs these contracts. Every
value a caller supplies (category IDs, field names, ...) is a plain string;
the caller (``lodging.py``/``parks.py``/``dining.py``/future packs) is
responsible for sourcing those strings from ``constants.py``.

Every contract here is immutable data, validated once at construction
(``__post_init__``, fail-fast) and never mutated afterward. ``DomainPack``
is not a plugin: it carries no I/O, no network, no provider calls, no
dynamic imports, and no global-state mutation. The one narrow exception --
``compose_summary_fn`` -- is an optional, explicitly bounded pure-function
reference kept only for AES-DATA-003A's legacy composition compatibility
(mission Amendment 3); callers must never pass it anything that is not a
deterministic, I/O-free callable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, FrozenSet, Mapping, Optional, Tuple

# job_id/batch_id already use this exact safe-path-component grammar
# elsewhere in the importer (scripts/pettripfinder/importer/batch.py); pack
# IDs and category IDs reuse it for one consistent ID convention repo-wide.
_SAFE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_SAFE_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


class DomainPackError(ValueError):
    """Base class for every domain-pack contract/registry error. A
    ``ValueError`` subclass, matching the established
    ``BatchManifestError``/``BatchRunError`` convention elsewhere in this
    package."""


class UnknownCategoryError(DomainPackError):
    """Raised by the registry when asked to resolve a category no pack
    declares (doctrine: unknown category lookup must fail clearly, never
    silently fall back)."""


class DuplicateCategoryRegistrationError(DomainPackError):
    """Raised when two packs claim the same category ID."""


def _require_safe_id(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not _SAFE_ID_RE.match(value):
        raise DomainPackError(
            "%s must be a safe lowercase id (got %r)" % (field_name, value))
    return value


def _require_version(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not _SAFE_VERSION_RE.match(value):
        raise DomainPackError(
            "%s must be a MAJOR.MINOR.PATCH version string (got %r)"
            % (field_name, value))
    return value


def _require_no_duplicates(values: Tuple[str, ...], field_name: str) -> None:
    seen = set()
    for v in values:
        if v in seen:
            raise DomainPackError("%s contains a duplicate entry: %r" % (field_name, v))
        seen.add(v)


# --------------------------------------------------------------------------- #
# Capability contracts (AES-DATA-003A: declared vocabulary + shape only --
# no candidate ever carries a populated Capability in this phase).
# --------------------------------------------------------------------------- #

class CapabilityState(str, Enum):
    """A capability's evidenced state -- never inferred. Absence of
    evidence is UNKNOWN, never a default 'false' (doctrine #3)."""

    SUPPORTED = "SUPPORTED"
    EXPLICITLY_ABSENT = "EXPLICITLY_ABSENT"
    UNKNOWN = "UNKNOWN"
    CONFLICTED = "CONFLICTED"


_CAPABILITY_STATE_VALUES = frozenset(s.value for s in CapabilityState)


@dataclass(frozen=True)
class Capability:
    """One normalized, cross-category, evidence-linked service/policy fact.
    ``evidence_index`` is a reference into the owning ``CandidateListing.
    evidence`` tuple (-1 = no evidence, i.e. the state must be UNKNOWN)."""

    capability_id: str
    state: str
    value: str = ""
    high_risk: bool = False
    evidence_index: int = -1
    source_url: str = ""

    def __post_init__(self) -> None:
        _require_safe_id(self.capability_id, "capability_id")
        if self.state not in _CAPABILITY_STATE_VALUES:
            raise DomainPackError("Capability.state must be a CapabilityState value (got %r)"
                                  % (self.state,))
        if self.state != CapabilityState.UNKNOWN.value and self.evidence_index < 0:
            raise DomainPackError(
                "Capability %r has state %r but no evidence_index -- a "
                "non-UNKNOWN capability must reference real evidence"
                % (self.capability_id, self.state))


@dataclass(frozen=True)
class CategoryDetail:
    """Typed, discriminated, idiosyncratic per-category facts that do not
    generalize into a cross-category Capability. Every field's evidence
    still lives in the owning ``CandidateListing.evidence`` list; this is a
    projection/discriminator, not a second evidence store."""

    detail_type: str
    detail_schema_version: str
    fields: Tuple[Tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        _require_safe_id(self.detail_type, "detail_type")
        _require_version(self.detail_schema_version, "detail_schema_version")
        object.__setattr__(self, "fields", tuple(tuple(p) for p in self.fields))


@dataclass(frozen=True)
class SourceRoleSpec:
    """Advisory metadata describing an expected kind of official source for
    a category (e.g. "location", "emergency-hours"). Informational only in
    AES-DATA-003A -- does not change S1/S2 role assignment or any gate."""

    role_id: str
    required: bool = False
    capability_affinity: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_safe_id(self.role_id, "role_id")
        object.__setattr__(self, "capability_affinity", tuple(self.capability_affinity))


# --------------------------------------------------------------------------- #
# DomainPack: the declarative, per-category compatibility descriptor.
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class DomainPack:
    pack_id: str
    category_ids: Tuple[str, ...]
    aliases: Tuple[str, ...] = ()
    allowed_fields: FrozenSet[str] = field(default_factory=frozenset)
    field_order: Tuple[str, ...] = ()
    field_normalizers: Tuple[Tuple[str, str], ...] = ()
    prompt_fragment: str = ""
    required_fields: Tuple[str, ...] = ()
    advisory_fields: Tuple[str, ...] = ()
    high_risk_capabilities: FrozenSet[str] = field(default_factory=frozenset)
    source_roles: Tuple[SourceRoleSpec, ...] = ()
    display_labels: Tuple[Tuple[str, str], ...] = ()
    detail_schema_version: str = ""
    pack_version: str = "1.0.0"
    # Narrowly bounded pure-function reference for AES-DATA-003A legacy
    # composition compatibility ONLY (mission Amendment 3) -- never
    # required, never used for capability projection or gate execution in
    # this phase. Must be deterministic and I/O-free; nothing in this
    # module enforces that beyond convention + the docstring contract.
    compose_summary_fn: Optional[Callable[[Mapping[str, str]], str]] = None

    def __post_init__(self) -> None:
        _require_safe_id(self.pack_id, "pack_id")
        _require_version(self.pack_version, "pack_version")

        if not self.category_ids:
            raise DomainPackError("pack %r must declare at least one category_id"
                                  % self.pack_id)
        for cat in self.category_ids:
            _require_safe_id(cat, "category_id")
        _require_no_duplicates(self.category_ids, "category_ids")

        object.__setattr__(self, "category_ids", tuple(self.category_ids))
        object.__setattr__(self, "aliases", tuple(self.aliases))
        object.__setattr__(self, "allowed_fields", frozenset(self.allowed_fields))
        object.__setattr__(self, "field_order", tuple(self.field_order))
        object.__setattr__(self, "field_normalizers", tuple(
            tuple(p) for p in self.field_normalizers))
        object.__setattr__(self, "required_fields", tuple(self.required_fields))
        object.__setattr__(self, "advisory_fields", tuple(self.advisory_fields))
        object.__setattr__(self, "high_risk_capabilities",
                           frozenset(self.high_risk_capabilities))
        object.__setattr__(self, "source_roles", tuple(self.source_roles))
        object.__setattr__(self, "display_labels", tuple(
            tuple(p) for p in self.display_labels))

        _require_no_duplicates(self.field_order, "field_order")
        for f in self.field_order:
            if f not in self.allowed_fields:
                raise DomainPackError(
                    "pack %r: field_order entry %r is not in allowed_fields"
                    % (self.pack_id, f))

        seen_normalizer_fields = set()
        for f, normalizer_name in self.field_normalizers:
            if f in seen_normalizer_fields:
                raise DomainPackError(
                    "pack %r: field_normalizers has a duplicate entry for field %r"
                    % (self.pack_id, f))
            seen_normalizer_fields.add(f)
            if f not in self.allowed_fields:
                raise DomainPackError(
                    "pack %r: field_normalizers references %r, which is not in "
                    "allowed_fields" % (self.pack_id, f))
            if not normalizer_name or not isinstance(normalizer_name, str):
                raise DomainPackError(
                    "pack %r: field_normalizers[%r] must name a normalizer "
                    "(non-empty string)" % (self.pack_id, f))

        role_ids = tuple(r.role_id for r in self.source_roles)
        _require_no_duplicates(role_ids, "source_roles")

        if self.detail_schema_version:
            _require_version(self.detail_schema_version, "detail_schema_version")

    def compose_summary(self, facts: Mapping[str, str]) -> str:
        """Delegates to the bound legacy composer, when one is wired in.
        Returns "" when this pack has no composer (a future non-legacy
        pack may legitimately have none in early phases)."""
        if self.compose_summary_fn is None:
            return ""
        return self.compose_summary_fn(facts)
