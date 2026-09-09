"""ATLAS-THROUGHPUT-006 -- the trusted artifact handoff.

005 established the rule this module enforces:

    NO BUILDER MAY RUN BETWEEN VALIDATION, AUTHORIZATION AND DEPLOYMENT.

Once a remote runner is in the loop that rule needs teeth, because the easiest
way to "fix" a handoff problem is to rebuild the candidate on the far side and
call it equivalent. It is not equivalent. It is a different artifact that was
never validated, and every guarantee 003, 004 and 005 established is about
specific bytes.

So a candidate travels as a content-addressed archive with a manifest that
names every file's digest, and the receiver re-hashes what it got. A remote
environment may COPY, EXTRACT, HASH, READ and TEST. It may not produce
replacement deployment bytes: ``substitution_problems`` exists to catch exactly
that, by comparing the received tree against the digests the sender recorded
rather than against a rebuilt copy.

Cross-platform is the reason this is byte-oriented rather than tree-oriented.
The factory builds on Windows; a runner is likely Linux. Text-mode copying,
line-ending translation, a lost executable bit or a case-folded path would all
silently change the artifact. The archive stores bytes and modes explicitly and
the receiver proves the digest, so Linux never has to reproduce Windows output
-- it only has to carry it faithfully and test it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import sys
import zipfile
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from scripts.pettripfinder import assemble_production_site as APS
from scripts.pettripfinder import sealed_market_package as SMP

HANDOFF_SCHEMA = "ptf-artifact-handoff/1.0"

#: Files a candidate directory carries besides ``site/``. Everything here is
#: evidence: dropping one would let a receiver validate a candidate it cannot
#: prove the provenance of.
CANDIDATE_FILES = (
    "release_manifest.json",
    "release_diff.json",
    "gates.json",
    "fast_lane_receipt.json",
    "telemetry.json",
    "authorization.json",
)
REQUIRED_FILES = ("release_manifest.json",)

#: Refusals.
ARCHIVE_DIGEST_MISMATCH = "ARCHIVE_DIGEST_MISMATCH"
FILE_DIGEST_MISMATCH = "FILE_DIGEST_MISMATCH"
FILE_MISSING = "FILE_MISSING"
FILE_ADDED = "FILE_ADDED"
BUNDLE_DIGEST_MISMATCH = "BUNDLE_DIGEST_MISMATCH"
CANDIDATE_DIGEST_MISMATCH = "CANDIDATE_DIGEST_MISMATCH"
REQUIRED_FILE_MISSING = "REQUIRED_FILE_MISSING"
SUBSTITUTED_ARTIFACT = "SUBSTITUTED_ARTIFACT"


class HandoffError(RuntimeError):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__("%s: %s" % (code, detail) if detail else code)
        self.code = code
        self.detail = detail


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def _walk(root: Path) -> List[Tuple[str, Path]]:
    out: List[Tuple[str, Path]] = []
    for path in sorted(Path(root).rglob("*")):
        if path.is_file():
            out.append((path.relative_to(root).as_posix(), path))
    return out


def file_digests(root: Path) -> "OrderedDict[str, str]":
    """Every file under ``root``, by posix relative path, with its digest."""
    return OrderedDict((rel, _sha256_file(path)) for rel, path in _walk(root))


# --------------------------------------------------------------------------- #
# Packaging.
# --------------------------------------------------------------------------- #

def package_candidate(candidate_dir: Path, archive_path: Path) -> "OrderedDict[str, Any]":
    """Write a deterministic archive of a staged candidate and describe it.

    Deterministic: entries sorted, a fixed timestamp, stored bytes only. Two
    packagings of the same candidate produce the same archive digest, which is
    what makes "the artifact changed in transit" a decidable question rather
    than a judgement call.
    """
    candidate_dir = Path(candidate_dir)
    archive_path = Path(archive_path)
    site = candidate_dir / "site"
    if not site.is_dir():
        raise HandoffError(REQUIRED_FILE_MISSING, "no site/ under %s" % candidate_dir)
    manifest_path = candidate_dir / "release_manifest.json"
    if not manifest_path.is_file():
        raise HandoffError(REQUIRED_FILE_MISSING, "no release_manifest.json under %s" % candidate_dir)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))

    members: "OrderedDict[str, str]" = OrderedDict()
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = archive_path.with_name(archive_path.name + ".tmp")
    with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for rel, path in _walk(site):
            member = "site/" + rel
            info = zipfile.ZipInfo(member, date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = 0o644 << 16
            data = path.read_bytes()
            zf.writestr(info, data)
            members[member] = "sha256:" + hashlib.sha256(data).hexdigest()
        for name in CANDIDATE_FILES:
            path = candidate_dir / name
            if not path.is_file():
                continue
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = 0o644 << 16
            data = path.read_bytes()
            zf.writestr(info, data)
            members[name] = "sha256:" + hashlib.sha256(data).hexdigest()
    os.replace(str(tmp), str(archive_path))

    doc = OrderedDict((
        ("schema", HANDOFF_SCHEMA),
        ("candidate_digest", SMP.sha256_text(SMP.canonical_json(manifest))),
        ("deployment_artifact_digest", manifest.get("deployment_artifact_digest")),
        ("parent_release_digest", manifest.get("parent_release_digest")),
        ("intended_delta_digest", manifest.get("intended_delta_digest")),
        ("participating_markets", list(manifest.get("participating_markets") or ())),
        ("source_commit", manifest.get("source_commit")),
        ("archive", archive_path.name),
        ("archive_sha256", _sha256_file(archive_path)),
        ("archive_bytes", archive_path.stat().st_size),
        ("file_count", len(members)),
        ("site_file_count", sum(1 for m in members if m.startswith("site/"))),
        ("members", members),
        ("evidence_present", sorted(n for n in CANDIDATE_FILES if (candidate_dir / n).is_file())),
        ("evidence_absent", sorted(n for n in CANDIDATE_FILES if not (candidate_dir / n).is_file())),
        ("packaged_from", str(candidate_dir)),
    ))
    return doc


def receive_candidate(archive_path: Path, handoff: Mapping, dest: Path,
                      *, verify: bool = True) -> "OrderedDict[str, Any]":
    """Extract an archive and prove it is the artifact the sender described.

    The archive digest is checked BEFORE extraction, so a corrupted or swapped
    archive never reaches the filesystem the tests will read.
    """
    archive_path = Path(archive_path)
    dest = Path(dest)
    problems: List[str] = []
    actual_archive = _sha256_file(archive_path)
    if verify and actual_archive != handoff.get("archive_sha256"):
        raise HandoffError(ARCHIVE_DIGEST_MISMATCH,
                           "archive hashes %s, the handoff says %s"
                           % (actual_archive[7:23], str(handoff.get("archive_sha256"))[7:23]))
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True)
    with zipfile.ZipFile(archive_path) as zf:
        zf.extractall(dest)

    expected = OrderedDict(handoff.get("members") or {})
    actual: "OrderedDict[str, str]" = OrderedDict()
    for rel, path in _walk(dest):
        actual[rel] = _sha256_file(path)
    for rel, digest in expected.items():
        if rel not in actual:
            problems.append("%s: %s" % (FILE_MISSING, rel))
        elif actual[rel] != digest:
            problems.append("%s: %s" % (FILE_DIGEST_MISMATCH, rel))
    for rel in actual:
        if rel not in expected:
            problems.append("%s: %s" % (FILE_ADDED, rel))
    for name in REQUIRED_FILES:
        if not (dest / name).is_file():
            problems.append("%s: %s" % (REQUIRED_FILE_MISSING, name))

    site = dest / "site"
    bundle = APS.bundle_digest(APS.file_hashes(site)) if site.is_dir() else None
    if bundle != handoff.get("deployment_artifact_digest"):
        problems.append("%s: received bytes hash %s, the handoff says %s"
                        % (BUNDLE_DIGEST_MISMATCH, str(bundle)[:16],
                           str(handoff.get("deployment_artifact_digest"))[:16]))
    manifest_path = dest / "release_manifest.json"
    candidate = None
    if manifest_path.is_file():
        candidate = SMP.sha256_text(SMP.canonical_json(
            json.loads(manifest_path.read_text(encoding="utf-8-sig"))))
        if candidate != handoff.get("candidate_digest"):
            problems.append("%s: received manifest is candidate %s, the handoff says %s"
                            % (CANDIDATE_DIGEST_MISMATCH, str(candidate)[7:23],
                               str(handoff.get("candidate_digest"))[7:23]))
    return OrderedDict((
        ("received_at", str(dest)),
        ("archive_sha256", actual_archive),
        ("deployment_artifact_digest", bundle),
        ("candidate_digest", candidate),
        ("file_count", len(actual)),
        ("problems", problems),
        ("identical", not problems),
    ))


def substitution_problems(handoff: Mapping, candidate_dir: Path) -> List[str]:
    """Refuse a candidate directory that is not the artifact that was sent.

    This is the anti-rebuild check. A remote runner that regenerated the site
    would produce a tree that differs somewhere -- a timestamp, a commit
    stamped into a manifest, one reordered attribute -- and every one of those
    is caught here, because the comparison is against the SENDER's digests and
    not against a fresh build.
    """
    candidate_dir = Path(candidate_dir)
    problems: List[str] = []
    site = candidate_dir / "site"
    if not site.is_dir():
        return ["%s: no site/ under %s" % (REQUIRED_FILE_MISSING, candidate_dir)]
    bundle = APS.bundle_digest(APS.file_hashes(site))
    if bundle != handoff.get("deployment_artifact_digest"):
        problems.append("%s: deployment bytes are %s, the validated artifact is %s -- a rebuilt "
                        "candidate is a different artifact, never an equivalent one"
                        % (SUBSTITUTED_ARTIFACT, bundle[:16],
                           str(handoff.get("deployment_artifact_digest"))[:16]))
    expected = OrderedDict(handoff.get("members") or {})
    for rel, digest in expected.items():
        if not rel.startswith("site/"):
            continue
        path = candidate_dir / rel
        if not path.is_file():
            problems.append("%s: %s" % (FILE_MISSING, rel))
        elif _sha256_file(path) != digest:
            problems.append("%s: %s" % (FILE_DIGEST_MISMATCH, rel))
    return problems


def round_trip(candidate_dir: Path, work_dir: Path) -> "OrderedDict[str, Any]":
    """Package, receive and re-verify -- the phase 12 proof, end to end.

    Records the digest at every hop so a reader can see that the same value
    appears at staging, in the archive, on arrival and at the point of
    authorization.
    """
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    before = APS.bundle_digest(APS.file_hashes(Path(candidate_dir) / "site"))
    handoff = package_candidate(candidate_dir, work_dir / "candidate.zip")
    received = receive_candidate(work_dir / "candidate.zip", handoff, work_dir / "received")
    after = received["deployment_artifact_digest"]
    again = package_candidate(work_dir / "received", work_dir / "candidate-2.zip")
    return OrderedDict((
        ("staged_deployment_digest", before),
        ("handoff_deployment_digest", handoff["deployment_artifact_digest"]),
        ("received_deployment_digest", after),
        ("candidate_digest_staged", handoff["candidate_digest"]),
        ("candidate_digest_received", received["candidate_digest"]),
        ("archive_sha256", handoff["archive_sha256"]),
        ("archive_sha256_repackaged", again["archive_sha256"]),
        ("archive_is_deterministic", handoff["archive_sha256"] == again["archive_sha256"]),
        ("identical", bool(received["identical"] and before == after)),
        ("problems", received["problems"]),
    ))


# --------------------------------------------------------------------------- #
# Phase 13: what crossing platforms can silently change.
# --------------------------------------------------------------------------- #

def cross_platform_audit(candidate_dir: Path) -> "OrderedDict[str, Any]":
    """What would differ if this artifact were rebuilt on another platform.

    The answer is not "nothing" -- it is "we never find out", because the
    artifact is carried, not rebuilt. This audit records the hazards that would
    apply if anyone tried, and proves the ones the archive already neutralises.
    """
    candidate_dir = Path(candidate_dir)
    site = candidate_dir / "site"
    files = _walk(site)
    crlf = [rel for rel, path in files
            if path.suffix in (".html", ".xml", ".txt", ".json")
            and b"\r\n" in path.read_bytes()]
    lower: Dict[str, List[str]] = {}
    for rel, _path in files:
        lower.setdefault(rel.lower(), []).append(rel)
    case_collisions = sorted(v for v in lower.values() if len(v) > 1)
    long_paths = [rel for rel, _p in files if len(rel) > 180]
    backslashes = [rel for rel, _p in files if "\\" in rel]
    executable = [rel for rel, path in files if os.name != "nt" and path.stat().st_mode & stat.S_IXUSR]
    return OrderedDict((
        ("files", len(files)),
        ("crlf_files", len(crlf)),
        ("crlf_examples", crlf[:5]),
        ("case_collisions", case_collisions[:5]),
        ("paths_over_180_chars", len(long_paths)),
        ("longest_path", max((len(rel) for rel, _p in files), default=0)),
        ("backslash_members", backslashes[:5]),
        ("executable_bits", len(executable)),
        ("neutralised_by", "the archive stores bytes and a fixed mode, and the receiver proves the "
                           "digest; line endings, path case and file modes cannot drift in transit"),
        ("residual_risk", "a receiver that REBUILDS instead of carrying would hit every one of these; "
                          "substitution_problems is what refuses that artifact"),
    ))


def main(argv: Optional[Sequence[str]] = None) -> int:  # pragma: no cover - CLI
    parser = argparse.ArgumentParser(description="ATLAS-THROUGHPUT-006 -- trusted artifact handoff")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("package")
    p.add_argument("--candidate", required=True)
    p.add_argument("--archive", required=True)
    p.add_argument("--out")
    p = sub.add_parser("receive")
    p.add_argument("--archive", required=True)
    p.add_argument("--handoff", required=True)
    p.add_argument("--dest", required=True)
    p = sub.add_parser("round-trip")
    p.add_argument("--candidate", required=True)
    p.add_argument("--work", required=True)
    args = parser.parse_args(argv)

    if args.command == "package":
        doc = package_candidate(Path(args.candidate), Path(args.archive))
        if args.out:
            Path(args.out).write_text(SMP.canonical_json(doc) + "\n", encoding="utf-8", newline="\n")
        print(SMP.canonical_json(OrderedDict((k, v) for k, v in doc.items() if k != "members")))
        return 0
    if args.command == "receive":
        handoff = json.loads(Path(args.handoff).read_text(encoding="utf-8-sig"))
        result = receive_candidate(Path(args.archive), handoff, Path(args.dest))
        print(SMP.canonical_json(result))
        return 0 if result["identical"] else 1
    if args.command == "round-trip":
        result = round_trip(Path(args.candidate), Path(args.work))
        print(SMP.canonical_json(result))
        return 0 if result["identical"] else 1
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
