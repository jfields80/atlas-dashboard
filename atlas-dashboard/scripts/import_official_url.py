"""AES-DATA-001 -- CLI: import one official URL into a reviewable candidate.

Deterministic offline example (no network, no API key):

    python scripts/import_official_url.py https://example.test/hotel \\
      --category hotels --extractor static \\
      --static-fixture tests/pettripfinder/importer/fixtures/hotel_strong.json \\
      --output-root data/import/test-run

Live example (requires ANTHROPIC_API_KEY; makes one paid call):

    python scripts/import_official_url.py <official-url> \\
      --category hotels --extractor anthropic

The live paid provider is used only when ``--extractor anthropic`` is given
and the key exists -- never silently.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from repositories.artifact_store_repository import ArtifactStoreRepository
from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.candidate import (
    persist_candidate,
    run_import,
)
from scripts.pettripfinder.importer.fetch import RequestsPageFetcher, StaticPageFetcher
from scripts.pettripfinder.importer.extraction import StaticFactExtractor
from scripts.pettripfinder.importer.models import CandidateListing, ImportContext
from scripts.pettripfinder.importer.rejection_log import append_rejection
from scripts.pettripfinder.importer.review_report import write_report


def import_url(
    url: str,
    context: ImportContext,
    *,
    fetcher,
    extractor,
    output_root: str,
    observed_at: str,
    created_at: str,
) -> Tuple[CandidateListing, Path, Path]:
    """Run the pipeline and persist candidate JSON + HTML report. Returns
    ``(candidate, json_path, report_path)``."""
    root = Path(output_root)
    cas = ArtifactStoreRepository(root / C.CAS_SUBDIR)
    candidate = run_import(
        url, context, fetcher=fetcher, extractor=extractor, cas=cas,
        observed_at=observed_at, created_at=created_at)
    json_path = persist_candidate(candidate, root / C.CANDIDATES_SUBDIR)
    report_path = write_report(candidate, root / C.REPORTS_SUBDIR, str(json_path))
    if candidate.recommendation == C.RECOMMEND_REJECT:
        append_rejection(candidate, root / C.REJECTIONS_NAME)
    return (candidate, json_path, report_path)


def _build_static(url: str, fixture_path: str):
    """Build a StaticPageFetcher + StaticFactExtractor from an offline
    fixture: {"html": "...", "extraction": {...}}."""
    data = json.loads(Path(fixture_path).read_text(encoding="utf-8"))
    html = data.get("html", "")
    if not html and data.get("html_path"):
        html = Path(data["html_path"]).read_text(encoding="utf-8")
    fetcher = StaticPageFetcher()
    if "fetch_result" in data:
        from scripts.pettripfinder.importer.models import FetchResult
        fr = data["fetch_result"]
        fetcher.add_result(url, FetchResult(
            requested_url=url, ok=fr.get("ok", False), final_url=fr.get("final_url", url),
            http_status=fr.get("http_status", 0), content_type=fr.get("content_type", ""),
            body=(fr.get("body", "") or "").encode("utf-8"),
            reason=fr.get("reason", "")))
    else:
        fetcher.add_html(url, html, content_type=data.get("content_type", "text/html"))
    extractor = StaticFactExtractor(data.get("extraction", {"facts": []}))
    return fetcher, extractor


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Import one official URL -> candidate.")
    p.add_argument("url")
    p.add_argument("--category", choices=C.IMPORTER_CATEGORIES, default="")
    p.add_argument("--candidate-name", default="")
    p.add_argument("--expected-city", default="")
    p.add_argument("--expected-state", default="")
    p.add_argument("--source-relationship", default="")
    p.add_argument("--source-type-hint", default="")
    p.add_argument("--extractor", choices=("static", "anthropic"), default="static")
    p.add_argument("--static-fixture", default="")
    p.add_argument("--output-root", default=C.DEFAULT_OUTPUT_ROOT)
    p.add_argument("--observed-at", default="")
    p.add_argument("--model", default=C.DEFAULT_ANTHROPIC_MODEL)
    args = p.parse_args(argv)

    observed_at = args.observed_at or date.today().isoformat()
    created_at = datetime.now().isoformat(timespec="seconds")
    context = ImportContext(
        category=args.category, expected_city=args.expected_city,
        expected_state=args.expected_state, candidate_name=args.candidate_name,
        source_type_hint=args.source_type_hint,
        source_relationship_hint=args.source_relationship)

    if args.extractor == "static":
        if not args.static_fixture:
            print("ERROR: --extractor static requires --static-fixture")
            return 2
        fetcher, extractor = _build_static(args.url, args.static_fixture)
    else:
        # Live: never silently call a paid provider.
        from scripts.pettripfinder.importer.extraction_anthropic import (
            AnthropicFactExtractor,
        )
        fetcher = RequestsPageFetcher()
        extractor = AnthropicFactExtractor(model=args.model)

    candidate, json_path, report_path = import_url(
        args.url, context, fetcher=fetcher, extractor=extractor,
        output_root=args.output_root, observed_at=observed_at, created_at=created_at)

    print("recommendation : %s" % candidate.recommendation)
    print("reasons        : %s" % ", ".join(candidate.recommendation_reasons))
    print("candidate json : %s" % json_path)
    print("review report  : %s" % report_path)
    print("snapshot hash  : %s" % candidate.snapshot.raw_content_hash)
    print("fetch warnings : %s" % ", ".join(candidate.snapshot.fetch_warnings))
    if candidate.recommendation != C.RECOMMEND_REJECT:
        print("next           : python scripts/approve_import_candidate.py "
              "--candidate %s --decision approve" % json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
