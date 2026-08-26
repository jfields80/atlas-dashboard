"""PTF-PITTSBURGH-HARDENED-RECENSUS-001 -- the local OSM extract as a discovery
source, operated.

    plan        --market <id>                 offline: readiness + exact next steps
    build-index --market <id> [--pbf ...]     reduce the extract to an index (pyosmium)
    inspect     --index <path>                offline: what an index holds
    dry-run     --market <id> --output-root   offline: which planned cells the index
                [--index ...]                 would answer, and with how many elements

Nothing here downloads, installs, or talks to a public server. The download is
an operator step named by ``plan``; ``build-index`` reads a file on disk;
``dry-run`` answers cells from the index in memory and writes nothing.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery import osm_extract as OX
from scripts.pettripfinder.discovery.cache import DiscoveryCache
from scripts.pettripfinder.discovery.market_config import load_market_config
from scripts.pettripfinder.discovery.query_plan import plan_queries


def _parse_categories(value: str):
    if not value:
        return (C.CATEGORY_HOTEL, C.CATEGORY_MOTEL)
    return tuple(token.strip() for token in value.split(",") if token.strip())


def _write_json(document, path: str) -> None:
    if not path:
        return
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8")
    print("written                 : %s" % out.as_posix())


def cmd_plan(args) -> int:
    registry = OX.ExtractRegistry.load(Path(args.registry)) if args.registry else None
    try:
        document = OX.readiness(args.market, registry=registry)
    except KeyError as exc:
        print("ERROR: %s" % exc)
        return 2
    print("market                  : %s" % document["market_id"])
    print("extract                 : %s (%s)" % (document["extract_id"], document["region"]))
    print("status                  : %s" % document["status"])
    print("extract file            : %s (%s)" % (
        document["pbf_path"], "present, %d bytes" % document["pbf_bytes"]
        if document["pbf_present"] else "ABSENT"))
    print("index file              : %s (%s)" % (
        document["index_path"], "present, %s elements" % document["index_element_count"]
        if document["index_present"] else "ABSENT"))
    print("pyosmium                : %s" % ("installed" if document["pyosmium_available"]
                                           else "NOT installed"))
    print("network required        : %s" % ("yes (operator steps below)"
                                           if document["network_required"] else "no"))
    print("license                 : %s" % document["license"])
    print("next steps:")
    for n, step in enumerate(document["next_steps"], 1):
        print("  %d. %s" % (n, step))
    _write_json(document, args.out)
    return 0


def cmd_build_index(args) -> int:
    registry = OX.ExtractRegistry.load(Path(args.registry)) if args.registry else OX.ExtractRegistry.load()
    record = registry.for_market(args.market) if args.market else None
    pbf = Path(args.pbf) if args.pbf else (OX.REPO_ROOT / record.local_pbf if record else None)
    out = Path(args.out) if args.out else (OX.REPO_ROOT / record.index_path if record else None)
    extract_id = args.extract_id or (record.extract_id if record else "")
    if pbf is None or out is None or not extract_id:
        print("ERROR: --market (a registered market) or all of --pbf/--out/--extract-id")
        return 2
    if not pbf.is_file():
        print("ERROR: no extract at %s; `plan --market %s` names the download step"
              % (pbf.as_posix(), args.market or "<id>"))
        return 2
    bbox = None
    if args.market and not args.no_bounds:
        bounds = load_market_config(args.market).bounds
        bbox = (bounds.min_lat, bounds.min_lng, bounds.max_lat, bounds.max_lng)
    keep = tuple(k.strip() for k in args.keep_tag_keys.split(",") if k.strip())
    try:
        written = OX.build_index_from_pbf(
            pbf, extract_id=extract_id, out=out, keep_tag_keys=keep,
            source_url=record.url if record else "", bbox=bbox)
    except OX.ExtractError as exc:
        print("ERROR: %s" % exc)
        return 2
    index = OX.ExtractIndex.load(Path(written))
    print("index                   : %s" % written)
    print("extract_id              : %s" % index.extract_id)
    print("elements                : %d" % len(index.elements))
    print("bbox                    : %s" % (list(bbox) if bbox else "(whole extract)"))
    print("kept tag keys           : %s" % ", ".join(keep))
    return 0


def cmd_inspect(args) -> int:
    index = OX.ExtractIndex.load(Path(args.index))
    by_type = {}
    by_tourism = {}
    for element in index.elements:
        by_type[element["type"]] = by_type.get(element["type"], 0) + 1
        tourism = (element.get("tags") or {}).get("tourism")
        if tourism:
            by_tourism[tourism] = by_tourism.get(tourism, 0) + 1
    print("extract_id              : %s" % index.extract_id)
    print("source                  : %s" % json.dumps(index.source, sort_keys=True))
    print("elements                : %d %s" % (len(index.elements), dict(sorted(by_type.items()))))
    print("tourism=*               : %s" % dict(sorted(by_tourism.items())))
    return 0


def cmd_dry_run(args) -> int:
    registry = OX.ExtractRegistry.load(Path(args.registry)) if args.registry else OX.ExtractRegistry.load()
    index_path = Path(args.index) if args.index else OX.REPO_ROOT / registry.for_market(args.market).index_path
    if not index_path.is_file():
        print("ERROR: no index at %s; `plan --market %s` names the steps"
              % (index_path.as_posix(), args.market))
        return 2
    index = OX.ExtractIndex.load(index_path)
    market = load_market_config(args.market)
    queries = [q for q in plan_queries(market, (C.PROVIDER_OPENSTREETMAP,),
                                       _parse_categories(args.categories))
               if q.provider == C.PROVIDER_OPENSTREETMAP]
    cache = DiscoveryCache(Path(args.output_root) / C.CACHE_SUBDIR) if args.output_root else None
    document = OX.answerability(index, market=market, queries=queries, cache=cache,
                                as_of=args.observed_at)
    print("market                  : %s   extract: %s (%d elements)"
          % (document["market_id"], document["extract_id"], document["index_element_count"]))
    print("cells total/cached/ans. : %d / %d / %d"
          % (document["cells_total"], document["cells_cached"], document["cells_answerable"]))
    print("elements from index     : %d over the answerable cells (%d answerable cells empty)"
          % (document["elements_from_index"], document["empty_answerable_cells"]))
    for row in document["cells"]:
        if row["disposition"] == "ANSWERABLE":
            print("  %-52s %3d elements" % (row["query_id"], row["elements"]))
    print("network requests        : 0 (a dry run answers from the index in memory)")
    _write_json(document, args.out)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    plan = sub.add_parser("plan", help="offline readiness and next steps for a market")
    plan.add_argument("--market", required=True)
    plan.add_argument("--registry", default="")
    plan.add_argument("--out", default="")
    plan.set_defaults(func=cmd_plan)

    build = sub.add_parser("build-index", help="reduce a .osm.pbf to an index (needs pyosmium)")
    build.add_argument("--market", default="")
    build.add_argument("--pbf", default="")
    build.add_argument("--out", default="")
    build.add_argument("--extract-id", default="")
    build.add_argument("--registry", default="")
    build.add_argument("--keep-tag-keys", default=",".join(OX.DEFAULT_INDEX_TAG_KEYS))
    build.add_argument("--no-bounds", action="store_true",
                       help="index the whole extract instead of the market's bounds")
    build.set_defaults(func=cmd_build_index)

    inspect = sub.add_parser("inspect", help="what an index holds")
    inspect.add_argument("--index", required=True)
    inspect.set_defaults(func=cmd_inspect)

    dry = sub.add_parser("dry-run", help="which planned cells an index would answer")
    dry.add_argument("--market", required=True)
    dry.add_argument("--index", default="")
    dry.add_argument("--registry", default="")
    dry.add_argument("--output-root", default="",
                     help="a discovery output root whose cache marks cells already answered")
    dry.add_argument("--categories", default="")
    dry.add_argument("--observed-at", default="")
    dry.add_argument("--out", default="")
    dry.set_defaults(func=cmd_dry_run)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
