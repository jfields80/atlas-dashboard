"""AES-DATA-001 -- CLI: promote approved staging rows into the production
seed CSV (mission sections 22/23).

Dry run (default, no mutation):

    python scripts/promote_import_candidates.py \\
      --staging data/import/approved_candidates.csv \\
      --target launch_packages/pettripfinder/seed_businesses.csv

Promote (mutates the target atomically; reruns existing validation):

    python scripts/promote_import_candidates.py \\
      --staging data/import/approved_candidates.csv \\
      --target launch_packages/pettripfinder/seed_businesses.csv --confirm

Promotion is the only command permitted to modify production inventory. It
reuses the existing listing_dataset_builder + inventory_validation unchanged.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.listing_dataset_builder import build_listing_dataset
from scripts.pettripfinder.inventory_validation import (
    assess_inventory,
    compute_launch_readiness,
)

_LAUNCH_DIR = _REPO_ROOT / "launch_packages" / "pettripfinder"


def _read_seed_rows(path: Path) -> List[Dict[str, object]]:
    """Read a 15-column seed CSV into builder-shaped rows (empty cells become
    absent; amenities split on ';'). Mirrors the pilot runner's reader
    without importing the heavy pilot module."""
    if not Path(path).exists():
        return []
    rows: List[Dict[str, object]] = []
    with Path(path).open("r", encoding="utf-8", newline="") as f:
        for raw in csv.DictReader(f):
            row: Dict[str, object] = {
                k: v.strip() for k, v in raw.items()
                if k is not None and v is not None and v.strip()
            }
            amenities = str(raw.get("amenities", "") or "").strip()
            row["amenities"] = [a.strip() for a in amenities.split(";") if a.strip()]
            rows.append(row)
    return rows


def _raw_rows(path: Path) -> List[Dict[str, str]]:
    if not Path(path).exists():
        return []
    with Path(path).open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _load_launch(launch_dir: Path) -> Tuple[list, list, dict]:
    categories = json.loads((launch_dir / "categories.json").read_text(encoding="utf-8"))
    locations = json.loads((launch_dir / "locations.json").read_text(encoding="utf-8"))
    config = json.loads((launch_dir / "pilot_config.json").read_text(encoding="utf-8"))
    return (categories, locations, config["inventory_thresholds"])


def _identity(row: Dict[str, str]) -> str:
    return "|".join([(row.get(k) or "").strip().lower() for k in ("name", "city", "state")])


def _assess(seed_rows, categories, locations, reference_date):
    result = build_listing_dataset(
        seed_businesses=seed_rows, categories=categories, locations=locations)
    if result.dataset is None:
        return (result, {}, None)
    assessments = assess_inventory(result.dataset, reference_date=reference_date)
    state_by_name = {a.business_name: a.state for a in assessments}
    readiness = compute_launch_readiness(assessments, _load_thresholds_cache["t"])
    return (result, state_by_name, readiness)


_load_thresholds_cache: Dict[str, dict] = {}


def dry_run(
    staging_csv, target_csv, *, launch_dir=_LAUNCH_DIR, reference_date: str = "",
) -> Dict[str, object]:
    """Combine production + staging, run the existing build/dedup/validation,
    and report -- no mutation."""
    launch_dir = Path(launch_dir)
    categories, locations, thresholds = _load_launch(launch_dir)
    _load_thresholds_cache["t"] = thresholds
    reference_date = reference_date or date.today().isoformat()

    prod_rows = _read_seed_rows(Path(target_csv))
    staging_rows = _read_seed_rows(Path(staging_csv))
    prod_raw = _raw_rows(Path(target_csv))
    staging_raw = _raw_rows(Path(staging_csv))

    prod_result, prod_states, _ = _assess(prod_rows, categories, locations, reference_date)
    combined_result, combined_states, combined_readiness = _assess(
        prod_rows + staging_rows, categories, locations, reference_date)
    staging_result, staging_states, _ = _assess(
        staging_rows, categories, locations, reference_date)

    prod_identities = {_identity(r) for r in prod_raw}
    per_row = []
    promotable = []
    for r in staging_raw:
        name = (r.get("name") or "").strip()
        ident = _identity(r)
        state = staging_states.get(name, "UNKNOWN")
        already = ident in prod_identities
        ok = (state != "NOT_READY") and (not already) and (staging_result.dataset is not None)
        per_row.append({"name": name, "state": state, "already_in_target": already,
                        "promotable": ok})
        if ok:
            promotable.append(r)

    # Existing committed inventory must remain valid: no production listing
    # demoted to NOT_READY by the combination, and the combined build succeeds.
    existing_valid = combined_result.dataset is not None and all(
        combined_states.get(name) != "NOT_READY" for name in prod_states)

    return {
        "rows_considered": len(prod_rows) + len(staging_rows),
        "production_rows": len(prod_rows),
        "staging_rows": len(staging_rows),
        "combined_build_ok": combined_result.dataset is not None,
        "combined_rejected_duplicates": list(combined_result.rejected_duplicates),
        "combined_readiness": combined_readiness,
        "existing_inventory_valid": existing_valid,
        "per_staging_row": per_row,
        "promotable_count": len(promotable),
        "_promotable_raw": promotable,      # internal handoff to promote()
    }


def promote(
    staging_csv, target_csv, *, confirm: bool = False,
    launch_dir=_LAUNCH_DIR, reference_date: str = "",
) -> Dict[str, object]:
    """Dry run unless ``confirm`` is True. On confirm: rerun validation,
    refuse on blocking failure, append only safe rows, write the target
    atomically, and mark promoted candidates in the staging audit."""
    report = dry_run(staging_csv, target_csv,
                     launch_dir=launch_dir, reference_date=reference_date)
    if not confirm:
        report["mode"] = "dry_run"
        report["confirmation_required"] = C.REASON_PROMOTION_CONFIRMATION_REQUIRED
        report.pop("_promotable_raw", None)
        return report

    if not report["combined_build_ok"] or not report["existing_inventory_valid"]:
        report["mode"] = "refused"
        report["reason"] = C.REASON_STAGING_VALIDATION_FAILED
        report.pop("_promotable_raw", None)
        return report

    promotable = report.pop("_promotable_raw", [])
    target_path = Path(target_csv)
    existing_raw = _raw_rows(target_path)
    existing_identities = {_identity(r) for r in existing_raw}

    appended = []
    for row in promotable:
        ident = _identity(row)
        if ident in existing_identities:
            continue
        existing_identities.add(ident)
        appended.append(row)

    all_rows = existing_raw + appended
    _atomic_write_csv(target_path, all_rows)
    _mark_promoted(Path(staging_csv).parent, appended, reference_date)

    report["mode"] = "promoted"
    report["promoted_count"] = len(appended)
    report["promoted_names"] = [r.get("name", "") for r in appended]
    return report


def _atomic_write_csv(target_path: Path, rows: List[Dict[str, str]]) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = target_path.with_suffix(target_path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(C.SEED_CSV_COLUMNS),
                                lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in C.SEED_CSV_COLUMNS})
    os.replace(str(tmp), str(target_path))


def _mark_promoted(staging_dir: Path, promoted_rows, promoted_at: str) -> None:
    audit_path = staging_dir / C.STAGING_AUDIT_NAME
    if not audit_path.exists():
        return
    promoted_idents = {_identity(r) for r in promoted_rows}
    lines = []
    for line in audit_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        ident = "|".join([(rec.get(k) or "").strip().lower()
                          for k in ("name", "city", "state")])
        if ident in promoted_idents:
            rec["review_status"] = C.REVIEW_PROMOTED
            rec["promoted_at"] = promoted_at
        lines.append(json.dumps(rec, sort_keys=True, ensure_ascii=False))
    audit_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Promote staged candidates -> seed CSV.")
    p.add_argument("--staging", default=str(Path(C.DEFAULT_OUTPUT_ROOT) / C.STAGING_CSV_NAME))
    p.add_argument("--target", default=str(_LAUNCH_DIR / "seed_businesses.csv"))
    p.add_argument("--confirm", action="store_true")
    p.add_argument("--reference-date", default="")
    args = p.parse_args(argv)
    result = promote(args.staging, args.target, confirm=args.confirm,
                     reference_date=args.reference_date)
    result.pop("_promotable_raw", None)
    print(json.dumps(result, sort_keys=True, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
