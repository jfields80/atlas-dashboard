"""``ptf-market-coverage-completion/1.0`` -- has the factory done everything it can?

WHY A MARKET NEEDS THIS ARTIFACT
--------------------------------
St. Louis and Louisville each needed a separate coverage-expansion work order
after their first acquisition pass, because nothing in the factory asked the
question this document answers: not "did a paid pass end?" but "is there any
identity in this census the factory could still move WITHOUT a human?". A market
that cannot answer that has no business calling itself complete, and a founder
handed its review packet is being asked to decide 63 hotels while 65 more sit
unrouted for reasons a free URL recovery would have fixed.

So the founder-review gate reads this document, and the document is built the
same way the closure ledger is: over EVERY census identity, by set, with one
state each, and it refuses to say READY while any identity's next state is one
the factory can reach on its own.

TWO KINDS OF NEXT-STATE
-----------------------
Every identity gets exactly one ``coverage_state`` (where it sits in the funnel)
and one ``next_state`` (what would move it). A next-state is either

    TERMINAL FOR THE FACTORY   a human, a new authorisation, a new lane in the
                               registry, or a routing repair is needed. The
                               factory has nothing left to try automatically.
    FACTORY_CAN_PROCEED        a phase the factory owns has not yet run for this
                               identity: a recovery, a reroute, an acquisition
                               on an approved lane.

``READY_FOR_FOUNDER_REVIEW`` is true only when no identity is in the second
kind -- and it may be true with a great many unresolved identities, so long as
each one says, in a closed vocabulary, why the factory stopped.

THE DENOMINATOR RULE, AGAIN
---------------------------
``reconcile`` compares the identity SET of the rows to the census, the same way
``contracts.closure`` does. A coverage report over the wrong membership is the
failure the partition contract already names, and it is refused here too.
"""

from __future__ import annotations

from collections import Counter, OrderedDict
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

SCHEMA = "ptf-market-coverage-completion/1.0"

# --------------------------------------------------------------------------- #
# Coverage states -- where an identity sits in the funnel. Exactly one each.
# --------------------------------------------------------------------------- #

NOT_ACTIVE = "NOT_ACTIVE"
UNROUTED_NEEDS_OFFICIAL_URL = "UNROUTED_NEEDS_OFFICIAL_URL"
UNROUTED_NEEDS_PROPERTY_URL = "UNROUTED_NEEDS_PROPERTY_URL"
UNROUTED_NEEDS_FIRST_PARTY_URL = "UNROUTED_NEEDS_FIRST_PARTY_URL"
UNROUTED_BRAND_EXCLUDED = "UNROUTED_BRAND_EXCLUDED"
ROUTED_NEVER_ATTEMPTED = "ROUTED_NEVER_ATTEMPTED"
ROUTED_BUDGET_DEFERRED = "ROUTED_BUDGET_DEFERRED"
ROUTED_ALTERNATE_LANE_AVAILABLE = "ROUTED_ALTERNATE_LANE_AVAILABLE"
ROUTED_ALTERNATE_LANE_REQUIRED = "ROUTED_ALTERNATE_LANE_REQUIRED"
SETTLED_FOUNDER_CANDIDATE = "SETTLED_FOUNDER_CANDIDATE"
SETTLED_VALID_NOT_PUBLICATION_GRADE = "SETTLED_VALID_NOT_PUBLICATION_GRADE"
#: The page was read, and nobody has yet asked whether the capture is
#: publication grade -- the state every VALID row is in before closure runs.
SETTLED_VALID_GRADE_PENDING = "SETTLED_VALID_GRADE_PENDING"
SETTLED_POLICY_NOT_FOUND = "SETTLED_POLICY_NOT_FOUND"
SETTLED_IDENTITY_MISMATCH = "SETTLED_IDENTITY_MISMATCH"

COVERAGE_STATES: Tuple[str, ...] = (
    NOT_ACTIVE, UNROUTED_NEEDS_OFFICIAL_URL, UNROUTED_NEEDS_PROPERTY_URL,
    UNROUTED_NEEDS_FIRST_PARTY_URL, UNROUTED_BRAND_EXCLUDED,
    ROUTED_NEVER_ATTEMPTED, ROUTED_BUDGET_DEFERRED,
    ROUTED_ALTERNATE_LANE_AVAILABLE, ROUTED_ALTERNATE_LANE_REQUIRED,
    SETTLED_FOUNDER_CANDIDATE, SETTLED_VALID_NOT_PUBLICATION_GRADE,
    SETTLED_VALID_GRADE_PENDING, SETTLED_POLICY_NOT_FOUND,
    SETTLED_IDENTITY_MISMATCH,
)

# --------------------------------------------------------------------------- #
# Next-states -- what would move the identity. Terminal ones need a human, a
# new authorisation, a registry change or a repair; the others name a phase the
# factory itself has not yet run for this identity.
# --------------------------------------------------------------------------- #

NEXT_CENSUS_REVIEW = "NEEDS_CENSUS_REVIEW"
NEXT_OFFICIAL_URL = "NEEDS_OFFICIAL_URL"
NEXT_PROPERTY_URL = "NEEDS_PROPERTY_URL"
NEXT_FIRST_PARTY_URL = "NEEDS_FIRST_PARTY_URL"
NEXT_ROUTE_REGISTRY_DECISION = "NEEDS_ROUTE_REGISTRY_DECISION"
NEXT_BUDGET_AUTHORIZATION = "NEEDS_BUDGET_AUTHORIZATION"
NEXT_ALTERNATE_LANE = "RETRY_REQUIRES_ALTERNATE_LANE"
NEXT_FOUNDER_DECISION = "AWAITING_FOUNDER_DECISION"
NEXT_POLICY_ARTIFACT = "NEEDS_POLICY_ARTIFACT"
NEXT_NONE_PAGE_SILENT = "NONE_PAGE_IS_SILENT"
NEXT_ROUTING_REPAIR = "NEEDS_ROUTING_REPAIR"

NEXT_RUN_ZERO_COST_RECOVERY = "FACTORY_RUN_ZERO_COST_RECOVERY"
NEXT_RUN_ACQUISITION = "FACTORY_RUN_ACQUISITION"
NEXT_RUN_ALTERNATE_LANE = "FACTORY_RUN_ALTERNATE_LANE_ACQUISITION"

TERMINAL_NEXT_STATES: Tuple[str, ...] = (
    NEXT_CENSUS_REVIEW, NEXT_OFFICIAL_URL, NEXT_PROPERTY_URL,
    NEXT_FIRST_PARTY_URL, NEXT_ROUTE_REGISTRY_DECISION,
    NEXT_BUDGET_AUTHORIZATION, NEXT_ALTERNATE_LANE, NEXT_FOUNDER_DECISION,
    NEXT_POLICY_ARTIFACT, NEXT_NONE_PAGE_SILENT, NEXT_ROUTING_REPAIR,
)
FACTORY_NEXT_STATES: Tuple[str, ...] = (
    NEXT_RUN_ZERO_COST_RECOVERY, NEXT_RUN_ACQUISITION, NEXT_RUN_ALTERNATE_LANE,
)
NEXT_STATES: Tuple[str, ...] = TERMINAL_NEXT_STATES + FACTORY_NEXT_STATES

NEXT_STATE_MEANINGS: Dict[str, str] = {
    NEXT_CENSUS_REVIEW:
        "The census does not admit this identity as active lodging in a "
        "corridor; a person reviews its presence and category.",
    NEXT_OFFICIAL_URL:
        "No official URL is known and every zero-cost source on disk has been "
        "asked; a person finds the property's own page.",
    NEXT_PROPERTY_URL:
        "The only URL on record is a brand index, locator or search page, and "
        "no recovered property page bound safely; a person replaces it.",
    NEXT_FIRST_PARTY_URL:
        "The only URL on record is a third-party listing; a person finds the "
        "property's own surface.",
    NEXT_ROUTE_REGISTRY_DECISION:
        "The routing registry excludes this brand on a measured cost or "
        "capability basis; only a registry change can route it.",
    NEXT_BUDGET_AUTHORIZATION:
        "Routed and attemptable, but the last paid pass stopped on its cap "
        "before reaching it; a new spend authorisation is needed.",
    NEXT_ALTERNATE_LANE:
        "Every approved lane was tried on this URL and answered nothing; a "
        "same-lane retry does not convert. Needs a lane the registry does not "
        "yet approve, an attended capture, or a routing repair. NOT settled.",
    NEXT_FOUNDER_DECISION:
        "A publication-grade observation exists; the founder decides.",
    NEXT_POLICY_ARTIFACT:
        "The page served and was read, but the capture does not satisfy the "
        "evidence contract; a citable artifact is needed.",
    NEXT_NONE_PAGE_SILENT:
        "The property's own page served its content and states nothing about "
        "pets. A fact about the hotel; nothing further to fetch.",
    NEXT_ROUTING_REPAIR:
        "The page reached is a different property's; the routing needs repair "
        "before any lane is spent again.",
    NEXT_RUN_ZERO_COST_RECOVERY:
        "The factory has not yet asked the evidence already on disk for this "
        "identity's URL. Free. Not terminal.",
    NEXT_RUN_ACQUISITION:
        "Routed to an approved lane and never attempted, with no cap having "
        "stopped short of it. Not terminal.",
    NEXT_RUN_ALTERNATE_LANE:
        "An approved lane the prior attempt never tried exists; the factory "
        "can attempt it. Not terminal.",
}

#: The fields the work order requires, in the order it names them.
REQUIRED_COUNTS: Tuple[str, ...] = (
    "CENSUS", "ROUTED", "UNROUTED", "ATTEMPTED", "VALID", "SETTLED",
    "UNSETTLED", "NEEDS_OFFICIAL_URL", "NEEDS_PROPERTY_URL", "BRAND_EXCLUDED",
    "BUDGET_DEFERRED", "ALTERNATE_LANE_REQUIRED", "FOUNDER_CANDIDATES",
)
REQUIRED_BOOLEANS: Tuple[str, ...] = (
    "ZERO_COST_RECOVERY_EXHAUSTED", "APPROVED_ROUTES_EXHAUSTED",
    "NEWLY_ROUTABLE_COHORT_EXHAUSTED", "SAME_LANE_RETRIES_SUPPRESSED",
    "CLOSURE_RECONCILED", "READY_FOR_FOUNDER_REVIEW",
)

#: A paid pass whose ``outcome`` is one of these stopped short of its queue for
#: a reason that is about money or telemetry, not about the properties.
BUDGET_STOP_OUTCOMES = frozenset({
    "STOPPED_HARD_CAP", "STOPPED_CREDIT_CAP", "STOPPED_TELEMETRY_LOST",
    "STOPPED_BEFORE_SPENDING",
})


class CoverageError(ValueError):
    """The coverage report does not reconcile with the census (fail closed)."""


def is_terminal(next_state: str) -> bool:
    return next_state in TERMINAL_NEXT_STATES


def row(*, identity_key: str, canonical_name: str, coverage_state: str,
        next_state: str, why: str, **extra) -> "OrderedDict":
    if coverage_state not in COVERAGE_STATES:
        raise CoverageError("unknown coverage state %r for %s"
                            % (coverage_state, identity_key))
    if next_state not in NEXT_STATES:
        raise CoverageError("unknown next state %r for %s"
                            % (next_state, identity_key))
    out = OrderedDict((
        ("identity_key", identity_key),
        ("canonical_name", canonical_name),
        ("coverage_state", coverage_state),
        ("next_state", next_state),
        ("next_state_is_terminal", is_terminal(next_state)),
        ("factory_can_proceed", not is_terminal(next_state)),
        ("why", why),
    ))
    for key in sorted(extra):
        out[key] = extra[key]
    return out


def reconcile(rows: Sequence[Mapping], census_keys: Iterable[str]) -> Dict:
    census: Set[str] = set(census_keys)
    seen = [r["identity_key"] for r in rows]
    counts = Counter(seen)
    return {
        "missing": sorted(census - set(seen)),
        "foreign": sorted(set(seen) - census),
        "duplicate": sorted(k for k, n in counts.items() if n > 1),
        "census_count": len(census),
        "row_count": len(rows),
    }


def _pct(numerator: int, denominator: int) -> float:
    return round(100.0 * numerator / denominator, 1) if denominator else 0.0


def document(market_id: str, rows: Sequence[Mapping], *, work_order: str,
             as_of: str, census_keys: Iterable[str], stage: str,
             counts: Mapping[str, int], booleans: Mapping[str, bool],
             evidence: Mapping, note: str = "", **extra) -> "OrderedDict":
    """A coverage-completion document that refuses to exist unless it
    reconciles, carries every required count and boolean, and gives every
    non-terminal identity a factory next-state."""
    problems = reconcile(rows, census_keys)
    if problems["missing"] or problems["foreign"] or problems["duplicate"]:
        raise CoverageError(
            "coverage report for %s does not reconcile: %d missing, %d foreign, "
            "%d duplicate (first missing: %s)"
            % (market_id, len(problems["missing"]), len(problems["foreign"]),
               len(problems["duplicate"]), problems["missing"][:3]))
    for name in REQUIRED_COUNTS:
        if name not in counts:
            raise CoverageError("coverage report lacks required count %s" % name)
    for name in REQUIRED_BOOLEANS:
        if name not in booleans or not isinstance(booleans[name], bool):
            raise CoverageError("coverage report lacks required boolean %s" % name)

    ordered = sorted(rows, key=lambda r: r["identity_key"])
    proceedable = [r["identity_key"] for r in ordered if r["factory_can_proceed"]]
    if booleans["READY_FOR_FOUNDER_REVIEW"] and proceedable:
        raise CoverageError(
            "READY_FOR_FOUNDER_REVIEW cannot be true while %d identities have "
            "a next-state the factory can reach itself (first: %s)"
            % (len(proceedable), proceedable[:3]))

    census_total = counts["CENSUS"]
    benchmark = OrderedDict((
        ("routed_pct_of_census", _pct(counts["ROUTED"], census_total)),
        ("attempted_pct_of_census", _pct(counts["ATTEMPTED"], census_total)),
        ("settled_pct_of_census", _pct(counts["SETTLED"], census_total)),
        ("publication_grade_pct_of_census",
         _pct(counts.get("PUBLICATION_GRADE", counts["FOUNDER_CANDIDATES"]),
              census_total)),
        ("founder_candidate_pct_of_census",
         _pct(counts["FOUNDER_CANDIDATES"], census_total)),
        ("unresolved_pct_of_census",
         _pct(census_total - counts["SETTLED"], census_total)),
        ("unresolved_basis", "census minus identities a terminal capture "
                             "outcome settled (VALID, POLICY_NOT_FOUND, "
                             "IDENTITY_MISMATCH)"),
    ))
    doc = OrderedDict((
        ("schema", SCHEMA),
        ("what_this_is",
         "Whether the generic market factory has exhausted everything it can "
         "do without a human, over every census identity, by set. Founder "
         "review may begin only when READY_FOR_FOUNDER_REVIEW is true, and it "
         "is true only when every unresolved identity carries a terminal "
         "next-state saying why the factory cannot proceed automatically."),
        ("market_id", market_id),
        ("work_order", work_order),
        ("as_of", as_of),
        ("evaluation_stage", stage),
        ("note", note),
        ("counts", OrderedDict((name, int(counts[name]))
                               for name in REQUIRED_COUNTS)),
        ("extra_counts", OrderedDict(sorted(
            (k, int(v)) for k, v in counts.items() if k not in REQUIRED_COUNTS))),
        ("booleans", OrderedDict((name, bool(booleans[name]))
                                 for name in REQUIRED_BOOLEANS)),
        ("boolean_basis", OrderedDict(sorted(
            (k, v) for k, v in dict(evidence).items()))),
        ("benchmark", benchmark),
        ("factory_complete", bool(booleans["READY_FOR_FOUNDER_REVIEW"])),
        ("factory_complete_basis",
         "a market is FACTORY_COMPLETE when READY_FOR_FOUNDER_REVIEW is true, "
         "never merely because one paid pass ended"),
        ("coverage_state_counts", OrderedDict(
            (name, n) for name, n in
            ((s, sum(1 for r in ordered if r["coverage_state"] == s))
             for s in COVERAGE_STATES) if n)),
        ("next_state_counts", OrderedDict(
            (name, n) for name, n in
            ((s, sum(1 for r in ordered if r["next_state"] == s))
             for s in NEXT_STATES) if n)),
        ("next_state_meanings", OrderedDict(
            (s, NEXT_STATE_MEANINGS[s]) for s in NEXT_STATES
            if any(r["next_state"] == s for r in ordered))),
        ("identities_the_factory_can_still_move", proceedable),
        ("reconciliation", OrderedDict(sorted(problems.items()))),
    ))
    for key in sorted(extra):
        doc[key] = extra[key]
    doc["rows"] = ordered
    return doc


__all__ = [
    "SCHEMA", "COVERAGE_STATES", "NEXT_STATES", "TERMINAL_NEXT_STATES",
    "FACTORY_NEXT_STATES", "NEXT_STATE_MEANINGS", "REQUIRED_COUNTS",
    "REQUIRED_BOOLEANS", "BUDGET_STOP_OUTCOMES", "CoverageError",
    "is_terminal", "row", "reconcile", "document",
    "NOT_ACTIVE", "UNROUTED_NEEDS_OFFICIAL_URL", "UNROUTED_NEEDS_PROPERTY_URL",
    "UNROUTED_NEEDS_FIRST_PARTY_URL", "UNROUTED_BRAND_EXCLUDED",
    "ROUTED_NEVER_ATTEMPTED", "ROUTED_BUDGET_DEFERRED",
    "ROUTED_ALTERNATE_LANE_AVAILABLE", "ROUTED_ALTERNATE_LANE_REQUIRED",
    "SETTLED_FOUNDER_CANDIDATE", "SETTLED_VALID_NOT_PUBLICATION_GRADE",
    "SETTLED_VALID_GRADE_PENDING", "SETTLED_POLICY_NOT_FOUND",
    "SETTLED_IDENTITY_MISMATCH",
    "NEXT_CENSUS_REVIEW", "NEXT_OFFICIAL_URL", "NEXT_PROPERTY_URL",
    "NEXT_FIRST_PARTY_URL", "NEXT_ROUTE_REGISTRY_DECISION",
    "NEXT_BUDGET_AUTHORIZATION", "NEXT_ALTERNATE_LANE", "NEXT_FOUNDER_DECISION",
    "NEXT_POLICY_ARTIFACT", "NEXT_NONE_PAGE_SILENT", "NEXT_ROUTING_REPAIR",
    "NEXT_RUN_ZERO_COST_RECOVERY", "NEXT_RUN_ACQUISITION",
    "NEXT_RUN_ALTERNATE_LANE",
]
