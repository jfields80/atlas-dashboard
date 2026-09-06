"""PTF-LEXINGTON-KY-NEW-MARKET-001 -- phase 4A/4B, the free OSM lodging census.

Runs the committed discovery factory over `config/lexington_ky.json` with the
OpenStreetMap provider only. No paid provider is constructed and no paid
category is asked for: the categories are lodging alone.

The three `observed-` fringe cells are queried like any other cell. They are in
the plan so this order MEASURES Georgetown, Nicholasville and Versailles rather
than assuming them; `included_municipalities` names Lexington alone, so market
membership will still put everything they return outside the market.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery.runner import RunConfig, execute_run

MARKET_ID = "lexington-ky"
LODGING_CATEGORIES = (C.CATEGORY_HOTEL, C.CATEGORY_MOTEL)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output-root", default="data/discovery/lexington_ky_free_census_001")
    ap.add_argument("--observed-at", required=True)
    ap.add_argument("--max-overpass-requests", type=int, default=120)
    ap.add_argument("--cache-only", action="store_true")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--osm-extract-index", default="")
    ap.add_argument("--override-progress-gate", action="store_true")
    args = ap.parse_args()

    config = RunConfig(
        market_id=MARKET_ID,
        providers=(C.PROVIDER_OPENSTREETMAP,),
        categories=LODGING_CATEGORIES,
        output_root=args.output_root,
        observed_at=args.observed_at,
        max_overpass_requests=args.max_overpass_requests,
        max_google_requests=0,
        cache_only=args.cache_only,
        resume=args.resume,
        osm_extract_index=args.osm_extract_index,
        override_progress_gate=args.override_progress_gate,
    )

    market, queries, results, candidates = execute_run(config)

    by_state: dict = {}
    for r in results:
        by_state[r.state] = by_state.get(r.state, 0) + 1

    out = Path(args.output_root)
    out.mkdir(parents=True, exist_ok=True)
    summary = {
        "schema": "ptf-lexington-free-census/1.0",
        "work_order": "PTF-LEXINGTON-KY-NEW-MARKET-001",
        "market_id": MARKET_ID,
        "observed_at": args.observed_at,
        "providers": [C.PROVIDER_OPENSTREETMAP],
        "categories": list(LODGING_CATEGORIES),
        "paid_provider_calls": 0,
        "usd_spent": 0.0,
        "cells": len(market.cells),
        "queries": len(queries),
        "query_states": by_state,
        "candidates": len(candidates),
    }
    (out / "free_census_summary.json").write_text(
        json.dumps(summary, indent=1) + "\n", encoding="utf-8")

    rows = []
    for c in candidates:
        d = c.__dict__ if hasattr(c, "__dict__") else dict(c)
        rows.append({k: v for k, v in d.items() if not k.startswith("_")})
    (out / "free_census_candidates.json").write_text(
        json.dumps(rows, indent=1, default=str) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
