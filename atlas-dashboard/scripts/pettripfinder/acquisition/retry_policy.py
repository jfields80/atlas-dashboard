"""PTF-MARKET-FACTORY-COVERAGE-HARDENING-001 -- no same-lane retry waste.

WHAT LOUISVILLE PROVED
----------------------
PTF-LOUISVILLE-COVERAGE-EXPANSION-003 paid for eight properties a prior pass had
already paid for and failed to read. All eight failed again, on the same lanes,
with the same outcomes -- 5 UNEXPECTED_PAGE, 2 ACCESS_DENIED, 1 UNHYDRATED --
and consumed roughly $1.20 of a $4.20 pass for no fact. They entered the cohort
automatically, because ``derive_cohort`` subtracts only the prior outcomes that
ANSWERED a property, and an access failure answers nothing.

The obvious fix -- declare them terminal -- is the wrong one. A terminal outcome
means the property's question was answered, and writing that into the ledger
for a page nobody could read would let the closure ledger say POLICY_NOT_FOUND
or ACCESS_UNRESOLVED-as-settled about a hotel whose page was never seen. So
those rows are neither bought nor settled: they are SUPPRESSED, named, and given
a state that says exactly what would change the answer.

THE RULE
--------
A prior access / navigation / unhydrated failure may re-enter a paid cohort
only if at least one of these is true, and the classification names which:

    RETRY_ALLOWED_ALTERNATE_LANE     the route's approved ladder holds a lane
                                     the prior attempts never tried. The row is
                                     given a per-property lane override so the
                                     run starts on the UNTRIED lane instead of
                                     re-walking the ladder from the top.
    RETRY_ALLOWED_URL_CHANGED        the source URL the row routes to is not
                                     the URL the prior attempt fetched -- a URL
                                     recovery displaced it, or discovery moved.
    RETRY_ALLOWED_READER_CHANGED     the route's reader changed AND the prior
                                     failure is one a reader can address. A
                                     channel refusal is not one of those; a new
                                     reader reads the same 403.
    RETRY_ALLOWED_OPERATOR_OVERRIDE  an explicit, named, reasoned override.

Otherwise the row is ``RETRY_REQUIRES_ALTERNATE_LANE``: every approved lane has
been tried on this URL and the factory has nothing new to offer it. That is a
terminal next-state for the factory -- an attended capture, a new lane in the
registry, or a routing repair -- and never a settlement.

A row whose prior lane is UNRECORDED is suppressed too. A different lane cannot
be proven when the first one was never written down, and "we cannot prove it
was the same lane" is not evidence that it was a different one. Every paid pass
records its lane; the free pilot records it at document level and the merge
carries it onto each row, so this case is confined to artifacts older than both.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.acquisition import failures as F         # noqa: E402
from scripts.pettripfinder.acquisition import market_routing as MR  # noqa: E402
from scripts.pettripfinder.brightdata import outcomes as O          # noqa: E402

SCHEMA = "ptf-retry-policy/1.0"

FIRST_ATTEMPT = "FIRST_ATTEMPT"
RETRY_ALLOWED_ALTERNATE_LANE = "RETRY_ALLOWED_ALTERNATE_LANE"
RETRY_ALLOWED_URL_CHANGED = "RETRY_ALLOWED_URL_CHANGED"
RETRY_ALLOWED_READER_CHANGED = "RETRY_ALLOWED_READER_CHANGED"
RETRY_ALLOWED_OPERATOR_OVERRIDE = "RETRY_ALLOWED_OPERATOR_OVERRIDE"
RETRY_REQUIRES_ALTERNATE_LANE = "RETRY_REQUIRES_ALTERNATE_LANE"

ALLOWED: Tuple[str, ...] = (
    FIRST_ATTEMPT, RETRY_ALLOWED_ALTERNATE_LANE, RETRY_ALLOWED_URL_CHANGED,
    RETRY_ALLOWED_READER_CHANGED, RETRY_ALLOWED_OPERATOR_OVERRIDE,
)
SUPPRESSED: Tuple[str, ...] = (RETRY_REQUIRES_ALTERNATE_LANE,)
CLASSIFICATIONS: Tuple[str, ...] = ALLOWED + SUPPRESSED

#: Reasons a row can be suppressed, so a report can say WHY without prose.
WHY_EVERY_LANE_TRIED = "EVERY_APPROVED_LANE_ALREADY_TRIED_ON_THIS_URL"
WHY_PRIOR_LANE_UNRECORDED = "PRIOR_LANE_UNRECORDED"

#: Router failures a different READER could address. Everything in
#: ``failures.TECHNICAL`` is a statement about the channel and is not here: the
#: page did not arrive, and no reader reads a page that did not arrive.
READER_ADDRESSABLE_FAILURES = frozenset({
    F.IDENTITY_UNCERTAIN, F.POLICY_SURFACE_INCOMPLETE,
})

#: Prior outcomes that answered the property. Kept in one place with the paid
#: pass's own default so the two cannot disagree about what "settled" means.
DEFAULT_TERMINAL: Tuple[str, ...] = (O.VALID, O.POLICY_NOT_FOUND,
                                     O.IDENTITY_MISMATCH)


class RetryPolicyError(ValueError):
    """An override that does not say who authorised it, or why."""


# --------------------------------------------------------------------------- #
# What the prior attempt was
# --------------------------------------------------------------------------- #

def lanes_tried(prior_row: Mapping, prior_document: Optional[Mapping] = None
                ) -> Tuple[str, ...]:
    """Every lane the prior attempt(s) on this row actually used, in order.

    A paid-pass row names them in ``providers_tried`` and its chosen lane in
    ``provider``. A free-pilot row names neither, but its DOCUMENT does: the
    pilot report carries one ``provider`` for every row in it. A merged view
    carries a comma-joined list at document level, which names no single lane
    and is ignored.
    """
    tried: List[str] = []
    for lane in (prior_row.get("providers_tried") or ()):
        if lane and lane not in tried:
            tried.append(str(lane))
    provider = str(prior_row.get("provider") or "")
    if provider and provider not in tried:
        tried.append(provider)
    if not tried and prior_document is not None:
        doc_lane = str(prior_document.get("provider") or "")
        if doc_lane and "," not in doc_lane:
            tried.append(doc_lane)
    return tuple(tried)


def approved_ladder(entry: Mapping) -> Tuple[str, ...]:
    """The lanes the routing registry permits for this row, primary first."""
    ladder = list(entry.get("ladder") or ())
    if not ladder:
        ladder = [entry.get("provider") or ""]
        ladder.extend(entry.get("fallback_providers") or ())
    seen: List[str] = []
    for lane in ladder:
        if lane and lane not in seen:
            seen.append(str(lane))
    return tuple(seen)


# --------------------------------------------------------------------------- #
# Overrides
# --------------------------------------------------------------------------- #

def load_overrides(path: Optional[Path]) -> Dict[str, Dict]:
    """``identity_key -> override`` from a ptf-retry-overrides document.

    Every override must name who authorised it and why. An override with no
    author is an anonymous decision to spend money, and an override with no
    reason cannot be reviewed after the money is gone.
    """
    if not path:
        return {}
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    out: Dict[str, Dict] = {}
    for row in document.get("overrides") or ():
        key = str(row.get("identity_key") or "").strip()
        if not key:
            raise RetryPolicyError("an override names no identity_key")
        if not str(row.get("authorised_by") or "").strip():
            raise RetryPolicyError("override for %r names no authorised_by" % key)
        if not str(row.get("why") or "").strip():
            raise RetryPolicyError("override for %r gives no why" % key)
        out[key] = OrderedDict((
            ("identity_key", key),
            ("authorised_by", str(row["authorised_by"])),
            ("why", str(row["why"])),
        ))
    return out


# --------------------------------------------------------------------------- #
# Classification
# --------------------------------------------------------------------------- #

def classify(entry: Mapping, prior_row: Optional[Mapping], *,
             prior_document: Optional[Mapping] = None,
             overrides: Optional[Mapping[str, Mapping]] = None,
             terminal: Sequence[str] = DEFAULT_TERMINAL) -> "OrderedDict":
    """One routed row -> whether a paid lane may attempt it, and why.

    ``entry`` is the row's CURRENT route (a ``market_routing`` entry or a
    ``derive_cohort`` row: identity_key, source_url, provider, reader, and the
    ladder when known). ``prior_row`` is the merged prior result for the same
    identity, or ``None`` when no pass has touched it.

    A row whose prior outcome is terminal is not this function's business --
    ``derive_cohort`` has already settled it -- but it is answered consistently
    rather than refused, so a caller that asks about every row gets an answer
    for every row.
    """
    key = entry.get("identity_key", "")
    result: "OrderedDict" = OrderedDict((
        ("identity_key", key),
        ("classification", ""),
        ("why", ""),
        ("prior_outcome", ""),
        ("prior_failure", ""),
        ("lanes_tried", []),
        ("approved_ladder", list(approved_ladder(entry))),
        ("alternate_lanes", []),
        ("lane_override", None),
    ))
    if prior_row is None or not prior_row.get("outcome"):
        result["classification"] = FIRST_ATTEMPT
        result["why"] = "no prior pass has attempted this property"
        result["prior_outcome"] = "NEVER_ATTEMPTED"
        return result

    outcome = str(prior_row.get("outcome") or "")
    failure = str(prior_row.get("failure") or outcome)
    result["prior_outcome"] = outcome
    result["prior_failure"] = failure
    if outcome in frozenset(terminal):
        result["classification"] = "SETTLED_BY_PRIOR_OUTCOME"
        result["why"] = ("a prior capture answered this property (%s); not a "
                         "retry question" % outcome)
        return result

    tried = lanes_tried(prior_row, prior_document)
    result["lanes_tried"] = list(tried)

    override = (overrides or {}).get(key)
    if override is not None:
        result["classification"] = RETRY_ALLOWED_OPERATOR_OVERRIDE
        result["why"] = ("explicit operator override by %s: %s"
                         % (override.get("authorised_by", ""),
                            override.get("why", "")))
        result["override"] = dict(override)
        return result

    prior_url = MR.normalize_source_url(str(prior_row.get("source_url") or ""))
    current_url = MR.normalize_source_url(str(entry.get("source_url") or ""))
    if prior_url and current_url and prior_url != current_url:
        result["classification"] = RETRY_ALLOWED_URL_CHANGED
        result["why"] = ("the source URL changed since the prior attempt "
                         "(%s -> %s); the prior failure was about a different "
                         "page" % (prior_url, current_url))
        result["prior_url"] = prior_url
        return result

    prior_reader = str(prior_row.get("reader") or "")
    current_reader = str(entry.get("reader") or "")
    if (prior_reader and current_reader and prior_reader != current_reader
            and failure in READER_ADDRESSABLE_FAILURES):
        result["classification"] = RETRY_ALLOWED_READER_CHANGED
        result["why"] = ("the reader changed (%s -> %s) and the prior failure "
                         "(%s) is one a reader can address"
                         % (prior_reader, current_reader, failure))
        return result

    if not tried:
        result["classification"] = RETRY_REQUIRES_ALTERNATE_LANE
        result["suppressed_because"] = WHY_PRIOR_LANE_UNRECORDED
        result["why"] = ("the prior attempt recorded no lane, so a different "
                         "lane cannot be shown; suppressed rather than retried "
                         "on what may be the same one")
        return result

    ladder = approved_ladder(entry)
    alternates = [lane for lane in ladder if lane not in tried]
    if alternates:
        result["classification"] = RETRY_ALLOWED_ALTERNATE_LANE
        result["alternate_lanes"] = alternates
        result["lane_override"] = OrderedDict((
            ("provider", alternates[0]),
            ("fallback_providers", alternates[1:]),
        ))
        result["why"] = ("the approved ladder %s holds %s, which the prior "
                         "attempt (%s) never tried; the run starts there"
                         % (list(ladder), alternates, list(tried)))
        return result

    result["classification"] = RETRY_REQUIRES_ALTERNATE_LANE
    result["suppressed_because"] = WHY_EVERY_LANE_TRIED
    result["why"] = ("every approved lane %s was already tried on this URL and "
                     "answered nothing (%s); a same-lane retry does not "
                     "convert -- it needs a lane the registry does not yet "
                     "approve, an attended capture, or a routing repair"
                     % (list(tried), outcome))
    return result


def apply(cohort: Sequence[Mapping], prior: Mapping, *,
          overrides: Optional[Mapping[str, Mapping]] = None,
          terminal: Sequence[str] = DEFAULT_TERMINAL
          ) -> Tuple[List[Dict], List[Dict]]:
    """``(eligible, suppressed)`` over a cohort ``derive_cohort`` built.

    Every eligible row gains ``retry_classification`` and, when an alternate
    lane was selected, has its ``provider`` moved to that lane and carries the
    ``lane_override`` the run must honour. Every suppressed row is returned in
    full with its classification, so a report can name each one.

    ``eligible + suppressed`` is the cohort handed in; a test asserts it.
    """
    prior_by_key = {r["identity_key"]: r for r in (prior.get("results") or ())}
    eligible: List[Dict] = []
    suppressed: List[Dict] = []
    for row in cohort:
        verdict = classify(row, prior_by_key.get(row["identity_key"]),
                           prior_document=prior, overrides=overrides,
                           terminal=terminal)
        out = OrderedDict(row)
        out["retry_classification"] = verdict["classification"]
        out["retry_why"] = verdict["why"]
        if verdict["classification"] in SUPPRESSED:
            out["suppressed_because"] = verdict.get("suppressed_because", "")
            out["lanes_tried"] = verdict["lanes_tried"]
            suppressed.append(out)
            continue
        if verdict.get("lane_override"):
            out["routed_provider"] = row.get("provider", "")
            out["provider"] = verdict["lane_override"]["provider"]
            out["lane_override"] = verdict["lane_override"]
            out["lanes_tried"] = verdict["lanes_tried"]
        eligible.append(out)
    return (eligible, suppressed)


def lane_overrides_registry(eligible: Sequence[Mapping], *, work_order: str,
                            base: Optional[Mapping] = None) -> Optional[Dict]:
    """A routing-registry overlay that starts each alternate-lane row on its
    untried lane, or ``None`` when no row needs one.

    Property-level entries are the most specific layer the registry resolves,
    and the brand's ``forbidden_providers`` still apply beneath them -- the
    alternates were taken from the ladder, which already excludes forbidden
    lanes, so nothing here can re-enter a lane a measurement ruled out. Every
    entry cites this work order as its ``measured_by``: the measurement is the
    prior pass that proved the primary lane does not convert for this row.
    """
    properties: Dict[str, Dict] = OrderedDict()
    for row in eligible:
        override = row.get("lane_override")
        if not override:
            continue
        properties[row["identity_key"]] = OrderedDict((
            ("provider", override["provider"]),
            ("fallback_providers", list(override.get("fallback_providers") or ())),
            ("why", "retry policy: %s already tried %s and answered nothing; "
                    "starting on the untried approved lane"
                    % (row["identity_key"], row.get("lanes_tried") or [])),
            ("measured_by", work_order),
        ))
    if not properties:
        return None
    registry: Dict = json.loads(json.dumps(base)) if base is not None else {}
    merged = OrderedDict(registry.get("properties") or {})
    merged.update(properties)
    registry["properties"] = merged
    return registry


def summary(eligible: Sequence[Mapping], suppressed: Sequence[Mapping]) -> Dict:
    """The retry-policy section of a paid-pass report or a cost plan."""
    return OrderedDict((
        ("schema", SCHEMA),
        ("rule", "a prior access, navigation or unhydrated failure re-enters a "
                 "paid cohort only on a different approved lane, a changed "
                 "URL, a reader change that addresses the failure, or an "
                 "explicit operator override; otherwise it is suppressed as "
                 "RETRY_REQUIRES_ALTERNATE_LANE and never marked settled"),
        ("eligible", len(eligible)),
        ("suppressed", len(suppressed)),
        ("classification_counts", OrderedDict(sorted(Counter(
            r.get("retry_classification", "") for r in list(eligible)
            + list(suppressed)).items()))),
        ("suppressed_rows", [OrderedDict((
            ("identity_key", r["identity_key"]),
            ("prior_outcome", r.get("prior_outcome", "")),
            ("lanes_tried", r.get("lanes_tried", [])),
            ("suppressed_because", r.get("suppressed_because", "")),
            ("next_state", RETRY_REQUIRES_ALTERNATE_LANE),
        )) for r in suppressed]),
        ("alternate_lane_rows", [OrderedDict((
            ("identity_key", r["identity_key"]),
            ("routed_provider", r.get("routed_provider", "")),
            ("starts_on", r.get("provider", "")),
            ("lanes_tried", r.get("lanes_tried", [])),
        )) for r in eligible
            if r.get("retry_classification") == RETRY_ALLOWED_ALTERNATE_LANE]),
    ))


__all__ = [
    "SCHEMA", "FIRST_ATTEMPT", "RETRY_ALLOWED_ALTERNATE_LANE",
    "RETRY_ALLOWED_URL_CHANGED", "RETRY_ALLOWED_READER_CHANGED",
    "RETRY_ALLOWED_OPERATOR_OVERRIDE", "RETRY_REQUIRES_ALTERNATE_LANE",
    "ALLOWED", "SUPPRESSED", "CLASSIFICATIONS", "WHY_EVERY_LANE_TRIED",
    "WHY_PRIOR_LANE_UNRECORDED", "READER_ADDRESSABLE_FAILURES",
    "DEFAULT_TERMINAL", "RetryPolicyError", "lanes_tried", "approved_ladder",
    "load_overrides", "classify", "apply", "lane_overrides_registry", "summary",
]
