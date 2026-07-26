from __future__ import annotations

import argparse
import sys
from pathlib import Path

from acdis.casefiles.loader import CaseFileError, CaseFileValidationError, load_case_file
from acdis.reports.markdown import render_markdown
from acdis.reports.writer import write_markdown_report
from acdis.review import ReviewValidationError, build_review_case, render_review_markdown
from acdis.safeguards.path_fence import PathFenceError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m acdis")
    subparsers = parser.add_subparsers(dest="command", required=True)

    render_parser = subparsers.add_parser("render-case", help="Render a manual research case file as Markdown")
    render_parser.add_argument("input_path", help="Path to the JSON case file")
    render_parser.add_argument("--output", required=True, help="Path to the Markdown report to write")
    render_parser.add_argument("--overwrite", action="store_true", help="Overwrite an existing output file")

    review_parser = subparsers.add_parser("review-case", help="Render a Phase 2 deterministic review report")
    review_parser.add_argument("input_path", help="Path to the JSON case file")
    review_parser.add_argument("--output", required=True, help="Path to the Markdown review report to write")
    review_parser.add_argument("--overwrite", action="store_true", help="Overwrite an existing output file")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "render-case":
        try:
            case = load_case_file(args.input_path)
            markdown_text = render_markdown(case)
            output_path = write_markdown_report(markdown_text, args.output, overwrite=args.overwrite)
        except (CaseFileError, CaseFileValidationError, PathFenceError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"Rendered report: {output_path}")
        return 0

    if args.command == "review-case":
        try:
            review_case = build_review_case(args.input_path)
            markdown_text = render_review_markdown(review_case)
            output_path = write_markdown_report(markdown_text, args.output, overwrite=args.overwrite)
        except (CaseFileError, CaseFileValidationError, ReviewValidationError, PathFenceError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"Rendered review report: {output_path}")
        return 0

    parser.error("Unsupported command")
    return 2


if __name__ == "__main__":
    sys.exit(main())
