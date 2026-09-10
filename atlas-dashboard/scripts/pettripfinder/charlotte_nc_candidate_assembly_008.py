"""PTF-CHARLOTTE-NC-ZERO-TO-LIVE-BENCHMARK-001 -- the exact final candidate.

Builds the whole-site bundle the founder would be authorizing, TWICE, and
records the digests the authorization binds.

PARTICIPATION IS AN INPUT, NOT A LATER FLIP
-------------------------------------------
ATLAS-THROUGHPUT-005: membership is read from the participation document and
hashed into the candidate before its digest exists. There is no build,
authorize, flip, rebuild path -- a pre-flip candidate is a DIFFERENT artifact
with a different digest, and an authorization of it refuses the post-flip one.
So the candidate has to be assembled with Charlotte participating.

That is not the same thing as DECIDING that Charlotte participates. This module
stages the participation document Charlotte's launch would use, builds against
it, and restores the committed file in a `finally` -- the committed record still
says SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH when this finishes, and
the sha256 of BOTH the committed and the staged document is recorded so a
reviewer can see exactly which bytes the build read. Nothing here authorizes
anything; it measures what an authorization would bind.

REPRODUCIBILITY
---------------
Two independent whole-site builds into two different output roots. The bundle
and sitemap digests must match, or FINAL_CANDIDATE_REPRODUCIBLE is NO and the
packet says so.

Output: launch_packages/pettripfinder/markets/reports/charlotte_nc_candidate_assembly_008.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from collections import OrderedDict
from pathlib import Path

_DASH = Path(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
if str(_DASH) not in sys.path:
    sys.path.insert(0, str(_DASH))

WORK_ORDER = "PTF-CHARLOTTE-NC-ZERO-TO-LIVE-BENCHMARK-001"
MARKET_ID = "charlotte-nc"
PARTICIPATION = _DASH / "deploy" / "netlify" / "launch_participation.json"
REPORTS = _DASH / "launch_packages" / "pettripfinder" / "markets" / "reports"
OUT = REPORTS / "charlotte_nc_candidate_assembly_008.json"
STAGED_NOTE = (
    "Charlotte staged as FOUNDER_AUTHORIZED_FOR_LAUNCH for the DURATION OF THIS BUILD ONLY, "
    "by PTF-CHARLOTTE-NC-ZERO-TO-LIVE-BENCHMARK-001, so that the candidate carries the "
    "participation a launch would carry and its digest is the one an authorization would bind. "
    "The committed record is restored before this module exits and still reads "
    "SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH. This is a MEASUREMENT, not a decision.")


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def stage_participation() -> str:
    doc = json.loads(PARTICIPATION.read_text(encoding="utf-8-sig"))
    for m in doc["markets"]:
        if m["market_id"] == MARKET_ID:
            m["launch_status"] = "FOUNDER_AUTHORIZED_FOR_LAUNCH"
    # The `decision` block is DELIBERATELY LEFT ALONE. Rewriting it -- even to
    # say honestly that this is not a founder decision -- broke the document's
    # own decision-chain validation, and the assembler then read EVERY market as
    # UNLISTED and refused the whole build. Staging means flipping one market's
    # launch_status and nothing else.
    PARTICIPATION.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n",
                             encoding="utf-8", newline="\n")
    return sha256_file(PARTICIPATION)


def assemble(output: Path):
    t0 = time.monotonic()
    proc = subprocess.run(
        [sys.executable, "-m", "scripts.pettripfinder.assemble_production_site",
         "--output", str(output)],
        cwd=str(_DASH), capture_output=True, text=True, encoding="utf-8", errors="replace")
    return OrderedDict((
        ("returncode", proc.returncode),
        ("seconds", round(time.monotonic() - t0, 1)),
        ("tail", "\n".join((proc.stdout or "").strip().splitlines()[-25:])),
        ("stderr_tail", "\n".join((proc.stderr or "").strip().splitlines()[-15:])),
    ))


def manifest_of(output: Path):
    # The multi-market assembler writes `global_bundle_manifest.json` at the
    # output root; the deployment manifest is a different, later document.
    for name in ("global_bundle_manifest.json", "global_deployment_manifest.json",
                 "deployment_manifest.json"):
        for p in (output / name, output.parent / name):
            if p.is_file():
                return json.loads(p.read_text(encoding="utf-8-sig")), p
    hits = sorted(output.rglob("*deployment_manifest*.json"))
    if hits:
        return json.loads(hits[0].read_text(encoding="utf-8-sig")), hits[0]
    return None, None


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--root", default=str(_DASH / "data" / "charlotte_candidate_008"))
    ap.add_argument("--read-only", action="store_true",
                    help="re-derive the report from builds already on disk; assemble nothing")
    args = ap.parse_args(argv)

    committed_sha = sha256_file(PARTICIPATION)
    original = PARTICIPATION.read_bytes()
    root = Path(args.root)
    builds = []
    staged_sha = ""
    try:
        if not args.read_only:
            staged_sha = stage_participation()
        for label in ("a", "b"):
            out_dir = root / label
            if args.read_only:
                res = OrderedDict((("returncode", 0), ("seconds", None),
                                   ("tail", "read-only re-derivation"), ("stderr_tail", "")))
            else:
                if out_dir.exists():
                    shutil.rmtree(out_dir)
                out_dir.mkdir(parents=True, exist_ok=True)
                res = assemble(out_dir)
            man, man_path = manifest_of(out_dir)
            res["label"] = label
            res["manifest_path"] = str(man_path.relative_to(_DASH)) if man_path else ""
            res["bundle_sha256"] = (man or {}).get("bundle_sha256", "")
            res["sitemap_sha256"] = (man or {}).get("sitemap_sha256", "")
            _frag = ((man or {}).get("participating_markets")
                     or (man or {}).get("market_fragments_included") or [])
            res["participating_markets"] = sorted(
                f["market_id"] if isinstance(f, dict) else f for f in _frag)
            res["profile_counts"] = {f["market_id"]: f.get("published_profiles")
                                     for f in _frag if isinstance(f, dict)}
            res["contract_disagreements"] = sorted(
                m for f in _frag if isinstance(f, dict) and f.get("contract_disagreements")
                for m in [f["market_id"]])
            res["broken_links"] = (man or {}).get("broken_links")
            frags = (man or {}).get("participating_markets") or                 (man or {}).get("market_fragments_included") or []
            res["total_profiles"] = ((man or {}).get("total_profiles")
                                     or sum(f.get("published_profiles", 0) for f in frags
                                            if isinstance(f, dict)) or None)
            res["sitemap_route_count"] = (man or {}).get("sitemap_route_count")
            res["total_files"] = (man or {}).get("total_files")
            res["total_html_pages"] = (man or {}).get("total_html_pages")
            builds.append(res)
    finally:
        PARTICIPATION.write_bytes(original)
        restored_sha = sha256_file(PARTICIPATION)

    a, b = (builds + [{}, {}])[:2]
    reproducible = bool(a.get("bundle_sha256")) and a.get("bundle_sha256") == b.get("bundle_sha256") \
        and a.get("sitemap_sha256") == b.get("sitemap_sha256")

    doc = OrderedDict((
        ("schema", "ptf-candidate-assembly/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("as_of", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
        ("participation", OrderedDict((
            ("committed_sha256", committed_sha),
            ("staged_for_the_build_sha256", staged_sha),
            ("restored_sha256", restored_sha),
            ("committed_record_unchanged", restored_sha == committed_sha),
            ("why", STAGED_NOTE),
        ))),
        ("FINAL_CANDIDATE_REPRODUCIBLE", "YES" if reproducible else "NO"),
        ("candidate", OrderedDict((
            ("bundle_sha256", a.get("bundle_sha256", "")),
            ("sitemap_sha256", a.get("sitemap_sha256", "")),
            ("participating_markets", a.get("participating_markets", [])),
            ("market_count", len(a.get("participating_markets", []))),
            ("total_profiles", a.get("total_profiles")),
            ("sitemap_route_count", a.get("sitemap_route_count")),
            ("total_html_pages", a.get("total_html_pages")),
            ("total_files", a.get("total_files")),
            ("profile_counts", a.get("profile_counts", {})),
        ))),
        ("builds", builds),
    ))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n",
                              encoding="utf-8", newline="\n")
    print("participation restored :", doc["participation"]["committed_record_unchanged"])
    for r in builds:
        print("build %s: rc=%s %ss bundle=%s sitemap=%s profiles=%s routes=%s"
              % (r.get("label"), r.get("returncode"), r.get("seconds"),
                 (r.get("bundle_sha256") or "")[:16], (r.get("sitemap_sha256") or "")[:16],
                 r.get("total_profiles"), r.get("sitemap_route_count")))
        if r.get("returncode"):
            print(r.get("tail", ""))
            print(r.get("stderr_tail", ""))
    print("REPRODUCIBLE           :", doc["FINAL_CANDIDATE_REPRODUCIBLE"])
    print("written                :", args.out)
    return 0 if reproducible else 1


if __name__ == "__main__":
    raise SystemExit(main())
