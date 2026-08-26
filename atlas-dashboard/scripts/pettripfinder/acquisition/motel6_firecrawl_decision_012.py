"""PTF-MOTEL6-FIRECRAWL-DECISION-012 -- can Firecrawl carry the Motel 6 lane?

The fourth brand decision test, and the one with the smallest cohort and the
thinnest incumbent evidence behind it. The committed Motel 6 route says, in its
own words, "generic walk; one property measured". A route resting on n=1 is not
a strong incumbent, but it is also not a reason to move: it is a reason to
measure properly before moving.

TWO THINGS MAKE MOTEL 6 DIFFERENT FROM THE THREE THAT PASSED
-------------------------------------------------------------
There is no dedicated Motel 6 reader. Choice, Wyndham and IHG each moved onto
Firecrawl carrying a brand reader with a locator built for their markup; Motel 6
uses the ``generic`` walk. So this test measures a provider AND a generic
reader together, and a failure could belong to either. Where that ambiguity
appears it is reported rather than resolved in the provider's favour.

And Motel 6's brand position is that pets stay free. That makes "no fee" the
expected answer, which makes it the dangerous one: a reader that finds nothing
and a property that charges nothing produce the same record. The audit below
separates them -- a zero fee must be STATED, never inferred from silence.

METHOD, UNCHANGED FROM THE THREE BEFORE IT
------------------------------------------
An in-memory registry override driven through ``router.route_property``: no
fallback, both Bright Data lanes forbidden, the existing ``generic`` reader,
the shared ``ROUTED_PROFILE``, every gate untouched, ``routes.json`` never
written. The override construction and the defect audits are IMPORTED from the
Wyndham and IHG decision modules rather than copied, so the fourth test cannot
quietly be a gentler test than the first three.
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
from typing import Dict, List

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import firecrawl_capture as FC       # noqa: E402
from scripts.pettripfinder.acquisition import ihg_firecrawl_decision_009 as IHG  # noqa: E402
from scripts.pettripfinder.acquisition import journal as JOURNAL            # noqa: E402
from scripts.pettripfinder.acquisition import router as ROUTER              # noqa: E402
from scripts.pettripfinder.acquisition import wyndham_firecrawl_decision_008 as WY  # noqa: E402
from scripts.pettripfinder.acquisition import firecrawl_choice_validation_004 as CV  # noqa: E402
from scripts.pettripfinder.brightdata import policy_reading as PR           # noqa: E402

WORK_ORDER = "PTF-MOTEL6-FIRECRAWL-DECISION-012"
MARKET = "milwaukee-wi"
BRAND = "MOTEL6"
READER = "generic"
REPORTS = REPO / "launch_packages" / "pettripfinder" / "markets" / "reports"
RUN_ROOT = REPO / "data" / "acquisition" / "motel6-firecrawl-decision-012"

#: Asserted before any request. A short cohort would make a rate out of fewer
#: properties than the bar was set for.
EXPECTED_COHORT = 4

#: Fixed before execution. 75% of four is three.
APPROVE_MIN_PUBLICATION_GRADE_RATE = 0.75
LIMITATION_MIN_PUBLICATION_GRADE_RATE = 0.40

#: An explicit statement that pets cost nothing. Motel 6 markets itself on this,
#: so the phrase is expected -- and a zero fee that is INFERRED rather than read
#: would be indistinguishable from a reader that found nothing at all.
_FREE_RE = re.compile(
    r"\b(?:no|without|free\s+of)\s+(?:additional\s+|extra\s+)?(?:charge|cost|fee)\b"
    r"|\bpets?\s+stay\s+free\b|\bfree\s+of\s+charge\b|\bat\s+no\s+cost\b",
    re.IGNORECASE)


def free_stay_audit(props: List[Dict]) -> Dict:
    """A zero fee must be STATED, never inferred from a reader finding nothing.

    For a brand whose whole proposition is that pets stay free, "no fee in the
    record" is the expected shape of both a correct answer and a total
    extraction failure. This separates them.
    """
    stated_free, silent, priced = [], [], []
    for prop in props:
        block = (prop.get("policy_surface_result") or {}).get("excerpt") or ""
        extraction = prop.get("extraction") or {}
        fee = extraction.get("pet_fee", extraction.get("fee_amount"))
        row = {"identity_key": prop["identity_key"],
               "fee_in_record": fee,
               "source_says_free": bool(_FREE_RE.search(block))}
        if fee not in (None, 0):
            priced.append(row)
        elif row["source_says_free"]:
            stated_free.append(row)
        else:
            silent.append(row)
    inferred = [r for r in stated_free + silent if r["fee_in_record"] == 0
                and not r["source_says_free"]]
    return {
        "source_states_no_charge": stated_free,
        "no_fee_and_source_silent": silent,
        "fee_stated": priced,
        "zero_fee_inferred_from_silence": inferred,
        "verdict": ("ZERO_FEE_INFERRED" if inferred else "NO_INFERRED_ZERO_FEE"),
        "note": ("a record carrying no fee because the source said nothing is "
                 "ABSENCE and is correct; a record carrying 0 because the "
                 "source said nothing would be an inference and is not. Only "
                 "the second is a defect."),
    }


#: A policy block should say something a guest can act on. These are the
#: features that make it a policy rather than a label.
_POLICY_FEATURE_FIELDS = ("pet_fee", "fee_amount", "fee_basis", "weight_limit",
                          "pet_count_limit", "species_allowed", "deposit",
                          "fee_cap", "refundable")


def amenity_chip_audit(props: List[Dict]) -> Dict:
    """Is the "policy" actually an item in an amenity grid?

    The sharpest failure this corpus has: a capture clears identity, hydration
    and publication-grade over a block that reads "Pets Allowed Coin Laundry".
    That is a checkbox in an amenities list sitting next to the laundry
    checkbox, and reading ``pets_allowed: true`` from it asserts a policy the
    property never wrote. It has no fee, no weight, no count, no species and no
    conditions, because it is a label rather than a statement.

    Flagged when a located block is short, carries no policy feature, and the
    extraction contains nothing but ``pets_allowed``. All three together, so a
    genuinely terse refusal -- "Sorry, no pets allowed." -- is not caught.
    """
    flagged, substantive = [], []
    for prop in props:
        block = ((prop.get("policy_surface_result") or {}).get("excerpt") or "").strip()
        if not block:
            continue
        extraction = prop.get("extraction") or {}
        features = [f for f in _POLICY_FEATURE_FIELDS if f in extraction]
        only_allowed = set(extraction) <= {"pets_allowed"}
        row = {"identity_key": prop["identity_key"], "block": block,
               "block_chars": len(block), "fields": sorted(extraction)}
        if len(block) <= 60 and not features and only_allowed                 and extraction.get("pets_allowed") is True:
            row["issue"] = ("the located block carries no policy feature and "
                            "reads as an amenity label, not a statement")
            flagged.append(row)
        else:
            substantive.append(row)
    return {
        "amenity_chips_read_as_policy": flagged,
        "substantive_policy_blocks": len(substantive),
        "verdict": ("AMENITY_CHIP_NOT_POLICY" if flagged
                    else "POLICY_BLOCKS_ARE_SUBSTANTIVE"),
        "why": ("publication-grade describes the EVIDENCE -- hashes, contiguous "
                "quotes, confirmed identity -- and an amenity checkbox can "
                "satisfy all three while telling a guest nothing. A lane whose "
                "successes are amenity chips has not acquired policy."),
    }


def service_animal_audit(props: List[Dict]) -> Dict:
    """Service-animal wording must not have become ordinary pet policy.

    The reader gained this rule in PTF-CHOICE-READER-AND-ROUTE-CLOSURE-005;
    this re-checks the OUTPUT rather than trusting the rule fired.
    """
    findings = {}
    for prop in props:
        extraction = prop.get("extraction") or {}
        offending = CV.refusal_carrying_pet_terms(extraction)
        if offending:
            findings[prop["identity_key"]] = offending
    return {
        "refusal_records_carrying_pet_terms": findings,
        "verdict": "SERVICE_ANIMAL_TERMS_LEAKED" if findings else "CLEAN",
    }


def duplicate_text_audit(props: List[Dict]) -> Dict:
    """Compare the four policy texts against each other, explicitly.

    Identical text is only a defect if it is BOILERPLATE -- text the property's
    own page does not support. Identical text that each page genuinely states
    is a brand standard, which is legitimate first-party evidence. The
    distinction is made the same way it was made for Wyndham: by asking whether
    the corpus varies at all.
    """
    groups: Dict[str, List[str]] = {}
    for prop in props:
        text = ((prop.get("policy_surface_result") or {}).get("excerpt") or "").strip()
        if text:
            groups.setdefault(text, []).append(prop["identity_key"])
    shared = {t: k for t, k in groups.items() if len(k) > 1}
    distinct = {json.dumps(p.get("extraction") or {}, sort_keys=True)
                for p in props if p.get("extraction")}
    all_identical = len(groups) == 1 and len(props) > 1
    return {
        "properties_sharing_identical_policy_text": {
            " / ".join(sorted(v)): len(v) for v in shared.values()},
        "distinct_policy_texts": len(groups),
        "distinct_extractions": len(distinct),
        "every_property_identical": all_identical,
        "verdict": ("BOILERPLATE_SUSPECTED" if all_identical
                    else "BRAND_STANDARD_OR_VARIED"),
        "why": ("if every property in the cohort returns the same text AND the "
                "same extraction, the lane cannot be shown to be reading the "
                "individual page, and a route must not be promoted on it. "
                "Variation anywhere in the cohort proves it reads each page."),
    }


async def main_async(args) -> Dict:
    rows = WY.subjects(BRAND)
    if len(rows) != EXPECTED_COHORT:
        raise SystemExit("ABORT: expected %d %s properties, derived %d"
                         % (EXPECTED_COHORT, BRAND, len(rows)))
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
        print("  %-44s %-30s id=%-5s policy=%-5s pub=%-5s attempts=%d"
              % (entry["property_name"][:44], entry["acquisition_result"],
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

    # Audits imported from the two decision tests before this one, plus the two
    # this brand specifically needs.
    generic = IHG.aggregate_audit(results)
    tiered = IHG.tiered_fee_audit(results)
    duplicates = duplicate_text_audit(results)
    free = free_stay_audit(results)
    service = service_animal_audit(results)
    amenity = amenity_chip_audit(results)

    systemic = list(generic["systemic_defects"])
    if amenity["verdict"] == "AMENITY_CHIP_NOT_POLICY":
        systemic.append("publication-grade was reached over an amenity label "
                        "rather than a policy statement")
    if duplicates["verdict"] == "BOILERPLATE_SUSPECTED":
        systemic.append("every property returned identical text and extraction")
    if free["verdict"] == "ZERO_FEE_INFERRED":
        systemic.append("a zero fee was inferred from a silent source")
    if service["verdict"] != "CLEAN":
        systemic.append("service-animal terms leaked into pet policy")

    pub_rate = (0.0 if not n else len(pub_ok) / n)

    # The bar exactly as this work order stated it, which is stricter than the
    # ladder the previous brands used: REJECT if fewer than the threshold reach
    # publication-grade OR if the failures show a systemic incompatibility.
    # APPROVE_WITH_LIMITATION needs a defined subset that is itself
    # trustworthy, so a systemic defect rules it out too -- a subset carved out
    # of boilerplate is not a subset.
    if pub_rate >= APPROVE_MIN_PUBLICATION_GRADE_RATE and not systemic:
        decision = "APPROVE"
    elif systemic or pub_rate < LIMITATION_MIN_PUBLICATION_GRADE_RATE:
        decision = "REJECT"
    else:
        decision = "APPROVE_WITH_LIMITATION"

    reasons = []
    if pub_rate < APPROVE_MIN_PUBLICATION_GRADE_RATE:
        reasons.append("publication-grade %d/%d is below the %d/%d bar fixed "
                       "before the run"
                       % (len(pub_ok), n,
                          round(APPROVE_MIN_PUBLICATION_GRADE_RATE * n), n))
    reasons += ["systemic defect: %s" % s for s in systemic]
    if not reasons:
        reasons.append("publication-grade %d/%d clears the %d/%d bar with no "
                       "systemic identity or policy-surface defect"
                       % (len(pub_ok), n,
                          round(APPROVE_MIN_PUBLICATION_GRADE_RATE * n), n))

    doc = {
        "schema": "ptf-brand-provider-decision/1.0",
        "work_order": WORK_ORDER,
        "market_id": MARKET,
        "brand": BRAND,
        "note": ("Firecrawl measured alone against the full remaining Milwaukee "
                 "Motel 6 cohort, through router.route_property with an "
                 "in-memory registry override. routes.json never written. The "
                 "override and the defect audits are imported from the Wyndham "
                 "and IHG decision modules, not copied."),
        "what_makes_this_brand_different": {
            "no_dedicated_reader": (
                "Motel 6 uses the ``generic`` walk. This test measures a "
                "provider and a generic reader together, so a failure could "
                "belong to either and is reported rather than attributed."),
            "incumbent_evidence_is_thin": (
                "the committed route says 'generic walk; one property "
                "measured'. n=1 is not a strong incumbent, and is also not a "
                "reason to move."),
            "pets_stay_free": (
                "this brand markets itself on pets staying free, so a record "
                "with no fee is the expected shape of BOTH a correct answer "
                "and a total extraction failure. free_stay_audit separates "
                "them."),
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
            "approve_min_records": round(APPROVE_MIN_PUBLICATION_GRADE_RATE * EXPECTED_COHORT),
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
        "defect_audit": generic,
        "tiered_fee_audit": tiered,
        "duplicate_text_audit": duplicates,
        "free_stay_audit": free,
        "service_animal_audit": service,
        "amenity_chip_audit": amenity,
        "systemic_defects": systemic,
        "decision": decision,
        "decision_reasons": reasons,
        "cost": {"firecrawl_credits": credits, "bright_data_usd": 0.0,
                 "bright_data_attempts": 0},
        "routes_changed": False,
        "authority_written": False,
        "policies_published": False,
        "total_elapsed_seconds": elapsed,
        "properties": results,
    }
    out = REPORTS / "ptf_motel6_firecrawl_decision_012.json"
    out.write_bytes((json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
                    .encode("utf-8"))
    return doc


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="motel6-decision-012")
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
    print("failures: %s" % doc["failures"]["by_class"])
    print("audits: generic=%s duplicates=%s free=%s service=%s tiered=%s"
          % (doc["defect_audit"]["verdict"], doc["duplicate_text_audit"]["verdict"],
             doc["free_stay_audit"]["verdict"], doc["service_animal_audit"]["verdict"],
             doc["tiered_fee_audit"]["verdict"]))
    print("amenity-chip audit: %s" % doc["amenity_chip_audit"]["verdict"])
    print("credits: %s" % doc["cost"]["firecrawl_credits"])
    print()
    print("DECISION: %s" % doc["decision"])
    for r in doc["decision_reasons"]:
        print("   - %s" % r)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
