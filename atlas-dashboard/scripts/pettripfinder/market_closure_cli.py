"""PTF-ST-LOUIS-MARKET-001 -- active eligibility, final partition, closure.

One pass, four artifacts, all derived and none asserted:

    active eligibility   which census identities are in play at all
    final partition      what each identity is WAITING ON
    closure ledger       what each ACTIVE identity IS, in founder terms
    review package       every publication-grade candidate, with its lineage

    python scripts/pettripfinder/market_closure_cli.py \
      --market st-louis-mo --observations <store.json> --pilot <pilot.json> \
      --as-of 2026-08-23 --work-order PTF-ST-LOUIS-MARKET-001

ACTIVE ELIGIBILITY IS MECHANICAL
--------------------------------
An identity is ACTIVE when the census says all three of:

    identity_state == IDENTITY_CONFIRMED
    lodging_state  in (LODGING_CONFIRMED, LODGING_BY_NAME)
    corridor       != ""   (a corridor claimed its postal code)

and NOT_ACTIVE otherwise -- with the reason recorded. There is no fourth
answer and no row without one. The active set is the closure ledger's
denominator, and the ledger refuses to exist unless it covers that set
exactly (set comparison, never arithmetic).

NOTHING HERE CREATES AUTHORITY
------------------------------
A publication-grade candidate closes as HELD_REVIEW and partitions as
AWAITING_FOUNDER_DECISION. ``AUTHORITY_PET_FRIENDLY`` and
``AUTHORITY_VERIFIED_NO_PETS`` are reachable in this vocabulary and
unreachable from this code path: only a founder decision produces one.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import census_partition_builder as CPB
from scripts.pettripfinder.acquisition import market_routing as MR
from scripts.pettripfinder.contracts import closure as CL
from scripts.pettripfinder.contracts import enums

PACKAGE_DIR = _REPO_ROOT / "launch_packages" / "pettripfinder"
from scripts.pettripfinder import census_location as CENSUS_LOCATION  # noqa: E402
CENSUS_DIR = CENSUS_LOCATION.identity_census_dir()  # committed, or $PTF_IDENTITY_CENSUS_DIR during a rebuild
ACTIVE = "ACTIVE_ELIGIBLE"
NOT_ACTIVE_IDENTITY = "NOT_ACTIVE_IDENTITY_UNRESOLVED"
NOT_ACTIVE_CATEGORY = "NOT_ACTIVE_NOT_LODGING"
NOT_ACTIVE_GEOGRAPHY = "NOT_ACTIVE_NO_CORRIDOR"

ELIGIBILITY_STATES: Tuple[str, ...] = (
    ACTIVE, NOT_ACTIVE_IDENTITY, NOT_ACTIVE_CATEGORY, NOT_ACTIVE_GEOGRAPHY,
)

#: Capture outcomes that mean the surface refused us, not that it was silent.
ACCESS_OUTCOMES = frozenset({"ACCESS_DENIED", "NAVIGATION_FAILED", "TIMEOUT",
                             "BLOCKED", "CAPTURE_FAILED"})
#: Capture outcomes that mean we reached a page but could not bind it to THIS
#: property, or the page we reached was not the one asked for.
IDENTITY_OUTCOMES = frozenset({"IDENTITY_MISMATCH", "UNEXPECTED_PAGE"})
#: Capture outcomes that mean the property's own page SERVED ITS CONTENT and
#: states nothing about pets. This is the only set from which the word
#: POLICY_NOT_FOUND may be said, because it is the only one that is a claim
#: about the hotel rather than about us.
SILENT_OUTCOMES = frozenset({"POLICY_NOT_FOUND"})

#: Outcomes that mean a document arrived and had not finished being a page --
#: an unrendered client-side template, a shell, a blank body. Not silence:
#: an escalation to a lane that renders.
UNRENDERED_OUTCOMES = frozenset({"UNHYDRATED", "BLANK_PAGE"})


def eligibility(row: Mapping) -> Tuple[str, str]:
    """``(state, why)`` -- mechanical, from census fields only."""
    if row.get("identity_state") != enums.IDENTITY_CONFIRMED:
        return (NOT_ACTIVE_IDENTITY,
                "census identity_state is %r" % row.get("identity_state"))
    if row.get("lodging_state") not in (enums.LODGING_CONFIRMED,
                                        enums.LODGING_BY_NAME):
        return (NOT_ACTIVE_CATEGORY,
                "census lodging_state is %r" % row.get("lodging_state"))
    if not (row.get("corridor") or "").strip():
        return (NOT_ACTIVE_GEOGRAPHY,
                "no corridor in the market registry claims this identity's "
                "postal code")
    return (ACTIVE, "identity confirmed, in category, claimed by corridor %s"
            % row["corridor"])


def _partition_state(*, routing: Mapping, capture: Optional[Mapping],
                     observation: Optional[Mapping]) -> Tuple[str, str]:
    """The ONE thing this active identity is waiting on, and why."""
    if observation is not None:
        grade = (observation.get("publication_grade") or {}).get("verdict")
        if grade == "PUBLICATION_GRADE_CONFIRMED":
            return (enums.AWAITING_FOUNDER_DECISION,
                    "a publication-grade observation exists on the property's "
                    "own page; the outstanding step is a founder decision")
        return (enums.AWAITING_POLICY_ARTIFACT,
                "a policy was read but the capture does not satisfy the "
                "evidence contract: %s"
                % "; ".join((observation.get("publication_grade") or {})
                            .get("reasons") or ["no reason recorded"])[:300])

    state = routing["routing_state"]
    if state == MR.ROUTE_NEEDS_OFFICIAL_URL:
        return (enums.AWAITING_OFFICIAL_URL,
                "no official URL has ever been found for this identity")
    if state == MR.ROUTE_NEEDS_PROPERTY_URL:
        return (enums.AWAITING_PROPERTY_LEVEL_URL, routing["why"])
    if state == MR.ROUTE_NEEDS_FIRST_PARTY_URL:
        return (enums.AWAITING_ROUTING_REPLACEMENT, routing["why"])
    if state == MR.ROUTE_BRAND_EXCLUDED:
        return (enums.AWAITING_ROUTING_REVIEW, routing["why"])

    if capture is None:
        return (enums.AWAITING_POLICY_OBSERVATION,
                "routed to a measured lane and never attempted, so nothing is "
                "known about what this property's page says")
    outcome = capture["outcome"]
    # Which lane was refused is part of the finding. The first St. Louis pass
    # could only say "the free lane" because it was the only lane that could
    # run; once a paid lane runs too, that phrasing names the wrong one.
    lane = capture.get("provider") or "the free lane"
    if outcome in ACCESS_OUTCOMES:
        return (enums.ACCESS_BLOCKED,
                "%s was refused (%s): %s"
                % (lane, outcome, capture.get("detail", "")[:200]))
    if outcome in IDENTITY_OUTCOMES:
        return (enums.AWAITING_ATTENDED_CAPTURE,
                "the page served but %s could not bind it to this property "
                "(%s): %s"
                % (lane, outcome, capture.get("detail", "")[:200]))
    if outcome in UNRENDERED_OUTCOMES:
        return (enums.AWAITING_ATTENDED_CAPTURE,
                "a document arrived but had not finished being a page (%s): %s"
                % (outcome, capture.get("detail", "")[:200]))
    if outcome in SILENT_OUTCOMES:
        return (enums.AWAITING_POLICY_OBSERVATION,
                "the property's own page served, its identity was confirmed, "
                "and it states no pet policy as read by %s (%s)"
                % (lane, outcome))
    return (enums.AWAITING_POLICY_OBSERVATION,
            "capture outcome %r left no policy observation" % outcome)


def closure_for(blocker: str, capture: Optional[Mapping]) -> str:
    """Partition blocker -> closure disposition, in ONE place, so the two
    artifacts can never tell a founder two different stories.

    ``AWAITING_POLICY_OBSERVATION`` is the one blocker that needs the capture
    to disambiguate. It covers two situations the founder must not see merged:
    a page that served and said nothing (POLICY_NOT_FOUND -- a fact about the
    hotel) and a page nobody has fetched (ACCESS_UNRESOLVED -- a fact about us).
    """
    if blocker != enums.AWAITING_POLICY_OBSERVATION:
        return CLOSURE_FOR_BLOCKER[blocker]
    outcome = (capture or {}).get("outcome", "")
    if outcome in SILENT_OUTCOMES:
        return CL.POLICY_NOT_FOUND
    return CL.ACCESS_UNRESOLVED


#: Blockers whose closure disposition needs no further evidence.
CLOSURE_FOR_BLOCKER: Dict[str, str] = {
    enums.AWAITING_FOUNDER_DECISION: CL.HELD_REVIEW,
    enums.AWAITING_POLICY_ARTIFACT: CL.INSUFFICIENT_EVIDENCE,
    enums.AWAITING_OFFICIAL_URL: CL.INSUFFICIENT_EVIDENCE,
    enums.AWAITING_PROPERTY_LEVEL_URL: CL.INSUFFICIENT_EVIDENCE,
    enums.AWAITING_ROUTING_REPLACEMENT: CL.INSUFFICIENT_EVIDENCE,
    enums.AWAITING_ROUTING_REVIEW: CL.ACCESS_UNRESOLVED,
    enums.ACCESS_BLOCKED: CL.ACCESS_UNRESOLVED,
    enums.AWAITING_ATTENDED_CAPTURE: CL.ACCESS_UNRESOLVED,
    enums.AWAITING_POLICY_OBSERVATION: CL.POLICY_NOT_FOUND,
    enums.AWAITING_CONTRADICTION_RESOLUTION: CL.SOURCE_CONFLICT,
    enums.AWAITING_IDENTITY_RESOLUTION: CL.IDENTITY_UNRESOLVED,
    enums.AWAITING_CENSUS_REVIEW: CL.OTHER,
}


def build(market_id: str, census: Mapping, *, observations: Mapping,
          pilot: Mapping, as_of: str, work_order: str):
    rows = census["hotels"]
    routing_entries, routing_summary = MR.route_census(rows)
    routing_by_key = {e["identity_key"]: e for e in routing_entries}
    capture_by_key = {r["identity_key"]: r for r in (pilot.get("results") or ())}
    obs_by_key = {r["identity_key"]: r for r in (observations.get("records") or ())}

    eligible: List[Dict] = []
    not_active: List[Dict] = []
    for row in rows:
        state, why = eligibility(row)
        record = OrderedDict((
            ("identity_key", row["identity_key"]),
            ("canonical_name", row["canonical_name"]),
            ("corridor", row.get("corridor", "")),
            ("eligibility", state),
            ("why", why),
        ))
        (eligible if state == ACTIVE else not_active).append(record)

    active_keys = [r["identity_key"] for r in eligible]

    partition_items: List[Dict] = []
    closure_rows: List[Dict] = []
    for row in rows:
        key = row["identity_key"]
        state, why = eligibility(row)
        routing = routing_by_key[key]
        if state != ACTIVE:
            blocker = {
                NOT_ACTIVE_IDENTITY: enums.AWAITING_IDENTITY_RESOLUTION,
                NOT_ACTIVE_CATEGORY: enums.AWAITING_CENSUS_REVIEW,
                NOT_ACTIVE_GEOGRAPHY: enums.AWAITING_CENSUS_REVIEW,
            }[state]
            partition_items.append(CPB.partition_item(
                identity_key=key, canonical_name=row["canonical_name"],
                slug=row.get("slug", ""), city=row.get("city", ""),
                state=row.get("state", ""), postal_code=row.get("postal_code", ""),
                final_state=blocker, next_action_source=why,
                determined_by=work_order, updated_at=as_of,
                official_url=routing["source_url"]))
            continue

        blocker, blocker_why = _partition_state(
            routing=routing, capture=capture_by_key.get(key),
            observation=obs_by_key.get(key))
        partition_items.append(CPB.partition_item(
            identity_key=key, canonical_name=row["canonical_name"],
            slug=row.get("slug", ""), city=row.get("city", ""),
            state=row.get("state", ""), postal_code=row.get("postal_code", ""),
            final_state=blocker, next_action_source=blocker_why,
            determined_by=work_order, updated_at=as_of,
            official_url=routing["source_url"]))

        capture = capture_by_key.get(key) or {}
        observation = obs_by_key.get(key) or {}
        closure_rows.append(CL.ledger_row(
            identity_key=key, canonical_name=row["canonical_name"],
            corridor=row.get("corridor", ""),
            disposition=closure_for(blocker, capture_by_key.get(key)),
            why=blocker_why,
            source_url=routing["source_url"], brand=routing["brand"],
            routing_state=routing["routing_state"],
            acquisition_outcome=capture.get("outcome", ""),
            evidence_ref=(observation.get("observation") or {}).get("obs_id", ""),
            partition_state=blocker))

    partition = CPB.partition_document(
        market_id, partition_items, as_of=as_of,
        note=("%s. Every census identity appears exactly once. Active "
              "eligibility is derived from census fields only; every active "
              "identity's blocker is derived from its routing entry, its "
              "capture outcome and its observation, in that order of "
              "specificity." % work_order),
        source_authorities=[
            CENSUS_LOCATION.relative_census_path(market_id),
            "scripts/pettripfinder/acquisition/market_routing.py over that census",
            observations.get("derived_from", ""),
        ])
    partition["work_order"] = work_order

    ledger = CL.document(
        market_id, closure_rows, work_order=work_order, as_of=as_of,
        active_keys=active_keys,
        note=("Every ACTIVE-ELIGIBLE identity, dispositioned exactly once. "
              "Authority buckets are empty by construction: no founder "
              "decision has been taken for this market."),
        eligibility_counts=OrderedDict(sorted(
            Counter(r["eligibility"] for r in (eligible + not_active)).items())),
        not_active=not_active,
        routing_summary=routing_summary)

    candidates = [OrderedDict((
        ("identity_key", r["identity_key"]),
        ("canonical_name", r["canonical_name"]),
        ("corridor", r["corridor"]),
        ("brand", r["brand"]),
    )) for r in (observations.get("records") or ())
        if (r.get("publication_grade") or {}).get("verdict")
        == "PUBLICATION_GRADE_CONFIRMED"]

    return partition, ledger, candidates, eligible, not_active


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--market", required=True)
    parser.add_argument("--observations", required=True)
    parser.add_argument("--pilot", required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--work-order", required=True)
    parser.add_argument("--url-overlay", default="",
                        help="the ptf-census-url-recovery report the paid pass "
                             "routed with; closure must route the same census "
                             "the run did, or it reports a market as unrouted "
                             "that the run reached")
    parser.add_argument("--partition-out", default="")
    parser.add_argument("--closure-out", default="")
    args = parser.parse_args(argv)

    census = json.loads((CENSUS_DIR / ("%s.json" % args.market))
                        .read_text(encoding="utf-8"))
    overlay = MR.apply_url_overlay(census["hotels"], args.url_overlay)
    observations = json.loads(Path(args.observations).read_text(encoding="utf-8"))
    pilot = json.loads(Path(args.pilot).read_text(encoding="utf-8"))

    partition, ledger, candidates, eligible, not_active = build(
        args.market, census, observations=observations, pilot=pilot,
        as_of=args.as_of, work_order=args.work_order)

    partition_path = Path(args.partition_out) if args.partition_out else (
        PACKAGE_DIR / ("%s_final_partition_001.json" % args.market.replace("-", "_")))
    closure_path = Path(args.closure_out) if args.closure_out else (
        PACKAGE_DIR / ("%s_closure_ledger_001.json" % args.market.replace("-", "_")))
    p_sha = CPB.write_json(partition_path, partition)
    c_sha = CPB.write_json(closure_path, ledger)

    print("census identities   : %d" % census["count"])
    print("url overlay applied : %d" % overlay["applied"])
    print("active eligible     : %d" % len(eligible))
    print("not active          : %d" % len(not_active))
    print("partition states    : %s" % dict(partition["final_state_counts"]))
    print("closure dispositions: %s" % dict(ledger["disposition_counts"]))
    print("review candidates   : %d" % len(candidates))
    print("partition           : %s (%s)" % (partition_path.name, p_sha))
    print("closure ledger      : %s (%s)" % (closure_path.name, c_sha))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
