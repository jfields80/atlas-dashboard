"""PTF-ST-LOUIS-MARKET-001 -- measure the ``direct_http`` lane over a market.

A route is added to ``routes.json`` by a benchmark, never by an opinion. This
is that benchmark for the lane ``providers.DIRECT_HTTP`` reserved and
``direct_http_capture`` now implements: it runs the free lane over a routed
census, records one outcome per property from the closed vocabulary, and
reports per-brand reach so a route decision has a measurement behind it.

    python scripts/pettripfinder/acquisition/direct_http_pilot.py \
      --market st-louis-mo --limit 0 --brands ALL \
      --run-dir data/acquisition/st_louis_direct_http_001

It costs nothing. It is still capped: ``--limit`` bounds the number of
properties and ``--max-attempts`` bounds the fetches per property, because an
unbounded loop against somebody else's origin is rude whoever is paying.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.acquisition import direct_http_capture as DH
from scripts.pettripfinder.acquisition import market_routing as MR
from scripts.pettripfinder.acquisition import readers as READERS
from scripts.pettripfinder.brightdata import browser_capture as BC
from scripts.pettripfinder.brightdata import declined_capture as DECLINED
from scripts.pettripfinder.brightdata import outcomes as O

CENSUS_DIR = _REPO_ROOT / "launch_packages" / "pettripfinder" / "identity_census"

#: Brands measured, at one probe each, to REFUSE this lane outright. Skipping
#: them is not an assumption: it is the 2026-08-23 probe recorded in
#: direct_http_capture's docstring, and re-running it 100 times would produce
#: 100 more 403s and 100 more timeouts at somebody else's expense.
LANE_REFUSED_BRANDS = OrderedDict((
    ("MARRIOTT", "HTTP 403 at the edge on both probes"),
    ("HILTON", "HTTP 403 at the edge on both probes"),
    ("IHG", "HTTP 403 at the edge on both probes"),
    ("RED_ROOF", "HTTP 403 at the edge on both probes"),
    ("CHOICE", "no response inside 25s on both probes"),
    ("MOTEL6", "no response inside 25s on both probes"),
))


def _slug(identity_key: str) -> str:
    return identity_key.replace(" ", "-").replace("/", "-")[:80]


def target_for(row, entry) -> BC.CaptureTarget:
    return BC.CaptureTarget(
        slug=_slug(row["identity_key"]),
        hotel=row["canonical_name"],
        requested_url=entry["source_url"],
        property_code="",
        market_id=row["market_id"],
        normalized_name=row.get("normalized_name", "") or row["identity_key"],
        identity_key=row["identity_key"],
        expected_postal_code=row.get("postal_code", "") or "",
        expected_street=row.get("address", "") or "",
        expected_phone=row.get("phone", "") or "",
        expected_locality=", ".join(
            x for x in (row.get("city", ""), row.get("state", "")) if x),
        identity_brand=entry["brand"] if not entry["brand"].startswith("INDEP:") else "",
    )


async def run(rows, entries, *, run_dir: Path, max_attempts: int, limit: int,
              brands: str):
    by_key = {r["identity_key"]: r for r in rows}
    queue = []
    skipped = []
    for entry in entries:
        if entry["routing_state"] != MR.ROUTED:
            continue
        brand = entry["brand"]
        family = "INDEPENDENT" if brand.startswith("INDEP:") else brand
        if brands not in ("ALL", "") and family not in brands.split(","):
            continue
        if family in LANE_REFUSED_BRANDS:
            skipped.append((entry, LANE_REFUSED_BRANDS[family]))
            continue
        queue.append(entry)
    if limit:
        queue = queue[:limit]

    results = []
    for index, entry in enumerate(queue, 1):
        row = by_key[entry["identity_key"]]
        target = target_for(row, entry)
        records, payload = await DH.capture_property(
            target, run_dir=run_dir,
            brand=READERS.locator_brand_for(entry.get("reader", "generic")),
            max_attempts=max_attempts)
        final = records[-1]
        # Where the decline preserved its document, when the outcome is one the
        # declined-capture contract keeps. Derived rather than returned, because
        # AttemptRecord is a frozen contract and widening it to carry a path
        # would change an artifact five markets already read.
        declined_dir = None
        for record in records:
            candidate = (run_dir / target.slug
                         / ("declined-%02d" % record.attempt))
            if (record.outcome in DECLINED.KEEPABLE_OUTCOMES
                    and (candidate / DECLINED.DECLINED_ARTIFACT).is_file()):
                declined_dir = candidate
        results.append(OrderedDict((
            ("identity_key", entry["identity_key"]),
            ("canonical_name", entry["canonical_name"]),
            ("brand", entry["brand"]),
            ("corridor", entry["corridor"]),
            ("source_url", entry["source_url"]),
            ("outcome", final.outcome),
            ("attempts", len(records)),
            ("final_url", final.final_url),
            ("title", final.title),
            ("body_chars", final.body_chars),
            ("detail", final.detail[:400]),
            ("identity_confirmed",
             bool((final.identity or {}).get("confirmed"))),
            ("identity_reasons", list((final.identity or {}).get("reasons") or ())),
            ("artifact_dir", final.artifact_dir),
            ("declined_dir", str(declined_dir) if declined_dir else ""),
            ("bytes_received", sum(int((r.network or {}).get("encoded_bytes") or 0)
                                   for r in records)),
            ("elapsed_seconds", round(sum(r.elapsed_seconds for r in records), 2)),
            ("policy_block", (payload["reading"].block_text[:4000]
                              if payload else "")),
            ("locator_strategy", (payload["surface"].strategy if payload else "")),
        )))
        print("[%3d/%3d] %-14s %-22s %s" % (
            index, len(queue), final.outcome[:14],
            (entry["brand"][:22] if not entry["brand"].startswith("INDEP:")
             else "INDEPENDENT"),
            entry["canonical_name"][:52]), flush=True)
    return results, skipped


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--market", required=True)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--brands", default="ALL")
    parser.add_argument("--max-attempts", type=int, default=DH.DEFAULT_MAX_ATTEMPTS)
    args = parser.parse_args(argv)

    census = json.loads((CENSUS_DIR / ("%s.json" % args.market))
                        .read_text(encoding="utf-8"))
    entries, summary = MR.route_census(census["hotels"])

    run_dir = Path(args.run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    results, skipped = asyncio.run(run(
        census["hotels"], entries, run_dir=run_dir,
        max_attempts=args.max_attempts, limit=args.limit, brands=args.brands))

    outcomes = Counter(r["outcome"] for r in results)
    by_brand = OrderedDict()
    for row in results:
        family = ("INDEPENDENT" if row["brand"].startswith("INDEP:")
                  else row["brand"])
        bucket = by_brand.setdefault(family, Counter())
        bucket[row["outcome"]] += 1

    document = OrderedDict((
        ("schema", "ptf-direct-http-pilot/1.0"),
        ("what_this_is",
         "A measurement of the free direct_http lane over a routed market "
         "census. It is evidence for a routing decision; it is not itself a "
         "routing decision, and it changes no route."),
        ("market_id", args.market),
        ("work_order", "PTF-ST-LOUIS-MARKET-001"),
        ("provider", DH.PROVIDER),
        ("provider_id", DH.PROVIDER_ID),
        ("usd_spent", 0.0),
        ("routing_summary", summary),
        ("attempted", len(results)),
        ("outcome_counts", OrderedDict(sorted(outcomes.items()))),
        ("outcomes_by_brand", OrderedDict(
            (brand, OrderedDict(sorted(counts.items())))
            for brand, counts in sorted(by_brand.items()))),
        ("valid", outcomes.get(O.VALID, 0)),
        ("bytes_received", sum(r["bytes_received"] for r in results)),
        ("elapsed_seconds", round(sum(r["elapsed_seconds"] for r in results), 1)),
        ("lane_refused_brands", LANE_REFUSED_BRANDS),
        ("skipped_lane_refused", [
            OrderedDict((("identity_key", e["identity_key"]),
                         ("brand", e["brand"]), ("why", why)))
            for e, why in skipped]),
        ("results", results),
    ))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(document, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    print()
    print("attempted : %d" % len(results))
    print("outcomes  : %s" % dict(sorted(outcomes.items())))
    print("skipped   : %d (lane measured to be refused by the brand)" % len(skipped))
    print("spend     : $0.00")
    print("written   : %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
