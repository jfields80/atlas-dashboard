"""PTF-FACTORY-THROUGHPUT-HARDENING-001 -- the acquisition ladder.

WHY THIS EXISTS
---------------
Dayton's hardened revalidation reached its answers through three lanes: owned
evidence, a direct static fetch, and an attended Chrome session. Firecrawl --
an adapter this repository has carried since PTF-FIRECRAWL-BENCHMARK-002, a
routed provider for IHG, Wyndham and Choice since decisions 008 / 009 / 004-006,
with credentials configured and a ledger that records its credits -- was never
invoked. Not because it was unavailable, but because nothing SAT BETWEEN the
static lane and the attended lane: the hardened per-market scripts go straight
from "the plain client was refused" to "open a browser", and the router that
knows about Firecrawl lives in the factory's PAID phase, gated behind a cost
plan and a founder cap. A $0 order therefore never reaches it.

This module is the rung that was missing. It expresses the whole ladder in one
ordered vocabulary, decides the NEXT lane for a row from the evidence already
on disk, and says -- by name -- when a Firecrawl attempt should be evaluated
before a cohort is walked into a browser by hand.

THE LADDER
----------
    0  OWNED_EVIDENCE          a transcription or capture the repository owns
    1  LOCAL_FREE_DISCOVERY    OSM / Geofabrik / official locators / sitemaps
    2  DIRECT_STATIC_FETCH     one HTTPS GET through the canonical gates
    3  FIRECRAWL               a rendered fetch billed in plan credits
    4  ATTENDED_BROWSER        a person, a real Chrome session, $0
    5  PAID_FETCH              Bright Data browser / unlocker, billed in USD
    6  PAID_IDENTITY_DISCOVERY Places and the like, billed in USD

Routing stays EVIDENCE-AWARE. Firecrawl is the next rung only for a source
family it has been MEASURED to read (the route table names it, from a decision
test) and never for one it has been measured to fail (Marriott and Hilton
returned SCRAPE_ALL_ENGINES_FAILED 6 of 7 times in HARD-LANES-003). A family
nobody has measured is not a candidate by default; it is PROBE-eligible, and
the plan says so rather than spending on a guess.

Firecrawl never outranks a deterministic free first-party fetch. A static
attempt that ANSWERED -- VALID, or a silence, or an identity mismatch -- is not
escalated anywhere; only a channel failure moves down the ladder, which is the
router's own rule (a refusal escalates, a silence does not).

IDENTITY IS NEVER POSITIONAL
----------------------------
The Dayton attended session batched a whole brand through one page. That is
fast, and it is exactly how one property's text ends up bound to the hotel
next to it in the list. Every request this planner emits carries the identity
key it is FOR and the URL it will fetch; a result binds only to the request
whose identity key AND requested URL it names, and only when the adapter's own
identity assessment confirmed the page. Nothing here binds by order of
arrival. ``bind_results`` refuses a result that names no identity, or names a
URL its request did not, and reports it UNBOUND instead of guessing.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.acquisition import market_routing as MR   # noqa: E402
from scripts.pettripfinder.acquisition import providers as PROVIDERS  # noqa: E402
from scripts.pettripfinder.acquisition import registry as REGISTRY    # noqa: E402
from scripts.pettripfinder.brightdata import outcomes as O            # noqa: E402
from scripts.pettripfinder.brightdata import policy_surface as PS     # noqa: E402

SCHEMA = "ptf-acquisition-ladder/1.0"
PLAN_SCHEMA = "ptf-acquisition-ladder-plan/1.0"

# --------------------------------------------------------------------------- #
# Lanes, in order.
# --------------------------------------------------------------------------- #

OWNED_EVIDENCE = "OWNED_EVIDENCE"
LOCAL_FREE_DISCOVERY = "LOCAL_FREE_DISCOVERY"
DIRECT_STATIC_FETCH = "DIRECT_STATIC_FETCH"
FIRECRAWL = "FIRECRAWL"
ATTENDED_BROWSER = "ATTENDED_BROWSER"
PAID_FETCH = "PAID_FETCH"
PAID_IDENTITY_DISCOVERY = "PAID_IDENTITY_DISCOVERY"


@dataclass(frozen=True)
class Lane:
    rank: int
    lane_id: str
    what: str
    #: ``none`` / ``credits`` / ``usd``.
    billed_in: str
    needs_authorization: bool
    #: Whether this lane can answer a POLICY question (as opposed to identity).
    answers_policy: bool


LADDER: Tuple[Lane, ...] = (
    Lane(0, OWNED_EVIDENCE, "a transcription or capture the repository already owns",
         "none", False, True),
    Lane(1, LOCAL_FREE_DISCOVERY, "OSM / Geofabrik / official locators / sitemap inventory",
         "none", False, False),
    Lane(2, DIRECT_STATIC_FETCH, "one HTTPS GET through the canonical gates",
         "none", False, True),
    Lane(3, FIRECRAWL, "a rendered fetch billed in plan credits",
         "credits", True, True),
    Lane(4, ATTENDED_BROWSER, "a person in a real Chrome session, $0",
         "none", False, True),
    Lane(5, PAID_FETCH, "Bright Data browser / web unlocker, billed in USD",
         "usd", True, True),
    Lane(6, PAID_IDENTITY_DISCOVERY, "paid places / identity discovery, billed in USD",
         "usd", True, False),
)
LANE_IDS: Tuple[str, ...] = tuple(l.lane_id for l in LADDER)
LANE_BY_ID: Dict[str, Lane] = {l.lane_id: l for l in LADDER}


def lane_rank(lane_id: str) -> int:
    return LANE_BY_ID[lane_id].rank


# --------------------------------------------------------------------------- #
# Firecrawl result classification (B6).
# --------------------------------------------------------------------------- #

FIRECRAWL_PUBLICATION_GRADE = "FIRECRAWL_PUBLICATION_GRADE"
FIRECRAWL_IDENTITY_ONLY = "FIRECRAWL_IDENTITY_ONLY"
FIRECRAWL_SOURCE_SILENT = "FIRECRAWL_SOURCE_SILENT"
FIRECRAWL_BLOCKED = "FIRECRAWL_BLOCKED"
FIRECRAWL_MISMATCH = "FIRECRAWL_MISMATCH"
FIRECRAWL_FAILED = "FIRECRAWL_FAILED"
FIRECRAWL_CLASSES: Tuple[str, ...] = (
    FIRECRAWL_PUBLICATION_GRADE, FIRECRAWL_IDENTITY_ONLY, FIRECRAWL_SOURCE_SILENT,
    FIRECRAWL_BLOCKED, FIRECRAWL_MISMATCH, FIRECRAWL_FAILED,
)

#: Surface strategies that are NOT policy evidence even when text arrived: a
#: brand-generic page or an amenity chip says nothing about THIS property's
#: operative policy. A reader that recorded one of these locates nothing.
NON_EVIDENCE_SURFACES = frozenset({"amenity_chip", "amenity_list", "brand_generic",
                                   "brand_faq", "heading_only", "HEADING_ONLY",
                                   "AMENITY_ONLY"})

_BLOCKED = frozenset({O.ACCESS_DENIED, O.UNHYDRATED, O.BLANK_PAGE})
_FAILED = frozenset({O.NAVIGATION_FAILED, O.CAPTURE_FAILED, O.UNEXPECTED_PAGE})


def classify_firecrawl_result(*, outcome: str, identity_confirmed: bool,
                              publication_grade: bool = False,
                              surface_strategy: str = "") -> str:
    """One of :data:`FIRECRAWL_CLASSES` for one Firecrawl attempt.

    A result is PUBLICATION_GRADE only when the adapter reached VALID (which
    it does only after its identity assessment confirmed the page), the
    downstream grade held, and the located surface is a property-specific
    policy block rather than a chip or a brand page.
    """
    if outcome == O.IDENTITY_MISMATCH:
        return FIRECRAWL_MISMATCH
    if outcome in _BLOCKED:
        return FIRECRAWL_BLOCKED
    if outcome in _FAILED:
        return FIRECRAWL_FAILED
    if outcome == O.POLICY_NOT_FOUND:
        return FIRECRAWL_SOURCE_SILENT if identity_confirmed else FIRECRAWL_FAILED
    if outcome == O.VALID:
        if not identity_confirmed:
            # The adapter never emits this pairing; if a caller does, it is
            # not evidence of anything about the property.
            return FIRECRAWL_FAILED
        if surface_strategy in NON_EVIDENCE_SURFACES:
            return FIRECRAWL_IDENTITY_ONLY
        return FIRECRAWL_PUBLICATION_GRADE if publication_grade else FIRECRAWL_IDENTITY_ONLY
    return FIRECRAWL_FAILED


# --------------------------------------------------------------------------- #
# Firecrawl candidacy (B4 / B5): evidence-aware, never positional.
# --------------------------------------------------------------------------- #

CANDIDATE_ROUTED = "FIRECRAWL_ROUTED_FOR_FAMILY"
NOT_CANDIDATE_KNOWN_WALL = "FIRECRAWL_KNOWN_CAPABILITY_WALL"
NOT_CANDIDATE_UNMEASURED = "FIRECRAWL_UNMEASURED_FOR_FAMILY"
NOT_CANDIDATE_STATIC_ANSWERED = "STATIC_LANE_ANSWERED"
NOT_CANDIDATE_NOT_ESCALATABLE = "PRIOR_OUTCOME_DOES_NOT_ESCALATE"
NOT_CANDIDATE_URL_SHAPE = "URL_IS_NOT_A_PROPERTY_PAGE"
NOT_CANDIDATE_CODE_UNPARSEABLE = "PROPERTY_CODE_UNPARSEABLE_ROUTING_REPAIR_REQUIRED"
NOT_CANDIDATE_ALREADY_TRIED = "FIRECRAWL_ALREADY_ATTEMPTED_ON_THIS_URL"
NOT_CANDIDATE_BRAND_EXCLUDED = "BRAND_EXCLUDED_FROM_ACQUISITION"

#: Families Firecrawl has been MEASURED to fail: HARD-LANES-003 saw
#: SCRAPE_ALL_ENGINES_FAILED on 6 of 7 Marriott/Hilton attempts, and the
#: benchmark body reproduced it, so it is the target and not the request.
KNOWN_CAPABILITY_WALLS: Dict[str, str] = {
    "MARRIOTT": "PTF-FIRECRAWL-HARD-LANES-003",
    "HILTON": "PTF-FIRECRAWL-HARD-LANES-003",
}

#: Families whose route binds identity on a property CODE parsed from the
#: URL. If the code cannot be parsed, the page-health gate can never pass
#: (Detroit FIRECRAWL-PASS-008 lost 49 of 65 attempts this way), so the row
#: needs a routing repair, not a credit.
CODE_BOUND_FAMILIES = frozenset({"IHG", "CHOICE", "MARRIOTT", "HILTON"})

#: Outcomes a static attempt may have produced that a rendered fetch could
#: plausibly answer. The rest are statements about the page, not the channel.
ESCALATABLE_STATIC_OUTCOMES = frozenset({
    O.ACCESS_DENIED, O.UNHYDRATED, O.BLANK_PAGE, O.NAVIGATION_FAILED,
    O.UNEXPECTED_PAGE, O.CAPTURE_FAILED,
})


def firecrawl_routed_families(registry: Optional[Mapping] = None) -> Tuple[str, ...]:
    """Families the committed route table sends to Firecrawl first."""
    data = registry if registry is not None else REGISTRY.load()
    out = []
    for brand, entry in sorted((data.get("brands") or {}).items()):
        if entry.get("provider") == PROVIDERS.FIRECRAWL:
            out.append(brand.upper())
    return tuple(out)


@dataclass(frozen=True)
class Candidacy:
    candidate: bool
    reason: str
    measured_by: str = ""
    probe_eligible: bool = False


def firecrawl_candidacy(*, family: str, url: str, prior_static_outcome: str,
                        firecrawl_already_tried: bool = False,
                        registry: Optional[Mapping] = None) -> Candidacy:
    """Is Firecrawl the next rung for this row? Says why either way."""
    family = (family or "").strip().upper()
    data = registry if registry is not None else REGISTRY.load()
    if REGISTRY.is_excluded(family, data):
        return Candidacy(False, NOT_CANDIDATE_BRAND_EXCLUDED)
    if firecrawl_already_tried:
        return Candidacy(False, NOT_CANDIDATE_ALREADY_TRIED)
    if prior_static_outcome == O.VALID:
        return Candidacy(False, NOT_CANDIDATE_STATIC_ANSWERED)
    if prior_static_outcome and prior_static_outcome not in ESCALATABLE_STATIC_OUTCOMES:
        return Candidacy(False, NOT_CANDIDATE_NOT_ESCALATABLE)
    if MR.classify_url_shape(url) != MR.PROPERTY_PAGE:
        return Candidacy(False, NOT_CANDIDATE_URL_SHAPE)
    if family in CODE_BOUND_FAMILIES and not PS.property_code(url, family):
        return Candidacy(False, NOT_CANDIDATE_CODE_UNPARSEABLE)
    if family in KNOWN_CAPABILITY_WALLS:
        return Candidacy(False, NOT_CANDIDATE_KNOWN_WALL,
                         measured_by=KNOWN_CAPABILITY_WALLS[family])
    routed = firecrawl_routed_families(data)
    if family in routed:
        entry = (data.get("brands") or {}).get(family) or {}
        return Candidacy(True, CANDIDATE_ROUTED,
                         measured_by=entry.get("measured_by", ""))
    return Candidacy(False, NOT_CANDIDATE_UNMEASURED, probe_eligible=True)


# --------------------------------------------------------------------------- #
# Planning: the next lane for one row.
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class RowEvidence:
    """What is already known about one identity, from artifacts on disk."""

    identity_key: str
    family: str
    url: str
    #: OWNED_EVIDENCE_ANSWERS when an owned transcription / capture already
    #: settles the policy on a bound identity; else "".
    owned_state: str = ""
    #: The direct static lane's outcome on this URL, or "" if never tried.
    static_outcome: str = ""
    #: A Firecrawl class from FIRECRAWL_CLASSES, or "" if never tried.
    firecrawl_class: str = ""
    #: The attended lane's disposition ("BOUND", "IDENTITY_NOT_BOUND", or "").
    attended_state: str = ""


OWNED_EVIDENCE_ANSWERS = "OWNED_EVIDENCE_ANSWERS"
ANSWERED = "ANSWERED"
ROUTING_REPAIR = "ROUTING_REPAIR_REQUIRED"


@dataclass(frozen=True)
class Decision:
    identity_key: str
    family: str
    url: str
    next_lane: str
    reason: str
    firecrawl: Candidacy
    #: True when the row is already settled and needs no lane at all.
    settled: bool = False

    def as_dict(self) -> Dict:
        return OrderedDict((
            ("identity_key", self.identity_key), ("family", self.family),
            ("url", self.url), ("next_lane", self.next_lane),
            ("reason", self.reason), ("settled", self.settled),
            ("firecrawl_candidate", self.firecrawl.candidate),
            ("firecrawl_reason", self.firecrawl.reason),
            ("firecrawl_measured_by", self.firecrawl.measured_by),
            ("firecrawl_probe_eligible", self.firecrawl.probe_eligible),
        ))


def plan_row(row: RowEvidence, *, registry: Optional[Mapping] = None,
             attended_available: bool = True) -> Decision:
    """The next rung for one row, from what is already on disk."""
    candidacy = firecrawl_candidacy(
        family=row.family, url=row.url,
        prior_static_outcome=row.static_outcome,
        firecrawl_already_tried=bool(row.firecrawl_class), registry=registry)

    def done(lane, reason, settled=False):
        return Decision(row.identity_key, row.family, row.url, lane, reason,
                        candidacy, settled)

    if row.owned_state == OWNED_EVIDENCE_ANSWERS:
        return done(OWNED_EVIDENCE, "an owned artifact answers on a bound identity", True)
    if row.static_outcome == O.VALID:
        return done(DIRECT_STATIC_FETCH, "the static lane answered; nothing outranks it", True)
    if row.static_outcome in (O.POLICY_NOT_FOUND, O.IDENTITY_MISMATCH):
        return done(DIRECT_STATIC_FETCH,
                    "the static lane produced a statement about the page (%s); "
                    "a second fetch buys the same answer" % row.static_outcome,
                    True)
    if row.firecrawl_class in (FIRECRAWL_PUBLICATION_GRADE, FIRECRAWL_SOURCE_SILENT,
                               FIRECRAWL_MISMATCH):
        return done(FIRECRAWL, "Firecrawl answered (%s)" % row.firecrawl_class, True)
    if row.attended_state == "BOUND":
        return done(ATTENDED_BROWSER, "the attended lane answered on a bound identity", True)
    if not row.url or MR.classify_url_shape(row.url) not in MR.ROUTABLE_SHAPES:
        return done(LOCAL_FREE_DISCOVERY,
                    "no routable first-party URL; discovery before any fetch")
    if candidacy.reason == NOT_CANDIDATE_CODE_UNPARSEABLE:
        return done(LOCAL_FREE_DISCOVERY, ROUTING_REPAIR + ": " + candidacy.reason)
    if not row.static_outcome:
        return done(DIRECT_STATIC_FETCH, "cheapest deterministic lane, not yet tried")
    # The static lane failed on the channel. Firecrawl before a browser --
    # when the evidence says it can read this family.
    if candidacy.candidate:
        return done(FIRECRAWL, "static channel failure (%s) on a Firecrawl-routed "
                               "family; evaluate the rendered fetch before a "
                               "browser session" % row.static_outcome)
    if row.firecrawl_class in (FIRECRAWL_BLOCKED, FIRECRAWL_FAILED,
                               FIRECRAWL_IDENTITY_ONLY) or not candidacy.candidate:
        if attended_available:
            return done(ATTENDED_BROWSER,
                        "static channel failure (%s); Firecrawl is not the next "
                        "rung (%s)" % (row.static_outcome, candidacy.reason))
        return done(PAID_FETCH, "no attended session available; paid fetch needs "
                                "a cost plan and authorization")
    return done(ATTENDED_BROWSER, "fallthrough")  # pragma: no cover


def plan_cohort(rows: Iterable[RowEvidence], *, registry: Optional[Mapping] = None,
                attended_available: bool = True) -> List[Decision]:
    data = registry if registry is not None else REGISTRY.load()
    return [plan_row(r, registry=data, attended_available=attended_available)
            for r in rows]


# --------------------------------------------------------------------------- #
# The trigger (B7): when a cohort is walking straight into a browser.
# --------------------------------------------------------------------------- #

DEFAULT_WARNING_THRESHOLD = 0.20


def attended_pressure(decisions: Sequence[Decision], *,
                      threshold: float = DEFAULT_WARNING_THRESHOLD) -> Dict:
    """How much of the unresolved routed cohort is moving from a static
    failure straight to the attended lane without Firecrawl being evaluated.

    A routing decision point, not a correctness rule: the warning says
    "evaluate Firecrawl before continuing", and the plan already names the
    rows it means.
    """
    unresolved = [d for d in decisions if not d.settled]
    static_to_attended = [d for d in unresolved if d.next_lane == ATTENDED_BROWSER]
    firecrawl_first = [d for d in unresolved if d.next_lane == FIRECRAWL]
    denominator = len(unresolved)
    share_attended = (len(static_to_attended) / denominator) if denominator else 0.0
    share_firecrawl = (len(firecrawl_first) / denominator) if denominator else 0.0
    # The warning fires when the cohort is being walked into a browser while
    # a material share of it is Firecrawl-routable and unevaluated.
    warning = denominator > 0 and share_firecrawl >= threshold
    return OrderedDict((
        ("unresolved_routed", denominator),
        ("static_to_attended", len(static_to_attended)),
        ("firecrawl_candidates", len(firecrawl_first)),
        ("share_static_to_attended", round(share_attended, 4)),
        ("share_firecrawl_candidates", round(share_firecrawl, 4)),
        ("threshold", threshold),
        ("warning", warning),
        ("message", ("%d of %d unresolved routed rows (%.0f%%) are Firecrawl "
                     "candidates: evaluate the Firecrawl lane before continuing "
                     "to the attended browser" % (len(firecrawl_first), denominator,
                                                  100 * share_firecrawl))
                    if warning else ""),
    ))


# --------------------------------------------------------------------------- #
# Binding results to requests (B5): never by position.
# --------------------------------------------------------------------------- #

BOUND = "BOUND"
UNBOUND_NO_IDENTITY = "UNBOUND_RESULT_NAMES_NO_IDENTITY"
UNBOUND_UNKNOWN_IDENTITY = "UNBOUND_RESULT_NAMES_AN_UNREQUESTED_IDENTITY"
UNBOUND_URL_MISMATCH = "UNBOUND_RESULT_URL_IS_NOT_THE_REQUESTED_URL"
UNBOUND_IDENTITY_UNCONFIRMED = "UNBOUND_IDENTITY_NOT_CONFIRMED_ON_PAGE"
UNBOUND_DUPLICATE = "UNBOUND_SECOND_RESULT_FOR_ONE_REQUEST"


@dataclass(frozen=True)
class Request:
    identity_key: str
    requested_url: str
    lane: str


def bind_results(requests: Sequence[Request], results: Sequence[Mapping]) -> Dict:
    """Bind each result to the request it names, or report why it cannot.

    A result must carry ``identity_key`` and ``requested_url`` matching one
    request exactly, and ``identity_confirmed`` true. Order of ``results`` is
    never consulted, which is the whole point.
    """
    by_key: Dict[Tuple[str, str], Request] = {}
    for r in requests:
        key = (r.identity_key, MR.normalize_source_url(r.requested_url))
        if key in by_key:
            raise ValueError("two requests for one identity+URL: %r" % (key,))
        by_key[key] = r
    bound: "OrderedDict[str, Mapping]" = OrderedDict()
    unbound: List[Dict] = []
    for result in results:
        identity = (result.get("identity_key") or "").strip()
        url = MR.normalize_source_url(result.get("requested_url") or "")
        if not identity:
            unbound.append({"result_url": url, "why": UNBOUND_NO_IDENTITY}); continue
        matching = [k for k in by_key if k[0] == identity]
        if not matching:
            unbound.append({"identity_key": identity, "why": UNBOUND_UNKNOWN_IDENTITY}); continue
        if (identity, url) not in by_key:
            unbound.append({"identity_key": identity, "result_url": url,
                            "why": UNBOUND_URL_MISMATCH}); continue
        if not result.get("identity_confirmed"):
            unbound.append({"identity_key": identity, "why": UNBOUND_IDENTITY_UNCONFIRMED}); continue
        if identity in bound:
            unbound.append({"identity_key": identity, "why": UNBOUND_DUPLICATE}); continue
        bound[identity] = result
    return OrderedDict((("bound", bound), ("unbound", unbound),
                        ("requests", len(requests)), ("results", len(results))))


# --------------------------------------------------------------------------- #
# Reading a market's committed reports into RowEvidence.
# --------------------------------------------------------------------------- #

def rows_from_reports(*, static_report: Optional[Mapping] = None,
                      attended_report: Optional[Mapping] = None,
                      owned_report: Optional[Mapping] = None,
                      firecrawl_classes: Optional[Mapping[str, str]] = None
                      ) -> List[RowEvidence]:
    """Fold a market's free-static, attended and owned-evidence reports into
    one RowEvidence per identity, keyed on identity_key. Nothing positional."""
    static: Dict[str, Mapping] = {}
    for r in (static_report or {}).get("rows") or []:
        static[r["identity_key"]] = r
    attended: Dict[str, str] = {}
    for r in (attended_report or {}).get("results") or []:
        binding = r.get("identity_binding") or {}
        attended[r["identity_key"]] = "BOUND" if binding.get("bound") else "IDENTITY_NOT_BOUND"
    owned: Dict[str, str] = {}
    for r in (owned_report or {}).get("rows") or []:
        # An owned artifact answers only when the repository itself holds a
        # corroborating capture on a bound identity. A "fresh" read in an
        # owned-evidence REPLAY came from whatever lane the replay used (in
        # Dayton, the attended session) and is that lane's evidence, not lane 0.
        if r.get("owned_was_corroborated_by_a_stored_capture")                 and r.get("fresh_identity_bound"):
            owned[r["identity_key"]] = OWNED_EVIDENCE_ANSWERS
    keys = sorted(set(static) | set(attended) | set(owned))
    out: List[RowEvidence] = []
    for key in keys:
        s = static.get(key) or {}
        out.append(RowEvidence(
            identity_key=key,
            family=(s.get("brand") or "").upper(),
            url=s.get("requested_url") or "",
            owned_state=owned.get(key, ""),
            static_outcome=s.get("outcome") or "",
            firecrawl_class=(firecrawl_classes or {}).get(key, ""),
            attended_state=attended.get(key, ""),
        ))
    return out


def plan_document(rows: Sequence[RowEvidence], *, market_id: str, work_order: str,
                  registry: Optional[Mapping] = None,
                  attended_available: bool = True) -> Dict:
    decisions = plan_cohort(rows, registry=registry,
                            attended_available=attended_available)
    by_lane = Counter(d.next_lane for d in decisions)
    by_lane_unsettled = Counter(d.next_lane for d in decisions if not d.settled)
    return OrderedDict((
        ("schema", PLAN_SCHEMA),
        ("work_order", work_order),
        ("market_id", market_id),
        ("ladder", [OrderedDict((("rank", l.rank), ("lane", l.lane_id),
                                 ("billed_in", l.billed_in),
                                 ("needs_authorization", l.needs_authorization)))
                    for l in LADDER]),
        ("rows", len(decisions)),
        ("settled", sum(1 for d in decisions if d.settled)),
        ("by_next_lane", OrderedDict((l, by_lane.get(l, 0)) for l in LANE_IDS)),
        ("by_next_lane_unsettled", OrderedDict((l, by_lane_unsettled.get(l, 0))
                                               for l in LANE_IDS)),
        ("firecrawl_routed_families", list(firecrawl_routed_families(registry))),
        ("known_capability_walls", dict(KNOWN_CAPABILITY_WALLS)),
        ("attended_pressure", attended_pressure(decisions)),
        ("decisions", [d.as_dict() for d in decisions]),
    ))


__all__ = [
    "SCHEMA", "PLAN_SCHEMA", "OWNED_EVIDENCE", "LOCAL_FREE_DISCOVERY",
    "DIRECT_STATIC_FETCH", "FIRECRAWL", "ATTENDED_BROWSER", "PAID_FETCH",
    "PAID_IDENTITY_DISCOVERY", "Lane", "LADDER", "LANE_IDS", "lane_rank",
    "FIRECRAWL_CLASSES", "FIRECRAWL_PUBLICATION_GRADE", "FIRECRAWL_IDENTITY_ONLY",
    "FIRECRAWL_SOURCE_SILENT", "FIRECRAWL_BLOCKED", "FIRECRAWL_MISMATCH",
    "FIRECRAWL_FAILED", "NON_EVIDENCE_SURFACES", "classify_firecrawl_result",
    "Candidacy", "firecrawl_candidacy", "firecrawl_routed_families",
    "KNOWN_CAPABILITY_WALLS", "CODE_BOUND_FAMILIES", "ESCALATABLE_STATIC_OUTCOMES",
    "RowEvidence", "Decision", "plan_row", "plan_cohort", "attended_pressure",
    "DEFAULT_WARNING_THRESHOLD", "Request", "bind_results", "rows_from_reports",
    "plan_document",
]
