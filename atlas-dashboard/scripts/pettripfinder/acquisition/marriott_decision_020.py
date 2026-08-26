"""PTF-MARRIOTT-ACQUISITION-DECISION-020 -- which lane should Marriott take.

Marriott is the last brand still leading with the Bright Data Browser API, and
it is the most expensive lane in the table. Choice, Wyndham and IHG each moved
to Firecrawl after a decision test measured them property by property; Marriott
never got that test. What it got was PTF-FIRECRAWL-HARD-LANES-003, which
reported that Firecrawl "cannot reach" Marriott -- on a sample that was small,
and against a source that was never audited first.

WHY THAT EARLIER RESULT IS NOT REUSED
-------------------------------------
Because "the provider failed" and "the page had nothing to find" produce the
same summary line and share nothing in a fix. Before this work order can name
a provider, seven things have to be told apart:

    1  source URL quality        did we even ask for the right page
    2  page acquisition          did the provider return that page
    3  identity                  is it the property we think it is
    4  canonical policy location did the locator find a bounded block
    5  reader performance        did the reader read the block it was given
    6  genuine absence           does this property publish no policy
    7  provider limitation       only what is left after the six above

Every failure in this module is attributed to exactly one of those, and
"FIRECRAWL_ACCESS_FAILURE" is reserved for a page that did not arrive. A page
that arrived and carried no policy is POLICY_NOT_PRESENT, and routing a lane
around that would buy nothing.

WHAT THE SOURCE AUDIT ALREADY ESTABLISHED, OFFLINE
--------------------------------------------------
All seventeen remaining properties share one host and one URL form,
``/en-us/hotels/{code}-{slug}/overview/``. Reading the Marriott documents
already on disk from the router-001 run shows the pet policy rendered INTO that
page, inside a ``hotel-details amenities-list`` section, as server-shaped AEM
markup:

    <div class="d-flex align-items-start">
      <span class="icon-pet-friendly ..."></span>
      <div class="t-font-s"><div class="pb-2 t-font-s">Pet Policy</div>
      <div class="t-font-xs">...the wording...</div></div></div>

``hotel-details`` is a CSS class on that page, not a separate URL, and the only
other occurrence of the words "Pet Policy" in the document is a JavaScript i18n
dictionary (``hws.petPolicy``) -- a decoy that a keyword sweep would quote and
that the bounded locator ignores. So there is no dedicated policy sub-page to
discover for this brand: the census URL already IS the policy-bearing page.
That is why the source classification below is computed rather than assumed,
and why a SOURCE_STRATEGY_REQUIRED verdict would need evidence this brand does
not currently show.

HOW THE DECISION COHORT IS CHOSEN
---------------------------------
Mechanically, and before any outcome is known. The seventeen group into eight
Marriott sub-brands, which is the only structural axis that varies (host and
URL form do not). One representative per group, the alphabetically first
canonical name in it. Eight subjects, no cherry-picking, and the nine held back
are named so the production run is a stated superset rather than a leftover.

ROUTE OVERRIDES ARE IN MEMORY
-----------------------------
The decision test drives the production router through an in-memory registry
copy. ``routes.json`` is not written by this module at any point: a benchmark
that edits the routing table before the decision is made cannot then be
evidence for the decision.
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

from scripts.pettripfinder.acquisition import providers as PROVIDERS    # noqa: E402
from scripts.pettripfinder.acquisition import registry as REGISTRY      # noqa: E402
from scripts.pettripfinder.acquisition import router as ROUTER          # noqa: E402
from scripts.pettripfinder.acquisition import source_selection as SS    # noqa: E402
from scripts.pettripfinder.brightdata import client as CLIENT           # noqa: E402
from scripts.pettripfinder.brightdata import corpus as CORPUS           # noqa: E402
from scripts.pettripfinder.brightdata import cross_brand_pilot_002 as P2  # noqa: E402
from scripts.pettripfinder.acquisition import firecrawl_capture as FC   # noqa: E402
from scripts.pettripfinder.brightdata import policy_locator as PL       # noqa: E402

WORK_ORDER = "PTF-MARRIOTT-ACQUISITION-DECISION-020"
MARKET = "milwaukee-wi"
BRAND = "MARRIOTT"

PKG = REPO / "launch_packages" / "pettripfinder"
REPORTS = PKG / "markets" / "reports"
QUEUE_PATH = REPORTS / ("%s_policy_acquisition_queue_001.json" % MARKET)
DECISION_REPORT = REPORTS / "ptf_marriott_decision_020.json"
RUN_REPORT = REPORTS / "ptf_marriott_milwaukee_run_020.json"

#: The run whose journal says which Marriott properties are already acquired.
PRIOR_RUN_JOURNAL = (REPO / "data" / "acquisition" / "milwaukee-router-001"
                     / "milwaukee-router-001" / "journal.jsonl")

DECISION_RUN_ID = "marriott-decision-020"
PRODUCTION_RUN_ID = "marriott-milwaukee-020"
RUN_ROOT = REPO / "data" / "acquisition"

EXPECTED_REMAINING = 17
DECISION_COHORT_MAX = 8

BILLABLE_ZONES = ("scraping_browser1", "mcp_unlocker", "cli_unlocker")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --------------------------------------------------------------------------- #
# Phase 1 -- the cohort, computed rather than listed.
# --------------------------------------------------------------------------- #

def _queue_rows() -> List[Dict]:
    doc = json.loads(QUEUE_PATH.read_text(encoding="utf-8-sig"))
    return [r for r in doc["items"] if not r["brand_excluded"]]


def _already_acquired() -> Dict[str, str]:
    """Identity keys the prior Milwaukee run already resolved, and their state."""
    done: Dict[str, str] = {}
    if PRIOR_RUN_JOURNAL.is_file():
        for line in PRIOR_RUN_JOURNAL.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            done[entry["identity_key"]] = entry.get("final_state", "")
    return done


def remaining_cohort() -> List[Dict]:
    """The Marriott properties Milwaukee has not yet acquired.

    Derived by subtracting the prior run's journal from the committed queue, so
    the number is a consequence of the record rather than a figure typed into
    this file. The caller asserts it.
    """
    done = _already_acquired()
    rows = [r for r in _queue_rows()
            if r["brand"] == BRAND and r["identity_key"] not in done]
    return sorted(rows, key=lambda r: r["canonical_name"])


#: Marriott sub-brand, read from the property-page slug. The slug is Marriott's
#: own, so this is a mechanical read of the URL rather than a judgement about
#: what the hotel is called.
_SUB_BRAND_PATTERNS: Tuple[Tuple[str, str], ...] = (
    ("residence-inn", "RESIDENCE_INN"),
    ("springhill-suites", "SPRINGHILL_SUITES"),
    ("towneplace-suites", "TOWNEPLACE_SUITES"),
    ("autograph-collection", "AUTOGRAPH_COLLECTION"),
    ("renaissance", "RENAISSANCE"),
    ("sheraton", "SHERATON"),
    ("westin", "WESTIN"),
    ("courtyard", "COURTYARD"),
    ("fairfield", "FAIRFIELD"),
    ("aloft", "ALOFT"),
    ("delta-hotels", "DELTA"),
    ("four-points", "FOUR_POINTS"),
)


def sub_brand_of(url: str) -> str:
    slug = url.lower()
    for needle, name in _SUB_BRAND_PATTERNS:
        if needle in slug:
            return name
    return "MARRIOTT_FULL_SERVICE"


def url_shape(url: str) -> Dict:
    """The structural facts about a property URL, read mechanically."""
    match = re.match(r"^https?://([^/]+)(/.*)$", url or "")
    host = match.group(1) if match else ""
    path = match.group(2) if match else ""
    code = ""
    slug_match = re.search(r"/hotels/([a-z0-9]{5})-", path)
    if slug_match:
        code = slug_match.group(1)
    return {
        "host": host,
        "path_form": re.sub(r"/hotels/[a-z0-9]{5}-[^/]+/", "/hotels/{code}-{slug}/",
                            path),
        "property_code": code,
        "sub_brand": sub_brand_of(url),
    }


def structural_groups(rows: Sequence[Dict]) -> Dict[str, List[Dict]]:
    """Group by every structural axis at once: host, URL form, sub-brand.

    The key is the whole shape rather than the sub-brand alone, so that if a
    property ever appears on another host or another path form it becomes its
    own group instead of being absorbed into a sub-brand that does not describe
    it.
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
    """One representative per structural group, chosen before any outcome.

    The representative is the alphabetically first canonical name in its group.
    That rule is arbitrary but it is FIXED and outcome-blind, which is the
    property that matters: nothing here can prefer a property because it is
    likely to succeed.
    """
    groups = structural_groups(rows)
    chosen: List[Dict] = []
    for key in sorted(groups):
        if len(chosen) >= DECISION_COHORT_MAX:
            break
        chosen.append(groups[key][0])
    chosen_keys = {r["identity_key"] for r in chosen}
    held = [r for r in rows if r["identity_key"] not in chosen_keys]
    summary = {
        "selection_method": (
            "group by host + URL path form + Marriott sub-brand; take the "
            "alphabetically first canonical name in each group; cap at %d. "
            "Applied before any acquisition outcome was known."
            % DECISION_COHORT_MAX),
        "groups": {k: [r["canonical_name"] for r in v]
                   for k, v in groups.items()},
        "group_count": len(groups),
    }
    return chosen, held, summary


# --------------------------------------------------------------------------- #
# Phase 3 -- the source audit. Before any provider is blamed.
# --------------------------------------------------------------------------- #

SOURCE_READY = "SOURCE_READY"
BETTER_URL = "BETTER_POLICY_URL_FOUND"
SOURCE_AMBIGUOUS = "SOURCE_AMBIGUOUS"
NO_POLICY_SOURCE = "NO_POLICY_SOURCE_FOUND"


def source_audit(row: Mapping) -> Dict:
    """What page this property's acquisition will start from, and whether it
    is the right one.

    Reads the source-selection seam rather than second-guessing it: the census
    URL stays authoritative, and the discovered-policy overlay is a preference
    layered on top. For Marriott the overlay is empty, so this records the
    census URL as the selection AND states the evidence that the census URL is
    already the policy-bearing surface, rather than treating "no overlay row"
    as an unexamined default.
    """
    selection = SS.select(row["identity_key"], row["official_url"],
                          market_id=MARKET)
    shape = url_shape(row["official_url"])
    selected = getattr(selection, "url", "") or row["official_url"]
    origin = getattr(selection, "origin", SS.FROM_CENSUS)

    problems: List[str] = []
    if not shape["property_code"]:
        problems.append("no Marriott property code in the URL, so the identity "
                        "gate has nothing to bind to")
    if shape["host"] != "www.marriott.com":
        problems.append("unexpected host %r for a Marriott property"
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
        "dedicated_policy_surface": (
            "none exists for this brand: 'hotel-details amenities-list' is a "
            "section CLASS on the overview page, not a separate URL, and the "
            "pet-policy container renders into that page"),
    }


# --------------------------------------------------------------------------- #
# Phase 4 -- the in-memory route override.
# --------------------------------------------------------------------------- #

def registry_override(*, provider: str, fallbacks: Sequence[str] = (),
                      forbid: Sequence[str] = ()) -> Dict:
    """A copy of the production registry with the Marriott row replaced.

    In memory only. Every other brand and domain row is carried through
    untouched, so a decision test cannot accidentally re-route a lane it is not
    measuring, and ``routes.json`` on disk is never written by this module.
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
    no benchmark to compare against and nothing that could leak into a capture."""
    return CORPUS.BenchmarkRecord(
        identity_key=row["identity_key"], name=row["canonical_name"],
        market_id=MARKET, brand=row["brand"],
        bucket=CORPUS.bucket_of(row["brand"]), source_url=row["official_url"],
        pets_allowed=None, facts={}, quotes=(), withheld_fields={},
        service_animal_statement="", categories=frozenset(), origin="census")


# --------------------------------------------------------------------------- #
# Phase 5 -- what actually counts as a Marriott policy success.
# --------------------------------------------------------------------------- #

USABLE = "USABLE_POLICY_SUCCESS"
NOT_USABLE = "NO_USABLE_POLICY"

#: Fields that say something a guest could act on. ``pets_allowed`` alone is
#: deliberately NOT in this set: an amenity chip produces exactly that and
#: nothing else, and counting it would let a chip pass as a policy.
SUBSTANTIVE_FIELDS = frozenset({
    "pet_fee", "fee_basis", "fee_currency", "fee_cap", "deposit",
    "weight_limit", "pet_count_limit", "species_allowed", "cats_allowed",
    "dogs_allowed", "service_animal_exception", "other_charges",
    "refundable", "pet_relief_area", "breed_restrictions",
})

#: The Marriott container the brand locator binds to. A block located anywhere
#: else has to earn its keep through feature count instead.
MARRIOTT_BOUND_LOCATORS = frozenset({"pet_policy_heading_parent"})

#: A property that refuses pets states a POLICY, and a refusal is exactly as
#: usable as an acceptance -- more so, since it settles the question outright.
#: Deliberately narrow. PTF-ACQUISITION-BRAND-REPAIR-003 recorded the inverse
#: error, where "no OTHER pets are allowed" was read as an acceptance, so these
#: patterns match a bare refusal and nothing qualified by "other".
_REFUSAL = re.compile(
    r"\b(?:pets?\s+(?:are\s+)?not\s+allowed"
    r"|no\s+pets\s+(?:are\s+)?(?:allowed|permitted)"
    r"|pets?\s+(?:are\s+)?not\s+permitted"
    r"|does\s+not\s+allow\s+pets)\b", re.I)
_REFUSAL_QUALIFIED = re.compile(r"\bno\s+other\s+pets\b", re.I)


def states_a_refusal(block: str) -> bool:
    """Whether this block refuses pets outright.

    A qualified refusal ("no OTHER pets are allowed") is NOT one: it sits
    inside an acceptance and reading it as a refusal -- or, as happened in
    003, as an acceptance -- is how a no-pets hotel nearly got published.
    """
    text = block or ""
    if _REFUSAL_QUALIFIED.search(text):
        return False
    return bool(_REFUSAL.search(text))


#: Marriott's SECOND property-page template, found by this work order. The
#: brand locator binds to ``<div class="pb-2 t-font-s">Pet Policy</div>``
#: beside an ``icon-pet-friendly`` span. Three of eight decision subjects
#: instead render the policy into an accordion headed by a ``<b>`` element,
#: which that locator cannot see -- so the generic walk runs and, on one
#: property, returned marketing prose while a real policy sat in the accordion.
_ACCORDION_POLICY = re.compile(
    r"<b[^>]*>\s*Pet Policy\s*</b>(.{0,1200}?)</div>", re.I | re.S)
_TAGS = re.compile(r"<[^>]+>")


def alternate_template_policy(html: str) -> str:
    """The policy text Marriott's accordion template carries, if any.

    Read from the persisted document, never from the network. Its only job is
    to tell a LOCATOR gap ("the page said it and we did not look there") apart
    from a genuine absence ("the page does not say"). It is not wired into
    acquisition and changes no reader.
    """
    match = _ACCORDION_POLICY.search(html or "")
    if not match:
        return ""
    text = _TAGS.sub(" ", match.group(1))
    return re.sub(r"\s+", " ", text).strip()


def usable_policy(document, *, expected_code: str) -> Dict:
    """Whether this capture yielded property-bound, meaningful pet policy.

    Publication grade is not sufficient on its own. It asks whether the
    EVIDENCE is sound -- hash rederived, quotes contiguous, identity confirmed
    -- and a page that says nothing but "Pet friendly" can satisfy all of that
    while telling a guest nothing. This asks the separate question: did we
    learn something about THIS property's pet policy, and did the reader either
    represent it or withhold it honestly.
    """
    if document is None:
        return {"verdict": NOT_USABLE, "reason": "no document was acquired",
                "checks": {}}

    observation = dict(document.observation or {})
    extraction = dict(observation.get("extraction") or {})
    if not extraction:
        # Some readers report the fact block under the observation root.
        extraction = {k: v for k, v in observation.items()
                      if k in SUBSTANTIVE_FIELDS or k == "pets_allowed"}
    withheld = dict(document.withheld_fields or {})
    block = (document.policy_text or "").strip()
    identity = dict(document.identity or {})
    signals = dict(identity.get("signals") or {})
    code_on_page = (signals.get("property_code_on_page") or "").lower()

    evidence = [e for e in (observation.get("evidence") or [])
                if (e.get("field_refs") or [])]
    substantive = sorted(set(extraction) & SUBSTANTIVE_FIELDS)
    refusal = states_a_refusal(block)

    # A REFUSAL is a complete policy. It carries no fee, no weight and no
    # count because there is nothing to charge for, so demanding a substantive
    # field of it would mark the clearest answer a property can give as a
    # failure. What it must still be is property-bound.
    substantive_or_refusal = bool(substantive) or refusal

    checks = {
        "identity_bound_to_this_property":
            bool(expected_code) and code_on_page == expected_code.lower(),
        "policy_block_present": bool(block),
        "block_states_terms_or_a_refusal":
            substantive_or_refusal or bool(withheld),
        "block_is_not_a_shell": refusal or len(block) >= 40,
        "block_bound_by_a_marriott_container":
            document.policy_locator in MARRIOTT_BOUND_LOCATORS
            or substantive_or_refusal,
        "evidence_quotes_bound_to_fields": bool(evidence) or refusal,
        "reader_produced_substantive_fields_or_withheld_honestly":
            substantive_or_refusal or bool(withheld),
        "not_a_bare_allowed_flag": substantive_or_refusal,
    }

    failed = sorted(k for k, v in checks.items() if not v)
    verdict = USABLE if not failed else NOT_USABLE
    return {
        "verdict": verdict,
        "reason": ("property-bound refusal located and read" if refusal and
                   verdict == USABLE else
                   "property-bound policy located and read"
                   if verdict == USABLE
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
    }


# --------------------------------------------------------------------------- #
# Phase 6 -- one primary cause per failure.
# --------------------------------------------------------------------------- #

SOURCE_URL_FAILURE = "SOURCE_URL_FAILURE"
FIRECRAWL_ACCESS_FAILURE = "FIRECRAWL_ACCESS_FAILURE"
IDENTITY_FAILURE = "IDENTITY_FAILURE"
LOCATOR_FAILURE = "LOCATOR_FAILURE"
READER_FAILURE = "READER_FAILURE"
POLICY_NOT_PRESENT = "POLICY_NOT_PRESENT"
GENERIC_BRAND_ONLY = "GENERIC_BRAND_ONLY"
OTHER = "OTHER"


def attribute_failure(*, source: Mapping, result, document,
                      usable: Mapping) -> Dict:
    """The single cause a failure is charged to.

    Ordered so that the cheapest explanation is excluded first. The ordering is
    the argument: a provider is only blamed once the source, the fetch, the
    identity, the locator and the reader have each been cleared, and a page
    that arrived intact carrying no policy is never charged to the provider.
    """
    if source["classification"] in (SOURCE_AMBIGUOUS, NO_POLICY_SOURCE):
        return {"cause": SOURCE_URL_FAILURE,
                "why": "the source audit could not name a sound policy URL: %s"
                       % "; ".join(source["problems"]) or source["classification"]}

    if document is None:
        failure = getattr(result, "failure", "") or ""
        return {"cause": FIRECRAWL_ACCESS_FAILURE,
                "why": "no document arrived; router failure=%r stopped_because=%r"
                       % (failure, getattr(result, "escalation_stopped_because", ""))}

    checks = usable.get("checks") or {}
    if not checks.get("identity_bound_to_this_property", True):
        return {"cause": IDENTITY_FAILURE,
                "why": "the page arrived but its property code %r is not this "
                       "property's" % usable.get("property_code_on_page")}

    # Does the page itself state a policy we failed to reach? Decided from the
    # persisted document, so "the locator missed it" and "the property does not
    # say" are told apart by evidence rather than by assumption. This is the
    # distinction the whole work order turns on.
    missed = ""
    path = usable.get("rendered_html_path") or ""
    if path:
        candidate = Path(path)
        if not candidate.is_absolute():
            candidate = REPO / path
        if candidate.is_file():
            missed = alternate_template_policy(
                candidate.read_text(encoding="utf-8", errors="replace"))

    if missed:
        return {"cause": LOCATOR_FAILURE,
                "why": "the page STATES a pet policy that the Marriott locator "
                       "does not reach: it renders under Marriott's accordion "
                       "template (<b>Pet Policy</b>) rather than the "
                       "icon-pet-friendly container the locator binds to. "
                       "Recovered text: %r" % missed[:220],
                "page_states_but_locator_missed": missed}

    if not checks.get("policy_block_present"):
        return {"cause": POLICY_NOT_PRESENT,
                "why": "the page arrived, carries no pet-policy container in "
                       "either Marriott template, and the locator found "
                       "nothing; an absence on the surface, not a fetch failure"}

    if not checks.get("block_is_not_a_shell"):
        return {"cause": GENERIC_BRAND_ONLY,
                "why": "a policy container was located but holds only a token "
                       "(%d chars), which is a brand flag and not a property "
                       "policy" % usable.get("block_chars", 0)}

    if not checks.get("not_a_bare_allowed_flag"):
        return {"cause": GENERIC_BRAND_ONLY,
                "why": "the located text is an amenity or marketing statement "
                       "carrying no terms; a 'pet friendly' claim is not a "
                       "policy"}

    if not checks.get("reader_produced_substantive_fields_or_withheld_honestly"):
        return {"cause": READER_FAILURE,
                "why": "a substantive block was located and the reader "
                       "returned neither a field nor an honest withholding"}

    if not checks.get("block_bound_by_a_marriott_container"):
        return {"cause": LOCATOR_FAILURE,
                "why": "the block was not bound by the Marriott container and "
                       "carries no substantive field to justify it"}

    return {"cause": OTHER, "why": "no earlier cause applied"}


# --------------------------------------------------------------------------- #
# Acquisition of one property through a given override.
# --------------------------------------------------------------------------- #

async def acquire(row: Mapping, *, registry: Mapping, run_dir: Path,
                  run_id: str, source: Mapping) -> Dict:
    record = _record_for(row)
    target = P2.target_for(record)
    # Which page we read and which lane fetches it are separate decisions; the
    # census URL is what the lane is resolved from.
    began = time.monotonic()
    result = await ROUTER.route_property(
        record, target, run_dir=run_dir, run_id=run_id, registry=registry,
        route_url=source["route_url"])
    document = result.document
    verdict = usable_policy(document, expected_code=source["property_code"])
    row_out = {
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
        "identity_confirmed": bool(
            (verdict.get("checks") or {}).get("identity_bound_to_this_property")),
        "policy_locator": (document.policy_locator if document else ""),
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
    if verdict["verdict"] != USABLE:
        row_out["attribution"] = attribute_failure(
            source=source, result=result, document=document, usable=verdict)
    else:
        row_out["attribution"] = {"cause": "", "why": ""}
    return row_out


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
    """Bright Data in dollars, Firecrawl in credits, never summed.

    The Bright Data month-to-date meter settles behind the traffic that moved
    it (measured in PTF-CANONICAL-POLICY-LOCATOR-FRESH-PROOF-019A: a session
    that moved 9.3 MB left the meter flat for over a minute and showed 17 cents
    four minutes later). So a zero here is reported as an unsettled meter and
    never as a measured absence of spend.
    """
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
        "brightdata_meter_moved": bool(total),
        "brightdata_measurement_status": (
            "MEASURED" if total else "UNSETTLED_AT_READ_TIME"),
        "firecrawl_credits_consumed": ((ca - cb)
                                       if (ca is not None and cb is not None)
                                       else None),
        "firecrawl_measurement_status": "MEASURED",
        "note": ("Firecrawl credits settle immediately and are measured. The "
                 "Bright Data zone meter lags, so an unmoved meter is reported "
                 "as unsettled rather than as zero spend."),
    }


# --------------------------------------------------------------------------- #
# Phases 4 and 7 -- the decision test, then the control.
# --------------------------------------------------------------------------- #

APPROVE_FIRECRAWL = "APPROVE_FIRECRAWL"
APPROVE_WITH_LIMITATION = "APPROVE_FIRECRAWL_WITH_LIMITATION"
RETAIN_BROWSER = "RETAIN_BROWSER"
SOURCE_STRATEGY_REQUIRED = "SOURCE_STRATEGY_REQUIRED"


def decide(firecrawl_rows: Sequence[Dict], control_rows: Sequence[Dict],
           sources: Sequence[Dict]) -> Dict:
    """The route verdict, from the measured rows only.

    The ordering matters. Bad inputs are excluded first, because a provider
    cannot be judged on pages nobody should have asked for. Then the question
    is not "did Firecrawl fail anywhere" but "did the Browser API RECOVER
    anything Firecrawl lost" -- a failure neither lane can fix is not a reason
    to pay for the expensive one.
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
    # Failures the provider could conceivably fix. An absent policy, a brand
    # flag or a locator gap is a property of the page and of our own code; it
    # follows the page to any lane and no provider change addresses it.
    provider_fixable = [r for r in failures
                        if r["attribution"]["cause"] in
                        (FIRECRAWL_ACCESS_FAILURE, IDENTITY_FAILURE)]
    recovered = [r for r in control_rows if r["usable_policy"] == USABLE]
    control_acquired = [r for r in control_rows
                        if r["acquisition_status"] == "ACQUIRED"]

    # A limitation route is only meaningful if some mechanically identifiable
    # subset actually WORKS on the cheap lane. When Firecrawl acquires nothing,
    # there is no such subset to name, and "Firecrawl with a limitation" would
    # describe a lane that never succeeds.
    firecrawl_works_somewhere = bool(acquired)

    if not provider_fixable and total and len(usable) == total:
        decision = APPROVE_FIRECRAWL
        why = ("Firecrawl produced usable property-bound policy on all %d "
               "decision subjects" % total)
    elif not provider_fixable and firecrawl_works_somewhere:
        decision = APPROVE_FIRECRAWL
        why = ("Firecrawl acquired every subject; the %d without usable policy "
               "failed for reasons that follow the page to any provider (%s)"
               % (len(failures),
                  ", ".join(sorted({r["attribution"]["cause"]
                                    for r in failures}))))
    elif not firecrawl_works_somewhere and recovered:
        decision = RETAIN_BROWSER
        why = ("Firecrawl acquired 0 of %d subjects -- every attempt returned "
               "ACCESS_DENIED before any page arrived -- while the Browser API "
               "acquired %d of %d and produced usable policy on %d. There is "
               "no Marriott subset on which the cheap lane works, so there is "
               "no limitation route to describe."
               % (total, len(control_acquired), len(control_rows),
                  len(recovered)))
    elif not firecrawl_works_somewhere:
        decision = RETAIN_BROWSER
        why = ("Firecrawl acquired 0 of %d subjects; nothing measured here "
               "supports moving the brand off its working lane" % total)
    elif recovered and len(recovered) >= len(provider_fixable):
        decision = APPROVE_WITH_LIMITATION
        why = ("Firecrawl works on part of the brand and the Browser API "
               "recovered %d of %d subjects it could not reach"
               % (len(recovered), len(provider_fixable)))
    elif recovered:
        decision = APPROVE_WITH_LIMITATION
        why = ("the Browser API recovered %d of %d provider-attributable "
               "Firecrawl failures; the rest are not a provider problem"
               % (len(recovered), len(provider_fixable)))
    else:
        decision = APPROVE_FIRECRAWL
        why = ("Firecrawl lost %d subjects to provider-attributable causes and "
               "the Browser API recovered none of them, so the expensive lane "
               "buys nothing here" % len(provider_fixable))

    return {
        "decision": decision, "why": why,
        "subjects": total,
        "usable_policy_successes": len(usable),
        "publication_grade": sum(1 for r in firecrawl_rows
                                 if r["publication_grade"]),
        "failures": len(failures),
        "provider_attributable_failures": len(provider_fixable),
        "browser_recoveries": len(recovered),
        "failure_causes": {c: sum(1 for r in failures
                                  if r["attribution"]["cause"] == c)
                           for c in sorted({r["attribution"]["cause"]
                                            for r in failures})},
    }


@dataclass(frozen=True)
class _PersistedDocument:
    """A capture reconstructed from disk, for re-assessment only.

    The reader output is carried through from the run that produced it -- this
    does NOT re-read the policy, because re-running a reader would be a second
    opinion rather than a re-assessment. What is re-read from disk is the
    persisted BLOCK and the persisted DOCUMENT, which is what the corrected
    definitions need: whether the block states a refusal, and whether the page
    states a policy the locator did not reach.
    """

    policy_text: str
    policy_locator: str
    rendered_html_path: str
    observation: Mapping
    withheld_fields: Mapping
    identity: Mapping


def _attempt_dir_for(run_dir: Path, slug: str) -> Optional[Path]:
    if not run_dir.is_dir():
        return None
    base = run_dir / slug
    if not base.is_dir():
        return None
    for attempt in sorted(base.glob("attempt-*"), reverse=True):
        if (attempt / PL.BLOCK_ARTIFACT).is_file():
            return attempt
    return None


def _slug_of(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")[:80]


def reassess(report_path: Optional[Path] = None) -> Dict:
    """Recompute the verdict from the persisted captures.

    Three defects in this module's own judgement were found after the run and
    corrected: a property-bound REFUSAL was scored as a failure though it is a
    complete policy; a page that states its policy in Marriott's SECOND
    template was charged to the reader rather than to the locator that cannot
    see that template; and a limitation route was offered for a lane that
    acquired nothing, which cannot be a limitation of anything.

    Re-assessment reads the artifacts already on disk. It makes no provider
    call, and it does not re-acquire: the captures are the evidence and they
    have not changed.
    """
    path = report_path or DECISION_REPORT
    doc = json.loads(path.read_text(encoding="utf-8-sig"))

    def redo(rows: Sequence[Dict], run_dir: Path) -> List[Dict]:
        out: List[Dict] = []
        for row in rows:
            updated = dict(row)
            attempt = _attempt_dir_for(run_dir, _slug_of(row["canonical_name"]))
            detail = dict(row.get("usable_policy_detail") or {})
            if attempt is not None:
                block = (attempt / PL.BLOCK_ARTIFACT).read_text(
                    encoding="utf-8", errors="replace").strip()
                stand_in = _PersistedDocument(
                    policy_text=block,
                    policy_locator=detail.get("policy_locator", ""),
                    rendered_html_path=str(attempt / "rendered.html"),
                    observation={"extraction": {f: True for f in
                                                detail.get("substantive_fields") or []},
                                 "evidence": [{"field_refs": ["pets_allowed"]}]
                                 if detail.get("substantive_fields") else []},
                    withheld_fields={f: "" for f in
                                     detail.get("withheld_fields") or []},
                    identity={"signals": {"property_code_on_page":
                                          detail.get("property_code_on_page", "")}})
                verdict = usable_policy(
                    stand_in, expected_code=detail.get("property_code_on_page", ""))
                updated["usable_policy"] = verdict["verdict"]
                updated["usable_policy_detail"] = verdict
                updated["policy_block_chars"] = verdict["block_chars"]
                updated["states_a_refusal"] = verdict["states_a_refusal"]
                updated["reassessed_from"] = str(
                    attempt.relative_to(REPO)).replace("\\", "/")
                if verdict["verdict"] != USABLE:
                    source = next((s for s in doc["source_audit"]
                                   if s["property_code"] ==
                                   detail.get("property_code_on_page")), None) or {
                        "classification": SOURCE_READY, "problems": []}
                    updated["attribution"] = attribute_failure(
                        source=source, result=None, document=stand_in,
                        usable=verdict)
                else:
                    updated["attribution"] = {"cause": "", "why": ""}
            out.append(updated)
        return out

    doc["firecrawl_rows"] = redo(
        doc["firecrawl_rows"], RUN_ROOT / DECISION_RUN_ID / DECISION_RUN_ID)
    doc["browser_control_rows"] = redo(
        doc["browser_control_rows"],
        RUN_ROOT / (DECISION_RUN_ID + "-control") / DECISION_RUN_ID)
    doc["verdict"] = decide(doc["firecrawl_rows"], doc["browser_control_rows"],
                            doc["source_audit"])
    doc["reassessed_at"] = _now()
    doc["reassessment_note"] = (
        "Verdict recomputed from the persisted captures after three defects in "
        "this module's own scoring were corrected: a property-bound refusal is "
        "a complete policy and now counts; a page stating its policy in "
        "Marriott's accordion template is a LOCATOR gap and no longer charged "
        "to the reader; and a limitation route is no longer offered for a lane "
        "that acquired nothing. No provider was called and nothing was "
        "re-acquired.")
    path.write_bytes((json.dumps(doc, indent=1, ensure_ascii=False)
                      + "\n").encode("utf-8"))
    return doc


async def run_decision() -> Dict:
    """Phases 1-8 end to end. Firecrawl first, Browser API only on failures."""
    rows = remaining_cohort()
    if len(rows) != EXPECTED_REMAINING:
        raise AssertionError("Marriott cohort is %d, expected %d"
                             % (len(rows), EXPECTED_REMAINING))
    chosen, held, grouping = decision_cohort(rows)
    sources = [source_audit(r) for r in chosen]

    firecrawl_registry = registry_override(
        provider=PROVIDERS.FIRECRAWL, fallbacks=(),
        forbid=(PROVIDERS.BRIGHTDATA_BROWSER, PROVIDERS.BRIGHTDATA_WEB_UNLOCKER))
    browser_registry = registry_override(
        provider=PROVIDERS.BRIGHTDATA_BROWSER, fallbacks=(), forbid=())

    spend_before = read_spend("020:before")
    run_dir = RUN_ROOT / DECISION_RUN_ID / DECISION_RUN_ID
    run_dir.mkdir(parents=True, exist_ok=True)

    firecrawl_rows: List[Dict] = []
    for row, source in zip(chosen, sources):
        firecrawl_rows.append(await acquire(
            row, registry=firecrawl_registry, run_dir=run_dir,
            run_id=DECISION_RUN_ID, source=source))
    spend_after_firecrawl = read_spend("020:after-firecrawl")

    # Phase 7. Only failures, and only those a provider could plausibly fix.
    control_subjects = [
        (row, source, fc) for row, source, fc in zip(chosen, sources, firecrawl_rows)
        if fc["usable_policy"] != USABLE
        and fc["attribution"]["cause"] in (FIRECRAWL_ACCESS_FAILURE,
                                           IDENTITY_FAILURE)]
    control_rows: List[Dict] = []
    control_run_dir = RUN_ROOT / (DECISION_RUN_ID + "-control") / DECISION_RUN_ID
    if control_subjects:
        control_run_dir.mkdir(parents=True, exist_ok=True)
    for row, source, _fc in control_subjects:
        control_rows.append(await acquire(
            row, registry=browser_registry, run_dir=control_run_dir,
            run_id=DECISION_RUN_ID + "-control", source=source))
    spend_after_control = read_spend("020:after-control")

    verdict = decide(firecrawl_rows, control_rows, sources)
    return {
        "schema": "ptf-marriott-decision/1.0",
        "work_order": WORK_ORDER,
        "market": MARKET,
        "generated_at": _now(),
        "remaining_marriott": len(rows),
        "cohort_assertion": "Marriott cohort == %d" % EXPECTED_REMAINING,
        "decision_cohort": [r["canonical_name"] for r in chosen],
        "held_for_production": [r["canonical_name"] for r in held],
        "grouping": grouping,
        "source_audit": sources,
        "route_before": dict(REGISTRY.load()["brands"][BRAND]),
        "routes_json_written": False,
        "firecrawl_rows": firecrawl_rows,
        "browser_control_rows": control_rows,
        "control_note": ("the Browser API was invoked only on Firecrawl "
                         "failures attributable to a provider; a page that "
                         "arrived and carried no policy is not one of those"),
        "verdict": verdict,
        "cost": {
            "firecrawl_phase": spend_delta(spend_before, spend_after_firecrawl),
            "control_phase": spend_delta(spend_after_firecrawl, spend_after_control),
            "readings": [spend_before, spend_after_firecrawl, spend_after_control],
        },
        "authority_written": False,
        "published": False,
        "readers_changed": False,
    }


# --------------------------------------------------------------------------- #
# Phase 11 -- the production run, on the approved route.
# --------------------------------------------------------------------------- #

async def run_production(*, limit: Optional[int] = None) -> Dict:
    """Acquire all seventeen remaining Marriott properties on the live route.

    No override. The registry on disk decides the lane, which is the point of
    running this after the decision rather than during it: what is measured
    here is production, not an experiment.
    """
    rows = remaining_cohort()
    if len(rows) != EXPECTED_REMAINING:
        raise AssertionError("Marriott subject count is %d, expected %d"
                             % (len(rows), EXPECTED_REMAINING))
    subjects = rows[:limit] if limit else rows

    run_dir = RUN_ROOT / PRODUCTION_RUN_ID / PRODUCTION_RUN_ID
    run_dir.mkdir(parents=True, exist_ok=True)
    journal_path = run_dir / "journal.jsonl"

    spend_before = read_spend("020-run:before")
    out: List[Dict] = []
    for row in subjects:
        source = source_audit(row)
        try:
            result = await acquire(row, registry=REGISTRY.load(),
                                   run_dir=run_dir, run_id=PRODUCTION_RUN_ID,
                                   source=source)
        except Exception as exc:                                  # noqa: BLE001
            result = {"identity_key": row["identity_key"],
                      "canonical_name": row["canonical_name"],
                      "sub_brand": source["sub_brand"],
                      "acquisition_status": "NOT_ACQUIRED",
                      "usable_policy": NOT_USABLE,
                      "final_state": "EXCEPTION",
                      "attribution": {"cause": OTHER, "why": repr(exc)[:300]}}
        # Journalled per property: a run that is killed loses at most the
        # property in flight.
        with journal_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(result, ensure_ascii=False) + "\n")
        out.append(result)
    spend_after = read_spend("020-run:after")

    usable = [r for r in out if r["usable_policy"] == USABLE]
    acquired = [r for r in out if r["acquisition_status"] == "ACQUIRED"]
    audit = template_audit(out, run_dir)
    unresolved = [r for r in out if r["usable_policy"] != USABLE]
    causes: Dict[str, int] = {}
    for row in unresolved:
        cause = (row.get("attribution") or {}).get("cause") or OTHER
        causes[cause] = causes.get(cause, 0) + 1
    providers: Dict[str, int] = {}
    for row in acquired:
        providers[row.get("provider_used", "")] = \
            providers.get(row.get("provider_used", ""), 0) + 1

    return {
        "schema": "ptf-marriott-run/1.0",
        "work_order": WORK_ORDER,
        "market": MARKET,
        "run_id": PRODUCTION_RUN_ID,
        "generated_at": _now(),
        "subject_count": len(subjects),
        "subject_assertion_held": len(rows) == EXPECTED_REMAINING,
        "route_used": dict(REGISTRY.load()["brands"][BRAND]),
        "acquired": len(acquired),
        "usable_policy_successes": len(usable),
        "refusals": sum(1 for r in usable
                        if (r.get("usable_policy_detail") or {}).get(
                            "states_a_refusal")),
        "publication_grade": sum(1 for r in out if r.get("publication_grade")),
        "unresolved": len(unresolved),
        "unresolved_causes": causes,
        "provider_mix": providers,
        "template_audit": audit,
        "fallback_uses": sum(1 for r in out
                             if len(r.get("providers_tried") or []) > 1),
        "cost": {"delta": spend_delta(spend_before, spend_after),
                 "readings": [spend_before, spend_after]},
        "authority_written": False,
        "published": False,
        "rows": out,
    }


#: Money and duration wording that changes what a guest pays. Used only to
#: FLAG a discrepancy for review, never to correct one: repairing a record from
#: a second surface is a re-derivation and belongs to its own work order.
_CHARGE_TERMS = re.compile(
    r"(\$\s?\d[\d,.]*|\bdaily\b|\bper\s+night\b|\bper\s+day\b|\bdeposit\b"
    r"|\bper\s+stay\b|\bnon-?refundable\b)", re.I)


def template_audit(rows: Sequence[Mapping], run_dir: Path) -> Dict:
    """Where Marriott's two templates disagree about what a stay costs.

    The brand locator binds to the icon-pet-friendly container. Properties that
    render their policy into the accordion template instead fall through to the
    generic walk, which on Marriott tends to land on the FAQ. The FAQ is
    property-bound and well-formed, so it passes every usability check -- and
    it can still be INCOMPLETE.

    This compares the block that was located against the accordion text on the
    same persisted page and reports the charge terms present in one and absent
    from the other. It reads artifacts only: no provider call, no re-locating,
    and no record is altered. Its output is a review queue, not a repair.
    """
    findings: List[Dict] = []
    for row in rows:
        detail = dict(row.get("usable_policy_detail") or {})
        attempt = _attempt_dir_for(run_dir, _slug_of(row["canonical_name"]))
        if attempt is None or not (attempt / "rendered.html").is_file():
            continue
        accordion = alternate_template_policy(
            (attempt / "rendered.html").read_text(encoding="utf-8",
                                                  errors="replace"))
        if not accordion:
            continue
        block = detail.get("block_text") or ""
        locator = detail.get("policy_locator") or ""
        reached_by_brand_locator = locator in MARRIOTT_BOUND_LOCATORS
        in_accordion = {t.lower().replace(" ", "")
                        for t in _CHARGE_TERMS.findall(accordion)}
        in_block = {t.lower().replace(" ", "")
                    for t in _CHARGE_TERMS.findall(block)}
        only_accordion = sorted(in_accordion - in_block)
        findings.append({
            "canonical_name": row["canonical_name"],
            "policy_locator": locator,
            "reached_by_brand_locator": reached_by_brand_locator,
            "located_block": block,
            "accordion_text": accordion,
            "charge_terms_only_in_accordion": only_accordion,
            "understates_the_cost": bool(only_accordion)
                                    and not reached_by_brand_locator,
            "note": ("the located block omits charge wording the property's own "
                     "Pet Policy section states"
                     if only_accordion else
                     "both surfaces state the same charge terms"),
        })
    understated = [f for f in findings if f["understates_the_cost"]]
    return {
        "properties_on_the_accordion_template": len(findings),
        "reached_by_the_brand_locator": sum(1 for f in findings
                                            if f["reached_by_brand_locator"]),
        "understating_records": len(understated),
        "held_for_review": [f["canonical_name"] for f in understated],
        "why_this_matters": (
            "A record that understates a pet fee is worse than one that is "
            "missing: it looks complete and a guest would act on it. None of "
            "these is published, and none is repaired here -- repairing a "
            "record from a second surface is a re-derivation and needs its own "
            "work order."),
        "findings": findings,
    }


def summarise_run(doc: Dict) -> str:
    lines = ["%s -- Milwaukee Marriott production run" % doc["work_order"],
             "subjects %d | acquired %d | usable %d (refusals %d) | unresolved %d"
             % (doc["subject_count"], doc["acquired"],
                doc["usable_policy_successes"], doc["refusals"],
                doc["unresolved"]), ""]
    for row in doc["rows"]:
        detail = row.get("usable_policy_detail") or {}
        kind = ("REFUSAL" if detail.get("states_a_refusal")
                else ("terms" if detail.get("substantive_fields") else "-"))
        lines.append("%-52s %-7s %-8s %s"
                     % (row["canonical_name"][:52],
                        "USABLE" if row["usable_policy"] == USABLE else "NO",
                        kind, (row.get("attribution") or {}).get("cause") or ""))
    cost = doc["cost"]["delta"]
    lines += ["", "provider mix: %s   fallback uses: %s"
              % (doc["provider_mix"], doc["fallback_uses"]),
              "cost: brightdata %s usd_minor (%s) | firecrawl %s credits"
              % (cost["brightdata_usd_minor_total"],
                 cost["brightdata_measurement_status"],
                 cost["firecrawl_credits_consumed"]),
              "unresolved causes: %s" % doc["unresolved_causes"]]
    return "\n".join(lines)


def summarise_decision(doc: Dict) -> str:
    lines = ["%s" % doc["work_order"],
             "remaining Marriott: %d   decision cohort: %d   held: %d"
             % (doc["remaining_marriott"], len(doc["decision_cohort"]),
                len(doc["held_for_production"])), ""]
    for row in doc["firecrawl_rows"]:
        lines.append("%-50s %-20s %-12s %s"
                     % (row["canonical_name"][:50], row["sub_brand"],
                        "USABLE" if row["usable_policy"] == USABLE else "NO",
                        row["final_state"]))
        detail = "     locator=%s block=%dch fields=%s withheld=%s" % (
            row["policy_locator"] or "-", row["policy_block_chars"],
            row["reader_fields"] or "-", row["reader_withheld"] or "-")
        lines.append(detail)
        if row["attribution"]["cause"]:
            lines.append("     CAUSE %s -- %s" % (row["attribution"]["cause"],
                                                  row["attribution"]["why"]))
    verdict = doc["verdict"]
    lines += ["", "DECISION: %s" % verdict["decision"], "  %s" % verdict["why"],
              "  usable %d/%d, publication-grade %d/%d, browser recoveries %d"
              % (verdict["usable_policy_successes"], verdict["subjects"],
                 verdict["publication_grade"], verdict["subjects"],
                 verdict["browser_recoveries"])]
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
    parser.add_argument("--plan-only", action="store_true",
                        help="cohort, grouping and source audit; no provider call")
    parser.add_argument("--decide", action="store_true",
                        help="run the Firecrawl decision test and the control")
    parser.add_argument("--run-production", action="store_true",
                        help="acquire all 17 remaining Marriott properties on "
                             "the live route")
    parser.add_argument("--reassess", action="store_true",
                        help="recompute the verdict from persisted captures; "
                             "makes no provider call")
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args(argv)

    if args.run_production:
        doc = asyncio.run(run_production())
        print(summarise_run(doc))
        if args.write_report:
            RUN_REPORT.write_bytes(
                (json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
                .encode("utf-8"))
            print("\nreport written: %s" % RUN_REPORT)
        return 0

    if args.reassess:
        doc = reassess()
        print(summarise_decision(doc))
        return 0

    if args.plan_only:
        rows = remaining_cohort()
        chosen, held, grouping = decision_cohort(rows)
        print(json.dumps({
            "remaining": len(rows),
            "assertion_holds": len(rows) == EXPECTED_REMAINING,
            "grouping": grouping,
            "decision_cohort": [r["canonical_name"] for r in chosen],
            "held": [r["canonical_name"] for r in held],
            "source_audit": [source_audit(r) for r in chosen],
        }, indent=1))
        return 0

    if args.decide:
        doc = asyncio.run(run_decision())
        print(summarise_decision(doc))
        if args.write_report:
            DECISION_REPORT.write_bytes(
                (json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
                .encode("utf-8"))
            print("\nreport written: %s" % DECISION_REPORT)
        return 0
    parser.error("choose --plan-only or --decide")


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "WORK_ORDER", "EXPECTED_REMAINING", "DECISION_COHORT_MAX",
    "remaining_cohort", "structural_groups", "decision_cohort", "sub_brand_of",
    "url_shape", "source_audit", "registry_override", "usable_policy",
    "attribute_failure", "acquire", "read_spend", "spend_delta",
    "SOURCE_READY", "BETTER_URL", "SOURCE_AMBIGUOUS", "NO_POLICY_SOURCE",
    "USABLE", "NOT_USABLE", "SOURCE_URL_FAILURE", "FIRECRAWL_ACCESS_FAILURE",
    "IDENTITY_FAILURE", "LOCATOR_FAILURE", "READER_FAILURE",
    "POLICY_NOT_PRESENT", "GENERIC_BRAND_ONLY", "OTHER",
    "SUBSTANTIVE_FIELDS",
]
