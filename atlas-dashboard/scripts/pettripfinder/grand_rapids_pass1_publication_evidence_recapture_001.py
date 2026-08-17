"""Record the attempted, but non-qualifying, Grand Rapids Pass 1 recapture.

The attended browser reached every official page.  Its screenshot operation
timed out and its HTML transport capped each capture at 200 KB; none of those
partial HTML files contains the exact policy quote.  This writer therefore
preserves the attempted-capture provenance without relabeling it as
publication-grade evidence or changing any authority.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LP = ROOT / "launch_packages" / "pettripfinder"
QUEUE = LP / "grand_rapids_holland_capture_pass1_recapture_queue_001.json"
ORIGINAL = LP / "grand_rapids_holland_capture_pass1_001.json"
OUTPUT = LP / "grand_rapids_holland_pass1_publication_evidence_recapture_001.json"
PROGRESS = LP / "grand_rapids_holland_pass1_publication_evidence_recapture_001_progress.json"
RAW = ROOT / "data" / "operator_evidence" / "grand-rapids-holland-pass1-publication-evidence-recapture-001"


def dump(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def normalized(value: str) -> str:
    return " ".join(value.split())


def main() -> None:
    queue = json.loads(QUEUE.read_text(encoding="utf-8"))["items"]
    original = {row["identity_key"]: row for row in
                json.loads(ORIGINAL.read_text(encoding="utf-8"))["terminal_rows"]}
    rows = []
    for position, item in enumerate(queue, 1):
        prefix = "%02d-" % position
        html_path = next(RAW.glob(prefix + "*.html"))
        text_path = next(RAW.glob(prefix + "*.txt"))
        metadata_path = next(RAW.glob(prefix + "*.json"))
        html = html_path.read_text(encoding="utf-8")
        text = text_path.read_text(encoding="utf-8")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        prior = original[item["identity_key"]]
        quote = prior["exact_contiguous_quote"]
        quote_in_html = normalized(quote) in normalized(html)
        quote_in_visible_text = normalized(quote) in normalized(text)
        # A visible-text extraction is useful diagnostic context but is not a
        # page artifact.  The HTML is hard-truncated and never contains the
        # quote, so no row passes the frozen artifact standard.
        rows.append({
            "queue_position": position,
            "identity_key": item["identity_key"],
            "canonical_name": item["canonical_name"],
            "official_url": item["official_url"],
            "final_url": metadata["final_url"],
            "prior_capture_artifact_sha256": prior["artifact_sha256"],
            "attempted_html_path": str(html_path.relative_to(ROOT)).replace("\\", "/"),
            "attempted_html_sha256": "sha256:" + hashlib.sha256(html.encode("utf-8")).hexdigest(),
            "attempted_visible_text_path": str(text_path.relative_to(ROOT)).replace("\\", "/"),
            "attempted_visible_text_sha256": metadata["text_sha256"],
            "captured_at": metadata["captured_at"],
            "exact_quote": quote,
            "quote_contiguous_in_attempted_html": quote_in_html,
            "quote_contiguous_in_visible_text_diagnostic": quote_in_visible_text,
            "publication_grade": False,
            "terminal_outcome": "CAPTURE_FAILED",
            "failure_reason": (
                "Browser screenshot capture timed out. The rendered-HTML "
                "transport was capped at 200 KB and does not contain the "
                "exact quote; the residual visible-text extraction is not "
                "a publication-grade page artifact."),
            "required_next_artifact": (
                "A durable operator_screenshot, or complete accepted "
                "rendered-page artifact, that contains both the exact quote "
                "and property identity context."),
        })
    assert len(rows) == 24
    assert all(not row["quote_contiguous_in_attempted_html"] for row in rows)
    report = {
        "schema": "ptf-market-publication-evidence-recapture/1.0",
        "work_order": "PTF-GRAND-RAPIDS-HOLLAND-PASS1-PUBLICATION-EVIDENCE-RECAPTURE-001",
        "market_id": "grand-rapids-holland-mi",
        "recapture_total": 24,
        "recaptured": 24,
        "publication_grade": 0,
        "publication_candidates": 0,
        "verified_no_pets_candidates": 0,
        "policy_not_found": 0,
        "access_blocked": 0,
        "identity_uncertain": 0,
        "capture_failed": 24,
        "source_ambiguous": 0,
        "artifact_insufficient_remaining": 24,
        "screenshot_artifacts": 0,
        "other_accepted_rendered_artifacts": 0,
        "authority_changed": False,
        "founder_review_ready": False,
        "note": (
            "Original Pass 1 transcriptions and founder-review packet remain "
            "unchanged. This report records failed evidence upgrades only; it "
            "does not erase or relabel their provenance."),
        "rows": rows,
    }
    dump(PROGRESS, {"processed": 24, "remaining": 0, "rows": rows})
    dump(OUTPUT, report)


if __name__ == "__main__":
    main()
