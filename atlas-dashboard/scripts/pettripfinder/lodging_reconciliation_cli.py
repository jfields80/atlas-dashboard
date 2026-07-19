"""AES-DATA-004I -- Columbus lodging reconciliation CLI.

Builds the deterministic source catalog from production seed rows and the
three operational candidate roots (004D / 004E-validation / 004G), groups
duplicates, applies precedence, proposes the promotion set, computes the
fixed beta-threshold decision, and writes every Task 8 artifact under:

    data/import/columbus_lodging_reconciliation/

ZERO network calls. ZERO production mutation -- actual promotion happens
only through the existing approve->staging->promote pipeline, after
explicit operator approval, outside this script.

Usage:
    python scripts/pettripfinder/lodging_reconciliation_cli.py
"""

from __future__ import annotations

import csv
import html
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.pettripfinder.importer.lodging_reconciliation import (  # noqa: E402
    SOURCE_DISCOVERY_ONLY,
    SOURCE_EXCLUDED,
    SOURCE_IMPORTER_READY,
    SOURCE_IMPORTER_REJECT_NO_PETS,
    SOURCE_IMPORTER_REVIEW,
    SOURCE_PRODUCTION_EXISTING,
    choose_canonical,
    group_duplicates,
    threshold_decision,
    validate_proposed_inventory,
)

PRODUCTION_CSV = REPO_ROOT / "launch_packages" / "pettripfinder" / "seed_businesses.csv"
CANDIDATE_ROOTS = (
    ("004D_wave1", REPO_ROOT / "data" / "import" / "columbus_lodging_wave1"),
    ("004E_srcval", REPO_ROOT / "data" / "import" / "columbus_lodging_source_strategy_validation"),
    ("004G_accessible", REPO_ROOT / "data" / "import" / "columbus_accessible_lodging_wave" / "run_001"),
)
ACCESSIBILITY_REPORT = (REPO_ROOT / "data" / "import" / "columbus_accessible_lodging_wave"
                        / "accessibility_report.json")
OUTPUT_ROOT = REPO_ROOT / "data" / "import" / "columbus_lodging_reconciliation"

_POLICY_FIELDS = ("pets_allowed", "pet_fee", "fee_basis", "pet_count_limit",
                  "weight_limit", "breed_restrictions", "species_allowed",
                  "unattended_policy", "general_restrictions")


def load_production_records():
    records = []
    with PRODUCTION_CSV.open(encoding="utf-8") as f:
        for i, row in enumerate(csv.DictReader(f)):
            if row.get("category") != "pet-friendly-hotels":
                continue
            records.append({
                "source_id": "prod_%03d" % i,
                "source_class": SOURCE_PRODUCTION_EXISTING,
                "candidate_id": "",
                "canonical_name": row["name"],
                "address": row.get("address", ""),
                "city": row.get("city", ""),
                "state": row.get("state", ""),
                "postal_code": row.get("postal_code", ""),
                "phone": row.get("phone", ""),
                "official_url": row.get("website_url", ""),
                "dedup_url": row.get("website_url", ""),
                "source_url": row.get("source_url", ""),
                "recommendation": "",
                "reasons": [],
                "pets_allowed": "true",     # every production lodging row is a promoted pet-friendly record
                "policy_fields": {"pet_policy": row.get("pet_policy", "")},
                "verified_at": row.get("observed_at", ""),
                "evidence_count": None,     # evidence lives with the original wave, not the CSV
                "provenance": "production_seed_csv",
                "in_production": True,
            })
    return records


def load_candidate_records():
    records = []
    for wave, root in CANDIDATE_ROOTS:
        for path in sorted((root / "candidates").glob("*.json")):
            with path.open(encoding="utf-8") as f:
                d = json.load(f)
            rec = d.get("recommendation", "")
            reasons = list(d.get("recommendation_reasons", []))
            facts = dict(d.get("pet_facts", []))
            proposed = dict(d.get("proposed_fields", []))
            if rec == "READY":
                cls = SOURCE_IMPORTER_READY
            elif rec == "REVIEW":
                cls = SOURCE_IMPORTER_REVIEW
            elif rec == "REJECT" and "no_pets" in reasons:
                cls = SOURCE_IMPORTER_REJECT_NO_PETS
            else:
                cls = SOURCE_EXCLUDED
            records.append({
                "source_id": "%s:%s" % (wave, d["candidate_id"]),
                "source_class": cls,
                "candidate_id": d["candidate_id"],
                "candidate_path": str(path.relative_to(REPO_ROOT)),
                "canonical_name": proposed.get("name") or d["context"]["candidate_name"],
                "address": proposed.get("address", ""),
                "city": proposed.get("city") or d["context"]["expected_city"],
                "state": proposed.get("state") or d["context"]["expected_state"],
                "postal_code": proposed.get("postal_code", ""),
                "phone": proposed.get("phone", ""),
                "official_url": proposed.get("website_url", "")
                                 or d.get("snapshot", {}).get("requested_url", ""),
                "dedup_url": d.get("snapshot", {}).get("requested_url", "")
                              or proposed.get("website_url", ""),
                "source_url": proposed.get("source_url", ""),
                "recommendation": rec,
                "reasons": reasons,
                "pets_allowed": facts.get("pets_allowed", ""),
                "policy_fields": {k: v for k, v in facts.items() if k in _POLICY_FIELDS},
                "composed_pet_policy": proposed.get("pet_policy", ""),
                "verified_at": d.get("snapshot", {}).get("observed_at", ""),
                "created_at": d.get("created_at", ""),
                "evidence_count": len(d.get("evidence", [])),
                "provenance": wave,
                "in_production": False,
            })
    return records


def load_discovery_only_summary():
    """Summarize the not-yet-attempted discovery universe from the 004G
    accessibility report (job-level, no provider data re-read)."""
    if not ACCESSIBILITY_REPORT.exists():
        return []
    with ACCESSIBILITY_REPORT.open(encoding="utf-8") as f:
        report = json.load(f)
    out = []
    for j in report.get("classified_jobs", []):
        cls = SOURCE_EXCLUDED if j["state"] == "MANUAL_REVIEW" else SOURCE_DISCOVERY_ONLY
        out.append({
            "source_id": "discovery:%s" % j["job_id"],
            "source_class": cls,
            "candidate_id": j["job_id"],
            "canonical_name": j["candidate_name"],
            "city": j["expected_city"],
            "official_url": j["url"],
            "accessibility_state": j["state"],
            "accessibility_reason": j["reason"],
            "exclusions": j["exclusions"],
            "provenance": "004G_accessibility_report",
            "in_production": False,
        })
    return out


def build_reconciliation():
    production = load_production_records()
    candidates = load_candidate_records()
    discovery = load_discovery_only_summary()

    # Duplicate grouping runs over production + candidates only (discovery
    # entries carry no verified identity to merge on and are never promoted).
    catalog = production + candidates
    groups = group_duplicates(catalog)

    by_id = {r["source_id"]: r for r in catalog}
    superseded_ids = set()
    precedence_decisions = []
    for g in groups:
        members = [by_id[m] for m in g["members"]]
        canonical, superseded, reason = choose_canonical(members)
        for s in superseded:
            superseded_ids.add(s["source_id"])
        precedence_decisions.append({
            "group": g["members"],
            "pair_reasons": g["pair_reasons"],
            "retained": canonical["source_id"],
            "superseded": [s["source_id"] for s in superseded],
            "precedence_reason": reason,
        })

    ready = [r for r in candidates
             if r["source_class"] == SOURCE_IMPORTER_READY
             and r["source_id"] not in superseded_ids]
    review = [r for r in candidates if r["source_class"] == SOURCE_IMPORTER_REVIEW]
    no_pets = [r for r in candidates
               if r["source_class"] == SOURCE_IMPORTER_REJECT_NO_PETS
               and r["source_id"] not in superseded_ids]

    promotions = []
    for r in sorted(ready, key=lambda x: x["source_id"]):
        promotions.append({
            **{k: r[k] for k in (
                "source_id", "source_class", "candidate_id", "candidate_path",
                "canonical_name", "address", "city", "state", "postal_code",
                "official_url", "source_url", "recommendation", "pets_allowed",
                "policy_fields", "composed_pet_policy", "verified_at",
                "evidence_count", "provenance")},
            "production_category": "pet-friendly-hotels",
            "promotion_reason": "unique_ready_pet_friendly_not_in_production",
            "duplicate_check": "no_strong_signal_match_against_production",
        })

    exclusions = []
    for r in candidates:
        if r["source_id"] in superseded_ids:
            exclusions.append({"source_id": r["source_id"],
                               "canonical_name": r["canonical_name"],
                               "reason": "superseded_duplicate"})
        elif r["source_class"] == SOURCE_EXCLUDED:
            exclusions.append({"source_id": r["source_id"],
                               "canonical_name": r["canonical_name"],
                               "reason": "rejected_without_no_pets_evidence:" + ",".join(r["reasons"])})
        elif r["source_class"] == SOURCE_IMPORTER_REVIEW:
            exclusions.append({"source_id": r["source_id"],
                               "canonical_name": r["canonical_name"],
                               "reason": "review_never_promoted:" + ",".join(r["reasons"])})

    production_pf = len(production)
    projected_total = production_pf + len(promotions)
    decision = threshold_decision(projected_total)
    validation_errors = validate_proposed_inventory(production, promotions)

    report = {
        "report_version": "1.0.0",
        "mission": "AES-DATA-004I",
        "production_pet_friendly": production_pf,
        "production_no_pets": 0,
        "ready_promotions": len(promotions),
        "no_pets_catalog": len(no_pets),
        "review_held": len(review),
        "duplicate_groups": len(groups),
        "projected_verified_pet_friendly_total": projected_total,
        "projected_verified_no_pets_total": len(no_pets),
        "beta_threshold_decision": decision,
        "validation_errors": validation_errors,
        "discovery_only_jobs": sum(1 for d in discovery
                                    if d["source_class"] == SOURCE_DISCOVERY_ONLY),
        "discovery_excluded_jobs": sum(1 for d in discovery
                                        if d["source_class"] == SOURCE_EXCLUDED),
    }

    return {
        "catalog": catalog + discovery,
        "production": production,
        "groups": groups,
        "precedence": precedence_decisions,
        "ready": sorted(ready, key=lambda r: r["source_id"]),
        "review": sorted(review, key=lambda r: r["source_id"]),
        "no_pets": sorted(no_pets, key=lambda r: r["source_id"]),
        "promotions": promotions,
        "exclusions": sorted(exclusions, key=lambda e: e["source_id"]),
        "report": report,
    }


def _dump(path: Path, obj) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(obj, f, indent=2, sort_keys=False)
        f.write("\n")


def _render_html(result) -> str:
    rows = []
    for p in result["promotions"]:
        rows.append("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>" % tuple(
            html.escape(str(x)) for x in (
                p["canonical_name"], p["city"], p["pets_allowed"],
                p["composed_pet_policy"][:120], p["verified_at"])))
    r = result["report"]
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<title>Columbus Lodging Reconciliation (AES-DATA-004I)</title></head><body>"
        "<h1>Columbus Lodging Reconciliation</h1>"
        "<p>Production pet-friendly: %d | Proposed promotions: %d | "
        "Projected total: %d | Decision: <strong>%s</strong></p>"
        "<h2>Proposed pet-friendly promotions</h2>"
        "<table border='1'><tr><th>Name</th><th>City</th><th>pets_allowed</th>"
        "<th>Policy</th><th>Verified</th></tr>%s</table>"
        "<h2>Verified no-pets (catalog only; no production category exists)</h2><ul>%s</ul>"
        "<h2>Held at REVIEW</h2><ul>%s</ul>"
        "</body></html>"
    ) % (
        r["production_pet_friendly"], r["ready_promotions"],
        r["projected_verified_pet_friendly_total"], html.escape(r["beta_threshold_decision"]),
        "".join(rows),
        "".join("<li>%s</li>" % html.escape(n["canonical_name"]) for n in result["no_pets"]),
        "".join("<li>%s — %s</li>" % (html.escape(v["canonical_name"]),
                                       html.escape(",".join(v["reasons"])))
                for v in result["review"]),
    )


def main() -> int:
    result = build_reconciliation()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    _dump(OUTPUT_ROOT / "source_catalog.json", result["catalog"])
    _dump(OUTPUT_ROOT / "production_baseline.json", result["production"])
    _dump(OUTPUT_ROOT / "duplicate_groups.json",
          {"groups": result["groups"], "precedence": result["precedence"]})
    _dump(OUTPUT_ROOT / "ready_candidates.json", result["ready"])
    _dump(OUTPUT_ROOT / "no_pets_candidates.json", result["no_pets"])
    _dump(OUTPUT_ROOT / "review_candidates.json", result["review"])
    _dump(OUTPUT_ROOT / "proposed_promotions.json", result["promotions"])
    _dump(OUTPUT_ROOT / "proposed_exclusions.json", result["exclusions"])
    _dump(OUTPUT_ROOT / "reconciliation_report.json", result["report"])
    (OUTPUT_ROOT / "reconciliation_report.html").write_text(
        _render_html(result), encoding="utf-8")

    print(json.dumps(result["report"], indent=2))
    print()
    for p in result["promotions"]:
        print("PROMOTE  %-50s %s" % (p["canonical_name"][:50], p["candidate_path"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
