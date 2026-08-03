"""PTF-DISCOVERY-001 WO-1A Step 2 -- immutable run context and replay hashing.

Implements ``DiscoveryRunContext`` (amendment v1.1 §A4/§B3) and
``INV-DET-EFFECTIVE-TIME``: deterministic-stage timestamps derive from an
explicit ``effective_time``; network/operational timestamps are excluded from
content hashes and from canonical candidate identity, so a replay of the same
inputs reproduces the same hashes and the same ordering.

WHAT THIS DOES AND DOES NOT CHANGE
----------------------------------
This is mostly *formalization*, not new discipline. The discovery subsystem
already refuses to read a wall clock: ``observed_at`` is threaded explicitly
through every stage (``DiscoveryRecord.observed_at`` is documented as "explicit
date, never wall-clock"; ``RunConfig.observed_at``; ``market_config`` reads its
observation date from the caller, never the file). What was missing was a
single immutable object naming *which versions of which stages* produced a
result, and an explicit statement of what may and may not enter a content hash.

Nothing here changes an existing stage's behavior. No module in the frozen set
is modified.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, fields
from typing import Any, FrozenSet, Mapping

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery.membrane import assert_dataclasses_clean

# --------------------------------------------------------------------------- #
# Stage versions.
#
# These name the *behavioral* version of each deterministic stage. They live
# here rather than in ``constants.py`` because they are governance metadata for
# the run context, not vocabulary the stages themselves consume -- and because
# WO-1A must not edit widely-imported frozen modules.
#
# HONEST LIMITATION: nothing yet enforces that changing a stage bumps its
# version. That enforcement is the same class of problem as the worker's
# contract-version bump (FD-3) and is deliberately left visible rather than
# papered over. Until it exists, these are a convention with a name.
# --------------------------------------------------------------------------- #

NORMALIZER_VERSION = "normalizer-v1"
DEDUPLICATION_VERSION = "dedup-v1"
OFFICIAL_URL_RESOLVER_VERSION = "official-url-v1"
SCORING_VERSION = "scoring-v0"          # no priority scorer exists yet (base §M)
MARKET_REGISTRY_VERSION = "market-registry-v1"
PROVIDER_TERMS_REGISTRY_VERSION = "terms-registry-v0"   # registry lands in Step 10
ADAPTER_REGISTRY_VERSION = "adapter-registry-v1"


# --------------------------------------------------------------------------- #
# Hash inclusion / exclusion (amendment §B3).
# --------------------------------------------------------------------------- #

#: Field names excluded from every content hash. Amendment §B3: the hash
#: INCLUDES canonical field values, version fields and ``effective_time``, and
#: EXCLUDES ``retrieved_at`` / HTTP timing / operational timestamps.
#:
#: ``observed_at`` is deliberately NOT here. In this codebase ``observed_at``
#: *is* the effective time -- an explicit date supplied by the caller, never a
#: wall clock -- so it is a canonical input, not an operational timestamp.
#:
#: ``run_context_ref`` is excluded because it is a pointer to the context that
#: is already mixed into the hash explicitly; including it would make the hash
#: depend on itself.
VOLATILE_HASH_FIELDS: FrozenSet[str] = frozenset({
    "retrieved_at",
    "cache_reference",
    "run_context_ref",
})


def canonical_json(payload: Any) -> str:
    """Compact, sorted, UTF-8 JSON -- the same convention the worker
    contracts use (``services.research_workers.contracts.canonical_json``),
    so hashes are comparable in shape across the two domains."""
    return json.dumps(payload, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), default=str)


def strip_volatile(value: Any, *, volatile: FrozenSet[str] = VOLATILE_HASH_FIELDS) -> Any:
    """Recursively drop operational fields so a replay hashes identically.

    Recursion is correct here (unlike the Membrane's key check) because this
    operates on ``asdict`` output over nested dataclasses, where every mapping
    key is a field name rather than data.
    """
    if isinstance(value, Mapping):
        return {k: strip_volatile(v, volatile=volatile)
                for k, v in value.items() if k not in volatile}
    if isinstance(value, (list, tuple)):
        return [strip_volatile(v, volatile=volatile) for v in value]
    return value


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# The context.
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class DiscoveryRunContext:
    """Immutable per-run version + effective-time bundle (amendment §B3).

    ``effective_time`` is the single source of every deterministic-stage
    timestamp. It is supplied explicitly by the caller (CLI ``--observed-at``,
    or a fixed date in tests) and is never read from a clock here.
    """

    run_id: str
    effective_time: str
    market_registry_version: str = MARKET_REGISTRY_VERSION
    provider_terms_registry_version: str = PROVIDER_TERMS_REGISTRY_VERSION
    scoring_version: str = SCORING_VERSION
    normalizer_version: str = NORMALIZER_VERSION
    deduplication_version: str = DEDUPLICATION_VERSION
    official_url_resolver_version: str = OFFICIAL_URL_RESOLVER_VERSION
    adapter_registry_version: str = ADAPTER_REGISTRY_VERSION
    software_version: str = C.DISCOVERY_VERSION

    def to_dict(self) -> dict:
        return {f.name: getattr(self, f.name) for f in fields(self)}

    @staticmethod
    def from_dict(d: Mapping) -> "DiscoveryRunContext":
        known = {f.name for f in fields(DiscoveryRunContext)}
        return DiscoveryRunContext(**{k: str(v) for k, v in d.items() if k in known})

    def content_hash(self) -> str:
        """Identity of the run context itself."""
        return "sha256:" + _sha256(canonical_json(self.to_dict()))

    def ref(self) -> str:
        """The value stored in a candidate's ``run_context_ref``.

        The ``run_id`` alone, deliberately: a candidate points at *which run*
        produced it, and the run's full version bundle is recoverable from the
        persisted context. Using the content hash here would make the ref
        change whenever an unrelated version field moved, which would churn
        every candidate for no semantic reason.
        """
        return self.run_id


# --------------------------------------------------------------------------- #
# Replay hashing.
# --------------------------------------------------------------------------- #

def content_hash_for(payload: Any, *, context: DiscoveryRunContext) -> str:
    """Deterministic content hash of ``payload`` under ``context``.

    Includes: the payload's canonical field values (volatile fields removed)
    plus every version field and ``effective_time`` from the context.
    Excludes: ``retrieved_at``, ``cache_reference``, ``run_context_ref``.

    Identical inputs + identical context => identical hash. Varying only a
    network retrieval timestamp does not change it.
    """
    body = {
        "payload": strip_volatile(payload),
        "context": context.to_dict(),
    }
    return "sha256:" + _sha256(canonical_json(body))


def candidate_content_hash(candidate, *, context: DiscoveryRunContext) -> str:
    """Content hash of one ``DiscoveryCandidate`` under a run context.

    Imported locally so this module stays importable without pulling the
    serialization layer for callers that only need the context object.
    """
    from scripts.pettripfinder.discovery.serialization import candidate_to_dict

    return content_hash_for(candidate_to_dict(candidate), context=context)


def candidates_content_hash(candidates, *, context: DiscoveryRunContext) -> str:
    """Content hash over an ordered candidate set -- the replayable identity
    of a whole run's output. Ordering is part of the identity: ``deduplicate``
    already returns candidates sorted by ``candidate_id``, and a replay that
    reordered them would be a real difference, not a cosmetic one."""
    from scripts.pettripfinder.discovery.serialization import candidate_to_dict

    body = [strip_volatile(candidate_to_dict(c)) for c in candidates]
    return content_hash_for(body, context=context)


assert_dataclasses_clean(DiscoveryRunContext, context="discovery.run_context")
