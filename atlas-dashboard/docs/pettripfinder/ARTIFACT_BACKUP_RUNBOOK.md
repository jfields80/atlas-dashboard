# Worker-Artifact Backup Runbook (Phase 1)

Operational procedure for snapshotting, verifying, and restoring the
PetTripFinder worker-artifact tree.

- Tooling: `scripts/pettripfinder/backup_worker_artifacts.py`,
  `scripts/pettripfinder/restore_worker_artifacts.py`
- Tests: `tests/pettripfinder/test_worker_artifact_backup.py`
- Source root: `atlas-dashboard/data/worker_runs/pettripfinder`

---

## 0. Why this exists

The worker-run tree is gitignored and **entirely untracked**: 0 files tracked by
git. Its size changes with every capture run, so no fixed file or byte count is
recorded here -- **read the live figures from the manifest of the snapshot you
just took** (`manifest.json` -> `files[]`, or the totals the tool prints), or run
the tool with `--dry-run` to scan without writing. It holds the only copies of

- operator **attestations** — a human opened a page and affirmed what it said;
- the browser **captures** behind them;
- the **CAS objects** those attestations cite by SHA-256.

Several source domains now block automated retrieval. A lost capture cannot be
re-fetched. It can only be re-earned by a person doing the work again.

Phase 1 is deliberately small: **full local snapshots, verified, never
deleted.** No pruning, no incremental mode, no upload.

---

## 1. SECURITY — read before moving a snapshot anywhere

> **Captures contain third-party credentials.**
> Captured pages are verbatim third-party HTML. Scanning found **67 Google API
> keys across 12 files**, embedded by Marriott and Hilton in their own public
> markup. They are not our keys, but they are real keys.

Consequences, without exception:

| Rule | Reason |
|---|---|
| **Never commit** captures, screenshots, or CAS objects to git | Would embed third-party keys in permanent history |
| **Never upload a snapshot unencrypted** | Same exposure, plus operator identity |
| **Never place a snapshot in a cloud-sync folder** | `C:\Users\jfiel\OneDrive` exists on this machine and auto-uploads |
| **Never paste capture contents into an issue, log, or chat** | — |

The tooling helps but does not absolve you: neither script ever prints file
contents, and both redact credential-shaped text from error messages.

What **is** safe to share: the manifest (relative path, byte size, SHA-256,
artifact class, timestamp) and the attestation index (see §6).

---

## 2. What is and is not backed up

| Included | Excluded |
|---|---|
| `attestations/`, `captures/`, `cas/objects/` | `**/site/**` rendered previews |
| `retrieval/`, `rendered_retrieval/` | `**/.chrome-profile/**` browser session scratch |
| `model_results/`, `assignments/`, `validated_results/`, `routing_envelopes/` | `*-partial` snapshot directories from a failed run |
| run-level reports and manifests | |

Rendered previews are excluded because the assembler regenerates them from the
committed policy package. The point is restore clarity, not space.

> ### `.chrome-profile` — never back up a browser profile
>
> Every capture batch driven by the automation carries a `.chrome-profile/`
> directory: the dedicated Chrome profile the runner drives. **It is not
> evidence.** No capture JSON, screenshot, view file, journal or batch manifest
> lives inside one.
>
> It does contain, per profile:
>
> - `Cookies` — live session cookies for the sites visited
> - `Login Data` — the credential store
> - `Web Data` — autofill and form data
> - `Trust Tokens`
> - `Service Worker/CacheStorage/**` — service-worker caches
>
> **A browser profile must never enter an artifact backup.** §1 already forbids
> moving third-party API keys found inside captured markup; session cookies and a
> credential store are a sharper form of the same exposure, and unlike the API
> keys they are not somebody else's — they are this machine's browsing session.
>
> This exclusion was added after a full run failed partway through. At the time,
> profiles accounted for the large majority of both the file count and the byte
> total of the source tree, so excluding them also removes most of the volume —
> but volume is not the reason. Credentials are.

Do not read this section as licence to drop anything else. The evidence
inclusion policy is unchanged apart from browser profiles and failed-run
`*-partial` directories: everything that is evidence is still backed up, and
nothing is pruned.

### Source roots (namespaces)

A snapshot may cover more than one artifact tree. Each is stored under its own
namespace directory inside `payload/`, so two trees can hold files with
identical relative paths without colliding. Nothing is included implicitly —
every root must be named on the command line.

File and byte counts are deliberately not tabulated here; they move with every
run. Take them from the manifest, or from `--dry-run`.

| Namespace | Path | Include? |
|---|---|---|
| `pettripfinder` | `data/worker_runs/pettripfinder` | **Yes** — operator attestations, captures, machine-review records |
| `accessible_lodging_wave` | `data/import/columbus_accessible_lodging_wave/run_001` | **Yes, separate namespace** — see below |

**Second tree (`accessible_lodging_wave`)** — an automated accessible-lodging
import wave: 20 candidate records, 20 reports, 20 content-addressed page
objects, 4 batch files. It is *not* a duplicate: its CAS objects are
**completely disjoint** from the worker-run tree (0 of 20 shared). Most of it is
reproducible machine output, but **4 of 20 candidates carry recorded human
approval decisions**, and the 20 CAS objects are point-in-time page captures
that a re-fetch would not reproduce byte-for-byte. It contains the same class of
third-party API keys inside `.bin` objects, and zero absolute paths, so it is
portable. Back it up — under its own namespace, never merged into the
attestation tree, because its provenance and retention value differ.

---

## 3. Choosing a backup root

The `--backup-root` is **required and has no default**. The tool refuses to run
if it resolves inside the source root, or anywhere inside the git repository.

On this machine only `C:` exists. Until an external drive is attached, use:

```
C:\AtlasBackups\worker_artifacts
```

- Outside `C:\Atlas`, so no git operation and no `git clean -fdx` can reach it.
- **Not** inside `C:\Users\jfiel\OneDrive` — that folder auto-syncs and would
  upload third-party keys in the clear.
- **Honest limitation — read this before relying on the snapshot.**
  `C:\AtlasBackups` is on the **same physical disk as the source**. This machine
  has exactly one filesystem drive (`C:`), so no second local destination is
  available. The snapshot therefore protects against **accidental deletion,
  `git clean -fdx`, and a bad edit** — and **not** against drive failure, theft,
  ransomware, or loss of the machine. A single-disk backup is a copy, not
  disaster recovery.

- **Required for off-device disaster recovery:** a **verified, encrypted second
  copy** held off this device. Encryption is not optional — §1 explains why: the
  payload contains third-party API keys embedded in captured markup, and a
  snapshot moved in the clear exposes them along with operator identity. The
  second copy must be verified exactly as the primary is: every manifest entry
  present, every hash matched. Until it exists, treat the corpus as single-copy,
  and remember that a lost capture can only be re-earned by a person doing the
  work again.

### Windows extended-length paths

Capture filenames are derived from URLs and run long. Under the snapshot prefix
one real capture reached **275 characters**, past the Win32 `MAX_PATH` limit of
260, and a full run failed outright with a bare
`[WinError 3] The system cannot find the path specified`.

The tool therefore addresses every file it reads, copies or hashes through the
Win32 extended-length form — see `long_path()`, used by the copy, the hash and
the verification passes. A deep destination is handled rather than truncated, so
neither a registry change nor a shortened backup root is required.

If you ever see `WinError 3` from this tool on a path that plainly exists,
suspect a code path that bypassed `long_path()`, not a missing file.

---

## 4. Create a snapshot

`--source-root` is **repeatable** and accepts `NAMESPACE=PATH` (or a bare path,
in which case the namespace is the directory name).

Dry run first — scans and reports, writes nothing:

```sh
cd C:\Atlas\atlas-dashboard
python scripts/pettripfinder/backup_worker_artifacts.py ^
  --source-root pettripfinder=data/worker_runs/pettripfinder ^
  --source-root accessible_lodging_wave=data/import/columbus_accessible_lodging_wave/run_001 ^
  --backup-root C:\AtlasBackups\worker_artifacts ^
  --dry-run
```

Then the real snapshot (same command without `--dry-run`):

```sh
python scripts/pettripfinder/backup_worker_artifacts.py ^
  --source-root pettripfinder=data/worker_runs/pettripfinder ^
  --source-root accessible_lodging_wave=data/import/columbus_accessible_lodging_wave/run_001 ^
  --backup-root C:\AtlasBackups\worker_artifacts
```

Duplicate namespaces, the same path supplied twice, and two namespaces pointing
at one tree are all refused. Every root is validated independently — a second
root inside the repository is rejected exactly like the first.

What it does, in order:

1. Refuses if the source root is missing, or the backup root is unsafe.
2. Hashes every included file (SHA-256, streamed).
3. Builds the snapshot in `snapshots/<id>-partial/`.
4. Copies each file, then **re-hashes the destination copy**. Any mismatch
   aborts immediately.
5. Writes `manifest.json`, then `manifest.sha256`.
6. Renames `-partial` → final. **Only a fully verified snapshot is ever
   promoted**, so a half-written snapshot can never be mistaken for a good one.

If a run fails, the `-partial/` directory is left in place for inspection. The
tool never deletes it — remove it yourself once you have looked.

Snapshot ids default to a UTC timestamp (`2026-07-31T140000Z`). An existing id
is refused, never overwritten.

---

## 5. Verify and restore

**Verify-only** — safe at any time; touches nothing outside the snapshot. This
is the quarterly drill:

```sh
python scripts/pettripfinder/restore_worker_artifacts.py ^
  --snapshot-root C:\AtlasBackups\worker_artifacts\snapshots\<snapshot-id> ^
  --verify-only
```

It checks `manifest.sha256`, re-hashes every payload file, and fails on any
missing, mismatched, or **undeclared** file.

**Restore into a scratch directory** (never over the live tree during a drill).
A snapshot spanning several namespaces requires **one `--destination-root` per
namespace** — the tool will not infer where a tree belongs:

```sh
python scripts/pettripfinder/restore_worker_artifacts.py ^
  --snapshot-root C:\AtlasBackups\worker_artifacts\snapshots\<snapshot-id> ^
  --destination-root pettripfinder=C:\AtlasBackups\restore-test\pettripfinder ^
  --destination-root accessible_lodging_wave=C:\AtlasBackups\restore-test\accessible_lodging_wave
```

A missing mapping, an unknown namespace (typo protection), and a single bare
destination for a multi-namespace snapshot are all hard refusals.

Behaviour:

- Verification always runs first; a failing snapshot is never partly restored.
- Files are staged into `<destination>/.restore-staging-<id>/`, verified there,
  placed, then verified again at the final location.
- An existing destination file **blocks** the restore. `--allow-existing-identical`
  skips files that are already byte-identical; a file whose content **differs**
  is never overwritten, with or without the flag.
- Nothing in the destination is ever deleted.

### Restore drill (quarterly)

1. `--verify-only` against the newest snapshot.
2. Restore into an empty scratch directory.
3. Confirm every CAS object's filename equals its own SHA-256.
4. Confirm every attestation's `screenshots[].sha256` resolves to a present
   CAS object.
5. Record the date and snapshot id below. Delete the scratch directory.

| Date | Snapshot id | Result | By |
|---|---|---|---|
| _(first drill pending)_ | | | |

---

## 6. Attestation index

The index lives at a **git-tracked** path:

```
docs/pettripfinder/artifact_indexes/attestation_index.json
```

Regenerate it with:

```sh
python scripts/pettripfinder/backup_worker_artifacts.py ^
  --source-root data/worker_runs/pettripfinder ^
  --emit-attestation-index docs/pettripfinder/artifact_indexes/attestation_index.json
```

It carries **metadata only** — `listing_key`, `attestation_id`,
`attestation_hash`, `observed_at`, `operator_id`, `capture_sha256`,
`publishable`, and `source_url` *only when that URL passes a safety check*
(no embedded userinfo, no private/local host, no non-web scheme, no
credential-shaped query parameter, no credential pattern). A URL that fails is
omitted and replaced with `source_url_omitted` plus a machine-readable
`source_url_omission_reason`.

It contains no HTML, screenshots, page payloads, headers, cookies, tokens, or
absolute paths. `test_tracked_index_is_clean` enforces this on every test run.

**Resolved in Phase 1B.** The index previously sat under
`data/worker_runs/pettripfinder/_index/`, which `atlas-dashboard/.gitignore:34`
(`data/`) ignores, so it was never trackable. It was relocated to the tracked
`docs/` path above after verifying the replacement was byte-identical, and the
old copy was removed. **No `.gitignore` rule was changed** — relocation made a
negation unnecessary. `test_tracked_index_path_is_not_gitignored` now asserts
this on every test run.

---

## 7. Retention (Phase 1 = manual)

Nothing is deleted automatically. The tools have no prune mode at all.

Target shape once you begin pruning by hand:

- 7 daily, 4 weekly, 12 monthly.
- A permanent `milestone` snapshot at each inventory milestone.
- **Append-only evidence rule:** never delete a snapshot that is the only copy
  of an attestation or CAS object. Confirm by comparing manifests — if every
  `sha256` in the old snapshot also appears in a newer one, it is safe to drop.

---

## 8. Phase 2 (not implemented)

1. Second physical destination (external drive).
2. Encrypted offsite copy — `age` with an identity file kept in a password
   manager, or 7-Zip AES-256 if no new tooling is wanted.
3. Scheduled task + drill reminder.

The §6 index-tracking decision was resolved in Phase 1B and is no longer a
Phase 2 prerequisite.

Encryption keys and passphrases never go in this repository.
