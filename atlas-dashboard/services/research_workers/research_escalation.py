"""PTF-WORKERS-004 -- research escalation ladder.

Web research is ESCALATION-ONLY. It may never run for a hotel whose official
page was already retrieved directly, because direct retrieval is both free and
strictly better evidence: ``source_retrieval`` returns a hashed page whose
quotes are verifiable verbatim, while a model report is prose that has to be
withheld to REVIEW no matter how good it looks.

This module is where that rule is ENFORCED rather than merely documented. A
comment saying "don't call this when retrieval works" is a rule that holds only
until somebody is in a hurry; ``require_escalation`` is a rule that holds
because the call raises.

Two separate decisions live here:

  1. **May we escalate at all?** Answered from the PRIOR retrieval outcome for
     the same hotel. No prior attempt, or a successful one, means no.
  2. **If so, to which provider?** Answered by cost: the least expensive tier
     that has been QUALIFIED against the evidence-quality gates. ``gpt-5.4`` is
     the final fallback, never the default.

On the ladder's ordering: tier cost is COMPUTED from operator-supplied prices,
not ranked by a hardcoded guess. Nothing in this file asserts that one model is
cheaper than another -- that would be an unverifiable claim baked into routing,
and the whole point of the ladder is to spend the least real money.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping, Optional, Sequence, Tuple

from services.research_workers.providers import SpendingAirlockError

ESCALATION_VERSION = "ptf-workers-004-escalation/1.0.0"


class EscalationBlocked(SpendingAirlockError):
    """Raised when web research is requested but is not the permitted next step.

    Subclasses SpendingAirlockError deliberately: refusing to escalate IS a
    spend refusal, and the CLI's existing airlock handling already reports it
    correctly and exits non-zero.
    """


# --------------------------------------------------------------------------- #
# Gate 1: has direct retrieval actually failed?
# --------------------------------------------------------------------------- #

def escalation_permitted(retrieval: Optional[Mapping], *,
                         listing_key: str = "") -> Tuple[bool, str]:
    """(permitted, reason) for ONE hotel, from its retrieval artifact.

    ``retrieval`` is the dict written by ``retrieve-official-sources``
    (``RetrievalOutcome.to_dict()``). Reading the persisted artifact rather than
    re-deriving the decision means the escalation is justified by evidence that
    already exists on disk and can be audited afterwards.
    """
    if not retrieval:
        return (False, "no_direct_retrieval_attempted")

    got_key = str(retrieval.get("listing_key") or "")
    if listing_key and got_key and got_key != listing_key:
        # Escalating hotel A on hotel B's failed retrieval would be a silent
        # cross-property authorization. Refuse rather than assume.
        return (False, "retrieval_artifact_is_for_a_different_hotel:%s" % got_key)

    if retrieval.get("ready_for_extraction") is True:
        return (False, "direct_retrieval_succeeded")

    status = str(retrieval.get("status") or "")
    if status == "RETRIEVED" and retrieval.get("policy_applicable") is True:
        # Defensive: ready_for_extraction is the authority, but if an older
        # artifact lacks the field, these two together mean the same thing.
        return (False, "direct_retrieval_succeeded")

    reason = str(retrieval.get("failure_reason") or "") or status or "unknown"
    if status == "RETRIEVED":
        # Fetched, but not applicable to THIS property (directory page, or a
        # brand policy that is not universal). Retrieval genuinely did not
        # recover usable evidence, so escalation is legitimate.
        return (True, "retrieved_but_not_applicable:%s" % reason)
    return (True, "direct_retrieval_failed:%s" % reason)


def require_escalation(retrieval: Optional[Mapping], *, listing_key: str = "") -> str:
    """Return the escalation reason, or raise. The only way in."""
    permitted, reason = escalation_permitted(retrieval, listing_key=listing_key)
    if not permitted:
        raise EscalationBlocked(
            "web research is escalation-only and was refused (%s). Direct official "
            "retrieval is free and yields stronger evidence -- run "
            "retrieve-official-sources first and escalate only on its failure." % reason)
    return reason


# --------------------------------------------------------------------------- #
# Gate 2: which provider, given it must be the cheapest that actually works?
# --------------------------------------------------------------------------- #

QUALIFIED = "QUALIFIED"
PENDING_BENCHMARK = "PENDING_BENCHMARK"
DISQUALIFIED = "DISQUALIFIED"


@dataclass(frozen=True)
class ProviderTier:
    """One rung. ``qualification`` is an empirical claim about whether this tier
    can recover valid official evidence, and only a benchmark may set it."""

    key: str
    model: str
    qualification: str
    note: str = ""

    @property
    def selectable(self) -> bool:
        return self.qualification == QUALIFIED


# The ladder. Cheaper-looking models sit ABOVE gpt-5.4 in intent, but none of
# them may be selected until a benchmark has qualified it against the same
# evidence-quality gates the flagship passed. Until then the router honestly
# falls through to the one tier that has been approved.
TIER_MINI = ProviderTier(
    key="web_research_mini", model="gpt-5.4-mini", qualification=PENDING_BENCHMARK,
    note="expected cheapest web-research tier; NOT yet benchmarked for evidence quality")
TIER_SEARCH_API = ProviderTier(
    key="web_research_search_api", model="gpt-5-search-api", qualification=PENDING_BENCHMARK,
    note="search-specialised model available on this project; NOT yet benchmarked")
TIER_FLAGSHIP = ProviderTier(
    key="web_research_flagship", model="gpt-5.4", qualification=QUALIFIED,
    note="final research fallback -- approved for the one-hotel proof, never the default")

PROVIDER_LADDER: Tuple[ProviderTier, ...] = (TIER_MINI, TIER_SEARCH_API, TIER_FLAGSHIP)

# Named so the deferred work is visible in code rather than only in a report.
PENDING_BENCHMARK_TIERS = tuple(t for t in PROVIDER_LADDER
                                if t.qualification == PENDING_BENCHMARK)


def select_research_tier(*, pricing_by_tier: Mapping[str, object],
                         caps, ladder: Sequence[ProviderTier] = PROVIDER_LADDER
                         ) -> Tuple[ProviderTier, float]:
    """The least expensive QUALIFIED tier, by COMPUTED worst-case cost.

    ``pricing_by_tier`` maps a tier key to a ``WebResearchPricing``. A qualified
    tier with no supplied price is skipped rather than guessed at -- consistent
    with ``pricing.py``: an unknown price is reported, never invented.

    Returns (tier, exact max cost). Raises if nothing is selectable, which is
    the correct outcome when every cheap tier is still unbenchmarked and the
    operator has not priced the fallback.
    """
    from services.research_workers.web_research import exact_max_cost_usd

    priced: list = []
    for tier in ladder:
        if not tier.selectable:
            continue
        pricing = pricing_by_tier.get(tier.key)
        if pricing is None:
            continue
        priced.append((exact_max_cost_usd(caps, pricing), tier))
    if not priced:
        raise EscalationBlocked(
            "no qualified, priced research tier is available. Qualified tiers: %s; "
            "pending benchmark: %s"
            % ([t.key for t in ladder if t.selectable] or "(none)",
               [t.key for t in ladder if t.qualification == PENDING_BENCHMARK] or "(none)"))
    # Ties break on tier key so selection is deterministic.
    priced.sort(key=lambda pair: (pair[0], pair[1].key))
    cost, tier = priced[0]
    return tier, cost


def ladder_report() -> Dict:
    """Auditable snapshot of the ladder for operator output."""
    return {
        "escalation_version": ESCALATION_VERSION,
        "policy": "escalation_only; cheapest qualified tier wins; gpt-5.4 is the "
                  "final fallback, never the default hotel worker",
        "tiers": [{"key": t.key, "model": t.model, "qualification": t.qualification,
                   "selectable": t.selectable, "note": t.note} for t in PROVIDER_LADDER],
        "pending_benchmark": [t.model for t in PENDING_BENCHMARK_TIERS],
    }
