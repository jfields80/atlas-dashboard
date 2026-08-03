"""PTF-DISCOVERY-001 WO-1A Step 1 -- the structural Membrane.

Implements ``INV-MEMBRANE-FIELD-DENYLIST`` (PTF-DISCOVERY-001 amendment
v1.1 §A1/§C): no discovery-domain record and no verification-queue entry
may *declare* a field whose name is a pet-policy field name.

WHY THIS EXISTS
---------------
Discovery answers "which hotel is this, where is it, what is its official
URL, and does a capture adapter support it". It must never answer "what is
this hotel's pet policy". Until now that separation held by convention and
two spot tests. This module makes it structural: a class that declares a
denylisted field fails at import, so no instance of it can ever exist.

THE ONE RULE THAT MATTERS
-------------------------
**This denylist inspects NAMES ONLY -- declared dataclass field names and
serialized mapping keys. It NEVER inspects values.**

That is not a performance shortcut; it is the difference between a working
invariant and a broken one. ``QueueEntry.required_fields`` legitimately
carries every denylisted token *as a value*
(``build_capture_queue.py`` -> ``list(vocabulary.POLICY_FIELDS)``): it is a
request telling the worker *which fields to go look for* on the official
page, and it carries no policy data whatsoever. A value-scanning denylist
would reject every valid production queue, and the natural "fix" for that
would be to weaken the invariant -- which is the worst available outcome.
So: names, never values. If you are about to add a value check here, stop
and re-read this paragraph.

SCOPE -- WHERE THIS MUST NOT BE APPLIED
---------------------------------------
Only the discovery domain and the queue entry are governed. The policy
domain legitimately declares every one of these names, because producing
those facts is its entire job:

  * ``services.research_workers.contracts.WorkerResult`` / ``ProposedField``
  * ``services.research_workers.routing.RoutingEnvelope``
  * ``services.research_workers.vocabulary.POLICY_FIELDS``
  * the importer's evidence/candidate models

Applying this denylist to any of those would disable the policy pipeline.
"""

from __future__ import annotations

import dataclasses
import re
from typing import Any, FrozenSet, Iterable, Mapping


class MembraneViolation(ValueError):
    """Raised when a discovery record or queue entry declares a policy field.

    Subclasses ``ValueError`` so existing callers that catch ``ValueError``
    around queue loading (which raises ``QueueError``, also a ``ValueError``)
    keep working unchanged.
    """


# --------------------------------------------------------------------------- #
# The denylists.
# --------------------------------------------------------------------------- #

#: The normative denylist, verbatim from amendment v1.1 §C
#: (``INV-MEMBRANE-FIELD-DENYLIST``). Fourteen names. Do not edit without
#: amending the architecture document -- this set IS the contract.
POLICY_FIELD_DENYLIST: FrozenSet[str] = frozenset({
    "pets_allowed",
    "dogs",
    "cats",
    "species",
    "maximum_pets",
    "weight_limit",
    "breed_restrictions",
    "pet_fee",
    "fee_basis",
    "fee_scope",
    "deposit",
    "compatibility",
    "verification_date",
    "policy_quote",
})

#: Additional names denied in the discovery domain specifically. These are
#: not in the amendment's normative set because the amendment assumed
#: third-party pet hints would be *captured and quarantined* inside a
#: ``DiscoveryPetSignal``. This implementation is stronger: the Google
#: Places field mask (``constants.GOOGLE_FIELD_MASK``) never requests
#: ``allowsDogs`` at all, so the hint never enters the system and there is
#: no ``DiscoveryPetSignal`` type to quarantine it into. Denying the names
#: outright keeps it that way.
#:
#: ``pet_policy`` is included because it is the *seed CSV's* policy column
#: (``launch_packages/pettripfinder/seed_businesses.csv``). A discovery
#: record declaring it would be one assignment away from publication.
DISCOVERY_SIGNAL_DENYLIST: FrozenSet[str] = frozenset({
    "allows_dogs",
    "pet_friendly",
    "dog_friendly",
    "pet_policy",
})

#: What discovery-domain classes and the queue entry are checked against.
DISCOVERY_DENYLIST: FrozenSet[str] = POLICY_FIELD_DENYLIST | DISCOVERY_SIGNAL_DENYLIST


# --------------------------------------------------------------------------- #
# Name normalization.
# --------------------------------------------------------------------------- #

_CAMEL_BOUNDARY = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


def normalize_field_name(name: str) -> str:
    """``petsAllowed`` -> ``pets_allowed``; ``PetFee`` -> ``pet_fee``.

    Providers speak camelCase and Atlas speaks snake_case; a denylist that
    only understood one of them would be trivially evaded by transcribing a
    provider field verbatim. Matching is exact-after-normalization, never
    substring -- substring matching would reject legitimate names like
    ``compatibility_version`` or ``deposit_required_by_operator`` and push
    someone toward loosening the rule.
    """
    return _CAMEL_BOUNDARY.sub("_", str(name)).lower()


def _violations(names: Iterable[str], denylist: FrozenSet[str]) -> list:
    hits = {
        str(n) for n in names
        if normalize_field_name(n) in denylist
    }
    return sorted(hits)


# --------------------------------------------------------------------------- #
# Field-name enforcement (the primary, structural guarantee).
# --------------------------------------------------------------------------- #

def assert_no_policy_fields(target: Any, *, context: str = "",
                            denylist: FrozenSet[str] = DISCOVERY_DENYLIST) -> None:
    """Reject a dataclass (class or instance) that DECLARES a policy field.

    Called at *import time* on each discovery-domain class rather than in
    ``__post_init__`` on each instance. That is deliberate and is the
    stronger guarantee of the two: a dataclass's declared fields are fixed
    when the class object is created, so checking once at import makes it
    impossible for a violating class to exist at all -- there is no
    constructor left to reach. It also costs nothing per record, which
    matters because deduplication constructs candidates in a hot loop.
    """
    if not dataclasses.is_dataclass(target):
        raise TypeError("assert_no_policy_fields expects a dataclass, got %r" % (target,))
    found = _violations((f.name for f in dataclasses.fields(target)), denylist)
    if found:
        name = getattr(target, "__name__", type(target).__name__)
        raise MembraneViolation(
            "INV-MEMBRANE-FIELD-DENYLIST: %s%s declares policy field(s) %s. "
            "Discovery records and queue entries may not carry pet-policy "
            "fields; the official-source worker is the sole producer of "
            "policy facts."
            % (name, (" in %s" % context) if context else "", ", ".join(found)))


def assert_no_policy_keys(mapping: Mapping, *, context: str = "",
                          denylist: FrozenSet[str] = DISCOVERY_DENYLIST,
                          recursive: bool = False) -> None:
    """Reject a serialized mapping that carries a policy field as a KEY.

    ``recursive`` defaults to **False** on purpose. Top-level keys of a
    serialized record are schema (field names). Nested maps are frequently
    *data*-keyed -- ``import_plan``'s ``provider_ids`` is
    ``{provider_name: provider_record_id}``, and ``coverage``'s counters are
    keyed by query id, category and municipality. Recursing into those would
    be checking data, which is the same category error as checking values.

    Pass ``recursive=True`` only where every nested key is known to be a
    field name -- i.e. output of ``dataclasses.asdict`` over nested
    dataclasses, which is exactly what ``serialization.py`` produces.
    """
    if not isinstance(mapping, Mapping):
        raise TypeError("assert_no_policy_keys expects a mapping, got %r" % type(mapping))
    found = _violations(mapping.keys(), denylist)
    if found:
        raise MembraneViolation(
            "INV-MEMBRANE-FIELD-DENYLIST: serialized %s carries policy key(s) %s"
            % (context or "mapping", ", ".join(found)))
    if recursive:
        for value in mapping.values():
            _assert_nested(value, context=context, denylist=denylist)


def _assert_nested(value: Any, *, context: str, denylist: FrozenSet[str]) -> None:
    if isinstance(value, Mapping):
        assert_no_policy_keys(value, context=context, denylist=denylist, recursive=True)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _assert_nested(item, context=context, denylist=denylist)


def assert_dataclasses_clean(*targets: Any, context: str = "",
                             denylist: FrozenSet[str] = DISCOVERY_DENYLIST) -> None:
    """Import-time convenience: check several classes in one call."""
    for target in targets:
        assert_no_policy_fields(target, context=context, denylist=denylist)
