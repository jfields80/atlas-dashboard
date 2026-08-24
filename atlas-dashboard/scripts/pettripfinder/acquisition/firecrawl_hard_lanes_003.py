"""PTF-FIRECRAWL-HARD-LANES-003 -- the Marriott / Hilton / Choice decision test.

Benchmark-002 measured Firecrawl on lanes Spider could reach. Those were the
easy ones. This is the decision test on the three that actually carry Milwaukee:
Marriott, Hilton and Choice -- 55 of the 127 queued properties, and the three
that defeated every cheap provider so far.

Ten properties chosen against stated criteria, not for being winnable
--------------------------------------------------------------------
Four Marriott (a seven-field fee/weight/count case, a species case, a
single-field minimal case, and the JS-heavy Aloft overview), three Hilton (the
richest table case, a detailed case, and a single-field minimal case), three
Choice (the richest structured case, the Country Inn / Radisson lane that
ACCESS_DENIED three times under the Web Unlocker, and a captured NO-PETS
refusal). The single-field baselines are in deliberately: they are the hardest
to agree with, because there is nothing to hide a disagreement behind.

Three gates, in order, and HTTP 200 clears none of them
-------------------------------------------------------
1. IDENTITY. The property's own page or nothing. A generic brand page and a
   sibling property both fail, via the same assessor the proven lanes use.
2. HYDRATION. Wyndham already proved a 176KB HTTP 200 can arrive with the
   policy node absent. So the branded policy container must be PRESENT, and a
   page carrying only a policy heading with no policy content is
   POLICY_SURFACE_INCOMPLETE -- not a success, however publication-grade its
   evidence technically is.
3. AGREEMENT. Against the committed Bright Data extraction, field by field.

Why the structured/free-text split is an explicit list here
-----------------------------------------------------------
Benchmark-002 classified a mismatch as cosmetic when both sides were strings.
That is wrong and it is dangerous: ``fee_basis`` is a string, and "per_night"
against "per_stay" is a factual disagreement that would misprice a guest's stay.
The split is now an explicit membership test, and anything unrecognised is
treated as STRUCTURED -- the fail-safe direction.

Nothing here writes authority, publishes, or edits routes.json.
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
from typing import Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import firecrawl_capture as FIRECRAWL  # noqa: E402
from scripts.pettripfinder.acquisition import journal as JOURNAL             # noqa: E402
from scripts.pettripfinder.acquisition import readers as READERS             # noqa: E402
from scripts.pettripfinder.acquisition.spider_benchmark_001 import (          # noqa: E402
    baseline_rows, compare, _extraction,
)
from scripts.pettripfinder.brightdata import corpus as CORPUS                # noqa: E402
from scripts.pettripfinder.brightdata import cross_brand_pilot_002 as P2     # noqa: E402
from scripts.pettripfinder.brightdata import policy_surface as PS            # noqa: E402
from scripts.pettripfinder.brightdata import publication_grade as PG         # noqa: E402

MARKET = "milwaukee-wi"
WORK_ORDER = "PTF-FIRECRAWL-HARD-LANES-003"
PKG = REPO / "launch_packages" / "pettripfinder"
REPORTS = PKG / "markets" / "reports"
RUN_ROOT = REPO / "data" / "acquisition" / "firecrawl-hard-lanes-003"

# --------------------------------------------------------------------------- #
# The sample. Chosen against the criteria, recorded with the reason, so nobody
# has to take "not unusually easy" on trust.
# --------------------------------------------------------------------------- #

SAMPLE: Tuple[Tuple[str, str, str], ...] = (
    ("MARRIOTT", "fairfield by marriott inn and suites milwaukee downtown",
     "detailed: fee amount, basis, currency, weight, count and scope (7 fields)"),
    ("MARRIOTT", "four points by sheraton milwaukee north shore",
     "detailed with species_allowed (7 fields)"),
    ("MARRIOTT", "courtyard by marriott milwaukee airport",
     "minimal: the baseline extracted pets_allowed and nothing else"),
    ("MARRIOTT", "aloft by marriott milwaukee downtown",
     "historically dynamic: JS-heavy overview surface"),

    ("HILTON", "embassy suites by hilton milwaukee brookfield",
     "table-style, richest Hilton baseline (6 fields incl. species and weight)"),
    ("HILTON", "hilton garden inn milwaukee airport",
     "detailed (6 fields)"),
    ("HILTON", "doubletree by hilton hotel milwaukee downtown",
     "minimal: the baseline extracted pets_allowed and nothing else"),

    ("CHOICE", "comfort suites milwaukee west",
     "richest structured Choice baseline (9 fields incl. fee scope and count scope)"),
    ("CHOICE", "country inn and suites by radisson germantown wi",
     "the Radisson sub-brand; three siblings ACCESS_DENIED under the Web Unlocker"),
    ("CHOICE", "cambria hotel milwaukee downtown",
     "a captured NO-PETS refusal: the case where a wrong answer is worst"),
)

# --------------------------------------------------------------------------- #
# Field classification. Explicit, because the type of a value does not tell you
# whether disagreeing about it misleads a guest.
# --------------------------------------------------------------------------- #

STRUCTURED_FIELDS = frozenset({
    "pets_allowed", "pet_fee", "fee_amount", "fee_basis", "fee_scope",
    "fee_currency", "fee_cap", "weight_limit", "combined_weight_limit",
    "weight_scope", "pet_count_limit", "pet_count_scope", "species_allowed",
    "species", "refundable", "deposit", "cleaning_fee", "other_charges",
    "reservation_required", "dimension_limit",
})

FREE_TEXT_FIELDS = frozenset({
    "service_animal_exception", "service_animal_statement", "policy_text",
    "notes", "other_information",
})

#: The facts §8 forbids getting wrong.
ZERO_WRONG_FACT_FIELDS = ("pets_allowed", "pet_fee", "fee_basis", "fee_scope",
                          "weight_limit", "pet_count_limit", "species_allowed",
                          "refundable")


def classify(mismatches: Dict) -> Dict:
    """STRUCTURED_MISMATCH versus TEXT_EXCERPT_VARIANT, by membership.

    An unrecognised field counts as STRUCTURED. A new field that nobody
    classified should make this test fail loudly rather than pass quietly.
    """
    structured, textual, unknown = {}, {}, []
    for field, sides in mismatches.items():
        if field in FREE_TEXT_FIELDS:
            textual[field] = sides
        else:
            structured[field] = sides
            if field not in STRUCTURED_FIELDS:
                unknown.append(field)
    return {"structured_mismatches": structured,
            "text_excerpt_variants": textual,
            "unclassified_fields_treated_as_structured": sorted(unknown)}


def false_facts(base: Dict, got: Dict) -> Dict:
    """The specific wrong answers §8 disqualifies on."""
    out: Dict[str, bool] = {}
    b, g = base.get("pets_allowed"), got.get("pets_allowed")
    out["false_pets_allowed"] = (b is False and g is True)
    out["false_no_pets"] = (b is True and g is False)
    for name, field in (("false_fee", "pet_fee"), ("false_weight", "weight_limit"),
                        ("false_species", "species_allowed")):
        out[name] = (field in base and field in got and base[field] != got[field])
    return out


# --------------------------------------------------------------------------- #
# The hydration gate.
# --------------------------------------------------------------------------- #

_HEADING_ONLY = re.compile(r"pet\s*(&|and)?\s*(service\s*animal\s*)?polic",
                           re.IGNORECASE)


def policy_surface_state(html: str, *, brand_locator: str,
                         block_text: str) -> Tuple[str, str]:
    """Is the policy-bearing surface actually here?

    Returns ``(state, detail)``. HTTP 200 is not consulted: a shell answers 200.
    """
    if not html:
        return "ABSENT", "no document"

    container = False
    for _name, selector in PS.BRAND_LOCATORS.get(brand_locator, ()):  # type: ignore[arg-type]
        for token in re.findall(r"\[([a-zA-Z-]+)\*?=", selector):
            if re.search(r"%s\s*=\s*[\"'][^\"']*pet" % re.escape(token), html,
                         re.IGNORECASE):
                container = True
                break
        if container:
            break
    if not container:
        container = bool(re.search(r"(class|id|data-testid)\s*=\s*[\"'][^\"']*pet",
                                   html, re.IGNORECASE))

    collapsed = " ".join((block_text or "").split())
    if not collapsed:
        return ("CONTAINER_PRESENT_NO_TEXT" if container else "ABSENT",
                "no bounded policy text was located")

    # A heading and nothing else is the failure Wyndham taught us to name.
    without_heading = _HEADING_ONLY.sub("", collapsed).strip(" -:–")
    if len(without_heading) < 25:
        return "HEADING_ONLY", ("the located block is a policy HEADING with no "
                                "policy content: %r" % collapsed[:80])
    return ("HYDRATED" if container else "TEXT_WITHOUT_BRAND_CONTAINER",
            "%d characters of policy text%s"
            % (len(collapsed), "" if container else
               "; the branded container was not found, so the text was reached "
               "by the generic walk"))


# --------------------------------------------------------------------------- #
# Deterministic interaction, used only when a plain scrape is incomplete.
# --------------------------------------------------------------------------- #

INTERACT_PROFILE: Dict = {
    "formats": ["rawHtml"],
    "waitFor": 6000,
    "timeout": 120000,
    "location": {"country": "US"},
    "actions": [
        {"type": "wait", "milliseconds": 3000},
        {"type": "scroll", "direction": "down"},
        {"type": "wait", "milliseconds": 1500},
        {"type": "scroll", "direction": "down"},
        {"type": "executeJavascript",
         # Deterministic, not prompt-driven: open every native disclosure and
         # click anything whose own text names a pet policy. No model decides
         # what to click.
         "script": (
             "document.querySelectorAll('details').forEach(d=>d.open=true);"
             "Array.from(document.querySelectorAll("
             "  'button,a,[role=button],summary')).filter(e=>"
             "  /pet/i.test(e.textContent||'')).slice(0,8)"
             "  .forEach(e=>{try{e.click()}catch(_){}});"
             "'ok'")},
        {"type": "wait", "milliseconds": 3000},
    ],
}

#: The adapter's own definition, not a copy of it. PTF-CHOICE-FIRECRAWL-ROUTE-
#: APPLICATION-006 registered Firecrawl as a routable provider using this exact
#: profile, and a second copy here would let the benchmark and the production
#: lane drift apart without either file changing.
SCRAPE_PROFILE: Dict = FIRECRAWL.ROUTED_PROFILE


async def acquire(entry: Dict, *, run_dir: Path, pace: float,
                  run_id: str = "firecrawl-hard-lanes-003",
                  ref_tag: str = "fc3", max_attempts: int = 2) -> Dict:
    """Plain scrape first; deterministic interaction only if it is incomplete.

    ``run_id`` and ``ref_tag`` exist so a later work order can reuse this exact
    acquisition path -- same profiles, same three gates, same comparison -- and
    still stamp its own provenance onto the evidence it produces, and
    ``max_attempts`` so a later work order can test whether a failure was
    intermittent without forking the acquisition path to do it. The defaults
    reproduce PTF-FIRECRAWL-HARD-LANES-003 unchanged.
    """
    record = CORPUS.BenchmarkRecord(
        identity_key=entry["identity_key"], name=entry["canonical_name"],
        market_id=MARKET, brand=entry["brand"],
        bucket=CORPUS.bucket_of(entry["brand"]), source_url=entry["official_url"],
        pets_allowed=None, facts={}, quotes=(), withheld_fields={},
        service_animal_statement="", categories=frozenset(), origin="census")
    target = P2.target_for(record)
    reader_id = entry.get("reader") or "generic"
    brand_locator = READERS.locator_brand_for(reader_id)
    base = _extraction(entry)

    out: Dict = {
        "identity_key": entry["identity_key"],
        "canonical_name": entry["canonical_name"],
        "reader": reader_id,
        "url": entry["official_url"],
        "bright_data_field_count": len(base),
        "bright_data_elapsed_seconds": entry.get("elapsed_seconds"),
        "bright_data_extraction": base,
        "scrape_calls": 0,
        "interact_calls": 0,
    }

    began = time.monotonic()
    payload = None
    attempts_all: List = []
    for mode, profile in (("scrape", SCRAPE_PROFILE), ("interact", INTERACT_PROFILE)):
        attempts, payload = await FIRECRAWL.capture_property(
            target, run_dir=run_dir / mode, brand=brand_locator,
            max_attempts=max_attempts, profile=profile)
        attempts_all.extend(attempts)
        out["%s_calls" % mode] = len(attempts)
        if payload is not None:
            surface_state, surface_detail = policy_surface_state(
                (payload["artifacts"].get("files") or {}) and _read_html(payload),
                brand_locator=brand_locator,
                block_text=payload["reading"].block_text)
            out["mode_used"] = mode
            out["surface_state"] = surface_state
            out["surface_detail"] = surface_detail
            if surface_state in ("HYDRATED", "TEXT_WITHOUT_BRAND_CONTAINER"):
                break
        if mode == "scrape":
            # No interaction pass when the vendor says every engine was
            # refused: there is no page to interact with, and a second call
            # spends a credit to be told the same thing.
            if any("ALL_ENGINES_FAILED" in (a.detail or "") for a in attempts):
                out["interaction_skipped"] = (
                    "the scrape returned SCRAPE_ALL_ENGINES_FAILED; interaction "
                    "cannot reach a page that never arrived")
                break
            await asyncio.sleep(pace)
    out["firecrawl_elapsed_seconds"] = round(time.monotonic() - began, 1)
    out["firecrawl_outcome"] = attempts_all[-1].outcome if attempts_all else "NO_ATTEMPT"

    if payload is None:
        out.update({"firecrawl_state": "NOT_ACQUIRED",
                    "firecrawl_failure": attempts_all[-1].detail if attempts_all else "",
                    "surface_state": out.get("surface_state", "ABSENT"),
                    "firecrawl_field_count": 0, "complete": False})
        return out

    last = attempts_all[-1]
    observation, _res = P2.build_observation(record, target, last, payload,
                                             run_id=run_id)
    grade = PG.assess(
        evidence_items=observation["evidence"], extraction=observation["extraction"],
        source_url=observation["source_url"], captured_at=last.started_at,
        ref_prefix="%s::%s" % (ref_tag, record.identity_key),
        artifact_path=P2._artifact_path(payload["artifacts"], PG.PRIMARY_ARTIFACT),
        recorded_sha256=str(((payload["artifacts"].get("files") or {})
                             .get(PG.PRIMARY_ARTIFACT) or {}).get("sha256") or ""),
        page_text_path=P2._artifact_path(payload["artifacts"], "page-text.txt"),
        identity_confirmed=bool((last.identity or {}).get("confirmed")))

    got = dict(observation["extraction"])
    comparison = compare(base, got)
    comparison.update(classify(comparison["mismatches"]))
    wrong = false_facts(base, got)

    # §6: publication-grade evidence over a heading is still not a policy.
    complete = (out.get("surface_state") in ("HYDRATED", "TEXT_WITHOUT_BRAND_CONTAINER")
                and not comparison["structured_mismatches"]
                and not comparison["counts"].get("MISSING"))

    out.update({
        "firecrawl_state": ("ACQUIRED_PUBLICATION_GRADE" if grade.confirmed
                            else "ACQUIRED_NONPUBLICATION_GRADE"),
        "publication_grade_verdict": grade.to_dict().get("verdict", ""),
        "firecrawl_field_count": len(got),
        "firecrawl_extraction": got,
        "comparison": comparison,
        "false_facts": wrong,
        "complete": bool(complete),
        "identity_confirmed": bool((last.identity or {}).get("confirmed")),
    })
    return out


def _read_html(payload: Dict) -> str:
    path = ((payload["artifacts"].get("files") or {}).get("rendered.html") or {}).get("path")
    if not path:
        return ""
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


# --------------------------------------------------------------------------- #

async def main_async(args) -> Dict:
    wanted = {key: (brand, why) for brand, key, why in SAMPLE}
    rows = {r["identity_key"]: r for r in baseline_rows(None)}
    missing = [k for k in wanted if k not in rows]
    if missing:
        raise SystemExit("no baseline for: %s" % missing)

    run_dir = RUN_ROOT / args.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    journal = JOURNAL.Journal(path=run_dir / "journal.jsonl")
    done = journal.completed_keys() if not args.no_resume else set()

    credits_before = FIRECRAWL.credits_remaining()
    started = time.monotonic()

    for brand, key, why in SAMPLE:
        if key in done:
            continue
        result = await acquire(rows[key], run_dir=run_dir, pace=args.pace)
        result["brand"] = brand
        result["selection_reason"] = why
        journal.append(result)          # durable before the next property
        print("  %-9s %-44s %-28s %-26s fields %d->%d"
              % (brand, result["canonical_name"][:44],
                 result.get("firecrawl_state", "?"),
                 result.get("surface_state", "?"),
                 result["bright_data_field_count"],
                 result.get("firecrawl_field_count", 0)), flush=True)
        await asyncio.sleep(args.pace)

    credits_after = FIRECRAWL.credits_remaining()
    results = [journal.read()[k] for k in journal.read()]
    results = sorted(results, key=lambda r: (r.get("brand", ""), r["identity_key"]))

    def bucket(name: str) -> Dict:
        rows_b = [r for r in results if r.get("brand") == name]
        compared = [r for r in rows_b if "comparison" in r]
        verdicts: Counter = Counter()
        for r in compared:
            verdicts.update(r["comparison"]["counts"])
        times = [r["firecrawl_elapsed_seconds"] for r in rows_b
                 if r.get("firecrawl_elapsed_seconds")]
        return {
            "total": len(rows_b),
            "acquired": sum(1 for r in rows_b
                            if str(r.get("firecrawl_state", "")).startswith("ACQUIRED")),
            "publication_grade": sum(
                1 for r in rows_b
                if r.get("firecrawl_state") == "ACQUIRED_PUBLICATION_GRADE"),
            "complete": sum(1 for r in rows_b if r.get("complete")),
            "match": verdicts.get("MATCH", 0),
            "extra": verdicts.get("EXTRA", 0),
            "missing": verdicts.get("MISSING", 0),
            "structured_mismatch": sum(
                len(r["comparison"]["structured_mismatches"]) for r in compared),
            "text_excerpt_variant": sum(
                len(r["comparison"]["text_excerpt_variants"]) for r in compared),
            "avg_seconds": round(statistics.mean(times), 1) if times else None,
            "scrape_calls": sum(r.get("scrape_calls", 0) for r in rows_b),
            "interact_calls": sum(r.get("interact_calls", 0) for r in rows_b),
            "surface_states": dict(Counter(r.get("surface_state", "?") for r in rows_b)),
        }

    brands = {name: bucket(name) for name in ("MARRIOTT", "HILTON", "CHOICE")}
    all_times = [r["firecrawl_elapsed_seconds"] for r in results
                 if r.get("firecrawl_elapsed_seconds")]
    wrong_totals = Counter()
    for r in results:
        for k, v in (r.get("false_facts") or {}).items():
            if v:
                wrong_totals[k] += 1
    structured_total = sum(b["structured_mismatch"] for b in brands.values())
    unclassified = sorted({f for r in results
                           for f in (r.get("comparison") or {})
                           .get("unclassified_fields_treated_as_structured", [])})

    doc = {
        "schema": "ptf-firecrawl-hard-lanes/1.0",
        "work_order": WORK_ORDER,
        "market_id": MARKET,
        "note": ("Decision test on the three lanes that carry Milwaukee. Same "
                 "readers, same gates, same comparison vocabulary as "
                 "PTF-SPIDER-BENCHMARK-001 and PTF-FIRECRAWL-BENCHMARK-002. "
                 "routes.json untouched, Firecrawl still unrouted, no authority "
                 "written."),
        "sample": [{"brand": b, "identity_key": k, "selection_reason": w}
                   for b, k, w in SAMPLE],
        "total": len(results),
        "by_brand": brands,
        "overall": {
            "acquired": sum(b["acquired"] for b in brands.values()),
            "publication_grade": sum(b["publication_grade"] for b in brands.values()),
            "complete": sum(b["complete"] for b in brands.values()),
            "structured_mismatch": structured_total,
            "text_excerpt_variant": sum(b["text_excerpt_variant"] for b in brands.values()),
            "false_pets_allowed": wrong_totals.get("false_pets_allowed", 0),
            "false_no_pets": wrong_totals.get("false_no_pets", 0),
            "false_fee": wrong_totals.get("false_fee", 0),
            "false_weight": wrong_totals.get("false_weight", 0),
            "false_species": wrong_totals.get("false_species", 0),
            "unclassified_fields_treated_as_structured": unclassified,
            "avg_seconds": round(statistics.mean(all_times), 1) if all_times else None,
            "median_seconds": round(statistics.median(all_times), 1) if all_times else None,
            "p95_seconds": (round(sorted(all_times)[max(0, int(len(all_times) * 0.95) - 1)], 1)
                            if all_times else None),
        },
        "cost": {
            "credits_before": credits_before,
            "credits_after": credits_after,
            "total_credits": ((credits_before - credits_after)
                              if credits_before is not None and credits_after is not None
                              else None),
            "scrape_calls": sum(b["scrape_calls"] for b in brands.values()),
            "interact_calls": sum(b["interact_calls"] for b in brands.values()),
            "avg_credits_per_property": None,
            "dollar_conversion": ("not derivable: the plan endpoint reports "
                                  "credits and a monthly allowance, not a unit "
                                  "price, so no dollar figure is asserted"),
            "bright_data_usd_per_attempted_property": 0.197,
            "bright_data_usd_per_publication_grade_record": 0.228,
        },
        "bright_data_comparison": {
            "avg_seconds": round(statistics.mean(
                [r["bright_data_elapsed_seconds"] for r in results
                 if r.get("bright_data_elapsed_seconds")]), 1) if results else None,
        },
        "authority_written": False,
        "routes_changed": False,
        "items": results,
    }
    total_credits = doc["cost"]["total_credits"]
    if total_credits is not None and results:
        doc["cost"]["avg_credits_per_property"] = round(total_credits / len(results), 2)
    doc["total_elapsed_seconds"] = round(time.monotonic() - started, 1)

    out = REPORTS / "ptf_firecrawl_hard_lanes_003.json"
    out.write_bytes((json.dumps(doc, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
    return doc


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="hard-lanes-003")
    parser.add_argument("--pace", type=float, default=8.0)
    parser.add_argument("--no-resume", action="store_true")
    args = parser.parse_args(argv)

    if not FIRECRAWL.credential_present():
        print("%s is not set" % FIRECRAWL.KEY_ENV)
        return 2

    doc = asyncio.run(main_async(args))
    o = doc["overall"]
    print()
    for name, b in doc["by_brand"].items():
        print("%-9s %d/%d acquired | pub %d | complete %d | struct-mismatch %d "
              "| %ss | surfaces %s"
              % (name, b["acquired"], b["total"], b["publication_grade"],
                 b["complete"], b["structured_mismatch"], b["avg_seconds"],
                 b["surface_states"]))
    print()
    print("OVERALL acquired %d/%d | pub-grade %d | complete %d"
          % (o["acquired"], doc["total"], o["publication_grade"], o["complete"]))
    print("STRUCTURED_MISMATCH %d | false pets_allowed %d | false no_pets %d"
          % (o["structured_mismatch"], o["false_pets_allowed"], o["false_no_pets"]))
    print("credits %s (scrape %d, interact %d) | %ss avg vs %ss bright data"
          % (doc["cost"]["total_credits"], doc["cost"]["scrape_calls"],
             doc["cost"]["interact_calls"], o["avg_seconds"],
             doc["bright_data_comparison"]["avg_seconds"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
