# PetTripFinder Operator Workflow — Directory #1 Runner

This document describes how to use the Directory #1 Operator Runner
(`scripts/generate_launch_kit.py`) to turn a Blueprint + Seed Package into
a launch package on disk. PetTripFinder is used as the worked example
throughout, but the script itself is generic and works for any project.

## What this script does

1. Loads a blueprint JSON (output of the Directory Blueprint Engine).
2. Loads a seed package JSON (output of the Directory Data Ingestion &
   Seeding Engine).
3. Calls the existing `LaunchKitService` with both inputs.
4. Writes the resulting launch package to:

   ```
   launch_packages/{project_slug}/
   ```

It does **not** run any engine logic itself, does not touch the Pipeline
Runner, and has no Flask/HTML/CSS/JS dependency.

## Prerequisites

- Run from the repository root: `C:\Atlas\atlas-dashboard`
- Python available on PATH (`python --version`)
- The real `services.launch_kit_service.LaunchKitService` importable from
  that root (i.e. `services/launch_kit_service.py` exists in the repo)

## Command

From `C:\Atlas\atlas-dashboard` (Windows Command Prompt or PowerShell):

```
python scripts\generate_launch_kit.py --project pettripfinder --blueprint examples\pettripfinder\blueprint_input.json --seed examples\pettripfinder\seed_package_input.json
```

Optional flags:

- `--output-dir launch_packages` — change where packages are written
  (default: `launch_packages`)
- `--overwrite` — regenerate a package that already exists

## Expected output

```
launch_packages/
  pettripfinder/
    launch_package.json        <- full raw export from LaunchKitService
    json_export.json           <- if the service separates this out
    listings.csv                <- if a CSV export is present
    url_map.json
    seo_export.json
    content_plan_export.json
    ai_task_queue_export.json
    launch_checklist.md
    operator_notes.md
```

Not every file will always be produced — the script only writes a file
if the corresponding field is present in what `LaunchKitService` returns.
`launch_package.json` is always written and contains the complete
raw output, so nothing is ever lost even if a specific sub-file is
skipped.

## Using this workflow for PetTripFinder specifically

PetTripFinder.com is currently live but unmonetized. The example
`blueprint_input.json` and `seed_package_input.json` in this repo are
illustrative placeholders (sample Columbus/Dublin, OH listings) meant to
exercise the script end-to-end. Before running this against the real
PetTripFinder data:

1. Replace `examples/pettripfinder/blueprint_input.json` with the actual
   Blueprint Engine output for PetTripFinder.
2. Replace `examples/pettripfinder/seed_package_input.json` with the
   actual Seeding Engine output (ideally the real Webflow/Airtable
   listing export, normalized).
3. Run the command above.
4. Review `launch_checklist.md` and `operator_notes.md` in the generated
   package before doing anything manual (e.g. activating affiliate
   links, publishing content).

## If the script errors out on the LaunchKitService call

The exact method signature of the real `LaunchKitService` was not
available when this script was written. If you see an error like:

```
None of the known LaunchKitService call signatures matched.
```

Open `scripts/generate_launch_kit.py` and look at `build_launch_kit()`.
There is a `candidate_calls` list near the top of that function — add
or fix the one line that matches your actual service method name and
argument order. Nothing else in the script needs to change.

## Re-running / idempotency

This script itself does not track state or write to any database — it
only reads the two input JSON files and writes files to
`launch_packages/{project_slug}/`. Re-running it with `--overwrite` will
regenerate the folder from scratch. Without `--overwrite`, it refuses to
run if the folder already exists, to avoid silently clobbering a package
you may have hand-edited.
