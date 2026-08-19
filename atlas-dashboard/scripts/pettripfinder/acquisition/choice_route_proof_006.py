"""PTF-CHOICE-FIRECRAWL-ROUTE-APPLICATION-006 -- prove the applied Choice route.

Two things have to be true for the route change to be more than a JSON edit, and
neither can be established by inspecting the file.

CONTROL. Normal Choice traffic goes to Firecrawl, wins there, and never touches
the fallback. Run live, through ``router.route_property`` itself.

FALLBACK. When Firecrawl fails for a CHANNEL reason, the router falls through to
the Web Unlocker, which acquires the same property, through the same reader, to
the same publication-grade standard. This path has never fired end to end. It is
proved by forcing the primary lane to fail -- in this harness only, by swapping
the provider's capture module for one that returns a technical failure and makes
no request -- and then letting the real router do the rest. Nothing about
Firecrawl's credentials, adapter or route is altered, and the substitution is
undone in a ``finally`` so a crash cannot leave the registry poisoned.

What the forced failure deliberately is NOT
-------------------------------------------
It is not a source-level answer. A second provider must never be used to
re-interpret what the first one successfully read: SOURCE_CONTRADICTORY,
SOURCE_AMBIGUOUS, POLICY_NOT_FOUND and IDENTITY_MISMATCH all stop the ladder.
Those are asserted in the unit tests rather than bought with live fetches,
because they are properties of the routing rule and not of any one page.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import envelope as ENV               # noqa: E402
from scripts.pettripfinder.acquisition import firecrawl_capture as FC       # noqa: E402
from scripts.pettripfinder.acquisition import providers as PROVIDERS        # noqa: E402
from scripts.pettripfinder.acquisition import registry as REGISTRY          # noqa: E402
from scripts.pettripfinder.acquisition import router as ROUTER              # noqa: E402
from scripts.pettripfinder.acquisition import firecrawl_choice_validation_004 as CV  # noqa: E402
from scripts.pettripfinder.brightdata import corpus as CORPUS               # noqa: E402
from scripts.pettripfinder.brightdata import cross_brand_pilot_002 as P2    # noqa: E402
from scripts.pettripfinder.brightdata import outcomes as O                  # noqa: E402
from scripts.pettripfinder.brightdata import browser_capture as BC          # noqa: E402

WORK_ORDER = "PTF-CHOICE-FIRECRAWL-ROUTE-APPLICATION-006"
MARKET = "milwaukee-wi"
BRAND = "CHOICE"
REPORTS = REPO / "launch_packages" / "pettripfinder" / "markets" / "reports"
RUN_ROOT = REPO / "data" / "acquisition" / "choice-route-proof-006"

#: The control. Chosen because Firecrawl has acquired it repeatedly and it is a
#: clean refusal -- the case where a wrong answer would be most damaging.
CONTROL_KEY = "econo lodge milwaukee airport"

#: The fallback subject. Chosen because the Web Unlocker has a STABLE EXISTING
#: BENCHMARK for it: it is one of the seven the production run acquired at
#: publication grade, so a failure to reproduce here is a real signal and not an
#: unknown. Firecrawl also acquires it, which is why the failure must be forced.
FALLBACK_KEY = "comfort inn and suites nw milwaukee"


class _ForcedTechnicalFailure:
    """Stands in for the Firecrawl capture module and makes NO request.

    It returns exactly what a channel refusal looks like coming out of the real
    adapter -- ``ACCESS_DENIED`` carrying the vendor's own
    ``SCRAPE_ALL_ENGINES_FAILED`` -- so the router is exercised on the shape it
    will actually meet in production, not on a synthetic one.
    """

    def __init__(self) -> None:
        self.calls = 0

    async def capture_property(self, target, *, run_dir: Path, brand: str,
                               max_attempts: int = 3, profile=None
                               ) -> Tuple[List, Optional[Dict]]:
        records = []
        for attempt in range(1, max_attempts + 1):
            self.calls += 1
            records.append(BC.AttemptRecord(
                attempt=attempt, outcome=O.ACCESS_DENIED,
                started_at="", ended_at="", elapsed_seconds=0.0,
                requested_url=target.requested_url,
                final_url=target.requested_url, title="", body_chars=0,
                detail=("FORCED BY %s: ALL_ENGINES_FAILED: every Firecrawl "
                        "engine was refused by this origin" % WORK_ORDER)))
        return records, None


def _record_for(key: str):
    entries, _tested = CV.remaining_sample()
    known = {e["identity_key"]: e for e in entries}
    if key not in known:
        raise SystemExit("%r is not in the derived Milwaukee Choice sample" % key)
    entry = known[key]
    record = CORPUS.BenchmarkRecord(
        identity_key=entry["identity_key"], name=entry["canonical_name"],
        market_id=MARKET, brand=BRAND, bucket=CORPUS.bucket_of(BRAND),
        source_url=entry["official_url"], pets_allowed=None, facts={},
        quotes=(), withheld_fields={}, service_animal_statement="",
        categories=frozenset(), origin="census")
    return record, P2.target_for(record), entry


def _summarise(result: ENV.RoutingResult) -> Dict:
    doc = result.document
    by_provider: Dict[str, List[str]] = {}
    for attempt in result.attempts:
        by_provider.setdefault(attempt.provider, []).append(attempt.outcome)
    return {
        "identity_key": result.identity_key,
        "state": result.state,
        "route_primary": result.route["provider"],
        "route_ladder": result.route["ladder"],
        "route_reader": result.route["reader"],
        "max_attempts_per_provider": result.route["max_attempts_per_provider"],
        "forbidden_providers": result.route["forbidden_providers"],
        "providers_tried": list(result.providers_tried),
        "outcomes_by_provider": by_provider,
        "acquired_by": (doc.provider if doc is not None else None),
        "publication_grade": bool(doc is not None and doc.is_publication_grade),
        # The identity verdict lives inside the identity mapping, and is read
        # from the document rather than re-derived here: the whole point is
        # that the fallback leg cleared the SAME gate as the primary would.
        "identity_confirmed": bool(doc is not None
                                   and (doc.identity or {}).get("confirmed")),
        "identity_detail": (dict(doc.identity) if doc is not None else {}),
        "reader": (doc.reader if doc is not None else None),
        "extraction": (dict(doc.observation.get("extraction") or {})
                       if doc is not None else {}),
        "failure": result.failure,
        "failure_class": result.failure_class,
        "escalation_stopped_because": result.escalation_stopped_because,
        "cost": result.cost.to_dict(),
        "brightdata_browser_calls": len(by_provider.get("brightdata_browser", [])),
    }


async def run_control(run_dir: Path) -> Dict:
    """Normal traffic: Firecrawl wins, fallback never invoked."""
    record, target, _entry = _record_for(CONTROL_KEY)
    began = time.monotonic()
    result = await ROUTER.route_property(
        record, target, run_dir=run_dir / "control", run_id="route-proof-006-control")
    out = _summarise(result)
    out["elapsed_seconds"] = round(time.monotonic() - began, 1)
    out["fallback_invoked"] = result.cost.fallback_invoked
    out["pass"] = bool(
        out["route_primary"] == "firecrawl"
        and out["acquired_by"] == "firecrawl"
        and out["publication_grade"]
        and not out["fallback_invoked"]
        and out["brightdata_browser_calls"] == 0
        and len(out["outcomes_by_provider"].get("firecrawl", [])) <= 3)
    return out


async def run_forced_fallback(run_dir: Path) -> Dict:
    """Force the primary to fail for a CHANNEL reason, then let the router run."""
    record, target, _entry = _record_for(FALLBACK_KEY)
    provider = PROVIDERS.get("firecrawl")
    stub = _ForcedTechnicalFailure()

    # Swap the capture module only, on the registered provider object, and put
    # it back whatever happens. Credentials, adapter and route are untouched.
    original = provider.module
    object.__setattr__(provider, "module", stub)
    began = time.monotonic()
    try:
        result = await ROUTER.route_property(
            record, target, run_dir=run_dir / "forced-fallback",
            run_id="route-proof-006-fallback")
    finally:
        object.__setattr__(provider, "module", original)
        assert PROVIDERS.get("firecrawl").module is FC

    out = _summarise(result)
    out["elapsed_seconds"] = round(time.monotonic() - began, 1)
    out["forced_primary_failure"] = ("ACCESS_DENIED / ALL_ENGINES_FAILED, "
                                     "injected in the harness; no request made")
    out["forced_primary_calls"] = stub.calls
    out["fallback_invoked"] = result.cost.fallback_invoked
    out["pass"] = bool(
        out["route_primary"] == "firecrawl"
        and out["providers_tried"][:1] == ["firecrawl"]
        and "brightdata_web_unlocker" in out["providers_tried"]
        and out["fallback_invoked"]
        and out["acquired_by"] == "brightdata_web_unlocker"
        and out["publication_grade"]
        and out["identity_confirmed"]
        and out["reader"] == "choice_static"
        and out["brightdata_browser_calls"] == 0)
    return out


async def main_async(args) -> Dict:
    run_dir = RUN_ROOT / args.run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    credits_before = FC.credits_remaining()
    control = await run_control(run_dir) if not args.skip_control else None
    fallback = await run_forced_fallback(run_dir) if not args.skip_fallback else None
    credits_after = FC.credits_remaining()

    route = REGISTRY.resolve(
        brand=BRAND,
        url="https://www.choicehotels.com/wisconsin/milwaukee/econo-lodge-hotels/wi423")
    others = {b: REGISTRY.resolve(brand=b, url="https://example.com/x").provider
              for b in ("MARRIOTT", "HILTON", "IHG", "WYNDHAM")}

    doc = {
        "schema": "ptf-choice-route-proof/1.0",
        "work_order": WORK_ORDER,
        "market_id": MARKET,
        "brand": BRAND,
        "note": ("Both proofs run through router.route_property itself, against "
                 "the applied route table. The forced failure replaces the "
                 "registered Firecrawl provider's capture module inside this "
                 "harness only and restores it in a finally block; no "
                 "credential, adapter or route is altered."),
        "applied_route": route.to_dict(),
        "other_brand_primaries": others,
        "firecrawl_registered": "firecrawl" in PROVIDERS.all_ids(),
        "normal_control": control,
        "forced_fallback": fallback,
        "firecrawl_credits": {
            "before": credits_before, "after": credits_after,
            "measured": (None if credits_before is None or credits_after is None
                         else credits_before - credits_after),
            "note": ("plan credits only. Bright Data's usage on the fallback "
                     "leg is billed in dollars and is reported separately by "
                     "the router; the two are never summed."),
        },
        "authority_written": False,
        "policies_published": False,
    }
    checks = [c for c in (control, fallback) if c is not None]
    doc["status"] = ("PASS" if checks and all(c["pass"] for c in checks)
                     else "FAIL" if checks else "NOT_RUN")
    out = REPORTS / "ptf_choice_route_proof_006.json"
    out.write_bytes((json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
                    .encode("utf-8"))
    return doc


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="route-proof-006")
    parser.add_argument("--skip-control", action="store_true")
    parser.add_argument("--skip-fallback", action="store_true")
    args = parser.parse_args(argv)

    doc = asyncio.run(main_async(args))
    for name in ("normal_control", "forced_fallback"):
        section = doc.get(name)
        if not section:
            continue
        print()
        print("%s: %s" % (name.upper(), "PASS" if section["pass"] else "FAIL"))
        print("  providers tried : %s" % section["providers_tried"])
        print("  outcomes        : %s" % section["outcomes_by_provider"])
        print("  acquired by     : %s" % section["acquired_by"])
        print("  publication grade: %s | identity: %s | reader: %s"
              % (section["publication_grade"], section["identity_confirmed"],
                 section["reader"]))
        print("  fallback invoked: %s" % section["fallback_invoked"])
        print("  browser calls   : %d" % section["brightdata_browser_calls"])
        print("  state           : %s" % section["state"])
    print()
    print("STATUS: %s" % doc["status"])
    return 0 if doc["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
