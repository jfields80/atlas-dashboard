# -*- coding: utf-8 -*-
"""PTF-GENERIC-EXACT-AUTHORIZED-COHORT-001 -- an authorisation is an allowlist, not a quota.

WHAT WENT WRONG WITHOUT THIS
-----------------------------
PTF-INDIANAPOLIS-TARGETED-POLICY-ACQUISITION-012 authorised 51 identities, at a
cap costed over those 51. The runner then derived its own eligible queue -- as
it should, because that is its job -- and the queue was 74: the 51, plus 24
census rows that already carried a URL and had simply never been attempted. The
cap that fitted 51 (651c worst case) did not fit 74 (1113c), so spending anyway
would have bought a set nobody costed and dropped ten rows on queue order.

Nothing was wrong with the runner. What was missing was a way to say WHICH
identities an authorisation covers.

WHAT THIS IS
------------
A named, hashed artifact that lists the exact identity keys a paid run may
touch, and a gate that intersects the runner's queue with it. Three properties
matter, and each of them is a rule about money:

    AN ALLOWLIST, NOT A QUOTA. If an authorised row is no longer payable --
    the ledger settled it, a prior attempt answered it -- the run gets smaller.
    It does NOT reach into the backlog for a replacement. A budget approved for
    51 named hotels is not a budget for "any 51 hotels".

    A CEILING, NOT A TARGET. The cap in the artifact bounds the run; a run may
    spend less and may not spend more.

    NEW ELIGIBILITY IS NOT AUTHORISED ELIGIBILITY. An identity that becomes
    routable after the authorisation was written is reported as
    UNAUTHORIZED_BACKLOG and left alone. It needs its own cost plan and its own
    approval, because nobody has priced it.

WHY A HASHED SET AND NOT A NAME FILTER
--------------------------------------
A substring or prefix filter is a rule about spelling, and the identity key is
not the property -- this codebase has already paid twice for one Hampton Inn
because a re-census renamed it. The artifact binds an explicit key set and a
sha256 over it, so a stale authorisation fails loudly instead of quietly
covering a cohort it was never written for.
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.acquisition import paid_attempt_ledger as PAL  # noqa: E402

SCHEMA = "ptf-authorized-cohort/1.0"
WHAT_THIS_IS = (
    "The exact identity keys one paid run is authorised to touch, with the cap "
    "that was approved over them. An allowlist and a ceiling: a row that is no "
    "longer payable shrinks the run rather than being replaced, and an "
    "identity that became eligible afterwards is left for its own approval."
)

#: The explicit state a row outside the authorisation carries. Named rather
#: than left blank so coverage and closure can account for it as a DECISION not
#: yet taken, never as work that failed or that the budget lost.
NOT_AUTHORIZED = "NOT_AUTHORIZED_THIS_WORK_ORDER"


class AuthorizedCohortError(ValueError):
    """The authorisation cannot be trusted, so no money moves."""


def fingerprint(keys: Sequence[str]) -> str:
    """Order-independent hash over an identity-key set.

    Deliberately the same construction ``cohort_cost_plan.cohort_fingerprint``
    uses, so an authorisation, a cost plan and a queue can all be compared with
    one another rather than each proving a different thing.
    """
    material = "\n".join(sorted(str(k) for k in keys))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def build(identity_keys: Sequence[str], *, market_id: str, work_order: str,
          run_id: str = "", cap_usd_minor: int = 0,
          plan_credit_cap: Optional[int] = None, cost_plan_path: str = "",
          cost_plan_fingerprint: str = "", generated_at: str = "",
          provenance: Optional[Mapping] = None) -> Dict:
    """The artifact. Refuses to describe a cohort it cannot describe honestly."""
    keys = [str(k) for k in identity_keys]
    duplicates = sorted(k for k, n in Counter(keys).items() if n > 1)
    if duplicates:
        raise AuthorizedCohortError(
            "an authorisation may not name the same identity twice -- a "
            "duplicate is either a clerical error or two different properties "
            "wearing one key, and both must be resolved before money moves: %s"
            % ", ".join(repr(d) for d in duplicates))
    if not keys:
        raise AuthorizedCohortError("an authorisation with no identities "
                                    "authorises nothing; say so explicitly "
                                    "rather than running an empty allowlist")
    canonical = sorted(set(keys))
    return OrderedDict((
        ("schema", SCHEMA), ("what_this_is", WHAT_THIS_IS),
        ("market_id", str(market_id)), ("work_order", str(work_order)),
        ("run_id", str(run_id)),
        ("authorization", OrderedDict((
            ("cap_usd_minor", int(cap_usd_minor)),
            ("plan_credit_cap", plan_credit_cap),
            ("means", "a ceiling and an allowlist: the run may spend less and "
                      "may not spend more, and may touch these identities and "
                      "no others"),
        ))),
        ("cost_plan", OrderedDict((
            ("path", str(cost_plan_path)),
            ("cohort_keys_sha256", str(cost_plan_fingerprint)),
        ))),
        ("cohort_count", len(canonical)),
        ("identity_keys", canonical),
        ("cohort_keys_sha256", fingerprint(canonical)),
        ("generated_at", str(generated_at)),
        ("provenance", OrderedDict(provenance or {})),
    ))


def load(path) -> Dict:
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    if document.get("schema") != SCHEMA:
        raise AuthorizedCohortError("not a %s document: %r"
                                    % (SCHEMA, document.get("schema")))
    return document


def validate(document: Mapping, *, market_id: str,
             cap_usd_minor: Optional[int] = None,
             plan_credit_cap: Optional[int] = None) -> Dict:
    """Every reason this authorisation might not describe this run.

    Checked rather than asked, and checked BEFORE the queue is touched: an
    authorisation for another market, or one whose key set no longer hashes to
    its own fingerprint, is a stale document and a stale document must not
    spend.
    """
    checks: List[Dict] = []

    def check(name, ok, detail):
        checks.append(OrderedDict((("check", name), ("ok", bool(ok)),
                                   ("detail", detail))))

    check("schema", document.get("schema") == SCHEMA,
          "schema %r" % document.get("schema"))
    check("market_matches_the_run",
          str(document.get("market_id")) == str(market_id),
          "authorisation names %r, the run is %r"
          % (document.get("market_id"), market_id))

    keys = list(document.get("identity_keys") or ())
    duplicates = sorted(k for k, n in Counter(keys).items() if n > 1)
    check("no_duplicate_identity", not duplicates,
          "duplicates: %s" % (", ".join(duplicates) or "none"))
    check("count_matches_the_list",
          int(document.get("cohort_count") or -1) == len(keys),
          "declared %s, listed %d" % (document.get("cohort_count"), len(keys)))
    recomputed = fingerprint(keys)
    check("fingerprint_matches_its_own_keys",
          str(document.get("cohort_keys_sha256")) == recomputed,
          "declared %s, recomputed %s"
          % (str(document.get("cohort_keys_sha256"))[:12], recomputed[:12]))

    authorised_cap = int((document.get("authorization") or {}).get(
        "cap_usd_minor") or 0)
    if cap_usd_minor is not None:
        check("run_cap_within_the_authorised_cap",
              int(cap_usd_minor) <= authorised_cap,
              "run cap %sc, authorised %sc" % (cap_usd_minor, authorised_cap))
    authorised_credits = (document.get("authorization") or {}).get("plan_credit_cap")
    if plan_credit_cap is not None and authorised_credits is not None:
        check("run_credit_cap_within_the_authorised_cap",
              int(plan_credit_cap) <= int(authorised_credits),
              "run credits %s, authorised %s"
              % (plan_credit_cap, authorised_credits))

    return OrderedDict((("ok", all(c["ok"] for c in checks)),
                        ("cohort_keys_sha256", recomputed),
                        ("checks", checks)))


def restrict(queue: Sequence[Mapping], document: Mapping, *,
             ledger: Optional[Mapping] = None,
             material_changes: Optional[Mapping[str, Mapping[str, str]]] = None
             ) -> Dict:
    """Intersect a runner's eligible queue with an authorisation.

    Returns the payable restricted cohort plus every row that did NOT make it,
    each under a named reason. Nothing here is silent: a row the ledger settles
    and a row nobody authorised are both absences, and telling them apart is
    the difference between "we already own that answer" and "nobody has priced
    that yet".
    """
    authorised = list(document.get("identity_keys") or ())
    allowed_set = set(authorised)
    in_queue = {str(row.get("identity_key") or ""): row for row in queue}

    allowed = [row for row in queue
               if str(row.get("identity_key") or "") in allowed_set]
    backlog = [row for row in queue
               if str(row.get("identity_key") or "") not in allowed_set]

    # Authorised but the runner did not offer it: already settled, no longer
    # routed, or named in an authorisation written against a different census.
    not_eligible = sorted(k for k in authorised if k not in in_queue)

    suppressed: List[Dict] = []
    payable = allowed
    if ledger is not None:
        payable, suppressed = PAL.suppress(allowed, ledger,
                                           material_changes=material_changes)

    return OrderedDict((
        ("authorised", len(authorised)),
        ("runner_queue", len(queue)),
        ("allowed_before_ledger", len(allowed)),
        ("payable", len(payable)),
        ("suppressed_by_paid_history", len(suppressed)),
        ("unauthorized_backlog", len(backlog)),
        ("authorised_but_not_eligible", not_eligible),
        ("cohort_keys_sha256", fingerprint(
            [str(r.get("identity_key") or "") for r in payable])),
        ("payable_rows", list(payable)),
        ("suppressed_rows", [OrderedDict((
            ("identity_key", r.get("identity_key")),
            ("decision", r.get("paid_history", {}).get("decision")),
            ("reason", r.get("paid_history", {}).get("reason")),
        )) for r in suppressed]),
        ("backlog_rows", [OrderedDict((
            ("identity_key", r.get("identity_key")),
            ("provider", r.get("provider")),
            ("state", NOT_AUTHORIZED),
            ("why", "eligible for acquisition, but outside the identity set "
                    "this work order authorised; it needs its own cost plan "
                    "and its own approval before any money reaches it"),
        )) for r in backlog]),
        ("no_substitution",
         "an authorised row that is no longer payable SHRINKS this run. No "
         "backlog identity was promoted to fill its place."),
    ))


def gate(queue: Sequence[Mapping], document: Mapping, *, market_id: str,
         cap_usd_minor: Optional[int] = None,
         plan_credit_cap: Optional[int] = None,
         ledger: Optional[Mapping] = None,
         material_changes: Optional[Mapping[str, Mapping[str, str]]] = None
         ) -> Tuple[List[Dict], Dict]:
    """``(payable_rows, report)``. Raises before spending if the authorisation
    cannot be trusted."""
    verdict = validate(document, market_id=market_id,
                       cap_usd_minor=cap_usd_minor,
                       plan_credit_cap=plan_credit_cap)
    if not verdict["ok"]:
        failed = [c for c in verdict["checks"] if not c["ok"]]
        raise AuthorizedCohortError(
            "the authorisation does not describe this run, so nothing is "
            "spent: %s" % "; ".join("%s (%s)" % (c["check"], c["detail"])
                                    for c in failed))
    outcome = restrict(queue, document, ledger=ledger,
                       material_changes=material_changes)
    report = OrderedDict((("validation", verdict),))
    report.update(outcome)
    return (list(outcome["payable_rows"]), report)
