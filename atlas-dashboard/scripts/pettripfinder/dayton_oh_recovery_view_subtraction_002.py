"""PTF-DAYTON-OH-HARDENED-APPLICATION-002 -- Phase 11 (cross-check maintenance).

Keep the recovery-002 proposed-authority document's DERIVED views current.

``dayton-recovery-002-proposed-authority.json`` holds three lists. ``candidates``
is the historical record of what PTF-DAYTON-RECOVERY-WORKER-002 proposed and is
never touched. ``candidates_still_proposed`` and ``remaining_unresolved`` are
DERIVED views: each later order subtracts from them whatever has since reached
the published policy package or the exclusion registry, and the document's own
note records each successive subtraction. PTF-DAYTON-CANDIDATE-PROMOTION-001 did
this for twelve identities and PTF-DAYTON-WORK-BROWSER-INTEGRATION-001 for four
more.

Dayton's release contract cross-checks the sum of those two lists against its
stated ``unresolved``. That check exists so a promotion which updated the
authority but not the contract shows up as a partition that no longer covers the
total -- which is exactly what it did here until this pass ran. Maintaining the
views is what keeps the check meaningful; leaving them stale and lowering the
contract instead would silence an independent witness.

Nothing is invented and nothing is deleted from ``candidates``.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.contracts.identity_key import ptf_identity_key  # noqa: E402

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
MARKET = "dayton-oh"
DOC = LP / "identity_census" / "dayton-recovery-002-proposed-authority.json"
POLICY = LP / ("hotel_policy_facts_%s.json" % MARKET)
EXCL = LP / "markets" / "authority" / MARKET / "hotel_exclusions.json"
WORK_ORDER = "PTF-DAYTON-OH-HARDENED-APPLICATION-002"

APPENDED_NOTE = (
    " %s then took the market to 54 / 24 / 51 by applying the 23-row clean "
    "inventory PTF-DAYTON-OH-HARDENED-REVALIDATION-001 recovered at $0 through "
    "the attended lane -- 7 published and 16 excluded. Those identities drop out "
    "of both derived lists below for the same reason every earlier subtraction "
    "did: an identity that has reached the published package or the exclusion "
    "registry is no longer unresolved, and leaving it here would double-count it "
    "against the release contract's cross-check." % WORK_ORDER)


def _load(p):
    return json.loads(Path(p).read_text(encoding="utf-8-sig"))


def build(write: bool):
    doc = _load(DOC)
    published = {r["identity_key"] for r in _load(POLICY)["hotels"]}
    excluded = {ptf_identity_key(e["canonical_name"]) for e in _load(EXCL)["exclusions"]}
    resolved = published | excluded

    before_c = len(doc["candidates_still_proposed"])
    before_r = len(doc["remaining_unresolved"])
    dropped = []

    def keep(rows):
        out = []
        for row in rows:
            key = ptf_identity_key(row["canonical_name"])
            if key in resolved:
                dropped.append((row["canonical_name"],
                                "published" if key in published else "excluded"))
                continue
            out.append(row)
        return out

    doc["candidates_still_proposed"] = keep(doc["candidates_still_proposed"])
    doc["remaining_unresolved"] = keep(doc["remaining_unresolved"])
    if APPENDED_NOTE.strip() not in doc.get("note", ""):
        doc["note"] = (doc.get("note", "").rstrip() + APPENDED_NOTE)

    after = len(doc["candidates_still_proposed"]) + len(doc["remaining_unresolved"])
    print("candidates_still_proposed %d -> %d" % (before_c, len(doc["candidates_still_proposed"])))
    print("remaining_unresolved      %d -> %d" % (before_r, len(doc["remaining_unresolved"])))
    print("sum -> %d" % after)
    print("candidates (historical record) untouched at %d" % len(doc["candidates"]))
    for name, why in dropped:
        print("   dropped %-52s (%s)" % (name[:52], why))
    if write:
        DOC.write_bytes((json.dumps(doc, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
        print("WRITTEN", DOC.relative_to(_REPO_ROOT).as_posix())
    else:
        print("(dry run)")
    return after


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)
    build(args.write)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
