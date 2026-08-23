"""PTF-ST-LOUIS-MARKET-001 -- the current-state observation store, offline.

Input: a capture run directory whose attempts already persisted their artifact
set (``rendered.html``, ``page-text.txt``, ``policy-block.txt``, ``locator.json``)
plus the pilot report that says which attempt each identity ended on.

Output: one ``ptf-policy-observation/1.0`` record per acquired identity, each
with its reader provenance, its publication-grade verdict, its withheld fields
and its membrane/readiness result -- and a store document that says, per row,
why it is or is not publishable.

RE-PARSE THE BLOCK, NEVER RE-LOCATE THE DOCUMENT
------------------------------------------------
PTF-MILWAUKEE-OBSERVATION-REDERIVATION-018 established this the expensive way:
re-locating from a persisted document runs TODAY'S locator, which can bound a
different block than the locator that actually ran, and a different block is a
record about a different thing. It flipped two of nine records and would have
published one of two stated fee bases.

So this module reads ``policy-block.txt`` -- the bytes the capture itself
bounded -- and checks it against ``locator.json``'s ``block_sha256`` before
parsing. A block that does not match its own locator record is refused, not
repaired. ``rendered.html`` is read only to be hashed and to hold the quotes,
which is exactly what the evidence contract attests.

ZERO NETWORK. ZERO SPEND. Nothing here fetches anything.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.brightdata import browser_capture as BC       # noqa: E402
from scripts.pettripfinder.brightdata import policy_reading as PR        # noqa: E402
from scripts.pettripfinder.brightdata import marriott_surface as MS      # noqa: E402
from scripts.pettripfinder.brightdata import policy_surface as PS        # noqa: E402
from scripts.pettripfinder.brightdata import publication_grade as PG     # noqa: E402
from scripts.pettripfinder.brightdata import unlocker_capture as UC      # noqa: E402
from scripts.pettripfinder.policy import policy_membrane as MEMBRANE     # noqa: E402
from scripts.pettripfinder.policy import policy_observation as PO        # noqa: E402
from scripts.pettripfinder.policy import readiness as READINESS          # noqa: E402

SCHEMA = "ptf-market-observation-store/1.0"

# Why a captured identity produced no usable observation.
BLOCK_MISSING = "PERSISTED_BLOCK_MISSING"
BLOCK_HASH_MISMATCH = "PERSISTED_BLOCK_DOES_NOT_MATCH_ITS_LOCATOR_RECORD"
READER_FOUND_NOTHING = "READER_FOUND_NOTHING_IN_THE_PERSISTED_BLOCK"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _identity_check(html_path: Path, result: Mapping) -> "OrderedDict":
    """The page's own identity signals, re-read from the persisted document.

    The membrane's M10 gate reads ``name_on_page``. A document <title> is not
    an identity: Extended Stay America titles every property page "Explore Our
    Nationwide Hotel Locations", which M10 correctly refuses as neither a
    subset nor a superset of the property it is supposed to name -- and the
    capture's own identity gate had already confirmed those properties on
    street, postal code and telephone. Read what the capture read.
    """
    check = OrderedDict()
    try:
        html = _read(html_path)
        title = MS.collapse(html.split("<title", 1)[1].split(">", 1)[1]
                            .split("</title", 1)[0]) if "<title" in html else ""
        signals = PS.read_identity(html, final_url=result.get("final_url", ""),
                                   title=title,
                                   brand=(result.get("brand") or "")
                                   if not str(result.get("brand", "")).startswith("INDEP:")
                                   else "")
        raw = signals.to_dict()
    except Exception:                                            # noqa: BLE001
        raw = {}
    check["name_on_page"] = (str(raw.get("name_on_page") or "").strip()
                             or result.get("title") or result["canonical_name"])
    for source_key, target_key in (("address_on_page", "address_on_page"),
                                   ("property_code_on_page", "property_code"),
                                   ("phone_on_page", "phone_on_page")):
        value = str(raw.get(source_key) or "").strip()
        if value:
            check[target_key] = value
    return check


def observation_for(result: Mapping, *, run_id: str, market_id: str
                    ) -> Tuple[Optional[Dict], Optional[Dict], str]:
    """``(observation, publication_grade, refusal_reason)`` for one result."""
    attempt_dir = Path(result.get("artifact_dir") or "")
    if not attempt_dir.is_dir():
        return (None, None, BLOCK_MISSING)
    block_path = attempt_dir / "policy-block.txt"
    html_path = attempt_dir / "rendered.html"
    text_path = attempt_dir / "page-text.txt"
    locator_path = attempt_dir / "locator.json"
    if not (block_path.is_file() and html_path.is_file()):
        return (None, None, BLOCK_MISSING)

    block_text = _read(block_path)
    locator: Dict = {}
    if locator_path.is_file():
        locator = json.loads(_read(locator_path))
        recorded = str(locator.get("block_sha256") or "")
        if recorded and BC.sha256_file(block_path) != recorded:
            return (None, None, BLOCK_HASH_MISMATCH)

    strategy = str(locator.get("strategy") or result.get("locator_strategy") or "")
    reading = PR.parse(block_text, strategy=strategy)
    if not reading.found:
        return (None, None, READER_FOUND_NOTHING)

    extraction_result = PR.to_extraction(
        reading,
        location="bounded policy container (%s / %s)"
                 % (strategy, locator.get("selector") or "no path"))

    html_sha = BC.sha256_file(html_path)
    observation = OrderedDict((
        ("obs_id", "%s::%s" % (run_id, result["identity_key"])),
        ("contract_version", PO.CONTRACT_VERSION),
        ("hotel_ref", OrderedDict((
            ("market_id", market_id),
            ("canonical_name", result["canonical_name"]),
            ("normalized_name", result["identity_key"]),
            ("official_url", result["source_url"]),
            ("property_code", ""),
        ))),
        ("identity_check", _identity_check(html_path, result)),
        ("source_url", result.get("final_url") or result["source_url"]),
        ("source_type", "official_property_page"),
        ("authority_tier", PO.PT1_OFFICIAL_PROPERTY),
        ("observed_at", "2026-08-23"),
        ("retrieved_at", "2026-08-23"),
        ("capture_method", "deterministic_fetch"),
        ("evidence", [dict(item) for item in extraction_result.evidence]),
        ("extraction", dict(extraction_result.extraction)),
        ("extraction_confidence", "EXACT_QUOTE"),
        ("flags", [dict(flag) for flag in extraction_result.flags]),
        ("snapshot_hash", html_sha),
        ("raw_pointer", str(attempt_dir)),
        ("capture_artifacts", OrderedDict((
            ("rendered.html", str(html_path)),
            ("page-text.txt", str(text_path)),
            ("policy-block.txt", str(block_path)),
            ("locator.json", str(locator_path) if locator_path.is_file() else ""),
        ))),
    ))
    if extraction_result.parser_warnings:
        observation["parser_warnings"] = list(extraction_result.parser_warnings)

    grade = PG.assess(
        evidence_items=observation["evidence"],
        extraction=observation["extraction"],
        source_url=observation["source_url"],
        captured_at="2026-08-23",
        ref_prefix="%s::%s" % (run_id, result["identity_key"]),
        artifact_path=html_path,
        recorded_sha256=html_sha,
        page_text_path=text_path if text_path.is_file() else None,
        identity_confirmed=bool(result.get("identity_confirmed")))

    membrane = MEMBRANE.evaluate(observation)
    readiness = READINESS.derive([observation], blocked=False,
                                 all_surfaces_reached=True)
    record = OrderedDict((
        ("identity_key", result["identity_key"]),
        ("canonical_name", result["canonical_name"]),
        ("corridor", result.get("corridor", "")),
        ("brand", result.get("brand", "")),
        ("provider", "direct_http"),
        ("reader", "generic"),
        ("reader_provenance", OrderedDict((
            ("module", "scripts/pettripfinder/brightdata/policy_reading.py"),
            ("entrypoint", "parse -> to_extraction"),
            ("locator_walk", str(locator.get("walk") or "")),
            ("locator_strategy", strategy),
            ("locator_contract", str(locator.get("contract") or "")),
            ("block_sha256", str(locator.get("block_sha256") or "")),
            ("document_sha256", html_sha),
        ))),
        ("observation", observation),
        ("publication_grade", grade.to_dict()),
        ("withheld_fields", dict(extraction_result.withheld)),
        ("non_inferences", list(extraction_result.non_inferences)),
        ("membrane", membrane.to_dict()),
        ("readiness", readiness.to_dict()),
        ("review_state", "AWAITING_FOUNDER_REVIEW"),
    ))
    return (record, grade.to_dict(), "")


def build(pilot: Mapping, *, run_id: str) -> Tuple[List[Dict], List[Dict]]:
    """``(records, refusals)``. Every VALID capture is accounted for."""
    market_id = pilot["market_id"]
    records: List[Dict] = []
    refusals: List[Dict] = []
    for result in pilot["results"]:
        if result["outcome"] != "VALID":
            continue
        record, _grade, refusal = observation_for(
            result, run_id=run_id, market_id=market_id)
        if record is None:
            refusals.append(OrderedDict((
                ("identity_key", result["identity_key"]),
                ("canonical_name", result["canonical_name"]),
                ("reason", refusal),
                ("artifact_dir", result.get("artifact_dir", "")),
            )))
            continue
        records.append(record)
    records.sort(key=lambda r: r["identity_key"])
    refusals.sort(key=lambda r: r["identity_key"])
    return (records, refusals)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--run-id", default="ptf-st-louis-direct-http-001")
    args = parser.parse_args(argv)

    pilot = json.loads(Path(args.pilot).read_text(encoding="utf-8"))
    records, refusals = build(pilot, run_id=args.run_id)

    grades = Counter(r["publication_grade"]["verdict"] for r in records)
    readiness_states = Counter(r["readiness"].get("state", "") for r in records)
    membrane_states = Counter(str(r["membrane"].get("verdict", "")) for r in records)
    pets = Counter(str(r["observation"]["extraction"].get("pets_allowed"))
                   for r in records)

    document = OrderedDict((
        ("schema", SCHEMA),
        ("what_this_is",
         "The current-state policy observation store for this market, derived "
         "offline from persisted capture artifacts. Every row carries its "
         "source, its capture, its locator, its evidence, its reader "
         "provenance, its current facts, its withheld fields and its review "
         "state. No row here is an authority; every row is AWAITING_FOUNDER_"
         "REVIEW until a human decides it."),
        ("market_id", pilot["market_id"]),
        ("work_order", pilot.get("work_order", "")),
        ("run_id", args.run_id),
        ("derived_from", args.pilot),
        ("network_calls", 0),
        ("usd_spent", 0.0),
        ("count", len(records)),
        ("publication_grade_counts", OrderedDict(sorted(grades.items()))),
        ("readiness_counts", OrderedDict(sorted(readiness_states.items()))),
        ("membrane_counts", OrderedDict(sorted(membrane_states.items()))),
        ("pets_allowed_counts", OrderedDict(sorted(pets.items()))),
        ("refusals", refusals),
        ("records", records),
    ))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(document, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    print("observations   : %d" % len(records))
    print("refusals       : %d" % len(refusals))
    print("grades         : %s" % dict(sorted(grades.items())))
    print("readiness      : %s" % dict(sorted(readiness_states.items())))
    print("pets_allowed   : %s" % dict(sorted(pets.items())))
    print("written        : %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
