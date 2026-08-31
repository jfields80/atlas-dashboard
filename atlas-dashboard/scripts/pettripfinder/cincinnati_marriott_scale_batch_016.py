# -*- coding: utf-8 -*-
"""PTF-CINCINNATI-MARRIOTT-SCALE-BATCH-016 -- the first Marriott scale batch.

Fourteen properties under the policy Order 015 measured: one first attempt,
and at most one same-lane retry for a row that came back with no usable page.
Executed as two explicit passes rather than one router decision, so "at most
two attempts" is a property of the run rather than a hope about the router.

Every one of the fourteen finished publication grade. That is a better result
than any prior Cincinnati pass and it is the reason this module is careful:

* the batch is fourteen, not the authorised seventeen. Seventeen rows at the
  settled rate is a worst case of exactly the cap, which would have left the
  account at $0.21. Reducing before spending was the instruction and also the
  only way the run could not strand its own tail;
* first-attempt access was 10/14 here against 3/8 in pilot 014. Those intervals
  OVERLAP, so this is not evidence that the wall got easier -- it is evidence
  that first-attempt access is variable, which is itself the argument for
  keeping the retry;
* the repeat-challenge rate is the number the policy rests on, and it is
  computed over CHALLENGE rows only. Two of the four retried rows were
  transport failures, and a tunnel that never reached Marriott cannot testify
  about a bot wall in either direction.
"""

from __future__ import annotations

import json
import math
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Sequence

from scripts.pettripfinder.cincinnati_brightdata_pilot_014 import (  # noqa: F401
    WALL_CHARS, PilotError, wilson,
)
from scripts.pettripfinder.cincinnati_hilton_close_marriott_retry_015 import (
    CHALLENGE, INFRASTRUCTURE, reached,
)

WORK_ORDER = "PTF-CINCINNATI-MARRIOTT-SCALE-BATCH-016"
MARKET_ID = "cincinnati-oh"
SCHEMA = "ptf-paid-scale-batch/1.0"

REPO_ROOT = Path(__file__).resolve().parents[2]
PKG = REPO_ROOT / "launch_packages" / "pettripfinder"
AUTH = PKG / "markets" / "authority" / MARKET_ID
REPORT = PKG / "markets" / "reports" / "cincinnati_marriott_scale_batch_016.json"

LANE = "brightdata_browser"

#: The most attempts any property may receive in this order, ever.
MAX_ATTEMPTS_PER_PROPERTY = 2

#: A first-attempt outcome that does NOT earn a retry: the page arrived, or the
#: source answered, or the row needs a decision rather than another fetch.
NOT_RETRY_ELIGIBLE = ("VALID", "POLICY_NOT_FOUND", "IDENTITY_MISMATCH",
                      "UNEXPECTED_PAGE")

#: The three answers this order may issue about the rest of the pool.
CONTINUE = "CONTINUE_SINGLE_RETRY_SCALE"
CHANGE_LANE = "CHANGE_LANE"
STOP = "STOP_PAID_ACQUISITION"

#: Above this, a repeat-challenge rate means the retry is buying the same wall
#: again and the one-retry policy has to be reconsidered rather than renewed.
MATERIAL_REPEAT_RATE = 0.25


class ScaleBatchError(RuntimeError):
    """Raised when the batch cannot be described honestly."""


def retry_eligible(row: Mapping) -> bool:
    """Did this first attempt leave us with no usable page?

    Publication grade is checked as well as outcome: a row that reached
    publication grade is finished whatever else its outcome says, and buying it
    again would be buying an answer we own.
    """
    if row.get("publication_grade"):
        return False
    return str(row.get("outcome") or "") not in NOT_RETRY_ELIGIBLE


def first_pass(rows: Sequence[Mapping]) -> Dict:
    """What one attempt each bought."""
    challenge = [r for r in rows if str(r.get("outcome") or "") == CHALLENGE]
    transport = [r for r in rows
                 if str(r.get("outcome") or "") in INFRASTRUCTURE]
    silent = [r for r in rows
              if str(r.get("outcome") or "") == "POLICY_NOT_FOUND"]
    identity = [r for r in rows
                if str(r.get("outcome") or "") in ("IDENTITY_MISMATCH",
                                                   "UNEXPECTED_PAGE")]
    return OrderedDict((
        ("attempts", len(rows)),
        ("reached", sum(1 for r in rows if reached(r))),
        ("publication_grade", sum(1 for r in rows if r.get("publication_grade"))),
        ("challenge_failures", len(challenge)),
        ("transport_failures", len(transport)),
        ("policy_silence", len(silent)),
        ("identity_failures", len(identity)),
        ("access", wilson(sum(1 for r in rows if reached(r)), len(rows))),
    ))


def retry_pass(eligible: Sequence[Mapping],
               retries: Sequence[Mapping]) -> Dict:
    """What the single authorised retry bought, and whether walls repeated.

    ``repeat_challenge_rate`` is deliberately computed over the rows whose
    FIRST attempt was a challenge, not over every retry. Pooling transport
    failures into that denominator would dilute the one number the policy
    depends on.
    """
    by_key = {str(r.get("identity_key") or ""): r for r in eligible}
    was_challenged = {k for k, r in by_key.items()
                      if str(r.get("outcome") or "") == CHALLENGE}

    recovered = [r for r in retries if reached(r)]
    graded = [r for r in retries if r.get("publication_grade")]
    repeated = [r for r in retries
                if str(r.get("outcome") or "") == CHALLENGE
                and str(r.get("identity_key") or "") in was_challenged]
    transport = [r for r in retries
                 if str(r.get("outcome") or "") in INFRASTRUCTURE]
    challenged_retries = [r for r in retries
                          if str(r.get("identity_key") or "") in was_challenged]
    other = [r for r in retries
             if not reached(r)
             and str(r.get("outcome") or "") not in INFRASTRUCTURE
             and str(r.get("outcome") or "") != CHALLENGE]

    return OrderedDict((
        ("eligible", len(eligible)),
        ("attempted", len(retries)),
        ("recovered_access", len(recovered)),
        ("recovered_publication_grade", len(graded)),
        ("repeated_challenges", len(repeated)),
        ("repeated_transport_failures", len(transport)),
        ("other_failures", len(other)),
        ("challenge_rows_retried", len(challenged_retries)),
        ("repeat_challenge_rate", wilson(len(repeated),
                                         len(challenged_retries))),
        ("recovery_over_attempts", wilson(len(recovered), len(retries))),
    ))


def combined(rows: Sequence[Mapping], retries: Sequence[Mapping]) -> Dict:
    """One terminal state per identity, counted once."""
    final: Dict[str, Mapping] = {}
    for row in rows:
        final[str(row.get("identity_key") or "")] = row
    for row in retries:                      # the retry supersedes its own first
        final[str(row.get("identity_key") or "")] = row
    graded = [r for r in final.values() if r.get("publication_grade")]
    return OrderedDict((
        ("unique_identities", len(final)),
        ("publication_grade", len(graded)),
        ("failures", len(final) - len(graded)),
        ("two_attempt_access", wilson(sum(1 for r in final.values()
                                          if reached(r)), len(final))),
    ))


def recommend(retry: Mapping, combined_view: Mapping) -> Dict:
    """Whether to keep buying the rest of the pool the same way.

    A zero repeat rate does not prove the wall is always per-session; it proves
    it was per-session every time we have looked. The recommendation therefore
    carries the condition that would retire it, and the next batch is expected
    to measure the rate again rather than inherit this one.
    """
    rate = retry["repeat_challenge_rate"]["point"]
    if retry["challenge_rows_retried"] == 0:
        raise ScaleBatchError(
            "no challenged row was retried, so this batch cannot speak to the "
            "repeat-challenge rate and must not issue a policy on it")
    if rate is not None and rate >= MATERIAL_REPEAT_RATE:
        return OrderedDict((
            ("recommendation", CHANGE_LANE),
            ("why", "challenges repeated at %.0f%%, so the second attempt is "
                    "buying the same wall again" % (100 * rate)),
        ))
    return OrderedDict((
        ("recommendation", CONTINUE),
        ("policy", "first attempt plus at most one same-lane retry"),
        ("why", "%d of %d retried challenge rows repeated, and the batch "
                "finished %d of %d publication grade"
         % (retry["repeated_challenges"], retry["challenge_rows_retried"],
            combined_view["publication_grade"],
            combined_view["unique_identities"])),
        ("what_would_retire_it",
         "a repeat-challenge rate at or above %.0f%% in any later batch. The "
         "rate must be measured again each time; a policy that stops checking "
         "the number it depends on is an assumption wearing a measurement's "
         "clothes." % (100 * MATERIAL_REPEAT_RATE)),
    ))


def affordable_rows(balance_usd: float, rate_usd: float, *,
                    floor_usd: float = 1.00) -> int:
    """How many rows a balance can cover at two attempts each, keeping a floor.

    The floor exists because an account drained to nothing cannot run the small
    diagnostic that a surprising result would demand.
    """
    spendable = balance_usd - floor_usd
    if spendable <= 0 or rate_usd <= 0:
        return 0
    return int(spendable // (MAX_ATTEMPTS_PER_PROPERTY * rate_usd))


def project(rows: int, *, first_access: Mapping, rate_usd: float,
            balance_usd: float, floor_usd: float = 1.00) -> Dict:
    """Cost and reach for the rest of the pool under the measured policy."""
    retry_share = 1.0 - (first_access["point"] or 0.0)
    expected = rows + int(math.ceil(rows * retry_share))
    ceiling = rows * MAX_ATTEMPTS_PER_PROPERTY
    affordable = affordable_rows(balance_usd, rate_usd, floor_usd=floor_usd)
    return OrderedDict((
        ("rows", rows),
        ("attempts_expected", expected),
        ("attempts_hard_ceiling", ceiling),
        ("usd_per_attempt", rate_usd),
        ("cost_expected_usd", round(expected * rate_usd, 2)),
        ("cost_hard_ceiling_usd", round(ceiling * rate_usd, 2)),
        ("recommended_hard_cap_usd", round(ceiling * rate_usd, 2)),
        ("prepaid_balance_usd", balance_usd),
        ("operational_floor_usd", floor_usd),
        ("rows_the_balance_can_fund", affordable),
        ("balance_sufficient_for_all", affordable >= rows),
    ))


def render_json(document: Mapping) -> str:
    return json.dumps(document, indent=1, ensure_ascii=False) + "\n"
