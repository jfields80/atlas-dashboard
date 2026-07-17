"""AES-DATA-001 -- CLI: importer benchmark (mission sections 27/30).

Two modes:

  static  -- StaticPageFetcher + StaticFactExtractor over offline gold
             fixtures. No network, no API key. Measures pipeline correctness
             and expected READY/REVIEW/REJECT classification.

  live    -- RequestsPageFetcher + AnthropicFactExtractor over an
             operator-supplied URL file. Measures machine metrics only; the
             labor-reduction target (>=8/10 accurate, <15 min review, zero
             unsupported approved claims) is an OPERATOR acceptance test and
             is never auto-claimed here. No automatic promotion.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.import_official_url import _build_static, import_url
from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.models import ImportContext


def _context_from(obj: dict) -> ImportContext:
    ctx = obj.get("context", {})
    return ImportContext(
        category=ctx.get("category", ""), expected_city=ctx.get("expected_city", ""),
        expected_state=ctx.get("expected_state", ""),
        candidate_name=ctx.get("candidate_name", ""),
        source_type_hint=ctx.get("source_type_hint", ""),
        source_relationship_hint=ctx.get("source_relationship_hint", ""))


def run_static_benchmark(fixtures_dir, output_root) -> Dict[str, object]:
    """Run every ``*.json`` gold fixture through the deterministic pipeline."""
    fixtures_dir = Path(fixtures_dir)
    results: List[dict] = []
    counts = {C.RECOMMEND_READY: 0, C.RECOMMEND_REVIEW: 0, C.RECOMMEND_REJECT: 0}
    correct = 0
    total = 0
    start = time.time()
    observed = date.today().isoformat()

    for fixture_path in sorted(fixtures_dir.glob("*.json")):
        obj = json.loads(fixture_path.read_text(encoding="utf-8"))
        if "expected_recommendation" not in obj:
            continue
        total += 1
        url = obj.get("url", "https://example.test/%s" % fixture_path.stem)
        fetcher, extractor = _build_static(url, str(fixture_path))
        candidate, _jp, _rp = import_url(
            url, _context_from(obj), fetcher=fetcher, extractor=extractor,
            output_root=str(Path(output_root) / fixture_path.stem),
            observed_at=observed, created_at="1970-01-01T00:00:00")
        rec = candidate.recommendation
        counts[rec] = counts.get(rec, 0) + 1
        expected = obj["expected_recommendation"]
        ok = rec == expected
        correct += 1 if ok else 0
        results.append({
            "fixture": fixture_path.name, "expected": expected, "actual": rec,
            "match": ok, "reasons": list(candidate.recommendation_reasons),
            "unsupported_dropped": sum(
                1 for e in candidate.evidence
                if e.support_state == C.SUPPORT_UNSUPPORTED)})

    elapsed = time.time() - start
    return {
        "mode": "static", "fixtures": total, "correct_classification": correct,
        "counts_by_recommendation": counts,
        "runtime_seconds": round(elapsed, 3), "results": results,
        "all_match": correct == total and total > 0,
    }


def run_live_benchmark(urls_file, output_root, model) -> Dict[str, object]:
    """Machine metrics only over operator URLs; requires ANTHROPIC_API_KEY."""
    from scripts.import_official_url import import_url as _imp
    from scripts.pettripfinder.importer.extraction_anthropic import AnthropicFactExtractor
    from scripts.pettripfinder.importer.fetch import RequestsPageFetcher

    lines = [l.strip() for l in Path(urls_file).read_text(encoding="utf-8").splitlines()
             if l.strip() and not l.startswith("#")]
    observed = date.today().isoformat()
    results: List[dict] = []
    api_calls = 0
    start = time.time()
    for line in lines:
        parts = line.split("\t")
        url = parts[0]
        ctx = ImportContext(
            category=parts[1] if len(parts) > 1 else "",
            expected_city=parts[2] if len(parts) > 2 else "",
            expected_state=parts[3] if len(parts) > 3 else "")
        extractor = AnthropicFactExtractor(model=model)
        candidate, jp, rp = _imp(
            url, ctx, fetcher=RequestsPageFetcher(), extractor=extractor,
            output_root=output_root, observed_at=observed,
            created_at=datetime.now().isoformat(timespec="seconds"))
        if candidate.snapshot.raw_content_hash:
            api_calls += 1
        results.append({
            "url": url, "recommendation": candidate.recommendation,
            "relationship": candidate.source_relationship,
            "evidence_mismatch": sum(
                1 for e in candidate.evidence
                if C.REASON_EVIDENCE_MISMATCH in e.warnings),
            "candidate_json": str(jp), "report": str(rp)})
    return {
        "mode": "live", "urls": len(lines), "api_calls": api_calls,
        "machine_runtime_seconds": round(time.time() - start, 3),
        "results": results,
        "operator_metrics_note": (
            "Review minutes, field corrections, accepted candidates, and "
            "unsupported approved claims are OPERATOR-entered after human "
            "review -- not measured here. The <15-minute / >=8-accurate / "
            "zero-unsupported target is an operator acceptance test."),
    }


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Importer benchmark (static|live).")
    p.add_argument("--mode", choices=("static", "live"), default="static")
    p.add_argument("--fixtures-dir",
                   default="tests/pettripfinder/importer/fixtures")
    p.add_argument("--urls", default="")
    p.add_argument("--output-root", default=str(Path(C.DEFAULT_OUTPUT_ROOT) / "benchmark"))
    p.add_argument("--model", default=C.DEFAULT_ANTHROPIC_MODEL)
    args = p.parse_args(argv)

    if args.mode == "static":
        report = run_static_benchmark(args.fixtures_dir, args.output_root)
    else:
        if not args.urls:
            print("ERROR: --mode live requires --urls <file>")
            return 2
        report = run_live_benchmark(args.urls, args.output_root, args.model)
    print(json.dumps(report, sort_keys=True, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
