# -*- coding: utf-8 -*-
"""PTF-CINCINNATI-BRIGHTDATA-PILOT-014 -- Cincinnati's first paid measurement.

Twelve properties, one Bright Data browser attempt each, no retries and no
escalation. The pilot exists to answer one question per brand family: does the
paid lane convert in THIS market, at a rate worth buying the rest of the
cohort at?

The distinction this module refuses to blend is the one the brand-repair pilot
established: **access is not extraction.** Five Marriott rows returned a ~250
character bot wall -- the lane never reached the property. One Hilton row
returned a six-thousand character page that simply does not publish a pet
policy. Both are "not published", and treating them as one number would price
a bot wall and a silent page identically. They have different causes, different
remedies, and only one of them is a reason to buy anything.

So every rate here is reported twice: over ATTEMPTS, which is what money buys,
and over PAGES REACHED, which is what the reader saw. Sizing uses the Wilson
lower bound on attempts, because a cohort sized on a point estimate is a cohort
sized on the luckiest reading of a small sample.
"""

from __future__ import annotations

import json
import math
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Sequence

WORK_ORDER = "PTF-CINCINNATI-BRIGHTDATA-PILOT-014"
MARKET_ID = "cincinnati-oh"
SCHEMA = "ptf-paid-pilot-measurement/1.0"

REPO_ROOT = Path(__file__).resolve().parents[2]
PKG = REPO_ROOT / "launch_packages" / "pettripfinder"
AUTH = PKG / "markets" / "authority" / MARKET_ID
REPORT = PKG / "markets" / "reports" / "cincinnati_brightdata_pilot_014.json"

#: The lane the order authorised, and the only one that was run.
LANE = "brightdata_browser"

#: An outcome where the lane never delivered the property's page. The body is a
#: challenge page of a few hundred characters, so nothing could be read from it
#: whatever reader ran. This is the failure a better crawler could fix.
ACCESS_FAILURES = ("ACCESS_DENIED",)

#: An outcome where the page ARRIVED and the property published no pet policy
#: on it. A paid provider cannot create text the hotel does not publish, so
#: this is never a reason to buy a different lane for the same row.
SOURCE_SILENCE = ("POLICY_NOT_FOUND",)

#: Below this, a body is a challenge page rather than a property page. Used
#: only to CORROBORATE the outcome the runner already recorded -- it never
#: overrides it, because a threshold that reclassifies a vendor's own verdict
#: is a second opinion nobody measured.
WALL_CHARS = 600


class PilotError(RuntimeError):
    """Raised when the pilot cannot be described honestly."""


def wilson(successes: int, trials: int, z: float = 1.96) -> Dict:
    """The 95% score interval. Point rates on twelve trials are not evidence.

    Returned with both bounds because they answer different questions: the
    LOWER bound is what a purchase must be sized on, and the UPPER bound is
    what a feasibility claim may lean on.
    """
    if trials <= 0:
        return OrderedDict((("point", None), ("low", 0.0), ("high", 1.0),
                            ("successes", 0), ("trials", 0)))
    phat = successes / trials
    denom = 1.0 + z * z / trials
    centre = phat + z * z / (2 * trials)
    margin = z * math.sqrt(phat * (1 - phat) / trials
                           + z * z / (4 * trials * trials))
    return OrderedDict((
        ("point", round(phat, 4)),
        ("low", round((centre - margin) / denom, 4)),
        ("high", round((centre + margin) / denom, 4)),
        ("successes", int(successes)), ("trials", int(trials)),
    ))


def classify(row: Mapping) -> str:
    """One of ACCESS_FAILED, SOURCE_SILENT, PUBLICATION_GRADE, OTHER."""
    outcome = str(row.get("outcome") or "")
    if outcome in ACCESS_FAILURES:
        return "ACCESS_FAILED"
    if outcome in SOURCE_SILENCE:
        return "SOURCE_SILENT"
    if row.get("publication_grade"):
        return "PUBLICATION_GRADE"
    return "OTHER"


def measure(rows: Sequence[Mapping]) -> Dict:
    """Per-brand access and extraction, each with its own interval."""
    families: Dict[str, List[Mapping]] = OrderedDict()
    for row in rows:
        families.setdefault(str(row.get("brand") or "UNKNOWN"), []).append(row)

    out: Dict[str, Dict] = OrderedDict()
    for brand in sorted(families):
        group = families[brand]
        states = [classify(r) for r in group]
        attempts = len(group)
        reached = sum(1 for s in states if s != "ACCESS_FAILED")
        graded = sum(1 for s in states if s == "PUBLICATION_GRADE")
        silent = sum(1 for s in states if s == "SOURCE_SILENT")
        out[brand] = OrderedDict((
            ("attempts", attempts),
            ("pages_reached", reached),
            ("publication_grade", graded),
            ("access_failed", attempts - reached),
            ("source_silent", silent),
            # What money buys: a publication-grade record per paid attempt.
            ("yield_per_attempt", wilson(graded, attempts)),
            # What the lane can reach at all. On a bot-walled brand this is the
            # number that decides whether to buy again; the reader is not the
            # bottleneck when the page never arrives.
            ("access_per_attempt", wilson(reached, attempts)),
            # What the reader did with the pages it actually got. Reported so a
            # reader problem can never hide inside a lane problem.
            ("extraction_per_page_reached", wilson(graded, reached)),
        ))
    return out


def spend_view(*, balance_before: float, balance_after: float,
               runner_measured_usd: float, attempts: int) -> Dict:
    """Three meters that disagree, all of them reported.

    The vendor's zone meter lags a session and has both settled upward and
    restated downward on previous runs, so no single figure is treated as the
    truth. The cap was enforced on the largest, which is the only safe way to
    enforce a ceiling against a lagging meter.
    """
    delta = round(balance_before - balance_after, 4)
    return OrderedDict((
        ("prepaid_balance_before_usd", balance_before),
        ("prepaid_balance_after_usd", balance_after),
        ("prepaid_balance_delta_usd", delta),
        ("runner_measured_usd", runner_measured_usd),
        ("attempts", attempts),
        ("usd_per_attempt_by_balance", round(delta / attempts, 4)
         if attempts else None),
        ("usd_per_attempt_by_runner", round(runner_measured_usd / attempts, 4)
         if attempts else None),
        ("sizing_rate_usd_per_attempt",
         round(max(delta, runner_measured_usd) / attempts, 4)
         if attempts else None),
        ("why_the_larger",
         "a cohort priced on the cheaper of two disagreeing meters is a cohort "
         "that overruns its cap when the cheaper meter turns out to be the "
         "lagging one"),
    ))


def reprice(remaining: Mapping[str, int], measured: Mapping[str, Dict],
            rate_usd: float) -> Dict:
    """What the rest of the cohort would cost, and what it would return.

    Sized on the Wilson LOWER bound: the honest floor of what the money buys.
    The point estimate is carried alongside so the range is visible, never so
    it can be quoted as the expectation.
    """
    out: Dict[str, Dict] = OrderedDict()
    for brand in sorted(remaining):
        count = int(remaining[brand])
        stats = measured.get(brand)
        if stats is None:
            raise PilotError(
                "%s has %d rows left and no measurement from this pilot; "
                "pricing it would be quoting another brand's luck"
                % (brand, count))
        band = stats["yield_per_attempt"]
        floor = int(math.floor(count * band["low"]))
        out[brand] = OrderedDict((
            ("remaining_rows", count),
            ("cost_usd", round(count * rate_usd, 2)),
            ("expected_records_low", floor),
            ("expected_records_point", int(round(count * (band["point"] or 0)))),
            ("expected_records_high", int(math.floor(count * band["high"]))),
            ("cost_per_record_at_low_bound",
             round(count * rate_usd / floor, 2) if floor > 0 else None),
        ))
    return out


def render_json(document: Mapping) -> str:
    return json.dumps(document, indent=1, ensure_ascii=False) + "\n"
