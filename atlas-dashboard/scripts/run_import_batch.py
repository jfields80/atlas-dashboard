"""AES-WORK-001A/B -- CLI: validate a batch manifest and either print its
execution plan (``--dry-run``, no fetch/extraction/persistence) or run it
for real, sequentially, through the existing single/multi-source importers.

Deterministic offline dry-run example (no network, no API key):

    python scripts/run_import_batch.py `
      --manifest data/import/jobs/columbus-wave-1.json `
      --extractor static `
      --dry-run

Deterministic offline execution example (no network, no API key):

    python scripts/run_import_batch.py `
      --manifest data/import/jobs/columbus-wave-1.json `
      --extractor static

Every ``--extractor anthropic`` combination without ``--dry-run`` makes one
live paid call per job -- never silently.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.batch import (
    BatchManifestError,
    BatchRunError,
    build_batch_summary,
    compute_job_fingerprint,
    compute_manifest_hash,
    get_batch_id,
    load_manifest,
    run_batch,
    validate_manifest,
)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Validate a batch import manifest and print its execution plan.")
    p.add_argument("--manifest", required=True)
    p.add_argument("--extractor", choices=("static", "anthropic"), default="static")
    p.add_argument("--model", default=C.DEFAULT_ANTHROPIC_MODEL)
    p.add_argument("--output-root", default=C.DEFAULT_OUTPUT_ROOT)
    p.add_argument("--observed-at", default="")
    p.add_argument("--max-workers", type=int, default=1)
    p.add_argument("--resume", action="store_true")
    p.add_argument("--force", action="store_true")
    p.add_argument("--job-id", action="append", default=[])
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)

    # --- argument-level validation: fail before touching the manifest ----
    if args.resume and args.force:
        print("ERROR: --resume and --force cannot be used together")
        return 2
    if not (1 <= args.max_workers <= C.MAX_BATCH_WORKERS):
        print("ERROR: --max-workers must be between 1 and %d (got %d)"
              % (C.MAX_BATCH_WORKERS, args.max_workers))
        return 2

    # --- manifest loading + validation ------------------------------------
    try:
        manifest = load_manifest(args.manifest)
    except BatchManifestError as exc:
        print("ERROR: %s" % exc)
        return 2

    errors = validate_manifest(manifest, extractor=args.extractor, repo_root=_REPO_ROOT)
    if errors:
        for err in errors:
            print("ERROR: %s" % err)
        return 2

    all_job_ids = [job.job_id for job in manifest.jobs]
    requested_ids = list(args.job_id)
    unknown_ids = [jid for jid in requested_ids if jid not in all_job_ids]
    if unknown_ids:
        print("ERROR: unknown --job-id value(s): %s" % ", ".join(unknown_ids))
        return 2

    observed_at = args.observed_at or date.today().isoformat()

    if args.dry_run:
        # --- plan: identity + fingerprints, no execution -------------------
        batch_id = get_batch_id(manifest)
        manifest_hash = compute_manifest_hash(manifest)
        selected_ids = set(requested_ids) if requested_ids else set(all_job_ids)

        jobs_plan = []
        for job in manifest.jobs:
            route = "single" if len(job.urls) == 1 else "multi"
            if not job.enabled:
                action = "disabled"
            elif job.job_id not in selected_ids:
                action = "not_selected"
            else:
                action = "would_run"
            fingerprint = compute_job_fingerprint(
                job, extractor=args.extractor, model=args.model,
                observed_at=observed_at, repo_root=_REPO_ROOT)
            jobs_plan.append({
                "job_id": job.job_id,
                "enabled": job.enabled,
                "url_count": len(job.urls),
                "route": route,
                "fingerprint": fingerprint,
                "planned_action": action,
            })

        plan = {
            "batch_id": batch_id,
            "batch_name": manifest.batch_name,
            "manifest_hash": manifest_hash,
            "manifest_schema_version": manifest.manifest_schema_version,
            "extractor": args.extractor,
            "model": args.model,
            "observed_at": observed_at,
            "max_workers": args.max_workers,
            "selected_job_ids": sorted(selected_ids),
            "jobs": jobs_plan,
        }
        print(json.dumps(plan, sort_keys=True, ensure_ascii=False, indent=2))
        return 0

    # --- real execution: sequential, through the existing importers --------
    try:
        state = run_batch(
            manifest,
            extractor_mode=args.extractor,
            model=args.model,
            output_root=args.output_root,
            observed_at=observed_at,
            resume=args.resume,
            force=args.force,
            selected_job_ids=tuple(requested_ids),
            repo_root=_REPO_ROOT,
        )
    except BatchRunError as exc:
        print("ERROR: %s" % exc)
        return 2
    except KeyboardInterrupt:
        print("ERROR: batch run interrupted (Ctrl+C)")
        return 130

    summary = build_batch_summary(state, manifest)
    print(json.dumps(summary, sort_keys=True, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
