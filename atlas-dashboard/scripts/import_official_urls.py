"""AES-DATA-002C -- CLI: import multiple official URLs for ONE intended
entity into a single reviewable aggregate candidate.

Deterministic offline example (no network, no API key):

    python scripts/import_official_urls.py `
      --url "https://example.test/faq" --url "https://example.test/contact" `
      --category restaurants --extractor static `
      --static-fixture tests/.../faq_fixture.json `
      --static-fixture tests/.../contact_fixture.json `
      --output-root data/import/test-run

Live example (requires ANTHROPIC_API_KEY; makes ONE paid call PER URL --
never a reconciliation call):

    python scripts/import_official_urls.py `
      --url "https://example.com/page-1" `
      --url "https://example.com/page-2" `
      --category restaurants `
      --candidate-name "Example Venue Columbus" `
      --expected-city Columbus `
      --expected-state OH `
      --source-relationship EXACT_ENTITY_DOMAIN `
      --extractor anthropic

The live paid provider is used only when ``--extractor anthropic`` is given
and the key exists -- never silently. This CLI calls ``run_multi_import``
exactly once; the single-source ``scripts/import_official_url.py`` is
untouched and unaffected by this file.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Dict, List, Tuple

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from repositories.artifact_store_repository import ArtifactStoreRepository
from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.aggregate import run_multi_import
from scripts.pettripfinder.importer.candidate import persist_candidate
from scripts.pettripfinder.importer.fetch import RequestsPageFetcher, StaticPageFetcher
from scripts.pettripfinder.importer.models import CandidateListing, FetchResult, ImportContext
from scripts.pettripfinder.importer.rejection_log import append_rejection
from scripts.pettripfinder.importer.review_report import write_report
from scripts.pettripfinder.importer.source_snapshot import normalize_html_to_text


def import_urls(
    urls: List[str],
    context: ImportContext,
    *,
    fetcher,
    extractor,
    output_root: str,
    observed_at: str,
    created_at: str,
) -> Tuple[CandidateListing, Path, Path]:
    """Run the aggregate pipeline and persist candidate JSON + HTML report,
    through the SAME persistence conventions as the single-source CLI (no
    parallel persistence system): ``data/import/candidates/<id>.json`` and
    ``data/import/reports/<id>.html`` under ``output_root``."""
    root = Path(output_root)
    cas = ArtifactStoreRepository(root / C.CAS_SUBDIR)
    candidate = run_multi_import(
        urls, context, fetcher=fetcher, extractor=extractor, cas=cas,
        observed_at=observed_at, created_at=created_at)
    json_path = persist_candidate(candidate, root / C.CANDIDATES_SUBDIR)
    report_path = write_report(candidate, root / C.REPORTS_SUBDIR, str(json_path))
    if candidate.recommendation == C.RECOMMEND_REJECT:
        append_rejection(candidate, root / C.REJECTIONS_NAME)
    return (candidate, json_path, report_path)


def _build_static_multi(urls: List[str], fixture_paths: List[str]):
    """Build one ``StaticPageFetcher`` (URL-keyed, unambiguous) and one
    ``StaticFactExtractor`` whose payload is dispatched by the EXACT
    normalized text ``import_source`` will hand it -- computed here with the
    same pure ``normalize_html_to_text`` transform the real pipeline uses, so
    the match is exact regardless of call order or URL deduplication (never
    a fragile positional/counter-based dispatch)."""
    from scripts.pettripfinder.importer.extraction import StaticFactExtractor

    fetcher = StaticPageFetcher()
    text_to_facts: Dict[str, dict] = {}
    for url, fixture_path in zip(urls, fixture_paths):
        data = json.loads(Path(fixture_path).read_text(encoding="utf-8"))
        html_body = data.get("html", "")
        if not html_body and data.get("html_path"):
            html_body = Path(data["html_path"]).read_text(encoding="utf-8")
        if "fetch_result" in data:
            fr = data["fetch_result"]
            body_bytes = (fr.get("body", "") or "").encode("utf-8")
            fetcher.add_result(url, FetchResult(
                requested_url=url, ok=fr.get("ok", False), final_url=fr.get("final_url", url),
                http_status=fr.get("http_status", 0), content_type=fr.get("content_type", ""),
                body=body_bytes, reason=fr.get("reason", "")))
            html_for_text = body_bytes.decode("utf-8", "ignore")
        else:
            fetcher.add_html(url, html_body, content_type=data.get("content_type", "text/html"))
            html_for_text = html_body
        normalized_text, _truncated = normalize_html_to_text(html_for_text)
        text_to_facts[normalized_text] = data.get("extraction", {"facts": []})

    def payload(normalized_text, _category, _allowed):
        return text_to_facts.get(normalized_text, {"facts": []})

    extractor = StaticFactExtractor(payload)
    return (fetcher, extractor)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Import multiple official URLs for one entity -> aggregate candidate.")
    p.add_argument("--url", action="append", default=[],
                   help="Official source URL; repeatable, first supplied is PRIMARY. "
                        "At least 1, at most %d." % C.MAX_AGGREGATE_SOURCES)
    p.add_argument("--category", choices=C.IMPORTER_CATEGORIES, default="")
    p.add_argument("--candidate-name", default="")
    p.add_argument("--expected-city", default="")
    p.add_argument("--expected-state", default="")
    p.add_argument("--source-relationship", default="")
    p.add_argument("--source-type-hint", default="")
    p.add_argument("--extractor", choices=("static", "anthropic"), default="static")
    p.add_argument("--static-fixture", action="append", default=[],
                   help="Offline fixture path, paired with --url by position; repeatable. "
                        "Required (one per --url) when --extractor static.")
    p.add_argument("--output-root", default=C.DEFAULT_OUTPUT_ROOT)
    p.add_argument("--observed-at", default="")
    p.add_argument("--created-at", default="")
    p.add_argument("--model", default=C.DEFAULT_ANTHROPIC_MODEL)
    args = p.parse_args(argv)

    # --- validation: fail before any fetch --------------------------------
    if not args.url:
        print("ERROR: at least one --url is required")
        return 2
    if len(args.url) > C.MAX_AGGREGATE_SOURCES:
        print("ERROR: at most %d --url values are supported (got %d)"
              % (C.MAX_AGGREGATE_SOURCES, len(args.url)))
        return 2

    if args.extractor == "static":
        if len(args.static_fixture) != len(args.url):
            print("ERROR: --extractor static requires exactly one --static-fixture "
                  "per --url (got %d urls, %d fixtures)"
                  % (len(args.url), len(args.static_fixture)))
            return 2
    elif args.static_fixture:
        print("ERROR: --static-fixture is only valid with --extractor static")
        return 2

    observed_at = args.observed_at or date.today().isoformat()
    created_at = args.created_at or datetime.now().isoformat(timespec="seconds")
    context = ImportContext(
        category=args.category, expected_city=args.expected_city,
        expected_state=args.expected_state, candidate_name=args.candidate_name,
        source_type_hint=args.source_type_hint,
        source_relationship_hint=args.source_relationship)

    if args.extractor == "static":
        fetcher, extractor = _build_static_multi(args.url, args.static_fixture)
    else:
        # Live: never silently call a paid provider.
        from scripts.pettripfinder.importer.extraction_anthropic import (
            AnthropicFactExtractor,
        )
        fetcher = RequestsPageFetcher()
        extractor = AnthropicFactExtractor(model=args.model)

    candidate, json_path, report_path = import_urls(
        args.url, context, fetcher=fetcher, extractor=extractor,
        output_root=args.output_root, observed_at=observed_at, created_at=created_at)

    print("recommendation : %s" % candidate.recommendation)
    print("reasons        : %s" % ", ".join(candidate.recommendation_reasons))
    print("sources        :")
    for s in candidate.sources:
        status = ("excluded:%s" % s.excluded_reason if s.excluded_reason
                  else "unusable:%s" % s.fetch_reason if not s.usable else "included")
        print("  %s %-11s %-24s %s" % (s.source_id, s.role, status, s.final_url or s.requested_url))
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
