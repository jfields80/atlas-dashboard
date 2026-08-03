"""PTF-DISCOVERY-001 WO-1A Step 10 -- the Provider Terms Registry.

Base architecture §G and ``INV-PROVIDER-AUTOSTOP``'s terms half. **No provider
may be enabled without a reviewed entry.**

FD-1: every provider starts ``UNREVIEWED``. The committed entries in
``config/provider_terms.json`` were transcribed from constants and comments
already in the discovery code -- they are a record of what the code believes,
not of what a human verified. Treating them as reviewed would convert an
engineer's comment into a compliance artifact, which is the precise failure
this registry exists to prevent.

Provider Zero is ``NOT_APPLICABLE`` rather than ``UNREVIEWED``: it reads local
cached and manually supplied inputs, makes zero network requests and incurs
zero spend, so it has no third-party terms surface at all.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, FrozenSet, Optional, Sequence, Tuple

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery.membrane import assert_dataclasses_clean

_CONFIG_DIR = Path(__file__).resolve().parent / "config"
_DEFAULT_FILENAME = "provider_terms.json"

# Review states.
UNREVIEWED = "UNREVIEWED"
REVIEWED = "REVIEWED"
NOT_APPLICABLE = "NOT_APPLICABLE"
REVIEW_STATES = frozenset({UNREVIEWED, REVIEWED, NOT_APPLICABLE})

PROVIDER_ZERO = "PROVIDER_ZERO"


class TermsRegistryError(ValueError):
    """Raised when a provider is used without a usable terms entry."""


@dataclass(frozen=True)
class ProviderTermsEntry:
    provider_name: str
    review_state: str = UNREVIEWED
    last_terms_review_date: Optional[str] = None
    review_freshness_days: Optional[int] = None
    enabled: bool = False
    permitted_use: Tuple[str, ...] = ()
    permitted_storage: str = "unknown"
    required_attribution: Optional[str] = None
    retention_limits_days: Optional[int] = None
    prohibited_fields: Tuple[str, ...] = ()
    allowed_persistence_fields: Tuple[str, ...] = ()
    transcribed_from: str = ""
    operator_notes: str = ""

    def validate(self) -> None:
        if self.review_state not in REVIEW_STATES:
            raise TermsRegistryError("unknown review_state: %r" % self.review_state)
        if self.review_state == REVIEWED and not self.last_terms_review_date:
            raise TermsRegistryError(
                "%s claims REVIEWED with no review date" % self.provider_name)

    def is_stale(self, *, as_of: str) -> bool:
        """Reviewed-but-expired counts as unusable. Explicit date, no clock."""
        if self.review_state != REVIEWED:
            return True
        if not self.last_terms_review_date or not self.review_freshness_days:
            return True
        try:
            reviewed = date.fromisoformat(self.last_terms_review_date)
            now = date.fromisoformat(as_of)
        except ValueError:
            return True
        return now > reviewed + timedelta(days=self.review_freshness_days)

    def to_dict(self) -> dict:
        return {
            "provider_name": self.provider_name, "review_state": self.review_state,
            "last_terms_review_date": self.last_terms_review_date,
            "review_freshness_days": self.review_freshness_days,
            "enabled": self.enabled, "permitted_use": list(self.permitted_use),
            "permitted_storage": self.permitted_storage,
            "required_attribution": self.required_attribution,
            "retention_limits_days": self.retention_limits_days,
            "prohibited_fields": list(self.prohibited_fields),
            "allowed_persistence_fields": list(self.allowed_persistence_fields),
            "transcribed_from": self.transcribed_from,
            "operator_notes": self.operator_notes,
        }


@dataclass(frozen=True)
class ProviderTermsRegistry:
    registry_version: str
    entries: Tuple[ProviderTermsEntry, ...]

    def get(self, provider_name: str) -> Optional[ProviderTermsEntry]:
        for e in self.entries:
            if e.provider_name == provider_name:
                return e
        return None

    def provider_names(self) -> Tuple[str, ...]:
        return tuple(sorted(e.provider_name for e in self.entries))


def _entry_from_dict(d: dict) -> ProviderTermsEntry:
    limits = d.get("request_limits") or {}
    entry = ProviderTermsEntry(
        provider_name=str(d["provider_name"]),
        review_state=str(d.get("review_state", UNREVIEWED)),
        last_terms_review_date=d.get("last_terms_review_date"),
        review_freshness_days=d.get("review_freshness_days"),
        enabled=bool(d.get("enabled", False)),
        permitted_use=tuple(d.get("permitted_use") or ()),
        permitted_storage=str(d.get("permitted_storage", "unknown")),
        required_attribution=d.get("required_attribution"),
        retention_limits_days=d.get("retention_limits_days"),
        prohibited_fields=tuple(d.get("prohibited_fields") or ()),
        allowed_persistence_fields=tuple(d.get("allowed_persistence_fields") or ()),
        transcribed_from=str(d.get("transcribed_from", "")),
        operator_notes=str(d.get("operator_notes", "")))
    entry.validate()
    return entry


def load_registry(path: Optional[Path] = None) -> ProviderTermsRegistry:
    p = Path(path) if path else (_CONFIG_DIR / _DEFAULT_FILENAME)
    data = json.loads(p.read_text(encoding="utf-8"))
    return ProviderTermsRegistry(
        registry_version=str(data.get("registry_version", "")),
        entries=tuple(_entry_from_dict(e) for e in data.get("providers", [])))


# --------------------------------------------------------------------------- #
# The gate.
# --------------------------------------------------------------------------- #

def assert_live_use_permitted(provider_name: str, *, registry: ProviderTermsRegistry,
                              as_of: str) -> None:
    """Fail closed unless this provider may make a LIVE call right now.

    Provider Zero is exempt by construction, not by exception: it has no
    third-party terms surface because it makes no third-party request.
    """
    if provider_name == PROVIDER_ZERO:
        return

    entry = registry.get(provider_name)
    if entry is None:
        raise TermsRegistryError(
            "%s has no Provider Terms Registry entry and cannot be instantiated"
            % provider_name)
    if entry.review_state == NOT_APPLICABLE:
        return
    if entry.review_state != REVIEWED:
        raise TermsRegistryError(
            "%s terms are %s -- no live call is permitted until an official "
            "terms entry is reviewed and approved (FD-1)"
            % (provider_name, entry.review_state))
    if not entry.enabled:
        raise TermsRegistryError("%s is reviewed but not enabled" % provider_name)
    if entry.is_stale(as_of=as_of):
        raise TermsRegistryError(
            "%s terms review is stale as of %s and the provider is disabled"
            % (provider_name, as_of))


def live_use_permitted(provider_name: str, *, registry: ProviderTermsRegistry,
                       as_of: str) -> bool:
    try:
        assert_live_use_permitted(provider_name, registry=registry, as_of=as_of)
        return True
    except TermsRegistryError:
        return False


def attribution_for(provider_name: str, *, registry: ProviderTermsRegistry) -> str:
    entry = registry.get(provider_name)
    return (entry.required_attribution or "") if entry else ""


def summarize(registry: ProviderTermsRegistry) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for e in registry.entries:
        counts[e.review_state] = counts.get(e.review_state, 0) + 1
    return dict(sorted(counts.items()))


assert_dataclasses_clean(ProviderTermsEntry, ProviderTermsRegistry,
                         context="discovery.terms_registry")
