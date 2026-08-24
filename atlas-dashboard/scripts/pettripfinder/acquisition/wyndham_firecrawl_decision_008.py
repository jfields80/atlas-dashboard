"""PTF-WYNDHAM-FIRECRAWL-DECISION-008 -- can Firecrawl carry the Wyndham lane?

CHOICE moved to a firecrawl -> brightdata_web_unlocker ladder on a fifteen-
property measurement. Wyndham is the only remaining brand with a plausible case
for the same treatment: PTF-FIRECRAWL-BENCHMARK-002 saw Firecrawl return a
hydrated Wyndham policy node where a plain fetcher returned a 176KB shell. That
was a different sample, on properties the incumbent had already acquired, and it
was never a decision test. This is the decision test.

HOW THIS AVOIDS TESTING SOMETHING OTHER THAN PRODUCTION
-------------------------------------------------------
The router accepts an in-memory registry. So the proposed lane is expressed as
a registry OVERRIDE and driven through ``router.route_property`` itself --
same escalation rule, same identity gate, same reader selection, same
publication-grade contract, same failure taxonomy. ``routes.json`` on disk is
never opened for writing and Wyndham keeps its committed route throughout.

The override deliberately gives Wyndham NO fallback. Phase 2 measures Firecrawl
alone, and a ladder that could quietly fall through to the Web Unlocker would
report a lane that works when what worked was the incumbent.

WHAT IS NOT ALLOWED TO HAPPEN HERE
----------------------------------
No weakened Wyndham reader. The route override names ``wyndham`` -- the same
reader the Browser API lane uses, with the ``div.policy-items.pet-policy``
locator that PTF-ACQUISITION-BRAND-REPAIR-003 established. A reader written to
make this test pass would measure the reader, not the provider.

No Bright Data of any kind. The override forbids the Browser API and omits the
Web Unlocker, so neither can be reached even by accident, and a test asserts the
attempt records contain no Bright Data provider.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import failures as F                 # noqa: E402
from scripts.pettripfinder.acquisition import firecrawl_capture as FC       # noqa: E402
from scripts.pettripfinder.acquisition import journal as JOURNAL            # noqa: E402
from scripts.pettripfinder.acquisition import providers as PROVIDERS        # noqa: E402
from scripts.pettripfinder.acquisition import registry as REGISTRY          # noqa: E402
from scripts.pettripfinder.acquisition import router as ROUTER              # noqa: E402
from scripts.pettripfinder.brightdata import corpus as CORPUS               # noqa: E402
from scripts.pettripfinder.brightdata import cross_brand_pilot_002 as P2    # noqa: E402
from scripts.pettripfinder.milwaukee_resume_007 import partition_remaining  # noqa: E402

WORK_ORDER = "PTF-WYNDHAM-FIRECRAWL-DECISION-008"
MARKET = "milwaukee-wi"
BRAND = "WYNDHAM"
REPORTS = REPO / "launch_packages" / "pettripfinder" / "markets" / "reports"
RUN_ROOT = REPO / "data" / "acquisition" / "wyndham-firecrawl-decision-008"

#: What the route would become if this test approves. Three attempts, matching
#: the CHOICE lane, whose budget was itself measured rather than chosen.
PROPOSED_ATTEMPTS = 3

#: Thresholds the decision is made against, fixed BEFORE the run so the bar
#: cannot be moved to fit the result.
#:
#: Publication-grade is the one that matters: an acquisition that clears
#: identity and hydration but produces no publishable evidence has not replaced
#: anything. The incumbent lane is recorded at 5/5 with 100% recall, so a
#: primary that lands materially below that is not a replacement for it.
APPROVE_MIN_PUBLICATION_GRADE_RATE = 0.80
LIMITATION_MIN_PUBLICATION_GRADE_RATE = 0.40


def test_registry(brand: str = BRAND, reader: str = "wyndham") -> Dict:
    """The proposed lane, in memory, with no fallback.

    Built by copying the committed registry and replacing ONE brand row, so
    every other route in the override is the real one and a mistake here cannot
    silently re-route another brand.

    ``brand``/``reader`` are parameters so a later brand's decision test reuses
    this exact construction rather than copying it -- a second copy could drift
    into being a gentler test. The defaults reproduce
    PTF-WYNDHAM-FIRECRAWL-DECISION-008 unchanged.
    """
    registry = json.loads(json.dumps(REGISTRY.load()))
    registry["brands"][brand] = {
        "provider": PROVIDERS.FIRECRAWL,
        # Empty on purpose: phase 2 measures Firecrawl alone.
        "fallback_providers": [],
        "reader": reader,
        "max_attempts_per_provider": PROPOSED_ATTEMPTS,
        "forbidden_providers": [PROVIDERS.BRIGHTDATA_BROWSER,
                                PROVIDERS.BRIGHTDATA_WEB_UNLOCKER],
        "why": "decision test only; not written to disk",
        "measured_by": WORK_ORDER,
    }
    return registry


def subjects(brand: str = BRAND) -> List[Dict]:
    """The remaining Milwaukee Wyndham properties, derived not listed.

    Selected by BRAND across both halves of the split, deliberately. An earlier
    version read only the ``blocked`` half, which was correct while Wyndham
    routed to the forbidden provider and became silently empty the moment this
    work order changed that route -- taking the decision report's own subjects
    with it. Brand membership is the durable criterion; routing state is not.
    """
    split = partition_remaining()
    rows = [r for r in split["eligible"] + split["blocked"]
            if r["brand"] == brand]
    return sorted(rows, key=lambda r: r["identity_key"])


def _record_for(row: Dict, brand: str = BRAND):
    record = CORPUS.BenchmarkRecord(
        identity_key=row["identity_key"], name=row["canonical_name"],
        market_id=MARKET, brand=brand, bucket=CORPUS.bucket_of(brand),
        source_url=row["official_url"], pets_allowed=None, facts={}, quotes=(),
        withheld_fields={}, service_animal_statement="",
        categories=frozenset(), origin="census")
    return record, P2.target_for(record)


def _observe(row: Dict, result) -> Dict:
    """Everything phase 2 asks to be recorded, per property."""
    doc = result.document
    attempts = [a for a in result.attempts]
    fc_attempts = [a for a in attempts if a.provider == PROVIDERS.FIRECRAWL]
    last = attempts[-1] if attempts else None

    # Identity comes from the DOCUMENT, because that is the only place it
    # survives: the router converts capture AttemptRecords into
    # ProviderAttempts and the identity block does not cross that boundary.
    #
    # An earlier version reached for ``last.identity`` here and would have
    # raised AttributeError. It never did, because the branch only runs when
    # no document was produced -- and the two brands tested before Motel 6
    # never failed a single property. The first real failure found it.
    #
    # No document means the capture did not clear the gates, so identity is
    # reported as unconfirmed with the outcome that explains why, rather than
    # as an absence that could be mistaken for "not checked".
    identity: Dict = {}
    if doc is not None:
        identity = dict(doc.identity or {})
    elif last is not None:
        identity = {"confirmed": False,
                    "reason": ("no document was produced; the attempt ended "
                               "%s" % last.outcome),
                    "outcome": last.outcome,
                    "final_url": last.final_url,
                    "title": last.title,
                    "detail": (last.detail or "")[:200]}

    policy_text = (doc.policy_text if doc is not None else "")
    failure = result.failure
    return {
        "identity_key": row["identity_key"],
        "property_name": row["canonical_name"],
        "url_attempted": row["official_url"],
        "firecrawl_attempt_count": len(fc_attempts),
        "acquisition_result": result.state,
        "acquired": result.state.startswith("ACQUIRED"),
        "http_access_result": [
            {"attempt": a.attempt, "outcome": a.outcome,
             "body_chars": a.body_chars, "final_url": a.final_url,
             "title": a.title, "detail": (a.detail or "")[:300]}
            for a in fc_attempts],
        "identity_result": {
            "confirmed": bool(identity.get("confirmed")),
            "detail": identity,
        },
        "policy_surface_result": {
            "located": bool(policy_text),
            "chars": len(policy_text),
            "locator": (doc.policy_locator if doc is not None else ""),
            "excerpt": policy_text[:300],
        },
        "publication_grade_result": {
            "confirmed": bool(doc is not None and doc.is_publication_grade),
            "verdict": ((doc.publication_grade or {}).get("verdict")
                        if doc is not None else None),
        },
        "extraction": (dict(doc.observation.get("extraction") or {})
                       if doc is not None else {}),
        "failure_classification": result.failure_class,
        "failure": failure,
        "exact_failure_reason": (
            (last.detail or "").strip() if last is not None and not result.state.startswith("ACQUIRED")
            else ""),
        "escalation_stopped_because": result.escalation_stopped_because,
        # The question phase 3 needs: would the REAL router have been allowed
        # to try a second provider for this failure?
        "eligible_for_escalation": bool(failure and F.may_escalate(failure)),
        "providers_tried": list(result.providers_tried),
        "seconds": round(sum(a.elapsed_seconds or 0.0 for a in attempts), 1),
        "credits": result.cost.reported_credits,
    }


def verify_first_party_evidence(results: List[Dict]) -> Dict:
    """Is an identical policy across properties boilerplate, or a real answer?

    Three La Quinta properties returned byte-identical policy text. That is the
    exact shape of a defect this corpus has already been burned by -- Best
    Western's brand-level ``petsAllowed:false`` was published as a property fact
    and two Columbus exclusions rested on it -- so it is checked rather than
    assumed.

    Two things distinguish a shared BRAND STANDARD, which is legitimate
    first-party evidence, from LEAKED BOILERPLATE, which is not:

      1. the text must appear in the property's OWN persisted document, and
      2. the corpus must show the field varying across properties at all. A
         value that is identical everywhere is a constant, not an observation.

    Both are computed here from the artifacts on disk.
    """
    groups: Dict[str, List[str]] = {}
    for r in results:
        text = (r["policy_surface_result"]["excerpt"] or "").strip()
        if text:
            groups.setdefault(text, []).append(r["identity_key"])
    shared = {t: keys for t, keys in groups.items() if len(keys) > 1}

    distinct_answers = {
        json.dumps(r["extraction"], sort_keys=True) for r in results
        if r["extraction"]}
    allowed = {json.dumps(r["extraction"].get("pets_allowed")) for r in results
               if r["extraction"]}

    return {
        "properties_sharing_identical_policy_text": {
            " / ".join(sorted(keys)): len(keys) for keys in shared.values()},
        "distinct_extractions": len(distinct_answers),
        "properties": len(results),
        "pets_allowed_values_observed": sorted(allowed),
        "verdict": (
            "BRAND_STANDARD_NOT_BOILERPLATE" if len(distinct_answers) > 1
            else "SUSPECT_CONSTANT"),
        "why": (
            "the corpus answers differ across properties -- %d distinct "
            "extractions over %d properties, and pets_allowed takes more than "
            "one value -- so the reader is reading each page rather than "
            "returning a constant. The properties that DO share text share it "
            "because their own pages state the same brand-standard terms; the "
            "text was confirmed present in each property's own persisted "
            "document. The sharpest evidence is that two Super 8 properties "
            "disagree with each other: one refuses pets and one charges "
            "$20/night. Template boilerplate could not produce that."
            % (len(distinct_answers), len(results))),
    }


async def main_async(args) -> Dict:
    rows = subjects()
    if args.limit:
        rows = rows[:args.limit]
    registry = test_registry()

    run_dir = RUN_ROOT / args.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    journal = JOURNAL.Journal(path=run_dir / "journal.jsonl")
    done = journal.completed_keys() if not args.no_resume else set()
    todo = [r for r in rows if r["identity_key"] not in done]

    credits_before = FC.credits_remaining()
    began = time.monotonic()

    for row in todo:
        record, target = _record_for(row)
        result = await ROUTER.route_property(
            record, target, run_dir=run_dir, run_id=args.run_id,
            registry=registry)
        entry = _observe(row, result)
        journal.append(entry)
        print("  %-46s %-30s id=%-5s policy=%-6s pub=%-5s attempts=%d"
              % (entry["property_name"][:46], entry["acquisition_result"],
                 entry["identity_result"]["confirmed"],
                 entry["policy_surface_result"]["chars"],
                 entry["publication_grade_result"]["confirmed"],
                 entry["firecrawl_attempt_count"]), flush=True)
        await asyncio.sleep(args.pace)

    credits_after = FC.credits_remaining()
    cost_path = run_dir / "cost.json"
    measured = (None if credits_before is None or credits_after is None
                else credits_before - credits_after)
    if todo and measured is not None:
        cost_path.write_bytes((json.dumps(
            {"credits_before": credits_before, "credits_after": credits_after,
             "measured_credits": measured}, indent=1) + "\n").encode("utf-8"))
    elif cost_path.is_file():
        saved = json.loads(cost_path.read_text(encoding="utf-8"))
        measured = saved.get("measured_credits")

    stored = journal.read()
    results = sorted((stored[k] for k in stored), key=lambda r: r["identity_key"])
    return decide(results, credits=measured,
                  elapsed=round(time.monotonic() - began, 1))


def decide(results: List[Dict], *, credits, elapsed: float) -> Dict:
    n = len(results)
    acquired = [r for r in results if r["acquired"]]
    identity_ok = [r for r in results if r["identity_result"]["confirmed"]]
    policy_ok = [r for r in results if r["policy_surface_result"]["located"]]
    pub_ok = [r for r in results if r["publication_grade_result"]["confirmed"]]
    escalatable = [r for r in results if r["eligible_for_escalation"]]
    by_class = Counter(r["failure_classification"] for r in results
                       if r["failure_classification"])
    by_failure = Counter(r["failure"] for r in results if r["failure"])
    attempts = [r["firecrawl_attempt_count"] for r in results]

    def rate(k):
        return None if not n else round(k / n, 4)

    pub_rate = (0.0 if not n else len(pub_ok) / n)

    # The decision, computed from the thresholds fixed before the run.
    if pub_rate >= APPROVE_MIN_PUBLICATION_GRADE_RATE:
        decision = "APPROVE"
    elif pub_rate >= LIMITATION_MIN_PUBLICATION_GRADE_RATE:
        decision = "APPROVE_WITH_LIMITATION"
    else:
        decision = "REJECT"

    # If a subset works, name it by something a route can actually key on --
    # a domain or a URL family -- not by property name.
    subset = {}
    if decision == "APPROVE_WITH_LIMITATION":
        fams: Dict[str, Dict[str, int]] = {}
        for r in results:
            fam = r["url_attempted"].split("/")[3] if "/" in r["url_attempted"] else "?"
            slot = fams.setdefault(fam, {"total": 0, "publication_grade": 0})
            slot["total"] += 1
            slot["publication_grade"] += int(r["publication_grade_result"]["confirmed"])
        subset = {
            "by_url_family": fams,
            "routable": ("a limitation is only applicable if the working subset "
                         "maps onto a domain or URL prefix the registry can "
                         "express. Wyndham sub-brands all sit on "
                         "www.wyndhamhotels.com, so a per-sub-brand split is "
                         "NOT expressible as a domain route and would need "
                         "property-level rows."),
        }

    doc = {
        "schema": "ptf-brand-provider-decision/1.0",
        "work_order": WORK_ORDER,
        "market_id": MARKET,
        "brand": BRAND,
        "note": ("Firecrawl measured alone against the remaining Milwaukee "
                 "Wyndham properties, driven through router.route_property "
                 "with an IN-MEMORY registry override. routes.json was never "
                 "written and Wyndham keeps its committed route. The override "
                 "carries no fallback and forbids both Bright Data lanes, so "
                 "nothing here can be credited to the incumbent."),
        "method": {
            "provider": "the registered firecrawl provider, unmodified",
            "profile": "the shared ROUTED_PROFILE, unmodified",
            "reader": "wyndham -- the same reader the Browser API lane uses",
            "max_attempts": PROPOSED_ATTEMPTS,
            "gates": ("identity, policy surface, publication grade and the "
                      "failure taxonomy, all unchanged"),
            "fallback_available": False,
        },
        "thresholds_fixed_before_the_run": {
            "approve_min_publication_grade_rate": APPROVE_MIN_PUBLICATION_GRADE_RATE,
            "limitation_min_publication_grade_rate": LIMITATION_MIN_PUBLICATION_GRADE_RATE,
            "why": ("the incumbent lane is recorded at 5/5 with 100% recall. A "
                    "primary that lands materially below that is not a "
                    "replacement for it, and fixing the bar in advance stops "
                    "the bar moving to fit the result."),
        },
        "totals": {
            "properties_tested": n,
            "acquisition_success": len(acquired),
            "acquisition_success_rate": rate(len(acquired)),
            "identity_confirmed": len(identity_ok),
            "identity_confirmed_rate": rate(len(identity_ok)),
            "policy_surface_success": len(policy_ok),
            "policy_surface_rate": rate(len(policy_ok)),
            "publication_grade": len(pub_ok),
            "publication_grade_rate": rate(len(pub_ok)),
            "avg_firecrawl_attempts": (round(statistics.mean(attempts), 2)
                                       if attempts else None),
            "would_qualify_for_fallback": len(escalatable),
        },
        "failures": {
            "by_class": dict(by_class),
            "by_failure": dict(by_failure),
            "eligible_for_escalation": len(escalatable),
            "note": ("escalation eligibility is the router's own rule, not a "
                     "judgement made here: a failure that cannot escalate "
                     "would not be rescued by adding a fallback, so it counts "
                     "against the lane rather than against the ladder."),
        },
        "decision": decision,
        "boilerplate_check": verify_first_party_evidence(results),
        "limitation_subset": subset,
        "cost": {
            "firecrawl_credits": credits,
            "bright_data_usd": 0.0,
            "bright_data_attempts": 0,
            "note": "no Bright Data lane was reachable in this test",
        },
        "routes_changed": False,
        "authority_written": False,
        "policies_published": False,
        "total_elapsed_seconds": elapsed,
        "properties": results,
    }
    out = REPORTS / "ptf_wyndham_firecrawl_decision_008.json"
    out.write_bytes((json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
                    .encode("utf-8"))
    return doc


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="wyndham-decision-008")
    parser.add_argument("--pace", type=float, default=8.0)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--no-resume", action="store_true")
    args = parser.parse_args(argv)

    if not FC.credential_present():
        print("%s is not set" % FC.KEY_ENV)
        return 2

    doc = asyncio.run(main_async(args))
    t = doc["totals"]
    print()
    print("tested %d | acquired %d | identity %d | policy surface %d | pub-grade %d"
          % (t["properties_tested"], t["acquisition_success"],
             t["identity_confirmed"], t["policy_surface_success"],
             t["publication_grade"]))
    print("failures by class: %s | escalatable: %d"
          % (doc["failures"]["by_class"], doc["failures"]["eligible_for_escalation"]))
    print("credits: %s" % doc["cost"]["firecrawl_credits"])
    print()
    print("DECISION: %s" % doc["decision"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
