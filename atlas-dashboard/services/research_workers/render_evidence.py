"""PTF-CAPTURE-004A -- when is "the page loaded fine" not the same as "we can
read the policy"?

``RENDER_REQUIRED`` used to mean one thing: the importer could not read the page
at all (``FETCH_STATUS_JAVASCRIPT_REQUIRED`` -- an empty shell). That is a
whole-page test, and it misses a real and different case.

Wyndham's La Quinta property pages return 200 with 420KB of HTML, EXACT_MATCH
identity, and the heading ``Pet &amp; Service Animal Policy`` sitting in the
static markup. What is NOT in the static markup is the policy itself: "Dogs
Allowed - 2 dogs max. 75lbs or less per pet. Fees - 25 USD per pet per night."
appears only after the page renders and an ordinary "Hotel Policies" control is
opened. Automated retrieval therefore succeeds and returns a document from
which the pet policy can never be extracted -- and, because the status was
``RETRIEVED``, nothing downstream was allowed to go and get it either.

This module classifies exactly that gap, and nothing wider.

WHY IT IS DELIBERATELY HARD TO SATISFY
--------------------------------------
``RENDER_REQUIRED`` is a CAPTURE_WORTHY status: it is a licence to put a human
and a browser on a hotel. Handed out loosely it would reroute pages that the
automated path handles perfectly well onto the manual path, turning clean
records into REVIEW. So every one of six conditions must hold, the decision is
made from EVIDENCE CHARACTERISTICS rather than from any domain list, and every
refusal names which condition failed.

There is no brand allowlist here on purpose. A rule keyed to "wyndhamhotels.com"
would be a bypass wearing a classifier's clothes: it would fire on a Wyndham
page that genuinely serves its policy statically, and it would never fire for
the next brand that behaves this way.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Tuple

#: The machine-readable reason recorded on a qualifying artifact.
POLICY_VALUES_REQUIRE_RENDERING = "policy_values_require_rendering"

#: Named refusals. Each says which condition failed, so a near-miss is
#: diagnosable without re-running the fetch.
NOT_SUCCESSFUL_RETRIEVAL = "not_a_successful_retrieval"
IDENTITY_INSUFFICIENT = "identity_insufficient_for_property"
NOT_PROPERTY_SCOPED = "not_a_property_scoped_page"
NO_STATIC_POLICY_LANDMARK = "no_static_policy_landmark"
STATIC_ALREADY_HAS_VALUES = "policy_values_already_in_static_html"
NO_RENDERED_EVIDENCE = "no_rendered_policy_values"
PAGE_IS_BLOCKED = "page_is_blocked_or_gated"
STATIC_SHELL_TOO_THIN = "static_page_is_an_empty_shell"

#: A landmark names a pet-policy SECTION. It is not the bare word "pets": a
#: page that merely mentions pets in marketing prose ("our pet-friendly hotel
#: is located off exit 15") has told us nothing about where a policy lives, and
#: treating that as a landmark would qualify half the web.
POLICY_LANDMARK_PHRASES = (
    "pet policy",
    "pet policies",
    "pet & service animal",
    "pet and service animal",
    "pet & service animal policy",
    "pet/service animal",
)

#: Structural landmarks: a class or id that names a pet-policy region. Wyndham
#: ships `class="policy-items pet-policy"` and `class="pet-policy-desc"` in the
#: static markup while the values themselves are absent.
POLICY_LANDMARK_TOKENS = (
    "pet-policy", "pet_policy", "petpolicy",
    "pet-policies", "pet_policies",
)

#: Markers that mean the page is gated rather than merely unrendered. Kept
#: local rather than imported from ``operator_capture`` -- that module imports
#: THIS package's ``source_retrieval``, and a cycle here would be paid for by
#: every importer of either.
_GATED_MARKERS = (
    "sign in to continue", "please sign in", "log in to continue",
    "create an account to continue", "verify you are human",
    "are you a robot", "access denied", "request blocked",
    "enable javascript and cookies to continue", "checking your browser",
)

#: Below this, the "static page" is a shell and the existing
#: JAVASCRIPT_REQUIRED path -- not this one -- is the honest classification.
MIN_STATIC_TEXT_CHARS = 2000

_MONEY = re.compile(
    r"(?:\$\s*\d[\d,]*(?:\.\d{2})?)"                     # $25, $25.00
    r"|(?:\b\d[\d,]*(?:\.\d{2})?\s*(?:usd|dollars?)\b)",  # 25 USD, 25 dollars
    re.I)


@dataclass(frozen=True)
class RenderVerdict:
    """Does this page qualify, and if not, which condition failed?"""
    qualifies: bool
    reason: str
    static_signals: Tuple[str, ...] = ()
    rendered_signals: Tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"qualifies": self.qualifies, "reason": self.reason,
                "static_signals": list(self.static_signals),
                "rendered_signals": list(self.rendered_signals)}


def has_policy_landmark(static_html: str) -> bool:
    """A pet-policy section is announced in the static markup."""
    h = (static_html or "").lower()
    # &amp; is how "Pet & Service Animal Policy" actually ships.
    h = h.replace("&amp;", "&")
    if any(p in h for p in POLICY_LANDMARK_PHRASES):
        return True
    return any(t in h for t in POLICY_LANDMARK_TOKENS)


def policy_value_signals(text: str) -> Tuple[str, ...]:
    """Which QUANTIFIED policy facts a text actually states.

    Deliberately not "does it mention pets": a value is a pet COUNT, a weight
    CEILING, or a money AMOUNT -- things with a number in them, which is what a
    published record is made of.

    Species is deliberately NOT a signal, and that is not an oversight. The La
    Quinta Dublin page carries the marketing line "you can bring your dog or
    cat along with our pet-friendly rooms" in its static HTML, which
    ``extract_species`` reads -- correctly -- as "dogs, cats". Counting that as
    a policy value made the classifier conclude the static page already carried
    the policy, when what it carried was an advertisement. A species claim with
    no quantity beside it cannot publish a record on its own and is exactly the
    kind of sentence brochures are made of, so it does not count as evidence
    either way here.
    """
    from scripts.pettripfinder.prose_facts import (
        extract_pet_count, extract_weight_limit,
    )
    t = text or ""
    found = []
    if extract_pet_count(t) is not None:
        found.append("pet_count")
    if extract_weight_limit(t) is not None:
        found.append("weight_limit")
    if _MONEY.search(t):
        found.append("money_amount")
    return tuple(found)


def looks_gated(text: str) -> bool:
    t = re.sub(r"\s+", " ", (text or "")).lower()
    return any(m in t for m in _GATED_MARKERS)


def classify_render_requirement(*, retrieval_succeeded: bool,
                                identity_sufficient: bool,
                                property_scoped: bool,
                                static_html: str,
                                static_text: str,
                                rendered_text: str) -> RenderVerdict:
    """The whole rule, in one pure function.

    All six conditions must hold. Order is chosen so the reason returned is the
    most informative one: gating and shells are reported as themselves rather
    than as "no landmark", because those cases already have correct
    classifications elsewhere and must keep them.
    """
    if not retrieval_succeeded:
        return RenderVerdict(False, NOT_SUCCESSFUL_RETRIEVAL)
    if looks_gated(static_text) or looks_gated(rendered_text):
        return RenderVerdict(False, PAGE_IS_BLOCKED)
    if len((static_text or "").strip()) < MIN_STATIC_TEXT_CHARS:
        return RenderVerdict(False, STATIC_SHELL_TOO_THIN)
    if not identity_sufficient:
        return RenderVerdict(False, IDENTITY_INSUFFICIENT)
    if not property_scoped:
        return RenderVerdict(False, NOT_PROPERTY_SCOPED)
    if not has_policy_landmark(static_html):
        return RenderVerdict(False, NO_STATIC_POLICY_LANDMARK)

    static_signals = policy_value_signals(static_text)
    rendered_signals = policy_value_signals(rendered_text)
    if static_signals:
        # The automated path can already read this. Sending it to a human would
        # be manufacturing work and downgrading a clean record to REVIEW.
        return RenderVerdict(False, STATIC_ALREADY_HAS_VALUES,
                             static_signals, rendered_signals)
    if not rendered_signals:
        # Nothing renders either. That is not "needs rendering" -- it is a page
        # that does not publish its policy, and claiming otherwise would send a
        # human to look at something that is not there.
        return RenderVerdict(False, NO_RENDERED_EVIDENCE,
                             static_signals, rendered_signals)

    return RenderVerdict(True, POLICY_VALUES_REQUIRE_RENDERING,
                         static_signals, rendered_signals)
