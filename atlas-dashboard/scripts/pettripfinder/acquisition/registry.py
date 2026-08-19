"""Which lane a property gets, and why. Data-driven and versioned.

Brand decisions live in ``routes.json`` and nowhere else. Scattering them
through capture code is how a repository ends up with six half-remembered
opinions about Choice; keeping them in one table means a new brand is a row and
a changed brand is a diff somebody can review.

EVERY ROW CITES A RUN
---------------------
``why`` and ``measured_by`` are required, not decorative. A route that cannot
say which benchmark set it is an opinion, and an opinion is exactly what this
table exists to keep out. The Choice row is the clearest case: it forbids the
Browser API, and it forbids it because that lane was refused fourteen times in
fifteen attempts, which is a fact with a report behind it.

FORBIDDEN IS STRONGER THAN NOT-PREFERRED
----------------------------------------
``forbidden_providers`` exists because "do not prefer" is not enough. Without
it, a Choice property whose unlocker attempt failed would escalate into the one
lane measured to be useless for Choice, and spend three more attempts proving
it again. A forbidden provider is removed from the ladder entirely.

OVERRIDE ORDER
--------------
    property -> domain -> brand -> default

Most specific wins, and the resolved route records which level answered, so a
surprising choice can be traced to the row that made it rather than guessed at.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.acquisition import providers as PROVIDERS  # noqa: E402
from scripts.pettripfinder.acquisition import readers as READERS      # noqa: E402

ROUTES_PATH = Path(__file__).resolve().parent / "routes.json"

DEFAULT_MAX_ATTEMPTS_PER_PROVIDER = 3


class RegistryError(ValueError):
    """The routing registry is invalid."""


@dataclass(frozen=True)
class Route:
    """The resolved lane for one property."""

    provider: str
    fallback_providers: Tuple[str, ...]
    reader: str
    max_attempts_per_provider: int
    resolved_by: str
    why: str
    measured_by: str
    forbidden_providers: Tuple[str, ...] = ()

    @property
    def ladder(self) -> Tuple[str, ...]:
        """Providers in order, with forbidden ones removed.

        Removal happens here rather than at the call site so that no caller can
        accidentally escalate into a lane a measurement has ruled out.
        """
        seen: List[str] = []
        for provider in (self.provider,) + tuple(self.fallback_providers):
            if provider in self.forbidden_providers:
                continue
            if provider not in seen:
                seen.append(provider)
        return tuple(seen)

    def to_dict(self) -> Dict:
        return {"provider": self.provider,
                "fallback_providers": list(self.fallback_providers),
                "forbidden_providers": list(self.forbidden_providers),
                "ladder": list(self.ladder),
                "reader": self.reader,
                "max_attempts_per_provider": self.max_attempts_per_provider,
                "resolved_by": self.resolved_by, "why": self.why,
                "measured_by": self.measured_by}


def load(path: Optional[Path] = None) -> Dict:
    """Read the registry, refusing anything it cannot honour.

    Validation is strict on purpose: a route naming a provider that is not
    registered, or a reader that does not exist, is a routing table that will
    fail at the worst possible moment -- mid-run, after paying for attempts.
    """
    source = Path(path or ROUTES_PATH)
    if not source.exists():
        raise RegistryError("routing registry not found at %s" % source)
    data = json.loads(source.read_text(encoding="utf-8"))

    known_providers = set(PROVIDERS.all_ids())
    for section in ("default",):
        _validate_entry(data.get(section) or {}, known_providers,
                        "%s" % section)
    for level in ("brands", "domains", "properties"):
        for key, entry in (data.get(level) or {}).items():
            _validate_entry(entry, known_providers, "%s.%s" % (level, key))
    return data


def _validate_entry(entry: Mapping, known_providers, where: str) -> None:
    provider = entry.get("provider")
    if provider and provider not in known_providers:
        raise RegistryError("%s routes to unregistered provider %r"
                            % (where, provider))
    for fallback in entry.get("fallback_providers") or ():
        if fallback not in known_providers:
            raise RegistryError("%s falls back to unregistered provider %r"
                                % (where, fallback))
    reader = entry.get("reader")
    if reader:
        READERS.get(reader)          # raises ReaderError on an unknown reader
    if where != "default" and not (entry.get("why")
                                   and entry.get("measured_by")):
        raise RegistryError(
            "%s has no 'why' and 'measured_by'. A route that cannot cite the "
            "run that set it is an opinion." % where)


def _host(url: str) -> str:
    return re.sub(r"^https?://", "", url or "").split("/")[0].lower()


def resolve(*, brand: str, url: str, identity_key: str = "",
            registry: Optional[Mapping] = None) -> Route:
    """The lane for one property. Most specific match wins."""
    data = registry if registry is not None else load()
    layers: List[Tuple[str, Mapping]] = []

    prop = (data.get("properties") or {}).get(identity_key)
    if prop:
        layers.append(("property:%s" % identity_key, prop))
    domain = (data.get("domains") or {}).get(_host(url))
    if domain:
        layers.append(("domain:%s" % _host(url), domain))
    brand_entry = (data.get("brands") or {}).get((brand or "").upper())
    if brand_entry:
        layers.append(("brand:%s" % brand.upper(), brand_entry))
    layers.append(("default", data.get("default") or {}))

    def pick(key, default=None):
        for _, layer in layers:
            if key in layer:
                return layer[key]
        return default

    resolved_by = layers[0][0]
    forbidden = tuple(pick("forbidden_providers", ()) or ())
    provider = pick("provider") or PROVIDERS.BRIGHTDATA_BROWSER
    fallbacks = tuple(pick("fallback_providers", ()) or ())

    if provider in forbidden:
        raise RegistryError(
            "%s names %r as its provider and also forbids it"
            % (resolved_by, provider))

    return Route(
        provider=provider, fallback_providers=fallbacks,
        reader=pick("reader") or READERS.DEFAULT_READER,
        max_attempts_per_provider=int(
            pick("max_attempts_per_provider",
                 DEFAULT_MAX_ATTEMPTS_PER_PROVIDER)),
        resolved_by=resolved_by,
        why=pick("why", "") or "", measured_by=pick("measured_by", "") or "",
        forbidden_providers=forbidden)


def excluded_brands(registry: Optional[Mapping] = None) -> Dict[str, str]:
    data = registry if registry is not None else load()
    return dict(data.get("excluded_brands") or {})


def is_excluded(brand: str, registry: Optional[Mapping] = None) -> bool:
    return (brand or "").upper() in excluded_brands(registry)


def brands(registry: Optional[Mapping] = None) -> Tuple[str, ...]:
    data = registry if registry is not None else load()
    return tuple(sorted(data.get("brands") or {}))


def describe(registry: Optional[Mapping] = None) -> Dict:
    data = registry if registry is not None else load()
    return {"schema": data.get("schema"), "version": data.get("version"),
            "brands": {b: {"provider": e.get("provider"),
                           "reader": e.get("reader"),
                           "forbidden": e.get("forbidden_providers") or [],
                           "measured_by": e.get("measured_by")}
                       for b, e in sorted((data.get("brands") or {}).items())},
            "domains": sorted(data.get("domains") or {}),
            "property_overrides": sorted(data.get("properties") or {}),
            "excluded_brands": sorted(data.get("excluded_brands") or {})}


__all__ = ["ROUTES_PATH", "DEFAULT_MAX_ATTEMPTS_PER_PROVIDER", "RegistryError",
           "Route", "load", "resolve", "excluded_brands", "is_excluded",
           "brands", "describe"]
