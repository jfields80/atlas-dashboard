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


# --------------------------------------------------------------------------- #
# Gate 3: given a report, what must happen NEXT?
# --------------------------------------------------------------------------- #
#
# Every one of these is an instruction to do more work, never a conclusion. A
# research report can tell us where to look and what a page appears to say; it
# can never close a hotel out. So the whole set is REVIEW-capped by
# construction: routing's MODEL_RESEARCH_NOT_OFFICIAL_EVIDENCE backstop fires on
# the provenance regardless of which action was recorded, and no value here is
# consulted when deciding READY.

# The report gave us prose but nothing retrievable yet -- someone must obtain
# the actual page before any of it counts.
RESEARCH_REPORT_REQUIRES_SOURCE_CAPTURE = "RESEARCH_REPORT_REQUIRES_SOURCE_CAPTURE"
# A plausible official URL was found. Next step is automatic retrieval.
OFFICIAL_SOURCE_LOCATED = "OFFICIAL_SOURCE_LOCATED"
# We found it and tried; the edge refused us (Akamai/Cloudflare 403 et al).
OFFICIAL_SOURCE_ACCESS_BLOCKED = "OFFICIAL_SOURCE_ACCESS_BLOCKED"
# Only a real browser will render it -- the operator-capture lane.
HUMAN_RENDER_CAPTURE_REQUIRED = "HUMAN_RENDER_CAPTURE_REQUIRED"
# No web path remains; the fact must come from the property itself.
DIRECT_CONTACT_REQUIRED = "DIRECT_CONTACT_REQUIRED"
# The search found no official page stating an applicable policy at all. This
# records ABSENCE OF FOUND EVIDENCE, never "this hotel has no pet policy".
NO_APPLICABLE_OFFICIAL_POLICY_FOUND = "NO_APPLICABLE_OFFICIAL_POLICY_FOUND"

RESEARCH_ACTIONS = frozenset({
    RESEARCH_REPORT_REQUIRES_SOURCE_CAPTURE, OFFICIAL_SOURCE_LOCATED,
    OFFICIAL_SOURCE_ACCESS_BLOCKED, HUMAN_RENDER_CAPTURE_REQUIRED,
    DIRECT_CONTACT_REQUIRED, NO_APPLICABLE_OFFICIAL_POLICY_FOUND,
})

# Actions a machine cannot discharge on its own.
HUMAN_ACTIONS = frozenset({HUMAN_RENDER_CAPTURE_REQUIRED, DIRECT_CONTACT_REQUIRED})

# Follow-up retrieval statuses (source_retrieval vocabulary) that mean the page
# was located but withheld by the far end, versus never found at all.
_BLOCKED_STATUSES = frozenset({"ACCESS_BLOCKED", "BROWSER_ACCESS_BLOCKED"})
_RENDER_STATUSES = frozenset({"RENDER_REQUIRED"})
_EXHAUSTED_STATUSES = frozenset({"NOT_FOUND", "ENTITY_MISMATCH",
                                 "UNSUPPORTED_CONTENT", "REJECTED_UNSAFE_URL"})


def classify_research_outcome(report, followup_retrieval: Optional[Mapping] = None) -> str:
    """The single next action implied by a report (+ any follow-up retrieval).

    Deterministic and total: every input maps to exactly one member of
    ``RESEARCH_ACTIONS``. ``followup_retrieval`` is the artifact from re-running
    ``retrieve-official-sources`` against a URL the report discovered; when it
    is absent, the report has not yet been acted on.

    Ordering matters. A blocked or render-only outcome is classified from the
    RETRIEVAL, not from the report, because the report's optimism about a URL
    says nothing about whether the edge will serve it to us.
    """
    if report is None or not getattr(report, "ok", False):
        # A failed or absent call is not a finding about the hotel. Saying
        # "no policy found" here would convert our own error into evidence.
        return RESEARCH_REPORT_REQUIRES_SOURCE_CAPTURE

    discovered = tuple(getattr(report, "discovered_urls", ()) or ())
    if not discovered:
        return NO_APPLICABLE_OFFICIAL_POLICY_FOUND

    if not followup_retrieval:
        return OFFICIAL_SOURCE_LOCATED

    status = str(followup_retrieval.get("status") or "")
    if followup_retrieval.get("ready_for_extraction") is True:
        # Retrieval succeeded on a URL the report found: the report did its job
        # and the evidence now comes from the fetched page, not from here.
        return OFFICIAL_SOURCE_LOCATED
    if status in _RENDER_STATUSES:
        return HUMAN_RENDER_CAPTURE_REQUIRED
    if status in _BLOCKED_STATUSES:
        return OFFICIAL_SOURCE_ACCESS_BLOCKED
    if status in _EXHAUSTED_STATUSES:
        return DIRECT_CONTACT_REQUIRED
    return RESEARCH_REPORT_REQUIRES_SOURCE_CAPTURE


def research_outcome_report(report, followup_retrieval: Optional[Mapping] = None) -> Dict:
    """Auditable record of the action and why it can never publish alone."""
    action = classify_research_outcome(report, followup_retrieval)
    return {
        "escalation_version": ESCALATION_VERSION,
        "action": action,
        "requires_human": action in HUMAN_ACTIONS,
        "max_route": "REVIEW",
        "publication_eligible": False,
        "rationale": "MODEL_RESEARCH_REPORT provenance is capped at REVIEW; this "
                     "action names the next evidence step, not a conclusion",
    }


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
