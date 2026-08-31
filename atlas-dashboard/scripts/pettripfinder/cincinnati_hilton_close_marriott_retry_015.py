# -*- coding: utf-8 -*-
"""PTF-CINCINNATI-HILTON-CLOSE-AND-MARRIOTT-RETRY-PROBE-015.

Two narrow questions, deliberately not pooled.

**Hilton** had four rows left. They were bought, and with pilot 014's four the
brand is finished: eight properties, eight pages reached, seven publication
grade, one hotel that publishes no pet policy. Nothing here is a rate to
extrapolate -- the population is exhausted, which is a better thing to be able
to say than a confidence interval.

**Marriott** is a measurement. Pilot 014 lost five rows to a challenge page and
could not test whether that challenge was per-session or per-property, because
the order authorised exactly one attempt each. This order retried those same
five once. The statistic is conditional and must stay conditional:

    P(reached on retry | first attempt was challenged)

Pooling fresh first attempts into that denominator would answer a different
question. So would quietly counting a proxy tunnel error as a challenge: one
retry never reached Marriott's servers at all, and a transport failure is not
evidence about a bot wall. It is reported on its own denominator instead.

The honest reading of the rates is that 4/5 and 3/8 have overlapping Wilson
intervals, so the rates alone do not establish that retrying helps. What does
carry weight is the mechanism: **none of the five challenges repeated.** A
property-specific block would have reproduced; these did not.
"""

from __future__ import annotations

import json
import math
from collections import OrderedDict
from pathlib import Path
from typing import Dict, Mapping, Sequence

from scripts.pettripfinder.cincinnati_brightdata_pilot_014 import (  # noqa: F401
    WALL_CHARS, PilotError, wilson,
)

WORK_ORDER = "PTF-CINCINNATI-HILTON-CLOSE-AND-MARRIOTT-RETRY-PROBE-015"
MARKET_ID = "cincinnati-oh"
SCHEMA = "ptf-retry-probe-measurement/1.0"

REPO_ROOT = Path(__file__).resolve().parents[2]
PKG = REPO_ROOT / "launch_packages" / "pettripfinder"
AUTH = PKG / "markets" / "authority" / MARKET_ID
REPORT = PKG / "markets" / "reports" / "cincinnati_hilton_close_marriott_retry_015.json"

#: The lane the order authorised, and the only one that ran.
LANE = "brightdata_browser"

#: A challenge repeating is the outcome that would have killed the retry idea.
CHALLENGE = "ACCESS_DENIED"

#: The transport never reached the origin. This says nothing about a bot wall
#: and is counted apart from one, in both directions: it is not a repeated
#: challenge, and it is not a reached page either.
INFRASTRUCTURE = ("NAVIGATION_FAILED", "CAPTURE_FAILED")

#: The three answers this order may issue about scaling Marriott.
SCALE_WITH_RETRY = "SCALE_WITH_SINGLE_RETRY_POLICY"
SCALE_FIRST_ONLY = "SCALE_FIRST_ATTEMPT_ONLY"
STOP_OR_CHANGE = "STOP_OR_CHANGE_LANE"


def reached(row: Mapping) -> bool:
    """Did the property's own page actually arrive?

    Size corroborates the outcome rather than overriding it: a challenge page
    is a few hundred characters and a transport failure is zero, so a row that
    claims success while carrying no content would be caught here.
    """
    if str(row.get("outcome") or "") in INFRASTRUCTURE:
        return False
    if str(row.get("outcome") or "") == CHALLENGE:
        return False
    return int(row.get("body_chars") or 0) > WALL_CHARS


def retry_measurement(first_attempts: Sequence[Mapping],
                      retries: Sequence[Mapping]) -> Dict:
    """The conditional question, on both denominators that matter."""
    challenged = [r for r in first_attempts
                  if str(r.get("outcome") or "") == CHALLENGE]
    retried_keys = {str(r.get("identity_key") or "") for r in retries}
    missing = sorted({str(r.get("identity_key") or "") for r in challenged}
                     - retried_keys)

    recovered = [r for r in retries if reached(r)]
    graded = [r for r in retries if r.get("publication_grade")]
    repeated = [r for r in retries
                if str(r.get("outcome") or "") == CHALLENGE]
    infra = [r for r in retries
             if str(r.get("outcome") or "") in INFRASTRUCTURE]
    connected = [r for r in retries
                 if str(r.get("outcome") or "") not in INFRASTRUCTURE]

    return OrderedDict((
        ("first_attempts", len(first_attempts)),
        ("first_attempt_reached", sum(1 for r in first_attempts if reached(r))),
        ("challenged_on_first_attempt", len(challenged)),
        ("retries_attempted", len(retries)),
        ("challenged_rows_not_retried", missing),
        ("retries_reaching_property_page", len(recovered)),
        ("retries_publication_grade", len(graded)),
        ("repeated_challenges", len(repeated)),
        ("infrastructure_failures", len(infra)),
        # What money buys: a retry that reaches the page, per retry paid for.
        ("reach_given_challenged_over_attempts",
         wilson(len(recovered), len(retries))),
        # What the wall did, among sessions that actually reached the origin.
        # A tunnel that never connected cannot testify about a bot challenge.
        ("reach_given_challenged_over_connected",
         wilson(len(recovered), len(connected))),
        ("challenge_repeat_rate", wilson(len(repeated), len(connected))),
    ))


def combined_access(first_attempts: Sequence[Mapping],
                    retries: Sequence[Mapping]) -> Dict:
    """Access over the ORIGINAL rows under a two-attempt policy.

    The denominator is the first-attempt cohort, not first attempts plus
    retries: a row retried once is still one property, and counting it twice
    would inflate the base the policy is meant to describe.
    """
    keys = [str(r.get("identity_key") or "") for r in first_attempts]
    got = {k for k, r in zip(keys, first_attempts) if reached(r)}
    got |= {str(r.get("identity_key") or "") for r in retries if reached(r)}
    return OrderedDict((
        ("rows", len(keys)),
        ("reached_within_two_attempts", len(got)),
        ("access", wilson(len(got), len(keys))),
    ))


def recommend(retry: Mapping, combined: Mapping) -> Dict:
    """One of three answers, with the reason it is not one of the others.

    The rule is deliberately not "the retry rate beat the first-attempt rate":
    on these sample sizes those intervals overlap, and a decision resting on
    overlapping intervals is a decision resting on noise. What licenses the
    retry policy is that challenges did not REPEAT -- a per-property block
    would have -- and that two-attempt access is materially above one-attempt
    access at the lower bound.
    """
    repeat_rate = retry["challenge_repeat_rate"]["point"]
    recovered = retry["retries_reaching_property_page"]
    attempted = retry["retries_attempted"]
    if attempted == 0:
        raise PilotError("no retry was attempted, so no retry policy can be "
                         "recommended from this order")

    if repeat_rate == 0 and recovered > 0:
        return OrderedDict((
            ("recommendation", SCALE_WITH_RETRY),
            ("policy", "at most two browser attempts per property: the first, "
                       "and one retry if and only if the first was challenged"),
            ("why", "none of the %d challenges repeated on retry, which a "
                    "property-specific block would have done, and %d of %d "
                    "retries reached the page. Two-attempt access is %s "
                    "against one-attempt access of %s."
             % (retry["challenged_on_first_attempt"], recovered, attempted,
                combined["access"]["point"],
                round(retry["first_attempt_reached"]
                      / max(1, retry["first_attempts"]), 4))),
            ("what_would_change_it",
             "a repeated challenge rate above zero at scale. Five rows cannot "
             "prove it stays zero, so the scale-up must measure it again "
             "rather than assume this held."),
        ))
    if recovered == 0:
        return OrderedDict((
            ("recommendation", STOP_OR_CHANGE),
            ("policy", "do not buy a second attempt on this lane"),
            ("why", "no retry reached the page, so the wall is not per-session "
                    "and a second attempt buys nothing"),
        ))
    return OrderedDict((
        ("recommendation", SCALE_FIRST_ONLY),
        ("policy", "one browser attempt per property"),
        ("why", "challenges repeated on retry, so a second attempt on the same "
                "lane is only sometimes the same wall again and cannot be "
                "priced as recovery"),
    ))


def project(rows: int, *, first_access: Mapping, combined: Mapping,
            extraction: Mapping, rate_usd: float) -> Dict:
    """What scaling the remainder would cost and return under the policy.

    Attempts are projected at the LOWER bound of first-attempt access, because
    the pessimistic case for cost is the case where most rows need the retry --
    and a budget that is only correct when access is good is not a budget.
    Records are projected at the lower bound too, for the same reason applied
    to the other side of the ledger.
    """
    retry_share_worst = 1.0 - first_access["low"]
    retry_share_point = 1.0 - (first_access["point"] or 0.0)
    expected = rows + int(math.ceil(rows * retry_share_point))
    worst = rows + int(math.ceil(rows * retry_share_worst))
    ceiling = rows * 2
    yield_low = combined["access"]["low"] * extraction["low"]
    yield_point = (combined["access"]["point"] or 0) * (extraction["point"] or 0)
    return OrderedDict((
        ("rows", rows),
        ("attempts_expected", expected),
        ("attempts_worst_case", worst),
        ("attempts_hard_ceiling", ceiling),
        ("usd_per_attempt", rate_usd),
        ("cost_expected_usd", round(expected * rate_usd, 2)),
        ("cost_worst_case_usd", round(worst * rate_usd, 2)),
        ("cost_hard_ceiling_usd", round(ceiling * rate_usd, 2)),
        ("records_low", int(math.floor(rows * yield_low))),
        ("records_point", int(round(rows * yield_point))),
        ("recommended_hard_cap_usd", round(ceiling * rate_usd, 2)),
        ("why_the_ceiling",
         "the cap is set at two attempts for every row, which is the most the "
         "policy can ever spend. Sizing a cap at the EXPECTED number of "
         "attempts guarantees the run stops halfway the first time access is "
         "worse than the sample."),
    ))


def render_json(document: Mapping) -> str:
    return json.dumps(document, indent=1, ensure_ascii=False) + "\n"
