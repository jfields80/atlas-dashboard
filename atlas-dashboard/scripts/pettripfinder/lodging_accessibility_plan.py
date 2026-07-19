"""AES-DATA-004G (Tasks 2-5) -- accessible-lodging planner CLI.

Classifies every generated Columbus lodging import job with the
domain-access registry (``importer/lodging_accessibility.py``), deduplicates
the job universe, compares it against production inventory and prior live
waves, ranks the executable remainder, and emits:

  data/import/columbus_accessible_lodging_wave/accessibility_report.json
  data/import/columbus_accessible_lodging_wave/manifests/
      accessible_lodging_batch_001.json

Deterministic; makes ZERO network calls; never mutates production inventory
or the source manifests.

Usage:
    python scripts/pettripfinder/lodging_accessibility_plan.py [--max-jobs 20]
        [--max-timeout-jobs 1] [--max-per-domain 4]
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.pettripfinder.importer.lodging_accessibility import (  # noqa: E402
    ACCESS_ACCESSIBLE_CONFIRMED,
    ACCESS_ACCESSIBLE_PROBABLE,
    ACCESS_TIMEOUT_RETRY_ELIGIBLE,
    DOMAIN_REGISTRY_VERSION,
    EXECUTABLE_STATES,
    _registrable,
    classify_url_accessibility,
    executable_sort_key,
)

MANIFESTS_DIR = REPO_ROOT / "data" / "discovery" / "columbus_wave1_lodging" / "resolution" / "import_batches"
PRODUCTION_CSV = REPO_ROOT / "launch_packages" / "pettripfinder" / "seed_businesses.csv"
OUTPUT_ROOT = REPO_ROOT / "data" / "import" / "columbus_accessible_lodging_wave"

# Prior live waves whose jobs must never be re-executed here (Task 5:
# "already imported properties"). Manifest paths, not property names.
PRIOR_WAVE_MANIFESTS = (
    REPO_ROOT / "data" / "discovery" / "columbus_wave1_lodging" / "resolution"
    / "import_batches" / "hotel_batch_001.json",
    REPO_ROOT / "data" / "import" / "columbus_lodging_source_strategy_validation"
    / "manifest" / "source_strategy_validation_batch.json",
)

BATCH_ID = "columbus-accessible-lodging-001"
BATCH_NAME = "Columbus Accessible Lodging 001"


def normalize_url(url: str) -> str:
    parts = urlsplit(url or "")
    host = (parts.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = (parts.path or "").rstrip("/").lower()
    return host + path


def normalize_name(name: str) -> str:
    n = (name or "").lower().replace("&", "and")
    n = re.sub(r"[^a-z0-9 ]+", " ", n)
    return " ".join(n.split())


def load_all_jobs():
    jobs = []
    for path in sorted(MANIFESTS_DIR.glob("*.json")):
        with path.open(encoding="utf-8") as f:
            manifest = json.load(f)
        for job in manifest["jobs"]:
            jobs.append({"source_manifest": path.name, **job})
    return jobs


def load_production_hotels():
    with PRODUCTION_CSV.open(encoding="utf-8") as f:
        return [r for r in csv.DictReader(f) if r.get("category") == "pet-friendly-hotels"]


def load_prior_wave_urls_and_ids():
    urls, ids = set(), set()
    for path in PRIOR_WAVE_MANIFESTS:
        if not path.exists():
            continue
        with path.open(encoding="utf-8") as f:
            manifest = json.load(f)
        for job in manifest["jobs"]:
            ids.add(job["job_id"])
            for u in job["urls"]:
                urls.add(normalize_url(u))
    return urls, ids


def build_plan(max_jobs: int, max_timeout_jobs: int, max_per_domain: int) -> dict:
    jobs = load_all_jobs()
    production = load_production_hotels()
    prior_urls, prior_ids = load_prior_wave_urls_and_ids()

    prod_by_name = {normalize_name(r["name"]): r for r in production}
    prod_by_url = {normalize_url(r.get("website_url", "")): r for r in production
                   if r.get("website_url")}

    classified = []
    seen_urls = {}
    universe_dupes = []
    for job in jobs:
        url = job["urls"][0] if job["urls"] else ""
        state, reason = classify_url_accessibility(url)
        entry = {
            "job_id": job["job_id"],
            "candidate_name": job["candidate_name"],
            "expected_city": job["expected_city"],
            "expected_state": job["expected_state"],
            "url": url,
            "url_count": len(job["urls"]),
            "domain": _registrable(urlsplit(url).hostname or "") if url else "",
            "state": state,
            "reason": reason,
            "source_manifest": job["source_manifest"],
            "exclusions": [],
            "raw_job": {k: job[k] for k in (
                "candidate_name", "category", "enabled", "expected_city",
                "expected_state", "job_id", "source_relationship_hint",
                "source_type_hint", "static_fixtures", "urls")},
        }
        norm = normalize_url(url)
        if norm and norm in seen_urls:
            entry["exclusions"].append("duplicate_of:" + seen_urls[norm])
            universe_dupes.append((entry["job_id"], seen_urls[norm]))
        elif norm:
            seen_urls[norm] = job["job_id"]

        prod_match = None
        if normalize_name(job["candidate_name"]) in prod_by_name:
            prod_match = prod_by_name[normalize_name(job["candidate_name"])]
        elif norm in prod_by_url:
            prod_match = prod_by_url[norm]
        if prod_match is not None:
            entry["exclusions"].append("production_duplicate:" + prod_match["name"])
            entry["production_name_mismatch"] = (
                normalize_name(prod_match["name"]) != normalize_name(job["candidate_name"]))

        if job["job_id"] in prior_ids or norm in prior_urls:
            entry["exclusions"].append("already_attempted_prior_wave")

        classified.append(entry)

    # --- report aggregates (Task 2) ---------------------------------------
    by_state = {}
    domains_by_state = {}
    for e in classified:
        by_state.setdefault(e["state"], []).append(e)
        domains_by_state.setdefault(e["state"], set()).add(e["domain"])

    executable = [
        e for e in classified
        if e["state"] in EXECUTABLE_STATES and not e["exclusions"]
    ]
    executable.sort(key=lambda e: executable_sort_key(e["state"], e["reason"], e["job_id"]))

    # Timeout-domain probes ranked by pending-job count on that domain
    # (higher count = more information value per probe), then job_id.
    timeout_pool = [e for e in executable if e["state"] == ACCESS_TIMEOUT_RETRY_ELIGIBLE]
    domain_counts = {}
    for e in classified:
        domain_counts[e["domain"]] = domain_counts.get(e["domain"], 0) + 1
    timeout_pool.sort(key=lambda e: (-domain_counts.get(e["domain"], 0), e["job_id"]))

    # --- batch selection (Tasks 3/5) --------------------------------------
    # Slots are reserved for the timeout probes up front: a single probe at
    # the highest-pending-count timeout domain carries information value for
    # every other job on that domain, so it must not be squeezed out by the
    # last-ranked probable job.
    probe_count = min(max_timeout_jobs, len(timeout_pool))
    selected = []
    per_domain = {}
    for e in executable:
        if len(selected) >= max_jobs - probe_count:
            break
        if e["state"] == ACCESS_TIMEOUT_RETRY_ELIGIBLE:
            continue   # handled from the ranked timeout pool below
        if per_domain.get(e["domain"], 0) >= max_per_domain:
            continue
        selected.append(e)
        per_domain[e["domain"]] = per_domain.get(e["domain"], 0) + 1
    for e in timeout_pool[:probe_count]:
        if len(selected) >= max_jobs:
            break
        selected.append(e)

    batch = {
        "batch_id": BATCH_ID,
        "batch_name": BATCH_NAME,
        "defaults": {},
        "jobs": sorted((e["raw_job"] for e in selected), key=lambda j: j["job_id"]),
        "manifest_schema_version": "1.0",
    }

    report = {
        "report_version": "1.0.0",
        "mission": "AES-DATA-004G Tasks 2-5",
        "domain_registry_version": DOMAIN_REGISTRY_VERSION,
        "total_jobs": len(jobs),
        "unique_jobs_after_url_dedup": len(jobs) - len(universe_dupes),
        "universe_duplicate_pairs": universe_dupes,
        "counts_by_state": {s: len(v) for s, v in sorted(by_state.items())},
        "domains_by_state": {s: sorted(d) for s, d in sorted(domains_by_state.items())},
        "single_source_jobs": sum(1 for e in classified if e["url_count"] == 1),
        "multi_source_jobs": sum(1 for e in classified if e["url_count"] > 1),
        "independent_small_chain_jobs": sum(
            1 for e in classified if e["reason"] == "unobserved_independent_domain"),
        "waf_blocked_jobs": len(by_state.get("WAF_BLOCKED", [])),
        "timeout_retry_jobs": len(by_state.get("TIMEOUT_RETRY_ELIGIBLE", [])),
        "missing_source_jobs": len(by_state.get("MISSING_OFFICIAL_SOURCE", [])),
        "production_duplicates": [
            {"job_id": e["job_id"], "candidate_name": e["candidate_name"],
             "matched": [x for x in e["exclusions"] if x.startswith("production_duplicate:")][0]}
            for e in classified
            if any(x.startswith("production_duplicate:") for x in e["exclusions"])],
        "already_attempted_prior_wave": [
            e["job_id"] for e in classified
            if "already_attempted_prior_wave" in e["exclusions"]],
        "executable_jobs_estimate": len(executable),
        "estimated_http_exposure_selected": len(selected),
        "estimated_anthropic_exposure_selected": len(selected),
        "selected_batch": {
            "batch_id": BATCH_ID,
            "job_count": len(selected),
            "jobs": [
                {"job_id": e["job_id"], "candidate_name": e["candidate_name"],
                 "expected_city": e["expected_city"], "url": e["url"],
                 "state": e["state"], "reason": e["reason"], "domain": e["domain"]}
                for e in sorted(selected, key=lambda x: x["job_id"])],
        },
        "classified_jobs": [
            {k: e[k] for k in ("job_id", "candidate_name", "expected_city", "url",
                                "domain", "state", "reason", "exclusions",
                                "source_manifest")}
            for e in classified],
    }
    return {"report": report, "batch": batch}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-jobs", type=int, default=20)
    parser.add_argument("--max-timeout-jobs", type=int, default=1)
    parser.add_argument("--max-per-domain", type=int, default=4)
    args = parser.parse_args()

    if args.max_jobs > 20:
        raise SystemExit("max-jobs is hard-capped at 20 for this phase")
    if args.max_timeout_jobs > 3:
        raise SystemExit("max-timeout-jobs is hard-capped at 3 for this phase")

    result = build_plan(args.max_jobs, args.max_timeout_jobs, args.max_per_domain)

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    (OUTPUT_ROOT / "manifests").mkdir(exist_ok=True)

    report_path = OUTPUT_ROOT / "accessibility_report.json"
    with report_path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(result["report"], f, indent=2, sort_keys=False)
        f.write("\n")

    batch_path = OUTPUT_ROOT / "manifests" / "accessible_lodging_batch_001.json"
    with batch_path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(result["batch"], f, indent=2, sort_keys=True)
        f.write("\n")

    print("report:", report_path.relative_to(REPO_ROOT))
    print("batch:", batch_path.relative_to(REPO_ROOT))
    print("selected jobs:", result["report"]["selected_batch"]["job_count"])
    for j in result["report"]["selected_batch"]["jobs"]:
        print("  %-22s %-12s %-50s %s" % (
            j["state"], j["expected_city"][:12], j["candidate_name"][:50], j["domain"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
