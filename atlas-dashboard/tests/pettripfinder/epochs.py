"""PTF-FACTORY-THROUGHPUT-HARDENING-001 -- epochs, cohorts and supersession.

THE PROBLEM THIS NAMES
----------------------
A one-shot work order (a founder pass, a recovery, an application) verifies its
own work with a test suite. Written on the day, the suite asserts over "every
record in the package" -- which, on the day, IS the cohort the order created.
Grow the package under a later order and every such assertion fails without a
single record of the original cohort having moved. Dayton APPLICATION-002 paid
that cost in 85 failures across 19 modules, none of them a defect.

The fix is to scope, never to relax. A historical suite is about a COHORT: the
records its order created, identified by the ledger that authorised them, by
the caveat naming the order, or by their identity keys. Scoped that way, the
suite keeps every assertion it had -- the count becomes a statement about the
cohort rather than an accident of the package's size -- and it keeps catching
the mutation it was written to catch.

VOCABULARY
----------
    HistoricalEpoch     what a closed work order left true (published 47 …),
                        declared in that order's suite, immutable.
    current             the market as it stands now -- pettripfinder.market_state,
                        never restated in a historical suite.
    cohort(...)         the subset of the live package a historical order owns.
    superseded(...)     an obsolete CURRENT-state assertion, retired by a NAMED
                        later work order. The test still exists and still runs
                        up to the point where it would assert the stale fact.
    moved_by_later_work an authorization's markets that later orders re-authored,
                        read from pins/supersessions.json -- named, never blanket.

WHAT IS NOT ALLOWED
-------------------
Skipping a module because a newer market state exists. The decorator here takes
a work-order id and a reason, refuses an id that is not one, and records every
supersession so a contract test can enumerate them. A suite that describes a
genuinely closed epoch marks each superseded assertion; it does not vanish.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import (Callable, Dict, FrozenSet, Iterable, List, Mapping,
                    Optional, Sequence, Tuple)

import pytest

PINS_DIR = Path(__file__).resolve().parent / "pins"
SUPERSESSIONS_PATH = PINS_DIR / "supersessions.json"
SUPERSESSIONS_SCHEMA = "ptf-supersession-registry/1.0"

#: A work order id. Every supersession and every epoch must name one.
WORK_ORDER_RE = re.compile(r"^PTF-[A-Z0-9]+(?:-[A-Z0-9]+)*-\d{3}[A-Z]?$")


def is_work_order(value: object) -> bool:
    return isinstance(value, str) and WORK_ORDER_RE.match(value) is not None


def _require_work_order(value: object, what: str) -> str:
    if not is_work_order(value):
        raise ValueError("%s must name a work order (PTF-…-NNN), got %r"
                         % (what, value))
    return value  # type: ignore[return-value]


# --------------------------------------------------------------------------- #
# Historical epochs.
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class HistoricalEpoch:
    """What one closed work order left true, at the time.

    ``facts`` holds the numbers the order's suite may assert about ITS OWN
    cohort -- ``pet_friendly=47`` -- and nothing about the market today. A
    suite reads them through :meth:`fact` so a typo fails loudly instead of
    returning ``None``.
    """

    work_order: str
    market_id: str
    facts: Mapping[str, int] = field(default_factory=dict)
    #: Later orders that moved the market past this epoch. Informational: a
    #: superseded CURRENT-state assertion names its superseder explicitly.
    superseded_by: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_work_order(self.work_order, "HistoricalEpoch.work_order")
        for later in self.superseded_by:
            _require_work_order(later, "HistoricalEpoch.superseded_by")

    def fact(self, name: str) -> int:
        if name not in self.facts:
            raise KeyError("%s declares no fact %r" % (self.work_order, name))
        return self.facts[name]

    @property
    def is_superseded(self) -> bool:
        return bool(self.superseded_by)


# --------------------------------------------------------------------------- #
# Cohorts: which records of the live package a historical order owns.
# --------------------------------------------------------------------------- #

Selector = Callable[[Mapping], bool]


def _approval(record: Mapping) -> Mapping:
    return record.get("approval") or {}


def _caveats(record: Mapping) -> List[str]:
    return list(_approval(record).get("caveats") or [])


def by_ledger(ledger_name: str) -> Selector:
    """Records whose approval names ``ledger_name`` as its decision source."""
    def select(record: Mapping) -> bool:
        source = _approval(record).get("decision_source") or {}
        return source.get("ledger") == ledger_name
    select.__name__ = "by_ledger(%s)" % ledger_name
    return select


def by_caveat(work_order: str) -> Selector:
    """Records whose approval caveats name ``work_order``."""
    _require_work_order(work_order, "by_caveat")
    def select(record: Mapping) -> bool:
        return any(work_order in c for c in _caveats(record))
    select.__name__ = "by_caveat(%s)" % work_order
    return select


def not_by_caveat(*work_orders: str) -> Selector:
    """Records NOT published by any of the named later orders.

    The selector for an order whose records carry no marker of their own:
    everything a LATER order did not publish is what the earlier one verified.
    """
    for w in work_orders:
        _require_work_order(w, "not_by_caveat")
    def select(record: Mapping) -> bool:
        return not any(w in c for w in work_orders for c in _caveats(record))
    select.__name__ = "not_by_caveat(%s)" % ",".join(work_orders)
    return select


def by_identity_keys(keys: Iterable[str], *, field_name: str = "key") -> Selector:
    """Records whose ``field_name`` is one of ``keys``."""
    wanted: FrozenSet[str] = frozenset(keys)
    def select(record: Mapping) -> bool:
        return record.get(field_name) in wanted
    select.__name__ = "by_identity_keys(%d)" % len(wanted)
    return select


def cohort(records: Sequence[Mapping], selector: Selector) -> List[Mapping]:
    """The records ``selector`` admits, in package order."""
    return [r for r in records if selector(r)]


def split(records: Sequence[Mapping], selector: Selector
          ) -> Tuple[List[Mapping], List[Mapping]]:
    """``(cohort, everything_else)`` -- for suites that assert a wider
    invariant over the rest, separately."""
    inside, outside = [], []
    for r in records:
        (inside if selector(r) else outside).append(r)
    return inside, outside


def assert_cohort_size(records: Sequence[Mapping], selector: Selector,
                       expected: int, *, epoch: HistoricalEpoch) -> List[Mapping]:
    """The cohort is exactly ``expected`` records, and says whose it is."""
    found = cohort(records, selector)
    assert len(found) == expected, (
        "%s: cohort %s holds %d records, expected %d"
        % (epoch.work_order, getattr(selector, "__name__", "selector"),
           len(found), expected))
    return found


# --------------------------------------------------------------------------- #
# Supersession: retiring an obsolete CURRENT-state assertion, by name.
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class Supersession:
    superseded_by: str
    what: str
    where: str


#: Every supersession declared in this process, in declaration order. A
#: contract test enumerates it so a supersession cannot be silent.
DECLARED_SUPERSESSIONS: List[Supersession] = []


def _record(by: str, what: str, where: str) -> Supersession:
    entry = Supersession(_require_work_order(by, "superseded(by=…)"),
                         what.strip(), where)
    if not entry.what:
        raise ValueError("superseded(): say WHAT current-state assertion was retired")
    DECLARED_SUPERSESSIONS.append(entry)
    return entry


def superseded_reason(by: str, what: str) -> str:
    return "SUPERSEDED by %s: %s" % (by, what)


def superseded(*, by: str, what: str):
    """Decorator: this whole test asserted a CURRENT state that ``by`` moved.

    Use it only on a test whose ENTIRE content is the stale current-state
    assertion. A test that also carries historical assertions should keep them
    running and call :func:`superseded_assertion` at the point the stale
    assertion used to be.
    """
    # Validate NOW, at declaration, so a bad id fails at import rather than
    # silently decorating a test that is then skipped for no named reason.
    _require_work_order(by, "superseded(by=…)")
    if not what.strip():
        raise ValueError("superseded(): say WHAT current-state assertion was retired")

    def decorate(fn):
        entry = _record(by, what, getattr(fn, "__qualname__", repr(fn)))
        return pytest.mark.skip(reason=superseded_reason(entry.superseded_by,
                                                         entry.what))(fn)
    return decorate


def superseded_assertion(*, by: str, what: str) -> None:
    """Inside a test: the historical assertions above this line RAN; the
    current-state assertion that used to follow is retired by ``by``."""
    entry = _record(by, what, "inline")
    pytest.skip(superseded_reason(entry.superseded_by, entry.what))


def whole_market_counts_or_superseded(epoch: HistoricalEpoch, current,
                                      fields: Mapping[str, str]) -> None:
    """A closed order's WHOLE-MARKET counts, asserted against the pin.

    While the market has not moved past this order -- the pin's
    ``last_moved_by`` is still this order -- the epoch's facts must equal the
    current pin exactly, field for field. Once a later order has moved the
    market, those assertions are obsolete CURRENT-state claims and are
    superseded BY THAT ORDER'S NAME, read from the pin rather than typed.
    The historical assertions around this call keep running either way.

    ``fields`` maps an epoch fact name to the pin attribute it corresponds to,
    e.g. ``{"pet_friendly": "pet_friendly", "no_pets": "verified_no_pets"}``.
    """
    if current.last_moved_by == epoch.work_order:
        for fact_name, attr in fields.items():
            assert epoch.fact(fact_name) == getattr(current, attr), (
                "%s: %s was %d when the order closed; the pin says %s is %d "
                "yet still names this order as the last mover"
                % (epoch.work_order, fact_name, epoch.fact(fact_name), attr,
                   getattr(current, attr)))
        return
    superseded_assertion(
        by=current.last_moved_by,
        what="whole-market counts of %s (%s)" % (
            epoch.work_order,
            ", ".join("%s=%s" % (k, epoch.fact(k)) for k in fields)))


# --------------------------------------------------------------------------- #
# Consumed authorizations: which markets later work moved.
# --------------------------------------------------------------------------- #

def supersession_registry() -> Dict:
    doc = json.loads(SUPERSESSIONS_PATH.read_text(encoding="utf-8"))
    if doc.get("schema") != SUPERSESSIONS_SCHEMA:
        raise ValueError("%s: expected schema %s, found %r"
                         % (SUPERSESSIONS_PATH.name, SUPERSESSIONS_SCHEMA,
                            doc.get("schema")))
    return doc


def moved_by_later_work(authorization_id: str) -> Dict[str, str]:
    """``market_id -> work order`` for the markets later work re-authored out
    from under a CONSUMED authorization. Empty for one nothing has moved.

    Raises ``KeyError`` for an authorization the registry does not list: a
    test re-verifying an unregistered authorization must bind EVERY market,
    which is the honest default.
    """
    registry = supersession_registry()["authorizations"]
    if authorization_id not in registry:
        raise KeyError("%s is not in %s" % (authorization_id, SUPERSESSIONS_PATH.name))
    moved = registry[authorization_id].get("moved_by_later_work") or {}
    for market, order in moved.items():
        _require_work_order(order, "%s.moved_by_later_work[%s]"
                            % (authorization_id, market))
    return dict(moved)


def markets_moved_since(authorization_id: str) -> FrozenSet[str]:
    return frozenset(moved_by_later_work(authorization_id))


__all__ = [
    "SUPERSESSIONS_PATH", "SUPERSESSIONS_SCHEMA", "WORK_ORDER_RE",
    "is_work_order", "HistoricalEpoch", "Selector", "by_ledger", "by_caveat",
    "not_by_caveat", "by_identity_keys", "cohort", "split",
    "assert_cohort_size", "Supersession", "DECLARED_SUPERSESSIONS",
    "superseded", "superseded_assertion", "superseded_reason",
    "whole_market_counts_or_superseded",
    "supersession_registry", "moved_by_later_work", "markets_moved_since",
]
