"""PTF-GENERIC-CHEAPEST-VALID-LANE-001 -- the cheapest lane that is PROVEN, not
the cheapest lane.

The question this answers
------------------------
A paid pass has two lanes that can actually acquire: ``brightdata_browser``,
which bills 16.0 US cents a property, and ``firecrawl``, which bills PLAN
CREDITS and draws no dollars at all. Sending everything to the browser is safe
and expensive. Sending everything to Firecrawl is cheap and, for most of this
corpus, unevidenced. Neither is a policy.

So the lane is chosen per SOURCE FAMILY, from what the market's own saved
acquisition artifacts already measured, and a family is QUALIFIED for a lane
only when that lane has been shown to produce publication-grade evidence for
it at a real sample size. Cost breaks ties between qualified lanes; it never
creates a qualification.

Why identity failures leave the denominator
-------------------------------------------
``IDENTITY_MISMATCH`` means the page served and is about a different hotel.
``market_paid_acquisition`` already calls that terminal because "no crawler
fixes a wrong URL" -- it is a ROUTING defect, and holding it against the lane
that faithfully fetched the URL it was given would disqualify a good lane for
somebody else's mistake. Choice reads 28 publication-grade of 37 Firecrawl
attempts (75.7%) with identity failures counted, and 28 of 30 (93.3%) without.
The second number is the one about Firecrawl.

Why POLICY_NOT_FOUND stays IN the denominator
----------------------------------------------
A page that served its content and was silent is a fact about the page, but a
richer renderer can still reveal a policy behind a tab or an accordion, so it
is a fair charge against a lane's ability to extract. It is NOT an escalation
trigger -- see ``may_escalate`` -- because the router's own rule is that a
refusal escalates and a silence does not.

The thresholds are derived, and they are conservative
------------------------------------------------------
``MIN_EFFECTIVE_ATTEMPTS`` = 20 and ``MIN_PUBLICATION_GRADE_RATE`` = 0.85. On
the committed corpus that qualifies exactly five (lane, family) pairs and
refuses everything else, including three families whose entire evidence is a
single attempt. A family with one lucky success must never become globally
qualified, and Milwaukee's bounded re-acquisition -- two properties, zero
publication-grade -- is exactly the sample size this refuses to learn from.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from scripts.pettripfinder.acquisition import providers as PROVIDERS
from scripts.pettripfinder.brightdata import outcomes as O

SCHEMA = "ptf-lane-qualification/1.0"

#: The lane a family falls back to when no cheaper lane is proven for it. It is
#: the SAFE default, not the preferred one.
DEFAULT_LANE = "brightdata_browser"

#: Lanes ordered cheapest-first by their own registry cost metadata. Firecrawl
#: bills plan credits and draws no dollars, so it sorts ahead of a lane that
#: bills 16.0 cents; the order is recomputed from the registry rather than
#: written down, so a repriced lane reorders itself.
CREDIT_BILLED = "PLAN_CREDITS"

#: Outcomes that do not justify a second, dearer purchase. Deliberately the
#: same set ``market_paid_acquisition`` already treats as terminal, because two
#: definitions of "answered" that can disagree is how a market pays twice.
#: VALID is answered; POLICY_NOT_FOUND is a silence and the router does not
#: escalate a silence; IDENTITY_MISMATCH is a routing defect no lane can fix.
NO_ESCALATION_OUTCOMES: Tuple[str, ...] = (O.VALID, O.POLICY_NOT_FOUND,
                                           O.IDENTITY_MISMATCH)

#: Failures that are about OUR ACCESS or about a page that did not render, and
#: that a browser lane may plausibly answer where a fetch lane could not.
ESCALATABLE_OUTCOMES: Tuple[str, ...] = (O.ACCESS_DENIED, O.UNHYDRATED,
                                         O.UNEXPECTED_PAGE, O.NAVIGATION_FAILED,
                                         O.BLANK_PAGE, O.CAPTURE_FAILED)

#: An attempt whose failure was classified IDENTITY is a routing defect and
#: leaves the lane's denominator.
IDENTITY_FAILURE_CLASS = "IDENTITY"

#: Recorded defect classes that disqualify a lane for a family outright,
#: whatever its rate: evidence that arrives systematically truncated or that
#: carries only an amenity list is not publication-grade and a high pass rate
#: over it would be measuring the wrong thing. No artifact in the committed
#: corpus records one; the check exists so that when a reader starts recording
#: them, the qualification notices without being rewritten.
DISQUALIFYING_DEFECTS = frozenset({"AMENITY_ONLY", "TRUNCATED", "TRUNCATION"})

MIN_EFFECTIVE_ATTEMPTS = 20
MIN_PUBLICATION_GRADE_RATE = 0.85


def _family(row: Mapping) -> str:
    return (row.get("family") or row.get("brand") or "").strip().upper()


def _is_identity_failure(row: Mapping) -> bool:
    return (row.get("outcome") == O.IDENTITY_MISMATCH
            or (row.get("failure_class") or "").strip().upper()
            == IDENTITY_FAILURE_CLASS)


def summarise(rows: Sequence[Mapping]) -> Dict[Tuple[str, str], Dict]:
    """``(provider, family) -> evidence``, over saved acquisition results.

    Every attempt is counted once. ``attempts`` is the raw sample size and is
    preserved, because a rate without its denominator is not evidence.
    """
    out: "OrderedDict[Tuple[str, str], Dict]" = OrderedDict()
    for row in rows:
        provider = (row.get("provider") or "").strip()
        family = _family(row)
        if not provider or not family:
            continue
        key = (provider, family)
        record = out.setdefault(key, OrderedDict((
            ("provider", provider), ("family", family),
            ("attempts", 0), ("identity_failures", 0),
            ("effective_attempts", 0), ("publication_grade", 0),
            ("outcomes", OrderedDict()), ("defects", OrderedDict()),
        )))
        record["attempts"] += 1
        outcome = row.get("outcome") or ""
        record["outcomes"][outcome] = record["outcomes"].get(outcome, 0) + 1
        defect = (row.get("defect_class") or "").strip().upper()
        if defect:
            record["defects"][defect] = record["defects"].get(defect, 0) + 1
        if _is_identity_failure(row):
            record["identity_failures"] += 1
            continue
        record["effective_attempts"] += 1
        if row.get("publication_grade"):
            record["publication_grade"] += 1
    for record in out.values():
        effective = record["effective_attempts"]
        record["publication_grade_rate"] = (
            round(record["publication_grade"] / effective, 4) if effective else 0.0)
    return out


def qualify(evidence: Mapping[Tuple[str, str], Mapping],
            *, available: Optional[Mapping[str, bool]] = None
            ) -> Dict[Tuple[str, str], Dict]:
    """``(provider, family) -> verdict``. Deterministic, and it says why."""
    verdicts: "OrderedDict[Tuple[str, str], Dict]" = OrderedDict()
    for key in sorted(evidence):
        record = evidence[key]
        provider, family = key
        effective = record["effective_attempts"]
        rate = record["publication_grade_rate"]
        defects = sorted(set(record["defects"]) & DISQUALIFYING_DEFECTS)
        if available is not None and not available.get(provider, False):
            ok, why = False, "the provider is not available in the registry"
        elif defects:
            ok, why = False, ("the lane records %s defects for this family; "
                              "systematically incomplete evidence is not "
                              "publication-grade" % ", ".join(defects))
        elif effective < MIN_EFFECTIVE_ATTEMPTS:
            ok, why = False, ("%d effective attempts is below the %d this "
                              "policy requires; one lucky success is not a "
                              "qualification"
                              % (effective, MIN_EFFECTIVE_ATTEMPTS))
        elif rate < MIN_PUBLICATION_GRADE_RATE:
            ok, why = False, ("%.1f%% publication-grade over %d effective "
                              "attempts is below the %.0f%% this policy "
                              "requires" % (rate * 100, effective,
                                            MIN_PUBLICATION_GRADE_RATE * 100))
        else:
            ok, why = True, ("%d of %d effective attempts publication-grade "
                             "(%.1f%%), identity failures excluded as routing "
                             "defects" % (record["publication_grade"],
                                          effective, rate * 100))
        verdicts[key] = OrderedDict((
            ("provider", provider), ("family", family),
            ("qualified", ok), ("why", why),
            ("attempts", record["attempts"]),
            ("effective_attempts", effective),
            ("publication_grade", record["publication_grade"]),
            ("publication_grade_rate", rate),
        ))
    return verdicts


def lane_costs() -> Dict[str, Dict]:
    """Each registered lane's own cost metadata. Never invented here."""
    out: "OrderedDict[str, Dict]" = OrderedDict()
    for provider_id in sorted(PROVIDERS.all_ids()):
        try:
            provider = PROVIDERS.get(provider_id)
            cost = provider.cost_metadata()
            health = provider.health_check()
        except Exception:
            continue
        usd = cost.usd_minor_per_property
        out[provider_id] = OrderedDict((
            ("usd_minor_per_property", usd),
            ("credit_billed", usd is None),
            ("available", bool(getattr(health, "available", False))),
        ))
    return out


def plan_lane(family: str, verdicts: Mapping[Tuple[str, str], Mapping],
              costs: Mapping[str, Mapping]) -> Dict:
    """The primary lane, its fallback, and why -- for one source family.

    Cheapest QUALIFIED lane wins. A credit-billed lane draws no dollars and so
    sorts ahead of any dollar lane; among dollar lanes the lower unit cost
    wins. When nothing is qualified the safe default lane takes it, and the
    row is marked ``browser_required`` with the reason.
    """
    family = (family or "").strip().upper()
    qualified = [p for (p, f), v in verdicts.items()
                 if f == family and v["qualified"]
                 and costs.get(p, {}).get("available")]

    def order(provider_id):
        cost = costs.get(provider_id, {})
        usd = cost.get("usd_minor_per_property")
        return (0, 0.0) if cost.get("credit_billed") else (1, float(usd or 0.0))

    qualified.sort(key=order)
    if qualified:
        primary = qualified[0]
        why = verdicts[(primary, family)]["why"]
    else:
        primary = DEFAULT_LANE
        why = ("no lane is qualified for family %r on the committed evidence, "
               "so the safe default lane takes it" % (family or "(unknown)"))

    browser_required = primary == DEFAULT_LANE
    fallback = "" if browser_required else DEFAULT_LANE
    return OrderedDict((
        ("family", family),
        ("primary_lane", primary),
        ("fallback_lane", fallback),
        ("browser_required", browser_required),
        ("qualification_reason", why),
        ("primary_credit_billed",
         bool(costs.get(primary, {}).get("credit_billed"))),
        ("primary_usd_minor",
         costs.get(primary, {}).get("usd_minor_per_property")),
        ("fallback_usd_minor",
         costs.get(fallback, {}).get("usd_minor_per_property") if fallback else None),
    ))


def may_escalate(outcome: str) -> Tuple[bool, str]:
    """May a Firecrawl-primary row buy ONE browser attempt on this outcome?"""
    if outcome in NO_ESCALATION_OUTCOMES:
        return (False, "%s is terminal: a second, dearer purchase would buy "
                       "the same answer" % outcome)
    if outcome in ESCALATABLE_OUTCOMES:
        return (True, "%s is a statement about our access or about a page that "
                      "did not render, which a browser lane may answer" % outcome)
    return (False, "%s is not on the approved escalation list" % (outcome or "(none)"))


def plan_cohort_lanes(cohort: Sequence[Mapping],
                      verdicts: Mapping[Tuple[str, str], Mapping],
                      costs: Mapping[str, Mapping]) -> List[Dict]:
    """One lane decision per cohort row. No row receives two primary lanes."""
    seen = set()
    out: List[Dict] = []
    for row in cohort:
        key = row.get("identity_key", "")
        if key in seen:
            continue
        seen.add(key)
        plan = plan_lane(_family(row), verdicts, costs)
        entry = OrderedDict((("identity_key", key),
                             ("canonical_name", row.get("canonical_name", "")),
                             ("current_lane", row.get("provider", ""))))
        entry.update(plan)
        out.append(entry)
    return out
