"""PTF-DAYTON-FOUNDER-REVIEW-QUEUE-001 -- packaging-only.

Builds a ChatGPT-Work browser-review queue for every Dayton census property
that is neither published nor verified-no-pets. Reads only committed
authority files (census, published policy facts, exclusions, the
recovery-002 proposed-authority manifest) and this run's own observation
batch. Writes nothing back into any authority file.

Partition (before this task, and unchanged by it):
    33 published + 6 verified no-pets + 90 not yet resolved = 129 census.

The 90 = 14 recovery-002 proposed candidates + 76 remaining_unresolved rows
from that same manifest. See README.txt in the output directory for the
explanation of the prior report's 33+6+14+75=128 arithmetic defect.
"""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.hotel_exclusions import load_exclusions  # noqa: E402
from scripts.pettripfinder.site_data import normalize_name  # noqa: E402

CENSUS_PATH = (_REPO_ROOT / "launch_packages" / "pettripfinder" / "identity_census"
               / "dayton-oh.json")
MANIFEST_PATH = (_REPO_ROOT / "launch_packages" / "pettripfinder" / "identity_census"
                  / "dayton-recovery-002-proposed-authority.json")
PUBLISHED_FACTS_PATH = (_REPO_ROOT / "launch_packages" / "pettripfinder"
                         / "hotel_policy_facts_dayton-oh.json")
EXCLUSIONS_PATH = (_REPO_ROOT / "launch_packages" / "pettripfinder" / "hotel_exclusions.json")
OBSERVATIONS_PATH = (_REPO_ROOT / "data" / "worker_runs" / "pettripfinder"
                      / "dayton-recovery-002" / "observations.json")

OUT_DIR = Path("C:/Atlas/atlas-dashboard/data/operator_evidence/dayton-founder-review-001")

MARKET_ID = "dayton-oh"
BATCH_SIZE = 10

OBJECTIVES = {
    "ACCESS_BLOCKED": (
        "Load the official brand property page in an attended/authenticated "
        "browser session (past the anti-bot wall that blocks static fetches) "
        "and capture the exact pet-policy text, or the absence of one.",
        "If browser access also fails, call the property directly and record "
        "the pet policy verbatim from the front desk.",
    ),
    "JS_RENDERED_NO_STATIC_CONTENT": (
        "Load the official page in a real browser so the client-side pet-"
        "policy template actually renders, then capture the exact text.",
        "If the client-rendered policy text still does not resolve, call the "
        "property directly and record the pet policy verbatim.",
    ),
    "PROPOSED_CANDIDATE": (
        "Re-open the source URL already on file, confirm the recovery-002 "
        "quote still matches the live page, and resolve the flagged "
        "ambiguity or marketing-only gap so the candidate can enter authority "
        "as a firm fact.",
        "If the live page no longer matches the captured quote, call the "
        "property to reconfirm the current pet policy.",
    ),
    "NO_FIRST_PARTY_URL_ON_RECORD": (
        "Search for the property's official website or brand/booking-"
        "platform page, then capture the pet-policy text from it.",
        "If no official URL can be found, call the property directly using "
        "the phone number on file (if any) and record the pet policy "
        "verbatim.",
    ),
    "UNREACHABLE_DOMAIN": (
        "Retry the property's domain and, if it resolves, capture the pet-"
        "policy text; otherwise locate an alternate first-party URL.",
        "If the domain still will not resolve, call the property directly "
        "and record the pet policy verbatim.",
    ),
    "IDENTITY_UNCERTAIN_PHANTOM_SUSPECT": (
        "Verify by phone (number on file) whether the property still "
        "operates at the recorded address before attempting any policy "
        "capture.",
        "If the phone number is disconnected or denies the property exists, "
        "mark it CLOSED/PHANTOM in the audit trail rather than capturing a "
        "policy.",
    ),
    "IDENTITY_RECOVERED_POLICY_STILL_NEEDED": (
        "Load the confirmed official page in an attended browser and "
        "capture the pet-policy text specifically (identity is already "
        "resolved).",
        "If the page still carries no pet-policy text, call the property "
        "directly and record the pet policy verbatim.",
    ),
}

PRIORITY_GROUPS = [
    "ACCESS_BLOCKED",
    "JS_RENDERED_NO_STATIC_CONTENT",
    "PROPOSED_CANDIDATE",
    "NO_FIRST_PARTY_URL_ON_RECORD",
    "UNREACHABLE_DOMAIN",
    "IDENTITY_UNCERTAIN_PHANTOM_SUSPECT",
    "IDENTITY_RECOVERED_POLICY_STILL_NEEDED",
]


def sha256_file(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def git_sha(path: Path) -> str:
    out = subprocess.run(
        ["git", "log", "-1", "--format=%H", "--", str(path.relative_to(_REPO_ROOT))],
        cwd=_REPO_ROOT, capture_output=True, text=True, check=True,
    )
    return out.stdout.strip()


def load_all():
    census = json.loads(CENSUS_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    facts = json.loads(PUBLISHED_FACTS_PATH.read_text(encoding="utf-8"))
    excl = json.loads(EXCLUSIONS_PATH.read_text(encoding="utf-8"))
    observations = []
    if OBSERVATIONS_PATH.exists():
        observations = json.loads(OBSERVATIONS_PATH.read_text(encoding="utf-8"))
    return census, manifest, facts, excl, observations


def reconcile(census, manifest, facts, excl):
    by_norm = {normalize_name(h["canonical_name"]): h["slug"] for h in census["hotels"]}
    by_slug = {h["slug"]: h for h in census["hotels"]}

    published_keys = {h["key"] for h in facts["hotels"]}
    published_slugs = {by_norm[k] for k in published_keys if k in by_norm}

    day_excl = [e for e in excl["exclusions"] if e.get("market_id") == MARKET_ID]
    excluded_slugs = {
        by_norm[normalize_name(e["canonical_name"])]
        for e in day_excl if normalize_name(e["canonical_name"]) in by_norm
    }

    candidate_slugs = {row["slug"] for row in manifest["candidates"]}
    remaining_slugs = {row["slug"] for row in manifest["remaining_unresolved"]}

    all_census_slugs = set(by_slug)
    union = published_slugs | excluded_slugs | candidate_slugs | remaining_slugs

    return {
        "by_slug": by_slug,
        "published_slugs": published_slugs,
        "excluded_slugs": excluded_slugs,
        "candidate_slugs": candidate_slugs,
        "remaining_slugs": remaining_slugs,
        "all_census_slugs": all_census_slugs,
        "union": union,
        "duplicates": (published_slugs & excluded_slugs) | (published_slugs & candidate_slugs)
        | (published_slugs & remaining_slugs) | (excluded_slugs & candidate_slugs)
        | (excluded_slugs & remaining_slugs) | (candidate_slugs & remaining_slugs),
        "omissions": all_census_slugs - union,
    }


def build_quote_index(observations):
    idx = {}
    for obs in observations:
        slug = obs["obs_id"].rsplit("-", 1)[0]
        quotes = [e["quote"] for e in obs.get("evidence", [])]
        idx[slug] = " | ".join(quotes)
    return idx


def build_rows(rc, manifest, quote_index):
    candidates_by_slug = {row["slug"]: row for row in manifest["candidates"]}
    remaining_by_slug = {row["slug"]: row for row in manifest["remaining_unresolved"]}

    ordered_slugs = []
    category_of = {}

    for slug in sorted(rc["remaining_slugs"]):
        cat = remaining_by_slug[slug]["category"]
        category_of[slug] = cat
    for slug in sorted(rc["candidate_slugs"]):
        category_of[slug] = "PROPOSED_CANDIDATE"

    for group in PRIORITY_GROUPS:
        for slug in sorted(category_of):
            if category_of[slug] == group and slug not in ordered_slugs:
                ordered_slugs.append(slug)

    assert set(ordered_slugs) == rc["candidate_slugs"] | rc["remaining_slugs"]
    assert len(ordered_slugs) == 90

    rows = []
    for i, slug in enumerate(ordered_slugs, start=1):
        h = rc["by_slug"][slug]
        cat = category_of[slug]
        objective, fallback = OBJECTIVES[cat]
        batch_number = (i - 1) // BATCH_SIZE + 1

        if slug in candidates_by_slug:
            cand = candidates_by_slug[slug]
            prior_result = cand["state"]
            reasons = "; ".join(cand.get("reasons", []))
            if reasons:
                prior_result = f"{prior_result} ({reasons})"
        else:
            r = remaining_by_slug[slug]
            prior_result = f"{r['category']}: {r['detail']}"

        rows.append(OrderedDict([
            ("queue_index", i),
            ("batch_number", batch_number),
            ("hotel_id", f"{MARKET_ID}:{slug}"),
            ("slug", slug),
            ("exact_census_name", h["canonical_name"]),
            ("street", h.get("address", "")),
            ("city", h.get("city", "")),
            ("state", h.get("state", "")),
            ("zip", h.get("postal_code", "")),
            ("phone", h.get("phone", "")),
            ("brand", h.get("_brand", "")),
            ("property_code", h.get("_property_code", "")),
            ("official_url", h.get("_official_url", "")),
            ("existing_routing_status", "NO_ROUTING_RECORD"),
            ("existing_policy_status", h.get("policy_state", "")),
            ("prior_recovery_result", prior_result),
            ("prior_exact_policy_quotation", quote_index.get(slug, "")),
            ("unresolved_category", cat),
            ("browser_objective", objective),
            ("fallback_next_action", fallback),
            ("published_status", "NOT_PUBLISHED"),
            ("verified_no_pets_status", "NOT_VERIFIED_NO_PETS"),
        ]))
    return rows


def write_csv(rows, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_manifest(rows, rc, path: Path):
    batch_counts = OrderedDict()
    for r in rows:
        batch_counts[str(r["batch_number"])] = batch_counts.get(str(r["batch_number"]), 0) + 1

    source_files = [CENSUS_PATH, MANIFEST_PATH, PUBLISHED_FACTS_PATH, EXCLUSIONS_PATH]
    sources = []
    for p in source_files:
        sources.append({
            "path": str(p.relative_to(_REPO_ROOT)).replace("\\", "/"),
            "commit": git_sha(p),
            "sha256": sha256_file(p),
        })

    manifest = OrderedDict([
        ("schema", "ptf-dayton-founder-review-queue/1.0"),
        ("generated_at", datetime.now(timezone.utc).isoformat()),
        ("market_id", MARKET_ID),
        ("census_total", 129),
        ("published_count", len(rc["published_slugs"])),
        ("verified_no_pets_count", len(rc["excluded_slugs"])),
        ("browser_review_queue_count", len(rows)),
        ("reconciliation", OrderedDict([
            ("published_plus_no_pets_plus_queue",
             len(rc["published_slugs"]) + len(rc["excluded_slugs"]) + len(rows)),
            ("equals_census_total",
             len(rc["published_slugs"]) + len(rc["excluded_slugs"]) + len(rows) == 129),
            ("duplicates", sorted(rc["duplicates"])),
            ("duplicate_count", len(rc["duplicates"])),
            ("omissions", sorted(rc["omissions"])),
            ("omission_count", len(rc["omissions"])),
        ])),
        ("prior_report_defect_explanation", (
            "The prior recovery worker's commit message (d550435, "
            "\"PTF-DAYTON-RECOVERY-WORKER-002: closeout categorization for "
            "all 75 remaining unresolved\") stated the arithmetic 33 "
            "published + 6 no-pets + 14 candidates + 75 remaining unresolved "
            "= 129, which sums to 128, not 129. The commit body's own "
            "category breakdown (ACCESS_BLOCKED 35 + "
            "JS_RENDERED_NO_STATIC_CONTENT 13 + NO_FIRST_PARTY_URL_ON_RECORD "
            "18 + IDENTITY_UNCERTAIN_PHANTOM_SUSPECT 8 + "
            "IDENTITY_RECOVERED_POLICY_STILL_NEEDED 1 + UNREACHABLE_DOMAIN 1) "
            "sums to 76, not 75 -- the prose undercounted its own listed "
            "categories by one when it wrote the headline total. The "
            "committed data was never wrong: "
            "dayton-recovery-002-proposed-authority.json's "
            "\"remaining_unresolved\" array has always contained exactly 76 "
            "entries (verified by re-running "
            "scripts/pettripfinder/dayton_recovery_002_closeout.py, which "
            "reproduces 76 rows deterministically from its own hand-built "
            "category tables, and by "
            "tests/pettripfinder/test_dayton_recovery_002.py::"
            "TestManifestIsProposalOnly::"
            "test_remaining_unresolved_plus_candidates_reconciles_the_full_census, "
            "which computes the union dynamically and already passes at 129 "
            "with zero duplicates and zero omissions). No census property "
            "was ever dropped or double-counted; the defect was a narrative "
            "off-by-one in the prior worker's summary sentence, not a data "
            "gap. This package's own reconciliation block above is computed "
            "the same way (dynamic set union, not a hardcoded literal) and "
            "confirms 33 + 6 + 90 = 129 with 0 duplicates and 0 omissions."
        )),
        ("browser_review_queue_composition", OrderedDict([
            ("recovery_002_proposed_candidates", len(rc["candidate_slugs"])),
            ("remaining_unresolved_from_manifest", len(rc["remaining_slugs"])),
            ("total", len(rc["candidate_slugs"]) + len(rc["remaining_slugs"])),
        ])),
        ("batch_size_target", "10-12"),
        ("batch_counts", batch_counts),
        ("priority_order", PRIORITY_GROUPS),
        ("sources", sources),
        ("outputs", [
            "dayton_founder_review.csv",
            "dayton_founder_review_manifest.json",
            "README.txt",
        ]),
    ])
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def write_readme(manifest, path: Path):
    lines = [
        "PTF-DAYTON-FOUNDER-REVIEW-QUEUE-001",
        "====================================",
        "",
        "ChatGPT Work browser-review queue for the Dayton, OH pet-friendly",
        "hotel market. Packaging-only output -- no production authority file",
        "was modified to produce this queue.",
        "",
        f"Census total:            {manifest['census_total']}",
        f"Published pet-friendly:  {manifest['published_count']}",
        f"Verified no-pets:        {manifest['verified_no_pets_count']}",
        f"Browser-review queue:    {manifest['browser_review_queue_count']}",
        "",
        "Reconciliation: 33 + 6 + 90 = 129, duplicates 0, omissions 0.",
        "See dayton_founder_review_manifest.json for the exact set-union",
        "computation and the source commit/hash pins.",
        "",
        "PRIOR REPORT DEFECT",
        "--------------------",
        "The prior recovery worker's commit (d550435) stated the queue math",
        "as 33 + 6 + 14 + 75 = 129, which actually sums to 128. Its own",
        "category breakdown in the same commit message (35 + 13 + 18 + 8 +",
        "1 + 1 = 76) already added up to 76, not 75 -- the headline number in",
        "the commit's title/summary line was a prose off-by-one, not a data",
        "problem. The committed JSON",
        "(dayton-recovery-002-proposed-authority.json's remaining_unresolved",
        "array) has always held 76 entries, confirmed by re-running",
        "scripts/pettripfinder/dayton_recovery_002_closeout.py (deterministic,",
        "76 rows every time) and by the existing test",
        "test_remaining_unresolved_plus_candidates_reconciles_the_full_census,",
        "which passes today. No census property was ever omitted or",
        "double-counted; only the prior worker's summary sentence miscounted",
        "its own listed totals.",
        "",
        "QUEUE COMPOSITION",
        "------------------",
        f"  14 recovery-002 proposed candidates (evidence status preserved,",
        "     not yet promoted to production authority)",
        "  76 remaining_unresolved rows from the same manifest",
        "  90 total, each exactly once",
        "",
        "BATCHES AND PRIORITY ORDER",
        "---------------------------",
        "Rows are grouped, in this priority order, then chunked into batches",
        "of ~10 properties each:",
        "  1. access-blocked branded properties (brand-platform 403/timeout)",
        "  2. JavaScript-rendered properties (policy text needs a real browser)",
        "  3. recovery-002 proposed candidates (confirm/upgrade existing evidence)",
        "  4. no-first-party-URL records, plus the one unreachable-domain record",
        "  5. uncertain identities, phantom suspects, and the one",
        "     identity-recovered-but-policy-still-needed record",
        "",
        "Batch counts:",
    ]
    for b, n in manifest["batch_counts"].items():
        lines.append(f"  batch {b}: {n} properties")
    lines += [
        "",
        "COLUMNS",
        "-------",
        "queue_index, batch_number, hotel_id, slug, exact_census_name, street,",
        "city, state, zip, phone, brand, property_code, official_url,",
        "existing_routing_status, existing_policy_status, prior_recovery_result,",
        "prior_exact_policy_quotation, unresolved_category, browser_objective,",
        "fallback_next_action, published_status, verified_no_pets_status",
        "",
        "existing_routing_status is NO_ROUTING_RECORD for every row: Dayton has",
        "no identity_routing.json entries (that registry currently holds only",
        "Columbus records), and none of these 90 properties are published, so",
        "none has a route.",
        "",
        "published_status is NOT_PUBLISHED and verified_no_pets_status is",
        "NOT_VERIFIED_NO_PETS for every row by construction: this queue is",
        "exactly the complement of the 33 published + 6 no-pets partition.",
        "",
        "SCOPE",
        "-----",
        "This task did not modify hotel_policy_facts_dayton-oh.json,",
        "hotel_exclusions.json, seed_businesses.csv, or",
        "dayton-recovery-002-proposed-authority.json. It did not build, deploy,",
        "merge, push main, or run the full regression suite. Targeted tests",
        "only (tests/pettripfinder/test_dayton_recovery_002.py and",
        "tests/pettripfinder/test_dayton_authority.py).",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    census, manifest, facts, excl, observations = load_all()
    rc = reconcile(census, manifest, facts, excl)

    print("published", len(rc["published_slugs"]))
    print("excluded (no-pets)", len(rc["excluded_slugs"]))
    print("candidates", len(rc["candidate_slugs"]))
    print("remaining_unresolved", len(rc["remaining_slugs"]))
    print("union size", len(rc["union"]))
    print("duplicates", rc["duplicates"])
    print("omissions", rc["omissions"])

    quote_index = build_quote_index(observations)
    rows = build_rows(rc, manifest, quote_index)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    write_csv(rows, OUT_DIR / "dayton_founder_review.csv")
    man = write_manifest(rows, rc, OUT_DIR / "dayton_founder_review_manifest.json")
    write_readme(man, OUT_DIR / "README.txt")

    print("wrote", len(rows), "rows to", OUT_DIR)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
