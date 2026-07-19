"""AES-DATA-004E (Task 8) -- deterministic Wave 1 source-strategy report.

Classifies all 20 AES-DATA-004D Wave 1 lodging jobs using ONLY already-
persisted candidate JSON (``data/import/columbus_lodging_wave1/candidates/``)
and the disclosed Task 3 static-research findings -- makes ZERO network
calls and re-fetches nothing.

Usage:
    python scripts/pettripfinder/lodging_source_strategy_report.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

REPO_ROOT = Path(__file__).resolve().parents[2]
CANDIDATES_DIR = REPO_ROOT / "data" / "import" / "columbus_lodging_wave1" / "candidates"

# Classification labels (Task 8).
CLASS_NORMAL_FETCHABLE = "NORMAL_FETCHABLE_OFFICIAL_SOURCE"
CLASS_HTTP_BLOCKED = "HTTP_BLOCKED"
CLASS_TIMED_OUT = "TIMED_OUT"
CLASS_BRAND_ALTERNATIVE_AVAILABLE = "BRAND_ALTERNATIVE_AVAILABLE"
CLASS_PROPERTY_IDENTITY_SOURCE_AVAILABLE = "PROPERTY_IDENTITY_SOURCE_AVAILABLE"
CLASS_BRAND_POLICY_SOURCE_AVAILABLE = "BRAND_POLICY_SOURCE_AVAILABLE"
CLASS_SUITABLE_FOR_MULTI_SOURCE_RETRY = "SUITABLE_FOR_MULTI_SOURCE_RETRY"
CLASS_NO_COMPLIANT_ALTERNATIVE_IDENTIFIED = "NO_COMPLIANT_ALTERNATIVE_IDENTIFIED"
CLASS_DEFER_MANUAL_REVIEW = "DEFER_MANUAL_REVIEW"

# Task 3 static research finding: chain domains observed blocking Wave 1 via
# enterprise edge WAF (Akamai, per the captured "server" response header),
# with no alternative official URL form found anywhere in existing
# repository data (discovery candidate records, prior 004C resolution
# fetches) for any of these 18 specific jobs. Retrying the SAME URL with the
# Task 4 hardened fetcher (longer timeout, one bounded 5xx retry, ordinary
# headers) is the only disclosed, compliant next step -- never a guessed
# endpoint, never stealth.
_KNOWN_BLOCKED_CHAIN_DOMAINS = frozenset({
    "www.hilton.com", "www.marriott.com", "www.ihg.com", "www.hyatt.com",
    "www.redroof.com", "www.radissonhotels.com",
})
_KNOWN_TIMEOUT_PRONE_DOMAINS = frozenset({"www.choicehotels.com"})


def _load_candidates():
    records = []
    for path in sorted(CANDIDATES_DIR.glob("*.json")):
        with path.open(encoding="utf-8") as f:
            records.append((path.name, json.load(f)))
    return records


def classify_job(candidate: dict) -> dict:
    snap = candidate.get("snapshot", {})
    host = urlsplit(snap.get("requested_url", "")).hostname or ""
    status = snap.get("http_status", 0)
    warnings = snap.get("fetch_warnings", [])
    server_header = dict(snap.get("response_header_subset", [])).get("server", "")

    if status == 200 and snap.get("normalized_text"):
        classification = CLASS_NORMAL_FETCHABLE
        retry_suitable = False
        alternative = "n/a (already fetchable)"
    elif "blocked_source" in warnings or status == 403:
        classification = CLASS_HTTP_BLOCKED
        retry_suitable = False
        alternative = (
            CLASS_NO_COMPLIANT_ALTERNATIVE_IDENTIFIED if host in _KNOWN_BLOCKED_CHAIN_DOMAINS
            else CLASS_DEFER_MANUAL_REVIEW)
    elif "fetch_timeout" in warnings:
        classification = CLASS_TIMED_OUT
        retry_suitable = host in _KNOWN_TIMEOUT_PRONE_DOMAINS or True
        alternative = (
            CLASS_SUITABLE_FOR_MULTI_SOURCE_RETRY if retry_suitable
            else CLASS_NO_COMPLIANT_ALTERNATIVE_IDENTIFIED)
    else:
        classification = CLASS_DEFER_MANUAL_REVIEW
        retry_suitable = False
        alternative = CLASS_DEFER_MANUAL_REVIEW

    return {
        "candidate_name": candidate.get("context", {}).get("candidate_name", ""),
        "requested_url": snap.get("requested_url", ""),
        "host": host,
        "http_status": status,
        "server_header": server_header,
        "classification": classification,
        "retry_with_hardened_fetcher_suitable": retry_suitable,
        "alternative_source_status": alternative,
        "brand_alternative_available": False,   # Task 3 finding: none identified for this batch
        "property_identity_source_available": classification == CLASS_NORMAL_FETCHABLE,
        "brand_policy_source_available": False,
    }


def build_report() -> dict:
    records = _load_candidates()
    jobs = [classify_job(c) for _name, c in records]
    jobs.sort(key=lambda j: j["candidate_name"])
    totals = {}
    for j in jobs:
        totals[j["classification"]] = totals.get(j["classification"], 0) + 1
    return {
        "report_version": "1.0.0",
        "mission": "AES-DATA-004E Task 8",
        "source_root": str(CANDIDATES_DIR.relative_to(REPO_ROOT)),
        "job_count": len(jobs),
        "totals_by_classification": totals,
        "jobs": jobs,
    }


def main() -> int:
    report = build_report()
    json.dump(report, sys.stdout, indent=2, sort_keys=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
