"""PETTRIPFINDER-PROD-003 Gate 2 (Stage D) -- Option-A worker-promotion adapter.

Promotes APPROVED_FOR_PROMOTION worker records (committed approval manifest, each
bound to a frozen Gate-1 result_hash) into the existing operational hotel-policy
corpus SCHEMA, so the unchanged export_hotel_policy_facts.py + site_data.py path
can later publish them. This is promotion automation for records a human has
already approved; it performs NO automatic approval of its own.

Safety model:
  * DRY RUN IS THE DEFAULT. An operational write requires the explicit --apply
    flag. The dry run validates and maps entirely in memory and writes only a
    report to a gitignored review directory -- never into data/import, never the
    committed launch package, never a page, never a deployment file.
  * Every selected record is re-checked against the frozen Gate-1 authority
    (stale hash, route, contradiction, incomplete extraction, source-authority
    ambiguity, multi-term fee signal, official source, evidence, duplicate, and
    collision with the committed package or an existing corpus record). Any
    failed gate excludes that record with an exact reason -- never a partial or
    silent promotion.
  * The mapping never infers a missing fact, never invents a fee basis or
    currency, never flattens a tiered fee, and never force-fits an unmapped fact
    into an unrelated field (unmapped supported facts are retained in
    provenance). Unknown vocabulary values fail closed.
  * Deterministic and idempotent: no wall clock is read; identical inputs yield
    byte-identical output.

This module imports the frozen worker vocabulary and site_data helpers READ-ONLY;
it modifies neither. It never adds to CANDIDATE_ROOTS.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_APP_ROOT = Path(__file__).resolve().parents[2]
if str(_APP_ROOT) not in sys.path:
    sys.path.insert(0, str(_APP_ROOT))

from scripts.pettripfinder import prod003_approvals as PA          # noqa: E402
from scripts.pettripfinder import site_data as SD                  # noqa: E402
from services.research_workers import vocabulary as V              # noqa: E402

BASELINE_COMMIT = "9bc30c13bd05e4e84f77f5826c8e7bb5e776ca53"
FROZEN_WORKER_COMMIT = "cde9745e6cc730a14bfafe05d0d896a0173b3ddd"

APPROVALS_PATH = _APP_ROOT / "launch_packages" / "pettripfinder" / "hotel_worker_approvals.json"
GATE1_MANIFEST_PATH = (_APP_ROOT / "data" / "worker_runs" / "pettripfinder"
                       / "prod003_gate1_review" / "launch_safe_manifest.json")
COMMITTED_PACKAGE_PATH = _APP_ROOT / "launch_packages" / "pettripfinder" / "hotel_policy_facts.json"
# Dedicated proposed destination root for the worker records. NOT added to
# site_data.CANDIDATE_ROOTS and NOT written during a dry run.
PROMOTION_ROOT = _APP_ROOT / "data" / "import" / "columbus_worker_promotion"
DRY_RUN_DIR = _APP_ROOT / "data" / "worker_runs" / "pettripfinder" / "prod003_gate2_dry_run"

REPORT_SCHEMA = "prod003-gate2-dryrun/1.0"

# worker fee_basis canonical token -> importer human phrase. Unknown -> fail closed.
FEE_BASIS_MAP = {
    "per_night": "per night",
    "per_stay": "per stay",
    "per_room": "per room",
    "per_room_per_day": "per room per day",
    "per_room_per_night": "per room per night",
}
# worker fact field -> importer corpus pet_facts field (direct rename, value verbatim).
DIRECT_FACT_MAP = {
    "pets_allowed": "pets_allowed",
    "pet_fee": "pet_fee",
    "maximum_pets": "pet_count_limit",
    "weight_limit": "weight_limit",
    "breed_restrictions": "breed_restrictions",
    "unattended_pet_rule": "unattended_policy",
}
# Supported worker facts with NO importer field -> retained in provenance ONLY,
# never force-fit (fee_currency: no field; refundable_deposit: no field;
# service_animal_note: MUST NOT be mapped into general_restrictions).
PROVENANCE_ONLY_FACTS = ("fee_currency", "refundable_deposit", "service_animal_note")
# worker source_type -> importer source_relationship.
SOURCE_REL_MAP = {"OFFICIAL_PROPERTY": "EXACT_ENTITY_DOMAIN", "OFFICIAL_BRAND": "BRAND_DOMAIN"}


def _slug(listing_key: str) -> str:
    return "worker-promotion-" + "-".join(listing_key.split())


def _destination_path(listing_key: str) -> Path:
    return PROMOTION_ROOT / "candidates" / (_slug(listing_key) + ".json")


# --------------------------------------------------------------------------- #
# Inputs (read-only).
# --------------------------------------------------------------------------- #

def load_context() -> Dict:
    approvals = PA.load_manifest(APPROVALS_PATH)
    gate1 = json.loads(GATE1_MANIFEST_PATH.read_text(encoding="utf-8"))
    g1_safe = {r["listing_key"]: r for r in gate1.get("launch_safe_candidates", [])}
    g1_manual = {r["listing_key"]: r for r in gate1.get("manual_review_candidates", [])}
    committed = json.loads(COMMITTED_PACKAGE_PATH.read_text(encoding="utf-8"))
    committed_keys = {h["key"] for h in committed.get("hotels", [])}
    corpus_ready = set(SD.load_hotel_policy_facts().keys())         # existing operational READY names
    prod_display = {SD.normalize_name(r["name"]): r["name"]
                    for r in SD.read_production_rows() if r["category"] == "pet-friendly-hotels"}
    return {"approvals": approvals, "g1_safe": g1_safe, "g1_manual": g1_manual,
            "committed_keys": committed_keys, "corpus_ready": corpus_ready,
            "prod_display": prod_display, "committed_count": len(committed_keys)}


# --------------------------------------------------------------------------- #
# Mapping (deterministic; no inference; unknown values fail closed).
# --------------------------------------------------------------------------- #

def _species_allowed(facts: Dict[str, Dict]) -> Optional[str]:
    species = [name for field, name in (("dogs_accepted", "dogs"), ("cats_accepted", "cats"))
               if facts.get(field, {}).get("value") == "true"]        # only explicitly-accepted; never inferred
    return ", ".join(species) if species else None


def build_mapping(approval: Dict, g1rec: Dict, display_name: str
                  ) -> Tuple[Optional[Dict], List[Dict], List[Dict], Optional[str]]:
    """Return (corpus_candidate, field_transformations, unmapped_facts, fail_reason).
    fail_reason is a slug (record fails closed) or None."""
    facts = {f["field_name"]: f for f in g1rec["supported_facts"]}
    pet_facts: Dict[str, str] = {}
    transforms: List[Dict] = []

    for wf in sorted(DIRECT_FACT_MAP):
        if wf in facts:
            impf = DIRECT_FACT_MAP[wf]
            pet_facts[impf] = facts[wf]["value"]
            transforms.append({"worker_field": wf, "worker_value": facts[wf]["value"],
                               "importer_field": impf, "importer_value": facts[wf]["value"],
                               "transform": "rename" if wf != impf else "direct"})
    species = _species_allowed(facts)
    if species is not None:
        pet_facts["species_allowed"] = species
        transforms.append({"worker_field": "dogs_accepted+cats_accepted",
                           "worker_value": species, "importer_field": "species_allowed",
                           "importer_value": species, "transform": "composite_no_inference"})
    if "fee_basis" in facts:
        token = facts["fee_basis"]["value"]
        if token not in FEE_BASIS_MAP:
            return (None, transforms, [], "unknown_fee_basis_value:%s" % token)   # fail closed
        pet_facts["fee_basis"] = FEE_BASIS_MAP[token]
        transforms.append({"worker_field": "fee_basis", "worker_value": token,
                           "importer_field": "fee_basis", "importer_value": FEE_BASIS_MAP[token],
                           "transform": "value_map"})

    unmapped = [{"field": wf, "value": facts[wf]["value"], "evidence_quote": facts[wf]["evidence_quote"],
                 "reason": "no_importer_field" if wf != "service_animal_note"
                           else "must_not_map_to_general_restrictions"}
                for wf in PROVENANCE_ONLY_FACTS if wf in facts]

    evidence = [{"field": f["field_name"], "value": f["value"],
                 "quote": f["evidence_quote"], "source_url": f["source_url"]}
                for f in g1rec["supported_facts"]]
    # pet_policy = deterministic join of the DISTINCT verbatim quotes (first-seen order).
    seen, quotes = set(), []
    for f in g1rec["supported_facts"]:
        q = f["evidence_quote"]
        if q and q not in seen:
            seen.add(q)
            quotes.append(q)
    pet_policy = " ".join(quotes)

    source_url = (g1rec.get("source_urls") or [""])[0]
    source_types = sorted({f["source_type"] for f in g1rec["supported_facts"]})
    source_rel = SOURCE_REL_MAP.get(source_types[0], "UNKNOWN") if source_types else "UNKNOWN"

    candidate = {
        "candidate_id": _slug(approval["listing_key"]),
        "recommendation": "READY",
        "source_relationship": source_rel,
        "proposed_fields": [["name", display_name], ["source_url", source_url],
                            ["pet_policy", pet_policy]],
        "pet_facts": sorted([[k, v] for k, v in pet_facts.items()]),
        "evidence": evidence,
        "snapshot": {"observed_at": approval["verification_date"]},
        "worker_provenance": {
            "result_hash": approval["result_hash"],
            "model_id": g1rec.get("model_id", ""),
            "prompt_version": g1rec.get("extraction_prompt_version", ""),
            "validator_version": g1rec.get("rederivation_validator_version", ""),
            "routing_version": g1rec.get("rederivation_routing_version", ""),
            "frozen_worker_commit": FROZEN_WORKER_COMMIT,
            "gate1_route": g1rec.get("final_route", ""),
            "source_types": source_types,
            "approval": {"decision": approval["decision"], "operator": approval["operator"],
                         "approval_date": approval["approval_date"]},
            "unmapped_facts": unmapped,
        },
    }
    return (candidate, transforms, unmapped, None)


def package_projection(candidate: Dict, listing_key: str, display_name: str) -> Dict:
    """How this record would appear in the committed package (mirrors
    export_hotel_policy_facts.build_package per-record logic)."""
    pet_facts = dict(candidate["pet_facts"])
    proposed = dict(candidate["proposed_fields"])
    state = "VERIFIED_NO_PETS" if pet_facts.get("pets_allowed") == "false" else "VERIFIED_PET_FRIENDLY"
    return {
        "key": listing_key,
        "name": display_name,
        "verification_state": state,
        "facts": {k: v for k, v in pet_facts.items() if k in SD._POLICY_FIELDS},
        "evidence_quote": proposed.get("pet_policy", "") or "",
        "verified_at": candidate["snapshot"]["observed_at"],
        "source_url": proposed.get("source_url", ""),
        "source_type": candidate["source_relationship"],
        "evidence_count": len(candidate["evidence"]),
    }


# --------------------------------------------------------------------------- #
# Promotion gates (deterministic).
# --------------------------------------------------------------------------- #

def evaluate(approval: Dict, ctx: Dict, batch_keys: List[str]) -> Dict:
    key = approval["listing_key"]
    failures: List[str] = []

    if approval.get("decision") != PA.DECISION_APPROVED:
        return {"listing_key": key, "listing_name": approval.get("listing_name", ""),
                "decision": approval.get("decision"), "selected": False, "excluded": True,
                "failures": ["decision:%s" % approval.get("decision")], "mapped": None}

    g1rec = ctx["g1_safe"].get(key)
    if g1rec is None:
        failures.append("manual_review_record" if key in ctx["g1_manual"]
                        else "unknown_in_gate1_manifest")
        return _excluded(approval, failures)

    if approval["result_hash"] != g1rec.get("candidate_identity"):
        failures.append("stale_result_hash")
    if g1rec.get("final_route") != "READY":
        failures.append("gate1_route_not_ready")
    rc = set(g1rec.get("reason_codes", []))
    if "CONTRADICTORY_OFFICIAL_SOURCES" in rc:
        failures.append("contradiction")
    if "INCOMPLETE_EXTRACTION" in rc:
        failures.append("incomplete_extraction")
    if "SOURCE_AUTHORITY_AMBIGUITY" in rc:
        failures.append("source_authority_ambiguity")
    if "STRUCTURED_FEE_REQUIRED" in rc:
        failures.append("structured_fee_required")
    if g1rec.get("multi_amount_detected"):
        failures.append("multi_term_fee_signal")
    if not g1rec.get("source_urls"):
        failures.append("no_source_url")
    supported = g1rec.get("supported_facts", [])
    if not supported:
        failures.append("no_supported_facts")
    if not all(str(f.get("source_type", "")).startswith("OFFICIAL") for f in supported):
        failures.append("source_not_official")
    if not all(f.get("evidence_quote") for f in supported):
        failures.append("missing_evidence_quote")
    if key in ctx["committed_keys"]:
        failures.append("collision_committed_package")
    if key in ctx["corpus_ready"]:
        failures.append("collision_existing_corpus_record")
    if batch_keys.count(key) > 1:
        failures.append("duplicate_listing_identity")
    dest = _destination_path(key)
    if dest.exists():
        failures.append("destination_would_overwrite")

    display_name = ctx["prod_display"].get(key, "")
    if not display_name:
        failures.append("no_production_display_row")

    mapped = transforms = unmapped = None
    projection = None
    if not failures:
        mapped, transforms, unmapped, map_fail = build_mapping(approval, g1rec, display_name)
        if map_fail:
            failures.append(map_fail)
            mapped = None
        else:
            projection = package_projection(mapped, key, display_name)

    return {
        "listing_key": key, "listing_name": approval["listing_name"],
        "decision": approval["decision"], "selected": True, "excluded": bool(failures),
        "failures": sorted(failures),
        "result_hash": approval["result_hash"],
        "destination_path": str(dest.relative_to(_APP_ROOT)).replace("\\", "/"),
        "is_new": not dest.exists(),
        "display_name": display_name,
        "mapped_corpus_candidate": mapped,
        "field_transformations": transforms or [],
        "unmapped_facts": unmapped or [],
        "package_projection": projection,
    }


def _excluded(approval: Dict, failures: List[str]) -> Dict:
    return {"listing_key": approval["listing_key"], "listing_name": approval.get("listing_name", ""),
            "decision": approval.get("decision"), "selected": True, "excluded": True,
            "failures": sorted(failures), "mapped_corpus_candidate": None,
            "field_transformations": [], "unmapped_facts": []}


# --------------------------------------------------------------------------- #
# Dry run (default) -- report only, zero operational writes.
# --------------------------------------------------------------------------- #

def evaluate_all(ctx: Dict) -> List[Dict]:
    approvals = sorted(ctx["approvals"].get("approvals", []), key=lambda a: a["listing_key"])
    batch_keys = [a["listing_key"] for a in approvals if a.get("decision") == PA.DECISION_APPROVED]
    return [evaluate(a, ctx, batch_keys) for a in approvals]


def build_report(ctx: Dict, results: List[Dict]) -> Dict:
    considered = results
    selected = [r for r in results if r.get("selected")]
    passed = [r for r in selected if not r["excluded"]]
    excluded = [r for r in considered if r["excluded"]]
    additions = [r for r in passed if r.get("is_new")]
    updates = [r for r in passed if not r.get("is_new")]
    return {
        "schema": REPORT_SCHEMA,
        "mode": "dry_run",
        "wrote_operational_data": False,
        "wrote_committed_package": False,
        "wrote_pages_or_deployment": False,
        "baseline_commit": BASELINE_COMMIT,
        "frozen_worker_commit": FROZEN_WORKER_COMMIT,
        "approval_manifest": "launch_packages/pettripfinder/hotel_worker_approvals.json",
        "promotion_root": str(PROMOTION_ROOT.relative_to(_APP_ROOT)).replace("\\", "/"),
        "promotion_root_in_candidate_roots": False,
        "counts": {
            "considered": len(considered),
            "approved_selected": len(selected),
            "passed_all_gates": len(passed),
            "excluded_by_gate": len(excluded),
            "proposed_new": len(additions),
            "proposed_update": len(updates),
            "conflicts": sum(1 for r in selected if any(
                f.startswith("collision") or f == "duplicate_listing_identity"
                or f == "destination_would_overwrite" for f in r["failures"])),
        },
        "future_package": {
            "current_record_count": ctx["committed_count"],
            "proposed_added": len(passed),
            "expected_total": ctx["committed_count"] + len(passed),
            "would_change": len(passed) > 0,
            "contingent_on": ("--apply writing the candidates AND the exporter being able to "
                              "read the promotion root (a future authorized CANDIDATE_ROOTS / "
                              "site_data change -- NOT done in this stage)"),
        },
        "records": results,
    }


def render_diff(report: Dict) -> str:
    lines: List[str] = []
    lines.append("# PROD-003 Gate 2 (Stage D) -- worker-promotion dry run")
    lines.append("")
    lines.append("**DRY RUN -- zero operational writes.** No candidate JSON was written to "
                 "data/import; the committed launch package was not modified; no page or "
                 "deployment file was touched.")
    c = report["counts"]
    lines.append("")
    lines.append("- Considered: **%d** | Approved-selected: **%d** | Passed all gates: **%d** | "
                 "Excluded: **%d**" % (c["considered"], c["approved_selected"],
                                       c["passed_all_gates"], c["excluded_by_gate"]))
    fp = report["future_package"]
    lines.append("- Future package: %d existing + %d new = **%d** (would_change=%s; contingent on: %s)"
                 % (fp["current_record_count"], fp["proposed_added"], fp["expected_total"],
                    fp["would_change"], fp["contingent_on"]))
    lines.append("")
    excluded = [r for r in report["records"] if r["excluded"]]
    if excluded:
        lines.append("## Excluded")
        for r in excluded:
            lines.append("- **%s** -> %s" % (r["listing_name"], ", ".join(r["failures"])))
        lines.append("")
    lines.append("## Proposed additions (field-level before -> after)")
    lines.append("")
    for r in [x for x in report["records"] if not x["excluded"] and x.get("selected")]:
        lines.append("### %s" % r["listing_name"])
        lines.append("- destination (proposed, NOT written): `%s`  (new=%s)"
                     % (r["destination_path"], r["is_new"]))
        lines.append("- result_hash: `%s`" % r["result_hash"])
        lines.append("- field transformations:")
        for t in r["field_transformations"]:
            lines.append("    - `%s` = `%s`  ->  `%s` = `%s`  [%s]"
                         % (t["worker_field"], t["worker_value"],
                            t["importer_field"], t["importer_value"], t["transform"]))
        if r["unmapped_facts"]:
            lines.append("- unmapped supported facts (retained in provenance, never force-fit):")
            for u in r["unmapped_facts"]:
                lines.append("    - `%s` = `%s`  (%s)  <- \"%s\""
                             % (u["field"], u["value"], u["reason"], u["evidence_quote"]))
        proj = r["package_projection"]
        lines.append("- package projection: key=`%s` name=`%s` state=`%s` facts=%s"
                     % (proj["key"], proj["name"], proj["verification_state"], proj["facts"]))
        lines.append("")
    return "\n".join(lines) + "\n"


def _write_json(path: Path, payload: Dict) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                    encoding="utf-8")


def run_dry_run(out_dir: Path = DRY_RUN_DIR) -> Dict:
    """Evaluate + map all approvals in memory and write ONLY the report to the
    gitignored ``out_dir``. Writes nothing into data/import or the committed
    package. Returns the report."""
    ctx = load_context()
    results = evaluate_all(ctx)
    report = build_report(ctx, results)
    out_dir.mkdir(parents=True, exist_ok=True)
    _write_json(out_dir / "promotion_report.json", report)
    (out_dir / "promotion_diff.md").write_text(render_diff(report), encoding="utf-8")
    return report


def apply_promotion() -> Dict:
    """Write the passing worker candidates into the dedicated promotion root.
    Fails closed: refuses (writes nothing) if ANY approved record fails a gate.
    This is the ONLY code path that writes operational data, and it writes ONLY
    to the dedicated promotion root -- never the committed package, never a page.
    It does NOT add the root to CANDIDATE_ROOTS."""
    ctx = load_context()
    results = evaluate_all(ctx)
    selected = [r for r in results if r.get("selected")]
    failing = [r for r in selected if r["excluded"]]
    if failing:
        raise SystemExit("refusing --apply: %d approved record(s) failed a gate: %s"
                         % (len(failing), {r["listing_key"]: r["failures"] for r in failing}))
    (PROMOTION_ROOT / "candidates").mkdir(parents=True, exist_ok=True)
    written = []
    for r in selected:
        dest = _destination_path(r["listing_key"])
        _write_json(dest, r["mapped_corpus_candidate"])
        written.append(str(dest.relative_to(_APP_ROOT)).replace("\\", "/"))
    return {"applied": True, "written": sorted(written)}


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--apply", action="store_true",
                    help="perform the operational write into the dedicated promotion root "
                         "(default is a zero-write dry run)")
    ap.add_argument("--out-dir", default=str(DRY_RUN_DIR))
    args = ap.parse_args(argv)
    if args.apply:
        result = apply_promotion()
        print("APPLIED: wrote %d candidate file(s):" % len(result["written"]))
        for p in result["written"]:
            print("  ", p)
        return 0
    report = run_dry_run(Path(args.out_dir))
    c = report["counts"]
    print("DRY RUN: considered %d, passed %d, excluded %d (zero operational writes)"
          % (c["considered"], c["passed_all_gates"], c["excluded_by_gate"]))
    print("Report: %s" % args.out_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
