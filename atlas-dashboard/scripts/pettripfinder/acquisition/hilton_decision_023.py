"""PTF-HILTON-ACQUISITION-DECISION-023 -- which lane should Hilton take.

Hilton is the last unresolved production lane. It leads with the Bright Data
Browser API, which is the most expensive provider in the table, and the only
evidence against Firecrawl on this brand is PTF-FIRECRAWL-HARD-LANES-003 --
a small sample, taken before reusable source selection, canonical locator
persistence, reader hardening and failure attribution existed.

WHY THAT RESULT IS RE-TESTED RATHER THAN REUSED
-----------------------------------------------
The same reason Marriott's was in 020: "the provider failed" and "the page had
nothing to find" produce the same summary line and share nothing in a fix.
Seven things are told apart before a provider is named, and every failure is
charged to exactly one:

    source quality, provider access, identity, policy location, reader
    interpretation, genuine absence, provider limitation

``FIRECRAWL_ACCESS_FAILURE`` is reserved for a page that did not arrive.

WHAT THE ALREADY-CAPTURED HILTON PAGES ESTABLISH, OFFLINE
---------------------------------------------------------
Fifteen Hilton-family properties were acquired by the router run, and every one
of them was read by ``generic_signal_walk`` rather than by the ``hilton_pet_panel``
brand container. That is NOT a Marriott-style blind spot. The
``hilton_competing`` reader exists precisely so the brand container COMPETES
with the generic walk instead of pre-empting it, and PTF-ACQUISITION-BRAND-
REPAIR-003 made it that way after a pre-empting container made the brand worse.
The generic walk winning is the design working.

Those captures also show what a Hilton policy surface looks like:

    Pets allowed Yes Deposit Yes. $75.00 Non-refundable Fee Max weight 75 lbs
    Max size Large

a labelled table, rendered into the property page.

THE REMAINING ELEVEN ARE A DIFFERENT HALF OF THE FAMILY
--------------------------------------------------------
The fifteen already acquired are Hilton, DoubleTree, Embassy Suites, Hilton
Garden Inn and Hampton. The eleven left are the focused-service brands: Home2
Suites, Homewood Suites, Tru and Spark. They share one host and one URL form,
so sub-brand is the structural axis, exactly as it was for Marriott -- and
whether they share the TEMPLATE is a question only capture can answer, which is
what Phase 13 is for.

ROUTE OVERRIDES ARE IN MEMORY
-----------------------------
``routes.json`` is not written by this module. A benchmark that edits the
routing table before the decision is made cannot be evidence for the decision.
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import json
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import firecrawl_capture as FC       # noqa: E402
from scripts.pettripfinder.acquisition import marriott_decision_020 as D    # noqa: E402
from scripts.pettripfinder.acquisition import providers as PROVIDERS        # noqa: E402
from scripts.pettripfinder.acquisition import registry as REGISTRY          # noqa: E402
from scripts.pettripfinder.acquisition import router as ROUTER              # noqa: E402
from scripts.pettripfinder.acquisition import source_selection as SS        # noqa: E402
from scripts.pettripfinder.brightdata import client as CLIENT               # noqa: E402
from scripts.pettripfinder.brightdata import corpus as CORPUS               # noqa: E402
from scripts.pettripfinder.brightdata import cross_brand_pilot_002 as P2    # noqa: E402
from scripts.pettripfinder.brightdata import policy_locator as PL           # noqa: E402
from scripts.pettripfinder.brightdata import policy_surface as PS           # noqa: E402

WORK_ORDER = "PTF-HILTON-ACQUISITION-DECISION-023"
MARKET = "milwaukee-wi"
BRAND = "HILTON"

REPORTS = REPO / "launch_packages" / "pettripfinder" / "markets" / "reports"
DECISION_REPORT = REPORTS / "ptf_hilton_decision_023.json"
RUN_REPORT = REPORTS / "ptf_hilton_milwaukee_run_023.json"

DECISION_RUN_ID = "hilton-decision-023"
PRODUCTION_RUN_ID = "hilton-milwaukee-023"
RUN_ROOT = REPO / "data" / "acquisition"

EXPECTED_REMAINING = 11
DECISION_COHORT_MAX = 8
#: At most two per structural group, so every group is represented and no group
#: dominates. Four groups exist, so the cohort lands at seven -- under the cap,
#: and chosen by a rule rather than to hit a number.
PER_GROUP = 2

BILLABLE_ZONES = ("scraping_browser1", "mcp_unlocker", "cli_unlocker")

#: The Hilton container, for the record. It competes with the generic walk and
#: usually loses, which is the repaired behaviour and not a defect.
HILTON_BOUND_LOCATORS = frozenset({"hilton_pet_panel"})


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --------------------------------------------------------------------------- #
# Phase 1 -- the cohort, computed rather than listed.
# --------------------------------------------------------------------------- #

def remaining_cohort() -> List[Dict]:
    """Hilton properties Milwaukee has never touched.

    Touched means an acquisition attempt was journalled, by either run, which
    is the definition 022 pinned. Derived by subtraction so the number is a
    consequence of the record rather than a figure typed here.
    """
    queue = json.loads(D.QUEUE_PATH.read_text(encoding="utf-8-sig"))
    routable = [r for r in queue["items"] if not r["brand_excluded"]]
    touched = set(D._already_acquired())
    for row in json.loads(D.RUN_REPORT.read_text(encoding="utf-8-sig"))["rows"]:
        touched.add(row["identity_key"])
    rows = [r for r in routable
            if r["brand"] == BRAND and r["identity_key"] not in touched]
    return sorted(rows, key=lambda r: r["canonical_name"])


#: Hilton sub-brand, read from the property-page slug. Hilton's own slug, so
#: this is a mechanical read of the URL and not a judgement about the hotel.
_SUB_BRAND_PATTERNS: Tuple[Tuple[str, str], ...] = (
    ("home2-suites", "HOME2_SUITES"),
    ("homewood-suites", "HOMEWOOD_SUITES"),
    ("embassy-suites", "EMBASSY_SUITES"),
    ("doubletree", "DOUBLETREE"),
    ("hampton", "HAMPTON"),
    ("garden-inn", "HILTON_GARDEN_INN"),
    ("spark-", "SPARK"),
    ("tru-", "TRU"),
    ("canopy", "CANOPY"),
    ("curio", "CURIO"),
    ("tapestry", "TAPESTRY"),
)


def sub_brand_of(url: str) -> str:
    slug = (url or "").lower()
    for needle, name in _SUB_BRAND_PATTERNS:
        if needle in slug:
            return name
    return "HILTON_FULL_SERVICE"


def url_shape(url: str) -> Dict:
    match = re.match(r"^https?://([^/]+)(/.*)$", url or "")
    host = match.group(1) if match else ""
    path = match.group(2) if match else ""
    code = ""
    found = re.search(r"/hotels/([a-z0-9]{5,9})-", path)
    if found:
        code = found.group(1)
    return {"host": host,
            "path_form": re.sub(r"/hotels/[a-z0-9]{5,9}-[^/]*/?",
                                "/hotels/{code}-{slug}/", path),
            "property_code": code,
            "sub_brand": sub_brand_of(url)}


def structural_groups(rows: Sequence[Dict]) -> Dict[str, List[Dict]]:
    """Group by host, URL form and sub-brand at once.

    The key is the whole shape, so a property on a different host or path form
    becomes its own group rather than being absorbed into a sub-brand that does
    not describe it.
    """
    groups: Dict[str, List[Dict]] = {}
    for row in rows:
        shape = url_shape(row["official_url"])
        key = "%s|%s|%s" % (shape["host"], shape["path_form"],
                            shape["sub_brand"])
        groups.setdefault(key, []).append(row)
    return {k: sorted(v, key=lambda r: r["canonical_name"])
            for k, v in sorted(groups.items())}


def decision_cohort(rows: Sequence[Dict]) -> Tuple[List[Dict], List[Dict], Dict]:
    """Up to two per structural group, alphabetically, before any outcome.

    Every group is represented, which the work order requires, and the rule is
    fixed and outcome-blind, which is the property that matters: nothing here
    can prefer a property because it is likely to succeed.
    """
    groups = structural_groups(rows)
    chosen: List[Dict] = []
    for key in sorted(groups):
        chosen.extend(groups[key][:PER_GROUP])
    chosen = sorted(chosen, key=lambda r: r["canonical_name"])
    chosen_keys = {r["identity_key"] for r in chosen}
    held = [r for r in rows if r["identity_key"] not in chosen_keys]
    return chosen, held, {
        "selection_method": (
            "group by host + URL path form + Hilton sub-brand; take the %d "
            "alphabetically first canonical names in each group. Four groups "
            "exist, so the cohort is %d -- under the cap of %d, and every "
            "structural group is covered. Applied before any acquisition "
            "outcome was known."
            % (PER_GROUP, len(chosen), DECISION_COHORT_MAX)),
        "groups": {k: [r["canonical_name"] for r in v]
                   for k, v in groups.items()},
        "group_count": len(groups),
        "cohort_size": len(chosen),
        "within_cap": len(chosen) <= DECISION_COHORT_MAX,
    }


# --------------------------------------------------------------------------- #
# Phase 4 -- the source audit.
# --------------------------------------------------------------------------- #

SOURCE_READY = D.SOURCE_READY
BETTER_URL = D.BETTER_URL
SOURCE_AMBIGUOUS = D.SOURCE_AMBIGUOUS
NO_POLICY_SOURCE = D.NO_POLICY_SOURCE


def source_audit(row: Mapping) -> Dict:
    """What page this property's acquisition starts from, and whether it is
    the right one.

    Reads the source-selection seam rather than second-guessing it: the census
    URL stays authoritative and the discovered-policy overlay is a preference
    layered on top. A homepage that never carries a policy is a SOURCE failure
    and must not be charged to a provider.
    """
    selection = SS.select(row["identity_key"], row["official_url"],
                          market_id=MARKET)
    shape = url_shape(row["official_url"])
    selected = getattr(selection, "url", "") or row["official_url"]
    origin = getattr(selection, "origin", SS.FROM_CENSUS)

    problems: List[str] = []
    if not shape["property_code"]:
        problems.append("no Hilton property code in the URL, so the identity "
                        "gate has nothing to bind to")
    if shape["host"] != "www.hilton.com":
        problems.append("unexpected host %r for a Hilton property"
                        % shape["host"])

    if problems:
        classification = SOURCE_AMBIGUOUS
    elif origin == SS.FROM_DISCOVERY and selected != row["official_url"]:
        classification = BETTER_URL
    else:
        classification = SOURCE_READY

    return {
        "census_url": row["official_url"],
        "selected_url": selected,
        "selection_origin": origin,
        "route_url": getattr(selection, "route_url", "") or row["official_url"],
        "property_code": shape["property_code"],
        "sub_brand": shape["sub_brand"],
        "host": shape["host"],
        "path_form": shape["path_form"],
        "classification": classification,
        "problems": problems,
        "policy_surface_note": (
            "the fifteen Hilton-family properties already acquired carry a "
            "labelled pet-policy table rendered into the property page itself, "
            "so the census URL is the policy-bearing surface for this brand on "
            "the evidence available"),
    }


# --------------------------------------------------------------------------- #
# Phase 5 -- the in-memory route override.
# --------------------------------------------------------------------------- #

def registry_override(*, provider: str, fallbacks: Sequence[str] = (),
                      forbid: Sequence[str] = ()) -> Dict:
    """A copy of the production registry with the Hilton row replaced.

    In memory only. Every other brand and domain row is carried through
    untouched, so a decision test cannot re-route a lane it is not measuring.
    """
    registry = copy.deepcopy(REGISTRY.load())
    row = dict(registry["brands"][BRAND])
    row["provider"] = provider
    row["fallback_providers"] = list(fallbacks)
    row["forbidden_providers"] = list(forbid)
    row["why"] = ("in-memory override for %s; not written to routes.json"
                  % WORK_ORDER)
    registry["brands"][BRAND] = row
    return registry


def _record_for(row: Mapping) -> "CORPUS.BenchmarkRecord":
    """Identity only. Milwaukee has no committed policy authority, so there is
    nothing a populated benchmark could leak into a capture."""
    return CORPUS.BenchmarkRecord(
        identity_key=row["identity_key"], name=row["canonical_name"],
        market_id=MARKET, brand=row["brand"],
        bucket=CORPUS.bucket_of(row["brand"]), source_url=row["official_url"],
        pets_allowed=None, facts={}, quotes=(), withheld_fields={},
        service_animal_statement="", categories=frozenset(), origin="census")


# --------------------------------------------------------------------------- #
# Phase 6 -- the usable-policy bar.
# --------------------------------------------------------------------------- #

USABLE = D.USABLE
NOT_USABLE = D.NOT_USABLE
SUBSTANTIVE_FIELDS = D.SUBSTANTIVE_FIELDS

#: Service animals are a legal obligation, not a pet policy. A block that says
#: only this tells a guest with a dog nothing.
_SERVICE_ANIMAL_ONLY = re.compile(
    r"^(?:[^.]*\bservice\s+animals?\b[^.]*\.?\s*)+$", re.IGNORECASE)


def service_animal_only(block: str) -> bool:
    text = (block or "").strip()
    if not text or "service animal" not in text.lower():
        return False
    without = re.sub(r"[^.]*\bservice\s+animals?\b[^.]*\.?", "", text,
                     flags=re.IGNORECASE).strip()
    return len(without) < 20


def usable_policy(document, *, expected_code: str) -> Dict:
    """Whether this capture yielded property-bound, meaningful pet policy.

    Publication grade asks whether the EVIDENCE is sound. This asks the
    separate question the work order names: did we learn something about THIS
    property's pet policy, and did the reader represent it or withhold it
    honestly. An amenity chip, generic Hilton-family copy, a shell, or a
    service-animal sentence all fail it.
    """
    if document is None:
        return {"verdict": NOT_USABLE, "reason": "no document was acquired",
                "checks": {}}

    observation = dict(document.observation or {})
    extraction = dict(observation.get("extraction") or {})
    withheld = dict(document.withheld_fields or {})
    block = (document.policy_text or "").strip()
    signals = dict((document.identity or {}).get("signals") or {})
    code_on_page = (signals.get("property_code_on_page") or "").lower()
    substantive = sorted(set(extraction) & SUBSTANTIVE_FIELDS)
    refusal = D.states_a_refusal(block)
    substantive_or_refusal = bool(substantive) or refusal

    checks = {
        "identity_bound_to_this_property":
            bool(expected_code) and code_on_page == expected_code.lower(),
        "policy_block_present": bool(block),
        "block_is_not_a_shell": refusal or len(block) >= 40,
        "not_service_animal_only": not service_animal_only(block),
        "states_terms_or_a_refusal": substantive_or_refusal or bool(withheld),
        "reader_represented_or_withheld": substantive_or_refusal or bool(withheld),
        "not_a_bare_allowed_flag": substantive_or_refusal,
    }
    failed = sorted(k for k, v in checks.items() if not v)
    return {
        "verdict": USABLE if not failed else NOT_USABLE,
        "reason": ("property-bound refusal located and read" if refusal and not failed
                   else "property-bound policy located and read" if not failed
                   else "failed: %s" % ", ".join(failed)),
        "checks": checks,
        "states_a_refusal": refusal,
        "substantive_fields": substantive,
        "withheld_fields": sorted(withheld),
        "block_chars": len(block),
        "block_text": block,
        "policy_locator": document.policy_locator,
        "property_code_on_page": code_on_page,
        "rendered_html_path": document.rendered_html_path or "",
        "brand_locator_used": document.policy_locator in HILTON_BOUND_LOCATORS,
    }


# --------------------------------------------------------------------------- #
# Phase 7 -- one primary cause per failure.
# --------------------------------------------------------------------------- #

SOURCE_URL_FAILURE = D.SOURCE_URL_FAILURE
FIRECRAWL_ACCESS_FAILURE = D.FIRECRAWL_ACCESS_FAILURE
IDENTITY_FAILURE = D.IDENTITY_FAILURE
LOCATOR_FAILURE = D.LOCATOR_FAILURE
READER_FAILURE = D.READER_FAILURE
POLICY_NOT_PRESENT = D.POLICY_NOT_PRESENT
GENERIC_BRAND_ONLY = D.GENERIC_BRAND_ONLY
OTHER = D.OTHER


#: A non-Firecrawl lane that could not fetch the page. The Phase 7 taxonomy is
#: written for the Firecrawl test and names Firecrawl explicitly; charging a
#: Bright Data failure to FIRECRAWL_ACCESS_FAILURE would be a plainly false
#: label on a row where Firecrawl never ran.
PROVIDER_ACCESS_FAILURE = "PROVIDER_ACCESS_FAILURE"


def attribute_failure(*, source: Mapping, result, document,
                      usable: Mapping, provider: str = PROVIDERS.FIRECRAWL) -> Dict:
    """The single cause a failure is charged to.

    Ordered so the cheapest explanation is excluded first: a provider is only
    blamed once source, fetch, identity, locator and reader have each been
    cleared, and a page that arrived carrying no policy is never charged to the
    provider.

    ``provider`` names the lane that actually ran, so a control row is not
    labelled with the name of a provider it never used.
    """
    if source["classification"] in (SOURCE_AMBIGUOUS, NO_POLICY_SOURCE):
        return {"cause": SOURCE_URL_FAILURE,
                "why": "the source audit could not name a sound policy URL: %s"
                       % ("; ".join(source["problems"])
                          or source["classification"])}
    if document is None:
        access = (FIRECRAWL_ACCESS_FAILURE if provider == PROVIDERS.FIRECRAWL
                  else PROVIDER_ACCESS_FAILURE)
        return {"cause": access,
                "provider": provider,
                "why": "no document arrived on the %s lane; router failure=%r "
                       "stopped_because=%r"
                       % (provider, getattr(result, "failure", ""),
                          getattr(result, "escalation_stopped_because", ""))}

    checks = usable.get("checks") or {}
    if not checks.get("identity_bound_to_this_property", True):
        return {"cause": IDENTITY_FAILURE,
                "why": "the page arrived but its property code %r is not this "
                       "property's" % usable.get("property_code_on_page")}
    if not checks.get("policy_block_present"):
        return {"cause": POLICY_NOT_PRESENT,
                "why": "the page arrived and no pet-policy container was "
                       "located; an absence on the surface, not a fetch failure"}
    if not checks.get("not_service_animal_only"):
        return {"cause": GENERIC_BRAND_ONLY,
                "why": "the located block addresses service animals only, "
                       "which is a legal obligation and not a pet policy"}
    if not checks.get("block_is_not_a_shell"):
        return {"cause": GENERIC_BRAND_ONLY,
                "why": "a container was located but holds only a token (%d "
                       "chars)" % usable.get("block_chars", 0)}
    if not checks.get("not_a_bare_allowed_flag"):
        return {"cause": GENERIC_BRAND_ONLY,
                "why": "the located text carries no terms; a 'pet friendly' "
                       "claim is not a policy"}
    if not checks.get("reader_represented_or_withheld"):
        return {"cause": READER_FAILURE,
                "why": "a substantive block was located and the reader "
                       "returned neither a field nor an honest withholding"}
    return {"cause": OTHER, "why": "no earlier cause applied"}


# --------------------------------------------------------------------------- #
# Acquisition of one property through a given registry.
# --------------------------------------------------------------------------- #

async def acquire(row: Mapping, *, registry: Mapping, run_dir: Path,
                  run_id: str, source: Mapping) -> Dict:
    record = _record_for(row)
    target = P2.target_for(record)
    began = time.monotonic()
    result = await ROUTER.route_property(record, target, run_dir=run_dir,
                                         run_id=run_id, registry=registry,
                                         route_url=source["route_url"])
    document = result.document
    verdict = usable_policy(document, expected_code=source["property_code"])
    out = {
        "identity_key": row["identity_key"],
        "canonical_name": row["canonical_name"],
        "sub_brand": source["sub_brand"],
        "source_url": source["selected_url"],
        "source_classification": source["classification"],
        "attempts": len(result.attempts),
        "providers_tried": list(result.providers_tried),
        "provider_used": (result.attempts[-1].provider
                          if result.attempts else ""),
        "final_state": result.state,
        "acquisition_status": ("ACQUIRED" if document is not None
                               else "NOT_ACQUIRED"),
        "artifact_written": document is not None,
        "identity_confirmed": bool(
            (verdict.get("checks") or {}).get("identity_bound_to_this_property")),
        "policy_locator": (document.policy_locator if document else ""),
        "brand_locator_used": verdict.get("brand_locator_used", False),
        "policy_block_chars": verdict.get("block_chars", 0),
        "reader": (result.route or {}).get("reader", ""),
        "reader_fields": verdict.get("substantive_fields", []),
        "reader_withheld": verdict.get("withheld_fields", []),
        "publication_grade": result.state == "ACQUIRED_PUBLICATION_GRADE",
        "usable_policy": verdict["verdict"],
        "usable_policy_detail": verdict,
        "failure": result.failure,
        "failure_class": result.failure_class,
        "escalation_stopped_because": result.escalation_stopped_because,
        "elapsed_seconds": round(time.monotonic() - began, 3),
        "estimated_bytes": result.cost.estimated_bytes,
        "reported_credits": result.cost.reported_credits,
    }
    lane = (registry.get("brands", {}).get(BRAND, {}) or {}).get(
        "provider", PROVIDERS.FIRECRAWL)
    out["attribution"] = ({"cause": "", "why": ""}
                          if verdict["verdict"] == USABLE
                          else attribute_failure(source=source, result=result,
                                                 document=document,
                                                 usable=verdict, provider=lane))
    # Artifacts can survive a capture that failed after persisting them, so
    # "did a document reach the router" and "are there files on disk" are two
    # different questions and both are recorded.
    out["artifacts_on_disk"] = bool(
        (run_dir / P2.target_for(record).slug).is_dir()
        and list((run_dir / P2.target_for(record).slug).glob(
            "attempt-*/" + PL.BLOCK_ARTIFACT)))
    return out


# --------------------------------------------------------------------------- #
# Cost.
# --------------------------------------------------------------------------- #

def read_spend(label: str) -> Dict:
    zones: Dict[str, Optional[int]] = {}
    for zone in BILLABLE_ZONES:
        snap = CLIENT.read_usage("%s:%s" % (label, zone), zone=zone)
        zones[zone] = snap.cost_month_usd_minor
    try:
        credits = FC.credits_remaining()
    except Exception:                                            # noqa: BLE001
        credits = None
    return {"label": label, "read_at": _now(),
            "brightdata_zone_cost_month_usd_minor": zones,
            "firecrawl_credits_remaining": credits}


def spend_delta(before: Mapping, after: Mapping) -> Dict:
    """Bright Data in dollars, Firecrawl in credits, never summed."""
    zones: Dict[str, Optional[int]] = {}
    total: Optional[int] = 0
    for zone in BILLABLE_ZONES:
        a = before["brightdata_zone_cost_month_usd_minor"].get(zone)
        b = after["brightdata_zone_cost_month_usd_minor"].get(zone)
        if a is None or b is None:
            zones[zone], total = None, None
            continue
        zones[zone] = max(0, b - a)
        if total is not None:
            total += zones[zone]
    ca = before.get("firecrawl_credits_remaining")
    cb = after.get("firecrawl_credits_remaining")
    return {
        "brightdata_usd_minor_by_zone": zones,
        "brightdata_usd_minor_total": total,
        "brightdata_measurement_status": ("MEASURED" if total
                                          else "UNSETTLED_AT_READ_TIME"),
        "firecrawl_credits_consumed": ((ca - cb) if (ca is not None
                                                     and cb is not None) else None),
        "firecrawl_measurement_status": "MEASURED",
        "note": ("Firecrawl credits settle immediately and are measured. The "
                 "Bright Data zone meter lags (019A), so an unmoved meter is "
                 "unsettled rather than zero spend. The two are never summed: "
                 "the plan endpoint reports an allowance, not a unit price."),
    }


# --------------------------------------------------------------------------- #
# Phases 5, 8 and 9 -- the test, the control, the decision.
# --------------------------------------------------------------------------- #

APPROVE_FIRECRAWL = "APPROVE_FIRECRAWL"
APPROVE_WITH_LIMITATION = "APPROVE_FIRECRAWL_WITH_LIMITATION"
RETAIN_BROWSER = "RETAIN_BROWSER"
SOURCE_STRATEGY_REQUIRED = "SOURCE_STRATEGY_REQUIRED"

#: Causes a different provider could plausibly fix. An absent policy, a brand
#: flag or a reader gap follows the page to any lane.
PROVIDER_FIXABLE = (FIRECRAWL_ACCESS_FAILURE, IDENTITY_FAILURE)


def _subset_rule(rows: Sequence[Dict]) -> Dict:
    """Whether Firecrawl's successes and failures split on a STRUCTURAL line.

    A limitation route may only be recommended if the subset can be named by
    something the router can key on -- sub-brand here, since host and URL form
    do not vary. If successes and failures share a sub-brand, no rule exists
    and the honest answer is a brand-wide decision.
    """
    ok, bad = {}, {}
    for row in rows:
        bucket = ok if row["usable_policy"] == USABLE else bad
        bucket.setdefault(row["sub_brand"], []).append(row["canonical_name"])
    contested = sorted(set(ok) & set(bad))
    return {
        "sub_brands_succeeding": sorted(ok),
        "sub_brands_failing": sorted(bad),
        "contested_sub_brands": contested,
        "separable": bool(ok) and bool(bad) and not contested,
        "why": ("successes and failures fall on different sub-brands, so a "
                "sub-brand rule is expressible"
                if bool(ok) and bool(bad) and not contested else
                "no structural line separates success from failure"),
    }


def decide(firecrawl_rows: Sequence[Dict], control_rows: Sequence[Dict],
           sources: Sequence[Dict]) -> Dict:
    """The route verdict, from the measured rows only.

    Bad inputs are excluded first, because a provider cannot be judged on pages
    nobody should have asked for. Then the question is not "did Firecrawl fail
    anywhere" but "did the Browser API RECOVER anything Firecrawl lost": a
    failure neither lane can fix is not a reason to pay for the expensive one.
    """
    total = len(firecrawl_rows)
    bad_source = [s for s in sources
                  if s["classification"] in (SOURCE_AMBIGUOUS, NO_POLICY_SOURCE)]
    if total and len(bad_source) > total / 2:
        return {"decision": SOURCE_STRATEGY_REQUIRED,
                "why": "%d of %d subjects have no sound policy URL; provider "
                       "performance cannot be judged on those inputs"
                       % (len(bad_source), total)}

    usable = [r for r in firecrawl_rows if r["usable_policy"] == USABLE]
    acquired = [r for r in firecrawl_rows
                if r["acquisition_status"] == "ACQUIRED"]
    failures = [r for r in firecrawl_rows if r["usable_policy"] != USABLE]
    fixable = [r for r in failures
               if r["attribution"]["cause"] in PROVIDER_FIXABLE]
    recovered = [r for r in control_rows if r["usable_policy"] == USABLE]
    subset = _subset_rule(firecrawl_rows)

    if total and len(usable) == total:
        decision = APPROVE_FIRECRAWL
        why = ("Firecrawl produced usable property-bound policy on all %d "
               "decision subjects, across every Hilton structural group" % total)
    elif not fixable and acquired:
        decision = APPROVE_FIRECRAWL
        why = ("Firecrawl acquired every subject; the %d without usable policy "
               "failed for reasons that follow the page to any provider (%s)"
               % (len(failures), ", ".join(sorted({r["attribution"]["cause"]
                                                   for r in failures}))))
    elif not acquired and recovered:
        decision = RETAIN_BROWSER
        why = ("Firecrawl acquired 0 of %d subjects while the Browser API "
               "produced usable policy on %d; there is no Hilton subset on "
               "which the cheap lane works, so there is no limitation route to "
               "describe" % (total, len(recovered)))
    elif not acquired:
        decision = RETAIN_BROWSER
        why = ("Firecrawl acquired 0 of %d subjects; nothing measured here "
               "supports moving the brand off its working lane" % total)
    elif recovered and subset["separable"]:
        decision = APPROVE_WITH_LIMITATION
        why = ("Firecrawl works on %s and the Browser API recovered %d subject"
               "(s) on %s; the split is expressible as a sub-brand rule"
               % (", ".join(subset["sub_brands_succeeding"]), len(recovered),
                  ", ".join(subset["sub_brands_failing"])))
    elif recovered:
        decision = RETAIN_BROWSER
        why = ("the Browser API recovered %d subject(s) Firecrawl lost, but "
               "successes and failures share sub-brands (%s), so no structural "
               "rule can name the working subset and a brand-wide cheap lane "
               "would silently drop those properties"
               % (len(recovered), ", ".join(subset["contested_sub_brands"])))
    else:
        decision = APPROVE_FIRECRAWL
        why = ("Firecrawl lost %d subject(s) to provider-attributable causes "
               "and the Browser API recovered none of them, so the expensive "
               "lane buys nothing here" % len(fixable))

    return {
        "decision": decision, "why": why, "subjects": total,
        "firecrawl_acquired": len(acquired),
        "usable_policy_successes": len(usable),
        "publication_grade": sum(1 for r in firecrawl_rows
                                 if r["publication_grade"]),
        "failures": len(failures),
        "provider_attributable_failures": len(fixable),
        "browser_recoveries": len(recovered),
        "subset_rule": subset,
        "failure_causes": {c: sum(1 for r in failures
                                  if r["attribution"]["cause"] == c)
                           for c in sorted({r["attribution"]["cause"]
                                            for r in failures})},
    }


#: The Firecrawl phase's own output, written before the control runs.
#: The two phases are separable on purpose: the Firecrawl phase is slow and
#: free (failed scrapes are not charged) while the control is fast and costs
#: real money, and a run killed between them should not have to repeat both.
PARTIAL = REPORTS / "ptf_hilton_decision_023_firecrawl.json"

#: The control phase journals one row per property as it completes.
CONTROL_JOURNAL = (RUN_ROOT / (DECISION_RUN_ID + "-control")
                   / "control-journal.jsonl")


async def run_firecrawl_phase() -> Dict:
    """Phase 5 only. Writes its rows so the control can resume from them."""
    rows = remaining_cohort()
    if len(rows) != EXPECTED_REMAINING:
        raise AssertionError("Hilton cohort is %d, expected %d"
                             % (len(rows), EXPECTED_REMAINING))
    chosen, held, grouping = decision_cohort(rows)
    sources = [source_audit(r) for r in chosen]
    registry = registry_override(
        provider=PROVIDERS.FIRECRAWL, fallbacks=(),
        forbid=(PROVIDERS.BRIGHTDATA_BROWSER, PROVIDERS.BRIGHTDATA_WEB_UNLOCKER))
    run_dir = RUN_ROOT / DECISION_RUN_ID / DECISION_RUN_ID
    run_dir.mkdir(parents=True, exist_ok=True)

    before = read_spend("023:before")
    out: List[Dict] = []
    for row, source in zip(chosen, sources):
        out.append(await acquire(row, registry=registry, run_dir=run_dir,
                                 run_id=DECISION_RUN_ID, source=source))
    after = read_spend("023:after-firecrawl")
    doc = {
        "schema": "ptf-hilton-decision-firecrawl/1.0",
        "work_order": WORK_ORDER,
        "generated_at": _now(),
        "remaining_hilton": len(rows),
        "decision_cohort": [r["canonical_name"] for r in chosen],
        "held_for_production": [r["canonical_name"] for r in held],
        "grouping": grouping,
        "source_audit": sources,
        "firecrawl_rows": out,
        "cost": {"firecrawl_phase": spend_delta(before, after),
                 "readings": [before, after]},
    }
    PARTIAL.write_bytes((json.dumps(doc, indent=1, ensure_ascii=False)
                         + "\n").encode("utf-8"))
    return doc


async def run_control_phase(limit: Optional[int] = None) -> Dict:
    """Phases 8 and 9, resuming from the Firecrawl phase's persisted rows."""
    partial = json.loads(PARTIAL.read_text(encoding="utf-8-sig"))
    rows = remaining_cohort()
    by_name = {r["canonical_name"]: r for r in rows}
    sources = {s["property_code"]: s for s in partial["source_audit"]}
    source_by_name = dict(zip(partial["decision_cohort"],
                              partial["source_audit"]))

    registry = registry_override(provider=PROVIDERS.BRIGHTDATA_BROWSER,
                                 fallbacks=(), forbid=())
    control_dir = RUN_ROOT / (DECISION_RUN_ID + "-control") / DECISION_RUN_ID
    subjects = [r for r in partial["firecrawl_rows"]
                if r["usable_policy"] != USABLE
                and r["attribution"]["cause"] in PROVIDER_FIXABLE]
    if subjects:
        control_dir.mkdir(parents=True, exist_ok=True)

    # Journalled per property and resumed from the journal, so a run that is
    # killed loses at most the property in flight. Long provider runs in this
    # environment have been interrupted repeatedly, and repeating a Browser API
    # capture that already succeeded spends money to learn nothing.
    journal = CONTROL_JOURNAL
    journal.parent.mkdir(parents=True, exist_ok=True)
    done: Dict[str, Dict] = {}
    if journal.is_file():
        for line in journal.read_text(encoding="utf-8").splitlines():
            if line.strip():
                entry = json.loads(line)
                done[entry["canonical_name"]] = entry

    before = read_spend("023:before-control")
    control_rows: List[Dict] = []
    for row in subjects:
        name = row["canonical_name"]
        if name in done:
            control_rows.append(done[name])
            continue
        if limit is not None and len(
                [r for r in control_rows if r["canonical_name"] not in done]) >= limit:
            break
        result = await acquire(
            by_name[name], registry=registry, run_dir=control_dir,
            run_id=DECISION_RUN_ID + "-control", source=source_by_name[name])
        with journal.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(result, ensure_ascii=False) + "\n")
        control_rows.append(result)
    after = read_spend("023:after-control")
    complete = len(control_rows) == len(subjects)

    return {
        "schema": "ptf-hilton-decision/1.0",
        "work_order": WORK_ORDER,
        "market": MARKET,
        "generated_at": _now(),
        "remaining_hilton": partial["remaining_hilton"],
        "cohort_assertion": "Hilton cohort == %d" % EXPECTED_REMAINING,
        "decision_cohort": partial["decision_cohort"],
        "held_for_production": partial["held_for_production"],
        "grouping": partial["grouping"],
        "source_audit": partial["source_audit"],
        "route_before": dict(REGISTRY.load()["brands"][BRAND]),
        "routes_json_written": False,
        "firecrawl_rows": partial["firecrawl_rows"],
        "browser_control_rows": control_rows,
        "control_note": ("the Browser API was invoked only on Firecrawl "
                         "failures a provider could plausibly fix; a page that "
                         "arrived and carried no policy is not one of those"),
        "control_complete": complete,
        "control_subjects": len(subjects),
        "verdict": (decide(partial["firecrawl_rows"], control_rows,
                           partial["source_audit"]) if complete else
                    {"decision": "PENDING_CONTROL",
                     "why": "the control has run %d of %d subjects; no verdict "
                            "is issued from a partial control"
                            % (len(control_rows), len(subjects))}),
        "cost": {
            "firecrawl_phase": partial["cost"]["firecrawl_phase"],
            "control_phase": spend_delta(before, after),
            "readings": partial["cost"]["readings"] + [before, after],
        },
        "authority_written": False,
        "published": False,
        "readers_changed": False,
    }


async def run_decision() -> Dict:
    rows = remaining_cohort()
    if len(rows) != EXPECTED_REMAINING:
        raise AssertionError("Hilton cohort is %d, expected %d"
                             % (len(rows), EXPECTED_REMAINING))
    chosen, held, grouping = decision_cohort(rows)
    sources = [source_audit(r) for r in chosen]

    firecrawl_registry = registry_override(
        provider=PROVIDERS.FIRECRAWL, fallbacks=(),
        forbid=(PROVIDERS.BRIGHTDATA_BROWSER, PROVIDERS.BRIGHTDATA_WEB_UNLOCKER))
    browser_registry = registry_override(
        provider=PROVIDERS.BRIGHTDATA_BROWSER, fallbacks=(), forbid=())

    spend_before = read_spend("023:before")
    run_dir = RUN_ROOT / DECISION_RUN_ID / DECISION_RUN_ID
    run_dir.mkdir(parents=True, exist_ok=True)

    firecrawl_rows: List[Dict] = []
    for row, source in zip(chosen, sources):
        firecrawl_rows.append(await acquire(
            row, registry=firecrawl_registry, run_dir=run_dir,
            run_id=DECISION_RUN_ID, source=source))
    spend_after_firecrawl = read_spend("023:after-firecrawl")

    control_subjects = [
        (row, source) for row, source, fc in zip(chosen, sources, firecrawl_rows)
        if fc["usable_policy"] != USABLE
        and fc["attribution"]["cause"] in PROVIDER_FIXABLE]
    control_rows: List[Dict] = []
    control_dir = RUN_ROOT / (DECISION_RUN_ID + "-control") / DECISION_RUN_ID
    if control_subjects:
        control_dir.mkdir(parents=True, exist_ok=True)
    for row, source in control_subjects:
        control_rows.append(await acquire(
            row, registry=browser_registry, run_dir=control_dir,
            run_id=DECISION_RUN_ID + "-control", source=source))
    spend_after_control = read_spend("023:after-control")

    return {
        "schema": "ptf-hilton-decision/1.0",
        "work_order": WORK_ORDER,
        "market": MARKET,
        "generated_at": _now(),
        "remaining_hilton": len(rows),
        "cohort_assertion": "Hilton cohort == %d" % EXPECTED_REMAINING,
        "decision_cohort": [r["canonical_name"] for r in chosen],
        "held_for_production": [r["canonical_name"] for r in held],
        "grouping": grouping,
        "source_audit": sources,
        "route_before": dict(REGISTRY.load()["brands"][BRAND]),
        "routes_json_written": False,
        "firecrawl_rows": firecrawl_rows,
        "browser_control_rows": control_rows,
        "control_note": ("the Browser API was invoked only on Firecrawl "
                         "failures a provider could plausibly fix; a page that "
                         "arrived and carried no policy is not one of those"),
        "verdict": decide(firecrawl_rows, control_rows, sources),
        "cost": {
            "firecrawl_phase": spend_delta(spend_before, spend_after_firecrawl),
            "control_phase": spend_delta(spend_after_firecrawl,
                                         spend_after_control),
            "readings": [spend_before, spend_after_firecrawl,
                         spend_after_control],
        },
        "authority_written": False,
        "published": False,
        "readers_changed": False,
    }


def summarise(doc: Mapping) -> str:
    lines = ["%s" % doc["work_order"],
             "remaining Hilton %d | cohort %d | held %d"
             % (doc["remaining_hilton"], len(doc["decision_cohort"]),
                len(doc["held_for_production"])), ""]
    for row in doc["firecrawl_rows"]:
        lines.append("%-50s %-16s %-8s %s"
                     % (row["canonical_name"][:50], row["sub_brand"],
                        "USABLE" if row["usable_policy"] == USABLE else "NO",
                        row["final_state"]))
        lines.append("     locator=%s block=%dch fields=%s"
                     % (row["policy_locator"] or "-",
                        row["policy_block_chars"], row["reader_fields"] or "-"))
        if row["attribution"]["cause"]:
            lines.append("     CAUSE %s -- %s"
                         % (row["attribution"]["cause"],
                            row["attribution"]["why"][:120]))
    if doc["browser_control_rows"]:
        lines += ["", "BROWSER CONTROL:"]
        for row in doc["browser_control_rows"]:
            lines.append("%-50s %-8s %s"
                         % (row["canonical_name"][:50],
                            "USABLE" if row["usable_policy"] == USABLE else "NO",
                            row["policy_locator"] or "-"))
    verdict = doc["verdict"]
    lines += ["", "DECISION: %s" % verdict["decision"], "  %s" % verdict["why"]]
    if "firecrawl_acquired" in verdict:
        lines.append(
            "  firecrawl acquired %d/%d, usable %d/%d, browser recoveries %d"
            % (verdict["firecrawl_acquired"], verdict["subjects"],
               verdict["usable_policy_successes"], verdict["subjects"],
               verdict["browser_recoveries"]))
    else:
        lines.append("  control %d of %d subjects done; no verdict from a "
                     "partial control"
                     % (len(doc["browser_control_rows"]),
                        doc.get("control_subjects", 0)))
    cost = doc["cost"]
    lines += ["", "firecrawl phase: %s credits | brightdata %s (%s)"
              % (cost["firecrawl_phase"]["firecrawl_credits_consumed"],
                 cost["firecrawl_phase"]["brightdata_usd_minor_total"],
                 cost["firecrawl_phase"]["brightdata_measurement_status"]),
              "control phase:   %s credits | brightdata %s (%s)"
              % (cost["control_phase"]["firecrawl_credits_consumed"],
                 cost["control_phase"]["brightdata_usd_minor_total"],
                 cost["control_phase"]["brightdata_measurement_status"])]
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--firecrawl-phase", action="store_true",
                        help="phase 5 only; writes its rows so the control "
                             "can resume without repeating it")
    parser.add_argument("--control-phase", action="store_true",
                        help="phases 8-9, resuming from the Firecrawl rows")
    parser.add_argument("--limit", type=int, default=None,
                        help="acquire at most N NEW control subjects this "
                             "invocation; already-journalled ones are reused")
    parser.add_argument("--run-production", action="store_true",
                        help="acquire the 11 remaining Hilton properties on "
                             "the live route; journalled and resumable")
    parser.add_argument("--decide", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args(argv)

    if args.plan_only:
        rows = remaining_cohort()
        chosen, held, grouping = decision_cohort(rows)
        print(json.dumps({"remaining": len(rows),
                          "assertion_holds": len(rows) == EXPECTED_REMAINING,
                          "grouping": grouping,
                          "decision_cohort": [r["canonical_name"] for r in chosen],
                          "held": [r["canonical_name"] for r in held],
                          "source_audit": [source_audit(r) for r in chosen]},
                         indent=1))
        return 0

    if args.firecrawl_phase:
        doc = asyncio.run(run_firecrawl_phase())
        for row in doc["firecrawl_rows"]:
            print("%-50s %-8s %-24s %s" % (
                row["canonical_name"][:50], row["acquisition_status"][:8],
                row["failure"] or "-", row["attribution"]["cause"] or ""))
        print("\ncredits: %s"
              % doc["cost"]["firecrawl_phase"]["firecrawl_credits_consumed"])
        print("partial: %s" % PARTIAL)
        return 0

    if args.control_phase:
        doc = asyncio.run(run_control_phase(limit=args.limit))
        print(summarise(doc))
        if args.write_report:
            DECISION_REPORT.write_bytes(
                (json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
                .encode("utf-8"))
            print("\nreport: %s" % DECISION_REPORT)
        return 0

    if args.run_production:
        doc = asyncio.run(run_production(limit=args.limit))
        for row in doc["rows"]:
            print("%-50s %-9s %-8s %s" % (
                row["canonical_name"][:50], row["acquisition_status"][:9],
                "USABLE" if row["usable_policy"] == USABLE else "NO",
                row["policy_locator"] or ""))
        a = doc["template_audit"]
        print()
        print("processed %d/%d complete=%s | acquired %d | usable %d | "
              "materially incomplete %d"
              % (doc["processed"], doc["subject_count"], doc["run_complete"],
                 doc["acquired"], doc["usable_policy_successes"],
                 a["materially_incomplete"]))
        print("held for review: %s" % (a["held_for_review"] or "none"))
        print("cost: brightdata %s (%s)"
              % (doc["cost"]["delta"]["brightdata_usd_minor_total"],
                 doc["cost"]["delta"]["brightdata_measurement_status"]))
        if args.write_report and doc["run_complete"]:
            RUN_REPORT.write_bytes(
                (json.dumps(doc, indent=1, ensure_ascii=False) + chr(10))
                .encode("utf-8"))
            print("report: %s" % RUN_REPORT)
        return 0

    if args.decide:
        doc = asyncio.run(run_decision())
        print(summarise(doc))
        if args.write_report:
            DECISION_REPORT.write_bytes(
                (json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
                .encode("utf-8"))
            print("\nreport: %s" % DECISION_REPORT)
        return 0
    parser.error("choose --plan-only or --decide")




# --------------------------------------------------------------------------- #
# Phase 12 -- the production run, on the approved route.
# --------------------------------------------------------------------------- #

PRODUCTION_JOURNAL = (RUN_ROOT / PRODUCTION_RUN_ID / "journal.jsonl")


async def run_production(limit: Optional[int] = None) -> Dict:
    """Acquire the eleven remaining Hilton properties on the live route.

    No override: the registry on disk decides the lane, which is the point of
    running this after the decision rather than during it. Journalled per
    property and resumed from the journal, so an interrupted run never repeats
    a Browser API capture that already succeeded.
    """
    rows = remaining_cohort()
    if len(rows) != EXPECTED_REMAINING:
        raise AssertionError("Hilton subject count is %d, expected %d"
                             % (len(rows), EXPECTED_REMAINING))

    run_dir = RUN_ROOT / PRODUCTION_RUN_ID / PRODUCTION_RUN_ID
    run_dir.mkdir(parents=True, exist_ok=True)
    PRODUCTION_JOURNAL.parent.mkdir(parents=True, exist_ok=True)

    done: Dict[str, Dict] = {}
    if PRODUCTION_JOURNAL.is_file():
        for line in PRODUCTION_JOURNAL.read_text(encoding="utf-8").splitlines():
            if line.strip():
                entry = json.loads(line)
                done[entry["canonical_name"]] = entry

    before = read_spend("023-run:before")
    out: List[Dict] = []
    fresh = 0
    for row in rows:
        name = row["canonical_name"]
        if name in done:
            out.append(done[name])
            continue
        if limit is not None and fresh >= limit:
            continue
        source = source_audit(row)
        try:
            result = await acquire(row, registry=REGISTRY.load(),
                                   run_dir=run_dir, run_id=PRODUCTION_RUN_ID,
                                   source=source)
        except Exception as exc:                                  # noqa: BLE001
            result = {"identity_key": row["identity_key"],
                      "canonical_name": name,
                      "sub_brand": source["sub_brand"],
                      "acquisition_status": "NOT_ACQUIRED",
                      "usable_policy": NOT_USABLE, "final_state": "EXCEPTION",
                      "policy_locator": "", "policy_block_chars": 0,
                      "usable_policy_detail": {},
                      "providers_tried": [], "provider_used": "", "attempts": 0,
                      "attribution": {"cause": OTHER, "why": repr(exc)[:300]}}
        with PRODUCTION_JOURNAL.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(result, ensure_ascii=False) + "\n")
        out.append(result)
        fresh += 1
    after = read_spend("023-run:after")

    complete = len(out) == len(rows)
    usable = [r for r in out if r["usable_policy"] == USABLE]
    acquired = [r for r in out if r["acquisition_status"] == "ACQUIRED"]
    unresolved = [r for r in out if r["usable_policy"] != USABLE]
    providers: Dict[str, int] = {}
    for r in acquired:
        providers[r.get("provider_used", "")] = \
            providers.get(r.get("provider_used", ""), 0) + 1
    causes: Dict[str, int] = {}
    for r in unresolved:
        cause = (r.get("attribution") or {}).get("cause") or OTHER
        causes[cause] = causes.get(cause, 0) + 1

    audit = template_audit(out)
    return {
        "schema": "ptf-hilton-run/1.0",
        "work_order": WORK_ORDER,
        "market": MARKET,
        "run_id": PRODUCTION_RUN_ID,
        "generated_at": _now(),
        "subject_count": len(rows),
        "subject_assertion_held": len(rows) == EXPECTED_REMAINING,
        "run_complete": complete,
        "processed": len(out),
        "route_used": dict(REGISTRY.load()["brands"][BRAND]),
        "acquired": len(acquired),
        "usable_policy_successes": len(usable),
        "publication_grade": sum(1 for r in out if r.get("publication_grade")),
        "unresolved": len(unresolved),
        "unresolved_causes": causes,
        "provider_mix": providers,
        "fallback_uses": sum(1 for r in out
                             if len(r.get("providers_tried") or []) > 1),
        "template_audit": audit,
        # Acquisition succeeding is not the record being right. Both numbers
        # are reported so neither can stand in for the other. A set difference
        # and not a subtraction: a record can be held AND not usable, and
        # subtracting the two counts would charge it twice.
        "usable_and_materially_complete": len(
            {r["canonical_name"] for r in usable}
            - set(audit["held_for_review"])),
        "cost": {"delta": spend_delta(before, after),
                 "readings": [before, after]},
        "authority_written": False,
        "published": False,
        "rows": out,
    }


# --------------------------------------------------------------------------- #
# Phase 13 -- the template audit.
# --------------------------------------------------------------------------- #

#: A tier: an amount tied to a night range. Hilton states these in free prose
#: under "Other pet information", in several spellings.
_TIER = re.compile(
    r"\$\s*(?P<amount>[\d,]+(?:\.\d{2})?)\s*(?:\(|/stay\s*(?:for\s*)?|\s+for\s+"
    r"(?:the\s+)?)?\s*(?P<range>\d+\s*[-+]\s*\d*\s*nights?|\d+\s*\+\s*nights?"
    r"|first\s+\w+\s+nights?|\d+\s*night)", re.IGNORECASE)

_ANY_AMOUNT = re.compile(r"\$\s*([\d,]+(?:\.\d{2})?)")

TIERED_FEE_UNDERSTATED = "TIERED_FEE_UNDERSTATED"
BRAND_CONTAINER_PREEMPTED = "BRAND_CONTAINER_PREEMPTED_THE_WALK"
#: The property publishes an affirmative flag and no terms. Not a defect in
#: anything of ours -- the surface says this much and no more.
THIN_SURFACE = "THIN_SURFACE_NO_TERMS_PUBLISHED"
COMPLETE = "COMPLETE"


def tiers_in(block: str) -> List[str]:
    """The night-banded amounts a Hilton block states, in the property's words."""
    return [m.group(0).strip() for m in _TIER.finditer(block or "")]


def refusal_in(block: str) -> bool:
    """A refusal is complete however short it is."""
    return D.states_a_refusal(block or "")


def _richer_candidate_exists(row: Mapping, block: str) -> bool:
    """Does the persisted document hold a policy candidate with more in it?

    Read from the artifact, never assumed. The static walk over the saved
    document is a different algorithm from the live DOM walk (019), so this is
    not a prediction of what the live walk would have chosen -- it is evidence
    about whether the PAGE carries more than the block we kept. That is the
    only question a pre-emption claim needs answered, and answering it from the
    bytes is what stops the claim being a guess.
    """
    path = (row.get("usable_policy_detail") or {}).get("rendered_html_path") or ""
    candidate = Path(path) if path else None
    if candidate is not None and not candidate.is_absolute():
        candidate = REPO / path
    if candidate is None or not candidate.is_file():
        return False
    from scripts.pettripfinder.brightdata import unlocker_capture as UC
    hit = UC.locate_policy_in_text(
        UC.html_to_text(candidate.read_text(encoding="utf-8", errors="replace")))
    if not hit.found:
        return False
    return (PS.policy_features(hit.text) > PS.policy_features(block)
            and len(MS_collapse(hit.text)) > len(MS_collapse(block)))


def MS_collapse(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "")).strip()


def audit_row(row: Mapping) -> Dict:
    """Whether an acquired Hilton record is materially complete.

    Acquisition succeeding is not the same as the record being right. Hilton
    states banded fees in prose -- "$50(1-4 nights),$125(5+ nights)" -- and the
    generic reader takes the labelled amount above it. Where the bands go
    higher than the asserted fee, the record understates what a stay costs,
    which is the same failure PTF-MARRIOTT-ACCORDION-LOCATOR-HARDENING-021
    ended for Marriott. That fix lives in ``marriott_surface`` and does NOT
    reach the generic reader this brand uses.

    Reported, and queued. Not fixed here: the generic reader serves every brand
    and several published markets, and changing it inside a Hilton routing work
    order would be a change nobody measured.
    """
    detail = dict(row.get("usable_policy_detail") or {})
    block = detail.get("block_text") or ""
    fields = set(detail.get("substantive_fields") or [])
    withheld = set(detail.get("withheld_fields") or [])
    tiers = tiers_in(block)
    amounts = [float(a.replace(",", "")) for a in _ANY_AMOUNT.findall(block)]
    asserted_fee = "pet_fee" in fields and "pet_fee" not in withheld

    issues: List[str] = []
    if tiers and asserted_fee:
        issues.append(TIERED_FEE_UNDERSTATED)

    # PRE-EMPTION IS A CLAIM ABOUT AN ALTERNATIVE, SO IT NEEDS ONE.
    # 023 charged this whenever the brand container matched and the block was
    # short, and that was wrong: it inferred a suppressed richer candidate
    # without ever looking for one. Spark by Hilton Milwaukee Airport was
    # flagged on that reasoning and its page publishes "Pets allowed Yes" and
    # nothing else -- the words "Max weight" and "Other pet information" appear
    # on it only inside a JavaScript label dictionary, and its own JSON payload
    # carries petMaxSize: null and petChargeRefundable: null.
    #
    # So a thin block from the brand container is only pre-emption when the
    # persisted document actually holds a richer candidate. Otherwise it is a
    # THIN SURFACE: the property said this much and no more, which is a fact
    # about the hotel and not a defect in the locator.
    thin = detail.get("block_chars", 0) < 40 and not refusal_in(block)
    if thin and row.get("policy_locator") in HILTON_BOUND_LOCATORS:
        richer = _richer_candidate_exists(row, block)
        issues.append(BRAND_CONTAINER_PREEMPTED if richer else THIN_SURFACE)
    elif thin:
        issues.append(THIN_SURFACE)

    return {
        "canonical_name": row["canonical_name"],
        "sub_brand": row.get("sub_brand", ""),
        "policy_locator": row.get("policy_locator", ""),
        "block_text": block,
        "tiers_stated": tiers,
        "amounts_stated": sorted(set(amounts)),
        "highest_amount_stated": max(amounts) if amounts else None,
        "asserted_pet_fee": asserted_fee,
        "withheld_fields": sorted(withheld),
        "issues": issues,
        "verdict": issues[0] if issues else COMPLETE,
        "why": ("the block states banded fees (%s) and the record asserts a "
                "single pet_fee; a longer stay costs more than the record says"
                % "; ".join(tiers) if TIERED_FEE_UNDERSTATED in issues else
                "the brand container returned a bare flag while the persisted "
                "document holds a richer candidate"
                if BRAND_CONTAINER_PREEMPTED in issues else
                "the property publishes an affirmative flag and no terms; the "
                "surface says this much and no more"
                if THIN_SURFACE in issues else
                "the record represents or withholds every term the block states"),
    }


def template_audit(rows: Sequence[Mapping]) -> Dict:
    findings = [audit_row(r) for r in rows
                if (r.get("usable_policy_detail") or {}).get("block_text")]
    held = [f for f in findings if f["issues"]]
    locators: Dict[str, int] = {}
    for row in rows:
        key = row.get("policy_locator") or "none"
        locators[key] = locators.get(key, 0) + 1
    return {
        "records_audited": len(findings),
        "locators_used": locators,
        "multiple_templates": len({k for k in locators if k != "none"}) > 1,
        "records_with_banded_fees": sum(1 for f in findings if f["tiers_stated"]),
        "materially_incomplete": len(held),
        "held_for_review": [f["canonical_name"] for f in held],
        "issue_counts": {
            issue: sum(1 for f in findings if issue in f["issues"])
            for issue in (TIERED_FEE_UNDERSTATED, BRAND_CONTAINER_PREEMPTED,
                          THIN_SURFACE)},
        "why_this_matters": (
            "A record that understates a pet fee is worse than one that is "
            "missing: it looks complete and a guest would act on it. None of "
            "these is published. The generic reader's banded-fee gap is the "
            "same defect 021 fixed inside marriott_surface, and fixing it for "
            "every brand is its own work order."),
        "findings": findings,
    }


__all__ = [
    "WORK_ORDER", "EXPECTED_REMAINING", "DECISION_COHORT_MAX", "PER_GROUP",
    "tiers_in", "audit_row", "template_audit", "TIERED_FEE_UNDERSTATED",
    "BRAND_CONTAINER_PREEMPTED", "THIN_SURFACE", "COMPLETE",
    "PROVIDER_ACCESS_FAILURE", "refusal_in",
    "remaining_cohort", "sub_brand_of", "url_shape", "structural_groups",
    "decision_cohort", "source_audit", "registry_override", "usable_policy",
    "attribute_failure", "acquire", "read_spend", "spend_delta",
    "service_animal_only", "HILTON_BOUND_LOCATORS",
    "SOURCE_READY", "BETTER_URL", "SOURCE_AMBIGUOUS", "NO_POLICY_SOURCE",
    "USABLE", "NOT_USABLE", "SOURCE_URL_FAILURE", "FIRECRAWL_ACCESS_FAILURE",
    "IDENTITY_FAILURE", "LOCATOR_FAILURE", "READER_FAILURE",
    "POLICY_NOT_PRESENT", "GENERIC_BRAND_ONLY", "OTHER",
]


if __name__ == "__main__":
    raise SystemExit(main())
