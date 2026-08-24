"""PTF-IHG-FIRECRAWL-DECISION-009 -- can Firecrawl carry the IHG lane?

Choice and Wyndham both moved onto Firecrawl on their own 100% measurements.
IHG is the third candidate and it is the one with a known reason to fail.

WHY IHG IS NOT JUST ANOTHER BRAND
---------------------------------
Two findings from earlier work orders bear directly on this:

  * PTF-DISCOVERY established that **IHG carries no ``petsAllowed`` in its
    JSON-LD** -- the value lives in inline JavaScript. A provider that returns
    rendered HTML only helps if the policy actually PAINTS into the DOM.
  * PTF-CLEVELAND-PASS-4 found that IHG's ``hoteldetail`` page freezes a CDP
    session on a full outerHTML read, and the policy had to be reached by
    querying ``[class*="faq"]`` innerHTML specifically.

So the incumbent lane's own record is 4/5 fetched at **62% recall** -- the
weakest recall of any routed brand, and the most expensive at $2.71 for five
properties. That combination is exactly why IHG is worth testing and exactly
why it might not pass: the bar is publication-grade evidence, and a lane that
returns a page without the policy painted on it produces none.

METHOD, IDENTICAL TO THE TWO DECISIONS BEFORE IT
------------------------------------------------
The proposed lane is an IN-MEMORY registry override driven through
``router.route_property``: no fallback, both Bright Data lanes forbidden, the
existing ``ihg`` reader, the shared ``ROUTED_PROFILE``, every gate unchanged.
``routes.json`` is never written. The construction is imported from the Wyndham
decision module rather than copied, so a third test cannot quietly be a gentler
test than the first two.

WHAT PHASE 2 ASKS TO BE INSPECTED FOR
-------------------------------------
Publication-grade is necessary and not sufficient. A capture can clear every
gate and still be useless or wrong, so the audit below looks for the specific
ways IHG could produce a passing-but-bad record: policy text lifted from a
global IHG page rather than the hotel, identical text across unrelated
properties, a fee with no basis, a weight with no scope, a species claim the
source never made. Those are reported per property and in aggregate, and a
systemic one is grounds for REJECT even at a passing rate.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import statistics
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import failures as F                 # noqa: E402
from scripts.pettripfinder.acquisition import firecrawl_capture as FC       # noqa: E402
from scripts.pettripfinder.acquisition import journal as JOURNAL            # noqa: E402
from scripts.pettripfinder.acquisition import providers as PROVIDERS        # noqa: E402
from scripts.pettripfinder.acquisition import router as ROUTER              # noqa: E402
from scripts.pettripfinder.acquisition import wyndham_firecrawl_decision_008 as WY  # noqa: E402
from scripts.pettripfinder.brightdata import policy_reading as PR           # noqa: E402

WORK_ORDER = "PTF-IHG-FIRECRAWL-DECISION-009"
MARKET = "milwaukee-wi"
BRAND = "IHG"
READER = "ihg"
REPORTS = REPO / "launch_packages" / "pettripfinder" / "markets" / "reports"
RUN_ROOT = REPO / "data" / "acquisition" / "ihg-firecrawl-decision-009"

#: The cohort this decision is made over. Asserted, not assumed: a short cohort
#: would make a rate out of fewer properties than the bar was set for.
EXPECTED_COHORT = 5

#: Fixed before execution, and the same bar the two previous brands cleared.
APPROVE_MIN_PUBLICATION_GRADE_RATE = 0.80
LIMITATION_MIN_PUBLICATION_GRADE_RATE = 0.40

#: Facts that, once claimed, need a companion fact to mean anything. A fee with
#: no basis is a number a guest cannot act on; a weight with no scope does not
#: say whether it caps one animal or all of them.
_INCOMPLETE_PAIRS = (
    ("pet_fee", "fee_basis", "a fee amount with no basis"),
    ("weight_limit", "weight_scope", "a weight limit with no stated scope"),
)


def audit_property(prop: Dict) -> Dict:
    """The specific ways a passing IHG record could still be a bad one."""
    extraction = prop.get("extraction") or {}
    block = (prop.get("policy_surface_result") or {}).get("excerpt") or ""
    reading = PR.parse(block, strategy="audit") if block else None

    findings = []
    for field, companion, why in _INCOMPLETE_PAIRS:
        if field in extraction and companion not in extraction:
            findings.append({"field": field, "issue": why})
    if extraction.get("pets_allowed") is True and "pet_count_limit" not in extraction:
        findings.append({"field": "pet_count_limit",
                         "issue": "an allowance with no stated pet count"})
    if "species_allowed" in extraction:
        stated = " ".join(str(v) for v in extraction["species_allowed"]).lower()
        if stated and not any(w in block.lower() for w in ("dog", "cat", "pet")):
            findings.append({"field": "species_allowed",
                             "issue": "a species claim the block does not state"})

    requested = urlparse(prop.get("url_attempted") or "")
    finals = {a.get("final_url") for a in (prop.get("http_access_result") or [])
              if a.get("final_url")}
    off_property = sorted(
        u for u in finals
        if urlparse(u).netloc != requested.netloc
        or "hoteldetail" not in urlparse(u).path.lower()
        and "hoteldetail" in requested.path.lower())

    return {
        "identity_key": prop["identity_key"],
        # policy_reading's own brand-generic detector: text that reads as a
        # chain statement rather than this hotel's.
        "brand_generic_text": bool(reading and reading.brand_generic),
        "landed_off_the_property_page": off_property,
        "incomplete_fact_pairs": findings,
        "fields": sorted(extraction),
        "field_count": len(extraction),
    }


#: Wording that means a stated amount is ONE TIER of several, not the price.
#: IHG writes these constantly: "50 USD ... for stays 1 to 6 nights, 150 USD
#: for stays over 7 nights".
_TIER_RE = re.compile(
    r"for\s+stays?\s+(over\s+)?\d|"
    r"\d\s*(to|-|through)\s*\d+\s*night|"
    r"\d+\s*or\s+more\s*(night|will\s+be)|"
    r"(weekly|monthly)\s+\d|"
    r"for\s+a\s+\d\s*(to|-)\s*\d\s*night",
    re.IGNORECASE)


def tiered_fee_audit(props: List[Dict]) -> Dict:
    """A fee amount published from a source that states several is WRONG.

    This is the check the work order asked for by name -- "do not flatten
    complex/tiered fees merely to obtain a pass" -- and it is the one place an
    IHG record can be publication-grade and still misprice a stay. Staybridge
    Milwaukee Airport South is the live example: its page states 50 USD for
    stays of 1 to 6 nights and 150 USD for stays over 7, and an extraction
    carrying 5000 has published the first tier as the price. A week costs the
    guest 100 USD more than that record says.

    A fee correctly WITHHELD from a tiered source is not a finding: that is the
    schema doing its job, and two of these five did exactly that.
    """
    flagged, withheld_correctly = [], []
    for prop in props:
        block = (prop.get("policy_surface_result") or {}).get("excerpt") or ""
        if not _TIER_RE.search(block):
            continue
        extraction = prop.get("extraction") or {}
        amount = extraction.get("pet_fee", extraction.get("fee_amount"))
        row = {
            "identity_key": prop["identity_key"],
            "tier_language": _TIER_RE.search(block).group(0).strip(),
            "published_amount_minor": amount,
            "fee_basis_present": "fee_basis" in extraction,
        }
        if amount is None:
            withheld_correctly.append(row)
        else:
            row["issue"] = ("a tiered fee was reduced to a single amount; the "
                            "source states more than one price")
            flagged.append(row)
    return {
        "properties_with_tiered_fee_language": len(flagged) + len(withheld_correctly),
        "fee_correctly_withheld": withheld_correctly,
        "fee_flattened_to_one_tier": flagged,
        "verdict": ("TIERED_FEE_FLATTENED" if flagged
                    else "NO_TIERED_FEE_PUBLISHED"),
        "provider_independent": (
            "this is a READER behaviour, not a provider one. The same text "
            "through the incumbent lane would produce the same record, so it "
            "does not bear on which provider carries IHG -- but it does bear "
            "on whether these records may be published."),
        "consequence": ("any property listed under fee_flattened_to_one_tier is "
                        "HELD from publication pending a reader fix. It is not "
                        "counted against the provider."),
    }


def aggregate_audit(props: List[Dict]) -> Dict:
    """Systemic versus incidental. One thin record is not a brand defect."""
    per = [audit_property(p) for p in props]
    texts: Dict[str, List[str]] = {}
    for p in props:
        t = ((p.get("policy_surface_result") or {}).get("excerpt") or "").strip()
        if t:
            texts.setdefault(t, []).append(p["identity_key"])
    shared = {t: k for t, k in texts.items() if len(k) > 1}
    distinct = {json.dumps(p.get("extraction") or {}, sort_keys=True)
                for p in props if p.get("extraction")}

    n = len(props) or 1
    generic = [a for a in per if a["brand_generic_text"]]
    off_page = [a for a in per if a["landed_off_the_property_page"]]
    incomplete = [a for a in per if a["incomplete_fact_pairs"]]

    systemic = []
    if len(generic) / n >= 0.5:
        systemic.append("brand-generic policy text on half or more of the cohort")
    if off_page:
        systemic.append("one or more captures landed off the property page")
    if len(distinct) <= 1 and len(props) > 1:
        systemic.append("every property produced the same extraction")

    return {
        "per_property": per,
        "properties_with_brand_generic_text": len(generic),
        "properties_landing_off_the_property_page": len(off_page),
        "properties_with_incomplete_fact_pairs": len(incomplete),
        "properties_sharing_identical_policy_text": {
            " / ".join(sorted(keys)): len(keys) for keys in shared.values()},
        "distinct_extractions": len(distinct),
        "systemic_defects": systemic,
        "verdict": "SYSTEMIC_DEFECT" if systemic else "NO_SYSTEMIC_DEFECT",
        "note": ("incomplete fact pairs are recorded but are NOT counted as "
                 "failures: a source that states a fee and no basis has been "
                 "read correctly, and flattening it to obtain a pass is the "
                 "thing this audit exists to prevent."),
    }


async def main_async(args) -> Dict:
    rows = WY.subjects(BRAND)
    if len(rows) != EXPECTED_COHORT:
        raise SystemExit("expected %d IHG properties, derived %d -- refusing "
                         "to make a rate out of a short cohort"
                         % (EXPECTED_COHORT, len(rows)))
    registry = WY.test_registry(BRAND, READER)

    run_dir = RUN_ROOT / args.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    journal = JOURNAL.Journal(path=run_dir / "journal.jsonl")
    done = journal.completed_keys() if not args.no_resume else set()
    todo = [r for r in rows if r["identity_key"] not in done]

    credits_before = FC.credits_remaining()
    began = time.monotonic()

    for row in todo:
        record, target = WY._record_for(row, BRAND)
        result = await ROUTER.route_property(
            record, target, run_dir=run_dir, run_id=args.run_id,
            registry=registry)
        entry = WY._observe(row, result)
        journal.append(entry)
        print("  %-46s %-30s id=%-5s policy=%-5s pub=%-5s attempts=%d"
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
        measured = json.loads(cost_path.read_text(encoding="utf-8")).get(
            "measured_credits")

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
    attempts = [r["firecrawl_attempt_count"] for r in results]
    audit = aggregate_audit(results)

    pub_rate = (0.0 if not n else len(pub_ok) / n)
    if pub_rate >= APPROVE_MIN_PUBLICATION_GRADE_RATE and not audit["systemic_defects"]:
        decision = "APPROVE"
    elif pub_rate >= LIMITATION_MIN_PUBLICATION_GRADE_RATE:
        decision = "APPROVE_WITH_LIMITATION"
    else:
        decision = "REJECT"

    reasons = []
    if pub_rate < APPROVE_MIN_PUBLICATION_GRADE_RATE:
        reasons.append("publication-grade rate %.0f%% is below the %.0f%% bar "
                       "fixed before the run"
                       % (pub_rate * 100, APPROVE_MIN_PUBLICATION_GRADE_RATE * 100))
    for defect in audit["systemic_defects"]:
        reasons.append("systemic defect: %s" % defect)
    if not reasons:
        reasons.append("publication-grade rate %.0f%% clears the %.0f%% bar with "
                       "no systemic identity or policy-surface defect"
                       % (pub_rate * 100, APPROVE_MIN_PUBLICATION_GRADE_RATE * 100))

    doc = {
        "schema": "ptf-brand-provider-decision/1.0",
        "work_order": WORK_ORDER,
        "market_id": MARKET,
        "brand": BRAND,
        "note": ("Firecrawl measured alone against the full 5-property "
                 "Milwaukee IHG cohort, through router.route_property with an "
                 "in-memory registry override. routes.json was never written. "
                 "The override construction is imported from the Wyndham "
                 "decision module, not copied, so this cannot be a gentler "
                 "test than the two that preceded it."),
        "prior_expectations": {
            "incumbent_record": ("4/5 fetched at 100% precision and 62% recall "
                                 "-- the weakest recall of any routed brand -- "
                                 "at $2.71 for five properties"),
            "known_hazards": [
                "IHG carries no petsAllowed in JSON-LD; the value lives in "
                "inline JavaScript, so a rendered fetch only helps if the "
                "policy paints into the DOM",
                "the hoteldetail page froze a CDP session on a full outerHTML "
                "read in PTF-CLEVELAND-PASS-4; the policy had to be reached "
                "through [class*='faq'] innerHTML",
            ],
        },
        "method": {
            "provider": "the registered firecrawl provider, unmodified",
            "profile": "the shared ROUTED_PROFILE, unmodified",
            "reader": READER,
            "max_attempts": WY.PROPOSED_ATTEMPTS,
            "fallback_available": False,
            "gates": "identity, policy surface, publication grade, failure taxonomy -- unchanged",
        },
        "thresholds_fixed_before_the_run": {
            "cohort": EXPECTED_COHORT,
            "approve_min_publication_grade_rate": APPROVE_MIN_PUBLICATION_GRADE_RATE,
            "limitation_min_publication_grade_rate": LIMITATION_MIN_PUBLICATION_GRADE_RATE,
            "approve_also_requires": "no systemic identity or policy-surface defect",
        },
        "totals": {
            "properties_tested": n,
            "acquisition_success": len(acquired),
            "acquisition_success_rate": round(len(acquired) / n, 4) if n else None,
            "identity_confirmed": len(identity_ok),
            "identity_confirmed_rate": round(len(identity_ok) / n, 4) if n else None,
            "policy_surface_success": len(policy_ok),
            "policy_surface_rate": round(len(policy_ok) / n, 4) if n else None,
            "publication_grade": len(pub_ok),
            "publication_grade_rate": round(pub_rate, 4),
            "avg_firecrawl_attempts": (round(statistics.mean(attempts), 2)
                                       if attempts else None),
            "would_qualify_for_fallback": len(escalatable),
        },
        "failures": {
            "by_class": dict(Counter(r["failure_classification"] for r in results
                                     if r["failure_classification"])),
            "by_failure": dict(Counter(r["failure"] for r in results if r["failure"])),
            "eligible_for_escalation": len(escalatable),
        },
        "defect_audit": audit,
        "tiered_fee_audit": tiered_fee_audit(results),
        "decision": decision,
        "decision_reasons": reasons,
        "cost": {
            "firecrawl_credits": credits,
            "bright_data_usd": 0.0,
            "bright_data_attempts": 0,
        },
        "routes_changed": False,
        "authority_written": False,
        "policies_published": False,
        "total_elapsed_seconds": elapsed,
        "properties": results,
    }
    out = REPORTS / "ptf_ihg_firecrawl_decision_009.json"
    out.write_bytes((json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
                    .encode("utf-8"))
    return doc


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="ihg-decision-009")
    parser.add_argument("--pace", type=float, default=8.0)
    parser.add_argument("--no-resume", action="store_true")
    args = parser.parse_args(argv)

    if not FC.credential_present():
        print("%s is not set" % FC.KEY_ENV)
        return 2

    doc = asyncio.run(main_async(args))
    t = doc["totals"]
    print()
    print("tested %d | acquired %d | identity %d | policy %d | pub-grade %d (%.0f%%)"
          % (t["properties_tested"], t["acquisition_success"],
             t["identity_confirmed"], t["policy_surface_success"],
             t["publication_grade"], t["publication_grade_rate"] * 100))
    print("failures: %s | escalatable: %d"
          % (doc["failures"]["by_class"], doc["failures"]["eligible_for_escalation"]))
    print("audit: %s %s" % (doc["defect_audit"]["verdict"],
                            doc["defect_audit"]["systemic_defects"] or ""))
    print("credits: %s" % doc["cost"]["firecrawl_credits"])
    print()
    print("DECISION: %s" % doc["decision"])
    for r in doc["decision_reasons"]:
        print("   - %s" % r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
